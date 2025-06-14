"""
波浪分析标签页 - 专业版升级
"""
import json
from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QColor, QKeySequence
from .wave_tab_pro import WaveAnalysisTabPro


class WaveAnalysisTab(WaveAnalysisTabPro):
    """波浪分析标签页 - 继承专业版功能，保持向后兼容"""

    def __init__(self, config_manager=None):
        """初始化波浪分析标签页"""
        super().__init__(config_manager)

        # 保持向后兼容的属性
        self.wave_results = []
        self.wave_statistics = {}

        # 连接信号以保持兼容性
        self.analysis_completed.connect(self._on_analysis_completed)

    def _on_analysis_completed(self, results):
        """分析完成处理 - 兼容原有接口"""
        try:
            self.hide_loading()
            self.status_label.setText("分析完成")

            if 'error' in results:
                self.error_occurred.emit(results['error'])
                return

            # 更新显示
            self._update_wave_display(results)

            # 发射兼容信号
            if 'elliott_waves' in results:
                self.wave_analysis_completed.emit(results)

        except Exception as e:
            self.log_manager.error(f"分析完成处理失败: {e}")

    def _update_wave_display(self, results):
        """更新波浪显示"""
        # 更新艾略特波浪表格
        if 'elliott_waves' in results:
            self._update_elliott_table(results['elliott_waves'])

        # 更新江恩表格
        if 'gann_levels' in results:
            self._update_gann_table(results['gann_levels'])

        # 更新斐波那契表格
        if 'fibonacci_levels' in results:
            self._update_fibonacci_table(results['fibonacci_levels'])

        # 更新预测显示
        if 'wave_prediction' in results:
            self.prediction_text.setText(results['wave_prediction'])

        # 更新综合报告
        if 'comprehensive_report' in results:
            self.report_text.setText(results['comprehensive_report'])

    def _update_elliott_table(self, waves):
        """更新艾略特波浪表格"""
        self.elliott_table.setRowCount(len(waves))
        for i, wave in enumerate(waves):
            self.elliott_table.setItem(i, 0, QTableWidgetItem(str(wave.get('wave', ''))))
            self.elliott_table.setItem(i, 1, QTableWidgetItem(str(wave.get('type', ''))))
            self.elliott_table.setItem(i, 2, QTableWidgetItem(str(wave.get('start', {}).get('date', ''))))
            self.elliott_table.setItem(i, 3, QTableWidgetItem(str(wave.get('end', {}).get('date', ''))))
            self.elliott_table.setItem(i, 4, QTableWidgetItem(f"{wave.get('amplitude', 0)*100:.2f}%"))
            self.elliott_table.setItem(i, 5, QTableWidgetItem(str(wave.get('time', ''))))
            self.elliott_table.setItem(i, 6, QTableWidgetItem(f"{wave.get('confidence', 0):.2f}"))
            self.elliott_table.setItem(i, 7, QTableWidgetItem(str(wave.get('status', ''))))

    def _update_gann_table(self, levels):
        """更新江恩表格"""
        self.gann_table.setRowCount(len(levels))
        for i, level in enumerate(levels):
            self.gann_table.setItem(i, 0, QTableWidgetItem(str(level.get('type', ''))))
            self.gann_table.setItem(i, 1, QTableWidgetItem(f"{level.get('angle', 0):.1f}°"))
            self.gann_table.setItem(i, 2, QTableWidgetItem(f"{level.get('price', 0):.2f}"))
            self.gann_table.setItem(i, 3, QTableWidgetItem(str(level.get('time', ''))))
            self.gann_table.setItem(i, 4, QTableWidgetItem(str(level.get('strength', ''))))
            self.gann_table.setItem(i, 5, QTableWidgetItem(str(level.get('status', ''))))

    def _update_fibonacci_table(self, levels):
        """更新斐波那契表格"""
        self.fibonacci_table.setRowCount(len(levels))
        for i, level in enumerate(levels):
            self.fibonacci_table.setItem(i, 0, QTableWidgetItem(str(level.get('ratio', ''))))
            self.fibonacci_table.setItem(i, 1, QTableWidgetItem(f"{level.get('price', 0):.2f}"))
            self.fibonacci_table.setItem(i, 2, QTableWidgetItem(str(level.get('type', ''))))
            self.fibonacci_table.setItem(i, 3, QTableWidgetItem(str(level.get('strength', ''))))
            self.fibonacci_table.setItem(i, 4, QTableWidgetItem(str(level.get('validity', ''))))

    # 保持向后兼容的方法
    def analyze_wave(self):
        """执行波浪分析 - 兼容原接口"""
        self.comprehensive_wave_analysis()

    def analyze_elliott_waves(self, period, sensitivity, min_wave, use_fibonacci):
        """分析艾略特波浪 - 兼容原接口"""
        self.elliott_wave_analysis()

    def analyze_gann(self, period, sensitivity):
        """分析江恩理论 - 兼容原接口"""
        self.gann_analysis()

    def analyze_support_resistance(self, period, sensitivity):
        """分析支撑阻力位 - 兼容原接口"""
        self.fibonacci_analysis()

    def clear_wave(self):
        """清除波浪 - 兼容原接口"""
        self._do_clear_data()

    def update_wave_display(self):
        """更新波浪显示 - 兼容原接口"""
        # 如果有最新的分析结果，更新显示
        if hasattr(self, 'latest_results') and self.latest_results:
            self._update_wave_display(self.latest_results)

    def update_wave_statistics(self):
        """更新波浪统计 - 兼容原接口"""
        # 计算统计信息
        self.wave_statistics = {
            'elliott_count': len(self.elliott_waves),
            'gann_count': len(self.gann_levels),
            'fibonacci_count': len(self.fibonacci_levels),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def export_wave_analysis(self):
        """导出波浪分析 - 兼容原接口"""
        self.export_results()

    def find_extremes(self, high_prices, low_prices, window):
        """寻找极值点 - 兼容原接口"""
        return self._find_extremes(high_prices, low_prices)

    def count_tests(self, prices, level, tolerance):
        """计算测试次数 - 兼容原接口"""
        count = 0
        for price in prices:
            if abs(price - level) / level <= tolerance:
                count += 1
        return count

    def refresh_data(self):
        """刷新数据 - 兼容原接口"""
        self._do_refresh_data()

    def clear_data(self):
        """清除数据 - 兼容原接口"""
        self._do_clear_data()

    # 向后兼容的信号
    wave_analysis_completed = pyqtSignal(dict)
