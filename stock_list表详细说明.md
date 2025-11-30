# stock_list 表详细说明文档

## 📋 表的作用

`stock_list` 表是 **DuckDB 数据库中的核心基础表**，用于存储和管理股票基础信息列表。

### 主要功能

1. **股票快速检索** - 提供高性能的股票代码和名称查询
2. **市场分类** - 按市场（上海、深圳、北交所等）组织股票数据
3. **数据源缓存** - 缓存从各数据插件获取的股票列表，减少API调用
4. **UI展示支持** - 为左侧面板股票列表提供数据源
5. **数据完整性** - 记录股票的基本属性和更新时间

### 表结构

```sql
CREATE TABLE stock_list (
    code VARCHAR,           -- 股票代码 (如: "000001", "600000")
    name VARCHAR,           -- 股票名称 (如: "平安银行", "浦发银行")
    market VARCHAR,         -- 市场代码 (sh/sz/bj)
    asset_type VARCHAR,     -- 资产类型 (stock/index/etf等)
    update_time TIMESTAMP,  -- 更新时间
    market_filter VARCHAR   -- 市场筛选标记
)
```

## 🔄 创建和录入时机

### 1. 表创建时机

表在 **首次使用时自动创建**，通过以下路径：

```python
# 路径: core/services/enhanced_duckdb_data_downloader.py (行 452-461)
async def _store_stock_list_to_duckdb(self, data: pd.DataFrame, market: str):
    """存储股票列表到DuckDB"""
    db_path = self.db_paths['kline']
    table_name = "stock_list"
    
    # 确保表存在 - 如果不存在则自动创建
    await self.table_manager.ensure_table_exists(
        db_path, 'asset_list', 'enhanced_duckdb_downloader'
    )
```

**关键点**：
- 使用 `TableType.ASSET_LIST` 类型创建
- 由 `TableManager.ensure_table_exists()` 方法负责
- 第一次下载股票列表时自动触发

### 2. 数据录入时机

数据录入有 **三个主要触发场景**：

#### 场景 1: 手动更新股票池
```python
# 用户主动调用
await unified_data_manager.update_stock_universe(market='all')
```

#### 场景 2: 增量数据更新
```python
# 定时任务或用户触发
await enhanced_duckdb_downloader.incremental_update_all_data()
```

#### 场景 3: 初始化数据下载
```python
# 首次使用或数据重建
await enhanced_duckdb_downloader.download_stock_list(market='sh')
```

## 📊 录入逻辑详解

### 完整的数据流

```
1. 发起下载请求
   ↓
2. 通过TET插件框架获取数据
   ↓
3. 数据验证和清洗
   ↓
4. 确保表存在（自动创建）
   ↓
5. 写入DuckDB
   ↓
6. 记录更新时间
```

### 详细实现代码

```python
# 文件: core/services/enhanced_duckdb_data_downloader.py

async def download_stock_list(self, market: str = 'all', asset_type: AssetType = AssetType.STOCK):
    """下载股票列表到DuckDB"""
    
    # 1. 构建查询请求
    query = StandardQuery(
        symbol="",
        data_type=DataType.ASSET_LIST,  # 资产列表类型
        asset_type=asset_type,
        extra_params={'market': market}
    )
    
    # 2. 通过TET插件框架执行请求
    context = await self.uni_plugin_manager.create_request_context(query)
    data = await self.uni_plugin_manager.execute_data_request(context)
    
    # 3. 数据验证和清洗
    if data is not None and not data.empty:
        cleaned_data = self._validate_and_clean_stock_list(data)
        
        # 4. 存储到DuckDB
        await self._store_stock_list_to_duckdb(cleaned_data, market)
        
        return cleaned_data
```

### 数据清洗逻辑

```python
def _validate_and_clean_stock_list(self, data: pd.DataFrame) -> pd.DataFrame:
    """验证和清洗股票列表数据"""
    
    # 1. 确保必需字段存在
    required_columns = ['code', 'name']
    
    # 2. 字段映射和标准化
    column_mapping = {
        'ts_code': 'code',
        'symbol': 'code',
        'stock_name': 'name',
        # ...
    }
    
    # 3. 数据类型转换
    # 4. 去重和排序
    # 5. 添加默认值
    
    return cleaned_data
```

### 存储逻辑

```python
async def _store_stock_list_to_duckdb(self, data: pd.DataFrame, market: str):
    """存储股票列表到DuckDB"""
    
    # 1. 指定数据库路径
    db_path = self.db_paths['kline']  # 使用K线数据库
    table_name = "stock_list"
    
    # 2. 确保表存在
    await self.table_manager.ensure_table_exists(
        db_path, 'asset_list', 'enhanced_duckdb_downloader'
    )
    
    # 3. 添加元数据
    data['update_time'] = datetime.now()      # 更新时间
    data['market_filter'] = market            # 市场标记
    
    # 4. 插入数据（冲突时替换）
    result = self.duckdb_operations.insert_dataframe(
        database_path=db_path,
        table_name=table_name,
        dataframe=data,
        conflict_resolution='replace'  # 关键：替换策略
    )
    
    if result.get('success'):
        logger.debug(f"股票列表存储成功: {len(data)} 只股票")
```

## 🔍 查询使用

### 查询路径

```python
# 文件: core/ui/panels/left_panel.py (行 1318-1404)

def _query_stocks_from_duckdb(self, uni_manager, market=None, search_text=None):
    """从DuckDB查询股票数据"""
    
    # 构建查询条件
    query_conditions = []
    
    if market:
        market_mapping = {
            "上海": "sh",
            "深圳": "sz",
            "创业板": "sz",
            "科创板": "sh",
            "北交所": "bj"
        }
        db_market = market_mapping.get(market, market.lower())
        query_conditions.append(f"market = '{db_market}'")
    
    if search_text:
        query_conditions.append(
            f"(code LIKE '%{search_text}%' OR name LIKE '%{search_text}%')"
        )
    
    # 执行查询
    query = "SELECT code, name, market, asset_type, update_time FROM stock_list"
    if query_conditions:
        query += f" WHERE {' AND '.join(query_conditions)}"
    query += " ORDER BY code"
    
    result = duckdb_ops.query_data(table_name="stock_list", ...)
    return result.data if result.success else pd.DataFrame()
```

## ⚠️ 当前问题和解决方案

### 问题：表不存在错误

**原因**：
1. ❌ 表未被创建（没有调用过 `download_stock_list`）
2. ❌ 数据库文件路径不正确
3. ❌ 首次使用时未触发初始化

**现有的降级机制**：
```python
# 修复后的代码 (已完成)
if result and result.success and result.data is not None:
    return result.data
else:
    logger.debug("stock_list表不存在，使用备用数据源")
    return pd.DataFrame()  # 触发备用数据源
```

### 解决方案

#### 方案 1: 自动初始化（推荐）

在应用启动时自动下载股票列表：

```python
# 在 MainWindowCoordinator 或启动脚本中添加
async def _initialize_stock_data(self):
    """初始化股票数据"""
    try:
        # 下载所有市场的股票列表
        for market in ['sh', 'sz', 'bj']:
            await self.unified_data_manager.update_stock_universe(market=market)
        
        logger.info("股票列表初始化完成")
    except Exception as e:
        logger.warning(f"股票列表初始化失败: {e}")
```

#### 方案 2: 手动触发

提供UI按钮让用户主动更新：

```python
# 在数据导入界面添加按钮
async def on_update_stock_list_clicked(self):
    """更新股票列表按钮"""
    await self.unified_data_manager.update_stock_universe(market='all')
    self.show_message("股票列表更新完成")
```

#### 方案 3: 懒加载（当前实现）

首次查询失败时自动下载：

```python
def _get_stocks_from_database(self, search_text=None):
    # 1. 尝试查询DuckDB
    stocks = self._query_stocks_from_duckdb(...)
    
    # 2. 如果为空且表不存在，触发下载
    if stocks.empty:
        # 降级到其他数据源（FactorWeave-Quant、插件等）
        stocks = self._get_stocks_from_hikyuu()
    
    return stocks
```

## 📈 数据更新策略

### 推荐的更新策略

1. **应用启动时** - 检查表是否存在，不存在则创建并下载
2. **定时更新** - 每天凌晨更新一次（新股上市）
3. **手动更新** - 用户可主动触发更新
4. **增量更新** - 只更新变化的部分

### 示例：定时更新任务

```python
from PyQt5.QtCore import QTimer

class StockListUpdater:
    def __init__(self, unified_data_manager):
        self.data_manager = unified_data_manager
        
        # 每天凌晨3点更新
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stock_list)
        self.timer.start(24 * 60 * 60 * 1000)  # 24小时
    
    async def update_stock_list(self):
        """定时更新股票列表"""
        try:
            await self.data_manager.update_stock_universe(market='all')
            logger.info("股票列表定时更新完成")
        except Exception as e:
            logger.error(f"股票列表定时更新失败: {e}")
```

## 🎯 最佳实践

### 1. 初始化检查

```python
async def ensure_stock_list_exists(self):
    """确保股票列表存在"""
    # 检查表是否有数据
    result = await self.query_stock_count()
    
    if result == 0:
        logger.info("检测到stock_list为空，开始初始化...")
        await self.download_stock_list(market='all')
```

### 2. 错误处理

```python
try:
    stocks = await self.get_stocks_from_duckdb()
except TableNotExistError:
    logger.info("表不存在，自动创建并下载数据...")
    await self.download_stock_list()
    stocks = await self.get_stocks_from_duckdb()
```

### 3. 性能优化

```python
# 使用索引加速查询
await self.create_index('stock_list', ['code', 'market'])

# 分批插入大量数据
await self.batch_insert_stock_list(stocks, batch_size=1000)
```

## 📝 总结

| 项目 | 说明 |
|------|------|
| **表名** | `stock_list` |
| **数据库** | DuckDB (kline数据库) |
| **主要字段** | code, name, market, asset_type, update_time |
| **创建时机** | 首次调用 `download_stock_list()` 时自动创建 |
| **录入时机** | 手动更新、增量更新、初始化下载 |
| **数据来源** | TET插件框架（AKShare、东方财富等） |
| **查询用途** | 左侧面板股票列表、股票筛选、市场分类 |
| **更新策略** | 按需更新 + 定时更新（可选） |
| **降级机制** | 表不存在时自动切换到FactorWeave-Quant或其他数据源 |

## 🔗 相关文件

- `core/services/enhanced_duckdb_data_downloader.py` - 下载和存储逻辑
- `core/services/unified_data_manager.py` - 数据管理接口
- `core/ui/panels/left_panel.py` - 查询和使用
- `core/database/table_manager.py` - 表结构管理
- `core/database/duckdb_operations.py` - 数据库操作

## ✅ 当前状态

- ✅ 表结构定义完整
- ✅ 数据下载逻辑完善
- ✅ 查询接口健全
- ✅ 降级机制已实现
- ⚠️ 缺少自动初始化（建议添加）
- ⚠️ 缺少定时更新（可选功能）
