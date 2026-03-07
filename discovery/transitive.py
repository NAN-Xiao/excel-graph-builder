#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 3: 传递关系推断

A->B 且 B->C，则推断 A 可能关联 C
"""

from collections import defaultdict
from typing import List, Set
try:
    from indexer.schema_graph import SchemaGraph, RelationEdge
except ImportError:
    from schema_graph import SchemaGraph, RelationEdge

from .base import RelationDiscoveryStrategy


class TransitiveDiscovery(RelationDiscoveryStrategy):
    """传递关系推断策略"""
    
    def discover(self, graph: SchemaGraph) -> List[RelationEdge]:
        """推断传递关系"""
        # 构建邻接表
        adj = defaultdict(list)
        for rel in graph.relations:
            adj[rel.from_table].append((rel.to_table, rel))
        
        inferred = []
        seen = set()
        
        # 找长度为2的路径 A->B->C
        for a in list(adj.keys()):
            for b, rel_ab in adj[a]:
                if b not in adj:
                    continue
                for c, rel_bc in adj[b]:
                    if a == c:
                        continue
                    
                    # 检查是否已有直接关系
                    if self._has_direct_relation(graph, a, c):
                        continue
                    
                    # 避免重复
                    key = (a, c)
                    if key in seen:
                        continue
                    seen.add(key)
                    
                    inferred.append(RelationEdge(
                        from_table=a,
                        from_column=f"via_{b}",
                        to_table=c,
                        to_column=rel_bc.to_column,
                        relation_type='inferred_transitive',
                        confidence=round(rel_ab.confidence * rel_bc.confidence * 0.5, 2)
                    ))
        
        self.logger.info(f"[Phase 3] 推断 {len(inferred)} 个传递关系")
        return inferred
    
    def _has_direct_relation(self, graph: SchemaGraph, table_a: str, table_b: str) -> bool:
        """检查两表是否已有直接关系"""
        for rel in graph.relations:
            if ((rel.from_table == table_a and rel.to_table == table_b) or
                (rel.from_table == table_b and rel.to_table == table_a)):
                return True
        return False
