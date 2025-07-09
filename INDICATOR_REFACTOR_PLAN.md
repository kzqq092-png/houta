# 技术指标系统V3 - 数据库驱动架构迁移计划

## 1. 概述

本文档为 `Hikyuu-UI` 技术指标系统重构的详细实施计划。旨在将系统从当前的混合实现，迁移至一个统一、动态、数据库驱动的全新架构。

- **最终交付物:** 一个由 `IndicatorService` 驱动，以 `indicators.db` 为数据核心，支持插件扩展的现代化指标系统。
- **核心原则:** 单一事实来源、数据驱动、完全解耦、动态扩展。

---

## 2. Phase 0: 准备工作 - 建立安全网 (Pre-computation)

**目标:** 在不改动任何现有代码的情况下，为系统的核心计算逻辑建立一个完整的测试套件。这是整个重构工作中最关键的一步，是保证重构安全性的基石。

- [ ] **创建测试数据夹具 (Fixture)**
  - **文件:** `test/fixtures/kdata.csv`
  - **操作:** 选取一只具有代表性的股票（如'SH.600036'）大约一年的日K线数据，包含 `datetime`, `open`, `high`, `low`, `close`, `volume` 列，保存为CSV文件。这将作为所有测试的统一输入，确保结果的可复现性。

- [ ] **为 `features` 模块编写单元测试**
  - **文件:** `test/test_feature_calculations.py`
  - **操作:**
    1.  加载 `test/fixtures/kdata.csv` 数据。
    2.  为 `features/basic_indicators.py` 中的 `calculate_base_indicators()` 函数编写测试用例。调用该函数，并将返回的DataFrame中每一个指标列（如 `MA5`, `MACD_hist`）的结果与手动验证或已知的正确值进行断言。
    3.  为 `features/advanced_indicators.py` 中的 `calculate_advanced_indicators()` 函数编写测试用例，断言其所有输出列（如 `cmf`, `trix`）的正确性。
    4.  为 `features/advanced_indicators.py` 中的 `create_pattern_recognition_features()` 编写测试用例。手动在 `kdata.csv` 中构造几个K线形态（如锤子线、吞没形态），并断言函数能正确识别它们（例如，对应行的 `is_hammer` 列值为 `1`）。

- [ ] **为 `indicators_algo.py` 编写单元测试**
  - **文件:** `test/test_algo_calculations.py`
  - **操作:**
    1.  加载 `test/fixtures/kdata.csv` 数据。
    2.  为 `indicators_algo.py` 中每一个核心的 `calc_` 函数（如 `calc_ma`, `calc_macd`, `calc_rsi`, `calc_kdj`, `calc_boll`）编写独立的测试用例。
    3.  断言计算结果与 `TA-Lib` 官方或其他可靠来源的计算结果一致。

**阶段完成标志:** 所有新建的测试用例均能稳定通过。我们拥有了一张覆盖所有现有计算逻辑的安全网。

---

## 3. Phase 1: 基础设施构建 (Foundation)

**目标:** 搭建新架构的核心组件，包括数据库、算法库和核心服务，为后续的迁移做准备。

- [ ] **创建并初始化数据库**
  - **文件:** `db/initialize_indicators.py`
  - **操作:**
    1.  完善该脚本，在 `initialize_system_indicators` 函数中添加**所有**系统内置指标的定义，包括 `RSI`, `KDJ`, `BOLL`, `ATR`, `OBV`, `CCI` 等。确保 `calculation_module` 和 `calculation_function` 的路径指向规划中的新位置。
    2.  在终端运行 `python db/initialize_indicators.py`。
    3.  **验证:** 检查 `db/indicators.db` 文件是否生成，并使用SQLite客户端工具打开，确认 `indicators` 表中数据完整、正确。

- [ ] **创建统一指标算法库**
  - **操作:**
    1.  创建新目录: `core/indicators/library/`
    2.  创建新文件:
        - `core/indicators/library/trends.py` (存放MA, BOLL等)
        - `core/indicators/library/oscillators.py` (存放MACD, RSI, KDJ, CCI等)
        - `core/indicators/library/volumes.py` (存放OBV等)
        - `core/indicators/library/volatility.py` (存放ATR等)
        - `core/indicators/library/patterns.py` (存放K线形态识别逻辑)
    3.  **迁移代码:**
        - 将 `indicators_algo.py` 中所有的 `calc_` 函数，按其分类分别剪切并粘贴到上述对应的新文件中。函数名可以保持不变（如`calculate_ma`）。
        - 将 `features/advanced_indicators.py` 中 `calculate_advanced_indicators` 函数内的所有计算逻辑，**逐个**拆分并迁移到上述对应的新文件中。
        - 将 `features/advanced_indicators.py` 中 `create_pattern_recognition_features` 的逻辑整体迁移到 `patterns.py` 中。
        - **确保:** 所有迁移后的函数都是纯粹的计算单元，只依赖 `pandas` 和 `numpy`，不依赖任何外部状态。

- [ ] **开发核心服务 `IndicatorService`**
  - **文件:** `core/services/indicator_service.py`
  - **操作:** 创建该文件并实现 `IndicatorService` 类。
    ```python
    import sqlite3
    import json
    import pandas as pd
    from importlib import import_module
    from typing import Dict, List, Any

    class IndicatorService:
        _instance = None

        def __new__(cls, *args, **kwargs):
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance

        def __init__(self, db_path='db/indicators.db'):
            if not hasattr(self, 'initialized'):
                self.db_path = db_path
                self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
                self.connection.row_factory = sqlite3.Row
                self.initialized = True

        def get_all_indicator_defs(self) -> List[Dict[str, Any]]:
            """从数据库获取所有指标的定义"""
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM indicators ORDER BY category, display_name;")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        def get_indicator_def(self, name: str) -> Dict[str, Any]:
            """获取单个指标的定义"""
            # ... 实现数据库查询 ...

        def calculate(self, name: str, kdata: pd.DataFrame, **params) -> pd.DataFrame:
            """动态计算指定指标"""
            indicator_def = self.get_indicator_def(name)
            if not indicator_def:
                raise ValueError(f"不支持的指标: {name}")

            module_path = indicator_def['calculation_module']
            func_name = indicator_def['calculation_function']
            
            try:
                module = import_module(module_path)
                calculation_func = getattr(module, func_name)
            except (ImportError, AttributeError) as e:
                raise RuntimeError(f"无法加载指标计算函数: {module_path}.{func_name}") from e

            # 此处可以加入对 `params` 的验证逻辑
            
            return calculation_func(kdata, **params)
            
        def close(self):
            self.connection.close()

    # 在服务容器中注册为单例
    def get_indicator_service():
        return IndicatorService()
    ```

**阶段完成标志:** `IndicatorService` 创建完成，能够成功从数据库加载指标定义并动态调用位于新算法库中的函数。

---

## 4. Phase 2: 增量替换与集成 (Migration)

**目标:** 将系统中所有旧的指标调用方式，逐一替换为对 `IndicatorService` 的调用，并在每一步都进行测试验证。

- [ ] **重构UI层**
  - **文件:** `gui/widgets/analysis_widget.py`, `gui/dialogs/indicator_config_dialog.py` (假设存在)
  - **操作:**
    1.  移除所有 `from indicators_algo import ...` 和 `from features.advanced_indicators import ...`。
    2.  在初始化时，注入 `IndicatorService` 实例。
    3.  修改UI构建逻辑，调用 `indicator_service.get_all_indicator_defs()` 来获取指标列表和分类，动态填充下拉菜单或树状列表。
    4.  当用户选择一个指标并配置参数时，调用 `indicator_service.calculate(name, kdata, **params)` 来获取计算结果，并更新图表或表格。
  - **验证:** 运行程序，检查技术分析窗口和图表指标功能是否正常。

- [ ] **重构核心逻辑层**
  - **文件:** `core/stock_screener.py`
    - **操作:** 找到所有使用 `calc_` 函数进行筛选的地方，改为 `IndicatorService.calculate()`。
  - **文件:** `core/signal/enhanced.py`
    - **操作:** 找到所有使用 `calc_` 函数生成信号的地方，改为 `IndicatorService.calculate()`。
  - **文件:** `analysis/enhanced_stock_analyzer.py`
    - **操作:** 移除对 `calculate_advanced_indicators` 的调用，改为循环调用 `IndicatorService.calculate()` 来获取所需的多个高级指标。
  - **验证:** 对以上每一个文件的修改，都要立刻运行 **Phase 0** 中对应的测试用例，确保新实现的计算结果与旧实现完全一致。

**阶段完成标志:** 所有业务代码中对旧指标模块的依赖全部移除，应用功能正常，且所有测试通过。

---

## 5. Phase 3: 清理与收尾 (Cleanup)

**目标:** 移除所有废弃的代码和文件，完成文档更新。

- [ ] **删除冗余文件**
  - **操作:** 在确认所有依赖都已移除后，从版本控制中安全删除以下文件：
    - `indicators_algo.py`
    - `features/basic_indicators.py`
    - `features/advanced_indicators.py`
    - `features/__init__.py` (如果该文件已无其他内容)
    - 如果 `features/` 目录已空，删除该目录。

- [ ] **代码审查**
  - **操作:** 对所有新建和修改的文件发起一次团队代码审查 (Code Review)，确保代码质量、风格统一和逻辑正确。

- [ ] **更新文档**
  - **文件:** `README.md`, `docs/developer.rst` (或其他开发者文档)
  - **操作:**
    1.  更新项目架构图和说明，反映新的指标系统。
    2.  添加关于如何添加新指标（修改 `initialize_indicators.py`）和通过插件扩展指标的开发者指南。

**阶段完成标志:** 项目代码库整洁，无废弃代码，文档与当前实现保持同步。

---

## 6. Phase 4: 插件系统实现 (Extension)

**目标:** 实现插件动态注册指标的功能。

- [ ] **完善 `PluginManager`**
  - **文件:** `core/plugin_manager.py`
  - **操作:**
    1.  在 `PluginManager` 加载插件的循环中，增加新的逻辑。
    2.  尝试从每个插件模块中 `import plugin_info`。
    3.  如果成功，检查是否存在 `register_indicators()` 函数。
    4.  如果存在，调用 `indicators_list = plugin.plugin_info.register_indicators()`。
    5.  获取 `IndicatorService` 实例。
    6.  创建 `IndicatorService.register_indicators(indicators_list: List[Dict], source: str)` 方法，该方法负责将插件提供的指标列表写入数据库。
    7.  在 `PluginManager` 中调用 `indicator_service.register_indicators(indicators_list, plugin_name)`。

- [ ] **创建示例插件**
  - **目录:** `plugins/examples/my_custom_indicator/`
  - **操作:** 创建一个完整的示例插件，包含 `plugin_info.py`，其中定义一个自定义指标（如 "情绪指标"），并提供其计算函数的实现，以作为未来插件开发的模板。

**阶段完成标志:** 插件可以成功地将其自定义的指标注册到系统中，并且这些指标可以立即在UI和策略中使用。

---

## 7. 实施进度跟踪

### 已完成部分

- **Phase 0: 准备工作**
  - ✅ 创建测试数据夹具：`test/fixtures/stock_data_100d.csv`, `test/fixtures/stock_data_500d.csv`
  - ✅ 编写测试用例：`test/test_indicators_system.py`, `test/test_new_indicator_system.py`

- **Phase 1: 基础设施构建**
  - ✅ 创建并初始化数据库：`db/indicators.db`, `db/initialize_indicators.py`
  - ✅ 创建统一指标算法库：`core/indicators/library/`下的各个模块
  - ✅ 开发核心服务：`core/indicator_service.py`
  - ✅ 开发指标适配器：`core/indicator_adapter.py`
  - ✅ 创建示例代码：`examples/indicator_system_demo.py`
  - ✅ 编写重构总结：`INDICATOR_REFACTOR_SUMMARY.md`

### 待完成部分

- **Phase 2: 增量替换与集成**
  - [ ] 重构UI层：更新`gui/widgets/analysis_widget.py`等文件
  - [ ] 重构核心逻辑层：更新`core/stock_screener.py`等文件

- **Phase 3: 清理与收尾**
  - [ ] 删除冗余文件：`indicators_algo.py`, `features/`目录下的文件
  - [ ] 代码审查
  - [ ] 更新文档

- **Phase 4: 插件系统实现**
  - [ ] 完善`PluginManager`：添加指标注册功能
  - [ ] 创建示例插件

### 下一步工作计划

1. 完成UI层的重构，将所有指标相关UI组件迁移到使用`IndicatorService`
2. 完成核心逻辑层的重构，将所有业务代码中的指标计算迁移到使用`IndicatorService`
3. 在确认所有依赖都已迁移后，清理旧代码
4. 实现插件系统的指标注册功能
5. 更新文档，反映新的指标系统架构 