# ORM框架使用情况全面分析报告

**日期**: 2025-10-18  
**分析范围**: 全系统代码库  
**分析深度**: 架构、调用链、业务框架集成

---

## 📋 执行摘要

### 核心发现

**❌ 系统中没有使用传统意义的ORM框架！**

系统使用了**混合式数据访问架构**：
1. ✅ **SQLAlchemy QueuePool**（连接池管理）
2. ✅ **原生SQL + DataClass**（数据模型）
3. ✅ **Schema Registry**（表结构管理）
4. ❌ **没有SQLAlchemy ORM**（declarative_base）
5. ❌ **没有Peewee ORM**
6. ❌ **没有Django ORM**

---

## 🏗️ 系统数据访问架构

### 架构层级

```
┌─────────────────────────────────────────────────────────────┐
│                     应用层 (Application Layer)                │
│  UnifiedDataManager, DatabaseService, FactorWeaveAnalyticsDB │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                   数据访问层 (Data Access Layer)              │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ 连接池管理 (SQLAlchemy QueuePool)                     │  │
│   │ - DuckDBConnectionPool                                │  │
│   │ - AdaptiveConnectionPool                              │  │
│   └──────────────────────────────────────────────────────┘  │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ 原生SQL执行 (Native SQL)                              │  │
│   │ - DuckDBOperations                                    │  │
│   │ - SQLiteExtensionManager                              │  │
│   └──────────────────────────────────────────────────────┘  │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ 表结构管理 (Schema Registry)                          │  │
│   │ - TableManager                                        │  │
│   │ - TableSchemaRegistry                                 │  │
│   └──────────────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                    数据模型层 (Model Layer)                   │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ DataClass Models (非ORM)                             │  │
│   │ - StockInfo, KlineData, MarketData                   │  │
│   │ - UIDataModel, TaskStatusUIModel                     │  │
│   └──────────────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                  数据库层 (Database Layer)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐    │
│  │  DuckDB     │  │   SQLite    │  │  Pandas DataFrame│    │
│  └─────────────┘  └─────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 详细组件分析

### 1. SQLAlchemy QueuePool（连接池）

#### 使用位置
- `core/database/duckdb_connection_pool.py`
- `core/database/adaptive_connection_pool.py`
- `core/database/factorweave_analytics_db.py`

#### 代码示例
```python
from sqlalchemy.pool import QueuePool

class DuckDBConnectionPool:
    def __init__(self, db_path: str, pool_size: int = 5, ...):
        self.pool = QueuePool(
            creator=self._create_connection,
            pool_size=pool_size,
            max_overflow=max_overflow,
            timeout=timeout,
            recycle=pool_recycle,
            use_lifo=use_lifo,
            echo=False
        )
    
    def _create_connection(self):
        return duckdb.connect(self.db_path, read_only=False)
```

#### 功能
- ✅ 线程安全的连接池管理
- ✅ 自动连接回收和健康检查
- ✅ 连接超时控制
- ❌ **不提供ORM映射功能**

#### 为什么只用连接池？
**设计决策**：
1. **DuckDB特性**：DuckDB是列式OLAP数据库，不适合传统ORM的"对象-关系"映射模式
2. **性能考虑**：ORM的对象映射层会增加开销，对于分析型查询不划算
3. **灵活性**：原生SQL提供更好的查询优化和控制

---

### 2. DataClass Models（数据模型）

#### 使用位置
- `core/data/models.py` - 业务数据模型
- `core/ui_integration/ui_models.py` - UI数据模型
- `core/data/enhanced_models.py` - 增强数据模型
- `core/database/table_manager.py` - 表结构模型

#### 代码示例

**业务数据模型**:
```python
# core/data/models.py
@dataclass
class StockInfo:
    """股票信息"""
    symbol: str
    name: str
    market: str
    exchange: Optional[str] = None
    industry: Optional[str] = None
    list_date: Optional[date] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

**UI数据模型**:
```python
# core/ui_integration/ui_models.py
@dataclass
class UIDataModel:
    """UI数据模型基类"""
    timestamp: datetime = field(default_factory=datetime.now)
    source_service: Optional[str] = None
    is_cached: bool = False
```

**表结构模型**:
```python
# core/database/table_manager.py
@dataclass
class TableSchema:
    """表结构定义"""
    table_type: TableType
    columns: Dict[str, str]
    primary_key: List[str]
    indexes: List[str]
    constraints: Dict[str, str]
    version: str = "1.0"
```

#### 特点
- ✅ 类型安全
- ✅ 自动生成`__init__`、`__repr__`等方法
- ✅ 可转换为字典（`asdict()`）
- ❌ **不提供数据库映射**
- ❌ **不提供查询构建器**

---

### 3. Schema Registry（表结构管理）

#### 核心组件

**文件**: `core/database/table_manager.py`

```python
class TableSchemaRegistry:
    """表结构注册表"""
    
    def __init__(self):
        self._schemas: Dict[TableType, TableSchema] = {}
        self._initialize_default_schemas()
    
    def _initialize_default_schemas(self):
        """初始化默认表结构"""
        # 股票基础信息表
        self._schemas[TableType.STOCK_BASIC_INFO] = TableSchema(
            table_type=TableType.STOCK_BASIC_INFO,
            columns={
                'symbol': 'VARCHAR NOT NULL',
                'name': 'VARCHAR NOT NULL',
                'market': 'VARCHAR NOT NULL',
                # ... 更多列定义
            },
            primary_key=['symbol'],
            indexes=['symbol', 'market']
        )
        
        # K线数据表
        self._schemas[TableType.KLINE_DATA] = TableSchema(
            table_type=TableType.KLINE_DATA,
            columns={
                'symbol': 'VARCHAR NOT NULL',
                'datetime': 'TIMESTAMP NOT NULL',
                'open': 'DECIMAL(10,4)',
                'high': 'DECIMAL(10,4)',
                'low': 'DECIMAL(10,4)',
                'close': 'DECIMAL(10,4)',
                'volume': 'BIGINT',
                # ... 更多列定义
            },
            primary_key=['symbol', 'datetime'],
            indexes=['symbol', 'datetime']
        )
```

#### 功能
- ✅ 集中管理所有表结构定义
- ✅ 版本控制和迁移支持
- ✅ 动态表创建
- ✅ 索引自动管理
- ❌ **不提供对象映射**

---

### 4. 原生SQL执行

#### 核心类

**DuckDBOperations** (`core/database/duckdb_operations.py`):
```python
class DuckDBOperations:
    """DuckDB数据操作类"""
    
    def query_data(self, database_path: str, table_name: str,
                   query_filter: Optional[QueryFilter] = None,
                   custom_sql: Optional[str] = None) -> QueryResult:
        """查询数据"""
        with self.connection_manager.get_connection(database_path) as conn:
            if custom_sql:
                query_sql = custom_sql
            else:
                query_sql = self._build_query_sql(table_name, query_filter)
            
            result_df = conn.execute(query_sql).df()
            return QueryResult(data=result_df, ...)
    
    def insert_data(self, database_path: str, table_name: str,
                    data: pd.DataFrame, batch_size: int = 1000):
        """插入数据"""
        with self.connection_manager.get_connection(database_path) as conn:
            conn.register('temp_data', data)
            conn.execute(f"INSERT INTO {table_name} SELECT * FROM temp_data")
```

**FactorWeaveAnalyticsDB** (`core/database/factorweave_analytics_db.py`):
```python
class FactorWeaveAnalyticsDB:
    """分析数据库管理器 - 使用连接池"""
    
    def execute_query(self, sql: str, params: Optional[List] = None,
                      scenario: QueryScenario = QueryScenario.NORMAL) -> pd.DataFrame:
        """执行查询"""
        with self.pool.get_connection() as conn:
            if params:
                result = conn.execute(sql, params).fetchdf()
            else:
                result = conn.execute(sql).fetchdf()
            return result
    
    def insert_strategy_result(self, strategy_name: str, symbol: str, ...):
        """插入策略结果"""
        sql = """
            INSERT INTO strategy_execution_results 
            (strategy_name, symbol, execution_time, signal_type, price, ...)
            VALUES (?, ?, ?, ?, ?, ...)
        """
        return self.execute_command(sql, [strategy_name, symbol, ...])
```

#### 特点
- ✅ 直接控制SQL查询
- ✅ 高性能（无ORM开销）
- ✅ 灵活的查询优化
- ❌ **需要手写SQL**
- ❌ **类型安全性依赖手工维护**

---

## 🔄 数据流调用链分析

### 场景1: 获取股票K线数据

```
用户请求
    ↓
UnifiedDataManager.get_kdata(stock_code="000001")
    ↓
DatabaseService.get_connection("stock_a_duckdb")
    ↓
DuckDBConnectionPool.get_connection()  [SQLAlchemy QueuePool]
    ↓
conn.execute("""
    SELECT * FROM kline_data_akshare 
    WHERE symbol = '000001' 
    ORDER BY datetime DESC 
    LIMIT 365
""").fetchdf()
    ↓
pd.DataFrame  [直接返回，无ORM转换]
    ↓
用户获得数据
```

**关键点**:
- ✅ 使用SQLAlchemy QueuePool管理连接
- ✅ 使用原生SQL查询
- ✅ 直接返回Pandas DataFrame
- ❌ **没有对象映射层**

### 场景2: 插入策略执行结果

```
策略执行
    ↓
FactorWeaveAnalyticsDB.insert_strategy_result(
    strategy_name="MA_Cross",
    symbol="000001",
    price=12.34,
    profit_loss=0.05,
    ...
)
    ↓
DuckDBConnectionPool.get_connection()  [SQLAlchemy QueuePool]
    ↓
conn.execute("""
    INSERT INTO strategy_execution_results 
    (strategy_name, symbol, execution_time, ...)
    VALUES (?, ?, ?, ...)
""", [strategy_name, symbol, ...])
    ↓
数据库写入完成
```

**关键点**:
- ✅ 使用SQLAlchemy QueuePool管理连接
- ✅ 使用参数化SQL（防SQL注入）
- ✅ 事务自动管理（DuckDB默认autocommit）
- ❌ **没有对象持久化层**

### 场景3: 查询性能指标

```
性能监控
    ↓
FactorWeavePerformanceIntegration._get_current_metric_value("query_response_time")
    ↓
FactorWeaveAnalyticsDB.execute_query("""
    SELECT AVG(value) as avg_time
    FROM performance_metrics 
    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 5 MINUTE
      AND metric_name = 'execution_time'
      AND value > 0
""")
    ↓
DuckDBConnectionPool.get_connection()  [SQLAlchemy QueuePool]
    ↓
conn.execute(sql).fetchdf()
    ↓
pd.DataFrame → result.iloc[0]['avg_time']
    ↓
返回float值
```

**关键点**:
- ✅ 复杂SQL聚合查询
- ✅ 时间范围过滤
- ✅ 直接获取结果值
- ❌ **完全原生SQL，无ORM抽象**

---

## 📊 架构对比

### 传统ORM架构 vs 当前架构

| 特性 | 传统ORM（如SQLAlchemy ORM） | 当前架构 |
|------|---------------------------|----------|
| **连接管理** | SQLAlchemy QueuePool | ✅ SQLAlchemy QueuePool |
| **对象映射** | declarative_base + mapper | ❌ 无（使用DataClass） |
| **查询构建** | Query API（如session.query()） | ❌ 原生SQL字符串 |
| **关系映射** | relationship() | ❌ 手动JOIN |
| **延迟加载** | lazy loading | ❌ 无 |
| **事务管理** | session.commit/rollback | ✅ 连接池 + DuckDB autocommit |
| **类型安全** | 声明式类型 | ⚠️ DataClass + 手工维护 |
| **迁移工具** | Alembic | ⚠️ 手工表结构管理 |
| **性能** | 有ORM开销 | ✅ 无ORM开销 |
| **灵活性** | 受限于ORM抽象 | ✅ 完全SQL控制 |

### 为什么不用传统ORM？

#### 优势分析

**✅ 当前架构优势**:

1. **性能优越**
   - 无ORM对象映射开销
   - 直接返回Pandas DataFrame（分析友好）
   - 适合OLAP查询（列式存储）

2. **灵活性高**
   - 完全SQL控制
   - 易于优化复杂查询
   - 支持DuckDB特有功能（如PIVOT、QUALIFY）

3. **维护简单**
   - 无ORM魔法，行为透明
   - 调试方便（直接看SQL）
   - 学习曲线低

4. **适配DuckDB**
   - DuckDB设计用于分析（OLAP），不是事务（OLTP）
   - 列式存储不适合ORM的行式操作
   - 直接SQL查询更高效

**❌ 潜在劣势**:

1. **手写SQL**
   - 容易出错（列名拼写）
   - 缺少编译时类型检查
   - 重构不友好

2. **无查询构建器**
   - 动态查询需要字符串拼接
   - 安全性依赖参数化（易遗漏）

3. **无关系映射**
   - 需要手动JOIN
   - 多对多关系需手动处理

4. **无迁移工具**
   - 表结构变更需手工管理
   - 版本控制不完善

---

## 💡 实际使用示例

### 示例1: 修复前的SQL错误

**问题代码** (`core/performance/factorweave_performance_integration.py`):
```python
# ❌ 错误：使用不存在的列名
recent_strategies = self.analytics_db.execute_query("""
    SELECT strategy_name, AVG(confidence) as avg_confidence,  -- confidence列不存在！
           COUNT(*) as execution_count
    FROM strategy_execution_results 
    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
    GROUP BY strategy_name
""")
```

**修复后**:
```python
# ✅ 正确：使用实际存在的列
recent_strategies = self.analytics_db.execute_query("""
    SELECT strategy_name, 
           AVG(profit_loss) as avg_profit_loss, 
           COUNT(*) as execution_count,
           SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate
    FROM strategy_execution_results 
    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
    GROUP BY strategy_name
""")
```

**如果使用ORM会怎样？**
```python
# 假设使用SQLAlchemy ORM
from sqlalchemy import select, func

# ✅ 编译时就会报错
stmt = select(
    StrategyExecutionResult.strategy_name,
    func.avg(StrategyExecutionResult.confidence).label('avg_confidence'),  # IDE会提示：没有confidence属性！
    func.count().label('execution_count')
).where(
    StrategyExecutionResult.created_at >= datetime.now() - timedelta(hours=1)
).group_by(
    StrategyExecutionResult.strategy_name
)
```

**教训**：**原生SQL缺少编译时类型检查，容易出现运行时错误！**

---

### 示例2: 表结构管理

**当前方式**:
```python
# core/database/table_manager.py
# 硬编码表结构
self._schemas[TableType.KLINE_DATA] = TableSchema(
    table_type=TableType.KLINE_DATA,
    columns={
        'symbol': 'VARCHAR NOT NULL',
        'datetime': 'TIMESTAMP NOT NULL',
        'open': 'DECIMAL(10,4)',
        'high': 'DECIMAL(10,4)',
        'low': 'DECIMAL(10,4)',
        'close': 'DECIMAL(10,4)',
        'volume': 'BIGINT',
        # 如果要加新列，需要手动修改这里
    },
    primary_key=['symbol', 'datetime']
)

# 创建表
def create_table(self, table_type: TableType):
    schema = self._schemas[table_type]
    columns_def = ', '.join([f"{col} {dtype}" for col, dtype in schema.columns.items()])
    pk_def = f", PRIMARY KEY ({', '.join(schema.primary_key)})"
    sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def}{pk_def})"
    conn.execute(sql)
```

**如果使用ORM**:
```python
# 使用SQLAlchemy ORM + Alembic迁移
from sqlalchemy import Column, String, TIMESTAMP, Numeric, BigInteger
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class KlineData(Base):
    __tablename__ = 'kline_data'
    
    symbol = Column(String, primary_key=True, nullable=False)
    datetime = Column(TIMESTAMP, primary_key=True, nullable=False)
    open = Column(Numeric(10, 4))
    high = Column(Numeric(10, 4))
    low = Column(Numeric(10, 4))
    close = Column(Numeric(10, 4))
    volume = Column(BigInteger)
    # 新增列：直接在类中添加，然后运行alembic revision --autogenerate

# 自动生成迁移脚本
# $ alembic revision --autogenerate -m "add new column"
# $ alembic upgrade head
```

**对比**:
| 特性 | 当前方式 | ORM方式 |
|------|----------|---------|
| 类型安全 | ❌ 字符串定义 | ✅ 类型声明 |
| 重构友好 | ❌ 手动查找替换 | ✅ IDE重构支持 |
| 迁移管理 | ❌ 手工维护 | ✅ Alembic自动生成 |
| 学习曲线 | ✅ 简单直观 | ❌ 需学习ORM |
| 性能开销 | ✅ 无 | ❌ 有对象映射开销 |

---

## 🎯 架构设计合理性评估

### 设计决策分析

#### 为什么选择"SQLAlchemy QueuePool + 原生SQL"而不是"SQLAlchemy ORM"？

**✅ 正确的设计决策**

**原因1: 数据库特性匹配**
- DuckDB是OLAP数据库（列式存储，适合分析查询）
- ORM是为OLTP设计的（行式操作，CRUD操作）
- **不匹配！** ORM的对象模型不适合列式分析查询

**原因2: 性能考虑**
- 系统主要查询：聚合查询、时间序列分析、统计计算
- ORM的对象映射层对这些操作是纯开销
- 示例：查询1000条K线数据
  ```
  原生SQL:   SELECT * FROM kline_data → DataFrame (1步)
  ORM方式:   SELECT → Python对象列表 → DataFrame (2步，多次内存复制)
  ```

**原因3: Pandas集成**
- 数据分析框架（如Pandas、NumPy）直接使用DataFrame
- DuckDB原生支持`.fetchdf()`返回DataFrame
- ORM返回对象列表，需要转换为DataFrame（额外开销）

**原因4: 查询复杂度**
- 系统有很多复杂聚合查询（如窗口函数、PIVOT、QUALIFY）
- 这些在ORM中表达非常困难或不可能
- 原生SQL更直观和高效

### 潜在风险与改进建议

#### 风险1: SQL注入 ⚠️

**当前状态**: 部分使用参数化查询，部分使用字符串拼接

**风险示例**:
```python
# ❌ 不安全：字符串拼接
def query_by_symbol(self, symbol: str):
    sql = f"SELECT * FROM kline_data WHERE symbol = '{symbol}'"  # SQL注入风险！
    return conn.execute(sql).fetchdf()

# ✅ 安全：参数化查询
def query_by_symbol(self, symbol: str):
    sql = "SELECT * FROM kline_data WHERE symbol = ?"
    return conn.execute(sql, [symbol]).fetchdf()
```

**建议**: 
- ✅ 强制使用参数化查询
- ✅ 添加代码审查检查点
- ✅ 使用查询构建器（非ORM）

#### 风险2: 列名拼写错误 ⚠️

**当前状态**: 完全依赖手工维护，无编译时检查

**风险示例**:
```python
# ❌ 拼写错误，运行时才发现
sql = "SELECT strategy_name, AVG(confidence) FROM ..."  # confidence列不存在！

# ✅ 如果有类型提示
class StrategyColumns:
    STRATEGY_NAME = "strategy_name"
    PROFIT_LOSS = "profit_loss"  # 集中管理列名

sql = f"SELECT {StrategyColumns.STRATEGY_NAME}, AVG({StrategyColumns.PROFIT_LOSS}) FROM ..."
```

**建议**:
- ✅ 创建列名常量类
- ✅ 使用类型提示
- ✅ 添加表结构单元测试

#### 风险3: 表结构迁移困难 ⚠️

**当前状态**: 手工修改表结构，无版本控制

**建议**:
- ✅ 实现简单的迁移系统（参考Alembic设计）
- ✅ 版本化表结构定义
- ✅ 自动生成迁移脚本

---

## 🚀 改进方案建议

### 方案1: 轻量级查询构建器（推荐）

**目标**: 保持原生SQL性能，增加类型安全

```python
# query_builder.py
from typing import List, Optional
from enum import Enum

class Column(Enum):
    """列名枚举 - 类型安全"""
    SYMBOL = "symbol"
    DATETIME = "datetime"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"

class QueryBuilder:
    """轻量级查询构建器"""
    
    def __init__(self, table: str):
        self.table = table
        self._select_columns: List[str] = []
        self._where_clauses: List[tuple] = []
        self._order_by: Optional[str] = None
        self._limit: Optional[int] = None
    
    def select(self, *columns: Column) -> 'QueryBuilder':
        self._select_columns = [col.value for col in columns]
        return self
    
    def where(self, column: Column, operator: str, value) -> 'QueryBuilder':
        self._where_clauses.append((column.value, operator, value))
        return self
    
    def order_by(self, column: Column, desc: bool = False) -> 'QueryBuilder':
        self._order_by = f"{column.value} {'DESC' if desc else 'ASC'}"
        return self
    
    def limit(self, n: int) -> 'QueryBuilder':
        self._limit = n
        return self
    
    def build(self) -> tuple[str, list]:
        """构建SQL和参数"""
        select_part = f"SELECT {', '.join(self._select_columns) or '*'}"
        from_part = f"FROM {self.table}"
        
        where_part = ""
        params = []
        if self._where_clauses:
            conditions = []
            for col, op, val in self._where_clauses:
                conditions.append(f"{col} {op} ?")
                params.append(val)
            where_part = f"WHERE {' AND '.join(conditions)}"
        
        order_part = f"ORDER BY {self._order_by}" if self._order_by else ""
        limit_part = f"LIMIT {self._limit}" if self._limit else ""
        
        sql = ' '.join(filter(None, [select_part, from_part, where_part, order_part, limit_part]))
        return sql, params

# 使用示例
builder = QueryBuilder("kline_data")
sql, params = (builder
    .select(Column.SYMBOL, Column.DATETIME, Column.CLOSE)
    .where(Column.SYMBOL, "=", "000001")
    .where(Column.DATETIME, ">=", "2024-01-01")
    .order_by(Column.DATETIME, desc=True)
    .limit(100)
    .build())

# sql = "SELECT symbol, datetime, close FROM kline_data WHERE symbol = ? AND datetime >= ? ORDER BY datetime DESC LIMIT 100"
# params = ["000001", "2024-01-01"]

result = conn.execute(sql, params).fetchdf()
```

**优势**:
- ✅ 类型安全（使用Enum）
- ✅ 自动参数化（防SQL注入）
- ✅ 链式调用（优雅API）
- ✅ 无性能开销（最终还是原生SQL）
- ✅ 易于测试

### 方案2: 表结构版本管理

```python
# migration_manager.py
class MigrationManager:
    """简化的迁移管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_migration_table()
    
    def _init_migration_table(self):
        """初始化迁移记录表"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
    
    def apply_migration(self, version: str, description: str, up_sql: str):
        """应用迁移"""
        with self.get_connection() as conn:
            # 检查是否已应用
            existing = conn.execute(
                "SELECT version FROM schema_migrations WHERE version = ?",
                [version]
            ).fetchone()
            
            if existing:
                logger.info(f"Migration {version} already applied")
                return
            
            # 应用迁移
            conn.execute(up_sql)
            
            # 记录迁移
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                [version, description]
            )
            
            logger.info(f"✅ Applied migration {version}: {description}")

# 使用示例
manager = MigrationManager("db/factorweave_analytics.duckdb")

# 迁移1: 添加win_rate列
manager.apply_migration(
    version="20251018_001",
    description="Add win_rate column to strategy_execution_results",
    up_sql="""
        ALTER TABLE strategy_execution_results 
        ADD COLUMN IF NOT EXISTS win_rate DECIMAL(5,4)
    """
)
```

### 方案3: 列名常量集中管理

```python
# table_columns.py
class StrategyExecutionResultColumns:
    """策略执行结果表列名"""
    ID = "id"
    STRATEGY_NAME = "strategy_name"
    SYMBOL = "symbol"
    EXECUTION_TIME = "execution_time"
    SIGNAL_TYPE = "signal_type"
    PRICE = "price"
    QUANTITY = "quantity"
    PROFIT_LOSS = "profit_loss"
    METADATA = "metadata"
    CREATED_AT = "created_at"

class PerformanceMetricsColumns:
    """性能指标表列名"""
    ID = "id"
    METRIC_TYPE = "metric_type"
    METRIC_NAME = "metric_name"
    VALUE = "value"
    TIMESTAMP = "timestamp"
    TAGS = "tags"
    CREATED_AT = "created_at"

# 使用示例
from core.database.table_columns import StrategyExecutionResultColumns as SEC

sql = f"""
    SELECT {SEC.STRATEGY_NAME}, 
           AVG({SEC.PROFIT_LOSS}) as avg_profit_loss,
           COUNT(*) as execution_count
    FROM strategy_execution_results
    WHERE {SEC.CREATED_AT} >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
    GROUP BY {SEC.STRATEGY_NAME}
"""
```

**优势**:
- ✅ 集中管理列名
- ✅ IDE自动完成
- ✅ 重构友好
- ✅ 减少拼写错误

---

## 📊 总结

### 核心结论

**系统没有使用传统ORM，但架构设计是合理的！**

### 架构组成

```
┌────────────────────────────────────────────┐
│         SQLAlchemy QueuePool               │  连接池管理（✅ 有）
├────────────────────────────────────────────┤
│         原生SQL执行                         │  数据访问（✅ 有）
├────────────────────────────────────────────┤
│         DataClass Models                   │  数据模型（✅ 有）
├────────────────────────────────────────────┤
│         Schema Registry                    │  表结构管理（✅ 有）
├────────────────────────────────────────────┤
│         SQLAlchemy ORM                     │  对象映射（❌ 无）
└────────────────────────────────────────────┘
```

### 设计合理性

**✅ 合理的决策**:
1. 使用SQLAlchemy QueuePool（成熟的连接池）
2. 使用原生SQL（性能优越，灵活控制）
3. 使用DataClass（轻量级数据模型）
4. 适配DuckDB特性（OLAP数据库）

**⚠️ 需要改进**:
1. 增加查询构建器（类型安全）
2. 实现迁移管理系统（版本控制）
3. 集中管理列名（减少拼写错误）
4. 强制参数化查询（防SQL注入）

### 是否需要引入ORM？

**❌ 不建议！**

**原因**:
1. DuckDB是OLAP数据库，不适合ORM
2. 当前架构性能优越
3. 引入ORM会增加复杂度和开销
4. 轻量级改进即可解决痛点

**✅ 建议行动**:
1. 实现轻量级查询构建器
2. 添加表结构版本管理
3. 集中管理列名常量
4. 完善单元测试

---

**报告状态**: ✅ 完成  
**建议优先级**: 🔴 高（实现查询构建器和列名管理）

