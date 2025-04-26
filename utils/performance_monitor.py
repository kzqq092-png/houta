"""
性能监控模块

提供系统性能监控和优化功能
"""

import os
import time
import psutil
import threading
import traceback
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from .config_types import PerformanceConfig
from contextlib import contextmanager

class PerformanceMonitor(QObject):
    """性能监控器，用于监控系统性能指标"""
    
    # 定义信号
    performance_updated = pyqtSignal(dict)
    alert_triggered = pyqtSignal(str)
    
    def __init__(self, config=None):
        """初始化性能监控器
        
        Args:
            config: 性能监控配置
        """
        super().__init__()
        self.config = config
        self.logger = None
        self.timer = None
        self.process = psutil.Process()
        
        # 获取CPU核心数
        self.cpu_count = psutil.cpu_count(logical=True)
        
        # 设置默认阈值
        self.cpu_threshold = getattr(self.config, 'cpu_threshold', 80)
        self.memory_threshold = getattr(self.config, 'memory_threshold', 80)
        self.response_threshold = getattr(self.config, 'response_threshold', 5)
        self.disk_threshold = getattr(self.config, 'disk_threshold', 90)
        
        # 初始化阈值字典
        self.thresholds = {
            'cpu_usage': self.cpu_threshold,
            'memory_usage': self.memory_threshold,
            'disk_usage': self.disk_threshold,
            'response_time': self.response_threshold
        }
        
        # 初始化性能历史数据
        self.history = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'response': []
        }
        
        # 初始化性能指标
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'memory_used': [],
            'response_times': {},
            'exceptions': [],
            'operation_times': {},
            'disk_usage': []
        }
        
        # 初始化CPU使用率计算所需的变量
        self._last_cpu_times = None
        self._last_time = None
        
        # 初始化停止事件
        self._stop_event = threading.Event()
        self._stop_event.set()
        
        # 初始化更新定时器
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_metrics)
        
    def set_logger(self, logger):
        """设置日志管理器
        
        Args:
            logger: 日志管理器实例
        """
        self.logger = logger
        
    def start_monitoring(self):
        """启动性能监控"""
        if not self._stop_event.is_set():
            return
            
        self._stop_event.clear()
        
        # 创建监控线程
        self._monitor_thread = threading.Thread(target=self._monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
        # 启动定时器
        if self.timer is None:
            self.timer = QTimer()
            self.timer.timeout.connect(self._check_performance)
            self.timer.start(int(getattr(self.config, 'update_interval', 1.0) * 1000))
            
        # 启动更新定时器
        self._update_timer.start(int(getattr(self.config, 'update_interval', 1.0) * 1000))
        
        if self.logger:
            self.logger.info("性能监控已启动")
            
    def stop_monitoring(self):
        """停止性能监控"""
        # 停止监控线程
        self._stop_event.set()
        if hasattr(self, '_monitor_thread'):
            self._monitor_thread.join()
            
        # 停止定时器
        if self.timer is not None:
            self.timer.stop()
            self.timer = None
            
        # 停止更新定时器
        self._update_timer.stop()
        
        if self.logger:
            self.logger.info("性能监控已停止")
            
    def _calculate_cpu_usage(self) -> float:
        """计算CPU使用率
        
        Returns:
            float: CPU使用率（0-100）
        """
        try:
            # 获取当前进程的 CPU 时间
            cpu_times = self.process.cpu_times()
            current_time = time.time()
            
            if self._last_cpu_times is None or self._last_time is None:
                self._last_cpu_times = cpu_times
                self._last_time = current_time
                return 0.0
                
            # 计算时间差
            time_delta = current_time - self._last_time
            if time_delta <= 0:
                return 0.0
                
            # 计算 CPU 时间差
            cpu_delta = (
                (cpu_times.user - self._last_cpu_times.user) +
                (cpu_times.system - self._last_cpu_times.system)
            )
            
            # 计算 CPU 使用率（考虑多核）
            cpu_usage = (cpu_delta / time_delta) * 100 / self.cpu_count
            
            # 更新上次的值
            self._last_cpu_times = cpu_times
            self._last_time = current_time
            
            # 限制使用率范围在 0-100 之间
            return max(0.0, min(100.0, cpu_usage))
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算CPU使用率失败: {str(e)}")
            return 0.0
            
    def _check_performance(self):
        """检查系统性能"""
        try:
            # 获取CPU使用率
            cpu_percent = self._calculate_cpu_usage()
            
            # 获取内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 获取磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 获取进程响应时间
            start_time = time.time()
            self.process.cpu_percent()
            response_time = time.time() - start_time
            
            # 更新历史数据
            self.history['cpu'].append(cpu_percent)
            self.history['memory'].append(memory_percent)
            self.history['disk'].append(disk_percent)
            self.history['response'].append(response_time)
            
            # 限制历史数据长度
            max_history = getattr(self.config, 'metrics_history_size', 100)
            for key in self.history:
                if len(self.history[key]) > max_history:
                    self.history[key] = self.history[key][-max_history:]
            
            # 创建性能指标数据
            metrics = {
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'disk_usage': disk_percent,
                'response_time': response_time,
                'history': self.history,
                'total_return': 0.0,
                'response_times': {}
            }
            
            # 发送性能更新信号
            self.performance_updated.emit(metrics)
            
            # 检查性能警告
            self._check_alerts(metrics)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"性能检查失败: {str(e)}")
                
    def _check_alerts(self, metrics: dict):
        """检查性能警告
        
        Args:
            metrics: 性能指标数据
        """
        try:
            # 检查CPU使用率
            if metrics['cpu_usage'] > self.thresholds['cpu_usage']:
                self.alert_triggered.emit(
                    f"CPU使用率过高: {metrics['cpu_usage']:.1f}%"
                )
                
            # 检查内存使用率
            if metrics['memory_usage'] > self.thresholds['memory_usage']:
                self.alert_triggered.emit(
                    f"内存使用率过高: {metrics['memory_usage']:.1f}%"
                )
                
            # 检查磁盘使用率
            if metrics['disk_usage'] > self.thresholds['disk_usage']:
                self.alert_triggered.emit(
                    f"磁盘使用率过高: {metrics['disk_usage']:.1f}%"
                )
                
            # 检查响应时间
            if metrics['response_time'] > self.thresholds['response_time']:
                self.alert_triggered.emit(
                    f"系统响应时间过长: {metrics['response_time']:.2f}秒"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"检查性能警告失败: {str(e)}")
                
    def get_metrics(self) -> dict:
        """获取当前性能指标
        
        Returns:
            dict: 性能指标数据
        """
        try:
            metrics = {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'response_time': 0.0,
                'history': self.history,
                'total_return': 0.0,  # 添加默认值
                'response_times': {},  # 添加默认值
            }
            
            # 添加性能历史数据
            if hasattr(self, 'metrics'):
                metrics.update({
                    'operation_times': self.metrics.get('operation_times', {}),
                    'exceptions': self.metrics.get('exceptions', []),
                    'memory_used': self.metrics.get('memory_used', [])
                })
                
            return metrics
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取性能指标失败: {str(e)}")
            return {
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'disk_usage': 0.0,
                'response_time': 0.0,
                'history': {},
                'total_return': 0.0,
                'response_times': {}
            }
        
    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(__name__)
        
    def _check_warnings(self, metrics: Dict[str, Any]):
        """检查性能警告"""
        try:
            # CPU使用率警告
            if metrics['cpu_usage'] > self.config.get('cpu_threshold', 80):
                warning = f"CPU使用率过高: {metrics['cpu_usage']}%"
                self.logger.warning(warning)
                self.alert_triggered.emit(warning)
                
            # 内存使用率警告
            if metrics['memory_usage'] > self.config.get('memory_threshold', 80):
                warning = f"内存使用率过高: {metrics['memory_usage']}%"
                self.logger.warning(warning)
                self.alert_triggered.emit(warning)
                
            # 磁盘使用率警告
            if metrics['disk_usage'] > self.config.get('disk_threshold', 90):
                warning = f"磁盘使用率过高: {metrics['disk_usage']}%"
                self.logger.warning(warning)
                self.alert_triggered.emit(warning)
                
            # 响应时间警告
            if metrics['response_time'] > self.config.get('response_threshold', 1.0):
                warning = f"响应时间过长: {metrics['response_time']:.2f}秒"
                self.logger.warning(warning)
                self.alert_triggered.emit(warning)
                
        except Exception as e:
            self.logger.error(f"检查性能警告失败: {str(e)}")
            
    def _monitor_loop(self):
        """监控循环，收集性能指标"""
        while not self._stop_event.is_set():
            try:
                # 收集CPU使用率
                if self.config.monitor_cpu:
                    cpu_percent = self.process.cpu_percent()
                    self.metrics['cpu_usage'].append({
                        'time': datetime.now(),
                        'value': cpu_percent
                    })
                    
                    if cpu_percent > self.thresholds['cpu_usage']:
                        self._trigger_alert(f"CPU使用率过高: {cpu_percent:.1f}%")
                        
                # 收集内存使用情况
                if self.config.monitor_memory:
                    memory_info = self.process.memory_info()
                    memory_percent = memory_info.rss / psutil.virtual_memory().total * 100
                    self.metrics['memory_usage'].append({
                        'time': datetime.now(),
                        'value': memory_percent
                    })
                    self.metrics['memory_used'].append({
                        'time': datetime.now(),
                        'value': memory_info.rss / (1024 * 1024)  # 转换为MB
                    })
                    
                    if memory_percent > self.thresholds['memory_usage']:
                        self._trigger_alert(f"内存使用率过高: {memory_percent:.1f}%")
                        
                # 收集磁盘使用情况
                disk_usage = psutil.disk_usage('/').percent
                self.metrics['disk_usage'].append({
                    'time': datetime.now(),
                    'value': disk_usage
                })
                
                if disk_usage > self.thresholds['disk_usage']:
                    self._trigger_alert(f"磁盘使用率过高: {disk_usage:.1f}%")
                
                # 修剪指标数据
                self._trim_metrics()
                
                # 等待下一次采集
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"性能监控错误: {str(e)}")
                time.sleep(1)
                
    def _update_metrics(self):
        """更新性能指标并发送信号"""
        try:
            metrics = self.get_metrics()
            self.performance_updated.emit(metrics)
        except Exception as e:
            self.logger.error(f"更新性能指标失败: {str(e)}")
            
    def _trigger_alert(self, message: str):
        """触发性能告警
        
        Args:
            message: 告警消息
        """
        self.alert_triggered.emit(message)
        self.logger.warning(message)
        
    def _trim_metrics(self):
        """修剪指标数据，只保留最近的数据"""
        for metric in self.metrics:
            if isinstance(self.metrics[metric], list):
                if len(self.metrics[metric]) > self.config.metrics_history_size:
                    self.metrics[metric] = self.metrics[metric][-self.config.metrics_history_size:]
            elif isinstance(self.metrics[metric], dict):
                for key in self.metrics[metric]:
                    if len(self.metrics[metric][key]) > self.config.metrics_history_size:
                        self.metrics[metric][key] = self.metrics[metric][key][-self.config.metrics_history_size:]
            
    @contextmanager
    def track_operation(self, operation: str):
        """跟踪操作执行时间
        
        Args:
            operation: 操作名称
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self._record_operation_time(operation, duration)
            
    def _record_operation_time(self, operation: str, duration: float):
        """记录操作执行时间
        
        Args:
            operation: 操作名称
            duration: 执行时间(秒)
        """
        if operation not in self.metrics['operation_times']:
            self.metrics['operation_times'][operation] = []
            
        self.metrics['operation_times'][operation].append({
            'time': datetime.now(),
            'value': duration
        })
        
        if duration > self.thresholds['response_time']:
            self._trigger_alert(f"操作 {operation} 执行时间过长: {duration:.2f}秒")
            
    def track_exception(self, exception: Exception, context: str = ""):
        """跟踪异常
        
        Args:
            exception: 异常对象
            context: 异常发生的上下文
        """
        self.metrics['exceptions'].append({
            'time': datetime.now(),
            'type': type(exception).__name__,
            'message': str(exception),
            'context': context
        })
        
        if self.config.log_to_file:
            self.logger.warning(f"异常发生在 {context}: {type(exception).__name__}: {str(exception)}")
            
    def get_history(self, metric: str) -> List[Dict[str, Any]]:
        """获取指标历史数据
        
        Args:
            metric: 指标名称
            
        Returns:
            指标历史数据列表
        """
        return self.metrics.get(metric, [])
        
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告
        
        Returns:
            性能报告字典
        """
        return {
            'system_metrics': self.get_metrics(),
            'operation_metrics': self.metrics['operation_times'],
            'exception_count': len(self.metrics['exceptions']),
            'uptime': time.time() - self.process.create_time()
        }
        
    def reset_metrics(self):
        """重置所有性能指标"""
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'memory_used': [],
            'response_times': {},
            'exceptions': [],
            'operation_times': {},
            'disk_usage': []
        }
        
    def set_threshold(self, metric: str, value: float):
        """设置性能阈值
        
        Args:
            metric: 指标名称
            value: 阈值
        """
        if metric == 'cpu_usage':
            self.cpu_threshold = value
            self.thresholds['cpu_usage'] = value
        elif metric == 'memory_usage':
            self.memory_threshold = value
            self.thresholds['memory_usage'] = value
        elif metric == 'disk_usage':
            self.disk_threshold = value
            self.thresholds['disk_usage'] = value
        elif metric == 'response_time':
            self.response_threshold = value
            self.thresholds['response_time'] = value
            
        # 更新配置对象
        if self.config:
            self.config.set(metric, value)
            
    def get_threshold(self, metric: str) -> Optional[float]:
        """获取性能阈值
        
        Args:
            metric: 指标名称
            
        Returns:
            阈值
        """
        return self.thresholds.get(metric)

    def check_performance(self, metrics: dict):
        """检查性能指标
        
        Args:
            metrics: 性能指标字典
        """
        try:
            # 检查CPU使用率
            if metrics.get('cpu_usage', 0) > self.thresholds['cpu_usage']:
                self.alert_triggered.emit(
                    f"CPU使用率过高: {metrics['cpu_usage']:.1f}%"
                )
                
            # 检查内存使用率
            if metrics.get('memory_usage', 0) > self.thresholds['memory_usage']:
                self.alert_triggered.emit(
                    f"内存使用率过高: {metrics['memory_usage']:.1f}%"
                )
                
            # 检查响应时间
            response_times = metrics.get('response_times', {})
            for func, time_value in response_times.items():
                if time_value > self.thresholds['response_time']:
                    self.alert_triggered.emit(
                        f"函数 {func} 响应时间过长: {time_value:.2f}秒"
                    )
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f"检查性能指标失败: {str(e)}") 