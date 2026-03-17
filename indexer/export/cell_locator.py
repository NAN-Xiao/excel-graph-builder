#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单元格定位索引导出

为外部 RAG 系统提供精确的单元格定位能力:
  表名 → 文件 → sheet → Excel行号 → Excel列号

导出文件: cell_locator.json

用法示例:
  查询 "hero 表 键值=5 的 英雄主动技能ID"
  →  hero.xlsx / sheet: hero / 单元格 D8
"""

import json
from pathlib import Path
from typing import Optional, Dict, List

from indexer.models import SchemaGraph


def _col_idx_to_excel_letter(idx: int) -> str:
    """将 0-based 列索引转为 Excel 列字母 (0→A, 1→B, ..., 25→Z, 26→AA, ...)"""
    result = ""
    while True:
        result = chr(65 + idx % 26) + result
        idx = idx // 26 - 1
        if idx < 0:
            break
    return result


def export_cell_locator(graph: SchemaGraph,
                        output_path: Optional[str] = None,
                        pk_row_map_max_rows: int = 200) -> dict:
    """
    导出单元格定位索引。

    对每张表提供:
    - file / sheet: 定位到 Excel 文件和工作表
    - data_start_row: 数据区第一行的 Excel 行号（1-based）
    - columns: 每列的 Excel 列字母和列序号
    - pk_column: 主键列名
    - pk_to_excel_row: 主键值 → Excel 行号映射（仅 ≤ pk_row_map_max_rows 行的小表）

    Args:
        graph: 图谱数据
        output_path: 输出文件路径（可选）
        pk_row_map_max_rows: 行数 ≤ 该值的表才生成 pk_to_excel_row 映射

    Returns:
        完整的定位索引 dict
    """
    locator: Dict[str, dict] = {}

    for name in sorted(graph.tables.keys()):
        table = graph.tables[name]

        # Excel 行号计算:
        #   Row 1 = pandas 读取为 column header
        #   Row 2 ~ Row 1+header_offset = 被跳过的元数据行（类型行/标识符行等）
        #   Row 2+header_offset = 数据区第一行
        data_start_row = 2 + table.header_offset  # Excel 1-based

        # 列信息: 列名 → {excel_col: "A", col_idx: 0}
        columns_map: Dict[str, dict] = {}
        for idx, col in enumerate(table.columns):
            col_name = col['name']
            columns_map[col_name] = {
                "excel_col": _col_idx_to_excel_letter(idx),
                "col_idx": idx,
            }

        entry: dict = {
            "file": Path(table.file_path).name,
            "sheet": table.sheet_name,
            "data_start_row": data_start_row,
            "row_count": table.row_count,
            "columns": columns_map,
            "pk_column": table.primary_key,
        }

        # 小表: 生成 pk_value → Excel 行号映射
        # 利用主键列的 sample_values（对于 ≤200 行的表，sample_values = 全量且保序）
        if (table.primary_key
                and table.row_count <= pk_row_map_max_rows):
            pk_col_data = None
            for col in table.columns:
                if col['name'] == table.primary_key:
                    pk_col_data = col
                    break

            if pk_col_data and pk_col_data.get('sample_values'):
                sv = pk_col_data['sample_values']
                # unique_count == row_count 说明 PK 确实唯一，sample_values 按行序排列
                if pk_col_data.get('unique_count', 0) >= table.row_count:
                    pk_to_row = {}
                    for i, val in enumerate(sv):
                        excel_row = data_start_row + i
                        pk_to_row[str(val)] = excel_row
                    entry["pk_to_excel_row"] = pk_to_row

        # 辅助字段: pk 列的 Excel 列字母（方便直接拼单元格地址）
        if table.primary_key and table.primary_key in columns_map:
            entry["pk_excel_col"] = columns_map[table.primary_key]["excel_col"]

        locator[name] = entry

    result = {
        "_meta": {
            "table_count": len(locator),
            "description": (
                "单元格定位索引。"
                "data_start_row 是数据区第一行的 Excel 行号（1-based）。"
                "columns 映射列名到 Excel 列字母。"
                "pk_to_excel_row 映射主键值到 Excel 行号（仅小表提供）。"
                "拼接单元格地址: columns[col_name].excel_col + pk_to_excel_row[pk_value]，如 'D8'。"
            ),
            "pk_row_map_max_rows": pk_row_map_max_rows,
        },
        "tables": locator,
    }

    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=1, default=str)

    return result

