#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pack 数组检测器

游戏策划配置表中常见的「多值打包列」模式：
  "10001|10002|10003"   → 竖线分隔的 ID 列表
  "101;102;103"         → 分号分隔的 ID 列表
  "1001,1002,1003"      → 逗号分隔的 ID 列表
  "task_a,task_b"       → 字符串 key 列表

这些列本质是外键数组，但常规 FK 发现策略对 string 列无效。
本模块在 schema 提取阶段预计算 pack_info，供 PackArrayDiscovery 使用。
"""

import re
from typing import Optional, Dict, Any, List

# 分隔符优先级：| > ; > ,（逗号最低，因为它也出现在 KV 对和小数中）
_SEPARATORS = ['|', ';', ',']

# 至少需要这么多非空采样值才尝试检测
_MIN_SAMPLES = 3

# 这个比例以上的值必须含有分隔符
_SEP_HIT_RATIO = 0.6

# 对逗号分隔符要求更高，避免把 KV 对误判为 pack
_SEP_HIT_RATIO_COMMA = 0.80

# 提取出的元素中，整数占比超过此阈值才判定为 int pack
_ELEM_INT_RATIO = 0.70

# 提取出的元素中，标识符占比超过此阈值才判定为 str pack
_ELEM_IDENT_RATIO = 0.70

# 单个 pack 字符串最长允许多少字符（过长的一般是注释或 JSON）
_MAX_PACK_STR_LEN = 200

# pack_element_samples 最多存多少个不重复元素值
_MAX_ELEM_SAMPLES = 2000

# 中文字符检测
_CN_RE = re.compile(r'[\u4e00-\u9fff]')
# 标识符检测（英文+下划线开头）
_IDENT_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def detect_pack_column(sample_values: list) -> Optional[Dict[str, Any]]:
    """
    检测字符串列是否为 Pack 数组列，返回 pack_info 字典或 None。

    pack_info 结构：
    {
        'is_pack': True,
        'pack_separator': '|',          # 主分隔符
        'pack_element_dtype': 'int',    # 元素类型：'int' | 'str'
        'pack_element_samples': [...],  # 去重后的元素采样（最多2000个）
        'pack_avg_size': 3.2,           # 平均每个 pack 字符串含多少元素
    }
    """
    # 过滤空值，转换为字符串
    str_vals: List[str] = []
    for v in sample_values:
        if v is None:
            continue
        s = str(v).strip()
        if not s or s.lower() in ('nan', 'none', 'null', ''):
            continue
        if len(s) > _MAX_PACK_STR_LEN:
            continue
        str_vals.append(s)

    if len(str_vals) < _MIN_SAMPLES:
        return None

    # 中文含量过高 → 注释/描述，直接跳过
    cn_hits = sum(1 for v in str_vals if _CN_RE.search(v))
    if cn_hits / len(str_vals) > 0.25:
        return None

    for sep in _SEPARATORS:
        result = _try_separator(str_vals, sep)
        if result:
            return result

    return None


def _try_separator(str_vals: List[str], sep: str) -> Optional[Dict[str, Any]]:
    """尝试用指定分隔符解析 pack 数组，成功返回 pack_info，否则 None。"""
    threshold = _SEP_HIT_RATIO_COMMA if sep == ',' else _SEP_HIT_RATIO

    # 分割所有值
    splits: List[List[str]] = []
    for v in str_vals:
        parts = [p.strip() for p in v.split(sep) if p.strip()]
        splits.append(parts)

    # 含分隔符（>=2个子值）的比例
    multi_splits = [p for p in splits if len(p) >= 2]
    if len(multi_splits) / len(str_vals) < threshold:
        return None
    if len(multi_splits) < 3:
        return None

    # 从多值行提取所有子元素
    all_elems = [e for parts in multi_splits for e in parts]
    if len(all_elems) < 5:
        return None

    # 尝试解析为整数
    int_elems: List[int] = []
    for e in all_elems:
        try:
            f = float(e)
            if f == int(f):
                int_elems.append(int(f))
        except (ValueError, TypeError):
            pass

    int_ratio = len(int_elems) / len(all_elems)

    if int_ratio >= _ELEM_INT_RATIO:
        unique_elems = sorted(set(int_elems))
        elem_dtype = 'int'
    else:
        # 尝试解析为字符串标识符
        ident_count = sum(1 for e in all_elems if _IDENT_RE.match(e) and len(e) >= 2)
        if ident_count / len(all_elems) >= _ELEM_IDENT_RATIO:
            unique_elems = sorted(set(all_elems))
            elem_dtype = 'str'
        else:
            return None  # 元素类型混乱，不认为是 pack

    avg_size = sum(len(p) for p in multi_splits) / len(multi_splits)

    return {
        'is_pack': True,
        'pack_separator': sep,
        'pack_element_dtype': elem_dtype,
        'pack_element_samples': unique_elems[:_MAX_ELEM_SAMPLES],
        'pack_avg_size': round(avg_size, 1),
    }
