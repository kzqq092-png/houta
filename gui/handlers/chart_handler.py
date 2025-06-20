"""
图表处理器模块

专门处理图表渲染、优化和交互功能
"""

from typing import Optional, Dict, Any, List, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt5.QtWidgets import QWidget, QMessageBox
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io
import base64
from core.logger import LogManager


class ChartRenderThread(QThread):
    """图表渲染线程"""

    render_completed = pyqtSignal(object)  # 渲染完成信号
    render_error = pyqtSignal(str)  # 渲染错误信号
    progress_updated = pyqtSignal(int)  # 进度更新信号

    def __init__(self, chart_data, chart_config):
        super().__init__()
        self.chart_data = chart_data
        self.chart_config = chart_config

    def run(self):
        """执行图表渲染"""
        try:
            self.progress_updated.emit(10)

            # 根据配置选择渲染方式
            chart_type = self.chart_config.get('type', 'candlestick')

            if chart_type == 'candlestick':
                result = self.render_candlestick()
            elif chart_type == 'line':
                result = self.render_line_chart()
            elif chart_type == 'volume':
                result = self.render_volume_chart()
            elif chart_type == 'indicator':
                result = self.render_indicator_chart()
            else:
                raise ValueError(f"不支持的图表类型: {chart_type}")

            self.progress_updated.emit(100)
            self.render_completed.emit(result)

        except Exception as e:
            self.render_error.emit(str(e))

    def render_candlestick(self):
        """渲染K线图"""
        try:
            data = self.chart_data
            config = self.chart_config

            # 创建子图
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=('K线图', '成交量'),
                row_width=[0.2, 0.7]
            )

            # 添加K线图
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='K线'
                ),
                row=1, col=1
            )

            # 添加成交量
            colors = ['red' if close >= open else 'green'
                      for close, open in zip(data['close'], data['open'])]

            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['volume'],
                    name='成交量',
                    marker_color=colors
                ),
                row=2, col=1
            )

            # 添加技术指标
            indicators = config.get('indicators', {})
            for indicator_name, indicator_data in indicators.items():
                if indicator_name in ['MA5', 'MA10', 'MA20']:
                    fig.add_trace(
                        go.Scatter(
                            x=data.index,
                            y=indicator_data,
                            mode='lines',
                            name=indicator_name
                        ),
                        row=1, col=1
                    )

            # 设置布局
            fig.update_layout(
                title=config.get('title', 'K线图'),
                xaxis_rangeslider_visible=False,
                height=600,
                showlegend=True
            )

            return fig

        except Exception as e:
            raise Exception(f"渲染K线图失败: {str(e)}")

    def render_line_chart(self):
        """渲染线图"""
        try:
            data = self.chart_data
            config = self.chart_config

            fig = go.Figure()

            # 添加收盘价线
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['close'],
                    mode='lines',
                    name='收盘价',
                    line=dict(color='blue', width=2)
                )
            )

            # 添加其他指标线
            indicators = config.get('indicators', {})
            for indicator_name, indicator_data in indicators.items():
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=indicator_data,
                        mode='lines',
                        name=indicator_name
                    )
                )

            # 设置布局
            fig.update_layout(
                title=config.get('title', '线图'),
                xaxis_title='时间',
                yaxis_title='价格',
                height=400,
                showlegend=True
            )

            return fig

        except Exception as e:
            raise Exception(f"渲染线图失败: {str(e)}")

    def render_volume_chart(self):
        """渲染成交量图"""
        try:
            data = self.chart_data
            config = self.chart_config

            fig = go.Figure()

            # 根据涨跌设置颜色
            colors = ['red' if close >= open else 'green'
                      for close, open in zip(data['close'], data['open'])]

            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['volume'],
                    name='成交量',
                    marker_color=colors
                )
            )

            # 设置布局
            fig.update_layout(
                title=config.get('title', '成交量图'),
                xaxis_title='时间',
                yaxis_title='成交量',
                height=300,
                showlegend=True
            )

            return fig

        except Exception as e:
            raise Exception(f"渲染成交量图失败: {str(e)}")

    def render_indicator_chart(self):
        """渲染指标图"""
        try:
            data = self.chart_data
            config = self.chart_config
            indicators = config.get('indicators', {})

            fig = go.Figure()

            for indicator_name, indicator_data in indicators.items():
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=indicator_data,
                        mode='lines',
                        name=indicator_name
                    )
                )

            # 设置布局
            fig.update_layout(
                title=config.get('title', '技术指标'),
                xaxis_title='时间',
                yaxis_title='指标值',
                height=300,
                showlegend=True
            )

            return fig

        except Exception as e:
            raise Exception(f"渲染指标图失败: {str(e)}")


class ChartHandler(QObject):
    """图表处理器"""

    # 定义信号
    chart_rendered = pyqtSignal(object)  # 图表渲染完成信号
    chart_updated = pyqtSignal(dict)  # 图表更新信号
    chart_error = pyqtSignal(str)  # 图表错误信号
    render_progress = pyqtSignal(int)  # 渲染进度信号

    def __init__(self, parent=None, log_manager: Optional[LogManager] = None):
        super().__init__(parent)
        self.log_manager = log_manager or LogManager()

        # 图表缓存
        self.chart_cache: Dict[str, Any] = {}
        self.max_cache_size = 50

        # 渲染配置
        self.render_config = {
            'theme': 'light',
            'dpi': 100,
            'figure_size': (12, 8),
            'font_size': 10,
            'line_width': 1.5,
            'colors': {
                'up': '#FF4444',
                'down': '#00AA00',
                'volume': '#4444FF',
                'ma5': '#FF8800',
                'ma10': '#8800FF',
                'ma20': '#00FF88'
            }
        }

        # 性能监控
        self.render_times = []
        self.max_render_time_records = 100

        # 初始化matplotlib设置
        self.init_matplotlib_settings()

    def init_matplotlib_settings(self):
        """初始化matplotlib设置"""
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['figure.dpi'] = self.render_config['dpi']
            plt.rcParams['font.size'] = self.render_config['font_size']

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化matplotlib设置失败: {str(e)}")

    def render_chart_async(self, chart_data: pd.DataFrame, chart_config: Dict[str, Any]) -> str:
        """异步渲染图表"""
        try:
            # 生成缓存键
            cache_key = self.generate_cache_key(chart_data, chart_config)

            # 检查缓存
            if cache_key in self.chart_cache:
                cached_chart = self.chart_cache[cache_key]
                self.chart_rendered.emit(cached_chart)
                return cache_key

            # 创建渲染线程
            self.render_thread = ChartRenderThread(chart_data, chart_config)
            self.render_thread.render_completed.connect(
                lambda result: self.on_render_completed(cache_key, result)
            )
            self.render_thread.render_error.connect(self.on_render_error)
            self.render_thread.progress_updated.connect(self.render_progress.emit)

            # 开始渲染
            start_time = datetime.now()
            self.render_thread.start()

            # 记录渲染开始时间
            self.current_render_start = start_time

            return cache_key

        except Exception as e:
            error_msg = f"异步渲染图表失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            self.chart_error.emit(error_msg)
            return ""

    def render_chart_sync(self, chart_data: pd.DataFrame, chart_config: Dict[str, Any]) -> Any:
        """同步渲染图表"""
        try:
            start_time = datetime.now()

            # 生成缓存键
            cache_key = self.generate_cache_key(chart_data, chart_config)

            # 检查缓存
            if cache_key in self.chart_cache:
                return self.chart_cache[cache_key]

            # 直接渲染
            chart_type = chart_config.get('type', 'candlestick')

            if chart_type == 'candlestick':
                result = self.render_candlestick_sync(chart_data, chart_config)
            elif chart_type == 'line':
                result = self.render_line_chart_sync(chart_data, chart_config)
            elif chart_type == 'volume':
                result = self.render_volume_chart_sync(chart_data, chart_config)
            elif chart_type == 'indicator':
                result = self.render_indicator_chart_sync(chart_data, chart_config)
            else:
                raise ValueError(f"不支持的图表类型: {chart_type}")

            # 缓存结果
            self.cache_chart(cache_key, result)

            # 记录渲染时间
            render_time = (datetime.now() - start_time).total_seconds()
            self.record_render_time(render_time)

            return result

        except Exception as e:
            error_msg = f"同步渲染图表失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            raise Exception(error_msg)

    def render_candlestick_sync(self, data: pd.DataFrame, config: Dict[str, Any]) -> Figure:
        """同步渲染K线图"""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.render_config['figure_size'],
                                           gridspec_kw={'height_ratios': [3, 1]})

            # 绘制K线图
            self.plot_candlestick(ax1, data, config)

            # 绘制成交量
            self.plot_volume(ax2, data, config)

            # 设置标题和标签
            ax1.set_title(config.get('title', 'K线图'))
            ax1.set_ylabel('价格')
            ax2.set_ylabel('成交量')
            ax2.set_xlabel('时间')

            # 格式化x轴
            self.format_xaxis(ax1, data.index)
            self.format_xaxis(ax2, data.index)

            plt.tight_layout()
            return fig

        except Exception as e:
            raise Exception(f"同步渲染K线图失败: {str(e)}")

    def plot_candlestick(self, ax, data: pd.DataFrame, config: Dict[str, Any]):
        """绘制K线"""
        try:
            colors = self.render_config['colors']

            for i, (idx, row) in enumerate(data.iterrows()):
                color = colors['up'] if row['close'] >= row['open'] else colors['down']

                # 绘制实体
                height = abs(row['close'] - row['open'])
                bottom = min(row['close'], row['open'])
                ax.bar(i, height, bottom=bottom, color=color, width=0.6, alpha=0.8)

                # 绘制影线
                ax.plot([i, i], [row['low'], row['high']], color='black', linewidth=0.5)

            # 添加技术指标
            indicators = config.get('indicators', {})
            for indicator_name, indicator_data in indicators.items():
                if len(indicator_data) == len(data):
                    color = colors.get(indicator_name.lower(), 'blue')
                    ax.plot(range(len(data)), indicator_data,
                            color=color, linewidth=self.render_config['line_width'],
                            label=indicator_name)

            if indicators or True:  # 总是显示图例
                # 检查是否有带标签的对象才创建图例
                handles, labels = ax.get_legend_handles_labels()
                if handles and labels:
                    ax.legend()

        except Exception as e:
            raise Exception(f"绘制K线失败: {str(e)}")

    def plot_volume(self, ax, data: pd.DataFrame, config: Dict[str, Any]):
        """绘制成交量"""
        try:
            colors = self.render_config['colors']

            volume_colors = [colors['up'] if close >= open else colors['down']
                             for close, open in zip(data['close'], data['open'])]

            ax.bar(range(len(data)), data['volume'], color=volume_colors, alpha=0.7)

        except Exception as e:
            raise Exception(f"绘制成交量失败: {str(e)}")

    def format_xaxis(self, ax, dates):
        """格式化x轴"""
        try:
            # 设置x轴标签
            step = max(1, len(dates) // 10)  # 最多显示10个标签
            ax.set_xticks(range(0, len(dates), step))
            ax.set_xticklabels([dates[i].strftime('%m-%d') for i in range(0, len(dates), step)],
                               rotation=45)

        except Exception as e:
            if self.log_manager:
                self.log_manager.warning(f"格式化x轴失败: {str(e)}")

    def render_line_chart_sync(self, data: pd.DataFrame, config: Dict[str, Any]) -> Figure:
        """同步渲染线图"""
        try:
            fig, ax = plt.subplots(figsize=self.render_config['figure_size'])

            # 绘制收盘价线
            ax.plot(range(len(data)), data['close'],
                    color='blue', linewidth=self.render_config['line_width'],
                    label='收盘价')

            # 添加技术指标
            indicators = config.get('indicators', {})
            colors = self.render_config['colors']

            for indicator_name, indicator_data in indicators.items():
                if len(indicator_data) == len(data):
                    color = colors.get(indicator_name.lower(), 'red')
                    ax.plot(range(len(data)), indicator_data,
                            color=color, linewidth=self.render_config['line_width'],
                            label=indicator_name)

            # 设置标题和标签
            ax.set_title(config.get('title', '线图'))
            ax.set_ylabel('价格')
            ax.set_xlabel('时间')

            # 格式化x轴
            self.format_xaxis(ax, data.index)

            if indicators or True:  # 总是显示图例
                # 检查是否有带标签的对象才创建图例
                handles, labels = ax.get_legend_handles_labels()
                if handles and labels:
                    ax.legend()

            plt.tight_layout()
            return fig

        except Exception as e:
            raise Exception(f"同步渲染线图失败: {str(e)}")

    def render_volume_chart_sync(self, data: pd.DataFrame, config: Dict[str, Any]) -> Figure:
        """同步渲染成交量图"""
        try:
            fig, ax = plt.subplots(figsize=(self.render_config['figure_size'][0],
                                            self.render_config['figure_size'][1] * 0.4))

            # 绘制成交量
            self.plot_volume(ax, data, config)

            # 设置标题和标签
            ax.set_title(config.get('title', '成交量图'))
            ax.set_ylabel('成交量')
            ax.set_xlabel('时间')

            # 格式化x轴
            self.format_xaxis(ax, data.index)

            plt.tight_layout()
            return fig

        except Exception as e:
            raise Exception(f"同步渲染成交量图失败: {str(e)}")

    def render_indicator_chart_sync(self, data: pd.DataFrame, config: Dict[str, Any]) -> Figure:
        """同步渲染指标图"""
        try:
            fig, ax = plt.subplots(figsize=self.render_config['figure_size'])

            indicators = config.get('indicators', {})
            colors = self.render_config['colors']

            for indicator_name, indicator_data in indicators.items():
                if len(indicator_data) == len(data):
                    color = colors.get(indicator_name.lower(), 'blue')
                    ax.plot(range(len(data)), indicator_data,
                            color=color, linewidth=self.render_config['line_width'],
                            label=indicator_name)

            # 设置标题和标签
            ax.set_title(config.get('title', '技术指标'))
            ax.set_ylabel('指标值')
            ax.set_xlabel('时间')

            # 格式化x轴
            self.format_xaxis(ax, data.index)

            if indicators or True:  # 总是显示图例
                # 检查是否有带标签的对象才创建图例
                handles, labels = ax.get_legend_handles_labels()
                if handles and labels:
                    ax.legend()

            plt.tight_layout()
            return fig

        except Exception as e:
            raise Exception(f"同步渲染指标图失败: {str(e)}")

    def generate_cache_key(self, data: pd.DataFrame, config: Dict[str, Any]) -> str:
        """生成缓存键"""
        try:
            # 基于数据和配置生成唯一键
            data_hash = hash(str(data.index[-1]) + str(len(data)) + str(data['close'].iloc[-1]))
            config_hash = hash(str(sorted(config.items())))
            return f"chart_{data_hash}_{config_hash}"

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"生成缓存键失败: {str(e)}")
            return f"chart_{datetime.now().timestamp()}"

    def cache_chart(self, cache_key: str, chart_data: Any):
        """缓存图表"""
        try:
            # 检查缓存大小
            if len(self.chart_cache) >= self.max_cache_size:
                # 删除最旧的缓存项
                oldest_key = next(iter(self.chart_cache))
                del self.chart_cache[oldest_key]

            self.chart_cache[cache_key] = chart_data

            if self.log_manager:
                self.log_manager.debug(f"图表已缓存: {cache_key}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"缓存图表失败: {str(e)}")

    def clear_cache(self):
        """清空缓存"""
        try:
            self.chart_cache.clear()
            if self.log_manager:
                self.log_manager.info("图表缓存已清空")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清空缓存失败: {str(e)}")

    def on_render_completed(self, cache_key: str, result: Any):
        """渲染完成回调"""
        try:
            # 缓存结果
            self.cache_chart(cache_key, result)

            # 记录渲染时间
            if hasattr(self, 'current_render_start'):
                render_time = (datetime.now() - self.current_render_start).total_seconds()
                self.record_render_time(render_time)

            # 发送信号
            self.chart_rendered.emit(result)

            if self.log_manager:
                self.log_manager.debug(f"图表渲染完成: {cache_key}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"处理渲染完成回调失败: {str(e)}")

    def on_render_error(self, error_msg: str):
        """渲染错误回调"""
        try:
            if self.log_manager:
                self.log_manager.error(f"图表渲染错误: {error_msg}")

            self.chart_error.emit(error_msg)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"处理渲染错误回调失败: {str(e)}")

    def record_render_time(self, render_time: float):
        """记录渲染时间"""
        try:
            self.render_times.append(render_time)

            # 限制记录数量
            if len(self.render_times) > self.max_render_time_records:
                self.render_times.pop(0)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"记录渲染时间失败: {str(e)}")

    def get_render_statistics(self) -> Dict[str, Any]:
        """获取渲染统计信息"""
        try:
            if not self.render_times:
                return {}

            return {
                'total_renders': len(self.render_times),
                'average_time': sum(self.render_times) / len(self.render_times),
                'min_time': min(self.render_times),
                'max_time': max(self.render_times),
                'cache_size': len(self.chart_cache),
                'cache_hit_rate': self.calculate_cache_hit_rate()
            }

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取渲染统计信息失败: {str(e)}")
            return {}

    def calculate_cache_hit_rate(self) -> float:
        """计算缓存命中率"""
        # 这里需要实际的缓存命中统计，简化实现
        return 0.0

    def update_render_config(self, config: Dict[str, Any]):
        """更新渲染配置"""
        try:
            self.render_config.update(config)

            # 重新初始化matplotlib设置
            self.init_matplotlib_settings()

            # 清空缓存以应用新配置
            self.clear_cache()

            if self.log_manager:
                self.log_manager.info("渲染配置已更新")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新渲染配置失败: {str(e)}")

    def export_chart(self, chart_data: Any, file_path: str, format: str = 'png') -> bool:
        """导出图表"""
        try:
            if isinstance(chart_data, Figure):
                # matplotlib图表
                chart_data.savefig(file_path, format=format, dpi=self.render_config['dpi'],
                                   bbox_inches='tight')
            else:
                # plotly图表
                if format.lower() == 'html':
                    chart_data.write_html(file_path)
                elif format.lower() in ['png', 'jpg', 'jpeg']:
                    chart_data.write_image(file_path, format=format)
                else:
                    raise ValueError(f"不支持的导出格式: {format}")

            if self.log_manager:
                self.log_manager.info(f"图表已导出: {file_path}")

            return True

        except Exception as e:
            error_msg = f"导出图表失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            return False
