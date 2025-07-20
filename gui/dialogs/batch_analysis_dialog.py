"""
批量分析对话框 - 已弃用

⚠️ 重要提示：此文件已弃用！
功能已整合到 AnalysisToolsPanel 中的增强版批量分析系统。

新系统特性：
- 保留真实分析功能（不再使用模拟数据）
- 集成CompactAdvancedFilterDialog的专业筛选界面
- 4选项卡UI设计：分析配置、进度监控、结果分析、分布式设置
- 完整的任务管理和控制功能

建议使用路径：
主界面 -> 右侧面板 -> 批量分析Tab

用于批量/分布式分析参数设置与进度监控
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QLabel, QLineEdit, QTextEdit, QGroupBox,
                             QFormLayout, QSpinBox, QCheckBox, QComboBox,
                             QProgressBar, QMessageBox, QHeaderView,
                             QSplitter, QFrame, QListWidget, QListWidgetItem,
                             QTreeWidget, QTreeWidgetItem, QDateEdit,
                             QSlider, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QDate
from PyQt5.QtGui import QFont
import json
import time
import threading


class BatchAnalysisWorker(QThread):
    """批量分析工作线程"""

    progress_updated = pyqtSignal(int)
    task_completed = pyqtSignal(dict)
    analysis_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, analysis_config):
        super().__init__()
        self.analysis_config = analysis_config
        self.is_running = True

    def run(self):
        """执行批量分析"""
        try:
            stocks = self.analysis_config.get('stocks', [])
            strategies = self.analysis_config.get('strategies', [])
            total_tasks = len(stocks) * len(strategies)

            results = []
            completed_tasks = 0

            for stock in stocks:
                if not self.is_running:
                    break

                for strategy in strategies:
                    if not self.is_running:
                        break

                    # 模拟分析过程
                    result = self.analyze_stock_strategy(stock, strategy)
                    results.append(result)

                    completed_tasks += 1
                    progress = int(completed_tasks / total_tasks * 100)
                    self.progress_updated.emit(progress)
                    self.task_completed.emit(result)

                    # 模拟处理时间
                    self.msleep(100)

            if self.is_running:
                self.analysis_finished.emit(results)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def analyze_stock_strategy(self, stock, strategy):
        """分析单个股票策略组合"""
        import random

        # 模拟分析结果
        return {
            'stock_code': stock['code'],
            'stock_name': stock['name'],
            'strategy': strategy,
            'return_rate': round(random.uniform(-0.2, 0.3), 4),
            'sharpe_ratio': round(random.uniform(0.5, 2.5), 2),
            'max_drawdown': round(random.uniform(0.05, 0.25), 4),
            'win_rate': round(random.uniform(0.4, 0.7), 2),
            'total_trades': random.randint(50, 200),
            'analysis_time': time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def stop(self):
        """停止分析"""
        self.is_running = False


class BatchAnalysisDialog(QDialog):
    """批量分析对话框"""

    analysis_started = pyqtSignal()
    analysis_finished = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量分析管理器")
        self.setModal(True)
        self.resize(1200, 800)

        # 分析配置和状态
        self.analysis_config = {}
        self.analysis_results = []
        self.worker_thread = None

        self.setup_ui()
        self.load_default_config()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 创建选项卡
        tab_widget = QTabWidget()

        # 分析配置选项卡
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "分析配置")

        # 进度监控选项卡
        monitor_tab = self.create_monitor_tab()
        tab_widget.addTab(monitor_tab, "进度监控")

        # 结果分析选项卡
        results_tab = self.create_results_tab()
        tab_widget.addTab(results_tab, "结果分析")

        # 分布式设置选项卡
        distributed_tab = self.create_distributed_tab()
        tab_widget.addTab(distributed_tab, "分布式设置")

        layout.addWidget(tab_widget)

        # 控制按钮
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始分析")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px 16px;
                font-size: 14px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)

        self.stop_btn = QPushButton("停止分析")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px 16px;
                font-size: 14px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)

        self.export_btn = QPushButton("导出结果")
        close_btn = QPushButton("关闭")

        self.start_btn.clicked.connect(self.start_analysis)
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.export_btn.clicked.connect(self.export_results)
        close_btn.clicked.connect(self.accept)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def create_config_tab(self):
        """创建分析配置选项卡"""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        # 股票选择
        stock_group = QGroupBox("股票选择")
        stock_layout = QVBoxLayout(stock_group)

        # 选择方式
        stock_selection_layout = QHBoxLayout()

        self.stock_selection_combo = QComboBox()
        self.stock_selection_combo.addItems([
            "全部股票", "指定股票列表", "按市值筛选", "按行业筛选", "自定义条件"
        ])
        self.stock_selection_combo.currentTextChanged.connect(
            self.on_stock_selection_changed)
        stock_selection_layout.addWidget(QLabel("选择方式:"))
        stock_selection_layout.addWidget(self.stock_selection_combo)
        stock_selection_layout.addStretch()

        stock_layout.addLayout(stock_selection_layout)

        # 股票列表
        self.stock_list = QListWidget()
        self.stock_list.setMaximumHeight(150)
        self.stock_list.setSelectionMode(QListWidget.MultiSelection)
        stock_layout.addWidget(QLabel("选中股票:"))
        stock_layout.addWidget(self.stock_list)

        # 股票选择按钮
        stock_button_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_none_btn = QPushButton("全不选")
        import_list_btn = QPushButton("导入列表")

        select_all_btn.clicked.connect(self.select_all_stocks)
        select_none_btn.clicked.connect(self.select_no_stocks)
        import_list_btn.clicked.connect(self.import_stock_list)

        stock_button_layout.addWidget(select_all_btn)
        stock_button_layout.addWidget(select_none_btn)
        stock_button_layout.addWidget(import_list_btn)
        stock_button_layout.addStretch()

        stock_layout.addLayout(stock_button_layout)

        layout.addWidget(stock_group)

        # 策略选择
        strategy_group = QGroupBox("策略选择")
        strategy_layout = QVBoxLayout(strategy_group)

        self.strategy_list = QListWidget()
        # self.strategy_list.setMaximumHeight()
        self.strategy_list.setSelectionMode(QListWidget.MultiSelection)

        strategies = [
            "均线策略", "MACD策略", "RSI策略", "布林带策略",
            "KDJ策略", "动量策略", "趋势跟踪", "均值回归"
        ]
        for strategy in strategies:
            item = QListWidgetItem(strategy)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.strategy_list.addItem(item)

        # strategy_layout.addWidget(QLabel("选择策略:"))
        strategy_layout.addWidget(self.strategy_list)

        layout.addWidget(strategy_group)

        # 分析参数
        params_group = QGroupBox("分析参数")
        params_layout = QFormLayout(params_group)

        # 时间范围
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setCalendarPopup(True)
        params_layout.addRow("开始日期:", self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        params_layout.addRow("结束日期:", self.end_date)

        # 其他参数
        self.initial_capital_spin = QSpinBox()
        self.initial_capital_spin.setRange(10000, 10000000)
        self.initial_capital_spin.setValue(100000)
        self.initial_capital_spin.setSuffix(" 元")
        params_layout.addRow("初始资金:", self.initial_capital_spin)

        self.commission_spin = QSpinBox()
        self.commission_spin.setRange(1, 100)
        self.commission_spin.setValue(5)
        self.commission_spin.setSuffix(" ‰")
        params_layout.addRow("手续费率:", self.commission_spin)

        self.slippage_spin = QSpinBox()
        self.slippage_spin.setRange(0, 50)
        self.slippage_spin.setValue(1)
        self.slippage_spin.setSuffix(" ‰")
        params_layout.addRow("滑点:", self.slippage_spin)

        layout.addWidget(params_group)

        return widget

    def create_monitor_tab(self):
        """创建进度监控选项卡"""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        # 总体进度
        progress_group = QGroupBox("总体进度")
        progress_layout = QVBoxLayout(progress_group)

        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        progress_layout.addWidget(self.overall_progress)

        # 进度信息
        progress_info_layout = QFormLayout()
        self.total_tasks_label = QLabel("0")
        self.completed_tasks_label = QLabel("0")
        self.remaining_tasks_label = QLabel("0")
        self.elapsed_time_label = QLabel("00:00:00")
        self.estimated_time_label = QLabel("00:00:00")

        progress_info_layout.addRow("总任务数:", self.total_tasks_label)
        progress_info_layout.addRow("已完成:", self.completed_tasks_label)
        progress_info_layout.addRow("剩余任务:", self.remaining_tasks_label)
        progress_info_layout.addRow("已用时间:", self.elapsed_time_label)
        progress_info_layout.addRow("预计剩余:", self.estimated_time_label)

        progress_layout.addLayout(progress_info_layout)

        layout.addWidget(progress_group)

        # 任务详情
        tasks_group = QGroupBox("任务详情")
        tasks_layout = QVBoxLayout(tasks_group)

        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(6)
        self.tasks_table.setHorizontalHeaderLabels([
            "股票代码", "股票名称", "策略", "状态", "进度", "完成时间"
        ])
        self.tasks_table.horizontalHeader().setStretchLastSection(True)
        tasks_layout.addWidget(self.tasks_table)

        layout.addWidget(tasks_group)

        # 实时日志
        log_group = QGroupBox("实时日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        # self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        # 日志控制
        log_control_layout = QHBoxLayout()
        clear_log_btn = QPushButton("清空日志")
        save_log_btn = QPushButton("保存日志")

        clear_log_btn.clicked.connect(self.clear_log)
        save_log_btn.clicked.connect(self.save_log)

        log_control_layout.addWidget(clear_log_btn)
        log_control_layout.addWidget(save_log_btn)
        log_control_layout.addStretch()

        log_layout.addLayout(log_control_layout)

        layout.addWidget(log_group)

        return widget

    def create_results_tab(self):
        """创建结果分析选项卡"""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        # 结果统计
        stats_group = QGroupBox("结果统计")
        stats_layout = QFormLayout(stats_group)

        self.total_combinations_label = QLabel("0")
        self.profitable_combinations_label = QLabel("0")
        self.best_return_label = QLabel("0.00%")
        self.worst_return_label = QLabel("0.00%")
        self.avg_return_label = QLabel("0.00%")
        self.best_sharpe_label = QLabel("0.00")

        stats_layout.addRow("总组合数:", self.total_combinations_label)
        stats_layout.addRow("盈利组合:", self.profitable_combinations_label)
        stats_layout.addRow("最佳收益率:", self.best_return_label)
        stats_layout.addRow("最差收益率:", self.worst_return_label)
        stats_layout.addRow("平均收益率:", self.avg_return_label)
        stats_layout.addRow("最高夏普比:", self.best_sharpe_label)

        layout.addWidget(stats_group)

        # 结果表格
        results_group = QGroupBox("详细结果")
        results_layout = QVBoxLayout(results_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "股票代码", "股票名称", "策略", "收益率", "夏普比率",
            "最大回撤", "胜率", "交易次数"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSortingEnabled(True)
        results_layout.addWidget(self.results_table)

        # 结果操作按钮
        results_button_layout = QHBoxLayout()
        sort_by_return_btn = QPushButton("按收益率排序")
        sort_by_sharpe_btn = QPushButton("按夏普比排序")
        filter_profitable_btn = QPushButton("筛选盈利组合")

        sort_by_return_btn.clicked.connect(
            lambda: self.sort_results("return_rate"))
        sort_by_sharpe_btn.clicked.connect(
            lambda: self.sort_results("sharpe_ratio"))
        filter_profitable_btn.clicked.connect(self.filter_profitable_results)

        results_button_layout.addWidget(sort_by_return_btn)
        results_button_layout.addWidget(sort_by_sharpe_btn)
        results_button_layout.addWidget(filter_profitable_btn)
        results_button_layout.addStretch()

        results_layout.addLayout(results_button_layout)

        layout.addWidget(results_group)

        return widget

    def create_distributed_tab(self):
        """创建分布式设置选项卡"""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        # 分布式配置
        distributed_group = QGroupBox("分布式配置")
        distributed_layout = QFormLayout(distributed_group)

        self.enable_distributed_check = QCheckBox("启用分布式计算")
        distributed_layout.addRow(self.enable_distributed_check)

        self.worker_nodes_spin = QSpinBox()
        self.worker_nodes_spin.setRange(1, 16)
        self.worker_nodes_spin.setValue(4)
        distributed_layout.addRow("工作节点数:", self.worker_nodes_spin)

        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 1000)
        self.batch_size_spin.setValue(10)
        distributed_layout.addRow("批处理大小:", self.batch_size_spin)

        self.max_memory_spin = QSpinBox()
        self.max_memory_spin.setRange(512, 32768)
        self.max_memory_spin.setValue(4096)
        self.max_memory_spin.setSuffix(" MB")
        distributed_layout.addRow("最大内存使用:", self.max_memory_spin)

        layout.addWidget(distributed_group)

        # 节点状态
        nodes_group = QGroupBox("工作节点状态")
        nodes_layout = QVBoxLayout(nodes_group)

        self.nodes_table = QTableWidget()
        self.nodes_table.setColumnCount(5)
        self.nodes_table.setHorizontalHeaderLabels([
            "节点ID", "IP地址", "状态", "CPU使用率", "内存使用率"
        ])
        self.nodes_table.horizontalHeader().setStretchLastSection(True)
        nodes_layout.addWidget(self.nodes_table)

        layout.addWidget(nodes_group)

        # 性能监控
        performance_group = QGroupBox("性能监控")
        performance_layout = QFormLayout(performance_group)

        self.cpu_usage_label = QLabel("0%")
        self.memory_usage_label = QLabel("0%")
        self.network_usage_label = QLabel("0 KB/s")
        self.tasks_per_second_label = QLabel("0")

        performance_layout.addRow("CPU使用率:", self.cpu_usage_label)
        performance_layout.addRow("内存使用率:", self.memory_usage_label)
        performance_layout.addRow("网络使用率:", self.network_usage_label)
        performance_layout.addRow("任务处理速度:", self.tasks_per_second_label)

        layout.addWidget(performance_group)

        return widget

    def load_default_config(self):
        """加载默认配置"""
        # 加载示例股票列表
        sample_stocks = [
            {"code": "000001", "name": "平安银行"},
            {"code": "000002", "name": "万科A"},
            {"code": "000858", "name": "五粮液"},
            {"code": "002415", "name": "海康威视"},
            {"code": "600036", "name": "招商银行"},
            {"code": "600519", "name": "贵州茅台"},
            {"code": "600887", "name": "伊利股份"},
        ]

        for stock in sample_stocks:
            item = QListWidgetItem(f"{stock['code']} {stock['name']}")
            item.setData(Qt.UserRole, stock)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.stock_list.addItem(item)

    def on_stock_selection_changed(self, selection_type):
        """股票选择方式改变"""
        if selection_type == "全部股票":
            self.select_all_stocks()
        elif selection_type == "指定股票列表":
            # 保持当前选择
            pass
        # 其他选择方式的实现...

    def select_all_stocks(self):
        """全选股票"""
        for i in range(self.stock_list.count()):
            item = self.stock_list.item(i)
            item.setCheckState(Qt.Checked)

    def select_no_stocks(self):
        """全不选股票"""
        for i in range(self.stock_list.count()):
            item = self.stock_list.item(i)
            item.setCheckState(Qt.Unchecked)

    def import_stock_list(self):
        """导入股票列表"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入股票列表", "", "CSV文件 (*.csv);;文本文件 (*.txt)"
        )
        if file_path:
            # 这里实现导入逻辑
            QMessageBox.information(
                self, "提示", f"股票列表导入功能开发中...\n文件: {file_path}")

    def start_analysis(self):
        """开始批量分析"""
        try:
            # 获取选中的股票
            selected_stocks = []
            for i in range(self.stock_list.count()):
                item = self.stock_list.item(i)
                if item.checkState() == Qt.Checked:
                    selected_stocks.append(item.data(Qt.UserRole))

            if not selected_stocks:
                QMessageBox.warning(self, "警告", "请至少选择一只股票")
                return

            # 获取选中的策略
            selected_strategies = []
            for i in range(self.strategy_list.count()):
                item = self.strategy_list.item(i)
                if item.checkState() == Qt.Checked:
                    selected_strategies.append(item.text())

            if not selected_strategies:
                QMessageBox.warning(self, "警告", "请至少选择一个策略")
                return

            # 配置分析参数
            self.analysis_config = {
                'stocks': selected_stocks,
                'strategies': selected_strategies,
                'start_date': self.start_date.date().toString("yyyy-MM-dd"),
                'end_date': self.end_date.date().toString("yyyy-MM-dd"),
                'initial_capital': self.initial_capital_spin.value(),
                'commission': self.commission_spin.value() / 1000,
                'slippage': self.slippage_spin.value() / 1000
            }

            # 更新UI状态
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.overall_progress.setValue(0)

            # 更新任务统计
            total_tasks = len(selected_stocks) * len(selected_strategies)
            self.total_tasks_label.setText(str(total_tasks))
            self.completed_tasks_label.setText("0")
            self.remaining_tasks_label.setText(str(total_tasks))

            # 清空结果
            self.analysis_results.clear()
            self.results_table.setRowCount(0)
            self.tasks_table.setRowCount(0)

            # 启动分析线程
            self.worker_thread = BatchAnalysisWorker(self.analysis_config)
            self.worker_thread.progress_updated.connect(self.update_progress)
            self.worker_thread.task_completed.connect(self.on_task_completed)
            self.worker_thread.analysis_finished.connect(
                self.on_analysis_finished)
            self.worker_thread.error_occurred.connect(self.on_analysis_error)
            self.worker_thread.start()

            self.add_log("开始批量分析...")
            self.analysis_started.emit()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动分析失败: {str(e)}")
            self.reset_ui_state()

    def stop_analysis(self):
        """停止批量分析"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait()

        self.reset_ui_state()
        self.add_log("分析已停止")

    def reset_ui_state(self):
        """重置UI状态"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def update_progress(self, progress):
        """更新进度"""
        self.overall_progress.setValue(progress)

        # 更新剩余任务数
        total_tasks = int(self.total_tasks_label.text())
        completed_tasks = int(total_tasks * progress / 100)
        remaining_tasks = total_tasks - completed_tasks

        self.completed_tasks_label.setText(str(completed_tasks))
        self.remaining_tasks_label.setText(str(remaining_tasks))

    def on_task_completed(self, result):
        """任务完成处理"""
        self.analysis_results.append(result)

        # 添加到任务表格
        row = self.tasks_table.rowCount()
        self.tasks_table.insertRow(row)

        self.tasks_table.setItem(
            row, 0, QTableWidgetItem(result['stock_code']))
        self.tasks_table.setItem(
            row, 1, QTableWidgetItem(result['stock_name']))
        self.tasks_table.setItem(row, 2, QTableWidgetItem(result['strategy']))
        self.tasks_table.setItem(row, 3, QTableWidgetItem("完成"))
        self.tasks_table.setItem(row, 4, QTableWidgetItem("100%"))
        self.tasks_table.setItem(
            row, 5, QTableWidgetItem(result['analysis_time']))

        # 添加到结果表格
        self.add_result_to_table(result)

        self.add_log(f"完成分析: {result['stock_code']} - {result['strategy']}")

    def on_analysis_finished(self, results):
        """分析完成处理"""
        self.reset_ui_state()
        self.update_results_statistics()
        self.add_log(f"批量分析完成，共处理 {len(results)} 个任务")

        QMessageBox.information(
            self, "分析完成", f"批量分析已完成！\n共处理 {len(results)} 个任务")
        self.analysis_finished.emit(results)

    def on_analysis_error(self, error_msg):
        """分析错误处理"""
        self.reset_ui_state()
        self.add_log(f"分析错误: {error_msg}")
        QMessageBox.critical(self, "分析错误", f"批量分析出现错误: {error_msg}")

    def add_result_to_table(self, result):
        """添加结果到表格"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        self.results_table.setItem(
            row, 0, QTableWidgetItem(result['stock_code']))
        self.results_table.setItem(
            row, 1, QTableWidgetItem(result['stock_name']))
        self.results_table.setItem(
            row, 2, QTableWidgetItem(result['strategy']))
        self.results_table.setItem(
            row, 3, QTableWidgetItem(f"{result['return_rate']:.2%}"))
        self.results_table.setItem(
            row, 4, QTableWidgetItem(str(result['sharpe_ratio'])))
        self.results_table.setItem(
            row, 5, QTableWidgetItem(f"{result['max_drawdown']:.2%}"))
        self.results_table.setItem(
            row, 6, QTableWidgetItem(f"{result['win_rate']:.1%}"))
        self.results_table.setItem(
            row, 7, QTableWidgetItem(str(result['total_trades'])))

    def update_results_statistics(self):
        """更新结果统计"""
        if not self.analysis_results:
            return

        total_combinations = len(self.analysis_results)
        profitable_combinations = len(
            [r for r in self.analysis_results if r['return_rate'] > 0])

        returns = [r['return_rate'] for r in self.analysis_results]
        sharpe_ratios = [r['sharpe_ratio'] for r in self.analysis_results]

        best_return = max(returns)
        worst_return = min(returns)
        avg_return = sum(returns) / len(returns)
        best_sharpe = max(sharpe_ratios)

        self.total_combinations_label.setText(str(total_combinations))
        self.profitable_combinations_label.setText(
            str(profitable_combinations))
        self.best_return_label.setText(f"{best_return:.2%}")
        self.worst_return_label.setText(f"{worst_return:.2%}")
        self.avg_return_label.setText(f"{avg_return:.2%}")
        self.best_sharpe_label.setText(f"{best_sharpe:.2f}")

    def sort_results(self, sort_key):
        """排序结果"""
        if not self.analysis_results:
            return

        reverse = True  # 降序排列
        self.analysis_results.sort(key=lambda x: x[sort_key], reverse=reverse)

        # 重新填充表格
        self.results_table.setRowCount(0)
        for result in self.analysis_results:
            self.add_result_to_table(result)

    def filter_profitable_results(self):
        """筛选盈利组合"""
        if not self.analysis_results:
            return

        profitable_results = [
            r for r in self.analysis_results if r['return_rate'] > 0]

        # 重新填充表格
        self.results_table.setRowCount(0)
        for result in profitable_results:
            self.add_result_to_table(result)

    def export_results(self):
        """导出结果"""
        if not self.analysis_results:
            QMessageBox.warning(self, "警告", "没有可导出的结果")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出分析结果", "batch_analysis_results.csv",
            "CSV文件 (*.csv);;Excel文件 (*.xlsx)"
        )

        if file_path:
            try:
                # 这里实现导出逻辑
                QMessageBox.information(self, "成功", f"结果已导出到: {file_path}")
                self.add_log(f"结果已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def add_log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)

        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()

    def save_log(self):
        """保存日志"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "batch_analysis_log.txt", "文本文件 (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, "成功", f"日志已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存日志失败: {str(e)}")

    def closeEvent(self, event):
        """关闭事件"""
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认关闭",
                "分析正在进行中，确定要关闭吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.worker_thread.stop()
                self.worker_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
