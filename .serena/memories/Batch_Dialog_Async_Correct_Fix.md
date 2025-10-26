## 批量选择对话框异步改造 - 正确方案

### 问题
1. `'BatchSelectionDialog' object has no attribute 'update_stats_label'` - 方法名错误
2. `'BatchSelectionDialog' object has no attribute 'get_stock_data'` - 逻辑错误
3. 从数据库加载 vs 从插件获取真实资产列表的混淆

### 根本原因
之前的修改过度了：
- 删除了太多原始方法
- 混淆了数据来源（应该从插件，不是数据库）
- 调用了不存在的方法名

### 正确解决方案

#### 1. 保留所有原始方法
✅ `populate_table()` - 填充表格数据
✅ `filter_items()` - 按搜索文本过滤
✅ `filter_by_category()` - 按分类过滤
✅ `select_all()` - 全选
✅ `clear_all()` - 清空
✅ `update_stats()` - 更新统计信息
✅ `get_selected_codes()` - 获取选中的代码

#### 2. 修复方法名
- 第310行：`self.update_stats_label()` → `self.update_stats()`

#### 3. 正确的数据获取逻辑
添加 `load_asset_list_from_plugins()` 方法：
```python
def load_asset_list_from_plugins(self):
    """从插件获取真实资产列表"""
    from core.services.uni_plugin_data_manager import get_unified_data_manager
    
    data_manager = get_unified_data_manager()
    
    # 调用正确的方法：
    if self.asset_type == "股票":
        result = data_manager.get_stock_list(market='all')  # ✅ 从插件获取
    elif self.asset_type == "指数":
        result = data_manager.get_index_list(market='all')
    # ... 等等
```

#### 4. 异步线程加载数据
```python
def run(self):
    # 从插件获取真实资产列表（异步）
    data = self.dialog.load_asset_list_from_plugins()
    self.finished.emit(data or [])
```

### 关键改进
1. ✅ 保留了所有 UI 控制方法
2. ✅ 纠正了方法名称
3. ✅ 从插件获取真实数据（不是硬编码列表）
4. ✅ 只做最小改动实现异步
5. ✅ 语法检查通过

### 数据流程
```
用户点击批量选择
  ↓
进度条显示（异步加载）
  ↓
DataLoaderThread 后台运行
  ↓
load_asset_list_from_plugins()
  ↓
UniPluginDataManager.get_stock_list() 等
  ↓
返回真实插件数据
  ↓
on_data_loaded() 回调
  ↓
populate_table() 显示
  ↓
update_stats() 更新统计
  ↓
启用所有交互元素
```