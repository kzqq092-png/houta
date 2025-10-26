## AKShare 部分股票无数据问题 - 最终解决方案

### 问题症状
```
23:29:04.557 | INFO | core.services.uni_plugin_data_manager:_execute_data_request:434 - 
[TET] TET框架开始数据请求处理 - 方法: get_kline_data, 资产类型: stock, 数据类型: historical_kline

23:29:04.565 | WARNING | plugin_data_sources_stock_akshare_plugin:get_kdata:497 - 
AKShare未返回000048的K线数据。依然无法获取数据
```

### 问题分析
1. **AKShare API 限制**：AKShare 库的 `ak.stock_zh_a_hist()` API 不是所有股票都有数据
2. **能力声明错误**：AKShare 被标记为支持 HISTORICAL_KLINE，但实际上不支持
3. **调用链问题**：系统被指定使用 AKShare 作为数据源，导致无法回退

### 解决方案

#### 1. 从支持数据类型中移除 HISTORICAL_KLINE
**文件**：plugins/data_sources/stock/akshare_plugin.py 行 91-98

```python
def get_supported_data_types(self) -> List[DataType]:
    """获取支持的数据类型"""
    return [
        DataType.SECTOR_FUND_FLOW,    # 板块资金流数据（主要功能）
        DataType.REAL_TIME_QUOTE,     # 实时行情
        DataType.ASSET_LIST           # 资产列表
        # 注意：不包含 HISTORICAL_KLINE，因为 AKShare 的 K线数据不完整
    ]
```

#### 2. 改进日志记录
**文件**：plugins/data_sources/stock/akshare_plugin.py 行 496-498

```python
if df.empty:
    self.logger.warning(f"AKShare未返回{symbol}的K线数据。依然无法获取数据 ...")
    self.logger.info(f"建议使用其他数据源获取{symbol}的K线数据（如：新浪财经、东方财富等）")
    return pd.DataFrame()
```

#### 3. 保留 get_kdata() 实现（用于兼容性）
- 虽然移除了 HISTORICAL_KLINE 支持声明
- 但保留了 get_kdata() 的实现
- 如果用户显式要求 AKShare，仍可以使用（但可能返回空数据）

### 工作原理

1. **首次调用**：如果指定数据源为 AKShare
   - 调用 AKShare.get_kdata()
   - 如果返回空 → 日志提示建议用其他数据源

2. **未来调用**：如果未指定数据源
   - 系统通过能力匹配找到支持 HISTORICAL_KLINE 的插件
   - AKShare 不在列表中（因为未声明支持此类型）
   - 自动选择其他插件（Sina、EastMoney、TongDaXin 等）

3. **故障转移**：如果选中的插件返回空数据
   - 自动尝试下一个可用的插件
   - 继续轮转直到找到有数据的插件

### 关键改进
- ✅ AKShare 不再被视为 K线数据的主要提供者
- ✅ 系统自动使用更可靠的数据源
- ✅ 明确的日志提示和建议
- ✅ 保持向后兼容性（仍可显式使用 AKShare）

### 修改清单
1. plugins/data_sources/stock/akshare_plugin.py
   - 行 91-98：更新 get_supported_data_types()
   - 行 496-498：改进日志记录

### 预期效果
对于无数据的股票（如 000055、000048）：
- 不再返回 0.0 质量分数错误
- 自动切换到其他可用的数据源
- 提供清晰的日志和诊断信息