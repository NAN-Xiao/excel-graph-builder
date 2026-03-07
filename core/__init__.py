#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
核心模块
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导出主要组件
from .config import BuildConfig, DEFAULT_CONFIG

__all__ = ['BuildConfig', 'DEFAULT_CONFIG']
