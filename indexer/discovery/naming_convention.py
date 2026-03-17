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
- 中文列名 → 英文表名桥接（含英文后缀如 _id）
- 前缀模糊匹配表名（skill → skill_base）
"""

import re
from typing import List, Dict, Optional, Tuple, Set

from indexer.models import SchemaGraph, RelationEdge

from .base import RelationDiscoveryStrategy, build_relation_key
from .value_utils import normalize_value_set
from .game_dictionary import expand_column_name, extract_cn_entity_tables, build_cn_table_index

_CN_CHAR_RE = re.compile(r'[\u4e00-\u9fff]')

# 中英文混合列名中的英文 FK 后缀（用于在中文列名上也能触发 CN 桥接）
_ALL_FK_SUFFIXES = (
    '_id', '_key', '_no', '_code', '_idx', '_ref',
    '_type', '_group', '_list', '_num', '_index',
    'ID', 'Id', 'id', '编号', '编码', '序号', '索引',
)


class NamingConventionDiscovery(RelationDiscoveryStrategy):
    """基于列命名约定发现外键关系"""

    FK_SUFFIXES = [
        '_id', '_key', '_no', '_code', '_idx', '_ref',
        '_type', '_group', '_list', '_num', '_index',
        'Id', 'Key', 'No', 'Code', 'Idx', 'Ref',
        'Num', 'Index',
        '_ID', '_KEY', '_NO', '_CODE', '_IDX', '_REF',
        '_NUM', '_INDEX',
    ]

    TARGET_PK_NAMES = ['id', 'ID', 'Id', 'key', 'Key', 'no', 'code', 'index']

    def __init__(self, confidence: float = 0.7):
        super().__init__()
        self.base_confidence = confidence

    def discover(self, graph: SchemaGraph,
                 changed_tables: Optional[Set[str]] = None) -> List[RelationEdge]:
        """基于命名约定发现关系。
        changed_tables 非 None 时只扫描变更表的列（但匹配目标仍为全部表）。"""
        table_names = set(graph.tables.keys())
        table_name_lower = {name.lower(): name for name in table_names}
        relations = []
        rel_index = self._build_relation_index(graph)

        cn_table_index = build_cn_table_index(list(table_names))

        prefix_table_index = self._build_prefix_table_index(table_names)

        # 增量模式：扫描全部表，但只保留至少一端是变更表的关系
        # （变更表的列可能引用其他表；其他表的列可能引用变更表）
        if changed_tables is not None:
            self.logger.info(
                f"[Phase 5] 增量模式: {len(changed_tables)} 个变更表, "
                f"只发现涉及变更表的关系"
            )

        for table_name, table in graph.tables.items():
            for col in table.columns:
                col_name = col['name']

                ref_info = self._extract_reference(
                    col_name, table_name_lower, cn_table_index,
                    prefix_table_index)
                if not ref_info:
                    continue

                ref_table_real_name, ref_prefix, suffix = ref_info

                if ref_table_real_name == table_name:
                    continue

                # 增量模式：至少一端是变更表才保留
                if changed_tables is not None:
                    if (table_name not in changed_tables and
                            ref_table_real_name not in changed_tables):
                        continue

                target_table = graph.tables[ref_table_real_name]
                target_col = self._find_target_column(target_table, ref_prefix)

                if not target_col:
                    continue

                key = build_relation_key(table_name, col_name,
                                         ref_table_real_name, target_col)
                if key in rel_index:
                    continue
                rel_index.add(key)

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

    @staticmethod
    def _build_prefix_table_index(table_names: Set[str]) -> Dict[str, str]:
        """
        构建 prefix → 最短实际表名 索引，用于模糊匹配。
        例: 'skill' → 'skill' (如果存在), 否则 'skill' → 'skill_base' (最短前缀匹配)
        """
        index: Dict[str, List[str]] = {}
        for name in table_names:
            parts = name.lower().split('_')
            # 用第一个有意义的词段作为 prefix key
            if parts:
                stem = parts[0]
                if len(stem) >= 3:
                    index.setdefault(stem, []).append(name)
        # 每个 stem 保留最短表名（更可能是基础实体表）
        result: Dict[str, str] = {}
        for stem, names in index.items():
            names.sort(key=len)
            result[stem] = names[0]
        return result

    def _extract_reference(self, col_name: str,
                           table_name_lower: Dict[str, str],
                           cn_table_index: Optional[Dict] = None,
                           prefix_table_index: Optional[Dict[str, str]] = None,
                           ) -> Optional[Tuple[str, str, str]]:
        """
        从列名中提取引用的表名。

        策略优先级:
        1. FK_SUFFIXES + 精确表名匹配
        2. FK_SUFFIXES + game_dictionary 缩写扩展
        3. FK_SUFFIXES + 复合名拆分
        4. FK_SUFFIXES + prefix 模糊匹配（skill → skill_base）
        5. 中文列名 CN 桥接（支持中英文混合后缀）
        """
        col_lower = col_name.lower()
        has_cn = bool(_CN_CHAR_RE.search(col_name))

        for suffix in self.FK_SUFFIXES:
            suffix_lower = suffix.lower()
            if col_lower.endswith(suffix_lower) and len(col_lower) > len(suffix_lower):
                prefix = col_lower[:-len(suffix_lower)]

                # 1. 精确匹配表名
                if prefix in table_name_lower:
                    return table_name_lower[prefix], prefix, suffix

                # 2. 游戏词典缩写扩展
                expanded = expand_column_name(col_name)
                for candidate in expanded:
                    if candidate in table_name_lower and candidate != prefix:
                        return table_name_lower[candidate], candidate, suffix

                # 3. 复合名拆分: reward_item_id → item
                parts = prefix.split('_')
                for i in range(len(parts)):
                    sub_name = '_'.join(parts[i:])
                    if sub_name in table_name_lower and len(sub_name) >= 2:
                        return table_name_lower[sub_name], sub_name, suffix
                    if parts[i] in table_name_lower and len(parts[i]) >= 3:
                        return table_name_lower[parts[i]], parts[i], suffix

                # 4. prefix 模糊匹配: skill → skill_base
                if prefix_table_index and not has_cn:
                    last_part = parts[-1] if parts else prefix
                    if last_part in prefix_table_index and len(last_part) >= 3:
                        real_name = prefix_table_index[last_part]
                        if real_name.lower() != prefix:
                            return real_name, last_part, suffix

        # 5. 中文列名→英文表名桥接（扩展: 支持 _id 等英文后缀 + 中文后缀）
        if has_cn:
            result = self._try_cn_bridge(col_name, cn_table_index, table_name_lower)
            if result:
                return result

        return None

    @staticmethod
    def _try_cn_bridge(col_name: str,
                       cn_table_index: Optional[Dict],
                       table_name_lower: Dict[str, str],
                       ) -> Optional[Tuple[str, str, str]]:
        """
        中文列名 → 英文表名桥接。
        支持中文后缀 (编号/ID) 和英文后缀 (_id/_key) 混合情况。
        """
        cn_suffix = ''
        for s in _ALL_FK_SUFFIXES:
            if col_name.endswith(s):
                cn_suffix = s
                break

        if not cn_suffix:
            return None

        cn_tables = extract_cn_entity_tables(col_name, cn_table_index)
        if cn_tables:
            for real_table_name in cn_tables:
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
