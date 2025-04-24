"""
性能监控配置模块

提供性能监控相关的配置管理功能
"""

from dataclasses import dataclass
from typing import Dict

@dataclass
class PerformanceConfig:
    """性能监控配置类"""
    
    # 更新间隔(秒)
    update_interval: float = 1.0
    
    # CPU使用率阈值(%)
    cpu_threshold: float = 80.0
    
    # 内存使用率阈值(%)
    memory_threshold: float = 80.0
    
    # 磁盘使用率阈值(%)
    disk_threshold: float = 90.0
    
    # 响应时间阈值(秒)
    response_threshold: float = 1.0
    
    @classmethod
    def from_dict(cls, config: Dict) -> 'PerformanceConfig':
        """从字典创建配置对象
        
        Args:
            config: 配置字典
            
        Returns:
            配置对象
        """
        return cls(
            update_interval=float(config.get('update_interval', 1.0)),
            cpu_threshold=float(config.get('cpu_threshold', 80.0)),
            memory_threshold=float(config.get('memory_threshold', 80.0)), 
            disk_threshold=float(config.get('disk_threshold', 90.0)),
            response_threshold=float(config.get('response_threshold', 1.0))
        )
        
    def to_dict(self) -> Dict:
        """转换为字典
        
        Returns:
            配置字典
        """
        return {
            'update_interval': self.update_interval,
            'cpu_threshold': self.cpu_threshold,
            'memory_threshold': self.memory_threshold,
            'disk_threshold': self.disk_threshold,
            'response_threshold': self.response_threshold
        } 