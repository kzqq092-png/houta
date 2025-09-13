"""
纯Loguru统一管理器
完全替代原有的LogManager和BaseLogManager
"""

from loguru import logger
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from .loguru_performance_sink import get_performance_sink, LoguruPerformanceSink
from gui.loguru_qt_handler import get_qt_handler, LoguruQtHandler

class LoguruManager:
    """Loguru统一管理器 - 纯净无兼容层实现"""
    
    def __init__(self):
        self.is_initialized = False
        self.sink_handlers = {}
        self.config = self._get_default_config()
        self.qt_handler: Optional[LoguruQtHandler] = None
        self.performance_sink: Optional[LoguruPerformanceSink] = None
        
        # 初始化时移除默认处理器
        logger.remove()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "level": "INFO",
            "console": {
                "enabled": True,
                "level": "INFO",
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                "colorize": True
            },
            "file": {
                "enabled": True,
                "level": "DEBUG",
                "path": "logs/factorweave_{time:YYYY-MM-DD}.log",
                "rotation": "100 MB",
                "retention": "30 days",
                "compression": "zip",
                "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {extra} - {message}",
                "encoding": "utf-8"
            },
            "error": {
                "enabled": True,
                "level": "ERROR",
                "path": "logs/errors_{time:YYYY-MM-DD}.log",
                "rotation": "50 MB",
                "retention": "90 days",
                "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {extra} - {message} | {exception}",
                "encoding": "utf-8"
            },
            "performance": {
                "enabled": True,
                "level": "DEBUG",
                "path": "logs/performance_{time:YYYY-MM-DD}.log",
                "rotation": "200 MB",
                "retention": "7 days",
                "format": "{message}",  # 性能日志使用JSON格式
                "encoding": "utf-8"
            },
            "async": {
                "enabled": True,
                "enqueue": True
            },
            "backtrace": True,
            "diagnose": True
        }
    
    def initialize(self, config: Optional[Dict[str, Any]] = None):
        """初始化Loguru管理器"""
        if self.is_initialized:
            logger.warning("LoguruManager 已经初始化，跳过重复初始化")
            return
        
        if config:
            self.config.update(config)
        
        # 确保日志目录存在
        self._ensure_log_directories()
        
        # 设置控制台输出
        self._setup_console_handler()
        
        # 设置文件输出
        self._setup_file_handlers()
        
        # 设置Qt UI集成
        self._setup_qt_integration()
        
        # 设置性能监控
        self._setup_performance_monitoring()
        
        # 设置全局异常处理
        self._setup_exception_handling()
        
        self.is_initialized = True
        logger.info("LoguruManager 初始化完成")
        logger.debug(f"当前配置: {json.dumps(self.config, indent=2, ensure_ascii=False)}")
    
    def _ensure_log_directories(self):
        """确保日志目录存在"""
        log_paths = [
            self.config["file"]["path"],
            self.config["error"]["path"],
            self.config["performance"]["path"]
        ]
        
        for log_path in log_paths:
            # 提取目录部分
            log_dir = Path(log_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
    
    def _setup_console_handler(self):
        """设置控制台处理器"""
        if not self.config["console"]["enabled"]:
            return
        
        console_config = self.config["console"]
        
        handler_id = logger.add(
            sys.stdout,
            level=console_config["level"],
            format=console_config["format"],
            colorize=console_config["colorize"],
            enqueue=self.config["async"]["enqueue"],
            backtrace=self.config["backtrace"],
            diagnose=self.config["diagnose"]
        )
        
        self.sink_handlers["console"] = handler_id
        logger.debug("控制台处理器设置完成")
    
    def _setup_file_handlers(self):
        """设置文件处理器"""
        # 主文件日志
        if self.config["file"]["enabled"]:
            file_config = self.config["file"]
            
            handler_id = logger.add(
                file_config["path"],
                level=file_config["level"],
                format=file_config["format"],
                rotation=file_config["rotation"],
                retention=file_config["retention"],
                compression=file_config.get("compression"),
                encoding=file_config["encoding"],
                enqueue=self.config["async"]["enqueue"],
                backtrace=self.config["backtrace"],
                diagnose=self.config["diagnose"]
            )
            
            self.sink_handlers["file"] = handler_id
            logger.debug("主文件处理器设置完成")
        
        # 错误文件日志
        if self.config["error"]["enabled"]:
            error_config = self.config["error"]
            
            handler_id = logger.add(
                error_config["path"],
                level=error_config["level"],
                format=error_config["format"],
                rotation=error_config["rotation"],
                retention=error_config["retention"],
                encoding=error_config["encoding"],
                enqueue=self.config["async"]["enqueue"],
                backtrace=self.config["backtrace"],
                diagnose=self.config["diagnose"]
            )
            
            self.sink_handlers["error"] = handler_id
            logger.debug("错误文件处理器设置完成")
        
        # 性能日志
        if self.config["performance"]["enabled"]:
            perf_config = self.config["performance"]
            
            def performance_log_sink(message):
                """性能日志专用sink - 只记录performance_log=True的消息"""
                record = message.record
                if record.get("extra", {}).get("performance_log", False):
                    # 直接写入文件，不使用标准格式
                    return message
                return None
            
            handler_id = logger.add(
                performance_log_sink,
                level=perf_config["level"],
                enqueue=self.config["async"]["enqueue"]
            )
            
            # 同时添加性能日志文件
            perf_file_handler = logger.add(
                perf_config["path"],
                level=perf_config["level"],
                format=perf_config["format"],
                rotation=perf_config["rotation"],
                retention=perf_config["retention"],
                encoding=perf_config["encoding"],
                filter=lambda record: record.get("extra", {}).get("performance_log", False),
                enqueue=self.config["async"]["enqueue"]
            )
            
            self.sink_handlers["performance"] = handler_id
            self.sink_handlers["performance_file"] = perf_file_handler
            logger.debug("性能日志处理器设置完成")
    
    def _setup_qt_integration(self):
        """设置Qt UI集成"""
        try:
            self.qt_handler = get_qt_handler()
            logger.debug("Qt UI集成设置完成")
        except Exception as e:
            logger.warning(f"Qt UI集成设置失败: {e}")
    
    def _setup_performance_monitoring(self):
        """设置性能监控"""
        try:
            self.performance_sink = get_performance_sink()
            logger.debug("性能监控设置完成")
        except Exception as e:
            logger.warning(f"性能监控设置失败: {e}")
    
    def _setup_exception_handling(self):
        """设置全局异常处理"""
        def exception_handler(type_, value, traceback):
            logger.exception(f"未捕获的异常: {type_.__name__}: {value}")
        
        # 注册全局异常处理器
        sys.excepthook = exception_handler
        logger.debug("全局异常处理器设置完成")
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        logger.info("开始更新Loguru配置")
        
        # 备份旧配置
        old_config = self.config.copy()
        
        try:
            # 更新配置
            self.config.update(new_config)
            
            # 重新初始化（移除旧处理器，添加新处理器）
            self._reinitialize_handlers()
            
            logger.info("Loguru配置更新成功")
            
        except Exception as e:
            # 恢复旧配置
            self.config = old_config
            logger.error(f"配置更新失败，已恢复旧配置: {e}")
            raise
    
    def _reinitialize_handlers(self):
        """重新初始化处理器"""
        # 移除旧处理器
        for handler_id in self.sink_handlers.values():
            try:
                logger.remove(handler_id)
            except ValueError:
                pass  # 处理器可能已经被移除
        
        self.sink_handlers.clear()
        
        # 重新设置处理器
        self._setup_console_handler()
        self._setup_file_handlers()
    
    def set_level(self, level: str):
        """设置全局日志级别"""
        self.config["level"] = level
        
        # 更新所有处理器的级别
        for handler_name, handler_id in self.sink_handlers.items():
            if handler_name in ["console", "file", "error"]:
                logger.remove(handler_id)
                
                # 重新添加处理器
                if handler_name == "console":
                    self._setup_console_handler()
                elif handler_name in ["file", "error"]:
                    self._setup_file_handlers()
                    break  # _setup_file_handlers会处理所有文件处理器
        
        logger.info(f"全局日志级别已设置为: {level}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        status = {
            "initialized": self.is_initialized,
            "handlers": list(self.sink_handlers.keys()),
            "config": self.config.copy(),
            "qt_handler_active": self.qt_handler is not None and self.qt_handler.is_active if self.qt_handler else False,
            "performance_sink_active": self.performance_sink is not None
        }
        
        # 添加Qt处理器状态
        if self.qt_handler:
            status["qt_handler_status"] = self.qt_handler.get_queue_status()
        
        # 添加性能监控状态
        if self.performance_sink:
            status["performance_summary"] = self.performance_sink.get_performance_summary()
        
        return status
    
    def clear_logs(self):
        """清空日志（保留当前会话）"""
        if self.qt_handler:
            self.qt_handler.clear_queue()
        
        logger.info("日志已清空")
    
    def shutdown(self):
        """关闭管理器"""
        logger.info("正在关闭LoguruManager...")
        
        # 关闭Qt处理器
        if self.qt_handler:
            self.qt_handler.shutdown()
        
        # 关闭性能监控
        if self.performance_sink:
            self.performance_sink.shutdown()
        
        # 移除所有处理器
        for handler_id in self.sink_handlers.values():
            try:
                logger.remove(handler_id)
            except ValueError:
                pass
        
        self.sink_handlers.clear()
        self.is_initialized = False
        
        logger.info("LoguruManager 已关闭")

# 全局管理器实例
_loguru_manager = None

def get_loguru_manager() -> LoguruManager:
    """获取全局Loguru管理器"""
    global _loguru_manager
    if _loguru_manager is None:
        _loguru_manager = LoguruManager()
    return _loguru_manager

def initialize_logging(config: Optional[Dict[str, Any]] = None):
    """初始化日志系统"""
    manager = get_loguru_manager()
    manager.initialize(config)
    return manager

# 便捷函数 - 完全替代原有的日志接口
def info(message: str, **kwargs):
    """信息日志"""
    logger.bind(**kwargs).info(message)

def debug(message: str, **kwargs):
    """调试日志"""
    logger.bind(**kwargs).debug(message)

def warning(message: str, **kwargs):
    """警告日志"""
    logger.bind(**kwargs).warning(message)

def error(message: str, **kwargs):
    """错误日志"""
    logger.bind(**kwargs).error(message)

def critical(message: str, **kwargs):
    """严重错误日志"""
    logger.bind(**kwargs).critical(message)

def exception(message: str, **kwargs):
    """异常日志"""
    logger.bind(**kwargs).exception(message)

# 性能日志便捷函数
def performance(category: str, metric_type: str, value: float, 
               service: str = "", operation: str = "", **extra):
    """性能日志"""
    from .loguru_performance_sink import log_performance
    log_performance(category, metric_type, value, service, operation, **extra)