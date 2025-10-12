# 未定义变量 base_config 修复说明

## 问题描述

在 `gui/widgets/enhanced_data_import_widget.py` 的 `start_import()` 方法中，第2014行使用了未定义的变量 `base_config.data_type`：

```python
# ❌ 错误代码
data_type=base_config.data_type,  # base_config 未定义
```

## 问题影响

- 运行时会抛出 `NameError: name 'base_config' is not defined`
- 导致任务创建失败
- 无法启动数据导入任务

## 修复方案

将 `data_type` 参数改为直接从UI控件读取：

```python
# ✅ 修复后
data_type=self.data_type_combo.currentText() if hasattr(self, 'data_type_combo') else "K线数据",
```

## 修复逻辑

1. **直接读取UI**: 使用 `self.data_type_combo.currentText()` 从界面获取用户选择的数据类型
2. **防护检查**: 使用 `hasattr(self, 'data_type_combo')` 检查控件是否存在
3. **默认值**: 如果控件不存在，使用 `"K线数据"` 作为默认值
4. **保持一致**: 与其他参数读取方式保持一致（如第2013行的 `asset_type`）

## 代码对比

### 修复前
```python
task_config = ImportTaskConfig(
    task_id=f"task_{int(datetime.now().timestamp())}",
    name=task_name,
    symbols=symbols,
    data_source=self.data_source_combo.currentText(),
    asset_type=self.asset_type_combo.currentText(),
    data_type=base_config.data_type,  # ❌ 未定义变量
    frequency=freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY),
    ...
)
```

### 修复后
```python
task_config = ImportTaskConfig(
    task_id=f"task_{int(datetime.now().timestamp())}",
    name=task_name,
    symbols=symbols,
    data_source=self.data_source_combo.currentText(),
    asset_type=self.asset_type_combo.currentText(),
    data_type=self.data_type_combo.currentText() if hasattr(self, 'data_type_combo') else "K线数据",  # ✅ 从UI读取
    frequency=freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY),
    ...
)
```

## 测试建议

1. 启动应用
2. 在数据导入界面输入股票代码
3. 选择数据类型（如"K线数据"）
4. 点击"开始导入"
5. 确认任务能够成功创建和启动

## 修改文件

- `gui/widgets/enhanced_data_import_widget.py` (行2014)

## 修复状态

✅ 已完成
✅ 无linting错误
✅ 逻辑正确

## 相关问题

这个问题可能是之前代码重构时遗留的，原本可能有一个 `base_config` 变量用于提供默认配置，但在当前代码版本中已被移除，而这一行未同步更新。

现在所有配置参数都直接从UI控件读取，保持了代码的一致性和简洁性。

