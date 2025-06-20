"""
日志控件模块

提供日志显示和管理功能
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
from core.logger import LogManager, LogLevel
import traceback
from utils.theme import get_theme_manager
import json
import pandas as pd
import matplotlib.pyplot as plt


class DragHandle(QWidget):
    """顶部可拖动分隔条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(4)
        self.setCursor(Qt.SizeVerCursor)
        self._dragging = False
        self._drag_start_pos = None
        self._orig_height = None
        self.setStyleSheet(
            "background: #e0e0e0; border-top: 1px solid #bdbdbd; border-bottom: 1px solid #bdbdbd;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPos()
            self._orig_height = self.parentWidget().height() if self.parentWidget() else None
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_start_pos and self._orig_height is not None:
            dy = event.globalY() - self._drag_start_pos.y()
            new_height = max(60, self._orig_height - dy)
            if self.parentWidget():
                self.parentWidget().setFixedHeight(new_height)
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._drag_start_pos = None
        self._orig_height = None
        event.accept()


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
            # 避免self作为parent导致布局错乱，parent只允许为None或QWidget实例且不能为self
            if parent is not None and (parent is self or not isinstance(parent, QWidget)):
                parent = None
            super().__init__(parent)
            self.log_text = None  # 确保属性总是存在

            # 使用传入的日志管理器或创建新的
            self.log_manager = log_manager or LogManager()

            self.pause_scroll = False  # 显式初始化
            self.user_paused = False  # 新增：区分用户主动暂停
            self.popup_dialog = None   # 持有弹窗引用
            self._all_logs = []        # 存储所有日志 (message, level, timestamp)
            self._structured_fields = set()  # 1. 在LogWidget.__init__中初始化结构化字段缓存

            # 初始化UI
            self.init_ui()

            # 连接信号
            self.connect_signals()

            # 设置样式
            self.theme_manager = get_theme_manager()

            self.log_manager.info("日志控件初始化完成")

        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            self.log_text = None
            if self.log_manager:
                self.log_manager.error(error_msg)
                self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def init_ui(self):
        """初始化UI，动态生成结构化字段筛选器和时间区间筛选"""
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.setAlignment(Qt.AlignTop)
            self.drag_handle = DragHandle(self)
            layout.addWidget(self.drag_handle)
            toolbar_layout = QHBoxLayout()
            toolbar_layout.setContentsMargins(-2, -2, -2, -2)
            toolbar_layout.setSpacing(0)
            toolbar_layout.setAlignment(Qt.AlignTop)
            # 日志级别过滤器
            level_label = QLabel("日志级别:")
            level_label.setFixedWidth(60)
            self.level_combo = QComboBox()
            self.level_combo.addItems(["全部", "信息", "警告", "错误", "调试"])
            self.level_combo.setFixedWidth(80)
            toolbar_layout.addWidget(level_label)
            toolbar_layout.addWidget(self.level_combo)
            # event筛选器
            self.event_combo = QComboBox()
            self.event_combo.setFixedWidth(120)
            self.event_combo.addItem("全部事件")
            toolbar_layout.addWidget(self.event_combo)
            # module筛选器
            self.module_combo = QComboBox()
            self.module_combo.setFixedWidth(120)
            self.module_combo.addItem("全部模块")
            toolbar_layout.addWidget(self.module_combo)
            # 时间区间筛选
            self.time_start = QDateTimeEdit()
            self.time_start.setDateTime(QDateTime.currentDateTime())
            self.time_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.time_start.setCalendarPopup(True)
            self.time_end = QDateTimeEdit()
            self.time_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.time_end.setDateTime(QDateTime.currentDateTime().addDays(1))
            self.time_end.setCalendarPopup(True)
            toolbar_layout.addWidget(QLabel("起止时间:"))
            toolbar_layout.addWidget(self.time_start)
            toolbar_layout.addWidget(QLabel("-"))
            toolbar_layout.addWidget(self.time_end)
            # 搜索框
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("搜索日志...")
            self.search_box.setFixedWidth(180)
            toolbar_layout.addWidget(self.search_box)
            toolbar_layout.addStretch(0)
            self.scroll_status_label = QLabel("自动滚动中")
            self.scroll_status_label.setFixedWidth(60)
            toolbar_layout.addWidget(self.scroll_status_label)
            self.maximize_btn = QPushButton("最大化")
            # self.maximize_btn.setFixedWidth(70)
            self.maximize_btn.clicked.connect(self.toggle_maximize)
            toolbar_layout.addWidget(self.maximize_btn)
            self.popup_btn = QPushButton("弹窗")
            # self.popup_btn.setFixedWidth(70)
            self.popup_btn.clicked.connect(self.show_popup)
            toolbar_layout.addWidget(self.popup_btn)
            self.pause_btn = QPushButton("暂停滚动")
            # self.pause_btn.setFixedWidth(80)
            self.pause_btn.clicked.connect(self.toggle_scroll)
            toolbar_layout.addWidget(self.pause_btn)
            self.clear_button = QPushButton("清除")
            # self.clear_button.setFixedWidth(60)
            toolbar_layout.addWidget(self.clear_button)
            self.export_button = QPushButton("导出日志")
            # self.export_button.setFixedWidth(60)
            toolbar_layout.addWidget(self.export_button)
            self.visual_button = QPushButton("日志可视化")
            # self.visual_button.setFixedWidth(60)
            toolbar_layout.addWidget(self.visual_button)
            layout.addLayout(toolbar_layout)
            if self.log_text is None:
                self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setLineWrapMode(QTextEdit.WidgetWidth)
            self.log_text.setContextMenuPolicy(Qt.CustomContextMenu)
            self.log_text.customContextMenuRequested.connect(self.show_log_context_menu)
            self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.log_text.setStyleSheet(
                "margin-top: 0px; margin-bottom: 0px; font-size: 12px; line-height: 1.4; padding: 5px 16px; font-family: 'Consolas', 'Microsoft YaHei', monospace;")
            layout.addWidget(self.log_text, 1)
            self.log_text.verticalScrollBar().valueChanged.connect(self._on_scrollbar_value_changed)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.update()
            self.adjustSize()
            self.log_manager.info("日志控件UI初始化完成")
        except Exception as e:
            error_msg = f"初始化UI失败,加载默认日志控件: {str(e)}"
            if self.log_text is None:
                self.log_text = QTextEdit()
                self.log_text.setReadOnly(True)
                self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.layout().addWidget(self.log_text, 1)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.apply_style()
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            self.setVisible(True)
            self.update()
            self.adjustSize()

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
            self.visual_button.clicked.connect(self.show_log_stats)
            self.log_manager.info("信号连接完成")
        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def apply_style(self):
        pass  # 移除自定义样式，统一由主题管理器apply_theme

    def add_log(self, message: str, level: str = "INFO"):
        """添加日志，自动识别结构化字段"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                data = json.loads(message)
                self._all_logs.append((data, level, timestamp))
                self._structured_fields.update(data.keys())
            except Exception:
                self._all_logs.append((message, level, timestamp))
            self.refresh_display(scroll_to_end=not self.pause_scroll)
            if level.upper() == "ERROR":
                self.flash_error()
            self.log_added.emit(message, level)
            self.setVisible(True)
            self.update()
            if self.log_text is not None:
                QTimer.singleShot(0, lambda: self._safe_move_cursor() if hasattr(self, 'log_text') and self.log_text is not None else None)
        except Exception as e:
            error_msg = f"添加日志失败: {str(e)}"
            if self.log_text is None:
                self.log_text = QTextEdit()
                self.log_text.setReadOnly(True)
                self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.layout().addWidget(self.log_text, 1)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.apply_style()
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            self.setVisible(True)
            self.update()
            self.adjustSize()

    def flash_error(self):
        """只让日志文本区闪烁红色背景，不影响整体布局"""
        try:
            orig_style = self.log_text.styleSheet() if self.log_text else ""
            self.log_text.setStyleSheet(
                orig_style + "background-color: #ffebee;")
            QTimer.singleShot(
                500, lambda: self._safe_set_style(orig_style) if hasattr(self, 'log_text') and self.log_text is not None else None)
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
            self._all_logs.clear()
            if self.log_text is not None:
                self.log_text.clear()
            self.log_cleared.emit()
            self.log_manager.info("日志已清除")
            # 清除后强制刷新UI
            self.setVisible(True)
            self.apply_style()
            self.update()
            self.adjustSize()
        except Exception as e:
            error_msg = f"清除日志失败: {str(e)}"
            if self.log_text is None:
                self.log_text = QTextEdit()
                self.log_text.setReadOnly(True)
                self.log_text.setSizePolicy(
                    QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.log_text.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarAlwaysOff)
                self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.layout().addWidget(self.log_text, 1)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.apply_style()
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            self.setVisible(True)
            self.update()
            self.adjustSize()

    def export_logs(self, fmt="csv"):
        """导出日志到文件"""
        try:
            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志",
                "",
                "CSV Files (*.csv);;JSON Files (*.json)"
            )

            if file_path:
                # 保存日志
                logs = [l for l in self._all_logs if isinstance(l[0], dict)]
                if not logs:
                    return
                df_data = []
                for d in logs:
                    try:
                        # 安全地合并字典，避免重复键冲突
                        log_dict = d[0] if isinstance(d[0], dict) else {}
                        row_data = log_dict.copy()  # 先复制原始数据

                        # 安全地添加level和timestamp，避免重复键
                        if 'level' not in row_data:
                            row_data['level'] = d[1]
                        else:
                            row_data['log_level'] = d[1]  # 使用不同的键名

                        if 'timestamp' not in row_data:
                            row_data['timestamp'] = d[2]
                        else:
                            row_data['log_timestamp'] = d[2]  # 使用不同的键名

                        df_data.append(row_data)
                    except Exception as e:
                        self.log_manager.warning(f"处理日志数据时出错: {str(e)}")
                        continue
                df = pd.DataFrame(df_data)
                if fmt == "csv":
                    df.to_csv(file_path, index=False)
                else:
                    df.to_json(file_path, orient="records", force_ascii=False)

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
            level_label.setFixedWidth(60)
            level_label.setFixedHeight(45)
            level_label.setAlignment(Qt.AlignCenter)
            level_label.setStyleSheet("color: #1376d2;")
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

            # 设置右键菜单
            log_text.setContextMenuPolicy(Qt.CustomContextMenu)

            def show_context_menu(pos):
                """弹窗日志文本的右键菜单"""
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

            log_text.customContextMenuRequested.connect(show_context_menu)

            def on_close():
                self.popup_dialog = None

            self.popup_dialog.finished.connect(on_close)

            # 显示弹窗并设置位置
            self.popup_dialog.show()
            self.center_dialog(self.popup_dialog, self.window(), offset_y=50)
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
        try:
            if not self._is_log_text_valid():
                return

            scrollbar = self.log_text.verticalScrollBar()
            if scroll_to_end:
                QTimer.singleShot(
                    0, lambda: self._safe_scroll_to_max(scrollbar) if scrollbar is not None else None)
            elif self.pause_scroll:
                # 恢复原有滚动条相对位置（防止跳到顶部）
                def restore():
                    if scrollbar is not None:
                        new_max = scrollbar.maximum()
                        new_value = int(self._last_scroll_ratio * new_max)
                        self._safe_set_scrollbar_value(scrollbar, new_value)
                QTimer.singleShot(0, restore)
        except Exception as e:
            self.log_manager.error(f"恢复滚动位置失败: {str(e)}")

    def refresh_display(self, scroll_to_end: bool = False):
        """根据所有筛选条件刷新日志显示"""
        level_text = self.level_combo.currentText()
        event_text = self.event_combo.currentText()
        module_text = self.module_combo.currentText()
        search_text = self.search_box.text().strip().lower()
        start_dt = self.time_start.dateTime().toPyDateTime()
        end_dt = self.time_end.dateTime().toPyDateTime()
        html_logs = []
        for msg, lvl, ts in self._all_logs:
            # 结构化日志
            if isinstance(msg, dict):
                if level_text != "全部":
                    if level_text == "信息" and lvl.upper() != "INFO":
                        continue
                    if level_text == "警告" and lvl.upper() != "WARNING":
                        continue
                    if level_text == "错误" and lvl.upper() != "ERROR":
                        continue
                    if level_text == "调试" and lvl.upper() != "DEBUG":
                        continue
                if event_text != "全部事件" and msg.get("event", "") != event_text:
                    continue
                if module_text != "全部模块" and msg.get("module", "") != module_text:
                    continue
                log_time = pd.to_datetime(ts)
                if log_time < start_dt or log_time > end_dt:
                    continue
                if search_text and search_text not in json.dumps(msg, ensure_ascii=False).lower():
                    continue
                color = {
                    "ERROR": "#FF0000",
                    "WARNING": "#FFA500",
                    "INFO": "#000000",
                    "DEBUG": "#808080"
                }.get(lvl.upper(), "#000000")
                html_logs.append(
                    f'<div style="text-align:left;color:{color};word-break:break-all;white-space:pre-wrap;width:100%;">[{ts}] [{lvl}] {json.dumps(msg, ensure_ascii=False)}</div>')
            else:
                # 未结构化日志
                if level_text != "全部":
                    if level_text == "信息" and lvl.upper() != "INFO":
                        continue
                    if level_text == "警告" and lvl.upper() != "WARNING":
                        continue
                    if level_text == "错误" and lvl.upper() != "ERROR":
                        continue
                    if level_text == "调试" and lvl.upper() != "DEBUG":
                        continue
                log_time = pd.to_datetime(ts)
                if log_time < start_dt or log_time > end_dt:
                    continue
                if search_text and search_text not in str(msg).lower():
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
            html_logs = ['<div style="color:#888;text-align:center;margin-top:40px;">暂无日志内容</div>']
        scrollbar = self.log_text.verticalScrollBar()
        old_value = scrollbar.value()
        old_max = scrollbar.maximum()
        self._last_scroll_ratio = old_value / old_max if old_max > 0 else 1.0
        if self.log_text is not None:
            self.log_text.setHtml("".join(html_logs))
            if scroll_to_end or not self.pause_scroll:
                QTimer.singleShot(0, lambda: self._safe_move_cursor() if hasattr(self, 'log_text') and self.log_text is not None else None)

    def refresh(self) -> None:
        """
        刷新日志控件内容，异常只记录日志不抛出。
        """
        try:
            self.refresh_display(scroll_to_end=True)
        except Exception as e:
            self.log_manager.error(f"刷新日志控件失败: {str(e)}")

    def update(self) -> None:
        """
        只做Qt刷新，不再递归调用refresh。
        """
        QWidget.update(self)

    def reload(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def show_log_stats(self):
        """嵌入式日志统计图，支持交互"""
        try:
            self.log_manager.info("开始显示日志统计可视化")

            # 检查是否有日志数据
            if not self._all_logs:
                self.log_manager.warning("没有日志数据可供统计")
                QMessageBox.information(self, "提示", "暂无日志数据可供统计分析")
                return

            # 过滤结构化日志数据
            logs = [l for l in self._all_logs if isinstance(l[0], dict)]
            if not logs:
                self.log_manager.warning("没有结构化日志数据可供统计")
                # 如果没有结构化日志，显示基本统计
                self._show_basic_log_stats()
                return

            self.log_manager.info(f"找到 {len(logs)} 条结构化日志数据")

            # 创建DataFrame
            df_data = []
            for d in logs:
                try:
                    # 安全地合并字典，避免重复键冲突
                    log_dict = d[0] if isinstance(d[0], dict) else {}
                    row_data = log_dict.copy()  # 先复制原始数据

                    # 安全地添加level和timestamp，避免重复键
                    if 'level' not in row_data:
                        row_data['level'] = d[1]
                    else:
                        row_data['log_level'] = d[1]  # 使用不同的键名

                    if 'timestamp' not in row_data:
                        row_data['timestamp'] = d[2]
                    else:
                        row_data['log_timestamp'] = d[2]  # 使用不同的键名

                    df_data.append(row_data)
                except Exception as e:
                    self.log_manager.warning(f"处理日志数据时出错: {str(e)}")
                    continue

            if not df_data:
                self.log_manager.warning("无法处理日志数据")
                return

            df = pd.DataFrame(df_data)
            self.log_manager.info(f"创建DataFrame成功，包含 {len(df)} 行数据")

            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("日志统计可视化")
            layout = QVBoxLayout(dialog)

            try:
                # 导入matplotlib组件
                from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
                from matplotlib.figure import Figure

                # 创建图表
                fig = Figure(figsize=(12, 8))
                canvas = FigureCanvas(fig)
                layout.addWidget(canvas)

                # 创建子图
                ax1 = fig.add_subplot(221)
                ax2 = fig.add_subplot(222)
                ax3 = fig.add_subplot(212)

                # 绘制事件分布
                if "event" in df.columns and not df["event"].empty:
                    try:
                        event_counts = df["event"].value_counts()
                        if len(event_counts) > 0:
                            event_counts.plot(kind="bar", ax=ax1, title="事件分布")
                            ax1.tick_params(axis='x', rotation=45)
                        else:
                            ax1.text(0.5, 0.5, '无事件数据', ha='center', va='center', transform=ax1.transAxes)
                            ax1.set_title("事件分布")
                    except Exception as e:
                        self.log_manager.error(f"绘制事件分布失败: {str(e)}")
                        ax1.text(0.5, 0.5, '事件分布绘制失败', ha='center', va='center', transform=ax1.transAxes)
                        ax1.set_title("事件分布")
                else:
                    ax1.text(0.5, 0.5, '无事件数据', ha='center', va='center', transform=ax1.transAxes)
                    ax1.set_title("事件分布")

                # 绘制级别分布
                if "level" in df.columns and not df["level"].empty:
                    try:
                        level_counts = df["level"].value_counts()
                        if len(level_counts) > 0:
                            level_counts.plot(kind="pie", ax=ax2, autopct="%1.1f%%", title="日志级别分布")
                        else:
                            ax2.text(0.5, 0.5, '无级别数据', ha='center', va='center', transform=ax2.transAxes)
                            ax2.set_title("日志级别分布")
                    except Exception as e:
                        self.log_manager.error(f"绘制级别分布失败: {str(e)}")
                        ax2.text(0.5, 0.5, '级别分布绘制失败', ha='center', va='center', transform=ax2.transAxes)
                        ax2.set_title("日志级别分布")
                else:
                    ax2.text(0.5, 0.5, '无级别数据', ha='center', va='center', transform=ax2.transAxes)
                    ax2.set_title("日志级别分布")

                # 绘制时间趋势
                if "timestamp" in df.columns and not df["timestamp"].empty:
                    try:
                        df["timestamp"] = pd.to_datetime(df["timestamp"])
                        time_series = df.set_index("timestamp").resample("min").size()
                        if len(time_series) > 0:
                            time_series.plot(ax=ax3, title="日志时间趋势")
                            ax3.tick_params(axis='x', rotation=45)
                        else:
                            ax3.text(0.5, 0.5, '无时间数据', ha='center', va='center', transform=ax3.transAxes)
                            ax3.set_title("日志时间趋势")
                    except Exception as e:
                        self.log_manager.error(f"绘制时间趋势失败: {str(e)}")
                        ax3.text(0.5, 0.5, '时间趋势绘制失败', ha='center', va='center', transform=ax3.transAxes)
                        ax3.set_title("日志时间趋势")
                else:
                    ax3.text(0.5, 0.5, '无时间数据', ha='center', va='center', transform=ax3.transAxes)
                    ax3.set_title("日志时间趋势")

                fig.tight_layout()

                # 支持导出图片
                btn_export = QPushButton("导出统计图")

                def do_export():
                    try:
                        file_path, _ = QFileDialog.getSaveFileName(dialog, "导出统计图", "", "PNG Files (*.png)")
                        if file_path:
                            fig.savefig(file_path, dpi=300, bbox_inches='tight')
                            self.log_manager.info(f"统计图已导出到: {file_path}")
                            QMessageBox.information(dialog, "成功", f"统计图已导出到:\n{file_path}")
                    except Exception as e:
                        self.log_manager.error(f"导出统计图失败: {str(e)}")
                        QMessageBox.warning(dialog, "错误", f"导出统计图失败: {str(e)}")

                btn_export.clicked.connect(do_export)
                layout.addWidget(btn_export)

                dialog.setLayout(layout)
                dialog.resize(900, 700)

                self.log_manager.info("日志统计可视化对话框创建成功")
                dialog.exec_()

            except ImportError as e:
                self.log_manager.error(f"matplotlib导入失败: {str(e)}")
                QMessageBox.warning(self, "错误", "无法导入matplotlib库，请确保已安装matplotlib")

        except Exception as e:
            error_msg = f"显示日志统计失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            QMessageBox.warning(self, "错误", error_msg)

    def _show_basic_log_stats(self):
        """显示基本日志统计（当没有结构化日志时）"""
        try:
            # 统计基本信息
            total_logs = len(self._all_logs)
            level_counts = {}
            for msg, level, ts in self._all_logs:
                level_counts[level] = level_counts.get(level, 0) + 1

            # 创建简单的统计对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("基本日志统计")
            layout = QVBoxLayout(dialog)

            # 添加统计信息
            info_text = f"总日志数: {total_logs}\n\n级别分布:\n"
            for level, count in sorted(level_counts.items()):
                info_text += f"  {level}: {count}\n"

            text_edit = QTextEdit()
            text_edit.setPlainText(info_text)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)

            # 关闭按钮
            btn_close = QPushButton("关闭")
            btn_close.clicked.connect(dialog.accept)
            layout.addWidget(btn_close)

            dialog.resize(400, 300)
            dialog.exec_()

        except Exception as e:
            self.log_manager.error(f"显示基本日志统计失败: {str(e)}")

    def _safe_move_cursor(self):
        """安全地移动光标到末尾，处理Qt对象生命周期问题"""
        try:
            if hasattr(self, 'log_text') and self.log_text is not None:
                # 尝试检查对象是否仍然有效
                try:
                    # 通过调用一个简单的方法来检查对象是否有效
                    self.log_text.document()
                    self.log_text.moveCursor(QTextCursor.End)
                except RuntimeError:
                    # Qt对象已被删除，忽略错误
                    pass
        except Exception:
            # 任何其他异常也忽略
            pass

    def _safe_set_style(self, style):
        """安全地设置日志文本区的样式"""
        try:
            if hasattr(self, 'log_text') and self.log_text is not None:
                self.log_text.setStyleSheet(style)
        except Exception:
            # 忽略所有异常，包括RuntimeError
            pass

    def _is_log_text_valid(self):
        """检查log_text是否有效"""
        try:
            if hasattr(self, 'log_text') and self.log_text is not None:
                # 通过调用一个简单的方法来检查对象是否有效
                self.log_text.document()
                return True
        except (RuntimeError, AttributeError):
            pass
        return False

    def _safe_scroll_to_max(self, scrollbar):
        """安全地滚动到最大值"""
        try:
            if scrollbar is not None:
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass

    def _safe_set_scrollbar_value(self, scrollbar, value):
        """安全地设置滚动条值"""
        try:
            if scrollbar is not None:
                scrollbar.setValue(value)
        except Exception:
            pass
