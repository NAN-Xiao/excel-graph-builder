#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 1: 包含度检测

通过列内容相似度发现隐式外键关系。

优化点（相对初版）：
- 基于值→列的倒排索引做分桶，只比较共享值的列对，避免 O(C²) 全量比较
- 值统一标准化（1/1.0/"001" → "1"），解决跨表格式差异导致的漏召回
- int/float/str 跨类型匹配
- 噪声列过滤（name/desc/text 等非 ID 列）
- 宽表候选列限流
"""

import os
import re
from typing import List, Optional, Dict, Tuple, Set, FrozenSet
from collections import defaultdict

from indexer.models import SchemaGraph, TableSchema, RelationEdge
from .base import RelationDiscoveryStrategy, build_relation_key
from .value_utils import normalize_value, normalize_value_set, expand_compound_values


# 噪声列关键词——出现即排除（除非列名同时含 id/key/code）
_NOISE_KEYWORDS = frozenset([
    'name', 'desc', 'description', 'title', 'text', 'content',
    'remark', 'note', 'comment', 'icon', 'image', 'img', 'path',
    'url', 'file', 'sound', 'bgm', 'sfx', 'vfx', 'prefab',
    'ui', 'atlas', 'bundle', 'asset',
    # 中文等价词
    '名字', '名称', '描述', '说明', '标题', '备注', '文本', '内容',
    '图标', '图片', '路径', '文件', '音效', '特效', '动画', '资源名',
])

# ID 类关键词——出现则优先保留
_ID_KEYWORDS = frozenset([
    'id', 'key', 'code', 'index', 'idx', 'no', 'ref', 'type',
    '主键', '键值', '编号', '索引',
])

# 每张表最多参与包含度对比的候选列数
_MAX_CANDIDATES_PER_TABLE = 80

# 两列至少要有这么多交集值才判定匹配（防止小样本噪声）
_MIN_INTERSECTION = 5
# ID-like 列可放宽到此值
_MIN_INTERSECTION_ID_LIKE = 3

# 复合值列名后缀——含此后缀时优先展开复合值
_COMPOUND_SUFFIXES = frozenset([
    '_list', '_group', '_ids', '_items', '_rewards', '_costs',
    '_arr', '_array', 'list', 'group',
])

# 通用列名——纯位置/标号列，与其他列名匹配时需降权
_GENERIC_COL_NAMES = frozenset([
    '主键', '键值', '等级', '编号', '索引', '自增id', '序号', '排序',
    '优先级', '权重', '排序值', '显示顺序',
    'id', 'key', 'index', 'idx', 'no', 'level', 'lv', 'order', 'sort',
])


class ContainmentDiscovery(RelationDiscoveryStrategy):
    """包含度关系发现策略"""

    def __init__(self, containment_threshold: float = 0.85,
                 overlap_threshold: float = 0.8,
                 min_sample_size: int = 3,
                 small_pk_threshold: int = 100):
        super().__init__()
        self.containment_threshold = containment_threshold
        self.overlap_threshold = overlap_threshold
        self.min_sample_size = min_sample_size
        self.small_pk_threshold = small_pk_threshold

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def discover(self, graph: SchemaGraph,
                 changed_tables: Optional[Set[str]] = None) -> List[RelationEdge]:
        """发现基于包含度的关系。
        changed_tables 非 None 时只检查涉及这些表的列对（增量模式）。"""
        tables = list(graph.tables.values())
        if len(tables) < 2:
            return []

        rel_index = self._build_relation_index(graph)

        # 1. 收集候选列 & 标准化值（始终收集全部表，用于交叉匹配）
        candidate_columns = self._collect_candidates(tables)
        self.logger.info(f"[Phase 1] 找到 {len(candidate_columns)} 个候选键列")

        # 增量模式：标记哪些候选列属于变更表
        changed_col_indices: Optional[FrozenSet[int]] = None
        if changed_tables is not None:
            changed_col_indices = frozenset(
                idx for idx, c in enumerate(candidate_columns)
                if c['table'] in changed_tables
            )
            self.logger.info(
                f"[Phase 1] 增量模式: {len(changed_tables)} 个变更表, "
                f"{len(changed_col_indices)} 个候选列需检查"
            )

        # 2. 构建倒排索引：value → [col_info_index, ...]
        inverted = defaultdict(list)
        for idx, col_info in enumerate(candidate_columns):
            for v in col_info['values']:
                inverted[v].append(idx)

        # 3. 基于倒排索引找到共享值的列对
        pair_shared: Dict[Tuple[int, int], int] = defaultdict(int)
        for indices in inverted.values():
            if len(indices) > 200:
                continue
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    a, b = indices[i], indices[j]
                    if a > b:
                        a, b = b, a
                    # 增量模式：跳过两端都不是变更表的列对
                    if changed_col_indices is not None:
                        if a not in changed_col_indices and b not in changed_col_indices:
                            continue
                    pair_shared[(a, b)] += 1

        self.logger.info(
            f"[Phase 1] 倒排索引产生 {len(pair_shared)} 个候选列对"
            f"（从 {len(candidate_columns)}C2={len(candidate_columns)*(len(candidate_columns)-1)//2} 剪枝）"
        )

        # 4. 对候选列对做精确包含度计算
        relations = []
        for (i, j), shared_count in pair_shared.items():
            col_a = candidate_columns[i]
            col_b = candidate_columns[j]

            # 动态交集阈值: ID-like 列可放宽
            min_isect = _MIN_INTERSECTION
            if col_a.get('is_id_like') or col_b.get('is_id_like'):
                min_isect = _MIN_INTERSECTION_ID_LIKE
            if shared_count < min_isect:
                continue

            if col_a['table'] == col_b['table']:
                continue

            # 自适应包含度阈值: ID-like 列对 PK 的引用可降低
            effective_threshold = self.containment_threshold
            if ((col_a.get('is_id_like') and col_b.get('is_pk')) or
                    (col_b.get('is_id_like') and col_a.get('is_pk'))):
                effective_threshold = min(effective_threshold, 0.70)

            result = self._calc_containment(col_a, col_b, effective_threshold)
            if not result['is_match']:
                continue

            # 小整数范围 / 通用列名降权
            result['confidence'] = self._adjust_confidence(
                col_a, col_b, result['confidence'])
            if result['confidence'] < 0.30:
                continue

            from_col, to_col = self._determine_direction(col_a, col_b, result)
            if not from_col or not to_col:
                continue

            key = build_relation_key(
                from_col['table'], from_col['column'],
                to_col['table'], to_col['column'])
            if key in rel_index:
                continue
            rel_index.add(key)

            # 生成证据摘要：共享值样本
            shared_sample = list(from_col['values'] & to_col['values'])[:5]
            evidence_str = f"shared({len(from_col['values'] & to_col['values'])}): {','.join(shared_sample)}"

            relations.append(RelationEdge(
                from_table=from_col['table'],
                from_column=from_col['column'],
                to_table=to_col['table'],
                to_column=to_col['column'],
                relation_type=result['match_type'],
                confidence=round(result['confidence'], 2),
                discovery_method='containment',
                evidence=evidence_str,
            ))

        self.logger.info(f"[Phase 1] 发现 {len(relations)} 个新关系")
        return relations

    # ------------------------------------------------------------------
    # 候选列收集
    # ------------------------------------------------------------------

    def _collect_candidates(self, tables: list) -> list:
        """收集并限流所有候选列"""
        candidate_columns = []
        for table in tables:
            table_candidates = []
            for col in table.columns:
                col_info = self._analyze_column(table, col)
                if col_info and col_info['is_candidate']:
                    table_candidates.append(col_info)

            # 宽表限流：优先保留 ID 类列
            table_candidates.sort(
                key=lambda c: (c['priority'], c['unique_ratio']),
                reverse=True
            )
            candidate_columns.extend(
                table_candidates[:_MAX_CANDIDATES_PER_TABLE]
            )
        return candidate_columns

    def _analyze_column(self, table: TableSchema, col: dict) -> Optional[Dict]:
        """分析列是否适合匹配"""
        sample_values = col.get('sample_values', [])
        if len(sample_values) < self.min_sample_size:
            return None

        col_name = col['name']
        col_lower = col_name.lower()

        # 噪声列过滤
        if self._is_noise_column(col_lower):
            return None

        # R4: 列名含复合后缀时展开 "101|102|103" 式的复合值
        is_compound = any(col_lower.endswith(s) for s in _COMPOUND_SUFFIXES)
        if is_compound:
            normalized = expand_compound_values(sample_values)
        else:
            normalized = normalize_value_set(sample_values)
        if len(normalized) < self.min_sample_size:
            return None

        unique_count = len(normalized)
        unique_ratio = unique_count / \
            len(sample_values) if sample_values else 0

        is_id_like = any(k in col_lower for k in _ID_KEYWORDS)
        is_candidate = (0.3 <= unique_ratio <= 1.0) or is_id_like

        if not is_candidate:
            return None

        # 标记是否为该表主键
        is_pk = (table.primary_key is not None and col_name == table.primary_key)

        # 优先级打分（用于宽表限流排序）
        priority = 0
        if is_id_like:
            priority += 3
        if unique_ratio >= 0.95:
            priority += 2
        elif unique_ratio >= 0.8:
            priority += 1

        numeric_values = []
        for v in normalized:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                pass

        return {
            'table': table.name,
            'column': col_name,
            'dtype': col.get('dtype', 'unknown'),
            'values': normalized,
            'row_count': table.row_count,
            'unique_count': unique_count,
            'unique_ratio': unique_ratio,
            'is_candidate': True,
            'is_id_like': is_id_like,
            'is_pk': is_pk,
            'priority': priority,
            'min_val': min(numeric_values) if numeric_values else None,
            'max_val': max(numeric_values) if numeric_values else None,
        }

    @staticmethod
    def _is_noise_column(col_lower: str) -> bool:
        """判断列是否为噪声列（不太可能是外键）"""
        has_noise = any(k in col_lower for k in _NOISE_KEYWORDS)
        if not has_noise:
            return False
        # 如果同时含 id/key/code 等，仍保留
        has_id = any(k in col_lower for k in _ID_KEYWORDS)
        return not has_id

    # ------------------------------------------------------------------
    # 置信度校准
    # ------------------------------------------------------------------

    def _adjust_confidence(self, col_a: Dict, col_b: Dict,
                           base_conf: float) -> float:
        """校准置信度：类型兼容性、小整数碰撞、通用列名、PK 巧合匹配"""
        conf = base_conf
        has_naming = self._has_naming_evidence(col_a, col_b)

        # 类型兼容性检查
        dtype_a = col_a.get('dtype', 'unknown')
        dtype_b = col_b.get('dtype', 'unknown')
        if dtype_a == dtype_b and dtype_a != 'unknown':
            conf += 0.05
        elif not self._dtypes_compatible(dtype_a, dtype_b):
            if not (col_a.get('is_id_like') or col_b.get('is_id_like')):
                conf -= 0.15

        a_small = self._is_small_int_range(col_a)
        b_small = self._is_small_int_range(col_b)

        # 惩罚1：双方都是小密集整数范围（乘法惩罚）
        if a_small and b_small:
            if not has_naming:
                # 双方值域 < 50 且无命名证据 → 极高碰撞风险
                a_span = (col_a.get('max_val', 0) - col_a.get('min_val', 0))
                b_span = (col_b.get('max_val', 0) - col_b.get('min_val', 0))
                if a_span < 50 and b_span < 50:
                    conf *= 0.30
                else:
                    conf *= 0.50
            else:
                conf -= 0.10

        # 惩罚2：连续自然数序列检测（1,2,...,N）
        if self._is_consecutive_sequence(col_a) or self._is_consecutive_sequence(col_b):
            if not has_naming:
                conf *= 0.60

        # 惩罚3：通用列名
        if (self._is_generic_name(col_a['column']) and
                self._is_generic_name(col_b['column'])):
            conf *= 0.80

        # 惩罚4：PK 碰撞
        a_is_small_pk = col_a.get('is_pk') and col_a['unique_count'] < self.small_pk_threshold
        b_is_small_pk = col_b.get('is_pk') and col_b['unique_count'] < self.small_pk_threshold
        if a_is_small_pk and b_is_small_pk:
            conf *= 0.25
        elif a_is_small_pk or b_is_small_pk:
            # 一方是小 PK：要求命名证据，否则大幅降权
            if not has_naming:
                small_pk = col_a if a_is_small_pk else col_b
                if small_pk['unique_count'] < 30:
                    conf *= 0.40
                else:
                    conf *= 0.60

        # 加分：列名包含对方表名 → 强 FK 信号
        if has_naming:
            conf = min(conf + 0.10, base_conf + 0.05)

        return round(max(0.05, conf), 2)

    @staticmethod
    def _is_small_int_range(col_info: Dict) -> bool:
        """列值是否为小密集整数范围（易产生巧合包含）"""
        min_v = col_info.get('min_val')
        max_v = col_info.get('max_val')
        if min_v is None or max_v is None:
            return False
        span = max_v - min_v
        unique = col_info['unique_count']
        return (0 < span < 300 and 0 < unique < 200
                and max_v < 1000 and (unique / span) > 0.3)

    @staticmethod
    def _is_consecutive_sequence(col_info: Dict) -> bool:
        """检测值域是否为近似连续自然数序列 (1,2,3,...,N)"""
        min_v = col_info.get('min_val')
        max_v = col_info.get('max_val')
        if min_v is None or max_v is None:
            return False
        unique = col_info['unique_count']
        span = max_v - min_v
        if span <= 0 or unique < 3:
            return False
        # unique 值几乎填满整个 span → 连续序列
        density = unique / (span + 1)
        return density > 0.85 and min_v >= 0 and max_v < 200

    @staticmethod
    def _dtypes_compatible(dtype_a: str, dtype_b: str) -> bool:
        """检查两列类型是否兼容（用于 FK 匹配）"""
        if dtype_a == dtype_b:
            return True
        numeric = {'int', 'float'}
        if dtype_a in numeric and dtype_b in numeric:
            return True
        # str vs int/float 不兼容（str 列不应匹配 int PK）
        return False

    @staticmethod
    def _is_generic_name(col_name: str) -> bool:
        """列名是否为通用标号列（无表级语义）"""
        return col_name.lower().strip() in _GENERIC_COL_NAMES

    @staticmethod
    def _has_naming_evidence(col_a: Dict, col_b: Dict) -> bool:
        """列名是否包含对方表名片段 → FK 命名证据"""
        a_col = col_a['column'].lower()
        b_col = col_b['column'].lower()

        def _segments(table_name: str):
            return {p for p in table_name.lower().split('_') if len(p) >= 3}

        for seg in _segments(col_b['table']):
            if seg in a_col:
                return True
        for seg in _segments(col_a['table']):
            if seg in b_col:
                return True
        return False

    # ------------------------------------------------------------------
    # 包含度计算
    # ------------------------------------------------------------------

    def _calc_containment(self, col_a: Dict, col_b: Dict,
                          containment_threshold: float = None) -> Dict:
        """计算包含度"""
        if containment_threshold is None:
            containment_threshold = self.containment_threshold

        values_a = col_a['values']
        values_b = col_b['values']

        result = {
            'is_match': False, 'confidence': 0.0, 'match_type': '',
            'direction': '', 'containment_a': 0.0, 'containment_b': 0.0,
            'jaccard': 0.0,
        }

        if not values_a or not values_b:
            return result

        intersection = values_a & values_b
        if len(intersection) < _MIN_INTERSECTION_ID_LIKE:
            return result

        union_size = len(values_a | values_b)
        result['jaccard'] = len(intersection) / union_size if union_size else 0
        result['containment_a'] = len(
            intersection) / len(values_a) if values_a else 0
        result['containment_b'] = len(
            intersection) / len(values_b) if values_b else 0

        id_bonus = 0.05 if (col_a.get('is_id_like')
                            and col_b.get('is_id_like')) else 0

        # A 是 B 的子集
        if (result['containment_a'] >= containment_threshold and
                len(values_a) <= len(values_b) * 0.95):
            result['is_match'] = True
            result['match_type'] = 'fk_content_subset'
            result['direction'] = 'a_to_b'
            size_ratio = min(len(values_a) / len(values_b),
                             1.0) if values_b else 0
            result['confidence'] = (
                result['containment_a'] * 0.7 +
                result['jaccard'] * 0.2 +
                size_ratio * 0.1 +
                id_bonus
            )

        # B 是 A 的子集
        elif (result['containment_b'] >= containment_threshold and
              len(values_b) <= len(values_a) * 0.95):
            result['is_match'] = True
            result['match_type'] = 'fk_content_subset'
            result['direction'] = 'b_to_a'
            size_ratio = min(len(values_b) / len(values_a),
                             1.0) if values_a else 0
            result['confidence'] = (
                result['containment_b'] * 0.7 +
                result['jaccard'] * 0.2 +
                size_ratio * 0.1 +
                id_bonus
            )

        # 高度重合
        elif result['jaccard'] >= self.overlap_threshold:
            result['is_match'] = True
            result['match_type'] = 'fk_content_overlap'
            result['direction'] = 'unknown'
            result['confidence'] = result['jaccard'] * 0.8 + id_bonus

        return result

    def _determine_direction(self, col_a: Dict, col_b: Dict, result: Dict) -> Tuple:
        """确定外键方向"""
        if result['direction'] == 'a_to_b':
            return col_a, col_b
        elif result['direction'] == 'b_to_a':
            return col_b, col_a

        a_is_pk = col_a['unique_count'] >= col_a['row_count'] * 0.95
        b_is_pk = col_b['unique_count'] >= col_b['row_count'] * 0.95

        if a_is_pk and not b_is_pk:
            return col_b, col_a
        elif b_is_pk and not a_is_pk:
            return col_a, col_b

        if col_a['row_count'] > col_b['row_count'] * 1.2:
            return col_b, col_a
        elif col_b['row_count'] > col_a['row_count'] * 1.2:
            return col_a, col_b

        return None, None
