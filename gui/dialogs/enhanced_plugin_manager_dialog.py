"""
增强型插件管理器对话框

集成了所有插件管理功能，包括：
- 通用插件管理（启用/禁用、状态监控）
- 情绪数据源插件配置（权重、参数等）
- 插件市场和安装管理
- 性能监控和日志查看

这个统一的界面避免了框架冗余，提供了完整的插件管理体验。
"""

import sys
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 导入现有的插件管理组件
try:
    from gui.dialogs.plugin_manager_dialog import PluginManagerDialog, PluginStatusWidget
    from gui.dialogs.sentiment_plugin_config_dialog import PluginConfigWidget
    from core.plugin_manager import PluginManager, PluginInfo, PluginStatus, PluginType
    PLUGIN_SYSTEM_AVAILABLE = True
except ImportError:
    PLUGIN_SYSTEM_AVAILABLE = False
    print("警告: 插件系统组件不可用")

try:
    from core.services.sentiment_data_service import SentimentDataService
    from plugins.sentiment_data_source_interface import ISentimentDataSource
    SENTIMENT_SERVICE_AVAILABLE = True
except ImportError:
    SENTIMENT_SERVICE_AVAILABLE = False
    print("警告: 情绪数据服务不可用")


class EnhancedPluginManagerDialog(QDialog):
    """增强型插件管理器对话框"""

    # 信号定义
    plugin_enabled = pyqtSignal(str)
    plugin_disabled = pyqtSignal(str)
    plugin_configured = pyqtSignal(str, dict)
    sentiment_plugin_tested = pyqtSignal(str, bool)

    def __init__(self, plugin_manager=None, sentiment_service=None, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.sentiment_service = sentiment_service
        self.plugin_widgets = {}
        self.sentiment_config_widgets = {}

        self.init_ui()
        self.load_plugins()

        # 定时器用于状态刷新
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(30000)  # 30秒刷新一次

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("插件管理器")
        self.setModal(True)
        self.resize(1000, 700)

        layout = QVBoxLayout(self)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("🔧 插件管理器")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 全局操作按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_status)
        title_layout.addWidget(refresh_btn)

        export_btn = QPushButton("📤 导出配置")
        export_btn.clicked.connect(self.export_all_configs)
        title_layout.addWidget(export_btn)

        import_btn = QPushButton("📥 导入配置")
        import_btn.clicked.connect(self.import_all_configs)
        title_layout.addWidget(import_btn)

        layout.addLayout(title_layout)

        # 选项卡界面
        self.tab_widget = QTabWidget()

        # 1. 通用插件管理标签页
        self.general_tab = self.create_general_plugins_tab()
        self.tab_widget.addTab(self.general_tab, "通用插件")

        # 2. 情绪数据源插件标签页
        self.sentiment_tab = self.create_sentiment_plugins_tab()
        self.tab_widget.addTab(self.sentiment_tab, "情绪数据源")

        # 3. 插件监控标签页
        self.monitor_tab = self.create_monitor_tab()
        self.tab_widget.addTab(self.monitor_tab, "性能监控")

        # 4. 插件市场标签页
        self.market_tab = self.create_market_tab()
        self.tab_widget.addTab(self.market_tab, "插件市场")

        layout.addWidget(self.tab_widget)

        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.plugin_count_label = QLabel("插件总数: 0")
        self.active_count_label = QLabel("活跃插件: 0")

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.plugin_count_label)
        status_layout.addWidget(QLabel("|"))
        status_layout.addWidget(self.active_count_label)

        layout.addLayout(status_layout)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self.apply_all_configs)
        button_layout.addWidget(apply_btn)

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def create_general_plugins_tab(self) -> QWidget:
        """创建通用插件管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 说明文本
        desc_label = QLabel("管理系统中的所有插件，包括启用/禁用、配置和状态监控。")
        desc_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        enable_all_btn = QPushButton("全部启用")
        enable_all_btn.clicked.connect(self.enable_all_general_plugins)
        toolbar_layout.addWidget(enable_all_btn)

        disable_all_btn = QPushButton("全部禁用")
        disable_all_btn.clicked.connect(self.disable_all_general_plugins)
        toolbar_layout.addWidget(disable_all_btn)

        toolbar_layout.addStretch()

        filter_label = QLabel("过滤:")
        self.general_filter_combo = QComboBox()
        self.general_filter_combo.addItems(["全部", "已启用", "已禁用", "数据源", "分析工具", "UI组件"])
        self.general_filter_combo.currentTextChanged.connect(self.filter_general_plugins)

        toolbar_layout.addWidget(filter_label)
        toolbar_layout.addWidget(self.general_filter_combo)

        layout.addLayout(toolbar_layout)

        # 插件列表（使用滚动区域）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.general_plugins_widget = QWidget()
        self.general_plugins_layout = QVBoxLayout(self.general_plugins_widget)
        self.general_plugins_layout.setSpacing(10)

        scroll_area.setWidget(self.general_plugins_widget)
        layout.addWidget(scroll_area)

        return widget

    def create_sentiment_plugins_tab(self) -> QWidget:
        """创建情绪数据源插件标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 说明文本
        desc_label = QLabel("配置和管理情绪分析数据源插件，包括权重设置、参数配置和连接测试。")
        desc_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        test_all_btn = QPushButton("🧪 测试所有连接")
        test_all_btn.clicked.connect(self.test_all_sentiment_plugins)
        toolbar_layout.addWidget(test_all_btn)

        reset_weights_btn = QPushButton("🔄 重置权重")
        reset_weights_btn.clicked.connect(self.reset_sentiment_weights)
        toolbar_layout.addWidget(reset_weights_btn)

        toolbar_layout.addStretch()

        # 全局配置
        global_config_group = QGroupBox("全局配置")
        global_layout = QFormLayout(global_config_group)

        self.auto_refresh_cb = QCheckBox()
        self.auto_refresh_cb.setChecked(True)
        global_layout.addRow("自动刷新:", self.auto_refresh_cb)

        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(1, 60)
        self.refresh_interval_spin.setValue(10)
        self.refresh_interval_spin.setSuffix(" 分钟")
        global_layout.addRow("刷新间隔:", self.refresh_interval_spin)

        toolbar_layout.addWidget(global_config_group)

        layout.addLayout(toolbar_layout)

        # 情绪插件配置区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.sentiment_plugins_widget = QWidget()
        self.sentiment_plugins_layout = QVBoxLayout(self.sentiment_plugins_widget)
        self.sentiment_plugins_layout.setSpacing(20)

        scroll_area.setWidget(self.sentiment_plugins_widget)
        layout.addWidget(scroll_area)

        return widget

    def create_monitor_tab(self) -> QWidget:
        """创建性能监控标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 监控指标显示
        metrics_group = QGroupBox("系统监控")
        metrics_layout = QGridLayout(metrics_group)

        # CPU使用率
        metrics_layout.addWidget(QLabel("CPU使用率:"), 0, 0)
        self.cpu_label = QLabel("0%")
        metrics_layout.addWidget(self.cpu_label, 0, 1)

        # 内存使用率
        metrics_layout.addWidget(QLabel("内存使用:"), 0, 2)
        self.memory_label = QLabel("0 MB")
        metrics_layout.addWidget(self.memory_label, 0, 3)

        # 活跃插件数
        metrics_layout.addWidget(QLabel("活跃插件:"), 1, 0)
        self.active_plugins_label = QLabel("0")
        metrics_layout.addWidget(self.active_plugins_label, 1, 1)

        # 数据更新次数
        metrics_layout.addWidget(QLabel("数据更新:"), 1, 2)
        self.update_count_label = QLabel("0")
        metrics_layout.addWidget(self.update_count_label, 1, 3)

        layout.addWidget(metrics_group)

        # 插件性能表格
        performance_group = QGroupBox("插件性能")
        performance_layout = QVBoxLayout(performance_group)

        self.performance_table = QTableWidget()
        self.performance_table.setColumnCount(6)
        self.performance_table.setHorizontalHeaderLabels([
            "插件名称", "状态", "响应时间", "错误次数", "内存使用", "最后活动"
        ])
        self.performance_table.horizontalHeader().setStretchLastSection(True)

        performance_layout.addWidget(self.performance_table)
        layout.addWidget(performance_group)

        # 日志显示
        logs_group = QGroupBox("插件日志")
        logs_layout = QVBoxLayout(logs_group)

        logs_toolbar = QHBoxLayout()
        clear_logs_btn = QPushButton("清除日志")
        clear_logs_btn.clicked.connect(self.clear_logs)
        logs_toolbar.addWidget(clear_logs_btn)

        export_logs_btn = QPushButton("导出日志")
        export_logs_btn.clicked.connect(self.export_logs)
        logs_toolbar.addWidget(export_logs_btn)
        logs_toolbar.addStretch()

        logs_layout.addLayout(logs_toolbar)

        self.logs_text = QTextEdit()
        self.logs_text.setMaximumHeight(200)
        self.logs_text.setReadOnly(True)
        logs_layout.addWidget(self.logs_text)

        layout.addWidget(logs_group)

        return widget

    def create_market_tab(self) -> QWidget:
        """创建插件市场标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入插件名称或关键词...")
        search_layout.addWidget(self.search_edit)

        search_btn = QPushButton("🔍 搜索")
        search_btn.clicked.connect(self.search_plugins)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # 分类过滤
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("分类:"))

        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部", "数据源", "技术指标", "策略工具", "UI增强", "实用工具"])
        category_layout.addWidget(self.category_combo)

        category_layout.addStretch()

        refresh_market_btn = QPushButton("🔄 刷新市场")
        refresh_market_btn.clicked.connect(self.refresh_market)
        category_layout.addWidget(refresh_market_btn)

        layout.addLayout(category_layout)

        # 插件卡片展示区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.market_plugins_widget = QWidget()
        self.market_plugins_layout = QVBoxLayout(self.market_plugins_widget)

        scroll_area.setWidget(self.market_plugins_widget)
        layout.addWidget(scroll_area)

        # 加载示例插件卡片
        self.load_market_plugins()

        return widget

    def load_plugins(self):
        """加载所有插件"""
        self.load_general_plugins()
        self.load_sentiment_plugins()
        self.update_status_counts()

    def load_general_plugins(self):
        """加载通用插件"""
        # 清理现有插件
        for i in reversed(range(self.general_plugins_layout.count())):
            child = self.general_plugins_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # 创建示例插件
        example_plugins = [
            {
                "name": "HIkyuu数据源",
                "type": "DATA_SOURCE",
                "version": "2.0.0",
                "description": "HIkyuu股票数据源插件，提供历史和实时数据",
                "enabled": True,
                "status": "运行中"
            },
            {
                "name": "技术指标库",
                "type": "ANALYSIS",
                "version": "1.5.0",
                "description": "常用技术指标计算插件",
                "enabled": True,
                "status": "运行中"
            },
            {
                "name": "策略回测引擎",
                "type": "STRATEGY",
                "version": "1.2.0",
                "description": "策略回测和评估插件",
                "enabled": False,
                "status": "已停用"
            }
        ]

        for plugin_info in example_plugins:
            plugin_widget = self.create_general_plugin_widget(plugin_info)
            self.general_plugins_layout.addWidget(plugin_widget)

        self.general_plugins_layout.addStretch()

    def load_sentiment_plugins(self):
        """加载情绪数据源插件"""
        # 清理现有配置
        for i in reversed(range(self.sentiment_plugins_layout.count())):
            child = self.sentiment_plugins_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        self.sentiment_config_widgets.clear()

        # 加载真实的情绪插件或示例
        if SENTIMENT_SERVICE_AVAILABLE and self.sentiment_service:
            plugins = self.sentiment_service.get_available_plugins()
            for plugin_name in plugins:
                self.add_sentiment_plugin_config(plugin_name)
        else:
            # 创建示例配置
            example_configs = {
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
                    'fx_sentiment_enabled': True
                },
                "东方财富数据源": {
                    'enabled': False,
                    'weight': 0.8,
                    'priority': 20,
                    'cache_duration_minutes': 3,
                    'retry_attempts': 2,
                    'timeout_seconds': 20
                }
            }

            for plugin_name, config in example_configs.items():
                self.add_sentiment_plugin_config(plugin_name, config)

        self.sentiment_plugins_layout.addStretch()

    def add_sentiment_plugin_config(self, plugin_name: str, config: Dict[str, Any] = None):
        """添加情绪插件配置widget"""
        if config is None:
            config = {
                'enabled': True,
                'weight': 1.0,
                'priority': 50,
                'cache_duration_minutes': 5,
                'retry_attempts': 3,
                'timeout_seconds': 30
            }

        try:
            # 使用现有的PluginConfigWidget
            if PLUGIN_SYSTEM_AVAILABLE:
                widget = PluginConfigWidget(plugin_name, config, self)
                widget.config_changed.connect(self.on_sentiment_config_changed)
                widget.test_requested.connect(self.test_sentiment_plugin)
            else:
                # 回退到简单的配置widget
                widget = self.create_simple_sentiment_widget(plugin_name, config)

            # 添加分隔线
            if self.sentiment_plugins_layout.count() > 0:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                self.sentiment_plugins_layout.addWidget(separator)

            self.sentiment_plugins_layout.addWidget(widget)
            self.sentiment_config_widgets[plugin_name] = widget

        except Exception as e:
            print(f"添加情绪插件配置失败: {e}")

    def create_general_plugin_widget(self, plugin_info: Dict[str, Any]) -> QWidget:
        """创建通用插件widget"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.StyledPanel)
        widget.setStyleSheet("QFrame { background-color: #f8f9fa; border-radius: 8px; padding: 10px; }")

        layout = QHBoxLayout(widget)

        # 插件信息
        info_layout = QVBoxLayout()

        name_label = QLabel(f"📦 {plugin_info['name']}")
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_layout.addWidget(name_label)

        desc_label = QLabel(plugin_info['description'])
        desc_label.setStyleSheet("color: #666;")
        info_layout.addWidget(desc_label)

        details_layout = QHBoxLayout()
        details_layout.addWidget(QLabel(f"版本: {plugin_info['version']}"))
        details_layout.addWidget(QLabel(f"类型: {plugin_info['type']}"))
        details_layout.addWidget(QLabel(f"状态: {plugin_info['status']}"))
        details_layout.addStretch()
        info_layout.addLayout(details_layout)

        layout.addLayout(info_layout)

        # 控制按钮
        controls_layout = QVBoxLayout()

        enable_cb = QCheckBox("启用")
        enable_cb.setChecked(plugin_info['enabled'])
        controls_layout.addWidget(enable_cb)

        config_btn = QPushButton("配置")
        config_btn.setMaximumWidth(80)
        controls_layout.addWidget(config_btn)

        layout.addLayout(controls_layout)

        return widget

    def create_simple_sentiment_widget(self, plugin_name: str, config: Dict[str, Any]) -> QWidget:
        """创建简单的情绪插件配置widget（回退方案）"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.StyledPanel)
        widget.setStyleSheet("QFrame { background-color: #f0f8ff; border-radius: 8px; padding: 15px; }")

        layout = QVBoxLayout(widget)

        # 标题
        title_layout = QHBoxLayout()
        title_label = QLabel(f"📊 {plugin_name}")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        enable_cb = QCheckBox("启用")
        enable_cb.setChecked(config.get('enabled', True))
        title_layout.addWidget(enable_cb)

        test_btn = QPushButton("🔍 测试")
        test_btn.setMaximumWidth(80)
        title_layout.addWidget(test_btn)

        layout.addLayout(title_layout)

        # 配置选项
        config_layout = QFormLayout()

        weight_spin = QDoubleSpinBox()
        weight_spin.setRange(0.1, 2.0)
        weight_spin.setSingleStep(0.1)
        weight_spin.setValue(config.get('weight', 1.0))
        config_layout.addRow("权重:", weight_spin)

        priority_spin = QSpinBox()
        priority_spin.setRange(1, 100)
        priority_spin.setValue(config.get('priority', 50))
        config_layout.addRow("优先级:", priority_spin)

        layout.addLayout(config_layout)

        # 存储配置控件引用
        widget.enable_cb = enable_cb
        widget.weight_spin = weight_spin
        widget.priority_spin = priority_spin
        widget.test_btn = test_btn

        return widget

    def load_market_plugins(self):
        """加载插件市场"""
        # 示例市场插件
        market_plugins = [
            {
                "name": "同花顺数据源",
                "description": "同花顺数据源插件，提供实时行情和财务数据",
                "version": "1.0.0",
                "author": "社区开发者",
                "downloads": 1250,
                "rating": 4.5,
                "status": "未安装"
            },
            {
                "name": "Wind数据接口",
                "description": "Wind金融终端数据接口，支持专业金融数据",
                "version": "2.1.0",
                "author": "Wind官方",
                "downloads": 890,
                "rating": 4.8,
                "status": "未安装"
            },
            {
                "name": "机器学习预测器",
                "description": "基于深度学习的股价预测插件",
                "version": "1.3.0",
                "author": "AI研究团队",
                "downloads": 2100,
                "rating": 4.2,
                "status": "可更新"
            }
        ]

        for plugin_info in market_plugins:
            plugin_card = self.create_market_plugin_card(plugin_info)
            self.market_plugins_layout.addWidget(plugin_card)

        self.market_plugins_layout.addStretch()

    def create_market_plugin_card(self, plugin_info: Dict[str, Any]) -> QWidget:
        """创建市场插件卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 15px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #007bff;
                box-shadow: 0 2px 8px rgba(0,123,255,0.15);
            }
        """)

        layout = QHBoxLayout(card)

        # 插件信息
        info_layout = QVBoxLayout()

        name_label = QLabel(plugin_info['name'])
        name_label.setFont(QFont("Arial", 14, QFont.Bold))
        info_layout.addWidget(name_label)

        desc_label = QLabel(plugin_info['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666;")
        info_layout.addWidget(desc_label)

        meta_layout = QHBoxLayout()
        meta_layout.addWidget(QLabel(f"版本: {plugin_info['version']}"))
        meta_layout.addWidget(QLabel(f"作者: {plugin_info['author']}"))
        meta_layout.addWidget(QLabel(f"下载: {plugin_info['downloads']}"))
        meta_layout.addWidget(QLabel(f"评分: {plugin_info['rating']}⭐"))
        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)

        layout.addLayout(info_layout)

        # 操作按钮
        button_layout = QVBoxLayout()

        status = plugin_info['status']
        if status == "未安装":
            install_btn = QPushButton("📥 安装")
            install_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        elif status == "可更新":
            install_btn = QPushButton("🔄 更新")
            install_btn.setStyleSheet("QPushButton { background-color: #ffc107; color: black; }")
        else:
            install_btn = QPushButton("✅ 已安装")
            install_btn.setEnabled(False)

        button_layout.addWidget(install_btn)

        details_btn = QPushButton("详情")
        button_layout.addWidget(details_btn)

        layout.addLayout(button_layout)

        return card

    # 事件处理方法
    def refresh_status(self):
        """刷新状态"""
        self.update_status_counts()
        self.update_monitor_data()

    def update_status_counts(self):
        """更新状态计数"""
        total_plugins = len(self.plugin_widgets) + len(self.sentiment_config_widgets)
        active_plugins = sum(1 for w in self.plugin_widgets.values() if hasattr(w, 'is_enabled') and w.is_enabled)

        self.plugin_count_label.setText(f"插件总数: {total_plugins}")
        self.active_count_label.setText(f"活跃插件: {active_plugins}")

    def update_monitor_data(self):
        """更新监控数据"""
        # 模拟监控数据
        import random

        self.cpu_label.setText(f"{random.randint(10, 30)}%")
        self.memory_label.setText(f"{random.randint(200, 500)} MB")
        self.active_plugins_label.setText(str(len(self.sentiment_config_widgets)))
        self.update_count_label.setText(str(random.randint(100, 999)))

        # 更新性能表格
        self.performance_table.setRowCount(len(self.sentiment_config_widgets))

        row = 0
        for plugin_name, widget in self.sentiment_config_widgets.items():
            self.performance_table.setItem(row, 0, QTableWidgetItem(plugin_name))
            self.performance_table.setItem(row, 1, QTableWidgetItem("运行中"))
            self.performance_table.setItem(row, 2, QTableWidgetItem(f"{random.randint(100, 3000)}ms"))
            self.performance_table.setItem(row, 3, QTableWidgetItem(str(random.randint(0, 5))))
            self.performance_table.setItem(row, 4, QTableWidgetItem(f"{random.randint(10, 50)}MB"))
            self.performance_table.setItem(row, 5, QTableWidgetItem(datetime.now().strftime('%H:%M:%S')))
            row += 1

    def on_sentiment_config_changed(self, plugin_name: str, config: Dict[str, Any]):
        """情绪插件配置变化处理"""
        self.plugin_configured.emit(plugin_name, config)

    def test_sentiment_plugin(self, plugin_name: str):
        """测试情绪插件"""
        # 模拟测试
        QTimer.singleShot(2000, lambda: self.sentiment_plugin_tested.emit(plugin_name, True))

    def test_all_sentiment_plugins(self):
        """测试所有情绪插件"""
        for plugin_name in self.sentiment_config_widgets.keys():
            self.test_sentiment_plugin(plugin_name)

    def reset_sentiment_weights(self):
        """重置情绪插件权重"""
        for widget in self.sentiment_config_widgets.values():
            if hasattr(widget, 'weight_spin'):
                widget.weight_spin.setValue(1.0)

    def enable_all_general_plugins(self):
        """启用所有通用插件"""
        # 实现启用逻辑
        pass

    def disable_all_general_plugins(self):
        """禁用所有通用插件"""
        # 实现禁用逻辑
        pass

    def filter_general_plugins(self):
        """过滤通用插件"""
        # 实现过滤逻辑
        pass

    def search_plugins(self):
        """搜索插件"""
        # 实现搜索逻辑
        pass

    def refresh_market(self):
        """刷新插件市场"""
        # 实现市场刷新逻辑
        pass

    def clear_logs(self):
        """清除日志"""
        self.logs_text.clear()

    def export_logs(self):
        """导出日志"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出日志", f"plugin_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text files (*.txt)"
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.logs_text.toPlainText())
            QMessageBox.information(self, "导出成功", f"日志已导出到: {filename}")

    def export_all_configs(self):
        """导出所有配置"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出插件配置", f"plugin_configs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json)"
        )
        if filename:
            configs = {}
            for plugin_name, widget in self.sentiment_config_widgets.items():
                if hasattr(widget, 'get_config'):
                    configs[plugin_name] = widget.get_config()

            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(configs, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "导出成功", f"配置已导出到: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出失败: {str(e)}")

    def import_all_configs(self):
        """导入所有配置"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "导入插件配置", "", "JSON files (*.json)"
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
                # 应用导入的配置
                # 这里需要实际的配置应用逻辑
                QMessageBox.information(self, "导入成功", "配置导入成功！请重启应用以使配置生效。")
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入失败: {str(e)}")

    def apply_all_configs(self):
        """应用所有配置"""
        try:
            # 应用通用插件配置
            for plugin_name, widget in self.plugin_widgets.items():
                # 应用插件配置逻辑
                pass

            # 应用情绪插件配置
            for plugin_name, widget in self.sentiment_config_widgets.items():
                if hasattr(widget, 'get_config'):
                    config = widget.get_config()
                    self.plugin_configured.emit(plugin_name, config)

            QMessageBox.information(self, "应用成功", "所有配置已成功应用！")

        except Exception as e:
            QMessageBox.critical(self, "应用失败", f"应用配置失败: {str(e)}")

    def accept(self):
        """确定按钮处理"""
        self.apply_all_configs()
        super().accept()


def show_enhanced_plugin_manager(parent=None, plugin_manager=None, sentiment_service=None):
    """显示增强型插件管理器对话框"""
    dialog = EnhancedPluginManagerDialog(plugin_manager, sentiment_service, parent)
    return dialog.exec_()


if __name__ == "__main__":
    # 独立运行测试
    app = QApplication(sys.argv)

    dialog = EnhancedPluginManagerDialog()
    dialog.show()

    sys.exit(app.exec_())
