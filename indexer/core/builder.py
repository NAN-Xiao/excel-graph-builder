#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图谱构建器 - 流程编排

整合所有 Phase，提供统一的构建接口
"""

import os
import time
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, Tuple, List, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from indexer.models import SchemaGraph, TableSchema, RelationEdge, ChangeRecord
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
    PackArrayDiscovery,
    FeedbackManager,
    classify_domain,
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
    analysis: Optional[object] = None  # AnalysisResult (避免循环导入用 object)
    # pack_array 弱信号候选：不进入主关系图，只供导出到 pack_array_candidates.json
    pack_array_candidates: List[RelationEdge] = field(default_factory=list)

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
            # Pack 数组策略：发现 "101|102|103" 类字符串列的隐式 FK
            PackArrayDiscovery(),
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
                max_workers=self.config.max_workers,
                # max_rows_per_table=None 表示读全量；设置上限仅用于内存受限场景
                max_read_rows=self.config.max_rows_per_table or None,
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

        now_iso = datetime.now().isoformat(timespec='seconds')

        # Phase 1: 扫描表结构
        scan_start = time.time()
        self.logger.info("\n[扫描] 扫描 Excel 文件...")
        scanner = self._get_scanner()
        scan_results = scanner.scan(
            existing_graph=graph if incremental else None)

        # Phase 0: 处理删除（合并外部传入 + 扫描器自动检测）
        all_deleted: Set[str] = set(deleted_tables or [])
        all_deleted.update(scan_results.get('deleted', []))
        for table_name in all_deleted:
            if graph.remove_table(table_name):
                result.deleted_tables += 1
                self.logger.info(f"  删除表: {table_name}")
                graph.changelog.append(ChangeRecord(
                    timestamp=now_iso, table_name=table_name,
                    change_type="table_removed", details="表被删除"))

        # 收集受影响的表名（增量关系发现用）
        affected_tables: Set[str] = set(all_deleted)

        for table_schema in scan_results['new']:
            self._assign_domain_label(table_schema)
            graph.add_table(table_schema)
            result.new_tables += 1
            affected_tables.add(table_schema.name)
            graph.changelog.append(ChangeRecord(
                timestamp=now_iso, table_name=table_schema.name,
                change_type="table_added",
                details=f"新增表 ({len(table_schema.columns)} 列, {table_schema.row_count} 行)"))

        for table_schema in scan_results['updated']:
            old_table = graph.tables.get(table_schema.name)
            if old_table:
                changes = self._diff_columns(old_table, table_schema)
                for ch in changes:
                    graph.changelog.append(ChangeRecord(
                        timestamp=now_iso, table_name=table_schema.name,
                        change_type=ch[0], details=ch[1]))
            graph.remove_table(table_schema.name)
            self._assign_domain_label(table_schema)
            graph.add_table(table_schema)
            result.updated_tables += 1
            affected_tables.add(table_schema.name)

        for table in graph.tables.values():
            if not table.domain_label:
                self._assign_domain_label(table)

        result.scan_time = time.time() - scan_start
        self.logger.info(
            f"  扫描完成: {result.new_tables} 新增, "
            f"{result.updated_tables} 更新, {result.deleted_tables} 删除"
        )

        # Phase 2: 关系发现
        discover_start = time.time()
        self.logger.info("\n[关系发现] 执行所有策略...")

        # 增量模式的核心：只清除受影响表的关系，保留其余
        # 同时顺带清理旧图中可能残留的 pack_array 关系（迁移兼容）
        changed_tables: Optional[Set[str]] = None
        if incremental and affected_tables:
            before_count = len(graph.relations)
            graph.relations = [
                r for r in graph.relations
                if r.from_table not in affected_tables
                and r.to_table not in affected_tables
                and r.discovery_method != 'pack_array'   # 剥离残留 pack_array
            ]
            kept = len(graph.relations)
            self.logger.info(
                f"  增量模式: {len(affected_tables)} 个受影响表, "
                f"保留 {kept}/{before_count} 条关系, "
                f"只重新发现涉及变更表的关系"
            )
            changed_tables = affected_tables
        elif incremental and not affected_tables:
            # 无文件变更，但仍需剥离旧 pack_array 关系（首次升级时执行一次）
            old_pack = [r for r in graph.relations if r.discovery_method == 'pack_array']
            if old_pack:
                graph.relations = [r for r in graph.relations
                                   if r.discovery_method != 'pack_array']
                self.logger.info(
                    f"  [迁移] 从主图剥离 {len(old_pack)} 条旧 pack_array 关系")
                # 把它们放进候选集，避免信息丢失
                result.pack_array_candidates.extend(old_pack)

            self.logger.info("  无变更，跳过关系发现")
            result.discover_time = 0
            result.table_count = len(graph.tables)
            result.relation_count = len(graph.relations)
            result.total_time = time.time() - total_start
            return graph, result
        else:
            # 全量构建：清空主图里所有旧 pack_array 关系
            pack_residual = sum(1 for r in graph.relations
                                if r.discovery_method == 'pack_array')
            if pack_residual:
                graph.relations = [r for r in graph.relations
                                   if r.discovery_method != 'pack_array']
                self.logger.info(f"  [迁移] 清理旧 pack_array 关系 {pack_residual} 条")

        # 策略分组：
        #   independent — 可并行、不依赖其他策略输出（不含 pack_array / transitive）
        #   pack_strats — PackArrayDiscovery：结果只进候选集，不进主图
        #   dependent   — TransitiveDiscovery：依赖主图关系，串行最后执行
        independent = [s for s in self.discovery_strategies
                       if not isinstance(s, (TransitiveDiscovery, PackArrayDiscovery))]
        pack_strats = [s for s in self.discovery_strategies
                       if isinstance(s, PackArrayDiscovery)]
        dependent = [s for s in self.discovery_strategies
                     if isinstance(s, TransitiveDiscovery)]

        # 并行执行独立策略（传递 changed_tables）
        with ThreadPoolExecutor(max_workers=len(independent) or 1) as pool:
            futures = {
                pool.submit(self._run_strategy, s, graph, changed_tables): s
                for s in independent
            }
            for i, future in enumerate(as_completed(futures)):
                rels = future.result()
                graph.relations.extend(rels)
                if self.progress_callback:
                    self.progress_callback(
                        "discovery", i + 1, len(self.discovery_strategies))

        # 串行执行 pack_array 策略 — 结果不进主图，只进候选集
        for strategy in pack_strats:
            pack_rels = self._run_strategy(strategy, graph, changed_tables)
            result.pack_array_candidates.extend(pack_rels)
            self.logger.info(
                f"  [PackArray候选] 发现 {len(pack_rels)} 条候选弱信号"
                f"（不进主图，仅导出至 pack_array_candidates.json）"
            )

        # 串行执行依赖策略（transitive 在主图关系上运行，不含 pack_array）
        for strategy in dependent:
            rels = self._run_strategy(strategy, graph, changed_tables)
            graph.relations.extend(rels)
        if self.progress_callback:
            self.progress_callback("discovery", len(self.discovery_strategies),
                                   len(self.discovery_strategies))

        # Phase 3: 应用反馈
        self.logger.info("\n[反馈] 应用历史反馈...")
        feedback_count = self.feedback.apply_to_graph(graph)
        self.logger.info(f"  应用 {feedback_count} 条反馈")

        # Phase 4: 跨策略融合 + 去重 + 最低置信度过滤
        graph.relations = self._fuse_cross_strategy(graph.relations)
        graph.relations = self._deduplicate_relations(graph.relations)
        graph.relations = [
            r for r in graph.relations
            if r.confidence >= self.config.min_relation_confidence
        ]
        graph.updated_at = datetime.now()

        result.table_count = len(graph.tables)
        result.relation_count = len(graph.relations)
        result.discover_time = time.time() - discover_start

        # Phase 5: 图算法分析
        analysis = None
        if len(graph.tables) >= 2:
            try:
                analyzer = GraphAnalyzer(graph)
                analysis = analyzer.analyze()
                self.logger.info(
                    f"[分析] {len(analysis.cycles)} 环, "
                    f"{len(analysis.modules)} 模块, "
                    f"{len(analysis.orphans)} 孤立表"
                )
            except Exception as e:
                self.logger.warning(f"图谱分析失败: {e}")

        result.analysis = analysis

        # Phase 6: 生成 HTML 报告
        try:
            self.html_generator.generate(graph, {
                'added': result.new_tables,
                'updated': result.updated_tables,
                'deleted': result.deleted_tables
            }, analysis=analysis)
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

    def _run_strategy(self, strategy, graph, changed_tables=None):
        """运行单个发现策略（带异常隔离）"""
        try:
            return strategy.discover(graph, changed_tables=changed_tables)
        except Exception as e:
            self.logger.error(
                f"  策略 {strategy.__class__.__name__} 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def _assign_domain_label(table: TableSchema):
        """根据表名自动分配业务域标签（使用统一规则）"""
        table.domain_label = classify_domain(table.name)

    @staticmethod
    def _diff_columns(old_table: TableSchema,
                      new_table: TableSchema) -> List[Tuple[str, str]]:
        """
        比对新旧表的列差异，返回 [(change_type, details), ...] 列表。

        change_type: added_columns | removed_columns | type_changed
        """
        old_cols = {c['name']: c for c in old_table.columns}
        new_cols = {c['name']: c for c in new_table.columns}

        old_names = set(old_cols.keys())
        new_names = set(new_cols.keys())

        changes: List[Tuple[str, str]] = []

        added = new_names - old_names
        if added:
            changes.append(
                ("added_columns",
                 f"新增列: {', '.join(sorted(added))}"))

        removed = old_names - new_names
        if removed:
            changes.append(
                ("removed_columns",
                 f"删除列: {', '.join(sorted(removed))}"))

        # 类型变更
        type_changes = []
        for col_name in old_names & new_names:
            old_dtype = old_cols[col_name].get('dtype', '?')
            new_dtype = new_cols[col_name].get('dtype', '?')
            if old_dtype != new_dtype:
                type_changes.append(
                    f"{col_name}: {old_dtype}→{new_dtype}")
        if type_changes:
            changes.append(
                ("type_changed",
                 f"类型变更: {', '.join(type_changes)}"))

        return changes

    @staticmethod
    def _fuse_cross_strategy(relations):
        """
        跨策略置信度融合: 同一列对被多个策略发现时，
        使用 merged = 1 - prod(1 - conf_i) 提升置信度。
        保留置信度最高的那条关系记录，更新其置信度。
        """
        from collections import defaultdict
        col_pair_groups = defaultdict(list)
        for rel in relations:
            key = tuple(sorted([
                f"{rel.from_table}.{rel.from_column}",
                f"{rel.to_table}.{rel.to_column}"
            ]))
            col_pair_groups[key].append(rel)

        result = []
        for key, rels in col_pair_groups.items():
            methods = {r.discovery_method for r in rels}
            if len(methods) > 1:
                # 多策略印证: 融合置信度
                product = 1.0
                for r in rels:
                    product *= (1.0 - r.confidence)
                merged_conf = min(0.98, 1.0 - product)
                # 保留最高优先级的关系记录
                best = max(rels, key=lambda r: r.confidence)
                best.confidence = round(merged_conf, 2)
                best.evidence += f" [fused: {','.join(sorted(methods))}]"
                result.append(best)
            else:
                # 单策略: 保留最高置信度
                result.append(max(rels, key=lambda r: r.confidence))
        return result

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

        # Step 2: 每对表之间只保留 top-N 关系
        # pack_array 已从主图剥离，这里不会出现 pack_array 方法的关系
        _MAX_PER_TABLE_PAIR = 3
        _METHOD_PRIORITY = {
            'naming_convention': 3,
            'abbreviation': 2,
            'containment': 1,
            'transitive': 0,
        }
        from collections import defaultdict
        pair_buckets = defaultdict(list)
        for rel in seen.values():
            pair_key = tuple(sorted([rel.from_table, rel.to_table]))
            pair_buckets[pair_key].append(rel)

        result = []
        for rels in pair_buckets.values():
            rels.sort(key=lambda r: (
                _METHOD_PRIORITY.get(r.discovery_method, 0),
                r.confidence
            ), reverse=True)
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
