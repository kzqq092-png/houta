"""
信号处理Mixin - 处理交易信号的绘制、高亮和管理
"""
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
import pandas as pd
import matplotlib.patches as mpatches
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer


class SignalMixin:
    """信号处理Mixin类 - 负责交易信号的绘制、高亮和管理"""

    def plot_signals(self, signals, visible_range=None, signal_filter=None):
        """绘制信号，支持密度自适应、聚合展示、气泡提示"""
        try:
            if not hasattr(self, 'main_ax') or not self.main_ax:
                return

            # 清除旧信号
            for artist in getattr(self, '_signal_artists', []):
                try:
                    artist.remove()
                except:
                    pass
            self._signal_artists = []

            if not signals:
                self.canvas.draw()
                return

            # 获取当前可见区间
            if visible_range is None:
                visible_range = self.get_visible_range()

            # 筛选可见区间内的信号
            visible_signals = []
            if visible_range:
                start_idx, end_idx = visible_range
                for signal in signals:
                    sig_idx = signal.get('index', 0)
                    if start_idx <= sig_idx <= end_idx:
                        visible_signals.append(signal)
            else:
                visible_signals = signals

            # 信号密度自适应
            max_signals_per_screen = 20  # 每屏最多显示信号数
            if len(visible_signals) > max_signals_per_screen:
                # 聚合展示：仅显示重要信号，其余用统计标记
                important_signals = self._select_important_signals(
                    visible_signals, max_signals_per_screen)
                aggregated_count = len(visible_signals) - \
                    len(important_signals)
                visible_signals = important_signals

                # 在角落显示聚合信息
                if aggregated_count > 0:
                    agg_text = self.main_ax.text(0.02, 0.98, f"+ {aggregated_count} 个信号",
                                                 transform=self.main_ax.transAxes,
                                                 bbox=dict(
                                                     boxstyle="round,pad=0.3", facecolor="orange", alpha=0.7),
                                                 fontsize=9, verticalalignment='top')
                    self._signal_artists.append(agg_text)

            # 绘制可见信号
            for signal in visible_signals:
                self._plot_single_signal(signal)

            # 启用气泡提示
            self._enable_signal_tooltips(visible_signals)

            self.canvas.draw()

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"绘制信号失败: {str(e)}")

    def _select_important_signals(self, signals, max_count):
        """选择重要信号，基于置信度、类型优先级等"""
        # 按置信度排序，优先显示高置信度信号
        sorted_signals = sorted(signals, key=lambda x: x.get(
            'confidence', 0), reverse=True)
        return sorted_signals[:max_count]

    def _plot_single_signal(self, signal):
        """绘制单个信号标记"""
        try:
            idx = signal.get('index', 0)
            signal_type = signal.get('type', 'unknown')
            confidence = signal.get('confidence', 0)
            price = signal.get('price', 0)

            # 根据信号类型设置颜色和标记
            if signal_type == 'double_top':
                color = 'red'
                marker = 'v'
                label = 'DT'
            elif signal_type == 'double_bottom':
                color = 'green'
                marker = '^'
                label = 'DB'
            else:
                color = 'blue'
                marker = 'o'
                label = signal_type[:2].upper()

            # 信号标记
            scatter = self.main_ax.scatter(idx, price, c=color, marker=marker, s=80,
                                           alpha=0.8, edgecolors='white', linewidth=1)
            self._signal_artists.append(scatter)

            # 简洁文字标注（仅高置信度显示）
            if confidence > 0.7:
                text = self.main_ax.text(idx, price * 1.01, label,
                                         fontsize=8, ha='center', va='bottom',
                                         color=color, fontweight='bold',
                                         bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
                self._signal_artists.append(text)

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"绘制单个信号失败: {str(e)}")

    def _enable_signal_tooltips(self, signals):
        """启用信号气泡提示 - 通过标志位与十字光标协调工作"""
        try:
            # 创建信号索引映射
            signal_map = {signal.get('index', 0): signal for signal in signals}

            # 存储信号映射供十字光标使用，而不是独立绑定事件
            self._signal_tooltip_map = signal_map
            self._signal_tooltips_enabled = True

            # 注意：不再独立绑定motion_notify_event，而是让十字光标处理器处理信号提示
            # 这样避免了事件冲突问题

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"启用信号提示失败: {str(e)}")

    def get_signal_tooltip_at_index(self, idx: int) -> str:
        """获取指定索引处的信号提示信息"""
        try:
            if (not hasattr(self, '_signal_tooltips_enabled') or
                not self._signal_tooltips_enabled or
                    not hasattr(self, '_signal_tooltip_map')):
                return ""

            if idx in self._signal_tooltip_map:
                signal = self._signal_tooltip_map[idx]
                tooltip_text = f"信号类型: {signal.get('type', 'unknown')}\n"
                tooltip_text += f"置信度: {signal.get('confidence', 0):.3f}\n"
                tooltip_text += f"价格: {signal.get('price', 0):.3f}\n"
                tooltip_text += f"时间: {signal.get('datetime', '')}"
                return tooltip_text
            return ""
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"获取信号提示失败: {str(e)}")
            return ""

    def disable_signal_tooltips(self):
        """禁用信号提示"""
        try:
            self._signal_tooltips_enabled = False
            self._signal_tooltip_map = {}

            # 清除现有提示
            for artist in getattr(self, '_tooltip_artists', []):
                try:
                    artist.remove()
                except:
                    pass
            self._tooltip_artists = []

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"禁用信号提示失败: {str(e)}")

    def highlight_signals(self, signals):
        """高亮指定信号"""
        try:
            # 清除旧高亮
            self.clear_signal_highlight()

            if not signals or not hasattr(self, 'main_ax') or not self.main_ax:
                return

            # 绘制高亮效果
            highlight_artists = []
            for signal in signals:
                idx = signal.get('index', 0)
                price = signal.get('price', 0)

                # 高亮圆圈
                highlight_circle = self.main_ax.scatter(idx, price, s=200,
                                                        facecolors='none', edgecolors='yellow',
                                                        linewidths=3, alpha=0.8, zorder=30)
                highlight_artists.append(highlight_circle)

                # 高亮文字
                highlight_text = self.main_ax.text(idx, price * 1.03, f"选中: {signal.get('type', '')}",
                                                   fontsize=10, ha='center', va='bottom',
                                                   color='yellow', fontweight='bold',
                                                   bbox=dict(boxstyle="round,pad=0.3", facecolor='black', alpha=0.7))
                highlight_artists.append(highlight_text)

            # 保存高亮对象用于清除
            self._highlight_artists = highlight_artists

            # 自动调整视图范围至高亮信号
            if len(signals) == 1:
                signal = signals[0]
                idx = signal.get('index', 0)
                current_xlim = self.main_ax.get_xlim()
                window_size = current_xlim[1] - current_xlim[0]
                new_center = idx
                self.main_ax.set_xlim(
                    new_center - window_size/2, new_center + window_size/2)

            self.canvas.draw()

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"高亮信号失败: {str(e)}")

    def clear_signal_highlight(self):
        """清除信号高亮"""
        try:
            # 移除高亮对象
            for artist in getattr(self, '_highlight_artists', []):
                try:
                    artist.remove()
                except:
                    pass
            self._highlight_artists = []

            # 清除气泡提示
            for artist in getattr(self, '_tooltip_artists', []):
                try:
                    artist.remove()
                except:
                    pass
            self._tooltip_artists = []

            self.canvas.draw()

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"清除信号高亮失败: {str(e)}")

    def plot_patterns(self, pattern_signals: list, highlight_index: int = None):
        """
        专业化形态信号显示：使用彩色箭头标记，默认隐藏浮窗，集成到十字光标显示
        Args:
            pattern_signals: List[dict]，每个dict至少包含 'index', 'pattern', 'signal', 'confidence' 等字段
        """
        if not hasattr(self, 'price_ax') or self.current_kdata is None or not pattern_signals:
            return

        ax = self.price_ax
        kdata = self.current_kdata
        x = np.arange(len(kdata))

        # 专业化颜色配置 - 参考同花顺、东方财富等软件
        signal_colors = {
            'buy': '#FF4444',      # 买入信号 - 红色箭头向上
            'sell': '#00AA00',     # 卖出信号 - 绿色箭头向下
            'neutral': '#FFB000'   # 中性信号 - 橙色圆点
        }

        # 置信度透明度映射
        def get_alpha(confidence):
            if confidence >= 0.8:
                return 1.0
            elif confidence >= 0.6:
                return 0.8
            else:
                return 0.6

        # 存储形态信息供十字光标使用
        self._pattern_info = {}

        # 统计有效和无效的形态信号
        valid_patterns = 0
        invalid_patterns = 0

        for pat in pattern_signals:
            idx = pat.get('index')
            if idx is None:
                invalid_patterns += 1
                continue

            # 修复：严格的索引边界检查
            if not isinstance(idx, (int, float)) or idx < 0 or idx >= len(kdata):
                if hasattr(self, 'log_manager') and self.log_manager:
                    self.log_manager.warning(
                        f"形态信号索引超出范围: {idx}, 数据长度: {len(kdata)}")
                invalid_patterns += 1
                continue

            # 确保索引为整数
            idx = int(idx)
            valid_patterns += 1

            pattern_name = pat.get(
                'pattern_name', pat.get('pattern', 'Unknown'))
            signal = pat.get('signal', 'neutral')
            confidence = pat.get('confidence', 0)
            price = kdata.iloc[idx]['high'] if signal == 'buy' else kdata.iloc[idx]['low']

            # 获取颜色和透明度
            color = signal_colors.get(signal, signal_colors['neutral'])
            alpha = get_alpha(confidence)

            # 绘制专业箭头标记
            if signal == 'buy':
                # 买入信号：空心向上三角，位于K线下方
                arrow_y = kdata.iloc[idx]['low'] - \
                    (kdata.iloc[idx]['high'] - kdata.iloc[idx]['low']) * 0.15
                ax.scatter(idx, arrow_y, marker='^', s=80, facecolors='none',
                           edgecolors=color, linewidths=0.8, alpha=alpha, zorder=100)
            elif signal == 'sell':
                # 卖出信号：空心向下三角，位于K线上方
                arrow_y = kdata.iloc[idx]['high'] + \
                    (kdata.iloc[idx]['high'] - kdata.iloc[idx]['low']) * 0.15
                ax.scatter(idx, arrow_y, marker='v', s=80, facecolors='none',
                           edgecolors=color, linewidths=0.8, alpha=alpha, zorder=100)
            else:
                # 中性信号：空心圆点，位于收盘价位置
                ax.scatter(idx, kdata.iloc[idx]['close'], marker='o', s=60, facecolors='none',
                           edgecolors=color, linewidths=0.8, alpha=alpha, zorder=100)

            # 存储形态信息供十字光标显示
            self._pattern_info[idx] = {
                'pattern_name': pattern_name,
                'signal': signal,
                'confidence': confidence,
                'signal_cn': {'buy': '买入', 'sell': '卖出', 'neutral': '中性'}.get(signal, signal),
                'price': kdata.iloc[idx]['close'],
                'datetime': kdata.index[idx].strftime('%Y-%m-%d') if hasattr(kdata.index[idx], 'strftime') else str(kdata.index[idx])
            }

        # 记录绘制结果
        if hasattr(self, 'log_manager') and self.log_manager:
            self.log_manager.info(
                f"形态信号绘制完成: 有效 {valid_patterns} 个, 无效 {invalid_patterns} 个")

        # 高亮特定形态（如果指定）
        if highlight_index is not None and highlight_index in self._pattern_info:
            # 添加高亮背景
            ax.axvspan(highlight_index-0.4, highlight_index+0.4,
                       color='yellow', alpha=0.2, zorder=50)

        self.canvas.draw_idle()
        self._current_pattern_signals = pattern_signals
        self._highlight_index = highlight_index

    def highlight_pattern(self, idx: int):
        """外部调用高亮指定K线索引的形态"""
        if hasattr(self, '_current_pattern_signals'):
            self.plot_patterns(self._current_pattern_signals,
                               highlight_index=idx)

    def mark_highlight_candle(self, event):
        # 标记鼠标所在K线为高亮
        try:
            if self.current_kdata is None or self.current_kdata.empty:
                return
            # 计算鼠标在axes中的xdata
            pos = self.price_ax.transData.inverted().transform((event.x(), event.y()))
            x_idx = int(round(pos[0]))
            if 0 <= x_idx < len(self.current_kdata):
                self.highlighted_indices.add(x_idx)
                self.refresh()
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"标记高亮K线失败: {str(e)}")

    def clear_highlighted_candles(self):
        """清除高亮K线"""
        self.highlighted_indices.clear()
        self.refresh()

    def toggle_replay(self):
        # 历史回看/回放动画
        try:
            if self._replay_timer and self._replay_timer.isActive():
                self._replay_timer.stop()
                self._replay_timer = None
                self._replay_index = None
                return
            if self.current_kdata is None or self.current_kdata.empty:
                return
            self._replay_index = 10  # 从第10根K线开始
            self._replay_timer = QTimer(self)
            self._replay_timer.timeout.connect(self._replay_step)
            self._replay_timer.start(100)
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"历史回看/回放启动失败: {str(e)}")

    def _replay_step(self):
        """回放步骤"""
        if self._replay_index is None or self.current_kdata is None:
            return
        if self._replay_index >= len(self.current_kdata):
            self._replay_timer.stop()
            self._replay_index = None
            return
        # 只显示前self._replay_index根K线
        self.update_chart(
            {'kdata': self.current_kdata.iloc[:self._replay_index]})
        self._replay_index += 1

    def get_visible_range(self):
        # 获取当前主图可见区间的K线索引范围（伪代码，需结合xlim等）
        try:
            xlim = self.indicator_ax.get_xlim()
            return int(xlim[0]), int(xlim[1])
        except Exception:
            return None
