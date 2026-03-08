#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 4: 人工反馈闭环

保存人工确认/拒绝的关系，下次构建时直接使用
"""

import os
import json
import threading
from typing import Set, Dict
from datetime import datetime
from indexer import SimpleLogger


class FeedbackManager:
    """反馈管理器（内存缓存 + 定时持久化）"""

    def __init__(self, feedback_file: str = "relation_feedback.json",
                 auto_save_interval: int = 60):
        self.feedback_file = feedback_file
        self.confirmed: Set[str] = set()
        self.rejected: Set[str] = set()
        self._modified = False
        self._lock = threading.Lock()
        self.logger = SimpleLogger()

        # 加载现有反馈
        self._load()

        # 启动定时保存线程
        self._stop_event = threading.Event()
        self._save_thread = threading.Thread(
            target=self._auto_save,
            args=(auto_save_interval,),
            daemon=True
        )
        self._save_thread.start()

    def _load(self):
        """加载反馈"""
        if not os.path.exists(self.feedback_file):
            return

        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data.get('confirmed', []):
                self.confirmed.add(item['relation_key'])
            for item in data.get('rejected', []):
                self.rejected.add(item['relation_key'])
            self.logger.info(
                f"[Feedback] 加载 {len(self.confirmed)} 确认, {len(self.rejected)} 拒绝")
        except Exception as e:
            self.logger.error(f"[Feedback] 加载失败: {e}")

    def _auto_save(self, interval: int):
        """定时保存线程"""
        while not self._stop_event.wait(interval):
            if self._modified:
                self._save()

    def _save(self):
        """保存到文件"""
        with self._lock:
            if not self._modified:
                return

            try:
                data = {
                    'confirmed': [{'relation_key': k} for k in self.confirmed],
                    'rejected': [{'relation_key': k} for k in self.rejected],
                    'updated_at': datetime.now().isoformat()
                }
                with open(self.feedback_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self._modified = False
            except Exception as e:
                self.logger.error(f"[Feedback] 保存失败: {e}")

    def confirm(self, from_table: str, from_col: str, to_table: str, to_col: str):
        """确认关系正确"""
        key = f"{from_table}.{from_col}->{to_table}.{to_col}"
        with self._lock:
            self.confirmed.add(key)
            self.rejected.discard(key)
            self._modified = True

    def reject(self, from_table: str, from_col: str, to_table: str, to_col: str):
        """标记关系错误"""
        key = f"{from_table}.{from_col}->{to_table}.{to_col}"
        with self._lock:
            self.rejected.add(key)
            self.confirmed.discard(key)
            self._modified = True

    def check(self, from_table: str, from_col: str, to_table: str, to_col: str) -> str:
        """检查状态: 'confirmed' | 'rejected' | 'unknown'"""
        key = f"{from_table}.{from_col}->{to_table}.{to_col}"
        if key in self.confirmed:
            return 'confirmed'
        if key in self.rejected:
            return 'rejected'
        return 'unknown'

    def apply_to_graph(self, graph) -> int:
        """应用反馈到图谱：确认的置信度置 1.0，拒绝的直接移除"""
        count = 0
        kept = []
        for rel in graph.relations:
            key_fwd = f"{rel.from_table}.{rel.from_column}->{rel.to_table}.{rel.to_column}"
            key_rev = f"{rel.to_table}.{rel.to_column}->{rel.from_table}.{rel.from_column}"
            if key_fwd in self.rejected or key_rev in self.rejected:
                count += 1
                continue  # 真正移除
            if key_fwd in self.confirmed or key_rev in self.confirmed:
                rel.confidence = 1.0
                count += 1
            kept.append(rel)
        graph.relations = kept
        return count

    def force_save(self):
        """强制立即保存"""
        self._save()

    def stop(self):
        """停止并保存"""
        self._stop_event.set()
        self._save_thread.join(timeout=5)
        self.force_save()
