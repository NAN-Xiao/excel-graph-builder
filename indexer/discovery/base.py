#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
关系发现基类
"""

from abc import ABC, abstractmethod
from typing import List, Set, Tuple

from indexer.models import SchemaGraph, RelationEdge
from indexer import SimpleLogger


def build_relation_key(from_table: str, from_col: str,
                       to_table: str, to_col: str) -> Tuple[str, str]:
    """生成方向无关的关系键，用于 O(1) 去重"""
    a = f"{from_table}.{from_col}"
    b = f"{to_table}.{to_col}"
    return (a, b) if a <= b else (b, a)


def build_relation_index(graph: SchemaGraph) -> Set[Tuple[str, str]]:
    """从现有图谱构建关系索引集合（O(R) 一次性构建，后续 O(1) 查找）"""
    index = set()
    for rel in graph.relations:
        index.add(build_relation_key(
            rel.from_table, rel.from_column,
            rel.to_table, rel.to_column))
    return index


class RelationDiscoveryStrategy(ABC):
    """关系发现策略基类"""

    def __init__(self):
        self.logger = SimpleLogger()

    @abstractmethod
    def discover(self, graph: SchemaGraph) -> List[RelationEdge]:
        """
        发现关系

        Args:
            graph: 当前图谱

        Returns:
            新发现的关系列表
        """
        pass

    def _build_relation_index(self, graph: SchemaGraph) -> Set[Tuple[str, str]]:
        """构建关系索引（子类在 discover 开头调一次即可）"""
        return build_relation_index(graph)

    def _relation_exists_in_index(self, index: Set[Tuple[str, str]],
                                  from_table: str, from_col: str,
                                  to_table: str, to_col: str) -> bool:
        """O(1) 检查关系是否已存在"""
        return build_relation_key(from_table, from_col, to_table, to_col) in index

    def _relation_exists(self, graph: SchemaGraph, from_table: str, from_col: str,
                         to_table: str, to_col: str) -> bool:
        """检查关系是否已存在（兼容旧调用，O(R)）"""
        key = build_relation_key(from_table, from_col, to_table, to_col)
        for rel in graph.relations:
            if build_relation_key(rel.from_table, rel.from_column,
                                  rel.to_table, rel.to_column) == key:
                return True
        return False
