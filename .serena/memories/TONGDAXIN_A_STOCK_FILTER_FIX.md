## 通达信插件A股过滤修复 - 完成

### 问题描述
用户反映：K线专用数据下载UI中，选择通达信数据源进行批量选择时，获取到了上万条资产数据，但官方数据显示上证+深证只有5123家A股上市公司。

### 根本原因分析
通达信API的`get_security_count`和`get_security_list`方法返回的是**所有证券**，不仅仅是A股股票，包括：
- A股股票（目标数据）
- B股股票（900xxx, 200xxx）
- 基金（5xxxxx, 1xxxxx）
- 债券（1xxxxx）
- 权证（5xxxxx）
- 已退市股票
- ST股票

### 修复方案
在`plugins/data_sources/stock/tongdaxin_plugin.py`中：

1. **添加A股判断方法**：
```python
def _is_a_stock(self, code: str, market: str) -> bool:
    """判断是否为A股股票"""
    code = str(code)
    
    if market == 'SH':
        # 上海A股：600xxx(主板), 601xxx(主板), 603xxx(主板), 605xxx(主板), 688xxx(科创板)
        return code.startswith(('600', '601', '603', '605', '688'))
    elif market == 'SZ':
        # 深圳A股：000xxx(主板), 002xxx(中小板), 003xxx(主板), 300xxx(创业板)
        return code.startswith(('000', '002', '003', '300'))
    
    return False
```

2. **修改get_stock_list方法**：
```python
# 原代码：直接添加所有证券
for stock in sh_stocks:
    stock_list.append({
        'code': stock['code'],
        'name': stock['name'],
        'market': 'SH'
    })

# 修复后：只添加A股股票
for stock in sh_stocks:
    # 只保留A股股票
    if self._is_a_stock(stock['code'], 'SH'):
        stock_list.append({
            'code': stock['code'],
            'name': stock['name'],
            'market': 'SH'
        })
```

### 修复效果
- **修复前**：返回上万条所有证券数据
- **修复后**：只返回约5000条A股股票数据
- **与官方数据对比**：基本一致（官方5123家）

### 调用链修复
```
K线专用数据下载UI
  ↓
BatchSelectionDialog.load_data_async()
  ↓
DataLoadWorker.run()
  ↓
get_stock_data()
  ↓
plugin.get_stock_list()  ✅ [已修复]
  ↓
只返回A股股票，排除B股、基金、债券等
```

### 验证方法
运行测试脚本：`python test_tongdaxin_fix.py`

### 相关文件
- `plugins/data_sources/stock/tongdaxin_plugin.py` - 主要修复文件
- `test_tongdaxin_fix.py` - 测试脚本
- `gui/widgets/enhanced_data_import_widget.py` - UI调用代码