#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2: 缩写模式挖掘

从已确认关系中学习缩写映射，如 sid -> skill
"""

import re
from typing import List, Optional, Dict
from indexer.models import SchemaGraph, RelationEdge

from .base import RelationDiscoveryStrategy, build_relation_key
from .value_utils import normalize_value_set


class AbbreviationDiscovery(RelationDiscoveryStrategy):
    """缩写关系发现策略"""

    def __init__(self, confidence_threshold: float = 0.8):
        super().__init__()
        self.confidence_threshold = confidence_threshold
        self.patterns: Dict[str, Dict] = {}

    def discover(self, graph: SchemaGraph) -> List[RelationEdge]:
        """基于缩写词典发现关系"""
        # 先从现有关系挖掘缩写
        self._mine_abbreviations(graph)

        if not self.patterns:
            return []

        # O(1) 关系查重
        rel_index = self._build_relation_index(graph)

        # 应用缩写发现新关系
        new_relations = []
        all_tables = list(graph.tables.keys())

        for table_name, table in graph.tables.items():
            for col in table.columns:
                # 提取列名缩写
                clean_col = self._clean_column_name(col['name'])
                if clean_col in self.patterns:
                    pattern = self.patterns[clean_col]
                    target_table = pattern['full_name']

                    if target_table in all_tables and target_table != table_name:
                        target_pk = graph.tables[target_table].primary_key
                        if target_pk:
                            key = build_relation_key(
                                table_name, col['name'],
                                target_table, target_pk)
                            if key in rel_index:
                                continue
                            # 验证内容匹配
                            if self._verify_match(table, col['name'],
                                                  graph.tables[target_table], target_pk):
                                rel_index.add(key)
                                new_relations.append(RelationEdge(
                                    from_table=table_name,
                                    from_column=col['name'],
                                    to_table=target_table,
                                    to_column=target_pk,
                                    relation_type='fk_abbreviation',
                                    confidence=round(
                                        pattern['confidence'] * 0.8, 2),
                                    discovery_method='abbreviation',
                                    evidence=f"abbrev '{clean_col}' -> '{target_table}'",
                                ))

        self.logger.info(f"[Phase 2] 通过缩写发现 {len(new_relations)} 个新关系")
        return new_relations

    def _mine_abbreviations(self, graph: SchemaGraph):
        """从现有关系挖掘缩写模式"""
        for rel in graph.relations:
            if rel.confidence < self.confidence_threshold:
                continue

            abbrev = self._extract_abbreviation(rel.from_column, rel.to_table)
            if abbrev:
                if abbrev not in self.patterns:
                    self.patterns[abbrev] = {
                        'full_name': rel.to_table,
                        'confidence': 0.0,
                        'count': 0,
                        'examples': []
                    }

                p = self.patterns[abbrev]
                p['count'] += 1
                p['examples'].append({
                    'from_table': rel.from_table,
                    'from_column': rel.from_column
                })

        # 计算置信度
        for p in self.patterns.values():
            p['confidence'] = min(0.95, 0.5 + p['count'] * 0.1)

        if self.patterns:
            self.logger.info(
                f"[Phase 2] 挖掘到 {len(self.patterns)} 个缩写模式: {list(self.patterns.keys())}")

    def _extract_abbreviation(self, col_name: str, table_name: str) -> Optional[str]:
        """提取缩写"""
        clean_col = self._clean_column_name(col_name)
        table_lower = table_name.lower()

        if clean_col == table_lower:
            return None

        # 检查首字母缩写 (sid -> skill)
        if len(clean_col) <= 4 and len(clean_col) >= 2:
            if self._is_abbreviation(clean_col, table_lower):
                return clean_col

        return None

    def _clean_column_name(self, col_name: str) -> str:
        """清理列名（去掉后缀）"""
        suffixes = ['_id', '_code', '_key', '_no', '_num']
        clean = col_name.lower()
        for suffix in suffixes:
            if clean.endswith(suffix):
                clean = clean[:-len(suffix)]
                break
        return clean

    def _is_abbreviation(self, abbrev: str, full: str) -> bool:
        """判断是否是首字母缩写"""
        if len(abbrev) > len(full):
            return False
        idx = 0
        for char in full:
            if idx < len(abbrev) and char == abbrev[idx]:
                idx += 1
        return idx == len(abbrev)

    def _verify_match(self, from_table, from_col, to_table, to_col) -> bool:
        """验证两列内容是否匹配"""
        from_col_data = next(
            (c for c in from_table.columns if c['name'] == from_col), None)
        to_col_data = next(
            (c for c in to_table.columns if c['name'] == to_col), None)

        if not from_col_data or not to_col_data:
            return False

        from_values = normalize_value_set(
            from_col_data.get('sample_values', []))
        to_values = normalize_value_set(
            to_col_data.get('sample_values', []))

        if not from_values or not to_values:
            return False

        intersection = from_values & to_values
        containment = len(intersection) / \
            len(from_values) if from_values else 0

        return containment >= 0.3
