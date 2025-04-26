"""
日志管理模块

提供日志记录和管理功能
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal
from utils.config_types import LoggingConfig

class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogManager(QObject):
    """日志管理器"""
    
    # 定义信号
    log_message = pyqtSignal(str, str)  # message, level
    log_cleared = pyqtSignal()
    performance_alert = pyqtSignal(str)
    exception_occurred = pyqtSignal(Exception)
    config_changed = pyqtSignal(LoggingConfig)  # 配置变更信号
    
    def __init__(self, config: Optional[LoggingConfig] = None):
        """初始化日志管理器
        
        Args:
            config: 日志配置对象
        """
        super().__init__()
        
        # 使用默认配置
        self.config = config or LoggingConfig()
        
        # 验证配置
        is_valid, error_msg = self.config.validate()
        if not is_valid:
            raise ValueError(f"日志配置无效: {error_msg}")
        
        # 创建日志目录
        os.makedirs('logs', exist_ok=True)
        
        # 配置日志记录器
        self._setup_logger()
        
        # 设置异步日志
        if self.config.async_logging:
            from concurrent.futures import ThreadPoolExecutor
            self.log_queue = []
            self.executor = ThreadPoolExecutor(max_workers=self.config.worker_threads)
            
    def _setup_logger(self):
        """设置日志记录器"""
        self.logger = logging.getLogger('TradingSystem')
        self.logger.setLevel(getattr(logging, self.config.level))
        
        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            
        # 添加文件处理器
        if self.config.save_to_file:
            file_handler = logging.handlers.RotatingFileHandler(
                os.path.join('logs', self.config.log_file),
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count
            )
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
            self.logger.addHandler(file_handler)
            
            # 性能日志处理器
            if self.config.performance_log:
                perf_handler = logging.handlers.RotatingFileHandler(
                    os.path.join('logs', self.config.performance_log_file),
                    maxBytes=self.config.max_bytes,
                    backupCount=self.config.backup_count
                )
                perf_handler.setFormatter(logging.Formatter(
                    "%(asctime)s - PERFORMANCE - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                ))
                self.logger.addHandler(perf_handler)
                
            # 异常日志处理器
            if self.config.exception_log:
                exc_handler = logging.handlers.RotatingFileHandler(
                    os.path.join('logs', self.config.exception_log_file),
                    maxBytes=self.config.max_bytes,
                    backupCount=self.config.backup_count
                )
                exc_handler.setFormatter(logging.Formatter(
                    "%(asctime)s - EXCEPTION - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                ))
                self.logger.addHandler(exc_handler)
            
        # 添加控制台处理器
        if self.config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
            self.logger.addHandler(console_handler)
            
    def _async_log(self, message: str, level: LogLevel):
        """异步记录日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        if len(self.log_queue) >= self.config.log_queue_size:
            self.log_queue.pop(0)  # 移除最旧的日志
        self.log_queue.append((message, level))
        self.executor.submit(self._write_log, message, level)
            
    def _write_log(self, message: str, level: LogLevel):
        """写入日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        try:
            # 发送信号
            self.log_message.emit(message, level.value)
            
            # 记录到文件
            if level == LogLevel.DEBUG:
                self.logger.debug(message)
            elif level == LogLevel.INFO:
                self.logger.info(message)
            elif level == LogLevel.WARNING:
                self.logger.warning(message)
            elif level == LogLevel.ERROR:
                self.logger.error(message)
            elif level == LogLevel.CRITICAL:
                self.logger.critical(message)
                
        except Exception as e:
            print(f"日志记录错误: {str(e)}")
            
    def log(self, message: str, level: LogLevel = LogLevel.INFO):
        """记录日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        if self.config.async_logging:
            self._async_log(message, level)
        else:
            self._write_log(message, level)
            
    def debug(self, message: str):
        """记录调试日志
        
        Args:
            message: 调试消息
        """
        self.log(message, LogLevel.DEBUG)
            
    def info(self, message: str):
        """记录信息日志
        
        Args:
            message: 信息消息
        """
        self.log(message, LogLevel.INFO)
            
    def warning(self, message: str):
        """记录警告日志
        
        Args:
            message: 警告消息
        """
        self.log(message, LogLevel.WARNING)
            
    def error(self, message: str):
        """记录错误日志
        
        Args:
            message: 错误消息
        """
        self.log(message, LogLevel.ERROR)
            
    def clear(self):
        """清除日志"""
        try:
            # 清除主日志文件
            if self.config.save_to_file:
                log_path = os.path.join('logs', self.config.log_file)
                if os.path.exists(log_path):
                    open(log_path, 'w').close()
                    
                # 清除性能日志
                if self.config.performance_log:
                    perf_path = os.path.join('logs', self.config.performance_log_file)
                    if os.path.exists(perf_path):
                        open(perf_path, 'w').close()
                        
                # 清除异常日志
                if self.config.exception_log:
                    exc_path = os.path.join('logs', self.config.exception_log_file)
                    if os.path.exists(exc_path):
                        open(exc_path, 'w').close()
                
            # 清除日志队列
            if self.config.async_logging:
                self.log_queue.clear()
                
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
            self.log(f"[Performance] {message}", LogLevel.WARNING)
            self.performance_alert.emit(message)
        except Exception as e:
            print(f"发送性能警告失败: {str(e)}")
            
    def handle_exception(self, e: Exception):
        """处理异常
        
        Args:
            e: 异常对象
        """
        try:
            error_msg = f"异常: {str(e)}\n堆栈跟踪:\n{traceback.format_exc()}"
            self.log(error_msg, LogLevel.ERROR)
            self.exception_occurred.emit(e)
        except Exception as ex:
            print(f"处理异常失败: {str(ex)}")

    def get_log_content(self) -> str:
        """获取日志内容
        
        Returns:
            str: 日志内容
        """
        try:
            log_path = os.path.join('logs', self.config.log_file)
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return ""
        except Exception as e:
            self.log(f"获取日志内容失败: {str(e)}", LogLevel.ERROR)
            return ""
            
    def log_exception(self, exception: Exception, context: str = ""):
        """记录异常
        
        Args:
            exception: 异常对象
            context: 上下文信息
        """
        try:
            error_msg = f"{context}\n异常: {str(exception)}\n堆栈跟踪:\n{traceback.format_exc()}"
            self.log(error_msg, LogLevel.ERROR)
            self.exception_occurred.emit(exception)
        except Exception as e:
            print(f"记录异常失败: {str(e)}")
            
    def update_config(self, new_config: LoggingConfig):
        """更新日志配置
        
        Args:
            new_config: 新的日志配置
        """
        # 验证新配置
        is_valid, error_msg = new_config.validate()
        if not is_valid:
            raise ValueError(f"日志配置无效: {error_msg}")
            
        # 更新配置
        self.config = new_config
        
        # 重新设置日志记录器
        self._setup_logger()
        
        # 发送配置变更信号
        self.config_changed.emit(new_config)
        
        # 记录配置变更
        self.info(f"日志配置已更新: {new_config.to_dict()}")
            
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)