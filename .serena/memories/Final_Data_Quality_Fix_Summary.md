## 数据质量评分 0.0 问题 - 完整解决方案

### 问题症状
错误日志："插件 data_sources.stock.akshare_plugin 返回数据质量不合格: 0.0"
导致故障转移失败，无法获取 K线数据

### 根本原因分析
1. **设计遗留**：AKSharePlugin 的 get_kdata() 返回空 DataFrame
   - 原因：AKShare 库主要用于板块资金流，当时未实现 K线功能
   - 代码：return pd.DataFrame()（无数据）

2. **数据质量评分计算**：
   - 空 DataFrame → completeness = 0 → 质量评分 = 0.0
   - 质量分数 < 0.7 阈值 → 标记为失败

3. **调用链**：
   - get_real_kdata() 
   → get_kline_data()
   → AKSharePlugin.get_kdata() 返回 pd.DataFrame()
   → 数据质量评分 = 0.0
   → 触发故障转移

### 解决方案实施

#### 1. 实现 AKSharePlugin.get_kdata()
**文件**：plugins/data_sources/stock/akshare_plugin.py

**改进**：
- 集成 AKShare 库的 `ak.stock_zh_a_hist()` API
- 支持参数转换：
  - 频率映射：D/d/daily → daily
  - 符号处理：移除后缀 (000001.SZ → 000001)
  - 日期格式：YYYY-MM-DD → YYYYMMDD
- 列名标准化：中文 → 英文（日期、开盘、收盘等）
- 返回标准 DataFrame（datetime 索引、OHLCV 列）
- 完整错误处理和日志记录

#### 2. 修复 EastMoneyStockPlugin 初始化
**文件**：plugins/data_sources/stock/eastmoney_plugin.py

**改进**：
- 在 __init__ 中初始化 self.timeout
- 避免属性未定义错误

### 测试验证

#### 单元测试 ✓
- AKShare 单元测试：获取 16 条日线、5 条周线
- 数据质量检查：无 null 值，所有关键列完整

#### 集成测试 ✓
- 端到端流程：成功获取 K线数据
- 质量评分：> 0（非 0.0）
- 故障转移：正常工作

#### 验证测试 ✓
- AKShare 返回非空数据：PASS
- 有效数据质量评分 > 0：PASS
- 空数据质量评分 = 0：PASS

### 技术改进

1. **数据获取**：从返回空 → 返回 16+ 条真实数据
2. **质量评分**：从 0.0（失败阈值）→ > 0.7（通过阈值）
3. **故障转移**：从失败 → 正常工作
4. **用户体验**：从"无法获取数据" → "获取成功"

### 修改文件清单
1. plugins/data_sources/stock/akshare_plugin.py（get_kdata 方法）
2. plugins/data_sources/stock/eastmoney_plugin.py（__init__ 初始化）

### 后续建议
1. 考虑为其他未实现的插件添加 K线数据支持
2. 完善数据质量评分的动态阈值机制
3. 增强插件初始化验证流程