#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2: 缩写模式挖掘

从 GAME_ABBREVIATIONS 词典 + 已确认关系中学习缩写映射，如 sid -> skill。
不再依赖 naming_convention 先产出种子关系。
"""

import re
from typing import List, Optional, Dict, Set
from indexer.models import SchemaGraph, RelationEdge

from .base import RelationDiscoveryStrategy, build_relation_key
from .value_utils import normalize_value_set
from .game_dictionary import GAME_ABBREVIATIONS


class AbbreviationDiscovery(RelationDiscoveryStrategy):
    """缩写关系发现策略"""

    def __init__(self, confidence_threshold: float = 0.8):
        super().__init__()
        self.confidence_threshold = confidence_threshold
        self.patterns: Dict[str, Dict] = {}

    def discover(self, graph: SchemaGraph,
                 changed_tables: Optional[Set[str]] = None) -> List[RelationEdge]:
        """基于缩写词典 + 现有关系发现新关系。
        changed_tables 非 None 时只发现涉及变更表的关系。"""
        self._seed_from_dictionary(graph)
        self._mine_abbreviations(graph)

        if not self.patterns:
            return []

        rel_index = self._build_relation_index(graph)
        new_relations = []
        all_tables_set = set(graph.tables.keys())

        if changed_tables is not None:
            self.logger.info(
                f"[Phase 2] 增量模式: 只发现涉及 {len(changed_tables)} 个变更表的关系"
            )

        for table_name, table in graph.tables.items():
            for col in table.columns:
                clean_col = self._clean_column_name(col['name'])
                if clean_col not in self.patterns:
                    continue

                pattern = self.patterns[clean_col]
                target_table = pattern['full_name']

                if target_table not in all_tables_set or target_table == table_name:
                    continue

                # 增量模式：至少一端是变更表
                if changed_tables is not None:
                    if (table_name not in changed_tables and
                            target_table not in changed_tables):
                        continue

                target_pk = graph.tables[target_table].primary_key
                if not target_pk:
                    continue

                key = build_relation_key(
                    table_name, col['name'], target_table, target_pk)
                if key in rel_index:
                    continue

                if self._verify_match(table, col['name'],
                                      graph.tables[target_table], target_pk):
                    rel_index.add(key)
                    new_relations.append(RelationEdge(
                        from_table=table_name,
                        from_column=col['name'],
                        to_table=target_table,
                        to_column=target_pk,
                        relation_type='fk_abbreviation',
                        confidence=round(pattern['confidence'] * 0.8, 2),
                        discovery_method='abbreviation',
                        evidence=f"abbrev '{clean_col}' -> '{target_table}'",
                    ))

        self.logger.info(f"[Phase 2] 通过缩写发现 {len(new_relations)} 个新关系")
        return new_relations

    def _seed_from_dictionary(self, graph: SchemaGraph):
        """从 GAME_ABBREVIATIONS 静态词典中构建初始缩写模式（不依赖现有关系）"""
        table_lower_map = {n.lower(): n for n in graph.tables.keys()}

        for abbrev, full_list in GAME_ABBREVIATIONS.items():
            if len(abbrev) < 2 or len(abbrev) > 5:
                continue
            for full_name in full_list:
                # 精确匹配表名
                target = table_lower_map.get(full_name)
                if not target:
                    # 前缀匹配: skill → skill_base
                    for tname_lower, tname_real in table_lower_map.items():
                        if (tname_lower.startswith(full_name) and
                                (len(tname_lower) == len(full_name) or
                                 tname_lower[len(full_name)] == '_')):
                            target = tname_real
                            break
                if not target:
                    continue

                if abbrev not in self.patterns:
                    self.patterns[abbrev] = {
                        'full_name': target,
                        'confidence': 0.65,
                        'count': 0,
                        'source': 'dictionary',
                        'examples': []
                    }

        if self.patterns:
            self.logger.info(
                f"[Phase 2] 从词典加载 {len(self.patterns)} 个缩写种子")

    def _mine_abbreviations(self, graph: SchemaGraph):
        """从现有高置信度关系中挖掘额外缩写模式"""
        mined = 0
        for rel in graph.relations:
            if rel.confidence < self.confidence_threshold:
                continue

            abbrev = self._extract_abbreviation(rel.from_column, rel.to_table)
            if not abbrev:
                continue

            if abbrev not in self.patterns:
                self.patterns[abbrev] = {
                    'full_name': rel.to_table,
                    'confidence': 0.0,
                    'count': 0,
                    'source': 'mined',
                    'examples': []
                }
                mined += 1

            p = self.patterns[abbrev]
            p['count'] += 1
            p['examples'].append({
                'from_table': rel.from_table,
                'from_column': rel.from_column
            })

        # 更新置信度（mined patterns 和 dictionary patterns 均受益于出现次数）
        for p in self.patterns.values():
            if p['count'] > 0:
                base = 0.65 if p.get('source') == 'dictionary' else 0.50
                p['confidence'] = min(0.95, base + p['count'] * 0.1)
            # dictionary patterns without observed count keep their base confidence

        if mined > 0:
            self.logger.info(
                f"[Phase 2] 从关系中额外挖掘 {mined} 个缩写模式")

    def _extract_abbreviation(self, col_name: str, table_name: str) -> Optional[str]:
        """提取缩写"""
        clean_col = self._clean_column_name(col_name)
        table_lower = table_name.lower()

        if clean_col == table_lower:
            return None

        if 2 <= len(clean_col) <= 4:
            if self._is_abbreviation(clean_col, table_lower):
                return clean_col

        return None

    def _clean_column_name(self, col_name: str) -> str:
        """清理列名（去掉后缀）"""
        suffixes = ['_id', '_code', '_key', '_no', '_num', '_idx', '_ref', '_type']
        clean = col_name.lower()
        for suffix in suffixes:
            if clean.endswith(suffix):
                clean = clean[:-len(suffix)]
                break
        return clean

    def _is_abbreviation(self, abbrev: str, full: str) -> bool:
        """判断是否是子序列缩写"""
        if len(abbrev) > len(full):
            return False
        idx = 0
        for char in full:
            if idx < len(abbrev) and char == abbrev[idx]:
                idx += 1
        return idx == len(abbrev)

    def _verify_match(self, from_table, from_col, to_table, to_col) -> bool:
        """验证两列值域有足够交集"""
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
        containment = len(intersection) / len(from_values) if from_values else 0

        return containment >= 0.3
