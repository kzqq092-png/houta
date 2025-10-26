"""
数据源工具模块

自动为所有数据源插件提供反爬虫功能
"""

from .retry_helper import (
    retry_on_connection_error,
    batch_retry_wrapper,
    with_timeout,
    log_execution_time,
    get_random_headers,
    apply_anti_crawler_delay,
    set_global_rate_limit
)

# 自动应用全局requests补丁
# 当任何插件导入这个模块时，自动为所有HTTP请求添加反爬虫功能
from .auto_patch_requests import patch_requests_globally
patch_requests_globally()

__all__ = [
    'retry_on_connection_error',
    'batch_retry_wrapper',
    'with_timeout',
    'log_execution_time',
    'get_random_headers',
    'apply_anti_crawler_delay',
    'set_global_rate_limit',
    'patch_requests_globally'
]

