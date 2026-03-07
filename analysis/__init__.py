#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析模块
"""

try:
    from indexer.analysis.analyzer import GraphAnalyzer, AnalysisResult
except ImportError:
    from analysis.analyzer import GraphAnalyzer, AnalysisResult

__all__ = ['GraphAnalyzer', 'AnalysisResult']
