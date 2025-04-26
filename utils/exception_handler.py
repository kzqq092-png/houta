"""
异常处理模块

提供全局异常处理功能
"""

import os
import sys
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from PyQt5.QtCore import QObject, pyqtSignal

class ExceptionHandler(QObject):
    """异常处理器"""
    
    # 定义信号
    exception_occurred = pyqtSignal(Exception, str, str)  # 异常对象, 错误类型, 错误消息
    
    def __init__(self):
        """初始化异常处理器"""
        super().__init__()
        self._logger = None
        self._handlers = {}
        
    def set_logger(self, logger):
        """设置日志记录器
        
        Args:
            logger: 日志记录器对象
        """
        self._logger = logger
        
    def register_handler(self, error_type: type, handler: Callable):
        """注册异常处理函数
        
        Args:
            error_type: 异常类型
            handler: 处理函数
        """
        self._handlers[error_type] = handler
        
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """处理未捕获的异常
        
        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_traceback: 异常堆栈
        """
        try:
            # 获取错误信息
            error_msg = str(exc_value)
            error_type = exc_type.__name__
            trace_info = ''.join(traceback.format_tb(exc_traceback))
            
            # 记录错误日志
            if self._logger:
                self._logger.error(f"未捕获的异常: {error_type}: {error_msg}\n{trace_info}")
            
            # 发送异常信号
            self.exception_occurred.emit(exc_value, error_type, error_msg)
            
            # 调用对应的处理函数
            if exc_type in self._handlers:
                self._handlers[exc_type](exc_value)
                
        except Exception as e:
            # 如果处理异常的过程中出现错误，至少打印到控制台
            print(f"处理异常时出错: {str(e)}")
            print(f"原始异常: {error_type}: {error_msg}")
            print(trace_info)
            
    def log_exception(self, e: Exception, context: str = ""):
        """记录异常
        
        Args:
            e: 异常对象
            context: 上下文信息
        """
        try:
            error_msg = f"{context}\n异常: {str(e)}\n堆栈跟踪:\n{traceback.format_exc()}"
            if self._logger:
                self._logger.error(error_msg)
            self.exception_occurred.emit(e, e.__class__.__name__, str(e))
        except Exception as ex:
            print(f"记录异常失败: {str(ex)}")
            print(f"原始异常: {str(e)}")
            
    def install(self):
        """安装全局异常处理器"""
        sys.excepthook = self.handle_exception 