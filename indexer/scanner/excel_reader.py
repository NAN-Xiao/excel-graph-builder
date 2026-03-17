#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel 文件读取器

支持大表分块读取，避免内存溢出。
对万行百列级别的游戏配置表做两阶段读取：
1. 头部采样（前 N 行）做类型推断
2. 全列扫描做唯一值统计（分块）
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Any

import pandas as pd

from indexer import SimpleLogger

# 游戏配置 Excel 常见的类型标记行关键词（精确匹配 + 复合类型基底）
_TYPE_KEYWORDS = frozenset({
    'int', 'float', 'string', 'str', 'bool', 'boolean',
    'int[]', 'float[]', 'string[]', 'int32', 'int64',
    'uint32', 'uint64', 'int16', 'uint16', 'int8', 'uint8',
    'json', 'long', 'double', 'short', 'byte', 'uint',
    'text', 'enum', 'array', 'list', 'map', 'dict',
    'vector2', 'vector3', 'color',
    'date', 'time', 'datetime', 'number', 'object',
})

# 用于拆分复合类型的分隔符，如 list<int> → list, int[][] → int
_TYPE_COMPOUND_RE = re.compile(r'[\[<(]')


def _is_type_value(v: str) -> bool:
    """判断单个值是否像类型标注（支持复合类型如 list<int>, int[][], map<k,v>）"""
    if v in _TYPE_KEYWORDS:
        return True
    # 取基础类型名称: list<int> → list, int[][] → int, map<string,int> → map
    base = _TYPE_COMPOUND_RE.split(v, maxsplit=1)[0]
    return base in _TYPE_KEYWORDS


class ExcelReader:
    """Excel/CSV 文件读取器（支持大表）"""

    EXCEL_EXTENSIONS = {'.xlsx', '.xls'}
    CSV_EXTENSIONS = {'.csv', '.tsv'}
    SUPPORTED_EXTENSIONS = EXCEL_EXTENSIONS | CSV_EXTENSIONS

    def __init__(self, max_sample_rows: int = 200, chunk_size: int = 5000):
        """
        Args:
            max_sample_rows: 每列采样的最大唯一值数量
            chunk_size: 分块读取时每块行数
        """
        self.max_sample_rows = max_sample_rows
        self.chunk_size = chunk_size
        self.logger = SimpleLogger()

    def read_file(self, file_path: str, sheet_name: str = None) -> List[Dict]:
        """
        读取单个文件的所有 sheet，返回每个 sheet 的原始数据信息。

        Returns:
            [{'sheet_name': str, 'df': DataFrame, 'row_count': int, 'col_count': int}, ...]
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            return []

        try:
            if ext in self.CSV_EXTENSIONS:
                return self._read_csv(file_path)
            else:
                return self._read_excel(file_path, sheet_name)
        except Exception as e:
            self.logger.error(f"读取文件失败 {file_path.name}: {e}")
            return []

    def skip_header_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """检测并跳过游戏配置 Excel 的元数据表头行，返回干净的 DataFrame。"""
        skip = self._detect_header_rows(df)
        if skip > 0:
            df = df.iloc[skip:].reset_index(drop=True)
        return df

    def _detect_header_rows(self, df: pd.DataFrame) -> int:
        """
        检测游戏配置 Excel 的元数据表头行数。

        常见模式（不同游戏项目格式可能不同）:
          A: [pandas_header=CN, ident_row, type_row, data...]
          B: [pandas_header=EN, type_row, data...]
          C: [pandas_header=CN, ident_row, desc_row, type_row, data...]
          D: [pandas_header=CN, tag_row(c/s/cs), ident_row, type_row, data...]

        策略: 逐行检测，支持类型行、标识符行、描述/注释行（需先检测到元数据）。
        允许在已确认的元数据行之间存在纯文本描述行（间隔容忍）。

        Returns:
            应跳过的行数（0 表示无需跳过）
        """
        skip = 0
        check_rows = min(5, len(df))

        for i in range(check_rows):
            row = df.iloc[i]
            non_null = [str(v).strip().lower()
                        for v in row if pd.notna(v) and str(v).strip()]
            if not non_null:
                if skip > 0:
                    skip = i + 1  # 元数据之间的空行一并跳过
                continue

            total = len(non_null)

            # 判定1: 类型标记行（>70% 是类型关键词，支持 list<int> 等复合类型）
            type_hits = sum(1 for v in non_null if _is_type_value(v))
            if type_hits / total > 0.7:
                skip = i + 1
                continue

            # 判定2: 英文标识符行（>80% 是 camelCase/snake_case 标识符）
            ident_hits = sum(
                1 for v in non_null
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v) and len(v) >= 2
            )
            if ident_hits / total > 0.8:
                skip = i + 1
                continue

            # 判定3: 描述/注释行 — 仅在已检测到至少一行元数据时启用
            # 纯文本行（几乎无数字）夹在元数据行之间，通常是中文字段说明
            if skip > 0:
                numeric_hits = sum(
                    1 for v in non_null if re.match(r'^-?\d+\.?\d*$', v)
                )
                if numeric_hits / total < 0.1:
                    skip = i + 1
                    continue

            # 当前行既不是元数据也不是描述行 — 停止检查
            break

        return skip

    def _read_csv(self, file_path: Path) -> List[Dict]:
        """读取 CSV 文件"""
        # 先尝试检测编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']:
            try:
                df = pd.read_csv(file_path, encoding=encoding,
                                 low_memory=False)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            self.logger.error(f"无法检测文件编码: {file_path.name}")
            return []

        if df.empty:
            return []

        return [{
            'sheet_name': file_path.stem,
            'df': df,
            'row_count': len(df),
            'col_count': len(df.columns)
        }]

    def _read_excel(self, file_path: Path, sheet_name: str = None) -> List[Dict]:
        """读取 Excel 文件（支持多 sheet）"""
        try:
            xls = pd.ExcelFile(file_path, engine='openpyxl')
        except Exception:
            try:
                xls = pd.ExcelFile(file_path, engine='xlrd')
            except Exception as e:
                self.logger.error(f"无法打开 Excel: {file_path.name}: {e}")
                return []

        sheets_to_read = [sheet_name] if sheet_name else xls.sheet_names
        results = []

        for sn in sheets_to_read:
            if sn not in xls.sheet_names:
                continue
            # 跳过备注/备份 sheet（# 开头）
            if any(sn.startswith(p) for p in ('#',)):
                continue
            try:
                # P4: 只读取前 max_rows 行，避免全量加载万行大表
                max_rows = self.max_sample_rows * 25  # 默认 50000
                df = xls.parse(sn, nrows=max_rows)
                if df.empty or len(df.columns) == 0:
                    continue

                # 跳过看起来不是数据表的 sheet（列数 < 2 或行数 < 1）
                if len(df.columns) < 2 or len(df) < 1:
                    continue

                results.append({
                    'sheet_name': sn,
                    'df': df,
                    'row_count': len(df),
                    'col_count': len(df.columns)
                })
            except Exception as e:
                self.logger.warning(f"跳过 sheet {sn}: {e}")

        return results

    def collect_column_samples(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        对每列收集采样数据（唯一值、类型推断等），适配大表。

        Returns:
            {
                'col_name': {
                    'sample_values': [...],   # 去重后 top-K
                    'dtype': str,             # int/float/str/mixed
                    'unique_count': int,
                    'null_count': int,
                    'total_count': int,
                }
            }
        """
        result = {}
        total_rows = len(df)

        for col_name in df.columns:
            col = df[col_name]
            non_null = col.dropna()

            # 过滤掉全空列
            if len(non_null) == 0:
                continue

            # 基本统计
            unique_vals = non_null.unique()
            unique_count = len(unique_vals)

            # 采样：取前 max_sample_rows 个唯一值
            if unique_count > self.max_sample_rows:
                sample_values = list(unique_vals[:self.max_sample_rows])
            else:
                sample_values = list(unique_vals)

            # 转为 Python 原生类型（避免 numpy 类型序列化问题）
            sample_values = [self._to_native(v) for v in sample_values]

            # 类型推断
            dtype = self._infer_dtype(col, non_null)

            result[str(col_name)] = {
                'sample_values': sample_values,
                'dtype': dtype,
                'unique_count': unique_count,
                'null_count': int(col.isna().sum()),
                'total_count': total_rows,
            }

        return result

    def _infer_dtype(self, col: pd.Series, non_null: pd.Series) -> str:
        """推断列的语义类型"""
        pandas_dtype = str(col.dtype)

        if 'int' in pandas_dtype:
            return 'int'
        if 'float' in pandas_dtype:
            # 检查是否其实是整数（float 列可能因为有 NaN）
            try:
                if non_null.apply(lambda x: float(x).is_integer()).all():
                    return 'int'
            except (ValueError, TypeError):
                pass
            return 'float'

        # object 类型需要进一步判断
        if pandas_dtype == 'object':
            sample = non_null.head(100)
            num_count = 0
            for v in sample:
                sv = str(v).strip()
                if sv == '':
                    continue
                try:
                    float(sv)
                    num_count += 1
                except ValueError:
                    pass

            if num_count > len(sample) * 0.8:
                # 大部分是数字
                try:
                    float_vals = sample.apply(lambda x: float(
                        str(x).strip()) if str(x).strip() else None).dropna()
                    if float_vals.apply(lambda x: x.is_integer()).all():
                        return 'int'
                    return 'float'
                except (ValueError, TypeError):
                    pass
                return 'float'
            return 'str'

        if 'bool' in pandas_dtype:
            return 'bool'
        if 'datetime' in pandas_dtype:
            return 'datetime'

        return 'str'

    @staticmethod
    def _to_native(val) -> Any:
        """将 numpy/pandas 类型转为 Python 原生类型"""
        import numpy as np
        import datetime as _dt
        if isinstance(val, (np.integer,)):
            return int(val)
        if isinstance(val, (np.floating,)):
            f = float(val)
            if f.is_integer():
                return int(f)
            return f
        if isinstance(val, (np.bool_,)):
            return bool(val)
        if isinstance(val, (np.ndarray,)):
            return val.tolist()
        if pd.isna(val):
            return None
        # datetime / time / Timestamp → 字符串（避免 JSON 序列化失败）
        if isinstance(val, (pd.Timestamp, _dt.datetime)):
            return val.isoformat()
        if isinstance(val, (_dt.time, _dt.date)):
            return str(val)
        if isinstance(val, _dt.timedelta):
            return str(val)
        return val
