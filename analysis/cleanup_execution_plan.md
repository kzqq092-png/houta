# DuckDB专业数据导入系统清理执行计划

## 清理目标
保留增强版数据导入系统，清理冗余的DuckDB专业数据导入组件，确保系统功能唯一不重复。

## 清理策略
采用安全渐进式清理，分阶段执行，每个阶段都进行验证。

## 阶段1: 准备和备份

### 1.1 创建备份目录
```bash
mkdir -p backup/duckdb_import_cleanup/
```

### 1.2 备份要清理的文件
- `gui/widgets/data_import_widget.py`
- `gui/dialogs/batch_import_dialog.py`
- 相关的协调器方法

## 阶段2: 清理冗余UI组件

### 2.1 删除传统数据导入UI组件
**文件**: `gui/widgets/data_import_widget.py`
**原因**: 
- 功能已被 `EnhancedDataImportWidget` 完全替代
- 虽然被协调器引用，但菜单入口未实际调用
- 删除后不会影响当前用户体验

**影响评估**: 低风险
- 菜单中的DuckDB导入入口目前只显示信息框
- 协调器中的 `_on_duckdb_import()` 方法需要同步清理

### 2.2 删除批量导入对话框
**文件**: `gui/dialogs/batch_import_dialog.py`
**原因**:
- 批量导入功能已集成到增强版系统的任务管理中
- 避免功能重复和用户困惑
- 菜单入口存在但未连接

**影响评估**: 低风险
- 菜单中的批量导入入口未连接到协调器
- 协调器中的 `_on_batch_import()` 方法需要同步清理

## 阶段3: 清理协调器中的相关方法

### 3.1 清理协调器方法
**文件**: `core/coordinators/main_window_coordinator.py`
**需要清理的方法**:
- `_on_duckdb_import()` (行2556-2578)
- `_on_batch_import()` (行2606-2625)

**替换策略**:
- 将 `_on_duckdb_import()` 重定向到增强版导入
- 删除 `_on_batch_import()` 方法

## 阶段4: 简化菜单结构

### 4.1 更新菜单系统
**文件**: `gui/menu_bar.py`

**需要修改的部分**:
1. **删除重复的DuckDB导入入口**:
   - 删除 `self.duckdb_import_action` (行320-323)
   - 删除对应的信号连接 (行386-387)

2. **保留并优化增强版导入入口**:
   - 保留 `self.enhanced_import_action` (行326-329)
   - 更新文本为 "🚀 DuckDB专业数据导入" 
   - 更新快捷键为 "Ctrl+Shift+I" (原DuckDB导入的快捷键)

3. **删除批量导入菜单项**:
   - 删除 `self.batch_import_action` (行340-342)
   - 删除相关的信号连接

### 4.2 更新菜单信号连接
**删除的连接**:
- `duckdb_import_action.triggered.connect(...)`
- `batch_import_action.triggered.connect(...)`

**保留的连接**:
- `enhanced_import_action.triggered.connect(...)`

## 阶段5: 清理测试文件

### 5.1 更新测试引用
检查并更新以下测试文件中的引用:
- `tests/test_integrated_task_management.py` (已使用增强版，无需修改)
- 其他可能引用传统组件的测试文件

## 阶段6: 清理导入语句和引用

### 6.1 搜索并清理残留引用
```bash
# 搜索可能的引用
grep -r "data_import_widget" --include="*.py" .
grep -r "DataImportWidget" --include="*.py" .
grep -r "batch_import_dialog" --include="*.py" .
grep -r "BatchImportDialog" --include="*.py" .
```

## 执行顺序

### 第1步: 备份
1. 创建备份目录
2. 复制要删除的文件到备份目录

### 第2步: 删除UI组件文件
1. 删除 `gui/widgets/data_import_widget.py`
2. 删除 `gui/dialogs/batch_import_dialog.py`

### 第3步: 更新协调器
1. 修改 `_on_duckdb_import()` 方法，重定向到增强版
2. 删除 `_on_batch_import()` 方法

### 第4步: 更新菜单
1. 删除重复的菜单项
2. 更新增强版菜单项文本和快捷键
3. 清理信号连接

### 第5步: 验证测试
1. 运行相关测试
2. 手动测试菜单功能
3. 确认增强版系统正常工作

## 风险控制

### 回滚计划
如果清理过程中出现问题:
1. 从备份目录恢复文件
2. 撤销对协调器的修改
3. 恢复菜单配置

### 验证检查点
每个阶段完成后进行验证:
1. 编译检查 (无语法错误)
2. 导入检查 (无导入错误)
3. 功能检查 (增强版系统正常)
4. 菜单检查 (菜单项正常显示和响应)

## 预期结果

### 清理后的系统结构
1. **统一的数据导入入口**: 只保留增强版智能导入
2. **简化的菜单结构**: 消除重复和困惑
3. **功能完整性**: 所有导入功能通过增强版系统提供
4. **代码简洁性**: 删除冗余代码，提高维护性

### 用户体验改进
1. **单一入口**: 用户只需要了解一个数据导入系统
2. **功能集中**: 所有导入相关功能集中在增强版系统中
3. **一致性**: 统一的UI风格和操作体验

## 注意事项

1. **保留核心引擎**: 不删除 `import_execution_engine.py` 等核心组件
2. **保留配置管理**: 不删除 `import_config_manager.py` 等配置组件
3. **渐进执行**: 每步都要验证，确保系统稳定
4. **文档更新**: 清理完成后更新相关文档
