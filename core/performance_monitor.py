"""
性能监控模块

提供系统性能监控和管理功能
"""

import os
import psutil
import time
from datetime import datetime
from typing import Dict, Optional, List
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from utils import PerformanceConfig

class PerformanceMetrics:
    """性能指标数据类"""
    def __init__(self):
        self.cpu_percent: float = 0.0
        self.memory_percent: float = 0.0
        self.memory_used: float = 0.0
        self.memory_total: float = 0.0
        self.disk_usage: float = 0.0
        self.response_time: float = 0.0
        self.exception_count: int = 0
        self.timestamp: datetime = datetime.now()

class PerformanceMonitor(QObject):
    """性能监控器"""
    
    # 定义信号
    metrics_updated = pyqtSignal(object)  # 性能指标更新信号
    alert_triggered = pyqtSignal(str)  # 性能告警信号
    
    def __init__(self, config: Optional[PerformanceConfig] = None):
        """初始化性能监控器
        
        Args:
            config: 性能监控配置对象
        """
        super().__init__()
        
        # 使用默认配置
        self.config = config or PerformanceConfig()
        
        # 初始化性能指标
        self.metrics = PerformanceMetrics()
        self.process = psutil.Process(os.getpid())
        
        # 初始化定时器
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_metrics)
        
        # 初始化异常计数
        self._exception_count = 0
        
        # 初始化响应时间记录
        self._response_times: List[float] = []
        
    def start(self):
        """启动性能监控"""
        try:
            # 设置更新间隔
            interval = self.config.update_interval * 1000  # 转换为毫秒
            self._update_timer.start(interval)
            
        except Exception as e:
            print(f"启动性能监控失败: {str(e)}")
            
    def stop(self):
        """停止性能监控"""
        try:
            self._update_timer.stop()
        except Exception as e:
            print(f"停止性能监控失败: {str(e)}")
            
    def _update_metrics(self):
        """更新性能指标"""
        try:
            # 更新CPU使用率
            self.metrics.cpu_percent = self.process.cpu_percent()
            
            # 更新内存使用情况
            memory_info = self.process.memory_info()
            self.metrics.memory_used = memory_info.rss / 1024 / 1024  # 转换为MB
            self.metrics.memory_total = psutil.virtual_memory().total / 1024 / 1024
            self.metrics.memory_percent = self.process.memory_percent()
            
            # 更新磁盘使用率
            self.metrics.disk_usage = psutil.disk_usage('/').percent
            
            # 更新响应时间
            if self._response_times:
                self.metrics.response_time = sum(self._response_times) / len(self._response_times)
                self._response_times = []
            
            # 更新异常计数
            self.metrics.exception_count = self._exception_count
            
            # 更新时间戳
            self.metrics.timestamp = datetime.now()
            
            # 发送指标更新信号
            self.metrics_updated.emit(self.metrics)
            
            # 检查性能告警
            self._check_alerts()
            
        except Exception as e:
            print(f"更新性能指标失败: {str(e)}")
            
    def _check_alerts(self):
        """检查性能告警"""
        try:
            # 检查CPU使用率
            if self.metrics.cpu_percent > self.config.cpu_threshold:
                self.alert_triggered.emit(
                    f"CPU使用率过高: {self.metrics.cpu_percent:.1f}%"
                )
                
            # 检查内存使用率
            if self.metrics.memory_percent > self.config.memory_threshold:
                self.alert_triggered.emit(
                    f"内存使用率过高: {self.metrics.memory_percent:.1f}%"
                )
                
            # 检查磁盘使用率
            if self.metrics.disk_usage > self.config.disk_threshold:
                self.alert_triggered.emit(
                    f"磁盘使用率过高: {self.metrics.disk_usage:.1f}%"
                )
                
            # 检查响应时间
            if (self.metrics.response_time > 0 and 
                self.metrics.response_time > self.config.response_threshold):
                self.alert_triggered.emit(
                    f"响应时间过长: {self.metrics.response_time:.2f}秒"
                )
                
        except Exception as e:
            print(f"检查性能告警失败: {str(e)}")
            
    def record_response_time(self, response_time: float):
        """记录响应时间
        
        Args:
            response_time: 响应时间(秒)
        """
        try:
            self._response_times.append(response_time)
        except Exception as e:
            print(f"记录响应时间失败: {str(e)}")
            
    def record_exception(self):
        """记录异常"""
        try:
            self._exception_count += 1
        except Exception as e:
            print(f"记录异常失败: {str(e)}")
            
    def reset_exception_count(self):
        """重置异常计数"""
        try:
            self._exception_count = 0
        except Exception as e:
            print(f"重置异常计数失败: {str(e)}")
            
    def get_metrics(self) -> Dict:
        """获取当前性能指标
        
        Returns:
            性能指标字典
        """
        try:
            return {
                'cpu_percent': self.metrics.cpu_percent,
                'memory_percent': self.metrics.memory_percent,
                'memory_used': self.metrics.memory_used,
                'memory_total': self.metrics.memory_total,
                'disk_usage': self.metrics.disk_usage,
                'response_time': self.metrics.response_time,
                'exception_count': self.metrics.exception_count,
                'timestamp': self.metrics.timestamp.isoformat()
            }
        except Exception as e:
            print(f"获取性能指标失败: {str(e)}")
            return {} 