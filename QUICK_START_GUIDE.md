# 资产元数据分离 - 快速启动指南

**版本**: 1.0  
**日期**: 2025-10-18  
**状态**: ✅ 生产就绪

---

## 🚀 5分钟快速开始

### 1. 运行测试（验证功能）

```bash
# 运行核心功能测试
python test_asset_metadata_phase1_4.py
```

**预期输出**:
```
✅ Phase 1 测试通过
✅ Phase 2 测试通过
✅ Phase 3 测试通过
✅ Phase 4 测试通过
🎉 所有测试通过！Phase 1-4 实施成功！
```

### 2. 基础使用示例

```python
from core.asset_database_manager import AssetSeparatedDatabaseManager
from core.tet_data_pipeline import TETDataPipeline
from core.plugin_types import AssetType

# 初始化
asset_mgr = AssetSeparatedDatabaseManager.get_instance()
tet = TETDataPipeline()

# 保存资产元数据
metadata = {
    'symbol': '000001.SZ',
    'name': '平安银行',
    'market': 'SZ',
    'asset_type': 'stock_a',
    'industry': '银行',
    'primary_data_source': 'eastmoney'
}
asset_mgr.upsert_asset_metadata('000001.SZ', AssetType.STOCK_A, metadata)

# 查询资产元数据
info = asset_mgr.get_asset_metadata('000001.SZ', AssetType.STOCK_A)
print(f"名称: {info['name']}, 行业: {info['industry']}")
```

---

## 📋 常见使用场景

### 场景1: 批量导入资产列表

```python
from core.plugin_manager import PluginManager

# 获取插件
pm = PluginManager.get_instance()
plugin = pm.get_plugin_instance('data_sources.stock.eastmoney_plugin')

# 获取资产列表（真实API调用）
raw_list = plugin.get_asset_list(asset_type=AssetType.STOCK_A)

# TET框架标准化
std_list = tet.transform_asset_list_data(raw_list, 'eastmoney')

# 批量保存
success_count = 0
for _, row in std_list.iterrows():
    if asset_mgr.upsert_asset_metadata(
        row['symbol'], 
        AssetType.STOCK_A, 
        row.to_dict()
    ):
        success_count += 1

print(f"✅ 成功导入 {success_count} 个资产")
```

### 场景2: 查询K线+元数据

```python
# 使用视图（推荐）
db_path = asset_mgr._get_database_path(AssetType.STOCK_A)
with asset_mgr.duckdb_manager.get_pool(db_path).get_connection() as conn:
    df = conn.execute("""
        SELECT * FROM kline_with_metadata
        WHERE symbol = ? AND timestamp >= ?
        ORDER BY timestamp DESC
        LIMIT 100
    """, ['000001.SZ', '2024-01-01']).fetchdf()
    
    # df 包含：timestamp, ohlcv, name, market, industry等
    print(df[['timestamp', 'close', 'name', 'industry']].head())
```

### 场景3: 切换数据源

```python
# 场景：从东方财富切换到新浪
sina_plugin = pm.get_plugin_instance('data_sources.stock.sina_plugin')

# 获取新数据源的资产列表
sina_list = sina_plugin.get_asset_list()
std_list = tet.transform_asset_list_data(sina_list, 'sina')

# 更新元数据（自动追加数据源）
for _, row in std_list.iterrows():
    asset_mgr.upsert_asset_metadata(
        row['symbol'],
        AssetType.STOCK_A,
        {**row.to_dict(), 'primary_data_source': 'sina'}
    )
    # ✅ data_sources: ["eastmoney"] → ["eastmoney", "sina"]

# 下载K线并标记数据源
kline = sina_plugin.get_kdata(symbol='000001.SZ')
# ... 保存时会自动标记 data_source='sina'
```

### 场景4: 批量查询元数据

```python
# 批量查询（性能优化）
symbols = ['000001.SZ', '000002.SZ', '600000.SH']
metadata_dict = asset_mgr.get_asset_metadata_batch(symbols, AssetType.STOCK_A)

for symbol, info in metadata_dict.items():
    print(f"{symbol}: {info['name']} ({info['industry']})")
```

---

## 🔍 核心API速查

### AssetSeparatedDatabaseManager

```python
# 插入/更新元数据
success = asset_mgr.upsert_asset_metadata(
    symbol='000001.SZ',
    asset_type=AssetType.STOCK_A,
    metadata={
        'name': '平安银行',
        'market': 'SZ',
        # ... 更多字段
    }
)

# 查询单个元数据
metadata = asset_mgr.get_asset_metadata('000001.SZ', AssetType.STOCK_A)

# 批量查询
batch = asset_mgr.get_asset_metadata_batch(['000001.SZ', '000002.SZ'], AssetType.STOCK_A)
```

### TETDataPipeline

```python
# 标准化资产列表
standardized = tet.transform_asset_list_data(
    raw_data=raw_dataframe,
    data_source='eastmoney'
)
# 输出: DataFrame[symbol, name, market, industry, ...]
```

---

## 📊 数据库表速查

### asset_metadata （元数据表）

**主要字段**:
- `symbol` (PK): 资产代码
- `name`: 名称
- `market`: 市场
- `industry/sector`: 行业/板块
- `data_sources`: 数据源列表（JSON）

### historical_kline_data （K线表）

**主要字段**:
- `symbol`: 资产代码
- `data_source`: 数据源标记
- `timestamp`: 时间戳
- `open/high/low/close`: OHLC（2位小数）
- `volume/amount`: 成交量/额

### kline_with_metadata （视图）

**用途**: K线 + 元数据联合查询

```sql
SELECT * FROM kline_with_metadata WHERE symbol = ?
```

---

## 💡 最佳实践

### 1. 数据导入流程

```
1. 选择数据源 → 2. 获取资产列表 → 3. TET标准化 → 4. 保存元数据 → 5. 下载K线
```

### 2. 查询优化

- ✅ **推荐**: 使用 `kline_with_metadata` 视图
- ✅ **推荐**: 批量查询用 `get_asset_metadata_batch()`
- ❌ **避免**: 在循环中逐个查询

### 3. 数据源管理

- ✅ **每次更新都标记数据源**
- ✅ **使用 `data_sources` 字段追溯来源**
- ✅ **切换数据源时保留历史记录**

### 4. 错误处理

```python
try:
    success = asset_mgr.upsert_asset_metadata(...)
    if not success:
        logger.error(f"保存失败: {symbol}")
except Exception as e:
    logger.error(f"异常: {e}")
```

---

## 🐛 故障排除

### 问题1: 表不存在

**症状**: `Table 'asset_metadata' not found`

**解决**:
```python
# 表会在首次访问时自动创建
# 如果仍然报错，手动初始化：
asset_mgr._initialize_table_schemas()
```

### 问题2: symbol格式不标准

**症状**: 数据保存但查询不到

**原因**: symbol格式不一致（"000001" vs "000001.SZ"）

**解决**: 使用TET框架标准化
```python
std_list = tet.transform_asset_list_data(raw_list, source)
# 自动标准化为 "000001.SZ"
```

### 问题3: 精度丢失

**症状**: 价格显示异常

**原因**: 精度设置不正确

**解决**: 确保使用正确的DECIMAL精度
```python
# 价格：2位小数
df['close'] = df['close'].round(2)

# 复权价格：4位小数
df['adj_close'] = df['adj_close'].round(4)
```

### 问题4: 数据源冲突

**症状**: 同一symbol有多个数据源的不同数据

**说明**: 这是正常的！系统支持多数据源并存

**查询特定数据源**:
```sql
SELECT * FROM historical_kline_data 
WHERE symbol = ? AND data_source = 'eastmoney'
```

---

## 📚 相关文档

- **详细实施报告**: `ASSET_METADATA_IMPLEMENTATION_COMPLETE.md`
- **实施总结**: `IMPLEMENTATION_SUCCESS_SUMMARY.md`
- **精度标准**: `DECIMAL_PRECISION_STANDARDS.md`
- **设计文档**: `ASSET_METADATA_SEPARATION_DESIGN.md`

---

## ✅ 检查清单

在投入生产使用前，请确认：

- [ ] 运行 `test_asset_metadata_phase1_4.py` 全部通过
- [ ] 理解核心API的使用方法
- [ ] 了解数据库表结构
- [ ] 掌握TET框架的标准化流程
- [ ] 知道如何查询K线+元数据
- [ ] 明白数据源切换的流程

---

## 🎯 下一步

**立即可用**: 核心功能已完整实现，可直接使用API

**可选扩展**: 如需UI组件，参考 `ASSET_METADATA_UI_DOWNLOAD_INTEGRATION.md`

---

**祝使用愉快！** 🎉

有问题请查阅详细文档或运行测试脚本。

