"""
现代化指标卡片组件

参考TradingView设计的指标显示卡片
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor


class ModernMetricCard(QFrame):
    """现代化指标卡片 - 参考TradingView设计"""

    def __init__(self, title: str, value: str = "0", unit: str = "", color: str = "#3498db", trend: str = "neutral"):
        super().__init__()
        self.title = title
        self.value = value
        self.unit = unit
        self.color = color
        self.trend = trend
        self.init_ui()

    def init_ui(self):
        # 设置现代化样式
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2c3e50, stop: 1 #34495e);
                border: 1px solid #404040;
                border-radius: 8px;
                margin: 3px;
                padding: 0px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: #ecf0f1;
            }}
        """)

        # 设置固定大小和阴影效果 - 更紧凑的卡片
        self.setFixedSize(130, 52)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(4)

        # 标题区域
        title_layout = QHBoxLayout()

        title_label = QLabel(self.title)
        title_font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: #bdc3c7; font-weight: 500;")

        # 趋势指示器
        trend_label = QLabel()
        if self.trend == "up":
            trend_label.setText("▲")
            trend_label.setStyleSheet("color: #e74c3c; font-size: 10px;")
        elif self.trend == "down":
            trend_label.setText("▼")
            trend_label.setStyleSheet("color: #27ae60; font-size: 10px;")
        else:
            trend_label.setText("●")
            trend_label.setStyleSheet("color: #95a5a6; font-size: 8px;")

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(trend_label)

        # 数值显示
        value_layout = QHBoxLayout()

        self.value_label = QLabel(self.value)
        value_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet(f"color: {self.color}; font-weight: bold;")

        unit_label = QLabel(self.unit)
        unit_font = QFont("Segoe UI", 8, QFont.Weight.Normal)
        unit_label.setFont(unit_font)
        unit_label.setStyleSheet("color: #7f8c8d; margin-left: 4px;")

        value_layout.addWidget(self.value_label)
        value_layout.addWidget(unit_label)
        value_layout.addStretch()

        layout.addLayout(title_layout)
        layout.addLayout(value_layout)
        layout.addStretch()

    def update_value(self, value: str, trend: str = "neutral"):
        """更新数值和趋势"""
        self.value_label.setText(value)
        self.trend = trend

        # 更新趋势指示器
        trend_label = self.findChild(QLabel)
        for child in self.findChildren(QLabel):
            if child.text() in ["▲", "▼", "●"]:
                if trend == "up":
                    child.setText("▲")
                    child.setStyleSheet("color: #27ae60; font-size: 10px;")
                elif trend == "down":
                    child.setText("▼")
                    child.setStyleSheet("color: #e74c3c; font-size: 10px;")
                else:
                    child.setText("●")
                    child.setStyleSheet("color: #95a5a6; font-size: 8px;")
                break
