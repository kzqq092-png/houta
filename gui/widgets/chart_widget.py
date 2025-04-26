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
import seaborn as sns

from core.logger import LogManager
from utils.theme import get_theme_manager
from utils.config_manager import ConfigManager
import traceback

class ChartWidget(QWidget):
    """图表控件类"""
    
    # 定义信号
    period_changed = pyqtSignal(str)  # 周期变更信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    chart_updated = pyqtSignal(dict)  # 图表更新信号
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, parent=None, config_manager: Optional[ConfigManager] = None):
        """初始化图表控件
        
        Args:
            parent: Parent widget
            config_manager: Optional ConfigManager instance to use
        """
        try:
            super().__init__(parent)
            
            # 初始化变量
            self.current_kdata = None
            self.current_signals = []
            self.current_period = 'D'
            self.current_indicator = None
            
            # 初始化管理器
            self.config_manager = config_manager or ConfigManager()
            self.theme_manager = get_theme_manager(self.config_manager)
            
            # 初始化日志管理器
            self.log_manager = LogManager()
            
            # 初始化UI
            self.init_ui()
            
            # 应用主题
            self.apply_theme()
            
            self.log_manager.info("图表控件初始化完成")
            
        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            toolbar_layout.addWidget(self.period_combo)
            
            # 添加指标选择
            toolbar_layout.addWidget(QLabel("指标:"))
            self.indicator_combo = QComboBox()
            self.indicator_combo.addItems([
                'MA', 'MACD', 'KDJ', 'RSI', 'BOLL', 'CCI', 'ATR', 'OBV',
                'WR', 'DMI', 'SAR', 'ROC', 'TRIX', 'MFI', 'ADX', 'BBW',
                'AD', 'CMO', 'DX', '综合指标'
            ])
            toolbar_layout.addWidget(self.indicator_combo)
            
            # 添加清除按钮
            self.clear_button = QPushButton("清除指标")
            toolbar_layout.addWidget(self.clear_button)
            
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
            
            self.log_manager.info("图表控件UI初始化完成")
            
        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def connect_signals(self):
        """连接信号"""
        try:
            # 连接周期选择信号
            self.period_combo.currentTextChanged.connect(self.on_period_changed)
            
            # 连接指标选择信号
            self.indicator_combo.currentTextChanged.connect(self.on_indicator_changed)
            
            # 连接清除按钮信号
            self.clear_button.clicked.connect(self.clear_indicators)
            
            self.log_manager.info("信号连接完成")
            
        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def update_chart(self, data: dict):
        """更新图表
        
        Args:
            data: Chart data dictionary
        """
        try:
            # TODO: 更新图表数据
            
            # 发送图表更新信号
            self.chart_updated.emit(data)
            
            self.log_manager.info("图表更新完成")
            
        except Exception as e:
            error_msg = f"更新图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            error_msg = f"绘制K线图失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            error_msg = f"绘制成交量图失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            error_msg = f"添加指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            error_msg = f"绘制MA指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            error_msg = f"绘制MACD指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            error_msg = f"绘制KDJ指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            error_msg = f"绘制交易信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            error_msg = f"清除指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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
            error_msg = f"处理周期变更失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def on_indicator_changed(self, indicator: str):
        """处理指标变更事件
        
        Args:
            indicator: 指标名称
        """
        try:
            self.indicator_changed.emit(indicator)
            self.add_indicator(indicator)
            
        except Exception as e:
            error_msg = f"处理指标变更失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def clear_chart(self):
        """Clear chart data"""
        try:
            # TODO: 清除图表数据
            
            self.log_manager.info("图表已清除")
            
        except Exception as e:
            error_msg = f"清除图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def apply_theme(self):
        """应用主题到图表"""
        try:
            # 获取当前主题
            theme = self.theme_manager.current_theme
            colors = self.theme_manager.get_theme_colors(theme)
            
            # 设置背景色
            self.setStyleSheet(f"background-color: {colors['background']};")
            
            # 设置图表样式
            if hasattr(self, 'figure'):
                self.figure.patch.set_facecolor(colors['chart_background'])
                for ax in self.figure.axes:
                    ax.set_facecolor(colors['chart_background'])
                    ax.tick_params(colors=colors['text'])
                    ax.spines['bottom'].set_color(colors['border'])
                    ax.spines['top'].set_color(colors['border'])
                    ax.spines['left'].set_color(colors['border'])
                    ax.spines['right'].set_color(colors['border'])
                    ax.title.set_color(colors['text'])
                    ax.xaxis.label.set_color(colors['text'])
                    ax.yaxis.label.set_color(colors['text'])
                
                # 更新画布
                self.canvas.draw()
                
        except Exception as e:
            error_msg = f"应用主题失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def update_performance_chart(self, metrics: dict):
        """更新性能图表
        
        Args:
            metrics: 性能指标字典
        """
        try:
            # 清除现有图表
            self.figure.clear()
            
            # 创建子图
            gs = self.figure.add_gridspec(2, 2)
            
            # 月度收益热力图
            ax1 = self.figure.add_subplot(gs[0, 0])
            if 'monthly_returns' in metrics:
                monthly_returns = metrics['monthly_returns']
                sns.heatmap(monthly_returns, ax=ax1, cmap='RdYlGn', 
                           center=0, annot=True, fmt='.1%')
                ax1.set_title('月度收益热力图')
            
            # 收益分布直方图
            ax2 = self.figure.add_subplot(gs[0, 1])
            if 'daily_returns' in metrics:
                sns.histplot(metrics['daily_returns'], ax=ax2, 
                            bins=50, kde=True)
                ax2.set_title('收益分布')
            
            # 滚动收益
            ax3 = self.figure.add_subplot(gs[1, 0])
            if 'rolling_returns' in metrics:
                ax3.plot(metrics['rolling_returns'])
                ax3.set_title('滚动收益')
            
            # 滚动波动率
            ax4 = self.figure.add_subplot(gs[1, 1])
            if 'rolling_volatility' in metrics:
                ax4.plot(metrics['rolling_volatility'])
                ax4.set_title('滚动波动率')
            
            # 调整布局
            self.figure.tight_layout()
            
            # 更新画布
            self.canvas.draw()
            
            self.log_manager.info("性能图表更新完成")
            
        except Exception as e:
            error_msg = f"更新性能图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg) 