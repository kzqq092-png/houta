"""
数据管理模块

提供数据加载、缓存和管理功能
"""

import pandas as pd
from typing import Dict, Any, Optional, List, Set
import hikyuu as hku
from hikyuu.interactive import *
from core.logger import LogManager
import traceback
from datetime import datetime
# import ptvsd


class DataManager:
    """数据管理器"""

    def __init__(self, log_manager: Optional[LogManager] = None):
        """初始化数据管理器

        Args:
            log_manager: 日志管理器实例，可选
        """
        self.log_manager = log_manager or LogManager()

        # 数据缓存
        self._data_cache = {}  # K线数据缓存
        self._cache_size = 1000  # 最大缓存条目数
        self._cache_ttl = 300  # 缓存有效期（秒）

        # 股票列表缓存
        self._stock_list_cache = []
        self._stock_list_timestamp = None
        self._stock_list_ttl = 3600  # 股票列表缓存有效期（秒）

        # 市场和行业数据缓存
        self._market_cache = {}  # 市场数据缓存
        self._industry_cache = {}  # 行业数据缓存
        self._market_stocks = {}  # 每个市场包含的股票
        self._industry_stocks = {}  # 每个行业包含的股票

        # 添加缓存统计
        self._cache_hits = 0
        self._cache_misses = 0
        self._last_cleanup = datetime.now()
        self._cleanup_interval = 3600  # 清理间隔（秒）

        try:
            # 初始化hikyuu
            self.log_manager.info("正在初始化hikyuu...")
            self.sm = hku.StockManager.instance()
            self.log_manager.info("hikyuu初始化完成")

            # 初始化行业管理器
            from core.industry_manager import IndustryManager
            self.industry_manager = IndustryManager(
                log_manager=self.log_manager)
            self.industry_manager.industry_updated.connect(
                self._on_industry_data_updated)
            self.log_manager.info("行业管理器初始化完成")

            # 初始化市场和行业数据
            self._init_market_industry_data()

            # 启动定期清理任务
            self._start_cleanup_timer()

        except Exception as e:
            self.log_manager.error(f"初始化失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def _start_cleanup_timer(self):
        """启动定期清理定时器"""
        try:
            from PyQt5.QtCore import QTimer
            self._cleanup_timer = QTimer()
            self._cleanup_timer.timeout.connect(self._cleanup_cache)
            self._cleanup_timer.start(self._cleanup_interval * 1000)
            self.log_manager.info("缓存清理定时器已启动")
        except Exception as e:
            self.log_manager.error(f"启动清理定时器失败: {str(e)}")

    def _cleanup_cache(self):
        """清理过期缓存"""
        try:
            now = datetime.now()

            # 清理K线数据缓存
            expired_keys = []
            for key, cache_item in self._data_cache.items():
                if (now - cache_item['timestamp']).total_seconds() > self._cache_ttl:
                    expired_keys.append(key)
            for key in expired_keys:
                del self._data_cache[key]

            # 如果缓存太大，删除最旧的条目
            if len(self._data_cache) > self._cache_size:
                sorted_items = sorted(self._data_cache.items(),
                                      key=lambda x: x[1]['timestamp'])
                num_to_remove = len(self._data_cache) - self._cache_size
                for key, _ in sorted_items[:num_to_remove]:
                    del self._data_cache[key]

            # 检查股票列表缓存是否过期
            if self._stock_list_timestamp:
                if (now - self._stock_list_timestamp).total_seconds() > self._stock_list_ttl:
                    self._stock_list_cache = []
                    self._stock_list_timestamp = None

            self.log_manager.info(f"缓存清理完成，当前缓存大小: {len(self._data_cache)}")

        except Exception as e:
            self.log_manager.error(f"清理缓存失败: {str(e)}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            缓存统计信息字典
        """
        try:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0

            return {
                'cache_size': len(self._data_cache),
                'max_cache_size': self._cache_size,
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses,
                'hit_rate': hit_rate,
                'last_cleanup': self._last_cleanup,
                'cleanup_interval': self._cleanup_interval
            }
        except Exception as e:
            self.log_manager.error(f"获取缓存统计失败: {str(e)}")
            return {}

    def _init_market_industry_data(self):
        """初始化市场和行业数据"""
        try:
            # 初始化市场映射
            self._market_cache = {
                'SH': {'name': '上海证券交易所', 'code': 'SH', 'prefix': ['600', '601', '603', '605', '688']},
                'SZ': {'name': '深圳证券交易所', 'code': 'SZ', 'prefix': ['000', '001', '002', '003', '300']},
                'BJ': {'name': '北京证券交易所', 'code': 'BJ', 'prefix': ['8', '430']},
                'HK': {'name': '港股通', 'code': 'HK', 'prefix': ['9']},
                'US': {'name': '美股', 'code': 'US', 'prefix': ['7']}
            }

            # 初始化市场和行业股票集合
            for market in self._market_cache:
                self._market_stocks[market] = set()

            # 遍历所有股票，更新市场和行业数据
            for stock in self.sm:
                try:
                    if not stock.valid:
                        continue

                    market = stock.market
                    code = stock.code

                    # 更新市场股票集合
                    if market in self._market_stocks:
                        self._market_stocks[market].add(code)

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
                                            if level not in self._industry_cache:
                                                self._industry_cache[level] = {
                                                    'sub_industries': set(), 'stocks': set()}
                                            self._industry_cache[level]['stocks'].add(
                                                code)
                                        elif i == 1:  # 子行业
                                            main_industry = industry_levels[0].strip(
                                            )
                                            if main_industry in self._industry_cache:
                                                self._industry_cache[main_industry]['sub_industries'].add(
                                                    level)
                                                if level not in self._industry_stocks:
                                                    self._industry_stocks[level] = set(
                                                    )
                                                self._industry_stocks[level].add(
                                                    code)
                    except Exception as e:
                        self.log_manager.warning(
                            f"获取股票 {code} 行业信息失败: {str(e)}")
                        continue

                except Exception as e:
                    self.log_manager.warning(f"处理股票数据失败: {code} - {str(e)}")
                    continue

            self.log_manager.info(
                f"市场和行业数据初始化完成: {len(self._market_cache)} 个市场, {len(self._industry_cache)} 个行业")

        except Exception as e:
            self.log_manager.error(f"初始化市场和行业数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def get_markets(self) -> Dict[str, Dict]:
        """获取所有市场数据

        Returns:
            市场数据字典
        """
        return self._market_cache.copy()

    def get_industries(self) -> Dict[str, Dict]:
        """获取所有行业数据

        Returns:
            行业数据字典
        """
        return self._industry_cache.copy()

    def get_market_stocks(self, market: str) -> Set[str]:
        """获取指定市场的所有股票

        Args:
            market: 市场代码

        Returns:
            股票代码集合
        """
        return self._market_stocks.get(market, set()).copy()

    def get_industry_stocks(self, industry: str) -> Set[str]:
        """获取指定行业的所有股票

        Args:
            industry: 行业名称

        Returns:
            股票代码集合
        """
        return self._industry_stocks.get(industry, set()).copy()

    def get_sub_industries(self, main_industry: str) -> Set[str]:
        """获取主行业的所有子行业

        Args:
            main_industry: 主行业名称

        Returns:
            子行业名称集合
        """
        industry_info = self._industry_cache.get(main_industry, {})
        return industry_info.get('sub_industries', set()).copy()

    def get_k_data(self, code: str, period: str = 'D') -> pd.DataFrame:
        """获取K线数据

        Args:
            code: 股票代码
            period: 周期，如 D=日线，W=周线，M=月线，m5=5分钟线，m15=15分钟线，m30=30分钟线，m60=60分钟线

        Returns:
            K线数据DataFrame
        """
        try:
            # 验证参数
            if not code:
                raise ValueError("股票代码不能为空")

            # 验证周期参数
            valid_periods = {'D', 'W', 'M', 'm5', 'm15', 'm30', 'm60'}
            if period not in valid_periods:
                raise ValueError(
                    f"不支持的周期类型: {period}，支持的周期类型: {', '.join(valid_periods)}")

            # 生成缓存键
            cache_key = f"{code}_{period}"

            # 检查缓存
            if cache_key in self._data_cache:
                cache_item = self._data_cache[cache_key]
                if (datetime.now() - cache_item['timestamp']).total_seconds() <= self._cache_ttl:
                    self._cache_hits += 1
                    return cache_item['data'].copy()  # 返回副本避免修改缓存
                else:
                    # 缓存过期，删除
                    del self._data_cache[cache_key]

            self._cache_misses += 1

            # 从hikyuu获取数据
            try:
                stock = self.sm[code]
                if not stock:
                    raise ValueError(f"无法获取股票: {code}")

                # 根据周期获取数据
                if period == 'D':
                    kdata = stock.getKData(hku.KQuery(-1000))  # 获取最近1000条日线数据
                elif period == 'W':
                    kdata = stock.getWeekKData(
                        hku.KQuery(-200))  # 获取最近200条周线数据
                elif period == 'M':
                    kdata = stock.getMonthKData(
                        hku.KQuery(-100))  # 获取最近100条月线数据
                elif period.startswith('m'):
                    minutes = int(period[1:])
                    kdata = stock.getMinKData(
                        minutes, hku.KQuery(-1000))  # 获取最近1000条分钟线数据
                else:
                    raise ValueError(f"不支持的周期类型: {period}")

                # 验证数据
                if not kdata or len(kdata) == 0:
                    self.log_manager.warning(f"股票 {code} 获取到的K线数据为空")
                    return pd.DataFrame()

                try:
                    # 获取各字段数据
                    date_list = kdata.getDatetimeList()
                    open_list = kdata.getOpenList()
                    high_list = kdata.getHighList()
                    low_list = kdata.getLowList()
                    close_list = kdata.getCloseList()
                    volume_list = kdata.getVolumeList()
                    amount_list = kdata.getAmountList()

                    # 检查所有字段长度一致且大于0
                    field_lengths = {
                        'date': len(date_list),
                        'open': len(open_list),
                        'high': len(high_list),
                        'low': len(low_list),
                        'close': len(close_list),
                        'volume': len(volume_list),
                        'amount': len(amount_list)
                    }

                    # 检查长度是否一致
                    lengths = list(field_lengths.values())
                    if len(set(lengths)) != 1:
                        self.log_manager.warning(
                            f"股票 {code} K线数据字段长度不一致: {field_lengths}"
                        )
                        return pd.DataFrame()

                    # 检查是否有数据
                    if lengths[0] == 0:
                        self.log_manager.warning(f"股票 {code} K线数据为空")
                        return pd.DataFrame()

                    # 转换为DataFrame
                    df = pd.DataFrame({
                        'date': date_list,
                        'open': open_list,
                        'high': high_list,
                        'low': low_list,
                        'close': close_list,
                        'volume': volume_list,
                        'amount': amount_list
                    })

                    # 验证数据类型
                    try:
                        # 设置日期索引
                        df.set_index('date', inplace=True)

                        # 验证数值列
                        numeric_cols = ['open', 'high', 'low',
                                        'close', 'volume', 'amount']
                        for col in numeric_cols:
                            df[col] = pd.to_numeric(df[col], errors='coerce')

                        # 检查是否有全为NaN的列
                        null_cols = df.columns[df.isnull().all()].tolist()
                        if null_cols:
                            self.log_manager.warning(
                                f"股票 {code} 以下列全为空值: {null_cols}"
                            )
                            return pd.DataFrame()

                        # 处理异常值
                        df = self._handle_data_anomalies(df)

                        # 更新缓存
                        if len(self._data_cache) >= self._cache_size:
                            # 删除最旧的缓存
                            oldest_key = min(self._data_cache.keys(),
                                             key=lambda k: self._data_cache[k]['timestamp'])
                            del self._data_cache[oldest_key]

                        self._data_cache[cache_key] = {
                            'data': df,
                            'timestamp': datetime.now()
                        }

                        return df.copy()  # 返回副本避免修改缓存

                    except Exception as e:
                        self.log_manager.error(
                            f"处理股票 {code} 数据类型转换失败: {str(e)}")
                        return pd.DataFrame()

                except Exception as e:
                    self.log_manager.error(f"获取股票 {code} K线数据字段失败: {str(e)}")
                    return pd.DataFrame()

            except Exception as e:
                self.log_manager.error(f"获取股票 {code} 数据失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
                return pd.DataFrame()

        except Exception as e:
            self.log_manager.error(f"获取K线数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return pd.DataFrame()

    def _handle_data_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理数据异常值

        Args:
            df: 原始数据DataFrame

        Returns:
            处理后的DataFrame
        """
        try:
            if df.empty:
                return df

            # 处理缺失值
            df = df.fillna(method='ffill')  # 用前值填充
            df = df.fillna(method='bfill')  # 用后值填充

            # 处理异常值
            for col in ['open', 'high', 'low', 'close']:
                # 计算3倍标准差范围
                mean = df[col].mean()
                std = df[col].std()
                lower_bound = mean - 3 * std
                upper_bound = mean + 3 * std

                # 将超出范围的值替换为边界值
                df.loc[df[col] < lower_bound, col] = lower_bound
                df.loc[df[col] > upper_bound, col] = upper_bound

            # 确保OHLC逻辑关系
            df['high'] = df[['high', 'open', 'close']].max(axis=1)
            df['low'] = df[['low', 'open', 'close']].min(axis=1)

            return df

        except Exception as e:
            self.log_manager.warning(f"处理数据异常值失败: {str(e)}")
            return df  # 如果处理失败，返回原始数据

    def get_stock_list(self) -> List[Dict[str, Any]]:
        """获取股票列表

        Returns:
            股票信息列表
        """
        try:
            # 检查缓存是否有效
            if self._stock_list_cache and self._stock_list_timestamp:
                if (datetime.now() - self._stock_list_timestamp).total_seconds() <= self._stock_list_ttl:
                    return self._stock_list_cache.copy()

            # 重新获取股票列表
            stock_list = []
            for stock in self.sm:
                try:
                    if not stock.valid:
                        continue

                    # 获取基本信息
                    info = {
                        'code': stock.code,
                        'name': stock.name,
                        'market': stock.market,
                        'marketCode': stock.market_code,
                        'type': stock.type,
                        'valid': stock.valid,
                        'start_date': str(stock.start_datetime) if stock.start_datetime else None,
                        'end_date': str(stock.last_datetime) if stock.last_datetime else None
                    }

                    # 获取行业信息
                    try:
                        industry_info = self.industry_manager.get_industry(
                            stock.code)
                        if industry_info:
                            info['industry'] = industry_info.get(
                                'csrc_industry', '') or industry_info.get('exchange_industry', '')
                    except Exception as e:
                        self.log_manager.warning(
                            f"获取股票 {stock.code} 行业信息失败: {str(e)}")
                        info['industry'] = ''

                    stock_list.append(info)

                except Exception as e:
                    self.log_manager.warning(
                        f"处理股票 {stock.code} 信息失败: {str(e)}")
                    continue

            # 更新缓存
            self._stock_list_cache = stock_list
            self._stock_list_timestamp = datetime.now()

            return stock_list.copy()

        except Exception as e:
            self.log_manager.error(f"获取股票列表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return []

    def clear_cache(self):
        """清除所有缓存"""
        try:
            self._data_cache.clear()
            self._stock_list_cache = []
            self._stock_list_timestamp = None
            self._cache_hits = 0
            self._cache_misses = 0
            self.log_manager.info("缓存已清除")
        except Exception as e:
            self.log_manager.error(f"清除缓存失败: {str(e)}")

    def get_stock_data(self, stock, query):
        """获取股票数据"""
        try:
            kdata = stock.get_kdata(query)
            if len(kdata) == 0:
                raise ValueError("无法获取股票数据")
            return kdata
        except Exception as e:
            self.log_manager.error(f"获取股票数据失败: {str(e)}")
            raise

    def get_sector_data(self, sector):
        """获取板块数据"""
        try:
            stocks = sector.get_stocks()
            if len(stocks) == 0:
                raise ValueError("无法获取板块数据")
            return stocks
        except Exception as e:
            self.log_manager.error(f"获取板块数据失败: {str(e)}")
            raise

    def filter_stock_list(self,
                          market: Optional[str] = None,
                          main_industry: Optional[str] = None,
                          sub_industry: Optional[str] = None,
                          keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """过滤股票列表

        Args:
            market: 市场，如 'SH', 'SZ' 等
            main_industry: 主行业
            sub_industry: 子行业
            keyword: 搜索关键词，可匹配代码或名称

        Returns:
            过滤后的股票列表
        """
        try:
            # 获取原始股票列表
            stock_list = self.get_stock_list()
            if not stock_list:
                return []

            # 应用过滤条件
            filtered_stocks = stock_list

            # 按市场过滤
            if market:
                market = market.upper()
                filtered_stocks = [
                    stock for stock in filtered_stocks
                    if stock['market'] == market
                ]

            # 按主行业过滤
            if main_industry:
                filtered_stocks = [
                    stock for stock in filtered_stocks
                    if stock['industry'] == main_industry
                ]

            # 按子行业过滤
            if sub_industry:
                filtered_stocks = [
                    stock for stock in filtered_stocks
                    if stock['industry'] == sub_industry
                ]

            # 按关键词过滤
            if keyword:
                keyword = keyword.lower()
                filtered_stocks = [
                    stock for stock in filtered_stocks
                    if (keyword in stock['code'].lower() or
                        keyword in stock['name'].lower() or
                        keyword in stock['industry'].lower())
                ]

            # 记录过滤结果
            self.log_manager.info(
                f"股票过滤完成: 市场={market}, 主行业={main_industry}, "
                f"子行业={sub_industry}, 关键词={keyword}, "
                f"结果数量={len(filtered_stocks)}"
            )

            return filtered_stocks

        except Exception as e:
            self.log_manager.error(f"过滤股票列表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return []

    def _on_industry_data_updated(self):
        """处理行业数据更新事件"""
        try:
            # 清除缓存
            self._stock_list_cache = []
            self._stock_list_timestamp = None
            self._industry_cache.clear()
            self._industry_stocks.clear()

            # 重新初始化市场和行业数据
            self._init_market_industry_data()

            self.log_manager.info("行业数据更新完成")

        except Exception as e:
            self.log_manager.error(f"处理行业数据更新失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
