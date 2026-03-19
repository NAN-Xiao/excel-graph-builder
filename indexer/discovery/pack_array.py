#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pack 数组外键发现策略

扫描已标注 pack_info 的字符串列，将其中提取的元素值与其他表的 PK 值进行重叠比较，
发现形如 "10001|10002|10003" → skill_base.id 的隐式外键关系。

这类关系无法被命名约定或普通包含度策略发现，是游戏配置表中大量漏报的根源。
"""

from typing import List, Optional, Set, Dict, Tuple

from indexer.models import SchemaGraph, RelationEdge
from .base import RelationDiscoveryStrategy, build_relation_key
from .value_utils import normalize_value


# 最少共享元素数：pack 元素集与 PK 值集至少有这么多交集
_MIN_OVERLAP = 5

# 最小重叠率（交集/pack元素总数）：pack 中多少比例指向目标表
# 真实外键应有很高命中率（如 96%+ 的 pack 元素都是有效 PK 值）
# 提高到 0.80，过滤掉顺序整数巧合（通常只有 30-70% 的重叠率）
_MIN_OVERLAP_RATIO = 0.80

# 最大 PK 覆盖率（交集/PK样本总数）：
# 若 pack 元素覆盖了目标表很多 PK，说明是顺序整数巧合，非真实外键
# 真实引用：pack 中 50 个技能ID / skill_base 中 3000 个ID = 1.7% → 远低于阈值
_MAX_PK_COVERAGE_RATIO = 0.50

# pack 列唯一元素数上限：元素数量过多通常是基础设施数据（服务器编号等）
# 真实业务外键引用的实体数量一般不超过此值
_MAX_PACK_UNIQUE_ELEMENTS = 200

# 每个 pack 列最多关联的目标表数量
# 真实FK pack 列通常只指向 1-2 张表；指向 10+ 张表的列是假阳性
_MAX_TARGETS_PER_COL = 5

# 基础置信度（弱信号模式：降低上限，避免污染主关系图）
_BASE_CONFIDENCE = 0.60
_MAX_CONFIDENCE = 0.78   # 原 0.88，pack 列归为弱信号后降低上限

# 每张表最多参与比对的 pack 列数（避免超宽表爆炸）
_MAX_PACK_COLS_PER_TABLE = 50

# 噪声列名关键词：这些列语义上是基础设施数据，不应做业务 FK 推断
_NOISE_COL_KEYWORDS = frozenset([
    'server', 'serverid', 'block_server', 'blockserver', 'localserver',
    'serverlist', 'server_list', 'server_range', 'serverrange',
])

# ── 业务实体关键词白名单 ──────────────────────────────────────
# 只有列名（去掉 _ids/_list/_array 等后缀后）包含以下关键词之一，
# 才认为这是真实业务 FK 引用，纳入候选弱信号。
# 不匹配的 pack 列（如 serverList、configIds 等通用数据）直接跳过。
_BUSINESS_COL_KEYWORDS = frozenset([
    # 角色/英雄
    'hero', 'char', 'character', 'role', 'player',
    # 技能/天赋/法术
    'skill', 'ability', 'talent', 'spell', 'buff', 'debuff', 'effect',
    # 道具/装备
    'item', 'prop', 'equip', 'equipment', 'weapon', 'armor', 'gear', 'goods',
    # 怪物/NPC
    'monster', 'enemy', 'npc', 'mob', 'boss', 'creature',
    # 任务/关卡
    'quest', 'task', 'mission', 'stage', 'dungeon', 'chapter', 'instance',
    # 奖励/资源
    'reward', 'prize', 'loot', 'drop', 'resource', 'material',
    # 建筑/地图
    'building', 'construct', 'map', 'region', 'area', 'scene',
    # 社交/联盟
    'alliance', 'guild', 'team', 'friend',
    # 其他高频实体
    'card', 'pet', 'mount', 'skin', 'title', 'rune', 'artifact',
    'troop', 'army', 'soldier', 'unit',
    # 游戏缩写常见实体前缀
    'sid', 'tid', 'eid', 'mid', 'wid', 'rid', 'gid',
])


class PackArrayDiscovery(RelationDiscoveryStrategy):
    """
    Pack 数组外键发现策略

    两阶段：
    1. 构建 PK 值索引（int + str 各一份）
    2. 遍历所有 pack 列，用元素采样做重叠检测
    """

    def __init__(self,
                 min_overlap: int = _MIN_OVERLAP,
                 min_overlap_ratio: float = _MIN_OVERLAP_RATIO,
                 base_confidence: float = _BASE_CONFIDENCE):
        super().__init__()
        self.min_overlap = min_overlap
        self.min_overlap_ratio = min_overlap_ratio
        self.base_confidence = base_confidence

    def discover(self, graph: SchemaGraph,
                 changed_tables: Optional[Set[str]] = None) -> List[RelationEdge]:
        """
        发现 pack 数组列指向其他表 PK 的外键关系。

        增量模式：只扫描 changed_tables 中的 pack 列（PK 索引始终全量构建）。
        """
        if not graph.tables:
            return []

        # ── 构建 PK 值索引 ──
        # pk_int_index: table_name → (pk_col_name, frozenset of normalized int strings)
        # pk_str_index: table_name → (pk_col_name, frozenset of normalized str values)
        pk_int_index: Dict[str, Tuple[str, Set[str]]] = {}
        pk_str_index: Dict[str, Tuple[str, Set[str]]] = {}

        for tname, table in graph.tables.items():
            if not table.primary_key:
                continue
            pk_col = next((c for c in table.columns
                           if c['name'] == table.primary_key), None)
            if not pk_col:
                continue

            sv = pk_col.get('sample_values') or []
            if len(sv) < 3:
                continue

            dtype = pk_col.get('dtype', 'str')
            norm_set = set()
            for v in sv:
                nv = normalize_value(v)
                if nv is not None:
                    norm_set.add(nv)

            if len(norm_set) < 3:
                continue

            if dtype in ('int', 'float'):
                pk_int_index[tname] = (table.primary_key, norm_set)
            else:
                pk_str_index[tname] = (table.primary_key, norm_set)

        if not pk_int_index and not pk_str_index:
            self.logger.info("[PackArray] PK 索引为空，跳过")
            return []

        # ── 构建已存在关系的快速索引（去重用）──
        existing = self._build_relation_index(graph)

        relations: List[RelationEdge] = []
        pack_col_count = 0
        checked_pairs = 0

        for tname, table in graph.tables.items():
            # 增量模式：只处理变更表
            if changed_tables and tname not in changed_tables:
                continue

            # 找出所有 pack 列
            pack_cols = [c for c in table.columns if c.get('pack_info', {}).get('is_pack')]
            if not pack_cols:
                continue

            # 超宽表限流
            if len(pack_cols) > _MAX_PACK_COLS_PER_TABLE:
                pack_cols = pack_cols[:_MAX_PACK_COLS_PER_TABLE]

            pack_col_count += len(pack_cols)

            for col in pack_cols:
                pack_info = col['pack_info']
                elem_dtype = pack_info['pack_element_dtype']
                elem_samples = pack_info.get('pack_element_samples', [])
                sep = pack_info['pack_separator']

                if not elem_samples:
                    continue

                # 过滤噪声列（服务器编号等基础设施列）
                col_name_lower = col['name'].lower().replace(' ', '_')
                if any(kw in col_name_lower for kw in _NOISE_COL_KEYWORDS):
                    continue

                # ── 业务关键词白名单过滤（弱信号降级策略）──
                # 将列名去掉常见后缀再做关键词匹配，只有命中业务实体词才继续。
                # 未命中的 pack 列（如 configIds、serverList）作为通用数据跳过，
                # 不纳入主关系图，避免大量假阳性扩散。
                col_stem = col_name_lower
                for sfx in ('_ids', '_list', '_array', '_set', '_group',
                            '_id', '_ref', '_config', '_data'):
                    if col_stem.endswith(sfx) and len(col_stem) > len(sfx):
                        col_stem = col_stem[:-len(sfx)]
                        break
                # 用 _ 分词后做全词匹配，避免 "config" 被 "gid" 误匹配
                stem_parts = set(col_stem.split('_'))
                if not any(kw in stem_parts or col_stem == kw
                           for kw in _BUSINESS_COL_KEYWORDS):
                    continue

                # 元素数量过多的 pack 列通常是基础设施数据（如 serverId 有 2000 个值）
                if len(elem_samples) > _MAX_PACK_UNIQUE_ELEMENTS:
                    continue

                # 将元素样本标准化为字符串集合（与 PK 索引保持一致）
                elem_set: Set[str] = set()
                for e in elem_samples:
                    nv = normalize_value(e)
                    if nv is not None:
                        elem_set.add(nv)

                if len(elem_set) < 3:
                    continue

                # 选择对应类型的 PK 索引
                target_index = pk_int_index if elem_dtype == 'int' else pk_str_index

                # 收集所有候选命中，按 overlap_ratio 排序后只保留 top-N
                candidates: List[tuple] = []  # (overlap_ratio, target_name, target_pk, n_overlap)
                for target_name, (target_pk, pk_vals) in target_index.items():
                    if target_name == tname:
                        continue

                    checked_pairs += 1

                    overlap = elem_set & pk_vals
                    n_overlap = len(overlap)
                    if n_overlap < self.min_overlap:
                        continue

                    overlap_ratio = n_overlap / len(elem_set)
                    if overlap_ratio < self.min_overlap_ratio:
                        continue

                    # PK 覆盖率过高 → 顺序整数巧合，非真实外键
                    pk_coverage = n_overlap / len(pk_vals)
                    if pk_coverage > _MAX_PK_COVERAGE_RATIO:
                        continue

                    candidates.append((overlap_ratio, target_name, target_pk, n_overlap))

                # 只保留 overlap_ratio 最高的 top-N 目标
                candidates.sort(reverse=True)
                for overlap_ratio, target_name, target_pk, n_overlap in candidates[:_MAX_TARGETS_PER_COL]:
                    # 已存在此关系则跳过
                    if self._relation_exists_in_index(
                            existing, tname, col['name'], target_name, target_pk):
                        continue

                    # 置信度：弱信号模式，上限降至 _MAX_CONFIDENCE（0.78）
                    # 防止 pack_array 通过融合机制拉高其他策略的置信度
                    conf = min(_MAX_CONFIDENCE, self.base_confidence + overlap_ratio * 0.15)

                    rel = RelationEdge(
                        from_table=tname,
                        from_column=col['name'],
                        to_table=target_name,
                        to_column=target_pk,
                        relation_type='pack_array_fk',
                        confidence=round(conf, 2),
                        discovery_method='pack_array',
                        evidence=(
                            f"sep={sep!r}, "
                            f"overlap={n_overlap}/{len(elem_set)} "
                            f"({overlap_ratio:.0%})"
                        ),
                    )
                    relations.append(rel)

        self.logger.info(
            f"[PackArray] 扫描 {pack_col_count} 个 pack 列, "
            f"检查 {checked_pairs} 列对, 发现 {len(relations)} 个关系"
        )
        return relations
