#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版实时性能监控
实现高精度实时监控、智能异常检测和自动告警系统

作者: Hikyuu UI系统
版本: 1.0
"""

import time
import threading
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque, defaultdict
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from loguru import logger

from .unified_performance_coordinator import (
    UnifiedPerformanceCoordinator, UnifiedPerformanceMetrics, 
    PerformanceAlert, AlertSeverity, PerformanceCategory
)

class AnomalyType(Enum):
    """异常类型"""
    SPIKE = "spike"           # 突发异常
    GRADUAL_CHANGE = "gradual_change"  # 渐进变化
    DEGRADATION = "degradation"  # 性能退化
    OUTLIER = "outlier"       # 离群值
    PATTERN_CHANGE = "pattern_change"  # 模式变化

class TrendDirection(Enum):
    """趋势方向"""
    IMPROVING = "improving"   # 改善
    STABLE = "stable"         # 稳定
    DECLINING = "declining"   # 下降

@dataclass
class AnomalyDetectionResult:
    """异常检测结果"""
    is_anomaly: bool
    anomaly_type: Optional[AnomalyType] = None
    confidence: float = 0.0
    severity: AlertSeverity = AlertSeverity.INFO
    description: str = ""
    detected_at: float = field(default_factory=time.time)
    metric_name: str = ""
    current_value: float = 0.0
    baseline_value: float = 0.0
    deviation: float = 0.0

@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    direction: TrendDirection
    confidence: float
    slope: float
    r_squared: float
    prediction_horizon: float  # 预测时间范围（秒）
    predicted_value: float
    change_rate: float  # 变化率 (per second)

@dataclass
class SmartThreshold:
    """智能阈值配置"""
    metric_name: str
    baseline_value: float
    upper_threshold: float
    lower_threshold: float
    threshold_sensitivity: float = 0.1  # 阈值敏感度
    adaptation_rate: float = 0.05       # 自适应率
    last_adaptation: float = field(default_factory=time.time)

class AnomalyDetector:
    """智能异常检测器"""
    
    def __init__(self, window_size: int = 300, 
                 spike_threshold: float = 3.0,
                 degradation_threshold: float = 0.7):
        self.window_size = window_size
        self.spike_threshold = spike_threshold
        self.degradation_threshold = degradation_threshold
        
        # 数据窗口
        self.metric_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.baseline_calculators: Dict[str, Dict] = {}
        
        # 统计信息
        self.statistics_cache: Dict[str, Dict] = {}
        
        logger.info(f"异常检测器初始化完成，窗口大小: {window_size}")
    
    def add_data_point(self, metric_name: str, value: float, timestamp: float = None):
        """添加数据点"""
        if timestamp is None:
            timestamp = time.time()
        
        self.metric_windows[metric_name].append((timestamp, value))
        
        # 维护统计缓存
        self._update_statistics_cache(metric_name)
    
    def _update_statistics_cache(self, metric_name: str):
        """更新统计缓存"""
        window = self.metric_windows[metric_name]
        if len(window) < 10:  # 需要足够数据才能计算统计信息
            return
        
        values = [item[1] for item in window]
        timestamps = [item[0] for item in window]
        
        try:
            # 基础统计
            mean_val = np.mean(values)
            std_val = np.std(values)
            median_val = np.median(values)
            q75, q25 = np.percentile(values, [75, 25])
            iqr = q75 - q25
            
            # 趋势分析
            slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps, values)
            
            self.statistics_cache[metric_name] = {
                'mean': mean_val,
                'std': std_val,
                'median': median_val,
                'q75': q75,
                'q25': q25,
                'iqr': iqr,
                'trend_slope': slope,
                'trend_r2': r_value ** 2,
                'trend_p_value': p_value,
                'min': np.min(values),
                'max': np.max(values),
                'range': np.max(values) - np.min(values),
                'count': len(values)
            }
            
        except Exception as e:
            logger.warning(f"更新{metric_name}统计缓存失败: {e}")
    
    def detect_anomaly(self, metric_name: str, current_value: float) -> AnomalyDetectionResult:
        """检测异常"""
        if metric_name not in self.statistics_cache:
            # 数据不足，无法检测
            return AnomalyDetectionResult(
                is_anomaly=False,
                confidence=0.0,
                description="数据不足，无法检测异常"
            )
        
        stats = self.statistics_cache[metric_name]
        
        # Z-Score检测 (突发异常)
        z_score = abs(current_value - stats['mean']) / (stats['std'] + 1e-8)
        is_spike = z_score > self.spike_threshold
        
        # IQR检测 (离群值)
        iqr_threshold = 1.5 * stats['iqr']
        is_outlier = (current_value < stats['q25'] - iqr_threshold or 
                     current_value > stats['q75'] + iqr_threshold)
        
        # 性能退化检测
        is_degradation = False
        if stats['trend_r2'] > 0.7:  # 强趋势
            # 根据趋势预测当前应该的值
            trend_impact = stats['trend_slope'] * 60  # 假设60秒前的基础值
            expected_value = stats['mean'] + trend_impact
            degradation_ratio = current_value / (expected_value + 1e-8)
            
            if degradation_ratio < self.degradation_threshold:
                is_degradation = True
        
        # 渐进变化检测
        is_gradual_change = False
        if abs(stats['trend_slope']) > stats['std'] * 0.001:  # 显著趋势
            recent_values = [item[1] for item in list(self.metric_windows[metric_name])[-10:]]
            if len(recent_values) >= 5:
                recent_trend = np.polyfit(range(len(recent_values)), recent_values, 1)[0]
                if abs(recent_trend) > stats['std'] * 0.01:
                    is_gradual_change = True
        
        # 确定异常类型和严重程度
        anomaly_type = None
        severity = AlertSeverity.INFO
        confidence = 0.0
        description = ""
        
        if is_spike or is_outlier:
            anomaly_type = AnomalyType.SPIKE if is_spike else AnomalyType.OUTLIER
            confidence = min(z_score / self.spike_threshold, 1.0)
            severity = AlertSeverity.ERROR if confidence > 0.8 else AlertSeverity.WARNING
            
            if is_spike:
                description = f"检测到突发异常，Z-Score: {z_score:.2f}"
            else:
                description = f"检测到离群值，值: {current_value:.2f}"
        
        elif is_degradation:
            anomaly_type = AnomalyType.DEGRADATION
            confidence = 0.9
            severity = AlertSeverity.CRITICAL
            description = f"检测到性能退化，退化比例: {degradation_ratio:.2f}"
        
        elif is_gradual_change:
            anomaly_type = AnomalyType.GRADUAL_CHANGE
            confidence = min(abs(stats['trend_r2']), 1.0)
            severity = AlertSeverity.WARNING if confidence > 0.7 else AlertSeverity.INFO
            description = f"检测到渐进变化，趋势斜率: {stats['trend_slope']:.4f}"
        
        return AnomalyDetectionResult(
            is_anomaly=anomaly_type is not None,
            anomaly_type=anomaly_type,
            confidence=confidence,
            severity=severity,
            description=description,
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=stats['mean'],
            deviation=abs(current_value - stats['mean'])
        )
    
    def analyze_trend(self, metric_name: str, prediction_horizon: float = 300) -> Optional[TrendAnalysis]:
        """分析趋势"""
        if metric_name not in self.statistics_cache:
            return None
        
        stats = self.statistics_cache[metric_name]
        
        # 趋势方向判断
        if abs(stats['trend_slope']) < stats['std'] * 0.001:
            direction = TrendDirection.STABLE
            slope = 0.0
        elif stats['trend_slope'] > 0:
            direction = TrendDirection.DECLINING if self._is_negative_trend(metric_name) else TrendDirection.IMPROVING
            slope = stats['trend_slope']
        else:
            direction = TrendDirection.IMPROVING if self._is_negative_trend(metric_name) else TrendDirection.DECLINING
            slope = stats['trend_slope']
        
        # 计算预测值
        predicted_value = stats['mean'] + slope * prediction_horizon
        change_rate = slope
        
        # 计算变化率（每秒）
        window = self.metric_windows[metric_name]
        if len(window) >= 2:
            time_span = window[-1][0] - window[0][0]
            if time_span > 0:
                change_rate = (window[-1][1] - window[0][1]) / time_span
        
        return TrendAnalysis(
            direction=direction,
            confidence=stats['trend_r2'],
            slope=slope,
            r_squared=stats['trend_r2'],
            prediction_horizon=prediction_horizon,
            predicted_value=predicted_value,
            change_rate=change_rate
        )
    
    def _is_negative_trend(self, metric_name: str) -> bool:
        """判断趋势是否为负向（对于需要降低的指标）"""
        # 对于这些指标，趋势上升是负面的
        negative_trend_metrics = [
            'cpu_utilization', 'memory_usage', 'gpu_utilization',
            'rendering_latency', 'error_rate', 'memory_pressure'
        ]
        
        return any(metric in metric_name.lower() for metric in negative_trend_metrics)

class SmartThresholdManager:
    """智能阈值管理器"""
    
    def __init__(self, adaptation_interval: float = 300):
        self.adaptation_interval = adaptation_interval
        self.thresholds: Dict[str, SmartThreshold] = {}
        self.adaptation_history: Dict[str, List[Tuple[float, float, float]]] = defaultdict(list)
    
    def add_threshold(self, threshold: SmartThreshold):
        """添加智能阈值"""
        self.thresholds[threshold.metric_name] = threshold
        logger.info(f"添加智能阈值: {threshold.metric_name}")
    
    def evaluate_threshold(self, metric_name: str, current_value: float) -> Dict[str, Any]:
        """评估阈值状态"""
        if metric_name not in self.thresholds:
            return {'breached': False, 'severity': AlertSeverity.INFO}
        
        threshold = self.thresholds[metric_name]
        
        # 检查是否超过阈值
        upper_breached = current_value > threshold.upper_threshold
        lower_breached = current_value < threshold.lower_threshold
        
        if not (upper_breached or lower_breached):
            return {'breached': False, 'severity': AlertSeverity.INFO}
        
        # 计算偏差程度
        if upper_breached:
            deviation = (current_value - threshold.upper_threshold) / threshold.upper_threshold
            severity = self._calculate_severity(deviation)
        else:
            deviation = (threshold.lower_threshold - current_value) / threshold.lower_threshold
            severity = self._calculate_severity(deviation)
        
        return {
            'breached': True,
            'severity': severity,
            'deviation': deviation,
            'threshold_type': 'upper' if upper_breached else 'lower',
            'current_value': current_value,
            'threshold_value': threshold.upper_threshold if upper_breached else threshold.lower_threshold
        }
    
    def _calculate_severity(self, deviation: float) -> AlertSeverity:
        """根据偏差计算严重程度"""
        if deviation < 0.1:
            return AlertSeverity.INFO
        elif deviation < 0.3:
            return AlertSeverity.WARNING
        elif deviation < 0.5:
            return AlertSeverity.ERROR
        else:
            return AlertSeverity.CRITICAL
    
    def adapt_thresholds(self, metric_name: str, current_value: float):
        """自适应调整阈值"""
        if metric_name not in self.thresholds:
            return
        
        threshold = self.thresholds[metric_name]
        current_time = time.time()
        
        # 检查是否需要自适应
        if current_time - threshold.last_adaptation < self.adaptation_interval:
            return
        
        # 收集历史数据进行自适应
        history = self.adaptation_history.get(metric_name, [])
        
        if len(history) < 10:  # 需要足够历史数据
            # 记录当前值
            self.adaptation_history[metric_name].append((current_time, current_value, threshold.baseline_value))
            return
        
        # 计算新的基线和阈值
        values = [item[1] for item in history[-50:]]  # 使用最近50个点
        if len(values) < 10:
            return
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        # 自适应调整
        new_baseline = threshold.baseline_value * (1 - threshold.adaptation_rate) + mean_val * threshold.adaptation_rate
        
        # 动态调整阈值范围
        threshold_factor = max(0.8, 1.0 - std_val / (mean_val + 1e-8))
        new_upper = new_baseline + threshold.upper_threshold - threshold.baseline_value
        new_lower = new_baseline - (threshold.baseline_value - threshold.lower_threshold)
        
        # 应用新阈值
        threshold.baseline_value = new_baseline
        threshold.upper_threshold = new_upper
        threshold.lower_threshold = new_lower
        threshold.last_adaptation = current_time
        
        logger.info(f"阈值自适应调整 {metric_name}: 基准 {threshold.baseline_value:.2f}, 上限 {threshold.upper_threshold:.2f}")

class EnhancedRealtimeMonitor:
    """增强版实时监控器"""
    
    def __init__(self, coordinator: UnifiedPerformanceCoordinator):
        self.coordinator = coordinator
        self.anomaly_detector = AnomalyDetector()
        self.threshold_manager = SmartThresholdManager()
        
        # 监控状态
        self.monitoring_active = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        # 实时数据缓存
        self.realtime_metrics: Dict[str, float] = {}
        self.last_update_time: Dict[str, float] = {}
        
        # 异常和告警统计
        self.anomaly_stats: Dict[str, int] = defaultdict(int)
        self.alert_stats: Dict[str, int] = defaultdict(int)
        
        # 回调函数
        self.anomaly_callbacks: List[Callable[[AnomalyDetectionResult], None]] = []
        self.trend_callbacks: List[Callable[[str, TrendAnalysis], None]] = []
        
        # 配置
        self.monitoring_interval = 0.5  # 500ms高频监控
        self.alert_cooldown = 30.0      # 30秒告警冷却
        
        # 初始化默认阈值
        self._initialize_default_thresholds()
        
        logger.info("增强版实时监控器初始化完成")
    
    def _initialize_default_thresholds(self):
        """初始化默认阈值"""
        default_thresholds = [
            SmartThreshold("cpu_utilization", 50.0, 80.0, 10.0),
            SmartThreshold("memory_usage", 60.0, 85.0, 20.0),
            SmartThreshold("gpu_utilization", 70.0, 90.0, 10.0),
            SmartThreshold("rendering_latency", 16.67, 33.33, 5.0),  # 60fps/30fps基准
            SmartThreshold("system_memory_usage_percent", 70.0, 90.0, 30.0),
            SmartThreshold("gpu_memory_used_mb", 1000.0, 2000.0, 100.0),
            SmartThreshold("total_threads_count", 50.0, 100.0, 10.0),
        ]
        
        for threshold in default_thresholds:
            self.threshold_manager.add_threshold(threshold)
        
        logger.info(f"初始化了 {len(default_thresholds)} 个默认阈值")
    
    def add_anomaly_callback(self, callback: Callable[[AnomalyDetectionResult], None]):
        """添加异常检测回调"""
        self.anomaly_callbacks.append(callback)
    
    def add_trend_callback(self, callback: Callable[[str, TrendAnalysis], None]):
        """添加趋势分析回调"""
        self.trend_callbacks.append(callback)
    
    def start_enhanced_monitoring(self, interval: float = 0.5) -> bool:
        """开始增强监控"""
        if self.monitoring_active:
            logger.warning("增强监控已在运行")
            return True
        
        try:
            self.monitoring_interval = interval
            
            # 确保协调器初始化
            if not self.coordinator.initialize_monitors():
                logger.error("监控协调器初始化失败")
                return False
            
            self.monitoring_active = True
            self.stop_event.clear()
            
            logger.info(f"开始增强版实时监控，间隔: {interval}秒")
            
            def enhanced_monitoring_loop():
                while self.monitoring_active and not self.stop_event.is_set():
                    try:
                        self._perform_enhanced_monitoring_cycle()
                        time.sleep(interval)
                        
                    except Exception as e:
                        logger.error(f"增强监控循环异常: {e}")
                        time.sleep(interval)
            
            self.monitor_thread = threading.Thread(target=enhanced_monitoring_loop, daemon=True)
            self.monitor_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动增强监控失败: {e}")
            self.monitoring_active = False
            return False
    
    def _perform_enhanced_monitoring_cycle(self):
        """执行增强监控周期"""
        # 获取当前统一指标
        current_metrics = self.coordinator.get_current_metrics()
        current_time = time.time()
        
        # 处理GPU指标
        if current_metrics.gpu_metrics:
            self._process_metric_group(
                "gpu", current_metrics.gpu_metrics.__dict__, current_time
            )
        
        # 处理内存指标
        if current_metrics.memory_metrics:
            self._process_metric_group(
                "memory", current_metrics.memory_metrics.__dict__, current_time
            )
        
        # 处理线程指标
        if current_metrics.thread_metrics:
            self._process_metric_group(
                "thread", current_metrics.thread_metrics.__dict__, current_time
            )
        
        # 处理渲染指标
        if current_metrics.rendering_fps > 0:
            self._process_single_metric(
                "rendering_fps", current_metrics.rendering_fps, current_time
            )
        
        if current_metrics.rendering_latency_ms > 0:
            self._process_single_metric(
                "rendering_latency", current_metrics.rendering_latency_ms, current_time
            )
        
        # 执行综合分析
        self._perform_comprehensive_analysis(current_metrics, current_time)
    
    def _process_metric_group(self, group_name: str, metrics_dict: Dict, timestamp: float):
        """处理指标组"""
        for metric_name, value in metrics_dict.items():
            if isinstance(value, (int, float)) and not np.isnan(value):
                full_name = f"{group_name}_{metric_name}"
                self._process_single_metric(full_name, float(value), timestamp)
    
    def _process_single_metric(self, metric_name: str, value: float, timestamp: float):
        """处理单个指标"""
        # 更新实时缓存
        self.realtime_metrics[metric_name] = value
        self.last_update_time[metric_name] = timestamp
        
        # 添加到异常检测器
        self.anomaly_detector.add_data_point(metric_name, value, timestamp)
        
        # 阈值检查
        threshold_result = self.threshold_manager.evaluate_threshold(metric_name, value)
        
        if threshold_result['breached']:
            self._handle_threshold_breach(metric_name, value, threshold_result)
        
        # 异常检测
        anomaly_result = self.anomaly_detector.detect_anomaly(metric_name, value)
        
        if anomaly_result.is_anomaly:
            self._handle_detected_anomaly(anomaly_result)
        
        # 趋势分析（周期性执行）
        if timestamp - self.last_update_time.get(f"{metric_name}_last_trend", 0) > 60:
            self._perform_trend_analysis(metric_name)
            self.last_update_time[f"{metric_name}_last_trend"] = timestamp
    
    def _handle_threshold_breach(self, metric_name: str, value: float, threshold_result: Dict):
        """处理阈值突破"""
        severity = threshold_result['severity']
        self.alert_stats[f"{metric_name}_threshold"] += 1
        
        # 创建性能告警
        alert = PerformanceAlert(
            alert_id=f"threshold_{metric_name}_{int(time.time())}",
            category=PerformanceCategory.ALL,
            severity=severity,
            title=f"阈值突破: {metric_name}",
            description=f"指标 {metric_name} 突破阈值，当前值: {value:.2f}",
            current_value=value,
            threshold_value=threshold_result['threshold_value'],
            timestamp=time.time(),
            metrics_data=threshold_result
        )
        
        # 委托给协调器处理
        self.coordinator._handle_alert(alert)
        
        logger.warning(f"阈值突破: {metric_name} = {value:.2f}")
    
    def _handle_detected_anomaly(self, anomaly_result: AnomalyDetectionResult):
        """处理检测到的异常"""
        self.anomaly_stats[anomaly_result.anomaly_type.value] += 1
        
        # 触发异常回调
        for callback in self.anomaly_callbacks:
            try:
                callback(anomaly_result)
            except Exception as e:
                logger.error(f"异常回调执行失败: {e}")
        
        # 如果是严重异常，创建告警
        if anomaly_result.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            alert = PerformanceAlert(
                alert_id=f"anomaly_{anomaly_result.metric_name}_{int(time.time())}",
                category=PerformanceCategory.ALL,
                severity=anomaly_result.severity,
                title=f"异常检测: {anomaly_result.metric_name}",
                description=f"{anomaly_result.description}，置信度: {anomaly_result.confidence:.2f}",
                current_value=anomaly_result.current_value,
                threshold_value=anomaly_result.baseline_value,
                timestamp=time.time(),
                metrics_data={
                    'anomaly_type': anomaly_result.anomaly_type.value,
                    'confidence': anomaly_result.confidence,
                    'baseline_value': anomaly_result.baseline_value,
                    'deviation': anomaly_result.deviation
                }
            )
            
            self.coordinator._handle_alert(alert)
        
        logger.info(f"检测到异常: {anomaly_result.metric_name} - {anomaly_result.description}")
    
    def _perform_trend_analysis(self, metric_name: str):
        """执行趋势分析"""
        trend_result = self.anomaly_detector.analyze_trend(metric_name)
        
        if trend_result:
            # 触发趋势回调
            for callback in self.trend_callbacks:
                try:
                    callback(metric_name, trend_result)
                except Exception as e:
                    logger.error(f"趋势回调执行失败: {e}")
            
            logger.debug(f"趋势分析: {metric_name} - {trend_result.direction.value} (置信度: {trend_result.confidence:.2f})")
    
    def _perform_comprehensive_analysis(self, current_metrics: UnifiedPerformanceMetrics, timestamp: float):
        """执行综合分析"""
        # 整体性能评分变化
        if hasattr(self, '_last_overall_score'):
            score_change = current_metrics.overall_performance_score - self._last_overall_score
            
            if abs(score_change) > 0.1:  # 显著变化
                logger.info(f"整体性能评分变化: {score_change:+.2f}")
        
        self._last_overall_score = current_metrics.overall_performance_score
        
        # 系统健康状态评估
        self._assess_system_health(current_metrics)
    
    def _assess_system_health(self, metrics: UnifiedPerformanceMetrics):
        """评估系统健康状态"""
        health_indicators = []
        
        # GPU健康检查
        if metrics.gpu_metrics:
            if metrics.gpu_metrics.gpu_status.value == "error":
                health_indicators.append("GPU错误")
            elif metrics.gpu_metrics.gpu_memory_utilization > 0.95:
                health_indicators.append("GPU内存不足")
        
        # 内存健康检查
        if metrics.memory_metrics:
            if metrics.memory_metrics.memory_status.value == "critical":
                health_indicators.append("内存严重不足")
            elif metrics.memory_metrics.memory_leak_detection > 0.2:
                health_indicators.append("疑似内存泄漏")
        
        # 线程健康检查
        if metrics.thread_metrics:
            if metrics.thread_metrics.thread_status.value == "deadlocked":
                health_indicators.append("线程死锁")
            elif metrics.thread_metrics.deadlock_risk_level > 0.7:
                health_indicators.append("死锁风险高")
        
        if health_indicators:
            logger.warning(f"系统健康问题: {', '.join(health_indicators)}")
    
    def get_realtime_status(self) -> Dict[str, Any]:
        """获取实时状态"""
        return {
            'monitoring_active': self.monitoring_active,
            'metrics_count': len(self.realtime_metrics),
            'last_updates': {
                name: time.time() - timestamp 
                for name, timestamp in self.last_update_time.items()
            },
            'anomaly_statistics': dict(self.anomaly_stats),
            'alert_statistics': dict(self.alert_stats),
            'recent_anomalies': len([a for a in self.coordinator.active_alerts.values() 
                                   if time.time() - a.timestamp < 300]),
            'system_health_score': getattr(self, '_last_overall_score', 1.0)
        }
    
    def stop_enhanced_monitoring(self):
        """停止增强监控"""
        if not self.monitoring_active:
            logger.warning("增强监控未运行")
            return
        
        try:
            logger.info("停止增强版实时监控...")
            
            self.monitoring_active = False
            self.stop_event.set()
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=3.0)
            
            logger.info("增强版实时监控已停止")
            
        except Exception as e:
            logger.error(f"停止增强监控失败: {e}")

# 全局增强监控实例
_global_enhanced_monitor = None

def get_enhanced_realtime_monitor() -> EnhancedRealtimeMonitor:
    """获取全局增强监控实例"""
    global _global_enhanced_monitor
    if _global_enhanced_monitor is None:
        coordinator = get_unified_performance_coordinator()
        _global_enhanced_monitor = EnhancedRealtimeMonitor(coordinator)
    return _global_enhanced_monitor