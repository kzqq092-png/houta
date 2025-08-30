"""
设置对话框

提供应用程序设置界面，包括主题管理、基本设置等功能。
"""

import logging
import os
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QFormLayout, QComboBox, QSpinBox, QCheckBox,
    QListWidget, QPushButton, QTextEdit, QLabel, QDialogButtonBox,
    QMessageBox, QFileDialog, QInputDialog, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """设置对话框"""

    # 信号
    theme_changed = pyqtSignal(str)
    settings_applied = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None,
                 theme_service=None, config_service=None):
        """
        初始化设置对话框

        Args:
            parent: 父窗口组件
            theme_service: 主题服务
            config_service: 配置服务
        """
        super().__init__(parent)
        self.theme_service = theme_service
        self.config_service = config_service

        self.setWindowTitle("设置")
        self.setMinimumSize(800, 600)
        self.setModal(True)

        # 设置样式
        self._setup_styles()

        # 创建UI
        self._create_widgets()

        # 加载当前设置
        self._load_current_settings()

        # 连接信号
        self._connect_signals()

    def _setup_styles(self) -> None:
        """设置样式"""
        self.setStyleSheet("""
            QDialog {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                background-color: #f8f9fa;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                background-color: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #e9ecef;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border: 1px solid #dee2e6;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)

    def _create_widgets(self) -> None:
        """创建UI组件"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 创建基本设置选项卡
        self._create_basic_settings_tab()

        # 创建主题管理选项卡
        self._create_theme_management_tab()

        # 创建按钮
        self._create_buttons(main_layout)

    def _create_basic_settings_tab(self) -> None:
        """创建基本设置选项卡"""
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.setContentsMargins(10, 10, 10, 10)
        basic_layout.setSpacing(10)

        # 外观设置组
        appearance_group = QGroupBox("外观设置")
        appearance_layout = QFormLayout(appearance_group)

        # 主题选择
        self.theme_combo = QComboBox()
        if self.theme_service:
            themes = self.theme_service.get_available_themes()
            self.theme_combo.addItems(themes)
        appearance_layout.addRow("主题:", self.theme_combo)

        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(12)
        self.font_size_spin.setSuffix(" pt")
        appearance_layout.addRow("字体大小:", self.font_size_spin)

        basic_layout.addWidget(appearance_group)

        # 行为设置组
        behavior_group = QGroupBox("行为设置")
        behavior_layout = QFormLayout(behavior_group)

        # 语言设置
        self.language_combo = QComboBox()
        self.language_combo.addItems(["简体中文", "English"])
        behavior_layout.addRow("语言:", self.language_combo)

        # 自动保存
        self.auto_save_checkbox = QCheckBox("启用自动保存")
        self.auto_save_checkbox.setChecked(True)
        behavior_layout.addRow("", self.auto_save_checkbox)

        # 启动时自动加载上次项目
        self.auto_load_checkbox = QCheckBox("启动时自动加载上次项目")
        self.auto_load_checkbox.setChecked(False)
        behavior_layout.addRow("", self.auto_load_checkbox)

        basic_layout.addWidget(behavior_group)

        # 数据设置组
        data_group = QGroupBox("数据设置")
        data_layout = QFormLayout(data_group)

        # 数据更新间隔
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(1, 60)
        self.update_interval_spin.setValue(5)
        self.update_interval_spin.setSuffix(" 分钟")
        data_layout.addRow("数据更新间隔:", self.update_interval_spin)

        # 缓存大小限制
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(100, 10000)
        self.cache_size_spin.setValue(1000)
        self.cache_size_spin.setSuffix(" MB")
        data_layout.addRow("缓存大小限制:", self.cache_size_spin)

        basic_layout.addWidget(data_group)

        basic_layout.addStretch()
        self.tab_widget.addTab(basic_tab, "基本设置")

    def _create_theme_management_tab(self) -> None:
        """创建主题管理选项卡"""
        theme_tab = QWidget()
        theme_layout = QVBoxLayout(theme_tab)
        theme_layout.setContentsMargins(10, 10, 10, 10)
        theme_layout.setSpacing(10)

        # 主题列表
        list_label = QLabel("主题列表:")
        list_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        theme_layout.addWidget(list_label)

        self.theme_list = QListWidget()
        self.theme_list.setMaximumHeight(150)
        if self.theme_service:
            themes = self.theme_service.get_available_themes()
            self.theme_list.addItems(themes)
        theme_layout.addWidget(self.theme_list)

        # 主题操作按钮
        btn_layout = QHBoxLayout()

        self.preview_btn = QPushButton("预览主题")
        self.import_btn = QPushButton("导入主题")
        self.export_btn = QPushButton("导出主题")
        self.delete_btn = QPushButton("删除主题")
        self.rename_btn = QPushButton("重命名主题")

        btn_layout.addWidget(self.preview_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.rename_btn)
        btn_layout.addStretch()

        theme_layout.addLayout(btn_layout)

        # 主题内容预览
        preview_label = QLabel("主题内容预览:")
        preview_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        theme_layout.addWidget(preview_label)

        self.theme_content_edit = QTextEdit()
        self.theme_content_edit.setReadOnly(True)
        self.theme_content_edit.setMaximumHeight(200)
        self.theme_content_edit.setFont(QFont("Consolas", 9))
        theme_layout.addWidget(self.theme_content_edit)

        self.tab_widget.addTab(theme_tab, "主题管理")

    def _create_buttons(self, layout: QVBoxLayout) -> None:
        """创建对话框按钮"""
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )

        self.ok_btn = button_box.button(QDialogButtonBox.Ok)
        self.cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        self.apply_btn = button_box.button(QDialogButtonBox.Apply)

        self.ok_btn.setText("确定")
        self.cancel_btn.setText("取消")
        self.apply_btn.setText("应用")

        layout.addWidget(button_box)

        # 连接按钮信号
        button_box.accepted.connect(self._on_ok_clicked)
        button_box.rejected.connect(self.reject)
        self.apply_btn.clicked.connect(self._on_apply_clicked)

    def _connect_signals(self) -> None:
        """连接信号"""
        # 主题列表选择
        self.theme_list.currentItemChanged.connect(self._on_theme_selected)

        # 主题操作按钮
        self.preview_btn.clicked.connect(self._on_preview_theme)
        self.import_btn.clicked.connect(self._on_import_theme)
        self.export_btn.clicked.connect(self._on_export_theme)
        self.delete_btn.clicked.connect(self._on_delete_theme)
        self.rename_btn.clicked.connect(self._on_rename_theme)

        # 主题下拉框变化
        self.theme_combo.currentTextChanged.connect(
            self._on_theme_combo_changed)

    def _load_current_settings(self) -> None:
        """加载当前设置"""
        try:
            if self.config_service:
                # 加载基本设置
                config = self.config_service.get_all()

                # 设置当前主题
                if self.theme_service:
                    current_theme = self.theme_service.get_current_theme()
                    if current_theme in [self.theme_combo.itemText(i) for i in range(self.theme_combo.count())]:
                        self.theme_combo.setCurrentText(current_theme)

                # 设置其他配置项
                appearance_config = config.get('appearance', {})
                self.font_size_spin.setValue(
                    appearance_config.get('font_size', 12))

                behavior_config = config.get('behavior', {})
                self.language_combo.setCurrentText(
                    behavior_config.get('language', '简体中文'))
                self.auto_save_checkbox.setChecked(
                    behavior_config.get('auto_save', True))
                self.auto_load_checkbox.setChecked(
                    behavior_config.get('auto_load', False))

                data_config = config.get('data', {})
                self.update_interval_spin.setValue(
                    data_config.get('update_interval', 5))
                self.cache_size_spin.setValue(
                    data_config.get('cache_size', 1000))

        except Exception as e:
            logger.error(f"Failed to load current settings: {e}")

    def _on_theme_selected(self) -> None:
        """主题选择事件"""
        current_item = self.theme_list.currentItem()
        if not current_item:
            self.theme_content_edit.clear()
            return

        theme_name = current_item.text()
        if self.theme_service:
            try:
                theme_config = self.theme_service.get_theme_config(theme_name)
                if theme_config:
                    # 显示主题配置内容
                    import json
                    content = json.dumps(
                        theme_config, indent=2, ensure_ascii=False)
                    self.theme_content_edit.setPlainText(content)
                else:
                    self.theme_content_edit.setPlainText("主题配置不可用")
            except Exception as e:
                self.theme_content_edit.setPlainText(f"加载主题配置失败: {e}")

    def _on_theme_combo_changed(self, theme_name: str) -> None:
        """主题下拉框变化事件"""
        # 同步选择主题列表中的项目
        for i in range(self.theme_list.count()):
            if self.theme_list.item(i).text() == theme_name:
                self.theme_list.setCurrentRow(i)
                break

    def _on_preview_theme(self) -> None:
        """预览主题"""
        current_item = self.theme_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个主题")
            return

        theme_name = current_item.text()
        if self.theme_service:
            try:
                self.theme_service.set_theme(theme_name)
                self.theme_changed.emit(theme_name)
                QMessageBox.information(self, "预览", f"已预览主题: {theme_name}")

                # 同步更新下拉框
                self.theme_combo.setCurrentText(theme_name)

            except Exception as e:
                QMessageBox.critical(self, "错误", f"预览主题失败: {e}")

    def _on_import_theme(self) -> None:
        """导入主题"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入主题", "",
            "主题文件 (*.json *.qss);;所有文件 (*)"
        )

        if not file_path:
            return

        try:
            theme_name = os.path.splitext(os.path.basename(file_path))[0]

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 这里需要根据实际的主题服务API来实现
            QMessageBox.information(self, "导入", f"主题导入功能待实现\n文件: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入主题失败: {e}")

    def _on_export_theme(self) -> None:
        """导出主题"""
        current_item = self.theme_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个主题")
            return

        theme_name = current_item.text()

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出主题", f"{theme_name}.json",
            "JSON文件 (*.json);;所有文件 (*)"
        )

        if not file_path:
            return

        try:
            # 这里需要根据实际的主题服务API来实现
            QMessageBox.information(self, "导出", f"主题导出功能待实现\n文件: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出主题失败: {e}")

    def _on_delete_theme(self) -> None:
        """删除主题"""
        current_item = self.theme_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个主题")
            return

        theme_name = current_item.text()

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除主题 '{theme_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 这里需要根据实际的主题服务API来实现
                QMessageBox.information(self, "删除", f"主题删除功能待实现")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除主题失败: {e}")

    def _on_rename_theme(self) -> None:
        """重命名主题"""
        current_item = self.theme_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个主题")
            return

        old_name = current_item.text()

        new_name, ok = QInputDialog.getText(
            self, "重命名主题", "请输入新的主题名称:",
            QLineEdit.Normal, old_name
        )

        if ok and new_name and new_name != old_name:
            try:
                # 这里需要根据实际的主题服务API来实现
                QMessageBox.information(self, "重命名", f"主题重命名功能待实现")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名主题失败: {e}")

    def _on_apply_clicked(self) -> None:
        """应用设置"""
        try:
            self._apply_settings()
            QMessageBox.information(self, "设置", "设置已应用")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用设置失败: {e}")

    def _on_ok_clicked(self) -> None:
        """确定按钮点击"""
        try:
            self._apply_settings()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")

    def _apply_settings(self) -> None:
        """应用设置"""
        if not self.config_service:
            return

        # 收集设置
        settings = {
            'appearance': {
                'theme': self.theme_combo.currentText(),
                'font_size': self.font_size_spin.value()
            },
            'behavior': {
                'language': self.language_combo.currentText(),
                'auto_save': self.auto_save_checkbox.isChecked(),
                'auto_load': self.auto_load_checkbox.isChecked()
            },
            'data': {
                'update_interval': self.update_interval_spin.value(),
                'cache_size': self.cache_size_spin.value()
            }
        }

        # 保存设置
        for category, config in settings.items():
            for key, value in config.items():
                self.config_service.set(f'{category}.{key}', value)

        # 应用主题
        if self.theme_service:
            theme_name = self.theme_combo.currentText()
            self.theme_service.set_theme(theme_name)
            self.theme_changed.emit(theme_name)

        # 发送设置应用信号
        self.settings_applied.emit(settings)

        logger.info("Settings applied successfully")


def show_settings_dialog(parent: Optional[QWidget] = None,
                         theme_service=None, config_service=None) -> None:
    """显示设置对话框"""
    dialog = SettingsDialog(parent, theme_service, config_service)
    dialog.exec_()
