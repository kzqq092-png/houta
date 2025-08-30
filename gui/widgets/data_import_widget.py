#!/usr/bin/env python3
"""
数据导入UI组件

提供专业的数据导入界面，对标Bloomberg Terminal和Wind万得
支持多数据源配置、任务管理、实时监控等功能
"""

import sys
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QSplitter, QScrollArea,
    QTableWidget, QTableWidgetItem, QTextEdit, QProgressBar,
    QGroupBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QApplication, QHeaderView, QComboBox, QLineEdit,
    QDateEdit, QSpinBox, QCheckBox, QListWidget, QListWidgetItem,
    QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDate, QEvent
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

# 导入数据导入相关模块
try:
    from core.importdata.import_config_manager import (
        ImportConfigManager, ImportTaskConfig, ImportMode, DataFrequency
    )
    from core.importdata.import_execution_engine import DataImportExecutionEngine
    IMPORT_ENGINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"导入引擎模块不可用: {e}")
    IMPORT_ENGINE_AVAILABLE = False
    ImportConfigManager = None
    ImportTaskConfig = None
    ImportMode = None
    DataFrequency = None
    DataImportExecutionEngine = None

logger = logging.getLogger(__name__)


# 自定义事件类
class ExecutionEngineReadyEvent(QEvent):
    """执行引擎准备就绪事件"""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, execution_engine):
        super().__init__(self.EVENT_TYPE)
        self.execution_engine = execution_engine


class ExecutionEngineFailedEvent(QEvent):
    """执行引擎初始化失败事件"""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, error_message):
        super().__init__(self.EVENT_TYPE)
        self.error_message = error_message


class DataImportWidget(QWidget):
    """
    数据导入主界面组件

    提供完整的数据导入功能界面
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dataImportWidget")

        # 初始化数据导入组件
        self._init_import_components()

        self._init_ui()
        self._setup_styles()
        self._connect_signals()

        logger.info("数据导入界面初始化完成")

    def _populate_data_sources(self):
        """动态获取并填充数据源列表"""
        try:
            # 尝试从服务容器获取统一数据管理器
            try:
                from core.containers import get_service_container
                from core.services.unified_data_manager import UnifiedDataManager

                service_container = get_service_container()
                if service_container.is_registered(UnifiedDataManager):
                    data_manager = service_container.resolve(UnifiedDataManager)

                    # 获取可用数据源名称
                    available_sources = data_manager.get_available_data_source_names()
                    if available_sources:
                        self.data_source_combo.addItems(available_sources)
                        logger.info(f"✅ 动态加载数据源: {available_sources}")
                        return
                    else:
                        logger.warning("⚠️ 未找到可用数据源，使用默认列表")
                else:
                    logger.warning("⚠️ 服务容器中未找到数据管理器")
            except Exception as e:
                logger.warning(f"⚠️ 获取数据管理器失败: {e}")

            # 降级到默认数据源列表
            default_sources = ["HIkyuu", "东方财富", "新浪财经", "同花顺", "Wind万得"]
            self.data_source_combo.addItems(default_sources)
            logger.info(f"📋 使用默认数据源列表: {default_sources}")

        except Exception as e:
            logger.error(f"❌ 填充数据源列表失败: {e}")
            # 最后的降级方案
            self.data_source_combo.addItems(["HIkyuu", "东方财富"])

    def _init_execution_engine_async(self):
        """异步初始化执行引擎"""
        def init_engine():
            try:
                # 尝试从服务容器获取已初始化的数据管理器
                try:
                    from core.containers import get_service_container
                    from core.services.unified_data_manager import UnifiedDataManager

                    service_container = get_service_container()
                    if service_container.is_registered(UnifiedDataManager):
                        data_manager = service_container.resolve(UnifiedDataManager)
                        logger.info("从服务容器获取数据管理器成功")
                    else:
                        data_manager = None
                        logger.warning("服务容器中未找到数据管理器")
                except Exception as e:
                    logger.warning(f"从服务容器获取数据管理器失败: {e}")
                    data_manager = None

                # 创建执行引擎
                from core.importdata.import_execution_engine import DataImportExecutionEngine
                self.execution_engine = DataImportExecutionEngine(
                    config_manager=self.config_manager,
                    data_manager=data_manager
                )

                # 连接信号（在主线程中执行）
                QApplication.instance().postEvent(self, ExecutionEngineReadyEvent(self.execution_engine))

                logger.info("执行引擎异步初始化成功")

            except Exception as e:
                logger.error(f"执行引擎异步初始化失败: {e}")
                # 发送失败事件
                QApplication.instance().postEvent(self, ExecutionEngineFailedEvent(str(e)))

        # 在后台线程中初始化
        import threading
        init_thread = threading.Thread(target=init_engine, daemon=True)
        init_thread.start()

    def event(self, event):
        """处理自定义事件"""
        if event.type() == ExecutionEngineReadyEvent.EVENT_TYPE:
            # 执行引擎准备就绪
            self.execution_engine = event.execution_engine

            # 连接信号
            self.execution_engine.task_started.connect(self._on_task_started)
            self.execution_engine.task_progress.connect(self._on_task_progress)
            self.execution_engine.task_completed.connect(self._on_task_completed)
            self.execution_engine.task_failed.connect(self._on_task_failed)

            logger.info("执行引擎信号连接完成")
            return True

        elif event.type() == ExecutionEngineFailedEvent.EVENT_TYPE:
            # 执行引擎初始化失败
            logger.error(f"执行引擎初始化失败: {event.error_message}")
            return True

        return super().event(event)

    def _init_import_components(self):
        """初始化数据导入相关组件"""
        if IMPORT_ENGINE_AVAILABLE:
            # 初始化配置管理器
            self.config_manager = ImportConfigManager()

            # 延迟初始化任务执行引擎，避免在UI线程中阻塞
            self.execution_engine = None
            self._init_execution_engine_async()

            logger.info("数据导入组件初始化成功")
        else:
            self.config_manager = None
            self.execution_engine = None
            logger.error("数据导入组件不可用，请检查系统依赖")

        # 初始化任务状态跟踪
        self.running_tasks = set()  # 跟踪正在运行的任务

        # 初始化异步数据导入管理器
        try:
            from core.services.async_data_import_manager import get_async_data_import_manager
            self.async_import_manager = get_async_data_import_manager()

            # 连接异步导入信号
            self.async_import_manager.import_started.connect(self._on_async_import_started)
            self.async_import_manager.progress_updated.connect(self._on_async_progress_updated)
            self.async_import_manager.import_completed.connect(self._on_async_import_completed)
            self.async_import_manager.import_failed.connect(self._on_async_import_failed)
            self.async_import_manager.data_chunk_imported.connect(self._on_async_data_chunk_imported)

            logger.info("异步数据导入管理器初始化成功")
        except Exception as e:
            logger.warning(f"异步数据导入管理器初始化失败: {e}")
            self.async_import_manager = None

    def _init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 标题栏
        self._create_title_bar(main_layout)

        # 主内容区域
        self._create_main_content(main_layout)

    def _create_title_bar(self, parent_layout):
        """创建标题栏"""
        title_layout = QHBoxLayout()

        # 标题
        title_label = QLabel("📥 数据导入管理")
        title_label.setObjectName("importTitle")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 新建任务按钮
        new_task_button = QPushButton("➕ 新建任务")
        new_task_button.setFixedSize(100, 30)
        new_task_button.clicked.connect(self._create_new_task)
        title_layout.addWidget(new_task_button)

        # 导入配置按钮
        import_config_button = QPushButton("📂 导入配置")
        import_config_button.setFixedSize(100, 30)
        import_config_button.clicked.connect(self._import_config)
        title_layout.addWidget(import_config_button)

        # 导出配置按钮
        export_config_button = QPushButton("💾 导出配置")
        export_config_button.setFixedSize(100, 30)
        export_config_button.clicked.connect(self._export_config)
        title_layout.addWidget(export_config_button)

        parent_layout.addLayout(title_layout)

    def _create_main_content(self, parent_layout):
        """创建主内容区域"""
        # 创建标签页
        self.tab_widget = QTabWidget()

        # 任务管理标签页
        self.task_tab = self._create_task_tab()
        self.tab_widget.addTab(self.task_tab, "📋 任务管理")

        # 数据源配置标签页
        self.source_tab = self._create_source_tab()
        self.tab_widget.addTab(self.source_tab, "🔗 数据源配置")

        # 监控面板标签页
        self.monitor_tab = self._create_monitor_tab()
        self.tab_widget.addTab(self.monitor_tab, "📊 监控面板")

        parent_layout.addWidget(self.tab_widget)

    def _create_task_tab(self):
        """创建任务管理标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # 左侧：任务列表
        left_panel = self._create_task_list_panel()
        layout.addWidget(left_panel, 1)

        # 右侧：任务详情
        right_panel = self._create_task_detail_panel()
        layout.addWidget(right_panel, 2)

        return tab

    def _create_task_list_panel(self):
        """创建任务列表面板"""
        panel = QFrame()
        panel.setObjectName("taskListPanel")
        layout = QVBoxLayout(panel)

        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入任务名称...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # 任务列表
        self.task_list = QListWidget()
        layout.addWidget(self.task_list)

        # 操作按钮
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("▶️ 启动")
        self.stop_button = QPushButton("⏹️ 停止")
        self.delete_button = QPushButton("🗑️ 删除")

        # 初始状态禁用按钮
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        # 连接按钮信号
        self.start_button.clicked.connect(self._start_task)
        self.stop_button.clicked.connect(self._stop_task)
        self.delete_button.clicked.connect(self._delete_task)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.delete_button)
        layout.addLayout(button_layout)

        # 加载任务列表
        self._populate_task_list()

        return panel

    def _create_task_detail_panel(self):
        """创建任务详情面板"""
        panel = QFrame()
        panel.setObjectName("taskDetailPanel")
        layout = QVBoxLayout(panel)

        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QGridLayout(basic_group)

        # 任务名称
        basic_layout.addWidget(QLabel("任务名称:"), 0, 0)
        self.task_name_input = QLineEdit()
        basic_layout.addWidget(self.task_name_input, 0, 1)

        # 数据源
        basic_layout.addWidget(QLabel("数据源:"), 1, 0)
        self.data_source_combo = QComboBox()
        self._populate_data_sources()  # 动态获取数据源
        basic_layout.addWidget(self.data_source_combo, 1, 1)

        # 资产类型
        basic_layout.addWidget(QLabel("资产类型:"), 2, 0)
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems(["股票", "债券", "基金", "期货", "期权"])
        basic_layout.addWidget(self.asset_type_combo, 2, 1)

        # 数据类型
        basic_layout.addWidget(QLabel("数据类型:"), 3, 0)
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["K线数据", "实时行情", "基本面数据", "财务数据", "新闻数据"])
        basic_layout.addWidget(self.data_type_combo, 3, 1)

        layout.addWidget(basic_group)

        # 导入配置组
        config_group = QGroupBox("导入配置")
        config_layout = QGridLayout(config_group)

        # 导入模式
        config_layout.addWidget(QLabel("导入模式:"), 0, 0)
        self.import_mode_combo = QComboBox()
        self.import_mode_combo.addItems(["实时导入", "批量导入", "定时导入", "手动导入"])
        config_layout.addWidget(self.import_mode_combo, 0, 1)

        # 数据频率
        config_layout.addWidget(QLabel("数据频率:"), 1, 0)
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["日线", "周线", "月线", "分钟线", "5分钟线", "15分钟线", "30分钟线", "60分钟线"])
        config_layout.addWidget(self.frequency_combo, 1, 1)

        # 日期范围
        config_layout.addWidget(QLabel("开始日期:"), 2, 0)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addYears(-1))
        self.start_date_edit.setCalendarPopup(True)
        config_layout.addWidget(self.start_date_edit, 2, 1)

        config_layout.addWidget(QLabel("结束日期:"), 3, 0)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        config_layout.addWidget(self.end_date_edit, 3, 1)

        # 性能配置
        config_layout.addWidget(QLabel("批处理大小:"), 4, 0)
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(100, 10000)
        self.batch_size_spin.setValue(1000)
        config_layout.addWidget(self.batch_size_spin, 4, 1)

        config_layout.addWidget(QLabel("最大工作线程:"), 5, 0)
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 16)
        self.max_workers_spin.setValue(4)
        config_layout.addWidget(self.max_workers_spin, 5, 1)

        layout.addWidget(config_group)

        # 股票代码选择组
        symbols_group = QGroupBox("股票代码")
        symbols_layout = QVBoxLayout(symbols_group)

        # 股票代码输入
        input_layout = QHBoxLayout()
        self.symbols_input = QLineEdit()
        self.symbols_input.setPlaceholderText("输入股票代码，如: 000001")
        add_symbol_button = QPushButton("添加")
        add_symbol_button.clicked.connect(self._add_symbols)
        input_layout.addWidget(self.symbols_input)
        input_layout.addWidget(add_symbol_button)
        symbols_layout.addLayout(input_layout)

        # 快捷添加按钮
        quick_layout = QGridLayout()

        # 第一行：A股相关
        add_all_a_button = QPushButton("添加全部A股")
        add_all_a_button.clicked.connect(self._add_all_a_shares)
        add_main_board_button = QPushButton("添加主板股票")
        add_main_board_button.clicked.connect(lambda: self._add_stocks_by_type("main_board"))
        add_gem_button = QPushButton("添加创业板")
        add_gem_button.clicked.connect(lambda: self._add_stocks_by_type("gem"))

        quick_layout.addWidget(add_all_a_button, 0, 0)
        quick_layout.addWidget(add_main_board_button, 0, 1)
        quick_layout.addWidget(add_gem_button, 0, 2)

        # 第二行：其他市场
        add_hk_button = QPushButton("添加港股通")
        add_hk_button.clicked.connect(lambda: self._add_stocks_by_type("hk_connect"))
        add_etf_button = QPushButton("添加ETF基金")
        add_etf_button.clicked.connect(lambda: self._add_stocks_by_type("etf"))
        add_bond_button = QPushButton("添加债券")
        add_bond_button.clicked.connect(lambda: self._add_stocks_by_type("bond"))

        quick_layout.addWidget(add_hk_button, 1, 0)
        quick_layout.addWidget(add_etf_button, 1, 1)
        quick_layout.addWidget(add_bond_button, 1, 2)

        # 第三行：操作按钮
        clear_button = QPushButton("清空列表")
        clear_button.clicked.connect(self._clear_symbols)
        import_from_file_button = QPushButton("从文件导入")
        import_from_file_button.clicked.connect(self._import_symbols_from_file)

        quick_layout.addWidget(clear_button, 2, 0)
        quick_layout.addWidget(import_from_file_button, 2, 1)

        symbols_layout.addLayout(quick_layout)

        # 股票代码列表
        self.symbols_list = QListWidget()
        symbols_layout.addWidget(self.symbols_list)

        layout.addWidget(symbols_group)

        # 保存按钮
        save_button = QPushButton("💾 保存任务")
        save_button.clicked.connect(self._save_task)
        layout.addWidget(save_button)

        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        return panel

    def _create_source_tab(self):
        """创建数据源配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 数据源列表
        sources_group = QGroupBox("数据源配置")
        sources_layout = QVBoxLayout(sources_group)

        self.sources_table = QTableWidget()
        self.sources_table.setColumnCount(4)
        self.sources_table.setHorizontalHeaderLabels(["名称", "类型", "状态", "操作"])
        sources_layout.addWidget(self.sources_table)

        # 填充数据源配置表
        self._populate_data_source_table()

        # 操作按钮
        button_layout = QHBoxLayout()

        add_source_button = QPushButton("➕ 添加数据源")
        add_source_button.clicked.connect(self._add_data_source)
        button_layout.addWidget(add_source_button)

        refresh_button = QPushButton("🔄 刷新")
        refresh_button.clicked.connect(self._refresh_data_sources)
        button_layout.addWidget(refresh_button)

        button_layout.addStretch()
        sources_layout.addLayout(button_layout)

        layout.addWidget(sources_group)

        return tab

    def _create_monitor_tab(self):
        """创建监控面板标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 实时状态
        status_group = QGroupBox("实时状态")
        status_layout = QGridLayout(status_group)

        # 运行中任务数
        status_layout.addWidget(QLabel("运行中任务:"), 0, 0)
        self.running_tasks_label = QLabel("0")
        status_layout.addWidget(self.running_tasks_label, 0, 1)

        # 总任务数
        status_layout.addWidget(QLabel("总任务数:"), 0, 2)
        self.total_tasks_label = QLabel("0")
        status_layout.addWidget(self.total_tasks_label, 0, 3)

        # 成功率
        status_layout.addWidget(QLabel("成功率:"), 1, 0)
        self.success_rate_label = QLabel("0%")
        status_layout.addWidget(self.success_rate_label, 1, 1)

        # 数据量
        status_layout.addWidget(QLabel("导入数据量:"), 1, 2)
        self.data_volume_label = QLabel("0")
        status_layout.addWidget(self.data_volume_label, 1, 3)

        layout.addWidget(status_group)

        # 日志显示
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        return tab

    def _setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            /* 主界面样式 */
            QWidget#dataImportWidget {
                background-color: #1a1d29;
                color: #ffffff;
            }
            
            /* 标题样式 */
            QLabel#importTitle {
                color: #ff6b35;
                margin-bottom: 10px;
            }
            
            /* 面板样式 */
            QFrame#taskListPanel, QFrame#taskDetailPanel {
                background-color: #2d3142;
                border: 1px solid #3d4152;
                border-radius: 8px;
                padding: 10px;
            }
            
            /* 标签页样式 */
            QTabWidget::pane {
                border: 1px solid #3d4152;
                background-color: #2d3142;
                border-radius: 8px;
            }
            
            QTabBar::tab {
                background-color: #252837;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            QTabBar::tab:selected {
                background-color: #4dabf7;
            }
            
            QTabBar::tab:hover {
                background-color: #343a4f;
            }
            
            /* 组件样式 */
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3d4152;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
                background-color: #252837;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4dabf7;
            }
            
            QPushButton {
                background-color: #4dabf7;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 6px 12px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #339af0;
            }
            
            QPushButton:pressed {
                background-color: #1971c2;
            }
            
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
            
            QLineEdit, QComboBox, QSpinBox, QDateEdit {
                background-color: #1a1d29;
                border: 1px solid #3d4152;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
            }
            
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {
                border-color: #4dabf7;
            }
            
            QListWidget, QTableWidget {
                background-color: #1a1d29;
                alternate-background-color: #252837;
                gridline-color: #3d4152;
                color: #ffffff;
                border: 1px solid #3d4152;
                border-radius: 4px;
            }
            
            QHeaderView::section {
                background-color: #252837;
                color: #ffffff;
                border: 1px solid #3d4152;
                padding: 6px;
                font-weight: bold;
            }
            
            QProgressBar {
                border: 1px solid #3d4152;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                background-color: #2d3142;
            }
            
            QProgressBar::chunk {
                background-color: #4dabf7;
                border-radius: 3px;
            }
        """)

    def _connect_signals(self):
        """连接信号"""
        self.task_list.itemSelectionChanged.connect(self._on_task_selected)
        self.search_input.textChanged.connect(self._filter_tasks)

    def _populate_task_list(self):
        """填充任务列表"""
        self.task_list.clear()

        if self.config_manager:
            tasks = self.config_manager.get_all_import_tasks()
            for task_id, task_config in tasks.items():
                item = QListWidgetItem(f"{task_config.name} ({task_id})")
                item.setData(Qt.UserRole, task_id)
                self.task_list.addItem(item)
        else:
            # 模拟模式：添加示例任务
            for i in range(3):
                item = QListWidgetItem(f"示例任务 {i+1}")
                item.setData(Qt.UserRole, f"demo_task_{i+1}")
                self.task_list.addItem(item)

    def _on_task_selected(self):
        """任务选择事件"""
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = current_item.data(Qt.UserRole)

            # 根据任务状态设置按钮状态
            is_running = task_id in self.running_tasks
            self.start_button.setEnabled(not is_running)
            self.stop_button.setEnabled(is_running)
            self.delete_button.setEnabled(not is_running)

            # 加载任务详情
            self._load_task_details(task_id)

            logger.info(f"选择任务: {task_id}, 运行状态: {is_running}")
        else:
            # 没有选择任务时禁用所有按钮
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def _load_task_details(self, task_id: str):
        """加载任务详情"""
        if self.config_manager:
            task_config = self.config_manager.get_import_task(task_id)
            if task_config:
                self.task_name_input.setText(task_config.name)
                self.data_source_combo.setCurrentText(task_config.data_source)
                self.asset_type_combo.setCurrentText(task_config.asset_type)
                self.data_type_combo.setCurrentText(task_config.data_type)

                # 设置导入模式
                mode_map = {
                    ImportMode.REAL_TIME: "实时导入",
                    ImportMode.BATCH: "批量导入",
                    ImportMode.SCHEDULED: "定时导入",
                    ImportMode.MANUAL: "手动导入"
                }
                self.import_mode_combo.setCurrentText(mode_map.get(task_config.mode, "手动导入"))

                # 设置频率
                freq_map = {
                    DataFrequency.DAILY: "日线",
                    DataFrequency.WEEKLY: "周线",
                    DataFrequency.MONTHLY: "月线",
                    DataFrequency.MINUTE_1: "分钟线",
                    DataFrequency.MINUTE_5: "5分钟线",
                    DataFrequency.MINUTE_15: "15分钟线",
                    DataFrequency.MINUTE_30: "30分钟线",
                    DataFrequency.HOUR_1: "60分钟线"
                }
                self.frequency_combo.setCurrentText(freq_map.get(task_config.frequency, "日线"))

                # 设置日期
                if task_config.start_date:
                    start_date = QDate.fromString(task_config.start_date, "yyyy-MM-dd")
                    self.start_date_edit.setDate(start_date)

                if task_config.end_date:
                    end_date = QDate.fromString(task_config.end_date, "yyyy-MM-dd")
                    self.end_date_edit.setDate(end_date)

                # 设置性能参数
                self.batch_size_spin.setValue(task_config.batch_size)
                self.max_workers_spin.setValue(task_config.max_workers)

                # 设置股票代码
                self.symbols_list.clear()
                for symbol in task_config.symbols:
                    self.symbols_list.addItem(symbol)

                logger.info(f"加载任务详情: {task_id}")
        else:
            # 模拟模式
            self.task_name_input.setText(f"任务 {task_id}")
            self.data_source_combo.setCurrentText("HIkyuu")
            self.asset_type_combo.setCurrentText("股票")
            self.data_type_combo.setCurrentText("K线数据")

    def _filter_tasks(self):
        """过滤任务列表"""
        search_text = self.search_input.text().lower()

        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            task_name = item.text().lower()
            item.setHidden(search_text not in task_name)

    def _create_new_task(self):
        """创建新任务"""
        # 清空表单
        self.task_name_input.clear()
        self.symbols_list.clear()

        # 切换到任务管理标签页
        self.tab_widget.setCurrentIndex(0)

    def _start_task(self):
        """启动任务（优先使用异步导入）"""
        current_item = self.task_list.currentItem()
        if not current_item:
            return

        task_id = current_item.data(Qt.UserRole)

        # 优先使用异步导入管理器
        if self.async_import_manager:
            try:
                # 获取任务配置
                task_config = self._get_task_config(task_id)
                if task_config:
                    # 启动异步导入
                    actual_task_id = self.async_import_manager.start_import(task_config)

                    # 更新任务状态
                    self.running_tasks.add(task_id)
                    self.start_button.setEnabled(False)
                    self.stop_button.setEnabled(True)

                    self._log_message(f"异步导入任务 {actual_task_id} 启动成功")
                    logger.info(f"任务 {task_id} 已添加到运行列表")
                    return
                else:
                    self._log_message(f"获取任务配置失败: {task_id}")
            except Exception as e:
                self._log_message(f"异步导入启动失败: {e}")
                logger.error(f"异步导入启动异常: {e}")
                # 降级到同步模式

        # 降级到同步执行引擎
        if self.execution_engine:
            success = self.execution_engine.start_task(task_id)
            if success:
                # 更新任务状态
                self.running_tasks.add(task_id)
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self._log_message(f"任务 {task_id} 启动成功（同步模式）")
                logger.info(f"同步任务 {task_id} 已添加到运行列表")
            else:
                QMessageBox.warning(self, "错误", f"任务 {task_id} 启动失败")
                logger.error(f"同步任务 {task_id} 启动失败")
        else:
            # 执行引擎尚未初始化完成
            self._log_message(f"⏳ 数据导入引擎正在初始化中，请稍后重试: {task_id}", "warning")
            QMessageBox.information(self, "提示", "数据导入引擎正在后台初始化中，请稍后重试")

    def _get_task_config(self, task_id: str) -> dict:
        """获取任务配置"""
        try:
            logger.info(f"🔍 开始获取任务配置: {task_id}")

            if self.config_manager:
                logger.info(f"📋 使用配置管理器获取任务配置")
                # 从配置管理器获取任务配置
                task_config = self.config_manager.get_import_task(task_id)
                if task_config:
                    config_dict = {
                        'task_id': task_id,
                        'mode': getattr(task_config, 'mode', 'incremental'),
                        'data_sources': getattr(task_config, 'symbols', ['default']),
                        'date_range': {
                            'start_date': getattr(task_config, 'start_date', None),
                            'end_date': getattr(task_config, 'end_date', None)
                        },
                        'frequency': getattr(task_config, 'frequency', 'daily')
                    }
                    logger.info(f"✅ 从配置管理器获取到任务配置: {config_dict}")
                    return config_dict
                else:
                    logger.warning(f"⚠️ 配置管理器中未找到任务: {task_id}")

            # 如果没有配置管理器，创建默认配置
            default_config = {
                'task_id': task_id,
                'mode': 'incremental',
                'data_sources': ['default'],
                'date_range': {},
                'frequency': 'daily'
            }
            logger.info(f"📋 使用默认配置: {default_config}")
            return default_config

        except Exception as e:
            logger.error(f"❌ 获取任务配置失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def _stop_task(self):
        """停止任务（支持异步导入）"""
        current_item = self.task_list.currentItem()
        if not current_item:
            return

        task_id = current_item.data(Qt.UserRole)

        # 优先尝试停止异步导入任务
        if self.async_import_manager:
            active_imports = self.async_import_manager.get_active_imports()
            if task_id in active_imports:
                success = self.async_import_manager.stop_import(task_id)
                if success:
                    self.start_button.setEnabled(True)
                    self.stop_button.setEnabled(False)
                    self._log_message(f"异步导入任务 {task_id} 停止成功")
                    return
                else:
                    self._log_message(f"异步导入任务 {task_id} 停止失败", "error")

        # 降级到同步执行引擎
        if self.execution_engine:
            success = self.execution_engine.stop_task(task_id)
            if success:
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                self._log_message(f"任务 {task_id} 停止成功")
            else:
                QMessageBox.warning(self, "错误", f"任务 {task_id} 停止失败")
        else:
            # 模拟模式
            self._log_message(f"模拟停止任务: {task_id}")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)

    def _delete_task(self):
        """删除任务"""
        current_item = self.task_list.currentItem()
        if not current_item:
            return

        task_id = current_item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除任务 {task_id} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.config_manager:
                success = self.config_manager.remove_import_task(task_id)
                if success:
                    self._populate_task_list()
                    self._log_message(f"任务 {task_id} 删除成功")
                else:
                    QMessageBox.warning(self, "错误", f"任务 {task_id} 删除失败")
            else:
                # 模拟模式
                self.task_list.takeItem(self.task_list.currentRow())
                self._log_message(f"模拟删除任务: {task_id}")

    def _add_symbols(self):
        """添加股票代码"""
        symbol = self.symbols_input.text().strip()
        if symbol:
            # 检查是否已存在
            for i in range(self.symbols_list.count()):
                if self.symbols_list.item(i).text() == symbol:
                    return

            self.symbols_list.addItem(symbol)
            self.symbols_input.clear()

    def _add_all_a_shares(self):
        """添加全部A股（异步操作避免UI卡死）"""
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setFormat("正在获取股票列表...")

        # 禁用按钮防止重复点击
        sender = self.sender()
        if sender:
            sender.setEnabled(False)
            sender.setText("获取中...")

        # 创建异步工作线程
        from PyQt5.QtCore import QThread, pyqtSignal

        class StockListWorker(QThread):
            stocks_loaded = pyqtSignal(list)
            error_occurred = pyqtSignal(str)
            progress_updated = pyqtSignal(str)  # 新增进度信号

            def run(self):
                import time
                start_time = time.time()

                try:
                    self.progress_updated.emit("正在连接数据源...")

                    # 设置总体超时时间（30秒）
                    timeout_seconds = 30

                    # 使用真实数据提供器获取股票列表
                    from core.real_data_provider import RealDataProvider

                    self.progress_updated.emit("正在获取股票列表...")

                    # 使用线程超时机制（Windows兼容）
                    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

                    def create_real_provider():
                        """在单独线程中创建RealDataProvider"""
                        return RealDataProvider()

                    def get_stock_list(provider):
                        """在单独线程中获取股票列表"""
                        return provider.get_real_stock_list(market='all', limit=500)

                    # 使用线程池执行，设置超时
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        # 步骤1：创建RealDataProvider（5秒超时）
                        try:
                            future = executor.submit(create_real_provider)
                            real_provider = future.result(timeout=5.0)
                            self.progress_updated.emit("数据源连接成功...")
                        except FutureTimeoutError:
                            self.progress_updated.emit("初始化超时，使用离线列表...")
                            raise TimeoutError("RealDataProvider初始化超时")
                        except Exception as e:
                            self.progress_updated.emit("初始化失败，使用离线列表...")
                            raise Exception(f"RealDataProvider初始化失败: {e}")

                        # 检查总体超时
                        if time.time() - start_time > timeout_seconds:
                            raise TimeoutError("获取股票列表超时")

                        # 步骤2：获取股票列表（10秒超时）
                        try:
                            future = executor.submit(get_stock_list, real_provider)
                            stock_codes = future.result(timeout=10.0)
                            self.progress_updated.emit("股票列表获取成功...")
                        except FutureTimeoutError:
                            self.progress_updated.emit("获取超时，使用离线列表...")
                            raise TimeoutError("获取股票列表超时")
                        except Exception as e:
                            self.progress_updated.emit("获取失败，使用离线列表...")
                            raise Exception(f"获取股票列表失败: {e}")

                    if not stock_codes:
                        self.progress_updated.emit("尝试备用数据源...")

                        # 检查是否超时
                        if time.time() - start_time > timeout_seconds:
                            raise TimeoutError("获取股票列表超时")

                        # 如果真实数据提供器失败，尝试使用统一数据管理器
                        from core.services.unified_data_manager import UnifiedDataManager
                        data_manager = UnifiedDataManager()
                        stock_df = data_manager.get_stock_list(market='all')

                        if not stock_df.empty and 'code' in stock_df.columns:
                            stock_codes = stock_df['code'].tolist()[:500]  # 限制500只
                        else:
                            self.progress_updated.emit("使用离线股票列表...")
                            logger.warning("无法获取真实股票列表，使用默认股票池")
                            stock_codes = self._get_default_stock_list()

                    # 检查获取到的股票数量
                    if len(stock_codes) == 0:
                        self.progress_updated.emit("使用离线股票列表...")
                        stock_codes = self._get_default_stock_list()

                    elapsed_time = time.time() - start_time
                    logger.info(f"股票列表获取完成，耗时: {elapsed_time:.2f}秒，获取到: {len(stock_codes)}只股票")

                    self.stocks_loaded.emit(stock_codes)

                except TimeoutError as e:
                    logger.error(f"获取股票列表超时: {e}")
                    self.progress_updated.emit("获取超时，使用离线列表...")
                    # 超时时使用默认列表
                    default_stocks = self._get_default_stock_list()
                    self.stocks_loaded.emit(default_stocks)

                except Exception as e:
                    logger.error(f"获取股票列表失败: {e}")
                    error_msg = str(e)

                    # 提供更友好的错误信息
                    if "Connection" in error_msg or "timeout" in error_msg.lower():
                        error_msg = "网络连接失败，已使用离线股票列表"
                        # 网络错误时也提供默认列表
                        default_stocks = self._get_default_stock_list()
                        self.stocks_loaded.emit(default_stocks)
                    elif "akshare" in error_msg.lower():
                        error_msg = "AKShare数据源暂时不可用，已使用离线股票列表"
                        default_stocks = self._get_default_stock_list()
                        self.stocks_loaded.emit(default_stocks)
                    else:
                        self.error_occurred.emit(error_msg)

            def _get_default_stock_list(self):
                """获取默认股票列表"""
                return [
                    # 主板蓝筹股
                    "000001", "000002", "000858", "002415", "000725", "000776", "002594", "300750",
                    "600000", "600036", "600519", "600887", "600276", "600585", "601318", "601398",
                    "601939", "603259", "002304", "002714", "300059", "300124",
                    # 科创板
                    "688981", "688036", "688111", "688169",
                    # 创业板
                    "300015", "300142", "300347", "300408", "300498"
                ]

        # 创建并启动工作线程
        self.stock_worker = StockListWorker()
        self.stock_worker.stocks_loaded.connect(self._on_stocks_loaded)
        self.stock_worker.error_occurred.connect(self._on_stock_load_error)
        self.stock_worker.progress_updated.connect(self._on_stock_load_progress)  # 连接进度信号
        self.stock_worker.start()

    def _on_stocks_loaded(self, stock_codes):
        """股票列表加载完成"""
        try:
            # 添加股票代码到列表
            added_count = 0
            for symbol in stock_codes:
                # 确保代码格式正确
                if '.' not in symbol:
                    # 根据代码判断市场
                    if symbol.startswith('6'):
                        symbol = f"{symbol}.SH"
                    elif symbol.startswith(('0', '3')):
                        symbol = f"{symbol}.SZ"

                # 检查是否已存在
                existing_symbols = [self.symbols_list.item(i).text()
                                    for i in range(self.symbols_list.count())]
                if symbol not in existing_symbols:
                    self.symbols_list.addItem(symbol)
                    added_count += 1

            logger.info(f"成功添加 {added_count} 只A股代码")

            # 显示成功消息
            QMessageBox.information(self, "成功", f"成功添加 {added_count} 只A股代码到导入列表")

        except Exception as e:
            logger.error(f"添加股票代码失败: {e}")
            QMessageBox.warning(self, "错误", f"添加股票代码失败: {str(e)}")

        finally:
            # 恢复UI状态
            self._restore_add_button_state()

    def _on_stock_load_error(self, error_msg):
        """股票列表加载失败"""
        logger.error(f"获取股票列表失败: {error_msg}")
        QMessageBox.warning(self, "错误", f"获取股票列表失败: {error_msg}")
        self._restore_add_button_state()

    def _on_stock_load_progress(self, progress_msg):
        """股票列表加载进度更新"""
        self.progress_bar.setFormat(progress_msg)
        logger.info(f"股票列表加载进度: {progress_msg}")

    def _restore_add_button_state(self):
        """恢复添加按钮状态"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)

        # 恢复按钮状态
        for child in self.findChildren(QPushButton):
            if child.text() == "获取中...":
                child.setEnabled(True)
                child.setText("添加全部A股")

    def _add_stocks_by_type(self, stock_type):
        """根据类型添加股票"""
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat(f"正在获取{self._get_type_name(stock_type)}...")

        # 禁用按钮
        sender = self.sender()
        if sender:
            sender.setEnabled(False)
            original_text = sender.text()
            sender.setText("获取中...")

        # 创建异步工作线程
        from PyQt5.QtCore import QThread, pyqtSignal

        class TypedStockWorker(QThread):
            stocks_loaded = pyqtSignal(list, str)
            error_occurred = pyqtSignal(str, str)

            def __init__(self, stock_type):
                super().__init__()
                self.stock_type = stock_type

            def run(self):
                try:
                    stock_codes = self._get_stocks_by_type(self.stock_type)
                    self.stocks_loaded.emit(stock_codes, self.stock_type)
                except Exception as e:
                    self.error_occurred.emit(str(e), self.stock_type)

            def _get_stocks_by_type(self, stock_type):
                """根据类型获取股票列表"""
                if stock_type == "main_board":
                    # 主板股票 (600开头的上海主板 + 000开头的深圳主板)
                    return [
                        "600000.SH", "600036.SH", "600519.SH", "600887.SH", "600276.SH",
                        "600585.SH", "600690.SH", "600703.SH", "600809.SH", "600900.SH",
                        "000001.SZ", "000002.SZ", "000858.SZ", "000725.SZ", "000776.SZ",
                        "000895.SZ", "000963.SZ", "000983.SZ", "001979.SZ", "002415.SZ"
                    ]
                elif stock_type == "gem":
                    # 创业板股票 (300开头)
                    return [
                        "300059.SZ", "300124.SZ", "300750.SZ", "300014.SZ", "300015.SZ",
                        "300033.SZ", "300142.SZ", "300144.SZ", "300347.SZ", "300408.SZ",
                        "300413.SZ", "300450.SZ", "300498.SZ", "300601.SZ", "300628.SZ"
                    ]
                elif stock_type == "hk_connect":
                    # 港股通股票
                    return [
                        "00700.HK", "00941.HK", "01299.HK", "02318.HK", "03690.HK",
                        "09988.HK", "09618.HK", "01810.HK", "02020.HK", "01024.HK",
                        "00388.HK", "01398.HK", "03988.HK", "02628.HK", "01288.HK"
                    ]
                elif stock_type == "etf":
                    # ETF基金
                    return [
                        "510050.SH", "510300.SH", "510500.SH", "159919.SZ", "159915.SZ",
                        "512100.SH", "512880.SH", "515050.SH", "516160.SH", "588000.SH",
                        "159941.SZ", "159928.SZ", "159949.SZ", "512690.SH", "515790.SH"
                    ]
                elif stock_type == "bond":
                    # 债券
                    return [
                        "019547.SH", "019612.SH", "019640.SH", "136073.SH", "136089.SH",
                        "127045.SZ", "127046.SZ", "127047.SZ", "123107.SZ", "123108.SZ",
                        "110059.SH", "110061.SH", "113050.SH", "113616.SH", "113617.SH"
                    ]
                else:
                    return []

        # 创建并启动工作线程
        self.typed_stock_worker = TypedStockWorker(stock_type)
        self.typed_stock_worker.stocks_loaded.connect(self._on_typed_stocks_loaded)
        self.typed_stock_worker.error_occurred.connect(self._on_typed_stock_error)
        self.typed_stock_worker.start()

    def _get_type_name(self, stock_type):
        """获取股票类型的中文名称"""
        type_names = {
            "main_board": "主板股票",
            "gem": "创业板股票",
            "hk_connect": "港股通股票",
            "etf": "ETF基金",
            "bond": "债券"
        }
        return type_names.get(stock_type, "股票")

    def _on_typed_stocks_loaded(self, stock_codes, stock_type):
        """特定类型股票加载完成"""
        try:
            added_count = 0
            existing_symbols = [self.symbols_list.item(i).text()
                                for i in range(self.symbols_list.count())]

            for symbol in stock_codes:
                if symbol not in existing_symbols:
                    self.symbols_list.addItem(symbol)
                    added_count += 1

            type_name = self._get_type_name(stock_type)
            logger.info(f"成功添加 {added_count} 只{type_name}")
            QMessageBox.information(self, "成功", f"成功添加 {added_count} 只{type_name}到导入列表")

        except Exception as e:
            logger.error(f"添加{stock_type}失败: {e}")
            QMessageBox.warning(self, "错误", f"添加股票失败: {str(e)}")

        finally:
            self._restore_typed_button_state(stock_type)

    def _on_typed_stock_error(self, error_msg, stock_type):
        """特定类型股票加载失败"""
        type_name = self._get_type_name(stock_type)
        logger.error(f"获取{type_name}失败: {error_msg}")
        QMessageBox.warning(self, "错误", f"获取{type_name}失败: {error_msg}")
        self._restore_typed_button_state(stock_type)

    def _restore_typed_button_state(self, stock_type):
        """恢复特定类型按钮状态"""
        self.progress_bar.setVisible(False)

        # 恢复按钮状态
        type_button_texts = {
            "main_board": "添加主板股票",
            "gem": "添加创业板",
            "hk_connect": "添加港股通",
            "etf": "添加ETF基金",
            "bond": "添加债券"
        }

        target_text = type_button_texts.get(stock_type, "")
        for child in self.findChildren(QPushButton):
            if child.text() == "获取中..." and hasattr(child, 'original_text'):
                child.setEnabled(True)
                child.setText(child.original_text)
            elif child.text() == "获取中...":
                # 尝试根据类型恢复
                child.setEnabled(True)
                child.setText(target_text)

    def _import_symbols_from_file(self):
        """从文件导入股票代码"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择股票代码文件", "",
            "文本文件 (*.txt);;CSV文件 (*.csv);;所有文件 (*)"
        )

        if file_path:
            try:
                symbols = []
                if file_path.endswith('.csv'):
                    import pandas as pd
                    df = pd.read_csv(file_path)
                    # 假设第一列是股票代码
                    if len(df.columns) > 0:
                        symbols = df.iloc[:, 0].astype(str).tolist()
                else:
                    # 文本文件，每行一个代码
                    with open(file_path, 'r', encoding='utf-8') as f:
                        symbols = [line.strip() for line in f if line.strip()]

                # 添加到列表
                added_count = 0
                existing_symbols = [self.symbols_list.item(i).text()
                                    for i in range(self.symbols_list.count())]

                for symbol in symbols:
                    symbol = symbol.strip()
                    if symbol and symbol not in existing_symbols:
                        self.symbols_list.addItem(symbol)
                        added_count += 1

                QMessageBox.information(self, "成功", f"从文件导入了 {added_count} 个股票代码")
                logger.info(f"从文件 {file_path} 导入了 {added_count} 个股票代码")

            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入文件失败: {str(e)}")
                logger.error(f"导入文件失败: {e}")

    def _clear_symbols(self):
        """清空股票代码"""
        self.symbols_list.clear()

    def _save_task(self):
        """保存任务"""
        task_name = self.task_name_input.text().strip()
        if not task_name:
            QMessageBox.warning(self, "错误", "请输入任务名称")
            return

        if self.config_manager and IMPORT_ENGINE_AVAILABLE:
            try:
                # 创建任务配置
                import uuid
                task_id = str(uuid.uuid4())

                # 映射UI选择到枚举值
                mode_map = {
                    "实时导入": ImportMode.REAL_TIME,
                    "批量导入": ImportMode.BATCH,
                    "定时导入": ImportMode.SCHEDULED,
                    "手动导入": ImportMode.MANUAL
                }

                freq_map = {
                    "日线": DataFrequency.DAILY,
                    "周线": DataFrequency.WEEKLY,
                    "月线": DataFrequency.MONTHLY,
                    "分钟线": DataFrequency.MINUTE_1,
                    "5分钟线": DataFrequency.MINUTE_5,
                    "15分钟线": DataFrequency.MINUTE_15,
                    "30分钟线": DataFrequency.MINUTE_30,
                    "60分钟线": DataFrequency.HOUR_1
                }

                # 收集股票代码
                symbols = [self.symbols_list.item(i).text()
                           for i in range(self.symbols_list.count())]

                task_config = ImportTaskConfig(
                    task_id=task_id,
                    name=task_name,
                    data_source=self.data_source_combo.currentText(),
                    asset_type=self.asset_type_combo.currentText(),
                    data_type=self.data_type_combo.currentText(),
                    symbols=symbols,
                    frequency=freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY),
                    mode=mode_map.get(self.import_mode_combo.currentText(), ImportMode.MANUAL),
                    start_date=self.start_date_edit.date().toString('yyyy-MM-dd'),
                    end_date=self.end_date_edit.date().toString('yyyy-MM-dd'),
                    batch_size=self.batch_size_spin.value(),
                    max_workers=self.max_workers_spin.value()
                )

                # 保存任务配置
                success = self.config_manager.add_import_task(task_config)
                if success:
                    self._populate_task_list()
                    self._log_message(f"任务 {task_name} 保存成功")
                    QMessageBox.information(self, "成功", "任务保存成功")
                else:
                    QMessageBox.warning(self, "错误", "任务保存失败")

            except Exception as e:
                logger.error(f"保存任务失败: {e}")
                QMessageBox.warning(self, "错误", f"任务保存失败: {str(e)}")
        else:
            # 模拟模式
            self._log_message(f"模拟保存任务: {task_name}")
            QMessageBox.information(self, "成功", "任务保存成功（模拟模式）")

    def _import_config(self):
        """导入配置"""
        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", "JSON文件 (*.json)"
        )

        if file_path and self.config_manager:
            success = self.config_manager.import_config(file_path)
            if success:
                self._populate_task_list()
                self._log_message("配置导入成功")
                QMessageBox.information(self, "成功", "配置导入成功")
            else:
                QMessageBox.warning(self, "错误", "配置导入失败")

    def _export_config(self):
        """导出配置"""
        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", "", "JSON文件 (*.json)"
        )

        if file_path and self.config_manager:
            success = self.config_manager.export_config(file_path)
            if success:
                self._log_message("配置导出成功")
                QMessageBox.information(self, "成功", "配置导出成功")
            else:
                QMessageBox.warning(self, "错误", "配置导出失败")

    def _populate_data_source_table(self):
        """填充数据源配置表"""
        try:
            # 获取统一数据管理器
            from core.containers import get_service_container
            from core.services.unified_data_manager import UnifiedDataManager

            service_container = get_service_container()
            if not service_container.is_registered(UnifiedDataManager):
                logger.warning("⚠️ 数据管理器不可用，无法获取数据源配置")
                return

            data_manager = service_container.resolve(UnifiedDataManager)
            registered_sources = data_manager.get_registered_data_sources()

            # 设置表格行数
            self.sources_table.setRowCount(len(registered_sources))

            # 填充数据
            for row, (plugin_id, info) in enumerate(registered_sources.items()):
                # 名称
                name_item = QTableWidgetItem(info.get('display_name', plugin_id))
                self.sources_table.setItem(row, 0, name_item)

                # 类型
                plugin_type = "数据源插件"
                if hasattr(info.get('adapter'), 'plugin_type'):
                    adapter_type = info['adapter'].plugin_type
                    # 如果是枚举类型，获取其值或名称
                    if hasattr(adapter_type, 'value'):
                        plugin_type = str(adapter_type.value)
                    elif hasattr(adapter_type, 'name'):
                        plugin_type = str(adapter_type.name)
                    else:
                        plugin_type = str(adapter_type)
                type_item = QTableWidgetItem(plugin_type)
                self.sources_table.setItem(row, 1, type_item)

                # 状态
                status = info.get('status', 'unknown')
                status_item = QTableWidgetItem(status)
                if status == 'active':
                    status_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                else:
                    status_item.setBackground(QColor(255, 182, 193))  # 浅红色
                self.sources_table.setItem(row, 2, status_item)

                # 操作按钮
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)

                config_btn = QPushButton("配置")
                config_btn.setFixedSize(50, 25)
                config_btn.clicked.connect(lambda checked, pid=plugin_id: self._configure_data_source(pid))

                test_btn = QPushButton("测试")
                test_btn.setFixedSize(50, 25)
                test_btn.clicked.connect(lambda checked, pid=plugin_id: self._test_data_source(pid))

                action_layout.addWidget(config_btn)
                action_layout.addWidget(test_btn)
                action_layout.addStretch()

                self.sources_table.setCellWidget(row, 3, action_widget)

            # 调整列宽
            self.sources_table.resizeColumnsToContents()

            logger.info(f"✅ 数据源配置表已填充，共 {len(registered_sources)} 个数据源")

        except Exception as e:
            logger.error(f"❌ 填充数据源配置表失败: {e}")

    def _configure_data_source(self, plugin_id: str):
        """配置数据源"""
        QMessageBox.information(self, "配置数据源", f"配置数据源 {plugin_id} 的功能开发中...")

    def _test_data_source(self, plugin_id: str):
        """测试数据源连接"""
        try:
            from core.containers import get_service_container
            from core.services.unified_data_manager import UnifiedDataManager

            service_container = get_service_container()
            data_manager = service_container.resolve(UnifiedDataManager)

            # 获取数据源信息
            source_info = data_manager.get_data_source_info(plugin_id)
            if source_info:
                QMessageBox.information(
                    self,
                    "测试结果",
                    f"数据源 {plugin_id} 连接正常\n"
                    f"显示名称: {source_info.get('display_name', 'N/A')}\n"
                    f"优先级: {source_info.get('priority', 'N/A')}\n"
                    f"状态: {source_info.get('status', 'N/A')}"
                )
            else:
                QMessageBox.warning(self, "测试失败", f"未找到数据源 {plugin_id} 的信息")

        except Exception as e:
            logger.error(f"❌ 测试数据源失败: {e}")
            QMessageBox.critical(self, "测试失败", f"测试数据源连接失败:\n{str(e)}")

    def _refresh_data_sources(self):
        """刷新数据源列表"""
        try:
            # 刷新数据源配置表
            self._populate_data_source_table()

            # 刷新任务管理中的数据源下拉框
            current_text = self.data_source_combo.currentText()
            self.data_source_combo.clear()
            self._populate_data_sources()

            # 尝试恢复之前的选择
            index = self.data_source_combo.findText(current_text)
            if index >= 0:
                self.data_source_combo.setCurrentIndex(index)

            logger.info("✅ 数据源列表已刷新")
            QMessageBox.information(self, "刷新完成", "数据源列表已更新")

        except Exception as e:
            logger.error(f"❌ 刷新数据源失败: {e}")
            QMessageBox.critical(self, "刷新失败", f"刷新数据源列表失败:\n{str(e)}")

    def _add_data_source(self):
        """添加数据源"""
        QMessageBox.information(self, "提示", "数据源配置功能开发中...")

    def _log_message(self, message: str):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        logger.info(message)

    # 任务执行引擎信号处理
    def _on_task_started(self, task_id: str):
        """任务开始处理"""
        self._log_message(f"任务 {task_id} 已启动")
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("任务启动中...")

    def _on_task_progress(self, task_id: str, progress: float, message: str):
        """任务进度处理"""
        self.progress_bar.setValue(int(progress))
        self.progress_label.setText(message)
        self._log_message(f"任务 {task_id}: {message} ({progress:.1f}%)")

    def _on_task_completed(self, task_id: str, result):
        """任务完成处理"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        # 从运行列表中移除任务
        self.running_tasks.discard(task_id)

        # 更新按钮状态
        current_item = self.task_list.currentItem()
        if current_item and current_item.data(Qt.UserRole) == task_id:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

        self._log_message(f"任务 {task_id} 执行完成")
        logger.info(f"任务 {task_id} 已从运行列表中移除")
        self._update_monitor_stats()

    def _on_task_failed(self, task_id: str, error_message: str):
        """任务失败处理"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        # 从运行列表中移除任务
        self.running_tasks.discard(task_id)

        # 更新按钮状态
        current_item = self.task_list.currentItem()
        if current_item and current_item.data(Qt.UserRole) == task_id:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

        self._log_message(f"任务 {task_id} 执行失败: {error_message}")
        logger.info(f"失败任务 {task_id} 已从运行列表中移除")
        QMessageBox.warning(self, "任务失败", f"任务执行失败:\n{error_message}")

    # ==================== 异步导入信号处理 ====================

    def _on_async_import_started(self, task_id: str):
        """异步导入开始"""
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"异步导入任务启动: {task_id}")
        self._log_message(f"🚀 异步导入任务启动: {task_id}")

        # 更新按钮状态
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def _on_async_progress_updated(self, progress: int, message: str):
        """异步导入进度更新"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
        if progress % 10 == 0:  # 每10%记录一次日志
            self._log_message(f"进度更新: {progress}% - {message}")

    def _on_async_import_completed(self, task_id: str, result: dict):
        """异步导入完成"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        # 从运行列表中移除任务
        self.running_tasks.discard(task_id)

        # 更新按钮状态
        current_item = self.task_list.currentItem()
        if current_item and current_item.data(Qt.UserRole) == task_id:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

        imported_count = result.get('imported_count', 0)
        failed_count = result.get('failed_count', 0)

        self._log_message(f"✅ 异步导入任务完成: {task_id}")
        self._log_message(f"   - 成功导入: {imported_count} 条记录")
        self._log_message(f"   - 失败记录: {failed_count} 条")
        logger.info(f"异步任务 {task_id} 已从运行列表中移除")

        # 更新监控统计
        self._update_monitor_stats()

    def _on_async_import_failed(self, task_id: str, error_msg: str):
        """异步导入失败"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        # 从运行列表中移除任务
        self.running_tasks.discard(task_id)

        # 更新按钮状态
        current_item = self.task_list.currentItem()
        if current_item and current_item.data(Qt.UserRole) == task_id:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

        self._log_message(f"❌ 异步导入任务失败: {task_id} - {error_msg}", "error")
        logger.info(f"失败的异步任务 {task_id} 已从运行列表中移除")
        QMessageBox.warning(self, "异步导入失败", f"异步导入任务失败:\n{error_msg}")

    def _on_async_data_chunk_imported(self, task_id: str, imported: int, total: int):
        """异步数据块导入进度"""
        progress_text = f"数据导入进度: {imported}/{total}"
        self._log_message(f"📊 {task_id}: {progress_text}")

    def _update_monitor_stats(self):
        """更新监控统计"""
        if self.execution_engine:
            running_tasks = len(self.execution_engine.get_running_tasks())
            self.running_tasks_label.setText(str(running_tasks))

        if self.config_manager:
            all_tasks = len(self.config_manager.get_all_import_tasks())
            self.total_tasks_label.setText(str(all_tasks))

            # 获取统计信息
            stats = self.config_manager.get_statistics()
            success_rate = stats.get('success_rate', 0)
            self.success_rate_label.setText(f"{success_rate:.1f}%")

            total_records = stats.get('total_records', 0)
            self.data_volume_label.setText(f"{total_records:,}")

    def closeEvent(self, event):
        """关闭事件"""
        if self.execution_engine:
            self.execution_engine.cleanup()
        event.accept()


def main():
    """测试函数"""
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    widget = DataImportWidget()
    widget.resize(1200, 800)
    widget.show()

    sys.exit(app.exec_())
