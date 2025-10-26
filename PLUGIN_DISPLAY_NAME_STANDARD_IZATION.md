# 插件显示名称标准化方案

**日期**: 2025-10-19  
**目标**: 规范插件 display_name，避免UI层硬编码映射  
**状态**: 📋 方案设计中

---

## 问题分析

### 当前问题
1. ✅ **已修复**：UI层删除了硬编码映射表
2. ⚠️ **待优化**：`_generate_friendly_name()` 仍然做映射转换
3. ⚠️ **根本问题**：插件 `display_name` 不是必填，导致UI需要备用方案

### 用户建议 ✨
> "不需要做数据源名称的映射，在插件接口里设置属性名称为必填，这样就可以直接获取插件友好的名字了，不用在中间转换方便后续扩展，而且在插件管理中心也可以看到对应的插件详细介绍"

---

## 插件接口现状

### 1. 统一插件接口（core/interfaces/plugin.py）

#### PluginInfo 定义
```python
@dataclass
class PluginInfo:
    """插件信息"""
    
    # 基础信息
    name: str                    # ✅ 必填
    version: str                 # ✅ 必填  
    description: str = ""        # ❌ 可选
    
    # 插件类型和分类
    plugin_type: PluginType = PluginType.UTILITY
    category: str = "general"
    
    # 作者和许可信息
    author: str = ""             # ❌ 可选
    license: str = ""
    homepage: str = ""
```

**优点**:
- ✅ `name` 已经是必填字段
- ✅ 完整的插件元信息结构

**问题**:
- ⚠️ `name` 字段语义不明确（技术名？显示名？）
- ⚠️ 没有明确的 `display_name` 字段

---

### 2. 数据源插件接口（core/data_source_extensions.py）

#### PluginInfo 定义
```python
@dataclass
class PluginInfo:
    """插件信息"""
    id: str                      # ✅ 必填 - 唯一标识
    name: str                    # ✅ 必填 - 显示名称
    version: str                 # ✅ 必填
    description: str             # ✅ 必填
    author: str                  # ✅ 必填
    supported_asset_types: List[AssetType]   # ✅ 必填
    supported_data_types: List[DataType]     # ✅ 必填
    capabilities: Dict[str, Any]  # ✅ 必填
```

**优点**:
- ✅ 字段语义清晰：`id` (技术标识) + `name` (显示名称)
- ✅ 所有核心字段都是必填
- ✅ 数据源特定信息完整

---

### 3. PluginManager 处理逻辑

#### 当前获取显示名称的逻辑（plugin_manager.py:1800-1828）
```python
plugin_display_name = plugin_name  # 默认使用插件模块名

if v2_info is not None:
    # 使用V2插件信息（包含中文名称）
    plugin_display_name = v2_info.name
elif metadata and 'display_name' in metadata:
    # 使用metadata中的显示名称
    plugin_display_name = metadata['display_name']
elif metadata and 'name' in metadata:
    # 使用metadata中的名称
    plugin_display_name = metadata['name']
else:
    # 后备方案：从插件实例获取
    plugin_display_name = getattr(plugin_instance, 'name', plugin_name)
```

**问题**:
- ⚠️ 多层备用逻辑复杂
- ⚠️ 没有强制插件提供 display_name

---

## 优化方案

### 方案A: 统一使用 `display_name` 字段（推荐）⭐

#### 1. 修改 PluginInfo 接口

**文件**: `core/interfaces/plugin.py`

```python
@dataclass
class PluginInfo:
    """插件信息"""
    
    # 基础信息（必填）
    plugin_id: str               # 插件唯一标识（如：data_sources.akshare_plugin）
    display_name: str            # 友好显示名称（如：AKShare、东方财富）✨ 新增必填
    version: str                 # 版本号
    description: str             # 插件描述 ✨ 改为必填
    
    # 插件类型和分类
    plugin_type: PluginType = PluginType.UTILITY
    category: str = "general"
    
    # 作者和许可信息
    author: str = ""
    license: str = ""
    homepage: str = ""
    
    # 技术信息
    module_path: str = ""
    entry_point: str = "create_plugin"
    
    # ... 其他字段保持不变
```

**变更**:
1. ✅ 新增 `plugin_id` 字段（技术标识）
2. ✅ 重命名 `name` → `display_name`（语义更清晰）
3. ✅ `description` 改为必填（无默认值）
4. ✅ 向后兼容：保留 `name` 属性映射到 `display_name`

---

#### 2. 修改数据源插件接口

**文件**: `core/data_source_extensions.py`

```python
@dataclass
class PluginInfo:
    """数据源插件信息"""
    
    # 基础信息（必填）
    plugin_id: str               # 插件唯一标识 ✨ id → plugin_id
    display_name: str            # 友好显示名称 ✨ name → display_name  
    version: str
    description: str
    author: str
    
    # 数据源特定信息（必填）
    supported_asset_types: List[AssetType]
    supported_data_types: List[DataType]
    capabilities: Dict[str, Any]
    
    # 向后兼容属性
    @property
    def id(self) -> str:
        """兼容旧代码的 id 属性"""
        return self.plugin_id
    
    @property
    def name(self) -> str:
        """兼容旧代码的 name 属性"""
        return self.display_name
```

---

#### 3. 修改 PluginManager 验证逻辑

**文件**: `core/plugin_manager.py`

```python
def _validate_plugin_info(self, plugin_instance, plugin_name: str) -> PluginInfo:
    """验证并获取插件信息"""
    
    # 1. 尝试从V2接口获取
    if hasattr(plugin_instance, 'get_plugin_info'):
        info = plugin_instance.get_plugin_info()
        
        # 验证必填字段
        if not hasattr(info, 'display_name') or not info.display_name:
            raise ValueError(
                f"插件 {plugin_name} 的 PluginInfo 缺少必填字段 'display_name'。\n"
                f"请在插件中定义友好的显示名称，例如：\n"
                f"  display_name='AKShare'  # 或 '东方财富'、'Binance' 等"
            )
        
        if not hasattr(info, 'description') or not info.description:
            raise ValueError(
                f"插件 {plugin_name} 的 PluginInfo 缺少必填字段 'description'。\n"
                f"请提供插件的简要描述。"
            )
        
        return info
    
    # 2. 旧版插件检查
    if hasattr(plugin_instance, 'plugin_info'):
        info = plugin_instance.plugin_info
        
        # 如果是旧格式，自动转换
        if not hasattr(info, 'display_name'):
            logger.warning(
                f"插件 {plugin_name} 使用旧版 PluginInfo 格式，"
                f"请升级到新版本并添加 'display_name' 字段"
            )
            # 尝试从旧字段获取
            display_name = getattr(info, 'name', plugin_name)
            # 打补丁（临时兼容）
            info.display_name = display_name
        
        return info
    
    # 3. 完全不兼容的插件
    raise ValueError(
        f"插件 {plugin_name} 未实现标准接口。\n"
        f"请实现 get_plugin_info() 方法并返回包含 'display_name' 的 PluginInfo。"
    )
```

---

#### 4. 简化 UI 层代码

**文件**: `gui/widgets/enhanced_data_import_widget.py`

**修改前**（当前代码）:
```python
def _generate_friendly_name(self, plugin_name: str, plugin_info: dict) -> str:
    """为插件生成友好的显示名称"""
    # 硬编码映射表
    name_mapping = {
        'akshare': 'AKShare',
        'eastmoney': '东方财富',
        # ... 20行代码
    }
    # 复杂的转换逻辑
    # ...
```

**修改后**（优化后）:
```python
def _load_available_data_sources(self):
    """动态加载可用的数据源插件"""
    try:
        plugin_manager = PluginManager.get_instance()
        
        if plugin_manager and hasattr(plugin_manager, 'plugins'):
            data_source_plugins = []
            
            for plugin_name, plugin_info in plugin_manager.plugins.items():
                if 'data_sources' in plugin_name:
                    # ✅ 直接使用插件的 display_name，无需转换
                    display_name = plugin_info.display_name
                    
                    data_source_plugins.append({
                        'plugin_id': plugin_name,
                        'display_name': display_name,
                        'info': plugin_info
                    })
            
            # 按显示名称排序
            data_source_plugins.sort(key=lambda x: x['display_name'])
            
            # 填充下拉列表
            self.data_source_combo.clear()
            self.data_source_mapping = {}
            
            for plugin in data_source_plugins:
                self.data_source_combo.addItem(plugin['display_name'])
                self.data_source_mapping[plugin['display_name']] = plugin['plugin_id']
            
            logger.info(f"成功加载 {len(data_source_plugins)} 个数据源插件")
            return True
        
        # 备用方案
        self._load_default_data_sources()
        return False
        
    except Exception as e:
        logger.error(f"加载数据源失败: {e}")
        self._load_default_data_sources()
        return False
```

**代码简化**:
- ❌ 删除 `_generate_friendly_name()` 方法（60行）
- ❌ 删除硬编码映射表（15行）
- ✅ 直接使用 `plugin_info.display_name`
- ✅ 代码从 130行 → 40行

---

### 方案B: 保持 `name` 字段，但改为必填（兼容性更好）

#### 优点
- ✅ 不需要修改现有插件
- ✅ 向后兼容性最好

#### 缺点
- ⚠️ `name` 语义仍不够明确
- ⚠️ 需要在文档中强调 `name` 是显示名称

---

## 实施步骤

### Phase 1: 接口规范化
1. ✅ 修改 `core/interfaces/plugin.py` 的 `PluginInfo`
2. ✅ 修改 `core/data_source_extensions.py` 的 `PluginInfo`
3. ✅ 添加向后兼容属性
4. ✅ 更新接口文档

### Phase 2: PluginManager 增强验证
1. ✅ 添加 `_validate_plugin_info()` 方法
2. ✅ 在插件加载时强制验证 `display_name`
3. ✅ 提供清晰的错误提示
4. ✅ 兼容旧版插件（自动转换）

### Phase 3: 简化 UI 层
1. ✅ 删除 `_generate_friendly_name()` 方法
2. ✅ 删除硬编码映射表
3. ✅ 直接使用 `plugin_info.display_name`
4. ✅ 测试UI显示

### Phase 4: 更新现有插件
1. 📋 为所有数据源插件添加 `display_name`
2. 📋 验证所有插件信息完整性
3. 📋 更新插件文档和示例

### Phase 5: 文档和指南
1. 📋 更新插件开发文档
2. 📋 提供插件模板
3. 📋 说明必填字段

---

## 插件示例

### 标准数据源插件示例

```python
# plugins/data_sources/akshare_plugin.py

from core.data_source_extensions import IDataSourcePlugin, PluginInfo, AssetType, DataType

class AKSharePlugin(IDataSourcePlugin):
    """AKShare 数据源插件"""
    
    @property
    def plugin_info(self) -> PluginInfo:
        return PluginInfo(
            plugin_id="data_sources.akshare_plugin",  # 唯一标识
            display_name="AKShare",                    # ✨ 友好显示名称（必填）
            version="1.0.0",
            description="AKShare金融数据接口，提供A股、指数、基金等数据",  # ✨ 必填
            author="FactorWeave团队",
            supported_asset_types=[
                AssetType.STOCK,
                AssetType.INDEX,
                AssetType.FUND
            ],
            supported_data_types=[
                DataType.HISTORICAL_KLINE,
                DataType.REAL_TIME_QUOTE
            ],
            capabilities={
                "rate_limit": 100,
                "supports_realtime": True
            }
        )
    
    # ... 其他方法实现
```

### 中文显示名称示例

```python
# 示例1: 东方财富插件
display_name="东方财富"

# 示例2: Binance插件
display_name="Binance"

# 示例3: 火币插件
display_name="火币"

# 示例4: 通达信插件
display_name="通达信"
```

---

## 优势分析

### 1. 代码简洁性
**修改前**:
- PluginManager: 复杂的备用逻辑（30行）
- UI层: 硬编码映射表 + 转换逻辑（75行）
- 总计: 105行额外代码

**修改后**:
- PluginManager: 清晰的验证逻辑（20行）
- UI层: 直接使用（10行）
- 总计: 30行核心代码
- **净减少**: 75行代码

### 2. 可维护性
- ✅ 插件自治：名称定义在插件内部
- ✅ 无硬编码：UI层无需维护映射表
- ✅ 强制规范：必填字段确保质量

### 3. 扩展性
- ✅ 新插件：只需定义 `display_name`，自动出现在UI
- ✅ 多语言：未来可支持 `display_name_i18n`
- ✅ 插件市场：直接使用插件提供的名称和描述

### 4. 用户体验
- ✅ 一致性：插件管理中心和UI使用相同名称
- ✅ 准确性：插件作者最了解如何命名
- ✅ 专业性：显示官方名称（如 "AKShare"）

---

## 风险评估

### 低风险 ✅
- 向后兼容：旧插件自动转换
- 渐进式：可分阶段实施
- 验证清晰：明确的错误提示

### 需要注意 ⚠️
1. **现有插件迁移**
   - 需要逐个更新插件
   - 提供迁移工具和文档

2. **第三方插件**
   - 需要通知第三方开发者
   - 提供兼容期和迁移指南

3. **测试覆盖**
   - 测试所有内置插件
   - 测试兼容模式

---

## 迁移计划

### 第一批（核心数据源，1天）
- `data_sources.akshare_plugin`
- `data_sources.eastmoney_plugin`
- `data_sources.sina_plugin`
- `data_sources.tongdaxin_plugin`

### 第二批（扩展数据源，1天）
- `data_sources.tushare_plugin`
- `data_sources.binance_plugin`
- `data_sources.huobi_plugin`
- 其他加密货币数据源

### 第三批（其他类型插件，2天）
- 情绪数据源插件
- 指标插件
- 策略插件

---

## 测试计划

### 单元测试
```python
def test_plugin_info_validation():
    """测试插件信息验证"""
    # 测试必填字段
    with pytest.raises(ValueError, match="缺少必填字段 'display_name'"):
        validate_plugin(plugin_without_display_name)
    
    # 测试正常插件
    plugin = validate_plugin(valid_plugin)
    assert plugin.display_name == "AKShare"

def test_ui_data_source_loading():
    """测试UI数据源加载"""
    widget = EnhancedDataImportWidget()
    widget._load_available_data_sources()
    
    # 验证下拉列表
    assert widget.data_source_combo.count() > 0
    assert "AKShare" in [widget.data_source_combo.itemText(i) 
                         for i in range(widget.data_source_combo.count())]
```

### 集成测试
1. ✅ 启动系统
2. ✅ 检查所有插件正常加载
3. ✅ 打开K线数据导入UI
4. ✅ 验证数据源下拉列表显示正确名称
5. ✅ 测试插件管理中心显示一致

---

## 文档更新

### 1. 插件开发指南
```markdown
# 插件开发指南

## 必填字段

所有插件必须提供以下信息：

### display_name（必填）
- **类型**: str
- **说明**: 插件的友好显示名称
- **示例**: "AKShare"、"东方财富"、"Binance"
- **要求**: 
  - 简洁明了
  - 使用官方名称或通用名称
  - 中英文均可
  - 避免使用技术标识符

### description（必填）
- **类型**: str  
- **说明**: 插件的简要描述
- **示例**: "AKShare金融数据接口，提供A股、指数、基金等数据"
- **要求**:
  - 说明插件用途
  - 20-100字为宜
  - 清晰准确

## 完整示例

见上方"插件示例"部分
```

---

## 总结

### 方案优势
1. ✅ **根本解决**：从接口层面规范，不是UI层打补丁
2. ✅ **代码简化**：减少75行维护代码
3. ✅ **可扩展**：新插件自动支持，无需修改UI
4. ✅ **一致性**：插件管理中心和UI显示统一
5. ✅ **专业性**：使用插件官方名称

### 推荐方案
**方案A: 使用 `display_name` 字段（推荐）** ⭐

### 实施时间
- Phase 1-3: 2小时（接口+验证+UI）
- Phase 4: 1天（更新现有插件）
- Phase 5: 1天（文档）
- **总计**: 2-3天完整实施

---

**状态**: 📋 待用户确认后实施

**下一步**: 用户确认方案 → 开始实施

