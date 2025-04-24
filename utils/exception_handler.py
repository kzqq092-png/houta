"""
异常处理模块

提供统一的异常处理和日志记录功能
"""

import traceback
import sys
from typing import Optional, Dict, Any
from core import LogManager, LogLevel

class ExceptionHandler:
    """异常处理器"""
    
    def __init__(self, log_manager: Optional[LogManager] = None):
        """初始化异常处理器
        
        Args:
            log_manager: 日志管理器实例
        """
        self.log_manager = log_manager or LogManager()
        
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        # Format exception info
        error_msg = f"Uncaught exception: {exc_type.__name__}: {exc_value}"
        traceback_info = ''.join(traceback.format_tb(exc_traceback))
        
        # Log error
        self.log_manager.error(error_msg)
        self.log_manager.error(traceback_info)
        
        # Print to stderr
        print(error_msg, file=sys.stderr)
        print(traceback_info, file=sys.stderr)
        
    def handle_gui_exception(self, exc_type, exc_value, exc_traceback):
        """Handle GUI-related exceptions
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        # Format exception info
        error_msg = f"GUI exception: {exc_type.__name__}: {exc_value}"
        traceback_info = ''.join(traceback.format_tb(exc_traceback))
        
        # Log error
        self.log_manager.error(error_msg)
        self.log_manager.error(traceback_info)
        
        # Print to stderr
        print(error_msg, file=sys.stderr)
        print(traceback_info, file=sys.stderr)
        
    def handle_data_exception(self, exc_type, exc_value, exc_traceback):
        """Handle data-related exceptions
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        # Format exception info
        error_msg = f"Data exception: {exc_type.__name__}: {exc_value}"
        traceback_info = ''.join(traceback.format_tb(exc_traceback))
        
        # Log error
        self.log_manager.error(error_msg)
        self.log_manager.error(traceback_info)
        
        # Print to stderr
        print(error_msg, file=sys.stderr)
        print(traceback_info, file=sys.stderr)
        
    def handle_trading_exception(self, exc_type, exc_value, exc_traceback):
        """Handle trading-related exceptions
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        # Format exception info
        error_msg = f"Trading exception: {exc_type.__name__}: {exc_value}"
        traceback_info = ''.join(traceback.format_tb(exc_traceback))
        
        # Log error
        self.log_manager.error(error_msg)
        self.log_manager.error(traceback_info)
        
        # Print to stderr
        print(error_msg, file=sys.stderr)
        print(traceback_info, file=sys.stderr)
        
    def get_exception_info(self, exc_type, exc_value, exc_traceback) -> Dict[str, Any]:
        """Get formatted exception information
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
            
        Returns:
            Dictionary containing exception information
        """
        return {
            'type': exc_type.__name__,
            'message': str(exc_value),
            'traceback': ''.join(traceback.format_tb(exc_traceback))
        } 