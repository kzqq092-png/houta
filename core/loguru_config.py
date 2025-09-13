"""
Loguru 配置模块
提供统一的日志配置管理，完全替代 Python 标准 logging 模块
"""

from loguru import logger
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class PureLoguruConfig:

    def __init__(self):
        self.handlers: Dict[str, int] = {}
        self.initialized = False

        # 创建日志目录
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

    def setup_pure_loguru(self, level: str = "INFO", async_logging: bool = True):
        if self.initialized:
            self.reset()

        # 移除所有现有handlers
        logger.remove()

        # 1. 控制台输出 - 彩色格式 (Windows环境简化格式)
        console_handler = logger.add(
            sys.stdout,
            level=level,
            format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <4}</level> | <cyan>{name}:{function}:{line}</cyan> - {message}",
            colorize=True,
            enqueue=async_logging,
            catch=True
        )
        self.handlers["console"] = console_handler

        # 2. 应用主日志文件
        app_handler = logger.add(
            self.log_dir / "factorweave_{time:YYYY-MM-DD}.log",
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <4} | {process.id} | {thread.id} | {name}:{function}:{line} - {message}",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            enqueue=async_logging,
            catch=True
        )
        self.handlers["app"] = app_handler

        # 3. 错误日志专用文件
        error_handler = logger.add(
            self.log_dir / "errors_{time:YYYY-MM-DD}.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {process.id} | {name}:{function}:{line} | {exception} - {message}",
            rotation="50 MB",
            retention="10 days",
            compression="zip",
            enqueue=async_logging,
            backtrace=True,
            diagnose=True,
            catch=True
        )
        self.handlers["error"] = error_handler

        self.initialized = True

    def reset(self):
        """重置所有配置"""
        for handler_id in self.handlers.values():
            logger.remove(handler_id)
        self.handlers.clear()
        self.initialized = False


loguru_config_instance = PureLoguruConfig()


def initialize_loguru(level: str = "INFO", async_logging: bool = True):
    """全局Loguru设置函数，确保只初始化一次"""
    if not loguru_config_instance.initialized:
        loguru_config_instance.setup_pure_loguru(level, async_logging)
        logger.info("=== FactorWeave-Quant 系统启动 ===")
        logger.info(f"日志级别: {level}")
        logger.info(f"异步模式: {'开启' if async_logging else '关闭'}")
    return logger


# 默认初始化，确保Loguru在模块导入时即可用
initialize_loguru()
