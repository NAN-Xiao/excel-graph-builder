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

__version__ = "1.0.0"


class SimpleLogger:
    """简单日志实现（独立使用）"""
    @staticmethod
    def info(msg):
        print(f"[INFO] {msg}")

    @staticmethod
    def success(msg):
        print(f"[OK] {msg}")

    @staticmethod
    def warning(msg):
        print(f"[WARN] {msg}")

    @staticmethod
    def error(msg):
        print(f"[ERR] {msg}")

    @staticmethod
    def debug(msg):
        pass
