"""
日志控件模块

提供日志显示和管理功能
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QLineEdit, QTextEdit,
                             QFileDialog, QMessageBox, QScrollArea, QDialog, QMenu, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QTextCursor
from datetime import datetime
from core.logger import LogManager, LogLevel
import traceback


class LogWidget(QWidget):
    """日志控件类"""

    # 定义信号
    log_added = pyqtSignal(str, str)  # 日志消息, 级别
    log_cleared = pyqtSignal()
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, log_manager: LogManager = None, parent=None):
        """初始化日志控件

        Args:
            log_manager: 日志管理器实例
            parent: 父窗口
        """
        try:
            super().__init__(parent)
            self.log_text = None  # 确保属性总是存在

            # 使用传入的日志管理器或创建新的
            self.log_manager = log_manager or LogManager()

            self.pause_scroll = False  # 显式初始化
            self.user_paused = False  # 新增：区分用户主动暂停
            self.popup_dialog = None   # 持有弹窗引用
            self._all_logs = []        # 存储所有日志 (message, level, timestamp)

            # 初始化UI
            self.init_ui()

            # 连接信号
            self.connect_signals()

            # 设置样式
            self.apply_style()

            self.log_manager.info("日志控件初始化完成")

        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            self.log_text = None
            if self.log_manager:
                self.log_manager.error(error_msg)
                self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def init_ui(self):
        """初始化UI"""
        try:
            # 创建主布局
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # 创建工具栏
            toolbar_layout = QHBoxLayout()
            toolbar_layout.setContentsMargins(0, 0, 0, 0)
            toolbar_layout.setSpacing(5)

            # 日志级别过滤器
            level_label = QLabel("日志级别:")
            self.level_combo = QComboBox()
            self.level_combo.addItems(["全部", "信息", "警告", "错误", "调试"])
            self.level_combo.setFixedWidth(100)
            toolbar_layout.addWidget(level_label)
            toolbar_layout.addWidget(self.level_combo)

            # 搜索框
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("搜索日志...")
            self.search_box.setFixedWidth(200)
            toolbar_layout.addWidget(self.search_box)

            # 添加弹性空间
            toolbar_layout.addStretch()

            # 状态提示
            self.scroll_status_label = QLabel("自动滚动中")
            self.scroll_status_label.setFixedHeight(50)
            self.scroll_status_label.setFixedWidth(70)
            toolbar_layout.addWidget(self.scroll_status_label)

            # 最大化/还原按钮
            self.maximize_btn = QPushButton("最大化")
            self.maximize_btn.setFixedWidth(80)
            self.maximize_btn.clicked.connect(self.toggle_maximize)
            toolbar_layout.addWidget(self.maximize_btn)

            # 弹窗按钮
            self.popup_btn = QPushButton("弹窗")
            self.popup_btn.setFixedWidth(80)
            self.popup_btn.clicked.connect(self.show_popup)
            toolbar_layout.addWidget(self.popup_btn)

            # 暂停/恢复滚动按钮
            self.pause_btn = QPushButton("暂停滚动")
            self.pause_btn.setFixedWidth(80)
            self.pause_btn.clicked.connect(self.toggle_scroll)
            toolbar_layout.addWidget(self.pause_btn)

            # 清除按钮
            self.clear_button = QPushButton("清除")
            self.clear_button.setFixedWidth(80)
            toolbar_layout.addWidget(self.clear_button)

            # 导出按钮
            self.export_button = QPushButton("导出")
            self.export_button.setFixedWidth(80)
            toolbar_layout.addWidget(self.export_button)

            layout.addLayout(toolbar_layout)

            # 插入分割线
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setObjectName("line")
            layout.addWidget(line)

            # 创建日志文本框（不再嵌套QScrollArea）
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setLineWrapMode(QTextEdit.WidgetWidth)
            self.log_text.setContextMenuPolicy(Qt.CustomContextMenu)
            self.log_text.customContextMenuRequested.connect(
                self.show_log_context_menu)
            self.log_text.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
            # 极简风格由全局QSS控制
            layout.addWidget(self.log_text, 1)  # 让内容区自动填满剩余空间

            # 自动检测用户手动滚动，切换自动滚动状态
            self.log_text.verticalScrollBar().valueChanged.connect(
                self._on_scrollbar_value_changed)

            self.log_manager.info("日志控件UI初始化完成")
        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            self.log_text = None
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def connect_signals(self):
        """连接控件信号（不再连接log_manager信号，信号连接只在主窗口进行）"""
        try:
            if getattr(self, '_signals_connected', False):
                return
            self._signals_connected = True
            # 只连接控件信号，不连接log_manager信号
            self.level_combo.currentTextChanged.connect(self.filter_logs)
            self.search_box.textChanged.connect(self.search_logs)
            self.clear_button.clicked.connect(self.clear_logs)
            self.export_button.clicked.connect(self.export_logs)
            self.log_manager.info("信号连接完成")
        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def apply_style(self):
        """应用样式"""
        try:
            # 判断主题（可根据主窗口theme_manager或自定义属性）
            dark = True
            if hasattr(self, 'theme_manager'):
                dark = getattr(self.theme_manager, 'is_dark', True)
            bg = "#181c24" if dark else "#fff"
            fg = "#e0e6ed" if dark else "#23293a"
            border = "#23293a" if dark else "#bdbdbd"
            hover = "#1976d2"
            highlight = "#ffd600"
            line_color = "#444a5a" if dark else "#e0e0e0"
            self.setStyleSheet(f"""
                QWidget {{
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    font-size: 12px;
                }}
                QLabel {{
                    color: #1976d2;
                }}
                QComboBox, QLineEdit {{
                    border: 1.5px solid {border};
                    border-radius: 4px;
                    padding: 4px;
                    background: {bg};
                    color: {fg};
                }}
                QComboBox:hover, QLineEdit:hover {{
                    background: {hover};
                    color: {highlight};
                }}
                QComboBox:focus, QLineEdit:focus {{
                    border-color: {hover};
                }}
                QPushButton {{
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    background: {hover};
                    color: white;
                }}
                QPushButton:hover {{
                    background: {border};
                    color: {highlight};
                }}
                QPushButton:pressed {{
                    background: #0d47a1;
                }}
                QTextEdit, QPlainTextEdit {{
                    border: none;
                    padding: 0;
                    margin: 0;
                    background: {bg};
                    color: {fg};
                    font-family: 'Consolas', 'Microsoft YaHei', monospace;
                    font-size: 13px;
                }}
                QTextEdit:focus, QPlainTextEdit:focus {{
                    outline: 1.5px solid {hover};
                }}
                QFrame#line {{
                    border-top: 1.5px solid {line_color};
                    margin: 6px 0;
                }}
                QScrollArea {{
                    border: none;
                    background: transparent;
                    margin: 0;
                    padding: 0;
                }}
                QScrollBar:vertical {{
                    background: #23293a;
                    width: 10px;
                    margin: 0;
                    border-radius: 5px;
                }}
                QScrollBar::handle:vertical {{
                    background: #bdbdbd;
                    min-height: 20px;
                    border-radius: 5px;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0;
                }}
                QScrollBar:horizontal {{
                    background: #23293a;
                    height: 10px;
                    margin: 0;
                    border-radius: 5px;
                }}
                QScrollBar::handle:horizontal {{
                    background: #bdbdbd;
                    min-width: 20px;
                    border-radius: 5px;
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    width: 0;
                }}
            """)
        except Exception as e:
            error_msg = f"应用样式失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def add_log(self, message: str, level: str = "INFO"):
        """添加日志，增加去重逻辑，并修复自动滚动逻辑"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 简单去重：如果上一条日志内容、级别、时间完全一致则不添加
            if self._all_logs and self._all_logs[-1] == (message, level, timestamp):
                return
            self._all_logs.append((message, level, timestamp))
            # 判断当前是否自动滚动
            self.refresh_display(scroll_to_end=not self.pause_scroll)
            # 错误消息闪烁
            if level.upper() == "ERROR":
                self.flash_error()
            self.log_added.emit(message, level)
        except Exception as e:
            error_msg = f"添加日志失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def flash_error(self):
        """闪烁错误提示"""
        try:
            def flash():
                self.setStyleSheet("""
                    QWidget {
                        background-color: #ffebee;
                    }
                """)
                QTimer.singleShot(500, lambda: self.apply_style())

            flash()
            QTimer.singleShot(1000, flash)

        except Exception as e:
            self.log_manager.error(f"闪烁错误提示失败: {str(e)}")

    def filter_logs(self, level: str):
        """根据级别过滤日志

        Args:
            level: 日志级别
        """
        self.refresh_display()

    def search_logs(self, text: str):
        """搜索日志

        Args:
            text: 搜索文本
        """
        self.refresh_display()

    def clear_logs(self):
        """清除日志"""
        try:
            self._all_logs.clear()  # 清空日志缓存
            if self.log_text is not None:
                self.log_text.clear()
            self.log_cleared.emit()
            self.log_manager.info("日志已清除")
        except Exception as e:
            error_msg = f"清除日志失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def export_logs(self):
        """导出日志到文件"""
        try:
            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志",
                "",
                "Text Files (*.txt);;Log Files (*.log)"
            )

            if file_path:
                # 保存日志
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())

                self.log_manager.info(f"日志已导出到: {file_path}")

        except Exception as e:
            error_msg = f"导出日志失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def show_log_context_menu(self, pos):
        """日志内容右键菜单：复制、全选、清空、导出"""
        menu = QMenu(self)
        copy_action = menu.addAction("复制")
        select_all_action = menu.addAction("全选")
        clear_action = menu.addAction("清空")
        export_action = menu.addAction("导出")
        action = menu.exec_(self.log_text.mapToGlobal(pos))
        if action == copy_action:
            self.log_text.copy()
        elif action == select_all_action:
            self.log_text.selectAll()
        elif action == clear_action:
            self.clear_logs()
        elif action == export_action:
            self.export_logs()

    def toggle_maximize(self):
        """最大化/全屏/还原日志区"""
        window = self.window()
        if hasattr(self, '_is_maximized') and self._is_maximized:
            # 还原
            if hasattr(self, '_old_geometry'):
                self.setGeometry(self._old_geometry)
            if hasattr(window, 'showNormal'):
                window.showNormal()
            self._is_maximized = False
            self.maximize_btn.setText("最大化")
        else:
            # 全屏
            self._old_geometry = self.geometry()
            if hasattr(window, 'showFullScreen'):
                window.showFullScreen()
            self._is_maximized = True
            self.maximize_btn.setText("还原")

    def show_popup(self):
        """弹出独立日志窗口，普通浮动窗，主题一致，功能完整"""
        try:
            if self.popup_dialog is not None:
                self.popup_dialog.raise_()
                self.popup_dialog.activateWindow()
                self.popup_dialog.show()
                return

            self.popup_dialog = QDialog()
            self.popup_dialog.setWindowTitle("系统日志详情")
            self.popup_dialog.resize(800, 1000)
            self.popup_dialog.setMinimumSize(600, 300)

            # 设置窗口标志
            self.popup_dialog.setWindowFlags(
                Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinMaxButtonsHint
            )
            self.popup_dialog.setWindowModality(Qt.NonModal)
            self.popup_dialog.setAttribute(Qt.WA_DeleteOnClose)

            # 应用主题样式
            self.popup_dialog.setStyleSheet(self.styleSheet())

            # 创建主布局
            layout = QVBoxLayout(self.popup_dialog)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(5)

            # 顶部工具栏
            toolbar_layout = QHBoxLayout()
            toolbar_layout.setSpacing(16)
            toolbar_layout.setContentsMargins(0, 0, 0, 0)

            # 日志级别过滤
            level_label = QLabel("日志级别1:")
            level_label.setFixedWidth(100)
            level_label.setFixedHeight(45)
            level_label.setAlignment(Qt.AlignCenter)
            level_label.setStyleSheet("color: #1976d2;")
            level_combo = QComboBox()
            toolbar_layout.addWidget(level_label)
            level_combo.addItems(["全部", "信息", "警告", "错误", "调试"])
            level_combo.setCurrentText(self.level_combo.currentText())
            level_combo.setFixedWidth(100)
            toolbar_layout.addWidget(level_combo)

            # 搜索框
            search_box = QLineEdit()
            search_box.setPlaceholderText("搜索日志...")
            search_box.setText(self.search_box.text())
            search_box.setFixedWidth(200)
            toolbar_layout.addWidget(search_box)

            # 添加弹性空间
            toolbar_layout.addStretch()

            # 清除按钮
            clear_btn = QPushButton("清除")
            clear_btn.setFixedWidth(80)
            toolbar_layout.addWidget(clear_btn)

            # 导出按钮
            export_btn = QPushButton("导出")
            export_btn.setFixedWidth(80)
            toolbar_layout.addWidget(export_btn)

            layout.addLayout(toolbar_layout)

            # 日志内容区
            log_text = QTextEdit()
            log_text.setReadOnly(True)
            log_text.setLineWrapMode(QTextEdit.WidgetWidth)
            log_text.setAlignment(Qt.AlignLeft)
            log_text.setStyleSheet("""
                QTextEdit {
                    font-family: 'Consolas', 'Microsoft YaHei', monospace;
                    font-size: 13px;
                    background: #f8fafc;
                    color: #23293a;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 0;
                }
                QScrollBar:vertical {
                    background: #f0f0f0;
                    width: 12px;
                    margin: 0;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background: #bdbdbd;
                    min-height: 30px;
                    border-radius: 6px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0;
                }
                QScrollBar:horizontal {
                    background: #f0f0f0;
                    height: 12px;
                    margin: 0;
                    border-radius: 6px;
                }
                QScrollBar::handle:horizontal {
                    background: #bdbdbd;
                    min-width: 30px;
                    border-radius: 6px;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    width: 0;
                }
            """)
            log_text.setSizePolicy(QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
            layout.addWidget(log_text, 1)

            # 日志内容渲染逻辑
            def get_filtered_logs_html():
                level_text = level_combo.currentText()
                search_text = search_box.text().strip().lower()
                html_logs = []
                for msg, lvl, ts in self._all_logs:
                    if level_text != "全部":
                        if level_text == "信息" and lvl.upper() != "INFO":
                            continue
                        if level_text == "警告" and lvl.upper() != "WARNING":
                            continue
                        if level_text == "错误" and lvl.upper() != "ERROR":
                            continue
                        if level_text == "调试" and lvl.upper() != "DEBUG":
                            continue
                    if search_text and search_text not in msg.lower():
                        continue
                    color = {
                        "ERROR": "#FF0000",
                        "WARNING": "#FFA500",
                        "INFO": "#000000",
                        "DEBUG": "#808080"
                    }.get(lvl.upper(), "#000000")
                    html_logs.append(
                        f'<div style="text-align:left;color:{color};word-break:break-all;white-space:pre-wrap;width:100%;">[{ts}] [{lvl}] {msg}</div>')
                if not html_logs:
                    return '<div style="color:#888;text-align:center;margin-top:40px;">暂无日志内容</div>'
                return "".join(html_logs)

            def refresh_popup():
                log_text.setHtml(get_filtered_logs_html())
                QTimer.singleShot(
                    0, lambda: log_text.moveCursor(QTextCursor.End))

            refresh_popup()

            # 工具栏交互同步
            def on_level_changed(text):
                refresh_popup()

            def on_search_changed(text):
                refresh_popup()

            level_combo.currentTextChanged.connect(on_level_changed)
            search_box.textChanged.connect(on_search_changed)
            clear_btn.clicked.connect(self.clear_logs)

            def do_export():
                file_path, _ = QFileDialog.getSaveFileName(
                    self.popup_dialog, "导出日志", "", "Text Files (*.txt);;Log Files (*.log)")
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(log_text.toPlainText())

            export_btn.clicked.connect(do_export)

            # 右键菜单
            def popup_context_menu(pos):
                menu = QMenu(self.popup_dialog)
                copy_action = menu.addAction("复制")
                select_all_action = menu.addAction("全选")
                clear_action = menu.addAction("清空")
                export_action = menu.addAction("导出")
                action = menu.exec_(log_text.mapToGlobal(pos))
                if action == copy_action:
                    log_text.copy()
                elif action == select_all_action:
                    log_text.selectAll()
                elif action == clear_action:
                    log_text.clear()
                elif action == export_action:
                    do_export()

            log_text.setContextMenuPolicy(Qt.CustomContextMenu)
            log_text.customContextMenuRequested.connect(popup_context_menu)

            def on_close():
                self.popup_dialog = None

            self.popup_dialog.finished.connect(on_close)

            # 显示弹窗并设置位置
            self.popup_dialog.show()
            QTimer.singleShot(0, lambda: self.center_dialog(
                self.popup_dialog, self.window(), offset_y=50))
            self.popup_dialog.raise_()
            self.popup_dialog.activateWindow()

        except Exception as e:
            error_msg = f"显示日志弹窗失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def center_dialog(self, dialog, parent=None, offset_y=50):
        """将弹窗居中到父窗口或屏幕，并尽量靠近上部

        Args:
            dialog: 要居中的对话框
            parent: 父窗口，如果为None则使用屏幕
            offset_y: 距离顶部的偏移量
        """
        try:
            if parent and parent.isVisible():
                # 相对于父窗口居中
                parent_geom = parent.geometry()
                dialog_geom = dialog.frameGeometry()
                x = parent_geom.center().x() - dialog_geom.width() // 2
                y = parent_geom.top() + offset_y

                # 确保弹窗不会超出父窗口边界
                x = max(parent_geom.left(), min(
                    x, parent_geom.right() - dialog_geom.width()))
                y = max(parent_geom.top(), min(
                    y, parent_geom.bottom() - dialog_geom.height()))
            else:
                # 相对于屏幕居中
                screen = dialog.screen() or dialog.parentWidget().screen()
                if screen:
                    screen_geom = screen.geometry()
                    dialog_geom = dialog.frameGeometry()
                    x = screen_geom.center().x() - dialog_geom.width() // 2
                    y = screen_geom.top() + offset_y

                    # 确保弹窗不会超出屏幕边界
                    x = max(screen_geom.left(), min(
                        x, screen_geom.right() - dialog_geom.width()))
                    y = max(screen_geom.top(), min(
                        y, screen_geom.bottom() - dialog_geom.height()))

            dialog.move(x, y)
        except Exception as e:
            self.log_manager.error(f"设置弹窗位置失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def toggle_scroll(self):
        """暂停/恢复自动滚动"""
        self.user_paused = not self.user_paused
        self.pause_scroll = self.user_paused
        if self.pause_scroll:
            self.pause_btn.setText("恢复滚动")
        else:
            self.pause_btn.setText("暂停滚动")
            # 恢复自动滚动时立即刷新并滚动到底部
            self.refresh_display(scroll_to_end=True)

    def _on_scrollbar_value_changed(self, value):
        """监听滚动条变化，自动切换自动滚动状态（仅在未手动暂停时生效）"""
        try:
            if self.user_paused:
                return  # 用户主动暂停时，自动检测不生效
            scrollbar = self.log_text.verticalScrollBar()
            if value == scrollbar.maximum():
                if self.pause_scroll:
                    self.pause_scroll = False
                    self.pause_btn.setText("暂停滚动")
            else:
                if not self.pause_scroll:
                    self.pause_scroll = True
                    self.pause_btn.setText("恢复滚动")
        except Exception as e:
            self.log_manager.error(f"滚动条监听失败: {str(e)}")

    def restore_scroll_position(self, scroll_to_end: bool = False):
        """刷新后还原滚动条位置或自动滚动到底部，供所有日志区/弹窗复用"""
        scrollbar = self.log_text.verticalScrollBar()
        if scroll_to_end:
            QTimer.singleShot(
                0, lambda: scrollbar.setValue(scrollbar.maximum()))
        elif self.pause_scroll:
            # 恢复原有滚动条相对位置（防止跳到顶部）
            def restore():
                new_max = scrollbar.maximum()
                new_value = int(self._last_scroll_ratio * new_max)
                scrollbar.setValue(new_value)
            QTimer.singleShot(0, restore)

    def refresh_display(self, scroll_to_end: bool = False):
        """根据当前过滤和搜索条件刷新日志显示（主日志区和弹窗统一HTML渲染）"""
        level_text = self.level_combo.currentText()
        search_text = self.search_box.text().strip().lower()
        html_logs = []
        for msg, lvl, ts in self._all_logs:
            if level_text != "全部":
                if level_text == "信息" and lvl.upper() != "INFO":
                    continue
                if level_text == "警告" and lvl.upper() != "WARNING":
                    continue
                if level_text == "错误" and lvl.upper() != "ERROR":
                    continue
                if level_text == "调试" and lvl.upper() != "DEBUG":
                    continue
            if search_text and search_text not in msg.lower():
                continue
            color = {
                "ERROR": "#FF0000",
                "WARNING": "#FFA500",
                "INFO": "#000000",
                "DEBUG": "#808080"
            }.get(lvl.upper(), "#000000")
            html_logs.append(
                f'<div style="text-align:left;color:{color};word-break:break-all;white-space:pre-wrap;width:100%;">[{ts}] [{lvl}] {msg}</div>')

        # 记录当前滚动条比例
        scrollbar = self.log_text.verticalScrollBar()
        old_value = scrollbar.value()
        old_max = scrollbar.maximum()
        self._last_scroll_ratio = old_value / old_max if old_max > 0 else 1.0

        self.log_text.setHtml("".join(html_logs))
        self.restore_scroll_position(scroll_to_end)
        # 更新UI状态提示
        if hasattr(self, 'scroll_status_label'):
            self.scroll_status_label.setText(
                "自动滚动中" if not self.pause_scroll else "已暂停滚动")
