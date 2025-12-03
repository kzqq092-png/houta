# HIkyuu 移除替换计划

## 🔄 替换策略

### 1. 技术指标替代

| HIkyuu 指标 | TA-Lib 替代 | Pandas-TA 替代 | 
|-------------|-------------|----------------|
| MA          | SMA         | ta.sma()       |
| EMA         | EMA         | ta.ema()       |
| MACD        | MACD        | ta.macd()      |
| RSI         | RSI         | ta.rsi()       |
| BOLL        | BBANDS      | ta.bbands()   |
| KDJ         | STOCH       | ta.stoch()     |
| CCI         | CCI         | ta.cci()       |
| ATR         | ATR         | ta.atr()       |
| OBV         | OBV         | ta.obv()       |

### 2. 核心替换文件

#### 替换 `core/signal/base.py`
```python
# 移除 hikyuu 依赖
import numpy as np
import pandas as pd
from typing import List, Dict, Any

# 替代技术指标库
import talib
import pandas_ta as ta
```

#### 替换 `plugins/indicators/hikyuu_indicators_plugin.py`
```python
# 使用 TA-Lib + Pandas-TA 作为后端
import talib
import pandas_ta as ta

class AlternativeIndicatorsPlugin:
    def __init__(self):
        self.backends = ['talib', 'pandas-ta']
    
    def calculate_indicator(self, name, data, params):
        if name.upper() == 'MA':
            return talib.SMA(data['close'], timeperiod=params.get('period', 20))
        elif name.upper() == 'RSI':
            return talib.RSI(data['close'], timeperiod=params.get('period', 14))
        # ... 其他指标
```

### 3. 策略系统替换

#### 替换 `plugins/strategies/hikyuu_strategy_plugin.py`
```python
# 使用通用策略框架替代
import backtrader as bt

class UniversalStrategy(bt.Strategy):
    def __init__(self):
        # 使用 talib 计算指标
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=20
        )
    
    def next(self):
        if self.data.close[0] > self.sma[0]:
            self.buy()
        else:
            self.sell()
```

### 4. 移除步骤

#### 步骤 1: 更新 requirements.txt
```diff
- hikyuu>=2.5.6
+ talib>=0.4.28
+ pandas-ta>=0.3.14b0
```

#### 步骤 2: 替换核心文件
- [ ] `core/signal/base.py` → `core/signal/talib_adapter.py`
- [ ] `core/signal/enhanced.py` → `core/signal/enhanced_talib.py` 
- [ ] `plugins/indicators/hikyuu_indicators_plugin.py` → `plugins/indicators/talib_indicators_plugin.py`
- [ ] `plugins/strategies/hikyuu_strategy_plugin.py` → `plugins/strategies/universal_strategy_plugin.py`

#### 步骤 3: 更新导入
```python
# 在相关文件中替换导入
- from hikyuu import *
- from hikyuu.indicator import MA, MACD, RSI
+ import talib
+ import pandas_ta as ta
```

### 5. 风险评估

#### 🔴 高风险模块
- 交易系统核心逻辑
- 策略回测引擎
- 复杂的信号生成算法

#### 🟡 中风险模块
- 技术指标计算
- 数据处理逻辑
- 可视化功能

#### 🟢 低风险模块
- 配置管理
- 日志系统
- UI 界面

### 6. 迁移时间预估

| 模块 | 复杂程度 | 预估时间 | 风险等级 |
|------|----------|----------|----------|
| 技术指标替换 | 中等 | 2-3天 | 低 |
| 策略系统重构 | 高 | 1-2周 | 高 |
| 交易系统适配 | 高 | 1-2周 | 高 |
| 测试验证 | 中等 | 3-5天 | 中 |

## 💡 建议

**推荐方案**: 方案1（修复安装）+ 方案2（逐步替换）
1. 先尝试修复 hikyuu 安装
2. 同时准备替换方案作为备选
3. 按模块逐步迁移，降低风险