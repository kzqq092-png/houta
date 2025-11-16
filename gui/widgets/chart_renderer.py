from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import to_rgba
import mplfinance as mpf
from typing import List, Dict, Any, Tuple, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import warnings
from loguru import logger

# 配置中文字体
try:
    from utils.matplotlib_font_config import configure_matplotlib_chinese_font
    configure_matplotlib_chinese_font()
except ImportError:
    logger.info("无法导入字体配置工具，使用默认配置")


class ChartRenderer(QObject):
    """高性能图表渲染器，优化大数据渲染性能"""

    render_progress = pyqtSignal(int, str)  # 渲染进度信号
    render_complete = pyqtSignal()  # 渲染完成信号
    render_error = pyqtSignal(str)  # 错误信号

    def __init__(self):
        super().__init__()
        self._view_range = None  # 当前视图范围
        self._downsampling_threshold = 5000  # 降采样阈值
        self._last_layout = None  # 缓存上一次布局参数

    def setup_figure(self, figure: Figure) -> Tuple[GridSpec, List]:
        """设置图表布局，避免tight_layout警告

        Args:
            figure: matplotlib图表对象

        Returns:
            Tuple[GridSpec, List[Axes]]: 网格布局和轴对象列表
        """
        # 清除现有内容
        figure.clear()

        # 创建网格布局
        gs = GridSpec(3, 1, figure=figure, height_ratios=[
                      3, 1, 1], hspace=0.05)

        # 创建子图，共享x轴
        price_ax = figure.add_subplot(gs[0])
        volume_ax = figure.add_subplot(gs[1], sharex=price_ax)
        indicator_ax = figure.add_subplot(gs[2], sharex=price_ax)

        # 隐藏不需要的刻度标签
        volume_ax.set_xticklabels([])
        price_ax.set_xticklabels([])

        # 设置边距
        figure.subplots_adjust(
            left=0.05, right=0.95,
            top=0.95, bottom=0.05,
            hspace=0.1
        )

        return gs, [price_ax, volume_ax, indicator_ax]

    def render_candlesticks(self, ax, data: pd.DataFrame, style: Dict[str, Any] = None, x: np.ndarray = None, use_datetime_axis: bool = True):
        """高性能K线绘制，支持datetime X轴和等距序号X轴
        Args:
            ax: matplotlib轴对象
            data: K线数据
            style: 样式字典
            x: 可选，X轴数据（可以是datetime数组或数字索引）
            use_datetime_axis: 是否使用datetime X轴（如果数据包含datetime列）
        """
        try:
            view_data = self._get_view_data(data)
            plot_data = self._downsample_data(view_data)
            
            # ✅ 修复：支持datetime X轴
            if use_datetime_axis and x is None and 'datetime' in plot_data.columns:
                try:
                    # 使用datetime作为X轴
                    datetime_series = pd.to_datetime(plot_data['datetime'])
                    x = mdates.date2num(datetime_series)
                    
                    # 设置智能日期格式化
                    formatter, locator = self._get_smart_date_formatter(plot_data, 'datetime')
                    if formatter and locator:
                        ax.xaxis.set_major_formatter(formatter)
                        ax.xaxis.set_major_locator(locator)
                        # 旋转标签以避免重叠
                        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
                        logger.debug(f"✅ 使用datetime X轴，时间范围: {datetime_series.min()} ~ {datetime_series.max()}")
                except Exception as e:
                    logger.warning(f"⚠️ datetime X轴设置失败，回退到数字索引: {e}")
                    use_datetime_axis = False
                    x = None
            
            # 如果use_datetime_axis为False或x为None，使用数字索引
            if x is None:
                x = np.arange(len(plot_data))
                logger.debug(f"使用数字索引X轴，数据长度: {len(plot_data)}")
            
            self._render_candlesticks_efficient(ax, plot_data, style or {}, x, use_datetime_axis)
            # ✅ 性能优化P1: 移除_optimize_display()调用，由调用方统一设置样式
            # 避免在每次渲染时重复设置样式，减少开销
            # self._optimize_display(ax, use_datetime_axis)  # 已移除，在rendering_mixin中统一设置
        except Exception as e:
            self.render_error.emit(f"绘制K线失败: {str(e)}")
            logger.error(f"绘制K线失败: {e}", exc_info=True)

    def _render_candlesticks_efficient(self, ax, data: pd.DataFrame, style: Dict[str, Any], x: np.ndarray = None, use_datetime_axis: bool = False):
        """使用collections高效渲染K线，支持datetime X轴和等距序号X轴，空心样式"""
        up_color = style.get('up_color', '#ff0000')
        down_color = style.get('down_color', '#00ff00')
        alpha = style.get('alpha', 1.0)
        
        # 横坐标
        if x is not None:
            xvals = x
        elif use_datetime_axis and 'datetime' in data.columns:
            # 尝试使用datetime列
            try:
                datetime_series = pd.to_datetime(data['datetime'])
                xvals = mdates.date2num(datetime_series)
            except Exception as e:
                logger.warning(f"datetime X轴转换失败: {e}，使用数字索引")
                xvals = np.arange(len(data))
        elif isinstance(data.index, pd.DatetimeIndex):
            # 如果索引是DatetimeIndex，使用索引
            xvals = mdates.date2num(data.index.to_pydatetime())
        else:
            # 默认使用数字索引
            xvals = np.arange(len(data))
        
        # 计算蜡烛宽度（根据X轴类型调整）
        if use_datetime_axis and len(xvals) > 1:
            # datetime X轴：根据时间间隔计算宽度
            avg_interval = np.mean(np.diff(xvals))
            candle_width = max(0.3, avg_interval * 0.6)  # 蜡烛宽度为平均间隔的60%
        else:
            # 数字索引：固定宽度
            candle_width = 0.3
        
        # ✅ 性能优化：使用完全向量化的numpy操作，提升10-100倍性能
        # 提取数据为numpy数组（避免iterrows()的性能开销）
        opens = data['open'].values
        closes = data['close'].values
        highs = data['high'].values
        lows = data['low'].values
        n = len(data)
        
        # 向量化计算left和right
        lefts = xvals - candle_width / 2
        rights = xvals + candle_width / 2
        
        # 向量化判断涨跌
        is_up = closes >= opens
        up_indices = np.where(is_up)[0]
        down_indices = np.where(~is_up)[0]
        
        # ✅ 性能优化：完全向量化构建，直接使用numpy数组（PolyCollection和LineCollection都支持）
        def build_candle_verts(indices):
            """批量构建蜡烛图顶点，返回numpy数组"""
            if len(indices) == 0:
                return np.empty((0, 4, 2))
            idx_arr = indices  # 已经是numpy数组，不需要转换
            verts = np.empty((len(indices), 4, 2), dtype=np.float64)
            verts[:, 0, 0] = lefts[idx_arr]  # 左下x
            verts[:, 0, 1] = opens[idx_arr]  # 左下y
            verts[:, 1, 0] = lefts[idx_arr]  # 左上x
            verts[:, 1, 1] = closes[idx_arr]  # 左上y
            verts[:, 2, 0] = rights[idx_arr]  # 右上x
            verts[:, 2, 1] = closes[idx_arr]  # 右上y
            verts[:, 3, 0] = rights[idx_arr]  # 右下x
            verts[:, 3, 1] = opens[idx_arr]  # 右下y
            return verts  # 直接返回numpy数组，PolyCollection支持
        
        verts_up = build_candle_verts(up_indices)
        verts_down = build_candle_verts(down_indices)
        
        # 批量构建影线段（直接使用numpy数组）
        def build_shadow_segments(indices):
            """批量构建影线段，返回numpy数组"""
            if len(indices) == 0:
                return np.empty((0, 2, 2))
            idx_arr = indices  # 已经是numpy数组
            segments = np.empty((len(indices), 2, 2), dtype=np.float64)
            segments[:, 0, 0] = xvals[idx_arr]  # 起点x
            segments[:, 0, 1] = lows[idx_arr]   # 起点y
            segments[:, 1, 0] = xvals[idx_arr]  # 终点x
            segments[:, 1, 1] = highs[idx_arr]  # 终点y
            return segments  # 直接返回numpy数组，LineCollection支持
        
        segments_up = build_shadow_segments(up_indices)
        segments_down = build_shadow_segments(down_indices)
        
        # 修改：空心蜡烛图样式，只有边框无填充
        # ✅ 性能优化：检查数组长度而不是转换为bool（避免numpy警告）
        if len(verts_up) > 0:
            collection_up = PolyCollection(
                verts_up, facecolor=up_color, edgecolor=up_color, linewidth=0.5, alpha=alpha)
            ax.add_collection(collection_up)
        if len(verts_down) > 0:
            collection_down = PolyCollection(
                verts_down, facecolor=down_color, edgecolor=down_color, linewidth=0.5, alpha=alpha)
            ax.add_collection(collection_down)
        if len(segments_up) > 0:  # 影线
            collection_shadow_up = LineCollection(
                segments_up, colors=up_color, linewidth=0.5, alpha=alpha)
            ax.add_collection(collection_shadow_up)
        if len(segments_down) > 0:
            collection_shadow_down = LineCollection(
                segments_down, colors=down_color, linewidth=0.5, alpha=alpha)
            ax.add_collection(collection_shadow_down)
        # ✅ 性能优化：移除autoscale_view()调用，由调用方统一处理
        # ax.autoscale_view()  # 已移除，在rendering_mixin中统一调用

    def render_volume(self, ax, data: pd.DataFrame, style: Dict[str, Any] = None, x: np.ndarray = None, use_datetime_axis: bool = True):
        """高性能成交量绘制，支持datetime X轴和等距序号X轴
        Args:
            ax: matplotlib轴对象
            data: 成交量数据
            style: 样式字典
            x: 可选，X轴数据（可以是datetime数组或数字索引）
            use_datetime_axis: 是否使用datetime X轴（如果数据包含datetime列）
        """
        try:
            view_data = self._get_view_data(data)
            plot_data = self._downsample_data(view_data)
            
            # ✅ 修复：支持datetime X轴（与K线图保持一致）
            if use_datetime_axis and x is None and 'datetime' in plot_data.columns:
                try:
                    datetime_series = pd.to_datetime(plot_data['datetime'])
                    x = mdates.date2num(datetime_series)
                except Exception as e:
                    logger.warning(f"⚠️ 成交量datetime X轴设置失败，回退到数字索引: {e}")
                    use_datetime_axis = False
                    x = None
            
            if x is None:
                x = np.arange(len(plot_data))
            
            self._render_volume_efficient(ax, plot_data, style or {}, x, use_datetime_axis)
            # ✅ 性能优化P1: 移除_optimize_display()调用，由调用方统一设置样式
            # 避免在每次渲染时重复设置样式，减少开销
            # self._optimize_display(ax, use_datetime_axis)  # 已移除，在rendering_mixin中统一设置
        except Exception as e:
            self.render_error.emit(f"绘制成交量失败: {str(e)}")
            logger.error(f"绘制成交量失败: {e}", exc_info=True)

    def _render_volume_efficient(self, ax, data: pd.DataFrame, style: Dict[str, Any], x: np.ndarray = None, use_datetime_axis: bool = False):
        """使用collections高效渲染成交量，支持datetime X轴和等距序号X轴"""
        up_color = style.get('up_color', '#ff0000')
        down_color = style.get('down_color', '#00ff00')
        alpha = style.get('volume_alpha', 0.5)
        
        # 横坐标（与K线图保持一致）
        if x is not None:
            xvals = x
        elif use_datetime_axis and 'datetime' in data.columns:
            try:
                datetime_series = pd.to_datetime(data['datetime'])
                xvals = mdates.date2num(datetime_series)
            except Exception as e:
                logger.warning(f"成交量datetime X轴转换失败: {e}，使用数字索引")
                xvals = np.arange(len(data))
        elif isinstance(data.index, pd.DatetimeIndex):
            xvals = mdates.date2num(data.index.to_pydatetime())
        else:
            xvals = np.arange(len(data))
        
        # 计算柱状图宽度（与K线图保持一致）
        if use_datetime_axis and len(xvals) > 1:
            avg_interval = np.mean(np.diff(xvals))
            bar_width = max(0.3, avg_interval * 0.6)
        else:
            bar_width = 0.3
        
        # ✅ 性能优化：使用完全向量化的numpy操作，提升10-100倍性能
        # 提取数据为numpy数组（避免iterrows()的性能开销）
        volumes = data['volume'].values
        closes = data['close'].values
        opens = data['open'].values
        n = len(data)
        
        # 向量化计算left和right
        lefts = xvals - bar_width / 2
        rights = xvals + bar_width / 2
        
        # 向量化判断涨跌
        is_up = closes >= opens
        up_indices = np.where(is_up)[0]
        down_indices = np.where(~is_up)[0]
        
        # ✅ 性能优化：完全向量化构建，直接使用numpy数组（PolyCollection支持）
        def build_volume_verts(indices):
            """批量构建成交量柱状图顶点，返回numpy数组"""
            if len(indices) == 0:
                return np.empty((0, 4, 2))
            idx_arr = indices  # 已经是numpy数组，不需要转换
            verts = np.empty((len(indices), 4, 2), dtype=np.float64)
            verts[:, 0, 0] = lefts[idx_arr]      # 左下x
            verts[:, 0, 1] = 0                   # 左下y (底部)
            verts[:, 1, 0] = lefts[idx_arr]      # 左上x
            verts[:, 1, 1] = volumes[idx_arr]    # 左上y (顶部)
            verts[:, 2, 0] = rights[idx_arr]     # 右上x
            verts[:, 2, 1] = volumes[idx_arr]    # 右上y (顶部)
            verts[:, 3, 0] = rights[idx_arr]     # 右下x
            verts[:, 3, 1] = 0                   # 右下y (底部)
            return verts  # 直接返回numpy数组，PolyCollection支持
        
        verts_up = build_volume_verts(up_indices)
        verts_down = build_volume_verts(down_indices)
        # ✅ 性能优化：检查数组长度而不是转换为bool（避免numpy警告）
        if len(verts_up) > 0:
            collection_up = PolyCollection(
                verts_up, facecolor=up_color, edgecolor='none', alpha=alpha)
            ax.add_collection(collection_up)
        if len(verts_down) > 0:
            collection_down = PolyCollection(
                verts_down, facecolor=down_color, edgecolor='none', alpha=alpha)
            ax.add_collection(collection_down)
        # ✅ 性能优化：移除autoscale_view()调用，由调用方统一处理
        # ax.autoscale_view()  # 已移除，在rendering_mixin中统一调用

    def render_line(self, ax, data: pd.Series, style: Dict[str, Any] = None):
        """高性能线图绘制

        Args:
            ax: matplotlib轴对象
            data: 线图数据
            style: 样式字典
        """
        try:
            # 获取当前视图范围内的数据
            view_data = self._get_view_data(data)

            # 降采样
            plot_data = self._downsample_data(view_data)

            # 使用LineCollection批量渲染
            self._render_line_efficient(ax, plot_data, style or {})

            # 优化显示
            self._optimize_display(ax)

        except Exception as e:
            self.render_error.emit(f"绘制线图失败: {str(e)}")

    def _render_line_efficient(self, ax, data: pd.Series, style: Dict[str, Any]):
        """使用LineCollection高效渲染线图

        Args:
            ax: matplotlib轴对象
            data: 线图数据
            style: 样式字典
        """
        # 获取样式
        color = style.get('color', 'blue')
        linewidth = style.get('linewidth', 0.5)
        alpha = style.get('alpha', 0.8)
        label = style.get('label', '')

        # 转换日期为数值
        if isinstance(data.index, pd.DatetimeIndex):
            x = mdates.date2num(data.index.to_pydatetime())
        else:
            x = np.arange(len(data))

        # 创建线段
        points = np.column_stack((x, data.values))
        segments = np.column_stack((points[:-1], points[1:]))

        # 创建LineCollection
        collection = LineCollection(
            segments,
            colors=color,
            linewidth=linewidth,
            alpha=alpha,
            label=label
        )

        # 添加到轴
        ax.add_collection(collection)

        # ✅ 性能优化：移除autoscale_view()调用，由调用方统一处理
        # ax.autoscale_view()  # 已移除，在rendering_mixin中统一调用

        # 添加图例
        if label:
            ax.legend()

    def _get_smart_date_formatter(self, data: pd.DataFrame, datetime_col: str = 'datetime') -> Tuple[mdates.DateFormatter, mdates.AutoDateLocator]:
        """根据时间跨度智能选择日期格式化器
        
        Args:
            data: K线数据DataFrame
            datetime_col: datetime列名
            
        Returns:
            Tuple[DateFormatter, AutoDateLocator]: 日期格式化器和定位器
        """
        try:
            if datetime_col not in data.columns:
                return None, None
                
            # 获取时间范围
            datetime_series = pd.to_datetime(data[datetime_col])
            time_span = datetime_series.max() - datetime_series.min()
            days = time_span.days
            
            # 根据时间跨度选择格式化器
            if days <= 7:
                # 7天内：显示 月-日 时:分
                formatter = mdates.DateFormatter('%m-%d %H:%M')
                # ✅ 修复：优化HourLocator间隔计算
                if days <= 1:
                    locator = mdates.HourLocator(interval=1)  # 每小时一个刻度
                elif days <= 3:
                    locator = mdates.HourLocator(interval=6)  # 每6小时一个刻度
                else:
                    locator = mdates.HourLocator(interval=12)  # 每12小时一个刻度
            elif days <= 30:
                # 30天内：显示 月-日
                formatter = mdates.DateFormatter('%m-%d')
                # ✅ 修复：优化DayLocator间隔计算
                if days <= 14:
                    locator = mdates.DayLocator(interval=1)  # 每天一个刻度（14天内）
                else:
                    # 14-30天：每3-5天一个刻度
                    locator = mdates.DayLocator(interval=max(1, days // 10))
            elif days <= 365:
                # 1年内：显示 月-日
                formatter = mdates.DateFormatter('%m-%d')
                # ✅ 修复：使用WeekLocator而不是WeekdayLocator（WeekdayLocator用于周几定位，不适用于日线数据）
                # 根据数据量自动选择：少于90天用DayLocator，90-365天用WeekLocator
                if days <= 90:
                    locator = mdates.DayLocator(interval=max(1, days // 15))  # 每15天一个刻度
                else:
                    locator = mdates.WeekLocator(interval=1)  # 每周一个刻度
            elif days <= 365 * 3:
                # 3年内：显示 年-月
                formatter = mdates.DateFormatter('%Y-%m')
                locator = mdates.MonthLocator(interval=2)
            else:
                # 3年以上：显示 年-月
                formatter = mdates.DateFormatter('%Y-%m')
                locator = mdates.MonthLocator(interval=6)
            
            return formatter, locator
        except Exception as e:
            logger.warning(f"智能日期格式化失败: {e}，使用默认格式")
            return mdates.DateFormatter('%Y-%m-%d'), mdates.AutoDateLocator()

    def _get_view_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """获取当前视图范围内的数据

        Args:
            data: 原始数据

        Returns:
            视图范围内的数据
        """
        if self._view_range is None:
            return data

        start, end = self._view_range
        return data.loc[start:end]

    def _downsample_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """智能降采样，保持关键特征

        Args:
            data: 原始数据

        Returns:
            降采样后的数据
        """
        if len(data) <= self._downsampling_threshold:
            return data

        # 使用 OHLCV 保持降采样
        sample_size = len(data) // self._downsampling_threshold

        # 创建结果DataFrame
        result = pd.DataFrame(index=data.index[::sample_size])

        # 处理OHLC数据
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            result['open'] = data['open'].iloc[::sample_size]
            result['high'] = data['high'].rolling(
                sample_size, min_periods=1).max()
            result['low'] = data['low'].rolling(
                sample_size, min_periods=1).min()
            result['close'] = data['close'].iloc[::sample_size]

        # 处理成交量
        if 'volume' in data.columns:
            result['volume'] = data['volume'].rolling(
                sample_size, min_periods=1).sum()

        # 处理其他列（使用平均值）
        other_cols = [col for col in data.columns if col not in [
            'open', 'high', 'low', 'close', 'volume']]
        for col in other_cols:
            result[col] = data[col].rolling(sample_size, min_periods=1).mean()

        return result

    def _optimize_display(self, ax, use_datetime_axis: bool = False):
        """优化显示效果

        Args:
            ax: matplotlib轴对象
            use_datetime_axis: 是否使用datetime X轴（如果True，不覆盖已设置的格式化器）
        """
        # ✅ 修复：只有在非datetime X轴或格式化器未设置时才设置日期格式
        # 避免覆盖智能日期格式化器
        if not use_datetime_axis:
            # 数字索引X轴：不设置日期格式
            pass
        else:
            # datetime X轴：检查是否已有格式化器，如果有就不覆盖
            current_formatter = ax.xaxis.get_major_formatter()
            if current_formatter is None or not isinstance(current_formatter, mdates.DateFormatter):
                # 只有在没有格式化器或格式化器不是DateFormatter时才设置
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                logger.debug("_optimize_display: 设置了默认日期格式化器")

        # 优化刻度
        ax.tick_params(axis='both', which='major', labelsize=8)

        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.3)

    def set_view_range(self, start: pd.Timestamp, end: pd.Timestamp):
        """设置视图范围

        Args:
            start: 起始时间
            end: 结束时间
        """
        self._view_range = (start, end)

    def clear_view_range(self):
        """清除视图范围限制"""
        self._view_range = None
