# WebGPU与Matplotlib集成技术方案

## 当前架构分析

### 系统现状

当前HIkyuu-UI系统的渲染架构：

```
ChartWidget (QWidget)
    ↓
matplotlib.figure.Figure (figsize=(15, 8))
    ↓ 
FigureCanvasQTAgg (Qt集成的matplotlib画布)
    ↓
三个子图轴 (GridSpec 3x1, 比例3:1:1)
    ├── price_ax (价格/K线图)
    ├── volume_ax (成交量)
    └── indicator_ax (技术指标)
```

### 关键发现

1. **UI层面**: `ChartWidget`继承自`QWidget`，使用`FigureCanvasQTAgg`作为matplotlib与Qt的桥梁
2. **图表结构**: 使用`matplotlib.gridspec.GridSpec`创建三个子图，固定比例分配
3. **渲染流程**: 通过`ChartRenderer.render_candlesticks(ax, data, style, x)`在matplotlib轴上绘制
4. **交互系统**: 十字光标、缩放、拖拽都基于matplotlib事件系统
5. **主题系统**: 通过matplotlib的样式API设置颜色和字体

## 方案一：WebGPU与Matplotlib轴集成 🎯 **推荐方案**

### 核心思路

让WebGPU渲染器能够在现有的matplotlib轴(`ax`)上绘制内容，保持完全的架构兼容性。

### 技术实现策略

#### 1.1 数据流转换层

```python
class WebGPUMatplotlibBridge:
    """WebGPU与Matplotlib的桥接器"""
    
    def __init__(self, ax):
        self.ax = ax
        self.webgpu_context = None
        self.texture_cache = {}
        
    def render_candlesticks_to_matplotlib(self, data: pd.DataFrame, style: Dict[str, Any], x: np.ndarray):
        """将WebGPU渲染结果转换为matplotlib绘图指令"""
        
        # 第一步：WebGPU渲染到纹理
        webgpu_texture = self._render_to_webgpu_texture(data, style, x)
        
        # 第二步：将WebGPU纹理转换为numpy数组
        image_array = self._texture_to_numpy(webgpu_texture)
        
        # 第三步：在matplotlib轴上显示图像
        extent = self._calculate_extent(x, data)
        self.ax.imshow(image_array, extent=extent, aspect='auto', alpha=0.9)
        
        # 第四步：添加matplotlib装饰（坐标轴、网格等）
        self._add_matplotlib_decorations(data, x)
```

#### 1.2 WebGPU渲染管道

```python
class WebGPUCandlestickRenderer:
    """WebGPU K线渲染器"""
    
    def __init__(self):
        self.device = None
        self.render_pipeline = None
        self.vertex_buffer = None
        self.uniform_buffer = None
        
    def initialize_webgpu(self):
        """初始化WebGPU设备和渲染管道"""
        # 1. 获取WebGPU适配器和设备
        self.device = self._get_webgpu_device()
        
        # 2. 创建渲染管道
        self.render_pipeline = self._create_candlestick_pipeline()
        
        # 3. 创建缓冲区
        self.vertex_buffer = self._create_vertex_buffer()
        self.uniform_buffer = self._create_uniform_buffer()
        
    def render_candlesticks(self, data: pd.DataFrame, style: Dict, viewport: tuple) -> np.ndarray:
        """渲染K线到纹理，返回图像数据"""
        
        # 1. 准备顶点数据
        vertices = self._prepare_candlestick_vertices(data)
        
        # 2. 更新缓冲区
        self._update_vertex_buffer(vertices)
        self._update_uniform_buffer(style, viewport)
        
        # 3. 创建渲染目标
        render_texture = self._create_render_texture(viewport)
        
        # 4. 执行渲染
        command_encoder = self.device.create_command_encoder()
        render_pass = self._begin_render_pass(command_encoder, render_texture)
        
        render_pass.set_pipeline(self.render_pipeline)
        render_pass.set_vertex_buffer(0, self.vertex_buffer)
        render_pass.set_bind_group(0, self.uniform_bind_group)
        render_pass.draw(len(vertices), 1, 0, 0)
        render_pass.end()
        
        command_buffer = command_encoder.finish()
        self.device.queue.submit([command_buffer])
        
        # 5. 读取渲染结果
        image_data = self._read_texture_data(render_texture)
        return image_data
```

#### 1.3 着色器程序

```wgsl
// vertex.wgsl - 顶点着色器
struct VertexInput {
    @location(0) position: vec2<f32>,
    @location(1) ohlc: vec4<f32>,  // open, high, low, close
    @location(2) color: vec3<f32>,
}

struct VertexOutput {
    @builtin(position) clip_position: vec4<f32>,
    @location(0) color: vec3<f32>,
    @location(1) ohlc: vec4<f32>,
}

struct Uniforms {
    transform: mat4x4<f32>,
    viewport_size: vec2<f32>,
    candlestick_width: f32,
    time_padding: f32,
}

@group(0) @binding(0)
var<uniform> uniforms: Uniforms;

@vertex
fn vs_main(input: VertexInput) -> VertexOutput {
    var output: VertexOutput;
    
    // 计算K线的几何形状
    let x = input.position.x;
    let open = input.ohlc.x;
    let high = input.ohlc.y;
    let low = input.ohlc.z;
    let close = input.ohlc.w;
    
    // 变换到clip空间
    let world_pos = vec4<f32>(x, input.position.y, 0.0, 1.0);
    output.clip_position = uniforms.transform * world_pos;
    
    output.color = input.color;
    output.ohlc = input.ohlc;
    
    return output;
}

// fragment.wgsl - 片段着色器
@fragment
fn fs_main(input: VertexOutput) -> @location(0) vec4<f32> {
    // 根据OHLC数据绘制K线
    let open = input.ohlc.x;
    let close = input.ohlc.w;
    
    // 根据涨跌设置颜色
    var color = input.color;
    if (close < open) {
        color = vec3<f32>(0.0, 1.0, 0.0);  // 绿色(下跌)
    } else {
        color = vec3<f32>(1.0, 0.0, 0.0);  // 红色(上涨)
    }
    
    return vec4<f32>(color, 1.0);
}
```

#### 1.4 集成到现有渲染器

```python
class EnhancedWebGPUChartRenderer(BaseChartRenderer):
    """增强的WebGPU图表渲染器"""
    
    def __init__(self, max_workers: int = 8, enable_progressive: bool = True):
        super().__init__(max_workers, enable_progressive)
        self.webgpu_renderer = WebGPUCandlestickRenderer()
        self.bridges = {}  # 缓存轴对应的桥接器
        
    def render_candlesticks(self, ax, data: pd.DataFrame, style: Dict[str, Any] = None, x: np.ndarray = None):
        """在matplotlib轴上使用WebGPU渲染K线"""
        
        try:
            # 1. 获取或创建桥接器
            if ax not in self.bridges:
                self.bridges[ax] = WebGPUMatplotlibBridge(ax)
                
            bridge = self.bridges[ax]
            
            # 2. 检查WebGPU可用性
            if self._should_use_webgpu() and self.webgpu_renderer.device:
                # 3. 使用WebGPU渲染
                success = bridge.render_candlesticks_to_matplotlib(data, style or {}, x)
                
                if success:
                    logger.debug(f"WebGPU K线渲染成功: {len(data)}个数据点")
                    return
                    
            # 4. 降级到matplotlib实现
            logger.debug("降级到matplotlib K线渲染")
            super().render_candlesticks(ax, data, style, x)
            
        except Exception as e:
            logger.error(f"WebGPU K线渲染失败: {e}")
            # 确保出错时仍有显示
            super().render_candlesticks(ax, data, style, x)
```

### 优势

1. **完全兼容**: 保持现有的matplotlib架构不变
2. **渐进优化**: 可以逐步替换各个图表类型
3. **自动降级**: WebGPU失败时自动使用matplotlib
4. **性能提升**: WebGPU渲染大量数据点时性能更好
5. **视觉一致**: 最终都在matplotlib轴上显示

### 挑战

1. **纹理转换开销**: WebGPU→Texture→numpy→matplotlib 有一定性能开销
2. **坐标系统同步**: 需要精确映射WebGPU和matplotlib坐标系
3. **样式同步**: WebGPU渲染的样式需要与matplotlib主题匹配
4. **交互处理**: 鼠标事件仍需要matplotlib处理

## 方案二：独立WebGPU Canvas 🚀 **高性能方案**

### 核心思路

创建独立的WebGPU渲染画布，与matplotlib并行或替代matplotlib。

### 技术实现策略

#### 2.1 双画布架构

```python
class HybridChartWidget(QWidget):
    """混合图表控件 - 支持matplotlib和WebGPU双模式"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI布局
        self.layout = QVBoxLayout(self)
        
        # 渲染模式选择
        self.render_mode = "webgpu"  # "webgpu" | "matplotlib" | "hybrid"
        
        # WebGPU Canvas (QOpenGLWidget)
        self.webgpu_canvas = WebGPUChartCanvas(self)
        
        # Matplotlib Canvas
        self.matplotlib_canvas = MatplotlibChartCanvas(self)
        
        # 控制面板
        self.control_panel = ChartControlPanel(self)
        
        self._setup_layout()
        
    def _setup_layout(self):
        """设置布局"""
        # 画布容器
        self.canvas_stack = QStackedWidget()
        self.canvas_stack.addWidget(self.webgpu_canvas)
        self.canvas_stack.addWidget(self.matplotlib_canvas)
        
        self.layout.addWidget(self.control_panel)
        self.layout.addWidget(self.canvas_stack)
        
    def switch_render_mode(self, mode: str):
        """切换渲染模式"""
        if mode == "webgpu":
            self.canvas_stack.setCurrentWidget(self.webgpu_canvas)
        elif mode == "matplotlib":
            self.canvas_stack.setCurrentWidget(self.matplotlib_canvas)
        
        self.render_mode = mode
        self._sync_data_between_canvases()
```

#### 2.2 WebGPU Canvas实现

```python
class WebGPUChartCanvas(QOpenGLWidget):
    """基于WebGPU的图表画布"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.webgpu_device = None
        self.render_context = None
        self.chart_layers = {}
        
        # 图表数据
        self.current_data = None
        self.viewport = ViewportState()
        
        # 交互系统
        self.interaction_manager = WebGPUInteractionManager(self)
        
    def initializeGL(self):
        """初始化WebGPU渲染上下文"""
        try:
            # 1. 初始化WebGPU设备
            self.webgpu_device = self._initialize_webgpu_device()
            
            # 2. 创建渲染上下文
            self.render_context = WebGPUChartRenderContext(
                device=self.webgpu_device,
                surface=self._get_surface(),
                width=self.width(),
                height=self.height()
            )
            
            # 3. 创建图表层
            self.chart_layers = {
                'background': BackgroundLayer(self.render_context),
                'grid': GridLayer(self.render_context),
                'candlesticks': CandlestickLayer(self.render_context),
                'volume': VolumeLayer(self.render_context),
                'indicators': IndicatorLayer(self.render_context),
                'crosshair': CrosshairLayer(self.render_context),
                'ui': UILayer(self.render_context)
            }
            
            logger.info("WebGPU图表画布初始化成功")
            
        except Exception as e:
            logger.error(f"WebGPU初始化失败: {e}")
            self._fallback_to_opengl()
            
    def paintGL(self):
        """WebGPU渲染帧"""
        if not self.render_context:
            return
            
        try:
            # 1. 开始帧渲染
            frame = self.render_context.begin_frame()
            
            # 2. 清除背景
            frame.clear(color=[0.1, 0.12, 0.15, 1.0])
            
            # 3. 渲染各个层（按Z顺序）
            render_order = ['background', 'grid', 'candlesticks', 'volume', 'indicators', 'crosshair', 'ui']
            
            for layer_name in render_order:
                layer = self.chart_layers.get(layer_name)
                if layer and layer.is_visible():
                    layer.render(frame, self.viewport, self.current_data)
            
            # 4. 提交渲染
            frame.present()
            
        except Exception as e:
            logger.error(f"WebGPU渲染失败: {e}")
            
    def update_chart_data(self, data: Dict[str, Any]):
        """更新图表数据"""
        self.current_data = data
        
        # 更新各个层的数据
        if 'kdata' in data:
            self.chart_layers['candlesticks'].update_data(data['kdata'])
            self.chart_layers['volume'].update_data(data['kdata'])
            
        if 'indicators' in data:
            self.chart_layers['indicators'].update_data(data['indicators'])
            
        # 触发重绘
        self.update()
```

#### 2.3 图表层系统

```python
class CandlestickLayer(ChartLayer):
    """K线图层"""
    
    def __init__(self, render_context):
        super().__init__(render_context)
        self.vertex_buffer = None
        self.index_buffer = None
        self.render_pipeline = None
        self._create_render_pipeline()
        
    def _create_render_pipeline(self):
        """创建K线渲染管道"""
        self.render_pipeline = self.render_context.create_render_pipeline({
            'vertex': {
                'module': self._load_shader('candlestick.vert.wgsl'),
                'entry_point': 'vs_main'
            },
            'fragment': {
                'module': self._load_shader('candlestick.frag.wgsl'),
                'entry_point': 'fs_main'
            },
            'primitive': {
                'topology': 'triangle-list',
                'cull_mode': 'back'
            },
            'vertex_buffers': [{
                'array_stride': 32,  # vec2 pos + vec4 ohlc + vec3 color
                'attributes': [
                    {'format': 'float32x2', 'offset': 0, 'shader_location': 0},
                    {'format': 'float32x4', 'offset': 8, 'shader_location': 1},
                    {'format': 'float32x3', 'offset': 24, 'shader_location': 2}
                ]
            }]
        })
        
    def update_data(self, kdata: pd.DataFrame):
        """更新K线数据"""
        if kdata is None or kdata.empty:
            return
            
        # 1. 生成顶点数据
        vertices = self._generate_candlestick_vertices(kdata)
        
        # 2. 更新GPU缓冲区
        if self.vertex_buffer:
            self.vertex_buffer.destroy()
            
        self.vertex_buffer = self.render_context.create_buffer(
            data=vertices,
            usage='vertex'
        )
        
    def render(self, frame, viewport: ViewportState, data: Dict[str, Any]):
        """渲染K线"""
        if not self.vertex_buffer:
            return
            
        # 1. 设置渲染管道
        pass = frame.begin_render_pass(self.render_target)
        pass.set_pipeline(self.render_pipeline)
        
        # 2. 设置uniform数据
        transform_matrix = viewport.get_transform_matrix()
        uniform_data = self._create_uniform_data(transform_matrix, viewport)
        pass.set_bind_group(0, uniform_data)
        
        # 3. 设置顶点缓冲区
        pass.set_vertex_buffer(0, self.vertex_buffer)
        
        # 4. 绘制
        vertex_count = len(self.vertex_buffer) // 32  # 32 bytes per vertex
        pass.draw(vertex_count, 1, 0, 0)
        
        pass.end()
```

#### 2.4 交互系统

```python
class WebGPUInteractionManager:
    """WebGPU交互管理器"""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.viewport = canvas.viewport
        
        # 绑定事件
        canvas.mousePressEvent = self._on_mouse_press
        canvas.mouseMoveEvent = self._on_mouse_move
        canvas.mouseReleaseEvent = self._on_mouse_release
        canvas.wheelEvent = self._on_wheel
        
    def _on_mouse_press(self, event):
        """鼠标按下事件"""
        pos = (event.x(), event.y())
        
        if event.button() == Qt.LeftButton:
            self._handle_selection(pos)
        elif event.button() == Qt.RightButton:
            self._handle_context_menu(pos)
            
    def _on_wheel(self, event):
        """滚轮缩放"""
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        
        # 计算缩放中心
        mouse_pos = (event.x(), event.y())
        world_pos = self.viewport.screen_to_world(mouse_pos)
        
        # 应用缩放
        self.viewport.zoom_at_point(world_pos, zoom_factor)
        
        # 触发重绘
        self.canvas.update()
```

### 优势

1. **极致性能**: 直接GPU渲染，无中间转换
2. **丰富交互**: 可实现复杂的GPU交互效果
3. **现代架构**: 基于最新的WebGPU标准
4. **无限扩展**: 可添加复杂的视觉效果和动画
5. **未来兼容**: 支持新的图表类型和特效

### 挑战

1. **开发复杂度高**: 需要重新实现所有图表功能
2. **兼容性风险**: WebGPU还在发展中，浏览器支持有限
3. **维护成本**: 需要同时维护两套渲染系统
4. **学习曲线**: 团队需要学习WebGPU/WGSL开发

## 方案对比与建议

### 性能对比

| 维度 | 方案一(集成) | 方案二(独立) | matplotlib |
|------|-------------|-------------|------------|
| **开发难度** | 中等 | 高 | 低 |
| **性能提升** | 30-50% | 200-500% | 基准 |
| **兼容性** | 完全兼容 | 需重构 | 完全兼容 |
| **维护成本** | 低 | 高 | 最低 |
| **风险程度** | 低 | 中等 | 无 |

### 实施建议

#### 阶段一：基础验证（1-2周）
1. **选择方案一**作为起点
2. 实现简单的WebGPU K线渲染到matplotlib
3. 验证技术可行性和性能收益

#### 阶段二：完善集成（2-3周）
1. 完善WebGPU与matplotlib的桥接
2. 实现成交量和基础指标的WebGPU渲染
3. 完善错误处理和降级机制

#### 阶段三：优化扩展（1-2周）
1. 优化渲染性能和内存使用
2. 添加更多图表类型支持
3. 完善样式和主题同步

#### 阶段四：高级特性（选择性）
1. 考虑引入方案二的独立Canvas
2. 实现高级视觉效果
3. 优化大数据量渲染

### 推荐实施路径

**短期目标**（解决当前问题）：
- 立即实施方案一的基础版本
- 修复WebGPU模拟渲染的问题
- 确保K线正常显示

**中期目标**（性能优化）：
- 完善WebGPU-matplotlib集成
- 实现主要图表类型的GPU加速
- 建立完善的测试体系

**长期目标**（架构升级）：
- 评估方案二的必要性
- 根据用户需求决定是否实施独立Canvas
- 持续优化性能和用户体验

## 技术细节补充

### 坐标系统转换

```python
class CoordinateTransform:
    """坐标系统转换器"""
    
    @staticmethod
    def matplotlib_to_webgpu(ax, data_points):
        """matplotlib坐标到WebGPU坐标转换"""
        # 获取matplotlib轴的数据范围
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        # 转换到WebGPU的NDC坐标 (-1, 1)
        webgpu_points = []
        for x, y in data_points:
            ndc_x = 2.0 * (x - xlim[0]) / (xlim[1] - xlim[0]) - 1.0
            ndc_y = 2.0 * (y - ylim[0]) / (ylim[1] - ylim[0]) - 1.0
            webgpu_points.append((ndc_x, ndc_y))
            
        return webgpu_points
```

### 样式同步机制

```python
class StyleSynchronizer:
    """样式同步器"""
    
    def __init__(self, theme_manager):
        self.theme_manager = theme_manager
        
    def get_webgpu_style(self, matplotlib_style):
        """将matplotlib样式转换为WebGPU样式"""
        theme_colors = self.theme_manager.get_theme_colors()
        
        return {
            'up_color': self._hex_to_rgb(matplotlib_style.get('up_color', theme_colors.get('up_color', '#ff0000'))),
            'down_color': self._hex_to_rgb(matplotlib_style.get('down_color', theme_colors.get('down_color', '#00ff00'))),
            'line_width': matplotlib_style.get('linewidth', 1.0),
            'alpha': matplotlib_style.get('alpha', 1.0)
        }
```

这个方案提供了一个渐进式的实施路径，既解决了当前的问题，又为未来的性能优化奠定了基础。关键是先让系统稳定运行，再逐步引入GPU加速功能。 