"""
插件管理主界面对话框

提供插件的统一管理界面，包括：
- 插件列表显示
- 插件状态管理
- 插件配置
- 插件监控
- 插件更新
"""

import os
import json
from typing import Dict, List, Optional, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSplitter,
    QProgressBar, QMessageBox, QWidget, QTabWidget,
    QTextEdit, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem, QToolBar, QAction, QMenu, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

from core.plugin_manager import PluginManager, PluginInfo, PluginStatus, PluginType, PluginCategory
from plugins.plugin_interface import PluginMetadata
from core.logger import get_logger

logger = get_logger(__name__)


class PluginStatusWidget(QWidget):
    """插件状态小部件"""

    def __init__(self, plugin_info: PluginInfo, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 插件名称
        name_label = QLabel(self.plugin_info.name)
        name_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(name_label)

        # 版本
        version_label = QLabel(f"v{self.plugin_info.version}")
        version_label.setStyleSheet("color: #666;")
        layout.addWidget(version_label)

        # 状态指示器
        status_label = QLabel()
        status_color = self._get_status_color(self.plugin_info.status)
        status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                border-radius: 6px;
                padding: 2px 8px;
                color: white;
                font-size: 10px;
            }}
        """)
        status_label.setText(self._get_status_text(self.plugin_info.status))
        layout.addWidget(status_label)

        layout.addStretch()

        # 操作按钮
        if self.plugin_info.status == PluginStatus.LOADED:
            enable_btn = QPushButton("启用")
            enable_btn.clicked.connect(self.enable_plugin)
            layout.addWidget(enable_btn)
        elif self.plugin_info.status == PluginStatus.ENABLED:
            disable_btn = QPushButton("禁用")
            disable_btn.clicked.connect(self.disable_plugin)
            layout.addWidget(disable_btn)

        config_btn = QPushButton("配置")
        config_btn.clicked.connect(self.configure_plugin)
        layout.addWidget(config_btn)

    def _get_status_color(self, status: PluginStatus) -> str:
        """获取状态颜色"""
        color_map = {
            PluginStatus.UNLOADED: "#666666",
            PluginStatus.LOADED: "#17a2b8",
            PluginStatus.ENABLED: "#28a745",
            PluginStatus.DISABLED: "#ffc107",
            PluginStatus.ERROR: "#dc3545"
        }
        return color_map.get(status, "#666666")

    def _get_status_text(self, status: PluginStatus) -> str:
        """获取状态文本"""
        text_map = {
            PluginStatus.UNLOADED: "未加载",
            PluginStatus.LOADED: "已加载",
            PluginStatus.ENABLED: "已启用",
            PluginStatus.DISABLED: "已禁用",
            PluginStatus.ERROR: "错误"
        }
        return text_map.get(status, "未知")

    def enable_plugin(self):
        """启用插件"""
        # 发送启用信号
        self.parent().parent().enable_plugin(self.plugin_info.name)

    def disable_plugin(self):
        """禁用插件"""
        # 发送禁用信号
        self.parent().parent().disable_plugin(self.plugin_info.name)

    def configure_plugin(self):
        """配置插件"""
        # 发送配置信号
        self.parent().parent().configure_plugin(self.plugin_info.name)


class PluginConfigDialog(QDialog):
    """插件配置对话框"""

    def __init__(self, plugin_info: PluginInfo, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        self.plugin_manager = plugin_manager
        self.config_widgets = {}
        self.init_ui()
        self.load_config()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"配置插件 - {self.plugin_info.name}")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # 插件信息
        info_group = QGroupBox("插件信息")
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("名称:"), 0, 0)
        info_layout.addWidget(QLabel(self.plugin_info.name), 0, 1)

        info_layout.addWidget(QLabel("版本:"), 1, 0)
        info_layout.addWidget(QLabel(self.plugin_info.version), 1, 1)

        info_layout.addWidget(QLabel("作者:"), 2, 0)
        info_layout.addWidget(QLabel(self.plugin_info.author), 2, 1)

        info_layout.addWidget(QLabel("描述:"), 3, 0)
        desc_label = QLabel(self.plugin_info.description)
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label, 3, 1)

        layout.addWidget(info_group)

        # 配置选项
        config_group = QGroupBox("配置选项")
        self.config_layout = QGridLayout(config_group)
        layout.addWidget(config_group)

        # 按钮
        button_layout = QHBoxLayout()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_config)
        button_layout.addWidget(reset_btn)

        layout.addLayout(button_layout)

    def load_config(self):
        """加载配置"""
        try:
            config = self.plugin_info.config

            # 动态创建配置控件
            row = 0
            for key, value in config.items():
                if key.startswith('_'):  # 跳过私有配置
                    continue

                label = QLabel(f"{key}:")
                self.config_layout.addWidget(label, row, 0)

                if isinstance(value, bool):
                    widget = QCheckBox()
                    widget.setChecked(value)
                elif isinstance(value, int):
                    widget = QSpinBox()
                    widget.setRange(-999999, 999999)
                    widget.setValue(value)
                elif isinstance(value, float):
                    widget = QDoubleSpinBox()
                    widget.setRange(-999999.0, 999999.0)
                    widget.setValue(value)
                elif isinstance(value, str):
                    widget = QLineEdit()
                    widget.setText(value)
                else:
                    widget = QLineEdit()
                    widget.setText(str(value))

                self.config_layout.addWidget(widget, row, 1)
                self.config_widgets[key] = widget
                row += 1

        except Exception as e:
            logger.error(f"加载插件配置失败: {e}")
            QMessageBox.warning(self, "警告", f"加载配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            new_config = {}

            for key, widget in self.config_widgets.items():
                if isinstance(widget, QCheckBox):
                    new_config[key] = widget.isChecked()
                elif isinstance(widget, QSpinBox):
                    new_config[key] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    new_config[key] = widget.value()
                elif isinstance(widget, QLineEdit):
                    text = widget.text()
                    # 尝试转换为原始类型
                    original_value = self.plugin_info.config.get(key)
                    if isinstance(original_value, (int, float)):
                        try:
                            new_config[key] = type(original_value)(text)
                        except ValueError:
                            new_config[key] = text
                    else:
                        new_config[key] = text

            # 更新插件配置
            self.plugin_info.config.update(new_config)

            # 通知插件管理器
            if hasattr(self.plugin_manager, 'update_plugin_config'):
                self.plugin_manager.update_plugin_config(
                    self.plugin_info.name, new_config)

            QMessageBox.information(self, "成功", "配置已保存")
            self.accept()

        except Exception as e:
            logger.error(f"保存插件配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")

    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(self, "确认", "确定要重置配置吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.load_config()


class PluginManagerDialog(QDialog):
    """插件管理主界面对话框"""

    # 信号定义
    plugin_enabled = pyqtSignal(str)
    plugin_disabled = pyqtSignal(str)
    plugin_configured = pyqtSignal(str)

    def __init__(self, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.plugin_widgets = {}
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_plugins)
        self.init_ui()
        self.load_plugins()

        # 启动定时刷新
        self.timer.start(5000)  # 每5秒刷新一次

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("插件管理器")
        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)

        # 选项卡
        self.tab_widget = QTabWidget()

        # 插件列表选项卡
        self.plugins_tab = self.create_plugins_tab()
        self.tab_widget.addTab(self.plugins_tab, "插件列表")

        # 插件监控选项卡
        self.monitor_tab = self.create_monitor_tab()
        self.tab_widget.addTab(self.monitor_tab, "性能监控")

        # 插件日志选项卡
        self.logs_tab = self.create_logs_tab()
        self.tab_widget.addTab(self.logs_tab, "日志")

        layout.addWidget(self.tab_widget)

        # 状态栏
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

        self.update_status()

    def create_toolbar(self) -> QToolBar:
        """创建工具栏"""
        toolbar = QToolBar()

        # 刷新按钮
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_plugins)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # 全部启用
        enable_all_action = QAction("全部启用", self)
        enable_all_action.triggered.connect(self.enable_all_plugins)
        toolbar.addAction(enable_all_action)

        # 全部禁用
        disable_all_action = QAction("全部禁用", self)
        disable_all_action.triggered.connect(self.disable_all_plugins)
        toolbar.addAction(disable_all_action)

        toolbar.addSeparator()

        # 插件市场
        market_action = QAction("插件市场", self)
        market_action.triggered.connect(self.open_plugin_market)
        toolbar.addAction(market_action)

        return toolbar

    def create_plugins_tab(self) -> QWidget:
        """创建插件列表选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入插件名称或描述...")
        self.search_edit.textChanged.connect(self.filter_plugins)
        search_layout.addWidget(self.search_edit)

        # 类型过滤
        search_layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", "")
        for plugin_type in PluginType:
            self.type_combo.addItem(plugin_type.value, plugin_type.value)
        self.type_combo.currentTextChanged.connect(self.filter_plugins)
        search_layout.addWidget(self.type_combo)

        # 状态过滤
        search_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", "")
        for status in PluginStatus:
            self.status_combo.addItem(status.value, status.value)
        self.status_combo.currentTextChanged.connect(self.filter_plugins)
        search_layout.addWidget(self.status_combo)

        layout.addLayout(search_layout)

        # 插件列表
        self.plugins_list = QListWidget()
        layout.addWidget(self.plugins_list)

        return widget

    def create_monitor_tab(self) -> QWidget:
        """创建性能监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QGridLayout(stats_group)

        self.total_plugins_label = QLabel("0")
        self.enabled_plugins_label = QLabel("0")
        self.disabled_plugins_label = QLabel("0")
        self.error_plugins_label = QLabel("0")

        stats_layout.addWidget(QLabel("总插件数:"), 0, 0)
        stats_layout.addWidget(self.total_plugins_label, 0, 1)

        stats_layout.addWidget(QLabel("已启用:"), 1, 0)
        stats_layout.addWidget(self.enabled_plugins_label, 1, 1)

        stats_layout.addWidget(QLabel("已禁用:"), 2, 0)
        stats_layout.addWidget(self.disabled_plugins_label, 2, 1)

        stats_layout.addWidget(QLabel("错误:"), 3, 0)
        stats_layout.addWidget(self.error_plugins_label, 3, 1)

        layout.addWidget(stats_group)

        # 性能图表区域
        perf_group = QGroupBox("性能监控")
        perf_layout = QVBoxLayout(perf_group)

        self.perf_text = QTextEdit()
        self.perf_text.setReadOnly(True)
        perf_layout.addWidget(self.perf_text)

        layout.addWidget(perf_group)

        return widget

    def create_logs_tab(self) -> QWidget:
        """创建日志选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 日志控制
        control_layout = QHBoxLayout()

        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.clear_logs)
        control_layout.addWidget(clear_btn)

        control_layout.addStretch()

        # 日志级别
        control_layout.addWidget(QLabel("级别:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        control_layout.addWidget(self.log_level_combo)

        layout.addLayout(control_layout)

        # 日志显示
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.logs_text)

        return widget

    def load_plugins(self):
        """加载插件列表"""
        try:
            self.plugins_list.clear()
            self.plugin_widgets.clear()

            # 获取所有插件
            plugins = self.plugin_manager.get_all_plugin_metadata()

            for plugin_name, metadata in plugins.items():
                # 创建插件信息对象
                plugin_info = PluginInfo(
                    name=plugin_name,
                    version=metadata.get('version', '1.0.0'),
                    description=metadata.get('description', ''),
                    author=metadata.get('author', ''),
                    path=metadata.get('path', ''),
                    status=PluginStatus.ENABLED if self.plugin_manager.is_plugin_loaded(
                        plugin_name) else PluginStatus.UNLOADED,
                    config=metadata.get('config', {}),
                    dependencies=metadata.get('dependencies', [])
                )

                # 创建插件状态小部件
                plugin_widget = PluginStatusWidget(plugin_info)

                # 创建列表项
                list_item = QListWidgetItem()
                list_item.setSizeHint(plugin_widget.sizeHint())

                self.plugins_list.addItem(list_item)
                self.plugins_list.setItemWidget(list_item, plugin_widget)

                self.plugin_widgets[plugin_name] = plugin_widget

            self.update_status()

        except Exception as e:
            logger.error(f"加载插件列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载插件列表失败: {e}")

    def refresh_plugins(self):
        """刷新插件列表"""
        self.load_plugins()
        self.update_monitor_stats()

    def filter_plugins(self):
        """过滤插件"""
        search_text = self.search_edit.text().lower()
        plugin_type = self.type_combo.currentData()
        status = self.status_combo.currentData()

        for i in range(self.plugins_list.count()):
            item = self.plugins_list.item(i)
            widget = self.plugins_list.itemWidget(item)

            if widget and isinstance(widget, PluginStatusWidget):
                plugin_info = widget.plugin_info

                # 文本匹配
                text_match = (search_text in plugin_info.name.lower() or
                              search_text in plugin_info.description.lower())

                # 类型匹配
                type_match = (not plugin_type or
                              (plugin_info.plugin_type and plugin_info.plugin_type.value == plugin_type))

                # 状态匹配
                status_match = (
                    not status or plugin_info.status.value == status)

                item.setHidden(
                    not (text_match and type_match and status_match))

    def enable_plugin(self, plugin_name: str):
        """启用插件"""
        try:
            # 这里应该调用插件管理器的启用方法
            # self.plugin_manager.enable_plugin(plugin_name)
            self.plugin_enabled.emit(plugin_name)
            self.add_log(f"插件 {plugin_name} 已启用")
            self.refresh_plugins()

        except Exception as e:
            logger.error(f"启用插件失败: {e}")
            QMessageBox.critical(self, "错误", f"启用插件失败: {e}")

    def disable_plugin(self, plugin_name: str):
        """禁用插件"""
        try:
            # 这里应该调用插件管理器的禁用方法
            # self.plugin_manager.disable_plugin(plugin_name)
            self.plugin_disabled.emit(plugin_name)
            self.add_log(f"插件 {plugin_name} 已禁用")
            self.refresh_plugins()

        except Exception as e:
            logger.error(f"禁用插件失败: {e}")
            QMessageBox.critical(self, "错误", f"禁用插件失败: {e}")

    def configure_plugin(self, plugin_name: str):
        """配置插件"""
        try:
            # 获取插件信息
            if plugin_name in self.plugin_widgets:
                plugin_widget = self.plugin_widgets[plugin_name]
                plugin_info = plugin_widget.plugin_info

                # 打开配置对话框
                config_dialog = PluginConfigDialog(
                    plugin_info, self.plugin_manager, self)
                if config_dialog.exec_() == QDialog.Accepted:
                    self.plugin_configured.emit(plugin_name)
                    self.add_log(f"插件 {plugin_name} 配置已更新")

        except Exception as e:
            logger.error(f"配置插件失败: {e}")
            QMessageBox.critical(self, "错误", f"配置插件失败: {e}")

    def enable_all_plugins(self):
        """启用所有插件"""
        reply = QMessageBox.question(self, "确认", "确定要启用所有插件吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for plugin_name in self.plugin_widgets:
                self.enable_plugin(plugin_name)

    def disable_all_plugins(self):
        """禁用所有插件"""
        reply = QMessageBox.question(self, "确认", "确定要禁用所有插件吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for plugin_name in self.plugin_widgets:
                self.disable_plugin(plugin_name)

    def open_plugin_market(self):
        """打开插件市场"""
        try:
            from gui.dialogs.enhanced_plugin_market_dialog import EnhancedPluginMarketDialog

            dialog = EnhancedPluginMarketDialog(self.plugin_manager, self)
            dialog.exec_()

        except Exception as e:
            logger.error(f"打开插件市场失败: {e}")
            QMessageBox.critical(self, "错误", f"打开插件市场失败: {e}")

    def update_status(self):
        """更新状态栏"""
        total = len(self.plugin_widgets)
        enabled = sum(1 for w in self.plugin_widgets.values()
                      if w.plugin_info.status == PluginStatus.ENABLED)

        self.status_bar.showMessage(f"总计: {total} 个插件, 已启用: {enabled} 个")

    def update_monitor_stats(self):
        """更新监控统计"""
        total = len(self.plugin_widgets)
        enabled = sum(1 for w in self.plugin_widgets.values()
                      if w.plugin_info.status == PluginStatus.ENABLED)
        disabled = sum(1 for w in self.plugin_widgets.values()
                       if w.plugin_info.status == PluginStatus.DISABLED)
        error = sum(1 for w in self.plugin_widgets.values()
                    if w.plugin_info.status == PluginStatus.ERROR)

        self.total_plugins_label.setText(str(total))
        self.enabled_plugins_label.setText(str(enabled))
        self.disabled_plugins_label.setText(str(disabled))
        self.error_plugins_label.setText(str(error))

        # 更新性能信息
        perf_info = f"""
插件性能监控报告
================

总插件数: {total}
已启用: {enabled}
已禁用: {disabled}
错误: {error}

内存使用: 估算中...
CPU使用: 估算中...
响应时间: 估算中...
        """
        self.perf_text.setText(perf_info.strip())

    def add_log(self, message: str, level: str = "INFO"):
        """添加日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        self.logs_text.append(log_entry)

    def clear_logs(self):
        """清空日志"""
        self.logs_text.clear()

    def closeEvent(self, event):
        """关闭事件"""
        self.timer.stop()
        event.accept()


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建模拟插件管理器
    class MockPluginManager:
        def get_all_plugin_metadata(self):
            return {
                "test_plugin": {
                    "name": "测试插件",
                    "version": "1.0.0",
                    "description": "这是一个测试插件",
                    "author": "测试作者",
                    "path": "/path/to/plugin",
                    "config": {"enabled": True, "threshold": 0.5}
                }
            }

        def is_plugin_loaded(self, name):
            return True

    dialog = PluginManagerDialog(MockPluginManager())
    dialog.show()

    sys.exit(app.exec_())
