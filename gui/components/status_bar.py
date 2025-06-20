"""
状态栏组件模块

包含自定义状态栏组件
"""

from PyQt5.QtWidgets import QStatusBar, QLabel, QProgressBar, QWidget


class StatusBar(QStatusBar):
    """
    自定义状态栏，支持状态信息、进度条、错误提示和永久控件。
    兼容主窗口和各类UI组件的调用。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_label = QLabel("就绪")
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(180)
        self._progress_bar.setMinimumWidth(120)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self.addWidget(self._status_label)
        self.addWidget(self._progress_bar)
        self._error_mode = False

    def set_status(self, message: str, error: bool = False, timeout: int = None):
        """
        设置状态栏文本，支持高亮错误和自定义超时时间。

        Args:
            message: 状态消息
            error: 是否为错误消息
            timeout: 消息显示超时时间（毫秒），如果为None则使用默认值
        """
        self._status_label.setText(message)
        if error:
            self._status_label.setStyleSheet("color: red;")
            self._error_mode = True
        else:
            self._status_label.setStyleSheet("")
            self._error_mode = False

        # 使用自定义超时时间或默认值
        if timeout is not None:
            self.showMessage(message, timeout)
        else:
            self.showMessage(message, 5000 if not error else 8000)

    def show_progress(self, visible: bool = True):
        """
        显示或隐藏进度条。
        """
        self._progress_bar.setVisible(visible)
        if not visible:
            self._progress_bar.setValue(0)
            self._progress_bar.setStyleSheet("")

    def set_progress(self, value: int):
        """
        设置进度条进度。
        """
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(max(0, min(100, int(value))))
        self._progress_bar.setStyleSheet("")

    def set_progress_error(self, message: str = "发生错误"):
        """
        进度条显示错误状态。
        """
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(100)
        self._progress_bar.setStyleSheet("QProgressBar::chunk {background-color: #FF1744;}")
        self.set_status(message, error=True)

    def addPermanentWidget(self, widget: QWidget, stretch: int = 0):
        """
        添加永久控件（如日志按钮），兼容QStatusBar接口。
        """
        super().addPermanentWidget(widget, stretch)

    def clear_status(self):
        """
        清除状态栏信息和进度。
        """
        self._status_label.setText("")
        self._progress_bar.setVisible(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet("")
        self._error_mode = False
