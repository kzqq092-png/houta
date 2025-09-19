"""
统一插件数据管理器

统一HIkyuu-UI系统的数据源管理，建立单一的插件中心架构，
消除三套并行数据源管理体系，实现真正的插件中心统一管理。

作者: FactorWeave-Quant团队
版本: 1.0
日期: 2024-09-17
"""

import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from loguru import logger
from core.plugin_types import AssetType, DataType, PluginType
from core.data_source_extensions import IDataSourcePlugin, PluginInfo, HealthCheckResult
from core.tet_data_pipeline import TETDataPipeline, StandardQuery, StandardData
from core.data_source_router import DataSourceRouter, RoutingStrategy
from core.plugin_manager import PluginManager

logger = logger.bind(module=__name__)


@dataclass
class RequestContext:
    """请求上下文"""
    asset_type: AssetType
    data_type: DataType
    symbol: Optional[str] = None
    market: Optional[str] = None
    priority: int = 50
    quality_requirement: float = 0.8
    timeout: int = 30
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PluginMetrics:
    """插件性能指标"""
    plugin_id: str
    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    quality_score: float = 1.0
    availability_score: float = 1.0


@dataclass
class ValidationResult:
    """数据验证结果"""
    is_valid: bool
    quality_score: float
    consistency_score: float
    anomaly_score: float
    validation_details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class PluginCenter:
    """
    插件中心 - 统一插件管理
    
    基于现有PluginManager增强，专注于数据源插件的统一管理
    """
    
    def __init__(self, plugin_manager: PluginManager):
        """
        初始化插件中心
        
        Args:
            plugin_manager: 现有的插件管理器实例
        """
        self.plugin_manager = plugin_manager
        self.data_source_plugins: Dict[str, IDataSourcePlugin] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.plugin_health: Dict[str, HealthCheckResult] = {}
        self.plugin_metrics: Dict[str, PluginMetrics] = {}
        
        # 线程安全
        self._lock = threading.RLock()
        
        logger.info("插件中心初始化完成")
    
    def discover_and_register_plugins(self) -> Dict[str, str]:
        """
        发现并注册所有数据源插件
        
        Returns:
            Dict[str, str]: 注册结果 {plugin_id: status}
        """
        registration_results = {}
        
        try:
            with self._lock:
                # 1. 获取所有已加载的插件
                all_plugins = self.plugin_manager.get_all_plugins()
                
                # 2. 筛选数据源插件
                for plugin_name, plugin_instance in all_plugins.items():
                    try:
                        if self._is_data_source_plugin(plugin_instance):
                            result = self._register_data_source_plugin(plugin_name, plugin_instance)
                            registration_results[plugin_name] = "success" if result else "failed"
                        else:
                            registration_results[plugin_name] = "skipped_not_data_source"
                            
                    except Exception as e:
                        logger.error(f"注册插件失败 {plugin_name}: {e}")
                        registration_results[plugin_name] = f"error: {str(e)}"
                
                logger.info(f"插件发现和注册完成，成功注册 {len(self.data_source_plugins)} 个数据源插件")
                
        except Exception as e:
            logger.error(f"插件发现和注册过程异常: {e}")
            
        return registration_results
    
    def _is_data_source_plugin(self, plugin_instance) -> bool:
        """检查是否为数据源插件"""
        # 检查是否实现了IDataSourcePlugin接口
        if not isinstance(plugin_instance, IDataSourcePlugin):
            return False
            
        # 检查插件信息中的类型
        if hasattr(plugin_instance, 'plugin_info'):
            plugin_info = plugin_instance.plugin_info
            if hasattr(plugin_info, 'plugin_type'):
                return plugin_info.plugin_type == PluginType.DATA_SOURCE
                
        return True
    
    def _register_data_source_plugin(self, plugin_id: str, plugin: IDataSourcePlugin) -> bool:
        """注册数据源插件"""
        try:
            # 存储插件实例
            self.data_source_plugins[plugin_id] = plugin
            
            # 初始化插件指标
            self.plugin_metrics[plugin_id] = PluginMetrics(plugin_id=plugin_id)
            
            # 加载插件配置
            self._load_plugin_config(plugin_id, plugin)
            
            # 初始健康检查
            self._perform_initial_health_check(plugin_id, plugin)
            
            logger.info(f"数据源插件注册成功: {plugin_id}")
            return True
            
        except Exception as e:
            logger.error(f"注册数据源插件失败 {plugin_id}: {e}")
            return False
    
    def _load_plugin_config(self, plugin_id: str, plugin: IDataSourcePlugin) -> None:
        """加载插件配置"""
        try:
            # 从插件获取默认配置
            if hasattr(plugin, 'get_default_config'):
                default_config = plugin.get_default_config()
                self.plugin_configs[plugin_id] = default_config
            else:
                self.plugin_configs[plugin_id] = {}
                
        except Exception as e:
            logger.warning(f"加载插件配置失败 {plugin_id}: {e}")
            self.plugin_configs[plugin_id] = {}
    
    def _perform_initial_health_check(self, plugin_id: str, plugin: IDataSourcePlugin) -> None:
        """执行初始健康检查"""
        try:
            health_result = plugin.health_check()
            self.plugin_health[plugin_id] = health_result
            
            if health_result.is_healthy:
                logger.info(f"插件健康检查通过: {plugin_id}")
            else:
                logger.warning(f"插件健康检查失败: {plugin_id} - {health_result.message}")
                
        except Exception as e:
            logger.error(f"插件健康检查异常 {plugin_id}: {e}")
            # 创建失败的健康检查结果
            self.plugin_health[plugin_id] = HealthCheckResult(
                is_healthy=False,
                message=f"健康检查异常: {str(e)}",
                details={"error": str(e)}
            )
    
    def get_available_plugins(self, data_type: DataType, 
                            asset_type: Optional[AssetType] = None,
                            market: Optional[str] = None) -> List[str]:
        """
        获取可用的插件列表
        
        Args:
            data_type: 数据类型
            asset_type: 资产类型（可选）
            market: 市场代码（可选）
            
        Returns:
            List[str]: 可用插件ID列表
        """
        available_plugins = []
        
        with self._lock:
            for plugin_id, plugin in self.data_source_plugins.items():
                try:
                    # 检查健康状态
                    if plugin_id in self.plugin_health:
                        health = self.plugin_health[plugin_id]
                        if not health.is_healthy:
                            continue
                    
                    # 检查插件能力
                    plugin_info = plugin.plugin_info
                    
                    # 检查支持的数据类型
                    if data_type not in plugin_info.supported_data_types:
                        continue
                    
                    # 检查支持的资产类型
                    if asset_type and asset_type not in plugin_info.supported_asset_types:
                        continue
                    
                    # 检查支持的市场
                    if market and hasattr(plugin_info, 'supported_markets'):
                        if market not in plugin_info.supported_markets:
                            continue
                    
                    available_plugins.append(plugin_id)
                    
                except Exception as e:
                    logger.warning(f"检查插件可用性失败 {plugin_id}: {e}")
        
        return available_plugins
    
    def get_plugin(self, plugin_id: str) -> Optional[IDataSourcePlugin]:
        """获取插件实例"""
        return self.data_source_plugins.get(plugin_id)
    
    def update_plugin_metrics(self, plugin_id: str, success: bool, 
                            response_time: float, quality_score: float = None) -> None:
        """更新插件性能指标"""
        if plugin_id not in self.plugin_metrics:
            return
            
        metrics = self.plugin_metrics[plugin_id]
        metrics.total_requests += 1
        
        if success:
            metrics.success_requests += 1
            metrics.last_success_time = datetime.now()
            if quality_score is not None:
                # 使用指数移动平均更新质量分数
                alpha = 0.1
                metrics.quality_score = alpha * quality_score + (1 - alpha) * metrics.quality_score
        else:
            metrics.failed_requests += 1
            metrics.last_failure_time = datetime.now()
        
        # 更新平均响应时间
        alpha = 0.1
        metrics.avg_response_time = alpha * response_time + (1 - alpha) * metrics.avg_response_time
        
        # 更新可用性分数
        if metrics.total_requests > 0:
            metrics.availability_score = metrics.success_requests / metrics.total_requests


class TETRouterEngine:
    """
    TET智能路由引擎
    
    基于现有DataSourceRouter和TETDataPipeline增强
    """
    
    def __init__(self, data_source_router: DataSourceRouter, tet_pipeline: TETDataPipeline):
        """
        初始化TET路由引擎
        
        Args:
            data_source_router: 数据源路由器
            tet_pipeline: TET数据管道
        """
        self.router = data_source_router
        self.pipeline = tet_pipeline
        self.routing_strategies = {
            'HEALTH_PRIORITY': self._health_priority_strategy,
            'QUALITY_WEIGHTED': self._quality_weighted_strategy,
            'ROUND_ROBIN': self._round_robin_strategy,
            'CIRCUIT_BREAKER': self._circuit_breaker_strategy
        }
        self.default_strategy = 'HEALTH_PRIORITY'
        
        logger.info("TET路由引擎初始化完成")
    
    def register_plugin(self, plugin_id: str, plugin: IDataSourcePlugin, 
                       priority: int = 50, weight: float = 1.0) -> bool:
        """
        向TET路由器注册插件
        
        Args:
            plugin_id: 插件ID
            plugin: 插件实例
            priority: 优先级
            weight: 权重
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 创建插件适配器
            from core.data_source_extensions import DataSourcePluginAdapter
            adapter = DataSourcePluginAdapter(plugin, plugin_id)
            
            # 注册到路由器
            success = self.router.register_data_source(plugin_id, adapter, priority, weight)
            
            if success:
                logger.info(f"插件注册到TET路由器成功: {plugin_id}")
            else:
                logger.warning(f"插件注册到TET路由器失败: {plugin_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"注册插件到TET路由器异常 {plugin_id}: {e}")
            return False
    
    def select_optimal_plugin(self, available_plugins: List[str], 
                            context: RequestContext,
                            plugin_center: PluginCenter,
                            strategy: str = None) -> Optional[str]:
        """
        选择最优插件
        
        Args:
            available_plugins: 可用插件列表
            context: 请求上下文
            plugin_center: 插件中心
            strategy: 路由策略
            
        Returns:
            Optional[str]: 选中的插件ID
        """
        if not available_plugins:
            logger.warning("没有可用的插件")
            return None
        
        strategy_name = strategy or self.default_strategy
        strategy_func = self.routing_strategies.get(strategy_name, self._health_priority_strategy)
        
        try:
            selected_plugin = strategy_func(available_plugins, context, plugin_center)
            if selected_plugin:
                logger.debug(f"路由策略 {strategy_name} 选择插件: {selected_plugin}")
            return selected_plugin
            
        except Exception as e:
            logger.error(f"插件选择失败 - 策略: {strategy_name}, 错误: {e}")
            # 降级到简单的第一个可用插件
            return available_plugins[0] if available_plugins else None
    
    def _health_priority_strategy(self, available_plugins: List[str], 
                                context: RequestContext,
                                plugin_center: PluginCenter) -> Optional[str]:
        """基于健康状态的优先级策略"""
        best_plugin = None
        best_score = -1
        
        for plugin_id in available_plugins:
            score = 0
            
            # 健康状态权重 (50%)
            if plugin_id in plugin_center.plugin_health:
                health = plugin_center.plugin_health[plugin_id]
                if health.is_healthy:
                    score += 50
            
            # 质量分数权重 (30%)
            if plugin_id in plugin_center.plugin_metrics:
                metrics = plugin_center.plugin_metrics[plugin_id]
                score += metrics.quality_score * 30
            
            # 可用性分数权重 (20%)
            if plugin_id in plugin_center.plugin_metrics:
                metrics = plugin_center.plugin_metrics[plugin_id]
                score += metrics.availability_score * 20
            
            if score > best_score:
                best_score = score
                best_plugin = plugin_id
        
        return best_plugin
    
    def _quality_weighted_strategy(self, available_plugins: List[str],
                                 context: RequestContext,
                                 plugin_center: PluginCenter) -> Optional[str]:
        """基于质量权重的策略"""
        import random
        
        # 计算每个插件的权重
        weights = []
        plugins = []
        
        for plugin_id in available_plugins:
            weight = 1.0  # 默认权重
            
            if plugin_id in plugin_center.plugin_metrics:
                metrics = plugin_center.plugin_metrics[plugin_id]
                weight = metrics.quality_score * metrics.availability_score
            
            weights.append(weight)
            plugins.append(plugin_id)
        
        if not weights:
            return None
        
        # 加权随机选择
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(plugins)
        
        r = random.uniform(0, total_weight)
        cumulative_weight = 0
        
        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return plugins[i]
        
        return plugins[-1]
    
    def _round_robin_strategy(self, available_plugins: List[str],
                            context: RequestContext,
                            plugin_center: PluginCenter) -> Optional[str]:
        """轮询策略"""
        if not hasattr(self, '_round_robin_index'):
            self._round_robin_index = 0
        
        if available_plugins:
            plugin = available_plugins[self._round_robin_index % len(available_plugins)]
            self._round_robin_index += 1
            return plugin
        
        return None
    
    def _circuit_breaker_strategy(self, available_plugins: List[str],
                                context: RequestContext,
                                plugin_center: PluginCenter) -> Optional[str]:
        """熔断器策略"""
        # 过滤掉故障率过高的插件
        healthy_plugins = []
        
        for plugin_id in available_plugins:
            if plugin_id in plugin_center.plugin_metrics:
                metrics = plugin_center.plugin_metrics[plugin_id]
                # 如果总请求数大于10且成功率小于50%，则认为不健康
                if metrics.total_requests > 10:
                    success_rate = metrics.success_requests / metrics.total_requests
                    if success_rate >= 0.5:
                        healthy_plugins.append(plugin_id)
                else:
                    # 请求数较少，给机会
                    healthy_plugins.append(plugin_id)
            else:
                # 没有指标，给机会
                healthy_plugins.append(plugin_id)
        
        # 在健康的插件中使用健康优先策略
        if healthy_plugins:
            return self._health_priority_strategy(healthy_plugins, context, plugin_center)
        
        # 如果没有健康的插件，返回第一个可用的插件
        return available_plugins[0] if available_plugins else None


class RiskManager:
    """
    风险管理器
    
    负责数据质量监控、异常检测、熔断器管理等
    """
    
    def __init__(self):
        """初始化风险管理器"""
        self.quality_thresholds = {
            'completeness': 0.95,    # 数据完整性阈值
            'accuracy': 0.90,        # 数据准确性阈值
            'timeliness': 300,       # 数据时效性阈值(秒)
            'consistency': 0.85      # 数据一致性阈值
        }
        
        self.execution_history: Dict[str, List[Dict]] = {}
        self._lock = threading.RLock()
        
        logger.info("风险管理器初始化完成")
    
    def execute_with_monitoring(self, plugin_id: str, func, **params) -> Tuple[Any, ValidationResult]:
        """
        带监控的执行
        
        Args:
            plugin_id: 插件ID
            func: 执行函数
            **params: 函数参数
            
        Returns:
            Tuple[Any, ValidationResult]: (执行结果, 验证结果)
        """
        start_time = datetime.now()
        validation_result = None
        
        try:
            # 执行数据获取
            result = func(**params)
            
            # 数据质量检查
            validation_result = self._validate_data_quality(result)
            
            # 记录成功执行
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_execution(plugin_id, True, execution_time, validation_result.quality_score)
            
            return result, validation_result
            
        except Exception as e:
            # 记录失败执行
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_execution(plugin_id, False, execution_time, 0.0, str(e))
            
            # 创建失败的验证结果
            validation_result = ValidationResult(
                is_valid=False,
                quality_score=0.0,
                consistency_score=0.0,
                anomaly_score=1.0,
                validation_details={"error": str(e)},
                recommendations=["检查插件连接状态", "尝试其他数据源"]
            )
            
            raise
    
    def _validate_data_quality(self, data: Any) -> ValidationResult:
        """验证数据质量"""
        try:
            if data is None:
                return ValidationResult(
                    is_valid=False,
                    quality_score=0.0,
                    consistency_score=0.0,
                    anomaly_score=1.0,
                    recommendations=["数据为空，检查数据源"]
                )
            
            if isinstance(data, pd.DataFrame):
                return self._validate_dataframe_quality(data)
            elif isinstance(data, list):
                return self._validate_list_quality(data)
            else:
                # 对于其他类型的数据，进行基本检查
                return ValidationResult(
                    is_valid=True,
                    quality_score=0.8,
                    consistency_score=0.8,
                    anomaly_score=0.1
                )
                
        except Exception as e:
            logger.error(f"数据质量验证异常: {e}")
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                consistency_score=0.0,
                anomaly_score=1.0,
                validation_details={"validation_error": str(e)}
            )
    
    def _validate_dataframe_quality(self, df: pd.DataFrame) -> ValidationResult:
        """验证DataFrame数据质量"""
        if df.empty:
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                consistency_score=0.0,
                anomaly_score=1.0,
                recommendations=["DataFrame为空"]
            )
        
        # 计算完整性分数
        completeness_score = 1.0 - (df.isnull().sum().sum() / (df.shape[0] * df.shape[1]))
        
        # 计算一致性分数 (基于数据类型一致性)
        consistency_score = 0.9  # 简化计算
        
        # 计算异常分数 (基于数值列的异常值检测)
        anomaly_score = 0.1  # 简化计算
        
        # 计算整体质量分数
        quality_score = (completeness_score * 0.4 + 
                        consistency_score * 0.4 + 
                        (1 - anomaly_score) * 0.2)
        
        return ValidationResult(
            is_valid=quality_score >= 0.7,
            quality_score=quality_score,
            consistency_score=consistency_score,
            anomaly_score=anomaly_score,
            validation_details={
                "row_count": len(df),
                "column_count": len(df.columns),
                "null_count": df.isnull().sum().sum(),
                "completeness_score": completeness_score
            }
        )
    
    def _validate_list_quality(self, data: List) -> ValidationResult:
        """验证列表数据质量"""
        if not data:
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                consistency_score=0.0,
                anomaly_score=1.0,
                recommendations=["列表为空"]
            )
        
        # 计算完整性 (非None元素比例)
        non_none_count = sum(1 for item in data if item is not None)
        completeness_score = non_none_count / len(data)
        
        # 简化的质量评估
        quality_score = completeness_score * 0.8 + 0.2  # 给基础分数
        
        return ValidationResult(
            is_valid=quality_score >= 0.6,
            quality_score=quality_score,
            consistency_score=0.8,
            anomaly_score=0.1,
            validation_details={
                "item_count": len(data),
                "non_none_count": non_none_count,
                "completeness_score": completeness_score
            }
        )
    
    def _record_execution(self, plugin_id: str, success: bool, 
                         execution_time: float, quality_score: float = 0.0,
                         error_message: str = None) -> None:
        """记录执行历史"""
        with self._lock:
            if plugin_id not in self.execution_history:
                self.execution_history[plugin_id] = []
            
            record = {
                'timestamp': datetime.now(),
                'success': success,
                'execution_time': execution_time,
                'quality_score': quality_score,
                'error_message': error_message
            }
            
            self.execution_history[plugin_id].append(record)
            
            # 保留最近100条记录
            if len(self.execution_history[plugin_id]) > 100:
                self.execution_history[plugin_id] = self.execution_history[plugin_id][-100:]


class UniPluginDataManager:
    """
    统一插件数据管理器
    
    HIkyuu-UI系统的统一数据访问入口，协调插件中心、TET路由引擎和风险管理器
    """
    
    def __init__(self, plugin_manager: PluginManager, 
                 data_source_router: DataSourceRouter,
                 tet_pipeline: TETDataPipeline):
        """
        初始化统一插件数据管理器
        
        Args:
            plugin_manager: 插件管理器
            data_source_router: 数据源路由器
            tet_pipeline: TET数据管道
        """
        self.plugin_center = PluginCenter(plugin_manager)
        self.tet_engine = TETRouterEngine(data_source_router, tet_pipeline)
        self.risk_manager = RiskManager()
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "avg_response_time": 0.0
        }
        
        # 缓存
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("统一插件数据管理器初始化完成")
    
    def initialize(self) -> None:
        """初始化管理器"""
        try:
            # 1. 发现和注册插件
            registration_results = self.plugin_center.discover_and_register_plugins()
            
            # 2. 将插件注册到TET路由引擎
            registered_count = 0
            for plugin_id, plugin in self.plugin_center.data_source_plugins.items():
                if self.tet_engine.register_plugin(plugin_id, plugin):
                    registered_count += 1
            
            logger.info(f"统一插件数据管理器初始化完成，注册了 {registered_count} 个插件到TET引擎")
            
        except Exception as e:
            logger.error(f"统一插件数据管理器初始化失败: {e}")
            raise
    
    def get_stock_list(self, market: str = None, **params) -> List[Dict[str, Any]]:
        """
        获取股票列表 - 统一入口
        
        Args:
            market: 市场代码
            **params: 其他参数
            
        Returns:
            List[Dict[str, Any]]: 股票列表
        """
        context = RequestContext(
            asset_type=AssetType.STOCK,
            data_type=DataType.ASSET_LIST,
            market=market
        )
        
        return self._execute_data_request(context, 'get_asset_list', **params)
    
    def get_fund_list(self, market: str = None, **params) -> List[Dict[str, Any]]:
        """
        获取基金列表 - 统一入口
        
        Args:
            market: 市场代码
            **params: 其他参数
            
        Returns:
            List[Dict[str, Any]]: 基金列表
        """
        context = RequestContext(
            asset_type=AssetType.FUND,
            data_type=DataType.ASSET_LIST,
            market=market
        )
        
        return self._execute_data_request(context, 'get_asset_list', **params)
    
    def get_index_list(self, market: str = None, **params) -> List[Dict[str, Any]]:
        """
        获取指数列表 - 统一入口
        
        Args:
            market: 市场代码
            **params: 其他参数
            
        Returns:
            List[Dict[str, Any]]: 指数列表
        """
        context = RequestContext(
            asset_type=AssetType.INDEX,
            data_type=DataType.ASSET_LIST,
            market=market
        )
        
        return self._execute_data_request(context, 'get_asset_list', **params)
    
    def get_kdata(self, symbol: str, freq: str = "D", 
                  start_date: str = None, end_date: str = None, 
                  count: int = None, **params) -> pd.DataFrame:
        """
        获取K线数据 - 统一入口
        
        Args:
            symbol: 股票代码
            freq: 频率
            start_date: 开始日期
            end_date: 结束日期
            count: 数据数量
            **params: 其他参数
            
        Returns:
            pd.DataFrame: K线数据
        """
        context = RequestContext(
            asset_type=AssetType.STOCK,
            data_type=DataType.HISTORICAL_KLINE,
            symbol=symbol
        )
        
        return self._execute_data_request(
            context, 'get_kdata',
            symbol=symbol, freq=freq, start_date=start_date, 
            end_date=end_date, count=count, **params
        )
    
    def get_real_time_quotes(self, symbols: List[str], **params) -> List[Dict[str, Any]]:
        """
        获取实时行情 - 统一入口
        
        Args:
            symbols: 股票代码列表
            **params: 其他参数
            
        Returns:
            List[Dict[str, Any]]: 实时行情数据
        """
        context = RequestContext(
            asset_type=AssetType.STOCK,
            data_type=DataType.REAL_TIME_QUOTE
        )
        
        return self._execute_data_request(
            context, 'get_real_time_quotes',
            symbols=symbols, **params
        )
    
    def _execute_data_request(self, context: RequestContext, method_name: str, **params) -> Any:
        """
        执行数据请求的核心逻辑
        
        Args:
            context: 请求上下文
            method_name: 方法名
            **params: 方法参数
            
        Returns:
            Any: 请求结果
        """
        start_time = datetime.now()
        self.stats["total_requests"] += 1
        
        try:
            # 1. 检查缓存
            cache_key = self._generate_cache_key(context, method_name, **params)
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                self.stats["cache_hits"] += 1
                return cached_result
            
            # 2. 获取可用插件
            available_plugins = self.plugin_center.get_available_plugins(
                context.data_type, context.asset_type, context.market
            )
            
            if not available_plugins:
                raise RuntimeError(f"没有可用的插件支持数据类型: {context.data_type}")
            
            # 3. 选择最优插件
            selected_plugin_id = self.tet_engine.select_optimal_plugin(
                available_plugins, context, self.plugin_center
            )
            
            if not selected_plugin_id:
                raise RuntimeError("无法选择合适的插件")
            
            # 4. 获取插件实例
            plugin = self.plugin_center.get_plugin(selected_plugin_id)
            if not plugin:
                raise RuntimeError(f"无法获取插件实例: {selected_plugin_id}")
            
            # 5. 执行数据获取
            method = getattr(plugin, method_name)
            result, validation_result = self.risk_manager.execute_with_monitoring(
                selected_plugin_id, method, **params
            )
            
            # 6. 更新插件指标
            execution_time = (datetime.now() - start_time).total_seconds()
            self.plugin_center.update_plugin_metrics(
                selected_plugin_id, True, execution_time, validation_result.quality_score
            )
            
            # 7. 缓存结果
            if validation_result.is_valid:
                self._cache_result(cache_key, result)
            
            # 8. 更新统计信息
            self.stats["successful_requests"] += 1
            self._update_avg_response_time(execution_time)
            
            logger.debug(f"数据请求成功 - 插件: {selected_plugin_id}, 方法: {method_name}, 用时: {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            # 更新失败统计
            self.stats["failed_requests"] += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_avg_response_time(execution_time)
            
            logger.error(f"数据请求失败 - 方法: {method_name}, 错误: {e}")
            raise
    
    def _generate_cache_key(self, context: RequestContext, method_name: str, **params) -> str:
        """生成缓存键"""
        import hashlib
        import json
        
        # 创建缓存键的组件
        key_components = {
            'method': method_name,
            'asset_type': context.asset_type.value if context.asset_type else None,
            'data_type': context.data_type.value if context.data_type else None,
            'symbol': context.symbol,
            'market': context.market,
            'params': params
        }
        
        # 序列化并生成哈希
        key_str = json.dumps(key_components, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_data
            else:
                # 清理过期缓存
                del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Any) -> None:
        """缓存结果"""
        self._cache[cache_key] = (result, datetime.now())
        
        # 限制缓存大小
        if len(self._cache) > 1000:
            # 删除最旧的缓存项
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
    
    def _update_avg_response_time(self, response_time: float) -> None:
        """更新平均响应时间"""
        total_requests = self.stats["total_requests"]
        if total_requests == 1:
            self.stats["avg_response_time"] = response_time
        else:
            # 使用指数移动平均
            alpha = 0.1
            self.stats["avg_response_time"] = (
                alpha * response_time + (1 - alpha) * self.stats["avg_response_time"]
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def clear_cache(self) -> None:
        """清理缓存"""
        self._cache.clear()
        logger.info("缓存已清理")
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(),
            "plugin_center": {
                "total_plugins": len(self.plugin_center.data_source_plugins),
                "healthy_plugins": sum(
                    1 for health in self.plugin_center.plugin_health.values()
                    if health.is_healthy
                )
            },
            "cache": {
                "cache_size": len(self._cache),
                "cache_hit_rate": (
                    self.stats["cache_hits"] / max(self.stats["total_requests"], 1)
                )
            },
            "performance": self.stats
        }
        
        return health_status


# 全局实例管理
_uni_plugin_data_manager: Optional[UniPluginDataManager] = None


def get_uni_plugin_data_manager() -> Optional[UniPluginDataManager]:
    """获取统一插件数据管理器实例"""
    return _uni_plugin_data_manager


def set_uni_plugin_data_manager(manager: UniPluginDataManager) -> None:
    """设置统一插件数据管理器实例"""
    global _uni_plugin_data_manager
    _uni_plugin_data_manager = manager
    logger.info("统一插件数据管理器全局实例已设置")
