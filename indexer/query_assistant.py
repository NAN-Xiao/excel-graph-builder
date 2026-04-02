#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一查询助手

将当前工程已有的表画像、关系图、JOIN 路径、行级取数、全量数值分析
串成一个可直接调用的入口，支持：

1. 自然语言定位复杂表
2. 组装分析证据
3. 给目标表提供填表辅助建议
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from indexer.export import EvidenceAssembler
from indexer.retrieval.row_retriever import RowRetriever


_TOKEN_RE = re.compile(r'[\u4e00-\u9fff]{2,}|[a-zA-Z_]{2,}|\d+')


class QueryAssistant:
    """面向复杂表定位、分析与填表辅助的一站式入口。"""

    def __init__(self, graph_dir: str, data_root: str):
        self.graph_dir = Path(graph_dir)
        self.data_root = Path(data_root)

        self._profiles = self._load_jsonl(self.graph_dir / "table_profiles.jsonl")
        self._profile_map = {
            p.get("table_name"): p for p in self._profiles if p.get("table_name")
        }
        self._relation_graph = self._load_json(self.graph_dir / "relation_graph.json")
        self._column_index = self._load_json(self.graph_dir / "column_index.json")
        self._join_paths = self._load_json(self.graph_dir / "join_paths.json")
        self._evidence = EvidenceAssembler(
            profiles_path=str(self.graph_dir / "table_profiles.jsonl"),
            join_paths_path=str(self.graph_dir / "join_paths.json"),
            data_root=str(self.data_root),
        )
        self._retriever = RowRetriever(data_root=str(self.data_root))

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        items: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return items

    def is_ready(self) -> bool:
        return bool(self._profiles and self._relation_graph and self._join_paths)

    def locate_tables(
        self,
        query: str,
        top_k: int = 6,
        expand_hops: int = 1,
        min_confidence: float = 0.65,
    ) -> List[Dict[str, Any]]:
        """
        根据自然语言 query 定位候选表并做轻量扩表。
        """
        q_lower = query.lower()
        tokens = [t.lower() for t in _TOKEN_RE.findall(query)]
        scores: Dict[str, float] = defaultdict(float)
        reasons: Dict[str, List[str]] = defaultdict(list)

        for profile in self._profiles:
            table = profile.get("table_name")
            if not table:
                continue
            table_lower = table.lower()
            searchable = str(profile.get("searchable_text", "")).lower()
            file_name = str(profile.get("file", "")).lower()
            sheet = str(profile.get("sheet", "")).lower()
            domain = str(profile.get("domain", "")).lower()
            columns = {
                str(col.get("name", "")).lower()
                for col in profile.get("columns", [])
                if col.get("name")
            }

            if q_lower in table_lower or table_lower in q_lower:
                scores[table] += 20.0
                reasons[table].append("表名直接命中")

            for tok in tokens:
                if len(tok) < 2:
                    continue
                if tok == table_lower:
                    scores[table] += 16.0
                    reasons[table].append(f"词元命中表名:{tok}")
                elif tok in table_lower:
                    scores[table] += 12.0
                    reasons[table].append(f"表名包含:{tok}")

                if tok in file_name:
                    scores[table] += 8.0
                    reasons[table].append(f"文件名包含:{tok}")
                if tok in sheet:
                    scores[table] += 8.0
                    reasons[table].append(f"sheet包含:{tok}")
                if tok in domain:
                    scores[table] += 6.0
                    reasons[table].append(f"域命中:{tok}")
                if tok in searchable:
                    scores[table] += 4.0
                    reasons[table].append(f"检索文本命中:{tok}")
                if tok in columns:
                    scores[table] += 14.0
                    reasons[table].append(f"列名命中:{tok}")

        column_tables = self._tables_from_column_index(tokens)
        for table, matched_cols in column_tables.items():
            scores[table] += 15.0 + min(10.0, len(matched_cols) * 2.0)
            reasons[table].append(f"列倒排命中:{','.join(matched_cols[:4])}")

        seed_tables = [
            table for table, _ in sorted(scores.items(), key=lambda x: -x[1])[:top_k]
            if table in self._profile_map
        ]

        expanded_scores = dict(scores)
        relation_tables = self._relation_graph.get("tables", {})
        frontier = list(seed_tables)
        visited = set(frontier)

        for hop in range(expand_hops):
            next_frontier: List[str] = []
            for table in frontier:
                node = relation_tables.get(table, {})
                base_score = max(1.0, expanded_scores.get(table, 0.0))
                for nb in node.get("neighbors", []):
                    conf = float(nb.get("confidence", 0.0) or 0.0)
                    target = nb.get("table")
                    if not target or conf < min_confidence:
                        continue
                    bonus = base_score * 0.35 * conf / (hop + 1.0)
                    expanded_scores[target] = expanded_scores.get(target, 0.0) + bonus
                    reasons[target].append(f"关系扩展:{table}->{target}@{conf}")
                    if target not in visited:
                        visited.add(target)
                        next_frontier.append(target)
            frontier = next_frontier

        ranked = sorted(
            (
                {
                    "table": table,
                    "score": round(score, 3),
                    "domain": self._profile_map.get(table, {}).get("domain", "other"),
                    "file": self._profile_map.get(table, {}).get("file", ""),
                    "sheet": self._profile_map.get(table, {}).get("sheet", ""),
                    "reasons": list(dict.fromkeys(reasons.get(table, [])))[:6],
                }
                for table, score in expanded_scores.items()
                if table in self._profile_map and score > 0
            ),
            key=lambda x: (-x["score"], x["table"]),
        )
        return ranked[:top_k]

    def analyze_query(
        self,
        query: str,
        top_k: int = 5,
        analysis_mode: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        自动定位相关表并组装分析证据。
        """
        located = self.locate_tables(query=query, top_k=top_k)
        tables = [item["table"] for item in located]
        evidence = self._evidence.assemble(
            query=query,
            table_names=tables,
            analysis_mode=analysis_mode,
        ) if tables else {
            "query": query,
            "tables": [],
            "_meta": {"table_count": 0, "analysis_mode": bool(analysis_mode)},
        }
        return {
            "query": query,
            "located_tables": located,
            "evidence": evidence,
            "prompt_text": self._evidence.to_prompt_text(evidence) if tables else "",
        }

    def suggest_fill(
        self,
        table_name: str,
        query: str = "",
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """
        为目标表生成填表建议：
        - 相似样例行
        - 每列的候选值 / 外键信息 / 枚举信息
        """
        profile = self._profile_map.get(table_name)
        if not profile:
            raise KeyError(f"unknown table: {table_name}")

        predicates = self._retriever.generate_predicates(query, profile) if query else []
        block = self._retriever.fetch_rows(profile, predicates, max_rows=max_rows)
        rows = block.rows or []
        suggestions = []

        for col in profile.get("columns", []):
            cname = col.get("name")
            if not cname:
                continue
            values = [r.get(cname) for r in rows if r.get(cname) not in ("", None)]
            top_values = [v for v, _ in Counter(values).most_common(3)]
            suggestion: Dict[str, Any] = {
                "column": cname,
                "dtype": col.get("dtype"),
                "is_pk": bool(col.get("is_pk")),
                "is_fk": bool(col.get("is_fk")),
                "semantic_type": col.get("semantic_type"),
            }
            if col.get("is_fk"):
                suggestion["fk_target"] = col.get("fk_target")
            if col.get("is_enum"):
                suggestion["enum_values"] = (col.get("enum_values") or [])[:10]
            if col.get("sample_values"):
                suggestion["sample_values"] = (col.get("sample_values") or [])[:5]
            if top_values:
                suggestion["candidate_values"] = top_values
                suggestion["reason"] = "来自相似样例行的高频值"
            elif col.get("is_enum") and col.get("enum_values"):
                suggestion["candidate_values"] = (col.get("enum_values") or [])[:5]
                suggestion["reason"] = "枚举列候选"
            elif col.get("sample_values"):
                suggestion["candidate_values"] = (col.get("sample_values") or [])[:3]
                suggestion["reason"] = "历史样本值"
            suggestions.append(suggestion)

        return {
            "table": table_name,
            "query": query,
            "primary_key": profile.get("primary_key"),
            "file": profile.get("file"),
            "sheet": profile.get("sheet"),
            "predicates": [p.to_display() for p in predicates],
            "matched_rows": {
                "total": block.total_matched,
                "columns": block.columns_returned,
                "rows": rows,
            },
            "column_suggestions": suggestions,
        }

    def _tables_from_column_index(self, tokens: List[str]) -> Dict[str, List[str]]:
        matched: Dict[str, List[str]] = defaultdict(list)
        exact_index = self._column_index if isinstance(self._column_index, dict) else {}
        normalized_index = exact_index.get("_normalized", {}) or {}
        cn_segments = exact_index.get("_cn_segments", {}) or {}

        for tok in tokens:
            if len(tok) < 2:
                continue
            for table in exact_index.get(tok, []) or []:
                matched[table].append(tok)
            for table in normalized_index.get(tok, []) or []:
                matched[table].append(tok)
            for seg, tables in cn_segments.items():
                if seg and seg in tok:
                    for table in tables:
                        matched[table].append(seg)

        return matched
