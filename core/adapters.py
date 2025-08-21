#!/usr/bin/env python3
"""
系统组件适配器

提供统一的接口来访问系统的各种组件
"""

from core.performance import get_performance_monitor
import logging
from typing import Dict, Any, Optional
from .logger import LogManager
from .config import ConfigManager
from .data_validator import ProfessionalDataValidator, ValidationLevel
# from .performance_monitor import get_performance_monitor  # 已迁移到统一模块
from utils import ConfigManager as UtilsConfigManager

# 全局实例
_log_manager = None
_config_manager = None
_data_validator = None


def get_logger(name: str = None) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    global _log_manager

    if _log_manager is None:
        try:
            from utils.config_types import LoggingConfig
            _log_manager = LogManager(LoggingConfig())
        except Exception:
            # 如果初始化失败，使用标准日志记录器
            return logging.getLogger(name or __name__)

    # 返回标准的日志记录器，但确保日志管理器已初始化
    return logging.getLogger(name or __name__)


def get_config() -> Dict[str, Any]:
    """
    获取配置管理器

    Returns:
        配置字典
    """
    global _config_manager

    if _config_manager is None:
        try:
            _config_manager = UtilsConfigManager()
        except Exception as e:
            logging.warning(f"配置管理器初始化失败: {e}")
            # 返回默认配置
            return {
                'strategy_database': {
                    'path': 'data/strategies.db'
                },
                'strategy_engine': {
                    'max_workers': 4,
                    'cache_size': 1000,
                    'cache_ttl': 3600
                },
                'strategy_system': {
                    'database': {
                        'path': 'data/strategies.db'
                    },
                    'engine': {
                        'max_workers': 4,
                        'cache_size': 1000,
                        'cache_ttl': 3600
                    },
                    'discovery': {
                        'auto_discover': True,
                        'paths': ['strategies']
                    }
                },
                'strategy_discovery': {
                    'paths': ['strategies']
                }
            }

    try:
        return _config_manager.get_all()
    except Exception as e:
        logging.warning(f"获取配置失败: {e}")
        return {}


class DataValidator:
    """数据验证器适配器"""

    def __init__(self):
        self._validator = ProfessionalDataValidator(
            validation_level=ValidationLevel.STANDARD)

    def validate_strategy_data(self, strategy_data: Dict[str, Any]) -> bool:
        """
        验证策略数据

        Args:
            strategy_data: 策略数据字典

        Returns:
            是否有效
        """
        try:
            # 检查必需字段
            required_fields = ['name']
            for field in required_fields:
                if field not in strategy_data:
                    return False

            # 检查数据类型
            if not isinstance(strategy_data.get('name'), str):
                return False

            # 检查可选字段的类型
            if 'version' in strategy_data and not isinstance(strategy_data['version'], str):
                return False

            if 'author' in strategy_data and not isinstance(strategy_data['author'], str):
                return False

            if 'description' in strategy_data and not isinstance(strategy_data['description'], str):
                return False

            if 'category' in strategy_data and not isinstance(strategy_data['category'], str):
                return False

            if 'metadata' in strategy_data and not isinstance(strategy_data['metadata'], dict):
                return False

            return True

        except Exception:
            return False


def get_data_validator() -> DataValidator:
    """
    获取数据验证器

    Returns:
        数据验证器实例
    """
    global _data_validator

    if _data_validator is None:
        _data_validator = DataValidator()

    return _data_validator


# 重新导出性能监控器（使用统一模块）

__all__ = [
    'get_logger',
    'get_config',
    'get_data_validator',
    'get_performance_monitor'
]
