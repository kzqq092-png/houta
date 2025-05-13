"""
多图表分屏控件 MultiChartPanel
支持3x3分屏，每个区块为ChartWidget，支持同步、mini map、主题自适应
"""
from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PyQt5.QtCore import Qt
from gui.widgets.chart_widget import ChartWidget
from utils.theme import get_theme_manager


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
        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        # 分屏切换按钮
        btn_layout = QHBoxLayout()
        self.switch_btn = QPushButton("切换多屏")
        self.switch_btn.clicked.connect(self.toggle_mode)
        btn_layout.addWidget(self.switch_btn)
        self.layout.addLayout(btn_layout)
        # 单屏区
        self.single_chart = ChartWidget(
            self, self.config_manager, self.theme_manager, self.log_manager, data_manager=self.data_manager)
        self.layout.addWidget(self.single_chart)
        # 多屏区
        self.grid = QGridLayout()
        self.grid.setSpacing(4)
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
        self.grid_widget = QWidget()
        self.grid_widget.setLayout(self.grid)
        self.grid_widget.setVisible(False)
        self.grid_widget.setAcceptDrops(True)
        self.grid_widget.dragMoveEvent = self._grid_drag_move_event
        self.layout.addWidget(self.grid_widget)
        self.setLayout(self.layout)
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

    def _on_indicator_changed(self, indicator):
        if self.sync_mode:
            for row in self.chart_widgets:
                for chart in row:
                    chart.current_indicator = indicator
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
            self.theme_manager.apply_theme(self)
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
        """支持拖拽股票代码到多屏任意子图表，只做分发，异常日志健壮"""
        try:
            if event.mimeData().hasFormat("text/plain") or event.mimeData().hasText():
                event.acceptProposedAction()
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"多屏拖入事件失败: {str(e)}")

    def dropEvent(self, event):
        """多屏面板只做分发，根据鼠标位置分发event到对应ChartWidget，不做数据处理，异常日志健壮"""
        try:
            if event.mimeData().hasFormat("text/plain") or event.mimeData().hasText():
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
                    target_chart.dropEvent(event)
                event.acceptProposedAction()
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"多屏拖拽分发失败: {str(e)}")

    def dragMoveEvent(self, event):
        """多屏面板拖拽移动事件，确保鼠标样式为可放开"""
        if event.mimeData().hasFormat("text/plain") or event.mimeData().hasText():
            event.acceptProposedAction()

    def _grid_drag_move_event(self, event):
        """多屏grid_widget拖拽移动事件，确保鼠标样式为可放开"""
        if event.mimeData().hasFormat("text/plain") or event.mimeData().hasText():
            event.acceptProposedAction()
