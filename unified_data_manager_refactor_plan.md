# UnifiedDataManager重构方案

## 📋 当前问题

### 问题方法
- `_manual_register_core_plugins()` (2498-2850行，约350行)
- 硬编码导入18个examples插件
- 难以维护和扩展

## ✅ 重构方案

### 新方法设计

```python
def _register_plugins_from_plugin_manager(self) -> int:
    """
    从插件管理器动态注册数据源插件
    
    Returns:
        成功注册的插件数量
    """
    if not self.plugin_manager:
        logger.warning("插件管理器未初始化，无法注册插件")
        return 0
    
    registered_count = 0
    
    try:
        # 1. 获取所有已启用的数据源插件
        from core.plugin_types import PluginType
        
        data_source_plugins = self.plugin_manager.get_enabled_plugins_by_type(
            PluginType.DATA_SOURCE
        )
        
        logger.info(f"发现 {len(data_source_plugins)} 个已启用的数据源插件")
        
        # 2. 注册每个插件
        for plugin_id, plugin_instance in data_source_plugins.items():
            try:
                # 验证插件有必要的方法
                if not self._is_valid_data_source_plugin(plugin_instance):
                    logger.warning(f"插件缺少必要方法，跳过: {plugin_id}")
                    continue
                
                # 注册插件
                success = self.register_data_source_plugin(
                    plugin_id=plugin_id,
                    adapter=plugin_instance,
                    priority=plugin_instance.priority if hasattr(plugin_instance, 'priority') else 0,
                    weight=plugin_instance.weight if hasattr(plugin_instance, 'weight') else 1.0
                )
                
                if success:
                    registered_count += 1
                    logger.info(f"✅ 成功注册插件: {plugin_id}")
                else:
                    logger.warning(f"⚠️ 注册插件失败: {plugin_id}")
                    
            except Exception as e:
                logger.error(f"❌ 注册插件异常 {plugin_id}: {e}")
                continue
        
        logger.info(f"插件注册完成: 成功 {registered_count}/{len(data_source_plugins)}")
        return registered_count
        
    except Exception as e:
        logger.error(f"从插件管理器注册插件失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return registered_count
```

### 调用位置修改

在 `discover_and_register_data_source_plugins()` 方法中：

```python
def discover_and_register_data_source_plugins(self) -> None:
    """
    发现并注册数据源插件（公共方法）
    在所有服务初始化完成后调用
    """
    if self._plugins_discovered:
        logger.info("插件已经被发现和注册，跳过重复注册")
        return
    
    try:
        logger.info("开始发现和注册数据源插件...")
        
        # 使用新的动态加载方法（替代旧的手动注册）
        registered_count = self._register_plugins_from_plugin_manager()
        
        self._plugins_discovered = True
        logger.info(f"✅ 插件发现和注册完成: 共注册 {registered_count} 个插件")
        
    except Exception as e:
        logger.error(f"插件发现和注册失败: {e}")
        logger.error(traceback.format_exc())
```

## 🔧 实施步骤

### 步骤1: 添加新方法

在unified_data_manager.py中添加 `_register_plugins_from_plugin_manager()` 方法

**位置**: 在 `_manual_register_core_plugins()` 方法之前

### 步骤2: 修改调用

修改 `discover_and_register_data_source_plugins()` 方法：
- 注释掉 `self._manual_register_core_plugins()`
- 改为调用 `self._register_plugins_from_plugin_manager()`

### 步骤3: 测试验证

1. 运行系统
2. 检查日志，确认插件被正确加载
3. 测试数据获取功能

### 步骤4: 删除旧方法

确认新方法工作正常后：
- 删除整个 `_manual_register_core_plugins()` 方法（350+行）

## 📊 预期收益

### 代码量
- **删除**: ~350行硬编码
- **新增**: ~60行动态加载
- **净减少**: ~290行

### 维护性
- ✅ 无需手动添加新插件
- ✅ 自动发现data_sources下的所有插件
- ✅ 统一使用插件管理器
- ✅ 符合插件架构设计

### 兼容性
- ✅ 现有插件继续工作
- ✅ Plugin Manager已启用的插件会被加载
- ✅ 禁用的插件不会被加载
- ✅ 支持未来新增插件

## ⚠️ 注意事项

### 依赖条件
1. **Plugin Manager必须先初始化**
   - 在service_bootstrap中确保顺序正确

2. **插件必须在data_sources目录**
   - 或被Plugin Manager正确发现

3. **插件必须被标记为启用**
   - 通过数据库或配置文件

### 兼容性处理

如果某些插件仍在examples中且需要保留：

**临时方案**: 在删除 `_manual_register_core_plugins()` 前，先迁移或复制这些插件到data_sources

**需要迁移的插件** (如果需要保留):
- wind_data_plugin
- tongdaxin_stock_plugin (检查是否已有stock/tongdaxin_plugin)
- futures_data_plugin (通用期货)
- ctp_futures_plugin
- forex_data_plugin
- bond_data_plugin
- mysteel_data_plugin

## 🎯 成功标准

### 功能验证
- ✅ 系统正常启动
- ✅ 所有需要的数据源插件被加载
- ✅ 数据获取功能正常
- ✅ 插件管理界面显示正确

### 日志验证
应看到类似日志：
```
[INFO] 发现 X 个已启用的数据源插件
[INFO] ✅ 成功注册插件: data_sources.crypto.binance_plugin
[INFO] ✅ 成功注册插件: data_sources.stock.akshare_plugin
...
[INFO] 插件注册完成: 成功 X/Y
```

### 性能验证
- 启动时间不应明显增加
- 内存占用相似

---

**准备执行**: ✅ 方案已设计完成
**下一步**: 实施重构

