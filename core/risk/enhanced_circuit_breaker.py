"""
增强熔断器系统

实现专业级的熔断器模式，提供多级降级策略、自适应阈值调整、
智能恢复机制等高级功能，确保交易系统的稳定性和可用性。

作者: FactorWeave-Quant团队
版本: 1.0
日期: 2024-09-17
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import statistics

from loguru import logger


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"        # 关闭（正常）
    HALF_OPEN = "half_open"  # 半开（试探）
    OPEN = "open"            # 打开（熔断）


class FailureType(Enum):
    """故障类型"""
    TIMEOUT = "timeout"              # 超时
    CONNECTION_ERROR = "connection"  # 连接错误
    DATA_QUALITY = "data_quality"    # 数据质量问题
    RATE_LIMIT = "rate_limit"        # 频率限制
    SERVER_ERROR = "server_error"    # 服务器错误
    UNKNOWN = "unknown"              # 未知错误


class DegradationLevel(Enum):
    """降级级别"""
    NONE = 0          # 无降级
    MINOR = 1         # 轻微降级
    MODERATE = 2      # 中等降级
    SEVERE = 3        # 严重降级
    CRITICAL = 4      # 关键降级


@dataclass
class FailureRecord:
    """故障记录"""
    timestamp: datetime
    failure_type: FailureType
    error_message: str
    response_time: float = 0.0
    severity: str = "medium"
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    # 基本阈值
    failure_threshold: int = 5           # 失败阈值
    success_threshold: int = 3           # 成功阈值（半开状态）
    timeout_seconds: float = 60.0       # 熔断超时时间
    
    # 高级配置
    failure_rate_threshold: float = 0.5  # 失败率阈值
    slow_call_threshold: float = 5.0     # 慢调用阈值（秒）
    slow_call_rate_threshold: float = 0.3 # 慢调用率阈值
    minimum_calls: int = 10              # 最小调用数
    
    # 时间窗口
    window_size_seconds: int = 60        # 统计窗口大小
    half_open_max_calls: int = 5         # 半开状态最大调用数
    
    # 自适应配置
    enable_adaptive_threshold: bool = True
    adaptive_factor: float = 0.1         # 自适应因子
    
    # 降级配置
    enable_degradation: bool = True
    degradation_levels: List[DegradationLevel] = field(
        default_factory=lambda: [DegradationLevel.MINOR, DegradationLevel.MODERATE, DegradationLevel.SEVERE]
    )


@dataclass
class CircuitBreakerMetrics:
    """熔断器指标"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    slow_calls: int = 0
    
    current_failure_rate: float = 0.0
    current_slow_call_rate: float = 0.0
    average_response_time: float = 0.0
    
    state_changes: int = 0
    last_state_change: Optional[datetime] = None
    total_downtime: timedelta = timedelta(0)
    
    # 故障类型统计
    failure_by_type: Dict[FailureType, int] = field(default_factory=lambda: defaultdict(int))


class EnhancedCircuitBreaker:
    """
    增强熔断器
    
    提供专业级的熔断器功能，包括多级降级、自适应阈值、智能恢复等
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        """
        初始化增强熔断器
        
        Args:
            name: 熔断器名称
            config: 熔断器配置
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # 状态管理
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
        self.half_open_calls = 0
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        
        # 指标和历史
        self.metrics = CircuitBreakerMetrics()
        self.failure_history: deque = deque(maxlen=1000)
        self.call_history: deque = deque(maxlen=1000)
        
        # 时间窗口统计
        self.window_calls: deque = deque()
        self.window_failures: deque = deque()
        self.window_slow_calls: deque = deque()
        
        # 降级管理
        self.current_degradation_level = DegradationLevel.NONE
        self.degradation_handlers: Dict[DegradationLevel, Callable] = {}
        
        # 自适应阈值
        self.adaptive_failure_threshold = self.config.failure_threshold
        self.adaptive_timeout = self.config.timeout_seconds
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 事件回调
        self.state_change_callbacks: List[Callable] = []
        self.failure_callbacks: List[Callable] = []
        
        self.logger = logger.bind(circuit_breaker=name)
        self.logger.info(f"增强熔断器初始化: {name}")
    
    def call(self, func: Callable, *args, **kwargs):
        """
        执行受保护的调用
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            CircuitBreakerOpenException: 熔断器打开时
            原函数的异常: 函数执行失败时
        """
        with self._lock:
            # 检查熔断器状态
            if not self._can_proceed():
                self._handle_circuit_open()
                raise CircuitBreakerOpenException(
                    f"熔断器 {self.name} 处于打开状态，降级级别: {self.current_degradation_level.name}"
                )
            
            # 记录调用开始
            start_time = time.time()
            call_record = {
                "timestamp": datetime.now(),
                "start_time": start_time
            }
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录成功
                end_time = time.time()
                response_time = end_time - start_time
                self._record_success(response_time, call_record)
                
                return result
                
            except Exception as e:
                # 记录失败
                end_time = time.time()
                response_time = end_time - start_time
                self._record_failure(e, response_time, call_record)
                raise
    
    def async_call(self, async_func: Callable, *args, **kwargs):
        """
        异步调用支持
        
        Args:
            async_func: 异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        """
        import asyncio
        
        async def protected_async_call():
            with self._lock:
                if not self._can_proceed():
                    self._handle_circuit_open()
                    raise CircuitBreakerOpenException(f"熔断器 {self.name} 处于打开状态")
                
                start_time = time.time()
                call_record = {
                    "timestamp": datetime.now(),
                    "start_time": start_time
                }
                
                try:
                    result = await async_func(*args, **kwargs)
                    
                    end_time = time.time()
                    response_time = end_time - start_time
                    self._record_success(response_time, call_record)
                    
                    return result
                    
                except Exception as e:
                    end_time = time.time()
                    response_time = end_time - start_time
                    self._record_failure(e, response_time, call_record)
                    raise
        
        return protected_async_call()
    
    def _can_proceed(self) -> bool:
        """检查是否可以继续执行"""
        current_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # 检查是否应该转换到半开状态
            if (self.last_failure_time and 
                current_time - self.last_failure_time >= timedelta(seconds=self.adaptive_timeout)):
                self._transition_to_half_open()
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            # 半开状态下限制调用数
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def _record_success(self, response_time: float, call_record: Dict) -> None:
        """记录成功调用"""
        current_time = datetime.now()
        
        # 更新基本指标
        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        
        # 更新响应时间
        self._update_average_response_time(response_time)
        
        # 检查是否是慢调用
        if response_time > self.config.slow_call_threshold:
            self.metrics.slow_calls += 1
            self.window_slow_calls.append(current_time)
        
        # 添加到窗口统计
        self.window_calls.append(current_time)
        self.call_history.append({
            **call_record,
            "success": True,
            "response_time": response_time,
            "end_time": time.time()
        })
        
        # 状态转换逻辑
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.consecutive_successes >= self.config.success_threshold:
                self._transition_to_closed()
        
        # 清理窗口数据
        self._cleanup_window_data()
        
        # 更新速率统计
        self._update_rates()
        
        # 自适应阈值调整
        if self.config.enable_adaptive_threshold:
            self._adapt_thresholds()
    
    def _record_failure(self, exception: Exception, response_time: float, call_record: Dict) -> None:
        """记录失败调用"""
        current_time = datetime.now()
        
        # 分析故障类型
        failure_type = self._classify_failure(exception)
        
        # 创建故障记录
        failure_record = FailureRecord(
            timestamp=current_time,
            failure_type=failure_type,
            error_message=str(exception),
            response_time=response_time,
            severity=self._determine_failure_severity(exception, failure_type),
            context={
                "exception_type": type(exception).__name__,
                "response_time": response_time
            }
        )
        
        # 更新指标
        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self.metrics.failure_by_type[failure_type] += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = current_time
        
        # 添加到历史记录
        self.failure_history.append(failure_record)
        self.window_calls.append(current_time)
        self.window_failures.append(current_time)
        
        self.call_history.append({
            **call_record,
            "success": False,
            "response_time": response_time,
            "error": str(exception),
            "failure_type": failure_type.value,
            "end_time": time.time()
        })
        
        # 清理窗口数据
        self._cleanup_window_data()
        
        # 更新速率统计
        self._update_rates()
        
        # 检查是否需要熔断
        self._check_circuit_breaker_conditions()
        
        # 触发故障回调
        self._trigger_failure_callbacks(failure_record)
        
        # 自适应阈值调整
        if self.config.enable_adaptive_threshold:
            self._adapt_thresholds()
    
    def _classify_failure(self, exception: Exception) -> FailureType:
        """分类故障类型"""
        exception_name = type(exception).__name__.lower()
        exception_message = str(exception).lower()
        
        if "timeout" in exception_name or "timeout" in exception_message:
            return FailureType.TIMEOUT
        elif "connection" in exception_name or "connection" in exception_message:
            return FailureType.CONNECTION_ERROR
        elif "rate" in exception_message and "limit" in exception_message:
            return FailureType.RATE_LIMIT
        elif "server" in exception_message or "http" in exception_name:
            return FailureType.SERVER_ERROR
        elif hasattr(exception, 'quality_score'):
            return FailureType.DATA_QUALITY
        else:
            return FailureType.UNKNOWN
    
    def _determine_failure_severity(self, exception: Exception, failure_type: FailureType) -> str:
        """确定故障严重程度"""
        # 根据故障类型和异常内容确定严重程度
        if failure_type == FailureType.CONNECTION_ERROR:
            return "high"
        elif failure_type == FailureType.TIMEOUT:
            return "medium"
        elif failure_type == FailureType.DATA_QUALITY:
            return "medium"
        elif failure_type == FailureType.RATE_LIMIT:
            return "low"
        else:
            return "medium"
    
    def _check_circuit_breaker_conditions(self) -> None:
        """检查熔断器条件"""
        if self.state == CircuitState.OPEN:
            return
        
        # 确保有足够的调用数据
        if len(self.window_calls) < self.config.minimum_calls:
            return
        
        # 检查失败率
        if self.metrics.current_failure_rate >= self.config.failure_rate_threshold:
            self._transition_to_open(f"失败率过高: {self.metrics.current_failure_rate:.2%}")
            return
        
        # 检查慢调用率
        if self.metrics.current_slow_call_rate >= self.config.slow_call_rate_threshold:
            self._transition_to_open(f"慢调用率过高: {self.metrics.current_slow_call_rate:.2%}")
            return
        
        # 检查连续失败数
        if self.consecutive_failures >= self.adaptive_failure_threshold:
            self._transition_to_open(f"连续失败数过多: {self.consecutive_failures}")
            return
    
    def _transition_to_open(self, reason: str) -> None:
        """转换到打开状态"""
        if self.state != CircuitState.OPEN:
            previous_state = self.state
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            self.metrics.state_changes += 1
            self.metrics.last_state_change = datetime.now()
            
            # 设置降级级别
            self._determine_degradation_level()
            
            self.logger.warning(f"熔断器打开: {reason}")
            self._trigger_state_change_callbacks(previous_state, CircuitState.OPEN, reason)
    
    def _transition_to_half_open(self) -> None:
        """转换到半开状态"""
        if self.state != CircuitState.HALF_OPEN:
            previous_state = self.state
            self.state = CircuitState.HALF_OPEN
            self.half_open_calls = 0
            self.consecutive_successes = 0
            self.metrics.state_changes += 1
            self.metrics.last_state_change = datetime.now()
            
            # 降级到较低级别
            self._reduce_degradation_level()
            
            self.logger.info("熔断器转换到半开状态")
            self._trigger_state_change_callbacks(previous_state, CircuitState.HALF_OPEN, "超时恢复")
    
    def _transition_to_closed(self) -> None:
        """转换到关闭状态"""
        if self.state != CircuitState.CLOSED:
            previous_state = self.state
            self.state = CircuitState.CLOSED
            self.half_open_calls = 0
            self.consecutive_failures = 0
            self.metrics.state_changes += 1
            self.metrics.last_state_change = datetime.now()
            
            # 取消降级
            self.current_degradation_level = DegradationLevel.NONE
            
            self.logger.info("熔断器关闭，服务恢复正常")
            self._trigger_state_change_callbacks(previous_state, CircuitState.CLOSED, "服务恢复")
    
    def _determine_degradation_level(self) -> None:
        """确定降级级别"""
        if not self.config.enable_degradation:
            return
        
        # 基于故障率和类型确定降级级别
        if self.metrics.current_failure_rate >= 0.8:
            self.current_degradation_level = DegradationLevel.CRITICAL
        elif self.metrics.current_failure_rate >= 0.6:
            self.current_degradation_level = DegradationLevel.SEVERE
        elif self.metrics.current_failure_rate >= 0.4:
            self.current_degradation_level = DegradationLevel.MODERATE
        else:
            self.current_degradation_level = DegradationLevel.MINOR
        
        self.logger.info(f"设置降级级别: {self.current_degradation_level.name}")
    
    def _reduce_degradation_level(self) -> None:
        """降低降级级别"""
        if self.current_degradation_level.value > 0:
            new_level = DegradationLevel(self.current_degradation_level.value - 1)
            self.current_degradation_level = new_level
            self.logger.info(f"降级级别降低到: {new_level.name}")
    
    def _handle_circuit_open(self) -> None:
        """处理熔断器打开状态"""
        # 执行降级处理
        if self.current_degradation_level in self.degradation_handlers:
            try:
                handler = self.degradation_handlers[self.current_degradation_level]
                handler()
            except Exception as e:
                self.logger.error(f"降级处理器执行失败: {e}")
    
    def _cleanup_window_data(self) -> None:
        """清理窗口数据"""
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=self.config.window_size_seconds)
        
        # 清理过期的窗口数据
        while self.window_calls and self.window_calls[0] < window_start:
            self.window_calls.popleft()
        
        while self.window_failures and self.window_failures[0] < window_start:
            self.window_failures.popleft()
        
        while self.window_slow_calls and self.window_slow_calls[0] < window_start:
            self.window_slow_calls.popleft()
    
    def _update_rates(self) -> None:
        """更新速率统计"""
        window_call_count = len(self.window_calls)
        
        if window_call_count > 0:
            # 计算失败率
            window_failure_count = len(self.window_failures)
            self.metrics.current_failure_rate = window_failure_count / window_call_count
            
            # 计算慢调用率
            window_slow_call_count = len(self.window_slow_calls)
            self.metrics.current_slow_call_rate = window_slow_call_count / window_call_count
        else:
            self.metrics.current_failure_rate = 0.0
            self.metrics.current_slow_call_rate = 0.0
    
    def _update_average_response_time(self, response_time: float) -> None:
        """更新平均响应时间"""
        if self.metrics.total_calls == 1:
            self.metrics.average_response_time = response_time
        else:
            # 使用指数移动平均
            alpha = 0.1
            self.metrics.average_response_time = (
                alpha * response_time + (1 - alpha) * self.metrics.average_response_time
            )
    
    def _adapt_thresholds(self) -> None:
        """自适应阈值调整"""
        if not self.config.enable_adaptive_threshold:
            return
        
        # 基于历史性能调整阈值
        if len(self.call_history) >= 50:
            recent_calls = list(self.call_history)[-50:]
            success_rate = sum(1 for call in recent_calls if call.get("success", False)) / len(recent_calls)
            
            # 根据成功率调整失败阈值
            if success_rate > 0.9:
                # 性能良好，可以提高容忍度
                self.adaptive_failure_threshold = min(
                    self.config.failure_threshold * 1.5,
                    self.adaptive_failure_threshold * (1 + self.config.adaptive_factor)
                )
            elif success_rate < 0.7:
                # 性能较差，降低容忍度
                self.adaptive_failure_threshold = max(
                    self.config.failure_threshold * 0.5,
                    self.adaptive_failure_threshold * (1 - self.config.adaptive_factor)
                )
            
            # 调整超时时间
            avg_response_time = statistics.mean([
                call.get("response_time", 0) for call in recent_calls
                if call.get("success", False)
            ]) if recent_calls else self.config.timeout_seconds
            
            if avg_response_time > 0:
                self.adaptive_timeout = max(
                    self.config.timeout_seconds,
                    avg_response_time * 1.5
                )
    
    def _trigger_state_change_callbacks(self, from_state: CircuitState, 
                                      to_state: CircuitState, reason: str) -> None:
        """触发状态变更回调"""
        for callback in self.state_change_callbacks:
            try:
                callback(self.name, from_state, to_state, reason)
            except Exception as e:
                self.logger.error(f"状态变更回调执行失败: {e}")
    
    def _trigger_failure_callbacks(self, failure_record: FailureRecord) -> None:
        """触发故障回调"""
        for callback in self.failure_callbacks:
            try:
                callback(self.name, failure_record)
            except Exception as e:
                self.logger.error(f"故障回调执行失败: {e}")
    
    # 公共接口方法
    def add_state_change_callback(self, callback: Callable) -> None:
        """添加状态变更回调"""
        self.state_change_callbacks.append(callback)
    
    def add_failure_callback(self, callback: Callable) -> None:
        """添加故障回调"""
        self.failure_callbacks.append(callback)
    
    def register_degradation_handler(self, level: DegradationLevel, handler: Callable) -> None:
        """注册降级处理器"""
        self.degradation_handlers[level] = handler
        self.logger.info(f"注册降级处理器: {level.name}")
    
    def force_open(self, reason: str = "手动打开") -> None:
        """强制打开熔断器"""
        with self._lock:
            self._transition_to_open(reason)
    
    def force_close(self, reason: str = "手动关闭") -> None:
        """强制关闭熔断器"""
        with self._lock:
            self._transition_to_closed()
    
    def reset(self) -> None:
        """重置熔断器"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.metrics = CircuitBreakerMetrics()
            self.failure_history.clear()
            self.call_history.clear()
            self.window_calls.clear()
            self.window_failures.clear()
            self.window_slow_calls.clear()
            self.current_degradation_level = DegradationLevel.NONE
            self.consecutive_failures = 0
            self.consecutive_successes = 0
            self.half_open_calls = 0
            
            self.logger.info("熔断器已重置")
    
    def get_state(self) -> CircuitState:
        """获取当前状态"""
        return self.state
    
    def get_metrics(self) -> CircuitBreakerMetrics:
        """获取指标"""
        return self.metrics
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        return {
            "name": self.name,
            "state": self.state.value,
            "degradation_level": self.current_degradation_level.value,
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "success_rate": (
                    self.metrics.successful_calls / self.metrics.total_calls
                    if self.metrics.total_calls > 0 else 0.0
                ),
                "failure_rate": self.metrics.current_failure_rate,
                "slow_call_rate": self.metrics.current_slow_call_rate,
                "average_response_time": self.metrics.average_response_time,
                "consecutive_failures": self.consecutive_failures,
                "state_changes": self.metrics.state_changes
            },
            "config": {
                "failure_threshold": self.adaptive_failure_threshold,
                "timeout_seconds": self.adaptive_timeout,
                "failure_rate_threshold": self.config.failure_rate_threshold,
                "slow_call_rate_threshold": self.config.slow_call_rate_threshold
            },
            "recent_failures": [
                {
                    "timestamp": record.timestamp.isoformat(),
                    "type": record.failure_type.value,
                    "message": record.error_message,
                    "severity": record.severity
                }
                for record in list(self.failure_history)[-5:]  # 最近5个故障
            ]
        }


class CircuitBreakerOpenException(Exception):
    """熔断器打开异常"""
    pass


class CircuitBreakerManager:
    """熔断器管理器"""
    
    def __init__(self):
        """初始化熔断器管理器"""
        self.circuit_breakers: Dict[str, EnhancedCircuitBreaker] = {}
        self._lock = threading.RLock()
        self.logger = logger.bind(module="CircuitBreakerManager")
    
    def get_or_create_circuit_breaker(self, name: str, 
                                    config: CircuitBreakerConfig = None) -> EnhancedCircuitBreaker:
        """获取或创建熔断器"""
        with self._lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = EnhancedCircuitBreaker(name, config)
                self.logger.info(f"创建新熔断器: {name}")
            
            return self.circuit_breakers[name]
    
    def get_circuit_breaker(self, name: str) -> Optional[EnhancedCircuitBreaker]:
        """获取熔断器"""
        return self.circuit_breakers.get(name)
    
    def get_all_health_reports(self) -> Dict[str, Dict[str, Any]]:
        """获取所有熔断器的健康报告"""
        reports = {}
        for name, breaker in self.circuit_breakers.items():
            reports[name] = breaker.get_health_report()
        return reports
    
    def reset_all(self) -> None:
        """重置所有熔断器"""
        with self._lock:
            for breaker in self.circuit_breakers.values():
                breaker.reset()
            self.logger.info("所有熔断器已重置")


# 全局熔断器管理器实例
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """获取全局熔断器管理器"""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager


def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """
    熔断器装饰器
    
    Args:
        name: 熔断器名称
        config: 熔断器配置
    
    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            breaker = manager.get_or_create_circuit_breaker(name, config)
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
