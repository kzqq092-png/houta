"""
HIkyuu数据管理器

使用真正的HIkyuu框架获取股票数据，替换模拟数据管理器。
实现与MockDataManager相同的接口，确保与现有架构兼容。
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HikyuuDataManager:
    """HIkyuu数据管理器 - 使用真正的HIkyuu框架获取数据"""

    def __init__(self):
        """初始化HIkyuu数据管理器"""
        try:
            # 导入hikyuu模块
            from hikyuu import StockManager, Query
            from hikyuu.interactive import sm

            self.sm = sm  # 使用全局StockManager实例
            self.StockManager = StockManager
            self.Query = Query

            # 验证hikyuu是否正常工作
            if self.sm is None:
                raise RuntimeError("HIkyuu StockManager not initialized")

            # 缓存无效股票代码，避免重复查询
            self._invalid_stocks_cache = set()
            self._valid_stocks_cache = set()

            logger.info("HIkyuu data manager initialized successfully")

        except ImportError as e:
            logger.error(f"Failed to import HIkyuu: {e}")
            raise RuntimeError("HIkyuu framework not available")
        except Exception as e:
            logger.error(f"Failed to initialize HIkyuu data manager: {e}")
            raise

    def initialize(self) -> None:
        """
        初始化方法（兼容性方法）

        这个方法主要是为了与其他服务的初始化模式保持一致
        实际的初始化工作已经在__init__中完成
        """
        # 验证HIkyuu是否正常工作
        if not self.test_connection():
            raise RuntimeError("HIkyuu connection test failed")

        logger.info("HIkyuu data manager initialization verified")

    def get_stock_list(self) -> List[Dict[str, Any]]:
        """
        获取股票列表

        Returns:
            股票信息列表，格式与MockDataManager兼容
        """
        try:
            logger.info("Loading stock list from HIkyuu...")

            stock_list = []
            total_count = 0
            valid_count = 0

            # 遍历所有股票
            for stock in self.sm:
                total_count += 1

                try:
                    # 只处理有效股票
                    if not stock.valid:
                        continue

                    # 构建股票代码（市场+代码）
                    market_code = f"{stock.market.lower()}{stock.code}"

                    # 获取行业信息
                    industry = getattr(stock, 'industry', None) or '其他'

                    # 构建股票信息
                    stock_info = {
                        'code': market_code,
                        'name': stock.name,
                        'market': stock.market,
                        'industry': industry,
                        'type': stock.type,
                        'valid': stock.valid,
                        'start_date': str(stock.start_datetime) if stock.start_datetime else None,
                        'end_date': str(stock.last_datetime) if stock.last_datetime else None
                    }

                    stock_list.append(stock_info)
                    valid_count += 1

                except Exception as e:
                    logger.warning(
                        f"Failed to process stock {getattr(stock, 'code', 'unknown')}: {e}")
                    continue

            logger.info(
                f"Loaded {valid_count} valid stocks out of {total_count} total stocks")
            return stock_list

        except Exception as e:
            logger.error(f"Failed to get stock list: {e}")
            return []

    def get_kdata(self, stock_code: str, period: str = 'D', count: int = 365) -> pd.DataFrame:
        """
        获取K线数据

        Args:
            stock_code: 股票代码
            period: 周期 (D/W/M)
            count: 数据条数

        Returns:
            K线数据DataFrame
        """
        try:
            logger.debug(
                f"Getting K-data for {stock_code}, period={period}, count={count}")

            # 检查缓存，避免重复查询无效股票
            if stock_code in self._invalid_stocks_cache:
                logger.debug(
                    f"Stock {stock_code} is in invalid cache, skipping")
                return pd.DataFrame()

            # 获取股票对象
            try:
                stock = self.sm[stock_code]
                if not stock.valid:
                    logger.warning(
                        f"Stock {stock_code} is not valid in HIkyuu data")
                    self._invalid_stocks_cache.add(stock_code)
                    return pd.DataFrame()
                else:
                    # 添加到有效股票缓存
                    self._valid_stocks_cache.add(stock_code)
            except Exception as e:
                logger.warning(
                    f"Stock {stock_code} not found in HIkyuu data: {e}")
                self._invalid_stocks_cache.add(stock_code)
                return pd.DataFrame()

            # 转换周期格式
            ktype = self._convert_period(period)

            # 创建查询对象
            query = self.Query(-count, ktype=ktype)

            # 获取K线数据
            try:
                kdata = stock.get_kdata(query)
                if kdata is None or len(kdata) == 0:
                    logger.warning(
                        f"No K-data available for {stock_code} (period={period}, count={count})")
                    # 将无数据的股票加入缓存
                    self._invalid_stocks_cache.add(stock_code)
                    return pd.DataFrame()
            except Exception as e:
                logger.error(f"Failed to get K-data for {stock_code}: {e}")
                # 将查询失败的股票加入缓存
                self._invalid_stocks_cache.add(stock_code)
                return pd.DataFrame()

            # 转换为DataFrame
            df = self._convert_kdata_to_dataframe(kdata, stock_code)

            logger.debug(
                f"Successfully loaded {len(df)} K-data records for {stock_code}")
            return df

        except Exception as e:
            logger.error(f"Failed to get K-data for {stock_code}: {e}")
            return pd.DataFrame()

    def get_historical_data(self, symbol: str, asset_type: str = 'stock', period: str = 'D', count: int = 365, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取历史数据 - TET模式兼容接口

        Args:
            symbol: 股票代码
            asset_type: 资产类型 (默认为'stock')，可以是字符串或AssetType枚举
            period: 周期 (D/W/M)
            count: 数据条数
            **kwargs: 其他参数

        Returns:
            历史数据DataFrame，如果获取失败返回None
        """
        try:
            logger.debug(f"TET模式获取历史数据: {symbol}, 资产类型={asset_type}, 周期={period}, 数量={count}")

            # 处理AssetType枚举
            asset_type_str = asset_type
            if hasattr(asset_type, 'value'):  # 是枚举类型
                asset_type_str = asset_type.value
            elif hasattr(asset_type, 'name'):  # 是枚举类型的另一种形式
                asset_type_str = asset_type.name.lower()

            # 目前只支持股票类型
            if asset_type_str not in ['stock', 'equity']:
                logger.warning(f"不支持的资产类型: {asset_type_str}")
                return None

            # 标准化股票代码
            normalized_symbol = self._normalize_stock_code(symbol)

            # 调用现有的get_kdata方法
            df = self.get_kdata(normalized_symbol, period, count)

            if df is not None and not df.empty:
                logger.debug(f"✅ TET模式获取成功: {symbol} -> {normalized_symbol} | 记录数: {len(df)}")
                return df
            else:
                logger.warning(f"⚠️ TET模式获取空数据: {symbol} -> {normalized_symbol}")
                return None

        except Exception as e:
            logger.error(f"❌ TET模式获取历史数据失败: {symbol} - {e}")
            return None

    def get_k_data(self, stock_code: str, period: str = 'D', count: int = 365) -> pd.DataFrame:
        """
        获取K线数据的别名方法 - 兼容不同的命名规范

        Args:
            stock_code: 股票代码
            period: 周期 (D/W/M)
            count: 数据条数

        Returns:
            K线数据DataFrame
        """
        return self.get_kdata(stock_code, period, count)

    def _normalize_stock_code(self, stock_code: str) -> str:
        """
        标准化股票代码格式

        Args:
            stock_code: 原始股票代码

        Returns:
            标准化后的股票代码
        """
        if not stock_code:
            return stock_code

        # 移除市场前缀（如果存在）
        code = stock_code.lower()
        if code.startswith(('sh', 'sz', 'bj')):
            return stock_code

        # 根据代码前缀添加市场标识
        if stock_code.startswith('6'):
            return f"sh{stock_code}"
        elif stock_code.startswith(('0', '3')):
            return f"sz{stock_code}"
        elif stock_code.startswith('8'):
            return f"bj{stock_code}"
        else:
            # 默认深圳市场
            return f"sz{stock_code}"

    def _is_valid_stock_code(self, stock_code: str) -> bool:
        """
        验证股票代码是否有效

        Args:
            stock_code: 股票代码

        Returns:
            是否有效
        """
        if not stock_code or len(stock_code) < 6:
            return False

        # 移除市场前缀
        code = stock_code.lower()
        if code.startswith(('sh', 'sz', 'bj')):
            pure_code = code[2:]
        else:
            pure_code = code

        # 检查是否为6位数字
        if not pure_code.isdigit() or len(pure_code) != 6:
            return False

        # 检查是否为有效的股票代码格式
        if pure_code.startswith('6'):  # 上海主板
            return True
        elif pure_code.startswith('00'):  # 深圳主板
            return True
        elif pure_code.startswith('30'):  # 创业板
            return True
        elif pure_code.startswith('68'):  # 科创板
            return True
        elif pure_code.startswith('8'):  # 北交所
            return True
        elif pure_code.startswith('43'):  # 新三板
            return True
        # 港股通（排除98开头的无效代码）
        elif pure_code.startswith('9') and not pure_code.startswith('98'):
            return True
        else:
            # 其他格式都是无效的
            return False

    def _convert_period(self, period: str):
        """
        转换周期格式

        Args:
            period: 周期字符串

        Returns:
            HIkyuu Query类型
        """
        period_map = {
            'D': self.Query.DAY,
            'W': self.Query.WEEK,
            'M': self.Query.MONTH,
            '60': self.Query.MIN60,
            '30': self.Query.MIN30,
            '15': self.Query.MIN15,
            '5': self.Query.MIN5,
            '1': self.Query.MIN
        }
        return period_map.get(period.upper(), self.Query.DAY)

    def _convert_kdata_to_dataframe(self, kdata, stock_code: str) -> pd.DataFrame:
        """
        将HIkyuu K线数据转换为DataFrame

        Args:
            kdata: HIkyuu K线数据
            stock_code: 股票代码

        Returns:
            标准格式的DataFrame
        """
        try:
            if not kdata or len(kdata) == 0:
                return pd.DataFrame()

            # 提取数据
            data_list = []
            for k in kdata:
                try:
                    # 转换日期
                    dt = self._convert_hikyuu_datetime(k.datetime)
                    if dt is None:
                        continue

                    # 构建数据行
                    data_row = {
                        'datetime': dt,
                        'open': float(k.open),
                        'high': float(k.high),
                        'low': float(k.low),
                        'close': float(k.close),
                        'volume': float(k.volume),
                        'amount': float(getattr(k, 'amount', 0))
                    }
                    data_list.append(data_row)

                except Exception as e:
                    logger.warning(f"Failed to convert K-data record: {e}")
                    continue

            if not data_list:
                return pd.DataFrame()

            # 创建DataFrame
            df = pd.DataFrame(data_list)

            # 设置datetime为索引
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)

            # 添加股票代码
            df['code'] = stock_code

            # 数据清洗
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.dropna(subset=['close'])

            # 按时间排序
            df = df.sort_index()

            # 生成模拟的价格变化数据（用于显示涨跌）
            if len(df) > 1:
                df['prev_close'] = df['close'].shift(1)
                df['change'] = df['close'] - df['prev_close']
                df['change_percent'] = (
                    df['change'] / df['prev_close'] * 100).round(2)

                # 填充第一行数据
                df.loc[df.index[0], 'prev_close'] = df.loc[df.index[0], 'close']
                df.loc[df.index[0], 'change'] = 0
                df.loc[df.index[0], 'change_percent'] = 0
            else:
                df['prev_close'] = df['close']
                df['change'] = 0
                df['change_percent'] = 0

            return df

        except Exception as e:
            logger.error(f"Failed to convert K-data to DataFrame: {e}")
            return pd.DataFrame()

    def _convert_hikyuu_datetime(self, dt) -> Optional[datetime]:
        """
        转换HIkyuu的Datetime对象为Python datetime

        Args:
            dt: HIkyuu Datetime对象

        Returns:
            Python datetime对象
        """
        try:
            if hasattr(dt, 'number'):
                n = int(dt.number)
                if n == 0:
                    return None
                s = str(n)
                if len(s) >= 8:
                    year = int(s[:4])
                    month = int(s[4:6])
                    day = int(s[6:8])
                    return datetime(year, month, day)
            elif isinstance(dt, (datetime, pd.Timestamp)):
                return dt
            else:
                # 尝试字符串解析
                return pd.to_datetime(str(dt))
        except Exception as e:
            logger.warning(f"Failed to convert datetime {dt}: {e}")
            return None

    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票信息

        Args:
            stock_code: 股票代码

        Returns:
            股票信息字典
        """
        try:
            logger.debug(f"Getting stock info for {stock_code}")

            # 检查缓存，避免重复查询无效股票
            if stock_code in self._invalid_stocks_cache:
                logger.debug(
                    f"Stock {stock_code} is in invalid cache, skipping")
                return None

            # 获取股票对象
            try:
                stock = self.sm[stock_code]
                if not stock.valid:
                    logger.warning(
                        f"Stock {stock_code} is not valid in HIkyuu data")
                    self._invalid_stocks_cache.add(stock_code)
                    return None
                else:
                    # 添加到有效股票缓存
                    self._valid_stocks_cache.add(stock_code)
            except Exception as e:
                logger.warning(
                    f"Stock {stock_code} not found in HIkyuu data: {e}")
                self._invalid_stocks_cache.add(stock_code)
                return None

            # 获取行业信息
            industry = getattr(stock, 'industry', None) or '其他'

            # 构建股票信息
            stock_info = {
                'code': stock_code,
                'name': stock.name,
                'market': stock.market,
                'industry': industry,
                'type': stock.type,
                'valid': stock.valid,
                'start_date': str(stock.start_datetime) if stock.start_datetime else None,
                'end_date': str(stock.last_datetime) if stock.last_datetime else None
            }

            logger.debug(
                f"Successfully got stock info for {stock_code}: {stock.name}")
            return stock_info

        except Exception as e:
            logger.error(f"Failed to get stock info for {stock_code}: {e}")
            return None

    def get_latest_price(self, stock_code: str) -> Optional[float]:
        """
        获取最新价格

        Args:
            stock_code: 股票代码

        Returns:
            最新价格
        """
        try:
            # 获取最近一天的数据
            df = self.get_kdata(stock_code, 'D', 1)
            if not df.empty:
                return float(df['close'].iloc[-1])
            return None
        except Exception as e:
            logger.error(f"Failed to get latest price for {stock_code}: {e}")
            return None

    def test_connection(self) -> bool:
        """
        测试数据连接是否正常

        Returns:
            连接是否正常
        """
        try:
            # 尝试获取上证指数数据
            df = self.get_kdata('sh000001', 'D', 1)
            return not df.empty
        except Exception as e:
            logger.error(f"Data connection test failed: {e}")
            return False

    def clear_cache(self) -> None:
        """清理股票缓存"""
        try:
            self._invalid_stocks_cache.clear()
            self._valid_stocks_cache.clear()
            logger.info("Stock cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        try:
            return {
                'invalid_stocks': len(self._invalid_stocks_cache),
                'valid_stocks': len(self._valid_stocks_cache)
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'invalid_stocks': 0, 'valid_stocks': 0}
