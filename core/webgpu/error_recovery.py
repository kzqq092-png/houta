from loguru import logger
"""
WebGPU错误处理和恢复机制

提供全面的错误处理功能：
- WebGPU错误类型分类和诊断
- 自动恢复策略
- 渲染引擎降级机制
- 用户友好的错误提示和解决方案
- 错误统计和分析

作者: FactorWeave-Quant团队
版本: 1.0.0
"""

import time
import traceback
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union, Type
from enum import Enum
from abc import ABC, abstractmethod

logger = logger


class ErrorCategory(Enum):
    """错误类别"""
    WEBGPU_NOT_SUPPORTED = "webgpu_not_supported"
    DEVICE_LOST = "device_lost"
    OUT_OF_MEMORY = "out_of_memory"
    SHADER_COMPILATION = "shader_compilation"
    BUFFER_CREATION = "buffer_creation"
    TEXTURE_CREATION = "texture_creation"
    PIPELINE_CREATION = "pipeline_creation"
    RENDERING_ERROR = "rendering_error"
    CONTEXT_LOST = "context_lost"
    DRIVER_ERROR = "driver_error"
    COMPATIBILITY_ERROR = "compatibility_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """错误严重程度"""
    CRITICAL = "critical"      # 严重错误，需要立即降级
    HIGH = "high"             # 高优先级错误，需要恢复
    MEDIUM = "medium"         # 中等错误，可以重试
    LOW = "low"              # 轻微错误，记录即可
    WARNING = "warning"       # 警告，不影响功能


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"                    # 重试操作
    RECREATE_DEVICE = "recreate_device"    # 重新创建设备
    FALLBACK_ENGINE = "fallback_engine"   # 降级到备用引擎
    REDUCE_QUALITY = "reduce_quality"     # 降低质量设置
    CLEAR_CACHE = "clear_cache"          # 清理缓存
    RESTART_CONTEXT = "restart_context"   # 重启上下文
    USER_INTERVENTION = "user_intervention"  # 需要用户干预
    NO_RECOVERY = "no_recovery"          # 无法恢复


@dataclass
class ErrorInfo:
    """错误信息"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    technical_details: str = ""
    user_message: str = ""
    recovery_strategies: List[RecoveryStrategy] = field(default_factory=list)
    error_code: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    strategy_used: RecoveryStrategy
    message: str
    duration: float
    new_engine: Optional[str] = None
    performance_impact: float = 0.0  # 性能影响百分比


@dataclass
class ErrorStatistics:
    """错误统计信息"""
    total_errors: int = 0
    errors_by_category: Dict[ErrorCategory, int] = field(default_factory=dict)
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=dict)
    recovery_success_rate: float = 0.0
    most_common_error: Optional[ErrorCategory] = None
    error_trend: List[float] = field(default_factory=list)  # 按时间的错误频率


class ErrorDetector:
    """错误检测器"""

    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()

    def _initialize_error_patterns(self) -> Dict[str, ErrorCategory]:
        """初始化错误模式匹配"""
        return {
            # WebGPU不支持
            "webgpu is not supported": ErrorCategory.WEBGPU_NOT_SUPPORTED,
            "webgpu not available": ErrorCategory.WEBGPU_NOT_SUPPORTED,
            "navigator.gpu is undefined": ErrorCategory.WEBGPU_NOT_SUPPORTED,

            # 设备丢失
            "device lost": ErrorCategory.DEVICE_LOST,
            "device.lost": ErrorCategory.DEVICE_LOST,
            "gpu device lost": ErrorCategory.DEVICE_LOST,

            # 内存不足
            "out of memory": ErrorCategory.OUT_OF_MEMORY,
            "insufficient memory": ErrorCategory.OUT_OF_MEMORY,
            "memory allocation failed": ErrorCategory.OUT_OF_MEMORY,
            "gpu memory exhausted": ErrorCategory.OUT_OF_MEMORY,

            # 着色器编译错误
            "shader compilation failed": ErrorCategory.SHADER_COMPILATION,
            "invalid shader": ErrorCategory.SHADER_COMPILATION,
            "shader error": ErrorCategory.SHADER_COMPILATION,

            # 缓冲区创建错误
            "buffer creation failed": ErrorCategory.BUFFER_CREATION,
            "invalid buffer": ErrorCategory.BUFFER_CREATION,

            # 纹理创建错误
            "texture creation failed": ErrorCategory.TEXTURE_CREATION,
            "invalid texture": ErrorCategory.TEXTURE_CREATION,

            # 管道创建错误
            "pipeline creation failed": ErrorCategory.PIPELINE_CREATION,
            "invalid pipeline": ErrorCategory.PIPELINE_CREATION,

            # 渲染错误
            "render error": ErrorCategory.RENDERING_ERROR,
            "rendering failed": ErrorCategory.RENDERING_ERROR,
            "draw call failed": ErrorCategory.RENDERING_ERROR,

            # 上下文丢失
            "context lost": ErrorCategory.CONTEXT_LOST,
            "webgl context lost": ErrorCategory.CONTEXT_LOST,

            # 驱动错误
            "driver error": ErrorCategory.DRIVER_ERROR,
            "graphics driver": ErrorCategory.DRIVER_ERROR,
            "gpu driver": ErrorCategory.DRIVER_ERROR,

            # 兼容性错误
            "unsupported feature": ErrorCategory.COMPATIBILITY_ERROR,
            "incompatible": ErrorCategory.COMPATIBILITY_ERROR,
        }

    def detect_error_category(self, error_message: str, exception: Optional[Exception] = None) -> ErrorCategory:
        """检测错误类别"""
        error_message_lower = error_message.lower()

        # 检查已知错误模式
        for pattern, category in self.error_patterns.items():
            if pattern in error_message_lower:
                return category

        # 根据异常类型推断
        if exception:
            exception_type = type(exception).__name__.lower()

            if "memory" in exception_type:
                return ErrorCategory.OUT_OF_MEMORY
            elif "timeout" in exception_type:
                return ErrorCategory.PERFORMANCE_DEGRADATION
            elif "permission" in exception_type:
                return ErrorCategory.COMPATIBILITY_ERROR

        return ErrorCategory.UNKNOWN_ERROR

    def assess_severity(self, category: ErrorCategory, context: Dict[str, Any]) -> ErrorSeverity:
        """评估错误严重程度"""
        # 严重错误
        if category in [ErrorCategory.WEBGPU_NOT_SUPPORTED, ErrorCategory.DEVICE_LOST]:
            return ErrorSeverity.CRITICAL

        # 高优先级错误
        if category in [ErrorCategory.OUT_OF_MEMORY, ErrorCategory.CONTEXT_LOST]:
            return ErrorSeverity.HIGH

        # 中等错误
        if category in [ErrorCategory.SHADER_COMPILATION, ErrorCategory.BUFFER_CREATION,
                        ErrorCategory.TEXTURE_CREATION, ErrorCategory.PIPELINE_CREATION]:
            return ErrorSeverity.MEDIUM

        # 低优先级错误
        if category in [ErrorCategory.RENDERING_ERROR, ErrorCategory.PERFORMANCE_DEGRADATION]:
            return ErrorSeverity.LOW

        # 默认为中等
        return ErrorSeverity.MEDIUM


class RecoveryStrategyManager:
    """恢复策略管理器"""

    def __init__(self):
        self.strategy_map = self._initialize_strategies()

    def _initialize_strategies(self) -> Dict[ErrorCategory, List[RecoveryStrategy]]:
        """初始化恢复策略映射"""
        return {
            ErrorCategory.WEBGPU_NOT_SUPPORTED: [
                RecoveryStrategy.FALLBACK_ENGINE
            ],
            ErrorCategory.DEVICE_LOST: [
                RecoveryStrategy.RECREATE_DEVICE,
                RecoveryStrategy.FALLBACK_ENGINE
            ],
            ErrorCategory.OUT_OF_MEMORY: [
                RecoveryStrategy.CLEAR_CACHE,
                RecoveryStrategy.REDUCE_QUALITY,
                RecoveryStrategy.FALLBACK_ENGINE
            ],
            ErrorCategory.SHADER_COMPILATION: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.REDUCE_QUALITY,
                RecoveryStrategy.FALLBACK_ENGINE
            ],
            ErrorCategory.BUFFER_CREATION: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.CLEAR_CACHE,
                RecoveryStrategy.REDUCE_QUALITY
            ],
            ErrorCategory.TEXTURE_CREATION: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.REDUCE_QUALITY,
                RecoveryStrategy.CLEAR_CACHE
            ],
            ErrorCategory.PIPELINE_CREATION: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.RECREATE_DEVICE
            ],
            ErrorCategory.RENDERING_ERROR: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.CLEAR_CACHE
            ],
            ErrorCategory.CONTEXT_LOST: [
                RecoveryStrategy.RESTART_CONTEXT,
                RecoveryStrategy.FALLBACK_ENGINE
            ],
            ErrorCategory.DRIVER_ERROR: [
                RecoveryStrategy.USER_INTERVENTION
            ],
            ErrorCategory.COMPATIBILITY_ERROR: [
                RecoveryStrategy.FALLBACK_ENGINE
            ],
            ErrorCategory.PERFORMANCE_DEGRADATION: [
                RecoveryStrategy.REDUCE_QUALITY,
                RecoveryStrategy.CLEAR_CACHE
            ],
            ErrorCategory.UNKNOWN_ERROR: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.FALLBACK_ENGINE
            ]
        }

    def get_recovery_strategies(self, category: ErrorCategory) -> List[RecoveryStrategy]:
        """获取错误类别对应的恢复策略"""
        return self.strategy_map.get(category, [RecoveryStrategy.NO_RECOVERY])


class RecoveryAction(ABC):
    """恢复动作抽象基类"""

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> RecoveryResult:
        """执行恢复动作"""
        pass


class RetryAction(RecoveryAction):
    """重试动作"""

    def __init__(self, max_retries: int = 3, delay: float = 1.0):
        self.max_retries = max_retries
        self.delay = delay

    def execute(self, context: Dict[str, Any]) -> RecoveryResult:
        start_time = time.time()

        failed_operation = context.get('failed_operation')
        if not failed_operation:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY,
                message="没有可重试的操作",
                duration=time.time() - start_time
            )

        for attempt in range(self.max_retries):
            try:
                logger.info(f"重试操作，第 {attempt + 1} 次尝试...")
                failed_operation()

                return RecoveryResult(
                    success=True,
                    strategy_used=RecoveryStrategy.RETRY,
                    message=f"重试成功，共尝试 {attempt + 1} 次",
                    duration=time.time() - start_time
                )

            except Exception as e:
                logger.warning(f"重试失败 ({attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.delay)

        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.RETRY,
            message=f"重试失败，已尝试 {self.max_retries} 次",
            duration=time.time() - start_time
        )


class FallbackEngineAction(RecoveryAction):
    """降级引擎动作"""

    def __init__(self, fallback_engines: List[str]):
        self.fallback_engines = fallback_engines

    def execute(self, context: Dict[str, Any]) -> RecoveryResult:
        start_time = time.time()

        current_engine = context.get('current_engine', 'webgpu')

        # 确定下一个可用的降级引擎
        try:
            current_index = self.fallback_engines.index(current_engine)
            next_engine = self.fallback_engines[current_index + 1]
        except (ValueError, IndexError):
            # 如果当前引擎不在列表中或已经是最后一个
            next_engine = self.fallback_engines[0] if self.fallback_engines else None

        if not next_engine:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK_ENGINE,
                message="没有可用的降级引擎",
                duration=time.time() - start_time
            )

        try:
            # 执行引擎切换
            switch_function = context.get('switch_engine_function')
            if switch_function:
                switch_function(next_engine)

            # 计算性能影响
            performance_impact = self._calculate_performance_impact(current_engine, next_engine)

            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.FALLBACK_ENGINE,
                message=f"成功降级到 {next_engine} 引擎",
                duration=time.time() - start_time,
                new_engine=next_engine,
                performance_impact=performance_impact
            )

        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK_ENGINE,
                message=f"引擎降级失败: {e}",
                duration=time.time() - start_time
            )

    def _calculate_performance_impact(self, from_engine: str, to_engine: str) -> float:
        """计算性能影响百分比"""
        # 基于经验的性能影响估算
        performance_hierarchy = {
            'webgpu': 100,
            'opengl': 70,
            'canvas2d': 40,
            'matplotlib': 20,
            'software': 10
        }

        from_performance = performance_hierarchy.get(from_engine, 50)
        to_performance = performance_hierarchy.get(to_engine, 50)

        impact = ((from_performance - to_performance) / from_performance) * 100
        return max(0, impact)


class ReduceQualityAction(RecoveryAction):
    """降低质量动作"""

    def execute(self, context: Dict[str, Any]) -> RecoveryResult:
        start_time = time.time()

        try:
            # 获取当前质量设置
            quality_settings = context.get('quality_settings', {})

            # 降低质量设置
            new_settings = self._reduce_quality_settings(quality_settings)

            # 应用新设置
            apply_settings_function = context.get('apply_quality_settings')
            if apply_settings_function:
                apply_settings_function(new_settings)

            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.REDUCE_QUALITY,
                message="已降低渲染质量以提高稳定性",
                duration=time.time() - start_time,
                performance_impact=25.0  # 估算25%的性能影响
            )

        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.REDUCE_QUALITY,
                message=f"质量降级失败: {e}",
                duration=time.time() - start_time
            )

    def _reduce_quality_settings(self, current_settings: Dict[str, Any]) -> Dict[str, Any]:
        """降低质量设置"""
        new_settings = current_settings.copy()

        # 降低分辨率
        if 'resolution_scale' in new_settings:
            new_settings['resolution_scale'] = max(0.5, new_settings['resolution_scale'] * 0.8)

        # 降低抗锯齿
        if 'antialiasing' in new_settings:
            new_settings['antialiasing'] = max(1, new_settings['antialiasing'] // 2)

        # 减少数据点
        if 'max_data_points' in new_settings:
            new_settings['max_data_points'] = max(500, new_settings['max_data_points'] // 2)

        # 禁用高级特效
        new_settings['advanced_effects'] = False
        new_settings['gpu_acceleration'] = min(2, new_settings.get('gpu_acceleration', 3))

        return new_settings


class ClearCacheAction(RecoveryAction):
    """清理缓存动作"""

    def execute(self, context: Dict[str, Any]) -> RecoveryResult:
        start_time = time.time()

        try:
            cleared_items = []

            # 清理渲染缓存
            clear_render_cache = context.get('clear_render_cache')
            if clear_render_cache:
                clear_render_cache()
                cleared_items.append("渲染缓存")

            # 清理纹理缓存
            clear_texture_cache = context.get('clear_texture_cache')
            if clear_texture_cache:
                clear_texture_cache()
                cleared_items.append("纹理缓存")

            # 清理缓冲区缓存
            clear_buffer_cache = context.get('clear_buffer_cache')
            if clear_buffer_cache:
                clear_buffer_cache()
                cleared_items.append("缓冲区缓存")

            # 强制垃圾回收
            import gc
            gc.collect()
            cleared_items.append("内存垃圾")

            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.CLEAR_CACHE,
                message=f"已清理: {', '.join(cleared_items)}",
                duration=time.time() - start_time
            )

        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.CLEAR_CACHE,
                message=f"缓存清理失败: {e}",
                duration=time.time() - start_time
            )


class ErrorRecoveryManager:
    """错误恢复管理器"""

    def __init__(self):
        self.error_detector = ErrorDetector()
        self.strategy_manager = RecoveryStrategyManager()
        self.error_history: List[ErrorInfo] = []
        self.recovery_actions = self._initialize_recovery_actions()
        self.statistics = ErrorStatistics()
        self._lock = threading.Lock()

    def _initialize_recovery_actions(self) -> Dict[RecoveryStrategy, RecoveryAction]:
        """初始化恢复动作"""
        return {
            RecoveryStrategy.RETRY: RetryAction(),
            RecoveryStrategy.FALLBACK_ENGINE: FallbackEngineAction(
                ['webgpu', 'opengl', 'canvas2d', 'matplotlib', 'software']
            ),
            RecoveryStrategy.REDUCE_QUALITY: ReduceQualityAction(),
            RecoveryStrategy.CLEAR_CACHE: ClearCacheAction(),
        }

    def handle_error(self, error_message: str, exception: Optional[Exception] = None,
                     context: Optional[Dict[str, Any]] = None) -> Optional[RecoveryResult]:
        """
        处理错误并尝试恢复

        Args:
            error_message: 错误消息
            exception: 异常对象
            context: 错误上下文信息

        Returns:
            恢复结果，如果无法恢复则返回None
        """
        with self._lock:
            # 检测错误信息
            error_info = self._analyze_error(error_message, exception, context or {})

            # 记录错误
            self._record_error(error_info)

            # 尝试恢复
            recovery_result = self._attempt_recovery(error_info, context or {})

            # 更新统计信息
            self._update_statistics(error_info, recovery_result)

            return recovery_result

    def _analyze_error(self, error_message: str, exception: Optional[Exception],
                       context: Dict[str, Any]) -> ErrorInfo:
        """分析错误信息"""
        category = self.error_detector.detect_error_category(error_message, exception)
        severity = self.error_detector.assess_severity(category, context)
        recovery_strategies = self.strategy_manager.get_recovery_strategies(category)

        # 生成用户友好的错误消息
        user_message = self._generate_user_message(category, severity)

        # 技术详情
        technical_details = f"错误消息: {error_message}"
        if exception:
            technical_details += f"\n异常类型: {type(exception).__name__}"
            technical_details += f"\n堆栈跟踪: {traceback.format_exc()}"

        return ErrorInfo(
            category=category,
            severity=severity,
            message=error_message,
            technical_details=technical_details,
            user_message=user_message,
            recovery_strategies=recovery_strategies,
            context=context
        )

    def _generate_user_message(self, category: ErrorCategory, severity: ErrorSeverity) -> str:
        """生成用户友好的错误消息"""
        messages = {
            ErrorCategory.WEBGPU_NOT_SUPPORTED: "您的浏览器或系统不支持WebGPU硬件加速，将自动切换到兼容模式。",
            ErrorCategory.DEVICE_LOST: "GPU设备连接丢失，正在尝试重新连接...",
            ErrorCategory.OUT_OF_MEMORY: "GPU内存不足，正在降低渲染质量以减少内存使用。",
            ErrorCategory.SHADER_COMPILATION: "图形渲染程序编译失败，正在尝试使用备用方案。",
            ErrorCategory.BUFFER_CREATION: "图形缓冲区创建失败，正在重试...",
            ErrorCategory.TEXTURE_CREATION: "纹理创建失败，正在清理缓存后重试。",
            ErrorCategory.PIPELINE_CREATION: "渲染管道创建失败，正在重新初始化。",
            ErrorCategory.RENDERING_ERROR: "渲染过程中出现错误，正在尝试恢复。",
            ErrorCategory.CONTEXT_LOST: "图形上下文丢失，正在重新创建。",
            ErrorCategory.DRIVER_ERROR: "显卡驱动错误，建议更新显卡驱动程序。",
            ErrorCategory.COMPATIBILITY_ERROR: "兼容性问题，正在切换到兼容模式。",
            ErrorCategory.PERFORMANCE_DEGRADATION: "性能下降，正在优化渲染设置。",
            ErrorCategory.UNKNOWN_ERROR: "遇到未知错误，正在尝试自动修复。"
        }

        base_message = messages.get(category, "发生了图形渲染错误。")

        if severity == ErrorSeverity.CRITICAL:
            return f" {base_message}"
        elif severity == ErrorSeverity.HIGH:
            return f" {base_message}"
        else:
            return f"ℹ {base_message}"

    def _record_error(self, error_info: ErrorInfo) -> None:
        """记录错误信息"""
        self.error_history.append(error_info)

        # 限制历史记录长度
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]

        # 记录日志
        if error_info.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            logger.error(f"严重错误: {error_info.category.value} - {error_info.message}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"中等错误: {error_info.category.value} - {error_info.message}")
        else:
            logger.info(f"轻微错误: {error_info.category.value} - {error_info.message}")

    def _attempt_recovery(self, error_info: ErrorInfo, context: Dict[str, Any]) -> Optional[RecoveryResult]:
        """尝试错误恢复"""
        if not error_info.recovery_strategies:
            logger.warning(f"没有可用的恢复策略: {error_info.category.value}")
            return None

        for strategy in error_info.recovery_strategies:
            if strategy == RecoveryStrategy.NO_RECOVERY:
                continue

            if strategy == RecoveryStrategy.USER_INTERVENTION:
                return RecoveryResult(
                    success=False,
                    strategy_used=strategy,
                    message="需要用户手动干预解决问题"
                )

            action = self.recovery_actions.get(strategy)
            if not action:
                logger.warning(f"未找到恢复动作: {strategy.value}")
                continue

            try:
                logger.info(f"尝试恢复策略: {strategy.value}")
                result = action.execute(context)

                if result.success:
                    logger.info(f"恢复成功: {result.message}")
                    return result
                else:
                    logger.warning(f"恢复失败: {result.message}")

            except Exception as e:
                logger.error(f"恢复策略执行异常: {strategy.value} - {e}")

        return None

    def _update_statistics(self, error_info: ErrorInfo, recovery_result: Optional[RecoveryResult]) -> None:
        """更新统计信息"""
        self.statistics.total_errors += 1

        # 按类别统计
        if error_info.category not in self.statistics.errors_by_category:
            self.statistics.errors_by_category[error_info.category] = 0
        self.statistics.errors_by_category[error_info.category] += 1

        # 按严重程度统计
        if error_info.severity not in self.statistics.errors_by_severity:
            self.statistics.errors_by_severity[error_info.severity] = 0
        self.statistics.errors_by_severity[error_info.severity] += 1

        # 更新恢复成功率
        if recovery_result:
            successful_recoveries = sum(1 for err in self.error_history
                                        if hasattr(err, 'recovery_successful') and err.recovery_successful)
            self.statistics.recovery_success_rate = successful_recoveries / self.statistics.total_errors

            # 标记当前错误的恢复状态
            error_info.context['recovery_successful'] = recovery_result.success

        # 更新最常见错误
        self.statistics.most_common_error = max(
            self.statistics.errors_by_category.items(),
            key=lambda x: x[1]
        )[0]

    def get_error_statistics(self) -> ErrorStatistics:
        """获取错误统计信息"""
        with self._lock:
            return self.statistics

    def get_recent_errors(self, limit: int = 10) -> List[ErrorInfo]:
        """获取最近的错误信息"""
        with self._lock:
            return self.error_history[-limit:]

    def clear_error_history(self) -> None:
        """清空错误历史"""
        with self._lock:
            self.error_history.clear()
            self.statistics = ErrorStatistics()

    def export_error_report(self, file_path: str) -> None:
        """导出错误报告"""
        try:
            import json

            report_data = {
                'timestamp': time.time(),
                'statistics': {
                    'total_errors': self.statistics.total_errors,
                    'recovery_success_rate': self.statistics.recovery_success_rate,
                    'most_common_error': self.statistics.most_common_error.value if self.statistics.most_common_error else None,
                    'errors_by_category': {cat.value: count for cat, count in self.statistics.errors_by_category.items()},
                    'errors_by_severity': {sev.value: count for sev, count in self.statistics.errors_by_severity.items()}
                },
                'recent_errors': [
                    {
                        'category': err.category.value,
                        'severity': err.severity.value,
                        'message': err.message,
                        'user_message': err.user_message,
                        'timestamp': err.timestamp
                    }
                    for err in self.error_history[-50:]  # 最近50个错误
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logger.info(f"错误报告已导出到: {file_path}")

        except Exception as e:
            logger.error(f"导出错误报告失败: {e}")


# 全局错误恢复管理器实例
_global_error_manager: Optional[ErrorRecoveryManager] = None


def get_error_recovery_manager() -> ErrorRecoveryManager:
    """获取全局错误恢复管理器"""
    global _global_error_manager
    if _global_error_manager is None:
        _global_error_manager = ErrorRecoveryManager()
    return _global_error_manager


def handle_webgpu_error(error_message: str, exception: Optional[Exception] = None,
                        context: Optional[Dict[str, Any]] = None) -> Optional[RecoveryResult]:
    """处理WebGPU错误的快捷函数"""
    manager = get_error_recovery_manager()
    return manager.handle_error(error_message, exception, context)


def setup_error_recovery_context(current_engine: str = "webgpu",
                                 switch_engine_function: Optional[Callable] = None,
                                 quality_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """设置错误恢复上下文"""
    context = {
        'current_engine': current_engine,
        'switch_engine_function': switch_engine_function,
        'quality_settings': quality_settings or {}
    }

    return context


if __name__ == "__main__":
    # 错误处理测试示例
    manager = get_error_recovery_manager()

    # 模拟WebGPU不支持错误
    context = setup_error_recovery_context(
        current_engine="webgpu",
        switch_engine_function=lambda engine: logger.info(f"切换到引擎: {engine}")
    )

    result = manager.handle_error(
        "WebGPU is not supported in this browser",
        context=context
    )

    if result:
        logger.info(f"恢复结果: {result.message}")
        logger.info(f"新引擎: {result.new_engine}")

    # 获取统计信息
    stats = manager.get_error_statistics()
    logger.info(f"错误统计: {stats.total_errors} 个错误，恢复成功率: {stats.recovery_success_rate:.1%}")
