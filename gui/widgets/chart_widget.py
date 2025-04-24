"""
图表控件模块
"""
from typing import Optional, List, Dict, Any
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                           QPushButton, QLabel)
from PyQt5.QtCore import pyqtSignal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from utils.logger import log_manager
from utils.theme import get_theme_manager
from utils.config_manager import ConfigManager

class ChartWidget(QWidget):
    """图表控件类"""
    
    # 定义信号
    period_changed = pyqtSignal(str)  # 周期变更信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    chart_updated = pyqtSignal()
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化图表控件
        
        Args:
            config_manager: Optional ConfigManager instance to use
        """
        super().__init__()
        
        try:
            # 初始化变量
            self.current_kdata = None
            self.current_signals = []
            self.current_period = 'D'
            self.current_indicator = None
            
            # 初始化管理器
            self.config_manager = config_manager or ConfigManager()
            self.theme_manager = get_theme_manager(self.config_manager)
            
            # 初始化UI
            self.init_ui()
            
            # 应用主题
            self.theme_manager.apply_theme(self)
            
        except Exception as e:
            log_manager.log(f"初始化图表控件失败: {str(e)}", "error")
            raise
            
    def init_ui(self):
        """初始化UI"""
        try:
            # 创建主布局
            layout = QVBoxLayout(self)
            
            # 创建工具栏
            toolbar_layout = QHBoxLayout()
            
            # 添加周期选择
            toolbar_layout.addWidget(QLabel("周期:"))
            self.period_combo = QComboBox()
            self.period_combo.addItems(['日线', '周线', '月线', '60分钟', '30分钟', '15分钟', '5分钟'])
            self.period_combo.currentTextChanged.connect(self.on_period_changed)
            toolbar_layout.addWidget(self.period_combo)
            
            # 添加指标选择
            toolbar_layout.addWidget(QLabel("指标:"))
            self.indicator_combo = QComboBox()
            self.indicator_combo.addItems([
                'MA', 'MACD', 'KDJ', 'RSI', 'BOLL', 'CCI', 'ATR', 'OBV',
                'WR', 'DMI', 'SAR', 'ROC', 'TRIX', 'MFI', 'ADX', 'BBW',
                'AD', 'CMO', 'DX', '综合指标'
            ])
            self.indicator_combo.currentTextChanged.connect(self.on_indicator_changed)
            toolbar_layout.addWidget(self.indicator_combo)
            
            # 添加清除按钮
            clear_button = QPushButton("清除指标")
            clear_button.clicked.connect(self.clear_indicators)
            toolbar_layout.addWidget(clear_button)
            
            # 添加工具栏到主布局
            layout.addLayout(toolbar_layout)
            
            # 创建图表
            self.figure = Figure(figsize=(8, 6))
            self.canvas = FigureCanvas(self.figure)
            
            # 创建工具栏
            self.toolbar = NavigationToolbar(self.canvas, self)
            
            # 添加到布局
            layout.addWidget(self.toolbar)
            layout.addWidget(self.canvas)
            
            # 创建子图
            self.price_ax = self.figure.add_subplot(211)  # K线图
            self.volume_ax = self.figure.add_subplot(212)  # 成交量图
            
            # 调整布局
            self.figure.tight_layout()
            
        except Exception as e:
            log_manager.log(f"初始化图表UI失败: {str(e)}", "error")
            raise
            
    def update_chart(self, kdata):
        """更新图表
        
        Args:
            kdata: K线数据
        """
        try:
            if kdata is None:
                return
                
            # 保存当前数据
            self.current_kdata = kdata
            
            # 清除现有图表
            self.price_ax.clear()
            self.volume_ax.clear()
            
            # 绘制K线图
            self.plot_kline(self.price_ax, kdata)
            
            # 绘制成交量图
            self.plot_volume(self.volume_ax, kdata)
            
            # 绘制指标
            if self.current_indicator:
                self.add_indicator(self.current_indicator)
                
            # 绘制信号
            if self.current_signals:
                self.plot_signals(self.current_signals)
                
            # 调整布局
            self.figure.tight_layout()
            
            # 更新画布
            self.canvas.draw()
            
            self.chart_updated.emit()
            
        except Exception as e:
            log_manager.log(f"更新图表失败: {str(e)}", "error")
            
    def plot_kline(self, ax, kdata):
        """绘制K线图
        
        Args:
            ax: 坐标轴对象
            kdata: K线数据
        """
        try:
            if kdata is None:
                return
                
            # 获取数据
            dates = range(len(kdata))
            opens = [float(k.open) for k in kdata]
            highs = [float(k.high) for k in kdata]
            lows = [float(k.low) for k in kdata]
            closes = [float(k.close) for k in kdata]
            
            # 计算颜色
            colors = ['red' if closes[i] >= opens[i] else 'green' 
                     for i in range(len(closes))]
            
            # 绘制K线
            for i in range(len(dates)):
                # 绘制实体
                if closes[i] >= opens[i]:
                    color = 'red'
                    bottom = opens[i]
                    height = closes[i] - opens[i]
                else:
                    color = 'green'
                    bottom = closes[i]
                    height = opens[i] - closes[i]
                    
                # 绘制K线实体
                ax.bar(dates[i], height, bottom=bottom, width=0.8,
                      color=color, alpha=0.6)
                
                # 绘制上下影线
                ax.plot([dates[i], dates[i]], [lows[i], highs[i]],
                       color=color, linewidth=1)
                
            # 设置标题
            if hasattr(self, 'current_stock'):
                title = f"{self.current_stock['name']} ({self.current_stock['code']})"
                ax.set_title(title)
                
            # 设置网格
            ax.grid(True, linestyle='--', alpha=0.3)
            
            # 设置刻度标签
            ax.set_xticks(range(0, len(dates), len(dates)//10))
            ax.set_xticklabels(
                [kdata[i].datetime.strftime('%Y-%m-%d') 
                 for i in range(0, len(dates), len(dates)//10)],
                rotation=45
            )
            
        except Exception as e:
            log_manager.log(f"绘制K线图失败: {str(e)}", "error")
            
    def plot_volume(self, ax, kdata):
        """绘制成交量图
        
        Args:
            ax: 坐标轴对象
            kdata: K线数据
        """
        try:
            if kdata is None:
                return
                
            # 获取数据
            dates = range(len(kdata))
            volumes = [float(k.volume) for k in kdata]
            opens = [float(k.open) for k in kdata]
            closes = [float(k.close) for k in kdata]
            
            # 计算颜色
            colors = ['red' if closes[i] >= opens[i] else 'green'
                     for i in range(len(closes))]
            
            # 绘制成交量柱状图
            ax.bar(dates, volumes, color=colors, alpha=0.6, width=0.8)
            
            # 设置网格
            ax.grid(True, linestyle='--', alpha=0.3)
            
            # 设置刻度标签
            ax.set_xticks(range(0, len(dates), len(dates)//10))
            ax.set_xticklabels(
                [kdata[i].datetime.strftime('%Y-%m-%d')
                 for i in range(0, len(dates), len(dates)//10)],
                rotation=45
            )
            
        except Exception as e:
            log_manager.log(f"绘制成交量图失败: {str(e)}", "error")
            
    def add_indicator(self, indicator: str):
        """添加技术指标
        
        Args:
            indicator: 指标名称
        """
        try:
            if self.current_kdata is None:
                return
                
            # 保存当前指标
            self.current_indicator = indicator
            
            # 创建指标子图
            if not hasattr(self, 'indicator_ax'):
                self.indicator_ax = self.figure.add_subplot(313)
                
            # 清除现有指标
            self.indicator_ax.clear()
            
            # 根据指标类型绘制
            if indicator == 'MA':
                self.plot_ma()
            elif indicator == 'MACD':
                self.plot_macd()
            elif indicator == 'KDJ':
                self.plot_kdj()
            elif indicator == 'RSI':
                self.plot_rsi()
            elif indicator == 'BOLL':
                self.plot_boll()
            # ... 其他指标
            
            # 调整布局
            self.figure.tight_layout()
            
            # 更新画布
            self.canvas.draw()
            
        except Exception as e:
            log_manager.log(f"添加指标失败: {str(e)}", "error")
            
    def plot_ma(self):
        """绘制MA指标"""
        try:
            from hikyuu.indicator import MA
            
            # 计算均线
            ma5 = MA(self.current_kdata.close, 5)
            ma10 = MA(self.current_kdata.close, 10)
            ma20 = MA(self.current_kdata.close, 20)
            ma60 = MA(self.current_kdata.close, 60)
            
            # 获取日期
            dates = range(len(self.current_kdata))
            
            # 绘制均线
            self.price_ax.plot(dates, ma5, label='MA5', linewidth=1)
            self.price_ax.plot(dates, ma10, label='MA10', linewidth=1)
            self.price_ax.plot(dates, ma20, label='MA20', linewidth=1)
            self.price_ax.plot(dates, ma60, label='MA60', linewidth=1)
            
            # 添加图例
            self.price_ax.legend()
            
        except Exception as e:
            log_manager.log(f"绘制MA指标失败: {str(e)}", "error")
            
    def plot_macd(self):
        """绘制MACD指标"""
        try:
            from hikyuu.indicator import MACD
            
            # 计算MACD
            macd = MACD(self.current_kdata.close)
            dates = range(len(self.current_kdata))
            
            # 绘制DIF和DEA线
            self.indicator_ax.plot(dates, macd.dif, label='DIF', color='blue')
            self.indicator_ax.plot(dates, macd.dea, label='DEA', color='orange')
            
            # 绘制MACD柱状图
            colors = ['red' if m >= 0 else 'green' for m in macd.macd]
            self.indicator_ax.bar(dates, macd.macd, color=colors, alpha=0.6)
            
            # 添加图例
            self.indicator_ax.legend()
            
            # 设置标题
            self.indicator_ax.set_title('MACD')
            
        except Exception as e:
            log_manager.log(f"绘制MACD指标失败: {str(e)}", "error")
            
    def plot_kdj(self):
        """绘制KDJ指标"""
        try:
            from hikyuu.indicator import KDJ
            
            # 计算KDJ
            kdj = KDJ(self.current_kdata)
            dates = range(len(self.current_kdata))
            
            # 绘制KDJ线
            self.indicator_ax.plot(dates, kdj.k, label='K', color='blue')
            self.indicator_ax.plot(dates, kdj.d, label='D', color='orange')
            self.indicator_ax.plot(dates, kdj.j, label='J', color='purple')
            
            # 添加超买超卖线
            self.indicator_ax.axhline(y=80, color='red', linestyle='--', alpha=0.5)
            self.indicator_ax.axhline(y=20, color='green', linestyle='--', alpha=0.5)
            
            # 添加图例
            self.indicator_ax.legend()
            
            # 设置标题
            self.indicator_ax.set_title('KDJ')
            
        except Exception as e:
            log_manager.log(f"绘制KDJ指标失败: {str(e)}", "error")
            
    def plot_signals(self, signals: List[Dict[str, Any]]):
        """绘制交易信号
        
        Args:
            signals: 信号列表
        """
        try:
            if not signals:
                return
                
            # 保存当前信号
            self.current_signals = signals
            
            # 绘制信号
            for signal in signals:
                if signal['signal'] == 'BUY':
                    color = 'red'
                    marker = '^'
                else:
                    color = 'green'
                    marker = 'v'
                    
                # 获取信号位置
                for i, k in enumerate(self.current_kdata):
                    if k.datetime == signal['time']:
                        self.price_ax.scatter(
                            i, signal['price'],
                            c=color, marker=marker, s=100,
                            label=f"{signal['type']}{signal['signal']}"
                        )
                        break
                        
            # 添加图例
            self.price_ax.legend()
            
            # 更新画布
            self.canvas.draw()
            
        except Exception as e:
            log_manager.log(f"绘制交易信号失败: {str(e)}", "error")
            
    def clear_indicators(self):
        """清除技术指标"""
        try:
            # 清除指标
            self.current_indicator = None
            
            if hasattr(self, 'indicator_ax'):
                self.indicator_ax.clear()
                delattr(self, 'indicator_ax')
                
            # 更新图表
            self.update_chart(self.current_kdata)
            
        except Exception as e:
            log_manager.log(f"清除指标失败: {str(e)}", "error")
            
    def on_period_changed(self, period: str):
        """处理周期变更事件
        
        Args:
            period: 周期名称
        """
        try:
            # 转换周期
            period_map = {
                '日线': 'D',
                '周线': 'W',
                '月线': 'M',
                '60分钟': '60',
                '30分钟': '30',
                '15分钟': '15',
                '5分钟': '5'
            }
            
            if period in period_map:
                self.current_period = period_map[period]
                self.period_changed.emit(self.current_period)
                
        except Exception as e:
            log_manager.log(f"处理周期变更失败: {str(e)}", "error")
            
    def on_indicator_changed(self, indicator: str):
        """处理指标变更事件
        
        Args:
            indicator: 指标名称
        """
        try:
            self.indicator_changed.emit(indicator)
            self.add_indicator(indicator)
            
        except Exception as e:
            log_manager.log(f"处理指标变更失败: {str(e)}", "error") 