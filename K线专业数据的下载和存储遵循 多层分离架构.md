┌─────────────────────────────────────────────────────────────┐
│                   UI 层 (GUI)                                 │
│  EnhancedDataImportWidget - 数据导入UI界面                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│              任务执行层 (Task Execution)                       │
│  DataImportExecutionEngine - 导入执行引擎                      │
│  • 智能配置优化、AI优化、AutoTuner                             │
│  • 性能监控、风险监控、数据质量监控                             │
│  • 分布式执行、事件发布、异步任务管理                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│              数据处理层 (Data Processing)                      │
│  • 数据下载：RealDataProvider - 真实数据供应器                 │
│  • 数据标准化：DataStandardizationEngine - 标准化引擎          │
│  • 字段映射、格式转换、质量检查                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│              数据存储层 (Data Storage)                         │
│  AssetSeparatedDatabaseManager - 资产分数据库管理器            │
│  • 按资产类型分离数据库（STOCK_A, STOCK_US等）               │
│  • historical_kline_data 主表 + 配套支持表                    │
│  • Upsert 操作、索引优化、数据质量监控表                       │
└─────────────────────────────────────────────────────────────┘


UIWidget.on_start_import()
  └─> import_engine.start_task(task_id)
        ├─> 智能配置优化 (if enable_intelligent_config)
        ├─> 缓存配置查询 (if enable_intelligent_caching)
        ├─> AutoTuner 自动调优 (if enable_auto_tuning)
        ├─> AI 参数优化 (if enable_ai_optimization)
        ├─> 检查分布式执行条件 (if enable_distributed_execution)
        └─> executor.submit(_execute_task, task_config, result)
              └─> _execute_task() 【核心执行】


_execute_task(task_config, result)
  └─> 根据 data_type 分支：
        ├─ "K线数据" → _import_kline_data()
        ├─ "实时行情" → _import_realtime_data()
        └─ "基本面数据" → _import_fundamental_data()


        
阶段 3：K线数据导入的详细流程 ⭐ 关键

_import_kline_data(task_config, result)
  │
  ├─ [初始化阶段]
  │  ├─> _ensure_data_manager()
  │  ├─> _ensure_real_data_provider()
  │  └─> 初始化实时写入服务 (RealtimeWriteService)
  │
  ├─ [并发下载阶段] 👈 **核心下载逻辑**
  │  └─> ThreadPoolExecutor (max_workers = min(task_config.max_workers, len(symbols), 8))
  │       └─> for each symbol in symbols:
  │            └─> download_single_stock(symbol)
  │                 ├─ _check_incremental_update(symbol, task_config)
  │                 │   └─ 查询 historical_kline_data 表的最新日期
  │                 │
  │                 ├─ [数据下载]
  │                 │  └─> real_data_provider.get_kline_data(
  │                 │       symbol, start_date, end_date, frequency, data_source)
  │                 │
  │                 ├─ [数据标准化] 👈 **字段映射关键点**
  │                 │  └─> _standardize_kline_data_fields(kdata, data_source=task_config.data_source)
  │                 │       ├─ datetime 处理（DatetimeIndex → datetime 列）
  │                 │       ├─ symbol 处理（code → symbol 映射）
  │                 │       ├─ 字段映射（20 个标准字段）
  │                 │       ├─ 类型转换（数值、日期）
  │                 │       ├─ 缺失字段补充（使用默认值）
  │                 │       ├─ data_source 字段设置 ✅ 【重点】
  │                 │       └─> 返回标准化 DataFrame
  │                 │
  │                 ├─ [数据验证]
  │                 │  └─> _validate_imported_data()
  │                 │       ├─ 数据质量评分计算
  │                 │       ├─ 质量指标记录
  │                 │       └─ 质量分数写入 DuckDB
  │                 │
  │                 ├─ [实时写入 或 批量积累]
  │                 │  ├─ [如果 RealtimeWriteService 可用]
  │                 │  │  └─> realtime_write_service.write_kline_data(
  │                 │  │       symbol, kdata, task_config.asset_type)
  │                 │  │       └─> 直接写入数据库 + 发布进度事件
  │                 │  │
  │                 │  └─ [降级到批量模式]
  │                 │     └─> all_kdata_list.append(kdata)
  │                 │
  │                 └─> 发布下载完成事件
  │
  ├─ [批量保存阶段] (仅降级模式)
  │  └─> _batch_save_kdata_to_database(all_kdata_list, task_config)
  │       ├─ pd.concat(all_kdata_list) → 合并所有数据
  │       ├─ _standardize_kline_data_fields() → 二次标准化
  │       ├─ _enrich_kline_data_with_metadata() → 补充元数据
  │       └─> asset_manager.store_standardized_data()
  │            └─> 【存储阶段】
  │
  └─ [清理和汇总]
     ├─ 清理数据源连接池
     ├─ 发布完成事件
     └─ 更新进度统计


阶段 4：数据存储到数据库

asset_manager.store_standardized_data(
    data=kdata, 
    asset_type=task_config.asset_type, 
    data_type=DataType.HISTORICAL_KLINE)
  │
  ├─ 获取资产类型对应数据库路径
  │  └─> _ensure_database_exists(asset_type)
  │      └─> 创建按资产类型分离的 DuckDB 数据库
  │          (e.g., data/databases/stock_a/stock_a_data.duckdb)
  │
  ├─ 确保表结构存在
  │  └─> _ensure_table_exists(conn, 'historical_kline_data', data, DataType.HISTORICAL_KLINE)
  │       └─ 表结构：
  │           CREATE TABLE historical_kline_data (
  │               symbol VARCHAR NOT NULL,
  │               data_source VARCHAR NOT NULL,     ← 关键字段！
  │               timestamp TIMESTAMP NOT NULL,      ← datetime 映射到此
  │               frequency VARCHAR NOT NULL DEFAULT '1d',
  │               open DECIMAL(10,2) NOT NULL,
  │               high DECIMAL(10,2) NOT NULL,
  │               low DECIMAL(10,2) NOT NULL,
  │               close DECIMAL(10,2) NOT NULL,
  │               volume BIGINT DEFAULT 0,
  │               amount DECIMAL(18,2) DEFAULT 0,
  │               ... [其他字段] ...
  │               PRIMARY KEY (symbol, data_source, timestamp, frequency)
  │           )
  │
  ├─ 获取表实际列名
  │  └─> _get_table_columns(conn, 'historical_kline_data')
  │
  ├─ 字段过滤和映射
  │  └─> _filter_dataframe_columns(data, table_columns)
  │       ├─ datetime → timestamp 字段映射 ✅
  │       ├─ 过滤不在表中的列
  │       └─ ⚠️ 【问题点】 data_source 列的检查 (line 1055-1057)
  │
  ├─ 数据验证
  │  └─> 检查 data_source 列存在且无空值
  │       └─ ⚠️ 【问题点】 如果检查失败，返回 0（不插入）
  │
  └─> _upsert_data(conn, 'historical_kline_data', filtered_data, DataType.HISTORICAL_KLINE)
       ├─ 【关键修复】 data_source 字段初始化
       │  └─ if 'data_source' not in data.columns:
       │       data['data_source'] = 'unknown'
       │
       ├─ 构建 INSERT ... ON CONFLICT 语句
       │  └─ PRIMARY KEY 冲突处理
       │      UPDATE (symbol, data_source, timestamp, frequency) 时的字段更新
       │
       └─> conn.executemany(sql, data_tuples)
           └─ 批量插入 → 数据库