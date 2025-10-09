#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志面板模块
封装日志组件，提供统一的日志面板接口
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from .base_panel import BasePanel
from gui.widgets.log_widget import LogWidget
from core.events.event_bus import EventBus

class LogPanel(BasePanel):
    """日志面板类"""

    def __init__(self, parent, coordinator):
        super().__init__(parent, coordinator)
        self.log_widget = None

    def _create_widgets(self):
        """创建UI组件"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建日志组件
        self.log_widget = LogWidget()
        layout.addWidget(self.log_widget)

        if self._root_frame:
            self._root_frame.setLayout(layout)

    def _bind_events(self):
        """绑定事件"""
        # 订阅日志事件
        if self.event_bus:
            self.event_bus.subscribe('log_message', self._on_log_message)

    def _on_log_message(self, event):
        """处理日志消息事件"""
        if self.log_widget:
            data = event.data
            if isinstance(data, dict):
                level = data.get('level', 'INFO')
                message = data.get('message', '')
                self.log_widget.add_log(level, message)
            else:
                self.log_widget.add_log('INFO', str(data))

    def add_log(self, level: str, message: str):
        """添加日志"""
        if self.log_widget:
            self.log_widget.add_log(level, message)

    def clear_logs(self):
        """清空日志"""
        if self.log_widget:
            self.log_widget.clear_logs()

    def export_logs(self, file_path: str):
        """导出日志"""
        if self.log_widget:
            self.log_widget.export_logs(file_path)

    def get_log_widget(self) -> LogWidget:
        """获取日志组件"""
        return self.log_widget
