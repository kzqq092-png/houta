#!/usr/bin/env python3
"""
K线情绪可视化组件
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
from datetime import datetime
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class EnhancedKLineChart(QWidget):
    """增强K线图表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 400)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        if MATPLOTLIB_AVAILABLE:
            # 创建matplotlib图表
            self.figure = Figure(figsize=(12, 8))
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
            
            # 创建子图
            self.ax_price = self.figure.add_subplot(3, 1, 1)
            self.ax_volume = self.figure.add_subplot(3, 1, 2)
            self.ax_sentiment = self.figure.add_subplot(3, 1, 3)
            
            self.figure.tight_layout()
        else:
            # 使用简单的文本显示
            self.text_display = QTextEdit()
            self.text_display.setReadOnly(True)
            layout.addWidget(self.text_display)
            
    def update_chart(self, data):
        """更新图表数据"""
        if not MATPLOTLIB_AVAILABLE:
            self.text_display.setText(f"K线数据更新时间: {datetime.now()}")
            return
            
        # 清除之前的图表
        self.ax_price.clear()
        self.ax_volume.clear()  
        self.ax_sentiment.clear()
        
        # 绘制价格K线
        if 'price_data' in data:
            price_data = data['price_data']
            self.ax_price.plot(price_data.get('close', []), label='收盘价', color='blue')
            self.ax_price.set_title('价格走势')
            self.ax_price.legend()
            
        # 绘制成交量
        if 'volume_data' in data:
            volume_data = data['volume_data']
            self.ax_volume.bar(range(len(volume_data)), volume_data, alpha=0.7, color='orange')
            self.ax_volume.set_title('成交量')
            
        # 绘制情绪指数
        if 'sentiment_data' in data:
            sentiment_data = data['sentiment_data']
            self.ax_sentiment.plot(sentiment_data, marker='o', color='red')
            self.ax_sentiment.set_title('情绪指数')
            self.ax_sentiment.set_ylim(0, 100)
            
        self.canvas.draw()

class SentimentHeatmap(QWidget):
    """情绪热力图组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.sentiment_data = {}
        
    def paintEvent(self, event):
        """绘制热力图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景
        painter.fillRect(self.rect(), QColor(248, 249, 250))
        
        # 绘制网格和情绪色块
        if self.sentiment_data:
            cell_width = self.width() // 10
            cell_height = self.height() // 6
            
            for i, (symbol, sentiment) in enumerate(self.sentiment_data.items()):
                if i >= 60:  # 最多显示60个
                    break
                    
                row = i // 10
                col = i % 10
                
                x = col * cell_width
                y = row * cell_height
                
                # 根据情绪值选择颜色
                if sentiment > 70:
                    color = QColor(76, 175, 80)  # 绿色-乐观
                elif sentiment > 30:
                    color = QColor(255, 193, 7)  # 黄色-中性
                else:
                    color = QColor(244, 67, 54)  # 红色-悲观
                    
                painter.fillRect(x + 2, y + 2, cell_width - 4, cell_height - 4, color)
                
                # 绘制文本
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(x + 5, y + 15, symbol[:4])
                painter.drawText(x + 5, y + 30, f"{sentiment:.0f}")
        
    def update_sentiment_data(self, data):
        """更新情绪数据"""
        self.sentiment_data = data
        self.update()
