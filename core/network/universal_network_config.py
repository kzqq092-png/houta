"""
通用网络配置模块
"""

import requests
from typing import Dict, Any, Optional, List, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NetworkEndpoint:
    """网络端点配置"""
    name: str
    url: str
    description: str = ""
    priority: int = 0
    timeout: int = 30
    headers: Optional[Dict[str, str]] = None
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class PluginNetworkConfig:
    """插件网络配置"""
    plugin_id: str
    endpoints: List[NetworkEndpoint]
    default_headers: Optional[Dict[str, str]] = None
    timeout: int = 30
    retry_config: Optional[Dict[str, Any]] = None


class INetworkConfigurable(Protocol):
    """网络可配置接口"""

    @abstractmethod
    def get_network_config(self) -> PluginNetworkConfig:
        """获取网络配置"""
        pass

    @abstractmethod
    def update_network_config(self, config: PluginNetworkConfig) -> bool:
        """更新网络配置"""
        pass

    @abstractmethod
    def test_network_connectivity(self) -> bool:
        """测试网络连通性"""
        pass


class UniversalNetworkManager:
    """通用网络管理器"""

    def __init__(self):
        self.configs: Dict[str, PluginNetworkConfig] = {}
        self.sessions: Dict[str, requests.Session] = {}

    def register_plugin_config(self, plugin_id: str, config: PluginNetworkConfig):
        """注册插件网络配置"""
        self.configs[plugin_id] = config

    def get_plugin_config(self, plugin_id: str) -> Optional[PluginNetworkConfig]:
        """获取插件网络配置"""
        return self.configs.get(plugin_id)

    def get_session(self, plugin_id: str) -> requests.Session:
        """获取插件的会话对象"""
        if plugin_id not in self.sessions:
            session = requests.Session()
            config = self.configs.get(plugin_id)
            if config and config.default_headers:
                session.headers.update(config.default_headers)
            self.sessions[plugin_id] = session
        return self.sessions[plugin_id]


class UniversalNetworkConfig:
    """通用网络配置类"""

    def __init__(self):
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        self.timeout = 30
        self.retry_count = 3
        self.retry_delay = 1

    def get_session(self, headers: Optional[Dict[str, str]] = None) -> requests.Session:
        """获取配置好的会话对象"""
        session = requests.Session()

        # 设置默认请求头
        session.headers.update(self.default_headers)
        if headers:
            session.headers.update(headers)

        return session

    def get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """获取请求头"""
        headers = self.default_headers.copy()
        if additional_headers:
            headers.update(additional_headers)
        return headers


# 全局实例
network_config = UniversalNetworkConfig()
_universal_network_manager = None


def get_universal_network_manager() -> UniversalNetworkManager:
    """获取全局网络管理器实例"""
    global _universal_network_manager
    if _universal_network_manager is None:
        _universal_network_manager = UniversalNetworkManager()
    return _universal_network_manager
