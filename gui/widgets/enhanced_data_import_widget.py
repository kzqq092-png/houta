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
    QSlider, QDoubleSpinBox, QLCDNumber
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QDate, QSize,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
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


class BatchSelectionDialog(QDialog):
    """批量选择对话化"""

    def __init__(self, asset_type: str, parent=None):
        super().__init__(parent)
        self.asset_type = asset_type
        self.selected_codes = []

        self.setWindowTitle(f"批量选择{asset_type}代码")
        self.setModal(True)
        self.resize(800, 600)

        self.setup_ui()
        self.load_data()

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

        # 分类选择区域（仅股票化
        if self.asset_type == "股票":
            category_layout = QHBoxLayout()
            category_layout.addWidget(QLabel("📂 分类:"))

            self.category_combo = QComboBox()
            self.category_combo.addItems(["全部", "银行", "地产", "电力", "白酒", "医药", "科技", "制造业", "沪深300", "中证500", "创业化0"])
            self.category_combo.currentTextChanged.connect(self.filter_by_category)
            category_layout.addWidget(self.category_combo)

            category_layout.addStretch()
            layout.addLayout(category_layout)

        # 列表区域
        self.item_list = QTableWidget()
        self.item_list.setColumnCount(3)
        self.item_list.setHorizontalHeaderLabels(["选择", "代码", "名称"])

        # 设置列宽
        header = self.item_list.horizontalHeader()
        header.setStretchLastSection(True)
        self.item_list.setColumnWidth(0, 60)
        self.item_list.setColumnWidth(1, 100)

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

    def load_data(self):
        """加载数据"""
        try:
            # 根据资产类型加载不同的数化
            if self.asset_type == "股票":
                self.all_items = self.get_stock_data()
            elif self.asset_type == "指数":
                self.all_items = self.get_index_data()
            elif self.asset_type == "期货":
                self.all_items = self.get_futures_data()
            elif self.asset_type == "基金":
                self.all_items = self.get_fund_data()
            elif self.asset_type == "债券":
                self.all_items = self.get_bond_data()
            else:
                self.all_items = []

            self.populate_table(self.all_items)

        except Exception as e:
            logger.error(f"加载{self.asset_type}数据失败: {e}") if logger else None
            self.all_items = []

    def get_stock_data(self):
        """获取股票数据 - 异步版本避免UI卡顿"""
        try:
            # 首先尝试使用统一插件数据管理器（最新架构）
            from core.services.uni_plugin_data_manager import get_uni_plugin_data_manager

            uni_manager = get_uni_plugin_data_manager()
            if uni_manager:
                # 显示进度对话框
                from PyQt5.QtWidgets import QProgressDialog
                from PyQt5.QtCore import Qt, QTimer

                progress = QProgressDialog("正在获取股票数据...", "取消", 0, 0, self)
                progress.setWindowTitle("数据加载")
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(1000)  # 1秒后显示
                progress.setValue(0)
                progress.show()

                # 记录开始时间
                start_time = datetime.now()

                # 通过统一插件数据管理器获取股票列表
                stock_list_data = uni_manager.get_stock_list()

                # 计算耗时
                elapsed = (datetime.now() - start_time).total_seconds()

                progress.close()

                if stock_list_data:
                    logger.info(f"通过统一插件数据管理器成功获取最新股票数据: {len(stock_list_data)} 只股票，耗时 {elapsed:.2f}秒") if logger else None
                    return stock_list_data

            # 备用方案：使用原有统一数据管理器
            from core.services.unified_data_manager import get_unified_data_manager

            data_manager = get_unified_data_manager()
            if data_manager:
                # 确保TET功能开启
                if hasattr(data_manager, 'tet_enabled'):
                    if not data_manager.tet_enabled:
                        logger.info("启用TET数据管道以获取最新股票数据") if logger else None
                        data_manager.tet_enabled = True

                # 获取股票列表DataFrame - 这里会优先使用TET管道
                stock_df = data_manager.get_stock_list()
                if not stock_df.empty:
                    # 转换为所需格式
                    stock_list = []
                    for _, row in stock_df.iterrows():
                        stock_info = {
                            "code": row.get('code', ''),
                            "name": row.get('name', ''),
                            "category": row.get('industry', '其他')
                        }
                        stock_list.append(stock_info)
                    logger.info(f"通过TET管道成功获取最新股票数据: {len(stock_list)} 只股票") if logger else None
                    return stock_list

            # 最后备用方案：使用股票服务
            from core.services.stock_service import StockService
            from core.containers import get_service_container

            container = get_service_container()
            if container:
                stock_service = container.resolve(StockService)
                if stock_service:
                    stock_list_data = stock_service.get_stock_list()
                    if stock_list_data:
                        # 转换格式
                        stock_list = []
                        for stock in stock_list_data:
                            stock_info = {
                                "code": stock.get('code', ''),
                                "name": stock.get('name', ''),
                                "category": stock.get('industry', '其他')
                            }
                            stock_list.append(stock_info)
                        logger.info(f"通过股票服务获取数据: {len(stock_list)} 只股票") if logger else None
                        return stock_list

            # 最后备用方案
            logger.warning("无法获取真实股票数据，返回空列表") if logger else None
            return []

        except Exception as e:
            logger.error(f"获取股票数据失败: {e}") if logger else None
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
        """填充表格"""
        self.item_list.setRowCount(len(items))

        for row, item in enumerate(items):
            # 选择
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.update_selection)
            self.item_list.setCellWidget(row, 0, checkbox)

            # 代码
            self.item_list.setItem(row, 1, QTableWidgetItem(item["code"]))

            # 名称
            self.item_list.setItem(row, 2, QTableWidgetItem(item["name"]))

        self.update_stats()

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

    def filter_by_category(self, category):
        """按分类过滤"""
        if category == "全部":
            filtered_items = self.all_items
        else:
            # 根据分类映射
            category_mapping = {
                "银行": ["银行"],
                "地产": ["地产"],
                "电力": ["电力"],
                "白酒": ["白酒"],
                "医药": ["医药"],
                "科技": ["科技"],
                "制造业": ["制造业"],
                "沪深300": ["沪深300"],
                "中证500": ["中证500"],
                "创业化0": ["创业化0"]
            }

            target_categories = category_mapping.get(category, [category])
            filtered_items = [
                item for item in self.all_items
                if item.get("category") in target_categories
            ]

        self.populate_table(filtered_items)

    def select_all(self):
        """全化"""
        for row in range(self.item_list.rowCount()):
            checkbox = self.item_list.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)

    def clear_all(self):
        """清空选择"""
        for row in range(self.item_list.rowCount()):
            checkbox = self.item_list.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)

    def update_selection(self):
        """更新选择状态"""
        self.update_stats()

    def update_stats(self):
        """更新统计信息"""
        total = self.item_list.rowCount()
        selected = 0
        for row in range(total):
            checkbox = self.item_list.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected += 1
        self.stats_label.setText(f"共 {total} 项，已选择 {selected} 项")

    def get_selected_codes(self):
        """获取选中的代码"""
        selected_codes = []

        for row in range(self.item_list.rowCount()):
            checkbox = self.item_list.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                code_item = self.item_list.item(row, 1)
                if code_item:
                    selected_codes.append(code_item.text())

        return selected_codes


class EnhancedDataImportWidget(QWidget):
    """增强版数据导入主界面"""

    # 信号定义
    task_started = pyqtSignal(str)  # 任务开化
    task_completed = pyqtSignal(str, object)  # 任务完成
    task_failed = pyqtSignal(str, str)  # 任务失败

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化核心组化
        self.import_engine = None
        self.config_manager = None
        self.ui_adapter = None
        self.ui_synchronizer = None

        # 初始化主题系统
        self.theme_manager = None
        if THEME_AVAILABLE:
            try:
                from utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                self.theme_manager = get_theme_manager(config_manager)
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
                max_workers=4,
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
                self.workers_spin.setValue(4)
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
        group.setFont(QFont("Arial", 10, QFont.Bold))
        main_layout = QVBoxLayout(group)

        # 创建滚动区域以容纳所有配置
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(700)  # 设置合理的最小高度
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

        # 资产类型
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems(["股票", "期货", "基金", "债券", "指数"])
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

        # ==================== 第二部分：代码选择 ====================
        symbols_group = QGroupBox("🏷️ 股票选择")
        symbols_layout = QVBoxLayout(symbols_group)

        # 批量选择按钮区域
        batch_buttons_layout = QHBoxLayout()

        self.batch_select_btn = QPushButton("📦 批量选择")
        self.batch_select_btn.clicked.connect(self.show_batch_selection_dialog)
        batch_buttons_layout.addWidget(self.batch_select_btn)

        # 快速选择按钮
        self.quick_select_btn = QPushButton("快速选择")
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

        # ==================== 第三部分：数据源配置 ====================
        datasource_group = QGroupBox("🔌 数据源配置")
        datasource_layout = QFormLayout(datasource_group)

        # 数据源选择
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["通达信", "东方财富", "新浪财经", "腾讯财经"])
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
        self.workers_spin.setValue(4)
        self.workers_spin.setToolTip("并行处理的线程数")
        resource_layout.addRow("工作线程数:", self.workers_spin)

        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(512, 16384)
        self.memory_limit_spin.setValue(2048)
        self.memory_limit_spin.setSuffix("MB")
        self.memory_limit_spin.setToolTip("内存使用限制")
        resource_layout.addRow("内存限制:", self.memory_limit_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(60, 3600)
        self.timeout_spin.setValue(300)
        self.timeout_spin.setSuffix("秒")
        self.timeout_spin.setToolTip("单个请求超时时间")
        resource_layout.addRow("超时设置:", self.timeout_spin)

        execution_layout.addWidget(resource_config)

        # 右侧：错误处理配置
        error_config = QGroupBox("⚠️ 错误处理")
        error_layout = QFormLayout(error_config)

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
        error_layout.addRow("进度间隔:", self.progress_interval_spin)

        execution_layout.addWidget(error_config)

        content_layout.addWidget(execution_group)

        # ==================== 第五部分：智能化功能 ====================
        ai_features_group = QGroupBox("🤖 智能化功能")
        ai_layout = QVBoxLayout(ai_features_group)

        # 创建两列布局
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
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems(["股票", "期货", "基金", "债券", "指数"])
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

        # 数据源选择
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["通达信", "东方财富", "新浪财经", "腾讯财经"])
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
        self.workers_spin.setValue(4)
        self.workers_spin.setToolTip("并行处理的线程数")
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
        self.timeout_spin.setValue(300)
        self.timeout_spin.setSuffix("秒")
        self.timeout_spin.setToolTip("单个请求超时时间")
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

        # 进度报告间隔
        self.progress_interval_spin = QSpinBox()
        self.progress_interval_spin.setRange(1, 60)
        self.progress_interval_spin.setValue(5)
        self.progress_interval_spin.setSuffix("秒")
        self.progress_interval_spin.setToolTip("进度更新间隔")
        error_layout.addRow("进度间隔:", self.progress_interval_spin)

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

        # 数据源选择
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["通达信", "东方财富", "新浪财经", "腾讯财经"])
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
        """创建任务操作组"""
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

        # 创建选项化
        self.monitor_tabs = QTabWidget()

        # 任务管理选项卡（集成增强功能化
        task_management_tab = self.create_enhanced_task_management_tab()
        self.monitor_tabs.addTab(task_management_tab, "任务管理")

        # AI功能控制面板选项卡化
        ai_control_tab = self.create_ai_control_panel_tab()
        self.monitor_tabs.addTab(ai_control_tab, "AI控制面板")

        # 分布式状态选项卡化
        distributed_tab = self.create_distributed_status_tab()
        self.monitor_tabs.addTab(distributed_tab, "分布式状化")

        # 数据质量选项化
        quality_tab = self.create_quality_status_tab()
        self.monitor_tabs.addTab(quality_tab, "数据质量")

        layout.addWidget(self.monitor_tabs)

        return widget

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

            # 创建任务配置
            # 频率映射
            freq_map = {
                "日线": DataFrequency.DAILY,
                "周线": DataFrequency.WEEKLY,
                "月线": DataFrequency.MONTHLY,
                "5分钟": DataFrequency.MINUTE_5,
                "15分钟": DataFrequency.MINUTE_15,
                "30分钟": DataFrequency.MINUTE_30,
                "60分钟": DataFrequency.HOUR_1}

            task_config = ImportTaskConfig(
                task_id=f"task_{int(datetime.now().timestamp())}",
                name=task_name,
                symbols=symbols,
                data_source=self.data_source_combo.currentText(),
                asset_type=self.asset_type_combo.currentText(),
                data_type=self.data_type_combo.currentText() if hasattr(self, 'data_type_combo') else "K线数据",  # 从UI读取数据类型
                frequency=freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY),
                mode=ImportMode.MANUAL,  # 默认手动模式
                batch_size=self.batch_size_spin.value(),
                max_workers=self.workers_spin.value(),
                start_date=self.start_date.date().toString("yyyy-MM-dd"),
                end_date=self.end_date.date().toString("yyyy-MM-dd"),
                retry_count=self.retry_count_spin.value() if hasattr(self, 'retry_count_spin') else 3,
                error_strategy=self.error_strategy_combo.currentText() if hasattr(self, 'error_strategy_combo') else "跳过",
                memory_limit=self.memory_limit_spin.value() if hasattr(self, 'memory_limit_spin') else 2048,
                timeout=self.timeout_spin.value() if hasattr(self, 'timeout_spin') else 300,
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
        self.log_message(f"进度更新: {progress:.1} - {message}")

    def on_task_completed(self, task_id: str, result):
        """任务完成回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(100)
        if hasattr(self, 'progress_label'):
            self.progress_label.setText("任务完成!")
        self.log_message(f"任务完成: {task_id}")
        # 刷新任务列表以更新状态
        self.refresh_task_list()

    def on_task_failed(self, task_id: str, error_message: str):
        """任务失败回调"""
        if hasattr(self, 'progress_label'):
            self.progress_label.setText("任务失败!")
        self.log_message(f"任务失败: {task_id} - {error_message}")
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

        layout.addWidget(self.task_table)

        # 任务详情面板
        details_group = QGroupBox("任务详情")
        details_layout = QVBoxLayout(details_group)

        self.task_details_text = QTextEdit()
        self.task_details_text.setMaximumHeight(120)
        self.task_details_text.setReadOnly(True)
        self.task_details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        details_layout.addWidget(self.task_details_text)

        layout.addWidget(details_group)

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

            # 构建配置字典，包含合并后的高级配置
            config = {
                'task_id': f"task_{int(datetime.now().timestamp())}",
                'name': f"导入任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'symbols': symbols,
                'asset_type': self.asset_type_combo.currentText() if hasattr(self, 'asset_type_combo') else "股票",
                'data_type': self.data_type_combo.currentText() if hasattr(self, 'data_type_combo') else "K线数据",
                'frequency': freq_map.get(self.frequency_combo.currentText() if hasattr(self, 'frequency_combo') else "日线", "1d"),
                'data_source': self.data_source_combo.currentText() if hasattr(self, 'data_source_combo') else "通达信",

                # 从合并的配置tab中读取高级配置
                'batch_size': self.batch_size_spin.value() if hasattr(self, 'batch_size_spin') else 1000,
                'max_workers': self.workers_spin.value() if hasattr(self, 'workers_spin') else 4,
                'memory_limit': self.memory_limit_spin.value() if hasattr(self, 'memory_limit_spin') else 2048,
                'timeout': self.timeout_spin.value() if hasattr(self, 'timeout_spin') else 300,
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
                'end_date': self.end_date.date().toString("yyyy-MM-dd") if hasattr(self, 'end_date') else None
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
                timeout=task_config_dict.get('timeout', 300),
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
        """刷新任务列表"""
        try:
            if not self.config_manager:
                return

            # 获取所有任务
            tasks = self.config_manager.get_import_tasks()

            # 清空表格
            self.task_table.setRowCount(0)

            # 填充任务数据
            for task in tasks:
                row = self.task_table.rowCount()
                self.task_table.insertRow(row)

                # 获取任务状态
                task_status = None
                if self.import_engine:
                    task_status = self.import_engine.get_task_status(task.task_id)

                # 填充列数据 - 匹配13列表头：任务名称, 状态, 进度, 数据源, 资产类型, 数据类型, 频率, 符号数量, 开始时间, 结束时间, 运行时间, 成功数, 失败数
                start_time = task_status.start_time.strftime("%Y-%m-%d %H:%M:%S") if task_status and hasattr(task_status, 'start_time') and task_status.start_time else "未开始"
                end_time = task_status.end_time.strftime("%Y-%m-%d %H:%M:%S") if task_status and hasattr(task_status, 'end_time') and task_status.end_time else "未结束"

                # 计算运行时间
                runtime = "未开始"
                if task_status and hasattr(task_status, 'start_time') and task_status.start_time:
                    if hasattr(task_status, 'end_time') and task_status.end_time:
                        delta = task_status.end_time - task_status.start_time
                        runtime = str(delta).split('.')[0]  # 去除微秒
                    else:
                        from datetime import datetime
                        delta = datetime.now() - task_status.start_time
                        runtime = str(delta).split('.')[0]  # 去除微秒

                items = [
                    task.name,
                    task_status.status.value if task_status else "未开始",
                    f"{task_status.progress:.1f}%" if task_status and hasattr(task_status, 'progress') else "0%",
                    task.data_source,
                    task.asset_type,
                    task.data_type,
                    task.frequency.value if hasattr(task.frequency, 'value') else str(task.frequency),
                    str(len(task.symbols)),
                    start_time,
                    end_time,
                    runtime,
                    str(task_status.success_count) if task_status and hasattr(task_status, 'success_count') else "0",
                    str(task_status.failure_count) if task_status and hasattr(task_status, 'failure_count') else "0"
                ]

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

                # 存储任务ID到第一列的数据化
                self.task_table.item(row, 0).setData(Qt.UserRole, task.task_id)

            # logger.info(f"刷新任务列表完成，共 {len(tasks)} 个任化") if logger else None

        except Exception as e:
            logger.error(f"刷新任务列表失败: {e}") if logger else None

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
        """任务选择变化处理"""
        try:
            selected_items = self.task_table.selectedItems()
            if not selected_items:
                self.task_details_text.clear()
                return

            # 获取选中的第一化
            row = selected_items[0].row()
            task_id = self.task_table.item(row, 0).data(Qt.UserRole)

            if not task_id or not self.import_engine:
                return

            # 获取任务详细信息
            task_status = self.import_engine.get_task_status(task_id)
            if task_status:
                details = f"""任务ID: {task_id}
                状化 {task_status.status.value}
                进度: {task_status.progress: .1f}({task_status.processed_count}/{task_status.total_count})
                开始时化 {task_status.start_time.strftime('Y-m-d H:M:S') if task_status.start_time else '未开化'}
                结束时间: {task_status.end_time.strftime('Y-m-d H:M:S') if task_status.end_time else '未完化'}
                运行时间: {self.format_duration(task_status.execution_time) if hasattr(task_status, 'execution_time') else '0s'}
                成功数量: {task_status.success_count if hasattr(task_status, 'success_count') else 0}
                失败数量: {task_status.error_count if hasattr(task_status, 'error_count') else 0}
                最后错化 {task_status.last_error if hasattr(task_status, 'last_error') and task_status.last_error else '化'}"""
            else:
                details = f"任务ID: {task_id}\n状化 未开始\n详细信息暂不可用"

            self.task_details_text.setPlainText(details)

        except Exception as e:
            logger.error(f"更新任务详情失败: {e}") if logger else None

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

                    start_action = QAction("开始导入", self)
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
        """停止单个任务"""
        try:
            if self.import_engine:
                success = self.import_engine.stop_task(task_id)
                if success:
                    QMessageBox.information(self, "成功", "任务停止成功")
                    self.refresh_task_list()
                else:
                    QMessageBox.warning(self, "失败", "任务停止失败")
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
        """批量停止任务"""
        try:
            selected_task_ids = self.get_selected_task_ids()
            if not selected_task_ids:
                QMessageBox.warning(self, "警告", "请选择要停止的任务")
                return

            success_count = 0
            for task_id in selected_task_ids:
                if self.import_engine and self.import_engine.stop_task(task_id):
                    success_count += 1

            QMessageBox.information(
                self, "批量停止结果",
                f"成功停止 {success_count}/{len(selected_task_ids)} 个任务"
            )
            self.refresh_task_list()

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
            # 这里可以打开任务编辑对话框
            # 暂时显示提示信息
            QMessageBox.information(self, "编辑任务", f"任务编辑功能开发中...\n任务ID: {task_id}")
        except Exception as e:
            logger.error(f"编辑任务失败: {e}") if logger else None
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

        # 进度报告间隔
        self.progress_interval_spin = QSpinBox()
        self.progress_interval_spin.setRange(1, 60)
        self.progress_interval_spin.setValue(5)
        self.progress_interval_spin.setSuffix("秒")
        self.progress_interval_spin.setToolTip("进度更新间隔")
        layout.addRow("进度间隔:", self.progress_interval_spin)

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
                    self.workers_spin.setValue(4)
                if hasattr(self, 'memory_limit_spin'):
                    self.memory_limit_spin.setValue(2048)
                if hasattr(self, 'timeout_spin'):
                    self.timeout_spin.setValue(300)

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

    def _initialize_batch_buttons(self):
        """初始化批量按钮状态"""
        try:
            # 这个方法用于初始化批量选择相关按钮的状态
            # 目前暂时保持空实现，可以根据需要添加初始化逻辑
            pass
        except Exception as e:
            logger.error(f"初始化批量按钮失败: {e}") if logger else None


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
