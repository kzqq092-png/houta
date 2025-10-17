# DuckDB连接池配置实施方案（基于现有Config系统）

**日期**: 2025-10-12
**版本**: v1.0 Final
**状态**: ✅ **实施方案确定**

---

## 📋 方案概述

### 采用现有系统
✅ 使用现有的`ConfigService` + SQLite `config`表
✅ 配置以JSON格式存储
✅ 无需创建新表，直接扩展现有系统

### 配置键设计

**主配置键**: `connection_pool`

**配置结构**:
```json
{
  "connection_pool": {
    "pool_size": 5,
    "max_overflow": 10,
    "timeout": 30.0,
    "pool_recycle": 3600,
    "use_lifo": true,
    "pre_ping": false,
    "echo": false
  },
  "connection_pool_scenarios": {
    "realtime": {"timeout": 5.0},
    "monitoring": {"timeout": 10.0},
    "normal": {"timeout": 30.0},
    "batch": {"timeout": 60.0},
    "analytics": {"timeout": 120.0}
  },
  "duckdb_optimization": {
    "memory_limit_gb": null,
    "threads": null,
    "enable_object_cache": true,
    "enable_progress_bar": false,
    "temp_directory": null,
    "max_memory_percent": 0.5
  },
  "performance_tuning": {
    "checkpoint_threshold": 16777216,
    "wal_autocheckpoint": 1000,
    "worker_threads": 4,
    "io_threads": 4,
    "default_order": "ASC"
  }
}
```

### 新增可配置的性能参数

#### 1. 连接池核心参数
| 参数 | 默认值 | 范围 | 说明 | 性能影响 |
|-----|--------|------|------|---------|
| pool_size | 5 | 1-50 | 核心连接数 | 高并发场景需增加 |
| max_overflow | 10 | 0-100 | 最大溢出连接 | 突发流量缓冲 |
| timeout | 30.0 | 1-300 | 获取连接超时(秒) | 影响用户等待时间 |
| pool_recycle | 3600 | 60-86400 | 连接回收时间(秒) | 防止连接泄漏 |
| use_lifo | true | bool | 使用LIFO策略 | 提高空闲连接回收 |

#### 2. DuckDB优化参数
| 参数 | 默认值 | 范围 | 说明 | 性能影响 |
|-----|--------|------|------|---------|
| memory_limit_gb | null | 1-128 | 内存限制(GB) | 控制内存使用 |
| threads | null | 1-32 | 执行线程数 | 并行查询性能 |
| enable_object_cache | true | bool | 对象缓存 | 减少重复编译 |
| enable_progress_bar | false | bool | 进度条 | 调试用，生产禁用 |
| temp_directory | null | string | 临时目录 | SSD加速临时数据 |
| max_memory_percent | 0.5 | 0.1-0.9 | 最大内存百分比 | 系统内存50% |

#### 3. 性能调优参数
| 参数 | 默认值 | 范围 | 说明 | 性能影响 |
|-----|--------|------|------|---------|
| checkpoint_threshold | 16777216 | 1M-1G | 检查点阈值(字节) | 写入性能 |
| wal_autocheckpoint | 1000 | 100-10000 | WAL自动检查点 | 写入性能 |
| worker_threads | 4 | 1-16 | 工作线程数 | 并行处理能力 |
| io_threads | 4 | 1-16 | IO线程数 | 磁盘IO性能 |
| default_order | "ASC" | ASC/DESC | 默认排序 | 查询优化 |

---

## 💻 实施代码

### 1. 配置类定义

```python
# core/database/connection_pool_config.py

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class ConnectionPoolConfig:
    """连接池配置"""
    pool_size: int = 5
    max_overflow: int = 10
    timeout: float = 30.0
    pool_recycle: int = 3600
    use_lifo: bool = True
    pre_ping: bool = False
    echo: bool = False
    
    def validate(self) -> tuple[bool, str]:
        """验证配置"""
        if not (1 <= self.pool_size <= 50):
            return False, "pool_size必须在1-50之间"
        if not (0 <= self.max_overflow <= 100):
            return False, "max_overflow必须在0-100之间"
        if not (1.0 <= self.timeout <= 300.0):
            return False, "timeout必须在1-300秒之间"
        if not (60 <= self.pool_recycle <= 86400):
            return False, "pool_recycle必须在60-86400秒之间"
        return True, "配置有效"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionPoolConfig':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class DuckDBOptimizationConfig:
    """DuckDB优化配置"""
    memory_limit_gb: Optional[float] = None  # None表示自动
    threads: Optional[int] = None  # None表示自动
    enable_object_cache: bool = True
    enable_progress_bar: bool = False
    temp_directory: Optional[str] = None
    max_memory_percent: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PerformanceTuningConfig:
    """性能调优配置"""
    checkpoint_threshold: int = 16777216  # 16MB
    wal_autocheckpoint: int = 1000
    worker_threads: int = 4
    io_threads: int = 4
    default_order: str = "ASC"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ConnectionPoolConfigManager:
    """连接池配置管理器（基于ConfigService）"""
    
    def __init__(self, config_service):
        """
        Args:
            config_service: ConfigService实例
        """
        self.config_service = config_service
        self._ensure_default_config()
    
    def _ensure_default_config(self):
        """确保默认配置存在"""
        if not self.config_service.get('connection_pool'):
            default_config = {
                "connection_pool": ConnectionPoolConfig().to_dict(),
                "connection_pool_scenarios": {
                    "realtime": {"timeout": 5.0},
                    "monitoring": {"timeout": 10.0},
                    "normal": {"timeout": 30.0},
                    "batch": {"timeout": 60.0},
                    "analytics": {"timeout": 120.0}
                },
                "duckdb_optimization": DuckDBOptimizationConfig().to_dict(),
                "performance_tuning": PerformanceTuningConfig().to_dict()
            }
            
            for key, value in default_config.items():
                self.config_service.set(key, value)
            
            logger.info("✅ 连接池默认配置已初始化")
    
    def load_pool_config(self) -> ConnectionPoolConfig:
        """加载连接池配置"""
        config_dict = self.config_service.get('connection_pool')
        if config_dict:
            return ConnectionPoolConfig.from_dict(config_dict)
        return ConnectionPoolConfig()
    
    def save_pool_config(self, config: ConnectionPoolConfig) -> bool:
        """保存连接池配置"""
        valid, msg = config.validate()
        if not valid:
            raise ValueError(msg)
        
        self.config_service.set('connection_pool', config.to_dict())
        logger.info(f"✅ 连接池配置已保存: {config}")
        return True
    
    def load_optimization_config(self) -> DuckDBOptimizationConfig:
        """加载优化配置"""
        config_dict = self.config_service.get('duckdb_optimization')
        if config_dict:
            return DuckDBOptimizationConfig(**config_dict)
        return DuckDBOptimizationConfig()
    
    def load_tuning_config(self) -> PerformanceTuningConfig:
        """加载性能调优配置"""
        config_dict = self.config_service.get('performance_tuning')
        if config_dict:
            return PerformanceTuningConfig(**config_dict)
        return PerformanceTuningConfig()
    
    def get_scenario_timeout(self, scenario: str) -> float:
        """获取场景超时配置"""
        scenarios = self.config_service.get('connection_pool_scenarios', {})
        return scenarios.get(scenario, {}).get('timeout', 30.0)
```

### 2. 集成到FactorWeaveAnalyticsDB

```python
# 修改：core/database/factorweave_analytics_db.py

from .connection_pool_config import (
    ConnectionPoolConfigManager,
    DuckDBOptimizationConfig,
    PerformanceTuningConfig
)

class FactorWeaveAnalyticsDB:
    """分析数据库管理器 - 支持配置化"""
    
    def __init__(self, db_path: str = 'db/factorweave_analytics.duckdb'):
        # ...前置代码...
        
        # ✅ 加载配置
        self.config_manager = self._get_config_manager()
        pool_config = self.config_manager.load_pool_config()
        optimization_config = self.config_manager.load_optimization_config()
        
        # ✅ 使用配置创建连接池
        self.pool = DuckDBConnectionPool(
            db_path=str(self.db_path),
            pool_size=pool_config.pool_size,
            max_overflow=pool_config.max_overflow,
            timeout=pool_config.timeout,
            pool_recycle=pool_config.pool_recycle,
            use_lifo=pool_config.use_lifo
        )
        
        logger.info(f"✅ 使用配置创建连接池: {pool_config}")
        
        # ✅ 应用优化配置
        self._apply_optimization(optimization_config)
    
    def _get_config_manager(self):
        """获取配置管理器"""
        try:
            from core.containers import get_service_container
            from core.services.config_service import ConfigService
            
            container = get_service_container()
            config_service = container.resolve(ConfigService)
            
            return ConnectionPoolConfigManager(config_service)
        except Exception as e:
            logger.warning(f"无法获取ConfigService，使用默认配置: {e}")
            # 返回使用默认值的管理器
            return None
    
    def _apply_optimization(self, config: DuckDBOptimizationConfig):
        """应用优化配置"""
        try:
            with self.pool.get_connection() as conn:
                # 内存限制
                if config.memory_limit_gb:
                    conn.execute(f"SET memory_limit = '{config.memory_limit_gb}GB'")
                else:
                    # 自动计算
                    import psutil
                    memory_gb = psutil.virtual_memory().total / (1024**3)
                    limit = max(2.0, memory_gb * config.max_memory_percent)
                    conn.execute(f"SET memory_limit = '{limit:.1f}GB'")
                
                # 线程数
                if config.threads:
                    conn.execute(f"SET threads = {config.threads}")
                else:
                    # 自动计算
                    import psutil
                    threads = min(psutil.cpu_count(), 8)
                    conn.execute(f"SET threads = {threads}")
                
                # 其他优化
                conn.execute(f"SET enable_object_cache = {str(config.enable_object_cache).lower()}")
                conn.execute(f"SET enable_progress_bar = {str(config.enable_progress_bar).lower()}")
                
                if config.temp_directory:
                    conn.execute(f"SET temp_directory = '{config.temp_directory}'")
            
            logger.info(f"✅ 数据库优化配置已应用")
        except Exception as e:
            logger.warning(f"应用优化配置失败: {e}")
```

### 3. UI集成（SettingsDialog）

```python
# 修改：gui/dialogs/settings_dialog.py

# 在__init__中添加连接池配置tab
self.pool_config_tab = ConnectionPoolConfigTab(self)
self.tabs.addTab(self.pool_config_tab, "连接池配置")

# 新增ConnectionPoolConfigTab类
class ConnectionPoolConfigTab(QWidget):
    """连接池配置标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = self._get_config_manager()
        self.init_ui()
        self.load_config()
    
    def _get_config_manager(self):
        """获取配置管理器"""
        from core.containers import get_service_container
        from core.services.config_service import ConfigService
        from core.database.connection_pool_config import ConnectionPoolConfigManager
        
        container = get_service_container()
        config_service = container.resolve(ConfigService)
        return ConnectionPoolConfigManager(config_service)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 连接池配置组
        pool_group = QGroupBox("连接池配置")
        pool_layout = QFormLayout()
        
        # 池大小
        self.pool_size_spin = QSpinBox()
        self.pool_size_spin.setRange(1, 50)
        self.pool_size_spin.setValue(5)
        pool_layout.addRow("池大小:", self.pool_size_spin)
        
        # 最大溢出
        self.max_overflow_spin = QSpinBox()
        self.max_overflow_spin.setRange(0, 100)
        self.max_overflow_spin.setValue(10)
        pool_layout.addRow("最大溢出:", self.max_overflow_spin)
        
        # 超时
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(1.0, 300.0)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.setSuffix(" 秒")
        pool_layout.addRow("超时:", self.timeout_spin)
        
        # 回收时间
        self.recycle_spin = QSpinBox()
        self.recycle_spin.setRange(60, 86400)
        self.recycle_spin.setValue(3600)
        self.recycle_spin.setSuffix(" 秒")
        pool_layout.addRow("回收时间:", self.recycle_spin)
        
        pool_group.setLayout(pool_layout)
        layout.addWidget(pool_group)
        
        # 优化配置组
        opt_group = QGroupBox("DuckDB优化")
        opt_layout = QFormLayout()
        
        # 内存限制
        self.memory_spin = QDoubleSpinBox()
        self.memory_spin.setRange(0, 128)
        self.memory_spin.setValue(0)  # 0表示自动
        self.memory_spin.setSpecialValueText("自动")
        self.memory_spin.setSuffix(" GB")
        opt_layout.addRow("内存限制:", self.memory_spin)
        
        # 线程数
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(0, 32)
        self.threads_spin.setValue(0)  # 0表示自动
        self.threads_spin.setSpecialValueText("自动")
        opt_layout.addRow("线程数:", self.threads_spin)
        
        # 对象缓存
        self.object_cache_cb = QCheckBox("启用对象缓存")
        self.object_cache_cb.setChecked(True)
        opt_layout.addRow("", self.object_cache_cb)
        
        opt_group.setLayout(opt_layout)
        layout.addWidget(opt_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("应用配置")
        self.apply_btn.clicked.connect(self.apply_config)
        self.reset_btn = QPushButton("重置默认")
        self.reset_btn.clicked.connect(self.reset_config)
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.reset_btn)
        layout.addLayout(btn_layout)
        
        # 状态标签
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def load_config(self):
        """加载配置"""
        pool_config = self.config_manager.load_pool_config()
        self.pool_size_spin.setValue(pool_config.pool_size)
        self.max_overflow_spin.setValue(pool_config.max_overflow)
        self.timeout_spin.setValue(pool_config.timeout)
        self.recycle_spin.setValue(pool_config.pool_recycle)
        
        opt_config = self.config_manager.load_optimization_config()
        self.memory_spin.setValue(opt_config.memory_limit_gb or 0)
        self.threads_spin.setValue(opt_config.threads or 0)
        self.object_cache_cb.setChecked(opt_config.enable_object_cache)
    
    def apply_config(self):
        """应用配置"""
        from core.database.connection_pool_config import (
            ConnectionPoolConfig,
            DuckDBOptimizationConfig
        )
        
        # 创建配置
        pool_config = ConnectionPoolConfig(
            pool_size=self.pool_size_spin.value(),
            max_overflow=self.max_overflow_spin.value(),
            timeout=self.timeout_spin.value(),
            pool_recycle=self.recycle_spin.value()
        )
        
        # 验证
        valid, msg = pool_config.validate()
        if not valid:
            QMessageBox.warning(self, "配置错误", msg)
            return
        
        # 保存
        self.config_manager.save_pool_config(pool_config)
        
        # 保存优化配置
        opt_config = DuckDBOptimizationConfig(
            memory_limit_gb=self.memory_spin.value() or None,
            threads=self.threads_spin.value() or None,
            enable_object_cache=self.object_cache_cb.isChecked()
        )
        self.config_manager.config_service.set('duckdb_optimization', opt_config.to_dict())
        
        QMessageBox.information(
            self,
            "配置已保存",
            "连接池配置已保存到数据库。\n\n⚠️ 需要重启应用程序才能生效。"
        )
        self.status_label.setText("✅ 配置已保存（需重启）")
    
    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置为默认配置吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            from core.database.connection_pool_config import (
                ConnectionPoolConfig,
                DuckDBOptimizationConfig
            )
            
            default_pool = ConnectionPoolConfig()
            default_opt = DuckDBOptimizationConfig()
            
            self.config_manager.save_pool_config(default_pool)
            self.config_manager.config_service.set('duckdb_optimization', default_opt.to_dict())
            
            self.load_config()
            self.status_label.setText("✅ 已重置为默认配置")
```

---

## 📊 配置参数性能影响分析

### 高影响参数（建议可配置）
1. **pool_size** - 直接影响并发能力
2. **memory_limit_gb** - 影响大查询性能
3. **threads** - 影响并行查询性能
4. **timeout** - 影响用户体验

### 中影响参数（建议可配置）
1. **max_overflow** - 影响突发流量处理
2. **enable_object_cache** - 影响编译缓存
3. **checkpoint_threshold** - 影响写入性能

### 低影响参数（可选配置）
1. **pool_recycle** - 长期稳定性
2. **temp_directory** - 特定场景
3. **default_order** - 查询优化

---

## ✅ 实施检查清单

- [ ] 创建配置类 (ConnectionPoolConfig, DuckDBOptimizationConfig, PerformanceTuningConfig)
- [ ] 创建配置管理器 (ConnectionPoolConfigManager)
- [ ] 集成到FactorWeaveAnalyticsDB
- [ ] 创建UI配置面板 (ConnectionPoolConfigTab)
- [ ] 集成到SettingsDialog
- [ ] 测试配置读写
- [ ] 测试配置生效
- [ ] 更新文档

---

**实施人**: 待定  
**审核人**: 待审核  
**批准人**: 待批准  
**日期**: 2025-10-12

---

*文档版本: v1.0*  
*最后更新: 2025-10-12 21:50*

