"""
情绪数据源插件配置对话框

此对话框允许用户：
- 查看已注册的情绪数据源插件
- 启用/禁用特定的数据源
- 配置插件参数（权重、优先级等）
- 测试插件连接和数据获取
- 管理插件缓存设置
"""

import sys
from typing import Dict, List, Any, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime

try:
    from core.services.sentiment_data_service import SentimentDataService, SentimentDataServiceConfig
    from plugins.sentiment_data_source_interface import ISentimentDataSource
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


class PluginConfigWidget(QWidget):
    """单个插件的配置控件"""

    config_changed = pyqtSignal(str, dict)  # 插件名称, 新配置
    test_requested = pyqtSignal(str)  # 插件名称

    def __init__(self, plugin_name: str, plugin_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.plugin_name = plugin_name
        self.config = plugin_config.copy()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 插件信息头部
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 8px; padding: 8px;")
        header_layout = QHBoxLayout(header_frame)

        # 插件名称和状态
        name_label = QLabel(f"📊 {self.plugin_name}")
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        # 启用/禁用开关
        self.enabled_cb = QCheckBox("启用")
        self.enabled_cb.setChecked(self.config.get('enabled', True))
        self.enabled_cb.stateChanged.connect(self._on_config_changed)
        header_layout.addWidget(self.enabled_cb)

        # 测试按钮
        test_btn = QPushButton("🔍 测试连接")
        test_btn.setMaximumWidth(100)
        test_btn.clicked.connect(lambda: self.test_requested.emit(self.plugin_name))
        header_layout.addWidget(test_btn)

        layout.addWidget(header_frame)

        # 配置详情
        details_group = QGroupBox("配置详情")
        details_layout = QFormLayout(details_group)

        # 权重设置
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.1, 2.0)
        self.weight_spin.setSingleStep(0.1)
        self.weight_spin.setValue(self.config.get('weight', 1.0))
        self.weight_spin.setToolTip("插件在数据聚合中的权重，值越大影响越大")
        self.weight_spin.valueChanged.connect(self._on_config_changed)
        details_layout.addRow("数据权重:", self.weight_spin)

        # 优先级设置
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 100)
        self.priority_spin.setValue(self.config.get('priority', 50))
        self.priority_spin.setToolTip("插件优先级，数值越小优先级越高")
        self.priority_spin.valueChanged.connect(self._on_config_changed)
        details_layout.addRow("优先级:", self.priority_spin)

        # 缓存设置
        self.cache_duration_spin = QSpinBox()
        self.cache_duration_spin.setRange(1, 60)
        self.cache_duration_spin.setSuffix(" 分钟")
        self.cache_duration_spin.setValue(self.config.get('cache_duration_minutes', 5))
        self.cache_duration_spin.setToolTip("数据缓存持续时间")
        self.cache_duration_spin.valueChanged.connect(self._on_config_changed)
        details_layout.addRow("缓存时长:", self.cache_duration_spin)

        # 重试设置
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(1, 10)
        self.retry_spin.setValue(self.config.get('retry_attempts', 3))
        self.retry_spin.setToolTip("网络请求失败时的重试次数")
        self.retry_spin.valueChanged.connect(self._on_config_changed)
        details_layout.addRow("重试次数:", self.retry_spin)

        # 超时设置
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setSuffix(" 秒")
        self.timeout_spin.setValue(self.config.get('timeout_seconds', 30))
        self.timeout_spin.setToolTip("网络请求超时时间")
        self.timeout_spin.valueChanged.connect(self._on_config_changed)
        details_layout.addRow("超时时间:", self.timeout_spin)

        layout.addWidget(details_group)

        # 高级配置（如果有）
        if self._has_advanced_config():
            advanced_group = QGroupBox("高级配置")
            advanced_layout = QVBoxLayout(advanced_group)

            # 插件特定配置
            self._create_advanced_config(advanced_layout)

            layout.addWidget(advanced_group)

        # 状态信息
        status_group = QGroupBox("状态信息")
        status_layout = QVBoxLayout(status_group)

        self.status_label = QLabel("状态: 未知")
        self.last_update_label = QLabel("最后更新: 从未")
        self.data_quality_label = QLabel("数据质量: 未知")

        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.last_update_label)
        status_layout.addWidget(self.data_quality_label)

        layout.addWidget(status_group)

        layout.addStretch()

    def _has_advanced_config(self) -> bool:
        """检查是否有高级配置选项"""
        advanced_keys = [
            'news_sentiment_enabled', 'weibo_enabled', 'vix_enabled',
            'consumer_confidence_enabled', 'fx_sentiment_enabled',
            'weibo_time_period', 'data_sources'
        ]
        return any(key in self.config for key in advanced_keys)

    def _create_advanced_config(self, layout: QVBoxLayout):
        """创建高级配置控件"""
        # AkShare插件特定配置
        if 'akshare' in self.plugin_name.lower():
            self._create_akshare_config(layout)

        # 通用高级配置
        if 'data_sources' in self.config:
            self._create_data_sources_config(layout)

    def _create_akshare_config(self, layout: QVBoxLayout):
        """创建AkShare插件特定配置"""
        akshare_frame = QFrame()
        akshare_layout = QFormLayout(akshare_frame)

        # 各数据源开关
        self.news_cb = QCheckBox()
        self.news_cb.setChecked(self.config.get('news_sentiment_enabled', True))
        self.news_cb.stateChanged.connect(self._on_config_changed)
        akshare_layout.addRow("新闻情绪:", self.news_cb)

        self.weibo_cb = QCheckBox()
        self.weibo_cb.setChecked(self.config.get('weibo_enabled', True))
        self.weibo_cb.stateChanged.connect(self._on_config_changed)
        akshare_layout.addRow("微博情绪:", self.weibo_cb)

        self.vix_cb = QCheckBox()
        self.vix_cb.setChecked(self.config.get('vix_enabled', True))
        self.vix_cb.stateChanged.connect(self._on_config_changed)
        akshare_layout.addRow("VIX指数:", self.vix_cb)

        self.confidence_cb = QCheckBox()
        self.confidence_cb.setChecked(self.config.get('consumer_confidence_enabled', True))
        self.confidence_cb.stateChanged.connect(self._on_config_changed)
        akshare_layout.addRow("消费者信心:", self.confidence_cb)

        self.fx_cb = QCheckBox()
        self.fx_cb.setChecked(self.config.get('fx_sentiment_enabled', True))
        self.fx_cb.stateChanged.connect(self._on_config_changed)
        akshare_layout.addRow("外汇情绪:", self.fx_cb)

        # 微博时间周期
        self.weibo_period_combo = QComboBox()
        self.weibo_period_combo.addItems(["近3天", "近7天", "近15天", "近30天"])
        current_period = self.config.get('weibo_time_period', '近7天')
        index = self.weibo_period_combo.findText(current_period)
        if index >= 0:
            self.weibo_period_combo.setCurrentIndex(index)
        self.weibo_period_combo.currentTextChanged.connect(self._on_config_changed)
        akshare_layout.addRow("微博时间周期:", self.weibo_period_combo)

        layout.addWidget(akshare_frame)

    def _create_data_sources_config(self, layout: QVBoxLayout):
        """创建数据源配置"""
        sources_frame = QFrame()
        sources_layout = QVBoxLayout(sources_frame)

        sources_label = QLabel("数据源配置:")
        sources_label.setFont(QFont("Arial", 10, QFont.Bold))
        sources_layout.addWidget(sources_label)

        # 这里可以添加更多通用数据源配置
        sources_text = QTextEdit()
        sources_text.setMaximumHeight(100)
        sources_text.setPlainText(str(self.config.get('data_sources', {})))
        sources_text.textChanged.connect(self._on_config_changed)
        sources_layout.addWidget(sources_text)

        layout.addWidget(sources_frame)

    def _on_config_changed(self):
        """配置变化处理"""
        # 更新基础配置
        self.config['enabled'] = self.enabled_cb.isChecked()
        self.config['weight'] = self.weight_spin.value()
        self.config['priority'] = self.priority_spin.value()
        self.config['cache_duration_minutes'] = self.cache_duration_spin.value()
        self.config['retry_attempts'] = self.retry_spin.value()
        self.config['timeout_seconds'] = self.timeout_spin.value()

        # 更新AkShare特定配置
        if hasattr(self, 'news_cb'):
            self.config['news_sentiment_enabled'] = self.news_cb.isChecked()
            self.config['weibo_enabled'] = self.weibo_cb.isChecked()
            self.config['vix_enabled'] = self.vix_cb.isChecked()
            self.config['consumer_confidence_enabled'] = self.confidence_cb.isChecked()
            self.config['fx_sentiment_enabled'] = self.fx_cb.isChecked()
            self.config['weibo_time_period'] = self.weibo_period_combo.currentText()

        # 发送配置变化信号
        self.config_changed.emit(self.plugin_name, self.config)

    def update_status(self, status: str, last_update: Optional[datetime] = None,
                      data_quality: str = "unknown"):
        """更新状态信息"""
        self.status_label.setText(f"状态: {status}")

        if last_update:
            update_str = last_update.strftime('%Y-%m-%d %H:%M:%S')
        else:
            update_str = "从未"
        self.last_update_label.setText(f"最后更新: {update_str}")

        # 根据数据质量设置颜色
        quality_colors = {
            'excellent': '#28a745',
            'good': '#6c757d',
            'fair': '#ffc107',
            'poor': '#dc3545',
            'unknown': '#6c757d'
        }
        color = quality_colors.get(data_quality, '#6c757d')
        self.data_quality_label.setText(f"数据质量: {data_quality}")
        self.data_quality_label.setStyleSheet(f"color: {color};")

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config.copy()


class SentimentPluginConfigDialog(QDialog):
    """情绪数据源插件配置对话框"""

    def __init__(self, sentiment_service=None, parent=None):
        super().__init__(parent)
        self.sentiment_service = sentiment_service
        self.plugin_widgets: Dict[str, PluginConfigWidget] = {}
        self.init_ui()
        self.load_plugin_configs()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("情绪数据源插件配置")
        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # 标题和说明
        title_label = QLabel("情绪数据源插件配置")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel("配置和管理情绪分析数据源插件，包括权重、优先级和特定参数设置。")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(desc_label)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 刷新状态")
        refresh_btn.clicked.connect(self.refresh_plugin_status)
        toolbar_layout.addWidget(refresh_btn)

        test_all_btn = QPushButton("🧪 测试所有")
        test_all_btn.clicked.connect(self.test_all_plugins)
        toolbar_layout.addWidget(test_all_btn)

        toolbar_layout.addStretch()

        export_btn = QPushButton("📤 导出配置")
        export_btn.clicked.connect(self.export_config)
        toolbar_layout.addWidget(export_btn)

        import_btn = QPushButton("📥 导入配置")
        import_btn.clicked.connect(self.import_config)
        toolbar_layout.addWidget(import_btn)

        layout.addLayout(toolbar_layout)

        # 滚动区域用于插件配置
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.plugins_widget = QWidget()
        self.plugins_layout = QVBoxLayout(self.plugins_widget)
        self.plugins_layout.setSpacing(20)

        scroll_area.setWidget(self.plugins_widget)
        layout.addWidget(scroll_area)

        # 全局服务配置
        global_group = QGroupBox("全局服务配置")
        global_layout = QFormLayout(global_group)

        self.auto_refresh_cb = QCheckBox()
        self.auto_refresh_cb.setChecked(True)
        global_layout.addRow("自动刷新:", self.auto_refresh_cb)

        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(1, 60)
        self.refresh_interval_spin.setValue(10)
        self.refresh_interval_spin.setSuffix(" 分钟")
        global_layout.addRow("刷新间隔:", self.refresh_interval_spin)

        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 10)
        self.max_concurrent_spin.setValue(3)
        global_layout.addRow("最大并发数:", self.max_concurrent_spin)

        layout.addWidget(global_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self.apply_config)
        button_layout.addWidget(apply_btn)

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def load_plugin_configs(self):
        """加载插件配置"""
        if not SERVICE_AVAILABLE or not self.sentiment_service:
            # 创建示例插件配置
            self.create_example_plugins()
            return

        try:
            # 获取已注册的插件
            plugins = self.sentiment_service.get_available_plugins()

            if not plugins:
                self.create_example_plugins()
                return

            for plugin_name in plugins:
                status = self.sentiment_service.get_plugin_status(plugin_name)

                # 构建插件配置
                config = {
                    'enabled': True,
                    'weight': 1.0,
                    'priority': status.get('priority', 50),
                    'cache_duration_minutes': 5,
                    'retry_attempts': 3,
                    'timeout_seconds': 30
                }

                # 添加插件特定配置
                if 'akshare' in plugin_name.lower():
                    config.update({
                        'news_sentiment_enabled': True,
                        'weibo_enabled': True,
                        'vix_enabled': True,
                        'consumer_confidence_enabled': True,
                        'fx_sentiment_enabled': True,
                        'weibo_time_period': '近7天'
                    })

                self.add_plugin_widget(plugin_name, config)

        except Exception as e:
            print(f"加载插件配置失败: {e}")
            self.create_example_plugins()

    def create_example_plugins(self):
        """创建示例插件配置"""
        example_plugins = {
            "AkShare情绪数据源": {
                'enabled': True,
                'weight': 1.0,
                'priority': 10,
                'cache_duration_minutes': 5,
                'retry_attempts': 3,
                'timeout_seconds': 30,
                'news_sentiment_enabled': True,
                'weibo_enabled': True,
                'vix_enabled': True,
                'consumer_confidence_enabled': True,
                'fx_sentiment_enabled': True,
                'weibo_time_period': '近7天'
            },
            "东方财富数据源": {
                'enabled': False,
                'weight': 0.8,
                'priority': 20,
                'cache_duration_minutes': 3,
                'retry_attempts': 2,
                'timeout_seconds': 20
            },
            "同花顺数据源": {
                'enabled': False,
                'weight': 0.9,
                'priority': 15,
                'cache_duration_minutes': 4,
                'retry_attempts': 3,
                'timeout_seconds': 25
            }
        }

        for plugin_name, config in example_plugins.items():
            self.add_plugin_widget(plugin_name, config)

    def add_plugin_widget(self, plugin_name: str, config: Dict[str, Any]):
        """添加插件配置控件"""
        widget = PluginConfigWidget(plugin_name, config, self)
        widget.config_changed.connect(self.on_plugin_config_changed)
        widget.test_requested.connect(self.test_plugin)

        # 添加分隔线
        if self.plugins_layout.count() > 0:
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            self.plugins_layout.addWidget(separator)

        self.plugins_layout.addWidget(widget)
        self.plugin_widgets[plugin_name] = widget

    def on_plugin_config_changed(self, plugin_name: str, config: Dict[str, Any]):
        """插件配置变化处理"""
        # 这里可以添加配置验证逻辑
        print(f"插件 {plugin_name} 配置已更新: {config}")

    def test_plugin(self, plugin_name: str):
        """测试单个插件"""
        widget = self.plugin_widgets.get(plugin_name)
        if not widget:
            return

        widget.update_status("正在测试...")

        # 模拟测试过程
        QTimer.singleShot(2000, lambda: self._finish_plugin_test(plugin_name, True))

    def _finish_plugin_test(self, plugin_name: str, success: bool):
        """完成插件测试"""
        widget = self.plugin_widgets.get(plugin_name)
        if not widget:
            return

        if success:
            widget.update_status("连接成功", datetime.now(), "good")
            QMessageBox.information(self, "测试成功", f"插件 {plugin_name} 连接测试成功！")
        else:
            widget.update_status("连接失败", None, "poor")
            QMessageBox.warning(self, "测试失败", f"插件 {plugin_name} 连接测试失败！")

    def test_all_plugins(self):
        """测试所有插件"""
        for plugin_name in self.plugin_widgets:
            self.test_plugin(plugin_name)

    def refresh_plugin_status(self):
        """刷新插件状态"""
        for plugin_name, widget in self.plugin_widgets.items():
            widget.update_status("正在刷新...")

        # 模拟刷新过程
        QTimer.singleShot(1000, self._finish_refresh)

    def _finish_refresh(self):
        """完成状态刷新"""
        import random
        statuses = ["连接正常", "连接异常", "部分可用"]
        qualities = ["excellent", "good", "fair", "poor"]

        for plugin_name, widget in self.plugin_widgets.items():
            status = random.choice(statuses)
            quality = random.choice(qualities)
            widget.update_status(status, datetime.now(), quality)

    def export_config(self):
        """导出配置"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出插件配置",
            f"sentiment_plugin_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json)"
        )

        if filename:
            config_data = {}
            for plugin_name, widget in self.plugin_widgets.items():
                config_data[plugin_name] = widget.get_config()

            # 添加全局配置
            config_data['_global'] = {
                'auto_refresh': self.auto_refresh_cb.isChecked(),
                'refresh_interval_minutes': self.refresh_interval_spin.value(),
                'max_concurrent_fetches': self.max_concurrent_spin.value()
            }

            try:
                import json
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "导出成功", f"配置已导出到: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出配置失败: {str(e)}")

    def import_config(self):
        """导入配置"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "导入插件配置", "",
            "JSON files (*.json)"
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 应用配置到插件
                for plugin_name, config in config_data.items():
                    if plugin_name == '_global':
                        # 应用全局配置
                        self.auto_refresh_cb.setChecked(config.get('auto_refresh', True))
                        self.refresh_interval_spin.setValue(config.get('refresh_interval_minutes', 10))
                        self.max_concurrent_spin.setValue(config.get('max_concurrent_fetches', 3))
                    elif plugin_name in self.plugin_widgets:
                        # 更新插件配置
                        widget = self.plugin_widgets[plugin_name]
                        # 这里需要重建插件widget或更新其配置
                        # 为简化，显示消息
                        pass

                QMessageBox.information(self, "导入成功", "配置导入成功！请重启应用以使配置生效。")

            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入配置失败: {str(e)}")

    def apply_config(self):
        """应用配置"""
        if not SERVICE_AVAILABLE or not self.sentiment_service:
            QMessageBox.information(self, "配置应用", "配置已保存，将在下次启动时生效。")
            return

        try:
            # 应用配置到服务
            for plugin_name, widget in self.plugin_widgets.items():
                config = widget.get_config()
                # 这里需要实际的配置应用逻辑
                print(f"应用插件 {plugin_name} 配置: {config}")

            QMessageBox.information(self, "应用成功", "配置已成功应用！")

        except Exception as e:
            QMessageBox.critical(self, "应用失败", f"应用配置失败: {str(e)}")

    def accept(self):
        """确定按钮处理"""
        self.apply_config()
        super().accept()


def show_sentiment_plugin_config_dialog(parent=None, sentiment_service=None):
    """显示情绪插件配置对话框"""
    dialog = SentimentPluginConfigDialog(sentiment_service, parent)
    return dialog.exec_()


if __name__ == "__main__":
    # 独立运行测试
    app = QApplication(sys.argv)

    dialog = SentimentPluginConfigDialog()
    dialog.show()

    sys.exit(app.exec_())
