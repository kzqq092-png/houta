"""
自定义控件模块

包含交易系统GUI的自定义控件和组件
"""

import sys
import traceback
from datetime import datetime
from PyQt5.QtWidgets import QListWidget, QApplication
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag, QColor


class StockListWidget(QListWidget):
    """自定义股票列表控件，支持拖拽功能"""

    def startDrag(self, supportedActions):
        """开始拖拽操作"""
        try:
            # 获取当前选中的项目
            current_item = self.currentItem()
            if not current_item:
                return

            # 创建拖拽对象
            drag = QDrag(self)
            mime_data = QMimeData()

            # 设置拖拽数据
            stock_text = current_item.text()
            mime_data.setText(stock_text)
            drag.setMimeData(mime_data)

            # 执行拖拽
            drag.exec_(Qt.CopyAction)

        except Exception as e:
            print(f"拖拽操作失败: {str(e)}")


class GlobalExceptionHandler:
    """全局异常处理器"""

    def __init__(self, app_instance):
        """初始化全局异常处理器

        Args:
            app_instance: QApplication实例
        """
        self.app = app_instance
        self.original_excepthook = sys.excepthook
        sys.excepthook = self.handle_exception

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """处理未捕获的异常

        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_traceback: 异常追踪
        """
        try:
            # 格式化异常信息
            error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))

            # 记录到日志
            print(f"未捕获的异常: {error_msg}")

            # 如果有主窗口，尝试记录到日志管理器
            if hasattr(self.app, 'main_window'):
                main_window = self.app.main_window
                if hasattr(main_window, 'log_manager') and main_window.log_manager:
                    main_window.log_manager.error(f"未捕获的异常: {str(exc_value)}")
                    main_window.log_manager.error(error_msg)

            # 显示错误对话框（仅在GUI模式下）
            if hasattr(self.app, 'main_window'):
                self._show_error_dialog(exc_type, exc_value, error_msg)

        except Exception as e:
            # 异常处理器本身出错时，回退到原始处理器
            print(f"异常处理器出错: {str(e)}")
            self.original_excepthook(exc_type, exc_value, exc_traceback)

    def _show_error_dialog(self, exc_type, exc_value, error_msg):
        """显示错误对话框

        Args:
            exc_type: 异常类型
            exc_value: 异常值
            error_msg: 错误消息
        """
        try:
            from PyQt5.QtWidgets import QMessageBox, QTextEdit

            # 创建错误对话框
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("系统错误")
            msg_box.setText(f"发生未处理的异常: {exc_type.__name__}")
            msg_box.setInformativeText(str(exc_value))

            # 添加详细信息
            text_edit = QTextEdit()
            text_edit.setPlainText(error_msg)
            text_edit.setReadOnly(True)
            msg_box.setDetailedText(error_msg)

            # 添加按钮
            msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Ignore)
            msg_box.setDefaultButton(QMessageBox.Ok)

            # 显示对话框
            result = msg_box.exec_()

            # 如果用户选择忽略，继续运行
            if result == QMessageBox.Ignore:
                return

        except Exception as e:
            print(f"显示错误对话框失败: {str(e)}")


def safe_strftime(dt, fmt='%Y-%m-%d'):
    """安全的日期时间格式化函数

    Args:
        dt: datetime对象
        fmt: 格式字符串

    Returns:
        格式化后的字符串
    """
    try:
        if dt is None:
            return ""

        if isinstance(dt, str):
            return dt

        if hasattr(dt, 'strftime'):
            return dt.strftime(fmt)

        return str(dt)

    except Exception as e:
        print(f"日期格式化失败: {str(e)}")
        return str(dt) if dt else ""


def add_shadow(widget, blur_radius=20, x_offset=0, y_offset=4, color=QColor(0, 0, 0, 80)):
    """为控件添加阴影效果

    Args:
        widget: 要添加阴影的控件
        blur_radius: 模糊半径
        x_offset: X轴偏移
        y_offset: Y轴偏移
        color: 阴影颜色
    """
    try:
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setXOffset(x_offset)
        shadow.setYOffset(y_offset)
        shadow.setColor(color)

        widget.setGraphicsEffect(shadow)

    except Exception as e:
        print(f"添加阴影效果失败: {str(e)}")


class ProgressStyleHelper:
    """进度条样式辅助类"""

    @staticmethod
    def get_progress_style(value: float) -> str:
        """根据进度值获取样式

        Args:
            value: 进度值 (0-100)

        Returns:
            CSS样式字符串
        """
        try:
            # 根据进度值确定颜色
            if value < 30:
                color = "#dc3545"  # 红色
            elif value < 70:
                color = "#ffc107"  # 黄色
            else:
                color = "#28a745"  # 绿色

            return f"""
                QProgressBar {{
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    width: 20px;
                }}
            """

        except Exception as e:
            print(f"获取进度条样式失败: {str(e)}")
            return ""


class StatusMessageHelper:
    """状态消息辅助类"""

    @staticmethod
    def show_status_message(status_bar, message: str, timeout: int = 5000, error: bool = False):
        """在状态栏显示消息

        Args:
            status_bar: 状态栏对象
            message: 消息内容
            timeout: 超时时间（毫秒）
            error: 是否为错误消息
        """
        try:
            if not status_bar:
                return

            # 设置样式
            if error:
                status_bar.setStyleSheet("color: red; font-weight: bold;")
            else:
                status_bar.setStyleSheet("color: black;")

            # 显示消息
            status_bar.showMessage(message, timeout)

        except Exception as e:
            print(f"显示状态消息失败: {str(e)}")

    @staticmethod
    def clear_status_message(status_bar):
        """清除状态栏消息

        Args:
            status_bar: 状态栏对象
        """
        try:
            if status_bar:
                status_bar.clearMessage()
                status_bar.setStyleSheet("")

        except Exception as e:
            print(f"清除状态消息失败: {str(e)}")


class DialogHelper:
    """对话框辅助类"""

    @staticmethod
    def center_dialog(dialog, parent=None, offset_y=50):
        """居中显示对话框

        Args:
            dialog: 对话框对象
            parent: 父窗口
            offset_y: Y轴偏移量
        """
        try:
            if parent:
                # 相对于父窗口居中
                parent_geometry = parent.geometry()
                dialog_geometry = dialog.geometry()

                x = parent_geometry.x() + (parent_geometry.width() - dialog_geometry.width()) // 2
                y = parent_geometry.y() + (parent_geometry.height() - dialog_geometry.height()) // 2 - offset_y

                dialog.move(x, y)
            else:
                # 相对于屏幕居中
                screen = QApplication.desktop().screenGeometry()
                dialog_geometry = dialog.geometry()

                x = (screen.width() - dialog_geometry.width()) // 2
                y = (screen.height() - dialog_geometry.height()) // 2 - offset_y

                dialog.move(x, y)

        except Exception as e:
            print(f"居中对话框失败: {str(e)}")


class ComboBoxHelper:
    """下拉框辅助类"""

    @staticmethod
    def adjust_combobox_width(combobox):
        """自动调整下拉框宽度

        Args:
            combobox: 下拉框对象
        """
        try:
            if not combobox:
                return

            # 计算最大文本宽度
            max_width = 0
            font_metrics = combobox.fontMetrics()

            for i in range(combobox.count()):
                text = combobox.itemText(i)
                width = font_metrics.width(text)
                max_width = max(max_width, width)

            # 设置最小宽度（加上一些边距）
            combobox.setMinimumWidth(max_width + 50)

        except Exception as e:
            print(f"调整下拉框宽度失败: {str(e)}")


class ThemeHelper:
    """主题辅助类"""

    @staticmethod
    def apply_dark_theme(widget):
        """应用暗色主题

        Args:
            widget: 要应用主题的控件
        """
        try:
            dark_style = """
                QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QLineEdit, QTextEdit, QPlainTextEdit {
                    background-color: #3c3c3c;
                    border: 1px solid #555555;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #404040;
                    border: 1px solid #555555;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #606060;
                }
            """
            widget.setStyleSheet(dark_style)

        except Exception as e:
            print(f"应用暗色主题失败: {str(e)}")

    @staticmethod
    def apply_light_theme(widget):
        """应用亮色主题

        Args:
            widget: 要应用主题的控件
        """
        try:
            light_style = """
                QWidget {
                    background-color: #ffffff;
                    color: #000000;
                }
                QLineEdit, QTextEdit, QPlainTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #cccccc;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """
            widget.setStyleSheet(light_style)

        except Exception as e:
            print(f"应用亮色主题失败: {str(e)}")
