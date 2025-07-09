# Hikyuu 量化交易系统
#注意：后续有新功能涉及多线程/定时器/UI更新，务必继续采用"信号/槽+主线程UI更新"模式：使用 pyqtSignal 和 pyqtSlot
   所有QWidget及其子类（如QTableWidgetItem）必须在主线程创建和操作。
   子线程只做数据计算，结果通过信号发回主线程，由主线程更新UI。
   后续有自定义指标或新UI组件，务必统一用self.main_layout管理布局，避免直接用self.layout。
   若有新指标或趋势分析方法，参考上述兼容写法，优先判断数据类型，保证健壮性
   有新增分析Tab或按钮，均建议统一用set_kdata同步数据，内部分析逻辑统一用self.current_kdata，避免多处维护
   在 gui/dialogs/db_field_permissions.json 中配置字段权限（如 \"readonly\"、\"hidden\"）。
   "批量修改"对话框支持条件筛选，操作更安全高效。
   只读字段在所有编辑场景下均不可更改，数据安全有保障。
体验方法
   在"字段权限管理"对话框中，点击"上传权限到云端"或"从云端拉取权限"即可同步配置。
   点击"查看权限变更日志"可浏览所有权限变更历史。
   注意：
   云端API地址需替换为你实际的企业API或云存储接口。
   权限日志和配置均为json格式，便于二次开发和自动化集成
   
## 系统概述
Hikyuu量化交易系统是一个功能完整的量化交易平台，支持策略开发、回测、实盘交易等功能。系统采用Python编写，具有良好的可扩展性和易用性。

## 🔧 最新优化 (2025)

### ✅ 技术指标系统V3 - 数据库驱动架构（已完成）
Hikyuu-UI项目的技术指标系统已完成从混合实现迁移至统一、动态、数据库驱动的全新架构。

#### 🎯 重构目标
- **单一事实来源**：消除多个模块中的重复计算逻辑
- **数据驱动**：所有指标定义存储在数据库中，支持动态加载和更新
- **完全解耦**：UI层和业务逻辑层与具体指标实现解耦
- **动态扩展**：支持通过插件系统添加自定义指标

#### 🛠️ 核心组件
- **IndicatorService**：统一的指标服务，负责指标的加载、计算和管理
- **indicators.db**：指标定义数据库，包含所有系统内置指标和用户自定义指标
- **指标适配器**：兼容旧接口，确保平滑迁移
- **插件系统**：支持通过插件动态注册新指标

#### 📊 使用方法
1. **获取指标列表**：
   ```python
   from core.indicator_service import get_all_indicators_metadata
   indicators = get_all_indicators_metadata()
   ```

2. **计算指标**：
   ```python
   from core.indicator_service import calculate_indicator
   result = calculate_indicator("MA", kdata, {"timeperiod": 5})
   ```

3. **添加自定义指标**：
   创建插件，实现`register_indicators`函数：
   ```python
   def register_indicators():
       return [
           {
               "name": "自定义指标",
               "calculation_module": "my_plugin.indicators",
               "calculation_function": "calculate_custom_indicator",
               "category": "自定义",
               "description": "这是一个自定义指标",
               "parameters": {...}
           }
       ]
   ```

#### 🔄 迁移状态
- **UI层**：已完成迁移，所有UI组件使用新的指标系统
- **核心逻辑层**：已完成迁移，所有业务代码使用新的指标系统
- **旧代码清理**：已完成，所有冗余文件已移除
- **插件系统**：已完成实现，支持通过插件注册自定义指标

## 系统特点
1. **完整的量化交易功能**：支持数据获取、策略开发、回测分析、实盘交易等全流程
2. **高度可定制**：提供丰富的API和插件系统，支持用户自定义指标、策略和交易规则
3. **性能优化**：关键计算模块采用C++实现，保证高效的数据处理和策略回测
4. **友好的用户界面**：提供直观的图形界面，方便用户操作和分析

## 安装方法
```bash
pip install -r requirements.txt
```

## 快速开始
```python
python main.py
```

## 文档
详细文档请参考 `docs` 目录下的文件。

## 贡献指南
欢迎提交问题报告、功能请求和代码贡献。请遵循以下步骤：
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证
本项目采用 MIT 许可证 - 详见 LICENSE 文件


#### 🎯 已完成的核心功能迁移
- ✅ **中间主图面板完善**：时间范围选择器、回测区间选择器、图表类型选择、区间统计功能
- ✅ **高级搜索系统**：完整的多维度股票筛选功能，支持异步搜索
- ✅ **数据导出功能**：单股票导出和批量导出，支持Excel和CSV格式
- ✅ **完整右键菜单系统**：查看详情、收藏管理、导出数据、投资组合管理等
- ✅ **股票详情对话框**：基本信息、历史K线数据、财务数据展示
- ✅ **投资组合管理**：创建投资组合、设置投资金额、组合分类管理
- ✅ **高级功能对话框**：节点管理、云端API、指标市场、批量分析、策略管理
- ✅ **数据质量检查**：单股和批量数据质量检查功能
- ✅ **系统设置**：主题管理、基本设置、数据设置等完整配置功能
## 系统架构

该交易系统遵循Hikyuu量化框架的设计理念，将交易系统拆分为多个独立组件：

- **信号指示器(Signal)**: 负责产生买入和卖出信号
- **资金管理(Money Manager)**: 决定每次交易的资金分配和头寸规模
- **止损策略(Stop Loss)**: 控制单笔交易的最大风险
- **止盈策略(Take Profit)**: 设定获利目标和退出条件
- **市场环境判断(Environment)**: 评估当前市场状态是否适合交易
- **系统有效条件(Condition)**: 确定交易系统是否处于有效状态
- **移滑价差算法(Slippage)**: 模拟实际交易中的价格滑点
- **交易成本(Trade Cost)**: 计算交易佣金和税费

## 目录结构

```
合适的买卖点/
├── backtest/                 # 回测相关组件
│   ├── backtest_engine.py    # 回测引擎实现
│   └── performance_metrics.py # 性能评估指标计算
├── core/                     # 核心组件
│   ├── adaptive_stop_loss.py # 自适应止损策略
│   ├── market_environment.py # 市场环境判断
│   ├── money_manager.py      # 资金管理策略
│   ├── money/                # 资金管理子组件
│   ├── risk_alert.py         # 风险预警
│   ├── risk_control.py       # 风险控制
│   ├── risk_exporter.py      # 风险数据导出
│   ├── risk_metrics.py       # 风险指标计算
│   ├── risk/                 # 风险管理子组件
│   ├── signal.py             # 信号生成基类
│   ├── signal_system.py      # 信号系统
│   ├── signal/               # 信号生成子组件
│   ├── stop_loss.py          # 止损策略