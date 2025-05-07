"""
数据管理模块

提供数据加载、缓存和管理功能
"""

import pandas as pd
from typing import Dict, Any, Optional, List, Set
import hikyuu as hku
from hikyuu.interactive import *
from core.base_logger import BaseLogManager
import traceback
from datetime import datetime, timedelta
from core.eastmoney_source import EastMoneyDataSource
from core.sina_source import SinaDataSource
from core.tonghuashun_source import TongHuaShunDataSource
from core.cache_manager import CacheManager
import numpy as np
# import ptvsd


class DataManager:
    """数据管理器"""

    def __init__(self, log_manager: Optional[BaseLogManager] = None):
        """初始化数据管理器

        Args:
            log_manager: 日志管理器实例，可选
        """
        try:
            self.log_manager = log_manager or BaseLogManager()

            # 初始化 StockManager
            try:
                from hikyuu.interactive import sm
                self.sm = sm
                self.log_manager.info("StockManager初始化成功")
            except Exception as e:
                self.log_manager.error(f"StockManager初始化失败: {str(e)}")
                self.sm = None

            # 初始化缓存管理器
            self.cache_manager = CacheManager(
                max_size=1000, default_ttl=300)  # 默认缓存5分钟

            # 初始化数据源
            self._data_sources = {}
            self._current_source = 'hikyuu'  # 默认使用 Hikyuu 数据源
            self._init_data_sources()

            # 初始化行业管理器
            from core.industry_manager import IndustryManager
            self.industry_manager = IndustryManager(
                log_manager=self.log_manager)
            self.industry_manager.industry_updated.connect(
                self._on_industry_data_updated)
            self.log_manager.info("行业管理器初始化完成")

            # 初始化市场和行业数据
            self._init_market_industry_data()

            self.log_manager.info("数据管理器初始化完成")

        except Exception as e:
            self.log_manager.error(f"初始化数据管理器失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def _init_market_industry_data(self):
        """初始化市场和行业数据"""
        try:
            # 初始化市场映射
            market_data = {
                'SH': {'name': '上海证券交易所', 'code': 'SH', 'prefix': ['600', '601', '603', '605', '688']},
                'SZ': {'name': '深圳证券交易所', 'code': 'SZ', 'prefix': ['000', '001', '002', '003', '300']},
                'BJ': {'name': '北京证券交易所', 'code': 'BJ', 'prefix': ['8', '430']},
                'HK': {'name': '港股通', 'code': 'HK', 'prefix': ['9']},
                'US': {'name': '美股', 'code': 'US', 'prefix': ['7']}
            }
            self.cache_manager.set('market_data', market_data)

            # 初始化市场和行业股票集合
            market_stocks = {}
            industry_stocks = {}
            industry_data = {}

            # 遍历所有股票，更新市场和行业数据
            for stock in sm:
                try:
                    if not stock.valid:
                        continue

                    market = stock.market
                    code = stock.code

                    # 更新市场股票集合
                    if market not in market_stocks:
                        market_stocks[market] = set()
                    market_stocks[market].add(code)

                    # 从行业管理器获取行业信息
                    try:
                        industry_info = self.industry_manager.get_industry(
                            code)
                        if industry_info:
                            industry = industry_info.get(
                                'csrc_industry', '') or industry_info.get('exchange_industry', '')
                            if industry:
                                # 处理多级行业
                                industry_levels = industry.split('/')
                                for i, level in enumerate(industry_levels):
                                    level = level.strip()
                                    if level:
                                        # 创建行业层级结构
                                        if i == 0:  # 主行业
                                            if level not in industry_data:
                                                industry_data[level] = {
                                                    'sub_industries': set(),
                                                    'stocks': set()
                                                }
                                            industry_data[level]['stocks'].add(
                                                code)
                                        elif i == 1:  # 子行业
                                            main_industry = industry_levels[0].strip(
                                            )
                                            if main_industry in industry_data:
                                                industry_data[main_industry]['sub_industries'].add(
                                                    level)
                                                if level not in industry_stocks:
                                                    industry_stocks[level] = set(
                                                    )
                                                industry_stocks[level].add(
                                                    code)
                    except Exception as e:
                        self.log_manager.warning(
                            f"获取股票 {code} 行业信息失败: {str(e)}")
                        continue

                except Exception as e:
                    self.log_manager.warning(f"处理股票数据失败: {code} - {str(e)}")
                    continue

            # 缓存市场和行业数据
            self.cache_manager.set('market_stocks', market_stocks)
            self.cache_manager.set('industry_stocks', industry_stocks)
            self.cache_manager.set('industry_data', industry_data)

            self.log_manager.info(
                f"市场和行业数据初始化完成: {len(market_data)} 个市场, {len(industry_data)} 个行业")

        except Exception as e:
            self.log_manager.error(f"初始化市场和行业数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def get_markets(self) -> Dict[str, Dict]:
        """获取所有市场数据

        Returns:
            市场数据字典
        """
        return self.cache_manager.get('market_data') or {}

    def get_industries(self) -> Dict[str, Dict]:
        """获取所有行业数据

        Returns:
            行业数据字典
        """
        return self.cache_manager.get('industry_data') or {}

    def get_market_stocks(self, market: str) -> Set[str]:
        """获取指定市场的所有股票

        Args:
            market: 市场代码

        Returns:
            股票代码集合
        """
        market_stocks = self.cache_manager.get('market_stocks') or {}
        return market_stocks.get(market, set()).copy()

    def get_industry_stocks(self, industry: str) -> Set[str]:
        """获取指定行业的所有股票

        Args:
            industry: 行业名称

        Returns:
            股票代码集合
        """
        industry_stocks = self.cache_manager.get('industry_stocks') or {}
        return industry_stocks.get(industry, set()).copy()

    def get_sub_industries(self, main_industry: str) -> Set[str]:
        """获取主行业的所有子行业

        Args:
            main_industry: 主行业名称

        Returns:
            子行业名称集合
        """
        industry_data = self.cache_manager.get('industry_data') or {}
        industry_info = industry_data.get(main_industry, {})
        return industry_info.get('sub_industries', set()).copy()

    def _convert_hikyuu_datetime(self, dt) -> str:
        """转换Hikyuu的Datetime对象为标准日期字符串

        Args:
            dt: Hikyuu的Datetime对象

        Returns:
            str: 标准日期字符串，格式：YYYY-MM-DD
        """
        try:
            if hasattr(dt, 'number'):
                n = int(dt.number)
                if n == 0:
                    return None
                s = str(n)
                return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
            elif isinstance(dt, (datetime, pd.Timestamp)):
                return dt.strftime('%Y-%m-%d')
            return str(dt)
        except Exception as e:
            self.log_manager.warning(f"转换日期失败: {str(e)}")
            return None

    def get_k_data(self, code: str, freq: str = 'D',
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   **kwargs) -> pd.DataFrame:
        """获取K线数据

        Args:
            code: 股票代码
            freq: K线周期 ('D':日线, 'W':周线, 'M':月线, '60':60分钟, '30':30分钟, '15':15分钟, '5':5分钟)
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            **kwargs: 其他参数

        Returns:
            pd.DataFrame: K线数据
        """
        try:
            # 检查股票代码格式
            if not code:
                self.log_manager.error("股票代码不能为空")
                return pd.DataFrame()

            # 标准化股票代码格式
            if not code.startswith(('sh', 'sz', 'bj')):
                if code.startswith('6'):
                    code = f'sh{code}'
                elif code.startswith(('0', '3')):
                    code = f'sz{code}'
                elif code.startswith('8'):
                    code = f'bj{code}'

            # 生成缓存键
            cache_key = f"kdata_{code}_{freq}_{start_date}_{end_date}"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                if not cached_data.empty:
                    return cached_data
                else:
                    self.log_manager.warning(f"缓存中的K线数据为空: {code}")

            # 根据当前数据源获取数据
            df = pd.DataFrame()

            try:
                if self._current_source == 'hikyuu':
                    stock = self.sm[code]
                    if not stock.valid:
                        self.log_manager.warning(f"股票 {code} 无效")
                        return pd.DataFrame()

                    # 转换周期格式
                    freq_map = {
                        'D': Query.DAY,
                        'W': Query.WEEK,
                        'M': Query.MONTH,
                        '60': Query.MIN60,
                        '30': Query.MIN30,
                        '15': Query.MIN15,
                        '5': Query.MIN5,
                        '1': Query.MIN
                    }
                    ktype = freq_map.get(freq, Query.DAY)

                    # 构建查询条件
                    if start_date and end_date:
                        query = Query(start_date, end_date, ktype)
                    elif start_date:
                        query = Query(
                            start_date, datetime.now().strftime('%Y-%m-%d'), ktype)
                    elif end_date:
                        query = Query(-9999, end_date, ktype)
                    else:
                        query = Query(-365, ktype=ktype)  # 默认获取一年数据

                    kdata = stock.get_kdata(query)
                    if kdata is None or len(kdata) == 0:
                        self.log_manager.warning(f"获取股票 {code} 的K线数据为空")
                        return pd.DataFrame()

                    # 转换Hikyuu的K线数据
                    dates = [self._convert_hikyuu_datetime(
                        k.datetime) for k in kdata]
                    df = pd.DataFrame({
                        'datetime': dates,
                        'open': [float(k.open) for k in kdata],
                        'high': [float(k.high) for k in kdata],
                        'low': [float(k.low) for k in kdata],
                        'close': [float(k.close) for k in kdata],
                        'volume': [float(k.volume) for k in kdata],
                        'amount': [float(k.amount) for k in kdata]
                    })

                    # 移除无效日期
                    df = df.dropna(subset=['datetime'])
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df.set_index('datetime', inplace=True)

                elif self._current_source == 'eastmoney':
                    df = self._data_sources['eastmoney'].get_kdata(
                        code, freq, start_date, end_date)

                elif self._current_source == 'sina':
                    df = self._data_sources['sina'].get_kdata(
                        code, freq, start_date, end_date)

                elif self._current_source == 'tonghuashun':
                    df = self._data_sources['tonghuashun'].get_kdata(
                        code, freq, start_date, end_date)

                # 验证数据完整性
                if df is None or df.empty:
                    self.log_manager.warning(f"获取股票 {code} 的K线数据为空")
                    return pd.DataFrame()

                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [
                    col for col in required_columns if col not in df.columns]
                if missing_columns:
                    self.log_manager.warning(
                        f"股票 {code} 的K线数据缺少必要列: {missing_columns}")
                    return pd.DataFrame()

                # 数据清洗
                df = df.replace([np.inf, -np.inf], np.nan)
                df = df.dropna(subset=['close'])  # 至少要有收盘价

                # 缓存数据
                self.cache_manager.set(cache_key, df)

                # 记录数据范围
                if not df.empty:
                    self.log_manager.info(
                        f"成功获取股票 {code} 的K线数据，"
                        f"时间范围: {df.index[0]} 至 {df.index[-1]}，"
                        f"共 {len(df)} 条记录"
                    )

                return df

            except Exception as source_error:
                self.log_manager.error(
                    f"从数据源 {self._current_source} 获取K线数据失败: {str(source_error)}")
                # 尝试切换到备用数据源
                for source in self.get_available_sources():
                    if source != self._current_source:
                        try:
                            self.log_manager.info(f"尝试使用备用数据源 {source}")
                            old_source = self._current_source
                            self._current_source = source
                            df = self.get_k_data(
                                code, freq, start_date, end_date)
                            if not df.empty:
                                return df
                            self._current_source = old_source
                        except:
                            continue
                return pd.DataFrame()

        except Exception as e:
            self.log_manager.error(f"获取K线数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return pd.DataFrame()

    def get_stock_list(self, market: str = 'all') -> pd.DataFrame:
        """获取股票列表

        Args:
            market: 市场类型 ('all', 'sh', 'sz', 'bj')

        Returns:
            pd.DataFrame: 股票列表数据
        """
        try:
            cache_key = f"stock_list_{market}"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                stocks = []
                for stock in sm:
                    if not stock.valid:
                        continue

                    # 根据market参数过滤
                    if market != 'all':
                        if market.lower() != stock.market.lower():
                            continue

                    # 获取行业信息
                    industry = getattr(stock, 'industry', None)
                    if not industry:
                        try:
                            industry_info = self.industry_manager.get_industry(
                                stock.code)
                            if industry_info:
                                industry = (industry_info.get('csrc_industry') or
                                            industry_info.get('exchange_industry') or
                                            industry_info.get('industry'))
                        except Exception as e:
                            self.log_manager.warning(
                                f"获取股票 {stock.code} 行业信息失败: {str(e)}")

                    stock_info = {
                        'code': stock.code,
                        'name': stock.name,
                        'market': stock.market,
                        'type': stock.type,
                        'valid': stock.valid,
                        'start_date': str(stock.start_datetime) if stock.start_datetime else None,
                        'end_date': str(stock.last_datetime) if stock.last_datetime else None,
                        'industry': industry or '其他'
                    }
                    stocks.append(stock_info)

                df = pd.DataFrame(stocks)

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_stock_list(market)
                # 补充行业信息
                if not df.empty and 'code' in df.columns:
                    df['industry'] = df.apply(
                        lambda x: self._get_industry(x['code']), axis=1)

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_stock_list(market)
                # 补充行业信息
                if not df.empty and 'code' in df.columns:
                    df['industry'] = df.apply(
                        lambda x: self._get_industry(x['code']), axis=1)

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_stock_list(market)
                # 补充行业信息
                if not df.empty and 'code' in df.columns:
                    df['industry'] = df.apply(
                        lambda x: self._get_industry(x['code']), axis=1)

            # 确保行业列存在
            if not df.empty and 'industry' not in df.columns:
                df['industry'] = '其他'

            # 缓存数据
            self.cache_manager.set(cache_key, df)

            return df

        except Exception as e:
            self.log_manager.error(f"获取股票列表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return pd.DataFrame()

    def _get_industry(self, code: str) -> str:
        """获取股票行业信息

        Args:
            code: 股票代码

        Returns:
            行业名称
        """
        try:
            industry_info = self.industry_manager.get_industry(code)
            if industry_info:
                return (industry_info.get('csrc_industry') or
                        industry_info.get('exchange_industry') or
                        industry_info.get('industry') or
                        '其他')
            return '其他'
        except Exception as e:
            self.log_manager.warning(f"获取股票 {code} 行业信息失败: {str(e)}")
            return '其他'

    def get_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情

        Args:
            codes: 股票代码列表

        Returns:
            pd.DataFrame: 实时行情数据
        """
        try:
            cache_key = f"realtime_{'_'.join(codes)}"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                quotes = [hku.Stock(code).get_realtime_quote()
                          for code in codes]
                df = pd.DataFrame(quotes)

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_realtime_quotes(codes)

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_realtime_quotes(codes)

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_realtime_quotes(
                    codes)

            # 缓存数据（实时行情缓存时间较短）
            self.cache_manager.set(cache_key, df, ttl=60)  # 60秒缓存

            return df

        except Exception as e:
            self.log_manager.error(f"获取实时行情失败: {str(e)}")
            return pd.DataFrame()

    def get_index_list(self) -> pd.DataFrame:
        """获取指数列表

        Returns:
            pd.DataFrame: 指数列表数据
        """
        try:
            cache_key = "index_list"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                indices = hku.get_index_list()
                df = pd.DataFrame({
                    'code': [i.code for i in indices],
                    'name': [i.name for i in indices]
                })

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_index_list()

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_index_list()

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_index_list()

            # 缓存数据
            self.cache_manager.set(cache_key, df)

            return df

        except Exception as e:
            self.log_manager.error(f"获取指数列表失败: {str(e)}")
            return pd.DataFrame()

    def get_industry_list(self) -> pd.DataFrame:
        """获取行业列表

        Returns:
            pd.DataFrame: 行业列表数据
        """
        try:
            cache_key = "industry_list"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                industries = hku.get_industry_list()
                df = pd.DataFrame({
                    'code': [i.code for i in industries],
                    'name': [i.name for i in industries]
                })

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_industry_list()

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_industry_list()

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_industry_list()

            # 缓存数据
            self.cache_manager.set(cache_key, df)

            return df

        except Exception as e:
            self.log_manager.error(f"获取行业列表失败: {str(e)}")
            return pd.DataFrame()

    def get_concept_list(self) -> pd.DataFrame:
        """获取概念列表

        Returns:
            pd.DataFrame: 概念列表数据
        """
        try:
            cache_key = "concept_list"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                concepts = hku.get_concept_list()
                df = pd.DataFrame({
                    'code': [c.code for c in concepts],
                    'name': [c.name for c in concepts]
                })

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_concept_list()

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_concept_list()

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_concept_list()

            # 缓存数据
            self.cache_manager.set(cache_key, df)

            return df

        except Exception as e:
            self.log_manager.error(f"获取概念列表失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_info(self, code: str) -> Dict[str, Any]:
        """获取股票基本信息

        Args:
            code: 股票代码

        Returns:
            Dict[str, Any]: 股票基本信息
        """
        try:
            cache_key = f"stock_info_{code}"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                stock = hku.Stock(code)
                info = {
                    'code': stock.code,
                    'name': stock.name,
                    'market': stock.market,
                    'type': stock.type,
                    'valid': stock.valid,
                    'start_date': stock.start_datetime,
                    'last_date': stock.last_datetime
                }

            elif self._current_source == 'eastmoney':
                info = self._data_sources['eastmoney'].get_stock_info(code)

            elif self._current_source == 'sina':
                info = self._data_sources['sina'].get_stock_info(code)

            elif self._current_source == 'tonghuashun':
                info = self._data_sources['tonghuashun'].get_stock_info(code)

            # 缓存数据
            self.cache_manager.set(cache_key, info)

            return info

        except Exception as e:
            self.log_manager.error(f"获取股票基本信息失败: {str(e)}")
            return {}

    def set_data_source(self, source: str) -> None:
        """设置数据源

        Args:
            source: 数据源名称 ("hikyuu", "eastmoney", "sina", "tonghuashun")
        """
        try:
            self.log_manager.info(f"设置数据源: {source}")

            # 清除缓存
            self.clear_cache()

            # 更新数据源
            self._current_source = source

            # 重新初始化数据源相关配置
            if source == "eastmoney":
                from .eastmoney_source import EastMoneyDataSource
                self._data_sources['eastmoney'] = EastMoneyDataSource()
            elif source == "sina":
                from .sina_source import SinaDataSource
                self._data_sources['sina'] = SinaDataSource()
            elif source == "tonghuashun":
                from .tonghuashun_source import TongHuaShunDataSource
                self._data_sources['tonghuashun'] = TongHuaShunDataSource()
            else:  # 默认使用 Hikyuu
                from data_source import HikyuuDataSource
                self._data_sources['hikyuu'] = HikyuuDataSource()

            # 初始化数据源
            self._data_sources[source].init()

            self.log_manager.info(f"数据源设置完成: {source}")

        except Exception as e:
            error_msg = f"设置数据源失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            raise

    def clear_cache(self) -> None:
        """清除所有缓存数据"""
        try:
            self.cache_manager.clear()
            self.log_manager.info("缓存已清除")
        except Exception as e:
            error_msg = f"清除缓存失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            raise

    def get_current_source(self) -> str:
        """获取当前数据源类型"""
        return self._current_source

    def get_available_sources(self) -> List[str]:
        """获取所有可用的数据源类型"""
        try:
            # 检查每个数据源是否可用
            available_sources = []
            for source_type, source in self._data_sources.items():
                try:
                    if source_type == 'hikyuu':
                        if source is not None:
                            test_data = source.Stock(
                                'sh000001').get_kdata(Query(-1))
                            if test_data is not None:
                                available_sources.append(source_type)
                    else:
                        if source is not None:
                            test_data = source.get_stock_list()
                            if test_data is not None:
                                available_sources.append(source_type)
                except:
                    continue
            return available_sources
        except Exception as e:
            self.log_manager.error(f"获取可用数据源失败: {str(e)}")
            return list(self._data_sources.keys())

    def _on_industry_data_updated(self):
        """处理行业数据更新事件"""
        try:
            # 清除缓存
            self.cache_manager.clear()

            # 重新初始化市场和行业数据
            self._init_market_industry_data()

            self.log_manager.info("行业数据更新完成")

        except Exception as e:
            self.log_manager.error(f"处理行业数据更新失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _init_data_sources(self) -> None:
        """初始化所有数据源"""
        try:
            # 初始化 Hikyuu 数据源
            try:
                from data_source import HikyuuDataSource
                self._data_sources['hikyuu'] = HikyuuDataSource()
                self.log_manager.info("Hikyuu数据源初始化成功")
            except Exception as e:
                self.log_manager.warning(f"Hikyuu数据源初始化失败: {str(e)}")

            # 初始化东方财富数据源
            try:
                from .eastmoney_source import EastMoneyDataSource
                self._data_sources['eastmoney'] = EastMoneyDataSource()
                self.log_manager.info("东方财富数据源初始化成功")
            except Exception as e:
                self.log_manager.warning(f"东方财富数据源初始化失败: {str(e)}")

            # 初始化新浪数据源
            try:
                from .sina_source import SinaDataSource
                self._data_sources['sina'] = SinaDataSource()
                self.log_manager.info("新浪数据源初始化成功")
            except Exception as e:
                self.log_manager.warning(f"新浪数据源初始化失败: {str(e)}")

            # 初始化同花顺数据源
            try:
                from .tonghuashun_source import TongHuaShunDataSource
                self._data_sources['tonghuashun'] = TongHuaShunDataSource()
                self.log_manager.info("同花顺数据源初始化成功")
            except Exception as e:
                self.log_manager.warning(f"同花顺数据源初始化失败: {str(e)}")

        except Exception as e:
            self.log_manager.error(f"初始化数据源失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _test_data_source(self, source_name: str) -> bool:
        """测试数据源是否可用

        Args:
            source_name: 数据源名称

        Returns:
            bool: 数据源是否可用
        """
        try:
            source = self._data_sources.get(source_name)
            if not source:
                return False

            # 尝试获取上证指数数据
            if source_name == 'hikyuu':
                test_data = source.Stock('sh000001').get_kdata(Query(-1))
                return test_data is not None and not test_data.empty
            else:
                test_data = source.get_kdata('sh000001', 'D')
                return test_data is not None and not test_data.empty

        except Exception as e:
            self.log_manager.warning(f"测试数据源 {source_name} 失败: {str(e)}")
            return False

    def _get_backup_source(self) -> Optional[str]:
        """获取备用数据源

        Returns:
            str: 备用数据源名称，如果没有可用的备用数据源则返回 None
        """
        try:
            # 按优先级尝试不同的数据源
            priority_list = ['hikyuu', 'eastmoney', 'sina', 'tonghuashun']
            for source_name in priority_list:
                if source_name != self._current_source and self._test_data_source(source_name):
                    return source_name
            return None

        except Exception as e:
            self.log_manager.error(f"获取备用数据源失败: {str(e)}")
            return None
