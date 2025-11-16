"""
实时写入服务实现

核心实时写入业务逻辑服务，负责协调数据写入过程。
基于现有ImportExecutionEngine和AssetSeparatedDatabaseManager增强。
"""

import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
import pandas as pd
from loguru import logger

from core.services.realtime_write_interfaces import IRealtimeWriteService
from core.services.realtime_write_config import RealtimeWriteConfig, WriteStrategy
from core.events.realtime_write_events import (
    WriteStartedEvent, WriteProgressEvent, WriteCompletedEvent, WriteErrorEvent
)
from core.events import get_event_bus


@dataclass
class WriteTaskState:
    """写入任务状态"""
    task_id: str
    status: str                    # running, paused, completed, failed
    total_symbols: int
    written_symbols: int = 0
    success_count: int = 0
    failure_count: int = 0
    start_time: datetime = None
    pause_time: Optional[datetime] = None
    total_records: int = 0
    written_records: int = 0
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()


class RealtimeWriteService(IRealtimeWriteService):
    """
    实时写入服务实现
    
    负责协调数据写入过程，包括：
    - 数据写入控制
    - 进度跟踪
    - 事件发布
    - 错误处理
    """
    
    def __init__(self, config: RealtimeWriteConfig = None):
        """
        初始化实时写入服务
        
        Args:
            config: 写入配置
        """
        try:
            self.config = config or RealtimeWriteConfig()
            self.config.validate()
            
            self.event_bus = get_event_bus()
            if self.event_bus is None:
                logger.warning("EventBus未初始化，使用None")
            
            # 任务状态管理
            self.tasks: Dict[str, WriteTaskState] = {}
            self.task_lock = threading.Lock()
            
            # 导入必要的数据库管理器
            self.asset_manager = None
            self._initialize_asset_manager()
            
            logger.info(f"RealtimeWriteService初始化完成，配置: {self.config.to_dict()}")
        except Exception as init_error:
            logger.error(f"RealtimeWriteService初始化失败: {init_error}")
            raise
    
    def _initialize_asset_manager(self):
        """初始化资产数据库管理器"""
        try:
            from core.asset_database_manager import AssetSeparatedDatabaseManager
            self.asset_manager = AssetSeparatedDatabaseManager()
            logger.debug("资产数据库管理器初始化成功")
        except Exception as e:
            logger.error(f"资产数据库管理器初始化失败: {e}")
    
    def start_write(self, task_id: str, config: Dict[str, Any] = None) -> bool:
        """开始实时写入任务"""
        try:
            with self.task_lock:
                if task_id in self.tasks:
                    logger.warning(f"任务 {task_id} 已存在")
                    return False
                
                # 创建任务状态
                state = WriteTaskState(
                    task_id=task_id,
                    status="running",
                    total_symbols=0
                )
                self.tasks[task_id] = state
            
            logger.info(f"开始实时写入任务: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"启动写入任务失败: {e}")
            return False
    
    def write_data(self, symbol: str, data: pd.DataFrame,
                   asset_type: str = "STOCK_A", data_source: str = "unknown") -> bool:
        """
        写入数据
        
        Args:
            symbol: 股票代码
            data: 数据DataFrame
            asset_type: 资产类型
            data_source: 数据来源（【改进】添加此参数以保留数据血缘）
            
        Returns:
            是否写入成功
        """
        if data is None or data.empty:
            logger.warning(f"数据为空，跳过写入: {symbol}")
            return False
        
        # 【改进】验证和传递 data_source
        if not data_source or data_source == 'unknown':
            logger.warning(f"data_source 为空或无效: {data_source}，symbol: {symbol}")
        
        try:
            start_time = time.time()
            
            # 使用资产数据库管理器写入数据
            if self.asset_manager:
                from core.plugin_types import AssetType, DataType
                
                # 转换资产类型
                asset_type_enum = self._convert_asset_type(asset_type)
                
                # 【改进】确保数据中包含 data_source 列
                data_to_write = data.copy()
                if 'data_source' not in data_to_write.columns:
                    data_to_write['data_source'] = data_source
                    logger.debug(f"添加 data_source 列: {data_source}")
                
                # 写入数据
                success = self.asset_manager.store_standardized_data(
                    data=data_to_write,
                    asset_type=asset_type_enum,
                    data_type=DataType.HISTORICAL_KLINE
                )
                
                if success:
                    write_time = time.time() - start_time
                    write_speed = len(data) / write_time if write_time > 0 else 0
                    
                    logger.info(f"成功写入 {symbol}: {len(data)} 条记录，耗时 {write_time:.2f}秒，"
                              f"速度 {write_speed:.0f}条/秒，data_source: {data_source}")
                    return True
                else:
                    logger.error(f"写入 {symbol} 失败，data_source: {data_source}")
                    return False
            else:
                logger.error("资产数据库管理器未初始化")
                return False
                
        except Exception as e:
            logger.error(f"写入数据失败 {symbol}: {e}，data_source: {data_source}")
            return False
    
    def pause_write(self, task_id: str) -> bool:
        """暂停写入任务"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    logger.warning(f"任务 {task_id} 不存在")
                    return False
                
                state = self.tasks[task_id]
                if state.status != "running":
                    logger.warning(f"任务 {task_id} 未在运行中")
                    return False
                
                state.status = "paused"
                state.pause_time = datetime.now()
                
                logger.info(f"任务 {task_id} 已暂停")
                return True
                
        except Exception as e:
            logger.error(f"暂停任务失败: {e}")
            return False
    
    def resume_write(self, task_id: str) -> bool:
        """恢复写入任务"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    logger.warning(f"任务 {task_id} 不存在")
                    return False
                
                state = self.tasks[task_id]
                if state.status != "paused":
                    logger.warning(f"任务 {task_id} 未被暂停")
                    return False
                
                state.status = "running"
                state.pause_time = None
                
                logger.info(f"任务 {task_id} 已恢复")
                return True
                
        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
            return False
    
    def cancel_write(self, task_id: str) -> bool:
        """取消写入任务"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    logger.warning(f"任务 {task_id} 不存在")
                    return False
                
                state = self.tasks[task_id]
                state.status = "cancelled"
                
                logger.info(f"任务 {task_id} 已取消")
                return True
                
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False
    
    def complete_write(self, task_id: str) -> bool:
        """完成写入任务"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    logger.warning(f"任务 {task_id} 不存在")
                    return False
                
                state = self.tasks[task_id]
                state.status = "completed"
                
                # 计算统计信息
                duration = (datetime.now() - state.start_time).total_seconds()
                avg_speed = state.written_records / duration if duration > 0 else 0
                
                # 发布完成事件
                event = WriteCompletedEvent(
                    task_id=task_id,
                    total_symbols=state.total_symbols,
                    success_count=state.success_count,
                    failure_count=state.failure_count,
                    total_records=state.written_records,
                    duration=duration,
                    average_speed=avg_speed
                )
                self.event_bus.publish(event)
                
                logger.info(f"任务 {task_id} 已完成: "
                          f"总符号数={state.total_symbols}, "
                          f"成功={state.success_count}, "
                          f"失败={state.failure_count}, "
                          f"总记录数={state.written_records}, "
                          f"平均速度={avg_speed:.0f}条/秒")
                
                return True
                
        except Exception as e:
            logger.error(f"完成任务失败: {e}")
            return False
    
    def handle_error(self, task_id: str, error: Exception) -> bool:
        """处理写入错误"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    logger.warning(f"任务 {task_id} 不存在")
                    return False
                
                state = self.tasks[task_id]
                state.failure_count += 1
                
                # 发布错误事件
                event = WriteErrorEvent(
                    task_id=task_id,
                    symbol="unknown",
                    error=str(error),
                    error_type=type(error).__name__,
                    error_details={
                        'timestamp': datetime.now().isoformat(),
                        'state': {
                            'total_symbols': state.total_symbols,
                            'written_symbols': state.written_symbols,
                            'written_records': state.written_records
                        }
                    }
                )
                self.event_bus.publish(event)
                
                logger.error(f"任务 {task_id} 写入错误: {error}")
                return True
                
        except Exception as e:
            logger.error(f"处理错误失败: {e}")
            return False
    
    def get_task_state(self, task_id: str) -> Optional[WriteTaskState]:
        """获取任务状态"""
        with self.task_lock:
            return self.tasks.get(task_id)
    
    def _convert_asset_type(self, asset_type_str: str):
        """将字符串资产类型转换为枚举"""
        try:
            from core.plugin_types import AssetType
            
            # 如果已经是字符串，尝试转换
            if isinstance(asset_type_str, str):
                # 处理映射
                mapping = {
                    "STOCK_A": AssetType.STOCK_A,
                    "STOCK_US": AssetType.STOCK_US,
                    "CRYPTO": AssetType.CRYPTO,
                    "FUTURES": AssetType.FUTURES,
                    "STOCK_HK": AssetType.STOCK_HK,
                }
                return mapping.get(asset_type_str, AssetType.STOCK_A)
            else:
                return asset_type_str
        except Exception as e:
            logger.warning(f"资产类型转换失败，使用默认值: {e}")
            from core.plugin_types import AssetType
            return AssetType.STOCK_A
