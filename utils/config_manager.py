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
    PerformanceConfig,
    DataConfig,
    UIConfig,
    LoggingConfig
)
import traceback

logger = logging.getLogger(__name__)


class ConfigManager(QObject):
    """Enhanced configuration manager with validation and auto-save support

    Features:
    - Multiple configuration formats support (JSON, YAML)
    - Configuration validation
    - Automatic saving
    - Thread-safe operations
    - Change notifications
    - Default values
    - Configuration sections
    - Version management
    """

    # Signal emitted when config changes
    config_changed = pyqtSignal(str, object)
    # Signal emitted when logging config changes
    logging_config_changed = pyqtSignal(LoggingConfig)

    def __init__(self, config_dir: str = None, config_name: str = "config.json",
                 format: str = "json", auto_save: bool = True, version: str = "1.0.0"):
        """Initialize configuration manager

        Args:
            config_dir: Configuration directory path
            config_name: Configuration file name
            format: Configuration file format (json/yaml)
            auto_save: Whether to auto save on changes
            version: Configuration version
        """
        super().__init__()

        self._config_dir = config_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config")
        self._config_name = config_name
        self._format = format.lower()
        self._auto_save = auto_save
        self._version = version

        # Initialize locks
        self._mutex = QMutex()

        # Ensure config directory exists
        self._ensure_config_dir()

        # Load configuration
        self._config = self._load_config()

        # Initialize configuration objects
        self._init_config_objects()

        # Connect logging config change signal
        if hasattr(self, '_logging'):
            self._logging.config_changed.connect(
                self._on_logging_config_changed)

    def _load_config(self) -> dict:
        """Load configuration from file

        Returns:
            Configuration dictionary
        """
        config_path = os.path.join(self._config_dir, self._config_name)

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    if self._format == 'json':
                        return json.load(f)
                    elif self._format == 'yaml':
                        return yaml.safe_load(f)
            else:
                print(f"配置文件不存在，将创建默认配置: {config_path}")
                return {}

        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            print(traceback.format_exc())
            return {}

    def _init_config_objects(self):
        """Initialize configuration objects from loaded data"""
        try:
            # Get config sections with defaults
            theme_config = self._config.get('theme', {})
            chart_config = self._config.get('chart', {})
            trading_config = self._config.get('trading', {})
            performance_config = self._config.get('performance', {})
            data_config = self._config.get('data', {})
            ui_config = self._config.get('ui', {})
            logging_config = self._config.get('logging', {})

            # Create config objects
            self._theme = ThemeConfig.from_dict(theme_config)
            self._chart = ChartConfig.from_dict(chart_config)
            self._trading = TradingConfig.from_dict(trading_config)
            self._performance = PerformanceConfig.from_dict(performance_config)
            self._data = DataConfig.from_dict(data_config)
            self._ui = UIConfig.from_dict(ui_config)
            self._logging = LoggingConfig.from_dict(logging_config)

            # Connect logging config change signal
            self._logging.config_changed.connect(
                self._on_logging_config_changed)

        except Exception as e:
            print(f"配置初始化失败，使用默认配置: {str(e)}")
            print(traceback.format_exc())

            # Create default config objects
            self._theme = ThemeConfig()
            self._chart = ChartConfig()
            self._trading = TradingConfig()
            self._performance = PerformanceConfig()
            self._data = DataConfig()
            self._ui = UIConfig()
            self._logging = LoggingConfig()

            # Connect logging config change signal
            self._logging.config_changed.connect(
                self._on_logging_config_changed)

            # Save default configuration
            self.save()

    def _ensure_config_dir(self):
        """Ensure configuration directory exists"""
        if not os.path.exists(self._config_dir):
            os.makedirs(self._config_dir)

    @property
    def config_path(self) -> str:
        """Get configuration file path"""
        return os.path.join(self._config_dir, self._config_name)

    def save(self):
        """Save configuration to file"""
        try:
            config = {
                'version': self._version,
                'theme': self._theme.to_dict(),
                'chart': self._chart.to_dict(),
                'trading': self._trading.to_dict(),
                'performance': self._performance.to_dict(),
                'data': self._data.to_dict(),
                'ui': self._ui.to_dict(),
                'logging': self._logging.to_dict()
            }

            with QMutexLocker(self._mutex):
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    if self._format == 'json':
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    elif self._format == 'yaml':
                        yaml.safe_dump(config, f, allow_unicode=True)

            print(f"配置已保存到: {self.config_path}")

        except Exception as e:
            print(f"保存配置失败: {str(e)}")
            print(traceback.format_exc())

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        try:
            with QMutexLocker(self._mutex):
                keys = key.split('.')
                value = self._config

                for k in keys:
                    if isinstance(value, dict):
                        value = value.get(k, default)
                    else:
                        return default

                return value

        except Exception as e:
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(
                    f"Error getting configuration value: {str(e)}")
            else:
                print(f"Error getting configuration value: {str(e)}")
            return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value

        Args:
            key: Configuration key
            value: Configuration value
        """
        try:
            with QMutexLocker(self._mutex):
                keys = key.split('.')
                config = self._config

                for k in keys[:-1]:
                    if k not in config:
                        config[k] = {}
                    config = config[k]

                config[keys[-1]] = value

                if self._auto_save:
                    self.save()

                self.config_changed.emit(key, value)

        except Exception as e:
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(
                    f"Error setting configuration value: {str(e)}")
            else:
                print(f"Error setting configuration value: {str(e)}")

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section

        Args:
            section: Section name

        Returns:
            Section configuration
        """
        with QMutexLocker(self._mutex):
            return self._config.get(section, {}).copy()

    def set_section(self, section: str, config: Dict[str, Any]):
        """Set configuration section

        Args:
            section: Section name
            config: Section configuration
        """
        with QMutexLocker(self._mutex):
            self._config[section] = config.copy()
            self.config_changed.emit(section, config)
            if self._auto_save:
                self.save()

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration

        Returns:
            All configuration
        """
        with QMutexLocker(self._mutex):
            return self._config.copy()

    def reset_section(self, section: str):
        """Reset configuration section to defaults

        Args:
            section: Section name
        """
        with QMutexLocker(self._mutex):
            if section in self._config:
                self._config[section] = {}
                self.config_changed.emit(section, self._config[section])
                if self._auto_save:
                    self.save()

    def reset_all(self):
        """Reset all configuration to defaults"""
        with QMutexLocker(self._mutex):
            self._config = {}
            self.config_changed.emit("all", self._config)
            if self._auto_save:
                self.save()

    def validate(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """验证配置

        Args:
            config: 要验证的配置，默认为当前配置

        Returns:
            配置是否有效
        """
        try:
            if config is None:
                config = self._config

            # 验证版本
            if 'version' not in config:
                logger.error("配置缺少版本信息")
                return False

            # 验证必需的配置部分
            required_sections = {
                'theme': ThemeConfig,
                'chart': ChartConfig,
                'trading': TradingConfig,
                'performance': PerformanceConfig,
                'data': DataConfig,
                'ui': UIConfig,
                'logging': LoggingConfig
            }

            for section, config_class in required_sections.items():
                if section not in config:
                    logger.error(f"缺少必需的配置部分: {section}")
                    return False

                try:
                    # 尝试创建配置对象来验证数据
                    config_class.from_dict(config[section])
                except Exception as e:
                    logger.error(f"配置部分 {section} 验证失败: {str(e)}")
                    return False

            return True

        except Exception as e:
            logger.error(f"配置验证失败: {str(e)}")
            return False

    @property
    def trading(self) -> TradingConfig:
        """Get trading configuration"""
        return self._trading

    @property
    def data(self) -> DataConfig:
        """Get data configuration"""
        return self._data

    @property
    def theme(self) -> ThemeConfig:
        """Get theme configuration"""
        return self._theme

    @property
    def chart(self) -> ChartConfig:
        """Get chart configuration"""
        return self._chart

    @property
    def ui(self) -> UIConfig:
        """Get UI configuration"""
        return self._ui

    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration"""
        return self._logging

    @property
    def performance(self) -> PerformanceConfig:
        """Get performance configuration"""
        return self._performance

    def get_version(self) -> str:
        """获取配置版本

        Returns:
            配置版本
        """
        with QMutexLocker(self._mutex):
            return self._config.get('version', self._version)

    def set_version(self, version: str):
        """设置配置版本

        Args:
            version: 新版本
        """
        with QMutexLocker(self._mutex):
            self._config['version'] = version
            if self._auto_save:
                self.save()

    def backup_config(self) -> bool:
        """备份当前配置

        Returns:
            是否备份成功
        """
        try:
            with QMutexLocker(self._mutex):
                # 创建备份文件名
                backup_path = f"{self.config_path}.{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"

                # 复制配置文件
                with open(self.config_path, 'r', encoding='utf-8') as src:
                    with open(backup_path, 'w', encoding='utf-8') as dst:
                        if self._format == 'json':
                            json.dump(json.load(src), dst,
                                      indent=2, ensure_ascii=False)
                        elif self._format == 'yaml':
                            yaml.safe_dump(yaml.safe_load(
                                src), dst, allow_unicode=True)

                return True

        except Exception as e:
            logger.error(f"备份配置失败: {str(e)}")
            return False

    def restore_backup(self, backup_path: str) -> bool:
        """从备份恢复配置

        Args:
            backup_path: 备份文件路径

        Returns:
            是否恢复成功
        """
        try:
            with QMutexLocker(self._mutex):
                # 读取备份文件
                with open(backup_path, 'r', encoding='utf-8') as f:
                    if self._format == 'json':
                        config = json.load(f)
                    elif self._format == 'yaml':
                        config = yaml.safe_load(f)

                # 验证配置
                if not self.validate(config):
                    logger.error("备份配置验证失败")
                    return False

                # 更新配置
                self._config = config
                if self._auto_save:
                    self.save()

                return True

        except Exception as e:
            logger.error(f"恢复配置失败: {str(e)}")
            return False

    def _on_logging_config_changed(self, new_config: LoggingConfig):
        """Handle logging configuration changes"""
        try:
            # 更新配置
            self._config['logging'] = new_config.to_dict()

            # 保存配置
            if self._auto_save:
                self.save()

            # 发送配置变更信号
            self.config_changed.emit('logging', new_config.to_dict())

        except Exception as e:
            logger.error(f"处理日志配置变更失败: {str(e)}")

    def set_logging_config(self, new_config: LoggingConfig):
        """设置日志配置

        Args:
            new_config: 新的日志配置
        """
        try:
            # 验证配置
            is_valid, error_msg = new_config.validate()
            if not is_valid:
                raise ValueError(f"日志配置无效: {error_msg}")

            # 发送日志配置变更信号
            self.logging_config_changed.emit(new_config)

        except Exception as e:
            logger.error(f"设置日志配置失败: {str(e)}")
