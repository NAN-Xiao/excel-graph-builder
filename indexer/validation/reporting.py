#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
构建后完整性校验 / 回归报表 / 本地告警摘要。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


_REQUIRED_ARTIFACTS = (
    "schema_graph.json",
    "schema_graph.html",
    "schema_summary.txt",
    "llm_chunks.jsonl",
    "table_profiles.jsonl",
    "relation_graph.json",
    "join_paths.json",
    "rag_preview.json",
    "evidence_config.json",
)


@dataclass
class AlertItem:
    severity: str
    code: str
    title: str
    detail: str
    action_hint: str = ""


@dataclass
class ValidationReport:
    build_id: str
    build_dir: str
    generated_at: str
    status: str
    publish_allowed: bool
    switched_current: bool = False
    fallback_used: bool = False
    summary: Dict[str, Any] = field(default_factory=dict)
    alerts: List[AlertItem] = field(default_factory=list)
    regression_results: List[Dict[str, Any]] = field(default_factory=list)

    def max_severity(self) -> str:
        order = {"OK": -1, "P2": 0, "P1": 1, "P0": 2}
        if not self.alerts:
            return "OK"
        return max((a.severity for a in self.alerts), key=lambda s: order.get(s, -1))

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "build_id": self.build_id,
            "build_dir": self.build_dir,
            "generated_at": self.generated_at,
            "status": self.status,
            "publish_allowed": self.publish_allowed,
            "switched_current": self.switched_current,
            "fallback_used": self.fallback_used,
            "summary": self.summary,
            "alerts": [asdict(a) for a in self.alerts],
            "regression_results": self.regression_results,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Regression Report - {self.build_id}",
            "",
            f"- status: `{self.status}`",
            f"- publish_allowed: `{self.publish_allowed}`",
            f"- switched_current: `{self.switched_current}`",
            f"- fallback_used: `{self.fallback_used}`",
            f"- generated_at: `{self.generated_at}`",
            "",
            "## Summary",
        ]
        for k, v in self.summary.items():
            lines.append(f"- {k}: `{v}`")

        lines.append("")
        lines.append("## Alerts")
        if not self.alerts:
            lines.append("- none")
        else:
            for a in self.alerts:
                lines.append(f"- [{a.severity}] {a.title}: {a.detail}")
                if a.action_hint:
                    lines.append(f"  action: {a.action_hint}")

        lines.append("")
        lines.append("## Regression Results")
        if not self.regression_results:
            lines.append("- none")
        else:
            for r in self.regression_results:
                lines.append(
                    f"- {r.get('id','?')}: status=`{r.get('status','?')}` "
                    f"tables={r.get('table_count', 0)} analytical_tables={r.get('analytical_tables', 0)}"
                )
                if r.get("issues"):
                    for issue in r["issues"]:
                        lines.append(f"  issue: {issue}")
        lines.append("")
        return "\n".join(lines)


class BuildValidator:
    """对单次构建目录做完整性检查与最小回归。"""

    def __init__(self, data_root: str):
        self.data_root = data_root

    def validate(
        self,
        build_dir: str,
        build_id: str,
        previous_report_path: Optional[str] = None,
        regression_queries_path: Optional[str] = None,
    ) -> ValidationReport:
        build_path = Path(build_dir)
        previous = self._load_json(previous_report_path) if previous_report_path else None
        report = ValidationReport(
            build_id=build_id,
            build_dir=str(build_path),
            generated_at=datetime.now().isoformat(timespec="seconds"),
            status="OK",
            publish_allowed=True,
        )

        summary = self._build_summary(build_path)
        report.summary.update(summary)
        self._check_required_artifacts(build_path, report)
        self._compare_with_previous(summary, previous, report)
        self._run_regressions(build_path, regression_queries_path, report)

        max_sev = report.max_severity()
        report.status = max_sev
        report.publish_allowed = max_sev != "P0"
        return report

    def _build_summary(self, build_path: Path) -> Dict[str, Any]:
        meta = self._load_json(build_path / "meta.json") or {}
        join_meta = ((self._load_json(build_path / "join_paths.json") or {}).get("_meta") or {})
        analysis = self._load_json(build_path / "analysis.json") or {}
        return {
            "table_count": meta.get("table_count", 0),
            "relation_count": meta.get("relation_count", 0),
            "join_path_count": join_meta.get("total_paths", 0),
            "join_max_hops": join_meta.get("max_hops", 0),
            "module_count": len(analysis.get("modules", []) or []),
            "orphan_count": len(analysis.get("orphans", []) or []),
        }

    def _check_required_artifacts(self, build_path: Path, report: ValidationReport) -> None:
        missing = [name for name in _REQUIRED_ARTIFACTS if not (build_path / name).exists()]
        if missing:
            report.alerts.append(AlertItem(
                severity="P0",
                code="missing_artifacts",
                title="关键产物缺失",
                detail=f"缺少 {', '.join(missing)}",
                action_hint="检查导出阶段是否失败，重点查看对应 exporter 和目标目录权限。",
            ))

    def _compare_with_previous(
        self,
        summary: Dict[str, Any],
        previous: Optional[Dict[str, Any]],
        report: ValidationReport,
    ) -> None:
        if not previous:
            return
        prev_summary = previous.get("summary", {})
        prev_rel = prev_summary.get("relation_count") or 0
        prev_join = prev_summary.get("join_path_count") or 0
        prev_orphan = prev_summary.get("orphan_count") or 0

        cur_rel = summary.get("relation_count", 0)
        cur_join = summary.get("join_path_count", 0)
        cur_orphan = summary.get("orphan_count", 0)

        if prev_rel and cur_rel < prev_rel * 0.7:
            report.alerts.append(AlertItem(
                severity="P0",
                code="relation_drop",
                title="主图关系数异常暴跌",
                detail=f"relation_count: {prev_rel} -> {cur_rel}",
                action_hint="检查 containment / naming / abbreviation 策略结果，以及最近是否有批量改名。",
            ))
        elif prev_rel and cur_rel < prev_rel * 0.85:
            report.alerts.append(AlertItem(
                severity="P1",
                code="relation_drop_warn",
                title="主图关系数明显下降",
                detail=f"relation_count: {prev_rel} -> {cur_rel}",
                action_hint="检查本次变更表是否导致外键推断规则收缩。",
            ))

        if prev_join and cur_join < prev_join * 0.6:
            report.alerts.append(AlertItem(
                severity="P1",
                code="join_path_drop",
                title="JOIN 路径数量下降",
                detail=f"join_path_count: {prev_join} -> {cur_join}",
                action_hint="检查 join_paths 导出是否正常，及主图高置信关系是否减少。",
            ))

        if prev_orphan and cur_orphan > prev_orphan * 1.2:
            report.alerts.append(AlertItem(
                severity="P2",
                code="orphan_rise",
                title="孤立表数量上升",
                detail=f"orphan_count: {prev_orphan} -> {cur_orphan}",
                action_hint="检查新增表是否缺主键或缺可发现关系。",
            ))

    def _run_regressions(
        self,
        build_path: Path,
        regression_queries_path: Optional[str],
        report: ValidationReport,
    ) -> None:
        cfg_path = Path(regression_queries_path) if regression_queries_path else (build_path.parent / "regression_queries.json")
        if not cfg_path.exists():
            return

        cfg = self._load_json(cfg_path) or {}
        cases = cfg.get("queries", [])
        if not cases:
            return

        from indexer.export.evidence_assembler import EvidenceAssembler

        assembler = EvidenceAssembler(
            profiles_path=str(build_path / "table_profiles.jsonl"),
            join_paths_path=str(build_path / "join_paths.json"),
            data_root=self.data_root,
        )

        for case in cases:
            issues: List[str] = []
            query = case.get("query", "")
            table_names = case.get("table_names", [])
            required_tables = set(case.get("required_tables", []))
            require_analysis = bool(case.get("analysis_mode", False))
            ev = assembler.assemble(query=query, table_names=table_names, analysis_mode=require_analysis or None)

            schema_tables = {s.get("table") for s in ev.get("schema", [])}
            missing_tables = sorted(required_tables - schema_tables)
            if missing_tables:
                issues.append(f"missing required tables: {', '.join(missing_tables)}")
                report.alerts.append(AlertItem(
                    severity="P0",
                    code="regression_missing_table",
                    title=f"关键回归 query 缺表: {case.get('id', query[:30])}",
                    detail=", ".join(missing_tables),
                    action_hint="检查表是否改名/删除、扫描器是否跳过，或回归样例中的表配置是否过期。",
                ))

            analytical = ev.get("analytical_result", [])
            if require_analysis and not analytical:
                issues.append("analytical_result empty")
                report.alerts.append(AlertItem(
                    severity="P1",
                    code="analytical_empty",
                    title=f"分析结果为空: {case.get('id', query[:30])}",
                    detail=query,
                    action_hint="检查 query 是否命中数值列，以及 semantic_type / metric_tag 是否仍有效。",
                ))

            report.regression_results.append({
                "id": case.get("id", query[:40]),
                "status": "failed" if issues else "passed",
                "query": query,
                "table_count": len(ev.get("schema", [])),
                "analytical_tables": len(analytical),
                "issues": issues,
            })

    @staticmethod
    def _load_json(path: Optional[Any]) -> Optional[Dict[str, Any]]:
        if not path:
            return None
        p = Path(path)
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
