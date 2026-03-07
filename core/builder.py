#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图谱构建器 - 流程编排

整合所有 Phase，提供统一的构建接口
"""

import os
import sys
from pathlib import Path
from typing import Optional, Set, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from indexer.schema_graph import SchemaGraph, TableSchema, RelationEdge
    from indexer import SimpleLogger
    from indexer.html_report import HTMLReportGenerator
    from indexer.graph_analyzer import GraphAnalyzer
    from indexer.storage import JsonGraphStorage
except ImportError:
    from schema_graph import SchemaGraph, TableSchema, RelationEdge
    from __init__ import SimpleLogger
    from html_report import HTMLReportGenerator
    from graph_analyzer import GraphAnalyzer
    from storage import JsonGraphStorage

from .config import BuildConfig
from discovery import (
    ContainmentDiscovery,
    AbbreviationDiscovery,
    TransitiveDiscovery,
    FeedbackManager
)


class GraphBuilder:
    """
    图谱构建器（整合所有 Phase）
    
    使用策略模式组织关系发现，支持混乱数据
    """
    
    def __init__(self, config: Optional[BuildConfig] = None):
        self.config = config or BuildConfig()
        self.logger = SimpleLogger()
        
        # 初始化各 Phase
        self.discovery_strategies = [
            ContainmentDiscovery(
                containment_threshold=self.config.containment_threshold,
                overlap_threshold=0.8,
                min_sample_size=self.config.min_sample_size
            ),
            AbbreviationDiscovery(
                confidence_threshold=self.config.abbrev_confidence_threshold
            ),
            TransitiveDiscovery()
        ]
        
        # 反馈管理
        self.feedback = FeedbackManager(
            feedback_file=self.config.feedback_file,
            auto_save_interval=self.config.auto_save_interval
        )
        
        self.logger.info(f"[Builder] 初始化完成，数据目录: {self.config.data_root}")
    
    def build(self, existing_graph: Optional[SchemaGraph] = None,
             deleted_tables: Optional[Set[str]] = None) -> SchemaGraph:
        """
        执行完整构建流程
        
        Args:
            existing_graph: 现有图谱（增量模式）
            deleted_tables: 删除的表名集合
            
        Returns:
            构建完成的图谱
        """
        graph = existing_graph or SchemaGraph()
        
        print("=" * 60)
        print("开始图谱构建")
        print("=" * 60)
        
        # 1. 扫描表结构（简化版，实际需要实现 scanner）
        # TODO: 调用 scanner 扫描 Excel 文件
        
        # 2. 执行关系发现（所有 Phase）
        print("\n[关系发现] 执行所有策略...")
        for strategy in self.discovery_strategies:
            new_relations = strategy.discover(graph)
            graph.relations.extend(new_relations)
        
        # 3. 应用反馈
        print("\n[Phase 4] 应用历史反馈...")
        feedback_count = self.feedback.apply_to_graph(graph)
        print(f"  应用 {feedback_count} 条反馈")
        
        # 4. 去重
        graph.relations = self._deduplicate_relations(graph.relations)
        
        print(f"\n[完成] 总关系数: {len(graph.relations)}")
        print("=" * 60)
        
        return graph
    
    def enhance(self, graph: SchemaGraph) -> SchemaGraph:
        """
        增强已有图谱（只执行关系发现，不重新扫描）
        
        适用于：已有图谱，需要补充发现关系
        """
        print("=" * 60)
        print("执行图谱增强（仅关系发现）")
        print("=" * 60)
        
        original_count = len(graph.relations)
        
        # 执行所有发现策略
        for strategy in self.discovery_strategies:
            new_relations = strategy.discover(graph)
            graph.relations.extend(new_relations)
        
        # 应用反馈
        self.feedback.apply_to_graph(graph)
        
        # 去重
        graph.relations = self._deduplicate_relations(graph.relations)
        
        final_count = len(graph.relations)
        print(f"\n[完成] 关系: {original_count} -> {final_count} (+{final_count - original_count})")
        print("=" * 60)
        
        return graph
    
    def save_feedback(self, confirmed=None, rejected=None):
        """保存人工反馈"""
        if confirmed:
            for ft, fc, tt, tc in confirmed:
                self.feedback.confirm(ft, fc, tt, tc)
        if rejected:
            for ft, fc, tt, tc in rejected:
                self.feedback.reject(ft, fc, tt, tc)
    
    def close(self):
        """清理资源"""
        self.feedback.stop()
    
    def _deduplicate_relations(self, relations: list) -> list:
        """关系去重"""
        seen = {}
        for rel in relations:
            key = tuple(sorted([
                f"{rel.from_table}.{rel.from_column}",
                f"{rel.to_table}.{rel.to_column}"
            ]))
            if key in seen:
                if rel.confidence > seen[key].confidence:
                    seen[key] = rel
            else:
                seen[key] = rel
        return list(seen.values())


# 便捷函数
def create_builder(data_root: str = "./data", **kwargs) -> GraphBuilder:
    """创建构建器"""
    config = BuildConfig(data_root=data_root, **kwargs)
    return GraphBuilder(config)


def enhance_graph(graph: SchemaGraph, **kwargs) -> SchemaGraph:
    """便捷函数：增强图谱"""
    builder = create_builder(**kwargs)
    enhanced = builder.enhance(graph)
    builder.close()
    return enhanced
