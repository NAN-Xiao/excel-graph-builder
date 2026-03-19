#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析 Pack 数组发现结果"""
import json
from pathlib import Path
from collections import Counter, defaultdict

graph_dir = Path(__file__).parent.parent.parent / "graph"

def load(name):
    with open(graph_dir / name, encoding='utf-8') as f:
        return json.load(f)

# ── data_health pack 统计 ──
health = load("data_health.json")
pack_cols = health.get("pack_columns", [])
print(f"=== Pack 列统计（共 {len(pack_cols)} 个）===")
sep_counter = Counter(c['separator'] for c in pack_cols)
dtype_counter = Counter(c['element_dtype'] for c in pack_cols)
print(f"  分隔符分布: {dict(sep_counter)}")
print(f"  元素类型:   {dict(dtype_counter)}")
print(f"  平均 pack 大小: {sum(c['avg_pack_size'] for c in pack_cols)/max(len(pack_cols),1):.1f}")
print(f"  平均唯一元素数: {sum(c['unique_elements'] for c in pack_cols)/max(len(pack_cols),1):.0f}")

print()
print("  Pack 唯一元素最多的列 Top10:")
for c in sorted(pack_cols, key=lambda x: -x['unique_elements'])[:10]:
    print(f"    {c['table']}.{c['column']}: {c['unique_elements']} 唯一值 sep={c['separator']!r}")

# ── relation 分析 ──
sg = load("schema_graph.json")
relations = sg.get("relations", [])

pack_rels = [r for r in relations if r.get("discovery_method") == "pack_array"]
other_rels = [r for r in relations if r.get("discovery_method") != "pack_array"]
print()
print(f"=== 关系统计 ===")
print(f"  Pack 方法发现: {len(pack_rels)}")
print(f"  其他方法发现: {len(other_rels)}")

# 置信度分布
conf_buckets = Counter()
for r in pack_rels:
    conf = r.get("confidence", 0)
    if conf >= 0.80: conf_buckets["0.80+"] += 1
    elif conf >= 0.75: conf_buckets["0.75+"] += 1
    elif conf >= 0.70: conf_buckets["0.70+"] += 1
    elif conf >= 0.65: conf_buckets["0.65+"] += 1
    else: conf_buckets["<0.65"] += 1
print(f"  置信度分布: {dict(sorted(conf_buckets.items()))}")

# 每对表有多少 pack 关系
pair_count = Counter()
for r in pack_rels:
    pair = (r['from_table'], r['to_table'])
    pair_count[pair] += 1
print(f"  表对数量: {len(pair_count)}")
print(f"  每对平均关系数: {len(pack_rels)/max(len(pair_count),1):.1f}")

print()
print("=== Pack 关系样例（高置信度前10条）===")
top_rels = sorted(pack_rels, key=lambda x: -x.get("confidence",0))[:10]
for r in top_rels:
    print(f"  {r['from_table']}.{r['from_column']} → {r['to_table']}.{r['to_column']}")
    print(f"    conf={r['confidence']} | {r.get('evidence','')}")

print()
print("=== 可疑的 Pack 关系（低置信度样例）===")
low_rels = [r for r in pack_rels if r.get("confidence", 0) < 0.65]
print(f"  低置信度（<0.65）关系数: {len(low_rels)}")
for r in sorted(low_rels, key=lambda x: x.get("confidence", 0))[:8]:
    print(f"  {r['from_table']}.{r['from_column']} → {r['to_table']}.{r['to_column']}")
    print(f"    conf={r['confidence']} | {r.get('evidence','')}")

# 哪些目标表被引用最多（可能是假阳性热点）
target_count = Counter(r['to_table'] for r in pack_rels)
print()
print("=== Pack 关系中被引用最多的目标表 Top15 ===")
for tname, cnt in target_count.most_common(15):
    pk = sg['tables'].get(tname, {}).get('primary_key', '?')
    row_count = sg['tables'].get(tname, {}).get('row_count', 0)
    print(f"  {tname}(pk={pk}, {row_count}行): 被 {cnt} 条 pack 关系引用")
