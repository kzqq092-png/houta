# DuckDB连接池配置管理设计

**日期**: 2025-10-12  
**版本**: v1.0  
**状态**: 📋 **设计完成，待实施**

---

## 📋 需求分析

### 用户需求
1. **可配置性**: 连接池参数应可修改，而非硬编码
2. **持久化**: 配置应保存在数据库中，重启后保留
3. **动态修改**: 提供UI界面修改配置
4. **即时生效**: 配置修改后应能生效（需重启连接池）

### 当前问题
```python
# 当前实现：硬编码配置
self.pool = DuckDBConnectionPool(
    db_path=str(self.db_path),
    pool_size=5,          # 硬编码
    max_overflow=10,      # 硬编码
    timeout=30.0,         # 硬编码
    pool_recycle=3600,    # 硬编码
    pool_pre_ping=True    # 硬编码
)
```

**问题**:
- ❌ 无法动态修改
- ❌ 需要改代码才能调整
- ❌ 不同环境需要不同配置很麻烦

---

## 🎯 解决方案

### 1. 配置存储方案

#### 方案A: DuckDB配置表（推荐）✅

**优点**:
- ✅ 与系统数据库集成，无需额外存储
- ✅ 支持SQL查询和修改
- ✅ 支持版本历史
- ✅ 支持事务保证一致性

**配置表结构**:
```sql
CREATE TABLE IF NOT EXISTS system_config (
    config_key VARCHAR PRIMARY KEY,
    config_value VARCHAR,
    config_type VARCHAR,  -- 'string', 'int', 'float', 'bool'
    description VARCHAR,
    default_value VARCHAR,
    min_value DOUBLE,
    max_value DOUBLE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR
);

-- 连接池配置
INSERT INTO system_config VALUES
('pool.size', '5', 'int', '连接池核心大小', '5', 1, 50, NOW(), 'system'),
('pool.max_overflow', '10', 'int', '最大溢出连接数', '10', 0, 100, NOW(), 'system'),
('pool.timeout', '30.0', 'float', '获取连接超时(秒)', '30.0', 1.0, 300.0, NOW(), 'system'),
('pool.recycle', '3600', 'int', '连接回收时间(秒)', '3600', 60, 86400, NOW(), 'system');
```

#### 方案B: JSON配置文件

**优点**:
- ✅ 简单直接
- ✅ 易于备份
- ✅ 版本控制友好

**缺点**:
- ❌ 需要额外文件管理
- ❌ 多实例同步困难
- ❌ 无版本历史

**不采用**，使用方案A。

---

### 2. 配置管理架构

```
┌────────────────────────────────────────────────────────┐
│  UI Layer (设置对话框)                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  ConnectionPoolConfigPanel                       │  │
│  │  - 池大小滑块 (1-50)                              │  │
│  │  - 溢出连接滑块 (0-100)                           │  │
│  │  - 超时时间输入 (1-300秒)                         │  │
│  │  - 回收时间输入 (60-86400秒)                      │  │
│  │  - [应用] [重置为默认]                            │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                        ▼
┌────────────────────────────────────────────────────────┐
│  Config Manager Layer                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  ConnectionPoolConfigManager                     │  │
│  │  - load_config()                                 │  │
│  │  - save_config(config)                           │  │
│  │  - get_config_value(key)                         │  │
│  │  - set_config_value(key, value)                  │  │
│  │  - reset_to_defaults()                           │  │
│  │  - validate_config(config)                       │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                        ▼
┌────────────────────────────────────────────────────────┐
│  Storage Layer                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  DuckDB: system_config 表                        │  │
│  │  - config_key                                    │  │
│  │  - config_value                                  │  │
│  │  - config_type                                   │  │
│  │  - description                                   │  │
│  │  - min_value, max_value                          │  │
│  │  - updated_at, updated_by                        │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                        ▼
┌────────────────────────────────────────────────────────┐
│  Database Layer (FactorWeaveAnalyticsDB)               │
│  - 启动时加载配置                                       │
│  - 使用配置创建连接池                                   │
│  - 提供热重载接口                                       │
└────────────────────────────────────────────────────────┘
```

---

### 3. 配置类设计

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ConnectionPoolConfig:
    """连接池配置"""
    pool_size: int = 5
    max_overflow: int = 10
    timeout: float = 30.0
    pool_recycle: int = 3600
    use_lifo: bool = True
    
    # 验证规则
    MIN_POOL_SIZE = 1
    MAX_POOL_SIZE = 50
    MIN_OVERFLOW = 0
    MAX_OVERFLOW = 100
    MIN_TIMEOUT = 1.0
    MAX_TIMEOUT = 300.0
    MIN_RECYCLE = 60
    MAX_RECYCLE = 86400
    
    def validate(self) -> tuple[bool, str]:
        """验证配置"""
        if not (self.MIN_POOL_SIZE <= self.pool_size <= self.MAX_POOL_SIZE):
            return False, f"pool_size必须在{self.MIN_POOL_SIZE}-{self.MAX_POOL_SIZE}之间"
        
        if not (self.MIN_OVERFLOW <= self.max_overflow <= self.MAX_OVERFLOW):
            return False, f"max_overflow必须在{self.MIN_OVERFLOW}-{self.MAX_OVERFLOW}之间"
        
        if not (self.MIN_TIMEOUT <= self.timeout <= self.MAX_TIMEOUT):
            return False, f"timeout必须在{self.MIN_TIMEOUT}-{self.MAX_TIMEOUT}之间"
        
        if not (self.MIN_RECYCLE <= self.pool_recycle <= self.MAX_RECYCLE):
            return False, f"pool_recycle必须在{self.MIN_RECYCLE}-{self.MAX_RECYCLE}之间"
        
        return True, "配置有效"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'timeout': self.timeout,
            'pool_recycle': self.pool_recycle,
            'use_lifo': self.use_lifo
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionPoolConfig':
        """从字典创建"""
        return cls(
            pool_size=data.get('pool_size', 5),
            max_overflow=data.get('max_overflow', 10),
            timeout=data.get('timeout', 30.0),
            pool_recycle=data.get('pool_recycle', 3600),
            use_lifo=data.get('use_lifo', True)
        )
```

---

### 4. 配置管理器设计

```python
class ConnectionPoolConfigManager:
    """连接池配置管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_config_table()
    
    def _ensure_config_table(self):
        """确保配置表存在"""
        # 创建配置表和默认值
        pass
    
    def load_config(self) -> ConnectionPoolConfig:
        """加载配置"""
        try:
            # 从数据库读取配置
            config_dict = self._read_config_from_db()
            return ConnectionPoolConfig.from_dict(config_dict)
        except Exception as e:
            logger.warning(f"加载配置失败，使用默认配置: {e}")
            return ConnectionPoolConfig()
    
    def save_config(self, config: ConnectionPoolConfig) -> bool:
        """保存配置"""
        # 验证配置
        valid, msg = config.validate()
        if not valid:
            raise ValueError(msg)
        
        # 保存到数据库
        return self._write_config_to_db(config.to_dict())
    
    def get_config_value(self, key: str) -> Any:
        """获取单个配置值"""
        pass
    
    def set_config_value(self, key: str, value: Any, user: str = 'system') -> bool:
        """设置单个配置值"""
        pass
    
    def reset_to_defaults(self) -> ConnectionPoolConfig:
        """重置为默认配置"""
        default_config = ConnectionPoolConfig()
        self.save_config(default_config)
        return default_config
    
    def get_config_history(self, limit: int = 10) -> List[Dict]:
        """获取配置历史"""
        pass
```

---

### 5. UI集成设计

#### SettingsDialog 新增连接池配置页

```python
# gui/dialogs/settings_dialog.py

class ConnectionPoolConfigPanel(QWidget):
    """连接池配置面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = ConnectionPoolConfigManager("db/factorweave_analytics.duckdb")
        self.init_ui()
        self.load_current_config()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 池大小配置
        pool_size_group = QGroupBox("连接池大小")
        pool_size_layout = QHBoxLayout()
        self.pool_size_slider = QSlider(Qt.Horizontal)
        self.pool_size_slider.setRange(1, 50)
        self.pool_size_slider.setValue(5)
        self.pool_size_label = QLabel("5")
        pool_size_layout.addWidget(QLabel("池大小:"))
        pool_size_layout.addWidget(self.pool_size_slider)
        pool_size_layout.addWidget(self.pool_size_label)
        pool_size_group.setLayout(pool_size_layout)
        layout.addWidget(pool_size_group)
        
        # 溢出连接配置
        overflow_group = QGroupBox("溢出连接")
        overflow_layout = QHBoxLayout()
        self.max_overflow_slider = QSlider(Qt.Horizontal)
        self.max_overflow_slider.setRange(0, 100)
        self.max_overflow_slider.setValue(10)
        self.max_overflow_label = QLabel("10")
        overflow_layout.addWidget(QLabel("最大溢出:"))
        overflow_layout.addWidget(self.max_overflow_slider)
        overflow_layout.addWidget(self.max_overflow_label)
        overflow_group.setLayout(overflow_layout)
        layout.addWidget(overflow_group)
        
        # 超时配置
        timeout_group = QGroupBox("超时设置")
        timeout_layout = QHBoxLayout()
        self.timeout_spinbox = QDoubleSpinBox()
        self.timeout_spinbox.setRange(1.0, 300.0)
        self.timeout_spinbox.setValue(30.0)
        self.timeout_spinbox.setSuffix(" 秒")
        timeout_layout.addWidget(QLabel("获取连接超时:"))
        timeout_layout.addWidget(self.timeout_spinbox)
        timeout_group.setLayout(timeout_layout)
        layout.addWidget(timeout_group)
        
        # 回收时间配置
        recycle_group = QGroupBox("连接回收")
        recycle_layout = QHBoxLayout()
        self.recycle_spinbox = QSpinBox()
        self.recycle_spinbox.setRange(60, 86400)
        self.recycle_spinbox.setValue(3600)
        self.recycle_spinbox.setSuffix(" 秒")
        recycle_layout.addWidget(QLabel("回收时间:"))
        recycle_layout.addWidget(self.recycle_spinbox)
        recycle_group.setLayout(recycle_layout)
        layout.addWidget(recycle_group)
        
        # 连接信号
        self.pool_size_slider.valueChanged.connect(
            lambda v: self.pool_size_label.setText(str(v))
        )
        self.max_overflow_slider.valueChanged.connect(
            lambda v: self.max_overflow_label.setText(str(v))
        )
        
        # 按钮
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("应用配置")
        self.apply_button.clicked.connect(self.apply_config)
        self.reset_button = QPushButton("重置为默认")
        self.reset_button.clicked.connect(self.reset_config)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        layout.addLayout(button_layout)
        
        # 状态信息
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
    
    def load_current_config(self):
        """加载当前配置"""
        config = self.config_manager.load_config()
        self.pool_size_slider.setValue(config.pool_size)
        self.max_overflow_slider.setValue(config.max_overflow)
        self.timeout_spinbox.setValue(config.timeout)
        self.recycle_spinbox.setValue(config.pool_recycle)
    
    def apply_config(self):
        """应用配置"""
        config = ConnectionPoolConfig(
            pool_size=self.pool_size_slider.value(),
            max_overflow=self.max_overflow_slider.value(),
            timeout=self.timeout_spinbox.value(),
            pool_recycle=self.recycle_spinbox.value()
        )
        
        # 验证配置
        valid, msg = config.validate()
        if not valid:
            QMessageBox.warning(self, "配置错误", msg)
            return
        
        # 保存配置
        if self.config_manager.save_config(config):
            QMessageBox.information(
                self, 
                "配置已保存", 
                "连接池配置已保存。\n\n⚠️ 需要重启应用程序才能生效。"
            )
            self.status_label.setText("✅ 配置已保存（需要重启生效）")
        else:
            QMessageBox.critical(self, "保存失败", "配置保存失败")
    
    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置为默认配置吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            config = self.config_manager.reset_to_defaults()
            self.load_current_config()
            self.status_label.setText("✅ 已重置为默认配置")
```

---

### 6. 热重载机制设计

```python
class FactorWeaveAnalyticsDB:
    """支持配置热重载的数据库管理器"""
    
    def reload_pool(self, new_config: Optional[ConnectionPoolConfig] = None):
        """重新加载连接池"""
        # 1. 关闭当前连接池
        if hasattr(self, 'pool'):
            logger.info("关闭当前连接池...")
            self.pool.dispose()
        
        # 2. 加载新配置
        if new_config is None:
            config_manager = ConnectionPoolConfigManager(str(self.db_path))
            new_config = config_manager.load_config()
        
        logger.info(f"使用新配置重新加载连接池: {new_config}")
        
        # 3. 创建新连接池
        self.pool = DuckDBConnectionPool(
            db_path=str(self.db_path),
            pool_size=new_config.pool_size,
            max_overflow=new_config.max_overflow,
            timeout=new_config.timeout,
            pool_recycle=new_config.pool_recycle,
            use_lifo=new_config.use_lifo
        )
        
        logger.info("✅ 连接池已重新加载")
```

---

## 📋 实施计划

### Phase 1: 配置存储 (优先级: 高)
- [ ] 创建`ConnectionPoolConfig`配置类
- [ ] 创建`system_config`配置表
- [ ] 实现配置表初始化和默认值

### Phase 2: 配置管理器 (优先级: 高)
- [ ] 创建`ConnectionPoolConfigManager`
- [ ] 实现`load_config()` / `save_config()`
- [ ] 实现配置验证逻辑

### Phase 3: UI集成 (优先级: 中)
- [ ] 在`SettingsDialog`中添加连接池配置页
- [ ] 实现配置面板UI
- [ ] 连接保存和重置逻辑

### Phase 4: 热重载 (优先级: 低)
- [ ] 实现`reload_pool()`方法
- [ ] 添加重载API
- [ ] 实现无缝切换（可选）

### Phase 5: 测试验证 (优先级: 高)
- [ ] 配置读写测试
- [ ] 配置验证测试
- [ ] UI交互测试
- [ ] 热重载测试

---

## 📝 调用链分析

### 配置加载链路

```
应用启动
   │
   ├─> FactorWeaveAnalyticsDB.__init__()
   │      │
   │      ├─> ConnectionPoolConfigManager.load_config()
   │      │      │
   │      │      ├─> 读取 system_config 表
   │      │      └─> 返回 ConnectionPoolConfig
   │      │
   │      └─> DuckDBConnectionPool(config.to_dict())
   │
   └─> 连接池就绪
```

### 配置修改链路

```
用户打开设置对话框
   │
   ├─> SettingsDialog.show()
   │      │
   │      ├─> ConnectionPoolConfigPanel显示
   │      │      │
   │      │      └─> load_current_config()
   │      │
   │      └─> 用户修改配置
   │
   ├─> 用户点击"应用"
   │      │
   │      ├─> ConnectionPoolConfigPanel.apply_config()
   │      │      │
   │      │      ├─> ConnectionPoolConfig.validate()
   │      │      │
   │      │      ├─> ConnectionPoolConfigManager.save_config()
   │      │      │      │
   │      │      │      └─> 写入 system_config 表
   │      │      │
   │      │      └─> 提示需要重启
   │      │
   │      └─> 配置已保存
   │
   └─> 用户重启应用
          │
          └─> 新配置生效
```

---

## 🔒 安全考虑

1. **配置验证**: 所有配置值必须通过验证才能保存
2. **范围限制**: 参数有明确的最小/最大值限制
3. **默认值**: 提供安全的默认值，防止配置丢失
4. **错误处理**: 配置加载失败时使用默认值
5. **权限控制**: 配置修改应记录操作用户（未来）

---

## 📚 参考文档

- SQLAlchemy连接池配置: https://docs.sqlalchemy.org/en/20/core/pooling.html
- DuckDB配置管理: https://duckdb.org/docs/configuration

---

**设计人**: AI Assistant  
**审核人**: 待审核  
**批准人**: 待批准  
**日期**: 2025-10-12

---

*文档版本: v1.0*  
*最后更新: 2025-10-12 21:40*

