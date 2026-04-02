#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析聚合层 (Analytical Aggregator)

面向游戏策划数值分析：在 Python 侧对全量数据做精确聚合，
将结果以紧凑表格形式给 LLM，避免采样导致分析失真。

用法：
    agg = AnalyticalAggregator(data_root="./data")
    df = agg.fetch_table(profile)
    result = agg.full_table_analytics(df, profile)
    # result 可直接序列化为 JSON 或格式化为 prompt 文本
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


class AnalyticalAggregator:
    """
    游戏策划表分析聚合器。

    参数：
        data_root — Excel 文件根目录
    """

    def __init__(self, data_root: str = "."):
        self.data_root = Path(data_root)

    def fetch_table(
        self,
        table_schema: Dict,
        predicates: Optional[List] = None,
    ) -> Optional[pd.DataFrame]:
        """
        回源加载表数据（全量或谓词过滤），返回 DataFrame。

        参数：
            table_schema — table_profiles 中的 profile 对象
            predicates    — 可选，Predicate 列表；为 None 时返回全表

        返回：
            DataFrame 或 None（文件不存在/读取失败时）
        """
        from .row_retriever import RowRetriever, _apply_predicate

        retriever = RowRetriever(data_root=str(self.data_root))
        file_path = retriever._resolve_path(table_schema)
        if not file_path or not file_path.exists():
            return None

        sheet = table_schema.get('sheet') or 0
        header_offset = table_schema.get('header_offset', 0)
        df = retriever._read_df(file_path, sheet, header_offset)
        if df is None or df.empty:
            return None

        if predicates:
            mask = pd.Series([False] * len(df), index=df.index)
            for pred in predicates:
                if pred.column in df.columns:
                    try:
                        mask = mask | _apply_predicate(df[pred.column], pred)
                    except Exception:
                        pass
            if mask.any():
                df = df[mask]

        return df

    def full_table_analytics(
        self,
        df: pd.DataFrame,
        table_schema: Dict,
        max_enum_values: int = 20,
        max_outliers: int = 10,
    ) -> Dict[str, Any]:
        """
        对全表做综合数值分析，返回紧凑结果（不丢数据，全量统计）。

        自动识别：
        - 枚举/档位列（is_enum 或 semantic_type=enum/identifier 且唯一值≤max_enum_values）
        - 数值列（dtype=int/float 且 semantic_type=metric 或非 identifier）

        对每个枚举列：groupby → count + 各数值列的 mean/min/max/p50/p90
        对全体数值列：整体 stats + 离群值检测（IQR 法）

        返回结构：
        {
          "table": "hero_base",
          "row_count": 1500,
          "groupby_stats": [
            {
              "group_col": "quality",
              "groups": [
                {"value": 1, "count": 52, "atk_mean": 210, "atk_min": 100, "atk_max": 320, ...},
                {"value": 2, "count": 118, ...},
                ...
              ],
              "metric_cols": ["atk", "hp", "def"]
            },
            ...
          ],
          "global_stats": {
            "atk": {"count": 1500, "mean": 520, "min": 80, "max": 1200, "p50": 480, "p90": 850},
            ...
          },
          "outliers": {
            "atk": {"high": [{"id": 1234, "atk": 950, "quality": 3}, ...], "low": [...]},
            ...
          }
        }
        """
        table_name = table_schema.get('table_name', '')
        cols_info = {c['name']: c for c in table_schema.get('columns', [])}
        pk = table_schema.get('primary_key')

        # 识别枚举/档位列（排除主键、排除唯一值=行数的列）
        enum_cols: List[str] = []
        for col in table_schema.get('columns', []):
            cn = col['name']
            if cn not in df.columns:
                continue
            if cn == pk:
                continue
            n_unique = df[cn].nunique()
            if n_unique == len(df) or n_unique < 2:
                continue
            if col.get('is_enum'):
                enum_cols.append(cn)
            elif col.get('semantic_type') in ('enum', 'identifier'):
                if 2 <= n_unique <= max_enum_values:
                    enum_cols.append(cn)

        # 识别数值列（排除主键若其为纯 ID）
        # 注意：RowRetriever._read_df 会把 Excel/CSV 全部按 str 读入，
        # 这里必须以 schema dtype 为准，而不能依赖 DataFrame 当前 dtype。
        metric_cols: List[str] = []
        for col in table_schema.get('columns', []):
            cn = col['name']
            if cn not in df.columns:
                continue
            if col.get('semantic_type') == 'identifier' and cn == pk:
                continue
            if col.get('semantic_type') == 'metric' or col.get('dtype') in ('int', 'float'):
                metric_cols.append(cn)

        result: Dict[str, Any] = {
            'table': table_name,
            'row_count': len(df),
            'groupby_stats': [],
            'global_stats': {},
            'outliers': {},
        }

        # 数值列转 float 便于统计
        for mc in metric_cols:
            df[mc] = pd.to_numeric(df[mc], errors='coerce')

        # ── 1. 分组统计（每个枚举列 × 各数值列）──
        for gc in enum_cols:
            if gc not in df.columns:
                continue
            valid_metrics = [m for m in metric_cols if m in df.columns and m != gc]
            if not valid_metrics:
                continue

            try:
                grp = df.groupby(gc, dropna=False)
                count_ser = grp.size()

                groups = []
                for gval in count_ser.index:
                    rec = {
                        'value': self._to_native(gval),
                        'count': int(count_ser.loc[gval]),
                    }
                    sub_df = df[df[gc] == gval]
                    for m in valid_metrics:
                        s = sub_df[m].dropna()
                        if len(s) > 0:
                            rec[f'{m}_mean'] = round(float(s.mean()), 4)
                            rec[f'{m}_min'] = self._to_native(s.min())
                            rec[f'{m}_max'] = self._to_native(s.max())
                            rec[f'{m}_p50'] = self._to_native(s.quantile(0.5))
                            rec[f'{m}_p90'] = self._to_native(s.quantile(0.9))
                    groups.append(rec)

                result['groupby_stats'].append({
                    'group_col': gc,
                    'groups': groups,
                    'metric_cols': valid_metrics,
                })
            except Exception:
                continue

        # ── 2. 全局统计 ──
        for m in metric_cols:
            s = df[m].dropna()
            if len(s) == 0:
                continue
            result['global_stats'][m] = {
                'count': int(s.count()),
                'mean': round(float(s.mean()), 4),
                'min': self._to_native(s.min()),
                'max': self._to_native(s.max()),
                'p50': self._to_native(s.quantile(0.5)),
                'p90': self._to_native(s.quantile(0.90)),
            }

        # ── 3. 离群值检测（IQR 法）──
        for m in metric_cols:
            s = df[m].dropna()
            if len(s) < 10:
                continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr <= 0:
                continue
            low_bound = q1 - 1.5 * iqr
            high_bound = q3 + 1.5 * iqr
            low_vals = df[df[m] < low_bound][[pk, m] if pk and pk in df.columns else [m]].head(max_outliers)
            high_vals = df[df[m] > high_bound][[pk, m] if pk and pk in df.columns else [m]].sort_values(m, ascending=False).head(max_outliers)
            result['outliers'][m] = {
                'high': self._records_from_df(high_vals),
                'low': self._records_from_df(low_vals),
            }

        return result

    def groupby_stats(
        self,
        df: pd.DataFrame,
        group_col: str,
        agg_cols: List[str],
        agg_funcs: Optional[Dict[str, List[str]]] = None,
    ) -> List[Dict]:
        """
        按指定列分组统计。

        参数：
            df         — 源数据
            group_col  — 分组列
            agg_cols   — 待聚合的数值列
            agg_funcs  — 可选，{col: ['mean','min','max']}；默认每列 mean/min/max

        返回：
            [{"group_value": v, "count": n, "atk_mean": x, ...}, ...]
        """
        if group_col not in df.columns:
            return []
        agg_cols = [c for c in agg_cols if c in df.columns]
        if not agg_cols:
            return []

        agg_funcs = agg_funcs or {c: ['mean', 'min', 'max'] for c in agg_cols}
        grp = df.groupby(group_col, dropna=False)
        result = grp.size().reset_index(name='count')

        for col in agg_cols:
            funcs = agg_funcs.get(col, ['mean', 'min', 'max'])
            agg_df = grp[col].agg(funcs).reset_index()
            agg_df.columns = [group_col] + [f'{col}_{f}' for f in funcs]
            result = result.merge(agg_df, on=group_col, how='left')

        return [
            {**{'group_value': self._to_native(row[group_col]), 'count': int(row['count'])},
             **{k: self._to_native(row[k]) for k in row.index if k != group_col and k != 'count' and pd.notna(row.get(k))}}
            for _, row in result.iterrows()
        ]

    def to_prompt_text(self, analytics: Dict, max_groups_display: int = 15) -> str:
        """
        将 full_table_analytics 结果格式化为 LLM 可读的紧凑文本。
        """
        lines: List[str] = []
        lines.append(f"## 表 {analytics['table']} 数值分析（全量 {analytics['row_count']} 行）\n")

        # 分组统计
        for gs in analytics.get('groupby_stats', []):
            gc = gs['group_col']
            groups = gs['groups'][:max_groups_display]
            metrics = gs.get('metric_cols', [])
            lines.append(f"### 按 {gc} 分组")
            header = f"| {gc} | count | " + " | ".join(f"{m}(mean/min/max)" for m in metrics) + " |"
            lines.append(header)
            lines.append("|" + "---|" * (2 + len(metrics)) + "")
            for g in groups:
                cells = [str(g['value']), str(g['count'])]
                for m in metrics:
                    mm = g.get(f'{m}_mean')
                    mn = g.get(f'{m}_min')
                    mx = g.get(f'{m}_max')
                    cells.append(f"{mm}/{mn}/{mx}" if all(x is not None for x in (mm, mn, mx)) else "-")
                lines.append("| " + " | ".join(str(c) for c in cells) + " |")
            if len(gs['groups']) > max_groups_display:
                lines.append(f"（共 {len(gs['groups'])} 组，仅展示前 {max_groups_display} 组）")
            lines.append("")

        # 全局统计
        gs = analytics.get('global_stats', {})
        if gs:
            lines.append("### 全局统计")
            for col, v in gs.items():
                lines.append(f"- **{col}**: count={v['count']} mean={v['mean']} "
                             f"min={v['min']} max={v['max']} p50={v.get('p50')} p90={v.get('p90')}")

        # 离群值
        out = analytics.get('outliers', {})
        if out:
            lines.append("\n### 离群值（IQR 法）")
            for col, v in out.items():
                high = v.get('high', [])[:5]
                low = v.get('low', [])[:5]
                if high:
                    lines.append(f"- **{col} 偏高**: {high}")
                if low:
                    lines.append(f"- **{col} 偏低**: {low}")

        return "\n".join(lines)

    @staticmethod
    def _to_native(v: Any) -> Any:
        if pd.isna(v):
            return None
        if hasattr(v, 'item'):
            return v.item()
        return v

    def _records_from_df(self, df: pd.DataFrame) -> List[Dict]:
        if df.empty:
            return []
        recs = []
        for _, row in df.iterrows():
            d = {k: self._to_native(v) for k, v in row.items() if pd.notna(v)}
            if d:
                recs.append(d)
        return recs


