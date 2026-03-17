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
from typing import List, Optional
from collections import defaultdict

from indexer.models import SchemaGraph


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
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text)

    return text


def export_llm_chunks(graph: SchemaGraph,
                      output_path: Optional[str] = None,
                      min_confidence: float = 0.65,
                      max_relations_per_dir: int = 10,
                      analysis=None) -> List[str]:
    """
    将图谱导出为 LLM 紧凑文本块列表。

    Args:
        graph: 已构建的 SchemaGraph
        output_path: 可选，输出到文件（.md 或 .jsonl）
        min_confidence: 关系最低置信度阈值（低于此的不导出）
        max_relations_per_dir: 每个方向（出/入）最多导出的关系数
        analysis: AnalysisResult（可选）

    Returns:
        每张表一个字符串的列表
    """
    # 预构建关系索引：table → outgoing / incoming
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
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

    _HIGH_CONF = 0.8

    chunks = []

    for name in sorted(graph.tables.keys()):
        table = graph.tables[name]
        domain = table.domain_label or "other"
        pk = table.primary_key or "-"
        col_count = len(table.columns)
        row_count = table.row_count

        # 列摘要（含值域信息）
        fk_map = {fc: (tt, tc) for fc, tt, tc, _, _ in outgoing.get(name, [])}
        col_parts = []
        for col in table.columns:
            cn = col['name']
            dt = col.get('dtype', '?')
            sv = col.get('sample_values', [])

            if cn in fk_map:
                tt, tc = fk_map[cn]
                part = f"{cn}({dt})→{tt}.{tc}"
            elif cn == pk and sv:
                if dt == 'int' and len(sv) >= 2:
                    part = f"{cn}({dt})[{sv[0]}~{sv[-1]},共{len(sv)}]"
                else:
                    part = f"{cn}({dt})"
            elif cn in (table.enum_columns or {}):
                evals = table.enum_columns[cn]
                text_vals = [str(v) for v in evals[:4]
                             if not str(v).replace('.', '').replace('-', '').isdigit()]
                if text_vals:
                    part = f"{cn}({dt})[{','.join(text_vals)}]"
                elif len(evals) <= 10:
                    part = f"{cn}({dt})[{','.join(str(v) for v in evals[:6])}]"
                else:
                    part = f"{cn}({dt})"
            else:
                part = f"{cn}({dt})"
            col_parts.append(part)
        if len(col_parts) > 25:
            col_str = ", ".join(col_parts[:25]) + f", ...+{len(col_parts)-25}列"
        else:
            col_str = ", ".join(col_parts)

        # 关联摘要 — 分层: [确定] conf >= 0.8, [可能] 0.65 <= conf < 0.8
        out_rels = sorted(outgoing.get(name, []), key=lambda x: -x[3])
        in_rels = sorted(incoming.get(name, []), key=lambda x: -x[3])

        rel_parts_certain = []
        rel_parts_likely = []

        for fc, tt, tc, conf, _ in out_rels[:max_relations_per_dir]:
            tag = "确定" if conf >= _HIGH_CONF else "可能"
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
        rel_str = " | ".join(rel_lines) if rel_lines else "无"

        # 代表性枚举值描述
        enum_hint = ""
        if table.enum_columns:
            hints = []
            for ecol, evals in list(table.enum_columns.items())[:2]:
                text_vals = [str(v) for v in evals[:5]
                             if not str(v).replace('.', '').replace('-', '').isdigit()]
                if text_vals:
                    hints.append(f"{ecol}=[{','.join(text_vals[:3])}]")
            if hints:
                enum_hint = f"- 枚举: {'; '.join(hints)}\n"

        chunk = (
            f"## 表: {name} [{domain}]\n"
            f"- 文件: {Path(table.file_path).name} | sheet: {table.sheet_name}\n"
            f"- 行数: {row_count} | 列数: {col_count} | 主键: {pk}\n"
            f"- 列: {col_str}\n"
            f"{enum_hint}"
            f"- 关联: {rel_str}\n"
        )
        # 追加分析标签
        if analysis:
            tags = []
            if analysis.orphans and name in analysis.orphans:
                tags.append("孤立表")
            if analysis.centrality and analysis.centrality.get(name, 0) > 0:
                tags.append(
                    f"中心性:{analysis.centrality[name]:.1f}")
            # 同模块邻居
            if analysis.modules:
                for mod in analysis.modules:
                    if name in mod:
                        neighbors = sorted(
                            n for n in mod if n != name)[:8]
                        if neighbors:
                            tags.append(
                                f"同模块: {', '.join(neighbors)}")
                        break
            if tags:
                chunk += f"- 标注: {' | '.join(tags)}\n"
        chunks.append(chunk)

    # 写文件
    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == '.jsonl':
            with open(p, 'w', encoding='utf-8') as f:
                for i, (name, chunk) in enumerate(
                        zip(sorted(graph.tables.keys()), chunks)):
                    obj = {"id": name, "text": chunk}
                    f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        else:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(f"# Schema Graph LLM Export\n")
                f.write(f"# {len(chunks)} tables, "
                        f"{len(graph.relations)} relations\n\n")
                for chunk in chunks:
                    f.write(chunk + "\n")

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
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=1)

    return result
