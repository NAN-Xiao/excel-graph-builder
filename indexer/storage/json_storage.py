#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图谱 JSON 持久化存储 - Indexer 独立模块
"""

import json
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

from indexer.models import SchemaGraph, TableSchema, RelationEdge, ChangeRecord
from indexer import SimpleLogger

# 跨平台文件锁

_LOCK_MODE = None  # 'fcntl' | 'msvcrt' | None
try:
    import fcntl  # Linux/Mac
    _LOCK_MODE = 'fcntl'
except ImportError:
    pass

if _LOCK_MODE is None and platform.system() == 'Windows':
    try:
        import msvcrt  # Windows
        _LOCK_MODE = 'msvcrt'
    except ImportError:
        pass


class JsonGraphStorage:
    """JSON 文件存储图谱数据"""

    def __init__(self, data_dir: str = "./data/indexer"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = SimpleLogger()

        self.graph_file = self.data_dir / "schema_graph.json"
        self.index_file = self.data_dir / "column_index.json"
        self.meta_file = self.data_dir / "meta.json"

        self.logger.info(f"存储目录: {self.data_dir}")

    def save(self, graph: SchemaGraph) -> bool:
        """保存图谱到 JSON"""
        try:
            # 1. 保存主图谱
            graph_data = {
                "version": graph.version,
                "created_at": graph.created_at.isoformat(),
                "updated_at": graph.updated_at.isoformat(),
                "tables": {
                    name: self._table_to_dict(table)
                    for name, table in graph.tables.items()
                },
                "relations": [
                    self._relation_to_dict(rel)
                    for rel in graph.relations
                ],
                "changelog": [
                    {"timestamp": c.timestamp, "table_name": c.table_name,
                     "change_type": c.change_type, "details": c.details}
                    for c in (graph.changelog or [])
                ][-200:]  # 保留最近 200 条
            }
            self._atomic_write(self.graph_file, graph_data)

            # 2. 保存列索引
            index_data = {
                "column_to_tables": {
                    col: list(tables)
                    for col, tables in graph._column_index.items()
                },
                "updated_at": datetime.now().isoformat()
            }
            self._atomic_write(self.index_file, index_data)

            # 3. 保存元信息
            meta_data = {
                "table_count": len(graph.tables),
                "relation_count": len(graph.relations),
                "last_full_build": graph.updated_at.isoformat(),
                "data_dir": str(self.data_dir)
            }
            self._atomic_write(self.meta_file, meta_data)

            self.logger.success(
                f"图谱已保存: {len(graph.tables)} 表, {len(graph.relations)} 关系")
            return True

        except Exception as e:
            self.logger.error(f"保存失败: {e}")
            return False

    def load(self) -> Optional[SchemaGraph]:
        """从 JSON 加载图谱"""
        if not self.graph_file.exists():
            self.logger.info("没有找到现有图谱文件")
            return None

        try:
            with open(self.graph_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            graph = SchemaGraph(
                version=data.get("version", "1.0"),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"])
            )

            # 加载表
            for name, table_data in data.get("tables", {}).items():
                table = self._dict_to_table(table_data)
                graph.tables[name] = table

            # 加载关系
            for rel_data in data.get("relations", []):
                rel = self._dict_to_relation(rel_data)
                graph.relations.append(rel)

            # 加载变更日志
            for cr in data.get("changelog", []):
                graph.changelog.append(ChangeRecord(
                    timestamp=cr.get("timestamp", ""),
                    table_name=cr.get("table_name", ""),
                    change_type=cr.get("change_type", ""),
                    details=cr.get("details", ""),
                ))

            # 重建列索引
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                for col, tables in index_data.get("column_to_tables", {}).items():
                    graph._column_index[col] = set(tables)
            else:
                graph._rebuild_index()

            self.logger.success(f"图谱已加载: {len(graph.tables)} 表")
            return graph

        except Exception as e:
            self.logger.error(f"加载失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _atomic_write(self, filepath: Path, data: dict):
        """原子写入（跨平台文件锁）"""
        temp_file = filepath.with_suffix('.tmp')

        with open(temp_file, 'w', encoding='utf-8') as f:
            # 加锁
            if _LOCK_MODE == 'fcntl':
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            elif _LOCK_MODE == 'msvcrt':
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            # 解锁
            if _LOCK_MODE == 'fcntl':
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            elif _LOCK_MODE == 'msvcrt':
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

        # 原子重命名（Windows 和 Unix 都支持）
        temp_file.replace(filepath)

    # 持久化时每列最多保留的 sample_values 数量（减小 JSON 文件体积）
    MAX_PERSISTED_SAMPLES = 30

    @staticmethod
    def _table_to_dict(table: TableSchema,
                       max_samples: int = 30) -> dict:
        # 截断 sample_values 以减小 schema_graph.json 体积
        columns_slim = []
        for col in table.columns:
            col_copy = dict(col)
            sv = col_copy.get('sample_values')
            if sv and len(sv) > max_samples:
                col_copy['sample_values'] = sv[:max_samples]
            columns_slim.append(col_copy)

        d = {
            "name": table.name,
            "file_path": table.file_path,
            "sheet_name": table.sheet_name,
            "row_count": table.row_count,
            "columns": columns_slim,
            "primary_key": table.primary_key,
            "modified_time": table.modified_time,
            "hash": table.hash,
            "numeric_columns": table.numeric_columns,
            "enum_columns": table.enum_columns,
            "header_offset": table.header_offset,
        }
        if table.domain_label:
            d["domain_label"] = table.domain_label
        return d

    @staticmethod
    def _dict_to_table(data: dict) -> TableSchema:
        return TableSchema(
            name=data["name"],
            file_path=data["file_path"],
            sheet_name=data.get("sheet_name", "Sheet1"),
            row_count=data.get("row_count", 0),
            columns=data.get("columns", []),
            primary_key=data.get("primary_key"),
            modified_time=data.get("modified_time", 0),
            hash=data.get("hash", ""),
            numeric_columns=data.get("numeric_columns", []),
            enum_columns=data.get("enum_columns", {}),
            domain_label=data.get("domain_label", ""),
            header_offset=data.get("header_offset", 0),
        )

    @staticmethod
    def _relation_to_dict(rel: RelationEdge) -> dict:
        d = {
            "from_table": rel.from_table,
            "from_column": rel.from_column,
            "to_table": rel.to_table,
            "to_column": rel.to_column,
            "relation_type": rel.relation_type,
            "confidence": rel.confidence,
        }
        if rel.discovery_method:
            d["discovery_method"] = rel.discovery_method
        if rel.evidence:
            d["evidence"] = rel.evidence
        return d

    @staticmethod
    def _dict_to_relation(data: dict) -> RelationEdge:
        return RelationEdge(
            from_table=data["from_table"],
            from_column=data["from_column"],
            to_table=data["to_table"],
            to_column=data["to_column"],
            relation_type=data["relation_type"],
            confidence=data["confidence"],
            discovery_method=data.get("discovery_method", ""),
            evidence=data.get("evidence", ""),
        )
