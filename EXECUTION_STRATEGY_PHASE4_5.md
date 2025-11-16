# Phase 4-5 执行策略

## 目标
确保实时写入功能正确工作并与UI无缝集成，每一项功能都必须通过验证。

## Phase 4 验证执行 (1周)

### 第1天: 基础验证

#### 步骤 1: 运行集成验证脚本
```bash
python verify_integration.py
```

**预期输出**:
```
✅ 所有验证通过！
```

**若失败**:
- 检查导入语句
- 检查文件是否被正确保存
- 查看错误日志

#### 步骤 2: 代码审查
- [ ] 检查 _import_kline_data() 是否包含实时写入逻辑
- [ ] 检查事件是否在正确的位置发布
- [ ] 验证错误处理是否完整
- [ ] 确认降级机制存在

### 第2天: 事件流程验证

#### 步骤 3: 事件发布验证
创建测试脚本验证事件流程：

```python
from core.events import get_event_bus
from core.events.realtime_write_events import WriteProgressEvent

event_bus = get_event_bus()

# 创建测试事件
event = WriteProgressEvent(
    task_id="verify_001",
    symbol="000001",
    progress=50.0,
    written_count=5,
    total_count=10,
    write_speed=100.0,
    success_count=5,
    failure_count=0
)

# 发布事件
event_bus.publish(event)

# 验证事件被处理
# (检查事件处理器日志)
```

**验证点**:
- [ ] 事件成功发布
- [ ] 事件被处理器接收
- [ ] 统计信息正确更新

#### 步骤 4: 服务验证
```python
from core.containers import get_service_container
from core.services.realtime_write_service import RealtimeWriteService
import pandas as pd

container = get_service_container()
service = container.resolve(RealtimeWriteService)

# 测试启动
service.start_write("test_001")

# 测试写入
test_data = pd.DataFrame({
    'symbol': ['000001'],
    'datetime': [pd.Timestamp.now()],
    'open': [10.0],
    'high': [11.0],
    'low': [9.5],
    'close': [10.5],
    'volume': [1000000]
})

success = service.write_data("000001", test_data, "STOCK_A")

# 测试完成
service.complete_write("test_001")
```

**验证点**:
- [ ] 服务成功启动
- [ ] 数据成功写入
- [ ] 任务成功完成

### 第3-4天: 小规模导入测试

#### 步骤 5: 小规模数据导入
运行包含 5-10 只股票的导入任务：

```python
from core.importdata.import_execution_engine import DataImportExecutionEngine
from core.importdata.import_config_manager import ImportTaskConfig, DataFrequency, ImportMode
from datetime import datetime, timedelta

config = ImportTaskConfig(
    task_id="verify_kline_001",
    name="验证K线导入",
    data_source="akshare",
    asset_type="STOCK_A",
    data_type="kline",
    symbols=["000001", "000002", "000003"],  # 小规模
    frequency=DataFrequency.DAILY,
    mode=ImportMode.MANUAL,
    start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
    end_date=datetime.now().strftime('%Y-%m-%d'),
    max_workers=2,
)

engine = DataImportExecutionEngine()
result = engine.execute_import(config)
```

**验证项目表**:

| 验证项 | 预期结果 | 实际结果 | 状态 |
|--------|---------|---------|------|
| 任务状态 | SUCCESS | | ✓ |
| 处理的符号数 | 3 | | ✓ |
| 总记录数 | > 0 | | ✓ |
| 错误数 | 0 | | ✓ |
| WriteStartedEvent | 发布 | | ✓ |
| WriteProgressEvent | 多次发布 | | ✓ |
| WriteCompletedEvent | 发布 | | ✓ |
| 数据库写入 | 成功 | | ✓ |

#### 步骤 6: 数据库验证
验证数据是否正确写入：

```python
from core.asset_database_manager import AssetSeparatedDatabaseManager
from core.plugin_types import AssetType

manager = AssetSeparatedDatabaseManager()

# 查询数据
result = manager.query_data(
    asset_type=AssetType.STOCK_A,
    symbol="000001"
)

# 验证
assert len(result) > 0, "未找到数据"
assert 'datetime' in result.columns, "缺少datetime列"
assert 'open' in result.columns, "缺少open列"
assert 'close' in result.columns, "缺少close列"
```

**验证点**:
- [ ] 数据已写入数据库
- [ ] 所有列都存在
- [ ] 数据完整无缺失

#### 步骤 7: 事件序列验证
检查完整的事件序列是否正确发布：

1. **WriteStartedEvent** (任务开始)
   - 包含: task_id, task_name, symbols, total_records
   - 时间: 任务初始化后

2. **WriteProgressEvent** (每个符号)
   - 包含: 进度%, 已写数, 总数, 写入速度
   - 次数: symbols 数量

3. **WriteCompletedEvent** (任务完成)
   - 包含: 总统计, 耗时, 平均速度
   - 时间: 任务完成后

### 第5天: 中等规模测试

#### 步骤 8: 运行 100 只股票导入
```python
# 相同的代码，但 symbols 改为 100 只
config.symbols = load_100_symbols()
result = engine.execute_import(config)
```

**验证指标**:
- [ ] 所有事件正确发布
- [ ] 写入速度 > 100条/秒
- [ ] 内存占用稳定
- [ ] 数据完整性

### 第6-7天: 故障场景测试

#### 步骤 9: 网络中断模拟
- [ ] 测试网络错误恢复
- [ ] 验证 WriteErrorEvent 发布
- [ ] 检查错误日志完整性

#### 步骤 10: 数据库离线测试
- [ ] 模拟数据库连接失败
- [ ] 验证错误处理
- [ ] 检查降级到批量模式

#### 步骤 11: 异常数据处理
- [ ] 测试无效数据
- [ ] 验证数据验证逻辑
- [ ] 确保系统继续处理

## Phase 5 UI集成执行 (2周)

### 第1周: 基础UI集成

#### 任务 1: 进度条显示
```python
# 在 EnhancedDataImportWidget 中添加
from PyQt5.QtWidgets import QProgressBar

progress_bar = QProgressBar()
progress_bar.setRange(0, 100)

# 订阅进度事件
def on_progress_update(event):
    progress_bar.setValue(int(event.progress))

event_bus.subscribe(WriteProgressEvent, on_progress_update)
```

**验证**:
- [ ] 进度条显示正确的百分比
- [ ] 实时更新（< 500ms 延迟）
- [ ] 任务完成时显示 100%

#### 任务 2: 实时信息显示
```python
# 显示实时统计信息
info_label = QLabel()

def on_progress_update(event):
    info_label.setText(
        f"速度: {event.write_speed:.0f} 条/秒 | "
        f"已写: {event.written_count}/{event.total_count} | "
        f"成功: {event.success_count} | "
        f"失败: {event.failure_count}"
    )
```

**验证**:
- [ ] 显示的数据准确
- [ ] 实时更新

#### 任务 3: 控制按钮
```python
# 添加暂停、恢复、取消按钮
pause_button = QPushButton("暂停")
resume_button = QPushButton("恢复")
cancel_button = QPushButton("取消")

def on_pause():
    realtime_service.pause_write(task_id)

def on_resume():
    realtime_service.resume_write(task_id)

def on_cancel():
    realtime_service.cancel_write(task_id)
```

**验证**:
- [ ] 按钮点击有效
- [ ] 任务状态正确更新
- [ ] UI 反馈及时

#### 任务 4: 错误日志显示
```python
# 显示错误日志
error_log = QTextEdit()

def on_error(event):
    error_log.append(
        f"[{event.timestamp}] {event.symbol}: "
        f"{event.error_type} - {event.error}"
    )
```

**验证**:
- [ ] 错误显示完整
- [ ] 格式清晰易读
- [ ] 实时更新

### 第2周: UI增强和优化

#### 任务 5: 统计面板
```python
# 显示完整的任务统计
stats_panel = QGroupBox("任务统计")

def on_completed(event):
    stats_text = f"""
    总符号数: {event.total_symbols}
    成功: {event.success_count}
    失败: {event.failure_count}
    总记录: {event.total_records}
    耗时: {event.duration:.1f}秒
    平均速度: {event.average_speed:.0f}条/秒
    """
```

**验证**:
- [ ] 统计数据准确
- [ ] 显示格式美观
- [ ] 单位正确

#### 任务 6: 性能监控
```python
# 实时显示性能指标
performance_label = QLabel()

def on_progress(event):
    performance_label.setText(
        f"写入速度: {event.write_speed:.0f}条/秒 | "
        f"进度: {event.progress:.1f}%"
    )
```

**验证**:
- [ ] 速度计算准确
- [ ] 显示及时
- [ ] 峰值记录正确

#### 任务 7: 用户体验优化
- [ ] 添加加载动画
- [ ] 显示预计完成时间
- [ ] 优化刷新频率（避免过度更新）
- [ ] 添加音频/视觉提示

**验证**:
- [ ] UI 流畅无卡顿
- [ ] 响应速度 < 100ms
- [ ] 用户体验良好

## 验证清单

### Phase 4 验证清单
- [ ] 所有导入都通过基础验证
- [ ] 事件流程完整
- [ ] 小规模导入成功
- [ ] 中等规模导入成功
- [ ] 故障场景正确处理
- [ ] 数据库完整性验证通过
- [ ] 写入速度达到预期

### Phase 5 验证清单
- [ ] 进度条正确显示
- [ ] 实时信息准确
- [ ] 控制按钮功能完好
- [ ] 错误日志显示清晰
- [ ] 统计面板数据准确
- [ ] 性能监控有效
- [ ] UI 流畅无卡顿

## 故障排查指南

### 事件未发布
1. 检查 REALTIME_WRITE_AVAILABLE 是否为 True
2. 查看 logger.warning 中的初始化失败信息
3. 验证 EventBus 是否正常工作

### 数据未写入
1. 检查 AssetSeparatedDatabaseManager 是否初始化
2. 查看数据库错误日志
3. 验证 asset_type 是否正确

### 进度不更新
1. 检查事件处理器是否注册
2. 查看 WriteProgressEvent 是否发布
3. 验证 UI 事件回调是否绑定

## 完成标准
- ✅ 所有导入方法都支持实时写入
- ✅ 所有事件都正确发布
- ✅ UI 实时显示进度
- ✅ 系统性能达到预期
- ✅ 异常正确处理
- ✅ 每一项功能都通过验证

## 时间估计
- Phase 4: 1 周 (7 天)
- Phase 5: 2 周 (14 天)
- 总计: 3 周 (21 天)
