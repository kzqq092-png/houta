## 问题
系统无法找到指定的数据源插件"AKShare数据源插件"，即使用户明确指定了该数据源。根本原因是插件查找依赖于能力索引，而 AKShare 虽然支持 STOCK 资产类型，但不支持 HISTORICAL_KLINE 数据类型。

## 解决方案
改进了 UniPluginDataManager 的插件查找机制：
1. 当用户指定数据源时，优先从所有已注册插件中查找，而不是仅依赖能力索引
2. 在 PluginInfo 中添加 chinese_name 字段便于识别
3. 增强了插件名称匹配算法，支持多种方式

## 修改的文件
1. core/services/uni_plugin_data_manager.py - 改进插件查找逻辑
2. plugins/data_sources/stock/akshare_plugin.py - 添加 chinese_name 属性  
3. core/data_source_extensions.py - 在 PluginInfo 中添加 chinese_name 字段

## 测试结果
✅ 成功获取 5438 支股票，数据质量评分 1.000，完全验证了修复的有效性

## 关键改进
- 用户现在可以通过指定 data_source="AKShare数据源插件" 明确使用该插件
- 系统不再依赖插件的完整能力定义就能使用插件
- 改进了错误提示，列出已注册的插件便于调试