"""
实时写入配置定义

定义了实时写入功能的配置参数。
这些参数用于控制实时写入的行为、性能和监控。
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum


class WriteStrategy(Enum):
    """写入策略枚举"""
    BATCH = "batch"              # 批量写入
    REALTIME = "realtime"        # 实时写入
    ADAPTIVE = "adaptive"        # 自适应写入（根据负载自动调整）


class ErrorHandlingStrategy(Enum):
    """错误处理策略"""
    STOP = "stop"                # 遇到错误停止
    SKIP = "skip"                # 跳过错误继续
    RETRY = "retry"              # 重试失败


@dataclass
class RealtimeWriteConfig:
    """
    实时写入配置
    
    包含了实时写入功能的所有配置参数。
    """
    
    # ==================== 基本配置 ====================
    enabled: bool = True                        # 是否启用实时写入
    write_strategy: WriteStrategy = WriteStrategy.REALTIME  # 写入策略
    error_strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.RETRY  # 错误处理策略
    
    # ==================== 性能配置 ====================
    batch_size: int = 100                       # 批量大小（条）
    concurrency: int = 4                        # 并发度
    timeout: int = 300                          # 超时时间（秒）
    max_retries: int = 3                        # 最大重试次数
    
    # ==================== 监控配置 ====================
    monitor_interval: int = 1                   # 监控间隔（秒）
    enable_performance_monitoring: bool = True  # 启用性能监控
    enable_quality_monitoring: bool = True      # 启用质量监控
    performance_warning_threshold: float = 500  # 性能警告阈值（条/秒）
    
    # ==================== 资源配置 ====================
    memory_limit_mb: int = 2048                 # 内存限制（MB）
    enable_memory_monitoring: bool = True       # 启用内存监控
    enable_gc: bool = True                      # 启用垃圾回收
    gc_interval: int = 100                      # 垃圾回收间隔（记录数）
    
    # ==================== 调试配置 ====================
    debug_mode: bool = False                    # 调试模式
    verbose_logging: bool = False               # 详细日志
    enable_performance_profiling: bool = False  # 启用性能分析
    
    # ==================== 扩展配置 ====================
    custom_config: Dict[str, Any] = field(default_factory=dict)  # 自定义配置
    
    def validate(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            配置是否有效
        """
        if self.batch_size <= 0:
            raise ValueError("batch_size必须大于0")
        if self.concurrency <= 0 or self.concurrency > 32:
            raise ValueError("concurrency必须在1-32之间")
        if self.timeout <= 0:
            raise ValueError("timeout必须大于0")
        if self.max_retries < 0:
            raise ValueError("max_retries必须大于等于0")
        if self.monitor_interval <= 0:
            raise ValueError("monitor_interval必须大于0")
        if self.memory_limit_mb < 512:
            raise ValueError("memory_limit_mb不能小于512MB")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return {
            'enabled': self.enabled,
            'write_strategy': self.write_strategy.value,
            'error_strategy': self.error_strategy.value,
            'batch_size': self.batch_size,
            'concurrency': self.concurrency,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'monitor_interval': self.monitor_interval,
            'enable_performance_monitoring': self.enable_performance_monitoring,
            'enable_quality_monitoring': self.enable_quality_monitoring,
            'performance_warning_threshold': self.performance_warning_threshold,
            'memory_limit_mb': self.memory_limit_mb,
            'enable_memory_monitoring': self.enable_memory_monitoring,
            'enable_gc': self.enable_gc,
            'gc_interval': self.gc_interval,
            'debug_mode': self.debug_mode,
            'verbose_logging': self.verbose_logging,
            'enable_performance_profiling': self.enable_performance_profiling,
            'custom_config': self.custom_config,
        }


# 默认配置实例
DEFAULT_REALTIME_WRITE_CONFIG = RealtimeWriteConfig()

# 性能优先配置（提高写入性能）
PERFORMANCE_CONFIG = RealtimeWriteConfig(
    batch_size=500,
    concurrency=8,
    timeout=600,
    enable_performance_profiling=False,
    enable_gc=True,
    gc_interval=200,
)

# 稳定性优先配置（降低风险）
STABILITY_CONFIG = RealtimeWriteConfig(
    batch_size=50,
    concurrency=2,
    timeout=300,
    max_retries=5,
    enable_performance_monitoring=True,
    enable_memory_monitoring=True,
)

# 调试配置（用于开发和测试）
DEBUG_CONFIG = RealtimeWriteConfig(
    debug_mode=True,
    verbose_logging=True,
    enable_performance_profiling=True,
    batch_size=10,
    concurrency=1,
)
