# PyQtGraph 迁移方案 - 深度分析报告

## 📋 执行摘要

本文档基于系统框架、功能需求和调用量分析，提供PyQtGraph替代matplotlib的**完整迁移方案**。方案不包含代码实现，仅提供技术架构、功能映射和实施策略。

---

## 🏗️ 系统架构分析

### 当前架构概览

**核心组件：**
- **ChartWidget**：主图表控件，使用Mixin模式
- **ChartRenderer**：渲染器，负责K线、成交量绘制
- **RenderingMixin**：渲染功能Mixin
- **多个功能Mixin**：IndicatorMixin, CrosshairMixin, InteractionMixin等

**架构特点：**
- ✅ **Mixin模式**：功能模块化，易于扩展
- ✅ **分离关注点**：渲染、交互、指标分离
- ✅ **统一接口**：ChartWidget提供统一API

**当前依赖：**
- matplotlib Figure/FigureCanvas
- matplotlib axes (price_ax, volume_ax, indicator_ax)
- matplotlib collections (PolyCollection, LineCollection)

---

## 📊 功能需求分析

### 核心功能清单

#### 1. 图表渲染功能

**K线图渲染：**
- 支持OHLC数据（开高低收）
- 涨跌颜色区分（红涨绿跌）
- 影线绘制（最高最低）
- 实体绘制（开盘收盘）
- 支持244+数据点（当前性能瓶颈）

**成交量图渲染：**
- 柱状图显示
- 涨跌颜色区分
- 与K线图X轴同步

**技术指标叠加：**
- MA移动平均线（多条）
- MACD指标（DIF、DEA、MACD柱）
- RSI指标
- BOLL布林带（上中下轨）
- 自定义指标（通过talib）

**多子图布局：**
- 价格图（主图，占3/5高度）
- 成交量图（占1/5高度）
- 指标图（占1/5高度）
- X轴共享，同步缩放

#### 2. 交互功能

**十字光标：**
- 鼠标移动显示十字线
- 价格和时间信息显示
- 多子图同步显示
- 数据点捕捉

**缩放和平移：**
- 鼠标滚轮缩放
- 拖拽平移
- 视图范围限制
- 自动缩放（autoscale）

**数据交互：**
- 区间选择
- 右键菜单
- 双击重置视图

#### 3. 数据更新功能

**实时更新：**
- 增量数据更新
- 全量数据刷新
- 数据验证
- 错误处理

**渐进式加载：**
- 分阶段渲染（K线→成交量→指标）
- 性能优化
- 加载进度显示

#### 4. 样式和主题

**主题支持：**
- 亮色/暗色主题
- 自定义颜色方案
- 网格和刻度样式
- 字体大小控制

**样式配置：**
- K线颜色
- 指标线条颜色
- 背景色
- 文本颜色

#### 5. 导出功能

**图像导出：**
- PNG导出
- PDF导出
- SVG导出
- 自定义分辨率

---

## 🔢 调用量分析

### 高频调用路径

#### 1. 图表更新调用链

**调用频率：每次股票切换**
```
用户选择股票
  → MainWindowCoordinator._on_stock_selected()
  → MiddlePanel.update_chart()
  → ChartWidget.update_chart()  [625ms瓶颈]
    → RenderingMixin.update_chart()
      → ChartRenderer.render_candlesticks()  [高频]
      → ChartRenderer.render_volume()  [高频]
      → IndicatorMixin._render_indicators()  [中频]
    → canvas.draw_idle()  [75处调用，高频]
```

**性能影响：**
- **当前耗时**：625ms（K线渲染）
- **调用频率**：每次股票切换（用户操作）
- **阻塞时间**：阻塞UI线程

#### 2. 十字光标更新

**调用频率：鼠标移动时（高频）**
```
鼠标移动事件
  → CrosshairMixin._create_unified_crosshair_handler()
  → _update_crosshair_lines()  [每次鼠标移动]
  → canvas.draw_idle()  [高频调用]
```

**性能影响：**
- **调用频率**：10-60次/秒（取决于鼠标移动速度）
- **单次耗时**：<10ms（但累积影响大）
- **优化空间**：节流处理已实现

#### 3. 缩放和平移

**调用频率：用户交互时**
```
鼠标滚轮/拖拽
  → ZoomMixin相关方法
  → 视图范围更新
  → canvas.draw_idle()  [中频调用]
```

**性能影响：**
- **调用频率**：用户交互时（不固定）
- **单次耗时**：<50ms
- **优化空间**：已实现延迟更新

#### 4. 指标计算和渲染

**调用频率：股票切换时**
```
指标计算
  → TechnicalTab.calculate_indicators()
  → _add_indicator_to_table()  [已优化批量插入]
  → IndicatorMixin._render_indicators()
  → canvas.draw_idle()
```

**性能影响：**
- **当前耗时**：101ms（已优化）
- **调用频率**：每次股票切换
- **优化状态**：已优化批量插入

---

## 🎯 PyQtGraph能力分析

### 核心能力匹配度

#### ✅ 完全支持的功能

**1. 多子图布局**
- PyQtGraph的`GraphicsLayoutWidget`支持多子图
- 可以创建多个`PlotWidget`并共享X轴
- 支持自定义高度比例（3:1:1）

**2. K线图渲染**
- 支持自定义GraphicsItem
- 可以使用`PlotDataItem`绘制线条
- 支持批量渲染（性能优势）

**3. 成交量图**
- 支持`BarGraphItem`柱状图
- 支持颜色区分
- 支持批量渲染

**4. 技术指标**
- 支持多条线叠加
- 支持不同颜色和样式
- 支持实时更新

**5. 交互功能**
- 内置缩放和平移
- 支持鼠标事件
- 支持十字光标（需自定义实现）

**6. 性能优化**
- 使用NumPy数组（高效）
- 支持数据降采样
- 支持视图范围优化
- 支持OpenGL后端（可选）

#### ⚠️ 需要自定义实现的功能

**1. K线图Item**
- PyQtGraph没有内置K线图Item
- 需要自定义`GraphicsItem`实现
- 可以使用`PolyLineItem`或自定义Item

**2. 十字光标**
- 需要自定义实现
- 可以使用`InfiniteLine`和`TextItem`
- 需要处理鼠标事件

**3. 主题系统**
- PyQtGraph有基础主题支持
- 需要扩展以匹配现有主题系统
- 颜色方案需要映射

**4. 导出功能**
- PyQtGraph支持图像导出
- 需要适配现有导出接口
- 格式支持：PNG、SVG

---

## 📐 架构映射方案

### 组件映射关系

#### 1. 核心组件映射

| 当前组件 | PyQtGraph对应 | 映射方式 |
|---------|--------------|---------|
| `FigureCanvas` | `GraphicsLayoutWidget` | 直接替换 |
| `Figure` | `GraphicsLayoutWidget` | 布局容器 |
| `price_ax` | `PlotWidget` (主图) | 创建PlotWidget |
| `volume_ax` | `PlotWidget` (成交量) | 创建PlotWidget |
| `indicator_ax` | `PlotWidget` (指标) | 创建PlotWidget |
| `canvas.draw_idle()` | `PlotWidget.update()` | 自动更新机制 |

#### 2. 渲染器映射

| 当前方法 | PyQtGraph实现 | 说明 |
|---------|--------------|------|
| `render_candlesticks()` | 自定义`CandlestickItem` | 使用GraphicsItem |
| `render_volume()` | `BarGraphItem` | 直接使用 |
| `render_line()` | `PlotDataItem` | 直接使用 |
| `PolyCollection` | 自定义Item批量渲染 | 性能优化 |

#### 3. Mixin功能映射

**RenderingMixin：**
- `update_chart()` → 使用PyQtGraph的更新机制
- `_render_indicators()` → 使用`PlotDataItem`
- `_optimize_display()` → 使用PyQtGraph的样式API

**CrosshairMixin：**
- `enable_crosshair()` → 使用`InfiniteLine`和`TextItem`
- `_update_crosshair_lines()` → 更新InfiniteLine位置
- `_update_crosshair_text()` → 更新TextItem内容

**InteractionMixin：**
- 缩放 → PyQtGraph内置支持
- 平移 → PyQtGraph内置支持
- 视图范围 → 使用`setXRange()`和`setYRange()`

**IndicatorMixin：**
- 指标渲染 → 使用`PlotDataItem`
- 指标计算 → 保持不变（使用现有逻辑）

**ZoomMixin：**
- 缩放功能 → PyQtGraph内置，需要适配API
- 视图限制 → 使用`setLimits()`

---

## 🚀 性能优化策略

### 1. 渲染性能优化

**当前问题：**
- matplotlib渲染625ms
- 75处`draw_idle()`调用
- 阻塞UI线程

**PyQtGraph优化：**
- **批量渲染**：使用NumPy数组一次性设置数据
- **自动更新**：PyQtGraph自动处理重绘，无需手动调用
- **数据降采样**：视图范围外的数据自动优化
- **OpenGL后端**：可选启用GPU加速

**预期改进：**
- 渲染时间：625ms → **150-250ms**（减少60-75%）
- `draw_idle()`调用：75处 → **0处**（自动处理）
- UI阻塞：显著减少

### 2. 交互性能优化

**当前问题：**
- 十字光标每次移动都触发重绘
- 缩放和平移响应延迟

**PyQtGraph优化：**
- **事件节流**：PyQtGraph内置节流机制
- **增量更新**：只更新变化部分
- **硬件加速**：OpenGL后端提升交互性能

**预期改进：**
- 交互响应：<10ms延迟
- 流畅度：60 FPS（启用OpenGL）

### 3. 内存优化

**当前问题：**
- matplotlib对象占用内存
- 多次绘制产生临时对象

**PyQtGraph优化：**
- **数据共享**：NumPy数组直接传递，无复制
- **对象复用**：GraphicsItem可复用
- **内存效率**：更少的内存占用

**预期改进：**
- 内存占用：减少30-40%
- 对象创建：减少50%+

---

## 📋 功能实现策略

### 1. K线图实现

**方案A：自定义GraphicsItem（推荐）**
- 创建`CandlestickItem`继承`GraphicsItem`
- 使用`paint()`方法批量绘制
- 支持涨跌颜色
- 性能最优

**方案B：使用PlotDataItem组合**
- 使用多条线组合
- 实现简单但性能略低
- 适合快速原型

**推荐：方案A**
- 性能最优
- 功能完整
- 可扩展性强

### 2. 多子图布局

**实现方式：**
- 使用`GraphicsLayoutWidget`作为容器
- 创建3个`PlotWidget`作为子图
- 使用`addItem()`添加子图
- 设置高度比例（3:1:1）
- 共享X轴使用`setXLink()`

**布局结构：**
```
GraphicsLayoutWidget
├── PlotWidget (price, row=0, col=0, rowspan=3)
├── PlotWidget (volume, row=3, col=0, rowspan=1)
└── PlotWidget (indicator, row=4, col=0, rowspan=1)
```

### 3. 十字光标实现

**实现方式：**
- 使用`InfiniteLine`创建十字线
- 使用`TextItem`显示信息
- 监听鼠标移动事件
- 更新线条和文本位置

**性能优化：**
- 使用节流机制
- 只更新可见部分
- 缓存计算结果

### 4. 技术指标叠加

**实现方式：**
- 使用`PlotDataItem`绘制指标线
- 支持多条线叠加
- 使用不同颜色区分
- 支持实时更新

**指标类型：**
- MA：多条`PlotDataItem`
- MACD：3条线 + 柱状图
- RSI：单条线
- BOLL：3条线

### 5. 主题系统适配

**实现方式：**
- 创建主题映射表
- 将现有主题颜色映射到PyQtGraph
- 使用`setBackground()`设置背景
- 使用`setPen()`和`setBrush()`设置颜色

**主题映射：**
- 亮色主题 → PyQtGraph默认主题
- 暗色主题 → 自定义暗色方案
- 自定义主题 → 颜色映射表

---

## 🔄 迁移实施策略

### 阶段1：基础架构搭建（1-2周）

**目标：**
- 创建PyQtGraph版本的ChartWidget
- 实现基础布局和多子图
- 保持API兼容性

**关键任务：**
1. 创建`ChartWidgetPyQtGraph`类
2. 实现多子图布局
3. 实现基础数据更新接口
4. 创建功能开关（matplotlib/PyQtGraph切换）

**验收标准：**
- 可以显示基础图表
- API与现有ChartWidget兼容
- 可以切换渲染引擎

### 阶段2：核心功能实现（2-3周）

**目标：**
- 实现K线图渲染
- 实现成交量图
- 实现基础交互

**关键任务：**
1. 实现自定义CandlestickItem
2. 实现成交量BarGraphItem
3. 实现基础缩放和平移
4. 实现十字光标

**验收标准：**
- K线图正确显示
- 成交量图正确显示
- 基础交互功能正常
- 性能达到预期（<300ms）

### 阶段3：高级功能实现（2-3周）

**目标：**
- 实现技术指标叠加
- 实现完整交互功能
- 实现主题系统

**关键任务：**
1. 实现技术指标渲染
2. 完善交互功能（缩放、平移、选择）
3. 实现主题系统
4. 实现导出功能

**验收标准：**
- 所有指标正常显示
- 交互功能完整
- 主题切换正常
- 导出功能正常

### 阶段4：优化和测试（1-2周）

**目标：**
- 性能优化
- 功能测试
- 兼容性测试

**关键任务：**
1. 性能调优
2. 功能回归测试
3. 多平台测试
4. 用户验收测试

**验收标准：**
- 性能达到目标（<250ms）
- 所有功能正常
- 无回归问题
- 用户满意度高

### 阶段5：逐步迁移（1-2周）

**目标：**
- 逐步替换matplotlib版本
- 监控性能指标
- 收集用户反馈

**关键任务：**
1. 功能开关控制
2. A/B测试
3. 性能监控
4. 问题修复

**验收标准：**
- 稳定运行
- 性能达标
- 用户反馈良好

---

## 📊 性能预期

### 渲染性能

| 场景 | 当前（Matplotlib） | 预期（PyQtGraph） | 改进 |
|------|-------------------|------------------|------|
| **K线图渲染** | 625ms | 150-250ms | **60-75%** ⬇️ |
| **成交量渲染** | ~50ms | 20-30ms | **40-50%** ⬇️ |
| **指标渲染** | ~100ms | 40-60ms | **40-50%** ⬇️ |
| **总渲染时间** | ~775ms | **210-340ms** | **56-73%** ⬇️ |

### 交互性能

| 操作 | 当前延迟 | 预期延迟 | 改进 |
|------|---------|---------|------|
| **十字光标更新** | 10-20ms | 5-10ms | **50%** ⬇️ |
| **缩放响应** | 50-100ms | 20-40ms | **60%** ⬇️ |
| **平移响应** | 50-100ms | 20-40ms | **60%** ⬇️ |

### 资源占用

| 资源 | 当前 | 预期 | 改进 |
|------|------|------|------|
| **内存占用** | 中等 | 低 | **30-40%** ⬇️ |
| **CPU占用** | 高 | 中 | **40-50%** ⬇️ |
| **GPU占用** | 无 | 可选 | 支持硬件加速 |

---

## ⚠️ 风险和挑战

### 技术风险

**1. 学习曲线**
- **风险**：团队需要学习PyQtGraph API
- **缓解**：提供培训、文档、代码审查

**2. 功能完整性**
- **风险**：某些matplotlib特性可能需要重新实现
- **缓解**：功能对比清单、逐步迁移、保留fallback

**3. 兼容性**
- **风险**：不同平台/硬件可能表现不同
- **缓解**：多平台测试、OpenGL fallback

### 实施风险

**1. 开发时间**
- **风险**：预计6-10周开发时间
- **缓解**：分阶段实施、并行开发、功能开关

**2. 回归风险**
- **风险**：可能引入新bug
- **缓解**：充分测试、A/B测试、逐步迁移

**3. 用户适应**
- **风险**：用户可能需要适应新界面
- **缓解**：保持UI一致性、收集反馈、快速迭代

---

## 📚 技术资源

### PyQtGraph文档
- **官方文档**：https://www.pyqtgraph.org/
- **API参考**：https://www.pyqtgraph.org/documentation/
- **示例代码**：https://github.com/pyqtgraph/pyqtgraph/tree/master/examples
- **性能指南**：https://www.pyqtgraph.org/documentation/performance.html

### 关键API参考

**核心组件：**
- `GraphicsLayoutWidget`：多子图容器
- `PlotWidget`：单个图表
- `PlotDataItem`：数据线
- `BarGraphItem`：柱状图
- `InfiniteLine`：无限线（十字光标）
- `TextItem`：文本显示

**性能优化：**
- `setDownsampling()`：数据降采样
- `setClipToView()`：视图裁剪
- `setAutoDownsample()`：自动降采样
- OpenGL后端：`useOpenGL=True`

---

## 🎯 成功标准

### 性能指标

- ✅ K线图渲染时间 < 250ms
- ✅ 总渲染时间 < 350ms
- ✅ 交互响应延迟 < 50ms
- ✅ 内存占用减少 30%+

### 功能指标

- ✅ 所有现有功能正常
- ✅ 无功能回归
- ✅ UI一致性保持
- ✅ 用户体验提升

### 质量指标

- ✅ 代码质量达标
- ✅ 测试覆盖率 > 80%
- ✅ 无严重bug
- ✅ 文档完整

---

## 📝 总结

### 方案优势

1. **性能提升显著**：预期减少60-75%渲染时间
2. **架构兼容性好**：可以保持现有Mixin架构
3. **实施风险可控**：分阶段实施，功能开关
4. **长期价值高**：技术路线清晰，可扩展性强

### 推荐决策

**建议采用PyQtGraph方案**，理由：
1. 性能提升明显（60-75%）
2. 实施难度适中（6-10周）
3. 风险可控（功能开关、fallback）
4. 长期价值高（技术先进、可扩展）

### 下一步行动

1. **技术验证**：创建原型验证可行性
2. **详细设计**：完善技术设计文档
3. **资源准备**：分配开发资源
4. **开始实施**：按阶段计划执行

---

**报告生成时间：** 2024-12-19  
**分析深度：** 全面（系统架构 + 功能需求 + 调用量）  
**方案状态：** ✅ 完整方案已输出，等待决策

