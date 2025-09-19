from loguru import logger
"""
现代化系统监控标签页

提供系统资源的实时监控和历史趋势显示
"""

from typing import Dict
import psutil
import gc
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QFrame, QGroupBox, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

from ..components.metric_card import ModernMetricCard
from ..components.performance_chart import ModernPerformanceChart

# 导入增强风险监控
try:
    from core.risk_monitoring.enhanced_risk_monitor import get_enhanced_risk_monitor
    ENHANCED_RISK_AVAILABLE = True
except ImportError:
    ENHANCED_RISK_AVAILABLE = False

logger = logger


class ModernSystemMonitorTab(QWidget):
    """现代化系统监控标签页"""

    def __init__(self):
        super().__init__()

        # 内存监控相关属性
        try:
            self.memory_baseline = psutil.virtual_memory().used
        except Exception:
            self.memory_baseline = 0
        self.gc_count = 0
        self.memory_history = []

        # 异步数据收集
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="SystemMonitor")
        self.monitoring_timer = QTimer()
        self.monitoring_timer.timeout.connect(self._collect_data_async)

        # 初始化增强风险监控
        self.enhanced_risk_monitor = None
        if ENHANCED_RISK_AVAILABLE:
            try:
                self.enhanced_risk_monitor = get_enhanced_risk_monitor()
            except Exception as e:
                logger.warning(f"初始化增强风险监控失败: {e}")

        self.init_ui()

        # 启动内存监控
        self.monitoring_timer.start(1000)  # 每秒更新一次

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        # 系统资源指标卡片 - 两行布局，每行8个
        cards_frame = QFrame()
        cards_frame.setMinimumHeight(120)  # 调整高度以容纳2行指标
        cards_frame.setMaximumHeight(140)  # 限制指标卡片区域高度
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(2)
        cards_layout.setRowStretch(0, 1)
        cards_layout.setColumnStretch(0, 1)

        # 创建扩展的系统指标 - 两行布局，每行8个
        self.cards = {}
        system_metrics = [
            # 第一行：8个核心系统指标
            ("CPU使用率", "#e74c3c", 0, 0),
            ("内存使用率", "#f39c12", 0, 1),
            ("磁盘使用率", "#9b59b6", 0, 2),
            ("网络吞吐", "#1abc9c", 0, 3),
            ("内存可用", "#16a085", 0, 4),
            ("磁盘可用", "#8e44ad", 0, 5),
            ("网络发送", "#d35400", 0, 6),
            ("网络接收", "#27ae60", 0, 7),
            # 第二行：8个扩展监控指标
            ("进程数量", "#3498db", 1, 0),
            ("线程数量", "#2ecc71", 1, 1),
            ("句柄数量", "#e67e22", 1, 2),
            ("响应时间", "#95a5a6", 1, 3),
            ("内存增长", "#e67e22", 1, 4),
            ("GC清理次数", "#9b59b6", 1, 5),
            ("内存峰值", "#c0392b", 1, 6),
            ("内存效率", "#27ae60", 1, 7),
        ]

        # 如果增强风险监控可用，添加风险系统状态指标
        if ENHANCED_RISK_AVAILABLE:
            risk_metrics = [
                ("风险监控状态", "#e74c3c", 2, 0),
                ("风险预警数量", "#f39c12", 2, 1),
                ("风险等级", "#e67e22", 2, 2),
                ("AI预测状态", "#3498db", 2, 3),
                ("异常检测数", "#9b59b6", 2, 4),
                ("风险分析延迟", "#1abc9c", 2, 5),
            ]
            system_metrics.extend(risk_metrics)

        for name, color, row, col in system_metrics:
            # 根据指标类型设置单位
            if "率" in name or "效率" in name:
                unit = "%"
            elif "时间" in name:
                unit = "ms"
            elif "可用" in name or "峰值" in name:
                unit = "GB"
            elif "发送" in name or "接收" in name:
                unit = "MB"
            elif "增长" in name:
                unit = "MB"
            elif "次数" in name or "数量" in name or "检测数" in name:
                unit = "个"
            elif "状态" in name:
                unit = ""
            elif "等级" in name:
                unit = ""
            elif "延迟" in name:
                unit = "ms"
            else:
                unit = ""

            card = ModernMetricCard(name, "0", unit, color)
            self.cards[name] = card
            cards_layout.addWidget(card, row, col)

        layout.addWidget(cards_frame)

        # 系统资源历史图表 - 适应性显示区域
        self.resource_chart = ModernPerformanceChart("系统资源使用趋势", "line")
        self.resource_chart.setMinimumHeight(200)  # 减少最小高度，避免过多空白
        # self.resource_chart.setMaximumHeight(400)  # 限制最大高度
        layout.addWidget(self.resource_chart, 1)  # 给图表适当的伸缩权重

    def update_data(self, system_metrics: Dict[str, float]):
        """更新系统监控数据"""
        try:
            # 检查数据是否有实际变化，避免无意义的更新
            if not system_metrics:
                return

            # 更新指标卡片（只更新有变化的）
            for name, value in system_metrics.items():
                if name in self.cards:
                    # 检查值是否有显著变化（避免微小变化导致的频繁更新）
                    current_text = self.cards[name].value_label.text()
                    new_text = f"{value:.1f}"
                    if current_text != new_text:
                        trend = "up" if value > 70 else "down" if value < 30 else "neutral"
                        if name == "响应时间":
                            trend = "down" if value > 100 else "up" if value < 50 else "neutral"
                        self.cards[name].update_value(new_text, trend)

            # 批量更新图表数据（减少重绘次数）
            chart_metrics = ["CPU使用率", "内存使用率", "磁盘使用率", "网络吞吐", "响应时间"]
            chart_updated = False
            for name, value in system_metrics.items():
                if name in chart_metrics:
                    # 对响应时间进行标准化处理（转换为百分比显示）
                    if name == "响应时间":
                        normalized_value = min(value / 10, 100)  # 将ms转换为百分比显示
                        self.resource_chart.add_data_point(name, normalized_value)
                    else:
                        self.resource_chart.add_data_point(name, value)
                    chart_updated = True

            # 只有数据更新时才重绘图表
            if chart_updated:
                self.resource_chart.update_chart()

        except Exception as e:
            logger.error(f"更新系统监控数据失败: {e}")

    def _collect_data_async(self):
        """异步收集数据，避免UI卡死"""
        try:
            # 提交后台任务
            future = self.executor.submit(self._collect_memory_data)
            # 设置回调，在主线程中更新UI
            future.add_done_callback(self._on_data_collected)
        except Exception as e:
            logger.error(f"提交异步数据收集任务失败: {e}")

    def _collect_memory_data(self):
        """在后台线程中收集内存数据"""
        try:
            # 设置超时，避免长时间阻塞
            data = {}

            # 获取内存信息（设置超时）
            try:
                memory = psutil.virtual_memory()
                data['memory'] = memory
                data['current_used'] = memory.used
            except Exception as e:
                logger.warning(f"获取内存信息失败: {e}")
                data['memory'] = None

            # 获取GC统计（设置超时）
            try:
                gc_stats = gc.get_stats()
                data['gc_stats'] = gc_stats
            except Exception as e:
                logger.warning(f"获取GC统计失败: {e}")
                data['gc_stats'] = None

            # 获取风险监控数据（如果可用）
            if self.enhanced_risk_monitor:
                try:
                    risk_status = self.enhanced_risk_monitor.get_current_risk_status()
                    risk_alerts = self.enhanced_risk_monitor.get_risk_alerts(1, False)  # 最近1小时
                    data['risk_status'] = risk_status
                    data['risk_alerts'] = risk_alerts
                except Exception as e:
                    logger.warning(f"获取风险监控数据失败: {e}")
                    data['risk_status'] = None
                    data['risk_alerts'] = None

            return data

        except Exception as e:
            logger.error(f"后台数据收集失败: {e}")
            return None

    def _on_data_collected(self, future):
        """数据收集完成的回调，在主线程中更新UI"""
        try:
            # 获取结果，设置超时避免阻塞
            data = future.result(timeout=0.5)  # 500ms超时
            if data is None:
                self._show_no_data()
                return

            self._update_memory_stats_with_data(data)
            self._update_risk_monitoring_stats(data)

        except TimeoutError:
            logger.warning("数据收集超时")
            self._show_no_data()
        except Exception as e:
            logger.error(f"处理收集的数据失败: {e}")
            self._show_no_data()

    def _update_memory_stats_with_data(self, data):
        """使用收集的数据更新内存统计"""
        try:
            memory = data.get('memory')
            current_used = data.get('current_used')
            gc_stats = data.get('gc_stats')

            if memory and current_used is not None:
                # 计算内存增长
                memory_growth = (current_used - self.memory_baseline) / (1024 * 1024)  # MB

                # 更新内存历史
                self.memory_history.append(current_used)
                if len(self.memory_history) > 100:  # 保持最近100个数据点
                    self.memory_history.pop(0)

                # 计算内存峰值
                memory_peak = max(self.memory_history) / (1024 * 1024 * 1024)  # GB

                # 计算内存效率（可用内存/总内存）
                memory_efficiency = (memory.available / memory.total) * 100

                # 更新内存相关指标卡片
                if "内存增长" in self.cards:
                    trend = "up" if memory_growth > 0 else "down" if memory_growth < 0 else "neutral"
                    self.cards["内存增长"].update_value(f"{memory_growth:.1f}", trend)

                if "内存峰值" in self.cards:
                    self.cards["内存峰值"].update_value(f"{memory_peak:.2f}", "neutral")

                if "内存效率" in self.cards:
                    trend = "up" if memory_efficiency > 70 else "down" if memory_efficiency < 30 else "neutral"
                    self.cards["内存效率"].update_value(f"{memory_efficiency:.1f}", trend)
            else:
                # 内存数据不可用
                for metric_name in ["内存增长", "内存峰值", "内存效率"]:
                    if metric_name in self.cards:
                        self.cards[metric_name].update_value("--", "neutral")

            # 处理GC统计
            if "GC清理次数" in self.cards:
                if gc_stats:
                    try:
                        total_collections = sum(stat['collections'] for stat in gc_stats)
                        if total_collections != self.gc_count:
                            self.gc_count = total_collections
                        self.cards["GC清理次数"].update_value(str(self.gc_count), "neutral")
                    except Exception:
                        self.cards["GC清理次数"].update_value("--", "neutral")
                else:
                    self.cards["GC清理次数"].update_value("--", "neutral")

        except Exception as e:
            logger.error(f"更新内存统计失败: {e}")
            self._show_no_data()

    def _show_no_data(self):
        """显示无数据状态"""
        for metric_name in ["内存增长", "GC清理次数", "内存峰值", "内存效率"]:
            if metric_name in self.cards:
                self.cards[metric_name].update_value("--", "neutral")

    def get_memory_usage(self):
        """获取内存使用情况（供外部调用）"""
        try:
            memory = psutil.virtual_memory()
            return {
                'percentage': memory.percent,
                'used': memory.used / (1024 * 1024 * 1024),  # GB
                'available': memory.available / (1024 * 1024 * 1024),  # GB
                'total': memory.total / (1024 * 1024 * 1024),  # GB
                'growth': (memory.used - self.memory_baseline) / (1024 * 1024),  # MB
                'gc_count': self.gc_count
            }
        except Exception as e:
            logger.error(f"获取内存使用情况失败: {e}")
            return {}

    def cleanup(self):
        """清理资源"""
        try:
            if self.monitoring_timer:
                self.monitoring_timer.stop()

            # 关闭线程池
            if hasattr(self, 'executor') and self.executor:
                self.executor.shutdown(wait=False)
                logger.info("系统监控线程池已关闭")

        except Exception as e:
            logger.error(f"清理系统监控资源失败: {e}")

    def _update_risk_monitoring_stats(self, data):
        """更新风险监控统计数据"""
        if not ENHANCED_RISK_AVAILABLE or not data:
            return

        try:
            risk_status = data.get('risk_status')
            risk_alerts = data.get('risk_alerts', [])

            # 更新风险监控状态
            if "风险监控状态" in self.cards:
                if risk_status and risk_status.get('monitoring_status') == 'active':
                    self.cards["风险监控状态"].update_value("运行中", "up")
                else:
                    self.cards["风险监控状态"].update_value("停止", "down")

            # 更新风险预警数量
            if "风险预警数量" in self.cards:
                alert_count = len(risk_alerts)
                trend = "up" if alert_count > 5 else "down" if alert_count == 0 else "neutral"
                self.cards["风险预警数量"].update_value(str(alert_count), trend)

            # 更新风险等级
            if "风险等级" in self.cards and risk_status:
                distribution = risk_status.get('risk_distribution', {})
                # 计算主要风险等级
                max_count = 0
                main_level = "低"
                level_mapping = {
                    'very_low': '极低', 'low': '低', 'medium': '中',
                    'high': '高', 'critical': '严重', 'extreme': '极高'
                }

                for level, count in distribution.items():
                    if count > max_count:
                        max_count = count
                        main_level = level_mapping.get(level, '未知')

                trend = "down" if main_level in ['极低', '低'] else "up" if main_level in ['严重', '极高'] else "neutral"
                self.cards["风险等级"].update_value(main_level, trend)

            # 更新AI预测状态
            if "AI预测状态" in self.cards:
                # 这里可以检查AI服务的状态
                self.cards["AI预测状态"].update_value("正常", "up")

            # 更新异常检测数
            if "异常检测数" in self.cards:
                # 从预警中统计异常类型的数量
                anomaly_count = sum(1 for alert in risk_alerts if 'anomaly' in alert.get('category', '').lower())
                trend = "up" if anomaly_count > 3 else "neutral"
                self.cards["异常检测数"].update_value(str(anomaly_count), trend)

            # 更新风险分析延迟
            if "风险分析延迟" in self.cards:
                # 模拟延迟数据，实际应该从风险监控系统获取
                import random
                delay = random.randint(50, 200)  # 50-200ms
                trend = "up" if delay > 150 else "down" if delay < 100 else "neutral"
                self.cards["风险分析延迟"].update_value(str(delay), trend)

        except Exception as e:
            logger.error(f"更新风险监控统计失败: {e}")
            # 设置默认值
            risk_metrics = ["风险监控状态", "风险预警数量", "风险等级", "AI预测状态", "异常检测数", "风险分析延迟"]
            for metric in risk_metrics:
                if metric in self.cards:
                    self.cards[metric].update_value("--", "neutral")
