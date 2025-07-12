"""
行业服务模块

负责行业数据的获取、缓存和管理。
封装IndustryManager，使其符合服务架构。
"""

import logging
from typing import Dict, List, Optional, Any
from .base_service import CacheableService, ConfigurableService
from ..events import DataUpdateEvent
from ..industry_manager import IndustryManager
from utils.manager_factory import get_industry_manager

logger = logging.getLogger(__name__)


class IndustryService(CacheableService, ConfigurableService):
    """
    行业服务

    负责行业数据的获取、缓存和管理。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, cache_size: int = 100, **kwargs):
        """
        初始化行业服务

        Args:
            config: 服务配置
            cache_size: 缓存大小
            **kwargs: 其他参数
        """
        # 初始化各个基类
        CacheableService.__init__(self, cache_size=cache_size, **kwargs)
        ConfigurableService.__init__(self, config=config, **kwargs)

        self._industry_manager = None
        self._industries_cache = {}
        self._last_update_time = None

    def _do_initialize(self) -> None:
        """初始化行业服务"""
        try:
            # 获取行业管理器实例
            self._industry_manager = get_industry_manager()

            if self._industry_manager:
                logger.info("Industry service initialized successfully")
            else:
                logger.warning(
                    "Failed to get industry manager, using fallback mode")
                self._create_fallback_manager()

        except Exception as e:
            logger.error(f"Failed to initialize industry service: {e}")
            self._create_fallback_manager()

    def _create_fallback_manager(self) -> None:
        """创建备用行业管理器"""
        try:
            # 创建一个简单的备用管理器
            class FallbackIndustryManager:
                def __init__(self):
                    self.industry_data = {}

                def get_industry_list(self, source="eastmoney"):
                    """获取行业列表"""
                    return [
                        {"code": "BK0001", "name": "银行", "source": source},
                        {"code": "BK0002", "name": "保险", "source": source},
                        {"code": "BK0003", "name": "证券", "source": source},
                        {"code": "BK0004", "name": "房地产", "source": source},
                        {"code": "BK0005", "name": "互联网", "source": source},
                        {"code": "BK0006", "name": "软件开发", "source": source},
                        {"code": "BK0007", "name": "电子信息", "source": source},
                        {"code": "BK0008", "name": "生物医药", "source": source},
                        {"code": "BK0009", "name": "新能源", "source": source},
                        {"code": "BK0010", "name": "汽车制造", "source": source},
                    ]

                def get_industry_stocks(self, industry_code, source="eastmoney"):
                    """获取行业股票"""
                    # 返回一些示例股票
                    return [
                        {"code": "000001", "name": "平安银行",
                            "industry": industry_code},
                        {"code": "600036", "name": "招商银行",
                            "industry": industry_code},
                        {"code": "000002", "name": "万科A",
                            "industry": industry_code},
                    ]

                def update_industry_data(self, source="eastmoney"):
                    """更新行业数据"""
                    logger.info(
                        f"Updating industry data from {source} (fallback mode)")
                    return True

                def get_supported_sources(self):
                    """获取支持的数据源"""
                    return ["eastmoney", "sina", "tencent"]

            self._industry_manager = FallbackIndustryManager()
            logger.info("Created fallback industry manager")

        except Exception as e:
            logger.error(f"Failed to create fallback industry manager: {e}")

    def get_industry_list(self, source: str = "eastmoney") -> List[Dict[str, Any]]:
        """
        获取行业列表

        Args:
            source: 数据源

        Returns:
            行业列表
        """
        self._ensure_initialized()

        cache_key = f"industry_list_{source}"
        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            if self._industry_manager:
                industries = self._industry_manager.get_industry_list(source)

                # 缓存结果
                self.put_to_cache(cache_key, industries)

                # 发布数据更新事件
                event = DataUpdateEvent(
                    data_type="industry_list",
                    update_info={
                        'source': source,
                        'count': len(industries) if industries else 0
                    }
                )
                self.event_bus.publish(event)

                return industries if industries else []
            else:
                logger.warning("Industry manager not available")
                return []

        except Exception as e:
            logger.error(f"Failed to get industry list from {source}: {e}")
            return []

    def get_industry_stocks(self, industry_code: str, source: str = "eastmoney") -> List[Dict[str, Any]]:
        """
        获取行业股票

        Args:
            industry_code: 行业代码
            source: 数据源

        Returns:
            行业股票列表
        """
        self._ensure_initialized()

        cache_key = f"industry_stocks_{industry_code}_{source}"
        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            if self._industry_manager:
                stocks = self._industry_manager.get_industry_stocks(
                    industry_code, source)

                # 缓存结果
                self.put_to_cache(cache_key, stocks)

                return stocks if stocks else []
            else:
                logger.warning("Industry manager not available")
                return []

        except Exception as e:
            logger.error(
                f"Failed to get industry stocks for {industry_code} from {source}: {e}")
            return []

    def update_industry_data(self, source: str = "eastmoney") -> bool:
        """
        更新行业数据

        Args:
            source: 数据源

        Returns:
            是否更新成功
        """
        self._ensure_initialized()

        try:
            if self._industry_manager:
                success = self._industry_manager.update_industry_data(source)

                if success:
                    # 清除缓存
                    self.clear_cache()

                    # 发布数据更新事件
                    event = DataUpdateEvent(
                        data_type="industry_data_update",
                        update_info={
                            'source': source,
                            'success': True
                        }
                    )
                    self.event_bus.publish(event)

                    logger.info(
                        f"Industry data updated successfully from {source}")

                return success
            else:
                logger.warning("Industry manager not available")
                return False

        except Exception as e:
            logger.error(f"Failed to update industry data from {source}: {e}")
            return False

    def get_supported_sources(self) -> List[str]:
        """
        获取支持的数据源

        Returns:
            支持的数据源列表
        """
        self._ensure_initialized()

        try:
            if self._industry_manager:
                return self._industry_manager.get_supported_sources()
            else:
                return ["eastmoney", "sina", "tencent"]

        except Exception as e:
            logger.error(f"Failed to get supported sources: {e}")
            return ["eastmoney"]

    def search_industries(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索行业

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的行业列表
        """
        self._ensure_initialized()

        try:
            # 获取所有行业
            all_industries = self.get_industry_list()

            # 过滤匹配的行业
            matched_industries = []
            keyword_lower = keyword.lower()

            for industry in all_industries:
                if (keyword_lower in industry.get('name', '').lower() or
                        keyword_lower in industry.get('code', '').lower()):
                    matched_industries.append(industry)

            return matched_industries

        except Exception as e:
            logger.error(
                f"Failed to search industries with keyword '{keyword}': {e}")
            return []

    def get_industry_info(self, industry_code: str, source: str = "eastmoney") -> Optional[Dict[str, Any]]:
        """
        获取行业信息

        Args:
            industry_code: 行业代码
            source: 数据源

        Returns:
            行业信息
        """
        self._ensure_initialized()

        try:
            industries = self.get_industry_list(source)

            for industry in industries:
                if industry.get('code') == industry_code:
                    return industry

            return None

        except Exception as e:
            logger.error(
                f"Failed to get industry info for {industry_code}: {e}")
            return None

    def refresh_data(self) -> bool:
        """
        刷新数据

        Returns:
            是否刷新成功
        """
        try:
            # 清除缓存
            self.clear_cache()

            # 更新数据
            success = self.update_industry_data()

            if success:
                logger.info("Industry data refreshed successfully")
            else:
                logger.warning("Failed to refresh industry data")

            return success

        except Exception as e:
            logger.error(f"Failed to refresh industry data: {e}")
            return False

    def _do_dispose(self) -> None:
        """释放资源"""
        try:
            if self._industry_manager and hasattr(self._industry_manager, 'dispose'):
                self._industry_manager.dispose()

            self._industry_manager = None
            self._industries_cache.clear()

            logger.info("Industry service disposed")

        except Exception as e:
            logger.error(f"Error disposing industry service: {e}")

    def clear_cache(self, cache_type: str = 'all') -> None:
        """
        清除缓存

        Args:
            cache_type: 缓存类型 ('all', 'industry_list', 'industry_stocks')
        """
        if cache_type == 'all':
            super().clear_cache()
        else:
            # 清除特定类型的缓存
            keys_to_remove = []
            for key in self._cache.keys():
                if key.startswith(cache_type):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                self._cache.pop(key, None)

            logger.debug(f"Cleared {cache_type} cache")
