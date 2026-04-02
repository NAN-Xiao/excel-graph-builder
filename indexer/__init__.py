#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Indexer - 配置表索引构建服务

独立进程，负责：
- 定时扫描 Excel 配置表
- 构建知识图谱（表结构、关联关系）
- 持久化为 JSON 文件
- 监控文件变化并增量更新

主服务通过读取 JSON 文件使用图谱数据
"""

import logging
import logging.handlers
import os
from pathlib import Path

__version__ = "1.0.0"


def _setup_logger() -> logging.Logger:
    """初始化结构化日志：控制台输出立即可用，文件输出延迟到首次写入时创建。"""
    logger = logging.getLogger("indexer")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


def _add_file_handler(logger: logging.Logger, log_dir: str | Path | None = None) -> None:
    """添加文件日志（10MB 轮转，保留 5 份）。仅在服务实际启动时调用。"""
    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers):
        return
    log_path = Path(log_dir or os.environ.get("INDEXER_LOG_DIR", "./graph"))
    log_path.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.handlers.RotatingFileHandler(
        log_path / "indexer.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)


_logger = _setup_logger()


class SimpleLogger:
    """结构化日志（控制台 + 文件持久化）"""

    @staticmethod
    def info(msg):
        _logger.info(msg)

    @staticmethod
    def success(msg):
        _logger.info(f"[OK] {msg}")

    @staticmethod
    def warning(msg):
        _logger.warning(msg)

    @staticmethod
    def error(msg):
        _logger.error(msg)

    @staticmethod
    def debug(msg):
        _logger.debug(msg)
