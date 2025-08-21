"""
日志管理模块

提供日志记录和管理功能
"""

import logging
import logging.handlers
import os
from typing import Optional
from PyQt5.QtCore import pyqtSignal
from utils.config_types import LoggingConfig
from .base_logger import BaseLogManager, LogLevel
import inspect
from utils.trace_context import TraceIdFilter


class LogManager(BaseLogManager):
    """日志管理器"""

    # 定义额外的信号
    config_changed = pyqtSignal(LoggingConfig)  # 配置变更信号

    def __init__(self, config: Optional[LoggingConfig] = None):
        """初始化日志管理器

        Args:
            config: 日志配置对象
        """
        try:
            super().__init__()
            self.config = config or LoggingConfig()
            is_valid, error_msg = self.config.validate()
            if not is_valid:
                print(f"日志配置无效: {error_msg}")
            self._setup_logger()
            if self.config.async_logging:
                from concurrent.futures import ThreadPoolExecutor
                self.log_queue = []
                self.executor = ThreadPoolExecutor(
                    max_workers=self.config.worker_threads)
        except Exception as e:
            print(f"LogManager初始化异常: {e}")

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
                backupCount=self.config.backup_count,
                encoding='utf-8'  # 强制UTF-8编码
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
                    backupCount=self.config.backup_count,
                    encoding='utf-8'
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
                    backupCount=self.config.backup_count,
                    encoding='utf-8'
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

        # 添加TraceIdFilter到所有处理器
        for handler in self.logger.handlers:
            handler.addFilter(TraceIdFilter())
            # 使用带有trace_id的格式
            formatter = logging.Formatter(
                '[%(asctime)s][%(levelname)s][%(trace_id)s] %(name)s: %(message)s')
            handler.setFormatter(formatter)

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

    def log(self, message: str, level: 'LogLevel | str' = LogLevel.INFO, trace_id: str = None, request_id: str = None):
        """记录日志，支持trace_id和request_id

        Args:
            message: 日志消息
            level: 日志级别（可为LogLevel或字符串）
            trace_id: 调用链ID
            request_id: 请求ID
        """
        # 兼容字符串类型
        if isinstance(level, str):
            try:
                level = LogLevel[level.upper()]
            except Exception:
                level = LogLevel.INFO
        # 拼接trace_id/request_id
        if trace_id or request_id:
            message = f"[trace_id={trace_id or ''}][request_id={request_id or ''}] {message}"

        # 检查配置是否存在且有效
        if (self.config and
            hasattr(self.config, 'async_logging') and
            hasattr(self.config, '__dict__') and  # 确保是对象而不是字符串
                self.config.async_logging):
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

    def performance(self, message: str):
        """记录耗时性能日志"""
        self.logger.info(f"[PERFORMANCE] {message}")
        self.log_message.emit(message, "PERFORMANCE")

    def get_last_trace_log(self, trace_id: str) -> str:
        """
        获取指定trace_id的最近一次调用链日志内容（从日志文件中检索）
        """
        log_file = os.path.join('logs', self.config.log_file)
        if not os.path.exists(log_file):
            return "日志文件不存在"
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        trace_logs = [line for line in lines if f"trace_id={trace_id}" in line]
        return ''.join(trace_logs[-20:]) if trace_logs else "未找到trace_id相关日志"


def get_logger(name: str = None) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称，默认为调用模块名

    Returns:
        logging.Logger: 日志记录器实例
    """
    if name is None:
        # 获取调用模块的名称
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')

    return logging.getLogger(name)
