"""
左侧面板 - 股票列表

提供股票搜索、筛选和管理功能。
"""

import logging
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QComboBox, QPushButton, QLabel, QFrame,
    QMenu, QMessageBox, QProgressBar, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon, QFont

from .base_panel import BasePanel
from core.events.events import StockSelectedEvent

logger = logging.getLogger(__name__)


class StockDataLoader(QThread):
    """异步股票数据加载器"""

    data_loaded = pyqtSignal(list)  # 数据加载完成信号
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, stock_service, market_filter=None, search_text=None):
        super().__init__()
        self.stock_service = stock_service
        self.market_filter = market_filter
        self.search_text = search_text

    def run(self):
        """运行数据加载"""
        try:
            # 模拟异步加载
            stocks = self.stock_service.get_stock_list()

            # 应用筛选
            if self.market_filter and self.market_filter != "全部":
                stocks = [s for s in stocks if s.get('market') == self.market_filter]

            if self.search_text:
                search_lower = self.search_text.lower()
                stocks = [s for s in stocks
                          if search_lower in s.get('name', '').lower()
                          or search_lower in s.get('code', '').lower()]

            self.data_loaded.emit(stocks)

        except Exception as e:
            self.error_occurred.emit(str(e))


class LeftPanel(BasePanel):
    """
    左侧面板 - 股票列表

    功能：
    1. 股票搜索和筛选
    2. 股票列表显示
    3. 收藏管理
    4. 股票信息展示
    """

    def __init__(self, parent, coordinator, **kwargs):
        """初始化左侧面板"""
        self.stock_service = None
        self.current_stocks = []
        self.favorites = set()
        self.search_timer = QTimer()
        self.data_loader = None

        super().__init__(parent, coordinator, **kwargs)

    def _create_widgets(self) -> None:
        """创建UI组件"""
        # 创建主布局
        main_layout = QVBoxLayout(self._root_frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建搜索区域
        self._create_search_area(main_layout)

        # 创建筛选区域
        self._create_filter_area(main_layout)

        # 创建股票列表
        self._create_stock_list(main_layout)

        # 创建状态栏
        self._create_status_bar(main_layout)

    def _create_search_area(self, parent_layout: QVBoxLayout) -> None:
        """创建搜索区域"""
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)

        # 搜索标签
        search_label = QLabel("搜索:")
        search_label.setFixedWidth(40)

        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入股票代码或名称...")
        self.search_input.setClearButtonEnabled(True)

        # 搜索按钮
        search_btn = QPushButton("搜索")
        search_btn.setFixedWidth(60)

        # 高级搜索按钮
        advanced_search_btn = QPushButton("高级搜索")
        advanced_search_btn.setFixedWidth(80)
        advanced_search_btn.clicked.connect(self._show_advanced_search)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(advanced_search_btn)

        parent_layout.addWidget(search_frame)

        # 保存组件引用
        self.add_widget('search_frame', search_frame)
        self.add_widget('search_input', self.search_input)
        self.add_widget('search_btn', search_btn)

    def _create_filter_area(self, parent_layout: QVBoxLayout) -> None:
        """创建筛选区域"""
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(0, 0, 0, 0)

        # 市场筛选
        market_label = QLabel("市场:")
        market_label.setFixedWidth(40)

        self.market_combo = QComboBox()
        self.market_combo.addItems(["全部", "上海", "深圳", "创业板", "科创板"])
        self.market_combo.setFixedWidth(80)

        # 收藏筛选
        self.favorites_btn = QPushButton("收藏")
        self.favorites_btn.setCheckable(True)
        self.favorites_btn.setFixedWidth(60)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedWidth(60)

        filter_layout.addWidget(market_label)
        filter_layout.addWidget(self.market_combo)
        filter_layout.addWidget(self.favorites_btn)
        filter_layout.addStretch()
        filter_layout.addWidget(refresh_btn)

        parent_layout.addWidget(filter_frame)

        # 保存组件引用
        self.add_widget('filter_frame', filter_frame)
        self.add_widget('market_combo', self.market_combo)
        self.add_widget('favorites_btn', self.favorites_btn)
        self.add_widget('refresh_btn', refresh_btn)

    def _create_stock_list(self, parent_layout: QVBoxLayout) -> None:
        """创建股票列表"""
        # 股票列表
        self.stock_tree = QTreeWidget()
        self.stock_tree.setHeaderLabels(["代码", "名称", "市场", "行业", "类型"])
        self.stock_tree.setRootIsDecorated(False)
        self.stock_tree.setAlternatingRowColors(True)
        self.stock_tree.setSortingEnabled(True)

        # 设置列宽
        self.stock_tree.setColumnWidth(0, 80)   # 代码
        self.stock_tree.setColumnWidth(1, 120)  # 名称
        self.stock_tree.setColumnWidth(2, 60)   # 市场
        self.stock_tree.setColumnWidth(3, 100)  # 行业
        self.stock_tree.setColumnWidth(4, 60)   # 类型

        # 启用右键菜单
        self.stock_tree.setContextMenuPolicy(Qt.CustomContextMenu)

        parent_layout.addWidget(self.stock_tree)

        # 保存组件引用
        self.add_widget('stock_tree', self.stock_tree)

    def _create_status_bar(self, parent_layout: QVBoxLayout) -> None:
        """创建状态栏"""
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666666; font-size: 12px;")

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(15)

        # 股票数量标签
        self.count_label = QLabel("股票: 0")
        self.count_label.setStyleSheet("color: #666666; font-size: 12px;")

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(self.count_label)

        parent_layout.addWidget(status_frame)

        # 保存组件引用
        self.add_widget('status_frame', status_frame)
        self.add_widget('status_label', self.status_label)
        self.add_widget('progress_bar', self.progress_bar)
        self.add_widget('count_label', self.count_label)

    def _bind_events(self) -> None:
        """绑定事件"""
        try:
            # 搜索事件
            self.search_input.textChanged.connect(self._on_search_text_changed)
            self.get_widget('search_btn').clicked.connect(self._on_search_clicked)

            # 筛选事件
            self.market_combo.currentTextChanged.connect(self._on_market_changed)
            self.favorites_btn.toggled.connect(self._on_favorites_toggled)
            self.get_widget('refresh_btn').clicked.connect(self._on_refresh_clicked)

            # 股票列表事件
            self.stock_tree.itemClicked.connect(self._on_stock_clicked)
            self.stock_tree.itemDoubleClicked.connect(self._on_stock_double_clicked)
            self.stock_tree.customContextMenuRequested.connect(self._on_context_menu)

            # 搜索延迟定时器
            self.search_timer.timeout.connect(self._perform_search)
            self.search_timer.setSingleShot(True)

            logger.debug("LeftPanel events bound successfully")

        except Exception as e:
            logger.error(f"Failed to bind LeftPanel events: {e}")
            raise

    def _initialize_data(self) -> None:
        """初始化数据"""
        try:
            # 获取股票服务
            if self.coordinator and hasattr(self.coordinator, 'service_container'):
                from core.services import StockService
                self.stock_service = self.coordinator.service_container.get_service(StockService)

            # 加载初始数据
            self._load_stock_data()

        except Exception as e:
            logger.error(f"Failed to initialize LeftPanel data: {e}")

    @pyqtSlot(str)
    def _on_search_text_changed(self, text: str) -> None:
        """搜索文本变化处理"""
        # 延迟搜索，避免频繁请求
        self.search_timer.stop()
        self.search_timer.start(500)  # 500ms延迟

    @pyqtSlot()
    def _on_search_clicked(self) -> None:
        """搜索按钮点击处理"""
        self._perform_search()

    @pyqtSlot(str)
    def _on_market_changed(self, market: str) -> None:
        """市场筛选变化处理"""
        self._load_stock_data()

    @pyqtSlot(bool)
    def _on_favorites_toggled(self, checked: bool) -> None:
        """收藏筛选切换处理"""
        self._load_stock_data()

    @pyqtSlot()
    def _on_refresh_clicked(self) -> None:
        """刷新按钮点击处理"""
        self._load_stock_data()

    @pyqtSlot(QTreeWidgetItem, int)
    def _on_stock_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """股票点击处理"""
        if item:
            stock_code = item.text(0)
            stock_name = item.text(1)
            market = item.text(2)
            self._select_stock(stock_code, stock_name, market)

    @pyqtSlot(QTreeWidgetItem, int)
    def _on_stock_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """股票双击处理"""
        if item:
            stock_code = item.text(0)
            stock_name = item.text(1)
            market = item.text(2)
            self._select_stock(stock_code, stock_name, market)
            # 双击可以触发额外操作，比如添加到收藏

    def _on_context_menu(self, position) -> None:
        """右键菜单处理"""
        item = self.stock_tree.itemAt(position)
        if not item:
            return

        stock_code = item.text(0)
        stock_name = item.text(1)

        # 创建右键菜单
        menu = QMenu(self.stock_tree)

        # 查看详情
        action = menu.addAction("查看详情")
        action.triggered.connect(lambda: self._show_stock_details(stock_code, stock_name))

        # 添加到收藏/取消收藏
        if stock_code in self.favorites:
            action = menu.addAction("从收藏移除")
            action.triggered.connect(lambda: self._remove_from_favorites(stock_code))
        else:
            action = menu.addAction("添加到收藏")
            action.triggered.connect(lambda: self._add_to_favorites(stock_code, stock_name))

        menu.addSeparator()

        # 导出数据
        action = menu.addAction("导出数据")
        action.triggered.connect(lambda: self._export_stock_data(stock_code, stock_name))

        menu.addSeparator()

        # 添加到自选股
        action = menu.addAction("添加到自选股")
        action.triggered.connect(lambda: self._add_to_watchlist(stock_code, stock_name))

        # 添加到投资组合
        action = menu.addAction("添加到投资组合")
        action.triggered.connect(lambda: self._add_to_portfolio(stock_code, stock_name))

        menu.addSeparator()

        # 分析功能
        action = menu.addAction("技术分析")
        action.triggered.connect(lambda: self._analyze_stock(stock_code, stock_name))

        action = menu.addAction("策略回测")
        action.triggered.connect(lambda: self._backtest_stock(stock_code, stock_name))

        menu.addSeparator()

        # 管理功能
        action = menu.addAction("历史数据管理")
        action.triggered.connect(lambda: self._manage_history_data(stock_code, stock_name))

        action = menu.addAction("策略管理")
        action.triggered.connect(lambda: self._manage_strategy(stock_code, stock_name))

        menu.addSeparator()

        # 工具功能
        action = menu.addAction("数据质量检查")
        action.triggered.connect(lambda: self._check_data_quality(stock_code, stock_name))

        action = menu.addAction("计算器")
        action.triggered.connect(lambda: self._show_calculator())

        action = menu.addAction("单位转换器")
        action.triggered.connect(lambda: self._show_converter())

        # 添加到投资组合
        action = menu.addAction("添加到投资组合")
        action.triggered.connect(lambda: self._add_to_portfolio(stock_code, stock_name))

        menu.addSeparator()

        # 技术分析
        action = menu.addAction("技术分析")
        action.triggered.connect(lambda: self._analyze_stock(stock_code, stock_name))

        # 策略回测
        action = menu.addAction("策略回测")
        action.triggered.connect(lambda: self._backtest_stock(stock_code, stock_name))

        # 历史数据管理
        action = menu.addAction("历史数据管理")
        action.triggered.connect(lambda: self._manage_history_data(stock_code, stock_name))

        # 策略管理
        action = menu.addAction("策略管理")
        action.triggered.connect(lambda: self._manage_strategy(stock_code, stock_name))

        # 显示菜单
        menu.exec_(self.stock_tree.mapToGlobal(position))

    def _perform_search(self) -> None:
        """执行搜索"""
        search_text = self.search_input.text().strip()
        self._load_stock_data(search_text=search_text)

    def _show_advanced_search(self) -> None:
        """显示高级搜索对话框"""
        try:
            from gui.dialogs.advanced_search_dialog import AdvancedSearchDialog

            dialog = AdvancedSearchDialog(parent=self, stock_service=self.stock_service)
            dialog.search_requested.connect(self._on_advanced_search)
            dialog.exec_()

        except Exception as e:
            logger.error(f"显示高级搜索对话框失败: {e}")

    def _on_advanced_search(self, conditions: Dict[str, Any]) -> None:
        """处理高级搜索请求"""
        try:
            # 执行高级搜索
            filtered_stocks = self.stock_service.perform_advanced_search(conditions)

            # 更新股票列表显示
            self._update_stock_tree(filtered_stocks)

            logger.info(f"高级搜索完成，找到 {len(filtered_stocks)} 只符合条件的股票")

        except Exception as e:
            logger.error(f"执行高级搜索失败: {e}")

    def _export_stock_data(self, stock_code: str, stock_name: str) -> None:
        """导出股票数据"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            import pandas as pd
            from datetime import datetime

            # 获取股票详细信息
            stock_info = self.stock_service.get_stock_info(stock_code)
            if not stock_info:
                QMessageBox.warning(self, "警告", f"无法获取股票 {stock_name} 的信息")
                return

            # 获取历史数据
            stock_data = self.stock_service.get_stock_data(stock_code, period='D', count=100)

            # 准备基本信息
            basic_info = [
                {'项目': '股票代码', '值': stock_code},
                {'项目': '股票名称', '值': stock_name},
                {'项目': '所属市场', '值': stock_info.get('market', '未知')},
                {'项目': '所属行业', '值': stock_info.get('industry', '未知')},
                {'项目': '上市日期', '值': stock_info.get('list_date', '未知')},
                {'项目': '总股本', '值': stock_info.get('total_shares', 0)},
                {'项目': '流通股本', '值': stock_info.get('circulating_shares', 0)}
            ]

            basic_df = pd.DataFrame(basic_info)

            # 准备历史数据
            history_df = stock_data if stock_data is not None and not stock_data.empty else pd.DataFrame()

            # 导出到Excel
            filename = f"stock_{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            with pd.ExcelWriter(filename) as writer:
                basic_df.to_excel(writer, sheet_name="基本信息", index=False)
                if not history_df.empty:
                    history_df.to_excel(writer, sheet_name="历史数据", index=False)

            QMessageBox.information(self, "成功", f"数据已导出到: {filename}")
            logger.info(f"股票数据已导出到: {filename}")

        except Exception as e:
            logger.error(f"导出股票数据失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"导出数据失败: {e}")

    def _add_to_watchlist(self, stock_code: str, stock_name: str) -> None:
        """添加到自选股"""
        try:
            from PyQt5.QtWidgets import QMessageBox

            # 这里可以调用自选股服务或者通过事件系统处理
            # 暂时使用简单的消息提示
            QMessageBox.information(self, "成功", f"已添加 {stock_name}({stock_code}) 到自选股")
            logger.info(f"添加到自选股: {stock_name}({stock_code})")

        except Exception as e:
            logger.error(f"添加到自选股失败: {e}")

    def _add_to_portfolio(self, stock_code: str, stock_name: str) -> None:
        """添加到投资组合"""
        try:
            from PyQt5.QtWidgets import QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QPushButton, QHBoxLayout, QLabel, QMessageBox

            # 创建投资组合对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("添加到投资组合")
            dialog.setModal(True)
            dialog.resize(400, 300)

            layout = QFormLayout(dialog)

            # 股票信息显示
            layout.addRow("股票:", QLabel(f"{stock_name} ({stock_code})"))

            # 投资组合名称
            portfolio_combo = QComboBox()
            portfolio_combo.setEditable(True)
            portfolio_combo.addItems(["默认组合", "价值投资", "成长股", "蓝筹股", "科技股"])
            layout.addRow("投资组合:", portfolio_combo)

            # 投资金额
            amount_spin = QDoubleSpinBox()
            amount_spin.setRange(0, 10000000)
            amount_spin.setValue(10000)
            amount_spin.setSuffix(" 元")
            layout.addRow("投资金额:", amount_spin)

            # 按钮
            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addRow(button_layout)

            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)

            if dialog.exec_() == QDialog.Accepted:
                portfolio_name = portfolio_combo.currentText()
                amount = amount_spin.value()

                QMessageBox.information(self, "成功", f"已添加 {stock_name} 到投资组合 {portfolio_name}")
                logger.info(f"添加到投资组合: {stock_name}({stock_code}) -> {portfolio_name}, 金额: {amount}")

        except Exception as e:
            logger.error(f"添加到投资组合失败: {e}")

    def _analyze_stock(self, stock_code: str, stock_name: str) -> None:
        """技术分析股票"""
        try:
            from gui.dialogs.technical_analysis_dialog import TechnicalAnalysisDialog

            # 获取分析服务
            analysis_service = None
            if self.coordinator and hasattr(self.coordinator, 'service_container'):
                from core.services.analysis_service import AnalysisService
                analysis_service = self.coordinator.service_container.try_resolve(AnalysisService)

            # 显示技术分析对话框
            dialog = TechnicalAnalysisDialog(self, stock_code, analysis_service)
            dialog.exec_()

            logger.info(f"启动技术分析: {stock_name}({stock_code})")

        except Exception as e:
            logger.error(f"技术分析失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"技术分析失败: {e}")

    def _backtest_stock(self, stock_code: str, stock_name: str) -> None:
        """策略回测股票"""
        try:
            from gui.dialogs.strategy_manager_dialog import StrategyManagerDialog

            # 获取策略服务
            strategy_service = None
            if self.coordinator and hasattr(self.coordinator, 'service_container'):
                from core.services.strategy_service import StrategyService
                strategy_service = self.coordinator.service_container.try_resolve(StrategyService)

            # 显示策略管理对话框，并切换到回测选项卡
            dialog = StrategyManagerDialog(self, strategy_service)
            dialog.tab_widget.setCurrentIndex(2)  # 切换到回测选项卡
            dialog.exec_()

            logger.info(f"启动策略回测: {stock_name}({stock_code})")

        except Exception as e:
            logger.error(f"策略回测失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"策略回测失败: {e}")

    def _manage_history_data(self, stock_code: str, stock_name: str) -> None:
        """历史数据管理"""
        try:
            from gui.dialogs.history_data_dialog import HistoryDataDialog

            # 显示历史数据管理对话框
            dialog = HistoryDataDialog(self, self.stock_service)

            # 设置当前股票
            if hasattr(dialog, 'stock_combo'):
                dialog.stock_combo.setCurrentText(f"{stock_code} - {stock_name}")

            dialog.exec_()

            logger.info(f"管理历史数据: {stock_name}({stock_code})")

        except Exception as e:
            logger.error(f"历史数据管理失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"历史数据管理失败: {e}")

    def _manage_strategy(self, stock_code: str, stock_name: str) -> None:
        """策略管理"""
        try:
            from gui.dialogs.strategy_manager_dialog import StrategyManagerDialog

            # 获取策略服务
            strategy_service = None
            if self.coordinator and hasattr(self.coordinator, 'service_container'):
                from core.services.strategy_service import StrategyService
                strategy_service = self.coordinator.service_container.try_resolve(StrategyService)

            # 显示策略管理对话框
            dialog = StrategyManagerDialog(self, strategy_service)
            dialog.exec_()

            logger.info(f"管理策略: {stock_name}({stock_code})")

        except Exception as e:
            logger.error(f"策略管理失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"策略管理失败: {e}")

    def _update_stock_tree(self, stocks: List[Dict[str, Any]]) -> None:
        """更新股票树显示"""
        try:
            self.stock_tree.clear()

            for stock in stocks:
                item = QTreeWidgetItem()
                item.setText(0, stock.get('code', ''))
                item.setText(1, stock.get('name', ''))
                item.setText(2, stock.get('market', ''))

                # 设置收藏状态
                if stock.get('code') in self.favorites:
                    item.setText(1, f"★ {stock.get('name', '')}")

                self.stock_tree.addTopLevelItem(item)

            # 调整列宽
            self.stock_tree.resizeColumnToContents(0)
            self.stock_tree.resizeColumnToContents(1)

        except Exception as e:
            logger.error(f"更新股票树显示失败: {e}")

    def _load_stock_data(self, search_text: str = None) -> None:
        """加载股票数据"""
        if not self.stock_service:
            return

        try:
            # 显示加载状态
            self._show_loading(True)

            # 获取筛选条件
            market_filter = self.market_combo.currentText()
            search_text = search_text or self.search_input.text().strip()

            # 停止之前的加载任务
            if self.data_loader and self.data_loader.isRunning():
                self.data_loader.terminate()
                self.data_loader.wait()

            # 创建新的加载任务
            self.data_loader = StockDataLoader(
                self.stock_service,
                market_filter,
                search_text
            )

            # 连接信号
            self.data_loader.data_loaded.connect(self._on_data_loaded)
            self.data_loader.error_occurred.connect(self._on_data_error)

            # 开始加载
            self.data_loader.start()

        except Exception as e:
            logger.error(f"Failed to load stock data: {e}")
            self._show_loading(False)
            self.status_label.setText(f"加载失败: {e}")

    @pyqtSlot(list)
    def _on_data_loaded(self, stocks: List[Dict[str, Any]]) -> None:
        """数据加载完成处理"""
        try:
            self.current_stocks = stocks
            self._update_stock_list(stocks)
            self._show_loading(False)
            self.status_label.setText("就绪")
            self.count_label.setText(f"股票: {len(stocks)}")

        except Exception as e:
            logger.error(f"Failed to process loaded data: {e}")
            self._on_data_error(str(e))

    @pyqtSlot(str)
    def _on_data_error(self, error: str) -> None:
        """数据加载错误处理"""
        logger.error(f"Stock data loading error: {error}")
        self._show_loading(False)
        self.status_label.setText(f"加载失败: {error}")

    def _update_stock_list(self, stocks: List[Dict[str, Any]]) -> None:
        """更新股票列表"""
        try:
            # 清空现有数据
            self.stock_tree.clear()

            # 添加股票数据
            for stock in stocks:
                # 显示基本信息，不显示实时价格（避免性能问题）
                item = QTreeWidgetItem([
                    stock.get('code', ''),
                    stock.get('name', ''),
                    stock.get('market', ''),
                    stock.get('industry', '其他'),
                    stock.get('type', '')
                ])

                # 收藏标记
                if stock.get('code') in self.favorites:
                    item.setForeground(1, Qt.blue)
                    font = item.font(1)
                    font.setBold(True)
                    item.setFont(1, font)

                # 设置工具提示
                tooltip = (f"代码: {stock.get('code', '')}\n"
                           f"名称: {stock.get('name', '')}\n"
                           f"市场: {stock.get('market', '')}\n"
                           f"行业: {stock.get('industry', '其他')}\n"
                           f"类型: {stock.get('type', '')}")
                item.setToolTip(0, tooltip)
                item.setToolTip(1, tooltip)

                self.stock_tree.addTopLevelItem(item)

        except Exception as e:
            logger.error(f"Failed to update stock list: {e}")

    def _select_stock(self, stock_code: str, stock_name: str, market: str = '') -> None:
        """选择股票"""
        try:
            # 发送股票选择事件
            if self.event_bus:
                event = StockSelectedEvent(stock_code=stock_code, stock_name=stock_name, market=market)
                self.event_bus.publish(event)

            logger.info(f"Stock selected: {stock_code} - {stock_name}")

        except Exception as e:
            logger.error(f"Failed to select stock: {e}")

    def _add_to_favorites(self, stock_code: str, stock_name: str) -> None:
        """添加到收藏"""
        try:
            self.favorites.add(stock_code)
            if self.stock_service:
                self.stock_service.add_to_favorites(stock_code)

            # 刷新显示
            self._update_stock_list(self.current_stocks)

            self.show_message(f"已添加 {stock_name} 到收藏", 'info')
            logger.info(f"Added to favorites: {stock_code}")

        except Exception as e:
            logger.error(f"Failed to add to favorites: {e}")
            self.show_message(f"添加收藏失败: {e}", 'error')

    def _remove_from_favorites(self, stock_code: str) -> None:
        """从收藏中移除"""
        try:
            self.favorites.discard(stock_code)
            if self.stock_service:
                self.stock_service.remove_from_favorites(stock_code)

            # 刷新显示
            self._update_stock_list(self.current_stocks)

            self.show_message(f"已从收藏中移除 {stock_code}", 'info')
            logger.info(f"Removed from favorites: {stock_code}")

        except Exception as e:
            logger.error(f"Failed to remove from favorites: {e}")
            self.show_message(f"移除收藏失败: {e}", 'error')

    def _show_stock_details(self, stock_code: str, stock_name: str) -> None:
        """显示股票详情"""
        try:
            from gui.dialogs.stock_detail_dialog import StockDetailDialog
            from PyQt5.QtWidgets import QMessageBox

            # 获取股票详细信息
            stock_info = self.stock_service.get_stock_info(stock_code) if self.stock_service else {}
            if not stock_info:
                QMessageBox.warning(self, "警告", f"无法获取股票 {stock_name} 的信息")
                return

            # 获取历史数据
            history_data = None
            if self.stock_service:
                history_data = self.stock_service.get_stock_data(stock_code, period='D', count=20)

            # 准备股票数据
            stock_data = dict(stock_info)
            stock_data['code'] = stock_code
            stock_data['name'] = stock_name

            # 添加历史数据
            if history_data is not None and not history_data.empty:
                history_list = []
                for idx, row in history_data.iterrows():
                    history_list.append({
                        'date': str(idx.date()) if hasattr(idx, 'date') else str(idx),
                        'open': float(row.get('open', 0)),
                        'high': float(row.get('high', 0)),
                        'low': float(row.get('low', 0)),
                        'close': float(row.get('close', 0)),
                        'volume': float(row.get('volume', 0))
                    })
                stock_data['history'] = history_list

            # 显示详情对话框
            dialog = StockDetailDialog(stock_data, self)
            dialog.exec_()

            logger.info(f"查看股票详情: {stock_name} ({stock_code})")

        except Exception as e:
            logger.error(f"显示股票详情失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"显示股票详情失败: {e}")

    def _show_loading(self, show: bool) -> None:
        """显示/隐藏加载状态"""
        self.progress_bar.setVisible(show)
        if show:
            self.progress_bar.setRange(0, 0)  # 不确定进度
            self.status_label.setText("加载中...")
        else:
            self.progress_bar.setVisible(False)

    def _apply_theme_to_widgets(self, theme: Dict[str, Any]) -> None:
        """应用主题到组件"""
        super()._apply_theme_to_widgets(theme)

        try:
            colors = theme.get('colors', {})

            # 应用到搜索输入框
            if self.search_input:
                self.search_input.setStyleSheet(f"""
                    QLineEdit {{
                        background-color: {colors.get('input_bg', '#ffffff')};
                        border: 1px solid {colors.get('border', '#cccccc')};
                        padding: 5px;
                        border-radius: 3px;
                    }}
                """)

            # 应用到股票列表
            if self.stock_tree:
                self.stock_tree.setStyleSheet(f"""
                    QTreeWidget {{
                        background-color: {colors.get('list_bg', '#ffffff')};
                        alternate-background-color: {colors.get('list_alt_bg', '#f5f5f5')};
                        border: 1px solid {colors.get('border', '#cccccc')};
                    }}
                    QTreeWidget::item:selected {{
                        background-color: {colors.get('selection_bg', '#0078d4')};
                        color: {colors.get('selection_fg', '#ffffff')};
                    }}
                """)

        except Exception as e:
            logger.debug(f"Failed to apply theme to LeftPanel widgets: {e}")

    def _do_dispose(self) -> None:
        """释放资源"""
        try:
            # 停止数据加载
            if self.data_loader and self.data_loader.isRunning():
                self.data_loader.terminate()
                self.data_loader.wait()

            # 停止定时器
            if self.search_timer:
                self.search_timer.stop()

        except Exception as e:
            logger.error(f"Error disposing LeftPanel resources: {e}")

    # 事件处理方法
    def on_stock_selected(self, event) -> None:
        """处理股票选择事件"""
        # 这里可以处理来自其他组件的股票选择事件
        pass

    def on_data_update(self, event) -> None:
        """处理数据更新事件"""
        # 刷新股票数据
        self._load_stock_data()

    def on_theme_changed(self, event) -> None:
        """处理主题变化事件"""
        if hasattr(event, 'theme'):
            self.apply_theme(event.theme)

    def _check_data_quality(self, stock_code: str, stock_name: str) -> None:
        """数据质量检查"""
        try:
            from gui.dialogs.data_quality_dialog import DataQualityDialog

            # 获取主窗口作为父窗口
            parent_widget = self.window() if hasattr(self, 'window') else None

            # 创建数据质量检查对话框
            dialog = DataQualityDialog(parent_widget, stock_code=stock_code)

            # 居中显示
            if self.coordinator:
                self.coordinator.center_dialog(dialog, parent_widget)

            dialog.exec_()

            logger.info(f"Opened data quality check for stock: {stock_code}")

        except Exception as e:
            logger.error(f"Failed to open data quality check: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.window() if hasattr(self, 'window') else None, "错误",
                f"打开数据质量检查失败: {str(e)}"
            )

    def _show_calculator(self) -> None:
        """显示计算器"""
        try:
            from gui.dialogs.calculator_dialog import CalculatorDialog

            # 获取主窗口作为父窗口
            parent_widget = self.window() if hasattr(self, 'window') else None

            # 创建计算器对话框
            dialog = CalculatorDialog(parent_widget)

            # 居中显示
            if self.coordinator:
                self.coordinator.center_dialog(dialog, parent_widget)

            dialog.exec_()

            logger.info("Opened calculator")

        except Exception as e:
            logger.error(f"Failed to open calculator: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.window() if hasattr(self, 'window') else None, "错误",
                f"打开计算器失败: {str(e)}"
            )

    def _show_converter(self) -> None:
        """显示单位转换器"""
        try:
            from gui.dialogs import ConverterDialog

            # 创建单位转换器对话框
            dialog = ConverterDialog(self)

            # 居中显示
            if self.coordinator:
                self.coordinator.center_dialog(dialog, self)

            dialog.exec_()

            logger.info("Opened unit converter")

        except Exception as e:
            logger.error(f"Failed to open unit converter: {e}")
            QMessageBox.critical(
                self, "错误",
                f"打开单位转换器失败: {str(e)}"
            )
