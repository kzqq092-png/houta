## 问题
在改进的插件查找代码中，调用 `getattr(plugin_info, 'name', '').lower()` 时出现 `'NoneType' object has no attribute 'lower'` 错误。这是因为 `getattr()` 返回的默认值是空字符串 ''，但当属性存在且值为 None 时，返回的是 None 而不是默认值。

## 根本原因
`getattr(obj, attr, default)` 仅在属性不存在时返回默认值。当属性存在但值为 None 时，会返回 None。

## 解决方案
在调用 `.lower()` 之前，先检查值是否为 None：
```python
# 错误做法
plugin_name = getattr(plugin_info, 'name', '').lower()  # 如果 name 属性是 None，会失败

# 正确做法
plugin_name_raw = getattr(plugin_info, 'name', '')
plugin_name = (plugin_name_raw.lower() if plugin_name_raw else '')
```

## 修改位置
core/services/uni_plugin_data_manager.py 第460-475行

## 影响
这个修复确保插件名称匹配逻辑在处理 None 值时不会崩溃，使代码更加健壮。