# 资产类型UI展示指南

## 📋 概述

为了统一管理资产类型在UI中的显示名称，创建了 `UIAssetTypeUtils` 工具类。

## 🔧 核心功能

### 1. 中文显示名称映射

**支持的资产类型：**

| AssetType | 显示名称 | 说明 |
|-----------|---------|------|
| **股票类** |
| `STOCK` | 股票（通用） | 自动映射到美股 |
| `STOCK_US` | 美股 | 美国股票市场 |
| `STOCK_A` | A股 | 沪深A股 |
| `STOCK_B` | B股 | B股市场 |
| `STOCK_H` | H股 | H股市场 |
| `STOCK_HK` | 港股 | 香港股票市场 |
| **衍生品** |
| `FUTURES` | 期货 | 期货合约 |
| `OPTION` | 期权 | 期权合约 |
| `WARRANT` | 权证 | 权证 |
| **基金债券** |
| `FUND` | 基金 | 投资基金 |
| `BOND` | 债券 | 债券市场 |
| **指数** |
| `INDEX` | 指数 | 市场指数 |
| **板块** |
| `SECTOR` | 板块（通用） | 通用板块 |
| `INDUSTRY_SECTOR` | 行业板块 | 行业分类 |
| `CONCEPT_SECTOR` | 概念板块 | 概念主题 |
| `STYLE_SECTOR` | 风格板块 | 投资风格 |
| `THEME_SECTOR` | 主题板块 | 投资主题 |
| **其他** |
| `CRYPTO` | 加密货币 | 数字货币 |
| `FOREX` | 外汇 | 外汇市场 |
| `COMMODITY` | 商品 | 大宗商品 |
| `MACRO` | 宏观经济 | 宏观数据 |

### 2. 常用资产类型（用于下拉框）

**默认显示（8个）：**
1. A股
2. 美股
3. 港股
4. 期货
5. 基金
6. 债券
7. 指数
8. 加密货币

### 3. 分类分组

```python
GROUPED_TYPES = {
    "股票": [A股, 美股, 港股, B股, H股],
    "衍生品": [期货, 期权, 权证],
    "基金债券": [基金, 债券],
    "指数板块": [指数, 板块, 行业板块, 概念板块],
    "其他": [加密货币, 外汇, 商品]
}
```

## 💻 使用方法

### 方法1：在下拉框中使用（推荐）

```python
from core.ui_asset_type_utils import get_asset_type_combo_items

# 创建下拉框
asset_combo = QComboBox()

# 添加常用资产类型（8个）
asset_combo.addItems(get_asset_type_combo_items())

# 或添加所有资产类型（20+个）
asset_combo.addItems(get_asset_type_combo_items(include_all=True))
```

### 方法2：使用工具类

```python
from core.ui_asset_type_utils import UIAssetTypeUtils
from core.plugin_types import AssetType

# 获取显示名称
display_name = UIAssetTypeUtils.get_display_name(AssetType.STOCK_A)
# 返回: "A股"

# 从显示名称获取AssetType
asset_type = UIAssetTypeUtils.get_asset_type("A股")
# 返回: AssetType.STOCK_A

# 获取所有常用类型的显示名称
common_names = UIAssetTypeUtils.get_common_display_names()
# 返回: ["A股", "美股", "港股", "期货", "基金", "债券", "指数", "加密货币"]

# 获取按类别分组的显示名称
grouped = UIAssetTypeUtils.get_grouped_display_names()
# 返回: {"股票": ["A股", "美股", ...], "衍生品": [...], ...}
```

### 方法3：格式化显示

```python
from core.ui_asset_type_utils import UIAssetTypeUtils
from core.plugin_types import AssetType

# 简单显示
formatted = UIAssetTypeUtils.format_for_ui(AssetType.STOCK_A)
# 返回: "A股"

# 显示代码
formatted = UIAssetTypeUtils.format_for_ui(AssetType.STOCK_A, show_code=True)
# 返回: "A股 [stock_a]"
```

### 方法4：解析用户选择

```python
from core.ui_asset_type_utils import parse_asset_type_from_combo

# 用户在下拉框选择了"A股"
selected_text = asset_combo.currentText()  # "A股"

# 解析为 AssetType
asset_type = parse_asset_type_from_combo(selected_text)
# 返回: AssetType.STOCK_A

# 然后可以用于数据库路由
from core.asset_database_manager import AssetSeparatedDatabaseManager
manager = AssetSeparatedDatabaseManager()
db_path = manager.get_database_path(asset_type)
# 返回: "db/databases/stock_a/stock_a_data.duckdb"
```

## 🎨 UI展示效果

### 数据导入面板（已更新）

**位置**：`gui/widgets/enhanced_data_import_widget.py`

**更新前**：
```python
self.asset_type_combo.addItems(["股票", "期货", "基金", "债券", "指数"])
# 问题：
# 1. 硬编码，难以维护
# 2. "股票"太模糊（是A股还是美股？）
# 3. 缺少其他资产类型（港股、加密货币等）
```

**更新后**：
```python
from core.ui_asset_type_utils import get_asset_type_combo_items
self.asset_type_combo.addItems(get_asset_type_combo_items())
# 优势：
# 1. 集中管理，易于维护
# 2. 显示名称明确（A股、美股、港股等）
# 3. 支持所有常用资产类型（8个）
# 4. 可选显示所有类型（20+个）
```

**显示效果**：
```
📊 资产类型: [下拉框]
  ├── A股
  ├── 美股
  ├── 港股
  ├── 期货
  ├── 基金
  ├── 债券
  ├── 指数
  └── 加密货币
```

### 插件管理器（可选更新）

**位置**：`gui/dialogs/enhanced_plugin_manager_dialog.py`

可以使用相同的方式更新资产类型选择。

## 📝 最佳实践

### 1. 始终使用工具类

❌ **错误做法**：
```python
# 硬编码显示名称
combo.addItems(["股票", "期货", "基金"])

# 硬编码映射
if selected == "股票":
    asset_type = AssetType.STOCK
```

✅ **正确做法**：
```python
from core.ui_asset_type_utils import get_asset_type_combo_items, parse_asset_type_from_combo

# 使用工具类获取选项
combo.addItems(get_asset_type_combo_items())

# 使用工具类解析
selected = combo.currentText()
asset_type = parse_asset_type_from_combo(selected)
```

### 2. 明确资产类型

❌ **模糊命名**：
- "股票" → 到底是A股还是美股？

✅ **明确命名**：
- "A股" → 沪深A股
- "美股" → 美国股票市场
- "港股" → 香港股票市场

### 3. 支持扩展

使用 `get_asset_type_combo_items(include_all=True)` 可以在需要时展示所有资产类型，而不需要修改代码。

## 🔄 完整工作流程

```
用户界面 → UIAssetTypeUtils → AssetType → AssetSeparatedDatabaseManager → 数据库
   ↓              ↓               ↓                 ↓                          ↓
"A股"   → AssetType.STOCK_A → stock_a → db/databases/stock_a/ → stock_a_data.duckdb
```

**示例代码**：
```python
# 1. UI层：用户选择
selected_text = self.asset_type_combo.currentText()  # "A股"

# 2. 解析层：转换为 AssetType
asset_type = parse_asset_type_from_combo(selected_text)  # AssetType.STOCK_A

# 3. 数据库层：获取数据库路径
manager = AssetSeparatedDatabaseManager()
db_path = manager.get_database_path(asset_type)  # "db/databases/stock_a/stock_a_data.duckdb"

# 4. 数据层：读取或写入数据
with duckdb.connect(db_path) as conn:
    data = conn.execute("SELECT * FROM stock_a_kline").fetchall()
```

## ✅ 总结

### 优势

1. **统一管理**：所有显示名称集中在一个文件中
2. **易于维护**：修改一次，所有UI自动更新
3. **类型安全**：使用 `AssetType` Enum，避免字符串硬编码
4. **国际化友好**：可以轻松添加多语言支持
5. **可扩展性**：新增资产类型时，只需更新工具类

### 已更新的组件

- ✅ `gui/widgets/enhanced_data_import_widget.py`（2处）

### 建议更新的组件

- ⏳ `gui/dialogs/enhanced_plugin_manager_dialog.py`
- ⏳ 其他有资产类型选择的对话框/面板

---

**创建时间**：2025-10-14 01:00  
**文件位置**：`core/ui_asset_type_utils.py`  
**状态**：✅ 已实现并集成

