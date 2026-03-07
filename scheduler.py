#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
定时调度器 - Indexer 独立模块
"""

import time
import threading
from datetime import datetime
from typing import Optional, Callable

import schedule

try:
    from indexer import SimpleLogger
except ImportError:
    from __init__ import SimpleLogger


class DelayedTask:
    """延迟执行任务（防抖机制）"""
    
    def __init__(self, callback: Callable, delay_seconds: float, logger=None):
        self.callback = callback
        self.delay_seconds = delay_seconds
        self.logger = logger or SimpleLogger()
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
    
    def trigger(self, *args, **kwargs):
        """触发延迟执行（重置计时器）"""
        with self._lock:
            # 取消已有的计时器
            if self._timer and self._timer.is_alive():
                self._timer.cancel()
                self.logger.debug(f"重置延迟任务计时器 ({self.delay_seconds}s)")
            
            # 创建新计时器
            self._timer = threading.Timer(
                self.delay_seconds, 
                self._execute, 
                args=args, 
                kwargs=kwargs
            )
            self._timer.daemon = True
            self._timer.start()
            self.logger.debug(f"延迟任务已设置 ({self.delay_seconds}s后执行)")
    
    def _execute(self, *args, **kwargs):
        """实际执行"""
        with self._lock:
            self._timer = None
        try:
            self.callback(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"延迟任务执行失败: {e}")
    
    def cancel(self):
        """取消待执行的延迟任务"""
        with self._lock:
            if self._timer and self._timer.is_alive():
                self._timer.cancel()
                self._timer = None
    
    def is_pending(self) -> bool:
        """是否有待执行的任务"""
        with self._lock:
            return self._timer is not None and self._timer.is_alive()


class BuildScheduler:
    """构建任务调度器"""
    
    def __init__(self):
        self.jobs = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._delayed_tasks: Dict[str, DelayedTask] = {}
    
    def add_daily_job(self, job_func: Callable, hour: int = 2, minute: int = 0):
        """添加每日定时任务"""
        job = schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(job_func)
        self.jobs.append(job)
        print(f"[INFO] 添加每日任务: {hour:02d}:{minute:02d}")
        return job
    
    def add_interval_job(self, job_func: Callable, minutes: int):
        """添加间隔任务"""
        job = schedule.every(minutes).minutes.do(job_func)
        self.jobs.append(job)
        print(f"[INFO] 添加间隔任务: 每 {minutes} 分钟")
        return job
    
    def add_delayed_task(self, name: str, callback: Callable, delay_seconds: float) -> DelayedTask:
        """
        添加一个可重复触发的延迟任务（防抖）
        
        Args:
            name: 任务标识名
            callback: 实际执行的函数
            delay_seconds: 延迟秒数
        
        Returns:
            DelayedTask 实例
        """
        task = DelayedTask(callback, delay_seconds)
        self._delayed_tasks[name] = task
        return task
    
    def trigger_delayed(self, name: str, *args, **kwargs):
        """触发指定名称的延迟任务"""
        if name in self._delayed_tasks:
            self._delayed_tasks[name].trigger(*args, **kwargs)
    
    def cancel_delayed(self, name: str):
        """取消指定名称的延迟任务"""
        if name in self._delayed_tasks:
            self._delayed_tasks[name].cancel()
    
    def start(self, blocking: bool = False):
        """启动调度器"""
        with self._lock:
            if self._running:
                print("[WARN] 调度器已在运行")
                return
            
            self._running = True
            
            if blocking:
                self._run_loop()
            else:
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()
                print("[OK] 调度器已在后台启动")
    
    def stop(self):
        """停止调度器"""
        with self._lock:
            self._running = False
            schedule.clear()
            # 取消所有延迟任务
            for task in self._delayed_tasks.values():
                task.cancel()
            print("[INFO] 调度器已停止")
    
    def _run_loop(self):
        """主循环"""
        print("[INFO] 调度循环已启动")
        
        while self._running:
            try:
                schedule.run_pending()
            except Exception as e:
                print(f"[ERR] 执行任务出错: {e}")
            
            time.sleep(60)
    
    def run_now(self, job_func: Callable):
        """立即执行一次任务"""
        print("[INFO] 立即执行任务")
        try:
            job_func()
        except Exception as e:
            print(f"[ERR] 立即执行出错: {e}")


# 导入 Dict 类型
from typing import Dict
