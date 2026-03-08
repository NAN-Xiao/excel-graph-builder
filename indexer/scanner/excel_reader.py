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
from pathlib import Path
from typing import List, Dict, Optional, Any

import pandas as pd

from indexer import SimpleLogger


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
                df = xls.parse(sn)
                if df.empty or len(df.columns) == 0:
                    continue

                # 跳过看起来不是数据表的 sheet（列数 < 2 或行数 < 1）
                if len(df.columns) < 2 or len(df) < 1:
                    continue

                # 超大表截断：保留前 max_rows 行
                if len(df) > self.max_sample_rows * 250:
                    self.logger.warning(
                        f"  {sn}: {len(df)} 行过大，截断为 {self.max_sample_rows * 250} 行")
                    df = df.head(self.max_sample_rows * 250)

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
        return val
