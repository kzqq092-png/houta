# 分布式UI对比分析

## 发现的重复UI

### 1. NodeManagerDialog (旧UI - 需删除)
**位置**: `gui/dialogs/node_manager_dialog.py`
**行数**: 481行
**引用位置**: `core/coordinators/main_window_coordinator.py:1352`

**特征**:
- ❌ **使用模拟数据**: `模拟节点发现`代码（第274-280行）
- ❌ 使用UDP广播发现节点（老式方法）
- ❌ 没有连接真实DistributedService
- ✅ 有节点发现/监控/配置三个标签页
- ✅ 支持手动添加节点
- ✅ 支持配置文件加载/保存

### 2. DistributedNodeMonitorDialog (新UI - 保留)
**位置**: `gui/dialogs/distributed_node_monitor_dialog.py`
**行数**: 381行
**引用位置**: `gui/menu_bar.py:1095`

**特征**:
- ✅ **使用真实数据**: 连接真实DistributedService
- ✅ 使用HTTP协议与节点通信（现代方法）
- ✅ 调用真实API: `get_all_nodes_status()`, `add_node()`, `remove_node()`, `test_node_connection()`
- ✅ 自动刷新（每5秒）
- ✅ 实时显示CPU/内存使用率
- ✅ 节点状态颜色标记（绿/黄/红）
- ✅ 简洁实用，代码量少

## 功能对比

| 功能 | NodeManagerDialog (旧) | DistributedNodeMonitorDialog (新) |
|------|------------------------|-----------------------------------|
| 数据源 | ❌ 模拟数据 | ✅ 真实DistributedService |
| 节点发现 | ❌ UDP广播（模拟） | ✅ 通过DistributedService |
| 添加节点 | ⚠️ 仅UI，无实际效果 | ✅ 调用真实API |
| 移除节点 | ❌ 未实现 | ✅ 调用真实API |
| 测试连接 | ❌ 未实现 | ✅ 调用真实API |
| 节点监控 | ⚠️ 显示模拟数据 | ✅ 显示真实数据 |
| 配置管理 | ✅ JSON配置 | ❌ 无（可扩展） |
| 自动刷新 | ⚠️ 手动刷新 | ✅ 自动刷新 |

## 合并决策

### 推荐方案：删除旧UI，更新引用

1. **删除**: `gui/dialogs/node_manager_dialog.py`
2. **更新引用**: 修改`core/coordinators/main_window_coordinator.py`中的`_on_node_management()`方法，改为使用`DistributedNodeMonitorDialog`
3. **原因**:
   - 旧UI完全是模拟数据，无实际价值
   - 新UI功能更强大且真实有效
   - 保留旧UI会误导用户

### 可选优化（不必要）

如果需要配置管理功能，可以将旧UI的配置标签页移植到新UI，但当前不是必需的。
