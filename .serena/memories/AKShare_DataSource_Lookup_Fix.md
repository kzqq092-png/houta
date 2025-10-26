## 问题描述
系统无法找到指定的数据源插件"AKShare数据源插件"，导致K线数据获取失败。日志显示："未找到匹配数据源 AKShare数据源插件 的插件，将使用所有可用插件"

## 根本原因
1. UniPluginDataManager 的 `_execute_data_request` 方法依赖于 PluginCenter 的能力索引 `get_available_plugins()` 来获取可用插件
2. PluginCenter 只返回支持特定数据类型和资产类型的插件
3. AKShare 插件虽然支持 STOCK 资产类型，但不支持 HISTORICAL_KLINE 数据类型
4. 当调用 `get_kline_data()` 时，系统查找支持 HISTORICAL_KLINE 和 STOCK 的插件，而 AKShare 不在其中
5. 因此即使用户指定了 "AKShare数据源插件"，系统也无法在能力列表中找到

## 解决方案
修改了 uni_plugin_data_manager.py 中的插件查找逻辑：
1. 当用户指定数据源时，优先从所有已注册的插件中查找，而不是仅从能力列表中查找
2. 增强了插件名称匹配算法，支持中文名称和英文ID的多种匹配方式
3. 在 PluginInfo 数据类中添加了 `chinese_name` 字段，便于用户更好地识别插件
4. 改进了错误消息，列出所有已注册的插件，帮助用户调试

## 修改文件
- core/services/uni_plugin_data_manager.py: 改进插件查找逻辑
- plugins/data_sources/stock/akshare_plugin.py: 添加 chinese_name 属性
- core/data_source_extensions.py: 在 PluginInfo 中添加 chinese_name 字段

## 测试方法
调用 get_kline_data() 时指定 data_source="AKShare数据源插件"，系统应该能正确识别并使用该插件（如果插件支持K线数据）或给出更明确的错误提示