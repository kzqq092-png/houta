"""
菜单处理器模块 - 处理菜单相关功能

包含菜单事件处理、对话框管理、文件操作等功能
"""

from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QInputDialog, QProgressDialog, QTabWidget, QComboBox,
    QCheckBox, QSpinBox, QSlider, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QObject
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices
from PyQt5.QtCore import QUrl
from typing import Optional, Dict, Any, List
import os
import json
from core.adapters import get_logger
from core.logger import LogManager

from gui.tools import Calculator, UnitConverter


class MenuHandler(QObject):
    """菜单处理器类"""

    # 定义信号
    file_operation_completed = pyqtSignal(str, bool)  # 文件操作完成信号
    settings_changed = pyqtSignal(dict)  # 设置变化信号
    help_requested = pyqtSignal(str)  # 帮助请求信号
    analysis_requested = pyqtSignal()
    backtest_requested = pyqtSignal()
    optimization_requested = pyqtSignal()

    def __init__(self, parent=None, log_manager: Optional[LogManager] = None):
        super().__init__(parent)
        self.log_manager = log_manager or get_logger("MenuHandler")
        self.parent_gui = parent

        # 文件操作相关
        self.current_file = None
        self.file_modified = False

        # 设置对话框引用
        self.settings_dialog = None
        self.about_dialog = None

    def new_file(self):
        """新建文件"""
        try:
            self.log_manager.info("请求'新建文件'操作")
            if self.file_modified:
                reply = QMessageBox.question(
                    self.parent_gui, "保存文件",
                    "当前文件已修改，是否保存？",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )

                if reply == QMessageBox.Yes:
                    if not self.save_file():
                        return False
                elif reply == QMessageBox.Cancel:
                    return False

            # 清空当前内容
            self.current_file = None
            self.file_modified = False

            # 通知主窗口
            self.file_operation_completed.emit("new", True)
            self.log_manager.info("新建文件完成")

            return True

        except Exception as e:
            self.log_manager.error(f"新建文件失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self.parent_gui, "错误", f"新建文件失败: {str(e)}")
            return False

    def open_file(self):
        """打开文件"""
        try:
            self.log_manager.info("请求'打开文件'操作")
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent_gui, "打开文件", "",
                "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
            )

            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.current_file = file_path
                self.file_modified = False

                # 通知主窗口
                self.file_operation_completed.emit("open", True)
                self.log_manager.info(f"打开文件成功: {file_path}")

                return True

        except Exception as e:
            self.log_manager.error(f"打开文件失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self.parent_gui, "错误", f"打开文件失败: {str(e)}")
            return False

    def save_file(self):
        """保存文件"""
        try:
            self.log_manager.info("请求'保存文件'操作")
            if not self.current_file:
                return self.save_file_as()

            # 这里应该获取当前内容并保存
            # 由于这是处理器模块，具体内容由主窗口提供

            self.file_modified = False
            self.file_operation_completed.emit("save", True)
            self.log_manager.info(f"保存文件成功: {self.current_file}")

            return True

        except Exception as e:
            self.log_manager.error(f"保存文件失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self.parent_gui, "错误", f"保存文件失败: {str(e)}")
            return False

    def save_file_as(self):
        """另存为文件"""
        try:
            self.log_manager.info("请求'另存为'操作")
            file_path, _ = QFileDialog.getSaveFileName(
                self.parent_gui, "另存为", "",
                "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
            )

            if file_path:
                # 这里应该获取当前内容并保存
                # 由于这是处理器模块，具体内容由主窗口提供

                self.current_file = file_path
                self.file_modified = False

                self.file_operation_completed.emit("save_as", True)
                self.log_manager.info(f"另存为文件成功: {file_path}")

                return True

        except Exception as e:
            self.log_manager.error(f"另存为文件失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self.parent_gui, "错误", f"另存为文件失败: {str(e)}")
            return False

    def show_settings(self):
        """显示设置对话框"""
        try:
            self.log_manager.info("请求显示'设置'对话框")
            if self.settings_dialog is None:
                self.settings_dialog = self.create_settings_dialog()

            if self.settings_dialog.exec_() == QDialog.Accepted:
                # 获取设置并发送信号
                settings = self.get_settings_from_dialog()
                self.settings_changed.emit(settings)
                self.log_manager.info("设置已更新")

        except Exception as e:
            self.log_manager.error(f"显示设置对话框失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self.parent_gui, "错误", f"显示设置失败: {str(e)}")

    def create_settings_dialog(self):
        """创建设置对话框"""
        self.log_manager.debug("创建设置对话框UI...")
        dialog = QDialog(self.parent_gui)
        dialog.setWindowTitle("系统设置")
        dialog.setModal(True)
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        # 创建标签页
        tab_widget = QTabWidget()

        # 通用设置标签页
        general_tab = self.create_general_settings_tab()
        tab_widget.addTab(general_tab, "通用设置")

        # 主题设置标签页
        theme_tab = self.create_theme_settings_tab()
        tab_widget.addTab(theme_tab, "主题设置")

        # 数据设置标签页
        data_tab = self.create_data_settings_tab()
        tab_widget.addTab(data_tab, "数据设置")

        # 高级设置标签页
        advanced_tab = self.create_advanced_settings_tab()
        tab_widget.addTab(advanced_tab, "高级设置")

        layout.addWidget(tab_widget)

        # 按钮区域
        button_layout = QHBoxLayout()

        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        apply_button = QPushButton("应用")

        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        apply_button.clicked.connect(lambda: self.apply_settings())

        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(apply_button)

        layout.addLayout(button_layout)

        return dialog

    def create_general_settings_tab(self):
        """创建通用设置标签页"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 自动保存设置
        self.auto_save_checkbox = QCheckBox("启用自动保存")
        layout.addRow("自动保存:", self.auto_save_checkbox)

        # 自动保存间隔
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 60)
        self.auto_save_interval.setValue(5)
        self.auto_save_interval.setSuffix(" 分钟")
        layout.addRow("保存间隔:", self.auto_save_interval)

        # 启动时恢复窗口
        self.restore_window_checkbox = QCheckBox("启动时恢复窗口状态")
        layout.addRow("窗口恢复:", self.restore_window_checkbox)

        # 显示启动画面
        self.show_splash_checkbox = QCheckBox("显示启动画面")
        layout.addRow("启动画面:", self.show_splash_checkbox)

        # 检查更新
        self.check_update_checkbox = QCheckBox("启动时检查更新")
        layout.addRow("自动更新:", self.check_update_checkbox)

        return widget

    def create_theme_settings_tab(self):
        """创建主题设置标签页"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 主题选择
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色主题", "深色主题", "自动切换"])
        layout.addRow("主题:", self.theme_combo)

        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(12)
        layout.addRow("字体大小:", self.font_size_spin)

        # 透明度
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(100)
        layout.addRow("窗口透明度:", self.opacity_slider)

        # 动画效果
        self.animation_checkbox = QCheckBox("启用动画效果")
        layout.addRow("动画:", self.animation_checkbox)

        return widget

    def create_data_settings_tab(self):
        """创建数据设置标签页"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 数据源选择
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["本地数据", "在线数据", "混合模式"])
        layout.addRow("数据源:", self.data_source_combo)

        # 缓存大小
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(100, 10000)
        self.cache_size_spin.setValue(1000)
        self.cache_size_spin.setSuffix(" MB")
        layout.addRow("缓存大小:", self.cache_size_spin)

        # 数据更新频率
        self.update_frequency_combo = QComboBox()
        self.update_frequency_combo.addItems(["实时", "1分钟", "5分钟", "15分钟", "手动"])
        layout.addRow("更新频率:", self.update_frequency_combo)

        # 历史数据天数
        self.history_days_spin = QSpinBox()
        self.history_days_spin.setRange(30, 3650)
        self.history_days_spin.setValue(365)
        self.history_days_spin.setSuffix(" 天")
        layout.addRow("历史数据:", self.history_days_spin)

        return widget

    def create_advanced_settings_tab(self):
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 线程数
        self.thread_count_spin = QSpinBox()
        self.thread_count_spin.setRange(1, 16)
        self.thread_count_spin.setValue(4)
        layout.addRow("线程数:", self.thread_count_spin)

        # 日志级别
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        layout.addRow("日志级别:", self.log_level_combo)

        # 调试模式
        self.debug_mode_checkbox = QCheckBox("启用调试模式")
        layout.addRow("调试模式:", self.debug_mode_checkbox)

        # 性能监控
        self.performance_monitor_checkbox = QCheckBox("启用性能监控")
        layout.addRow("性能监控:", self.performance_monitor_checkbox)

        return widget

    def get_settings_from_dialog(self):
        """从对话框获取设置"""
        settings = {
            "general": {
                "auto_save": self.auto_save_checkbox.isChecked(),
                "auto_save_interval": self.auto_save_interval.value(),
                "restore_window": self.restore_window_checkbox.isChecked(),
                "show_splash": self.show_splash_checkbox.isChecked(),
                "check_update": self.check_update_checkbox.isChecked()
            },
            "theme": {
                "theme_name": self.theme_combo.currentText(),
                "font_size": self.font_size_spin.value(),
                "opacity": self.opacity_slider.value(),
                "animation": self.animation_checkbox.isChecked()
            },
            "data": {
                "data_source": self.data_source_combo.currentText(),
                "cache_size": self.cache_size_spin.value(),
                "update_frequency": self.update_frequency_combo.currentText(),
                "history_days": self.history_days_spin.value()
            },
            "advanced": {
                "thread_count": self.thread_count_spin.value(),
                "log_level": self.log_level_combo.currentText(),
                "debug_mode": self.debug_mode_checkbox.isChecked(),
                "performance_monitor": self.performance_monitor_checkbox.isChecked()
            }
        }
        return settings

    def apply_settings(self):
        """应用设置"""
        try:
            settings = self.get_settings_from_dialog()
            self.settings_changed.emit(settings)
            self.log_manager.info("设置已应用")

        except Exception as e:
            self.log_manager.error(f"应用设置失败: {str(e)}", exc_info=True)

    def show_about(self):
        """显示关于对话框"""
        try:
            self.log_manager.info("请求显示'关于'对话框")
            if self.about_dialog is None:
                self.about_dialog = self.create_about_dialog()
            self.about_dialog.exec_()
        except Exception as e:
            self.log_manager.error(f"显示关于对话框失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self.parent_gui, "错误", f"显示关于对话框失败: {str(e)}")

    def create_about_dialog(self):
        """创建关于对话框"""
        self.log_manager.debug("创建关于对话框UI...")
        dialog = QDialog(self.parent_gui)
        dialog.setWindowTitle("关于 HIkyuu-UI")
        dialog.setFixedSize(500, 350)

        layout = QVBoxLayout(dialog)

        # 标题
        title_label = QLabel("HIkyuu量化交易系统")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 版本信息
        version_label = QLabel("版本 2.5.6")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # 描述
        description = QTextEdit()
        description.setReadOnly(True)
        description.setHtml("""
        <h3>HIkyuu量化交易系统</h3>
        <p>基于HIkyuu框架的专业量化交易平台，提供完整的股票分析、策略回测、风险管理等功能。</p>
        
        <h4>主要功能：</h4>
        <ul>
            <li>实时股票数据获取和分析</li>
            <li>技术指标计算和图表显示</li>
            <li>策略开发和回测</li>
            <li>风险管理和组合优化</li>
            <li>AI辅助分析和决策</li>
        </ul>
        
        <h4>技术栈：</h4>
        <ul>
            <li>Python 3.11+</li>
            <li>PyQt5 GUI框架</li>
            <li>HIkyuu量化框架</li>
            <li>Pandas数据处理</li>
            <li>Matplotlib图表绘制</li>
        </ul>
        
        <p><b>开发团队：</b> HIkyuu开发团队</p>
        <p><b>许可证：</b> MIT License</p>
        """)
        layout.addWidget(description)

        # 按钮
        button_layout = QHBoxLayout()

        website_button = QPushButton("访问官网")
        github_button = QPushButton("GitHub")
        close_button = QPushButton("关闭")

        website_button.clicked.connect(lambda: self.open_url("https://hikyuu.org"))
        github_button.clicked.connect(lambda: self.open_url("https://github.com/fasiondog/hikyuu"))
        close_button.clicked.connect(dialog.close)

        button_layout.addWidget(website_button)
        button_layout.addWidget(github_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        return dialog

    def show_help(self):
        """显示帮助对话框"""
        try:
            self.log_manager.info("请求显示'帮助'对话框")
            # 使用更专业的帮助文档浏览器
            help_dialog = QDialog(self.parent_gui)
            help_dialog.setWindowTitle("帮助文档")
            help_dialog.setModal(True)
            help_dialog.resize(800, 600)

            layout = QVBoxLayout(help_dialog)

            # 帮助内容
            help_content = QTextEdit()
            help_content.setReadOnly(True)
            help_content.setHtml("""
            <h2>HIkyuu量化交易系统 - 用户手册</h2>
            
            <h3>快速开始</h3>
            <p>1. 启动系统后，左侧面板显示股票列表</p>
            <p>2. 点击股票可在中间面板查看K线图</p>
            <p>3. 右侧面板提供分析工具和策略功能</p>
            
            <h3>主要功能</h3>
            <h4>股票筛选</h4>
            <ul>
                <li>支持按市场、行业、关键词筛选</li>
                <li>收藏功能方便管理常用股票</li>
                <li>拖拽操作快速添加到分析列表</li>
            </ul>
            
            <h4>图表分析</h4>
            <ul>
                <li>多种时间周期：分钟、小时、日线、周线、月线</li>
                <li>技术指标：MA、EMA、BOLL、MACD、RSI、KDJ等</li>
                <li>图表控制：缩放、保存、主题切换</li>
            </ul>
            
            <h4>策略分析</h4>
            <ul>
                <li>内置多种经典策略</li>
                <li>支持自定义策略参数</li>
                <li>批量回测和优化</li>
                <li>AI辅助策略推荐</li>
            </ul>
            
            <h3>快捷键</h3>
            <ul>
                <li>Ctrl+N: 新建文件</li>
                <li>Ctrl+O: 打开文件</li>
                <li>Ctrl+S: 保存文件</li>
                <li>F1: 显示帮助</li>
                <li>F11: 全屏模式</li>
            </ul>
            
            <h3>技术支持</h3>
            <p>如有问题，请访问：</p>
            <ul>
                <li>官方网站：https://hikyuu.org</li>
                <li>GitHub：https://github.com/fasiondog/hikyuu</li>
                <li>文档：https://hikyuu.readthedocs.io</li>
            </ul>
            """)
            layout.addWidget(help_content)

            # 关闭按钮
            close_button = QPushButton("关闭")
            close_button.clicked.connect(help_dialog.close)

            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            layout.addLayout(button_layout)

            help_dialog.exec_()

        except Exception as e:
            self.log_manager.error(f"显示帮助文档失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self.parent_gui, "错误", f"显示帮助文档失败: {str(e)}")

    def check_for_updates_worker(self):
        """检查更新的工作线程函数"""
        try:
            self.log_manager.info("正在从远程服务器检查更新...")
            # 模拟网络请求
            QThread.sleep(2)
            # 模拟检查结果
            self.log_manager.info("更新检查完成")
        except Exception as e:
            self.log_manager.error(f"检查更新时出错: {str(e)}", exc_info=True)

    def check_update(self):
        """检查更新"""
        try:
            self.log_manager.info("请求'检查更新'操作")
            progress_dialog = QProgressDialog(
                "正在检查更新，请稍候...", "取消", 0, 0, self.parent_gui)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()

        except Exception as e:
            self.log_manager.error(f"启动更新检查失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self.parent_gui, "错误", f"检查更新失败: {str(e)}")

    def open_url(self, url: str):
        """打开URL"""
        try:
            self.log_manager.info(f"请求打开URL: {url}")
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            self.log_manager.error(f"打开URL失败: {str(e)}", exc_info=True)

    def undo(self):
        """撤销操作"""
        self.log_manager.info("请求'撤销'操作")
        # 这里需要具体的撤销逻辑
        QMessageBox.information(self.parent_gui, "提示", "撤销功能正在开发中")

    def redo(self):
        """重做操作"""
        self.log_manager.info("请求'重做'操作")
        # 这里需要具体的重做逻辑
        QMessageBox.information(self.parent_gui, "提示", "重做功能正在开发中")

    def copy(self):
        """复制操作"""
        self.log_manager.info("请求'复制'操作")
        # 这里需要具体的复制逻辑
        QMessageBox.information(self.parent_gui, "提示", "复制功能正在开发中")

    def paste(self):
        """粘贴操作"""
        self.log_manager.info("请求'粘贴'操作")
        # 这里需要具体的粘贴逻辑
        QMessageBox.information(self.parent_gui, "提示", "粘贴功能正在开发中")

    def set_file_modified(self, modified: bool):
        """设置文件修改状态"""
        self.file_modified = modified

    def get_current_file(self) -> Optional[str]:
        """获取当前文件路径"""
        return self.current_file

    def analyze(self):
        """执行分析"""
        self.log_manager.info("请求'执行分析'操作")
        self.analysis_requested.emit()
        QMessageBox.information(self.parent_gui, "提示", "开始执行分析...")

    def backtest(self):
        """执行回测"""
        self.log_manager.info("请求'执行回测'操作")
        self.backtest_requested.emit()
        QMessageBox.information(self.parent_gui, "提示", "开始执行回测...")

    def optimize(self):
        """执行优化"""
        self.log_manager.info("请求'执行优化'操作")
        self.optimization_requested.emit()
        QMessageBox.information(self.parent_gui, "提示", "开始执行优化...")

    def show_calculator(self):
        """显示计算器"""
        try:
            self.log_manager.info("请求显示'计算器'")
            calculator = Calculator(self.parent_gui)
            calculator.exec_()
        except Exception as e:
            self.log_manager.error(f"显示计算器失败: {str(e)}", exc_info=True)

    def show_converter(self):
        """显示单位转换器"""
        try:
            self.log_manager.info("请求显示'单位转换器'")
            converter = UnitConverter(self.parent_gui)
            converter.exec_()
        except Exception as e:
            self.log_manager.error(f"显示单位转换器失败: {str(e)}", exc_info=True)

    def on_data_source_changed(self, source_name: str):
        """处理数据源切换"""
        try:
            self.log_manager.info(f"请求切换数据源到: {source_name}")
            # 这里需要具体的数据源切换逻辑
            QMessageBox.information(
                self.parent_gui, "提示", f"数据源已切换到: {source_name}")
        except Exception as e:
            self.log_manager.error(f"切换数据源失败: {str(e)}", exc_info=True)

    def show_node_manager(self):
        """显示节点管理器"""
        self.log_manager.info("请求显示'节点管理器'")
        QMessageBox.information(self.parent_gui, "提示", "节点管理功能正在开发中")

    def show_cloud_api_manager(self):
        """显示云API管理器"""
        self.log_manager.info("请求显示'云API管理器'")
        QMessageBox.information(self.parent_gui, "提示", "云API管理功能正在开发中")

    def show_indicator_market(self):
        """显示指标市场"""
        self.log_manager.info("请求显示'指标市场'")
        QMessageBox.information(self.parent_gui, "提示", "指标市场功能正在开发中")

    def show_batch_analysis(self):
        """显示批量分析"""
        self.log_manager.info("请求显示'批量分析'")
        QMessageBox.information(self.parent_gui, "提示", "批量分析功能正在开发中")

    def show_optimization_dashboard(self):
        """显示优化仪表盘"""
        self.log_manager.info("请求显示'优化仪表盘'")
        QMessageBox.information(self.parent_gui, "提示", "优化仪表盘功能正在开发中")

    def run_one_click_optimization(self):
        """运行一键优化"""
        self.log_manager.info("请求'运行一键优化'")
        QMessageBox.information(self.parent_gui, "提示", "一键优化功能正在开发中")

    def run_smart_optimization(self):
        """运行智能优化"""
        self.log_manager.info("请求'运行智能优化'")
        QMessageBox.information(self.parent_gui, "提示", "智能优化功能正在开发中")

    def show_optimization_status(self):
        """显示优化状态"""
        self.log_manager.info("请求显示'优化状态'")
        QMessageBox.information(self.parent_gui, "提示", "优化状态显示功能正在开发中")

    def center_dialog(self, dialog, offset_y=50):
        """将弹窗居中显示"""
        try:
            if self.parent_gui:
                parent_geometry = self.parent_gui.geometry()
                dialog_geometry = dialog.geometry()
                x = parent_geometry.x() + (parent_geometry.width() -
                                           dialog_geometry.width()) / 2
                y = parent_geometry.y() + (parent_geometry.height() -
                                           dialog_geometry.height()) / 2 - offset_y
                dialog.move(int(x), int(y))
        except Exception as e:
            self.log_manager.warning(f"居中弹窗失败: {str(e)}")
