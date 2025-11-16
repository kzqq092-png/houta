# UnifiedDataManager 多资产类型支持文档

## 📋 概述

`UnifiedDataManager` 已全面支持6种资产类型的K线数据查询，通过资产分离数据库架构实现自动路由和质量优选。

---

## 🎯 支持的资产类型

| 资产类型 | AssetType枚举 | 数据库路径 | 说明 |
|---------|--------------|-----------|------|
| 股票 | `AssetType.STOCK_A` | `cache/duckdb/stock_a/stock_a_data.duckdb` | A股股票 |
| 加密货币 | `AssetType.CRYPTO` | `cache/duckdb/crypto/crypto_data.duckdb` | 比特币、以太坊等 |
| 期货 | `AssetType.FUTURES` | `cache/duckdb/futures/futures_data.duckdb` | 商品期货、股指期货 |
| 外汇 | `AssetType.FOREX` | `cache/duckdb/forex/forex_data.duckdb` | 主要货币对 |
| 指数 | `AssetType.INDEX` | `cache/duckdb/index/index_data.duckdb` | 上证指数、恒生指数 |
| 基金 | `AssetType.FUND` | `cache/duckdb/fund/fund_data.duckdb` | 公募基金、ETF |

---

## 🔧 核心API

### 1. request_data（异步）

```python
async def request_data(
    stock_code: str,                      # 资产代码
    data_type: str = 'kdata',             # 数据类型
    period: str = 'D',                    # 周期
    time_range: str = "最近1年",          # 时间范围
    asset_type: AssetType = AssetType.STOCK_A,  # ✅ 资产类型
    **kwargs
) -> Any
```

**使用示例：**

```python
# 查询股票数据
stock_data = await data_manager.request_data(
    stock_code='000001',
    data_type='kdata',
    asset_type=AssetType.STOCK_A
)

# 查询加密货币数据
crypto_data = await data_manager.request_data(
    stock_code='BTC-USD',
    data_type='kdata',
    asset_type=AssetType.CRYPTO
)

# 查询期货数据
futures_data = await data_manager.request_data(
    stock_code='IF2403',
    data_type='kdata',
    asset_type=AssetType.FUTURES
)
```

### 2. get_kdata（同步）

```python
def get_kdata(
    stock_code: str,                      # 资产代码
    period: str = 'D',                    # 周期
    count: int = 365,                     # 数据条数
    asset_type: AssetType = AssetType.STOCK_A  # ✅ 资产类型
) -> pd.DataFrame
```

**使用示例：**

```python
# 获取比特币日K线
btc_kline = data_manager.get_kdata(
    stock_code='BTC-USD',
    period='D',
    count=365,
    asset_type=AssetType.CRYPTO
)

# 获取外汇数据
eurusd_kline = data_manager.get_kdata(
    stock_code='EURUSD',
    period='60',  # 60分钟线
    count=1000,
    asset_type=AssetType.FOREX
)
```

---

## 🔄 数据流程

### 完整调用链

```
用户操作
  ↓
LeftPanel.current_asset_type = AssetType.CRYPTO  # 用户切换资产类型
  ↓
LeftPanel._async_select_stock()  # 选择资产
  ↓
data_manager.request_data(
    stock_code='BTC-USD',
    asset_type=AssetType.CRYPTO  # ✅ 传递资产类型
)
  ↓
_get_kdata(asset_type=AssetType.CRYPTO)
  ↓
get_kdata(asset_type=AssetType.CRYPTO)
  ↓
_get_kdata_from_duckdb(asset_type=AssetType.CRYPTO)
  ↓
asset_manager.get_database_path(AssetType.CRYPTO)
  ↓
返回: cache/duckdb/crypto/crypto_data.duckdb
  ↓
查询 unified_best_quality_kline 视图
  ↓
返回最优质量K线数据
```

---

## 🎨 左侧面板资产切换

### UI组件

左侧面板提供资产类型下拉选择器：

```python
# 用户界面
asset_type_combo = QComboBox()
asset_types = [
    ("股票 (Stock)", AssetType.STOCK_A),
    ("加密货币 (Crypto)", AssetType.CRYPTO),
    ("期货 (Futures)", AssetType.FUTURES),
    ("外汇 (Forex)", AssetType.FOREX),
    ("指数 (Index)", AssetType.INDEX),
    ("基金 (Fund)", AssetType.FUND)
]
```

### 切换流程

1. 用户在下拉框选择资产类型
2. 触发 `_on_asset_type_changed` 事件
3. 更新 `self.current_asset_type`
4. 调用 `_update_market_filters()` 更新市场过滤器
5. 调用 `_reload_asset_list()` 重新加载资产列表

---

## 💾 数据库架构

### 资产分离存储

每种资产类型使用独立的DuckDB数据库文件：

```
cache/duckdb/
├── stock_a/
│   └── stock_a_data.duckdb       # 股票数据
├── crypto/
│   └── crypto_data.duckdb        # 加密货币数据
├── futures/
│   └── futures_data.duckdb       # 期货数据
├── forex/
│   └── forex_data.duckdb         # 外汇数据
├── index/
│   └── index_data.duckdb         # 指数数据
└── fund/
    └── fund_data.duckdb          # 基金数据
```

### 视图结构

每个数据库都包含 `unified_best_quality_kline` 视图：

```sql
CREATE VIEW unified_best_quality_kline AS
WITH ranked_data AS (
    SELECT 
        hkd.*,
        dqm.quality_score,
        CASE 
            WHEN dqm.quality_score IS NOT NULL THEN dqm.quality_score
            WHEN hkd.data_source = 'tushare' THEN 65.0
            WHEN hkd.data_source = 'tongdaxin' THEN 60.0
            WHEN hkd.data_source = 'akshare' THEN 55.0
            ELSE 50.0
        END as effective_quality_score,
        ROW_NUMBER() OVER (
            PARTITION BY hkd.symbol, hkd.timestamp, hkd.frequency 
            ORDER BY effective_quality_score DESC, hkd.updated_at DESC
        ) as quality_rank
    FROM historical_kline_data hkd
    LEFT JOIN data_quality_monitor dqm 
        ON hkd.symbol = dqm.symbol 
        AND hkd.data_source = dqm.data_source 
        AND DATE(hkd.timestamp) = dqm.check_date
)
SELECT * FROM ranked_data WHERE quality_rank = 1
```

### 视图特性

1. ✅ **自动质量优选**：按数据源质量评分排序
2. ✅ **数据去重**：每个时间戳只保留最优记录
3. ✅ **实时评分**：LEFT JOIN data_quality_monitor获取最新评分
4. ✅ **优先级排序**：tushare (65.0) > tongdaxin (60.0) > akshare (55.0)
5. ✅ **最新优先**：相同质量评分时选择更新时间最新的

---

## 🔍 缓存机制

### 缓存键格式

```python
cache_key = f"kdata_{asset_type.value}_{stock_code}_{period}_{count}"
```

### 缓存隔离

不同资产类型的缓存键完全独立：

```python
# 股票缓存键
"kdata_stock_a_000001_D_365"

# 加密货币缓存键（同代码不同资产）
"kdata_crypto_BTC-USD_D_365"

# 指数缓存键（同代码不同资产）
"kdata_index_000001_D_365"
```

**优势**：避免不同资产类型之间的数据混淆。

---

## 🛡️ 向后兼容

### 默认参数

所有涉及的方法都使用 `asset_type: AssetType = AssetType.STOCK_A` 作为默认值：

```python
# 旧代码（不传asset_type）
data = await data_manager.request_data(stock_code='000001')
# ✅ 自动使用 AssetType.STOCK_A，行为与之前完全一致

# 新代码（传asset_type）
data = await data_manager.request_data(
    stock_code='BTC-USD',
    asset_type=AssetType.CRYPTO
)
# ✅ 自动路由到crypto数据库
```

---

## 📊 日志追踪

### 关键日志点

1. **请求数据**
   ```
   ✅ 请求数据：代码=BTC-USD, 类型=kdata, 周期=D, 时间范围=365天, 资产类型=crypto
   ```

2. **获取K线**
   ```
   ✅ 获取K线数据: BTC-USD, 周期=D, 数量=365, 资产类型=crypto
   ```

3. **DuckDB查询**
   ```
   ✅ 尝试从DuckDB获取K线数据: BTC-USD, period=D, count=365, asset_type=crypto
   ```

4. **视图查询**
   ```
   ✅ DuckDB视图查询（质量优选）: database=cache/duckdb/crypto/crypto_data.duckdb, symbol=BTC-USD, frequency=1d
   ```

5. **查询结果**
   ```
   ✅ DuckDB视图查询成功（质量优选）: BTC-USD, frequency=1d, 365 条记录
   ```

6. **缓存命中**
   ```
   ✅ 缓存命中: BTC-USD (crypto)
   ```

---

## 🧪 测试验证

### 运行测试脚本

```bash
python tests/test_multi_asset_support.py
```

### 测试内容

1. ✅ 数据库自动路由机制
2. ✅ 多资产类型K线查询
3. ✅ 缓存键隔离机制
4. ✅ 视图查询逻辑
5. ✅ 完整数据流追踪

---

## ⚠️ 注意事项

1. **数据库文件**：首次查询某资产类型时，如果数据库不存在会自动创建
2. **视图创建**：数据库初始化时会自动创建 `unified_best_quality_kline` 视图
3. **降级机制**：视图查询失败时自动降级到基础表 `historical_kline_data`
4. **数据导入**：需要使用ImportExecutionEngine导入对应资产类型的数据

---

## 🔗 相关文件

- `core/services/unified_data_manager.py` - 数据管理器主文件
- `core/ui/panels/left_panel.py` - 左侧资产选择面板
- `core/coordinators/main_window_coordinator.py` - 主窗口协调器
- `core/asset_database_manager.py` - 资产分离数据库管理器
- `core/plugin_types.py` - AssetType枚举定义

---

## 📞 技术支持

如遇问题，请检查：
1. 日志中的asset_type参数是否正确传递
2. 数据库路径是否正确路由
3. 视图是否成功创建
4. 数据是否已导入到对应数据库

---

**文档版本**: 1.0.0  
**最后更新**: 2025-11-06

