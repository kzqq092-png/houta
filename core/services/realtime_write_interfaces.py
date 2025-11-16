"""
实时写入服务接口定义

定义了实时写入功能的核心服务接口。
这些接口用于服务容器的注册和依赖注入。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import pandas as pd


class IRealtimeWriteService(ABC):
    """
    实时写入服务接口
    
    核心实时写入业务逻辑服务，负责协调数据写入过程。
    """
    
    @abstractmethod
    def start_write(self, task_id: str, config: Dict[str, Any] = None) -> bool:
        """
        开始实时写入任务
        
        Args:
            task_id: 任务ID
            config: 写入配置（可选）
            
        Returns:
            是否成功开始
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def pause_write(self, task_id: str) -> bool:
        """暂停写入任务"""
        pass
    
    @abstractmethod
    def resume_write(self, task_id: str) -> bool:
        """恢复写入任务"""
        pass
    
    @abstractmethod
    def cancel_write(self, task_id: str) -> bool:
        """取消写入任务"""
        pass
    
    @abstractmethod
    def complete_write(self, task_id: str) -> bool:
        """完成写入任务"""
        pass
    
    @abstractmethod
    def handle_error(self, task_id: str, error: Exception) -> bool:
        """处理写入错误"""
        pass


class IWriteProgressService(ABC):
    """
    写入进度跟踪服务接口
    
    负责跟踪写入进度、计算统计信息、监控性能指标。
    """
    
    @abstractmethod
    def start_tracking(self, task_id: str, total_count: int) -> bool:
        """开始跟踪进度"""
        pass
    
    @abstractmethod
    def update_progress(self, task_id: str, symbol: str, 
                       written_count: int, success_count: int, 
                       failure_count: int) -> Dict[str, Any]:
        """
        更新进度
        
        Returns:
            进度统计信息
        """
        pass
    
    @abstractmethod
    def get_progress(self, task_id: str) -> Dict[str, Any]:
        """获取当前进度"""
        pass
    
    @abstractmethod
    def get_statistics(self, task_id: str) -> Dict[str, Any]:
        """获取统计信息"""
        pass
    
    @abstractmethod
    def complete_tracking(self, task_id: str) -> Dict[str, Any]:
        """完成进度跟踪，返回最终统计"""
        pass


class IWriteErrorService(ABC):
    """
    写入错误处理服务接口
    
    负责错误处理、重试管理、错误恢复。
    """
    
    @abstractmethod
    def handle_write_error(self, task_id: str, symbol: str, 
                          error: Exception) -> bool:
        """处理写入错误"""
        pass
    
    @abstractmethod
    def should_retry(self, task_id: str, symbol: str) -> bool:
        """判断是否应该重试"""
        pass
    
    @abstractmethod
    def get_error_summary(self, task_id: str) -> Dict[str, Any]:
        """获取错误汇总"""
        pass


class IWritePerformanceService(ABC):
    """
    写入性能监控服务接口
    
    负责监控写入性能，提供性能指标和优化建议。
    """
    
    @abstractmethod
    def record_write_time(self, task_id: str, symbol: str, 
                         write_time: float, record_count: int) -> None:
        """记录写入耗时"""
        pass
    
    @abstractmethod
    def get_performance_metrics(self, task_id: str) -> Dict[str, Any]:
        """获取性能指标"""
        pass
    
    @abstractmethod
    def get_optimization_suggestions(self, task_id: str) -> List[str]:
        """获取优化建议"""
        pass
