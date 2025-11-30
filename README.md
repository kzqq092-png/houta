# FactorWeave-Quant 2.0

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Active%20Development-brightgreen.svg)]()

一个功能强大的Python量化交易系统，集成了多数据源支持、智能插件系统、实时数据处理、AI预测分析等核心功能。专为量化投资者和金融技术研究者设计。

## 🌟 核心特性

### 📊 数据管理
- **多数据源支持**：集成AKShare、东方财富、通达信、新浪等10+数据源
- **统一数据接口**：UnifiedDataManager提供一致的数据访问API
- **DuckDB高性能分析数据库**：支持亚秒级查询，适合大规模历史数据
- **实时行情推送**：异步事件驱动架构支持实时数据更新
- **多资产类型**：支持A股、港股、美股、加密货币、期货等

### 🏗️ 架构设计
- **插件系统**：TET框架支持数据源、指标、策略动态加载
- **服务容器**：依赖注入容器管理40+个业务服务
- **事件驱动**：异步事件总线支持高效的松耦合通信
- **多级缓存**：缓存系统提升数据访问性能3-5倍
- **微服务化**：模块独立部署，支持分布式架构

### 🚀 AI与预测
- **深度学习集成**：TensorFlow/Keras支持自定义预测模型
- **特征工程**：自动化因子提取与特征工程
- **模型训练**：支持增量模型训练与在线学习
- **情绪分析**：市场情绪和舆情监控
- **智能推荐**：基于历史表现的策略推荐

### 📈 策略与回测
- **完整回测引擎**：支持逐笔成交、高保真回测
- **动态策略加载**：运行时加载/卸载策略
- **风险管理**：多层级风险控制与止损机制
- **绩效分析**：详细的收益分析、最大回撤、夏普比率等
- **参数优化**：支持网格搜索和贝叶斯优化

### 🎯 UI与交互
- **PyQt5现代界面**：响应式设计，暗色主题支持
- **实时监控面板**：K线图、技术指标、策略信号实时展示
- **交互式图表**：基于pyecharts和mplfinance的高级可视化
- **配置管理**：图形化配置界面，无需编码修改参数
- **日志监控**：实时日志输出与问题诊断

### ⚡ 性能优化
- **硬件加速**：支持GPU加速（CUDA）
- **连接池管理**：SQLAlchemy QueuePool优化数据库连接
- **异步处理**：基于asyncio的全异步架构
- **并行计算**：多线程/多进程支持
- **内存优化**：精确的小数点精度标准（符合金融行业标准）

## 🚀 快速开始

### 系统要求
- **Python**: 3.8 或更高版本
- **操作系统**: Windows / Linux / macOS
- **内存**: 8GB+ (推荐16GB)
- **磁盘**: 10GB+ (根据数据量调整)

### 安装步骤

#### 1. 克隆项目
```bash
git clone https://github.com/yourusername/FactorWeave-Quant.git
cd FactorWeave-Quant
```

#### 2. 创建虚拟环境（推荐）
```bash
# 使用 conda
conda create -n factorweave python=3.10
conda activate factorweave

# 或使用 venv
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```

**注意**：某些包（如 ta-lib、torch）可能需要特殊配置：
```bash
# ta-lib (可选，用于技术分析)
# Windows: 从 https://github.com/mrjbq7/ta-lib/releases 下载
# pip install --user --upgrade ta-lib

# 如需GPU支持 (可选)
# conda install pytorch::pytorch torchvision torchaudio -c pytorch
```

#### 4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，设置API密钥等
```

#### 5. 初始化数据库
```bash
python init_database.py
```

#### 6. 启动应用
```bash
python main.py
```

## 📚 项目结构

```
FactorWeave-Quant/
├── core/                          # 核心业务逻辑
│   ├── containers/               # 依赖注入容器
│   ├── services/                 # 业务服务（40+个）
│   ├── events/                   # 事件系统
│   ├── database/                 # 数据库管理
│   ├── data/                     # 数据模型与处理
│   ├── performance/              # 性能监控
│   └── tet_framework/            # TET插件框架
│
├── gui/                          # PyQt5 用户界面
│   ├── panels/                   # 各类面板组件
│   ├── dialogs/                  # 对话框
│   ├── widgets/                  # 自定义小部件
│   ├── themes/                   # UI主题
│   └── main_window.py            # 主窗口
│
├── plugins/                      # 插件系统
│   ├── data_sources/             # 数据源插件
│   │   ├── akshare_plugin/
│   │   ├── tongdaxin_plugin/
│   │   └── eastmoney_plugin/
│   ├── indicators/               # 技术指标插件
│   ├── strategies/               # 交易策略插件
│   └── analysis/                 # 分析插件
│
├── db/                          # 数据库相关
│   ├── models/                  # ORM模型定义
│   ├── migrations/              # 数据库迁移脚本
│   └── init_database.py         # 数据库初始化
│
├── utils/                       # 工具函数库
│   ├── config.py               # 配置管理
│   ├── logger.py               # 日志配置
│   └── decorators.py           # 装饰器工具
│
├── config/                     # 配置文件
│   ├── app_config.json
│   ├── plugin_config.json
│   └── strategy_config.json
│
├── tests/                      # 测试套件
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   ├── performance/            # 性能测试
│   └── fixtures/               # 测试数据
│
├── examples/                   # 使用示例
│   ├── data_download/          # 数据下载示例
│   ├── strategy_demo/          # 策略示例
│   └── indicator_demo/         # 指标示例
│
├── docs/                       # 文档
│   ├── architecture/           # 架构设计文档
│   ├── api/                    # API参考
│   ├── plugins/                # 插件开发指南
│   └── tutorials/              # 教程
│
├── main.py                     # 应用入口
├── requirements.txt            # 项目依赖
├── CLAUDE.md                   # 开发指南
├── LICENSE                     # Apache 2.0许可证
└── README.md                   # 本文件
```

## 🔧 使用指南

### 基本用法

#### 数据获取
```python
from core.services.unified_data_manager import UnifiedDataManager

# 初始化数据管理器
data_manager = UnifiedDataManager()

# 获取K线数据
klines = await data_manager.get_kdata(
    symbol="000001",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency="1d"
)

# 获取实时行情
quote = await data_manager.get_quote(symbol="000001")
```

#### 策略开发
```python
from core.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.name = "My Strategy"

    async def on_bar(self, symbol: str, bar_data: dict):
        # 技术分析
        ma20 = self.calculate_ma(symbol, 20)
        ma50 = self.calculate_ma(symbol, 50)

        # 信号生成
        if ma20 > ma50:
            await self.buy(symbol, quantity=100)
        elif ma20 < ma50:
            await self.sell(symbol, quantity=100)
```

#### 指标计算
```python
from core.indicators.technical_indicators import TechnicalIndicators

indicators = TechnicalIndicators(klines_data)

# 计算移动平均线
ma20 = indicators.moving_average(period=20)

# 计算RSI
rsi = indicators.rsi(period=14)

# 计算MACD
macd = indicators.macd(fast=12, slow=26, signal=9)
```

### 插件开发

#### 创建数据源插件
```python
from core.tet_framework.plugin_base import IDataSourcePlugin

class MyDataSourcePlugin(IDataSourcePlugin):
    def __init__(self):
        super().__init__()
        self.name = "MyDataSource"

    async def fetch_kdata(self, symbol: str, start: str, end: str):
        # 实现数据获取逻辑
        pass
```

#### 创建策略插件
```python
from core.plugin_manager import IStrategyPlugin

class MyStrategyPlugin(IStrategyPlugin):
    def __init__(self):
        super().__init__()
        self.name = "MyStrategy"

    async def on_bar(self, data):
        # 实现策略逻辑
        pass
```

详见 [插件开发指南](docs/plugins/plugin_development.md)

## 📊 核心功能详解

### 1. TET插件框架
- **动态插件加载**：运行时发现和加载插件
- **标准接口定义**：所有插件遵循统一接口
- **生命周期管理**：完整的插件初始化、运行、卸载流程
- **配置化管理**：JSON配置控制插件行为

### 2. 统一数据管理器
- **多源数据融合**：自动选择最佳数据源
- **缓存策略**：智能缓存减少API调用
- **数据验证**：自动数据质量检查
- **历史对比**：不同数据源一致性验证

### 3. 服务容器系统
- **依赖注入**：自动解决服务依赖
- **生命周期管理**：SINGLETON/SCOPED/TRANSIENT
- **健康检查**：服务状态监控
- **优雅启停**：安全的服务启动和关闭

### 4. 实时事件系统
- **异步事件处理**：基于asyncio
- **事件订阅/发布**：松耦合通信
- **事件过滤**：灵活的事件匹配
- **重试机制**：失败自动重试

### 5. 性能监控
- **实时指标收集**：查询时间、数据量等
- **性能分析**：识别瓶颈
- **告警机制**：异常自动告警
- **历史追踪**：性能趋势分析

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定分类
pytest -m unit              # 单元测试
pytest -m integration       # 集成测试
pytest -m performance       # 性能测试

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

### 测试覆盖率要求
- 目标：≥ 80% 代码覆盖率
- 关键模块：100% 覆盖
- 自动化回归测试：每次提交前运行

## 📖 文档

详细文档请参考：
- [开发指南](CLAUDE.md) - Claude Code开发指南
- [架构设计](docs/architecture/) - 系统架构设计文档
- [API参考](docs/api/) - API详细文档
- [插件开发](docs/plugins/) - 插件开发教程
- [性能优化](docs/performance/) - 性能优化指南

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 贡献流程
1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 代码规范
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 风格指南
- 使用 [Black](https://github.com/psf/black) 格式化代码
- 使用 [isort](https://github.com/PyCPA/isort) 整理导入
- 使用 [MyPy](http://mypy-lang.org/) 进行类型检查
- 编写详细的注释和文档字符串

### 提交规范
```
<type>(<scope>): <subject>

<body>

<footer>
```

类型包括：
- `feat`: 新特性
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码风格
- `refactor`: 代码重构
- `test`: 测试用例
- `chore`: 构建/工具

## 🐛 已知问题

- ta-lib在某些系统上安装困难，可选安装
- GPU版torch包较大，建议使用conda安装
- 某些数据源API可能需要密钥授权

## 📋 功能路线图

### v2.1 (计划)
- [ ] 期权交易支持
- [ ] 高频交易框架
- [ ] GraphQL API接口

### v2.2 (计划)
- [ ] Web服务化部署
- [ ] Kubernetes容器编排
- [ ] 实时数据流处理

### v2.3+ (规划中)
- [ ] 机器学习模型库扩展
- [ ] 分布式回测引擎
- [ ] 区块链数据集成

## 📞 获取帮助

- **文档**: 查看 [docs/](docs/) 目录
- **问题**: 提交 [Issue](https://github.com/yourusername/FactorWeave-Quant/issues)
- **讨论**: 参与 [Discussions](https://github.com/yourusername/FactorWeave-Quant/discussions)
- **邮件**: 联系开发团队 (如有)

## 📄 许可证

本项目采用 [Apache License 2.0](LICENSE) 许可证。

详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

感谢以下项目和社区的支持：
- [AKShare](https://github.com/akfamily/akshare) - 数据获取
- [Hikyuu](https://github.com/fasiondog/hikyuu) - 系统交易框架
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - UI框架
- [DuckDB](https://duckdb.org/) - 分析数据库

## 📊 项目统计

- **代码行数**: 50,000+
- **测试覆盖**: 85%+
- **核心服务**: 40+
- **插件系统**: 支持自定义扩展
- **数据源**: 10+ 集成

## 🔐 安全性

- 所有API调用使用HTTPS
- 敏感信息（密钥、密码）从环境变量读取
- 定期安全审计
- 依赖更新策略：有漏洞及时更新

---

**项目维护者**: FactorWeave-Quant开发团队

**最后更新**: 2025年11月27日

**当前版本**: 2.0.0

⭐ 如果您觉得这个项目有帮助，请给个Star支持！
