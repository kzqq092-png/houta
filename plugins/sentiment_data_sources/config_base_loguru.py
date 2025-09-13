#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪插件配置基类 - 纯Loguru版本
提供插件配置的标准接口和管理功能，使用纯Loguru日志系统
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union
import json
import os
from datetime import datetime


@dataclass
class PluginConfigField:
    """插件配置字段定义"""
    name: str                           # 字段名称
    display_name: str                   # 显示名称
    field_type: str                     # 字段类型：string, number, boolean, select, multiselect
    default_value: Any                  # 默认值
    description: str = ""               # 字段描述
    required: bool = True               # 是否必填
    options: List[str] = field(default_factory=list)  # 选择项（用于select类型）
    min_value: Optional[float] = None   # 最小值（用于number类型）
    max_value: Optional[float] = None   # 最大值（用于number类型）
    validation_regex: Optional[str] = None  # 验证正则表达式
    placeholder: str = ""               # 输入框占位符
    group: str = "基本设置"             # 配置分组


class ConfigurablePlugin(ABC):
    """可配置插件基类 - 纯Loguru版本"""

    def __init__(self):
        self._config = None
        self._config_file = None
        
        # 初始化插件专用日志器
        from plugins.loguru_plugin_logger import get_plugin_config_logger
        self._config_logger = get_plugin_config_logger(self.__class__.__name__)

    @abstractmethod
    def get_config_schema(self) -> List[PluginConfigField]:
        """获取配置模式定义"""
        pass

    @abstractmethod
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """验证配置"""
        pass

    def load_config(self, config_file: str = None) -> Dict[str, Any]:
        """加载配置"""
        if config_file:
            self._config_file = config_file

        # 如果没有配置文件，使用默认配置
        if not self._config_file or not os.path.exists(self._config_file):
            self._config = self.get_default_config()
            self._config_logger.config_loaded("default", list(self._config.keys()))
            return self._config

        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)

            # 合并默认配置和文件配置
            default_config = self.get_default_config()
            default_config.update(file_config)
            self._config = default_config

            # 验证配置
            is_valid, error_msg = self.validate_config(self._config)
            if not is_valid:
                self._config_logger.config_validation_error(error_msg)
                self._config = self.get_default_config()
                self._config_logger.config_reset()
            else:
                self._config_logger.config_loaded(self._config_file, list(self._config.keys()))

        except Exception as e:
            self._safe_log("warning", f"加载配置文件失败: {e}，使用默认配置")
            self._config = self.get_default_config()
            self._config_logger.config_reset()

        return self._config

    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """保存配置"""
        if config is not None:
            # 验证配置
            is_valid, error_msg = self.validate_config(config)
            if not is_valid:
                self._config_logger.config_validation_error(error_msg)
                return False
            self._config = config

        if not self._config_file:
            self._safe_log("error", "未设置配置文件路径")
            return False

        try:
            # 确保配置目录存在
            config_dir = os.path.dirname(self._config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            # 保存配置
            config_to_save = self._config.copy()
            config_to_save['_last_updated'] = datetime.now().isoformat()

            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)

            self._config_logger.config_saved(self._config_file)
            return True

        except Exception as e:
            self._safe_log("error", f"保存配置失败: {e}")
            return False

    def reset_config(self) -> bool:
        """重置为默认配置"""
        self._config = self.get_default_config()
        self._config_logger.config_reset()
        return self.save_config()

    def get_config(self, key: str = None, default: Any = None) -> Any:
        """获取配置值"""
        if self._config is None:
            self.load_config()

        if key is None:
            return self._config

        return self._config.get(key, default)

    def set_config(self, key: str, value: Any) -> bool:
        """设置配置值"""
        if self._config is None:
            self.load_config()

        old_value = self._config.get(key)
        self._config[key] = value

        # 验证更新后的配置
        is_valid, error_msg = self.validate_config(self._config)
        if not is_valid:
            self._config_logger.config_validation_error(error_msg)
            return False

        # 记录配置变更
        self._config_logger.logger.config_change(key, old_value, value)
        return True

    def is_enabled(self) -> bool:
        """检查插件是否启用"""
        return self.get_config('enabled', True)

    def set_enabled(self, enabled: bool) -> bool:
        """启用/禁用插件"""
        return self.set_config('enabled', enabled)

    def get_config_ui_schema(self) -> Dict[str, Any]:
        """获取配置UI模式"""
        schema = self.get_config_schema()

        # 按组分类字段
        groups = {}
        for field in schema:
            group_name = field.group
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append({
                'name': field.name,
                'displayName': field.display_name,
                'type': field.field_type,
                'defaultValue': field.default_value,
                'description': field.description,
                'required': field.required,
                'options': field.options,
                'minValue': field.min_value,
                'maxValue': field.max_value,
                'validationRegex': field.validation_regex,
                'placeholder': field.placeholder
            })

        return {
            'groups': groups,
            'currentConfig': self.get_config() or {}
        }

    def _safe_log(self, level: str, message: str):
        """安全的日志记录方法 - 纯Loguru实现"""
        from plugins.loguru_plugin_logger import safe_log
        plugin_name = getattr(self, '__class__').__name__
        safe_log(level, message, plugin_name=plugin_name)


def create_config_file_path(plugin_name: str) -> str:
    """创建配置文件路径"""
    config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'sentiment_plugins')
    return os.path.join(config_dir, f"{plugin_name}.json")


def validate_api_key(api_key: str, required_format: str = None) -> tuple[bool, str]:
    """验证API Key格式"""
    if not api_key or not api_key.strip():
        return False, "API Key不能为空"

    if len(api_key.strip()) < 10:
        return False, "API Key长度不能少于10个字符"

    if required_format:
        import re
        if not re.match(required_format, api_key):
            return False, f"API Key格式不符合要求: {required_format}"

    return True, "API Key格式正确"


def validate_number_range(value: Union[int, float], min_val: float = None, max_val: float = None) -> tuple[bool, str]:
    """验证数值范围"""
    try:
        num_value = float(value)

        if min_val is not None and num_value < min_val:
            return False, f"值不能小于 {min_val}"

        if max_val is not None and num_value > max_val:
            return False, f"值不能大于 {max_val}"

        return True, "数值范围正确"

    except (ValueError, TypeError):
        return False, "必须是有效的数值"