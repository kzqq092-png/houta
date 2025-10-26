## 异步批量选择对话框和 AKShare API 修复

### 问题1：BatchSelectionDialog 属性缺失
**错误**：`'BatchSelectionDialog' object has no attribute 'get_stock_data'`

**原因**：在异步改进中删除了原始数据加载方法

**修复**：
1. 添加了 `get_stock_data()` 方法 - 从 unified_data_manager 获取股票列表
2. 添加了 `get_index_data()` 方法 - 返回基础指数列表
3. 添加了 `get_futures_data()` 方法 - 返回基础期货列表
4. 添加了 `get_fund_data()` 方法 - 返回基础基金列表
5. 添加了 `get_bond_data()` 方法 - 返回基础债券列表

**文件**：gui/widgets/enhanced_data_import_widget.py（第332-423行）

### 问题2：AKShare API 日期参数错误
**错误日志**：`AKShare未返回000048的K线数据 (symbol=000048, period=daily, dates=2024-06-08 23:35:18.201706~2025-10-21 23:35:18.201706)`

**根本原因**：
1. 日期格式包含时间戳信息，但 AKShare API 要求 YYYYMMDD 格式（纯数字）
2. 当前 format_date() 函数处理不了 datetime 对象

**修复方案**（plugins/data_sources/stock/akshare_plugin.py 第471-506行）：
```python
def format_date(date_input):
    # 支持三种格式：
    # 1. datetime 对象 → YYYYMMDD
    # 2. 字符串日期 (YYYY-MM-DD 或 YYYYMMDD) → YYYYMMDD
    # 3. 包含时间戳的字符串 → 提取日期部分 → YYYYMMDD
    
    # 使用正则表达式匹配 YYYY-MM-DD 或 YYYYMMDD
    # match = re.search(r'(\d{4})[-/]?(\d{2})[-/]?(\d{2})', date_str)
```

**关键改进**：
- ✓ 直接支持 datetime.datetime 和 datetime.date 对象
- ✓ 使用正则表达式从各种格式中提取日期
- ✓ 正确处理时间戳字符串（如"2024-06-08 23:35:18.201706"）
- ✓ 保留备用方案处理非标准格式

### 可能的第三个问题：AKShare 不支持所有股票的 K线数据
**症状**：某些股票（000037, 000048, 000055等）无法获取数据

**根本原因**：
- AKShare 的 `ak.stock_zh_a_hist()` API 不是对所有股票都有数据
- 可能是 ST股票、新股或数据不完整的股票

**解决方案**：
- 从 AKShare 的 supported_data_types 中移除 HISTORICAL_KLINE
- AKShare 现在仅作为辅助数据源（板块资金流、实时行情、资产列表）
- 系统自动故障转移到其他插件获取 K线数据

### 测试方案
1. 打开批量选择对话框 - 应显示进度条
2. 等待后台加载完成 - 不应卡死
3. 获取K线数据 - 日期参数应正确转换为 YYYYMMDD 格式
4. 如果 AKShare 无法获取 - 应自动故障转移到其他插件