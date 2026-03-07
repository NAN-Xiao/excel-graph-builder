#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
报告模块
"""

try:
    from indexer.report.html_generator import HTMLReportGenerator
except ImportError:
    from report.html_generator import HTMLReportGenerator

__all__ = ['HTMLReportGenerator']
