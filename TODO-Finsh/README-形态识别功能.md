# YS-Quant‌ 形态识别功能完整指南

## 概述

YS-Quant‌的形态识别功能是一个完整的K线形态分析系统，支持从UI入口到后端业务逻辑的完整调用链。该系统具备统一接口、通达信形态导入、自动识别等强大功能。

## 🎯 核心特性

### 1. 统一形态识别框架
- **基础框架** (`analysis/pattern_base.py`)
  - `SignalType`、`PatternCategory` 枚举类型
  - `PatternResult`、`PatternConfig` 数据类
  - `BasePatternRecognizer` 抽象基类
  - `PatternAlgorithmFactory` 工厂模式
  - `GenericPatternRecognizer` 通用识别器

### 2. 数据库驱动的算法管理
- **算法数据库化** (`db/init_pattern_algorithms.py`)
  - 15种核心形态的完整算法代码
  - 单根K线：hammer、doji、shooting_star、inverted_hammer、marubozu、spinning_top
  - 双根K线：bullish_engulfing、bearish_engulfing、piercing_pattern、dark_cloud_cover
  - 三根K线：three_white_soldiers、three_black_crows、morning_star、evening_star
  - 每个算法包含完整的识别逻辑和参数配置

### 3. 增强的形态管理器
- **形态管理** (`analysis/pattern_manager.py`)
  - 集成新的基础框架和数据库算法
  - 数据库表结构管理（pattern_history、tdx_patterns表）
  - 形态配置的增删改查功能
  - 通达信公式导入（`_convert_tdx_formula`方法）
  - 形态效果统计和推荐功能

### 4. 完整的UI界面
- **UI层集成** (`gui/widgets/analysis_widget.py`)
  - 自动识别按钮
  - 形态配置管理
  - 通达信导入界面
  - 形态统计分析
  - 高级功能支持

## 🚀 快速开始

### 1. 初始化数据库
```bash
python db/init_pattern_algorithms.py
```

### 2. 运行测试
```bash
python test_pattern_complete.py
```

### 3. 启动主程序
```bash
python main.py
```

## 📋 功能详解

### 自动识别功能
- **一键识别**：点击"自动识别"按钮，系统自动扫描当前股票的所有形态
- **智能过滤**：支持按置信度、时间范围、形态类型进行筛选
- **实时更新**：支持自动刷新，数据更新时自动重新识别

### 形态配置管理
- **参数调整**：可调整每种形态的识别参数
- **启用/禁用**：可选择性启用或禁用特定形态
- **配置导入导出**：支持配置文件的导入导出

### 通达信公式导入
- **公式转换**：将通达信公式自动转换为Python代码
- **自定义形态**：支持用户自定义形态的添加
- **兼容性强**：支持大部分通达信公式语法

### 统计分析功能
- **成功率统计**：分析每种形态的历史成功率
- **收益率分析**：计算形态出现后的平均收益
- **推荐系统**：基于历史数据推荐效果最好的形态

## 🔧 技术架构

### 设计模式
- **工厂模式**：`PatternAlgorithmFactory`实现算法的动态加载
- **策略模式**：`BasePatternRecognizer`定义统一的识别接口
- **观察者模式**：UI组件与业务逻辑的解耦

### 数据存储
- **SQLite数据库**：存储形态配置和算法代码
- **热更新支持**：算法代码可动态修改无需重启
- **版本管理**：支持算法代码的版本控制

### 安全机制
- **沙箱执行**：算法代码在安全环境中执行
- **输入验证**：严格的数据验证和错误处理
- **权限控制**：限制算法代码的执行权限

## 📊 支持的形态类型

### 单根K线形态
| 形态名称 | 英文名 | 信号类型 | 描述 |
|---------|--------|----------|------|
| 锤头线 | hammer | 买入 | 长下影线，小实体，几乎没有上影线 |
| 十字星 | doji | 中性 | 开盘价与收盘价几乎相等 |
| 流星线 | shooting_star | 卖出 | 长上影线，小实体，几乎没有下影线 |
| 倒锤头线 | inverted_hammer | 买入 | 长上影线，小实体，出现在下跌趋势中 |
| 光头光脚线 | marubozu | 趋势 | 没有上下影线的K线 |
| 纺锤线 | spinning_top | 中性 | 小实体，上下影线较长 |

### 双根K线形态
| 形态名称 | 英文名 | 信号类型 | 描述 |
|---------|--------|----------|------|
| 看涨吞没 | bullish_engulfing | 买入 | 阳线完全吞没前一根阴线 |
| 看跌吞没 | bearish_engulfing | 卖出 | 阴线完全吞没前一根阳线 |
| 刺透形态 | piercing_pattern | 买入 | 阳线刺透阴线实体的一半以上 |
| 乌云盖顶 | dark_cloud_cover | 卖出 | 阴线覆盖阳线实体的一半以上 |

### 三根K线形态
| 形态名称 | 英文名 | 信号类型 | 描述 |
|---------|--------|----------|------|
| 三白兵 | three_white_soldiers | 买入 | 三根连续上涨的阳线 |
| 三只乌鸦 | three_black_crows | 卖出 | 三根连续下跌的阴线 |
| 早晨之星 | morning_star | 买入 | 阴线+星线+阳线组合 |
| 黄昏之星 | evening_star | 卖出 | 阳线+星线+阴线组合 |

## 🎮 UI操作指南

### 形态识别Tab界面

#### 工具栏功能
- **自动识别**：一键识别所有形态
- **形态配置**：管理形态参数和算法
- **通达信导入**：导入通达信公式
- **形态统计**：查看统计分析结果

#### 快速设置
- **置信度预设**：高/中/低/全部置信度快速选择
- **时间范围预设**：1个月/3个月/6个月/1年/全部时间
- **自动刷新**：开启后数据更新时自动重新识别

#### 筛选功能
- **形态类型**：多选支持，可选择特定形态类型
- **交易信号**：按买入/卖出/中性信号筛选
- **置信度区间**：设置最小和最大置信度阈值
- **时间区间**：设置识别的时间范围

#### 结果展示
- **表格显示**：详细的形态识别结果
- **右键菜单**：查看详情、定位图表、删除形态
- **导出功能**：支持Excel、CSV、JSON格式导出

### 快捷键支持
- `Ctrl+R`：识别形态
- `Ctrl+F`：筛选结果
- `F5`：刷新当前Tab

## 🔍 API接口说明

### PatternManager类

#### 主要方法
```python
# 识别所有形态
patterns = manager.identify_all_patterns(kdata, confidence_threshold=0.5)

# 获取形态配置
configs = manager.get_pattern_configs()

# 获取特定形态
config = manager.get_pattern_by_name('hammer')

# 导入通达信公式
success = manager.import_tdx_formula(name, formula)

# 获取统计信息
stats = manager.get_pattern_statistics(kdata)
```

### GenericPatternRecognizer类

#### 使用示例
```python
from analysis.pattern_base import GenericPatternRecognizer
from analysis.pattern_manager import PatternManager

# 获取形态配置
manager = PatternManager()
config = manager.get_pattern_by_name('hammer')

# 创建识别器
recognizer = GenericPatternRecognizer(config)

# 执行识别
results = recognizer.recognize(kdata)
```

## 🧪 测试验证

### 运行完整测试
```bash
python test_pattern_complete.py
```

### 测试单个形态
```bash
python test_single_pattern.py
```

### 检查数据库算法
```bash
python check_db_algorithms.py
```

## 📈 性能优化

### 算法优化
- **向量化计算**：使用NumPy进行批量计算
- **缓存机制**：缓存计算结果避免重复计算
- **并行处理**：支持多线程形态识别

### 内存管理
- **数据分片**：大数据集分片处理
- **垃圾回收**：及时释放不需要的对象
- **内存监控**：监控内存使用情况

## 🔧 扩展开发

### 添加新形态

1. **定义算法代码**
```python
# 新形态识别算法
for i in range(len(kdata)):
    k = kdata.iloc[i]
    # 识别逻辑
    if condition:
        result = create_result(
            pattern_type='new_pattern',
            signal_type=SignalType.BUY,
            confidence=0.8,
            index=i,
            price=k['close']
        )
        results.append(result)
```

2. **添加到数据库**
```python
# 在init_pattern_algorithms.py中添加
patterns_data.append({
    'name': '新形态',
    'english_name': 'new_pattern',
    'category': '单根K线',
    'signal_type': 'buy',
    'algorithm_code': algorithm_code
})
```

### 自定义识别器

```python
from analysis.pattern_base import BasePatternRecognizer

class CustomPatternRecognizer(BasePatternRecognizer):
    def recognize(self, kdata):
        # 自定义识别逻辑
        results = []
        # ... 识别代码 ...
        return results

# 注册到工厂
PatternAlgorithmFactory.register('custom_pattern', CustomPatternRecognizer)
```

## 🐛 故障排除

### 常见问题

1. **算法执行失败**
   - 检查算法代码语法
   - 确认执行环境变量
   - 查看错误日志

2. **形态识别结果为空**
   - 降低置信度阈值
   - 检查数据质量
   - 验证算法逻辑

3. **UI界面无响应**
   - 检查数据量大小
   - 启用后台处理
   - 优化算法性能

### 调试工具

```python
# 启用调试模式
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看算法执行详情
recognizer.debug_mode = True
results = recognizer.recognize(kdata)
```

## 📚 参考资料

- [HIkyuu框架文档](https://hikyuu.org/)
- [技术分析理论](https://www.investopedia.com/technical-analysis/)
- [K线形态大全](https://www.candlestickforum.com/)
- [通达信公式语法](https://www.tdx.com.cn/)

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进形态识别功能：

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

---

**注意**：本功能仅供学习和研究使用，不构成投资建议。投资有风险，入市需谨慎。 