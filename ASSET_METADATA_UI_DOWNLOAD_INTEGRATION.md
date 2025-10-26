# 资产元数据分离 - UI下载流程集成方案

**日期**: 2025-10-18  
**目标**: 实现UI下载流程中资产列表与详细数据的分离存储，支持数据源切换，通过TET框架标准化  
**状态**: 完整实施方案

---

## 📋 目录

1. [用户需求分析](#用户需求分析)
2. [现有流程分析](#现有流程分析)
3. [新架构设计](#新架构设计)
4. [UI交互流程](#ui交互流程)
5. [TET框架集成](#tet框架集成)
6. [数据源切换兼容](#数据源切换兼容)
7. [实施代码](#实施代码)

---

## 用户需求分析

### 核心需求

1. **资产列表获取**: UI调用数据源插件的 `get_asset_list()` 获取最新真实资产列表
2. **用户选择**: 用户在UI中选择要下载的资产
3. **分离存储**:
   - 资产元数据 → `asset_metadata` 表
   - 资产详细数据(K线) → `historical_kline_data` 表
4. **TET标准化**: 所有数据经过TET框架标准化后再存储
5. **数据源切换**: 切换数据源不影响表结构，数据可追溯来源

### 用户场景

```
用户视角：下载某些股票的历史数据

Step 1: 选择数据源
  └─ UI展示可用数据源：东方财富、新浪、AKShare、通达信...

Step 2: 获取资产列表
  └─ 点击"获取资产列表"
  └─ 后台调用插件API获取最新列表
  └─ UI展示：代码、名称、市场、行业等信息

Step 3: 选择资产
  └─ 勾选要下载的资产
  └─ 或输入代码/名称搜索

Step 4: 设置参数
  └─ 开始日期、结束日期
  └─ 数据类型（日K、周K、分钟K...）
  └─ 下载选项（覆盖/追加、验证等）

Step 5: 开始下载
  └─ 后台并发下载
  └─ 实时显示进度
  └─ 自动保存到数据库

结果：
✅ asset_metadata 表存储了资产元数据
✅ historical_kline_data 表存储了K线数据
✅ 两表通过 symbol 关联
✅ 数据源信息可追溯
```

---

## 现有流程分析

### 当前数据导入流程

```
UI (HistoryDataDialog / DataImportWizardDialog)
  ↓ 用户配置任务
DataImportExecutionEngine
  ↓ 创建任务
_import_kline_data()
  ├─ 获取插件
  ├─ 并发下载数据
  └─ _batch_save_kdata_to_database()
      ↓
AssetSeparatedDatabaseManager
  ├─ 路由到对应资产数据库
  └─ 直接插入 historical_kline_data 表
```

**问题**:
- ❌ 没有单独保存资产元数据
- ❌ K线表中嵌入元数据字段（冗余）
- ❌ 没有资产列表获取和选择的专门流程

---

## 新架构设计

### 完整数据流

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: UI - 数据源选择与资产列表获取                         │
├─────────────────────────────────────────────────────────────┤
│  HistoryDataDialog / EnhancedDataImportWidget               │
│    ├─ 用户选择数据源（下拉框）                               │
│    ├─ 点击"获取资产列表"按钮                                 │
│    └─ 调用: get_asset_list_from_plugin(data_source, ...)    │
│                                                              │
│  get_asset_list_from_plugin()                               │
│    ├─ 从 PluginManager 获取插件实例                         │
│    ├─ 调用 plugin.get_asset_list()                          │
│    └─ 返回: DataFrame[symbol, name, market, industry, ...]  │
│                                                              │
│  UI 展示资产列表（表格）                                     │
│    ├─ 复选框选择资产                                         │
│    ├─ 搜索/过滤功能                                          │
│    └─ 用户选择要下载的资产                                   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 保存资产元数据到 asset_metadata 表                   │
├─────────────────────────────────────────────────────────────┤
│  save_asset_metadata_to_db()                                │
│    ├─ 输入: selected_assets (用户选择的资产列表)            │
│    ├─ TET框架标准化                                          │
│    │   └─ transform_asset_list_data(raw_data)               │
│    ├─ 路由到对应资产数据库                                   │
│    └─ UPSERT INTO asset_metadata (...)                      │
│        └─ 记录数据源、更新时间等                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 下载并保存K线数据                                    │
├─────────────────────────────────────────────────────────────┤
│  DataImportExecutionEngine._import_kline_data()             │
│    ├─ 并发下载: plugin.get_kdata(symbol, ...)               │
│    ├─ TET框架标准化                                          │
│    │   └─ transform_kline_data(raw_data)                    │
│    │       └─ 从 asset_metadata 补全元数据（可选）           │
│    └─ _batch_save_kdata_to_database()                       │
│        └─ INSERT INTO historical_kline_data (...)           │
│            └─ 不再存储 name/market（已在metadata表）         │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 数据验证与完整性检查                                 │
├─────────────────────────────────────────────────────────────┤
│  validate_imported_data()                                   │
│    ├─ 检查 asset_metadata 是否有记录                        │
│    ├─ 检查 historical_kline_data 是否有记录                 │
│    ├─ 验证数据完整性（缺失值、异常值）                       │
│    └─ 记录到 data_quality_monitor 表                        │
└─────────────────────────────────────────────────────────────┘
```

### 数据库结构

```sql
-- 1. asset_metadata 表（每个资产一条记录）
stock_a_data.duckdb
├── asset_metadata
│   ├── symbol: "000001.SZ"
│   ├── name: "平安银行"
│   ├── market: "SZ"
│   ├── industry: "银行"
│   ├── sector: "金融"
│   ├── data_sources: ["eastmoney", "sina", "akshare"]  -- JSON字段
│   ├── primary_data_source: "eastmoney"
│   └── last_verified: 2025-10-18 10:00:00

-- 2. historical_kline_data 表（每个资产多条记录）
├── historical_kline_data
│   ├── symbol: "000001.SZ"
│   ├── data_source: "eastmoney"
│   ├── timestamp: 2025-10-18
│   ├── open: 10.23
│   ├── high: 10.50
│   ├── low: 10.10
│   ├── close: 10.45
│   ├── volume: 1000000
│   └── (不再有 name, market 字段)
```

---

## UI交互流程

### 1. 资产列表获取页面

#### UI组件设计

```python
class AssetListDownloadWidget(QWidget):
    """资产列表下载和选择组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugin_manager = None
        self.selected_assets = []
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # === 1. 数据源选择区域 ===
        source_group = QGroupBox("数据源设置")
        source_layout = QHBoxLayout(source_group)
        
        source_layout.addWidget(QLabel("数据源:"))
        self.source_combo = QComboBox()
        # 动态加载可用数据源
        self._load_available_data_sources()
        source_layout.addWidget(self.source_combo)
        
        self.refresh_button = QPushButton("🔄 获取资产列表")
        self.refresh_button.clicked.connect(self.fetch_asset_list)
        source_layout.addWidget(self.refresh_button)
        
        self.save_metadata_button = QPushButton("💾 保存元数据")
        self.save_metadata_button.clicked.connect(self.save_asset_metadata)
        self.save_metadata_button.setEnabled(False)
        source_layout.addWidget(self.save_metadata_button)
        
        source_layout.addStretch()
        layout.addWidget(source_group)
        
        # === 2. 搜索和过滤区域 ===
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入代码或名称搜索...")
        self.search_edit.textChanged.connect(self.filter_assets)
        filter_layout.addWidget(self.search_edit)
        
        filter_layout.addWidget(QLabel("市场:"))
        self.market_combo = QComboBox()
        self.market_combo.addItems(["全部", "SH", "SZ", "BJ"])
        self.market_combo.currentTextChanged.connect(self.filter_assets)
        filter_layout.addWidget(self.market_combo)
        
        filter_layout.addWidget(QLabel("行业:"))
        self.industry_combo = QComboBox()
        self.industry_combo.addItem("全部")
        self.industry_combo.currentTextChanged.connect(self.filter_assets)
        filter_layout.addWidget(self.industry_combo)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # === 3. 资产列表表格 ===
        self.asset_table = QTableWidget()
        self.asset_table.setColumnCount(7)
        self.asset_table.setHorizontalHeaderLabels([
            "选择", "代码", "名称", "市场", "行业", "板块", "状态"
        ])
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setAlternatingRowColors(True)
        self.asset_table.setSortingEnabled(True)
        layout.addWidget(self.asset_table)
        
        # === 4. 统计信息 ===
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("总数: 0 | 已选: 0")
        stats_layout.addWidget(self.stats_label)
        
        select_all_button = QPushButton("全选")
        select_all_button.clicked.connect(self.select_all_assets)
        stats_layout.addWidget(select_all_button)
        
        deselect_all_button = QPushButton("取消全选")
        deselect_all_button.clicked.connect(self.deselect_all_assets)
        stats_layout.addWidget(deselect_all_button)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
```

#### 资产列表获取逻辑

```python
def fetch_asset_list(self):
    """从数据源获取资产列表"""
    try:
        # 显示加载状态
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("⏳ 获取中...")
        QApplication.processEvents()
        
        # 获取选择的数据源
        data_source = self.source_combo.currentText()
        
        # 从插件管理器获取插件
        from core.plugin_manager import PluginManager
        plugin_manager = PluginManager.get_instance()
        
        # 获取对应的插件
        plugin_id = self._map_source_to_plugin_id(data_source)
        plugin = plugin_manager.get_plugin_instance(plugin_id)
        
        if not plugin:
            QMessageBox.warning(self, "错误", f"未找到数据源插件: {data_source}")
            return
        
        logger.info(f"🔄 从插件获取资产列表: {data_source}")
        
        # 调用插件的 get_asset_list 方法
        asset_list = plugin.get_asset_list(
            asset_type=AssetType.STOCK_A,
            market=None  # 获取所有市场
        )
        
        if not asset_list:
            QMessageBox.information(self, "提示", "未获取到资产列表")
            return
        
        # 转换为 DataFrame
        if isinstance(asset_list, list):
            import pandas as pd
            asset_df = pd.DataFrame(asset_list)
        else:
            asset_df = asset_list
        
        logger.info(f"✅ 获取到 {len(asset_df)} 个资产")
        
        # 存储原始数据
        self.raw_asset_data = asset_df
        self.current_data_source = data_source
        
        # 更新UI
        self._populate_asset_table(asset_df)
        self._update_filter_options(asset_df)
        self._update_stats()
        
        # 启用保存按钮
        self.save_metadata_button.setEnabled(True)
        
        QMessageBox.information(
            self, 
            "成功", 
            f"成功获取 {len(asset_df)} 个资产的元数据\n\n"
            f"请选择要下载的资产，然后点击'保存元数据'"
        )
        
    except Exception as e:
        logger.error(f"获取资产列表失败: {e}")
        QMessageBox.critical(self, "错误", f"获取资产列表失败:\n{str(e)}")
        
    finally:
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("🔄 获取资产列表")

def _map_source_to_plugin_id(self, source_name: str) -> str:
    """映射数据源名称到插件ID"""
    mapping = {
        "东方财富": "data_sources.stock.eastmoney_plugin",
        "新浪财经": "data_sources.stock.sina_plugin",
        "AKShare": "data_sources.stock.akshare_plugin",
        "通达信": "data_sources.stock.tongdaxin_plugin",
        "Yahoo Finance": "data_sources.stock_international.yahoo_finance_plugin",
    }
    return mapping.get(source_name, "")

def _populate_asset_table(self, asset_df):
    """填充资产列表表格"""
    self.asset_table.setRowCount(0)
    self.asset_table.setRowCount(len(asset_df))
    
    for row_idx, (_, row) in enumerate(asset_df.iterrows()):
        # 列0: 复选框
        checkbox = QCheckBox()
        checkbox.stateChanged.connect(self._on_asset_selected)
        self.asset_table.setCellWidget(row_idx, 0, checkbox)
        
        # 列1: 代码
        self.asset_table.setItem(row_idx, 1, QTableWidgetItem(row.get('symbol', row.get('code', ''))))
        
        # 列2: 名称
        self.asset_table.setItem(row_idx, 2, QTableWidgetItem(row.get('name', '')))
        
        # 列3: 市场
        self.asset_table.setItem(row_idx, 3, QTableWidgetItem(row.get('market', '')))
        
        # 列4: 行业
        self.asset_table.setItem(row_idx, 4, QTableWidgetItem(row.get('industry', '')))
        
        # 列5: 板块
        self.asset_table.setItem(row_idx, 5, QTableWidgetItem(row.get('sector', '')))
        
        # 列6: 状态
        status = row.get('listing_status', 'active')
        status_item = QTableWidgetItem(status)
        if status == 'active':
            status_item.setForeground(QColor('green'))
        else:
            status_item.setForeground(QColor('red'))
        self.asset_table.setItem(row_idx, 6, status_item)
    
    self.asset_table.resizeColumnsToContents()
```

### 2. 保存资产元数据

```python
def save_asset_metadata(self):
    """保存选中资产的元数据到数据库"""
    try:
        # 获取选中的资产
        selected_rows = self._get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要保存的资产")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认保存",
            f"将保存 {len(selected_rows)} 个资产的元数据到数据库\n\n"
            f"数据源: {self.current_data_source}\n"
            f"是否继续?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 提取选中资产的数据
        selected_assets = self.raw_asset_data.iloc[selected_rows].copy()
        
        logger.info(f"💾 开始保存 {len(selected_assets)} 个资产的元数据...")
        
        # 显示进度对话框
        progress = QProgressDialog(
            "正在保存资产元数据...", 
            "取消", 
            0, 
            len(selected_assets),
            self
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("保存进度")
        
        # 保存元数据（使用新的API）
        from core.asset_database_manager import AssetSeparatedDatabaseManager
        asset_manager = AssetSeparatedDatabaseManager.get_instance()
        
        success_count = 0
        failed_count = 0
        
        for idx, (_, row) in enumerate(selected_assets.iterrows()):
            if progress.wasCanceled():
                break
            
            try:
                # 准备元数据字典
                metadata = {
                    'symbol': row.get('symbol', row.get('code', '')),
                    'name': row.get('name', ''),
                    'market': row.get('market', 'unknown'),
                    'asset_type': 'stock_a',
                    'industry': row.get('industry', None),
                    'sector': row.get('sector', None),
                    'listing_date': row.get('listing_date', None),
                    'listing_status': row.get('listing_status', 'active'),
                    'total_shares': row.get('total_shares', None),
                    'circulating_shares': row.get('circulating_shares', None),
                    'primary_data_source': self.current_data_source,
                    'data_sources': [self.current_data_source],  # JSON字段
                    'attributes': {}  # 其他属性
                }
                
                # 调用保存API
                success = asset_manager.upsert_asset_metadata(
                    symbol=metadata['symbol'],
                    asset_type=AssetType.STOCK_A,
                    metadata=metadata
                )
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                
            except Exception as e:
                logger.error(f"保存资产元数据失败 {row.get('symbol')}: {e}")
                failed_count += 1
            
            progress.setValue(idx + 1)
        
        progress.close()
        
        # 显示结果
        QMessageBox.information(
            self,
            "保存完成",
            f"资产元数据保存完成！\n\n"
            f"成功: {success_count}\n"
            f"失败: {failed_count}\n\n"
            f"您现在可以继续下载这些资产的详细数据"
        )
        
        logger.info(f"✅ 资产元数据保存完成: 成功={success_count}, 失败={failed_count}")
        
    except Exception as e:
        logger.error(f"保存资产元数据失败: {e}")
        QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")

def _get_selected_rows(self) -> List[int]:
    """获取选中的行索引"""
    selected_rows = []
    for row in range(self.asset_table.rowCount()):
        checkbox = self.asset_table.cellWidget(row, 0)
        if checkbox and checkbox.isChecked():
            selected_rows.append(row)
    return selected_rows
```

### 3. K线数据下载页面集成

```python
class EnhancedDataImportWidget(QWidget):
    """增强的数据导入组件（集成资产元数据）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 添加选项卡
        self.tab_widget = QTabWidget()
        
        # Tab 1: 资产列表管理
        self.asset_list_widget = AssetListDownloadWidget()
        self.tab_widget.addTab(self.asset_list_widget, "📋 资产列表管理")
        
        # Tab 2: K线数据下载
        self.kline_download_widget = KlineDataDownloadWidget()
        self.tab_widget.addTab(self.kline_download_widget, "📈 K线数据下载")
        
        # Tab 3: 数据验证
        self.validation_widget = DataValidationWidget()
        self.tab_widget.addTab(self.validation_widget, "✅ 数据验证")
        
        layout.addWidget(self.tab_widget)
        
        # 连接信号
        self.asset_list_widget.assets_saved.connect(
            self.kline_download_widget.on_assets_updated
        )
```

---

## TET框架集成

### 1. 资产列表数据标准化

```python
# core/tet_data_pipeline.py

def transform_asset_list_data(self, raw_data: pd.DataFrame, 
                              query: StandardQuery) -> pd.DataFrame:
    """
    转换资产列表数据（新增方法）
    
    功能：
    1. 统一字段名称
    2. 数据类型转换
    3. 数据验证
    4. 补全缺失字段
    
    Args:
        raw_data: 插件返回的原始资产列表
        query: 查询参数
        
    Returns:
        标准化后的资产列表DataFrame
    """
    try:
        if raw_data is None or raw_data.empty:
            return pd.DataFrame()
        
        logger.info(f"开始标准化资产列表数据: {len(raw_data)} 条记录")
        logger.debug(f"原始字段: {list(raw_data.columns)}")
        
        # 1. 字段映射（统一不同插件的字段名）
        field_mapping = {
            # 基本字段
            'code': 'symbol',           # 代码 → symbol
            'stock_code': 'symbol',
            'ts_code': 'symbol',
            'stock_name': 'name',       # 名称 → name
            'stock_market': 'market',   # 市场 → market
            'exchange': 'market',
            
            # 分类字段
            'industry_name': 'industry',
            'sector_name': 'sector',
            'industry_code': 'industry_code',
            
            # 上市信息
            'list_date': 'listing_date',
            'delist_date': 'delisting_date',
            'status': 'listing_status',
            'list_status': 'listing_status',
            
            # 股本信息
            'total_capital': 'total_shares',
            'float_capital': 'circulating_shares',
        }
        
        # 应用字段映射
        mapped_data = raw_data.rename(columns=field_mapping)
        
        # 2. 确保必需字段存在
        required_fields = ['symbol', 'name', 'market']
        for field in required_fields:
            if field not in mapped_data.columns:
                if field == 'symbol' and 'code' in raw_data.columns:
                    mapped_data['symbol'] = raw_data['code']
                elif field == 'market':
                    # 从symbol推断market
                    mapped_data['market'] = mapped_data['symbol'].apply(
                        lambda s: self._infer_market_from_symbol(s)
                    )
                else:
                    mapped_data[field] = None
        
        # 3. 标准化symbol格式
        mapped_data['symbol'] = mapped_data['symbol'].apply(
            lambda s: self._standardize_symbol(s)
        )
        
        # 4. 补全可选字段（如果不存在）
        optional_fields = {
            'name_en': None,
            'full_name': None,
            'short_name': None,
            'asset_type': 'stock_a',
            'exchange': None,
            'sector': None,
            'industry': None,
            'industry_code': None,
            'listing_date': None,
            'delisting_date': None,
            'listing_status': 'active',
            'total_shares': None,
            'circulating_shares': None,
            'currency': 'CNY',
            'tags': [],
            'attributes': {}
        }
        
        for field, default_value in optional_fields.items():
            if field not in mapped_data.columns:
                mapped_data[field] = default_value
        
        # 5. 数据类型转换
        # 数值字段
        numeric_fields = ['total_shares', 'circulating_shares']
        for field in numeric_fields:
            if field in mapped_data.columns:
                mapped_data[field] = pd.to_numeric(
                    mapped_data[field], 
                    errors='coerce'
                )
        
        # 日期字段
        date_fields = ['listing_date', 'delisting_date']
        for field in date_fields:
            if field in mapped_data.columns:
                mapped_data[field] = pd.to_datetime(
                    mapped_data[field], 
                    errors='coerce'
                )
        
        # 6. 数据验证
        # 移除无效记录（symbol或name为空）
        before_count = len(mapped_data)
        mapped_data = mapped_data[
            mapped_data['symbol'].notna() & 
            (mapped_data['symbol'] != '') &
            mapped_data['name'].notna() &
            (mapped_data['name'] != '')
        ]
        after_count = len(mapped_data)
        
        if before_count > after_count:
            logger.warning(
                f"移除了 {before_count - after_count} 条无效记录"
            )
        
        # 7. 去重（按symbol）
        before_count = len(mapped_data)
        mapped_data = mapped_data.drop_duplicates(subset=['symbol'], keep='last')
        after_count = len(mapped_data)
        
        if before_count > after_count:
            logger.warning(
                f"移除了 {before_count - after_count} 条重复记录"
            )
        
        # 8. 添加元数据管理字段
        mapped_data['metadata_version'] = 1
        mapped_data['last_verified'] = datetime.now()
        mapped_data['created_at'] = datetime.now()
        mapped_data['updated_at'] = datetime.now()
        
        logger.info(f"✅ 资产列表标准化完成: {len(mapped_data)} 条有效记录")
        logger.debug(f"标准化后字段: {list(mapped_data.columns)}")
        
        return mapped_data
        
    except Exception as e:
        logger.error(f"资产列表数据标准化失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return pd.DataFrame()

def _standardize_symbol(self, symbol: str) -> str:
    """标准化symbol格式"""
    if not symbol:
        return symbol
    
    symbol = str(symbol).strip()
    
    # 已有后缀，直接返回
    if '.' in symbol:
        return symbol.upper()
    
    # 根据代码前缀添加后缀
    if symbol.startswith('6'):
        return f"{symbol}.SH"
    elif symbol.startswith(('0', '3')):
        return f"{symbol}.SZ"
    elif symbol.startswith(('4', '8')):
        return f"{symbol}.BJ"
    else:
        # 无法判断，返回原值
        return symbol

def _infer_market_from_symbol(self, symbol: str) -> str:
    """从symbol推断market"""
    if not symbol:
        return 'unknown'
    
    if symbol.endswith('.SH'):
        return 'SH'
    elif symbol.endswith('.SZ'):
        return 'SZ'
    elif symbol.endswith('.BJ'):
        return 'BJ'
    
    code = symbol.split('.')[0]
    if code.startswith('6'):
        return 'SH'
    elif code.startswith(('0', '3')):
        return 'SZ'
    elif code.startswith(('4', '8')):
        return 'BJ'
    
    return 'unknown'
```

### 2. K线数据标准化（更新）

```python
def transform_kline_data(self, raw_data: pd.DataFrame, 
                        query: StandardQuery) -> pd.DataFrame:
    """
    转换K线数据（更新版，不再填充name/market）
    
    Args:
        raw_data: 插件返回的原始K线数据
        query: 查询参数
        
    Returns:
        标准化后的K线DataFrame
    """
    try:
        if raw_data is None or raw_data.empty:
            return pd.DataFrame()
        
        logger.info(f"开始标准化K线数据: {len(raw_data)} 条记录")
        
        # 1. 字段映射
        mapped_data = self.field_mapping_engine.map_fields(
            raw_data, 
            DataType.HISTORICAL_KLINE
        )
        
        # 2. 数据类型转换
        standardized_data = self._standardize_data_types(
            mapped_data, 
            DataType.HISTORICAL_KLINE
        )
        
        # 3. ✅ 不再填充 name/market 字段
        #    这些字段现在从 asset_metadata 表获取
        #    如果插件提供了这些字段，保留它们用于验证
        
        # 4. 数据清洗
        standardized_data = self._clean_data(standardized_data)
        
        # 5. 数据验证
        standardized_data = self._validate_data(
            standardized_data, 
            DataType.HISTORICAL_KLINE
        )
        
        logger.info(f"✅ K线数据标准化完成: {len(standardized_data)} 条记录")
        
        return standardized_data
        
    except Exception as e:
        logger.error(f"K线数据标准化失败: {e}")
        return pd.DataFrame()
```

---

## 数据源切换兼容

### 核心机制：数据源追溯

```python
# asset_metadata 表设计（支持多数据源）

CREATE TABLE asset_metadata (
    symbol VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    market VARCHAR NOT NULL,
    
    -- ✅ 数据源追溯字段
    data_sources JSON,              -- 所有提供过此资产数据的源 ["eastmoney", "sina"]
    primary_data_source VARCHAR,    -- 主要数据源
    source_priority JSON,           -- 数据源优先级 {"eastmoney": 1, "sina": 2}
    
    -- ✅ 元数据版本控制
    metadata_version INTEGER DEFAULT 1,
    last_verified TIMESTAMP,        -- 最后验证时间
    last_update_source VARCHAR,     -- 最后更新此元数据的数据源
    
    ...
)

# historical_kline_data 表（K线数据）

CREATE TABLE historical_kline_data (
    symbol VARCHAR NOT NULL,
    
    -- ✅ 每条K线记录都标记数据源
    data_source VARCHAR NOT NULL,   -- 此K线数据来自哪个数据源
    
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL,
    close DECIMAL,
    ...
    
    PRIMARY KEY (symbol, data_source, timestamp, frequency)
)
```

### 数据源切换场景

#### 场景1: 从东方财富切换到新浪

```python
# 用户操作流程

Step 1: 选择新数据源（新浪）
  └─ UI: source_combo.setCurrentText("新浪财经")

Step 2: 获取资产列表
  └─ 调用: sina_plugin.get_asset_list()
  └─ 返回: DataFrame[symbol, name, market, ...]

Step 3: 保存/更新元数据
  └─ upsert_asset_metadata()
      ├─ 检查 asset_metadata 表是否已有该symbol
      ├─ 如果存在：
      │   ├─ 更新 data_sources: ["eastmoney", "sina"]  # 追加
      │   ├─ 更新 last_update_source: "sina"
      │   ├─ 更新 last_verified: now()
      │   └─ metadata_version += 1
      └─ 如果不存在：
          └─ 插入新记录，primary_data_source = "sina"

Step 4: 下载K线数据
  └─ download_kline_data()
      ├─ 调用: sina_plugin.get_kdata(symbol)
      └─ 保存: INSERT INTO historical_kline_data
          ├─ symbol = "000001.SZ"
          ├─ data_source = "sina"  # ← 标记数据源
          └─ timestamp, ohlcv, ...

结果：
✅ asset_metadata 表记录了多个数据源
✅ historical_kline_data 表可以有同一symbol的不同数据源记录
✅ 数据完整追溯
```

#### 场景2: 数据源优先级和数据合并

```python
def get_kdata_with_best_quality(self, symbol: str, period: str = 'D', 
                                count: int = 100) -> pd.DataFrame:
    """
    获取最佳质量的K线数据（多数据源合并）
    
    策略：
    1. 从asset_metadata获取数据源优先级
    2. 按优先级查询K线数据
    3. 合并数据，优先级高的覆盖优先级低的
    
    Args:
        symbol: 资产代码
        period: 周期
        count: 数量
        
    Returns:
        合并后的最佳质量K线数据
    """
    try:
        # 1. 获取资产元数据
        asset_meta = self.asset_manager.get_asset_metadata(
            symbol=symbol,
            asset_type=AssetType.STOCK_A
        )
        
        if not asset_meta:
            logger.warning(f"未找到资产元数据: {symbol}")
            return pd.DataFrame()
        
        # 2. 获取数据源优先级
        data_sources = asset_meta.get('data_sources', [])
        if not data_sources:
            logger.warning(f"资产无可用数据源: {symbol}")
            return pd.DataFrame()
        
        # 3. 按优先级查询K线数据
        kline_data_by_source = {}
        for source in data_sources:
            try:
                df = self._query_kline_from_source(
                    symbol=symbol,
                    source=source,
                    period=period,
                    count=count
                )
                if not df.empty:
                    kline_data_by_source[source] = df
            except Exception as e:
                logger.warning(f"从数据源 {source} 查询K线失败: {e}")
        
        if not kline_data_by_source:
            logger.warning(f"所有数据源都无K线数据: {symbol}")
            return pd.DataFrame()
        
        # 4. 合并数据（按时间戳，高优先级覆盖低优先级）
        merged_df = self._merge_kline_data_by_priority(
            kline_data_by_source,
            priority_order=data_sources
        )
        
        logger.info(f"✅ 合并K线数据成功: {symbol}, {len(merged_df)} 条记录")
        
        return merged_df
        
    except Exception as e:
        logger.error(f"获取最佳质量K线数据失败: {e}")
        return pd.DataFrame()

def _merge_kline_data_by_priority(self, kline_dict: Dict[str, pd.DataFrame],
                                   priority_order: List[str]) -> pd.DataFrame:
    """
    按优先级合并多数据源的K线数据
    
    策略：
    - 按timestamp分组
    - 同一timestamp，高优先级数据覆盖低优先级
    - 保留data_source字段追溯
    """
    if not kline_dict:
        return pd.DataFrame()
    
    # 反向优先级（优先级低的先合并）
    reversed_priority = list(reversed(priority_order))
    
    merged = None
    for source in reversed_priority:
        if source not in kline_dict:
            continue
        
        df = kline_dict[source].copy()
        df['_priority'] = priority_order.index(source)  # 记录优先级
        
        if merged is None:
            merged = df
        else:
            # 合并：按timestamp，保留高优先级（_priority值小）
            merged = pd.concat([merged, df])
            merged = merged.sort_values('_priority')
            merged = merged.drop_duplicates(subset=['timestamp'], keep='first')
    
    if merged is not None:
        merged = merged.drop(columns=['_priority'])
        merged = merged.sort_values('timestamp')
    
    return merged
```

### 表结构保持一致性

**关键点**: 无论哪个数据源，存储到数据库的表结构完全一致

```python
# 所有数据源返回的数据，经过TET框架标准化后，都符合相同的schema

# 东方财富插件返回
eastmoney_data = {
    'f12': '000001',     # 代码
    'f14': '平安银行',    # 名称
    'f2': 10.23,        # 价格
    ...
}

# TET标准化后
standardized_data = {
    'symbol': '000001.SZ',
    'name': '平安银行',
    'close': 10.23,
    ...
}

# ================================

# 新浪插件返回
sina_data = {
    'code': '000001',
    'name': '平安银行',
    'price': 10.23,
    ...
}

# TET标准化后（相同的schema）
standardized_data = {
    'symbol': '000001.SZ',
    'name': '平安银行',
    'close': 10.23,
    ...
}

# ================================

# 最终存储（相同的表结构）
INSERT INTO asset_metadata (symbol, name, market, data_source, ...)
INSERT INTO historical_kline_data (symbol, timestamp, open, close, data_source, ...)
```

---

## 实施代码

### 新增API: AssetSeparatedDatabaseManager

```python
# core/asset_database_manager.py

def upsert_asset_metadata(self, symbol: str, asset_type: AssetType, 
                          metadata: Dict[str, Any]) -> bool:
    """
    插入或更新资产元数据
    
    功能：
    - 如果symbol不存在，插入新记录
    - 如果symbol存在，更新记录并追加数据源
    - 自动管理版本号和时间戳
    
    Args:
        symbol: 资产代码
        asset_type: 资产类型
        metadata: 元数据字典
        
    Returns:
        是否成功
    """
    try:
        db_path = self._get_database_path(asset_type)
        with self.duckdb_manager.get_pool(db_path).get_connection() as conn:
            # 检查是否已存在
            existing = conn.execute(
                "SELECT * FROM asset_metadata WHERE symbol = ?",
                [symbol]
            ).fetchone()
            
            if existing:
                # 更新逻辑
                logger.debug(f"更新资产元数据: {symbol}")
                
                # 提取现有data_sources
                existing_dict = dict(zip(
                    [desc[0] for desc in conn.description],
                    existing
                ))
                existing_sources = existing_dict.get('data_sources', [])
                if isinstance(existing_sources, str):
                    import json
                    existing_sources = json.loads(existing_sources)
                
                # 追加新数据源（去重）
                new_source = metadata.get('primary_data_source')
                if new_source and new_source not in existing_sources:
                    existing_sources.append(new_source)
                
                # 构建UPDATE语句
                update_fields = []
                update_params = []
                
                for key, value in metadata.items():
                    if key in ['symbol', 'created_at']:  # 跳过主键和创建时间
                        continue
                    
                    update_fields.append(f"{key} = ?")
                    
                    # JSON字段特殊处理
                    if key == 'data_sources':
                        import json
                        update_params.append(json.dumps(existing_sources))
                    elif key in ['tags', 'attributes'] and isinstance(value, (list, dict)):
                        import json
                        update_params.append(json.dumps(value))
                    else:
                        update_params.append(value)
                
                # 添加元数据管理字段
                update_fields.extend([
                    "metadata_version = metadata_version + 1",
                    "last_verified = CURRENT_TIMESTAMP",
                    "updated_at = CURRENT_TIMESTAMP"
                ])
                
                update_params.append(symbol)  # WHERE条件
                
                sql = f"""
                    UPDATE asset_metadata 
                    SET {', '.join(update_fields)}
                    WHERE symbol = ?
                """
                
                conn.execute(sql, update_params)
                
            else:
                # 插入逻辑
                logger.debug(f"插入新资产元数据: {symbol}")
                
                # JSON字段处理
                import json
                if 'data_sources' in metadata:
                    if isinstance(metadata['data_sources'], list):
                        metadata['data_sources'] = json.dumps(metadata['data_sources'])
                else:
                    metadata['data_sources'] = json.dumps([metadata.get('primary_data_source')])
                
                if 'tags' in metadata and isinstance(metadata['tags'], list):
                    metadata['tags'] = json.dumps(metadata['tags'])
                
                if 'attributes' in metadata and isinstance(metadata['attributes'], dict):
                    metadata['attributes'] = json.dumps(metadata['attributes'])
                
                # 构建INSERT语句
                columns = list(metadata.keys())
                placeholders = ['?' for _ in columns]
                values = [metadata[col] for col in columns]
                
                sql = f"""
                    INSERT INTO asset_metadata ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                """
                
                conn.execute(sql, values)
            
            conn.commit()
            logger.info(f"✅ 资产元数据保存成功: {symbol}")
            return True
            
    except Exception as e:
        logger.error(f"保存资产元数据失败: {symbol}, {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
```

---

## 总结

### 完整流程

```
1. 用户选择数据源（东方财富/新浪/AKShare...）
   ↓
2. 点击"获取资产列表"
   └─ plugin.get_asset_list()
   └─ TET标准化
   └─ UI展示列表
   ↓
3. 用户选择要下载的资产
   ↓
4. 点击"保存元数据"
   └─ UPSERT INTO asset_metadata
   └─ 追加data_sources
   ↓
5. 点击"下载K线数据"
   └─ plugin.get_kdata(symbol)
   └─ TET标准化
   └─ INSERT INTO historical_kline_data
   └─ 标记data_source
   ↓
6. 数据验证
   └─ 检查完整性
   └─ 记录质量
```

### 关键优势

1. **元数据分离** ✅
   - asset_metadata 只存一次
   - historical_kline_data 不含冗余

2. **数据源追溯** ✅
   - 每条记录都知道来源
   - 支持多数据源合并

3. **TET标准化** ✅
   - 统一表结构
   - 数据源无关

4. **向后兼容** ✅
   - 视图保持旧查询可用
   - 平滑迁移

5. **用户友好** ✅
   - 直观的UI流程
   - 实时进度反馈
   - 错误提示清晰

---

**状态**: ✅ 完整方案设计完成  
**下一步**: 开始实施代码

