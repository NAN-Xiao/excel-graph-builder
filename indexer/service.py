#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Index Service - 索引构建服务入口

完全独立进程，不依赖主应用的 core 模块
"""

import sys
import argparse
import signal
import time
import threading
from pathlib import Path
from typing import Optional, Set

from indexer.storage import JsonGraphStorage
from indexer.scheduler import BuildScheduler
from indexer.watcher import FileWatcher
from indexer.core.builder import GraphBuilder
from indexer.models import SchemaGraph
from indexer import SimpleLogger


class IndexService:
    """索引构建服务"""

    # 文件变化后延迟 3 秒执行增量构建（防抖）
    INCREMENTAL_DELAY = 3.0

    def __init__(self, data_root: str, storage_dir: str = "./graph", html_dir: str = "./graph", offline_html: bool = True):
        self.data_root = Path(data_root)
        self.storage = JsonGraphStorage(storage_dir)
        self.scheduler = BuildScheduler()
        self.watcher: Optional[FileWatcher] = None
        # 使用新的 GraphBuilder
        from indexer.core.config import BuildConfig
        config = BuildConfig(
            data_root=str(self.data_root),
            html_dir=html_dir,
            offline_html=offline_html
        )
        self.builder = GraphBuilder(config)
        self.logger = SimpleLogger()

        self.current_graph: Optional[SchemaGraph] = None

        # 待处理的变更
        self._pending_changes: Set[str] = set()     # 新增/修改的表
        self._pending_deletions: Set[str] = set()   # 删除的表

        # 并发控制
        self._is_building = False
        self._build_lock = threading.Lock()

        self._load_existing()

    def _load_existing(self):
        """加载已有图谱"""
        self.current_graph = self.storage.load()
        if self.current_graph:
            stats = self.current_graph.get_stats()
            self.logger.success(
                f"已加载现有图谱: {stats['table_count']} 表, "
                f"{stats['relation_count']} 关系"
            )
        else:
            self.logger.info("未找到现有图谱，需要首次构建")

    def build_full(self, incremental: bool = False) -> bool:
        """
        执行全量/增量构建

        Returns:
            bool: 是否成功
        """
        mode_str = "增量" if incremental else "全量"
        self.logger.info(f"开始{mode_str}构建...")

        try:
            graph, result = self.builder.build_full_graph(
                incremental=incremental,
                existing_graph=self.current_graph,
                deleted_tables=self._pending_deletions if incremental else None
            )

            if self.storage.save(graph):
                self.current_graph = graph
                # 清空待处理队列
                self._pending_changes.clear()
                self._pending_deletions.clear()

                self.logger.success(f"构建完成 | {result.summary()}")

                # 自动导出 LLM 资产（传入分析结果）
                self._export_llm_assets(analysis=result.analysis)

                return True
            else:
                self.logger.error("保存图谱失败")
                return False

        except Exception as e:
            self.logger.error(f"构建失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _export_llm_assets(self, analysis=None):
        """构建完成后自动导出 LLM/RAG 所需资产"""
        if not self.current_graph:
            return
        try:
            from indexer.export import (
                export_llm_chunks, export_schema_summary,
                export_column_index,
                export_relation_graph, export_join_paths,
                export_table_profiles,
                export_cell_locator,
                export_analysis,
                export_value_index, export_domain_graph,
                export_enum_cross_ref,
            )
            storage_dir = Path(self.storage.data_dir)

            # ── Schema 层 ──
            # 1. schema_summary.txt — 轻量表名摘要，~500 tokens，RAG 意图提取
            summary_path = storage_dir / "schema_summary.txt"
            export_schema_summary(self.current_graph, str(summary_path),
                                  analysis=analysis)

            # 2. llm_chunks.jsonl — 每表一行 JSON，向量化召回
            jsonl_path = storage_dir / "llm_chunks.jsonl"
            export_llm_chunks(self.current_graph, str(jsonl_path),
                              analysis=analysis)

            # 3. llm_chunks.md — Markdown 格式，人工检查
            md_path = storage_dir / "llm_chunks.md"
            export_llm_chunks(self.current_graph, str(md_path),
                              analysis=analysis)

            # 4. column_index.json — 列名→表名倒排索引
            col_idx_path = storage_dir / "column_index.json"
            export_column_index(self.current_graph, str(col_idx_path))

            # ── RAG 关系层 ──
            # 5. relation_graph.json — 邻接表 + JOIN 条件
            rel_graph_path = storage_dir / "relation_graph.json"
            export_relation_graph(self.current_graph, str(rel_graph_path))

            # 6. join_paths.json — 预计算表间 JOIN 路径（≤1 跳，控制文件体积）
            join_path_path = storage_dir / "join_paths.json"
            export_join_paths(self.current_graph, str(join_path_path),
                              max_hops=1)

            # 7. table_profiles.jsonl — 每表富元数据 profile
            profiles_path = storage_dir / "table_profiles.jsonl"
            export_table_profiles(self.current_graph, str(profiles_path))

            # 8. cell_locator.json — 单元格定位索引（表名→文件→行号→列号）
            cell_loc_path = storage_dir / "cell_locator.json"
            export_cell_locator(self.current_graph, str(cell_loc_path))

            # 9. analysis.json — 图算法分析结果（centrality/modules/orphans）
            analysis_path = storage_dir / "analysis.json"
            export_analysis(analysis, str(analysis_path))

            # 10. value_index.json — 跨表值反查索引
            value_idx_path = storage_dir / "value_index.json"
            export_value_index(self.current_graph, str(value_idx_path))

            # 11. domain_graph.json — 域级关系图
            domain_graph_path = storage_dir / "domain_graph.json"
            export_domain_graph(self.current_graph, str(domain_graph_path))

            # 12. enum_cross_ref.json — 枚举值交叉索引
            enum_xref_path = storage_dir / "enum_cross_ref.json"
            export_enum_cross_ref(self.current_graph, str(enum_xref_path))

            self.logger.success(
                f"LLM/RAG 资产已导出 → {summary_path.name}, "
                f"{jsonl_path.name}, {col_idx_path.name}, "
                f"{rel_graph_path.name}, {join_path_path.name}, "
                f"{profiles_path.name}, {cell_loc_path.name}, "
                f"{analysis_path.name}, {value_idx_path.name}, "
                f"{domain_graph_path.name}, {enum_xref_path.name}"
            )
        except Exception as e:
            self.logger.error(f"LLM/RAG 资产导出失败: {e}")

    def _do_incremental_build(self):
        """执行真正的增量构建（由延迟任务调用）"""
        with self._build_lock:
            if self._is_building:
                self.logger.info("已有构建任务进行中，跳过本次增量构建")
                return

            if not self._pending_changes and not self._pending_deletions:
                self.logger.debug("没有待处理的变更，跳过构建")
                return

            self._is_building = True

        try:
            self.logger.info(
                f"执行增量构建: {len(self._pending_changes)} 个变更, "
                f"{len(self._pending_deletions)} 个删除"
            )
            self.build_full(incremental=True)
        finally:
            with self._build_lock:
                self._is_building = False

    def on_file_changed(self, file_path: str, event_type: str):
        """
        文件变化回调

        区分处理：
        - created/modified: 加入变更队列，触发延迟构建
        - deleted: 加入删除队列，触发延迟构建
        """
        table_name = Path(file_path).stem

        if event_type == 'deleted':
            self._pending_deletions.add(table_name)
            self.logger.info(f"检测到文件删除: {table_name}")
        else:
            self._pending_changes.add(table_name)
            self.logger.info(f"检测到文件{event_type}: {table_name}")

        # 触发延迟增量构建（防抖：3 秒内多次变化只执行一次）
        if self.scheduler._running:
            self.scheduler.trigger_delayed('incremental_build')

    def start_scheduler(self, schedule_type: str = "daily", **kwargs):
        """启动定时调度"""
        if schedule_type == "daily":
            hour = kwargs.get("hour", 2)
            minute = kwargs.get("minute", 0)
            self.scheduler.add_daily_job(
                self.build_full, hour=hour, minute=minute)
        elif schedule_type == "interval":
            minutes = kwargs.get("minutes", 60)
            self.scheduler.add_interval_job(self.build_full, minutes=minutes)

        # 注册延迟增量构建任务（防抖机制）
        self.scheduler.add_delayed_task(
            'incremental_build',
            self._do_incremental_build,
            self.INCREMENTAL_DELAY
        )

        self.scheduler.start(blocking=False)

    def start_watcher(self):
        """启动文件监控"""
        self.watcher = FileWatcher(self.data_root, self.on_file_changed)
        return self.watcher.start()

    def run(self, daemon: bool = False):
        """运行服务"""
        print("=" * 60)
        print("  Excel Graph Builder")
        print("=" * 60)
        print(f"  数据目录: {self.data_root}")
        print(f"  输出目录: {self.storage.data_dir}")
        if daemon:
            jobs = schedule_mod.get_jobs() if 'schedule_mod' not in dir() else []
            try:
                import schedule as schedule_mod
                jobs = schedule_mod.get_jobs()
            except Exception:
                jobs = []
            if jobs:
                print(f"  调度任务: {len(jobs)} 个")
                for j in jobs:
                    print(f"    - {j}")
            if self.watcher:
                print(f"  文件监控: 已启用")
        print("=" * 60)

        if daemon:
            print("\n守护模式运行中，按 Ctrl+C 停止\n")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.shutdown()
        else:
            self.build_full(incremental=True)

    def shutdown(self):
        """优雅关闭"""
        self.logger.info("正在关闭...")

        # 取消待执行的延迟任务
        if self.scheduler._running:
            self.scheduler.cancel_delayed('incremental_build')
            self.scheduler.stop()

        if self.watcher:
            self.watcher.stop()

        self.logger.success("已关闭")


def main():
    parser = argparse.ArgumentParser(description="索引构建服务")
    parser.add_argument("--config", default=None,
                        help="配置文件路径（如 configs/settings.yml）")
    parser.add_argument("--data-root", default=None, help="Excel 数据根目录")
    parser.add_argument("--storage-dir", default=None, help="构建产出目录")
    parser.add_argument("--html-dir", default=None, help="HTML 报告输出目录")
    parser.add_argument("--offline-html", action="store_true",
                        default=True, help="生成离线 HTML 报告（内联 vis.js）")
    parser.add_argument("--daemon", action="store_true", help="后台服务模式")
    parser.add_argument("--run-now", action="store_true", help="立即执行一次构建")
    parser.add_argument("--schedule", default="daily:02:00", help="调度策略")
    parser.add_argument("--export-llm", default=None,
                        help="导出 LLM 紧凑摘要（输出路径，如 data/llm_chunks.md 或 .jsonl）")
    parser.add_argument("--query", default=None,
                        help="查询表/列/关系，如 --query hero 查看 hero 相关表和关系")

    args = parser.parse_args()

    # 从配置文件加载默认值，CLI 参数优先
    data_root = args.data_root or "."
    storage_dir = args.storage_dir or "./graph"
    html_dir = args.html_dir or "./graph"

    if args.config:
        from indexer.core.config import load_config_file
        try:
            cfg = load_config_file(args.config)
            config_dir = Path(args.config).resolve().parent

            def _resolve_cfg_path(path_val: str) -> str:
                p = Path(path_val)
                if p.is_absolute():
                    return str(p)
                return str((config_dir / p).resolve())

            if not args.data_root and "data_root" in cfg:
                data_root = _resolve_cfg_path(cfg["data_root"])
            if not args.storage_dir and "graph_dir" in cfg:
                storage_dir = _resolve_cfg_path(cfg["graph_dir"])
            if not args.html_dir and "graph_dir" in cfg:
                html_dir = _resolve_cfg_path(cfg["graph_dir"])
        except FileNotFoundError as e:
            print(f"[ERR] {e}")
            sys.exit(1)

    service = IndexService(data_root, storage_dir, html_dir, args.offline_html)

    # L3: LLM 紧凑导出
    if args.export_llm:
        if service.current_graph is None:
            print("[ERR] 无可用图谱，请先执行 --run-now 构建")
            return
        from indexer.export.llm_chunks import export_llm_chunks
        chunks = export_llm_chunks(service.current_graph, args.export_llm)
        print(f"[OK] 已导出 {len(chunks)} 个表的 LLM 摘要 → {args.export_llm}")
        return

    # L4: 快速查询
    if args.query:
        if service.current_graph is None:
            print("[ERR] 无可用图谱，请先执行 --run-now 构建")
            return
        _handle_query(service.current_graph, args.query)
        return

    if args.daemon:
        # 守护模式：定时调度 + 文件监控 + 可选首次立即构建
        _parse_and_start_schedule(service, args.schedule)
        service.start_watcher()

        def signal_handler(sig, frame):
            service.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # --run-now 与 --daemon 可组合：先立即构建一次，再进入守护循环
        if args.run_now:
            service.build_full(incremental=True)

        service.run(daemon=True)

    elif args.run_now:
        service.build_full(incremental=True)

    else:
        service.build_full(incremental=True)


def _parse_and_start_schedule(service: IndexService, schedule_str: str):
    """解析调度策略字符串并启动调度器

    支持格式:
      daily:HH:MM    — 每日定时（如 daily:02:00）
      interval:N     — 每 N 分钟执行一次
    """
    if schedule_str.startswith("daily:"):
        time_str = schedule_str.split(":", 1)[1]
        hour, minute = map(int, time_str.split(":"))
        service.start_scheduler("daily", hour=hour, minute=minute)
    elif schedule_str.startswith("interval:"):
        minutes = int(schedule_str.split(":", 1)[1])
        service.start_scheduler("interval", minutes=minutes)
    else:
        service.logger.warning(f"未知调度策略: {schedule_str}，将使用默认 daily:02:00")
        service.start_scheduler("daily", hour=2, minute=0)


def _handle_query(graph: SchemaGraph, keyword: str):
    """L4: 基于关键词查询表/关系"""
    kw = keyword.lower()
    matched_tables = [
        name for name in graph.tables
        if kw in name.lower()
    ]

    if not matched_tables:
        print(f"未找到包含 '{keyword}' 的表")
        return

    for name in sorted(matched_tables):
        t = graph.tables[name]
        pk = t.primary_key or "-"
        print(f"\n{'='*50}")
        print(f"表: {name}  [{t.domain_label or 'other'}]")
        print(f"文件: {Path(t.file_path).name} | sheet: {t.sheet_name}")
        print(f"行数: {t.row_count} | 列数: {len(t.columns)} | 主键: {pk}")
        print(f"列: {', '.join(c['name'] for c in t.columns[:20])}")
        if len(t.columns) > 20:
            print(f"     ...+{len(t.columns)-20} 列")

        # 关联
        out_rels = [r for r in graph.relations if r.from_table == name]
        in_rels = [r for r in graph.relations if r.to_table == name]
        if out_rels:
            print(f"引用({len(out_rels)}):")
            for r in sorted(out_rels, key=lambda x: -x.confidence):
                print(f"  → {r.to_table}.{r.to_column} via {r.from_column} "
                      f"(conf={r.confidence}, {r.discovery_method})")
        if in_rels:
            print(f"被引用({len(in_rels)}):")
            for r in sorted(in_rels, key=lambda x: -x.confidence):
                print(f"  ← {r.from_table}.{r.from_column} → {r.to_column} "
                      f"(conf={r.confidence}, {r.discovery_method})")
    print()


if __name__ == "__main__":
    main()
