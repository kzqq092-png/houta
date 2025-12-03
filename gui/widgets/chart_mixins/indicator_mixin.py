from loguru import logger
"""
Chart组件的指标渲染混入类
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Tuple, Optional
from PyQt5.QtCore import QTimer, pyqtSignal
import traceback
import time
from datetime import datetime

# 替换旧的指标系统导入
from core.indicator_service import get_indicator_metadata, calculate_indicator
from core.indicator_adapter import get_indicator_english_name

class IndicatorMixin:
    """指标渲染混入类"""

    def _calculate_macd(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD指标"""
        close = data['close']
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist

    def _calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_boll(self, data: pd.DataFrame, n: int = 20, k: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带指标"""
        mid = data['close'].rolling(n).mean()
        std = data['close'].rolling(n).std()
        upper = mid + k * std
        lower = mid - k * std
        return mid, upper, lower

    def _get_active_indicators(self) -> list:
        """
        统一通过主窗口接口获取当前激活的所有指标及参数
        Returns:
            List[dict]: [{"name": 指标名, "params": 参数字典}, ...]
        """
        main_window = self.parentWidget()
        while main_window and not hasattr(main_window, 'get_current_indicators'):
            main_window = main_window.parentWidget() if hasattr(
                main_window, 'parentWidget') else None
        if main_window and hasattr(main_window, 'get_current_indicators'):
            return main_window.get_current_indicators()
        # 兜底：如果未找到主窗口接口，返回默认指标
        return [
            {"name": "MA20", "params": {"period": 20}},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}},
            {"name": "RSI", "params": {"period": 14}},
            {"name": "BOLL", "params": {"period": 20, "std": 2.0}}
        ]

    def _render_indicators(self, kdata: pd.DataFrame, x=None):
        """渲染技术指标，所有指标与K线对齐，节假日无数据自动跳过，X轴为等距序号。"""
        try:
            logger.info(f"🎨 _render_indicators开始执行")
            indicators = getattr(self, 'active_indicators', None)
            # 如果active_indicators为None，使用空列表
            if indicators is None:
                indicators = []
            logger.info(f"🎨 获取到active_indicators: {len(indicators) if indicators else 0}个指标")
            if not indicators:
                logger.warning(f"❌ active_indicators为空或不存在，_render_indicators直接返回")
                return

            if x is None:
                x = np.arange(len(kdata))

            for i, indicator in enumerate(indicators):
                name = indicator.get('name', '')
                group = indicator.get('group', '')
                params = indicator.get('params', {})
                formula = indicator.get('formula', None)
                style = self._get_indicator_style(name, i)

                try:
                    # 使用新的指标系统计算指标
                    if name.startswith('MA') and (group == 'builtin' or name[2:].isdigit()):
                        # 处理MA指标
                        period = int(params.get('n', name[2:]) or 5)
                        result_df = calculate_indicator(
                            'MA', kdata, {'timeperiod': period})
                        if 'MA' in result_df.columns:
                            ma_values = result_df['MA'].values
                            valid_indices = ~np.isnan(ma_values)
                            if np.any(valid_indices):
                                valid_x = x[valid_indices]
                                valid_values = ma_values[valid_indices]
                                self.price_ax.plot(valid_x, valid_values, color=style['color'],
                                                   linewidth=style['linewidth'], alpha=style['alpha'], label=name)

                    elif name == 'MACD' and group == 'builtin':
                        # 处理MACD指标
                        result_df = calculate_indicator('MACD', kdata, {
                            'fastperiod': int(params.get('fast', 12)),
                            'slowperiod': int(params.get('slow', 26)),
                            'signalperiod': int(params.get('signal', 9))
                        })

                        if all(col in result_df.columns for col in ['MACD', 'MACDSignal', 'MACDHist']):
                            macd_values = result_df['MACD'].values
                            signal_values = result_df['MACDSignal'].values
                            hist_values = result_df['MACDHist'].values

                            # 过滤NaN值
                            valid_indices = ~np.isnan(macd_values)
                            if np.any(valid_indices):
                                valid_x = x[valid_indices]
                                valid_macd = macd_values[valid_indices]
                                valid_signal = signal_values[valid_indices]
                                valid_hist = hist_values[valid_indices]

                                self.indicator_ax.plot(valid_x, valid_macd,
                                                       color=self._get_indicator_style('MACD', i)[
                                                           'color'],
                                                       linewidth=0.7, alpha=0.85, label='MACD')
                                self.indicator_ax.plot(valid_x, valid_signal,
                                                       color=self._get_indicator_style(
                                                           'MACD-Signal', i+1)['color'],
                                                       linewidth=0.7, alpha=0.85, label='Signal')

                                # 绘制柱状图
                                colors = ['red' if h >=
                                          0 else 'green' for h in valid_hist]
                                self.indicator_ax.bar(
                                    valid_x, valid_hist, color=colors, alpha=0.5, width=0.6)

                    elif name == 'RSI' and group == 'builtin':
                        # 处理RSI指标
                        period = int(params.get('n', 14))
                        result_df = calculate_indicator(
                            'RSI', kdata, {'timeperiod': period})

                        if 'RSI' in result_df.columns:
                            rsi_values = result_df['RSI'].values
                            valid_indices = ~np.isnan(rsi_values)
                            if np.any(valid_indices):
                                valid_x = x[valid_indices]
                                valid_values = rsi_values[valid_indices]
                                self.indicator_ax.plot(valid_x, valid_values, color=style['color'],
                                                       linewidth=style['linewidth'], alpha=style['alpha'], label='RSI')

                    elif name == 'BOLL' and group == 'builtin':
                        # 处理布林带指标
                        n = int(params.get('n', 20))
                        p = float(params.get('p', 2))
                        result_df = calculate_indicator('BBANDS', kdata, {
                            'timeperiod': n,
                            'nbdevup': p,
                            'nbdevdn': p
                        })

                        if all(col in result_df.columns for col in ['BBMiddle', 'BBUpper', 'BBLower']):
                            mid_values = result_df['BBMiddle'].values
                            upper_values = result_df['BBUpper'].values
                            lower_values = result_df['BBLower'].values

                            # 过滤NaN值
                            valid_indices = ~np.isnan(mid_values)
                            if np.any(valid_indices):
                                valid_x = x[valid_indices]
                                valid_mid = mid_values[valid_indices]
                                valid_upper = upper_values[valid_indices]
                                valid_lower = lower_values[valid_indices]

                                self.price_ax.plot(valid_x, valid_mid,
                                                   color=self._get_indicator_style(
                                                       'BOLL-Mid', i)['color'],
                                                   linewidth=0.5, alpha=0.85, label='BOLL-Mid')
                                self.price_ax.plot(valid_x, valid_upper,
                                                   color=self._get_indicator_style(
                                                       'BOLL-Upper', i+1)['color'],
                                                   linewidth=0.7, alpha=0.85, label='BOLL-Upper')
                                self.price_ax.plot(valid_x, valid_lower,
                                                   color=self._get_indicator_style(
                                                       'BOLL-Lower', i+2)['color'],
                                                   linewidth=0.5, alpha=0.85, label='BOLL-Lower')

                    elif group == 'talib':
                        # 处理其他TA-Lib指标
                        try:
                            # 如果name是中文名称，需要转换为英文名称
                            english_name = get_indicator_english_name(name)

                            # 为某些需要特定参数的指标提供默认参数
                            final_params = params.copy() if params else {}

                            # 定义各指标的默认参数（TA-Lib要求）
                            default_params_map = {
                                'ADOSC': {'fastperiod': 3, 'slowperiod': 10},  # AD Oscillator
                                'AROON': {'timeperiod': 25},  # Aroon
                                'AROONOSC': {'timeperiod': 25},  # Aroon Oscillator
                                'ATR': {'timeperiod': 14},  # Average True Range
                                'BBANDS': {'timeperiod': 5, 'nbdevup': 2, 'nbdevdn': 2},  # Bollinger Bands
                                'CCI': {'timeperiod': 14},  # Commodity Channel Index
                                'CMO': {'timeperiod': 14},  # Chande Momentum Oscillator
                                'DX': {'timeperiod': 14},  # Directional Movement Index
                                'KAMA': {'timeperiod': 10},  # Kaufman's Adaptive Moving Average
                                'MACD': {'fastperiod': 12, 'slowperiod': 26, 'signalperiod': 9},
                                'MFI': {'timeperiod': 14},  # Money Flow Index
                                'NATR': {'timeperiod': 14},  # Normalized Average True Range
                                'RSI': {'timeperiod': 14},
                                'STOCH': {'fastk_period': 5, 'slowk_period': 3, 'slowd_period': 3},
                                'STOCHF': {'fastk_period': 5, 'fastd_period': 3},
                                'STOCHRSI': {'timeperiod': 14, 'fastk_period': 5, 'fastd_period': 3},
                                'TRANGE': {'timeperiod': 14},
                                'WILLR': {'timeperiod': 14},
                            }

                            # 如果指标有默认参数且当前params为空，则使用默认参数
                            if english_name in default_params_map and not final_params:
                                final_params = default_params_map[english_name]

                            logger.debug(f"计算{english_name}指标，参数: {final_params}")

                            # 使用新的指标系统计算
                            result_df = calculate_indicator(
                                english_name, kdata, **final_params)

                            # 遍历结果中的每一列，绘制到图表上
                            for j, col in enumerate(result_df.columns):
                                if col in ['open', 'high', 'low', 'close', 'volume', 'datetime']:
                                    continue  # 跳过原始数据列

                                values = result_df[col].values
                                valid_indices = ~np.isnan(values)
                                if np.any(valid_indices):
                                    valid_x = x[valid_indices]
                                    valid_values = values[valid_indices]

                                    # 决定绘制在哪个坐标轴上
                                    target_ax = self.indicator_ax
                                    if col.startswith('BB') or name in ['MA', 'EMA', 'SMA', 'WMA']:
                                        target_ax = self.price_ax

                                    target_ax.plot(valid_x, valid_values,
                                                   color=self._get_indicator_style(
                                                       f"{name}-{col}", i+j)['color'],
                                                   linewidth=0.7, alpha=0.85,
                                                   label=f"{name}-{col}" if len(result_df.columns) > 1 else name)
                        except Exception as e:
                            logger.error(f"TA-Lib指标 {name} 渲染失败: {str(e)}", exc_info=True)

                    elif group == 'custom' and formula:
                        try:
                            # 安全地用pandas.eval计算表达式
                            local_vars = {col: kdata[col]
                                          for col in kdata.columns}
                            arr = pd.eval(formula, local_dict=local_vars)
                            arr = arr.dropna()
                            self.price_ax.plot(x[-len(arr):], arr.values, color=style['color'],
                                               linewidth=style['linewidth'], alpha=style['alpha'], label=name)
                        except Exception as e:
                            logger.error(f"自定义公式渲染失败: {str(e)}")

                except Exception as e:
                    logger.error(f"渲染指标 {name} 失败: {str(e)}")
                    continue

        except Exception as e:
            if hasattr(self, 'error_occurred'):
                self.error_occurred.emit(f"渲染指标失败: {str(e)}")
            else:
                logger.info(f"渲染指标失败: {str(e)}")

    def _get_indicator_style(self, name: str, index: int = 0) -> Dict[str, Any]:
        """获取指标样式，颜色从theme_manager.get_theme_colors获取"""
        colors = self.theme_manager.get_theme_colors()
        indicator_colors = colors.get('indicator_colors', [
            '#fbc02d', '#ab47bc', '#1976d2', '#43a047', '#e53935', '#00bcd4', '#ff9800'])
        return {
            'color': indicator_colors[index % len(indicator_colors)],
            'linewidth': 0.7,
            'alpha': 0.85,
            'label': name
        }

    def add_indicator(self, indicator_data):
        """添加技术指标

        Args:
            indicator_data: 指标数据
        """
        try:
            if indicator_data is None:
                logger.warning("指标数据为空")
                return

            # 将添加指标任务加入队列
            self.queue_update(self._add_indicator_impl, indicator_data)

        except Exception as e:
            error_msg = f"添加指标失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def _add_indicator_impl(self, indicator_data, indicator_colors: list = None):
        try:
            self.current_indicator = indicator_data
            if hasattr(self, 'price_ax'):
                color_map = indicator_colors or [
                    '#fbc02d', '#ab47bc', '#1976d2', '#43a047', '#e53935', '#00bcd4', '#ff9800']
                for i, (name, series) in enumerate(indicator_data.items()):
                    self.price_ax.plot(
                        series.index, series.values,
                        color=color_map[i % len(color_map)],
                        linewidth=0.7, alpha=0.85, label=name, solid_capstyle='round'
                    )
                # 添加指标后更新图例
                lines = self.price_ax.get_lines()
                labels = [l.get_label() for l in lines]
                if lines and labels and any(l.get_visible() for l in lines):
                    self.price_ax.legend(
                        loc='upper left', fontsize=9, frameon=False)
                QTimer.singleShot(0, self.canvas.draw)
            logger.info(f"添加指标 {indicator_data.name} 完成")
        except Exception as e:
            error_msg = f"添加指标实现失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def clear_indicators(self):
        """清除所有指标"""
        try:
            self.current_indicator = None
            if hasattr(self, 'price_ax'):
                # 保留主图K线，清除其他线条
                # 只需注释或删除相关行即可
                # lines = self.price_ax.get_lines()
                # if len(lines) > 0:
                #     for line in lines[1:]:  # 跳过第一条K线
                #         line.remove()

                # 更新图例
                self.price_ax.legend(loc='upper left', fontsize=8)

                # 更新画布
                QTimer.singleShot(0, self.canvas.draw)

            logger.info("清除指标完成")
            self._optimize_display()  # 保证清除后也显示网格和刻度

        except Exception as e:
            error_msg = f"清除指标失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def on_indicator_changed(self, indicator: str):
        """处理指标变更事件

        Args:
            indicator: 指标名称
        """
        try:
            self.current_indicator = indicator
            # 发出指标变更信号
            self.indicator_changed.emit(indicator)

            # 如果有数据，重新绘制图表
            if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                self.update_chart({'kdata': self.current_kdata})

            logger.info(f"指标变更为: {indicator}")

        except Exception as e:
            error_msg = f"指标变更失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

    def on_indicator_selected(self, indicators: list):
        """处理指标选择事件"""
        try:
            self.active_indicators = indicators
            self._on_indicator_changed(indicators)
        except Exception as e:
            logger.error(f"指标选择处理失败: {str(e)}")

    def _on_indicator_changed(self, indicators):
        """内部指标变更处理"""
        self.active_indicators = indicators
        # 修复：传入当前K线数据，否则update_chart会因data=None直接返回
        if hasattr(self, 'current_kdata') and self.current_kdata is not None and not self.current_kdata.empty:
            self.update_chart({'kdata': self.current_kdata})
        else:
            logger.warning("_on_indicator_changed: 没有可用的K线数据，无法更新图表")

    def _on_calculation_progress(self, progress: int, message: str):
        """处理计算进度"""
        self.update_loading_progress(progress, message)

    def _on_calculation_complete(self, results: dict):
        """处理计算完成"""
        try:
            # 更新图表数据
            self._update_chart_with_results(results)

        except Exception as e:
            self.error_occurred.emit(f"更新图表数据失败: {str(e)}")

    def _on_calculation_error(self, error: str):
        """处理计算错误"""
        self.error_occurred.emit(error)
        self.close_loading_dialog()

    def _update_chart_with_results(self, results: dict):
        """使用计算结果更新图表"""
        try:
            if not hasattr(self, 'figure') or not hasattr(self, 'canvas'):
                return

            # 清除现有图表
            self.figure.clear()

            # 创建子图
            gs = self.figure.add_gridspec(
                3, 1, height_ratios=[3, 1, 1], hspace=0.05)
            price_ax = self.figure.add_subplot(gs[0])
            volume_ax = self.figure.add_subplot(gs[1], sharex=price_ax)
            indicator_ax = self.figure.add_subplot(gs[2], sharex=price_ax)

            # 使用优化的渲染器绘制图表
            self.renderer.render_candlesticks(
                price_ax, self.current_kdata, self._get_style())
            self.renderer.render_volume(
                volume_ax, self.current_kdata, self._get_style())

            # 绘制指标
            for name, data in results.items():
                if isinstance(data, tuple):
                    for i, series in enumerate(data):
                        self.renderer.render_line(
                            indicator_ax,
                            series,
                            self._get_indicator_style(name, i)
                        )
                else:
                    self.renderer.render_line(
                        indicator_ax,
                        data,
                        self._get_indicator_style(name)
                    )

            # 只保留subplots_adjust，不再设置tight_layout或constrained_layout
            self.figure.subplots_adjust(
                left=0.05, right=0.98, top=0.98, bottom=0.06, hspace=0.08)

            # 更新画布
            self.canvas.draw_idle()

            # 关闭加载对话框
            self.close_loading_dialog()

            # --- 十字光标X轴日期标签固定在X轴下方 ---
            # 十字光标将在update_chart方法结尾统一启用
            # --- 图例左对齐固定在主图X轴下方，支持点击隐藏/显示 ---
            lines = self.price_ax.get_lines()
            labels = [l.get_label() for l in lines]
            if lines and labels and any(l.get_visible() for l in lines):
                self.price_ax.legend(loc='upper left', fontsize=8)
            if not self.current_kdata.empty:
                step = max(1, len(self.current_kdata)//8)
                xticks = np.arange(0, len(self.current_kdata), step)
                xticklabels = [self._safe_format_date(
                    self.current_kdata.iloc[i], i, self.current_kdata) for i in xticks]
                self.indicator_ax.set_xticks(xticks)
                self.indicator_ax.set_xticklabels(
                    xticklabels, rotation=0, fontsize=7)

            # 绘制高亮K线
            try:
                if self.current_kdata is not None and hasattr(self, 'price_ax'):
                    for idx in self.highlighted_indices:
                        if 0 <= idx < len(self.current_kdata):
                            candle = self.current_kdata.iloc[idx]
                            self.price_ax.axvline(
                                idx, color='#ffd600', linestyle='--', linewidth=1.5, alpha=0.7, zorder=1000)
            except Exception as e:
                logger.error(f"高亮K线绘制失败: {str(e)}")

            # 左上角显示技术指标名称（下移到0.95）
            if hasattr(self, '_indicator_info_text') and self._indicator_info_text:
                try:
                    if self._indicator_info_text in self.price_ax.texts:
                        self._indicator_info_text.remove()
                except Exception as e:
                    if True:  # 使用Loguru日志
                        logger.warning(f"移除指标信息文本失败: {str(e)}")
                self._indicator_info_text = None
            indicator_names = []
            if hasattr(self, 'active_indicators') and self.active_indicators:
                for ind in self.active_indicators:
                    name = ind.get('name', '')
                    if name:
                        indicator_names.append(name)
            indicator_str = ', '.join(indicator_names)
            if indicator_str:
                # 获取主题颜色
                colors = self.theme_manager.get_theme_colors()
                text_color = colors.get('chart_text', '#222b45')
                bg_color = colors.get('chart_background', '#ffffff')

                self._indicator_info_text = self.price_ax.text(
                    0.01, 0.9, indicator_str,
                    transform=self.price_ax.transAxes,
                    va='top', ha='left',
                    fontsize=8,
                    color=text_color,
                    bbox=dict(facecolor=bg_color, alpha=0.7,
                              edgecolor='none', boxstyle='round,pad=0.2'),
                    zorder=200
                )

            # ✅ 性能优化：避免强制重新绑定，只在必要时启用
            # 重新启用十字光标（确保切换股票后十字光标正常工作）
            # 使用force_rebind=False，让enable_crosshair检查状态，避免重复绑定
            if hasattr(self, 'crosshair_enabled') and self.crosshair_enabled:
                self.enable_crosshair(force_rebind=False)  # 不强制重新绑定，检查状态

        except Exception as e:
            logger.error(f"更新图表失败: {str(e)}")
            self.close_loading_dialog()

    def draw_overview(self, ax, kdata):
        """绘制缩略图（mini map/overview），所有K线与主图对齐，节假日无数据自动跳过，X轴为等距序号。"""
        try:
            colors = self.theme_manager.get_theme_colors()
            k_up = colors.get('overview_k_up', colors.get('k_up', '#d32f2f'))
            k_down = colors.get('overview_k_down',
                                colors.get('k_down', '#388e3c'))
            bg = colors.get('overview_background', colors.get(
                'chart_background', '#fafdff'))
            ax.set_facecolor(bg)
            opens = kdata['open']
            closes = kdata['close']
            highs = kdata['high']
            lows = kdata['low']
            x = np.arange(len(kdata))

            # 绘制K线简化版
            for i in range(len(kdata)):
                color = k_up if closes.iloc[i] >= opens.iloc[i] else k_down
                ax.plot([x[i], x[i]], [lows.iloc[i], highs.iloc[i]],
                        color=color, linewidth=0.5)
                ax.plot([x[i], x[i]], [opens.iloc[i], closes.iloc[i]],
                        color=color, linewidth=1.5)

            ax.set_xlim(0, len(kdata))
            ax.set_ylim(lows.min() * 0.98, highs.max() * 1.02)
            ax.tick_params(axis='both', which='major', labelsize=6)

        except Exception as e:
            logger.error(f"绘制缩略图失败: {str(e)}")
