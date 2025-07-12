"""
股票管理业务逻辑

负责股票相关的业务逻辑处理，包括：
- 股票筛选和搜索
- 股票信息管理
- 行业分类管理
- 自选股管理
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..data.models import StockInfo, QueryParams
from ..data.data_access import DataAccess


class StockManager:
    """股票管理器"""

    def __init__(self, data_access: DataAccess):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_access = data_access
        self._favorites = set()  # 自选股列表
        self._industry_cache = {}  # 行业缓存

    def get_stock_info(self, stock_code: str) -> Optional[StockInfo]:
        """
        获取股票基本信息

        Args:
            stock_code: 股票代码

        Returns:
            股票信息对象，如果不存在返回None
        """
        try:
            stock_info = self.data_access.get_stock_info(stock_code)
            if stock_info:
                # 添加自选股标记
                stock_info.is_favorite = stock_code in self._favorites
            return stock_info
        except Exception as e:
            self.logger.error(
                f"Failed to get stock info for {stock_code}: {e}")
            return None

    def get_stock_list(self, market: Optional[str] = None,
                       industry: Optional[str] = None) -> List[StockInfo]:
        """
        获取股票列表

        Args:
            market: 市场筛选（如'SH', 'SZ'）
            industry: 行业筛选

        Returns:
            股票信息列表
        """
        try:
            stock_list = self.data_access.get_stock_list(market)

            # 行业筛选
            if industry:
                stock_list = [s for s in stock_list if s.industry == industry]

            # 添加自选股标记
            for stock in stock_list:
                stock.is_favorite = stock.code in self._favorites

            return stock_list
        except Exception as e:
            self.logger.error(f"Failed to get stock list: {e}")
            return []

    def search_stocks(self, keyword: str, limit: int = 50) -> List[StockInfo]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词（股票代码或名称）
            limit: 返回结果数量限制

        Returns:
            匹配的股票信息列表
        """
        try:
            stock_list = self.data_access.search_stocks(keyword)

            # 限制返回数量
            if limit > 0:
                stock_list = stock_list[:limit]

            # 添加自选股标记
            for stock in stock_list:
                stock.is_favorite = stock.code in self._favorites

            return stock_list
        except Exception as e:
            self.logger.error(
                f"Failed to search stocks with keyword '{keyword}': {e}")
            return []

    def add_to_favorites(self, stock_code: str) -> bool:
        """
        添加到自选股

        Args:
            stock_code: 股票代码

        Returns:
            是否添加成功
        """
        try:
            # 验证股票是否存在
            stock_info = self.data_access.get_stock_info(stock_code)
            if not stock_info:
                self.logger.warning(
                    f"Stock {stock_code} not found, cannot add to favorites")
                return False

            self._favorites.add(stock_code)
            self.logger.info(f"Added {stock_code} to favorites")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add {stock_code} to favorites: {e}")
            return False

    def remove_from_favorites(self, stock_code: str) -> bool:
        """
        从自选股中移除

        Args:
            stock_code: 股票代码

        Returns:
            是否移除成功
        """
        try:
            if stock_code in self._favorites:
                self._favorites.remove(stock_code)
                self.logger.info(f"Removed {stock_code} from favorites")
                return True
            else:
                self.logger.warning(f"Stock {stock_code} not in favorites")
                return False
        except Exception as e:
            self.logger.error(
                f"Failed to remove {stock_code} from favorites: {e}")
            return False

    def get_favorites(self) -> List[StockInfo]:
        """
        获取自选股列表

        Returns:
            自选股信息列表
        """
        try:
            favorites_list = []
            for stock_code in self._favorites:
                stock_info = self.data_access.get_stock_info(stock_code)
                if stock_info:
                    stock_info.is_favorite = True
                    favorites_list.append(stock_info)

            return favorites_list
        except Exception as e:
            self.logger.error(f"Failed to get favorites: {e}")
            return []

    def is_favorite(self, stock_code: str) -> bool:
        """
        检查是否为自选股

        Args:
            stock_code: 股票代码

        Returns:
            是否为自选股
        """
        return stock_code in self._favorites

    def get_industries(self) -> List[str]:
        """
        获取所有行业列表

        Returns:
            行业名称列表
        """
        try:
            if not self._industry_cache:
                # 从股票列表中提取行业信息
                stock_list = self.data_access.get_stock_list()
                industries = set()
                for stock in stock_list:
                    if stock.industry:
                        industries.add(stock.industry)
                self._industry_cache = sorted(list(industries))

            return self._industry_cache
        except Exception as e:
            self.logger.error(f"Failed to get industries: {e}")
            return []

    def get_stocks_by_industry(self, industry: str) -> List[StockInfo]:
        """
        按行业获取股票列表

        Args:
            industry: 行业名称

        Returns:
            该行业的股票列表
        """
        return self.get_stock_list(industry=industry)

    def validate_stock_code(self, stock_code: str) -> bool:
        """
        验证股票代码是否有效

        Args:
            stock_code: 股票代码

        Returns:
            是否有效
        """
        try:
            stock_info = self.data_access.get_stock_info(stock_code)
            return stock_info is not None
        except Exception as e:
            self.logger.error(
                f"Failed to validate stock code {stock_code}: {e}")
            return False

    def get_stock_statistics(self) -> Dict[str, Any]:
        """
        获取股票统计信息

        Returns:
            统计信息字典
        """
        try:
            stock_list = self.data_access.get_stock_list()

            # 按市场统计
            market_stats = {}
            industry_stats = {}

            for stock in stock_list:
                # 市场统计
                market = stock.market or 'Unknown'
                market_stats[market] = market_stats.get(market, 0) + 1

                # 行业统计
                industry = stock.industry or 'Unknown'
                industry_stats[industry] = industry_stats.get(industry, 0) + 1

            return {
                'total_stocks': len(stock_list),
                'favorites_count': len(self._favorites),
                'market_distribution': market_stats,
                'industry_distribution': industry_stats,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get stock statistics: {e}")
            return {}

    def clear_cache(self) -> None:
        """清除缓存"""
        self._industry_cache.clear()
        self.logger.info("Stock manager cache cleared")
