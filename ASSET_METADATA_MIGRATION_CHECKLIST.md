# 资产元数据分离 - 迁移检查清单

**日期**: 2025-10-19  
**状态**: 🔍 发现遗漏，需要修复  

---

## 🐛 发现的问题

### 问题：UnifiedDataManager 未更新表名

**日志信息**:
```
00:32:10.337 | INFO | core.services.unified_data_manager:_get_asset_list_from_duckdb:878 
- DuckDB中没有stock资产列表数据
```

**根本原因**:
`_get_asset_list_from_duckdb()` 方法仍在查询旧的表名：
- `stock_basic`
- `crypto_basic`
- `fund_basic`
- 等

而新设计使用统一的 **`asset_metadata`** 表。

---

## 📋 需要修改的地方

### 1. ✅ 已完成的修改

- [x] `core/asset_database_manager.py`
  - [x] 创建 `asset_metadata` 表
  - [x] 创建 `kline_with_metadata` 视图
  - [x] 修改 `historical_kline_data` 表精度
  - [x] 实现 `upsert_asset_metadata()` API
  - [x] 实现 `get_asset_metadata()` API
  - [x] 实现 `get_asset_metadata_batch()` API

- [x] `core/tet_data_pipeline.py`
  - [x] 添加 `transform_asset_list_data()` 方法
  - [x] 延迟导入修复

- [x] `core/importdata/import_execution_engine.py`
  - [x] 添加 `_enrich_kline_data_with_metadata()` 方法

### 2. ❌ 遗漏的修改

#### 核心问题：`core/services/unified_data_manager.py`

**位置**: `_get_asset_list_from_duckdb()` 方法（772-883行）

**当前实现**（错误）:
```python
table_mapping = {
    'stock': 'stock_basic',      # ❌ 旧表名
    'crypto': 'crypto_basic',    # ❌ 旧表名
    'fund': 'fund_basic',        # ❌ 旧表名
    'bond': 'bond_basic',        # ❌ 旧表名
    'index': 'index_basic',      # ❌ 旧表名
    'sector': 'sector_basic'     # ❌ 旧表名
}

query = f"""
    SELECT DISTINCT 
        symbol as code,
        name,
        market,
        industry,
        sector,
        list_date,         # ❌ 字段名不匹配
        status,            # ❌ 字段名不匹配
        '{asset_type}' as asset_type
    FROM {table_name}      # ❌ 使用旧表名
    WHERE status = 'L'     # ❌ 字段名不匹配
    ORDER BY symbol
"""
```

**应该修改为**（正确）:
```python
# 所有资产类型都使用同一个表
table_name = 'asset_metadata'  # ✅ 统一表名

query = f"""
    SELECT DISTINCT 
        symbol as code,
        name,
        market,
        industry,
        sector,
        listing_date as list_date,        # ✅ 新字段名
        listing_status as status,         # ✅ 新字段名
        asset_type
    FROM asset_metadata                   # ✅ 新表名
    WHERE listing_status = 'active'       # ✅ 新状态值
    AND asset_type = '{asset_type}'       # ✅ 过滤资产类型
    {f"AND market = '{market.upper()}'" if market and market != 'all' else ''}
    ORDER BY symbol
"""
```

---

## 🔍 全面检查清单

### A. 数据库表相关

- [x] `asset_metadata` 表是否已创建？
- [x] `kline_with_metadata` 视图是否已创建？
- [x] `historical_kline_data` 表精度是否已修改？
- [ ] **所有查询是否已更新为新表名？** ← 当前问题

### B. API方法相关

- [x] `upsert_asset_metadata()` 是否已实现？
- [x] `get_asset_metadata()` 是否已实现？
- [x] `get_asset_metadata_batch()` 是否已实现？
- [ ] **`get_asset_list()` 是否使用新表？** ← 当前问题

### C. 数据导入流程

- [x] TET框架是否支持资产列表标准化？
- [x] 导入引擎是否补全元数据字段？
- [ ] **资产列表是否保存到正确的表？** ← 需要验证

### D. 向后兼容

- [x] 旧代码是否可以通过视图访问？
- [ ] **查询方法是否正确路由？** ← 当前问题

---

## 🚀 修复方案

### 方案1: 完全迁移（推荐）

**修改**: `core/services/unified_data_manager.py:_get_asset_list_from_duckdb()`

**优点**:
- 彻底迁移到新架构
- 统一数据源
- 简化代码逻辑

**缺点**:
- 需要验证所有调用者
- 可能影响现有数据

### 方案2: 渐进迁移（保守）

**修改**: 
1. 先检查 `asset_metadata` 表是否存在
2. 存在则使用新表，否则降级到旧表
3. 逐步废弃旧表

**优点**:
- 向后兼容
- 渐进式迁移
- 降低风险

**缺点**:
- 代码更复杂
- 维护两套逻辑

---

## 📝 详细修复步骤

### Step 1: 修复 `_get_asset_list_from_duckdb()`

#### 1.1 更新表名映射

```python
# 旧代码（删除）
table_mapping = {
    'stock': 'stock_basic',
    'crypto': 'crypto_basic',
    # ...
}
table_name = table_mapping.get(asset_type, 'stock_basic')

# 新代码（替换）
# 所有资产类型统一使用asset_metadata表
table_name = 'asset_metadata'
```

#### 1.2 更新SQL查询

```python
# 旧字段映射 → 新字段映射
list_date     → listing_date
status        → listing_status
status = 'L'  → listing_status = 'active'
```

#### 1.3 添加资产类型过滤

```python
# 新增WHERE条件
WHERE asset_type = '{asset_type_value}'
```

### Step 2: 检查其他SQL查询

搜索所有包含表名的SQL：
- `stock_basic`
- `crypto_basic`
- `fund_basic`
- `kline_stock`
- `stock_kline`

### Step 3: 更新字段名引用

全局搜索并替换：
- `list_date` → `listing_date`
- `status = 'L'` → `listing_status = 'active'`

### Step 4: 测试验证

```python
# 测试资产列表查询
result = unified_manager.get_asset_list(asset_type='stock', market='SZ')
assert not result.empty, "应该返回数据"
assert 'code' in result.columns, "应该有code字段"
assert 'name' in result.columns, "应该有name字段"
```

---

## ⚠️ 潜在的其他遗漏

### 1. UI组件

**可能位置**:
- `gui/widgets/enhanced_ui/*.py`
- `gui/dialogs/*.py`

**检查项**:
- 资产列表显示是否正确
- 字段名是否匹配

### 2. 数据导入对话框

**可能位置**:
- `gui/widgets/enhanced_ui/data_download_dialog.py`
- `gui/widgets/enhanced_ui/history_data_dialog.py`

**检查项**:
- 资产列表来源是否正确
- 保存逻辑是否使用新API

### 3. 插件接口

**可能位置**:
- `plugins/data_sources/*_plugin.py`

**检查项**:
- `get_asset_list()` 返回格式
- 字段名是否标准化

### 4. 测试脚本

**可能位置**:
- `test_*.py`
- `verify_*.py`

**检查项**:
- 测试是否覆盖新功能
- Mock数据是否匹配新结构

---

## 🎯 优先级排序

### 🔴 P0 - 立即修复（影响核心功能）

1. **`unified_data_manager.py:_get_asset_list_from_duckdb()`**
   - 影响: 资产列表查询失败
   - 估时: 15分钟

### 🟡 P1 - 近期修复（影响用户体验）

2. **UI组件字段映射**
   - 影响: 显示可能异常
   - 估时: 30分钟

3. **数据导入对话框**
   - 影响: 导入流程可能失败
   - 估时: 30分钟

### 🟢 P2 - 计划修复（优化改进）

4. **测试脚本更新**
   - 影响: 测试覆盖不全
   - 估时: 1小时

5. **文档更新**
   - 影响: 文档与代码不一致
   - 估时: 30分钟

---

## ✅ 验证清单

修复完成后，运行以下验证：

- [ ] 单元测试通过：`python test_asset_metadata_phase1_4.py`
- [ ] 资产列表查询成功：`unified_manager.get_asset_list('stock')`
- [ ] 元数据查询成功：`asset_manager.get_asset_metadata('000001.SZ', AssetType.STOCK_A)`
- [ ] 数据导入成功：测试导入流程
- [ ] UI显示正常：启动main.py检查UI
- [ ] 日志无错误：检查logs目录

---

## 📚 相关文档

- `ASSET_METADATA_SEPARATION_DESIGN.md` - 设计方案
- `ASSET_METADATA_IMPLEMENTATION_COMPLETE.md` - 实施报告
- `AUTOMATED_TEST_FIX_REPORT.md` - 测试修复报告
- **本文档** - 迁移检查清单

---

**下一步**: 立即修复 `_get_asset_list_from_duckdb()` 方法

