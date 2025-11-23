# VisPy + OpenGL 实施计划补充分析报告

## 📋 执行摘要

本报告基于对代码库的深入分析，对《VisPy + OpenGL 实施计划 - 深度分析报告》进行全面审查，识别遗漏、缺失和逻辑异常，并提供补充建议。

**分析范围：**
- 代码架构深度分析
- 调用链完整梳理
- 业务框架集成点识别
- 功能完整性检查
- 实施计划逻辑验证

---

## 🔍 第一部分：关键发现和遗漏

### 1.1 渲染器架构遗漏

#### ❌ 遗漏1：BaseChartRenderer抽象基类定义不明确

**问题：**
- 实施计划中提到`BaseChartRenderer`作为抽象基类，但代码中实际使用的是`optimization/chart_renderer.py`中的`ChartRenderer`作为基类
- `WebGPUChartRenderer`继承自`ChartRenderer`，而非真正的抽象基类
- 缺少明确的接口定义和抽象方法

**实际代码结构：**
```python
# optimization/chart_renderer.py
class ChartRenderer(QObject):  # 这是实际基类，不是抽象类

# optimization/webgpu_chart_renderer.py  
class WebGPUChartRenderer(BaseChartRenderer):  # BaseChartRenderer = ChartRenderer
```

**建议补充：**
1. 创建真正的抽象基类`BaseChartRenderer(ABC)`
2. 定义抽象方法：`render_candlesticks()`, `render_volume()`, `render_line()`, `setup_figure()`
3. 确保所有渲染器实现统一接口

#### ❌ 遗漏2：渲染器初始化逻辑复杂

**问题：**
- `ChartWidget.__init__()`中渲染器初始化逻辑复杂，包含多层降级
- 当前逻辑：WebGPU → optimization.chart_renderer → 基础ChartRenderer
- VisPy集成时需要插入新的降级层级

**当前代码（chart_widget.py:137-159）：**
```python
# 使用统一的WebGPU渲染器（自动包含降级功能）
try:
    from optimization.webgpu_chart_renderer import get_webgpu_chart_renderer
    self.renderer = get_webgpu_chart_renderer()
except (ImportError, Exception) as e:
    # 降级到传统渲染器
    try:
        from optimization.chart_renderer import get_chart_renderer
        self.renderer = get_chart_renderer()
    except (ImportError, Exception) as fallback_error:
        # 最后降级方案
        from optimization.chart_renderer import ChartRenderer
        self.renderer = ChartRenderer(max_workers=4, enable_progressive=True)
```

**建议补充：**
1. 创建渲染器工厂类`ChartRendererFactory`
2. 实现统一的渲染器选择逻辑
3. 支持配置驱动的渲染器优先级
4. VisPy应该插入到WebGPU之后、matplotlib之前

**建议降级链：**
```
VisPy → WebGPU → Matplotlib(optimized) → Matplotlib(basic)
```

### 1.2 Mixin架构集成遗漏

#### ❌ 遗漏3：UIMixin与VisPy画布集成冲突

**问题：**
- `UIMixin._init_figure_layout()`直接创建matplotlib画布
- VisPy需要完全不同的画布初始化方式
- 实施计划中提到的修改点不够详细

**当前代码（ui_mixin.py:47-76）：**
```python
def _init_figure_layout(self):
    """初始化图表布局"""
    self.figure = Figure(figsize=(15, 8), dpi=100, constrained_layout=False)
    self.canvas = FigureCanvas(self.figure)
    # ... matplotlib特定代码
```

**建议补充：**
1. 创建`UIMixin`的抽象方法`_create_canvas()`
2. 实现`MatplotlibUIMixin`和`VisPyUIMixin`两个版本
3. 或者使用策略模式，在`ChartWidget`初始化时选择正确的Mixin

#### ❌ 遗漏4：CrosshairMixin与VisPy交互不兼容

**问题：**
- `CrosshairMixin`依赖matplotlib的事件系统（`canvas.mpl_connect`）
- VisPy使用不同的事件系统（`vispy.app`事件）
- 十字光标实现需要完全重写

**当前代码（crosshair_mixin.py:42-80）：**
```python
def enable_crosshair(self, force_rebind=False):
    # 使用matplotlib事件
    self._create_unified_crosshair_handler()
    # matplotlib特定的十字光标实现
```

**建议补充：**
1. 创建`BaseCrosshairMixin`抽象类
2. 实现`MatplotlibCrosshairMixin`和`VisPyCrosshairMixin`
3. 或者使用适配器模式，统一十字光标接口

#### ❌ 遗漏5：ZoomMixin与VisPy交互不兼容

**问题：**
- `ZoomMixin`使用matplotlib的缩放和平移机制
- VisPy内置`panzoom`相机，但交互方式不同
- 需要适配或重写缩放逻辑

**当前代码（zoom_mixin.py:13-25）：**
```python
def _init_zoom_interaction(self):
    """自定义鼠标缩放交互"""
    self.canvas.mpl_connect('button_press_event', self._on_zoom_press)
    self.canvas.mpl_connect('motion_notify_event', self._on_zoom_motion)
    # matplotlib特定事件
```

**VisPy方式：**
```python
# VisPy内置支持
view.camera = 'panzoom'  # 但需要自定义交互逻辑
```

**建议补充：**
1. 创建统一的缩放接口
2. 实现VisPy特定的缩放适配器
3. 保持API兼容性

### 1.3 事件系统集成遗漏

#### ❌ 遗漏6：VisPy渲染完成事件缺失

**问题：**
- 实施计划提到`VisPyRenderCompleteEvent`，但未定义事件结构
- 缺少性能监控事件的详细设计
- 事件总线集成点不明确

**当前事件系统：**
- `UIDataReadyEvent`: UI数据就绪
- `ChartUpdateEvent`: 图表更新请求
- 缺少渲染器特定事件

**建议补充：**
```python
@dataclass
class VisPyRenderCompleteEvent(BaseEvent):
    """VisPy渲染完成事件"""
    chart_id: str
    render_time: float  # 渲染耗时（ms）
    data_points: int  # 渲染的数据点数
    fps: float  # 帧率
    gpu_used: bool  # 是否使用GPU
    
@dataclass
class VisPyBackendSwitchEvent(BaseEvent):
    """VisPy后端切换事件"""
    chart_id: str
    from_backend: str  # 原后端
    to_backend: str  # 新后端
    reason: str  # 切换原因
```

### 1.4 数据流和性能优化遗漏

#### ❌ 遗漏7：数据降采样策略不兼容

**问题：**
- 当前降采样基于matplotlib的视图范围
- VisPy需要不同的降采样策略（基于视口变换）
- 实施计划未详细说明VisPy的数据处理流程

**当前代码（chart_renderer.py:1118-1163）：**
```python
def _get_view_data(self, data: pd.DataFrame) -> pd.DataFrame:
    """获取视图范围内的数据"""
    # 基于matplotlib的xlim/ylim
    
def _downsample_data(self, data: pd.DataFrame) -> pd.DataFrame:
    """根据阈值对数据进行降采样"""
    # 固定阈值5000
```

**VisPy需要：**
- 基于视口变换的动态降采样
- GPU友好的数据格式转换
- 顶点缓冲对象（VBO）管理

**建议补充：**
1. 创建`VisPyDataProcessor`类
2. 实现VisPy特定的降采样算法
3. 支持LOD（Level of Detail）系统

#### ❌ 遗漏8：渐进式加载与VisPy集成

**问题：**
- `ProgressiveLoadingManager`设计用于matplotlib的渐进渲染
- VisPy的渲染机制不同，需要适配
- 实施计划未涉及渐进式加载的VisPy适配

**当前代码（progressive_loading_manager.py:362-400）：**
```python
def load_chart_progressive(self, chart_widget, kdata, indicators):
    """渐进式加载图表"""
    # 分阶段加载：basic_kdata → volume → indicators
    # 每个阶段调用chart_widget.update_chart()
```

**VisPy需要：**
- 分阶段Visual创建
- 异步数据上传到GPU
- 渲染优先级管理

**建议补充：**
1. 创建`VisPyProgressiveLoader`
2. 实现VisPy特定的渐进加载策略
3. 支持Visual的延迟创建和更新

### 1.5 主题系统集成遗漏

#### ❌ 遗漏9：主题系统与VisPy样式不兼容

**问题：**
- `ThemeManager`返回的颜色格式可能不兼容VisPy
- VisPy需要特定的颜色格式（RGBA数组）
- 实施计划未详细说明主题适配

**当前代码（base_mixin.py:82-114）：**
```python
def _apply_initial_theme(self):
    """应用初始主题"""
    colors = self.theme_manager.get_theme_colors(theme)
    # matplotlib颜色格式：'#181c24'
    self.figure.patch.set_facecolor(colors.get('chart_background', '#181c24'))
```

**VisPy需要：**
```python
# VisPy颜色格式：(R, G, B, A) 或 [R, G, B, A]
color = (0.094, 0.110, 0.141, 1.0)  # #181c24转换为RGBA
```

**建议补充：**
1. 创建`VisPyThemeAdapter`
2. 实现颜色格式转换
3. 支持VisPy特定的样式属性

### 1.6 指标渲染遗漏

#### ❌ 遗漏10：指标渲染Visual设计不完整

**问题：**
- 实施计划提到`VisPyIndicatorVisual`，但设计不详细
- 不同指标类型需要不同的Visual实现
- 指标数据格式转换未说明

**当前指标渲染（indicator_mixin.py:381-433）：**
```python
def _update_chart_with_results(self, results: dict):
    """使用计算结果更新图表"""
    # 使用renderer.render_line()渲染指标
    for name, data in results.items():
        self.renderer.render_line(indicator_ax, series, style)
```

**VisPy需要：**
- 不同类型的指标需要不同的Visual
- 线图：`LineVisual`
- 柱状图：`BarVisual`或`PolygonVisual`
- 面积图：`PolygonVisual`填充

**建议补充：**
1. 创建指标Visual工厂
2. 实现各类型指标的VisPy适配
3. 支持指标组合渲染

---

## 🔧 第二部分：调用链补充分析

### 2.1 完整调用链（补充）

#### 数据加载到渲染的完整流程（详细版）

```
用户选择股票
  ↓
LeftPanel._select_asset()
  ↓
EventBus.emit(StockSelectedEvent)
  ↓
MainWindowCoordinator._on_stock_selected() [异步]
  ↓
UnifiedChartService.load_chart_data()
  ↓
ChartDataLoader (QThread)
  ↓
EventBus.emit(UIDataReadyEvent)
  ↓
MiddlePanel._on_ui_data_ready()
  ↓
ChartCanvas.update_chart()
  ↓
ChartWidget.update_chart() [RenderingMixin]
  ↓
ChartRenderer.render_candlesticks() [625ms瓶颈]
  ↓
ChartRenderer._render_candlesticks_efficient()
  ↓
matplotlib PolyCollection/LineCollection
  ↓
canvas.draw_idle() [触发绘制]
  ↓
FigureCanvasQTAgg.draw() [Qt事件循环]
  ↓
屏幕渲染
```

#### VisPy调用链（新增）

```
用户选择股票
  ↓
[相同的数据加载流程]
  ↓
ChartWidget.update_chart() [RenderingMixin]
  ↓
VisPyChartRenderer.render_candlesticks()
  ↓
VisPyKLineVisual.update_data()
  ↓
准备顶点数据（numpy数组）
  ↓
上传到GPU（VBO）
  ↓
VisPy SceneCanvas渲染
  ↓
OpenGL绘制调用
  ↓
屏幕渲染（GPU加速）
```

### 2.2 关键集成点补充

#### 集成点1：ServiceContainer注册（补充）

**当前实现缺失：**
- 实施计划提到注册，但未说明注册时机
- 未说明渲染器选择器的实现细节

**建议补充：**
```python
# core/services/service_bootstrap.py
def _register_chart_services(self):
    """注册图表相关服务"""
    
    # 1. 注册渲染器工厂（按优先级）
    self.service_container.register_factory(
        'VisPyChartRenderer',
        lambda: VisPyChartRenderer(),
        scope=ServiceScope.SINGLETON,
        priority=1  # 最高优先级
    )
    
    self.service_container.register_factory(
        'WebGPUChartRenderer',
        lambda: WebGPUChartRenderer(),
        scope=ServiceScope.SINGLETON,
        priority=2
    )
    
    # 2. 注册渲染器选择器
    self.service_container.register_factory(
        ChartRendererSelector,
        lambda: ChartRendererSelector(
            service_container=self.service_container
        ),
        scope=ServiceScope.SINGLETON
    )
    
    # 3. 注册渲染器工厂（统一入口）
    self.service_container.register_factory(
        ChartRendererFactory,
        lambda: ChartRendererFactory(
            selector=self.service_container.resolve(ChartRendererSelector)
        ),
        scope=ServiceScope.SINGLETON
    )
```

#### 集成点2：ChartWidget初始化（补充）

**当前实现问题：**
- 渲染器初始化逻辑硬编码在`ChartWidget.__init__()`
- 应该使用ServiceContainer解析

**建议修改：**
```python
# gui/widgets/chart_widget.py
def __init__(self, ...):
    # ... 现有初始化代码 ...
    
    # 使用ServiceContainer获取渲染器工厂
    if coordinator and hasattr(coordinator, 'service_container'):
        renderer_factory = coordinator.service_container.resolve(ChartRendererFactory)
        self.renderer = renderer_factory.create_renderer(
            preferred_backend='vispy',  # 优先VisPy
            fallback_chain=['webgpu', 'matplotlib']
        )
    else:
        # 降级到直接初始化（向后兼容）
        self._init_renderer_fallback()
```

---

## ⚠️ 第三部分：逻辑异常和风险

### 3.1 架构设计异常

#### ⚠️ 异常1：Mixin模式与VisPy不兼容

**问题：**
- ChartWidget使用10个Mixin，每个都假设matplotlib存在
- VisPy需要完全不同的实现，Mixin模式可能导致代码重复

**风险：**
- 需要创建10个VisPy版本的Mixin
- 或者需要大量条件判断（if self.use_vispy）
- 代码维护成本高

**建议：**
1. 考虑使用策略模式替代部分Mixin
2. 或者创建VisPy版本的ChartWidget（VisPyChartWidget）
3. 使用适配器模式统一接口

#### ⚠️ 异常2：渲染器接口不一致

**问题：**
- 当前渲染器方法签名包含`ax`参数（matplotlib Axes）
- VisPy渲染器不需要`ax`，需要`view`（VisPy ViewBox）
- API不兼容

**当前接口：**
```python
def render_candlesticks(self, ax, data, style, x=None, use_datetime_axis=True):
    # ax是matplotlib Axes对象
```

**VisPy接口：**
```python
def render_candlesticks(self, view, data, style, x=None):
    # view是VisPy ViewBox对象
```

**建议：**
1. 创建渲染上下文对象（RenderContext）
2. 上下文包含ax/view的抽象
3. 或者使用适配器包装

### 3.2 性能优化风险

#### ⚠️ 风险1：数据转换开销

**问题：**
- DataFrame到numpy数组转换
- numpy数组到GPU缓冲区转换
- 可能抵消GPU加速收益

**建议：**
1. 实现数据缓存机制
2. 使用零拷贝技术（如果可能）
3. 批量数据转换

#### ⚠️ 风险2：内存管理

**问题：**
- VisPy使用GPU显存
- 大数据集可能导致显存不足
- 需要实现显存管理策略

**建议：**
1. 实现显存监控
2. 自动降级到CPU渲染
3. 数据分块加载

### 3.3 兼容性风险

#### ⚠️ 风险3：OpenGL版本兼容性

**问题：**
- 不同平台的OpenGL版本不同
- 某些平台可能不支持所需特性
- 需要详细的兼容性测试

**建议：**
1. 实现OpenGL版本检测
2. 提供功能降级方案
3. 详细的错误提示

---

## 📊 第四部分：实施计划补充建议

### 4.1 阶段0：架构准备（新增）

**目标：** 在开始VisPy实现前，先完善架构基础

#### 任务0.1：创建抽象基类
- [ ] 创建`BaseChartRenderer(ABC)`抽象基类
- [ ] 定义统一的渲染接口
- [ ] 重构现有渲染器继承抽象基类

#### 任务0.2：创建渲染器工厂
- [ ] 实现`ChartRendererFactory`
- [ ] 实现`ChartRendererSelector`
- [ ] 集成到ServiceContainer

#### 任务0.3：创建渲染上下文
- [ ] 设计`RenderContext`抽象
- [ ] 实现`MatplotlibRenderContext`
- [ ] 为VisPy预留`VisPyRenderContext`接口

### 4.2 阶段1补充：技术验证

#### 任务1.4补充：VisPy与现有系统集成测试
- [ ] 测试VisPy与ServiceContainer集成
- [ ] 测试VisPy与EventBus集成
- [ ] 测试VisPy与ThemeManager集成
- [ ] 测试VisPy与ProgressiveLoadingManager集成

#### 任务1.5补充：性能基准测试详细设计
- [ ] 定义性能测试场景
- [ ] 设计性能指标收集机制
- [ ] 实现自动化性能测试脚本

### 4.3 阶段2补充：核心功能开发

#### 任务2.9：渲染器适配器实现（新增）
- [ ] 实现`MatplotlibToVisPyAdapter`
- [ ] 实现统一的渲染接口包装
- [ ] 确保API兼容性

#### 任务2.10：数据处理器实现（新增）
- [ ] 实现`VisPyDataProcessor`
- [ ] 实现DataFrame到VisPy数据格式转换
- [ ] 实现VBO管理

#### 任务2.11：主题适配器实现（新增）
- [ ] 实现`VisPyThemeAdapter`
- [ ] 实现颜色格式转换
- [ ] 支持VisPy特定样式属性

### 4.4 阶段3补充：系统集成

#### 任务3.7：Mixin适配（新增）
- [ ] 创建VisPy版本的UIMixin
- [ ] 创建VisPy版本的CrosshairMixin
- [ ] 创建VisPy版本的ZoomMixin
- [ ] 或者使用适配器模式统一接口

#### 任务3.8：渐进式加载适配（新增）
- [ ] 实现`VisPyProgressiveLoader`
- [ ] 适配ProgressiveLoadingManager
- [ ] 支持VisPy的渐进渲染

#### 任务3.9：配置系统集成（补充）
- [ ] 添加VisPy相关配置项
- [ ] 实现渲染器选择配置
- [ ] 实现性能参数配置

### 4.5 阶段4补充：优化和测试

#### 任务4.8：内存和显存优化（新增）
- [ ] 实现显存监控
- [ ] 实现自动降级机制
- [ ] 优化数据缓存策略

#### 任务4.9：兼容性测试详细设计（补充）
- [ ] Windows平台测试矩阵
- [ ] Linux平台测试矩阵
- [ ] macOS平台测试矩阵
- [ ] 不同GPU厂商测试

---

## 🎯 第五部分：关键文件修改清单（补充）

### 5.1 必须修改的文件

| 文件路径 | 修改类型 | 优先级 | 说明 |
|---------|---------|--------|------|
| `gui/widgets/chart_widget.py` | 重构 | 高 | 渲染器初始化逻辑 |
| `gui/widgets/chart_mixins/ui_mixin.py` | 重构 | 高 | 画布创建逻辑 |
| `gui/widgets/chart_mixins/crosshair_mixin.py` | 适配 | 高 | 十字光标事件系统 |
| `gui/widgets/chart_mixins/zoom_mixin.py` | 适配 | 高 | 缩放交互逻辑 |
| `gui/widgets/chart_mixins/rendering_mixin.py` | 修改 | 高 | 渲染调用逻辑 |
| `core/services/service_bootstrap.py` | 新增 | 中 | 渲染器注册 |
| `core/services/unified_chart_service.py` | 修改 | 中 | 渲染器工厂集成 |
| `utils/theme.py` | 扩展 | 中 | VisPy颜色适配 |

### 5.2 新增文件清单（补充）

| 文件路径 | 说明 | 优先级 |
|---------|------|--------|
| `optimization/base_chart_renderer.py` | 抽象基类 | 高 |
| `optimization/vispy_chart_renderer.py` | VisPy渲染器 | 高 |
| `optimization/vispy_visuals.py` | VisPy Visual类 | 高 |
| `optimization/vispy_data_processor.py` | 数据处理器 | 高 |
| `optimization/vispy_theme_adapter.py` | 主题适配器 | 中 |
| `optimization/chart_renderer_factory.py` | 渲染器工厂 | 高 |
| `optimization/chart_renderer_selector.py` | 渲染器选择器 | 高 |
| `optimization/render_context.py` | 渲染上下文 | 中 |
| `optimization/vispy_progressive_loader.py` | 渐进式加载器 | 中 |
| `tests/test_vispy_renderer.py` | 单元测试 | 高 |
| `tests/test_vispy_integration.py` | 集成测试 | 高 |

---

## 📝 第六部分：API设计建议

### 6.1 统一渲染接口

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

class RenderContext(ABC):
    """渲染上下文抽象"""
    pass

class BaseChartRenderer(ABC):
    """图表渲染器抽象基类"""
    
    @abstractmethod
    def render_candlesticks(self, context: RenderContext, 
                           data: pd.DataFrame, 
                           style: Dict[str, Any] = None,
                           x: Optional[np.ndarray] = None) -> None:
        """渲染K线图"""
        pass
    
    @abstractmethod
    def render_volume(self, context: RenderContext,
                     data: pd.DataFrame,
                     style: Dict[str, Any] = None,
                     x: Optional[np.ndarray] = None) -> None:
        """渲染成交量"""
        pass
    
    @abstractmethod
    def render_line(self, context: RenderContext,
                   data: pd.Series,
                   style: Dict[str, Any] = None) -> None:
        """渲染线图"""
        pass
    
    @abstractmethod
    def setup_figure(self, context: RenderContext) -> None:
        """设置图表布局"""
        pass
```

### 6.2 渲染器工厂接口

```python
class ChartRendererFactory:
    """图表渲染器工厂"""
    
    def create_renderer(self, 
                       preferred_backend: str = 'auto',
                       fallback_chain: List[str] = None) -> BaseChartRenderer:
        """
        创建渲染器
        
        Args:
            preferred_backend: 首选后端 ('vispy', 'webgpu', 'matplotlib', 'auto')
            fallback_chain: 降级链，如 ['vispy', 'webgpu', 'matplotlib']
        
        Returns:
            BaseChartRenderer实例
        """
        pass
```

---

## 🔗 第七部分：依赖关系图

### 7.1 渲染器依赖关系

```
BaseChartRenderer (抽象基类)
  ├── MatplotlibChartRenderer
  │     └── ChartRenderer (optimization/chart_renderer.py)
  ├── WebGPUChartRenderer
  │     └── ChartRenderer (继承)
  └── VisPyChartRenderer (新增)
        ├── VisPyKLineVisual
        ├── VisPyVolumeVisual
        └── VisPyIndicatorVisual
```

### 7.2 服务依赖关系

```
ServiceContainer
  └── ChartRendererFactory
        └── ChartRendererSelector
              ├── VisPyChartRenderer
              ├── WebGPUChartRenderer
              └── MatplotlibChartRenderer
```

### 7.3 Mixin依赖关系（VisPy版本）

```
ChartWidget
  ├── BaseMixin (通用)
  ├── UIMixin → VisPyUIMixin (需要适配)
  ├── RenderingMixin → VisPyRenderingMixin (需要适配)
  ├── CrosshairMixin → VisPyCrosshairMixin (需要适配)
  ├── ZoomMixin → VisPyZoomMixin (需要适配)
  └── [其他Mixin保持通用]
```

---

## ✅ 第八部分：检查清单

### 8.1 架构完整性检查

- [ ] 抽象基类定义完整
- [ ] 渲染器接口统一
- [ ] 工厂模式实现
- [ ] 服务容器集成
- [ ] 事件系统集成
- [ ] 主题系统适配
- [ ] 配置系统支持

### 8.2 功能完整性检查

- [ ] K线图渲染
- [ ] 成交量渲染
- [ ] 指标渲染（所有类型）
- [ ] 十字光标
- [ ] 缩放和平移
- [ ] 主题切换
- [ ] 数据导出
- [ ] 渐进式加载

### 8.3 兼容性检查

- [ ] Windows平台
- [ ] Linux平台
- [ ] macOS平台
- [ ] 不同GPU厂商
- [ ] 不同OpenGL版本
- [ ] 降级机制
- [ ] 错误处理

### 8.4 性能检查

- [ ] 渲染时间 < 100ms
- [ ] FPS > 10
- [ ] CPU占用降低
- [ ] 内存占用优化
- [ ] 显存管理
- [ ] 大数据集支持

---

## 📚 第九部分：参考资料补充

### 9.1 VisPy特定资源

- **VisPy与Qt集成：** https://vispy.org/gallery.html#qt-integration
- **VisPy性能优化：** https://vispy.org/performance.html
- **VisPy自定义Visual：** https://vispy.org/visuals.html
- **VisPy事件系统：** https://vispy.org/app.html#event-system

### 9.2 OpenGL资源补充

- **OpenGL与Qt：** https://doc.qt.io/qt-5/qopenglwidget.html
- **OpenGL ES 2.0规范：** https://www.khro