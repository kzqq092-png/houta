# K线专业数据导入UI修复计划

**日期**: 2025-10-19  
**问题来源**: 用户反馈  
**状态**: 📋 待修复

---

## 问题描述

### 问题1: 数据源配置只有4个 ⚠️
**现象**: 数据源下拉列表只显示4个硬编码选项  
**期望**: 显示所有已注册的可用数据源插件

### 问题2: 资产数据无法获取 ❌
**现象**: 选择数据源后，批量/快速选择UI中没有真实资产数据  
**期望**: 显示对应数据源的真实资产列表，无mock数据

---

## 根本原因分析

### 问题1分析

**硬编码位置**: `gui/widgets/enhanced_data_import_widget.py`
- 第937行（主UI）
- 第1176行（配置tab）
- 第1327行（数据源tab）

**硬编码内容**:
```python
self.data_source_combo.addItems(["通达信", "东方财富", "新浪财经", "腾讯财经"])
```

**问题**:
1. 使用中文名称，与插件注册名不匹配
2. 无法动态获取已注册插件
3. 新增插件需要手动修改UI代码

---

### 问题2分析

**资产获取逻辑**: 第211-299行 `get_stock_data()` 方法

**代码结构**:
```python
def get_stock_data(self):
    try:
        # 方案1: 统一插件数据管理器
        uni_manager = get_uni_plugin_data_manager()
        if uni_manager:
            stock_list_data = uni_manager.get_stock_list()
            if stock_list_data:
                return stock_list_data
        
        # 方案2: 原有统一数据管理器
        data_manager = get_unified_data_manager()
        if data_manager:
            stock_df = data_manager.get_stock_list()
            if not stock_df.empty:
                return [convert to list]
        
        # 方案3: 股票服务
        stock_service = container.resolve(StockService)
        if stock_service:
            return stock_service.get_stock_list()
        
        # 失败
        return []
    except Exception as e:
        return []
```

**问题**:
1. 没有根据用户选择的数据源获取数据
2. 3层备用方案都可能因初始化失败而返回空
3. 异常被捕获但没有详细日志

---

## 修复方案

### 修复方案1: 动态加载数据源

#### Step 1: 添加辅助方法
```python
def _load_available_data_sources(self):
    """动态加载可用的数据源插件"""
    try:
        from core.plugin_manager import PluginManager
        from core.containers import get_service_container
        
        # 获取插件管理器
        container = get_service_container()
        plugin_manager = container.get('plugin_manager') if container else None
        
        if not plugin_manager:
            # 尝试全局实例
            plugin_manager = PluginManager.get_instance()
        
        if plugin_manager:
            # 获取所有数据源插件
            data_source_plugins = []
            
            for plugin_name, plugin_info in plugin_manager.plugins.items():
                # 筛选数据源插件
                if 'data_sources' in plugin_name:
                    display_name = plugin_info.get('display_name', plugin_name)
                    data_source_plugins.append({
                        'name': plugin_name,
                        'display_name': display_name
                    })
            
            # 填充下拉列表
            self.data_source_combo.clear()
            self.data_source_mapping = {}  # 映射：display_name -> plugin_name
            
            for plugin in data_source_plugins:
                self.data_source_combo.addItem(plugin['display_name'])
                self.data_source_mapping[plugin['display_name']] = plugin['name']
            
            logger.info(f"成功加载 {len(data_source_plugins)} 个数据源插件")
            return True
        
        # 备用方案：使用默认列表
        logger.warning("无法获取插件管理器，使用默认数据源列表")
        self._load_default_data_sources()
        return False
        
    except Exception as e:
        logger.error(f"加载数据源失败: {e}")
        self._load_default_data_sources()
        return False

def _load_default_data_sources(self):
    """加载默认数据源列表（备用）"""
    default_sources = {
        "AKShare": "data_sources.akshare_plugin",
        "东方财富": "data_sources.eastmoney_plugin",
        "新浪财经": "data_sources.sina_plugin",
        "通达信": "data_sources.tongdaxin_plugin"
    }
    
    self.data_source_combo.clear()
    self.data_source_mapping = default_sources
    
    for display_name in default_sources.keys():
        self.data_source_combo.addItem(display_name)
```

#### Step 2: 替换所有硬编码
```python
# 原代码（3处）
self.data_source_combo = QComboBox()
self.data_source_combo.addItems(["通达信", "东方财富", "新浪财经", "腾讯财经"])

# 新代码
self.data_source_combo = QComboBox()
self._load_available_data_sources()
```

---

### 修复方案2: 根据数据源获取资产

#### Step 1: 修改 get_stock_data 方法
```python
def get_stock_data(self):
    """获取股票数据 - 根据用户选择的数据源"""
    try:
        # 获取用户选择的数据源
        selected_display_name = self.parent().data_source_combo.currentText()
        selected_plugin_name = self.parent().data_source_mapping.get(selected_display_name)
        
        logger.info(f"使用数据源: {selected_display_name} ({selected_plugin_name})")
        
        # 方案1: 通过UnifiedDataManager获取
        from core.services.unified_data_manager import get_unified_data_manager
        
        data_manager = get_unified_data_manager()
        if data_manager:
            # 获取资产列表（从DuckDB或数据源）
            asset_df = data_manager.get_asset_list(asset_type='stock', market='all')
            
            if not asset_df.empty:
                stock_list = []
                for _, row in asset_df.iterrows():
                    stock_info = {
                        "code": row.get('code', ''),
                        "name": row.get('name', ''),
                        "category": row.get('industry', '其他')
                    }
                    stock_list.append(stock_info)
                
                logger.info(f"成功获取股票数据: {len(stock_list)} 只股票")
                return stock_list
            else:
                logger.warning("获取的股票DataFrame为空")
        
        # 方案2: 直接通过插件获取
        if selected_plugin_name:
            from core.plugin_manager import PluginManager
            
            plugin_manager = PluginManager.get_instance()
            if plugin_manager:
                plugin = plugin_manager.get_plugin(selected_plugin_name)
                if plugin and hasattr(plugin, 'get_stock_list'):
                    stock_list_data = plugin.get_stock_list()
                    if stock_list_data:
                        logger.info(f"直接从插件获取股票数据: {len(stock_list_data)} 只")
                        return stock_list_data
        
        # 失败
        logger.error("所有方案都无法获取股票数据")
        QMessageBox.warning(
            self,
            "数据获取失败",
            f"无法从数据源 '{selected_display_name}' 获取股票列表。\n"
            "请检查:\n"
            "1. 数据源插件是否正确注册\n"
            "2. DuckDB数据库是否已初始化\n"
            "3. 网络连接是否正常"
        )
        return []
        
    except Exception as e:
        logger.error(f"获取股票数据失败: {e}", exc_info=True)
        QMessageBox.critical(self, "错误", f"获取股票数据时发生错误:\n{str(e)}")
        return []
```

#### Step 2: 添加调试日志
```python
def load_data(self):
    """加载数据"""
    try:
        logger.info(f"开始加载 {self.asset_type} 数据")
        
        # 根据资产类型加载不同的数据
        if self.asset_type == "股票":
            self.all_items = self.get_stock_data()
        elif self.asset_type == "指数":
            self.all_items = self.get_index_data()
        # ... 其他资产类型
        
        logger.info(f"成功加载 {len(self.all_items)} 条数据")
        
        if not self.all_items:
            QMessageBox.warning(
                self,
                "数据为空",
                f"未能获取到 {self.asset_type} 数据。\n"
                "请检查数据源配置或数据库状态。"
            )
        
        self.populate_table(self.all_items)
        
    except Exception as e:
        logger.error(f"加载{self.asset_type}数据失败: {e}", exc_info=True)
        QMessageBox.critical(self, "错误", f"加载数据失败:\n{str(e)}")
        self.all_items = []
```

---

## 实施步骤

### Phase 1: 数据源动态加载
1. 在 `EnhancedDataImportWidget` 类中添加 `_load_available_data_sources()` 方法
2. 在 `EnhancedDataImportWidget` 类中添加 `_load_default_data_sources()` 方法
3. 添加 `self.data_source_mapping = {}` 属性
4. 替换所有硬编码的数据源列表（3处）
5. 测试数据源下拉列表

### Phase 2: 资产数据真实获取
1. 修改 `BatchSelectionDialog.get_stock_data()` 方法
2. 修改 `BatchSelectionDialog.load_data()` 方法
3. 添加详细的错误提示和日志
4. 测试资产列表获取

### Phase 3: 验证测试
1. 启动系统
2. 打开K线数据导入UI
3. 检查数据源下拉列表（应显示所有已注册插件）
4. 选择不同数据源
5. 点击"批量选择"按钮
6. 验证显示真实的资产列表
7. 测试下载功能

---

## 修改文件清单

### 主要修改
- `gui/widgets/enhanced_data_import_widget.py`
  - 添加 `_load_available_data_sources()` 方法（约30行）
  - 添加 `_load_default_data_sources()` 方法（约15行）
  - 修改 `get_stock_data()` 方法（约50行）
  - 修改 `load_data()` 方法（约10行）
  - 替换硬编码数据源（3处）

### 预计工作量
- 代码修改: 约100行
- 测试验证: 30分钟
- 总计: 1-1.5小时

---

## 风险评估

### 低风险 ✅
- 添加新方法不影响现有功能
- 保留备用方案确保兼容性
- 详细的错误处理和日志

### 需要注意
1. 插件名称映射正确性
2. 不同数据源返回格式一致性
3. 异常处理的完整性

---

## 测试计划

### 单元测试
```python
def test_load_data_sources():
    """测试数据源加载"""
    widget = EnhancedDataImportWidget()
    widget._load_available_data_sources()
    
    assert widget.data_source_combo.count() > 0
    assert len(widget.data_source_mapping) > 0

def test_get_stock_data():
    """测试股票数据获取"""
    dialog = BatchSelectionDialog("股票")
    stock_data = dialog.get_stock_data()
    
    assert isinstance(stock_data, list)
    assert len(stock_data) > 0
    assert 'code' in stock_data[0]
    assert 'name' in stock_data[0]
```

### 集成测试
1. 系统启动测试
2. UI交互测试
3. 数据获取测试
4. 下载功能测试

---

## 后续优化

1. **缓存机制**: 缓存资产列表，避免重复获取
2. **异步加载**: 使用QThread避免UI卡顿
3. **进度显示**: 显示数据加载进度
4. **数据刷新**: 添加手动刷新按钮

---

**状态**: 📋 待下次会话实施

**预计时间**: 1-1.5小时

