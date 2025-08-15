"""
HIkyuu数据源插件

将HIkyuu框架作为插件引入系统，提供本地股票数据访问功能。
支持动态加载，如果HIkyuu不可用，系统可以正常运行。
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from plugins.plugin_interface import IDataSourcePlugin, PluginMetadata, PluginType, PluginCategory
from core.tet.models import StandardQuery, StandardData, StockInfo, AssetType, DataType
from core.tet.exceptions import PluginUnavailableError, DataExtractionError

logger = logging.getLogger(__name__)


class HIkyuuDataPlugin(IDataSourcePlugin):
    """HIkyuu数据源插件实现"""

    def __init__(self):
        self.hikyuu_available = False
        self.sm = None
        self.Query = None
        self.Stock = None
        self._invalid_stocks_cache = set()
        self._valid_stocks_cache = set()

        # 尝试初始化HIkyuu
        self._initialize_hikyuu()

    @property
    def metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        return PluginMetadata(
            name="HIkyuu数据源插件",
            version="1.0.0",
            description="HIkyuu框架数据源插件，提供高性能的本地股票数据访问",
            author="FactorWeave Team",
            email="support@factorweave.com",
            website="https://github.com/factorweave/hikyuu-ui",
            license="MIT",
            plugin_type=PluginType.DATA_SOURCE,
            category=PluginCategory.CORE,
            dependencies=["hikyuu>=2.5.6"],
            min_hikyuu_version="2.0.0",
            max_hikyuu_version="3.0.0",
            tags=["data", "stock", "hikyuu", "local"]
        )

    def _initialize_hikyuu(self):
        """初始化HIkyuu框架"""
        try:
            # 动态导入HIkyuu模块
            import hikyuu as hku
            from hikyuu import StockManager, Query, Stock
            from hikyuu.interactive import sm

            # 初始化HIkyuu
            hku.init()

            self.sm = sm
            self.Query = Query
            self.Stock = Stock

            # 验证HIkyuu是否正常工作
            if self.sm is None:
                raise RuntimeError("HIkyuu StockManager not initialized")

            self.hikyuu_available = True
            logger.info("HIkyuu插件初始化成功")

        except ImportError as e:
            logger.warning(f"HIkyuu框架不可用: {e}")
            self.hikyuu_available = False
        except Exception as e:
            logger.error(f"HIkyuu插件初始化失败: {e}")
            self.hikyuu_available = False

    def initialize(self, context) -> bool:
        """插件初始化"""
        if not self.hikyuu_available:
            logger.warning("HIkyuu框架不可用，插件初始化失败")
            return False

        try:
            # 注册到TET数据路由器
            if hasattr(context, 'register_data_adapter'):
                context.register_data_adapter('hikyuu', self)

            # 注册支持的数据类型
            self._register_supported_types(context)

            logger.info("HIkyuu插件注册成功")
            return True

        except Exception as e:
            logger.error(f"HIkyuu插件注册失败: {e}")
            return False

    def _register_supported_types(self, context):
        """注册支持的数据类型"""
        supported_types = {
            AssetType.STOCK: [DataType.KDATA],
            AssetType.INDEX: [DataType.KDATA]
        }

        if hasattr(context, 'register_supported_types'):
            context.register_supported_types('hikyuu', supported_types)

    def cleanup(self) -> None:
        """清理插件资源"""
        try:
            self.sm = None
            self.Query = None
            self.Stock = None
            self._invalid_stocks_cache.clear()
            self._valid_stocks_cache.clear()
            self.hikyuu_available = False
            logger.info("HIkyuu插件资源已清理")
        except Exception as e:
            logger.error(f"HIkyuu插件清理失败: {e}")

    def supports(self, query: StandardQuery) -> bool:
        """检查是否支持指定查询"""
        if not self.hikyuu_available:
            return False

        # 检查资产类型
        if query.asset_type not in [AssetType.STOCK, AssetType.INDEX]:
            return False

        # 检查数据类型
        if query.data_type != DataType.KDATA:
            return False

        # 检查股票代码格式
        return self._is_valid_stock_code(query.symbol)

    async def extract(self, query: StandardQuery) -> StandardData:
        """提取数据"""
        if not self.hikyuu_available:
            raise PluginUnavailableError("HIkyuu插件不可用")

        if not self.supports(query):
            raise DataExtractionError(f"不支持的查询: {query}")

        try:
            # 获取K线数据
            df = await self._get_kdata(query)

            # 构建标准数据响应
            return StandardData(
                data=df,
                metadata={
                    'symbol': query.symbol,
                    'period': query.period,
                    'source': 'hikyuu',
                    'plugin_version': self.metadata.version
                },
                source='hikyuu',
                timestamp=datetime.now(),
                quality_score=0.95  # HIkyuu数据质量很高
            )

        except Exception as e:
            logger.error(f"HIkyuu数据提取失败: {query.symbol} - {e}")
            raise DataExtractionError(f"数据提取失败: {e}")

    async def _get_kdata(self, query: StandardQuery) -> pd.DataFrame:
        """获取K线数据"""
        symbol = query.symbol

        # 检查缓存，避免重复查询无效股票
        if symbol in self._invalid_stocks_cache:
            logger.debug(f"股票 {symbol} 在无效缓存中，跳过查询")
            return pd.DataFrame()

        try:
            # 获取股票对象
            stock = self.sm[symbol]
            if not stock.valid:
                logger.warning(f"股票 {symbol} 在HIkyuu中无效")
                self._invalid_stocks_cache.add(symbol)
                return pd.DataFrame()
            else:
                self._valid_stocks_cache.add(symbol)

            # 转换周期格式
            ktype = self._convert_period(query.period)

            # 创建查询对象
            if query.count:
                hikyuu_query = self.Query(-query.count, ktype=ktype)
            elif query.start_date and query.end_date:
                hikyuu_query = self.Query(query.start_date, query.end_date, ktype)
            else:
                # 默认获取最近365天的数据
                hikyuu_query = self.Query(-365, ktype=ktype)

            # 获取K线数据
            kdata = stock.get_kdata(hikyuu_query)
            if kdata is None or len(kdata) == 0:
                logger.warning(f"股票 {symbol} 没有K线数据")
                self._invalid_stocks_cache.add(symbol)
                return pd.DataFrame()

            # 转换为DataFrame
            df = self._convert_kdata_to_dataframe(kdata, symbol)

            logger.debug(f"成功获取 {symbol} 的 {len(df)} 条K线数据")
            return df

        except Exception as e:
            logger.error(f"获取K线数据失败: {symbol} - {e}")
            self._invalid_stocks_cache.add(symbol)
            return pd.DataFrame()

    def _convert_period(self, period: str):
        """转换周期格式"""
        period_map = {
            '1': self.Query.MIN,
            '5': self.Query.MIN5,
            '15': self.Query.MIN15,
            '30': self.Query.MIN30,
            '60': self.Query.MIN60,
            'D': self.Query.DAY,
            'W': self.Query.WEEK,
            'M': self.Query.MONTH
        }
        return period_map.get(period.upper(), self.Query.DAY)

    def _convert_kdata_to_dataframe(self, kdata, symbol: str) -> pd.DataFrame:
        """将HIkyuu K线数据转换为DataFrame"""
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
                    logger.warning(f"转换K线记录失败: {e}")
                    continue

            if not data_list:
                return pd.DataFrame()

            # 创建DataFrame
            df = pd.DataFrame(data_list)

            # 设置datetime为索引
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)

            # 添加股票代码
            df['symbol'] = symbol

            # 数据清洗
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.dropna(subset=['close'])

            # 按时间排序
            df = df.sort_index()

            # 计算价格变化
            if len(df) > 1:
                df['prev_close'] = df['close'].shift(1)
                df['change'] = df['close'] - df['prev_close']
                df['change_percent'] = (df['change'] / df['prev_close'] * 100).round(2)

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
            logger.error(f"转换K线数据为DataFrame失败: {e}")
            return pd.DataFrame()

    def _convert_hikyuu_datetime(self, dt) -> Optional[datetime]:
        """转换HIkyuu的Datetime对象为Python datetime"""
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
            logger.warning(f"转换日期时间失败 {dt}: {e}")
            return None

    def _is_valid_stock_code(self, stock_code: str) -> bool:
        """验证股票代码是否有效"""
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
        else:
            return False

    async def get_stock_list(self) -> List[StockInfo]:
        """获取股票列表"""
        if not self.hikyuu_available:
            raise PluginUnavailableError("HIkyuu插件不可用")

        try:
            logger.info("从HIkyuu加载股票列表...")

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
                    stock_info = StockInfo(
                        code=market_code,
                        name=stock.name,
                        market=stock.market,
                        industry=industry
                    )

                    stock_list.append(stock_info)
                    valid_count += 1

                except Exception as e:
                    logger.warning(f"处理股票失败 {getattr(stock, 'code', 'unknown')}: {e}")
                    continue

            logger.info(f"从HIkyuu加载了 {valid_count}/{total_count} 只有效股票")
            return stock_list

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise DataExtractionError(f"获取股票列表失败: {e}")

    async def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票信息"""
        if not self.hikyuu_available:
            raise PluginUnavailableError("HIkyuu插件不可用")

        try:
            # 检查缓存
            if symbol in self._invalid_stocks_cache:
                return None

            # 获取股票对象
            stock = self.sm[symbol]
            if not stock.valid:
                self._invalid_stocks_cache.add(symbol)
                return None
            else:
                self._valid_stocks_cache.add(symbol)

            # 构建股票信息
            stock_info = StockInfo(
                code=symbol,
                name=stock.name,
                market=stock.market,
                industry=getattr(stock, 'industry', None) or '其他'
            )

            return stock_info

        except Exception as e:
            logger.error(f"获取股票信息失败: {symbol} - {e}")
            self._invalid_stocks_cache.add(symbol)
            return None

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            'invalid_stocks': len(self._invalid_stocks_cache),
            'valid_stocks': len(self._valid_stocks_cache)
        }

    def clear_cache(self) -> None:
        """清理缓存"""
        self._invalid_stocks_cache.clear()
        self._valid_stocks_cache.clear()
        logger.info("HIkyuu插件缓存已清理")


# 插件注册
def create_plugin():
    """创建插件实例"""
    return HIkyuuDataPlugin()


# 插件元数据（用于插件市场）
PLUGIN_METADATA = {
    "name": "HIkyuu数据源插件",
    "version": "1.0.0",
    "description": "HIkyuu框架数据源插件，提供高性能的本地股票数据访问",
    "author": "FactorWeave Team",
    "plugin_type": "data_source",
    "category": "core",
    "dependencies": ["hikyuu>=2.5.6"],
    "tags": ["data", "stock", "hikyuu", "local"]
}
