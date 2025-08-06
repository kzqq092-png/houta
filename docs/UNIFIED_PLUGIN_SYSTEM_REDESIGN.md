# HIkyuu插件管理系统统一重构设计

> **基于现状分析**: 深度分析现有插件架构和功能
> **融合设计**: 企业级安全 + 量化专家性能 + 现有接口兼容

## 🔍 现有插件系统分析

### 当前插件架构现状

#### ✅ **已有优势特性**
```python
完善的插件接口体系:
- 8种插件类型: INDICATOR/STRATEGY/DATA_SOURCE/ANALYSIS/UI_COMPONENT/EXPORT/NOTIFICATION/CHART_TOOL
- 4种插件分类: CORE/COMMUNITY/COMMERCIAL/EXPERIMENTAL
- 标准化生命周期: initialize() -> cleanup()
- 元数据装饰器: @plugin_metadata + @register_plugin
- 插件上下文系统: PluginContext (配置/事件/日志)

成熟的开发生态:
- 完整的插件市场 (plugin_market.py)
- 专业开发SDK (plugin_sdk.py)
- 示例插件库 (examples/*) 
- 项目模板生成器
- 测试框架集成

现有插件实例:
- 技术指标: MACD, RSI
- 交易策略: 双均线策略
- 数据源: Yahoo Finance, 情绪数据源
- 分析工具: 各类分析插件
```

#### ❌ **存在的问题**
```python
管理层面:
- 缺乏统一的数据库存储
- 状态管理依赖内存(重启丢失)
- 插件发现机制不够智能
- 缺乏性能监控和资源限制

安全层面:
- 无文件完整性验证
- 缺乏代码安全扫描
- 无运行时沙箱隔离
- 授权机制不完善

性能层面:
- 插件加载时间不可控
- 无资源使用限制
- 缺乏性能基准测试
- 无热插拔支持
```

## 🎯 统一重构设计目标

### 核心设计原则

```
兼容性优先: 保持现有插件接口100%兼容
性能导向: 量化交易级别的性能要求
安全增强: 企业级安全防护机制
管理专业: 数据库驱动的状态管理
```

## 🏗️ 新架构设计

### 分层架构设计

```
┌─────────────────────────────────────────────────────────┐
│                插件管理统一重构架构                      │
├─────────────────────────────────────────────────────────┤
│  插件接口层     │    管理服务层    │    数据存储层      │
│  ┌───────────┐   │  ┌─────────────┐ │  ┌─────────────┐   │
│  │现有8类型  │   │  │智能发现引擎 │ │  │混合数据库   │   │
│  │兼容接口   │◄──┼──│状态管理器   │◄┼──│内存+SQLite  │   │
│  │装饰器支持 │   │  │性能监控器   │ │  │缓存策略     │   │
│  └───────────┘   │  └─────────────┘ │  └─────────────┘   │
├─────────────────────────────────────────────────────────┤
│  安全防护层     │    性能优化层    │    兼容性层        │
│  ┌───────────┐   │  ┌─────────────┐ │  ┌─────────────┐   │
│  │轻量验证   │   │  │快速加载    │ │  │现有SDK     │   │
│  │沙箱隔离   │◄──┼──│资源限制    │◄┼──│装饰器保持   │   │
│  │完整性检查 │   │  │热插拔支持  │ │  │元数据格式   │   │
│  └───────────┘   │  └─────────────┘ │  └─────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 💾 混合数据库设计

### 双层存储策略

```sql
-- === 热数据层 (内存数据库) === --
-- 运行时状态，毫秒级查询
CREATE TABLE memory_plugins (
    plugin_name TEXT PRIMARY KEY,
    status TEXT NOT NULL,           -- loaded/running/stopped/error
    load_time_ms REAL,
    memory_usage_mb REAL,
    cpu_usage_percent REAL,
    last_heartbeat TIMESTAMP,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- === 持久化层 (文件数据库) === --
-- 完整插件信息，持久化存储
CREATE TABLE plugins_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_name TEXT UNIQUE NOT NULL,
    display_name TEXT,
    version TEXT NOT NULL,
    plugin_type TEXT NOT NULL,      -- 现有8种类型
    category TEXT NOT NULL,         -- 现有4种分类
    
    -- 文件信息
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_size INTEGER,
    
    -- 元数据 (兼容现有格式)
    author TEXT,
    email TEXT,
    description TEXT,
    website TEXT,
    license TEXT,
    dependencies TEXT,              -- JSON数组
    tags TEXT,                      -- JSON数组
    icon_path TEXT,
    
    -- 版本兼容性
    min_hikyuu_version TEXT,
    max_hikyuu_version TEXT,
    
    -- 状态管理
    status TEXT DEFAULT 'discovered',
    auto_discovered BOOLEAN DEFAULT 1,
    enabled BOOLEAN DEFAULT 0,
    
    -- 性能配置
    max_memory_mb INTEGER DEFAULT 256,
    max_cpu_percent INTEGER DEFAULT 10,
    timeout_seconds INTEGER DEFAULT 30,
    
    -- 审计字段
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_loaded_at TIMESTAMP,
    last_error TEXT,
    load_count INTEGER DEFAULT 0,
    
    -- 防重复
    UNIQUE(file_path, file_hash)
);

-- 插件配置表 (兼容现有PluginContext.get_plugin_config)
CREATE TABLE plugin_configs (
    plugin_name TEXT NOT NULL,
    config_key TEXT NOT NULL,
    config_value TEXT NOT NULL,     -- JSON格式
    config_type TEXT DEFAULT 'user', -- user/default/system
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (plugin_name, config_key, config_type)
);

-- 插件事件日志 (兼容现有事件系统)
CREATE TABLE plugin_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_name TEXT NOT NULL,
    event_type TEXT NOT NULL,       -- initialize/cleanup/error/performance
    event_message TEXT,
    event_data TEXT,                -- JSON格式
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 性能基准表 (新增)
CREATE TABLE plugin_performance_benchmarks (
    plugin_name TEXT PRIMARY KEY,
    avg_load_time_ms REAL,
    peak_memory_mb REAL,
    avg_cpu_percent REAL,
    success_rate REAL,
    last_benchmark_at TIMESTAMP,
    benchmark_count INTEGER DEFAULT 0
);
```

## 🔍 智能插件发现引擎

### 兼容现有+增强扫描

```python
class UnifiedPluginDiscoveryEngine:
    """统一插件发现引擎 - 兼容现有架构"""
    
    def __init__(self, db_service, existing_plugin_manager):
        self.db_service = db_service
        self.existing_manager = existing_plugin_manager  # 现有PluginManager
        self.classification_engine = PluginClassificationEngine()
        
    async def discover_and_sync_all_plugins(self) -> dict:
        """发现并同步所有插件 - 兼容现有架构"""
        discovery_results = {
            'total_discovered': 0,
            'new_plugins': 0,
            'updated_plugins': 0,
            'compatible_plugins': 0,
            'incompatible_plugins': 0,
            'classification_results': {}
        }
        
        try:
            # 1. 使用现有PluginManager的扫描路径
            scan_paths = [
                'plugins/',
                'plugins/examples/',
                'plugins/sentiment_data_sources/',
                'plugins/development/'
            ]
            
            # 2. 复用现有的排除规则
            excluded_files = ["plugin_interface.py", "plugin_market.py", "__init__.py"]
            
            for scan_path in scan_paths:
                await self._scan_directory_enhanced(scan_path, excluded_files, discovery_results)
            
            # 3. 同步现有插件管理器的已加载插件
            await self._sync_existing_loaded_plugins(discovery_results)
            
            return discovery_results
            
        except Exception as e:
            logger.error(f"统一插件发现失败: {e}")
            raise
    
    async def _scan_directory_enhanced(self, directory: str, excluded_files: list, results: dict):
        """增强目录扫描 - 兼容现有+新增功能"""
        try:
            directory_path = Path(directory)
            if not directory_path.exists():
                return
            
            for plugin_file in directory_path.glob("**/*.py"):
                if plugin_file.name in excluded_files or plugin_file.name.startswith("__"):
                    continue
                
                results['total_discovered'] += 1
                
                # 计算文件哈希
                file_hash = self._calculate_file_hash(plugin_file)
                
                # 检查数据库中是否已存在
                existing_plugin = await self.db_service.get_plugin_by_hash(file_hash)
                
                if existing_plugin:
                    # 检查文件是否被修改
                    if await self._verify_file_integrity(existing_plugin, plugin_file):
                        continue  # 文件未变更
                    else:
                        await self._handle_modified_plugin(existing_plugin, plugin_file, results)
                else:
                    # 新插件注册
                    await self._register_new_plugin_enhanced(plugin_file, file_hash, results)
                    
        except Exception as e:
            logger.error(f"增强目录扫描失败 {directory}: {e}")
    
    async def _register_new_plugin_enhanced(self, plugin_file: Path, file_hash: str, results: dict):
        """注册新插件 - 兼容现有装饰器"""
        try:
            # 1. 尝试解析现有装饰器元数据
            metadata = await self._extract_existing_metadata(plugin_file)
            
            if not metadata:
                # 2. 降级到传统分析
                metadata = await self._fallback_analysis(plugin_file)
            
            # 3. 验证插件兼容性
            compatibility_check = await self._check_plugin_compatibility(plugin_file, metadata)
            
            if not compatibility_check['compatible']:
                results['incompatible_plugins'] += 1
                logger.warning(f"插件不兼容: {plugin_file}, 原因: {compatibility_check['reason']}")
                return
            
            results['compatible_plugins'] += 1
            
            # 4. 智能分类 (兼容现有类型)
            if 'plugin_type' not in metadata:
                metadata['plugin_type'] = await self._classify_plugin_type(plugin_file, metadata)
            
            results['classification_results'][metadata['plugin_type']] = \
                results['classification_results'].get(metadata['plugin_type'], 0) + 1
            
            # 5. 注册到数据库
            plugin_record = self._build_plugin_record(plugin_file, file_hash, metadata)
            plugin_id = await self.db_service.register_plugin(plugin_record)
            
            results['new_plugins'] += 1
            logger.info(f"新插件注册成功: {metadata.get('name', plugin_file.stem)} (类型: {metadata['plugin_type']})")
            
        except Exception as e:
            logger.error(f"注册新插件失败 {plugin_file}: {e}")
    
    async def _extract_existing_metadata(self, plugin_file: Path) -> dict:
        """提取现有装饰器元数据"""
        try:
            with open(plugin_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST查找@plugin_metadata装饰器
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and any(
                    isinstance(decorator, ast.Call) and 
                    getattr(decorator.func, 'id', None) == 'plugin_metadata'
                    for decorator in node.decorator_list
                ):
                    # 找到@plugin_metadata装饰器
                    for decorator in node.decorator_list:
                        if (isinstance(decorator, ast.Call) and 
                            getattr(decorator.func, 'id', None) == 'plugin_metadata'):
                            
                            # 提取装饰器参数
                            metadata = {}
                            for keyword in decorator.keywords:
                                try:
                                    if keyword.arg in ['plugin_type', 'category']:
                                        # 处理枚举值
                                        if isinstance(keyword.value, ast.Attribute):
                                            metadata[keyword.arg] = keyword.value.attr.lower()
                                    else:
                                        # 处理普通值
                                        metadata[keyword.arg] = ast.literal_eval(keyword.value)
                                except:
                                    pass  # 忽略无法解析的值
                            
                            return metadata
            
            return {}
            
        except Exception as e:
            logger.debug(f"提取现有元数据失败: {e}")
            return {}
    
    async def _check_plugin_compatibility(self, plugin_file: Path, metadata: dict) -> dict:
        """检查插件兼容性"""
        compatibility_result = {
            'compatible': True,
            'reason': '',
            'required_fixes': []
        }
        
        try:
            # 1. 检查必要的导入
            with open(plugin_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否导入了插件接口
            required_imports = [
                'plugins.plugin_interface',
                'IPlugin', 'IIndicatorPlugin', 'IStrategyPlugin'
            ]
            
            missing_imports = []
            for required_import in required_imports:
                if required_import not in content and not any(
                    alternative in content for alternative in [
                        'from plugins.plugin_interface import',
                        'from .plugin_interface import'
                    ]
                ):
                    missing_imports.append(required_import)
            
            # 2. 检查基础接口实现
            tree = ast.parse(content)
            has_plugin_class = False
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # 检查是否继承了插件接口
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id.endswith('Plugin'):
                            has_plugin_class = True
                            break
            
            if not has_plugin_class:
                compatibility_result['compatible'] = False
                compatibility_result['reason'] = '未找到插件类定义'
                compatibility_result['required_fixes'].append('需要继承适当的插件接口类')
            
            # 3. 检查版本兼容性
            min_version = metadata.get('min_hikyuu_version', '0.0.0')
            max_version = metadata.get('max_hikyuu_version', '999.0.0')
            current_version = '2.0.1'  # 当前系统版本
            
            if not self._version_in_range(current_version, min_version, max_version):
                compatibility_result['compatible'] = False
                compatibility_result['reason'] = f'版本不兼容: 需要 {min_version}-{max_version}, 当前 {current_version}'
            
            return compatibility_result
            
        except Exception as e:
            compatibility_result['compatible'] = False
            compatibility_result['reason'] = f'兼容性检查异常: {e}'
            return compatibility_result
    
    def _build_plugin_record(self, plugin_file: Path, file_hash: str, metadata: dict) -> dict:
        """构建插件记录 - 兼容现有字段"""
        return {
            'plugin_name': metadata.get('name', plugin_file.stem),
            'display_name': metadata.get('name', plugin_file.stem),
            'version': metadata.get('version', '1.0.0'),
            'plugin_type': metadata.get('plugin_type', 'analysis'),
            'category': metadata.get('category', 'community'),
            
            'file_path': str(plugin_file),
            'file_hash': file_hash,
            'file_size': plugin_file.stat().st_size,
            
            'author': metadata.get('author', ''),
            'email': metadata.get('email', ''),
            'description': metadata.get('description', ''),
            'website': metadata.get('website', ''),
            'license': metadata.get('license', 'MIT'),
            'dependencies': json.dumps(metadata.get('dependencies', [])),
            'tags': json.dumps(metadata.get('tags', [])),
            'icon_path': metadata.get('icon_path', ''),
            
            'min_hikyuu_version': metadata.get('min_hikyuu_version', ''),
            'max_hikyuu_version': metadata.get('max_hikyuu_version', ''),
            
            'max_memory_mb': metadata.get('max_memory_mb', 256),
            'max_cpu_percent': metadata.get('max_cpu_percent', 10),
            'timeout_seconds': metadata.get('timeout_seconds', 30)
        }
```

## ⚡ 性能优化插件加载器

### 兼容现有+性能增强

```python
class HighPerformanceCompatibleLoader:
    """高性能兼容插件加载器"""
    
    def __init__(self, existing_plugin_manager, db_service):
        self.existing_manager = existing_plugin_manager
        self.db_service = db_service
        self.bytecode_cache = {}
        self.metadata_cache = {}
        
    async def load_plugin_optimized(self, plugin_name: str) -> dict:
        """优化的插件加载 - 兼容现有接口"""
        start_time = time.perf_counter()
        
        try:
            # 1. 从数据库获取插件信息
            plugin_record = await self.db_service.get_plugin_by_name(plugin_name)
            if not plugin_record:
                raise PluginNotFoundError(f"插件未注册: {plugin_name}")
            
            plugin_path = Path(plugin_record['file_path'])
            
            # 2. 文件完整性验证
            current_hash = self._calculate_file_hash(plugin_path)
            if current_hash != plugin_record['file_hash']:
                logger.warning(f"插件文件已变更: {plugin_name}")
                # 重新注册插件
                await self._update_plugin_record(plugin_name, plugin_path, current_hash)
            
            # 3. 字节码缓存加载
            cache_key = f"{plugin_path}_{plugin_record['file_hash']}"
            
            if cache_key in self.bytecode_cache:
                plugin_module = self.bytecode_cache[cache_key]
                logger.debug(f"从字节码缓存加载: {plugin_name}")
            else:
                # 编译并缓存
                plugin_module = await self._compile_and_cache_plugin(plugin_path, cache_key)
            
            # 4. 查找插件类 (复用现有逻辑)
            plugin_class = self.existing_manager._find_plugin_class(plugin_module)
            if not plugin_class:
                raise PluginLoadError(f"未找到插件类: {plugin_name}")
            
            # 5. 创建插件实例
            plugin_instance = plugin_class()
            
            # 6. 兼容现有初始化流程
            context = self._create_plugin_context(plugin_name, plugin_record)
            
            if hasattr(plugin_instance, 'initialize'):
                success = plugin_instance.initialize(context)
                if not success:
                    raise PluginInitializationError(f"插件初始化失败: {plugin_name}")
            
            # 7. 注册到现有管理器 (保持兼容性)
            self.existing_manager.plugin_instances[plugin_name] = plugin_instance
            self.existing_manager.plugin_metadata[plugin_name] = plugin_record
            
            # 8. 更新数据库状态
            await self.db_service.update_plugin_status(
                plugin_name, 'loaded', f"加载耗时: {(time.perf_counter() - start_time) * 1000:.2f}ms"
            )
            
            load_time = (time.perf_counter() - start_time) * 1000
            
            # 9. 记录性能基准
            await self._record_performance_benchmark(plugin_name, {
                'load_time_ms': load_time,
                'memory_usage_mb': self._get_memory_usage(),
                'success': True
            })
            
            logger.info(f"插件加载成功: {plugin_name} ({load_time:.2f}ms)")
            
            return {
                'plugin_instance': plugin_instance,
                'load_time_ms': load_time,
                'status': 'loaded_successfully',
                'from_cache': cache_key in self.bytecode_cache
            }
            
        except Exception as e:
            # 记录失败基准
            await self._record_performance_benchmark(plugin_name, {
                'load_time_ms': (time.perf_counter() - start_time) * 1000,
                'success': False,
                'error': str(e)
            })
            
            logger.error(f"插件加载失败 {plugin_name}: {e}")
            raise
    
    def _create_plugin_context(self, plugin_name: str, plugin_record: dict):
        """创建插件上下文 - 兼容现有PluginContext"""
        from plugins.plugin_interface import PluginContext
        
        # 复用现有PluginContext，但增强配置管理
        context = PluginContext(
            main_window=self.existing_manager.main_window,
            data_manager=self.existing_manager.data_manager,
            config_manager=self.existing_manager.config_manager,
            log_manager=self.existing_manager.log_manager
        )
        
        # 增强配置获取方法
        original_get_config = context.get_plugin_config
        
        async def enhanced_get_config(plugin_name_param):
            """增强的配置获取 - 支持数据库存储"""
            # 首先尝试从数据库获取
            db_config = await self.db_service.get_plugin_config(plugin_name_param)
            if db_config:
                return db_config
            
            # 降级到原有方法
            return original_get_config(plugin_name_param)
        
        context.get_plugin_config = enhanced_get_config
        
        return context
```

## 🔒 轻量级安全防护

### 非侵入式安全机制

```python
class LightweightSecurityManager:
    """轻量级安全管理器 - 不影响性能"""
    
    def __init__(self, db_service):
        self.db_service = db_service
        self.file_watchers = {}
        self.resource_monitors = {}
        
    async def verify_plugin_security(self, plugin_name: str, plugin_path: Path) -> dict:
        """轻量级安全验证"""
        security_result = {
            'file_integrity': True,
            'code_safety': True,
            'resource_limits': True,
            'security_score': 100,  # 0-100分
            'warnings': [],
            'action_required': False
        }
        
        try:
            # 1. 文件完整性检查 (~5ms)
            integrity_check = await self._check_file_integrity(plugin_name, plugin_path)
            security_result.update(integrity_check)
            
            # 2. 代码安全快速扫描 (~10ms)
            if security_result['file_integrity']:
                code_check = await self._quick_code_scan(plugin_path)
                security_result.update(code_check)
            
            # 3. 资源限制验证 (~1ms)
            resource_check = await self._verify_resource_limits(plugin_name)
            security_result.update(resource_check)
            
            # 4. 计算综合安全分数
            security_result['security_score'] = self._calculate_security_score(security_result)
            
            return security_result
            
        except Exception as e:
            logger.error(f"安全验证失败: {e}")
            security_result.update({
                'file_integrity': False,
                'code_safety': False,
                'security_score': 0,
                'warnings': [f"安全验证异常: {e}"],
                'action_required': True
            })
            return security_result
    
    async def _quick_code_scan(self, plugin_path: Path) -> dict:
        """快速代码安全扫描 - 针对量化代码优化"""
        scan_result = {
            'code_safety': True,
            'risk_patterns': [],
            'warnings': []
        }
        
        try:
            content = plugin_path.read_text(encoding='utf-8')
            
            # 量化交易允许的"危险"模式 (降低误报)
            QUANTITATIVE_SAFE_PATTERNS = [
                (r'numpy\.(array|zeros|ones)', 'numpy数组操作'),
                (r'pandas\.(DataFrame|Series)', 'pandas数据操作'),
                (r'exec\s*\(\s*[\'"]import', 'import语句动态执行'),
                (r'eval\s*\(\s*[\'"][\w\.\+\-\*/\s]+[\'"]', '数学表达式求值'),
            ]
            
            # 真正的高风险模式
            HIGH_RISK_PATTERNS = [
                (r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True', 'HIGH', '系统命令注入风险'),
                (r'os\.system\s*\([^)]*[;\|&]', 'HIGH', '命令注入风险'),
                (r'pickle\.loads?\s*\([^)]*input', 'HIGH', '反序列化攻击风险'),
                (r'exec\s*\([^)]*input', 'HIGH', '代码注入风险'),
                (r'open\s*\([^)]*[\'"]\/[^\'\"]*[\'"][^)]*[\'"]w', 'MEDIUM', '系统文件写入'),
            ]
            
            # 检查高风险模式
            for pattern, risk_level, description in HIGH_RISK_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    # 检查是否为量化安全模式
                    is_safe = any(
                        re.search(safe_pattern, content, re.IGNORECASE)
                        for safe_pattern, _ in QUANTITATIVE_SAFE_PATTERNS
                    )
                    
                    if not is_safe:
                        risk_info = {
                            'type': 'code_pattern',
                            'risk_level': risk_level,
                            'description': description,
                            'pattern': pattern,
                            'match_count': len(matches)
                        }
                        
                        scan_result['risk_patterns'].append(risk_info)
                        
                        if risk_level == 'HIGH':
                            scan_result['code_safety'] = False
                            scan_result['warnings'].append(f"高风险代码模式: {description}")
                        else:
                            scan_result['warnings'].append(f"中风险代码模式: {description}")
            
            return scan_result
            
        except Exception as e:
            logger.warning(f"代码扫描失败: {e}")
            scan_result['warnings'].append(f"代码扫描异常: {e}")
            return scan_result
```

## 🎛️ 统一插件管理服务

### 桥接现有+新增功能

```python
class UnifiedPluginManagementService:
    """统一插件管理服务 - 桥接现有架构"""
    
    def __init__(self, existing_plugin_manager):
        self.existing_manager = existing_plugin_manager
        self.db_service = PluginDatabaseService()
        self.discovery_engine = UnifiedPluginDiscoveryEngine(
            self.db_service, existing_plugin_manager
        )
        self.performance_loader = HighPerformanceCompatibleLoader(
            existing_plugin_manager, self.db_service
        )
        self.security_manager = LightweightSecurityManager(self.db_service)
        
        # 事件桥接
        self._setup_event_bridge()
    
    def _setup_event_bridge(self):
        """设置事件桥接 - 现有事件系统集成"""
        # 桥接现有插件管理器的信号
        if hasattr(self.existing_manager, 'plugin_loaded'):
            self.existing_manager.plugin_loaded.connect(self._on_plugin_loaded)
        if hasattr(self.existing_manager, 'plugin_enabled'):
            self.existing_manager.plugin_enabled.connect(self._on_plugin_enabled)
        if hasattr(self.existing_manager, 'plugin_disabled'):
            self.existing_manager.plugin_disabled.connect(self._on_plugin_disabled)
    
    async def initialize_unified_system(self) -> dict:
        """初始化统一系统"""
        initialization_result = {
            'success': True,
            'database_initialized': False,
            'plugins_discovered': 0,
            'plugins_migrated': 0,
            'compatibility_issues': 0,
            'performance_baseline_set': False
        }
        
        try:
            # 1. 初始化数据库
            await self.db_service.initialize_database()
            initialization_result['database_initialized'] = True
            
            # 2. 发现和注册所有插件
            discovery_results = await self.discovery_engine.discover_and_sync_all_plugins()
            initialization_result['plugins_discovered'] = discovery_results['total_discovered']
            initialization_result['compatibility_issues'] = discovery_results['incompatible_plugins']
            
            # 3. 迁移现有已加载插件状态
            migration_results = await self._migrate_existing_plugins()
            initialization_result['plugins_migrated'] = migration_results['migrated_count']
            
            # 4. 设置性能基准
            await self._establish_performance_baselines()
            initialization_result['performance_baseline_set'] = True
            
            logger.info(f"统一插件系统初始化完成: {initialization_result}")
            return initialization_result
            
        except Exception as e:
            logger.error(f"统一系统初始化失败: {e}")
            initialization_result['success'] = False
            initialization_result['error'] = str(e)
            return initialization_result
    
    async def _migrate_existing_plugins(self) -> dict:
        """迁移现有插件状态"""
        migration_result = {
            'migrated_count': 0,
            'failed_migrations': 0,
            'preserved_configs': 0
        }
        
        try:
            # 迁移已加载的插件实例
            for plugin_name, plugin_instance in self.existing_manager.plugin_instances.items():
                try:
                    # 保存现有配置
                    if hasattr(self.existing_manager, 'config_manager'):
                        existing_config = self.existing_manager.config_manager.get_plugin_config(plugin_name)
                        if existing_config:
                            await self.db_service.save_plugin_config(plugin_name, existing_config)
                            migration_result['preserved_configs'] += 1
                    
                    # 更新数据库状态
                    await self.db_service.update_plugin_status(plugin_name, 'loaded', '从现有系统迁移')
                    migration_result['migrated_count'] += 1
                    
                except Exception as e:
                    logger.error(f"迁移插件失败 {plugin_name}: {e}")
                    migration_result['failed_migrations'] += 1
            
            return migration_result
            
        except Exception as e:
            logger.error(f"插件状态迁移失败: {e}")
            raise
    
    # === 兼容现有接口的方法 === #
    
    def get_all_plugin_metadata(self) -> dict:
        """获取所有插件元数据 - 兼容现有接口"""
        # 桥接到现有方法，但增强数据来源
        existing_metadata = self.existing_manager.get_all_plugin_metadata()
        
        # TODO: 从数据库获取增强的元数据
        # enhanced_metadata = await self.db_service.get_all_plugins_metadata()
        
        return existing_metadata
    
    def load_plugin(self, plugin_name: str, plugin_path: Path = None) -> bool:
        """加载插件 - 兼容现有接口"""
        try:
            # 使用高性能加载器
            result = asyncio.run(self.performance_loader.load_plugin_optimized(plugin_name))
            return result['status'] == 'loaded_successfully'
        except Exception as e:
            logger.error(f"插件加载失败: {e}")
            return False
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件 - 兼容现有接口"""
        # 桥接到现有方法
        if hasattr(self.existing_manager, 'enable_plugin'):
            return self.existing_manager.enable_plugin(plugin_name)
        else:
            return self.load_plugin(plugin_name)
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件 - 兼容现有接口"""
        # 桥接到现有方法
        if hasattr(self.existing_manager, 'disable_plugin'):
            return self.existing_manager.disable_plugin(plugin_name)
        else:
            return self.unload_plugin(plugin_name)
    
    # === 事件处理 === #
    
    async def _on_plugin_loaded(self, plugin_name: str):
        """插件加载事件处理"""
        await self.db_service.update_plugin_status(plugin_name, 'loaded')
        await self.db_service.record_event(plugin_name, 'loaded', '插件加载成功')
    
    async def _on_plugin_enabled(self, plugin_name: str):
        """插件启用事件处理"""
        await self.db_service.update_plugin_status(plugin_name, 'enabled')
        await self.db_service.record_event(plugin_name, 'enabled', '插件启用成功')
    
    async def _on_plugin_disabled(self, plugin_name: str):
        """插件禁用事件处理"""
        await self.db_service.update_plugin_status(plugin_name, 'disabled')
        await self.db_service.record_event(plugin_name, 'disabled', '插件禁用')
```

## 🎯 实施策略

### 渐进式升级路径

```
Phase 1: 兼容性基础 (1周)
├── 数据库结构实现
├── 现有插件发现和注册
├── 状态同步桥接
└── 基础性能监控

Phase 2: 性能优化 (1周)  
├── 高性能加载器
├── 字节码缓存系统
├── 资源监控和限制
└── 性能基准建立

Phase 3: 安全增强 (1周)
├── 文件完整性验证
├── 轻量级代码扫描
├── 沙箱运行环境
└── 权限管理系统

Phase 4: 管理优化 (1周)
├── UI集成优化
├── 远程管理简化
├── 监控仪表板
└── 文档和测试
```

### 兼容性保证

```python
兼容性承诺:
✅ 现有8种插件类型完全支持
✅ @plugin_metadata装饰器语法不变
✅ @register_plugin装饰器语法不变  
✅ PluginContext接口保持不变
✅ 现有示例插件无需修改
✅ 插件开发SDK继续可用
✅ 插件市场功能保持
✅ 现有加载路径支持

性能保证:
🚀 插件加载时间: < 100ms (现有可能>1s)
🚀 内存占用优化: 减少30%缓存开销
🚀 状态查询: < 1ms (数据库索引优化)
🚀 并发加载: 支持10个插件同时加载

安全增强:
🔒 文件完整性自动验证
🔒 代码安全快速扫描 (< 20ms)
🔒 资源使用实时监控
🔒 权限细粒度控制
```

## 📊 成功指标

### 技术指标

```
性能指标:
- 插件发现速度: < 5秒 (100个插件)
- 插件加载速度: < 100ms/插件
- 状态查询速度: < 1ms
- 内存使用优化: 减少30%

兼容性指标:
- 现有插件兼容率: 100%
- API接口兼容率: 100%
- 装饰器语法兼容: 100%
- 开发工具兼容: 100%

安全指标:
- 文件完整性检测: 100%
- 代码安全扫描覆盖: > 95%
- 误报率: < 5%
- 安全响应时间: < 100ms

可靠性指标:
- 系统稳定性: > 99.9%
- 数据一致性: 100%
- 错误恢复能力: < 30秒
- 向后兼容性: 100%
```

这个统一重构设计既保持了现有插件系统的完整兼容性，又融合了企业级安全特性和量化专家级性能优化，为HIkyuu提供了一个面向未来的插件管理解决方案。 