"""
优化功能模块 - 策略优化和AI功能

包含策略优化、批量分析、AI诊断、性能评估等高级功能
"""

from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextEdit, QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QFormLayout, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QIcon, QFont
from typing import Optional, Dict, Any, List
import pandas as pd
import json
import os
from core.logger import LogManager


class OptimizationThread(QThread):
    """优化线程类"""

    progress_updated = pyqtSignal(int)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, strategy, parameters, data):
        super().__init__()
        self.strategy = strategy
        self.parameters = parameters
        self.data = data

    def run(self):
        """执行优化"""
        try:
            # 模拟优化过程
            for i in range(101):
                self.progress_updated.emit(i)
                self.msleep(50)  # 模拟计算时间

            # 模拟优化结果
            result = {
                "best_params": {"param1": 10, "param2": 20},
                "best_score": 0.85,
                "total_tests": 100,
                "success_rate": 0.75
            }

            self.result_ready.emit(result)

        except Exception as e:
            self.error_occurred.emit(str(e))


class OptimizationFeatures(QWidget):
    """优化功能类"""

    # 定义信号
    optimization_completed = pyqtSignal(dict)
    batch_analysis_completed = pyqtSignal(dict)
    ai_analysis_completed = pyqtSignal(dict)

    def __init__(self, parent=None, log_manager: Optional[LogManager] = None):
        super().__init__(parent)
        self.log_manager = log_manager or LogManager()
        self.parent_gui = parent

        # 优化相关
        self.optimization_thread = None
        self.current_optimization = None

        # 批量分析相关
        self.batch_results = []

    def show_optimization_dashboard(self):
        """显示优化仪表板"""
        try:
            dialog = QDialog(self.parent_gui)
            dialog.setWindowTitle("策略优化仪表板")
            dialog.setModal(True)
            dialog.resize(800, 600)

            layout = QVBoxLayout(dialog)

            # 创建标签页
            tab_widget = QTabWidget()

            # 参数优化标签页
            param_tab = self.create_parameter_optimization_tab()
            tab_widget.addTab(param_tab, "参数优化")

            # 批量测试标签页
            batch_tab = self.create_batch_test_tab()
            tab_widget.addTab(batch_tab, "批量测试")

            # 结果分析标签页
            result_tab = self.create_result_analysis_tab()
            tab_widget.addTab(result_tab, "结果分析")

            layout.addWidget(tab_widget)

            # 控制按钮
            button_layout = QHBoxLayout()

            start_button = QPushButton("开始优化")
            stop_button = QPushButton("停止优化")
            export_button = QPushButton("导出结果")
            close_button = QPushButton("关闭")

            start_button.clicked.connect(self.start_optimization)
            stop_button.clicked.connect(self.stop_optimization)
            export_button.clicked.connect(self.export_optimization_results)
            close_button.clicked.connect(dialog.close)

            button_layout.addWidget(start_button)
            button_layout.addWidget(stop_button)
            button_layout.addWidget(export_button)
            button_layout.addStretch()
            button_layout.addWidget(close_button)

            layout.addLayout(button_layout)

            dialog.exec_()

        except Exception as e:
            self.log_manager.error(f"显示优化仪表板失败: {str(e)}")

    def create_parameter_optimization_tab(self):
        """创建参数优化标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 策略选择
        strategy_group = QGroupBox("策略选择")
        strategy_layout = QFormLayout(strategy_group)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["MA策略", "MACD策略", "RSI策略", "KDJ策略"])
        strategy_layout.addRow("策略:", self.strategy_combo)

        layout.addWidget(strategy_group)

        # 参数范围设置
        param_group = QGroupBox("参数范围")
        param_layout = QFormLayout(param_group)

        # 参数1
        param1_layout = QHBoxLayout()
        self.param1_min = QSpinBox()
        self.param1_min.setRange(1, 100)
        self.param1_min.setValue(5)
        self.param1_max = QSpinBox()
        self.param1_max.setRange(1, 100)
        self.param1_max.setValue(30)
        self.param1_step = QSpinBox()
        self.param1_step.setRange(1, 10)
        self.param1_step.setValue(1)

        param1_layout.addWidget(QLabel("最小:"))
        param1_layout.addWidget(self.param1_min)
        param1_layout.addWidget(QLabel("最大:"))
        param1_layout.addWidget(self.param1_max)
        param1_layout.addWidget(QLabel("步长:"))
        param1_layout.addWidget(self.param1_step)

        param_layout.addRow("参数1:", param1_layout)

        # 参数2
        param2_layout = QHBoxLayout()
        self.param2_min = QSpinBox()
        self.param2_min.setRange(1, 100)
        self.param2_min.setValue(10)
        self.param2_max = QSpinBox()
        self.param2_max.setRange(1, 100)
        self.param2_max.setValue(50)
        self.param2_step = QSpinBox()
        self.param2_step.setRange(1, 10)
        self.param2_step.setValue(2)

        param2_layout.addWidget(QLabel("最小:"))
        param2_layout.addWidget(self.param2_min)
        param2_layout.addWidget(QLabel("最大:"))
        param2_layout.addWidget(self.param2_max)
        param2_layout.addWidget(QLabel("步长:"))
        param2_layout.addWidget(self.param2_step)

        param_layout.addRow("参数2:", param2_layout)

        layout.addWidget(param_group)

        # 优化设置
        opt_group = QGroupBox("优化设置")
        opt_layout = QFormLayout(opt_group)

        self.optimization_method = QComboBox()
        self.optimization_method.addItems(["网格搜索", "随机搜索", "遗传算法", "粒子群算法"])
        opt_layout.addRow("优化方法:", self.optimization_method)

        self.max_iterations = QSpinBox()
        self.max_iterations.setRange(10, 10000)
        self.max_iterations.setValue(1000)
        opt_layout.addRow("最大迭代:", self.max_iterations)

        self.target_metric = QComboBox()
        self.target_metric.addItems(["总收益率", "夏普比率", "最大回撤", "胜率"])
        opt_layout.addRow("目标指标:", self.target_metric)

        layout.addWidget(opt_group)

        # 进度显示
        self.optimization_progress = QProgressBar()
        layout.addWidget(self.optimization_progress)

        return widget

    def create_batch_test_tab(self):
        """创建批量测试标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 股票选择
        stock_group = QGroupBox("股票选择")
        stock_layout = QVBoxLayout(stock_group)

        stock_options_layout = QHBoxLayout()
        self.all_stocks_checkbox = QCheckBox("全部股票")
        self.selected_stocks_checkbox = QCheckBox("选中股票")
        self.custom_stocks_checkbox = QCheckBox("自定义列表")

        stock_options_layout.addWidget(self.all_stocks_checkbox)
        stock_options_layout.addWidget(self.selected_stocks_checkbox)
        stock_options_layout.addWidget(self.custom_stocks_checkbox)

        stock_layout.addLayout(stock_options_layout)

        # 股票列表
        self.stock_list_table = QTableWidget(0, 3)
        self.stock_list_table.setHorizontalHeaderLabels(["代码", "名称", "状态"])
        stock_layout.addWidget(self.stock_list_table)

        layout.addWidget(stock_group)

        # 测试设置
        test_group = QGroupBox("测试设置")
        test_layout = QFormLayout(test_group)

        self.test_period_combo = QComboBox()
        self.test_period_combo.addItems(["最近1年", "最近2年", "最近3年", "全部历史"])
        test_layout.addRow("测试周期:", self.test_period_combo)

        self.parallel_jobs = QSpinBox()
        self.parallel_jobs.setRange(1, 8)
        self.parallel_jobs.setValue(4)
        test_layout.addRow("并行任务:", self.parallel_jobs)

        layout.addWidget(test_group)

        # 批量进度
        self.batch_progress = QProgressBar()
        layout.addWidget(self.batch_progress)

        return widget

    def create_result_analysis_tab(self):
        """创建结果分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 结果表格
        self.result_table = QTableWidget(0, 6)
        self.result_table.setHorizontalHeaderLabels([
            "策略", "参数", "收益率", "夏普比率", "最大回撤", "胜率"
        ])
        layout.addWidget(self.result_table)

        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QFormLayout(stats_group)

        self.total_tests_label = QLabel("0")
        self.success_tests_label = QLabel("0")
        self.best_strategy_label = QLabel("无")
        self.avg_return_label = QLabel("0%")

        stats_layout.addRow("总测试数:", self.total_tests_label)
        stats_layout.addRow("成功测试:", self.success_tests_label)
        stats_layout.addRow("最佳策略:", self.best_strategy_label)
        stats_layout.addRow("平均收益:", self.avg_return_label)

        layout.addWidget(stats_group)

        return widget

    def start_optimization(self):
        """开始优化"""
        try:
            if self.optimization_thread and self.optimization_thread.isRunning():
                QMessageBox.warning(self.parent_gui, "警告", "优化正在进行中...")
                return

            # 获取优化参数
            strategy = self.strategy_combo.currentText()
            parameters = {
                "param1_range": (self.param1_min.value(), self.param1_max.value(), self.param1_step.value()),
                "param2_range": (self.param2_min.value(), self.param2_max.value(), self.param2_step.value()),
                "method": self.optimization_method.currentText(),
                "max_iterations": self.max_iterations.value(),
                "target_metric": self.target_metric.currentText()
            }

            # 创建优化线程
            self.optimization_thread = OptimizationThread(strategy, parameters, None)
            self.optimization_thread.progress_updated.connect(self.optimization_progress.setValue)
            self.optimization_thread.result_ready.connect(self.on_optimization_completed)
            self.optimization_thread.error_occurred.connect(self.on_optimization_error)

            # 开始优化
            self.optimization_thread.start()
            self.log_manager.info(f"开始优化策略: {strategy}")

        except Exception as e:
            self.log_manager.error(f"开始优化失败: {str(e)}")
            QMessageBox.critical(self.parent_gui, "错误", f"开始优化失败: {str(e)}")

    def stop_optimization(self):
        """停止优化"""
        try:
            if self.optimization_thread and self.optimization_thread.isRunning():
                self.optimization_thread.terminate()
                self.optimization_thread.wait()
                self.optimization_progress.setValue(0)
                self.log_manager.info("优化已停止")

        except Exception as e:
            self.log_manager.error(f"停止优化失败: {str(e)}")

    def on_optimization_completed(self, result: dict):
        """优化完成处理"""
        try:
            # 更新结果表格
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)

            self.result_table.setItem(row, 0, QTableWidgetItem(self.strategy_combo.currentText()))
            self.result_table.setItem(row, 1, QTableWidgetItem(str(result.get("best_params", {}))))
            self.result_table.setItem(row, 2, QTableWidgetItem(f"{result.get('best_score', 0):.2%}"))
            self.result_table.setItem(row, 3, QTableWidgetItem("1.25"))  # 示例数据
            self.result_table.setItem(row, 4, QTableWidgetItem("5.2%"))  # 示例数据
            self.result_table.setItem(row, 5, QTableWidgetItem("65%"))   # 示例数据

            # 更新统计信息
            self.update_statistics()

            # 发送完成信号
            self.optimization_completed.emit(result)

            self.log_manager.info("优化完成")
            QMessageBox.information(self.parent_gui, "完成", "策略优化已完成！")

        except Exception as e:
            self.log_manager.error(f"处理优化结果失败: {str(e)}")

    def on_optimization_error(self, error_msg: str):
        """优化错误处理"""
        self.log_manager.error(f"优化过程出错: {error_msg}")
        QMessageBox.critical(self.parent_gui, "优化错误", f"优化过程出错: {error_msg}")

    def update_statistics(self):
        """更新统计信息"""
        try:
            total_tests = self.result_table.rowCount()
            self.total_tests_label.setText(str(total_tests))

            if total_tests > 0:
                # 计算成功测试数（示例逻辑）
                success_tests = int(total_tests * 0.8)  # 假设80%成功
                self.success_tests_label.setText(str(success_tests))

                # 找到最佳策略（示例逻辑）
                self.best_strategy_label.setText("MA策略")

                # 计算平均收益（示例逻辑）
                self.avg_return_label.setText("12.5%")

        except Exception as e:
            self.log_manager.error(f"更新统计信息失败: {str(e)}")

    def export_optimization_results(self):
        """导出优化结果"""
        try:
            if self.result_table.rowCount() == 0:
                QMessageBox.warning(self.parent_gui, "警告", "没有结果可导出")
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self.parent_gui, "导出优化结果", "",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )

            if file_path:
                # 收集表格数据
                data = []
                headers = []
                for col in range(self.result_table.columnCount()):
                    headers.append(self.result_table.horizontalHeaderItem(col).text())

                for row in range(self.result_table.rowCount()):
                    row_data = []
                    for col in range(self.result_table.columnCount()):
                        item = self.result_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)

                # 创建DataFrame并导出
                df = pd.DataFrame(data, columns=headers)

                if file_path.endswith('.xlsx'):
                    df.to_excel(file_path, index=False)
                else:
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')

                QMessageBox.information(self.parent_gui, "成功", f"结果已导出到: {file_path}")
                self.log_manager.info(f"优化结果导出成功: {file_path}")

        except Exception as e:
            self.log_manager.error(f"导出优化结果失败: {str(e)}")
            QMessageBox.critical(self.parent_gui, "错误", f"导出失败: {str(e)}")

    def run_batch_analysis(self):
        """运行批量分析"""
        try:
            # 获取选中的股票
            selected_stocks = self.get_selected_stocks()

            if not selected_stocks:
                QMessageBox.warning(self.parent_gui, "警告", "请选择要分析的股票")
                return

            # 开始批量分析
            self.batch_progress.setValue(0)

            # 模拟批量分析过程
            total_stocks = len(selected_stocks)
            for i, stock in enumerate(selected_stocks):
                # 模拟分析单个股票
                progress = int((i + 1) / total_stocks * 100)
                self.batch_progress.setValue(progress)

                # 这里应该调用实际的分析函数
                # result = analyze_stock(stock)

            # 完成批量分析
            self.batch_progress.setValue(100)

            result = {
                "total_stocks": total_stocks,
                "success_count": int(total_stocks * 0.9),  # 假设90%成功
                "avg_score": 0.75
            }

            self.batch_analysis_completed.emit(result)
            self.log_manager.info(f"批量分析完成，共分析{total_stocks}只股票")

        except Exception as e:
            self.log_manager.error(f"批量分析失败: {str(e)}")

    def get_selected_stocks(self) -> List[str]:
        """获取选中的股票列表"""
        stocks = []

        if self.all_stocks_checkbox.isChecked():
            # 返回所有股票（示例）
            stocks = ["000001", "000002", "600000", "600036"]
        elif self.selected_stocks_checkbox.isChecked():
            # 返回当前选中的股票
            if hasattr(self.parent_gui, 'get_selected_stocks'):
                stocks = self.parent_gui.get_selected_stocks()
        elif self.custom_stocks_checkbox.isChecked():
            # 从表格中获取自定义股票列表
            for row in range(self.stock_list_table.rowCount()):
                code_item = self.stock_list_table.item(row, 0)
                if code_item:
                    stocks.append(code_item.text())

        return stocks

    def show_ai_diagnosis(self):
        """显示AI诊断功能"""
        try:
            dialog = QDialog(self.parent_gui)
            dialog.setWindowTitle("AI智能诊断")
            dialog.setModal(True)
            dialog.resize(600, 500)

            layout = QVBoxLayout(dialog)

            # 诊断选项
            options_group = QGroupBox("诊断选项")
            options_layout = QVBoxLayout(options_group)

            self.diagnose_strategy = QCheckBox("策略诊断")
            self.diagnose_portfolio = QCheckBox("组合诊断")
            self.diagnose_risk = QCheckBox("风险诊断")
            self.diagnose_performance = QCheckBox("性能诊断")

            options_layout.addWidget(self.diagnose_strategy)
            options_layout.addWidget(self.diagnose_portfolio)
            options_layout.addWidget(self.diagnose_risk)
            options_layout.addWidget(self.diagnose_performance)

            layout.addWidget(options_group)

            # 诊断结果
            result_group = QGroupBox("诊断结果")
            result_layout = QVBoxLayout(result_group)

            self.diagnosis_result = QTextEdit()
            self.diagnosis_result.setReadOnly(True)
            result_layout.addWidget(self.diagnosis_result)

            layout.addWidget(result_group)

            # 按钮
            button_layout = QHBoxLayout()

            diagnose_button = QPushButton("开始诊断")
            export_button = QPushButton("导出报告")
            close_button = QPushButton("关闭")

            diagnose_button.clicked.connect(self.run_ai_diagnosis)
            export_button.clicked.connect(self.export_diagnosis_report)
            close_button.clicked.connect(dialog.close)

            button_layout.addWidget(diagnose_button)
            button_layout.addWidget(export_button)
            button_layout.addStretch()
            button_layout.addWidget(close_button)

            layout.addLayout(button_layout)

            dialog.exec_()

        except Exception as e:
            self.log_manager.error(f"显示AI诊断失败: {str(e)}")

    def run_ai_diagnosis(self):
        """运行AI诊断"""
        try:
            # 收集诊断选项
            options = []
            if self.diagnose_strategy.isChecked():
                options.append("策略诊断")
            if self.diagnose_portfolio.isChecked():
                options.append("组合诊断")
            if self.diagnose_risk.isChecked():
                options.append("风险诊断")
            if self.diagnose_performance.isChecked():
                options.append("性能诊断")

            if not options:
                QMessageBox.warning(self.parent_gui, "警告", "请选择至少一个诊断选项")
                return

            # 模拟AI诊断过程
            diagnosis_text = "AI诊断报告\n" + "="*50 + "\n\n"

            for option in options:
                diagnosis_text += f"【{option}】\n"

                if option == "策略诊断":
                    diagnosis_text += "• 当前策略表现良好，建议继续使用\n"
                    diagnosis_text += "• 建议适当调整参数以提高收益率\n"
                    diagnosis_text += "• 风险控制措施有效\n\n"

                elif option == "组合诊断":
                    diagnosis_text += "• 投资组合分散度适中\n"
                    diagnosis_text += "• 建议增加防御性股票比例\n"
                    diagnosis_text += "• 行业配置相对均衡\n\n"

                elif option == "风险诊断":
                    diagnosis_text += "• 整体风险水平可控\n"
                    diagnosis_text += "• 最大回撤在合理范围内\n"
                    diagnosis_text += "• 建议设置止损点\n\n"

                elif option == "性能诊断":
                    diagnosis_text += "• 系统运行稳定\n"
                    diagnosis_text += "• 数据处理效率良好\n"
                    diagnosis_text += "• 建议定期清理缓存\n\n"

            diagnosis_text += "总体评分：85/100\n"
            diagnosis_text += "建议：继续当前策略，适当优化参数"

            self.diagnosis_result.setText(diagnosis_text)

            # 发送AI分析完成信号
            result = {
                "options": options,
                "score": 85,
                "recommendations": ["继续当前策略", "适当优化参数"]
            }

            self.ai_analysis_completed.emit(result)
            self.log_manager.info("AI诊断完成")

        except Exception as e:
            self.log_manager.error(f"AI诊断失败: {str(e)}")

    def export_diagnosis_report(self):
        """导出诊断报告"""
        try:
            if not self.diagnosis_result.toPlainText():
                QMessageBox.warning(self.parent_gui, "警告", "没有诊断结果可导出")
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self.parent_gui, "导出诊断报告", "",
                "Text Files (*.txt);;PDF Files (*.pdf)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.diagnosis_result.toPlainText())

                QMessageBox.information(self.parent_gui, "成功", f"报告已导出到: {file_path}")
                self.log_manager.info(f"诊断报告导出成功: {file_path}")

        except Exception as e:
            self.log_manager.error(f"导出诊断报告失败: {str(e)}")
            QMessageBox.critical(self.parent_gui, "错误", f"导出失败: {str(e)}")
