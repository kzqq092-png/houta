# 插件异步初始化重构方案

## 📋 方案概述

**目标**：将插件的耗时网络连接操作从同步的 `initialize()` 方法中移除，改为异步后台执行，从而将应用启动时间从 **85秒** 降至 **<15秒**。

**影响范围**：
- 插件接口规范
- 插件管理器
- 东方财富插件
- 通达信插件
- 其他数据源插件（可选，逐步适配）

---

## 🎯 设计目标

### 功能目标
1. ✅ **快速启动**：应用启动时不等待插件连接，UI立即显示
2. ✅ **后台连接**：插件在后台线程中异步建立连接
3. ✅ **状态透明**：用户可以看到插件的连接状态（连接中/已连接/失败）
4. ✅ **优雅降级**：连接失败时不影响应用启动，可以稍后重试
5. ✅ **首次使用**：首次使用时如果插件未就绪，自动等待或提示用户

### 性能目标
| 阶段 | 修复前 | 修复后 | 改进 |
|-----|-------|-------|-----|
| **插件对象创建** | <1秒 | <1秒 | - |
| **同步初始化** | 70秒 | <2秒 | **97% ↓** |
| **异步连接（后台）** | N/A | 60秒 | 不阻塞UI |
| **应用启动总时间** | 85秒 | 15秒 | **82% ↓** |

---

## 🏗️ 架构设计

### 1. 插件状态机

```
┌─────────────┐
│  CREATED    │  插件对象已创建
└──────┬──────┘
       │ __init__()
       ↓
┌─────────────┐
│INITIALIZING │  正在同步初始化（<1秒）
└──────┬──────┘
       │ initialize()
       ↓
┌─────────────┐
│ INITIALIZED │  同步初始化完成，可以使用基本功能
└──────┬──────┘
       │ connect_async()
       ↓
┌─────────────┐
│ CONNECTING  │  正在异步连接（后台线程）
└──────┬──────┘
       │ (成功)
       ↓
┌─────────────┐     (失败)     ┌─────────────┐
│  CONNECTED  │ ←──────────────┤   FAILED    │
└─────────────┘                 └─────────────┘
       │                               │
       │ is_ready() == True           │ is_ready() == False
       ↓                               ↓
   可以使用                      可以重试连接
```

### 2. 插件接口扩展

```python
class IDataSourcePlugin(ABC):
    """数据源插件接口（扩展版）"""
    
    def __init__(self):
        """
        构造函数：仅创建对象，设置默认值
        耗时：<10ms
        """
        self.plugin_state = PluginState.CREATED
        self._connection_future = None  # 连接任务的 Future 对象
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        同步初始化：配置加载、对象创建、数据结构初始化
        耗时：<100ms
        不允许：网络请求、文件I/O（除非很快）、数据库连接
        """
        self.plugin_state = PluginState.INITIALIZING
        # ... 快速初始化逻辑 ...
        self.plugin_state = PluginState.INITIALIZED
        return True
    
    def connect_async(self) -> Future:
        """
        异步连接：在后台线程中建立网络连接
        返回：Future对象，可以查询连接状态
        """
        if self.plugin_state == PluginState.CONNECTED:
            # 已连接，直接返回成功的 Future
            future = Future()
            future.set_result(True)
            return future
        
        if self._connection_future and not self._connection_future.done():
            # 连接中，返回现有的 Future
            return self._connection_future
        
        # 启动新的连接任务
        self.plugin_state = PluginState.CONNECTING
        self._connection_future = self._executor.submit(self._do_connect)
        return self._connection_future
    
    def _do_connect(self) -> bool:
        """
        实际的连接逻辑（在后台线程中执行）
        """
        try:
            # ... 网络连接、服务器测试、连接池建立等耗时操作 ...
            self.plugin_state = PluginState.CONNECTED
            return True
        except Exception as e:
            self.plugin_state = PluginState.FAILED
            self.last_error = str(e)
            return False
    
    def is_ready(self) -> bool:
        """
        检查插件是否已就绪（已连接）
        """
        return self.plugin_state == PluginState.CONNECTED
    
    def wait_until_ready(self, timeout: float = 30.0) -> bool:
        """
        等待插件就绪
        用于首次使用时确保连接已建立
        """
        if self.is_ready():
            return True
        
        if not self._connection_future:
            # 还未开始连接，立即启动
            self.connect_async()
        
        try:
            # 等待连接完成
            result = self._connection_future.result(timeout=timeout)
            return result
        except TimeoutError:
            return False
```

### 3. 插件管理器修改

```python
class PluginManager:
    """插件管理器（修改后）"""
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="PluginConnector")
        self._connection_tasks = {}  # plugin_name -> Future
    
    def load_plugin(self, plugin_name: str, plugin_path: str) -> bool:
        """
        加载插件（快速返回，不等待连接）
        """
        # 1. 创建插件实例（快速）
        plugin_instance = plugin_class()  # <10ms
        
        # 2. 同步初始化（快速）
        plugin_instance.initialize(config)  # <100ms
        
        # 3. 启动异步连接（不等待）
        connection_future = plugin_instance.connect_async()
        self._connection_tasks[plugin_name] = connection_future
        
        # 4. 立即返回，不等待连接完成
        logger.info(f"✅ 插件加载完成（连接中）: {plugin_name}")
        return True
    
    def get_plugin_connection_status(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件连接状态
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {"status": "not_found"}
        
        return {
            "status": plugin.plugin_state.value,
            "is_ready": plugin.is_ready(),
            "last_error": getattr(plugin, 'last_error', None)
        }
    
    def wait_for_all_connections(self, timeout: float = 60.0):
        """
        等待所有插件连接完成（可选，用于测试或特殊场景）
        """
        from concurrent.futures import wait, FIRST_EXCEPTION
        
        futures = list(self._connection_tasks.values())
        done, not_done = wait(futures, timeout=timeout, return_when=FIRST_EXCEPTION)
        
        return {
            "completed": len(done),
            "pending": len(not_done),
            "total": len(futures)
        }
```

---

## 📝 实施步骤

### Phase 1: 接口定义（不影响现有代码）

**文件**: `core/plugin_interface.py`

1. 添加插件状态枚举 `PluginState`
2. 在 `IDataSourcePlugin` 中添加新方法：
   - `connect_async()`
   - `is_ready()`
   - `wait_until_ready()`
3. 标记旧方法为 `@deprecated`（但仍然兼容）

**代码示例**:

```python
from enum import Enum
from concurrent.futures import Future, ThreadPoolExecutor

class PluginState(Enum):
    """插件状态"""
    CREATED = "created"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"

# 在 IDataSourcePlugin 中添加
class IDataSourcePlugin(ABC):
    def __init__(self):
        super().__init__()
        self.plugin_state = PluginState.CREATED
        self._connection_future = None
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"Plugin-{self.__class__.__name__}")
        self.last_error = None
    
    @abstractmethod
    def connect_async(self) -> Future:
        """异步连接（子类实现）"""
        pass
    
    def is_ready(self) -> bool:
        """检查插件是否就绪"""
        return self.plugin_state == PluginState.CONNECTED
    
    def wait_until_ready(self, timeout: float = 30.0) -> bool:
        """等待插件就绪"""
        if self.is_ready():
            return True
        
        if not self._connection_future:
            self.connect_async()
        
        try:
            return self._connection_future.result(timeout=timeout)
        except Exception:
            return False
```

---

### Phase 2: 修改东方财富插件

**文件**: `plugins/data_sources/eastmoney_plugin.py`

**修改内容**:

```python
class EastMoneyStockPlugin(IDataSourcePlugin):
    """东方财富股票数据源插件（异步优化版）"""
    
    def __init__(self):
        super().__init__()  # 调用父类初始化
        self.logger = logger
        self.initialized = False
        self.config = DEFAULT_CONFIG.copy()
        self.session = None
        # ... 其他基本属性 ...
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        同步初始化（快速）
        移除：网络测试代码
        """
        try:
            self.plugin_state = PluginState.INITIALIZING
            
            merged = DEFAULT_CONFIG.copy()
            merged.update(config or {})
            self.config = merged
            
            # 创建会话（快速）
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://quote.eastmoney.com/',
                'Accept': 'application/json, text/plain, */*'
            })
            
            # 配置参数（快速）
            self.timeout = int(self.config.get('timeout', DEFAULT_CONFIG['timeout']))
            self.max_retries = int(self.config.get('max_retries', DEFAULT_CONFIG['max_retries']))
            
            self.initialized = True
            self.plugin_state = PluginState.INITIALIZED
            logger.info("东方财富插件同步初始化完成（<100ms）")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            self.plugin_state = PluginState.FAILED
            logger.error(f"东方财富插件初始化失败: {e}")
            return False
    
    def connect_async(self) -> Future:
        """
        异步连接
        新增：将网络测试移到这里
        """
        if self.plugin_state == PluginState.CONNECTED:
            future = Future()
            future.set_result(True)
            return future
        
        if self._connection_future and not self._connection_future.done():
            return self._connection_future
        
        self.plugin_state = PluginState.CONNECTING
        self._connection_future = self._executor.submit(self._do_connect)
        return self._connection_future
    
    def _do_connect(self) -> bool:
        """
        实际连接逻辑（后台线程执行）
        """
        try:
            logger.info("东方财富插件开始连接测试...")
            
            # 网络测试（原来在 initialize 中的代码）
            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            test_url = f"{base_url}{api['stock_list']}"
            params = {
                'pn': '1',
                'pz': '20',
                'po': '1',
                'np': '1',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                'fields': 'f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11'
            }
            
            response = self.session.get(test_url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and data['data']:
                    logger.info("✅ 东方财富插件连接成功，网络正常")
                    self.plugin_state = PluginState.CONNECTED
                    return True
                else:
                    logger.warning("⚠️  东方财富插件连接成功，但测试数据异常")
                    self.plugin_state = PluginState.CONNECTED  # 仍然认为连接成功
                    return True
            else:
                raise Exception(f"API返回状态码: {response.status_code}")
                
        except Exception as e:
            self.last_error = str(e)
            self.plugin_state = PluginState.FAILED
            logger.error(f"❌ 东方财富插件连接失败: {e}")
            return False
```

---

### Phase 3: 修改通达信插件

**文件**: `plugins/data_sources/tongdaxin_plugin.py`

**修改内容**:

```python
class TongdaxinStockPlugin(IDataSourcePlugin):
    """通达信股票数据源插件（异步优化版）"""
    
    def __init__(self):
        super().__init__()  # 调用父类初始化
        self.logger = logger.bind(module=__name__)
        self.initialized = False
        # ... 其他基本属性 ...
        
        # 连接池相关
        self.connection_pool = None
        self.server_list = []
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        同步初始化（快速）
        移除：连接池初始化代码
        """
        try:
            self.plugin_state = PluginState.INITIALIZING
            
            if not PYTDX_AVAILABLE:
                raise ImportError("pytdx库未安装")
            
            # 合并配置（快速）
            merged = self.DEFAULT_CONFIG.copy()
            merged.update(config or {})
            self.config = merged
            
            # 配置参数（快速）
            self.timeout = int(self.config.get('timeout', self.DEFAULT_CONFIG['timeout']))
            self.max_retries = int(self.config.get('max_retries', self.DEFAULT_CONFIG['max_retries']))
            self.use_connection_pool = self.config.get('use_connection_pool', True)
            
            # 初始化服务器列表（快速，不测试连接）
            self._initialize_servers()
            
            self.initialized = True
            self.plugin_state = PluginState.INITIALIZED
            logger.info("通达信插件同步初始化完成（<100ms）")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            self.plugin_state = PluginState.FAILED
            logger.error(f"通达信插件初始化失败: {e}")
            return False
    
    def connect_async(self) -> Future:
        """
        异步连接
        新增：将连接池初始化移到这里
        """
        if self.plugin_state == PluginState.CONNECTED:
            future = Future()
            future.set_result(True)
            return future
        
        if self._connection_future and not self._connection_future.done():
            return self._connection_future
        
        self.plugin_state = PluginState.CONNECTING
        self._connection_future = self._executor.submit(self._do_connect)
        return self._connection_future
    
    def _do_connect(self) -> bool:
        """
        实际连接逻辑（后台线程执行）
        """
        try:
            logger.info("通达信插件开始连接...")
            
            if self.use_connection_pool and self.server_list:
                # 初始化连接池（原来在 initialize 中的代码）
                connection_pool_size = int(self.config.get('connection_pool_size', 10))
                self.connection_pool = ConnectionPool(max_connections=connection_pool_size)
                
                logger.info("开始初始化连接池，选择最优服务器...")
                self.connection_pool.initialize(self.server_list)
                
                logger.info(f"✅ 通达信连接池初始化完成，活跃连接数: {self.connection_pool.connections.qsize()}")
                self.plugin_state = PluginState.CONNECTED
                return True
            else:
                # 单连接模式
                if self.config.get('auto_select_server', True):
                    self._select_best_server()
                
                self.api_client = TdxHq_API()
                
                if self._test_connection():
                    logger.info(f"✅ 通达信插件连接成功，服务器: {self.current_server}")
                    self.plugin_state = PluginState.CONNECTED
                    return True
                else:
                    raise Exception("连接测试失败")
                    
        except Exception as e:
            self.last_error = str(e)
            self.plugin_state = PluginState.FAILED
            logger.error(f"❌ 通达信插件连接失败: {e}")
            return False
```

---

### Phase 4: 修改插件管理器

**文件**: `core/plugin_manager.py`

**修改内容**:

```python
class PluginManager:
    """插件管理器（异步连接版）"""
    
    def __init__(self):
        # ... 现有代码 ...
        self._connection_executor = ThreadPoolExecutor(
            max_workers=10, 
            thread_name_prefix="PluginConnector"
        )
        self._connection_tasks = {}  # plugin_name -> Future
    
    def load_plugin(self, plugin_name: str, plugin_path: str) -> bool:
        """
        加载插件（快速返回，不等待连接）
        """
        try:
            # ... 现有的插件加载逻辑（创建实例、调用initialize）...
            
            # === 新增：启动异步连接 ===
            if isinstance(plugin_instance, IDataSourcePlugin):
                # 启动异步连接
                connection_future = plugin_instance.connect_async()
                self._connection_tasks[plugin_name] = connection_future
                
                # 添加回调，连接完成后记录日志
                connection_future.add_done_callback(
                    lambda f: self._on_plugin_connected(plugin_name, f)
                )
                
                logger.info(f"✅ 插件加载完成（后台连接中）: {plugin_name}")
            else:
                logger.info(f"✅ 插件加载完成: {plugin_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"插件加载失败 {plugin_name}: {e}")
            return False
    
    def _on_plugin_connected(self, plugin_name: str, future: Future):
        """
        插件连接完成的回调
        """
        try:
            result = future.result()
            if result:
                logger.info(f"🎉 插件连接成功: {plugin_name}")
            else:
                logger.warning(f"⚠️  插件连接失败: {plugin_name}")
        except Exception as e:
            logger.error(f"❌ 插件连接异常 {plugin_name}: {e}")
    
    def get_plugin_connection_status(self, plugin_name: str = None) -> Dict[str, Any]:
        """
        获取插件连接状态
        """
        if plugin_name:
            # 查询单个插件
            plugin = self.get_plugin(plugin_name)
            if not plugin:
                return {"status": "not_found"}
            
            return {
                "plugin_name": plugin_name,
                "status": plugin.plugin_state.value,
                "is_ready": plugin.is_ready(),
                "last_error": getattr(plugin, 'last_error', None)
            }
        else:
            # 查询所有数据源插件
            statuses = {}
            for name, plugin_info in self.data_source_plugins.items():
                plugin = plugin_info.instance
                statuses[name] = {
                    "status": plugin.plugin_state.value,
                    "is_ready": plugin.is_ready(),
                    "last_error": getattr(plugin, 'last_error', None)
                }
            return statuses
    
    def wait_for_plugin_connections(self, timeout: float = 60.0) -> Dict[str, Any]:
        """
        等待所有插件连接完成（可选，用于测试）
        """
        from concurrent.futures import wait, ALL_COMPLETED
        
        futures = list(self._connection_tasks.values())
        done, not_done = wait(futures, timeout=timeout, return_when=ALL_COMPLETED)
        
        # 统计结果
        connected = 0
        failed = 0
        for plugin_name, future in self._connection_tasks.items():
            if future.done():
                try:
                    if future.result():
                        connected += 1
                    else:
                        failed += 1
                except:
                    failed += 1
        
        return {
            "completed": len(done),
            "pending": len(not_done),
            "connected": connected,
            "failed": failed,
            "total": len(futures)
        }
```

---

### Phase 5: 添加UI连接状态指示器（可选）

**文件**: `gui/widgets/plugin_status_widget.py` （新建）

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import QTimer, pyqtSignal

class PluginStatusWidget(QWidget):
    """
    插件连接状态指示器
    显示在状态栏或侧边栏，实时显示插件连接状态
    """
    
    all_connected = pyqtSignal()  # 所有插件连接完成的信号
    
    def __init__(self, plugin_manager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self._init_ui()
        self._start_monitor()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        self.label = QLabel("插件连接中...")
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
    
    def _start_monitor(self):
        """启动定时器监控连接状态"""
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_status)
        self.timer.start(1000)  # 每秒更新一次
    
    def _update_status(self):
        """更新连接状态"""
        statuses = self.plugin_manager.get_plugin_connection_status()
        
        total = len(statuses)
        connected = sum(1 for s in statuses.values() if s['is_ready'])
        
        self.progress.setMaximum(total)
        self.progress.setValue(connected)
        self.label.setText(f"插件连接: {connected}/{total}")
        
        if connected == total:
            self.label.setText(f"✅ 所有插件已就绪 ({total}/{total})")
            self.timer.stop()
            self.all_connected.emit()
```

**集成到主窗口**:

```python
# 在 MainWindow 或 MainWindowCoordinator 中
def _create_status_bar(self):
    self.plugin_status_widget = PluginStatusWidget(self.plugin_manager)
    self.statusBar().addPermanentWidget(self.plugin_status_widget)
    
    # 连接信号
    self.plugin_status_widget.all_connected.connect(
        lambda: self.statusBar().showMessage("所有数据源已就绪", 3000)
    )
```

---

## 🧪 测试计划

### 测试1：启动性能测试

```python
import time

def test_startup_performance():
    """测试启动性能"""
    start = time.time()
    
    # 启动应用
    app = FactorWeaveQuantApplication()
    app.initialize()
    
    startup_time = time.time() - start
    
    # 断言启动时间<15秒
    assert startup_time < 15, f"启动时间过长: {startup_time}s"
    
    print(f"✅ 启动时间: {startup_time:.2f}s")
```

### 测试2：插件连接状态测试

```python
def test_plugin_connection_status():
    """测试插件连接状态"""
    plugin_manager = PluginManager()
    plugin_manager.load_all_plugins()
    
    # 立即检查状态（应该是 CONNECTING）
    status = plugin_manager.get_plugin_connection_status("data_sources.eastmoney_plugin")
    assert status['status'] in ['initialized', 'connecting']
    print(f"东方财富插件状态: {status['status']}")
    
    # 等待连接完成
    result = plugin_manager.wait_for_plugin_connections(timeout=60)
    print(f"连接结果: {result}")
    
    # 再次检查（应该是 CONNECTED）
    status = plugin_manager.get_plugin_connection_status("data_sources.eastmoney_plugin")
    assert status['status'] == 'connected'
    assert status['is_ready'] == True
    print(f"✅ 东方财富插件已就绪")
```

### 测试3：首次使用自动等待测试

```python
def test_first_use_wait():
    """测试首次使用时自动等待"""
    plugin_manager = PluginManager()
    plugin_manager.load_all_plugins()
    
    # 立即使用插件（可能还未连接完成）
    plugin = plugin_manager.get_plugin("data_sources.eastmoney_plugin")
    
    # 调用数据获取方法
    data = plugin.get_asset_list()
    
    # 应该能正常获取数据（内部自动等待连接）
    assert data is not None
    assert len(data) > 0
    print(f"✅ 获取资产列表成功: {len(data)} 条")
```

### 测试4：连接失败降级测试

```python
def test_connection_failure_graceful():
    """测试连接失败的优雅降级"""
    # 模拟网络不可用
    with mock.patch('requests.Session.get', side_effect=ConnectionError):
        plugin_manager = PluginManager()
        plugin_manager.load_all_plugins()
        
        # 等待连接尝试
        time.sleep(5)
        
        # 应用应该仍然正常启动
        status = plugin_manager.get_plugin_connection_status("data_sources.eastmoney_plugin")
        assert status['status'] == 'failed'
        assert status['is_ready'] == False
        print(f"✅ 连接失败，但应用正常运行")
```

---

## 📊 预期效果

### 启动流程对比

**修复前**：
```
[0s]   应用启动
[1s]   加载配置
[2s]   初始化服务
[3s]   开始加载插件
       ├─ AKShare (<1s)
       ├─ EastMoney (16s) ⛔ 阻塞
       └─ Tongdaxin (50s) ⛔ 阻塞
[69s]  插件加载完成
[85s]  UI显示 ❌ 用户体验差
```

**修复后**：
```
[0s]   应用启动
[1s]   加载配置
[2s]   初始化服务
[3s]   开始加载插件
       ├─ AKShare.initialize() (<100ms)
       ├─ EastMoney.initialize() (<100ms)
       └─ Tongdaxin.initialize() (<100ms)
[4s]   插件加载完成（同步初始化）
[15s]  UI显示 ✅ 用户体验好
       
[后台] 插件异步连接进行中...
       ├─ AKShare.connect_async() (5s)
       ├─ EastMoney.connect_async() (16s)
       └─ Tongdaxin.connect_async() (50s)
[65s]  所有插件连接完成
```

### 性能提升

| 指标 | 修复前 | 修复后 | 改进 |
|-----|-------|-------|-----|
| **应用启动时间** | 85秒 | 15秒 | **82% ↓** |
| **UI响应时间** | 85秒 | 15秒 | **立即可用** |
| **插件初始化** | 70秒（阻塞） | 0.3秒 | **99% ↓** |
| **插件连接** | N/A | 60秒（后台） | **不阻塞** |
| **用户感知启动时间** | 85秒 | 15秒 | **质的飞跃** |

---

## 🚀 部署建议

### 立即执行
1. ✅ Phase 1: 定义接口（不影响现有代码）
2. ✅ Phase 2: 修改东方财富插件
3. ✅ Phase 3: 修改通达信插件
4. ✅ Phase 4: 修改插件管理器

### 短期优化（1周内）
5. ✅ Phase 5: 添加UI状态指示器
6. ✅ 适配其他数据源插件（AKShare, Sina等）
7. ✅ 添加重连机制

### 中期改进（1月内）
8. 添加连接状态持久化（记住上次连接成功的服务器）
9. 添加智能预连接（应用启动后立即连接最常用的插件）
10. 优化连接池策略（根据实际使用情况动态调整）

---

## 💡 风险评估

| 风险 | 影响 | 缓解措施 |
|-----|-----|---------|
| **接口不兼容** | 高 | 保留旧接口，逐步废弃 |
| **首次使用卡顿** | 中 | 实现 wait_until_ready() 超时处理 |
| **连接失败无提示** | 中 | 添加UI状态指示器 |
| **线程安全问题** | 低 | 使用线程安全的数据结构 |

---

## 📞 支持信息

**方案版本**：v2.0.0  
**创建时间**：2025-10-17  
**预计实施时间**：2-3小时  

**相关文档**：
- `STARTUP_AND_RUNTIME_ERRORS_FIX_REPORT.md`
- `PLUGIN_DUPLICATE_LOADING_FIX_REPORT.md`

---

**方案状态**：✅ **已完成设计，待用户确认后实施**


