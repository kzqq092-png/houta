"""
TET (Transform-Extract-Transform) 数据处理框架

现代化的数据处理管道，支持多数据源、智能路由、缓存管理等功能。
"""

from .pipeline import TETDataPipeline, TETConfig
from .models import StandardQuery, StandardData, DataRequest, DataResponse
from .adapters import TETDataAdapter, HIkyuuTETAdapter, AkShareTETAdapter
from .router import TETDataRouter
from .cache import TETCacheManager, CacheConfig
from .transformers import DataTransformer, DataCleaningTransformer, DataValidationTransformer
from .exceptions import TETProcessingError, DataSourceUnavailableError, NoAvailableDataSourceError

__version__ = "1.0.0"
__author__ = "FactorWeave Team"

__all__ = [
    # 核心组件
    'TETDataPipeline',
    'TETConfig',

    # 数据模型
    'StandardQuery',
    'StandardData',
    'DataRequest',
    'DataResponse',

    # 适配器
    'TETDataAdapter',
    'HIkyuuTETAdapter',
    'AkShareTETAdapter',

    # 路由和缓存
    'TETDataRouter',
    'TETCacheManager',
    'CacheConfig',

    # 数据转换器
    'DataTransformer',
    'DataCleaningTransformer',
    'DataValidationTransformer',

    # 异常类
    'TETProcessingError',
    'DataSourceUnavailableError',
    'NoAvailableDataSourceError'
]


def create_tet_pipeline(config: dict = None) -> TETDataPipeline:
    """
    创建TET数据管道实例

    Args:
        config: 配置字典

    Returns:
        TET数据管道实例
    """
    tet_config = TETConfig.from_dict(config or {})
    return TETDataPipeline(tet_config)
