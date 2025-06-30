# Main.py 重构详细开发计划

## 📋 **项目概述**

基于前期深入分析，本文档提供main.py重构的详细开发计划，包括具体的目录结构、文件清单、代码块功能分配和实施步骤。

---

## 🗂️ **目标目录结构**

### **重构后的项目结构**
```
hikyuu-ui/
├── main.py                          # 精简主入口 (50行)
├── core/
│   ├── coordinators/                # 新增：协调器模块
│   │   ├── __init__.py
│   │   ├── main_window_coordinator.py    # 主窗口协调器 (300行)
│   │   └── ui_coordinator.py            # UI协调器 (200行)
│   ├── services/                    # 新增：业务服务层
│   │   ├── __init__.py
│   │   ├── stock_service.py             # 股票业务服务 (400行)
│   │   ├── analysis_service.py          # 分析业务服务 (500行)
│   │   ├── chart_service.py             # 图表业务服务 (300行)
│   │   └── data_service.py              # 数据业务服务 (350行)
│   ├── events/                      # 新增：事件系统
│   │   ├── __init__.py
│   │   ├── event_bus.py                 # 事件总线 (200行)
│   │   ├── event_types.py               # 事件类型定义 (100行)
│   │   └── event_handlers.py            # 事件处理器 (250行)
│   ├── containers/                  # 新增：依赖注入
│   │   ├── __init__.py
│   │   ├── service_container.py         # 服务容器 (200行)
│   │   └── dependency_injector.py       # 依赖注入器 (150行)
│   └── [现有文件保持不变]
├── gui/
│   ├── widgets/ [保持现有结构]
│   ├── panels/                      # 现有空目录，新增面板
│   │   ├── __init__.py
│   │   ├── left_panel.py                # 左侧面板 (400行)
│   │   ├── middle_panel.py              # 中间面板 (300行)
│   │   ├── right_panel.py               # 右侧面板 (350行)
│   │   └── bottom_panel.py              # 底部面板 (200行)
│   ├── managers/                    # 现有空目录，新增管理器
│   │   ├── __init__.py
│   │   ├── ui_manager.py                # UI管理器 (300行)
│   │   ├── layout_manager.py            # 布局管理器 (250行)
│   │   └── interaction_manager.py       # 交互管理器 (200行)
│   └── [其他现有文件保持不变]
└── [其他目录保持不变]
```

---

## 📝 **详细文件计划**

### **阶段1: 核心架构搭建 (第1-2周)**

#### **1.1 事件系统** (优先级: 🔴 高)

**文件: `core/events/event_bus.py`**
```python
"""
事件总线 - 系统核心通信机制
功能: 统一的事件发布订阅机制，替代现有的信号槽连接
代码量: 约200行
"""
class EventBus(QObject):
    def __init__(self):
        # 事件订阅者管理
        self.subscribers = {}
        # 事件历史记录
        self.event_history = []
        # 异步事件队列
        self.async_queue = Queue()
    
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        pass
    
    def publish(self, event: Event):
        """发布事件"""
        pass
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        pass

# 从main.py迁移的代码块:
# - connect_signals() 方法 (第248-285行)
# - 所有信号连接逻辑
# - 事件处理方法 (handle_*)
```

**文件: `core/events/event_types.py`**
```python
"""
事件类型定义 - 标准化事件接口
功能: 定义所有系统事件类型和数据结构
代码量: 约100行
"""
@dataclass
class StockSelectedEvent:
    stock_code: str
    stock_data: dict
    timestamp: datetime

@dataclass  
class AnalysisCompletedEvent:
    results: dict
    analysis_type: str
    timestamp: datetime

# 从main.py迁移的信号定义:
# - theme_changed = pyqtSignal(Theme)
# - data_updated = pyqtSignal(dict)
# - analysis_completed = pyqtSignal(dict)
# - performance_updated = pyqtSignal(dict)
# - error_occurred = pyqtSignal(str)
```

#### **1.2 服务容器** (优先级: 🔴 高)

**文件: `core/containers/service_container.py`**
```python
"""
服务容器 - 依赖注入核心
功能: 管理所有服务实例，提供依赖注入能力
代码量: 约200行
"""
class ServiceContainer:
    def __init__(self):
        self.services = {}
        self.singletons = {}
        self.factories = {}
    
    def register_singleton(self, service_type: Type, instance):
        """注册单例服务"""
        pass
    
    def register_factory(self, service_type: Type, factory: Callable):
        """注册工厂服务"""
        pass
    
    def get(self, service_type: Type):
        """获取服务实例"""
        pass

# 从main.py迁移的初始化代码:
# - 所有管理器初始化逻辑 (第130-220行)
# - self.config_manager, self.log_manager等
```

#### **1.3 主窗口协调器** (优先级: 🔴 高)

**文件: `core/coordinators/main_window_coordinator.py`**
```python
"""
主窗口协调器 - 替代原TradingGUI类
功能: 协调各个面板和服务，不包含具体业务逻辑
代码量: 约300行
"""
class MainWindowCoordinator(QMainWindow):
    def __init__(self, container: ServiceContainer):
        super().__init__()
        self.container = container
        self.event_bus = container.get(EventBus)
        
        # 初始化各个面板
        self.left_panel = LeftPanel(container)
        self.middle_panel = MiddlePanel(container)
        self.right_panel = RightPanel(container)
        self.bottom_panel = BottomPanel(container)
        
        self.setup_ui()
        self.connect_events()
    
    def setup_ui(self):
        """设置UI布局"""
        pass
    
    def connect_events(self):
        """连接事件"""
        pass

# 从main.py迁移的代码块:
# - init_ui() 方法 (第393-469行)
# - 窗口基础设置和布局代码
# - 菜单栏和状态栏创建 (保持接口不变)
```

### **阶段2: 业务服务层 (第2-3周)**

#### **2.1 股票业务服务** (优先级: 🔴 高)

**文件: `core/services/stock_service.py`**
```python
"""
股票业务服务 - 股票相关业务逻辑
功能: 股票选择、筛选、收藏等业务逻辑
代码量: 约400行
"""
class StockService:
    def __init__(self, data_manager, event_bus):
        self.data_manager = data_manager
        self.event_bus = event_bus
        self.current_stock = None
        self.favorites = set()
    
    def select_stock(self, stock_code: str):
        """选择股票"""
        pass
    
    def filter_stocks(self, filters: dict) -> List[dict]:
        """筛选股票"""
        pass
    
    def toggle_favorite(self, stock_code: str):
        """切换收藏状态"""
        pass

# 从main.py迁移的代码块:
# - on_stock_selected() 方法 (第2630-2732行)
# - filter_stock_list() 方法 (第1297-1411行)
# - toggle_favorite() 方法 (第2192-2230行)
# - 股票列表相关的所有业务逻辑
```

#### **2.2 分析业务服务** (优先级: 🔴 高)

**文件: `core/services/analysis_service.py`**
```python
"""
分析业务服务 - 分析相关业务逻辑
功能: 技术分析、策略分析、回测等业务逻辑
代码量: 约500行
"""
class AnalysisService:
    def __init__(self, data_manager, event_bus):
        self.data_manager = data_manager
        self.event_bus = event_bus
        self.current_strategy = None
        self.analysis_results = {}
    
    def run_analysis(self, stock_code: str, strategy: str) -> dict:
        """执行分析"""
        pass
    
    def run_backtest(self, strategy: str, params: dict) -> dict:
        """执行回测"""
        pass
    
    def get_analysis_results(self) -> dict:
        """获取分析结果"""
        pass

# 从main.py迁移的代码块:
# - analyze() 方法 (第3986-4048行)
# - _execute_analysis() 方法 (第4049-4254行)
# - backtest() 方法 (第5808-5829行)
# - 所有分析相关的业务逻辑
```

#### **2.3 图表业务服务** (优先级: 🟡 中)

**文件: `core/services/chart_service.py`**
```python
"""
图表业务服务 - 图表相关业务逻辑  
功能: 图表更新、主题切换、数据同步等
代码量: 约300行
"""
class ChartService:
    def __init__(self, data_manager, event_bus):
        self.data_manager = data_manager
        self.event_bus = event_bus
        self.current_chart_data = None
        self.chart_widgets = []
    
    def update_chart(self, stock_code: str, period: str):
        """更新图表"""
        pass
    
    def apply_theme(self, theme: Theme):
        """应用主题"""
        pass
    
    def sync_charts(self, data: dict):
        """同步多图表"""
        pass

# 从main.py迁移的代码块:
# - update_chart() 方法 (第3879-3933行)
# - on_period_changed() 方法 (第2085-2125行)
# - apply_theme() 方法中的图表部分 (第729-756行)
```

### **阶段3: UI面板重构 (第3-4周)**

#### **3.1 左侧面板** (优先级: 🟡 中)

**文件: `gui/panels/left_panel.py`**
```python
"""
左侧面板 - 股票列表和指标选择
功能: 股票列表显示、筛选、指标选择等UI逻辑
代码量: 约400行
"""
class LeftPanel(QWidget):
    def __init__(self, container: ServiceContainer):
        super().__init__()
        self.container = container
        self.stock_service = container.get(StockService)
        self.event_bus = container.get(EventBus)
        
        self.setup_ui()
        self.connect_events()
    
    def setup_ui(self):
        """设置UI"""
        # 创建股票列表
        # 创建指标选择
        # 创建筛选控件
        pass
    
    def on_stock_selected(self, item):
        """股票选择事件"""
        pass

# 从main.py迁移的代码块:
# - create_left_panel() 方法 (第757-987行)
# - 股票列表UI创建和事件处理
# - 指标选择UI和逻辑
```

#### **3.2 中间面板** (优先级: 🟡 中)

**文件: `gui/panels/middle_panel.py`**
```python
"""
中间面板 - 图表显示区域
功能: 图表显示、工具栏、多屏切换等UI逻辑
代码量: 约300行
"""
class MiddlePanel(QWidget):
    def __init__(self, container: ServiceContainer):
        super().__init__()
        self.container = container
        self.chart_service = container.get(ChartService)
        self.event_bus = container.get(EventBus)
        
        self.setup_ui()
        self.connect_events()
    
    def setup_ui(self):
        """设置UI"""
        # 创建图表组件
        # 创建工具栏
        # 创建多屏面板
        pass

# 从main.py迁移的代码块:
# - create_middle_panel() 方法 (第1513-1595行)
# - 图表相关UI创建和事件处理
# - 工具栏创建和功能绑定
```

#### **3.3 右侧面板** (优先级: 🟡 中)

**文件: `gui/panels/right_panel.py`**
```python
"""
右侧面板 - 分析和交易区域
功能: 分析标签页、交易控件等UI逻辑
代码量: 约350行
"""
class RightPanel(QWidget):
    def __init__(self, container: ServiceContainer):
        super().__init__()
        self.container = container
        self.analysis_service = container.get(AnalysisService)
        self.event_bus = container.get(EventBus)
        
        self.setup_ui()
        self.connect_events()
    
    def setup_ui(self):
        """设置UI"""
        # 创建分析标签页
        # 创建交易控件
        # 创建优化面板
        pass

# 从main.py迁移的代码块:
# - create_right_panel() 方法 (第1763-1817行)
# - 分析标签页创建和管理
# - 交易控件集成
```

### **阶段4: 集成测试和优化 (第5-6周)**

#### **4.1 主入口文件重构** (优先级: 🔴 高)

**文件: `main.py` (重构后)**
```python
"""
主入口文件 - 精简版
功能: 应用启动和基础配置，委托给协调器处理
代码量: 约50行
"""
import sys
from PyQt5.QtWidgets import QApplication
from core.containers.service_container import ServiceContainer
from core.coordinators.main_window_coordinator import MainWindowCoordinator
from utils.manager_factory import setup_managers

def main():
    """应用主入口"""
    app = QApplication(sys.argv)
    
    # 设置全局样式
    app.setStyleSheet(get_global_styles())
    
    # 初始化服务容器
    container = ServiceContainer()
    setup_managers(container)
    
    # 创建主窗口协调器
    main_window = MainWindowCoordinator(container)
    main_window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

# 原main.py的5987行代码精简为50行
# 所有业务逻辑都迁移到对应的服务和面板中
```

---

## 🔄 **代码迁移映射表**

### **main.py原有代码块分配**

| 原代码块 | 行数范围 | 目标文件 | 新功能模块 |
|---------|---------|---------|-----------|
| `__init__()` 初始化 | 75-247 | `service_container.py` | 服务注册和依赖注入 |
| `connect_signals()` | 248-285 | `event_bus.py` | 事件订阅机制 |
| `init_ui()` | 393-469 | `main_window_coordinator.py` | UI协调和布局 |
| `create_menubar()` | 473-555 | `main_window_coordinator.py` | 菜单栏创建 |
| `create_left_panel()` | 757-987 | `left_panel.py` | 左侧面板UI |
| `filter_stock_list()` | 1297-1411 | `stock_service.py` | 股票筛选业务 |
| `create_middle_panel()` | 1513-1595 | `middle_panel.py` | 中间面板UI |
| `create_right_panel()` | 1763-1817 | `right_panel.py` | 右侧面板UI |
| `on_stock_selected()` | 2630-2732 | `stock_service.py` | 股票选择业务 |
| `create_bottom_panel()` | 2835-2873 | `bottom_panel.py` | 底部面板UI |
| `analyze()` | 3986-4048 | `analysis_service.py` | 分析业务逻辑 |
| `update_chart()` | 3879-3933 | `chart_service.py` | 图表更新业务 |
| 工具类方法 | 3165-3454 | `gui/tools/` | 工具组件 |
| 优化相关方法 | 5103-5429 | `optimization/` | 优化模块 |

### **保持不变的组件**

| 组件 | 文件路径 | 原因 |
|------|---------|------|
| BaseAnalysisTab | `gui/widgets/analysis_tabs/base_tab.py` | 设计优秀，无需修改 |
| ChartWidget | `gui/widgets/chart_widget.py` | 功能完整，接口稳定 |
| TradingWidget | `gui/widgets/trading_widget.py` | 组件化良好 |
| 所有analysis_tabs | `gui/widgets/analysis_tabs/` | 专业分析功能完整 |
| 管理器工厂 | `utils/manager_factory.py` | 架构合理 |
| 配置管理 | `utils/config_manager.py` | 功能稳定 |

---

## 📅 **详细时间计划**

### **第1周: 事件系统和依赖注入**
```
周一-周二: 事件系统开发
├── event_bus.py 实现
├── event_types.py 定义
└── 基础测试

周三-周四: 服务容器开发  
├── service_container.py 实现
├── dependency_injector.py 实现
└── 集成测试

周五: 主窗口协调器框架
├── main_window_coordinator.py 基础框架
├── 与现有组件集成测试
└── 代码审查
```

### **第2周: 核心业务服务**
```
周一-周二: 股票业务服务
├── stock_service.py 实现
├── 从main.py迁移股票相关逻辑
└── 单元测试

周三-周四: 分析业务服务
├── analysis_service.py 实现  
├── 从main.py迁移分析相关逻辑
└── 单元测试

周五: 图表业务服务
├── chart_service.py 实现
├── 与ChartWidget集成
└── 集成测试
```

### **第3周: UI面板重构**
```
周一: 左侧面板
├── left_panel.py 实现
├── 从main.py迁移UI逻辑
└── 功能测试

周二: 中间面板
├── middle_panel.py 实现
├── 图表集成
└── 功能测试

周三: 右侧面板
├── right_panel.py 实现
├── 分析标签页集成
└── 功能测试

周四: 底部面板
├── bottom_panel.py 实现
├── 控制逻辑集成
└── 功能测试

周五: UI集成测试
├── 所有面板集成
├── 布局和交互测试
└── 问题修复
```

### **第4周: 主入口重构和集成**
```
周一-周二: 主入口重构
├── main.py 精简重写
├── 启动流程优化
└── 服务初始化测试

周三-周四: 全系统集成
├── 所有模块集成测试
├── 功能完整性验证
└── 性能基准测试

周五: 问题修复
├── Bug修复
├── 性能优化
└── 代码审查
```

### **第5周: 测试和优化**
```
周一-周二: 功能测试
├── 所有功能回归测试
├── 用户场景测试
└── 兼容性测试

周三-周四: 性能优化
├── 启动时间优化
├── 内存使用优化
└── 响应速度优化

周五: 文档和部署
├── 技术文档更新
├── 部署脚本准备
└── 发布准备
```

### **第6周: 发布和验收**
```
周一-周二: 用户验收测试
├── 内部用户测试
├── 反馈收集和处理
└── 最终调优

周三-周四: 正式发布
├── 生产环境部署
├── 监控和日志配置
└── 回滚方案准备

周五: 项目总结
├── 重构效果评估
├── 经验总结文档
└── 后续优化计划
```

---

## 🧪 **测试策略**

### **单元测试覆盖**
```
必须测试的模块:
├── EventBus - 事件发布订阅机制
├── ServiceContainer - 依赖注入功能
├── StockService - 股票业务逻辑
├── AnalysisService - 分析业务逻辑
└── ChartService - 图表业务逻辑

测试覆盖率目标: >80%
```

### **集成测试重点**
```
关键集成点:
├── 事件系统与UI组件集成
├── 服务层与数据层集成
├── 新旧组件接口兼容性
└── 整体功能完整性
```

### **性能测试基准**
```
性能指标:
├── 启动时间: <10秒
├── 股票切换: <2秒
├── 分析计算: <15秒
├── 内存使用: <500MB
└── CPU使用: <50%
```

---

## 🎯 **成功验收标准**

### **功能完整性** ✅
- [ ] 所有现有功能正常工作
- [ ] 无功能缺失或降级
- [ ] 用户操作习惯保持不变
- [ ] 数据兼容性完整

### **代码质量** ✅
- [ ] 主文件代码行数 <600行
- [ ] 圈复杂度 <25
- [ ] 测试覆盖率 >60%
- [ ] 代码审查通过

### **性能指标** ✅
- [ ] 启动时间提升 >20%
- [ ] 开发效率提升 >30%
- [ ] Bug修复效率提升 >50%
- [ ] 系统稳定性保持

### **团队满意度** ✅
- [ ] 开发团队满意度 >80%
- [ ] 代码可维护性显著提升
- [ ] 新人上手时间 <1周
- [ ] 技术债务大幅减少

**本开发计划基于保守估算，确保在6周内完成高质量的重构工作，实现代码质量和开发效率的显著提升。** 