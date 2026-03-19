#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对比 PK 识别改善效果"""
import json
import re
from pathlib import Path

graph_dir = Path(__file__).parent.parent.parent / "graph"
with open(graph_dir / "schema_graph.json", encoding="utf-8") as f:
    sg = json.load(f)

tables = sg["tables"]
total = len(tables)
no_pk = [n for n, t in tables.items() if not t.get("primary_key")]
has_pk = total - len(no_pk)

cn_pk, en_pk = 0, 0
for t in tables.values():
    pk = t.get("primary_key") or ""
    if pk:
        if any("\u4e00" <= c <= "\u9fff" for c in pk):
            cn_pk += 1
        else:
            en_pk += 1

# 疑似坐标 PK：PK 值中含逗号且较短
coord_pk = [
    (n, t["primary_key"])
    for n, t in tables.items()
    if t.get("primary_key") and "," in str(t["primary_key"]) and len(str(t["primary_key"])) < 10
]

print(f"=== PK 识别统计 ===")
print(f"  总表数:        {total}")
print(f"  有 PK:         {has_pk} ({has_pk/total*100:.1f}%)")
print(f"  无 PK:         {len(no_pk)} ({len(no_pk)/total*100:.1f}%)")
print(f"  英文 PK:       {en_pk}")
print(f"  中文 PK:       {cn_pk}")
print(f"  疑似坐标 PK:   {len(coord_pk)}")
for n, pk in coord_pk[:5]:
    print(f"    {n}: pk={pk!r}")

print()
print("无 PK 的表 Top10:")
for n in no_pk[:10]:
    t = tables[n]
    print(f"  {n}: {t.get('row_count',0)}行 x {len(t.get('columns',[]))}列")

# 验证 pack_info 补算
pack_count = sum(
    1 for t in tables.values()
    for col in t.get("columns", [])
    if col.get("pack_info", {}).get("is_pack")
)
print(f"\nPack 列总数 (含旧图补算): {pack_count}")
