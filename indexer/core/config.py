#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置集中管理
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict


def load_config_file(config_path: str) -> Dict[str, str]:
    """加载简单 YAML 配置文件（仅支持 flat key: value 格式）

    不依赖 PyYAML，适用于 configs/settings.yml 这类简单配置。
    """
    result: Dict[str, str] = {}
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                result[key] = value
    return result


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
