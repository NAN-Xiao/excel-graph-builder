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
            # 精确匹配（最高优先级）
            if en_lower in table_lower_map:
                exact_matches.append(table_lower_map[en_lower])
                continue
            # 前缀匹配（en 是某个表名的前缀，如 'skill' 匹配 'skill_level'）
            # 但候选词需 >= 3 字符，且匹配的表名必须以 _ 或行尾衔接
            if len(en_lower) >= 3:
                for tname_lower, tname_real in table_lower_map.items():
                    if (tname_lower.startswith(en_lower) and
                            (len(tname_lower) == len(en_lower) or
                             tname_lower[len(en_lower)] == '_')):
                        if tname_real not in exact_matches and tname_real not in prefix_matches:
                            prefix_matches.append(tname_real)
        # 精确匹配优先，前缀匹配按表名长度排序（短表名更可能是基础实体表）
        prefix_matches.sort(key=len)
        combined = exact_matches + prefix_matches
        if combined:
            result[cn_key] = combined

    return result


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
