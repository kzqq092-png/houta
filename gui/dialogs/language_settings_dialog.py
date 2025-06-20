"""
语言设置对话框
提供语言选择和国际化设置功能
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup,
    QPushButton, QLabel, QGroupBox, QMessageBox, QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QFont
from typing import Optional
import traceback


class LanguageSettingsDialog(QDialog):
    """语言设置对话框"""

    def __init__(self, i18n_manager, parent=None):
        """
        初始化语言设置对话框

        Args:
            i18n_manager: 国际化管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.i18n_manager = i18n_manager
        self.parent_window = parent
        self.log_manager = getattr(parent, 'log_manager', None)
        self.selected_language = None

        # 设置窗口属性
        self.setWindowTitle("语言设置")
        self.setModal(True)
        self.resize(500, 400)

        # 初始化UI
        self.init_ui()

        # 设置当前语言
        self.set_current_language()

    def init_ui(self):
        """初始化用户界面"""
        try:
            # 主布局
            main_layout = QVBoxLayout(self)

            # 创建分割器
            splitter = QSplitter(Qt.Horizontal)
            main_layout.addWidget(splitter)

            # 左侧：语言选择
            left_widget = self.create_language_selection_widget()
            splitter.addWidget(left_widget)

            # 右侧：语言预览
            right_widget = self.create_language_preview_widget()
            splitter.addWidget(right_widget)

            # 设置分割器比例
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 1)

            # 底部按钮
            button_layout = self.create_button_layout()
            main_layout.addLayout(button_layout)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化语言设置对话框失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def create_language_selection_widget(self):
        """创建语言选择控件"""
        group = QGroupBox("选择语言")
        layout = QVBoxLayout(group)

        # 创建按钮组
        self.language_button_group = QButtonGroup()

        # 获取支持的语言
        supported_languages = self.i18n_manager.get_supported_languages()

        # 创建语言选项
        for lang_code, lang_name in supported_languages.items():
            radio_button = QRadioButton(lang_name)
            radio_button.setProperty("lang_code", lang_code)
            radio_button.toggled.connect(self.on_language_selected)

            self.language_button_group.addButton(radio_button)
            layout.addWidget(radio_button)

        layout.addStretch()

        return group

    def create_language_preview_widget(self):
        """创建语言预览控件"""
        group = QGroupBox("预览")
        layout = QVBoxLayout(group)

        # 预览说明
        preview_label = QLabel("选择语言后，在这里可以看到界面文本的预览效果：")
        preview_label.setWordWrap(True)
        layout.addWidget(preview_label)

        # 预览文本区域
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        layout.addWidget(self.preview_text)

        # 示例文本
        layout.addWidget(QLabel("示例界面元素："))

        # 创建示例界面元素
        self.create_sample_elements(layout)

        return group

    def create_sample_elements(self, layout):
        """创建示例界面元素"""
        # 示例菜单项
        self.sample_file_label = QLabel("文件")
        self.sample_file_label.setFont(QFont("", 9, QFont.Bold))
        layout.addWidget(self.sample_file_label)

        self.sample_edit_label = QLabel("编辑")
        self.sample_edit_label.setFont(QFont("", 9, QFont.Bold))
        layout.addWidget(self.sample_edit_label)

        self.sample_view_label = QLabel("视图")
        self.sample_view_label.setFont(QFont("", 9, QFont.Bold))
        layout.addWidget(self.sample_view_label)

        # 示例按钮文本
        layout.addWidget(QLabel("按钮示例："))

        self.sample_ok_label = QLabel("确定")
        layout.addWidget(self.sample_ok_label)

        self.sample_cancel_label = QLabel("取消")
        layout.addWidget(self.sample_cancel_label)

        self.sample_apply_label = QLabel("应用")
        layout.addWidget(self.sample_apply_label)

        layout.addStretch()

    def create_button_layout(self):
        """创建底部按钮布局"""
        layout = QHBoxLayout()

        layout.addStretch()

        # 确定按钮
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

        # 应用按钮
        self.apply_button = QPushButton("应用")
        self.apply_button.clicked.connect(self.apply_language)
        layout.addWidget(self.apply_button)

        return layout

    def set_current_language(self):
        """设置当前语言选项"""
        try:
            current_language = self.i18n_manager.get_current_language()

            # 查找并选中当前语言的单选按钮
            for button in self.language_button_group.buttons():
                lang_code = button.property("lang_code")
                if lang_code == current_language:
                    button.setChecked(True)
                    self.selected_language = lang_code
                    self.update_preview()
                    break

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"设置当前语言失败: {str(e)}")

    def on_language_selected(self, checked):
        """语言选择事件"""
        if not checked:
            return

        try:
            sender = self.sender()
            lang_code = sender.property("lang_code")
            self.selected_language = lang_code

            # 更新预览
            self.update_preview()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"处理语言选择事件失败: {str(e)}")

    def update_preview(self):
        """更新语言预览 - 优化版本，避免实际语言切换"""
        if not self.selected_language:
            return

        try:
            # 不进行实际的语言切换，直接获取翻译文本
            preview_texts = self._get_preview_texts_for_language(self.selected_language)
            self.preview_text.setPlainText("\n".join(preview_texts))

            # 更新示例界面元素
            self._update_sample_elements_for_language(self.selected_language)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新语言预览失败: {str(e)}")

    def _get_preview_texts_for_language(self, lang_code: str) -> list:
        """获取指定语言的预览文本，不切换当前语言"""
        try:
            # 直接从翻译字典获取文本，避免切换语言
            translations = getattr(self.i18n_manager, 'translations', {})
            lang_translations = translations.get(lang_code, {})

            # 如果没有翻译，使用默认文本
            def get_text(key, default):
                return lang_translations.get(key, default)

            preview_texts = [
                f"主窗口标题: {get_text('main_window_title', 'HIkyuu量化交易系统')}",
                f"状态: {get_text('ready', '就绪')}",
                f"股票列表: {get_text('stock_list', '股票列表')}",
                f"技术分析: {get_text('technical_analysis', '技术分析')}",
                f"回测: {get_text('backtest', '回测')}",
                f"设置: {get_text('settings', '设置')}"
            ]

            return preview_texts

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取预览文本失败: {str(e)}")
            return ["预览文本获取失败"]

    def _update_sample_elements_for_language(self, lang_code: str):
        """更新示例界面元素，不切换当前语言"""
        try:
            # 直接从翻译字典获取文本
            translations = getattr(self.i18n_manager, 'translations', {})
            lang_translations = translations.get(lang_code, {})

            def get_text(key, default):
                return lang_translations.get(key, default)

            self.sample_file_label.setText(get_text('file_menu', '文件'))
            self.sample_edit_label.setText(get_text('edit_menu', '编辑'))
            self.sample_view_label.setText(get_text('view_menu', '视图'))
            self.sample_ok_label.setText(get_text('ok', '确定'))
            self.sample_cancel_label.setText(get_text('cancel', '取消'))
            self.sample_apply_label.setText(get_text('apply', '应用'))

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新示例元素失败: {str(e)}")

    def apply_language(self):
        """应用语言设置 - 优化版本，避免递归调用"""
        if not self.selected_language:
            QMessageBox.warning(self, "警告", "请先选择一种语言")
            return

        try:
            # 检查是否正在切换语言，避免重复操作
            if getattr(self, '_applying_language', False):
                self.log_manager.debug("语言设置正在应用中，忽略重复调用")
                return

            self._applying_language = True

            try:
                # 应用语言设置
                self.i18n_manager.set_language(self.selected_language)

                # 异步通知父窗口，避免阻塞
                self._notify_parent_async()

                QMessageBox.information(self, "成功", "语言设置已应用")

                if self.log_manager:
                    self.log_manager.info(f"语言设置已应用: {self.selected_language}")

            finally:
                # 异步清除标志
                QTimer.singleShot(500, self._clear_applying_flag)

        except Exception as e:
            self._applying_language = False
            if self.log_manager:
                self.log_manager.error(f"应用语言设置失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"应用语言设置失败: {str(e)}")

    def _notify_parent_async(self):
        """异步通知父窗口语言变更，避免递归调用"""
        def notify():
            try:
                if hasattr(self.parent_window, 'on_language_changed'):
                    # 直接调用方法，避免信号递归
                    self.parent_window.on_language_changed(self.selected_language)
                else:
                    # 如果没有直接方法，才使用信号（但要防护）
                    if hasattr(self.parent_window, 'language_changed') and not getattr(self.parent_window, '_language_changing', False):
                        self.parent_window.language_changed.emit(self.selected_language)
            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"通知父窗口失败: {str(e)}")

        # 延迟通知，避免阻塞
        QTimer.singleShot(100, notify)

    def _clear_applying_flag(self):
        """清除应用标志"""
        self._applying_language = False

    def accept(self):
        """确定按钮事件 - 优化版本"""
        if self.selected_language:
            self.apply_language()
        super().accept()

    def reject(self):
        """取消按钮事件"""
        super().reject()

    def get_selected_language(self) -> Optional[str]:
        """获取选中的语言"""
        return self.selected_language
