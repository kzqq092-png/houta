"""
配置管理器模块
提供系统配置管理功能
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = "config.json"):
        """初始化配置管理器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self._config = {}
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                # 使用默认配置
                self._config = self._get_default_config()
                self._save_config()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self._config = self._get_default_config()

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "ui": {
                "theme": "light",
                "language": "zh_CN"
            },
            "data": {
                "cache_dir": ".cache",
                "data_dir": "data"
            },
            "indicators": {
                "cache_size": 1000,
                "default_period": 20
            },
            "logging": {
                "level": "INFO",
                "file": "logs/app.log"
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """设置配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config

        # 创建嵌套字典路径
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # 设置最终值
        config[keys[-1]] = value

        # 保存配置
        self._save_config()

    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置节

        Args:
            section: 节名称

        Returns:
            配置节字典
        """
        return self._config.get(section, {})

    def update_section(self, section: str, values: Dict[str, Any]):
        """更新配置节

        Args:
            section: 节名称
            values: 新的配置值
        """
        if section not in self._config:
            self._config[section] = {}

        self._config[section].update(values)
        self._save_config()

    def reload(self):
        """重新加载配置"""
        self._load_config()

    def reset_to_defaults(self):
        """重置为默认配置"""
        self._config = self._get_default_config()
        self._save_config()


# 全局配置管理器实例
_config_manager = None


def get_config_manager(config_file: str = "config.json") -> ConfigManager:
    """获取配置管理器实例

    Args:
        config_file: 配置文件路径

    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager
