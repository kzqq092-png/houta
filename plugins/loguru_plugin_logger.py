"""
插件系统纯Loguru日志适配器
完全替代原有的三层安全日志机制，使用纯Loguru接口
"""

from loguru import logger
from typing import Optional, Any, Dict
import traceback
import sys
from contextlib import contextmanager
from functools import wraps


class PluginLoggerAdapter:
    """插件专用Loguru适配器 - 替代原有的_safe_log机制"""

    def __init__(self, plugin_name: str = "unknown_plugin", plugin_version: str = "1.0.0"):
        self.plugin_name = plugin_name
        self.plugin_version = plugin_version

        # 为插件创建专用的logger bind
        self.plugin_logger = logger.bind(
            plugin=True,
            plugin_name=plugin_name,
            plugin_version=plugin_version
        )

    def info(self, message: str, **extra):
        """信息日志"""
        self.plugin_logger.bind(**extra).info(f"[{self.plugin_name}] {message}")

    def debug(self, message: str, **extra):
        """调试日志"""
        self.plugin_logger.bind(**extra).debug(f"[{self.plugin_name}] {message}")

    def warning(self, message: str, **extra):
        """警告日志"""
        self.plugin_logger.bind(**extra).warning(f"[{self.plugin_name}] {message}")

    def error(self, message: str, error: Optional[Exception] = None, **extra):
        """错误日志"""
        if error:
            self.plugin_logger.bind(**extra).error(f"[{self.plugin_name}] {message}: {error}")
        else:
            self.plugin_logger.bind(**extra).error(f"[{self.plugin_name}] {message}")

    def critical(self, message: str, error: Optional[Exception] = None, **extra):
        """严重错误日志"""
        if error:
            self.plugin_logger.bind(**extra).critical(f"[{self.plugin_name}] {message}: {error}")
        else:
            self.plugin_logger.bind(**extra).critical(f"[{self.plugin_name}] {message}")

    def exception(self, message: str, **extra):
        """异常日志 - 自动捕获异常信息"""
        self.plugin_logger.bind(**extra).exception(f"[{self.plugin_name}] {message}")

    def performance(self, operation: str, duration_ms: float, **extra):
        """性能日志"""
        from core.loguru_performance_sink import log_performance
        log_performance(
            category="PLUGIN",
            metric_type="EXECUTION_TIME",
            value=duration_ms,
            service=self.plugin_name,
            operation=operation,
            **extra
        )

    def config_change(self, config_key: str, old_value: Any, new_value: Any):
        """配置变更日志"""
        self.plugin_logger.bind(
            config_change=True,
            config_key=config_key,
            old_value=str(old_value),
            new_value=str(new_value)
        ).info(f"[{self.plugin_name}] 配置更新: {config_key} = {new_value}")

    def data_operation(self, operation: str, record_count: int = 0, **extra):
        """数据操作日志"""
        self.plugin_logger.bind(
            data_operation=True,
            operation=operation,
            record_count=record_count,
            **extra
        ).info(f"[{self.plugin_name}] 数据操作: {operation}, 记录数: {record_count}")


class SafePluginLogger:
    """安全插件日志器 - 完全基于Loguru，移除三层安全机制"""

    def __init__(self, plugin_name: str, plugin_version: str = "1.0.0"):
        self.adapter = PluginLoggerAdapter(plugin_name, plugin_version)
        self.plugin_name = plugin_name

    def safe_log(self, level: str, message: str, error: Optional[Exception] = None, **extra):
        """安全日志记录 - 纯Loguru实现，移除print fallback"""
        try:
            # 直接使用Loguru，移除三层安全机制
            method = getattr(self.adapter, level.lower(), self.adapter.info)

            if error and level.lower() in ['error', 'critical']:
                method(message, error=error, **extra)
            else:
                method(message, **extra)

        except Exception as log_error:
            # 只在Loguru完全失败时才使用最后备用方案
            try:
                # 尝试使用基本的Loguru记录
                logger.error("[{}] 日志记录失败: {}, 原始消息: {}", self.plugin_name, str(log_error), str(message))
            except Exception:
                # 极端情况下的最后备用方案
                logger.info("[CRITICAL][{}] 完全日志失败: {}", self.plugin_name, str(message))

    def __getattr__(self, name):
        """代理到适配器"""
        return getattr(self.adapter, name)


@contextmanager
def plugin_logging_context(plugin_name: str, operation: str):
    """插件日志上下文管理器"""
    safe_logger = SafePluginLogger(plugin_name)
    start_time = logger._get_time()

    safe_logger.debug(f"开始操作: {operation}")

    try:
        yield safe_logger

        # 计算执行时间
        duration = (logger._get_time() - start_time) * 1000
        safe_logger.performance(operation, duration)
        safe_logger.debug(f"完成操作: {operation}, 耗时: {duration:.2f}ms")

    except Exception as e:
        duration = (logger._get_time() - start_time) * 1000
        safe_logger.error(f"操作失败: {operation}", error=e)
        safe_logger.performance(f"{operation}_error", duration, error=str(e))
        raise


def plugin_method_logger(plugin_name: str):
    """插件方法日志装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            safe_logger = SafePluginLogger(plugin_name)
            operation = f"{func.__name__}"

            with plugin_logging_context(plugin_name, operation) as logger_ctx:
                return func(*args, **kwargs)

        return wrapper
    return decorator


class PluginConfigLogger:
    """插件配置专用日志器"""

    def __init__(self, plugin_name: str = "unknown_plugin"):
        self.logger = SafePluginLogger(plugin_name)

    def config_loaded(self, config_file: str, config_keys: list):
        """配置加载日志"""
        self.logger.info(f"配置已加载: {config_file}, 包含键: {config_keys}")

    def config_saved(self, config_file: str):
        """配置保存日志"""
        self.logger.info(f"配置已保存: {config_file}")

    def config_validation_error(self, error_message: str):
        """配置验证错误"""
        self.logger.error(f"配置验证失败: {error_message}")

    def config_migration(self, from_version: str, to_version: str):
        """配置迁移日志"""
        self.logger.info(f"配置已迁移: {from_version} -> {to_version}")

    def config_reset(self):
        """配置重置日志"""
        self.logger.warning("配置已重置为默认值")

# 便捷函数


def get_plugin_logger(plugin_name: str, plugin_version: str = "1.0.0") -> SafePluginLogger:
    """获取插件专用日志器"""
    return SafePluginLogger(plugin_name, plugin_version)


def get_plugin_config_logger(plugin_name: str) -> PluginConfigLogger:
    """获取插件配置专用日志器"""
    return PluginConfigLogger(plugin_name)

# 向后兼容的safe_log函数


def safe_log(level: str, message: str, plugin_name: str = "Unknown", error: Optional[Exception] = None):
    """向后兼容的safe_log函数 - 现在基于纯Loguru"""
    safe_logger = SafePluginLogger(plugin_name)
    safe_logger.safe_log(level, message, error=error)
