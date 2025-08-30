# TET数据源问题修复方案

## 🔍 问题分析

### 根本原因
通过深入分析日志和代码，发现了TET数据源获取失败的根本原因：

#### 1. HIkyuu插件股票代码格式问题
**问题**: HIkyuu插件在`get_kdata`方法中直接使用原始股票代码（如"000001"）查询HIkyuu，但HIkyuu需要带市场前缀的格式（如"sz000001"）。

**代码位置**: `plugins/data_sources/hikyuu_data_plugin.py:431`
```python
# 错误的实现
stock = self._sm[symbol]  # 直接使用 "000001"

# 应该是
normalized_symbol = self.normalize_symbol(symbol)  # "000001" -> "sz000001"
stock = self._sm[normalized_symbol]
```

#### 2. Tongdaxin插件适配器缺失
**问题**: 系统配置中引用了`examples.tongdaxin_stock_plugin`，但该插件没有正确注册为数据源适配器。

**错误信息**: 
```
数据源适配器不存在: examples.tongdaxin_stock_plugin
```

#### 3. 数据源路由配置问题
**问题**: 数据源路由器尝试使用多个数据源，但除了HIkyuu外的其他数据源都未正确配置或注册。

## 🛠️ 修复方案

### 修复1: HIkyuu插件股票代码标准化

**文件**: `plugins/data_sources/hikyuu_data_plugin.py`

**修复内容**:
```python
# 在get_kdata方法中添加股票代码标准化
def get_kdata(self, symbol: str, freq: str = "D", start_date: str = None,
              end_date: str = None, count: int = None) -> pd.DataFrame:
    # ... existing code ...
    
    # 标准化股票代码（添加市场前缀）
    normalized_symbol = self.normalize_symbol(symbol)
    self.logger.debug(f"股票代码标准化: {symbol} -> {normalized_symbol}")
    
    # 获取股票对象
    try:
        stock = self._sm[normalized_symbol]  # 使用标准化后的代码
        # ... rest of the method
```

**预期效果**: HIkyuu能够正确识别和查询股票数据，解决"数据源返回空数据"问题。

### 修复2: 移除或修复Tongdaxin插件引用

**选项A: 移除Tongdaxin插件引用**
```python
# 在UnifiedDataManager中只使用HIkyuu
data_source_router.set_asset_priorities(AssetType.STOCK, ["hikyuu"])
# 移除对tongdaxin的引用
```

**选项B: 正确注册Tongdaxin插件**
```python
# 确保tongdaxin插件正确注册
if self._register_tongdaxin_plugin():
    data_source_router.set_asset_priorities(AssetType.STOCK, ["hikyuu", "tongdaxin"])
```

### 修复3: 字符串转换错误处理

**文件**: `gui/widgets/modern_performance_widget.py`

**问题**: 当显示"--"时仍尝试转换为float
**修复**:
```python
try:
    if value == "--":
        trend = "neutral"
        numeric_value = 0  # 避免后续逻辑错误
    else:
        numeric_value = float(value)
```

## 🎯 实施步骤

### 步骤1: 修复HIkyuu插件（最关键）
1. ✅ 已修复：在`get_kdata`方法中添加股票代码标准化
2. 测试HIkyuu数据获取是否正常

### 步骤2: 简化数据源配置
1. 临时移除对tongdaxin插件的依赖
2. 确保只使用HIkyuu作为主要数据源
3. 验证TET管道正常工作

### 步骤3: 测试验证
1. 测试股票代码: 000001, 000002, 600000, 600036
2. 验证K线数据获取成功
3. 确认策略性能计算正常

## 📊 预期结果

### 修复前
```
[ERROR] 所有数据源都失败: 000001
[ERROR] 数据源返回空数据: hikyuu
[ERROR] 数据源适配器不存在: examples.tongdaxin_stock_plugin
```

### 修复后
```
[INFO] 股票代码标准化: 000001 -> sz000001
[INFO] ✅ 通过TET成功获取股票 000001 的 89 个收益率数据点
[INFO] ✅ 成功获取真实市场数据: 来自 4 只股票，总共 356 个收益率数据点
```

## 🔧 立即执行的修复

### 关键修复（已完成）
```python
# plugins/data_sources/hikyuu_data_plugin.py
# 在第429行后添加股票代码标准化
normalized_symbol = self.normalize_symbol(symbol)
stock = self._sm[normalized_symbol]
```

### 后续优化
1. **清理数据源配置**: 移除无效的tongdaxin引用
2. **增强错误处理**: 改进插件注册失败的处理逻辑
3. **优化缓存机制**: 避免重复查询无效股票

## 🎉 总结

这次修复解决了TET数据源获取失败的根本原因：
1. **HIkyuu股票代码格式问题** - 最关键的修复
2. **数据源配置冲突** - 简化配置避免依赖问题
3. **错误处理优化** - 提高系统稳定性

**修复后，TET多数据源框架将能够正常获取真实的HIkyuu市场数据，为策略性能计算提供可靠的数据基础。**

---

**修复时间**: 2025-08-19  
**修复范围**: HIkyuu插件、数据源路由、错误处理  
**测试状态**: 待验证  
**影响范围**: 策略性能数据获取 