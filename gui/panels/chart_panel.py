"""
图表分析面板模块

负责图表显示、技术指标、图表控制等功能
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd
import numpy as np
import traceback
from typing import Dict, Any, List, Optional
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt


class ChartAnalysisPanel(QWidget):
    """图表分析面板"""

    # 信号定义
    chart_updated = pyqtSignal(dict)  # 图表更新信号
    indicator_changed = pyqtSignal(str, dict)  # 指标变化信号
    time_range_changed = pyqtSignal(str)  # 时间范围变化信号

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化属性
        self.current_stock = None
        self.current_period = 'D'  # 默认日线
        self.current_chart_type = 'candlestick'  # 默认K线图
        self.current_time_range = -365  # 默认显示一年
        self.selected_indicators = []  # 选中的指标

        # 获取父窗口的管理器
        if parent:
            self.log_manager = getattr(parent, 'log_manager', None)
            self.data_manager = getattr(parent, 'data_manager', None)
            self.sm = getattr(parent, 'sm', None)

        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 创建图表控制区域
        self.create_chart_controls(layout)

        # 创建图表显示区域
        self.create_chart_display(layout)

        # 创建指标控制区域
        self.create_indicator_controls(layout)

    def create_chart_controls(self, layout):
        """创建图表控制区域"""
        controls_group = QGroupBox("图表控制")
        controls_layout = QHBoxLayout(controls_group)

        # 周期选择
        controls_layout.addWidget(QLabel("周期:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["1分钟", "5分钟", "15分钟", "30分钟", "60分钟", "日线", "周线", "月线"])
        self.period_combo.setCurrentText("日线")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        controls_layout.addWidget(self.period_combo)

        # 图表类型选择
        controls_layout.addWidget(QLabel("类型:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["K线图", "线图", "柱状图", "面积图"])
        self.chart_type_combo.currentTextChanged.connect(self.on_chart_type_changed)
        controls_layout.addWidget(self.chart_type_combo)

        # 时间范围选择
        controls_layout.addWidget(QLabel("时间:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["1个月", "3个月", "6个月", "1年", "2年", "5年", "全部"])
        self.time_range_combo.setCurrentText("1年")
        self.time_range_combo.currentTextChanged.connect(self.on_time_range_changed)
        controls_layout.addWidget(self.time_range_combo)

        controls_layout.addStretch()

        # 图表操作按钮
        save_btn = QPushButton("保存图表")
        save_btn.clicked.connect(self.save_chart)
        controls_layout.addWidget(save_btn)

        reset_btn = QPushButton("重置视图")
        reset_btn.clicked.connect(self.reset_chart_view)
        controls_layout.addWidget(reset_btn)

        layout.addWidget(controls_group)

    def create_chart_display(self, layout):
        """创建图表显示区域"""
        chart_group = QGroupBox("图表显示")
        chart_layout = QVBoxLayout(chart_group)

        # 创建matplotlib图表
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(400)
        chart_layout.addWidget(self.canvas)

        # 图表工具栏
        toolbar_layout = QHBoxLayout()

        zoom_in_btn = QPushButton("放大")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar_layout.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("缩小")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(zoom_out_btn)

        pan_btn = QPushButton("平移")
        pan_btn.setCheckable(True)
        toolbar_layout.addWidget(pan_btn)

        toolbar_layout.addStretch()

        # 图表信息显示
        self.chart_info_label = QLabel("请选择股票查看图表")
        toolbar_layout.addWidget(self.chart_info_label)

        chart_layout.addLayout(toolbar_layout)
        layout.addWidget(chart_group)

    def create_indicator_controls(self, layout):
        """创建指标控制区域"""
        indicator_group = QGroupBox("技术指标")
        indicator_layout = QVBoxLayout(indicator_group)

        # 指标选择区域
        selection_layout = QHBoxLayout()

        # 可用指标列表
        available_layout = QVBoxLayout()
        available_layout.addWidget(QLabel("可用指标:"))

        self.available_indicators = QListWidget()
        self.available_indicators.setMaximumHeight(150)
        # 添加常用技术指标
        indicators = [
            "MA5", "MA10", "MA20", "MA60",
            "MACD", "RSI", "KDJ", "BOLL",
            "VOL", "OBV", "CCI", "WR",
            "DMI", "BIAS", "ROC", "PSY"
        ]
        self.available_indicators.addItems(indicators)
        self.available_indicators.itemDoubleClicked.connect(self.add_indicator)
        available_layout.addWidget(self.available_indicators)

        selection_layout.addLayout(available_layout)

        # 中间按钮
        button_layout = QVBoxLayout()
        button_layout.addStretch()

        add_btn = QPushButton("添加 >>")
        add_btn.clicked.connect(self.add_selected_indicator)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("<< 移除")
        remove_btn.clicked.connect(self.remove_selected_indicator)
        button_layout.addWidget(remove_btn)

        button_layout.addStretch()
        selection_layout.addLayout(button_layout)

        # 已选指标列表
        selected_layout = QVBoxLayout()
        selected_layout.addWidget(QLabel("已选指标:"))

        self.selected_indicators_list = QListWidget()
        self.selected_indicators_list.setMaximumHeight(150)
        self.selected_indicators_list.itemDoubleClicked.connect(self.remove_indicator)
        selected_layout.addWidget(self.selected_indicators_list)

        selection_layout.addLayout(selected_layout)
        indicator_layout.addLayout(selection_layout)

        # 指标参数设置
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("指标参数:"))

        self.indicator_params_btn = QPushButton("参数设置")
        self.indicator_params_btn.clicked.connect(self.show_indicator_params)
        params_layout.addWidget(self.indicator_params_btn)

        params_layout.addStretch()

        clear_all_btn = QPushButton("清空所有")
        clear_all_btn.clicked.connect(self.clear_all_indicators)
        params_layout.addWidget(clear_all_btn)

        indicator_layout.addLayout(params_layout)
        layout.addWidget(indicator_group)

    def on_period_changed(self, period: str):
        """周期改变事件"""
        try:
            period_map = {
                "1分钟": "1m",
                "5分钟": "5m",
                "15分钟": "15m",
                "30分钟": "30m",
                "60分钟": "60m",
                "日线": "D",
                "周线": "W",
                "月线": "M"
            }
            self.current_period = period_map.get(period, "D")
            self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"周期改变处理失败: {str(e)}")

    def on_chart_type_changed(self, chart_type: str):
        """图表类型改变事件"""
        try:
            type_map = {
                "K线图": "candlestick",
                "线图": "line",
                "柱状图": "bar",
                "面积图": "area"
            }
            self.current_chart_type = type_map.get(chart_type, "candlestick")
            self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"图表类型改变处理失败: {str(e)}")

    def on_time_range_changed(self, time_range: str):
        """时间范围改变事件"""
        try:
            range_map = {
                "1个月": -30,
                "3个月": -90,
                "6个月": -180,
                "1年": -365,
                "2年": -730,
                "5年": -1825,
                "全部": None
            }
            self.current_time_range = range_map.get(time_range, -365)
            self.time_range_changed.emit(time_range)
            self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"时间范围改变处理失败: {str(e)}")

    def add_indicator(self, item):
        """添加指标"""
        try:
            indicator_name = item.text()
            if indicator_name not in self.selected_indicators:
                self.selected_indicators.append(indicator_name)
                self.selected_indicators_list.addItem(indicator_name)
                self.indicator_changed.emit(indicator_name, {"action": "add"})
                self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"添加指标失败: {str(e)}")

    def add_selected_indicator(self):
        """添加选中的指标"""
        try:
            current_item = self.available_indicators.currentItem()
            if current_item:
                self.add_indicator(current_item)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"添加选中指标失败: {str(e)}")

    def remove_indicator(self, item):
        """移除指标"""
        try:
            indicator_name = item.text()
            if indicator_name in self.selected_indicators:
                self.selected_indicators.remove(indicator_name)
                row = self.selected_indicators_list.row(item)
                self.selected_indicators_list.takeItem(row)
                self.indicator_changed.emit(indicator_name, {"action": "remove"})
                self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"移除指标失败: {str(e)}")

    def remove_selected_indicator(self):
        """移除选中的指标"""
        try:
            current_item = self.selected_indicators_list.currentItem()
            if current_item:
                self.remove_indicator(current_item)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"移除选中指标失败: {str(e)}")

    def clear_all_indicators(self):
        """清空所有指标"""
        try:
            self.selected_indicators.clear()
            self.selected_indicators_list.clear()
            self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清空指标失败: {str(e)}")

    def show_indicator_params(self):
        """显示指标参数设置对话框"""
        try:
            current_item = self.selected_indicators_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "提示", "请先选择一个指标")
                return

            indicator_name = current_item.text()

            dialog = QDialog(self)
            dialog.setWindowTitle(f"{indicator_name} 参数设置")
            dialog.setMinimumSize(400, 300)

            layout = QVBoxLayout(dialog)

            # 参数设置区域
            params_group = QGroupBox("参数设置")
            params_layout = QFormLayout(params_group)

            # 根据指标类型添加不同参数
            if indicator_name.startswith("MA"):
                period_spin = QSpinBox()
                period_spin.setRange(1, 250)
                period_spin.setValue(int(indicator_name[2:]) if indicator_name[2:].isdigit() else 20)
                params_layout.addRow("周期:", period_spin)

            elif indicator_name == "MACD":
                fast_spin = QSpinBox()
                fast_spin.setRange(1, 50)
                fast_spin.setValue(12)
                params_layout.addRow("快线周期:", fast_spin)

                slow_spin = QSpinBox()
                slow_spin.setRange(1, 100)
                slow_spin.setValue(26)
                params_layout.addRow("慢线周期:", slow_spin)

                signal_spin = QSpinBox()
                signal_spin.setRange(1, 20)
                signal_spin.setValue(9)
                params_layout.addRow("信号线周期:", signal_spin)

            elif indicator_name == "RSI":
                period_spin = QSpinBox()
                period_spin.setRange(1, 100)
                period_spin.setValue(14)
                params_layout.addRow("周期:", period_spin)

            layout.addWidget(params_group)

            # 按钮
            button_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(dialog.reject)

            button_layout.addWidget(ok_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)

            if dialog.exec_() == QDialog.Accepted:
                # TODO: 应用参数设置
                self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"显示指标参数对话框失败: {str(e)}")

    def update_chart(self, stock_code: str = None, data: pd.DataFrame = None):
        """更新图表"""
        try:
            if stock_code:
                self.current_stock = stock_code

            if not self.current_stock:
                return

            # 清除之前的图表
            self.figure.clear()

            # 获取数据
            if data is None:
                data = self.get_stock_data(self.current_stock)

            if data is None or data.empty:
                self.chart_info_label.setText("无数据")
                self.canvas.draw()
                return

            # 创建子图
            if self.selected_indicators:
                # 主图 + 指标图
                ax1 = self.figure.add_subplot(2, 1, 1)
                ax2 = self.figure.add_subplot(2, 1, 2)
            else:
                # 只有主图
                ax1 = self.figure.add_subplot(1, 1, 1)
                ax2 = None

            # 绘制主图
            self.plot_main_chart(ax1, data)

            # 绘制指标
            if ax2 and self.selected_indicators:
                self.plot_indicators(ax2, data)

            # 设置图表信息
            self.chart_info_label.setText(f"{self.current_stock} - {self.current_period}")

            # 刷新画布
            self.figure.tight_layout()
            self.canvas.draw()

            # 发送更新信号
            self.chart_updated.emit({
                "stock_code": self.current_stock,
                "period": self.current_period,
                "chart_type": self.current_chart_type,
                "indicators": self.selected_indicators
            })

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新图表失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def plot_main_chart(self, ax, data):
        """绘制主图"""
        try:
            if self.current_chart_type == "candlestick":
                # K线图
                self.plot_candlestick(ax, data)
            elif self.current_chart_type == "line":
                # 线图
                ax.plot(data.index, data['close'], label='收盘价')
            elif self.current_chart_type == "bar":
                # 柱状图
                ax.bar(data.index, data['close'], label='收盘价')
            elif self.current_chart_type == "area":
                # 面积图
                ax.fill_between(data.index, data['close'], alpha=0.7, label='收盘价')

            ax.set_title(f"{self.current_stock} - {self.current_period}")
            # 检查是否有带标签的对象才创建图例
            handles, labels = ax.get_legend_handles_labels()
            if handles and labels:
                ax.legend()
            ax.grid(True, alpha=0.3)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"绘制主图失败: {str(e)}")

    def plot_candlestick(self, ax, data):
        """绘制K线图"""
        try:
            # 简化的K线图实现
            for i, (idx, row) in enumerate(data.iterrows()):
                color = 'red' if row['close'] >= row['open'] else 'green'

                # 绘制影线
                ax.plot([i, i], [row['low'], row['high']], color='black', linewidth=1)

                # 绘制实体
                height = abs(row['close'] - row['open'])
                bottom = min(row['close'], row['open'])
                ax.bar(i, height, bottom=bottom, color=color, alpha=0.8, width=0.8)

            ax.set_xlabel('时间')
            ax.set_ylabel('价格')

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"绘制K线图失败: {str(e)}")

    def plot_indicators(self, ax, data):
        """绘制技术指标"""
        try:
            for indicator in self.selected_indicators:
                if indicator.startswith("MA"):
                    # 移动平均线
                    period = int(indicator[2:]) if indicator[2:].isdigit() else 20
                    ma_data = data['close'].rolling(window=period).mean()
                    ax.plot(data.index, ma_data, label=indicator)

                elif indicator == "VOL":
                    # 成交量
                    ax.bar(data.index, data['volume'], alpha=0.7, label='成交量')

                # TODO: 添加更多指标的绘制逻辑

            # 检查是否有带标签的对象才创建图例
            handles, labels = ax.get_legend_handles_labels()
            if handles and labels:
                ax.legend()
            ax.grid(True, alpha=0.3)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"绘制指标失败: {str(e)}")

    def get_stock_data(self, stock_code: str) -> pd.DataFrame:
        """获取股票数据"""
        try:
            if not self.sm:
                return None

            stock = self.sm[stock_code]
            if not stock:
                return None

            # 构建查询
            from hikyuu import Query, KType

            # 周期映射
            ktype_map = {
                "1m": KType.MIN,
                "5m": KType.MIN5,
                "15m": KType.MIN15,
                "30m": KType.MIN30,
                "60m": KType.MIN60,
                "D": KType.DAY,
                "W": KType.WEEK,
                "M": KType.MONTH
            }

            ktype = ktype_map.get(self.current_period, KType.DAY)

            # 构建查询条件
            if self.current_time_range:
                query = Query(self.current_time_range)
            else:
                query = Query()

            # 获取K线数据
            kdata = stock.getKData(query, ktype)

            # 转换为DataFrame
            data = []
            for k in kdata:
                data.append({
                    'datetime': k.datetime,
                    'open': k.openPrice,
                    'high': k.highPrice,
                    'low': k.lowPrice,
                    'close': k.closePrice,
                    'volume': k.volume
                })

            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index('datetime', inplace=True)

            return df

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取股票数据失败: {str(e)}")
            return None

    def save_chart(self):
        """保存图表"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存图表",
                f"{self.current_stock}_chart.png",
                "PNG Files (*.png);;JPG Files (*.jpg);;PDF Files (*.pdf)"
            )

            if file_path:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "成功", f"图表已保存到: {file_path}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"保存图表失败: {str(e)}")

    def reset_chart_view(self):
        """重置图表视图"""
        try:
            self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"重置图表视图失败: {str(e)}")

    def zoom_in(self):
        """放大图表"""
        try:
            # TODO: 实现图表放大逻辑
            pass

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"放大图表失败: {str(e)}")

    def zoom_out(self):
        """缩小图表"""
        try:
            # TODO: 实现图表缩小逻辑
            pass

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"缩小图表失败: {str(e)}")

    def set_stock(self, stock_code: str):
        """设置当前股票"""
        try:
            self.current_stock = stock_code
            self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"设置股票失败: {str(e)}")

    def get_current_indicators(self) -> List[str]:
        """获取当前选中的指标"""
        return self.selected_indicators.copy()

    def set_indicators(self, indicators: List[str]):
        """设置指标列表"""
        try:
            self.selected_indicators = indicators.copy()
            self.selected_indicators_list.clear()
            self.selected_indicators_list.addItems(indicators)
            self.update_chart()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"设置指标失败: {str(e)}")
