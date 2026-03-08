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
    storage_dir: str = "./data/indexer"
    html_dir: str = "./html"

    # 性能配置
    max_workers: int = 4
    max_sample_rows: int = 2000
    max_sample_cols: int = 200
    max_rows_per_table: int = 50000  # 超过此行数的表截断采样
    skip_sheet_prefixes: tuple = ('#',)  # 跳过这些前缀的 sheet（备注/备份）

    # Phase 1: 包含度检测
    containment_threshold: float = 0.85
    overlap_threshold: float = 0.75
    min_sample_size: int = 3
    small_pk_threshold: int = 100  # PK 列唯一值少于此数时触发碰撞惩罚

    # Phase 2: 缩写挖掘
    abbrev_confidence_threshold: float = 0.8

    # 关系质量控制
    min_relation_confidence: float = 0.45

    # 缓存配置
    enable_perf_opt: bool = True
    fingerprint_cache_file: str = "./data/fingerprints.json"
    feedback_file: str = "relation_feedback.json"
    auto_save_interval: int = 60

    # HTML 报告
    offline_html: bool = True

    # 调度配置
    incremental_delay: float = 3.0


# 全局默认配置
DEFAULT_CONFIG = BuildConfig()
