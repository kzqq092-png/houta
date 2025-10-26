# `{"result": "error"}` JSON输出捕获解决方案

## 🎯 问题定位

用户确认JSON输出出现在 `core/services/unified_data_manager.py` 的 **740-761行范围内**。

根据日志时间线：
```
14:54:13.260 | INFO | get_asset_list:744 - 从DuckDB数据库获取stock资产列表
           ↓ (0ms)
           {"result": "error"}  ← 神秘输出
           ↓ (3ms)
14:54:13.263 | INFO | _get_asset_list_from_duckdb:850 - DuckDB中没有stock资产列表数据
```

**结论**: JSON输出发生在 `_get_asset_list_from_duckdb` 方法内部，具体在调用 `query_data` 期间。

## 🔧 实施的解决方案

### 方案：输出捕获

在 `unified_data_manager.py:838-871` 添加了输出捕获代码：

```python
# 执行查询 - 使用query_data方法
import sys
import io

# 捕获所有输出
old_stdout = sys.stdout
old_stderr = sys.stderr
captured_stdout = io.StringIO()
captured_stderr = io.StringIO()

try:
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr
    
    result = self.duckdb_operations.query_data(
        database_path=self.asset_manager.get_database_path(asset_type_enum),
        table_name=table_name,
        custom_sql=query
    )
finally:
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    
    # 检查是否有输出
    stdout_content = captured_stdout.getvalue()
    stderr_content = captured_stderr.getvalue()
    
    if stdout_content:
        logger.warning(f"[CAPTURED STDOUT] query_data produced stdout output: {stdout_content!r}")
    if stderr_content:
        logger.warning(f"[CAPTURED STDERR] query_data produced stderr output: {stderr_content!r}")
```

### 工作原理

1. **捕获阶段**
   - 临时替换 `sys.stdout` 和 `sys.stderr`
   - 将所有输出重定向到 `StringIO` 缓冲区

2. **执行阶段**
   - 正常调用 `query_data` 方法
   - 任何 `print()` 语句的输出都会被捕获

3. **报告阶段**
   - 恢复原始的 stdout/stderr
   - 如果捕获到任何输出，通过logger报告
   - 输出内容会包含完整的原始文本

## 📊 预期结果

### 场景1: 如果JSON来自query_data内部

重新运行应用后，日志会显示：

```
14:54:13.260 | INFO | get_asset_list:744 - 从DuckDB数据库获取stock资产列表
14:54:13.262 | WARNING | _get_asset_list_from_duckdb:866 - [CAPTURED STDOUT] query_data produced stdout output: '{\n    "result": "error"\n}\n'
14:54:13.263 | INFO | _get_asset_list_from_duckdb:850 - DuckDB中没有stock资产列表数据
```

这将**确认输出来源**并**阻止其显示在控制台**。

### 场景2: 如果JSON来自其他地方

如果捕获不到任何输出，说明JSON来自：
- `query_data` 方法之外的其他地方
- 多线程/异步任务
- C扩展模块（绕过Python的stdout）

## 🎯 下一步行动

### 立即测试

1. **重启应用**
   ```bash
   python main.py
   ```

2. **观察日志**
   - 查找 `[CAPTURED STDOUT]` 或 `[CAPTURED STDERR]` 消息
   - 检查是否还能看到原始的 `{"result": "error"}` 输出

3. **报告结果**
   - 如果看到捕获消息 → 成功定位！
   - 如果仍然看到JSON但没有捕获消息 → 需要扩大捕获范围

### 如果捕获成功

找到来源后，可以：

1. **定位具体代码**
   - 在 `query_data` 方法中搜索print语句
   - 或在其调用的方法中搜索

2. **移除或修复**
   - 删除调试print语句
   - 或将其改为logger输出

3. **清理捕获代码**
   - 问题解决后，可以移除捕获代码
   - 或保留作为调试工具

### 如果捕获失败

扩大捕获范围：

```python
# 在更早的位置开始捕获
# 例如在746行之前：
old_stdout = sys.stdout
sys.stdout = io.StringIO()

try:
    asset_list_df = self._get_asset_list_from_duckdb(asset_type, market)
finally:
    captured = sys.stdout.getvalue()
    sys.stdout = old_stdout
    if captured:
        logger.warning(f"[CAPTURED] {captured!r}")
```

## 📝 技术说明

### 为什么这个方法有效

1. **Python的print()函数**
   - 默认输出到 `sys.stdout`
   - 可以通过替换 `sys.stdout` 来捕获

2. **StringIO作为缓冲区**
   - 在内存中模拟文件对象
   - 可以捕获所有写入的内容

3. **try-finally保证恢复**
   - 即使发生异常，也会恢复stdout
   - 避免影响后续代码

### 限制

这个方法**无法捕获**：
- C扩展模块直接写入文件描述符的输出
- 多线程中其他线程的输出（如果没有GIL保护）
- 子进程的输出

但对于Python代码中的 `print()` 语句，这个方法是100%有效的。

## 🎉 总结

### 已完成

- ✅ 精确定位问题范围（740-761行）
- ✅ 添加输出捕获代码
- ✅ 提供调试和修复方案

### 待验证

- ⏳ 重启应用测试捕获效果
- ⏳ 确认JSON输出来源
- ⏳ 移除或修复源头代码

### 预期结果

- 🎯 **最佳情况**: 捕获到输出，定位到具体的print语句，移除它
- ⚠️ **次佳情况**: 捕获到输出但来自第三方库，添加过滤器
- 🔍 **需要进一步调查**: 未捕获到输出，说明来自更底层

---

**修改文件**: `core/services/unified_data_manager.py`  
**修改行数**: 838-871  
**修改类型**: 添加调试代码（临时）  
**下一步**: 重启应用并观察日志

**报告生成时间**: 2025-10-18 15:05

