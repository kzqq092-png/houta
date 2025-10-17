# data/目录SQLite数据库合并分析

## 📊 当前状况

### 7个数据库文件（2.25MB）

| 文件 | 大小 | 记录数 | 表数 | 状态 |
|------|------|--------|------|------|
| `enhanced_risk_monitor.db` | 2.13MB | 2,072 | 8 | ✅ 有数据 |
| `tdx_servers.db` | 68KB | 299 | 3 | ✅ 有数据 |
| `strategy.db` | 4KB | 0 | 1 | ⚠️ 空 |
| `task_status.db` | 24KB | 0 | 3 | ⚠️ 空 |
| `unified_quality_monitor.db` | 40KB | 0 | 4 | ⚠️ 空 |
| `unified_quality_monitor.sqlite` | 40KB | 0 | 4 | ⚠️ 重复 |
| `factorweave.db` | 0KB | - | 0 | ⚠️ 完全空 |

## 🔍 数据量预测

### 未来数据增长分析

| 数据库 | 当前大小 | 预计增长 | 是否大数据 |
|--------|---------|---------|-----------|
| **风险监控** | 2.13MB | 中等（每天+KB级） | ❌ 否 |
| **通达信服务器** | 68KB | 极小（仅配置） | ❌ 否 |
| **策略定义** | 4KB | 小（用户策略数） | ❌ 否 |
| **任务状态** | 24KB | 小（活跃任务数） | ❌ 否 |
| **质量监控** | 40KB | 小（监控报告） | ❌ 否 |

**结论**：这些都是**轻量级配置和状态数据**，不是大数据库。

### 为什么不是大数据？

1. **风险监控（2.13MB）**
   - 存储风险事件和告警
   - 通常保留近期数据（如30天）
   - 旧数据会归档或删除
   - **预计最大：10-50MB**

2. **通达信服务器（68KB）**
   - 仅存储服务器列表和统计
   - 数据量固定（约100-200个服务器）
   - **预计最大：1-2MB**

3. **策略定义（4KB）**
   - 存储用户创建的策略配置
   - 数量有限（用户策略数）
   - **预计最大：10-20MB**

4. **任务状态（24KB）**
   - 存储任务执行状态
   - 完成的任务会清理
   - **预计最大：5-10MB**

5. **质量监控（40KB）**
   - 存储数据质量报告
   - 保留周期有限
   - **预计最大：10-20MB**

## 💡 合并方案

### 方案：统一到 `factorweave_system.sqlite`

**为什么合并？**

1. ✅ **简化管理**：1个文件比7个易管理
2. ✅ **原子性事务**：跨表事务更可靠
3. ✅ **减少文件数**：避免文件系统开销
4. ✅ **统一备份**：一次备份所有配置
5. ✅ **性能更好**：减少文件打开/关闭开销

**为什么可以合并？**

1. ✅ 数据量都很小（总计<10MB）
2. ✅ 都是配置和状态数据
3. ✅ 没有高并发写入需求
4. ✅ SQLite完全支持（最大支持140TB）

### 不合并的场景（不适用当前情况）

如果满足以下条件，才需要独立数据库：
- ❌ 单个数据库>1GB（当前最大2MB）
- ❌ 高并发写入（当前读多写少）
- ❌ 不同生命周期（当前都是长期配置）
- ❌ 独立部署需求（当前集成系统）

### 合并后的表结构

```sql
-- factorweave_system.sqlite

-- 1. 策略管理表
CREATE TABLE strategies (...);

-- 2. 任务状态表
CREATE TABLE tasks (...);
CREATE TABLE task_history (...);

-- 3. 风险监控表（8个表）
CREATE TABLE risk_events (...);
CREATE TABLE risk_metrics (...);
-- ... 其他6个表

-- 4. 通达信服务器表
CREATE TABLE tdx_servers (...);
CREATE TABLE tdx_server_stats (...);

-- 5. 数据质量表
CREATE TABLE quality_reports (...);
CREATE TABLE quality_issues (...);
CREATE TABLE quality_trends (...);

-- 6. 系统配置表（新增）
CREATE TABLE system_config (
    key VARCHAR PRIMARY KEY,
    value TEXT,
    category VARCHAR,
    updated_at TIMESTAMP
);
```

## 🚀 执行计划

### 阶段1：重命名（统一后缀）

```bash
# 将所有 .db 改为 .sqlite
mv data/enhanced_risk_monitor.db data/enhanced_risk_monitor.sqlite
mv data/strategy.db data/strategy.sqlite
mv data/task_status.db data/task_status.sqlite
mv data/tdx_servers.db data/tdx_servers.sqlite
```

### 阶段2：合并数据库

```sql
-- 1. 创建主数据库
CREATE DATABASE factorweave_system.sqlite

-- 2. 附加其他数据库并导入
ATTACH 'enhanced_risk_monitor.sqlite' AS risk;
ATTACH 'tdx_servers.sqlite' AS tdx;
ATTACH 'strategy.sqlite' AS strat;
-- ... 逐个导入表

-- 3. 添加命名空间前缀（避免冲突）
-- risk_events, tdx_servers, strategy_definitions
```

### 阶段3：更新代码引用

```python
# 所有数据库访问改为统一路径
DB_PATH = "data/factorweave_system.sqlite"

# 表名添加前缀
TABLE_RISK_EVENTS = "risk_events"
TABLE_TDX_SERVERS = "tdx_servers"
TABLE_STRATEGIES = "strategies"
```

### 阶段4：清理旧文件

```bash
# 备份旧文件
mv data/*.db data/backup/
mv data/*.sqlite.old data/backup/

# 删除重复文件
rm data/unified_quality_monitor.db  # 保留 .sqlite 版本
rm data/factorweave.db  # 完全空文件
```

## 📝 实施建议

### 立即执行

1. ✅ **重命名为 .sqlite**（统一命名规范）
2. ✅ **删除重复和空文件**（清理冗余）
3. ⏳ **合并到主数据库**（可选，建议执行）

### 合并的优先级

**高优先级（建议立即合并）：**
- ✅ `strategy.db` → 空数据库，直接删除或合并
- ✅ `task_status.db` → 空数据库，直接删除或合并
- ✅ `factorweave.db` → 完全空，删除

**中优先级（建议合并）：**
- ✅ `unified_quality_monitor` → 有2个副本，保留1个并合并
- ✅ `tdx_servers` → 配置数据，适合合并

**低优先级（可暂缓）：**
- ⏳ `enhanced_risk_monitor` → 有数据，可先观察增长

## ✅ 最终决策

### 推荐方案：渐进式合并

**第一步（立即）：清理和规范**
```bash
# 1. 重命名为 .sqlite
# 2. 删除空文件：factorweave.db
# 3. 删除重复：unified_quality_monitor.db（保留.sqlite）
```

**第二步（本次）：合并轻量配置**
```bash
# 合并到 factorweave_system.sqlite：
# - strategy（空）
# - task_status（空）
# - unified_quality_monitor（空）
# - tdx_servers（68KB，配置数据）
```

**第三步（可选）：合并风险监控**
```bash
# enhanced_risk_monitor（2MB）暂时保留独立
# 或合并到 factorweave_system.sqlite
```

---

**分析完成时间**：2025-10-14 01:10  
**推荐**：执行渐进式合并，先清理规范，再合并轻量配置

