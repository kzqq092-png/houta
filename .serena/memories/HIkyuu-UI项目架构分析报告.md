# HIkyuu-UI量化交易系统架构分析报告

## 项目概述
HIkyuu-UI是一个基于Python的量化交易系统，采用PyQt5构建用户界面，具有完整的数据获取、技术分析、策略回测和实盘交易功能。

## 架构特点

### 1. 核心架构模式
- **协调器模式**: MainWindowCoordinator作为核心控制器
- **服务定位器**: ServiceContainer管理服务依赖注入
- **事件总线**: EventBus实现组件间松耦合通信
- **分层架构**: 清晰的UI层、服务层、业务逻辑层、数据层分离

### 2. 主要组件
- **core/**: 核心业务逻辑，包含23个子模块
- **gui/**: 图形界面组件，基于PyQt5
- **plugins/**: 插件系统，支持扩展功能
- **optimization/**: 性能优化模块
- **db/**: 数据库相关，支持SQLite和DuckDB

### 3. 技术栈
- **UI框架**: PyQt5 + qasync异步支持
- **数据处理**: pandas, numpy, ta-lib
- **机器学习**: tensorflow, scikit-learn, xgboost
- **数据库**: SQLite (配置) + DuckDB (分析)
- **日志系统**: Loguru现代化日志架构
- **图表渲染**: matplotlib + WebGPU硬件加速

## 执行流程

### 1. 应用启动流程
```
main.py → FactorWeaveQuantApplication.initialize() → 
创建Qt应用 → 初始化核心组件 → 注册服务 → 创建主窗口协调器 → 运行事件循环
```

### 2. 服务注册流程
```
bootstrap_services() → 注册各种服务到ServiceContainer → 
AnalysisService, ChartService, DataManager等
```

### 3. UI组件协调
```
MainWindowCoordinator → 创建四个面板(左中右底) → 
事件总线协调组件交互 → 异步数据加载和渲染
```

## 性能优化特性
1. **渐进式加载**: 分阶段显示图表内容
2. **异步数据处理**: 多线程数据加载和计算
3. **WebGPU硬件加速**: GPU加速图表渲染
4. **智能缓存**: 多层缓存机制
5. **优先级渲染**: 关键内容优先显示

## 数据流向
```
用户操作 → UI事件 → 事件总线 → 服务层处理 → 数据层查询 → 
异步计算 → 结果缓存 → UI更新
```