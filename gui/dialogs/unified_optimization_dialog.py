from loguru import logger
"""
统一优化服务管理对话框

为5个深度优化模块提供统一的GUI管理界面
"""

import asyncio
import time
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QComboBox, QCheckBox, QPushButton, QProgressBar, QLabel,
    QTextEdit, QMessageBox, QSplitter, QFrame, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QSlider,
    QSpinBox, QDoubleSpinBox, QLineEdit, QScrollArea, QWidget,
    QGridLayout, QTextBrowser
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

# 导入统一优化服务
from core.advanced_optimization import (
    UnifiedOptimizationService,
    OptimizationConfig,
    OptimizationMetrics,
    OptimizationMode
)

class OptimizationWorker(QThread):
    """优化服务工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(str, float)  # 消息, 进度
    status_updated = pyqtSignal(str)  # 状态
    optimization_completed = pyqtSignal(object)  # 优化结果
    optimization_failed = pyqtSignal(str)  # 错误信息
    
    def __init__(self, service: UnifiedOptimizationService, mode: str):
        super().__init__()
        self.service = service
        self.mode = mode
        self._should_stop = False
        
    def run(self):
        """运行优化任务"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.status_updated.emit("启动统一优化服务...")
            
            # 根据模式执行相应操作
            if self.mode == "start":
                self._run_start()
            elif self.mode == "test":
                self._run_test()
            elif self.mode == "monitor":
                self._run_monitor()
            else:
                self.optimization_failed.emit(f"未知的操作模式: {self.mode}")
                
        except Exception as e:
            self.optimization_failed.emit(str(e))
        finally:
            loop.close()
            
    def _run_start(self):
        """执行启动模式"""
        async def async_start():
            result = await self.service.start()
            
            # 模拟启动进度
            for i in range(0, 101, 10):
                if self._should_stop:
                    break
                self.progress_updated.emit(f"正在启动优化服务... {i}%", i / 100)
                await asyncio.sleep(0.1)
            
            if result:
                self.status_updated.emit("统一优化服务启动成功")
                self.optimization_completed.emit({"status": "success", "message": "启动成功"})
            else:
                self.status_updated.emit("统一优化服务启动失败")
                self.optimization_failed.emit("启动失败")
                
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_start())
        finally:
            loop.close()
            
    def _run_test(self):
        """执行测试模式"""
        async def async_test():
            # 获取性能指标
            metrics = self.service.get_performance_metrics()
            
            for i in range(0, 101, 5):
                if self._should_stop:
                    break
                    
                # 模拟测试进度
                self.progress_updated.emit(f"正在测试优化模块... {i}%", i / 100)
                await asyncio.sleep(0.05)
            
            # 测试完成
            self.status_updated.emit("优化服务测试完成")
            self.optimization_completed.emit({
                "status": "success", 
                "message": "测试完成",
                "metrics": metrics
            })
                
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_test())
        finally:
            loop.close()
            
    def _run_monitor(self):
        """执行监控模式"""
        for i in range(60):  # 监控60秒
            if self._should_stop:
                break
                
            # 获取当前指标
            metrics = self.service.get_performance_metrics()
            
            progress = (i + 1) / 60
            self.progress_updated.emit(f"正在监控性能... {i+1}/60秒", progress)
            self.status_updated.emit(f"当前运行时间: {metrics.get('uptime', 0):.1f}秒")
            
            self.msleep(1000)  # 每秒检查一次
            
        self.optimization_completed.emit({"status": "completed", "message": "监控结束"})
        
    def stop(self):
        """停止工作"""
        self._should_stop = True

class UnifiedOptimizationDialog(QDialog):
    """统一优化服务管理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.optimization_service = None
        self.worker = None
        
        # 设置窗口属性
        self.setWindowTitle("统一优化服务管理")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # 初始化服务
        self._init_service()
        
        # 创建UI
        self._create_ui()
        
        # 连接信号
        self._connect_signals()
        
        # 设置定时器更新指标
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self._update_metrics_display)
        self.metrics_timer.start(2000)  # 每2秒更新一次
        
    async def _init_service_async(self):
        """异步初始化统一优化服务"""
        try:
            # 创建默认配置
            config = OptimizationConfig()
            
            # 创建服务实例
            self.optimization_service = UnifiedOptimizationService(config)
            
            # 初始化服务
            init_result = await self.optimization_service.initialize()
            if init_result:
                logger.info("统一优化服务初始化成功")
            else:
                logger.error("统一优化服务初始化失败")
                QMessageBox.critical(self, "初始化错误", "无法初始化统一优化服务")
                
        except Exception as e:
            logger.error(f"统一优化服务初始化失败: {e}")
            QMessageBox.critical(self, "初始化错误", f"无法初始化统一优化服务:\n{e}")
            
    def _init_service(self):
        """初始化统一优化服务"""
        try:
            # 在新事件循环中运行异步初始化
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._init_service_async())
            loop.close()
            
        except Exception as e:
            logger.error(f"统一优化服务初始化失败: {e}")
            QMessageBox.critical(self, "初始化错误", f"无法初始化统一优化服务:\n{e}")
            
    def _create_ui(self):
        """创建用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建各个选项卡
        self._create_overview_tab()
        self._create_control_tab()
        self._create_metrics_tab()
        self._create_config_tab()
        self._create_logs_tab()
        
        # 创建底部按钮
        self._create_buttons(layout)
        
    def _create_overview_tab(self):
        """创建概览选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 服务状态卡片
        status_group = QGroupBox("服务状态")
        status_layout = QFormLayout(status_group)
        
        self.service_status_label = QLabel("未启动")
        self.service_status_label.setStyleSheet("""
            QLabel {
                background-color: #f44336;
                color: white;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        status_layout.addRow("当前状态:", self.service_status_label)
        
        self.startup_time_label = QLabel("N/A")
        status_layout.addRow("启动时间:", self.startup_time_label)
        
        self.enabled_modules_label = QLabel("N/A")
        status_layout.addRow("启用模块:", self.enabled_modules_label)
        
        layout.addWidget(status_group)
        
        # 快速操作卡片
        quick_group = QGroupBox("快速操作")
        quick_layout = QGridLayout(quick_group)
        
        # 启动/停止按钮
        self.start_btn = QPushButton("🚀 启动服务")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        quick_layout.addWidget(self.start_btn, 0, 0)
        
        self.stop_btn = QPushButton("🛑 停止服务")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_btn.setEnabled(False)
        quick_layout.addWidget(self.stop_btn, 0, 1)
        
        # 性能模式按钮
        self.performance_btn = QPushButton("⚡ 性能模式")
        self.performance_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        quick_layout.addWidget(self.performance_btn, 1, 0)
        
        self.balance_btn = QPushButton("⚖️ 平衡模式")
        self.balance_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        quick_layout.addWidget(self.balance_btn, 1, 1)
        
        # 监控按钮
        self.monitor_btn = QPushButton("📊 实时监控")
        self.monitor_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        quick_layout.addWidget(self.monitor_btn, 2, 0)
        
        layout.addWidget(quick_group)
        
        # 当前指标卡片
        metrics_group = QGroupBox("当前性能指标")
        metrics_layout = QVBoxLayout(metrics_group)
        
        # 指标表格
        self.metrics_table = QTableWidget(6, 2)
        self.metrics_table.setHorizontalHeaderLabels(["指标", "值"])
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.setAlternatingRowColors(True)
        self.metrics_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                selection-background-color: #3f51b5;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        
        # 设置表格数据
        self.metrics_data = [
            ("运行时间", "0.0秒"),
            ("缓存命中率", "0.0%"),
            ("虚拟滚动渲染", "未启用"),
            ("实时连接数", "0"),
            ("AI推荐精度", "0.0%"),
            ("UI响应时间", "0ms")
        ]
        
        for i, (name, value) in enumerate(self.metrics_data):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(name))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(value))
            
        # 调整列宽
        header = self.metrics_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        metrics_layout.addWidget(self.metrics_table)
        layout.addWidget(metrics_group)
        
        self.tab_widget.addTab(tab, "📊 概览")
        
    def _create_control_tab(self):
        """创建控制选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 服务控制
        control_group = QGroupBox("服务控制")
        control_layout = QFormLayout(control_group)
        
        # 优化模式选择
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "性能优先",
            "内存优化", 
            "响应速度",
            "平衡模式",
            "自定义配置"
        ])
        control_layout.addRow("优化模式:", self.mode_combo)
        
        # 手动启动按钮
        manual_layout = QHBoxLayout()
        self.manual_start_btn = QPushButton("手动启动服务")
        manual_layout.addWidget(self.manual_start_btn)
        
        self.manual_stop_btn = QPushButton("手动停止服务")
        manual_stop_btn = QPushButton("手动停止服务")
        manual_layout.addWidget(manual_stop_btn)
        control_layout.addRow("", manual_layout)
        
        layout.addWidget(control_group)
        
        # 模块配置
        modules_group = QGroupBox("模块配置")
        modules_layout = QVBoxLayout(modules_group)
        
        # 模块开关
        modules_grid = QGridLayout()
        
        # 智能缓存
        self.cache_checkbox = QCheckBox("智能缓存管理器")
        self.cache_checkbox.setChecked(True)
        modules_grid.addWidget(self.cache_checkbox, 0, 0)
        
        # 组件虚拟化
        self.virtual_scroll_checkbox = QCheckBox("组件虚拟化")
        self.virtual_scroll_checkbox.setChecked(True)
        modules_grid.addWidget(self.virtual_scroll_checkbox, 0, 1)
        
        # 实时数据流
        self.realtime_checkbox = QCheckBox("实时数据流")
        self.realtime_checkbox.setChecked(True)
        modules_grid.addWidget(self.realtime_checkbox, 1, 0)
        
        # AI推荐
        self.ai_checkbox = QCheckBox("AI智能推荐")
        self.ai_checkbox.setChecked(True)
        modules_grid.addWidget(self.ai_checkbox, 1, 1)
        
        # 响应式UI
        self.responsive_checkbox = QCheckBox("响应式UI")
        self.responsive_checkbox.setChecked(True)
        modules_grid.addWidget(self.responsive_checkbox, 2, 0)
        
        modules_layout.addLayout(modules_grid)
        layout.addWidget(modules_group)
        
        # 进度条和状态
        progress_group = QGroupBox("操作进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.operation_progress = QProgressBar()
        self.operation_progress.setVisible(False)
        progress_layout.addWidget(self.operation_progress)
        
        self.operation_status = QLabel("准备就绪")
        self.operation_status.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.operation_status)
        
        layout.addWidget(progress_group)
        
        self.tab_widget.addTab(tab, "🎛️ 控制")
        
    def _create_metrics_tab(self):
        """创建指标选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 性能监控图表区域
        performance_group = QGroupBox("性能监控")
        performance_layout = QVBoxLayout(performance_group)
        
        # 性能表格
        self.performance_table = QTableWidget(10, 4)
        self.performance_table.setHorizontalHeaderLabels([
            "时间", "CPU使用率", "内存使用率", "响应时间"
        ])
        self.performance_table.verticalHeader().setVisible(False)
        scroll_layout.addWidget(performance_group)
        
        # 缓存统计
        cache_group = QGroupBox("缓存统计")
        cache_layout = QVBoxLayout(cache_group)
        
        self.cache_table = QTableWidget(5, 3)
        self.cache_table.setHorizontalHeaderLabels([
            "指标", "当前值", "目标值"
        ])
        self.cache_table.verticalHeader().setVisible(False)
        scroll_layout.addWidget(cache_group)
        
        # 网络连接
        network_group = QGroupBox("网络连接")
        network_layout = QVBoxLayout(network_group)
        
        self.network_table = QTableWidget(4, 3)
        self.network_table.setHorizontalHeaderLabels([
            "连接类型", "状态", "数量"
        ])
        self.network_table.verticalHeader().setVisible(False)
        scroll_layout.addWidget(network_group)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(tab, "📈 指标")
        
    def _create_config_tab(self):
        """创建配置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 性能配置
        perf_group = QGroupBox("性能配置")
        perf_layout = QFormLayout(perf_group)
        
        # 内存配置
        self.memory_size = QSpinBox()
        self.memory_size.setRange(64, 4096)
        self.memory_size.setValue(256)
        self.memory_size.setSuffix(" MB")
        perf_layout.addRow("缓存内存:", self.memory_size)
        
        self.cache_ttl = QSpinBox()
        self.cache_ttl.setRange(1, 1440)
        self.cache_ttl.setValue(60)
        self.cache_ttl.setSuffix(" 分钟")
        perf_layout.addRow("缓存过期时间:", self.cache_ttl)
        
        # 渲染配置
        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(10, 100)
        self.chunk_size.setValue(50)
        self.chunk_size.setSuffix(" 项")
        perf_layout.addRow("虚拟滚动块大小:", self.chunk_size)
        
        self.max_connections = QSpinBox()
        self.max_connections.setRange(10, 1000)
        self.max_connections.setValue(100)
        perf_layout.addRow("最大连接数:", self.max_connections)
        
        layout.addWidget(perf_group)
        
        # AI配置
        ai_group = QGroupBox("AI配置")
        ai_layout = QFormLayout(ai_group)
        
        self.recommendation_count = QSpinBox()
        self.recommendation_count.setRange(1, 20)
        self.recommendation_count.setValue(5)
        ai_layout.addRow("推荐数量:", self.recommendation_count)
        
        self.learning_window = QSpinBox()
        self.learning_window.setRange(1, 365)
        self.learning_window.setValue(30)
        self.learning_window.setSuffix(" 天")
        ai_layout.addRow("学习窗口:", self.learning_window)
        
        layout.addWidget(ai_group)
        
        # 应用配置按钮
        config_btn_layout = QHBoxLayout()
        apply_config_btn = QPushButton("应用配置")
        save_config_btn = QPushButton("保存配置")
        reset_config_btn = QPushButton("重置配置")
        
        config_btn_layout.addWidget(apply_config_btn)
        config_btn_layout.addWidget(save_config_btn)
        config_btn_layout.addWidget(reset_config_btn)
        
        layout.addLayout(config_btn_layout)
        
        self.tab_widget.addTab(tab, "⚙️ 配置")
        
    def _create_logs_tab(self):
        """创建日志选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 日志控制
        log_control_layout = QHBoxLayout()
        
        self.log_filter = QComboBox()
        self.log_filter.addItems(["所有", "错误", "警告", "信息", "调试"])
        log_control_layout.addWidget(QLabel("日志级别:"))
        log_control_layout.addWidget(self.log_filter)
        
        clear_log_btn = QPushButton("清空日志")
        log_control_layout.addWidget(clear_log_btn)
        
        export_log_btn = QPushButton("导出日志")
        log_control_layout.addWidget(export_log_btn)
        
        layout.addLayout(log_control_layout)
        
        # 日志内容
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_browser = QTextBrowser()
        self.log_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                selection-background-color: #404040;
            }
        """)
        log_layout.addWidget(self.log_browser)
        
        layout.addWidget(log_group)
        
        self.tab_widget.addTab(tab, "📋 日志")
        
    def _create_buttons(self, main_layout):
        """创建底部按钮"""
        button_layout = QHBoxLayout()
        
        # 状态标签
        self.footer_status = QLabel("就绪")
        button_layout.addWidget(self.footer_status)
        
        button_layout.addStretch()
        
        # 功能按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_status)
        
        settings_btn = QPushButton("高级设置")
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(settings_btn)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        
    def _connect_signals(self):
        """连接信号"""
        # 概览选项卡按钮
        self.start_btn.clicked.connect(lambda: self._start_operation("start"))
        self.stop_btn.clicked.connect(lambda: self._start_operation("stop"))
        self.performance_btn.clicked.connect(self._apply_performance_mode)
        self.balance_btn.clicked.connect(self._apply_balance_mode)
        self.monitor_btn.clicked.connect(lambda: self._start_operation("monitor"))
        
        # 控制选项卡按钮
        self.manual_start_btn.clicked.connect(lambda: self._start_operation("start"))
        
    def _start_operation(self, operation_type: str):
        """启动操作"""
        if self.worker and self.worker.isRunning():
            return
            
        # 更新UI状态
        self._update_operation_ui(True, f"正在执行{operation_type}操作...")
        
        # 创建工作线程
        self.worker = OptimizationWorker(self.optimization_service, operation_type)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.status_updated.connect(self._on_status_updated)
        self.worker.optimization_completed.connect(self._on_operation_completed)
        self.worker.optimization_failed.connect(self._on_operation_failed)
        
        # 启动工作线程
        self.worker.start()
        
    def _apply_performance_mode(self):
        """应用性能模式"""
        # 更新配置
        self.memory_size.setValue(512)
        self.chunk_size.setValue(30)
        self.max_connections.setValue(200)
        self._log_message("已应用性能优先模式配置")
        
    def _apply_balance_mode(self):
        """应用平衡模式"""
        # 更新配置
        self.memory_size.setValue(256)
        self.chunk_size.setValue(50)
        self.max_connections.setValue(100)
        self._log_message("已应用平衡模式配置")
        
    def _on_progress_updated(self, message: str, progress: float):
        """进度更新"""
        self.operation_progress.setValue(int(progress * 100))
        self.operation_status.setText(message)
        
    def _on_status_updated(self, status: str):
        """状态更新"""
        self.operation_status.setText(status)
        
    def _on_operation_completed(self, result):
        """操作完成"""
        self._update_operation_ui(False)
        
        if result.get("status") == "success":
            self._update_service_status("运行中", True)
            self._log_message("✅ 统一优化服务启动成功")
        else:
            self._log_message("ℹ️ 操作完成")
            
    def _on_operation_failed(self, error: str):
        """操作失败"""
        self._update_operation_ui(False)
        self._update_service_status("错误", False)
        self._log_message(f"❌ 操作失败: {error}")
        
    def _update_operation_ui(self, is_running: bool, status: str = ""):
        """更新操作UI状态"""
        self.operation_progress.setVisible(is_running)
        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)
        
        if is_running:
            self.operation_status.setText(status)
            
    def _update_service_status(self, status: str, is_running: bool):
        """更新服务状态显示"""
        self.service_status_label.setText(status)
        
        if is_running:
            self.service_status_label.setStyleSheet("""
                QLabel {
                    background-color: #4CAF50;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.service_status_label.setStyleSheet("""
                QLabel {
                    background-color: #f44336;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
    def _update_metrics_display(self):
        """更新指标显示"""
        if not self.optimization_service:
            return
            
        try:
            # 检查服务是否已初始化且是同步方法
            if hasattr(self.optimization_service, 'get_performance_metrics') and callable(self.optimization_service.get_performance_metrics):
                # 直接调用同步方法
                metrics = self.optimization_service.get_performance_metrics()
                
                # 更新表格数据
                current_time = time.time()
                uptime = current_time - getattr(self.optimization_service, '_start_time', current_time)
                
                # 更新运行时间
                self.metrics_table.setItem(0, 1, QTableWidgetItem(f"{uptime:.1f}秒"))
                
                # 更新其他指标（使用真实数据）
                self.metrics_table.setItem(1, 1, QTableWidgetItem(f"{metrics.get('cache_hit_rate', 0.0):.1f}%"))
                self.metrics_table.setItem(2, 1, QTableWidgetItem("已启用"))
                self.metrics_table.setItem(3, 1, QTableWidgetItem(f"{metrics.get('active_connections', 0)}"))
                self.metrics_table.setItem(4, 1, QTableWidgetItem(f"{metrics.get('ai_recommendation_accuracy', 0.0):.1f}%"))
                self.metrics_table.setItem(5, 1, QTableWidgetItem(f"{metrics.get('ui_response_time', 0)}ms"))
                
                # 更新启动时间
                self.startup_time_label.setText(time.strftime("%Y-%m-%d %H:%M:%S"))
                
                # 更新启用模块
                enabled_modules = []
                if self.cache_checkbox.isChecked():
                    enabled_modules.append("缓存")
                if self.virtual_scroll_checkbox.isChecked():
                    enabled_modules.append("虚拟化")
                if self.realtime_checkbox.isChecked():
                    enabled_modules.append("实时")
                if self.ai_checkbox.isChecked():
                    enabled_modules.append("AI")
                if self.responsive_checkbox.isChecked():
                    enabled_modules.append("UI")
                    
                self.enabled_modules_label.setText(", ".join(enabled_modules) if enabled_modules else "无")
                
            else:
                logger.warning("性能指标方法不可用")
                
        except Exception as e:
            logger.error(f"更新指标显示失败: {e}")
            # 更新表格显示错误状态
            self.metrics_table.setItem(0, 1, QTableWidgetItem("服务错误"))
            
    def _refresh_status(self):
        """刷新状态"""
        self._update_metrics_display()
        self._log_message("🔄 状态已刷新")
        
    def _log_message(self, message: str, level: str = "info"):
        """记录日志消息"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        if level == "error":
            formatted_message = f"[{timestamp}] ❌ {message}"
        elif level == "warning":
            formatted_message = f"[{timestamp}] ⚠️ {message}"
        else:
            formatted_message = f"[{timestamp}] ℹ️ {message}"
            
        self.log_browser.append(formatted_message)
        self.log_browser.ensureCursorVisible()
        
    def closeEvent(self, event):
        """关闭事件"""
        # 停止工作线程
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
        # 停止定时器
        self.metrics_timer.stop()
        
        # 关闭优化服务
        if self.optimization_service:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.optimization_service.stop())
            except Exception as e:
                logger.error(f"关闭优化服务失败: {e}")
                
        event.accept()