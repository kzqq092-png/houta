# 数据库管理后台 - DuckDB完整功能支持

## 概述
实现了DatabaseAdminDialog对DuckDB的完整CRUD支持，使其与SQLite功能对等。

## 核心实现

### 1. 可编辑DuckDB表模型
创建了完整的`DuckDBTableModel`类，继承自`QAbstractTableModel`：

**核心特性**：
- **数据结构**：使用可修改的列表存储数据
- **变更追踪**：
  - `_modified_cells`: 记录修改的单元格 {(row, col): value}
  - `_new_rows`: 记录新增的行索引
  - `_deleted_rows`: 记录待删除的行数据
- **可编辑标志**：实现`flags()`返回可编辑标志
- **背景颜色**：修改的单元格显示浅黄色，新增行显示浅绿色

### 2. CRUD操作实现

#### 插入行 (insertRow)
```python
- 创建空行，所有列初始化为None
- 添加到_new_rows列表追踪
- 触发beginInsertRows/endInsertRows信号
```

#### 删除行 (removeRow)
```python
- 从数据中移除行
- 如果不是新增行，加入_deleted_rows
- 更新_modified_cells中的行号
- 触发beginRemoveRows/endRemoveRows信号
```

#### 更新数据 (setData)
```python
- 直接修改内存中的数据
- 记录到_modified_cells
- 触发dataChanged信号
```

#### 提交更改 (submitAll)
执行顺序：
1. **DELETE**: 删除_deleted_rows中的行（使用所有列匹配）
2. **UPDATE**: 更新_modified_cells中的行（SET修改的列，WHERE未修改的列）
3. **INSERT**: 插入_new_rows中的新行
4. 清空所有追踪记录

### 3. SQL生成策略

**DELETE语句**：
```sql
DELETE FROM table WHERE col1 = ? AND col2 IS NULL AND col3 = ?
```
使用所有列作为WHERE条件，NULL值使用IS NULL

**UPDATE语句**：
```sql
UPDATE table SET modified_col1 = ?, modified_col2 = ? 
WHERE unmodified_col1 = ? AND unmodified_col2 = ?
```
SET子句包含修改的列，WHERE子句包含未修改的列

**INSERT语句**：
```sql
INSERT INTO table (col1, col2, col3) VALUES (?, ?, ?)
```

### 4. 统一的接口

所有编辑功能现在支持两种数据库：
- `add_row()`: 新增行
- `del_row()`: 删除行  
- `save_changes()`: 保存更改
- `import_csv()`: 导入CSV
- `export_csv()`: 导出CSV
- `show_batch_modify()`: 批量修改
- `toggle_edit_mode()`: 编辑模式切换（DuckDB提示手动提交）

### 5. 表管理功能

**SQLite**: 完整功能（新增字段、删除表、编辑注释等）
**DuckDB**: 表结构查看 + 删除表操作

## 使用流程

### DuckDB数据编辑
1. 选择DuckDB数据库并连接
2. 选择表，数据加载到可编辑模型
3. 直接在表格中编辑、新增、删除行
4. 点击"保存修改"按钮提交到数据库
5. 修改的单元格显示黄色，新增行显示绿色

### 批量操作
1. 支持导入CSV到DuckDB表
2. 支持批量修改字段值
3. 支持查找替换
4. 所有操作需要手动保存

## 技术要点

### 变更追踪机制
- 内存中维护原始数据副本
- 所有修改先缓存在追踪结构中
- submitAll时批量生成SQL并执行

### 错误处理
- 每个操作都有try-except包装
- 详细的logger日志记录
- 用户友好的错误提示

### 兼容性设计
- 使用isinstance检查模型类型
- 统一的接口，透明的后端切换
- SQLite模型和DuckDB模型共用相同的UI逻辑

## 文件位置
`gui/dialogs/database_admin_dialog.py`
- DuckDBTableModel类：第1797-2001行
- CRUD方法：第801-891行
