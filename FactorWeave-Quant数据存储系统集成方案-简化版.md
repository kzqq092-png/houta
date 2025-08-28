# FactorWeave-Quant数据存储系统集成方案 - 简化版

## 📋 项目概述

### 架构决策
🎯 **不保持向后兼容，重构为现代化架构**
- 移除旧的数据管理器
- 统一使用新的DuckDB+SQLite混合架构
- 简化代码结构，提升可维护性
- 采用现代化设计模式

### 集成目标
✨ **构建全新的现代化数据存储架构**
- 完全替换现有数据管理层
- 统一数据访问接口
- 提升系统性能和可扩展性
- 建立清晰的架构边界

---

## 🏗️ 简化架构设计

### 1. 核心组件替换

#### 1.1 数据管理器统一
```python
# 移除旧组件
- core/services/unified_data_manager.py (旧版)
- core/data/data_access.py (旧版)
- core/data/repository.py (旧版)

# 使用新组件
+ core/services/enhanced_unified_data_manager.py (新版)
+ core/integration/data_router.py (智能路由)
+ core/database/* (完整DuckDB解决方案)
```

#### 1.2 统一数据接口
```python
# core/services/data_service.py - 全新设计

class DataService:
    """统一数据服务 - 现代化设计"""
    
    def __init__(self):
        # 直接使用新的数据管理器
        self.duckdb_operations = get_duckdb_operations()
        self.sqlite_manager = get_sqlite_extension_manager()
        self.data_router = DataRouter()
        self.cache_manager = MultiLevelCacheManager()
        self.tet_pipeline = TETDataPipeline()
    
    def get_kline_data(self, symbol: str, period: str = '1d', 
                       count: int = 100) -> pd.DataFrame:
        """获取K线数据 - 统一接口"""
        # 智能路由选择存储后端
        backend = self.data_router.route('kline_data', 
                                       symbol=symbol, 
                                       row_count=count)
        
        if backend == StorageBackend.DUCKDB:
            return self._get_kline_from_duckdb(symbol, period, count)
        else:
            return self._get_kline_from_sqlite(symbol, period, count)
    
    def store_kline_data(self, data: pd.DataFrame, plugin_name: str,
                        period: str) -> bool:
        """存储K线数据 - 统一接口"""
        # TET管道处理
        processed = self.tet_pipeline.transform_data(data, DataType.KLINE)
        
        # 存储到DuckDB
        table_name = f"kline_data_{plugin_name}_{period}"
        return self.duckdb_operations.insert_dataframe(
            database_path="analytics/hikyuu_analytics.db",
            table_name=table_name,
            data=processed.data,
            upsert=True
        ).success
```

### 2. 插件系统现代化

#### 2.1 插件接口简化
```python
# plugins/base_plugin.py - 重新设计

class ModernDataSourcePlugin:
    """现代化数据源插件基类"""
    
    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.data_service = DataService()  # 直接使用新服务
    
    def fetch_and_store(self, symbol: str, period: str) -> bool:
        """获取并存储数据 - 简化流程"""
        try:
            # 1. 获取原始数据
            raw_data = self.fetch_raw_data(symbol, period)
            
            # 2. 存储数据（自动处理路由和转换）
            return self.data_service.store_kline_data(
                data=raw_data,
                plugin_name=self.plugin_name,
                period=period
            )
        except Exception as e:
            logger.error(f"插件 {self.plugin_name} 数据处理失败: {e}")
            return False
    
    def fetch_raw_data(self, symbol: str, period: str) -> pd.DataFrame:
        """子类实现具体的数据获取逻辑"""
        raise NotImplementedError
```

### 3. 服务层重构

#### 3.1 StockService现代化
```python
# core/services/stock_service.py - 完全重写

class StockService:
    """股票服务 - 现代化实现"""
    
    def __init__(self):
        self.data_service = DataService()
        self.cache_ttl = {
            '1m': 60,
            '5m': 300,
            '1d': 3600,
            '1w': 86400
        }
    
    def get_stock_data(self, symbol: str, period: str = '1d',
                      count: int = 100) -> Optional[pd.DataFrame]:
        """获取股票数据 - 统一入口"""
        cache_key = f"stock_{symbol}_{period}_{count}"
        
        # 检查缓存
        cached = self.data_service.cache_manager.get(cache_key)
        if cached is not None:
            return cached
        
        # 从数据服务获取
        data = self.data_service.get_kline_data(symbol, period, count)
        
        # 缓存结果
        if data is not None and not data.empty:
            ttl = self.cache_ttl.get(period, 3600)
            self.data_service.cache_manager.set(cache_key, data, ttl=ttl)
        
        return data
    
    def get_stock_list(self) -> List[Dict[str, str]]:
        """获取股票列表"""
        # 直接从SQLite获取基础信息
        return self.data_service.sqlite_manager.get_stock_list()
```

---

## 🔄 重构实施计划

### Phase 1: 核心重构（第1-2周）

#### 1.1 移除旧组件
- [ ] 删除旧的UnifiedDataManager
- [ ] 删除旧的DataAccess和Repository
- [ ] 清理重复的数据管理代码
- [ ] 更新所有导入引用

#### 1.2 部署新架构
- [ ] 部署EnhancedUnifiedDataManager
- [ ] 配置DuckDB和SQLite数据库
- [ ] 设置数据路由规则
- [ ] 初始化缓存系统

### Phase 2: 服务层重构（第3-4周）

#### 2.1 核心服务重写
- [ ] 重写StockService
- [ ] 重写AnalysisService
- [ ] 重写BacktestService
- [ ] 统一服务接口

#### 2.2 插件系统重构
- [ ] 重写插件基类
- [ ] 迁移现有插件
- [ ] 测试插件功能
- [ ] 优化插件性能

### Phase 3: UI层适配（第5-6周）

#### 3.1 UI组件更新
- [ ] 更新图表组件数据接口
- [ ] 修改分析面板数据获取
- [ ] 适配回测界面
- [ ] 优化数据加载体验

#### 3.2 配置界面开发
- [ ] 数据库配置面板
- [ ] 缓存管理界面
- [ ] 性能监控面板
- [ ] 系统状态显示

### Phase 4: 测试和优化（第7-8周）

#### 4.1 全面测试
- [ ] 功能测试
- [ ] 性能测试
- [ ] 压力测试
- [ ] 用户验收测试

#### 4.2 性能优化
- [ ] 查询优化
- [ ] 缓存调优
- [ ] 内存优化
- [ ] 并发优化

---

## 📊 代码清理策略

### 1. 移除清单
```bash
# 需要删除的文件和目录
rm -rf core/services/unified_data_manager.py
rm -rf core/data/data_access.py
rm -rf core/data/repository.py
rm -rf core/data/hikyuu_data_manager.py
rm -rf utils/data_sync.py

# 需要清理的重复配置
rm -rf core/config.py (保留core/services/config_service.py)
rm -rf utils/config_manager.py (保留core/services/config_service.py)
```

### 2. 重构清单
```python
# 需要重构的核心文件
core/services/stock_service.py -> 完全重写
core/services/analysis_service.py -> 适配新架构
gui/widgets/analysis_widget.py -> 更新数据接口
plugins/*/plugin.py -> 继承新基类
```

### 3. 配置更新
```yaml
# config/app_config.json - 简化配置
{
    "database": {
        "duckdb": {
            "path": "analytics/hikyuu_analytics.db",
            "memory_limit": "6GB",
            "threads": "auto"
        },
        "sqlite": {
            "path": "db/hikyuu_system.db"
        }
    },
    "cache": {
        "memory_size": 1000,
        "disk_size_mb": 1024,
        "disk_path": "cache/data_cache.db"
    },
    "routing": {
        "large_data_threshold": 1000,
        "default_backend": "duckdb"
    }
}
```

---

## 🎯 架构优势

### 1. 代码简洁性
- **单一数据服务**: 统一的DataService替代多个管理器
- **清晰的职责分离**: 路由、缓存、存储各司其职
- **现代化设计模式**: 依赖注入、策略模式、工厂模式

### 2. 性能优化
- **智能路由**: 自动选择最优存储后端
- **多级缓存**: 内存+磁盘缓存策略
- **批量处理**: DuckDB批量插入和查询优化

### 3. 可维护性
- **统一接口**: 所有数据访问通过DataService
- **插件标准化**: 统一的插件开发模式
- **配置集中化**: 统一的配置管理

### 4. 可扩展性
- **插件化架构**: 易于添加新数据源
- **存储后端抽象**: 易于添加新存储类型
- **缓存策略可配置**: 灵活的缓存配置

---

## 📈 预期收益

### 1. 开发效率提升
- **代码减少30%**: 移除重复代码
- **开发速度提升50%**: 统一接口和工具
- **维护成本降低40%**: 清晰的架构

### 2. 系统性能提升
- **查询性能**: 10-30倍提升
- **内存使用**: 优化30-50%
- **启动速度**: 提升2-3倍

### 3. 用户体验改善
- **响应速度**: 界面响应提升50%
- **稳定性**: 系统稳定性显著提升
- **功能丰富**: 支持更大规模数据分析

---

## 🔍 风险评估

### 1. 技术风险（低）
- **数据迁移**: 使用TET管道确保数据完整性
- **功能缺失**: 新架构功能更强大
- **性能问题**: 经过充分测试和优化

### 2. 业务风险（极低）
- **用户适应**: 界面保持一致，用户无感知
- **功能中断**: 分阶段实施，确保连续性
- **数据安全**: 多重备份和事务保护

---

## 📝 总结

通过不保持向后兼容的重构策略，我们将构建一个：
- **更简洁**: 移除重复代码，统一架构
- **更高效**: 现代化设计，性能优化
- **更可维护**: 清晰职责，标准接口
- **更可扩展**: 插件化架构，灵活配置

的现代化数据存储系统。这将为HIkyuu-UI的长期发展奠定坚实基础。 