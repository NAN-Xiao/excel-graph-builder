#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG 预览资产导出

供静态前端和调试工具直接消费的轻量 JSON：
- 表级元数据
- 列级语义字段
- 关系摘要
- 图分析摘要
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from indexer.models import SchemaGraph
from indexer.export.atomic_write import atomic_write_json


def build_rag_preview(graph: SchemaGraph, analysis=None) -> Dict:
    tables = {}
    for name, table in graph.tables.items():
        cols = []
        for c in table.columns:
            item = {
                "name": c.get("name"),
                "dtype": c.get("dtype"),
            }
            for f in (
                "semantic_type", "domain_role", "metric_tag",
                "is_pk", "is_fk", "fk_target",
                "is_enum", "enum_values", "stats", "sample_values",
            ):
                if f in c and c[f] not in (None, False, [], {}):
                    item[f] = c[f]
            cols.append(item)

        tables[name] = {
            "table": name,
            "domain": table.domain_label or "other",
            "row_count": table.row_count,
            "primary_key": table.primary_key,
            "file": Path(table.file_path).name,
            "sheet": table.sheet_name,
            "columns": cols,
        }

    relations = [
        {
            "from": rel.from_table,
            "to": rel.to_table,
            "from_column": rel.from_column,
            "to_column": rel.to_column,
            "label": f"{rel.from_column} → {rel.to_column}",
            "confidence": round(rel.confidence, 4),
            "relation_type": rel.relation_type,
            "method": rel.discovery_method,
        }
        for rel in graph.relations
    ]

    analysis_data = {}
    if analysis is not None:
        analysis_data = {
            "cycles": [list(c) for c in (analysis.cycles or [])[:20]],
            "centrality_top": sorted(
                analysis.centrality.items(),
                key=lambda x: x[1], reverse=True
            )[:15] if analysis.centrality else [],
            "modules": [
                sorted(list(m))[:20] for m in (analysis.modules or [])[:20]
            ],
            "orphans": sorted(analysis.orphans or [])[:50],
            "critical_path": list(analysis.critical_path or []),
        }

    return {
        "_meta": {
            "table_count": len(graph.tables),
            "relation_count": len(graph.relations),
            "description": "供静态前端与 RAG 调试使用的轻量预览资产。",
        },
        "tables": tables,
        "relations": relations,
        "analysis": analysis_data,
    }


def export_rag_preview(graph: SchemaGraph, output_path: Optional[str] = None, analysis=None) -> Dict:
    data = build_rag_preview(graph, analysis=analysis)
    if output_path:
        atomic_write_json(output_path, data)
    return data
