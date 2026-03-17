#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
原子文件写入工具

确保导出的数据文件在写入过程中不会被 RAG 系统读到半成品：
  1. 写入临时文件 (.tmp)
  2. fsync 确保数据落盘
  3. 原子 rename 覆盖目标文件
  4. 自动重试（指数退避），应对文件被占用等瞬时错误

Windows 特殊处理:
  - os.replace() 在目标文件被其他进程以独占方式打开时会抛 PermissionError
  - 对此情况做有限次重试（RAG 系统的读取通常是短暂的）
"""

import json
import os
import time
import platform
import logging
from pathlib import Path
from typing import Union, Callable

_logger = logging.getLogger("indexer")

_IS_WINDOWS = platform.system() == "Windows"

_DEFAULT_MAX_RETRIES = 5
_DEFAULT_RETRY_BASE_DELAY = 0.3  # 秒


def atomic_write_json(filepath: Union[str, Path], data: dict, *,
                      indent: int = 1,
                      max_retries: int = _DEFAULT_MAX_RETRIES) -> None:
    """原子写入 JSON 文件（dict → JSON）"""

    def _writer(f):
        json.dump(data, f, ensure_ascii=False, indent=indent, default=str)

    _atomic_write_impl(filepath, _writer, suffix=".json.tmp",
                       max_retries=max_retries)


def atomic_write_jsonl(filepath: Union[str, Path], records: list, *,
                       max_retries: int = _DEFAULT_MAX_RETRIES) -> None:
    """原子写入 JSONL 文件（list[dict] → 每行一个 JSON）"""

    def _writer(f):
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    _atomic_write_impl(filepath, _writer, suffix=".jsonl.tmp",
                       max_retries=max_retries)


def atomic_write_text(filepath: Union[str, Path], text: str, *,
                      max_retries: int = _DEFAULT_MAX_RETRIES) -> None:
    """原子写入纯文本文件"""

    def _writer(f):
        f.write(text)

    _atomic_write_impl(filepath, _writer, suffix=".txt.tmp",
                       max_retries=max_retries)


# ──────────────────────────────────────────────────────────────
# 内部实现
# ──────────────────────────────────────────────────────────────

def _atomic_write_impl(filepath: Union[str, Path],
                       writer_fn: Callable,
                       suffix: str = ".tmp",
                       max_retries: int = _DEFAULT_MAX_RETRIES) -> None:
    """
    原子写入核心流程:
      1. 写入同目录临时文件
      2. flush + fsync 确保数据落盘
      3. os.replace() 原子替换目标文件
      4. 替换失败时自动重试（指数退避）
    """
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = p.with_suffix(suffix)

    # ── Phase 1: 写临时文件（可能失败则直接抛异常） ──
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            writer_fn(f)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        _safe_remove(tmp_path)
        raise

    # ── Phase 2: 原子替换（带重试） ──
    last_err = None
    for attempt in range(max_retries):
        try:
            os.replace(str(tmp_path), str(p))
            return
        except PermissionError as e:
            last_err = e
            delay = _DEFAULT_RETRY_BASE_DELAY * (2 ** attempt)
            _logger.warning(
                f"[atomic_write] rename 被占用，重试 {attempt + 1}/{max_retries} "
                f"({p.name})，等待 {delay:.1f}s: {e}"
            )
            time.sleep(delay)
        except Exception:
            _safe_remove(tmp_path)
            raise

    # 重试耗尽
    _safe_remove(tmp_path)
    raise OSError(
        f"原子写入失败: {p.name} 在 {max_retries} 次重试后仍无法替换 "
        f"(最后错误: {last_err})"
    )


def _safe_remove(path: Path) -> None:
    """安全删除临时文件（忽略不存在等异常）"""
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
