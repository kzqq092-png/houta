#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版数据导入UI组件

集成了所有新开发的智能化功能：
- AI预测和参数优化
- 实时性能监控和异常检测
- 多级缓存系统
- 分布式执行
- 自动调优
- 数据质量监控

作者: FactorWeave-Quant团队
版本: 2.0 (集成智能化功能)
"""

import sys
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QSplitter, QScrollArea,
    QTableWidget, QTableWidgetItem, QTextEdit, QProgressBar,
    QGroupBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QApplication, QHeaderView, QComboBox, QLineEdit,
    QDateEdit, QSpinBox, QCheckBox, QListWidget, QListWidgetItem,
    QMessageBox, QMenu, QToolBar, QAction, QStatusBar,
    QDialog, QDialogButtonBox, QFormLayout, QAbstractItemView,
    QSlider, QDoubleSpinBox, QLCDNumber, QTableWidgetSelectionRange
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QDate, QSize,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QObject
)
from PyQt5.QtGui import (
    QFont, QPalette, QColor, QIcon, QPixmap, QPainter,
    QLinearGradient, QPen, QBrush
)

# 导入核心组件
try:
    from utils.theme import get_theme_manager
    THEME_AVAILABLE = True
except ImportError as e:
    logger.warning(f"主题系统不可用: {e}") if logger else None
    THEME_AVAILABLE = False

try:
    from gui.utils.display_optimization import DisplayOptimizer, VirtualizationManager, MemoryManager
    PERFORMANCE_OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"性能优化模块不可用: {e}") if logger else None
    PERFORMANCE_OPTIMIZATION_AVAILABLE = False

try:
    from core.importdata.import_execution_engine import DataImportExecutionEngine
    from core.importdata.import_config_manager import ImportConfigManager, ImportTaskConfig, DataFrequency, ImportMode
    from core.plugin_types import AssetType, DataType, PluginType
    from gui.utils.responsive_layout_manager import (
        ResponsiveLayoutManager, ResponsiveConfig, ScreenSize, LayoutMode,
        ResponsiveTabWidget, apply_responsive_behavior
    )
    # 导入UI适配化
    from core.ui_integration.ui_business_logic_adapter import (
        get_ui_adapter, initialize_ui_adapter, TaskStatusUIModel,
        AIStatusUIModel, PerformanceUIModel, QualityUIModel
    )
    from core.ui_integration.ui_state_synchronizer import (
        get_ui_synchronizer, initialize_ui_synchronizer
    )
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    logger = None
    print(f"导入核心组件失败: {e}")
    CORE_AVAILABLE = False

logger = logger.bind(module=__name__) if logger else None

try:
    from gui.widgets.task_dependency_visualizer import TaskDependencyVisualizer
    DEPENDENCY_VISUALIZER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"任务依赖可视化器导入失败: {e}") if logger else None
    DEPENDENCY_VISUALIZER_AVAILABLE = False

# 导入实时写入UI组件（仅监控面板，配置和控制已融入左侧面板）
try:
    from gui.widgets.realtime_write_ui_components import RealtimeWriteMonitoringWidget, IPMonitorWidget
    REALTIME_WRITE_UI_AVAILABLE = True
    logger.info("实时写入监控组件已加载") if logger else None
except ImportError as e:
    logger.warning(f"实时写入监控组件导入失败: {e}") if logger else None
    REALTIME_WRITE_UI_AVAILABLE = False
    RealtimeWriteMonitoringWidget = None
    IPMonitorWidget = None


class IPStatsWorker(QObject):
    """IP统计信息获取工作线程（避免阻塞UI）"""
    finished = pyqtSignal(dict)  # 获取完成信号
    error = pyqtSignal(str)  # 错误信号

    def __init__(self, import_engine):
        super().__init__()
        self.import_engine = import_engine

    def fetch_ip_stats(self):
        """在后台线程获取IP统计信息"""
        try:
            if not self.import_engine:
                self.error.emit("导入引擎不可用")
                return

            # 获取IP统计信息（可能耗时）
            ip_stats = self.import_engine.get_tongdaxin_ip_stats()
            self.finished.emit(ip_stats if ip_stats else {})
        except Exception as e:
            logger.error(f"获取IP统计信息失败: {e}", exc_info=True)
            self.error.emit(str(e))


class DataLoadWorker(QThread):
    """数据加载工作线程"""
    finished = pyqtSignal(list)  # 加载完成信号
    error = pyqtSignal(str)  # 错误信号
    progress = pyqtSignal(int, str)  # 进度信号 (百分比, 消息)

    def __init__(self, asset_type: str, parent_dialog):
        super().__init__()
        self.asset_type = asset_type
        self.parent_dialog = parent_dialog

    def run(self):
        """在后台线程执行数据加载"""
        try:
            self.progress.emit(10, f"正在连接{self.asset_type}数据源...")

            # 调用父对话框的数据获取方法
            if self.asset_type == "股票" or self.asset_type == "A股":
                self.progress.emit(30, "正在获取股票列表...")
                data = self.parent_dialog.get_stock_data()
            elif self.asset_type == "指数":
                self.progress.emit(30, "正在获取指数列表...")
                data = self.parent_dialog.get_index_data()
            elif self.asset_type == "期货":
                self.progress.emit(30, "正在获取期货列表...")
                data = self.parent_dialog.get_futures_data()
            elif self.asset_type == "基金":
                self.progress.emit(30, "正在获取基金列表...")
                data = self.parent_dialog.get_fund_data()
            elif self.asset_type == "债券":
                self.progress.emit(30, "正在获取债券列表...")
                data = self.parent_dialog.get_bond_data()
            else:
                data = []

            self.progress.emit(90, "正在处理数据...")
            self.finished.emit(data if data else [])

        except Exception as e:
            logger.error(f"数据加载失败: {e}") if logger else None
            import traceback
            logger.error(traceback.format_exc()) if logger else None
            self.error.emit(str(e))


class BatchSelectionDialog(QDialog):
    """批量选择对话框（异步加载版）"""

    def __init__(self, asset_type: str, parent=None):
        super().__init__(parent)
        self.asset_type = asset_type
        self.selected_codes = []
        self.all_items = []
        self.loading_worker = None
        self.progress_dialog = None

        self.setWindowTitle(f"批量选择{asset_type}代码")
        self.setModal(True)
        self.resize(800, 600)

        self.setup_ui()
        # 延迟加载数据，避免阻塞UI
        QTimer.singleShot(100, self.load_data_async)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 搜索区域
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(f"输入{self.asset_type}名称或代码进行搜化..")
        self.search_edit.textChanged.connect(self.filter_items)
        search_layout.addWidget(self.search_edit)

        layout.addLayout(search_layout)

        # 列表区域
        self.item_list = QTableWidget()
        self.item_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.item_list.setColumnCount(2)  # 只需要代码和名称两列
        self.item_list.setHorizontalHeaderLabels(["代码", "名称"])

        # 设置选择模式为多选整行
        self.item_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.item_list.setSelectionMode(QTableWidget.MultiSelection)

        # 连接行点击事件
        self.item_list.itemClicked.connect(self.on_row_clicked)

        # 设置列宽
        header = self.item_list.horizontalHeader()
        header.setStretchLastSection(True)
        self.item_list.setColumnWidth(0, 100)

        layout.addWidget(self.item_list)

        # 统计信息
        self.stats_label = QLabel("优化0项，已选择 0项")
        layout.addWidget(self.stats_label)

        # 按钮区域
        button_layout = QHBoxLayout()

        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton("清空")
        clear_all_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(clear_all_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color:  # 28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton: hover {
                background-color:  # 218838;
            }
        """)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

    def load_data_async(self):
        """异步加载数据（使用QThread）"""
        try:
            # 创建进度对话框
            from PyQt5.QtWidgets import QProgressDialog
            self.progress_dialog = QProgressDialog(
                f"正在加载{self.asset_type}数据，请稍候...",
                "取消",
                0,
                100,
                self
            )
            self.progress_dialog.setWindowTitle("数据加载中")
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setValue(0)

            # 创建并启动工作线程
            self.loading_worker = DataLoadWorker(self.asset_type, self)
            self.loading_worker.progress.connect(self.on_loading_progress)
            self.loading_worker.finished.connect(self.on_loading_finished)
            self.loading_worker.error.connect(self.on_loading_error)

            # 连接取消按钮
            self.progress_dialog.canceled.connect(self.on_loading_canceled)

            self.loading_worker.start()

        except Exception as e:
            logger.error(f"启动异步加载失败: {e}") if logger else None
            import traceback
            logger.error(traceback.format_exc()) if logger else None
            QMessageBox.warning(self, "加载失败", f"启动数据加载失败: {str(e)}")

    def on_loading_progress(self, value: int, message: str):
        """更新加载进度"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)

    def on_loading_finished(self, data: list):
        """数据加载完成"""
        try:
            if self.progress_dialog:
                self.progress_dialog.setValue(100)
                self.progress_dialog.close()

            self.all_items = data
            logger.info(f"✅ 数据加载完成: {len(self.all_items)} 条记录") if logger else None

            # 更新UI
            self.populate_table(self.all_items)

        except Exception as e:
            logger.error(f"处理加载完成事件失败: {e}") if logger else None

    def on_loading_error(self, error_msg: str):
        """数据加载错误"""
        if self.progress_dialog:
            self.progress_dialog.close()

        QMessageBox.critical(
            self,
            "加载失败",
            f"加载{self.asset_type}数据失败:\n{error_msg}\n\n请检查数据源连接或稍后重试。"
        )

    def on_loading_canceled(self):
        """用户取消加载"""
        if self.loading_worker and self.loading_worker.isRunning():
            self.loading_worker.terminate()
            self.loading_worker.wait()
        logger.info("用户取消了数据加载") if logger else None

    def get_stock_data(self):
        """获取股票数据 - 根据用户选择的数据源"""
        try:
            # 获取父窗口中用户选择的数据源
            selected_data_source = None
            selected_plugin_name = None

            logger.info("开始获取股票数据...") if logger else None

            if hasattr(self.parent(), 'data_source_combo') and hasattr(self.parent(), 'data_source_mapping'):
                selected_display_name = self.parent().data_source_combo.currentText()
                selected_plugin_name = self.parent().data_source_mapping.get(selected_display_name)
                logger.info(f"父窗口数据源信息: combo={hasattr(self.parent(), 'data_source_combo')}, mapping={hasattr(self.parent(), 'data_source_mapping')}") if logger else None
                logger.info(f"选择的显示名称: {selected_display_name}") if logger else None
                logger.info(f"映射的插件名称: {selected_plugin_name}") if logger else None
                logger.info(f"完整映射表: {self.parent().data_source_mapping}") if logger else None
            else:
                logger.warning("父窗口缺少必要属性") if logger else None

            # 方案1: 优先通过选定的插件获取（符合业务逻辑）
            if selected_plugin_name:
                logger.info(f"尝试直接从插件 {selected_plugin_name} 获取数据...") if logger else None

                from core.plugin_manager import PluginManager

                try:
                    # 通过ServiceContainer获取PluginManager实例
                    from core.containers import get_service_container
                    container = get_service_container()
                    plugin_manager = container.resolve(PluginManager) if container else None
                    logger.info(f"PluginManager实例: {plugin_manager is not None}") if logger else None

                    if plugin_manager:
                        plugin = plugin_manager.get_plugin(selected_plugin_name)
                        logger.info(f"插件实例: {plugin is not None}, 类型: {type(plugin)}") if logger else None

                        if plugin:
                            # 尝试调用插件的股票列表获取方法
                            if hasattr(plugin, 'get_stock_list'):
                                logger.info("插件有get_stock_list方法") if logger else None
                                stock_list_data = plugin.get_stock_list()

                                # 处理DataFrame和列表两种格式
                                if hasattr(stock_list_data, 'empty'):  # DataFrame
                                    logger.info(f"get_stock_list返回DataFrame: {len(stock_list_data) if not stock_list_data.empty else 0} 条数据") if logger else None
                                    if not stock_list_data.empty:
                                        # 将DataFrame转换为标准格式
                                        stock_list = []
                                        for _, row in stock_list_data.iterrows():
                                            stock_info = {
                                                "code": row.get('code', ''),
                                                "name": row.get('name', ''),
                                                "category": row.get('industry', '其他')
                                            }
                                            stock_list.append(stock_info)
                                        logger.info(f"✅ 从插件DataFrame获取股票数据: {len(stock_list)} 只") if logger else None
                                        return stock_list
                                else:  # 列表格式
                                    logger.info(f"get_stock_list返回列表: {len(stock_list_data) if stock_list_data else 0} 条数据") if logger else None
                                    if stock_list_data:
                                        logger.info(f"✅ 直接从插件获取股票数据: {len(stock_list_data)} 只") if logger else None
                                        return stock_list_data
                            elif hasattr(plugin, 'get_asset_list'):
                                logger.info("插件有get_asset_list方法") if logger else None
                                from core.plugin_types import AssetType
                                asset_list_data = plugin.get_asset_list(AssetType.STOCK_A)
                                logger.info(f"get_asset_list返回: {len(asset_list_data) if asset_list_data else 0} 条数据") if logger else None
                                if asset_list_data:
                                    logger.info(f"✅ 从插件获取资产数据: {len(asset_list_data)} 只") if logger else None
                                    return asset_list_data
                            else:
                                logger.warning("插件没有get_stock_list或get_asset_list方法") if logger else None
                        else:
                            logger.warning("无法获取插件实例") if logger else None
                    else:
                        logger.warning("PluginManager实例为空") if logger else None
                except Exception as e:
                    logger.error(f"从插件获取数据失败: {e}") if logger else None
                    import traceback
                    logger.error(f"详细错误: {traceback.format_exc()}") if logger else None
            else:
                logger.warning("selected_plugin_name为空，无法从插件获取数据") if logger else None

            # 方案2: 备用方案 - 通过 UnifiedDataManager 获取（当插件获取失败时）
            logger.info("插件获取失败，尝试备用方案...") if logger else None
            from core.services.unified_data_manager import get_unified_data_manager
            from core.containers import get_service_container
            from core.services.unified_data_manager import UnifiedDataManager
            from core.events import get_event_bus

            data_manager = None

            # 尝试从get_unified_data_manager获取
            try:
                data_manager = get_unified_data_manager()
                if data_manager:
                    logger.info("通过get_unified_data_manager获取UnifiedDataManager成功") if logger else None
            except Exception as e:
                logger.debug(f"get_unified_data_manager失败: {e}") if logger else None

            # 如果失败，尝试从ServiceContainer获取
            if not data_manager:
                try:
                    container = get_service_container()
                    if container and container.is_registered(UnifiedDataManager):
                        data_manager = container.resolve(UnifiedDataManager)
                        logger.info("从ServiceContainer获取UnifiedDataManager成功") if logger else None
                except Exception as e:
                    logger.debug(f"从ServiceContainer获取失败: {e}") if logger else None

            # 如果仍然失败，尝试手动创建
            if not data_manager:
                try:
                    container = get_service_container()
                    event_bus = get_event_bus()
                    if container and event_bus:
                        data_manager = UnifiedDataManager(container, event_bus)
                        # 注册到容器
                        container.register_instance(UnifiedDataManager, data_manager)
                        logger.info("手动创建并注册UnifiedDataManager成功") if logger else None
                except Exception as e:
                    logger.debug(f"手动创建UnifiedDataManager失败: {e}") if logger else None

            if data_manager:
                logger.info("尝试通过UnifiedDataManager获取股票数据...") if logger else None

                # 获取资产列表（从DuckDB或数据源）
                asset_df = data_manager.get_asset_list(asset_type='stock', market='all')

                if not asset_df.empty:
                    stock_list = []
                    for _, row in asset_df.iterrows():
                        stock_info = {
                            "code": row.get('code', ''),
                            "name": row.get('name', ''),
                            "category": row.get('industry', '其他')
                        }
                        stock_list.append(stock_info)

                    logger.info(f"✅ 成功获取股票数据: {len(stock_list)} 只股票") if logger else None
                    return stock_list
                else:
                    logger.warning("UnifiedDataManager返回空DataFrame") if logger else None

            # 失败提示
            logger.error("所有方案都无法获取股票数据") if logger else None
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "数据获取失败",
                f"无法获取股票列表数据。\n\n"
                f"可能原因:\n"
                f"1. 数据源插件未正确注册或初始化\n"
                f"2. DuckDB数据库为空，需先导入数据\n"
                f"3. 网络连接问题（如使用在线数据源）\n\n"
                f"建议:\n"
                f"• 检查插件状态\n"
                f"• 尝试运行数据导入\n"
                f"• 查看日志了解详细错误"
            )
            return []

        except Exception as e:
            logger.error(f"获取股票数据失败: {e}", exc_info=True) if logger else None
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"获取股票数据时发生错误:\n{str(e)}")
            return []

    def get_index_data(self):
        """获取指数数据 - 优先使用统一插件数据管理器"""
        try:
            # 首先尝试使用统一插件数据管理器（最新架构）
            from core.services.uni_plugin_data_manager import get_uni_plugin_data_manager

            uni_manager = get_uni_plugin_data_manager()
            if uni_manager:
                # 通过统一插件数据管理器获取指数列表
                index_list_data = uni_manager.get_index_list()
                if index_list_data:
                    logger.info(f"通过统一插件数据管理器成功获取最新指数数据: {len(index_list_data)} 个指数") if logger else None
                    return index_list_data

            # 备用方案：使用原有统一数据管理器
            from core.services.unified_data_manager import get_unified_data_manager
            from core.plugin_types import AssetType

            data_manager = get_unified_data_manager()
            if data_manager:
                # 确保TET功能开启
                if hasattr(data_manager, 'tet_enabled'):
                    if not data_manager.tet_enabled:
                        logger.info("启用TET数据管道以获取最新指数数据") if logger else None
                        data_manager.tet_enabled = True

                # 获取指数列表（传入AssetType.INDEX）- 这里会优先使用TET管道
                index_df = data_manager.get_stock_list(market='index')
                if not index_df.empty:
                    # 转换为所需格式
                    index_list = []
                    for _, row in index_df.iterrows():
                        index_info = {
                            "code": row.get('code', ''),
                            "name": row.get('name', ''),
                            "category": "指数"
                        }
                        index_list.append(index_info)
                    logger.info(f"通过TET管道成功获取最新指数数据: {len(index_list)} 个指数") if logger else None
                    return index_list

            # 备用方案：返回常用指数
            basic_indices = [
                {"code": "000001", "name": "上证指数", "category": "主要指数"},
                {"code": "399001", "name": "深证成指", "category": "主要指数"},
                {"code": "399006", "name": "创业板指", "category": "主要指数"},
                {"code": "000300", "name": "沪深300", "category": "主要指数"},
                {"code": "000905", "name": "中证500", "category": "主要指数"}
            ]
            logger.info(f"使用基础指数数据: {len(basic_indices)} 个指数") if logger else None
            return basic_indices

        except Exception as e:
            logger.error(f"获取指数数据失败: {e}") if logger else None
            return []

    def get_futures_data(self):
        """获取期货数据 - 优先使用TET时候接口"""
        try:
            # 使用统一数据管理器获取真实期货数据（已集成TET管道）
            from core.services.unified_data_manager import get_unified_data_manager
            from core.plugin_types import AssetType

            data_manager = get_unified_data_manager()
            if data_manager:
                # 确保TET功能开启
                if hasattr(data_manager, 'tet_enabled'):
                    if not data_manager.tet_enabled:
                        logger.info("启用TET数据管道以获取最新期货数据") if logger else None
                        data_manager.tet_enabled = True

                # 获取期货列表（传入AssetType.FUTURES）- 这里会优先使用TET管道
                futures_df = data_manager.get_stock_list(market='futures')
                if not futures_df.empty:
                    # 转换为所需格式
                    futures_list = []
                    for _, row in futures_df.iterrows():
                        futures_info = {
                            "code": row.get('code', ''),
                            "name": row.get('name', ''),
                            "category": row.get('industry', '期货')
                        }
                        futures_list.append(futures_info)
                    logger.info(f"通过TET管道成功获取最新期货数据: {len(futures_list)} 个期货") if logger else None
                    return futures_list

            # 备用方案：返回常用期货
            basic_futures = [
                {"code": "IF2401", "name": "沪深300股指期货", "category": "金融"},
                {"code": "IH2401", "name": "上证50股指期货", "category": "金融"},
                {"code": "IC2401", "name": "中证500股指期货", "category": "金融"},
                {"code": "AU2401", "name": "黄金期货", "category": "金属"},
                {"code": "AG2401", "name": "白银期货", "category": "金属"}
            ]
            logger.info(f"使用基础期货数据: {len(basic_futures)} 个期货") if logger else None
            return basic_futures

        except Exception as e:
            logger.error(f"获取期货数据失败: {e}") if logger else None
            return []

    def get_fund_data(self):
        """获取基金数据 - 优先使用统一插件数据管理器"""
        try:
            # 首先尝试使用统一插件数据管理器（最新架构）
            from core.services.uni_plugin_data_manager import get_uni_plugin_data_manager

            uni_manager = get_uni_plugin_data_manager()
            if uni_manager:
                # 通过统一插件数据管理器获取基金列表
                fund_list_data = uni_manager.get_fund_list()
                if fund_list_data:
                    logger.info(f"通过统一插件数据管理器成功获取最新基金数据: {len(fund_list_data)} 个基金") if logger else None
                    return fund_list_data

            # 备用方案：使用原有统一数据管理器
            from core.services.unified_data_manager import get_unified_data_manager
            from core.plugin_types import AssetType

            data_manager = get_unified_data_manager()
            if data_manager:
                # 确保TET功能开启
                if hasattr(data_manager, 'tet_enabled'):
                    if not data_manager.tet_enabled:
                        logger.info("启用TET数据管道以获取最新基金数据") if logger else None
                        data_manager.tet_enabled = True

                # 获取基金列表（传入AssetType.FUND）- 这里会优先使用TET管道
                fund_df = data_manager.get_stock_list(market='fund')
                if not fund_df.empty:
                    # 转换为所需格式
                    fund_list = []
                    for _, row in fund_df.iterrows():
                        fund_info = {
                            "code": row.get('code', ''),
                            "name": row.get('name', ''),
                            "category": row.get('industry', '基金')
                        }
                        fund_list.append(fund_info)
                    logger.info(f"通过TET管道成功获取最新基金数据: {len(fund_list)} 个基金") if logger else None
                    return fund_list

            # 备用方案：返回常用基金
            basic_funds = [
                {"code": "000001", "name": "华夏成长", "category": "股票"},
                {"code": "110022", "name": "易方达消费", "category": "股票"},
                {"code": "161725", "name": "招商中证白酒", "category": "指数"},
                {"code": "163407", "name": "兴全沪深300", "category": "指数"}
            ]
            logger.info(f"使用基础基金数据: {len(basic_funds)} 个基金") if logger else None
            return basic_funds

        except Exception as e:
            logger.error(f"获取基金数据失败: {e}") if logger else None
            return []

    def get_bond_data(self):
        """获取债券数据 - 优先使用TET时候接口"""
        try:
            # 使用统一数据管理器获取真实债券数据（已集成TET管道）
            from core.services.unified_data_manager import get_unified_data_manager
            from core.plugin_types import AssetType

            data_manager = get_unified_data_manager()
            if data_manager:
                # 确保TET功能开启
                if hasattr(data_manager, 'tet_enabled'):
                    if not data_manager.tet_enabled:
                        logger.info("启用TET数据管道以获取最新债券数据") if logger else None
                        data_manager.tet_enabled = True

                # 获取债券列表（传入AssetType.BOND）- 这里会优先使用TET管道
                bond_df = data_manager.get_stock_list(market='bond')
                if not bond_df.empty:
                    # 转换为所需格式
                    bond_list = []
                    for _, row in bond_df.iterrows():
                        bond_info = {
                            "code": row.get('code', ''),
                            "name": row.get('name', ''),
                            "category": row.get('industry', '债券')
                        }
                        bond_list.append(bond_info)
                    logger.info(f"通过TET管道成功获取最新债券数据: {len(bond_list)} 个债券") if logger else None
                    return bond_list

            # 备用方案：返回常用债券
            basic_bonds = [
                {"code": "019649", "name": "21国债1", "category": "国债"},
                {"code": "019664", "name": "21国债6", "category": "国债"},
                {"code": "180401", "name": "18农发01", "category": "金融债"},
                {"code": "180210", "name": "18国开10", "category": "金融债"}
            ]
            logger.info(f"使用基础债券数据: {len(basic_bonds)} 个债券") if logger else None
            return basic_bonds

        except Exception as e:
            logger.error(f"获取债券数据失败: {e}") if logger else None
            return []

    def populate_table(self, items):
        """填充表格（优化版 - 无复选框，性能提升）"""
        logger.info(f"populate_table被调用，数据量: {len(items) if items else 0}") if logger else None

        if not items:
            logger.warning("items为空，设置表格行数为0") if logger else None
            self.item_list.setRowCount(0)
            self.update_stats()
            return

        logger.info(f"设置表格行数: {len(items)}") if logger else None

        # 性能优化：暂停UI更新
        self.item_list.setUpdatesEnabled(False)
        try:
            self.item_list.setRowCount(len(items))

            for row, item in enumerate(items):
                # 代码列
                code_item = QTableWidgetItem(item["code"])
                self.item_list.setItem(row, 0, code_item)

                # 名称列
                name_item = QTableWidgetItem(item["name"])
                self.item_list.setItem(row, 1, name_item)

            logger.info("🔍 [INFO] 表格填充完成，调用update_stats") if logger else None
            self.update_stats()
        finally:
            # 恢复UI更新
            self.item_list.setUpdatesEnabled(True)

    def filter_items(self, text):
        """过滤项目"""
        if not text:
            filtered_items = self.all_items
        else:
            text = text.lower()
            filtered_items = [
                item for item in self.all_items
                if text in item["code"].lower() or text in item["name"].lower()
            ]

        self.populate_table(filtered_items)

    def on_row_clicked(self, item):
        """行点击事件 - 切换选中状态"""
        row = item.row()
        # 如果行已选中，则取消选中；否则选中
        if self.item_list.item(row, 0).isSelected():
            self.item_list.setRangeSelected(
                QTableWidgetSelectionRange(row, 0, row, self.item_list.columnCount() - 1),
                False
            )
        else:
            self.item_list.setRangeSelected(
                QTableWidgetSelectionRange(row, 0, row, self.item_list.columnCount() - 1),
                True
            )
        self.update_stats()

    def select_all(self):
        """全选"""
        self.item_list.selectAll()
        self.update_stats()

    def clear_all(self):
        """清空选择"""
        self.item_list.clearSelection()
        self.update_stats()

    def update_stats(self):
        """更新统计信息（优化版）"""
        total = self.item_list.rowCount()
        selected = len(self.item_list.selectedItems()) // self.item_list.columnCount()  # 每行有2列，所以除以列数

        stats_text = f"共 {total} 项，已选择 {selected} 项"
        self.stats_label.setText(stats_text)

    def get_selected_codes(self):
        """获取选中的代码（优化版）"""
        selected_codes = []
        selected_rows = set()

        # 收集所有选中的行号
        for item in self.item_list.selectedItems():
            selected_rows.add(item.row())

        # 按行号排序后获取代码
        for row in sorted(selected_rows):
            code_item = self.item_list.item(row, 0)  # 第0列是代码
            if code_item:
                selected_codes.append(code_item.text())

        return selected_codes


class EnhancedDataImportWidget(QWidget):
    """增强版数据导入主界面"""

    # 信号定义
    task_started = pyqtSignal(str)  # 任务开化
    task_completed = pyqtSignal(str, object)  # 任务完成
    task_failed = pyqtSignal(str, str)  # 任务失败

    def __init__(self, parent=None, plugin_manager=None):
        super().__init__(parent)

        # 初始化核心组化
        self.import_engine = None
        self.config_manager = None
        self.ui_adapter = None
        self.ui_synchronizer = None
        self.plugin_manager = plugin_manager  # ✅ 直接保存plugin_manager
        self.db_manager = None  # ✅ 初始化db_manager以避免AttributeError

        # 初始化数据源映射（用于动态加载数据源插件）
        self.data_source_mapping = {}

        # 初始化主题系统
        self.theme_manager = None
        self.design_system = None  # 初始化设计系统属性
        if THEME_AVAILABLE:
            try:
                from utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                self.theme_manager = get_theme_manager(config_manager)
                # 尝试获取设计系统
                if hasattr(self.theme_manager, 'design_system'):
                    self.design_system = self.theme_manager.design_system
                logger.info("主题系统初始化成功") if logger else None
            except Exception as e:
                logger.error(f"主题系统初始化失败: {e}") if logger else None

        # 初始化性能优化组件
        self.display_optimizer = None
        self.virtualization_manager = None
        self.memory_manager = None
        if PERFORMANCE_OPTIMIZATION_AVAILABLE:
            try:
                self.display_optimizer = DisplayOptimizer()
                self.virtualization_manager = VirtualizationManager()
                self.memory_manager = MemoryManager()
                logger.info("性能优化组件初始化成功") if logger else None
            except Exception as e:
                logger.error(f"性能优化组件初始化失败: {e}") if logger else None

        if CORE_AVAILABLE:
            self.config_manager = ImportConfigManager()
            self.import_engine = DataImportExecutionEngine(
                config_manager=self.config_manager,
                max_workers=8,  # ✅ 优化：默认工作线程数从4增加到8，提升并行性能
                enable_ai_optimization=True
            )

            # 初始化UI适配器和同步化
            try:
                self.ui_adapter = initialize_ui_adapter()
                self.ui_synchronizer = initialize_ui_synchronizer(self.ui_adapter)
                logger.info("UI适配器和同步器初始化成功") if logger else None
            except Exception as e:
                logger.error(f"UI适配器初始化失败: {e}") if logger else None

        self.setup_ui()
        self.setup_responsive_layout()
        self._register_write_event_handlers()
        self.setup_connections()
        self.setup_timers()

        # 预初始化关键UI组件以避免运行时错误
        self._ensure_critical_components()

        # 应用统一主题
        self.apply_unified_theme()

        # 应用性能优化
        self.apply_performance_optimization()

    def apply_performance_optimization(self):
        """应用性能优化"""
        try:
            if self.display_optimizer:
                # 启用显示优化
                self.display_optimizer.optimize_widget(self)
                logger.debug("显示优化应用成功") if logger else None

            if self.virtualization_manager:
                # 启用虚拟化管理
                self.virtualization_manager.enable_for_widget(self)
                logger.debug("虚拟化管理启用成功") if logger else None

            if self.memory_manager:
                # 启用内存管理
                self.memory_manager.register_widget(self)
                logger.debug("内存管理注册成功") if logger else None
        except Exception as e:
            logger.warning(f"应用性能优化失败: {e}") if logger else None

    def _ensure_critical_components(self):
        """确保关键UI组件已初始化"""
        try:
            # 确保性能趋势组件存在
            if not hasattr(self, 'performance_trends'):
                self.performance_trends = QTextEdit()
                self.performance_trends.setMaximumHeight(100)
                self.performance_trends.setReadOnly(True)
                logger.debug("预创建了performance_trends组件") if logger else None

            # 确保状态标签存化
            if not hasattr(self, 'progress_label'):
                self.progress_label = QLabel("就绪")
                logger.debug("预创建了progress_label组件") if logger else None

            if not hasattr(self, 'predictions_count_label'):
                self.predictions_count_label = QLabel("0")
                logger.debug("预创建了predictions_count_label组件") if logger else None

            if not hasattr(self, 'time_saved_label'):
                self.time_saved_label = QLabel("0.0s")
                logger.debug("预创建了time_saved_label组件") if logger else None

            if not hasattr(self, 'accuracy_label'):
                self.accuracy_label = QLabel("0.0")
                logger.debug("预创建了accuracy_label组件") if logger else None

            if not hasattr(self, 'active_tuning_label'):
                self.active_tuning_label = QLabel("0")
                logger.debug("预创建了active_tuning_label组件") if logger else None

            if not hasattr(self, 'completed_tuning_label'):
                self.completed_tuning_label = QLabel("0")
                logger.debug("预创建了completed_tuning_label组件") if logger else None

            if not hasattr(self, 'total_improvement_label'):
                self.total_improvement_label = QLabel("0.0")
                logger.debug("预创建了total_improvement_label组件") if logger else None

            if not hasattr(self, 'discovered_nodes_label'):
                self.discovered_nodes_label = QLabel("0")
                logger.debug("预创建了discovered_nodes_label组件") if logger else None

            if not hasattr(self, 'available_nodes_label'):
                self.available_nodes_label = QLabel("0")
                logger.debug("预创建了available_nodes_label组件") if logger else None

            # 确保配置控件存在
            if not hasattr(self, 'batch_size_spin'):
                self.batch_size_spin = QSpinBox()
                self.batch_size_spin.setRange(1, 10000)
                self.batch_size_spin.setValue(1000)
                logger.debug("预创建了batch_size_spin组件") if logger else None

            if not hasattr(self, 'workers_spin'):
                self.workers_spin = QSpinBox()
                self.workers_spin.setRange(1, 32)
                self.workers_spin.setValue(8)  # ✅ 优化：默认工作线程数从4增加到8
                logger.debug("预创建了workers_spin组件") if logger else None

            # 确保日志文本框存在
            if not hasattr(self, 'log_text'):
                self.log_text = QTextEdit()
                self.log_text.setMaximumHeight(150)
                self.log_text.setReadOnly(True)
                logger.debug("预创建了log_text组件") if logger else None

            # 确保节点表格存在
            if not hasattr(self, 'nodes_table'):
                self.nodes_table = QTableWidget()
                self.nodes_table.setColumnCount(4)
                self.nodes_table.setHorizontalHeaderLabels(["节点ID", "地址", "任务数", "状态"])
                logger.debug("预创建了nodes_table组件") if logger else None

        except Exception as e:
            logger.warning(f"预初始化关键组件失败: {e}") if logger else None

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题区域
        title_frame = self.create_title_frame()
        layout.addWidget(title_frame)

        # 主要内容区域
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧：配置和控制面板
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)

        # 右侧：监控和状态面化
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)

        layout.addWidget(main_splitter)

    def create_title_frame(self) -> QFrame:
        """创建标题框架"""
        frame = QFrame()
        frame.setFixedHeight(60)
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0#4a90e2, stop:1#357abd);
                border-radius: 10px;
                margin: 5px;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
        """)

        layout = QHBoxLayout(frame)

        # 标题
        title_label = QLabel("K线专业数据导入系统")
        title_label.setFont(QFont("Arial", 15, QFont.Bold))
        layout.addWidget(title_label)

        layout.addStretch()

        # 版本信息
        version_label = QLabel("V2.0 - AI增强化")
        version_label.setFont(QFont("Arial", 10))
        layout.addWidget(version_label)

        return frame

    def create_left_panel(self) -> QWidget:
        """创建左侧控制面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 任务配置区域（已包含智能化功能，无需重复添加）
        config_group = self.create_task_config_group()
        layout.addWidget(config_group)

        # 任务操作区域
        task_ops_group = self.create_task_operations_group()
        layout.addWidget(task_ops_group)

        layout.addStretch()
        return widget

    def create_task_config_group(self) -> QGroupBox:
        """创建扩展任务配置组（合并所有配置，无Tab标签）"""
        group = QGroupBox("任务配置")
        group.setMinimumHeight(1000)
        group.setFont(QFont("Arial", 10, QFont.Bold))
        main_layout = QVBoxLayout(group)

        # 创建滚动区域以容纳所有配置
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(740)  # 设置合理的最小高度
        scroll.setMinimumWidth(450)
        scroll.setAlignment(Qt.AlignCenter)
        # 内容widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(5)

        # ==================== 第一部分：基本信息 ====================
        basic_info_group = QGroupBox("📋 基本信息")
        basic_layout = QFormLayout(basic_info_group)

        # 任务名称
        self.task_name_edit = QLineEdit()
        self.task_name_edit.setText(f"导入任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        basic_layout.addRow("任务名称:", self.task_name_edit)

        # 任务描述
        self.task_desc_edit = QTextEdit()
        self.task_desc_edit.setMaximumHeight(60)  # 恢复为60，更灵活
        self.task_desc_edit.setPlaceholderText("输入任务描述（可选）...")
        basic_layout.addRow("任务描述:", self.task_desc_edit)

        # 🎯 数据用途（新增）- 用于智能权重配置
        self.data_usage_combo = QComboBox()
        self.data_usage_combo.addItems([
            "通用场景",      # general - 默认
            "历史数据分析",  # historical
            "回测验证",      # backtest
            "实时行情",      # realtime
            "实盘交易"       # live_trading
        ])
        self.data_usage_combo.setToolTip(
            "选择数据用途后，系统会自动调整质量评分权重：\n"
            "• 历史数据分析：注重准确性和完整性\n"
            "• 回测验证：注重一致性和准确性\n"
            "• 实时行情：提高及时性权重\n"
            "• 实盘交易：最高及时性和准确性权重"
        )
        basic_layout.addRow("🎯 数据用途:", self.data_usage_combo)

        # 资产类型
        from core.ui_asset_type_utils import get_asset_type_combo_items
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems(get_asset_type_combo_items())
        self.asset_type_combo.currentTextChanged.connect(self.on_asset_type_changed)
        basic_layout.addRow("📊 资产类型:", self.asset_type_combo)

        # 数据类型
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["K线数据", "分笔数据", "财务数据", "基本面数据"])
        basic_layout.addRow("📈 数据类型:", self.data_type_combo)

        # 数据频率
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["日线", "周线", "月线", "5分钟", "15分钟", "30分钟", "60分钟"])
        basic_layout.addRow("⏱️ 数据频率:", self.frequency_combo)

        content_layout.addWidget(basic_info_group)

        # ==================== 第二部分：数据源配置 ====================
        datasource_group = QGroupBox("🔌 数据源配置")
        datasource_layout = QFormLayout(datasource_group)

        # 数据源选择 - 动态加载已注册的数据源插件
        self.data_source_combo = QComboBox()
        self._load_available_data_sources()
        datasource_layout.addRow("数据源:", self.data_source_combo)

        # 数据时间范围
        date_range_layout = QHBoxLayout()

        date_range_layout.addWidget(QLabel("开始日期:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-12))
        self.start_date.setCalendarPopup(True)
        date_range_layout.addWidget(self.start_date)

        date_range_layout.addWidget(QLabel("结束日期:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_range_layout.addWidget(self.end_date)

        datasource_layout.addRow("📅 时间范围:", date_range_layout)

        content_layout.addWidget(datasource_group)

        # ==================== 新增：增量下载配置 ====================
        incremental_group = QGroupBox("增量下载配置")
        incremental_layout = QVBoxLayout(incremental_group)

        # 下载模式选择 - 水平排列的单选按钮
        mode_label = QLabel("下载模式:")
        mode_label.setStyleSheet("font-weight: bold;")
        incremental_layout.addWidget(mode_label)

        mode_buttons_layout = QHBoxLayout()

        # 创建单选按钮组
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup
        self.mode_button_group = QButtonGroup()

        modes = [
            ("全量下载", "full", "下载指定时间范围内的所有数据"),
            ("增量下载", "incremental", "仅下载最新数据（默认7天）"),
            ("智能补全", "smart_fill", "自动识别并补全缺失数据"),
            ("间隙填充", "gap_fill", "填充特定范围内的数据间隙")
        ]

        for i, (label, value, tooltip) in enumerate(modes):
            radio_btn = QRadioButton(label)
            radio_btn.setToolTip(tooltip)
            radio_btn.setProperty("mode_value", value)
            self.mode_button_group.addButton(radio_btn, i)
            mode_buttons_layout.addWidget(radio_btn)

            # 第一个按钮默认选中
            if i == 0:
                radio_btn.setChecked(True)
                self.current_download_mode = "full"

        # 连接信号
        self.mode_button_group.buttonClicked.connect(self._on_mode_button_clicked)

        mode_buttons_layout.addStretch()
        incremental_layout.addLayout(mode_buttons_layout)

        # 添加分割线
        from PyQt5.QtWidgets import QFrame
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        incremental_layout.addWidget(separator)

        # 配置区域
        config_label = QLabel("模式配置:")
        config_label.setStyleSheet("font-weight: bold;")
        incremental_layout.addWidget(config_label)

        incremental_config_layout = QGridLayout()
        incremental_config_layout.setSpacing(10)

        # 回溯天数（增量下载模式）
        self.incremental_days_label = QLabel("回溯天数:")
        self.incremental_days_spin = QSpinBox()
        self.incremental_days_spin.setRange(1, 365)
        self.incremental_days_spin.setValue(7)
        self.incremental_days_spin.setToolTip("增量下载的回溯天数（默认：7天）")
        self.incremental_days_spin.setVisible(False)  # 默认隐藏
        self.incremental_days_label.setVisible(False)
        incremental_config_layout.addWidget(self.incremental_days_label, 0, 0)
        incremental_config_layout.addWidget(self.incremental_days_spin, 0, 1)

        # 补全策略（智能补全模式）
        self.completion_strategy_label = QLabel("补全策略:")
        self.completion_strategy_combo = QComboBox()
        self.completion_strategy_combo.addItems(["全部补全", "仅最近30天", "仅重要数据"])
        self.completion_strategy_combo.setToolTip("选择数据补全的策略")
        self.completion_strategy_combo.setVisible(False)  # 默认隐藏
        self.completion_strategy_label.setVisible(False)
        incremental_config_layout.addWidget(self.completion_strategy_label, 1, 0)
        incremental_config_layout.addWidget(self.completion_strategy_combo, 1, 1)

        # 间隙阈值（间隙填充模式）
        self.gap_threshold_label = QLabel("间隙阈值（天）:")
        self.gap_threshold_spin = QSpinBox()
        self.gap_threshold_spin.setRange(1, 365)
        self.gap_threshold_spin.setValue(30)
        self.gap_threshold_spin.setToolTip("最大间隙填充天数（默认：30天）")
        self.gap_threshold_spin.setVisible(False)  # 默认隐藏
        self.gap_threshold_label.setVisible(False)
        incremental_config_layout.addWidget(self.gap_threshold_label, 2, 0)
        incremental_config_layout.addWidget(self.gap_threshold_spin, 2, 1)

        incremental_layout.addLayout(incremental_config_layout)

        # 数据完整性检查选项
        self.check_completeness_cb = QCheckBox("启用数据完整性检查")
        self.check_completeness_cb.setChecked(True)
        self.check_completeness_cb.setToolTip("检查数据连续性，识别缺失日期")
        incremental_layout.addWidget(self.check_completeness_cb)

        # 自动跳过最新数据选项
        self.skip_latest_data_cb = QCheckBox("自动跳过已有最新数据")
        self.skip_latest_data_cb.setChecked(True)
        self.skip_latest_data_cb.setToolTip("如果数据已是最新，自动跳过下载")
        incremental_layout.addWidget(self.skip_latest_data_cb)

        content_layout.addWidget(incremental_group)

        # ==================== 第三部分：代码选择 ====================
        symbols_group = QGroupBox("🏷️ 股票选择")
        symbols_layout = QVBoxLayout(symbols_group)

        # 批量选择按钮区域
        batch_buttons_layout = QHBoxLayout()

        self.batch_select_btn = QPushButton("📦 批量选择")
        self.batch_select_btn.clicked.connect(self.show_batch_selection_dialog)
        batch_buttons_layout.addWidget(self.batch_select_btn)

        # 快速选择按钮
        self.quick_select_btn = QPushButton("🔍 快速选择")
        self.quick_select_btn.clicked.connect(self.show_quick_selection_dialog)
        batch_buttons_layout.addWidget(self.quick_select_btn)

        self.clear_symbols_btn = QPushButton("🗑️ 清空")
        self.clear_symbols_btn.clicked.connect(lambda: self.symbols_edit.clear())
        batch_buttons_layout.addWidget(self.clear_symbols_btn)

        batch_buttons_layout.addStretch()
        symbols_layout.addLayout(batch_buttons_layout)

        # 代码输入框
        self.symbols_edit = QTextEdit()
        self.symbols_edit.setMaximumHeight(80)  # 恢复为80，批量输入更方便
        self.symbols_edit.setPlaceholderText("输入代码，多个代码用逗号或换行分隔，如：000001,600000")
        symbols_layout.addWidget(self.symbols_edit)

        content_layout.addWidget(symbols_group)

        # ==================== 第四部分：执行配置 ====================
        execution_group = QGroupBox("")
        execution_layout = QHBoxLayout(execution_group)

        # 左侧：资源配置
        resource_config = QGroupBox("💻 资源配置")
        resource_layout = QFormLayout(resource_config)

        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 10000)
        self.batch_size_spin.setValue(1000)
        self.batch_size_spin.setToolTip("每批处理的记录数")
        resource_layout.addRow("批量大小:", self.batch_size_spin)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 32)
        self.workers_spin.setValue(8)  # ✅ 优化：默认工作线程数从4增加到8，提升并行性能
        self.workers_spin.setToolTip("并行处理的线程数（建议8-16，可根据CPU核心数调整）")
        resource_layout.addRow("工作线程数:", self.workers_spin)

        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(512, 16384)
        self.memory_limit_spin.setValue(2048)
        self.memory_limit_spin.setSuffix("MB")
        self.memory_limit_spin.setToolTip("内存使用限制")
        resource_layout.addRow("内存限制:", self.memory_limit_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(60, 3600)
        self.timeout_spin.setValue(60)  # ✅ 优化：默认超时从300秒减少到60秒，快速失败避免长时间等待
        self.timeout_spin.setSuffix("秒")
        self.timeout_spin.setToolTip("单个请求超时时间（建议60-120秒，快速失败提升响应速度）")
        resource_layout.addRow("超时设置:", self.timeout_spin)

        execution_layout.addWidget(resource_config)

        # 右侧：错误处理配置
        error_config = QGroupBox("⚠️ 错误处理")
        error_layout = QFormLayout(error_config)
        error_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        error_layout.setHorizontalSpacing(10)

        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(3)
        self.retry_count_spin.setToolTip("失败重试次数")
        error_layout.addRow("重试次数:", self.retry_count_spin)

        self.error_strategy_combo = QComboBox()
        self.error_strategy_combo.addItems(["停止", "跳过", "重试"])
        self.error_strategy_combo.setCurrentText("跳过")
        self.error_strategy_combo.setToolTip("遇到错误时的处理策略")
        error_layout.addRow("错误处理:", self.error_strategy_combo)

        self.progress_interval_spin = QSpinBox()
        self.progress_interval_spin.setRange(1, 60)
        self.progress_interval_spin.setValue(5)
        self.progress_interval_spin.setSuffix("秒")
        self.progress_interval_spin.setToolTip("进度更新间隔")
        self.progress_interval_spin.setMinimumWidth(100)
        self.progress_interval_spin.setMaximumWidth(200)
        error_layout.addRow("进度间隔:", self.progress_interval_spin)

        execution_layout.addWidget(error_config)

        content_layout.addWidget(execution_group)

        # ==================== 第五部分：智能化功能与实时写入 ====================
        ai_features_group = QGroupBox("🤖 智能化功能")
        ai_layout = QVBoxLayout(ai_features_group)

        # 创建三列布局
        ai_row1 = QHBoxLayout()
        ai_row2 = QHBoxLayout()
        ai_row3 = QHBoxLayout()

        self.ai_optimization_cb = QCheckBox("启用AI参数优化")
        self.ai_optimization_cb.setChecked(True)
        self.ai_optimization_cb.setToolTip("使用机器学习算法优化执行参数")
        ai_row1.addWidget(self.ai_optimization_cb)

        self.auto_tuning_cb = QCheckBox("启用AutoTuner自动调优")
        self.auto_tuning_cb.setChecked(True)
        self.auto_tuning_cb.setToolTip("使用AutoTuner进行参数自动调优")
        ai_row1.addWidget(self.auto_tuning_cb)

        self.distributed_cb = QCheckBox("启用分布式执行")
        self.distributed_cb.setChecked(True)
        self.distributed_cb.setToolTip("大任务自动分布式执行")
        ai_row2.addWidget(self.distributed_cb)

        self.caching_cb = QCheckBox("启用智能缓存")
        self.caching_cb.setChecked(True)
        self.caching_cb.setToolTip("启用多级缓存加速")
        ai_row2.addWidget(self.caching_cb)

        self.quality_monitoring_cb = QCheckBox("启用数据质量监控")
        self.quality_monitoring_cb.setChecked(True)
        self.quality_monitoring_cb.setToolTip("实时监控数据质量")
        ai_row3.addWidget(self.quality_monitoring_cb)

        # 数据验证
        self.validate_data_cb = QCheckBox("启用数据验证")
        self.validate_data_cb.setChecked(True)
        self.validate_data_cb.setToolTip("导入前验证数据格式")
        ai_row3.addWidget(self.validate_data_cb)

        ai_layout.addLayout(ai_row1)
        ai_layout.addLayout(ai_row2)
        ai_layout.addLayout(ai_row3)

        # ==================== 实时写入配置（融入智能化功能组）====================
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        ai_layout.addWidget(separator)

        realtime_label = QLabel("⚡ 实时写入配置")
        realtime_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        ai_layout.addWidget(realtime_label)

        realtime_row = QHBoxLayout()

        # 启用性能监控
        self.enable_perf_monitor_cb = QCheckBox("性能监控")
        self.enable_perf_monitor_cb.setChecked(True)
        self.enable_perf_monitor_cb.setToolTip("启用性能监控，实时显示写入速度和资源使用情况")
        realtime_row.addWidget(self.enable_perf_monitor_cb)

        # 启用内存监控
        self.enable_memory_monitor_cb = QCheckBox("内存监控")
        self.enable_memory_monitor_cb.setChecked(True)
        self.enable_memory_monitor_cb.setToolTip("启用内存使用监控")
        realtime_row.addWidget(self.enable_memory_monitor_cb)

        ai_layout.addLayout(realtime_row)

        # 写入策略选择
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("写入策略:"))
        self.write_strategy_combo = QComboBox()
        self.write_strategy_combo.addItems(["禁用写入", "批量写入", "实时写入", "自适应"])
        self.write_strategy_combo.setCurrentText("禁用写入")
        self.write_strategy_combo.setToolTip("禁用写入：不执行数据写入\n批量写入：累积到批量大小后写入\n实时写入：单条数据立即写入\n自适应：根据系统负载自动选择")
        self.write_strategy_combo.currentTextChanged.connect(self.on_write_strategy_changed)
        strategy_layout.addWidget(self.write_strategy_combo)
        strategy_layout.addStretch()
        ai_layout.addLayout(strategy_layout)

        content_layout.addWidget(ai_features_group)

        # 设置内容widget到滚动区域
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # 添加验证和重置按钮
        button_layout = QHBoxLayout()

        self.validate_config_btn = QPushButton("✅ 验证配置")
        self.validate_config_btn.clicked.connect(self.validate_current_configuration)
        button_layout.addWidget(self.validate_config_btn)

        self.reset_config_btn = QPushButton("🔄 重置")
        self.reset_config_btn.clicked.connect(self.reset_configuration)
        button_layout.addWidget(self.reset_config_btn)

        main_layout.addLayout(button_layout)

        # 初始化批量按钮状态
        self._initialize_batch_buttons()

        return group

    def _create_integrated_basic_tab(self) -> QWidget:
        """创建整合的基本信息选项化"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 任务名称
        self.task_name_edit = QLineEdit()
        self.task_name_edit.setText(f"导入任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        layout.addRow("任务名称:", self.task_name_edit)

        # 任务描述
        self.task_desc_edit = QTextEdit()
        self.task_desc_edit.setMaximumHeight(60)
        self.task_desc_edit.setPlaceholderText("输入任务描述（可选）...")
        layout.addRow("任务描述:", self.task_desc_edit)

        # 资产类型
        from core.ui_asset_type_utils import get_asset_type_combo_items
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems(get_asset_type_combo_items())
        self.asset_type_combo.currentTextChanged.connect(self.on_asset_type_changed)
        layout.addRow("资产类型:", self.asset_type_combo)

        # 数据类型
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["K线数化", "分笔数据", "财务数据", "基本面数化"])
        layout.addRow("数据类型:", self.data_type_combo)

        # 数据频率
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["日线", "周线", "月线", "5分钟", "15分钟", "30分钟", "60分钟"])
        layout.addRow("⏱️ 数据频率:", self.frequency_combo)

        # 股票代码输入区域（整合批量选择功能化
        symbols_group = QGroupBox("🏷代码选择")
        symbols_layout = QVBoxLayout(symbols_group)

        # 批量选择按钮区域
        batch_buttons_layout = QHBoxLayout()

        # 批量选择按钮
        self.batch_select_btn = QPushButton("批量选择")
        self.batch_select_btn.clicked.connect(self.show_batch_selection_dialog)
        batch_buttons_layout.addWidget(self.batch_select_btn)

        # 快速选择按钮
        self.quick_select_btn = QPushButton("快速选择")
        self.quick_select_btn.clicked.connect(self.show_quick_selection_dialog)
        batch_buttons_layout.addWidget(self.quick_select_btn)

        # 清空按钮
        self.clear_symbols_btn = QPushButton("🗑清空")
        self.clear_symbols_btn.clicked.connect(lambda: self.symbols_edit.clear())
        batch_buttons_layout.addWidget(self.clear_symbols_btn)

        batch_buttons_layout.addStretch()
        symbols_layout.addLayout(batch_buttons_layout)

        # 代码输入化
        self.symbols_edit = QTextEdit()
        self.symbols_edit.setMaximumHeight(120)
        self.symbols_edit.setPlaceholderText("输入股票代码，每行一个，例如：\n000001（平安银行）\n000002（万科A）\n600000（浦发银行）\n\n或使用上方按钮批量选择")
        symbols_layout.addWidget(self.symbols_edit)

        layout.addRow(symbols_group)

        # 初始化按钮状化
        self._initialize_batch_buttons()

        return widget

    def _create_integrated_config_tab(self) -> QWidget:
        """创建整合的数据源与高级配置tab"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)

        # 内容widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # 第一部分：数据源配置
        datasource_group = QGroupBox("🔌 数据源配置")
        datasource_layout = QFormLayout(datasource_group)

        # 数据源选择 - 动态加载已注册的数据源插件
        self.data_source_combo = QComboBox()
        self._load_available_data_sources()
        datasource_layout.addRow("数据源:", self.data_source_combo)

        # 数据范围
        date_group = QGroupBox("📅 数据时间范围")
        date_layout = QFormLayout(date_group)

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-12))
        self.start_date.setCalendarPopup(True)
        date_layout.addRow("开始日期:", self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_layout.addRow("结束日期:", self.end_date)

        datasource_layout.addRow(date_group)
        content_layout.addWidget(datasource_group)

        # 第二部分：执行配置
        execution_group = QGroupBox("⚙️ 执行配置")
        execution_layout = QHBoxLayout(execution_group)

        # 左侧：资源配置
        resource_config = QGroupBox("💻 资源配置")
        resource_layout = QFormLayout(resource_config)

        # 批量大小
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 10000)
        self.batch_size_spin.setValue(1000)
        self.batch_size_spin.setToolTip("每批处理的记录数")
        resource_layout.addRow("批量大小:", self.batch_size_spin)

        # 工作线程数
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 32)
        self.workers_spin.setValue(8)  # ✅ 优化：默认工作线程数从4增加到8，提升并行性能
        self.workers_spin.setToolTip("并行处理的线程数（建议8-16，可根据CPU核心数调整）")
        resource_layout.addRow("工作线程数:", self.workers_spin)

        # 内存限制
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(512, 16384)
        self.memory_limit_spin.setValue(2048)
        self.memory_limit_spin.setSuffix("MB")
        self.memory_limit_spin.setToolTip("内存使用限制")
        resource_layout.addRow("内存限制:", self.memory_limit_spin)

        # 超时设置
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(60, 3600)
        self.timeout_spin.setValue(60)  # ✅ 优化：默认超时从300秒减少到60秒，快速失败避免长时间等待
        self.timeout_spin.setSuffix("秒")
        self.timeout_spin.setToolTip("单个请求超时时间（建议60-120秒，快速失败提升响应速度）")
        resource_layout.addRow("超时设置:", self.timeout_spin)

        execution_layout.addWidget(resource_config)

        # 右侧：错误处理配置
        error_config = QGroupBox("错误处理")
        error_layout = QFormLayout(error_config)

        # 重试次数
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(3)
        self.retry_count_spin.setToolTip("失败重试次数")
        error_layout.addRow("重试次数:", self.retry_count_spin)

        # 错误处理策略
        self.error_strategy_combo = QComboBox()
        self.error_strategy_combo.addItems(["停止", "跳过", "重试"])
        self.error_strategy_combo.setCurrentText("跳过")
        self.error_strategy_combo.setToolTip("遇到错误时的处理策略")
        error_layout.addRow("错误处理:", self.error_strategy_combo)

        execution_layout.addWidget(error_config)
        content_layout.addWidget(execution_group)

        # 第三部分：智能化功能
        ai_features_group = QGroupBox("智能化功能")
        ai_layout = QVBoxLayout(ai_features_group)

        # 创建两列布局
        ai_row1 = QHBoxLayout()
        ai_row2 = QHBoxLayout()
        ai_row3 = QHBoxLayout()

        # AI优化开关
        self.ai_optimization_cb = QCheckBox("启用AI参数优化")
        self.ai_optimization_cb.setChecked(True)
        self.ai_optimization_cb.setToolTip("使用机器学习算法优化执行参数")
        ai_row1.addWidget(self.ai_optimization_cb)

        # 自动调优开关
        self.auto_tuning_cb = QCheckBox("启用AutoTuner自动调优")
        self.auto_tuning_cb.setChecked(True)
        self.auto_tuning_cb.setToolTip("使用AutoTuner进行参数自动调优")
        ai_row1.addWidget(self.auto_tuning_cb)

        # 分布式执行开关
        self.distributed_cb = QCheckBox("启用分布式执行")
        self.distributed_cb.setChecked(True)
        self.distributed_cb.setToolTip("大任务自动分布式执行")
        ai_row2.addWidget(self.distributed_cb)

        # 智能缓存开关
        self.caching_cb = QCheckBox("启用智能缓存")
        self.caching_cb.setChecked(True)
        self.caching_cb.setToolTip("启用多级缓存加速")
        ai_row2.addWidget(self.caching_cb)

        # 数据质量监控开关
        self.quality_monitoring_cb = QCheckBox("启用数据质量监控")
        self.quality_monitoring_cb.setChecked(True)
        self.quality_monitoring_cb.setToolTip("实时监控数据质量")
        ai_row3.addWidget(self.quality_monitoring_cb)

        # 数据验证开关
        self.validate_data_cb = QCheckBox("启用数据验证")
        self.validate_data_cb.setChecked(True)
        self.validate_data_cb.setToolTip("导入前验证数据格式")
        ai_row3.addWidget(self.validate_data_cb)

        ai_layout.addLayout(ai_row1)
        ai_layout.addLayout(ai_row2)
        ai_layout.addLayout(ai_row3)

        content_layout.addWidget(ai_features_group)

        main_layout.addWidget(content_widget)

        return widget

    def _create_integrated_datasource_tab(self) -> QWidget:
        """创建整合的数据源配置选项化"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 数据源选择 - 动态加载已注册的数据源插件
        self.data_source_combo = QComboBox()
        self._load_available_data_sources()
        layout.addRow("🔌 数据源:", self.data_source_combo)

        # 数据范围
        date_group = QGroupBox("📅 数据时间范围")
        date_layout = QFormLayout(date_group)

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-6))
        self.start_date.setCalendarPopup(True)
        date_layout.addRow("开始日期:", self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_layout.addRow("结束日期:", self.end_date)

        layout.addRow(date_group)

        return widget

    def _create_integrated_advanced_tab(self) -> QWidget:
        """创建整合的高级配置选项化"""
        widget = QWidget()
        main_layout = QHBoxLayout(widget)

        # 左侧：资源额度配置
        left_panel = self._create_resource_quota_panel()
        main_layout.addWidget(left_panel, 1)

        # 右侧：执行配置
        right_panel = self._create_execution_config_panel()
        main_layout.addWidget(right_panel, 1)

        return widget

    def create_task_operations_group(self) -> QGroupBox:
        """创建任务操作组（融入实时写入控制）"""
        group = QGroupBox("任务操作")
        group.setFont(QFont("Arial", 10, QFont.Bold))
        layout = QVBoxLayout(group)

        # 新建任务按钮
        self.new_task_btn = QPushButton("新建任务")
        self.new_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.new_task_btn.clicked.connect(self.create_new_task_from_config)
        layout.addWidget(self.new_task_btn)

        # 初始化当前任务ID（用于跟踪下载任务）
        if REALTIME_WRITE_UI_AVAILABLE:
            self.current_task_id = None

        # 添加提示文本
        hint_label = QLabel("[INFO] 提示：任务的启动/停止可通过右侧任务列表的右键菜单操作")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(hint_label)

        return group

    def create_right_panel(self) -> QWidget:
        """创建右侧监控面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建选项卡
        self.monitor_tabs = QTabWidget()

        # 任务管理选项卡（集成增强功能）
        task_management_tab = self.create_enhanced_task_management_tab()
        self.monitor_tabs.addTab(task_management_tab, "任务管理")

        # 增量更新历史选项卡
        history_tab = self.create_incremental_update_history_tab()
        self.monitor_tabs.addTab(history_tab, "更新历史")

        # AI功能控制面板选项卡
        ai_control_tab = self.create_ai_control_panel_tab()
        self.monitor_tabs.addTab(ai_control_tab, "AI控制面板")

        # 分布式状态选项卡
        distributed_tab = self.create_distributed_status_tab()
        self.monitor_tabs.addTab(distributed_tab, "分布式状态")

        # 数据质量选项卡
        quality_tab = self.create_quality_status_tab()
        self.monitor_tabs.addTab(quality_tab, "数据质量")

        # 新增：数据状态显示选项卡
        data_status_tab = self.create_data_status_tab()
        self.monitor_tabs.addTab(data_status_tab, "数据状态")

        layout.addWidget(self.monitor_tabs)

        return widget

    def create_incremental_update_history_tab(self) -> QWidget:
        """创建增量更新历史选项卡"""
        try:
            # 导入UpdateHistoryWidget
            from gui.widgets.incremental_update_history_widget import UpdateHistoryWidget

            # 创建历史组件
            history_widget = UpdateHistoryWidget()

            # 保存引用以便后续使用
            self.incremental_update_history = history_widget

            # 如果有导入引擎，连接信号
            if self.import_engine:
                try:
                    self.import_engine.task_completed.connect(
                        lambda task_id, result: self._on_task_completed_update_history(task_id, result)
                    )
                except Exception as e:
                    logger.warning(f"连接导入引擎信号失败: {e}") if logger else None

            return history_widget

        except ImportError as e:
            logger.warning(f"UpdateHistoryWidget导入失败: {e}") if logger else None
            return self._create_basic_history_tab()

    def _create_basic_history_tab(self) -> QWidget:
        """创建基础历史选项卡（回退版本）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 提示信息
        info_label = QLabel("增量更新历史")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(info_label)

        # 历史显示区域
        history_text = QTextEdit()
        history_text.setPlainText("增量更新历史组件暂不可用，请检查相关依赖")
        history_text.setReadOnly(True)
        layout.addWidget(history_text)

        return widget

    def _on_task_completed_update_history(self, task_id: str, result: object):
        """当任务完成时更新历史记录"""
        try:
            if hasattr(self, 'incremental_update_history'):
                # 刷新历史组件数据
                self.incremental_update_history.refresh_history()
                logger.info(f"已更新增量更新历史记录") if logger else None
        except Exception as e:
            logger.warning(f"更新历史记录失败: {e}") if logger else None

    def create_enhanced_task_management_tab(self) -> QWidget:
        """创建增强任务管理选项化"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建选项化
        task_tabs = QTabWidget()

        # 任务列表和控制
        task_list_tab = self.create_task_management_tab()
        task_tabs.addTab(task_list_tab, "任务列表")

        # 任务依赖可视化
        dependency_tab = self.create_task_dependency_tab()
        task_tabs.addTab(dependency_tab, "依赖关系")

        # 任务调度控制器
        scheduler_tab = self.create_task_scheduler_tab()
        task_tabs.addTab(scheduler_tab, "调度控制")

        layout.addWidget(task_tabs)
        return widget

    def create_task_dependency_tab(self) -> QWidget:
        """创建任务依赖关系选项化"""
        try:
            # 尝试导入任务依赖可视化器
            from gui.widgets.task_dependency_visualizer import TaskDependencyVisualizer

            # 创建依赖可视化器
            dependency_visualizer = TaskDependencyVisualizer(ui_adapter=self.ui_adapter)

            # 保存引用以便后续使用
            self.task_dependency_visualizer = dependency_visualizer

            return dependency_visualizer

        except ImportError as e:
            logger.warning(f"任务依赖可视化器导入失败: {e}") if logger else None
            return self._create_basic_dependency_tab()

    def _create_basic_dependency_tab(self) -> QWidget:
        """创建基础依赖关系选项卡（回退版本化"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 提示信息
        info_label = QLabel("任务依赖关系可视化")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(info_label)

        # 依赖关系显示区域
        dependency_text = QTextEdit()
        dependency_text.setPlainText("依赖关系可视化功能暂不可用，请检查相关组件化")
        dependency_text.setReadOnly(True)
        layout.addWidget(dependency_text)

        return widget

    def create_task_scheduler_tab(self) -> QWidget:
        """创建任务调度控制器选项卡"""
        try:
            # 尝试导入任务调度控制器器
            from gui.widgets.task_scheduler_control import TaskSchedulerControl

            # 创建调度控制器器
            scheduler_control = TaskSchedulerControl(ui_adapter=self.ui_adapter)

            # 保存引用以便后续使用
            self.task_scheduler_control = scheduler_control

            return scheduler_control

        except ImportError as e:
            logger.warning(f"任务调度控制器器导入失化 {e}") if logger else None
            return self._create_basic_scheduler_tab()

    def _create_basic_scheduler_tab(self) -> QWidget:
        """创建基础调度控制选项卡（回退版本化"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 提示信息
        info_label = QLabel("化任务调度控制器")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(info_label)

        # 调度控制显示区域
        scheduler_text = QTextEdit()
        scheduler_text.setPlainText("任务调度控制器功能暂不可用，请检查相关组件化")
        scheduler_text.setReadOnly(True)
        layout.addWidget(scheduler_text)

        return widget

    def create_ai_control_panel_tab(self) -> QWidget:
        """创建AI功能控制面板选项卡"""
        try:
            # 尝试导入AI功能控制面板
            from gui.widgets.ai_features_control_panel import AIFeaturesControlPanel

            # 创建AI控制面板
            ai_control_panel = AIFeaturesControlPanel(ui_adapter=self.ui_adapter)

            # 保存引用以便后续使用
            self.ai_features_control_panel = ai_control_panel

            return ai_control_panel

        except ImportError as e:
            logger.warning(f"AI功能控制面板导入失败: {e}") if logger else None
            return self._create_basic_ai_control_tab()

    def _create_basic_ai_control_tab(self) -> QWidget:
        """创建基础AI控制选项卡（回退版本化"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 提示信息
        info_label = QLabel("AI功能控制面板")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(info_label)

        # AI控制显示区域
        ai_control_text = QTextEdit()
        ai_control_text.setPlainText("AI功能控制面板暂不可用，请检查相关组件化")
        ai_control_text.setReadOnly(True)
        layout.addWidget(ai_control_text)

        return widget

    def create_ai_status_tab(self) -> QWidget:
        """创建AI状态选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # AI优化统计
        ai_group = QGroupBox("AI优化统计")
        ai_layout = QGridLayout(ai_group)

        ai_layout.addWidget(QLabel("预测次数:"), 0, 0)
        self.predictions_count_label = QLabel("0")
        ai_layout.addWidget(self.predictions_count_label, 0, 1)

        ai_layout.addWidget(QLabel("节省时间:"), 1, 0)
        self.time_saved_label = QLabel("0")
        ai_layout.addWidget(self.time_saved_label, 1, 1)

        ai_layout.addWidget(QLabel("准确性"), 2, 0)
        self.accuracy_label = QLabel("0")
        ai_layout.addWidget(self.accuracy_label, 2, 1)

        layout.addWidget(ai_group)

        # AutoTuner状态
        tuner_group = QGroupBox("AutoTuner状态")
        tuner_layout = QGridLayout(tuner_group)

        tuner_layout.addWidget(QLabel("活跃任务:"), 0, 0)
        self.active_tuning_label = QLabel("0")
        tuner_layout.addWidget(self.active_tuning_label, 0, 1)

        tuner_layout.addWidget(QLabel("完成任务:"), 1, 0)
        self.completed_tuning_label = QLabel("0")
        tuner_layout.addWidget(self.completed_tuning_label, 1, 1)

        tuner_layout.addWidget(QLabel("总体改进:"), 2, 0)
        self.total_improvement_label = QLabel("0")
        tuner_layout.addWidget(self.total_improvement_label, 2, 1)

        layout.addWidget(tuner_group)

        layout.addStretch()
        return widget

    def create_distributed_status_tab(self) -> QWidget:
        """创建分布式状态选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 节点状态化
        nodes_group = QGroupBox("节点状态化")
        nodes_layout = QGridLayout(nodes_group)

        nodes_layout.addWidget(QLabel("发现节点:"), 0, 0)
        self.discovered_nodes_label = QLabel("0")
        nodes_layout.addWidget(self.discovered_nodes_label, 0, 1)

        nodes_layout.addWidget(QLabel("可用节点:"), 1, 0)
        self.available_nodes_label = QLabel("0")
        nodes_layout.addWidget(self.available_nodes_label, 1, 1)

        nodes_layout.addWidget(QLabel("分布式任"), 2, 0)
        self.distributed_tasks_label = QLabel("0")
        nodes_layout.addWidget(self.distributed_tasks_label, 2, 1)

        layout.addWidget(nodes_group)

        # 节点列表
        nodes_list_group = QGroupBox("节点列表")
        nodes_list_layout = QVBoxLayout(nodes_list_group)

        self.nodes_table = QTableWidget()
        self.nodes_table.setColumnCount(4)
        self.nodes_table.setHorizontalHeaderLabels(["节点ID", "地址", "任务", "状"])
        self.nodes_table.horizontalHeader().setStretchLastSection(True)
        nodes_list_layout.addWidget(self.nodes_table)

        layout.addWidget(nodes_list_group)

        return widget

    def create_quality_status_tab(self) -> QWidget:
        """创建增强的数据质量控制中心"""
        try:
            # 尝试导入数据质量控制中心心
            from gui.widgets.data_quality_control_center import DataQualityControlCenter

            # 创建数据质量控制中心心
            quality_center = DataQualityControlCenter()

            # 保存引用以便后续使用
            self.data_quality_control_center = quality_center

            logger.info("成功加载数据质量控制中心") if logger else None
            return quality_center

        except ImportError as e:
            logger.warning(f"无法加载数据质量控制中心，使用基础版本: {e}") if logger else None

            # 回退到基础版本
            return self._create_basic_quality_tab()

    def _create_basic_quality_tab(self) -> QWidget:
        """创建基础数据质量选项卡（回退版本）化"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 质量指标
        quality_group = QGroupBox("质量指标")
        quality_layout = QGridLayout(quality_group)

        quality_layout.addWidget(QLabel("整体评分:"), 0, 0)
        self.overall_quality_label = QLabel("0.0")
        quality_layout.addWidget(self.overall_quality_label, 0, 1)

        quality_layout.addWidget(QLabel("完整性化"), 1, 0)
        self.completeness_label = QLabel("0")
        quality_layout.addWidget(self.completeness_label, 1, 1)

        quality_layout.addWidget(QLabel("准确性化"), 2, 0)
        self.accuracy_quality_label = QLabel("0")
        quality_layout.addWidget(self.accuracy_quality_label, 2, 1)

        quality_layout.addWidget(QLabel("一致性化"), 3, 0)
        self.consistency_label = QLabel("0")
        quality_layout.addWidget(self.consistency_label, 3, 1)

        layout.addWidget(quality_group)

        # 质量问题
        issues_group = QGroupBox("质量问题")
        issues_layout = QVBoxLayout(issues_group)

        self.quality_issues_text = QTextEdit()
        self.quality_issues_text.setMaximumHeight(150)
        self.quality_issues_text.setReadOnly(True)
        issues_layout.addWidget(self.quality_issues_text)

        layout.addWidget(issues_group)

        return widget

    def setup_connections(self):
        """设置信号连接"""
        if not CORE_AVAILABLE:
            return

        # 按钮连接已移至任务操作组

        # 引擎信号连接
        if self.import_engine:
            self.import_engine.task_started.connect(self.on_task_started)
            self.import_engine.task_progress.connect(self.on_task_progress)
            self.import_engine.task_completed.connect(self.on_task_completed)
            self.import_engine.task_failed.connect(self.on_task_failed)

        # UI适配器信号连化
        if self.ui_adapter:
            self.ui_adapter.task_status_updated.connect(self.on_adapter_task_updated)
            self.ui_adapter.ai_status_updated.connect(self.on_adapter_ai_updated)
            self.ui_adapter.performance_updated.connect(self.on_adapter_performance_updated)
            self.ui_adapter.quality_updated.connect(self.on_adapter_quality_updated)
            self.ui_adapter.service_status_changed.connect(self.on_service_status_changed)
            self.ui_adapter.error_occurred.connect(self.on_adapter_error)

        # UI同步器信号连化
        if self.ui_synchronizer:
            self.ui_synchronizer.state_changed.connect(self.on_state_changed)
            self.ui_synchronizer.conflict_detected.connect(self.on_conflict_detected)
            self.ui_synchronizer.sync_completed.connect(self.on_sync_completed)
            self.ui_synchronizer.sync_failed.connect(self.on_sync_failed)

    def setup_responsive_layout(self):
        """设置响应式布局"""
        try:
            # 创建响应式配化
            responsive_config = ResponsiveConfig(
                adaptive_spacing=True,
                adaptive_fonts=True,
                touch_optimization=True,
                animation_enabled=True
            )

            # 应用响应式行为
            self.responsive_manager = apply_responsive_behavior(self, **responsive_config.__dict__)

            # 连接响应式事件
            self.responsive_manager.screen_size_changed.connect(self._on_screen_size_changed)
            self.responsive_manager.orientation_changed.connect(self._on_orientation_changed)
            self.responsive_manager.layout_changed.connect(self._on_layout_changed)

            # 设置组件响应式规则
            self._setup_component_responsive_rules()

            logger.info("响应式布局已设置")

        except Exception as e:
            logger.error(f"设置响应式布局失败: {e}")
            self.responsive_manager = None

    def create_data_status_tab(self) -> QWidget:
        """创建数据状态显示选项卡 - 支持多资产类型"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 资产类型选择
        asset_type_layout = QHBoxLayout()
        asset_type_layout.addWidget(QLabel("选择资产类型:"))
        self.status_asset_type_combo = QComboBox()
        from core.ui_asset_type_utils import get_asset_type_combo_items
        self.status_asset_type_combo.addItems(get_asset_type_combo_items())
        self.status_asset_type_combo.currentTextChanged.connect(self._on_status_asset_type_changed)
        asset_type_layout.addWidget(self.status_asset_type_combo)
        asset_type_layout.addStretch()
        layout.addLayout(asset_type_layout)

        # 数据状态总览
        overview_group = QGroupBox("数据状态总览")
        overview_layout = QGridLayout(overview_group)

        overview_layout.addWidget(QLabel("资产总数:"), 0, 0)
        self.total_stocks_label = QLabel("0")
        overview_layout.addWidget(self.total_stocks_label, 0, 1)

        overview_layout.addWidget(QLabel("已下载:"), 1, 0)
        self.downloaded_stocks_label = QLabel("0")
        overview_layout.addWidget(self.downloaded_stocks_label, 1, 1)

        overview_layout.addWidget(QLabel("待更新:"), 2, 0)
        self.pending_update_label = QLabel("0")
        overview_layout.addWidget(self.pending_update_label, 2, 1)

        overview_layout.addWidget(QLabel("有数据缺口:"), 3, 0)
        self.data_gaps_label = QLabel("0")
        overview_layout.addWidget(self.data_gaps_label, 3, 1)

        layout.addWidget(overview_group)

        # 增量下载配置
        incremental_group = QGroupBox("增量下载配置")
        incremental_layout = QFormLayout(incremental_group)

        # 增量下载模式
        self.incremental_mode_combo = QComboBox()
        self.incremental_mode_combo.addItems([
            "最新数据",  # LATEST_ONLY
            "缺失数据",  # MISSING_ONLY
            "间隙填充",  # GAP_FILL
            "智能补全"   # SMART_FILL
        ])
        self.incremental_mode_combo.setToolTip("选择增量下载策略")
        incremental_layout.addRow("下载模式:", self.incremental_mode_combo)

        # 回溯天数
        self.lookback_days_spin = QSpinBox()
        self.lookback_days_spin.setRange(1, 365)
        self.lookback_days_spin.setValue(7)
        self.lookback_days_spin.setToolTip("回溯的天数（仅最新数据模式有效）")
        incremental_layout.addRow("回溯天数:", self.lookback_days_spin)

        # 最小记录数阈值
        self.min_records_spin = QSpinBox()
        self.min_records_spin.setRange(1, 1000)
        self.min_records_spin.setValue(10)
        self.min_records_spin.setToolTip("最少记录数，低于此数量则跳过下载")
        incremental_layout.addRow("最小记录数:", self.min_records_spin)

        layout.addWidget(incremental_group)

        # 数据状态详情
        details_group = QGroupBox("数据状态详情")
        details_layout = QVBoxLayout(details_group)

        # 创建表格
        self.data_status_table = QTableWidget()
        self.data_status_table.setColumnCount(7)
        self.data_status_table.setHorizontalHeaderLabels([
            "代码", "名称", "最新日期", "完整性", "状态", "缺口数", "操作"
        ])

        # 设置列宽
        self.data_status_table.setColumnWidth(0, 80)   # 代码
        self.data_status_table.setColumnWidth(1, 120)  # 名称
        self.data_status_table.setColumnWidth(2, 120)  # 最新日期
        self.data_status_table.setColumnWidth(3, 80)   # 完整性
        self.data_status_table.setColumnWidth(4, 80)   # 状态
        self.data_status_table.setColumnWidth(5, 60)   # 缺口数
        self.data_status_table.setColumnWidth(6, 100)  # 操作

        # 设置表头不可编辑
        self.data_status_table.horizontalHeader().setStretchLastSection(True)

        details_layout.addWidget(self.data_status_table)

        layout.addWidget(details_group)

        # 控制按钮
        control_group = QGroupBox("数据状态操作")
        control_layout = QHBoxLayout(control_group)

        self.refresh_status_btn = QPushButton("刷新状态")
        self.refresh_status_btn.clicked.connect(self.refresh_data_status)
        control_layout.addWidget(self.refresh_status_btn)

        self.analyze_gaps_btn = QPushButton("分析缺口")
        self.analyze_gaps_btn.clicked.connect(self.analyze_data_gaps)
        control_layout.addWidget(self.analyze_gaps_btn)

        self.fix_gaps_btn = QPushButton("修复缺口")
        self.fix_gaps_btn.clicked.connect(self.fix_data_gaps)
        control_layout.addWidget(self.fix_gaps_btn)

        layout.addWidget(control_group)

        # 状态信息
        self.data_status_info = QTextEdit()
        self.data_status_info.setMaximumHeight(150)
        self.data_status_info.setReadOnly(True)
        layout.addWidget(self.data_status_info)

        layout.addStretch()
        return widget

    def _on_status_asset_type_changed(self, asset_type: str):
        """数据状态页面的资产类型变化事件"""
        try:
            logger.info(f"数据状态页面资产类型已切换至: {asset_type}")
            # 清空表格
            self.data_status_table.setRowCount(0)
            # 重置统计标签
            self.total_stocks_label.setText("0")
            self.downloaded_stocks_label.setText("0")
            self.pending_update_label.setText("0")
            self.data_gaps_label.setText("0")
            self.data_status_info.clear()
            self.data_status_info.append(f'已切换至 {asset_type}，请点击"刷新状态"按钮查看数据')
        except Exception as e:
            logger.error(f"资产类型切换失败: {e}")

    def refresh_data_status(self):
        """刷新数据状态 - 支持所有资产类型"""
        try:
            self.data_status_info.clear()
            self.data_status_info.append("正在刷新数据状态...")

            # 获取当前选择的资产类型
            asset_type = self.status_asset_type_combo.currentText() if hasattr(self, 'status_asset_type_combo') else "股票"

            # 获取该资产类型的所有符号
            symbols = self.get_all_symbols(asset_type)
            if not symbols:
                self.data_status_info.append(f"未找到 {asset_type} 数据")
                return

            self.total_stocks_label.setText(str(len(symbols)))

            # 初始化计数器
            downloaded_count = 0
            pending_count = 0
            gaps_count = 0

            # 清空表格
            self.data_status_table.setRowCount(0)

            # 获取当前日期
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            # 获取UnifiedDataManager用于查询数据
            from core.services.unified_data_manager import get_unified_data_manager
            data_manager = get_unified_data_manager()

            if not data_manager:
                self.data_status_info.append("错误: 无法获取数据管理器")
                return

            # 检查每个符号的状态
            for symbol in symbols[:100]:  # 限制前100个避免界面卡顿
                try:
                    # 方案1: 尝试直接从DuckDB查询获取最新日期和数据完整性
                    latest_date = self._get_latest_date_from_db(symbol, asset_type)

                    # 计算数据完整性和状态
                    completeness_percentage = self._calculate_completeness(symbol, asset_type, start_date, end_date)

                    # 确定状态
                    if latest_date is None:
                        status = "未下载"
                        pending_count += 1
                    elif (end_date - latest_date).days > 7:
                        status = "需更新"
                        pending_count += 1
                    elif completeness_percentage < 95:
                        status = "有缺口"
                        gaps_count += 1
                        pending_count += 1
                    else:
                        status = "正常"
                        downloaded_count += 1

                    # 添加到表格
                    row = self.data_status_table.rowCount()
                    self.data_status_table.insertRow(row)

                    self.data_status_table.setItem(row, 0, QTableWidgetItem(symbol))
                    self.data_status_table.setItem(row, 1, QTableWidgetItem(""))  # 名称待填充

                    # 格式化最新日期
                    latest_date_str = latest_date.strftime("%Y-%m-%d") if latest_date else "无"
                    self.data_status_table.setItem(row, 2, QTableWidgetItem(latest_date_str))

                    # 完整性百分比
                    completeness_str = f"{completeness_percentage:.1f}%"
                    self.data_status_table.setItem(row, 3, QTableWidgetItem(completeness_str))

                    # 状态
                    status_item = QTableWidgetItem(status)
                    # 根据状态设置颜色
                    if status == "正常":
                        status_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                    elif status == "需更新":
                        status_item.setBackground(QColor(255, 255, 144))  # 浅黄色
                    elif status == "有缺口":
                        status_item.setBackground(QColor(255, 144, 144))  # 浅红色
                    else:
                        status_item.setBackground(QColor(200, 200, 200))  # 浅灰色

                    self.data_status_table.setItem(row, 4, status_item)

                    # 缺口数 (简化计算)
                    missing_count = max(0, int(30 * (1 - completeness_percentage / 100)))
                    self.data_status_table.setItem(row, 5, QTableWidgetItem(str(missing_count)))

                    # 操作按钮
                    action_widget = QWidget()
                    action_layout = QHBoxLayout(action_widget)
                    action_layout.setContentsMargins(2, 2, 2, 2)

                    details_btn = QPushButton("详情")
                    details_btn.setMaximumWidth(40)
                    details_btn.clicked.connect(lambda checked, s=symbol: self.show_symbol_details(s))

                    update_btn = QPushButton("更新")
                    update_btn.setMaximumWidth(40)
                    update_btn.clicked.connect(lambda checked, s=symbol: self.update_single_symbol(s))

                    action_layout.addWidget(details_btn)
                    action_layout.addWidget(update_btn)
                    action_layout.addStretch()

                    self.data_status_table.setCellWidget(row, 6, action_widget)

                except Exception as e:
                    logger.warning(f"检查 {symbol} 状态失败: {e}")
                    continue

            # 更新统计标签
            self.downloaded_stocks_label.setText(str(downloaded_count))
            self.pending_update_label.setText(str(pending_count))
            self.data_gaps_label.setText(str(gaps_count))

            self.data_status_info.append(f"状态刷新完成！共检查 {len(symbols[:100])} 个资产")
            self.data_status_info.append(f"正常: {downloaded_count}, 需更新: {pending_count}, 有缺口: {gaps_count}")

        except Exception as e:
            logger.error(f"刷新数据状态失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.data_status_info.append(f"刷新失败: {str(e)}")

    def _get_latest_date_from_db(self, symbol: str, asset_type: str) -> Optional:
        """
        从数据库获取符号的最新日期

        Args:
            symbol: 资产符号
            asset_type: 资产类型（UI显示名称）

        Returns:
            最新日期或None
        """
        try:
            # 资产类型映射到表名
            table_mappings = {
                "股票": "daily_kline_data",
                "指数": "index_kline_data",
                "期货": "futures_kline_data",
                "基金": "fund_kline_data",
                "债券": "bond_kline_data",
                "加密货币": "crypto_kline_data",
                "外汇": "forex_kline_data"
            }

            table_name = table_mappings.get(asset_type, "daily_kline_data")

            # 直接SQL查询获取最新日期
            from core.database.duckdb_manager import get_connection_manager
            conn_manager = get_connection_manager()

            if conn_manager:
                conn = conn_manager.get_connection()
                try:
                    result = conn.execute(
                        f"SELECT MAX(datetime) as latest_date FROM {table_name} WHERE symbol = '{symbol}'"
                    ).fetchall()

                    if result and result[0][0]:
                        from datetime import datetime
                        date_str = result[0][0]
                        # 处理可能的日期格式
                        if isinstance(date_str, str):
                            return datetime.fromisoformat(date_str)
                        else:
                            return date_str
                    return None
                except Exception as e:
                    logger.debug(f"从{table_name}查询{symbol}最新日期失败: {e}")
                    return None
            return None

        except Exception as e:
            logger.debug(f"获取{symbol}最新日期异常: {e}")
            return None

    def _calculate_completeness(self, symbol: str, asset_type: str, start_date, end_date) -> float:
        """
        计算数据完整性百分比

        Args:
            symbol: 资产符号
            asset_type: 资产类型
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            完整性百分比 (0-100)
        """
        try:
            table_mappings = {
                "股票": "daily_kline_data",
                "指数": "index_kline_data",
                "期货": "futures_kline_data",
                "基金": "fund_kline_data",
                "债券": "bond_kline_data",
                "加密货币": "crypto_kline_data",
                "外汇": "forex_kline_data"
            }

            table_name = table_mappings.get(asset_type, "daily_kline_data")

            from core.database.duckdb_manager import get_connection_manager
            conn_manager = get_connection_manager()

            if conn_manager:
                conn = conn_manager.get_connection()
                try:
                    # 计算指定日期范围内的数据记录数
                    result = conn.execute(f"""
                        SELECT COUNT(*) as count FROM {table_name}
                        WHERE symbol = '{symbol}'
                        AND datetime >= '{start_date.strftime('%Y-%m-%d')}'
                        AND datetime <= '{end_date.strftime('%Y-%m-%d')}'
                    """).fetchall()

                    if result:
                        actual_records = result[0][0]
                        # 估算的交易天数 (假设每个月20个交易日)
                        days_diff = (end_date - start_date).days
                        expected_records = max(1, int(days_diff * 0.67))  # 约67%的天数是交易日

                        completeness = min(100, (actual_records / expected_records) * 100) if expected_records > 0 else 0
                        return completeness
                    return 0
                except Exception as e:
                    logger.debug(f"计算{symbol}完整性失败: {e}")
                    return 0
            return 0

        except Exception as e:
            logger.debug(f"计算完整性异常: {e}")
            return 0

    def get_all_symbols(self, asset_type: str = "股票") -> List[str]:
        """
        获取指定资产类型的所有符号

        支持多种资产类型：股票、指数、期货、基金、债券、加密货币等
        从UnifiedDataManager获取符号列表，支持多种数据源。

        Args:
            asset_type: 资产类型，默认为"股票"

        Returns:
            所有符号的列表，如果获取失败则返回空列表
        """
        try:
            # 资产类型映射
            asset_type_mapping = {
                "股票": "stock",
                "指数": "index",
                "期货": "futures",
                "基金": "fund",
                "债券": "bond",
                "加密货币": "crypto",
                "外汇": "forex"
            }

            asset_type_value = asset_type_mapping.get(asset_type, "stock")

            # 方案1: 优先从UnifiedDataManager获取
            from core.services.unified_data_manager import get_unified_data_manager
            data_manager = get_unified_data_manager()

            if data_manager:
                try:
                    # 获取资产列表（包含所有市场）
                    asset_df = data_manager.get_asset_list(asset_type=asset_type_value, market='all')
                    if asset_df is not None and not asset_df.empty:
                        # 提取symbol或code列
                        if 'code' in asset_df.columns:
                            symbols = asset_df['code'].tolist()
                        elif 'symbol' in asset_df.columns:
                            symbols = asset_df['symbol'].tolist()
                        else:
                            logger.warning(f"数据框中找不到code或symbol列: {asset_df.columns.tolist()}")
                            return []

                        logger.info(f"✅ 成功获取 {len(symbols)} 个{asset_type}符号")
                        return symbols
                except Exception as e:
                    logger.warning(f"从UnifiedDataManager获取{asset_type}列表失败: {e}")

            # 方案2: 备用方案 - 直接从DuckDB查询
            try:
                from core.database.duckdb_manager import get_connection_manager
                conn_manager = get_connection_manager()

                if conn_manager:
                    conn = conn_manager.get_connection()

                    # 尝试从asset_metadata表查询
                    try:
                        # 资产类型在数据库中的表示形式
                        asset_type_db_mapping = {
                            "stock": "stock_a",
                            "index": "index",
                            "futures": "futures",
                            "fund": "fund",
                            "bond": "bond",
                            "crypto": "crypto",
                            "forex": "forex"
                        }
                        asset_type_db_value = asset_type_db_mapping.get(asset_type_value, "stock_a")

                        query = f"""
                        SELECT DISTINCT symbol FROM asset_metadata
                        WHERE asset_type = '{asset_type_db_value}'
                        ORDER BY symbol
                        """
                        result = conn.execute(query).fetchall()

                        if result:
                            symbols = [row[0] for row in result]
                            logger.info(f"✅ 从数据库成功获取 {len(symbols)} 个{asset_type}符号")
                            return symbols
                    except Exception as e:
                        logger.debug(f"从asset_metadata查询失败: {e}")

                    # 尝试从各类型数据表查询（备用方案）
                    table_mappings = {
                        "stock": "daily_kline_data",
                        "index": "index_kline_data",
                        "futures": "futures_kline_data",
                        "fund": "fund_kline_data",
                        "bond": "bond_kline_data",
                        "crypto": "crypto_kline_data",
                        "forex": "forex_kline_data"
                    }

                    table_name = table_mappings.get(asset_type_value, "daily_kline_data")

                    try:
                        result = conn.execute(
                            f"SELECT DISTINCT symbol FROM {table_name} ORDER BY symbol LIMIT 10000"
                        ).fetchall()

                        if result:
                            symbols = [row[0] for row in result]
                            logger.info(f"✅ 从 {table_name} 表成功获取 {len(symbols)} 个{asset_type}符号")
                            return symbols
                    except Exception as e:
                        logger.debug(f"从{table_name}查询失败: {e}")

            except Exception as e:
                logger.warning(f"从数据库获取{asset_type}列表失败: {e}")

            # 如果所有方案都失败，返回空列表
            logger.error(f"无法获取 {asset_type} 符号，请检查数据库配置和数据源")
            return []

        except Exception as e:
            logger.error(f"get_all_symbols执行异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _ensure_db_manager(self) -> bool:
        """
        确保db_manager已初始化

        Returns:
            是否成功初始化db_manager
        """
        if self.db_manager:
            return True

        try:
            from core.database.duckdb_manager import get_connection_manager
            self.db_manager = get_connection_manager()
            if self.db_manager:
                logger.info("✅ db_manager初始化成功")
                return True
            else:
                logger.error("❌ db_manager初始化失败: get_connection_manager返回None")
                return False
        except Exception as e:
            logger.error(f"❌ db_manager初始化异常: {e}")
            return False

    def analyze_data_gaps(self):
        """分析数据缺口"""
        try:
            self.data_status_info.clear()
            self.data_status_info.append("开始分析数据缺口...")

            # 获取需要分析的资产
            symbols = []
            for row in range(self.data_status_table.rowCount()):
                status_item = self.data_status_table.item(row, 4)
                if status_item and status_item.text() in ["需更新", "有缺口"]:
                    symbol = self.data_status_table.item(row, 0).text()
                    symbols.append(symbol)

            if not symbols:
                self.data_status_info.append("没有需要分析缺口的资产")
                return

            # 获取当前选择的资产类型
            asset_type = self.status_asset_type_combo.currentText() if hasattr(self, 'status_asset_type_combo') else "股票"

            # 获取当前日期
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)

            # 分析缺口
            gap_count = 0
            for symbol in symbols:
                try:
                    completeness = self._calculate_completeness(symbol, asset_type, start_date, end_date)
                    if completeness < 95:
                        gap_count += 1
                        self.data_status_info.append(f"{symbol}: 完整性 {completeness:.1f}%")
                except Exception as e:
                    logger.debug(f"分析{symbol}缺口失败: {e}")

            self.data_status_info.append(f"\n分析完成：共发现 {gap_count} 个资产存在数据缺口")

        except Exception as e:
            logger.error(f"分析数据缺口失败: {e}")
            self.data_status_info.append(f"分析失败: {str(e)}")

    def fix_data_gaps(self):
        """修复数据缺口"""
        try:
            self.data_status_info.clear()
            self.data_status_info.append("开始修复数据缺口...")

            # 获取需要修复的股票
            symbols_to_fix = []
            for row in range(self.data_status_table.rowCount()):
                status_item = self.data_status_table.item(row, 4)
                if status_item and status_item.text() == "有缺口":
                    symbol = self.data_status_table.item(row, 0).text()
                    symbols_to_fix.append(symbol)

            if not symbols_to_fix:
                self.data_status_info.append("没有需要修复缺口的股票")
                return

            self.data_status_info.append(f"准备修复 {len(symbols_to_fix)} 只股票的数据缺口...")

            # 创建增量下载器并设置间隙填充模式
            from datetime import datetime
            from core.services.incremental_data_analyzer import DownloadStrategy

            if hasattr(self, 'download_service'):
                # 设置间隙填充策略
                self.download_service.set_download_strategy(DownloadStrategy.GAP_FILL)

                # 开始下载
                future = asyncio.get_event_loop().run_until_complete(
                    self.download_service.download_incremental_data(
                        symbols=symbols_to_fix,
                        end_date=datetime.now(),
                        strategy=DownloadStrategy.GAP_FILL,
                        skip_weekends=True,
                        skip_holidays=True
                    )
                )

                self.data_status_info.append("缺口修复任务已启动，请查看进度监控标签页")
            else:
                self.data_status_info.append("下载服务未初始化，无法修复缺口")

        except Exception as e:
            logger.error(f"修复数据缺口失败: {e}")
            self.data_status_info.append(f"修复失败: {str(e)}")

    def show_symbol_details(self, symbol: str):
        """显示资产详情"""
        try:
            from datetime import datetime, timedelta

            # 获取当前选择的资产类型
            asset_type = self.status_asset_type_combo.currentText() if hasattr(self, 'status_asset_type_combo') else "股票"

            # 获取当前日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            # 获取最新日期
            latest_date = self._get_latest_date_from_db(symbol, asset_type)

            # 计算完整性
            completeness = self._calculate_completeness(symbol, asset_type, start_date, end_date)

            # 显示详情
            details = f"\n资产 {symbol} 数据详情:\n"
            details += f"资产类型: {asset_type}\n"
            details += f"最新日期: {latest_date.strftime('%Y-%m-%d') if latest_date else '无'}\n"
            details += f"完整性: {completeness:.1f}%\n"
            details += f"查询区间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}\n"

            self.data_status_info.append(details)

        except Exception as e:
            logger.error(f"显示{symbol}详情失败: {e}")
            self.data_status_info.append(f"详情获取失败: {str(e)}")

    def update_single_symbol(self, symbol: str):
        """更新单个股票"""
        try:
            from datetime import datetime
            from core.services.incremental_data_analyzer import DownloadStrategy

            if hasattr(self, 'download_service'):
                # 设置最新数据策略
                self.download_service.set_download_strategy(DownloadStrategy.LATEST_ONLY)

                # 开始下载
                future = asyncio.get_event_loop().run_until_complete(
                    self.download_service.download_incremental_data(
                        symbols=[symbol],
                        end_date=datetime.now(),
                        strategy=DownloadStrategy.LATEST_ONLY,
                        skip_weekends=True,
                        skip_holidays=True
                    )
                )

                self.data_status_info.append(f"已启动 {symbol} 的增量更新任务")
            else:
                self.data_status_info.append("下载服务未初始化，无法更新股票")

        except Exception as e:
            logger.error(f"更新股票失败: {e}")
            self.data_status_info.append(f"更新失败: {str(e)}")

    def create_detailed_progress_display(self):
        """创建详细进度显示"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 进度总览
        overview_group = QGroupBox("任务总览")
        overview_layout = QGridLayout(overview_group)

        overview_layout.addWidget(QLabel("任务ID:"), 0, 0)
        self.task_id_label = QLabel("无")
        overview_layout.addWidget(self.task_id_label, 0, 1)

        overview_layout.addWidget(QLabel("任务名称:"), 1, 0)
        self.task_name_label = QLabel("无")
        overview_layout.addWidget(self.task_name_label, 1, 1)

        overview_layout.addWidget(QLabel("开始时间:"), 2, 0)
        self.start_time_label = QLabel("无")
        overview_layout.addWidget(self.start_time_label, 2, 1)

        overview_layout.addWidget(QLabel("运行时间:"), 3, 0)
        self.elapsed_time_label = QLabel("00:00:00")
        overview_layout.addWidget(self.elapsed_time_label, 3, 1)

        layout.addWidget(overview_group)

        # 进度条和统计
        progress_group = QGroupBox("下载进度")
        progress_layout = QVBoxLayout(progress_group)

        # 总进度条
        progress_layout.addWidget(QLabel("总体进度:"))
        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setRange(0, 100)
        self.total_progress_bar.setValue(0)
        progress_layout.addWidget(self.total_progress_bar)

        # 详细统计
        stats_layout = QHBoxLayout()

        # 左侧统计
        left_stats = QVBoxLayout()
        left_stats.addWidget(QLabel("成功:"))
        self.success_count_label = QLabel("0")
        left_stats.addWidget(self.success_count_label)

        left_stats.addWidget(QLabel("失败:"))
        self.failed_count_label = QLabel("0")
        left_stats.addWidget(self.failed_count_label)

        left_stats.addWidget(QLabel("跳过:"))
        self.skipped_count_label = QLabel("0")
        left_stats.addWidget(self.skipped_count_label)

        progress_layout.addLayout(left_stats)

        # 右侧统计
        right_stats = QVBoxLayout()
        right_stats.addWidget(QLabel("总记录:"))
        self.total_records_label = QLabel("0")
        right_stats.addWidget(self.total_records_label)

        right_stats.addWidget(QLabel("当前批次:"))
        self.current_batch_label = QLabel("0/0")
        right_stats.addWidget(self.current_batch_label)

        right_stats.addWidget(QLabel("速度:"))
        self.speed_label = QLabel("0 记录/秒")
        right_stats.addWidget(self.speed_label)

        progress_layout.addLayout(right_stats)

        layout.addWidget(progress_group)

        # 实时日志
        log_group = QGroupBox("实时日志")
        log_layout = QVBoxLayout(log_group)

        self.progress_log = QTextEdit()
        self.progress_log.setMaximumHeight(200)
        self.progress_log.setReadOnly(True)
        log_layout.addWidget(self.progress_log)

        layout.addWidget(log_group)

        # 控制按钮
        control_group = QGroupBox("任务控制")
        control_layout = QHBoxLayout(control_group)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.toggle_pause_task)
        self.pause_btn.setEnabled(False)
        control_layout.addWidget(self.pause_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_task)
        self.cancel_btn.setEnabled(False)
        control_layout.addWidget(self.cancel_btn)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_progress_display)
        control_layout.addWidget(self.reset_btn)

        layout.addWidget(control_group)

        # 符号详情表格
        details_group = QGroupBox("符号下载详情")
        details_layout = QVBoxLayout(details_group)

        self.symbol_progress_table = QTableWidget()
        self.symbol_progress_table.setColumnCount(6)
        self.symbol_progress_table.setHorizontalHeaderLabels([
            "代码", "状态", "已下载", "总记录", "进度", "错误"
        ])

        # 设置列宽
        self.symbol_progress_table.setColumnWidth(0, 80)   # 代码
        self.symbol_progress_table.setColumnWidth(1, 80)   # 状态
        self.symbol_progress_table.setColumnWidth(2, 80)   # 已下载
        self.symbol_progress_table.setColumnWidth(3, 80)   # 总记录
        self.symbol_progress_table.setColumnWidth(4, 100)  # 进度
        self.symbol_progress_table.setColumnWidth(5, 200)  # 错误

        details_layout.addWidget(self.symbol_progress_table)
        layout.addWidget(details_group)

        return widget

    def toggle_pause_task(self):
        """切换任务暂停状态"""
        try:
            if hasattr(self, 'current_task_id'):
                # 实现暂停/恢复逻辑
                self.progress_log.append("暂停/恢复功能待实现")
            else:
                self.progress_log.append("没有运行中的任务")
        except Exception as e:
            logger.error(f"切换任务状态失败: {e}")
            self.progress_log.append(f"操作失败: {str(e)}")

    def cancel_task(self):
        """取消当前任务"""
        try:
            if hasattr(self, 'current_task_id'):
                # 实现取消逻辑
                self.progress_log.append("取消功能待实现")
            else:
                self.progress_log.append("没有运行中的任务")
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            self.progress_log.append(f"操作失败: {str(e)}")

    def reset_progress_display(self):
        """重置进度显示"""
        self.task_id_label.setText("无")
        self.task_name_label.setText("无")
        self.start_time_label.setText("无")
        self.elapsed_time_label.setText("00:00:00")

        self.total_progress_bar.setValue(0)
        self.success_count_label.setText("0")
        self.failed_count_label.setText("0")
        self.skipped_count_label.setText("0")
        self.total_records_label.setText("0")
        self.current_batch_label.setText("0/0")
        self.speed_label.setText("0 记录/秒")

        self.progress_log.clear()
        self.symbol_progress_table.setRowCount(0)

        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        if hasattr(self, 'current_task_id'):
            delattr(self, 'current_task_id')

    def update_task_progress(self, task_id: str, progress: float, success_count: int,
                             failed_count: int, skipped_count: int, total_records: int,
                             batch_info: str = "", errors: dict = None):
        """更新任务进度"""
        try:
            # 保存任务ID
            self.current_task_id = task_id

            # 更新基本进度信息
            self.total_progress_bar.setValue(int(progress))
            self.success_count_label.setText(str(success_count))
            self.failed_count_label.setText(str(failed_count))
            self.skipped_count_label.setText(str(skipped_count))
            self.total_records_label.setText(str(total_records))

            if batch_info:
                self.current_batch_label.setText(batch_info)

            # 更新运行时间
            if hasattr(self, 'start_time'):
                elapsed = datetime.now() - self.start_time
                self.elapsed_time_label.setText(str(elapsed).split('.')[0])

                # 计算速度
                if elapsed.total_seconds() > 0 and total_records > 0:
                    speed = total_records / elapsed.total_seconds()
                    self.speed_label.setText(f"{speed:.1f} 记录/秒")

            # 更新日志
            self.progress_log.append(f"进度更新: {progress:.1f}% | 成功: {success_count} | 失败: {failed_count}")

            # 更新符号详情表格
            if errors:
                for symbol, error in errors.items():
                    self.add_symbol_progress_row(symbol, "失败", 0, 0, 0, error)
            elif hasattr(self, 'last_updated_symbols'):
                for symbol in self.last_updated_symbols:
                    self.add_symbol_progress_row(symbol, "成功", 1, 1, 100, "")

        except Exception as e:
            logger.error(f"更新任务进度失败: {e}")

    def add_symbol_progress_row(self, symbol: str, status: str, downloaded: int,
                                total: int, progress: int, error: str):
        """添加符号进度行"""
        try:
            row = self.symbol_progress_table.rowCount()

            # 检查是否已存在该符号的行
            existing_row = -1
            for i in range(self.symbol_progress_table.rowCount()):
                if self.symbol_progress_table.item(i, 0).text() == symbol:
                    existing_row = i
                    break

            if existing_row >= 0:
                # 更新现有行
                row = existing_row
            else:
                # 插入新行
                self.symbol_progress_table.insertRow(row)

            # 设置单元格内容
            self.symbol_progress_table.setItem(row, 0, QTableWidgetItem(symbol))

            status_item = QTableWidgetItem(status)
            # 根据状态设置颜色
            if status == "成功":
                status_item.setBackground(QColor(144, 238, 144))  # 浅绿色
            elif status == "失败":
                status_item.setBackground(QColor(255, 144, 144))  # 浅红色
            else:
                status_item.setBackground(QColor(255, 255, 144))  # 浅黄色

            self.symbol_progress_table.setItem(row, 1, status_item)
            self.symbol_progress_table.setItem(row, 2, QTableWidgetItem(str(downloaded)))
            self.symbol_progress_table.setItem(row, 3, QTableWidgetItem(str(total)))

            progress_item = QTableWidgetItem(f"{progress}%")
            self.symbol_progress_table.setItem(row, 4, progress_item)

            error_item = QTableWidgetItem(error)
            self.symbol_progress_table.setItem(row, 5, error_item)

        except Exception as e:
            logger.error(f"添加符号进度行失败: {e}")

    def start_detailed_progress_monitoring(self, task_name: str):
        """开始详细进度监控"""
        try:
            import time

            # 记录开始时间
            self.start_time = datetime.now()

            # 设置任务信息
            self.task_name_label.setText(task_name)
            self.task_id_label.setText(f"TASK_{int(time.time())}")
            self.start_time_label.setText(self.start_time.strftime("%Y-%m-%d %H:%M:%S"))

            # 启用控制按钮
            self.pause_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)

            # 清空日志
            self.progress_log.clear()
            self.progress_log.append(f"任务 '{task_name}' 开始执行...")

            # 开始监控循环（在实际实现中，这应该通过事件或定时器实现）
            self.monitor_task_progress()

        except Exception as e:
            logger.error(f"开始进度监控失败: {e}")
            self.progress_log.append(f"启动失败: {str(e)}")

    def monitor_task_progress(self):
        """监控任务进度（模拟实现）"""
        try:
            # 这里应该是实际的任务进度监控逻辑
            # 可以通过定时器或事件监听来实现

            # 模拟进度更新
            if hasattr(self, 'current_task_id'):
                # 在实际实现中，这里应该从IncrementalUpdateRecorder获取真实进度
                self.progress_log.append("监控任务进度...")

                # 可以设置定时器定期调用此方法
            else:
                # 任务已结束，停止监控
                self.progress_log.append("任务结束")

        except Exception as e:
            logger.error(f"监控任务进度失败: {e}")

    def _setup_component_responsive_rules(self):
        """设置组件响应式规化"""
        try:
            if not hasattr(self, 'responsive_manager') or not self.responsive_manager:
                return

            # 为不同屏幕尺寸设置组件规化

            # 监控标签页的响应式规化
            if hasattr(self, 'monitor_tabs'):
                monitor_rules = {
                    ScreenSize.EXTRA_SMALL: {
                        'visible': True,
                        'collapsed': False,
                        'width': 300,
                        'height': 400},
                    ScreenSize.SMALL: {
                        'visible': True,
                        'collapsed': False,
                        'width': 400,
                        'height': 500},
                    ScreenSize.MEDIUM: {
                        'visible': True,
                        'collapsed': False,
                        'width': 600,
                        'height': 600},
                    ScreenSize.LARGE: {
                        'visible': True,
                        'collapsed': False,
                        'width': 800,
                        'height': 700},
                    ScreenSize.EXTRA_LARGE: {
                        'visible': True,
                        'collapsed': False,
                        'width': 1000,
                        'height': 800}
                }
                self.responsive_manager.set_component_responsive_rules('monitor_tabs', monitor_rules)

            # 配置面板的响应式规则
            config_rules = {
                ScreenSize.EXTRA_SMALL: {
                    'visible': True,
                    'width': 280,
                    'height': 300},
                ScreenSize.SMALL: {
                    'visible': True,
                    'width': 350,
                    'height': 400},
                ScreenSize.MEDIUM: {
                    'visible': True,
                    'width': 400,
                    'height': 500},
                ScreenSize.LARGE: {
                    'visible': True,
                    'width': 450,
                    'height': 600},
                ScreenSize.EXTRA_LARGE: {
                    'visible': True,
                    'width': 500,
                    'height': 700}
            }

            # 应用到配置相关组化
            for component_name in ['task_config_group', 'control_buttons']:
                if hasattr(self, component_name):
                    self.responsive_manager.set_component_responsive_rules(component_name, config_rules)

        except Exception as e:
            logger.error(f"设置组件响应式规则失化 {e}")

    def _on_screen_size_changed(self, screen_size: str):
        """屏幕尺寸变化处理"""
        try:
            logger.debug(f"屏幕尺寸变化: {screen_size}")

            # 根据屏幕尺寸调整UI
            if screen_size in ['xs', 'sm']:
                self._apply_compact_layout()
            elif screen_size in ['md']:
                self._apply_normal_layout()
            else:  # lg, xl
                self._apply_expanded_layout()

        except Exception as e:
            logger.error(f"处理屏幕尺寸变化失败: {e}")

    def _on_orientation_changed(self, orientation: str):
        """屏幕方向变化处理"""
        try:
            logger.debug(f"屏幕方向变化: {orientation}")

            # 根据方向调整布局
            if orientation == 'portrait':
                self._apply_portrait_layout()
            else:  # landscape
                self._apply_landscape_layout()

        except Exception as e:
            logger.error(f"处理屏幕方向变化失败: {e}")

    def _on_layout_changed(self, layout_params: dict):
        """布局变化处理"""
        try:
            logger.debug(f"布局变化: {layout_params.get('layout_mode', 'unknown')}")

            # 更新组件可见性和布局
            self._update_component_visibility(layout_params)

        except Exception as e:
            logger.error(f"处理布局变化失败: {e}")

    def _apply_compact_layout(self):
        """应用紧凑布局"""
        try:
            # 隐藏或折叠非关键组件
            if hasattr(self, 'monitor_tabs'):
                # 在小屏幕上只显示关键标签化
                for i in range(self.monitor_tabs.count()):
                    tab_text = self.monitor_tabs.tabText(i)
                    # 只保留进度和日志标签化
                    if tab_text not in ['进度监控', '执行日志']:
                        self.monitor_tabs.setTabVisible(i, False)
                    else:
                        self.monitor_tabs.setTabVisible(i, True)

            # 按钮布局调整已不需要（按钮已移除）

        except Exception as e:
            logger.error(f"应用紧凑布局失败: {e}")

    def _apply_normal_layout(self):
        """应用正常布局"""
        try:
            # 显示大部分组化
            if hasattr(self, 'monitor_tabs'):
                for i in range(self.monitor_tabs.count()):
                    tab_text = self.monitor_tabs.tabText(i)
                    # 隐藏高级功能标签化
                    if tab_text in ['分布式监化', '高级监控']:
                        self.monitor_tabs.setTabVisible(i, False)
                    else:
                        self.monitor_tabs.setTabVisible(i, True)

            # 恢复按钮水平布局
            # 按钮布局调整已不需要（按钮已移除）

        except Exception as e:
            logger.error(f"应用正常布局失败: {e}")

    def _apply_expanded_layout(self):
        """应用扩展布局"""
        try:
            # 显示所有组件
            if hasattr(self, 'monitor_tabs'):
                for i in range(self.monitor_tabs.count()):
                    self.monitor_tabs.setTabVisible(i, True)

            # 使用水平布局
            # 按钮布局调整已不需要（按钮已移除）

        except Exception as e:
            logger.error(f"应用扩展布局失败: {e}")

    def _apply_portrait_layout(self):
        """应用竖屏布局"""
        try:
            # 调整为垂直堆叠布局
            if hasattr(self, 'main_splitter'):
                self.main_splitter.setOrientation(Qt.Vertical)

        except Exception as e:
            logger.error(f"应用竖屏布局失败: {e}")

    def _apply_landscape_layout(self):
        """应用横屏布局"""
        try:
            # 调整为水平分割布局
            if hasattr(self, 'main_splitter'):
                self.main_splitter.setOrientation(Qt.Horizontal)

        except Exception as e:
            logger.error(f"应用横屏布局失败: {e}")

    def _update_component_visibility(self, layout_params: dict):
        """更新组件可见性"""
        try:
            components = layout_params.get('components', {})

            for component_id, component_layout in components.items():
                visible = component_layout.get('visible', True)

                # 根据组件ID找到对应的组件并设置可见性
                if hasattr(self, component_id):
                    component = getattr(self, component_id)
                    if hasattr(component, 'setVisible'):
                        component.setVisible(visible)

        except Exception as e:
            logger.error(f"更新组件可见性失败: {e}")

    def _arrange_buttons_vertically(self):
        """垂直排列按钮"""
        try:
            # 这里可以实现按钮的垂直排列逻辑
            pass
        except Exception as e:
            logger.error(f"垂直排列按钮失败: {e}")

    def _arrange_buttons_horizontally(self):
        """水平排列按钮"""
        try:
            # 这里可以实现按钮的水平排列逻辑
            pass
        except Exception as e:
            logger.error(f"水平排列按钮失败: {e}")

    def setup_timers(self):
        """设置定时器"""
        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # 2秒更新一次

        # 任务列表刷新定时器
        self.task_refresh_timer = QTimer()
        self.task_refresh_timer.timeout.connect(self.refresh_task_list)
        self.task_refresh_timer.start(5000)  # 5秒刷新一次任务列表

        # ✅ 数据库写入队列监控定时器（新增）
        self.queue_monitor_timer = QTimer()
        self.queue_monitor_timer.timeout.connect(self.update_queue_stats)
        # 延迟启动，避免UI刚打开时立即执行耗时操作
        self._queue_monitor_initialized = False
        self._queue_monitor_start_time = None
        self.queue_monitor_timer.start(1000)  # 1秒更新一次队列统计

        # IP监控更新计数器，用于降低更新频率
        self._ip_monitor_update_counter = 0
        self._ip_monitor_update_interval = 3  # 每3秒更新一次IP监控（降低频率）
        # ✅ 修复：初始化IP监控缓存相关变量
        self._ip_stats_cache = None
        self._ip_stats_cache_time = 0  # 初始化为0，确保第一次会触发更新
        self._ip_stats_cache_ttl = 5.0  # 缓存有效期5秒
        self._ip_stats_thread = None
        self._ip_stats_worker = None

    def update_queue_stats(self):
        """
        更新数据库写入队列统计（新增方法）

        定时从执行引擎获取队列统计信息并更新到监控面板
        """
        try:
            # 延迟初始化：UI刚打开时等待3秒再开始更新，避免卡顿
            if not self._queue_monitor_initialized:
                if self._queue_monitor_start_time is None:
                    self._queue_monitor_start_time = time.time()
                    logger.debug("队列监控: 开始延迟初始化计时")
                    return
                elif time.time() - self._queue_monitor_start_time < 3.0:
                    # 等待3秒后再开始更新
                    return
                else:
                    self._queue_monitor_initialized = True
                    logger.debug("队列监控: 延迟初始化完成，开始正常更新")

            # 检查引擎和监控面板是否可用
            if not hasattr(self, 'import_engine') or not self.import_engine:
                return
            if not hasattr(self, 'download_monitoring') or not self.download_monitoring:
                return

            # 从引擎获取统计信息
            queue_stats = self.import_engine.get_database_writer_stats()

            # 更新到监控面板
            self.download_monitoring.update_queue_stats(queue_stats)

            # ✅ 更新IP监控信息（使用后台线程，避免阻塞UI）
            if hasattr(self, 'ip_monitor') and self.ip_monitor is not None:
                self._ip_monitor_update_counter += 1
                # 每3秒更新一次IP监控（降低频率）
                if self._ip_monitor_update_counter >= self._ip_monitor_update_interval:
                    self._ip_monitor_update_counter = 0
                    # ✅ 修复：检查缓存是否已初始化
                    if not hasattr(self, '_ip_stats_cache_time') or self._ip_stats_cache_time == 0:
                        # 缓存未初始化，直接获取新数据
                        self._update_ip_stats_in_background()
                    else:
                        # 检查缓存是否有效
                        current_time = time.time()
                        if current_time - self._ip_stats_cache_time < self._ip_stats_cache_ttl:
                            # 使用缓存数据
                            if self._ip_stats_cache:
                                self.ip_monitor.update_ip_stats(self._ip_stats_cache)
                        else:
                            # 缓存过期，使用后台线程获取新数据
                            self._update_ip_stats_in_background()

            # ✅ 更新数据源实例池状态（RealDataProvider）
            try:
                from core.real_data_provider import get_real_data_provider
                provider = get_real_data_provider()
                pool_stats = provider.get_pool_status()
                if hasattr(self, 'download_monitoring') and hasattr(self.download_monitoring, 'update_instance_pool_stats'):
                    self.download_monitoring.update_instance_pool_stats(pool_stats)
            except Exception:
                pass

            # ✅ 新增：更新数据库连接池使用统计
            try:
                from core.asset_database_manager import AssetSeparatedDatabaseManager
                manager = AssetSeparatedDatabaseManager.get_instance()
                if hasattr(manager, 'get_database_pool_status'):
                    db_pool_status = manager.get_database_pool_status()
                    if hasattr(self, 'download_monitoring') and hasattr(self.download_monitoring, 'db_pool_usage_label'):
                        active_connections = db_pool_status.get('active_connections', 0)
                        total_connections = db_pool_status.get('total_connections', 0)
                        max_pool_size = db_pool_status.get('max_pool_size', manager.config.pool_size if hasattr(manager, 'config') else 10)

                        # ✅ 修复：使用实际创建的连接数（total_connections）而不是最大池大小作为分母
                        # 如果total_connections为0，则使用max_pool_size（连接池还未创建任何连接）
                        denominator = total_connections if total_connections > 0 else max_pool_size
                        usage_text = f"{active_connections}/{denominator}"
                        if total_connections > 0:
                            usage_text += f" (最大:{max_pool_size})"
                        self.download_monitoring.db_pool_usage_label.setText(usage_text)

                        # 根据使用率调整颜色
                        if denominator > 0:
                            usage_rate = active_connections / denominator
                            if usage_rate > 0.8:
                                self.download_monitoring.db_pool_usage_label.setStyleSheet("color: red; font-weight: bold;")
                            elif usage_rate > 0.5:
                                self.download_monitoring.db_pool_usage_label.setStyleSheet("color: orange;")
                            else:
                                self.download_monitoring.db_pool_usage_label.setStyleSheet("color: green;")
            except Exception as e:
                logger.debug(f"更新数据库连接池使用统计失败: {e}")
                pass  # 静默失败

        except Exception as e:
            # 静默错误，避免过多日志
            pass

    def _update_ip_stats_in_background(self):
        """
        在后台线程更新IP监控信息（真正异步，避免阻塞UI线程）
        """
        try:
            if not hasattr(self, 'import_engine') or not self.import_engine:
                return
            if not hasattr(self, 'ip_monitor') or self.ip_monitor is None:
                return

            # ✅ 修复：安全检查线程状态，避免访问已删除的对象
            if self._ip_stats_thread is not None:
                try:
                    if self._ip_stats_thread.isRunning():
                        return  # 线程正在运行，跳过本次更新
                except RuntimeError:
                    # QThread对象已被删除，清空引用
                    logger.debug("IP监控: QThread对象已被删除，清空引用")
                    self._ip_stats_thread = None
                    self._ip_stats_worker = None

            # 创建后台线程和工作对象
            self._ip_stats_thread = QThread()
            self._ip_stats_worker = IPStatsWorker(self.import_engine)
            self._ip_stats_worker.moveToThread(self._ip_stats_thread)

            # 连接信号
            self._ip_stats_thread.started.connect(self._ip_stats_worker.fetch_ip_stats)
            self._ip_stats_worker.finished.connect(self._on_ip_stats_received)
            self._ip_stats_worker.finished.connect(self._ip_stats_thread.quit)
            self._ip_stats_worker.error.connect(self._on_ip_stats_error)
            self._ip_stats_worker.error.connect(self._ip_stats_thread.quit)
            # ✅ 修复：线程完成后清空引用，避免访问已删除的对象
            self._ip_stats_thread.finished.connect(self._on_ip_stats_thread_finished)

            # 启动线程
            self._ip_stats_thread.start()

        except Exception as e:
            logger.error(f"启动IP监控后台线程失败: {e}", exc_info=True)
            # 即使失败也更新UI，显示错误状态
            if hasattr(self, 'ip_monitor') and self.ip_monitor is not None:
                self.ip_monitor.update_ip_stats({
                    'total_connections': 0,
                    'active_servers': 0,
                    'healthy_ips': 0,
                    'limited_ips': 0,
                    'failed_ips': 0,
                    'ip_stats': [],
                    'error_message': f'更新失败: {str(e)}'
                })

    def _on_ip_stats_received(self, ip_stats: dict):
        """IP统计信息接收回调（在主线程执行）"""
        try:
            # 更新缓存
            self._ip_stats_cache = ip_stats
            self._ip_stats_cache_time = time.time()

            # 更新UI
            if hasattr(self, 'ip_monitor') and self.ip_monitor is not None:
                if ip_stats:
                    self.ip_monitor.update_ip_stats(ip_stats)
                else:
                    logger.debug("IP监控: 获取到的IP统计为空")
                    # 显示空状态
                    self.ip_monitor.update_ip_stats({
                        'total_connections': 0,
                        'active_servers': 0,
                        'healthy_ips': 0,
                        'limited_ips': 0,
                        'failed_ips': 0,
                        'ip_stats': [],
                        'error_message': '数据为空'
                    })
        except Exception as e:
            logger.error(f"处理IP统计信息失败: {e}", exc_info=True)

    def _on_ip_stats_error(self, error_msg: str):
        """IP统计信息错误回调（在主线程执行）"""
        try:
            logger.error(f"IP监控: {error_msg}")
            # 即使失败也更新UI，显示错误状态
            if hasattr(self, 'ip_monitor') and self.ip_monitor is not None:
                self.ip_monitor.update_ip_stats({
                    'total_connections': 0,
                    'active_servers': 0,
                    'healthy_ips': 0,
                    'limited_ips': 0,
                    'failed_ips': 0,
                    'ip_stats': [],
                    'error_message': f'更新失败: {error_msg}'
                })
        except Exception as e:
            logger.error(f"处理IP统计错误失败: {e}", exc_info=True)

    def _on_ip_stats_thread_finished(self):
        """IP统计线程完成回调（在主线程执行）- 线程完成后的清理工作"""
        try:
            # ✅ 修复：清空引用，避免访问已删除的对象
            if self._ip_stats_thread:
                self._ip_stats_thread.deleteLater()
                self._ip_stats_thread = None
            if self._ip_stats_worker:
                self._ip_stats_worker = None
            logger.debug("IP监控: 线程清理完成")
        except Exception as e:
            logger.debug(f"IP监控: 线程清理失败: {e}")

    def start_import(self):
        """开始导入"""
        if not CORE_AVAILABLE or not self.import_engine:
            QMessageBox.warning(self, "错误", "核心组件不可用")
            return

        try:
            # 获取配置
            task_name = self.task_name_edit.text() or f"导入任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            symbols_text = self.symbols_edit.toPlainText().strip()

            if not symbols_text:
                QMessageBox.warning(self, "警告", "请输入股票代码")
                return

            symbols = [s.strip() for s in symbols_text.split('\n') if s.strip()]

            # 获取当前选择的下载模式
            download_mode = getattr(self, 'current_download_mode', 'full')

            # 创建基础配置
            freq_map = {
                "日线": DataFrequency.DAILY,
                "周线": DataFrequency.WEEKLY,
                "月线": DataFrequency.MONTHLY,
                "5分钟": DataFrequency.MINUTE_5,
                "15分钟": DataFrequency.MINUTE_15,
                "30分钟": DataFrequency.MINUTE_30,
                "60分钟": DataFrequency.HOUR_1
            }

            # 获取复选框状态
            check_completeness = self.check_completeness_cb.isChecked() if hasattr(self, 'check_completeness_cb') else True
            skip_latest_data = self.skip_latest_data_cb.isChecked() if hasattr(self, 'skip_latest_data_cb') else True

            # 根据下载模式创建不同的任务配置
            if download_mode == "gap_fill":
                # 间隙填充模式配置
                gap_threshold = self.gap_threshold_spin.value() if hasattr(self, 'gap_threshold_spin') else 30

                task_config = ImportTaskConfig(
                    task_id=f"task_{int(datetime.now().timestamp())}",
                    name=task_name,
                    symbols=symbols,
                    data_source=self.data_source_combo.currentText(),
                    asset_type=self._get_asset_type_value(),
                    data_type=self.data_type_combo.currentText() if hasattr(self, 'data_type_combo') else "K线数据",
                    frequency=freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY),
                    mode=ImportMode.MANUAL,  # 使用MANUAL模式，通过config区分功能
                    batch_size=self.batch_size_spin.value(),
                    max_workers=self.workers_spin.value(),
                    start_date=self.start_date.date().toString("yyyy-MM-dd"),
                    end_date=self.end_date.date().toString("yyyy-MM-dd"),
                    retry_count=self.retry_count_spin.value() if hasattr(self, 'retry_count_spin') else 3,
                    error_strategy=self.error_strategy_combo.currentText() if hasattr(self, 'error_strategy_combo') else "跳过",
                    memory_limit=self.memory_limit_spin.value() if hasattr(self, 'memory_limit_spin') else 2048,
                    timeout=self.timeout_spin.value() if hasattr(self, 'timeout_spin') else 60,
                    progress_interval=self.progress_interval_spin.value() if hasattr(self, 'progress_interval_spin') else 5,
                    validate_data=self.validate_data_cb.isChecked() if hasattr(self, 'validate_data_cb') else True,
                    # 间隙填充专用配置
                    gap_fill_mode=True,
                    gap_threshold_days=gap_threshold,
                    gap_fill_threshold=gap_threshold,
                    auto_fill_gaps=True,
                    skip_weekends=True,
                    skip_holidays=True,
                    # 复选框配置
                    check_completeness=check_completeness,
                    skip_latest_data=skip_latest_data
                )

            elif download_mode == "smart_fill":
                # 智能补全模式配置
                strategy = self.completion_strategy_combo.currentText() if hasattr(self, 'completion_strategy_combo') else "全部补全"

                task_config = ImportTaskConfig(
                    task_id=f"task_{int(datetime.now().timestamp())}",
                    name=task_name,
                    symbols=symbols,
                    data_source=self.data_source_combo.currentText(),
                    asset_type=self._get_asset_type_value(),
                    data_type=self.data_type_combo.currentText() if hasattr(self, 'data_type_combo') else "K线数据",
                    frequency=freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY),
                    mode=ImportMode.MANUAL,  # 使用MANUAL模式，通过config区分功能
                    batch_size=self.batch_size_spin.value(),
                    max_workers=self.workers_spin.value(),
                    start_date=self.start_date.date().toString("yyyy-MM-dd"),
                    end_date=self.end_date.date().toString("yyyy-MM-dd"),
                    retry_count=self.retry_count_spin.value() if hasattr(self, 'retry_count_spin') else 3,
                    error_strategy=self.error_strategy_combo.currentText() if hasattr(self, 'error_strategy_combo') else "跳过",
                    memory_limit=self.memory_limit_spin.value() if hasattr(self, 'memory_limit_spin') else 2048,
                    timeout=self.timeout_spin.value() if hasattr(self, 'timeout_spin') else 60,
                    progress_interval=self.progress_interval_spin.value() if hasattr(self, 'progress_interval_spin') else 5,
                    validate_data=self.validate_data_cb.isChecked() if hasattr(self, 'validate_data_cb') else True,
                    # 智能补全专用配置
                    smart_fill_mode=True,
                    completion_strategy=strategy,
                    recent_days_only=30,
                    auto_fill_gaps=True,
                    skip_weekends=True,
                    skip_holidays=True,
                    # 复选框配置
                    check_completeness=check_completeness,
                    skip_latest_data=skip_latest_data
                )

            elif download_mode == "incremental":
                # 增量下载模式配置
                incremental_days = self.incremental_days_spin.value() if hasattr(self, 'incremental_days_spin') else 7

                task_config = ImportTaskConfig(
                    task_id=f"task_{int(datetime.now().timestamp())}",
                    name=task_name,
                    symbols=symbols,
                    data_source=self.data_source_combo.currentText(),
                    asset_type=self._get_asset_type_value(),
                    data_type=self.data_type_combo.currentText() if hasattr(self, 'data_type_combo') else "K线数据",
                    frequency=freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY),
                    mode=ImportMode.INCREMENTAL,  # 使用INCREMENTAL模式
                    batch_size=self.batch_size_spin.value(),
                    max_workers=self.workers_spin.value(),
                    start_date=self.start_date.date().toString("yyyy-MM-dd"),
                    end_date=self.end_date.date().toString("yyyy-MM-dd"),
                    retry_count=self.retry_count_spin.value() if hasattr(self, 'retry_count_spin') else 3,
                    error_strategy=self.error_strategy_combo.currentText() if hasattr(self, 'error_strategy_combo') else "跳过",
                    memory_limit=self.memory_limit_spin.value() if hasattr(self, 'memory_limit_spin') else 2048,
                    timeout=self.timeout_spin.value() if hasattr(self, 'timeout_spin') else 60,
                    progress_interval=self.progress_interval_spin.value() if hasattr(self, 'progress_interval_spin') else 5,
                    validate_data=self.validate_data_cb.isChecked() if hasattr(self, 'validate_data_cb') else True,
                    # 增量下载专用配置
                    incremental_days=incremental_days,
                    skip_weekends=True,
                    skip_holidays=True,
                    # 复选框配置
                    check_completeness=check_completeness,
                    skip_latest_data=skip_latest_data
                )

            else:
                # 全量下载模式配置
                task_config = ImportTaskConfig(
                    task_id=f"task_{int(datetime.now().timestamp())}",
                    name=task_name,
                    symbols=symbols,
                    data_source=self.data_source_combo.currentText(),
                    asset_type=self._get_asset_type_value(),
                    data_type=self.data_type_combo.currentText() if hasattr(self, 'data_type_combo') else "K线数据",
                    frequency=freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY),
                    mode=ImportMode.MANUAL,  # 全量下载使用MANUAL模式
                    batch_size=self.batch_size_spin.value(),
                    max_workers=self.workers_spin.value(),
                    start_date=self.start_date.date().toString("yyyy-MM-dd"),
                    end_date=self.end_date.date().toString("yyyy-MM-dd"),
                    retry_count=self.retry_count_spin.value() if hasattr(self, 'retry_count_spin') else 3,
                    error_strategy=self.error_strategy_combo.currentText() if hasattr(self, 'error_strategy_combo') else "跳过",
                    memory_limit=self.memory_limit_spin.value() if hasattr(self, 'memory_limit_spin') else 2048,
                    timeout=self.timeout_spin.value() if hasattr(self, 'timeout_spin') else 60,
                    progress_interval=self.progress_interval_spin.value() if hasattr(self, 'progress_interval_spin') else 5,
                    validate_data=self.validate_data_cb.isChecked() if hasattr(self, 'validate_data_cb') else True
                )

            # 更新引擎配置
            self.import_engine.enable_ai_optimization = self.ai_optimization_cb.isChecked()
            self.import_engine.enable_auto_tuning = self.auto_tuning_cb.isChecked()
            self.import_engine.enable_distributed_execution = self.distributed_cb.isChecked()
            self.import_engine.enable_intelligent_caching = self.caching_cb.isChecked()
            self.import_engine.enable_data_quality_monitoring = self.quality_monitoring_cb.isChecked()

            # 保存配置并启动任化
            self.config_manager.add_import_task(task_config)

            if self.import_engine.start_task(task_config.task_id):
                self.log_message(f"任务启动成功: {task_name}")

                # 保存当前任务ID
                self.current_task_id = task_config.task_id

                # 通知监控面板任务已启动
                if hasattr(self, 'download_monitoring'):
                    # ✅ 设置当前任务配置（用于重新下载功能）
                    self.download_monitoring.set_current_task_config(task_config)
                    self.download_monitoring.update_progress({
                        'progress': 0.0,
                        'message': '任务已启动',
                        'task_id': task_config.task_id,
                        'task_name': task_config.name
                    })
            else:
                self.log_message(f"任务启动失败: {task_name}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动任务失败: {str(e)}")
            self.log_message(f"启动任务失败: {str(e)}")

    def stop_import(self):
        """停止导入"""
        if self.import_engine:
            # 这里可以添加停止逻辑
            self.log_message("停止导入请求已发送")

    def on_task_started(self, task_id: str):
        """任务开始回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(0)
        if hasattr(self, 'progress_label'):
            self.progress_label.setText("任务已开始..")
        self.log_message(f"任务开始: {task_id}")
        # 刷新任务列表以更新状态
        self.refresh_task_list()

    def on_task_progress(self, task_id: str, progress: float, message: str):
        """任务进度回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(int(progress * 100))
        if hasattr(self, 'progress_label'):
            self.progress_label.setText(message)
        self.log_message(f"进度更新: {progress:.1%} - {message}")

        # ✅ 修复：检测并记录符号级错误到错误日志表，成功时清除错误记录
        if hasattr(self, 'download_monitoring') and self.download_monitoring:
            try:
                # ✅ 修复：从message中提取错误信息（格式：导入股票数据: SYMBOL (成功数/总数) 或包含错误信息）
                import re
                from datetime import datetime

                # ✅ 修复：检查message是否包含错误信息（匹配格式：导入股票数据: SYMBOL (x/y) | SYMBOL失败: 错误信息）
                error_patterns = [
                    r'(\d{6})失败[:：]\s*(.+)',  # 匹配"SYMBOL失败: 错误信息"格式（新格式）
                    r'(\d{6}).*?失败[:：]\s*(.+)',  # 匹配"SYMBOL...失败: 错误信息"格式
                    r'失败.*?(\d{6})',  # 匹配"失败"后跟股票代码（旧格式，兼容）
                ]

                symbol = None
                error_msg = None
                error_type = "导入失败"
                is_error = False

                # 检查是否包含错误信息
                for pattern in error_patterns:
                    match = re.search(pattern, message)
                    if match:
                        is_error = True
                        if len(match.groups()) >= 1:
                            symbol = match.group(1)
                        if len(match.groups()) >= 2:
                            error_msg = match.group(2).strip()
                        else:
                            # 如果没有提取到错误信息，使用默认值
                            error_msg = "导入失败"
                        break

                # ✅ 新增：如果检测到错误，添加到错误日志表
                if is_error and symbol and error_msg:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    self.download_monitoring.add_error(
                        timestamp=timestamp,
                        symbol=symbol,
                        error_type=error_type,
                        error_msg=error_msg
                    )
                    logger.debug(f"✅ [错误日志] 已记录符号级错误: {symbol} - {error_msg}")
                # ✅ 新增：如果检测到成功导入（不包含"失败"关键字），清除对应的错误记录
                elif not is_error:
                    # 尝试从message中提取symbol（格式：导入股票数据: SYMBOL (x/y)）
                    success_patterns = [
                        r'导入.*?[:：]\s*(\d{6})\s*\(',  # 匹配"导入...: SYMBOL ("
                        r'(\d{6})\s*\([^)]*\)',  # 匹配"SYMBOL (x/y)"
                        r'正在导入\s+(\d{6})',  # 匹配"正在导入 SYMBOL"
                    ]

                    for pattern in success_patterns:
                        match = re.search(pattern, message)
                        if match:
                            symbol = match.group(1)
                            # ✅ 清除该symbol的错误记录（如果存在）
                            if hasattr(self.download_monitoring, 'remove_error'):
                                removed = self.download_monitoring.remove_error(symbol)
                                if removed:
                                    logger.debug(f"✅ [错误日志] 已清除符号错误记录: {symbol}（导入成功）")
                            break

                # 解析message获取详细信息
                progress_data = {
                    'progress': progress,
                    'message': message,
                    'task_id': task_id,
                    'task_name': self.task_name_edit.text() if hasattr(self, 'task_name_edit') else ''
                }
                self.download_monitoring.update_progress(progress_data)
            except Exception as e:
                logger.error(f"更新下载监控失败: {e}") if logger else None

    def on_task_completed(self, task_id: str, result):
        """任务完成回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(100)
        if hasattr(self, 'progress_label'):
            self.progress_label.setText("任务完成!")
        self.log_message(f"✅ 任务完成: {task_id}")

        # 通知监控面板任务已完成
        if hasattr(self, 'download_monitoring'):
            self.download_monitoring.update_progress({
                'progress': 1.0,
                'message': '任务已完成',
                'task_id': task_id,
                'task_name': self.task_name_edit.text()
            })

        # 清除当前任务ID
        if hasattr(self, 'current_task_id') and self.current_task_id == task_id:
            self.current_task_id = None

        # 刷新任务列表以更新状态
        self.refresh_task_list()

    def on_task_failed(self, task_id: str, error_message: str):
        """任务失败回调"""
        if hasattr(self, 'progress_label'):
            self.progress_label.setText("任务失败!")
        self.log_message(f"❌ 任务失败: {task_id} - {error_message}")

        # 通知监控面板任务已失败
        if hasattr(self, 'download_monitoring'):
            self.download_monitoring.update_progress({
                'progress': 0.0,
                'message': f'任务失败: {error_message}',
                'task_id': task_id,
                'task_name': self.task_name_edit.text()
            })

        # 清除当前任务ID
        if hasattr(self, 'current_task_id') and self.current_task_id == task_id:
            self.current_task_id = None

        # 刷新任务列表以更新状态
        self.refresh_task_list()

    def update_status(self):
        """更新状态显化"""
        if not CORE_AVAILABLE or not self.import_engine:
            return

        try:
            # 安全检查组件是否存在
            if not self._check_component_exists('predictions_count_label'):
                return

            # 更新AI状态
            ai_stats = self.import_engine.get_ai_optimization_stats()
            if self._update_label_safe('predictions_count_label', str(ai_stats.get('predictions_made', 0))):
                pass
            if self._update_label_safe('time_saved_label', f"{ai_stats.get('execution_time_saved', 0):.1f}"):
                pass
            if self._update_label_safe('accuracy_label', f"{ai_stats.get('accuracy_improved', 0):.1f}"):
                pass

            # 更新AutoTuner状态
            tuner_stats = self.import_engine.get_auto_tuning_status()
            if self._update_label_safe('active_tuning_label', str(tuner_stats.get('active_tasks', 0))):
                pass
            if self._update_label_safe('completed_tuning_label', str(tuner_stats.get('completed_tasks', 0))):
                pass
            if self._update_label_safe('total_improvement_label', f"{tuner_stats.get('total_improvement', 0):.1f}"):
                pass

            # 更新缓存状态
            cache_stats = self.import_engine.get_cache_statistics()
            # 这里可以添加缓存统计的显示逻辑

            # 更新分布式状态
            distributed_stats = self.import_engine.get_distributed_status()
            if self._update_label_safe('discovered_nodes_label', str(distributed_stats.get('discovered_nodes', 0))):
                pass
            if self._update_label_safe('available_nodes_label', str(distributed_stats.get('available_nodes', 0))):
                pass

            # 更新节点表格
            self.update_nodes_table(distributed_stats.get('nodes_detail', []))

            # 更新数据质量状态
            quality_stats = self.import_engine.get_data_quality_statistics()
            # 这里可以添加数据质量统计的显示逻辑

        except Exception as e:
            logger.error(f"更新状态失败: {e}") if logger else None

    def _check_component_exists(self, component_name: str) -> bool:
        """安全检查组件是否存在"""
        try:
            return hasattr(self, component_name) and getattr(self, component_name) is not None
        except Exception:
            return False

    def _update_label_safe(self, label_name: str, text: str) -> bool:
        """安全更新标签文本"""
        try:
            if self._check_component_exists(label_name):
                label = getattr(self, label_name)
                if hasattr(label, 'setText'):
                    label.setText(text)
                    return True
        except Exception:
            pass
        return False

    def update_nodes_table(self, nodes_data: List[Dict]):
        """更新节点表格"""
        self.nodes_table.setRowCount(len(nodes_data))

        for row, node in enumerate(nodes_data):
            self.nodes_table.setItem(row, 0, QTableWidgetItem(node.get('node_id', '')))
            self.nodes_table.setItem(row, 1, QTableWidgetItem(f"{node.get('address', '')}:{node.get('port', '')}"))
            self.nodes_table.setItem(row, 2, QTableWidgetItem(str(node.get('task_count', 0))))

            status = "可用" if node.get('available', False) else "不可用"
            self.nodes_table.setItem(row, 3, QTableWidgetItem(status))

    def log_message(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("H:M:S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)

        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def create_task_management_tab(self) -> QWidget:
        """创建任务管理选项"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 工具
        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)

        # 新建任务按钮
        new_task_btn = QPushButton("新建任务")
        new_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        new_task_btn.clicked.connect(self.create_new_import_task)
        toolbar_layout.addWidget(new_task_btn)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_task_list)
        toolbar_layout.addWidget(refresh_btn)

        # 批量操作按钮
        batch_start_btn = QPushButton("▶️ 批量启动")
        batch_start_btn.setStyleSheet("""
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
        """)
        batch_start_btn.clicked.connect(self.batch_start_tasks)
        toolbar_layout.addWidget(batch_start_btn)

        batch_stop_btn = QPushButton("⏹️ 批量停止")
        batch_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        batch_stop_btn.clicked.connect(self.batch_stop_tasks)
        toolbar_layout.addWidget(batch_stop_btn)

        toolbar_layout.addStretch()

        # 搜索
        search_label = QLabel("搜索:")
        toolbar_layout.addWidget(search_label)

        self.task_search_input = QLineEdit()
        self.task_search_input.setPlaceholderText("输入任务名称或状态..")
        self.task_search_input.setMaximumWidth(200)
        self.task_search_input.textChanged.connect(self.filter_task_list)
        toolbar_layout.addWidget(self.task_search_input)

        layout.addWidget(toolbar_frame)

        # 任务列表表格
        self.task_table = QTableWidget()
        self.task_table.setMinimumHeight(200)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSortingEnabled(True)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_table.customContextMenuRequested.connect(self.show_task_context_menu)

        # 设置表格
        columns = [
            "任务名称", "状态", "进度", "数据源", "资产类型", "数据类型",
            "频率", "下载数量", "开始时间", "结束时间", "运行时间", "成功数", "失败数"
        ]
        self.task_table.setColumnCount(len(columns))
        self.task_table.setHorizontalHeaderLabels(columns)

        # 设置表格属性
        header = self.task_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 任务名称列自动拉伸

        # 设置列宽
        column_widths = [200, 80, 100, 100, 80, 80, 80, 80, 140, 140, 100, 60, 60]
        for i, width in enumerate(column_widths[1:], 1):  # 跳过第一列（自动拉伸）
            self.task_table.setColumnWidth(i, width)

        # 🔧 使用拉伸因子：任务表格占主要空间
        layout.addWidget(self.task_table, stretch=30)

        # ✅ 删除：任务详情面板已移除

        # K线下载情况监控面板
        if REALTIME_WRITE_UI_AVAILABLE:
            download_monitoring_group = QGroupBox("📊 K线下载情况")
            # 🔧 设置最小高度确保内容可见
            download_monitoring_group.setMinimumHeight(350)
            download_monitoring_layout = QVBoxLayout(download_monitoring_group)

            # 创建监控组件
            self.download_monitoring = RealtimeWriteMonitoringWidget()
            # ✅ 设置父组件引用和当前任务配置（用于重新下载功能）
            self.download_monitoring.set_parent_widget(self)
            download_monitoring_layout.addWidget(self.download_monitoring)

            # 🔧 给予一定的拉伸权重，确保可见
            layout.addWidget(download_monitoring_group, stretch=3)
            logger.info("K线下载情况监控面板已添加到任务详情区域") if logger else None

        # IP使用监控（通达信）- 独立组件
        if REALTIME_WRITE_UI_AVAILABLE and IPMonitorWidget is not None:
            ip_monitor_group = QGroupBox("🌐 IP使用监控（通达信）")
            ip_monitor_group.setMinimumHeight(300)
            ip_monitor_layout = QVBoxLayout(ip_monitor_group)

            # 创建IP监控组件
            self.ip_monitor = IPMonitorWidget()
            ip_monitor_layout.addWidget(self.ip_monitor)

            # 添加到布局，与K线下载情况平级
            layout.addWidget(ip_monitor_group, stretch=1)
            logger.info("IP使用监控面板已添加到任务详情区域") if logger else None
        else:
            self.ip_monitor = None

        # 连接表格选择信号
        self.task_table.itemSelectionChanged.connect(self.on_task_selection_changed)
        self.task_table.itemDoubleClicked.connect(self._on_task_double_clicked)

        # 初始化任务列表
        self.refresh_task_list()

        return tab

    def create_new_task_from_config(self):
        """根据当前UI配置创建新任务"""
        try:
            # 获取当前UI中的配置
            task_config_dict = self._get_current_ui_config()

            # 验证必要参数
            if not task_config_dict.get('symbols'):
                QMessageBox.warning(self, "提示", "请先输入或选择股票代码")
                return

            # 使用传统方式创建任务
            self._create_task_legacy(task_config_dict)

        except Exception as e:
            logger.error(f"从配置创建任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"创建任务失败: {e}")

    def _get_current_ui_config(self) -> dict:
        """获取当前UI中的配置"""
        try:
            # 解析股票代码
            symbols_text = self.symbols_edit.toPlainText().strip() if hasattr(self, 'symbols_edit') else ""
            symbols = []
            if symbols_text:
                lines = symbols_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        # 提取代码部分（去掉名称）
                        if '（' in line:
                            code = line.split('（')[0].strip()
                        elif '(' in line:
                            code = line.split('(')[0].strip()
                        else:
                            code = line
                        if code:
                            symbols.append(code)

            # 频率映射
            freq_map = {
                "日线": "1d",
                "周线": "1w",
                "月线": "1m",
                "5分钟": "5m",
                "15分钟": "15m",
                "30分钟": "30m",
                "60分钟": "60m"
            }

            # 🎯 构建任务名称（自动追加数据用途标记）
            base_task_name = self.task_name_edit.text().strip() if hasattr(self, 'task_name_edit') and self.task_name_edit.text().strip() else f"导入任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            usage_tag = self._get_data_usage_tag() if hasattr(self, '_get_data_usage_tag') else "[通用]"

            # 如果任务名已经包含标记，先移除旧标记
            import re
            base_task_name = re.sub(r'\[(通用|历史|回测|实时|实盘)\]$', '', base_task_name).strip()

            # 追加新标记
            final_task_name = f"{base_task_name}{usage_tag}"

            # 构建配置字典，包含合并后的高级配置
            config = {
                'task_id': f"task_{int(datetime.now().timestamp())}",
                'name': final_task_name,  # ✅ 使用带标记的任务名
                'data_usage': self._get_data_usage_value() if hasattr(self, '_get_data_usage_value') else "general",  # 🆕 添加数据用途字段
                'symbols': symbols,
                'asset_type': self._get_asset_type_value() if hasattr(self, '_get_asset_type_value') else (self.asset_type_combo.currentText() if hasattr(self, 'asset_type_combo') else "股票"),
                'data_type': self.data_type_combo.currentText() if hasattr(self, 'data_type_combo') else "K线数据",
                'frequency': freq_map.get(self.frequency_combo.currentText() if hasattr(self, 'frequency_combo') else "日线", "1d"),
                'data_source': self.data_source_combo.currentText() if hasattr(self, 'data_source_combo') else "通达信",

                # 从合并的配置tab中读取高级配置
                'batch_size': self.batch_size_spin.value() if hasattr(self, 'batch_size_spin') else 1000,
                'max_workers': self.workers_spin.value() if hasattr(self, 'workers_spin') else 8,  # ✅ 优化：默认工作线程数从4增加到8
                'memory_limit': self.memory_limit_spin.value() if hasattr(self, 'memory_limit_spin') else 2048,
                'timeout': self.timeout_spin.value() if hasattr(self, 'timeout_spin') else 60,  # ✅ 优化：默认超时从300秒减少到60秒
                'retry_count': self.retry_count_spin.value() if hasattr(self, 'retry_count_spin') else 3,
                'error_strategy': self.error_strategy_combo.currentText() if hasattr(self, 'error_strategy_combo') else "跳过",
                'progress_interval': self.progress_interval_spin.value() if hasattr(self, 'progress_interval_spin') else 5,
                'validate_data': self.validate_data_cb.isChecked() if hasattr(self, 'validate_data_cb') else True,

                # 智能化功能配置
                'ai_optimization': self.ai_optimization_cb.isChecked() if hasattr(self, 'ai_optimization_cb') else True,
                'auto_tuning': self.auto_tuning_cb.isChecked() if hasattr(self, 'auto_tuning_cb') else True,
                'distributed': self.distributed_cb.isChecked() if hasattr(self, 'distributed_cb') else True,
                'caching': self.caching_cb.isChecked() if hasattr(self, 'caching_cb') else True,
                'quality_monitoring': self.quality_monitoring_cb.isChecked() if hasattr(self, 'quality_monitoring_cb') else True,

                # 时间范围配置
                'start_date': self.start_date.date().toString("yyyy-MM-dd") if hasattr(self, 'start_date') else None,
                'end_date': self.end_date.date().toString("yyyy-MM-dd") if hasattr(self, 'end_date') else None,

                # 实时写入配置
                'write_strategy': self.write_strategy_combo.currentText() if hasattr(self, 'write_strategy_combo') else "禁用写入",
                'enable_perf_monitor': self.enable_perf_monitor_cb.isChecked() if hasattr(self, 'enable_perf_monitor_cb') else True,
                'enable_memory_monitor': self.enable_memory_monitor_cb.isChecked() if hasattr(self, 'enable_memory_monitor_cb') else True
            }

            return config

        except Exception as e:
            logger.error(f"获取UI配置失败: {e}") if logger else None
            return {}

    def create_new_import_task(self):
        """创建新的导入任务（增强版）"""
        try:
            # 使用集成的任务创建功能
            self.create_new_task_from_config()

        except Exception as e:
            logger.error(f"创建任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"创建任务失败: {e}")

    def _create_task_legacy(self, task_config_dict):
        """传统方式创建任务（回退方案）"""
        try:
            # 频率字符串到枚举的映射
            frequency_str = task_config_dict.get('frequency', '1d')
            frequency_map = {
                '1d': DataFrequency.DAILY,
                '1w': DataFrequency.WEEKLY,
                '1m': DataFrequency.MONTHLY,
                '5m': DataFrequency.MINUTE_5,
                '15m': DataFrequency.MINUTE_15,
                '30m': DataFrequency.MINUTE_30,
                '60m': DataFrequency.HOUR_1,
                '1min': DataFrequency.MINUTE_1,
                'daily': DataFrequency.DAILY
            }
            frequency_enum = frequency_map.get(frequency_str, DataFrequency.DAILY)

            # 转换为ImportTaskConfig对象
            task_config = ImportTaskConfig(
                task_id=task_config_dict.get('task_id', f"task_{int(datetime.now().timestamp())}"),
                name=task_config_dict.get('name', f"导入任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                symbols=task_config_dict.get('symbols', []),
                data_source=task_config_dict.get('data_source', ''),
                asset_type=task_config_dict.get('asset_type', ''),
                data_type=task_config_dict.get('data_type', 'K线数据'),
                frequency=frequency_enum,
                mode=ImportMode.MANUAL,
                batch_size=task_config_dict.get('batch_size', 100),
                max_workers=task_config_dict.get('max_workers', 4),
                start_date=task_config_dict.get('start_date', None),
                end_date=task_config_dict.get('end_date', None),
                retry_count=task_config_dict.get('retry_count', 3),
                error_strategy=task_config_dict.get('error_strategy', '跳过'),
                memory_limit=task_config_dict.get('memory_limit', 2048),
                timeout=task_config_dict.get('timeout', 60),  # ✅ 优化：默认超时从300秒减少到60秒
                progress_interval=task_config_dict.get('progress_interval', 5),
                validate_data=task_config_dict.get('validate_data', True)
            )

            # 添加任务到配置管理器
            if self.config_manager:
                self.config_manager.add_import_task(task_config)
                logger.info(f"创建新任务 {task_config.name}") if logger else None
                self.refresh_task_list()
                QMessageBox.information(self, "成功", f"任务 '{task_config.name}' 创建成功")
            else:
                QMessageBox.warning(self, "错误", "配置管理器未初始化")

        except Exception as e:
            logger.error(f"传统方式创建任务失败: {e}")
            QMessageBox.critical(self, "错误", f"创建任务失败: {e}")

    def refresh_task_list(self):
        """刷新任务列表（优化版：增量更新，减少闪烁）"""
        try:
            if not self.config_manager:
                logger.warning("配置管理器未初始化，无法刷新任务列表") if logger else None
                return

            # 获取所有任务
            tasks = self.config_manager.get_import_tasks()

            # 🔧 优化：禁用排序和更新信号，减少闪烁
            self.task_table.setSortingEnabled(False)
            self.task_table.blockSignals(True)

            try:
                # 构建任务ID到任务对象的映射
                task_map = {task.task_id: task for task in tasks}

                # 构建当前表格中的任务ID集合
                existing_task_ids = set()
                for row in range(self.task_table.rowCount()):
                    item = self.task_table.item(row, 0)
                    if item:
                        task_id = item.data(Qt.UserRole)
                        if task_id:
                            existing_task_ids.add(task_id)

                # 🔧 删除不存在的任务行（从后往前删除避免索引错乱）
                for row in range(self.task_table.rowCount() - 1, -1, -1):
                    item = self.task_table.item(row, 0)
                    if item:
                        task_id = item.data(Qt.UserRole)
                        if task_id and task_id not in task_map:
                            self.task_table.removeRow(row)

                # 🔧 增量更新：更新已存在的任务，添加新任务
                for task in tasks:
                    task_id = task.task_id

                    # 查找任务所在行
                    row_index = -1
                    for row in range(self.task_table.rowCount()):
                        item = self.task_table.item(row, 0)
                        if item and item.data(Qt.UserRole) == task_id:
                            row_index = row
                            break

                    # 获取任务状态
                    task_status = None
                    if self.import_engine:
                        task_status = self.import_engine.get_task_status(task_id)

                    # 准备任务数据
                    start_time = task_status.start_time.strftime("%Y-%m-%d %H:%M:%S") if task_status and hasattr(task_status, 'start_time') and task_status.start_time else "未开始"
                    end_time = task_status.end_time.strftime("%Y-%m-%d %H:%M:%S") if task_status and hasattr(task_status, 'end_time') and task_status.end_time else "未结束"

                    # 计算运行时间
                    runtime = "未开始"
                    if task_status and hasattr(task_status, 'start_time') and task_status.start_time:
                        if hasattr(task_status, 'end_time') and task_status.end_time:
                            delta = task_status.end_time - task_status.start_time
                            runtime = str(delta).split('.')[0]
                        else:
                            from datetime import datetime
                            delta = datetime.now() - task_status.start_time
                            runtime = str(delta).split('.')[0]

                    # 状态中文映射
                    status_map = {
                        'pending': '待执行',
                        'running': '运行中',
                        'completed': '已完成',
                        'failed': '失败',
                        'cancelled': '已取消',
                        'paused': '已暂停'
                    }

                    if task_status:
                        status_value = task_status.status.value if hasattr(task_status.status, 'value') else str(task_status.status)
                        status_text = status_map.get(status_value.lower(), status_value)
                    else:
                        status_text = "未开始"

                    # 计算成功数和失败数
                    success_count = 0
                    failure_count = 0
                    if task_status:
                        if hasattr(task_status, 'processed_records'):
                            total_processed = task_status.processed_records
                            failed = getattr(task_status, 'failed_records', 0)
                            success_count = total_processed - failed
                            failure_count = failed
                        elif hasattr(task_status, 'success_count'):
                            success_count = task_status.success_count
                            failure_count = getattr(task_status, 'failure_count', 0)

                    items = [
                        task.name,
                        status_text,
                        f"{task_status.progress:.1f}%" if task_status and hasattr(task_status, 'progress') else "0%",
                        task.data_source,
                        task.asset_type,
                        task.data_type,
                        task.frequency.value if hasattr(task.frequency, 'value') else str(task.frequency),
                        str(len(task.symbols)),
                        start_time,
                        end_time,
                        runtime,
                        str(success_count),
                        str(failure_count)
                    ]

                    # 🔧 如果任务存在，更新单元格内容而非重建整行
                    if row_index >= 0:
                        for col, item_text in enumerate(items):
                            item = self.task_table.item(row_index, col)
                            if item:
                                # 只在内容变化时更新
                                if item.text() != str(item_text):
                                    item.setText(str(item_text))

                                    # 根据状态设置颜色
                                    if col == 1:  # 状态列
                                        if "运行中" in item_text:
                                            item.setBackground(QColor("#d4edda"))
                                        elif "完成" in item_text:
                                            item.setBackground(QColor("#cce5ff"))
                                        elif "失败" in item_text or "错误" in item_text:
                                            item.setBackground(QColor("#f8d7da"))
                                        elif "暂停" in item_text:
                                            item.setBackground(QColor("#fff3cd"))
                                        else:
                                            item.setBackground(QColor("#ffffff"))
                    else:
                        # 🔧 新任务：添加新行
                        row = self.task_table.rowCount()
                        self.task_table.insertRow(row)

                        for col, item_text in enumerate(items):
                            item = QTableWidgetItem(str(item_text))

                            # 根据状态设置颜色
                            if col == 1:  # 状态列
                                if "运行中" in item_text:
                                    item.setBackground(QColor("#d4edda"))
                                elif "完成" in item_text:
                                    item.setBackground(QColor("#cce5ff"))
                                elif "失败" in item_text or "错误" in item_text:
                                    item.setBackground(QColor("#f8d7da"))
                                elif "暂停" in item_text:
                                    item.setBackground(QColor("#fff3cd"))

                            self.task_table.setItem(row, col, item)

                        # 存储任务ID
                        self.task_table.item(row, 0).setData(Qt.UserRole, task_id)

            finally:
                # 🔧 恢复信号和排序
                self.task_table.blockSignals(False)
                self.task_table.setSortingEnabled(True)

        except Exception as e:
            logger.error(f"刷新任务列表失败: {e}") if logger else None
            import traceback
            logger.error(traceback.format_exc()) if logger else None

    def filter_task_list(self):
        """过滤任务列表"""
        try:
            filter_text = self.task_search_input.text().lower()

            for row in range(self.task_table.rowCount()):
                show_row = False

                # 检查任务名称和状态列
                for col in [0, 1]:  # 任务名称和状化
                    item = self.task_table.item(row, col)
                    if item and filter_text in item.text().lower():
                        show_row = True
                        break

                self.task_table.setRowHidden(row, not show_row)

        except Exception as e:
            logger.error(f"过滤任务列表失败: {e}") if logger else None

    def on_task_selection_changed(self):
        """任务选择变化处理（任务详情UI已删除，此方法保留用于未来扩展）"""
        try:
            selected_items = self.task_table.selectedItems()
            if not selected_items:
                return

            # ✅ 删除：任务详情UI已移除，此方法保留用于未来扩展
            # 可以在这里添加其他选择变化时的处理逻辑

        except Exception as e:
            logger.error(f"处理任务选择变化失败: {e}") if logger else None

    def show_task_context_menu(self, position):
        """显示任务右键菜单"""
        try:
            item = self.task_table.itemAt(position)
            if not item:
                # 如果没有点击到具体项目，仍然显示基本菜单
                menu = QMenu(self)
                refresh_action = QAction("刷新任务列表", self)
                refresh_action.triggered.connect(self.refresh_task_list)
                menu.addAction(refresh_action)
                menu.exec_(self.task_table.mapToGlobal(position))
                return

            menu = QMenu(self)

            # 获取选中的任务
            selected_rows = set()
            for selected_item in self.task_table.selectedItems():
                selected_rows.add(selected_item.row())

            # 如果没有选中任何行，选中当前点击的行
            if not selected_rows:
                clicked_row = item.row()
                self.task_table.selectRow(clicked_row)
                selected_rows.add(clicked_row)

            if len(selected_rows) == 1:
                # 单个任务操作
                row = list(selected_rows)[0]
                task_name_item = self.task_table.item(row, 0)
                status_item = self.task_table.item(row, 1)

                if not task_name_item or not status_item:
                    # 添加刷新菜单作为默认选项
                    refresh_action = QAction("刷新任务列表", self)
                    refresh_action.triggered.connect(self.refresh_task_list)
                    menu.addAction(refresh_action)
                else:
                    task_id = task_name_item.data(Qt.UserRole)
                    task_name = task_name_item.text()
                    status = status_item.text()

                    # 如果没有task_id，使用任务名称作为标识
                    if not task_id:
                        task_id = task_name

                    start_action = QAction("▶️ 开始导入", self)
                    start_action.triggered.connect(lambda: self.start_single_task(task_id))
                    start_action.setEnabled("运行中" not in status and "完成" not in status)
                    menu.addAction(start_action)

                    stop_action = QAction("⏹️ 停止导入", self)
                    stop_action.triggered.connect(lambda: self.stop_single_task(task_id))
                    stop_action.setEnabled("运行中" in status)
                    menu.addAction(stop_action)

                    menu.addSeparator()

                    view_action = QAction("👁️ 查看详情", self)
                    view_action.triggered.connect(lambda: self.view_task_details(task_id))
                    menu.addAction(view_action)

                    edit_action = QAction("✏️ 编辑任务", self)
                    edit_action.triggered.connect(lambda: self.edit_task(task_id))
                    menu.addAction(edit_action)

                    menu.addSeparator()

                    delete_action = QAction("🗑️ 删除任务", self)
                    delete_action.triggered.connect(lambda: self.delete_single_task(task_id))
                    menu.addAction(delete_action)

            else:
                # 批量操作
                batch_start_action = QAction(f"▶️ 批量启动 ({len(selected_rows)}项)", self)
                batch_start_action.triggered.connect(self.batch_start_tasks)
                menu.addAction(batch_start_action)

                batch_stop_action = QAction(f"⏹️ 批量停止 ({len(selected_rows)}项)", self)
                batch_stop_action.triggered.connect(self.batch_stop_tasks)
                menu.addAction(batch_stop_action)

                menu.addSeparator()

                batch_delete_action = QAction(f"🗑️ 批量删除 ({len(selected_rows)}项)", self)
                batch_delete_action.triggered.connect(self.batch_delete_tasks)
                menu.addAction(batch_delete_action)

            # 添加通用刷新选项
            if menu.actions():  # 如果菜单不为空，添加分隔符
                menu.addSeparator()
            refresh_action = QAction("刷新任务列表", self)
            refresh_action.triggered.connect(self.refresh_task_list)
            menu.addAction(refresh_action)

            menu.exec_(self.task_table.mapToGlobal(position))

        except Exception as e:
            logger.error(f"显示右键菜单失败: {e}") if logger else None

    def start_single_task(self, task_id: str):
        """启动单个任务"""
        try:
            if self.import_engine:
                success = self.import_engine.start_task(task_id)
                if success:
                    QMessageBox.information(self, "成功", "任务启动成功")
                    self.refresh_task_list()
                else:
                    QMessageBox.warning(self, "失败", "任务启动失败")
        except Exception as e:
            logger.error(f"启动任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"启动任务失败: {e}")

    def stop_single_task(self, task_id: str):
        """停止单个任务（异步执行避免UI卡顿）"""
        try:
            if not self.import_engine:
                QMessageBox.warning(self, "错误", "导入引擎未初始化")
                return

            # 使用QThread异步执行停止操作
            from PyQt5.QtCore import QThread, pyqtSignal

            class SingleStopWorker(QThread):
                """停止单个任务的后台工作线程"""
                finished = pyqtSignal(bool)  # success

                def __init__(self, task_id, import_engine):
                    super().__init__()
                    self.task_id = task_id
                    self.import_engine = import_engine

                def run(self):
                    try:
                        success = self.import_engine.stop_task(self.task_id)
                        self.finished.emit(success)
                    except Exception as e:
                        logger.error(f"停止任务失败: {e}") if logger else None
                        self.finished.emit(False)

            # 创建并启动工作线程
            worker = SingleStopWorker(task_id, self.import_engine)

            def on_finished(success):
                if success:
                    QMessageBox.information(self, "成功", "任务停止成功")
                else:
                    QMessageBox.warning(self, "失败", "任务停止失败")
                self.refresh_task_list()

            worker.finished.connect(on_finished)
            worker.start()

            # 保持worker引用避免被垃圾回收
            self._stop_worker = worker

            # 显示提示
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.showMessage("正在停止任务...", 2000)

        except Exception as e:
            logger.error(f"停止任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"停止任务失败: {e}")

    def delete_single_task(self, task_id: str):
        """删除单个任务"""
        try:
            reply = QMessageBox.question(
                self, "确认删除",
                "确定要删除这个任务吗？\n删除后无法恢复！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                if self.config_manager:
                    self.config_manager.remove_import_task(task_id)
                    QMessageBox.information(self, "成功", "任务删除成功")
                    self.refresh_task_list()
                else:
                    QMessageBox.warning(self, "错误", "配置管理器未初始化")
        except Exception as e:
            logger.error(f"删除任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"删除任务失败: {e}")

    def batch_start_tasks(self):
        """批量启动任务"""
        try:
            selected_task_ids = self.get_selected_task_ids()
            if not selected_task_ids:
                QMessageBox.warning(self, "警告", "请选择要启动的任务")
                return

            success_count = 0
            for task_id in selected_task_ids:
                if self.import_engine and self.import_engine.start_task(task_id):
                    success_count += 1

            QMessageBox.information(
                self, "批量启动结果",
                f"成功启动 {success_count}/{len(selected_task_ids)} 个任务"
            )
            self.refresh_task_list()

        except Exception as e:
            logger.error(f"批量启动任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"批量启动任务失败: {e}")

    def batch_pause_tasks(self):
        """批量暂停任务"""
        try:
            selected_task_ids = self.get_selected_task_ids()
            if not selected_task_ids:
                QMessageBox.warning(self, "警告", "请选择要暂停的任务")
                return

            success_count = 0
            for task_id in selected_task_ids:
                if self.ui_adapter:
                    try:
                        self.ui_adapter.pause_task(task_id)
                        success_count += 1
                    except Exception as e:
                        logger.warning(f"暂停任务 {task_id} 失败: {e}") if logger else None

            QMessageBox.information(
                self, "批量暂停结果",
                f"成功暂停 {success_count}/{len(selected_task_ids)} 个任务"
            )
            self.refresh_task_list()

        except Exception as e:
            logger.error(f"批量暂停任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"批量暂停任务失败: {e}")

    def batch_cancel_tasks(self):
        """批量取消任务"""
        try:
            selected_task_ids = self.get_selected_task_ids()
            if not selected_task_ids:
                QMessageBox.warning(self, "警告", "请选择要取消的任务")
                return

            reply = QMessageBox.question(
                self, "确认取消",
                f"确定要取消选中的 {len(selected_task_ids)} 个任务吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                success_count = 0
                for task_id in selected_task_ids:
                    if self.ui_adapter:
                        try:
                            self.ui_adapter.cancel_task(task_id)
                            success_count += 1
                        except Exception as e:
                            logger.warning(f"取消任务 {task_id} 失败: {e}") if logger else None

                QMessageBox.information(
                    self, "批量取消结果",
                    f"成功取消 {success_count}/{len(selected_task_ids)} 个任务"
                )
                self.refresh_task_list()

        except Exception as e:
            logger.error(f"批量取消任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"批量取消任务失败: {e}")

    def show_task_creation_wizard(self):
        """显示任务创建向导（现在使用集成的左侧面板功能）"""
        try:
            # 使用集成的任务创建功能
            self.create_new_task_from_config()

        except Exception as e:
            logger.error(f"显示任务创建向导失败: {e}") if logger else None
            # 降级到简单的任务创建对话框
            self._show_simple_task_creation_dialog()

    def _show_simple_task_creation_dialog(self):
        """显示简单的任务创建对话框（回退版本）"""
        from PyQt5.QtWidgets import QInputDialog

        task_name, ok = QInputDialog.getText(
            self, "创建新任务", "请输入任务名称"
        )

        if ok and task_name.strip():
            # 创建基础任务配置
            task_config = {
                'name': task_name.strip(),
                'data_source': 'default',
                'import_type': 'kline_data',
                'auto_start': False
            }

            if self.ui_adapter:
                try:
                    task_id = self.ui_adapter.create_task(
                        name=task_config['name'],
                        config=task_config
                    )

                    QMessageBox.information(
                        self, "任务创建成功",
                        f"任务 '{task_config['name']}' 创建成功\n任务ID: {task_id}"
                    )

                    self.refresh_task_list()

                except Exception as e:
                    QMessageBox.critical(self, "创建失败", f"任务创建失败: {e}")
            else:
                QMessageBox.warning(self, "警告", "UI适配器未初始化")

    def apply_unified_theme(self):
        """应用统一主题样式"""
        try:
            if not self.theme_manager or not self.design_system:
                return

            # 获取当前主题
            current_theme = self.theme_manager.get_current_theme()

            # 应用设计系统样式
            self._apply_design_system_styles()

            # 连接主题变化信号
            if hasattr(self.theme_manager, 'theme_changed'):
                self.theme_manager.theme_changed.connect(self._on_theme_changed)

            logger.info("统一主题应用成功") if logger else None

        except Exception as e:
            logger.error(f"应用统一主题失败: {e}") if logger else None

    def _apply_design_system_styles(self):
        """应用设计系统样式"""
        try:
            if not self.design_system:
                return

            # 应用统一的字体设置
            if hasattr(self.design_system, 'typography'):
                typography = self.design_system.typography

                # 设置主要字体
                if hasattr(typography, 'primary_font'):
                    main_font = QFont(typography.primary_font)
                    if hasattr(typography, 'base_size'):
                        main_font.setPointSize(typography.base_size)
                    self.setFont(main_font)

            # 应用间距和尺寸规范
            if hasattr(self.design_system, 'spacing'):
                # 这里可以设置组件间距
                pass

            # 应用阴影和边框效果
            if hasattr(self.design_system, 'elevation'):
                # 应用阴影效果
                pass

            logger.debug("设计系统样式应用成功") if logger else None

        except Exception as e:
            logger.error(f"应用设计系统样式失败: {e}") if logger else None

    def _on_theme_changed(self, new_theme):
        """主题改变时的处理"""
        try:
            # 通知所有子组件更新主题
            self._update_child_themes(new_theme)

            logger.info(f"主题已更化 {new_theme.name if hasattr(new_theme, 'name') else 'Unknown'}")

        except Exception as e:
            logger.error(f"处理主题变化失败: {e}") if logger else None

    def _update_child_themes(self, theme):
        """更新子组件主化"""
        try:
            # 更新已初始化的UI组件
            ui_components = [
                'task_dependency_visualizer',
                'task_scheduler_control',
                'ai_features_control_panel',
                'data_quality_control_center',
                'enhanced_performance_dashboard',
                'cache_status_monitor',
                'distributed_status_monitor'
            ]

            for component_name in ui_components:
                if hasattr(self, component_name):
                    component = getattr(self, component_name)
                    if component and hasattr(component, 'apply_theme'):
                        try:
                            component.apply_theme(theme)
                        except Exception as e:
                            logger.warning(f"更新组件 {component_name} 主题失败: {e}") if logger else None

        except Exception as e:
            logger.error(f"更新子组件主题失败: {e}") if logger else None

    def set_theme(self, theme_type: str):
        """设置主题类型"""
        try:
            if self.theme_manager:
                # ThemeManager使用主题名称字符串，不是枚举
                if theme_type.lower() == 'dark':
                    self.theme_manager.set_theme('Dark')
                elif theme_type.lower() == 'light':
                    self.theme_manager.set_theme('Light')
                elif theme_type.lower() == 'auto':
                    # ThemeManager暂不支持auto，使用Light作为默认
                    self.theme_manager.set_theme('Light')
                else:
                    logger.warning(f"未知主题类型: {theme_type}") if logger else None

        except Exception as e:
            logger.error(f"设置主题失败: {e}") if logger else None

    def get_current_theme_info(self) -> Dict[str, Any]:
        """获取当前主题信息"""
        try:
            if self.theme_manager:
                current_theme = self.theme_manager.get_current_theme()
                return {
                    'name': getattr(current_theme, 'name', 'Unknown'),
                    'type': getattr(current_theme, 'theme_type', 'Unknown'),
                    'category': getattr(current_theme, 'category', 'Unknown'),
                    'colors_available': hasattr(current_theme, 'colors'),
                    'dark_mode': getattr(current_theme, 'theme_type', '') == 'dark'
                }
            else:
                return {'name': 'Default', 'type': 'system', 'available': False}
        except Exception as e:
            logger.error(f"获取主题信息失败: {e}") if logger else None
            return {'error': str(e)}

    def apply_performance_optimization(self):
        """应用性能优化"""
        try:
            if not PERFORMANCE_OPTIMIZATION_AVAILABLE:
                logger.info("性能优化模块不可用，跳过优化") if logger else None
                return

            # 应用显示优化
            self._apply_display_optimization()

            # 应用虚拟化渲化
            self._apply_virtualization()

            # 应用内存管理
            self._apply_memory_management()

            logger.info("性能优化应用成功") if logger else None

        except Exception as e:
            logger.error(f"应用性能优化失败: {e}") if logger else None

    def _apply_display_optimization(self):
        """应用显示优化"""
        try:
            if not self.display_optimizer:
                return

            # 优化高DPI显示
            if hasattr(self.display_optimizer, 'optimize_high_dpi'):
                self.display_optimizer.optimize_high_dpi(self)

            # 优化字体渲染
            if hasattr(self.display_optimizer, 'optimize_font_rendering'):
                self.display_optimizer.optimize_font_rendering(self)

            # 优化图标显示
            if hasattr(self.display_optimizer, 'optimize_icon_display'):
                self.display_optimizer.optimize_icon_display(self)

            logger.debug("显示优化应用成功") if logger else None

        except Exception as e:
            logger.error(f"应用显示优化失败: {e}") if logger else None

    def _apply_virtualization(self):
        """应用虚拟化渲化"""
        try:
            if not self.virtualization_manager:
                return

            # 为大型表格启用虚拟化
            if hasattr(self, 'task_table') and self.task_table:
                if hasattr(self.virtualization_manager, 'enable_table_virtualization'):
                    self.virtualization_manager.enable_table_virtualization(self.task_table)

            # 为列表组件启用虚拟化
            list_widgets = self.findChildren(QListWidget)
            for list_widget in list_widgets:
                if hasattr(self.virtualization_manager, 'enable_list_virtualization'):
                    self.virtualization_manager.enable_list_virtualization(list_widget)

            # 为选项卡启用延迟加化
            if hasattr(self, 'monitor_tabs') and self.monitor_tabs:
                if hasattr(self.virtualization_manager, 'enable_tab_lazy_loading'):
                    self.virtualization_manager.enable_tab_lazy_loading(self.monitor_tabs)

            logger.debug("虚拟化渲染应用成功") if logger else None

        except Exception as e:
            logger.error(f"应用虚拟化渲染失败: {e}") if logger else None

    def _apply_memory_management(self):
        """应用内存管理"""
        try:
            if not self.memory_manager:
                return

            # 启用内存监控
            if hasattr(self.memory_manager, 'start_memory_monitoring'):
                self.memory_manager.start_memory_monitoring()

            # 设置内存清理策略
            if hasattr(self.memory_manager, 'set_cleanup_strategy'):
                self.memory_manager.set_cleanup_strategy('aggressive')

            # 优化图像缓存
            if hasattr(self.memory_manager, 'optimize_image_cache'):
                self.memory_manager.optimize_image_cache()

            # 设置内存限制
            if hasattr(self.memory_manager, 'set_memory_limit'):
                self.memory_manager.set_memory_limit(512)  # 512MB限制

            logger.debug("内存管理应用成功") if logger else None

        except Exception as e:
            logger.error(f"应用内存管理失败: {e}") if logger else None

    def optimize_performance_for_large_data(self, enable: bool = True):
        """为大数据量优化性能"""
        try:
            if not PERFORMANCE_OPTIMIZATION_AVAILABLE:
                return

            if enable:
                # 启用批量更新模式
                if hasattr(self, 'task_table') and self.task_table:
                    self.task_table.setUpdatesEnabled(False)

                # 减少定时器频化
                if hasattr(self, 'update_timer'):
                    self.update_timer.setInterval(5000)  # 5秒更新一化

                # 启用延迟渲染
                if self.virtualization_manager and hasattr(self.virtualization_manager, 'enable_lazy_rendering'):
                    self.virtualization_manager.enable_lazy_rendering(True)

                logger.info("大数据量性能优化已启用") if logger else None
            else:
                # 恢复正常更新模式
                if hasattr(self, 'task_table') and self.task_table:
                    self.task_table.setUpdatesEnabled(True)

                # 恢复正常定时器频化
                if hasattr(self, 'update_timer'):
                    self.update_timer.setInterval(1000)  # 1秒更新一化

                # 禁用延迟渲染
                if self.virtualization_manager and hasattr(self.virtualization_manager, 'enable_lazy_rendering'):
                    self.virtualization_manager.enable_lazy_rendering(False)

                logger.info("大数据量性能优化已禁用") if logger else None

        except Exception as e:
            logger.error(f"优化大数据量性能失败: {e}") if logger else None

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            metrics = {
                'display_optimization': False,
                'virtualization_enabled': False,
                'memory_management': False,
                'memory_usage': 0,
                'widget_count': 0,
                'timer_intervals': []
            }

            # 检查优化状态
            if self.display_optimizer:
                metrics['display_optimization'] = True

            if self.virtualization_manager:
                metrics['virtualization_enabled'] = True

            if self.memory_manager:
                metrics['memory_management'] = True
                if hasattr(self.memory_manager, 'get_memory_usage'):
                    metrics['memory_usage'] = self.memory_manager.get_memory_usage()

            # 统计组件数量
            metrics['widget_count'] = len(self.findChildren(QWidget))

            # 获取定时器信息
            timers = self.findChildren(QTimer)
            metrics['timer_intervals'] = [timer.interval() for timer in timers if timer.isActive()]

            return metrics

        except Exception as e:
            logger.error(f"获取性能指标失败: {e}") if logger else None
            return {'error': str(e)}

    def cleanup_resources(self):
        """清理资源"""
        try:
            # 停止所有定时器
            timers = self.findChildren(QTimer)
            for timer in timers:
                if timer.isActive():
                    timer.stop()

            # 清理内存
            if self.memory_manager and hasattr(self.memory_manager, 'cleanup'):
                self.memory_manager.cleanup()

            # 清理缓存
            from PyQt5.QtGui import QPixmapCache
            QPixmapCache.clear()

            # 断开信号连接
            if self.theme_manager and hasattr(self.theme_manager, 'theme_changed'):
                try:
                    self.theme_manager.theme_changed.disconnect()
                except:
                    pass

            logger.info("资源清理完成") if logger else None

        except Exception as e:
            logger.error(f"清理资源失败: {e}") if logger else None

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 清理资源
            self.cleanup_resources()

            # 保存设置
            if self.theme_manager and hasattr(self.theme_manager, 'save_settings'):
                self.theme_manager.save_settings()

            # 调用父类方法
            super().closeEvent(event)

        except Exception as e:
            logger.error(f"窗口关闭处理失败: {e}") if logger else None
            event.accept()

    def batch_stop_tasks(self):
        """批量停止任务（异步执行避免UI卡顿）"""
        try:
            selected_task_ids = self.get_selected_task_ids()
            if not selected_task_ids:
                QMessageBox.warning(self, "警告", "请选择要停止的任务")
                return

            reply = QMessageBox.question(
                self, "确认批量停止",
                f"确定要停止选中的 {len(selected_task_ids)} 个任务吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 使用QThread异步执行停止操作，避免阻塞UI
                from PyQt5.QtCore import QThread, pyqtSignal

                class StopTasksWorker(QThread):
                    """停止任务的后台工作线程"""
                    finished = pyqtSignal(int, int)  # success_count, total_count
                    progress = pyqtSignal(str)  # status_message

                    def __init__(self, task_ids, import_engine):
                        super().__init__()
                        self.task_ids = task_ids
                        self.import_engine = import_engine

                    def run(self):
                        success_count = 0
                        for i, task_id in enumerate(self.task_ids, 1):
                            try:
                                self.progress.emit(f"正在停止任务 {i}/{len(self.task_ids)}...")
                                if self.import_engine and self.import_engine.stop_task(task_id):
                                    success_count += 1
                            except Exception as e:
                                logger.warning(f"停止任务 {task_id} 失败: {e}") if logger else None

                        self.finished.emit(success_count, len(self.task_ids))

                # 创建并启动工作线程
                self.stop_worker = StopTasksWorker(selected_task_ids, self.import_engine)

                def on_stop_finished(success_count, total_count):
                    QMessageBox.information(
                        self, "批量停止结果",
                        f"成功停止 {success_count}/{total_count} 个任务"
                    )
                    self.refresh_task_list()

                def on_stop_progress(message):
                    if hasattr(self, 'status_bar') and self.status_bar:
                        self.status_bar.showMessage(message, 2000)

                self.stop_worker.finished.connect(on_stop_finished)
                self.stop_worker.progress.connect(on_stop_progress)
                self.stop_worker.start()

                # 显示提示
                if hasattr(self, 'status_bar') and self.status_bar:
                    self.status_bar.showMessage("正在停止任务，请稍候...", 3000)

        except Exception as e:
            logger.error(f"批量停止任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"批量停止任务失败: {e}")

    def batch_delete_tasks(self):
        """批量删除任务"""
        try:
            selected_task_ids = self.get_selected_task_ids()
            if not selected_task_ids:
                QMessageBox.warning(self, "警告", "请选择要删除的任务")
                return

            reply = QMessageBox.question(
                self, "确认批量删除",
                f"确定要删除选中化{len(selected_task_ids)} 个任务吗？\n删除后无法恢复化",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                success_count = 0
                for task_id in selected_task_ids:
                    if self.config_manager:
                        self.config_manager.remove_import_task(task_id)
                        success_count += 1

                QMessageBox.information(
                    self, "批量删除结果",
                    f"成功删除 {success_count}/{len(selected_task_ids)} 个任化"
                )
                self.refresh_task_list()

        except Exception as e:
            logger.error(f"批量删除任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"批量删除任务失败: {e}")

    def get_selected_task_ids(self) -> List[str]:
        """获取选中的任务ID列表"""
        task_ids = []
        selected_rows = set()

        for item in self.task_table.selectedItems():
            selected_rows.add(item.row())

        for row in selected_rows:
            task_id = self.task_table.item(row, 0).data(Qt.UserRole)
            if task_id:
                task_ids.append(task_id)

        return task_ids

    def view_task_details(self, task_id: str):
        """查看任务详情"""
        try:
            # 这里可以打开一个详细的任务信息对话框
            # 暂时使用消息框显示基本信息
            if self.import_engine:
                task_status = self.import_engine.get_task_status(task_id)
                if task_status:
                    progress_str = f"{task_status.progress:.1f}"
                    start_time_str = task_status.start_time.strftime('Y-m-d H:M:S') if task_status.start_time else '未开始'
                    end_time_str = task_status.end_time.strftime('Y-m-d H:M:S') if task_status.end_time else '未完成'

                    details = f"""任务详细信息:

    任务ID: {task_id}
    状态: {task_status.status.value}
    进度: {progress_str}
    开始时间: {start_time_str}
    结束时间: {end_time_str}"""
                    QMessageBox.information(self, "任务详情", details)
                else:
                    QMessageBox.information(self, "任务详情", f"任务ID: {task_id}\n状态: 未开始")
        except Exception as e:
            logger.error(f"查看任务详情失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"查看任务详情失败: {e}")

    def edit_task(self, task_id: str):
        """编辑任务"""
        try:
            if not self.config_manager:
                QMessageBox.warning(self, "错误", "配置管理器未初始化")
                return

            # 获取任务配置
            task = self.config_manager.get_import_task(task_id)
            if not task:
                QMessageBox.warning(self, "错误", f"未找到任务: {task_id}")
                return

            # 创建编辑对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(f"编辑任务 - {task.name}")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(400)

            layout = QVBoxLayout(dialog)

            # 创建表单布局
            form_layout = QFormLayout()

            # 任务名称（只读，由用途自动生成）
            name_edit = QLineEdit()
            # 移除任务名中的用途标记，显示基础名称
            import re
            base_name = re.sub(r'\[(通用|历史|回测|实时|实盘)\]$', '', task.name).strip()
            name_edit.setText(base_name)
            name_edit.setToolTip("任务名称将自动添加用途标记，如：任务名[回测]")
            form_layout.addRow("任务名称:", name_edit)

            # 🎯 数据用途（新增）- 从任务名中提取或使用默认值
            data_usage_edit_combo = QComboBox()
            data_usage_edit_combo.addItems([
                "通用场景",      # general
                "历史数据分析",  # historical
                "回测验证",      # backtest
                "实时行情",      # realtime
                "实盘交易"       # live_trading
            ])
            # 从任务名中提取用途标记
            usage_from_name = None
            if '[通用]' in task.name:
                usage_from_name = "通用场景"
            elif '[历史]' in task.name:
                usage_from_name = "历史数据分析"
            elif '[回测]' in task.name:
                usage_from_name = "回测验证"
            elif '[实时]' in task.name:
                usage_from_name = "实时行情"
            elif '[实盘]' in task.name:
                usage_from_name = "实盘交易"

            if usage_from_name:
                index = data_usage_edit_combo.findText(usage_from_name)
                if index >= 0:
                    data_usage_edit_combo.setCurrentIndex(index)

            data_usage_edit_combo.setToolTip(
                "选择数据用途后，任务名将自动添加对应标记\n"
                "系统会根据用途调整质量评分权重"
            )
            form_layout.addRow("🎯 数据用途:", data_usage_edit_combo)

            # 数据源
            data_source_combo = QComboBox()
            if hasattr(self, 'data_source_combo') and self.data_source_combo:
                for i in range(self.data_source_combo.count()):
                    data_source_combo.addItem(self.data_source_combo.itemText(i))
                # 设置当前值
                index = data_source_combo.findText(task.data_source)
                if index >= 0:
                    data_source_combo.setCurrentIndex(index)
            else:
                data_source_combo.addItem(task.data_source)
                data_source_combo.setCurrentIndex(0)
            form_layout.addRow("数据源:", data_source_combo)

            # 资产类型
            asset_type_combo = QComboBox()
            if hasattr(self, 'asset_type_combo') and self.asset_type_combo:
                for i in range(self.asset_type_combo.count()):
                    asset_type_combo.addItem(self.asset_type_combo.itemText(i))
                # 设置当前值
                index = asset_type_combo.findText(task.asset_type)
                if index >= 0:
                    asset_type_combo.setCurrentIndex(index)
            else:
                asset_type_combo.addItem(task.asset_type)
                asset_type_combo.setCurrentIndex(0)
            form_layout.addRow("资产类型:", asset_type_combo)

            # 数据类型
            data_type_combo = QComboBox()
            data_type_combo.addItems(["K线数据", "实时行情", "基本面数据"])
            index = data_type_combo.findText(task.data_type)
            if index >= 0:
                data_type_combo.setCurrentIndex(index)
            form_layout.addRow("数据类型:", data_type_combo)

            # 频率
            frequency_combo = QComboBox()
            frequency_items = ["日线", "周线", "月线", "5分钟", "15分钟", "30分钟", "60分钟"]
            frequency_combo.addItems(frequency_items)
            # 尝试匹配当前频率
            freq_value = task.frequency.value if hasattr(task.frequency, 'value') else str(task.frequency)
            freq_map_reverse = {
                "daily": "日线", "weekly": "周线", "monthly": "月线",
                "5min": "5分钟", "15min": "15分钟", "30min": "30分钟", "60min": "60分钟"
            }
            freq_display = freq_map_reverse.get(freq_value, "日线")
            index = frequency_combo.findText(freq_display)
            if index >= 0:
                frequency_combo.setCurrentIndex(index)
            form_layout.addRow("频率:", frequency_combo)

            # 日期范围
            from PyQt5.QtCore import QDate
            from datetime import datetime as dt

            date_layout = QHBoxLayout()
            start_date_edit = QDateEdit()
            start_date_edit.setCalendarPopup(True)
            start_date_edit.setDisplayFormat("yyyy-MM-dd")
            try:
                start_dt = dt.strptime(task.start_date, "%Y-%m-%d")
                start_date_edit.setDate(QDate(start_dt.year, start_dt.month, start_dt.day))
            except:
                start_date_edit.setDate(QDate.currentDate().addMonths(-3))
            date_layout.addWidget(start_date_edit)

            date_layout.addWidget(QLabel("至"))

            end_date_edit = QDateEdit()
            end_date_edit.setCalendarPopup(True)
            end_date_edit.setDisplayFormat("yyyy-MM-dd")
            try:
                end_dt = dt.strptime(task.end_date, "%Y-%m-%d")
                end_date_edit.setDate(QDate(end_dt.year, end_dt.month, end_dt.day))
            except:
                end_date_edit.setDate(QDate.currentDate())
            date_layout.addWidget(end_date_edit)

            form_layout.addRow("日期范围:", date_layout)

            # 股票代码列表（每行一个代码，方便编辑）
            symbols_text = QTextEdit()
            symbols_text.setPlainText("\n".join(task.symbols))  # ✅ 使用换行符分隔，更清晰
            symbols_text.setMaximumHeight(100)
            symbols_text.setPlaceholderText("每行一个股票代码，如：\n000001\n000002\n...")
            form_layout.addRow("股票代码:", symbols_text)

            # 批量大小
            batch_size_spin = QSpinBox()
            batch_size_spin.setRange(1, 1000)
            batch_size_spin.setValue(task.batch_size)
            form_layout.addRow("批量大小:", batch_size_spin)

            # 并发数
            workers_spin = QSpinBox()
            workers_spin.setRange(1, 32)
            workers_spin.setValue(task.max_workers)
            form_layout.addRow("并发数:", workers_spin)

            layout.addLayout(form_layout)

            # 按钮
            button_layout = QHBoxLayout()
            save_btn = QPushButton("保存")
            cancel_btn = QPushButton("取消")

            def save_changes():
                try:
                    # 🎯 构建任务名称（自动追加数据用途标记）
                    base_name = name_edit.text().strip()

                    # 获取数据用途标记
                    usage_display = data_usage_edit_combo.currentText()
                    tag_mapping = {
                        "通用场景": "[通用]",
                        "历史数据分析": "[历史]",
                        "回测验证": "[回测]",
                        "实时行情": "[实时]",
                        "实盘交易": "[实盘]"
                    }
                    usage_tag = tag_mapping.get(usage_display, "[通用]")

                    # 组合最终任务名
                    final_task_name = f"{base_name}{usage_tag}"

                    # 获取数据用途英文值
                    usage_mapping = {
                        "通用场景": "general",
                        "历史数据分析": "historical",
                        "回测验证": "backtest",
                        "实时行情": "realtime",
                        "实盘交易": "live_trading"
                    }
                    data_usage_value = usage_mapping.get(usage_display, "general")

                    # 更新任务配置
                    task.name = final_task_name  # ✅ 使用带标记的任务名
                    task.data_source = data_source_combo.currentText()
                    task.asset_type = asset_type_combo.currentText()
                    task.data_type = data_type_combo.currentText()

                    # 频率映射
                    freq_map = {
                        "日线": "daily", "周线": "weekly", "月线": "monthly",
                        "5分钟": "5min", "15分钟": "15min", "30分钟": "30min", "60分钟": "60min"
                    }
                    from core.importdata.import_config_manager import DataFrequency
                    freq_value = freq_map.get(frequency_combo.currentText(), "daily")
                    task.frequency = DataFrequency(freq_value) if hasattr(DataFrequency, freq_value.upper()) else DataFrequency.DAILY

                    # 日期
                    task.start_date = start_date_edit.date().toString("yyyy-MM-dd")
                    task.end_date = end_date_edit.date().toString("yyyy-MM-dd")

                    # 股票代码（支持换行或逗号分隔）
                    symbols_str = symbols_text.toPlainText().strip()
                    if symbols_str:
                        # ✅ 修复：先按换行分割，再按逗号分割，支持两种格式
                        symbols = []
                        for line in symbols_str.split('\n'):
                            line = line.strip()
                            if ',' in line:
                                # 如果包含逗号，按逗号分割
                                symbols.extend([s.strip() for s in line.split(',') if s.strip()])
                            elif line:
                                # 否则作为单个代码
                                symbols.append(line)
                        task.symbols = symbols
                    else:
                        task.symbols = []

                    # 批量参数
                    task.batch_size = batch_size_spin.value()
                    task.max_workers = workers_spin.value()

                    # 保存到配置管理器 (使用**kwargs方式)
                    success = self.config_manager.update_import_task(
                        task_id,
                        name=task.name,
                        data_usage=data_usage_value,  # 🆕 添加数据用途
                        data_source=task.data_source,
                        asset_type=task.asset_type,
                        data_type=task.data_type,
                        frequency=task.frequency,
                        start_date=task.start_date,
                        end_date=task.end_date,
                        symbols=task.symbols,
                        batch_size=task.batch_size,
                        max_workers=task.max_workers
                    )

                    if success:
                        QMessageBox.information(dialog, "成功", "任务更新成功")
                        # 刷新任务列表
                        self.refresh_task_list()
                        dialog.accept()
                    else:
                        QMessageBox.warning(dialog, "失败", "任务更新失败")

                except Exception as e:
                    logger.error(f"保存任务更改失败: {e}") if logger else None
                    QMessageBox.critical(dialog, "错误", f"保存失败: {e}")

            save_btn.clicked.connect(save_changes)
            cancel_btn.clicked.connect(dialog.reject)

            button_layout.addStretch()
            button_layout.addWidget(save_btn)
            button_layout.addWidget(cancel_btn)

            layout.addLayout(button_layout)

            # 显示对话框
            dialog.exec_()

        except Exception as e:
            logger.error(f"编辑任务失败: {e}") if logger else None
            import traceback
            logger.error(traceback.format_exc()) if logger else None
            QMessageBox.critical(self, "错误", f"编辑任务失败: {e}")

    def format_duration(self, seconds: float) -> str:
        """格式化持续时间"""
        try:
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                return f"{seconds/3600:.1f}h"
        except:
            return "0s"

    def _on_task_double_clicked(self, item):
        """任务双击处理"""
        try:
            if not item:
                return

            row = item.row()
            task_id = self.task_table.item(row, 0).data(Qt.UserRole)

            if task_id:
                self.view_task_details(task_id)

        except Exception as e:
            logger.error(f"处理任务双击失败: {e}") if logger else None

    # 适配器信号处理方化
    def on_adapter_task_updated(self, task_model: TaskStatusUIModel):
        """处理适配器任务状态更化"""
        try:
            # 更新任务列表中的对应化
            self._update_task_in_table(task_model)
        except Exception as e:
            logger.error(f"处理任务状态更新失败: {e}") if logger else None

    def on_adapter_ai_updated(self, ai_model: AIStatusUIModel):
        """处理适配器AI状态更化"""
        try:
            # 更新AI状态显化
            self._update_ai_status_display(ai_model)
        except Exception as e:
            logger.error(f"处理AI状态更新失败: {e}") if logger else None

    def on_adapter_performance_updated(self, perf_model: PerformanceUIModel):
        """处理适配器性能指标更新"""
        try:
            # 更新性能指标显示
            self._update_performance_display(perf_model)
        except Exception as e:
            logger.error(f"处理性能指标更新失败: {e}") if logger else None

    def on_adapter_quality_updated(self, quality_model: QualityUIModel):
        """处理适配器质量指标更化"""
        try:
            # 更新质量指标显示
            self._update_quality_display(quality_model)
        except Exception as e:
            logger.error(f"处理质量指标更新失败: {e}") if logger else None

    def on_service_status_changed(self, service_name: str, status: str):
        """处理服务状态变化"""
        try:
            logger.info(f"服务状态变化 {service_name} -> {status}") if logger else None
        except Exception as e:
            logger.error(f"处理服务状态变更失败: {e}") if logger else None

    def on_adapter_error(self, service_name: str, error_message: str):
        """处理适配器错化"""
        try:
            logger.error(f"适配器错化({service_name}): {error_message}") if logger else None
        except Exception as e:
            logger.error(f"处理适配器错误失败: {e}") if logger else None

    def on_state_changed(self, entity_type: str, entity_id: str, new_state):
        """处理状态变化"""
        try:
            logger.debug(f"状态变化 {entity_type}:{entity_id}") if logger else None
        except Exception as e:
            logger.error(f"处理状态变更失败: {e}") if logger else None

    def on_conflict_detected(self, conflict):
        """处理状态冲化"""
        try:
            logger.warning(f"检测到状态冲化 {conflict.entity_type}:{conflict.entity_id}") if logger else None
        except Exception as e:
            logger.error(f"处理状态冲突失败: {e}") if logger else None

    def on_sync_completed(self, entity_type: str, entity_id: str):
        """处理同步完成"""
        try:
            logger.debug(f"同步完成: {entity_type}:{entity_id}") if logger else None
        except Exception as e:
            logger.error(f"处理同步完成失败: {e}") if logger else None

    def on_sync_failed(self, entity_type: str, entity_id: str, error_message: str):
        """处理同步失败"""
        try:
            logger.error(f"同步失败 ({entity_type}:{entity_id}): {error_message}") if logger else None
        except Exception as e:
            logger.error(f"处理同步失败失败: {e}") if logger else None

    def _update_task_in_table(self, task_model: TaskStatusUIModel):
        """更新任务表格中的任务"""
        try:
            # 查找对应的任务行
            for row in range(self.task_table.rowCount()):
                task_id_item = self.task_table.item(row, 0)
                if task_id_item and task_model.task_id in task_id_item.text():
                    # 更新状态列
                    status_item = QTableWidgetItem(task_model.status)
                    self.task_table.setItem(row, 1, status_item)

                    # 更新进度化
                    progress_item = QTableWidgetItem(f"{task_model.progress:.1f}")
                    self.task_table.setItem(row, 2, progress_item)
                    break
        except Exception as e:
            logger.error(f"更新任务表格失败: {e}") if logger else None

    def _update_ai_status_display(self, ai_model: AIStatusUIModel):
        """更新AI状态显化"""
        pass

    def _update_performance_display(self, perf_model: PerformanceUIModel):
        """更新性能指标显示"""
        pass

    def _update_quality_display(self, quality_model: QualityUIModel):
        """更新质量指标显示"""
        pass

    def _create_resource_quota_panel(self) -> QWidget:
        """创建资源配额配置面板"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 批量大小
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 10000)
        self.batch_size_spin.setValue(1000)
        self.batch_size_spin.setToolTip("每批处理的记录数")
        layout.addRow("批量大小:", self.batch_size_spin)

        # 工作线程数
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 32)
        self.workers_spin.setValue(4)
        self.workers_spin.setToolTip("并行处理的线程数")
        layout.addRow("工作线程数:", self.workers_spin)

        # 内存限制
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(512, 16384)
        self.memory_limit_spin.setValue(2048)
        self.memory_limit_spin.setSuffix("MB")
        self.memory_limit_spin.setToolTip("内存使用限制")
        layout.addRow("内存限制:", self.memory_limit_spin)

        # 超时设置
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(60, 3600)
        self.timeout_spin.setValue(300)
        self.timeout_spin.setSuffix("秒")
        self.timeout_spin.setToolTip("任务执行超时时间")
        layout.addRow("执行超时:", self.timeout_spin)

        return widget

    def _create_execution_config_panel(self) -> QWidget:
        """创建执行配置面板"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 重试次数
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(3)
        self.retry_count_spin.setToolTip("失败重试次数")
        layout.addRow("重试次数:", self.retry_count_spin)

        # 错误处理策略
        self.error_strategy_combo = QComboBox()
        self.error_strategy_combo.addItems(["停止", "跳过", "重试"])
        self.error_strategy_combo.setCurrentText("跳过")
        self.error_strategy_combo.setToolTip("遇到错误时的处理策略")
        layout.addRow("错误处理:", self.error_strategy_combo)

        # 进度报告间隔（仅在高级配置中创建独立副本）
        # 如果主副本已存在，使用主副本的值；否则创建新副本
        if not hasattr(self, '_advanced_progress_interval_spin'):
            self._advanced_progress_interval_spin = QSpinBox()
            self._advanced_progress_interval_spin.setRange(1, 60)
            self._advanced_progress_interval_spin.setValue(5)
            self._advanced_progress_interval_spin.setSuffix("秒")
            self._advanced_progress_interval_spin.setToolTip("进度更新间隔")
        layout.addRow("进度间隔:", self._advanced_progress_interval_spin)

        return widget

    def validate_current_configuration(self):
        """验证当前配置"""
        try:
            # 验证基本信息
            task_name = self.task_name_edit.text().strip()
            if not task_name:
                QMessageBox.warning(self, "验证失败", "请输入任务名称")
                return

            symbols_text = self.symbols_edit.toPlainText().strip()
            if not symbols_text:
                QMessageBox.warning(self, "验证失败", "请输入股票代码")
                return

            symbols = [s.strip() for s in symbols_text.split('\n') if s.strip()]
            if len(symbols) == 0:
                QMessageBox.warning(self, "验证失败", "未检测到有效的股票代码")
                return

            # 验证数据源连接
            data_source = self.data_source_combo.currentText()
            if data_source == "通达信":
                # 验证通达信连接
                try:
                    from core.services.unified_data_manager import get_unified_data_manager
                    data_manager = get_unified_data_manager()
                    if data_manager and data_manager.test_connection():
                        connection_status = "连接正常"
                    else:
                        connection_status = "[ERROR] 连接失败"
                except Exception as e:
                    connection_status = f"[ERROR] 连接错误: {str(e)}"
            else:
                connection_status = "ℹ️ 未验证"

            # 显示验证结果
            result_text = f"""配置验证结果:

    基本信息:
    - 任务名称: {task_name}
    - 资产类型: {self.asset_type_combo.currentText()}
    - 数据类型: {self.data_type_combo.currentText()}
    - 数据频率: {self.frequency_combo.currentText()}
    - 股票代码: {len(symbols)} 个

    数据源配置:
    - 数据源: {data_source}
    - 连接状态: {connection_status}

    高级配置:
    - 批量大小: {self.batch_size_spin.value()}
    - 工作线程: {self.workers_spin.value()}

    AI功能:
    - AI优化: {'启用' if self.ai_optimization_cb.isChecked() else '[ERROR] 禁用'}
    - 自动调优: {'启用' if self.auto_tuning_cb.isChecked() else '[ERROR] 禁用'}
    - 分布式执行: {'启用' if self.distributed_cb.isChecked() else '[ERROR] 禁用'}
    - 智能缓存: {'启用' if self.caching_cb.isChecked() else '[ERROR] 禁用'}
    - 数据质量监控: {'启用' if self.quality_monitoring_cb.isChecked() else '[ERROR] 禁用'}

    实时写入:
    - 写入策略: {self.write_strategy_combo.currentText() if hasattr(self, 'write_strategy_combo') else '禁用写入'}
    - 性能监控: {'启用' if (hasattr(self, 'enable_perf_monitor_cb') and self.enable_perf_monitor_cb.isChecked()) else '禁用'}
    - 内存监控: {'启用' if (hasattr(self, 'enable_memory_monitor_cb') and self.enable_memory_monitor_cb.isChecked()) else '禁用'}
    """
            QMessageBox.information(self, "配置验证", result_text)

        except Exception as e:
            QMessageBox.critical(self, "验证失败", f"配置验证过程中发生错误: {str(e)}")

    def reset_configuration(self):
        """重置配置"""
        try:
            reply = QMessageBox.question(
                self, "确认重置",
                "确定要重置所有配置到默认值吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 重置基本信息
                self.task_name_edit.setText(f"导入任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                self.task_desc_edit.clear()
                self.asset_type_combo.setCurrentIndex(0)
                self.data_type_combo.setCurrentIndex(0)
                self.frequency_combo.setCurrentIndex(0)
                self.symbols_edit.clear()

                # 重置数据源配置
                self.data_source_combo.setCurrentIndex(0)
                self.start_date.setDate(QDate.currentDate().addMonths(-6))
                self.end_date.setDate(QDate.currentDate())

                # 重置合并后的高级配置
                # 资源配置
                if hasattr(self, 'batch_size_spin'):
                    self.batch_size_spin.setValue(1000)
                if hasattr(self, 'workers_spin'):
                    self.workers_spin.setValue(8)  # ✅ 优化：默认工作线程数从4增加到8
                if hasattr(self, 'memory_limit_spin'):
                    self.memory_limit_spin.setValue(2048)
                if hasattr(self, 'timeout_spin'):
                    self.timeout_spin.setValue(60)  # ✅ 优化：默认超时从300秒减少到60秒

                # 错误处理配置
                if hasattr(self, 'retry_count_spin'):
                    self.retry_count_spin.setValue(3)
                if hasattr(self, 'error_strategy_combo'):
                    self.error_strategy_combo.setCurrentText("跳过")
                if hasattr(self, 'progress_interval_spin'):
                    self.progress_interval_spin.setValue(5)
                if hasattr(self, 'validate_data_cb'):
                    self.validate_data_cb.setChecked(True)

                # 重置AI功能开关
                if hasattr(self, 'ai_optimization_cb'):
                    self.ai_optimization_cb.setChecked(True)
                if hasattr(self, 'auto_tuning_cb'):
                    self.auto_tuning_cb.setChecked(True)
                if hasattr(self, 'distributed_cb'):
                    self.distributed_cb.setChecked(True)
                if hasattr(self, 'caching_cb'):
                    self.caching_cb.setChecked(True)
                if hasattr(self, 'quality_monitoring_cb'):
                    self.quality_monitoring_cb.setChecked(True)

                # 重置实时写入配置
                if hasattr(self, 'write_strategy_combo'):
                    self.write_strategy_combo.setCurrentText("禁用写入")
                if hasattr(self, 'enable_perf_monitor_cb'):
                    self.enable_perf_monitor_cb.setChecked(True)
                if hasattr(self, 'enable_memory_monitor_cb'):
                    self.enable_memory_monitor_cb.setChecked(True)

                QMessageBox.information(self, "重置成功", "配置已重置到默认值")

        except Exception as e:
            QMessageBox.critical(self, "重置失败", f"重置配置时发生错误: {str(e)}")

    def on_asset_type_changed(self, asset_type: str):
        """资产类型变化处理"""
        try:
            # 根据资产类型调整数据类型选项
            if asset_type == "股票":
                self.data_type_combo.clear()
                self.data_type_combo.addItems(["K线数据", "分笔数据", "财务数据", "基本面数据"])
            elif asset_type == "期货":
                self.data_type_combo.clear()
                self.data_type_combo.addItems(["K线数据", "分笔数据", "持仓数据"])
            elif asset_type == "基金":
                self.data_type_combo.clear()
                self.data_type_combo.addItems(["K线数据", "净值数据", "持仓数据"])
            elif asset_type == "债券":
                self.data_type_combo.clear()
                self.data_type_combo.addItems(["K线数据", "收益率数据"])
            elif asset_type == "指数":
                self.data_type_combo.clear()
                self.data_type_combo.addItems(["K线数据", "成分股数据"])

            logger.debug(f"资产类型变化: {asset_type}") if logger else None

        except Exception as e:
            logger.error(f"处理资产类型变化失败: {e}") if logger else None

    def show_batch_selection_dialog(self):
        """显示批量选择对话框"""
        try:
            # 获取当前选择的资产类型
            asset_type = self.asset_type_combo.currentText() if hasattr(self, 'asset_type_combo') else "股票"

            # 创建并显示批量选择对话框
            dialog = BatchSelectionDialog(asset_type, self)
            if dialog.exec_() == QDialog.Accepted:
                # 获取选择的代码列表
                selected_codes = dialog.get_selected_codes()
                if selected_codes and hasattr(self, 'symbols_edit'):
                    # 将选择的代码添加到文本框
                    current_text = self.symbols_edit.toPlainText().strip()
                    new_codes = '\n'.join(selected_codes)

                    if current_text:
                        self.symbols_edit.setPlainText(current_text + '\n' + new_codes)
                    else:
                        self.symbols_edit.setPlainText(new_codes)

                    logger.info(f"批量选择完成，已添加 {len(selected_codes)} 个代码") if logger else None

        except Exception as e:
            logger.error(f"显示批量选择对话框失败: {e}") if logger else None
            if hasattr(self, 'parent') and callable(self.parent):
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.parent(),
                    "错误",
                    f"批量选择功能暂时不可用:\n{str(e)}"
                )

    def show_quick_selection_dialog(self):
        """显示快速选择对话框"""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QRadioButton

            # 创建快速选择对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("快速选择")
            dialog.setModal(True)
            dialog.resize(400, 300)

            layout = QVBoxLayout(dialog)

            # 标题
            title_label = QLabel("快速选择常用股票组合")
            title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
            layout.addWidget(title_label)

            # 预设选择组
            self.quick_selection_group = QButtonGroup(dialog)

            # 沪深300
            hs300_radio = QRadioButton("沪深300成分股")
            hs300_radio.setObjectName("hs300")
            self.quick_selection_group.addButton(hs300_radio)
            layout.addWidget(hs300_radio)

            # 中证500
            zz500_radio = QRadioButton("中证500成分股")
            zz500_radio.setObjectName("zz500")
            self.quick_selection_group.addButton(zz500_radio)
            layout.addWidget(zz500_radio)

            # 创业板50
            cyb50_radio = QRadioButton("创业板50成分股")
            cyb50_radio.setObjectName("cyb50")
            self.quick_selection_group.addButton(cyb50_radio)
            layout.addWidget(cyb50_radio)

            # 科创50
            kc50_radio = QRadioButton("科创50成分股")
            kc50_radio.setObjectName("kc50")
            self.quick_selection_group.addButton(kc50_radio)
            layout.addWidget(kc50_radio)

            # 热门股票
            hot_radio = QRadioButton("热门股票 (贵州茅台、腾讯控股、招商银行等)")
            hot_radio.setObjectName("hot")
            self.quick_selection_group.addButton(hot_radio)
            layout.addWidget(hot_radio)

            # 默认选择第一个
            hs300_radio.setChecked(True)

            layout.addStretch()

            # 按钮区域
            button_layout = QHBoxLayout()

            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)

            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(dialog.accept)
            ok_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            button_layout.addWidget(ok_btn)

            layout.addLayout(button_layout)

            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                selected_button = self.quick_selection_group.checkedButton()
                if selected_button and hasattr(self, 'symbols_edit'):
                    selection_type = selected_button.objectName()
                    codes = self._get_quick_selection_codes(selection_type)

                    if codes:
                        current_text = self.symbols_edit.toPlainText().strip()
                        new_codes = '\n'.join(codes)

                        if current_text:
                            self.symbols_edit.setPlainText(current_text + '\n' + new_codes)
                        else:
                            self.symbols_edit.setPlainText(new_codes)

                        logger.info(f"快速选择完成：{selection_type}，已添加 {len(codes)} 个代码") if logger else None

        except Exception as e:
            logger.error(f"显示快速选择对话框失败: {e}") if logger else None
            if hasattr(self, 'parent') and callable(self.parent):
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.parent(),
                    "错误",
                    f"快速选择功能暂时不可用:\n{str(e)}"
                )

    def _get_quick_selection_codes(self, selection_type: str) -> list:
        """获取快速选择的代码列表"""
        try:
            if selection_type == "hs300":
                # 沪深300部分代码示例
                return [
                    "000001", "000002", "000858", "000895", "000938",
                    "600000", "600036", "600519", "600887", "600900",
                    "000725", "002415", "300059", "300142", "300450"
                ]
            elif selection_type == "zz500":
                # 中证500部分代码示例
                return [
                    "000021", "000063", "000100", "000157", "000338",
                    "600009", "600015", "600028", "600031", "600048",
                    "002007", "002013", "002027", "002049", "002065"
                ]
            elif selection_type == "cyb50":
                # 创业板50部分代码示例
                return [
                    "300003", "300015", "300024", "300033", "300059",
                    "300122", "300142", "300347", "300408", "300450"
                ]
            elif selection_type == "kc50":
                # 科创50部分代码示例
                return [
                    "688001", "688005", "688009", "688012", "688016",
                    "688036", "688111", "688122", "688169", "688188"
                ]
            elif selection_type == "hot":
                # 热门股票示例
                return [
                    "600519",  # 贵州茅台
                    "000858",  # 五粮液
                    "600036",  # 招商银行
                    "000001",  # 平安银行
                    "000002",  # 万科A
                    "600887",  # 伊利股份
                    "000725",  # 京东方A
                    "002415",  # 海康威视
                    "300059",  # 东方财富
                    "300142"   # 沃森生物
                ]
            else:
                return []

        except Exception as e:
            logger.error(f"获取快速选择代码失败: {e}") if logger else None
            return []

    def _load_available_data_sources(self):
        """动态加载可用的数据源插件"""
        try:
            logger.info("开始动态加载数据源插件...") if logger else None

            # 方案1: 使用初始化时传入的plugin_manager（推荐）
            plugin_manager = None
            if hasattr(self, 'plugin_manager') and self.plugin_manager:
                plugin_manager = self.plugin_manager
                logger.info("✅ 使用初始化时传入的PluginManager") if logger else None

            # 方案2: 从容器获取
            if not plugin_manager:
                try:
                    from core.containers import get_service_container
                    container = get_service_container()
                    if container:
                        plugin_manager = container.get('plugin_manager')
                        if plugin_manager:
                            logger.info("从ServiceContainer获取PluginManager") if logger else None
                except Exception as e:
                    logger.debug(f"从容器获取PluginManager失败: {e}") if logger else None

            # 方案3: 从全局导入的PluginManager实例
            if not plugin_manager:
                try:
                    # 尝试从main模块获取（如果已经启动）
                    import sys
                    if 'main' in sys.modules:
                        main_module = sys.modules['main']
                        if hasattr(main_module, 'plugin_manager'):
                            plugin_manager = main_module.plugin_manager
                            logger.info("从main模块获取PluginManager") if logger else None
                except Exception as e:
                    logger.debug(f"从main模块获取PluginManager失败: {e}") if logger else None

            if plugin_manager:
                # 获取所有数据源插件 - 使用与插件管理UI相同的方法
                data_source_plugins = []

                # 方法1: 尝试get_all_enhanced_plugins()（优先）
                enhanced_plugins = None
                if hasattr(plugin_manager, 'get_all_enhanced_plugins'):
                    try:
                        enhanced_plugins = plugin_manager.get_all_enhanced_plugins()
                        logger.info(f"通过get_all_enhanced_plugins获取到 {len(enhanced_plugins) if enhanced_plugins else 0} 个插件") if logger else None
                    except Exception as e:
                        logger.debug(f"get_all_enhanced_plugins失败: {e}") if logger else None

                # 方法2: 尝试get_all_plugins()
                if not enhanced_plugins:
                    if hasattr(plugin_manager, 'get_all_plugins'):
                        try:
                            all_plugins = plugin_manager.get_all_plugins()
                            logger.info(f"通过get_all_plugins获取到 {len(all_plugins) if all_plugins else 0} 个插件") if logger else None

                            # 转换为enhanced格式
                            if all_plugins:
                                for plugin_name, plugin_instance in all_plugins.items():
                                    # 筛选数据源插件 - 只匹配plugins/data_sources/目录下的插件
                                    if (plugin_name.startswith('data_sources.') and
                                            'sentiment' not in plugin_name.lower()):
                                        display_name = getattr(plugin_instance, 'name', plugin_name)

                                        data_source_plugins.append({
                                            'name': plugin_name,
                                            'display_name': display_name,
                                            'info': plugin_instance
                                        })
                                        logger.debug(f"找到数据源插件: {plugin_name} -> {display_name}") if logger else None
                        except Exception as e:
                            logger.debug(f"get_all_plugins失败: {e}") if logger else None

                # 方法3: 使用enhanced_plugins（如果获取到了）
                if enhanced_plugins:
                    for plugin_name, plugin_info in enhanced_plugins.items():
                        # 筛选数据源插件 - 只匹配plugins/data_sources/目录下的插件
                        if (plugin_name.startswith('data_sources.') and
                                'sentiment' not in plugin_name.lower()):
                            display_name = plugin_info.name if hasattr(plugin_info, 'name') else plugin_name

                            data_source_plugins.append({
                                'name': plugin_name,
                                'display_name': display_name,
                                'info': plugin_info
                            })
                            logger.debug(f"找到数据源插件: {plugin_name} -> {display_name}") if logger else None

                if data_source_plugins:
                    # 按显示名称排序
                    data_source_plugins.sort(key=lambda x: x['display_name'])

                    # 填充下拉列表
                    self.data_source_combo.clear()
                    self.data_source_mapping = {}  # 映射：display_name -> plugin_name

                    for plugin in data_source_plugins:
                        self.data_source_combo.addItem(plugin['display_name'])
                        self.data_source_mapping[plugin['display_name']] = plugin['name']

                    logger.info(f"✅ 成功加载 {len(data_source_plugins)} 个数据源插件到UI") if logger else None
                    return True
                else:
                    logger.warning("PluginManager中没有找到data_sources插件") if logger else None
            else:
                logger.warning("PluginManager不可用或没有plugins属性") if logger else None

            # 备用方案：使用默认列表
            logger.warning("⚠️ 无法获取插件管理器或无可用插件，使用默认数据源列表（4个）") if logger else None
            self._load_default_data_sources()
            return False

        except Exception as e:
            logger.error(f"❌ 加载数据源失败: {e}", exc_info=True) if logger else None
            self._load_default_data_sources()
            return False

    def _load_default_data_sources(self):
        """加载默认数据源列表（备用）"""
        default_sources = {
            "AKShare数据源插件": "data_sources.stock.akshare_plugin",  # ✅ 修复：添加stock层级并使用完整名称
            "东方财富股票数据源插件": "data_sources.stock.eastmoney_plugin",  # ✅ 修复：添加stock层级并使用完整名称
            "新浪股票数据源": "data_sources.stock.sina_plugin",  # ✅ 修复：添加stock层级
            "通达信股票数据源": "data_sources.stock.tongdaxin_plugin"  # ✅ 修复：添加stock层级
        }

        self.data_source_combo.clear()
        self.data_source_mapping = default_sources

        for display_name in default_sources.keys():
            self.data_source_combo.addItem(display_name)

        logger.info(f"使用默认数据源列表: {len(default_sources)} 个") if logger else None

    def showEvent(self, event):
        """UI显示时重新加载数据源插件列表"""
        super().showEvent(event)

        try:
            # 只在首次显示时加载，避免重复加载
            if not hasattr(self, '_data_sources_loaded'):
                logger.info("UI首次显示，重新加载数据源插件列表") if logger else None
                self._load_available_data_sources()
                self._data_sources_loaded = True
        except Exception as e:
            logger.error(f"showEvent加载数据源失败: {e}") if logger else None

    def _initialize_batch_buttons(self):
        """初始化批量按钮状态"""
        try:
            # 这个方法用于初始化批量选择相关按钮的状态
            # 目前暂时保持空实现，可以根据需要添加初始化逻辑
            pass
        except Exception as e:
            logger.error(f"初始化批量按钮失败: {e}") if logger else None

    # ==================== 实时写入事件处理方法 ====================

    def on_realtime_config_changed(self, config: Dict[str, Any]):
        """实时写入配置变更"""
        try:
            logger.info(f"实时写入配置已变更: {config}") if logger else None
            self.current_realtime_config = config
        except Exception as e:
            logger.error(f"处理配置变更失败: {e}") if logger else None

    def on_stop_download(self):
        """停止下载"""
        try:
            # ✅ 根因修复：优先检查import_engine是否可用
            if not CORE_AVAILABLE or not self.import_engine:
                QMessageBox.warning(
                    self, "功能不可用",
                    "数据导入引擎未初始化，无法停止任务。\n请检查核心组件是否正确加载。"
                )
                logger.error("停止下载失败: import_engine未初始化") if logger else None
                return

            if not hasattr(self, 'current_task_id') or not self.current_task_id:
                QMessageBox.warning(self, "提示", "没有正在运行的任务")
                return

            # 确认对话框
            reply = QMessageBox.question(
                self, '确认',
                f'确定要停止当前下载任务吗？\n任务ID: {self.current_task_id}',
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 调用后台停止方法
                try:
                    success = self.import_engine.stop_task(self.current_task_id)
                    if success:
                        self.log_message(f"✅ 任务 {self.current_task_id} 已停止")
                        logger.info(f"K线下载任务已停止: {self.current_task_id}") if logger else None

                        # 通知监控面板任务已停止
                        if hasattr(self, 'download_monitoring'):
                            self.download_monitoring.update_progress({
                                'progress': 0.0,
                                'message': '任务已停止',
                                'task_id': self.current_task_id,
                                'task_name': self.task_name_edit.text()
                            })

                        # 清除当前任务ID
                        self.current_task_id = None
                    else:
                        QMessageBox.warning(self, "错误", "停止任务失败，任务可能已完成或不存在")
                        logger.warning(f"停止任务失败: {self.current_task_id}") if logger else None
                except AttributeError as ae:
                    error_msg = f"导入引擎缺少stop_task方法: {ae}"
                    logger.error(error_msg) if logger else None
                    QMessageBox.critical(self, "错误", error_msg)
                except Exception as te:
                    error_msg = f"调用stop_task时发生异常: {te}"
                    logger.error(error_msg) if logger else None
                    QMessageBox.critical(self, "错误", error_msg)
        except Exception as e:
            logger.error(f"停止下载失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"停止失败: {str(e)}")

    def on_write_strategy_changed(self, strategy):
        """写入策略变更处理"""
        try:
            logger.info(f"写入策略已变更: {strategy}") if logger else None

            # 根据策略启用/禁用相关控制
            if strategy == "禁用写入":
                # 禁用所有写入相关控制
                if hasattr(self, 'realtime_pause_btn'):
                    self.realtime_pause_btn.setEnabled(False)
                if hasattr(self, 'realtime_resume_btn'):
                    self.realtime_resume_btn.setEnabled(False)
                if hasattr(self, 'realtime_cancel_btn'):
                    self.realtime_cancel_btn.setEnabled(False)
                if hasattr(self, 'enable_perf_monitor_cb'):
                    self.enable_perf_monitor_cb.setEnabled(False)
                if hasattr(self, 'enable_memory_monitor_cb'):
                    self.enable_memory_monitor_cb.setEnabled(False)
                if hasattr(self, 'realtime_status_label'):
                    self.realtime_status_label.setText("状态: 禁用")
                    self.realtime_status_label.setStyleSheet("color: gray; font-weight: bold;")
            else:
                # 启用写入相关控制（在未运行时仍然禁用按钮，但启用监控选项）
                if hasattr(self, 'enable_perf_monitor_cb'):
                    self.enable_perf_monitor_cb.setEnabled(True)
                if hasattr(self, 'enable_memory_monitor_cb'):
                    self.enable_memory_monitor_cb.setEnabled(True)
                if hasattr(self, 'realtime_status_label'):
                    if strategy == "实时写入":
                        self.realtime_status_label.setText("状态: 实时模式（未运行）")
                        self.realtime_status_label.setStyleSheet("color: navy; font-weight: bold;")
                    elif strategy == "批量写入":
                        self.realtime_status_label.setText("状态: 批量模式（未运行）")
                        self.realtime_status_label.setStyleSheet("color: navy; font-weight: bold;")
                    elif strategy == "自适应":
                        self.realtime_status_label.setText("状态: 自适应模式（未运行）")
                        self.realtime_status_label.setStyleSheet("color: navy; font-weight: bold;")
        except Exception as e:
            logger.error(f"处理写入策略变更失败: {e}") if logger else None

    def _on_mode_button_clicked(self, button):
        """处理下载模式单选按钮点击"""
        try:
            mode_value = button.property("mode_value")
            mode_text = button.text()

            self.current_download_mode = mode_value
            logger.info(f"下载模式已变更: {mode_text} ({mode_value})") if logger else None

            # 根据模式显示/隐藏相应的配置选项
            if mode_value == "incremental":  # 增量下载
                self.incremental_days_label.setVisible(True)
                self.incremental_days_spin.setVisible(True)
                self.completion_strategy_label.setVisible(False)
                self.completion_strategy_combo.setVisible(False)
                self.gap_threshold_label.setVisible(False)
                self.gap_threshold_spin.setVisible(False)
            elif mode_value == "smart_fill":  # 智能补全
                self.incremental_days_label.setVisible(False)
                self.incremental_days_spin.setVisible(False)
                self.completion_strategy_label.setVisible(True)
                self.completion_strategy_combo.setVisible(True)
                self.gap_threshold_label.setVisible(False)
                self.gap_threshold_spin.setVisible(False)
            elif mode_value == "gap_fill":  # 间隙填充
                self.incremental_days_label.setVisible(False)
                self.incremental_days_spin.setVisible(False)
                self.completion_strategy_label.setVisible(False)
                self.completion_strategy_combo.setVisible(False)
                self.gap_threshold_label.setVisible(True)
                self.gap_threshold_spin.setVisible(True)
            else:  # 全量下载
                self.incremental_days_label.setVisible(False)
                self.incremental_days_spin.setVisible(False)
                self.completion_strategy_label.setVisible(False)
                self.completion_strategy_combo.setVisible(False)
                self.gap_threshold_label.setVisible(False)
                self.gap_threshold_spin.setVisible(False)

            # 更新日期范围的提示信息
            if mode_value == "incremental":
                tooltip_text = "建议设置为当前日期前N天，仅下载缺失数据"
            elif mode_value == "smart_fill":
                tooltip_text = "建议设置为较长时间范围，以便检测数据间隙"
            elif mode_value == "gap_fill":
                tooltip_text = "建议设置包含预期数据缺失的日期范围"
            else:  # 全量下载
                tooltip_text = "设置需要下载的完整时间范围"

            # 更新日期选择器的提示
            self.start_date.setToolTip(f"开始日期（{mode_text}模式）\n{tooltip_text}")
            self.end_date.setToolTip(f"结束日期（{mode_text}模式）\n{tooltip_text}")

        except Exception as e:
            logger.error(f"处理下载模式变更失败: {e}") if logger else None

    def on_download_mode_changed(self, mode: str):
        """下载模式变更处理"""
        try:
            logger.info(f"下载模式已变更: {mode}") if logger else None

            # 根据模式显示/隐藏相应的配置选项
            if mode == "增量下载":
                self.incremental_days_spin.setVisible(True)
                self.completion_strategy_combo.setVisible(False)
                self.gap_threshold_spin.setVisible(False)
            elif mode == "智能补全":
                self.incremental_days_spin.setVisible(False)
                self.completion_strategy_combo.setVisible(True)
                self.gap_threshold_spin.setVisible(False)
            elif mode == "间隙填充":
                self.incremental_days_spin.setVisible(False)
                self.completion_strategy_combo.setVisible(False)
                self.gap_threshold_spin.setVisible(True)
            else:  # 全量下载
                self.incremental_days_spin.setVisible(False)
                self.completion_strategy_combo.setVisible(False)
                self.gap_threshold_spin.setVisible(False)

            # 更新日期范围的提示信息
            if mode == "增量下载":
                tooltip_text = "建议设置为当前日期前N天，仅下载缺失数据"
            elif mode == "智能补全":
                tooltip_text = "建议设置为较长时间范围，以便检测数据间隙"
            elif mode == "间隙填充":
                tooltip_text = "建议设置包含预期数据缺失的日期范围"
            else:  # 全量下载
                tooltip_text = "设置需要下载的完整时间范围"

            # 更新日期选择器的提示
            self.start_date.setToolTip(f"开始日期（{mode}模式）\n{tooltip_text}")
            self.end_date.setToolTip(f"结束日期（{mode}模式）\n{tooltip_text}")

        except Exception as e:
            logger.error(f"处理下载模式变更失败: {e}") if logger else None

    def _register_write_event_handlers(self):
        """注册实时写入事件处理器【修复】"""
        try:
            from core.events import get_event_bus
            from core.events.realtime_write_events import (
                WriteStartedEvent, WriteProgressEvent, WriteCompletedEvent, WriteErrorEvent
            )
            from core.services.realtime_write_event_handlers import get_write_event_handlers
            from datetime import datetime

            event_bus = get_event_bus()
            write_handlers = get_write_event_handlers()

            if not event_bus or not write_handlers:
                return

            def on_ui_update(event_type, event):
                """【修复】实现实时UI更新回调（使用融合后的按钮）"""
                try:
                    if event_type == 'write_started':
                        logger.info(f"[UI] 写入开始") if logger else None
                        # 更新左侧控制按钮状态
                        if hasattr(self, 'realtime_pause_btn'):
                            self.realtime_pause_btn.setEnabled(True)
                        if hasattr(self, 'realtime_cancel_btn'):
                            self.realtime_cancel_btn.setEnabled(True)
                        if hasattr(self, 'realtime_status_label'):
                            self.realtime_status_label.setText("状态: 运行中")
                            self.realtime_status_label.setStyleSheet("color: blue; font-weight: bold;")

                    elif event_type == 'write_progress':
                        # 【修复】更新监控面板的进度信息
                        if hasattr(self, 'realtime_monitoring') and self.realtime_monitoring:
                            # 更新进度条
                            self.realtime_monitoring.progress_bar.setValue(int(event.progress))

                            # 更新速度标签
                            self.realtime_monitoring.speed_label.setText(f"{event.write_speed:.0f} 条/秒")

                            # 更新成功计数
                            self.realtime_monitoring.success_label.setText(str(event.success_count))

                            # 更新失败计数
                            self.realtime_monitoring.failure_label.setText(str(event.failure_count))

                            logger.debug(f"[UI] 更新进度: {event.progress:.1f}%, 速度: {event.write_speed:.0f}条/秒") if logger else None

                    elif event_type == 'write_completed':
                        logger.info(f"[UI] 写入完成") if logger else None
                        # 更新左侧控制按钮状态
                        if hasattr(self, 'realtime_pause_btn'):
                            self.realtime_pause_btn.setEnabled(False)
                        if hasattr(self, 'realtime_resume_btn'):
                            self.realtime_resume_btn.setEnabled(False)
                        if hasattr(self, 'realtime_cancel_btn'):
                            self.realtime_cancel_btn.setEnabled(False)
                        if hasattr(self, 'realtime_status_label'):
                            self.realtime_status_label.setText("状态: 已完成")
                            self.realtime_status_label.setStyleSheet("color: green; font-weight: bold;")

                    elif event_type == 'write_error':
                        # 【修复】添加错误到错误日志表
                        if hasattr(self, 'realtime_monitoring') and self.realtime_monitoring:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            self.realtime_monitoring.add_error(
                                timestamp=timestamp,
                                symbol=event.symbol,
                                error_type=event.error_type,
                                error_msg=event.error
                            )
                            logger.warning(f"[UI] 错误已添加: {event.symbol} - {event.error_type}") if logger else None

                except Exception as e:
                    logger.error(f"[UI] 回调处理失败: {e}") if logger else None

            write_handlers.ui_callback = on_ui_update
            event_bus.subscribe(WriteStartedEvent, write_handlers.on_write_started)
            event_bus.subscribe(WriteProgressEvent, write_handlers.on_write_progress)
            event_bus.subscribe(WriteCompletedEvent, write_handlers.on_write_completed)
            event_bus.subscribe(WriteErrorEvent, write_handlers.on_write_error)

            logger.info("实时写入事件处理器已注册") if logger else None
        except Exception as e:
            logger.warning(f"注册实时写入事件处理器失败: {e}") if logger else None

    def _get_asset_type_value(self):
        """获取资产类型值"""
        try:
            # 获取UI中选中的资产类型中文名称
            display_name = self.asset_type_combo.currentText()

            # ✅ 使用工具函数将中文名称转换为AssetType枚举
            from core.ui_asset_type_utils import parse_asset_type_from_combo
            asset_type_enum = parse_asset_type_from_combo(display_name)

            # 返回枚举值字符串（如"stock_a"）而不是枚举对象
            # 这样ImportTaskConfig可以直接存储字符串
            return asset_type_enum.value

        except Exception as e:
            logger.error(f"获取资产类型值失败: {e}，使用默认值 stock_a") if logger else None
            return "stock_a"  # 默认值

    def _get_data_usage_value(self):
        """
        获取数据用途值（将中文显示名称转换为英文枚举值）

        Returns:
            str: 数据用途枚举值 ('general', 'historical', 'backtest', 'realtime', 'live_trading')
        """
        try:
            display_name = self.data_usage_combo.currentText()

            # 中文显示名称 → 英文枚举值映射
            usage_mapping = {
                "通用场景": "general",
                "历史数据分析": "historical",
                "回测验证": "backtest",
                "实时行情": "realtime",
                "实盘交易": "live_trading"
            }

            return usage_mapping.get(display_name, "general")

        except Exception as e:
            logger.error(f"获取数据用途值失败: {e}，使用默认值 general") if logger else None
            return "general"

    def _get_data_usage_tag(self):
        """
        获取数据用途的中文标记（用于追加到任务名）

        Returns:
            str: 用途标记，如 "[通用]", "[回测]", "[实盘]"
        """
        try:
            display_name = self.data_usage_combo.currentText()

            # 提取简短的中文标记
            tag_mapping = {
                "通用场景": "[通用]",
                "历史数据分析": "[历史]",
                "回测验证": "[回测]",
                "实时行情": "[实时]",
                "实盘交易": "[实盘]"
            }

            return tag_mapping.get(display_name, "[通用]")

        except Exception as e:
            logger.error(f"获取数据用途标记失败: {e}") if logger else None
            return "[通用]"


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 05px 05px;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
            border-radius: 5px;
        }
        QTabBar::tab {
            background: #f0f0f0;
            border: 1px solid #cccccc;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #4a90e2;
            color: white;
        }
    """)

    widget = EnhancedDataImportWidget()
    widget.show()

    sys.exit(app.exec_())
