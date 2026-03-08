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
from typing import Optional, Set, Tuple, List

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

    def __init__(self, config=None):
        self.config = config or BuildConfig()
        self.logger = SimpleLogger()

        # 初始化各 Phase
        self.discovery_strategies = [
            NamingConventionDiscovery(confidence=0.7),
            ContainmentDiscovery(
                containment_threshold=self.config.containment_threshold,
                overlap_threshold=0.8,
                min_sample_size=self.config.min_sample_size
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
        scan_results = scanner.scan(existing_graph=graph if incremental else None)

        for table_schema in scan_results['new']:
            graph.add_table(table_schema)
            result.new_tables += 1
        for table_schema in scan_results['updated']:
            graph.remove_table(table_schema.name)
            graph.add_table(table_schema)
            result.updated_tables += 1

        result.scan_time = time.time() - scan_start
        self.logger.info(
            f"  扫描完成: {result.new_tables} 新增, "
            f"{result.updated_tables} 更新, {result.deleted_tables} 删除"
        )

        # Phase 2: 执行关系发现
        discover_start = time.time()
        self.logger.info("\n[关系发现] 执行所有策略...")
        if incremental and (result.new_tables > 0 or result.updated_tables > 0 or result.deleted_tables > 0):
            graph.relations.clear()

        for strategy in self.discovery_strategies:
            new_relations = strategy.discover(graph)
            graph.relations.extend(new_relations)

        # Phase 3: 应用反馈
        self.logger.info("\n[反馈] 应用历史反馈...")
        feedback_count = self.feedback.apply_to_graph(graph)
        self.logger.info(f"  应用 {feedback_count} 条反馈")

        # Phase 4: 去重
        graph.relations = self._deduplicate_relations(graph.relations)
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
            new_relations = strategy.discover(graph)
            graph.relations.extend(new_relations)

        self.feedback.apply_to_graph(graph)
        graph.relations = self._deduplicate_relations(graph.relations)

        final_count = len(graph.relations)
        self.logger.info(f"关系: {original_count} -> {final_count} (+{final_count - original_count})")
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

    def _deduplicate_relations(self, relations):
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
        return list(seen.values())


def create_builder(data_root="./data", **kwargs):
    config = BuildConfig(data_root=data_root, **kwargs)
    return GraphBuilder(config)


def enhance_graph(graph, **kwargs):
    builder = create_builder(**kwargs)
    enhanced = builder.enhance(graph)
    builder.close()
    return enhanced
