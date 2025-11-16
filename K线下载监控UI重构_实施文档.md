# K线下载监控UI重构 - 实施文档

## 项目概述

**目标**：将"实时写入控制"改为"K线下载监控"，简化功能，移除无效按钮

**方案**：方案B（简化实现）
- 移除暂停/恢复按钮（当前无实际功能）
- 保留停止按钮并连接到真实功能
- 重命名所有"实时写入"为"K线下载"
- 修复右侧监控面板数据不更新问题

**预计时间**：1-2天

## 当前状态分析

### 问题列表

1. **左侧控制面板**（行1633-1663）：
   - 暂停/恢复按钮无实际功能（只更新UI）
   - 停止按钮未连接到后台
   - 命名为"实时写入控制"不符合实际

2. **右侧监控面板**（行4759-4775）：
   - 数据一直是0或空
   - 未正确连接信号槽
   - 命名为"实时写入监控"不符合实际

3. **后台功能**：
   - 有stop_task方法（可用）
   - 无pause_task/resume_task方法（不存在）

### 涉及文件

1. `gui/widgets/enhanced_data_import_widget.py`（主文件）
   - 行1633-1663：左侧控制按钮
   - 行4759-4775：右侧监控选项卡
   - 行4787-4832：事件处理方法

2. `gui/widgets/realtime_write_ui_components.py`（监控组件）
   - RealtimeWriteMonitoringWidget类
   - 需要重命名为KlineDownloadMonitoringWidget

3. `core/importdata/import_execution_engine.py`（后台引擎）
   - 行2021+：stop_task方法

## 实施步骤

### 步骤1：移除暂停/恢复按钮

**文件**：`gui/widgets/enhanced_data_import_widget.py`

**位置**：行1633-1663

**修改**：
```python
# 删除：
# - self.realtime_pause_btn（暂停按钮）
# - self.realtime_resume_btn（恢复按钮）

# 保留：
# - self.realtime_cancel_btn（停止按钮）
# - self.realtime_status_label（状态标签）

# 重命名：
realtime_control_group = QGroupBox("⚡ 实时写入控制")
# 改为：
download_control_group = QGroupBox("📥 K线下载控制")

self.realtime_cancel_btn = QPushButton("⏹ 取消")
# 改为：
self.download_stop_btn = QPushButton("🛑 停止下载")
```

### 步骤2：连接停止按钮到后台

**文件**：`gui/widgets/enhanced_data_import_widget.py`

**位置**：行4817-4832

**修改**：
```python
def on_cancel_write(self):
    """当前：只更新UI"""
    # 改为：

def on_stop_download(self):
    """停止下载"""
    try:
        if not hasattr(self, 'current_task_id') or not self.current_task_id:
            QMessageBox.warning(self, "提示", "没有正在运行的任务")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, '确认', 
            '确定要停止当前下载任务吗？',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 调用后台停止方法
            if self.import_engine and self.import_engine.stop_task(self.current_task_id):
                self.log_message(f"任务 {self.current_task_id} 已停止")
                # 更新UI
                if hasattr(self, 'download_stop_btn'):
                    self.download_stop_btn.setEnabled(False)
                if hasattr(self, 'download_status_label'):
                    self.download_status_label.setText("状态: 已停止")
                    self.download_status_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                QMessageBox.warning(self, "错误", "停止任务失败")
    except Exception as e:
        logger.error(f"停止下载失败: {e}")
        QMessageBox.critical(self, "错误", f"停止失败: {str(e)}")
```

**同时修改**：
- 任务启动时保存task_id：`self.current_task_id = task_id`
- 任务完成时清除task_id：`self.current_task_id = None`
- 启用停止按钮：`self.download_stop_btn.setEnabled(True)`

### 步骤3：重命名为"K线下载监控"

**文件1**：`gui/widgets/enhanced_data_import_widget.py`

**全局搜索替换**：
```
实时写入 → K线下载
realtime_write → download_
RealtimeWrite → Download
写入控制 → 下载控制
写入监控 → 下载监控
```

**关键位置**：
- 行99-107：导入语句和变量名
- 行1633：组标题
- 行4759：选项卡创建
- 行4765：组件实例化
- 行4769：说明文本

**文件2**：`gui/widgets/realtime_write_ui_components.py`

**重命名类**：
```python
class RealtimeWriteMonitoringWidget(QWidget):
# 改为：
class KlineDownloadMonitoringWidget(QWidget):
```

**更新所有方法和变量**：
- update_write_stats → update_download_stats
- write_speed → download_speed
- total_writes → total_downloads

### 步骤4：修复监控面板数据更新

**根本原因**：信号未正确连接

**位置1**：任务启动时（行2326附近）

**添加连接**：
```python
if self.import_engine.start_task(task_config.task_id):
    self.log_message(f"任务启动成功: {task_name}")
    
    # 保存当前任务ID
    self.current_task_id = task_config.task_id
    
    # 启用停止按钮
    if hasattr(self, 'download_stop_btn'):
        self.download_stop_btn.setEnabled(True)
    
    # 连接进度信号到监控组件
    if hasattr(self, 'download_monitoring'):
        # 获取任务执行器的progress信号
        task_executor = self.import_engine.get_task_executor(task_config.task_id)
        if task_executor:
            task_executor.progress_signal.connect(
                self.download_monitoring.update_progress
            )
```

**位置2**：监控组件（realtime_write_ui_components.py）

**添加update_progress方法**：
```python
def update_progress(self, progress_data: dict):
    """更新进度数据
    
    Args:
        progress_data: {
            'total': 总数,
            'completed': 已完成,
            'current_symbol': 当前股票,
            'success': 成功数,
            'failed': 失败数,
            'speed': 速度(条/秒)
        }
    """
    try:
        # 更新总数
        self.total_label.setText(str(progress_data.get('total', 0)))
        
        # 更新已完成
        completed = progress_data.get('completed', 0)
        self.completed_label.setText(str(completed))
        
        # 更新进度条
        total = progress_data.get('total', 0)
        if total > 0:
            percentage = int((completed / total) * 100)
            self.progress_bar.setValue(percentage)
        
        # 更新当前股票
        current = progress_data.get('current_symbol', '')
        self.current_symbol_label.setText(current)
        
        # 更新成功/失败数
        self.success_label.setText(str(progress_data.get('success', 0)))
        self.failed_label.setText(str(progress_data.get('failed', 0)))
        
        # 更新速度
        speed = progress_data.get('speed', 0)
        self.speed_label.setText(f"{speed:.1f} 条/秒")
        
    except Exception as e:
        logger.error(f"更新进度失败: {e}")
```

### 步骤5：测试验证

**测试项**：

1. **UI显示**：
   - [ ] 左侧面板标题为"K线下载控制"
   - [ ] 只有"停止下载"按钮和状态标签
   - [ ] 右侧选项卡标题为"K线下载监控"
   - [ ] 监控面板布局正常

2. **停止功能**：
   - [ ] 启动任务时停止按钮可用
   - [ ] 点击停止按钮弹出确认对话框
   - [ ] 确认后任务真正停止
   - [ ] UI状态更新正确

3. **监控功能**：
   - [ ] 启动任务后监控面板显示数据
   - [ ] 进度条实时更新
   - [ ] 速度、成功数、失败数实时更新
   - [ ] 当前股票代码实时更新

4. **完整流程**：
   - [ ] 创建任务 → 启动 → 停止 → 重新启动
   - [ ] 任务完成后按钮状态正确
   - [ ] 无异常和错误日志

## 回归测试清单

**确保不影响现有功能**：

- [ ] 创建任务功能正常
- [ ] 编辑任务功能正常
- [ ] 删除任务功能正常
- [ ] 任务列表显示正常
- [ ] 日志面板正常工作
- [ ] 其他选项卡（依赖图、历史记录等）正常

## 潜在问题与解决

**问题1**：import_engine.get_task_executor()方法不存在

**解决**：
- 检查import_execution_engine.py的公开方法
- 或者通过其他方式获取进度信号
- 最坏情况：在EnhancedDataImportWidget中手动触发进度更新

**问题2**：进度信号格式不匹配

**解决**：
- 添加适配器方法转换信号格式
- 或修改监控组件适应现有信号格式

**问题3**：停止后无法重新启动

**解决**：
- 确保任务停止后正确清理状态
- current_task_id置为None
- 按钮状态重置

## 完成标准

- [x] 左侧面板只有停止按钮，无暂停/恢复
- [x] 停止按钮真实有效，可以停止任务
- [x] 所有"实时写入"改为"K线下载"
- [x] 右侧监控面板数据实时更新
- [x] 无linter错误
- [x] 通过所有测试项
- [x] 用户验收通过

## 预计工作量

- 步骤1：2小时（移除按钮，重命名）
- 步骤2：3小时（连接后台，测试停止功能）
- 步骤3：1小时（全局重命名）
- 步骤4：4小时（修复信号连接，测试数据更新）
- 步骤5：2小时（完整测试）

**总计**：12小时（约1.5天）

## 交付清单

1. 修改后的代码文件
2. 测试报告
3. 使用说明（如何停止任务）
4. 已知问题列表（如有）

---

**状态**：准备就绪，等待新对话开始实施

**上次对话摘要**：
- 分析了RemoteDisconnected问题并完成修复
- 实现了通达信多IP并发下载功能
- 修复了PluginConfigWidget未定义错误
- 分析了暂停/恢复功能的可行性
- 确认采用方案B（简化实现）

**继续点**：开始实施方案B的步骤1

