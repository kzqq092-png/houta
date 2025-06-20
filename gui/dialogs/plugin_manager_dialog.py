"""
插件管理器对话框
提供插件的加载、卸载、激活、停用等管理功能
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QTextEdit, QSplitter, QHeaderView, QMessageBox,
    QProgressBar, QComboBox, QLineEdit, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont
from typing import Optional
import traceback


class PluginManagerDialog(QDialog):
    """插件管理器对话框"""

    def __init__(self, plugin_manager, parent=None):
        """
        初始化插件管理器对话框

        Args:
            plugin_manager: 插件管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.parent_window = parent
        self.log_manager = getattr(parent, 'log_manager', None)

        # 设置窗口属性
        self.setWindowTitle("插件管理器")
        self.setModal(True)
        self.resize(800, 600)

        # 初始化UI
        self.init_ui()

        # 加载插件列表
        self.refresh_plugin_list()

    def init_ui(self):
        """初始化用户界面"""
        try:
            # 主布局
            main_layout = QVBoxLayout(self)

            # 创建分割器
            splitter = QSplitter(Qt.Horizontal)
            main_layout.addWidget(splitter)

            # 左侧：插件列表
            left_widget = self.create_plugin_list_widget()
            splitter.addWidget(left_widget)

            # 右侧：插件详情
            right_widget = self.create_plugin_detail_widget()
            splitter.addWidget(right_widget)

            # 设置分割器比例
            splitter.setStretchFactor(0, 2)
            splitter.setStretchFactor(1, 1)

            # 底部按钮
            button_layout = self.create_button_layout()
            main_layout.addLayout(button_layout)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化插件管理器对话框失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def create_plugin_list_widget(self):
        """创建插件列表控件"""
        group = QGroupBox("插件列表")
        layout = QVBoxLayout(group)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入插件名称或描述...")
        self.search_edit.textChanged.connect(self.filter_plugins)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # 状态筛选
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "已加载", "已激活", "错误", "未加载"])
        self.status_combo.currentTextChanged.connect(self.filter_plugins)
        filter_layout.addWidget(self.status_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 插件表格
        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(5)
        self.plugin_table.setHorizontalHeaderLabels([
            "名称", "版本", "状态", "描述", "作者"
        ])

        # 设置表格属性
        header = self.plugin_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.plugin_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.plugin_table.setAlternatingRowColors(True)
        self.plugin_table.itemSelectionChanged.connect(self.on_plugin_selected)

        layout.addWidget(self.plugin_table)

        return group

    def create_plugin_detail_widget(self):
        """创建插件详情控件"""
        group = QGroupBox("插件详情")
        layout = QVBoxLayout(group)

        # 插件信息表单
        form_layout = QFormLayout()

        self.name_label = QLabel("未选择")
        self.name_label.setFont(QFont("", 10, QFont.Bold))
        form_layout.addRow("名称:", self.name_label)

        self.version_label = QLabel("-")
        form_layout.addRow("版本:", self.version_label)

        self.status_label = QLabel("-")
        form_layout.addRow("状态:", self.status_label)

        self.author_label = QLabel("-")
        form_layout.addRow("作者:", self.author_label)

        self.dependencies_label = QLabel("-")
        form_layout.addRow("依赖:", self.dependencies_label)

        layout.addLayout(form_layout)

        # 插件描述
        layout.addWidget(QLabel("描述:"))
        self.description_text = QTextEdit()
        self.description_text.setMaximumHeight(100)
        self.description_text.setReadOnly(True)
        layout.addWidget(self.description_text)

        # 错误信息
        layout.addWidget(QLabel("错误信息:"))
        self.error_text = QTextEdit()
        self.error_text.setMaximumHeight(80)
        self.error_text.setReadOnly(True)
        layout.addWidget(self.error_text)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.load_btn = QPushButton("加载")
        self.load_btn.clicked.connect(self.load_plugin)
        button_layout.addWidget(self.load_btn)

        self.unload_btn = QPushButton("卸载")
        self.unload_btn.clicked.connect(self.unload_plugin)
        button_layout.addWidget(self.unload_btn)

        self.activate_btn = QPushButton("激活")
        self.activate_btn.clicked.connect(self.activate_plugin)
        button_layout.addWidget(self.activate_btn)

        self.deactivate_btn = QPushButton("停用")
        self.deactivate_btn.clicked.connect(self.deactivate_plugin)
        button_layout.addWidget(self.deactivate_btn)

        self.reload_btn = QPushButton("重新加载")
        self.reload_btn.clicked.connect(self.reload_plugin)
        button_layout.addWidget(self.reload_btn)

        layout.addLayout(button_layout)

        return group

    def create_button_layout(self):
        """创建底部按钮布局"""
        layout = QHBoxLayout()

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_plugin_list)
        layout.addWidget(refresh_btn)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return layout

    def refresh_plugin_list(self):
        """刷新插件列表"""
        try:
            # 重新扫描插件
            self.plugin_manager.scan_plugins()

            # 获取插件列表
            plugins = self.plugin_manager.list_plugins()

            # 清空表格
            self.plugin_table.setRowCount(0)

            # 填充表格
            for plugin in plugins:
                row = self.plugin_table.rowCount()
                self.plugin_table.insertRow(row)

                # 名称
                name_item = QTableWidgetItem(plugin["name"])
                name_item.setData(Qt.UserRole, plugin)
                self.plugin_table.setItem(row, 0, name_item)

                # 版本
                self.plugin_table.setItem(row, 1, QTableWidgetItem(plugin["version"]))

                # 状态
                status_item = QTableWidgetItem(plugin["status"])
                # 根据状态设置颜色
                if plugin["status"] == "active":
                    status_item.setBackground(Qt.green)
                elif plugin["status"] == "loaded":
                    status_item.setBackground(Qt.yellow)
                elif plugin["status"] == "error":
                    status_item.setBackground(Qt.red)
                self.plugin_table.setItem(row, 2, status_item)

                # 描述
                self.plugin_table.setItem(row, 3, QTableWidgetItem(plugin["description"]))

                # 作者
                self.plugin_table.setItem(row, 4, QTableWidgetItem(plugin["author"]))

            if self.log_manager:
                self.log_manager.info(f"插件列表已刷新，共 {len(plugins)} 个插件")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"刷新插件列表失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"刷新插件列表失败: {str(e)}")

    def filter_plugins(self):
        """筛选插件"""
        try:
            search_text = self.search_edit.text().lower()
            status_filter = self.status_combo.currentText()

            for row in range(self.plugin_table.rowCount()):
                item = self.plugin_table.item(row, 0)
                plugin_data = item.data(Qt.UserRole)

                # 文本筛选
                text_match = (
                    search_text in plugin_data["name"].lower() or
                    search_text in plugin_data["description"].lower()
                )

                # 状态筛选
                status_match = (
                    status_filter == "全部" or
                    (status_filter == "已加载" and plugin_data["status"] in ["loaded", "active"]) or
                    (status_filter == "已激活" and plugin_data["status"] == "active") or
                    (status_filter == "错误" and plugin_data["status"] == "error") or
                    (status_filter == "未加载" and plugin_data["status"] == "unloaded")
                )

                # 显示或隐藏行
                self.plugin_table.setRowHidden(row, not (text_match and status_match))

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"筛选插件失败: {str(e)}")

    def on_plugin_selected(self):
        """插件选择事件"""
        try:
            current_row = self.plugin_table.currentRow()
            if current_row < 0:
                self.clear_plugin_details()
                return

            item = self.plugin_table.item(current_row, 0)
            plugin_data = item.data(Qt.UserRole)

            # 更新详情显示
            self.update_plugin_details(plugin_data)

            # 更新按钮状态
            self.update_button_states(plugin_data["status"])

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"处理插件选择事件失败: {str(e)}")

    def update_plugin_details(self, plugin_data):
        """更新插件详情显示"""
        try:
            self.name_label.setText(plugin_data["name"])
            self.version_label.setText(plugin_data["version"])
            self.status_label.setText(plugin_data["status"])
            self.author_label.setText(plugin_data["author"])
            self.dependencies_label.setText(", ".join(plugin_data["dependencies"]))
            self.description_text.setPlainText(plugin_data["description"])
            self.error_text.setPlainText(plugin_data.get("error_message", ""))

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新插件详情失败: {str(e)}")

    def clear_plugin_details(self):
        """清空插件详情"""
        self.name_label.setText("未选择")
        self.version_label.setText("-")
        self.status_label.setText("-")
        self.author_label.setText("-")
        self.dependencies_label.setText("-")
        self.description_text.clear()
        self.error_text.clear()

    def update_button_states(self, status):
        """更新按钮状态"""
        self.load_btn.setEnabled(status in ["unloaded", "error"])
        self.unload_btn.setEnabled(status in ["loaded", "active", "error"])
        self.activate_btn.setEnabled(status == "loaded")
        self.deactivate_btn.setEnabled(status == "active")
        self.reload_btn.setEnabled(status in ["loaded", "active", "error"])

    def get_selected_plugin_name(self):
        """获取选中的插件名称"""
        current_row = self.plugin_table.currentRow()
        if current_row < 0:
            return None

        item = self.plugin_table.item(current_row, 0)
        plugin_data = item.data(Qt.UserRole)
        return plugin_data["name"]

    def load_plugin(self):
        """加载插件"""
        plugin_name = self.get_selected_plugin_name()
        if not plugin_name:
            return

        try:
            if self.plugin_manager.load_plugin(plugin_name):
                QMessageBox.information(self, "成功", f"插件 '{plugin_name}' 加载成功")
                self.refresh_plugin_list()
            else:
                QMessageBox.warning(self, "失败", f"插件 '{plugin_name}' 加载失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载插件失败: {str(e)}")

    def unload_plugin(self):
        """卸载插件"""
        plugin_name = self.get_selected_plugin_name()
        if not plugin_name:
            return

        try:
            if self.plugin_manager.unload_plugin(plugin_name):
                QMessageBox.information(self, "成功", f"插件 '{plugin_name}' 卸载成功")
                self.refresh_plugin_list()
            else:
                QMessageBox.warning(self, "失败", f"插件 '{plugin_name}' 卸载失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"卸载插件失败: {str(e)}")

    def activate_plugin(self):
        """激活插件"""
        plugin_name = self.get_selected_plugin_name()
        if not plugin_name:
            return

        try:
            if self.plugin_manager.activate_plugin(plugin_name):
                QMessageBox.information(self, "成功", f"插件 '{plugin_name}' 激活成功")
                self.refresh_plugin_list()
            else:
                QMessageBox.warning(self, "失败", f"插件 '{plugin_name}' 激活失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"激活插件失败: {str(e)}")

    def deactivate_plugin(self):
        """停用插件"""
        plugin_name = self.get_selected_plugin_name()
        if not plugin_name:
            return

        try:
            if self.plugin_manager.deactivate_plugin(plugin_name):
                QMessageBox.information(self, "成功", f"插件 '{plugin_name}' 停用成功")
                self.refresh_plugin_list()
            else:
                QMessageBox.warning(self, "失败", f"插件 '{plugin_name}' 停用失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"停用插件失败: {str(e)}")

    def reload_plugin(self):
        """重新加载插件"""
        plugin_name = self.get_selected_plugin_name()
        if not plugin_name:
            return

        try:
            if self.plugin_manager.reload_plugin(plugin_name):
                QMessageBox.information(self, "成功", f"插件 '{plugin_name}' 重新加载成功")
                self.refresh_plugin_list()
            else:
                QMessageBox.warning(self, "失败", f"插件 '{plugin_name}' 重新加载失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"重新加载插件失败: {str(e)}")
