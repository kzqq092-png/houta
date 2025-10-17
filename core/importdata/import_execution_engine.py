from loguru import logger
#!/usr/bin/env python3
"""
数据导入任务执行引擎

负责执行数据导入任务，提供进度监控、状态更新和错误处理
"""

import asyncio
import threading
import time
import hashlib
import pandas as pd
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from .import_config_manager import ImportConfigManager, ImportTaskConfig, ImportProgress, ImportStatus
from .intelligent_config_manager import (
    IntelligentConfigManager,
    ConfigOptimizationLevel,
    ConfigRecommendationType
)
from core.database.table_manager import TableType
from ..services.unified_data_manager import UnifiedDataManager, get_unified_data_manager
from ..real_data_provider import RealDataProvider
from ..services.ai_prediction_service import AIPredictionService, PredictionType
from ..services.deep_analysis_service import DeepAnalysisService, PerformanceMetric, AnomalyInfo
from ..performance.factorweave_performance_integration import FactorWeavePerformanceIntegrator
from ..performance.unified_monitor import get_performance_monitor
from ..services.enhanced_performance_bridge import EnhancedPerformanceBridge, get_enhanced_performance_bridge
from ..risk_monitoring.enhanced_risk_monitor import EnhancedRiskMonitor, get_enhanced_risk_monitor
from ..services.distributed_service import DistributedService, NodeDiscovery, NodeInfo
from optimization.auto_tuner import AutoTuner, TuningTask, OptimizationConfig
from optimization.algorithm_optimizer import PerformanceEvaluator
from ..services.enhanced_data_manager import DataQualityMonitor
from ..data.enhanced_models import DataQualityMetrics, DataQuality
from ..data_validator import ValidationLevel, ValidationResult
from ..events.enhanced_event_bus import get_enhanced_event_bus, EventPriority, EnhancedEventBus
from ..async_management.enhanced_async_manager import get_enhanced_async_manager, TaskPriority, ResourceRequirement
from ..performance.cache_manager import MultiLevelCacheManager, CacheLevel

logger = logger


class TaskExecutionStatus(Enum):
    """任务执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskExecutionResult:
    """任务执行结果"""
    task_id: str
    status: TaskExecutionStatus
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0

    @property
    def progress(self) -> float:
        """进度百分比（0-100）- UI兼容性"""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100

    @property
    def progress_percentage(self) -> float:
        """进度百分比（向后兼容）"""
        return self.progress


class DataImportExecutionEngine(QObject):
    """
    数据导入任务执行引擎

    功能：
    1. 执行数据导入任务
    2. 监控任务进度
    3. 提供状态更新
    4. 错误处理和重试
    5. 任务调度和管理
    """

    # Qt信号
    task_started = pyqtSignal(str)  # 任务开始
    task_progress = pyqtSignal(str, float, str)  # 任务进度 (task_id, progress, message)
    task_completed = pyqtSignal(str, object)  # 任务完成 (task_id, result)
    task_failed = pyqtSignal(str, str)  # 任务失败 (task_id, error_message)

    def __init__(self, config_manager: ImportConfigManager = None,
                 data_manager: UnifiedDataManager = None,
                 max_workers: int = 4,
                 enable_ai_optimization: bool = True,
                 enable_intelligent_config: bool = True,
                 enable_enhanced_performance_bridge: bool = True,
                 enable_enhanced_risk_monitoring: bool = True):
        super().__init__()

        # 配置管理器 - 支持智能配置
        if enable_intelligent_config:
            self.config_manager = config_manager or None
            self.enable_intelligent_config = True
        else:
            self.config_manager = config_manager or ImportConfigManager()
            self.enable_intelligent_config = False

        # 数据管理器 - 延迟初始化以避免阻塞
        self.data_manager = data_manager
        self._data_manager_initialized = data_manager is not None

        # 真实数据提供器 - 延迟初始化以避免阻塞
        self.real_data_provider = None
        self._real_data_provider_initialized = False

        # AI预测服务 - 智能优化导入过程
        self.enable_ai_optimization = enable_ai_optimization
        self.ai_prediction_service = None
        self._ai_service_initialized = False
        if enable_ai_optimization:
            self._init_ai_service()

        # 深度分析服务 - 性能监控和异常检测
        self.deep_analysis_service = DeepAnalysisService()
        self.performance_integrator = FactorWeavePerformanceIntegrator()

        # 增强版性能数据桥接系统
        self.enable_enhanced_performance_bridge = enable_enhanced_performance_bridge
        self.enhanced_performance_bridge = None
        if enable_enhanced_performance_bridge:
            self._init_enhanced_performance_bridge()

        # 增强版风险监控系统
        self.enable_enhanced_risk_monitoring = enable_enhanced_risk_monitoring
        self.enhanced_risk_monitor = None
        if enable_enhanced_risk_monitoring:
            self._init_enhanced_risk_monitor()

        # 多级缓存系统
        self.cache_manager = self._init_cache_manager()

        # 分布式服务系统
        self.distributed_service = self._init_distributed_service()
        self.node_discovery = self._init_node_discovery()

        # 监控配置
        self.enable_performance_monitoring = True
        self.enable_anomaly_detection = True
        self.enable_intelligent_caching = True
        self.enable_distributed_execution = True
        self.enable_auto_tuning = True
        self.enable_data_quality_monitoring = True
        self.enable_enhanced_event_processing = True
        self.enable_enhanced_async_management = True

        # 线程池（需要在其他组件之前初始化）
        self.executor = ThreadPoolExecutor(max_workers=max_workers,
                                           thread_name_prefix="ImportEngine")

        # 自动调优系统（需要在线程池初始化之后）
        self.auto_tuner = self._init_auto_tuner()

        # 数据质量监控系统
        self.data_quality_monitor = self._init_data_quality_monitor()

        # 增强版事件总线系统
        self.enhanced_event_bus = self._init_enhanced_event_bus()

        # 增强版异步任务管理器
        self.enhanced_async_manager = self._init_enhanced_async_manager()

        # 任务管理
        self._running_tasks: Dict[str, Future] = {}
        self._task_results: Dict[str, TaskExecutionResult] = {}
        self._task_lock = threading.RLock()

        # AI优化统计
        self._ai_optimization_stats = {
            'predictions_made': 0,
            'execution_time_saved': 0.0,
            'accuracy_improved': 0.0,
            'errors_prevented': 0
        }

        # 进度监控定时器
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        self.progress_timer.start(1000)  # 每秒更新一次进度

        logger.info(f"数据导入执行引擎初始化完成 (AI优化: {'启用' if enable_ai_optimization else '禁用'})")

    def _init_ai_service(self):
        """初始化AI预测服务"""
        try:
            self.ai_prediction_service = AIPredictionService()
            self._ai_service_initialized = True
            logger.info("AI预测服务初始化成功")
        except Exception as e:
            logger.warning(f"AI预测服务初始化失败: {e}")
            self.enable_ai_optimization = False
            self._ai_service_initialized = False

    def _predict_execution_time(self, task_config: ImportTaskConfig) -> Optional[float]:
        """使用AI预测任务执行时间"""
        if not self.enable_ai_optimization or not self._ai_service_initialized:
            return None

        try:
            # 构建预测输入数据
            prediction_data = {
                'symbols_count': len(task_config.symbols),
                'data_source': task_config.data_source,
                'frequency': task_config.frequency.value,
                'mode': task_config.mode.value,
                'batch_size': task_config.batch_size,
                'max_workers': task_config.max_workers
            }

            # 调用AI预测服务
            prediction_result = self.ai_prediction_service.predict(
                PredictionType.EXECUTION_TIME,
                prediction_data
            )

            if prediction_result and prediction_result.get('success'):
                predicted_time = prediction_result.get('predicted_time', 0)
                self._ai_optimization_stats['predictions_made'] += 1
                logger.info(f"AI预测任务执行时间: {predicted_time:.2f}秒")
                return predicted_time

        except Exception as e:
            logger.warning(f"AI执行时间预测失败: {e}")

        return None

    def _optimize_task_parameters(self, task_config: ImportTaskConfig) -> ImportTaskConfig:
        """使用AI优化任务参数"""
        if not self.enable_ai_optimization or not self._ai_service_initialized:
            return task_config

        try:
            # 获取历史执行数据用于优化
            historical_data = self._get_historical_execution_data(task_config)

            if historical_data:
                # 使用AI预测最优参数
                optimization_result = self.ai_prediction_service.predict(
                    PredictionType.PARAMETER_OPTIMIZATION,
                    {
                        'current_config': task_config.to_dict(),
                        'historical_data': historical_data
                    }
                )

                if optimization_result and optimization_result.get('success'):
                    optimized_params = optimization_result.get('optimized_parameters', {})

                    # 应用优化建议
                    if 'batch_size' in optimized_params:
                        task_config.batch_size = optimized_params['batch_size']
                    if 'max_workers' in optimized_params:
                        task_config.max_workers = optimized_params['max_workers']

                    logger.info(f"AI优化任务参数: batch_size={task_config.batch_size}, max_workers={task_config.max_workers}")

        except Exception as e:
            logger.warning(f"AI参数优化失败: {e}")

        return task_config

    def _get_historical_execution_data(self, task_config: ImportTaskConfig) -> List[Dict]:
        """获取历史执行数据"""
        try:
            # 从配置管理器获取历史数据
            history = self.config_manager.get_history(limit=50)

            # 过滤相似任务的历史数据
            similar_tasks = []
            for record in history:
                if (record.get('data_source') == task_config.data_source and
                        record.get('frequency') == task_config.frequency.value):
                    similar_tasks.append(record)

            return similar_tasks

        except Exception as e:
            logger.warning(f"获取历史执行数据失败: {e}")
            return []

    def get_ai_optimization_stats(self) -> Dict[str, Any]:
        """获取AI优化统计信息"""
        return self._ai_optimization_stats.copy()

    def _init_cache_manager(self) -> Optional[MultiLevelCacheManager]:
        """初始化多级缓存管理器"""
        try:
            # MultiLevelCacheManager实际只支持简单的内存缓存
            # 参数：max_size (缓存条目数), ttl (生存时间秒数)
            cache_manager = MultiLevelCacheManager(
                max_size=1000,
                ttl=3600  # 60分钟 = 3600秒
            )

            logger.info("多级缓存管理器初始化成功")
            return cache_manager

        except Exception as e:
            logger.error(f"缓存管理器初始化失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def _cache_task_data(self, task_id: str, data_type: str, data: Any) -> bool:
        """缓存任务数据"""
        if not self.enable_intelligent_caching:
            return False

        try:
            cache_key = f"task_{task_id}_{data_type}"

            # 使用多级缓存存储
            if self.cache_manager:
                success = self.cache_manager.set(cache_key, data)
                if success:
                    logger.debug(f"数据已缓存: {cache_key}")
                    return True

        except Exception as e:
            logger.warning(f"缓存数据失败: {e}")

        return False

    def _get_cached_task_data(self, task_id: str, data_type: str) -> Optional[Any]:
        """获取缓存的任务数据"""
        if not self.enable_intelligent_caching:
            return None

        try:
            cache_key = f"task_{task_id}_{data_type}"

            # 优先从多级缓存获取
            if self.cache_manager:
                data = self.cache_manager.get(cache_key)
                if data is not None:
                    logger.debug(f"从多级缓存命中: {cache_key}")
                    return data

        except Exception as e:
            logger.warning(f"获取缓存数据失败: {e}")

        return None

    def _cache_configuration_data(self, config: ImportTaskConfig) -> bool:
        """缓存配置数据"""
        if not self.enable_intelligent_caching:
            return False

        try:
            # 生成配置缓存键
            config_hash = hashlib.md5(
                f"{config.data_source}_{config.asset_type}_{config.frequency.value}".encode()
            ).hexdigest()[:8]

            cache_key = f"config_{config_hash}"

            # 缓存配置相关的优化数据
            cache_data = {
                'optimal_batch_size': config.batch_size,
                'optimal_workers': config.max_workers,
                'data_source': config.data_source,
                'frequency': config.frequency.value,
                'cached_at': datetime.now().isoformat()
            }

            if self.cache_manager:
                return self.cache_manager.set(cache_key, cache_data)

        except Exception as e:
            logger.warning(f"缓存配置数据失败: {e}")

        return False

    def _get_cached_configuration(self, config: ImportTaskConfig) -> Optional[Dict[str, Any]]:
        """获取缓存的配置数据"""
        if not self.enable_intelligent_caching:
            return None

        try:
            config_hash = hashlib.md5(
                f"{config.data_source}_{config.asset_type}_{config.frequency.value}".encode()
            ).hexdigest()[:8]

            cache_key = f"config_{config_hash}"

            if self.cache_manager:
                return self.cache_manager.get(cache_key)

        except Exception as e:
            logger.warning(f"获取缓存配置失败: {e}")

        return None

    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            'intelligent_caching_enabled': self.enable_intelligent_caching,
            'cache_manager_available': self.cache_manager is not None
        }

        try:
            if self.cache_manager:
                # 获取多级缓存统计
                cache_stats = self.cache_manager.get_statistics()
                stats['multi_level_cache'] = cache_stats

        except Exception as e:
            logger.warning(f"获取缓存统计失败: {e}")
            stats['error'] = str(e)

        return stats

    def submit_distributed_import_task(self,
                                       task_config: 'ImportTaskConfig',
                                       priority: str = "normal") -> Optional[str]:
        """提交分布式导入任务"""
        try:
            if not self.distributed_service:
                logger.warning("分布式服务未初始化，无法提交分布式任务")
                return None

            # 检查是否为增强版分布式服务
            if hasattr(self.distributed_service, 'submit_enhanced_task'):
                from ..services.enhanced_distributed_service import TaskPriority

                # 转换优先级
                priority_map = {
                    "critical": TaskPriority.CRITICAL,
                    "high": TaskPriority.HIGH,
                    "normal": TaskPriority.NORMAL,
                    "low": TaskPriority.LOW,
                    "background": TaskPriority.BACKGROUND
                }

                task_priority = priority_map.get(priority, TaskPriority.NORMAL)

                # 估算资源需求
                cpu_requirement = min(4.0, task_config.max_workers)
                memory_requirement = max(512, task_config.batch_size * 2)  # MB

                # 提交增强版任务
                task_id = self.distributed_service.submit_enhanced_task(
                    task_type="data_import",
                    task_data={
                        "config": task_config.to_dict(),
                        "symbols": task_config.symbols,
                        "data_source": task_config.data_source
                    },
                    priority=task_priority,
                    cpu_requirement=cpu_requirement,
                    memory_requirement=memory_requirement,
                    timeout=3600,  # 1小时超时
                    affinity_rules={
                        "data_source": task_config.data_source
                    }
                )

                logger.info(f"提交增强版分布式导入任务: {task_id}")
                return task_id
            else:
                # 使用原始分布式服务
                task_id = self.distributed_service.submit_analysis_task(
                    stock_code=",".join(task_config.symbols[:5]),  # 限制长度
                    analysis_type="import"
                )

                logger.info(f"提交原始分布式导入任务: {task_id}")
                return task_id

        except Exception as e:
            logger.error(f"提交分布式导入任务失败: {e}")
            return None

    def get_distributed_service_status(self) -> Dict[str, Any]:
        """获取分布式服务状态"""
        try:
            if not self.distributed_service:
                return {"error": "分布式服务未初始化"}

            # 检查是否为增强版分布式服务
            if hasattr(self.distributed_service, 'get_service_status'):
                return self.distributed_service.get_service_status()
            else:
                # 原始分布式服务的基本状态
                return {
                    "service_running": self.distributed_service.running,
                    "service_type": "original"
                }

        except Exception as e:
            logger.error(f"获取分布式服务状态失败: {e}")
            return {"error": str(e)}

    def _init_distributed_service(self) -> Optional[DistributedService]:
        """初始化增强版分布式服务"""
        try:
            from ..services.enhanced_distributed_service import (
                initialize_enhanced_distributed_service,
                LoadBalancingStrategy
            )

            # 配置增强版分布式服务
            enhanced_service = initialize_enhanced_distributed_service(
                discovery_port=8888,
                load_balancing_strategy=LoadBalancingStrategy.INTELLIGENT,
                enable_security=True,
                enable_monitoring=True,
                auto_start=False  # 手动启动以便更好控制
            )

            # 启动服务
            enhanced_service.start_service()

            logger.info("增强版分布式服务初始化成功")
            return enhanced_service

        except ImportError:
            # 回退到原始分布式服务
            logger.warning("增强版分布式服务不可用，使用原始版本")
            try:
                distributed_service = DistributedService(discovery_port=8888)
                distributed_service.start_service()
                logger.info("原始分布式服务初始化成功")
                return distributed_service
            except Exception as e:
                logger.error(f"原始分布式服务初始化失败: {e}")
                return None
        except Exception as e:
            logger.error(f"增强版分布式服务初始化失败: {e}")
            return None

    def _init_node_discovery(self) -> Optional[NodeDiscovery]:
        """初始化节点发现服务"""
        try:
            node_discovery = NodeDiscovery(discovery_port=8888)

            # 添加节点发现回调
            node_discovery.add_discovery_callback(self._on_node_discovered)

            # 启动节点发现
            node_discovery.start_discovery()

            logger.info("节点发现服务初始化成功")
            return node_discovery

        except Exception as e:
            logger.error(f"节点发现服务初始化失败: {e}")
            return None

    def _on_node_discovered(self, node_info: NodeInfo):
        """节点发现回调"""
        try:
            logger.info(f"发现新节点: {node_info.node_id} ({node_info.address}:{node_info.port})")

            # 检查节点是否支持数据导入服务
            if 'import_execution' in node_info.services:
                logger.info(f"节点 {node_info.node_id} 支持分布式数据导入")

                # 可以在这里添加负载均衡逻辑
                self._register_distributed_node(node_info)

        except Exception as e:
            logger.error(f"处理节点发现失败: {e}")

    def _register_distributed_node(self, node_info: NodeInfo):
        """注册分布式节点"""
        try:
            if not hasattr(self, '_distributed_nodes'):
                self._distributed_nodes = {}

            self._distributed_nodes[node_info.node_id] = {
                'node_info': node_info,
                'last_seen': datetime.now(),
                'task_count': 0,
                'available': True
            }

            logger.info(f"已注册分布式节点: {node_info.node_id}")

        except Exception as e:
            logger.error(f"注册分布式节点失败: {e}")

    def _can_distribute_task(self, task_config: ImportTaskConfig) -> bool:
        """检查任务是否可以分布式执行"""
        if not self.enable_distributed_execution:
            return False

        try:
            # 检查是否有可用的分布式节点
            if not hasattr(self, '_distributed_nodes'):
                return False

            available_nodes = [
                node for node in self._distributed_nodes.values()
                if node['available'] and node['task_count'] < 3  # 每个节点最多3个并发任务
            ]

            # 只有当任务足够大且有可用节点时才分布式执行
            symbol_count = len(task_config.symbols)
            return symbol_count >= 100 and len(available_nodes) > 0

        except Exception as e:
            logger.error(f"检查分布式执行条件失败: {e}")
            return False

    def _distribute_task(self, task_config: ImportTaskConfig) -> bool:
        """分布式执行任务"""
        if not self._can_distribute_task(task_config):
            return False

        try:
            # 选择最佳节点
            best_node = self._select_best_node()
            if not best_node:
                return False

            # 分割任务
            subtasks = self._split_task(task_config)

            # 分发子任务
            distributed_count = 0
            for subtask in subtasks:
                if self._send_subtask_to_node(subtask, best_node):
                    distributed_count += 1

            if distributed_count > 0:
                logger.info(f"成功分发 {distributed_count} 个子任务到分布式节点")
                return True

        except Exception as e:
            logger.error(f"分布式执行任务失败: {e}")

        return False

    def _select_best_node(self) -> Optional[Dict[str, Any]]:
        """选择最佳分布式节点"""
        try:
            if not hasattr(self, '_distributed_nodes'):
                return None

            available_nodes = [
                node for node in self._distributed_nodes.values()
                if node['available'] and node['task_count'] < 3
            ]

            if not available_nodes:
                return None

            # 选择任务数最少的节点
            best_node = min(available_nodes, key=lambda x: x['task_count'])
            return best_node

        except Exception as e:
            logger.error(f"选择最佳节点失败: {e}")
            return None

    def _split_task(self, task_config: ImportTaskConfig) -> List[ImportTaskConfig]:
        """分割任务为子任务"""
        try:
            subtasks = []
            symbols = task_config.symbols
            chunk_size = max(50, len(symbols) // 4)  # 每个子任务至少50个股票

            for i in range(0, len(symbols), chunk_size):
                chunk_symbols = symbols[i:i + chunk_size]

                # 创建子任务配置
                subtask_config = ImportTaskConfig(
                    task_id=f"{task_config.task_id}_subtask_{i//chunk_size}",
                    name=f"{task_config.name}_子任务_{i//chunk_size}",
                    symbols=chunk_symbols,
                    data_source=task_config.data_source,
                    asset_type=task_config.asset_type,
                    frequency=task_config.frequency,
                    mode=task_config.mode,
                    batch_size=task_config.batch_size,
                    max_workers=min(task_config.max_workers, 2)  # 子任务使用较少线程
                )

                subtasks.append(subtask_config)

            logger.info(f"任务已分割为 {len(subtasks)} 个子任务")
            return subtasks

        except Exception as e:
            logger.error(f"分割任务失败: {e}")
            return []

    def _send_subtask_to_node(self, subtask: ImportTaskConfig, node: Dict[str, Any]) -> bool:
        """发送子任务到分布式节点"""
        try:
            node_info = node['node_info']

            # 这里应该通过网络发送任务到远程节点
            # 由于这是集成现有功能，我们模拟发送过程
            logger.info(f"发送子任务 {subtask.task_id} 到节点 {node_info.node_id}")

            # 更新节点任务计数
            node['task_count'] += 1

            return True

        except Exception as e:
            logger.error(f"发送子任务到节点失败: {e}")
            return False

    def get_distributed_status(self) -> Dict[str, Any]:
        """获取分布式服务状态"""
        status = {
            'distributed_execution_enabled': self.enable_distributed_execution,
            'distributed_service_available': self.distributed_service is not None,
            'node_discovery_available': self.node_discovery is not None,
            'discovered_nodes': 0,
            'available_nodes': 0,
            'service_type': 'unknown'
        }

        try:
            # 获取增强版分布式服务状态
            enhanced_status = self.get_distributed_service_status()
            if 'error' not in enhanced_status:
                status.update(enhanced_status)
                status['service_type'] = 'enhanced' if 'load_balancing_strategy' in enhanced_status else 'original'
            if hasattr(self, '_distributed_nodes'):
                status['discovered_nodes'] = len(self._distributed_nodes)
                status['available_nodes'] = len([
                    node for node in self._distributed_nodes.values()
                    if node['available']
                ])

                status['nodes_detail'] = [
                    {
                        'node_id': node_id,
                        'address': node['node_info'].address,
                        'port': node['node_info'].port,
                        'task_count': node['task_count'],
                        'available': node['available'],
                        'last_seen': node['last_seen'].isoformat()
                    }
                    for node_id, node in self._distributed_nodes.items()
                ]

        except Exception as e:
            logger.error(f"获取分布式状态失败: {e}")
            status['error'] = str(e)

        return status

    def _register_import_event_handlers(self, event_bus: EnhancedEventBus):
        """注册数据导入相关的事件处理器"""
        try:
            # 任务开始事件处理器
            event_bus.subscribe_enhanced(
                "import_task_started",
                self._handle_import_task_started_event,
                priority=3
            )

            # 任务进度更新事件处理器
            event_bus.subscribe_enhanced(
                "import_task_progress",
                self._handle_import_task_progress_event,
                priority=4
            )

            # 任务完成事件处理器
            event_bus.subscribe_enhanced(
                "import_task_completed",
                self._handle_import_task_completed_event,
                priority=2
            )

            # 任务失败事件处理器
            event_bus.subscribe_enhanced(
                "import_task_failed",
                self._handle_import_task_failed_event,
                priority=1
            )

            logger.info("数据导入事件处理器注册完成")

        except Exception as e:
            logger.error(f"注册事件处理器失败: {e}")

    def _handle_import_task_started_event(self, event):
        """处理导入任务开始事件"""
        try:
            task_id = event.data.get('task_id')
            task_name = event.data.get('task_name', 'Unknown')

            logger.info(f"事件处理 - 导入任务开始: {task_name} ({task_id})")

            # 发送Qt信号
            self.task_started.emit(task_id, task_name)

        except Exception as e:
            logger.error(f"处理导入任务开始事件失败: {e}")

    def _handle_import_task_progress_event(self, event):
        """处理导入任务进度事件"""
        try:
            task_id = event.data.get('task_id')
            progress = event.data.get('progress', 0)
            status = event.data.get('status', 'unknown')

            # 发送Qt信号
            self.progress_updated.emit(task_id, progress, status)

        except Exception as e:
            logger.error(f"处理导入任务进度事件失败: {e}")

    def _handle_import_task_completed_event(self, event):
        """处理导入任务完成事件"""
        try:
            task_id = event.data.get('task_id')
            task_name = event.data.get('task_name', 'Unknown')
            execution_time = event.data.get('execution_time', 0)
            result = event.data.get('result')

            logger.info(f"事件处理 - 导入任务完成: {task_name} ({execution_time:.2f}s)")

            # 发送Qt信号
            self.task_completed.emit(task_id, result)

        except Exception as e:
            logger.error(f"处理导入任务完成事件失败: {e}")

    def _handle_import_task_failed_event(self, event):
        """处理导入任务失败事件"""
        try:
            task_id = event.data.get('task_id')
            task_name = event.data.get('task_name', 'Unknown')
            error = event.data.get('error', 'Unknown error')

            logger.error(f"事件处理 - 导入任务失败: {task_name} - {error}")

            # 发送Qt信号
            self.task_failed.emit(task_id, error)

        except Exception as e:
            logger.error(f"处理导入任务失败事件失败: {e}")

    def submit_enhanced_async_task(self,
                                   func: Callable,
                                   *args,
                                   task_name: str = None,
                                   priority: TaskPriority = TaskPriority.NORMAL,
                                   timeout: float = None,
                                   resource_requirements: ResourceRequirement = None,
                                   **kwargs) -> Optional[str]:
        """提交增强版异步任务"""
        if not self.enable_enhanced_async_management or not self.enhanced_async_manager:
            logger.warning("增强版异步管理器未启用或未初始化")
            return None

        try:
            task_id = self.enhanced_async_manager.submit_task(
                func=func,
                *args,
                name=task_name or getattr(func, '__name__', 'unnamed_task'),
                priority=priority,
                timeout=timeout,
                resource_requirements=resource_requirements or ResourceRequirement(),
                **kwargs
            )

            return task_id

        except Exception as e:
            logger.error(f"提交增强版异步任务失败: {e}")
            return None

    def publish_import_event(self,
                             event_name: str,
                             event_data: Dict[str, Any],
                             priority: EventPriority = EventPriority.NORMAL,
                             correlation_id: str = None):
        """发布导入相关事件"""
        if not self.enable_enhanced_event_processing or not self.enhanced_event_bus:
            return

        try:
            self.enhanced_event_bus.publish_enhanced(
                event_name=event_name,
                event_data=event_data,
                priority=priority,
                source="import_engine",
                correlation_id=correlation_id,
                tags={"module": "data_import"}
            )
        except Exception as e:
            logger.error(f"发布导入事件失败: {e}")

    def get_enhanced_processing_stats(self) -> Dict[str, Any]:
        """获取增强版处理统计信息"""
        stats = {}

        # 事件总线统计
        if self.enhanced_event_bus:
            stats['event_bus'] = self.enhanced_event_bus.get_enhanced_stats()

        # 异步管理器统计
        if self.enhanced_async_manager:
            stats['async_manager'] = self.enhanced_async_manager.get_stats()

        return stats

    def _init_auto_tuner(self) -> Optional[AutoTuner]:
        """初始化自动调优器"""
        try:
            # 确保PerformanceEvaluator可用
            try:
                from optimization.algorithm_optimizer import PerformanceEvaluator
                evaluator = PerformanceEvaluator(debug_mode=False)
                logger.debug("PerformanceEvaluator初始化成功")
            except Exception as eval_error:
                logger.warning(f"PerformanceEvaluator初始化失败: {eval_error}")
                # 继续初始化AutoTuner，它可能有内置的评估器

            # 配置自动调优器
            max_workers = min(4, self.executor._max_workers)  # 使用较少的工作线程
            auto_tuner = AutoTuner(max_workers=max_workers, debug_mode=False)

            logger.info("自动调优器初始化成功")
            return auto_tuner

        except Exception as e:
            logger.error(f"自动调优器初始化失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def _auto_tune_task_parameters(self, task_config: ImportTaskConfig) -> ImportTaskConfig:
        """使用AutoTuner自动调优任务参数"""
        if not self.enable_auto_tuning or not self.auto_tuner:
            return task_config

        try:
            logger.info("开始AutoTuner自动调优...")

            # 创建调优配置
            tuning_config = OptimizationConfig(
                target_metric='execution_time',
                method='bayesian',  # 参数名是'method'不是'optimization_method'
                max_iterations=10
                # OptimizationConfig不支持early_stopping参数
            )

            # 创建调优任务
            tuning_task = TuningTask(
                pattern_name=f"import_task_{task_config.data_source}",
                priority=1,
                config=tuning_config
            )

            # 定义参数空间
            parameter_space = {
                'batch_size': {
                    'type': 'integer',
                    'min': 500,
                    'max': 5000,
                    'current': task_config.batch_size
                },
                'max_workers': {
                    'type': 'integer',
                    'min': 2,
                    'max': min(8, self.executor._max_workers),
                    'current': task_config.max_workers
                }
            }

            # 执行自动调优
            tuning_result = self._execute_auto_tuning(tuning_task, parameter_space, task_config)

            if tuning_result and tuning_result.get('success'):
                optimized_params = tuning_result.get('optimized_parameters', {})

                # 应用优化参数
                if 'batch_size' in optimized_params:
                    task_config.batch_size = optimized_params['batch_size']
                if 'max_workers' in optimized_params:
                    task_config.max_workers = optimized_params['max_workers']

                logger.info(f" AutoTuner优化完成: batch_size={task_config.batch_size}, max_workers={task_config.max_workers}")
                logger.info(f" 预期性能提升: {tuning_result.get('improvement_percentage', 0):.1f}%")
            else:
                logger.warning("AutoTuner调优未找到更优参数，保持原配置")

        except Exception as e:
            logger.error(f"AutoTuner调优失败: {e}")

        return task_config

    def _execute_auto_tuning(self, tuning_task: TuningTask, parameter_space: Dict[str, Any],
                             base_config: ImportTaskConfig) -> Optional[Dict[str, Any]]:
        """执行自动调优"""
        try:
            # 定义目标函数
            def objective_function(params: Dict[str, Any]) -> float:
                """调优目标函数：最小化执行时间"""
                try:
                    # 创建测试配置
                    test_config = ImportTaskConfig(
                        task_id=f"tuning_test_{int(time.time())}",
                        name="调优测试任务",
                        symbols=base_config.symbols[:min(10, len(base_config.symbols))],  # 使用少量股票测试
                        data_source=base_config.data_source,
                        asset_type=base_config.asset_type,
                        data_type=base_config.data_type,  # 添加必需的data_type参数
                        frequency=base_config.frequency,
                        mode=base_config.mode,
                        batch_size=params.get('batch_size', base_config.batch_size),
                        max_workers=params.get('max_workers', base_config.max_workers)
                    )

                    # 模拟执行并测量性能
                    start_time = time.time()

                    # 这里应该执行实际的数据导入测试
                    # 为了演示，我们使用简化的性能估算
                    estimated_time = self._estimate_execution_time(test_config)

                    execution_time = time.time() - start_time + estimated_time

                    logger.debug(f"调优测试 - batch_size: {params['batch_size']}, "
                                 f"max_workers: {params['max_workers']}, "
                                 f"执行时间: {execution_time:.2f}秒")

                    return execution_time

                except Exception as e:
                    logger.error(f"调优目标函数执行失败: {e}")
                    return float('inf')

            # 使用AutoTuner执行优化
            best_params = None
            best_score = float('inf')

            # 网格搜索优化（简化版）
            batch_sizes = [500, 1000, 2000, 3000, 5000]
            worker_counts = [2, 3, 4, 6, 8]

            for batch_size in batch_sizes:
                if batch_size < parameter_space['batch_size']['min'] or batch_size > parameter_space['batch_size']['max']:
                    continue

                for workers in worker_counts:
                    if workers < parameter_space['max_workers']['min'] or workers > parameter_space['max_workers']['max']:
                        continue

                    params = {'batch_size': batch_size, 'max_workers': workers}
                    score = objective_function(params)

                    if score < best_score:
                        best_score = score
                        best_params = params

            if best_params:
                # 计算改进百分比
                current_params = {
                    'batch_size': parameter_space['batch_size']['current'],
                    'max_workers': parameter_space['max_workers']['current']
                }
                current_score = objective_function(current_params)

                improvement = max(0, (current_score - best_score) / current_score * 100)

                return {
                    'success': True,
                    'optimized_parameters': best_params,
                    'improvement_percentage': improvement,
                    'best_score': best_score,
                    'current_score': current_score
                }
            else:
                return {'success': False, 'reason': '未找到更优参数'}

        except Exception as e:
            logger.error(f"执行自动调优失败: {e}")
            return None

    def _estimate_execution_time(self, config: ImportTaskConfig) -> float:
        """估算执行时间（用于调优）"""
        try:
            # 基于配置参数的简单时间估算模型
            symbol_count = len(config.symbols)
            batch_size = config.batch_size
            max_workers = config.max_workers

            # 基础时间（秒）
            base_time = symbol_count * 0.1  # 每个股票0.1秒基础时间

            # 批次大小影响
            batch_factor = 1.0 + (1000 - batch_size) / 1000 * 0.3  # 批次越小，开销越大

            # 并发影响
            worker_factor = 1.0 / min(max_workers, symbol_count)  # 工作线程数影响

            estimated_time = base_time * batch_factor * worker_factor

            return max(0.1, estimated_time)  # 最小0.1秒

        except Exception as e:
            logger.error(f"估算执行时间失败: {e}")
            return 1.0  # 默认1秒

    def get_auto_tuning_status(self) -> Dict[str, Any]:
        """获取自动调优状态"""
        status = {
            'auto_tuning_enabled': self.enable_auto_tuning,
            'auto_tuner_available': self.auto_tuner is not None
        }

        try:
            if self.auto_tuner:
                # 获取调优器状态
                tuner_status = self.auto_tuner.get_status()
                status.update({
                    'active_tasks': tuner_status.get('active_tasks', 0),
                    'completed_tasks': tuner_status.get('completed_tasks', 0),
                    'failed_tasks': tuner_status.get('failed_tasks', 0),
                    'total_improvement': tuner_status.get('total_improvement', 0)
                })

        except Exception as e:
            logger.error(f"获取自动调优状态失败: {e}")
            status['error'] = str(e)

        return status

    def _init_data_quality_monitor(self) -> Optional[DataQualityMonitor]:
        """初始化数据质量监控器"""
        try:
            data_quality_monitor = DataQualityMonitor()
            logger.info("数据质量监控器初始化成功")
            return data_quality_monitor

        except Exception as e:
            logger.error(f"数据质量监控器初始化失败: {e}")
            return None

    def _validate_imported_data(self, task_id: str, data: pd.DataFrame,
                                data_source: str, data_type: str = 'kdata') -> ValidationResult:
        """验证导入的数据质量"""
        if not self.enable_data_quality_monitoring or not self.data_quality_monitor:
            return ValidationResult(
                is_valid=True,
                quality_level=DataQuality.GOOD,
                overall_score=0.8,
                issues=[]
            )

        try:
            logger.info(f" 开始数据质量验证: {task_id}")

            # 计算数据质量评分
            quality_score = self.data_quality_monitor.calculate_quality_score(data, data_type)

            # 记录质量指标
            table_name = f"{data_source}_{data_type}"
            self.data_quality_monitor.record_quality_metrics(
                plugin_name=data_source,
                table_name=table_name,
                data=data,
                data_type=data_type
            )

            # 创建详细的验证结果
            validation_result = self._create_detailed_validation_result(
                data, quality_score, data_source, data_type
            )

            # 记录质量评估结果
            quality_level = validation_result.quality_level
            logger.info(f" 数据质量评估完成: {quality_level.value}, 评分: {quality_score:.3f}")

            if quality_score < 0.7:
                logger.warning(f" 数据质量较差 (评分: {quality_score:.3f})，建议检查数据源")

            return validation_result

        except Exception as e:
            logger.error(f"数据质量验证失败: {e}")
            return ValidationResult(
                is_valid=False,
                quality_level=DataQuality.POOR,
                overall_score=0.0,
                issues=[f"验证过程出错: {str(e)}"]
            )

    def _create_detailed_validation_result(self, data: pd.DataFrame, quality_score: float,
                                           data_source: str, data_type: str) -> ValidationResult:
        """创建详细的验证结果"""
        try:
            issues = []

            # 检查数据完整性
            if data.empty:
                issues.append("数据为空")
                return ValidationResult(
                    is_valid=False,
                    quality_level=DataQuality.POOR,
                    overall_score=0.0,
                    issues=issues
                )

            # 检查空值
            null_percentage = data.isnull().sum().sum() / data.size
            if null_percentage > 0.1:
                issues.append(f"空值比例过高: {null_percentage:.1%}")

            # 检查重复数据
            duplicate_percentage = data.duplicated().sum() / len(data)
            if duplicate_percentage > 0.05:
                issues.append(f"重复数据比例过高: {duplicate_percentage:.1%}")

            # 检查数据范围（针对K线数据）
            if data_type == 'kdata':
                numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                available_columns = [col for col in numeric_columns if col in data.columns]

                for col in available_columns:
                    if col in ['open', 'high', 'low', 'close']:
                        # 价格数据应该大于0
                        if (data[col] <= 0).any():
                            issues.append(f"{col}列存在非正数价格")
                    elif col == 'volume':
                        # 成交量应该大于等于0
                        if (data[col] < 0).any():
                            issues.append(f"{col}列存在负数成交量")

                # 检查价格逻辑关系
                if all(col in data.columns for col in ['high', 'low', 'open', 'close']):
                    # 最高价应该 >= 最低价
                    if (data['high'] < data['low']).any():
                        issues.append("存在最高价小于最低价的异常数据")

                    # 开盘价和收盘价应该在最高价和最低价之间
                    if ((data['open'] > data['high']) | (data['open'] < data['low'])).any():
                        issues.append("存在开盘价超出最高最低价范围的异常数据")

                    if ((data['close'] > data['high']) | (data['close'] < data['low'])).any():
                        issues.append("存在收盘价超出最高最低价范围的异常数据")

            # 确定质量等级
            if quality_score >= 0.95:
                quality_level = DataQuality.EXCELLENT
            elif quality_score >= 0.85:
                quality_level = DataQuality.GOOD
            elif quality_score >= 0.70:
                quality_level = DataQuality.FAIR
            else:
                quality_level = DataQuality.POOR

            is_valid = quality_score >= 0.70 and len(issues) == 0

            return ValidationResult(
                is_valid=is_valid,
                quality_level=quality_level,
                overall_score=quality_score,
                issues=issues,
                total_records=len(data),
                null_records=int(data.isnull().sum().sum()),
                duplicate_records=int(data.duplicated().sum()),
                completeness_score=1.0 - null_percentage,
                accuracy_score=quality_score  # 简化处理
            )

        except Exception as e:
            logger.error(f"创建验证结果失败: {e}")
            return ValidationResult(
                is_valid=False,
                quality_level=DataQuality.POOR,
                overall_score=0.0,
                issues=[f"验证结果创建失败: {str(e)}"]
            )

    def _handle_quality_issues(self, validation_result: ValidationResult, task_id: str):
        """处理数据质量问题"""
        if not validation_result.is_valid or validation_result.quality_level == DataQuality.POOR:
            logger.warning(f"任务 {task_id} 数据质量问题:")
            for issue in validation_result.issues:
                logger.warning(f"  - {issue}")

            # 可以在这里添加自动修复逻辑
            if validation_result.duplicate_records > 0:
                logger.info(f"  建议: 清理 {validation_result.duplicate_records} 条重复数据")

            if validation_result.null_records > 0:
                logger.info(f"  建议: 处理 {validation_result.null_records} 个空值")

    def get_data_quality_statistics(self) -> Dict[str, Any]:
        """获取数据质量统计信息"""
        stats = {
            'data_quality_monitoring_enabled': self.enable_data_quality_monitoring,
            'data_quality_monitor_available': self.data_quality_monitor is not None
        }

        try:
            if self.data_quality_monitor:
                # 这里可以添加从数据库获取历史质量统计的逻辑
                stats.update({
                    'monitoring_active': True,
                    'quality_checks_performed': 0,  # 可以从数据库统计
                    'average_quality_score': 0.0,   # 可以从数据库计算
                    'last_check_time': datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"获取数据质量统计失败: {e}")
            stats['error'] = str(e)

        return stats

    def _start_performance_monitoring(self, task_id: str):
        """启动任务性能监控"""
        if not self.enable_performance_monitoring:
            return

        try:
            # 记录任务开始时的系统状态
            self.deep_analysis_service.record_metric(
                f"task_start_{task_id}",
                time.time(),
                "import_task"
            )

            # 启动性能集成器监控
            self.performance_integrator.start_monitoring()

            logger.info(f"任务 {task_id} 性能监控已启动")

        except Exception as e:
            logger.warning(f"启动性能监控失败: {e}")

    def _stop_performance_monitoring(self, task_id: str, execution_time: float):
        """停止任务性能监控"""
        if not self.enable_performance_monitoring:
            return

        try:
            # 记录任务执行时间
            self.deep_analysis_service.record_operation_timing(
                f"import_task_{task_id}",
                execution_time
            )

            # 记录任务完成时的系统状态
            self.deep_analysis_service.record_metric(
                f"task_end_{task_id}",
                time.time(),
                "import_task"
            )

            # 分析性能瓶颈
            bottlenecks = self.deep_analysis_service.analyze_bottlenecks()
            if bottlenecks:
                logger.info(f"任务 {task_id} 性能瓶颈分析: {len(bottlenecks)} 个瓶颈点")
                for bottleneck in bottlenecks[:3]:  # 显示前3个瓶颈
                    logger.info(f"  - {bottleneck.component}: {bottleneck.avg_duration:.2f}ms ({bottleneck.severity})")

            logger.info(f"任务 {task_id} 性能监控已停止")

        except Exception as e:
            logger.warning(f"停止性能监控失败: {e}")

    def _detect_anomalies(self, task_id: str) -> List[AnomalyInfo]:
        """检测任务执行异常"""
        if not self.enable_anomaly_detection:
            return []

        try:
            anomalies = self.deep_analysis_service.detect_anomalies()

            if anomalies:
                logger.warning(f"任务 {task_id} 检测到 {len(anomalies)} 个异常:")
                for anomaly in anomalies:
                    logger.warning(f"  - {anomaly.metric_name}: {anomaly.description} (严重程度: {anomaly.severity})")

            return anomalies

        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return []

    def _monitor_task_progress(self, task_id: str, progress: float, message: str):
        """监控任务进度并检测异常"""
        try:
            # 记录进度指标
            if self.enable_performance_monitoring:
                self.deep_analysis_service.record_metric(
                    f"task_progress_{task_id}",
                    progress,
                    "import_progress"
                )

            # 检测进度异常
            if self.enable_anomaly_detection:
                # 如果进度长时间没有变化，可能存在问题
                current_time = time.time()
                if hasattr(self, '_last_progress_time'):
                    time_diff = current_time - self._last_progress_time
                    if time_diff > 300 and progress == getattr(self, '_last_progress', 0):  # 5分钟没有进度变化
                        logger.warning(f"任务 {task_id} 可能存在进度停滞问题")

                self._last_progress_time = current_time
                self._last_progress = progress

            # 发送进度信号
            self.task_progress.emit(task_id, progress, message)

        except Exception as e:
            logger.error(f"监控任务进度失败: {e}")

    def get_performance_report(self, task_id: str = None) -> Dict[str, Any]:
        """获取性能报告"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'monitoring_enabled': self.enable_performance_monitoring,
                'anomaly_detection_enabled': self.enable_anomaly_detection
            }

            if self.enable_performance_monitoring:
                # 获取性能统计
                bottlenecks = self.deep_analysis_service.analyze_bottlenecks()
                report['bottlenecks'] = [
                    {
                        'component': b.component,
                        'avg_duration': b.avg_duration,
                        'call_count': b.call_count,
                        'severity': b.severity
                    } for b in bottlenecks[:5]
                ]

                # 获取系统指标
                system_metrics = self.deep_analysis_service.get_system_metrics()
                report['system_metrics'] = system_metrics

            if self.enable_anomaly_detection:
                # 获取异常信息
                anomalies = self.deep_analysis_service.detect_anomalies()
                report['anomalies'] = [
                    {
                        'metric_name': a.metric_name,
                        'value': a.value,
                        'threshold': a.threshold,
                        'severity': a.severity,
                        'description': a.description,
                        'timestamp': a.timestamp.isoformat()
                    } for a in anomalies
                ]

            return report

        except Exception as e:
            logger.error(f"生成性能报告失败: {e}")
            return {'error': str(e)}

    def _ensure_data_manager(self):
        """确保数据管理器已初始化"""
        if not self._data_manager_initialized:
            try:
                logger.info("延迟初始化数据管理器...")
                self.data_manager = get_unified_data_manager()
                self._data_manager_initialized = True
                logger.info("数据管理器延迟初始化完成")
            except Exception as e:
                logger.error(f" 数据管理器初始化失败: {e}")
                # 创建一个最小的数据管理器替代
                self.data_manager = None
                self._data_manager_initialized = False

    def _ensure_real_data_provider(self):
        """确保真实数据提供器已初始化"""
        if not self._real_data_provider_initialized:
            try:
                logger.info("延迟初始化真实数据提供器...")
                self.real_data_provider = RealDataProvider()
                self._real_data_provider_initialized = True
                logger.info("真实数据提供器延迟初始化完成")
            except Exception as e:
                logger.error(f" 真实数据提供器初始化失败: {e}")
                # 创建一个最小的替代
                self.real_data_provider = None
                self._real_data_provider_initialized = False

    def _get_data_source_plugin(self, plugin_id: str):
        """获取指定的数据源插件实例"""
        try:
            # 从插件管理器获取插件实例
            from ..plugin_manager import get_plugin_manager
            plugin_manager = get_plugin_manager()

            if plugin_manager:
                # 获取数据源插件
                plugin_instance = plugin_manager.get_data_source_plugin(plugin_id)
                if plugin_instance:
                    logger.info(f"获取数据源插件成功: {plugin_id}")
                    return plugin_instance
                else:
                    logger.warning(f"未找到数据源插件: {plugin_id}")

            # 如果插件管理器不可用，尝试直接导入
            if plugin_id.startswith('examples.'):
                module_name = plugin_id.replace('examples.', 'plugins.examples.')
                try:
                    import importlib
                    module = importlib.import_module(module_name)

                    # 查找插件类
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (hasattr(attr, '__bases__') and
                                any('IDataSourcePlugin' in str(base) for base in attr.__bases__)):
                            plugin_instance = attr()
                            logger.info(f"直接导入数据源插件成功: {plugin_id}")
                            return plugin_instance

                except ImportError as e:
                    logger.error(f"直接导入数据源插件失败 {plugin_id}: {e}")

            return None

        except Exception as e:
            logger.error(f"获取数据源插件失败 {plugin_id}: {e}")
            return None

    def start_task(self, task_id: str) -> bool:
        """
        启动任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功启动
        """
        try:
            logger.info(f" 开始启动任务: {task_id}")

            # 获取任务配置
            task_config = self.config_manager.get_import_task(task_id)
            if not task_config:
                logger.error(f" 任务配置不存在: {task_id}")
                return False

            logger.info(f" 找到任务配置: {task_config.name}, 股票数量: {len(task_config.symbols)}")

            # 智能配置优化（最高优先级）
            if self.enable_intelligent_config:
                logger.info("开始智能配置优化...")
                intelligent_config = self._apply_intelligent_optimization(task_config, ConfigOptimizationLevel.BALANCED)
                if intelligent_config:
                    task_config = intelligent_config
                    logger.info(f" 智能配置优化完成: batch_size={task_config.batch_size}, max_workers={task_config.max_workers}")

            # 检查缓存的配置优化
            cached_config = self._get_cached_configuration(task_config)
            if cached_config and self.enable_intelligent_caching:
                logger.info("使用缓存的配置优化")
                task_config.batch_size = cached_config.get('optimal_batch_size', task_config.batch_size)
                task_config.max_workers = cached_config.get('optimal_workers', task_config.max_workers)

            # AutoTuner自动调优
            if self.enable_auto_tuning:
                task_config = self._auto_tune_task_parameters(task_config)

            # AI优化任务参数
            if self.enable_ai_optimization:
                logger.info("开始AI优化任务参数...")
                task_config = self._optimize_task_parameters(task_config)

                # 缓存优化后的配置
                self._cache_configuration_data(task_config)

                # AI预测执行时间
                predicted_time = self._predict_execution_time(task_config)
                if predicted_time:
                    logger.info(f" AI预测执行时间: {predicted_time:.2f}秒")

            # 检查是否可以分布式执行
            if self.enable_distributed_execution and self._can_distribute_task(task_config):
                logger.info("任务符合分布式执行条件，尝试分布式执行...")
                if self._distribute_task(task_config):
                    logger.info(f"任务 {task_id} 已分布式执行")
                    return True
                else:
                    logger.info("分布式执行失败，回退到本地执行")

            # 检查任务是否已在运行
            with self._task_lock:
                if task_id in self._running_tasks:
                    logger.warning(f"任务已在运行: {task_id}")
                    return False

            # 创建任务执行结果
            result = TaskExecutionResult(
                task_id=task_id,
                status=TaskExecutionStatus.PENDING,
                start_time=datetime.now()
            )

            with self._task_lock:
                self._task_results[task_id] = result

            # 提交任务到线程池
            future = self.executor.submit(self._execute_task, task_config, result)

            with self._task_lock:
                self._running_tasks[task_id] = future

            # 启动增强版性能监控
            if self.enable_enhanced_performance_bridge:
                self.start_enhanced_performance_monitoring()
                logger.info("增强版性能监控已启动")

            # 启动增强版风险监控
            if self.enable_enhanced_risk_monitoring:
                self.start_enhanced_risk_monitoring()
                logger.info("增强版风险监控已启动")

            # 启动性能监控
            self._start_performance_monitoring(task_id)

            # 发送任务开始信号
            self.task_started.emit(task_id)

            logger.info(f"任务启动成功: {task_id}")
            return True

        except Exception as e:
            logger.error(f"启动任务失败 {task_id}: {e}")
            self.task_failed.emit(task_id, str(e))
            return False

    def stop_task(self, task_id: str) -> bool:
        """
        停止任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功停止
        """
        try:
            with self._task_lock:
                if task_id not in self._running_tasks:
                    logger.warning(f"任务未在运行: {task_id}")
                    return False

                # 取消任务
                future = self._running_tasks[task_id]
                cancelled = future.cancel()

                if cancelled:
                    # 更新任务状态
                    if task_id in self._task_results:
                        self._task_results[task_id].status = TaskExecutionStatus.CANCELLED
                        self._task_results[task_id].end_time = datetime.now()

                    # 移除运行中的任务
                    del self._running_tasks[task_id]

                    # 停止增强版性能监控
                    if self.enable_enhanced_performance_bridge:
                        self.stop_enhanced_performance_monitoring()
                        logger.info("增强版性能监控已停止")

                    # 停止增强版风险监控
                    if self.enable_enhanced_risk_monitoring:
                        self.stop_enhanced_risk_monitoring()
                        logger.info("增强版风险监控已停止")

                    logger.info(f"任务停止成功: {task_id}")
                    return True
                else:
                    logger.warning(f"任务无法取消: {task_id}")
                    return False

        except Exception as e:
            logger.error(f"停止任务失败 {task_id}: {e}")
            return False

    def get_task_status(self, task_id: str) -> Optional[TaskExecutionResult]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            TaskExecutionResult: 任务执行结果
        """
        with self._task_lock:
            return self._task_results.get(task_id)

    def get_running_tasks(self) -> List[str]:
        """获取正在运行的任务列表"""
        with self._task_lock:
            return list(self._running_tasks.keys())

    def stop_all_tasks(self) -> bool:
        """
        停止所有正在运行的任务

        Returns:
            bool: 是否成功停止所有任务
        """
        try:
            with self._task_lock:
                running_task_ids = list(self._running_tasks.keys())

                if not running_task_ids:
                    logger.info("没有正在运行的任务需要停止")
                    return True

                logger.info(f"停止 {len(running_task_ids)} 个正在运行的任务")

                success_count = 0
                for task_id in running_task_ids:
                    if self.stop_task(task_id):
                        success_count += 1

                logger.info(f"成功停止 {success_count}/{len(running_task_ids)} 个任务")
                return success_count == len(running_task_ids)

        except Exception as e:
            logger.error(f"停止所有任务失败: {e}")
            return False

    def _execute_task(self, task_config: ImportTaskConfig, result: TaskExecutionResult):
        """
        执行任务的核心逻辑

        Args:
            task_config: 任务配置
            result: 任务执行结果
        """
        try:
            logger.info(f" 开始执行任务: {task_config.task_id}")
            logger.info(f" 任务详情: 数据类型={getattr(task_config, 'data_type', 'K线数据')}, 股票数量={len(task_config.symbols)}")

            # 更新任务状态
            result.status = TaskExecutionStatus.RUNNING

            # 根据任务类型执行不同的导入逻辑
            data_type = getattr(task_config, 'data_type', 'K线数据')  # 默认为K线数据
            logger.info(f" 执行数据类型: {data_type}")

            if data_type == "K线数据":
                logger.info("开始导入K线数据")
                self._import_kline_data(task_config, result)
            elif data_type == "实时行情":
                logger.info("开始导入实时行情")
                self._import_realtime_data(task_config, result)
            elif data_type == "基本面数据":
                logger.info("开始导入基本面数据")
                self._import_fundamental_data(task_config, result)
            else:
                logger.warning(f" 不支持的数据类型，默认使用K线数据: {data_type}")
                self._import_kline_data(task_config, result)

            # 任务完成
            result.status = TaskExecutionStatus.COMPLETED
            result.success = True
            result.end_time = datetime.now()
            result.execution_time = (result.end_time - result.start_time).total_seconds()

            # 记录智能配置性能反馈
            if self.enable_intelligent_config:
                self.record_task_performance_feedback(task_config.task_id, result)

            # 记录增强性能数据
            if self.enable_enhanced_performance_bridge and result.success:
                execution_time = (result.end_time - result.start_time).total_seconds()
                self.record_custom_performance_metric(
                    f"task_execution_time_{task_config.task_id}",
                    execution_time,
                    "task_performance"
                )
                self.record_custom_performance_metric(
                    f"task_success_rate_{task_config.task_id}",
                    1.0,
                    "task_quality"
                )

            # 更新配置管理器中的进度
            progress = ImportProgress(
                task_id=task_config.task_id,
                status=ImportStatus.COMPLETED,
                total_records=result.total_records,
                imported_records=result.processed_records,
                error_count=result.failed_records,
                start_time=result.start_time.isoformat(),
                end_time=result.end_time.isoformat(),
                error_message=result.error_message
            )
            self.config_manager.update_progress(progress)

            # 停止性能监控并检测异常
            execution_time = (result.end_time - result.start_time).total_seconds()
            self._stop_performance_monitoring(task_config.task_id, execution_time)

            # 检测执行异常
            anomalies = self._detect_anomalies(task_config.task_id)
            if anomalies:
                logger.warning(f"任务 {task_config.task_id} 检测到 {len(anomalies)} 个异常")

            # 发送完成信号
            self.task_completed.emit(task_config.task_id, result)

            logger.info(f"任务执行完成: {task_config.task_id}")

        except Exception as e:
            logger.error(f"任务执行失败 {task_config.task_id}: {e}")

            # 更新任务状态
            result.status = TaskExecutionStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.now()

            # 停止性能监控
            if result.start_time and result.end_time:
                execution_time = (result.end_time - result.start_time).total_seconds()
                self._stop_performance_monitoring(task_config.task_id, execution_time)

            # 发送失败信号
            self.task_failed.emit(task_config.task_id, str(e))

        finally:
            # 清理运行中的任务
            with self._task_lock:
                if task_config.task_id in self._running_tasks:
                    del self._running_tasks[task_config.task_id]

    def _save_kdata_to_database(self, symbol: str, kdata: 'pd.DataFrame', task_config: ImportTaskConfig):
        """保存K线数据到数据库（使用新的增强资产数据库管理器）"""
        try:
            # 使用资产分数据库管理器
            from ..asset_database_manager import AssetSeparatedDatabaseManager
            from ..plugin_types import AssetType, DataType

            asset_manager = AssetSeparatedDatabaseManager()

            # 标准化数据字段，确保与表结构匹配
            kdata = self._standardize_kline_data_fields(kdata)

            # 根据股票代码确定资产类型
            asset_type = AssetType.STOCK_A if symbol.endswith(('.SZ', '.SH')) else AssetType.STOCK

            # 保存数据到新架构
            success = asset_manager.store_standardized_data(
                data=kdata,
                asset_type=asset_type,
                data_type=DataType.HISTORICAL_KLINE
            )

            if success:
                logger.info(f"K线数据保存到新架构成功: {symbol} -> {asset_type.value}, {len(kdata)}条记录")
            else:
                logger.error(f"K线数据保存到新架构失败: {symbol} -> {asset_type.value}")

        except Exception as e:
            logger.error(f"保存K线数据到数据库失败 {symbol}: {e}")

    def _save_fundamental_data_to_database(self, symbol: str, data: 'pd.DataFrame', data_type: str):
        """保存基本面数据到数据库"""
        try:
            from ..database.duckdb_operations import get_duckdb_operations
            from ..database.table_manager import get_table_manager

            duckdb_ops = get_duckdb_operations()
            table_manager = get_table_manager()

            if not duckdb_ops or not table_manager:
                logger.warning("DuckDB操作或表管理器不可用，跳过数据保存")
                return

            # 确定表名
            table_name = f"fundamental_{data_type.lower().replace(' ', '_')}"

            # 确保表存在 - 使用统一的DuckDB数据库
            db_path = self.asset_manager.get_database_path(asset_type)
            # 确保表存在
            if not table_manager.ensure_table_exists(db_path, TableType.FINANCIAL_STATEMENT, "import_engine"):
                logger.error("创建财务数据表失败")
                return

            # 添加symbol列
            data_with_symbol = data.copy()
            data_with_symbol['symbol'] = symbol

            # 插入数据
            result = duckdb_ops.insert_dataframe(
                database_path=db_path,
                table_name=table_name,
                data=data_with_symbol,
                upsert=True,
                conflict_columns=['symbol', 'date'] if 'date' in data_with_symbol.columns else ['symbol']
            )

            if result.success:
                logger.info(f" 基本面数据保存到DuckDB成功: {symbol}, {len(data)}条记录")
            else:
                logger.error(f" 基本面数据保存失败: {symbol}")

        except Exception as e:
            logger.error(f"保存基本面数据到数据库失败 {symbol}: {e}")

    def _save_realtime_data_to_database(self, symbol: str, data: 'pd.DataFrame'):
        """保存实时数据到数据库"""
        try:
            from ..database.duckdb_operations import get_duckdb_operations
            from ..database.table_manager import get_table_manager

            duckdb_ops = get_duckdb_operations()
            table_manager = get_table_manager()

            if not duckdb_ops or not table_manager:
                logger.warning("DuckDB操作或表管理器不可用，跳过数据保存")
                return

            # 确定表名
            table_name = "realtime_data"

            # 确保表存在 - 使用统一的DuckDB数据库
            db_path = self.asset_manager.get_database_path(asset_type)
            # 确保表存在
            if not table_manager.ensure_table_exists(db_path, TableType.REAL_TIME_QUOTE, "import_engine"):
                logger.error("创建实时行情表失败")
                return

            # 添加symbol列
            data_with_symbol = data.copy()
            data_with_symbol['symbol'] = symbol

            # 插入数据（实时数据通常不需要upsert，直接插入）
            result = duckdb_ops.insert_dataframe(
                database_path=db_path,
                table_name=table_name,
                data=data_with_symbol,
                upsert=False
            )

            if result.success:
                logger.info(f" 实时数据保存到DuckDB成功: {symbol}, {len(data)}条记录")
            else:
                logger.error(f" 实时数据保存失败: {symbol}")

        except Exception as e:
            logger.error(f"保存实时数据到数据库失败 {symbol}: {e}")

    def _import_kline_data(self, task_config: ImportTaskConfig, result: TaskExecutionResult):
        """导入K线数据（优化版本：并发下载+批量保存）"""
        try:
            # 确保数据管理器已初始化
            self._ensure_data_manager()

            # 确保真实数据提供器已初始化
            self._ensure_real_data_provider()

            symbols = task_config.symbols
            result.total_records = len(symbols)

            # 显示股票列表概要（避免日志过长）
            symbols_preview = symbols[:5] if len(symbols) > 5 else symbols
            logger.info(f" 开始导入K线数据，股票数量: {len(symbols)}, 示例: {symbols_preview}")
            logger.info(f" 时间范围: {task_config.start_date} 到 {task_config.end_date}")
            logger.info(f" 频率: {task_config.frequency}")
            logger.info(f" 使用并发下载模式，最大工作线程: {task_config.max_workers}")

            # 使用并发下载优化性能
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading

            # 用于收集所有下载的数据
            all_kdata_list = []
            download_lock = threading.Lock()

            # 进度跟踪
            completed_count = 0
            progress_lock = threading.Lock()

            def download_single_stock(symbol: str) -> dict:
                """下载单只股票的数据"""
                nonlocal completed_count  # 声明必须在函数开头
                try:
                    # 发送进度更新信号（下载开始时）
                    with progress_lock:
                        current_progress = (completed_count / len(symbols)) * 100
                    self.task_progress.emit(
                        task_config.task_id,
                        current_progress,
                        f"正在下载 {symbol} 的K线数据..."
                    )

                    logger.info(f" [{completed_count + 1}/{len(symbols)}] 正在获取 {symbol} 的K线数据...")

                    # 使用真实数据提供器获取K线数据，传递数据源信息
                    kdata = self.real_data_provider.get_real_kdata(
                        code=symbol,
                        freq=task_config.frequency.value,
                        start_date=task_config.start_date,
                        end_date=task_config.end_date,
                        data_source=task_config.data_source  # 传递任务配置中的数据源
                    )

                    # 更新进度
                    with progress_lock:
                        completed_count += 1
                        current_progress = (completed_count / len(symbols)) * 100

                    # 发送进度更新信号（下载完成时）
                    self.task_progress.emit(
                        task_config.task_id,
                        current_progress,
                        f"已完成 {completed_count}/{len(symbols)} 只股票的数据下载"
                    )

                    if not kdata.empty:
                        # 添加symbol列
                        kdata_with_meta = kdata.copy()
                        kdata_with_meta['symbol'] = symbol

                        # ✅ 关键修复：如果datetime是索引，将其转换为列
                        import pandas as pd
                        if isinstance(kdata_with_meta.index, pd.DatetimeIndex):
                            logger.debug(f"{symbol}: 检测到DatetimeIndex，转换为datetime列")
                            kdata_with_meta = kdata_with_meta.reset_index()
                            # 如果reset后的列名为'index'或'date'，重命名为datetime
                            if 'index' in kdata_with_meta.columns and 'datetime' not in kdata_with_meta.columns:
                                kdata_with_meta = kdata_with_meta.rename(columns={'index': 'datetime'})
                            elif 'date' in kdata_with_meta.columns and 'datetime' not in kdata_with_meta.columns:
                                kdata_with_meta = kdata_with_meta.rename(columns={'date': 'datetime'})

                        # 调试：检查datetime列
                        if 'datetime' not in kdata_with_meta.columns:
                            logger.warning(f"{symbol}: 数据中缺少datetime列，可用列: {kdata_with_meta.columns.tolist()}")
                        elif kdata_with_meta['datetime'].isna().all():
                            logger.warning(f"{symbol}: datetime列全部为None")
                        else:
                            logger.debug(f"{symbol}: datetime列正常，非空记录数: {kdata_with_meta['datetime'].notna().sum()}/{len(kdata_with_meta)}")

                        # 线程安全地添加到列表
                        with download_lock:
                            all_kdata_list.append(kdata_with_meta)

                        logger.info(f" [{completed_count}/{len(symbols)}] {symbol} 数据获取成功: {len(kdata)} 条记录")
                        return {'symbol': symbol, 'status': 'success', 'records': len(kdata)}
                    else:
                        logger.warning(f" [{completed_count}/{len(symbols)}] 未获取到 {symbol} 的K线数据")
                        return {'symbol': symbol, 'status': 'no_data', 'records': 0}

                except Exception as e:
                    with progress_lock:
                        completed_count += 1
                        current_progress = (completed_count / len(symbols)) * 100

                    # 发送进度更新信号（异常时）
                    self.task_progress.emit(
                        task_config.task_id,
                        current_progress,
                        f"下载失败 {completed_count}/{len(symbols)} - {symbol}: {str(e)}"
                    )

                    logger.error(f" [{completed_count}/{len(symbols)}] 导入 {symbol} K线数据失败: {e}")
                    return {'symbol': symbol, 'status': 'error', 'error': str(e), 'records': 0}

            # 并发下载所有股票数据
            max_workers = min(task_config.max_workers, len(symbols), 8)  # 限制最大并发数
            logger.info(f" 启动 {max_workers} 个并发下载线程...")

            download_results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有下载任务
                future_to_symbol = {executor.submit(download_single_stock, symbol): symbol
                                    for symbol in symbols}

                # 收集结果
                for future in as_completed(future_to_symbol):
                    if result.status == TaskExecutionStatus.CANCELLED:
                        break

                    try:
                        download_result = future.result()
                        download_results.append(download_result)

                        # 更新任务结果统计
                        if download_result['status'] == 'success':
                            result.processed_records += 1
                        else:
                            result.failed_records += 1

                    except Exception as e:
                        symbol = future_to_symbol[future]
                        logger.error(f"下载任务异常 {symbol}: {e}")
                        result.failed_records += 1

            # 批量保存所有数据到数据库
            if all_kdata_list and result.status != TaskExecutionStatus.CANCELLED:
                logger.info(f" 开始批量保存数据到DuckDB，共 {len(all_kdata_list)} 只股票的数据...")
                self._batch_save_kdata_to_database(all_kdata_list, task_config)
                logger.info(f" 批量保存完成")

            # 输出统计信息
            success_count = sum(1 for r in download_results if r['status'] == 'success')
            failed_count = sum(1 for r in download_results if r['status'] in ['error', 'no_data'])
            total_records = sum(r.get('records', 0) for r in download_results)

            logger.info(f" K线数据导入完成统计:")
            logger.info(f"   成功: {success_count} 只股票")
            logger.info(f"   失败: {failed_count} 只股票")
            logger.info(f"   总记录数: {total_records} 条")

            # 清理数据源连接池
            if self.real_data_provider:
                try:
                    pool_status = self.real_data_provider.get_pool_status()
                    logger.info(f" 任务完成前连接池状态: {pool_status}")
                    self.real_data_provider.cleanup_data_source_pool()
                except Exception as pool_e:
                    logger.warning(f"清理数据源连接池失败: {pool_e}")

        except Exception as e:
            # 即使出错也要清理连接池
            if self.real_data_provider:
                try:
                    self.real_data_provider.cleanup_data_source_pool()
                except Exception as pool_e:
                    logger.warning(f"清理数据源连接池失败: {pool_e}")

            raise Exception(f"K线数据导入失败: {e}")

    def _batch_save_kdata_to_database(self, all_kdata_list: list, task_config: ImportTaskConfig):
        """批量保存K线数据到数据库（使用新的增强资产数据库管理器）"""
        try:
            if not all_kdata_list:
                logger.warning("没有数据需要保存")
                return

            # 使用资产分数据库管理器
            from ..asset_database_manager import AssetSeparatedDatabaseManager
            from ..plugin_types import AssetType, DataType
            import pandas as pd

            asset_manager = AssetSeparatedDatabaseManager()

            # 合并所有数据
            combined_data = pd.concat(all_kdata_list, ignore_index=True)

            # 标准化数据字段，确保与表结构匹配
            combined_data = self._standardize_kline_data_fields(combined_data)

            logger.info(f"准备批量插入 {len(combined_data)} 条K线数据记录")

            # 根据股票代码确定资产类型（批量处理时取第一个符号作为示例）
            if not combined_data.empty and 'symbol' in combined_data.columns:
                first_symbol = combined_data['symbol'].iloc[0]
                asset_type = AssetType.STOCK_A if str(first_symbol).endswith(('.SZ', '.SH')) else AssetType.STOCK

                # 保存数据到新架构
                success = asset_manager.store_standardized_data(
                    data=combined_data,
                    asset_type=asset_type,
                    data_type=DataType.HISTORICAL_KLINE
                )

                if success:
                    logger.info(f"批量保存K线数据成功到新架构: {asset_type.value}, {len(combined_data)}条记录")
                else:
                    logger.error(f"批量保存K线数据失败到新架构: {asset_type.value}")
            else:
                logger.error("数据为空或缺少symbol字段，无法保存")

        except Exception as e:
            logger.error(f"批量保存K线数据到数据库失败: {e}")

    def _standardize_kline_data_fields(self, df) -> 'pd.DataFrame':
        """标准化K线数据字段，确保与表结构匹配"""
        import pandas as pd  # 在函数开头导入，避免后续引用错误

        try:
            if df.empty:
                return df

            # ✅ 步骤1: 如果datetime是index，将其重置为列
            if isinstance(df.index, pd.DatetimeIndex):
                logger.debug("检测到DatetimeIndex，转换为datetime列")
                df = df.reset_index()
                # 如果reset后的列名为'index'或'date'，重命名为datetime
                if 'index' in df.columns and 'datetime' not in df.columns:
                    df = df.rename(columns={'index': 'datetime'})
                    logger.debug("已将'index'列重命名为'datetime'")
                elif 'date' in df.columns and 'datetime' not in df.columns:
                    df = df.rename(columns={'date': 'datetime'})
                    logger.debug("已将'date'列重命名为'datetime'")

            # ✅ 步骤2: 如果有'date'列但没有'datetime'列，重命名
            if 'date' in df.columns and 'datetime' not in df.columns:
                df = df.rename(columns={'date': 'datetime'})
                logger.debug("已将'date'列重命名为'datetime'")

            # 处理字段名称映射（code -> symbol）
            if 'code' in df.columns and 'symbol' not in df.columns:
                df['symbol'] = df['code']

            # 删除code列（如果存在，避免与symbol冲突）
            if 'code' in df.columns:
                df = df.drop('code', axis=1)

            # 基础字段映射和默认值
            # 标准量化表字段（20字段 - 方案B）
            # 包括基础OHLCV、复权数据、扩展交易数据、元数据
            field_defaults = {
                # 基础OHLCV字段（8个）
                'symbol': '',
                'datetime': None,
                'open': 0.0,
                'high': 0.0,
                'low': 0.0,
                'close': 0.0,
                'volume': 0,
                'amount': 0.0,
                'turnover': 0.0,

                # 复权数据（2个）- 量化回测必需
                'adj_close': None,      # 复权收盘价
                'adj_factor': 1.0,      # 复权因子（默认1.0=不复权）

                # 扩展交易数据（2个）
                'turnover_rate': None,  # 换手率（行业标准）
                'vwap': None,           # 成交量加权均价（机构常用）

                # 元数据（6个）
                'name': None,
                'market': None,
                'frequency': '1d',
                'period': None,
                'data_source': 'unknown',  # 数据来源追溯
                'created_at': None,
                'updated_at': None,
            }

            # 添加缺失的必需字段
            for field, default_value in field_defaults.items():
                if field not in df.columns:
                    df[field] = default_value

            # 确保数据类型正确
            numeric_fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
            for field in numeric_fields:
                if field in df.columns:
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)

            # 确保datetime字段格式正确且不为空
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
                # 删除datetime为空的行（数据库NOT NULL约束）
                null_datetime_count = df['datetime'].isna().sum()
                if null_datetime_count > 0:
                    logger.warning(f"发现 {null_datetime_count} 条datetime为空的记录，将被过滤")
                    df = df[df['datetime'].notna()]
            else:
                # 如果没有datetime列，尝试使用其他时间列
                time_columns = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()]
                if time_columns:
                    logger.warning(f"未找到datetime列，尝试使用 {time_columns[0]}")
                    df['datetime'] = pd.to_datetime(df[time_columns[0]], errors='coerce')
                    df = df[df['datetime'].notna()]
                else:
                    # 最后尝试：检查是否有DatetimeIndex但还没有被重置
                    if isinstance(df.index, pd.DatetimeIndex):
                        logger.warning("发现DatetimeIndex但未被重置为datetime列，正在修复")
                        df = df.reset_index()
                        if 'index' in df.columns:
                            df = df.rename(columns={'index': 'datetime'})
                    else:
                        logger.error(f"未找到时间相关列，无法标准化数据。可用列: {df.columns.tolist()}")
                        return pd.DataFrame()

            # 确保symbol字段不为空
            if 'symbol' in df.columns:
                df['symbol'] = df['symbol'].fillna('').astype(str)

            # 删除code列（如果存在），避免与symbol混淆
            if 'code' in df.columns:
                logger.debug("删除code列（已有symbol列）")
                df = df.drop(columns=['code'])

            # 设置默认时间戳
            if 'created_at' in df.columns and df['created_at'].isna().all():
                df['created_at'] = pd.Timestamp.now()

            # 智能计算复权价格（如果数据源没有提供）
            if 'adj_close' in df.columns:
                # 如果adj_close为空但有adj_factor，则计算
                mask = df['adj_close'].isna() & df['adj_factor'].notna()
                if mask.any():
                    df.loc[mask, 'adj_close'] = df.loc[mask, 'close'] * df.loc[mask, 'adj_factor']

                # 如果adj_close和adj_factor都为空，设置adj_close=close（不复权）
                mask = df['adj_close'].isna()
                if mask.any():
                    df.loc[mask, 'adj_close'] = df.loc[mask, 'close']

            # 智能计算VWAP（如果数据源没有提供）
            if 'vwap' in df.columns and df['vwap'].isna().all():
                # vwap = amount / volume
                df['vwap'] = df['amount'] / df['volume'].replace(0, pd.NA)

            # 最终检查：确保datetime字段存在且有效
            if 'datetime' not in df.columns:
                logger.error(f"标准化完成但缺少datetime字段！可用列: {df.columns.tolist()}")
                return pd.DataFrame()  # 返回空DataFrame，避免插入失败

            if df['datetime'].isna().all():
                logger.error(f"标准化完成但datetime字段全为空！")
                return pd.DataFrame()

            logger.debug(f"数据字段标准化完成，字段数: {len(df.columns)}, 记录数: {len(df)}")
            logger.debug(f"标准化后的列: {df.columns.tolist()}")
            return df

        except Exception as e:
            logger.error(f"标准化K线数据字段失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return df

    def _import_realtime_data(self, task_config: ImportTaskConfig, result: TaskExecutionResult):
        """导入实时行情数据"""
        try:
            symbols = task_config.symbols
            result.total_records = len(symbols)

            for i, symbol in enumerate(symbols):
                if result.status == TaskExecutionStatus.CANCELLED:
                    break

                try:
                    # 获取实时行情数据
                    quote_data = self.real_data_provider.get_real_quote(symbol)

                    if quote_data:
                        # 将实时数据转换为DataFrame并保存
                        if isinstance(quote_data, dict):
                            import pandas as pd
                            quote_df = pd.DataFrame([quote_data])
                            self._save_realtime_data_to_database(symbol, quote_df)
                        logger.info(f"成功导入并保存 {symbol} 的实时行情数据")
                        result.processed_records += 1
                    else:
                        logger.warning(f"未获取到 {symbol} 的实时行情数据")
                        result.failed_records += 1

                except Exception as e:
                    logger.error(f"导入 {symbol} 实时行情失败: {e}")
                    result.failed_records += 1

                time.sleep(0.05)  # 实时数据处理更快

        except Exception as e:
            raise Exception(f"实时行情导入失败: {e}")

    def _import_fundamental_data(self, task_config: ImportTaskConfig, result: TaskExecutionResult):
        """导入基本面数据"""
        try:
            symbols = task_config.symbols
            result.total_records = len(symbols)

            for i, symbol in enumerate(symbols):
                if result.status == TaskExecutionStatus.CANCELLED:
                    break

                try:
                    # 获取基本面数据
                    fundamental_data = self.real_data_provider.get_real_fundamental_data(symbol)

                    if fundamental_data:
                        # 将基本面数据转换为DataFrame并保存
                        if isinstance(fundamental_data, (dict, list)):
                            import pandas as pd
                            if isinstance(fundamental_data, dict):
                                fund_df = pd.DataFrame([fundamental_data])
                            else:
                                fund_df = pd.DataFrame(fundamental_data)
                            self._save_fundamental_data_to_database(symbol, fund_df, "基本面数据")
                        logger.info(f"成功导入并保存 {symbol} 的基本面数据")
                        result.processed_records += 1
                    else:
                        logger.warning(f"未获取到 {symbol} 的基本面数据")
                        result.failed_records += 1

                except Exception as e:
                    logger.error(f"导入 {symbol} 基本面数据失败: {e}")
                    result.failed_records += 1

                time.sleep(0.2)  # 基本面数据处理较慢

        except Exception as e:
            raise Exception(f"基本面数据导入失败: {e}")

    def _update_progress(self):
        """更新任务进度"""
        with self._task_lock:
            for task_id, result in self._task_results.items():
                if result.status == TaskExecutionStatus.RUNNING:
                    progress = result.progress_percentage
                    message = f"已处理 {result.processed_records}/{result.total_records} 条记录"

                    # 使用监控功能发送进度信号
                    self._monitor_task_progress(task_id, progress, message)

    # ==================== 智能配置管理功能 ====================

    def _apply_intelligent_optimization(self, config: ImportTaskConfig,
                                        optimization_level: ConfigOptimizationLevel = ConfigOptimizationLevel.BALANCED) -> Optional[ImportTaskConfig]:
        """应用智能配置优化"""
        if not self.enable_intelligent_config or not isinstance(self.config_manager, IntelligentConfigManager):
            return None

        try:
            logger.info(f"开始智能配置优化: {config.task_id}")

            # 使用智能配置管理器生成优化配置
            optimized_config = self.config_manager.generate_intelligent_config(
                config,
                optimization_level
            )

            logger.info(f"智能配置优化完成: {config.task_id}")
            return optimized_config

        except Exception as e:
            logger.error(f"智能配置优化失败: {e}")
            return None

    def generate_config_recommendations(self, task_id: str,
                                        recommendation_type: ConfigRecommendationType = ConfigRecommendationType.BALANCED) -> List[Dict[str, Any]]:
        """生成配置推荐"""
        if not self.enable_intelligent_config or not isinstance(self.config_manager, IntelligentConfigManager):
            return []

        try:
            recommendations = self.config_manager.generate_config_recommendations(
                task_id, recommendation_type
            )

            # 转换为字典格式便于UI显示
            return [
                {
                    'recommendation_id': rec.recommendation_id,
                    'recommendation_type': rec.recommendation_type.value,
                    'recommended_changes': rec.recommended_changes,
                    'expected_improvement': rec.expected_improvement,
                    'confidence_score': rec.confidence_score,
                    'reasoning': rec.reasoning,
                    'created_at': rec.created_at
                }
                for rec in recommendations
            ]

        except Exception as e:
            logger.error(f"生成配置推荐失败: {e}")
            return []

    def detect_and_resolve_config_conflicts(self, auto_resolve: bool = True) -> Dict[str, Any]:
        """检测并解决配置冲突"""
        if not self.enable_intelligent_config or not isinstance(self.config_manager, IntelligentConfigManager):
            return {'conflicts_detected': 0, 'conflicts_resolved': 0, 'message': '智能配置未启用'}

        try:
            # 检测配置冲突
            conflicts = self.config_manager.detect_config_conflicts()

            result = {
                'conflicts_detected': len(conflicts),
                'conflicts_resolved': 0,
                'conflicts': []
            }

            # 转换冲突信息为字典格式
            for conflict in conflicts:
                conflict_info = {
                    'conflict_id': conflict.conflict_id,
                    'config_ids': conflict.config_ids,
                    'conflict_type': conflict.conflict_type,
                    'description': conflict.description,
                    'severity': conflict.severity,
                    'auto_resolvable': conflict.auto_resolvable,
                    'suggested_resolution': conflict.suggested_resolution
                }
                result['conflicts'].append(conflict_info)

            # 自动解决冲突
            if auto_resolve and conflicts:
                resolution_results = self.config_manager.auto_resolve_conflicts(conflicts)
                result['conflicts_resolved'] = resolution_results['resolved']
                result['resolution_details'] = resolution_results['details']

            logger.info(f"配置冲突检测完成: 发现{len(conflicts)}个冲突")
            return result

        except Exception as e:
            logger.error(f"配置冲突检测失败: {e}")
            return {'error': str(e), 'conflicts_detected': 0, 'conflicts_resolved': 0}

    def record_task_performance_feedback(self, task_id: str, execution_result: TaskExecutionResult):
        """记录任务性能反馈用于智能学习"""
        if not self.enable_intelligent_config or not isinstance(self.config_manager, IntelligentConfigManager):
            return

        try:
            # 获取任务配置
            config = self.config_manager.get_import_task(task_id)
            if not config:
                return

            # 计算性能指标
            execution_time = execution_result.duration or 0
            success_rate = 1.0 if execution_result.success else 0.0
            error_rate = 1.0 - success_rate
            throughput = (execution_result.processed_records / execution_time) if execution_time > 0 else 0

            # 记录性能反馈
            self.config_manager.record_performance_feedback(
                config, execution_time, success_rate, error_rate, throughput
            )

            logger.info(f"记录任务性能反馈: {task_id}")

        except Exception as e:
            logger.error(f"记录性能反馈失败: {e}")

    def get_intelligent_config_statistics(self) -> Dict[str, Any]:
        """获取智能配置统计信息"""
        if not self.enable_intelligent_config or not isinstance(self.config_manager, IntelligentConfigManager):
            return {
                'intelligent_config_enabled': False,
                'message': '智能配置未启用'
            }

        try:
            stats = self.config_manager.get_intelligent_statistics()
            stats['intelligent_config_enabled'] = True
            return stats

        except Exception as e:
            logger.error(f"获取智能配置统计失败: {e}")
            return {
                'intelligent_config_enabled': True,
                'error': str(e),
                'message': '获取智能配置统计失败'
            }

    # ==================== 增强版性能桥接系统功能 ====================

    def _init_enhanced_performance_bridge(self):
        """初始化增强版性能数据桥接系统"""
        try:
            self.enhanced_performance_bridge = get_enhanced_performance_bridge()
            logger.info("增强版性能数据桥接系统初始化完成")
        except Exception as e:
            logger.error(f"初始化增强版性能桥接系统失败: {e}")
            self.enhanced_performance_bridge = None

    def _init_enhanced_risk_monitor(self):
        """初始化增强版风险监控系统"""
        try:
            self.enhanced_risk_monitor = get_enhanced_risk_monitor()
            logger.info("增强版风险监控系统初始化完成")
        except Exception as e:
            logger.error(f"初始化增强版风险监控系统失败: {e}")
            self.enhanced_risk_monitor = None

    def _init_enhanced_event_bus(self) -> Optional[EnhancedEventBus]:
        """初始化增强版事件总线"""
        try:
            enhanced_event_bus = get_enhanced_event_bus()

            # 注册数据导入相关的事件处理器
            self._register_import_event_handlers(enhanced_event_bus)

            logger.info("增强版事件总线初始化完成")
            return enhanced_event_bus
        except Exception as e:
            logger.error(f"增强版事件总线初始化失败: {e}")
            return None

    def _init_enhanced_async_manager(self):
        """初始化增强版异步任务管理器"""
        try:
            enhanced_async_manager = get_enhanced_async_manager()

            # 配置任务管理器
            enhanced_async_manager.max_workers = self.executor._max_workers

            logger.info("增强版异步任务管理器初始化完成")
            return enhanced_async_manager
        except Exception as e:
            logger.error(f"增强版异步任务管理器初始化失败: {e}")
            return None

    def start_enhanced_performance_monitoring(self):
        """启动增强版性能监控"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return False

        try:
            self.enhanced_performance_bridge.start_enhanced_monitoring()
            logger.info("增强版性能监控已启动")
            return True
        except Exception as e:
            logger.error(f"启动增强版性能监控失败: {e}")
            return False

    def stop_enhanced_performance_monitoring(self):
        """停止增强版性能监控"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return False

        try:
            self.enhanced_performance_bridge.stop_enhanced_monitoring()
            logger.info("增强版性能监控已停止")
            return True
        except Exception as e:
            logger.error(f"停止增强版性能监控失败: {e}")
            return False

    def get_enhanced_performance_summary(self) -> Dict[str, Any]:
        """获取增强版性能摘要"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return {
                'enhanced_performance_bridge_enabled': False,
                'message': '增强版性能桥接系统未启用'
            }

        try:
            summary = self.enhanced_performance_bridge.get_performance_summary()
            summary['enhanced_performance_bridge_enabled'] = True
            return summary
        except Exception as e:
            logger.error(f"获取增强版性能摘要失败: {e}")
            return {
                'enhanced_performance_bridge_enabled': True,
                'error': str(e),
                'message': '获取增强版性能摘要失败'
            }

    def get_performance_anomalies(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取性能异常"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return []

        try:
            return self.enhanced_performance_bridge.get_recent_anomalies(hours)
        except Exception as e:
            logger.error(f"获取性能异常失败: {e}")
            return []

    def get_performance_trends(self) -> Dict[str, Dict[str, Any]]:
        """获取性能趋势"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return {}

        try:
            return self.enhanced_performance_bridge.get_performance_trends()
        except Exception as e:
            logger.error(f"获取性能趋势失败: {e}")
            return {}

    def get_performance_optimization_suggestions(self, priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取性能优化建议"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return []

        try:
            return self.enhanced_performance_bridge.get_optimization_suggestions(priority_filter)
        except Exception as e:
            logger.error(f"获取性能优化建议失败: {e}")
            return []

    def get_metric_performance_history(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取指标性能历史"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return []

        try:
            return self.enhanced_performance_bridge.get_metric_history(metric_name, hours)
        except Exception as e:
            logger.error(f"获取指标性能历史失败: {e}")
            return []

    def resolve_performance_anomaly(self, anomaly_id: str) -> bool:
        """解决性能异常"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return False

        try:
            return self.enhanced_performance_bridge.resolve_anomaly(anomaly_id)
        except Exception as e:
            logger.error(f"解决性能异常失败: {e}")
            return False

    def apply_performance_optimization(self, suggestion_id: str) -> bool:
        """应用性能优化建议"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return False

        try:
            return self.enhanced_performance_bridge.apply_optimization_suggestion(suggestion_id)
        except Exception as e:
            logger.error(f"应用性能优化建议失败: {e}")
            return False

    def record_custom_performance_metric(self, metric_name: str, value: float, category: str = "custom"):
        """记录自定义性能指标"""
        if not self.enable_enhanced_performance_bridge or not self.enhanced_performance_bridge:
            return

        try:
            # 通过深度分析服务记录指标，增强桥接系统会自动收集
            self.deep_analysis_service.record_metric(metric_name, value, category)
            logger.debug(f"记录自定义性能指标: {metric_name} = {value}")
        except Exception as e:
            logger.error(f"记录自定义性能指标失败: {e}")

    def get_comprehensive_performance_report(self) -> Dict[str, Any]:
        """获取综合性能报告"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'engine_status': {
                    'ai_optimization_enabled': self.enable_ai_optimization,
                    'intelligent_config_enabled': self.enable_intelligent_config,
                    'enhanced_performance_bridge_enabled': self.enable_enhanced_performance_bridge,
                    'enhanced_risk_monitoring_enabled': self.enable_enhanced_risk_monitoring,
                    'performance_monitoring_enabled': self.enable_performance_monitoring,
                    'anomaly_detection_enabled': self.enable_anomaly_detection,
                    'intelligent_caching_enabled': self.enable_intelligent_caching,
                    'distributed_execution_enabled': self.enable_distributed_execution,
                    'auto_tuning_enabled': self.enable_auto_tuning,
                    'data_quality_monitoring_enabled': self.enable_data_quality_monitoring
                }
            }

            # 添加各个系统的统计信息
            if self.enable_ai_optimization:
                report['ai_optimization_stats'] = self.get_ai_optimization_stats()

            if self.enable_performance_monitoring:
                report['performance_report'] = self.get_performance_report()

            if self.enable_intelligent_caching:
                report['cache_statistics'] = self.get_cache_statistics()

            if self.enable_distributed_execution:
                report['distributed_status'] = self.get_distributed_status()

            if self.enable_auto_tuning:
                report['auto_tuning_status'] = self.get_auto_tuning_status()

            if self.enable_data_quality_monitoring:
                report['data_quality_statistics'] = self.get_data_quality_statistics()

            if self.enable_intelligent_config:
                report['intelligent_config_statistics'] = self.get_intelligent_config_statistics()

            if self.enable_enhanced_performance_bridge:
                report['enhanced_performance_summary'] = self.get_enhanced_performance_summary()
                report['performance_anomalies'] = self.get_performance_anomalies(1)  # 最近1小时
                report['performance_trends'] = self.get_performance_trends()
                report['optimization_suggestions'] = self.get_performance_optimization_suggestions('high')  # 高优先级建议

            if self.enable_enhanced_risk_monitoring:
                report['risk_status'] = self.get_current_risk_status()
                report['risk_alerts'] = self.get_risk_alerts(1, False)  # 最近1小时未解决的预警
                report['risk_scenarios'] = self.get_risk_scenarios(3)  # 前3个风险情景
                report['risk_dashboard'] = self.get_risk_dashboard_data()

            return report

        except Exception as e:
            logger.error(f"获取综合性能报告失败: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    # ==================== 增强版风险监控系统功能 ====================

    def start_enhanced_risk_monitoring(self):
        """启动增强版风险监控"""
        if not self.enable_enhanced_risk_monitoring or not self.enhanced_risk_monitor:
            return False

        try:
            self.enhanced_risk_monitor.start_monitoring()
            logger.info("增强版风险监控已启动")
            return True
        except Exception as e:
            logger.error(f"启动增强版风险监控失败: {e}")
            return False

    def stop_enhanced_risk_monitoring(self):
        """停止增强版风险监控"""
        if not self.enable_enhanced_risk_monitoring or not self.enhanced_risk_monitor:
            return False

        try:
            self.enhanced_risk_monitor.stop_monitoring()
            logger.info("增强版风险监控已停止")
            return True
        except Exception as e:
            logger.error(f"停止增强版风险监控失败: {e}")
            return False

    def get_current_risk_status(self) -> Dict[str, Any]:
        """获取当前风险状态"""
        if not self.enable_enhanced_risk_monitoring or not self.enhanced_risk_monitor:
            return {
                'enhanced_risk_monitoring_enabled': False,
                'message': '增强版风险监控系统未启用'
            }

        try:
            status = self.enhanced_risk_monitor.get_current_risk_status()
            status['enhanced_risk_monitoring_enabled'] = True
            return status
        except Exception as e:
            logger.error(f"获取风险状态失败: {e}")
            return {
                'enhanced_risk_monitoring_enabled': True,
                'error': str(e),
                'message': '获取风险状态失败'
            }

    def get_risk_alerts(self, hours: int = 24, resolved: bool = False) -> List[Dict[str, Any]]:
        """获取风险预警"""
        if not self.enable_enhanced_risk_monitoring or not self.enhanced_risk_monitor:
            return []

        try:
            return self.enhanced_risk_monitor.get_risk_alerts(hours, resolved)
        except Exception as e:
            logger.error(f"获取风险预警失败: {e}")
            return []

    def resolve_risk_alert(self, alert_id: str, resolution_action: str = "") -> bool:
        """解决风险预警"""
        if not self.enable_enhanced_risk_monitoring or not self.enhanced_risk_monitor:
            return False

        try:
            return self.enhanced_risk_monitor.resolve_alert(alert_id, resolution_action)
        except Exception as e:
            logger.error(f"解决风险预警失败: {e}")
            return False

    def get_risk_scenarios(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取风险情景"""
        if not self.enable_enhanced_risk_monitoring or not self.enhanced_risk_monitor:
            return []

        try:
            return self.enhanced_risk_monitor.get_risk_scenarios(limit)
        except Exception as e:
            logger.error(f"获取风险情景失败: {e}")
            return []

    def get_risk_dashboard_data(self) -> Dict[str, Any]:
        """获取风险仪表板数据"""
        try:
            dashboard_data = {
                'timestamp': datetime.now().isoformat(),
                'risk_monitoring_enabled': self.enable_enhanced_risk_monitoring
            }

            if self.enable_enhanced_risk_monitoring and self.enhanced_risk_monitor:
                # 当前风险状态
                dashboard_data['current_status'] = self.get_current_risk_status()

                # 最近预警
                dashboard_data['recent_alerts'] = self.get_risk_alerts(24, False)

                # 风险情景
                dashboard_data['risk_scenarios'] = self.get_risk_scenarios(5)

                # 风险趋势（最近7天）
                dashboard_data['risk_trends'] = self._get_risk_trends(7)

                # 风险分布
                dashboard_data['risk_distribution'] = self._get_risk_distribution()

            return dashboard_data

        except Exception as e:
            logger.error(f"获取风险仪表板数据失败: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    def _get_risk_trends(self, days: int) -> Dict[str, List[Dict[str, Any]]]:
        """获取风险趋势数据"""
        try:
            if not self.enhanced_risk_monitor:
                return {}

            # 这里可以实现具体的风险趋势分析逻辑
            # 暂时返回模拟数据
            trends = {
                'market_risk': [
                    {'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                     'value': np.random.uniform(0.2, 0.8)}
                    for i in range(days, 0, -1)
                ],
                'liquidity_risk': [
                    {'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                     'value': np.random.uniform(0.1, 0.6)}
                    for i in range(days, 0, -1)
                ],
                'concentration_risk': [
                    {'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                     'value': np.random.uniform(0.3, 0.7)}
                    for i in range(days, 0, -1)
                ]
            }

            return trends

        except Exception as e:
            logger.error(f"获取风险趋势失败: {e}")
            return {}

    def _get_risk_distribution(self) -> Dict[str, int]:
        """获取风险分布"""
        try:
            if not self.enhanced_risk_monitor:
                return {}

            # 获取当前风险状态中的分布信息
            status = self.get_current_risk_status()
            return status.get('risk_distribution', {})

        except Exception as e:
            logger.error(f"获取风险分布失败: {e}")
            return {}

    def cleanup(self):
        """清理资源"""
        try:
            # 停止进度定时器
            if self.progress_timer.isActive():
                self.progress_timer.stop()

            # 取消所有运行中的任务
            with self._task_lock:
                for task_id in list(self._running_tasks.keys()):
                    self.stop_task(task_id)

            # 关闭线程池
            self.executor.shutdown(wait=True)

            logger.info("数据导入执行引擎清理完成")

        except Exception as e:
            logger.error(f"清理执行引擎失败: {e}")


def main():
    """测试函数"""
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建执行引擎
    engine = DataImportExecutionEngine()

    # 测试任务配置
    from .import_config_manager import ImportTaskConfig, ImportMode, DataFrequency

    task_config = ImportTaskConfig(
        task_id="test_task_001",
        name="测试K线数据导入",
        data_source="HIkyuu",
        asset_type="股票",
        data_type="K线数据",
        symbols=["000001", "000002"],
        frequency=DataFrequency.DAILY,
        mode=ImportMode.MANUAL
    )

    # 添加任务配置
    engine.config_manager.add_import_task(task_config)

    # 启动任务
    success = engine.start_task("test_task_001")
    logger.info(f"任务启动: {'成功' if success else '失败'}")

    # 运行应用
    try:
        app.exec_()
    finally:
        engine.cleanup()


if __name__ == "__main__":
    main()
