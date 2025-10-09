from loguru import logger
"""
基于纯Loguru的异常处理器

提供全局异常处理功能，充分利用Loguru的异常处理能力。
"""

import sys
import traceback
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMessageBox


class LoguruExceptionHandler:
    """基于纯Loguru的全局异常处理器"""

    def __init__(self, app: Optional[QApplication] = None):
        """
        初始化异常处理器

        Args:
            app: Qt应用程序实例
        """
        self.app = app
        self.original_excepthook = sys.excepthook
        self.error_callbacks: List[Callable] = []

        # 添加专用的异常日志sink
        self._setup_exception_sink()

    def _setup_exception_sink(self):
        """设置专用的异常日志sink"""
        exception_log_path = Path("logs") / "exceptions_{time:YYYY-MM-DD}.log"

        # 添加异常专用日志文件
        logger.add(
            exception_log_path,
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | EXCEPTION | {process.id} | {thread.id} | {extra[exception_type]} | {extra[exception_context]} | {message}",
            filter=lambda record: "exception_type" in record["extra"],
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            enqueue=True,
            serialize=True,  # 启用JSON序列化以便后续分析
            backtrace=True,
            diagnose=True,
            catch=True
        )

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
                logger.info("接收到键盘中断信号，程序正常退出")
                sys.exit(0)

            # 使用Loguru的结构化异常记录
            exception_context = {
                "exception_type": exc_type.__name__,
                "exception_module": getattr(exc_type, '__module__', 'unknown'),
                "exception_context": self._extract_exception_context(exc_traceback),
                "system_info": self._get_system_info(),
                "timestamp": datetime.now().isoformat()
            }

            # 记录结构化异常信息 - 利用Loguru的bind功能
            logger.bind(**exception_context).exception(
                f"未捕获的异常: {exc_type.__name__}: {exc_value}"
            )

            # 分析异常并提供建议
            suggestions = self._analyze_exception(exc_type, exc_value, exc_traceback)
            if suggestions:
                logger.bind(analysis=True).warning(f"异常分析建议: {'; '.join(suggestions)}")

            # 调用注册的错误回调
            self._call_error_callbacks(exc_type, exc_value, exc_traceback, exception_context)

            # 显示用户友好的错误对话框
            self._show_user_error_dialog(exc_type, exc_value, suggestions)

            # 调用原始的异常处理器
            self.original_excepthook(exc_type, exc_value, exc_traceback)

        except Exception as handler_error:
            # 异常处理器本身出错，使用Loguru的安全记录
            logger.opt(exception=True).critical(
                f"异常处理器自身出错: {handler_error}"
            )
            self.original_excepthook(exc_type, exc_value, exc_traceback)

    def _extract_exception_context(self, exc_traceback) -> Dict[str, Any]:
        """提取异常上下文信息"""
        context = {
            "file_path": None,
            "line_number": None,
            "function_name": None,
            "code_context": [],
            "stack_depth": 0
        }

        if exc_traceback:
            tb = exc_traceback
            stack_frames = []

            while tb:
                frame = tb.tb_frame
                stack_frames.append({
                    "file": frame.f_code.co_filename,
                    "line": tb.tb_lineno,
                    "function": frame.f_code.co_name,
                    "locals": {k: str(v)[:100] for k, v in frame.f_locals.items()
                               if not k.startswith('__')}
                })
                tb = tb.tb_next

            if stack_frames:
                last_frame = stack_frames[-1]
                context.update({
                    "file_path": last_frame["file"],
                    "line_number": last_frame["line"],
                    "function_name": last_frame["function"],
                    "stack_depth": len(stack_frames),
                    "stack_frames": stack_frames[-3:]  # 只保留最后3帧
                })

        return context

    def _get_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        import platform
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture()[0]
        }

    def _analyze_exception(self, exc_type, exc_value, exc_traceback) -> List[str]:
        """分析异常并提供修复建议"""
        suggestions = []
        exc_name = exc_type.__name__
        exc_str = str(exc_value)

        # 常见异常分析
        if exc_name == "ModuleNotFoundError":
            missing_module = exc_str.split("'")[1] if "'" in exc_str else "unknown"
            suggestions.append(f"缺少模块 {missing_module}，请检查依赖是否正确安装")

        elif exc_name == "ImportError":
            suggestions.append("导入错误，请检查模块路径和依赖关系")

        elif exc_name == "AttributeError":
            suggestions.append("属性错误，请检查对象是否具有所访问的属性")

        elif exc_name == "KeyError":
            missing_key = exc_str.strip("'\"")
            suggestions.append(f"缺少键 {missing_key}，请检查字典或配置")

        elif exc_name == "FileNotFoundError":
            suggestions.append("文件未找到，请检查文件路径是否正确")

        elif exc_name == "PermissionError":
            suggestions.append("权限错误，请检查文件/目录访问权限")

        elif exc_name == "ConnectionError":
            suggestions.append("连接错误，请检查网络连接或服务状态")

        return suggestions

    def _call_error_callbacks(self, exc_type, exc_value, exc_traceback, context):
        """调用注册的错误回调"""
        for callback in self.error_callbacks:
            try:
                callback(exc_type, exc_value, exc_traceback, context)
            except Exception as callback_error:
                logger.warning(f"错误回调执行失败: {callback_error}")

    def _show_user_error_dialog(self, exc_type, exc_value, suggestions):
        """显示用户友好的错误对话框"""
        if not self.app:
            return

        try:
            title = "程序遇到错误"
            message = f"错误类型: {exc_type.__name__}\n错误信息: {exc_value}"

            if suggestions:
                message += f"\n\n建议:\n " + "\n ".join(suggestions)

            message += "\n\n详细信息已记录到日志文件中。"

            QMessageBox.critical(None, title, message)
        except Exception as dialog_error:
            logger.warning(f"无法显示错误对话框: {dialog_error}")

    def register_error_callback(self, callback: Callable):
        """注册错误回调函数"""
        self.error_callbacks.append(callback)

    def unregister_error_callback(self, callback: Callable):
        """取消注册错误回调函数"""
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)


# 全局异常处理器实例
_global_handler: Optional[LoguruExceptionHandler] = None


def setup_exception_handler(app: Optional[QApplication] = None):
    """
    设置全局异常处理器

    Args:
        app: Qt应用程序实例
    """
    global _global_handler

    try:
        _global_handler = LoguruExceptionHandler(app)
        sys.excepthook = _global_handler.handle_exception

        logger.success("基于Loguru的全局异常处理器已配置")
        logger.info("异常信息将被结构化记录并分析")

    except Exception as e:
        logger.error(f"异常处理器设置失败: {e}")


def get_exception_handler() -> Optional[LoguruExceptionHandler]:
    """获取当前的异常处理器实例"""
    return _global_handler


def register_error_callback(callback: Callable):
    """注册全局错误回调"""
    if _global_handler:
        _global_handler.register_error_callback(callback)
    else:
        logger.warning("异常处理器尚未初始化，无法注册回调")


def unregister_error_callback(callback: Callable):
    """取消注册全局错误回调"""
    if _global_handler:
        _global_handler.unregister_error_callback(callback)

# 便捷的异常记录函数


def log_handled_exception(exc_type, exc_value, context: Dict[str, Any] = None):
    """记录已处理的异常"""
    context = context or {}
    logger.bind(
        exception_type=exc_type.__name__,
        exception_context=context,
        handled=True
    ).exception(f"已处理的异常: {exc_type.__name__}: {exc_value}")


def log_recovery_action(action: str, success: bool, details: str = ""):
    """记录恢复操作"""
    logger.bind(recovery=True, action=action, success=success).info(
        f"恢复操作 {action}: {'成功' if success else '失败'} - {details}"
    )
