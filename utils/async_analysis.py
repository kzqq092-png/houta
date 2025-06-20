#!/usr/bin/env python3
"""
统一异步分析工具模块

提供统一的异步分析方法，避免重复的信号连接问题
"""

from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from PyQt5.QtWidgets import QPushButton
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Optional
import traceback


class AsyncAnalysisManager(QObject):
    """异步分析管理器 - 统一处理按钮异步分析，避免重复连接"""

    analysis_completed = pyqtSignal(object)  # 分析完成信号
    analysis_error = pyqtSignal(str)  # 分析错误信号

    def __init__(self, log_manager=None):
        super().__init__()
        self.log_manager = log_manager
        self._thread_pool = ThreadPoolExecutor(max_workers=2)
        self._active_tasks = {}  # 跟踪活跃的任务

    def run_analysis_async(self, button: QPushButton, analysis_func: Callable,
                           *args, progress_callback=None, **kwargs):
        """
        统一的异步分析方法

        Args:
            button: 触发分析的按钮
            analysis_func: 分析函数
            *args: 分析函数的位置参数
            progress_callback: 进度回调函数
            **kwargs: 分析函数的关键字参数
        """
        # 防止重复执行
        button_id = id(button)
        if button_id in self._active_tasks:
            if self.log_manager:
                self.log_manager.warning("分析任务已在进行中，忽略重复请求")
            return

        original_text = button.text()
        button.setText("取消")
        button.setEnabled(True)

        # 标记任务为活跃状态
        self._active_tasks[button_id] = True

        def on_cancel():
            """取消分析任务"""
            self._active_tasks[button_id] = False
            button.setText(original_text)
            button.setEnabled(True)
            if self.log_manager:
                self.log_manager.info("用户取消了分析任务")

        # 临时连接取消功能
        try:
            button.clicked.disconnect()
        except Exception:
            pass
        button.clicked.connect(on_cancel)

        def task():
            """分析任务"""
            try:
                if not self._active_tasks.get(button_id, False):
                    return None

                if progress_callback:
                    progress_callback(0, "开始分析...")

                result = analysis_func(*args, **kwargs)

                if progress_callback:
                    progress_callback(100, "分析完成")

                return result
            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"分析异常: {str(e)}")
                    self.log_manager.error(traceback.format_exc())
                raise e

        def on_done(future):
            """分析完成回调"""
            try:
                # 清理活跃任务标记
                self._active_tasks.pop(button_id, None)

                # 恢复按钮状态
                button.setText(original_text)
                button.setEnabled(True)

                # 重新连接原始功能
                try:
                    button.clicked.disconnect()
                except Exception:
                    pass
                button.clicked.connect(
                    lambda: self.run_analysis_async(
                        button, analysis_func, *args,
                        progress_callback=progress_callback, **kwargs
                    )
                )

                # 处理结果
                try:
                    result = future.result()
                    if result is not None:
                        self.analysis_completed.emit(result)
                        if self.log_manager:
                            self.log_manager.info("分析任务完成")
                except Exception as e:
                    error_msg = f"分析失败: {str(e)}"
                    self.analysis_error.emit(error_msg)
                    if self.log_manager:
                        self.log_manager.error(error_msg)

            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"处理分析完成回调失败: {str(e)}")

        # 提交任务到线程池
        future = self._thread_pool.submit(task)
        future.add_done_callback(on_done)

        if self.log_manager:
            self.log_manager.info("已启动异步分析任务")

    def cleanup(self):
        """清理资源"""
        try:
            self._active_tasks.clear()
            self._thread_pool.shutdown(wait=False)
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清理异步分析管理器失败: {str(e)}")


# 全局实例（可选）
_global_async_manager = None


def get_async_analysis_manager(log_manager=None):
    """获取全局异步分析管理器实例"""
    global _global_async_manager
    if _global_async_manager is None:
        _global_async_manager = AsyncAnalysisManager(log_manager)
    return _global_async_manager
