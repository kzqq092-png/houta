"""
实时写入事件定义

定义了数据导入过程中的实时写入相关事件。
这些事件用于驱动UI更新、监控报告、错误处理等。
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from datetime import datetime


@dataclass
class WriteStartedEvent:
    """
    实时写入开始事件
    
    当开始对数据进行实时写入时发布此事件。
    """
    task_id: str                    # 任务ID
    task_name: str                  # 任务名称
    symbols: list                   # 要写入的股票列表
    total_records: int              # 总记录数
    timestamp: datetime = None      # 事件时间戳
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class WriteProgressEvent:
    """
    实时写入进度事件
    
    在写入过程中定期发布此事件，包含进度信息和统计数据。
    """
    task_id: str                    # 任务ID
    symbol: str                     # 当前股票代码
    progress: float                 # 进度百分比（0-100）
    written_count: int              # 已写入条数
    total_count: int                # 总条数
    write_speed: float              # 写入速度（条/秒）
    success_count: int              # 成功写入条数
    failure_count: int              # 失败条数
    timestamp: datetime = None      # 事件时间戳
    status: str = "writing"         # 当前状态
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class WriteCompletedEvent:
    """
    实时写入完成事件
    
    当所有数据写入完成时发布此事件。
    """
    task_id: str                    # 任务ID
    total_symbols: int              # 总股票数
    success_count: int              # 成功写入数
    failure_count: int              # 失败数
    total_records: int              # 总记录数
    duration: float                 # 耗时（秒）
    average_speed: float            # 平均速度（条/秒）
    timestamp: datetime = None      # 事件时间戳
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class WriteErrorEvent:
    """
    实时写入错误事件
    
    当写入过程中发生错误时发布此事件。
    """
    task_id: str                    # 任务ID
    symbol: str                     # 相关股票代码
    error: str                      # 错误信息
    error_type: str                 # 错误类型
    retry_count: int = 0            # 重试次数
    timestamp: datetime = None      # 事件时间戳
    error_details: Dict[str, Any] = None  # 错误详情
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.error_details is None:
            self.error_details = {}
