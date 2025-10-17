# 数据库使用情况完整分析报告

## 🔍 关键发现

### 1. data/main.duckdb - **空数据库，未实际使用**

```
路径: data/main.duckdb
大小: 12KB (0.01MB)
修改时间: 2025-10-09 22:19:26
状态: ⚠️ 空数据库（无表）
代码引用: 1处（仅在 DatabaseService 配置中）
```

**结论**：
- ❌ **完全未使用**：数据库为空，没有任何表
- ❌ **配置无效**：虽然在 `database_service.py` 中配置了，但从未被实际使用
- ✅ **可以安全删除**

### 2. stock_data.duckdb vs stock_a_data.duckdb - **功能相同，按资产类型分类**

#### stock_data.duckdb（股票数据）

```
路径: data/databases/stock/stock_data.duckdb
大小: 3.51MB
表: 6个
核心表: stock_kline
记录数: 4,508条
数据范围: 2024-05-12 ~ 2025-10-13
用途: 存储通用股票数据（如美股 AAPL.US）
```

**表结构**：
1. ✅ `stock_kline` - **4,508条记录**，核心K线数据
2. ✅ `metadata` - 3条元数据记录
3. ⚠️ `historical_kline_data` - 0条（未使用）
4. ⚠️ `data_source_records` - 0条（未使用）
5. ⚠️ `data_quality_monitor` - 0条（未使用）
6. ⚠️ `unified_best_quality_kline` - 视图（依赖未使用的表）

#### stock_a_data.duckdb（A股数据）

```
路径: data/databases/stock_a/stock_a_data.duckdb
大小: 6.76MB
表: 5个
核心表: stock_a_kline
记录数: 10,703条
数据范围: 2024-05-12 ~ 2025-09-24
用途: 存储A股数据（如 000001.SZ）
```

**表结构**：
1. ✅ `stock_a_kline` - **10,703条记录**，A股K线数据
2. ✅ `metadata` - 3条元数据记录
3. ⚠️ `data_quality_monitor` - 0条（未使用）
4. ⚠️ `data_source_records` - 0条（未使用）
5. ⚠️ `unified_best_quality_kline` - 视图（定义错误）

**关键区别**：

| 特性 | stock_data.duckdb | stock_a_data.duckdb |
|-----|------------------|---------------------|
| **存储内容** | 通用股票（美股、港股等） | A股专用 |
| **表名** | `stock_kline` | `stock_a_kline` |
| **数据量** | 4,508条 | 10,703条（2.4倍） |
| **资产类型** | `AssetType.STOCK` | `AssetType.STOCK_A` |
| **目录结构** | `db/databases/stock/` | `db/databases/stock_a/` |
| **路由逻辑** | `AssetSeparatedDatabaseManager` 根据资产类型自动路由 |

### 3. db/kline_stock.duckdb - **空数据库，遗留代码**

```
路径: db/kline_stock.duckdb
大小: 2.01MB
表: 9个（全部为空）
记录数: 0条
状态: ⚠️ 有表结构但无数据
```

**结论**：
- ❌ **遗留数据库**：所有9个表都是空的
- ❌ **硬编码引用**：代码中有多处硬编码 `"db/kline_stock.duckdb"`
- ⚠️ **需要迁移**：将硬编码改为使用 `AssetSeparatedDatabaseManager`

## 📊 完整数据库清单

### A. 有效数据库（3个，11.8MB）

| 数据库 | 大小 | 表数 | 记录数 | 用途 | 状态 |
|-------|------|------|--------|------|------|
| `db/factorweave_analytics.duckdb` | 8.01MB | 13 | ~17条 | 分析数据库 | ✅ **核心** |
| `data/databases/stock/stock_data.duckdb` | 3.51MB | 6 | 4,511 | 股票数据 | ✅ **核心** |
| `data/databases/stock_a/stock_a_data.duckdb` | 6.76MB | 5 | 10,706 | A股数据 | ✅ **核心** |

### B. 空/未使用数据库（3个，2.04MB）

| 数据库 | 大小 | 状态 | 建议 |
|-------|------|------|------|
| `data/main.duckdb` | 12KB | ⚠️ 完全空 | ❌ **删除** |
| `data/analytics.duckdb` | 12KB | ⚠️ 完全空 | ❌ **删除** |
| `db/kline_stock.duckdb` | 2.01MB | ⚠️ 有表无数据 | ❌ **删除** |

### C. 测试数据库（40+个，15MB+）

见之前的分析报告，全部可删除。

## 🔧 调用链分析

### 1. AssetSeparatedDatabaseManager 的路由逻辑

```python
# core/asset_database_manager.py:265-270
def _get_database_path(self, asset_type: AssetType) -> str:
    base_path = Path(self.config.base_path)  # 默认: "data/databases"
    asset_dir = base_path / asset_type.value.lower()  # "stock" 或 "stock_a"
    db_file = asset_dir / f"{asset_type.value.lower()}_data.duckdb"
    return str(db_file)

# 示例：
# AssetType.STOCK → data/databases/stock/stock_data.duckdb
# AssetType.STOCK_A → data/databases/stock_a/stock_a_data.duckdb
```

### 2. 资产类型识别逻辑

```python
# core/asset_type_identifier.py:378-386
database_mapping = {
    AssetType.STOCK: "stock_data.duckdb",     # 通用股票
    AssetType.STOCK_A: "stock_data.duckdb",   # A股（注意：文件名相同！）
    AssetType.STOCK_B: "stock_data.duckdb",
    # ...
}

# ⚠️ 问题：映射中都是 "stock_data.duckdb"
# ✅ 实际使用：通过目录区分（stock/ 和 stock_a/）
```

**真实路径生成**：
1. 识别资产类型：`000001.SZ` → `AssetType.STOCK_A`
2. 生成目录：`data/databases/stock_a/`
3. 生成文件名：`stock_a_data.duckdb`（从 `asset_type.value.lower()` 生成）
4. 最终路径：`data/databases/stock_a/stock_a_data.duckdb`

### 3. 硬编码路径问题（需要修复）

#### 问题代码1：UnifiedDataManager

```python
# core/services/unified_data_manager.py:818
database_path="db/kline_stock.duckdb"  # ❌ 硬编码

# 应改为：
asset_manager = AssetSeparatedDatabaseManager()
db_path = asset_manager.get_database_path(asset_type)
```

#### 问题代码2：ImportExecutionEngine

```python
# core/importdata/import_execution_engine.py:1906
db_path = "db/kline_stock.duckdb"  # ❌ 硬编码

# 应改为：使用 AssetSeparatedDatabaseManager
```

#### 问题代码3：DatabaseService

```python
# core/services/database_service.py:268
"main_duckdb": DatabaseConfig(
    db_path="data/main.duckdb",  # ❌ 未使用的空数据库
)

# 应删除此配置，或改为实际使用的数据库
```

## 🎯 修正后的迁移方案

### 方案：统一到 db/ 目录

```
db/
  ├── 核心系统数据库
  │   ├── factorweave_analytics.duckdb     # 分析数据库（已存在）
  │   └── factorweave_system.sqlite        # 系统配置（已存在）
  │
  ├── 统一数据存储（保留）
  │   ├── unified_fundamental_data.duckdb
  │   ├── unified_kline_data.duckdb
  │   ├── unified_macro_data.duckdb
  │   ├── unified_metadata.duckdb
  │   └── unified_realtime_data.duckdb
  │
  └── 资产分类存储（从 data/ 迁移）
      └── databases/
          ├── stock/
          │   └── stock_data.duckdb        # 从 data/databases/stock/ 迁移
          └── stock_a/
              └── stock_a_data.duckdb      # 从 data/databases/stock_a/ 迁移
```

### 删除的数据库（3个，2.04MB）

1. ❌ `data/main.duckdb` - 空数据库
2. ❌ `data/analytics.duckdb` - 空数据库
3. ❌ `db/kline_stock.duckdb` - 空数据库（有表但无数据）

### 需要修改的代码（3个文件）

| 文件 | 修改内容 | 原因 |
|-----|---------|------|
| `core/asset_database_manager.py` | `base_path: "data/databases"` → `"db/databases"` | 统一路径 |
| `core/services/unified_data_manager.py` | 移除硬编码 `"db/kline_stock.duckdb"` | 使用 `AssetSeparatedDatabaseManager` |
| `core/importdata/import_execution_engine.py` | 移除硬编码 `"db/kline_stock.duckdb"` | 使用 `AssetSeparatedDatabaseManager` |
| `core/services/database_service.py` | 删除 `main_duckdb` 配置或改为实际使用的数据库 | 清理未使用配置 |

## 📝 最终建议

### 立即执行（低风险）

1. **删除空数据库**（3个，2.04MB）
   ```bash
   rm data/main.duckdb
   rm data/analytics.duckdb
   rm db/kline_stock.duckdb
   ```

2. **删除测试文件**（40+个，15MB+）
   ```bash
   python cleanup_invalid_databases.py
   ```

3. **迁移有效数据**（2个数据库，10.27MB）
   ```bash
   # 迁移 stock_data.duckdb
   mkdir -p db/databases/stock
   mv data/databases/stock/stock_data.duckdb db/databases/stock/
   
   # 迁移 stock_a_data.duckdb
   mkdir -p db/databases/stock_a
   mv data/databases/stock_a/stock_a_data.duckdb db/databases/stock_a/
   ```

4. **更新配置**
   ```python
   # core/asset_database_manager.py
   base_path: str = "db/databases"  # 从 "data/databases" 改为 "db/databases"
   ```

5. **修复硬编码**（3处）
   - `unified_data_manager.py` - 使用 `AssetSeparatedDatabaseManager`
   - `import_execution_engine.py` - 使用 `AssetSeparatedDatabaseManager`
   - `database_service.py` - 删除 `main_duckdb` 配置

### 不需要迁移

1. ✅ `db/factorweave_analytics.duckdb` - 已经在正确位置
2. ✅ `db/unified_*.duckdb` - 已经在正确位置

## 🔍 回答用户的3个问题

### Q1: data/main.duckdb 有在使用吗？

**A: 没有在使用！**

证据：
- ❌ 数据库完全为空（无表）
- ❌ 代码中0处实际调用
- ⚠️ 仅在 `database_service.py` 中有配置声明，但从未被实际使用
- ✅ **可以安全删除**

### Q2: stock_data.duckdb 和 stock_a_data.duckdb 有什么区别？

**A: 按资产类型分类存储，表名和用途不同**

| 区别 | stock_data.duckdb | stock_a_data.duckdb |
|-----|------------------|---------------------|
| **存储内容** | 通用股票（美股、港股等） | A股专用 |
| **核心表名** | `stock_kline` | `stock_a_kline` |
| **数据量** | 4,508条 | 10,703条（2.4倍） |
| **示例代码** | `AAPL.US` | `000001.SZ` |
| **路由依据** | `AssetType.STOCK` | `AssetType.STOCK_A` |

**设计目的**：
- 按资产类型分库存储，提高查询效率
- 避免单表过大
- 支持不同资产类型的独立管理

### Q3: 是否有遗漏的数据库？

**A: 已全面检查，发现3个额外问题**

1. ❌ **db/kline_stock.duckdb** - 空数据库（有表无数据）
   - 大小：2.01MB
   - 9个表全部为空
   - 代码中有硬编码引用
   - **需要删除并修复硬编码**

2. ❌ **data/analytics.duckdb** - 空数据库
   - 大小：12KB
   - 完全为空
   - **可以安全删除**

3. ⚠️ **硬编码路径问题** - 3处需要修复
   - `unified_data_manager.py`
   - `import_execution_engine.py`
   - `database_service.py`

## 📊 空间回收统计

| 类别 | 文件数 | 大小 | 操作 |
|-----|--------|------|------|
| 空数据库 | 3 | 2.04MB | ❌ 删除 |
| 测试文件 | 40+ | 15MB+ | ❌ 删除 |
| 有效数据 | 5 | 18.28MB | ✅ 保留/迁移 |
| **总回收** | **43+** | **17MB+** | **节省70%文件** |

---

**分析完成时间**：2025-10-14 00:17  
**分析方法**：代码扫描 + 数据库内容检查 + 调用链追踪  
**结论**：3个核心数据库有效，3个空数据库待删除，40+测试文件待清理

