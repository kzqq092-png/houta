"""
Configuration Manager Module - 专业级配置管理

This module provides classes for managing application configuration settings.
合并了验证、迁移、备份等专业功能，对标专业软件
"""

import os
import json
import yaml
import logging
import time
import threading
from utils.theme_utils import load_theme_json_with_comments
from typing import Any, Dict, Optional, Union, List
from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker
from PyQt5.QtCore import QTimer, QThread, pyqtSlot
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
import sys
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'db', 'hikyuu_system.db')


class ConfigManager(QObject):
    """专业级配置管理器 - 基于SQLite，支持验证、迁移、备份"""

    # 专业级信号
    config_changed = pyqtSignal(str, object)  # 配置项变更信号 (key, value)
    config_validated = pyqtSignal(bool, str)  # 配置验证信号 (is_valid, message)
    config_migrated = pyqtSignal(str, str)    # 配置迁移信号 (from_version, to_version)
    config_backed_up = pyqtSignal(str)        # 配置备份信号 (backup_path)

    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._mutex = QMutex()
        self._ensure_table()

        # 初始化时验证和迁移配置
        self._initialize_config()

    def _ensure_table(self):
        """确保配置表存在"""
        cursor = self.conn.cursor()
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY, 
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

        # 创建配置历史表
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS config_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                old_value TEXT,
                new_value TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

        self.conn.commit()

    def _initialize_config(self):
        """初始化配置，包括验证和迁移"""
        try:
            current_config = self.get_all()

            # 如果没有配置，创建默认配置
            if not current_config:
                self._create_default_config()
                return

            # 验证配置
            is_valid, message = self.validate_config(current_config)
            self.config_validated.emit(is_valid, message)

            if not is_valid:
                logger.warning(f"配置验证失败: {message}，将使用默认配置")
                self._create_default_config()
                return

            # 迁移配置
            current_version = current_config.get('version', '1.0.0')
            migrated_config = self.migrate_config(current_config, current_version)

            if migrated_config != current_config:
                # 配置已迁移，保存新配置
                for key, value in migrated_config.items():
                    self.set(key, value)
                logger.info("配置迁移完成")

        except Exception as e:
            logger.error(f"配置初始化失败: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """创建默认配置"""
        default_config = {
            'version': '1.3.0',
            'theme': {
                'theme_name': 'default',
                'font_size': 12,
                'color_scheme': 'light'
            },
            'trading': {
                'initial_cash': 100000,
                'commission_rate': 0.0003,
                'position_ratio': 1.0,
                'stop_loss': 0.05,
                'trailing_stop': 0.1,
                'time_stop': 5
            },
            'data': {
                'source': 'hikyuu',
                'auto_save': True,
                'cache_enabled': True
            },
            'logging': {
                'level': 'INFO',
                'save_to_file': True,
                'console_output': True,
                'log_file': 'trading_system.log'
            },
            'ui': {
                'theme': 'default',
                'language': 'zh_CN'
            },
            'performance': {
                'track_time': True,
                'track_memory': True,
                'track_cpu': True,
                'track_exceptions': True
            }
        }

        for key, value in default_config.items():
            self.set(key, value)

        logger.info("默认配置已创建")

    def get(self, key: str, default=None):
        """获取配置项"""
        with QMutexLocker(self._mutex):
            cursor = self.conn.cursor()
            cursor.execute('SELECT value FROM config WHERE key=?', (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except Exception:
                    return row[0]
            return default

    def set(self, key: str, value):
        """设置配置项"""
        with QMutexLocker(self._mutex):
            # 获取旧值用于历史记录
            old_value = self.get(key)

            value_str = json.dumps(value, ensure_ascii=False)
            cursor = self.conn.cursor()

            # 更新配置
            cursor.execute(
                '''REPLACE INTO config (key, value, updated_at) 
                   VALUES (?, ?, CURRENT_TIMESTAMP)''',
                (key, value_str))

            # 记录历史
            if old_value != value:
                old_value_str = json.dumps(old_value, ensure_ascii=False) if old_value is not None else None
                cursor.execute(
                    '''INSERT INTO config_history (key, old_value, new_value) 
                       VALUES (?, ?, ?)''',
                    (key, old_value_str, value_str))

                # 发送变更信号
                self.config_changed.emit(key, value)

            self.conn.commit()

    def set_async(self, key: str, value, callback=None):
        """真正异步设置配置项，使用QThread避免阻塞UI"""
        from PyQt5.QtCore import QThread, QObject, pyqtSignal

        class ConfigSaveWorker(QObject):
            finished = pyqtSignal(bool, str)  # success, error_message

            def __init__(self, config_manager, key, value):
                super().__init__()
                self.config_manager = config_manager
                self.key = key
                self.value = value

            def save_config(self):
                try:
                    self.config_manager.set(self.key, self.value)
                    self.finished.emit(True, "")
                except Exception as e:
                    logger.error(f"异步保存配置失败: {str(e)}")
                    self.finished.emit(False, str(e))

        def on_save_finished(success, error_msg):
            if callback:
                callback(success, error_msg if not success else None)

        # 创建工作线程（如果不存在）
        if not hasattr(self, '_async_save_thread'):
            self._async_save_thread = QThread()
            self._async_save_thread.start()

        # 创建工作对象
        worker = ConfigSaveWorker(self, key, value)
        worker.moveToThread(self._async_save_thread)
        worker.finished.connect(on_save_finished)

        # 异步执行保存操作
        QTimer.singleShot(0, worker.save_config)

    def get_all(self):
        """获取所有配置"""
        with QMutexLocker(self._mutex):
            cursor = self.conn.cursor()
            cursor.execute('SELECT key, value FROM config')
            rows = cursor.fetchall()
            result = {}
            for k, v in rows:
                try:
                    result[k] = json.loads(v)
                except Exception:
                    result[k] = v
            return result

    def validate_config(self, config: Optional[Dict[str, Any]] = None) -> tuple[bool, str]:
        """验证配置是否有效

        Args:
            config: 配置字典，如果为None则验证当前配置

        Returns:
            (是否有效, 错误消息)
        """
        try:
            if config is None:
                config = self.get_all()

            # 验证版本信息
            if 'version' not in config:
                return False, "配置缺少版本信息"

            # 验证必需的配置部分
            required_sections = {
                'theme': dict,
                'trading': dict,
                'data': dict,
                'logging': dict
            }

            for section, expected_type in required_sections.items():
                if section not in config:
                    return False, f"缺少必需的配置部分: {section}"

                if not isinstance(config[section], expected_type):
                    return False, f"配置部分 {section} 类型错误"

            # 验证交易配置
            if 'trading' in config:
                trading_config = config['trading']

                # 验证佣金率
                commission_rate = trading_config.get('commission_rate', 0)
                if not isinstance(commission_rate, (int, float)) or commission_rate < 0:
                    return False, "佣金率必须为非负数"

                # 验证初始资金
                initial_cash = trading_config.get('initial_cash', 0)
                if not isinstance(initial_cash, (int, float)) or initial_cash <= 0:
                    return False, "初始资金必须大于0"

                # 验证仓位比例
                position_ratio = trading_config.get('position_ratio', 0)
                if not isinstance(position_ratio, (int, float)) or not 0 <= position_ratio <= 1:
                    return False, "仓位比例必须在0到1之间"

            # 验证日志配置
            if 'logging' in config:
                logging_config = config['logging']
                valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                level = logging_config.get('level', 'INFO')
                if level not in valid_levels:
                    return False, f"日志级别必须是以下之一: {valid_levels}"

            return True, "配置验证通过"

        except Exception as e:
            return False, f"配置验证失败: {str(e)}"

    def migrate_config(self, config: Dict[str, Any], current_version: str) -> Dict[str, Any]:
        """迁移配置到最新版本

        Args:
            config: 当前配置
            current_version: 当前配置版本

        Returns:
            迁移后的配置
        """
        try:
            migrated_config = config.copy()
            original_version = current_version

            # 如果没有版本信息，假定为最早的版本
            if 'version' not in migrated_config:
                migrated_config['version'] = '1.0.0'
                current_version = '1.0.0'

            # 逐步迁移
            if current_version == '1.0.0':
                migrated_config['version'] = '1.1.0'
                current_version = '1.1.0'
                logger.info("配置已迁移到版本 1.1.0")

            if current_version == '1.1.0':
                # 迁移到 1.2.0
                if 'ui' not in migrated_config:
                    migrated_config['ui'] = {'theme': 'default', 'language': 'zh_CN'}

                # 更新交易配置
                if 'trading' in migrated_config:
                    trading = migrated_config['trading']
                    if 'stop_loss' not in trading:
                        trading['stop_loss'] = 0.05
                    if 'trailing_stop' not in trading:
                        trading['trailing_stop'] = 0.1
                    if 'time_stop' not in trading:
                        trading['time_stop'] = 5

                migrated_config['version'] = '1.2.0'
                current_version = '1.2.0'
                logger.info("配置已迁移到版本 1.2.0")

            if current_version == '1.2.0':
                # 迁移到 1.3.0
                if 'performance' not in migrated_config:
                    migrated_config['performance'] = {
                        'track_time': True,
                        'track_memory': True,
                        'track_cpu': True,
                        'track_exceptions': True
                    }
                else:
                    perf = migrated_config['performance']
                    if 'track_time' not in perf:
                        perf['track_time'] = True
                    if 'track_memory' not in perf:
                        perf['track_memory'] = True
                    if 'track_cpu' not in perf:
                        perf['track_cpu'] = True
                    if 'track_exceptions' not in perf:
                        perf['track_exceptions'] = True

                migrated_config['version'] = '1.3.0'
                current_version = '1.3.0'
                logger.info("配置已迁移到版本 1.3.0")

            # 如果版本有变化，发送迁移信号
            if original_version != current_version:
                self.config_migrated.emit(original_version, current_version)

            return migrated_config

        except Exception as e:
            logger.error(f"配置迁移失败: {str(e)}")
            return config

    def backup_config(self, backup_dir: str = "backups") -> Optional[str]:
        """备份当前配置

        Args:
            backup_dir: 备份目录

        Returns:
            备份文件路径，如果备份失败则返回 None
        """
        try:
            # 确保备份目录存在
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            # 创建备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"config_backup_{timestamp}.json")

            # 保存当前配置
            config_data = {
                'backup_timestamp': timestamp,
                'backup_version': '1.0',
                'config': self.get_all()
            }

            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"配置已备份到: {backup_path}")
            self.config_backed_up.emit(backup_path)
            return backup_path

        except Exception as e:
            logger.error(f"配置备份失败: {str(e)}")
            return None

    def restore_config(self, backup_path: str) -> bool:
        """从备份恢复配置

        Args:
            backup_path: 备份文件路径

        Returns:
            是否恢复成功
        """
        try:
            # 读取备份文件
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            # 提取配置数据
            if 'config' in backup_data:
                config = backup_data['config']
            else:
                # 兼容旧格式
                config = backup_data

            # 验证配置
            is_valid, message = self.validate_config(config)
            if not is_valid:
                logger.error(f"备份配置验证失败: {message}")
                return False

            # 迁移配置到最新版本
            config = self.migrate_config(config, config.get('version', '1.0.0'))

            # 更新配置
            for key, value in config.items():
                self.set(key, value)

            logger.info(f"配置已从备份恢复: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"恢复配置失败: {str(e)}")
            return False

    def get_config_history(self, key: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取配置变更历史

        Args:
            key: 配置键，如果为None则获取所有配置的历史
            limit: 返回记录数限制

        Returns:
            配置变更历史列表
        """
        with QMutexLocker(self._mutex):
            cursor = self.conn.cursor()

            if key:
                cursor.execute(
                    '''SELECT key, old_value, new_value, changed_at 
                       FROM config_history 
                       WHERE key = ? 
                       ORDER BY changed_at DESC 
                       LIMIT ?''',
                    (key, limit))
            else:
                cursor.execute(
                    '''SELECT key, old_value, new_value, changed_at 
                       FROM config_history 
                       ORDER BY changed_at DESC 
                       LIMIT ?''',
                    (limit,))

            rows = cursor.fetchall()
            history = []

            for key, old_value, new_value, changed_at in rows:
                try:
                    old_val = json.loads(old_value) if old_value else None
                    new_val = json.loads(new_value) if new_value else None
                except Exception:
                    old_val = old_value
                    new_val = new_value

                history.append({
                    'key': key,
                    'old_value': old_val,
                    'new_value': new_val,
                    'changed_at': changed_at
                })

            return history

    def export_config(self, filepath: str = None) -> str:
        """导出配置到文件

        Args:
            filepath: 导出文件路径

        Returns:
            导出文件路径
        """
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"config_export_{timestamp}.json"

        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'export_version': '1.0',
                'system_info': {
                    'platform': os.name,
                    'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                },
                'config': self.get_all(),
                'config_history': self.get_config_history(limit=50)
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"配置已导出到: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            raise

    # 保持向后兼容的属性方法
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

    @property
    def ui(self):
        return self.get('ui', {})

    @property
    def performance(self):
        return self.get('performance', {})

    def set_theme_type(self, size: int, theme_name: str):
        """设置主题类型"""
        theme = self.get('theme', {})
        theme['font_size'] = size
        theme['theme_name'] = theme_name
        self.set('theme', theme)

    def set_language(self, lang: str):
        """设置语言"""
        ui = self.get('ui', {})
        ui['language'] = lang
        self.set('ui', ui)

    def set_auto_save(self, auto: bool):
        """设置自动保存"""
        data = self.get('data', {})
        data['auto_save'] = auto
        self.set('data', data)

    def __del__(self):
        """析构函数"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
        except Exception:
            pass


# 全局配置管理器实例
_config_manager = None
_config_lock = threading.Lock()


def get_config_manager() -> ConfigManager:
    """获取配置管理器单例"""
    global _config_manager

    if _config_manager is None:
        with _config_lock:
            if _config_manager is None:
                _config_manager = ConfigManager()

    return _config_manager


# 导出的公共接口
__all__ = [
    'ConfigManager',
    'get_config_manager'
]
