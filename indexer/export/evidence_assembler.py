#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
证据组装层 (Evidence Assembly)

将 RAG 召回链路中已确定相关的表集合，按照固定四段结构组装成
发送给 LLM 的上下文输入，控制 token 消耗并保持结构清晰。

四段结构
--------
1. schema      — 每张相关表的"列级裁剪后的"列 schema
                 只保留与 query 语义相关的列（semantic_type / domain_role 筛选）

2. join        — 相关表集合之间的 JOIN 路径（来自 join_paths.json）

3. key_rows    — 按 query 谓词从源文件取回的命中行块
                 （调用 RowRetriever.fetch_rows）

4. stat_summary — 相关数值 / 枚举列的统计摘要（min/max/mean/enum_values）

使用示例
--------
    from indexer.export.evidence_assembler import EvidenceAssembler

    assembler = EvidenceAssembler(
        profiles_path="./graph/table_profiles.jsonl",
        join_paths_path="./graph/join_paths.json",
        data_root="./data",
    )
    evidence = assembler.assemble(
        query="英雄攻击力大于500的英雄id列表",
        table_names=["hero_base"],
    )
    # evidence 可直接序列化为 JSON 或格式化为 Prompt 文本
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ──────────────────────────────────────────────────────────
# 列级裁剪策略
# ──────────────────────────────────────────────────────────

# 这些 semantic_type 总是保留（核心结构列）
_ALWAYS_KEEP_TYPES: Set[str] = {'identifier', 'flag', 'enum'}

# 这些 domain_role 总是保留（关键业务角色）
_ALWAYS_KEEP_ROLES: Set[str] = {'id_key', 'type_category', 'level_grade'}

# 最大保留列数（超宽表裁剪）
_MAX_COLS_PER_TABLE = 25

_ANALYSIS_QUERY_KEYWORDS: Set[str] = {
    '分析', '平衡', '平衡性', '风险', '泄露', '异常', '离群', '分布', '统计',
    '均值', '平均', '中位', '分位', '波动', '趋势', '对比', '商业化', '掉落',
    '概率', '成长', '超模', 'balance', 'risk', 'anomaly', 'outlier',
    'distribution', 'stats', 'mean', 'median', 'percentile', 'analyze',
}

_ANALYSIS_FOCUS_HINTS: List[str] = [
    '数值分布', '档位差异', '异常值', '趋势变化', '平衡性风险'
]

_LOOKUP_FOCUS_HINTS: List[str] = [
    '关键配置项', '表间关联链路', '命中样例行', '可追溯数据来源'
]

_MAX_VISIBLE_GROUPS_PER_ANALYTICS = 8
_MAX_VISIBLE_GLOBAL_STATS = 8
_MAX_VISIBLE_OUTLIER_METRICS = 6


def _select_columns(
    columns: List[Dict],
    query_lower: str,
    max_cols: int = _MAX_COLS_PER_TABLE,
) -> List[Dict]:
    """
    按查询语义裁剪列：

    优先级：
      1. 主键 / FK / 枚举 / flag（结构性列）
      2. 列名或 metric_tag / domain_role 与 query 有词语重叠
      3. metric 类型的数值列（统计摘要必备）
      4. 描述性列（name / desc 等）
      5. 其余列按原序填充至 max_cols
    """
    scored: List[tuple] = []  # (score, col)

    for col in columns:
        score = 0
        sem = col.get('semantic_type', '')
        role = col.get('domain_role', '') or ''
        tag = col.get('metric_tag', '') or ''
        name_lower = col.get('name', '').lower()

        # 结构必须列
        if col.get('is_pk'):
            score += 100
        if col.get('is_fk'):
            score += 50
        if sem in _ALWAYS_KEEP_TYPES:
            score += 30
        if role in _ALWAYS_KEEP_ROLES:
            score += 20

        # query 语义匹配
        for kw in (name_lower, role, tag):
            if kw and _token_overlap(kw, query_lower) > 0:
                score += 15

        # metric 列（需要 stat_summary 支撑）
        if sem == 'metric':
            score += 10

        # 描述列
        if sem == 'descriptor':
            score += 5

        scored.append((score, col))

    scored.sort(key=lambda x: -x[0])
    return [col for _, col in scored[:max_cols]]


def _token_overlap(a: str, b: str) -> int:
    """计算两个字符串之间的词素重叠数（用 _ 分词）"""
    tokens_a = set(t for t in a.replace('-', '_').split('_') if len(t) >= 2)
    tokens_b = set(t for t in b.replace('-', '_').split('_') if len(t) >= 2)
    return len(tokens_a & tokens_b)


def _is_analysis_query(query: str) -> bool:
    """根据 query 关键词自动判定是否启用全量数值分析模式。"""
    q = query.lower()
    return any(kw in q for kw in _ANALYSIS_QUERY_KEYWORDS)


# ──────────────────────────────────────────────────────────
# 统计摘要辅助
# ──────────────────────────────────────────────────────────

def _build_stat_summary(profiles: List[Dict], selected_cols_map: Dict[str, List[Dict]]) -> List[Dict]:
    """
    为每张表中被选中的 metric / enum 列生成统计摘要条目。

    返回格式：
    [
      {
        "table": "hero_base",
        "column": "atk",
        "semantic_type": "metric",
        "metric_tag": "attack",
        "min": 100, "max": 2000, "mean": 650.3,
        "unique_count": 450
      },
      {
        "table": "hero_base",
        "column": "quality",
        "semantic_type": "enum",
        "domain_role": "level_grade",
        "enum_values": [1, 2, 3, 4, 5],
        "unique_count": 5
      },
      ...
    ]
    """
    summary: List[Dict] = []
    profile_map = {p['table_name']: p for p in profiles}

    for table_name, sel_cols in selected_cols_map.items():
        profile = profile_map.get(table_name)
        if not profile:
            continue
        for col in sel_cols:
            sem = col.get('semantic_type', '')
            entry: Dict[str, Any] = {
                'table': table_name,
                'column': col['name'],
                'semantic_type': sem,
            }
            if col.get('domain_role'):
                entry['domain_role'] = col['domain_role']
            if col.get('metric_tag'):
                entry['metric_tag'] = col['metric_tag']
            entry['unique_count'] = col.get('unique_count', 0)

            if sem == 'metric' and col.get('stats'):
                stats = col['stats']
                entry['min'] = stats.get('min')
                entry['max'] = stats.get('max')
                entry['mean'] = round(stats['mean'], 4) if stats.get('mean') is not None else None
                summary.append(entry)

            elif col.get('is_enum') and col.get('enum_values'):
                entry['enum_values'] = col['enum_values'][:20]
                summary.append(entry)

    return summary


def _build_question_focus(
    query: str,
    table_names: List[str],
    analysis_mode: bool,
) -> Dict[str, Any]:
    return {
        'question': query,
        'mode': 'analysis' if analysis_mode else 'lookup',
        'focus': (
            '优先根据全量统计、分组分布和离群值来判断配置特征与潜在风险。'
            if analysis_mode else
            '优先根据命中配置样例、表结构和表间关联来回答具体规则与配置含义。'
        ),
        'coverage': (
            _ANALYSIS_FOCUS_HINTS[:] if analysis_mode else _LOOKUP_FOCUS_HINTS[:]
        ),
        'table_scope': table_names,
    }


def _summarize_table_role(schema_item: Dict[str, Any]) -> str:
    description = (schema_item.get('description') or '').strip()
    columns = schema_item.get('columns', [])
    key_cols = [c.get('name') for c in columns[:4] if c.get('name')]
    pk = schema_item.get('primary_key')

    if description:
        return description
    if pk and key_cols:
        return f"以 {pk} 为主键，围绕 {', '.join(key_cols[:3])} 等关键字段组织配置。"
    if key_cols:
        return f"包含 {', '.join(key_cols[:4])} 等与当前问题相关的字段。"
    return "与当前问题相关的配置表。"


def _build_table_roles(
    schema_section: List[Dict[str, Any]],
    profile_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    roles: List[Dict[str, Any]] = []
    for item in schema_section:
        tname = item.get('table')
        profile = profile_map.get(tname, {})
        roles.append({
            'table': tname,
            'file': profile.get('file', ''),
            'sheet': profile.get('sheet', ''),
            'domain': item.get('domain', profile.get('domain', 'other')),
            'row_count': item.get('row_count', 0),
            'primary_key': item.get('primary_key'),
            'selected_columns': [c.get('name') for c in item.get('columns', []) if c.get('name')],
            'role': _summarize_table_role(item),
        })
    return roles


def _build_join_story(
    join_section: List[Dict[str, Any]],
    role_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    stories: List[Dict[str, Any]] = []
    for item in join_section:
        src = item.get('from')
        dst = item.get('to')
        joins = item.get('joins', [])
        src_role = role_map.get(src, {}).get('role', '')
        dst_role = role_map.get(dst, {}).get('role', '')
        if joins:
            join_text = ' -> '.join(joins)
            meaning = (
                f"{src} 通过 {join_text} 关联到 {dst}，"
                f"可把 {src_role or '上游配置'} 与 {dst_role or '下游配置'} 串成同一条业务链路。"
            )
        else:
            meaning = f"{src} 与 {dst} 之间存在可用的表间关联。"
        stories.append({
            'from': src,
            'to': dst,
            'hops': item.get('hops', 1),
            'joins': joins,
            'min_confidence': item.get('min_confidence', 0),
            'business_meaning': meaning,
        })
    return stories


def _build_trend_hints(
    stat_summary: List[Dict[str, Any]],
    analytical_result: List[Dict[str, Any]],
) -> List[str]:
    hints: List[str] = []

    for stat in stat_summary:
        if stat.get('semantic_type') != 'metric':
            continue
        table = stat.get('table')
        col = stat.get('column')
        min_val = stat.get('min')
        max_val = stat.get('max')
        mean_val = stat.get('mean')
        if min_val is None or max_val is None:
            continue
        hint = f"{table}.{col} 的取值范围为 {min_val} ~ {max_val}"
        if mean_val is not None:
            hint += f"，均值约 {mean_val}"
        hint += "，可用于判断数值跨度和波动区间。"
        hints.append(hint)
        if len(hints) >= 6:
            break

    for analytics in analytical_result:
        table = analytics.get('table')
        for group_stat in analytics.get('groupby_stats', [])[:2]:
            group_col = group_stat.get('group_col')
            groups = group_stat.get('groups', [])
            if len(groups) >= 2:
                hints.append(
                    f"{table} 按 {group_col} 可分成 {len(groups)} 组，适合比较不同档位/类型之间的配置差异。"
                )
        for metric_col, metric_stats in list(analytics.get('global_stats', {}).items())[:2]:
            p50 = metric_stats.get('p50')
            p90 = metric_stats.get('p90')
            max_val = metric_stats.get('max')
            if p50 not in (None, 0) and p90 not in (None, 0):
                if p90 >= p50 * 1.5:
                    hints.append(
                        f"{table}.{metric_col} 的 p90 明显高于 p50，说明高位段拉升较明显。"
                    )
            if p90 not in (None, 0) and max_val not in (None, 0):
                if max_val >= p90 * 1.3:
                    hints.append(
                        f"{table}.{metric_col} 的最大值明显高于高分位区间，存在需要重点复核的高值样本。"
                    )
        for metric_col, outlier_info in analytics.get('outliers', {}).items():
            if outlier_info.get('high') or outlier_info.get('low'):
                hints.append(
                    f"{table}.{metric_col} 存在离群值样本，适合重点检查异常档位或特殊配置。"
                )
            if len(hints) >= 10:
                break
        if len(hints) >= 10:
            break

    deduped: List[str] = []
    seen: Set[str] = set()
    for hint in hints:
        if hint not in seen:
            seen.add(hint)
            deduped.append(hint)
    return deduped[:10]


def _build_sources(
    table_names: List[str],
    profile_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    for tname in table_names:
        profile = profile_map.get(tname, {})
        sources.append({
            'table': tname,
            'file': profile.get('file', ''),
            'sheet': profile.get('sheet', ''),
            'domain': profile.get('domain', 'other'),
        })
    return sources


def _build_hidden_but_available(
    schema_section: List[Dict[str, Any]],
    join_section: List[Dict[str, Any]],
    key_rows_section: List[Dict[str, Any]],
    analytical_section: List[Dict[str, Any]],
) -> Dict[str, Any]:
    schema_hidden = []
    for item in schema_section:
        hidden_cols = max(0, int(item.get('total_columns', 0)) - int(item.get('selected_columns', 0)))
        if hidden_cols > 0:
            schema_hidden.append({
                'table': item.get('table'),
                'hidden_columns': hidden_cols,
                'selected_columns': item.get('selected_columns', 0),
                'total_columns': item.get('total_columns', 0),
            })

    rows_hidden = []
    for item in key_rows_section:
        hidden_rows = max(0, int(item.get('total_matched', 0)) - int(item.get('rows_returned', 0)))
        if hidden_rows > 0:
            rows_hidden.append({
                'table': item.get('table'),
                'hidden_rows': hidden_rows,
                'rows_returned': item.get('rows_returned', 0),
                'total_matched': item.get('total_matched', 0),
            })

    analytics_hidden = []
    for item in analytical_section:
        hidden_group_cols = []
        for gs in item.get('groupby_stats', []):
            group_count = len(gs.get('groups', []))
            if group_count > _MAX_VISIBLE_GROUPS_PER_ANALYTICS:
                hidden_group_cols.append({
                    'group_col': gs.get('group_col'),
                    'total_groups': group_count,
                    'visible_groups': min(group_count, _MAX_VISIBLE_GROUPS_PER_ANALYTICS),
                })
        hidden_global_stats = max(0, len(item.get('global_stats', {})) - _MAX_VISIBLE_GLOBAL_STATS)
        hidden_outlier_metrics = max(0, len(item.get('outliers', {})) - _MAX_VISIBLE_OUTLIER_METRICS)
        if hidden_group_cols or hidden_global_stats > 0 or hidden_outlier_metrics > 0:
            analytics_hidden.append({
                'table': item.get('table'),
                'hidden_group_columns': hidden_group_cols,
                'hidden_global_stats': hidden_global_stats,
                'hidden_outlier_metrics': hidden_outlier_metrics,
            })

    return {
        'schema': schema_hidden,
        'join': {
            'total_paths': len(join_section),
            'all_paths_available': bool(join_section),
        },
        'rows': rows_hidden,
        'analytics': analytics_hidden,
    }


def _build_fetch_hints(
    query: str,
    table_names: List[str],
    schema_section: List[Dict[str, Any]],
    join_section: List[Dict[str, Any]],
    key_rows_section: List[Dict[str, Any]],
    analytical_section: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    hints: List[Dict[str, Any]] = []

    for item in schema_section:
        total_cols = int(item.get('total_columns', 0))
        selected_cols = int(item.get('selected_columns', 0))
        if total_cols > selected_cols:
            hints.append({
                'type': 'expand_schema',
                'table': item.get('table'),
                'reason': f"当前仅展示 {selected_cols}/{total_cols} 列，可继续拉取完整 schema。",
                'suggested_args': {
                    'table': item.get('table'),
                    'include_all_columns': True,
                },
            })

    for item in key_rows_section:
        total_matched = int(item.get('total_matched', 0))
        rows_returned = int(item.get('rows_returned', 0))
        if total_matched > rows_returned:
            hints.append({
                'type': 'expand_rows',
                'table': item.get('table'),
                'reason': f"当前仅展示 {rows_returned}/{total_matched} 行命中结果，可继续翻页或放宽返回上限。",
                'suggested_args': {
                    'table': item.get('table'),
                    'query': query,
                    'offset': rows_returned,
                    'limit': min(100, total_matched - rows_returned),
                },
            })

    for item in analytical_section:
        for gs in item.get('groupby_stats', []):
            group_count = len(gs.get('groups', []))
            if group_count > _MAX_VISIBLE_GROUPS_PER_ANALYTICS:
                hints.append({
                    'type': 'expand_analysis_groups',
                    'table': item.get('table'),
                    'reason': (
                        f"{item.get('table')}.{gs.get('group_col')} 的分组统计共 {group_count} 组，"
                        f"当前建议首屏只看前 {_MAX_VISIBLE_GROUPS_PER_ANALYTICS} 组。"
                    ),
                    'suggested_args': {
                        'table': item.get('table'),
                        'group_col': gs.get('group_col'),
                        'include_all_groups': True,
                    },
                })
        if len(item.get('global_stats', {})) > _MAX_VISIBLE_GLOBAL_STATS:
            hints.append({
                'type': 'expand_global_stats',
                'table': item.get('table'),
                'reason': f"{item.get('table')} 还有更多数值列统计未在首屏展示，可继续拉取完整全局统计。",
                'suggested_args': {
                    'table': item.get('table'),
                    'include_all_metrics': True,
                },
            })

    if len(table_names) >= 2 and join_section:
        hints.append({
            'type': 'expand_join_paths',
            'reason': "如需解释更完整的业务链路，可继续拉取涉及表之间的全部 JOIN 路径。",
            'suggested_args': {
                'tables': table_names,
                'include_all_join_paths': True,
            },
        })

    return hints[:12]


def _build_visible_analytics_summary(analytical_section: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    visible: List[Dict[str, Any]] = []
    for item in analytical_section:
        visible_item = {
            'table': item.get('table'),
            'row_count': item.get('row_count', 0),
            'groupby_stats': [],
            'global_stats': {},
            'outliers': {},
        }
        for gs in item.get('groupby_stats', []):
            visible_item['groupby_stats'].append({
                'group_col': gs.get('group_col'),
                'metric_cols': gs.get('metric_cols', []),
                'groups': (gs.get('groups') or [])[:_MAX_VISIBLE_GROUPS_PER_ANALYTICS],
                'total_groups': len(gs.get('groups', [])),
            })
        for metric_name, stats in list(item.get('global_stats', {}).items())[:_MAX_VISIBLE_GLOBAL_STATS]:
            visible_item['global_stats'][metric_name] = stats
        for metric_name, outlier_info in list(item.get('outliers', {}).items())[:_MAX_VISIBLE_OUTLIER_METRICS]:
            visible_item['outliers'][metric_name] = outlier_info
        visible.append(visible_item)
    return visible


# ──────────────────────────────────────────────────────────
# JOIN 路径提取
# ──────────────────────────────────────────────────────────

def _extract_join_paths(
    join_data: Dict,
    table_names: List[str],
) -> List[Dict]:
    """
    从 join_paths.json 中抽取 table_names 集合内部的 JOIN 路径。

    返回格式：
    [
      {
        "from": "hero_base",
        "to": "skill_base",
        "hops": 1,
        "joins": ["hero_base.skill_id = skill_base.id"],
        "min_confidence": 0.92
      },
      ...
    ]
    """
    paths_data = join_data.get('paths', {})
    name_set = set(table_names)
    result: List[Dict] = []
    seen: Set[str] = set()

    for key, info in paths_data.items():
        src, _, dst = key.partition(' -> ')
        if src not in name_set or dst not in name_set:
            continue
        # 去掉反向重复（A→B 和 B→A 只保留一个）
        canonical = tuple(sorted([src, dst]))
        if canonical in seen:
            continue
        seen.add(canonical)
        result.append({
            'from': src,
            'to': dst,
            'hops': info.get('hops', 1),
            'joins': info.get('joins', []),
            'min_confidence': info.get('min_confidence', 0),
        })

    result.sort(key=lambda x: (x['hops'], -x['min_confidence']))
    return result


# ──────────────────────────────────────────────────────────
# 主类
# ──────────────────────────────────────────────────────────

class EvidenceAssembler:
    """
    四段式证据组装器。

    构造参数：
        profiles_path   — table_profiles.jsonl 路径
        join_paths_path — join_paths.json 路径
        data_root       — 源 Excel 根目录（供 RowRetriever 使用）
    """

    def __init__(
        self,
        profiles_path: str,
        join_paths_path: str,
        data_root: str = ".",
    ):
        self._profiles: List[Dict] = _load_jsonl(profiles_path)
        self._profile_map: Dict[str, Dict] = {
            p['table_name']: p for p in self._profiles
        }
        self._join_data: Dict = _load_json(join_paths_path)
        self._data_root = data_root

        # 延迟导入，避免循环依赖
        self._retriever = None

    def _get_retriever(self):
        if self._retriever is None:
            from indexer.retrieval.row_retriever import RowRetriever
            self._retriever = RowRetriever(data_root=self._data_root)
        return self._retriever

    # ----------------------------------------------------------
    # 主接口
    # ----------------------------------------------------------

    def assemble(
        self,
        query: str,
        table_names: List[str],
        max_rows_per_table: int = 20,
        max_cols_per_table: int = _MAX_COLS_PER_TABLE,
        fetch_rows: bool = True,
        analysis_mode: Optional[bool] = None,
    ) -> Dict:
        """
        组装四段式证据包。

        参数：
            query              — 原始自然语言问题（用于语义裁剪和谓词生成）
            table_names        — 表级召回层已锁定的候选表名列表
            max_rows_per_table — 每张表最多取回的行数
            max_cols_per_table — 每张表 schema 段最多保留的列数
            fetch_rows         — 是否执行行级取数（False 时跳过，只生成前三段）
            analysis_mode     — None 时按 query 自动判定；True 时强制用全量统计聚合

        返回：
        {
          "query": "...",
          "tables": ["hero_base", ...],
          "_meta": {...},
          "schema": [...],
          "join": [...],
          "key_rows": [...],       # analysis_mode=False 时有值
          "analytical_result": [...],  # analysis_mode=True 时有值（全量分组统计+离群值）
          "stat_summary": [...]
        }
        """
        query_lower = query.lower()
        use_analysis_mode = (
            _is_analysis_query(query) if analysis_mode is None else analysis_mode
        )

        # ── 1. schema 段 ──
        schema_section: List[Dict] = []
        selected_cols_map: Dict[str, List[Dict]] = {}

        for tname in table_names:
            profile = self._profile_map.get(tname)
            if not profile:
                continue
            all_cols = profile.get('columns', [])
            sel_cols = _select_columns(all_cols, query_lower, max_cols_per_table)
            selected_cols_map[tname] = sel_cols

            # 简化列输出（不携带 sample_values，节省 token）
            schema_cols = []
            for c in sel_cols:
                sc: Dict[str, Any] = {
                    'name': c['name'],
                    'dtype': c.get('dtype', '?'),
                }
                for f in ('semantic_type', 'domain_role', 'metric_tag',
                          'is_pk', 'is_fk', 'fk_target',
                          'is_enum', 'enum_values', 'null_rate'):
                    if f in c and c[f] not in (None, False, 0.0):
                        sc[f] = c[f]
                if c.get('stats'):
                    sc['stats'] = c['stats']
                schema_cols.append(sc)

            schema_section.append({
                'table': tname,
                'domain': profile.get('domain', 'other'),
                'row_count': profile.get('row_count', 0),
                'primary_key': profile.get('primary_key'),
                'description': profile.get('description', ''),
                'columns': schema_cols,
                'total_columns': len(all_cols),
                'selected_columns': len(sel_cols),
            })

        # ── 2. join 段 ──
        join_section = _extract_join_paths(self._join_data, table_names)

        # ── 3. key_rows 段 或 analytical_result 段 ──
        key_rows_section: List[Dict] = []
        analytical_section: List[Dict] = []

        if use_analysis_mode:
            # 数值分析模式：全量聚合，不丢数据
            from indexer.retrieval.analytical_aggregator import AnalyticalAggregator
            agg = AnalyticalAggregator(data_root=self._data_root)
            retriever = self._get_retriever()
            for tname in table_names:
                profile = self._profile_map.get(tname)
                if not profile:
                    continue
                predicates = retriever.generate_predicates(query, profile)
                df = agg.fetch_table(profile, predicates)
                if df is not None and not df.empty:
                    analytics = agg.full_table_analytics(df, profile)
                    analytical_section.append(analytics)
        elif fetch_rows:
            retriever = self._get_retriever()
            for tname in table_names:
                profile = self._profile_map.get(tname)
                if not profile:
                    continue
                predicates = retriever.generate_predicates(query, profile)
                return_col_names = [c['name'] for c in selected_cols_map.get(tname, [])]
                block = retriever.fetch_rows(
                    profile,
                    predicates,
                    max_rows=max_rows_per_table,
                    return_cols=return_col_names or None,
                )
                key_rows_section.append({
                    'table': block.table_name,
                    'predicates_used': block.predicates_used,
                    'predicates_skipped': block.predicates_skipped,
                    'total_matched': block.total_matched,
                    'rows_returned': len(block.rows),
                    'columns': block.columns_returned,
                    'rows': block.rows,
                })

        # ── 4. stat_summary 段 ──
        stat_section = _build_stat_summary(self._profiles, selected_cols_map)
        question_focus = _build_question_focus(query, table_names, use_analysis_mode)
        table_roles = _build_table_roles(schema_section, self._profile_map)
        role_map = {item['table']: item for item in table_roles if item.get('table')}
        join_story = _build_join_story(join_section, role_map)
        trend_hints = _build_trend_hints(stat_section, analytical_section)
        sources = _build_sources(table_names, self._profile_map)
        hidden_but_available = _build_hidden_but_available(
            schema_section=schema_section,
            join_section=join_section,
            key_rows_section=key_rows_section,
            analytical_section=analytical_section,
        )
        fetch_hints = _build_fetch_hints(
            query=query,
            table_names=table_names,
            schema_section=schema_section,
            join_section=join_section,
            key_rows_section=key_rows_section,
            analytical_section=analytical_section,
        )
        visible_analytical_section = _build_visible_analytics_summary(analytical_section)

        out: Dict[str, Any] = {
            'query': query,
            'tables': table_names,
            '_meta': {
                'table_count': len(table_names),
                'schema_col_counts': {s['table']: s['selected_columns']
                                      for s in schema_section},
                'join_count': len(join_section),
                'key_rows_total': sum(b.get('rows_returned', 0) for b in key_rows_section),
                'analytical_tables': len(analytical_section),
                'analysis_mode': use_analysis_mode,
                'stat_entries': len(stat_section),
                'evidence_mode': 'summary_plus_drilldown',
            },
            'question_focus': question_focus,
            'table_roles': table_roles,
            'join_story': join_story,
            'schema': schema_section,
            'join': join_section,
            'key_rows': key_rows_section,
            'stat_summary': stat_section,
            'trend_hints': trend_hints,
            'sources': sources,
            'hidden_but_available': hidden_but_available,
            'fetch_hints': fetch_hints,
        }
        if analytical_section:
            out['analytical_result'] = analytical_section
            out['analytical_result_visible'] = visible_analytical_section
        return out

    def to_prompt_text(self, evidence: Dict, max_rows_display: int = 10) -> str:
        """
        将 assemble() 返回的证据包格式化为 LLM Prompt 文本。

        四段以 Markdown 标题分隔，可直接插入 system / user message。
        """
        lines: List[str] = []
        focus = evidence.get('question_focus', {})
        query = focus.get('question') or evidence.get('query', '')
        lines.append(f"## 用户问题\n{query}\n")

        lines.append("## 分析焦点")
        focus_text = focus.get('focus')
        if focus_text:
            lines.append(f"- {focus_text}")
        coverage = focus.get('coverage', [])
        if coverage:
            lines.append(f"- 当前证据重点覆盖：{'、'.join(coverage)}")
        table_scope = focus.get('table_scope', [])
        if table_scope:
            lines.append(f"- 当前涉及表：{', '.join(table_scope)}")

        lines.append("\n## 涉及表与作用")
        for role in evidence.get('table_roles', []):
            selected_cols = role.get('selected_columns', [])
            columns_text = f"；关键列：{', '.join(selected_cols[:6])}" if selected_cols else ""
            source_text = ""
            if role.get('file'):
                source_text = f"（来源：{role['file']}"
                if role.get('sheet'):
                    source_text += f" / {role['sheet']}"
                source_text += "）"
            lines.append(
                f"- **{role['table']}** [{role.get('domain', 'other')}]："
                f"{role.get('role', '与当前问题相关的配置表。')}"
                f"{columns_text}{source_text}"
            )

        # ── Schema ──
        lines.append("\n## 相关表结构（Schema）")
        for tbl in evidence.get('schema', []):
            lines.append(
                f"\n### {tbl['table']}  "
                f"[{tbl['domain']}]  "
                f"{tbl['row_count']} 行  "
                f"主键: {tbl['primary_key'] or '无'}"
            )
            if tbl.get('description'):
                lines.append(f"> {tbl['description']}")
            lines.append(f"（已选 {tbl['selected_columns']}/{tbl['total_columns']} 列）")
            for c in tbl['columns']:
                parts = [f"- **{c['name']}** `{c['dtype']}`"]
                tags = []
                if c.get('is_pk'):
                    tags.append('PK')
                if c.get('is_fk'):
                    tags.append(f"FK→{c.get('fk_target','?')}")
                if c.get('semantic_type'):
                    tags.append(c['semantic_type'])
                if c.get('metric_tag'):
                    tags.append(f"[{c['metric_tag']}]")
                if c.get('domain_role'):
                    tags.append(c['domain_role'])
                if c.get('stats'):
                    s = c['stats']
                    tags.append(f"范围[{s.get('min')}~{s.get('max')}]")
                if c.get('is_enum') and c.get('enum_values'):
                    ev = c['enum_values'][:8]
                    tags.append(f"枚举{ev}")
                if tags:
                    parts.append(' | ' + ', '.join(str(t) for t in tags))
                lines.append(''.join(parts))

        # ── Join ──
        join_story = evidence.get('join_story', [])
        if join_story:
            lines.append("\n## 关键关联关系")
            for item in join_story:
                lines.append(
                    f"- **{item['from']} -> {item['to']}**：{item.get('business_meaning', '')}"
                )
                joins = item.get('joins', [])
                if joins:
                    lines.append(f"  - JOIN: `{ ' -> '.join(joins) }`")
                lines.append(
                    f"  - 跳数: {item.get('hops', 1)}，最小置信度: {item.get('min_confidence', 0)}"
                )

        join_list = evidence.get('join', [])
        if join_list:
            lines.append("\n## 表间 JOIN 路径")
            for j in join_list:
                hops = j['hops']
                conf = j['min_confidence']
                joins_str = ' -> '.join(j['joins'])
                lines.append(f"- {j['from']} -> {j['to']}  ({hops}跳, conf={conf})")
                lines.append(f"  `{joins_str}`")

        # ── Analytical Result（数值分析模式）或 Key Rows ──
        analytical_list = evidence.get('analytical_result_visible') or evidence.get('analytical_result', [])
        if analytical_list:
            from indexer.retrieval.analytical_aggregator import AnalyticalAggregator
            agg = AnalyticalAggregator()
            lines.append("\n## 数值分析（全量统计，无采样）")
            for a in analytical_list:
                lines.append(agg.to_prompt_text(a, max_groups_display=15))
        else:
            key_rows_list = evidence.get('key_rows', [])
            if key_rows_list:
                lines.append("\n## 关键数据行（样本，不代表全量分布）")
                for block in key_rows_list:
                    tname = block['table']
                    total = block['total_matched']
                    returned = block['rows_returned']
                    preds = block['predicates_used']
                    lines.append(
                        f"\n### {tname}  "
                        f"（命中 {total} 行，展示 {min(returned, max_rows_display)} 行）"
                    )
                    if preds:
                        lines.append(f"过滤条件: {', '.join(preds)}")
                    cols = block.get('columns', [])
                    rows = block.get('rows', [])[:max_rows_display]
                    if cols and rows:
                        lines.append('| ' + ' | '.join(cols) + ' |')
                        lines.append('| ' + ' | '.join(['---'] * len(cols)) + ' |')
                        for row in rows:
                            cells = [str(row.get(c, '')) for c in cols]
                            lines.append('| ' + ' | '.join(cells) + ' |')

        # ── Stat Summary ──
        stat_list = evidence.get('stat_summary', [])
        if stat_list:
            lines.append("\n## 全量统计摘要")
            for s in stat_list:
                tbl = s['table']
                col = s['column']
                sem = s.get('semantic_type', '')
                if sem == 'metric':
                    tag = f"[{s['metric_tag']}] " if s.get('metric_tag') else ''
                    lines.append(
                        f"- {tbl}.{col} {tag}"
                        f"min={s.get('min')} max={s.get('max')} "
                        f"mean={s.get('mean')} "
                        f"unique={s.get('unique_count')}"
                    )
                else:
                    ev = s.get('enum_values', [])[:10]
                    lines.append(
                        f"- {tbl}.{col} 枚举({s.get('unique_count')}种): {ev}"
                    )

        trend_hints = evidence.get('trend_hints', [])
        if trend_hints:
            lines.append("\n## 趋势观察")
            for hint in trend_hints:
                lines.append(f"- {hint}")

        sources = evidence.get('sources', [])
        if sources:
            lines.append("\n## 数据来源")
            for source in sources:
                src = source.get('file') or '未知文件'
                sheet = source.get('sheet')
                domain = source.get('domain', 'other')
                suffix = f" / {sheet}" if sheet else ""
                lines.append(f"- {src}{suffix} -> {source.get('table')} [{domain}]")

        hidden = evidence.get('hidden_but_available', {})
        fetch_hints = evidence.get('fetch_hints', [])
        if hidden or fetch_hints:
            lines.append("\n## 可继续展开")
            for item in hidden.get('schema', [])[:5]:
                lines.append(
                    f"- {item['table']} 还有 {item['hidden_columns']} 列未展示，当前仅展开 {item['selected_columns']}/{item['total_columns']} 列。"
                )
            for item in hidden.get('rows', [])[:5]:
                lines.append(
                    f"- {item['table']} 还有 {item['hidden_rows']} 行命中结果未展示，当前展示 {item['rows_returned']}/{item['total_matched']} 行。"
                )
            for item in hidden.get('analytics', [])[:5]:
                table = item.get('table')
                if item.get('hidden_group_columns'):
                    cols = ', '.join(g.get('group_col', '') for g in item.get('hidden_group_columns', [])[:3] if g.get('group_col'))
                    if cols:
                        lines.append(f"- {table} 的 {cols} 分组统计还有更多组可继续展开。")
                if item.get('hidden_global_stats', 0) > 0:
                    lines.append(f"- {table} 还有 {item['hidden_global_stats']} 个数值列统计未在首屏展示。")
            for hint in fetch_hints[:6]:
                lines.append(f"- 提示: {hint.get('reason', '')}")

        return '\n'.join(lines)


# ──────────────────────────────────────────────────────────
# I/O 辅助
# ──────────────────────────────────────────────────────────

def _load_jsonl(path: str) -> List[Dict]:
    p = Path(path)
    if not p.exists():
        return []
    items = []
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return items


def _load_json(path: str) -> Dict:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)
