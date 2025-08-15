"""
交互功能Mixin - 处理用户交互、拖拽、右键菜单、高亮等功能
"""
import traceback
from typing import Tuple
import numpy as np
import matplotlib.patches as mpatches
from PyQt5.QtWidgets import QMenu, QFileDialog, QMessageBox, QApplication
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
import io


class InteractionMixin:
    """交互功能Mixin"""

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """处理拖拽释放事件"""
        try:
            code, raw_text = self.parse_dragged_stock_code(event)
            if not code:
                self.show_no_data("拖拽内容无效")
                return
            data_manager = getattr(self, 'data_manager', None)
            if not data_manager:
                parent = self.parent()
                p = parent
                while p is not None:
                    if hasattr(p, 'data_manager') and p.data_manager:
                        data_manager = p.data_manager
                        break
                    p = p.parent()

            # 🚀 优先使用TET模式（AssetService）
            kdata = None
            try:
                from core.containers import get_service_container
                from core.services import AssetService
                from core.plugin_types import AssetType

                service_container = get_service_container()
                asset_service = service_container.resolve(AssetService)

                if asset_service:
                    kdata = asset_service.get_historical_data(
                        symbol=code,
                        asset_type=AssetType.STOCK,
                        period='D'
                    )
                    if kdata is not None and not kdata.empty:
                        self.update_chart({'kdata': kdata, 'stock_code': code})
                        return
            except Exception as e:
                if hasattr(self, 'log_manager') and self.log_manager:
                    self.log_manager.warning(f"TET模式拖拽数据获取失败: {e}")

            # 📊 降级到传统data_manager
            if data_manager:
                kdata = data_manager.get_kdata(code)
                if kdata is not None and not kdata.empty:
                    self.update_chart({'kdata': kdata, 'stock_code': code})
                else:
                    self.show_no_data(f"无法获取 {code} 的数据")
            else:
                self.show_no_data("所有数据获取方式都失败")
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"处理拖拽事件失败: {str(e)}")
            self.show_no_data("拖拽处理失败")

    def handle_external_drop_event(self, event):
        """处理外部拖拽事件"""
        self.dropEvent(event)

    def dragMoveEvent(self, event):
        """处理拖拽移动事件"""
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    @staticmethod
    def parse_dragged_stock_code(event):
        """解析拖拽事件中的股票代码"""
        raw_text = ""
        if event.mimeData().hasText():
            raw_text = event.mimeData().text().strip()
        elif event.mimeData().hasFormat("text/plain"):
            raw_text = str(event.mimeData().data(
                "text/plain"), encoding="utf-8").strip()
        if raw_text.startswith("★"):
            raw_text = raw_text[1:].strip()
        code = raw_text.split()[0] if raw_text else ""
        return code, raw_text

    def resizeEvent(self, event):
        """处理窗口大小变化事件"""
        super().resizeEvent(event)
        # 只在尺寸变化幅度较大时重绘
        if event.oldSize().width() > 0 and event.oldSize().height() > 0:
            if abs(event.oldSize().width() - event.size().width()) < 10 and abs(event.oldSize().height() - event.size().height()) < 10:
                return  # 跳过微小变化
        QTimer.singleShot(0, self.canvas.draw_idle)
        self._optimize_display()

    def contextMenuEvent(self, event):
        """处理右键菜单事件"""
        menu = QMenu(self)
        save_action = menu.addAction("保存图表为图片")
        export_action = menu.addAction("导出K线/指标数据")
        indicator_action = menu.addAction("添加/隐藏指标")
        stat_action = menu.addAction("区间统计")
        highlight_action = menu.addAction("标记/高亮K线")
        replay_action = menu.addAction("历史回看/回放")
        copy_action = menu.addAction("复制图表到剪贴板")
        refresh_action = menu.addAction("刷新图表")
        clear_highlight_action = menu.addAction("清空高亮")
        action = menu.exec_(event.globalPos())
        if action == save_action:
            self.save_chart_image()
        elif action == export_action:
            self.export_kline_and_indicators()
        elif action == indicator_action:
            self.request_indicator_dialog.emit()
        elif action == stat_action:
            self.trigger_stat_dialog()
        elif action == highlight_action:
            self.mark_highlight_candle(event)
        elif action == replay_action:
            self.toggle_replay()
        elif action == copy_action:
            self.copy_chart_to_clipboard()
        elif action == refresh_action:
            try:
                # 使用update_chart方法而不是refresh方法
                if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                    self.update_chart({'kdata': self.current_kdata})
                else:
                    self.show_no_data("无数据")
            except Exception as e:
                if hasattr(self, 'log_manager'):
                    self.log_manager.error(f"刷新图表失败: {str(e)}")
                if hasattr(self, 'error_occurred'):
                    self.error_occurred.emit(f"刷新图表失败: {str(e)}")
        elif action == clear_highlight_action:
            self.clear_highlighted_candles()

    def save_chart_image(self):
        """保存图表为图片"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存图表", "", "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf)")
            if file_path:
                self.figure.savefig(file_path)
                if self.log_manager:
                    self.log_manager.info(f"图表已保存到: {file_path}")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"保存图表失败: {str(e)}")

    def export_kline_and_indicators(self):
        """导出K线和指标数据"""
        try:
            if self.current_kdata is None or self.current_kdata.empty:
                QMessageBox.warning(self, "提示", "当前无K线数据可导出！")
                return
            df = self.current_kdata.copy()
            # 合并所有已绘制指标（假设指标已添加为df列）
            # 可扩展：遍历self.active_indicators，合并指标数据
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出K线/指标数据", "", "CSV Files (*.csv)")
            if file_path:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                if self.log_manager:
                    self.log_manager.info(f"K线/指标数据已导出到: {file_path}")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"导出K线/指标数据失败: {str(e)}")

    def trigger_stat_dialog(self):
        """触发统计对话框"""
        # 统计当前缩放区间或鼠标选区
        try:
            if self.current_kdata is None or self.current_kdata.empty:
                QMessageBox.warning(self, "提示", "当前无K线数据可统计！")
                return
            # 取当前X轴可见范围
            xlim = self.price_ax.get_xlim()
            start_idx = int(max(0, round(xlim[0])))
            end_idx = int(min(len(self.current_kdata)-1, round(xlim[1])))
            self.request_stat_dialog.emit((start_idx, end_idx))
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"区间统计失败: {str(e)}")

    def mark_highlight_candle(self, event):
        """标记高亮K线"""
        # 标记鼠标所在K线为高亮
        try:
            if self.current_kdata is None or self.current_kdata.empty:
                return
            # 计算鼠标在axes中的xdata
            pos = self.price_ax.transData.inverted().transform((event.x(), event.y()))
            x_idx = int(round(pos[0]))
            if 0 <= x_idx < len(self.current_kdata):
                if not hasattr(self, 'highlighted_indices'):
                    self.highlighted_indices = set()
                self.highlighted_indices.add(x_idx)
                self.refresh()
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"标记高亮K线失败: {str(e)}")

    def clear_highlighted_candles(self):
        """清空高亮K线"""
        if hasattr(self, 'highlighted_indices'):
            self.highlighted_indices.clear()
        self.refresh()

    def toggle_replay(self):
        """切换历史回放"""
        # 历史回看/回放动画
        try:
            if hasattr(self, '_replay_timer') and self._replay_timer and self._replay_timer.isActive():
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
        if not hasattr(self, '_replay_index') or self._replay_index is None or self.current_kdata is None:
            return
        if self._replay_index >= len(self.current_kdata):
            if hasattr(self, '_replay_timer') and self._replay_timer:
                self._replay_timer.stop()
            self._replay_index = None
            return
        # 只显示前self._replay_index根K线
        self.update_chart(
            {'kdata': self.current_kdata.iloc[:self._replay_index]})
        self._replay_index += 1

    def copy_chart_to_clipboard(self):
        """复制图表到剪贴板"""
        try:
            buf = io.BytesIO()
            self.figure.savefig(buf, format='png')
            buf.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.read(), 'PNG')
            QApplication.clipboard().setPixmap(pixmap)
            if self.log_manager:
                self.log_manager.info("图表已复制到剪贴板")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"复制图表到剪贴板失败: {str(e)}")

    def on_indicator_selected(self, indicators: list):
        """接收指标选择结果，更新active_indicators并刷新图表"""
        self.active_indicators = indicators
        self.update_chart()

    def _on_indicator_changed(self, indicators):
        """多屏同步所有激活指标，仅同步选中项（已废弃，自动同步主窗口get_current_indicators）"""
        self.update_chart()

    # 删除冲突的refresh方法，使用ChartWidget或utility_mixin中的实现

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

    def highlight_signals(self, signals):
        """高亮指定信号"""
        try:
            # 清除旧高亮
            self.clear_signal_highlight()

            if not signals or not hasattr(self, 'price_ax') or not self.price_ax:
                return

            # 绘制高亮效果
            highlight_artists = []
            for signal in signals:
                idx = signal.get('index', 0)
                price = signal.get('price', 0)

                # 高亮圆圈
                highlight_circle = self.price_ax.scatter(idx, price, s=200,
                                                         facecolors='none', edgecolors='yellow',
                                                         linewidths=3, alpha=0.8, zorder=30)
                highlight_artists.append(highlight_circle)

                # 高亮文字
                highlight_text = self.price_ax.text(idx, price * 1.03, f"选中: {signal.get('type', '')}",
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
                current_xlim = self.price_ax.get_xlim()
                window_size = current_xlim[1] - current_xlim[0]
                new_center = idx
                self.price_ax.set_xlim(
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
