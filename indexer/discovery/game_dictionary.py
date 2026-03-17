#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
游戏领域词典

提供游戏配置表常用的缩写映射、领域术语、列名模式。
辅助关系发现（特别是缩写挖掘）提高准确率。
"""

from typing import Dict, List, Set, Optional, Tuple


# 常见游戏缩写 → 全称映射
GAME_ABBREVIATIONS: Dict[str, List[str]] = {
    # 属性类
    'atk': ['attack'],
    'def': ['defense', 'defence'],
    'hp': ['hitpoint', 'health', 'healthpoint'],
    'mp': ['mana', 'manapoint', 'magic'],
    'sp': ['skill_point', 'stamina', 'special'],
    'spd': ['speed'],
    'crit': ['critical'],
    'dmg': ['damage'],
    'str': ['strength'],
    'agi': ['agility'],
    'int': ['intelligence'],
    'vit': ['vitality'],
    'luk': ['luck'],
    'exp': ['experience'],
    'lv': ['level'],
    'lvl': ['level'],

    # 实体类
    'char': ['character'],
    'npc': ['non_player_character'],
    'mob': ['monster'],
    'equip': ['equipment'],
    'wpn': ['weapon'],
    'itm': ['item'],
    'inv': ['inventory'],
    'ach': ['achievement'],
    'evt': ['event'],
    'tsk': ['task'],
    'qst': ['quest'],
    'dng': ['dungeon'],
    'pvp': ['player_vs_player'],
    'pve': ['player_vs_environment'],
    'cfg': ['config', 'configuration'],
    'desc': ['description'],
    'txt': ['text'],
    'img': ['image'],
    'btn': ['button'],
    'ui': ['user_interface'],
    'bgm': ['background_music'],
    'sfx': ['sound_effect'],
    'vfx': ['visual_effect'],
    'res': ['resource'],
    'sid': ['skill'],
    'tid': ['task', 'template'],
    'gid': ['group'],
    'pid': ['player'],
    'mid': ['monster', 'map'],
    'eid': ['event', 'equipment'],
    'rid': ['reward', 'role'],
    'cid': ['character', 'chapter'],
    'aid': ['activity', 'achievement'],
    'bid': ['buff', 'battle'],
    'did': ['dungeon'],
    'wid': ['weapon', 'world'],

    # 系统类
    'cd': ['cooldown'],
    'buff': ['buff'],
    'debuff': ['debuff'],
    'aoe': ['area_of_effect'],
    'dot': ['damage_over_time'],
    'hot': ['heal_over_time'],
    'cc': ['crowd_control'],
    'rng': ['random_number_generator', 'range'],
    'prob': ['probability'],
    'pct': ['percent', 'percentage'],
    'cnt': ['count'],
    'num': ['number'],
    'max': ['maximum'],
    'min': ['minimum'],
    'dur': ['duration'],
    'cd': ['cooldown'],
    'req': ['requirement', 'require'],
    'cond': ['condition'],
    'tgt': ['target'],
    'src': ['source'],
    'dst': ['destination'],
    'prev': ['previous'],
    'nxt': ['next'],
    'cur': ['current'],
    'tmp': ['temporary'],
    'perm': ['permanent'],
}

# 反向索引：全称 → 缩写列表
_REVERSE_ABBREV: Dict[str, List[str]] = {}
for abbr, fulls in GAME_ABBREVIATIONS.items():
    for full in fulls:
        if full not in _REVERSE_ABBREV:
            _REVERSE_ABBREV[full] = []
        _REVERSE_ABBREV[full].append(abbr)


# 游戏配置表常见业务域分类关键词（通用，用于 classify_table_domain 等查询）
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    'hero': ['hero', 'character', 'role', 'char', 'player'],
    'skill': ['skill', 'ability', 'talent', 'spell', 'magic'],
    'item': ['item', 'goods', 'product', 'material', 'equip', 'equipment', 'weapon', 'armor'],
    'monster': ['monster', 'enemy', 'mob', 'boss', 'creature', 'npc'],
    'quest': ['quest', 'task', 'mission', 'story', 'chapter', 'campaign'],
    'dungeon': ['dungeon', 'stage', 'level', 'map', 'scene', 'instance'],
    'reward': ['reward', 'prize', 'loot', 'drop', 'bonus', 'gift'],
    'shop': ['shop', 'store', 'mall', 'trade', 'exchange'],
    'activity': ['activity', 'event', 'festival', 'season', 'campaign'],
    'ui': ['ui', 'interface', 'menu', 'dialog', 'text', 'localization', 'i18n', 'lang'],
    'battle': ['battle', 'combat', 'fight', 'arena', 'pvp', 'pve', 'war'],
    'social': ['guild', 'clan', 'team', 'friend', 'chat', 'mail', 'social'],
    'gacha': ['gacha', 'summon', 'draw', 'pool', 'banner', 'wish', 'lottery'],
    'growth': ['upgrade', 'enhance', 'evolve', 'awaken', 'refine', 'breakthrough', 'star'],
}


# ============================================================
# 统一业务域分类规则（有序列表）
# 用于 GraphBuilder._assign_domain_label / HTMLReportGenerator._get_group
# 规则按顺序匹配，第一个命中即停止，因此更具体的放前面
# ============================================================

DOMAIN_CLASSIFICATION_RULES: List[tuple] = [
    ("hero",     ['hero', 'character', 'char_']),
    ("skill",    ['skill', 'ability', 'spell', 'buff', 'talent']),
    ("battle",   ['battle', 'fight', 'pvp', 'war', 'combat', 'army']),
    ("item",     ['item', 'equip', 'prop', 'goods', 'material', 'resource']),
    ("building", ['building', 'construct', 'castle', 'city']),
    ("quest",    ['quest', 'task', 'mission', 'chapter', 'stage']),
    ("alliance", ['alliance', 'guild', 'union', 'clan', 'legion']),
    ("monster",  ['monster', 'enemy', 'npc', 'mob', 'boss', 'creature']),
    ("reward",   ['reward', 'drop', 'loot', 'prize', 'chest', 'gift']),
    ("world",    ['map', 'world', 'terrain', 'region', 'area', 'field']),
    ("social",   ['mail', 'chat', 'message', 'notice', 'friend']),
    ("config",   ['config', 'setting', 'param', 'const', 'global', 'system']),
]

# 分类颜色映射（HTML 可视化用）
DOMAIN_COLORS: Dict[str, str] = {
    'hero': '#ff6b6b', 'skill': '#feca57', 'battle': '#ff9ff3',
    'item': '#55efc4', 'building': '#74b9ff', 'quest': '#a29bfe',
    'alliance': '#00cec9', 'monster': '#e17055', 'reward': '#fdcb6e',
    'world': '#81ecec', 'social': '#fd79a8', 'config': '#636e72',
    'other': '#b2bec3',
}


def classify_domain(table_name: str) -> str:
    """
    根据表名按统一规则分类业务域（有序匹配）。

    Returns:
        域名标签，未匹配返回 'other'
    """
    name_lower = table_name.lower()
    for label, keywords in DOMAIN_CLASSIFICATION_RULES:
        if any(kw in name_lower for kw in keywords):
            return label
    return "other"


# 中文实体关键词 → 英文表名前缀的种子词典（通用游戏术语）
# 仅作为基础映射；实际使用时通过 build_cn_table_index() 结合真实表名动态构建
_BASE_CN_ENTITY_MAP: Dict[str, List[str]] = {
    '技能': ['skill', 'ability', 'talent', 'spell'],
    '英雄': ['hero', 'character', 'champion', 'role'],
    '物品': ['item', 'goods', 'product'],
    '道具': ['item', 'prop'],
    '装备': ['equip', 'equipment', 'gear'],
    '活动': ['activity', 'event'],
    '怪物': ['monster', 'enemy', 'mob', 'creature'],
    '建筑': ['building', 'construct'],
    '兵种': ['army', 'troop', 'soldier', 'unit'],
    '科技': ['science', 'tech', 'technology', 'research'],
    '武器': ['weapon', 'arm'],
    '任务': ['quest', 'task', 'mission'],
    '关卡': ['stage', 'instance', 'dungeon', 'level'],
    '奖励': ['reward', 'prize', 'bonus'],
    '商店': ['shop', 'store', 'mall'],
    '公会': ['guild', 'alliance', 'clan'],
    '联盟': ['alliance', 'league', 'union'],
    '地图': ['map', 'world', 'scene'],
    '角色': ['hero', 'character', 'role', 'avatar'],
    '宝箱': ['chest', 'box', 'treasure'],
    '资源': ['resource', 'res'],
    '阵营': ['camp', 'faction', 'side'],
    '特效': ['effect', 'vfx'],
    'buff': ['buff'],
    '天赋': ['talent', 'perk'],
    '皮肤': ['skin', 'costume'],
    '称号': ['title'],
    '成就': ['achievement'],
    '副本': ['instance', 'dungeon', 'raid'],
    '战斗': ['battle', 'combat', 'fight'],
    '赛季': ['season'],
    '排行': ['rank', 'leaderboard'],
    '邮件': ['mail', 'message'],
    '聊天': ['chat'],
    'vip': ['vip'],
    '等级': ['level', 'grade'],
    '星级': ['star'],
    '品质': ['quality', 'rarity'],
    '卡牌': ['card'],
    '宠物': ['pet', 'familiar'],
    '坐骑': ['mount', 'ride'],
    '背包': ['bag', 'inventory', 'backpack'],
    '签到': ['signin', 'checkin'],
    '抽卡': ['gacha', 'draw', 'summon'],
    '好友': ['friend', 'social'],
    '战队': ['team', 'squad', 'party'],
    '法术': ['spell', 'magic'],
    '伙伴': ['partner', 'companion'],
    '神器': ['artifact', 'relic'],
    '符文': ['rune'],
    '职业': ['class', 'profession', 'job', 'vocation'],
    '种族': ['race', 'tribe', 'faction'],
    '图鉴': ['collection', 'codex', 'handbook'],
    '剧情': ['story', 'plot', 'scenario'],
    '阵型': ['formation'],
    '时装': ['fashion', 'costume', 'outfit'],
    '礼包': ['package', 'bundle', 'gift'],
    '通关': ['clear', 'pass'],
    '竞技': ['arena', 'pvp', 'tournament'],
}


def lookup_abbreviation(abbrev: str) -> List[str]:
    """查询缩写对应的全称"""
    return GAME_ABBREVIATIONS.get(abbrev.lower(), [])


def lookup_full_name(full_name: str) -> List[str]:
    """查询全称对应的缩写"""
    return _REVERSE_ABBREV.get(full_name.lower(), [])


def classify_table_domain(table_name: str) -> Optional[str]:
    """
    根据表名判断业务域

    Returns:
        域名（如 'hero', 'skill'）或 None
    """
    name_lower = table_name.lower()
    best_domain = None
    best_score = 0

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                score = len(kw)  # 越长的匹配越精确
                if score > best_score:
                    best_score = score
                    best_domain = domain

    return best_domain


def expand_column_name(col_name: str) -> List[str]:
    """
    扩展列名缩写，返回可能的全称表名列表。

    例: 'sid' → ['skill'], 'hero_id' → ['hero']
    """
    clean = col_name.lower()

    # 先去掉后缀
    for suffix in ['_id', '_key', '_no', '_code', '_type', '_idx']:
        if clean.endswith(suffix):
            clean = clean[:-len(suffix)]
            break

    # 直接查字典
    results = lookup_abbreviation(clean)

    # 也返回自身（如果就是表名）
    if clean not in results:
        results.append(clean)

    return results


def build_cn_table_index(table_names: List[str]) -> Dict[str, List[str]]:
    """
    动态构建 中文关键词 → 实际表名 的映射索引。

    策略:
    1. 用 _BASE_CN_ENTITY_MAP 中的英文候选词，反向匹配实际存在的表名
    2. 只保留在图谱中真实存在的表名，确保不会匹配到不存在的目标
    3. 自动从表名中提取 stem（去掉 _base/_config/_data 等后缀），
       反向查 _REVERSE_CN_MAP 补充词典覆盖

    Args:
        table_names: 图谱中所有实际表名（如 ['hero', 'skill', 'item', ...]）

    Returns:
        {'技能': ['skill'], '英雄': ['hero'], ...}
        只包含能匹配到实际表名的条目
    """
    table_lower_map = {n.lower(): n for n in table_names}
    result: Dict[str, List[str]] = {}

    for cn_key, en_candidates in _BASE_CN_ENTITY_MAP.items():
        exact_matches = []
        prefix_matches = []
        for en in en_candidates:
            en_lower = en.lower()
            if en_lower in table_lower_map:
                exact_matches.append(table_lower_map[en_lower])
                continue
            if len(en_lower) >= 3:
                for tname_lower, tname_real in table_lower_map.items():
                    if (tname_lower.startswith(en_lower) and
                            (len(tname_lower) == len(en_lower) or
                             tname_lower[len(en_lower)] == '_')):
                        if tname_real not in exact_matches and tname_real not in prefix_matches:
                            prefix_matches.append(tname_real)
        prefix_matches.sort(key=len)
        combined = exact_matches + prefix_matches
        if combined:
            result[cn_key] = combined

    # 自动扩展: 从实际表名 stem 反查中文关键词，补充未覆盖的映射
    _auto_expand_cn_index(result, table_lower_map)

    return result


# 英文 stem → 中文关键词 的反向索引（用于自动扩展）
_REVERSE_CN_MAP: Dict[str, List[str]] = {}
for _cn, _en_list in _BASE_CN_ENTITY_MAP.items():
    for _en in _en_list:
        _REVERSE_CN_MAP.setdefault(_en.lower(), []).append(_cn)

_TABLE_STEM_SUFFIXES = frozenset([
    '_base', '_config', '_data', '_info', '_list', '_detail',
    '_table', '_cfg', '_setting', '_param', '_define',
])


def _auto_expand_cn_index(result: Dict[str, List[str]],
                          table_lower_map: Dict[str, str]):
    """
    从实际表名中提取 stem，反查中文关键词。
    若该 stem 已被 _BASE_CN_ENTITY_MAP 覆盖但 result 中缺失该表名，
    则将表名补入 result。
    """
    for tname_lower, tname_real in table_lower_map.items():
        stem = tname_lower
        for sfx in _TABLE_STEM_SUFFIXES:
            if tname_lower.endswith(sfx) and len(tname_lower) > len(sfx):
                stem = tname_lower[:-len(sfx)]
                break

        cn_keys = _REVERSE_CN_MAP.get(stem, [])
        for cn_key in cn_keys:
            existing = result.get(cn_key, [])
            if tname_real not in existing:
                result.setdefault(cn_key, []).append(tname_real)


def extract_cn_entity_tables(col_name: str,
                             cn_table_index: Optional[Dict[str, List[str]]] = None
                             ) -> List[str]:
    """
    从中文列名中提取引用的实际表名候选。

    例: '英雄主动技能ID' → ['skill'] (如果图谱中有 skill 表)
        '英雄专属雕像物品ID' → ['item']

    Args:
        col_name: 列名
        cn_table_index: 由 build_cn_table_index() 动态构建的索引。
                        如果为 None 则回退到 _BASE_CN_ENTITY_MAP（仅返回英文候选）。

    策略: 从列名末尾向前查找最长匹配的中文实体关键词，
    避免 "英雄主动技能ID" 同时返回 hero 和 skill — 优先取最靠近后缀的实体。
    """
    # 去掉常见后缀
    name = col_name
    for suffix in ('ID', 'Id', 'id', '编号', '编码', '序号', '索引'):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break

    if not name:
        return []

    lookup = cn_table_index if cn_table_index is not None else _BASE_CN_ENTITY_MAP

    # 从后向前扫描，找最靠近后缀的中文实体
    best_pos = -1
    best_tables: List[str] = []
    for cn_key, table_list in lookup.items():
        pos = name.rfind(cn_key)
        if pos >= 0 and pos > best_pos:
            best_pos = pos
            best_tables = list(table_list)

    return best_tables
