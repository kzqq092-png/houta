## 批量选择对话框 - 导入和数据获取修复

### 问题
`ImportError: cannot import name 'get_unified_data_manager' from 'core.services.uni_plugin_data_manager'`

### 根本原因
1. 函数 `get_unified_data_manager()` 不在 `uni_plugin_data_manager.py` 中
2. 而是在 `unified_data_manager.py` 中，但通常应该通过服务容器获取

### 正确的获取方式

#### 方法1：从服务容器获取（推荐在 UI 运行时）
```python
from core.containers import get_service_container
container = get_service_container()
data_manager = container.get('UnifiedDataManager')
```

#### 方法2：直接实例化（备选方案）
```python
from core.services.unified_data_manager import UnifiedDataManager
data_manager = UnifiedDataManager()
```

### 完整实现
```python
def load_asset_list_from_plugins(self):
    """从插件获取真实资产列表"""
    try:
        # 优先使用容器方式
        from core.containers import get_service_container
        container = get_service_container()
        data_manager = container.get('UnifiedDataManager') if container else None
        
        # 备选：直接实例化
        if not data_manager:
            from core.services.unified_data_manager import UnifiedDataManager
            data_manager = UnifiedDataManager()
        
        # 根据资产类型获取列表
        if self.asset_type == "股票":
            result = data_manager.get_asset_list(asset_type='stock', market='all')
        # ... 其他类型
        
        # 处理 DataFrame 返回值
        import pandas as pd
        if isinstance(result, pd.DataFrame):
            items = []
            for _, row in result.iterrows():
                code = row.get('code', '') if hasattr(row, 'get') else row['code']
                name = row.get('name', '') if hasattr(row, 'get') else row['name']
                items.append({
                    "code": code,
                    "name": name,
                    "category": row.get('industry', '其他')
                })
            return items
        
        return []
```

### 关键点
1. ✅ 先尝试从容器获取（运行时的标准做法）
2. ✅ 如果失败，直接实例化（开发/测试时的备选）
3. ✅ 正确处理 DataFrame 返回值（通过 iterrows() 遍历）
4. ✅ 处理 pandas Series 对象的属性访问
5. ✅ 添加详细的日志和错误处理