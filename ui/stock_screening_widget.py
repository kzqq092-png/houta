"""
选股策略UI组件

实现选股策略的用户界面,包括技术指标筛选、基本面筛选、资金流向筛选等
"""

import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QFileDialog, QDoubleSpinBox, QSpinBox,
                             QGroupBox, QFormLayout, QProgressBar, QListWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import pandas as pd
from core.stock_screener import StockScreener
from core.data_manager import DataManager
from core.logger import LogManager, LogLevel


class ScreeningWorker(QThread):
    """选股工作线程"""

    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)

    def __init__(self, screener: StockScreener, params: dict):
        """初始化工作线程

        Args:
            screener: 选股策略实例
            params: 筛选参数
        """
        super().__init__()
        self.screener = screener
        self.params = params

    def run(self):
        """执行筛选"""
        try:
            # 执行筛选
            results = self.screener.screen_stocks(
                strategy_type=self.params['strategy_type'],
                template=self.params['template'],
                technical_params=self.params['technical'],
                fundamental_params=self.params['fundamental'],
                capital_params=self.params['capital']
            )

            # 发送结果
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


class StockScreeningWidget(QWidget):
    """选股策略UI组件"""

    def __init__(self, data_manager: DataManager, log_manager: LogManager):
        """初始化选股策略UI组件

        Args:
            data_manager: 数据管理器实例
            log_manager: 日志管理器实例
        """
        super().__init__()

        # 初始化成员变量
        self.data_manager = data_manager
        self.log_manager = log_manager
        self.screener = StockScreener(data_manager, log_manager)
        self.screening_worker = None

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        if self.layout() is None:
            layout = QVBoxLayout(self)
            self.setLayout(layout)
        else:
            layout = self.layout()

        # 创建策略选择区域
        strategy_layout = QHBoxLayout()

        # 策略类型选择
        strategy_type_label = QLabel("策略类型:")
        self.strategy_type_combo = QComboBox()
        self.strategy_type_combo.addItems(
            ["技术指标筛选", "基本面筛选", "资金流向筛选", "综合筛选"])
        strategy_layout.addWidget(strategy_type_label)
        strategy_layout.addWidget(self.strategy_type_combo)

        # 策略模板选择
        template_label = QLabel("策略模板:")
        self.template_combo = QComboBox()
        self.template_combo.addItems(
            ["", "强势股筛选", "价值投资", "成长股筛选", "反转策略", "动量策略"])
        strategy_layout.addWidget(template_label)
        strategy_layout.addWidget(self.template_combo)

        # 添加到主布局
        layout.addLayout(strategy_layout)

        # 创建参数设置区域
        params_layout = QHBoxLayout()

        # 技术指标参数
        technical_group = QWidget()
        technical_layout = QVBoxLayout()
        technical_layout.addWidget(QLabel("技术指标参数"))

        # 均线参数
        ma_layout = QHBoxLayout()
        ma_layout.addWidget(QLabel("短期均线:"))
        self.ma_short_spin = QSpinBox()
        self.ma_short_spin.setRange(5, 60)
        self.ma_short_spin.setValue(5)
        ma_layout.addWidget(self.ma_short_spin)

        ma_layout.addWidget(QLabel("长期均线:"))
        self.ma_long_spin = QSpinBox()
        self.ma_long_spin.setRange(20, 250)
        self.ma_long_spin.setValue(20)
        ma_layout.addWidget(self.ma_long_spin)
        technical_layout.addLayout(ma_layout)

        # MACD参数
        macd_layout = QHBoxLayout()
        macd_layout.addWidget(QLabel("MACD信号:"))
        self.macd_signal_combo = QComboBox()
        self.macd_signal_combo.addItems(["金叉", "死叉", "多头", "空头"])
        macd_layout.addWidget(self.macd_signal_combo)
        technical_layout.addLayout(macd_layout)

        # RSI参数
        rsi_layout = QHBoxLayout()
        rsi_layout.addWidget(QLabel("RSI条件:"))
        self.rsi_operator_combo = QComboBox()
        self.rsi_operator_combo.addItems([">", "<", ">=", "<="])
        rsi_layout.addWidget(self.rsi_operator_combo)

        self.rsi_value_spin = QSpinBox()
        self.rsi_value_spin.setRange(0, 100)
        self.rsi_value_spin.setValue(50)
        rsi_layout.addWidget(self.rsi_value_spin)
        technical_layout.addLayout(rsi_layout)

        technical_group.setLayout(technical_layout)
        params_layout.addWidget(technical_group)

        # 基本面参数
        fundamental_group = QWidget()
        fundamental_layout = QVBoxLayout()
        fundamental_layout.addWidget(QLabel("基本面参数"))

        # 市盈率参数
        pe_layout = QHBoxLayout()
        pe_layout.addWidget(QLabel("市盈率范围:"))
        self.pe_min_spin = QSpinBox()
        self.pe_min_spin.setRange(0, 1000)
        pe_layout.addWidget(self.pe_min_spin)

        pe_layout.addWidget(QLabel("-"))
        self.pe_max_spin = QSpinBox()
        self.pe_max_spin.setRange(0, 1000)
        pe_layout.addWidget(self.pe_max_spin)
        fundamental_layout.addLayout(pe_layout)

        # 市净率参数
        pb_layout = QHBoxLayout()
        pb_layout.addWidget(QLabel("市净率范围:"))
        self.pb_min_spin = QSpinBox()
        self.pb_min_spin.setRange(0, 100)
        pb_layout.addWidget(self.pb_min_spin)

        pb_layout.addWidget(QLabel("-"))
        self.pb_max_spin = QSpinBox()
        self.pb_max_spin.setRange(0, 100)
        pb_layout.addWidget(self.pb_max_spin)
        fundamental_layout.addLayout(pb_layout)

        # ROE参数
        roe_layout = QHBoxLayout()
        roe_layout.addWidget(QLabel("ROE最小值:"))
        self.roe_min_spin = QSpinBox()
        self.roe_min_spin.setRange(0, 100)
        self.roe_min_spin.setValue(10)
        self.roe_min_spin.setSuffix(" %")
        roe_layout.addWidget(self.roe_min_spin)
        fundamental_layout.addLayout(roe_layout)

        fundamental_group.setLayout(fundamental_layout)
        params_layout.addWidget(fundamental_group)

        # 资金流向参数
        capital_group = QWidget()
        capital_layout = QVBoxLayout()
        capital_layout.addWidget(QLabel("资金流向参数"))

        # 主力资金参数
        main_force_layout = QHBoxLayout()
        main_force_layout.addWidget(QLabel("主力资金天数:"))
        self.main_force_days_spin = QSpinBox()
        self.main_force_days_spin.setRange(1, 30)
        self.main_force_days_spin.setValue(5)
        main_force_layout.addWidget(self.main_force_days_spin)

        main_force_layout.addWidget(QLabel("最小金额(万):"))
        self.main_force_amount_spin = QSpinBox()
        self.main_force_amount_spin.setRange(0, 100000)
        self.main_force_amount_spin.setValue(1000)
        main_force_layout.addWidget(self.main_force_amount_spin)
        capital_layout.addLayout(main_force_layout)

        # 北向资金参数
        north_layout = QHBoxLayout()
        north_layout.addWidget(QLabel("北向资金天数:"))
        self.north_days_spin = QSpinBox()
        self.north_days_spin.setRange(1, 30)
        self.north_days_spin.setValue(5)
        north_layout.addWidget(self.north_days_spin)

        north_layout.addWidget(QLabel("最小金额(万):"))
        self.north_amount_spin = QSpinBox()
        self.north_amount_spin.setRange(0, 100000)
        self.north_amount_spin.setValue(1000)
        north_layout.addWidget(self.north_amount_spin)
        capital_layout.addLayout(north_layout)

        capital_group.setLayout(capital_layout)
        params_layout.addWidget(capital_group)

        # 添加到主布局
        layout.addLayout(params_layout)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        # 开始筛选按钮
        self.start_button = QPushButton("开始筛选")
        self.start_button.clicked.connect(self.start_screening)
        button_layout.addWidget(self.start_button)

        # 导出结果按钮
        self.export_button = QPushButton("导出结果")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)

        # 添加到主布局
        layout.addLayout(button_layout)

        # 创建结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(10)
        self.result_table.setHorizontalHeaderLabels([
            "代码", "名称", "行业", "价格", "涨跌幅",
            "市盈率", "市净率", "ROE", "主力资金", "北向资金"
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.result_table)

    def start_screening(self):
        """开始筛选"""
        try:
            # 获取参数
            params = {
                'strategy_type': self.strategy_type_combo.currentText(),
                'template': self.template_combo.currentText(),
                'technical': {
                    'ma_short': self.ma_short_spin.value(),
                    'ma_long': self.ma_long_spin.value(),
                    'macd_signal': self.macd_signal_combo.currentText(),
                    'rsi_operator': self.rsi_operator_combo.currentText(),
                    'rsi_value': self.rsi_value_spin.value()
                },
                'fundamental': {
                    'pe_min': self.pe_min_spin.value(),
                    'pe_max': self.pe_max_spin.value(),
                    'pb_min': self.pb_min_spin.value(),
                    'pb_max': self.pb_max_spin.value(),
                    'roe_min': self.roe_min_spin.value()
                },
                'capital': {
                    'main_force_days': self.main_force_days_spin.value(),
                    'main_force_amount': self.main_force_amount_spin.value(),
                    'north_days': self.north_days_spin.value(),
                    'north_amount': self.north_amount_spin.value()
                }
            }

            # 创建工作线程
            self.screening_worker = ScreeningWorker(self.screener, params)
            self.screening_worker.finished.connect(self.on_screening_finished)
            self.screening_worker.error.connect(self.on_screening_error)

            # 禁用按钮
            self.start_button.setEnabled(False)
            self.export_button.setEnabled(False)

            # 开始筛选
            self.screening_worker.start()

        except Exception as e:
            self.log_manager.log(f"开始筛选失败: {str(e)}", LogLevel.ERROR)
            QMessageBox.critical(self, "错误", f"开始筛选失败: {str(e)}")

    def on_screening_finished(self, results: pd.DataFrame):
        """筛选完成回调

        Args:
            results: 筛选结果
        """
        try:
            # 更新表格
            self.update_result_table(results)

            # 启用按钮
            self.start_button.setEnabled(True)
            self.export_button.setEnabled(True)

        except Exception as e:
            self.log_manager.log(f"更新结果失败: {str(e)}", LogLevel.ERROR)
            QMessageBox.critical(self, "错误", f"更新结果失败: {str(e)}")

    def on_screening_error(self, error: str):
        """筛选错误回调

        Args:
            error: 错误信息
        """
        # 启用按钮
        self.start_button.setEnabled(True)
        self.export_button.setEnabled(False)

        # 显示错误
        self.log_manager.log(f"筛选失败: {error}", LogLevel.ERROR)
        QMessageBox.critical(self, "错误", f"筛选失败: {error}")

    def update_result_table(self, results: pd.DataFrame):
        """更新结果表格

        Args:
            results: 筛选结果
        """
        # 清空表格
        self.result_table.setRowCount(0)

        # 添加数据
        for i, row in results.iterrows():
            self.result_table.insertRow(i)

            # 添加单元格
            self.result_table.setItem(i, 0, QTableWidgetItem(row['code']))
            self.result_table.setItem(i, 1, QTableWidgetItem(row['name']))
            self.result_table.setItem(i, 2, QTableWidgetItem(row['industry']))
            self.result_table.setItem(
                i, 3, QTableWidgetItem(f"{row['price']:.2f}"))
            self.result_table.setItem(
                i, 4, QTableWidgetItem(f"{row['change']:.2f}%"))
            self.result_table.setItem(
                i, 5, QTableWidgetItem(f"{row['pe']:.2f}"))
            self.result_table.setItem(
                i, 6, QTableWidgetItem(f"{row['pb']:.2f}"))
            self.result_table.setItem(
                i, 7, QTableWidgetItem(f"{row['roe']:.2f}%"))
            self.result_table.setItem(
                i, 8, QTableWidgetItem(f"{row['main_force']:.2f}"))
            self.result_table.setItem(
                i, 9, QTableWidgetItem(f"{row['north_money']:.2f}"))

    def export_results(self):
        """导出结果"""
        try:
            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出结果", "", "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )

            if not file_path:
                return

            # 获取表格数据
            data = []
            for i in range(self.result_table.rowCount()):
                row = []
                for j in range(self.result_table.columnCount()):
                    item = self.result_table.item(i, j)
                    row.append(item.text() if item else "")
                data.append(row)

            # 创建DataFrame
            df = pd.DataFrame(data, columns=[
                "代码", "名称", "行业", "价格", "涨跌幅",
                "市盈率", "市净率", "ROE", "主力资金", "北向资金"
            ])

            # 导出数据
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)

            QMessageBox.information(self, "成功", "导出结果成功")

        except Exception as e:
            self.log_manager.log(f"导出结果失败: {str(e)}", LogLevel.ERROR)
            QMessageBox.critical(self, "错误", f"导出结果失败: {str(e)}")
