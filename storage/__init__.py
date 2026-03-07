#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
存储模块
"""

try:
    from indexer.storage.json_storage import JsonGraphStorage
except ImportError:
    from storage.json_storage import JsonGraphStorage

__all__ = ['JsonGraphStorage']
