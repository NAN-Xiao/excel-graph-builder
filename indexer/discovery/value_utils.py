#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
值标准化工具

解决游戏配置表中同一 ID 在不同表内格式不同的问题：
- 1 / 1.0 / "001" / " 1 " → "1"
- 整数浮点互通
- 前导零/空格清理
"""

import re
from typing import Optional, Set, Iterable

# 预编译正则
_RE_INT_LIKE = re.compile(r'^[+-]?0*(\d+)\.0*$')
_RE_PURE_INT = re.compile(r'^[+-]?0*(\d+)$')
_RE_FLOAT = re.compile(r'^[+-]?\d+\.\d+$')


def normalize_value(value) -> Optional[str]:
    """
    将单个值标准化为统一字符串形式。

    规则：
    - None / nan / 空字符串 → None（跳过）
    - 数字型（1 / 1.0 / "001" / "1.0"）→ 去前导零的整数字符串 "1"
    - 浮点数但不是整数（3.14）→ 精简格式 "3.14"
    - 其他字符串 → strip 后原样返回
    """
    if value is None:
        return None

    s = str(value).strip()
    if not s or s.lower() in ('none', 'nan', 'null', 'na', 'nat'):
        return None

    # 快速路径：纯整数 "123" / "0123" / "+45"
    m = _RE_PURE_INT.match(s)
    if m:
        return m.group(1).lstrip('0') or '0'

    # "1.0" / "001.00" → 整数
    m = _RE_INT_LIKE.match(s)
    if m:
        return m.group(1).lstrip('0') or '0'

    # 真浮点 "3.14"
    if _RE_FLOAT.match(s):
        try:
            f = float(s)
            if f.is_integer():
                return str(int(f))
            return format(f, 'g')
        except ValueError:
            pass

    # 通用：尝试浮点转换（处理科学计数法等）
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
        return format(f, 'g')
    except (ValueError, OverflowError):
        pass

    return s


def normalize_value_set(values: Iterable) -> Set[str]:
    """将一组值标准化后去重，返回 set。"""
    result = set()
    for v in values:
        nv = normalize_value(v)
        if nv is not None:
            result.add(nv)
    return result


# 复合值分隔符（游戏配置常见：101|102|103 或 1001,1002,1003 或 1;2;3）
_RE_COMPOUND_SEP = re.compile(r'[|;,，、]')


def expand_compound_values(values: Iterable) -> Set[str]:
    """
    将复合值（如 "101|102|103"）拆开，与原子值合并后标准化。

    仅当一个值包含分隔符且拆分后所有子值都能标准化为非空字符串时才展开。
    返回展开后的去重标准化集合。
    """
    result = set()
    for v in values:
        s = str(v).strip() if v is not None else ''
        if not s:
            continue
        parts = _RE_COMPOUND_SEP.split(s)
        if len(parts) > 1 and all(p.strip() for p in parts):
            for p in parts:
                nv = normalize_value(p.strip())
                if nv is not None:
                    result.add(nv)
        else:
            nv = normalize_value(v)
            if nv is not None:
                result.add(nv)
    return result
