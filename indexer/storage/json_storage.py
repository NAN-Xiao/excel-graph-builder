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

from indexer.models import SchemaGraph, TableSchema, RelationEdge

# 跨平台文件锁
try:
    import fcntl  # Linux/Mac
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False  # Windows


class JsonGraphStorage:
    """JSON 文件存储图谱数据"""

    def __init__(self, data_dir: str = "./data/indexer"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.graph_file = self.data_dir / "schema_graph.json"
        self.index_file = self.data_dir / "column_index.json"
        self.meta_file = self.data_dir / "meta.json"

        print(f"[INFO] 存储目录: {self.data_dir}")

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
                ]
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

            print(
                f"[OK] 图谱已保存: {len(graph.tables)} 表, {len(graph.relations)} 关系")
            return True

        except Exception as e:
            print(f"[ERR] 保存失败: {e}")
            return False

    def load(self) -> Optional[SchemaGraph]:
        """从 JSON 加载图谱"""
        if not self.graph_file.exists():
            print("[INFO] 没有找到现有图谱文件")
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

            # 重建列索引
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                for col, tables in index_data.get("column_to_tables", {}).items():
                    graph._column_index[col] = set(tables)
            else:
                graph._rebuild_index()

            print(f"[OK] 图谱已加载: {len(graph.tables)} 表")
            return graph

        except Exception as e:
            print(f"[ERR] 加载失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _atomic_write(self, filepath: Path, data: dict):
        """原子写入（跨平台）"""
        temp_file = filepath.with_suffix('.tmp')

        with open(temp_file, 'w', encoding='utf-8') as f:
            # 文件锁（Linux/Mac）
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)

            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # 原子重命名（Windows 和 Unix 都支持）
        temp_file.replace(filepath)

    @staticmethod
    def _table_to_dict(table: TableSchema) -> dict:
        return {
            "name": table.name,
            "file_path": table.file_path,
            "sheet_name": table.sheet_name,
            "row_count": table.row_count,
            "columns": table.columns,
            "primary_key": table.primary_key,
            "modified_time": table.modified_time,
            "hash": table.hash,
            "numeric_columns": table.numeric_columns,
            "enum_columns": table.enum_columns
        }

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
            enum_columns=data.get("enum_columns", {})
        )

    @staticmethod
    def _relation_to_dict(rel: RelationEdge) -> dict:
        return {
            "from_table": rel.from_table,
            "from_column": rel.from_column,
            "to_table": rel.to_table,
            "to_column": rel.to_column,
            "relation_type": rel.relation_type,
            "confidence": rel.confidence
        }

    @staticmethod
    def _dict_to_relation(data: dict) -> RelationEdge:
        return RelationEdge(
            from_table=data["from_table"],
            from_column=data["from_column"],
            to_table=data["to_table"],
            to_column=data["to_column"],
            relation_type=data["relation_type"],
            confidence=data["confidence"]
        )
