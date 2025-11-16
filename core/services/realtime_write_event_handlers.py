"""
实时写入事件处理器

定义了对实时写入事件的处理逻辑。
这些处理器被注册到EventBus中，用于处理UI更新、日志记录、监控触发等。
"""

from typing import Optional, Dict, Any
from loguru import logger
from datetime import datetime

from core.events.realtime_write_events import (
    WriteStartedEvent, WriteProgressEvent, WriteCompletedEvent, WriteErrorEvent
)


class RealtimeWriteEventHandlers:
    """
    实时写入事件处理器集合
    
    包含对四种实时写入事件的处理逻辑。
    """
    
    def __init__(self, ui_callback=None, monitoring_callback=None):
        """
        初始化事件处理器
        
        Args:
            ui_callback: UI更新回调函数
            monitoring_callback: 监控触发回调函数
        """
        self.ui_callback = ui_callback
        self.monitoring_callback = monitoring_callback
        self.task_statistics: Dict[str, Any] = {}
        
        logger.info("RealtimeWriteEventHandlers初始化完成")
    
    def on_write_started(self, event: WriteStartedEvent) -> None:
        """处理写入开始事件"""
        try:
            logger.info(f"[写入开始] 任务={event.task_id}, 名称={event.task_name}, "
                       f"股票数={len(event.symbols)}, 总记录数={event.total_records}")
            
            # 初始化任务统计
            self.task_statistics[event.task_id] = {
                'task_id': event.task_id,
                'task_name': event.task_name,
                'symbols': event.symbols,
                'total_records': event.total_records,
                'start_time': event.timestamp,
                'status': 'started'
            }
            
            # 触发UI更新回调
            if self.ui_callback:
                self.ui_callback(event_type='write_started', event=event)
            
            # 触发监控回调
            if self.monitoring_callback:
                self.monitoring_callback(event_type='write_started', event=event)
                
        except Exception as e:
            logger.error(f"处理写入开始事件失败: {e}")
    
    def on_write_progress(self, event: WriteProgressEvent) -> None:
        """处理写入进度事件"""
        try:
            # 每N条消息输出一次日志，避免日志过多
            if event.written_count % 100 == 0 or event.written_count == event.total_count:
                logger.info(f"[写入进度] 任务={event.task_id}, 股票={event.symbol}, "
                           f"进度={event.progress:.1f}%, 已写={event.written_count}/{event.total_count}, "
                           f"速度={event.write_speed:.0f}条/秒, 成功={event.success_count}, "
                           f"失败={event.failure_count}")
            
            # 更新任务统计
            if event.task_id in self.task_statistics:
                self.task_statistics[event.task_id].update({
                    'latest_symbol': event.symbol,
                    'progress': event.progress,
                    'written_count': event.written_count,
                    'total_count': event.total_count,
                    'write_speed': event.write_speed,
                    'success_count': event.success_count,
                    'failure_count': event.failure_count,
                    'last_update_time': event.timestamp,
                    'status': event.status
                })
            
            # 触发UI更新回调
            if self.ui_callback:
                self.ui_callback(event_type='write_progress', event=event)
            
            # 定期触发监控回调（每处理1000条记录触发一次）
            if event.written_count % 1000 == 0 and self.monitoring_callback:
                self.monitoring_callback(event_type='write_progress', event=event)
                
        except Exception as e:
            logger.error(f"处理写入进度事件失败: {e}")
    
    def on_write_completed(self, event: WriteCompletedEvent) -> None:
        """处理写入完成事件"""
        try:
            logger.info(f"[写入完成] 任务={event.task_id}, "
                       f"总符号={event.total_symbols}, "
                       f"成功={event.success_count}, "
                       f"失败={event.failure_count}, "
                       f"总记录={event.total_records}, "
                       f"耗时={event.duration:.2f}秒, "
                       f"平均速度={event.average_speed:.0f}条/秒")
            
            # 更新任务统计
            if event.task_id in self.task_statistics:
                self.task_statistics[event.task_id].update({
                    'total_symbols': event.total_symbols,
                    'success_count': event.success_count,
                    'failure_count': event.failure_count,
                    'total_records': event.total_records,
                    'duration': event.duration,
                    'average_speed': event.average_speed,
                    'end_time': event.timestamp,
                    'status': 'completed'
                })
            
            # 计算成功率
            total_count = event.success_count + event.failure_count
            success_rate = (event.success_count / total_count * 100) if total_count > 0 else 0
            
            logger.info(f"[写入统计] 成功率={success_rate:.2f}%, 平均每条耗时={event.duration*1000/event.total_records:.2f}ms")
            
            # 触发UI更新回调
            if self.ui_callback:
                self.ui_callback(event_type='write_completed', event=event)
            
            # 触发监控回调
            if self.monitoring_callback:
                self.monitoring_callback(event_type='write_completed', event=event)
                
        except Exception as e:
            logger.error(f"处理写入完成事件失败: {e}")
    
    def on_write_error(self, event: WriteErrorEvent) -> None:
        """处理写入错误事件"""
        try:
            logger.error(f"[写入错误] 任务={event.task_id}, "
                        f"股票={event.symbol}, "
                        f"错误类型={event.error_type}, "
                        f"错误信息={event.error}, "
                        f"重试次数={event.retry_count}")
            
            # 更新任务统计（如果存在）
            if event.task_id in self.task_statistics:
                if 'errors' not in self.task_statistics[event.task_id]:
                    self.task_statistics[event.task_id]['errors'] = []
                
                self.task_statistics[event.task_id]['errors'].append({
                    'symbol': event.symbol,
                    'error': event.error,
                    'error_type': event.error_type,
                    'retry_count': event.retry_count,
                    'timestamp': event.timestamp,
                    'details': event.error_details
                })
            
            # 触发UI更新回调
            if self.ui_callback:
                self.ui_callback(event_type='write_error', event=event)
            
            # 触发监控回调
            if self.monitoring_callback:
                self.monitoring_callback(event_type='write_error', event=event)
                
        except Exception as e:
            logger.error(f"处理写入错误事件失败: {e}")
    
    def get_task_statistics(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务统计信息"""
        return self.task_statistics.get(task_id)
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """获取所有任务统计信息"""
        return self.task_statistics.copy()
    
    def clear_statistics(self, task_id: str = None) -> None:
        """清除统计信息"""
        if task_id:
            if task_id in self.task_statistics:
                del self.task_statistics[task_id]
                logger.info(f"已清除任务 {task_id} 的统计信息")
        else:
            self.task_statistics.clear()
            logger.info("已清除所有统计信息")


# 创建全局事件处理器实例
_global_write_event_handlers: Optional[RealtimeWriteEventHandlers] = None


def get_write_event_handlers() -> RealtimeWriteEventHandlers:
    """获取全局事件处理器实例"""
    global _global_write_event_handlers
    if _global_write_event_handlers is None:
        _global_write_event_handlers = RealtimeWriteEventHandlers()
    return _global_write_event_handlers


def set_write_event_handlers(handlers: RealtimeWriteEventHandlers) -> None:
    """设置全局事件处理器实例"""
    global _global_write_event_handlers
    _global_write_event_handlers = handlers
