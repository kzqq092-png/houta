#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪插件管理对话框
提供情绪插件的配置、启用/禁用、重置等管理功能
"""

import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget, QWidget,
                             QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QComboBox, QTextEdit, QLabel, QGroupBox,
                             QScrollArea, QMessageBox, QHeaderView, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from typing import Dict, Any, List, Optional

from plugins.sentiment_data_sources import (
    AVAILABLE_PLUGINS, FMPSentimentPlugin, ExordeSentimentPlugin,
    NewsSentimentPlugin, VIXSentimentPlugin, CryptoSentimentPlugin,
    ConfigurablePlugin, PluginConfigField
)


class PluginConfigWidget(QWidget):
    """插件配置组件"""

    configChanged = pyqtSignal(str, dict)  # 插件名称, 配置字典

    def __init__(self, plugin_name: str, plugin_class, parent=None):
        super().__init__(parent)
        self.plugin_name = plugin_name
        self.plugin_class = plugin_class
        self.plugin_instance = None
        self.config_controls = {}

        self.init_ui()
        self.load_plugin_config()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 插件信息
        info_group = QGroupBox("插件信息")
        info_layout = QFormLayout(info_group)

        # 创建插件实例获取元数据
        try:
            print(f"🔨 [调试] 创建插件实例: {self.plugin_class}")
            self.plugin_instance = self.plugin_class()
            print(f"✅ [调试] 插件实例创建成功: {type(self.plugin_instance)}")

            metadata = self.plugin_instance.metadata
            print(f"📝 [调试] 获取元数据成功: {metadata.name}")

            info_layout.addRow("名称:", QLabel(metadata.name))
            info_layout.addRow("版本:", QLabel(metadata.version))
            info_layout.addRow("作者:", QLabel(metadata.author))
            info_layout.addRow("描述:", QLabel(metadata.description))

        except Exception as e:
            print(f"❌ [调试] 插件实例创建失败: {e}")
            import traceback
            traceback.print_exc()
            info_layout.addRow("错误:", QLabel(f"无法加载插件信息: {e}"))

        scroll_layout.addWidget(info_group)

        # 配置表单
        print(f"🔍 [调试] 检查插件是否为可配置插件...")
        if self.plugin_instance and isinstance(self.plugin_instance, ConfigurablePlugin):
            print(f"✅ [调试] 插件是可配置插件")
            try:
                print(f"📋 [调试] 获取配置模式...")
                config_schema = self.plugin_instance.get_config_schema()
                print(f"✅ [调试] 配置模式获取成功，字段数量: {len(config_schema)}")
                self.create_config_form(config_schema, scroll_layout)
            except Exception as e:
                print(f"❌ [调试] 配置模式获取失败: {e}")
                import traceback
                traceback.print_exc()
                error_label = QLabel(f"无法加载配置模式: {e}")
                error_label.setStyleSheet("color: red;")
                scroll_layout.addWidget(error_label)
        else:
            print(f"❌ [调试] 插件不是可配置插件")
            no_config_label = QLabel("此插件不支持配置")
            no_config_label.setStyleSheet("color: gray; font-style: italic;")
            scroll_layout.addWidget(no_config_label)

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_config)

        self.reset_button = QPushButton("重置为默认")
        self.reset_button.clicked.connect(self.reset_config)

        self.test_button = QPushButton("测试插件")
        self.test_button.clicked.connect(self.test_plugin)

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.test_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def create_config_form(self, config_schema: List[PluginConfigField], parent_layout: QVBoxLayout):
        """创建配置表单"""
        print(f"📋 [调试] 开始创建配置表单，字段数量: {len(config_schema)}")

        # 按组分类配置项
        groups = {}
        for field in config_schema:
            group_name = field.group
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(field)

        print(f"📊 [调试] 配置字段按组分类: {list(groups.keys())}")

        # 为每个组创建GroupBox
        for group_name, fields in groups.items():
            print(f"📦 [调试] 创建组: {group_name}，字段数量: {len(fields)}")
            group_box = QGroupBox(group_name)
            group_layout = QFormLayout(group_box)

            for field in fields:
                print(f"🔧 [调试] 创建控件: {field.name} ({field.field_type})")
                try:
                    control = self.create_field_control(field)
                    if control:
                        self.config_controls[field.name] = control

                        # 创建标签和帮助文本
                        label_text = field.display_name
                        if field.required:
                            label_text += " *"

                        label = QLabel(label_text)
                        if field.description:
                            label.setToolTip(field.description)
                            control.setToolTip(field.description)

                        group_layout.addRow(label, control)
                        print(f"  ✅ [调试] 控件创建成功: {field.name}")
                    else:
                        print(f"  ❌ [调试] 控件创建失败: {field.name}")
                except Exception as e:
                    print(f"  ❌ [调试] 创建控件时出错: {field.name} - {e}")
                    import traceback
                    traceback.print_exc()

            parent_layout.addWidget(group_box)
            print(f"  ✅ [调试] 组添加到布局: {group_name}")

        print(f"✅ [调试] 配置表单创建完成，总共创建了 {len(self.config_controls)} 个控件")

    def create_field_control(self, field: PluginConfigField):
        """根据字段类型创建控件"""
        if field.field_type == "boolean":
            control = QCheckBox()
            control.setChecked(field.default_value)
            return control

        elif field.field_type == "number":
            if field.min_value is not None and field.min_value >= 0 and field.max_value is not None and field.max_value <= 100 and isinstance(field.default_value, int):
                # 整数类型
                control = QSpinBox()
                control.setMinimum(int(field.min_value) if field.min_value is not None else 0)
                control.setMaximum(int(field.max_value) if field.max_value is not None else 9999)
                control.setValue(int(field.default_value))
            else:
                # 浮点数类型
                control = QDoubleSpinBox()
                control.setDecimals(3)
                control.setMinimum(field.min_value if field.min_value is not None else -999999.0)
                control.setMaximum(field.max_value if field.max_value is not None else 999999.0)
                control.setValue(float(field.default_value))
            return control

        elif field.field_type == "select":
            control = QComboBox()
            control.addItems(field.options)
            if field.default_value in field.options:
                control.setCurrentText(field.default_value)
            return control

        elif field.field_type == "multiselect":
            # 使用文本框，逗号分隔
            control = QLineEdit()
            if isinstance(field.default_value, list):
                control.setText(",".join(field.default_value))
            else:
                control.setText(str(field.default_value))
            if field.placeholder:
                control.setPlaceholderText(field.placeholder)
            return control

        else:  # string
            if field.name in ["description", "suggestion"] or len(str(field.default_value)) > 50:
                # 多行文本
                control = QTextEdit()
                control.setMaximumHeight(80)
                control.setPlainText(str(field.default_value))
            else:
                # 单行文本
                control = QLineEdit()
                control.setText(str(field.default_value))
                if field.placeholder:
                    control.setPlaceholderText(field.placeholder)
            return control

    def load_plugin_config(self):
        """加载插件配置"""
        if not self.plugin_instance or not isinstance(self.plugin_instance, ConfigurablePlugin):
            return

        try:
            # 加载当前配置
            current_config = self.plugin_instance.load_config()

            # 更新控件值
            for field_name, control in self.config_controls.items():
                if field_name in current_config:
                    value = current_config[field_name]
                    self.set_control_value(control, value)

        except Exception as e:
            QMessageBox.warning(self, "加载配置失败", f"无法加载插件配置:\n{str(e)}")

    def set_control_value(self, control, value):
        """设置控件值"""
        if isinstance(control, QCheckBox):
            control.setChecked(bool(value))
        elif isinstance(control, QSpinBox):
            # QSpinBox需要整数值
            control.setValue(int(value) if value is not None else 0)
        elif isinstance(control, QDoubleSpinBox):
            # QDoubleSpinBox需要浮点数值
            control.setValue(float(value) if value is not None else 0.0)
        elif isinstance(control, QComboBox):
            control.setCurrentText(str(value))
        elif isinstance(control, QLineEdit):
            if isinstance(value, list):
                control.setText(",".join(map(str, value)))
            else:
                control.setText(str(value))
        elif isinstance(control, QTextEdit):
            control.setPlainText(str(value))

    def get_control_value(self, control):
        """获取控件值"""
        if isinstance(control, QCheckBox):
            return control.isChecked()
        elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
            return control.value()
        elif isinstance(control, QComboBox):
            return control.currentText()
        elif isinstance(control, QLineEdit):
            text = control.text().strip()
            # 如果包含逗号，认为是列表
            if "," in text:
                return [item.strip() for item in text.split(",") if item.strip()]
            return text
        elif isinstance(control, QTextEdit):
            return control.toPlainText()
        return None

    def save_config(self):
        """保存配置"""
        if not self.plugin_instance or not isinstance(self.plugin_instance, ConfigurablePlugin):
            QMessageBox.warning(self, "保存失败", "插件不支持配置保存")
            return

        try:
            # 收集当前配置
            current_config = {}
            for field_name, control in self.config_controls.items():
                current_config[field_name] = self.get_control_value(control)

            # 验证配置
            is_valid, error_msg = self.plugin_instance.validate_config(current_config)
            if not is_valid:
                QMessageBox.warning(self, "配置验证失败", f"配置验证失败:\n{error_msg}")
                return

            # 保存配置
            success = self.plugin_instance.save_config(current_config)
            if success:
                QMessageBox.information(self, "保存成功", "插件配置已保存")
                self.configChanged.emit(self.plugin_name, current_config)
            else:
                QMessageBox.warning(self, "保存失败", "无法保存插件配置")

        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存配置时发生错误:\n{str(e)}")

    def reset_config(self):
        """重置配置"""
        if not self.plugin_instance or not isinstance(self.plugin_instance, ConfigurablePlugin):
            return

        reply = QMessageBox.question(self, "确认重置",
                                     "确定要重置为默认配置吗？\n当前配置将被覆盖。",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                success = self.plugin_instance.reset_config()
                if success:
                    self.load_plugin_config()  # 重新加载配置
                    QMessageBox.information(self, "重置成功", "已重置为默认配置")
                else:
                    QMessageBox.warning(self, "重置失败", "无法重置配置")
            except Exception as e:
                QMessageBox.critical(self, "重置错误", f"重置配置时发生错误:\n{str(e)}")

    def test_plugin(self):
        """测试插件"""
        if not self.plugin_instance:
            return

        try:
            # 先保存当前配置
            current_config = {}
            for field_name, control in self.config_controls.items():
                current_config[field_name] = self.get_control_value(control)

            # 验证配置
            if isinstance(self.plugin_instance, ConfigurablePlugin):
                is_valid, error_msg = self.plugin_instance.validate_config(current_config)
                if not is_valid:
                    QMessageBox.warning(self, "配置无效", f"当前配置无效:\n{error_msg}")
                    return

                # 临时应用配置
                self.plugin_instance._config = current_config

            # 初始化插件
            self.plugin_instance.initialize(None)

            # 测试数据获取
            response = self.plugin_instance._fetch_raw_sentiment_data()

            if response.success:
                result_text = f"✅ 测试成功\n\n"
                result_text += f"数据项: {len(response.data)}\n"
                result_text += f"综合指数: {response.composite_score}\n"
                result_text += f"数据质量: {response.data_quality}\n\n"

                if response.data:
                    result_text += "数据详情:\n"
                    for item in response.data[:3]:  # 只显示前3项
                        result_text += f"- {item.indicator_name}: {item.value} ({item.status})\n"

                    if len(response.data) > 3:
                        result_text += f"... 还有 {len(response.data) - 3} 项数据\n"

                QMessageBox.information(self, "插件测试结果", result_text)
            else:
                QMessageBox.warning(self, "测试失败",
                                    f"插件测试失败:\n{response.error_message}")

        except Exception as e:
            QMessageBox.critical(self, "测试错误", f"测试插件时发生错误:\n{str(e)}")


class SentimentPluginManagerDialog(QDialog):
    """情绪插件管理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("情绪分析插件管理器")
        self.setMinimumSize(900, 700)

        self.init_ui()
        self.load_plugins()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("情绪分析插件管理器")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：插件列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        left_layout.addWidget(QLabel("已安装的情绪插件:"))

        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(4)
        self.plugin_table.setHorizontalHeaderLabels(["插件名称", "状态", "类型", "操作"])

        # 设置表格列宽
        header = self.plugin_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.plugin_table.selectionModel().selectionChanged.connect(self.on_plugin_selection_changed)
        left_layout.addWidget(self.plugin_table)

        # 全局操作按钮
        global_button_layout = QHBoxLayout()

        refresh_button = QPushButton("刷新列表")
        refresh_button.clicked.connect(self.load_plugins)

        enable_all_button = QPushButton("启用全部")
        enable_all_button.clicked.connect(self.enable_all_plugins)

        disable_all_button = QPushButton("禁用全部")
        disable_all_button.clicked.connect(self.disable_all_plugins)

        global_button_layout.addWidget(refresh_button)
        global_button_layout.addWidget(enable_all_button)
        global_button_layout.addWidget(disable_all_button)
        global_button_layout.addStretch()

        left_layout.addLayout(global_button_layout)

        # 右侧：插件配置
        self.config_tab_widget = QTabWidget()
        self.config_tab_widget.setTabsClosable(False)

        # 默认显示欢迎页面
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.addStretch()

        welcome_label = QLabel("请从左侧选择一个插件进行配置")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("color: gray; font-size: 16px;")
        welcome_layout.addWidget(welcome_label)
        welcome_layout.addStretch()

        self.config_tab_widget.addTab(welcome_widget, "欢迎")

        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(self.config_tab_widget)
        splitter.setSizes([300, 600])

        layout.addWidget(splitter)

        # 底部按钮
        button_layout = QHBoxLayout()

        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def load_plugins(self):
        """加载插件列表"""
        self.plugin_table.setRowCount(0)

        # 只加载可配置的情绪插件
        configurable_plugins = {
            'fmp_sentiment': ('FMP社交情绪', FMPSentimentPlugin),
            'exorde_sentiment': ('Exorde情绪光谱', ExordeSentimentPlugin),
            'news_sentiment': ('新闻情绪分析', NewsSentimentPlugin),
            'vix_sentiment': ('VIX恐慌指数', VIXSentimentPlugin),
            'crypto_sentiment': ('加密货币情绪', CryptoSentimentPlugin),
        }

        for plugin_key, (display_name, plugin_class) in configurable_plugins.items():
            self.add_plugin_to_table(plugin_key, display_name, plugin_class)

    def add_plugin_to_table(self, plugin_key: str, display_name: str, plugin_class):
        """添加插件到表格"""
        row = self.plugin_table.rowCount()
        self.plugin_table.insertRow(row)

        # 插件名称
        name_item = QTableWidgetItem(display_name)
        name_item.setData(Qt.UserRole, plugin_key)
        name_item.setData(Qt.UserRole + 1, plugin_class)
        self.plugin_table.setItem(row, 0, name_item)

        # 状态
        try:
            plugin_instance = plugin_class()
            if isinstance(plugin_instance, ConfigurablePlugin):
                plugin_instance.load_config()
                is_enabled = plugin_instance.is_enabled()

                # 检查配置状态
                if hasattr(plugin_instance, 'is_properly_configured') and hasattr(plugin_instance, 'get_config_status_message'):
                    config_ok = plugin_instance.is_properly_configured()
                    config_msg = plugin_instance.get_config_status_message()

                    if is_enabled and config_ok:
                        status = "✅ 已启用且配置正常"
                    elif is_enabled:
                        status = f"⚠️ 已启用但{config_msg}"
                    else:
                        status = f"❌ 已禁用 - {config_msg}"
                else:
                    status = "✅ 已启用" if is_enabled else "❌ 已禁用"
            else:
                status = "⚠️ 不可配置"
        except Exception as e:
            status = f"❌ 错误: {str(e)[:20]}"

        status_item = QTableWidgetItem(status)
        self.plugin_table.setItem(row, 1, status_item)

        # 类型
        type_item = QTableWidgetItem("情绪数据源")
        self.plugin_table.setItem(row, 2, type_item)

        # 操作按钮
        config_button = QPushButton("配置")
        config_button.clicked.connect(lambda checked, pk=plugin_key, pc=plugin_class: self.open_plugin_config(pk, pc))
        self.plugin_table.setCellWidget(row, 3, config_button)

    def on_plugin_selection_changed(self):
        """插件选择改变"""
        current_row = self.plugin_table.currentRow()
        if current_row >= 0:
            name_item = self.plugin_table.item(current_row, 0)
            plugin_key = name_item.data(Qt.UserRole)
            plugin_class = name_item.data(Qt.UserRole + 1)
            self.open_plugin_config(plugin_key, plugin_class)

    def open_plugin_config(self, plugin_key: str, plugin_class):
        """打开插件配置"""
        # 查找是否已经打开
        for i in range(self.config_tab_widget.count()):
            widget = self.config_tab_widget.widget(i)
            if hasattr(widget, 'plugin_name') and widget.plugin_name == plugin_key:
                self.config_tab_widget.setCurrentIndex(i)
                return

        # 创建新的配置页面
        try:
            config_widget = PluginConfigWidget(plugin_key, plugin_class)
            config_widget.configChanged.connect(self.on_plugin_config_changed)

            # 移除欢迎页面（如果存在）
            if self.config_tab_widget.count() == 1 and self.config_tab_widget.tabText(0) == "欢迎":
                self.config_tab_widget.removeTab(0)

            # 添加配置页面
            display_name = config_widget.plugin_instance.metadata.name if config_widget.plugin_instance else plugin_key
            tab_index = self.config_tab_widget.addTab(config_widget, display_name)
            self.config_tab_widget.setCurrentIndex(tab_index)

        except Exception as e:
            QMessageBox.critical(self, "打开配置失败", f"无法打开插件配置:\n{str(e)}")

    def on_plugin_config_changed(self, plugin_name: str, config: Dict[str, Any]):
        """插件配置改变"""
        # 刷新插件状态
        self.refresh_plugin_status(plugin_name)

    def refresh_plugin_status(self, plugin_key: str):
        """刷新插件状态"""
        for row in range(self.plugin_table.rowCount()):
            name_item = self.plugin_table.item(row, 0)
            if name_item.data(Qt.UserRole) == plugin_key:
                plugin_class = name_item.data(Qt.UserRole + 1)
                try:
                    plugin_instance = plugin_class()
                    if isinstance(plugin_instance, ConfigurablePlugin):
                        plugin_instance.load_config()
                        is_enabled = plugin_instance.is_enabled()

                        # 检查配置状态
                        if hasattr(plugin_instance, 'is_properly_configured') and hasattr(plugin_instance, 'get_config_status_message'):
                            config_ok = plugin_instance.is_properly_configured()
                            config_msg = plugin_instance.get_config_status_message()

                            if is_enabled and config_ok:
                                status = "✅ 已启用且配置正常"
                            elif is_enabled:
                                status = f"⚠️ 已启用但{config_msg}"
                            else:
                                status = f"❌ 已禁用 - {config_msg}"
                        else:
                            status = "✅ 已启用" if is_enabled else "❌ 已禁用"
                    else:
                        status = "⚠️ 不可配置"
                except Exception as e:
                    status = f"❌ 错误: {str(e)[:20]}"

                self.plugin_table.setItem(row, 1, QTableWidgetItem(status))
                break

    def enable_all_plugins(self):
        """启用全部插件"""
        self.set_all_plugins_enabled(True)

    def disable_all_plugins(self):
        """禁用全部插件"""
        self.set_all_plugins_enabled(False)

    def set_all_plugins_enabled(self, enabled: bool):
        """设置所有插件的启用状态"""
        action_text = "启用" if enabled else "禁用"

        reply = QMessageBox.question(self, f"确认{action_text}",
                                     f"确定要{action_text}所有插件吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            success_count = 0
            total_count = 0

            for row in range(self.plugin_table.rowCount()):
                name_item = self.plugin_table.item(row, 0)
                plugin_key = name_item.data(Qt.UserRole)
                plugin_class = name_item.data(Qt.UserRole + 1)

                try:
                    plugin_instance = plugin_class()
                    if isinstance(plugin_instance, ConfigurablePlugin):
                        plugin_instance.load_config()
                        if plugin_instance.set_enabled(enabled):
                            plugin_instance.save_config()
                            success_count += 1
                        total_count += 1
                except Exception:
                    pass

            if success_count > 0:
                QMessageBox.information(self, f"{action_text}完成",
                                        f"成功{action_text} {success_count}/{total_count} 个插件")
                self.load_plugins()  # 刷新列表
            else:
                QMessageBox.warning(self, f"{action_text}失败", "没有插件被成功处理")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    dialog = SentimentPluginManagerDialog()
    dialog.show()
    sys.exit(app.exec_())
