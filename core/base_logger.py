"""
基础日志管理模块

提供基本的日志记录功能，避免循环导入
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BaseLogManager(QObject):
    """基础日志管理器"""

    # 定义信号
    log_message = pyqtSignal(str, str)  # message, level
    log_cleared = pyqtSignal()
    performance_alert = pyqtSignal(str)
    exception_occurred = pyqtSignal(Exception)

    def __init__(self):
        """初始化基础日志管理器"""
        super().__init__()

        # 创建日志目录
        os.makedirs('logs', exist_ok=True)

        # 配置基本日志记录器
        self.logger = logging.getLogger("TradingSystem")
        self.logger.setLevel(logging.INFO)

        # 只添加一次控制台处理器，避免重复日志
        if not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
            self.logger.addHandler(console_handler)

    def debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(message)
        self.log_message.emit(message, LogLevel.DEBUG.value)

    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
        self.log_message.emit(message, LogLevel.INFO.value)

    def warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)
        self.log_message.emit(message, LogLevel.WARNING.value)

    def error(self, message: str):
        """记录错误日志"""
        self.logger.error(message)
        self.log_message.emit(message, LogLevel.ERROR.value)

    def critical(self, message: str):
        """记录严重错误日志"""
        self.logger.critical(message)
        self.log_message.emit(message, LogLevel.CRITICAL.value)

    def clear(self):
        """清除日志"""
        try:
            for handler in self.logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    if os.path.exists(handler.baseFilename):
                        open(handler.baseFilename, 'w').close()
            self.log_cleared.emit()
        except Exception as e:
            self.logger(f"清除日志失败: {str(e)}")

    def handle_exception(self, e: Exception):
        """处理异常"""
        try:
            error_msg = f"异常: {str(e)}\n堆栈跟踪:\n{traceback.format_exc()}"
            self.error(error_msg)
            self.exception_occurred.emit(e)
        except Exception as ex:
            self.logger(f"处理异常失败: {str(ex)}")

    def performance(self, message: str):
        """记录性能日志"""
        self.logger.info(f"[PERFORMANCE] {message}")
        self.log_message.emit(message, "PERFORMANCE")
