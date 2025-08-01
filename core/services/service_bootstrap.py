"""
服务引导模块

负责在应用程序启动时按正确的顺序注册和初始化所有服务。
"""

import logging
from typing import Optional
import traceback

# 先导入容器和事件总线
from core.containers import ServiceContainer, get_service_container
from core.containers.service_registry import ServiceScope
from core.events import EventBus, get_event_bus

# 然后导入服务类型
from core.services.config_service import ConfigService
from core.services.theme_service import ThemeService
from core.services.stock_service import StockService
from core.services.chart_service import ChartService
from core.services.analysis_service import AnalysisService
from core.services.industry_service import IndustryService
from core.services.ai_prediction_service import AIPredictionService
from core.services.unified_data_manager import UnifiedDataManager
from core.plugin_manager import PluginManager
from core.logger import LogManager

# 最后导入监控服务
from core.metrics.repository import MetricsRepository
from core.metrics.resource_service import SystemResourceService
from core.metrics.app_metrics_service import ApplicationMetricsService, initialize_app_metrics_service
from core.metrics.aggregation_service import MetricsAggregationService

logger = logging.getLogger(__name__)


class ServiceBootstrap:
    """
    服务引导类

    负责在应用程序启动时按正确的顺序注册和初始化所有服务。
    """

    def __init__(self, service_container: Optional[ServiceContainer] = None):
        """
        初始化服务引导器

        Args:
            service_container: 服务容器，如果为None则使用全局容器
        """
        self.service_container = service_container or get_service_container()
        self.event_bus = get_event_bus()

    def bootstrap(self) -> bool:
        """
        引导所有服务

        Returns:
            引导是否成功
        """
        try:
            # 1. 注册核心服务
            self._register_core_services()

            # 2. 注册业务服务
            self._register_business_services()

            # 3. 注册交易服务
            self._register_trading_service()

            # 4. 注册监控服务
            self._register_monitoring_services()

            # 5. 注册插件服务
            self._register_plugin_services()

            return True
        except Exception as e:
            logger.error(f"服务引导失败: {e}")
            logger.error(traceback.format_exc())
            return False

    def _register_core_services(self) -> None:
        """注册核心服务"""
        logger.info("注册核心服务...")

        # 注册事件总线 (EventBus)
        self.service_container.register_instance(EventBus, self.event_bus)
        # 确保也注册具体类型，以便能够通过类型注入
        self.service_container.register_instance(
            type(self.event_bus), self.event_bus)
        logger.info("✓ 事件总线注册完成")

        # 注册 ConfigManager
        from utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        self.service_container.register_instance(ConfigManager, config_manager)
        logger.info("✓ ConfigManager 注册完成")

        # 注册配置服务
        config_service = ConfigService(config_file='config/config.json')
        config_service.initialize()
        self.service_container.register_instance(ConfigService, config_service)
        logger.info("✓ 配置服务注册完成")

        # 注册日志服务
        log_manager = LogManager()
        self.service_container.register_instance(LogManager, log_manager)
        logger.info("✓ 日志服务注册完成")

    def _register_business_services(self) -> None:
        """注册业务服务"""
        logger.info("注册业务服务...")

        # 添加依赖检查
        self._check_dependencies()

        # 先注册UnifiedDataManager
        self.service_container.register_factory(
            UnifiedDataManager,
            lambda: UnifiedDataManager(self.service_container, self.event_bus)
        )

        # 确保初始化成功后再继续
        try:
            data_manager = self.service_container.resolve(UnifiedDataManager)
            logger.info("✓ 统一数据管理器注册完成")
        except Exception as e:
            logger.error(f"Failed to initialize UnifiedDataManager: {e}")
            # 提供回退机制
            self._initialize_fallback_data_manager()

        # 主题服务
        self.service_container.register(
            ThemeService, scope=ServiceScope.SINGLETON)
        theme_service = self.service_container.resolve(ThemeService)
        theme_service.initialize()
        logger.info("✓ 主题服务注册完成")

        # 股票服务
        self.service_container.register(
            StockService, scope=ServiceScope.SINGLETON)
        stock_service = self.service_container.resolve(StockService)
        stock_service.initialize()
        logger.info("✓ 股票服务注册完成")

        # 图表服务
        self.service_container.register(
            ChartService, scope=ServiceScope.SINGLETON)
        chart_service = self.service_container.resolve(ChartService)
        chart_service.initialize()
        logger.info("✓ 图表服务注册完成")

        # WebGPU图表渲染器
        try:
            from optimization.webgpu_chart_renderer import get_webgpu_chart_renderer
            webgpu_renderer = get_webgpu_chart_renderer()
            self.service_container.register_instance(
                'webgpu_chart_renderer', webgpu_renderer)
            logger.info("✓ WebGPU图表渲染器注册完成")
        except ImportError as e:
            logger.warning(f"WebGPU图表渲染器不可用: {e}")
        except Exception as e:
            logger.error(f"WebGPU图表渲染器注册失败: {e}")

        # 分析服务
        self.service_container.register(
            AnalysisService, scope=ServiceScope.SINGLETON)
        analysis_service = self.service_container.resolve(AnalysisService)
        analysis_service.initialize()
        logger.info("✓ 分析服务注册完成")

        # 行业服务
        try:
            self.service_container.register(
                IndustryService, scope=ServiceScope.SINGLETON)
            industry_service = self.service_container.resolve(IndustryService)
            industry_service.initialize()
            logger.info("✓ 行业服务注册完成")
        except Exception as e:
            logger.error(f"❌ 行业服务注册失败: {e}")
            logger.error(traceback.format_exc())

        # AI预测服务
        try:
            self.service_container.register(
                AIPredictionService, scope=ServiceScope.SINGLETON)
            ai_prediction_service = self.service_container.resolve(AIPredictionService)
            logger.info("✓ AI预测服务注册完成")
        except Exception as e:
            logger.error(f"❌ AI预测服务注册失败: {e}")
            logger.error(traceback.format_exc())

    def _check_dependencies(self):
        """检查UnifiedDataManager的依赖项"""
        dependencies = ['config_service']
        for dep in dependencies:
            try:
                # 尝试解析依赖服务
                self.service_container.resolve(dep)
            except Exception as e:
                logger.warning(
                    f"Dependency {dep} not available for UnifiedDataManager: {e}")

    def _initialize_fallback_data_manager(self):
        """初始化失败时的回退策略"""
        logger.info("Initializing fallback data manager")
        try:
            # 尝试使用简化版数据管理器
            from core.data_manager import DataManager
            self.service_container.register_instance(
                'unified_data_manager', DataManager())
            logger.info("✓ 回退数据管理器注册完成")
        except Exception as e:
            logger.error(f"Failed to initialize fallback data manager: {e}")
            # 创建最小可用的数据管理器

            class MinimalDataManager:
                def request_data(self, *args, **kwargs):
                    logger.warning(
                        "Using minimal data manager - limited functionality")
                    return "request_id"
            self.service_container.register_instance(
                'unified_data_manager', MinimalDataManager())
            logger.warning("✓ 最小数据管理器注册完成 - 功能受限")

    def _register_trading_service(self) -> None:
        """注册交易服务"""
        logger.info("注册交易服务...")

        try:
            from .trading_service import TradingService

            self.service_container.register(
                TradingService,
                scope=ServiceScope.SINGLETON,
                factory=lambda: TradingService(
                    event_bus=self.event_bus,
                    config={}
                )
            )

            # 初始化交易服务
            trading_service = self.service_container.resolve(TradingService)
            trading_service.initialize()

            logger.info("✓ 交易服务注册完成")

        except Exception as e:
            logger.error(f"❌ 交易服务注册失败: {e}")
            logger.error(traceback.format_exc())

    def _register_monitoring_services(self) -> None:
        """注册监控服务"""
        logger.info("注册监控服务...")

        try:
            # 1. 注册数据库仓储
            self.service_container.register(
                MetricsRepository, scope=ServiceScope.SINGLETON)
            logger.info("✓ 指标数据库仓储(MetricsRepository)注册完成")

            # 2. 初始化并注册应用性能度量服务
            app_metrics_service = initialize_app_metrics_service(
                self.event_bus)
            self.service_container.register_instance(
                ApplicationMetricsService, app_metrics_service)
            logger.info("✓ 应用性能度量服务(ApplicationMetricsService)初始化完成")

            # 3. 注册系统资源服务
            # 确保直接传递事件总线实例，而不是通过容器解析
            self.service_container.register_factory(
                SystemResourceService,
                lambda: SystemResourceService(self.event_bus)
            )
            resource_service = self.service_container.resolve(
                SystemResourceService)
            resource_service.start()
            logger.info("✓ 系统资源服务(SystemResourceService)启动完成")

            # 4. 注册指标聚合服务
            # 同样使用工厂函数直接传递事件总线
            self.service_container.register_factory(
                MetricsAggregationService,
                lambda: MetricsAggregationService(
                    self.event_bus, self.service_container.resolve(MetricsRepository))
            )
            aggregation_service = self.service_container.resolve(
                MetricsAggregationService)
            aggregation_service.start()
            logger.info("✓ 指标聚合服务(MetricsAggregationService)启动完成")

        except Exception as e:
            logger.error(f"❌ 监控服务注册失败: {e}")
            logger.error(traceback.format_exc())

    def _register_plugin_services(self) -> None:
        """注册插件服务"""
        logger.info("注册插件服务...")

        try:
            self.service_container.register(
                PluginManager, scope=ServiceScope.SINGLETON)
            plugin_manager = self.service_container.resolve(PluginManager)
            plugin_manager.initialize()
            logger.info("✓ 插件管理器服务注册完成")
        except Exception as e:
            logger.error(f"❌ 插件管理器服务注册失败: {e}")
            logger.error(traceback.format_exc())


def bootstrap_services() -> bool:
    """
    引导所有服务的便捷函数

    Returns:
        引导是否成功
    """
    bootstrap = ServiceBootstrap()
    return bootstrap.bootstrap()
