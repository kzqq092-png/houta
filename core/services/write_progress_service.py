"""
写入进度跟踪服务实现

负责跟踪写入进度、计算统计信息、监控性能指标。
"""

import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger

from core.services.realtime_write_interfaces import IWriteProgressService
from core.events.realtime_write_events import WriteProgressEvent
from core.events import get_event_bus


@dataclass
class ProgressMetrics:
    """进度指标"""
    task_id: str
    total_count: int
    written_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    start_time: datetime = None
    last_update_time: datetime = None
    symbol_times: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.last_update_time is None:
            self.last_update_time = datetime.now()
    
    def calculate_progress(self) -> float:
        """计算进度百分比"""
        if self.total_count == 0:
            return 0.0
        return min(100.0, (self.written_count / self.total_count) * 100)
    
    def calculate_write_speed(self) -> float:
        """计算写入速度（条/秒）"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        return self.written_count / elapsed
    
    def calculate_eta(self) -> float:
        """计算预计完成时间（秒）"""
        speed = self.calculate_write_speed()
        if speed == 0:
            return -1.0
        remaining = self.total_count - self.written_count
        return remaining / speed if remaining > 0 else 0.0


class WriteProgressService(IWriteProgressService):
    """
    写入进度跟踪服务实现
    
    负责跟踪写入进度、计算统计信息、监控性能指标。
    """
    
    def __init__(self):
        """初始化进度跟踪服务"""
        self.metrics: Dict[str, ProgressMetrics] = {}
        self.metrics_lock = threading.Lock()
        self.event_bus = get_event_bus()
        
        logger.info("WriteProgressService初始化完成")
    
    def start_tracking(self, task_id: str, total_count: int) -> bool:
        """开始跟踪进度"""
        try:
            with self.metrics_lock:
                if task_id in self.metrics:
                    logger.warning(f"进度跟踪 {task_id} 已存在")
                    return False
                
                metrics = ProgressMetrics(
                    task_id=task_id,
                    total_count=total_count
                )
                self.metrics[task_id] = metrics
                
            logger.info(f"开始跟踪进度: {task_id}, 总数: {total_count}")
            return True
            
        except Exception as e:
            logger.error(f"启动进度跟踪失败: {e}")
            return False
    
    def update_progress(self, task_id: str, symbol: str,
                       written_count: int, success_count: int,
                       failure_count: int) -> Dict[str, Any]:
        """
        更新进度
        
        Returns:
            进度统计信息
        """
        try:
            with self.metrics_lock:
                if task_id not in self.metrics:
                    logger.warning(f"进度跟踪 {task_id} 不存在")
                    return {}
                
                metrics = self.metrics[task_id]
                metrics.written_count = written_count
                metrics.success_count = success_count
                metrics.failure_count = failure_count
                metrics.last_update_time = datetime.now()
                
                # 记录符号写入时间
                if symbol not in metrics.symbol_times:
                    metrics.symbol_times[symbol] = time.time()
            
            # 发布进度事件
            progress = metrics.calculate_progress()
            write_speed = metrics.calculate_write_speed()
            
            event = WriteProgressEvent(
                task_id=task_id,
                symbol=symbol,
                progress=progress,
                written_count=written_count,
                total_count=metrics.total_count,
                write_speed=write_speed,
                success_count=success_count,
                failure_count=failure_count
            )
            self.event_bus.publish(event)
            
            # 返回统计信息
            return {
                'task_id': task_id,
                'symbol': symbol,
                'progress': progress,
                'written_count': written_count,
                'total_count': metrics.total_count,
                'write_speed': write_speed,
                'success_count': success_count,
                'failure_count': failure_count,
                'eta': metrics.calculate_eta(),
            }
            
        except Exception as e:
            logger.error(f"更新进度失败: {e}")
            return {}
    
    def get_progress(self, task_id: str) -> Dict[str, Any]:
        """获取当前进度"""
        try:
            with self.metrics_lock:
                if task_id not in self.metrics:
                    return {}
                
                metrics = self.metrics[task_id]
                return {
                    'task_id': task_id,
                    'progress': metrics.calculate_progress(),
                    'written_count': metrics.written_count,
                    'total_count': metrics.total_count,
                    'success_count': metrics.success_count,
                    'failure_count': metrics.failure_count,
                    'write_speed': metrics.calculate_write_speed(),
                    'eta': metrics.calculate_eta(),
                    'elapsed_time': (datetime.now() - metrics.start_time).total_seconds(),
                }
                
        except Exception as e:
            logger.error(f"获取进度失败: {e}")
            return {}
    
    def get_statistics(self, task_id: str) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            with self.metrics_lock:
                if task_id not in self.metrics:
                    return {}
                
                metrics = self.metrics[task_id]
                elapsed = (datetime.now() - metrics.start_time).total_seconds()
                
                return {
                    'task_id': task_id,
                    'total_count': metrics.total_count,
                    'written_count': metrics.written_count,
                    'success_count': metrics.success_count,
                    'failure_count': metrics.failure_count,
                    'success_rate': (metrics.success_count / metrics.written_count * 100) if metrics.written_count > 0 else 0,
                    'failure_rate': (metrics.failure_count / metrics.written_count * 100) if metrics.written_count > 0 else 0,
                    'average_speed': metrics.calculate_write_speed(),
                    'elapsed_time': elapsed,
                    'symbol_count': len(metrics.symbol_times),
                }
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def complete_tracking(self, task_id: str) -> Dict[str, Any]:
        """完成进度跟踪，返回最终统计"""
        try:
            with self.metrics_lock:
                if task_id not in self.metrics:
                    return {}
                
                metrics = self.metrics[task_id]
                elapsed = (datetime.now() - metrics.start_time).total_seconds()
                
                result = {
                    'task_id': task_id,
                    'total_count': metrics.total_count,
                    'written_count': metrics.written_count,
                    'success_count': metrics.success_count,
                    'failure_count': metrics.failure_count,
                    'success_rate': (metrics.success_count / metrics.written_count * 100) if metrics.written_count > 0 else 0,
                    'failure_rate': (metrics.failure_count / metrics.written_count * 100) if metrics.written_count > 0 else 0,
                    'average_speed': metrics.calculate_write_speed(),
                    'total_time': elapsed,
                    'symbol_count': len(metrics.symbol_times),
                }
                
                # 移除任务的跟踪信息
                del self.metrics[task_id]
                
                logger.info(f"完成进度跟踪: {task_id}, 统计信息: {result}")
                return result
                
        except Exception as e:
            logger.error(f"完成进度跟踪失败: {e}")
            return {}
    
    def clear_all(self) -> None:
        """清除所有跟踪信息"""
        with self.metrics_lock:
            self.metrics.clear()
            logger.info("已清除所有进度跟踪信息")
