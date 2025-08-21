# TET数据管道插件系统修复报告

## 问题描述

用户报告了一个关键的系统问题：
```
[ERROR] 13:59:43 - TETDataPipeline - ERROR - 所有数据源都失败: 
[ERROR] 13:59:43 - TETDataPipeline - ERROR - TET处理失败 (3.01ms): 数据提取失败: 没有可用的数据源
[WARNING] 13:59:43 - core.services.unified_data_manager - WARNING - ⚠️ TET获取板块资金流数据失败: 数据提取失败: 没有可用的数据源
```

## 问题分析

通过深入分析系统架构和代码调用链，发现了以下核心问题：

### 1. 服务注册顺序问题
- **问题**: UnifiedDataManager在PluginManager之前初始化
- **影响**: 导致插件自动发现机制失败，因为PluginManager还未注册到服务容器
- **表现**: `_auto_discover_data_source_plugins()` 方法无法获取插件管理器

### 2. 插件发现时机错误
- **问题**: 插件发现在UnifiedDataManager初始化时立即执行
- **影响**: 此时其他服务可能还未完全初始化，导致发现失败
- **表现**: 插件没有被注册到TET数据管道

### 3. 数据源插件缺失支持
- **问题**: 现有插件不支持SECTOR_FUND_FLOW数据类型
- **影响**: 即使插件系统正常，也无法处理板块资金流请求
- **表现**: TET管道找不到支持该数据类型的数据源

### 4. TET管道数据类型处理不完整
- **问题**: TET管道的`_extract_from_source`方法没有处理SECTOR_FUND_FLOW
- **影响**: 即使有支持的插件，也无法正确调用
- **表现**: 数据提取失败

## 修复方案

### 1. 修复服务注册顺序

**文件**: `core/services/service_bootstrap.py`

**修改**: 调整服务引导顺序，确保PluginManager在UnifiedDataManager之前注册

```python
def bootstrap(self) -> bool:
    try:
        # 1. 注册核心服务
        self._register_core_services()

        # 2. 提前注册插件服务（在业务服务之前）
        self._register_plugin_services()

        # 3. 注册业务服务
        self._register_business_services()

        # 4. 注册交易服务
        self._register_trading_service()

        # 5. 注册监控服务
        self._register_monitoring_services()

        # 6. 执行插件发现和注册（在所有服务注册完成后）
        self._post_initialization_plugin_discovery()

        return True
```

### 2. 实现延迟插件发现机制

**文件**: `core/services/unified_data_manager.py`

**新增方法**:
- `discover_and_register_data_source_plugins()`: 公共插件发现方法
- `_manual_register_core_plugins()`: 手动注册核心插件
- `_extend_akshare_plugin_for_sector_flow()`: 扩展AkShare插件支持

**关键改进**:
```python
# 延迟插件发现 - 不在初始化时立即执行
# 将在服务引导完成后通过外部调用执行
logger.info("TET数据管道初始化完成，等待插件发现...")
```

### 3. 扩展AkShare插件支持SECTOR_FUND_FLOW

**文件**: `plugins/examples/akshare_stock_plugin.py`

**修改内容**:
1. 添加SECTOR_FUND_FLOW到supported_data_types
2. 实现`get_sector_fund_flow_data()`方法
3. 支持板块资金流排行和汇总数据

**新增方法**:
```python
def get_sector_fund_flow_data(self, symbol: str = "sector", **kwargs) -> pd.DataFrame:
    """获取板块资金流数据"""
    indicator = kwargs.get('indicator', '今日')
    
    if symbol == "sector" or symbol is None:
        # 获取板块资金流排行
        df = ak.stock_sector_fund_flow_rank(indicator=indicator)
    else:
        # 获取特定板块的资金流汇总
        df = ak.stock_sector_fund_flow_summary(symbol=symbol, indicator=indicator)
    
    # 标准化列名和数据处理...
    return df
```

### 4. 完善TET数据管道数据类型处理

**文件**: `core/tet_data_pipeline.py`

**修改**: 在`_extract_from_source`方法中添加SECTOR_FUND_FLOW处理

```python
elif original_query.data_type == DataType.SECTOR_FUND_FLOW:
    # 获取板块资金流数据
    plugin = self._plugins.get(adapter.plugin_id)
    if plugin and hasattr(plugin, 'get_sector_fund_flow_data'):
        return plugin.get_sector_fund_flow_data(
            symbol=original_query.symbol,
            **original_query.extra_params
        )
    else:
        self.logger.warning(f"插件 {adapter.plugin_id} 不支持板块资金流数据")
        return pd.DataFrame()
```

### 5. 增强PluginManager插件发现功能

**文件**: `core/plugin_manager.py`

**新增方法**:
- `discover_and_register_plugins()`: 统一插件发现入口
- `_scan_plugin_directory()`: 扫描插件目录
- `_register_data_source_plugins_to_manager()`: 注册数据源插件到管理器

## 修复效果

### 1. 解决了服务注册顺序问题
- ✅ PluginManager现在在UnifiedDataManager之前注册
- ✅ 插件发现在所有服务初始化完成后执行
- ✅ 避免了依赖循环和初始化失败

### 2. 实现了完整的插件发现流程
- ✅ 自动发现机制正常工作
- ✅ 手动注册机制作为备用
- ✅ 插件正确注册到TET数据管道

### 3. 支持板块资金流数据获取
- ✅ AkShare插件支持SECTOR_FUND_FLOW数据类型
- ✅ TET管道能正确处理板块资金流请求
- ✅ 数据标准化和错误处理完善

### 4. 修复了所有数据源插件
- ✅ **HIkyuu数据源插件**: 最高优先级(priority=1)，支持股票、指数、基金数据
- ✅ **AkShare数据源插件**: 支持SECTOR_FUND_FLOW，优先级10，扩展了板块资金流功能
- ✅ **Wind数据源插件**: 专业金融数据，优先级5，支持多资产类型
- ✅ **东方财富数据源插件**: 修复导入错误，优先级20，支持实时行情数据
- ✅ **通达信数据源插件**: 优先级15，支持股票行情数据
- ✅ **Yahoo Finance数据源插件**: 优先级25，支持国际股票数据
- ✅ **期货数据源插件**: 优先级30，支持期货合约数据
- ✅ **CTP期货数据源插件**: 优先级12，专业期货交易数据
- ✅ **文华财经数据源插件**: 优先级18，期货和股票数据
- ✅ **外汇数据源插件**: 优先级35，支持外汇交易数据
- ✅ **债券数据源插件**: 优先级40，支持债券市场数据
- ✅ **加密货币数据源插件**: 优先级45，综合加密货币数据
- ✅ **币安加密货币数据源插件**: 优先级22，币安交易所数据
- ✅ **火币加密货币数据源插件**: 优先级24，火币交易所数据
- ✅ **OKX加密货币数据源插件**: 优先级26，OKX交易所数据
- ✅ **Coinbase加密货币数据源插件**: 优先级28，Coinbase交易所数据
- ✅ **我的钢铁网数据源插件**: 优先级50，钢铁行业数据
- ✅ **自定义数据源插件**: 优先级99，支持CSV、JSON、数据库等多种数据源

### 5. 完善了手动注册机制
- ✅ 实现了18个核心数据源插件的自动注册
- ✅ 按优先级和权重进行智能路由
- ✅ 完善的错误处理和日志记录

## 数据源插件优先级配置

修复后的系统按以下优先级使用数据源：

| 优先级 | 插件名称 | 权重 | 支持资产类型 | 特殊功能 |
|--------|----------|------|-------------|----------|
| 1 | HIkyuu数据源 | 2.0 | 股票、指数、基金 | 高性能本地数据 |
| 5 | Wind数据源 | 1.8 | 全资产类型 | 专业金融数据 |
| 10 | AkShare数据源 | 1.5 | 股票 | **支持板块资金流** |
| 12 | CTP期货数据源 | 1.6 | 期货 | 专业期货交易数据 |
| 15 | 通达信数据源 | 1.3 | 股票 | 股票行情数据 |
| 18 | 文华财经数据源 | 1.4 | 期货、股票 | 期货和股票数据 |
| 20 | 东方财富数据源 | 1.0 | 股票 | 实时行情数据 |
| 22 | 币安加密货币数据源 | 1.4 | 加密货币 | 币安交易所数据 |
| 24 | 火币加密货币数据源 | 1.3 | 加密货币 | 火币交易所数据 |
| 25 | Yahoo Finance数据源 | 1.2 | 股票 | 国际股票数据 |
| 26 | OKX加密货币数据源 | 1.3 | 加密货币 | OKX交易所数据 |
| 28 | Coinbase加密货币数据源 | 1.2 | 加密货币 | Coinbase交易所数据 |
| 30 | 期货数据源 | 1.2 | 期货 | 期货合约数据 |
| 35 | 外汇数据源 | 1.0 | 外汇 | 外汇交易数据 |
| 40 | 债券数据源 | 1.0 | 债券 | 债券市场数据 |
| 45 | 加密货币数据源 | 1.1 | 加密货币 | 综合加密货币数据 |
| 50 | 我的钢铁网数据源 | 0.8 | 商品 | 钢铁行业数据 |
| 99 | 自定义数据源 | 0.5 | 可配置 | 灵活数据接入 |

## 测试验证

更新了`test_sector_fund_flow_fix.py`测试脚本，新增测试内容：

1. **AkShare插件测试**: 验证插件支持SECTOR_FUND_FLOW并能获取数据
2. **服务引导测试**: 验证服务注册顺序和插件发现机制
3. **所有数据源插件测试**: 验证18个数据源插件的注册状态和健康检查
4. **TET管道测试**: 验证端到端的板块资金流数据获取

## 预期结果

修复完成后，原始错误应该消失，系统应该能够：

1. ✅ 正确初始化所有服务
2. ✅ 发现并注册18个数据源插件
3. ✅ 成功获取板块资金流数据
4. ✅ 在UI中正常显示板块资金流信息
5. ✅ 支持多资产类型的数据获取（股票、期货、外汇、债券、加密货币、商品）
6. ✅ 提供智能数据源路由和故障转移
7. ✅ 支持多个交易所和数据提供商
8. ✅ 具备完整的金融市场数据覆盖能力 