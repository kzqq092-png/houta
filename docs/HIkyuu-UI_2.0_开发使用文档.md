# FactorWeave-Quant ‌ 2.0 开发使用文档

## 项目概述

FactorWeave-Quant ‌ 2.0 是一个基于 Python 3.11 的专业股票分析系统，采用现代化的模块化架构设计，提供完整的股票分析、形态识别、策略回测、优化系统等功能。

### 核心特性

- **模块化架构**：采用依赖注入和服务容器模式
- **事件驱动**：松耦合的事件系统
- **分布式计算**：支持多节点分布式处理
- **云端集成**：完整的云端API和数据同步
- **插件生态**：可扩展的插件系统
- **AI优化**：67种形态识别算法的智能优化

## 系统架构

### 目录结构

```
FactorWeave-Quant ‌/
├── core/                    # 核心模块
│   ├── services/           # 服务层
│   ├── coordinators/       # 协调器
│   ├── ui/                # UI组件
│   ├── data/              # 数据访问
│   └── business/          # 业务逻辑
├── gui/                    # 图形界面
│   ├── dialogs/           # 对话框
│   ├── widgets/           # 控件
│   └── panels/            # 面板
├── analysis/              # 分析模块
├── optimization/          # 优化系统
├── plugins/               # 插件系统
├── backtest/             # 回测模块
└── docs/                 # 文档
```

### 核心组件

#### 1. 服务容器 (ServiceContainer)

服务容器是系统的核心，负责管理所有服务的生命周期和依赖注入。

**位置**: `core/service_container.py`

**基本用法**:

```python
from core.service_container import ServiceContainer

# 创建服务容器
container = ServiceContainer()

# 注册服务
container.register('data_service', DataService, singleton=True)

# 获取服务
data_service = container.get_service('data_service')
```

**支持的服务类型**:
- `data_service`: 数据服务
- `analysis_service`: 分析服务
- `distributed_service`: 分布式服务
- `cloud_api_service`: 云端API服务
- `plugin_service`: 插件服务

#### 2. 事件总线 (EventBus)

事件总线提供组件间的松耦合通信机制。

**位置**: `core/event_bus.py`

**基本用法**:

```python
from core.event_bus import EventBus

# 创建事件总线
event_bus = EventBus()

# 订阅事件
def on_stock_selected(event_data):
    print(f"股票选择: {event_data['code']}")

event_bus.subscribe('stock_selected', on_stock_selected)

# 发布事件
event_bus.publish('stock_selected', {'code': '000001', 'name': '平安银行'})
```

**内置事件类型**:
- `stock_selected`: 股票选择事件
- `analysis_completed`: 分析完成事件
- `optimization_started`: 优化开始事件
- `data_updated`: 数据更新事件

#### 3. 主窗口协调器 (MainWindowCoordinator)

主窗口协调器负责协调各个UI面板和业务逻辑。

**位置**: `core/coordinators/main_window_coordinator.py`

**主要方法**:

```python
# 显示各种对话框
coordinator.show_settings_dialog()
coordinator.show_node_manager_dialog()
coordinator.show_cloud_api_dialog()
coordinator.show_indicator_market_dialog()

# 执行优化操作
coordinator.run_one_click_optimization()
coordinator.run_smart_optimization()
coordinator.show_optimization_dashboard()

# 数据质量检查
coordinator.check_single_stock_quality()
coordinator.check_all_stocks_quality()
```

## 功能模块详解

### 1. 分析系统

#### 形态识别 (Pattern Recognition)

**位置**: `analysis/pattern_recognition.py`

**支持的形态** (67种):
- 反转形态：头肩顶/底、双顶/底、三重顶/底等
- 持续形态：三角形、矩形、楔形等
- K线形态：锤子线、十字星、吞噬形态等

**基本用法**:

```python
from analysis.pattern_recognition import PatternRecognizer

# 创建识别器
recognizer = PatternRecognizer()

# 识别形态
patterns = recognizer.recognize_patterns(kdata, pattern_types=['head_shoulders', 'double_top'])

# 获取识别结果
for pattern in patterns:
    print(f"形态: {pattern.name}, 置信度: {pattern.confidence}")
```

#### 技术分析 (Technical Analysis)

**位置**: `analysis/technical_analysis.py`

**支持的指标**:
- 趋势指标：MA、EMA、MACD、KDJ等
- 震荡指标：RSI、CCI、威廉指标等
- 成交量指标：OBV、VRSI等

**基本用法**:

```python
from analysis.technical_analysis import TechnicalAnalyzer

# 创建分析器
analyzer = TechnicalAnalyzer()

# 计算技术指标
indicators = analyzer.calculate_indicators(kdata, ['ma', 'rsi', 'macd'])

# 生成交易信号
signals = analyzer.generate_signals(kdata, indicators)
```

### 2. 优化系统

#### 算法优化器 (Algorithm Optimizer)

**位置**: `optimization/algorithm_optimizer.py`

**支持的优化算法**:
- 遗传算法 (Genetic Algorithm)
- 贝叶斯优化 (Bayesian Optimization)
- 随机搜索 (Random Search)
- 梯度优化 (Gradient Optimization)

**基本用法**:

```python
from optimization.algorithm_optimizer import AlgorithmOptimizer, OptimizationConfig

# 创建优化器
optimizer = AlgorithmOptimizer()

# 配置优化参数
config = OptimizationConfig(
    algorithm='genetic',
    max_iterations=100,
    population_size=50
)

# 执行优化
result = optimizer.optimize_pattern('head_shoulders', config)
print(f"优化结果: {result.best_params}")
```

#### 自动调优器 (Auto Tuner)

**位置**: `optimization/auto_tuner.py`

**功能特性**:
- 一键优化：批量优化所有形态
- 智能优化：自动识别需要优化的形态
- 并行处理：多线程并发优化
- 进度监控：实时显示优化进度

**基本用法**:

```python
from optimization.auto_tuner import AutoTuner

# 创建调优器
tuner = AutoTuner(max_workers=4)

# 添加优化任务
tuner.add_task('head_shoulders', priority=1)
tuner.add_task('double_top', priority=2)

# 执行批量优化
results = tuner.run_batch_optimization()

# 获取优化状态
status = tuner.get_optimization_status()
```

#### 版本管理器 (Version Manager)

**位置**: `optimization/version_manager.py`

**功能特性**:
- Git-like版本控制
- 自动版本保存
- 版本比较和回滚
- 性能历史追踪

**基本用法**:

```python
from optimization.version_manager import VersionManager

# 创建版本管理器
vm = VersionManager()

# 保存新版本
version_id = vm.save_version('head_shoulders', new_params, performance_metrics)

# 获取版本历史
history = vm.get_version_history('head_shoulders')

# 回滚到指定版本
vm.activate_version('head_shoulders', version_id)
```

### 3. 分布式系统

#### 分布式服务 (Distributed Service)

**位置**: `core/services/distributed_service.py`

**功能特性**:
- 节点自动发现
- 任务智能调度
- 负载均衡
- 故障恢复

**基本用法**:

```python
from core.services.distributed_service import DistributedService

# 创建分布式服务
service = DistributedService(discovery_port=8888)

# 启动服务
service.start_service()

# 提交任务
task_id = service.submit_analysis_task('000001', 'technical')
task_id = service.submit_backtest_task('000001', 'ma_cross')
task_id = service.submit_optimization_task('head_shoulders')

# 获取任务状态
task = service.get_task_status(task_id)
print(f"任务状态: {task.status}")

# 获取节点信息
nodes = service.get_nodes_info()
```

#### 节点管理 (Node Management)

**UI入口**: 菜单 -> 工具 -> 节点管理器

**功能特性**:
- 节点发现和注册
- 节点状态监控
- 手动添加节点
- 节点性能统计

### 4. 云端集成

#### 云端API服务 (Cloud API Service)

**位置**: `core/services/cloud_api_service.py`

**功能特性**:
- 安全认证（HMAC-SHA256）
- 自动重试机制
- 数据同步
- 配置管理

**基本用法**:

```python
from core.services.cloud_api_service import CloudAPIService, CloudConfig

# 配置云端服务
config = CloudConfig(
    api_url='https://api.FactorWeave-Quant ‌.com',
    api_key='your_api_key',
    secret_key='your_secret_key'
)

# 创建服务
service = CloudAPIService(config)

# 启动服务
service.start_service()

# 测试连接
connected = service.test_connection()

# 获取服务信息
info = service.get_service_info()
```

#### 云端同步 (Cloud Sync)

**UI入口**: 菜单 -> 工具 -> 云端API管理

**功能特性**:
- 配置同步
- 策略同步
- 指标同步
- 自动同步

### 5. 插件系统

#### 插件管理器 (Plugin Manager)

**位置**: `core/plugin_manager.py`

**功能特性**:
- 插件加载和卸载
- 依赖管理
- 配置管理
- 性能监控

**基本用法**:

```python
from core.plugin_manager import PluginManager

# 创建插件管理器
pm = PluginManager()

# 加载插件
pm.load_plugin('my_indicator')

# 获取插件信息
plugins = pm.get_loaded_plugins()

# 启用/禁用插件
pm.enable_plugin('my_indicator')
pm.disable_plugin('my_indicator')
```

#### 插件市场 (Plugin Market)

**位置**: `plugins/plugin_market.py`

**UI入口**: 菜单 -> 工具 -> 插件管理器

**功能特性**:
- 在线插件浏览
- 插件安装和卸载
- 插件评分和评论
- 插件上传

**基本用法**:

```python
from plugins.plugin_market import PluginMarket

# 创建插件市场
market = PluginMarket(plugins_dir='./plugins', cache_dir='./cache')

# 搜索插件
plugins, total = market.search_plugins(query='MACD', category='indicators')

# 下载插件
downloader = market.download_plugin(plugin_info)
downloader.start()

# 安装插件
success = market.install_plugin(plugin_file)
```

## UI组件开发

### 1. 对话框开发

#### 基础对话框模板

```python
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("我的对话框")
        self.setModal(True)
        self.resize(600, 400)
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 添加控件
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        
        layout.addWidget(ok_btn)
        layout.addWidget(cancel_btn)
        
    def connect_signals(self):
        """连接信号"""
        pass
```

#### 现有对话框列表

- `AdvancedSearchDialog`: 高级搜索
- `BatchAnalysisDialog`: 批量分析
- `CalculatorDialog`: 计算器
- `CloudApiDialog`: 云端API管理
- `DataExportDialog`: 数据导出
- `NodeManagerDialog`: 节点管理器
- `PluginManagerDialog`: 插件管理器
- `SettingsDialog`: 系统设置

### 2. 面板开发

#### 面板基类

```python
from core.ui.panels.base_panel import BasePanel

class MyPanel(BasePanel):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        
    def setup_ui(self):
        """设置UI - 子类必须实现"""
        pass
        
    def update_content(self, data):
        """更新内容 - 子类可选实现"""
        pass
```

#### 现有面板

- `LeftPanel`: 左侧面板（股票列表、指标管理）
- `MiddlePanel`: 中间面板（图表显示）
- `RightPanel`: 右侧面板（分析结果）
- `BottomPanel`: 底部面板（日志显示）
- `LogPanel`: 日志面板

### 3. 控件开发

#### 自定义控件示例

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal

class StockInfoWidget(QWidget):
    """股票信息控件"""
    
    stock_selected = pyqtSignal(str)  # 股票选择信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        self.name_label = QLabel("股票名称")
        self.code_label = QLabel("股票代码")
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.code_label)
        
    def set_stock_info(self, name, code):
        """设置股票信息"""
        self.name_label.setText(name)
        self.code_label.setText(code)
        self.stock_selected.emit(code)
```

## 数据处理

### 1. 数据服务 (Data Service)

**位置**: `core/services/data_service.py`

**功能特性**:
- 多数据源支持
- 数据缓存
- 数据验证
- 异步加载

**基本用法**:

```python
from core.services.data_service import DataService

# 创建数据服务
data_service = DataService()

# 获取K线数据
kdata = data_service.get_kdata('000001', period='day', count=100)

# 获取股票列表
stock_list = data_service.get_stock_list(market='sh')

# 获取实时数据
realtime_data = data_service.get_realtime_data(['000001', '000002'])
```

### 2. 数据验证器 (Data Validator)

**位置**: `core/data_validator.py`

**验证规则**:
- 数据完整性检查
- 数据一致性验证
- 异常值检测
- 缺失值处理

**基本用法**:

```python
from core.data_validator import DataValidator

# 创建验证器
validator = DataValidator()

# 验证K线数据
result = validator.validate_kdata(kdata)

if result.is_valid:
    print("数据验证通过")
else:
    print(f"数据验证失败: {result.errors}")
```

## 配置管理

### 1. 配置管理器 (Config Manager)

**位置**: `utils/config_manager.py`

**配置文件位置**:
- 主配置: `config/config.json`
- 主题配置: `config/theme.json`
- 插件配置: `config/plugins/`

**基本用法**:

```python
from utils.config_manager import ConfigManager

# 创建配置管理器
config = ConfigManager()

# 获取配置
value = config.get('ui.theme', default='dark')

# 设置配置
config.set('ui.theme', 'light')

# 保存配置
config.save()
```

### 2. 主题管理

**支持的主题**:
- 深色主题 (dark)
- 浅色主题 (light)
- 自定义主题

**主题文件格式**:

```json
{
    "name": "深色主题",
    "colors": {
        "background": "#2b2b2b",
        "foreground": "#ffffff",
        "accent": "#007acc"
    },
    "fonts": {
        "default": "Microsoft YaHei",
        "code": "Consolas"
    }
}
```

## 测试指南

### 1. 单元测试

**测试框架**: pytest

**测试目录**: `test/`

**运行测试**:

```bash
# 运行所有测试
python -m pytest test/

# 运行特定测试
python -m pytest test/test_pattern_recognition.py

# 生成覆盖率报告
python -m pytest --cov=analysis test/
```

### 2. 集成测试

**集成测试脚本**:
- `test_ui_integration.py`: UI集成测试
- `test_complete_features.py`: 功能完整性测试
- `test_enhanced_features.py`: 增强功能测试

**运行集成测试**:

```bash
python test_ui_integration.py
```

### 3. 性能测试

**性能测试工具**:
- 内存使用监控
- 执行时间测量
- 并发性能测试

**基本用法**:

```python
from core.performance_monitor import PerformanceMonitor

# 创建性能监控器
monitor = PerformanceMonitor()

# 开始监控
monitor.start_monitoring()

# 执行业务逻辑
# ...

# 获取性能报告
report = monitor.get_performance_report()
```

## 部署指南

### 1. 环境要求

**Python版本**: 3.11+

**依赖包**:
```bash
pip install -r requirements.txt
```

**系统要求**:
- Windows 10/11
- 内存: 8GB+
- 硬盘: 10GB+

### 2. 安装步骤

1. **克隆项目**:
```bash
git clone https://github.com/your-repo/FactorWeave-Quant ‌.git
cd FactorWeave-Quant ‌
```

2. **安装依赖**:
```bash
python install_dependencies.py
```

3. **初始化数据库**:
```bash
python db/init_db.py
```

4. **启动应用**:
```bash
python main.py
```

### 3. 配置说明

**数据源配置**:
```json
{
    "data_sources": {
        "primary": "FactorWeave-Quant",
        "fallback": ["akshare", "tushare"]
    }
}
```

**性能配置**:
```json
{
    "performance": {
        "cache_size": 1000,
        "thread_pool_size": 8,
        "memory_limit": "4GB"
    }
}
```

## 开发最佳实践

### 1. 代码规范

**遵循PEP 8**:
- 使用4个空格缩进
- 行长度不超过88字符
- 类名使用PascalCase
- 函数名使用snake_case

**类型提示**:
```python
from typing import List, Dict, Optional

def process_data(data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """处理数据"""
    pass
```

**文档字符串**:
```python
def calculate_indicators(self, kdata: pd.DataFrame, indicators: List[str]) -> Dict[str, pd.Series]:
    """
    计算技术指标
    
    Args:
        kdata: K线数据
        indicators: 指标列表
        
    Returns:
        指标计算结果
        
    Raises:
        ValueError: 当指标名称无效时
    """
    pass
```

### 2. 错误处理

**使用自定义异常**:
```python
class FactorWeave-QuantUIException(Exception):
    """FactorWeave-Quant ‌基础异常"""
    pass

class DataValidationError(FactorWeave-QuantUIException):
    """数据验证错误"""
    pass
```

**异常处理模式**:
```python
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"操作失败: {e}")
    # 处理特定异常
except Exception as e:
    logger.error(f"未知错误: {e}")
    # 处理通用异常
finally:
    # 清理资源
    cleanup()
```

### 3. 日志记录

**日志配置**:
```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

**日志使用**:
```python
logger.info("开始处理数据")
logger.warning("数据质量较差")
logger.error("处理失败", exc_info=True)
```

### 4. 性能优化

**缓存策略**:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(param):
    """昂贵的计算操作"""
    pass
```

**异步处理**:
```python
import asyncio

async def async_data_processing():
    """异步数据处理"""
    tasks = [process_chunk(chunk) for chunk in data_chunks]
    results = await asyncio.gather(*tasks)
    return results
```

## API参考

### 1. 核心API

#### ServiceContainer

```python
class ServiceContainer:
    def register(self, name: str, service_class: type, singleton: bool = False) -> None
    def get_service(self, name: str) -> Any
    def has_service(self, name: str) -> bool
    def remove_service(self, name: str) -> None
```

#### EventBus

```python
class EventBus:
    def subscribe(self, event_type: str, handler: Callable) -> None
    def unsubscribe(self, event_type: str, handler: Callable) -> None
    def publish(self, event_type: str, data: Any) -> None
```

### 2. 分析API

#### PatternRecognizer

```python
class PatternRecognizer:
    def recognize_patterns(self, kdata: pd.DataFrame, pattern_types: List[str] = None) -> List[Pattern]
    def get_available_patterns(self) -> List[str]
    def get_pattern_confidence(self, pattern: Pattern) -> float
```

#### TechnicalAnalyzer

```python
class TechnicalAnalyzer:
    def calculate_indicators(self, kdata: pd.DataFrame, indicators: List[str]) -> Dict[str, pd.Series]
    def generate_signals(self, kdata: pd.DataFrame, indicators: Dict[str, pd.Series]) -> List[Signal]
    def get_available_indicators(self) -> List[str]
```

### 3. 优化API

#### AlgorithmOptimizer

```python
class AlgorithmOptimizer:
    def optimize_pattern(self, pattern_name: str, config: OptimizationConfig) -> OptimizationResult
    def get_optimization_history(self, pattern_name: str) -> List[OptimizationResult]
    def cancel_optimization(self, optimization_id: str) -> bool
```

#### AutoTuner

```python
class AutoTuner:
    def add_task(self, pattern_name: str, priority: int = 5) -> None
    def run_batch_optimization(self) -> List[Dict[str, Any]]
    def get_optimization_status(self) -> Dict[str, Any]
```

## 常见问题

### 1. 安装问题

**Q: 依赖安装失败**
A: 检查Python版本是否为3.11+，使用以下命令：
```bash
python --version
pip install --upgrade pip
pip install -r requirements.txt
```

**Q: FactorWeave-Quant安装失败**
A: FactorWeave-Quant需要特定的编译环境，请参考FactorWeave-Quant官方文档。

### 2. 运行问题

**Q: 界面无法显示**
A: 检查PyQt5是否正确安装：
```bash
pip install PyQt5
```

**Q: 数据获取失败**
A: 检查网络连接和数据源配置，确保API密钥有效。

### 3. 性能问题

**Q: 分析速度慢**
A: 
- 检查缓存设置
- 增加线程池大小
- 使用分布式计算

**Q: 内存占用过高**
A:
- 减少缓存大小
- 启用数据压缩
- 使用内存映射文件

## 更新日志

### v2.0.0 (2024-01-XX)

**新增功能**:
- 模块化架构重构
- 分布式计算支持
- 云端API集成
- 插件市场系统
- 67种形态识别算法
- AI驱动的参数优化

**改进功能**:
- 性能优化（提升5-10倍）
- UI响应速度优化
- 内存使用优化
- 错误处理改进

**修复问题**:
- 数据同步问题
- 界面卡顿问题
- 内存泄漏问题

## 贡献指南

### 1. 开发流程

1. Fork项目
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request

### 2. 代码审查

- 代码规范检查
- 单元测试覆盖率
- 性能影响评估
- 文档完整性

### 3. 发布流程

1. 版本号更新
2. 更新日志编写
3. 文档更新
4. 测试验证
5. 正式发布

## 联系方式

- **项目主页**: https://github.com/your-repo/FactorWeave-Quant ‌
- **文档网站**: https://docs.FactorWeave-Quant ‌.com
- **问题反馈**: https://github.com/your-repo/FactorWeave-Quant ‌/issues
- **讨论社区**: https://community.FactorWeave-Quant ‌.com

---

**版权声明**: 本文档遵循 MIT 许可证，详见 LICENSE 文件。

## 异步环境下日志与性能监控最佳实践

### 1. 异步任务日志上下文与异常捕获
- 在async/await、线程池、QThread等异步环境中，日志应包含trace_id、request_id等上下文信息，便于跨线程追踪。
- 异步任务中所有异常必须被try...except捕获，并通过logger.error记录详细堆栈。

**示例：**
```python
import asyncio
import logging

logger = logging.getLogger(__name__)

async def async_task(trace_id=None):
    try:
        # ... 异步逻辑 ...
        logger.info(f"[trace_id={trace_id}] 异步任务开始")
        await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"[trace_id={trace_id}] 异步任务异常: {e}", exc_info=True)

# 调用时传递trace_id
asyncio.run(async_task(trace_id="abc123"))
```

### 2. 异步函数性能监控装饰器用法
- 推荐在所有高耗时异步函数、回调、数据处理等环节加性能监控装饰器。
- 支持同步与异步函数的统一监控。

**示例：**
```python
from utils.performance_monitor import measure_performance

@measure_performance("async_data_load")
async def load_data_async():
    # ... 异步数据加载 ...
    pass
```

### 3. 主线程与异步线程日志合并与追踪ID设计
- 日志格式建议统一包含trace_id、request_id等字段。
- 日志处理器可用logging.Filter或上下文变量自动注入追踪信息。
- 合并日志时可用多文件Handler或集中式日志系统。

**示例：**
```python
import logging
import contextvars

trace_id_var = contextvars.ContextVar('trace_id', default='')

class TraceIdFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = trace_id_var.get()
        return True

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s [trace_id=%(trace_id)s] %(message)s')
handler.setFormatter(formatter)
handler.addFilter(TraceIdFilter())
logger.addHandler(handler)

# 在主线程和异步任务中设置trace_id
trace_id_var.set('main-xyz')
logger.info('主线程日志')

async def async_func():
    trace_id_var.set('async-abc')
    logger.info('异步日志')
```

### 4. 典型问题与建议
- 避免在主线程直接执行耗时操作，所有IO/计算密集型任务应异步或线程池处理。
- 异步回调/信号中如需UI更新，务必用QMetaObject.invokeMethod或QTimer.singleShot切回主线程。
- 日志与性能监控建议定期归档、分析，发现瓶颈及时优化。

---

如需更多异步编程、日志与性能监控的最佳实践，请参考[Python官方文档](https://docs.python.org/3/howto/logging-cookbook.html)和[asyncio官方文档](https://docs.python.org/3/library/asyncio.html)。