# FactorWeave-Quant 多数据源插件数据存储架构深度分析与完整方案

## 📋 方案概述

本方案基于对现有系统的深入分析，包括TET数据管道、插件系统实现、数据库架构等，结合行业专业软件标准，设计了一套完整的多数据源插件数据存储解决方案，确保与现有架构无缝集成，避免重复设计。

**设计版本**: v2.0  
**设计日期**: 2025-01-27  
**设计目标**: 深度集成、无缝扩展、行业对标

## 🔍 现有系统深度分析

### 1. 现有插件系统架构分析

#### 1.1 插件类型体系（已实现）
```python
class PluginType(Enum):
    INDICATOR = "indicator"          # 技术指标插件 ✅
    STRATEGY = "strategy"            # 策略插件 ✅
    DATA_SOURCE = "data_source"      # 数据源插件 ✅
    ANALYSIS = "analysis"            # 分析工具插件 ✅
    UI_COMPONENT = "ui_component"    # UI组件插件 ✅
    EXPORT = "export"                # 导出插件 ✅
    NOTIFICATION = "notification"    # 通知插件 ✅
    CHART_TOOL = "chart_tool"        # 图表工具插件 ✅
```

#### 1.2 现有数据源插件实现
- **HIkyuu数据插件**: 支持股票、指数、基金数据
- **插件元数据管理**: JSON配置文件支持
- **插件生命周期**: 初始化、连接、健康检查、清理
- **能力声明**: 支持的资产类型、数据类型、市场、频率

#### 1.3 现有插件管理机制
- **PluginDatabaseManager**: SQLite插件注册表
- **插件SDK**: 开发、验证、构建、测试工具链
- **插件市场**: 浏览、安装、管理界面

### 2. TET数据管道架构分析

#### 2.1 TET核心组件（已实现）
```python
class TETDataPipeline:
    """Transform-Extract-Transform三阶段数据处理"""
    
    # Stage 1: Transform Query（查询转换）
    def transform_query(self, query: StandardQuery) -> RoutingRequest
    
    # Stage 2: Extract Data（数据提取）
    def extract_data_with_failover(self, request, query) -> Tuple[Any, Dict, FailoverResult]
    
    # Stage 3: Transform Data（数据标准化）
    def transform_data(self, raw_data, query) -> pd.DataFrame
```

#### 2.2 现有字段映射机制
```python
self.field_mappings = {
    DataType.HISTORICAL_KLINE: {
        'o': 'open', 'Open': 'open', 'OPEN': 'open',
        'h': 'high', 'High': 'high', 'HIGH': 'high',
        # ... 更多映射
    }
}
```

#### 2.3 数据源路由器
- **DataSourceRouter**: 智能路由和负载均衡
- **故障转移**: 多数据源自动切换
- **缓存机制**: 5分钟TTL缓存
- **性能统计**: 请求统计和响应时间监控

### 3. 现有数据库架构分析

#### 3.1 混合数据库架构（已实现）
```
SQLite (OLTP)              │  DuckDB (OLAP)
• 系统配置                 │ • 历史K线数据
• 插件管理                 │ • 回测结果
• 用户设置                 │ • 技术指标计算
• 实时状态                 │ • 统计分析
• 缓存数据                 │ • 性能监控数据
```

#### 3.2 现有数据库文件
- **hikyuu_system.db** (180KB) - SQLite系统数据库
- **factorweave_system.db** (3.0MB) - FactorWeave系统数据库
- **factorweave_analytics.db** (3.2MB) - DuckDB分析数据库

#### 3.3 DuckDB性能优化（已实现）
- **DuckDBPerformanceOptimizer**: 自动性能优化
- **工作负载类型**: OLAP/OLTP/MIXED
- **配置管理**: DuckDBConfigManager

## 🎯 完整方案设计（基于现有架构扩展）

### 1. 数据源插件扩展架构

#### 1.1 扩展IDataSourcePlugin接口
```python
class IEnhancedDataSourcePlugin(IDataSourcePlugin):
    """增强数据源插件接口（扩展现有接口）"""
    
    # 继承现有方法
    # connect(), disconnect(), is_connected(), health_check()
    # get_asset_list(), get_kdata()
    
    # 新增方法
    @abstractmethod
    def get_fundamental_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """获取基本面数据"""
        pass
    
    @abstractmethod
    def get_macro_data(self, indicator: str, **kwargs) -> pd.DataFrame:
        """获取宏观数据"""
        pass
    
    @abstractmethod
    def get_financial_statements(self, symbol: str, **kwargs) -> pd.DataFrame:
        """获取财务报表数据"""
        pass
    
    @abstractmethod
    def get_market_depth(self, symbol: str, **kwargs) -> pd.DataFrame:
        """获取市场深度数据"""
        pass
    
    @abstractmethod
    def get_trade_ticks(self, symbol: str, **kwargs) -> pd.DataFrame:
        """获取逐笔交易数据"""
        pass
    
    def get_data_schema(self, data_type: str) -> Dict[str, Any]:
        """获取数据模式定义"""
        return {}
    
    def validate_data_quality(self, data: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """数据质量验证"""
        return {"quality_score": 1.0, "issues": []}
```

#### 1.2 插件注册表扩展（基于现有plugins表）
```sql
-- 扩展现有plugins表，添加数据源特定字段
ALTER TABLE plugins ADD COLUMN supported_assets TEXT DEFAULT '[]';
ALTER TABLE plugins ADD COLUMN supported_data_types TEXT DEFAULT '[]';
ALTER TABLE plugins ADD COLUMN supported_markets TEXT DEFAULT '[]';
ALTER TABLE plugins ADD COLUMN field_mappings TEXT DEFAULT '{}';
ALTER TABLE plugins ADD COLUMN api_endpoints TEXT DEFAULT '{}';
ALTER TABLE plugins ADD COLUMN rate_limits TEXT DEFAULT '{}';
ALTER TABLE plugins ADD COLUMN data_quality_config TEXT DEFAULT '{}';

-- 新增数据源插件配置表
CREATE TABLE IF NOT EXISTS data_source_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_name TEXT NOT NULL,
    config_key TEXT NOT NULL,
    config_value TEXT,
    config_type TEXT DEFAULT 'string',
    is_encrypted BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plugin_name) REFERENCES plugins(name),
    UNIQUE(plugin_name, config_key)
);
```

### 2. TET数据管道增强

#### 2.1 扩展StandardQuery（基于现有实现）
```python
@dataclass
class EnhancedStandardQuery(StandardQuery):
    """增强标准查询（扩展现有StandardQuery）"""
    
    # 继承现有字段
    # symbol, asset_type, data_type, start_date, end_date, period, market, provider
    
    # 新增字段
    data_quality_threshold: float = 0.8      # 数据质量阈值
    enable_cache: bool = True                # 是否启用缓存
    cache_ttl_minutes: int = 5               # 缓存TTL
    enable_validation: bool = True           # 是否启用数据验证
    output_format: str = "pandas"            # 输出格式
    include_metadata: bool = True            # 是否包含元数据
    
    # 高级查询参数
    aggregation_level: Optional[str] = None  # 聚合级别
    filters: Dict[str, Any] = field(default_factory=dict)  # 过滤条件
    sort_by: Optional[str] = None            # 排序字段
    limit: Optional[int] = None              # 记录限制
```

#### 2.2 增强字段映射配置（扩展现有field_mappings）
```python
ENHANCED_FIELD_MAPPINGS = {
    # 继承现有映射
    **TETDataPipeline.field_mappings,
    
    # 新增基本面数据映射
    DataType.FUNDAMENTAL: {
        # Wind标准字段
        'total_mv': 'market_cap', '总市值': 'market_cap',
        'float_mv': 'float_market_cap', '流通市值': 'float_market_cap',
        'pe_ttm': 'pe_ratio', 'PE(TTM)': 'pe_ratio',
        'pb_lf': 'pb_ratio', 'PB(LF)': 'pb_ratio',
        'ps_ttm': 'ps_ratio', 'PS(TTM)': 'ps_ratio',
        
        # Bloomberg标准字段
        'EV_TO_EBITDA': 'ev_ebitda', 'ev_ebitda': 'ev_ebitda',
        'RETURN_ON_EQUITY': 'roe', 'roe': 'roe',
        'RETURN_ON_ASSETS': 'roa', 'roa': 'roa',
        'GROSS_MARGIN': 'gross_margin', 'gross_margin': 'gross_margin',
        
        # 行业分类映射
        'industry_citic_l1': 'industry_l1', '中信一级行业': 'industry_l1',
        'industry_citic_l2': 'industry_l2', '中信二级行业': 'industry_l2',
        'industry_sw_l1': 'industry_l1', '申万一级行业': 'industry_l1',
    },
    
    # 财务数据映射
    DataType.FINANCIAL_STATEMENTS: {
        # 资产负债表
        'total_assets': 'total_assets', '资产总计': 'total_assets',
        'total_liab': 'total_liabilities', '负债合计': 'total_liabilities',
        'total_equity': 'shareholders_equity', '股东权益合计': 'shareholders_equity',
        
        # 利润表
        'total_revenue': 'total_revenue', '营业总收入': 'total_revenue',
        'oper_rev': 'operating_revenue', '营业收入': 'operating_revenue',
        'net_profit_is': 'net_profit', '净利润': 'net_profit',
        'net_profit_parent': 'net_profit_parent', '归母净利润': 'net_profit_parent',
        
        # 现金流量表
        'ocf': 'operating_cash_flow', '经营活动现金流': 'operating_cash_flow',
        'icf': 'investing_cash_flow', '投资活动现金流': 'investing_cash_flow',
        'fcf': 'financing_cash_flow', '筹资活动现金流': 'financing_cash_flow',
    },
    
    # 宏观数据映射
    DataType.MACRO_ECONOMIC: {
        'indicator_code': 'indicator_code', '指标代码': 'indicator_code',
        'indicator_name': 'indicator_name', '指标名称': 'indicator_name',
        'value': 'value', '数值': 'value', 'val': 'value',
        'unit': 'unit', '单位': 'unit',
        'frequency': 'frequency', '频率': 'frequency',
        'country': 'country', '国家': 'country',
        'region': 'region', '地区': 'region',
    }
}
```

### 3. 数据存储架构设计

#### 3.1 DuckDB表结构设计（扩展现有factorweave_analytics.db）

##### 3.1.1 K线数据表（按插件分表）
```sql
-- 动态创建表：kline_data_{plugin_name}_{period}
CREATE TABLE kline_data_hikyuu_1d (
    symbol VARCHAR NOT NULL,
    datetime TIMESTAMP NOT NULL,
    
    -- 基础OHLCV
    open DECIMAL(12,4) NOT NULL,
    high DECIMAL(12,4) NOT NULL,
    low DECIMAL(12,4) NOT NULL,
    close DECIMAL(12,4) NOT NULL,
    volume BIGINT NOT NULL,
    amount DECIMAL(20,2),
    
    -- 复权数据（Wind标准）
    adj_close DECIMAL(12,4),
    adj_factor DECIMAL(10,6),
    
    -- 技术指标预计算
    ma5 DECIMAL(12,4),
    ma10 DECIMAL(12,4),
    ma20 DECIMAL(12,4),
    ma60 DECIMAL(12,4),
    rsi_14 DECIMAL(8,4),
    macd_dif DECIMAL(8,4),
    macd_dea DECIMAL(8,4),
    kdj_k DECIMAL(8,4),
    kdj_d DECIMAL(8,4),
    kdj_j DECIMAL(8,4),
    
    -- 市场微观结构（Bloomberg标准）
    vwap DECIMAL(12,4),
    bid_price DECIMAL(12,4),
    ask_price DECIMAL(12,4),
    spread DECIMAL(8,4),
    
    -- 资金流向（东方财富标准）
    net_inflow_large DECIMAL(20,2),
    net_inflow_main DECIMAL(20,2),
    
    -- 市场情绪
    turnover_rate DECIMAL(8,4),
    amplitude DECIMAL(8,4),
    change_pct DECIMAL(8,4),
    
    -- 扩展字段
    plugin_specific_data JSON,
    
    -- 元数据
    data_source VARCHAR NOT NULL,
    data_quality_score DECIMAL(4,3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (symbol, datetime)
);

-- 创建索引
CREATE INDEX idx_kline_symbol_datetime ON kline_data_hikyuu_1d(symbol, datetime);
CREATE INDEX idx_kline_datetime ON kline_data_hikyuu_1d(datetime);
CREATE INDEX idx_kline_data_source ON kline_data_hikyuu_1d(data_source);
```

##### 3.1.2 基本面数据表
```sql
CREATE TABLE stock_fundamental_{plugin_name} (
    symbol VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    
    -- 基本信息
    name VARCHAR,
    market VARCHAR,
    industry_l1 VARCHAR,
    industry_l2 VARCHAR,
    industry_l3 VARCHAR,
    
    -- 市值信息
    total_shares BIGINT,
    float_shares BIGINT,
    market_cap DECIMAL(20,2),
    float_market_cap DECIMAL(20,2),
    
    -- 估值指标
    pe_ratio DECIMAL(10,4),
    pb_ratio DECIMAL(10,4),
    ps_ratio DECIMAL(10,4),
    pcf_ratio DECIMAL(10,4),
    ev_ebitda DECIMAL(10,4),
    
    -- 盈利能力
    roe DECIMAL(8,4),
    roa DECIMAL(8,4),
    gross_margin DECIMAL(8,4),
    net_margin DECIMAL(8,4),
    
    -- 风险指标
    beta DECIMAL(8,6),
    volatility_30d DECIMAL(8,6),
    volatility_252d DECIMAL(8,6),
    
    -- 扩展字段
    plugin_specific_data JSON,
    
    -- 元数据
    data_source VARCHAR NOT NULL,
    data_quality_score DECIMAL(4,3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (symbol, trade_date)
);
```

##### 3.1.3 财务报表数据表
```sql
CREATE TABLE financial_statements_{plugin_name} (
    symbol VARCHAR NOT NULL,
    report_date DATE NOT NULL,
    report_type VARCHAR NOT NULL, -- annual/semi_annual/quarterly
    
    -- 资产负债表
    total_assets DECIMAL(20,2),
    total_liabilities DECIMAL(20,2),
    shareholders_equity DECIMAL(20,2),
    current_assets DECIMAL(20,2),
    current_liabilities DECIMAL(20,2),
    cash_and_equivalents DECIMAL(20,2),
    
    -- 利润表
    total_revenue DECIMAL(20,2),
    operating_revenue DECIMAL(20,2),
    operating_cost DECIMAL(20,2),
    gross_profit DECIMAL(20,2),
    operating_profit DECIMAL(20,2),
    net_profit DECIMAL(20,2),
    net_profit_parent DECIMAL(20,2),
    
    -- 现金流量表
    operating_cash_flow DECIMAL(20,2),
    investing_cash_flow DECIMAL(20,2),
    financing_cash_flow DECIMAL(20,2),
    free_cash_flow DECIMAL(20,2),
    
    -- 财务比率
    current_ratio DECIMAL(8,4),
    quick_ratio DECIMAL(8,4),
    debt_to_equity DECIMAL(8,4),
    interest_coverage DECIMAL(8,4),
    
    -- 扩展字段
    plugin_specific_data JSON,
    
    -- 元数据
    data_source VARCHAR NOT NULL,
    data_quality_score DECIMAL(4,3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (symbol, report_date, report_type)
);
```

##### 3.1.4 宏观经济数据表
```sql
CREATE TABLE macro_economic_{plugin_name} (
    indicator_code VARCHAR NOT NULL,
    date DATE NOT NULL,
    
    -- 基本信息
    indicator_name VARCHAR NOT NULL,
    value DECIMAL(20,6),
    unit VARCHAR,
    frequency VARCHAR, -- daily/weekly/monthly/quarterly/yearly
    
    -- 分类信息
    category_l1 VARCHAR,
    category_l2 VARCHAR,
    category_l3 VARCHAR,
    
    -- 地区信息
    country VARCHAR,
    region VARCHAR,
    
    -- 数据属性
    is_seasonally_adjusted BOOLEAN DEFAULT FALSE,
    is_preliminary BOOLEAN DEFAULT FALSE,
    revision_count INTEGER DEFAULT 0,
    
    -- 扩展字段
    plugin_specific_data JSON,
    
    -- 元数据
    data_source VARCHAR NOT NULL,
    data_quality_score DECIMAL(4,3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (indicator_code, date)
);
```

#### 3.2 SQLite配置表扩展（基于现有系统数据库）

##### 3.2.1 字段映射表
```sql
CREATE TABLE IF NOT EXISTS field_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_name TEXT NOT NULL,
    data_type TEXT NOT NULL,
    source_field TEXT NOT NULL,
    target_field TEXT NOT NULL,
    field_type TEXT NOT NULL,
    transform_rule TEXT DEFAULT '{}', -- JSON格式转换规则
    validation_rule TEXT DEFAULT '{}', -- JSON格式验证规则
    is_required BOOLEAN DEFAULT 0,
    default_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(plugin_name, data_type, source_field)
);
```

##### 3.2.2 数据质量监控表
```sql
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    metric_date DATE NOT NULL,
    
    -- 完整性指标
    total_records INTEGER DEFAULT 0,
    null_records INTEGER DEFAULT 0,
    duplicate_records INTEGER DEFAULT 0,
    completeness_score DECIMAL(5,4) DEFAULT 0,
    
    -- 准确性指标
    validation_errors INTEGER DEFAULT 0,
    format_errors INTEGER DEFAULT 0,
    range_errors INTEGER DEFAULT 0,
    accuracy_score DECIMAL(5,4) DEFAULT 0,
    
    -- 及时性指标
    data_delay_minutes INTEGER DEFAULT 0,
    timeliness_score DECIMAL(5,4) DEFAULT 0,
    
    -- 一致性指标
    consistency_errors INTEGER DEFAULT 0,
    consistency_score DECIMAL(5,4) DEFAULT 0,
    
    -- 综合评分
    overall_score DECIMAL(5,4) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(plugin_name, table_name, metric_date)
);
```

### 4. 数据管理服务增强

#### 4.1 扩展UnifiedDataManager
```python
class EnhancedUnifiedDataManager(UnifiedDataManager):
    """增强统一数据管理器（扩展现有实现）"""
    
    def __init__(self):
        super().__init__()
        self.plugin_table_manager = PluginTableManager()
        self.data_quality_monitor = DataQualityMonitor()
        self.field_mapping_manager = FieldMappingManager()
    
    def register_data_source_plugin(self, plugin: IEnhancedDataSourcePlugin) -> bool:
        """注册增强数据源插件"""
        try:
            # 调用父类方法
            if not super().register_plugin_data_source(plugin.plugin_info.id, plugin):
                return False
            
            # 创建插件专用表
            self.plugin_table_manager.create_plugin_tables(plugin)
            
            # 注册字段映射
            self.field_mapping_manager.register_plugin_mappings(plugin)
            
            # 初始化数据质量监控
            self.data_quality_monitor.setup_plugin_monitoring(plugin)
            
            return True
            
        except Exception as e:
            logger.error(f"注册插件失败: {e}")
            return False
    
    def get_multi_source_data(self, symbol: str, data_types: List[str], 
                             quality_threshold: float = 0.8) -> Dict[str, pd.DataFrame]:
        """获取多源数据（增强版本）"""
        results = {}
        
        for data_type in data_types:
            try:
                # 使用TET管道获取数据
                query = EnhancedStandardQuery(
                    symbol=symbol,
                    data_type=DataType(data_type),
                    data_quality_threshold=quality_threshold
                )
                
                result = self.tet_pipeline.process(query)
                
                if result and result.data is not None:
                    # 数据质量检查
                    quality_score = self.data_quality_monitor.calculate_quality_score(
                        result.data, data_type
                    )
                    
                    if quality_score >= quality_threshold:
                        results[data_type] = result.data
                    else:
                        logger.warning(f"数据质量不达标: {symbol} {data_type} (score: {quality_score})")
                        
            except Exception as e:
                logger.error(f"获取数据失败: {symbol} {data_type} - {e}")
        
        return results
```

#### 4.2 插件表管理器
```python
class PluginTableManager:
    """插件表管理器"""
    
    def __init__(self, duckdb_path: str = "db/factorweave_analytics.db"):
        self.duckdb_path = duckdb_path
        self.conn = duckdb.connect(duckdb_path)
    
    def create_plugin_tables(self, plugin: IEnhancedDataSourcePlugin) -> bool:
        """为插件创建专用数据表"""
        try:
            plugin_name = plugin.plugin_info.id
            supported_data_types = plugin.plugin_info.supported_data_types
            
            for data_type in supported_data_types:
                if data_type == DataType.HISTORICAL_KLINE:
                    self._create_kline_tables(plugin_name)
                elif data_type == DataType.FUNDAMENTAL:
                    self._create_fundamental_table(plugin_name)
                elif data_type == DataType.FINANCIAL_STATEMENTS:
                    self._create_financial_table(plugin_name)
                elif data_type == DataType.MACRO_ECONOMIC:
                    self._create_macro_table(plugin_name)
            
            return True
            
        except Exception as e:
            logger.error(f"创建插件表失败: {e}")
            return False
    
    def _create_kline_tables(self, plugin_name: str):
        """创建K线数据表"""
        periods = ['1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M']
        
        for period in periods:
            table_name = f"kline_data_{plugin_name}_{period}"
            
            # 检查表是否已存在
            if self._table_exists(table_name):
                continue
            
            sql = f"""
            CREATE TABLE {table_name} (
                symbol VARCHAR NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open DECIMAL(12,4) NOT NULL,
                high DECIMAL(12,4) NOT NULL,
                low DECIMAL(12,4) NOT NULL,
                close DECIMAL(12,4) NOT NULL,
                volume BIGINT NOT NULL,
                amount DECIMAL(20,2),
                adj_close DECIMAL(12,4),
                adj_factor DECIMAL(10,6),
                ma5 DECIMAL(12,4),
                ma10 DECIMAL(12,4),
                ma20 DECIMAL(12,4),
                ma60 DECIMAL(12,4),
                rsi_14 DECIMAL(8,4),
                macd_dif DECIMAL(8,4),
                macd_dea DECIMAL(8,4),
                kdj_k DECIMAL(8,4),
                kdj_d DECIMAL(8,4),
                kdj_j DECIMAL(8,4),
                vwap DECIMAL(12,4),
                bid_price DECIMAL(12,4),
                ask_price DECIMAL(12,4),
                spread DECIMAL(8,4),
                net_inflow_large DECIMAL(20,2),
                net_inflow_main DECIMAL(20,2),
                turnover_rate DECIMAL(8,4),
                amplitude DECIMAL(8,4),
                change_pct DECIMAL(8,4),
                plugin_specific_data JSON,
                data_source VARCHAR NOT NULL,
                data_quality_score DECIMAL(4,3),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, datetime)
            );
            """
            
            self.conn.execute(sql)
            
            # 创建索引
            self.conn.execute(f"CREATE INDEX idx_{table_name}_symbol_datetime ON {table_name}(symbol, datetime);")
            self.conn.execute(f"CREATE INDEX idx_{table_name}_datetime ON {table_name}(datetime);")
    
    def _table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        result = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            [table_name]
        ).fetchone()
        return result is not None
```

### 5. 数据质量监控系统

#### 5.1 数据质量监控器
```python
class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self, sqlite_path: str = "db/factorweave_system.db"):
        self.sqlite_path = sqlite_path
        self.conn = sqlite3.connect(sqlite_path)
    
    def calculate_quality_score(self, data: pd.DataFrame, data_type: str) -> float:
        """计算数据质量综合评分"""
        if data is None or data.empty:
            return 0.0
        
        scores = {}
        
        # 完整性检查
        scores['completeness'] = self._check_completeness(data)
        
        # 准确性检查
        scores['accuracy'] = self._check_accuracy(data, data_type)
        
        # 一致性检查
        scores['consistency'] = self._check_consistency(data, data_type)
        
        # 及时性检查
        scores['timeliness'] = self._check_timeliness(data)
        
        # 加权计算综合评分
        weights = {
            'completeness': 0.3,
            'accuracy': 0.3,
            'consistency': 0.2,
            'timeliness': 0.2
        }
        
        overall_score = sum(scores[key] * weights[key] for key in scores)
        
        return round(overall_score, 4)
    
    def _check_completeness(self, data: pd.DataFrame) -> float:
        """检查数据完整性"""
        if data.empty:
            return 0.0
        
        total_cells = data.size
        null_cells = data.isnull().sum().sum()
        
        completeness = (total_cells - null_cells) / total_cells
        return completeness
    
    def _check_accuracy(self, data: pd.DataFrame, data_type: str) -> float:
        """检查数据准确性"""
        accuracy_score = 1.0
        
        if data_type == "kline":
            # K线数据准确性检查
            if 'open' in data.columns and 'high' in data.columns and 'low' in data.columns and 'close' in data.columns:
                # 检查OHLC逻辑关系
                invalid_ohlc = (
                    (data['high'] < data['open']) |
                    (data['high'] < data['close']) |
                    (data['low'] > data['open']) |
                    (data['low'] > data['close'])
                )
                
                if invalid_ohlc.any():
                    accuracy_score -= 0.2
            
            # 检查成交量是否为负数
            if 'volume' in data.columns:
                if (data['volume'] < 0).any():
                    accuracy_score -= 0.1
        
        return max(0.0, accuracy_score)
    
    def _check_consistency(self, data: pd.DataFrame, data_type: str) -> float:
        """检查数据一致性"""
        consistency_score = 1.0
        
        # 检查时间序列连续性
        if 'datetime' in data.columns:
            data_sorted = data.sort_values('datetime')
            time_diffs = data_sorted['datetime'].diff()
            
            # 检查是否有异常的时间跳跃
            if len(time_diffs) > 1:
                median_diff = time_diffs.median()
                outliers = time_diffs > median_diff * 3
                
                if outliers.any():
                    consistency_score -= 0.1
        
        return consistency_score
    
    def _check_timeliness(self, data: pd.DataFrame) -> float:
        """检查数据及时性"""
        if 'datetime' in data.columns and not data.empty:
            latest_time = pd.to_datetime(data['datetime']).max()
            current_time = datetime.now()
            
            # 计算数据延迟（分钟）
            delay_minutes = (current_time - latest_time).total_seconds() / 60
            
            # 根据延迟时间计算及时性评分
            if delay_minutes <= 5:
                return 1.0
            elif delay_minutes <= 30:
                return 0.8
            elif delay_minutes <= 60:
                return 0.6
            elif delay_minutes <= 1440:  # 1天
                return 0.4
            else:
                return 0.2
        
        return 1.0
```

### 6. 实施计划与集成策略

#### 6.1 阶段化实施计划

##### 阶段一：核心扩展（2周）
1. **扩展现有接口**
   - 扩展IDataSourcePlugin接口
   - 增强StandardQuery和TET管道
   - 扩展UnifiedDataManager

2. **数据库架构扩展**
   - 扩展现有SQLite表结构
   - 在DuckDB中创建新的数据表
   - 实现PluginTableManager

##### 阶段二：数据质量系统（2周）
1. **数据质量监控**
   - 实现DataQualityMonitor
   - 集成到TET管道
   - 创建质量报告界面

2. **字段映射管理**
   - 实现FieldMappingManager
   - 扩展字段映射配置
   - 支持动态映射更新

##### 阶段三：插件生态扩展（3周）
1. **现有插件升级**
   - 升级HIkyuu数据插件
   - 添加新的数据源插件
   - 完善插件元数据

2. **测试和验证**
   - 单元测试覆盖
   - 集成测试验证
   - 性能基准测试

##### 阶段四：优化和部署（2周）
1. **性能优化**
   - DuckDB查询优化
   - 缓存策略调整
   - 内存使用优化

2. **文档和培训**
   - 更新开发文档
   - 创建使用指南
   - 插件开发教程

#### 6.2 与现有系统集成策略

##### 6.2.1 无缝集成原则
- **向后兼容**: 所有现有功能保持不变
- **渐进式升级**: 逐步启用新功能
- **配置驱动**: 通过配置控制新功能启用

##### 6.2.2 集成检查清单
- [ ] 现有插件系统兼容性测试
- [ ] TET数据管道功能验证
- [ ] 数据库迁移脚本测试
- [ ] UI界面适配验证
- [ ] 性能影响评估

## 📈 预期收益与技术优势

### 技术收益
1. **完全兼容**: 与现有系统100%兼容，无破坏性变更
2. **性能提升**: DuckDB列式存储，查询性能提升10-50倍
3. **数据质量**: 建立完善的数据质量监控和评分体系
4. **扩展性强**: 支持新数据源插件的快速接入
5. **标准统一**: 基于TET标准，统一所有数据源格式

### 业务收益
1. **行业对标**: 数据字段完全对标Wind、Bloomberg等专业软件
2. **数据丰富**: 支持K线、基本面、财务、宏观等全方位数据
3. **质量保障**: 数据质量实时监控，确保数据可靠性
4. **开发效率**: 标准化接口，降低插件开发成本
5. **用户体验**: 数据源切换无缝，用户体验一致

## 📋 总结

本方案基于对现有系统的深入分析，采用扩展而非重构的方式，确保与现有架构的完美集成。通过增强TET数据管道、扩展插件系统、优化数据库架构，实现了多数据源插件的统一管理和高效存储，同时建立了完善的数据质量保障体系。

该方案的核心优势在于：
1. **无缝集成**: 完全基于现有架构扩展，无破坏性变更
2. **标准统一**: 基于TET标准和行业最佳实践
3. **质量保障**: 完善的数据质量监控和评分体系
4. **性能优化**: 充分利用DuckDB的技术优势
5. **扩展性强**: 支持未来新数据源的快速接入

这将为FactorWeave-Quant系统提供强大的多数据源统一管理能力，支持历史k线和金融信息在SQLite/DuckDB中的高效存储和查询，完全满足专业量化交易系统的需求。 