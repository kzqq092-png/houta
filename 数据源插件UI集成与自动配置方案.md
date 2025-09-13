# 数据源插件UI集成与自动配置方案

## 概述

本方案旨在将数据源插件的管理和配置完全集成到HIkyuu-UI中，让用户通过直观的图形界面管理复杂的数据源配置，系统自动将UI设置应用到底层的TET框架，实现"所见即所得"的配置体验。

## 1. 整体架构设计

### 1.1 系统分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    UI界面层 (PyQt/PySide)                    │
├─────────────────────────────────────────────────────────────┤
│                    配置管理层                                │
│  UIConfigManager | ConfigValidator | ConfigTransformer      │
├─────────────────────────────────────────────────────────────┤
│                    通信层                                   │
│    ConfigBridge | EventBus | StatusMonitor                 │
├─────────────────────────────────────────────────────────────┤
│                    集成层                                   │
│  PluginManager | RouterManager | CacheManager              │
├─────────────────────────────────────────────────────────────┤
│                 TET框架 (现有系统)                           │
│  DataSourceRouter | FieldMappingEngine | StandardQuery     │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件说明

- **UI界面层**：用户交互界面，提供直观的配置管理体验
- **配置管理层**：处理UI配置的存储、验证和转换
- **通信层**：UI与TET框架之间的通信桥梁
- **集成层**：将UI配置应用到TET框架的具体实现
- **TET框架**：现有的数据处理核心系统

## 2. UI界面设计方案

### 2.1 主数据源管理界面

**布局结构：**
```
┌─────────────────────────────────────────────────────────────┐
│  [刷新] [导入配置] [导出配置] [应用配置] [保存配置]          │
├─────────────────┬───────────────────────────────────────────┤
│ 数据源列表      │           选中数据源详细信息               │
│ ┌─────────────┐ │ ┌───────────────────────────────────────┐ │
│ │🟢 通达信    │ │ │ 数据源名称: 通达信                    │ │
│ │   健康度:95%│ │ │ 状态: ✅ 正常运行                     │ │
│ │─────────────│ │ │ 连接池大小: 5                        │ │
│ │🟡 东方财富  │ │ │ 响应时间: 120ms                      │ │
│ │   健康度:78%│ │ │ 成功率: 98.5%                        │ │
│ │─────────────│ │ │ 最后更新: 2分钟前                    │ │
│ │🔴 新浪财经  │ │ │ [启用] [禁用] [测试连接] [重置配置]   │ │
│ │   健康度:12%│ │ │                                       │ │
│ └─────────────┘ │ │ 配置参数:                            │ │
│                 │ │ • 服务器地址: [输入框]               │ │
│                 │ │ • 超时时间: [数字输入]               │ │
│                 │ │ • 重试次数: [数字输入]               │ │
│                 │ │ • 连接池: [启用/禁用]                │ │
│                 │ └───────────────────────────────────────┘ │
└─────────────────┴───────────────────────────────────────────┘
```

**功能特性：**
- 实时状态指示：绿色(正常)、黄色(警告)、红色(错误)
- 健康度评分：综合响应时间、成功率、稳定性的评分
- 一键操作：启用、禁用、测试连接、重置配置
- 参数配置：直观的表单式配置界面

### 2.2 智能路由策略配置界面

**布局结构：**
```
┌─────────────────────────────────────────────────────────────┐
│ [股票] [期货] [数字货币] [外汇]                              │
├─────────────────────────────────────────────────────────────┤
│ 股票数据路由策略                                            │
│                                                             │
│ 实时行情数据:                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 1. [通达信 ↕] ──→ 2. [东方财富 ↕] ──→ 3. [腾讯财经 ↕] │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ K线历史数据:                                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 1. [东方财富 ↕] ──→ 2. [通达信 ↕] ──→ 3. [新浪财经 ↕] │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 基本面数据:                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 1. [东方财富 ↕] ──→ 2. [同花顺 ↕]                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [添加备选方案] [智能推荐] [恢复默认] [预设模板]             │
└─────────────────────────────────────────────────────────────┘
```

**功能特性：**
- 拖拽排序：用户可以拖拽调整数据源优先级
- 资产分类：不同资产类型使用不同的路由策略
- 数据类型细分：实时、历史、基本面数据分别配置
- 智能推荐：根据历史性能数据推荐最佳配置

### 2.3 实时监控仪表板

**布局结构：**
```
┌─────────────────────────────────────────────────────────────┐
│ 数据源状态总览                    最近24小时性能趋势        │
│ ┌─────────────────┐              ┌───────────────────────┐ │
│ │     🟢 6个      │              │ 响应时间 (ms)         │ │
│ │   正常运行      │              │ 200┤                  │ │
│ │     🟡 2个      │              │ 150┤     ╱╲           │ │
│ │     警告        │              │ 100┤   ╱    ╲         │ │
│ │     🔴 1个      │              │  50┤ ╱        ╲       │ │
│ │     错误        │              │   0└─────────────────── │ │
│ └─────────────────┘              └───────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ 实时告警信息                                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🔴 14:23 新浪财经连接超时，已切换到备选数据源           │ │
│ │ 🟡 14:20 通达信响应时间异常，当前平均180ms              │ │
│ │ 🟢 14:15 东方财富数据更新正常                           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 数据源详细状态:                                             │
│ ┌─────────┬─────────┬─────────┬─────────┬─────────────────┐ │
│ │ 数据源  │ 状态    │ 响应时间│ 成功率  │ 最后活跃时间    │ │
│ ├─────────┼─────────┼─────────┼─────────┼─────────────────┤ │
│ │ 通达信  │ 🟢 正常 │ 120ms   │ 98.5%   │ 1分钟前         │ │
│ │ 东方财富│ 🟢 正常 │ 95ms    │ 99.2%   │ 30秒前          │ │
│ │ 腾讯财经│ 🟡 警告 │ 280ms   │ 95.1%   │ 3分钟前         │ │
│ │ 新浪财经│ 🔴 错误 │ 超时    │ 12.3%   │ 15分钟前        │ │
│ └─────────┴─────────┴─────────┴─────────┴─────────────────┘ │
│                                                             │
│ [自动刷新: 开启] [刷新间隔: 30秒] [导出报告]               │
└─────────────────────────────────────────────────────────────┘
```

**功能特性：**
- 状态总览：饼图显示数据源整体健康状况
- 性能趋势：图表显示响应时间、成功率等关键指标
- 实时告警：显示最新的错误和警告信息
- 详细状态表：表格形式显示所有数据源的详细状态

### 2.4 场景配置模板界面

**布局结构：**
```
┌─────────────────────────────────────────────────────────────┐
│ 预设配置模板                                                │
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│ │ 🚀 速度优先 │ │ 🛡️ 稳定优先 │ │ 🔄 全面覆盖 │             │
│ │             │ │             │ │             │             │
│ │ 优先使用响应│ │ 优先使用稳定│ │ 启用所有可用│             │
│ │ 最快的数据源│ │ 性最好的源  │ │ 的数据源    │             │
│ │             │ │             │ │             │             │
│ │ [应用模板]  │ │ [应用模板]  │ │ [应用模板]  │             │
│ └─────────────┘ └─────────────┘ └─────────────┘             │
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│ │ 📊 回测专用 │ │ ⚡ 实时交易 │ │ 🎯 自定义   │             │
│ │             │ │             │ │             │             │
│ │ 历史数据优先│ │ 实时数据优先│ │ 用户自定义  │             │
│ │ 准确性重要  │ │ 速度最重要  │ │ 配置方案    │             │
│ │             │ │             │ │             │             │
│ │ [应用模板]  │ │ [应用模板]  │ │ [创建模板]  │             │
│ └─────────────┘ └─────────────┘ └─────────────┘             │
│                                                             │
│ 当前使用模板: 稳定优先                                      │
│ [保存当前配置为模板] [删除模板] [重置为默认]                │
└─────────────────────────────────────────────────────────────┘
```

**功能特性：**
- 预设模板：提供常用的配置模板供快速选择
- 场景化配置：针对不同使用场景优化的配置
- 模板管理：用户可以创建、保存、删除自定义模板
- 一键切换：快速在不同配置间切换

## 3. 配置存储与管理

### 3.1 数据库表结构设计

**数据源配置表 (datasource_config)**
```sql
CREATE TABLE datasource_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,
    plugin_class VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    config_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**路由策略表 (routing_strategy)**
```sql
CREATE TABLE routing_strategy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type VARCHAR(20) NOT NULL,  -- stock, futures, crypto, forex
    data_type VARCHAR(20) NOT NULL,   -- realtime, kline, fundamental
    datasource_priority TEXT,         -- JSON array of datasource names in priority order
    fallback_strategy TEXT,           -- JSON config for fallback behavior
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**用户偏好表 (user_preferences)**
```sql
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(50) NOT NULL UNIQUE,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**配置模板表 (config_templates)**
```sql
CREATE TABLE config_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    template_config TEXT,  -- JSON config
    is_system_template BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 配置管理组件

**UIConfigManager**
```python
class UIConfigManager:
    """UI配置管理器，负责配置的读写和缓存"""
    
    def load_datasource_configs(self) -> List[Dict]:
        """加载所有数据源配置"""
        
    def save_datasource_config(self, config: Dict) -> bool:
        """保存数据源配置"""
        
    def load_routing_strategy(self, asset_type: str, data_type: str) -> Dict:
        """加载路由策略"""
        
    def save_routing_strategy(self, strategy: Dict) -> bool:
        """保存路由策略"""
        
    def apply_template(self, template_name: str) -> bool:
        """应用配置模板"""
```

## 4. 自动化配置应用机制

### 4.1 配置监听与通知系统

**ConfigBridge (配置桥梁)**
```python
class ConfigBridge:
    """UI配置与TET框架之间的通信桥梁"""
    
    def __init__(self, tet_pipeline):
        self.tet_pipeline = tet_pipeline
        self.event_bus = EventBus()
        self.config_manager = UIConfigManager()
        
    def on_config_changed(self, config_type: str, config_data: Dict):
        """配置变化时的回调处理"""
        
    def apply_datasource_config(self, config: Dict):
        """应用数据源配置到TET框架"""
        
    def apply_routing_strategy(self, strategy: Dict):
        """应用路由策略到TET框架"""
```

**EventBus (事件总线)**
```python
class EventBus:
    """异步事件通信机制"""
    
    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        
    def publish(self, event_type: str, data: Dict):
        """发布事件"""
        
    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
```

### 4.2 配置验证与转换

**ConfigValidator (配置验证器)**
```python
class ConfigValidator:
    """配置有效性验证"""
    
    def validate_datasource_config(self, config: Dict) -> Tuple[bool, str]:
        """验证数据源配置"""
        
    def validate_routing_strategy(self, strategy: Dict) -> Tuple[bool, str]:
        """验证路由策略"""
        
    def test_connection(self, datasource_config: Dict) -> Tuple[bool, str]:
        """测试数据源连接"""
```

**ConfigTransformer (配置转换器)**
```python
class ConfigTransformer:
    """UI配置与TET框架配置之间的转换"""
    
    def ui_to_tet_config(self, ui_config: Dict) -> Dict:
        """将UI配置转换为TET框架配置"""
        
    def tet_to_ui_config(self, tet_config: Dict) -> Dict:
        """将TET框架配置转换为UI配置"""
```

### 4.3 热更新机制

**HotReloadManager (热更新管理器)**
```python
class HotReloadManager:
    """支持不重启系统的配置热更新"""
    
    def reload_datasource_plugins(self, configs: List[Dict]):
        """热重载数据源插件"""
        
    def update_routing_strategy(self, strategy: Dict):
        """热更新路由策略"""
        
    def refresh_cache_config(self, cache_config: Dict):
        """刷新缓存配置"""
```

## 5. 状态监控与反馈

### 5.1 状态监控系统

**StatusMonitor (状态监控器)**
```python
class StatusMonitor:
    """收集和传递TET框架状态信息给UI"""
    
    def collect_datasource_status(self) -> List[Dict]:
        """收集数据源状态信息"""
        
    def collect_performance_metrics(self) -> Dict:
        """收集性能指标"""
        
    def collect_error_logs(self, limit: int = 100) -> List[Dict]:
        """收集错误日志"""
        
    def start_monitoring(self, interval: int = 30):
        """启动定时监控"""
```

### 5.2 健康度评估

**HealthScoreCalculator (健康度计算器)**
```python
class HealthScoreCalculator:
    """计算数据源健康度评分"""
    
    def calculate_health_score(self, metrics: Dict) -> int:
        """
        基于多个指标计算健康度评分 (0-100)
        - 响应时间 (30%)
        - 成功率 (40%)
        - 稳定性 (20%)
        - 数据质量 (10%)
        """
        
    def get_health_level(self, score: int) -> str:
        """根据评分获取健康等级"""
        # 90-100: 优秀
        # 70-89: 良好
        # 50-69: 一般
        # 30-49: 较差
        # 0-29: 严重
```

## 6. 用户体验优化

### 6.1 智能推荐系统

**SmartRecommendationEngine (智能推荐引擎)**
```python
class SmartRecommendationEngine:
    """基于历史数据和用户行为的智能配置推荐"""
    
    def recommend_routing_strategy(self, asset_type: str, data_type: str) -> Dict:
        """推荐最佳路由策略"""
        
    def recommend_datasource_priority(self, usage_pattern: Dict) -> List[str]:
        """推荐数据源优先级"""
        
    def detect_performance_issues(self) -> List[Dict]:
        """检测性能问题并提供优化建议"""
```

### 6.2 配置向导

**ConfigurationWizard (配置向导)**
```python
class ConfigurationWizard:
    """引导用户完成初始配置的向导系统"""
    
    def start_wizard(self) -> Dict:
        """启动配置向导"""
        
    def get_wizard_steps(self) -> List[Dict]:
        """获取向导步骤"""
        # 1. 选择主要使用场景
        # 2. 检测可用数据源
        # 3. 测试数据源连接
        # 4. 配置路由策略
        # 5. 设置监控选项
        # 6. 完成配置
        
    def apply_wizard_result(self, wizard_data: Dict) -> bool:
        """应用向导配置结果"""
```

### 6.3 可视化组件

**数据源状态可视化**
- 使用不同颜色表示状态：绿色(正常)、黄色(警告)、红色(错误)
- 健康度评分用进度条或圆形进度显示
- 响应时间用折线图显示趋势
- 成功率用柱状图对比显示

**路由策略可视化**
- 拖拽式优先级设置，支持鼠标拖拽排序
- 流程图显示数据流向和备选路径
- 实时预览配置效果

## 7. 实施步骤

### 7.1 第一阶段：基础架构搭建
1. 设计并创建数据库表结构
2. 实现基础的配置管理组件 (UIConfigManager)
3. 开发配置验证和转换机制
4. 创建基本的UI框架

### 7.2 第二阶段：核心功能实现
1. 实现数据源管理界面
2. 开发路由策略配置功能
3. 集成TET框架通信机制
4. 实现配置的热更新

### 7.3 第三阶段：监控和优化
1. 开发实时监控仪表板
2. 实现状态监控和健康度评估
3. 添加智能推荐功能
4. 优化用户体验

### 7.4 第四阶段：高级功能
1. 实现配置模板系统
2. 开发配置向导
3. 添加数据可视化组件
4. 完善错误处理和日志系统

## 8. 技术要点

### 8.1 性能考虑
- 使用缓存减少数据库查询
- 异步处理配置更新，避免阻塞UI
- 合理的监控频率，平衡实时性和性能

### 8.2 安全考虑
- 配置参数的输入验证和过滤
- 敏感信息(如API密钥)的加密存储
- 操作权限控制和审计日志

### 8.3 扩展性设计
- 插件式架构，便于添加新的数据源
- 配置格式的版本兼容性
- 模块化设计，便于功能扩展

## 9. 预期效果

通过实施本方案，用户将能够：

1. **直观管理**：通过图形界面直观地管理所有数据源插件
2. **智能配置**：系统自动推荐最佳配置，降低配置复杂度
3. **实时监控**：实时了解数据源状态，及时发现和解决问题
4. **一键切换**：在不同使用场景间快速切换配置
5. **无缝集成**：UI配置自动应用到底层系统，无需重启

这样的设计将大大提升系统的易用性，让不懂技术的用户也能轻松管理复杂的数据源配置，同时保持系统的高性能和稳定性。
