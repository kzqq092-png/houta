"""
Core Package

This package contains core functionality for the trading system.
"""

# 导入纯Loguru日志系统 - 简化版本，避免循环导入
from loguru import logger
from .loguru_config import initialize_loguru

# 向后兼容导入
# 纯Loguru架构，移除旧的日志导入
__all__ = [
    # 新的Loguru系统
    'initialize_loguru',
    # 向后兼容
    'BaseLogManager',
    'LogLevel',
    'LogManager',
    # 'get_log_manager'  # 已删除，使用纯Loguru
]
