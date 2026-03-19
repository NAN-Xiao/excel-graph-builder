#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel 文件读取器

支持大表全量读取 + 分层采样，避免截断导致外键发现和枚举识别失真。
对万行百列级别的游戏配置表做两阶段处理：
1. 全量（或按 max_read_rows 上限）读取，获取真实行数和完整唯一值集合
2. 分层采样（头部+中段+尾部均匀取点）控制存储的 sample_values 数量
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


def _stratified_sample(arr, n: int) -> list:
    """从 arr 中均匀取 n 个元素（首、尾、中间均匀分布）。

    保证取到数值范围的两端，避免只取头部值导致代表性不足。
    """
    total = len(arr)
    if total <= n:
        return list(arr)
    if n == 1:
        return [arr[0]]
    step = (total - 1) / (n - 1)
    indices = sorted({round(i * step) for i in range(n)})
    return [arr[i] for i in indices]


class ExcelReader:
    """Excel/CSV 文件读取器（支持大表全量读取 + 分层采样）"""

    EXCEL_EXTENSIONS = {'.xlsx', '.xls'}
    CSV_EXTENSIONS = {'.csv', '.tsv'}
    SUPPORTED_EXTENSIONS = EXCEL_EXTENSIONS | CSV_EXTENSIONS

    # 默认最大读取行数：None 表示不限制（读全量）
    DEFAULT_MAX_READ_ROWS = None

    def __init__(self, max_sample_rows: int = 200, chunk_size: int = 5000,
                 max_read_rows: Optional[int] = None):
        """
        Args:
            max_sample_rows: 每列存储的最大唯一值数量（用于 FK 发现和枚举识别）
            chunk_size: 保留参数（未来分块流式读取扩展用）
            max_read_rows: 读取行数上限（None = 不限制，读全部行）
        """
        self.max_sample_rows = max_sample_rows
        self.chunk_size = chunk_size
        self.max_read_rows = max_read_rows  # None = 读全量
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

    # c/s/cs 导出标记（服务端/客户端导出标记行）
    _EXPORT_MARKERS = frozenset([
        'c', 's', 'cs', 'sc', 'all', 'none',
        'server', 'client', 'both', '0', '1',
        'common', '服务端', '客户端', '全端', '全量',
    ])

    def skip_header_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """检测并跳过游戏配置 Excel 的元数据表头行，返回干净的 DataFrame。"""
        skip, _ = self._detect_header_rows(df)
        if skip > 0:
            df = df.iloc[skip:].reset_index(drop=True)
        return df

    def detect_and_fix_header(self, df: pd.DataFrame) -> tuple:
        """
        检测元数据表头行并修复列名。

        当 pandas 误将注释行/说明行读为表头时，此方法会找到真正的字段名行，
        用其值覆盖错误的列名，然后返回跳过所有元数据行后的干净 DataFrame。

        Returns:
            (cleaned_df, header_offset)
        """
        skip, better_cols = self._detect_header_rows(df)

        if skip > 0 and better_cols:
            # 当前列名看起来不正常（含注释符/大量 Unnamed），用真正的字段名替换
            bad_col_count = sum(
                1 for c in df.columns
                if (str(c).startswith('Unnamed:')
                    or any(ch in str(c) for ch in ('//', '#', '@', '/*'))
                    or len(str(c)) > 80)
            )
            if bad_col_count >= max(1, len(df.columns) * 0.3):
                df = df.copy()
                # 用检测到的标识符行值重命名列
                for j, new_name in enumerate(better_cols):
                    if j < len(df.columns):
                        df.rename(columns={df.columns[j]: new_name}, inplace=True)

        if skip > 0:
            df = df.iloc[skip:].reset_index(drop=True)

        return df, skip

    def _detect_header_rows(self, df: pd.DataFrame) -> tuple:
        """
        检测游戏配置 Excel 的元数据表头行数。

        常见模式（不同游戏项目格式可能不同）:
          A: [pandas_header=CN字段名, type_row, data...]
          B: [pandas_header=EN字段名, type_row, data...]
          C: [pandas_header=注释行, ident_row, type_row, data...]    ← 列名修复场景
          D: [pandas_header=CN字段名, c/s/cs标记行, type_row, data...]
          E: [pandas_header=注释行, ident_row, desc_row, type_row, data...]

        Returns:
            (skip_count, identifier_row_values_or_None)
            - skip_count: 应跳过的行数（0 表示无需跳过）
            - identifier_row_values: 若检测到英文标识符行，返回其值列表（可用于修复列名）
        """
        skip = 0
        better_cols = None  # 找到的"真正字段名行"的值列表
        check_rows = min(6, len(df))

        for i in range(check_rows):
            row = df.iloc[i]
            raw_vals = [(j, str(v).strip()) for j, v in enumerate(row)
                        if pd.notna(v) and str(v).strip()]
            if not raw_vals:
                if skip > 0:
                    skip = i + 1  # 元数据之间的空行一并跳过
                continue

            non_null = [v.lower() for _, v in raw_vals]
            total = len(non_null)

            # 判定1: 类型标记行（>70% 是类型关键词，支持 list<int> 等复合类型）
            type_hits = sum(1 for v in non_null if _is_type_value(v))
            if type_hits / total > 0.7:
                skip = i + 1
                continue

            # 判定2: 英文标识符行（>75% 是 camelCase/snake_case 标识符）
            # 保存这行的值，用于可能的列名修复
            ident_hits = sum(
                1 for v in non_null
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v) and 2 <= len(v) <= 60
            )
            if ident_hits / total > 0.75:
                skip = i + 1
                # 保存原始大小写的值，作为潜在的列名
                row_vals = [str(v).strip() for _, v in raw_vals]
                # 补全到完整列数（处理末尾空单元格）
                full_vals = []
                raw_idx = 0
                for j in range(len(df.columns)):
                    if raw_idx < len(raw_vals) and raw_vals[raw_idx][0] == j:
                        full_vals.append(raw_vals[raw_idx][1])
                        raw_idx += 1
                    else:
                        full_vals.append(f"_col_{j}")
                better_cols = full_vals
                continue

            # 判定3: c/s/cs 导出标记行（>70% 是导出作用域标记）
            marker_hits = sum(1 for v in non_null if v in self._EXPORT_MARKERS)
            if marker_hits / total > 0.7:
                skip = i + 1
                continue

            # 判定4: 注释行 — 即使 skip=0 也识别
            # 行内容几乎全是中文/文本，无数字，且首单元格含注释符或中文说明词
            numeric_hits = sum(1 for v in non_null if re.match(r'^-?\d+\.?\d*$', v))
            first_val = non_null[0] if non_null else ''
            is_comment = (
                numeric_hits / total < 0.05 and
                (first_val.startswith('//') or
                 first_val.startswith('#') or
                 first_val.startswith('/*') or
                 # 首单元格是纯中文说明（含"说明""注释""备注"等）
                 any(kw in first_val for kw in
                     ('说明', '注释', '备注', '注意', '描述', 'remark', 'note', 'desc')))
            )
            if is_comment:
                skip = i + 1
                continue

            # 判定5: 描述/注释行 — 仅在已检测到至少一行元数据时启用
            # 纯文本行（几乎无数字）夹在元数据行之间，通常是中文字段说明
            if skip > 0:
                if numeric_hits / total < 0.1:
                    skip = i + 1
                    continue

            # 当前行既不是元数据也不是描述行 — 停止检查
            break

        return skip, better_cols

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
                # 读全量行：nrows=None 表示不截断。
                # 若配置了 max_read_rows，则只读取前 N 行（用于内存受限场景）。
                # 注意：不再使用 max_sample_rows * 25 的隐式计算，两个参数职责分离。
                df = xls.parse(sn, nrows=self.max_read_rows)
                if df.empty or len(df.columns) == 0:
                    continue

                # 跳过看起来不是数据表的 sheet（列数 < 2 或行数 < 1）
                if len(df.columns) < 2 or len(df) < 1:
                    continue

                if self.max_read_rows and len(df) >= self.max_read_rows:
                    self.logger.warning(
                        f"  {file_path.name}/{sn}: 已达读取上限 {self.max_read_rows} 行，"
                        f"实际行数可能更多，建议调大 max_rows_per_table 配置"
                    )

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
        对每列收集采样数据（唯一值、类型推断、数值统计），适配大表。

        改进点：
        - unique_count / null_count 基于全量行计算，不受 sample_values 限制影响
        - sample_values 使用分层采样（头+中+尾均匀取点），保证数值范围覆盖
        - 数值列额外记录 stats: {min, max, mean}，供 FK 验证和数据分析使用

        Returns:
            {
                'col_name': {
                    'sample_values': [...],   # 分层采样后 top-K 唯一值
                    'dtype': str,             # int/float/str/mixed
                    'unique_count': int,      # 真实唯一值数量（全量统计）
                    'null_count': int,        # 空值数量
                    'total_count': int,       # 总行数
                    'stats': {...},           # 仅数值列：{min, max, mean}
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

            # 全量唯一值统计（不截断，保证 unique_count 准确）
            unique_vals = non_null.unique()
            unique_count = len(unique_vals)

            # 分层采样：均匀取 max_sample_rows 个唯一值（首+中+尾覆盖全范围）
            # 优于只取前 N 个——对大表 FK 和枚举发现更有代表性
            if unique_count > self.max_sample_rows:
                sample_values = _stratified_sample(unique_vals, self.max_sample_rows)
            else:
                sample_values = list(unique_vals)

            # 转为 Python 原生类型（避免 numpy 类型序列化问题）
            sample_values = [self._to_native(v) for v in sample_values]

            # 类型推断
            dtype = self._infer_dtype(col, non_null)

            col_info: Dict[str, Any] = {
                'sample_values': sample_values,
                'dtype': dtype,
                'unique_count': unique_count,
                'null_count': int(col.isna().sum()),
                'total_count': total_rows,
            }

            # 数值列：补充 min/max/mean 统计，用于后续 FK 验证和数据分析
            if dtype in ('int', 'float'):
                try:
                    numeric = pd.to_numeric(non_null, errors='coerce').dropna()
                    if len(numeric) > 0:
                        col_info['stats'] = {
                            'min': self._to_native(numeric.min()),
                            'max': self._to_native(numeric.max()),
                            'mean': round(float(numeric.mean()), 4),
                        }
                except Exception:
                    pass

            result[str(col_name)] = col_info

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
