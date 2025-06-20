"""
多图表分屏控件 MultiChartPanel
支持3x3分屏，每个区块为ChartWidget，支持同步、mini map、主题自适应
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from gui.widgets.chart_widget import ChartWidget
from utils.theme import get_theme_manager
import pandas as pd


class DraggableWidget(QWidget):
    def dragEnterEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain") or event.mimeData().hasFormat("text/application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain") or event.mimeData().hasFormat("text/application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        # 直接调用父控件的dropEvent分发
        if self.parent() and hasattr(self.parent(), 'dropEvent'):
            self.parent().dropEvent(event)


class MultiChartPanel(QWidget):
    def __init__(self, parent=None, config_manager=None, theme_manager=None, log_manager=None, rows=3, cols=3, stock_list=None, data_manager=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.config_manager = config_manager
        self.theme_manager = theme_manager or get_theme_manager(config_manager)
        self.log_manager = log_manager
        self.data_manager = data_manager
        self.stock_list = stock_list or []
        self.sync_mode = True  # 是否同步分屏
        self.is_multi = False  # 默认单屏
        self._resize_timer = QTimer(self)  # 新增：防抖定时器
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._on_debounced_resize)
        self._init_ui()

    def _init_ui(self):
        # 先设置主布局，确保self.layout()不为None
        if self.layout() is None:
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(2)
            self.setLayout(self.main_layout)
        else:
            self.main_layout = self.layout()
        # 分屏切换按钮
        btn_layout = QHBoxLayout()
        self.switch_btn = QPushButton("切换九宫格")
        self.switch_btn.clicked.connect(self.toggle_mode)
        btn_layout.addWidget(self.switch_btn)
        self.main_layout.addLayout(btn_layout)
        # 单屏区
        self.single_chart = ChartWidget(
            self, self.config_manager, self.theme_manager, self.log_manager, data_manager=self.data_manager)
        self.main_layout.addWidget(self.single_chart)
        # 多屏区
        self.grid = QGridLayout()
        self.grid.setSpacing(2)
        self.chart_widgets = []
        for r in range(self.rows):
            row_widgets = []
            for c in range(self.cols):
                chart = ChartWidget(self, self.config_manager,
                                    self.theme_manager, self.log_manager, data_manager=self.data_manager)
                chart.setSizePolicy(QSizePolicy.Expanding,
                                    QSizePolicy.Expanding)
                chart.period_changed.connect(self._on_period_changed)
                chart.indicator_changed.connect(self._on_indicator_changed)
                chart.chart_updated.connect(self._on_chart_updated)
                chart.error_occurred.connect(self._on_error)
                self.grid.addWidget(chart, r, c)
                row_widgets.append(chart)
            self.chart_widgets.append(row_widgets)
        # 默认只显示单屏
        self.grid_widget = DraggableWidget(self)
        # 修复QLayout重复添加问题，先判断是否已有布局
        if self.grid_widget.layout() is None:
            self.grid_widget.setLayout(self.grid)
        self.grid_widget.setVisible(False)
        self.grid_widget.setAcceptDrops(True)
        self.main_layout.addWidget(self.grid_widget)
        self.setAcceptDrops(True)

    def set_stock_list(self, stock_list):
        """动态设置股票列表"""
        self.stock_list = stock_list or []

    def set_data_manager(self, data_manager):
        """动态设置数据管理器，并同步给所有子图"""
        self.data_manager = data_manager
        # 同步给所有ChartWidget
        if hasattr(self, 'single_chart') and self.single_chart:
            self.single_chart.data_manager = data_manager
        if hasattr(self, 'chart_widgets'):
            for row in self.chart_widgets:
                for chart in row:
                    chart.data_manager = data_manager

    def toggle_mode(self):
        """切换单屏/多屏模式"""
        try:
            self.is_multi = not self.is_multi
            if self.is_multi:
                self.switch_btn.setText("切换单屏")
                self.single_chart.setVisible(False)
                self.grid_widget.setVisible(True)
            else:
                self.switch_btn.setText("切换多屏")
                self.single_chart.setVisible(True)
                self.grid_widget.setVisible(False)
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"切换显示模式失败: {str(e)}")
            self.is_multi = False
            self.switch_btn.setText("切换多屏")
            self.single_chart.setVisible(True)
            self.grid_widget.setVisible(False)

    def auto_fill_multi_charts(self):
        """自动获取不同股票的初始数据并展示，遇到无效数据自动跳过"""
        if not self.stock_list or not self.data_manager:
            return
        idx = 0
        total = len(self.stock_list)
        for r in range(self.rows):
            for c in range(self.cols):
                chart = self.chart_widgets[r][c]
                # 跳过无效股票
                while idx < total:
                    code = self.stock_list[idx]['marketCode'] if isinstance(
                        self.stock_list[idx], dict) else self.stock_list[idx]
                    kdata = self.data_manager.get_k_data(code=code, freq='D')
                    if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                        kdata = kdata.copy()
                        kdata['code'] = code
                    idx += 1
                    if kdata is not None and not kdata.empty:
                        data = {
                            'stock_code': code,
                            'kdata': kdata,
                            'title': code,
                            'period': 'D',
                            'chart_type': 'candlestick'
                        }
                        chart.update_chart(data)
                        break
                else:
                    # 没有可用股票，显示无数据
                    if hasattr(chart, 'show_no_data'):
                        chart.show_no_data("无可用数据")

    def _on_period_changed(self, period):
        if self.sync_mode:
            for row in self.chart_widgets:
                for chart in row:
                    chart.current_period = period
                    chart.update_chart()

    def _on_indicator_changed(self, indicators):
        """多屏同步所有激活指标，仅同步选中项（不再直接赋值active_indicators，自动同步主窗口get_current_indicators）"""
        if self.sync_mode:
            for row in self.chart_widgets:
                for chart in row:
                    chart.update_chart()

    def _on_chart_updated(self, data):
        # 可扩展：同步缩放、mini map等
        pass

    def _on_error(self, msg):
        if self.log_manager:
            self.log_manager.error(msg)

    def update_all_charts(self, data_list):
        """批量更新所有分屏图表的数据"""
        try:
            idx = 0
            for r in range(self.rows):
                for c in range(self.cols):
                    if idx < len(data_list):
                        self.chart_widgets[r][c].update_chart(data_list[idx])
                    idx += 1
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"批量更新图表失败: {str(e)}")

    def update_chart(self, data):
        """统一更新图表，自动适配单屏/多屏。只分发到ChartWidget，仅用于K线/分屏业务。"""
        try:
            if self.is_multi:
                for row in self.chart_widgets:
                    for chart in row:
                        if chart:
                            chart.update_chart(data)
            else:
                if hasattr(self, 'single_chart') and self.single_chart:
                    self.single_chart.update_chart(data)
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新图表失败: {str(e)}")

    def apply_theme(self):
        """统一应用主题，自动适配单屏/多屏"""
        try:
            if self.is_multi:
                for row in self.chart_widgets:
                    for chart in row:
                        if chart:
                            chart.apply_theme()
            else:
                if hasattr(self, 'single_chart') and self.single_chart:
                    self.single_chart.apply_theme()
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"应用主题失败: {str(e)}")

    def reset_zoom(self):
        """统一重置缩放，自动适配单屏/多屏"""
        try:
            if self.is_multi:
                for row in self.chart_widgets:
                    for chart in row:
                        if hasattr(chart, 'reset_zoom'):
                            chart.reset_zoom()
            else:
                if hasattr(self, 'single_chart') and hasattr(self.single_chart, 'reset_zoom'):
                    self.single_chart.reset_zoom()
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"重置缩放失败: {str(e)}")

    def clear_chart(self):
        """统一清除图表，自动适配单屏/多屏"""
        try:
            if self.is_multi:
                for row in self.chart_widgets:
                    for chart in row:
                        if hasattr(chart, 'clear_chart'):
                            chart.clear_chart()
            else:
                if hasattr(self, 'single_chart') and hasattr(self.single_chart, 'clear_chart'):
                    self.single_chart.clear_chart()
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清除图表失败: {str(e)}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """多屏面板只做分发，根据鼠标位置分发event到对应ChartWidget，不做数据处理，异常日志健壮"""
        try:
            if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain"):
                pos = event.pos()
                target_chart = None
                for r, row in enumerate(self.chart_widgets):
                    for c, chart in enumerate(row):
                        chart_pos = chart.mapFromParent(pos)
                        if chart and chart.geometry().contains(chart_pos):
                            target_chart = chart
                            break
                    if target_chart:
                        break
                if not target_chart:
                    target_chart = self.chart_widgets[0][0]
                if target_chart:
                    # 构造新的QDropEvent，pos为ChartWidget本地坐标
                    new_event = QDropEvent(
                        chart.mapFromParent(pos),
                        event.dropAction(),
                        event.mimeData(),
                        event.mouseButtons(),
                        event.keyboardModifiers(),
                        event.type()
                    )
                    if hasattr(target_chart, 'handle_external_drop_event'):
                        target_chart.handle_external_drop_event(new_event)
                    else:
                        target_chart.dropEvent(new_event)
                event.acceptProposedAction()
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"多屏拖拽分发失败: {str(e)}")

    def resizeEvent(self, event):
        # 新增：防抖处理，避免频繁刷新
        if self._resize_timer.isActive():
            self._resize_timer.stop()
        self._resize_timer.start(150)  # 150ms后触发实际刷新
        super().resizeEvent(event)

    def _on_debounced_resize(self):
        # 新增：实际执行所有子图的布局和刷新
        try:
            if self.is_multi:
                for row in self.chart_widgets:
                    for chart in row:
                        if hasattr(chart, 'resizeEvent'):
                            chart.resizeEvent(QResizeEvent(
                                chart.size(), chart.size()))
            else:
                if hasattr(self, 'single_chart') and hasattr(self.single_chart, 'resizeEvent'):
                    self.single_chart.resizeEvent(QResizeEvent(
                        self.single_chart.size(), self.single_chart.size()))
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"多图表区防抖刷新失败: {str(e)}")

    def refresh_all_charts(self):
        """
        批量刷新所有子图，分批处理，避免UI卡顿。
        """
        if self.is_multi:
            charts = [chart for row in self.chart_widgets for chart in row]
        else:
            charts = [self.single_chart] if hasattr(
                self, 'single_chart') else []
        self._refresh_chart_batch(charts, 0)

    def _refresh_chart_batch(self, charts, idx, batch_size=2):
        if idx >= len(charts):
            return
        for i in range(idx, min(idx+batch_size, len(charts))):
            chart = charts[i]
            if hasattr(chart, 'resizeEvent'):
                chart.resizeEvent(QResizeEvent(chart.size(), chart.size()))
        QTimer.singleShot(30, lambda: self._refresh_chart_batch(
            charts, idx+batch_size, batch_size) if hasattr(self, '_refresh_chart_batch') else None)
