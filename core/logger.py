"""
日志管理模块

提供日志记录和管理功能
"""

import logging
import os
from datetime import datetime
from enum import Enum, auto
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal
from utils import LoggingConfig

class LogLevel(Enum):
    """日志级别"""
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()

class LogManager(QObject):
    """日志管理器"""
    
    # 定义信号
    log_added = pyqtSignal(str, str)  # 日志消息, 级别
    log_cleared = pyqtSignal()
    performance_alert = pyqtSignal(str)
    exception_occurred = pyqtSignal(Exception)
    
    def __init__(self, config: Optional[LoggingConfig] = None):
        """初始化日志管理器
        
        Args:
            config: 日志配置对象
        """
        super().__init__()
        
        # 使用默认配置
        self.config = config or LoggingConfig()
        
        # 创建日志目录
        os.makedirs('logs', exist_ok=True)
        
        # 配置日志记录器
        self.logger = logging.getLogger('TradingSystem')
        self.logger.setLevel(logging.DEBUG)
        
        # 添加文件处理器
        if self.config.save_to_file:
            file_handler = logging.FileHandler(
                f'logs/{self.config.log_file}',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
        # 添加控制台处理器
        if self.config.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
    def log(self, message: str, level: str = "INFO"):
        """记录日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        try:
            # 转换日志级别
            level = level.upper()
            if level == "DEBUG":
                self.logger.debug(message)
            elif level == "INFO":
                self.logger.info(message)
            elif level == "WARNING":
                self.logger.warning(message)
            elif level == "ERROR":
                self.logger.error(message)
            else:
                self.logger.info(message)
                
            # 发送日志添加信号
            self.log_added.emit(message, level)
            
        except Exception as e:
            print(f"记录日志失败: {str(e)}")
            
    def clear(self):
        """清除日志"""
        try:
            # 清除日志文件
            if self.config.save_to_file:
                open(f'logs/{self.config.log_file}', 'w').close()
                
            # 发送日志清除信号
            self.log_cleared.emit()
            
        except Exception as e:
            print(f"清除日志失败: {str(e)}")
            
    def alert_performance(self, message: str):
        """发送性能警告
        
        Args:
            message: 警告消息
        """
        try:
            self.log(message, "WARNING")
            self.performance_alert.emit(message)
        except Exception as e:
            print(f"发送性能警告失败: {str(e)}")
            
    def handle_exception(self, e: Exception):
        """处理异常
        
        Args:
            e: 异常对象
        """
        try:
            self.log(str(e), "ERROR")
            self.exception_occurred.emit(e)
        except Exception as ex:
            print(f"处理异常失败: {str(ex)}")