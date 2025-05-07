"""
日志管理模块

提供日志记录和管理功能
"""

import logging.handlers
import os
from typing import Optional
from PyQt5.QtCore import pyqtSignal
from utils.config_types import LoggingConfig
from .base_logger import BaseLogManager, LogLevel


class LogManager(BaseLogManager):
    """日志管理器"""

    # 定义额外的信号
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

        # 配置日志记录器
        self._setup_logger()

        # 设置异步日志
        if self.config.async_logging:
            from concurrent.futures import ThreadPoolExecutor
            self.log_queue = []
            self.executor = ThreadPoolExecutor(
                max_workers=self.config.worker_threads)

    def _setup_logger(self):
        """设置日志记录器"""
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
            console_handler = logging.StreamHandler()
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
        self.info("日志配置已更新")
