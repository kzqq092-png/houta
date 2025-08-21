# FactorWeave-Quant 系统重构清理计划

## 📋 执行概述

**执行时间**: 2024年12月19日  
**重构类型**: 系统名称变更 + 数据库架构重构 + 代码清理  
**目标**: HIkyuu-UI → FactorWeave-Quant，实施SQLite+DuckDB混合架构  
**原则**: 不保留兼容层，直接重构，彻底清理  

---

## 🎯 重构目标

### 1. 系统名称统一变更
- **旧名称**: HIkyuu-UI
- **新名称**: FactorWeave-Quant
- **影响范围**: 类名、文件名、配置、文档、数据库路径

### 2. 数据库架构重构
- **旧架构**: 纯SQLite架构
- **新架构**: SQLite(配置) + DuckDB(分析) 混合架构
- **清理原则**: 移除不使用的数据库，重组数据结构

### 3. 代码清理
- **移除**: 兼容层代码、废弃功能、冗余组件
- **重构**: 直接修改，不保留向后兼容
- **优化**: 统一命名规范，清理导入依赖

---

## 📊 数据库重构计划

### 🗑️ 需要删除的数据库

| 数据库文件 | 大小 | 删除原因 | 操作 |
|-----------|------|----------|------|
| `db/metrics.db` | 4.48GB | 用户确认不需要历史监控数据 | 直接删除 |
| `visualization/stock.db` | 0字节 | 空文件，无实际内容 | 直接删除 |

### 🔄 需要重命名的数据库

| 旧路径 | 新路径 | 用途 | 架构 |
|--------|--------|------|------|
| `db/hikyuu_system.db` | `db/factorweave_system.db` | 系统配置和元数据 | SQLite |
| `data/strategies.db` | `data/factorweave_strategies.db` | 策略定义 | SQLite |
| `visualization/block.db` | `visualization/factorweave_blocks.db` | 可视化配置 | SQLite |

### 🆕 需要创建的数据库

| 新路径 | 用途 | 架构 | 数据来源 |
|--------|------|------|----------|
| `analytics/factorweave_analytics.db` | 分析和回测数据 | DuckDB | 从SQLite迁移 |

### 📋 数据迁移映射

#### SQLite保留数据 (配置层)
```
factorweave_system.db
├── config                    # 系统配置
├── themes                    # 主题配置  
├── plugins                   # 插件注册
├── plugin_configs            # 插件配置
├── data_source              # 数据源配置
├── user_favorites           # 用户偏好
├── industry                 # 行业分类
├── market                   # 市场信息
├── indicators               # 指标定义 (仅定义)
├── strategies               # 策略定义 (仅定义)
├── algorithm_versions       # 算法版本 (仅定义)
├── pattern_info            # 形态信息 (仅定义)
└── ai_prediction_config    # AI配置
```

#### DuckDB迁移数据 (分析层)
```
factorweave_analytics.db
├── strategy_execution_results    # 策略执行结果
├── indicator_calculation_results # 指标计算结果  
├── pattern_recognition_results   # 形态识别结果
├── backtest_metrics_history     # 回测指标历史
├── backtest_alerts_history      # 回测预警历史
├── performance_metrics          # 性能指标
├── optimization_logs           # 优化日志
└── analysis_cache             # 分析缓存数据
```

---

## 🔧 代码重构计划

### 1. 主要类重命名

| 旧类名 | 新类名 | 文件位置 |
|--------|--------|----------|
| `HIkyuuUIApplication` | `FactorWeaveQuantApplication` | `main.py` |
| `HIkyuuQuickStart` | `FactorWeaveQuantLauncher` | `quick_start.py` |
| `HikyuuSignalAdapter` | `FactorWeaveSignalAdapter` | `plugins/strategies/` |
| `HikyuuStrategyPlugin` | `FactorWeaveStrategyPlugin` | `plugins/strategies/` |
| `HikyuuTradingSystemAdapter` | `FactorWeaveTradingSystemAdapter` | `plugins/strategies/` |

### 2. 文件路径更新

| 配置项 | 旧值 | 新值 |
|--------|------|------|
| 数据库路径 | `db/hikyuu_system.db` | `db/factorweave_system.db` |
| 日志文件 | `hikyuu_ui.log` | `factorweave_quant.log` |
| 缓存目录 | `cache/hikyuu/` | `cache/factorweave/` |
| 配置目录 | `config/hikyuu/` | `config/factorweave/` |

### 3. 字符串替换规则

| 旧字符串模式 | 新字符串模式 | 适用范围 |
|--------------|--------------|----------|
| `HIkyuu-UI` | `FactorWeave-Quant` | 所有文件 |
| `HIkyuu` | `FactorWeave` | 类名、变量名 |
| `hikyuu_ui` | `factorweave_quant` | 文件名、路径 |
| `hikyuu_system` | `factorweave_system` | 数据库相关 |

---

## 🗂️ 文件操作清单

### 删除操作
```bash
# 删除不使用的数据库
rm db/metrics.db
rm visualization/stock.db

# 删除临时和缓存文件
rm -rf __pycache__/
rm -rf .pytest_cache/
rm -rf *.pyc
```

### 重命名操作
```bash
# 重命名数据库文件
mv db/hikyuu_system.db db/factorweave_system.db
mv data/strategies.db data/factorweave_strategies.db  
mv visualization/block.db visualization/factorweave_blocks.db

# 创建新目录结构
mkdir -p analytics/
mkdir -p cache/factorweave/
mkdir -p config/factorweave/
```

### 新建操作
```bash
# 创建DuckDB分析数据库
touch analytics/factorweave_analytics.db
```

---

## 📝 代码修改清单

### 1. 主应用文件 (`main.py`)
- [ ] 类名: `HIkyuuUIApplication` → `FactorWeaveQuantApplication`
- [ ] 日志文件路径: `hikyuu_ui.log` → `factorweave_quant.log`
- [ ] 窗口标题和应用名称更新

### 2. 启动器文件 (`quick_start.py`)
- [ ] 类名: `HIkyuuQuickStart` → `FactorWeaveQuantLauncher`
- [ ] 所有字符串引用更新
- [ ] 帮助信息和联系方式更新

### 3. 配置管理 (`utils/config_manager.py`, `utils/theme.py`)
- [ ] 数据库路径: `hikyuu_system.db` → `factorweave_system.db`
- [ ] 配置键名更新

### 4. 插件系统
- [ ] 插件元数据文件更新
- [ ] 插件类名重命名
- [ ] 插件描述和信息更新

### 5. 策略系统 (`strategies/`)
- [ ] 策略类名更新
- [ ] 策略描述更新
- [ ] 数据库连接更新

### 6. 测试文件 (`tests/`)
- [ ] 测试类名更新
- [ ] 测试描述更新
- [ ] 测试数据路径更新

---

## 🏗️ 新架构实施

### 1. DuckDB集成
```python
# 新增DuckDB连接管理器
class FactorWeaveAnalyticsDB:
    def __init__(self):
        self.db_path = "analytics/factorweave_analytics.db"
        self.conn = duckdb.connect(self.db_path)
    
    def create_tables(self):
        # 创建分析表结构
        pass
```

### 2. 数据访问层重构
```python
# 统一数据访问接口
class FactorWeaveDataManager:
    def __init__(self):
        self.config_db = SQLiteDB("db/factorweave_system.db")
        self.analytics_db = DuckDB("analytics/factorweave_analytics.db")
    
    def route_query(self, query_type, sql, params=None):
        if query_type in ['config', 'plugin', 'user']:
            return self.config_db.execute(sql, params)
        else:
            return self.analytics_db.execute(sql, params)
```

### 3. 数据迁移脚本
```python
# 数据迁移工具
class DatabaseMigrator:
    def migrate_to_new_architecture(self):
        # 1. 重命名SQLite数据库
        # 2. 创建DuckDB数据库
        # 3. 迁移分析数据
        # 4. 验证数据完整性
        pass
```

---

## ⚡ 执行顺序

### 阶段1: 准备工作 (30分钟)
1. **备份现有数据库**
   ```bash
   cp -r db/ db_backup_$(date +%Y%m%d_%H%M%S)/
   ```

2. **创建新目录结构**
   ```bash
   mkdir -p analytics/ cache/factorweave/ config/factorweave/
   ```

### 阶段2: 数据库重构 (45分钟)
1. **删除不使用的数据库**
2. **重命名现有数据库**
3. **创建DuckDB分析数据库**
4. **实施数据迁移**

### 阶段3: 代码重构 (90分钟)
1. **更新主要类名**
2. **更新配置路径**
3. **更新字符串引用**
4. **更新插件元数据**

### 阶段4: 测试验证 (30分钟)
1. **功能测试**
2. **数据库连接测试**
3. **插件系统测试**
4. **性能验证**

---

## ✅ 验证检查清单

### 数据库验证
- [ ] 新数据库文件存在且可访问
- [ ] 旧数据库已正确删除或重命名
- [ ] 数据迁移完整性检查
- [ ] 新架构性能测试

### 代码验证
- [ ] 应用正常启动
- [ ] 所有功能模块正常工作
- [ ] 插件系统正常加载
- [ ] 日志文件正确生成

### 配置验证
- [ ] 配置文件路径正确
- [ ] 数据库连接正常
- [ ] 主题和UI配置正常
- [ ] 用户偏好设置保留

---

## 🚨 风险控制

### 数据安全
- 执行前完整备份所有数据库
- 分步执行，每步验证
- 保留回滚脚本

### 功能完整性
- 逐模块测试
- 关键功能优先验证
- 用户数据完整性检查

### 性能监控
- 对比重构前后性能
- 监控内存使用
- 验证查询效率提升

---

**执行负责人**: AI助手  
**预计总耗时**: 3小时  
**风险级别**: 中等 (有完整备份和回滚方案)  
**成功标准**: 系统正常运行，性能提升，数据完整 