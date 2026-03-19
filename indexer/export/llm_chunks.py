#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM 紧凑摘要导出

将 SchemaGraph 转换为面向 LLM/RAG 的紧凑文本 Chunk，
每张表约 200-400 tokens，方便向量化召回。

导出格式（Markdown）：
```
## 表: hero_base [hero]
- 文件: hero_base.xlsx
- 行数: 320 | 列数: 15 | 主键: id
- 列: id(int), name(str), quality(int), camp_id→camp_base.id, skill_id→skill_base.id, ...
- 关联: → camp_base(camp_id→id), → skill_base(skill_id→id), ← hero_equip(hero_id→id)
```
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from collections import defaultdict

from indexer.models import SchemaGraph
from indexer.export.atomic_write import (
    atomic_write_json, atomic_write_jsonl, atomic_write_text,
)

# 超过此列数的表触发列组拆分，避免 LLM 上下文中看不到后半部分列
_WIDE_TABLE_COL_THRESHOLD = 30
# 每个列组最多包含的列数
_GROUP_MAX_COLS = 20


def _group_columns_for_wide_table(
    table, fk_map: Dict[str, Tuple[str, str]]
) -> List[Tuple[str, List[str]]]:
    """
    将宽表的列按语义分组，每组返回 (组标签, 列名列表)。

    分组策略：
    1. 外键列单独成一组（类型统一，方便 RAG 识别关联关系）
    2. 剩余非外键列按位置顺序分组，每组 _GROUP_MAX_COLS 列
       - 第一组包含主键，作为"基础信息"
    """
    pk = table.primary_key
    all_col_names = [c['name'] for c in table.columns]

    fk_cols = [cn for cn in all_col_names if cn in fk_map]
    non_fk_cols = [cn for cn in all_col_names if cn not in fk_map]

    groups: List[Tuple[str, List[str]]] = []

    # 分割非外键列为若干组
    remaining = list(non_fk_cols)
    group_idx = 1
    while remaining:
        batch = remaining[:_GROUP_MAX_COLS]
        remaining = remaining[_GROUP_MAX_COLS:]
        if group_idx == 1 and pk:
            label = "基础信息"
        else:
            label = f"属性组{group_idx}"
        groups.append((label, batch))
        group_idx += 1

    # 外键列独立成一组
    if fk_cols:
        groups.append(("外键引用", fk_cols))

    return groups


def export_schema_summary(graph: SchemaGraph,
                          output_path: Optional[str] = None,
                          analysis=None) -> str:
    """
    生成轻量 schema 摘要（按业务域分组的表名列表），约 500 tokens。
    用于 RAG 意图提取步骤注入 LLM prompt。

    Args:
        graph: 已构建的 SchemaGraph
        output_path: 可选，输出到文件
        analysis: AnalysisResult（可选，追加分析洞察）

    Returns:
        摘要文本
    """
    domain_tables: dict[str, list[str]] = {}
    for name, t in graph.tables.items():
        domain = t.domain_label or "other"
        domain_tables.setdefault(domain, []).append(name)

    lines = [
        f"# Schema Summary — {len(graph.tables)} tables, {len(graph.relations)} relations",
        "",
        "可用配置表（按业务域分组）：",
    ]
    for domain in sorted(domain_tables.keys()):
        tables = sorted(domain_tables[domain])
        lines.append(f"[{domain}] {', '.join(tables)}")

    # 追加分析洞察
    if analysis:
        lines.append("")
        lines.append("## 分析洞察")
        # 核心枢纽表 Top5
        if analysis.centrality:
            top5 = sorted(analysis.centrality.items(),
                          key=lambda x: x[1], reverse=True)[:5]
            top_str = ", ".join(f"{n}({s:.1f})" for n, s in top5)
            lines.append(f"核心枢纽表 Top5: {top_str}")
        # 孤立表
        if analysis.orphans:
            lines.append(
                f"孤立表({len(analysis.orphans)}): "
                + ", ".join(sorted(analysis.orphans)[:15])
                + ("..." if len(analysis.orphans) > 15 else "")
            )
        # 循环依赖
        if analysis.cycles:
            lines.append(f"循环依赖: {len(analysis.cycles)} 个")
        else:
            lines.append("循环依赖: 无")
        # 业务模块数
        if analysis.modules:
            lines.append(f"业务模块数: {len(analysis.modules)}")

    text = "\n".join(lines) + "\n"

    if output_path:
        atomic_write_text(output_path, text)

    return text


def _build_col_part(cn: str, dt: str, sv: list, pk: str,
                    fk_map: Dict, enum_columns: Dict,
                    stats: Dict = None, pack_info: Dict = None) -> str:
    """将单列信息格式化为摘要字符串。

    pack 列格式：skill_ids(pack|int)→skill_base.id  或  skill_ids(pack|int)[101~5000]
    数值范围优先使用 stats.min/max（精确，来自全量数据）。
    """
    # Pack 数组列：优先标注 pack 类型，再标注 FK 目标
    if pack_info and pack_info.get('is_pack'):
        sep = pack_info['pack_separator']
        elem_dt = pack_info['pack_element_dtype']
        pack_tag = f"pack{sep}{elem_dt}"
        if cn in fk_map:
            tt, tc = fk_map[cn]
            return f"{cn}({pack_tag})→{tt}.{tc}"
        elems = pack_info.get('pack_element_samples', [])
        if elems and elem_dt == 'int':
            return f"{cn}({pack_tag})[{elems[0]}~{elems[-1]}]"
        return f"{cn}({pack_tag})"

    if cn in fk_map:
        tt, tc = fk_map[cn]
        return f"{cn}({dt})→{tt}.{tc}"

    if cn == pk:
        if dt == 'int' and stats:
            return f"{cn}({dt})[{stats['min']}~{stats['max']}]"
        if dt == 'int' and sv and len(sv) >= 2:
            return f"{cn}({dt})[{sv[0]}~{sv[-1]}]"
        return f"{cn}({dt})"

    if cn in (enum_columns or {}):
        evals = enum_columns[cn]
        text_vals = [str(v) for v in evals[:4]
                     if not str(v).replace('.', '').replace('-', '').isdigit()]
        if text_vals:
            return f"{cn}({dt})[{','.join(text_vals)}]"
        if len(evals) <= 10:
            return f"{cn}({dt})[{','.join(str(v) for v in evals[:6])}]"
        return f"{cn}({dt})"

    # 普通数值列：展示值范围，帮助 LLM 判断量纲和类型
    if dt in ('int', 'float') and stats:
        lo, hi = stats['min'], stats['max']
        if lo != hi:
            return f"{cn}({dt})[{lo}~{hi}]"

    return f"{cn}({dt})"


def _build_rel_str(outgoing, incoming, name: str,
                   max_relations_per_dir: int) -> str:
    """构建关联摘要字符串。"""
    _HIGH_CONF = 0.8
    out_rels = sorted(outgoing.get(name, []), key=lambda x: -x[3])
    in_rels = sorted(incoming.get(name, []), key=lambda x: -x[3])

    rel_parts_certain = []
    rel_parts_likely = []

    for fc, tt, tc, conf, _ in out_rels[:max_relations_per_dir]:
        entry = f"→ {tt}({fc}→{tc} @{conf})"
        if conf >= _HIGH_CONF:
            rel_parts_certain.append(entry)
        else:
            rel_parts_likely.append(entry)
    out_extra = len(out_rels) - max_relations_per_dir
    if out_extra > 0:
        rel_parts_likely.append(f"...+{out_extra}条出向")

    for ft, fc, tc, conf, _ in in_rels[:max_relations_per_dir]:
        entry = f"← {ft}({fc}→{tc} @{conf})"
        if conf >= _HIGH_CONF:
            rel_parts_certain.append(entry)
        else:
            rel_parts_likely.append(entry)
    in_extra = len(in_rels) - max_relations_per_dir
    if in_extra > 0:
        rel_parts_likely.append(f"...+{in_extra}条入向")

    rel_lines = []
    if rel_parts_certain:
        rel_lines.append(f"[确定] {', '.join(rel_parts_certain)}")
    if rel_parts_likely:
        rel_lines.append(f"[可能] {', '.join(rel_parts_likely)}")
    return " | ".join(rel_lines) if rel_lines else "无"


def export_llm_chunks(graph: SchemaGraph,
                      output_path: Optional[str] = None,
                      min_confidence: float = 0.65,
                      max_relations_per_dir: int = 10,
                      analysis=None) -> List[str]:
    """
    将图谱导出为 LLM 紧凑文本块列表。

    宽表（列数 > _WIDE_TABLE_COL_THRESHOLD）自动拆分为多个列组 chunk，
    每组 _GROUP_MAX_COLS 列，保证所有列对 LLM 可见，不再截断为 "...+N列"。

    Args:
        graph: 已构建的 SchemaGraph
        output_path: 可选，输出到文件（.md 或 .jsonl）
        min_confidence: 关系最低置信度阈值
        max_relations_per_dir: 每个方向（出/入）最多导出的关系数
        analysis: AnalysisResult（可选）

    Returns:
        chunk 字符串列表（宽表会产生多个 chunk）
    """
    # 预构建关系索引：table → outgoing / incoming
    outgoing: Dict[str, list] = defaultdict(list)
    incoming: Dict[str, list] = defaultdict(list)
    for rel in graph.relations:
        if rel.confidence < min_confidence:
            continue
        outgoing[rel.from_table].append((
            rel.from_column, rel.to_table, rel.to_column,
            rel.confidence, rel.discovery_method
        ))
        incoming[rel.to_table].append((
            rel.from_table, rel.from_column, rel.to_column,
            rel.confidence, rel.discovery_method
        ))

    chunks = []
    # JSONL 模式下 records 保存结构化元数据 + text
    # 字段：id, table_name, chunk_type, chunk_group, text
    #   id          — 向量库主键（向后兼容格式：table 或 table__gN）
    #   table_name  — 始终等于原始表名（消费侧无需解析 id）
    #   chunk_type  — "table"（窄表完整 chunk）| "table_group"（宽表列组 chunk）
    #   chunk_group — 列组序号（窄表为 null，宽表从 1 开始）
    records = []

    for name in sorted(graph.tables.keys()):
        table = graph.tables[name]
        domain = table.domain_label or "other"
        pk = table.primary_key or "-"
        col_count = len(table.columns)
        row_count = table.row_count
        file_name = Path(table.file_path).name

        # FK 映射：本表出向关系 column → (target_table, target_col)
        fk_map: Dict[str, Tuple[str, str]] = {
            fc: (tt, tc) for fc, tt, tc, _, _ in outgoing.get(name, [])
        }

        # 关联摘要（所有 chunk 共享同一份关联描述）
        rel_str = _build_rel_str(outgoing, incoming, name, max_relations_per_dir)

        # 分析标签（所有 chunk 共享）
        analysis_line = ""
        if analysis:
            tags = []
            if analysis.orphans and name in analysis.orphans:
                tags.append("孤立表")
            if analysis.centrality and analysis.centrality.get(name, 0) > 0:
                tags.append(f"中心性:{analysis.centrality[name]:.1f}")
            if analysis.modules:
                for mod in analysis.modules:
                    if name in mod:
                        neighbors = sorted(n for n in mod if n != name)[:8]
                        if neighbors:
                            tags.append(f"同模块: {', '.join(neighbors)}")
                        break
            if tags:
                analysis_line = f"- 标注: {' | '.join(tags)}\n"

        # 枚举提示（只在第一个 chunk 中展示）
        enum_hint = ""
        if table.enum_columns:
            hints = []
            for ecol, evals in list(table.enum_columns.items())[:3]:
                text_vals = [str(v) for v in evals[:5]
                             if not str(v).replace('.', '').replace('-', '').isdigit()]
                if text_vals:
                    hints.append(f"{ecol}=[{','.join(text_vals[:4])}]")
            if hints:
                enum_hint = f"- 枚举: {'; '.join(hints)}\n"

        # ── 窄表（≤ 阈值列）：保持原有单 chunk 格式 ──
        if col_count <= _WIDE_TABLE_COL_THRESHOLD:
            col_parts = []
            for col in table.columns:
                cn = col['name']
                dt = col.get('dtype', '?')
                sv = col.get('sample_values', [])
                col_parts.append(_build_col_part(
                    cn, dt, sv, pk, fk_map, table.enum_columns,
                    stats=col.get('stats'), pack_info=col.get('pack_info')))
            col_str = ", ".join(col_parts)

            chunk = (
                f"## 表: {name} [{domain}]\n"
                f"- 文件: {file_name} | sheet: {table.sheet_name}\n"
                f"- 行数: {row_count} | 列数: {col_count} | 主键: {pk}\n"
                f"- 列: {col_str}\n"
                f"{enum_hint}"
                f"- 关联: {rel_str}\n"
                f"{analysis_line}"
            )
            chunks.append(chunk)
            records.append({
                "id": name,
                "table_name": name,
                "chunk_type": "table",
                "chunk_group": None,
                "text": chunk,
            })

        # ── 宽表（> 阈值列）：按列组拆分为多个 chunk ──
        else:
            col_groups = _group_columns_for_wide_table(table, fk_map)
            col_lookup = {c['name']: c for c in table.columns}
            total_groups = len(col_groups)

            for g_idx, (group_label, group_col_names) in enumerate(col_groups, start=1):
                col_parts = []
                for cn in group_col_names:
                    col = col_lookup.get(cn, {})
                    dt = col.get('dtype', '?')
                    sv = col.get('sample_values', [])
                    col_parts.append(_build_col_part(
                        cn, dt, sv, pk, fk_map, table.enum_columns,
                        stats=col.get('stats'), pack_info=col.get('pack_info')))
                col_str = ", ".join(col_parts)

                # 第一个 chunk 包含枚举提示和分析标签
                extra = (enum_hint if g_idx == 1 else "") + (analysis_line if g_idx == 1 else "")

                chunk = (
                    f"## 表: {name} [{domain}] — {group_label} ({g_idx}/{total_groups})\n"
                    f"- 文件: {file_name} | sheet: {table.sheet_name}\n"
                    f"- 行数: {row_count} | 总列数: {col_count} | 主键: {pk} | "
                    f"本组列数: {len(group_col_names)}\n"
                    f"- 列: {col_str}\n"
                    f"{extra}"
                    f"- 关联: {rel_str}\n"
                )
                chunks.append(chunk)
                chunk_id = name if total_groups == 1 else f"{name}__g{g_idx}"
                records.append({
                    "id": chunk_id,
                    "table_name": name,
                    "chunk_type": "table_group",
                    "chunk_group": g_idx,
                    "text": chunk,
                })

    # 写文件
    if output_path:
        p = Path(output_path)
        if p.suffix == '.jsonl':
            atomic_write_jsonl(output_path, records)
        else:
            text = (
                f"# Schema Graph LLM Export\n"
                f"# {len(records)} chunks from {len(graph.tables)} tables, "
                f"{len(graph.relations)} relations\n\n"
                + "\n".join(chunks) + "\n"
            )
            atomic_write_text(output_path, text)

    return chunks


_FK_SUFFIXES_FOR_NORMALIZE = frozenset([
    '_id', '_key', '_code', '_no', '_idx', '_ref', '_type', '_num', '_index',
])

_CN_CHAR_PATTERN = __import__('re').compile(r'[\u4e00-\u9fff]+')


def export_column_index(graph: SchemaGraph,
                        output_path: Optional[str] = None) -> dict:
    """
    导出列名→所属表名的倒排索引（JSON 格式），用于 RAG 列级召回。

    增强:
    - _normalized: 去掉 FK 后缀的归一化列名 → 表名
    - _cn_segments: 中文列名按游戏实体词典切词 → 表名

    Args:
        graph: 已构建的 SchemaGraph
        output_path: 可选，输出到 JSON 文件

    Returns:
        包含 exact / _normalized / _cn_segments 的字典
    """
    index: dict[str, list[str]] = {}
    normalized: dict[str, list[str]] = {}
    cn_segments: dict[str, list[str]] = {}

    # 加载中文实体词典（用于切词）
    try:
        from indexer.discovery.game_dictionary import _BASE_CN_ENTITY_MAP
        cn_keywords = sorted(_BASE_CN_ENTITY_MAP.keys(), key=len, reverse=True)
    except ImportError:
        cn_keywords = []

    for name, table in graph.tables.items():
        for col in table.columns:
            col_name = col['name']
            index.setdefault(col_name, []).append(name)

            # 归一化: 去掉 FK 后缀
            norm = col_name.lower()
            for sfx in _FK_SUFFIXES_FOR_NORMALIZE:
                if norm.endswith(sfx) and len(norm) > len(sfx):
                    norm = norm[:-len(sfx)]
                    break
            if norm != col_name.lower():
                normalized.setdefault(norm, []).append(name)

            # 中文切词: 用实体词典做最长匹配
            if cn_keywords:
                cn_matches = _CN_CHAR_PATTERN.findall(col_name)
                cn_text = ''.join(cn_matches)
                if cn_text:
                    for kw in cn_keywords:
                        if kw in cn_text:
                            cn_segments.setdefault(kw, []).append(name)

    # 去重排序
    index = {k: sorted(set(v)) for k, v in sorted(index.items())}
    normalized = {k: sorted(set(v)) for k, v in sorted(normalized.items())}
    cn_segments = {k: sorted(set(v)) for k, v in sorted(cn_segments.items())}

    result = dict(index)
    if normalized:
        result["_normalized"] = normalized
    if cn_segments:
        result["_cn_segments"] = cn_segments

    if output_path:
        atomic_write_json(output_path, result)

    return result
