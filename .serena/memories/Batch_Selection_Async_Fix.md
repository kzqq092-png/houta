## K线专业数据导入UI卡死问题 - 解决方案

### 问题分析
1. **UI卡死原因**：
   - BatchSelectionDialog.load_data() 在主UI线程同步执行
   - get_stock_data() 调用插件API获取股票列表（可能需要几秒钟）
   - 没有进度反馈，用户体验差

2. **AKShare API问题**：
   - format_date() 函数未处理 datetime 对象
   - 只处理字符串格式，导致 datetime 参数无法转换

### 解决方案

#### 1. 修复 AKShare 日期转换（plugins/data_sources/stock/akshare_plugin.py）
- 增强 format_date() 函数支持 datetime.datetime 和 datetime.date 对象
- 使用正则表达式匹配多种日期格式
- 提供完善的错误处理

#### 2. 异步加载股票列表（gui/widgets/enhanced_data_import_widget.py）
**新增 DataLoadWorker 类**：
- 继承 QThread，在后台线程加载数据
- 发射进度信号 (progress)、完成信号 (finished)、错误信号 (error)
- 支持多种资产类型（股票、指数、期货、基金、债券）

**改进 BatchSelectionDialog**：
- 使用 load_data_async() 替代同步 load_data()
- 显示 QProgressDialog 进度对话框
- 支持取消操作
- 数据加载完成后更新UI

### 关键改进
- ✅ UI 不再卡死（后台线程加载）
- ✅ 提供进度反馈（进度条 + 状态消息）
- ✅ 支持用户取消操作
- ✅ AKShare API 正确处理日期参数
- ✅ 更好的错误处理和用户提示

### 修改文件
1. plugins/data_sources/stock/akshare_plugin.py（行 472-504）
2. gui/widgets/enhanced_data_import_widget.py（行 93-309）