# FactorWeave-Quant 策略示例

## 概述

本目录包含基于20字段标准K线数据的量化策略示例，展示如何正确使用新增的专业字段（adj_close, adj_factor, turnover_rate, vwap, data_source）进行策略开发。

---

## 📁 策略列表

### 1. 复权价格动量策略 (`adj_price_momentum_strategy.py`)

**核心逻辑**: 使用复权价格计算真实动量，选择动量最强的股票

**使用字段**:
- ✅ `adj_close` - 复权收盘价（核心）
- ✅ `adj_factor` - 复权因子（验证）
- ✅ `close` - 原始收盘价（对比）

**策略特点**:
- 正确处理除权除息
- 避免虚假的价格跳空
- 分红影响分析

**适用场景**:
- 中长期趋势跟踪
- 动量因子构建
- 多因子模型

**关键代码**:
```python
# ❌ 错误：使用原始价格（除权除息会产生虚假负收益）
returns_wrong = df['close'].pct_change()

# ✅ 正确：使用复权价格
returns_correct = df['adj_close'].pct_change()
```

---

### 2. VWAP均值回归策略 (`vwap_mean_reversion_strategy.py`)

**核心逻辑**: 价格偏离VWAP时进行反向交易，期待均值回归

**使用字段**:
- ✅ `vwap` - 成交量加权均价（核心）
- ✅ `turnover_rate` - 换手率（流动性过滤）
- ✅ `close` - 收盘价（信号生成）
- ✅ `volume` - 成交量（验证）
- ✅ `amount` - 成交额（验证）

**策略特点**:
- VWAP作为价格中枢
- 流动性过滤（换手率）
- 数据质量验证

**适用场景**:
- 日内交易
- 短期均值回归
- 机构交易参考

**关键代码**:
```python
# 计算偏离度
deviation = (df['close'] - df['vwap']) / df['vwap']

# 买入信号：价格低于VWAP超过2%
buy_signal = (deviation < -0.02) & (df['turnover_rate'] > 0.5)
```

---

## 🎯 使用指南

### 安装依赖

```bash
pip install pandas numpy loguru
```

### 快速开始

#### 1. 复权价格动量策略

```python
from adj_price_momentum_strategy import AdjPriceMomentumStrategy

# 准备数据（从数据库加载）
stocks_data = {
    '000001': df_stock_1,  # 必须包含adj_close, adj_factor, close
    '600519': df_stock_2,
    # ...
}

# 创建策略
strategy = AdjPriceMomentumStrategy(
    lookback_period=20,  # 20日动量
    top_n=10             # 选择前10只
)

# 生成信号
selected_stocks = strategy.generate_signals(stocks_data)

print(f"选中股票: {selected_stocks}")
```

#### 2. VWAP均值回归策略

```python
from vwap_mean_reversion_strategy import VWAPMeanReversionStrategy

# 准备单只股票数据
df = load_stock_kline('000001')  # 必须包含vwap, turnover_rate

# 创建策略
strategy = VWAPMeanReversionStrategy(
    deviation_threshold=0.02,  # 2%偏离阈值
    hold_period=3,             # 持有3天
    use_turnover_filter=True,  # 启用流动性过滤
    min_turnover_rate=0.5      # 最小换手率0.5%
)

# 生成信号
df_with_signals = strategy.generate_signals(df)

# 回测
results = strategy.backtest(df_with_signals)

print(f"胜率: {results['win_rate']:.1%}")
print(f"累计收益: {results['total_return']:.2%}")
```

---

## 💡 最佳实践

### 1. 数据验证

**始终验证复权数据质量**:

```python
def validate_adj_data(df):
    """验证复权数据"""
    # 检查1：adj_close = close * adj_factor
    calculated = df['close'] * df['adj_factor']
    error = (df['adj_close'] - calculated).abs() / calculated
    
    if error.mean() > 0.01:
        logger.warning("复权价格计算异常")
        return False
    
    # 检查2：adj_factor合理范围
    if (df['adj_factor'] < 0).any() or (df['adj_factor'] > 100).any():
        logger.warning("复权因子异常")
        return False
    
    return True
```

**验证VWAP数据质量**:

```python
def validate_vwap_data(df):
    """验证VWAP数据"""
    # VWAP应该在[low, high]范围内
    valid = ((df['vwap'] >= df['low']) & (df['vwap'] <= df['high']))
    valid_rate = valid.sum() / len(df)
    
    if valid_rate < 0.9:
        logger.warning(f"VWAP合理性不足: {valid_rate:.1%}")
        return False
    
    return True
```

### 2. 收益率计算

**✅ 正确方式**:

```python
# 使用复权价格计算真实收益率
df['returns'] = df['adj_close'].pct_change()

# 累计收益
cumulative_return = (1 + df['returns']).prod() - 1
```

**❌ 错误方式**:

```python
# ❌ 使用原始价格（除权除息会产生虚假跳空）
df['returns'] = df['close'].pct_change()

# ❌ 会导致策略回测结果不准确
```

### 3. 流动性过滤

```python
# 使用换手率过滤低流动性股票
liquid_stocks = df[df['turnover_rate'] > 0.5]  # 换手率>0.5%

# 或使用成交额过滤
active_stocks = df[df['amount'] > 1e7]  # 成交额>1000万
```

### 4. 数据来源追溯

```python
# 检查数据来源
source_distribution = df.groupby('data_source')['symbol'].count()

# 优先使用高质量数据源
preferred_sources = ['Tushare', 'AKShare']
high_quality_data = df[df['data_source'].isin(preferred_sources)]
```

---

## 📊 策略评估指标

### 基础指标

```python
def calculate_metrics(returns):
    """计算策略指标"""
    metrics = {
        # 收益指标
        'total_return': (1 + returns).prod() - 1,
        'annual_return': returns.mean() * 252,  # 假设252个交易日
        
        # 风险指标
        'volatility': returns.std() * np.sqrt(252),
        'max_drawdown': calculate_max_drawdown(returns),
        
        # 风险调整收益
        'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252),
        
        # 交易指标
        'win_rate': (returns > 0).sum() / len(returns),
    }
    
    return metrics

def calculate_max_drawdown(returns):
    """计算最大回撤"""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min()
```

---

## 🔬 进阶示例

### 多因子组合策略

```python
class MultiFactorStrategy:
    """多因子组合策略"""
    
    def __init__(self):
        self.momentum_strategy = AdjPriceMomentumStrategy()
        self.vwap_strategy = VWAPMeanReversionStrategy()
    
    def generate_composite_signals(self, df):
        """生成组合信号"""
        # 动量因子
        momentum = self.momentum_strategy.calculate_momentum(df)
        
        # VWAP偏离因子
        vwap_deviation = self.vwap_strategy.calculate_vwap_deviation(df)
        
        # 流动性因子
        liquidity = df['turnover_rate']
        
        # 因子标准化
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        
        factors = pd.DataFrame({
            'momentum': scaler.fit_transform(momentum.values.reshape(-1, 1)).flatten(),
            'vwap_dev': scaler.fit_transform(vwap_deviation.values.reshape(-1, 1)).flatten(),
            'liquidity': scaler.fit_transform(liquidity.values.reshape(-1, 1)).flatten(),
        })
        
        # 加权组合（权重可优化）
        composite_score = (
            factors['momentum'] * 0.4 +
            factors['vwap_dev'] * (-0.3) +  # 负权重：偏离VWAP是买入机会
            factors['liquidity'] * 0.3
        )
        
        return composite_score
```

### 分红影响分析

```python
def analyze_dividend_impact(df):
    """分析分红对策略的影响"""
    # 检测除权除息事件
    df['adj_factor_change'] = df['adj_factor'].pct_change()
    dividend_days = df[df['adj_factor_change'].abs() > 0.005]
    
    # 分析分红前后收益
    results = []
    for idx in dividend_days.index:
        before = df.loc[idx-5:idx-1]['adj_close'].pct_change().mean()
        after = df.loc[idx+1:idx+5]['adj_close'].pct_change().mean()
        
        results.append({
            'date': df.loc[idx, 'datetime'],
            'return_before': before,
            'return_after': after,
            'adj_factor_change': df.loc[idx, 'adj_factor_change']
        })
    
    return pd.DataFrame(results)
```

---

## ⚠️ 注意事项

### 1. 数据完整性

- 确保K线数据包含所有20个标准字段
- 缺失字段会导致策略无法运行
- 使用`validate_adj_data()`和`validate_vwap_data()`验证

### 2. 复权方式

- 系统默认使用**前复权** (adj_factor调整历史价格)
- 适合回测和因子计算
- 不要混用复权和不复权数据

### 3. VWAP使用限制

- VWAP仅适用于**日内或短期**策略
- 长期策略建议使用移动平均线
- 注意验证VWAP的合理性（应在[low, high]范围内）

### 4. 流动性风险

- 始终进行流动性过滤（`turnover_rate > 0.5%`）
- 避免交易低流动性股票
- 考虑滑点和冲击成本

### 5. 数据来源

- 不同数据源可能有差异
- 使用`data_source`字段追溯数据质量
- 建立数据源优先级策略

---

## 📚 延伸阅读

### 复权理论

- [什么是复权](https://www.investopedia.com/terms/a/adjusted-close.asp)
- [前复权vs后复权vs不复权](https://zhuanlan.zhihu.com/p/141279522)
- [复权对量化回测的影响](https://zhuanlan.zhihu.com/p/359842156)

### VWAP策略

- [VWAP详解](https://www.investopedia.com/terms/v/vwap.asp)
- [VWAP算法交易](https://en.wikipedia.org/wiki/Volume-weighted_average_price)
- [VWAP均值回归策略](https://quantpedia.com/strategies/vwap-mean-reversion/)

### 多因子模型

- [多因子选股模型](https://zhuanlan.zhihu.com/p/100058974)
- [因子标准化方法](https://zhuanlan.zhihu.com/p/370651912)
- [因子组合优化](https://zhuanlan.zhihu.com/p/412589156)

---

## 🤝 贡献

欢迎贡献新的策略示例！

**贡献指南**:
1. 策略应基于20字段标准
2. 包含完整的数据验证
3. 提供使用示例和回测结果
4. 添加详细注释

---

## 📞 支持

遇到问题？
- 查看主项目README
- 提交Issue
- 加入技术交流群

---

**最后更新**: 2025-10-12  
**版本**: V2.0.4  
**作者**: FactorWeave-Quant Team

