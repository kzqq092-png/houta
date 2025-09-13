"""
向后兼容的base_logger模块
重定向到新的Loguru系统
"""

from loguru import logger
from PyQt5.QtCore import QObject, pyqtSignal
from enum import Enum

class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class BaseLogManager(QObject):
    """向后兼容的BaseLogManager类"""
    
    log_message = pyqtSignal(str, str, str)  # message, level, timestamp
    
    def __init__(self):
        super().__init__()
    
    def info(self, message, **kwargs):
        logger.bind(**kwargs).info(message)
        self.log_message.emit(message, "INFO", "")
    
    def debug(self, message, **kwargs):
        logger.bind(**kwargs).debug(message)
        self.log_message.emit(message, "DEBUG", "")
    
    def warning(self, message, **kwargs):
        logger.bind(**kwargs).warning(message)
        self.log_message.emit(message, "WARNING", "")
    
    def error(self, message, **kwargs):
        logger.bind(**kwargs).error(message)
        self.log_message.emit(message, "ERROR", "")
    
    def critical(self, message, **kwargs):
        logger.bind(**kwargs).critical(message)
        self.log_message.emit(message, "CRITICAL", "")
    
    def exception(self, message, **kwargs):
        logger.bind(**kwargs).exception(message)
        self.log_message.emit(message, "ERROR", "")