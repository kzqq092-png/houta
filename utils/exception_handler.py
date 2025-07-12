"""
异常处理器

提供全局异常处理功能。
"""

import sys
import logging
import traceback
from typing import Optional

from PyQt5.QtWidgets import QApplication, QMessageBox

logger = logging.getLogger(__name__)


class GlobalExceptionHandler:
    """全局异常处理器"""

    def __init__(self, app: Optional[QApplication] = None):
        """
        初始化异常处理器

        Args:
            app: Qt应用程序实例
        """
        self.app = app
        self.original_excepthook = sys.excepthook

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        处理未捕获的异常

        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_traceback: 异常追踪
        """
        try:
            # 如果是KeyboardInterrupt，直接退出
            if issubclass(exc_type, KeyboardInterrupt):
                sys.exit(0)

            # 记录异常信息
            error_msg = ''.join(traceback.format_exception(
                exc_type, exc_value, exc_traceback))
            logger.error(f"Uncaught exception: {error_msg}")

            # 显示错误对话框
            if self.app:
                try:
                    QMessageBox.critical(
                        None,
                        "程序错误",
                        f"程序遇到未处理的错误：\n\n{exc_value}\n\n详细信息请查看日志文件。"
                    )
                except:
                    pass

            # 调用原始的异常处理器
            self.original_excepthook(exc_type, exc_value, exc_traceback)

        except Exception as e:
            # 异常处理器本身出错，直接调用原始处理器
            logger.error(f"Exception handler failed: {e}")
            self.original_excepthook(exc_type, exc_value, exc_traceback)


def setup_exception_handler(app: Optional[QApplication] = None):
    """
    设置全局异常处理器

    Args:
        app: Qt应用程序实例
    """
    try:
        handler = GlobalExceptionHandler(app)
        sys.excepthook = handler.handle_exception
        logger.info("Global exception handler configured")

    except Exception as e:
        logger.error(f"Failed to setup exception handler: {e}")
