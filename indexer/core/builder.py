#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图谱构建器 - 流程编排

整合所有 Phase，提供统一的构建接口
"""

import os
import time
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set, Tuple, List, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from indexer.models import SchemaGraph, TableSchema, RelationEdge
from indexer import SimpleLogger
from indexer.report.html_generator import HTMLReportGenerator
from indexer.analysis.analyzer import GraphAnalyzer
from indexer.storage.json_storage import JsonGraphStorage

from .config import BuildConfig
from indexer.discovery import (
    ContainmentDiscovery,
    AbbreviationDiscovery,
    TransitiveDiscovery,
    NamingConventionDiscovery,
    FeedbackManager
)


@dataclass
class BuildResult:
    """构建结果统计"""
    table_count: int = 0
    relation_count: int = 0
    new_tables: int = 0
    updated_tables: int = 0
    deleted_tables: int = 0
    scan_time: float = 0.0
    discover_time: float = 0.0
    total_time: float = 0.0

    def summary(self) -> str:
        return (
            f"{self.table_count} 表, {self.relation_count} 关系 | "
            f"新增 {self.new_tables}, 更新 {self.updated_tables}, 删除 {self.deleted_tables} | "
            f"扫描 {self.scan_time:.1f}s, 发现 {self.discover_time:.1f}s, 总计 {self.total_time:.1f}s"
        )


class GraphBuilder:
    """
    图谱构建器（整合所有 Phase）

    使用策略模式组织关系发现，支持混乱数据
    """

    def __init__(self, config=None, progress_callback: Optional[Callable[[str, int, int], None]] = None):
        self.config = config or BuildConfig()
        self.logger = SimpleLogger()
        # E5: fn(phase_name, current, total)
        self.progress_callback = progress_callback

        # 初始化各 Phase
        self.discovery_strategies = [
            NamingConventionDiscovery(confidence=0.7),
            ContainmentDiscovery(
                containment_threshold=self.config.containment_threshold,
                overlap_threshold=0.8,
                min_sample_size=self.config.min_sample_size,
                small_pk_threshold=self.config.small_pk_threshold,
            ),
            AbbreviationDiscovery(
                confidence_threshold=self.config.abbrev_confidence_threshold
            ),
            TransitiveDiscovery()
        ]

        # 反馈管理
        self.feedback = FeedbackManager(
            feedback_file=self.config.feedback_file,
            auto_save_interval=self.config.auto_save_interval
        )

        # HTML 报告生成器
        self.html_generator = HTMLReportGenerator(
            output_dir=self.config.html_dir,
            offline=self.config.offline_html
        )

        # Scanner
        self._scanner = None

        self.logger.info(f"[Builder] 初始化完成，数据目录: {self.config.data_root}")

    def _get_scanner(self):
        if self._scanner is None:
            from indexer.scanner.directory_scanner import DirectoryScanner
            self._scanner = DirectoryScanner(
                data_root=self.config.data_root,
                max_sample_rows=self.config.max_sample_rows,
                max_workers=self.config.max_workers
            )
        return self._scanner

    def build_full_graph(self, incremental=False, existing_graph=None,
                         deleted_tables=None):
        total_start = time.time()
        result = BuildResult()
        graph = existing_graph or SchemaGraph()

        self.logger.info("=" * 60)
        self.logger.info("开始图谱构建" + ("（增量）" if incremental else "（全量）"))
        self.logger.info("=" * 60)

        # Phase 0: 处理删除
        if deleted_tables:
            for table_name in deleted_tables:
                if graph.remove_table(table_name):
                    result.deleted_tables += 1
                    self.logger.info(f"  删除表: {table_name}")

        # Phase 1: 扫描表结构
        scan_start = time.time()
        self.logger.info("\n[扫描] 扫描 Excel 文件...")
        scanner = self._get_scanner()
        scan_results = scanner.scan(
            existing_graph=graph if incremental else None)

        for table_schema in scan_results['new']:
            self._assign_domain_label(table_schema)
            graph.add_table(table_schema)
            result.new_tables += 1
        for table_schema in scan_results['updated']:
            graph.remove_table(table_schema.name)
            self._assign_domain_label(table_schema)
            graph.add_table(table_schema)
            result.updated_tables += 1

        # 补全存量表的 domain_label（从 JSON 加载的旧表可能缺失）
        for table in graph.tables.values():
            if not table.domain_label:
                self._assign_domain_label(table)

        result.scan_time = time.time() - scan_start
        self.logger.info(
            f"  扫描完成: {result.new_tables} 新增, "
            f"{result.updated_tables} 更新, {result.deleted_tables} 删除"
        )

        # Phase 2: 执行关系发现（P5: 并行执行独立策略）
        discover_start = time.time()
        self.logger.info("\n[关系发现] 执行所有策略...")
        if incremental and (result.new_tables > 0 or result.updated_tables > 0 or result.deleted_tables > 0):
            graph.relations.clear()

        # Transitive 依赖前面策略的结果，需要后执行
        independent = [s for s in self.discovery_strategies
                       if not isinstance(s, TransitiveDiscovery)]
        dependent = [s for s in self.discovery_strategies
                     if isinstance(s, TransitiveDiscovery)]

        # 并行执行独立策略
        with ThreadPoolExecutor(max_workers=len(independent) or 1) as pool:
            futures = {
                pool.submit(self._run_strategy, s, graph): s
                for s in independent
            }
            for i, future in enumerate(as_completed(futures)):
                rels = future.result()
                graph.relations.extend(rels)
                if self.progress_callback:
                    self.progress_callback(
                        "discovery", i + 1, len(self.discovery_strategies))

        # 串行执行依赖策略（transitive）
        for strategy in dependent:
            rels = self._run_strategy(strategy, graph)
            graph.relations.extend(rels)
        if self.progress_callback:
            self.progress_callback("discovery", len(self.discovery_strategies),
                                   len(self.discovery_strategies))

        # Phase 3: 应用反馈
        self.logger.info("\n[反馈] 应用历史反馈...")
        feedback_count = self.feedback.apply_to_graph(graph)
        self.logger.info(f"  应用 {feedback_count} 条反馈")

        # Phase 4: 去重 + 最低置信度过滤
        graph.relations = self._deduplicate_relations(graph.relations)
        graph.relations = [
            r for r in graph.relations
            if r.confidence >= self.config.min_relation_confidence
        ]
        graph.updated_at = datetime.now()

        result.table_count = len(graph.tables)
        result.relation_count = len(graph.relations)
        result.discover_time = time.time() - discover_start

        # Phase 5: 生成 HTML 报告
        try:
            self.html_generator.generate(graph, {
                'added': result.new_tables,
                'updated': result.updated_tables,
                'deleted': result.deleted_tables
            })
        except Exception as e:
            self.logger.warning(f"HTML 报告生成失败: {e}")

        result.total_time = time.time() - total_start
        self.logger.info(f"\n[完成] {result.summary()}")
        self.logger.info("=" * 60)

        return graph, result

    def enhance(self, graph):
        original_count = len(graph.relations)

        for strategy in self.discovery_strategies:
            rels = self._run_strategy(strategy, graph)
            graph.relations.extend(rels)

        self.feedback.apply_to_graph(graph)
        graph.relations = self._deduplicate_relations(graph.relations)
        graph.relations = [
            r for r in graph.relations
            if r.confidence >= self.config.min_relation_confidence
        ]

        final_count = len(graph.relations)
        self.logger.info(
            f"关系: {original_count} -> {final_count} (+{final_count - original_count})")
        return graph

    def save_feedback(self, confirmed=None, rejected=None):
        if confirmed:
            for ft, fc, tt, tc in confirmed:
                self.feedback.confirm(ft, fc, tt, tc)
        if rejected:
            for ft, fc, tt, tc in rejected:
                self.feedback.reject(ft, fc, tt, tc)

    def close(self):
        self.feedback.stop()

    def _run_strategy(self, strategy, graph):
        """运行单个发现策略（带异常隔离）"""
        try:
            return strategy.discover(graph)
        except Exception as e:
            self.logger.error(
                f"  策略 {strategy.__class__.__name__} 执行失败: {e}")
            return []

    # 业务域分类关键词（与 html_generator._get_group 保持一致）
    _DOMAIN_RULES = [
        ("hero",     ['hero', 'character', 'char_']),
        ("skill",    ['skill', 'ability', 'spell', 'buff', 'talent']),
        ("battle",   ['battle', 'fight', 'pvp', 'war', 'combat', 'army']),
        ("item",     ['item', 'equip', 'prop',
         'goods', 'material', 'resource']),
        ("building", ['building', 'construct', 'castle', 'city']),
        ("quest",    ['quest', 'task', 'mission', 'chapter', 'stage']),
        ("alliance", ['alliance', 'guild', 'union', 'clan', 'legion']),
        ("monster",  ['monster', 'enemy', 'npc', 'mob', 'boss', 'creature']),
        ("reward",   ['reward', 'drop', 'loot', 'prize', 'chest', 'gift']),
        ("world",    ['map', 'world', 'terrain', 'region', 'area', 'field']),
        ("social",   ['mail', 'chat', 'message', 'notice', 'friend']),
        ("config",   ['config', 'setting',
         'param', 'const', 'global', 'system']),
    ]

    def _assign_domain_label(self, table: TableSchema):
        """根据表名自动分配业务域标签"""
        name_lower = table.name.lower()
        for label, keywords in self._DOMAIN_RULES:
            if any(kw in name_lower for kw in keywords):
                table.domain_label = label
                return
        table.domain_label = "other"

    def _deduplicate_relations(self, relations):
        # Step 1: 每对列只保留最高置信度
        seen = {}
        for rel in relations:
            key = tuple(sorted([
                f"{rel.from_table}.{rel.from_column}",
                f"{rel.to_table}.{rel.to_column}"
            ]))
            if key in seen:
                if rel.confidence > seen[key].confidence:
                    seen[key] = rel
            else:
                seen[key] = rel

        # Step 2: 每对表之间只保留 top-N 关系（避免同类信号重复）
        _MAX_PER_TABLE_PAIR = 3
        from collections import defaultdict
        pair_buckets = defaultdict(list)
        for rel in seen.values():
            pair_key = tuple(sorted([rel.from_table, rel.to_table]))
            pair_buckets[pair_key].append(rel)

        result = []
        for rels in pair_buckets.values():
            rels.sort(key=lambda r: r.confidence, reverse=True)
            result.extend(rels[:_MAX_PER_TABLE_PAIR])
        return result


def create_builder(data_root="./data", **kwargs):
    config = BuildConfig(data_root=data_root, **kwargs)
    return GraphBuilder(config)


def enhance_graph(graph, **kwargs):
    builder = create_builder(**kwargs)
    enhanced = builder.enhance(graph)
    builder.close()
    return enhanced
