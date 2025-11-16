# 【阶段2】真实实现路线图

**目标**: 从演示验证转向真实生产代码改进

---

## 第一步：整合 import_execution_engine.py

### 问题诊断
1. `_standardize_kline_data_fields()` 是快速标准化，不使用 TET 框架
2. 在 `download_single_stock()` 中直接调用快速标准化，导致 data_source 丢失

### 改进方案

```
【当前流程】（❌ 混乱）
download_single_stock()
  ├─ RealDataProvider.get_kline_data()  
  │   └─ 原始数据 (字段名不统一)
  │
  └─ _standardize_kline_data_fields()  
      └─ 手工字段映射 → data_source 丢失 ❌

【改进流程】（✓ 清晰）
download_single_stock()
  ├─ RealDataProvider.get_kline_data()  
  │   └─ 原始数据 (字段名不统一)
  │
  ├─ TETDataPipeline.transform_data()
  │   └─ StandardData (字段已映射，data_source保留)
  │
  ├─ DataStandardizationEngine.validate()
  │   └─ 业务验证 + 质量评分
  │
  └─ store_standardized_data()
      └─ 存储 (data_source完整)
```

### 具体代码改进位置

| 文件 | 方法 | 改进类型 | 优先级 |
|------|------|--------|-------|
| import_execution_engine.py | download_single_stock() | 调用链改进 | **高** |
| import_execution_engine.py | execute_import_task() | 流程协调 | **高** |
| import_execution_engine.py | _standardize_kline_data_fields() | 移除或标记为fallback | **中** |
| real_data_provider.py | 添加 data_source 参数 | 参数传递 | **高** |
| asset_database_manager.py | store_standardized_data() | 参数检查 | **中** |

---

## 第二步：修改 realtime_write_service.py

### 当前问题
```python
def write_data(self, symbol: str, data: pd.DataFrame,
               asset_type: str = "STOCK_A") -> bool:
    # ❌ 缺少 data_source 参数
```

### 改进方案
```python
def write_data(self, symbol: str, data: pd.DataFrame,
               asset_type: str = "STOCK_A",
               data_source: str = "unknown") -> bool:  # ✓ 添加 data_source
    
    # 【关键】验证 data_source
    if not data_source or data_source == 'unknown':
        logger.warning(f"data_source is invalid: {data_source}")
    
    # 确保数据中包含 data_source
    if 'data_source' not in data.columns:
        data['data_source'] = data_source
```

---

## 第三步：创建改进的集成测试

### 测试策略
1. **单元测试** - 每个组件的改进单独测试
2. **集成测试** - 完整的5阶段流程测试
3. **性能测试** - 对比快速标准化 vs TET 框架
4. **回归测试** - 确保不破坏现有功能

### 关键测试场景
- ✓ data_source 完整链路（能追踪到每一条数据）
- ✓ 不同数据源的字段映射正确性
- ✓ 性能不下降超过10%
- ✓ 质量评分准确
- ✓ 分布式场景下的数据一致性

---

## 第四步：缓存策略统一

### 当前状态
- RealDataProvider._cache (TTL 300s)
- TETDataPipeline._cache (TTL 5min)
- MultiLevelCacheManager (基本未使用)

### 改进方案

```python
【L3 持久化缓存】24小时
┌─ 资产基础信息
├─ 数据源配置
└─ 字段映射表 (DuckDB或文件系统)

【L2 内存缓存】5-10分钟
┌─ 最近下载的原始数据
├─ TET转换的StandardData  
└─ 业务验证结果 (LRU缓存, 500MB限制)

【L1 进程缓存】1分钟
┌─ 当前处理中的数据
└─ 同一任务内的重复请求
```

---

## 第五步：插件管理和配置集成

### 新数据源的标准流程

```
1. 实现 IDataSourcePlugin 接口
2. 注册到 DataSourceRouter
3. 提供字段映射表
4. 在 TETDataPipeline 中配置映射规则
5. 通过集成测试
```

### 配置管理集成

```python
task_config = {
    'task_id': 'unique_id',
    'data_source': 'tongdaxin',      # 数据源标识
    'asset_type': 'STOCK_A',
    'symbols': [...],
    'cache_strategy': 'multi_level',  # 使用多级缓存
    'quality_threshold': 70,          # 质量评分阈值
    'enable_distributed': False,      # 分布式支持
}
```

---

## 执行计划

### 第1周：核心改进
- [ ] 修改 import_execution_engine.py (下载流程)
- [ ] 修改 real_data_provider.py (参数传递)
- [ ] 修改 realtime_write_service.py (data_source参数)
- [ ] 创建集成测试框架

### 第2周：验证和优化
- [ ] 运行所有集成测试
- [ ] 性能对比测试 (快速标准化 vs TET)
- [ ] 修复发现的问题
- [ ] 完整的回归测试

### 第3周：进阶功能
- [ ] 缓存策略统一
- [ ] 插件管理标准化
- [ ] 配置管理集成
- [ ] 分布式支持设计

### 第4-5周：文档和上线
- [ ] 完整的技术文档
- [ ] 开发者指南 (如何添加新数据源)
- [ ] 运维指南 (监控、告警、故障转移)
- [ ] 灰度部署计划

---

## 风险识别和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|--------|
| TET性能差于快速标准化 | 系统变慢 | 性能测试早发现，提前优化 |
| 现有依赖大量调用快速标准化 | 改进困难 | 保留fallback，渐进式迁移 |
| data_source 历史数据为'unknown' | 数据混乱 | 数据迁移脚本，离线补充 |
| 分布式环境下不一致 | 数据错误 | 完整的分布式测试 |

---

## 成功标准

✅ **必须完成**
- data_source 不再丢失（零个NOT NULL错误）
- TET框架正确集成（所有字段映射通过TET完成）
- 职责清晰分工（4层明确的职责）
- 没有破坏现有功能（回归测试100%通过）

✅ **应该完成**
- 性能不下降超过10%（对比基准36.44ms）
- 代码可维护性提升30%
- 新数据源接入时间<2小时

✅ **可以做**
- 完整的分布式支持
- 高级缓存策略
- 实时监控仪表板
