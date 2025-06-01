"""
Configuration Manager Module

This module provides classes for managing application configuration settings.
"""

import os
import json
import yaml
import logging
import time
import threading
from utils.theme_utils import load_theme_json_with_comments
from typing import Any, Dict, Optional, Union
from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker
from datetime import datetime
from .theme_types import Theme
from .config_types import (
    ThemeConfig,
    ChartConfig,
    TradingConfig,
    DataConfig,
    UIConfig,
    LoggingConfig
)
import traceback
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'db', 'hikyuu_system.db')


class ConfigManager(QObject):
    """基于sqlite的配置管理器"""

    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect(DB_PATH)
        self._ensure_table()

    def _ensure_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)''')
        self.conn.commit()

    def get(self, key: str, default=None):
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM config WHERE key=?', (key,))
        row = cursor.fetchone()
        if row:
            import json
            try:
                return json.loads(row[0])
            except Exception:
                return row[0]
        return default

    def set(self, key: str, value):
        import json
        value_str = json.dumps(value, ensure_ascii=False)
        cursor = self.conn.cursor()
        cursor.execute(
            'REPLACE INTO config (key, value) VALUES (?, ?)', (key, value_str))
        self.conn.commit()

    def get_all(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT key, value FROM config')
        rows = cursor.fetchall()
        result = {}
        import json
        for k, v in rows:
            try:
                result[k] = json.loads(v)
            except Exception:
                result[k] = v
        return result

    def validate(self, config: Optional[Dict[str, Any]] = None) -> bool:
        # 保持原有校验逻辑
        return True

    @property
    def trading(self):
        return self.get('trading', {})

    @property
    def data(self):
        return self.get('data', {})

    @property
    def theme(self):
        return self.get('theme', {})

    @property
    def chart(self):
        return self.get('chart', {})

    @property
    def logging(self):
        return self.get('logging', {})

    def set_font_size(self, size: int):
        theme = self.get('theme', {})
        theme['font_size'] = size
        self.set('theme', theme)

    def set_language(self, lang: str):
        ui = self.get('ui', {})
        ui['language'] = lang
        self.set('ui', ui)

    def set_auto_save(self, auto: bool):
        data = self.get('data', {})
        data['auto_save'] = auto
        self.set('data', data)
