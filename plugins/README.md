# HIkyuu-UI 插件系统

HIkyuu-UI 2.0 提供了完整的插件生态系统，支持多种类型的插件开发和管理。

## 🚀 快速开始

### 1. 插件市场

通过主菜单 **高级功能 → 插件市场** 打开插件市场，可以：

- 浏览和搜索插件
- 安装/卸载插件
- 查看插件详情和评分
- 管理已安装的插件

### 2. 插件开发

#### 创建新插件项目

```python
from plugins.development.plugin_sdk import PluginSDK
from plugins.plugin_interface import PluginType, PluginCategory

# 初始化SDK
sdk = PluginSDK("plugins/.sdk")

# 创建技术指标插件
project_dir = sdk.create_plugin_project(
    name="我的指标",
    plugin_type=PluginType.INDICATOR,
    author="Your Name",
    email="your.email@example.com",
    description="自定义技术指标",
    category=PluginCategory.COMMUNITY
)

print(f"插件项目已创建: {project_dir}")
```

#### 构建和测试插件

```python
# 验证插件
validation_result = sdk.validate_plugin_project(project_dir)
print(f"验证结果: {validation_result}")

# 构建插件
plugin_file = sdk.build_plugin(project_dir)
print(f"插件已构建: {plugin_file}")

# 测试插件
test_result = sdk.test_plugin(project_dir)
print(f"测试结果: {test_result}")
```

## 📦 插件类型

HIkyuu-UI 支持8种插件类型：

### 1. 技术指标插件 (Indicator)

用于计算技术指标，如MACD、RSI等。

**示例**: `plugins/examples/macd_indicator.py`, `plugins/examples/rsi_indicator.py`

```python
from plugins.plugin_interface import IIndicatorPlugin, PluginType, plugin_metadata, register_plugin

@plugin_metadata(
    name="自定义指标",
    plugin_type=PluginType.INDICATOR,
    # ... 其他元数据
)
@register_plugin(PluginType.INDICATOR)
class CustomIndicatorPlugin(IIndicatorPlugin):
    def get_indicator_name(self) -> str:
        return "Custom"
    
    def calculate(self, data, **params):
        # 指标计算逻辑
        pass
```

### 2. 策略插件 (Strategy)

用于实现交易策略。

**示例**: `plugins/examples/moving_average_strategy.py`

```python
from plugins.plugin_interface import IStrategyPlugin, PluginType, plugin_metadata, register_plugin

@plugin_metadata(
    name="自定义策略",
    plugin_type=PluginType.STRATEGY,
    # ... 其他元数据
)
@register_plugin(PluginType.STRATEGY)
class CustomStrategyPlugin(IStrategyPlugin):
    def get_strategy_name(self) -> str:
        return "Custom Strategy"
    
    def generate_signals(self, data, **params):
        # 信号生成逻辑
        pass
    
    def backtest(self, data, **params):
        # 回测逻辑
        pass
```

### 3. 数据源插件 (DataSource)

用于获取外部数据。

```python
from plugins.plugin_interface import IDataSourcePlugin, PluginType, plugin_metadata, register_plugin

@plugin_metadata(
    name="自定义数据源",
    plugin_type=PluginType.DATA_SOURCE,
    # ... 其他元数据
)
@register_plugin(PluginType.DATA_SOURCE)
class CustomDataSourcePlugin(IDataSourcePlugin):
    def get_data_source_name(self) -> str:
        return "Custom DataSource"
    
    def fetch_data(self, symbol, data_type, **params):
        # 数据获取逻辑
        pass
```

### 4. 分析工具插件 (Analysis)

用于实现分析工具。

```python
from plugins.plugin_interface import IAnalysisPlugin, PluginType, plugin_metadata, register_plugin

@plugin_metadata(
    name="自定义分析工具",
    plugin_type=PluginType.ANALYSIS,
    # ... 其他元数据
)
@register_plugin(PluginType.ANALYSIS)
class CustomAnalysisPlugin(IAnalysisPlugin):
    def get_analysis_name(self) -> str:
        return "Custom Analysis"
    
    def analyze(self, data, **params):
        # 分析逻辑
        pass
```

### 5. UI组件插件 (UI Component)

用于创建自定义UI组件。

```python
from plugins.plugin_interface import IUIComponentPlugin, PluginType, plugin_metadata, register_plugin

@plugin_metadata(
    name="自定义UI组件",
    plugin_type=PluginType.UI_COMPONENT,
    # ... 其他元数据
)
@register_plugin(PluginType.UI_COMPONENT)
class CustomUIComponentPlugin(IUIComponentPlugin):
    def get_component_name(self) -> str:
        return "Custom Widget"
    
    def create_widget(self, parent=None):
        # 创建QWidget组件
        pass
```

### 6. 导出插件 (Export)

用于数据导出功能。

```python
from plugins.plugin_interface import IExportPlugin, PluginType, plugin_metadata, register_plugin

@plugin_metadata(
    name="自定义导出",
    plugin_type=PluginType.EXPORT,
    # ... 其他元数据
)
@register_plugin(PluginType.EXPORT)
class CustomExportPlugin(IExportPlugin):
    def get_export_name(self) -> str:
        return "Custom Export"
    
    def export_data(self, data, format_type, output_path, **params):
        # 导出逻辑
        pass
```

### 7. 通知插件 (Notification)

用于消息通知功能。

```python
from plugins.plugin_interface import INotificationPlugin, PluginType, plugin_metadata, register_plugin

@plugin_metadata(
    name="自定义通知",
    plugin_type=PluginType.NOTIFICATION,
    # ... 其他元数据
)
@register_plugin(PluginType.NOTIFICATION)
class CustomNotificationPlugin(INotificationPlugin):
    def get_notification_name(self) -> str:
        return "Custom Notification"
    
    def send_notification(self, title, message, **params):
        # 通知发送逻辑
        pass
```

### 8. 图表工具插件 (Chart Tool)

用于图表绘制工具。

```python
from plugins.plugin_interface import IChartToolPlugin, PluginType, plugin_metadata, register_plugin

@plugin_metadata(
    name="自定义图表工具",
    plugin_type=PluginType.CHART_TOOL,
    # ... 其他元数据
)
@register_plugin(PluginType.CHART_TOOL)
class CustomChartToolPlugin(IChartToolPlugin):
    def get_tool_name(self) -> str:
        return "Custom Chart Tool"
    
    def activate_tool(self, chart_widget):
        # 激活工具逻辑
        pass
```

## 🛠️ 插件开发指南

### 插件元数据

每个插件都需要定义元数据：

```python
@plugin_metadata(
    name="插件名称",                    # 必需
    version="1.0.0",                   # 必需
    description="插件描述",             # 必需
    author="作者名称",                  # 必需
    email="author@example.com",        # 必需
    website="https://example.com",     # 可选
    license="MIT",                     # 必需
    plugin_type=PluginType.INDICATOR,  # 必需
    category=PluginCategory.COMMUNITY, # 必需
    dependencies=["numpy", "pandas"],  # 可选
    min_hikyuu_version="2.0.0",       # 必需
    max_hikyuu_version="3.0.0",       # 必需
    tags=["标签1", "标签2"],           # 可选
    icon_path="icons/plugin.png",     # 可选
    documentation_url="https://...",   # 可选
    support_url="https://...",         # 可选
    changelog_url="https://..."        # 可选
)
```

### 插件配置

插件可以定义配置参数：

```python
def get_config_schema(self) -> Dict[str, Any]:
    return {
        'type': 'object',
        'properties': {
            'param1': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 100,
                'default': 10,
                'title': '参数1'
            },
            'param2': {
                'type': 'string',
                'enum': ['option1', 'option2'],
                'default': 'option1',
                'title': '参数2'
            }
        },
        'required': ['param1']
    }

def get_default_config(self) -> Dict[str, Any]:
    return {
        'param1': 10,
        'param2': 'option1'
    }

def validate_config(self, config: Dict[str, Any]) -> bool:
    # 配置验证逻辑
    return True
```

### 事件处理

插件可以处理系统事件：

```python
def initialize(self, context: PluginContext) -> bool:
    # 注册事件处理器
    context.register_event_handler("data_updated", self._on_data_updated)
    return True

def on_event(self, event_name: str, *args, **kwargs) -> None:
    if event_name == "data_updated":
        # 处理数据更新事件
        pass

def _on_data_updated(self, symbol: str, data: pd.DataFrame) -> None:
    # 具体的事件处理逻辑
    pass
```

### UI组件创建

插件可以创建自定义UI组件：

```python
def create_config_widget(self, parent: Optional[QWidget] = None) -> QWidget:
    widget = QWidget(parent)
    layout = QFormLayout(widget)
    
    # 添加控件
    spinbox = QSpinBox()
    spinbox.setRange(1, 100)
    layout.addRow("参数:", spinbox)
    
    return widget
```

## 📁 目录结构

```
plugins/
├── __init__.py                 # 插件包初始化
├── plugin_interface.py         # 插件接口定义
├── plugin_market.py           # 插件市场系统
├── README.md                  # 本文档
├── development/               # 开发工具
│   └── plugin_sdk.py         # 插件开发工具包
├── examples/                  # 示例插件
│   ├── macd_indicator.py     # MACD指标插件
│   ├── rsi_indicator.py      # RSI指标插件
│   └── moving_average_strategy.py  # 双均线策略插件
├── installed/                 # 已安装的插件
├── cache/                     # 缓存目录
└── .sdk/                     # SDK工作空间
```

## 🔧 插件管理

### 通过代码管理插件

```python
from core.plugin_manager import PluginManager

# 获取插件管理器
plugin_manager = PluginManager()

# 加载插件
plugin_manager.load_plugin("my_plugin", "/path/to/plugin.py")

# 获取插件实例
plugin = plugin_manager.get_plugin("my_plugin")

# 调用插件方法
result = plugin_manager.call_plugin_method("my_plugin", "calculate", data)

# 广播事件
plugin_manager.broadcast_event("data_updated", symbol="AAPL", data=df)

# 卸载插件
plugin_manager.unload_plugin("my_plugin")
```

### 通过插件市场管理

```python
from plugins.plugin_market import PluginMarket

# 创建插件市场
market = PluginMarket("plugins", "plugins/cache")

# 搜索插件
plugins, total = market.search_plugins(query="MACD", category="indicator")

# 下载插件
downloader = market.download_plugin(plugin_info)
downloader.start()

# 安装插件
market.install_plugin("/path/to/plugin.zip")

# 获取已安装插件
installed = market.get_installed_plugins()
```

## 📋 最佳实践

### 1. 代码规范

- 遵循PEP 8 Python代码风格
- 使用类型提示(Type Hints)
- 编写详细的文档字符串
- 实现适当的错误处理

### 2. 性能优化

- 避免在计算函数中进行重复计算
- 使用NumPy和Pandas进行向量化操作
- 合理使用缓存机制
- 避免内存泄漏

### 3. 测试

- 编写单元测试
- 测试边界条件
- 验证参数有效性
- 测试错误处理

### 4. 文档

- 提供清晰的使用说明
- 包含参数说明和示例
- 更新版本变更日志
- 提供技术支持信息

## 🔍 调试和故障排除

### 日志记录

```python
def initialize(self, context: PluginContext) -> bool:
    try:
        # 初始化逻辑
        context.log_manager.info("插件初始化成功")
        return True
    except Exception as e:
        context.log_manager.error(f"插件初始化失败: {e}")
        return False
```

### 错误处理

```python
def calculate(self, data: pd.DataFrame, **params) -> Dict[str, pd.Series]:
    try:
        # 参数验证
        if len(data) < 10:
            raise ValueError("数据长度不足")
        
        # 计算逻辑
        result = self._do_calculation(data, **params)
        return result
        
    except Exception as e:
        if self._context:
            self._context.log_manager.error(f"计算失败: {e}")
        raise
```

### 常见问题

1. **插件加载失败**
   - 检查插件文件路径
   - 验证插件元数据
   - 检查依赖是否安装

2. **计算错误**
   - 验证输入数据格式
   - 检查参数有效性
   - 查看错误日志

3. **UI组件显示异常**
   - 检查PyQt5版本兼容性
   - 验证组件创建逻辑
   - 查看UI错误信息

## 📚 API参考

详细的API文档请参考：

- [插件接口定义](plugin_interface.py)
- [插件管理器](../core/plugin_manager.py)
- [插件市场](plugin_market.py)
- [开发工具包](development/plugin_sdk.py)

## 🤝 贡献指南

欢迎为HIkyuu-UI插件生态系统做出贡献：

1. Fork项目仓库
2. 创建功能分支
3. 开发和测试插件
4. 提交Pull Request
5. 代码审查和合并

## 📄 许可证

本插件系统遵循MIT许可证。详细信息请查看LICENSE文件。

## 📞 技术支持

- 官方网站: https://hikyuu.org
- 技术论坛: https://forum.hikyuu.org
- 问题反馈: https://github.com/hikyuu/hikyuu-ui/issues
- 邮箱支持: support@hikyuu.org 