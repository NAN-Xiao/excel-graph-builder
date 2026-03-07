#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
关系发现基类
"""

from abc import ABC, abstractmethod
from typing import List

try:
    from indexer.schema_graph import SchemaGraph, RelationEdge
    from indexer import SimpleLogger
except ImportError:
    from schema_graph import SchemaGraph, RelationEdge
    from __init__ import SimpleLogger


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
    
    def _relation_exists(self, graph: SchemaGraph, from_table: str, from_col: str,
                        to_table: str, to_col: str) -> bool:
        """检查关系是否已存在"""
        for rel in graph.relations:
            if (rel.from_table == from_table and rel.from_column == from_col and
                rel.to_table == to_table and rel.to_column == to_col):
                return True
            if (rel.from_table == to_table and rel.from_column == to_col and
                rel.to_table == from_table and rel.to_column == from_col):
                return True
        return False
