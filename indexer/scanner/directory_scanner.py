#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
目录扫描器

递归扫描 Excel 目录，支持增量检测（基于 mtime + hash）。
处理大量表文件时使用线程池并行读取。
"""

import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set

from indexer.models import SchemaGraph, TableSchema
from indexer import SimpleLogger

from .excel_reader import ExcelReader
from .schema_extractor import SchemaExtractor


class DirectoryScanner:
    """
    目录扫描器

    返回格式: {'new': [TableSchema], 'updated': [TableSchema], 'unchanged': [str]}
    """

    def __init__(self, data_root: str, max_sample_rows: int = 200,
                 max_workers: int = 4, skip_sheet_prefixes: tuple = ('#',)):
        self.data_root = Path(data_root)
        self.max_sample_rows = max_sample_rows
        self.max_workers = max_workers
        self.skip_sheet_prefixes = skip_sheet_prefixes
        self.reader = ExcelReader(max_sample_rows=max_sample_rows)
        self.extractor = SchemaExtractor(max_sample_rows=max_sample_rows)
        self.logger = SimpleLogger()

    def scan(self, existing_graph: Optional[SchemaGraph] = None
             ) -> Dict[str, list]:
        """
        扫描目录中的所有 Excel/CSV 文件。

        Args:
            existing_graph: 已有图谱（用于增量检测）

        Returns:
            {
                'new': [TableSchema],       # 新文件
                'updated': [TableSchema],   # 内容变更的文件
                'unchanged': [str],         # 未变化的表名
            }
        """
        if not self.data_root.exists():
            self.logger.error(f"数据目录不存在: {self.data_root}")
            return {'new': [], 'updated': [], 'unchanged': []}

        # 1. 收集所有文件
        files = self._discover_files()
        self.logger.info(f"发现 {len(files)} 个数据文件")

        if not files:
            return {'new': [], 'updated': [], 'unchanged': []}

        # 2. 构建已有表索引 (table_name -> TableSchema)
        existing_tables: Dict[str, TableSchema] = {}
        if existing_graph:
            existing_tables = {
                t.name: t for t in existing_graph.tables.values()}

        # 3. 快速过滤：哪些文件需要重新读取
        files_to_read = []
        unchanged = []
        existing_files_seen: Set[str] = set()

        for finfo in files:
            rel_path = finfo['rel_path']
            mtime = finfo['mtime']

            # 查找已有表（一个文件可能对应多个表：多sheet）
            # 先按文件名匹配
            base_name = os.path.splitext(os.path.basename(rel_path))[0]
            matched_existing = [
                (name, t) for name, t in existing_tables.items()
                if t.file_path == rel_path or name == base_name or name.startswith(f"{base_name}_")
            ]

            if matched_existing:
                # 检查是否需要更新：mtime 变化
                needs_update = False
                for name, t in matched_existing:
                    existing_files_seen.add(name)
                    if abs(t.modified_time - mtime) > 1.0:  # 1秒容差
                        needs_update = True

                if needs_update:
                    files_to_read.append({**finfo, 'mode': 'updated'})
                else:
                    for name, _ in matched_existing:
                        unchanged.append(name)
            else:
                files_to_read.append({**finfo, 'mode': 'new'})

        self.logger.info(
            f"需读取: {len(files_to_read)} ({len(files) - len(files_to_read)} 未变化)"
        )

        # 4. 并行读取文件并提取 Schema
        new_tables = []
        updated_tables = []

        if files_to_read:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {
                    pool.submit(self._process_file, finfo): finfo
                    for finfo in files_to_read
                }

                for future in as_completed(futures):
                    finfo = futures[future]
                    try:
                        schemas = future.result()
                        for schema in schemas:
                            if finfo['mode'] == 'new':
                                new_tables.append(schema)
                            else:
                                updated_tables.append(schema)
                    except Exception as e:
                        self.logger.error(
                            f"处理文件失败 {finfo['rel_path']}: {e}"
                        )

        self.logger.info(
            f"扫描结果: {len(new_tables)} 新增, "
            f"{len(updated_tables)} 更新, {len(unchanged)} 未变化"
        )

        return {
            'new': new_tables,
            'updated': updated_tables,
            'unchanged': unchanged,
        }

    def _discover_files(self) -> List[Dict]:
        """递归查找所有 Excel/CSV 文件"""
        files = []

        for root, dirs, filenames in os.walk(self.data_root):
            # 跳过隐藏目录和临时文件目录
            dirs[:] = [d for d in dirs if not d.startswith(
                '.') and d != '__pycache__']

            for fn in filenames:
                # 跳过临时文件（~ 开头或 ~$ 开头）
                if fn.startswith('~') or fn.startswith('.'):
                    continue

                ext = os.path.splitext(fn)[1].lower()
                if ext not in ExcelReader.SUPPORTED_EXTENSIONS:
                    continue

                full_path = os.path.join(root, fn)
                try:
                    stat = os.stat(full_path)
                except OSError:
                    continue

                rel_path = os.path.relpath(full_path, self.data_root)

                files.append({
                    'full_path': full_path,
                    'rel_path': rel_path,
                    'mtime': stat.st_mtime,
                    'size': stat.st_size,
                })

        return files

    def _process_file(self, finfo: Dict) -> List[TableSchema]:
        """处理单个文件：读取 + 提取 Schema"""
        full_path = finfo['full_path']
        rel_path = finfo['rel_path']
        mtime = finfo['mtime']

        sheets_data = self.reader.read_file(full_path)
        if not sheets_data:
            return []

        schemas = []
        for sheet_info in sheets_data:
            try:
                schema = self.extractor.extract(
                    file_path=rel_path,
                    sheet_name=sheet_info['sheet_name'],
                    df=sheet_info['df'],
                    file_mtime=mtime,
                )
                self.logger.info(
                    f"  {schema.name}: {schema.row_count} 行 x {len(schema.columns)} 列"
                    + (f" [PK: {schema.primary_key}]" if schema.primary_key else "")
                )
                schemas.append(schema)
            except Exception as e:
                self.logger.error(
                    f"  提取 schema 失败 {rel_path}/{sheet_info['sheet_name']}: {e}"
                )

        return schemas
