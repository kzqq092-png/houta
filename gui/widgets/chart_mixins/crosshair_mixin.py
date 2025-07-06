"""
图表控件十字光标功能Mixin

该模块包含ChartWidget的十字光标相关功能，包括：
- 十字光标启用/禁用
- 光标信息显示
- 光标线条更新
- 轴标签更新
- 光标元素清理
"""

import time
from typing import Tuple, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd


class CrosshairMixin:
    """十字光标功能Mixin

    包含ChartWidget的十字光标显示、信息提示、线条更新等功能
    """

    def __init__(self):
        """初始化十字光标相关变量"""
        super().__init__()
        # 十字光标相关变量
        self._crosshair_lines: Dict[str, object] = {}  # 改为字典管理，键为 'price_v', 'volume_v', 'indicator_v', 'price_h'
        self._crosshair_text = None
        self._crosshair_xtext = None
        self._crosshair_ytext = None
        self._last_crosshair_update_time = 0
        self._crosshair_event_id = None  # 存储事件连接ID，避免重复绑定

    def enable_crosshair(self, force_rebind=False):
        """启用十字光标功能"""
        try:
            if not self.crosshair_enabled:
                return

            # 清除现有的十字光标元素
            self._clear_crosshair_elements()

            # 创建统一的鼠标移动处理器（避免重复绑定）
            if self._crosshair_event_id is None or force_rebind:
                self._create_unified_crosshair_handler()

            # 限制X轴范围
            self._limit_xlim()

        except Exception as e:
            self.log_manager.error(f"启用十字光标失败: {str(e)}")

    def _limit_xlim(self):
        """限制X轴范围，防止越界"""
        try:
            if self.current_kdata is not None and len(self.current_kdata) > 0:
                max_x = len(self.current_kdata) - 1
                for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                    if ax is not None:
                        current_xlim = ax.get_xlim()
                        new_xlim = (max(0, current_xlim[0]), min(max_x, current_xlim[1]))
                        ax.set_xlim(new_xlim)
        except Exception as e:
            self.log_manager.error(f"限制X轴范围失败: {str(e)}")

    def _create_crosshair_info_text(self, row, idx: int, kdata) -> Tuple[str, str]:
        """创建十字光标信息文本 - 集成信号提示"""
        try:
            # 获取日期字符串
            date_str = self._safe_format_date(row, idx, kdata)

            # 计算涨跌幅
            if idx > 0:
                prev_close = kdata.iloc[idx-1]['close']
                change = row['close'] - prev_close
                change_pct = (change / prev_close) * 100
                if change > 0:
                    change_symbol = "+"
                    change_str = f"↑+{change:.3f} (+{change_pct:.2f}%)"
                elif change < 0:
                    change_symbol = "-"
                    change_str = f"↓{change:.3f} ({change_pct:.2f}%)"
                else:
                    change_symbol = ""
                    change_str = "0.000 (0.00%)"
            else:
                change_symbol = ""
                change_str = "0.000 (0.00%)"

            # 构建基础信息文本
            info = (
                f"日期: {date_str}\n"
                f"开盘: {row['open']:.3f}  收盘: {row['close']:.3f}\n"
                f"最高: {row['high']:.3f}  最低: {row['low']:.3f}\n"
                f"涨跌: {change_str}\n"
                f"成交量: {row['volume']:.0f}"
            )

            # 检查是否有信号提示信息需要添加
            signal_info = ""
            if hasattr(self, 'get_signal_tooltip_at_index'):
                signal_info = self.get_signal_tooltip_at_index(idx)
                if signal_info:
                    info += f"\n\n--- 交易信号 ---\n{signal_info}"

            # 检查是否有形态识别信息需要添加
            pattern_info = ""
            if hasattr(self, '_pattern_info') and idx in self._pattern_info:
                pattern_data = self._pattern_info[idx]
                pattern_info = f"\n\n--- 形态识别 ---\n"
                pattern_info += f"形态: {pattern_data.get('pattern_name', 'Unknown')}\n"
                pattern_info += f"信号: {pattern_data.get('signal', 'neutral')}\n"
                pattern_info += f"置信度: {pattern_data.get('confidence', 0):.3f}"
                info += pattern_info

            # 获取文本颜色
            text_color = self._get_change_color(change_symbol)

            return info, text_color

        except Exception as e:
            self.log_manager.error(f"创建十字光标信息失败: {str(e)}")
            return "信息加载失败", self._get_default_text_color()

    def _get_change_color(self, change_symbol: str) -> str:
        """根据涨跌符号获取颜色"""
        try:
            colors = self.theme_manager.get_theme_colors()
            if change_symbol == "-":
                return colors.get('up_color', '#00ff00')
            elif change_symbol == "+":
                return colors.get('down_color', '#ff0000')
            else:
                return colors.get('chart_text', '#ffffff')
        except Exception:
            # 默认颜色
            if change_symbol == "-":
                return '#00ff00'
            elif change_symbol == "+":
                return '#ff0000'
            else:
                return '#ffffff'

    def _get_default_text_color(self) -> str:
        """获取默认文本颜色"""
        try:
            colors = self.theme_manager.get_theme_colors()
            return colors.get('chart_text', '#ffffff')
        except Exception:
            return '#ffffff'

    def _get_primary_color(self) -> str:
        """获取主题色"""
        try:
            colors = self.theme_manager.get_theme_colors()
            return colors.get('primary', '#1976d2')
        except Exception:
            return '#1976d2'

    def _update_crosshair_lines(self, x_val: float, y_val: float, primary_color: str):
        """更新十字光标线条 - 修复多条线问题"""
        try:
            # 定义需要的线条及其对应的子图
            line_configs = [
                ('price_v', self.price_ax, 'vertical'),
                ('volume_v', self.volume_ax, 'vertical'),
                ('indicator_v', self.indicator_ax, 'vertical'),
                ('price_h', self.price_ax, 'horizontal')
            ]

            for line_key, ax, line_type in line_configs:
                if ax is None:
                    continue

                # 如果线条不存在，创建新的
                if line_key not in self._crosshair_lines:
                    if line_type == 'vertical':
                        line = ax.axvline(x_val, color=primary_color, lw=1.2,
                                          ls='--', alpha=0.55, visible=True, zorder=100)
                    else:  # horizontal
                        line = ax.axhline(y_val, color=primary_color, lw=1.2,
                                          ls='--', alpha=0.55, visible=True, zorder=100)
                    self._crosshair_lines[line_key] = line
                else:
                    # 更新现有线条
                    line = self._crosshair_lines[line_key]
                    if line_type == 'vertical':
                        line.set_xdata([x_val, x_val])
                    else:  # horizontal - 只在主图显示横线
                        if line_key == 'price_h':
                            line.set_ydata([y_val, y_val])
                    line.set_color(primary_color)
                    line.set_visible(True)

        except Exception as e:
            self.log_manager.error(f"更新十字光标线条失败: {str(e)}")

    def _update_crosshair_text(self, event, x_val: float, y_val: float, info: str, text_color: str):
        """更新十字光标信息文本 - 修复悬浮框位置问题，让其跟随鼠标"""
        try:
            # 计算悬浮框位置 - 跟随鼠标但避免超出边界
            ax = self.price_ax
            if ax is None:
                return

            # 获取坐标轴范围
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()

            # 计算相对位置（0-1范围）
            x_rel = (x_val - xlim[0]) / (xlim[1] - xlim[0])
            y_rel = (y_val - ylim[0]) / (ylim[1] - ylim[0])

            # 动态调整悬浮框位置，避免超出边界
            if x_rel > 0.7:  # 鼠标在右侧，悬浮框显示在左侧
                text_x = x_rel - 0.05
                ha = 'right'
            else:  # 鼠标在左侧，悬浮框显示在右侧
                text_x = x_rel + 0.05
                ha = 'left'

            if y_rel > 0.7:  # 鼠标在上方，悬浮框显示在下方
                text_y = y_rel - 0.05
                va = 'top'
            else:  # 鼠标在下方，悬浮框显示在上方
                text_y = y_rel + 0.05
                va = 'bottom'

            # 确保位置在有效范围内
            text_x = max(0.02, min(0.98, text_x))
            text_y = max(0.02, min(0.98, text_y))

            if self._crosshair_text is None:
                # 创建信息文本框
                self._crosshair_text = ax.text(
                    text_x, text_y, info,
                    transform=ax.transAxes,
                    va=va, ha=ha,
                    fontsize=8.5,
                    color=text_color,  # #585d58
                    bbox=dict(facecolor='#fff', alpha=0.5, edgecolor='#1976d2',
                              boxstyle='round,pad=0.5', linewidth=0.8),
                    zorder=200
                )
            else:
                # 更新现有文本
                self._crosshair_text.set_position((text_x, text_y))
                self._crosshair_text.set_text(info)
                self._crosshair_text.set_color(text_color)
                self._crosshair_text.set_ha(ha)
                self._crosshair_text.set_va(va)
                self._crosshair_text.set_visible(True)

        except Exception as e:
            self.log_manager.error(f"更新十字光标文本失败: {str(e)}")

    def _update_crosshair_axis_labels(self, row, idx: int, kdata, x_val: float, y_val: float, primary_color: str):
        """更新十字光标轴标签"""
        try:
            # X轴标签（日期）
            date_str = self._safe_format_date(row, idx, kdata)
            if self.indicator_ax is not None:
                if self._crosshair_xtext is None:
                    self._crosshair_xtext = self.indicator_ax.text(
                        x_val, +1, date_str,
                        transform=self.indicator_ax.get_xaxis_transform(),
                        ha='center', va='top',
                        fontsize=8,
                        color=primary_color,
                        bbox=dict(facecolor='#fff', alpha=0.8,
                                  edgecolor=primary_color, boxstyle='round,pad=0.2'),
                        zorder=200
                    )
                else:
                    self._crosshair_xtext.set_position((x_val, +1))
                    self._crosshair_xtext.set_text(date_str)
                    self._crosshair_xtext.set_color(primary_color)
                    self._crosshair_xtext.set_visible(True)

            # Y轴标签（价格）
            if self.price_ax is not None:
                price_str = f"{y_val:.3f}"
                if self._crosshair_ytext is None:
                    self._crosshair_ytext = self.price_ax.text(
                        +0.03, y_val, price_str,
                        transform=self.price_ax.get_yaxis_transform(),
                        ha='right', va='center',
                        fontsize=8,
                        color=primary_color,
                        bbox=dict(facecolor='#fff', alpha=0.8,
                                  edgecolor=primary_color, boxstyle='round,pad=0.2'),
                        zorder=200
                    )
                else:
                    self._crosshair_ytext.set_position((+0.03, y_val))
                    self._crosshair_ytext.set_text(price_str)
                    self._crosshair_ytext.set_color(primary_color)
                    self._crosshair_ytext.set_visible(True)

        except Exception as e:
            self.log_manager.error(f"更新十字光标轴标签失败: {str(e)}")

    def _hide_crosshair_elements(self):
        """隐藏十字光标元素"""
        try:
            # 隐藏线条
            for line in self._crosshair_lines.values():
                if line is not None:
                    line.set_visible(False)

            # 隐藏文本
            if self._crosshair_text:
                self._crosshair_text.set_visible(False)
            if self._crosshair_xtext:
                self._crosshair_xtext.set_visible(False)
            if self._crosshair_ytext:
                self._crosshair_ytext.set_visible(False)

        except Exception as e:
            self.log_manager.error(f"隐藏十字光标元素失败: {str(e)}")

    def _clear_crosshair_elements(self):
        """清除十字光标元素"""
        try:
            # 清除线条
            for line in self._crosshair_lines.values():
                if line is not None:
                    try:
                        line.remove()
                    except Exception:
                        pass
            self._crosshair_lines.clear()

            # 清除文本
            if self._crosshair_text:
                try:
                    self._crosshair_text.remove()
                except Exception:
                    pass
                self._crosshair_text = None

            if self._crosshair_xtext:
                try:
                    self._crosshair_xtext.remove()
                except Exception:
                    pass
                self._crosshair_xtext = None

            if self._crosshair_ytext:
                try:
                    self._crosshair_ytext.remove()
                except Exception:
                    pass
                self._crosshair_ytext = None

        except Exception as e:
            self.log_manager.error(f"清除十字光标元素失败: {str(e)}")

    def _create_unified_crosshair_handler(self):
        """创建统一的十字光标处理器 - 避免重复绑定"""
        try:
            def on_mouse_move(event):
                # 限制更新频率
                now = int(time.time() * 1000)
                if hasattr(self, '_last_crosshair_update_time') and now - self._last_crosshair_update_time < 16:
                    return
                self._last_crosshair_update_time = now

                # 获取主题色
                primary_color = self._get_primary_color()

                # 检查事件有效性 - 只处理在图表区域内的事件
                if (not event.inaxes or
                    event.inaxes not in [self.price_ax, self.volume_ax, self.indicator_ax] or
                    self.current_kdata is None or
                    len(self.current_kdata) == 0 or
                        event.xdata is None):
                    self._hide_crosshair_elements()
                    self.canvas.draw_idle()
                    return

                # 获取数据
                kdata = self.current_kdata
                idx = int(max(0, min(len(kdata)-1, round(event.xdata))))
                row = kdata.iloc[idx]
                x_val = idx
                y_val = row['close']

                # 更新十字光标线条
                self._update_crosshair_lines(x_val, y_val, primary_color)

                # 创建信息文本
                info, text_color = self._create_crosshair_info_text(row, idx, kdata)

                # 更新信息文本
                self._update_crosshair_text(event, x_val, y_val, info, text_color)

                # 更新轴标签
                self._update_crosshair_axis_labels(row, idx, kdata, x_val, y_val, primary_color)

                # 刷新画布
                self.canvas.draw_idle()

            # 断开之前的连接（如果存在）
            if self._crosshair_event_id is not None:
                try:
                    self.canvas.mpl_disconnect(self._crosshair_event_id)
                except Exception:
                    pass

            # 绑定新的事件处理器
            self._crosshair_event_id = self.canvas.mpl_connect('motion_notify_event', on_mouse_move)

        except Exception as e:
            self.log_manager.error(f"创建十字光标处理器失败: {str(e)}")

    def disable_crosshair(self):
        """禁用十字光标功能"""
        try:
            # 清除所有十字光标元素
            self._clear_crosshair_elements()

            # 断开事件连接
            if self._crosshair_event_id is not None:
                try:
                    self.canvas.mpl_disconnect(self._crosshair_event_id)
                except Exception:
                    pass
                self._crosshair_event_id = None

            # 刷新画布
            if hasattr(self, 'canvas'):
                self.canvas.draw_idle()

        except Exception as e:
            self.log_manager.error(f"禁用十字光标失败: {str(e)}")
