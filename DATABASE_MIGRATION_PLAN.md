# 数据库统一到 db/ 目录迁移方案

## 📋 迁移目标

将所有数据库文件统一到 `db/` 目录，不再区分环境，简化管理。

## 🔄 迁移内容

### 1. 数据文件迁移（3个，9.03MB）

| 源路径 | 目标路径 | 大小 | 说明 |
|-------|---------|------|------|
| `data/main.duckdb` | `db/main.duckdb` | 12KB | 主数据库 |
| `data/databases/stock/stock_data.duckdb` | `db/databases/stock/stock_data.duckdb` | 2.26MB | 股票数据 |
| `data/databases/stock_a/stock_a_data.duckdb` | `db/databases/stock_a/stock_a_data.duckdb` | 6.76MB | A股数据 |

### 2. 清理无效文件（约40个，15MB+）

| 类别 | 文件 | 数量 | 说明 |
|-----|------|------|------|
| 测试数据库 | `db/test_*.duckdb` | 9 | ✅ 可删除 |
| 测试数据库 | `db/quick_*.duckdb` | 3 | ✅ 可删除 |
| 演示文件 | `db/demo_*.duckdb` | 1 | ✅ 可删除 |
| 验证文件 | `db/verify_*.duckdb` | 2 | ✅ 可删除 |
| 测试文件 | `db/complete_test.duckdb` | 1 | ✅ 可删除 |
| 测试文件 | `db/final_verification.duckdb` | 1 | ✅ 可删除 |
| 测试文件 | `db/performance_test.duckdb` | 1 | ✅ 可删除 |
| 空数据库 | `db/assets/*.duckdb` | 21 | ✅ 可删除 |
| 旧版本 | `data/analytics.duckdb` | 1 | ✅ 可删除 |

### 3. 代码路径更新（2个文件）

| 文件 | 修改内容 |
|-----|---------|
| `core/services/database_service.py` | `data/main.duckdb` → `db/main.duckdb` |
|  | `data/analytics.duckdb` → `db/factorweave_analytics.duckdb` |
| `core/asset_database_manager.py` | `base_path: "data/databases"` → `"db/databases"` |

## 📁 迁移后的目录结构

```
db/
  ├── 核心数据库
  │   ├── main.duckdb                      # 主数据库（新迁移）
  │   ├── factorweave_analytics.duckdb     # 分析数据库（现有）
  │   └── kline_stock.duckdb               # K线数据（现有）
  │
  ├── 统一数据存储
  │   ├── unified_fundamental_data.duckdb  # 基本面数据
  │   ├── unified_kline_data.duckdb        # 统一K线
  │   ├── unified_macro_data.duckdb        # 宏观数据
  │   ├── unified_metadata.duckdb          # 元数据
  │   └── unified_realtime_data.duckdb     # 实时数据
  │
  └── 资产分类存储（新迁移）
      └── databases/
          ├── stock/
          │   └── stock_data.duckdb        # 股票数据
          └── stock_a/
              └── stock_a_data.duckdb      # A股数据
```

## 🚀 执行步骤

### 步骤1：数据迁移（自动）

```bash
python migrate_to_db_directory.py
```

**操作内容：**
1. 迁移 `data/main.duckdb` → `db/main.duckdb`
2. 迁移 `data/databases/stock/*` → `db/databases/stock/*`
3. 迁移 `data/databases/stock_a/*` → `db/databases/stock_a/*`
4. 删除约40个无效测试文件
5. 清理空目录

**安全措施：**
- ✅ 如果目标文件已存在，会自动备份
- ✅ 迁移使用 `shutil.move()`，不会丢失数据
- ✅ 可以随时恢复备份文件

### 步骤2：代码路径更新（自动）

```bash
python update_database_paths.py
```

**修改文件：**
1. `core/services/database_service.py`
2. `core/asset_database_manager.py`

**修改内容：**
- 所有 `data/` 路径 → `db/` 路径
- 统一使用 `db/factorweave_analytics.duckdb`

### 步骤3：验证（手动）

```bash
# 1. 检查文件是否迁移成功
ls -lh db/main.duckdb
ls -lh db/databases/stock/stock_data.duckdb
ls -lh db/databases/stock_a/stock_a_data.duckdb

# 2. 启动应用验证
python main.py
```

## ⚠️ 注意事项

### 1. 备份建议

在执行迁移前，建议备份关键数据：

```bash
# 备份整个 data 目录
cp -r data data_backup_$(date +%Y%m%d_%H%M%S)

# 或者只备份关键文件
cp data/main.duckdb data/main.duckdb.backup
cp -r data/databases data/databases.backup
```

### 2. Git 版本控制

```bash
# 提交前检查修改
git status
git diff

# 提交迁移
git add .
git commit -m "refactor: 统一数据库到 db/ 目录

- 迁移 data/ 下的数据库文件到 db/
- 清理测试和空数据库文件（节省15MB）
- 更新代码中的数据库路径配置
- 简化目录结构，不再区分环境"
```

### 3. 可能的问题

**问题1：文件被占用**
```
解决：关闭所有正在运行的应用，再执行迁移
```

**问题2：路径更新遗漏**
```
解决：全局搜索 "data/databases" 和 "data/main.duckdb"
grep -r "data/databases" core/
grep -r "data/main.duckdb" core/
```

**问题3：数据库连接失败**
```
解决：检查 database_service.py 中的路径配置
```

## 📊 预期效果

### 空间优化

| 项目 | 迁移前 | 迁移后 | 变化 |
|-----|--------|--------|------|
| **文件数量** | 51个 | 12个 | -76% |
| **总大小** | 24.6MB | 17.6MB | -28% |
| **测试文件** | 18个 | 0个 | -100% |
| **目录数量** | 2个 | 1个 | -50% |

### 管理简化

| 方面 | 迁移前 | 迁移后 |
|-----|--------|--------|
| **路径规则** | 混乱（data/和db/混用） | 统一（只用db/） |
| **配置复杂度** | 高（需区分环境） | 低（单一配置） |
| **维护成本** | 高 | 低 |
| **新人理解** | 困难 | 简单 |

## ✅ 执行检查清单

- [ ] 1. 阅读并理解迁移方案
- [ ] 2. 备份关键数据文件
- [ ] 3. 关闭所有正在运行的应用
- [ ] 4. 执行 `python migrate_to_db_directory.py`
- [ ] 5. 输入 `yes` 确认迁移
- [ ] 6. 执行 `python update_database_paths.py`
- [ ] 7. 检查代码修改是否正确
- [ ] 8. 启动应用验证功能
- [ ] 9. 运行测试确保无问题
- [ ] 10. 提交 git 代码
- [ ] 11. 清理 `data/` 目录（可选）
- [ ] 12. 更新 `.gitignore`

## 🔄 回滚方案

如果迁移后出现问题，可以快速回滚：

```bash
# 1. 停止应用
pkill -f python

# 2. 恢复数据文件
mv db/main.duckdb.backup_* data/main.duckdb
mv db/databases/stock/stock_data.duckdb.backup_* data/databases/stock/stock_data.duckdb
# ... 其他文件

# 3. 恢复代码
git checkout core/services/database_service.py
git checkout core/asset_database_manager.py

# 4. 重启应用
python main.py
```

---

**准备完成，等待执行！**

输入 `yes` 执行迁移，或 `no` 取消操作。

