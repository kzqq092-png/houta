#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多屏幕图表面板

支持单屏和多屏模式切换，提供多股票同时分析功能
"""

import sys
import os
import traceback
from typing import List, Dict, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QSplitter,
    QFrame, QScrollArea, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from gui.widgets.chart_widget import ChartWidget as ChartCanvas
from core.logger import get_logger


class MultiChartPanel(QWidget):
    """多屏幕图表面板"""

    # 信号定义
    chart_updated = pyqtSignal(str, dict)  # 股票代码, 图表数据
    mode_changed = pyqtSignal(bool)  # 是否为多屏模式
    stock_selected = pyqtSignal(str)  # 选中的股票代码

    def __init__(self, parent=None):
        """
        初始化多屏幕图表面板

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)

        # 状态变量
        self.is_multi = False  # 是否为多屏模式
        self.stock_list = []  # 股票列表
        self.data_manager = None  # 数据管理器
        self.current_indicators = []  # 当前指标

        # 图表组件
        self.single_chart = None  # 单屏图表
        self.chart_widgets = []  # 多屏图表网格 [[chart, chart], [chart, chart]]
        self.grid_size = (2, 2)  # 默认2x2网格

        # UI组件
        self.main_layout = None
        self.control_panel = None
        self.chart_container = None
        self.single_container = None
        self.multi_container = None

        self.init_ui()
        self.setup_single_mode()

        self.logger.info("多屏幕图表面板初始化完成")

    def init_ui(self):
        """初始化用户界面"""
        try:
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(5, 5, 5, 5)
            self.main_layout.setSpacing(5)

            # 创建控制面板
            self.create_control_panel()

            # 创建图表容器
            self.create_chart_containers()

        except Exception as e:
            self.logger.error(f"初始化UI失败: {e}")
            self.logger.error(traceback.format_exc())

    def create_control_panel(self):
        """创建控制面板"""
        try:
            self.control_panel = QFrame()
            self.control_panel.setFrameStyle(QFrame.StyledPanel)
            self.control_panel.setMaximumHeight(50)

            layout = QHBoxLayout(self.control_panel)
            layout.setContentsMargins(10, 5, 10, 5)

            # 模式切换按钮
            self.mode_btn = QPushButton("切换到多屏模式")
            self.mode_btn.clicked.connect(self.toggle_mode)
            layout.addWidget(self.mode_btn)

            # 网格大小选择
            layout.addWidget(QLabel("网格大小:"))
            self.grid_combo = QComboBox()
            self.grid_combo.addItems(
                ["2x2", "2x3", "3x2", "3x3", "4x2", "2x4"])
            self.grid_combo.currentTextChanged.connect(
                self.on_grid_size_changed)
            layout.addWidget(self.grid_combo)

            # 自动填充按钮
            self.auto_fill_btn = QPushButton("自动填充")
            self.auto_fill_btn.clicked.connect(self.auto_fill_multi_charts)
            self.auto_fill_btn.setEnabled(False)
            layout.addWidget(self.auto_fill_btn)

            # 清空按钮
            self.clear_btn = QPushButton("清空图表")
            self.clear_btn.clicked.connect(self.clear_all_charts)
            self.clear_btn.setEnabled(False)
            layout.addWidget(self.clear_btn)

            layout.addStretch()

            # 状态标签
            self.status_label = QLabel("单屏模式")
            self.status_label.setStyleSheet("color: blue; font-weight: bold;")
            layout.addWidget(self.status_label)

            self.main_layout.addWidget(self.control_panel)

        except Exception as e:
            self.logger.error(f"创建控制面板失败: {e}")

    def create_chart_containers(self):
        """创建图表容器"""
        try:
            # 创建主容器
            self.chart_container = QWidget()
            container_layout = QVBoxLayout(self.chart_container)
            container_layout.setContentsMargins(0, 0, 0, 0)

            # 单屏容器
            self.single_container = QWidget()
            single_layout = QVBoxLayout(self.single_container)
            single_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(self.single_container)

            # 多屏容器
            self.multi_container = QScrollArea()
            self.multi_container.setWidgetResizable(True)
            self.multi_container.setVisible(False)
            container_layout.addWidget(self.multi_container)

            self.main_layout.addWidget(self.chart_container)

        except Exception as e:
            self.logger.error(f"创建图表容器失败: {e}")

    def setup_single_mode(self):
        """设置单屏模式"""
        try:
            if self.single_chart is None:
                self.single_chart = ChartCanvas(self)
                self.single_chart.stock_selected.connect(
                    self.stock_selected.emit)

            # 清空单屏容器并添加图表
            layout = self.single_container.layout()
            self.clear_layout(layout)
            layout.addWidget(self.single_chart)

            self.logger.debug("单屏模式设置完成")

        except Exception as e:
            self.logger.error(f"设置单屏模式失败: {e}")

    def setup_multi_mode(self):
        """设置多屏模式"""
        try:
            # 解析网格大小
            rows, cols = self.parse_grid_size(self.grid_combo.currentText())
            self.grid_size = (rows, cols)

            # 创建多屏网格容器
            multi_widget = QWidget()
            grid_layout = QGridLayout(multi_widget)
            grid_layout.setSpacing(5)

            # 清空现有图表
            self.chart_widgets = []

            # 创建图表网格
            for row in range(rows):
                chart_row = []
                for col in range(cols):
                    chart = ChartCanvas(self)
                    chart.setMinimumSize(300, 200)
                    chart.stock_selected.connect(self.stock_selected.emit)

                    # 添加图表标题
                    chart_frame = QFrame()
                    chart_frame.setFrameStyle(QFrame.StyledPanel)
                    frame_layout = QVBoxLayout(chart_frame)
                    frame_layout.setContentsMargins(2, 2, 2, 2)

                    # 标题栏
                    title_bar = QWidget()
                    title_layout = QHBoxLayout(title_bar)
                    title_layout.setContentsMargins(5, 2, 5, 2)

                    title_label = QLabel(f"图表 {row+1}-{col+1}")
                    title_label.setStyleSheet(
                        "font-weight: bold; color: #333;")
                    title_layout.addWidget(title_label)

                    # 股票选择下拉框
                    stock_combo = QComboBox()
                    stock_combo.setMaximumWidth(120)
                    stock_combo.currentTextChanged.connect(
                        lambda code, r=row, c=col: self.on_chart_stock_changed(
                            r, c, code)
                    )
                    title_layout.addWidget(stock_combo)

                    title_layout.addStretch()

                    frame_layout.addWidget(title_bar)
                    frame_layout.addWidget(chart)

                    grid_layout.addWidget(chart_frame, row, col)

                    chart_row.append({
                        'chart': chart,
                        'frame': chart_frame,
                        'title': title_label,
                        'combo': stock_combo,
                        'stock_code': None
                    })

                self.chart_widgets.append(chart_row)

            # 设置到滚动区域
            self.multi_container.setWidget(multi_widget)

            # 更新股票下拉框
            self.update_stock_combos()

            self.logger.debug(f"多屏模式设置完成，网格大小: {rows}x{cols}")

        except Exception as e:
            self.logger.error(f"设置多屏模式失败: {e}")

    def toggle_mode(self):
        """切换显示模式"""
        try:
            self.is_multi = not self.is_multi

            if self.is_multi:
                # 切换到多屏模式
                self.setup_multi_mode()
                self.single_container.setVisible(False)
                self.multi_container.setVisible(True)
                self.mode_btn.setText("切换到单屏模式")
                self.status_label.setText("多屏模式")
                self.status_label.setStyleSheet(
                    "color: green; font-weight: bold;")
                self.auto_fill_btn.setEnabled(True)
                self.clear_btn.setEnabled(True)
            else:
                # 切换到单屏模式
                self.single_container.setVisible(True)
                self.multi_container.setVisible(False)
                self.mode_btn.setText("切换到多屏模式")
                self.status_label.setText("单屏模式")
                self.status_label.setStyleSheet(
                    "color: blue; font-weight: bold;")
                self.auto_fill_btn.setEnabled(False)
                self.clear_btn.setEnabled(False)

            self.mode_changed.emit(self.is_multi)
            self.logger.info(f"已切换到{'多屏' if self.is_multi else '单屏'}模式")

        except Exception as e:
            self.logger.error(f"切换模式失败: {e}")

    def on_grid_size_changed(self, grid_text: str):
        """网格大小改变事件"""
        try:
            if self.is_multi:
                # 重新设置多屏模式
                self.setup_multi_mode()
                self.logger.debug(f"网格大小已更改为: {grid_text}")
        except Exception as e:
            self.logger.error(f"更改网格大小失败: {e}")

    def on_chart_stock_changed(self, row: int, col: int, stock_code: str):
        """图表股票选择改变事件"""
        try:
            if not stock_code or stock_code == "请选择股票":
                return

            if row < len(self.chart_widgets) and col < len(self.chart_widgets[row]):
                chart_info = self.chart_widgets[row][col]
                chart_info['stock_code'] = stock_code
                chart_info['title'].setText(f"{stock_code}")

                # 更新图表数据
                self.update_chart_data(row, col, stock_code)

                self.logger.debug(f"图表 {row}-{col} 股票已更改为: {stock_code}")

        except Exception as e:
            self.logger.error(f"更改图表股票失败: {e}")

    def auto_fill_multi_charts(self):
        """自动填充多屏图表"""
        try:
            if not self.is_multi or not self.stock_list:
                return

            stock_index = 0
            for row in range(len(self.chart_widgets)):
                for col in range(len(self.chart_widgets[row])):
                    if stock_index < len(self.stock_list):
                        stock = self.stock_list[stock_index]
                        stock_code = stock.get('code', '')

                        if stock_code:
                            chart_info = self.chart_widgets[row][col]
                            chart_info['combo'].setCurrentText(stock_code)

                        stock_index += 1
                    else:
                        break

                if stock_index >= len(self.stock_list):
                    break

            self.logger.info("多屏图表自动填充完成")

        except Exception as e:
            self.logger.error(f"自动填充多屏图表失败: {e}")

    def clear_all_charts(self):
        """清空所有图表"""
        try:
            if self.is_multi:
                for row in range(len(self.chart_widgets)):
                    for col in range(len(self.chart_widgets[row])):
                        chart_info = self.chart_widgets[row][col]
                        chart_info['combo'].setCurrentIndex(0)
                        chart_info['chart'].clear()
                        chart_info['title'].setText(f"图表 {row+1}-{col+1}")
                        chart_info['stock_code'] = None
            else:
                if self.single_chart:
                    self.single_chart.clear()

            self.logger.info("所有图表已清空")

        except Exception as e:
            self.logger.error(f"清空图表失败: {e}")

    def update_chart_data(self, row: int, col: int, stock_code: str):
        """更新指定图表的数据"""
        try:
            if not self.data_manager:
                return

            chart_info = self.chart_widgets[row][col]
            chart = chart_info['chart']

            # 获取K线数据
            kdata = self.data_manager.get_kdata(stock_code)
            if kdata is not None and not kdata.empty:
                # 更新图表
                chart.update_chart(kdata, self.current_indicators)
                self.chart_updated.emit(stock_code, {'kdata': kdata})

        except Exception as e:
            self.logger.error(f"更新图表数据失败: {e}")

    def set_stock_list(self, stock_list: List[Dict[str, Any]]):
        """设置股票列表"""
        try:
            self.stock_list = stock_list or []
            self.update_stock_combos()
            self.logger.debug(f"股票列表已更新，共 {len(self.stock_list)} 只股票")
        except Exception as e:
            self.logger.error(f"设置股票列表失败: {e}")

    def set_data_manager(self, data_manager):
        """设置数据管理器"""
        try:
            self.data_manager = data_manager
            self.logger.debug("数据管理器已设置")
        except Exception as e:
            self.logger.error(f"设置数据管理器失败: {e}")

    def set_indicators(self, indicators: List[Dict[str, Any]]):
        """设置技术指标"""
        try:
            self.current_indicators = indicators or []

            # 更新所有图表的指标
            if self.is_multi:
                for row in range(len(self.chart_widgets)):
                    for col in range(len(self.chart_widgets[row])):
                        chart_info = self.chart_widgets[row][col]
                        if chart_info['stock_code']:
                            self.update_chart_data(
                                row, col, chart_info['stock_code'])
            else:
                if self.single_chart and hasattr(self.single_chart, 'update_indicators'):
                    self.single_chart.update_indicators(indicators)

            self.logger.debug(f"技术指标已更新，共 {len(indicators)} 个指标")

        except Exception as e:
            self.logger.error(f"设置技术指标失败: {e}")

    def update_stock_combos(self):
        """更新股票下拉框选项"""
        try:
            if not self.is_multi or not self.chart_widgets:
                return

            stock_items = ["请选择股票"]
            for stock in self.stock_list:
                code = stock.get('code', '')
                name = stock.get('name', '')
                if code:
                    display_text = f"{code} {name}" if name else code
                    stock_items.append(display_text.split()[0])  # 只保留代码部分

            for row in range(len(self.chart_widgets)):
                for col in range(len(self.chart_widgets[row])):
                    combo = self.chart_widgets[row][col]['combo']
                    current_text = combo.currentText()
                    combo.clear()
                    combo.addItems(stock_items)

                    # 恢复之前的选择
                    if current_text in stock_items:
                        combo.setCurrentText(current_text)

        except Exception as e:
            self.logger.error(f"更新股票下拉框失败: {e}")

    def parse_grid_size(self, grid_text: str) -> tuple:
        """解析网格大小文本"""
        try:
            parts = grid_text.split('x')
            if len(parts) == 2:
                rows = int(parts[0])
                cols = int(parts[1])
                return (rows, cols)
            else:
                return (2, 2)  # 默认值
        except:
            return (2, 2)

    def clear_layout(self, layout):
        """清空布局中的所有组件"""
        try:
            if layout is not None:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
        except Exception as e:
            self.logger.error(f"清空布局失败: {e}")

    def get_current_chart(self):
        """获取当前活动的图表"""
        if self.is_multi:
            # 多屏模式下返回第一个有数据的图表
            for row in range(len(self.chart_widgets)):
                for col in range(len(self.chart_widgets[row])):
                    chart_info = self.chart_widgets[row][col]
                    if chart_info['stock_code']:
                        return chart_info['chart']
            return None
        else:
            return self.single_chart

    def broadcast_data(self, data: Dict[str, Any]):
        """广播数据到所有图表"""
        try:
            if self.is_multi:
                for row in range(len(self.chart_widgets)):
                    for col in range(len(self.chart_widgets[row])):
                        chart = self.chart_widgets[row][col]['chart']
                        if hasattr(chart, 'update_data'):
                            chart.update_data(data)
            else:
                if self.single_chart and hasattr(self.single_chart, 'update_data'):
                    self.single_chart.update_data(data)

        except Exception as e:
            self.logger.error(f"广播数据失败: {e}")

    def load_stock_data(self, stock_code: str, stock_name: str = '', chart_data: Dict[str, Any] = None):
        """
        加载股票数据到图表

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            chart_data: 图表数据
        """
        try:
            if not chart_data:
                self.logger.warning(f"没有提供图表数据: {stock_code}")
                return

            # 如果是单屏模式，直接加载到单屏图表
            if not self.is_multi:
                if self.single_chart and hasattr(self.single_chart, 'update_chart'):
                    self.single_chart.update_chart(chart_data)
                elif self.single_chart and hasattr(self.single_chart, 'update_chart_data'):
                    self.single_chart.update_chart_data(chart_data)
                else:
                    self.logger.warning(
                        "单屏图表没有update_chart或update_chart_data方法")
            else:
                # 多屏模式，加载到第一个图表
                if self.chart_widgets and len(self.chart_widgets) > 0 and len(self.chart_widgets[0]) > 0:
                    chart = self.chart_widgets[0][0]['chart']
                    if chart and hasattr(chart, 'update_chart'):
                        chart.update_chart(chart_data)
                    elif chart and hasattr(chart, 'update_chart_data'):
                        chart.update_chart_data(chart_data)

            self.logger.info(f"成功加载股票数据: {stock_code} - {stock_name}")

        except Exception as e:
            self.logger.error(f"加载股票数据失败: {e}")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import sys

    app = QApplication(sys.argv)

    # 测试窗口
    window = QMainWindow()
    window.setWindowTitle("多屏幕图表面板测试")
    window.setGeometry(100, 100, 1200, 800)

    # 创建面板
    panel = MultiChartPanel()
    window.setCentralWidget(panel)

    # 设置测试数据
    test_stocks = [
        {"code": "000001", "name": "平安银行"},
        {"code": "000002", "name": "万科A"},
        {"code": "600000", "name": "浦发银行"},
        {"code": "600036", "name": "招商银行"},
    ]
    panel.set_stock_list(test_stocks)

    window.show()
    sys.exit(app.exec_())
