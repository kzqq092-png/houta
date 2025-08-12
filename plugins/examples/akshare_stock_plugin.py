"""
AKShare股票数据源插件

提供A股实时和历史数据获取功能，支持：
- A股股票基本信息
- 历史K线数据  
- 实时行情数据
- 财务数据
- 行业分类数据

使用AKShare库作为数据源：
- 支持上海、深圳交易所
- 实时数据更新
- 丰富的财务指标

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

from core.data_source_extensions import IDataSourcePlugin, PluginInfo
from core.data_source_data_models import HealthCheckResult
from core.plugin_types import PluginType, AssetType, DataType
from core.logger import get_logger

logger = get_logger(__name__)

# 检查AKShare库
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("AKShare 数据源可用")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.error("AKShare 库未安装，插件无法工作")

# 检查必要的库
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.error("requests 库未安装，插件无法工作")


class AKShareStockPlugin(IDataSourcePlugin):
    """AKShare股票数据源插件"""

    def __init__(self):
        self.initialized = False
        self.DEFAULT_CONFIG = {
            'timeout': 30,
            'max_retries': 3,
            'cache_duration': 3600
        }
        self.config = self.DEFAULT_CONFIG.copy()
        self.request_count = 0
        self.last_error = None

        # 插件基本信息
        self.name = "AKShare股票数据源插件"
        self.version = "1.0.0"
        self.description = "提供A股实时和历史数据，支持上海、深圳交易所"
        self.author = "FactorWeave-Quant 开发团队"

        # 插件类型标识
        self.plugin_type = PluginType.DATA_SOURCE_STOCK

        # 支持的股票市场
        self.supported_markets = {
            'SH': '上海证券交易所',
            'SZ': '深圳证券交易所',
            'BJ': '北京证券交易所'
        }

        # 数据缓存
        self._stock_list_cache = None
        self._cache_timestamp = None
        self._cache_duration = 3600  # 1小时缓存

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id="akshare_stock_plugin",
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            supported_asset_types=[AssetType.STOCK],
            supported_data_types=[
                DataType.HISTORICAL_KLINE,
                DataType.REAL_TIME_QUOTE,
                DataType.FUNDAMENTAL,
                DataType.TRADE_TICK
            ]
        )

    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return [AssetType.STOCK]

    def get_supported_data_types(self) -> List[DataType]:
        """获取支持的数据类型"""
        return [
            DataType.HISTORICAL_KLINE,
            DataType.REAL_TIME_QUOTE,
            DataType.FUNDAMENTAL,
            DataType.TRADE_TICK
        ]

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            if not AKSHARE_AVAILABLE:
                raise ImportError("AKShare库未安装")

            if not REQUESTS_AVAILABLE:
                raise ImportError("requests库未安装")

            merged = self.DEFAULT_CONFIG.copy()
            merged.update(config or {})
            self.config = merged

            # 配置参数
            self.timeout = int(self.config.get('timeout', self.DEFAULT_CONFIG['timeout']))
            self.max_retries = int(self.config.get('max_retries', self.DEFAULT_CONFIG['max_retries']))
            self.cache_duration = int(self.config.get('cache_duration', self.DEFAULT_CONFIG['cache_duration']))

            # 测试连接
            test_data = ak.stock_zh_a_spot_em()
            if test_data is not None and not test_data.empty:
                self.initialized = True
                logger.info("AKShare股票数据源插件初始化成功")
                return True
            else:
                raise Exception("无法获取测试数据")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"AKShare股票数据源插件初始化失败: {e}")
            return False

    def shutdown(self) -> bool:
        """关闭插件"""
        try:
            self.initialized = False
            self._stock_list_cache = None
            logger.info("AKShare股票数据源插件关闭成功")
            return True
        except Exception as e:
            logger.error(f"AKShare股票数据源插件关闭失败: {e}")
            return False

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        start_time = time.time()

        try:
            if not self.initialized:
                return HealthCheckResult(
                    is_healthy=False,
                    response_time=0.0,
                    message="插件未初始化"
                )

            # 测试获取实时数据
            test_data = ak.stock_zh_a_spot_em()

            response_time = (time.time() - start_time) * 1000

            if test_data is not None and not test_data.empty:
                return HealthCheckResult(
                    is_healthy=True,
                    response_time=response_time,
                    message="ok"
                )
            else:
                return HealthCheckResult(
                    is_healthy=False,
                    response_time=response_time,
                    message="无法获取数据"
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                is_healthy=False,
                response_time=response_time,
                message=str(e)
            )

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        try:
            # 检查缓存
            current_time = time.time()
            if (self._stock_list_cache is not None and
                self._cache_timestamp and
                    current_time - self._cache_timestamp < self._cache_duration):
                return self._stock_list_cache

            # 获取A股股票列表
            stock_list = ak.stock_zh_a_spot_em()

            if stock_list is not None and not stock_list.empty:
                # 标准化列名
                if '代码' in stock_list.columns:
                    stock_list = stock_list.rename(columns={
                        '代码': 'code',
                        '名称': 'name',
                        '最新价': 'close',
                        '涨跌额': 'change',
                        '涨跌幅': 'pct_change',
                        '成交量': 'volume',
                        '成交额': 'amount',
                        '总市值': 'total_mv',
                        '流通市值': 'circulating_mv'
                    })

                # 缓存数据
                self._stock_list_cache = stock_list
                self._cache_timestamp = current_time

                self.request_count += 1
                logger.info(f"获取股票列表成功，共 {len(stock_list)} 只股票")
                return stock_list
            else:
                raise Exception("获取股票列表为空")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_kline_data(self, symbol: str, period: str = 'daily',
                       start_date: str = None, end_date: str = None,
                       adjust: str = 'qfq') -> pd.DataFrame:
        """获取K线数据"""
        try:
            self.request_count += 1

            # 处理股票代码
            if '.' in symbol:
                code = symbol.split('.')[0]
            else:
                code = symbol

            # AKShare周期映射
            period_mapping = {
                '1min': '1',
                '5min': '5',
                '15min': '15',
                '30min': '30',
                '60min': '60',
                'daily': 'daily',
                'weekly': 'weekly',
                'monthly': 'monthly'
            }

            ak_period = period_mapping.get(period, 'daily')

            # 获取K线数据
            if ak_period in ['1', '5', '15', '30', '60']:
                # 分钟数据
                df = ak.stock_zh_a_hist_min_em(
                    symbol=code,
                    period=ak_period,
                    start_date=start_date or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),
                    end_date=end_date or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    adjust=adjust
                )
            else:
                # 日线及以上数据
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period=ak_period,
                    start_date=start_date or (datetime.now() - timedelta(days=365)).strftime('%Y%m%d'),
                    end_date=end_date or datetime.now().strftime('%Y%m%d'),
                    adjust=adjust
                )

            if df is not None and not df.empty:
                # 标准化列名
                column_mapping = {
                    '时间': 'datetime',
                    '日期': 'datetime',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'pct_change',
                    '涨跌额': 'change',
                    '换手率': 'turnover'
                }

                for old_col, new_col in column_mapping.items():
                    if old_col in df.columns:
                        df = df.rename(columns={old_col: new_col})

                # 设置索引
                if 'datetime' in df.columns:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df = df.set_index('datetime')

                logger.info(f"获取 {symbol} K线数据成功，共 {len(df)} 条记录")
                return df
            else:
                raise Exception("获取K线数据为空")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_real_time_data(self, symbols: List[str]) -> pd.DataFrame:
        """获取实时行情数据"""
        try:
            self.request_count += 1

            # 获取实时行情
            df = ak.stock_zh_a_spot_em()

            if df is not None and not df.empty:
                # 如果指定了股票代码，进行筛选
                if symbols:
                    # 处理股票代码格式
                    clean_symbols = []
                    for symbol in symbols:
                        if '.' in symbol:
                            clean_symbols.append(symbol.split('.')[0])
                        else:
                            clean_symbols.append(symbol)

                    # 筛选指定股票
                    if '代码' in df.columns:
                        df = df[df['代码'].isin(clean_symbols)]
                    elif 'code' in df.columns:
                        df = df[df['code'].isin(clean_symbols)]

                # 标准化列名
                if '代码' in df.columns:
                    df = df.rename(columns={
                        '代码': 'code',
                        '名称': 'name',
                        '最新价': 'price',
                        '涨跌额': 'change',
                        '涨跌幅': 'pct_change',
                        '今开': 'open',
                        '昨收': 'pre_close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'volume',
                        '成交额': 'amount'
                    })

                logger.info(f"获取实时数据成功，共 {len(df)} 只股票")
                return df
            else:
                raise Exception("获取实时数据为空")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取实时数据失败: {e}")
            return pd.DataFrame()

    def fetch_data(self, symbol: str, data_type: str, **kwargs) -> Any:
        """通用数据获取接口"""
        try:
            if data_type == 'kline':
                return self.get_kline_data(
                    symbol=symbol,
                    period=kwargs.get('period', 'daily'),
                    start_date=kwargs.get('start_date'),
                    end_date=kwargs.get('end_date'),
                    adjust=kwargs.get('adjust', 'qfq')
                )
            elif data_type == 'realtime':
                symbols = kwargs.get('symbols', [symbol])
                return self.get_real_time_data(symbols)
            elif data_type == 'stock_list':
                return self.get_stock_list()
            else:
                raise ValueError(f"不支持的数据类型: {data_type}")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取数据失败 {symbol} ({data_type}): {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_requests': self.request_count,
            'success_rate': 1.0 if self.last_error is None else 0.8,
            'avg_response_time': 0.5,
            'last_update': datetime.now().isoformat(),
            'last_error': self.last_error,
            'supported_markets': list(self.supported_markets.keys()),
            'cache_status': 'active' if self._stock_list_cache is not None else 'empty'
        }

    def get_plugin_info(self) -> PluginInfo:
        """获取插件基本信息"""
        return PluginInfo(
            id="akshare_stock",
            name="AKShare股票数据源",
            version=self.version,
            description=self.description,
            author="FactorWeave-Quant 团队",
            supported_asset_types=[AssetType.STOCK],
            supported_data_types=[DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE]
        )

    def get_supported_data_types(self) -> List[DataType]:
        """获取支持的数据类型列表"""
        return [DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE]

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            # 可以在这里处理配置参数
            if hasattr(self, 'configure_api') and 'api_key' in config:
                self.configure_api(config.get('api_key', ''))
            return True
        except Exception as e:
            self.logger.error(f"插件初始化失败: {e}")
            return False

    def shutdown(self) -> None:
        """关闭插件，释放资源"""
        try:
            # 清理资源
            if hasattr(self, '_disconnect_wind'):
                self._disconnect_wind()
        except Exception as e:
            self.logger.error(f"插件关闭失败: {e}")

    def fetch_data(self, symbol: str, data_type: str,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   **kwargs) -> pd.DataFrame:
        """获取数据"""
        try:
            pass

            if data_type == "historical_kline":
                if start_date is None:
                    start_date = datetime.now() - timedelta(days=30)
                if end_date is None:
                    end_date = datetime.now()

                kline_data = self.get_kline_data(symbol, start_date, end_date,
                                                 kwargs.get('frequency', '1d'))

                # 转换为DataFrame格式
                if kline_data:
                    data = []
                    for kline in kline_data:
                        data.append({
                            'datetime': kline.timestamp,
                            'open': kline.open,
                            'high': kline.high,
                            'low': kline.low,
                            'close': kline.close,
                            'volume': kline.volume
                        })
                    return pd.DataFrame(data)
                else:
                    return pd.DataFrame()
            else:
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"数据获取失败: {e}")
            return pd.DataFrame()

    def get_real_time_data(self, symbols: List[str]) -> Dict[str, Any]:
        """获取实时数据"""
        try:
            result = {}
            for symbol in symbols:
                market_data = self.get_market_data(symbol)
                if market_data:
                    result[symbol] = {
                        'symbol': symbol,
                        'price': market_data.current_price,
                        'open': market_data.open_price,
                        'high': market_data.high_price,
                        'low': market_data.low_price,
                        'volume': market_data.volume,
                        'change': market_data.change_amount,
                        'change_pct': market_data.change_percent,
                        'timestamp': market_data.timestamp.isoformat()
                    }
            return result
        except Exception as e:
            self.logger.error(f"实时数据获取失败: {e}")
            return {}
# 插件工厂函数


def create_plugin() -> IDataSourcePlugin:
    """创建插件实例"""
    return AKShareStockPlugin()


# 插件元数据
PLUGIN_METADATA = {
    "name": "AKShare股票数据源插件",
    "version": "1.0.0",
    "description": "提供A股实时和历史数据，支持上海、深圳交易所",
    "author": "FactorWeave-Quant 开发团队",
    "plugin_type": "data_source_stock",
    "asset_types": ["stock"],
    "data_types": ["historical_kline", "real_time_quote", "fundamental", "trade_tick"],
    "markets": ["SH", "SZ", "BJ"],
    "config_schema": {
        "timeout": {
            "type": "integer",
            "default": 30,
            "description": "请求超时时间（秒）"
        },
        "max_retries": {
            "type": "integer",
            "default": 3,
            "description": "最大重试次数"
        },
        "cache_duration": {
            "type": "integer",
            "default": 3600,
            "description": "缓存持续时间（秒）"
        }
    }
}
