#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图数据模型 - Indexer 独立模块
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Optional


@dataclass
class TableSchema:
    """表结构定义"""
    name: str
    file_path: str
    sheet_name: str = "Sheet1"
    row_count: int = 0
    columns: List[Dict] = field(default_factory=list)
    primary_key: Optional[str] = None
    modified_time: float = 0.0
    hash: str = ""
    numeric_columns: List[str] = field(default_factory=list)
    enum_columns: Dict[str, List] = field(default_factory=dict)
    domain_label: str = ""  # 业务域标签（hero/skill/battle/item/...）


@dataclass
class RelationEdge:
    """表关联关系"""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relation_type: str
    confidence: float
    discovery_method: str = ""
    evidence: str = ""  # 可读证据摘要（共享值样本 / 命名匹配 / 路径说明）


@dataclass
class SchemaGraph:
    """完整的配置表知识图谱"""
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    tables: Dict[str, TableSchema] = field(default_factory=dict)
    relations: List[RelationEdge] = field(default_factory=list)
    _column_index: Dict[str, Set[str]] = field(default_factory=dict)

    def add_table(self, table: TableSchema):
        self.tables[table.name] = table
        for col in table.columns:
            col_name = col['name']
            if col_name not in self._column_index:
                self._column_index[col_name] = set()
            self._column_index[col_name].add(table.name)

    def _rebuild_index(self):
        self._column_index = {}
        for table_name, table in self.tables.items():
            for col in table.columns:
                col_name = col['name']
                if col_name not in self._column_index:
                    self._column_index[col_name] = set()
                self._column_index[col_name].add(table_name)

    def remove_table(self, table_name: str) -> bool:
        """
        删除表及其所有关联关系

        Returns:
            bool: 是否成功删除
        """
        if table_name not in self.tables:
            return False

        # 删除表
        del self.tables[table_name]

        # 清理关联关系（无论 from 还是 to 都要清理）
        original_count = len(self.relations)
        self.relations = [
            r for r in self.relations
            if r.from_table != table_name and r.to_table != table_name
        ]

        # 重建列索引
        self._rebuild_index()

        return True

    def get_table_relations(self, table_name: str) -> List[RelationEdge]:
        """获取与指定表相关的所有关系"""
        return [
            r for r in self.relations
            if r.from_table == table_name or r.to_table == table_name
        ]

    def get_stats(self) -> Dict[str, int]:
        """获取图谱统计信息"""
        return {
            "table_count": len(self.tables),
            "relation_count": len(self.relations),
            "column_count": len(self._column_index)
        }
