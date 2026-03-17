#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG 专用资产导出

为外部 RAG 召回系统提供三份关键数据：

1. relation_graph.json  — 邻接表 + JOIN 条件
   外部系统拿到用户提到的表名后，用这份数据找到关联表和 JOIN 路径，
   从而知道"要回答这个问题还需要读哪些表、怎么关联"。

2. join_paths.json      — 预计算的表间最短 JOIN 路径（1~3 跳）
   外部系统不用自己做 BFS，直接查 A→B 的 JOIN 链，
   即可知道需要经过哪些中间表、用哪些列关联。

3. table_profiles.jsonl — 每表一行的富元数据 profile
   包含列清单、主键、枚举值列表、样本值、关联方向等，
   让外部系统在向量召回后能快速判断"这张表能回答什么问题"。

导出目录结构:
    <excel_dir>/graph/
    ├── relation_graph.json
    ├── join_paths.json
    └── table_profiles.jsonl
"""

import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
from collections import defaultdict, deque

from indexer.models import SchemaGraph, RelationEdge

# domain → 中文名映射（用于 enriched searchable_text）
_DOMAIN_CN_NAMES: Dict[str, List[str]] = {
    'hero': ['英雄', '角色', '人物'],
    'skill': ['技能', '法术', '天赋'],
    'battle': ['战斗', '对战', '战争'],
    'item': ['物品', '道具', '装备', '材料'],
    'building': ['建筑', '城堡'],
    'quest': ['任务', '关卡', '副本'],
    'alliance': ['联盟', '公会'],
    'monster': ['怪物', '敌人', 'Boss'],
    'reward': ['奖励', '掉落', '宝箱'],
    'world': ['地图', '世界', '场景'],
    'social': ['社交', '邮件', '聊天'],
    'config': ['配置', '系统', '参数'],
    'growth': ['成长', '升级', '进阶'],
    'gacha': ['抽卡', '召唤', '卡池'],
    'shop': ['商店', '商城'],
}


def _get_cn_synonyms(table_name: str) -> List[str]:
    """从 game_dictionary 反查表名的中文同义词"""
    try:
        from indexer.discovery.game_dictionary import _BASE_CN_ENTITY_MAP
    except ImportError:
        return []
    name_lower = table_name.lower()
    # 提取表名 stem（去掉 _base/_config 等后缀）
    stem = name_lower
    for sfx in ('_base', '_config', '_data', '_info', '_list', '_detail',
                '_table', '_cfg', '_setting', '_param', '_define'):
        if name_lower.endswith(sfx) and len(name_lower) > len(sfx):
            stem = name_lower[:-len(sfx)]
            break

    synonyms = []
    for cn_key, en_list in _BASE_CN_ENTITY_MAP.items():
        for en in en_list:
            if en.lower() == stem or en.lower() == name_lower:
                synonyms.append(cn_key)
                break
    return synonyms


# ──────────────────────────────────────────────────────────
# 1. relation_graph.json — 邻接表 + JOIN 条件
# ──────────────────────────────────────────────────────────

def export_relation_graph(graph: SchemaGraph,
                          output_path: Optional[str] = None,
                          min_confidence: float = 0.5) -> dict:
    """
    导出完整的关系邻接表（双向），附带 JOIN 条件。

    格式:
    {
      "hero_base": {
        "domain": "hero",
        "primary_key": "id",
        "file": "hero_base.xlsx",
        "neighbors": [
          {
            "table": "skill_base",
            "direction": "outgoing",       # hero_base 引用 skill_base
            "join": "hero_base.skill_id = skill_base.id",
            "local_column": "skill_id",
            "remote_column": "id",
            "confidence": 0.92,
            "relation_type": "foreign_key",
            "method": "naming_convention"
          },
          ...
        ]
      }
    }
    """
    adj: Dict[str, dict] = {}

    # 初始化所有表
    for name, table in graph.tables.items():
        adj[name] = {
            "domain": table.domain_label or "other",
            "primary_key": table.primary_key,
            "file": Path(table.file_path).name,
            "sheet": table.sheet_name,
            "row_count": table.row_count,
            "col_count": len(table.columns),
            "neighbors": []
        }

    # 填充双向邻居
    for rel in graph.relations:
        if rel.confidence < min_confidence:
            continue

        # outgoing: from_table → to_table
        if rel.from_table in adj:
            adj[rel.from_table]["neighbors"].append({
                "table": rel.to_table,
                "direction": "outgoing",
                "join": f"{rel.from_table}.{rel.from_column} = {rel.to_table}.{rel.to_column}",
                "local_column": rel.from_column,
                "remote_column": rel.to_column,
                "confidence": round(rel.confidence, 3),
                "relation_type": rel.relation_type,
                "method": rel.discovery_method,
            })

        # incoming: to_table ← from_table
        if rel.to_table in adj:
            adj[rel.to_table]["neighbors"].append({
                "table": rel.from_table,
                "direction": "incoming",
                "join": f"{rel.from_table}.{rel.from_column} = {rel.to_table}.{rel.to_column}",
                "local_column": rel.to_column,
                "remote_column": rel.from_column,
                "confidence": round(rel.confidence, 3),
                "relation_type": rel.relation_type,
                "method": rel.discovery_method,
            })

    # 按置信度排序邻居
    for info in adj.values():
        info["neighbors"].sort(key=lambda x: -x["confidence"])

    result = {"_meta": {
        "table_count": len(graph.tables),
        "relation_count": len(graph.relations),
        "min_confidence": min_confidence,
        "description": "表间关系邻接表。neighbors 数组包含双向关系和 JOIN 条件。"
    }, "tables": adj}

    if output_path:
        _write_json(output_path, result)

    return result


# ──────────────────────────────────────────────────────────
# 2. join_paths.json — 预计算 JOIN 路径
# ──────────────────────────────────────────────────────────

def export_join_paths(graph: SchemaGraph,
                      output_path: Optional[str] = None,
                      min_confidence: float = 0.65,
                      max_hops: int = 2) -> dict:
    """
    预计算所有表对之间的最短 JOIN 路径（BFS, ≤ max_hops 跳）。

    格式:
    {
      "hero_base -> skill_base": {
        "hops": 1,
        "path": ["hero_base", "skill_base"],
        "joins": ["hero_base.skill_id = skill_base.id"],
        "min_confidence": 0.92
      },
      "hero_base -> buff_base": {
        "hops": 2,
        "path": ["hero_base", "skill_base", "buff_base"],
        "joins": [
          "hero_base.skill_id = skill_base.id",
          "skill_base.buff_id = buff_base.id"
        ],
        "min_confidence": 0.85
      }
    }

    外部 RAG 系统用法:
      1. 用户问题涉及表 A 和表 B
      2. 查 join_paths["A -> B"]
      3. 拿到 joins 列表，依次读表并关联
    """
    # 构建加权邻接表（仅保留高置信度关系）
    # adj[A] = [(B, join_str, confidence), ...]
    adj: Dict[str, List[Tuple[str, str, float]]] = defaultdict(list)
    for rel in graph.relations:
        if rel.confidence < min_confidence:
            continue
        join_str = f"{rel.from_table}.{rel.from_column} = {rel.to_table}.{rel.to_column}"
        adj[rel.from_table].append((rel.to_table, join_str, rel.confidence))
        adj[rel.to_table].append((rel.from_table, join_str, rel.confidence))

    # Only compute paths for tables that have at least one relation (skip orphans)
    connected_tables = sorted(adj.keys())
    paths: Dict[str, dict] = {}

    # BFS from each connected table
    for src in connected_tables:
        visited: Dict[str, Tuple[List[str], List[str], float]] = {}
        # visited[node] = (path, joins, min_conf)
        queue: deque = deque()
        queue.append((src, [src], [], 1.0))
        visited[src] = ([src], [], 1.0)

        while queue:
            node, path, joins, min_conf = queue.popleft()
            if len(path) - 1 >= max_hops:
                continue
            for neighbor, join_str, conf in adj.get(node, []):
                new_min_conf = min(min_conf, conf)
                if neighbor not in visited or len(path) + 1 < len(visited[neighbor][0]):
                    new_path = path + [neighbor]
                    new_joins = joins + [join_str]
                    visited[neighbor] = (new_path, new_joins, new_min_conf)
                    queue.append((neighbor, new_path, new_joins, new_min_conf))

        for dst, (path, joins, min_conf) in visited.items():
            if dst == src:
                continue
            key = f"{src} -> {dst}"
            paths[key] = {
                "hops": len(path) - 1,
                "path": path,
                "joins": joins,
                "min_confidence": round(min_conf, 3)
            }

    result = {
        "_meta": {
            "total_paths": len(paths),
            "max_hops": max_hops,
            "min_confidence": min_confidence,
            "description": (
                "预计算的表间最短 JOIN 路径。"
                "key 格式: 'source -> target'。"
                "joins 数组是按顺序执行的 JOIN 条件。"
            )
        },
        "paths": paths
    }

    if output_path:
        _write_json(output_path, result)

    return result


# ──────────────────────────────────────────────────────────
# 3. table_profiles.jsonl — 每表富元数据
# ──────────────────────────────────────────────────────────

def export_table_profiles(graph: SchemaGraph,
                          output_path: Optional[str] = None,
                          min_confidence: float = 0.5) -> List[dict]:
    """
    导出每张表的富元数据 profile（一行一个 JSON 对象）。

    每个 profile 包含:
    - 基本信息: name, domain, file, sheet, row_count, primary_key
    - columns: [{name, dtype, is_pk, is_fk, fk_target, is_enum, enum_values, sample_values}]
    - outgoing_relations: 本表引用的其他表
    - incoming_relations: 引用本表的其他表
    - searchable_terms: 用于外部向量化检索的文本片段（表名+列名+枚举值+领域）

    外部 RAG 系统用法:
      1. 向量化 searchable_terms，建索引
      2. 用户提问时，向量召回 top-K profiles
      3. 用 profile 里的列和关系信息定位数据
    """
    # 预构建关系索引
    outgoing: Dict[str, List[RelationEdge]] = defaultdict(list)
    incoming: Dict[str, List[RelationEdge]] = defaultdict(list)
    for rel in graph.relations:
        if rel.confidence < min_confidence:
            continue
        outgoing[rel.from_table].append(rel)
        incoming[rel.to_table].append(rel)

    profiles = []

    for name in sorted(graph.tables.keys()):
        table = graph.tables[name]
        pk = table.primary_key

        # FK 列查找表
        fk_map: Dict[str, Tuple[str, str]] = {}
        for rel in outgoing.get(name, []):
            fk_map[rel.from_column] = (rel.to_table, rel.to_column)

        # 列详情
        columns = []
        for col in table.columns:
            cn = col['name']
            is_fk = cn in fk_map
            col_info = {
                "name": cn,
                "dtype": col.get('dtype', '?'),
                "is_pk": cn == pk,
                "is_fk": is_fk,
            }
            if is_fk:
                col_info["fk_target"] = f"{fk_map[cn][0]}.{fk_map[cn][1]}"

            # 枚举值
            if cn in (table.enum_columns or {}):
                col_info["is_enum"] = True
                vals = table.enum_columns[cn]
                col_info["enum_values"] = vals[:50]  # 限制大小
            else:
                col_info["is_enum"] = False

            # 样本值（profile 只需少量代表性值，控制文件体积）
            sv = col.get('sample_values')
            if sv:
                col_info["sample_values"] = sv[:8]

            columns.append(col_info)

        # 关系
        out_rels = [{
            "target_table": r.to_table,
            "local_column": r.from_column,
            "remote_column": r.to_column,
            "join": f"{name}.{r.from_column} = {r.to_table}.{r.to_column}",
            "confidence": round(r.confidence, 3),
            "type": r.relation_type,
        } for r in sorted(outgoing.get(name, []),
                          key=lambda x: -x.confidence)]

        in_rels = [{
            "source_table": r.from_table,
            "local_column": r.to_column,
            "remote_column": r.from_column,
            "join": f"{r.from_table}.{r.from_column} = {name}.{r.to_column}",
            "confidence": round(r.confidence, 3),
            "type": r.relation_type,
        } for r in sorted(incoming.get(name, []),
                          key=lambda x: -x.confidence)]

        # 生成可检索文本（供外部向量化）
        searchable_parts = [
            name,
            table.domain_label or "",
            Path(table.file_path).stem,
        ]
        # 中文同义词和 domain 中文名
        domain = table.domain_label or ""
        if domain:
            cn_names = _DOMAIN_CN_NAMES.get(domain, [])
            searchable_parts.extend(cn_names)
            cn_synonyms = _get_cn_synonyms(name)
            searchable_parts.extend(cn_synonyms)
        # 列名
        searchable_parts.extend(c['name'] for c in table.columns)
        # 列语义描述
        if pk:
            searchable_parts.append(f"主键:{pk}")
        for fk_col, (fk_tgt_table, fk_tgt_col) in fk_map.items():
            searchable_parts.append(f"引用{fk_tgt_table}")
        # 表规模描述
        if table.row_count > 5000:
            searchable_parts.append("大表")
        elif table.row_count > 500:
            searchable_parts.append("中表")
        else:
            searchable_parts.append("小表")
        # 枚举值（文本类型的，如阵营名、品质名等）
        for cn, vals in (table.enum_columns or {}).items():
            for v in vals[:30]:
                sv = str(v)
                if not sv.replace('.', '').replace('-', '').isdigit():
                    searchable_parts.append(sv)
        # 关联表名
        searchable_parts.extend(r.to_table for r in outgoing.get(name, []))
        searchable_parts.extend(r.from_table for r in incoming.get(name, []))

        searchable_text = " ".join(dict.fromkeys(
            p for p in searchable_parts if p))  # 去重保序

        profile = {
            "table_name": name,
            "domain": table.domain_label or "other",
            "file": Path(table.file_path).name,
            "sheet": table.sheet_name,
            "row_count": table.row_count,
            "primary_key": pk,
            "columns": columns,
            "outgoing_relations": out_rels,
            "incoming_relations": in_rels,
            "searchable_text": searchable_text,
        }
        profiles.append(profile)

    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            for profile in profiles:
                f.write(json.dumps(profile, ensure_ascii=False, default=str) + "\n")

    return profiles


# ──────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────

def _write_json(output_path: str, data: dict):
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1, default=str)

