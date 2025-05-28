# Hikyuu 量化交易系统 API 参考文档

## 目录

1. [核心模块](#核心模块)
   - [交易系统](#交易系统)
   - [数据管理](#数据管理)
   - [风险管理](#风险管理)
   - [信号系统](#信号系统)
   - [资金管理](#资金管理)
   
2. [分析模块](#分析模块)
   - [技术分析](#技术分析)
   - [模式识别](#模式识别)
   - [波浪分析](#波浪分析)
   
3. [数据处理模块](#数据处理模块)
   - [数据加载](#数据加载)
   - [数据预处理](#数据预处理)
   
4. [回测模块](#回测模块)
   - [回测引擎](#回测引擎)
   - [性能指标](#性能指标)
   
5. [图表模块](#图表模块)
   - [图表优化](#图表优化)
   - [实时更新](#实时更新)
   
6. [工具模块](#工具模块)
   - [性能监控](#性能监控)
   - [配置管理](#配置管理)
   - [异常处理](#异常处理)

## 核心模块

### 交易系统 (core/trading_system.py)

#### TradingSystem
主要的交易系统类，负责整体交易流程控制。

```python
class TradingSystem:
    def __init__(self):
        """初始化交易系统"""
        
    def set_stock(self, stock_code: str):
        """设置当前交易的股票
        
        Args:
            stock_code: 股票代码
        """
        
    def load_kdata(self, start_date: Optional[str] = None):
        """加载K线数据
        
        Args:
            start_date: 开始日期，可选
        """
        
    def calculate_signals(self, strategy: str = 'MA') -> List[Dict[str, Any]]:
        """计算交易信号
        
        Args:
            strategy: 策略名称，默认为MA策略
            
        Returns:
            交易信号列表
        """
        
    def run_backtest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """运行回测
        
        Args:
            params: 回测参数
            
        Returns:
            回测结果
        """
```

### 数据管理 (core/data_manager.py)

#### DataManager
数据管理类，处理数据的获取、存储和缓存。

```python
class DataManager:
    def get_k_data(self, stock_code: str, period: str) -> pd.DataFrame:
        """获取K线数据
        
        Args:
            stock_code: 股票代码
            period: 周期，如 'D'(日线), 'W'(周线)
            
        Returns:
            K线数据DataFrame
        """
        
    def get_stock_list(self) -> List[Dict]:
        """获取股票列表
        
        Returns:
            股票信息列表
        """
```

### 风险管理 (core/risk_manager.py)

#### RiskManager
风险管理类，实现风险控制策略。

```python
class RiskManager:
    def check_risk(self, signal: Dict) -> bool:
        """检查交易信号的风险
        
        Args:
            signal: 交易信号
            
        Returns:
            是否通过风险检查
        """
        
    def calculate_position_size(self, signal: Dict) -> int:
        """计算开仓数量
        
        Args:
            signal: 交易信号
            
        Returns:
            建议开仓数量
        """
```

## 分析模块

### 技术分析 (analysis/technical_analysis.py)

#### TechnicalAnalyzer
技术分析类，提供各种技术指标计算。

```python
class TechnicalAnalyzer:
    def analyze_support_resistance(self, kdata: KData, period: int = 20) -> Dict:
        """分析支撑和阻力位
        
        Args:
            kdata: K线数据
            period: 周期
            
        Returns:
            支撑阻力位分析结果
        """
        
    def analyze_momentum(self, kdata: KData) -> Dict:
        """分析动量指标
        
        Args:
            kdata: K线数据
            
        Returns:
            动量分析结果
        """
```

### 模式识别 (analysis/pattern_recognition.py)

#### PatternRecognizer
图形模式识别类。

```python
class PatternRecognizer:
    def find_head_shoulders(self, kdata: KData, threshold: float = 0.02) -> List[Dict]:
        """识别头肩形态
        
        Args:
            kdata: K线数据
            threshold: 阈值
            
        Returns:
            识别到的头肩形态列表
        """
        
    def find_double_tops_bottoms(self, kdata: KData, threshold: float = 0.02) -> List[Dict]:
        """识别双顶双底形态
        
        Args:
            kdata: K线数据
            threshold: 阈值
            
        Returns:
            识别到的双顶双底形态列表
        """
```

## 数据处理模块

### 数据加载 (data/data_loader.py)

```python
def fetch_fundamental_data(stock, use_cache: bool = True) -> pd.DataFrame:
    """获取基本面数据
    
    Args:
        stock: 股票代码
        use_cache: 是否使用缓存
        
    Returns:
        基本面数据DataFrame
    """
    
def validate_fundamental_data(df: pd.DataFrame) -> DataValidationResult:
    """验证基本面数据
    
    Args:
        df: 数据DataFrame
        
    Returns:
        验证结果
    """
```

### 数据预处理 (data/data_preprocessing.py)

```python
def optimize_data_quality(df: pd.DataFrame) -> pd.DataFrame:
    """优化数据质量
    
    Args:
        df: 输入数据
        
    Returns:
        优化后的数据
    """
    
def detect_and_handle_outliers(series, n_sigmas=3.0):
    """检测和处理异常值
    
    Args:
        series: 数据序列
        n_sigmas: 标准差倍数
        
    Returns:
        处理后的数据序列
    """
```

## 工具模块


### 配置管理 (utils/config_manager.py)

#### ConfigManager
配置管理类。

```python
class ConfigManager:
    def load_config(self, config_file: str):
        """加载配置文件
        
        Args:
            config_file: 配置文件路径
        """
        
    def save_config(self):
        """保存配置"""
```

## 未使用的函数和类

以下是系统中定义但未被使用的函数和类：

### optimization/performance_optimizer.py


### data/data_preprocessing.py

```python
def simple_kalman_filter(series, q=0.01, r=0.1):
    """简单卡尔曼滤波(未使用)"""
    
def reduce_noise_with_filtering(df, columns=None, window=5, method='ewm'):
    """降噪过滤(未使用)"""
```

## 注意事项

1. 使用未使用的函数和类时需要谨慎，它们可能已经过时或存在问题。
2. 建议使用核心模块中的稳定功能。
3. 在进行性能监控时，优先使用 utils/performance_monitor.py 中的实现。
4. 数据预处理时，优先使用已经过验证的函数。

## 最佳实践

1. 使用类型提示来提高代码可读性和可维护性
2. 遵循PEP 8编码规范
3. 编写详细的文档字符串
4. 实现适当的错误处理
5. 使用日志记录来跟踪问题
6. 编写单元测试确保代码质量

## 版本兼容性

- Python 3.8+
- 依赖库版本要求见 requirements.txt

## 更多资源

- [完整文档](docs/index.md)
- [开发指南](docs/development.md)
- [常见问题](docs/faq.md)
- [更新日志](CHANGELOG.md) 