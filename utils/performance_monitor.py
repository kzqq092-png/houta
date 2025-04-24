"""
性能监控模块

提供系统性能监控和优化功能
"""

import os
import time
import psutil
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from .config_types import PerformanceConfig
from core.logger import LogManager, LogLevel

class PerformanceMonitor(QObject):
    """性能监控器"""
    
    performance_updated = pyqtSignal(dict)  # 性能数据更新信号
    
    def __init__(self, config: Optional[PerformanceConfig] = None, log_manager: Optional[LogManager] = None):
        """初始化性能监控器
        
        Args:
            config: 性能监控配置
            log_manager: 日志管理器实例
        """
        super().__init__()
        self.config = config or PerformanceConfig()
        self.log_manager = log_manager or LogManager()
        
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'response_times': {},
            'exceptions': []
        }
        
        self.process = psutil.Process(os.getpid())
        self._stop_event = threading.Event()
        
        if self.config.enable_monitoring:
            self.start_monitoring()
            
    def start_monitoring(self):
        """Start performance monitoring"""
        if not self._stop_event.is_set():
            return
            
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self._stop_event.set()
        if hasattr(self, '_monitor_thread'):
            self._monitor_thread.join()
            
    def _monitor_loop(self):
        """Monitor loop for collecting metrics"""
        while not self._stop_event.is_set():
            try:
                # Collect CPU usage
                if self.config.enable_monitoring:
                    cpu_percent = self.process.cpu_percent()
                    self.metrics['cpu_usage'].append({
                        'time': datetime.now(),
                        'value': cpu_percent
                    })
                    
                    if cpu_percent > self.config.cpu_threshold:
                        self.log_manager.log(
                            f"High CPU usage: {cpu_percent}%",
                            "warning"
                        )
                        
                # Collect memory usage
                if self.config.enable_monitoring:
                    memory_info = self.process.memory_info()
                    memory_percent = memory_info.rss / psutil.virtual_memory().total * 100
                    self.metrics['memory_usage'].append({
                        'time': datetime.now(),
                        'value': memory_percent
                    })
                    
                    if memory_percent > self.config.memory_threshold:
                        self.log_manager.log(
                            f"High memory usage: {memory_percent:.1f}%",
                            "warning"
                        )
            
                # Trim metrics if needed
                if len(self.metrics['cpu_usage']) > self.config.metrics_history_size:
                    self._trim_metrics()
                
                # Wait for next collection
                time.sleep(1)  # 每秒采集一次数据
                
            except Exception as e:
                self.log_manager.log(f"Error in performance monitoring: {str(e)}", "error")
                if self.config.log_to_file:
                    self.log_manager.log_to_file(str(e), self.config.log_file)
                time.sleep(1)
                
    def _trim_metrics(self):
        """Trim metrics to keep only recent data"""
        # Trim CPU usage
        if len(self.metrics['cpu_usage']) > self.config.metrics_history_size:
            self.metrics['cpu_usage'] = self.metrics['cpu_usage'][-self.config.metrics_history_size:]
        
        # Trim memory usage
        if len(self.metrics['memory_usage']) > self.config.metrics_history_size:
            self.metrics['memory_usage'] = self.metrics['memory_usage'][-self.config.metrics_history_size:]
        
        # Trim response times
        for func in list(self.metrics['response_times'].keys()):
            if len(self.metrics['response_times'][func]) > self.config.metrics_history_size:
                self.metrics['response_times'][func] = self.metrics['response_times'][func][-self.config.metrics_history_size:]
            
        # Trim exceptions - keep all exceptions but limit to history size
        if len(self.metrics['exceptions']) > self.config.metrics_history_size:
            self.metrics['exceptions'] = self.metrics['exceptions'][-self.config.metrics_history_size:]
        
    def track_time(self, func_name: str) -> float:
        """Track function execution time
        
        Args:
            func_name: Function name to track
            
        Returns:
            Execution time in seconds
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not self.config.enable_monitoring:
                    return func(*args, **kwargs)
                    
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Record execution time
                    if func_name not in self.metrics['response_times']:
                        self.metrics['response_times'][func_name] = []
                    self.metrics['response_times'][func_name].append({
                        'time': datetime.now(),
                        'value': execution_time
                    })
            
                    # Check threshold
                    if execution_time > self.config.response_threshold:
                        self.log_manager.log(
                            f"Slow execution of {func_name}: {execution_time:.2f}s (threshold: {self.config.response_threshold}s)",
                            "warning"
                        )
                        if self.config.log_to_file:
                            self.log_manager.log_to_file(
                                f"Slow execution of {func_name}: {execution_time:.2f}s",
                                self.config.log_file
                            )
                            
                    return result
                    
                except Exception as e:
                    if self.config.enable_monitoring:
                        self.track_exception(e, func_name)
                    raise
                    
            return wrapper
        return decorator
            
    def track_exception(self, exception: Exception, context: str = ""):
        """Track exception
        
        Args:
            exception: Exception to track
            context: Context where exception occurred
        """
        if not self.config.enable_monitoring:
            return
            
        self.metrics['exceptions'].append({
            'time': datetime.now(),
            'type': type(exception).__name__,
            'message': str(exception),
            'context': context
        })
        
        if self.config.log_to_file:
            self.log_manager.log_to_file(
                f"Exception in {context}: {type(exception).__name__}: {str(exception)}",
                self.config.log_file
            )
                
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics
        
        Returns:
            Dictionary containing current metrics
        """
        return {
            'cpu_usage': self.metrics['cpu_usage'][-1]['value'] if self.metrics['cpu_usage'] else 0,
            'memory_usage': self.metrics['memory_usage'][-1]['value'] if self.metrics['memory_usage'] else 0,
            'response_times': {
                func: times[-1]['value']
                for func, times in self.metrics['response_times'].items()
                if times
            },
            'exceptions': len(self.metrics['exceptions'])
        }
        
    def get_history(self, metric: str) -> List[Dict[str, Any]]:
        """Get metric history
        
        Args:
            metric: Metric name to get history for
            
        Returns:
            List of metric values with timestamps
        """
        return self.metrics.get(metric, [])

    def get_performance_data(self) -> Dict[str, Any]:
        """获取性能数据
        
        Returns:
            包含性能数据的字典
        """
        try:
            # 获取当前系统资源使用情况
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_percent = memory_info.rss / psutil.virtual_memory().total * 100
            
            # 获取历史数据
            cpu_history = [m['value'] for m in self.metrics['cpu_usage'][-60:]]  # 最近60个数据点
            memory_history = [m['value'] for m in self.metrics['memory_usage'][-60:]]
            
            # 计算平均响应时间
            avg_response_times = {}
            for func, times in self.metrics['response_times'].items():
                if times:
                    avg_response_times[func] = sum(t['value'] for t in times[-10:]) / len(times[-10:])
            
            return {
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'cpu_history': cpu_history,
                'memory_history': memory_history,
                'response_times': avg_response_times,
                'exception_count': len(self.metrics['exceptions'])
            }
            
        except Exception as e:
            self.log_manager.log(f"获取性能数据失败: {str(e)}", "error")
            return {
                'cpu_usage': 0,
                'memory_usage': 0,
                'cpu_history': [],
                'memory_history': [],
                'response_times': {},
                'exception_count': 0
            } 