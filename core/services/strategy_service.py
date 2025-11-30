from ..strategy_events import (
    StrategyStartedEvent, StrategyStoppedEvent, StrategyErrorEvent
)
from ..strategy_extensions import (
    IStrategyPlugin, StrategyInfo, StrategyContext, PerformanceMetrics,
    Signal, TradeResult, Position, StandardMarketData,
    StrategyType, AssetType, TimeFrame, RiskLevel
)
from ..containers import ServiceContainer
from ..events import EventBus
from .base_service import BaseService
from loguru import logger
"""
策略服务

提供策略插件管理、回测、优化等功能。
支持多种策略框架（FactorWeave-Quant、Backtrader、自定义等）。
"""

import json
import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import numpy as np
import pandas as pd

# ✅ 修复：确保项目根目录在 Python 路径中，以便导入 strategies 模块
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


logger = logger


class BacktestStatus(Enum):
    """回测状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OptimizationStatus(Enum):
    """优化状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_id: str
    plugin_type: str  # 'hikyuu', 'backtrader', 'custom'
    parameters: Dict[str, Any]
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestTask:
    """回测任务"""
    task_id: str
    strategy_config: StrategyConfig
    market_data: StandardMarketData
    context: StrategyContext
    status: BacktestStatus = BacktestStatus.PENDING
    progress: float = 0.0
    result: Optional[PerformanceMetrics] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class OptimizationTask:
    """优化任务"""
    task_id: str
    strategy_config: StrategyConfig
    optimization_params: Dict[str, Any]
    market_data: StandardMarketData
    context: StrategyContext
    status: OptimizationStatus = OptimizationStatus.PENDING
    progress: float = 0.0
    best_parameters: Optional[Dict[str, Any]] = None
    best_performance: Optional[PerformanceMetrics] = None
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class StrategyService(BaseService):
    """
    策略服务

    负责：
    1. 策略插件管理和注册
    2. 策略配置管理
    3. 策略回测服务
    4. 策略优化服务
    5. 策略评估和性能分析
    6. 策略模板管理
    """

    def __init__(self,
                 event_bus: Optional[EventBus] = None,
                 config: Optional[Dict[str, Any]] = None,
                 **kwargs):
        """初始化策略服务"""
        super().__init__(event_bus=event_bus, **kwargs)
        self._config = config or {}

        # 策略插件管理
        self._strategy_plugins: Dict[str, IStrategyPlugin] = {}
        self._plugin_factories: Dict[str, Callable[[], IStrategyPlugin]] = {}

        # 策略配置管理
        self._strategy_configs: Dict[str, StrategyConfig] = {}

        # 回测管理
        self._backtest_tasks: Dict[str, BacktestTask] = {}
        self._running_backtests: Dict[str, asyncio.Task] = {}

        # 优化管理
        self._optimization_tasks: Dict[str, OptimizationTask] = {}
        self._running_optimizations: Dict[str, asyncio.Task] = {}

        # 性能缓存
        self._performance_cache: Dict[str, PerformanceMetrics] = {}

        # 服务状态
        self._max_concurrent_backtests = 3
        self._max_concurrent_optimizations = 1

        # 初始化
        self._load_strategy_plugins()
        self._load_strategy_configs()

    def _do_initialize(self) -> None:
        """初始化策略服务"""
        try:
            logger.info("Strategy service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize strategy service: {e}")
            raise

    def _load_strategy_plugins(self) -> None:
        """加载策略插件"""
        try:
            # 注册内置策略插件工厂
            self._register_builtin_plugin_factories()

            logger.info(f"已注册 {len(self._plugin_factories)} 个策略插件工厂")

        except Exception as e:
            logger.error(f"加载策略插件失败: {e}")

    def _register_builtin_plugin_factories(self) -> None:
        """注册内置策略插件工厂"""
        try:
            # FactorWeave-Quant策略插件
            try:
                from plugins.strategies.hikyuu_strategy_plugin import HikyuuStrategyPlugin
                self._plugin_factories['hikyuu'] = lambda: HikyuuStrategyPlugin()
            except ImportError:
                logger.warning("FactorWeave-Quant策略插件不可用")

            # Backtrader策略插件
            try:
                from plugins.strategies.backtrader_strategy_plugin import BacktraderStrategyPlugin
                self._plugin_factories['backtrader'] = lambda: BacktraderStrategyPlugin()
            except ImportError:
                logger.warning("Backtrader策略插件不可用")

            # 20字段标准策略插件 (New)
            # ✅ 修复：确保路径正确，然后尝试导入策略插件
            try:
                # 确保项目根目录在路径中
                project_root = Path(__file__).parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))

                from strategies.adj_vwap_strategies import AdjMomentumPlugin, VWAPReversionPlugin
                self._plugin_factories['adj_momentum_v2'] = lambda: AdjMomentumPlugin()
                self._plugin_factories['vwap_reversion_v2'] = lambda: VWAPReversionPlugin()
                logger.info(">> 已注册20字段标准策略: adj_momentum_v2, vwap_reversion_v2")
            except ImportError as e:
                # ✅ 修复：详细记录导入错误，帮助诊断问题
                error_msg = str(e)
                import traceback
                logger.warning(
                    f"20字段标准策略插件导入失败: {e}\n"
                    f"项目根目录: {Path(__file__).parent.parent.parent}\n"
                    f"Python路径: {sys.path[:3]}\n"
                    f"详细错误: {traceback.format_exc()}"
                )
            except Exception as e:
                # 其他类型的错误（非导入错误）
                logger.error(f"20字段标准策略插件初始化失败: {e}", exc_info=True)

            # 自定义策略插件
            try:
                from plugins.strategies.custom_strategy_plugin import CustomStrategyPlugin
                self._plugin_factories['custom'] = lambda: CustomStrategyPlugin()
            except ImportError:
                logger.warning("自定义策略插件不可用")

        except Exception as e:
            logger.error(f"注册内置策略插件工厂失败: {e}")

    def _load_strategy_configs(self) -> None:
        """加载策略配置"""
        try:
            # 这里应该从数据库或文件加载策略配置
            # 暂时使用示例数据
            self._strategy_configs = {}
            logger.info(f"已加载 {len(self._strategy_configs)} 个策略配置")

        except Exception as e:
            logger.error(f"加载策略配置失败: {e}")

    # 策略插件管理
    def register_strategy_plugin(self, plugin_type: str, plugin_factory: Callable[[], IStrategyPlugin]) -> bool:
        """注册策略插件工厂"""
        try:
            self._plugin_factories[plugin_type] = plugin_factory
            logger.info(f"策略插件工厂已注册: {plugin_type}")
            return True

        except Exception as e:
            logger.error(f"注册策略插件工厂失败: {e}")
            return False

    def unregister_strategy_plugin(self, plugin_type: str) -> bool:
        """注销策略插件工厂"""
        try:
            if plugin_type in self._plugin_factories:
                del self._plugin_factories[plugin_type]

                # 清理相关的插件实例
                plugins_to_remove = [pid for pid, plugin in self._strategy_plugins.items()
                                     if pid.startswith(f"{plugin_type}_")]
                for plugin_id in plugins_to_remove:
                    del self._strategy_plugins[plugin_id]

                logger.info(f"策略插件工厂已注销: {plugin_type}")
                return True
            else:
                logger.warning(f"策略插件工厂不存在: {plugin_type}")
                return False

        except Exception as e:
            logger.error(f"注销策略插件工厂失败: {e}")
            return False

    def get_available_plugin_types(self) -> List[str]:
        """获取可用的策略插件类型"""
        return list(self._plugin_factories.keys())

    def create_strategy_plugin(self, plugin_type: str) -> Optional[IStrategyPlugin]:
        """创建策略插件实例"""
        try:
            if plugin_type not in self._plugin_factories:
                logger.error(f"策略插件类型不存在: {plugin_type}")
                return None

            plugin = self._plugin_factories[plugin_type]()
            plugin_id = f"{plugin_type}_{uuid.uuid4().hex[:8]}"
            self._strategy_plugins[plugin_id] = plugin

            logger.info(f"策略插件实例已创建: {plugin_id}")
            return plugin

        except Exception as e:
            logger.error(f"创建策略插件实例失败: {e}")
            return None

    def get_strategy_plugin_info(self, plugin_type: str) -> Optional[Dict[str, Any]]:
        """获取策略插件信息"""
        try:
            plugin = self.create_strategy_plugin(plugin_type)
            if plugin:
                return plugin.plugin_info
            return None

        except Exception as e:
            logger.error(f"获取策略插件信息失败: {e}")
            return None

    # 策略配置管理
    def create_strategy_config(self,
                               strategy_id: str,
                               plugin_type: str,
                               parameters: Dict[str, Any],
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """创建策略配置"""
        try:
            if strategy_id in self._strategy_configs:
                logger.error(f"策略配置已存在: {strategy_id}")
                return False

            if plugin_type not in self._plugin_factories:
                logger.error(f"策略插件类型不存在: {plugin_type}")
                return False

            config = StrategyConfig(
                strategy_id=strategy_id,
                plugin_type=plugin_type,
                parameters=parameters,
                metadata=metadata or {}
            )

            self._strategy_configs[strategy_id] = config
            logger.info(f"策略配置已创建: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"创建策略配置失败: {e}")
            return False

    def update_strategy_config(self,
                               strategy_id: str,
                               parameters: Optional[Dict[str, Any]] = None,
                               enabled: Optional[bool] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新策略配置"""
        try:
            if strategy_id not in self._strategy_configs:
                logger.error(f"策略配置不存在: {strategy_id}")
                return False

            config = self._strategy_configs[strategy_id]

            if parameters is not None:
                config.parameters.update(parameters)

            if enabled is not None:
                config.enabled = enabled

            if metadata is not None:
                config.metadata.update(metadata)

            config.updated_at = datetime.now()

            logger.info(f"策略配置已更新: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"更新策略配置失败: {e}")
            return False

    def delete_strategy_config(self, strategy_id: str) -> bool:
        """删除策略配置"""
        try:
            if strategy_id not in self._strategy_configs:
                logger.error(f"策略配置不存在: {strategy_id}")
                return False

            del self._strategy_configs[strategy_id]

            # 清理相关的回测和优化任务
            self._cleanup_strategy_tasks(strategy_id)

            logger.info(f"策略配置已删除: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"删除策略配置失败: {e}")
            return False

    def get_strategy_config(self, strategy_id: str) -> Optional[StrategyConfig]:
        """获取策略配置"""
        return self._strategy_configs.get(strategy_id)

    def get_all_strategy_configs(self) -> List[StrategyConfig]:
        """获取所有策略配置"""
        return list(self._strategy_configs.values())

    def clone_strategy_config(self, source_strategy_id: str, new_strategy_id: str) -> bool:
        """克隆策略配置"""
        try:
            if source_strategy_id not in self._strategy_configs:
                logger.error(f"源策略配置不存在: {source_strategy_id}")
                return False

            if new_strategy_id in self._strategy_configs:
                logger.error(f"目标策略配置已存在: {new_strategy_id}")
                return False

            source_config = self._strategy_configs[source_strategy_id]

            new_config = StrategyConfig(
                strategy_id=new_strategy_id,
                plugin_type=source_config.plugin_type,
                parameters=source_config.parameters.copy(),
                metadata=source_config.metadata.copy()
            )

            self._strategy_configs[new_strategy_id] = new_config

            logger.info(f"策略配置已克隆: {source_strategy_id} -> {new_strategy_id}")
            return True

        except Exception as e:
            logger.error(f"克隆策略配置失败: {e}")
            return False

    # 回测服务
    async def run_backtest(self,
                           strategy_id: str,
                           market_data: StandardMarketData,
                           context: StrategyContext) -> str:
        """运行回测"""
        try:
            if strategy_id not in self._strategy_configs:
                raise ValueError(f"策略配置不存在: {strategy_id}")

            # 检查并发限制
            if len(self._running_backtests) >= self._max_concurrent_backtests:
                raise ValueError(f"回测任务数量超限，最大允许 {self._max_concurrent_backtests} 个")

            # 创建回测任务
            task_id = f"backtest_{strategy_id}_{uuid.uuid4().hex[:8]}"

            backtest_task = BacktestTask(
                task_id=task_id,
                strategy_config=self._strategy_configs[strategy_id],
                market_data=market_data,
                context=context
            )

            self._backtest_tasks[task_id] = backtest_task

            # 启动回测任务
            async_task = asyncio.create_task(self._execute_backtest(task_id))
            self._running_backtests[task_id] = async_task

            logger.info(f"回测任务已启动: {task_id}")
            return task_id

        except Exception as e:
            logger.error(f"启动回测失败: {e}")
            raise

    async def _execute_backtest(self, task_id: str) -> None:
        """执行回测"""
        backtest_task = self._backtest_tasks[task_id]

        try:
            backtest_task.status = BacktestStatus.RUNNING
            backtest_task.started_at = datetime.now()

            # 创建策略插件实例
            plugin = self.create_strategy_plugin(backtest_task.strategy_config.plugin_type)
            if not plugin:
                raise ValueError(f"无法创建策略插件: {backtest_task.strategy_config.plugin_type}")

            # 初始化策略
            if not plugin.initialize_strategy(backtest_task.context, backtest_task.strategy_config.parameters):
                raise ValueError("策略初始化失败")

            # 执行回测
            signals = plugin.generate_signals(backtest_task.market_data, backtest_task.context)
            backtest_task.progress = 0.5

            # 模拟交易执行和性能计算
            performance = plugin.calculate_performance(backtest_task.context)
            backtest_task.progress = 1.0

            # 保存结果
            backtest_task.result = performance
            backtest_task.status = BacktestStatus.COMPLETED
            backtest_task.completed_at = datetime.now()

            # 缓存性能结果
            cache_key = f"{backtest_task.strategy_config.strategy_id}_{hash(str(backtest_task.strategy_config.parameters))}"
            self._performance_cache[cache_key] = performance

            logger.info(f"回测任务完成: {task_id}")

        except Exception as e:
            backtest_task.status = BacktestStatus.FAILED
            backtest_task.error_message = str(e)
            backtest_task.completed_at = datetime.now()

            logger.error(f"回测任务失败: {task_id}, 错误: {e}")

        finally:
            # 清理运行中的任务
            if task_id in self._running_backtests:
                del self._running_backtests[task_id]

    def get_backtest_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取回测状态"""
        if task_id not in self._backtest_tasks:
            return None

        task = self._backtest_tasks[task_id]
        return {
            'task_id': task_id,
            'status': task.status.value,
            'progress': task.progress,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'error_message': task.error_message
        }

    def get_backtest_result(self, task_id: str) -> Optional[PerformanceMetrics]:
        """获取回测结果"""
        if task_id not in self._backtest_tasks:
            return None

        task = self._backtest_tasks[task_id]
        return task.result

    def cancel_backtest(self, task_id: str) -> bool:
        """取消回测"""
        try:
            if task_id in self._running_backtests:
                self._running_backtests[task_id].cancel()
                del self._running_backtests[task_id]

            if task_id in self._backtest_tasks:
                self._backtest_tasks[task_id].status = BacktestStatus.CANCELLED

            logger.info(f"回测任务已取消: {task_id}")
            return True

        except Exception as e:
            logger.error(f"取消回测任务失败: {e}")
            return False

    # 优化服务
    async def run_optimization(self,
                               strategy_id: str,
                               optimization_params: Dict[str, Any],
                               market_data: StandardMarketData,
                               context: StrategyContext) -> str:
        """运行策略优化"""
        try:
            if strategy_id not in self._strategy_configs:
                raise ValueError(f"策略配置不存在: {strategy_id}")

            # 检查并发限制
            if len(self._running_optimizations) >= self._max_concurrent_optimizations:
                raise ValueError(f"优化任务数量超限，最大允许 {self._max_concurrent_optimizations} 个")

            # 创建优化任务
            task_id = f"optimization_{strategy_id}_{uuid.uuid4().hex[:8]}"

            optimization_task = OptimizationTask(
                task_id=task_id,
                strategy_config=self._strategy_configs[strategy_id],
                optimization_params=optimization_params,
                market_data=market_data,
                context=context
            )

            self._optimization_tasks[task_id] = optimization_task

            # 启动优化任务
            async_task = asyncio.create_task(self._execute_optimization(task_id))
            self._running_optimizations[task_id] = async_task

            logger.info(f"优化任务已启动: {task_id}")
            return task_id

        except Exception as e:
            logger.error(f"启动优化失败: {e}")
            raise

    async def _execute_optimization(self, task_id: str) -> None:
        """执行优化"""
        optimization_task = self._optimization_tasks[task_id]

        try:
            optimization_task.status = OptimizationStatus.RUNNING
            optimization_task.started_at = datetime.now()

            # 获取优化参数
            opt_params = optimization_task.optimization_params
            algorithm = opt_params.get('algorithm', 'grid_search')
            target_metric = opt_params.get('target_metric', 'total_return')
            param_ranges = opt_params.get('parameter_ranges', {})

            # 执行优化算法
            if algorithm == 'grid_search':
                await self._grid_search_optimization(optimization_task, param_ranges, target_metric)
            elif algorithm == 'random_search':
                await self._random_search_optimization(optimization_task, param_ranges, target_metric)
            elif algorithm == 'bayesian':
                await self._bayesian_optimization(optimization_task, param_ranges, target_metric)
            else:
                raise ValueError(f"不支持的优化算法: {algorithm}")

            optimization_task.status = OptimizationStatus.COMPLETED
            optimization_task.completed_at = datetime.now()

            logger.info(f"优化任务完成: {task_id}")

        except Exception as e:
            optimization_task.status = OptimizationStatus.FAILED
            optimization_task.error_message = str(e)
            optimization_task.completed_at = datetime.now()

            logger.error(f"优化任务失败: {task_id}, 错误: {e}")

        finally:
            # 清理运行中的任务
            if task_id in self._running_optimizations:
                del self._running_optimizations[task_id]

    async def _grid_search_optimization(self,
                                        optimization_task: OptimizationTask,
                                        param_ranges: Dict[str, Any],
                                        target_metric: str) -> None:
        """网格搜索优化"""
        # 生成参数组合
        param_combinations = self._generate_parameter_combinations(param_ranges)
        total_combinations = len(param_combinations)

        best_score = float('-inf')
        best_params = None
        best_performance = None

        for i, params in enumerate(param_combinations):
            try:
                # 更新策略参数
                test_params = optimization_task.strategy_config.parameters.copy()
                test_params.update(params)

                # 运行回测
                plugin = self.create_strategy_plugin(optimization_task.strategy_config.plugin_type)
                if plugin and plugin.initialize_strategy(optimization_task.context, test_params):
                    signals = plugin.generate_signals(optimization_task.market_data, optimization_task.context)
                    performance = plugin.calculate_performance(optimization_task.context)

                    # 评估性能
                    score = self._evaluate_performance(performance, target_metric)

                    # 记录历史
                    optimization_task.optimization_history.append({
                        'iteration': i + 1,
                        'parameters': params.copy(),
                        'performance': performance,
                        'score': score
                    })

                    # 更新最佳结果
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                        best_performance = performance

                # 更新进度
                optimization_task.progress = (i + 1) / total_combinations

                # 避免CPU占用过高
                if i % 10 == 0:
                    await asyncio.sleep(0.01)

            except Exception as e:
                logger.warning(f"优化迭代失败: {e}")
                continue

        # 保存最佳结果
        optimization_task.best_parameters = best_params
        optimization_task.best_performance = best_performance

    async def _random_search_optimization(self,
                                          optimization_task: OptimizationTask,
                                          param_ranges: Dict[str, Any],
                                          target_metric: str) -> None:
        """随机搜索优化"""
        max_iterations = optimization_task.optimization_params.get('max_iterations', 100)

        best_score = float('-inf')
        best_params = None
        best_performance = None

        for i in range(max_iterations):
            try:
                # 随机生成参数
                params = self._generate_random_parameters(param_ranges)

                # 更新策略参数
                test_params = optimization_task.strategy_config.parameters.copy()
                test_params.update(params)

                # 运行回测
                plugin = self.create_strategy_plugin(optimization_task.strategy_config.plugin_type)
                if plugin and plugin.initialize_strategy(optimization_task.context, test_params):
                    signals = plugin.generate_signals(optimization_task.market_data, optimization_task.context)
                    performance = plugin.calculate_performance(optimization_task.context)

                    # 评估性能
                    score = self._evaluate_performance(performance, target_metric)

                    # 记录历史
                    optimization_task.optimization_history.append({
                        'iteration': i + 1,
                        'parameters': params.copy(),
                        'performance': performance,
                        'score': score
                    })

                    # 更新最佳结果
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                        best_performance = performance

                # 更新进度
                optimization_task.progress = (i + 1) / max_iterations

                # 避免CPU占用过高
                if i % 10 == 0:
                    await asyncio.sleep(0.01)

            except Exception as e:
                logger.warning(f"优化迭代失败: {e}")
                continue

        # 保存最佳结果
        optimization_task.best_parameters = best_params
        optimization_task.best_performance = best_performance

    async def _bayesian_optimization(self,
                                     optimization_task: OptimizationTask,
                                     param_ranges: Dict[str, Any],
                                     target_metric: str) -> None:
        """贝叶斯优化（简化实现）"""
        # 这里是简化的贝叶斯优化实现
        # 实际应用中可以使用scikit-optimize等库
        max_iterations = optimization_task.optimization_params.get('max_iterations', 50)

        # 先进行少量随机搜索作为初始样本
        await self._random_search_optimization(optimization_task, param_ranges, target_metric)

        # 简化处理：使用随机搜索结果作为贝叶斯优化结果
        optimization_task.progress = 1.0

    def _generate_parameter_combinations(self, param_ranges: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成参数组合"""
        combinations = []

        # 简化实现：为每个参数生成几个值
        param_values = {}
        for param_name, param_range in param_ranges.items():
            if isinstance(param_range, dict):
                min_val = param_range.get('min', 1)
                max_val = param_range.get('max', 10)
                step = param_range.get('step', 1)
                param_values[param_name] = list(range(min_val, max_val + 1, step))
            elif isinstance(param_range, list):
                param_values[param_name] = param_range

        # 生成笛卡尔积
        import itertools
        keys = list(param_values.keys())
        values = list(param_values.values())

        for combination in itertools.product(*values):
            combinations.append(dict(zip(keys, combination)))

        return combinations

    def _generate_random_parameters(self, param_ranges: Dict[str, Any]) -> Dict[str, Any]:
        """生成随机参数"""
        import random

        params = {}
        for param_name, param_range in param_ranges.items():
            if isinstance(param_range, dict):
                min_val = param_range.get('min', 1)
                max_val = param_range.get('max', 10)
                if isinstance(min_val, int) and isinstance(max_val, int):
                    params[param_name] = random.randint(min_val, max_val)
                else:
                    params[param_name] = random.uniform(min_val, max_val)
            elif isinstance(param_range, list):
                params[param_name] = random.choice(param_range)

        return params

    def _evaluate_performance(self, performance: PerformanceMetrics, target_metric: str) -> float:
        """评估性能指标"""
        if target_metric == 'total_return':
            return performance.total_return
        elif target_metric == 'sharpe_ratio':
            return performance.sharpe_ratio
        elif target_metric == 'max_drawdown':
            return -performance.max_drawdown  # 负值，因为回撤越小越好
        elif target_metric == 'win_rate':
            return performance.win_rate
        elif target_metric == 'profit_factor':
            return performance.profit_factor
        else:
            # 默认使用总收益率
            return performance.total_return

    def get_optimization_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取优化状态"""
        if task_id not in self._optimization_tasks:
            return None

        task = self._optimization_tasks[task_id]
        return {
            'task_id': task_id,
            'status': task.status.value,
            'progress': task.progress,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'error_message': task.error_message,
            'iterations_completed': len(task.optimization_history)
        }

    def get_optimization_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取优化结果"""
        if task_id not in self._optimization_tasks:
            return None

        task = self._optimization_tasks[task_id]
        return {
            'best_parameters': task.best_parameters,
            'best_performance': task.best_performance,
            'optimization_history': task.optimization_history
        }

    def cancel_optimization(self, task_id: str) -> bool:
        """取消优化"""
        try:
            if task_id in self._running_optimizations:
                self._running_optimizations[task_id].cancel()
                del self._running_optimizations[task_id]

            if task_id in self._optimization_tasks:
                self._optimization_tasks[task_id].status = OptimizationStatus.CANCELLED

            logger.info(f"优化任务已取消: {task_id}")
            return True

        except Exception as e:
            logger.error(f"取消优化任务失败: {e}")
            return False

    # 策略评估服务
    def evaluate_strategy_performance(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """评估策略性能"""
        try:
            if strategy_id not in self._strategy_configs:
                return None

            # 获取该策略的所有回测结果
            strategy_backtests = [task for task in self._backtest_tasks.values()
                                  if task.strategy_config.strategy_id == strategy_id
                                  and task.status == BacktestStatus.COMPLETED]

            if not strategy_backtests:
                return None

            # 计算统计指标
            performances = [task.result for task in strategy_backtests if task.result]

            if not performances:
                return None

            total_returns = [p.total_return for p in performances]
            sharpe_ratios = [p.sharpe_ratio for p in performances]
            max_drawdowns = [p.max_drawdown for p in performances]
            win_rates = [p.win_rate for p in performances]

            evaluation = {
                'strategy_id': strategy_id,
                'total_backtests': len(performances),
                'performance_stats': {
                    'avg_total_return': np.mean(total_returns),
                    'std_total_return': np.std(total_returns),
                    'min_total_return': np.min(total_returns),
                    'max_total_return': np.max(total_returns),
                    'avg_sharpe_ratio': np.mean(sharpe_ratios),
                    'avg_max_drawdown': np.mean(max_drawdowns),
                    'avg_win_rate': np.mean(win_rates),
                },
                'consistency_score': 1 - (np.std(total_returns) / np.mean(total_returns)) if np.mean(total_returns) != 0 else 0,
                'risk_adjusted_return': np.mean(total_returns) / (np.mean(max_drawdowns) + 0.01),  # 避免除零
                'evaluation_date': datetime.now()
            }

            return evaluation

        except Exception as e:
            logger.error(f"评估策略性能失败: {e}")
            return None

    def compare_strategies(self, strategy_ids: List[str]) -> Optional[Dict[str, Any]]:
        """比较多个策略"""
        try:
            evaluations = {}

            for strategy_id in strategy_ids:
                evaluation = self.evaluate_strategy_performance(strategy_id)
                if evaluation:
                    evaluations[strategy_id] = evaluation

            if not evaluations:
                return None

            # 生成比较报告
            comparison = {
                'strategies': evaluations,
                'rankings': {
                    'by_total_return': sorted(evaluations.keys(),
                                              key=lambda s: evaluations[s]['performance_stats']['avg_total_return'],
                                              reverse=True),
                    'by_sharpe_ratio': sorted(evaluations.keys(),
                                              key=lambda s: evaluations[s]['performance_stats']['avg_sharpe_ratio'],
                                              reverse=True),
                    'by_consistency': sorted(evaluations.keys(),
                                             key=lambda s: evaluations[s]['consistency_score'],
                                             reverse=True),
                    'by_risk_adjusted_return': sorted(evaluations.keys(),
                                                      key=lambda s: evaluations[s]['risk_adjusted_return'],
                                                      reverse=True)
                },
                'comparison_date': datetime.now()
            }

            return comparison

        except Exception as e:
            logger.error(f"比较策略失败: {e}")
            return None

    # 辅助方法
    def _cleanup_strategy_tasks(self, strategy_id: str) -> None:
        """清理策略相关的任务"""
        # 清理回测任务
        backtest_tasks_to_remove = [task_id for task_id, task in self._backtest_tasks.items()
                                    if task.strategy_config.strategy_id == strategy_id]
        for task_id in backtest_tasks_to_remove:
            self.cancel_backtest(task_id)
            del self._backtest_tasks[task_id]

        # 清理优化任务
        optimization_tasks_to_remove = [task_id for task_id, task in self._optimization_tasks.items()
                                        if task.strategy_config.strategy_id == strategy_id]
        for task_id in optimization_tasks_to_remove:
            self.cancel_optimization(task_id)
            del self._optimization_tasks[task_id]

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'service_name': 'StrategyService',
            'status': 'running',
            'plugin_types_count': len(self._plugin_factories),
            'strategy_configs_count': len(self._strategy_configs),
            'active_backtests': len(self._running_backtests),
            'active_optimizations': len(self._running_optimizations),
            'total_backtest_tasks': len(self._backtest_tasks),
            'total_optimization_tasks': len(self._optimization_tasks),
            'performance_cache_size': len(self._performance_cache),
            'last_update': datetime.now().isoformat()
        }

    def _do_dispose(self) -> None:
        """清理资源"""
        try:
            # 取消所有运行中的任务
            for task_id in list(self._running_backtests.keys()):
                self.cancel_backtest(task_id)

            for task_id in list(self._running_optimizations.keys()):
                self.cancel_optimization(task_id)

            # 清理插件实例
            self._strategy_plugins.clear()

            super()._do_dispose()
            logger.info("Strategy service disposed")

        except Exception as e:
            logger.error(f"Failed to dispose strategy service: {e}")
