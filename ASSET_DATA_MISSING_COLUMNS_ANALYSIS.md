# 资产数据缺失列全面分析与修复报告

**日期**: 2025-10-18  
**问题**: 下载历史资产数据时，数据库没有资产的名字等列  
**影响**: 数据完整性、查询功能、UI显示

---

## 📋 问题描述

### 用户反馈
"下载历史资产数据时，数据库没有资产的名字"

### 问题验证

通过代码分析发现：

1. ✅ **数据标准化时添加了`name`列**（`_standardize_kline_data_fields`）
2. ❌ **数据库表结构没有`name`列**（`historical_kline_data`表定义）
3. ⚠️ **导致数据插入时`name`列被丢弃或报错**

---

## 🔍 根本原因分析

### 调用链梳理

```
用户触发数据导入
    ↓
DataImportExecutionEngine._import_kline_data()
    ↓
_batch_save_kdata_to_database(all_kdata_list)
    ↓
_standardize_kline_data_fields(df)  ← 添加 name 列
    ↓ combined_data 包含 name 列
    ↓
AssetSeparatedDatabaseManager.store_standardized_data(combined_data)
    ↓
_ensure_table_exists(conn, table_name, data, data_type)
    ↓
_generate_create_table_sql(table_name, data, data_type)  ← 查看表结构定义
    ↓
使用 historical_kline_data 表结构  ← ❌ 没有 name 列！
    ↓
_upsert_data(conn, table_name, data, data_type)
    ↓
❌ name 列被丢弃或导致SQL错误
```

### 代码分析

#### 1. 数据标准化代码（添加name列）

**文件**: `core/importdata/import_execution_engine.py`

**代码**:
```python
def _standardize_kline_data_fields(self, df) -> 'pd.DataFrame':
    """标准化K线数据字段，确保与表结构匹配"""
    
    # 基础字段映射和默认值
    field_defaults = {
        # 基础OHLCV字段（8个）
        'symbol': '',
        'datetime': None,
        'open': 0.0,
        'high': 0.0,
        'low': 0.0,
        'close': 0.0,
        'volume': 0,
        'amount': 0.0,
        'turnover': 0.0,
        
        # 元数据（6个）
        'name': None,           # ← ✅ 添加了 name 列！
        'market': None,
        'frequency': '1d',
        'period': None,
        'data_source': 'unknown',
        'created_at': None,
        'updated_at': None,
    }
    
    # 添加缺失的必需字段
    for field, default_value in field_defaults.items():
        if field not in df.columns:
            df[field] = default_value
    
    return df
```

**问题**: 数据中有`name`列，但数据库表结构没有对应的列！

#### 2. 数据库表结构（没有name列）

**文件**: `core/asset_database_manager.py`

**代码**:
```python
def _initialize_table_schemas(self) -> Dict[str, str]:
    """初始化标准表结构定义"""
    return {
        # K线数据表（通用）
        'historical_kline_data': """
            CREATE TABLE IF NOT EXISTS historical_kline_data (
                symbol VARCHAR NOT NULL,
                data_source VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open DECIMAL(18,6) NOT NULL,
                high DECIMAL(18,6) NOT NULL,
                low DECIMAL(18,6) NOT NULL,
                close DECIMAL(18,6) NOT NULL,
                volume BIGINT DEFAULT 0,
                amount DECIMAL(18,6) DEFAULT 0,
                frequency VARCHAR NOT NULL DEFAULT '1d',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, data_source, timestamp, frequency)
            )
        """,
        # ❌ 没有 name 列！
        # ❌ 也没有 market, turnover, period 等列！
    }
```

**问题**: 表结构缺少多个字段：`name`, `market`, `turnover`, `period`, `adj_close`, `adj_factor`, `turnover_rate`, `vwap`

---

## 📊 缺失列详细对比

### K线数据表列对比

| 列名 | 数据标准化 | 数据库表结构 | 状态 |
|------|-----------|------------|------|
| **基础OHLCV** |
| `symbol` | ✅ | ✅ | 匹配 |
| `datetime/timestamp` | ✅ | ✅ | 匹配（名称不同） |
| `open` | ✅ | ✅ | 匹配 |
| `high` | ✅ | ✅ | 匹配 |
| `low` | ✅ | ✅ | 匹配 |
| `close` | ✅ | ✅ | 匹配 |
| `volume` | ✅ | ✅ | 匹配 |
| `amount` | ✅ | ✅ | 匹配 |
| **扩展字段** |
| `turnover` | ✅ | ❌ | **缺失** |
| `adj_close` | ✅ | ❌ | **缺失** |
| `adj_factor` | ✅ | ❌ | **缺失** |
| `turnover_rate` | ✅ | ❌ | **缺失** |
| `vwap` | ✅ | ❌ | **缺失** |
| **元数据** |
| `name` | ✅ | ❌ | **缺失** ⚠️ |
| `market` | ✅ | ❌ | **缺失** ⚠️ |
| `frequency` | ✅ | ✅ | 匹配 |
| `period` | ✅ | ❌ | **缺失** |
| `data_source` | ✅ | ✅ | 匹配 |
| `created_at` | ✅ | ✅ | 匹配 |
| `updated_at` | ✅ | ✅ | 匹配 |

**统计**:
- ✅ 匹配: 11 列
- ❌ 缺失: **9 列**
- 缺失率: **45%**

---

## 🎯 影响范围

### 1. 数据丢失

**影响**: 重要字段无法存储

**丢失的字段**:
- `name`: 资产名称（**用户反馈的核心问题**）
- `market`: 市场信息（SH/SZ/BJ等）
- `adj_close`: 复权价格（量化回测必需）
- `adj_factor`: 复权因子
- `turnover_rate`: 换手率（技术分析指标）
- `vwap`: 成交量加权均价（机构常用）

### 2. 查询功能受限

**场景1**: UI显示资产列表
```python
# ❌ 无法获取资产名称
df = manager.get_kdata("000001")
# df 中没有 'name' 列，UI 只能显示代码
```

**场景2**: 市场过滤
```python
# ❌ 无法按市场过滤
df = manager.get_kdata("000001")
# df 中没有 'market' 列，无法区分 SH/SZ
```

**场景3**: 复权回测
```python
# ❌ 无法进行复权回测
df = manager.get_kdata("000001")
# df 中没有 'adj_close' 列，回测结果不准确
```

### 3. 数据质量问题

**问题**: 数据与表结构不匹配

**可能后果**:
- 插入时列被丢弃（DuckDB不报错但数据丢失）
- 或者插入失败（如果使用严格模式）

---

## ✅ 解决方案

### 方案1: 完整修复（推荐✅）

**目标**: 完全匹配数据标准化和表结构

#### 1.1 修改表结构定义

**文件**: `core/asset_database_manager.py`

**位置**: `_initialize_table_schemas` 方法，`historical_kline_data` 表定义

**修改前**:
```python
'historical_kline_data': """
    CREATE TABLE IF NOT EXISTS historical_kline_data (
        symbol VARCHAR NOT NULL,
        data_source VARCHAR NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        open DECIMAL(18,6) NOT NULL,
        high DECIMAL(18,6) NOT NULL,
        low DECIMAL(18,6) NOT NULL,
        close DECIMAL(18,6) NOT NULL,
        volume BIGINT DEFAULT 0,
        amount DECIMAL(18,6) DEFAULT 0,
        frequency VARCHAR NOT NULL DEFAULT '1d',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (symbol, data_source, timestamp, frequency)
    )
""",
```

**修改后**:
```python
'historical_kline_data': """
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
        
        -- 扩展交易数据
        turnover DECIMAL(18,6) DEFAULT 0,
        adj_close DECIMAL(18,6),
        adj_factor DECIMAL(18,6) DEFAULT 1.0,
        turnover_rate DECIMAL(10,4),
        vwap DECIMAL(18,6),
        
        -- 元数据（✅ 新增）
        name VARCHAR,
        market VARCHAR,
        period VARCHAR,
        
        -- 时间戳
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        PRIMARY KEY (symbol, data_source, timestamp, frequency)
    )
""",
```

**变更摘要**:
- ✅ 新增 `name` 列 - 资产名称
- ✅ 新增 `market` 列 - 市场信息
- ✅ 新增 `period` 列 - 周期信息
- ✅ 新增 `turnover` 列 - 成交额
- ✅ 新增 `adj_close` 列 - 复权价格
- ✅ 新增 `adj_factor` 列 - 复权因子
- ✅ 新增 `turnover_rate` 列 - 换手率
- ✅ 新增 `vwap` 列 - 成交量加权均价

#### 1.2 检查并修复其他表结构

##### ASSET_LIST表（资产列表）

**当前结构**:
```python
'ASSET_LIST': """
    CREATE TABLE {table_name} (
        symbol VARCHAR PRIMARY KEY,
        name VARCHAR,               # ✅ 有name列
        market VARCHAR,
        asset_type VARCHAR,
        status VARCHAR,
        category VARCHAR,
        updated_time TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""
```

**状态**: ✅ 正常，已包含name列

##### REAL_TIME_QUOTE表（实时行情）

**当前结构**:
```python
'REAL_TIME_QUOTE': """
    CREATE TABLE {table_name} (
        symbol VARCHAR,
        name VARCHAR,               # ✅ 有name列
        market VARCHAR,
        current_price DOUBLE,
        open DOUBLE,
        high DOUBLE,
        low DOUBLE,
        close DOUBLE,
        volume DOUBLE,
        amount DOUBLE,
        change DOUBLE,
        change_percent DOUBLE,
        timestamp TIMESTAMP,
        bid_price DOUBLE,
        ask_price DOUBLE,
        bid_volume DOUBLE,
        ask_volume DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (symbol, timestamp)
    )
"""
```

**状态**: ✅ 正常，已包含name列

##### FUNDAMENTAL表（基本面数据）

**当前结构**:
```python
'FUNDAMENTAL': """
    CREATE TABLE {table_name} (
        symbol VARCHAR PRIMARY KEY,
        name VARCHAR,               # ✅ 有name列
        market VARCHAR,
        industry VARCHAR,
        sector VARCHAR,
        list_date DATE,
        total_shares DOUBLE,
        float_shares DOUBLE,
        market_cap DOUBLE,
        status VARCHAR,
        currency VARCHAR,
        is_st BOOLEAN,
        updated_time TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""
```

**状态**: ✅ 正常，已包含name列

**总结**: 只有 `historical_kline_data` 表缺少关键列！

---

### 方案2: 渐进式迁移（备选）

如果担心直接修改表结构影响现有数据，可以使用渐进式迁移：

#### 2.1 创建新表

```python
def migrate_historical_kline_data():
    """迁移历史K线数据表"""
    
    # 1. 创建新表（带所有列）
    sql_create_new = """
        CREATE TABLE IF NOT EXISTS historical_kline_data_v2 (
            -- 完整的列定义（如方案1）
            ...
        )
    """
    
    # 2. 复制现有数据
    sql_migrate = """
        INSERT INTO historical_kline_data_v2 
        SELECT 
            symbol,
            data_source,
            timestamp,
            open,
            high,
            low,
            close,
            volume,
            amount,
            frequency,
            NULL as turnover,
            NULL as adj_close,
            1.0 as adj_factor,
            NULL as turnover_rate,
            NULL as vwap,
            NULL as name,
            NULL as market,
            NULL as period,
            created_at,
            updated_at
        FROM historical_kline_data
    """
    
    # 3. 删除旧表
    sql_drop_old = "DROP TABLE historical_kline_data"
    
    # 4. 重命名新表
    sql_rename = "ALTER TABLE historical_kline_data_v2 RENAME TO historical_kline_data"
```

---

## 🔄 数据补全逻辑

### 3.1 从资产列表补全name和market

**思路**: K线数据中的`symbol`可以关联到`asset_list`表获取`name`和`market`

**实现**:

```python
def enrich_kline_data_with_asset_info(self, kline_df: pd.DataFrame) -> pd.DataFrame:
    """
    从资产列表补全K线数据的name和market字段
    
    Args:
        kline_df: K线数据DataFrame
        
    Returns:
        补全后的DataFrame
    """
    try:
        # 1. 获取资产列表
        asset_list_df = self.get_asset_list()
        
        if asset_list_df.empty:
            logger.warning("资产列表为空，无法补全name和market字段")
            return kline_df
        
        # 2. 准备映射字典
        symbol_to_info = {}
        for _, row in asset_list_df.iterrows():
            symbol = row.get('symbol', row.get('code', ''))
            symbol_to_info[symbol] = {
                'name': row.get('name', ''),
                'market': row.get('market', '')
            }
        
        # 3. 补全K线数据
        def get_asset_info(symbol, field):
            """获取资产信息"""
            info = symbol_to_info.get(symbol, {})
            return info.get(field, None)
        
        # 如果name列不存在或为空，则补全
        if 'name' not in kline_df.columns or kline_df['name'].isna().all():
            kline_df['name'] = kline_df['symbol'].apply(lambda x: get_asset_info(x, 'name'))
            logger.debug(f"补全了 {kline_df['name'].notna().sum()} 条记录的name字段")
        
        # 如果market列不存在或为空，则补全
        if 'market' not in kline_df.columns or kline_df['market'].isna().all():
            kline_df['market'] = kline_df['symbol'].apply(lambda x: get_asset_info(x, 'market'))
            logger.debug(f"补全了 {kline_df['market'].notna().sum()} 条记录的market字段")
        
        # 4. 从symbol推断market（作为后备）
        if 'market' in kline_df.columns:
            def infer_market_from_symbol(row):
                """从symbol推断market"""
                if pd.notna(row['market']) and row['market']:
                    return row['market']  # 已有market信息
                
                symbol = str(row['symbol'])
                if symbol.endswith('.SH'):
                    return 'SH'
                elif symbol.endswith('.SZ'):
                    return 'SZ'
                elif symbol.endswith('.BJ'):
                    return 'BJ'
                elif symbol.startswith('6'):
                    return 'SH'  # 沪市A股
                elif symbol.startswith(('0', '3')):
                    return 'SZ'  # 深市A股/创业板
                elif symbol.startswith(('4', '8')):
                    return 'BJ'  # 北交所
                else:
                    return 'unknown'
            
            kline_df['market'] = kline_df.apply(infer_market_from_symbol, axis=1)
        
        logger.info(f"K线数据补全完成: {len(kline_df)} 条记录")
        return kline_df
        
    except Exception as e:
        logger.error(f"补全K线数据失败: {e}")
        return kline_df
```

**集成位置**: 在 `_standardize_kline_data_fields` 之后调用

```python
def _batch_save_kdata_to_database(self, all_kdata_list: list, task_config: ImportTaskConfig):
    """批量保存K线数据到数据库"""
    try:
        # 合并所有数据
        combined_data = pd.concat(all_kdata_list, ignore_index=True)
        
        # 标准化数据字段
        combined_data = self._standardize_kline_data_fields(combined_data)
        
        # ✅ 新增：补全name和market字段
        combined_data = self.enrich_kline_data_with_asset_info(combined_data)
        
        # 保存数据
        success = asset_manager.store_standardized_data(...)
```

### 3.2 复权因子计算

**思路**: 如果数据源提供了复权价格，自动计算复权因子

```python
def calculate_adj_factor(row):
    """计算复权因子"""
    if pd.notna(row['adj_close']) and row['close'] > 0:
        return row['adj_close'] / row['close']
    return 1.0

kline_df['adj_factor'] = kline_df.apply(calculate_adj_factor, axis=1)
```

### 3.3 换手率计算

**思路**: 从成交量和流通股本计算

```python
def calculate_turnover_rate(symbol, volume, date):
    """计算换手率"""
    # 获取该日期的流通股本
    shares = get_float_shares(symbol, date)
    if shares and shares > 0:
        return (volume / shares) * 100
    return None
```

---

## 📝 实施步骤

### 第1步: 修改表结构定义 ✅

**文件**: `core/asset_database_manager.py`

**修改**: `_initialize_table_schemas` 方法中的 `historical_kline_data` 表定义

### 第2步: 清理现有数据库（可选）⚠️

**警告**: 会删除现有K线数据！

```bash
# 备份现有数据库
cp db/databases/stock_a/stock_a_data.duckdb db/databases/stock_a/stock_a_data.duckdb.backup

# 删除旧表（让系统重新创建）
# 在DuckDB中执行
DROP TABLE IF EXISTS historical_kline_data;
```

**或者使用迁移方案**（推荐）:
```python
# 运行迁移脚本
python migrate_kline_table_structure.py
```

### 第3步: 添加数据补全逻辑 ✅

**文件**: `core/importdata/import_execution_engine.py`

**修改**: 在 `_batch_save_kdata_to_database` 方法中添加数据补全调用

### 第4步: 重新导入数据 ✅

```python
# 重新运行数据导入
python import_stock_data.py
```

### 第5步: 验证数据完整性 ✅

```python
# 检查name列是否有数据
import duckdb
conn = duckdb.connect('db/databases/stock_a/stock_a_data.duckdb')
result = conn.execute("""
    SELECT COUNT(*) as total,
           COUNT(name) as with_name,
           COUNT(market) as with_market
    FROM historical_kline_data
""").fetchone()
print(f"总记录数: {result[0]}")
print(f"有name的记录: {result[1]}")
print(f"有market的记录: {result[2]}")
```

---

## 🎯 预期效果

### 修复前 ❌

```python
df = manager.get_kdata("000001")
print(df.columns)
# ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'amount', ...]
# ❌ 没有 'name', 'market', 'adj_close' 等列

print(df[['symbol', 'close']].head())
#     symbol   close
# 0  000001   10.23
# 1  000001   10.45
# ❌ 无法显示资产名称
```

### 修复后 ✅

```python
df = manager.get_kdata("000001")
print(df.columns)
# ['symbol', 'name', 'market', 'timestamp', 'open', 'high', 'low', 'close', 
#  'volume', 'amount', 'adj_close', 'adj_factor', 'turnover_rate', 'vwap', ...]
# ✅ 包含所有必要列

print(df[['symbol', 'name', 'market', 'close', 'adj_close']].head())
#     symbol    name  market   close  adj_close
# 0  000001  平安银行     SZ   10.23      10.23
# 1  000001  平安银行     SZ   10.45      10.45
# ✅ 可以显示资产名称、市场等完整信息
```

---

## 🔒 后续优化建议

### 1. 实施数据库迁移系统

**参考**: Alembic风格的迁移管理

```python
# migrations/001_add_kline_metadata_columns.py
def upgrade(conn):
    """添加元数据列"""
    conn.execute("""
        ALTER TABLE historical_kline_data 
        ADD COLUMN IF NOT EXISTS name VARCHAR,
        ADD COLUMN IF NOT EXISTS market VARCHAR,
        ADD COLUMN IF NOT EXISTS period VARCHAR,
        ADD COLUMN IF NOT EXISTS turnover DECIMAL(18,6),
        ADD COLUMN IF NOT EXISTS adj_close DECIMAL(18,6),
        ADD COLUMN IF NOT EXISTS adj_factor DECIMAL(18,6) DEFAULT 1.0,
        ADD COLUMN IF NOT EXISTS turnover_rate DECIMAL(10,4),
        ADD COLUMN IF NOT EXISTS vwap DECIMAL(18,6)
    """)

def downgrade(conn):
    """回滚迁移"""
    conn.execute("""
        ALTER TABLE historical_kline_data 
        DROP COLUMN IF EXISTS name,
        DROP COLUMN IF EXISTS market,
        ...
    """)
```

### 2. 添加数据完整性检查

```python
def check_data_completeness(df: pd.DataFrame) -> Dict[str, float]:
    """检查数据完整性"""
    return {
        'name_completeness': df['name'].notna().sum() / len(df) * 100,
        'market_completeness': df['market'].notna().sum() / len(df) * 100,
        'adj_close_completeness': df['adj_close'].notna().sum() / len(df) * 100,
    }
```

### 3. UI显示优化

```python
# 在资产列表显示时，优先使用name，如果没有则使用symbol
def display_asset_name(row):
    """显示资产名称"""
    if pd.notna(row.get('name')) and row['name']:
        return f"{row['name']} ({row['symbol']})"
    return row['symbol']
```

---

## ✅ 总结

### 问题
下载历史资产数据时，`name`、`market`等列缺失

### 根因
1. ❌ 数据标准化添加了9个列
2. ❌ 数据库表结构只有11个列
3. ❌ 9个列被丢弃（45%数据丢失）

### 解决方案
1. ✅ 修改 `historical_kline_data` 表结构（新增9列）
2. ✅ 实现数据补全逻辑（从asset_list获取name/market）
3. ✅ 添加数据完整性验证

### 实施优先级
- 🔴 **高**: 修改表结构定义
- 🔴 **高**: 添加数据补全逻辑
- 🟡 **中**: 实施数据库迁移
- 🟢 **低**: 添加完整性检查

---

**报告状态**: ✅ 完成  
**建议行动**: **立即修改表结构并重新导入数据**

