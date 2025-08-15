# HIkyuu框架插件化与TET集成重构方案

## 📋 方案概述

本方案旨在将HIkyuu框架从系统强依赖转换为插件化引入，同时全面接入TET框架，实现更灵活、可扩展的架构设计。

**重构目标**:
- ✅ 消除HIkyuu框架的强依赖
- ✅ 实现HIkyuu功能的插件化
- ✅ 全面接入TET框架
- ✅ 保持现有功能完整性
- ✅ 提升系统扩展性和可维护性

---

## 🔍 当前HIkyuu强依赖分析

### 1. 强依赖点统计

通过代码分析发现，HIkyuu框架在以下文件中存在强依赖：

#### 1.1 核心数据层 (7个文件)
- `core/hikyuu_source.py` - HIkyuu数据源
- `core/data/hikyuu_data_manager.py` - HIkyuu数据管理器
- `core/data_manager.py` - 数据管理器主文件
- `core/trading_system.py` - 交易系统
- `core/services/stock_service.py` - 股票服务

#### 1.2 策略和信号系统 (8个文件)
- `strategies/adaptive_strategy.py` - 自适应策略
- `core/signal/base.py` - 信号基类
- `core/signal/enhanced.py` - 增强信号
- `core/signal/factory.py` - 信号工厂
- `core/money/base.py` - 资金管理基类
- `core/stop_loss.py` - 止损策略
- `core/take_profit.py` - 止盈策略
- `core/system_condition.py` - 系统条件

#### 1.3 技术指标系统 (5个文件)
- `features/basic_indicators.py` - 基础指标
- `analysis/technical_analysis.py` - 技术分析
- `gui/widgets/analysis_widget.py` - 分析控件
- `components/stock_screener.py` - 股票筛选器
- `gui/widgets/analysis_tabs/professional_sentiment_tab.py` - 情绪分析标签

#### 1.4 工具和可视化 (4个文件)
- `visualization/visualization.py` - 可视化工具
- `utils/trading_utils.py` - 交易工具
- `component_factory.py` - 组件工厂
- `core/stock_screener.py` - 股票筛选器

**总计**: 24个文件存在HIkyuu强依赖

### 2. 依赖类型分析

```python
# 类型1: 直接导入整个模块
import hikyuu as hku
from hikyuu import *
from hikyuu.interactive import *

# 类型2: 导入特定组件
from hikyuu import StockManager, Query, KData, Stock
from hikyuu.indicator import MA, MACD, RSI, KDJ, BOLL
from hikyuu.trade_sys import SignalBase, MoneyManagerBase

# 类型3: 条件导入 (已有部分容错处理)
try:
    import hikyuu as hku
    HIKYUU_AVAILABLE = True
except ImportError:
    hku = None
    HIKYUU_AVAILABLE = False
```

---

## 🏗️ TET框架架构设计

### 1. TET框架核心概念

**TET (Transform-Extract-Transform)** 是一个现代化的数据处理框架：

```
┌─────────────────────────────────────────────────────────────┐
│                    TET数据处理流水线                          │
├─────────────────────────────────────────────────────────────┤
│  Transform 1    →    Extract    →    Transform 2           │
│  (数据预处理)        (数据提取)      (数据后处理)             │
├─────────────────────────────────────────────────────────────┤
│  ├── 数据清洗      ├── 多源聚合    ├── 格式标准化             │
│  ├── 格式转换      ├── 智能路由    ├── 质量验证               │
│  ├── 参数验证      ├── 缓存管理    ├── 结果封装               │
│  └── 权限检查      └── 并发控制    └── 错误处理               │
└─────────────────────────────────────────────────────────────┘
```

### 2. TET框架核心组件

#### 2.1 数据管道 (Data Pipeline)

```python
# core/tet/pipeline.py
class TETDataPipeline:
    """TET数据管道 - 统一数据处理流程"""
    
    def __init__(self, config: TETConfig):
        self.transformers = []  # 数据转换器列表
        self.extractors = []    # 数据提取器列表
        self.validators = []    # 数据验证器列表
        self.cache_manager = TETCacheManager()
        self.router = TETDataRouter()
    
    async def process(self, request: DataRequest) -> DataResponse:
        """处理数据请求"""
        # Transform 1: 预处理
        transformed_request = await self._pre_transform(request)
        
        # Extract: 数据提取
        raw_data = await self._extract(transformed_request)
        
        # Transform 2: 后处理
        processed_data = await self._post_transform(raw_data)
        
        return DataResponse(data=processed_data, metadata=metadata)
```

#### 2.2 数据适配器 (Data Adapters)

```python
# core/tet/adapters.py
class TETDataAdapter(ABC):
    """TET数据适配器基类"""
    
    @abstractmethod
    async def extract(self, request: StandardQuery) -> StandardData:
        """提取数据"""
        pass
    
    @abstractmethod
    def supports(self, data_type: str, asset_type: AssetType) -> bool:
        """检查是否支持指定数据类型"""
        pass

class HIkyuuTETAdapter(TETDataAdapter):
    """HIkyuu数据适配器 - 插件化实现"""
    
    def __init__(self):
        self.hikyuu_plugin = None
        self._load_hikyuu_plugin()
    
    def _load_hikyuu_plugin(self):
        """动态加载HIkyuu插件"""
        try:
            from plugins.data_sources.hikyuu_plugin import HIkyuuDataPlugin
            self.hikyuu_plugin = HIkyuuDataPlugin()
        except ImportError:
            logger.warning("HIkyuu插件不可用，将使用其他数据源")
    
    async def extract(self, request: StandardQuery) -> StandardData:
        if self.hikyuu_plugin:
            return await self.hikyuu_plugin.get_data(request)
        else:
            raise DataSourceUnavailableError("HIkyuu插件未安装")
```

#### 2.3 标准化数据模型

```python
# core/tet/models.py
@dataclass
class StandardQuery:
    """标准化查询请求"""
    symbol: str
    asset_type: AssetType
    data_type: DataType
    period: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StandardData:
    """标准化数据响应"""
    data: pd.DataFrame
    metadata: Dict[str, Any]
    source: str
    timestamp: datetime
    quality_score: float = 1.0
```

---

## 🔌 HIkyuu插件化架构设计

### 1. HIkyuu插件系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                   HIkyuu插件生态系统                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┬─────────────────┬─────────────────┐   │
│  │  数据源插件      │   指标插件       │   策略插件       │   │
│  │                │                │                │   │
│  │ HIkyuuData     │ HIkyuuIndicator │ HIkyuuStrategy │   │
│  │ Plugin         │ Plugin          │ Plugin         │   │
│  └─────────────────┴─────────────────┴─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                   插件管理层                                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┬─────────────────┬─────────────────┐   │
│  │  插件加载器      │   依赖管理器     │   生命周期管理   │   │
│  │                │                │                │   │
│  │ PluginLoader   │ DependencyMgr   │ LifecycleMgr   │   │
│  └─────────────────┴─────────────────┴─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                   TET集成层                                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┬─────────────────┬─────────────────┐   │
│  │  TET适配器       │   数据管道       │   路由器         │   │
│  │                │                │                │   │
│  │ TETAdapter     │ TETDataPipeline │ TETDataRouter  │   │
│  └─────────────────┴─────────────────┴─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2. HIkyuu插件接口定义

#### 2.1 数据源插件接口

```python
# plugins/interfaces/data_source_plugin.py
class IHikyuuDataSourcePlugin(IDataSourcePlugin):
    """HIkyuu数据源插件接口"""
    
    @abstractmethod
    async def get_stock_list(self) -> List[StockInfo]:
        """获取股票列表"""
        pass
    
    @abstractmethod
    async def get_kdata(self, symbol: str, period: str, count: int) -> pd.DataFrame:
        """获取K线数据"""
        pass
    
    @abstractmethod
    async def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票信息"""
        pass
    
    @abstractmethod
    def supports_realtime(self) -> bool:
        """是否支持实时数据"""
        pass
```

#### 2.2 技术指标插件接口

```python
# plugins/interfaces/indicator_plugin.py
class IHikyuuIndicatorPlugin(IIndicatorPlugin):
    """HIkyuu技术指标插件接口"""
    
    @abstractmethod
    def calculate_ma(self, data: pd.DataFrame, period: int) -> pd.Series:
        """计算移动平均线"""
        pass
    
    @abstractmethod
    def calculate_macd(self, data: pd.DataFrame, 
                      fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """计算MACD指标"""
        pass
    
    @abstractmethod
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        pass
    
    @abstractmethod
    def get_supported_indicators(self) -> List[str]:
        """获取支持的指标列表"""
        pass
```

#### 2.3 策略插件接口

```python
# plugins/interfaces/strategy_plugin.py
class IHikyuuStrategyPlugin(IStrategyPlugin):
    """HIkyuu策略插件接口"""
    
    @abstractmethod
    def create_signal(self, signal_type: str, parameters: Dict[str, Any]) -> Any:
        """创建信号生成器"""
        pass
    
    @abstractmethod
    def create_money_manager(self, mm_type: str, parameters: Dict[str, Any]) -> Any:
        """创建资金管理器"""
        pass
    
    @abstractmethod
    def create_trading_system(self, config: Dict[str, Any]) -> Any:
        """创建交易系统"""
        pass
    
    @abstractmethod
    def backtest_strategy(self, strategy_config: Dict[str, Any], 
                         data: pd.DataFrame) -> BacktestResult:
        """策略回测"""
        pass
```

### 3. HIkyuu插件实现

#### 3.1 HIkyuu数据源插件

```python
# plugins/data_sources/hikyuu_plugin.py
@plugin_metadata(
    name="HIkyuu数据源插件",
    version="1.0.0",
    plugin_type=PluginType.DATA_SOURCE,
    category=PluginCategory.CORE,
    description="HIkyuu框架数据源插件，提供本地股票数据访问"
)
class HIkyuuDataPlugin(IHikyuuDataSourcePlugin):
    """HIkyuu数据源插件实现"""
    
    def __init__(self):
        self.hikyuu_available = False
        self.sm = None
        self.Query = None
        self._initialize_hikyuu()
    
    def _initialize_hikyuu(self):
        """初始化HIkyuu框架"""
        try:
            import hikyuu as hku
            from hikyuu import StockManager, Query
            from hikyuu.interactive import sm
            
            hku.init()  # 初始化HIkyuu
            self.sm = sm
            self.Query = Query
            self.hikyuu_available = True
            
            logger.info("HIkyuu插件初始化成功")
        except ImportError as e:
            logger.error(f"HIkyuu框架不可用: {e}")
            self.hikyuu_available = False
        except Exception as e:
            logger.error(f"HIkyuu插件初始化失败: {e}")
            self.hikyuu_available = False
    
    def initialize(self, context: PluginContext) -> bool:
        """插件初始化"""
        if not self.hikyuu_available:
            logger.error("HIkyuu框架不可用，插件初始化失败")
            return False
        
        # 注册到TET数据路由器
        context.register_data_adapter('hikyuu', self)
        return True
    
    async def get_stock_list(self) -> List[StockInfo]:
        """获取股票列表"""
        if not self.hikyuu_available:
            raise PluginUnavailableError("HIkyuu插件不可用")
        
        stock_list = []
        for stock in self.sm:
            if stock.valid:
                stock_info = StockInfo(
                    code=f"{stock.market.lower()}{stock.code}",
                    name=stock.name,
                    market=stock.market,
                    industry=getattr(stock, 'industry', '其他')
                )
                stock_list.append(stock_info)
        
        return stock_list
    
    async def get_kdata(self, symbol: str, period: str, count: int) -> pd.DataFrame:
        """获取K线数据"""
        if not self.hikyuu_available:
            raise PluginUnavailableError("HIkyuu插件不可用")
        
        try:
            stock = self.sm[symbol]
            if not stock.valid:
                raise ValueError(f"无效的股票代码: {symbol}")
            
            ktype = self._convert_period(period)
            query = self.Query(-count, ktype=ktype)
            kdata = stock.get_kdata(query)
            
            return self._convert_kdata_to_dataframe(kdata)
        except Exception as e:
            logger.error(f"获取K线数据失败: {symbol} - {e}")
            raise
    
    def _convert_period(self, period: str):
        """转换周期格式"""
        period_map = {
            'D': self.Query.DAY,
            'W': self.Query.WEEK,
            'M': self.Query.MONTH,
            '60': self.Query.MIN60,
            '30': self.Query.MIN30,
            '15': self.Query.MIN15,
            '5': self.Query.MIN5,
            '1': self.Query.MIN
        }
        return period_map.get(period.upper(), self.Query.DAY)
    
    def _convert_kdata_to_dataframe(self, kdata) -> pd.DataFrame:
        """转换K线数据为DataFrame"""
        data_list = []
        for k in kdata:
            data_row = {
                'datetime': k.datetime,
                'open': float(k.open),
                'high': float(k.high),
                'low': float(k.low),
                'close': float(k.close),
                'volume': float(k.volume),
                'amount': float(getattr(k, 'amount', 0))
            }
            data_list.append(data_row)
        
        df = pd.DataFrame(data_list)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        return df
    
    def cleanup(self) -> None:
        """清理插件资源"""
        self.sm = None
        self.Query = None
        self.hikyuu_available = False
```

#### 3.2 HIkyuu指标插件

```python
# plugins/indicators/hikyuu_indicators_plugin.py
@plugin_metadata(
    name="HIkyuu技术指标插件",
    version="1.0.0",
    plugin_type=PluginType.INDICATOR,
    category=PluginCategory.CORE,
    description="HIkyuu框架技术指标插件"
)
class HIkyuuIndicatorPlugin(IHikyuuIndicatorPlugin):
    """HIkyuu技术指标插件实现"""
    
    def __init__(self):
        self.hikyuu_available = False
        self.indicators = {}
        self._initialize_hikyuu_indicators()
    
    def _initialize_hikyuu_indicators(self):
        """初始化HIkyuu指标"""
        try:
            from hikyuu.indicator import MA, MACD, RSI, KDJ, BOLL, ATR, OBV, CCI
            
            self.indicators = {
                'MA': MA,
                'MACD': MACD,
                'RSI': RSI,
                'KDJ': KDJ,
                'BOLL': BOLL,
                'ATR': ATR,
                'OBV': OBV,
                'CCI': CCI
            }
            self.hikyuu_available = True
            logger.info("HIkyuu指标插件初始化成功")
        except ImportError as e:
            logger.error(f"HIkyuu指标模块不可用: {e}")
            self.hikyuu_available = False
    
    def initialize(self, context: PluginContext) -> bool:
        """插件初始化"""
        if not self.hikyuu_available:
            return False
        
        # 注册指标计算器
        context.register_indicator_calculator('hikyuu', self)
        return True
    
    def calculate_ma(self, data: pd.DataFrame, period: int) -> pd.Series:
        """计算移动平均线"""
        if not self.hikyuu_available:
            raise PluginUnavailableError("HIkyuu指标插件不可用")
        
        ma_indicator = self.indicators['MA'](period)
        # 转换数据格式并计算
        result = ma_indicator(self._convert_to_hikyuu_data(data))
        return self._convert_to_pandas_series(result)
    
    def calculate_macd(self, data: pd.DataFrame, 
                      fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """计算MACD指标"""
        if not self.hikyuu_available:
            raise PluginUnavailableError("HIkyuu指标插件不可用")
        
        macd_indicator = self.indicators['MACD'](fast, slow, signal)
        result = macd_indicator(self._convert_to_hikyuu_data(data))
        
        return {
            'macd': self._convert_to_pandas_series(result),
            'signal': self._convert_to_pandas_series(result.get_result(1)),
            'histogram': self._convert_to_pandas_series(result.get_result(2))
        }
    
    def get_supported_indicators(self) -> List[str]:
        """获取支持的指标列表"""
        return list(self.indicators.keys()) if self.hikyuu_available else []
```

---

## 🔄 TET框架集成实现

### 1. TET数据管道核心实现

```python
# core/tet/pipeline.py
class TETDataPipeline:
    """TET数据管道实现"""
    
    def __init__(self, config: TETConfig):
        self.config = config
        self.adapters: Dict[str, TETDataAdapter] = {}
        self.transformers: List[DataTransformer] = []
        self.cache_manager = TETCacheManager(config.cache_config)
        self.router = TETDataRouter()
        self.quality_checker = DataQualityChecker()
        
        # 初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化TET组件"""
        # 注册默认适配器
        self.register_adapter('hikyuu', HIkyuuTETAdapter())
        self.register_adapter('akshare', AkShareTETAdapter())
        self.register_adapter('eastmoney', EastMoneyTETAdapter())
        
        # 注册数据转换器
        self.register_transformer(DataCleaningTransformer())
        self.register_transformer(DataValidationTransformer())
        self.register_transformer(DataNormalizationTransformer())
    
    def register_adapter(self, name: str, adapter: TETDataAdapter):
        """注册数据适配器"""
        self.adapters[name] = adapter
        logger.info(f"TET适配器已注册: {name}")
    
    async def process_request(self, request: StandardQuery) -> StandardData:
        """处理数据请求"""
        try:
            # 1. Transform阶段1：预处理
            processed_request = await self._pre_transform(request)
            
            # 2. Extract阶段：数据提取
            raw_data = await self._extract_data(processed_request)
            
            # 3. Transform阶段2：后处理
            final_data = await self._post_transform(raw_data)
            
            # 4. 质量检查
            quality_score = self.quality_checker.check(final_data)
            
            # 5. 缓存结果
            await self.cache_manager.store(request, final_data)
            
            return StandardData(
                data=final_data,
                metadata={
                    'source': raw_data.source,
                    'processed_at': datetime.now(),
                    'quality_score': quality_score
                },
                source=raw_data.source,
                timestamp=datetime.now(),
                quality_score=quality_score
            )
            
        except Exception as e:
            logger.error(f"TET数据处理失败: {e}")
            raise TETProcessingError(f"数据处理失败: {e}")
    
    async def _pre_transform(self, request: StandardQuery) -> StandardQuery:
        """预处理转换"""
        # 参数验证
        if not request.symbol:
            raise ValueError("股票代码不能为空")
        
        # 标准化股票代码
        normalized_symbol = self._normalize_symbol(request.symbol)
        
        # 日期范围验证
        if request.start_date and request.end_date:
            if request.start_date > request.end_date:
                raise ValueError("开始日期不能晚于结束日期")
        
        return StandardQuery(
            symbol=normalized_symbol,
            asset_type=request.asset_type,
            data_type=request.data_type,
            period=request.period,
            start_date=request.start_date,
            end_date=request.end_date,
            parameters=request.parameters
        )
    
    async def _extract_data(self, request: StandardQuery) -> StandardData:
        """数据提取"""
        # 检查缓存
        cached_data = await self.cache_manager.get(request)
        if cached_data:
            logger.info(f"从缓存获取数据: {request.symbol}")
            return cached_data
        
        # 选择最优数据源
        adapter_name = self.router.route(request)
        adapter = self.adapters.get(adapter_name)
        
        if not adapter:
            raise DataSourceUnavailableError(f"数据源不可用: {adapter_name}")
        
        # 提取数据
        data = await adapter.extract(request)
        logger.info(f"从{adapter_name}获取数据: {request.symbol}")
        
        return data
    
    async def _post_transform(self, data: StandardData) -> pd.DataFrame:
        """后处理转换"""
        df = data.data.copy()
        
        # 应用所有转换器
        for transformer in self.transformers:
            df = await transformer.transform(df)
        
        return df
```

### 2. TET数据路由器

```python
# core/tet/router.py
class TETDataRouter:
    """TET数据路由器 - 智能选择最优数据源"""
    
    def __init__(self):
        self.adapter_priorities = {
            'hikyuu': {'priority': 1, 'supports_realtime': False, 'data_quality': 0.95},
            'akshare': {'priority': 2, 'supports_realtime': True, 'data_quality': 0.85},
            'eastmoney': {'priority': 3, 'supports_realtime': True, 'data_quality': 0.80},
            'sina': {'priority': 4, 'supports_realtime': True, 'data_quality': 0.75}
        }
        self.adapter_health = {}
        
    def route(self, request: StandardQuery) -> str:
        """路由数据请求到最优数据源"""
        available_adapters = self._get_available_adapters(request)
        
        if not available_adapters:
            raise NoAvailableDataSourceError("没有可用的数据源")
        
        # 根据优先级和健康状态选择
        best_adapter = self._select_best_adapter(available_adapters, request)
        
        logger.info(f"路由请求到数据源: {best_adapter} (symbol: {request.symbol})")
        return best_adapter
    
    def _get_available_adapters(self, request: StandardQuery) -> List[str]:
        """获取可用的数据适配器"""
        available = []
        
        for adapter_name, config in self.adapter_priorities.items():
            # 检查适配器是否支持请求的数据类型
            if self._adapter_supports_request(adapter_name, request):
                # 检查适配器健康状态
                if self._is_adapter_healthy(adapter_name):
                    available.append(adapter_name)
        
        return available
    
    def _select_best_adapter(self, adapters: List[str], request: StandardQuery) -> str:
        """选择最佳适配器"""
        # 按优先级排序
        adapters.sort(key=lambda x: self.adapter_priorities[x]['priority'])
        
        # 如果需要实时数据，优先选择支持实时的数据源
        if request.parameters.get('realtime', False):
            realtime_adapters = [
                a for a in adapters 
                if self.adapter_priorities[a]['supports_realtime']
            ]
            if realtime_adapters:
                return realtime_adapters[0]
        
        # 返回优先级最高的适配器
        return adapters[0]
    
    def update_adapter_health(self, adapter_name: str, is_healthy: bool, 
                            response_time: float = None, error_rate: float = None):
        """更新适配器健康状态"""
        self.adapter_health[adapter_name] = {
            'is_healthy': is_healthy,
            'last_check': datetime.now(),
            'response_time': response_time,
            'error_rate': error_rate
        }
```

### 3. TET缓存管理器

```python
# core/tet/cache.py
class TETCacheManager:
    """TET缓存管理器"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.memory_cache = {}
        self.disk_cache = DiskCache(config.disk_cache_path)
        self.cache_stats = CacheStats()
        
    async def get(self, request: StandardQuery) -> Optional[StandardData]:
        """获取缓存数据"""
        cache_key = self._generate_cache_key(request)
        
        # 先检查内存缓存
        if cache_key in self.memory_cache:
            cache_entry = self.memory_cache[cache_key]
            if not self._is_expired(cache_entry):
                self.cache_stats.record_hit('memory')
                return cache_entry['data']
        
        # 检查磁盘缓存
        disk_data = await self.disk_cache.get(cache_key)
        if disk_data and not self._is_expired(disk_data):
            # 提升到内存缓存
            self.memory_cache[cache_key] = disk_data
            self.cache_stats.record_hit('disk')
            return disk_data['data']
        
        self.cache_stats.record_miss()
        return None
    
    async def store(self, request: StandardQuery, data: StandardData):
        """存储数据到缓存"""
        cache_key = self._generate_cache_key(request)
        cache_entry = {
            'data': data,
            'timestamp': datetime.now(),
            'ttl': self.config.default_ttl
        }
        
        # 存储到内存缓存
        self.memory_cache[cache_key] = cache_entry
        
        # 异步存储到磁盘缓存
        if self.config.enable_disk_cache:
            await self.disk_cache.store(cache_key, cache_entry)
        
        # 清理过期缓存
        await self._cleanup_expired_cache()
    
    def _generate_cache_key(self, request: StandardQuery) -> str:
        """生成缓存键"""
        key_parts = [
            request.symbol,
            request.asset_type.value,
            request.data_type.value,
            request.period,
            str(request.start_date) if request.start_date else '',
            str(request.end_date) if request.end_date else '',
            str(sorted(request.parameters.items()))
        ]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
```

---

## 🚀 重构实施计划

### 阶段1: 基础架构搭建 (2-3周)

#### 1.1 TET框架核心实现
- [ ] 实现TET数据管道核心类
- [ ] 实现TET数据路由器
- [ ] 实现TET缓存管理器
- [ ] 实现标准化数据模型

#### 1.2 插件系统增强
- [ ] 扩展插件接口定义
- [ ] 实现插件生命周期管理
- [ ] 实现插件依赖管理
- [ ] 实现插件健康检查

### 阶段2: HIkyuu插件化 (3-4周)

#### 2.1 HIkyuu数据源插件
- [ ] 实现HIkyuu数据源插件
- [ ] 实现数据格式转换
- [ ] 实现错误处理和降级
- [ ] 编写插件测试用例

#### 2.2 HIkyuu指标插件
- [ ] 实现HIkyuu技术指标插件
- [ ] 实现指标计算接口
- [ ] 实现指标参数管理
- [ ] 实现指标结果缓存

#### 2.3 HIkyuu策略插件
- [ ] 实现HIkyuu策略插件
- [ ] 实现信号生成器插件化
- [ ] 实现资金管理器插件化
- [ ] 实现交易系统插件化

### 阶段3: 系统集成重构 (2-3周)

#### 3.1 数据层重构
- [ ] 重构UnifiedDataManager集成TET
- [ ] 重构数据访问层使用插件
- [ ] 更新数据仓储实现
- [ ] 实现数据源自动切换

#### 3.2 服务层重构
- [ ] 重构StockService使用TET
- [ ] 重构AnalysisService使用插件
- [ ] 重构ChartService集成TET
- [ ] 更新服务引导系统

#### 3.3 UI层适配
- [ ] 更新分析控件使用插件
- [ ] 更新图表控件集成TET
- [ ] 实现插件状态显示
- [ ] 实现插件管理界面

### 阶段4: 测试和优化 (2周)

#### 4.1 功能测试
- [ ] 单元测试覆盖
- [ ] 集成测试验证
- [ ] 性能测试对比
- [ ] 兼容性测试

#### 4.2 文档和部署
- [ ] 更新开发文档
- [ ] 编写迁移指南
- [ ] 实现平滑升级
- [ ] 用户培训材料

---

## 📊 预期收益

### 1. 技术收益

- **降低耦合度**: 消除HIkyuu强依赖，提升系统灵活性
- **提升扩展性**: 插件化架构支持更多数据源和功能
- **改善性能**: TET框架优化数据处理流程
- **增强稳定性**: 多数据源冗余，提升系统可靠性

### 2. 业务收益

- **功能完整性**: 保持现有所有功能不变
- **用户体验**: 更快的数据加载和更稳定的服务
- **可维护性**: 模块化设计便于维护和升级
- **生态建设**: 开放的插件系统促进社区发展

### 3. 风险控制

- **向下兼容**: 保持现有API接口不变
- **渐进迁移**: 分阶段实施，降低风险
- **回滚机制**: 支持快速回滚到原有架构
- **监控告警**: 完善的监控体系确保系统稳定

---

## 🔧 实施建议

### 1. 开发策略

- **并行开发**: TET框架和HIkyuu插件可并行开发
- **增量集成**: 逐步替换现有组件，确保系统稳定
- **充分测试**: 每个阶段都要进行充分的测试验证
- **文档先行**: 先完善设计文档，再开始编码

### 2. 团队协作

- **架构师**: 负责TET框架设计和技术决策
- **插件开发**: 负责HIkyuu插件化实现
- **集成测试**: 负责系统集成和测试验证
- **文档维护**: 负责文档更新和用户支持

### 3. 质量保证

- **代码审查**: 所有代码都要经过审查
- **自动化测试**: 建立完善的CI/CD流程
- **性能监控**: 实时监控系统性能指标
- **用户反馈**: 及时收集和处理用户反馈

---

## 📋 总结

通过本重构方案，我们将实现：

1. **彻底解耦**: 将HIkyuu从强依赖转为可选插件
2. **架构升级**: 引入现代化的TET数据处理框架
3. **功能保持**: 确保所有现有功能完整保留
4. **性能提升**: 通过智能路由和缓存优化性能
5. **生态开放**: 建立开放的插件生态系统

这个方案不仅解决了当前的强依赖问题，还为系统未来的发展奠定了坚实的基础。 