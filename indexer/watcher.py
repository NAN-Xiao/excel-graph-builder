#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件系统监控 - Indexer 独立模块
"""

from pathlib import Path
from typing import Callable, Optional

from indexer import SimpleLogger

_logger = SimpleLogger()

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    _logger.warning("watchdog 未安装，文件监控功能不可用。请运行: pip install watchdog")


class ExcelChangeHandler(FileSystemEventHandler):
    """Excel 文件变化处理器"""
    
    def __init__(self, on_change: Callable[[str, str], None]):
        self.on_change = on_change
    
    def on_modified(self, event):
        if not event.is_directory and self._is_excel(event.src_path):
            self.on_change(event.src_path, 'modified')
    
    def on_created(self, event):
        if not event.is_directory and self._is_excel(event.src_path):
            self.on_change(event.src_path, 'created')
    
    def on_deleted(self, event):
        if not event.is_directory and self._is_excel(event.src_path):
            self.on_change(event.src_path, 'deleted')
    
    def _is_excel(self, path: str) -> bool:
        return path.lower().endswith(('.xlsx', '.xls', '.csv', '.tsv'))


class FileWatcher:
    """文件监控管理器"""
    
    def __init__(self, watch_path: str, on_change: Callable[[str, str], None]):
        self.watch_path = Path(watch_path)
        self.on_change = on_change
        self.observer: Optional[Observer] = None
        self._running = False
    
    def start(self):
        """启动监控"""
        if not WATCHDOG_AVAILABLE:
            _logger.error("watchdog 未安装，无法启动监控")
            return False
        
        if self._running:
            return True
        
        try:
            handler = ExcelChangeHandler(self.on_change)
            self.observer = Observer()
            self.observer.schedule(handler, str(self.watch_path), recursive=True)
            self.observer.start()
            self._running = True
            
            _logger.success(f"文件监控已启动: {self.watch_path}")
            return True
        except Exception as e:
            _logger.error(f"启动监控失败: {e}")
            return False
    
    def stop(self):
        """停止监控"""
        if self.observer and self._running:
            self.observer.stop()
            self.observer.join()
            self._running = False
            _logger.info("文件监控已停止")
    
    def is_running(self) -> bool:
        return self._running
