# 基于TET框架的数据源分类使用优化方案

## 🎯 方案概述

基于FactorWeave-Quant已有的TET（Transform-Extract-Transform）数据管道框架，优化数据源分类使用策略，充分利用现有的智能路由、故障转移和插件化架构。

## 🏗️ TET框架核心架构

### 1. TET数据管道流程

```python
class TETDataPipeline:
    """TET数据处理管道 - 已实现"""
    
    def process(self, query: StandardQuery) -> StandardData:
        """三阶段数据处理"""
        
        # Stage 1: Transform Query (查询标准化)
        routing_request = self.transform_query(query)
        
        # Stage 2: Extract Data (智能数据提取)
        raw_data, provider_info, failover = self.extract_data_with_failover(
            routing_request, query
        )
        
        # Stage 3: Transform Data (数据标准化)
        standard_data = self.transform_data(raw_data, query)
        
        return StandardData(
            data=standard_data,
            metadata=metadata,
            source_info=provider_info,
            processing_time_ms=processing_time
        )
```

### 2. 智能数据源路由器

```python
class DataSourceRouter:
    """智能路由器 - 已实现多种策略"""
    
    ROUTING_STRATEGIES = {
        'PRIORITY': 优先级路由,
        'ROUND_ROBIN': 轮询路由,
        'HEALTH_BASED': 健康状态路由,
        'CIRCUIT_BREAKER': 熔断器路由,
        'WEIGHTED_ROUND_ROBIN': 加权轮询,
        'LEAST_CONNECTIONS': 最少连接数路由
    }
```

## 📊 基于TET的数据源分类策略

### 1. 按路由策略分类使用

#### 🚀 **高可用核心数据** (Circuit Breaker策略)
```python
HIGH_AVAILABILITY_CONFIG = {
    'asset_types': [AssetType.STOCK, AssetType.INDEX],
    'data_types': [DataType.REAL_TIME_QUOTE, DataType.HISTORICAL_KLINE],
    'routing_strategy': RoutingStrategy.CIRCUIT_BREAKER,
    'data_sources': [
        'tongdaxin_stock_plugin',  # 主要数据源
        'sina_source',             # 备用数据源
        'eastmoney_source'         # 第三备用
    ],
    'circuit_breaker_config': {
        'failure_threshold': 3,
        'failure_rate_threshold': 0.3,
        'recovery_timeout_ms': 30000
    }
}
```

#### ⚖️ **负载均衡历史数据** (Weighted Round Robin策略)
```python
LOAD_BALANCED_CONFIG = {
    'asset_types': [AssetType.STOCK],
    'data_types': [DataType.HISTORICAL_KLINE],
    'routing_strategy': RoutingStrategy.WEIGHTED_ROUND_ROBIN,
    'data_sources': [
        {'source': 'eastmoney_stock_plugin', 'weight': 0.5},  # 50%权重
        {'source': 'tongdaxin_stock_plugin', 'weight': 0.3},  # 30%权重
        {'source': 'sina_source', 'weight': 0.2}              # 20%权重
    ]
}
```

#### 🎯 **优先级情绪数据** (Priority策略)
```python
PRIORITY_SENTIMENT_CONFIG = {
    'asset_types': [AssetType.STOCK, AssetType.CRYPTO],
    'data_types': [DataType.SENTIMENT, DataType.NEWS],
    'routing_strategy': RoutingStrategy.PRIORITY,
    'data_sources': [
        {'source': 'multi_source_sentiment_plugin', 'priority': 1},
        {'source': 'news_sentiment_plugin', 'priority': 2},
        {'source': 'vix_sentiment_plugin', 'priority': 3}
    ]
}
```

### 2. 按资产类型分类路由

```python
ASSET_TYPE_ROUTING = {
    AssetType.STOCK: {
        'primary_sources': ['tongdaxin_stock_plugin', 'eastmoney_stock_plugin'],
        'fallback_sources': ['sina_source'],
        'routing_strategy': RoutingStrategy.HEALTH_BASED
    },
    
    AssetType.CRYPTO: {
        'primary_sources': ['binance_crypto_plugin'],
        'fallback_sources': ['huobi_crypto_plugin', 'okx_crypto_plugin'],
        'routing_strategy': RoutingStrategy.ROUND_ROBIN
    },
    
    AssetType.FUTURES: {
        'primary_sources': ['futures_data_plugin'],
        'fallback_sources': ['ctp_futures_plugin'],
        'routing_strategy': RoutingStrategy.PRIORITY
    },
    
    AssetType.FOREX: {
        'primary_sources': ['forex_data_plugin'],
        'routing_strategy': RoutingStrategy.CIRCUIT_BREAKER
    }
}
```

## 🔧 TET框架使用优化

### 1. 标准化查询接口

```python
class OptimizedTETQueryManager:
    """基于TET的优化查询管理器"""
    
    def __init__(self):
        # 使用现有的TET管道
        from core.data_source_router import DataSourceRouter
        from core.tet_data_pipeline import TETDataPipeline
        
        self.router = DataSourceRouter()
        self.pipeline = TETDataPipeline(self.router)
        
        # 配置不同场景的路由策略
        self._configure_routing_strategies()
    
    def _configure_routing_strategies(self):
        """配置路由策略"""
        
        # 实时交易场景 - 熔断器策略
        self.router.set_strategy_for_scenario(
            scenario='realtime_trading',
            strategy=RoutingStrategy.CIRCUIT_BREAKER,
            config={
                'failure_threshold': 2,
                'recovery_timeout_ms': 15000
            }
        )
        
        # 历史分析场景 - 加权轮询
        self.router.set_strategy_for_scenario(
            scenario='historical_analysis',
            strategy=RoutingStrategy.WEIGHTED_ROUND_ROBIN,
            config={
                'weights': {
                    'eastmoney_stock_plugin': 0.6,
                    'tongdaxin_stock_plugin': 0.4
                }
            }
        )
        
        # 情绪分析场景 - 优先级策略
        self.router.set_strategy_for_scenario(
            scenario='sentiment_analysis',
            strategy=RoutingStrategy.PRIORITY,
            config={
                'priorities': {
                    'multi_source_sentiment_plugin': 1,
                    'news_sentiment_plugin': 2
                }
            }
        )
    
    async def get_stock_data(self, 
                           symbol: str,
                           data_type: str = 'kline',
                           period: str = 'daily',
                           start_date: str = None,
                           end_date: str = None,
                           scenario: str = 'historical_analysis') -> pd.DataFrame:
        """
        获取股票数据 - 基于TET框架
        
        Args:
            symbol: 股票代码
            data_type: 数据类型 ('kline', 'realtime', 'sentiment')
            period: 周期
            start_date: 开始日期
            end_date: 结束日期
            scenario: 使用场景，影响路由策略选择
        """
        
        # 构建标准查询
        query = StandardQuery(
            symbol=symbol,
            asset_type=AssetType.STOCK,
            data_type=self._map_data_type(data_type),
            start_date=start_date,
            end_date=end_date,
            period=period,
            extra_params={
                'scenario': scenario  # 传递场景信息给路由器
            }
        )
        
        # 通过TET管道处理
        result = self.pipeline.process(query)
        
        # 记录路由信息
        logger.info(f"数据获取完成 - 使用数据源: {result.source_info.get('provider', 'unknown')}")
        logger.info(f"处理时间: {result.processing_time_ms:.2f}ms")
        
        return result.data
    
    def _map_data_type(self, data_type_str: str) -> DataType:
        """映射数据类型字符串到枚举"""
        mapping = {
            'kline': DataType.HISTORICAL_KLINE,
            'realtime': DataType.REAL_TIME_QUOTE,
            'sentiment': DataType.SENTIMENT,
            'news': DataType.NEWS,
            'financial': DataType.FUNDAMENTAL
        }
        return mapping.get(data_type_str, DataType.HISTORICAL_KLINE)
```

### 2. 智能场景路由配置

```python
class ScenarioBasedRouting:
    """基于场景的智能路由"""
    
    SCENARIO_CONFIGS = {
        # 高频交易场景
        'high_frequency_trading': {
            'routing_strategy': RoutingStrategy.CIRCUIT_BREAKER,
            'timeout_ms': 1000,  # 1秒超时
            'retry_count': 1,
            'cache_ttl_ms': 5000,  # 5秒缓存
            'preferred_sources': ['tongdaxin_stock_plugin', 'sina_source']
        },
        
        # 日内交易场景  
        'intraday_trading': {
            'routing_strategy': RoutingStrategy.HEALTH_BASED,
            'timeout_ms': 3000,
            'retry_count': 2,
            'cache_ttl_ms': 30000,  # 30秒缓存
            'preferred_sources': ['tongdaxin_stock_plugin', 'eastmoney_stock_plugin']
        },
        
        # 历史回测场景
        'historical_backtest': {
            'routing_strategy': RoutingStrategy.WEIGHTED_ROUND_ROBIN,
            'timeout_ms': 10000,
            'retry_count': 3,
            'cache_ttl_ms': 300000,  # 5分钟缓存
            'preferred_sources': ['eastmoney_stock_plugin', 'tongdaxin_stock_plugin'],
            'weights': {'eastmoney_stock_plugin': 0.7, 'tongdaxin_stock_plugin': 0.3}
        },
        
        # 实时监控场景
        'realtime_monitoring': {
            'routing_strategy': RoutingStrategy.LEAST_CONNECTIONS,
            'timeout_ms': 2000,
            'retry_count': 2,
            'cache_ttl_ms': 10000,  # 10秒缓存
            'preferred_sources': ['sina_source', 'tongdaxin_stock_plugin']
        },
        
        # 情绪分析场景
        'sentiment_analysis': {
            'routing_strategy': RoutingStrategy.PRIORITY,
            'timeout_ms': 5000,
            'retry_count': 2,
            'cache_ttl_ms': 60000,  # 1分钟缓存
            'preferred_sources': ['multi_source_sentiment_plugin', 'news_sentiment_plugin']
        }
    }
```

### 3. 数据质量监控与优化

```python
class TETDataQualityMonitor:
    """基于TET的数据质量监控"""
    
    def __init__(self, tet_pipeline: TETDataPipeline):
        self.pipeline = tet_pipeline
        self.quality_metrics = defaultdict(list)
    
    def monitor_data_quality(self, result: StandardData):
        """监控数据质量"""
        
        source = result.source_info.get('provider', 'unknown')
        
        # 数据完整性检查
        completeness = self._check_completeness(result.data)
        
        # 数据一致性检查（如果有多源数据）
        consistency = self._check_consistency(result)
        
        # 响应时间监控
        response_time = result.processing_time_ms
        
        # 记录质量指标
        self.quality_metrics[source].append({
            'timestamp': datetime.now(),
            'completeness': completeness,
            'consistency': consistency,
            'response_time': response_time,
            'data_size': len(result.data)
        })
        
        # 触发质量报警
        if completeness < 0.9 or response_time > 5000:
            self._trigger_quality_alert(source, completeness, response_time)
    
    def _check_completeness(self, data: pd.DataFrame) -> float:
        """检查数据完整性"""
        if data.empty:
            return 0.0
        
        # 检查必要字段是否存在
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        existing_fields = [field for field in required_fields if field in data.columns]
        
        field_completeness = len(existing_fields) / len(required_fields)
        
        # 检查数据空值率
        non_null_rate = (1 - data.isnull().sum().sum() / (len(data) * len(data.columns)))
        
        return (field_completeness + non_null_rate) / 2
    
    def get_quality_report(self) -> Dict[str, Any]:
        """获取数据质量报告"""
        
        report = {}
        
        for source, metrics in self.quality_metrics.items():
            if not metrics:
                continue
                
            recent_metrics = metrics[-10:]  # 最近10次记录
            
            report[source] = {
                'avg_completeness': sum(m['completeness'] for m in recent_metrics) / len(recent_metrics),
                'avg_response_time': sum(m['response_time'] for m in recent_metrics) / len(recent_metrics),
                'total_requests': len(metrics),
                'last_update': recent_metrics[-1]['timestamp'].isoformat()
            }
        
        return report
```

## 📈 实际使用示例

### 1. 基于场景的数据获取

```python
# 初始化TET查询管理器
query_manager = OptimizedTETQueryManager()

# 高频交易场景 - 获取实时数据
realtime_data = await query_manager.get_stock_data(
    symbol='000001',
    data_type='realtime',
    scenario='high_frequency_trading'
)

# 历史回测场景 - 获取历史数据
historical_data = await query_manager.get_stock_data(
    symbol='000001',
    data_type='kline',
    period='daily',
    start_date='2024-01-01',
    end_date='2024-12-01',
    scenario='historical_backtest'
)

# 情绪分析场景 - 获取情绪数据
sentiment_data = await query_manager.get_stock_data(
    symbol='000001',
    data_type='sentiment',
    scenario='sentiment_analysis'
)
```

### 2. 多资产并行获取

```python
async def get_multi_asset_portfolio_data():
    """获取多资产组合数据"""
    
    # 并行构建多个查询
    queries = [
        # 股票数据
        StandardQuery(
            symbol='000001',
            asset_type=AssetType.STOCK,
            data_type=DataType.HISTORICAL_KLINE,
            period='daily'
        ),
        # 加密货币数据
        StandardQuery(
            symbol='BTCUSDT',
            asset_type=AssetType.CRYPTO,
            data_type=DataType.HISTORICAL_KLINE,
            period='daily'
        ),
        # 期货数据
        StandardQuery(
            symbol='IF2412',
            asset_type=AssetType.FUTURES,
            data_type=DataType.HISTORICAL_KLINE,
            period='daily'
        )
    ]
    
    # 并行处理所有查询
    tasks = [pipeline.process(query) for query in queries]
    results = await asyncio.gather(*tasks)
    
    # 组合结果
    portfolio_data = {
        'stock': results[0].data,
        'crypto': results[1].data,
        'futures': results[2].data
    }
    
    return portfolio_data
```

### 3. 智能故障转移示例

```python
class IntelligentFailoverExample:
    """智能故障转移示例"""
    
    def __init__(self):
        self.pipeline = TETDataPipeline(DataSourceRouter())
        
        # 配置故障转移策略
        self._configure_failover()
    
    def _configure_failover(self):
        """配置故障转移策略"""
        
        # 为股票数据配置多层故障转移
        self.pipeline.router.configure_failover_chain(
            asset_type=AssetType.STOCK,
            primary='tongdaxin_stock_plugin',
            fallback_chain=[
                'sina_source',
                'eastmoney_stock_plugin'
            ],
            health_check_interval=30  # 30秒健康检查
        )
    
    async def get_resilient_data(self, symbol: str) -> pd.DataFrame:
        """获取高可用数据"""
        
        query = StandardQuery(
            symbol=symbol,
            asset_type=AssetType.STOCK,
            data_type=DataType.HISTORICAL_KLINE,
            fallback_enabled=True,  # 启用故障转移
            retry_count=3
        )
        
        try:
            result = self.pipeline.process(query)
            
            # 记录使用的数据源
            used_source = result.source_info.get('provider', 'unknown')
            logger.info(f"成功获取数据，使用数据源: {used_source}")
            
            return result.data
            
        except Exception as e:
            logger.error(f"所有数据源都失败: {e}")
            return pd.DataFrame()  # 返回空数据框
```

## 🚀 性能优化建议

### 1. TET管道优化
```python
TET_OPTIMIZATION_CONFIG = {
    # 缓存优化
    'cache': {
        'enable_l1_cache': True,     # 内存缓存
        'enable_l2_cache': True,     # 磁盘缓存
        'default_ttl_minutes': 5,    # 默认缓存时间
        'max_cache_size_mb': 200     # 最大缓存大小
    },
    
    # 并发优化
    'concurrency': {
        'max_workers': 8,            # 最大工作线程
        'connection_pool_size': 10,  # 连接池大小
        'batch_size': 100           # 批处理大小
    },
    
    # 路由优化
    'routing': {
        'health_check_interval': 30, # 健康检查间隔(秒)
        'circuit_breaker_timeout': 60, # 熔断器超时(秒)
        'load_balance_window': 100   # 负载均衡窗口大小
    }
}
```

### 2. 监控和告警
```python
# 集成到现有的TET框架中
class TETMonitoringIntegration:
    """TET框架监控集成"""
    
    def setup_monitoring(self, pipeline: TETDataPipeline):
        """设置监控"""
        
        # 添加性能监控钩子
        pipeline.add_hook('pre_extract', self._log_request_start)
        pipeline.add_hook('post_extract', self._log_request_end)
        pipeline.add_hook('on_failover', self._log_failover_event)
        
        # 设置质量监控
        pipeline.add_quality_monitor(TETDataQualityMonitor(pipeline))
```

## 📋 总结

基于现有TET框架的优化方案具有以下优势：

1. **无缝集成**: 完全基于现有架构，无需重构
2. **智能路由**: 利用已有的多种路由策略
3. **高可用性**: 内置故障转移和熔断器机制
4. **性能优化**: 缓存、并发、批处理等优化
5. **监控完善**: 数据质量和性能监控
6. **场景适配**: 针对不同使用场景优化配置

这个方案充分发挥了FactorWeave-Quant TET框架的强大功能，为数据源分类使用提供了企业级的解决方案。
