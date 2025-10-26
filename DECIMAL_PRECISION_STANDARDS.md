# 金融数据小数点精度标准

**日期**: 2025-10-18  
**目标**: 定义合理的金融数据小数点精度，避免过高精度导致的存储浪费和精度误差

---

## 📋 行业标准参考

### 专业软件精度对比

| 软件 | 价格精度 | 成交量 | 成交额 | 涨跌幅 |
|-----|---------|--------|--------|--------|
| **同花顺** | 2位 (10.23) | 整数 | 2位 | 2位 (2.34%) |
| **通达信** | 2位 (10.23) | 整数 | 2位 | 2位 (2.34%) |
| **东方财富** | 2位 (10.23) | 整数 | 2位 | 2位 (2.34%) |
| **Wind万得** | 4位 (10.2345) | 整数 | 2位 | 4位 (2.3456%) |

**结论**: A股市场标准精度为**2位小数**，专业量化软件可以用**4位小数**

---

## 🎯 本系统精度标准

### A股市场 (stock_a)

```sql
-- 价格类字段: DECIMAL(10,2) - 2位小数
open DECIMAL(10,2)        -- 最高 99,999,999.99 (9千万，足够)
high DECIMAL(10,2)
low DECIMAL(10,2)
close DECIMAL(10,2)
pre_close DECIMAL(10,2)

-- 复权价格: DECIMAL(10,4) - 4位小数（需要更高精度）
adj_close DECIMAL(10,4)   -- 复权价格
adj_factor DECIMAL(10,6)  -- 复权因子（需要6位）

-- 成交量: BIGINT - 整数
volume BIGINT             -- 单位：手（100股）

-- 成交额: DECIMAL(18,2) - 2位小数
amount DECIMAL(18,2)      -- 单位：元，最高 9999万亿

-- 换手率/涨跌幅: DECIMAL(8,2) - 2位小数（百分比）
turnover_rate DECIMAL(8,2)    -- 0.00% ~ 999,999.99%
change_pct DECIMAL(8,2)       -- -99.99% ~ +999.99%

-- VWAP: DECIMAL(10,2) - 2位小数
vwap DECIMAL(10,2)

-- 市值: DECIMAL(20,2) - 2位小数
market_cap DECIMAL(20,2)      -- 单位：元，支持百万亿级别
```

### 美股市场 (stock_us)

```sql
-- 价格类: DECIMAL(12,2) - 2位小数（美股价格可能很高）
open DECIMAL(12,2)        -- 最高 9,999,999,999.99 (99亿美元)
high DECIMAL(12,2)
low DECIMAL(12,2)
close DECIMAL(12,2)

-- 复权价格: DECIMAL(12,4)
adj_close DECIMAL(12,4)
adj_factor DECIMAL(10,6)

-- 成交量: BIGINT
volume BIGINT             -- 单位：股

-- 成交额: DECIMAL(20,2)
amount DECIMAL(20,2)      -- 单位：美元
```

### 加密货币市场 (crypto)

```sql
-- 价格类: DECIMAL(18,8) - 8位小数（加密货币可能很小）
open DECIMAL(18,8)        -- 支持 0.00000001 到 9,999,999,999.99999999
high DECIMAL(18,8)        -- 例如：BTC: 43250.12345678
low DECIMAL(18,8)         --      SHIB: 0.00001234
close DECIMAL(18,8)

-- 成交量: DECIMAL(24,8)
volume DECIMAL(24,8)      -- 加密货币成交量可能有小数

-- 成交额: DECIMAL(24,2)
amount DECIMAL(24,2)      -- 单位：USDT/USD
```

### 期货市场 (futures)

```sql
-- 价格类: DECIMAL(12,2) - 2位小数
open DECIMAL(12,2)
high DECIMAL(12,2)
low DECIMAL(12,2)
close DECIMAL(12,2)

-- 成交量: BIGINT
volume BIGINT             -- 单位：手

-- 持仓量: BIGINT
open_interest BIGINT      -- 单位：手

-- 成交额: DECIMAL(20,2)
amount DECIMAL(20,2)
```

---

## 🔧 实施修改

### 修改位置

#### 1. core/asset_database_manager.py

```python
def _initialize_table_schemas(self) -> Dict[str, str]:
    return {
        'historical_kline_data': """
            CREATE TABLE IF NOT EXISTS historical_kline_data (
                symbol VARCHAR NOT NULL,
                data_source VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                frequency VARCHAR NOT NULL DEFAULT '1d',
                
                -- ✅ 基础OHLCV字段：2位小数（A股标准）
                open DECIMAL(10,2) NOT NULL,
                high DECIMAL(10,2) NOT NULL,
                low DECIMAL(10,2) NOT NULL,
                close DECIMAL(10,2) NOT NULL,
                volume BIGINT DEFAULT 0,           -- 整数
                amount DECIMAL(18,2) DEFAULT 0,    -- 2位小数
                
                -- ✅ 扩展交易数据
                turnover DECIMAL(18,2) DEFAULT 0,      -- 2位小数
                adj_close DECIMAL(10,4),               -- 4位小数（复权需要）
                adj_factor DECIMAL(10,6) DEFAULT 1.0,  -- 6位小数（因子）
                turnover_rate DECIMAL(8,2),            -- 2位小数（百分比）
                vwap DECIMAL(10,2),                    -- 2位小数
                
                -- ✅ 涨跌数据
                change DECIMAL(10,2),                  -- 2位小数
                change_pct DECIMAL(8,2),               -- 2位小数（百分比）
                
                -- 元数据（不再存储name/market）
                -- name VARCHAR,          -- ❌ 移除
                -- market VARCHAR,        -- ❌ 移除
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                PRIMARY KEY (symbol, data_source, timestamp, frequency)
            )
        """,
        
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
                
                -- ✅ 股本信息（使用BIGINT，单位：股）
                total_shares BIGINT,
                circulating_shares BIGINT,
                currency VARCHAR DEFAULT 'CNY',
                
                -- 加密货币/期货特有
                base_currency VARCHAR,
                quote_currency VARCHAR,
                contract_type VARCHAR,
                
                -- ✅ 数据源信息
                data_sources VARCHAR,              -- JSON字符串
                primary_data_source VARCHAR,
                last_update_source VARCHAR,
                
                -- ✅ 元数据管理
                metadata_version INTEGER DEFAULT 1,
                data_quality_score DECIMAL(3,2),   -- 0.00 ~ 1.00
                last_verified TIMESTAMP,
                
                -- 扩展字段
                tags VARCHAR,                      -- JSON字符串
                attributes VARCHAR,                -- JSON字符串
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
    }
```

#### 2. 动态精度（按资产类型）

```python
def get_precision_config(asset_type: AssetType) -> Dict[str, int]:
    """
    获取资产类型对应的精度配置
    
    Returns:
        Dict[str, int]: 字段名 -> 小数位数
    """
    if asset_type in [AssetType.STOCK, AssetType.STOCK_A, AssetType.STOCK_HK]:
        return {
            'price': 2,       # 价格：2位
            'adj_price': 4,   # 复权价格：4位
            'adj_factor': 6,  # 复权因子：6位
            'amount': 2,      # 成交额：2位
            'percentage': 2,  # 百分比：2位
        }
    elif asset_type == AssetType.STOCK_US:
        return {
            'price': 2,
            'adj_price': 4,
            'adj_factor': 6,
            'amount': 2,
            'percentage': 2,
        }
    elif asset_type == AssetType.CRYPTO:
        return {
            'price': 8,       # 加密货币：8位
            'adj_price': 8,
            'adj_factor': 8,
            'amount': 2,
            'percentage': 2,
            'volume': 8,      # 加密货币成交量可能有小数
        }
    elif asset_type == AssetType.FUTURES:
        return {
            'price': 2,
            'adj_price': 4,
            'adj_factor': 6,
            'amount': 2,
            'percentage': 2,
        }
    else:
        # 默认配置
        return {
            'price': 2,
            'adj_price': 4,
            'adj_factor': 6,
            'amount': 2,
            'percentage': 2,
        }
```

---

## ✅ 精度处理最佳实践

### Python代码中的处理

```python
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP

def round_financial_data(df: pd.DataFrame, asset_type: AssetType) -> pd.DataFrame:
    """
    按照金融标准精度处理DataFrame
    
    Args:
        df: 原始数据
        asset_type: 资产类型
        
    Returns:
        精度处理后的数据
    """
    precision_config = get_precision_config(asset_type)
    
    # 价格类字段
    price_fields = ['open', 'high', 'low', 'close', 'pre_close', 'vwap']
    for field in price_fields:
        if field in df.columns:
            df[field] = df[field].round(precision_config['price'])
    
    # 复权价格
    if 'adj_close' in df.columns:
        df['adj_close'] = df[adj_close'].round(precision_config['adj_price'])
    
    # 复权因子
    if 'adj_factor' in df.columns:
        df['adj_factor'] = df['adj_factor'].round(precision_config['adj_factor'])
    
    # 成交额
    if 'amount' in df.columns:
        df['amount'] = df['amount'].round(precision_config['amount'])
    
    # 换手率、涨跌幅
    percentage_fields = ['turnover_rate', 'change_pct']
    for field in percentage_fields:
        if field in df.columns:
            df[field] = df[field].round(precision_config['percentage'])
    
    # 成交量：转整数（除了加密货币）
    if 'volume' in df.columns:
        if asset_type == AssetType.CRYPTO:
            df['volume'] = df['volume'].round(precision_config.get('volume', 8))
        else:
            df['volume'] = df['volume'].astype('Int64')  # 可空整数类型
    
    return df
```

### 存储时的精度控制

```python
# 在保存到DuckDB前，统一处理精度
df_to_save = round_financial_data(raw_df, asset_type)

# DuckDB的DECIMAL类型会自动处理精度
# 例如：DECIMAL(10,2) 会自动将 10.123456 存储为 10.12
```

---

## 🎯 精度验证

### 测试用例

```python
def test_price_precision():
    """测试价格精度"""
    # A股价格
    price = 10.123456
    rounded = round(price, 2)
    assert rounded == 10.12
    
    # 复权价格
    adj_price = 10.123456
    rounded_adj = round(adj_price, 4)
    assert rounded_adj == 10.1235
    
    # 复权因子
    adj_factor = 1.123456789
    rounded_factor = round(adj_factor, 6)
    assert rounded_factor == 1.123457

def test_crypto_precision():
    """测试加密货币精度"""
    # BTC价格
    btc_price = 43250.12345678
    rounded = round(btc_price, 8)
    assert rounded == 43250.12345678
    
    # SHIB价格
    shib_price = 0.000012345678
    rounded = round(shib_price, 8)
    assert rounded == 0.00001235
```

---

## 📝 总结

### 关键决策

1. **A股使用2位小数** - 符合行业标准
2. **复权数据使用4-6位** - 保证计算精度
3. **加密货币使用8位** - 支持小额币种
4. **成交量使用整数** - 除了加密货币
5. **避免过高精度** - 节省存储，提高性能

### 存储空间对比

```
高精度 DECIMAL(18,6)：9字节
标准精度 DECIMAL(10,2)：5字节

3000股票 × 2500条 × 5字段 = 37,500,000条记录
节省：37,500,000 × 4字节 = 150MB
```

---

**状态**: ✅ 精度标准已定义  
**下一步**: 修改数据库表结构和数据处理代码

