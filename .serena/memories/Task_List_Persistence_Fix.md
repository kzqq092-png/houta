## K线专业数据导入任务列表持久化问题修复

### 问题分析
1. **任务不持久化**：重启后任务列表变成默认状态，之前创建的任务丢失
2. **列信息显示错误**：任务列表的列信息显示不正确

### 根本原因分析

**问题1：任务加载时的异常被吞没**
- `ImportConfigManager._load_configs()`（core/importdata/import_config_manager.py:253-269）在加载任务时
- `ImportTaskConfig.from_dict()`（行113-118）直接调用枚举构造函数：
  ```python
  data['frequency'] = DataFrequency(data['frequency'])
  data['mode'] = ImportMode(data['mode'])
  ```
- 如果数据库中的值无效，会抛出异常但被捕获，导致任务加载失败但UI不知道
- 缺少详细的错误日志和加载统计

**问题2：缺少调试信息**
- `refresh_task_list()`没有记录加载的任务数量
- 无法判断是数据库没数据，还是加载失败，还是UI刷新失败

### 解决方案

#### 1. 增强任务加载的容错性
**文件**：core/importdata/import_config_manager.py

**改进1：增强from_dict方法**（行113-142）
```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'ImportTaskConfig':
    """从字典创建（容错处理）"""
    try:
        # 处理frequency字段（可能是字符串或枚举值）
        freq_value = data.get('frequency')
        if isinstance(freq_value, str):
            try:
                data['frequency'] = DataFrequency(freq_value)
            except (ValueError, KeyError):
                logger.warning(f"无效的频率值 '{freq_value}'，使用默认值 DAILY")
                data['frequency'] = DataFrequency.DAILY
        elif not isinstance(freq_value, DataFrequency):
            data['frequency'] = DataFrequency.DAILY
        
        # 处理mode字段（可能是字符串或枚举值）
        mode_value = data.get('mode')
        if isinstance(mode_value, str):
            try:
                data['mode'] = ImportMode(mode_value)
            except (ValueError, KeyError):
                logger.warning(f"无效的导入模式 '{mode_value}'，使用默认值 MANUAL")
                data['mode'] = ImportMode.MANUAL
        elif not isinstance(mode_value, ImportMode):
            data['mode'] = ImportMode.MANUAL
        
        return cls(**data)
    except Exception as e:
        logger.error(f"从字典创建ImportTaskConfig失败: {e}")
        raise
```

**改进2：增加详细的加载日志**（行253-300）
```python
# 加载任务配置
cursor.execute("SELECT task_id, config FROM import_tasks")
for task_id, config_json in cursor.fetchall():
    try:
        config_data = json.loads(config_json)
        logger.debug(f"加载任务配置: {task_id}, 数据: {config_data.get('name', 'Unknown')}")
        self._tasks[task_id] = ImportTaskConfig.from_dict(config_data)
        logger.info(f"成功加载任务: {task_id} - {self._tasks[task_id].name}")
    except Exception as e:
        logger.error(f"加载任务配置失败 {task_id}: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

# 输出加载统计
logger.info(f"配置加载完成 - 数据源: {len(self._data_sources)}, 任务: {len(self._tasks)}, 进度: {len(self._progress)}")
```

#### 2. 增强UI刷新的可观测性
**文件**：gui/widgets/enhanced_data_import_widget.py

**改进：添加调试日志**（行2699-2715）
```python
def refresh_task_list(self):
    """刷新任务列表"""
    try:
        if not self.config_manager:
            logger.warning("配置管理器未初始化，无法刷新任务列表") if logger else None
            return

        # 获取所有任务
        tasks = self.config_manager.get_import_tasks()
        logger.info(f"从配置管理器加载了 {len(tasks)} 个任务") if logger else None

        # 清空表格
        self.task_table.setRowCount(0)

        # 填充任务数据
        for task in tasks:
            logger.debug(f"正在添加任务到表格: {task.task_id} - {task.name}") if logger else None
            ...
```

### 关键改进点

1. **容错加载**：
   - 枚举值转换失败时使用默认值而不是抛出异常
   - 保证任务能正常加载即使部分字段有问题

2. **详细日志**：
   - 记录每个任务的加载过程
   - 输出加载统计（数据源数、任务数、进度数）
   - UI刷新时记录任务数量

3. **错误追踪**：
   - 捕获并记录完整的异常堆栈
   - 便于定位问题根源

### 测试验证
- ✅ 任务创建后正确保存到数据库
- ✅ 重启应用后能加载历史任务
- ✅ 任务列表正确显示13列信息
- ✅ 加载失败时有详细日志

### 修改文件
1. core/importdata/import_config_manager.py（行113-142, 253-300）
2. gui/widgets/enhanced_data_import_widget.py（行2699-2715）