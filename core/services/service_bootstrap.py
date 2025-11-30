from loguru import logger
"""
服务引导模块

负责在应用程序启动时按正确的顺序注册和初始化所有服务。
"""

import time
from typing import Optional, Set, Type
import traceback
import pandas as pd
from threading import Lock

# 先导入容器和事件总线
from core.containers import ServiceContainer, get_service_container
from core.containers.service_registry import ServiceScope
from core.events import EventBus, get_event_bus

# 然后导入服务类型
from core.services.config_service import ConfigService
from core.services.extension_service import ExtensionService
from core.services.database_service import DatabaseService
from core.services.stock_service import StockService
from core.services.chart_service import ChartService
from core.services.analysis_service import AnalysisService
from core.services.industry_service import IndustryService
from core.services.ai_prediction_service import AIPredictionService
from core.services.unified_data_manager import UnifiedDataManager
from core.plugin_manager import PluginManager
from core.services.uni_plugin_data_manager import UniPluginDataManager

# 增量下载相关服务
from core.services.data_completeness_checker import DataCompletenessChecker
from core.services.incremental_data_analyzer import IncrementalDataAnalyzer
from core.services.incremental_update_recorder import IncrementalUpdateRecorder
from core.services.enhanced_duckdb_data_downloader import EnhancedDuckDBDataDownloader
# # from core.services.error_service import LoguruErrorService  # 暂时注释，让系统先启动

# 最后导入监控服务
from core.metrics.repository import MetricsRepository
from core.metrics.resource_service import SystemResourceService
from core.metrics.app_metrics_service import ApplicationMetricsService, initialize_app_metrics_service
from core.metrics.aggregation_service import MetricsAggregationService

logger = logger


class ServiceBootstrap:
    """
    服务引导类

    负责在应用程序启动时按正确的顺序注册和初始化所有服务。
    包含初始化防护机制，防止重复服务创建。
    """

    # 类级别的初始化跟踪
    _initialized_services: Set[Type] = set()
    _registration_attempts: dict = {}
    _initialization_lock = Lock()

    def __init__(self, service_container: Optional[ServiceContainer] = None):
        """
        初始化服务引导器

        Args:
            service_container: 服务容器，如果为None则使用全局容器
        """
        self.service_container = service_container or get_service_container()
        self.event_bus = get_event_bus()

        # 实例级别的跟踪
        self._instance_registered_services: Set[Type] = set()
        self._duplicate_attempts = 0

    def _is_service_registered(self, service_type: Type) -> bool:
        """检查服务是否已注册"""
        return service_type in self._instance_registered_services or self.service_container.is_registered(service_type)

    def _mark_service_registered(self, service_type: Type):
        """标记服务已注册"""
        self._instance_registered_services.add(service_type)
        logger.debug(f"服务已标记为已注册: {service_type.__name__}")

    def _safe_register_service(self, service_type: Type, implementation=None, scope=ServiceScope.SINGLETON, name="") -> bool:
        """
        安全注册服务，包含重复检测和防护

        Args:
            service_type: 服务类型
            implementation: 服务实现
            scope: 服务作用域
            name: 服务名称

        Returns:
            是否成功注册（False表示已存在或注册失败）
        """
        with self._initialization_lock:
            service_name = name or service_type.__name__

            # 检查是否已在容器中注册
            if self.service_container.is_registered(service_type):
                self._duplicate_attempts += 1

                # 记录重复注册尝试
                if service_type not in self._registration_attempts:
                    self._registration_attempts[service_type] = 0
                self._registration_attempts[service_type] += 1

                logger.warning(
                    f"🔄 Service {service_name} already registered in container. "
                    f"Duplicate attempt #{self._registration_attempts[service_type]}. "
                    f"Stack trace: {traceback.format_stack()[-3:-1]}"
                )
                return False

            # 检查是否已在类级别跟踪中
            if service_type in self._initialized_services:
                self._duplicate_attempts += 1
                logger.warning(
                    f"🔄 Service {service_name} already in initialized services list. "
                    f"Skipping registration."
                )
                return False

            # 检查是否已在实例级别跟踪中
            if service_type in self._instance_registered_services:
                self._duplicate_attempts += 1
                logger.warning(
                    f"🔄 Service {service_name} already registered in this bootstrap instance. "
                    f"Skipping registration."
                )
                return False

            try:
                # 执行实际注册
                if implementation:
                    self.service_container.register(service_type, implementation, scope, name)
                else:
                    self.service_container.register(service_type, scope=scope, name=name)

                # 记录成功注册
                self._initialized_services.add(service_type)
                self._instance_registered_services.add(service_type)

                logger.info(f"Service {service_name} registered successfully")
                return True

            except Exception as e:
                logger.error(
                    f"[ERROR] Failed to register service {service_name}: {e}\n"
                    f"Stack trace: {traceback.format_exc()}"
                )
                return False

    def bootstrap(self) -> bool:
        """
        引导所有服务

        Returns:
            引导是否成功
        """
        try:
            logger.info("[BOOTSTRAP] Starting service bootstrap with duplicate detection...")

            # 1. 注册核心服务
            self._register_core_services()

            # 2. 注册业务服务（包含UnifiedDataManager）
            self._register_business_services()

            # 2.5. 注册增量下载服务（在业务服务之后，插件服务之前）
            self._register_incremental_services()

            # 3. 注册插件服务（在UnifiedDataManager之后）
            self._register_plugin_services()

            # 4. 注册交易服务
            self._register_trading_service()

            # 5. 注册监控服务
            self._register_monitoring_services()

            # 6. 注册高级服务（GPU加速等）
            self._register_advanced_services()

            # 7. 执行插件发现和注册（在所有服务注册完成后）
            self._post_initialization_plugin_discovery()

            # 8. 输出重复检测报告
            self._report_duplicate_attempts()

            logger.info("Service bootstrap completed successfully")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 服务引导失败: {e}")
            logger.error(traceback.format_exc())
            return False

    def _report_duplicate_attempts(self) -> None:
        """报告重复初始化尝试统计"""
        if self._duplicate_attempts > 0 or self._registration_attempts:
            logger.warning(f"📊 Duplicate Registration Detection Report:")
            logger.warning(f"   Total duplicate attempts prevented: {self._duplicate_attempts}")

            if self._registration_attempts:
                logger.warning(f"   Services with multiple registration attempts:")
                for service_type, count in self._registration_attempts.items():
                    logger.warning(f"     - {service_type.__name__}: {count} attempts")

            logger.warning(f"   Successfully registered services: {len(self._instance_registered_services)}")
        else:
            logger.info("[INFO] No duplicate service registration attempts detected")

    def _register_core_services(self) -> None:
        """注册核心服务"""
        logger.info("注册核心服务...")

        # 注册事件总线 (EventBus)
        self.service_container.register_instance(EventBus, self.event_bus)
        # 确保也注册具体类型，以便能够通过类型注入
        self.service_container.register_instance(
            type(self.event_bus), self.event_bus)
        logger.info("事件总线注册完成")

        # 注册统一配置服务
        config_service = ConfigService(config_file='config/config.json', use_sqlite=True)
        config_service.initialize()
        self.service_container.register_instance(ConfigService, config_service)
        # 也按名称注册，方便通过名称访问
        self.service_container.register_instance(ConfigService, config_service, name='config_service')

        # 为了兼容性，也注册为ConfigManager类型
        from utils.config_manager import ConfigManager
        self.service_container.register_instance(ConfigManager, config_service)
        logger.info("统一配置服务注册完成（类型 + 名称 'config_service'）")

        # 注册扩展服务 (ExtensionService)
        extension_service = ExtensionService()
        extension_service.initialize()
        self.service_container.register_instance(ExtensionService, extension_service)
        logger.info("扩展服务注册完成")

        # 日志服务现在由纯Loguru系统全局管理，无需注册到容器
        # log_manager = LogManager()
        # self.service_container.register_instance(LogManager, log_manager)
        logger.info("纯Loguru日志系统已全局可用")

        # 注册基于Loguru的错误处理服务 (暂时注释)
        # error_service = LoguruErrorService()
        # self.service_container.register_instance(LoguruErrorService, error_service)
        logger.info("Loguru日志系统运行正常，错误处理集成待完善")

    def _register_business_services(self) -> None:
        """注册业务服务"""
        logger.info("注册业务服务...")

        # 添加依赖检查
        self._check_dependencies()

        # 先注册DataSourceRouter（TET模式依赖）
        logger.info("注册数据源路由器...")
        try:
            from ..data_source_router import DataSourceRouter
            self.service_container.register_factory(
                DataSourceRouter,
                lambda: DataSourceRouter(),
                scope=ServiceScope.SINGLETON
            )
            router = self.service_container.resolve(DataSourceRouter)
            logger.info("数据源路由器注册完成")
        except Exception as e:
            logger.warning(f" 数据源路由器注册失败: {e}")

        # 注册数据库服务（在其他业务服务之前）
        logger.info("注册数据库服务...")
        try:
            if not self._is_service_registered(DatabaseService):
                self.service_container.register(
                    DatabaseService,
                    scope=ServiceScope.SINGLETON,
                    factory=lambda: DatabaseService(
                        service_container=self.service_container
                    )
                )
            database_service = self.service_container.resolve(DatabaseService)
            database_service.initialize()
            logger.info("✅ 数据库服务注册完成")
        except Exception as e:
            logger.error(f"❌ 数据库服务注册失败: {e}")
            logger.error(traceback.format_exc())

        # 然后注册UnifiedDataManager（使用安全注册）
        if not self._safe_register_service(
            UnifiedDataManager,
            lambda: UnifiedDataManager(self.service_container, self.event_bus),
            ServiceScope.SINGLETON
        ):
            logger.warning("UnifiedDataManager already registered, skipping...")

        # 延迟初始化模式 - 不要立即解析以避免触发构造函数初始化

        # 安全注册完成，进行备份检查
        try:
            # 验证注册是否成功
            if self.service_container.is_registered(UnifiedDataManager):
                logger.info("UnifiedDataManager registration verified")

            logger.info("统一数据管理器注册完成（延迟初始化模式）")

        except Exception as e:

            logger.error(f"Failed to initialize UnifiedDataManager: {e}")

            # 提供回退机制

            self._initialize_fallback_data_manager()

        #  股票服务 - 使用工厂方法传递服务容器（延迟初始化）
        self.service_container.register_factory(
            StockService,
            lambda: StockService(service_container=self.service_container),
            scope=ServiceScope.SINGLETON
        )
        # 注意：StockService的初始化将在分阶段初始化中进行，以确保UnifiedDataManager已经初始化
        logger.info("股票服务注册完成（延迟初始化）")

        # 图表服务

        if not self._is_service_registered(ChartService):
            self.service_container.register(
                ChartService, scope=ServiceScope.SINGLETON)
        chart_service = self.service_container.resolve(ChartService)
        chart_service.initialize()
        logger.info("图表服务注册完成")

        # WebGPU图表渲染器
        try:
            from optimization.webgpu_chart_renderer import get_webgpu_chart_renderer, WebGPUChartRenderer
            webgpu_renderer = get_webgpu_chart_renderer()
            self.service_container.register_instance(
                WebGPUChartRenderer, webgpu_renderer)
            logger.info("WebGPU图表渲染器注册完成")
        except ImportError as e:
            logger.warning(f"WebGPU图表渲染器不可用: {e}")
        except Exception as e:
            logger.error(f"WebGPU图表渲染器注册失败: {e}")

        # 分析服务

        if not self._is_service_registered(AnalysisService):
            self.service_container.register(
                AnalysisService, scope=ServiceScope.SINGLETON)
        analysis_service = self.service_container.resolve(AnalysisService)
        analysis_service.initialize()
        logger.info("分析服务注册完成")

        # 行业服务
        try:

            if not self._is_service_registered(IndustryService):
                self.service_container.register(
                    IndustryService, scope=ServiceScope.SINGLETON)
            industry_service = self.service_container.resolve(IndustryService)
            industry_service.initialize()
            logger.info("行业服务注册完成")
        except Exception as e:
            logger.error(f" 行业服务注册失败: {e}")
            logger.error(traceback.format_exc())

        # AI预测服务
        try:

            if not self._is_service_registered(AIPredictionService):
                self.service_container.register(
                    AIPredictionService, scope=ServiceScope.SINGLETON)
            ai_prediction_service = self.service_container.resolve(AIPredictionService)
            logger.info("AI预测服务注册完成")
        except Exception as e:
            logger.error(f" AI预测服务注册失败: {e}")
            logger.error(traceback.format_exc())

        # 模型训练服务
        try:
            from .model_training_service import ModelTrainingService
            if not self._is_service_registered(ModelTrainingService):
                self.service_container.register(
                    ModelTrainingService, scope=ServiceScope.SINGLETON)
            model_training_service = self.service_container.resolve(ModelTrainingService)
            model_training_service.initialize()
            logger.info("模型训练服务注册完成")
        except Exception as e:
            logger.error(f" 模型训练服务注册失败: {e}")
            logger.error(traceback.format_exc())

        # 预测跟踪服务
        try:
            from .prediction_tracking_service import PredictionTrackingService
            if not self._is_service_registered(PredictionTrackingService):
                self.service_container.register(
                    PredictionTrackingService, scope=ServiceScope.SINGLETON)
            prediction_tracking_service = self.service_container.resolve(PredictionTrackingService)
            prediction_tracking_service.initialize()
            logger.info("预测跟踪服务注册完成")
        except Exception as e:
            logger.error(f" 预测跟踪服务注册失败: {e}")
            logger.error(traceback.format_exc())

        # 资产服务（多资产类型支持）
        try:
            from .asset_service import AssetService
            self.service_container.register_factory(
                AssetService,
                lambda: AssetService(
                    unified_data_manager=self.service_container.resolve(UnifiedDataManager),
                    stock_service=self.service_container.resolve(StockService),
                    service_container=self.service_container
                ),
                scope=ServiceScope.SINGLETON
            )
            asset_service = self.service_container.resolve(AssetService)
            logger.info("资产服务注册完成")
        except Exception as e:
            logger.error(f" 资产服务注册失败: {e}")
            logger.error(traceback.format_exc())

            # ✅ 情绪数据服务和K线情绪分析服务已删除（被热点分析功能取代）
            # 相关文件已清理：sentiment_data_service.py、kline_sentiment_analyzer.py
            # 相关UI组件已删除：enhanced_kline_sentiment_tab.py、sentiment_overview_widget.py
            logger.debug("情绪数据服务和K线情绪分析服务已移除（功能已整合到热点分析）")

            # 板块资金流服务
        try:
            logger.info("开始注册板块资金流服务...")
            from .sector_fund_flow_service import SectorFundFlowService, SectorFlowConfig
            logger.info("板块资金流服务模块导入成功")

            # 创建配置
            logger.info("创建板块资金流服务配置...")
            sector_config = SectorFlowConfig(
                cache_duration_minutes=5,
                auto_refresh_interval_minutes=10,
                enable_auto_refresh=True
            )
            logger.info("板块资金流服务配置创建完成")

            def create_sector_flow_service():
                logger.info("开始创建板块资金流服务实例...")
                start_time = time.time()

                # 获取数据管理器
                logger.info("尝试获取统一数据管理器...")
                data_manager = None
                try:
                    if self.service_container.is_registered(UnifiedDataManager):
                        data_manager = self.service_container.resolve(UnifiedDataManager)
                        logger.info("统一数据管理器获取成功")
                    else:
                        logger.warning("统一数据管理器未注册")
                except Exception as e:
                    logger.warning(f" 统一数据管理器获取失败: {e}")

                # 创建服务
                logger.info("创建板块资金流服务实例...")
                service = SectorFundFlowService(
                    data_manager=data_manager,
                    config=sector_config
                )

                end_time = time.time()
                logger.info(f" 板块资金流服务实例创建完成，耗时: {(end_time - start_time):.2f}秒")
                return service

            # 注册服务工厂
            self.service_container.register_factory(
                SectorFundFlowService,
                create_sector_flow_service,
                scope=ServiceScope.SINGLETON
            )

            logger.info("板块资金流服务注册完成")
        except Exception as e:
            logger.error(f" 板块资金流服务注册失败: {e}")
            logger.error(traceback.format_exc())

        # 在分阶段初始化之前，先注册PluginManager和UniPluginDataManager
        self._register_plugin_manager_early()
        self._register_uni_plugin_data_manager()

        # 分阶段初始化服务
        self._initialize_services_in_order()

    def _initialize_services_in_order(self):
        """按正确顺序初始化服务，避免循环依赖"""
        logger.info("开始分阶段初始化服务...")

        try:
            # 阶段1: 初始化插件管理器
            if self.service_container.is_registered(PluginManager):
                plugin_manager = self.service_container.resolve(PluginManager)
                if hasattr(plugin_manager, 'initialize'):
                    plugin_manager.initialize()
                logger.info("插件管理器初始化完成")

            # 阶段2: 初始化UniPluginDataManager
            if self.service_container.is_registered(UniPluginDataManager):
                uni_plugin_manager = self.service_container.resolve(UniPluginDataManager)
                if hasattr(uni_plugin_manager, 'initialize'):
                    uni_plugin_manager.initialize()
                logger.info("UniPluginDataManager初始化完成")

            # 阶段3: 初始化UnifiedDataManager
            if self.service_container.is_registered(UnifiedDataManager):
                unified_manager = self.service_container.resolve(UnifiedDataManager)
                if hasattr(unified_manager, 'initialize'):
                    unified_manager.initialize()
                logger.info("UnifiedDataManager初始化完成")

            # 阶段4: 初始化依赖UnifiedDataManager的服务
            from core.services.stock_service import StockService
            if self.service_container.is_registered(StockService):
                stock_service = self.service_container.resolve(StockService)
                if hasattr(stock_service, 'initialize'):
                    stock_service.initialize()
                logger.info("StockService初始化完成")

            logger.info("分阶段初始化完成")

        except Exception as e:
            logger.error(f"[ERROR] 分阶段初始化失败: {e}")
            raise

    def _check_dependencies(self):
        """检查UnifiedDataManager的依赖项"""
        from .config_service import ConfigService

        dependencies = {
            'config_service': ConfigService
        }

        for dep_name, dep_class in dependencies.items():
            try:
                # 尝试解析依赖服务
                self.service_container.resolve(dep_class)
                logger.debug(f"Dependency {dep_name} is available")
            except Exception as e:
                logger.warning(
                    f"Dependency {dep_name} not available for UnifiedDataManager: {e}")

    def _initialize_fallback_data_manager(self):
        """初始化失败时的回退策略"""
        logger.info("Initializing fallback data manager")
        try:
            # 尝试使用UnifiedDataManager作为回退
            fallback_manager = UnifiedDataManager()
            self.service_container.register_instance(
                type(fallback_manager), fallback_manager, name='unified_data_manager')
            logger.info("回退数据管理器注册完成")
        except Exception as e:
            logger.error(f"Failed to initialize fallback data manager: {e}")
            # 创建最小可用的数据管理器

            # 使用UnifiedDataManager作为最终回退
            minimal_manager = UnifiedDataManager()
            self.service_container.register_instance(
                type(minimal_manager), minimal_manager, name='unified_data_manager')
            logger.warning("最小数据管理器注册完成 - 功能受限")

    def _register_trading_service(self) -> None:
        """注册交易服务"""
        logger.info("注册交易服务...")

        try:
            # 注册新的交易引擎
            from ..trading_engine import TradingEngine, initialize_trading_engine

            trading_engine = initialize_trading_engine(
                service_container=self.service_container,
                event_bus=self.event_bus
            )

            self.service_container.register_instance(TradingEngine, trading_engine)
            logger.info("交易引擎注册完成")

            # 兼容性：也注册为TradingService
            try:
                from .trading_service import TradingService

                if not self._is_service_registered(TradingService):
                    self.service_container.register(
                        TradingService,
                        scope=ServiceScope.SINGLETON,
                        factory=lambda: TradingService(
                            service_container=self.service_container
                        )
                    )

                # 初始化交易服务
                trading_service = self.service_container.resolve(TradingService)
                trading_service.initialize()
                logger.info("交易服务（兼容性）注册完成")

            except Exception as e:
                logger.warning(f" 交易服务兼容性注册失败: {e}")

            # 注册TradingController
            try:
                from ..trading_controller import TradingController
                # 移除LogManager依赖，TradingController现在直接使用Loguru

                self.service_container.register_factory(
                    TradingController,
                    lambda: TradingController(
                        service_container=self.service_container
                        # log_manager=LogManager()  # 已移除，使用纯Loguru
                    ),
                    scope=ServiceScope.SINGLETON
                )
                logger.info("交易控制器注册完成")

            except Exception as e:
                logger.warning(f" 交易控制器注册失败: {e}")

            # 注册StrategyService
            try:
                from .strategy_service import StrategyService

                if not self._is_service_registered(StrategyService):
                    self.service_container.register(
                        StrategyService,
                        scope=ServiceScope.SINGLETON,
                        factory=lambda: StrategyService(
                            event_bus=self.event_bus,
                            config={}
                        )
                    )

                # 初始化策略服务
                strategy_service = self.service_container.resolve(StrategyService)
                strategy_service.initialize()
                logger.info("策略服务注册完成")

            except Exception as e:
                logger.warning(f" 策略服务注册失败: {e}")

        except Exception as e:
            logger.error(f" 交易服务注册失败: {e}")
            logger.error(traceback.format_exc())

    def _register_monitoring_services(self) -> None:
        """注册监控服务"""
        logger.info("注册监控服务...")

        try:
            # 1. 注册数据库仓储
            self.service_container.register(
                MetricsRepository, scope=ServiceScope.SINGLETON)
            logger.info("指标数据库仓储(MetricsRepository)注册完成")

            # 2. 初始化并注册应用性能度量服务
            app_metrics_service = initialize_app_metrics_service(
                self.event_bus)
            self.service_container.register_instance(
                ApplicationMetricsService, app_metrics_service)
            logger.info("应用性能度量服务(ApplicationMetricsService)初始化完成")

            # 3. 注册系统资源服务
            # 确保直接传递事件总线实例，而不是通过容器解析
            self.service_container.register_factory(
                SystemResourceService,
                lambda: SystemResourceService(self.event_bus)
            )
            resource_service = self.service_container.resolve(
                SystemResourceService)
            resource_service.start()
            logger.info("系统资源服务(SystemResourceService)启动完成")

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
            logger.info("指标聚合服务(MetricsAggregationService)启动完成")

            # 5. 新增：注册性能数据桥接器
            try:
                from core.services.performance_data_bridge import initialize_performance_bridge, PerformanceDataBridge
                performance_bridge = initialize_performance_bridge(auto_start=True)
                self.service_container.register_instance(
                    PerformanceDataBridge, performance_bridge)
                logger.info("性能数据桥接器(PerformanceDataBridge)初始化完成")
            except Exception as e:
                logger.error(f"性能数据桥接器初始化失败: {e}")

            #  新增：注册告警事件处理器
            try:
                from core.services.alert_event_handler import register_alert_handlers
                register_alert_handlers(self.event_bus)
                logger.info("告警事件处理器注册完成")
            except Exception as e:
                logger.error(f" 告警事件处理器注册失败: {e}")
                logger.error(traceback.format_exc())

            #  新增：确保告警数据库已初始化
            try:
                from db.models.alert_config_models import get_alert_config_database
                alert_db = get_alert_config_database()
                logger.info("告警数据库初始化完成")
            except Exception as e:
                logger.error(f" 告警数据库初始化失败: {e}")
                logger.error(traceback.format_exc())

            #  新增：注册并启动告警规则引擎服务
            try:
                from .alert_rule_engine import AlertRuleEngine, initialize_alert_rule_engine
                self.service_container.register(
                    AlertRuleEngine,
                    scope=ServiceScope.SINGLETON
                )

                # 自动初始化并启动告警引擎
                alert_engine = initialize_alert_rule_engine(self.event_bus)
                alert_engine.start()
                logger.info("告警规则引擎服务注册并启动完成")
            except Exception as e:
                logger.error(f" 告警规则引擎服务注册失败: {e}")

            #  新增：注册并启动告警规则热加载服务
            try:
                from .alert_rule_hot_loader import AlertRuleHotLoader, initialize_alert_rule_hot_loader
                self.service_container.register(
                    AlertRuleHotLoader,
                    scope=ServiceScope.SINGLETON
                )

                # 自动初始化并启动热加载服务
                hot_loader = initialize_alert_rule_hot_loader(check_interval=5)
                hot_loader.start()

                # 将引擎作为热加载回调
                try:
                    alert_engine = initialize_alert_rule_engine(self.event_bus)
                    hot_loader.add_update_callback(alert_engine.reload_rules_sync)
                    logger.info("告警引擎与热加载服务关联完成")
                except:
                    pass

                logger.info("告警规则热加载服务注册并启动完成")
            except Exception as e:
                logger.error(f" 告警规则热加载服务注册失败: {e}")

        except Exception as e:
            logger.error(f" 监控服务注册失败: {e}")
            logger.error(traceback.format_exc())

    def _register_incremental_services(self) -> None:
        """注册增量下载相关服务"""
        logger.info("注册增量下载服务...")

        try:
            # 获取必要的依赖服务
            uni_plugin_manager = self.service_container.resolve(UniPluginDataManager)
            unified_data_manager = self.service_container.resolve(UnifiedDataManager)
            event_bus = self.event_bus

            # 1. 注册数据完整性检查器
            logger.info("注册数据完整性检查器...")
            from ..services.data_completeness_checker import DataCompletenessChecker
            completeness_checker = DataCompletenessChecker(
                db_manager=unified_data_manager.duckdb_manager,
                event_bus=event_bus,
                db_path="data/factorweave_system.sqlite"
            )
            self.service_container.register_instance(
                DataCompletenessChecker,
                completeness_checker
            )
            logger.info("数据完整性检查器注册完成")

            # 2. 注册增量数据分析仪
            logger.info("注册增量数据分析仪...")
            from ..services.incremental_data_analyzer import IncrementalDataAnalyzer
            incremental_analyzer = IncrementalDataAnalyzer(
                db_manager=unified_data_manager.duckdb_manager,
                event_bus=event_bus,
                completeness_checker=completeness_checker
            )
            self.service_container.register_instance(
                IncrementalDataAnalyzer,
                incremental_analyzer
            )
            logger.info("增量数据分析仪注册完成")

            # 3. 注册增量更新记录器
            logger.info("注册增量更新记录器...")
            from ..services.incremental_update_recorder import IncrementalUpdateRecorder
            update_recorder = IncrementalUpdateRecorder(
                db_manager=unified_data_manager.duckdb_manager,
                event_bus=event_bus,
                db_path="data/factorweave_system.sqlite"
            )
            self.service_container.register_instance(
                IncrementalUpdateRecorder,
                update_recorder
            )
            logger.info("增量更新记录器注册完成")

            # 4. 注册增强的DuckDB数据下载器
            logger.info("注册增强的DuckDB数据下载器...")
            from ..services.enhanced_duckdb_data_downloader import EnhancedDuckDBDataDownloader
            enhanced_downloader = EnhancedDuckDBDataDownloader(
                uni_plugin_manager=uni_plugin_manager,
                tet_pipeline=unified_data_manager.tet_pipeline,
                data_source_router=unified_data_manager.data_source_router,
                incremental_analyzer=incremental_analyzer,
                completeness_checker=completeness_checker,
                update_recorder=update_recorder
            )
            self.service_container.register_instance(
                EnhancedDuckDBDataDownloader,
                enhanced_downloader
            )
            logger.info("增强的DuckDB数据下载器注册完成")

            logger.info("所有增量下载服务注册完成")

            # 5. 注册增量更新调度器
            logger.info("注册增量更新调度器...")
            from ..services.incremental_update_scheduler import IncrementalUpdateScheduler
            scheduler = IncrementalUpdateScheduler()
            self.service_container.register_instance(
                IncrementalUpdateScheduler,
                scheduler
            )
            logger.info("增量更新调度器注册完成")

            # 6. 注册断点续传管理器
            logger.info("注册断点续传管理器...")
            from ..services.breakpoint_resume_manager import BreakpointResumeManager
            resume_manager = BreakpointResumeManager()
            self.service_container.register_instance(
                BreakpointResumeManager,
                resume_manager
            )
            logger.info("断点续传管理器注册完成")

        except Exception as e:
            logger.error(f" 增量下载服务注册失败: {e}")
            logger.error(traceback.format_exc())

    def _register_plugin_services(self) -> None:
        """注册插件服务"""
        logger.info("注册插件服务...")

        try:
            # PluginManager和UniPluginDataManager已经在业务服务阶段注册，这里只需要初始化
            if self.service_container.is_registered(PluginManager):
                plugin_manager = self.service_container.resolve(PluginManager)
                plugin_manager.initialize()
                logger.info("插件管理器初始化完成")
            else:
                logger.warning("PluginManager未注册，跳过初始化")

            # ✅ 情绪数据服务已删除（功能已整合到热点分析）
            logger.debug("情绪数据服务初始化已跳过（服务已移除）")

        except Exception as e:
            logger.error(f" 插件管理器服务注册失败: {e}")
            logger.error(traceback.format_exc())

    def _post_initialization_plugin_discovery(self) -> None:
        """
        在所有服务注册完成后执行异步插件发现和注册
        """
        logger.info("启动异步插件发现和注册...")
        try:
            # 导入异步插件发现服务
            from .async_plugin_discovery import get_async_plugin_discovery_service

            # 获取插件管理器和数据管理器
            plugin_manager = self.service_container.resolve(PluginManager)
            data_manager = None
            if self.service_container.is_registered(UnifiedDataManager):
                data_manager = self.service_container.resolve(UnifiedDataManager)

            # 获取异步插件发现服务
            async_discovery = get_async_plugin_discovery_service()

            # 连接信号处理进度更新
            async_discovery.progress_updated.connect(self._on_plugin_discovery_progress)
            async_discovery.discovery_completed.connect(self._on_plugin_discovery_completed)
            async_discovery.discovery_failed.connect(self._on_plugin_discovery_failed)

            # 启动异步插件发现
            async_discovery.start_discovery(plugin_manager, data_manager)
            logger.info("异步插件发现服务已启动")

        except Exception as e:
            logger.error(f" 启动异步插件发现失败: {e}")
            logger.error(traceback.format_exc())

            # 降级到同步模式
            logger.info("降级到同步插件发现模式...")
            self._fallback_sync_plugin_discovery()

    def _on_plugin_discovery_progress(self, progress: int, message: str):
        """插件发现进度更新"""
        logger.info(f"插件发现进度: {progress}% - {message}")

    def _on_plugin_discovery_completed(self, result: dict):
        """插件发现完成"""
        logger.info("异步插件发现和注册完成")
        logger.info(f"发现结果: {result}")

    def _on_plugin_discovery_failed(self, error_msg: str):
        """插件发现失败"""
        logger.error(f" 异步插件发现失败: {error_msg}")
        # 可以选择降级到同步模式
        logger.info("尝试降级到同步插件发现模式...")
        self._fallback_sync_plugin_discovery()

    def _fallback_sync_plugin_discovery(self):
        """降级到同步插件发现模式"""
        try:
            logger.info("执行同步插件发现...")

            # 1. 插件管理器插件发现
            plugin_manager = self.service_container.resolve(PluginManager)
            plugin_manager.discover_and_register_plugins()
            logger.info("插件管理器插件发现完成")

            # 2. 统一数据管理器数据源插件发现
            if self.service_container.is_registered(UnifiedDataManager):
                data_manager = self.service_container.resolve(UnifiedDataManager)
                if hasattr(data_manager, 'discover_and_register_data_source_plugins'):
                    data_manager.discover_and_register_data_source_plugins()
                    logger.info("数据源插件发现和注册完成")
                else:
                    logger.warning("UnifiedDataManager不支持插件发现")
            else:
                logger.warning("UnifiedDataManager未注册")

        except Exception as e:
            logger.error(f" 同步插件发现失败: {e}")
            logger.error(traceback.format_exc())

    def _register_advanced_services(self) -> None:
        """注册高级服务（GPU加速、分布式等）"""
        logger.info("注册高级服务...")

        # GPU加速服务
        try:
            from .gpu_acceleration_manager import GPUAccelerationManager

            def create_gpu_service():
                """创建GPU加速服务实例"""
                return GPUAccelerationManager()

            self.service_container.register_factory(
                GPUAccelerationManager,
                create_gpu_service,
                scope=ServiceScope.SINGLETON
            )

            # 立即解析以触发初始化
            gpu_service = self.service_container.resolve(GPUAccelerationManager)
            logger.info("GPU加速服务注册完成")

        except ImportError:
            logger.warning("GPU加速模块不可用，跳过注册")
        except Exception as e:
            logger.error(f" GPU加速服务注册失败: {e}")
            logger.error(traceback.format_exc())
        
        # ✅ 分布式服务
        try:
            from .distributed_service import DistributedService
            
            def create_distributed_service():
                """创建分布式服务实例"""
                service = DistributedService()
                # 自动启动服务
                service.start_service()
                logger.info("分布式服务已启动")
                return service
            
            # 按类型注册（主注册）
            self.service_container.register_factory(
                DistributedService,
                create_distributed_service,
                scope=ServiceScope.SINGLETON
            )
            
            # 添加名称注册，方便UI按名称访问
            self.service_container.register_factory(
                DistributedService,
                create_distributed_service,
                scope=ServiceScope.SINGLETON,
                name='distributed_service'
            )
            
            logger.info("✅ 分布式服务注册完成（类型 + 名称 'distributed_service'）")
            
        except ImportError as e:
            logger.warning(f"分布式服务模块不可用，跳过注册: {e}")
        except Exception as e:
            logger.error(f"❌ 分布式服务注册失败: {e}")
            logger.error(traceback.format_exc())

    def _register_plugin_manager_early(self) -> None:
        """提前注册插件管理器，以便在分阶段初始化时可用"""
        logger.info("提前注册插件管理器...")

        try:
            # 注册插件管理器，传递必要的依赖项
            from utils.config_manager import ConfigManager

            # 获取或创建ConfigManager
            config_manager = None
            if self.service_container.is_registered(ConfigManager):
                config_manager = self.service_container.resolve(ConfigManager)
            else:
                config_manager = ConfigManager()

            # 使用安全注册方法注册PluginManager
            if not self._safe_register_service(
                PluginManager,
                lambda: PluginManager(
                    plugin_dir="plugins",
                    main_window=None,  # 稍后在主窗口创建时设置
                    data_manager=None,  # 稍后设置
                    config_manager=config_manager
                ),
                ServiceScope.SINGLETON
            ):
                logger.warning("PluginManager already registered, using existing instance...")

            plugin_manager = self.service_container.resolve(PluginManager)

            # 将UnifiedDataManager连接到插件管理器
            if self.service_container.is_registered(UnifiedDataManager):
                data_manager = self.service_container.resolve(UnifiedDataManager)
                plugin_manager.data_manager = data_manager
                logger.info("插件管理器已连接到UnifiedDataManager")

            logger.info("插件管理器提前注册完成")

        except Exception as e:
            logger.error(f"插件管理器提前注册失败: {e}")
            logger.error(traceback.format_exc())

    def _register_uni_plugin_data_manager(self) -> None:
        """注册统一插件数据管理器"""
        logger.info("注册统一插件数据管理器...")

        try:
            # 获取必需的依赖服务
            plugin_manager = self.service_container.resolve(PluginManager)

            # 获取数据源路由器
            from core.data_source_router import DataSourceRouter
            data_source_router = None
            if self.service_container.is_registered(DataSourceRouter):
                data_source_router = self.service_container.resolve(DataSourceRouter)
            else:
                # 如果未注册，创建新实例
                data_source_router = DataSourceRouter()
                self.service_container.register_instance(
                    DataSourceRouter, data_source_router)

            # 获取TET数据管道
            from core.tet_data_pipeline import TETDataPipeline
            tet_pipeline = TETDataPipeline(data_source_router)

            # 注册统一插件数据管理器工厂
            def create_uni_plugin_data_manager():
                manager = UniPluginDataManager(
                    plugin_manager=plugin_manager,
                    data_source_router=data_source_router,
                    tet_pipeline=tet_pipeline
                )
                # 初始化管理器
                manager.initialize()
                return manager

            self.service_container.register_factory(
                UniPluginDataManager,
                create_uni_plugin_data_manager,
                scope=ServiceScope.SINGLETON
            )

            # 设置全局实例
            uni_manager = self.service_container.resolve(UniPluginDataManager)
            from core.services.uni_plugin_data_manager import set_uni_plugin_data_manager
            set_uni_plugin_data_manager(uni_manager)

            logger.info("统一插件数据管理器注册完成")

        except Exception as e:
            logger.error(f"统一插件数据管理器注册失败: {e}")
            logger.error(traceback.format_exc())


def bootstrap_services() -> bool:
    """
    引导所有服务的便捷函数

    Returns:
        引导是否成功
    """
    # 使用全局服务容器确保一致性
    from core.containers.service_container import get_service_container
    container = get_service_container()
    bootstrap = ServiceBootstrap(container)
    return bootstrap.bootstrap()
