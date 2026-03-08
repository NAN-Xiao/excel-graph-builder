#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 5: 命名约定关系发现

游戏配置表最常见的关联模式：
- hero_id 列 → hero 表的 id/pk 列
- skill_type → skill 表
- reward_item_id → item 表
"""

import re
from typing import List, Dict, Optional, Tuple

from indexer.models import SchemaGraph, RelationEdge

from .base import RelationDiscoveryStrategy


class NamingConventionDiscovery(RelationDiscoveryStrategy):
    """基于列命名约定发现外键关系"""

    # 常见外键后缀（按优先级）
    FK_SUFFIXES = [
        '_id', '_key', '_no', '_code',
        'Id', 'Key', 'No', 'Code',
        '_ID', '_KEY', '_NO', '_CODE',
    ]

    # 常见引用列名（在目标表中查找）
    TARGET_PK_NAMES = ['id', 'ID', 'Id', 'key', 'Key', 'no', 'code', 'index']

    def __init__(self, confidence: float = 0.7):
        super().__init__()
        self.base_confidence = confidence

    def discover(self, graph: SchemaGraph) -> List[RelationEdge]:
        """基于命名约定发现关系"""
        table_names = set(graph.tables.keys())
        table_name_lower = {name.lower(): name for name in table_names}
        relations = []

        for table_name, table in graph.tables.items():
            for col in table.columns:
                col_name = col['name']

                # 尝试从列名中提取引用的表名
                ref_info = self._extract_reference(col_name, table_name_lower)
                if not ref_info:
                    continue

                ref_table_real_name, ref_prefix, suffix = ref_info

                # 不要自引用
                if ref_table_real_name == table_name:
                    continue

                # 在目标表中找主键或同名列
                target_table = graph.tables[ref_table_real_name]
                target_col = self._find_target_column(target_table, ref_prefix)

                if not target_col:
                    continue

                # 检查是否已有关系
                if self._relation_exists(graph, table_name, col_name,
                                         ref_table_real_name, target_col):
                    continue

                # 计算置信度
                confidence = self._calc_confidence(
                    col, target_table, target_col, graph)

                relations.append(RelationEdge(
                    from_table=table_name,
                    from_column=col_name,
                    to_table=ref_table_real_name,
                    to_column=target_col,
                    relation_type='fk_naming_convention',
                    confidence=round(confidence, 2)
                ))

        self.logger.info(f"[Phase 5] 通过命名约定发现 {len(relations)} 个新关系")
        return relations

    def _extract_reference(self, col_name: str,
                           table_name_lower: Dict[str, str]
                           ) -> Optional[Tuple[str, str, str]]:
        """
        从列名中提取引用的表名。

        Returns:
            (real_table_name, prefix, suffix) 或 None
        """
        col_lower = col_name.lower()

        for suffix in self.FK_SUFFIXES:
            suffix_lower = suffix.lower()
            if col_lower.endswith(suffix_lower) and len(col_lower) > len(suffix_lower):
                prefix = col_lower[:-len(suffix_lower)]

                # 直接匹配表名
                if prefix in table_name_lower:
                    return table_name_lower[prefix], prefix, suffix

                # 复合名尝试：reward_item_id → item 表
                parts = prefix.split('_')
                for i in range(len(parts)):
                    sub_name = '_'.join(parts[i:])
                    if sub_name in table_name_lower and len(sub_name) >= 2:
                        return table_name_lower[sub_name], sub_name, suffix
                    # 单层尝试
                    if parts[i] in table_name_lower and len(parts[i]) >= 3:
                        return table_name_lower[parts[i]], parts[i], suffix

        return None

    def _find_target_column(self, target_table, ref_prefix: str) -> Optional[str]:
        """在目标表中找对应的主键/ID列"""
        # 优先用已推断的主键
        if target_table.primary_key:
            return target_table.primary_key

        # 按常见名字查找
        col_names = {c['name'].lower(): c['name']
                     for c in target_table.columns}

        for pk_name in self.TARGET_PK_NAMES:
            if pk_name.lower() in col_names:
                return col_names[pk_name.lower()]

        return None

    def _calc_confidence(self, source_col: Dict, target_table,
                         target_col_name: str, graph: SchemaGraph) -> float:
        """
        计算关系置信度，综合考虑：
        1. 数据类型匹配
        2. 值域交集
        3. 命名精确度
        """
        confidence = self.base_confidence

        # 找到目标列数据
        target_col = next(
            (c for c in target_table.columns if c['name']
             == target_col_name), None
        )
        if not target_col:
            return confidence

        # 类型匹配加分
        if source_col.get('dtype') == target_col.get('dtype'):
            confidence += 0.1

        # 值域交集验证
        src_vals = set(str(v) for v in source_col.get(
            'sample_values', []) if v is not None)
        tgt_vals = set(str(v) for v in target_col.get(
            'sample_values', []) if v is not None)

        if src_vals and tgt_vals:
            intersection = src_vals & tgt_vals
            if src_vals:
                containment = len(intersection) / len(src_vals)
                if containment >= 0.5:
                    confidence += 0.15
                elif containment >= 0.2:
                    confidence += 0.05
                elif containment == 0:
                    confidence -= 0.2  # 完全不交集，降低置信度

        return min(0.95, max(0.1, confidence))
