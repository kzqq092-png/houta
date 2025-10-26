# 资产元数据与K线数据分离架构设计

**日期**: 2025-10-18  
**设计目标**: 在资产数据库中增加独立的资产元数据表，与K线数据分离存储，优化查询性能和数据管理  
**状态**: 设计方案 - 待实施

---

## 📋 目录

1. [问题分析](#问题分析)
2. [当前架构分析](#当前架构分析)
3. [设计方案](#设计方案)
4. [实施步骤](#实施步骤)
5. [性能优化](#性能优化)
6. [迁移策略](#迁移策略)
7. [API设计](#api设计)

---

## 问题分析

### 当前问题

#### 1. 数据冗余严重

**K线表中的元数据冗余**:
```sql
CREATE TABLE historical_kline_data (
    symbol VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(18,6),
    close DECIMAL(18,6),
    ...
    name VARCHAR,          -- ❌ 每条K线记录都重复存储
    market VARCHAR,        -- ❌ 每条K线记录都重复存储
    ...
    PRIMARY KEY (symbol, data_source, timestamp, frequency)
)
```

**问题**:
- 假设一只股票有10年日K线数据 = ~2,500条记录
- 每条记录都存储 `name` 和 `market` → **2,500次冗余**
- 3,000只股票 × 2,500条 = **750万次冗余存储**
- 浪费存储空间：每个name平均10字节 × 750万 = **75MB仅用于存储重复的name**

#### 2. 数据一致性风险

**场景**: 股票改名

```python
# 场景：平安银行从"深圳发展银行"更名为"平安银行"
# 问题：需要更新所有历史K线记录的name字段

UPDATE historical_kline_data 
SET name = '平安银行' 
WHERE symbol = '000001.SZ';  
-- ❌ 需要更新2,500+条记录！
-- ❌ 高风险：可能遗漏部分记录
-- ❌ 性能差：大量行更新
```

#### 3. 查询性能问题

**当前查询模式**:
```python
# UI需要显示"股票名称 + K线数据"
# 方式1：从K线表直接获取（存在冗余）
SELECT symbol, name, market, open, close, volume 
FROM historical_kline_data 
WHERE symbol = '000001.SZ' 
ORDER BY timestamp DESC 
LIMIT 1000;
-- ✅ 速度快，但数据可能不一致
-- ❌ name/market可能是旧数据

# 方式2：没有专门的元数据表，无法单独查询
# ❌ 无法高效获取所有股票的最新元数据
```

#### 4. 元数据管理混乱

**资产列表表 vs K线表**:
```
asset_list表 (全局，跨资产类型)
├─ 存储所有资产的基本信息
├─ 位置：可能在统一数据库
└─ 问题：不一定按资产类型分离

historical_kline_data表 (按资产类型分数据库)
├─ 每个资产数据库都有独立的K线表
├─ K线表中嵌入了元数据字段
└─ 问题：元数据分散在各个资产数据库中
```

**问题**:
- 元数据分散在多个地方
- 更新元数据需要同步多个表
- 无法保证一致性

---

## 当前架构分析

### 数据库结构

#### 资产分离架构

```
db/databases/
├── stock_a/               # A股数据库
│   └── stock_a_data.duckdb
│       ├── historical_kline_data  ← 包含name/market
│       ├── data_quality_monitor
│       └── metadata
│
├── stock_us/              # 美股数据库
│   └── stock_us_data.duckdb
│       ├── historical_kline_data  ← 包含name/market
│       └── ...
│
├── crypto/                # 加密货币数据库
│   └── crypto_data.duckdb
│       └── ...
│
└── futures/               # 期货数据库
    └── futures_data.duckdb
        └── ...
```

**特点**:
- ✅ 按资产类型物理隔离
- ✅ 查询性能好（单资产类型查询）
- ❌ 元数据分散
- ❌ 跨资产查询困难

### 表结构分析

#### 当前 historical_kline_data 表

```sql
CREATE TABLE IF NOT EXISTS historical_kline_data (
    -- 主键字段
    symbol VARCHAR NOT NULL,
    data_source VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    frequency VARCHAR NOT NULL DEFAULT '1d',
    
    -- 基础OHLCV字段
    open DECIMAL(18,6) NOT NULL,
    high DECIMAL(18,6) NOT NULL,
    low DECIMAL(18,6) NOT NULL,
    close DECIMAL(18,6) NOT NULL,
    volume BIGINT DEFAULT 0,
    amount DECIMAL(18,6) DEFAULT 0,
    
    -- ❌ 冗余：元数据字段（每条K线记录都存储）
    name VARCHAR,
    market VARCHAR,
    period VARCHAR,
    
    -- 扩展交易数据
    turnover DECIMAL(18,6) DEFAULT 0,
    adj_close DECIMAL(18,6),
    adj_factor DECIMAL(18,6) DEFAULT 1.0,
    turnover_rate DECIMAL(10,4),
    vwap DECIMAL(18,6),
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (symbol, data_source, timestamp, frequency)
)
```

**问题总结**:
- `name` 字段冗余：每条K线记录都存储相同的股票名称
- `market` 字段冗余：每条K线记录都存储相同的市场信息
- `period` 字段冗余：与 `frequency` 重复
- 无法单独高效查询元数据
- 更新元数据需要修改大量行

#### 当前资产列表查询

```python
# core/services/unified_data_manager.py
def _get_asset_list_from_duckdb(self, asset_type: str, market: str = None):
    """
    从DuckDB获取资产列表
    
    问题：
    1. 没有专门的asset_metadata表
    2. 可能从K线表中DISTINCT提取（性能差）
    3. 或者依赖外部asset_list表（一致性问题）
    """
    # 实际实现可能是：
    # SELECT DISTINCT symbol, name, market FROM historical_kline_data
    # ❌ 全表扫描！性能差！
```

---

## 设计方案

### 方案概述

**核心思想**: 在每个资产数据库中增加独立的 `asset_metadata` 表

```
db/databases/
├── stock_a/
│   └── stock_a_data.duckdb
│       ├── asset_metadata              ← ✅ 新增：资产元数据表
│       │   └── (symbol, name, market, industry, ...)
│       ├── historical_kline_data       ← 🔄 简化：移除name/market
│       │   └── (symbol, timestamp, ohlcv, ...)
│       ├── real_time_quote             ← 🔄 简化：移除name/market
│       └── fundamental_data            ← 🔄 简化：移除name/market
│
├── stock_us/
│   └── stock_us_data.duckdb
│       ├── asset_metadata              ← ✅ 新增
│       └── historical_kline_data       ← 🔄 简化
│
└── crypto/
    └── crypto_data.duckdb
        ├── asset_metadata              ← ✅ 新增
        └── historical_kline_data       ← 🔄 简化
```

### 新表结构设计

#### 1. asset_metadata 表（核心）

```sql
-- 资产元数据表：存储资产的静态/准静态信息
CREATE TABLE IF NOT EXISTS asset_metadata (
    -- 主键
    symbol VARCHAR PRIMARY KEY,
    
    -- 基本信息
    name VARCHAR NOT NULL,
    name_en VARCHAR,                    -- 英文名称
    full_name VARCHAR,                  -- 全称
    short_name VARCHAR,                 -- 简称
    
    -- 分类信息
    asset_type VARCHAR NOT NULL,        -- 资产类型：stock/crypto/futures等
    market VARCHAR NOT NULL,            -- 市场：SH/SZ/BJ/NASDAQ等
    exchange VARCHAR,                   -- 交易所
    
    -- 行业分类
    sector VARCHAR,                     -- 板块
    industry VARCHAR,                   -- 行业
    industry_code VARCHAR,              -- 行业代码
    
    -- 上市信息
    listing_date DATE,                  -- 上市日期
    delisting_date DATE,                -- 退市日期（如有）
    listing_status VARCHAR DEFAULT 'active',  -- 状态：active/suspended/delisted
    
    -- 股本信息（股票特有）
    total_shares BIGINT,                -- 总股本
    circulating_shares BIGINT,          -- 流通股本
    currency VARCHAR DEFAULT 'CNY',     -- 货币单位
    
    -- 加密货币特有
    base_currency VARCHAR,              -- 基础货币（如BTC）
    quote_currency VARCHAR,             -- 计价货币（如USDT）
    contract_type VARCHAR,              -- 合约类型（期货特有）
    
    -- 数据源信息
    data_sources JSON,                  -- 可用数据源列表 ["eastmoney", "sina", "akshare"]
    primary_data_source VARCHAR,        -- 主要数据源
    
    -- 元数据管理
    metadata_version INTEGER DEFAULT 1,  -- 元数据版本号
    data_quality_score DECIMAL(3,2),    -- 数据质量评分 0-1
    last_verified TIMESTAMP,            -- 最后验证时间
    
    -- 扩展字段
    tags JSON,                          -- 标签 ["蓝筹股", "高股息", ...]
    attributes JSON,                    -- 其他属性（灵活存储）
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_name (name),
    INDEX idx_market (market),
    INDEX idx_sector (sector),
    INDEX idx_industry (industry),
    INDEX idx_listing_status (listing_status)
)
```

**设计亮点**:
1. ✅ **单一职责**: 只存储资产的元数据，不存储时序数据
2. ✅ **规范化**: 元数据只存储一次，避免冗余
3. ✅ **可扩展**: JSON字段支持不同资产类型的特殊属性
4. ✅ **版本控制**: metadata_version支持元数据变更追踪
5. ✅ **数据质量**: data_quality_score跟踪元数据质量

#### 2. historical_kline_data 表（简化版）

```sql
-- K线数据表：只存储交易数据，移除元数据字段
CREATE TABLE IF NOT EXISTS historical_kline_data (
    -- 主键字段
    symbol VARCHAR NOT NULL,
    data_source VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    frequency VARCHAR NOT NULL DEFAULT '1d',
    
    -- 基础OHLCV字段
    open DECIMAL(18,6) NOT NULL,
    high DECIMAL(18,6) NOT NULL,
    low DECIMAL(18,6) NOT NULL,
    close DECIMAL(18,6) NOT NULL,
    volume BIGINT DEFAULT 0,
    amount DECIMAL(18,6) DEFAULT 0,
    
    -- 扩展交易数据（量化必需）
    turnover DECIMAL(18,6) DEFAULT 0,
    adj_close DECIMAL(18,6),
    adj_factor DECIMAL(18,6) DEFAULT 1.0,
    turnover_rate DECIMAL(10,4),
    vwap DECIMAL(18,6),
    
    -- ✅ 移除冗余字段
    -- name VARCHAR,          -- ❌ 删除：改用JOIN asset_metadata
    -- market VARCHAR,        -- ❌ 删除：改用JOIN asset_metadata
    -- period VARCHAR,        -- ❌ 删除：与frequency重复
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (symbol, data_source, timestamp, frequency),
    
    -- 外键约束（可选，DuckDB 0.8+支持）
    FOREIGN KEY (symbol) REFERENCES asset_metadata(symbol)
)
```

**优化效果**:
- ✅ 移除 `name`, `market`, `period` 字段
- ✅ 减少每条记录约 20-50 字节
- ✅ 3,000股票 × 2,500条 × 30字节 = **节省 ~225MB**
- ✅ 查询性能提升（行更窄，缓存利用率更高）

#### 3. 统一查询视图（便捷性）

```sql
-- 视图：K线数据 + 资产元数据（便于查询）
CREATE VIEW IF NOT EXISTS kline_with_metadata AS
SELECT 
    k.*,
    m.name,
    m.market,
    m.industry,
    m.sector,
    m.listing_status
FROM historical_kline_data k
LEFT JOIN asset_metadata m ON k.symbol = m.symbol;

-- 使用示例：
-- SELECT * FROM kline_with_metadata WHERE symbol = '000001.SZ' LIMIT 100;
-- ✅ 简单易用，性能优于直接JOIN（视图可能被优化）
```

---

## 调用链分析

### 数据流入（写入）

#### 1. 资产列表导入

```python
# 插件返回资产列表
plugin.get_asset_list() 
→ [{"symbol": "000001.SZ", "name": "平安银行", "market": "SZ", ...}]

# TET框架处理
→ TETDataPipeline.transform_data()
  └─ 标准化字段映射

# 存储层
→ AssetSeparatedDatabaseManager.store_asset_metadata()
  ├─ 路由到对应资产数据库（stock_a_data.duckdb）
  ├─ UPSERT INTO asset_metadata (symbol, name, market, ...)
  └─ 记录版本号和时间戳
```

**关键代码位置**:
- `core/tet_data_pipeline.py`: 数据标准化
- `core/asset_database_manager.py`: 存储逻辑
- **需要新增**: `store_asset_metadata()` 方法

#### 2. K线数据导入

```python
# 插件返回K线数据（不含name/market）
plugin.get_kdata(symbol="000001.SZ") 
→ DataFrame[symbol, timestamp, open, high, low, close, volume, ...]

# TET框架补全元数据（可选，用于验证）
→ TETDataPipeline.transform_data()
  └─ _enrich_with_metadata()  # 从asset_metadata获取name/market
      └─ 仅用于验证symbol是否存在，不写入K线表

# 存储层
→ AssetSeparatedDatabaseManager.store_kline_data()
  ├─ 路由到对应资产数据库
  ├─ INSERT INTO historical_kline_data (symbol, timestamp, ohlcv, ...)
  └─ ✅ 不再存储name/market字段
```

**优化**:
- K线数据更轻量（移除冗余字段）
- 插入性能提升（更少的列）
- 存储空间节省

### 数据流出（查询）

#### 1. UI查询股票列表

```python
# 旧方式（当前）
unified_manager.get_asset_list(asset_type="stock_a")
→ SELECT DISTINCT symbol, name, market FROM historical_kline_data
  # ❌ 全表扫描，性能差

# 新方式（推荐）
unified_manager.get_asset_list(asset_type="stock_a")
→ SELECT symbol, name, market, industry, sector, listing_status 
  FROM asset_metadata 
  WHERE listing_status = 'active'
  ORDER BY symbol
  # ✅ 索引查询，性能好
  # ✅ 返回完整元数据
```

**查询性能对比**:
| 方式 | 表大小 | 查询时间 | 返回字段 |
|-----|--------|---------|---------|
| DISTINCT K线表 | ~750万行 | ~500ms | symbol, name, market |
| asset_metadata表 | ~3,000行 | ~5ms | 所有元数据字段 |
| **性能提升** | - | **100倍** | 更丰富 |

#### 2. UI查询K线数据

```python
# 方式1：只需要K线数据（最快）
unified_manager.get_kdata(symbol="000001.SZ", period="D", count=100)
→ SELECT symbol, timestamp, open, high, low, close, volume 
  FROM historical_kline_data 
  WHERE symbol = ? 
  ORDER BY timestamp DESC 
  LIMIT ?
  # ✅ 最快，但不含name/market

# 方式2：需要K线 + 元数据（推荐）
unified_manager.get_kdata_with_metadata(symbol="000001.SZ", period="D", count=100)
→ SELECT k.*, m.name, m.market, m.industry 
  FROM historical_kline_data k 
  LEFT JOIN asset_metadata m ON k.symbol = m.symbol 
  WHERE k.symbol = ? 
  ORDER BY k.timestamp DESC 
  LIMIT ?
  # ✅ 一次JOIN，性能可接受
  # ✅ 返回完整信息

# 方式3：使用视图（最方便）
→ SELECT * FROM kline_with_metadata 
  WHERE symbol = ? 
  ORDER BY timestamp DESC 
  LIMIT ?
  # ✅ 简单易用
  # ✅ DuckDB优化器可能推送谓词到基表
```

**JOIN性能分析**:
- **JOIN条件**: `k.symbol = m.symbol` (两边都是主键)
- **JOIN类型**: LEFT JOIN (保证返回所有K线数据)
- **索引利用**: 
  - K线表: `WHERE symbol = ?` → 主键索引
  - 元数据表: `ON k.symbol = m.symbol` → 主键查找
- **性能**: 
  - 元数据表小（~3000行），可能完全缓存在内存
  - JOIN开销 < 10ms
  - 总查询时间增加 < 5%

#### 3. 批量查询优化

```python
# 场景：UI显示多只股票的最新行情
symbols = ["000001.SZ", "000002.SZ", ..., "600000.SH"]  # 100只股票

# 方式1：先获取元数据（批量）
metadata_map = unified_manager.get_asset_metadata_batch(symbols)
# → SELECT * FROM asset_metadata WHERE symbol IN (?, ?, ...)
# ✅ 一次查询，100行 → ~2ms

# 方式2：再获取K线数据（并行）
kline_data_list = []
for symbol in symbols:
    kline = unified_manager.get_latest_kline(symbol)
    kline['name'] = metadata_map[symbol]['name']  # 内存JOIN
    kline['market'] = metadata_map[symbol]['market']
    kline_data_list.append(kline)
# ✅ 并行查询 + 内存JOIN，总耗时 ~50ms

# 方式3：使用CTE批量JOIN（推荐）
→ WITH symbols AS (
      SELECT unnest(?) AS symbol
  )
  SELECT k.*, m.name, m.market 
  FROM symbols s
  JOIN historical_kline_data k ON s.symbol = k.symbol
  JOIN asset_metadata m ON k.symbol = m.symbol
  WHERE k.timestamp = (
      SELECT MAX(timestamp) FROM historical_kline_data 
      WHERE symbol = k.symbol
  )
# ✅ 一次查询，数据库内JOIN，最优性能
```

---

## 实施步骤

### Phase 1: 表结构迁移（向后兼容）

#### Step 1.1: 创建 asset_metadata 表

**文件**: `core/asset_database_manager.py`

```python
def _initialize_table_schemas(self) -> Dict[str, str]:
    """初始化标准表结构定义"""
    return {
        # ✅ 新增：资产元数据表
        'asset_metadata': """
            CREATE TABLE IF NOT EXISTS asset_metadata (
                -- 主键
                symbol VARCHAR PRIMARY KEY,
                
                -- 基本信息
                name VARCHAR NOT NULL,
                name_en VARCHAR,
                full_name VARCHAR,
                short_name VARCHAR,
                
                -- 分类信息
                asset_type VARCHAR NOT NULL,
                market VARCHAR NOT NULL,
                exchange VARCHAR,
                
                -- 行业分类
                sector VARCHAR,
                industry VARCHAR,
                industry_code VARCHAR,
                
                -- 上市信息
                listing_date DATE,
                delisting_date DATE,
                listing_status VARCHAR DEFAULT 'active',
                
                -- 股本信息
                total_shares BIGINT,
                circulating_shares BIGINT,
                currency VARCHAR DEFAULT 'CNY',
                
                -- 加密货币/期货特有字段
                base_currency VARCHAR,
                quote_currency VARCHAR,
                contract_type VARCHAR,
                
                -- 数据源信息
                data_sources JSON,
                primary_data_source VARCHAR,
                
                -- 元数据管理
                metadata_version INTEGER DEFAULT 1,
                data_quality_score DECIMAL(3,2),
                last_verified TIMESTAMP,
                
                -- 扩展字段
                tags JSON,
                attributes JSON,
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        
        # 保持原有K线表结构（向后兼容）
        'historical_kline_data': """...""",  # 不变
        
        # ✅ 新增：视图
        'kline_with_metadata': """
            CREATE VIEW IF NOT EXISTS kline_with_metadata AS
            SELECT 
                k.*,
                m.name,
                m.market,
                m.industry,
                m.sector,
                m.listing_status,
                m.exchange
            FROM historical_kline_data k
            LEFT JOIN asset_metadata m ON k.symbol = m.symbol
        """,
        
        ...
    }
```

#### Step 1.2: 添加索引

```python
def _create_asset_metadata_indexes(self, conn):
    """创建asset_metadata表的索引"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_asset_metadata_name ON asset_metadata(name)",
        "CREATE INDEX IF NOT EXISTS idx_asset_metadata_market ON asset_metadata(market)",
        "CREATE INDEX IF NOT EXISTS idx_asset_metadata_sector ON asset_metadata(sector)",
        "CREATE INDEX IF NOT EXISTS idx_asset_metadata_industry ON asset_metadata(industry)",
        "CREATE INDEX IF NOT EXISTS idx_asset_metadata_status ON asset_metadata(listing_status)",
    ]
    
    for idx_sql in indexes:
        conn.execute(idx_sql)
```

### Phase 2: 数据迁移

#### Step 2.1: 从K线表提取元数据

```python
def migrate_metadata_from_kline_table(self, asset_type: AssetType):
    """
    从K线表提取元数据到asset_metadata表
    
    策略：
    1. 提取DISTINCT symbol, name, market
    2. 补充其他元数据（从资产列表API）
    3. 插入到asset_metadata表
    """
    logger.info(f"开始迁移 {asset_type.value} 的元数据...")
    
    db_path = self._get_database_path(asset_type)
    with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
        # 1. 从K线表提取现有元数据
        result = conn.execute("""
            SELECT DISTINCT 
                symbol, 
                name, 
                market,
                MAX(timestamp) as last_trade_date
            FROM historical_kline_data
            WHERE name IS NOT NULL
            GROUP BY symbol, name, market
        """).fetchall()
        
        logger.info(f"从K线表提取了 {len(result)} 个唯一资产")
        
        # 2. 准备插入数据
        insert_sql = """
            INSERT INTO asset_metadata (
                symbol, name, market, asset_type, 
                listing_status, last_verified, created_at
            ) VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (symbol) DO UPDATE SET
                name = EXCLUDED.name,
                market = EXCLUDED.market,
                last_verified = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 3. 批量插入
        for row in result:
            symbol, name, market, last_trade_date = row
            conn.execute(insert_sql, [
                symbol, 
                name if name else symbol,  # 如果name为空，使用symbol
                market if market else 'unknown', 
                asset_type.value
            ])
        
        conn.commit()
        logger.info(f"✅ {asset_type.value} 元数据迁移完成")

def migrate_all_asset_metadata(self):
    """迁移所有资产类型的元数据"""
    for asset_type in AssetType:
        try:
            self.migrate_metadata_from_kline_table(asset_type)
        except Exception as e:
            logger.error(f"迁移 {asset_type.value} 元数据失败: {e}")
```

#### Step 2.2: 从插件补全元数据

```python
def enrich_asset_metadata_from_plugins(self, asset_type: AssetType):
    """
    从插件获取最新的资产列表，补全元数据
    
    补全字段：
    - industry, sector
    - listing_date
    - total_shares, circulating_shares
    - 等
    """
    logger.info(f"从插件补全 {asset_type.value} 的元数据...")
    
    # 1. 获取插件的完整资产列表
    from .services.unified_data_manager import get_unified_data_manager
    manager = get_unified_data_manager()
    
    asset_list_df = manager.get_asset_list(asset_type=asset_type.value)
    if asset_list_df.empty:
        logger.warning(f"插件未返回 {asset_type.value} 的资产列表")
        return
    
    logger.info(f"插件返回了 {len(asset_list_df)} 个资产")
    
    # 2. 更新asset_metadata表
    db_path = self._get_database_path(asset_type)
    with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
        update_sql = """
            INSERT INTO asset_metadata (
                symbol, name, market, asset_type,
                industry, sector, listing_date,
                total_shares, circulating_shares,
                listing_status, last_verified, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (symbol) DO UPDATE SET
                name = EXCLUDED.name,
                market = EXCLUDED.market,
                industry = EXCLUDED.industry,
                sector = EXCLUDED.sector,
                listing_date = EXCLUDED.listing_date,
                total_shares = EXCLUDED.total_shares,
                circulating_shares = EXCLUDED.circulating_shares,
                listing_status = EXCLUDED.listing_status,
                last_verified = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """
        
        for _, row in asset_list_df.iterrows():
            conn.execute(update_sql, [
                row.get('symbol', row.get('code')),
                row.get('name', ''),
                row.get('market', 'unknown'),
                asset_type.value,
                row.get('industry', None),
                row.get('sector', None),
                row.get('listing_date', None),
                row.get('total_shares', None),
                row.get('circulating_shares', None),
                row.get('listing_status', 'active')
            ])
        
        conn.commit()
        logger.info(f"✅ {asset_type.value} 元数据补全完成")
```

### Phase 3: API更新

#### Step 3.1: 新增元数据管理API

**文件**: `core/asset_database_manager.py`

```python
def get_asset_metadata(self, symbol: str, asset_type: AssetType) -> Optional[Dict[str, Any]]:
    """
    获取单个资产的元数据
    
    Args:
        symbol: 资产代码
        asset_type: 资产类型
        
    Returns:
        元数据字典或None
    """
    try:
        db_path = self._get_database_path(asset_type)
        with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
            result = conn.execute(
                "SELECT * FROM asset_metadata WHERE symbol = ?",
                [symbol]
            ).fetchone()
            
            if result:
                columns = [desc[0] for desc in conn.description]
                return dict(zip(columns, result))
            return None
            
    except Exception as e:
        logger.error(f"获取资产元数据失败: {symbol}, {e}")
        return None

def get_asset_metadata_batch(self, symbols: List[str], asset_type: AssetType) -> Dict[str, Dict[str, Any]]:
    """
    批量获取资产元数据
    
    Args:
        symbols: 资产代码列表
        asset_type: 资产类型
        
    Returns:
        {symbol: metadata_dict}
    """
    try:
        if not symbols:
            return {}
        
        db_path = self._get_database_path(asset_type)
        with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
            # 使用IN查询
            placeholders = ','.join(['?' for _ in symbols])
            query = f"SELECT * FROM asset_metadata WHERE symbol IN ({placeholders})"
            
            result = conn.execute(query, symbols).fetchall()
            columns = [desc[0] for desc in conn.description]
            
            return {
                row[0]: dict(zip(columns, row))  # row[0] is symbol
                for row in result
            }
            
    except Exception as e:
        logger.error(f"批量获取资产元数据失败: {e}")
        return {}

def update_asset_metadata(self, symbol: str, asset_type: AssetType, 
                          metadata: Dict[str, Any]) -> bool:
    """
    更新资产元数据
    
    Args:
        symbol: 资产代码
        asset_type: 资产类型
        metadata: 要更新的字段
        
    Returns:
        是否成功
    """
    try:
        db_path = self._get_database_path(asset_type)
        with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
            # 构建UPDATE语句
            set_clause = ', '.join([f"{k} = ?" for k in metadata.keys()])
            set_clause += ", updated_at = CURRENT_TIMESTAMP, metadata_version = metadata_version + 1"
            
            sql = f"UPDATE asset_metadata SET {set_clause} WHERE symbol = ?"
            params = list(metadata.values()) + [symbol]
            
            conn.execute(sql, params)
            conn.commit()
            
            logger.info(f"✅ 更新资产元数据成功: {symbol}")
            return True
            
    except Exception as e:
        logger.error(f"更新资产元数据失败: {symbol}, {e}")
        return False

def search_assets(self, asset_type: AssetType, 
                  name_query: str = None,
                  market: str = None,
                  sector: str = None,
                  industry: str = None,
                  listing_status: str = 'active',
                  limit: int = 100) -> pd.DataFrame:
    """
    搜索资产（支持多条件）
    
    Args:
        asset_type: 资产类型
        name_query: 名称关键词（模糊匹配）
        market: 市场过滤
        sector: 板块过滤
        industry: 行业过滤
        listing_status: 上市状态
        limit: 返回数量限制
        
    Returns:
        资产列表DataFrame
    """
    try:
        db_path = self._get_database_path(asset_type)
        with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
            # 构建WHERE子句
            where_clauses = []
            params = []
            
            if name_query:
                where_clauses.append("(name LIKE ? OR symbol LIKE ?)")
                params.extend([f"%{name_query}%", f"%{name_query}%"])
            
            if market:
                where_clauses.append("market = ?")
                params.append(market)
            
            if sector:
                where_clauses.append("sector = ?")
                params.append(sector)
            
            if industry:
                where_clauses.append("industry = ?")
                params.append(industry)
            
            if listing_status:
                where_clauses.append("listing_status = ?")
                params.append(listing_status)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
                SELECT * FROM asset_metadata 
                WHERE {where_sql}
                ORDER BY symbol
                LIMIT {limit}
            """
            
            result = conn.execute(query, params).fetchdf()
            logger.info(f"搜索到 {len(result)} 个资产")
            return result
            
    except Exception as e:
        logger.error(f"搜索资产失败: {e}")
        return pd.DataFrame()
```

#### Step 3.2: 更新 UnifiedDataManager

**文件**: `core/services/unified_data_manager.py`

```python
def get_asset_list(self, asset_type: str = 'stock', market: str = None, 
                   with_metadata: bool = True) -> pd.DataFrame:
    """
    获取资产列表（使用asset_metadata表）
    
    Args:
        asset_type: 资产类型
        market: 市场过滤
        with_metadata: 是否返回完整元数据
        
    Returns:
        资产列表DataFrame
    """
    try:
        # 映射asset_type字符串到枚举
        asset_type_enum = AssetType(asset_type) if isinstance(asset_type, str) else asset_type
        
        # ✅ 使用新的asset_metadata表
        df = self.asset_manager.search_assets(
            asset_type=asset_type_enum,
            market=market,
            listing_status='active'
        )
        
        if not with_metadata:
            # 只返回基本字段
            df = df[['symbol', 'name', 'market']]
        
        logger.info(f"✅ 从asset_metadata表获取 {len(df)} 个资产")
        return df
        
    except Exception as e:
        logger.error(f"获取资产列表失败: {e}")
        return pd.DataFrame()

def get_kdata_with_metadata(self, symbol: str, period: str = 'D', 
                            count: int = 100) -> pd.DataFrame:
    """
    获取K线数据 + 元数据
    
    Args:
        symbol: 资产代码
        period: 周期
        count: 数量
        
    Returns:
        包含元数据的K线DataFrame
    """
    try:
        # 1. 识别资产类型
        asset_type = self.asset_identifier.identify_asset_type(symbol)
        
        # 2. 获取K线数据
        db_path = self.asset_manager.get_database_path(asset_type)
        with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
            # ✅ 使用视图（自动JOIN元数据）
            query = """
                SELECT * FROM kline_with_metadata
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """
            
            df = conn.execute(query, [symbol, count]).fetchdf()
            
            logger.info(f"✅ 获取K线+元数据成功: {symbol}, {len(df)} 条记录")
            return df
            
    except Exception as e:
        logger.error(f"获取K线+元数据失败: {symbol}, {e}")
        return pd.DataFrame()
```

### Phase 4: TET框架集成

**文件**: `core/tet_data_pipeline.py`

```python
def _enrich_with_metadata(self, data: pd.DataFrame, query: StandardQuery) -> pd.DataFrame:
    """
    补全元数据（使用asset_metadata表）
    
    修改点：
    - 从asset_metadata表查询，而不是asset_list
    - 支持批量查询优化
    - 缓存优化
    """
    try:
        if data.empty:
            return data
        
        # 只对需要元数据的数据类型处理
        if query.data_type not in [DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE]:
            return data
        
        # 获取所有唯一的symbol
        symbols = data['symbol'].unique().tolist()
        
        # ✅ 批量查询asset_metadata
        from .asset_database_manager import AssetSeparatedDatabaseManager
        asset_manager = AssetSeparatedDatabaseManager.get_instance()
        
        metadata_map = asset_manager.get_asset_metadata_batch(
            symbols=symbols,
            asset_type=query.asset_type
        )
        
        if metadata_map:
            # 补全name字段
            if 'name' not in data.columns or data['name'].isna().all():
                data['name'] = data['symbol'].map(lambda s: metadata_map.get(s, {}).get('name', None))
            
            # 补全market字段
            if 'market' not in data.columns or data['market'].isna().all():
                data['market'] = data['symbol'].map(lambda s: metadata_map.get(s, {}).get('market', None))
            
            logger.debug(f"✅ 从asset_metadata批量补全了 {len(symbols)} 个资产的元数据")
        
        return data
        
    except Exception as e:
        logger.error(f"补全元数据失败: {e}")
        return data
```

---

## 性能优化

### 1. 索引策略

```sql
-- asset_metadata表的关键索引
CREATE INDEX idx_asset_metadata_symbol ON asset_metadata(symbol);        -- 主键，自动创建
CREATE INDEX idx_asset_metadata_name ON asset_metadata(name);            -- 名称搜索
CREATE INDEX idx_asset_metadata_market ON asset_metadata(market);        -- 市场过滤
CREATE INDEX idx_asset_metadata_sector ON asset_metadata(sector);        -- 板块过滤
CREATE INDEX idx_asset_metadata_industry ON asset_metadata(industry);    -- 行业过滤
CREATE INDEX idx_asset_metadata_status ON asset_metadata(listing_status);-- 状态过滤

-- 复合索引（常见查询模式）
CREATE INDEX idx_asset_metadata_market_status ON asset_metadata(market, listing_status);
CREATE INDEX idx_asset_metadata_sector_industry ON asset_metadata(sector, industry);
```

### 2. 查询优化

#### 优化1: 使用视图避免重复JOIN

```sql
-- 视图会被DuckDB优化器优化
CREATE VIEW kline_with_metadata AS
SELECT 
    k.symbol, k.timestamp, k.open, k.high, k.low, k.close, k.volume,
    m.name, m.market, m.industry, m.sector
FROM historical_kline_data k
LEFT JOIN asset_metadata m ON k.symbol = m.symbol;

-- 查询时，DuckDB会将WHERE条件下推到基表
SELECT * FROM kline_with_metadata WHERE symbol = '000001.SZ';
-- 等价于：
-- SELECT k.*, m.name, m.market 
-- FROM historical_kline_data k 
-- LEFT JOIN asset_metadata m ON k.symbol = m.symbol
-- WHERE k.symbol = '000001.SZ';  -- WHERE条件下推
```

#### 优化2: 批量查询减少JOIN开销

```python
# 场景：查询多只股票的最新K线

# ❌ 低效方式：逐个查询并JOIN
for symbol in symbols:
    df = conn.execute("""
        SELECT k.*, m.name FROM historical_kline_data k
        LEFT JOIN asset_metadata m ON k.symbol = m.symbol
        WHERE k.symbol = ?
        LIMIT 1
    """, [symbol]).fetchdf()
    # 100次查询 × 10ms = 1000ms

# ✅ 高效方式：批量查询 + 内存JOIN
# Step 1: 批量获取元数据（一次查询）
metadata_df = conn.execute("""
    SELECT * FROM asset_metadata WHERE symbol IN (?, ?, ...)
""", symbols).fetchdf()  # ~5ms

# Step 2: 批量获取K线（并行或CTE）
kline_df = conn.execute("""
    SELECT * FROM historical_kline_data 
    WHERE symbol IN (?, ?, ...)
    AND timestamp >= ?
""", symbols + [start_date]).fetchdf()  # ~50ms

# Step 3: Pandas内存JOIN
result = kline_df.merge(metadata_df[['symbol', 'name', 'market']], 
                        on='symbol', how='left')  # ~5ms
# 总耗时: ~60ms（17倍加速）
```

#### 优化3: 元数据缓存

```python
class MetadataCache:
    """资产元数据缓存"""
    
    def __init__(self, ttl_seconds=3600):
        self._cache = {}  # {symbol: metadata_dict}
        self._cache_time = {}  # {symbol: timestamp}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
    
    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取缓存的元数据"""
        with self._lock:
            if symbol in self._cache:
                # 检查是否过期
                if time.time() - self._cache_time[symbol] < self._ttl:
                    return self._cache[symbol]
                else:
                    # 过期，删除
                    del self._cache[symbol]
                    del self._cache_time[symbol]
        return None
    
    def set(self, symbol: str, metadata: Dict[str, Any]):
        """设置缓存"""
        with self._lock:
            self._cache[symbol] = metadata
            self._cache_time[symbol] = time.time()
    
    def get_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量获取缓存"""
        result = {}
        missing = []
        
        for symbol in symbols:
            cached = self.get(symbol)
            if cached:
                result[symbol] = cached
            else:
                missing.append(symbol)
        
        return result, missing

# 在AssetSeparatedDatabaseManager中使用
class AssetSeparatedDatabaseManager:
    def __init__(self, ...):
        ...
        self._metadata_cache = MetadataCache(ttl_seconds=3600)  # 1小时TTL
    
    def get_asset_metadata_batch(self, symbols, asset_type):
        """批量获取元数据（带缓存）"""
        # 1. 从缓存获取
        cached, missing = self._metadata_cache.get_batch(symbols)
        
        # 2. 查询缺失的
        if missing:
            db_metadata = self._query_metadata_from_db(missing, asset_type)
            # 更新缓存
            for symbol, metadata in db_metadata.items():
                self._metadata_cache.set(symbol, metadata)
            # 合并结果
            cached.update(db_metadata)
        
        return cached
```

### 3. 存储优化

#### 优化1: 压缩存储

```python
# DuckDB支持透明压缩
# asset_metadata表通常较小（~3000行 × ~500字节 = ~1.5MB）
# 开启压缩后 → ~500KB（3倍压缩比）

# 在创建表时设置压缩
CREATE TABLE asset_metadata (...) WITH (
    compression = 'zstd'  -- 或 'gzip', 'snappy'
);
```

#### 优化2: 列式存储优势

DuckDB默认使用列式存储，对于元数据表有以下优势：

```
# 查询：SELECT name, market FROM asset_metadata WHERE market = 'SH'
# 
# 列式存储：
# - 只需读取 name, market 两列
# - market列连续存储，压缩效果好
# - WHERE过滤在列级别，速度快
#
# 行式存储（如SQLite）：
# - 需要读取整行数据
# - 压缩效果差
# - WHERE过滤需要扫描所有列
```

### 4. 并发优化

```python
# asset_metadata表为读多写少场景
# 优化策略：

# 1. 读操作：无锁（DuckDB MVCC）
# 多个查询可以并发读取

# 2. 写操作：批量更新
def update_asset_metadata_batch(self, updates: List[Dict]):
    """批量更新元数据"""
    with transaction:
        for update in updates:
            # UPSERT操作
            conn.execute("""
                INSERT INTO asset_metadata (...)
                VALUES (...)
                ON CONFLICT (symbol) DO UPDATE SET ...
            """)
    # 一次事务提交，减少锁竞争
```

---

## 迁移策略

### 向后兼容策略

**目标**: 零停机迁移，保持系统可用性

#### 阶段1: 双写模式（过渡期）

```python
def store_kline_data(self, df: pd.DataFrame, asset_type: AssetType):
    """
    存储K线数据（双写模式）
    
    阶段1（当前）：
    - 写入historical_kline_data（含name/market）
    - 同时写入asset_metadata（提取唯一值）
    
    阶段2（未来）：
    - 只写入historical_kline_data（不含name/market）
    - asset_metadata由单独的元数据更新流程维护
    """
    try:
        db_path = self._get_database_path(asset_type)
        with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
            # 1. 写入K线数据（保持原有逻辑）
            self._upsert_kline_data(conn, df)
            
            # 2. ✅ 新增：提取并更新asset_metadata
            if 'name' in df.columns or 'market' in df.columns:
                unique_assets = df[['symbol', 'name', 'market']].drop_duplicates()
                self._upsert_asset_metadata(conn, unique_assets, asset_type)
            
            conn.commit()
            
    except Exception as e:
        logger.error(f"存储K线数据失败: {e}")
        raise

def _upsert_asset_metadata(self, conn, assets_df: pd.DataFrame, asset_type: AssetType):
    """更新asset_metadata表（UPSERT）"""
    for _, row in assets_df.iterrows():
        conn.execute("""
            INSERT INTO asset_metadata (symbol, name, market, asset_type, last_verified)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (symbol) DO UPDATE SET
                name = COALESCE(EXCLUDED.name, asset_metadata.name),
                market = COALESCE(EXCLUDED.market, asset_metadata.market),
                last_verified = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """, [
            row['symbol'],
            row.get('name'),
            row.get('market'),
            asset_type.value
        ])
```

#### 阶段2: 视图兼容（查询过渡）

```python
# 旧代码（使用K线表的name/market）
df = conn.execute("""
    SELECT symbol, name, market, open, close 
    FROM historical_kline_data 
    WHERE symbol = ?
""", [symbol]).fetchdf()
# ✅ 仍然可用（向后兼容）

# 新代码（使用视图）
df = conn.execute("""
    SELECT symbol, name, market, open, close 
    FROM kline_with_metadata 
    WHERE symbol = ?
""", [symbol]).fetchdf()
# ✅ 相同结果，更高效

# 最终代码（显式JOIN）
df = conn.execute("""
    SELECT k.symbol, m.name, m.market, k.open, k.close
    FROM historical_kline_data k
    LEFT JOIN asset_metadata m ON k.symbol = m.symbol
    WHERE k.symbol = ?
""", [symbol]).fetchdf()
# ✅ 最清晰，性能最优
```

#### 阶段3: 清理冗余字段（可选）

```sql
-- ⚠️ 破坏性变更：移除K线表的name/market字段
-- 仅在确认所有代码已迁移后执行

-- Step 1: 创建新表结构（无name/market）
CREATE TABLE historical_kline_data_v2 AS
SELECT 
    symbol, data_source, timestamp, frequency,
    open, high, low, close, volume, amount,
    turnover, adj_close, adj_factor, turnover_rate, vwap,
    created_at, updated_at
FROM historical_kline_data;

-- Step 2: 删除旧表
DROP TABLE historical_kline_data;

-- Step 3: 重命名新表
ALTER TABLE historical_kline_data_v2 RENAME TO historical_kline_data;

-- Step 4: 重建索引
CREATE INDEX idx_kline_symbol ON historical_kline_data(symbol);
CREATE INDEX idx_kline_timestamp ON historical_kline_data(timestamp);
...
```

### 回滚策略

```python
def rollback_metadata_separation():
    """
    回滚到旧架构（如果迁移失败）
    
    步骤：
    1. 从asset_metadata回填K线表的name/market
    2. 删除asset_metadata表
    3. 恢复旧查询逻辑
    """
    logger.warning("开始回滚元数据分离...")
    
    for asset_type in AssetType:
        db_path = self._get_database_path(asset_type)
        with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
            # 从asset_metadata回填到K线表
            conn.execute("""
                UPDATE historical_kline_data AS k
                SET 
                    name = m.name,
                    market = m.market
                FROM asset_metadata AS m
                WHERE k.symbol = m.symbol
            """)
            
            conn.commit()
            logger.info(f"✅ {asset_type.value} 回滚完成")
```

---

## API设计

### RESTful API（如果需要对外暴露）

```python
# routes/asset_metadata.py

@app.get("/api/v1/assets/{asset_type}")
def get_asset_list(
    asset_type: str,
    market: Optional[str] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100
):
    """
    获取资产列表
    
    示例：
    GET /api/v1/assets/stock_a?market=SH&sector=金融&limit=50
    """
    manager = AssetSeparatedDatabaseManager.get_instance()
    df = manager.search_assets(
        asset_type=AssetType(asset_type),
        name_query=search,
        market=market,
        sector=sector,
        industry=industry,
        limit=limit
    )
    return df.to_dict(orient='records')

@app.get("/api/v1/assets/{asset_type}/{symbol}")
def get_asset_metadata(asset_type: str, symbol: str):
    """
    获取单个资产的元数据
    
    示例：
    GET /api/v1/assets/stock_a/000001.SZ
    """
    manager = AssetSeparatedDatabaseManager.get_instance()
    metadata = manager.get_asset_metadata(
        symbol=symbol,
        asset_type=AssetType(asset_type)
    )
    if metadata:
        return metadata
    else:
        raise HTTPException(status_code=404, detail="Asset not found")

@app.put("/api/v1/assets/{asset_type}/{symbol}")
def update_asset_metadata(
    asset_type: str, 
    symbol: str, 
    metadata: Dict[str, Any]
):
    """
    更新资产元数据
    
    示例：
    PUT /api/v1/assets/stock_a/000001.SZ
    {
        "name": "平安银行",
        "sector": "金融",
        "industry": "银行"
    }
    """
    manager = AssetSeparatedDatabaseManager.get_instance()
    success = manager.update_asset_metadata(
        symbol=symbol,
        asset_type=AssetType(asset_type),
        metadata=metadata
    )
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=500, detail="Update failed")

@app.get("/api/v1/kline/{asset_type}/{symbol}")
def get_kline_with_metadata(
    asset_type: str,
    symbol: str,
    period: str = 'D',
    count: int = 100
):
    """
    获取K线数据（含元数据）
    
    示例：
    GET /api/v1/kline/stock_a/000001.SZ?period=D&count=100
    """
    manager = get_unified_data_manager()
    df = manager.get_kdata_with_metadata(
        symbol=symbol,
        period=period,
        count=count
    )
    return df.to_dict(orient='records')
```

---

## 总结

### 设计优势

1. **消除冗余** ✅
   - 移除K线表中的name/market冗余字段
   - 节省存储空间 ~225MB（3000股票场景）

2. **数据一致性** ✅
   - 元数据单点维护
   - 避免多处同步问题
   - 版本控制追踪变更

3. **查询性能** ✅
   - 资产列表查询：100倍加速（5ms vs 500ms）
   - K线查询：JOIN开销 < 5%
   - 批量查询优化

4. **可扩展性** ✅
   - JSON字段支持不同资产类型
   - 方便添加新元数据字段
   - 支持未来需求

5. **向后兼容** ✅
   - 双写模式平滑过渡
   - 视图保持旧查询可用
   - 可回滚

### 实施时间表

| 阶段 | 内容 | 预计时间 |
|-----|------|---------|
| Phase 1 | 表结构创建 | 1天 |
| Phase 2 | 数据迁移 | 2天 |
| Phase 3 | API更新 | 2天 |
| Phase 4 | TET框架集成 | 1天 |
| Phase 5 | 测试验证 | 2天 |
| Phase 6 | 文档更新 | 1天 |
| **总计** | | **9天** |

### 风险与缓解

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| 数据迁移失败 | 高 | 1. 备份数据库<br>2. 分批迁移<br>3. 回滚方案 |
| JOIN性能问题 | 中 | 1. 索引优化<br>2. 视图优化<br>3. 缓存机制 |
| 代码兼容性 | 中 | 1. 双写模式<br>2. 向后兼容视图<br>3. 充分测试 |
| 元数据不一致 | 低 | 1. 版本控制<br>2. 定期验证<br>3. 审计日志 |

---

**状态**: ✅ 设计完成，待用户确认后实施  
**建议**: 🚀 立即开始Phase 1（创建表结构）

