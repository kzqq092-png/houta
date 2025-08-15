"""
数据仓库层

定义数据访问的抽象接口和具体实现。
遵循仓库模式，为不同类型的数据提供统一的访问接口。
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd

from .models import StockInfo, KlineData, MarketData, QueryParams

logger = logging.getLogger(__name__)


class FallbackDataManager:
    """
    统一的备用数据管理器

    当主数据管理器不可用时，提供模拟数据以确保系统正常运行。
    """

    def __init__(self):
        self.logger = logging.getLogger("FallbackDataManager")
        self.mock_stocks = [
            {'code': '000001', 'name': '平安银行', 'market': 'sz', 'industry': '银行'},
            {'code': '000002', 'name': '万科A', 'market': 'sz', 'industry': '房地产'},
            {'code': '600000', 'name': '浦发银行', 'market': 'sh', 'industry': '银行'},
            {'code': '600036', 'name': '招商银行', 'market': 'sh', 'industry': '银行'},
            {'code': '600519', 'name': '贵州茅台', 'market': 'sh', 'industry': '食品饮料'},
            {'code': '000858', 'name': '五粮液', 'market': 'sz', 'industry': '食品饮料'},
            {'code': '300750', 'name': '宁德时代', 'market': 'sz', 'industry': '电池'},
            {'code': '002415', 'name': '海康威视', 'market': 'sz', 'industry': '电子'},
            {'code': '000725', 'name': '京东方A', 'market': 'sz', 'industry': '电子'},
            {'code': '600276', 'name': '恒瑞医药', 'market': 'sh', 'industry': '医药生物'},
        ]

    def get_stock_list(self, market=None):
        """返回模拟股票列表"""
        if market:
            return [s for s in self.mock_stocks if s['market'] == market]
        return self.mock_stocks

    def get_stock_info(self, stock_code):
        """返回模拟股票信息"""
        for stock in self.mock_stocks:
            if stock['code'] == stock_code:
                return stock
        return None

    def search_stocks(self, keyword):
        """搜索股票"""
        keyword_lower = keyword.lower()
        results = []
        for stock in self.mock_stocks:
            if (keyword_lower in stock['code'].lower() or
                    keyword_lower in stock['name'].lower()):
                results.append(stock)
        return results

    def get_kdata(self, stock_code, period='D', count=365):
        """返回空DataFrame"""
        return pd.DataFrame()

    def get_latest_price(self, stock_code):
        """返回模拟价格"""
        return 10.0  # 模拟价格

    def get_market_data(self, index_code, date=None):
        """返回模拟市场数据"""
        return {
            'date': date or datetime.now(),
            'index_code': index_code,
            'index_name': '模拟指数',
            'open': 3000.0,
            'high': 3100.0,
            'low': 2900.0,
            'close': 3050.0,
            'volume': 1000000.0,
            'amount': 3000000000.0,
            'change': 50.0,
            'change_pct': 1.67
        }

    def get_market_indices(self):
        """返回模拟指数列表"""
        return ['000001', '000300', '399001', '399006']


class MinimalDataManager:
    """
    最小化的数据管理器

    当FallbackDataManager也无法创建时的最后备用方案。
    """

    def get_stock_list(self, market=None):
        return []

    def get_stock_info(self, stock_code):
        return None

    def search_stocks(self, keyword):
        return []

    def get_kdata(self, stock_code, period='D', count=365):
        return pd.DataFrame()


class BaseRepository(ABC):
    """数据仓库基类"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def connect(self) -> bool:
        """连接数据源"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据源连接"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass


class StockRepository(BaseRepository):
    """股票信息仓库"""

    def __init__(self, data_manager=None):
        super().__init__()
        self.data_manager = data_manager
        self._stock_cache = {}

    def connect(self) -> bool:
        """连接数据源"""
        try:
            if self.data_manager is None:
                # 动态导入避免循环依赖
                from core.data_manager import DataManager
                self.data_manager = DataManager()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect stock repository: {e}")
            # 如果DataManager创建失败，创建一个简单的模拟数据管理器
            self._create_fallback_data_manager()
            return True

    def disconnect(self) -> None:
        """断开连接"""
        self._stock_cache.clear()

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.data_manager is not None

    def _create_fallback_data_manager(self) -> None:
        """创建备用数据管理器"""
        try:
            self.data_manager = FallbackDataManager()
            self.logger.info("Created fallback data manager")
        except Exception as e:
            self.logger.error(f"Failed to create fallback data manager: {e}")
            # 最后的备用方案
            self.data_manager = MinimalDataManager()

    def get_stock_info(self, stock_code: str) -> Optional[StockInfo]:
        """获取股票基本信息"""
        try:
            # 先检查缓存
            if stock_code in self._stock_cache:
                return self._stock_cache[stock_code]

            if not self.is_connected():
                self.connect()

            # 从数据管理器获取股票信息
            if hasattr(self.data_manager, 'get_stock_info'):
                stock_info_dict = self.data_manager.get_stock_info(stock_code)
            else:
                # 从股票列表中查找
                stock_list = self.data_manager.get_stock_list()
                stock_info_dict = None
                for stock in stock_list:
                    if stock.get('code') == stock_code:
                        stock_info_dict = stock
                        break

            if not stock_info_dict:
                return None

            # 转换为StockInfo对象
            stock_info = StockInfo(
                code=stock_info_dict.get('code', stock_code),
                name=stock_info_dict.get('name', ''),
                market=stock_info_dict.get('market', ''),
                industry=stock_info_dict.get('industry'),
                sector=stock_info_dict.get('sector'),
                list_date=stock_info_dict.get('list_date'),
                market_cap=stock_info_dict.get('market_cap'),
                pe_ratio=stock_info_dict.get('pe_ratio'),
                pb_ratio=stock_info_dict.get('pb_ratio')
            )

            # 缓存结果
            self._stock_cache[stock_code] = stock_info
            return stock_info

        except Exception as e:
            self.logger.error(
                f"Failed to get stock info for {stock_code}: {e}")
            return None

    def get_stock_list(self, market: Optional[str] = None) -> List[StockInfo]:
        """获取股票列表"""
        try:
            if not self.is_connected():
                self.connect()

            # 安全获取底层方法；若不存在则切换到备用数据管理器
            get_list_fn = getattr(self.data_manager, 'get_stock_list', None)
            if get_list_fn is None:
                self.logger.warning("DataManager缺少get_stock_list方法，切换到备用数据管理器")
                self._create_fallback_data_manager()
                get_list_fn = getattr(self.data_manager, 'get_stock_list', None)
                if get_list_fn is None:
                    self.logger.error("备用数据管理器仍缺少get_stock_list方法，返回空列表")
                    return []

            # 调用底层方法，兼容是否接受market参数
            try:
                raw_list = get_list_fn(market)
            except TypeError:
                # 方法可能不支持参数；获取全部后再过滤
                raw_all = get_list_fn()
                if market:
                    # 尝试在上层过滤（支持DataFrame或列表）
                    try:
                        import pandas as pd  # 局部导入以避免全局依赖
                        if isinstance(raw_all, pd.DataFrame):
                            raw_list = raw_all[raw_all['market'].str.lower() == str(market).lower()]
                        else:
                            raw_list = [s for s in raw_all if (
                                (hasattr(s, 'get') and str(s.get('market', '')).lower() == str(market).lower()) or
                                (hasattr(s, 'market') and str(getattr(s, 'market', '')).lower() == str(market).lower())
                            )]
                    except Exception:
                        raw_list = raw_all
                else:
                    raw_list = raw_all

            stock_list: List[StockInfo] = []

            # 统一不同返回类型到StockInfo
            try:
                if isinstance(raw_list, pd.DataFrame):
                    iter_items = raw_list.to_dict(orient='records')
                else:
                    iter_items = raw_list
            except Exception:
                iter_items = raw_list

            for item in (iter_items or []):
                try:
                    if isinstance(item, StockInfo):
                        stock_info = item
                    elif hasattr(item, 'get'):
                        stock_info = StockInfo(
                            code=item.get('code', '') or item.get('symbol', ''),
                            name=item.get('name', ''),
                            market=item.get('market', ''),
                            industry=item.get('industry'),
                            sector=item.get('sector')
                        )
                    elif hasattr(item, 'code'):
                        stock_info = StockInfo(
                            code=getattr(item, 'code', ''),
                            name=getattr(item, 'name', ''),
                            market=getattr(item, 'market', ''),
                            industry=getattr(item, 'industry', None),
                            sector=getattr(item, 'sector', None)
                        )
                    elif isinstance(item, str):
                        stock_info = StockInfo(
                            code=item,
                            name='',
                            market='',
                            industry=None,
                            sector=None
                        )
                    else:
                        self.logger.warning(f"跳过不支持的股票数据类型: {type(item)}")
                        continue

                    stock_list.append(stock_info)
                except Exception as inner_e:
                    self.logger.warning(f"跳过异常股票项: {inner_e}")
                    continue

            return stock_list

        except Exception as e:
            self.logger.error(f"Failed to get stock list: {e}")
            return []

    def search_stocks(self, keyword: str) -> List[StockInfo]:
        """搜索股票"""
        try:
            if not self.is_connected():
                self.connect()

            # 如果数据管理器支持搜索，直接使用
            if hasattr(self.data_manager, 'search_stocks'):
                search_results = self.data_manager.search_stocks(keyword)
            else:
                # 否则从股票列表中搜索
                all_stocks = self.data_manager.get_stock_list()
                keyword_lower = keyword.lower()
                search_results = []
                for stock in all_stocks:
                    # 安全地访问股票信息
                    code = ''
                    name = ''
                    if hasattr(stock, 'get'):
                        code = stock.get('code', '')
                        name = stock.get('name', '')
                    elif hasattr(stock, 'code'):
                        code = getattr(stock, 'code', '')
                        name = getattr(stock, 'name', '')
                    elif isinstance(stock, str):
                        code = stock

                    if (keyword_lower in code.lower() or keyword_lower in name.lower()):
                        search_results.append(stock)

            stock_list = []

            for stock_dict in search_results:
                # 确保stock_dict是字典类型或有get方法的对象
                if isinstance(stock_dict, str):
                    # 如果是字符串，可能是股票代码
                    stock_info = StockInfo(
                        code=stock_dict,
                        name='',
                        market='',
                        industry=None,
                        sector=None
                    )
                elif hasattr(stock_dict, 'get'):
                    # 字典或类字典对象
                    stock_info = StockInfo(
                        code=stock_dict.get('code', ''),
                        name=stock_dict.get('name', ''),
                        market=stock_dict.get('market', ''),
                        industry=stock_dict.get('industry'),
                        sector=stock_dict.get('sector')
                    )
                elif hasattr(stock_dict, 'code'):
                    # 对象属性访问
                    stock_info = StockInfo(
                        code=getattr(stock_dict, 'code', ''),
                        name=getattr(stock_dict, 'name', ''),
                        market=getattr(stock_dict, 'market', ''),
                        industry=getattr(stock_dict, 'industry', None),
                        sector=getattr(stock_dict, 'sector', None)
                    )
                else:
                    # 跳过无法处理的数据类型
                    self.logger.warning(
                        f"Skipping unsupported stock data type: {type(stock_dict)}")
                    continue

                stock_list.append(stock_info)

            return stock_list

        except Exception as e:
            self.logger.error(
                f"Failed to search stocks with keyword '{keyword}': {e}")
            return []


class KlineRepository(BaseRepository):
    """K线数据仓库（现代化TET模式）"""

    def __init__(self, asset_service=None):
        super().__init__()
        self.asset_service = asset_service
        self.data_manager = None  # 备用兼容
        self._cache = {}

    def connect(self) -> bool:
        """连接数据源（TET模式优先）"""
        try:
            if self.asset_service is None:
                # 首先尝试获取AssetService（TET模式）
                try:
                    from ..containers import get_service_container
                    from ..services import AssetService
                    container = get_service_container()
                    self.asset_service = container.resolve(AssetService)
                    self.logger.info("✅ KlineRepository使用TET模式（AssetService）")

                    # 即使TET模式成功，也要准备传统模式的备用
                    if self.data_manager is None:
                        try:
                            from core.data_manager import DataManager
                            self.data_manager = DataManager()
                            self.logger.debug("📊 KlineRepository同时准备传统模式DataManager作为备用")
                        except Exception as dm_e:
                            self.logger.warning(f"⚠️ 无法创建备用DataManager: {dm_e}")

                    return True
                except Exception as e:
                    self.logger.warning(f"⚠️ 无法获取AssetService，降级到传统模式: {e}")

            # 如果AssetService可用，优先使用
            if self.asset_service is not None:
                return True

            # 降级到传统DataManager
            if self.data_manager is None:
                try:
                    from core.data_manager import DataManager
                    self.data_manager = DataManager()
                    self.logger.info("📊 KlineRepository使用传统模式（DataManager）")
                except ImportError:
                    self.logger.error("❌ 无法导入DataManager类")
                    return False
                except Exception as dm_e:
                    self.logger.error(f"❌ 创建DataManager失败: {dm_e}")
                    # 如果都失败，创建备用数据管理器
                    self._create_fallback_data_manager()

            return True
        except Exception as e:
            self.logger.error(f"Failed to connect kline repository: {e}")
            # 如果都失败，创建备用数据管理器
            self._create_fallback_data_manager()
            return True

    def disconnect(self) -> None:
        """断开连接"""
        self._cache.clear()

    def is_connected(self) -> bool:
        """检查连接状态（TET模式优先）"""
        return self.asset_service is not None or self.data_manager is not None

    def _create_fallback_data_manager(self) -> None:
        """创建备用数据管理器"""
        try:
            self.data_manager = FallbackDataManager()
            self.logger.info(
                "Created fallback data manager for kline repository")
        except Exception as e:
            self.logger.error(f"Failed to create fallback data manager: {e}")
            self.data_manager = MinimalDataManager()

    def get_kline_data(self, params: QueryParams) -> Optional[KlineData]:
        """获取K线数据"""
        try:
            # 验证参数
            if not params.validate():
                self.logger.error(f"Invalid query params: {params}")
                return None

            # 生成缓存键
            cache_key = f"{params.stock_code}_{params.period}_{params.start_date}_{params.end_date}_{params.count}"

            # 检查缓存
            if cache_key in self._cache:
                return self._cache[cache_key]

            if not self.is_connected():
                self.connect()

            # 优先使用TET模式（AssetService）
            kline_df = None
            if self.asset_service is not None:
                try:
                    from ..plugin_types import AssetType
                    self.logger.info(f"🚀 KlineRepository使用TET模式获取数据: {params.stock_code}")

                    kline_df = self.asset_service.get_historical_data(
                        symbol=params.stock_code,
                        asset_type=AssetType.STOCK,
                        period=params.period
                    )

                    if kline_df is not None and not kline_df.empty:
                        self.logger.info(f"✅ TET模式获取成功: {params.stock_code} | 数据源: AssetService | 记录数: {len(kline_df)}")
                    else:
                        self.logger.warning(f"⚠️ TET模式返回空数据: {params.stock_code}")

                except Exception as e:
                    self.logger.warning(f"❌ TET模式获取失败: {params.stock_code} - {e}")
                    kline_df = None

            # 如果TET模式失败，降级到传统DataManager
            if kline_df is None or (hasattr(kline_df, 'empty') and kline_df.empty):
                self.logger.info(f"🔄 降级到传统模式: {params.stock_code}")

                # 兼容不同DataManager实现的命名：get_kdata 与 get_k_data
                dm_get_kdata = getattr(self.data_manager, 'get_kdata', None)
                if dm_get_kdata is None:
                    dm_get_kdata = getattr(self.data_manager, 'get_k_data', None)

                if dm_get_kdata is None:
                    self.logger.error("❌ DataManager缺少get_kdata/get_k_data方法，无法获取K线数据")
                    return None

                # 从数据管理器获取K线数据
                try:
                    # 优先使用count，若DataManager实现支持start/end也能兼容
                    kline_df = dm_get_kdata(
                        params.stock_code,
                        params.period,
                        params.count or 365
                    )
                    if kline_df is not None:
                        self.logger.info(f"✅ 传统模式获取成功: {params.stock_code} | 数据源: DataManager | 记录数: {len(kline_df)}")
                except TypeError:
                    # 某些实现可能要求命名参数
                    kline_df = dm_get_kdata(
                        stock_code=params.stock_code,
                        period=params.period,
                        count=params.count or 365
                    )
                    if kline_df is not None:
                        self.logger.info(f"✅ 传统模式获取成功: {params.stock_code} | 数据源: DataManager | 记录数: {len(kline_df)}")

            if kline_df is None or getattr(kline_df, 'empty', True):
                return None

            # 转换为KlineData对象
            kline_data = KlineData(
                stock_code=params.stock_code,
                period=params.period,
                data=kline_df,
                start_date=params.start_date,
                end_date=params.end_date,
                count=params.count
            )

            # 缓存结果
            self._cache[cache_key] = kline_data
            return kline_data

        except Exception as e:
            self.logger.error(f"Failed to get kline data: {e}")
            return None

    def get_latest_price(self, stock_code: str) -> Optional[float]:
        """获取最新价格"""
        try:
            if not self.is_connected():
                self.connect()

            # 获取最新一条K线数据
            params = QueryParams(stock_code=stock_code, period='D', count=1)
            kline_data = self.get_kline_data(params)

            if kline_data and not kline_data.data.empty:
                return float(kline_data.data.iloc[-1]['close'])

            return None

        except Exception as e:
            self.logger.error(
                f"Failed to get latest price for {stock_code}: {e}")
            return None


class MarketRepository(BaseRepository):
    """市场数据仓库"""

    def __init__(self, data_manager=None):
        super().__init__()
        self.data_manager = data_manager
        self._market_cache = {}

    def connect(self) -> bool:
        """连接数据源"""
        try:
            if self.data_manager is None:
                # ✅ 动态导入避免循环依赖
                from core.data_manager import DataManager
                self.data_manager = DataManager()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect market repository: {e}")
            # 如果DataManager创建失败，创建一个简单的模拟数据管理器
            self._create_fallback_data_manager()
            return True

    def disconnect(self) -> None:
        """断开连接"""
        self._market_cache.clear()

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.data_manager is not None

    def _create_fallback_data_manager(self) -> None:
        """创建备用数据管理器"""
        try:
            self.data_manager = FallbackDataManager()
            self.logger.info(
                "Created fallback data manager for market repository")
        except Exception as e:
            self.logger.error(f"Failed to create fallback data manager: {e}")
            self.data_manager = MinimalDataManager()

    def get_market_data(self, index_code: str, date: Optional[datetime] = None) -> Optional[MarketData]:
        """获取市场数据"""
        try:
            if not self.is_connected():
                self.connect()

            # 从数据管理器获取市场数据
            market_dict = self.data_manager.get_market_data(index_code, date)
            if not market_dict:
                return None

            # 转换为MarketData对象
            market_data = MarketData(
                date=market_dict.get('date', datetime.now()),
                index_code=market_dict.get('index_code', index_code),
                index_name=market_dict.get('index_name', ''),
                open=market_dict.get('open', 0.0),
                high=market_dict.get('high', 0.0),
                low=market_dict.get('low', 0.0),
                close=market_dict.get('close', 0.0),
                volume=market_dict.get('volume', 0.0),
                amount=market_dict.get('amount', 0.0),
                change=market_dict.get('change'),
                change_pct=market_dict.get('change_pct')
            )

            return market_data

        except Exception as e:
            self.logger.error(
                f"Failed to get market data for {index_code}: {e}")
            return None

    def get_market_indices(self) -> List[str]:
        """获取市场指数列表"""
        try:
            if not self.is_connected():
                self.connect()

            return self.data_manager.get_market_indices()

        except Exception as e:
            self.logger.error(f"Failed to get market indices: {e}")
            return []
