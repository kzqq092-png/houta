"""
图表渲染功能Mixin - 处理K线渲染、指标渲染、样式配置等功能
"""
import time
import numpy as np
import pandas as pd
from typing import Dict, Any
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt


class RenderingMixin:
    """图表渲染功能Mixin"""

    def update_chart(self, data: dict = None):
        """唯一K线渲染实现，X轴为等距序号，彻底消除节假日断层。"""
        try:
            if not data or 'kdata' not in data:
                return
            kdata = data['kdata']
            kdata = self._downsample_kdata(kdata)
            kdata = kdata.dropna(how='any')
            kdata = kdata.loc[~kdata.index.duplicated(keep='first')]
            self.current_kdata = kdata
            if not kdata.empty:
                self._ymin = float(kdata['low'].min())
                self._ymax = float(kdata['high'].max())
            else:
                self._ymin = 0
                self._ymax = 1
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.cla()
            style = self._get_chart_style()
            x = np.arange(len(kdata))  # 用等距序号做X轴
            self.renderer.render_candlesticks(self.price_ax, kdata, style, x=x)
            self.renderer.render_volume(self.volume_ax, kdata, style, x=x)
            # 修复：自动同步主窗口指标
            if hasattr(self, 'parentWidget') and callable(getattr(self, 'parentWidget', None)):
                main_window = self.parentWidget()
                while main_window and not hasattr(main_window, 'get_current_indicators'):
                    main_window = main_window.parentWidget() if hasattr(
                        main_window, 'parentWidget') else None
                if main_window and hasattr(main_window, 'get_current_indicators'):
                    self.active_indicators = main_window.get_current_indicators()
            self._render_indicators(kdata, x=x)
            # --- 新增：形态信号可视化 ---
            pattern_signals = data.get('pattern_signals', None)
            if pattern_signals:
                self.plot_patterns(pattern_signals)
            self._optimize_display()
            if not kdata.empty:
                for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                    ax.set_xlim(0, len(kdata)-1)
                self.price_ax.set_ylim(self._ymin, self._ymax)
                # 设置X轴刻度和标签（间隔显示，防止过密）
                step = max(1, len(kdata)//8)
                xticks = np.arange(0, len(kdata), step)
                xticklabels = [self._safe_format_date(kdata.iloc[i], i, kdata) for i in xticks]
                self.indicator_ax.set_xticks(xticks)
                # 修复：确保tick数量和label数量一致
                if len(xticks) == len(xticklabels):
                    self.indicator_ax.set_xticklabels(xticklabels, rotation=30, fontsize=8)
                else:
                    # 自动补齐或截断
                    min_len = min(len(xticks), len(xticklabels))
                    self.indicator_ax.set_xticks(xticks[:min_len])
                    self.indicator_ax.set_xticklabels(xticklabels[:min_len], rotation=30, fontsize=8)
            self.close_loading_dialog()
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.yaxis.set_tick_params(direction='in', pad=0)
                ax.yaxis.set_label_position('left')
                ax.tick_params(axis='y', direction='in', pad=0)
            self.crosshair_enabled = True
            self.enable_crosshair(force_rebind=True)
            # 左上角显示股票名称和代码
            if hasattr(self, '_stock_info_text') and self._stock_info_text:
                try:
                    if self._stock_info_text in self.price_ax.texts:
                        self._stock_info_text.remove()
                except Exception as e:
                    if hasattr(self, 'log_manager'):
                        self.log_manager.warning(f"移除股票信息文本失败: {str(e)}")
                self._stock_info_text = None
            stock_name = data.get('title') or getattr(
                self, 'current_stock', '')
            stock_code = data.get('stock_code') or getattr(
                self, 'current_stock', '')
            if stock_name and stock_code and stock_code not in stock_name:
                info_str = f"{stock_name} ({stock_code})"
            elif stock_name:
                info_str = stock_name
            elif stock_code:
                info_str = stock_code
            else:
                info_str = ''
            colors = self.theme_manager.get_theme_colors()
            text_color = colors.get('chart_text', '#222b45')
            bg_color = colors.get('chart_background', '#ffffff')
            self._stock_info_text = self.price_ax.text(
                0.01, 0.99, info_str,  # y坐标0.98
                transform=self.price_ax.transAxes,
                va='top', ha='left',
                fontsize=8,
                color=text_color,
                bbox=dict(facecolor=bg_color, alpha=0.7,
                          edgecolor='none', boxstyle='round,pad=0.2'),
                zorder=200
            )
            self.canvas.draw()
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                for label in (ax.get_xticklabels() + ax.get_yticklabels()):
                    label.set_fontsize(8)
                ax.title.set_fontsize(8)
                ax.xaxis.label.set_fontsize(8)
                ax.yaxis.label.set_fontsize(8)
            self._optimize_display()
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"更新图表失败: {str(e)}")
            self.show_no_data("渲染失败")

    def _render_indicators(self, kdata: pd.DataFrame, x=None):
        """渲染技术指标，所有指标与K线对齐，节假日无数据自动跳过，X轴为等距序号。"""
        try:
            indicators = getattr(self, 'active_indicators', [])
            if not indicators:
                return
            if x is None:
                x = np.arange(len(kdata))
            for i, indicator in enumerate(indicators):
                name = indicator.get('name', '')
                group = indicator.get('group', '')
                params = indicator.get('params', {})
                formula = indicator.get('formula', None)
                style = self._get_indicator_style(name, i)
                # 内置MA
                if name.startswith('MA') and (group == 'builtin' or name[2:].isdigit()):
                    period = int(params.get('n', name[2:]) or 5)
                    ma = kdata['close'].rolling(period).mean().dropna()
                    self.price_ax.plot(x[-len(ma):], ma.values, color=style['color'],
                                       linewidth=style['linewidth'], alpha=style['alpha'], label=name)
                elif name == 'MACD' and group == 'builtin':
                    macd, sig, hist = self._calculate_macd(kdata)
                    macd = macd.dropna()
                    sig = sig.dropna()
                    hist = hist.dropna()
                    self.indicator_ax.plot(x[-len(macd):], macd.values, color=self._get_indicator_style('MACD', i)['color'],
                                           linewidth=0.7, alpha=0.85, label='MACD')
                    self.indicator_ax.plot(x[-len(sig):], sig.values, color=self._get_indicator_style('MACD-Signal', i+1)['color'],
                                           linewidth=0.7, alpha=0.85, label='Signal')
                    if not hist.empty:
                        colors = ['red' if h >= 0 else 'green' for h in hist]
                        self.indicator_ax.bar(
                            x[-len(hist):], hist.values, color=colors, alpha=0.5)
                elif name == 'RSI' and group == 'builtin':
                    period = int(params.get('n', 14))
                    rsi = self._calculate_rsi(kdata, period).dropna()
                    self.indicator_ax.plot(x[-len(rsi):], rsi.values, color=style['color'],
                                           linewidth=style['linewidth'], alpha=style['alpha'], label='RSI')
                elif name == 'BOLL' and group == 'builtin':
                    n = int(params.get('n', 20))
                    p = float(params.get('p', 2))
                    mid, upper, lower = self._calculate_boll(kdata, n, p)
                    mid = mid.dropna()
                    upper = upper.dropna()
                    lower = lower.dropna()
                    self.price_ax.plot(x[-len(mid):], mid.values, color=self._get_indicator_style('BOLL-Mid', i)['color'],
                                       linewidth=0.5, alpha=0.85, label='BOLL-Mid')
                    self.price_ax.plot(x[-len(upper):], upper.values, color=self._get_indicator_style('BOLL-Upper', i+1)['color'],
                                       linewidth=0.7, alpha=0.85, label='BOLL-Upper')
                    self.price_ax.plot(x[-len(lower):], lower.values, color=self._get_indicator_style('BOLL-Lower', i+2)['color'],
                                       linewidth=0.5, alpha=0.85, label='BOLL-Lower')
                elif group == 'talib':
                    try:
                        import talib
                        # 如果name是中文名称，需要转换为英文名称
                        from indicators_algo import get_indicator_english_name
                        english_name = get_indicator_english_name(name)

                        func = getattr(talib, english_name)
                        # 只传递非空参数
                        func_params = {k: v for k,
                                       v in params.items() if v != ''}
                        # 传递收盘价等
                        result = func(
                            kdata['close'].values, **{k: float(v) if v else None for k, v in func_params.items()})
                        if isinstance(result, tuple):
                            for j, arr in enumerate(result):
                                arr = np.asarray(arr)
                                arr = arr[~np.isnan(arr)]
                                # 使用中文名称作为标签显示
                                display_name = name
                                self.indicator_ax.plot(x[-len(arr):], arr, color=self._get_indicator_style(display_name, i+j)['color'],
                                                       linewidth=0.7, alpha=0.85, label=f'{display_name}-{j}')
                        else:
                            arr = np.asarray(result)
                            arr = arr[~np.isnan(arr)]
                            display_name = name
                            self.indicator_ax.plot(x[-len(arr):], arr, color=style['color'],
                                                   linewidth=0.7, alpha=0.85, label=display_name)
                    except Exception as e:
                        self.error_occurred.emit(f"ta-lib指标渲染失败: {str(e)}")
                elif group == 'custom' and formula:
                    try:
                        # 安全地用pandas.eval计算表达式
                        local_vars = {col: kdata[col] for col in kdata.columns}
                        arr = pd.eval(formula, local_dict=local_vars)
                        arr = arr.dropna()
                        self.price_ax.plot(x[-len(arr):], arr.values, color=style['color'],
                                           linewidth=style['linewidth'], alpha=style['alpha'], label=name)
                    except Exception as e:
                        self.error_occurred.emit(f"自定义公式渲染失败: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"渲染指标失败: {str(e)}")

    def _get_chart_style(self) -> Dict[str, Any]:
        """获取图表样式，所有颜色从theme_manager.get_theme_colors获取"""
        try:
            colors = self.theme_manager.get_theme_colors()
            return {
                'up_color': colors.get('k_up', '#e74c3c'),
                'down_color': colors.get('k_down', '#27ae60'),
                'edge_color': colors.get('k_edge', '#2c3140'),
                'volume_up_color': colors.get('volume_up', '#e74c3c'),
                'volume_down_color': colors.get('volume_down', '#27ae60'),
                'volume_alpha': colors.get('volume_alpha', 0.5),
                'grid_color': colors.get('chart_grid', '#e0e0e0'),
                'background_color': colors.get('chart_background', '#ffffff'),
                'text_color': colors.get('chart_text', '#222b45'),
                'axis_color': colors.get('chart_grid', '#e0e0e0'),
                'label_color': colors.get('chart_text', '#222b45'),
                'border_color': colors.get('chart_grid', '#e0e0e0'),
            }
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"获取图表样式失败: {str(e)}")
            return {}

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

    def _optimize_rendering(self):
        """优化渲染性能"""
        try:
            # 启用双缓冲
            self.setAttribute(Qt.WA_OpaquePaintEvent)
            self.setAttribute(Qt.WA_NoSystemBackground)
            self.setAutoFillBackground(True)

            # 优化matplotlib设置
            plt.style.use('fast')
            self.figure.set_dpi(100)

            # 禁用不必要的特性
            plt.rcParams['path.simplify'] = True
            plt.rcParams['path.simplify_threshold'] = 1.0
            plt.rcParams['agg.path.chunksize'] = 20000

            # 优化布局（只保留subplots_adjust，去除set_tight_layout和set_constrained_layout）
            # self.figure.set_tight_layout(False)
            # self.figure.set_constrained_layout(True)

            # 设置固定边距
            self.figure.subplots_adjust(
                left=0.02, right=0.98,
                top=0.98, bottom=0.02,
                hspace=0.1
            )

        except Exception as e:
            if hasattr(self, 'error_occurred'):
                self.error_occurred.emit(f"优化渲染失败: {str(e)}")

    def _on_render_progress(self, progress: int, message: str):
        """处理渲染进度"""
        self.update_loading_progress(progress, message)

    def _on_render_complete(self):
        """处理渲染完成"""
        self.close_loading_dialog()

    def _on_render_error(self, error: str):
        """处理渲染错误"""
        if hasattr(self, 'error_occurred'):
            self.error_occurred.emit(error)
        self.close_loading_dialog()

    def clear_chart(self):
        """清空图表"""
        try:
            # 清空所有子图
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.cla()

            # 重置数据
            self.current_kdata = None
            self._ymin = 0
            self._ymax = 1

            # 清空十字光标
            if hasattr(self, '_crosshair_lines'):
                for line in self._crosshair_lines:
                    try:
                        line.remove()
                    except:
                        pass
                self._crosshair_lines = []

            if hasattr(self, '_crosshair_text') and self._crosshair_text:
                try:
                    self._crosshair_text.remove()
                except:
                    pass
                self._crosshair_text = None

            # 清空股票信息文本
            if hasattr(self, '_stock_info_text') and self._stock_info_text:
                try:
                    self._stock_info_text.remove()
                except:
                    pass
                self._stock_info_text = None

            # 重新绘制
            self.canvas.draw()

        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"清空图表失败: {str(e)}")

    def apply_theme(self):
        """应用主题"""
        try:
            if not hasattr(self, 'theme_manager') or not self.theme_manager:
                return

            colors = self.theme_manager.get_theme_colors()
            bg_color = colors.get('chart_background', '#ffffff')

            # 设置图表背景色
            self.figure.patch.set_facecolor(bg_color)

            # 设置各子图背景色
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.set_facecolor(bg_color)

                # 设置网格样式
                grid_color = colors.get('chart_grid', '#e0e0e0')
                ax.grid(True, color=grid_color, alpha=0.3, linewidth=0.5)

                # 设置刻度和标签颜色
                text_color = colors.get('chart_text', '#222b45')
                ax.tick_params(colors=text_color)
                ax.xaxis.label.set_color(text_color)
                ax.yaxis.label.set_color(text_color)

            # 重新绘制
            self.canvas.draw()

        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"应用主题失败: {str(e)}")

    def _init_figure_layout(self):
        """初始化图表布局"""
        try:
            # 创建子图
            self.price_ax = self.figure.add_subplot(211)  # 价格图
            self.volume_ax = self.figure.add_subplot(212)  # 成交量图
            self.indicator_ax = self.volume_ax  # 指标图与成交量图共用

            # 设置子图间距
            self.figure.subplots_adjust(
                left=0.02, right=0.98,
                top=0.98, bottom=0.02,
                hspace=0.1
            )

            # 应用主题
            self.apply_theme()

        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"初始化图表布局失败: {str(e)}")

    def draw_overview(self, ax, kdata):
        """绘制概览图"""
        try:
            if kdata is None or kdata.empty:
                return

            # 简化的K线图
            x = np.arange(len(kdata))
            ax.plot(x, kdata['close'], color='blue', linewidth=1, alpha=0.7)

            # 设置样式
            ax.set_xlim(0, len(kdata)-1)
            ax.set_ylim(kdata['low'].min(), kdata['high'].max())
            ax.grid(True, alpha=0.3)

        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"绘制概览图失败: {str(e)}")

    def show_no_data(self, message: str = "无数据"):
        """无数据时清空图表并显示提示信息，所有字体统一为8号，健壮处理异常，始终显示网格和XY轴刻度"""
        try:
            if hasattr(self, 'figure'):
                self.figure.clear()
                # 重新创建子图，防止后续渲染异常
                self.price_ax = self.figure.add_subplot(211)
                self.volume_ax = self.figure.add_subplot(212)
                self.indicator_ax = self.volume_ax
                # 清空其他内容
                self.price_ax.cla()
                self.volume_ax.cla()
                # 在主图中央显示提示文本
                self.price_ax.text(0.5, 0.5, message,
                                   transform=self.price_ax.transAxes,
                                   fontsize=16, color='#888',
                                   ha='center', va='center', alpha=0.85)
                # 设置默认XY轴刻度和网格
                self.price_ax.set_xlim(0, 1)
                self.price_ax.set_ylim(0, 1)
                self.volume_ax.set_xlim(0, 1)
                self.volume_ax.set_ylim(0, 1)
                self._optimize_display()  # 保证无数据时也显示网格和刻度

                # 使用安全的布局调整方式
                from utils.matplotlib_utils import safe_figure_layout
                safe_figure_layout(self.figure)

                self.canvas.draw()

                # 统一字体大小（全部设为8号）
                for ax in [self.price_ax, self.volume_ax]:
                    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
                        label.set_fontsize(8)
                    ax.title.set_fontsize(8)
                    ax.xaxis.label.set_fontsize(8)
                    ax.yaxis.label.set_fontsize(8)
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"显示无数据提示失败: {str(e)}")

    def _get_style(self) -> Dict[str, Any]:
        """获取样式配置"""
        return self._get_chart_style()

    def on_period_changed(self, period: str):
        """处理周期变更"""
        try:
            # 这里可以根据周期调整显示样式
            if hasattr(self, 'current_period'):
                self.current_period = period

            # 发射周期变更信号
            if hasattr(self, 'period_changed'):
                self.period_changed.emit(period)

            # 刷新图表
            if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                self.update_chart({'kdata': self.current_kdata})

        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"处理周期变更失败: {str(e)}")

    def on_indicator_changed(self, indicator: str):
        """处理指标变更"""
        try:
            # 发射指标变更信号
            if hasattr(self, 'indicator_changed'):
                self.indicator_changed.emit(indicator)

            # 刷新图表
            if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                self.update_chart({'kdata': self.current_kdata})

        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"处理指标变更失败: {str(e)}")
