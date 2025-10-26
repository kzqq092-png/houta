"""
自动为所有HTTP请求添加反爬虫功能

在插件加载时自动应用，无需修改每个插件
"""

import functools
from loguru import logger

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests库未安装")

from .retry_helper import (
    get_random_headers, get_conservative_headers, get_minimal_anti_crawler_headers,
    get_ultra_conservative_headers, is_connection_error
)


# 标记是否已应用补丁
_PATCH_APPLIED = False


def _smart_request_with_retry(original_func, *args, **kwargs):
    """
    智能请求处理，支持连接错误重试
    
    Args:
        original_func: 原始请求函数
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        请求结果
    """
    max_retries = 2
    retry_delay = 1.0
    
    for attempt in range(max_retries + 1):
        try:
            # 创建kwargs的副本，避免修改原始参数
            current_kwargs = kwargs.copy()
            
            # 根据尝试次数选择请求头策略
            if attempt == 0:
                # 第一次尝试：使用智能策略
                if 'headers' not in current_kwargs or not current_kwargs['headers']:
                    current_kwargs['headers'] = get_conservative_headers()
                else:
                    anti_crawler_headers = get_minimal_anti_crawler_headers()
                    for key, value in anti_crawler_headers.items():
                        if key not in current_kwargs['headers']:
                            current_kwargs['headers'][key] = value
            elif attempt == 1:
                # 第二次尝试：使用超保守策略
                logger.debug("连接错误，使用超保守请求头重试")
                current_kwargs['headers'] = get_ultra_conservative_headers()
                # 添加额外延迟
                import time
                time.sleep(retry_delay)
            else:
                # 最后一次尝试：使用最保守策略
                logger.debug("连接错误，使用最保守请求头重试")
                current_kwargs['headers'] = get_ultra_conservative_headers()
                # 添加更长延迟
                import time
                time.sleep(retry_delay * 2)
            
            return original_func(*args, **current_kwargs)
            
        except Exception as e:
            if is_connection_error(e) and attempt < max_retries:
                logger.debug(f"检测到连接错误，准备重试 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)[:100]}")
                continue
            else:
                # 非连接错误或重试次数用完，直接抛出异常
                if is_connection_error(e):
                    logger.warning(f"连接错误重试失败，已尝试 {attempt + 1} 次: {str(e)[:100]}")
                raise e


def patch_requests_globally():
    """
    全局补丁requests库，为所有HTTP请求添加反爬虫功能
    
    这个函数会修改requests.get和requests.post的默认行为：
    1. 自动添加浏览器请求头
    2. 保留用户自定义的请求头
    
    Returns:
        bool: 是否成功应用补丁
    """
    global _PATCH_APPLIED
    
    if _PATCH_APPLIED:
        logger.debug("requests补丁已经应用，跳过")
        return True
    
    if not REQUESTS_AVAILABLE:
        logger.warning("requests库不可用，无法应用补丁")
        return False
    
    try:
        # 保存原始函数
        original_get = requests.get
        original_post = requests.post
        original_request = requests.request
        
        @functools.wraps(original_get)
        def patched_get(*args, **kwargs):
            """修补后的requests.get - 智能反爬虫策略"""
            return _smart_request_with_retry(original_get, *args, **kwargs)
        
        @functools.wraps(original_post)
        def patched_post(*args, **kwargs):
            """修补后的requests.post - 智能反爬虫策略"""
            return _smart_request_with_retry(original_post, *args, **kwargs)
        
        @functools.wraps(original_request)
        def patched_request(*args, **kwargs):
            """修补后的requests.request - 智能反爬虫策略"""
            return _smart_request_with_retry(original_request, *args, **kwargs)
        
        # 应用补丁
        requests.get = patched_get
        requests.post = patched_post
        requests.request = patched_request
        
        # 也修补Session类
        original_session_request = requests.Session.request
        
        @functools.wraps(original_session_request)
        def patched_session_request(self, *args, **kwargs):
            """修补后的Session.request - 智能反爬虫策略"""
            return _smart_request_with_retry(original_session_request, self, *args, **kwargs)
        
        requests.Session.request = patched_session_request
        
        _PATCH_APPLIED = True
        logger.info("✅ 已为所有HTTP请求应用反爬虫补丁（requests库）")
        return True
        
    except Exception as e:
        logger.error(f"应用requests补丁失败: {e}")
        return False


# 自动应用补丁
# 当这个模块被导入时，自动应用
if REQUESTS_AVAILABLE:
    patch_requests_globally()

