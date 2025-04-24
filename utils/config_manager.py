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
    
    config_changed = pyqtSignal(str, object)  # Signal emitted when config changes
    
    def __init__(
        self,
        config_dir: str = ".config",
        config_name: str = "config",
        format: str = "json",
        auto_save: bool = True,
        version: str = "1.0.0"
    ):
        super().__init__()
        
        self.config_dir = config_dir
        self.config_name = config_name
        self.format = format.lower()
        self.auto_save = auto_save
        self.version = version
        
        # Initialize locks
        self._mutex = QMutex()
        
        # Ensure config directory exists
        self._ensure_config_dir()
        
        # Initialize configuration with defaults
        self._init_defaults()
        
        # Load configuration from file
        self.load()
        
        # Initialize configuration objects
        self._init_config_objects()
        
    def _init_defaults(self):
        """Initialize default configuration"""
        self._defaults = {
            "theme": {
                "name": "light",
                "background_color": "#FFFFFF",
                "text_color": "#000000",
                "grid_color": "#E0E0E0",
                "chart_colors": ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728"],
                "custom_colors": {},
                "font_family": "Arial",
                "font_size": 12
            },
            "chart": {
                "show_grid": True,
                "show_volume": True,
                "show_ma": True,
                "ma_periods": [5, 10, 20, 60],
                "candlestick_width": 0.8,
                "chart_height": 600,
                "chart_width": 800,
                "auto_update": True,
                "update_interval": 5,
                "default_period": "D",
                "default_indicators": ["MA", "MACD", "RSI"]
            },
            "trading": {
                "default_symbol": "000001",
                "default_period": "1d",
                "auto_refresh": True,
                "refresh_interval": 60,
                "trade_amount": 10000.0,
                "commission_rate": 0.0003,
                "slippage": 0.0,
                "initial_cash": 1000000.0,
                "position_ratio": 0.8,
                "stop_loss": 0.05,
                "trailing_stop": 0.1,
                "time_stop": 5
            },
            "performance": {
                "enable_monitoring": True,
                "cpu_threshold": 80.0,
                "memory_threshold": 80.0,
                "response_threshold": 1.0,
                "metrics_history_size": 1000,
                "log_to_file": True,
                "log_file": "performance.log"
            },
            "data": {
                "enable_cache": True,
                "max_cache_size": 1000,
                "auto_update": True,
                "update_interval": 3600,
                "data_source": 'local',
                "backup_enabled": True
            },
            "ui": {
                "font_size": 12,
                "language": 'zh_CN',
                "show_tooltips": True,
                "confirm_exit": True,
                "layout": 'default',
                "window_size": {'width': 1200, 'height': 800}
            },
            "logging": {
                "level": "INFO",
                "save_to_file": True,
                "log_file": "hikyuu_ui.log",
                "max_bytes": 10 * 1024 * 1024,  # 10MB
                "backup_count": 5,
                "console_output": True,
                "auto_compress": True,
                "max_logs": 1000,
                "performance_log": True,
                "performance_log_file": "performance.log",
                "exception_log": True,
                "exception_log_file": "exceptions.log",
                "async_logging": True,
                "log_queue_size": 1000,
                "worker_threads": 2
            },
            "cache": {
                "size": 1000,
                "expire_minutes": 30,
                "cleanup_interval": 5
            },
            "system": {
                "max_threads": 4,
                "update_interval": 1000,
                "log_level": "INFO"
            }
        }
        self._config = self._defaults.copy()
        
    def _init_config_objects(self):
        """Initialize configuration objects from loaded config"""
        theme_config = self._config.get("theme", {})
        chart_config = self._config.get("chart", {})
        trading_config = self._config.get("trading", {})
        performance_config = self._config.get("performance", {})
        data_config = self._config.get("data", {})
        ui_config = self._config.get("ui", {})
        logging_config = self._config.get("logging", {})
        
        self._theme = ThemeConfig.from_dict(theme_config)
        self._chart = ChartConfig.from_dict(chart_config)
        self._trading = TradingConfig.from_dict(trading_config)
        self._performance = PerformanceConfig.from_dict(performance_config)
        self._data = DataConfig.from_dict(data_config)
        self._ui = UIConfig.from_dict(ui_config)
        self._logging = LoggingConfig.from_dict(logging_config)
        
    def _ensure_config_dir(self):
        """Ensure configuration directory exists"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
    @property
    def config_path(self) -> str:
        """Get configuration file path"""
        return os.path.join(self.config_dir, f"{self.config_name}.{self.format}")
        
    def load(self):
        """Load configuration from file"""
        try:
            with QMutexLocker(self._mutex):
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        if self.format == 'json':
                            self._config = json.load(f)
                        elif self.format == 'yaml':
                            self._config = yaml.safe_load(f)
                        else:
                            raise ValueError(f"Unsupported format: {self.format}")
                            
                # Apply defaults for missing values
                self._apply_defaults()
                
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            self._config = self._defaults.copy()
            
    def save(self):
        """Save configuration to file"""
        try:
            with QMutexLocker(self._mutex):
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    if self.format == 'json':
                        json.dump(self._config, f, indent=4, ensure_ascii=False)
                    elif self.format == 'yaml':
                        yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
                    else:
                        raise ValueError(f"Unsupported format: {self.format}")
                        
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
                
    def _apply_defaults(self):
        """Apply default values for missing configuration items"""
        for key, value in self._defaults.items():
            if key not in self._config:
                self._config[key] = value
                
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
            logger.error(f"Error getting configuration value: {str(e)}")
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
                
                if self.auto_save:
                    self.save()
                    
                self.config_changed.emit(key, value)
                
        except Exception as e:
            logger.error(f"Error setting configuration value: {str(e)}")
                
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
            if self.auto_save:
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
            if section in self._defaults:
                self._config[section] = self._defaults[section].copy()
                self.config_changed.emit(section, self._config[section])
                if self.auto_save:
                    self.save()
                    
    def reset_all(self):
        """Reset all configuration to defaults"""
        with QMutexLocker(self._mutex):
            self._config = self._defaults.copy()
            self.config_changed.emit("all", self._config)
            if self.auto_save:
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
            return self._config.get('version', self.version)
            
    def set_version(self, version: str):
        """设置配置版本
        
        Args:
            version: 新版本
        """
        with QMutexLocker(self._mutex):
            self._config['version'] = version
            if self.auto_save:
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
                        if self.format == 'json':
                            json.dump(json.load(src), dst, indent=2, ensure_ascii=False)
                        elif self.format == 'yaml':
                            yaml.safe_dump(yaml.safe_load(src), dst, allow_unicode=True)
                            
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
                    if self.format == 'json':
                        config = json.load(f)
                    elif self.format == 'yaml':
                        config = yaml.safe_load(f)
                        
                # 验证配置
                if not self.validate(config):
                    logger.error("备份配置验证失败")
                    return False
                    
                # 更新配置
                self._config = config
                if self.auto_save:
                    self.save()
                    
                return True
                
        except Exception as e:
            logger.error(f"恢复配置失败: {str(e)}")
            return False 