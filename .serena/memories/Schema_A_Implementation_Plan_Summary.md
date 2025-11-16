# 方案A 实施计划总结

## 目标
删除底部数据质量Dock浮窗，消除100%视觉重复，保留并增强右侧Tab。

## 7项代码删除操作

### 操作1-7（总计83行代码删除）

**文件1: gui/enhanced_main_window_integration.py**
- 第226-256行：删除_integrate_quality_monitor方法(31行)
- 第319-326行：删除菜单项代码块(8行)
- 第104行：删除集成方法调用("quality_monitor", self._integrate_quality_monitor)
- 第35行：清理DataQualityMonitorTab导入

**文件2: core/coordinators/main_window_coordinator.py**
- 第3322-3325行：删除DataQualityMonitorTab初始化(4行)
- 第3365-3371行：删除Dock创建代码(7行)
- 第3444-3455行：删除_on_toggle_quality_monitor_panel方法(12行)

## 关键发现
- 两个文件都创建了相同的Dock，导致100%重复
- DataQualityMonitorTab被多次初始化
- 菜单切换方法在main_window_coordinator中

## 验证流程（4阶段）
1. 代码删除 - 使用MCP工具逐个删除
2. 语法验证 - python -m py_compile
3. 导入验证 - 导入测试
4. 启动测试 - UI验证

## 增强方案
1. 快捷访问按钮 - 左侧面板底部
2. 状态指示器 - 标题栏右侧
3. 菜单调整 - 增强功能菜单优化