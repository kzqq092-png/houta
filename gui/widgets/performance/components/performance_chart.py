"""
现代化性能图表组件

参考专业交易软件设计的图表组件
"""

import logging
from collections import defaultdict
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)

# 可选导入matplotlib
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class ModernPerformanceChart(QWidget):
    """现代化性能图表组件 - 参考专业交易软件"""

    def __init__(self, title: str = "性能图表", chart_type: str = "line"):
        super().__init__()
        self.title = title
        self.chart_type = chart_type
        self.data_history = defaultdict(list)
        self.max_points = 100
        self._update_pending = False  # 防止频繁更新
        self._last_update_time = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标题栏
        header = QHBoxLayout()

        title_label = QLabel(self.title)
        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #11f0f1; font-weight: bold; margin-bottom: 8px;")

        header.addWidget(title_label)
        header.addStretch()

        layout.addLayout(header)

        if MATPLOTLIB_AVAILABLE:
            # 专业图表样式
            self.figure = Figure(figsize=(8, 4), facecolor='#1e1e1e')
            self.canvas = FigureCanvas(self.figure)
            self.ax = self.figure.add_subplot(111, facecolor='#1e1e1e')

            # 设置专业样式
            self.ax.spines['top'].set_visible(False)
            self.ax.spines['right'].set_visible(False)
            self.ax.spines['bottom'].set_color('#404040')
            self.ax.spines['left'].set_color('#404040')
            self.ax.grid(True, alpha=0.2, color='#404040', linewidth=0.5)

            layout.addWidget(self.canvas)
        else:
            placeholder = QLabel("图表需要matplotlib支持")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #7f8c8d; font-style: italic;")
            layout.addWidget(placeholder)

    def add_data_point(self, series_name: str, value: float):
        """添加数据点"""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.data_history[series_name].append(value)
        if len(self.data_history[series_name]) > self.max_points:
            self.data_history[series_name].pop(0)

    def update_chart(self):
        """更新图表 - 专业交易软件风格"""
        if not MATPLOTLIB_AVAILABLE or not self.data_history:
            return

        # 限制更新频率，避免频繁重绘
        import time
        current_time = time.time()
        if current_time - self._last_update_time < 1.0:  # 1秒内只更新一次
            if not self._update_pending:
                self._update_pending = True
                QTimer.singleShot(1000, self._delayed_update)
            return

        self._last_update_time = current_time
        self._update_pending = False

        self.ax.clear()

        # 专业色彩方案
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']

        for i, (series_name, data) in enumerate(self.data_history.items()):
            if not data:
                continue

            color = colors[i % len(colors)]

            if self.chart_type == "line":
                line = self.ax.plot(data, label=series_name, color=color, linewidth=1, alpha=0.8)[0]

                # 在最右边的点位显示当前数值
                if data:
                    latest_value = data[-1]
                    x_pos = len(data) - 1
                    y_pos = latest_value

                    # 确定数值单位
                    unit = self._get_value_unit(series_name, latest_value)
                    value_text = f"{latest_value:.1f}{unit}"

                    # 添加数值标注
                    self.ax.annotate(value_text,
                                     xy=(x_pos, y_pos),
                                     xytext=(8, 8), textcoords='offset points',
                                     bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7),
                                     color='white', fontsize=8, fontweight='bold',
                                     ha='left', va='bottom')

                    # 在最新点添加圆形标记
                    self.ax.scatter([x_pos], [y_pos], color=color, s=40, zorder=5, alpha=0.9)

            elif self.chart_type == "bar":
                x_pos = np.arange(len(data))
                self.ax.bar(x_pos, data, label=series_name, color=color, alpha=0.7)

                # 条形图的最新值显示
                if data:
                    latest_value = data[-1]
                    unit = self._get_value_unit(series_name, latest_value)
                    value_text = f"{latest_value:.1f}{unit}"

                    # 在最后一个条形图上方显示数值
                    last_x = len(data) - 1
                    self.ax.text(last_x, latest_value + max(data) * 0.02, value_text,
                                 ha='center', va='bottom', color=color,
                                 fontsize=8, fontweight='bold',
                                 bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

        # 专业样式设置
        self.ax.set_facecolor('#1e1e1e')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color('#404040')
        self.ax.spines['left'].set_color('#404040')
        self.ax.grid(True, alpha=0.2, color='#404040', linewidth=0.5)

        if len(self.data_history) > 1:
            # 🎨 修复：设置图例文本颜色与线条颜色一致
            legend = self.ax.legend(frameon=False, loc='upper left',
                                    fontsize=8, fancybox=False, shadow=False)

            # 为每个图例文本设置与对应线条相同的颜色
            for i, (series_name, _) in enumerate(self.data_history.items()):
                color = colors[i % len(colors)]
                legend.get_texts()[i].set_color(color)

        self.ax.tick_params(colors='#cccccc', labelsize=8)

        # 设置合适的边距，为数值标注留出空间
        self.ax.margins(x=0.02, y=0.1)

        self.figure.tight_layout()
        self.canvas.draw()

    def _get_value_unit(self, series_name: str, value: float) -> str:
        """根据序列名称和数值确定单位"""
        # 百分比指标
        if any(keyword in series_name for keyword in ['率', '收益', '回撤', '波动', '误差']):
            return '%'

        # 时间指标
        elif any(keyword in series_name for keyword in ['时间', '延迟']):
            if value < 1000:
                return 'ms'
            else:
                return 's'

        # 频率指标
        elif any(keyword in series_name for keyword in ['帧率', '频率']):
            return 'fps' if '帧率' in series_name else 'Hz'

        # 次数指标
        elif any(keyword in series_name for keyword in ['次数', '连续', '获利']):
            return '次'

        # 吞吐量指标
        elif '吞吐量' in series_name:
            return 'ops/s'

        # 默认无单位（比率类指标）
        else:
            return ''

    def _delayed_update(self):
        """延迟更新图表"""
        if self._update_pending:
            self._update_pending = False
            self.update_chart()

    def clear_data(self):
        """清空图表数据"""
        self.data_history.clear()
        if MATPLOTLIB_AVAILABLE:
            self.ax.clear()
            self.canvas.draw()
