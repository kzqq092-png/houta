"""
简化的Loguru管理器 - 避免循环导入
"""

from loguru import logger
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

class SimpleLoguruManager:
    """简化的Loguru管理器 - 无外部依赖"""
    
    def __init__(self):
        self.is_initialized = False
        self.sink_handlers = {}
        
    def initialize(self, config: Optional[Dict[str, Any]] = None):
        """初始化Loguru管理器"""
        if self.is_initialized:
            return
        
        # 移除默认处理器
        logger.remove()
        
        # 设置控制台输出
        console_handler = logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
            enqueue=True,
            backtrace=True,
            diagnose=True
        )
        self.sink_handlers["console"] = console_handler
        
        # 确保日志目录存在
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 设置文件输出
        file_handler = logger.add(
            "logs/factorweave_{time:YYYY-MM-DD}.log",
            level="DEBUG", 
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {extra} - {message}",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=True
        )
        self.sink_handlers["file"] = file_handler
        
        # 设置错误文件输出
        error_handler = logger.add(
            "logs/errors_{time:YYYY-MM-DD}.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {extra} - {message} | {exception}",
            rotation="50 MB", 
            retention="90 days",
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=True
        )
        self.sink_handlers["error"] = error_handler
        
        self.is_initialized = True
        logger.info(" 简化Loguru管理器初始化完成")
    
    def shutdown(self):
        """关闭管理器"""
        for handler_id in self.sink_handlers.values():
            try:
                logger.remove(handler_id)
            except ValueError:
                pass
        self.sink_handlers.clear()
        self.is_initialized = False

# 全局简化管理器实例
_simple_manager = SimpleLoguruManager()

def get_simple_loguru_manager():
    """获取简化的Loguru管理器"""
    return _simple_manager

def initialize_simple_logging():
    """初始化简化的日志系统"""
    _simple_manager.initialize()
    return _simple_manager