#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
行级取数层 (Row-level Retrieval)

职责：
  1. 从自然语言 query 提取谓词（数值范围、ID 精确匹配、关键词模糊匹配）
  2. 按谓词回源读取 Excel，只返回命中行块（最多 max_rows 行）
  3. 结果以 RowBlock 列表返回，供证据组装层拼装 key_rows 段

用法示例：
    retriever = RowRetriever(data_root="./data")
    predicates = retriever.generate_predicates(query, table_schema)
    block = retriever.fetch_rows(table_schema, predicates, max_rows=20)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ──────────────────────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────────────────────

@dataclass
class Predicate:
    """单条过滤谓词"""
    column: str
    op: str          # eq | ne | gt | gte | lt | lte | contains | in
    value: Any
    source: str = ""  # 谓词来源说明（便于调试）

    def to_display(self) -> str:
        return f"{self.column} {self.op} {self.value!r}"


@dataclass
class RowBlock:
    """一张表的行级取数结果"""
    table_name: str
    file_path: str
    predicates_used: List[str]          # 已生效的谓词描述
    predicates_skipped: List[str]       # 列不存在而跳过的谓词
    rows: List[Dict[str, Any]]          # 匹配行（最多 max_rows 条）
    total_matched: int                  # 满足谓词的总行数（截断前）
    columns_returned: List[str]         # 返回的列名列表


# ──────────────────────────────────────────────────────────
# 谓词提取辅助
# ──────────────────────────────────────────────────────────

# 匹配裸数字（整数或小数，可带负号）
_NUM_RE = re.compile(r'-?\d+(?:\.\d+)?')

# 常见比较短语 → (op, offset_in_match)
_COMPARISON_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r'(?:>=|≥|不低于|至少)\s*(-?\d+(?:\.\d+)?)'), 'gte'),
    (re.compile(r'(?:<=|≤|不高于|至多|最多)\s*(-?\d+(?:\.\d+)?)'), 'lte'),
    (re.compile(r'(?:>|大于|超过)\s*(-?\d+(?:\.\d+)?)'),        'gt'),
    (re.compile(r'(?:<|小于|低于)\s*(-?\d+(?:\.\d+)?)'),        'lt'),
    (re.compile(r'(?:=|==|等于|是)\s*(-?\d+(?:\.\d+)?)'),       'eq'),
]

# 中文/英文 "范围" 表达：N 到 M、N~M、between N and M
_RANGE_RE = re.compile(
    r'(-?\d+(?:\.\d+)?)\s*(?:到|~|至|-|—|and)\s*(-?\d+(?:\.\d+)?)'
)


def _extract_numbers(text: str) -> List[float]:
    return [float(m) for m in _NUM_RE.findall(text)]


def _numeric_predicates_from_query(
    query: str,
    numeric_cols: List[str],
    col_hints: Dict[str, str],   # col_name → domain_role / metric_tag
) -> List[Predicate]:
    """
    从自然语言 query 中提取数值谓词。

    策略：
    1. 识别 query 中显式的比较符（>=、大于、between…）→ 生成范围谓词
    2. 将数值与数值列的 domain_role / metric_tag 做语义对齐
    3. 若 query 仅含裸数字，尝试与 PK/FK 候选列做精确匹配
    """
    predicates: List[Predicate] = []

    # 1. 范围表达式（N 到 M）
    for m in _RANGE_RE.finditer(query):
        lo, hi = float(m.group(1)), float(m.group(2))
        context = query[max(0, m.start() - 20): m.start()].lower()
        target_col = _guess_numeric_col(context, numeric_cols, col_hints)
        if target_col:
            predicates.append(Predicate(target_col, 'gte', lo, 'range_expr'))
            predicates.append(Predicate(target_col, 'lte', hi, 'range_expr'))

    # 2. 比较表达式
    for pat, op in _COMPARISON_PATTERNS:
        for m in pat.finditer(query):
            val = float(m.group(1))
            context = query[max(0, m.start() - 20): m.start()].lower()
            target_col = _guess_numeric_col(context, numeric_cols, col_hints)
            if target_col:
                predicates.append(Predicate(target_col, op, val, 'comparison_expr'))

    return predicates


def _guess_numeric_col(
    context: str,
    numeric_cols: List[str],
    col_hints: Dict[str, str],
) -> Optional[str]:
    """
    从上文关键词中猜测最相关的数值列。
    col_hints 是 {col_name: role_or_tag}，用于语义对齐。
    """
    context_lower = context.lower()
    best: Optional[str] = None
    best_score = 0
    for col in numeric_cols:
        col_lower = col.lower()
        # 列名直接出现在上文
        if col_lower in context_lower:
            score = len(col_lower) + 10
        else:
            hint = col_hints.get(col, '').lower()
            score = _substring_score(context_lower, hint)
        if score > best_score:
            best_score = score
            best = col
    return best if best_score > 0 else (numeric_cols[0] if numeric_cols else None)


def _substring_score(text: str, keywords: str) -> int:
    """计算 keywords 在 text 中的最长匹配片段长度之和。"""
    score = 0
    for kw in keywords.split('_'):
        if len(kw) >= 2 and kw in text:
            score += len(kw)
    return score


def _keyword_predicates_from_query(
    query: str,
    text_cols: List[str],
    enum_cols: Dict[str, List],
) -> List[Predicate]:
    """
    从 query 中提取关键词谓词（contains / in）。

    - 枚举列：若 query 中出现某枚举值 → eq 谓词
    - 文本列：若 query 含非数字词 → contains 谓词
    """
    predicates: List[Predicate] = []

    # 枚举列：精确值命中
    for col, vals in enum_cols.items():
        str_vals = [str(v) for v in vals if str(v) not in ('', 'None', 'nan')]
        for sv in str_vals:
            if sv and len(sv) >= 2 and sv.lower() in query.lower():
                predicates.append(Predicate(col, 'eq', sv, 'enum_match'))
                break  # 每列只取第一个命中

    # 文本列：提取中文/英文关键词
    words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', query)
    for col in text_cols:
        for w in words:
            if not _NUM_RE.fullmatch(w):
                predicates.append(Predicate(col, 'contains', w, 'keyword_search'))
                break  # 每文本列只取第一个关键词谓词

    return predicates


def _id_predicates_from_query(
    query: str,
    id_cols: List[str],
) -> List[Predicate]:
    """query 中的裸整数 → PK/FK 精确匹配谓词"""
    predicates: List[Predicate] = []
    nums = [int(float(n)) for n in _NUM_RE.findall(query)
            if '.' not in n and 1 <= len(n) <= 8]
    if nums and id_cols:
        # 默认只对第一个 ID 列生成谓词（避免爆炸）
        for col in id_cols[:2]:
            for n in nums[:5]:
                predicates.append(Predicate(col, 'eq', n, 'id_match'))
    return predicates


def _combine_predicate_masks(
    df: pd.DataFrame,
    predicates: List[Predicate],
) -> Tuple[pd.Series, List[str], List[str]]:
    """
    组合多条谓词掩码。

    规则：
    - 同列的范围谓词（gt/gte/lt/lte/ne）使用 AND，避免范围条件失效
    - 同列的多个 eq/in 谓词使用 OR，支持多个候选 ID / 枚举值
    - 不同列之间使用 AND，保证结果真正被过滤
    """
    used: List[str] = []
    skipped: List[str] = []
    per_column_masks: Dict[str, pd.Series] = {}
    per_column_mode: Dict[str, str] = {}

    for pred in predicates:
        if pred.column not in df.columns:
            skipped.append(pred.to_display())
            continue
        try:
            col_series = df[pred.column]
            new_mask = _apply_predicate(col_series, pred)
        except Exception:
            skipped.append(pred.to_display())
            continue

        mode = _predicate_combine_mode(pred)
        if pred.column not in per_column_masks:
            per_column_masks[pred.column] = new_mask
            per_column_mode[pred.column] = mode
        else:
            existing_mode = per_column_mode[pred.column]
            if existing_mode != mode:
                mode = 'and'
                per_column_mode[pred.column] = mode
            if mode == 'or':
                per_column_masks[pred.column] = per_column_masks[pred.column] | new_mask
            else:
                per_column_masks[pred.column] = per_column_masks[pred.column] & new_mask
        used.append(pred.to_display())

    if not per_column_masks:
        return pd.Series([True] * len(df), index=df.index), used, skipped

    mask = pd.Series([True] * len(df), index=df.index)
    for col_mask in per_column_masks.values():
        mask = mask & col_mask
    return mask, used, skipped


def _predicate_combine_mode(pred: Predicate) -> str:
    """返回谓词在同列内的组合模式：or 或 and。"""
    if pred.op in ('eq', '==', 'contains', 'in'):
        return 'or'
    return 'and'


# ──────────────────────────────────────────────────────────
# 主类
# ──────────────────────────────────────────────────────────

class RowRetriever:
    """
    按谓词从源 Excel 文件中取回相关行块。

    参数：
        data_root  — Excel 文件根目录，file_path 相对此目录解析
        header_cache — 可选的 {file_path: header_offset} 缓存，
                       避免重复检测表头行
    """

    def __init__(self, data_root: str = ".", header_cache: Optional[Dict[str, int]] = None):
        self.data_root = Path(data_root)
        self._header_cache: Dict[str, int] = header_cache or {}

    # ----------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------

    def generate_predicates(
        self,
        query: str,
        table_schema: Dict,
        max_predicates: int = 6,
    ) -> List[Predicate]:
        """
        从自然语言 query + 表 schema（table_profiles 中的一条 profile）推导谓词列表。

        table_schema 格式参考 export_table_profiles 的 profile 对象，
        关键字段：
            columns: [{name, dtype, semantic_type, domain_role, metric_tag,
                       is_pk, is_fk, is_enum, enum_values}]
            primary_key: str

        返回谓词按优先级排序，调用方可按需截断。
        """
        cols = table_schema.get('columns', [])
        pk = table_schema.get('primary_key')

        # 分类列
        id_cols = [c['name'] for c in cols
                   if c.get('semantic_type') == 'identifier' or c['name'] == pk]
        numeric_cols = [c['name'] for c in cols
                        if c.get('dtype') in ('int', 'float')
                        and c.get('semantic_type') not in ('identifier',)]
        text_cols = [c['name'] for c in cols
                     if c.get('semantic_type') in ('descriptor', 'text')]
        enum_cols = {c['name']: c.get('enum_values', []) for c in cols
                     if c.get('is_enum') and c.get('enum_values')}

        # col_name → hint（domain_role 或 metric_tag，供数值对齐）
        col_hints = {}
        for c in cols:
            hint = c.get('metric_tag') or c.get('domain_role') or ''
            col_hints[c['name']] = hint

        all_preds: List[Predicate] = []

        # 1. ID 精确匹配（优先级最高）
        all_preds += _id_predicates_from_query(query, id_cols)

        # 2. 枚举 / 文本关键词
        all_preds += _keyword_predicates_from_query(query, text_cols, enum_cols)

        # 3. 数值范围
        all_preds += _numeric_predicates_from_query(query, numeric_cols, col_hints)

        # 去重同列谓词（保留最先出现的）
        seen: Dict[str, bool] = {}
        unique: List[Predicate] = []
        for p in all_preds:
            key = f"{p.column}:{p.op}:{p.value}"
            if key not in seen:
                seen[key] = True
                unique.append(p)

        return unique[:max_predicates]

    def fetch_rows(
        self,
        table_schema: Dict,
        predicates: List[Predicate],
        max_rows: int = 30,
        return_cols: Optional[List[str]] = None,
    ) -> RowBlock:
        """
        按谓词回源读取 Excel，返回命中行块。

        参数：
            table_schema  — table_profiles 中的 profile 对象
            predicates    — generate_predicates() 的输出
            max_rows      — 最多返回行数（截断超大结果集）
            return_cols   — 指定返回的列子集；None 则返回所有列

        返回：
            RowBlock（包含行列表、命中总数、使用/跳过的谓词信息）
        """
        table_name = table_schema.get('table_name', '')
        file_rel = table_schema.get('file', '')
        sheet = table_schema.get('sheet') or 0
        header_offset = table_schema.get('header_offset', 0)

        # 解析文件路径
        file_path = self._resolve_path(table_schema)
        if not file_path or not file_path.exists():
            return RowBlock(
                table_name=table_name,
                file_path=str(file_path) if file_path else file_rel,
                predicates_used=[],
                predicates_skipped=[p.to_display() for p in predicates],
                rows=[],
                total_matched=0,
                columns_returned=[],
            )

        # 读取 DataFrame
        df = self._read_df(file_path, sheet, header_offset)
        if df is None or df.empty:
            return RowBlock(
                table_name=table_name,
                file_path=str(file_path),
                predicates_used=[],
                predicates_skipped=[p.to_display() for p in predicates],
                rows=[],
                total_matched=0,
                columns_returned=list(df.columns) if df is not None else [],
            )

        # 应用谓词
        mask, used, skipped = _combine_predicate_masks(df, predicates)

        # 若所有谓词都跳过（无法过滤），返回前 max_rows 行作为样本
        if not used:
            result_df = df.head(max_rows)
            total = len(df)
        else:
            result_df = df[mask]
            total = len(result_df)
            result_df = result_df.head(max_rows)

        # 列裁剪
        if return_cols:
            cols_to_return = [c for c in return_cols if c in result_df.columns]
            result_df = result_df[cols_to_return]
        cols_returned = list(result_df.columns)

        # 转为 JSON 友好格式
        rows = _df_to_records(result_df)

        return RowBlock(
            table_name=table_name,
            file_path=str(file_path),
            predicates_used=used,
            predicates_skipped=skipped,
            rows=rows,
            total_matched=total,
            columns_returned=cols_returned,
        )

    # ----------------------------------------------------------
    # 内部辅助
    # ----------------------------------------------------------

    def _resolve_path(self, table_schema: Dict) -> Optional[Path]:
        """从 profile 解析真实文件路径"""
        file_name = table_schema.get('file', '')
        if not file_name:
            return None
        candidate = self.data_root / file_name
        if candidate.exists():
            return candidate
        # 递归搜索子目录
        for p in self.data_root.rglob(file_name):
            return p
        return candidate  # 即使不存在也返回（调用方会判断）

    def _read_df(
        self,
        file_path: Path,
        sheet,
        header_offset: int,
    ) -> Optional[pd.DataFrame]:
        """读取 Excel / CSV，跳过已知表头偏移行。"""
        suffix = file_path.suffix.lower()
        try:
            if suffix in ('.xlsx', '.xls'):
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet,
                    header=header_offset,
                    dtype=str,   # 全部读为字符串，避免类型转换失真
                )
            elif suffix in ('.csv', '.tsv'):
                sep = '\t' if suffix == '.tsv' else ','
                df = pd.read_csv(
                    file_path,
                    sep=sep,
                    skiprows=header_offset,
                    dtype=str,
                )
            else:
                return None
            # 清理列名
            df.columns = [str(c).strip() for c in df.columns]
            # 去掉全空行
            df = df.dropna(how='all')
            return df
        except Exception:
            return None


# ──────────────────────────────────────────────────────────
# 谓词执行
# ──────────────────────────────────────────────────────────

def _apply_predicate(series: pd.Series, pred: Predicate) -> pd.Series:
    """将单条 Predicate 作用于 Series，返回布尔掩码。"""
    op = pred.op
    val = pred.value

    if op == 'contains':
        return series.astype(str).str.contains(str(val), case=False, na=False)

    # 数值型操作：先尝试转换
    try:
        num_series = pd.to_numeric(series, errors='coerce')
        num_val = float(val)
        if op in ('eq', '=='):
            return num_series == num_val
        if op in ('ne', '!='):
            return num_series != num_val
        if op in ('gt', '>'):
            return num_series > num_val
        if op in ('gte', '>='):
            return num_series >= num_val
        if op in ('lt', '<'):
            return num_series < num_val
        if op in ('lte', '<='):
            return num_series <= num_val
    except (ValueError, TypeError):
        pass

    # 字符串精确匹配
    if op in ('eq', '=='):
        return series.astype(str) == str(val)
    if op == 'in':
        str_vals = [str(v) for v in val] if isinstance(val, list) else [str(val)]
        return series.astype(str).isin(str_vals)

    return pd.Series([False] * len(series), index=series.index)


# ──────────────────────────────────────────────────────────
# DataFrame → JSON 友好 records
# ──────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """将 DataFrame 转为 List[Dict]，过滤 NaN / NaT。"""
    records = []
    for _, row in df.iterrows():
        rec = {}
        for col, val in row.items():
            if pd.isna(val) if not isinstance(val, str) else False:
                continue
            str_val = str(val).strip()
            if str_val in ('', 'nan', 'None', 'NaT', '<NA>'):
                continue
            rec[col] = str_val
        records.append(rec)
    return records
