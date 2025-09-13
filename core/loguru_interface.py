"""
纯Loguru统一接口模块
完全替代原有的logging系统，提供向后兼容的接口
"""

from loguru import logger
from typing import Any, Dict, Optional, Union
import sys
import traceback

# 从核心模块导入
from .loguru_manager import get_loguru_manager
from .loguru_performance_sink import log_performance, PerformanceTimer

class LoguruInterface:
    """Loguru统一接口 - 替代原有的LogManager"""
    
    def __init__(self):
        self.manager = get_loguru_manager()
    
    # 基本日志方法 - 完全兼容原有接口
    def info(self, message: str, **kwargs):
        """信息日志"""
        logger.bind(**kwargs).info(message)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        logger.bind(**kwargs).debug(message)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        logger.bind(**kwargs).warning(message)
    
    def warn(self, message: str, **kwargs):
        """警告日志 - 别名"""
        self.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        logger.bind(**kwargs).error(message)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        logger.bind(**kwargs).critical(message)
    
    def exception(self, message: str, **kwargs):
        """异常日志"""
        logger.bind(**kwargs).exception(message)
    
    # 性能监控方法
    def performance(self, category: str, metric_type: str, value: float, 
                   service: str = "", operation: str = "", **extra):
        """性能日志"""
        log_performance(category, metric_type, value, service, operation, **extra)
    
    # 配置管理方法
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        if self.manager.is_initialized:
            self.manager.update_config(config)
    
    def set_level(self, level: str):
        """设置日志级别"""
        self.manager.set_level(level)
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return self.manager.get_status()
    
    def clear(self):
        """清空日志"""
        self.manager.clear_logs()
    
    # 向后兼容的日志方法
    def log(self, level: str, message: str, **kwargs):
        """通用日志方法"""
        method = getattr(self, level.lower(), self.info)
        method(message, **kwargs)

# 全局接口实例
_loguru_interface = LoguruInterface()

def get_loguru_interface() -> LoguruInterface:
    """获取Loguru接口"""
    return _loguru_interface

# 兼容函数 - 替代原有的日志函数
def get_logger(name: str = None):
    """获取logger - 返回Loguru logger"""
    return logger

def info(message: str, **kwargs):
    """信息日志"""
    logger.bind(**kwargs).info(message)

def debug(message: str, **kwargs):
    """调试日志"""
    logger.bind(**kwargs).debug(message)

def warning(message: str, **kwargs):
    """警告日志"""
    logger.bind(**kwargs).warning(message)

def warn(message: str, **kwargs):
    """警告日志 - 别名"""
    warning(message, **kwargs)

def error(message: str, **kwargs):
    """错误日志"""
    logger.bind(**kwargs).error(message)

def critical(message: str, **kwargs):
    """严重错误日志"""
    logger.bind(**kwargs).critical(message)

def exception(message: str, **kwargs):
    """异常日志"""
    logger.bind(**kwargs).exception(message)

def performance(category: str, metric_type: str, value: float, 
               service: str = "", operation: str = "", **extra):
    """性能日志"""
    log_performance(category, metric_type, value, service, operation, **extra)

# 替代logging.getLogger的函数
def getLogger(name: str = None):
    """替代logging.getLogger - 返回Loguru logger"""
    return logger

# 日志级别常量 - 兼容标准logging
DEBUG = "DEBUG"
INFO = "INFO"
WARNING = "WARNING"
ERROR = "ERROR"
CRITICAL = "CRITICAL"

# 向后兼容的类
class LoggerAdapter:
    """日志适配器 - 提供标准logging接口"""
    
    def __init__(self, name: str = ""):
        self.name = name
    
    def info(self, message, *args, **kwargs):
        if args:
            message = message % args
        logger.bind(logger_name=self.name, **kwargs).info(message)
    
    def debug(self, message, *args, **kwargs):
        if args:
            message = message % args
        logger.bind(logger_name=self.name, **kwargs).debug(message)
    
    def warning(self, message, *args, **kwargs):
        if args:
            message = message % args
        logger.bind(logger_name=self.name, **kwargs).warning(message)
    
    def warn(self, message, *args, **kwargs):
        self.warning(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        if args:
            message = message % args
        logger.bind(logger_name=self.name, **kwargs).error(message)
    
    def critical(self, message, *args, **kwargs):
        if args:
            message = message % args
        logger.bind(logger_name=self.name, **kwargs).critical(message)
    
    def exception(self, message, *args, **kwargs):
        if args:
            message = message % args
        logger.bind(logger_name=self.name, **kwargs).exception(message)
    
    def log(self, level, message, *args, **kwargs):
        if args:
            message = message % args
        method_name = level.lower() if isinstance(level, str) else {
            10: 'debug', 20: 'info', 30: 'warning', 40: 'error', 50: 'critical'
        }.get(level, 'info')
        method = getattr(self, method_name, self.info)
        method(message, **kwargs)

def create_logger_adapter(name: str) -> LoggerAdapter:
    """创建日志适配器"""
    return LoggerAdapter(name)

# 打印替换函数
def print_to_logger(*args, sep=' ', end='\n', file=None, flush=False, **logger_kwargs):
    """替代print函数，输出到logger"""
    message = sep.join(str(arg) for arg in args) + end.rstrip('\n')
    
    # 获取调用者信息
    frame = sys._getframe(1)
    caller_name = frame.f_globals.get('__name__', 'unknown')
    caller_function = frame.f_code.co_name
    caller_line = frame.f_lineno
    
    logger.bind(
        caller_name=caller_name,
        caller_function=caller_function,
        caller_line=caller_line,
        print_replacement=True,
        **logger_kwargs
    ).info(message)

# 异常处理工具
def log_exception(exc: Exception, message: str = "未处理的异常", **kwargs):
    """记录异常"""
    logger.bind(**kwargs).exception(f"{message}: {exc}")

def log_traceback(message: str = "异常追踪", **kwargs):
    """记录当前异常追踪"""
    logger.bind(**kwargs).error(f"{message}:\n{traceback.format_exc()}")

# 上下文管理器
class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, **context):
        self.context = context
        self.bound_logger = logger.bind(**context)
    
    def __enter__(self):
        return self.bound_logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.bound_logger.exception(f"上下文异常: {exc_val}")
        return False

def log_context(**context):
    """创建日志上下文"""
    return LogContext(**context)