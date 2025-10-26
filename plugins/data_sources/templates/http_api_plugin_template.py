"""
HTTP API插件模板

提供基于HTTP REST API的数据源插件标准实现，包括：
- requests.Session连接池复用
- 智能重试机制（指数退避）
- API限流处理
- 响应缓存
- 请求签名支持

适用于大多数基于HTTP API的数据源（如交易所API、金融数据API等）
"""

from typing import Dict, List, Optional, Any
from abc import abstractmethod
import time
import hashlib
import hmac
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from loguru import logger

from .base_plugin_template import BasePluginTemplate
from core.plugin_types import AssetType, DataType


class HTTPAPIPluginTemplate(BasePluginTemplate):
    """
    HTTP API插件模板

    提供基于HTTP REST API的标准实现
    """

    def __init__(self):
        """初始化HTTP API插件"""
        super().__init__()

        # HTTP Session（连接池）
        self.session = None

        # 默认配置（子类可覆盖）
        self.DEFAULT_HTTP_CONFIG = {
            'base_url': '',
            'api_key': '',
            'api_secret': '',
            'timeout': 30,
            'max_retries': 3,
            'retry_backoff_factor': 0.5,
            'pool_connections': 10,
            'pool_maxsize': 10,
            'cache_enabled': True,
            'cache_ttl': 300,  # 缓存5分钟
            'rate_limit_per_minute': 1200,
        }

        # 合并配置
        self.DEFAULT_CONFIG.update(self.DEFAULT_HTTP_CONFIG)

        # 缓存
        self._cache = {}
        self._cache_timestamps = {}

        # 限流
        self._request_times = []
        self._rate_limit = 1200  # 默认每分钟1200次

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        config = super()._get_default_config()
        # 在__init__期间，DEFAULT_HTTP_CONFIG可能还未定义，使用默认值
        if hasattr(self, 'DEFAULT_HTTP_CONFIG'):
            config.update(self.DEFAULT_HTTP_CONFIG)
        else:
            # 提供默认的HTTP配置
            config.update({
                'base_url': '',
                'api_key': '',
                'api_secret': '',
                'timeout': 30,
                'max_retries': 3,
                'retry_backoff_factor': 0.5,
                'pool_connections': 10,
                'pool_maxsize': 10,
                'cache_enabled': True,
                'cache_ttl': 300,
                'rate_limit_per_minute': 1200,
            })
        return config

    def _check_dependencies(self) -> bool:
        """检查依赖"""
        try:
            import requests
            return True
        except ImportError:
            self.logger.error("requests 库未安装")
            return False

    def _validate_config(self) -> bool:
        """验证配置"""
        if not super()._validate_config():
            return False

        # 验证base_url
        if not self.config.get('base_url'):
            self.logger.error("base_url 未配置")
            return False

        # 验证限流配置
        self._rate_limit = self.config.get('rate_limit_per_minute', 1200)
        if self._rate_limit <= 0:
            self.logger.error("rate_limit_per_minute 必须大于0")
            return False

        return True

    def _establish_connection(self) -> bool:
        """建立HTTP连接"""
        try:
            # 创建Session（连接池）
            self.session = requests.Session()

            # 配置连接池
            pool_connections = self.config.get('pool_connections', 10)
            pool_maxsize = self.config.get('pool_maxsize', 10)

            # 配置重试策略
            max_retries = self.config.get('max_retries', 3)
            retry_backoff_factor = self.config.get('retry_backoff_factor', 0.5)

            retry_strategy = Retry(
                total=max_retries,
                backoff_factor=retry_backoff_factor,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "OPTIONS", "POST"]
            )

            adapter = HTTPAdapter(
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                max_retries=retry_strategy
            )

            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

            # 设置默认headers
            self.session.headers.update(self._get_default_headers())

            # 测试连接
            return self._test_connection()

        except Exception as e:
            self.logger.error(f"建立HTTP连接失败: {e}")
            return False

    @abstractmethod
    def _get_default_headers(self) -> Dict[str, str]:
        """
        获取默认请求头

        子类应实现此方法，返回特定API所需的headers

        Returns:
            Dict[str, str]: 请求头字典
        """
        return {
            'User-Agent': f'FactorWeave-Quant/{self.version}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    @abstractmethod
    def _test_connection(self) -> bool:
        """
        测试连接

        子类应实现此方法，执行简单的API测试请求

        Returns:
            bool: 测试是否成功
        """
        return True

    def _perform_health_check(self) -> bool:
        """执行健康检查"""
        if not self.session:
            return False

        return self._test_connection()

    def _cleanup(self):
        """清理资源"""
        if self.session:
            self.session.close()
            self.session = None

        # 清理缓存
        self._cache.clear()
        self._cache_timestamps.clear()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        signed: bool = False,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        执行HTTP请求

        Args:
            method: HTTP方法（GET, POST等）
            endpoint: API端点
            params: URL参数
            data: 请求体数据
            headers: 额外的headers
            signed: 是否需要签名
            use_cache: 是否使用缓存

        Returns:
            Optional[Dict]: 响应数据，失败返回None
        """
        if not self.session:
            self.logger.error("Session未初始化")
            return None

        try:
            # 限流检查
            self._rate_limit_check()

            # 构建完整URL
            url = f"{self.config['base_url']}{endpoint}"

            # 缓存检查（仅GET请求）
            if method.upper() == 'GET' and use_cache:
                cached_data = self._get_cached(url, params)
                if cached_data is not None:
                    return cached_data

            # 签名（如果需要）
            if signed:
                params = self._sign_request(method, endpoint, params, data)

            # 合并headers
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)

            # 发送请求
            start_time = time.time()

            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=request_headers,
                timeout=self.config.get('timeout', 30)
            )

            response_time = time.time() - start_time

            # 检查响应状态
            response.raise_for_status()

            # 解析响应
            result = response.json()

            # 缓存（仅GET请求）
            if method.upper() == 'GET' and use_cache and self.config.get('cache_enabled', True):
                self._set_cached(url, params, result)

            # 记录统计
            self._record_request(success=True, response_time=response_time)

            return result

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP错误 {method} {endpoint}: {e}")
            self._record_request(success=False)
            self._handle_http_error(e)
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"请求异常 {method} {endpoint}: {e}")
            self._record_request(success=False)
            return None

        except Exception as e:
            self.logger.error(f"未知错误 {method} {endpoint}: {e}")
            self._record_request(success=False)
            return None

    def _rate_limit_check(self):
        """限流检查"""
        current_time = time.time()

        # 清理1分钟前的请求记录
        self._request_times = [
            t for t in self._request_times
            if current_time - t < 60
        ]

        # 检查是否超过限流
        if len(self._request_times) >= self._rate_limit:
            # 计算需要等待的时间
            oldest_request = self._request_times[0]
            wait_time = 60 - (current_time - oldest_request)

            if wait_time > 0:
                self.logger.warning(f"触发限流，等待 {wait_time:.2f} 秒")
                time.sleep(wait_time)

        # 记录本次请求时间
        self._request_times.append(current_time)

    @abstractmethod
    def _sign_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """
        请求签名

        子类应实现此方法，根据特定API的签名规则进行签名

        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            data: 请求体数据

        Returns:
            Dict: 签名后的参数（通常包括signature, timestamp等）
        """
        # 默认实现：无签名
        return params or {}

    def _handle_http_error(self, error: requests.exceptions.HTTPError):
        """
        处理HTTP错误

        Args:
            error: HTTP错误对象
        """
        status_code = error.response.status_code

        if status_code == 429:
            # 限流错误
            self.logger.warning("API限流，降低健康度")
            self._health_score = max(0.0, self._health_score - 0.3)

        elif status_code == 401 or status_code == 403:
            # 认证错误
            self.logger.error("API认证失败，请检查API密钥")
            self._health_score = 0.0

        elif status_code >= 500:
            # 服务器错误
            self.logger.error("API服务器错误")
            self._health_score = max(0.0, self._health_score - 0.2)

    def _get_cached(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """获取缓存数据"""
        cache_key = self._generate_cache_key(url, params)

        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            cache_ttl = self.config.get('cache_ttl', 300)

            if time.time() - timestamp < cache_ttl:
                self.logger.debug(f"缓存命中: {cache_key}")
                return self._cache[cache_key]
            else:
                # 缓存过期
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]

        return None

    def _set_cached(self, url: str, params: Optional[Dict], data: Dict):
        """设置缓存"""
        cache_key = self._generate_cache_key(url, params)
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()

        # 限制缓存大小（LRU）
        if len(self._cache) > 1000:
            # 删除最旧的10%
            sorted_keys = sorted(
                self._cache_timestamps.keys(),
                key=lambda k: self._cache_timestamps[k]
            )
            for key in sorted_keys[:100]:
                del self._cache[key]
                del self._cache_timestamps[key]

    def _generate_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        if params:
            param_str = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
            return f"{url}?{param_str}"
        return url

    def _generate_signature(self, message: str, secret: str) -> str:
        """
        生成HMAC-SHA256签名

        Args:
            message: 待签名消息
            secret: 密钥

        Returns:
            str: 签名（hex格式）
        """
        return hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()


# 使用示例
if __name__ == "__main__":
    # 子类应继承并实现抽象方法
    pass
