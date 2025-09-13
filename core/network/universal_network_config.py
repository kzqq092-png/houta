"""
通用网络配置管理器
为所有插件提供统一的网络配置接口
"""

import json
import logging
import requests
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)


@dataclass
class NetworkEndpoint:
    """网络端点配置"""
    name: str  # 端点名称，如 'primary', 'backup1'
    url: str   # 完整URL
    description: str = ""  # 描述
    priority: int = 1      # 优先级，数字越大优先级越高
    timeout: int = 30      # 超时时间（秒）
    enabled: bool = True   # 是否启用
    success_count: int = 0 # 成功次数
    failure_count: int = 0 # 失败次数
    last_used: Optional[str] = None  # 最后使用时间
    avg_response_time: float = 0.0   # 平均响应时间


@dataclass
class PluginNetworkConfig:
    """插件网络配置"""
    plugin_id: str
    plugin_name: str
    endpoints: List[NetworkEndpoint] = field(default_factory=list)
    proxy_enabled: bool = False
    proxy_list: List[str] = field(default_factory=list)
    rate_limit_enabled: bool = True
    requests_per_minute: int = 30
    request_delay: float = 2.0  # 请求间隔（秒）
    retry_count: int = 3
    retry_delay: float = 1.0
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    custom_headers: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class INetworkConfigurable(ABC):
    """网络可配置接口 - 需要网络配置的插件应实现此接口"""
    
    @abstractmethod
    def get_default_endpoints(self) -> List[NetworkEndpoint]:
        """获取默认网络端点配置"""
        pass
    
    @abstractmethod
    def get_network_config_schema(self) -> Dict[str, Any]:
        """获取网络配置架构"""
        pass
    
    @abstractmethod
    def apply_network_config(self, config: PluginNetworkConfig) -> bool:
        """应用网络配置"""
        pass
    
    def get_endpoint_categories(self) -> Dict[str, str]:
        """获取端点分类 - 可选实现"""
        return {
            "primary": "主要端点",
            "backup": "备用端点", 
            "fallback": "后备端点"
        }


class UniversalNetworkConfigManager:
    """通用网络配置管理器"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = Path.cwd() / "config" / "network"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.configs: Dict[str, PluginNetworkConfig] = {}
        self.sessions: Dict[str, requests.Session] = {}
        
        # 加载已有配置
        self._load_all_configs()

    def _get_config_file_path(self, plugin_id: str) -> Path:
        """获取插件配置文件路径"""
        safe_plugin_id = plugin_id.replace(".", "_").replace("/", "_")
        return self.config_dir / f"{safe_plugin_id}_network.json"

    def register_plugin(self, plugin_id: str, plugin_name: str, 
                       network_configurable: INetworkConfigurable) -> bool:
        """
        注册插件网络配置
        
        Args:
            plugin_id: 插件ID
            plugin_name: 插件名称
            network_configurable: 实现了INetworkConfigurable接口的插件实例
            
        Returns:
            注册是否成功
        """
        try:
            # 检查是否已有配置
            existing_config = self.get_plugin_config(plugin_id)
            
            if existing_config:
                # 合并默认端点和现有配置
                default_endpoints = network_configurable.get_default_endpoints()
                self._merge_endpoints(existing_config, default_endpoints)
                config = existing_config
            else:
                # 创建新配置
                default_endpoints = network_configurable.get_default_endpoints()
                config = PluginNetworkConfig(
                    plugin_id=plugin_id,
                    plugin_name=plugin_name,
                    endpoints=default_endpoints
                )
            
            # 保存配置
            self.configs[plugin_id] = config
            self._save_plugin_config(plugin_id, config)
            
            # 应用配置到插件
            network_configurable.apply_network_config(config)
            
            logger.info(f"注册插件网络配置成功: {plugin_name} ({plugin_id})")
            return True
            
        except Exception as e:
            logger.error(f"注册插件网络配置失败 {plugin_id}: {e}")
            return False

    def _merge_endpoints(self, existing_config: PluginNetworkConfig, 
                        default_endpoints: List[NetworkEndpoint]):
        """合并现有端点和默认端点"""
        existing_urls = {ep.url for ep in existing_config.endpoints}
        
        # 添加新的默认端点
        for default_ep in default_endpoints:
            if default_ep.url not in existing_urls:
                existing_config.endpoints.append(default_ep)
                logger.info(f"添加新端点: {default_ep.name} - {default_ep.url}")

    def get_plugin_config(self, plugin_id: str) -> Optional[PluginNetworkConfig]:
        """获取插件网络配置"""
        if plugin_id in self.configs:
            return self.configs[plugin_id]
        
        # 尝试从文件加载
        config_file = self._get_config_file_path(plugin_id)
        if config_file.exists():
            return self._load_plugin_config(plugin_id)
        
        return None

    def update_plugin_config(self, plugin_id: str, config: PluginNetworkConfig) -> bool:
        """更新插件网络配置"""
        try:
            config.updated_at = datetime.now().isoformat()
            self.configs[plugin_id] = config
            self._save_plugin_config(plugin_id, config)
            
            logger.info(f"更新插件网络配置: {plugin_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新插件网络配置失败 {plugin_id}: {e}")
            return False

    def update_endpoints_from_string(self, plugin_id: str, endpoints_str: str) -> bool:
        """
        从分号分隔的字符串更新端点配置
        
        Args:
            plugin_id: 插件ID
            endpoints_str: 端点字符串，格式: "url1;url2;url3"
            
        Returns:
            更新是否成功
        """
        try:
            config = self.get_plugin_config(plugin_id)
            if not config:
                logger.error(f"插件配置不存在: {plugin_id}")
                return False
            
            # 解析端点字符串
            urls = [url.strip() for url in endpoints_str.split(';') if url.strip()]
            
            if not urls:
                logger.warning(f"端点字符串为空: {plugin_id}")
                return False
            
            # 清空现有端点
            config.endpoints.clear()
            
            # 创建新端点
            for i, url in enumerate(urls):
                endpoint = NetworkEndpoint(
                    name=f"endpoint_{i+1}",
                    url=url,
                    description=f"用户配置端点 {i+1}",
                    priority=len(urls) - i  # 第一个优先级最高
                )
                config.endpoints.append(endpoint)
            
            # 保存配置
            self.update_plugin_config(plugin_id, config)
            
            logger.info(f"从字符串更新端点配置: {plugin_id}, 端点数: {len(urls)}")
            return True
            
        except Exception as e:
            logger.error(f"从字符串更新端点配置失败 {plugin_id}: {e}")
            return False

    def get_endpoints_as_string(self, plugin_id: str) -> str:
        """
        获取端点配置的字符串表示
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            分号分隔的端点字符串
        """
        config = self.get_plugin_config(plugin_id)
        if not config or not config.endpoints:
            return ""
        
        # 按优先级排序
        sorted_endpoints = sorted(config.endpoints, key=lambda x: x.priority, reverse=True)
        urls = [ep.url for ep in sorted_endpoints if ep.enabled]
        
        return ';'.join(urls)

    def get_available_endpoint(self, plugin_id: str) -> Optional[NetworkEndpoint]:
        """获取可用的端点（按优先级和成功率）"""
        config = self.get_plugin_config(plugin_id)
        if not config or not config.endpoints:
            return None
        
        # 筛选启用的端点
        enabled_endpoints = [ep for ep in config.endpoints if ep.enabled]
        if not enabled_endpoints:
            return None
        
        # 按优先级和成功率排序
        def endpoint_score(ep: NetworkEndpoint) -> float:
            total_requests = ep.success_count + ep.failure_count
            success_rate = ep.success_count / max(total_requests, 1)
            # 综合评分：优先级 * 成功率 * 响应时间权重
            time_weight = 1.0 / (ep.avg_response_time + 0.1)  # 响应时间越短权重越高
            return ep.priority * success_rate * time_weight
        
        sorted_endpoints = sorted(enabled_endpoints, key=endpoint_score, reverse=True)
        return sorted_endpoints[0]

    def record_request_result(self, plugin_id: str, endpoint_url: str, 
                            success: bool, response_time: float = 0.0):
        """记录请求结果"""
        try:
            config = self.get_plugin_config(plugin_id)
            if not config:
                return
            
            # 找到对应端点
            endpoint = None
            for ep in config.endpoints:
                if ep.url == endpoint_url:
                    endpoint = ep
                    break
            
            if not endpoint:
                return
            
            # 更新统计信息
            if success:
                endpoint.success_count += 1
            else:
                endpoint.failure_count += 1
            
            endpoint.last_used = datetime.now().isoformat()
            
            # 更新平均响应时间
            if success and response_time > 0:
                total_requests = endpoint.success_count + endpoint.failure_count
                endpoint.avg_response_time = (
                    (endpoint.avg_response_time * (total_requests - 1) + response_time) / total_requests
                )
            
            # 保存配置
            self.update_plugin_config(plugin_id, config)
            
        except Exception as e:
            logger.error(f"记录请求结果失败: {e}")

    def get_session(self, plugin_id: str) -> requests.Session:
        """获取插件的HTTP会话"""
        if plugin_id not in self.sessions:
            self.sessions[plugin_id] = requests.Session()
            
            # 应用配置
            config = self.get_plugin_config(plugin_id)
            if config:
                # 设置User-Agent
                headers = {'User-Agent': config.user_agent}
                headers.update(config.custom_headers)
                self.sessions[plugin_id].headers.update(headers)
                
                # 设置代理
                if config.proxy_enabled and config.proxy_list:
                    # 简单轮换代理
                    proxy_url = config.proxy_list[0]  # 可以实现更复杂的选择逻辑
                    proxies = {
                        'http': f'http://{proxy_url}',
                        'https': f'http://{proxy_url}'
                    }
                    self.sessions[plugin_id].proxies.update(proxies)
        
        return self.sessions[plugin_id]

    def make_request(self, plugin_id: str, method: str = 'GET', 
                    endpoint_name: str = None, url: str = None, **kwargs) -> requests.Response:
        """
        使用配置进行HTTP请求
        
        Args:
            plugin_id: 插件ID
            method: HTTP方法
            endpoint_name: 端点名称（如果指定，则使用配置的端点）
            url: 直接指定URL（如果endpoint_name未指定）
            **kwargs: requests参数
            
        Returns:
            Response对象
        """
        config = self.get_plugin_config(plugin_id)
        if not config:
            raise Exception(f"插件配置不存在: {plugin_id}")
        
        # 确定请求URL
        target_url = url
        if endpoint_name:
            endpoint = None
            for ep in config.endpoints:
                if ep.name == endpoint_name and ep.enabled:
                    endpoint = ep
                    break
            
            if not endpoint:
                raise Exception(f"端点不存在或已禁用: {endpoint_name}")
            
            target_url = endpoint.url
        elif not target_url:
            # 自动选择最佳端点
            endpoint = self.get_available_endpoint(plugin_id)
            if not endpoint:
                raise Exception(f"没有可用端点: {plugin_id}")
            
            target_url = endpoint.url
        
        # 频率限制
        if config.rate_limit_enabled:
            time.sleep(config.request_delay)
        
        # 发起请求
        session = self.get_session(plugin_id)
        
        # 设置超时
        if 'timeout' not in kwargs:
            kwargs['timeout'] = next(
                (ep.timeout for ep in config.endpoints if ep.url == target_url),
                30
            )
        
        start_time = time.time()
        
        try:
            response = session.request(method, target_url, **kwargs)
            response_time = time.time() - start_time
            
            # 记录成功请求
            self.record_request_result(plugin_id, target_url, True, response_time)
            
            return response
            
        except Exception as e:
            # 记录失败请求
            self.record_request_result(plugin_id, target_url, False)
            raise

    def _load_all_configs(self):
        """加载所有配置文件"""
        try:
            for config_file in self.config_dir.glob("*_network.json"):
                plugin_id = config_file.stem.replace("_network", "").replace("_", ".")
                self._load_plugin_config(plugin_id)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")

    def _load_plugin_config(self, plugin_id: str) -> Optional[PluginNetworkConfig]:
        """加载插件配置"""
        try:
            config_file = self._get_config_file_path(plugin_id)
            if not config_file.exists():
                return None
            
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换端点数据
            endpoints = []
            for ep_data in data.get('endpoints', []):
                endpoint = NetworkEndpoint(**ep_data)
                endpoints.append(endpoint)
            
            # 创建配置对象
            config = PluginNetworkConfig(
                plugin_id=data['plugin_id'],
                plugin_name=data['plugin_name'],
                endpoints=endpoints,
                proxy_enabled=data.get('proxy_enabled', False),
                proxy_list=data.get('proxy_list', []),
                rate_limit_enabled=data.get('rate_limit_enabled', True),
                requests_per_minute=data.get('requests_per_minute', 30),
                request_delay=data.get('request_delay', 2.0),
                retry_count=data.get('retry_count', 3),
                retry_delay=data.get('retry_delay', 1.0),
                user_agent=data.get('user_agent', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
                custom_headers=data.get('custom_headers', {}),
                created_at=data.get('created_at', datetime.now().isoformat()),
                updated_at=data.get('updated_at', datetime.now().isoformat())
            )
            
            self.configs[plugin_id] = config
            return config
            
        except Exception as e:
            logger.error(f"加载插件配置失败 {plugin_id}: {e}")
            return None

    def _save_plugin_config(self, plugin_id: str, config: PluginNetworkConfig):
        """保存插件配置"""
        try:
            config_file = self._get_config_file_path(plugin_id)
            
            # 转换为可序列化的数据
            data = {
                'plugin_id': config.plugin_id,
                'plugin_name': config.plugin_name,
                'endpoints': [
                    {
                        'name': ep.name,
                        'url': ep.url,
                        'description': ep.description,
                        'priority': ep.priority,
                        'timeout': ep.timeout,
                        'enabled': ep.enabled,
                        'success_count': ep.success_count,
                        'failure_count': ep.failure_count,
                        'last_used': ep.last_used,
                        'avg_response_time': ep.avg_response_time
                    }
                    for ep in config.endpoints
                ],
                'proxy_enabled': config.proxy_enabled,
                'proxy_list': config.proxy_list,
                'rate_limit_enabled': config.rate_limit_enabled,
                'requests_per_minute': config.requests_per_minute,
                'request_delay': config.request_delay,
                'retry_count': config.retry_count,
                'retry_delay': config.retry_delay,
                'user_agent': config.user_agent,
                'custom_headers': config.custom_headers,
                'created_at': config.created_at,
                'updated_at': config.updated_at
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"保存插件配置失败 {plugin_id}: {e}")

    def get_all_plugin_configs(self) -> Dict[str, PluginNetworkConfig]:
        """获取所有插件配置"""
        return self.configs.copy()

    def get_plugin_statistics(self, plugin_id: str) -> Dict[str, Any]:
        """获取插件网络统计信息"""
        config = self.get_plugin_config(plugin_id)
        if not config:
            return {}
        
        total_requests = 0
        total_success = 0
        total_failures = 0
        avg_response_time = 0.0
        
        for ep in config.endpoints:
            total_requests += ep.success_count + ep.failure_count
            total_success += ep.success_count
            total_failures += ep.failure_count
            avg_response_time += ep.avg_response_time
        
        if config.endpoints:
            avg_response_time /= len(config.endpoints)
        
        return {
            'plugin_id': plugin_id,
            'plugin_name': config.plugin_name,
            'total_endpoints': len(config.endpoints),
            'enabled_endpoints': len([ep for ep in config.endpoints if ep.enabled]),
            'total_requests': total_requests,
            'total_success': total_success,
            'total_failures': total_failures,
            'success_rate': total_success / max(total_requests, 1),
            'avg_response_time': avg_response_time,
            'proxy_enabled': config.proxy_enabled,
            'rate_limit_enabled': config.rate_limit_enabled
        }


# 全局实例
_universal_network_manager = None


def get_universal_network_manager() -> UniversalNetworkConfigManager:
    """获取通用网络配置管理器实例"""
    global _universal_network_manager
    if _universal_network_manager is None:
        _universal_network_manager = UniversalNetworkConfigManager()
    return _universal_network_manager
