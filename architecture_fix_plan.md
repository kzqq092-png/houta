# FactorWeave-Quant 架构修复计划

## 🚨 紧急修复（立即执行）

### 1. 停止双重初始化

#### 修复文件：`core/services/unified_data_manager.py`

```python
class UnifiedDataManager:
    def __init__(self, service_container: ServiceContainer = None, event_bus: EventBus = None):
        """构造函数只负责依赖装配，不执行业务逻辑"""
        self.service_container = service_container or get_service_container()
        self.event_bus = event_bus or get_event_bus()
        
        # 移除立即初始化调用
        # self._initialize_uni_plugin_manager()  # ❌ 移除这行
        
        # 只声明引用，延迟初始化
        self._uni_plugin_manager = None
        self._is_initialized = False
        
    def initialize(self):
        """延迟初始化，由服务容器控制时机"""
        if self._is_initialized:
            return
            
        # 从服务容器获取已注册的实例，而不是创建新的
        if self.service_container.is_registered(UniPluginDataManager):
            self._uni_plugin_manager = self.service_container.resolve(UniPluginDataManager)
        else:
            logger.warning("UniPluginDataManager未在服务容器中注册")
            
        self._is_initialized = True
```

#### 修复文件：`core/services/uni_plugin_data_manager.py`

```python
class UniPluginDataManager:
    def __init__(self, plugin_manager: PluginManager,
                 data_source_router: DataSourceRouter,
                 tet_pipeline: TETDataPipeline):
        """构造函数只进行依赖装配"""
        self.plugin_center = PluginCenter(plugin_manager)
        self.tet_engine = TETRouterEngine(data_source_router, tet_pipeline)
        self.risk_manager = DataQualityRiskManager()
        self.data_source_router = data_source_router
        
        # 移除立即初始化
        # self._register_plugins_to_router()  # ❌ 移除这行
        
        self._is_initialized = False
        
    def initialize(self) -> None:
        """统一的初始化入口"""
        if self._is_initialized:
            logger.info("UniPluginDataManager已初始化，跳过重复初始化")
            return
            
        logger.info("开始初始化UniPluginDataManager...")
        
        # 现在才执行插件注册
        self._register_plugins_to_router()
        
        self._is_initialized = True
        logger.info("UniPluginDataManager初始化完成")
```

### 2. 修复服务注册顺序

#### 修复文件：`core/services/service_bootstrap.py`

```python
def _register_business_services(self) -> None:
    """注册业务服务 - 修复版本"""
    logger.info("注册业务服务...")
    
    # 1. 先注册底层依赖
    self._register_data_source_router()
    
    # 2. 注册插件管理器（不要立即初始化）
    self._register_plugin_manager()
    
    # 3. 注册UniPluginDataManager（依赖前两者）
    self._register_uni_plugin_data_manager()
    
    # 4. 最后注册UnifiedDataManager（依赖UniPluginDataManager）
    self._register_unified_data_manager()
    
    # 5. 分阶段初始化
    self._initialize_services_in_order()

def _register_unified_data_manager(self):
    """修复后的UnifiedDataManager注册"""
    self.service_container.register_factory(
        UnifiedDataManager,
        lambda: UnifiedDataManager(self.service_container, self.event_bus),
        scope=ServiceScope.SINGLETON
    )
    
    # 不要立即解析，避免触发构造函数中的初始化
    logger.info("UnifiedDataManager注册完成（延迟初始化）")

def _initialize_services_in_order(self):
    """按正确顺序初始化服务"""
    logger.info("开始分阶段初始化服务...")
    
    # 阶段1: 初始化基础组件
    plugin_manager = self.service_container.resolve(PluginManager)
    plugin_manager.initialize()
    
    # 阶段2: 初始化插件数据管理器
    uni_plugin_manager = self.service_container.resolve(UniPluginDataManager)
    uni_plugin_manager.initialize()
    
    # 阶段3: 初始化统一数据管理器
    unified_manager = self.service_container.resolve(UnifiedDataManager)
    unified_manager.initialize()
    
    logger.info("分阶段初始化完成")
```

### 3. 添加单例保护

```python
class SingletonMeta(type):
    """单例元类，确保关键组件只有一个实例"""
    _instances = {}
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class UniPluginDataManager(metaclass=SingletonMeta):
    """应用单例保护的UniPluginDataManager"""
    pass
```

## 🔧 中期架构重构（1-2周）

### 1. Manager类合并计划

#### 数据管理器合并
```
现有: UnifiedDataManager, UniPluginDataManager, EnhancedAssetDatabaseManager
合并为: CoreDataService (单一数据访问入口)
```

#### 插件管理器统一
```
现有: PluginManager, PluginCenter, AsyncPluginDiscovery
合并为: PluginService (统一插件生命周期管理)
```

#### 缓存管理器整合
```
现有: MultiLevelCacheManager, IntelligentCacheManager, CacheManager
合并为: CacheService (统一缓存策略)
```

### 2. 标准服务接口定义

```python
from abc import ABC, abstractmethod

class IService(ABC):
    """标准服务接口"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化服务"""
        pass
        
    @abstractmethod
    def start(self) -> bool:
        """启动服务"""
        pass
        
    @abstractmethod
    def stop(self) -> bool:
        """停止服务"""
        pass
        
    @abstractmethod
    def get_health_status(self) -> dict:
        """获取健康状态"""
        pass

class IDataService(IService):
    """数据服务接口"""
    
    @abstractmethod
    def get_data(self, request: DataRequest) -> DataResponse:
        """获取数据"""
        pass

class IPluginService(IService):
    """插件服务接口"""
    
    @abstractmethod
    def load_plugin(self, plugin_id: str) -> bool:
        """加载插件"""
        pass
        
    @abstractmethod
    def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        pass
```

### 3. 服务生命周期管理

```python
class ServiceLifecycleManager:
    """服务生命周期管理器"""
    
    def __init__(self):
        self.services: List[IService] = []
        self.initialization_order = [
            "ConfigService",
            "CacheService", 
            "DataService",
            "PluginService",
            "UIService"
        ]
    
    def register_service(self, service: IService):
        """注册服务"""
        self.services.append(service)
    
    def initialize_all(self):
        """按顺序初始化所有服务"""
        for service_name in self.initialization_order:
            service = self._find_service(service_name)
            if service:
                service.initialize()
    
    def start_all(self):
        """启动所有服务"""
        for service in self.services:
            service.start()
    
    def stop_all(self):
        """停止所有服务"""
        for service in reversed(self.services):
            service.stop()
```

## 🏗️ 长期架构演进（1-2个月）

### 1. 微服务化改造

#### 服务拆分策略
```
核心服务模块:
├── DataService          # 数据访问服务
├── PluginService        # 插件管理服务  
├── CacheService         # 缓存服务
├── ConfigService        # 配置服务
├── UIService           # UI服务
├── TradingService      # 交易服务
└── MonitoringService   # 监控服务
```

#### 服务间通信
```python
class ServiceBus:
    """服务总线，负责服务间通信"""
    
    def __init__(self):
        self.message_router = MessageRouter()
        self.event_dispatcher = EventDispatcher()
    
    def publish_event(self, event: ServiceEvent):
        """发布服务事件"""
        self.event_dispatcher.dispatch(event)
    
    def send_message(self, target_service: str, message: ServiceMessage):
        """发送服务消息"""
        self.message_router.route(target_service, message)
```

### 2. 配置驱动的服务组装

```yaml
# services.yaml
services:
  data_service:
    class: "core.services.DataService"
    dependencies: ["cache_service", "config_service"]
    initialization_priority: 1
    
  plugin_service:
    class: "core.services.PluginService" 
    dependencies: ["data_service"]
    initialization_priority: 2
    
  ui_service:
    class: "core.services.UIService"
    dependencies: ["data_service", "plugin_service"]
    initialization_priority: 3
```

### 3. 监控和诊断系统

```python
class ServiceDiagnostics:
    """服务诊断系统"""
    
    def check_service_health(self) -> Dict[str, HealthStatus]:
        """检查所有服务健康状态"""
        results = {}
        for service in self.services:
            results[service.name] = service.get_health_status()
        return results
    
    def detect_circular_dependencies(self) -> List[str]:
        """检测循环依赖"""
        dependency_graph = self._build_dependency_graph()
        return self._find_cycles(dependency_graph)
    
    def generate_initialization_report(self) -> str:
        """生成初始化报告"""
        return self._analyze_initialization_sequence()
```

## 🎯 实施建议

### 优先级排序
1. **P0 (立即)**: 修复双重初始化问题
2. **P1 (本周)**: 实施服务生命周期管理
3. **P2 (2周内)**: Manager类合并重构
4. **P3 (1个月)**: 微服务化改造

### 风险控制
1. **渐进式重构**: 一次只重构一个模块
2. **向后兼容**: 保持API兼容性
3. **充分测试**: 每个阶段都要有测试覆盖
4. **回滚机制**: 准备快速回滚方案

### 测试策略
1. **单元测试**: 每个服务的独立测试
2. **集成测试**: 服务间协作测试  
3. **性能测试**: 重构后的性能验证
4. **稳定性测试**: 长时间运行测试
