"""
选股策略组件

提供多种选股策略，包括技术指标筛选、基本面筛选、资金流向筛选等
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QFrame, QGridLayout, QProgressBar, QFileDialog,
                             QGroupBox, QSplitter, QComboBox, QSpinBox,
                             QDoubleSpinBox, QCheckBox, QFormLayout, QInputDialog,
                             QMessageBox, QProgressDialog, QListWidget, QAbstractItemView,
                             QLineEdit)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QPainter, QFont
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union
from core.data_manager import DataManager
from core.logger import LogManager, LogLevel
from core.stock_screener import StockScreener
from datetime import datetime
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
import json
import traceback


class StockScreenerWidget(QWidget):
    """选股策略组件"""

    def __init__(self, parent=None, data_manager=None, log_manager=None):
        """初始化选股策略组件

        Args:
            parent: 父窗口
            data_manager: 数据管理器实例
            log_manager: 日志管理器实例
        """
        super().__init__(parent)
        self.setFont(QFont("Microsoft YaHei", 10))  # 设置默认字体为微软雅黑

        # 初始化数据管理器
        self.data_manager = data_manager
        self.log_manager = log_manager or LogManager()
        self.screener = StockScreener(data_manager, log_manager)

        # 初始化UI
        self.init_ui()

        # 初始化条件和模板
        self.conditions = []
        self.templates = {}
        self.load_templates()

    def init_ui(self):
        """Initialize UI components"""
        try:
            # Create main layout
            layout = QVBoxLayout(self)

            # Create strategy selection group
            strategy_group = QGroupBox("选股策略")
            strategy_layout = QVBoxLayout(strategy_group)

            # Add strategy type selector
            self.strategy_type = QComboBox()
            self.strategy_type.addItems([
                "技术指标选股",
                "基本面选股",
                "资金面选股",
                "综合选股"
            ])
            self.strategy_type.currentTextChanged.connect(
                self.on_strategy_changed)
            strategy_layout.addWidget(self.strategy_type)

            # Add template management
            template_layout = QHBoxLayout()

            # Add template selector
            self.template_combo = QComboBox()
            self.template_combo.currentTextChanged.connect(
                self.on_template_changed)
            template_layout.addWidget(self.template_combo)

            # Add template buttons
            load_button = QPushButton("加载模板")
            load_button.clicked.connect(self.load_template)
            template_layout.addWidget(load_button)

            save_button = QPushButton("保存模板")
            save_button.clicked.connect(self.save_template)
            template_layout.addWidget(save_button)

            delete_button = QPushButton("删除模板")
            delete_button.clicked.connect(self.delete_template)
            template_layout.addWidget(delete_button)

            strategy_layout.addLayout(template_layout)

            # Add to main layout
            layout.addWidget(strategy_group)

            # Create condition settings group
            self.condition_group = QGroupBox("选股条件")
            self.condition_layout = QVBoxLayout(self.condition_group)
            layout.addWidget(self.condition_group)

            # Create result display group
            self.result_group = QGroupBox("选股结果")
            result_layout = QVBoxLayout(self.result_group)

            # Add result table first
            self.result_table = QTableWidget()
            self.result_table.setColumnCount(5)
            self.result_table.setHorizontalHeaderLabels([
                "股票代码", "股票名称", "最新价", "涨跌幅", "筛选得分"
            ])
            self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.result_table.setSelectionMode(QTableWidget.SingleSelection)
            self.result_table.itemSelectionChanged.connect(
                self.on_stock_selected)
            result_layout.addWidget(self.result_table)

            # Add sorting functions after result table is created
            self.add_sorting_functions()

            # Add filter functions
            self.add_filter_functions()

            # Add action buttons
            buttons_layout = QHBoxLayout()

            screen_button = QPushButton("开始选股")
            screen_button.clicked.connect(self.run_screener)
            buttons_layout.addWidget(screen_button)

            export_button = QPushButton("导出结果")
            export_button.clicked.connect(self.export_results)
            buttons_layout.addWidget(export_button)

            save_button = QPushButton("保存策略")
            save_button.clicked.connect(self.save_strategy)
            buttons_layout.addWidget(save_button)

            result_layout.addLayout(buttons_layout)
            layout.addWidget(self.result_group)

            # Initialize condition settings
            self.on_strategy_changed(self.strategy_type.currentText())

            # Load templates
            self.load_templates()

            # Add chart functions
            self.add_chart_functions()

        except Exception as e:
            self.log_manager.log(f"初始化UI失败: {str(e)}", LogLevel.ERROR)
            raise

    def on_strategy_changed(self, strategy_type: str):
        """Handle strategy type change

        Args:
            strategy_type: Selected strategy type
        """
        try:
            # Clear condition layout
            while self.condition_layout.count():
                item = self.condition_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add condition settings based on strategy type
            if strategy_type == "技术指标选股":
                self.add_technical_conditions()
            elif strategy_type == "基本面选股":
                self.add_fundamental_conditions()
            elif strategy_type == "资金面选股":
                self.add_capital_conditions()
            else:
                self.add_comprehensive_conditions()

        except Exception as e:
            self.log_manager.log(f"更新策略设置失败: {str(e)}", LogLevel.ERROR)

    def add_technical_conditions(self):
        """Add technical indicator conditions"""
        try:
            # Add MA condition
            ma_layout = QHBoxLayout()
            ma_layout.addWidget(QLabel("均线条件:"))

            self.ma_type = QComboBox()
            self.ma_type.addItems(["MA5", "MA10", "MA20", "MA60"])
            ma_layout.addWidget(self.ma_type)

            self.ma_condition = QComboBox()
            self.ma_condition.addItems(["上穿", "下穿", "金叉", "死叉"])
            ma_layout.addWidget(self.ma_condition)

            self.condition_layout.addLayout(ma_layout)

            # Add MACD condition
            macd_layout = QHBoxLayout()
            macd_layout.addWidget(QLabel("MACD条件:"))

            self.macd_condition = QComboBox()
            self.macd_condition.addItems(["金叉", "死叉", "红柱", "绿柱"])
            macd_layout.addWidget(self.macd_condition)

            self.condition_layout.addLayout(macd_layout)

            # Add RSI condition
            rsi_layout = QHBoxLayout()
            rsi_layout.addWidget(QLabel("RSI条件:"))

            self.rsi_period = QSpinBox()
            self.rsi_period.setRange(5, 30)
            self.rsi_period.setValue(14)
            rsi_layout.addWidget(self.rsi_period)

            self.rsi_condition = QComboBox()
            self.rsi_condition.addItems(["超买", "超卖", "背离"])
            rsi_layout.addWidget(self.rsi_condition)

            self.condition_layout.addLayout(rsi_layout)

        except Exception as e:
            self.log_manager.log(f"添加技术指标条件失败: {str(e)}", LogLevel.ERROR)

    def add_fundamental_conditions(self):
        """Add fundamental conditions"""
        try:
            # Add PE condition
            pe_layout = QHBoxLayout()
            pe_layout.addWidget(QLabel("市盈率:"))

            self.pe_min = QDoubleSpinBox()
            self.pe_min.setDecimals(2)
            self.pe_min.setRange(0.0, 100.0)
            self.pe_min.setValue(0.0)
            pe_layout.addWidget(self.pe_min)

            pe_layout.addWidget(QLabel("至"))

            self.pe_max = QDoubleSpinBox()
            self.pe_max.setDecimals(2)
            self.pe_max.setRange(0.0, 100.0)
            self.pe_max.setValue(100.0)
            pe_layout.addWidget(self.pe_max)

            self.condition_layout.addLayout(pe_layout)

            # Add PB condition
            pb_layout = QHBoxLayout()
            pb_layout.addWidget(QLabel("市净率:"))

            self.pb_min = QDoubleSpinBox()
            self.pb_min.setDecimals(2)
            self.pb_min.setRange(0.0, 10.0)
            self.pb_min.setValue(0.0)
            pb_layout.addWidget(self.pb_min)

            pb_layout.addWidget(QLabel("至"))

            self.pb_max = QDoubleSpinBox()
            self.pb_max.setDecimals(2)
            self.pb_max.setRange(0.0, 10.0)
            self.pb_max.setValue(10.0)
            pb_layout.addWidget(self.pb_max)

            self.condition_layout.addLayout(pb_layout)

            # Add ROE condition
            roe_layout = QHBoxLayout()
            roe_layout.addWidget(QLabel("净资产收益率:"))

            self.roe_min = QDoubleSpinBox()
            self.roe_min.setDecimals(2)
            self.roe_min.setRange(0.0, 100.0)
            self.roe_min.setValue(10.0)
            self.roe_min.setSuffix(" %")
            roe_layout.addWidget(self.roe_min)

            self.condition_layout.addLayout(roe_layout)

        except Exception as e:
            self.log_manager.log(f"添加基本面条件失败: {str(e)}", LogLevel.ERROR)

    def add_capital_conditions(self):
        """Add capital flow conditions"""
        try:
            # Add main net inflow condition
            inflow_layout = QHBoxLayout()
            inflow_layout.addWidget(QLabel("主力净流入:"))

            self.inflow_min = QDoubleSpinBox()
            self.inflow_min.setDecimals(2)
            self.inflow_min.setRange(0.0, 1000000.0)
            self.inflow_min.setValue(100000.0)
            self.inflow_min.setSuffix(" 万元")
            inflow_layout.addWidget(self.inflow_min)

            self.condition_layout.addLayout(inflow_layout)

            # Add volume condition
            volume_layout = QHBoxLayout()
            volume_layout.addWidget(QLabel("成交量:"))

            self.volume_min = QDoubleSpinBox()
            self.volume_min.setDecimals(2)
            self.volume_min.setRange(0.0, 1000000.0)
            self.volume_min.setValue(100000.0)
            self.volume_min.setSuffix(" 手")
            volume_layout.addWidget(self.volume_min)

            self.condition_layout.addLayout(volume_layout)

        except Exception as e:
            self.log_manager.log(f"添加资金面条件失败: {str(e)}", LogLevel.ERROR)

    def add_comprehensive_conditions(self):
        """Add comprehensive conditions"""
        try:
            # Add technical weight
            tech_layout = QHBoxLayout()
            tech_layout.addWidget(QLabel("技术指标权重:"))

            self.tech_weight = QDoubleSpinBox()
            self.tech_weight.setDecimals(2)
            self.tech_weight.setRange(0.0, 1.0)
            self.tech_weight.setValue(0.4)
            self.tech_weight.setSingleStep(0.1)
            tech_layout.addWidget(self.tech_weight)

            self.condition_layout.addLayout(tech_layout)

            # Add fundamental weight
            fund_layout = QHBoxLayout()
            fund_layout.addWidget(QLabel("基本面权重:"))

            self.fund_weight = QDoubleSpinBox()
            self.fund_weight.setDecimals(2)
            self.fund_weight.setRange(0.0, 1.0)
            self.fund_weight.setValue(0.3)
            self.fund_weight.setSingleStep(0.1)
            fund_layout.addWidget(self.fund_weight)

            self.condition_layout.addLayout(fund_layout)

            # Add capital weight
            cap_layout = QHBoxLayout()
            cap_layout.addWidget(QLabel("资金面权重:"))

            self.cap_weight = QDoubleSpinBox()
            self.cap_weight.setDecimals(2)
            self.cap_weight.setRange(0.0, 1.0)
            self.cap_weight.setValue(0.3)
            self.cap_weight.setSingleStep(0.1)
            cap_layout.addWidget(self.cap_weight)

            self.condition_layout.addLayout(cap_layout)

        except Exception as e:
            self.log_manager.log(f"添加综合条件失败: {str(e)}", LogLevel.ERROR)

    def run_screener(self):
        """运行选股器"""
        try:
            # 禁用运行按钮,避免重复点击
            QTimer.singleShot(0, lambda: self.run_button.setEnabled(False))

            # 获取选股条件
            conditions = self._get_screener_conditions()
            if not conditions:
                return

            # 在新线程中运行选股
            self.screener_thread = QThread()
            self.screener_worker = StockScreenerWorker(conditions)
            self.screener_worker.moveToThread(self.screener_thread)

            # 连接信号
            self.screener_thread.started.connect(self.screener_worker.run)
            self.screener_worker.finished.connect(self.screener_thread.quit)
            self.screener_worker.finished.connect(
                self.screener_worker.deleteLater)
            self.screener_thread.finished.connect(
                self.screener_thread.deleteLater)
            self.screener_worker.progress.connect(self._update_progress)
            self.screener_worker.result.connect(self._handle_screener_result)

            # 启动线程
            self.screener_thread.start()

        except Exception as e:
            self.log_manager.log(f"启动选股失败: {e}", LogLevel.ERROR)
            QTimer.singleShot(0, lambda: self.run_button.setEnabled(True))

    def _update_progress(self, progress: int):
        """更新进度条

        Args:
            progress: 进度值(0-100)
        """
        try:
            QTimer.singleShot(0, lambda: self.progress_bar.setValue(progress))
        except Exception as e:
            self.log_manager.log(f"更新进度条失败: {e}", LogLevel.ERROR)

    def _handle_screener_result(self, result: dict):
        """处理选股结果

        Args:
            result: 选股结果字典
        """
        try:
            QTimer.singleShot(0, lambda: self._update_ui_safely(result))
        except Exception as e:
            self.log_manager.log(f"处理选股结果失败: {e}", LogLevel.ERROR)

    def _update_ui_safely(self, result: dict):
        """在主线程中安全地更新UI

        Args:
            result: 选股结果字典
        """
        try:
            # 更新结果表格
            self.update_result_table(result.get('stocks', []))

            # 更新统计信息
            self._update_statistics(result.get('stats', {}))

            # 更新图表
            self._update_distribution_chart()

            # 启用运行按钮
            self.run_button.setEnabled(True)

            # 重置进度条
            self.progress_bar.setValue(0)

        except Exception as e:
            self.log_manager.log(f"更新UI失败: {e}", LogLevel.ERROR)
            self.run_button.setEnabled(True)

    def on_stock_selected(self):
        """Handle stock selection in result table"""
        try:
            # Get selected row
            selected_items = self.result_table.selectedItems()
            if not selected_items:
                return

            # Get stock code
            stock_code = selected_items[0].text()

            # Emit signal to parent
            if hasattr(self.parent(), 'on_stock_selected'):
                self.parent().on_stock_selected(stock_code)

        except Exception as e:
            self.log_manager.log(f"处理股票选择失败: {str(e)}", LogLevel.ERROR)

    def export_results(self):
        """导出选股结果"""
        try:
            # 获取当前数据
            data = []
            for row in range(self.result_table.rowCount()):
                data.append({
                    'code': self.result_table.item(row, 0).text(),
                    'name': self.result_table.item(row, 1).text(),
                    'close': float(self.result_table.item(row, 2).text()),
                    'change_percent': float(self.result_table.item(row, 3).text().rstrip('%')),
                    'score': float(self.result_table.item(row, 4).text())
                })

            if not data:
                QMessageBox.warning(self, "警告", "没有可导出的数据")
                return

            # 转换为DataFrame
            df = pd.DataFrame(data)

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出选股结果",
                f"选股结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )

            if file_path:
                # 根据文件类型保存
                if file_path.endswith('.xlsx'):
                    df.to_excel(file_path, index=False)
                else:
                    df.to_csv(file_path, index=False)

                self.log_manager.log(f"选股结果已导出到: {file_path}", LogLevel.INFO)
                QMessageBox.information(self, "成功", "选股结果导出成功")

        except Exception as e:
            self.log_manager.log(f"导出选股结果失败: {str(e)}", LogLevel.ERROR)
            QMessageBox.critical(self, "错误", f"导出选股结果失败: {str(e)}")

    def save_strategy(self):
        """保存当前选股策略"""
        try:
            # 获取当前策略设置
            strategy_type = self.strategy_type.currentText()
            conditions = self.get_current_conditions()

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存选股策略",
                f"选股策略_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "JSON Files (*.json)"
            )

            if file_path:
                # 构建策略数据
                strategy_data = {
                    'strategy_type': strategy_type,
                    'conditions': conditions,
                    'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(strategy_data, f, ensure_ascii=False, indent=4)

                self.log_manager.log(f"选股策略已保存到: {file_path}", LogLevel.INFO)
                QMessageBox.information(self, "成功", "选股策略保存成功")

        except Exception as e:
            self.log_manager.log(f"保存选股策略失败: {str(e)}", LogLevel.ERROR)
            QMessageBox.critical(self, "错误", f"保存选股策略失败: {str(e)}")

    def load_strategy(self):
        """加载选股策略"""
        try:
            # 获取文件路径
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "加载选股策略",
                "",
                "JSON Files (*.json)"
            )

            if file_path:
                # 读取策略数据
                with open(file_path, 'r', encoding='utf-8') as f:
                    strategy_data = json.load(f)

                # 更新策略类型
                index = self.strategy_type.findText(
                    strategy_data['strategy_type'])
                if index >= 0:
                    self.strategy_type.setCurrentIndex(index)

                # 更新条件设置
                self.update_conditions(strategy_data['conditions'])

                self.log_manager.log(f"已加载选股策略: {file_path}", LogLevel.INFO)

                # 显示成功对话框
                dialog = QMessageBox(self)
                dialog.setWindowTitle("成功")
                dialog.setIcon(QMessageBox.Information)
                dialog.setText("选股策略加载成功")
                dialog.setStandardButtons(QMessageBox.Ok)

                # 显示对话框并居中
                dialog.show()
                self.center_dialog(dialog, self)
                dialog.exec_()

        except Exception as e:
            self.log_manager.log(f"加载选股策略失败: {str(e)}", LogLevel.ERROR)

            # 显示错误对话框
            dialog = QMessageBox(self)
            dialog.setWindowTitle("错误")
            dialog.setIcon(QMessageBox.Critical)
            dialog.setText(f"加载选股策略失败: {str(e)}")
            dialog.setStandardButtons(QMessageBox.Ok)

            # 显示对话框并居中
            dialog.show()
            self.center_dialog(dialog, self)
            dialog.exec_()

    def get_current_conditions(self) -> dict:
        """获取当前UI中设置的选股条件

        Returns:
            dict: 选股条件字典
        """
        try:
            strategy_type = self.strategy_type.currentText()
            conditions = {}

            if strategy_type == "技术指标选股":
                conditions = {
                    "ma_type": self.ma_type.currentText(),
                    "ma_condition": self.ma_condition.currentText(),
                    "macd_condition": self.macd_condition.currentText(),
                    "rsi_period": self.rsi_period.value(),
                    "rsi_condition": self.rsi_condition.currentText()
                }
            elif strategy_type == "基本面选股":
                conditions = {
                    "pe_min": self.pe_min.value(),
                    "pe_max": self.pe_max.value(),
                    "pb_min": self.pb_min.value(),
                    "pb_max": self.pb_max.value(),
                    "roe_min": self.roe_min.value()
                }
            elif strategy_type == "资金面选股":
                conditions = {
                    "inflow_min": self.inflow_min.value(),
                    "volume_min": self.volume_min.value()
                }
            else:  # 综合选股
                conditions = {
                    "tech_weight": self.tech_weight.value(),
                    "fund_weight": self.fund_weight.value(),
                    "cap_weight": self.cap_weight.value()
                }

            return conditions

        except Exception as e:
            self.log_manager.log(f"获取选股条件失败: {str(e)}", LogLevel.ERROR)
            return {}

    def load_templates(self):
        """加载策略模板列表"""
        try:
            # 清空模板列表
            self.template_combo.clear()

            # 获取模板列表
            templates = self.screener.list_templates()
            self.template_combo.addItems(templates)

        except Exception as e:
            self.log_manager.log(f"加载模板列表失败: {str(e)}", LogLevel.ERROR)

    def on_template_changed(self, template_name: str):
        """处理模板选择变更

        Args:
            template_name: 选中的模板名称
        """
        try:
            if not template_name:
                return

            # 加载模板
            strategy_type, conditions = self.screener.load_strategy(
                template_name)
            if strategy_type and conditions:
                # 更新策略类型
                index = self.strategy_type.findText(strategy_type)
                if index >= 0:
                    self.strategy_type.setCurrentIndex(index)

                # 更新条件设置
                self.update_conditions(conditions)

        except Exception as e:
            self.log_manager.log(f"加载模板失败: {str(e)}", LogLevel.ERROR)

    def update_conditions(self, conditions: dict):
        """更新选股条件设置

        Args:
            conditions: 选股条件字典
        """
        try:
            strategy_type = self.strategy_type.currentText()

            if strategy_type == "技术指标选股":
                # 更新技术指标条件
                if 'ma_type' in conditions:
                    index = self.ma_type.findText(conditions['ma_type'])
                    if index >= 0:
                        self.ma_type.setCurrentIndex(index)

                if 'ma_condition' in conditions:
                    index = self.ma_condition.findText(
                        conditions['ma_condition'])
                    if index >= 0:
                        self.ma_condition.setCurrentIndex(index)

                if 'macd_condition' in conditions:
                    index = self.macd_condition.findText(
                        conditions['macd_condition'])
                    if index >= 0:
                        self.macd_condition.setCurrentIndex(index)

                if 'rsi_period' in conditions:
                    self.rsi_period.setValue(conditions['rsi_period'])

                if 'rsi_condition' in conditions:
                    index = self.rsi_condition.findText(
                        conditions['rsi_condition'])
                    if index >= 0:
                        self.rsi_condition.setCurrentIndex(index)

            elif strategy_type == "基本面选股":
                # 更新基本面条件
                if 'pe_min' in conditions:
                    self.pe_min.setValue(conditions['pe_min'])

                if 'pe_max' in conditions:
                    self.pe_max.setValue(conditions['pe_max'])

                if 'pb_min' in conditions:
                    self.pb_min.setValue(conditions['pb_min'])

                if 'pb_max' in conditions:
                    self.pb_max.setValue(conditions['pb_max'])

                if 'roe_min' in conditions:
                    self.roe_min.setValue(conditions['roe_min'])

            elif strategy_type == "资金面选股":
                # 更新资金面条件
                if 'inflow_min' in conditions:
                    self.inflow_min.setValue(conditions['inflow_min'])

                if 'volume_min' in conditions:
                    self.volume_min.setValue(conditions['volume_min'])

            else:  # 综合选股
                # 更新综合条件
                if 'tech_weight' in conditions:
                    self.tech_weight.setValue(conditions['tech_weight'])

                if 'fund_weight' in conditions:
                    self.fund_weight.setValue(conditions['fund_weight'])

                if 'cap_weight' in conditions:
                    self.cap_weight.setValue(conditions['cap_weight'])

        except Exception as e:
            self.log_manager.log(f"更新选股条件失败: {str(e)}", LogLevel.ERROR)
            QMessageBox.critical(self, "错误", f"更新选股条件失败: {str(e)}")

    def save_template(self):
        """保存当前策略为模板"""
        try:
            # 获取模板名称
            template_name, ok = QInputDialog.getText(
                self,
                "保存模板",
                "请输入模板名称:",
                text=f"{self.strategy_type.currentText()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            if ok and template_name:
                # 获取当前策略设置
                strategy_type = self.strategy_type.currentText()
                conditions = self.get_current_conditions()

                # 保存模板
                self.screener.save_strategy(
                    strategy_type, conditions, template_name)

                # 重新加载模板列表
                self.load_templates()

        except Exception as e:
            self.log_manager.log(f"保存模板失败: {str(e)}", LogLevel.ERROR)

    def delete_template(self):
        """删除选中的模板"""
        try:
            template_name = self.template_combo.currentText()
            if not template_name:
                return

            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除模板 '{template_name}' 吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 删除模板
                self.screener.delete_template(template_name)

                # 重新加载模板列表
                self.load_templates()

        except Exception as e:
            self.log_manager.log(f"删除模板失败: {str(e)}", LogLevel.ERROR)

    def add_sorting_functions(self):
        """添加排序功能"""
        try:
            # 设置表格可排序
            self.result_table.setSortingEnabled(True)

            # 添加排序按钮
            sort_layout = QHBoxLayout()

            # 添加排序方式选择
            self.sort_combo = QComboBox()
            self.sort_combo.addItems([
                "按得分排序",
                "按涨跌幅排序",
                "按最新价排序"
            ])
            self.sort_combo.currentTextChanged.connect(self.on_sort_changed)
            sort_layout.addWidget(self.sort_combo)

            # 添加排序方向选择
            self.sort_direction = QComboBox()
            self.sort_direction.addItems([
                "降序",
                "升序"
            ])
            self.sort_direction.currentTextChanged.connect(
                self.on_sort_changed)
            sort_layout.addWidget(self.sort_direction)

            # 添加到结果组
            self.result_group.layout().insertLayout(0, sort_layout)

        except Exception as e:
            self.log_manager.log(f"添加排序功能失败: {str(e)}", LogLevel.ERROR)

    def on_sort_changed(self):
        """处理排序变更"""
        try:
            # 获取排序方式和方向
            sort_by = self.sort_combo.currentText()
            ascending = self.sort_direction.currentText() == "升序"

            # 获取当前数据
            data = []
            for row in range(self.result_table.rowCount()):
                data.append({
                    'code': self.result_table.item(row, 0).text(),
                    'name': self.result_table.item(row, 1).text(),
                    'close': float(self.result_table.item(row, 2).text()),
                    'change_percent': float(self.result_table.item(row, 3).text().rstrip('%')),
                    'score': float(self.result_table.item(row, 4).text())
                })

            # 转换为DataFrame并排序
            df = pd.DataFrame(data)
            if sort_by == "按得分排序":
                df = df.sort_values('score', ascending=ascending)
            elif sort_by == "按涨跌幅排序":
                df = df.sort_values('change_percent', ascending=ascending)
            else:  # 按最新价排序
                df = df.sort_values('close', ascending=ascending)

            # 更新表格
            self.update_result_table(df)

        except Exception as e:
            self.log_manager.log(f"处理排序变更失败: {str(e)}", LogLevel.ERROR)

    def add_filter_functions(self):
        """添加筛选功能"""
        try:
            # 添加筛选布局
            filter_layout = QHBoxLayout()

            # 添加筛选条件选择
            self.filter_combo = QComboBox()
            self.filter_combo.addItems([
                "全部",
                "得分>0.8",
                "涨跌幅>5%",
                "最新价<20"
            ])
            self.filter_combo.currentTextChanged.connect(
                self.on_filter_changed)
            filter_layout.addWidget(self.filter_combo)

            # 添加到结果组
            self.result_group.layout().insertLayout(1, filter_layout)

        except Exception as e:
            self.log_manager.log(f"添加筛选功能失败: {str(e)}", LogLevel.ERROR)

    def on_filter_changed(self):
        """处理筛选变更"""
        try:
            # 获取筛选条件
            filter_condition = self.filter_combo.currentText()

            # 获取当前数据
            data = []
            for row in range(self.result_table.rowCount()):
                data.append({
                    'code': self.result_table.item(row, 0).text(),
                    'name': self.result_table.item(row, 1).text(),
                    'close': float(self.result_table.item(row, 2).text()),
                    'change_percent': float(self.result_table.item(row, 3).text().rstrip('%')),
                    'score': float(self.result_table.item(row, 4).text())
                })

            # 转换为DataFrame并筛选
            df = pd.DataFrame(data)
            if filter_condition == "得分>0.8":
                df = df[df['score'] > 0.8]
            elif filter_condition == "涨跌幅>5%":
                df = df[df['change_percent'] > 5]
            elif filter_condition == "最新价<20":
                df = df[df['close'] < 20]

            # 更新表格
            self.update_result_table(df)

        except Exception as e:
            self.log_manager.log(f"处理筛选变更失败: {str(e)}", LogLevel.ERROR)

    def add_chart_functions(self):
        """添加图表显示功能"""
        try:
            # 创建图表组
            chart_group = QGroupBox("选股结果图表")
            chart_layout = QVBoxLayout(chart_group)

            # 创建图表类型选择
            chart_type_layout = QHBoxLayout()
            chart_type_layout.addWidget(QLabel("图表类型:"))

            self.chart_type = QComboBox()
            self.chart_type.addItems([
                "得分分布图",
                "涨跌幅分布图",
                "价格分布图"
            ])
            self.chart_type.currentTextChanged.connect(
                self.update_distribution_chart)
            chart_type_layout.addWidget(self.chart_type)

            chart_layout.addLayout(chart_type_layout)

            # 创建图表画布
            self.figure = Figure(figsize=(8, 4))
            self.canvas = FigureCanvas(self.figure)
            chart_layout.addWidget(self.canvas)

            # 添加到结果组
            self.result_group.layout().addWidget(chart_group)

            # 初始化图表
            self.update_distribution_chart()

        except Exception as e:
            self.log_manager.log(f"添加图表功能失败: {str(e)}", LogLevel.ERROR)

    def update_distribution_chart(self):
        """更新分布图/直方图，仅用于选股器等非K线业务"""
        try:
            # 清空图表
            self.figure.clear()
            # 获取当前数据
            data = []
            for row in range(self.result_table.rowCount()):
                data.append({
                    'code': self.result_table.item(row, 0).text(),
                    'name': self.result_table.item(row, 1).text(),
                    'close': float(self.result_table.item(row, 2).text()),
                    'change_percent': float(self.result_table.item(row, 3).text().rstrip('%')),
                    'score': float(self.result_table.item(row, 4).text())
                })
            if not data:
                return
            # 转换为DataFrame
            df = pd.DataFrame(data)
            # 创建子图
            ax = self.figure.add_subplot(111)
            # 根据图表类型绘制
            chart_type = self.chart_type.currentText()
            if chart_type == "得分分布图":
                ax.hist(df['score'], bins=20, alpha=0.7)
                ax.set_xlabel('筛选得分')
                ax.set_ylabel('股票数量')
                ax.set_title('筛选得分分布')
            elif chart_type == "涨跌幅分布图":
                ax.hist(df['change_percent'], bins=20, alpha=0.7)
                ax.set_xlabel('涨跌幅(%)')
                ax.set_ylabel('股票数量')
                ax.set_title('涨跌幅分布')
            else:  # 价格分布图
                ax.hist(df['close'], bins=20, alpha=0.7)
                ax.set_xlabel('最新价')
                ax.set_ylabel('股票数量')
                ax.set_title('价格分布')
            # 调整布局
            self.figure.tight_layout()
            # 更新画布
            self.canvas.draw()
        except Exception as e:
            self.log_manager.log(f"更新分布图失败: {str(e)}", LogLevel.ERROR)

    def screen_stocks(self):
        """执行股票筛选"""
        if not self.conditions:
            QMessageBox.warning(self, "警告", "请添加筛选条件")
            return

        try:
            # 创建进度对话框
            progress = QProgressDialog("正在筛选股票...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("股票筛选")
            progress.setAutoClose(True)
            progress.setAutoReset(True)

            # 获取所有股票列表
            stock_list = self.data_manager.get_stock_list()
            total_stocks = len(stock_list)
            progress.setMaximum(total_stocks)

            # 初始化结果列表
            results = []

            # 遍历股票进行筛选
            for i, stock in enumerate(stock_list):
                if progress.wasCanceled():
                    break

                # 更新进度
                progress.setValue(i)
                progress.setLabelText(
                    f"正在筛选股票: {stock['code']} - {stock['name']}")

                # 获取股票数据
                stock_data = self.data_manager.get_stock_data(stock['code'])
                if stock_data.empty:
                    continue

                # 检查是否满足所有条件
                match_score = 0
                total_conditions = len(self.conditions)

                for condition in self.conditions:
                    condition_type = condition['type']
                    condition_params = condition['params']

                    # 根据条件类型进行筛选
                    if condition_type == "技术指标":
                        if self.check_technical_condition(stock_data, condition_params):
                            match_score += 1
                    elif condition_type == "基本面":
                        if self.check_fundamental_condition(stock, condition_params):
                            match_score += 1
                    elif condition_type == "资金流向":
                        if self.check_capital_condition(stock_data, condition_params):
                            match_score += 1
                    elif condition_type == "消息面":
                        if self.check_news_condition(stock['code'], condition_params):
                            match_score += 1

                # 计算匹配度
                match_ratio = match_score / total_conditions

                # 如果匹配度大于0，添加到结果中
                if match_ratio > 0:
                    results.append({
                        'code': stock['code'],
                        'name': stock['name'],
                        'match_ratio': match_ratio
                    })

            # 更新结果表格
            self.update_result_table(results)

            # 显示完成消息
            QMessageBox.information(
                self,
                "完成",
                f"筛选完成，共找到 {len(results)} 只符合条件的股票"
            )

        except Exception as e:
            QMessageBox.critical(self, "错误", f"筛选过程中发生错误: {str(e)}")

    def check_technical_condition(self, stock_data, condition_params):
        """检查技术指标条件"""
        try:
            # 解析条件参数
            # 示例：MA5>MA10
            parts = condition_params.split('>')
            if len(parts) != 2:
                return False

            indicator1 = parts[0].strip()
            indicator2 = parts[1].strip()

            # 计算指标值
            if indicator1.startswith('MA'):
                period1 = int(indicator1[2:])
                ma1 = stock_data['close'].rolling(window=period1).mean()
            else:
                return False

            if indicator2.startswith('MA'):
                period2 = int(indicator2[2:])
                ma2 = stock_data['close'].rolling(window=period2).mean()
            else:
                return False

            # 检查条件
            return ma1.iloc[-1] > ma2.iloc[-1]

        except Exception:
            return False

    def check_fundamental_condition(self, stock, condition_params):
        """检查基本面条件"""
        try:
            # 解析条件参数
            # 示例：PE<20
            parts = condition_params.split('<')
            if len(parts) != 2:
                return False

            indicator = parts[0].strip()
            value = float(parts[1].strip())

            # 获取基本面数据
            if indicator == 'PE':
                return stock['pe'] < value
            elif indicator == 'PB':
                return stock['pb'] < value
            elif indicator == 'ROE':
                return stock['roe'] > value
            else:
                return False

        except Exception:
            return False

    def check_capital_condition(self, stock_data, condition_params):
        """检查资金流向条件"""
        try:
            # 解析条件参数
            # 示例：主力净流入>1000万
            parts = condition_params.split('>')
            if len(parts) != 2:
                return False

            indicator = parts[0].strip()
            value = float(parts[1].strip()) * 10000  # 转换为元

            # 获取资金流向数据
            if indicator == '主力净流入':
                return stock_data['main_net_inflow'].iloc[-1] > value
            elif indicator == '北向资金':
                return stock_data['north_money'].iloc[-1] > value
            else:
                return False

        except Exception:
            return False

    def check_news_condition(self, stock_code, condition_params):
        """检查消息面条件"""
        try:
            # 获取股票新闻数据
            news_data = self.data_manager.get_stock_news(stock_code)

            # 检查是否包含关键词
            keywords = condition_params.split(',')
            for news in news_data:
                for keyword in keywords:
                    if keyword.strip() in news['title'] or keyword.strip() in news['content']:
                        return True

            return False

        except Exception:
            return False

    def update_result_table(self, results):
        """更新结果表格

        Args:
            results: DataFrame or list of dict containing stock screening results
        """
        try:
            # 清空表格
            self.result_table.setRowCount(0)

            if isinstance(results, pd.DataFrame):
                # 如果输入是DataFrame
                self.result_table.setRowCount(len(results))
                for i, (_, row) in enumerate(results.iterrows()):
                    # 设置股票代码
                    code_item = QTableWidgetItem(str(row['code']))
                    self.result_table.setItem(i, 0, code_item)

                    # 设置股票名称
                    name_item = QTableWidgetItem(str(row['name']))
                    self.result_table.setItem(i, 1, name_item)

                    # 设置最新价
                    close_item = QTableWidgetItem(f"{row['close']:.2f}")
                    close_item.setTextAlignment(
                        Qt.AlignRight | Qt.AlignVCenter)
                    self.result_table.setItem(i, 2, close_item)

                    # 设置涨跌幅
                    change_item = QTableWidgetItem(
                        f"{row['change_percent']:.2f}%")
                    change_item.setTextAlignment(
                        Qt.AlignRight | Qt.AlignVCenter)
                    if row['change_percent'] > 0:
                        change_item.setForeground(QColor("#FF4D4D"))
                    elif row['change_percent'] < 0:
                        change_item.setForeground(QColor("#4DB870"))
                    self.result_table.setItem(i, 3, change_item)

                    # 设置筛选得分
                    score_item = QTableWidgetItem(f"{row['score']:.2f}")
                    score_item.setTextAlignment(
                        Qt.AlignRight | Qt.AlignVCenter)
                    self.result_table.setItem(i, 4, score_item)
            else:
                # 如果输入是字典列表
                self.result_table.setRowCount(len(results))
                for i, result in enumerate(results):
                    # 设置股票代码
                    code_item = QTableWidgetItem(str(result['code']))
                    self.result_table.setItem(i, 0, code_item)

                    # 设置股票名称
                    name_item = QTableWidgetItem(str(result['name']))
                    self.result_table.setItem(i, 1, name_item)

                    # 设置最新价
                    close_item = QTableWidgetItem(f"{result['close']:.2f}")
                    close_item.setTextAlignment(
                        Qt.AlignRight | Qt.AlignVCenter)
                    self.result_table.setItem(i, 2, close_item)

                    # 设置涨跌幅
                    change_item = QTableWidgetItem(
                        f"{result['change_percent']:.2f}%")
                    change_item.setTextAlignment(
                        Qt.AlignRight | Qt.AlignVCenter)
                    if result['change_percent'] > 0:
                        change_item.setForeground(QColor("#FF4D4D"))
                    elif result['change_percent'] < 0:
                        change_item.setForeground(QColor("#4DB870"))
                    self.result_table.setItem(i, 3, change_item)

                    # 设置筛选得分
                    score_item = QTableWidgetItem(f"{result['score']:.2f}")
                    score_item.setTextAlignment(
                        Qt.AlignRight | Qt.AlignVCenter)
                    self.result_table.setItem(i, 4, score_item)

            # 调整列宽
            self.result_table.resizeColumnsToContents()

            # 更新状态
            self.log_manager.info(f"更新选股结果表格完成，共{len(results)}条记录")

        except Exception as e:
            error_msg = f"更新结果表格失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", error_msg)

    def load_template(self):
        """加载选中的模板"""
        try:
            # 获取选中的模板名称
            template_name = self.template_combo.currentText()
            if not template_name:
                QMessageBox.warning(self, "警告", "请先选择一个模板")
                return

            # 加载模板
            strategy_type, conditions = self.screener.load_strategy(
                template_name)
            if strategy_type and conditions:
                # 更新策略类型
                index = self.strategy_type.findText(strategy_type)
                if index >= 0:
                    self.strategy_type.setCurrentIndex(index)

                # 更新条件设置
                self.update_conditions(conditions)

                self.log_manager.log(f"已加载模板: {template_name}", LogLevel.INFO)
                QMessageBox.information(self, "成功", "模板加载成功")

        except Exception as e:
            self.log_manager.log(f"加载模板失败: {str(e)}", LogLevel.ERROR)
            QMessageBox.critical(self, "错误", f"加载模板失败: {str(e)}")

    def center_dialog(self, dialog, parent=None, offset_y=50):
        """将弹窗居中到父窗口或屏幕，并尽量靠近上部

        Args:
            dialog: 要居中的对话框
            parent: 父窗口，如果为None则使用屏幕
            offset_y: 距离顶部的偏移量
        """
        try:
            if parent and parent.isVisible():
                # 相对于父窗口居中
                parent_geom = parent.geometry()
                dialog_geom = dialog.frameGeometry()
                x = parent_geom.center().x() - dialog_geom.width() // 2
                y = parent_geom.top() + offset_y

                # 确保弹窗不会超出父窗口边界
                x = max(parent_geom.left(), min(
                    x, parent_geom.right() - dialog_geom.width()))
                y = max(parent_geom.top(), min(
                    y, parent_geom.bottom() - dialog_geom.height()))
            else:
                # 相对于屏幕居中
                screen = dialog.screen() or dialog.parentWidget().screen()
                if screen:
                    screen_geom = screen.geometry()
                    dialog_geom = dialog.frameGeometry()
                    x = screen_geom.center().x() - dialog_geom.width() // 2
                    y = screen_geom.top() + offset_y

                    # 确保弹窗不会超出屏幕边界
                    x = max(screen_geom.left(), min(
                        x, screen_geom.right() - dialog_geom.width()))
                    y = max(screen_geom.top(), min(
                        y, screen_geom.bottom() - dialog_geom.height()))

            dialog.move(x, y)
        except Exception as e:
            self.log_manager.log(f"设置弹窗位置失败: {str(e)}", LogLevel.ERROR)


class ScreeningThread(QThread):
    """选股线程"""

    # 定义信号
    progress_updated = pyqtSignal(int)
    screening_completed = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)

    def __init__(self, screener: 'StockScreener', strategy_type: str, conditions: dict):
        """初始化选股线程

        Args:
            screener: 选股器实例
            strategy_type: 策略类型
            conditions: 选股条件
        """
        super().__init__()
        self.screener = screener
        self.strategy_type = strategy_type
        self.conditions = conditions

    def run(self):
        """运行选股线程"""
        try:
            # 获取股票列表
            stocks = self.screener.data_manager.get_stock_list()
            total_stocks = len(stocks)

            # 初始化结果列表
            results = []

            # 遍历股票列表
            for i, stock in enumerate(stocks):
                try:
                    # 更新进度
                    progress = int((i + 1) / total_stocks * 100)
                    self.progress_updated.emit(progress)

                    # 获取股票数据
                    data = self.screener.data_manager.get_stock_data(
                        stock['code'])
                    if data is None or data.empty:
                        continue

                    # 根据策略类型筛选股票
                    if self.strategy_type == "技术指标选股":
                        if self.screener.check_technical_conditions(data, self.conditions):
                            results.append({
                                'code': stock['code'],
                                'name': stock['name'],
                                'close': data['close'].iloc[-1],
                                'change_percent': data['change_percent'].iloc[-1],
                                'score': self.screener.calculate_technical_score(data, self.conditions)
                            })
                    elif self.strategy_type == "基本面选股":
                        if self.screener.check_fundamental_conditions(data, self.conditions):
                            results.append({
                                'code': stock['code'],
                                'name': stock['name'],
                                'close': data['close'].iloc[-1],
                                'change_percent': data['change_percent'].iloc[-1],
                                'score': self.screener.calculate_fundamental_score(data, self.conditions)
                            })
                    elif self.strategy_type == "资金面选股":
                        if self.screener.check_capital_conditions(data, self.conditions):
                            results.append({
                                'code': stock['code'],
                                'name': stock['name'],
                                'close': data['close'].iloc[-1],
                                'change_percent': data['change_percent'].iloc[-1],
                                'score': self.screener.calculate_capital_score(data, self.conditions)
                            })
                    else:  # 综合选股
                        score = self.screener.calculate_comprehensive_score(
                            data, self.conditions)
                        if score > 0:
                            results.append({
                                'code': stock['code'],
                                'name': stock['name'],
                                'close': data['close'].iloc[-1],
                                'change_percent': data['change_percent'].iloc[-1],
                                'score': score
                            })

                except Exception as e:
                    self.screener.log_manager.log(
                        f"处理股票 {stock['code']} 失败: {str(e)}", LogLevel.ERROR)
                    continue

            # 转换为DataFrame并排序
            results_df = pd.DataFrame(results)
            if not results_df.empty:
                results_df = results_df.sort_values('score', ascending=False)

            # 发送完成信号
            self.screening_completed.emit(results_df)

        except Exception as e:
            # 发送错误信号
            self.error_occurred.emit(str(e))
