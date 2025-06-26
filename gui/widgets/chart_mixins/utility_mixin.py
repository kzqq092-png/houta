"""
图表控件工具方法Mixin

该模块包含ChartWidget的工具方法，包括：
- 数据处理和格式化
- 周期变更处理
- 可见范围获取
- 基础的图表操作方法
"""

import numpy as np
import pandas as pd
import traceback
from datetime import datetime, timedelta
from typing import Tuple, Optional


class UtilityMixin:
    """工具功能Mixin

    包含ChartWidget的各种工具方法和辅助功能
    """

    def _downsample_kdata(self, kdata, max_points=1200):
        """对K线数据做降采样，提升渲染性能

        Args:
            kdata: K线数据DataFrame
            max_points: 最大点数，默认1200

        Returns:
            pd.DataFrame: 降采样后的K线数据
        """
        if len(kdata) <= max_points:
            return kdata
        idx = np.linspace(0, len(kdata)-1, max_points).astype(int)
        return kdata.iloc[idx]

    def _safe_format_date(self, row, idx, kdata):
        """安全地格式化日期，处理数值索引和datetime索引的情况

        Args:
            row: K线数据行
            idx: K线索引
            kdata: K线数据DataFrame

        Returns:
            str: 格式化后的日期字符串
        """
        try:
            # 优先从kdata的实际索引获取datetime
            if hasattr(kdata.index[idx], 'strftime'):
                return kdata.index[idx].strftime('%Y-%m-%d')
            elif hasattr(row.name, 'strftime'):
                # 如果索引本身是datetime
                return row.name.strftime('%Y-%m-%d')
            else:
                # 如果都不是datetime，检查是否有datetime列
                if 'datetime' in kdata.columns:
                    try:
                        date_val = pd.to_datetime(kdata.iloc[idx]['datetime'])
                        return date_val.strftime('%Y-%m-%d')
                    except:
                        pass

                # 尝试转换索引
                try:
                    date_val = pd.to_datetime(kdata.index[idx])
                    return date_val.strftime('%Y-%m-%d')
                except:
                    # 最后的兜底方案：使用索引位置生成相对日期
                    base_date = datetime(2024, 1, 1)
                    actual_date = base_date + timedelta(days=idx)
                    return actual_date.strftime('%Y-%m-%d')
        except Exception:
            return f"第{idx}根K线"

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

    def refresh(self) -> None:
        """
        刷新当前图表内容，异常只记录日志不抛出。
        若有数据则重绘K线图，否则显示"无数据"提示。
        """
        try:
            # 这里假设有self.current_kdata等数据
            if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                self.update_chart({'kdata': self.current_kdata})
            else:
                self.show_no_data("无数据")
        except Exception as e:
            error_msg = f"刷新图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            # 发射异常信号，主窗口可捕获弹窗
            self.error_occurred.emit(error_msg)

    def update(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def reload(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def get_visible_range(self) -> Optional[Tuple[int, int]]:
        """获取当前主图可见区间的K线索引范围

        Returns:
            Optional[Tuple[int, int]]: (开始索引, 结束索引) 或 None
        """
        try:
            xlim = self.indicator_ax.get_xlim()
            return int(xlim[0]), int(xlim[1])
        except Exception:
            return None

    def on_indicator_selected(self, indicators: list):
        """指标选择事件处理

        Args:
            indicators: 选中的指标列表
        """
        self.active_indicators = indicators

    def _on_indicator_changed(self, indicators):
        """指标变更处理（内部方法）

        Args:
            indicators: 变更的指标列表
        """
        self.active_indicators = indicators
