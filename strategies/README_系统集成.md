# 策略系统集成指南

## 概述

本文档说明如何将20字段标准策略集成到FactorWeave-Quant系统中，使用户可以直接在UI中使用策略功能。

---

## 📁 已创建的文件

### 1. 策略管理器 (`strategies/strategy_manager.py`)

**功能**:
- 策略注册和管理
- 统一的策略执行接口
- 策略回测功能
- 单例模式设计

**内置策略**:
1. `adj_momentum` - 复权价格动量策略
2. `vwap_reversion` - VWAP均值回归策略

**使用示例**:
```python
from strategies.strategy_manager import get_strategy_manager

# 获取管理器实例
manager = get_strategy_manager()

# 列出所有策略
strategies = manager.list_strategies()

# 执行策略
results = manager.execute_strategy(
    strategy_id='adj_momentum',
    symbols=['000001', '600519'],
    lookback_period=20,
    top_n=10
)

# 策略回测
backtest_results = manager.backtest_strategy(
    strategy_id='vwap_reversion',
    symbols=['000001'],
    deviation_threshold=0.02
)
```

### 2. 策略UI组件 (`gui/widgets/strategy_widget.py`)

**功能**:
- 策略选择下拉列表
- 动态参数配置界面
- 策略执行按钮
- 结果表格显示
- 回测功能

**UI组件**:
```
┌─────────────────────────────────────────┐
│ 策略配置                                 │
│  选择策略: [复权价格动量策略 ▼]          │
│  描述: 使用复权价格计算真实动量...        │
│  股票列表: [000001,600519,000858]        │
│  参数:                                   │
│    Lookback Period: [20]                │
│    Top N: [10]                          │
│  [执行策略] [策略回测]                   │
├─────────────────────────────────────────┤
│ 策略结果                                 │
│  股票代码 │ 信号数量 │ 买入 │ 卖出 │...   │
│  ────────┼─────────┼─────┼─────┼──── │
│  000001   │   365    │  12  │  8   │...   │
│  600519   │   365    │  15  │  10  │...   │
├─────────────────────────────────────────┤
│ 执行日志:                                │
│  正在执行策略: 复权价格动量策略...        │
│  ✅ 策略执行完成！                        │
└─────────────────────────────────────────┘
```

---

## 🔌 集成步骤

### 方案1: 作为独立Tab页集成到主窗口

**步骤**:

1. **在主窗口中导入策略组件**

```python
# 在 main.py 或主窗口文件中
from gui.widgets.strategy_widget import StrategyWidget
```

2. **添加策略Tab页**

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        # ... 其他初始化代码 ...
        
        # 创建主Tab控件
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # 添加策略Tab
        self.strategy_widget = StrategyWidget(self)
        self.tab_widget.addTab(self.strategy_widget, "策略执行")
        
        # 连接信号
        self.strategy_widget.strategy_executed.connect(self._on_strategy_executed)
    
    def _on_strategy_executed(self, result_data):
        """策略执行完成回调"""
        logger.info(f"策略执行完成: {result_data}")
        # 可以在这里处理策略执行结果，例如显示图表
```

### 方案2: 作为独立窗口

```python
# 在主窗口添加菜单或按钮
def show_strategy_window(self):
    """显示策略窗口"""
    from gui.widgets.strategy_widget import StrategyWidget
    
    if not hasattr(self, 'strategy_window'):
        self.strategy_window = StrategyWidget()
        self.strategy_window.setWindowTitle("FactorWeave-Quant 策略执行")
        self.strategy_window.resize(1000, 700)
    
    self.strategy_window.show()
    self.strategy_window.raise_()
```

### 方案3: 集成到现有的回测模块

```python
# 在 gui/widgets/backtest_widget.py 中
from strategies.strategy_manager import get_strategy_manager

class BacktestWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.strategy_manager = get_strategy_manager()
        # ... 其他初始化代码 ...
    
    def add_strategy_selection(self):
        """添加策略选择功能"""
        strategies = self.strategy_manager.list_strategies()
        
        strategy_combo = QComboBox()
        for strategy_info in strategies:
            strategy_combo.addItem(
                strategy_info['name'],
                strategy_info['id']
            )
        
        # 添加到回测界面
        self.layout.addWidget(QLabel("选择策略:"))
        self.layout.addWidget(strategy_combo)
```

---

## 🎨 UI集成示例（完整代码）

### 方法1: 修改 `main.py`

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主程序入口
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt5.QtCore import Qt

# 导入各个功能模块
from gui.widgets.strategy_widget import StrategyWidget
# ... 其他导入 ...

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FactorWeave-Quant 量化交易系统 V2.0.4")
        self.resize(1400, 900)
        
        # 创建Tab控件
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # 添加各个功能模块
        self._init_tabs()
    
    def _init_tabs(self):
        """初始化Tab页"""
        # 策略执行模块 🆕
        self.strategy_widget = StrategyWidget(self)
        self.tab_widget.addTab(self.strategy_widget, "📊 策略执行")
        
        # ... 其他Tab页 ...
        # self.tab_widget.addTab(self.data_import_widget, "数据导入")
        # self.tab_widget.addTab(self.backtest_widget, "回测分析")
        # self.tab_widget.addTab(self.chart_widget, "图表分析")


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("FactorWeave-Quant")
    app.setApplicationVersion("V2.0.4")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
```

---

## 🔧 策略扩展

### 添加自定义策略

**步骤1**: 创建策略类

```python
# strategies/my_custom_strategy.py

from strategies.strategy_manager import StrategyBase
import pandas as pd

class MyCustomStrategy(StrategyBase):
    """我的自定义策略"""
    
    def __init__(self):
        super().__init__(
            name="我的动量策略",
            description="自定义的动量策略"
        )
        self.parameters = {
            'period': 10,
            'threshold': 0.05
        }
    
    def get_required_fields(self):
        return ['adj_close', 'volume', 'datetime', 'symbol']
    
    def generate_signals(self, data):
        if not self.validate_data(data):
            return pd.DataFrame()
        
        period = self.parameters.get('period', 10)
        threshold = self.parameters.get('threshold', 0.05)
        
        # 计算动量
        data['momentum'] = data['adj_close'].pct_change(period)
        
        # 生成信号
        data['buy_signal'] = (data['momentum'] > threshold).astype(int)
        data['sell_signal'] = (data['momentum'] < -threshold).astype(int)
        
        return data
```

**步骤2**: 注册策略

```python
# 方法1: 在 strategy_manager.py 中注册
def _register_builtin_strategies(self):
    # 现有策略
    self.register_strategy('adj_momentum', AdjPriceMomentumStrategy())
    self.register_strategy('vwap_reversion', VWAPMeanReversionStrategy())
    
    # 新增自定义策略
    from strategies.my_custom_strategy import MyCustomStrategy
    self.register_strategy('my_custom', MyCustomStrategy())

# 方法2: 动态注册
manager = get_strategy_manager()
manager.register_strategy('my_custom', MyCustomStrategy())
```

---

## 📊 数据流说明

```
┌──────────────┐
│ 用户操作UI   │
│  - 选择策略  │
│  - 配置参数  │
│  - 执行策略  │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  StrategyWidget   │ (GUI层)
│  - 参数收集       │
│  - 结果展示       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ StrategyManager   │ (业务逻辑层)
│  - 策略路由       │
│  - 参数管理       │
│  - 回测计算       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  StrategyBase     │ (策略层)
│  - 信号生成       │
│  - 数据验证       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ UnifiedDataManager│ (数据层)
│  - K线数据获取    │
│  - 20字段标准     │
└──────────────────┘
```

---

## ✅ 验证测试

### 测试步骤

1. **启动应用**
```bash
python main.py
```

2. **选择策略Tab页**

3. **测试复权动量策略**
   - 选择策略: "复权价格动量策略"
   - 输入股票: "000001,600519"
   - 设置参数: lookback_period=20, top_n=2
   - 点击"执行策略"
   - 查看结果表格

4. **测试VWAP策略**
   - 选择策略: "VWAP均值回归策略"
   - 输入股票: "000001"
   - 设置参数: deviation_threshold=0.02
   - 点击"策略回测"
   - 查看回测结果

### 预期结果

```
执行日志:
正在执行策略: 复权价格动量策略
股票列表: ['000001', '600519']
策略参数: {'lookback_period': 20, 'top_n': 2}
✅ 策略执行完成！成功: 2/2

结果表格:
股票代码 │ 信号数量 │ 买入信号 │ 卖出信号 │ 最新信号 │ 信号时间
────────┼─────────┼─────────┼─────────┼─────────┼──────────
000001   │   365    │    12    │    0     │   买入   │ 2025-10-11
600519   │   365    │    15    │    0     │   买入   │ 2025-10-11
```

---

## 🎯 功能特点

### ✅ 已实现

1. **策略管理**
   - 内置2个专业策略
   - 单例模式管理器
   - 策略注册机制

2. **UI集成**
   - 策略选择下拉菜单
   - 动态参数配置
   - 结果表格展示
   - 执行日志显示

3. **数据集成**
   - 使用UnifiedDataManager
   - 支持20字段标准
   - 自动数据验证

4. **回测功能**
   - 简单回测逻辑
   - 收益率计算
   - 胜率统计

### 🔄 可扩展

1. **策略扩展**
   - 支持自定义策略
   - 继承StrategyBase
   - 动态注册

2. **UI扩展**
   - 可集成到现有模块
   - 支持独立窗口
   - Tab页集成

3. **功能扩展**
   - 更复杂的回测逻辑
   - 图表可视化
   - 实盘交易接口

---

## 📝 注意事项

### 1. 数据依赖

策略执行需要数据库中有K线数据，确保：
- 数据库已初始化
- 已导入目标股票的K线数据
- 数据包含策略需要的字段（adj_close, vwap等）

### 2. 性能考虑

- 大量股票执行策略可能耗时较长
- 建议使用异步执行（后续可优化）
- 回测数据量大时注意内存占用

### 3. 错误处理

- 策略执行失败不会影响其他股票
- UI会显示详细错误信息
- 日志记录所有执行过程

---

## 📚 相关文档

- [K线表20字段升级完成报告](../K线表20字段升级完成报告.md)
- [策略示例README](../examples/strategies/README_策略示例.md)
- [复权价格动量策略源码](../examples/strategies/adj_price_momentum_strategy.py)
- [VWAP均值回归策略源码](../examples/strategies/vwap_mean_reversion_strategy.py)

---

## 🤝 贡献

欢迎贡献新的策略或UI改进！

**贡献方式**:
1. Fork项目
2. 创建新策略类
3. 提交Pull Request
4. 更新文档

---

**最后更新**: 2025-10-12  
**版本**: V2.0.4  
**作者**: FactorWeave-Quant Team

