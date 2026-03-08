#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 3: 传递关系推断

A->B 且 B->C，则推断 A 可能关联 C
"""

from collections import defaultdict
from typing import List, Set
from indexer.models import SchemaGraph, RelationEdge

from .base import RelationDiscoveryStrategy


class TransitiveDiscovery(RelationDiscoveryStrategy):
    """传递关系推断策略"""

    # 只从高置信度关系构建推断路径
    _MIN_SOURCE_CONFIDENCE = 0.65
    # 传递关系上限（按置信度排序取 top-N）
    _MAX_TRANSITIVE = 500

    def discover(self, graph: SchemaGraph) -> List[RelationEdge]:
        """推断传递关系（仅基于高置信度直接关系）"""
        # O(1) 直接关系查重
        direct_pairs: Set[tuple] = set()
        for rel in graph.relations:
            direct_pairs.add((rel.from_table, rel.to_table))
            direct_pairs.add((rel.to_table, rel.from_table))

        # 只从高置信度关系构建邻接表
        adj = defaultdict(list)
        for rel in graph.relations:
            if rel.confidence >= self._MIN_SOURCE_CONFIDENCE:
                adj[rel.from_table].append((rel.to_table, rel))

        inferred = []
        seen: Set[tuple] = set()

        for a in list(adj.keys()):
            for b, rel_ab in adj[a]:
                if b not in adj:
                    continue
                for c, rel_bc in adj[b]:
                    if a == c or (a, c) in direct_pairs:
                        continue
                    key = (a, c)
                    if key in seen:
                        continue
                    seen.add(key)

                    conf = round(
                        rel_ab.confidence * rel_bc.confidence * 0.5, 2)
                    inferred.append(RelationEdge(
                        from_table=a,
                        from_column=rel_ab.from_column,
                        to_table=c,
                        to_column=rel_bc.to_column,
                        relation_type='inferred_transitive',
                        confidence=conf,
                        discovery_method='transitive',
                        evidence=f"{a}.{rel_ab.from_column}->{b}.{rel_ab.to_column}->{c}.{rel_bc.to_column}",
                    ))

        # 只保留 top-N
        if len(inferred) > self._MAX_TRANSITIVE:
            inferred.sort(key=lambda r: r.confidence, reverse=True)
            inferred = inferred[:self._MAX_TRANSITIVE]

        self.logger.info(f"[Phase 3] 推断 {len(inferred)} 个传递关系")
        return inferred
