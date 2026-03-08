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
                          output_path: Optional[str] = None) -> str:
    """
    生成轻量 schema 摘要（按业务域分组的表名列表），约 500 tokens。
    用于 RAG 意图提取步骤注入 LLM prompt。

    Args:
        graph: 已构建的 SchemaGraph
        output_path: 可选，输出到文件

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

    text = "\n".join(lines) + "\n"

    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text)

    return text


def export_llm_chunks(graph: SchemaGraph,
                      output_path: Optional[str] = None,
                      min_confidence: float = 0.6,
                      max_relations_per_dir: int = 10) -> List[str]:
    """
    将图谱导出为 LLM 紧凑文本块列表。

    Args:
        graph: 已构建的 SchemaGraph
        output_path: 可选，输出到文件（.md 或 .jsonl）
        min_confidence: 关系最低置信度阈值（低于此的不导出）
        max_relations_per_dir: 每个方向（出/入）最多导出的关系数

    Returns:
        每张表一个字符串的列表
    """
    # 预构建关系索引：table → outgoing / incoming
    # from_table → [(from_col, to_table, to_col, conf, method)]
    outgoing = defaultdict(list)
    # to_table → [(from_table, from_col, to_col, conf, method)]
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

    chunks = []

    for name in sorted(graph.tables.keys()):
        table = graph.tables[name]
        domain = table.domain_label or "other"
        pk = table.primary_key or "-"
        col_count = len(table.columns)
        row_count = table.row_count

        # 列摘要：列名(类型)，外键列标注 →target.col
        fk_map = {fc: (tt, tc) for fc, tt, tc, _, _ in outgoing.get(name, [])}
        col_parts = []
        for col in table.columns:
            cn = col['name']
            dt = col.get('dtype', '?')
            if cn in fk_map:
                tt, tc = fk_map[cn]
                col_parts.append(f"{cn}({dt})→{tt}.{tc}")
            else:
                col_parts.append(f"{cn}({dt})")
        # 限制展示列数
        if len(col_parts) > 25:
            col_str = ", ".join(col_parts[:25]) + f", ...+{len(col_parts)-25}列"
        else:
            col_str = ", ".join(col_parts)

        # 关联摘要（按置信度排序，限制数量）
        rel_parts = []
        out_rels = sorted(outgoing.get(name, []), key=lambda x: -x[3])
        in_rels = sorted(incoming.get(name, []), key=lambda x: -x[3])
        for fc, tt, tc, conf, _ in out_rels[:max_relations_per_dir]:
            rel_parts.append(f"→ {tt}({fc}→{tc} @{conf})")
        out_extra = len(out_rels) - max_relations_per_dir
        if out_extra > 0:
            rel_parts.append(f"...+{out_extra}条出向")
        for ft, fc, tc, conf, _ in in_rels[:max_relations_per_dir]:
            rel_parts.append(f"← {ft}({fc}→{tc} @{conf})")
        in_extra = len(in_rels) - max_relations_per_dir
        if in_extra > 0:
            rel_parts.append(f"...+{in_extra}条入向")
        rel_str = ", ".join(rel_parts) if rel_parts else "无"

        chunk = (
            f"## 表: {name} [{domain}]\n"
            f"- 文件: {Path(table.file_path).name} | sheet: {table.sheet_name}\n"
            f"- 行数: {row_count} | 列数: {col_count} | 主键: {pk}\n"
            f"- 列: {col_str}\n"
            f"- 关联: {rel_str}\n"
        )
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
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        else:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(f"# Schema Graph LLM Export\n")
                f.write(f"# {len(chunks)} tables, "
                        f"{len(graph.relations)} relations\n\n")
                for chunk in chunks:
                    f.write(chunk + "\n")

    return chunks
