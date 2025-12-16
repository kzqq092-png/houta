"""
专业性能优化器模块

提供统一的性能优化接口和优化级别配置
"""

from enum import Enum
from typing import Dict, Any, Optional
from loguru import logger
import psutil


class OptimizationLevel(Enum):
    """优化级别枚举"""
    BASIC = "basic"              # 基础优化
    STANDARD = "standard"        # 标准优化
    AGGRESSIVE = "aggressive"    # 激进优化
    PROFESSIONAL = "professional"  # 专业级优化


class ProfessionalPerformanceOptimizer:
    """
    专业性能优化器
    
    提供性能监控、资源管理和优化建议
    """
    
    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.PROFESSIONAL):
        """
        初始化性能优化器
        Args:
            optimization_level: 优化级别
        """
        self.logger = logger.bind(module=self.__class__.__name__)
        self.optimization_level = optimization_level
        
        # 性能阈值配置
        self.thresholds = self._get_thresholds()
        # 性能统计
        self.stats = {
            'cpu_usage_samples': [],
            'memory_usage_samples': [],
            'optimization_suggestions': []
        }
    
    def _get_thresholds(self) -> Dict[str, Any]:
        """根据优化级别获取性能阈值"""
        thresholds = {
            OptimizationLevel.BASIC: {
                'max_cpu': 90.0,
                'max_memory': 90.0,
                'min_vectorization': 0.3,
                'min_parallel_efficiency': 0.5
            },
            OptimizationLevel.STANDARD: {
                'max_cpu': 80.0,
                'max_memory': 85.0,
                'min_vectorization': 0.5,
                'min_parallel_efficiency': 0.7
            },
            OptimizationLevel.AGGRESSIVE: {
                'max_cpu': 70.0,
                'max_memory': 80.0,
                'min_vectorization': 0.7,
                'min_parallel_efficiency': 0.8
            },
            OptimizationLevel.PROFESSIONAL: {
                'max_cpu': 60.0,
                'max_memory': 75.0,
                'min_vectorization': 0.8,
                'min_parallel_efficiency': 0.9
            }
        }
        return thresholds.get(self.optimization_level, thresholds[OptimizationLevel.STANDARD])
    
    def monitor_performance(self) -> Dict[str, float]:
        """
        监控当前性能指标
        Returns:
            性能指标字典
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            # 记录样本
            self.stats['cpu_usage_samples'].append(cpu_percent)
            self.stats['memory_usage_samples'].append(memory_percent)
            # 保持最近100个样本
            if len(self.stats['cpu_usage_samples']) > 100:
                self.stats['cpu_usage_samples'].pop(0)
            if len(self.stats['memory_usage_samples']) > 100:
                self.stats['memory_usage_samples'].pop(0)
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'cpu_available': 100 - cpu_percent,
                'memory_available': 100 - memory_percent
            }
        except Exception as e:
            self.logger.error(f"性能监控失败: {e}")
            return {
                'cpu_percent': 0.0,
                'memory_percent': 0.0,
                'cpu_available': 100.0,
                'memory_available': 100.0
            }
    
    def check_resource_availability(self) -> bool:
        """
        检查资源是否充足
        Returns:
            True表示资源充足，False表示资源紧张
        """
        metrics = self.monitor_performance()
        cpu_ok = metrics['cpu_percent'] < self.thresholds['max_cpu']
        memory_ok = metrics['memory_percent'] < self.thresholds['max_memory']
        if not cpu_ok:
            self.logger.warning(f"CPU使用率过高: {metrics['cpu_percent']:.1f}% (阈值: {self.thresholds['max_cpu']}%)")
        if not memory_ok:
            self.logger.warning(f"内存使用率过高: {metrics['memory_percent']:.1f}% (阈值: {self.thresholds['max_memory']}%)")
        return cpu_ok and memory_ok
    
    def get_optimization_suggestions(self) -> list:
        """
        获取优化建议
        Returns:
            优化建议列表
        """
        suggestions = []
        if not self.check_resource_availability():
            suggestions.append("资源使用率过高，建议降低并发数或优化算法")
        # 检查CPU使用趋势
        if len(self.stats['cpu_usage_samples']) >= 10:
            recent_cpu = sum(self.stats['cpu_usage_samples'][-10:]) / 10
            if recent_cpu > self.thresholds['max_cpu']:
                suggestions.append(f"CPU使用率持续偏高（{recent_cpu:.1f}%），考虑使用更高效的算法")
        # 检查内存使用趋势
        if len(self.stats['memory_usage_samples']) >= 10:
            recent_memory = sum(self.stats['memory_usage_samples'][-10:]) / 10
            if recent_memory > self.thresholds['max_memory']:
                suggestions.append(f"内存使用率持续偏高（{recent_memory:.1f}%），考虑分批处理或释放缓存")
        return suggestions
    
    def optimize(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        执行优化操作
        Args:
            operation: 操作类型
            **kwargs: 操作参数
        Returns:
            优化结果
        """
        if operation == "check_resources":
            return {
                'available': self.check_resource_availability(),
                'metrics': self.monitor_performance(),
                'suggestions': self.get_optimization_suggestions()
            }
        elif operation == "get_optimal_workers":
            # 根据当前资源情况推荐最优工作线程数
            metrics = self.monitor_performance()
            cpu_count = psutil.cpu_count()
            if metrics['cpu_percent'] > 80:
                optimal_workers = max(1, cpu_count // 2)
            elif metrics['cpu_percent'] > 60:
                optimal_workers = cpu_count
            else:
                optimal_workers = min(32, cpu_count + 4)
            return {
                'optimal_workers': optimal_workers,
                'reason': f"基于当前CPU使用率{metrics['cpu_percent']:.1f}%"
            }
        else:
            self.logger.warning(f"未知的优化操作: {operation}")
            return {'success': False, 'error': '未知操作'}
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'cpu_usage_samples': [],
            'memory_usage_samples': [],
            'optimization_suggestions': []
        }
        self.logger.info("性能统计已重置")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'optimization_level': self.optimization_level.value,
            'thresholds': self.thresholds,
            'samples_count': len(self.stats['cpu_usage_samples']),
            'avg_cpu': sum(self.stats['cpu_usage_samples']) / len(self.stats['cpu_usage_samples']) if self.stats['cpu_usage_samples'] else 0,
            'avg_memory': sum(self.stats['memory_usage_samples']) / len(self.stats['memory_usage_samples']) if self.stats['memory_usage_samples'] else 0
        }

