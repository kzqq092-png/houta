#!/usr/bin/env python3
"""
图表性能监控脚本

监控图表加载性能和错误日志，用于验证修复效果
"""

import time
import psutil
import logging
from datetime import datetime
from typing import Dict, List
import json


class ChartPerformanceMonitor:
    """图表性能监控器"""

    def __init__(self):
        self.metrics = {
            'chart_load_times': [],
            'memory_usage': [],
            'error_count': 0,
            'success_count': 0,
            'start_time': datetime.now()
        }

        # 设置日志监控
        self.setup_logging()

    def setup_logging(self):
        """设置日志监控"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('chart_performance.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def start_chart_load_timing(self):
        """开始图表加载计时"""
        return time.time()

    def end_chart_load_timing(self, start_time: float, success: bool = True):
        """结束图表加载计时"""
        load_time = time.time() - start_time
        self.metrics['chart_load_times'].append(load_time)

        if success:
            self.metrics['success_count'] += 1
            self.logger.info(f"图表加载成功，耗时: {load_time:.3f}秒")
        else:
            self.metrics['error_count'] += 1
            self.logger.error(f"图表加载失败，耗时: {load_time:.3f}秒")

        # 记录内存使用
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.metrics['memory_usage'].append(memory_usage)

    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        load_times = self.metrics['chart_load_times']
        if not load_times:
            return {"error": "无性能数据"}

        stats = {
            'total_loads': len(load_times),
            'success_count': self.metrics['success_count'],
            'error_count': self.metrics['error_count'],
            'success_rate': self.metrics['success_count'] / len(load_times) * 100,
            'avg_load_time': sum(load_times) / len(load_times),
            'min_load_time': min(load_times),
            'max_load_time': max(load_times),
            'avg_memory_usage': sum(self.metrics['memory_usage']) / len(self.metrics['memory_usage']),
            'monitoring_duration': (datetime.now() - self.metrics['start_time']).total_seconds()
        }

        return stats

    def log_chart_error(self, error_msg: str, stock_code: str = ""):
        """记录图表错误"""
        self.logger.error(f"图表错误 [{stock_code}]: {error_msg}")
        self.metrics['error_count'] += 1

    def generate_report(self) -> str:
        """生成性能报告"""
        stats = self.get_performance_stats()

        if "error" in stats:
            return stats["error"]

        report = f"""
=== 图表性能监控报告 ===
监控时间: {stats['monitoring_duration']:.1f}秒
总加载次数: {stats['total_loads']}
成功次数: {stats['success_count']}
失败次数: {stats['error_count']}
成功率: {stats['success_rate']:.1f}%

性能指标:
- 平均加载时间: {stats['avg_load_time']:.3f}秒
- 最快加载时间: {stats['min_load_time']:.3f}秒
- 最慢加载时间: {stats['max_load_time']:.3f}秒
- 平均内存使用: {stats['avg_memory_usage']:.1f}MB

性能评级:
"""

        # 性能评级
        if stats['avg_load_time'] < 0.5:
            report += "- 加载速度: 优秀 ✓"
        elif stats['avg_load_time'] < 1.0:
            report += "- 加载速度: 良好 ✓"
        elif stats['avg_load_time'] < 2.0:
            report += "- 加载速度: 一般 ⚠"
        else:
            report += "- 加载速度: 需要优化 ✗"

        if stats['success_rate'] >= 95:
            report += "\n- 稳定性: 优秀 ✓"
        elif stats['success_rate'] >= 90:
            report += "\n- 稳定性: 良好 ✓"
        elif stats['success_rate'] >= 80:
            report += "\n- 稳定性: 一般 ⚠"
        else:
            report += "\n- 稳定性: 需要优化 ✗"

        return report

    def save_metrics(self, filename: str = "chart_metrics.json"):
        """保存监控数据"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, default=str, ensure_ascii=False)

    def load_metrics(self, filename: str = "chart_metrics.json"):
        """加载监控数据"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.metrics = json.load(f)
        except FileNotFoundError:
            self.logger.info("未找到历史监控数据，从头开始")


# 全局监控器实例
chart_monitor = ChartPerformanceMonitor()


def monitor_chart_load(func):
    """图表加载监控装饰器"""
    def wrapper(*args, **kwargs):
        start_time = chart_monitor.start_chart_load_timing()
        try:
            result = func(*args, **kwargs)
            chart_monitor.end_chart_load_timing(start_time, success=True)
            return result
        except Exception as e:
            chart_monitor.end_chart_load_timing(start_time, success=False)
            chart_monitor.log_chart_error(str(e))
            raise
    return wrapper


if __name__ == "__main__":
    # 示例使用
    print("图表性能监控器初始化完成")
    print("使用方法:")
    print("1. 在图表加载函数上添加 @monitor_chart_load 装饰器")
    print("2. 调用 chart_monitor.generate_report() 生成报告")
    print("3. 调用 chart_monitor.save_metrics() 保存数据")
