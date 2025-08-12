"""
数据源插件配置对话框

提供数据源插件的详细配置功能，包括：
- 插件基本配置（连接参数、认证信息等）
- 路由权重和优先级设置
- 健康检查和监控配置
- 插件测试和验证

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QCheckBox, QTextEdit, QProgressBar, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QWidget, QSplitter, QListWidget, QListWidgetItem, QSlider,
    QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from core.logger import get_logger

logger = get_logger(__name__)


class HealthCheckWorker(QThread):
    """健康检查工作线程"""

    health_result = pyqtSignal(bool, float, str)  # is_healthy, response_time, message

    def __init__(self, source_id):
        super().__init__()
        self.source_id = source_id
        self.running = False

    def run(self):
        """执行健康检查"""
        self.running = True
        try:
            from core.services.unified_data_manager import get_unified_data_manager

            unified_manager = get_unified_data_manager()
            if not unified_manager or not hasattr(unified_manager, 'data_source_router'):
                self.health_result.emit(False, 0.0, "数据源路由器未启用")
                return

            router = unified_manager.data_source_router
            if self.source_id not in router.data_sources:
                self.health_result.emit(False, 0.0, f"插件 {self.source_id} 不存在")
                return

            # 执行健康检查
            start_time = time.time()
            adapter = router.data_sources[self.source_id]
            health_result = adapter.health_check()
            response_time = (time.time() - start_time) * 1000

            self.health_result.emit(
                health_result.is_healthy,
                response_time,
                health_result.error_message or "健康检查通过"
            )

        except Exception as e:
            self.health_result.emit(False, 0.0, f"健康检查失败: {str(e)}")
        finally:
            self.running = False

    def stop(self):
        """停止健康检查"""
        self.running = False


class DataSourcePluginConfigDialog(QDialog):
    """数据源插件配置对话框"""

    config_changed = pyqtSignal(str, dict)  # source_id, config

    def __init__(self, source_id: str, parent=None):
        super().__init__(parent)
        self.source_id = source_id
        self.adapter = None
        self.plugin_info = None
        self.current_config = {}
        self.health_worker = None

        self.setWindowTitle(f"配置数据源插件 - {source_id}")
        self.setModal(True)
        self.resize(800, 600)

        self.init_ui()
        self.load_plugin_info()
        self.load_config()

        # 启动定时器进行周期性健康检查
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self.check_health)
        self.health_timer.start(5000)  # 5秒间隔

    def init_ui(self):
        """初始化UI"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #495057;
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
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #007bff;
                outline: none;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                background-color: white;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #e9ecef;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
        """)

        layout = QVBoxLayout(self)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel(f"🔧 配置数据源插件")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 状态指示器
        self.status_label = QLabel("🔴 未连接")
        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        title_layout.addWidget(self.status_label)

        layout.addLayout(title_layout)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 1. 基本配置标签页
        self.basic_tab = self.create_basic_config_tab()
        self.tab_widget.addTab(self.basic_tab, "基本配置")

        # 2. 路由配置标签页
        self.routing_tab = self.create_routing_config_tab()
        self.tab_widget.addTab(self.routing_tab, "路由配置")

        # 3. 健康监控标签页
        self.monitoring_tab = self.create_monitoring_tab()
        self.tab_widget.addTab(self.monitoring_tab, "健康监控")

        # 4. 高级设置标签页
        self.advanced_tab = self.create_advanced_config_tab()
        self.tab_widget.addTab(self.advanced_tab, "高级设置")

        layout.addWidget(self.tab_widget)

        # 按钮栏
        button_layout = QHBoxLayout()

        test_btn = QPushButton("🧪 测试连接")
        test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(test_btn)

        reset_btn = QPushButton("🔄 重置配置")
        reset_btn.clicked.connect(self.reset_config)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        save_btn = QPushButton("💾 保存配置")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)

        apply_btn = QPushButton("⚡ 保存并重连")
        apply_btn.clicked.connect(self.save_and_reconnect)
        button_layout.addWidget(apply_btn)

        cancel_btn = QPushButton("❌ 取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def create_basic_config_tab(self):
        """创建基本配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 插件信息组
        info_group = QGroupBox("插件信息")
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("插件ID:"), 0, 0)
        self.plugin_id_label = QLabel("-")
        info_layout.addWidget(self.plugin_id_label, 0, 1)

        info_layout.addWidget(QLabel("版本:"), 1, 0)
        self.plugin_version_label = QLabel("-")
        info_layout.addWidget(self.plugin_version_label, 1, 1)

        info_layout.addWidget(QLabel("作者:"), 2, 0)
        self.plugin_author_label = QLabel("-")
        info_layout.addWidget(self.plugin_author_label, 2, 1)

        info_layout.addWidget(QLabel("描述:"), 3, 0)
        self.plugin_desc_label = QLabel("-")
        self.plugin_desc_label.setWordWrap(True)
        info_layout.addWidget(self.plugin_desc_label, 3, 1)

        layout.addWidget(info_group)

        # 连接配置组
        conn_group = QGroupBox("连接配置")
        conn_layout = QFormLayout(conn_group)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("例如: api.example.com")
        conn_layout.addRow("主机地址:", self.host_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(443)
        conn_layout.addRow("端口:", self.port_spin)

        self.use_ssl_check = QCheckBox("使用SSL/TLS")
        self.use_ssl_check.setChecked(True)
        conn_layout.addRow("安全连接:", self.use_ssl_check)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" 秒")
        conn_layout.addRow("连接超时:", self.timeout_spin)

        layout.addWidget(conn_group)

        # 认证配置组
        auth_group = QGroupBox("认证配置")
        auth_layout = QFormLayout(auth_group)

        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItems(["无认证", "API密钥", "用户名密码", "Token认证"])
        self.auth_type_combo.currentTextChanged.connect(self.update_auth_fields)
        auth_layout.addRow("认证类型:", self.auth_type_combo)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("输入API密钥")
        auth_layout.addRow("API密钥:", self.api_key_edit)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名")
        auth_layout.addRow("用户名:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("密码")
        auth_layout.addRow("密码:", self.password_edit)

        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.Password)
        self.token_edit.setPlaceholderText("访问令牌")
        auth_layout.addRow("访问令牌:", self.token_edit)

        layout.addWidget(auth_group)

        # 初始状态下隐藏认证字段
        self.update_auth_fields()

        layout.addStretch()
        return tab

    def create_routing_config_tab(self):
        """创建路由配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 权重配置组
        weight_group = QGroupBox("权重配置")
        weight_layout = QGridLayout(weight_group)

        weight_layout.addWidget(QLabel("路由权重:"), 0, 0)
        self.weight_slider = QSlider(Qt.Horizontal)
        self.weight_slider.setRange(1, 100)
        self.weight_slider.setValue(50)
        self.weight_slider.valueChanged.connect(self.update_weight_label)
        weight_layout.addWidget(self.weight_slider, 0, 1)

        self.weight_label = QLabel("50%")
        weight_layout.addWidget(self.weight_label, 0, 2)

        weight_layout.addWidget(QLabel("优先级:"), 1, 0)
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 10)
        self.priority_spin.setValue(5)
        weight_layout.addWidget(self.priority_spin, 1, 1)

        layout.addWidget(weight_group)

        # 支持资产类型配置
        asset_group = QGroupBox("支持的资产类型")
        asset_layout = QVBoxLayout(asset_group)

        # 使用表格显示资产类型和是否启用
        self.asset_table = QTableWidget()
        self.asset_table.setColumnCount(3)
        self.asset_table.setHorizontalHeaderLabels(["资产类型", "启用", "优先级"])

        # 设置表格列宽
        header = self.asset_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        asset_layout.addWidget(self.asset_table)

        layout.addWidget(asset_group)

        # 负载均衡配置
        lb_group = QGroupBox("负载均衡配置")
        lb_layout = QFormLayout(lb_group)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["优先级", "轮询", "加权轮询", "基于健康状态"])
        lb_layout.addRow("负载均衡策略:", self.strategy_combo)

        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(0, 10)
        self.max_retries_spin.setValue(3)
        lb_layout.addRow("最大重试次数:", self.max_retries_spin)

        layout.addWidget(lb_group)

        layout.addStretch()
        return tab

    def create_monitoring_tab(self):
        """创建健康监控标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 实时状态组
        status_group = QGroupBox("实时状态")
        status_layout = QGridLayout(status_group)

        status_layout.addWidget(QLabel("连接状态:"), 0, 0)
        self.connection_status_label = QLabel("🔴 未连接")
        status_layout.addWidget(self.connection_status_label, 0, 1)

        status_layout.addWidget(QLabel("最后检查:"), 1, 0)
        self.last_check_label = QLabel("-")
        status_layout.addWidget(self.last_check_label, 1, 1)

        status_layout.addWidget(QLabel("响应时间:"), 2, 0)
        self.response_time_label = QLabel("-")
        status_layout.addWidget(self.response_time_label, 2, 1)

        # 手动检查按钮
        manual_check_btn = QPushButton("🔍 立即检查")
        manual_check_btn.clicked.connect(self.check_health)
        status_layout.addWidget(manual_check_btn, 3, 1)

        layout.addWidget(status_group)

        # 性能指标组
        metrics_group = QGroupBox("性能指标")
        metrics_layout = QGridLayout(metrics_group)

        metrics_layout.addWidget(QLabel("总请求数:"), 0, 0)
        self.total_requests_label = QLabel("0")
        metrics_layout.addWidget(self.total_requests_label, 0, 1)

        metrics_layout.addWidget(QLabel("成功率:"), 1, 0)
        self.success_rate_label = QLabel("0%")
        metrics_layout.addWidget(self.success_rate_label, 1, 1)

        metrics_layout.addWidget(QLabel("平均响应时间:"), 2, 0)
        self.avg_response_time_label = QLabel("0ms")
        metrics_layout.addWidget(self.avg_response_time_label, 2, 1)

        metrics_layout.addWidget(QLabel("健康分数:"), 3, 0)
        self.health_score_label = QLabel("0.0")
        metrics_layout.addWidget(self.health_score_label, 3, 1)

        # 重置统计按钮
        reset_metrics_btn = QPushButton("🔄 重置统计")
        reset_metrics_btn.clicked.connect(self.reset_metrics)
        metrics_layout.addWidget(reset_metrics_btn, 4, 1)

        layout.addWidget(metrics_group)

        # 健康检查配置组
        health_config_group = QGroupBox("健康检查配置")
        health_config_layout = QFormLayout(health_config_group)

        self.health_interval_spin = QSpinBox()
        self.health_interval_spin.setRange(10, 300)
        self.health_interval_spin.setValue(30)
        self.health_interval_spin.setSuffix(" 秒")
        health_config_layout.addRow("检查间隔:", self.health_interval_spin)

        self.health_timeout_spin = QSpinBox()
        self.health_timeout_spin.setRange(1, 60)
        self.health_timeout_spin.setValue(10)
        self.health_timeout_spin.setSuffix(" 秒")
        health_config_layout.addRow("检查超时:", self.health_timeout_spin)

        self.enable_auto_check = QCheckBox("启用自动健康检查")
        self.enable_auto_check.setChecked(True)
        health_config_layout.addRow("自动检查:", self.enable_auto_check)

        layout.addWidget(health_config_group)

        layout.addStretch()
        return tab

    def create_advanced_config_tab(self):
        """创建高级设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 缓存配置组
        cache_group = QGroupBox("缓存配置")
        cache_layout = QFormLayout(cache_group)

        self.enable_cache_check = QCheckBox("启用数据缓存")
        self.enable_cache_check.setChecked(True)
        cache_layout.addRow("缓存启用:", self.enable_cache_check)

        self.cache_ttl_spin = QSpinBox()
        self.cache_ttl_spin.setRange(1, 3600)
        self.cache_ttl_spin.setValue(300)
        self.cache_ttl_spin.setSuffix(" 秒")
        cache_layout.addRow("缓存TTL:", self.cache_ttl_spin)

        self.max_cache_size_spin = QSpinBox()
        self.max_cache_size_spin.setRange(1, 1000)
        self.max_cache_size_spin.setValue(100)
        self.max_cache_size_spin.setSuffix(" MB")
        cache_layout.addRow("最大缓存大小:", self.max_cache_size_spin)

        layout.addWidget(cache_group)

        # 限流配置组
        limit_group = QGroupBox("请求限流配置")
        limit_layout = QFormLayout(limit_group)

        self.enable_rate_limit_check = QCheckBox("启用请求限流")
        self.enable_rate_limit_check.setChecked(False)
        limit_layout.addRow("限流启用:", self.enable_rate_limit_check)

        self.requests_per_second_spin = QSpinBox()
        self.requests_per_second_spin.setRange(1, 1000)
        self.requests_per_second_spin.setValue(10)
        limit_layout.addRow("每秒请求数:", self.requests_per_second_spin)

        self.burst_size_spin = QSpinBox()
        self.burst_size_spin.setRange(1, 100)
        self.burst_size_spin.setValue(20)
        limit_layout.addRow("突发请求数:", self.burst_size_spin)

        layout.addWidget(limit_group)

        # 自定义参数组
        custom_group = QGroupBox("自定义参数")
        custom_layout = QVBoxLayout(custom_group)

        custom_layout.addWidget(QLabel("JSON格式的自定义配置参数:"))
        self.custom_config_text = QTextEdit()
        self.custom_config_text.setPlaceholderText('{\n  "param1": "value1",\n  "param2": 123\n}')
        self.custom_config_text.setMaximumHeight(150)
        custom_layout.addWidget(self.custom_config_text)

        # 验证按钮
        validate_btn = QPushButton("✅ 验证JSON")
        validate_btn.clicked.connect(self.validate_custom_config)
        custom_layout.addWidget(validate_btn)

        layout.addWidget(custom_group)

        layout.addStretch()
        return tab

    def load_plugin_info(self):
        """加载插件信息"""
        try:

            unified_manager = get_unified_data_manager()
            if not unified_manager or not hasattr(unified_manager, 'data_source_router'):
                return

            router = unified_manager.data_source_router
            if self.source_id not in router.data_sources:
                return

            self.adapter = router.data_sources[self.source_id]
            self.plugin_info = self.adapter.get_plugin_info()

            # 更新插件信息显示
            self.plugin_id_label.setText(self.plugin_info.id)
            self.plugin_version_label.setText(self.plugin_info.version)
            self.plugin_author_label.setText(self.plugin_info.author)
            self.plugin_desc_label.setText(self.plugin_info.description)

            # 更新资产类型表格
            self.update_asset_table()

            # 更新性能指标
            self.update_metrics()

        except Exception as e:
            logger.error(f"加载插件信息失败: {str(e)}")
            QMessageBox.warning(self, "加载失败", f"加载插件信息失败:\n{str(e)}")

    def update_asset_table(self):
        """更新资产类型表格"""
        if not self.plugin_info:
            return

        supported_assets = self.plugin_info.supported_asset_types
        self.asset_table.setRowCount(len(supported_assets))

        for row, asset_type in enumerate(supported_assets):
            # 资产类型
            self.asset_table.setItem(row, 0, QTableWidgetItem(asset_type.value))

            # 启用复选框
            enable_check = QCheckBox()
            enable_check.setChecked(True)
            self.asset_table.setCellWidget(row, 1, enable_check)

            # 优先级
            priority_spin = QSpinBox()
            priority_spin.setRange(1, 10)
            priority_spin.setValue(5)
            self.asset_table.setCellWidget(row, 2, priority_spin)

    def load_config(self):
        """加载配置"""
        try:
            # 优先从数据库加载
            try:
                from db.models.plugin_models import get_data_source_config_manager  # type: ignore
                config_manager = get_data_source_config_manager()
                db_entry = config_manager.get_plugin_config(self.source_id)
            except Exception:
                db_entry = None

            # 默认配置
            default_config = {
                "connection": {
                    "host": "",
                    "port": 443,
                    "use_ssl": True,
                    "timeout": 30
                },
                "auth": {
                    "type": "无认证",
                    "api_key": "",
                    "username": "",
                    "password": "",
                    "token": ""
                },
                "routing": {
                    "weight": 50,
                    "priority": 5,
                    "strategy": "优先级",
                    "max_retries": 3
                },
                "monitoring": {
                    "health_interval": 30,
                    "health_timeout": 10,
                    "enable_auto_check": True
                },
                "advanced": {
                    "enable_cache": True,
                    "cache_ttl": 300,
                    "max_cache_size": 100,
                    "enable_rate_limit": False,
                    "requests_per_second": 10,
                    "burst_size": 20,
                    "custom_params": {}
                }
            }

            if db_entry and isinstance(db_entry, dict):
                # db_entry: {config_data, priority, weight, enabled}
                config_data = db_entry.get("config_data", {})
                if isinstance(config_data, dict):
                    # 合并：DB覆盖默认
                    merged = {**default_config, **config_data}
                    self.current_config = merged
                else:
                    self.current_config = default_config
            else:
                self.current_config = default_config

            self.apply_config_to_ui()

        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")

    def apply_config_to_ui(self):
        """将配置应用到UI控件"""
        try:
            config = self.current_config

            # 连接配置
            conn = config.get("connection", {})
            self.host_edit.setText(conn.get("host", ""))
            self.port_spin.setValue(conn.get("port", 443))
            self.use_ssl_check.setChecked(conn.get("use_ssl", True))
            self.timeout_spin.setValue(conn.get("timeout", 30))

            # 认证配置
            auth = config.get("auth", {})
            auth_type = auth.get("type", "无认证")
            index = self.auth_type_combo.findText(auth_type)
            if index >= 0:
                self.auth_type_combo.setCurrentIndex(index)

            self.api_key_edit.setText(auth.get("api_key", ""))
            self.username_edit.setText(auth.get("username", ""))
            self.password_edit.setText(auth.get("password", ""))
            self.token_edit.setText(auth.get("token", ""))

            # 路由配置
            routing = config.get("routing", {})
            self.weight_slider.setValue(routing.get("weight", 50))
            self.priority_spin.setValue(routing.get("priority", 5))

            strategy = routing.get("strategy", "优先级")
            index = self.strategy_combo.findText(strategy)
            if index >= 0:
                self.strategy_combo.setCurrentIndex(index)

            self.max_retries_spin.setValue(routing.get("max_retries", 3))

            # 监控配置
            monitoring = config.get("monitoring", {})
            self.health_interval_spin.setValue(monitoring.get("health_interval", 30))
            self.health_timeout_spin.setValue(monitoring.get("health_timeout", 10))
            self.enable_auto_check.setChecked(monitoring.get("enable_auto_check", True))

            # 高级配置
            advanced = config.get("advanced", {})
            self.enable_cache_check.setChecked(advanced.get("enable_cache", True))
            self.cache_ttl_spin.setValue(advanced.get("cache_ttl", 300))
            self.max_cache_size_spin.setValue(advanced.get("max_cache_size", 100))
            self.enable_rate_limit_check.setChecked(advanced.get("enable_rate_limit", False))
            self.requests_per_second_spin.setValue(advanced.get("requests_per_second", 10))
            self.burst_size_spin.setValue(advanced.get("burst_size", 20))

            custom_params = advanced.get("custom_params", {})
            if custom_params:
                self.custom_config_text.setPlainText(json.dumps(custom_params, indent=2, ensure_ascii=False))

            self.update_auth_fields()

        except Exception as e:
            logger.error(f"应用配置到UI失败: {str(e)}")

    def collect_config_from_ui(self):
        """从UI控件收集配置"""
        try:
            config = {
                "connection": {
                    "host": self.host_edit.text().strip(),
                    "port": self.port_spin.value(),
                    "use_ssl": self.use_ssl_check.isChecked(),
                    "timeout": self.timeout_spin.value()
                },
                "auth": {
                    "type": self.auth_type_combo.currentText(),
                    "api_key": self.api_key_edit.text().strip(),
                    "username": self.username_edit.text().strip(),
                    "password": self.password_edit.text().strip(),
                    "token": self.token_edit.text().strip()
                },
                "routing": {
                    "weight": self.weight_slider.value(),
                    "priority": self.priority_spin.value(),
                    "strategy": self.strategy_combo.currentText(),
                    "max_retries": self.max_retries_spin.value()
                },
                "monitoring": {
                    "health_interval": self.health_interval_spin.value(),
                    "health_timeout": self.health_timeout_spin.value(),
                    "enable_auto_check": self.enable_auto_check.isChecked()
                },
                "advanced": {
                    "enable_cache": self.enable_cache_check.isChecked(),
                    "cache_ttl": self.cache_ttl_spin.value(),
                    "max_cache_size": self.max_cache_size_spin.value(),
                    "enable_rate_limit": self.enable_rate_limit_check.isChecked(),
                    "requests_per_second": self.requests_per_second_spin.value(),
                    "burst_size": self.burst_size_spin.value(),
                    "custom_params": self.get_custom_params()
                }
            }

            return config

        except Exception as e:
            logger.error(f"从UI收集配置失败: {str(e)}")
            return {}

    def get_custom_params(self):
        """获取自定义参数"""
        try:
            text = self.custom_config_text.toPlainText().strip()
            if not text:
                return {}
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def update_auth_fields(self):
        """根据认证类型更新字段显示"""
        auth_type = self.auth_type_combo.currentText()

        # 隐藏所有认证字段
        self.api_key_edit.setVisible(False)
        self.username_edit.setVisible(False)
        self.password_edit.setVisible(False)
        self.token_edit.setVisible(False)

        # 根据类型显示相应字段
        if auth_type == "API密钥":
            self.api_key_edit.setVisible(True)
        elif auth_type == "用户名密码":
            self.username_edit.setVisible(True)
            self.password_edit.setVisible(True)
        elif auth_type == "Token认证":
            self.token_edit.setVisible(True)

    def update_weight_label(self):
        """更新权重标签"""
        value = self.weight_slider.value()
        self.weight_label.setText(f"{value}%")

    def check_health(self):
        """执行健康检查"""
        if self.health_worker and self.health_worker.running:
            return

        self.health_worker = HealthCheckWorker(self.source_id)
        self.health_worker.health_result.connect(self.on_health_result)
        self.health_worker.start()

    def on_health_result(self, is_healthy: bool, response_time: float, message: str):
        """健康检查结果处理"""
        try:
            if is_healthy:
                self.status_label.setText("🟢 已连接")
                self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
                self.connection_status_label.setText("🟢 正常")
            else:
                self.status_label.setText("🔴 连接失败")
                self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
                self.connection_status_label.setText(f"🔴 失败: {message}")

            self.last_check_label.setText(datetime.now().strftime("%H:%M:%S"))
            self.response_time_label.setText(f"{response_time:.1f}ms")

            # 更新性能指标
            self.update_metrics()

        except Exception as e:
            logger.error(f"处理健康检查结果失败: {str(e)}")

    def update_metrics(self):
        """更新性能指标"""
        try:

            unified_manager = get_unified_data_manager()
            if not unified_manager or not hasattr(unified_manager, 'data_source_router'):
                return

            router = unified_manager.data_source_router
            metrics = router.get_all_metrics()

            if self.source_id in metrics:
                metric = metrics[self.source_id]
                self.total_requests_label.setText(str(metric.total_requests))
                self.success_rate_label.setText(f"{metric.success_rate:.2%}")
                self.avg_response_time_label.setText(f"{metric.avg_response_time_ms:.1f}ms")
                self.health_score_label.setText(f"{metric.health_score:.2f}")

        except Exception as e:
            logger.error(f"更新性能指标失败: {str(e)}")

    def test_connection(self):
        """测试连接"""
        self.check_health()
        QMessageBox.information(self, "测试连接", "正在执行连接测试，请查看健康监控标签页的结果。")

    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置所有配置到默认值吗？\n这将丢失当前的所有配置。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.load_config()
            QMessageBox.information(self, "重置完成", "配置已重置到默认值。")

    def reset_metrics(self):
        """重置性能指标"""
        try:

            unified_manager = get_unified_data_manager()
            if not unified_manager or not hasattr(unified_manager, 'data_source_router'):
                QMessageBox.warning(self, "重置失败", "数据源路由器未启用")
                return

            router = unified_manager.data_source_router
            if self.source_id in router.source_metrics:
                # 重置指标
                router.source_metrics[self.source_id] = router.source_metrics[self.source_id].__class__()
                self.update_metrics()
                QMessageBox.information(self, "重置成功", "性能指标已重置。")

        except Exception as e:
            QMessageBox.critical(self, "重置失败", f"重置性能指标失败:\n{str(e)}")

    def validate_custom_config(self):
        """验证自定义配置JSON"""
        try:
            text = self.custom_config_text.toPlainText().strip()
            if not text:
                QMessageBox.information(self, "验证通过", "空配置，验证通过。")
                return

            json.loads(text)
            QMessageBox.information(self, "验证通过", "JSON格式正确。")

        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON错误", f"JSON格式错误:\n{str(e)}")

    def save_config(self):
        """保存配置"""
        try:
            # 验证配置
            config = self.collect_config_from_ui()
            if not config:
                QMessageBox.warning(self, "保存失败", "配置收集失败，请检查输入。")
                return

            # 验证必填字段
            if not config["connection"]["host"]:
                QMessageBox.warning(self, "验证失败", "主机地址不能为空。")
                return

            # 保存配置
            self.current_config = config

            # 写入数据库
            try:
                config_manager = get_data_source_config_manager()

                # 保持与数据源路由兼容的基础字段
                routing = config.get("routing", {})
                priority = int(routing.get("priority", 5))
                weight = float(routing.get("weight", 50)) / 50.0  # 将百分比粗略映射到[0,2]
                enabled = True

                # 存储一份完整 JSON 作为 config_data
                config_manager.save_plugin_config(
                    plugin_id=self.source_id,
                    config_data=config,
                    priority=priority,
                    weight=weight,
                    enabled=enabled,
                )
            except Exception as db_err:
                logger.error(f"保存配置到数据库失败: {db_err}")

            # 发送配置变更信号
            self.config_changed.emit(self.source_id, config)

            QMessageBox.information(self, "保存成功", "配置已保存。")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存配置失败:\n{str(e)}")

    def save_and_reconnect(self):
        """保存配置并重连适配器（不关闭对话框）"""
        try:
            config = self.collect_config_from_ui()
            if not config:
                QMessageBox.warning(self, "保存失败", "配置收集失败，请检查输入。")
                return

            if not config["connection"]["host"]:
                QMessageBox.warning(self, "验证失败", "主机地址不能为空。")
                return

            # 写入数据库
            try:
                config_manager = get_data_source_config_manager()
                routing = config.get("routing", {})
                priority = int(routing.get("priority", 5))
                weight = float(routing.get("weight", 50)) / 50.0
                enabled = True
                config_manager.save_plugin_config(
                    plugin_id=self.source_id,
                    config_data=config,
                    priority=priority,
                    weight=weight,
                    enabled=enabled,
                )
            except Exception as db_err:
                logger.error(f"保存配置到数据库失败: {db_err}")
                QMessageBox.warning(self, "部分成功", "配置保存失败，但将尝试重连。")

            # 重连适配器
            try:
                unified_manager = get_unified_data_manager()
                if not unified_manager or not hasattr(unified_manager, 'data_source_router'):
                    QMessageBox.warning(self, "重连失败", "数据源路由器未启用")
                    return

                router = unified_manager.data_source_router
                if self.source_id not in router.data_sources:
                    QMessageBox.warning(self, "重连失败", f"未找到数据源适配器: {self.source_id}")
                    return

                adapter = router.data_sources[self.source_id]
                try:
                    adapter.disconnect()
                except Exception:
                    pass

                success = adapter.connect()
                if success:
                    QMessageBox.information(self, "已应用", "配置已保存并重连成功。")
                    # 刷新状态与指标
                    self.status_label.setText("🟢 已连接")
                    self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
                    self.update_metrics()
                else:
                    QMessageBox.warning(self, "重连失败", "适配器重连失败，请检查日志。")

            except Exception as e:
                logger.error(f"保存并重连失败: {e}")
                QMessageBox.critical(self, "重连失败", f"发生异常：\n{str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "操作失败", f"保存并重连失败：\n{str(e)}")

    def closeEvent(self, event):
        """关闭事件处理"""
        if self.health_timer:
            self.health_timer.stop()

        if self.health_worker and self.health_worker.running:
            self.health_worker.stop()
            self.health_worker.wait(1000)

        event.accept()


def show_data_source_plugin_config(source_id: str, parent=None):
    """显示数据源插件配置对话框"""
    dialog = DataSourcePluginConfigDialog(source_id, parent)
    return dialog.exec_()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 测试对话框
    dialog = DataSourcePluginConfigDialog("test_plugin")
    dialog.show()

    sys.exit(app.exec_())
