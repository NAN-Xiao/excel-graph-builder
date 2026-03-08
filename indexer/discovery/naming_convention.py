#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 5: 命名约定关系发现

游戏配置表最常见的关联模式：
- hero_id 列 → hero 表的 id/pk 列
- skill_type → skill 表
- reward_item_id → item 表

增强：
- 接入 game_dictionary 做缩写扩展（sid → skill）
- 补齐 _type/_idx/_ref/_list/_group 等后缀
- 值标准化后再做交集验证
"""

import re
from typing import List, Dict, Optional, Tuple

from indexer.models import SchemaGraph, RelationEdge

from .base import RelationDiscoveryStrategy, build_relation_key
from .value_utils import normalize_value_set
from .game_dictionary import expand_column_name, extract_cn_entity_tables, build_cn_table_index


class NamingConventionDiscovery(RelationDiscoveryStrategy):
    """基于列命名约定发现外键关系"""

    # 常见外键后缀（按优先级），包括游戏配置常用的扩展后缀
    FK_SUFFIXES = [
        '_id', '_key', '_no', '_code', '_idx', '_ref',
        '_type', '_group', '_list', '_num', '_index',
        'Id', 'Key', 'No', 'Code', 'Idx', 'Ref',
        'Num', 'Index',
        '_ID', '_KEY', '_NO', '_CODE', '_IDX', '_REF',
        '_NUM', '_INDEX',
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
        rel_index = self._build_relation_index(graph)

        # 动态构建 CN→实际表名 的桥接索引（基于当前图谱的真实表名）
        cn_table_index = build_cn_table_index(list(table_names))

        for table_name, table in graph.tables.items():
            for col in table.columns:
                col_name = col['name']

                # 尝试从列名中提取引用的表名
                ref_info = self._extract_reference(
                    col_name, table_name_lower, cn_table_index)
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

                # O(1) 检查是否已有关系
                key = build_relation_key(table_name, col_name,
                                         ref_table_real_name, target_col)
                if key in rel_index:
                    continue
                rel_index.add(key)

                # 计算置信度
                confidence = self._calc_confidence(
                    col, target_table, target_col, graph)

                relations.append(RelationEdge(
                    from_table=table_name,
                    from_column=col_name,
                    to_table=ref_table_real_name,
                    to_column=target_col,
                    relation_type='fk_naming_convention',
                    confidence=round(confidence, 2),
                    discovery_method='naming_convention',
                    evidence=f"col '{col_name}' matches table '{ref_table_real_name}' (suffix={suffix})",
                ))

        self.logger.info(f"[Phase 5] 通过命名约定发现 {len(relations)} 个新关系")
        return relations

    def _extract_reference(self, col_name: str,
                           table_name_lower: Dict[str, str],
                           cn_table_index: Optional[Dict] = None,
                           ) -> Optional[Tuple[str, str, str]]:
        """
        从列名中提取引用的表名。

        增强：
        1. FK_SUFFIXES 匹配 + game_dictionary 缩写扩展
        2. 中文列名 → 英文表名桥接（via 动态 cn_table_index）

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

                # 通过游戏词典扩展（sid → skill, eid → event/equipment 等）
                expanded = expand_column_name(col_name)
                for candidate in expanded:
                    if candidate in table_name_lower and candidate != prefix:
                        return table_name_lower[candidate], candidate, suffix

                # 复合名尝试：reward_item_id → item 表
                parts = prefix.split('_')
                for i in range(len(parts)):
                    sub_name = '_'.join(parts[i:])
                    if sub_name in table_name_lower and len(sub_name) >= 2:
                        return table_name_lower[sub_name], sub_name, suffix
                    # 单层尝试
                    if parts[i] in table_name_lower and len(parts[i]) >= 3:
                        return table_name_lower[parts[i]], parts[i], suffix

        # 中文列名→英文表名桥接（使用动态索引，基于实际图谱表名）
        # "英雄主动技能ID" → 找"技能" → ['skill'] → 匹配 skill 表
        cn_tables = extract_cn_entity_tables(col_name, cn_table_index)
        if cn_tables:
            # 确定用什么后缀（检测原始列名是否以 ID/编号 等结尾）
            cn_suffix = ''
            for s in ('ID', 'Id', 'id', '编号', '编码', '序号', '索引'):
                if col_name.endswith(s):
                    cn_suffix = s
                    break
            if cn_suffix:
                for real_table_name in cn_tables:
                    # cn_table_index 返回的已经是实际表名，直接使用
                    if real_table_name in table_name_lower.values():
                        return real_table_name, real_table_name.lower(), cn_suffix

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
        2. 值域交集（标准化后）
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

        # 值域交集验证（标准化后比较）
        src_vals = normalize_value_set(
            source_col.get('sample_values', []))
        tgt_vals = normalize_value_set(
            target_col.get('sample_values', []))

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
