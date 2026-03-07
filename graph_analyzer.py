#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图谱分析器 - 图算法分析工具

提供：
- 环检测（发现循环依赖）
- 关键路径分析（PageRank 中心性）
- 模块聚类（社区发现）
- 孤立节点检测
"""

from typing import List, Set, Dict, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass

from indexer.schema_graph import SchemaGraph, RelationEdge
from indexer import SimpleLogger


@dataclass
class AnalysisResult:
    """图谱分析结果"""
    cycles: List[List[str]]                    # 检测到的环
    centrality: Dict[str, float]               # 节点中心性得分
    modules: List[Set[str]]                    # 业务模块（社区）
    orphans: List[str]                         # 孤立表
    critical_path: List[str]                   # 关键路径（最长的依赖链）


class GraphAnalyzer:
    """图谱图算法分析器"""
    
    def __init__(self, graph: SchemaGraph):
        self.graph = graph
        self.logger = SimpleLogger()
        
        # 构建邻接表
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adj: Dict[str, Set[str]] = defaultdict(set)
        
        for rel in graph.relations:
            self.adjacency[rel.from_table].add(rel.to_table)
            self.reverse_adj[rel.to_table].add(rel.from_table)
    
    def analyze(self) -> AnalysisResult:
        """执行全部分析"""
        self.logger.info("开始图谱分析...")
        
        cycles = self.detect_cycles()
        centrality = self.calculate_centrality()
        modules = self.detect_communities()
        orphans = self.find_orphans()
        critical_path = self.find_critical_path()
        
        self.logger.info(
            f"分析完成: {len(cycles)} 个环, {len(modules)} 个模块, "
            f"{len(orphans)} 个孤立表"
        )
        
        return AnalysisResult(
            cycles=cycles,
            centrality=centrality,
            modules=modules,
            orphans=orphans,
            critical_path=critical_path
        )
    
    def detect_cycles(self) -> List[List[str]]:
        """
        检测图中的所有环（循环依赖）
        
        使用 DFS + 三色标记法
        WHITE: 未访问
        GRAY:  正在访问（在递归栈中）
        BLACK: 已完成访问
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self.graph.tables}
        cycles = []
        
        def dfs(node: str, path: List[str]):
            color[node] = GRAY
            path.append(node)
            
            for neighbor in self.adjacency[node]:
                if color[neighbor] == GRAY:
                    # 发现环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif color[neighbor] == WHITE:
                    dfs(neighbor, path)
            
            path.pop()
            color[node] = BLACK
        
        for node in self.graph.tables:
            if color[node] == WHITE:
                dfs(node, [])
        
        # 去重：相同的环只保留一次
        unique_cycles = []
        seen = set()
        for cycle in cycles:
            # 将环标准化（从最小的元素开始）
            normalized = tuple(min_rotation(cycle[:-1]))  # 去掉重复的最后一个
            if normalized not in seen:
                seen.add(normalized)
                unique_cycles.append(cycle[:-1])
        
        return unique_cycles
    
    def calculate_centrality(self, iterations: int = 100) -> Dict[str, float]:
        """
        计算节点中心性（简化版 PageRank）
        
        被引用越多的表越重要
        """
        nodes = list(self.graph.tables.keys())
        if not nodes:
            return {}
        
        # 初始化
        n = len(nodes)
        scores = {node: 1.0 / n for node in nodes}
        damping = 0.85
        
        for _ in range(iterations):
            new_scores = {}
            for node in nodes:
                # 计算流入的分数
                incoming = 0
                for prev in self.reverse_adj[node]:
                    out_degree = len(self.adjacency[prev])
                    if out_degree > 0:
                        incoming += scores[prev] / out_degree
                
                new_scores[node] = (1 - damping) / n + damping * incoming
            
            scores = new_scores
        
        # 归一化到 0-100
        max_score = max(scores.values()) if scores else 1
        return {k: round(v / max_score * 100, 2) for k, v in scores.items()}
    
    def detect_communities(self) -> List[Set[str]]:
        """
        社区发现（业务模块聚类）
        
        使用简单的标签传播算法（Label Propagation）
        外键密集的表聚集在一起 = 一个业务模块
        """
        nodes = list(self.graph.tables.keys())
        if not nodes:
            return []
        
        # 初始化：每个节点有自己的标签
        labels = {node: i for i, node in enumerate(nodes)}
        
        # 迭代传播
        for _ in range(100):
            updated = False
            for node in nodes:
                # 收集邻居的标签
                neighbor_labels = defaultdict(int)
                for neighbor in self.adjacency[node]:
                    neighbor_labels[labels[neighbor]] += 1
                for neighbor in self.reverse_adj[node]:
                    neighbor_labels[labels[neighbor]] += 1
                
                if neighbor_labels:
                    # 选择出现次数最多的标签
                    best_label = max(neighbor_labels, key=neighbor_labels.get)
                    if best_label != labels[node]:
                        labels[node] = best_label
                        updated = True
            
            if not updated:
                break
        
        # 收集社区
        communities: Dict[int, Set[str]] = defaultdict(set)
        for node, label in labels.items():
            communities[label].add(node)
        
        # 过滤掉太小的社区（可能是噪声）
        return [nodes for nodes in communities.values() if len(nodes) >= 2]
    
    def find_orphans(self) -> List[str]:
        """
        找出孤立表（没有被引用，也没有引用别人的）
        
        可能是废弃表
        """
        orphans = []
        for table_name in self.graph.tables:
            out_degree = len(self.adjacency[table_name])
            in_degree = len(self.reverse_adj[table_name])
            
            if out_degree == 0 and in_degree == 0:
                orphans.append(table_name)
        
        return orphans
    
    def find_critical_path(self) -> List[str]:
        """
        找出最长的依赖链（关键路径）
        
        使用拓扑排序 + DP
        """
        # 计算入度
        in_degree = {node: 0 for node in self.graph.tables}
        for node in self.adjacency:
            for neighbor in self.adjacency[node]:
                in_degree[neighbor] += 1
        
        # DP 数组：到每个节点的最长路径
        dist = {node: 1 for node in self.graph.tables}  # 至少包含自己
        parent = {node: None for node in self.graph.tables}
        
        # 拓扑排序
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        
        while queue:
            node = queue.popleft()
            
            for neighbor in self.adjacency[node]:
                if dist[node] + 1 > dist[neighbor]:
                    dist[neighbor] = dist[node] + 1
                    parent[neighbor] = node
                
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 找出最长路径的终点
        if not dist:
            return []
        
        max_node = max(dist, key=dist.get)
        
        # 回溯路径
        path = []
        node = max_node
        while node is not None:
            path.append(node)
            node = parent[node]
        
        return list(reversed(path))
    
    def get_summary(self) -> str:
        """获取分析摘要文本"""
        result = self.analyze()
        
        lines = ["=" * 50, "📊 图谱分析报告", "=" * 50]
        
        # 环检测
        lines.append(f"\n🔴 循环依赖: {len(result.cycles)} 个")
        for i, cycle in enumerate(result.cycles[:5], 1):  # 最多显示 5 个
            lines.append(f"  {i}. {' → '.join(cycle)} → {cycle[0]}")
        if len(result.cycles) > 5:
            lines.append(f"  ... 还有 {len(result.cycles) - 5} 个")
        
        # 中心性排名
        lines.append(f"\n⭐ 核心表（Top 5）:")
        sorted_cent = sorted(result.centrality.items(), key=lambda x: x[1], reverse=True)
        for table, score in sorted_cent[:5]:
            lines.append(f"  {table}: {score} 分")
        
        # 业务模块
        lines.append(f"\n📦 业务模块: {len(result.modules)} 个")
        for i, module in enumerate(result.modules[:5], 1):
            lines.append(f"  模块{i}: {', '.join(list(module)[:5])}" + 
                        (f" 等 {len(module)} 个表" if len(module) > 5 else ""))
        
        # 孤立表
        lines.append(f"\n🚫 孤立表（可能是废弃表）: {len(result.orphans)} 个")
        if result.orphans:
            lines.append(f"  {', '.join(result.orphans[:10])}")
            if len(result.orphans) > 10:
                lines.append(f"  ... 还有 {len(result.orphans) - 10} 个")
        
        # 关键路径
        lines.append(f"\n🔗 最长依赖链: {' → '.join(result.critical_path[:8])}")
        if len(result.critical_path) > 8:
            lines.append(f"  ... 共 {len(result.critical_path)} 个表")
        
        lines.append("=" * 50)
        return "\n".join(lines)


def min_rotation(lst: List) -> Tuple:
    """返回列表的最小旋转（用于环的标准化）"""
    if not lst:
        return tuple()
    n = len(lst)
    rotations = [tuple(lst[i:] + lst[:i]) for i in range(n)]
    return min(rotations)
