# 方案A实时写入配置重构 - 最终决策

## 用户确认
- ✅ 执行方案A（合并为单一策略选择器）
- ✅ 不添加兼容层或转换层
- ✅ 直接使用对应字段

## 修改范围（7个位置）

### 位置A-B：UI控件（enhanced_data_import_widget.py）
- 删除enable_realtime_write_cb（第1255-1259行）
- 更新write_strategy选项为4个（第1278-1280行）
- 删除checkbox从realtime_row布局

### 位置C-E：配置收集和重置
- 删除'enable_realtime_write'字段收集（第2680行）
- 更新验证显示，删除enable_realtime_write显示（第3992行）
- 修改重置为写入策略重置为"禁用写入"（第4060-4063行）

### 位置F-G：事件处理
- 删除on_realtime_write_toggled()方法（第4468-4492行）
- 创建on_write_strategy_changed()方法处理策略变更

## 4个新策略
1. "禁用写入" - 不执行写入
2. "批量写入" - 累积批量后写入
3. "实时写入" - 单条立即写入
4. "自适应" - 根据系统负载选择

## 后端字段处理
后端直接读取write_strategy字段，根据值判断启用/禁用和策略类型
不需要enable_realtime_write字段