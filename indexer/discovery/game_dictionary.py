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


# 游戏配置表常见业务域分类关键词
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
