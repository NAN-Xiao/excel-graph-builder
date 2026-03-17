#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
表结构提取器

从 DataFrame 提取 TableSchema，包括：
- 列名、类型、采样值
- 主键推断
- 枚举列识别
- 数值列识别
"""

import hashlib
import re
from typing import Dict, List, Optional, Any

import pandas as pd

from indexer.models import TableSchema

from .excel_reader import ExcelReader


class SchemaExtractor:
    """从 DataFrame 提取 TableSchema"""

    # 常见主键列名后缀
    PK_SUFFIXES = ('_id', '_key', '_no', '_code', 'id', 'key')
    PK_EXACT_NAMES = {'id', 'ID', 'Id', 'key',
                      'Key', 'KEY', 'no', 'code', 'index'}

    # 常见外键列名模式
    FK_PATTERN = re.compile(
        r'^(\w+?)(?:_id|_key|_no|_code|Id|Key|No|Code)$', re.IGNORECASE)

    # 枚举列的唯一值阈值（唯一值数量/行数 < 该阈值认为是枚举）
    ENUM_RATIO_THRESHOLD = 0.05
    ENUM_MAX_UNIQUE = 50  # 枚举值最多这么多个

    def __init__(self, max_sample_rows: int = 200):
        self.reader = ExcelReader(max_sample_rows=max_sample_rows)
        self.max_sample_rows = max_sample_rows

    def extract(self, file_path: str, sheet_name: str,
                df: pd.DataFrame, file_mtime: float) -> TableSchema:
        """
        从 DataFrame 提取完整的 TableSchema

        Args:
            file_path: 文件相对路径
            sheet_name: sheet 名
            df: 数据
            file_mtime: 文件修改时间戳

        Returns:
            TableSchema 实例
        """
        # 表名 = 文件名（不含扩展名）
        # 如果有多 sheet，表名 = 文件名_sheet名
        import os
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        table_name = base_name if sheet_name in (
            'Sheet1', base_name, None) else f"{base_name}_{sheet_name}"

        # 检测并跳过元数据表头行（英文字段名行、类型标记行等）
        header_offset = self.reader._detect_header_rows(df)
        if header_offset > 0:
            df = df.iloc[header_offset:].reset_index(drop=True)

        # 收集列信息
        col_samples = self.reader.collect_column_samples(df)
        columns = []
        numeric_columns = []
        enum_columns = {}

        for col_name, info in col_samples.items():
            col_entry = {
                'name': col_name,
                'dtype': info['dtype'],
                'sample_values': info['sample_values'],
                'unique_count': info['unique_count'],
                'null_count': info['null_count'],
                'total_count': info['total_count'],
            }

            # 标记是否疑似外键引用
            col_entry['is_fk_candidate'] = self._is_fk_candidate(
                col_name, info)

            columns.append(col_entry)

            # 数值列
            if info['dtype'] in ('int', 'float'):
                numeric_columns.append(col_name)

            # 枚举列
            if self._is_enum_column(info):
                enum_columns[col_name] = info['sample_values']

        # 推断主键
        primary_key = self._infer_primary_key(columns, len(df))

        # 计算内容哈希（用于增量检测）
        content_hash = self._compute_hash(df)

        return TableSchema(
            name=table_name,
            file_path=file_path,
            sheet_name=sheet_name,
            row_count=len(df),
            columns=columns,
            primary_key=primary_key,
            modified_time=file_mtime,
            hash=content_hash,
            numeric_columns=numeric_columns,
            enum_columns=enum_columns,
            header_offset=header_offset,
        )

    def _infer_primary_key(self, columns: List[Dict], row_count: int) -> Optional[str]:
        """
        推断主键列

        策略：
        1. 第一列如果唯一率 > 95% 且名字含 id/key，直接选
        2. 否则找唯一率最高 + 命名匹配的列
        3. 都找不到返回 None
        """
        if not columns or row_count == 0:
            return None

        candidates = []

        for col in columns:
            unique_ratio = col['unique_count'] / \
                row_count if row_count > 0 else 0
            name_lower = col['name'].lower()

            # 命名得分
            name_score = 0
            if name_lower in self.PK_EXACT_NAMES:
                name_score = 10
            elif any(name_lower.endswith(s) for s in self.PK_SUFFIXES):
                name_score = 5

            # 唯一性得分
            if unique_ratio >= 0.99:
                unique_score = 10
            elif unique_ratio >= 0.95:
                unique_score = 7
            elif unique_ratio >= 0.8:
                unique_score = 3
            else:
                unique_score = 0

            # 类型得分（整数更可能是 PK）
            type_score = 3 if col['dtype'] == 'int' else 1

            total = name_score + unique_score + type_score
            if unique_ratio >= 0.8 and (name_score > 0 or unique_ratio >= 0.95):
                candidates.append((col['name'], total))

        if not candidates:
            # 退而求其次：第一列唯一率 > 80%
            first = columns[0]
            if first['unique_count'] / row_count >= 0.8 if row_count > 0 else False:
                return first['name']
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _is_fk_candidate(self, col_name: str, info: Dict) -> bool:
        """判断列是否可能是外键引用"""
        name_lower = col_name.lower()

        # 命名模式匹配
        if self.FK_PATTERN.match(col_name):
            return True

        # 以 _id 结尾的整数列
        if name_lower.endswith('_id') and info['dtype'] in ('int', 'float'):
            return True

        # 较高唯一率的整数列（可能是 ID 引用）
        total = info['total_count']
        if total > 0 and info['dtype'] == 'int':
            unique_ratio = info['unique_count'] / total
            if 0.1 < unique_ratio < 0.95:
                return True

        return False

    def _is_enum_column(self, info: Dict) -> bool:
        """判断是否为枚举列"""
        total = info['total_count']
        if total == 0:
            return False

        unique_ratio = info['unique_count'] / total
        return (
            info['unique_count'] <= self.ENUM_MAX_UNIQUE and
            unique_ratio <= self.ENUM_RATIO_THRESHOLD and
            info['unique_count'] >= 2  # 至少两个值才算枚举
        )

    @staticmethod
    def _compute_hash(df: pd.DataFrame) -> str:
        """
        计算 DataFrame 内容哈希，用于增量检测。
        只用前几行 + 列名 + shape 做快速哈希，不遍历全表。
        """
        h = hashlib.md5()
        h.update(str(df.shape).encode())
        h.update(','.join(str(c) for c in df.columns).encode())
        # 取前10行 + 后10行做哈希
        head = df.head(10).to_csv(index=False, header=False)
        tail = df.tail(10).to_csv(index=False, header=False)
        h.update(head.encode('utf-8', errors='replace'))
        h.update(tail.encode('utf-8', errors='replace'))
        return h.hexdigest()
