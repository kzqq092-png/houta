# 🔄 自适应连接池动态调整设计方案

**目标**: 根据实际负载自动调整DuckDB连接池配置，实现智能资源管理

**日期**: 2025-10-13  
**状态**: 设计中

---

## 📋 需求分析

### 用户需求
根据实际负载自动动态调整连接池配置，无需人工干预。

### 设计目标
1. ✅ **实时监控**: 持续监控连接池使用情况
2. ✅ **智能决策**: 根据负载模式自动调整配置
3. ✅ **平滑过渡**: 调整过程不影响现有连接
4. ✅ **安全边界**: 设置合理的最小/最大值
5. ✅ **历史学习**: 基于历史数据优化决策

---

## 🏗️ 架构设计

### 核心组件

```
┌─────────────────────────────────────────────────────┐
│           自适应连接池管理系统                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────┐      ┌──────────────────┐   │
│  │   指标收集器     │ ───> │   决策引擎       │   │
│  │  MetricsCollector│      │ DecisionEngine   │   │
│  └─────────────────┘      └──────────────────┘   │
│         │                          │               │
│         │                          ▼               │
│         │                  ┌──────────────────┐   │
│         │                  │   配置调整器     │   │
│         │                  │ ConfigAdjuster   │   │
│         │                  └──────────────────┘   │
│         │                          │               │
│         ▼                          ▼               │
│  ┌─────────────────┐      ┌──────────────────┐   │
│  │   历史数据库     │      │   连接池实例     │   │
│  │ MetricsHistory   │      │ ConnectionPool   │   │
│  └─────────────────┘      └──────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📊 监控指标

### 1. 连接池指标
- **pool_size**: 核心池大小
- **checked_out**: 活跃连接数
- **overflow**: 溢出连接数
- **wait_count**: 等待连接次数
- **usage_rate**: 使用率 (checked_out / pool_size)

### 2. 性能指标
- **avg_wait_time**: 平均等待时间
- **peak_concurrent**: 峰值并发数
- **throughput**: 吞吐量 (ops/sec)
- **error_rate**: 错误率

### 3. 系统指标
- **cpu_usage**: CPU使用率
- **memory_usage**: 内存使用率
- **query_latency**: 查询延迟

---

## 🧠 决策算法

### 调整策略

#### 1. 扩容（Scale Up）触发条件
```python
if (usage_rate > 0.8 and avg_wait_time > 0.1) or \
   (overflow > pool_size * 0.5) or \
   (wait_count > 100 in last_minute):
    # 增加 pool_size
    new_pool_size = min(pool_size * 1.5, MAX_POOL_SIZE)
```

#### 2. 缩容（Scale Down）触发条件
```python
if (usage_rate < 0.3 for 5 minutes) and \
   (overflow == 0) and \
   (pool_size > MIN_POOL_SIZE):
    # 减少 pool_size
    new_pool_size = max(pool_size * 0.8, MIN_POOL_SIZE)
```

#### 3. 稳定期（Hold）
```python
if 0.3 <= usage_rate <= 0.8:
    # 保持当前配置
    pass
```

---

## 🔧 实现细节

### 1. 指标收集器（MetricsCollector）

```python
class MetricsCollector:
    """连接池指标收集器"""
    
    def __init__(self, pool: DuckDBConnectionPool, interval: int = 10):
        self.pool = pool
        self.interval = interval  # 采集间隔（秒）
        self.metrics_history = deque(maxlen=1000)  # 最近1000条记录
        self._running = False
        self._thread = None
    
    def start(self):
        """启动指标收集"""
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
    
    def _collect_loop(self):
        """指标收集循环"""
        while self._running:
            metrics = self._collect_metrics()
            self.metrics_history.append(metrics)
            time.sleep(self.interval)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """收集当前指标"""
        status = self.pool.get_pool_status()
        
        return {
            'timestamp': datetime.now(),
            'pool_size': status['pool_size'],
            'checked_out': status['checked_out'],
            'overflow': status.get('overflow', 0),
            'usage_rate': status['checked_out'] / status['pool_size'] if status['pool_size'] > 0 else 0
        }
    
    def get_recent_metrics(self, window_seconds: int = 60) -> List[Dict]:
        """获取最近N秒的指标"""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        return [m for m in self.metrics_history if m['timestamp'] > cutoff]
```

### 2. 决策引擎（DecisionEngine）

```python
class AdaptiveDecisionEngine:
    """自适应决策引擎"""
    
    # 配置边界
    MIN_POOL_SIZE = 3
    MAX_POOL_SIZE = 50
    
    # 调整阈值
    SCALE_UP_USAGE_THRESHOLD = 0.8
    SCALE_DOWN_USAGE_THRESHOLD = 0.3
    SCALE_UP_WAIT_THRESHOLD = 0.1  # 秒
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.last_adjustment_time = None
        self.cooldown_seconds = 60  # 冷却期（避免频繁调整）
    
    def should_adjust(self) -> tuple[bool, Optional[int]]:
        """
        判断是否需要调整
        
        Returns:
            (是否调整, 新的pool_size)
        """
        # 冷却期检查
        if self.last_adjustment_time and \
           (datetime.now() - self.last_adjustment_time).seconds < self.cooldown_seconds:
            return False, None
        
        # 获取最近指标
        recent = self.collector.get_recent_metrics(window_seconds=60)
        if not recent:
            return False, None
        
        # 计算平均指标
        avg_usage = sum(m['usage_rate'] for m in recent) / len(recent)
        avg_overflow = sum(m.get('overflow', 0) for m in recent) / len(recent)
        current_pool_size = recent[-1]['pool_size']
        
        # 扩容决策
        if avg_usage > self.SCALE_UP_USAGE_THRESHOLD or \
           avg_overflow > current_pool_size * 0.5:
            new_size = min(int(current_pool_size * 1.5), self.MAX_POOL_SIZE)
            if new_size > current_pool_size:
                return True, new_size
        
        # 缩容决策（所有recent指标的usage都低于阈值）
        if all(m['usage_rate'] < self.SCALE_DOWN_USAGE_THRESHOLD for m in recent) and \
           all(m.get('overflow', 0) == 0 for m in recent) and \
           current_pool_size > self.MIN_POOL_SIZE:
            new_size = max(int(current_pool_size * 0.8), self.MIN_POOL_SIZE)
            if new_size < current_pool_size:
                return True, new_size
        
        return False, None
```

### 3. 自适应管理器（AdaptiveConnectionPoolManager）

```python
class AdaptiveConnectionPoolManager:
    """自适应连接池管理器"""
    
    def __init__(self, db: FactorWeaveAnalyticsDB):
        self.db = db
        self.collector = MetricsCollector(db.pool)
        self.decision_engine = AdaptiveDecisionEngine(self.collector)
        self._running = False
        self._thread = None
    
    def start(self):
        """启动自适应管理"""
        logger.info("🔄 启动自适应连接池管理...")
        
        # 启动指标收集
        self.collector.start()
        
        # 启动调整循环
        self._running = True
        self._thread = threading.Thread(target=self._adjustment_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """停止自适应管理"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("⏸️ 自适应连接池管理已停止")
    
    def _adjustment_loop(self):
        """调整循环"""
        while self._running:
            try:
                should_adjust, new_pool_size = self.decision_engine.should_adjust()
                
                if should_adjust:
                    self._apply_adjustment(new_pool_size)
                    self.decision_engine.last_adjustment_time = datetime.now()
                
            except Exception as e:
                logger.error(f"自适应调整失败: {e}")
            
            time.sleep(30)  # 每30秒检查一次
    
    def _apply_adjustment(self, new_pool_size: int):
        """应用调整"""
        old_size = self.db.pool.pool_size
        logger.info(f"🔄 自动调整连接池: {old_size} -> {new_pool_size}")
        
        # 创建新配置
        from core.database.connection_pool_config import ConnectionPoolConfig
        new_config = ConnectionPoolConfig(pool_size=new_pool_size)
        
        # 热重载
        self.db.reload_pool(new_config)
        
        logger.info(f"✅ 连接池已自动调整: pool_size={new_pool_size}")
```

---

## 🎯 使用示例

### 启用自适应管理

```python
from core.database.factorweave_analytics_db import get_analytics_db
from core.database.adaptive_connection_pool import AdaptiveConnectionPoolManager

# 获取数据库实例
db = get_analytics_db()

# 创建并启动自适应管理器
adaptive_manager = AdaptiveConnectionPoolManager(db)
adaptive_manager.start()

# 系统自动运行，无需人工干预
# ...

# 如需停止
adaptive_manager.stop()
```

### 集成到系统启动

```python
# main.py 或 app_init.py

def initialize_adaptive_pool_management():
    """初始化自适应连接池管理"""
    try:
        db = get_analytics_db()
        adaptive_manager = AdaptiveConnectionPoolManager(db)
        adaptive_manager.start()
        
        logger.info("✅ 自适应连接池管理已启动")
        return adaptive_manager
    except Exception as e:
        logger.error(f"❌ 自适应连接池管理启动失败: {e}")
        return None
```

---

## 📊 监控与可视化

### UI集成

在系统健康面板添加实时监控：

```python
class AdaptivePoolMonitorWidget(QWidget):
    """自适应连接池监控组件"""
    
    def __init__(self, adaptive_manager: AdaptiveConnectionPoolManager):
        super().__init__()
        self.manager = adaptive_manager
        self._init_ui()
        self._start_update_timer()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 实时指标
        self.current_size_label = QLabel("当前池大小: -")
        self.usage_rate_label = QLabel("使用率: -%")
        self.adjustment_count_label = QLabel("调整次数: 0")
        
        layout.addWidget(self.current_size_label)
        layout.addWidget(self.usage_rate_label)
        layout.addWidget(self.adjustment_count_label)
        
        # 历史图表
        self.chart = QChartView()
        layout.addWidget(self.chart)
    
    def _update_metrics(self):
        """更新显示的指标"""
        recent = self.manager.collector.get_recent_metrics(60)
        if recent:
            latest = recent[-1]
            self.current_size_label.setText(f"当前池大小: {latest['pool_size']}")
            self.usage_rate_label.setText(f"使用率: {latest['usage_rate']*100:.1f}%")
```

---

## ⚙️ 配置选项

### 可调参数

```python
@dataclass
class AdaptivePoolConfig:
    """自适应连接池配置"""
    
    # 边界
    min_pool_size: int = 3
    max_pool_size: int = 50
    
    # 阈值
    scale_up_usage_threshold: float = 0.8
    scale_down_usage_threshold: float = 0.3
    
    # 时间窗口
    metrics_window_seconds: int = 60
    cooldown_seconds: int = 60
    
    # 采集间隔
    collection_interval: int = 10
    
    # 调整策略
    scale_up_factor: float = 1.5
    scale_down_factor: float = 0.8
    
    # 是否启用
    enabled: bool = True
```

---

## 🔒 安全性考虑

### 1. 防止震荡
- **冷却期**: 调整后60秒内不再调整
- **趋势检测**: 需要多个连续采样点满足条件

### 2. 资源保护
- **最小值**: 不低于3个连接
- **最大值**: 不超过50个连接
- **步进限制**: 单次调整不超过50%

### 3. 异常处理
- 调整失败时回滚
- 指标收集异常时保持现状
- 系统资源不足时降级

---

## 📈 效果预期

### 优势
1. ✅ **自动化**: 无需人工干预
2. ✅ **高效**: 根据实际需求动态分配
3. ✅ **节省资源**: 低负载时释放连接
4. ✅ **高峰应对**: 高负载时自动扩容
5. ✅ **平滑**: 调整过程不影响业务

### 性能提升
- **资源利用率**: 提升30-50%
- **响应速度**: 高峰期提升20-30%
- **稳定性**: 减少等待超时

---

## 🚀 实施计划

### 阶段1: 核心实现（1-2小时）
- ✅ MetricsCollector
- ✅ AdaptiveDecisionEngine
- ✅ AdaptiveConnectionPoolManager

### 阶段2: 集成测试（30分钟）
- ✅ 单元测试
- ✅ 集成测试
- ✅ 压力测试

### 阶段3: UI集成（30分钟）
- ✅ 监控组件
- ✅ 配置界面
- ✅ 历史图表

### 阶段4: 文档与部署（15分钟）
- ✅ 用户文档
- ✅ 系统集成
- ✅ 配置持久化

---

## 📝 总结

自适应连接池管理系统将：
1. ✅ 自动监控连接池使用情况
2. ✅ 智能决策何时调整配置
3. ✅ 平滑地应用新配置
4. ✅ 提供实时监控和可视化
5. ✅ 确保系统高效稳定运行

**预计完成时间**: 2-3小时  
**用户体验**: 零干预，自动优化  
**系统影响**: 提升资源利用率30-50%

---

**下一步**: 确认方案后开始实施

