#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 1: 包含度检测

通过列内容相似度发现隐式外键关系
"""

import os
from typing import List, Optional, Dict, Tuple
try:
    from indexer.schema_graph import SchemaGraph, TableSchema, RelationEdge
except ImportError:
    from schema_graph import SchemaGraph, TableSchema, RelationEdge

from .base import RelationDiscoveryStrategy


class ContainmentDiscovery(RelationDiscoveryStrategy):
    """包含度关系发现策略"""
    
    def __init__(self, containment_threshold: float = 0.85, 
                 overlap_threshold: float = 0.8,
                 min_sample_size: int = 3):
        super().__init__()
        self.containment_threshold = containment_threshold
        self.overlap_threshold = overlap_threshold
        self.min_sample_size = min_sample_size
    
    def discover(self, graph: SchemaGraph) -> List[RelationEdge]:
        """发现基于包含度的关系"""
        tables = list(graph.tables.values())
        if len(tables) < 2:
            return []
        
        # 收集候选列
        candidate_columns = []
        for table in tables:
            file_path = os.path.join("./data", table.file_path) if table.file_path else None
            for col in table.columns:
                col_info = self._analyze_column(table, col, file_path)
                if col_info and col_info['is_candidate_key']:
                    candidate_columns.append(col_info)
        
        self.logger.info(f"[Phase 1] 找到 {len(candidate_columns)} 个候选键列")
        
        # 两两比较
        relations = []
        compared = set()
        
        for i, col_a in enumerate(candidate_columns):
            for j, col_b in enumerate(candidate_columns[i+1:], i+1):
                pair_key = tuple(sorted([f"{col_a['table']}.{col_a['column']}", 
                                        f"{col_b['table']}.{col_b['column']}"]))
                if pair_key in compared:
                    continue
                compared.add(pair_key)
                
                if col_a['table'] == col_b['table']:
                    continue
                if col_a['dtype'] != col_b['dtype']:
                    continue
                
                result = self._calc_containment(col_a, col_b)
                
                if result['is_match']:
                    from_col, to_col = self._determine_direction(col_a, col_b, result)
                    if from_col and to_col:
                        if not self._relation_exists(graph, from_col['table'], from_col['column'],
                                                    to_col['table'], to_col['column']):
                            relations.append(RelationEdge(
                                from_table=from_col['table'],
                                from_column=from_col['column'],
                                to_table=to_col['table'],
                                to_column=to_col['column'],
                                relation_type=result['match_type'],
                                confidence=round(result['confidence'], 2)
                            ))
        
        self.logger.info(f"[Phase 1] 发现 {len(relations)} 个新关系")
        return relations
    
    def _analyze_column(self, table: TableSchema, col: dict, 
                       file_path: str = None) -> Optional[Dict]:
        """分析列是否适合匹配"""
        sample_values = col.get('sample_values', [])
        if len(sample_values) < self.min_sample_size:
            return None
        
        # 过滤空值
        non_null = [v for v in sample_values 
                   if v is not None and str(v) not in ['nan', 'None', '', 'NaN']]
        if len(non_null) < self.min_sample_size:
            return None
        
        unique_count = len(set(non_null))
        unique_ratio = unique_count / len(non_null)
        is_candidate = 0.3 <= unique_ratio <= 1.0
        
        numeric_values = []
        for v in non_null:
            try:
                numeric_values.append(float(v))
            except:
                pass
        
        return {
            'table': table.name,
            'column': col['name'],
            'dtype': col.get('dtype', 'unknown'),
            'values': set(non_null),
            'row_count': table.row_count,
            'unique_count': unique_count,
            'unique_ratio': unique_ratio,
            'is_candidate_key': is_candidate,
            'min_val': min(numeric_values) if numeric_values else None,
            'max_val': max(numeric_values) if numeric_values else None,
        }
    
    def _calc_containment(self, col_a: Dict, col_b: Dict) -> Dict:
        """计算包含度"""
        values_a = col_a['values']
        values_b = col_b['values']
        
        result = {
            'is_match': False, 'confidence': 0.0, 'match_type': '',
            'direction': '', 'containment_a': 0.0, 'containment_b': 0.0, 'jaccard': 0.0
        }
        
        if not values_a or not values_b:
            return result
        
        intersection = values_a & values_b
        if not intersection:
            return result
        
        result['jaccard'] = len(intersection) / len(values_a | values_b)
        result['containment_a'] = len(intersection) / len(values_a) if values_a else 0
        result['containment_b'] = len(intersection) / len(values_b) if values_b else 0
        
        # A 是 B 的子集
        if (result['containment_a'] >= self.containment_threshold and 
            len(values_a) <= len(values_b) * 0.95):
            result['is_match'] = True
            result['match_type'] = 'fk_content_subset'
            result['direction'] = 'a_to_b'
            size_ratio = min(len(values_a) / len(values_b), 1.0) if values_b else 0
            result['confidence'] = result['containment_a'] * 0.7 + result['jaccard'] * 0.2 + size_ratio * 0.1
        
        # B 是 A 的子集
        elif (result['containment_b'] >= self.containment_threshold and 
              len(values_b) <= len(values_a) * 0.95):
            result['is_match'] = True
            result['match_type'] = 'fk_content_subset'
            result['direction'] = 'b_to_a'
            size_ratio = min(len(values_b) / len(values_a), 1.0) if values_a else 0
            result['confidence'] = result['containment_b'] * 0.7 + result['jaccard'] * 0.2 + size_ratio * 0.1
        
        # 高度重合
        elif result['jaccard'] >= self.overlap_threshold:
            result['is_match'] = True
            result['match_type'] = 'fk_content_overlap'
            result['direction'] = 'unknown'
            result['confidence'] = result['jaccard'] * 0.8
        
        return result
    
    def _determine_direction(self, col_a: Dict, col_b: Dict, result: Dict) -> Tuple:
        """确定外键方向"""
        if result['direction'] == 'a_to_b':
            return col_a, col_b
        elif result['direction'] == 'b_to_a':
            return col_b, col_a
        
        a_is_pk = col_a['unique_count'] >= col_a['row_count'] * 0.95
        b_is_pk = col_b['unique_count'] >= col_b['row_count'] * 0.95
        
        if a_is_pk and not b_is_pk:
            return col_b, col_a
        elif b_is_pk and not a_is_pk:
            return col_a, col_b
        
        if col_a['row_count'] > col_b['row_count'] * 1.2:
            return col_b, col_a
        elif col_b['row_count'] > col_a['row_count'] * 1.2:
            return col_a, col_b
        
        return None, None
