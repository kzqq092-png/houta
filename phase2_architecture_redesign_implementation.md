# 【阶段2】架构重设 - 实施计划

**状态**: 进行中  
**开始时间**: 2025-10-27  
**预计周期**: 3-5 周  
**负责人**: AI 开发团队  

---

## 一、阶段2的核心目标

基于阶段1的性能基准测试（快速标准化: 36.44ms, 137208 records/sec），实现系统架构从"多层混乱"到"清晰统一"的转变。

### 关键改进方向
1. **明确职责分工** - TET vs DataStandardization vs ImportEngine
2. **统一数据流规范** - 从下载到存储的完整规范化
3. **缓存策略统一** - 消除多层缓存混乱
4. **分布式场景支持** - 多节点一致性保证
5. **插件管理标准化** - 新数据源的动态注册
6. **配置管理集成** - ImportConfigManager 的角色定义
7. **实时写入改进** - RealtimeWriteService 的 data_source 参数

---

## 二、任务 2.1：明确的职责分工定义

### 2.1.1 问题分析

**当前状况：**
- TETDataPipeline: 字段映射、类型转换、缺失值处理
- DataStandardizationEngine: 业务规则验证、预处理、质量评分
- ImportExecutionEngine: 导入调度、进度管理、统计报告
- 但职责边界模糊，功能重叠约 70%

**根本问题：**
在 Phase 1 性能测试中发现，快速标准化直接在 ImportExecutionEngine 中实现，而不是使用 TET 框架，这导致：
- 信息丢失（data_source 被硬编码）
- 逻辑重复（字段映射做了多次）
- 代码分散（标准化逻辑散落多处）

### 2.1.2 职责分工规范

**新的职责模型：**

```
【数据流向图】

RealDataProvider (数据获取层)
  │ 职责: 从各数据源获取原始数据
  │ 输出: 原始 DataFrame + metadata
  │ 约束: 不做任何转换
  ↓

TETDataPipeline (通用标准化层 - 【改进焦点】)
  │ 职责: 字段映射、类型转换、格式标准化
  │ 输入: 原始 DataFrame + StandardQuery
  │ 输出: StandardData (data + metadata + source_info)
  │ 约束: 
  │   - 只做通用的字段和类型处理
  │   - 保留所有元数据信息
  │   - data_source 从 query 或 metadata 提取
  ↓

DataStandardizationEngine (业务标准化层 - 【改进焦点】)
  │ 职责: 业务规则验证、预处理、质量评分
  │ 输入: StandardData
  │ 输出: 业务验证的 DataFrame + quality_score
  │ 约束:
  │   - 不做字段映射或类型转换
  │   - 基于业务规则进行验证
  │   - 计算数据质量分数
  ↓

ImportExecutionEngine (流程编排层 - 【改进焦点】)
  │ 职责: 协调上下游、生命周期管理、监控统计
  │ 输入: task_config
  │ 输出: 导入结果 + 统计信息
  │ 约束:
  │   - 不实现具体的标准化逻辑
  │   - 调用 TET 和 DataStandardization 完成处理
  ↓

AssetSeparatedDatabaseManager (存储层)
  │ 职责: 数据持久化、约束检查、主键管理
  │ 输入: 业务验证的数据 + quality_score
  │ 输出: 存储结果
```

### 2.1.3 职责分工表

| 组件 | 旧职责（混乱） | 新职责（清晰） | 改进要点 |
|------|---------------|-------------|--------|
| TET | 存在但未使用 | 字段映射+类型转换 | 【重点】从快速标准化迁移到 TET |
| DataStd | 混乱的验证 | 业务规则+质量评分 | 【重点】明确只做业务层面 |
| ImportEngine | 全包揽 | 流程协调 | 【重点】移除具体的标准化逻辑 |
| Database | 被动接收 | 主动约束 | 改进参数验证 |

### 2.1.4 关键改进点

**改进 1：TET 框架的正确使用**
```
当前（错误）:
  ImportExecutionEngine._standardize_kline_data_fields()
    └─ 手工映射字段 → data_source 丢失 ❌

改进后（正确）:
  ImportExecutionEngine
    └─ 调用 TETDataPipeline.transform_data()
       └─ 完整的字段映射+元数据保留 ✓
       └─ data_source 从 StandardQuery 来源
```

**改进 2：DataStandardizationEngine 的明确定位**
```
当前（混乱）:
  既做字段映射，又做业务验证，职责不清 ❌

改进后（清晰）:
  只做业务规则验证
    • OHLC 逻辑检查
    • 价格范围检查
    • 成交量合理性检查
    • 数据完整性检查
    • 质量评分计算 ✓
```

**改进 3：ImportExecutionEngine 的流程协调职责**
```
当前（全包揽）:
  既下载、又标准化、又验证、又存储、又监控 ❌

改进后（只协调）:
  1. 启动任务
  2. 调用 RealDataProvider 下载
  3. 调用 TET 标准化
  4. 调用 DataStandardization 验证
  5. 调用 Database 存储
  6. 监控进度和统计 ✓
```

---

## 三、任务 2.2：统一的数据流规范

### 2.2.1 数据流的五个阶段

**完整的数据处理链路：**

```
【阶段1】配置和初始化
  输入: task_config (包含 symbols, data_source, asset_type 等)
  处理: 验证参数有效性
  输出: 有效的 task_context
  关键: data_source 在此确定并保留到最后

【阶段2】数据下载
  输入: task_context + symbols
  处理: RealDataProvider.get_kline_data(symbol, data_source)
  输出: 原始 DataFrame (raw_data)
  关键: 
    - 原始数据中字段名称可能不统一
    - data_source 仍然需要显式保留
    - 不进行任何转换

【阶段3】通用标准化（【关键改进】）
  输入: raw_data + StandardQuery(包含 data_source、provider 等)
  处理: TETDataPipeline.transform_data()
  输出: StandardData (
    data: 标准化的 DataFrame,
    metadata: {
      source: data_source,
      datetime_field: 'timestamp',
      symbol_field: 'code',
      ...
    },
    source_info: {
      provider: 'tongdaxin',
      timestamp: datetime.now(),
      record_count: len(data)
    }
  )
  关键:
    - data_source 从 StandardQuery 保留到 metadata
    - 所有字段映射通过 field_mappings 完成
    - 不进行任何业务验证

【阶段4】业务验证和质量评分
  输入: StandardData
  处理: DataStandardizationEngine.validate_and_score()
  输出: (
    processed_data: 验证通过的 DataFrame,
    quality_score: float (0-100),
    validation_results: {
      passed: bool,
      issues: List[str]
    }
  )
  关键:
    - 检查业务规则（OHLC 关系、价格范围等）
    - 计算数据质量评分
    - data_source 保持原值

【阶段5】存储和监控
  输入: processed_data + quality_score + data_source
  处理: AssetSeparatedDatabaseManager.store_standardized_data()
  输出: 存储结果
  关键:
    - 最终验证 data_source 不为空
    - 记录写入统计
    - 触发监控事件
```

### 2.2.2 数据结构规范

**task_config 结构：**
```python
{
  "task_id": "unique_id",
  "data_source": "tongdaxin",        # 【必需】在此定义一次
  "asset_type": "STOCK_A",
  "symbols": ["000001", "000002"],
  "data_type": "HISTORICAL_KLINE",
  "period": "D",
  "start_date": "2023-01-01",
  "end_date": "2025-01-01",
  "use_realtime_write": False,
  "batch_size": 1000
}
```

**StandardQuery 结构：**
```python
StandardQuery(
  symbol="000001",
  asset_type=AssetType.STOCK_A,
  data_type=DataType.HISTORICAL_KLINE,
  provider="tongdaxin",              # 【关键】来源标识
  period="D",
  start_date="2023-01-01",
  end_date="2025-01-01"
)
```

**StandardData 结构：**
```python
@dataclass
class StandardData:
  data: pd.DataFrame                 # 标准化后的数据
  metadata: Dict[str, str]           # 字段映射信息
  source_info: Dict[str, Any]        # 【关键】包含 data_source
  quality_score: Optional[float] = None
```

---

## 四、任务 2.3：缓存策略统一

### 4.1 问题分析

**当前混乱状态：**
- RealDataProvider._cache (TTL 300s) 
- TETDataPipeline._cache (TTL 5min)
- MultiLevelCacheManager (未充分使用)

**改进方向：**
统一到 MultiLevelCacheManager，定义三层缓存策略

### 4.2 统一的缓存策略

```
【L3 持久化缓存】24 小时
  内容: 
    - 资产基础信息（symbol、公司名称等）
    - 数据源配置
    - 字段映射表
  位置: DuckDB 或文件系统
  
【L2 内存缓存】5-10 分钟
  内容:
    - 最近下载的原始数据
    - TET 转换的 StandardData
    - 业务验证结果
  位置: 内存中的 LRU 缓存
  大小限制: 500MB
  
【L1 进程缓存】1 分钟（进程级）
  内容:
    - 当前处理中的数据
    - 同一任务内的重复请求
  位置: 进程内的快速缓存
```

---

## 五、后续任务清单

- [ ] 2.4 分布式场景的整合方案
- [ ] 2.5 插件管理的标准化
- [ ] 2.6 ImportConfigManager 的集成
- [ ] 2.7 RealtimeWriteService 的改进

---

## 六、实施时间表

```
第3周 (第1-2天): 明确职责分工
  - 编写职责分工文档
  - 确定 TET 框架的初始化方式
  - 修改 ImportExecutionEngine 调用结构

第3周 (第3-5天): 统一数据流规范
  - 定义 StandardQuery 和 StandardData
  - 实现数据流五阶段处理
  - 添加 data_source 的完整链路

第4周: 缓存策略和其他
  - 缓存层统一
  - 分布式方案设计
  - 插件和配置管理

第5周: 集成测试和文档
  - 完整流程测试
  - 性能验证
  - 文档完善
```

---

## 七、风险和缓解

| 风险 | 缓解措施 |
|------|--------|
| TET 初始化参数混乱 | 深入研究 DataSourceRouter 的正确使用方式 |
| 修改后性能下降 | 每个改进点都进行性能测试（基准: 36.44ms） |
| 数据丢失或不一致 | 添加完整的数据流追踪日志 |
