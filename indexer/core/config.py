#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置集中管理
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BuildConfig:
    """构建配置"""
    # 路径配置
    data_root: str = "./data"
    storage_dir: str = "./graph"
    html_dir: str = "./graph"

    # 性能配置
    max_workers: int = 4
    max_sample_rows: int = 2000
    max_sample_cols: int = 200
    max_rows_per_table: int = 50000
    skip_sheet_prefixes: tuple = ('#',)

    # Phase 1: 包含度检测
    containment_threshold: float = 0.80
    overlap_threshold: float = 0.75
    min_sample_size: int = 3
    small_pk_threshold: int = 50
    min_intersection: int = 5
    max_per_table_pair: int = 2

    # Phase 2: 缩写挖掘
    abbrev_confidence_threshold: float = 0.8

    # 关系质量控制
    min_relation_confidence: float = 0.50

    # 缓存配置
    enable_perf_opt: bool = True
    fingerprint_cache_file: str = "./graph/fingerprints.json"
    feedback_file: str = "relation_feedback.json"
    auto_save_interval: int = 60

    # HTML 报告
    offline_html: bool = True

    # 调度配置
    incremental_delay: float = 3.0


# 全局默认配置
DEFAULT_CONFIG = BuildConfig()
