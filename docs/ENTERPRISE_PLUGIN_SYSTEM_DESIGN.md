# 企业级插件管理系统设计方案

## 🎯 设计目标

基于数据库为中心的插件管理系统，支持远程授权、防篡改、自动分类录入，对标企业级专业软件。

## 🏗️ 系统架构设计

### 1. 整体架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    企业级插件管理系统                        │
├─────────────────────────────────────────────────────────────┤
│  远程管理端        │        本地客户端        │    安全层    │
│  ┌─────────────┐   │   ┌─────────────────┐   │  ┌─────────┐ │
│  │授权服务器   │◄──┼──►│插件发现引擎     │◄──┼──│数字签名 │ │
│  │插件仓库     │   │   │注册服务         │   │  │远程授权 │ │
│  │安全校验     │   │   │数据库管理       │   │  │访问控制 │ │
│  └─────────────┘   │   └─────────────────┘   │  └─────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2. 核心设计原则

#### 🔒 安全优先
- 数字签名验证所有插件
- 远程授权管理
- 加密通信传输
- 访问权限控制

#### 📊 数据库中心
- 所有状态以数据库为准
- 内存缓存作为性能优化
- 自动数据同步机制
- 防重复录入保护

#### 🚀 企业级特性
- 远程管理支持
- 批量操作能力
- 审计日志记录
- 高可用设计

## 💾 数据库设计方案

### 核心表结构扩展

```sql
-- 1. 插件注册表 (扩展版)
CREATE TABLE plugins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    plugin_type TEXT NOT NULL,  -- 自动分类结果
    status TEXT NOT NULL DEFAULT 'discovered',
    description TEXT DEFAULT '',
    author TEXT DEFAULT '',
    file_path TEXT NOT NULL,    -- 源文件路径
    file_hash TEXT NOT NULL,    -- 文件哈希值 (防篡改)
    signature_hash TEXT,        -- 数字签名哈希
    signature_valid BOOLEAN DEFAULT 0,  -- 签名验证状态
    license_key TEXT,           -- 授权密钥
    license_valid BOOLEAN DEFAULT 0,    -- 授权验证状态
    license_expires_at TIMESTAMP,       -- 授权过期时间
    auto_discovered BOOLEAN DEFAULT 1,  -- 是否自动发现
    install_source TEXT DEFAULT 'local', -- local/remote/market
    dependencies TEXT DEFAULT '[]',
    capabilities TEXT DEFAULT '[]',     -- 插件能力列表
    security_level INTEGER DEFAULT 1,   -- 安全等级 1-5
    remote_url TEXT DEFAULT '',
    checksum TEXT NOT NULL,             -- 完整性校验
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scanned_at TIMESTAMP,          -- 最后扫描时间
    scan_result TEXT DEFAULT '{}',      -- 扫描结果JSON
    UNIQUE(file_path, file_hash)        -- 防重复约束
);

-- 2. 插件分类规则表
CREATE TABLE plugin_classification_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL,    -- file_pattern/class_pattern/content_pattern
    pattern TEXT NOT NULL,      -- 匹配模式
    target_type TEXT NOT NULL,  -- 目标插件类型
    priority INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 远程授权管理表
CREATE TABLE remote_licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_id INTEGER NOT NULL,
    license_server TEXT NOT NULL,
    license_key TEXT NOT NULL,
    license_type TEXT DEFAULT 'standard', -- trial/standard/enterprise
    issued_at TIMESTAMP,
    expires_at TIMESTAMP,
    max_instances INTEGER DEFAULT 1,
    current_instances INTEGER DEFAULT 0,
    last_validated_at TIMESTAMP,
    validation_result TEXT DEFAULT '{}',
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (plugin_id) REFERENCES plugins (id)
);

-- 4. 安全审计表
CREATE TABLE security_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,   -- signature_check/license_check/access_denied
    plugin_id INTEGER,
    event_level TEXT DEFAULT 'INFO',
    event_message TEXT NOT NULL,
    source_ip TEXT DEFAULT '',
    user_agent TEXT DEFAULT '',
    risk_score INTEGER DEFAULT 0,
    mitigation_action TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plugin_id) REFERENCES plugins (id)
);

-- 5. 插件文件完整性表
CREATE TABLE plugin_file_integrity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    original_hash TEXT NOT NULL,
    current_hash TEXT,
    last_verified_at TIMESTAMP,
    integrity_status TEXT DEFAULT 'unknown', -- valid/corrupted/missing
    auto_repair_attempted BOOLEAN DEFAULT 0,
    FOREIGN KEY (plugin_id) REFERENCES plugins (id)
);
```

### 索引优化策略

```sql
-- 性能优化索引
CREATE INDEX idx_plugins_type_status ON plugins(plugin_type, status);
CREATE INDEX idx_plugins_hash ON plugins(file_hash);
CREATE INDEX idx_plugins_signature ON plugins(signature_hash);
CREATE INDEX idx_licenses_active ON remote_licenses(is_active, expires_at);
CREATE INDEX idx_audit_type_time ON security_audit_log(event_type, created_at);
CREATE INDEX idx_integrity_status ON plugin_file_integrity(integrity_status);
```

## 🔍 插件自动发现与分类系统

### 1. 智能插件发现引擎

```python
class EnterprisePluginDiscoveryEngine:
    """企业级插件发现引擎"""
    
    def __init__(self, db_service, security_manager):
        self.db_service = db_service
        self.security_manager = security_manager
        self.classification_rules = self._load_classification_rules()
        
    async def discover_and_register_all_plugins(self):
        """发现并注册所有插件"""
        discovery_results = {
            'total_scanned': 0,
            'new_discovered': 0,
            'updated': 0,
            'security_issues': 0,
            'classification_results': {}
        }
        
        try:
            # 1. 扫描所有可能的插件位置
            scan_paths = [
                'plugins/',
                'plugins/examples/',
                'plugins/third_party/',
                'plugins/enterprise/'
            ]
            
            for scan_path in scan_paths:
                await self._scan_directory(scan_path, discovery_results)
                
            # 2. 更新扫描统计
            await self._update_discovery_statistics(discovery_results)
            
            return discovery_results
            
        except Exception as e:
            logger.error(f"插件发现失败: {e}")
            raise
    
    async def _scan_directory(self, directory: str, results: dict):
        """扫描指定目录"""
        try:
            for plugin_file in Path(directory).glob("**/*.py"):
                if self._should_skip_file(plugin_file):
                    continue
                    
                results['total_scanned'] += 1
                
                # 计算文件哈希
                file_hash = self._calculate_file_hash(plugin_file)
                
                # 检查是否已存在
                existing_plugin = await self.db_service.get_plugin_by_hash(file_hash)
                
                if existing_plugin:
                    # 检查文件是否被修改
                    if await self._verify_file_integrity(existing_plugin, plugin_file):
                        continue  # 文件未变更，跳过
                    else:
                        await self._handle_modified_plugin(existing_plugin, plugin_file, results)
                else:
                    # 新插件发现
                    await self._register_new_plugin(plugin_file, file_hash, results)
                    
        except Exception as e:
            logger.error(f"扫描目录失败 {directory}: {e}")
    
    async def _register_new_plugin(self, plugin_file: Path, file_hash: str, results: dict):
        """注册新发现的插件"""
        try:
            # 1. 分析插件文件
            plugin_analysis = await self._analyze_plugin_file(plugin_file)
            
            # 2. 自动分类
            plugin_type = await self._classify_plugin(plugin_analysis)
            results['classification_results'][plugin_type] = results['classification_results'].get(plugin_type, 0) + 1
            
            # 3. 安全验证
            security_result = await self._verify_plugin_security(plugin_file, plugin_analysis)
            
            if security_result['has_issues']:
                results['security_issues'] += 1
                await self._log_security_issue(plugin_file, security_result)
                return  # 跳过有安全问题的插件
            
            # 4. 创建插件记录
            plugin_record = {
                'name': plugin_analysis['name'],
                'display_name': plugin_analysis.get('display_name', plugin_analysis['name']),
                'version': plugin_analysis.get('version', '1.0.0'),
                'plugin_type': plugin_type,
                'description': plugin_analysis.get('description', ''),
                'author': plugin_analysis.get('author', ''),
                'file_path': str(plugin_file),
                'file_hash': file_hash,
                'signature_hash': security_result.get('signature_hash', ''),
                'signature_valid': security_result.get('signature_valid', False),
                'capabilities': json.dumps(plugin_analysis.get('capabilities', [])),
                'dependencies': json.dumps(plugin_analysis.get('dependencies', [])),
                'security_level': security_result.get('security_level', 1),
                'checksum': self._calculate_checksum(plugin_file),
                'scan_result': json.dumps(plugin_analysis),
                'last_scanned_at': datetime.now().isoformat()
            }
            
            # 5. 插入数据库
            plugin_id = await self.db_service.register_plugin(plugin_record)
            
            # 6. 记录文件完整性
            await self._record_file_integrity(plugin_id, plugin_file, file_hash)
            
            results['new_discovered'] += 1
            logger.info(f"新插件注册成功: {plugin_analysis['name']} (类型: {plugin_type})")
            
        except Exception as e:
            logger.error(f"注册插件失败 {plugin_file}: {e}")
```

### 2. 智能分类系统

```python
class PluginClassificationSystem:
    """插件智能分类系统"""
    
    CLASSIFICATION_RULES = [
        # 基于文件名模式
        {'pattern': r'.*indicator.*', 'type': 'indicator', 'priority': 90},
        {'pattern': r'.*strategy.*', 'type': 'strategy', 'priority': 90},
        {'pattern': r'.*data.*source.*', 'type': 'data_source', 'priority': 85},
        {'pattern': r'.*analysis.*', 'type': 'analysis', 'priority': 80},
        
        # 基于类继承模式
        {'pattern': r'.*Indicator\b', 'type': 'indicator', 'priority': 95},
        {'pattern': r'.*Strategy\b', 'type': 'strategy', 'priority': 95},
        {'pattern': r'.*DataSource\b', 'type': 'data_source', 'priority': 95},
        
        # 基于功能特征
        {'pattern': r'.*chart.*tool.*', 'type': 'chart_tool', 'priority': 85},
        {'pattern': r'.*notification.*', 'type': 'notification', 'priority': 85},
        {'pattern': r'.*export.*', 'type': 'export', 'priority': 80},
    ]
    
    async def classify_plugin(self, plugin_analysis: dict) -> str:
        """智能分类插件"""
        try:
            classification_scores = {}
            
            # 1. 基于文件名分析
            file_scores = self._analyze_filename(plugin_analysis.get('file_name', ''))
            self._merge_scores(classification_scores, file_scores)
            
            # 2. 基于类名分析
            class_scores = self._analyze_class_names(plugin_analysis.get('classes', []))
            self._merge_scores(classification_scores, class_scores)
            
            # 3. 基于方法名分析
            method_scores = self._analyze_methods(plugin_analysis.get('methods', []))
            self._merge_scores(classification_scores, method_scores)
            
            # 4. 基于导入模块分析
            import_scores = self._analyze_imports(plugin_analysis.get('imports', []))
            self._merge_scores(classification_scores, import_scores)
            
            # 5. 基于注释和文档分析
            doc_scores = self._analyze_documentation(plugin_analysis.get('docstring', ''))
            self._merge_scores(classification_scores, doc_scores)
            
            # 6. 选择最高分类型
            if classification_scores:
                best_type = max(classification_scores.keys(), 
                              key=lambda k: classification_scores[k])
                
                # 置信度检查
                confidence = classification_scores[best_type] / sum(classification_scores.values())
                
                if confidence >= 0.6:
                    return best_type
                else:
                    return 'analysis'  # 默认分类
            
            return 'analysis'  # 无法分类时的默认值
            
        except Exception as e:
            logger.error(f"插件分类失败: {e}")
            return 'analysis'
    
    def _analyze_filename(self, filename: str) -> dict:
        """基于文件名分析"""
        scores = {}
        filename_lower = filename.lower()
        
        for rule in self.CLASSIFICATION_RULES:
            if 'filename' in rule['pattern']:
                if re.search(rule['pattern'], filename_lower):
                    scores[rule['type']] = scores.get(rule['type'], 0) + rule['priority']
        
        return scores
    
    def _analyze_class_names(self, class_names: list) -> dict:
        """基于类名分析"""
        scores = {}
        
        for class_name in class_names:
            # 指标类识别
            if re.search(r'(Indicator|MA|RSI|MACD|KDJ|BOLL)', class_name):
                scores['indicator'] = scores.get('indicator', 0) + 100
            
            # 策略类识别
            elif re.search(r'(Strategy|Signal|Trading)', class_name):
                scores['strategy'] = scores.get('strategy', 0) + 100
            
            # 数据源类识别
            elif re.search(r'(DataSource|Provider|Feed)', class_name):
                scores['data_source'] = scores.get('data_source', 0) + 100
            
            # 分析工具类识别
            elif re.search(r'(Analyzer|Analysis|Calculator)', class_name):
                scores['analysis'] = scores.get('analysis', 0) + 80
        
        return scores
```

## 🔐 安全与授权系统设计

### 1. 数字签名验证系统

```python
class PluginSecurityManager:
    """插件安全管理器"""
    
    def __init__(self, certificate_store):
        self.certificate_store = certificate_store
        self.trusted_publishers = self._load_trusted_publishers()
        
    async def verify_plugin_security(self, plugin_file: Path, analysis: dict) -> dict:
        """综合安全验证"""
        security_result = {
            'signature_valid': False,
            'signature_hash': '',
            'trust_level': 0,
            'security_level': 1,
            'has_issues': False,
            'issues': [],
            'recommendations': []
        }
        
        try:
            # 1. 数字签名验证
            signature_result = await self._verify_digital_signature(plugin_file)
            security_result.update(signature_result)
            
            # 2. 代码安全扫描
            code_scan_result = await self._scan_code_security(plugin_file, analysis)
            security_result['has_issues'] = security_result['has_issues'] or code_scan_result['has_issues']
            security_result['issues'].extend(code_scan_result['issues'])
            
            # 3. 权限需求分析
            permission_analysis = await self._analyze_permissions(analysis)
            security_result['required_permissions'] = permission_analysis['permissions']
            security_result['risk_score'] = permission_analysis['risk_score']
            
            # 4. 计算综合安全等级
            security_result['security_level'] = self._calculate_security_level(security_result)
            
            return security_result
            
        except Exception as e:
            logger.error(f"安全验证失败: {e}")
            security_result['has_issues'] = True
            security_result['issues'].append(f"安全验证异常: {e}")
            return security_result
    
    async def _verify_digital_signature(self, plugin_file: Path) -> dict:
        """验证数字签名"""
        result = {
            'signature_valid': False,
            'signature_hash': '',
            'trust_level': 0,
            'signer_info': {}
        }
        
        try:
            # 检查是否有签名文件
            signature_file = plugin_file.with_suffix('.py.sig')
            
            if signature_file.exists():
                # 验证签名
                signature_data = signature_file.read_bytes()
                file_data = plugin_file.read_bytes()
                
                # 使用公钥验证签名
                is_valid, signer_info = await self._validate_signature(
                    file_data, signature_data
                )
                
                result['signature_valid'] = is_valid
                result['signature_hash'] = hashlib.sha256(signature_data).hexdigest()
                result['signer_info'] = signer_info
                
                # 检查签名者信任级别
                if is_valid and signer_info.get('publisher') in self.trusted_publishers:
                    result['trust_level'] = self.trusted_publishers[signer_info['publisher']]['trust_level']
            
            return result
            
        except Exception as e:
            logger.error(f"数字签名验证失败: {e}")
            return result
    
    async def _scan_code_security(self, plugin_file: Path, analysis: dict) -> dict:
        """代码安全扫描"""
        scan_result = {
            'has_issues': False,
            'issues': [],
            'risk_patterns': []
        }
        
        # 危险模式检测
        DANGEROUS_PATTERNS = [
            (r'exec\s*\(', 'HIGH', '动态代码执行'),
            (r'eval\s*\(', 'HIGH', '表达式求值'),
            (r'__import__\s*\(', 'MEDIUM', '动态导入'),
            (r'subprocess\.(call|run|Popen)', 'HIGH', '系统命令执行'),
            (r'os\.system\s*\(', 'HIGH', '系统命令执行'),
            (r'open\s*\([^)]*[\'"]w', 'MEDIUM', '文件写入操作'),
            (r'socket\.socket\s*\(', 'MEDIUM', '网络连接'),
            (r'urllib\.request', 'MEDIUM', '网络请求'),
            (r'pickle\.loads?\s*\(', 'HIGH', '反序列化操作'),
        ]
        
        try:
            plugin_code = plugin_file.read_text(encoding='utf-8')
            
            for pattern, risk_level, description in DANGEROUS_PATTERNS:
                matches = re.findall(pattern, plugin_code, re.IGNORECASE)
                
                if matches:
                    issue = {
                        'type': 'dangerous_pattern',
                        'risk_level': risk_level,
                        'description': description,
                        'pattern': pattern,
                        'matches': len(matches)
                    }
                    
                    scan_result['risk_patterns'].append(issue)
                    
                    if risk_level == 'HIGH':
                        scan_result['has_issues'] = True
                        scan_result['issues'].append(f"高风险代码模式: {description}")
            
            return scan_result
            
        except Exception as e:
            logger.error(f"代码安全扫描失败: {e}")
            scan_result['has_issues'] = True
            scan_result['issues'].append(f"代码扫描异常: {e}")
            return scan_result
```

### 2. 远程授权管理系统

```python
class RemoteLicenseManager:
    """远程授权管理器"""
    
    def __init__(self, license_server_config):
        self.license_servers = license_server_config
        self.local_cache = {}
        self.session = aiohttp.ClientSession()
        
    async def validate_plugin_license(self, plugin_id: int, plugin_name: str) -> dict:
        """验证插件授权"""
        validation_result = {
            'is_valid': False,
            'license_type': 'none',
            'expires_at': None,
            'remaining_days': 0,
            'features': [],
            'restrictions': {}
        }
        
        try:
            # 1. 检查本地缓存
            cached_license = await self._get_cached_license(plugin_id)
            
            if cached_license and not self._is_cache_expired(cached_license):
                return cached_license['validation_result']
            
            # 2. 远程验证
            for server_config in self.license_servers:
                try:
                    remote_result = await self._validate_with_server(
                        server_config, plugin_id, plugin_name
                    )
                    
                    if remote_result['is_valid']:
                        validation_result = remote_result
                        break
                        
                except Exception as e:
                    logger.warning(f"授权服务器 {server_config['url']} 验证失败: {e}")
                    continue
            
            # 3. 更新本地缓存
            await self._update_license_cache(plugin_id, validation_result)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"授权验证失败: {e}")
            return validation_result
    
    async def _validate_with_server(self, server_config: dict, plugin_id: int, plugin_name: str) -> dict:
        """与授权服务器验证"""
        try:
            # 构建验证请求
            validation_request = {
                'plugin_id': plugin_id,
                'plugin_name': plugin_name,
                'client_id': self._get_client_id(),
                'machine_fingerprint': self._get_machine_fingerprint(),
                'version': self._get_app_version(),
                'timestamp': int(time.time())
            }
            
            # 添加数字签名
            validation_request['signature'] = self._sign_request(validation_request, server_config['private_key'])
            
            # 发送验证请求
            async with self.session.post(
                f"{server_config['url']}/api/v1/validate_license",
                json=validation_request,
                headers={'Authorization': f"Bearer {server_config['api_key']}"},
                ssl=True,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # 验证服务器响应签名
                    if self._verify_server_response(result, server_config['public_key']):
                        return result['validation_result']
                    else:
                        raise SecurityError("服务器响应签名验证失败")
                else:
                    raise ConnectionError(f"服务器返回错误: {response.status}")
                    
        except Exception as e:
            logger.error(f"远程授权验证失败: {e}")
            raise
    
    def _get_machine_fingerprint(self) -> str:
        """获取机器指纹"""
        import platform
        import uuid
        
        # 收集硬件信息
        hardware_info = [
            platform.machine(),
            platform.processor(),
            str(uuid.getnode()),  # MAC地址
            platform.system(),
            platform.release()
        ]
        
        # 生成指纹
        fingerprint_data = '|'.join(hardware_info)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()
```

## 🌐 远程管理端设计

### 1. 授权服务器架构

```python
# 授权服务器 (Flask/FastAPI)
class LicenseAuthorizationServer:
    """授权服务器"""
    
    def __init__(self):
        self.app = FastAPI(title="HIkyuu Plugin License Server")
        self.db = AsyncSQLAlchemy()
        self.security = SecurityManager()
        self._setup_routes()
    
    def _setup_routes(self):
        """设置API路由"""
        
        @self.app.post("/api/v1/validate_license")
        async def validate_license(request: LicenseValidationRequest):
            """验证插件授权"""
            try:
                # 1. 验证请求签名
                if not self.security.verify_request_signature(request):
                    raise HTTPException(401, "请求签名验证失败")
                
                # 2. 查询授权记录
                license_record = await self.db.get_license_record(
                    request.plugin_name, request.client_id
                )
                
                if not license_record:
                    return LicenseValidationResponse(
                        is_valid=False,
                        reason="未找到有效授权"
                    )
                
                # 3. 验证授权状态
                validation_result = await self._validate_license_record(
                    license_record, request
                )
                
                # 4. 记录验证日志
                await self._log_validation_attempt(request, validation_result)
                
                # 5. 签名响应
                response = LicenseValidationResponse(**validation_result)
                response.signature = self.security.sign_response(response)
                
                return response
                
            except Exception as e:
                logger.error(f"授权验证异常: {e}")
                raise HTTPException(500, "内部服务器错误")
        
        @self.app.post("/api/v1/register_plugin")
        async def register_plugin(request: PluginRegistrationRequest):
            """注册新插件"""
            # 插件注册逻辑
            pass
        
        @self.app.get("/api/v1/plugin_market")
        async def get_plugin_market():
            """获取插件市场列表"""
            # 插件市场逻辑
            pass
        
        @self.app.post("/api/v1/download_plugin")
        async def download_plugin(request: PluginDownloadRequest):
            """下载插件"""
            # 插件下载逻辑
            pass
```

### 2. 管理控制台

```python
class PluginManagementConsole:
    """插件管理控制台 (Web界面)"""
    
    def __init__(self):
        self.app = FastAPI()
        self.auth = AuthenticationManager()
        self._setup_admin_routes()
    
    def _setup_admin_routes(self):
        """设置管理员路由"""
        
        @self.app.get("/admin/dashboard")
        async def admin_dashboard():
            """管理员仪表板"""
            return {
                'total_clients': await self._get_total_clients(),
                'active_licenses': await self._get_active_licenses(),
                'plugin_downloads': await self._get_download_stats(),
                'security_alerts': await self._get_security_alerts()
            }
        
        @self.app.get("/admin/clients")
        async def list_clients():
            """客户端列表"""
            return await self._get_client_list()
        
        @self.app.post("/admin/licenses/issue")
        async def issue_license(request: LicenseIssueRequest):
            """颁发授权"""
            return await self._issue_new_license(request)
        
        @self.app.delete("/admin/licenses/{license_id}/revoke")
        async def revoke_license(license_id: int):
            """撤销授权"""
            return await self._revoke_license(license_id)
```

## 📊 缓存策略设计

### 三级缓存架构

```python
class PluginCacheManager:
    """插件缓存管理器"""
    
    def __init__(self, db_service, remote_service):
        self.db_service = db_service
        self.remote_service = remote_service
        
        # L1: 内存缓存 (最快访问)
        self.memory_cache = {}
        self.memory_cache_ttl = {}
        
        # L2: 数据库缓存 (持久化)
        self.db_cache_ttl = 3600  # 1小时
        
        # L3: 远程同步 (权威源)
        self.remote_sync_interval = 86400  # 24小时
    
    async def get_plugin_info(self, plugin_name: str, force_refresh: bool = False):
        """获取插件信息 (三级缓存策略)"""
        
        # L1: 检查内存缓存
        if not force_refresh and self._is_memory_cache_valid(plugin_name):
            logger.debug(f"从内存缓存获取插件信息: {plugin_name}")
            return self.memory_cache[plugin_name]
        
        # L2: 检查数据库缓存
        db_cached = await self.db_service.get_cached_plugin_info(plugin_name)
        if not force_refresh and db_cached and self._is_db_cache_valid(db_cached):
            logger.debug(f"从数据库缓存获取插件信息: {plugin_name}")
            # 更新L1缓存
            self._update_memory_cache(plugin_name, db_cached['data'])
            return db_cached['data']
        
        # L3: 远程同步
        try:
            remote_data = await self.remote_service.get_plugin_info(plugin_name)
            
            # 更新所有缓存层
            await self._update_all_caches(plugin_name, remote_data)
            
            logger.info(f"从远程同步获取插件信息: {plugin_name}")
            return remote_data
            
        except Exception as e:
            logger.warning(f"远程同步失败，使用本地缓存: {e}")
            
            # 降级到本地数据
            if db_cached:
                self._update_memory_cache(plugin_name, db_cached['data'])
                return db_cached['data']
            
            raise CacheError(f"无法获取插件信息: {plugin_name}")
    
    async def _update_all_caches(self, plugin_name: str, data: dict):
        """更新所有缓存层"""
        try:
            # 更新L1 (内存)
            self._update_memory_cache(plugin_name, data)
            
            # 更新L2 (数据库)
            await self.db_service.update_plugin_cache(plugin_name, data)
            
            logger.debug(f"缓存更新完成: {plugin_name}")
            
        except Exception as e:
            logger.error(f"缓存更新失败: {e}")
```

## 🔄 实施计划

### 阶段一：核心架构 (2周)
1. 扩展数据库表结构
2. 实现插件发现引擎
3. 基础安全验证系统
4. 自动分类算法

### 阶段二：安全增强 (2周)
1. 数字签名验证系统
2. 代码安全扫描
3. 文件完整性监控
4. 访问权限控制

### 阶段三：远程管理 (3周)
1. 授权服务器开发
2. 远程API接口
3. 管理控制台
4. 客户端集成

### 阶段四：优化完善 (1周)
1. 缓存性能优化
2. 监控和告警
3. 文档和测试
4. 部署和上线

## 📈 技术指标

### 性能指标
- 插件发现速度: < 5秒 (100个插件)
- 缓存命中率: > 90%
- 授权验证响应: < 500ms
- 数据库查询: < 100ms

### 安全指标
- 签名验证率: 100%
- 代码扫描覆盖: > 95%
- 授权准确率: > 99.9%
- 安全事件响应: < 1分钟

### 可用性指标
- 系统可用性: > 99.5%
- 远程服务可用性: > 99%
- 缓存一致性: > 99.9%
- 错误恢复时间: < 30秒

这个设计方案提供了企业级的插件管理能力，确保了安全性、可靠性和可扩展性。 