# FactorWeave-Quant远程插件加载系统设计

> **企业级远程插件管理**: 安全 + 便利 + 扩展性
> **兼容现有架构**: 100%兼容现有插件接口和装饰器
> **商业化支持**: 支持付费插件、企业私有仓库、授权管理

## 🎯 设计目标

### 核心需求
```python
安全性: 数字签名 + 完整性验证 + 沙箱执行
便利性: 一键安装 + 自动更新 + 离线支持  
扩展性: 多仓库源 + 第三方集成 + 企业级管理
兼容性: 现有@plugin_metadata装饰器100%兼容
商业化: 付费插件 + 授权管理 + 使用统计
```

### 业务场景
```python
1. 公共插件市场: 免费开源插件的远程分发
2. 商业插件生态: 付费插件的授权和交付
3. 企业内部管理: 私有插件仓库的集中管理
4. 第三方集成: 合作伙伴插件的远程发布
5. 自动化运维: 插件的批量部署和更新
```

## 🏗️ 系统架构设计

### 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                FactorWeave-Quant远程插件加载系统架构                    │
├─────────────────────────────────────────────────────────────┤
│  UI交互层        │    业务逻辑层      │    数据传输层       │
│  ┌─────────────┐ │  ┌───────────────┐ │  ┌───────────────┐  │
│  │插件市场界面  │◄┼──│远程插件管理器  │◄┼──│安全传输协议   │  │
│  │安装进度显示  │ │  │版本控制器     │ │  │数字签名验证   │  │
│  │权限确认对话  │ │  │授权管理器     │ │  │完整性校验     │  │
│  └─────────────┘ │  └───────────────┘ │  └───────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  缓存存储层      │    安全执行层      │    兼容适配层       │
│  ┌─────────────┐ │  ┌───────────────┐ │  ┌───────────────┐  │
│  │本地插件缓存  │ │  │沙箱执行环境   │ │  │现有接口桥接   │  │
│  │版本依赖管理  │◄┼──│资源限制控制   │◄┼──│装饰器兼容     │  │
│  │离线模式支持  │ │  │权限细粒控制   │ │  │PluginManager │  │
│  └─────────────┘ │  └───────────────┘ │  └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件设计

#### 1. 远程插件仓库服务 (Remote Plugin Registry)

```python
class RemotePluginRegistry:
    """远程插件仓库客户端"""
    
    def __init__(self, config_manager, security_manager):
        self.config = config_manager
        self.security = security_manager
        self.repositories = self._load_repository_configs()
        self.auth_manager = RemoteAuthManager()
        
    async def search_plugins(self, query: str, filters: dict = None) -> List[RemotePluginInfo]:
        """搜索远程插件"""
        search_results = []
        
        for repo in self.repositories:
            try:
                # 构建搜索请求
                search_request = {
                    'query': query,
                    'filters': filters or {},
                    'client_version': '2.0.1',
                    'supported_types': [t.value for t in PluginType],
                    'auth_token': await self.auth_manager.get_token(repo['name'])
                }
                
                # 发送HTTPS请求
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'Authorization': f"Bearer {search_request['auth_token']}",
                        'Content-Type': 'application/json',
                        'User-Agent': 'FactorWeave-Quant-Plugin-Client/2.0.1'
                    }
                    
                    async with session.post(
                        f"{repo['url']}/api/v1/plugins/search",
                        json=search_request,
                        headers=headers,
                        ssl=True  # 强制HTTPS
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            plugins = [RemotePluginInfo.from_dict(p) for p in data['plugins']]
                            search_results.extend(plugins)
                        else:
                            logger.warning(f"搜索失败 {repo['name']}: {response.status}")
                            
            except Exception as e:
                logger.error(f"仓库搜索异常 {repo['name']}: {e}")
                continue
        
        return search_results
    
    async def get_plugin_details(self, plugin_id: str, repository: str) -> RemotePluginDetails:
        """获取插件详细信息"""
        repo_config = self._get_repository_config(repository)
        if not repo_config:
            raise RepositoryNotFoundError(f"仓库未配置: {repository}")
        
        try:
            auth_token = await self.auth_manager.get_token(repository)
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f"Bearer {auth_token}",
                    'User-Agent': 'FactorWeave-Quant-Plugin-Client/2.0.1'
                }
                
                async with session.get(
                    f"{repo_config['url']}/api/v1/plugins/{plugin_id}",
                    headers=headers,
                    ssl=True
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return RemotePluginDetails.from_dict(data['plugin'])
                    elif response.status == 404:
                        raise PluginNotFoundError(f"插件不存在: {plugin_id}")
                    elif response.status == 403:
                        raise AuthorizationError(f"无权限访问插件: {plugin_id}")
                    else:
                        raise RemoteRegistryError(f"获取插件详情失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"获取插件详情异常 {plugin_id}: {e}")
            raise

@dataclass
class RemotePluginInfo:
    """远程插件信息"""
    plugin_id: str
    name: str
    version: str
    plugin_type: PluginType
    category: PluginCategory
    description: str
    author: str
    
    # 远程特有字段
    repository: str
    download_url: str
    signature_url: str
    file_size: int
    file_hash: str
    
    # 商业化字段
    is_paid: bool = False
    price: float = 0.0
    license_type: str = "MIT"
    required_permissions: List[str] = field(default_factory=list)
    
    # 统计字段
    download_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RemotePluginInfo':
        """从字典创建实例"""
        return cls(
            plugin_id=data['plugin_id'],
            name=data['name'],
            version=data['version'],
            plugin_type=PluginType(data['plugin_type']),
            category=PluginCategory(data['category']),
            description=data['description'],
            author=data['author'],
            repository=data['repository'],
            download_url=data['download_url'],
            signature_url=data['signature_url'],
            file_size=data['file_size'],
            file_hash=data['file_hash'],
            is_paid=data.get('is_paid', False),
            price=data.get('price', 0.0),
            license_type=data.get('license_type', 'MIT'),
            required_permissions=data.get('required_permissions', []),
            download_count=data.get('download_count', 0),
            rating=data.get('rating', 0.0),
            rating_count=data.get('rating_count', 0)
        )
```

#### 2. 安全下载和验证模块

```python
class SecurePluginDownloader:
    """安全插件下载器"""
    
    def __init__(self, security_manager, cache_manager):
        self.security = security_manager
        self.cache = cache_manager
        self.download_progress = {}
        
    async def download_and_verify_plugin(
        self, 
        plugin_info: RemotePluginInfo,
        progress_callback: Optional[Callable] = None
    ) -> PluginPackage:
        """安全下载和验证插件"""
        
        download_id = f"{plugin_info.repository}_{plugin_info.plugin_id}_{plugin_info.version}"
        
        try:
            # 1. 检查本地缓存
            cached_plugin = await self.cache.get_cached_plugin(
                plugin_info.plugin_id, 
                plugin_info.version,
                plugin_info.file_hash
            )
            
            if cached_plugin and await self._verify_cached_plugin(cached_plugin):
                logger.info(f"使用缓存插件: {plugin_info.name}")
                return cached_plugin
            
            # 2. 创建临时下载目录
            download_dir = Path(tempfile.mkdtemp(prefix=f"FactorWeave-Quant_plugin_{download_id}_"))
            
            try:
                # 3. 下载插件文件
                plugin_file_path = await self._download_plugin_file(
                    plugin_info, download_dir, progress_callback
                )
                
                # 4. 下载数字签名
                signature_file_path = await self._download_signature_file(
                    plugin_info, download_dir
                )
                
                # 5. 验证数字签名
                signature_valid = await self.security.verify_plugin_signature(
                    plugin_file_path, signature_file_path, plugin_info.repository
                )
                
                if not signature_valid:
                    raise SecurityError(f"插件数字签名验证失败: {plugin_info.name}")
                
                # 6. 验证文件完整性
                file_hash = await self._calculate_file_hash(plugin_file_path)
                if file_hash != plugin_info.file_hash:
                    raise IntegrityError(f"插件文件完整性验证失败: {plugin_info.name}")
                
                # 7. 创建插件包
                plugin_package = await self._create_plugin_package(
                    plugin_info, plugin_file_path, download_dir
                )
                
                # 8. 缓存已验证的插件
                await self.cache.cache_plugin(plugin_package)
                
                logger.info(f"插件下载验证成功: {plugin_info.name}")
                return plugin_package
                
            finally:
                # 清理临时目录
                shutil.rmtree(download_dir, ignore_errors=True)
                
        except Exception as e:
            logger.error(f"插件下载失败 {plugin_info.name}: {e}")
            raise
        finally:
            # 清理进度记录
            self.download_progress.pop(download_id, None)
    
    async def _download_plugin_file(
        self,
        plugin_info: RemotePluginInfo, 
        download_dir: Path,
        progress_callback: Optional[Callable]
    ) -> Path:
        """下载插件文件"""
        
        file_path = download_dir / f"{plugin_info.plugin_id}.hpk"
        download_id = f"{plugin_info.repository}_{plugin_info.plugin_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(plugin_info.download_url) as response:
                    
                    if response.status != 200:
                        raise DownloadError(f"下载失败: HTTP {response.status}")
                    
                    # 验证内容长度
                    content_length = int(response.headers.get('Content-Length', 0))
                    if content_length != plugin_info.file_size:
                        raise DownloadError(f"文件大小不匹配: 期望{plugin_info.file_size}, 实际{content_length}")
                    
                    # 流式下载并显示进度
                    downloaded = 0
                    chunk_size = 8192
                    
                    with open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # 更新进度
                            progress = (downloaded / content_length) * 100 if content_length > 0 else 0
                            self.download_progress[download_id] = {
                                'downloaded': downloaded,
                                'total': content_length,
                                'progress': progress
                            }
                            
                            # 回调进度更新
                            if progress_callback:
                                await progress_callback(progress, downloaded, content_length)
            
            return file_path
            
        except Exception as e:
            logger.error(f"下载插件文件失败: {e}")
            raise
    
    async def _create_plugin_package(
        self,
        plugin_info: RemotePluginInfo,
        plugin_file_path: Path,
        extract_dir: Path
    ) -> PluginPackage:
        """创建插件包对象"""
        
        # 解压插件包 (假设是.hpk格式的zip文件)
        with zipfile.ZipFile(plugin_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # 查找主插件文件
        plugin_main_file = None
        manifest_file = extract_dir / "manifest.json"
        
        if manifest_file.exists():
            # 从manifest.json读取主文件信息
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                plugin_main_file = extract_dir / manifest['main_file']
        else:
            # 搜索.py文件
            py_files = list(extract_dir.glob("*.py"))
            if py_files:
                plugin_main_file = py_files[0]
        
        if not plugin_main_file or not plugin_main_file.exists():
            raise InvalidPluginError(f"未找到有效的插件主文件: {plugin_info.name}")
        
        return PluginPackage(
            plugin_info=plugin_info,
            main_file_path=plugin_main_file,
            extract_directory=extract_dir,
            manifest=manifest if 'manifest' in locals() else None,
            verified=True,
            cached=False
        )

@dataclass
class PluginPackage:
    """插件包"""
    plugin_info: RemotePluginInfo
    main_file_path: Path
    extract_directory: Path
    manifest: Optional[dict] = None
    verified: bool = False
    cached: bool = False
    
    def get_plugin_metadata(self) -> dict:
        """获取插件元数据"""
        if self.manifest:
            return self.manifest.get('metadata', {})
        
        # 从插件文件解析@plugin_metadata装饰器
        return self._extract_metadata_from_file()
    
    def _extract_metadata_from_file(self) -> dict:
        """从文件提取元数据 - 兼容现有装饰器"""
        try:
            with open(self.main_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST查找@plugin_metadata装饰器
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for decorator in node.decorator_list:
                        if (isinstance(decorator, ast.Call) and 
                            hasattr(decorator.func, 'id') and 
                            decorator.func.id == 'plugin_metadata'):
                            
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
                                    pass
                            
                            return metadata
            
            return {}
            
        except Exception as e:
            logger.warning(f"提取插件元数据失败: {e}")
            return {}
```

#### 3. 授权和许可管理系统

```python
class RemoteAuthManager:
    """远程授权管理器"""
    
    def __init__(self, config_manager, db_service):
        self.config = config_manager
        self.db = db_service
        self.token_cache = {}
        self.license_manager = PluginLicenseManager(db_service)
        
    async def authenticate_repository(self, repository: str, credentials: dict) -> str:
        """仓库认证"""
        try:
            repo_config = self._get_repository_config(repository)
            
            auth_request = {
                'client_id': credentials.get('client_id'),
                'client_secret': credentials.get('client_secret'),
                'grant_type': 'client_credentials',
                'scope': 'plugin:read plugin:download'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{repo_config['auth_url']}/oauth/token",
                    data=auth_request,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        token = data['access_token']
                        expires_in = data.get('expires_in', 3600)
                        
                        # 缓存token
                        self.token_cache[repository] = {
                            'token': token,
                            'expires_at': datetime.now() + timedelta(seconds=expires_in)
                        }
                        
                        # 保存到数据库
                        await self.db.save_auth_token(repository, token, expires_in)
                        
                        logger.info(f"仓库认证成功: {repository}")
                        return token
                    else:
                        raise AuthenticationError(f"仓库认证失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"仓库认证异常 {repository}: {e}")
            raise
    
    async def get_token(self, repository: str) -> str:
        """获取有效token"""
        # 检查缓存
        cached_token = self.token_cache.get(repository)
        if cached_token and cached_token['expires_at'] > datetime.now():
            return cached_token['token']
        
        # 从数据库获取
        db_token = await self.db.get_auth_token(repository)
        if db_token and db_token['expires_at'] > datetime.now():
            self.token_cache[repository] = db_token
            return db_token['token']
        
        # 需要重新认证
        credentials = await self._get_repository_credentials(repository)
        if credentials:
            return await self.authenticate_repository(repository, credentials)
        else:
            raise AuthenticationError(f"仓库无认证凭据: {repository}")
    
    async def check_plugin_license(self, plugin_info: RemotePluginInfo) -> LicenseCheckResult:
        """检查插件许可证"""
        if not plugin_info.is_paid:
            return LicenseCheckResult(
                valid=True,
                license_type='free',
                message='免费插件'
            )
        
        # 检查已购买许可证
        license_record = await self.license_manager.get_plugin_license(
            plugin_info.plugin_id, 
            plugin_info.version
        )
        
        if license_record:
            # 验证许可证有效性
            if await self._verify_license_validity(license_record, plugin_info):
                return LicenseCheckResult(
                    valid=True,
                    license_type='purchased',
                    license_info=license_record,
                    message='许可证有效'
                )
            else:
                return LicenseCheckResult(
                    valid=False,
                    license_type='expired',
                    license_info=license_record,
                    message='许可证已过期'
                )
        else:
            return LicenseCheckResult(
                valid=False,
                license_type='required',
                message=f'需要购买许可证，价格: ${plugin_info.price}'
            )
    
    async def purchase_plugin_license(
        self, 
        plugin_info: RemotePluginInfo,
        payment_info: dict
    ) -> PurchaseResult:
        """购买插件许可证"""
        try:
            repo_config = self._get_repository_config(plugin_info.repository)
            auth_token = await self.get_token(plugin_info.repository)
            
            purchase_request = {
                'plugin_id': plugin_info.plugin_id,
                'version': plugin_info.version,
                'payment_method': payment_info['method'],
                'client_id': self.config.get('client_id'),
                'client_info': {
                    'platform': 'FactorWeave-Quant',
                    'version': '2.0.1',
                    'machine_id': self._get_machine_id()
                }
            }
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f"Bearer {auth_token}",
                    'Content-Type': 'application/json'
                }
                
                async with session.post(
                    f"{repo_config['url']}/api/v1/plugins/{plugin_info.plugin_id}/purchase",
                    json=purchase_request,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # 保存许可证
                        license_info = LicenseInfo(
                            plugin_id=plugin_info.plugin_id,
                            version=plugin_info.version,
                            license_key=data['license_key'],
                            issued_at=datetime.fromisoformat(data['issued_at']),
                            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
                            license_type=data['license_type'],
                            repository=plugin_info.repository
                        )
                        
                        await self.license_manager.save_license(license_info)
                        
                        return PurchaseResult(
                            success=True,
                            license_info=license_info,
                            message='购买成功'
                        )
                    else:
                        return PurchaseResult(
                            success=False,
                            message=f'购买失败: {response.status}'
                        )
                        
        except Exception as e:
            logger.error(f"购买插件许可证失败: {e}")
            return PurchaseResult(
                success=False,
                message=f'购买异常: {e}'
            )

@dataclass
class LicenseCheckResult:
    """许可证检查结果"""
    valid: bool
    license_type: str  # free/purchased/expired/required
    license_info: Optional['LicenseInfo'] = None
    message: str = ""

@dataclass  
class PurchaseResult:
    """购买结果"""
    success: bool
    license_info: Optional['LicenseInfo'] = None
    message: str = ""

@dataclass
class LicenseInfo:
    """许可证信息"""
    plugin_id: str
    version: str
    license_key: str
    issued_at: datetime
    expires_at: Optional[datetime]
    license_type: str  # perpetual/subscription/trial
    repository: str
    machine_bindings: List[str] = field(default_factory=list)
```

#### 4. 远程插件管理器集成

```python
class RemotePluginManager:
    """远程插件管理器 - 集成到现有系统"""
    
    def __init__(self, existing_plugin_manager, db_service):
        self.existing_manager = existing_plugin_manager
        self.db = db_service
        self.registry = RemotePluginRegistry(
            existing_plugin_manager.config_manager,
            SecurityManager(db_service)
        )
        self.downloader = SecurePluginDownloader(
            SecurityManager(db_service),
            PluginCacheManager(db_service)
        )
        self.auth_manager = RemoteAuthManager(
            existing_plugin_manager.config_manager,
            db_service
        )
        
    async def install_remote_plugin(
        self, 
        plugin_info: RemotePluginInfo,
        progress_callback: Optional[Callable] = None
    ) -> InstallResult:
        """安装远程插件"""
        try:
            # 1. 检查许可证
            license_check = await self.auth_manager.check_plugin_license(plugin_info)
            if not license_check.valid:
                if license_check.license_type == 'required':
                    return InstallResult(
                        success=False,
                        error_type='license_required',
                        message=license_check.message,
                        plugin_info=plugin_info
                    )
                else:
                    return InstallResult(
                        success=False, 
                        error_type='license_invalid',
                        message=license_check.message
                    )
            
            # 2. 检查依赖和兼容性
            compatibility_check = await self._check_plugin_compatibility(plugin_info)
            if not compatibility_check.compatible:
                return InstallResult(
                    success=False,
                    error_type='compatibility',
                    message=compatibility_check.reason
                )
            
            # 3. 下载和验证插件
            plugin_package = await self.downloader.download_and_verify_plugin(
                plugin_info, progress_callback
            )
            
            # 4. 检查权限需求
            if plugin_info.required_permissions:
                permission_granted = await self._request_user_permissions(
                    plugin_info.required_permissions
                )
                if not permission_granted:
                    return InstallResult(
                        success=False,
                        error_type='permission_denied',
                        message='用户拒绝授权所需权限'
                    )
            
            # 5. 安装插件到本地
            local_install_result = await self._install_plugin_locally(plugin_package)
            if not local_install_result.success:
                return local_install_result
            
            # 6. 注册到现有插件管理器
            success = self.existing_manager.load_plugin(
                plugin_package.plugin_info.name,
                plugin_package.main_file_path
            )
            
            if success:
                # 7. 更新数据库记录
                await self.db.record_plugin_installation(
                    plugin_info,
                    local_install_result.install_path,
                    'remote_install'
                )
                
                # 8. 记录使用统计
                await self._record_usage_statistics(plugin_info, 'install')
                
                return InstallResult(
                    success=True,
                    message=f'插件安装成功: {plugin_info.name}',
                    install_path=local_install_result.install_path
                )
            else:
                return InstallResult(
                    success=False,
                    error_type='load_failed',
                    message='插件加载失败'
                )
                
        except Exception as e:
            logger.error(f"远程插件安装失败 {plugin_info.name}: {e}")
            return InstallResult(
                success=False,
                error_type='install_error',
                message=str(e)
            )
    
    async def check_plugin_updates(self) -> List[PluginUpdateInfo]:
        """检查插件更新"""
        update_list = []
        
        try:
            # 获取所有已安装的远程插件
            installed_remote_plugins = await self.db.get_installed_remote_plugins()
            
            for plugin_record in installed_remote_plugins:
                try:
                    # 查询远程最新版本
                    latest_info = await self.registry.get_plugin_details(
                        plugin_record['plugin_id'],
                        plugin_record['repository']
                    )
                    
                    # 比较版本
                    if self._is_newer_version(latest_info.version, plugin_record['version']):
                        update_info = PluginUpdateInfo(
                            plugin_id=plugin_record['plugin_id'],
                            current_version=plugin_record['version'],
                            latest_version=latest_info.version,
                            repository=plugin_record['repository'],
                            update_available=True,
                            release_notes=latest_info.changelog,
                            breaking_changes=latest_info.breaking_changes
                        )
                        update_list.append(update_info)
                        
                except Exception as e:
                    logger.warning(f"检查更新失败 {plugin_record['plugin_id']}: {e}")
                    continue
            
            return update_list
            
        except Exception as e:
            logger.error(f"检查插件更新失败: {e}")
            return []
    
    async def update_plugin(
        self, 
        plugin_id: str,
        target_version: str = None,
        progress_callback: Optional[Callable] = None
    ) -> UpdateResult:
        """更新插件"""
        try:
            # 1. 获取当前插件信息
            current_plugin = await self.db.get_installed_plugin(plugin_id)
            if not current_plugin:
                return UpdateResult(
                    success=False,
                    message=f'插件未安装: {plugin_id}'
                )
            
            # 2. 获取目标版本信息
            if not target_version:
                latest_info = await self.registry.get_plugin_details(
                    plugin_id, current_plugin['repository']
                )
                target_version = latest_info.version
            
            target_plugin_info = await self.registry.get_plugin_details(
                plugin_id, current_plugin['repository']
            )
            
            # 3. 备份当前版本
            backup_path = await self._backup_current_plugin(current_plugin)
            
            try:
                # 4. 卸载当前版本
                unload_success = self.existing_manager.unload_plugin(plugin_id)
                if not unload_success:
                    logger.warning(f"卸载当前插件失败: {plugin_id}")
                
                # 5. 安装新版本
                install_result = await self.install_remote_plugin(
                    target_plugin_info, progress_callback
                )
                
                if install_result.success:
                    # 6. 清理备份
                    await self._cleanup_backup(backup_path)
                    
                    # 7. 更新数据库记录
                    await self.db.update_plugin_version(
                        plugin_id, 
                        target_version,
                        'updated_from_remote'
                    )
                    
                    return UpdateResult(
                        success=True,
                        message=f'插件更新成功: {plugin_id} -> {target_version}',
                        old_version=current_plugin['version'],
                        new_version=target_version
                    )
                else:
                    # 8. 回滚到备份版本
                    await self._restore_from_backup(backup_path, current_plugin)
                    return UpdateResult(
                        success=False,
                        message=f'插件更新失败，已回滚: {install_result.message}'
                    )
                    
            except Exception as e:
                # 异常情况下回滚
                await self._restore_from_backup(backup_path, current_plugin)
                raise
                
        except Exception as e:
            logger.error(f"插件更新异常 {plugin_id}: {e}")
            return UpdateResult(
                success=False,
                message=f'更新异常: {e}'
            )

@dataclass
class InstallResult:
    """安装结果"""
    success: bool
    message: str = ""
    error_type: str = ""  # license_required/compatibility/permission_denied/install_error
    plugin_info: Optional[RemotePluginInfo] = None
    install_path: Optional[str] = None

@dataclass
class UpdateResult:
    """更新结果"""
    success: bool
    message: str = ""
    old_version: str = ""
    new_version: str = ""

@dataclass
class PluginUpdateInfo:
    """插件更新信息"""
    plugin_id: str
    current_version: str
    latest_version: str
    repository: str
    update_available: bool
    release_notes: str = ""
    breaking_changes: List[str] = field(default_factory=list)
```

## 🎛️ UI集成和用户体验

### 远程插件市场界面增强

```python
class EnhancedPluginMarketDialog(QDialog):
    """增强的插件市场对话框 - 支持远程插件"""
    
    def __init__(self, existing_plugin_manager, parent=None):
        super().__init__(parent)
        self.existing_manager = existing_plugin_manager
        self.remote_manager = RemotePluginManager(existing_plugin_manager, PluginDatabaseService())
        self.current_search_results = []
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("FactorWeave-Quant插件市场 - 远程插件支持")
        self.setMinimumSize(1200, 800)
        
        layout = QVBoxLayout(self)
        
        # === 搜索区域 === #
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索插件名称、作者或关键词...")
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍 搜索")
        search_layout.addWidget(self.search_btn)
        
        # 仓库选择
        self.repository_combo = QComboBox()
        self.repository_combo.addItem("所有仓库", "all")
        self.repository_combo.addItem("官方仓库", "official")
        self.repository_combo.addItem("社区仓库", "community")
        search_layout.addWidget(self.repository_combo)
        
        layout.addLayout(search_layout)
        
        # === 筛选区域 === #
        filter_layout = QHBoxLayout()
        
        # 插件类型筛选
        type_group = QGroupBox("插件类型")
        type_layout = QHBoxLayout(type_group)
        
        self.type_filters = {}
        for plugin_type in PluginType:
            cb = QCheckBox(plugin_type.value)
            cb.setChecked(True)
            self.type_filters[plugin_type] = cb
            type_layout.addWidget(cb)
        
        filter_layout.addWidget(type_group)
        
        # 价格筛选
        price_group = QGroupBox("价格")
        price_layout = QHBoxLayout(price_group)
        
        self.free_only_cb = QCheckBox("仅免费")
        self.free_only_cb.setChecked(True)
        price_layout.addWidget(self.free_only_cb)
        
        self.paid_cb = QCheckBox("包含付费")
        price_layout.addWidget(self.paid_cb)
        
        filter_layout.addWidget(price_group)
        
        layout.addLayout(filter_layout)
        
        # === 结果显示区域 === #
        results_splitter = QSplitter(Qt.Horizontal)
        
        # 插件列表
        self.plugin_list = QListWidget()
        self.plugin_list.setMinimumWidth(350)
        results_splitter.addWidget(self.plugin_list)
        
        # 插件详情
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        # 插件基本信息
        self.plugin_name_label = QLabel("<b>选择插件查看详情</b>")
        self.plugin_name_label.setStyleSheet("font-size: 16px; padding: 10px;")
        details_layout.addWidget(self.plugin_name_label)
        
        # 插件描述
        self.plugin_description = QTextEdit()
        self.plugin_description.setReadOnly(True)
        self.plugin_description.setMaximumHeight(150)
        details_layout.addWidget(self.plugin_description)
        
        # 插件详细信息
        info_group = QGroupBox("插件信息")
        info_layout = QFormLayout(info_group)
        
        self.version_label = QLabel()
        self.author_label = QLabel()
        self.license_label = QLabel()
        self.downloads_label = QLabel()
        self.rating_label = QLabel()
        
        info_layout.addRow("版本:", self.version_label)
        info_layout.addRow("作者:", self.author_label)
        info_layout.addRow("许可证:", self.license_label)
        info_layout.addRow("下载量:", self.downloads_label)
        info_layout.addRow("评分:", self.rating_label)
        
        details_layout.addWidget(info_group)
        
        # 权限信息
        self.permissions_group = QGroupBox("所需权限")
        self.permissions_layout = QVBoxLayout(self.permissions_group)
        details_layout.addWidget(self.permissions_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("📥 安装插件")
        self.install_btn.setEnabled(False)
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.install_btn)
        
        self.purchase_btn = QPushButton("💳 购买许可证")
        self.purchase_btn.setVisible(False)
        self.purchase_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(self.purchase_btn)
        
        details_layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        details_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        details_layout.addWidget(self.status_label)
        
        results_splitter.addWidget(details_widget)
        results_splitter.setSizes([350, 850])
        
        layout.addWidget(results_splitter)
        
        # === 底部按钮 === #
        bottom_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 刷新")
        bottom_layout.addWidget(self.refresh_btn)
        
        self.settings_btn = QPushButton("⚙️ 设置")
        bottom_layout.addWidget(self.settings_btn)
        
        bottom_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
    
    def setup_connections(self):
        """设置信号连接"""
        self.search_btn.clicked.connect(self.search_plugins)
        self.search_input.returnPressed.connect(self.search_plugins)
        self.plugin_list.currentItemChanged.connect(self.on_plugin_selected)
        self.install_btn.clicked.connect(self.install_selected_plugin)
        self.purchase_btn.clicked.connect(self.purchase_plugin_license)
        self.refresh_btn.clicked.connect(self.refresh_plugin_list)
        self.close_btn.clicked.connect(self.accept)
        
        # 筛选器变化
        for cb in self.type_filters.values():
            cb.toggled.connect(self.apply_filters)
        self.free_only_cb.toggled.connect(self.apply_filters)
        self.paid_cb.toggled.connect(self.apply_filters)
    
    async def search_plugins(self):
        """搜索插件"""
        try:
            self.status_label.setText("正在搜索插件...")
            self.search_btn.setEnabled(False)
            
            # 构建搜索条件
            query = self.search_input.text().strip()
            filters = self.build_search_filters()
            
            # 执行远程搜索
            search_results = await self.remote_manager.registry.search_plugins(query, filters)
            
            # 更新搜索结果
            self.current_search_results = search_results
            self.update_plugin_list(search_results)
            
            self.status_label.setText(f"找到 {len(search_results)} 个插件")
            
        except Exception as e:
            self.status_label.setText(f"搜索失败: {e}")
            QMessageBox.warning(self, "搜索失败", f"插件搜索失