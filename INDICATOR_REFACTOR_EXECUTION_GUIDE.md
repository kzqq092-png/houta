# Hikyuu-UI 指标系统重构执行指南

## 1. 背景介绍

Hikyuu-UI项目的指标系统重构旨在将系统从当前的混合实现，迁移至一个统一、动态、数据库驱动的全新架构。目前已经完成了基础设施建设阶段，包括数据库设计、算法库实现、核心服务和适配器实现。本指南将帮助您完成剩余的重构工作。

### 已完成部分

- **数据库设计与初始化**：`db/indicators.db`、`db/initialize_indicators.py`、`db/models/indicator_models.py`
- **指标算法库**：`core/indicators/library/`下的各个模块
- **核心服务**：`core/indicator_service.py`
- **指标适配器**：`core/indicator_adapter.py`
- **测试与示例**：`test/test_indicators_system.py`、`test/test_new_indicator_system.py`、`examples/indicator_system_demo.py`

### 待完成部分

- **UI层集成**：更新UI组件，使用新的指标计算服务
- **核心逻辑层迁移**：更新业务代码，使用新的指标计算服务
- **旧代码清理**：安全删除不再需要的旧文件
- **插件系统实现**：完成指标注册功能

## 2. 环境准备

1. **确保开发环境已经安装了所有必要的依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **确保指标数据库已经初始化**：
   ```bash
   python db/initialize_indicators.py
   ```

3. **检查指标数据库是否正常**：
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('db/indicators.db'); print(conn.execute('SELECT name FROM indicators').fetchall()); conn.close()"
   ```

## 3. 测试运行

1. **运行现有测试，确保基础设施正常工作**：
   ```bash
   python -m unittest test/test_new_indicator_system.py
   ```

2. **运行示例代码，确保指标计算服务正常工作**：
   ```bash
   python examples/indicator_system_demo.py
   ```

## 4. 自动化迁移

### 4.1 UI层迁移

1. **下载自动化迁移脚本**：
   ```bash
   curl -O https://raw.githubusercontent.com/your-repo/update_ui_indicator_references.py
   ```

2. **运行UI层迁移脚本**：
   ```bash
   python update_ui_indicator_references.py
   ```

3. **检查迁移日志**：
   ```bash
   cat ui_migration.log
   ```

### 4.2 核心逻辑层迁移

1. **下载自动化迁移脚本**：
   ```bash
   curl -O https://raw.githubusercontent.com/your-repo/update_core_indicator_references.py
   ```

2. **运行核心逻辑层迁移脚本**：
   ```bash
   python update_core_indicator_references.py
   ```

3. **检查迁移日志**：
   ```bash
   cat core_migration.log
   ```

## 5. 手动调整

对于自动化脚本无法处理的复杂情况，需要进行手动调整。以下是一些常见的情况和解决方法：

### 5.1 复杂计算逻辑

对于包含复杂计算逻辑的代码，需要将其重构为使用`IndicatorService`：

```python
# 旧代码
def analyze_stock(df):
    ma5 = calc_ma(df['close'], 5)
    ma10 = calc_ma(df['close'], 10)
    result = (ma5 > ma10).astype(int)
    return result

# 新代码
def analyze_stock(df):
    from core.indicator_service import calculate_indicator
    
    # 计算MA5
    df_ma5 = calculate_indicator('MA', df, {'timeperiod': 5})
    
    # 计算MA10
    df_ma10 = calculate_indicator('MA', df, {'timeperiod': 10})
    
    # 比较结果
    result = (df_ma5['MA'] > df_ma10['MA']).astype(int)
    return result
```

### 5.2 自定义指标

对于自定义指标，需要将其添加到指标数据库中：

```python
from db.models.indicator_models import (
    IndicatorDatabase,
    Indicator,
    IndicatorParameter,
    IndicatorImplementation
)

def add_custom_indicator():
    db = IndicatorDatabase('db/indicators.db')
    
    # 创建自定义指标
    custom_indicator = Indicator(
        id=None,  # 自动分配ID
        name='MY_CUSTOM_INDICATOR',
        display_name='我的自定义指标',
        category_id=6,  # 其他类别
        description='这是一个自定义指标',
        formula='自定义公式',
        parameters=[
            IndicatorParameter(
                name='param1',
                description='参数1',
                type='int',
                default_value=10
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='custom',
                function_name='my_module.calculate_custom_indicator',
                is_default=True
            )
        ],
        output_names=['CustomIndicator']
    )
    
    # 添加到数据库
    db.add_indicator(custom_indicator)
    db.close()
```

## 6. 测试验证

1. **运行单元测试**：
   ```bash
   python -m unittest discover test
   ```

2. **运行集成测试**：
   ```bash
   python -m unittest test/test_integration.py
   ```

3. **手动测试UI功能**：
   - 启动应用程序
   - 测试指标配置对话框
   - 测试图表指标显示
   - 测试股票筛选功能

## 7. 清理旧代码

1. **下载依赖检查脚本**：
   ```bash
   curl -O https://raw.githubusercontent.com/your-repo/check_dependencies_and_cleanup.py
   ```

2. **运行依赖检查脚本**：
   ```bash
   python check_dependencies_and_cleanup.py --check-only
   ```

3. **检查依赖报告**：
   ```bash
   cat dependencies_report.txt
   ```

4. **如果确认所有依赖都已经被替换，运行清理脚本**：
   ```bash
   python check_dependencies_and_cleanup.py --cleanup
   ```

5. **要删除的文件**：
   - `indicators_algo.py`
   - `features/basic_indicators.py`
   - `features/advanced_indicators.py`
   - `features/__init__.py`（如果该文件已无其他内容）

## 8. 插件系统实现

### 8.1 更新`IndicatorService`

1. **编辑`core/indicator_service.py`，添加`register_indicators()`方法**：

```python
def register_indicators(self, indicators_list: List[Dict], source: str) -> List[int]:
    """
    注册指标列表
    
    参数:
        indicators_list: 指标定义列表
        source: 指标来源
        
    返回:
        List[int]: 新增指标的ID列表
    """
    indicator_ids = []
    
    for indicator_dict in indicators_list:
        # 创建指标对象
        indicator = Indicator.from_dict(indicator_dict)
        indicator.is_builtin = False  # 插件指标不是内置的
        
        # 添加到数据库
        indicator_id = self.db.add_indicator(indicator)
        indicator_ids.append(indicator_id)
        
    return indicator_ids
```

### 8.2 更新`PluginManager`

1. **编辑`core/plugin_manager.py`，添加加载插件指标的逻辑**：

```python
def load_plugin_indicators(self, plugin_name: str, plugin_module) -> None:
    """
    加载插件指标
    
    参数:
        plugin_name: 插件名称
        plugin_module: 插件模块
    """
    try:
        # 尝试导入plugin_info模块
        plugin_info = importlib.import_module(f"{plugin_module.__name__}.plugin_info")
        
        # 检查是否存在register_indicators函数
        if hasattr(plugin_info, 'register_indicators'):
            # 获取指标列表
            indicators_list = plugin_info.register_indicators()
            
            # 注册指标
            from core.indicator_service import IndicatorService
            indicator_service = IndicatorService()
            indicator_service.register_indicators(indicators_list, plugin_name)
            
            self.logger.info(f"已加载插件 {plugin_name} 的 {len(indicators_list)} 个指标")
    except (ImportError, AttributeError) as e:
        self.logger.debug(f"插件 {plugin_name} 未提供指标: {str(e)}")
```

### 8.3 创建示例插件

1. **创建插件目录**：
   ```bash
   mkdir -p plugins/examples/my_custom_indicator
   ```

2. **创建`plugin_info.py`**：

```python
def register_indicators():
    """
    注册插件指标
    
    返回:
        List[Dict]: 指标定义列表
    """
    return [
        {
            "name": "MY_SENTIMENT",
            "display_name": "情绪指标",
            "category_id": 6,  # 其他类别
            "description": "一个基于价格波动计算市场情绪的指标",
            "formula": "Sentiment = (Close - Open) / Range * 100",
            "parameters": [
                {
                    "name": "timeperiod",
                    "description": "计算周期",
                    "type": "int",
                    "default_value": 14,
                    "min_value": 1,
                    "max_value": 100,
                    "step": 1
                }
            ],
            "implementations": [
                {
                    "engine": "custom",
                    "function_name": "plugins.examples.my_custom_indicator.indicators.calculate_sentiment",
                    "is_default": True
                }
            ],
            "output_names": ["Sentiment"]
        }
    ]
```

3. **创建`indicators.py`**：

```python
import pandas as pd
import numpy as np

def calculate_sentiment(df: pd.DataFrame, timeperiod: int = 14) -> pd.DataFrame:
    """
    计算情绪指标
    
    参数:
        df: 输入DataFrame，包含OHLCV数据
        timeperiod: 计算周期
        
    返回:
        DataFrame: 添加了情绪指标列的DataFrame
    """
    # 复制输入数据
    result = df.copy()
    
    # 计算价格范围
    price_range = df['high'] - df['low']
    
    # 计算价格变化
    price_change = df['close'] - df['open']
    
    # 计算情绪值
    sentiment = price_change / price_range * 100
    
    # 使用移动平均平滑结果
    sentiment = sentiment.rolling(window=timeperiod).mean()
    
    # 添加到结果DataFrame
    result['Sentiment'] = sentiment
    
    return result
```

## 9. 文档更新

### 9.1 更新开发者文档

1. **编辑`docs/developer.rst`，添加指标系统的说明**：

```rst
指标系统
========

Hikyuu-UI的指标系统采用数据库驱动的架构，支持动态加载和计算指标。

指标计算服务
----------

指标计算服务(`IndicatorService`)是指标系统的核心，负责从数据库加载指标定义并进行计算。

.. code-block:: python

   from core.indicator_service import calculate_indicator
   
   # 计算MA指标
   df_ma = calculate_indicator('MA', df, {'timeperiod': 20})
   
   # 计算MACD指标
   df_macd = calculate_indicator('MACD', df, {
       'fastperiod': 12,
       'slowperiod': 26,
       'signalperiod': 9
   })

添加新指标
--------

要添加新指标，可以通过以下两种方式：

1. 直接修改`db/initialize_indicators.py`文件，添加新的指标定义。
2. 通过插件系统注册指标。

插件指标示例
---------

.. code-block:: python

   # plugin_info.py
   def register_indicators():
       return [
           {
               "name": "MY_INDICATOR",
               "display_name": "我的指标",
               "category_id": 1,
               "description": "这是一个示例指标",
               "parameters": [
                   {
                       "name": "param1",
                       "description": "参数1",
                       "type": "int",
                       "default_value": 10
                   }
               ],
               "implementations": [
                   {
                       "engine": "custom",
                       "function_name": "my_plugin.calculate_indicator",
                       "is_default": True
                   }
               ],
               "output_names": ["MyIndicator"]
           }
       ]
```

### 9.2 更新用户文档

1. **编辑`README.md`，添加指标系统的说明**：

```markdown
## 技术指标系统

Hikyuu-UI提供了丰富的技术指标，包括：

- **趋势类指标**：MA、BOLL等
- **震荡类指标**：MACD、RSI、KDJ等
- **成交量类指标**：OBV等
- **波动性类指标**：ATR等
- **形态类指标**：K线形态识别

### 自定义指标

您可以通过插件系统添加自定义指标。详情请参考[插件开发指南](docs/plugin_development.md)。
```

## 10. 总结与验证

完成上述步骤后，您应该已经成功地将指标系统从旧架构迁移到了新架构。以下是验证工作的步骤：

1. **运行所有测试**：
   ```bash
   python -m unittest discover
   ```

2. **启动应用程序**：
   ```bash
   python main.py
   ```

3. **验证功能**：
   - 检查技术分析窗口是否正常显示指标
   - 检查指标配置对话框是否正常工作
   - 检查股票筛选功能是否正常工作
   - 检查插件指标是否正常加载和使用

4. **检查性能**：
   - 比较新旧系统的性能差异
   - 确保新系统不会导致性能下降

如果您在执行过程中遇到任何问题，请参考日志文件或联系开发团队获取帮助。 