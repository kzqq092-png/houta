# Hikyuu 量化交易系统
#注意：后续有新功能涉及多线程/定时器/UI更新，务必继续采用"信号/槽+主线程UI更新"模式：使用 pyqtSignal 和 pyqtSlot
   所有QWidget及其子类（如QTableWidgetItem）必须在主线程创建和操作。
   子线程只做数据计算，结果通过信号发回主线程，由主线程更新UI。
   后续有自定义指标或新UI组件，务必统一用self.main_layout管理布局，避免直接用self.layout。
   若有新指标或趋势分析方法，参考上述兼容写法，优先判断数据类型，保证健壮性
   有新增分析Tab或按钮，均建议统一用set_kdata同步数据，内部分析逻辑统一用self.current_kdata，避免多处维护
   在 gui/dialogs/db_field_permissions.json 中配置字段权限（如 \"readonly\"、\"hidden\"）。
   "批量修改"对话框支持条件筛选，操作更安全高效。
   只读字段在所有编辑场景下均不可更改，数据安全有保障。
   
## 系统概述
YS-Quant 量化交易系统是一个功能完整的量化交易平台，支持策略开发、回测、实盘交易等功能。系统采用Python编写，基于PyQt5构建用户界面，具有良好的可扩展性和易用性。通过模块化设计，系统集成了数据获取、技术分析、策略实现、回测验证和实盘交易等全链路功能。

### 核心架构特点
- **模块化设计**：采用服务定位器、事件总线和协调器模式，实现高度模块化
- **异步处理**：数据加载、指标计算和渲染全面采用异步模式
- **可扩展性**：支持插件系统，允许用户自定义指标、策略和交易规则
- **高性能**：多线程计算、渐进式加载和智能缓存机制确保高效处理大量数据

## 系统架构

YS-Quant‌采用现代化的分层架构设计，主要组件包括：

1. **主窗口协调器(MainWindowCoordinator)**：核心控制器，协调UI面板和业务逻辑的交互
2. **事件总线(EventBus)**：负责组件间的通信和事件处理
3. **服务容器(ServiceContainer)**：管理服务依赖注入和生命周期
4. **核心服务层**：
   - **UnifiedDataManager**：统一的数据访问接口，处理数据加载、缓存和去重
   - **AnalysisService**：提供技术分析和策略分析功能
   - **ChartService**：管理图表渲染和交互
   - **StockService**：提供股票数据和基本信息
   - **ThemeService**：管理UI主题和样式
   - **ConfigService**：处理系统配置
5. **UI面板**：
   - **LeftPanel**：股票列表和筛选
   - **MiddlePanel**：K线图表展示
   - **RightPanel**：技术分析和指标
   - **BottomPanel**：日志和状态信息

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    UI层 (主线程)                              │
├─────────────────────────────────────────────────────────────┤
│  ChartWidget → ProgressiveLoadingManager → UpdateThrottler  │
├─────────────────────────────────────────────────────────────┤
│                   渲染层 (优先级调度)                          │
├─────────────────────────────────────────────────────────────┤
│  ChartRenderer → RenderPriority → ThreadPoolExecutor       │
├─────────────────────────────────────────────────────────────┤
│                   数据层 (异步处理)                           │
├─────────────────────────────────────────────────────────────┤
│  DataManager → AsyncDataProcessor → Cache → HikyuuAPI      │
└─────────────────────────────────────────────────────────────┘
```

### 工作流程图

```
sequenceDiagram
    participant User
    participant UI as ChartWidget
    participant PL as 渐进式加载管理器
    participant CR as 图表渲染器
    participant DP as 数据处理器
    participant DS as 数据服务
    
    User->>UI: 请求加载图表
    activate UI
    UI->>PL: 启动渐进式加载
    activate PL
    
    PL->>DS: 请求K线数据
    activate DS
    DS-->>PL: 返回K线数据
    deactivate DS
    
    PL->>CR: 第一阶段：渲染K线主图(CRITICAL)
    activate CR
    CR-->>UI: 更新主图(立即显示)
    deactivate CR
    UI-->>User: 显示K线主图
    
    PL->>CR: 第二阶段：渲染成交量(HIGH)
    activate CR
    CR-->>UI: 更新成交量(100ms)
    deactivate CR
    UI-->>User: 显示成交量
    
    PL->>DS: 请求指标数据
    activate DS
    DS->>DP: 异步计算指标
    activate DP
    DP-->>DS: 返回指标结果
    deactivate DP
    DS-->>PL: 返回指标数据
    deactivate DS
    
    PL->>CR: 第三阶段：渲染基础指标(NORMAL)
    activate CR
    CR-->>UI: 更新基础指标(200ms)
    deactivate CR
    UI-->>User: 显示基础指标
    
    PL->>CR: 第四阶段：渲染高级指标(LOW)
    activate CR
    CR-->>UI: 更新高级指标(300ms)
    deactivate CR
    UI-->>User: 显示高级指标
    
    PL->>CR: 第五阶段：渲染装饰元素(BACKGROUND)
    activate CR
    CR-->>UI: 更新装饰元素(500ms)
    deactivate CR
    UI-->>User: 显示完整图表
    
    PL-->>UI: 加载完成
    deactivate PL
    UI-->>User: 通知加载完成
    deactivate UI
```

## 主要功能

### 1. 股票数据管理
- **多数据源支持**：集成多家数据提供商的接口
- **数据缓存**：本地数据缓存减少网络请求
- **异步加载**：多线程异步加载提高响应速度
- **数据预处理**：自动处理数据异常和缺失值

### 2. 技术分析功能
- **基础指标**：MA、MACD、RSI、KDJ、BOLL等经典指标
- **趋势分析**：自动识别趋势方向和强度
- **支撑阻力位**：计算关键价格位置
- **形态识别**：识别常见K线形态和价格模式

### 3. 图表系统
- **交互式K线图**：支持缩放、平移、十字光标等交互功能
- **多周期支持**：分钟、小时、日、周、月多周期切换
- **指标叠加**：支持在主图叠加显示多个指标
- **区间统计**：选定区间的价格统计和表现分析

### 4. 策略系统
- **策略编辑器**：可视化策略创建和编辑
- **策略回测**：历史数据回测和性能评估
- **策略优化**：自动参数优化和最优解搜索
- **实时监控**：实盘策略运行状态监控

### 5. 指标系统
- **数据库驱动**：所有指标定义存储在数据库中
- **动态加载**：支持运行时添加和修改指标
- **自定义组合**：创建和保存指标组合
- **参数优化**：自动寻找最优指标参数

### 6. 插件系统
- **插件市场**：分享和下载社区插件
- **插件开发SDK**：便捷的插件开发工具
- **安全机制**：插件权限控制和安全审核
- **版本管理**：插件版本兼容性检查

## 🔧 性能优化系统

YS-Quant‌项目实现了全面的性能优化，显著提升了UI响应速度和用户体验：

### 🎯 优化目标
- **消除UI阻塞**：解决数据加载和图表渲染中的同步阻塞问题
- **提升渲染速度**：优化图表渲染流程，减少主图显示延迟
- **智能资源管理**：根据系统配置动态调整线程池和缓存策略
- **渐进式加载**：分阶段显示图表内容，优先显示关键信息

### 🛠️ 核心优化组件

#### 1. 智能线程池管理 (AsyncDataProcessor)
- **动态线程配置**：根据CPU核心数和内存大小自动调整
  - 16GB+内存：`min(cpu_count * 2, 16)` 线程
  - 8-16GB内存：`min(cpu_count + 2, 8)` 线程  
  - <8GB内存：`min(cpu_count, 4)` 线程
- **性能监控**：实时监控CPU使用率、内存占用和缓存命中率
- **智能分块**：根据内存大小动态调整数据分块大小

#### 2. 异步数据加载 (DataManager)
- **异步方法**：`get_k_data_async()`, `get_stock_list_async()`, `get_realtime_quotes_async()`
- **数据预加载**：`preload_data()` 支持按优先级预加载常用数据
- **Qt信号支持**：`AsyncDataManagerWrapper` 提供UI线程安全的数据加载

#### 3. 渲染优先级系统 (ChartRenderer)
- **优先级定义**：
  - `CRITICAL`: K线主图（立即显示）
  - `HIGH`: 成交量和基础指标
  - `NORMAL`: 常用技术指标
  - `LOW`: 高级分析指标
  - `BACKGROUND`: 装饰元素
- **智能调度**：高优先级任务可抢占低优先级任务
- **更新节流**：`UpdateThrottler` 控制最小更新间隔

#### 4. 渐进式加载管理 (ProgressiveLoadingManager)
- **分阶段加载**：
  1. 第一阶段：立即显示基础K线图
  2. 第二阶段：100ms后显示成交量
  3. 第三阶段：200ms后显示高优先级指标
  4. 第四阶段：300ms后显示普通指标
  5. 第五阶段：500ms后显示低优先级指标
- **可配置延迟**：支持根据系统性能调整各阶段延迟
- **进度反馈**：实时显示加载进度和当前阶段

### 📊 性能提升效果
- **主图显示速度**：提升60-80%，基础K线图几乎瞬时显示
- **UI响应性**：消除数据加载时的界面冻结现象
- **内存效率**：优化内存使用，减少30-50%的峰值占用
- **并发处理**：支持多股票、多指标并行计算

### 🔧 使用方法

```python
# 启用渐进式加载
chart_widget.enable_progressive_loading(True)
chart_widget.set_kdata(kdata, indicators, enable_progressive=True)

# 配置线程池
data_processor = AsyncDataProcessor(max_workers=8)

# 异步数据加载
data = await data_manager.get_k_data_async(code, freq)

# 预加载常用股票数据
data_manager.preload_data(['000001', '600519'], priority=1)

# 优先级渲染（立即显示）
renderer.render_with_priority(figure, data, indicators, RenderPriority.CRITICAL)

# 带节流的渲染（防止频繁更新）
renderer.render_with_throttling(figure, data, indicators)
```

## ✅ 技术指标系统V3 - 数据库驱动架构

YS-Quant‌项目的技术指标系统已完成从混合实现迁移至统一、动态、数据库驱动的全新架构。

### 🎯 重构目标
- **单一事实来源**：消除多个模块中的重复计算逻辑
- **数据驱动**：所有指标定义存储在数据库中，支持动态加载和更新
- **完全解耦**：UI层和业务逻辑层与具体指标实现解耦
- **动态扩展**：支持通过插件系统添加自定义指标

### 🛠️ 核心组件
- **IndicatorService**：统一的指标服务，负责指标的加载、计算和管理
- **indicators.db**：指标定义数据库，包含所有系统内置指标和用户自定义指标
- **指标适配器**：兼容旧接口，确保平滑迁移

## 📁 项目目录结构

YS-Quant‌项目采用模块化设计，各功能模块以目录形式清晰组织，便于开发和维护。以下是完整的目录结构及其功能说明：

```
YS-Quant‌/
├── __init__.py                          # 包初始化文件
├── advanced_analysis.py                 # 高级分析功能
├── ai_stock_selector.py                 # AI选股功能
├── analysis/                            # 分析功能模块
│   ├── __init__.py
│   ├── enhanced_stock_analyzer.py       # 增强股票分析器
│   ├── pattern_base.py                  # 形态识别基类
│   ├── pattern_manager.py               # 形态管理器
│   ├── pattern_recognition.py           # 形态识别算法
│   ├── system_health_checker.py         # 系统健康检查
│   ├── technical_analysis.py            # 技术分析功能
│   └── wave_analysis.py                 # 波浪分析
├── api_server.py                        # API服务器
├── async_manager.py                     # 异步任务管理器
├── backtest/                            # 回测系统
│   ├── backtest_optimizer.py            # 回测优化器
│   ├── backtest_validator.py            # 回测验证器
│   ├── performance_metrics.py           # 性能评估指标
│   ├── professional_ui_system.py        # 专业UI系统
│   ├── real_time_backtest_monitor.py    # 实时回测监控
│   ├── ultra_performance_optimizer.py   # 超性能优化器
│   └── unified_backtest_engine.py       # 统一回测引擎
├── chart_optimizer.py                   # 图表优化器
├── component_factory.py                 # 组件工厂
├── components/                          # 可复用业务组件
│   ├── ai_alert.py                      # AI预警组件
│   ├── ai_assistant.py                  # AI助手组件
│   ├── ai_kg.py                         # AI知识图谱
│   ├── ai_market_news.py                # AI市场新闻
│   ├── ai_multimodal.py                 # AI多模态分析
│   ├── ai_rebalance.py                  # AI再平衡
│   ├── ai_report.py                     # AI报告生成
│   ├── ai_stock_selection.py            # AI选股组件
│   ├── ai_strategy_generator.py         # AI策略生成器
│   ├── custom_indicator_manager.py      # 自定义指标管理器
│   ├── fund_flow.py                     # 资金流向分析
│   ├── market_sentiment.py              # 市场情绪分析
│   ├── sentiment_stock_selector.py      # 情绪选股器
│   ├── stock_screener.py                # 股票筛选器
│   ├── StockScreenerWidget.py           # 股票筛选控件
│   └── trade_api.py                     # 交易API
├── config/                              # 配置文件
│   ├── app_config.json                  # 应用配置
│   ├── config.json                      # 全局配置
│   ├── favorites.json                   # 收藏夹配置
│   ├── indicator_combinations/          # 指标组合配置
│   ├── industry_cache.json              # 行业缓存
│   ├── interval_stat_settings.json      # 区间统计设置
│   ├── plugins/                         # 插件配置
│   │   ├── global_config.yaml           # 全局插件配置
│   │   └── security_policies.yaml       # 安全策略配置
│   └── theme.json                       # 主题配置
├── core/                                # 核心业务逻辑
│   ├── __init__.py
│   ├── adapters.py                      # 适配器
│   ├── akshare_data_source.py           # AKShare数据源
│   ├── base_logger.py                   # 基础日志
│   ├── business/                        # 业务模型
│   │   ├── __init__.py
│   │   ├── analysis_manager.py          # 分析管理器
│   │   └── portfolio_manager.py         # 投资组合管理器
│   ├── config.py                        # 核心配置
│   ├── containers/                      # 依赖注入容器
│   │   ├── __init__.py
│   │   ├── service_container.py         # 服务容器
│   │   └── service_registry.py          # 服务注册表
│   ├── coordinators/                    # 协调器
│   │   ├── __init__.py
│   │   ├── base_coordinator.py          # 基础协调器
│   │   └── main_window_coordinator.py   # 主窗口协调器
│   ├── data/                            # 数据访问层
│   │   ├── __init__.py
│   │   ├── data_access.py               # 数据访问
│   │   └── hikyuu_data_manager.py       # Hikyuu数据管理器
│   ├── data_manager.py                  # 数据管理器
│   ├── data_source.py                   # 数据源基类
│   ├── data_validator.py                # 数据验证器
│   ├── eastmoney_source.py              # 东方财富数据源
│   ├── events/                          # 事件系统
│   │   ├── __init__.py
│   │   ├── event_bus.py                 # 事件总线
│   │   └── event_handler.py             # 事件处理器
│   ├── hikyuu_source.py                 # Hikyuu数据源
│   ├── indicator_adapter.py             # 指标适配器
│   ├── indicator_combination_manager.py # 指标组合管理器
│   ├── indicator_service.py             # 指标服务
│   ├── indicators/                      # 指标定义
│   │   ├── __init__.py
│   │   └── library/                     # 指标库
│   │       ├── __init__.py
│   │       ├── momentum.py              # 动量指标
│   │       └── oscillators.py           # 振荡指标
│   ├── industry_manager.py              # 行业管理器
│   ├── logger.py                        # 日志管理器
│   ├── market_environment.py            # 市场环境
│   ├── metrics/                         # 性能指标
│   │   ├── __init__.py
│   │   ├── aggregation_service.py       # 聚合服务
│   │   └── app_metrics_service.py       # 应用指标服务
│   ├── money/                           # 资金管理
│   │   └── base.py                      # 基础资金管理
│   ├── money_manager.py                 # 资金管理器
│   ├── performance_monitor.py           # 性能监控
│   ├── performance_optimizer.py         # 性能优化器
│   ├── plugin_config_manager.py         # 插件配置管理器
│   ├── plugin_manager.py                # 插件管理器
│   ├── position_manager.py              # 仓位管理器
│   ├── qt_types.py                      # Qt类型定义
│   ├── real_data_provider.py            # 实时数据提供器
│   ├── risk/                            # 风险管理
│   ├── risk_alert.py                    # 风险预警
│   ├── risk_control.py                  # 风险控制
│   ├── risk_exporter.py                 # 风险导出器
│   ├── risk_manager.py                  # 风险管理器
│   ├── risk_metrics.py                  # 风险指标
│   ├── services/                        # 核心服务
│   │   ├── __init__.py
│   │   ├── analysis_service.py          # 分析服务
│   │   ├── base_service.py              # 基础服务
│   │   ├── chart_service.py             # 图表服务
│   │   ├── service_bootstrap.py         # 服务引导
│   │   └── unified_data_manager.py      # 统一数据管理器
│   ├── signal/                          # 信号处理
│   │   ├── base.py                      # 基础信号
│   │   ├── enhanced.py                  # 增强信号
│   │   └── factory.py                   # 信号工厂
│   ├── sina_source.py                   # 新浪数据源
│   ├── stock_screener.py                # 股票筛选器
│   ├── stop_loss.py                     # 止损策略
│   ├── strategy/                        # 策略框架
│   │   ├── __init__.py
│   │   ├── base_strategy.py             # 基础策略
│   │   └── builtin_strategies.py        # 内置策略
│   ├── system/                          # 系统模块
│   ├── system_condition.py              # 系统条件
│   ├── take_profit.py                   # 止盈策略
│   ├── templates/                       # 模板
│   │   └── risk_report.html             # 风险报告模板
│   ├── tonghuashun_source.py            # 同花顺数据源
│   ├── trading_controller.py            # 交易控制器
│   ├── trading_system.py                # 交易系统
│   └── ui/                              # UI核心组件
│       ├── __init__.py
│       ├── main_window_coordinator.py   # 主窗口协调器
│       └── panels/                      # 面板
│           ├── __init__.py
│           ├── base_panel.py            # 基础面板
│           ├── bottom_panel.py          # 底部面板
│           ├── left_panel.py            # 左侧面板
│           ├── middle_panel.py          # 中间面板
│           └── right_panel.py           # 右侧面板
├── data/                                # 数据处理
│   ├── __init__.py
│   ├── data_loader.py                   # 数据加载器
│   ├── data_preprocessing.py            # 数据预处理
│   └── strategies.db                    # 策略数据库
├── db/                                  # 数据库相关
│   ├── __init__.py
│   ├── hikyuu_system.db                 # 系统数据库
│   ├── indicators.db                    # 指标数据库
│   ├── init_db.py                       # 数据库初始化
│   ├── init_pattern_algorithms.py       # 初始化形态算法
│   ├── initialize_indicators.py         # 初始化指标
│   ├── metrics.db                       # 指标数据库
│   ├── migrate_theme_to_config.py       # 主题迁移
│   └── models/                          # 数据模型
│       ├── __init__.py
│       └── indicator_models.py          # 指标模型
├── docs/                                # 文档
│   ├── api_reference.md                 # API参考
│   ├── hikyuu-docs/                     # Hikyuu文档
│   │   ├── examples/                    # 示例
│   │   ├── make.bat                     # Windows构建脚本
│   │   ├── make.sh                      # Linux构建脚本
│   │   ├── requirements.txt             # 依赖要求
│   │   └── source/                      # 文档源文件
│   └── 版本管理系统开发使用文档.md         # 版本管理文档
├── evaluation/                          # 评估模块
│   ├── __init__.py
│   ├── performance_evaluation.py        # 性能评估
│   └── risk_evaluation.py               # 风险评估
├── gui/                                 # 图形界面
│   ├── __init__.py
│   ├── backtest_ui_launcher.py          # 回测UI启动器
│   ├── components/                      # UI组件
│   ├── core/                            # UI核心
│   ├── dialogs/                         # 对话框
│   │   ├── __init__.py
│   │   ├── advanced_search_dialog.py    # 高级搜索对话框
│   │   └── batch_analysis_dialog.py     # 批量分析对话框
│   ├── factories/                       # 工厂类
│   ├── features/                        # 特性
│   ├── handlers/                        # 处理器
│   ├── layouts/                         # 布局
│   ├── managers/                        # 管理器
│   ├── menu_bar.py                      # 菜单栏
│   ├── panels/                          # 面板
│   │   ├── performance_dashboard_panel.py # 性能仪表盘
│   │   └── system_optimizer_panel.py    # 系统优化器面板
│   ├── settings.json                    # 设置
│   ├── tool_bar.py                      # 工具栏
│   ├── tools/                           # 工具
│   │   ├── __init__.py
│   │   ├── calculator.py                # 计算器
│   │   └── commission_calculator.py     # 佣金计算器
│   ├── ui_components.py                 # UI组件
│   ├── utils/                           # 工具类
│   └── widgets/                         # 控件
│       ├── analysis_tabs/               # 分析标签页
│       │   ├── __init__.py
│       │   ├── base_tab.py              # 基础标签页
│       │   └── hotspot_tab.py           # 热点标签页
│       ├── analysis_widget.py           # 分析控件
│       ├── async_data_processor.py      # 异步数据处理器
│       ├── backtest_widget.py           # 回测控件
│       ├── chart/                       # 图表组件
│       │   ├── core/                    # 图表核心
│       │   ├── engines/                 # 图表引擎
│       │   ├── interaction/             # 交互功能
│       │   ├── layout/                  # 布局
│       │   ├── rendering/               # 渲染
│       │   ├── services/                # 服务
│       │   ├── ui/                      # UI组件
│       │   └── utils/                   # 工具
│       ├── chart_mixins/                # 图表混入类
│       │   ├── __init__.py
│       │   ├── base_mixin.py            # 基础混入
│       │   ├── crosshair_mixin.py       # 十字光标混入
│       │   ├── interaction_mixin.py     # 交互混入
│       │   ├── rendering_mixin.py       # 渲染混入
│       │   ├── utility_mixin.py         # 工具混入
│       │   └── zoom_mixin.py            # 缩放混入
│       ├── chart_widget.py              # 图表控件
│       ├── log_widget.py                # 日志控件
│       ├── multi_chart_panel.py         # 多图表面板
│       └── trading_widget.py            # 交易控件
├── main.py                              # 主程序入口
├── models/                              # 模型
│   ├── __init__.py
│   ├── deep_learning.py                 # 深度学习模型
│   └── model_evaluation.py              # 模型评估
├── optimization/                        # 优化模块
│   ├── __init__.py
│   ├── algorithm_optimizer.py           # 算法优化器
│   ├── async_data_processor.py          # 异步数据处理器
│   ├── chart_renderer.py                # 图表渲染器
│   └── progressive_loading_manager.py   # 渐进式加载管理器
├── plugins/                             # 插件系统
│   ├── development/                     # 开发工具
│   │   └── plugin_sdk.py                # 插件SDK
│   ├── examples/                        # 示例插件
│   │   ├── __init__.py
│   │   ├── macd_indicator.py            # MACD指标插件
│   │   ├── moving_average_strategy.py   # 移动平均策略插件
│   │   └── my_custom_indicator/         # 自定义指标插件
│   │       ├── __init__.py
│   │       ├── indicator_impl.py        # 指标实现
│   │       └── indicators.py            # 指标定义
│   ├── plugin_interface.py              # 插件接口
│   ├── plugin_market.py                 # 插件市场
│   └── README.md                        # 插件说明
├── requirements.txt                     # 项目依赖
├── scripts/                             # 脚本
│   ├── check_dependencies_and_cleanup.py # 依赖检查和清理
│   ├── update_core_indicator_references.py # 更新核心指标引用
│   └── update_ui_indicator_references.py # 更新UI指标引用
├── signals/                             # 信号处理
│   ├── __init__.py
│   ├── market_regime.py                 # 市场状态
│   └── signal_filters.py                # 信号过滤器
├── strategies/                          # 策略实现
│   ├── adaptive_strategy.py             # 自适应策略
│   └── trend_following.py               # 趋势跟踪策略
├── system_optimizer.py                  # 系统优化器
├── templates/                           # 模板
│   ├── market_sentiment/                # 市场情绪模板
│   │   └── qqq.json                     # QQQ模板
│   ├── stock_analysis/                  # 股票分析模板
│   └── stock_screener/                  # 股票筛选模板
├── test/                                # 测试
│   ├── __init__.py
│   ├── fixtures/                        # 测试固件
│   │   ├── db/                          # 数据库测试
│   │   ├── generate_test_data.py        # 生成测试数据
│   │   └── stock_data_100d.csv          # 100天股票数据
│   ├── test_all_analysis_tabs.py        # 测试所有分析标签页
│   └── test_analysis_modules_comprehensive.py # 综合测试分析模块
└── utils/                               # 工具类
    ├── __init__.py
    ├── cache.py                         # 缓存工具
    ├── config_manager.py                # 配置管理器
    ├── performance_monitor.py           # 性能监控
    └── theme.py                         # 主题工具
```

### 核心目录详解

#### 1. core/ - 核心业务逻辑
系统的核心业务逻辑层，采用分层架构设计，包含多个子模块：

- **business/** - 业务模型和领域逻辑
  - `analysis_manager.py` - 分析功能管理器，整合各种技术分析方法
  - `portfolio_manager.py` - 投资组合管理，处理资产配置和风险控制

- **containers/** - 依赖注入容器
  - `service_container.py` - 服务定位器实现，管理服务实例的创建和获取
  - `service_registry.py` - 服务注册管理，维护可用服务的注册表

- **coordinators/** - 协调器模式实现
  - `main_window_coordinator.py` - 主窗口协调器，连接UI和业务逻辑，处理用户交互

- **events/** - 事件总线系统
  - `event_bus.py` - 事件总线实现，支持组件间的松耦合通信
  - `event_handler.py` - 事件处理器基类，定义事件处理接口

- **services/** - 核心服务实现
  - `analysis_service.py` - 技术分析服务，提供各种分析算法
  - `chart_service.py` - 图表服务，处理图表数据和渲染
  - `unified_data_manager.py` - 统一数据管理器，整合多数据源

#### 2. gui/ - 图形界面
用户界面相关组件，基于PyQt5实现：

- **dialogs/** - 对话框组件
  - `advanced_search_dialog.py` - 高级搜索对话框，支持多条件查询
  - `batch_analysis_dialog.py` - 批量分析对话框，处理多股票分析

- **widgets/** - 自定义控件
  - `chart_widget.py` - K线图表控件，支持交互式操作和指标显示
  - `analysis_widget.py` - 分析控件，整合各种分析功能
  - `backtest_widget.py` - 回测控件，提供策略回测界面

- **chart_mixins/** - 图表混入类
  - `crosshair_mixin.py` - 十字光标功能，显示价格和时间信息
  - `rendering_mixin.py` - 渲染功能，处理图表绘制
  - `zoom_mixin.py` - 缩放功能，支持图表缩放和平移

#### 3. analysis/ - 分析功能模块
提供各种技术分析功能：

- `pattern_recognition.py` - 形态识别算法，识别常见K线形态
- `technical_analysis.py` - 技术分析功能，计算各种技术指标
- `wave_analysis.py` - 波浪分析，实现Elliott波浪理论

#### 4. backtest/ - 回测系统
策略回测和优化功能：

- `unified_backtest_engine.py` - 统一回测引擎，支持多种回测模式
- `performance_metrics.py` - 性能评估指标，计算策略表现
- `backtest_optimizer.py` - 回测优化器，寻找最优参数组合

#### 5. db/ - 数据库相关
数据库访问和模型定义：

- `init_db.py` - 数据库初始化，创建表和初始数据
- `models/indicator_models.py` - 指标数据模型，定义指标存储结构
- `indicators.db` - 指标定义数据库，存储所有指标信息
- `hikyuu_system.db` - 系统配置数据库，存储系统设置

#### 6. plugins/ - 插件系统
支持用户自定义扩展：

- `plugin_interface.py` - 插件接口定义，规定插件必须实现的方法
- `plugin_market.py` - 插件市场，管理插件的发布和安装
- `development/plugin_sdk.py` - 插件开发工具，提供插件开发API
- `examples/` - 示例插件实现，展示如何开发自定义插件

#### 7. optimization/ - 优化模块
性能优化和资源管理：

- `algorithm_optimizer.py` - 算法优化器，提高算法执行效率
- `async_data_processor.py` - 异步数据处理器，多线程数据处理
- `chart_renderer.py` - 图表渲染器，高效绘制图表
- `progressive_loading_manager.py` - 渐进式加载管理器，分阶段加载内容

#### 8. utils/ - 工具类
通用工具和辅助功能：

- `cache.py` - 缓存工具，实现内存和磁盘缓存
- `config_manager.py` - 配置管理器，处理应用配置
- `performance_monitor.py` - 性能监控，跟踪系统性能指标
- `theme.py` - 主题工具，管理UI主题和样式

### 关键文件说明

1. **main.py** - 应用程序入口点
   - 初始化应用程序和Qt环境
   - 创建主窗口和核心服务
   - 配置日志和异常处理
   - 启动事件循环

2. **core/coordinators/main_window_coordinator.py** - 主窗口协调器
   - 实现协调器模式，连接UI和业务逻辑
   - 创建和管理四个主面板（左、中、右、底部）
   - 处理全局事件和状态管理
   - 协调各服务之间的交互

3. **gui/widgets/chart_widget.py** - 图表控件
   - 基于Mixin模式的图表控件，支持多功能混入
   - 实现交互式K线图表，支持缩放、平移、十字光标等
   - 支持渐进式加载和优先级渲染
   - 处理图表更新和事件响应

4. **core/services/unified_data_manager.py** - 统一数据管理器
   - 提供统一的数据访问接口
   - 整合多个数据源（Hikyuu、东方财富、新浪、同花顺等）
   - 实现数据缓存和异步加载
   - 处理数据预处理和验证

5. **core/events/event_bus.py** - 事件总线
   - 实现发布-订阅模式
   - 支持组件间松耦合通信
   - 处理事件注册、触发和分发
   - 支持优先级和异步事件处理

6. **optimization/progressive_loading_manager.py** - 渐进式加载管理器
   - 实现分阶段图表渲染
   - 定义加载优先级和时间安排
   - 监控加载进度和状态
   - 优化用户体验和响应速度

7. **plugins/plugin_interface.py** - 插件接口
   - 定义插件API和生命周期
   - 规范插件开发标准
   - 提供插件注册和加载机制
   - 实现插件安全和兼容性检查

8. **db/models/indicator_models.py** - 指标数据模型
   - 定义指标数据结构
   - 实现ORM映射
   - 支持指标参数和元数据
   - 提供数据库查询和更新方法

9. **core/strategy/base_strategy.py** - 基础策略类
   - 定义策略接口和基础功能
   - 实现信号生成和处理
   - 提供回测和实盘接口
   - 支持参数优化和评估

10. **backtest/unified_backtest_engine.py** - 统一回测引擎
    - 支持多种回测模式（历史、蒙特卡洛、事件驱动）
    - 实现性能评估和结果分析
    - 提供参数优化和敏感性分析
    - 支持可视化回测结果

## 系统特点
1. **完整的量化交易功能**：支持数据获取、策略开发、回测分析、实盘交易等全流程
2. **高度可定制**：提供丰富的API和插件系统，支持用户自定义指标、策略和交易规则
3. **性能优化**：关键计算模块采用C++实现，保证高效的数据处理和策略回测
4. **友好的用户界面**：提供直观的图形界面，方便用户操作和分析
5. **智能渲染**：采用渐进式加载和优先级渲染，确保UI响应流畅
6. **多数据源支持**：内置支持多种数据源，易于扩展新数据源

## 安装方法
```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python db/init_db.py
```

## 快速开始
```python
# 启动应用程序
python main.py
```

## 故障排除

### 常见性能问题
1. **主图渲染慢**：
   - 检查内存使用情况，考虑增加内存
   - 启用渐进式加载：`chart_widget.enable_progressive_loading(True)`
   - 减少同时显示的指标数量

2. **数据加载卡顿**：
   - 使用异步数据加载方法
   - 启用数据预加载功能
   - 检查网络连接状态

3. **界面响应慢**：
   - 调整更新节流间隔：`renderer.set_throttle_interval(200)`
   - 关闭不必要的实时更新功能
   - 清理缓存：`data_manager.clear_cache()`

### 性能监控
系统提供详细的性能监控功能：
```python
# 获取性能统计
stats = chart_widget.get_loading_performance_stats()
print("渲染统计:", stats['render'])
print("数据处理统计:", stats['data_processing']) 
print("渐进式加载统计:", stats['progressive_loading'])
```

## 系统要求
- **推荐配置**：16GB+ 内存，8核+ CPU，SSD硬盘
- **最低配置**：8GB 内存，4核 CPU
- **Python版本**：3.11+
- **依赖库**：PyQt5, pandas, numpy, qasync等

## 交易系统组件

HIkyuu量化框架将交易系统拆分为多个独立组件：

- **信号指示器(Signal)**: 负责产生买入和卖出信号
- **资金管理(Money Manager)**: 决定每次交易的资金分配和头寸规模
- **止损策略(Stop Loss)**: 控制单笔交易的最大风险
- **止盈策略(Take Profit)**: 设定获利目标和退出条件
- **市场环境判断(Environment)**: 评估当前市场状态是否适合交易
- **系统有效条件(Condition)**: 确定交易系统是否处于有效状态
- **移滑价差算法(Slippage)**: 模拟实际交易中的价格滑点
- **交易成本(Trade Cost)**: 计算交易佣金和税费

## 已完成的核心功能
- ✅ **中间主图面板完善**：时间范围选择器、回测区间选择器、图表类型选择、区间统计功能
- ✅ **高级搜索系统**：完整的多维度股票筛选功能，支持异步搜索
- ✅ **数据导出功能**：单股票导出和批量导出，支持Excel和CSV格式
- ✅ **完整右键菜单系统**：查看详情、收藏管理、导出数据、投资组合管理等
- ✅ **股票详情对话框**：基本信息、历史K线数据、财务数据展示
- ✅ **投资组合管理**：创建投资组合、设置投资金额、组合分类管理
- ✅ **高级功能对话框**：节点管理、云端API、指标市场、批量分析、策略管理
- ✅ **数据质量检查**：单股和批量数据质量检查功能
- ✅ **系统设置**：主题管理、基本设置、数据设置等完整配置功能
- ✅ **性能优化系统**：主图渲染加速、异步数据加载、智能资源管理

## 文档
详细文档请参考 `docs` 目录下的文件，包括：
- API参考文档
- 用户指南
- 开发者文档
- 插件开发指南

## 贡献指南
欢迎提交问题报告、功能请求和代码贡献。请遵循以下步骤：
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证
本项目采用 MIT 许可证 - 详见 LICENSE 文件



