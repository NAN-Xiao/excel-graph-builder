#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
表结构提取器

从 DataFrame 提取 TableSchema，包括：
- 列名、类型、采样值
- 主键推断
- 枚举列识别
- 数值列识别
- 列语义标注（semantic_type / domain_role / metric_tag）
"""

import hashlib
import re
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd

from indexer.models import TableSchema

from .excel_reader import ExcelReader
from .pack_detector import detect_pack_column


# ──────────────────────────────────────────────────────────
# 列级语义标注规则表
# ──────────────────────────────────────────────────────────

# domain_role: 列的业务角色（按列名关键词前缀/后缀匹配，有序，先匹配先得）
_DOMAIN_ROLE_RULES: List[Tuple[str, List[str]]] = [
    ('id_key',       ['_id', '_key', '_no', '_code', '_idx', '_index']),
    ('name_label',   ['_name', '_desc', '_text', '_title', '_label', '_tip',
                      'name', 'desc', 'description', 'title', 'label', 'remark']),
    ('stat_hp',      ['_hp', 'hp', 'health', 'hitpoint', 'blood', 'life']),
    ('stat_atk',     ['atk', 'attack', '_dmg', 'damage', '_pow', 'power', '_str', 'strength']),
    ('stat_def',     ['_def', 'defense', 'defence', 'armour', 'armor', 'resist']),
    ('stat_spd',     ['_spd', 'speed', '_agi', 'agility', 'movespeed']),
    ('stat_crit',    ['crit', 'critical', '_luk', 'luck']),
    ('cooldown',     ['_cd', 'cooldown', 'colddown']),
    ('duration',     ['_dur', 'duration', '_interval', 'interval', '_delay', 'delay', '_period']),
    ('cost',         ['cost', 'price', '_fee', 'spend', 'consume', 'pay', 'expend']),
    ('resource',     ['gold', 'coin', 'gem', 'diamond', 'crystal', 'wood',
                      'food', 'iron', 'stone', 'ore', 'lumber', 'meat']),
    ('reward',       ['reward', 'bonus', 'prize', 'profit', 'earn', 'gain']),
    ('level_grade',  ['_lv', '_lvl', '_level', '_grade', '_tier', '_star',
                      'quality', 'rarity', 'rank']),
    ('count_limit',  ['_count', '_num', '_cnt', '_amount', '_max', '_min',
                      '_limit', '_cap', '_quota', 'max_', 'min_', 'num_', 'count_']),
    ('probability',  ['prob', 'rate', '_ratio', '_pct', 'percent', 'chance', 'probability']),
    ('flag_switch',  ['is_', 'enable', 'unlock', 'open', 'active', 'valid',
                      'show', 'hide', 'visible']),
    ('type_category',['_type', '_kind', '_class', '_sort', '_group', '_camp',
                      '_faction', 'type', 'kind', 'category']),
    ('position',     ['_pos', '_x', '_y', '_z', 'coord', 'location', '_slot', 'position']),
    ('time_stamp',   ['_time', '_date', '_ts', 'create_', 'update_', 'expire_']),
]

# metric_tag: 仅用于数值列，标记可聚合的游戏指标语义
_METRIC_TAG_RULES: List[Tuple[str, List[str]]] = [
    ('hp',        ['hp', 'health', 'hitpoint', 'blood', 'life']),
    ('attack',    ['atk', 'attack', 'dmg', 'damage', 'pow', 'power', 'str', 'strength']),
    ('defense',   ['def', 'defense', 'defence', 'armor', 'armour', 'resist']),
    ('speed',     ['spd', 'speed', 'agi', 'agility']),
    ('critical',  ['crit', 'critical', 'luk', 'luck']),
    ('cooldown',  ['cd', 'cooldown', 'colddown']),
    ('duration',  ['dur', 'duration', 'interval', 'delay', 'period']),
    ('level',     ['lv', 'lvl', 'level', 'grade', 'tier']),
    ('exp',       ['exp', 'xp', 'experience']),
    ('cost',      ['cost', 'price', 'fee', 'spend', 'consume', 'pay']),
    ('resource',  ['gold', 'coin', 'gem', 'diamond', 'crystal', 'wood',
                   'food', 'iron', 'stone', 'ore']),
    ('count',     ['count', 'num', 'cnt', 'amount', 'quantity', 'limit', 'cap', 'quota']),
    ('rate',      ['rate', 'prob', 'ratio', 'pct', 'percent', 'chance']),
    ('range',     ['range', 'radius', 'dist', 'distance', 'area']),
    ('rank',      ['rank', 'star', 'quality', 'rarity']),
    ('reward',    ['reward', 'bonus', 'prize', 'earn', 'gain']),
]

# temporal 列名关键词（无论 dtype 如何，都归为 temporal）
_TEMPORAL_KEYWORDS = frozenset([
    'time', 'date', 'ts', 'timestamp', 'createtime', 'updatetime',
    'expiretime', 'starttime', 'endtime', 'opentime', 'closetime',
])

# descriptor 列名关键词
_DESCRIPTOR_KEYWORDS = frozenset([
    'name', 'desc', 'description', 'text', 'title', 'label',
    'tip', 'hint', 'remark', 'comment', 'note', 'info',
    'path', 'icon', 'prefab', 'texture', 'resource',
])


class SchemaExtractor:
    """从 DataFrame 提取 TableSchema"""

    # 常见主键列名后缀
    PK_SUFFIXES = ('_id', '_key', '_no', '_code', 'id', 'key')
    PK_EXACT_NAMES = {'id', 'ID', 'Id', 'key',
                      'Key', 'KEY', 'no', 'code', 'index'}

    # 常见外键列名模式
    FK_PATTERN = re.compile(
        r'^(\w+?)(?:_id|_key|_no|_code|Id|Key|No|Code)$', re.IGNORECASE)

    # 枚举列识别阈值
    # ENUM_RATIO_THRESHOLD: 唯一值数 / 总行数 < 该比例时触发枚举检测
    ENUM_RATIO_THRESHOLD = 0.05
    # ENUM_MAX_UNIQUE: 唯一值数量上限
    # 原值 50 对万行表过严（100个状态码也不会被识别为枚举），调整为 200
    # 游戏配置中 200 个以内的离散值基本都属于枚举类型
    ENUM_MAX_UNIQUE = 200

    def __init__(self, max_sample_rows: int = 200):
        self.reader = ExcelReader(max_sample_rows=max_sample_rows)
        self.max_sample_rows = max_sample_rows

    def extract(self, file_path: str, sheet_name: str,
                df: pd.DataFrame, file_mtime: float) -> TableSchema:
        """
        从 DataFrame 提取完整的 TableSchema

        Args:
            file_path: 文件相对路径
            sheet_name: sheet 名
            df: 数据
            file_mtime: 文件修改时间戳

        Returns:
            TableSchema 实例
        """
        # 表名 = 文件名（不含扩展名）
        # 如果有多 sheet，表名 = 文件名_sheet名
        import os
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        table_name = base_name if sheet_name in (
            'Sheet1', base_name, None) else f"{base_name}_{sheet_name}"

        # 检测并修复表头：
        # - 跳过类型标记行、c/s/cs 导出标记行、注释说明行
        # - 若 pandas 误将注释行读为表头（导致列名为"// 说明"、"Unnamed: 1"等），
        #   自动用检测到的真正字段名行替换列名
        df, header_offset = self.reader.detect_and_fix_header(df)

        # 收集列信息
        col_samples = self.reader.collect_column_samples(df)
        columns = []
        numeric_columns = []
        enum_columns = {}

        for col_name, info in col_samples.items():
            col_entry = {
                'name': col_name,
                'dtype': info['dtype'],
                'sample_values': info['sample_values'],
                'unique_count': info['unique_count'],
                'null_count': info['null_count'],
                'total_count': info['total_count'],
            }

            # 数值统计（min/max/mean），由 ExcelReader.collect_column_samples 生成
            if 'stats' in info:
                col_entry['stats'] = info['stats']

            # Pack 数组检测：对 str 列识别 "101|102|103" 类多值格式
            # 检测结果存入 pack_info，供 PackArrayDiscovery 使用
            if info['dtype'] == 'str' and info['sample_values']:
                pack_info = detect_pack_column(info['sample_values'])
                if pack_info:
                    col_entry['pack_info'] = pack_info

            # 标记是否疑似外键引用
            col_entry['is_fk_candidate'] = self._is_fk_candidate(
                col_name, info)

            # 列级语义标注（列级裁剪层所需）
            is_enum = self._is_enum_column(info)
            pack_info = col_entry.get('pack_info')
            sem = _annotate_column(
                col_name=col_name,
                info=info,
                is_pk=False,          # PK 在此阶段尚未确定，后面修正
                is_fk=col_entry['is_fk_candidate'],
                is_enum=is_enum,
                pack_info=pack_info,
            )
            col_entry['semantic_type'] = sem['semantic_type']
            col_entry['domain_role']   = sem['domain_role']
            if sem['metric_tag']:
                col_entry['metric_tag'] = sem['metric_tag']

            columns.append(col_entry)

            # 数值列
            if info['dtype'] in ('int', 'float'):
                numeric_columns.append(col_name)

            # 枚举列
            if self._is_enum_column(info):
                enum_columns[col_name] = info['sample_values']

        # 推断主键
        primary_key = self._infer_primary_key(columns, len(df))

        # 修正主键列的 semantic_type（主键推断在列扫描后完成，需回写）
        if primary_key:
            for col_entry in columns:
                if col_entry['name'] == primary_key:
                    col_entry['semantic_type'] = 'identifier'
                    col_entry['domain_role'] = 'id_key'
                    col_entry.pop('metric_tag', None)
                    break

        # 计算内容哈希（用于增量检测）
        content_hash = self._compute_hash(df)

        return TableSchema(
            name=table_name,
            file_path=file_path,
            sheet_name=sheet_name,
            row_count=len(df),
            columns=columns,
            primary_key=primary_key,
            modified_time=file_mtime,
            hash=content_hash,
            numeric_columns=numeric_columns,
            enum_columns=enum_columns,
            header_offset=header_offset,
        )

    # 坐标/向量格式：N,M 或 N|M 或 N.M.K
    _COORD_RE = re.compile(r'^-?\d+[,|.]-?\d+')

    # c/s/cs 导出标记 — 这些不是业务 ID
    _EXPORT_MARKER_SET = frozenset([
        'c', 's', 'cs', 'sc', 'all', 'none', 'both',
        'server', 'client', 'common',
    ])

    def _infer_primary_key(self, columns: List[Dict], row_count: int) -> Optional[str]:
        """
        推断主键列

        策略：
        1. 过滤掉明显不是 PK 的列（坐标格式、c/s/cs 标记、长字符串路径）
        2. 第一列如果唯一率 > 95% 且名字含 id/key，直接选
        3. 否则找唯一率最高 + 命名匹配的列
        4. 都找不到返回 None
        """
        if not columns or row_count == 0:
            return None

        candidates = []

        for col in columns:
            unique_ratio = col['unique_count'] / row_count if row_count > 0 else 0
            name_lower = col['name'].lower()

            # ── 排除明显非 PK 的列 ──
            sv = col.get('sample_values') or []

            # 排除：坐标/向量格式（如 "0,0", "1|2", "1.2.3"）
            if sv and all(
                isinstance(v, str) and self._COORD_RE.match(str(v))
                for v in sv[:10] if v is not None
            ):
                continue

            # 排除：c/s/cs 导出标记列（所有值都在标记集里）
            if sv and all(
                str(v).strip().lower() in self._EXPORT_MARKER_SET
                for v in sv[:20] if v is not None
            ):
                continue

            # 排除：平均值长度过长的字符串列（路径/描述/名称，不是 ID）
            if col['dtype'] == 'str' and sv:
                avg_len = sum(len(str(v)) for v in sv[:20]) / max(len(sv[:20]), 1)
                if avg_len > 30:
                    continue

            # ── 计分 ──
            # 命名得分
            name_score = 0
            if name_lower in self.PK_EXACT_NAMES:
                name_score = 10
            elif any(name_lower.endswith(s) for s in self.PK_SUFFIXES):
                name_score = 5
            # 中文主键列名（如"主键"、"编号"、"索引"）
            elif any(kw in col['name'] for kw in ('主键', '编号', '索引', '序号')):
                name_score = 8

            # 唯一性得分
            if unique_ratio >= 0.99:
                unique_score = 10
            elif unique_ratio >= 0.95:
                unique_score = 7
            elif unique_ratio >= 0.8:
                unique_score = 3
            else:
                unique_score = 0

            # 类型得分（整数更可能是 PK）
            type_score = 3 if col['dtype'] == 'int' else 1

            total = name_score + unique_score + type_score
            if unique_ratio >= 0.8 and (name_score > 0 or unique_ratio >= 0.95):
                candidates.append((col['name'], total))

        if not candidates:
            # 退而求其次：第一列唯一率 > 80%（但仍排除坐标/标记列）
            first = columns[0]
            if row_count > 0 and first['unique_count'] / row_count >= 0.8:
                sv = first.get('sample_values') or []
                is_coord = sv and all(
                    isinstance(v, str) and self._COORD_RE.match(str(v))
                    for v in sv[:10] if v is not None
                )
                if not is_coord:
                    return first['name']
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _is_fk_candidate(self, col_name: str, info: Dict) -> bool:
        """判断列是否可能是外键引用"""
        name_lower = col_name.lower()

        # 命名模式匹配
        if self.FK_PATTERN.match(col_name):
            return True

        # 以 _id 结尾的整数列
        if name_lower.endswith('_id') and info['dtype'] in ('int', 'float'):
            return True

        # 较高唯一率的整数列（可能是 ID 引用）
        total = info['total_count']
        if total > 0 and info['dtype'] == 'int':
            unique_ratio = info['unique_count'] / total
            if 0.1 < unique_ratio < 0.95:
                return True

        return False

    def _is_enum_column(self, info: Dict) -> bool:
        """判断是否为枚举列。

        双重条件（满足任一即可）：
        1. 绝对数量小（≤ 20）：无论行数多少，20个以内的离散值几乎必然是枚举
        2. 比例+绝对数量联合判断：unique_count ≤ ENUM_MAX_UNIQUE 且比例 ≤ 阈值
           — 适配大表（万行），允许最多 200 个枚举值
        """
        total = info['total_count']
        if total == 0:
            return False
        if info['unique_count'] < 2:
            return False

        unique_count = info['unique_count']
        unique_ratio = unique_count / total

        # 条件1：绝对少量离散值（≤20），不受比例限制
        if unique_count <= 20:
            return True

        # 条件2：满足比例阈值且在最大枚举数内
        return (
            unique_count <= self.ENUM_MAX_UNIQUE and
            unique_ratio <= self.ENUM_RATIO_THRESHOLD
        )

    @staticmethod
    def _compute_hash(df: pd.DataFrame) -> str:
        """
        计算 DataFrame 内容哈希，用于增量检测。
        只用前几行 + 列名 + shape 做快速哈希，不遍历全表。
        """
        h = hashlib.md5()
        h.update(str(df.shape).encode())
        h.update(','.join(str(c) for c in df.columns).encode())
        # 取前10行 + 后10行做哈希
        head = df.head(10).to_csv(index=False, header=False)
        tail = df.tail(10).to_csv(index=False, header=False)
        h.update(head.encode('utf-8', errors='replace'))
        h.update(tail.encode('utf-8', errors='replace'))
        return h.hexdigest()


# ──────────────────────────────────────────────────────────
# 列级语义标注（模块级函数，SchemaExtractor.extract() 调用）
# ──────────────────────────────────────────────────────────

def _annotate_column(
    col_name: str,
    info: Dict,
    is_pk: bool,
    is_fk: bool,
    is_enum: bool,
    pack_info: Optional[Dict],
) -> Dict:
    """
    为单列推断三个语义字段：

    semantic_type:
        identifier  — 主键或外键引用（整数 ID）
        metric      — 可聚合的数值指标
        flag        — 布尔 / 0-1 开关
        enum        — 有限离散值（非 ID、非 flag）
        pack_array  — 多值打包字符串（101|102|103）
        temporal    — 日期时间
        descriptor  — 名称、描述、路径等字符串
        text        — 长文本
        coordinate  — 坐标/向量格式

    domain_role:
        业务角色关键词（id_key / stat_hp / cost / level_grade / …）

    metric_tag:
        仅数值列有效，标注可聚合的游戏指标语义（hp/attack/cost/…）
    """
    name_lower = col_name.lower()
    dtype = info.get('dtype', 'str')
    sv = info.get('sample_values') or []
    unique_count = info.get('unique_count', 0)

    # ── semantic_type ──

    # pack_array 优先（结构性强）
    if pack_info and pack_info.get('is_pack'):
        sem_type = 'pack_array'

    # 主键 / 外键 → identifier
    elif is_pk or (is_fk and dtype == 'int'):
        sem_type = 'identifier'

    # 日期时间
    elif dtype == 'datetime' or any(kw in name_lower for kw in _TEMPORAL_KEYWORDS):
        sem_type = 'temporal'

    # bool / 极小枚举（≤3值，常见 0/1/2 或 True/False/None）
    elif dtype == 'bool':
        sem_type = 'flag'
    elif is_enum and unique_count <= 3:
        str_vals = {str(v).lower() for v in sv if v is not None}
        if str_vals <= {'0', '1', '2', 'true', 'false', 'yes', 'no',
                        'none', '', 'enable', 'disable', 'on', 'off'}:
            sem_type = 'flag'
        else:
            sem_type = 'enum'

    # 枚举
    elif is_enum and dtype != 'int':
        sem_type = 'enum'

    # 整数枚举（ID 类型枚举）→ identifier（如 camp_type、quality_level）
    elif is_enum and dtype == 'int':
        sem_type = 'identifier' if is_fk else 'enum'

    # 坐标列（已在 PK 推断中排除，但列本身可能保留）
    elif dtype == 'str' and sv:
        _COORD_RE = re.compile(r'^-?\d+[,|.]-?\d+')
        if all(isinstance(v, str) and _COORD_RE.match(str(v))
               for v in sv[:8] if v is not None):
            sem_type = 'coordinate'
        else:
            avg_len = sum(len(str(v)) for v in sv[:20]) / max(len(sv[:20]), 1)
            # 短字符串 → 看名字
            if avg_len > 40:
                sem_type = 'text'
            elif any(kw in name_lower for kw in _DESCRIPTOR_KEYWORDS):
                sem_type = 'descriptor'
            else:
                sem_type = 'descriptor'

    # 数值（非 identifier、非 enum）
    elif dtype in ('int', 'float'):
        sem_type = 'metric'

    else:
        sem_type = 'descriptor'

    # ── domain_role ──
    domain_role = _match_role(name_lower, _DOMAIN_ROLE_RULES)

    # ── metric_tag ──（仅 metric / identifier 的数值列）
    metric_tag: Optional[str] = None
    if dtype in ('int', 'float') and sem_type in ('metric', 'identifier', 'enum'):
        metric_tag = _match_role(name_lower, _METRIC_TAG_RULES)

    return {
        'semantic_type': sem_type,
        'domain_role':   domain_role,
        'metric_tag':    metric_tag,
    }


def _match_role(name_lower: str, rules: List[Tuple[str, List[str]]]) -> Optional[str]:
    """按规则列表做前/后/中缀匹配，返回第一个命中的角色标签。"""
    for role, keywords in rules:
        for kw in keywords:
            # 后缀匹配（最常见：_type / _id）
            if name_lower.endswith(kw):
                return role
            # 前缀匹配（max_ / min_ / num_）
            if kw.endswith('_') and name_lower.startswith(kw):
                return role
            # 精确片段匹配（中间词）
            if kw in name_lower:
                return role
    return None
