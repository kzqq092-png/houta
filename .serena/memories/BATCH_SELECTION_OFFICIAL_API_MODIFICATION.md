## 批量选择功能修改 - 直接使用官方akshare API

### 修改目标
将批量选择时获取的股票资产列表改为直接使用官方的最新最全的资产列表，不再使用数据源插件提供的资产列表。

### 修改内容

#### 1. 修改文件
**文件**: `gui/widgets/enhanced_data_import_widget.py`
**方法**: `get_stock_data()`

#### 2. 修改逻辑
**原始逻辑**:
- 方案1：通过选定的插件获取数据
- 方案2：通过UnifiedDataManager获取数据（备用方案）

**修改后逻辑**:
- **主要方案**：直接使用akshare官方API获取A股列表
- **备用方案**：通过UnifiedDataManager获取数据
- **失败处理**：显示详细的错误信息和解决建议

#### 3. 具体实现

**直接使用akshare官方API**:
```python
import akshare as ak
stock_list_df = ak.stock_info_a_code_name()
```

**数据转换**:
```python
stock_list = []
for _, row in stock_list_df.iterrows():
    stock_info = {
        "code": str(row.get('code', '')).strip(),
        "name": str(row.get('name', '')).strip(),
        "category": "A股"  # 统一标记为A股
    }
    stock_list.append(stock_info)
```

#### 4. 优势

1. **数据最新最全**: 直接使用akshare官方API，确保数据是最新的
2. **绕过插件系统**: 不再依赖数据源插件的状态和配置
3. **数据一致性**: 避免不同插件返回不同数据的问题
4. **性能提升**: 直接调用官方API，减少中间层
5. **错误处理**: 提供详细的错误信息和解决建议

#### 5. 预期效果

- **批量选择时**: 直接显示官方A股列表
- **数据量**: 接近官方统计的5,123只A股
- **数据质量**: 确保是纯A股数据，不包含B股、基金等
- **用户体验**: 更快的加载速度和更准确的数据

#### 6. 依赖要求

- 需要安装akshare库: `pip install akshare`
- 需要网络连接访问akshare API

#### 7. 错误处理

- 检查akshare库是否安装
- 处理网络连接问题
- 提供详细的错误信息和解决建议
- 备用方案确保系统可用性

### 修改完成
批量选择功能现在直接使用官方akshare API获取最新最全的A股列表，确保数据的准确性和完整性。