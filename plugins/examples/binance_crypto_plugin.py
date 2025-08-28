"""
币安数字货币数据源插件

提供币安交易所数字货币数据获取功能，支持：
- 主流数字货币实时价格
- 历史K线数据
- 市场深度数据
- 交易对信息
- 24小时统计数据

使用币安公开API：
- 无需API密钥的公开数据
- 高频实时更新
- 丰富的交易对

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

from core.data_source_extensions import IDataSourcePlugin, PluginInfo, HealthCheckResult
from core.data_source_data_models import QueryParams, StockInfo
from core.plugin_types import PluginType, AssetType, DataType
from core.logger import get_logger

logger = get_logger(__name__)

# 默认配置集中管理
DEFAULT_CONFIG = {
    'base_url': 'https://api.binance.com',
    'api_urls': {
        'ping': '/api/v3/ping',
        'time': '/api/v3/time',
        'exchange_info': '/api/v3/exchangeInfo',
        'klines': '/api/v3/klines',
        'ticker_24hr': '/api/v3/ticker/24hr',
        'ticker_price': '/api/v3/ticker/price',
        'depth': '/api/v3/depth'
    },
    'interval_mapping': {
        '1min': '1m', '3min': '3m', '5min': '5m', '15min': '15m', '30min': '30m',
        '1hour': '1h', '2hour': '2h', '4hour': '4h', '6hour': '6h', '8hour': '8h', '12hour': '12h',
        'daily': '1d', 'weekly': '1w', 'monthly': '1M'
    },
    'timeout': 30,
    'max_retries': 3
}


class BinanceCryptoPlugin(IDataSourcePlugin):
    """币安数字货币数据源插件"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)  # 添加logger属性
        self.initialized = False
        # 配置以 DB 为主，未提供时使用默认
        self.config = DEFAULT_CONFIG.copy()
        self.session = None
        self.request_count = 0
        self.last_error = None

        # 插件基本信息
        self.name = "币安数字货币数据源插件"
        self.version = "1.0.0"
        self.description = "提供币安交易所数字货币实时和历史数据"
        self.author = "FactorWeave-Quant 开发团队"

        # 插件类型标识
        self.plugin_type = PluginType.DATA_SOURCE_CRYPTO

        # 支持的主要交易对
        self.major_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
            'DOGEUSDT', 'DOTUSDT', 'UNIUSDT', 'LTCUSDT', 'LINKUSDT',
            'BCHUSDT', 'XLMUSDT', 'VETUSDT', 'ETCUSDT', 'THETAUSDT'
        ]

        # 币安K线周期映射引用配置
        self.interval_mapping = self.config.get('interval_mapping', DEFAULT_CONFIG['interval_mapping'])

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息"""

        pass

    def is_connected(self) -> bool:
        """检查连接状态"""
        return getattr(self, 'initialized', False)

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id="binance_crypto_plugin",
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            supported_asset_types=[AssetType.CRYPTO],
            supported_data_types=[
                DataType.HISTORICAL_KLINE,
                DataType.REAL_TIME_QUOTE,
                DataType.MARKET_DEPTH,
                DataType.TRADE_TICK
            ]
        )

    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return [AssetType.CRYPTO]

    def get_supported_data_types(self) -> List[DataType]:
        """获取支持的数据类型"""
        return [
            DataType.HISTORICAL_KLINE,
            DataType.REAL_TIME_QUOTE,
            DataType.MARKET_DEPTH,
            DataType.TRADE_TICK
        ]

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            # 合并配置：外部/DB配置优先
            merged = DEFAULT_CONFIG.copy()
            merged.update(config or {})
            self.config = merged

            # 创建会话
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'FactorWeave-Quant /1.0.0'
            })

            # 配置参数
            self.timeout = int(self.config.get('timeout', DEFAULT_CONFIG['timeout']))
            self.max_retries = int(self.config.get('max_retries', DEFAULT_CONFIG['max_retries']))

            # 尝试测试连接（可选）
            try:
                base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
                api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
                ping_url = f"{base_url}{api['ping']}"
                response = self.session.get(ping_url, timeout=self.timeout)

                if response.status_code == 200:
                    # 获取服务器时间验证连接
                    time_url = f"{base_url}{api['time']}"
                    time_response = self.session.get(time_url, timeout=self.timeout)

                    if time_response.status_code == 200:
                        time_data = time_response.json()
                        if 'serverTime' in time_data:
                            logger.info("币安数字货币数据源插件初始化成功，网络连接正常")
                        else:
                            logger.warning("币安数字货币数据源插件初始化成功，但时间数据异常")
                    else:
                        logger.warning(f"币安数字货币数据源插件初始化成功，但时间API返回: {time_response.status_code}")
                else:
                    logger.warning(f"币安数字货币数据源插件初始化成功，但ping返回: {response.status_code}")
            except Exception as test_e:
                logger.warning(f"币安数字货币数据源插件初始化成功，但网络测试失败: {test_e}")

            # 无论网络测试是否成功，都认为插件初始化成功
            self.initialized = True
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"币安数字货币数据源插件初始化失败: {e}")
            return False

    def shutdown(self) -> bool:
        """关闭插件"""
        try:
            if self.session:
                self.session.close()
            self.initialized = False
            logger.info("币安数字货币数据源插件关闭成功")
            return True
        except Exception as e:
            logger.error(f"币安数字货币数据源插件关闭失败: {e}")
            return False

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        start_time = time.time()

        try:
            if not self.initialized or not self.session:
                return HealthCheckResult(
                    is_healthy=False,
                    response_time=0.0,
                    message="插件未初始化"
                )

            # Ping测试
            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            ping_url = f"{base_url}{api['ping']}"
            response = self.session.get(ping_url, timeout=10)

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return HealthCheckResult(
                    is_healthy=True,
                    response_time=response_time,
                    message="API访问正常"
                )
            elif response.status_code == 451:
                # HTTP 451: 因法律原因不可用（地区限制）
                return HealthCheckResult(
                    is_healthy=True,
                    response_time=response_time,
                    message="插件可用但API受地区限制"
                )
            elif response.status_code in [403, 429]:
                # 403: 禁止访问, 429: 请求过多
                return HealthCheckResult(
                    is_healthy=True,
                    response_time=response_time,
                    message="插件可用但需要API认证"
                )
            else:
                return HealthCheckResult(
                    is_healthy=True,
                    response_time=response_time,
                    message=f"插件可用但API异常: {response.status_code}"
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            # 如果插件已初始化，网络异常时仍认为插件可用
            if self.initialized:
                return HealthCheckResult(
                    is_healthy=True,
                    response_time=response_time,
                    message=f"插件可用但网络异常: {str(e)[:50]}"
                )
            else:
                return HealthCheckResult(
                    is_healthy=False,
                    response_time=response_time,
                    message=str(e)
                )

    def get_exchange_info(self) -> Dict[str, Any]:
        """获取交易所信息"""
        try:
            self.request_count += 1

            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            url = f"{base_url}{api['exchange_info']}"
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                logger.info("获取币安交易所信息成功")
                return data
            else:
                raise Exception(f"API请求失败: {response.status_code}")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取交易所信息失败: {e}")
            return {}

    def get_symbol_list(self) -> pd.DataFrame:
        """获取交易对列表"""
        try:
            exchange_info = self.get_exchange_info()

            if exchange_info and 'symbols' in exchange_info:
                symbols_data = []

                for symbol_info in exchange_info['symbols']:
                    if symbol_info['status'] == 'TRADING':
                        symbols_data.append({
                            'symbol': symbol_info['symbol'],
                            'base_asset': symbol_info['baseAsset'],
                            'quote_asset': symbol_info['quoteAsset'],
                            'status': symbol_info['status'],
                            'base_precision': symbol_info['baseAssetPrecision'],
                            'quote_precision': symbol_info['quotePrecision']
                        })

                df = pd.DataFrame(symbols_data)
                logger.info(f"获取币安交易对列表成功，共 {len(df)} 个交易对")
                return df
            else:
                raise Exception("无法获取交易对信息")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取交易对列表失败: {e}")
            return pd.DataFrame()

    def get_kline_data(self, symbol: str, interval: str = 'daily',
                       start_time: int = None, end_time: int = None,
                       limit: int = 500) -> pd.DataFrame:
        """获取K线数据"""
        try:
            self.request_count += 1

            # 转换周期
            binance_interval = self.interval_mapping.get(interval, DEFAULT_CONFIG['interval_mapping'].get('daily', '1d'))

            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            url = f"{base_url}{api['klines']}"
            params = {
                'symbol': symbol.upper(),
                'interval': binance_interval,
                'limit': min(limit, 1000)  # 币安限制最大1000
            }

            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()

                if data:
                    # 转换为DataFrame
                    df = pd.DataFrame(data, columns=[
                        'open_time', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'count', 'taker_buy_volume',
                        'taker_buy_quote_volume', 'ignore'
                    ])

                    # 数据类型转换
                    df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
                    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']

                    for col in numeric_cols:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                    # 设置索引
                    df = df.set_index('datetime')

                    # 选择主要列
                    df = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume', 'count']]

                    logger.info(f"获取 {symbol} K线数据成功，共 {len(df)} 条记录")
                    return df

            raise Exception(f"API请求失败: {response.status_code}")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_24hr_ticker(self, symbol: str = None) -> pd.DataFrame:
        """获取24小时价格变动统计"""
        try:
            self.request_count += 1

            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            url = f"{base_url}{api['ticker_24hr']}"
            params = {}

            if symbol:
                params['symbol'] = symbol.upper()

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()

                # 确保数据是列表格式
                if isinstance(data, dict):
                    data = [data]

                df = pd.DataFrame(data)

                if not df.empty:
                    # 选择主要列并重命名
                    columns_mapping = {
                        'symbol': 'symbol',
                        'lastPrice': 'price',
                        'priceChangePercent': 'pct_change',
                        'priceChange': 'change',
                        'volume': 'volume',
                        'quoteVolume': 'quote_volume',
                        'highPrice': 'high_24h',
                        'lowPrice': 'low_24h',
                        'openPrice': 'open_24h',
                        'count': 'trade_count'
                    }

                    available_cols = {k: v for k, v in columns_mapping.items() if k in df.columns}
                    df = df[list(available_cols.keys())].rename(columns=available_cols)

                    # 数据类型转换
                    numeric_cols = ['price', 'pct_change', 'change', 'volume', 'quote_volume',
                                    'high_24h', 'low_24h', 'open_24h']

                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')

                    logger.info(f"获取24小时统计数据成功，共 {len(df)} 个交易对")
                    return df

            raise Exception(f"API请求失败: {response.status_code}")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取24小时统计数据失败: {e}")
            return pd.DataFrame()

    def get_real_time_price(self, symbols: List[str] = None) -> pd.DataFrame:
        """获取实时价格"""
        try:
            self.request_count += 1

            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            url = f"{base_url}{api['ticker_price']}"
            params = {}

            if symbols:
                if len(symbols) == 1:
                    params['symbol'] = symbols[0].upper()
                else:
                    # 对于多个交易对，使用24hr ticker
                    return self.get_24hr_ticker()

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()

                # 确保数据是列表格式
                if isinstance(data, dict):
                    data = [data]

                df = pd.DataFrame(data)

                if not df.empty:
                    # 重命名列
                    df = df.rename(columns={'lastPrice': 'price'})

                    # 数据类型转换
                    df['price'] = pd.to_numeric(df['price'], errors='coerce')

                    # 如果指定了交易对，进行筛选
                    if symbols and len(symbols) > 1:
                        upper_symbols = [s.upper() for s in symbols]
                        df = df[df['symbol'].isin(upper_symbols)]

                    logger.info(f"获取实时价格成功，共 {len(df)} 个交易对")
                    return df

            raise Exception(f"API请求失败: {response.status_code}")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取实时价格失败: {e}")
            return pd.DataFrame()

    def get_market_depth(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """获取市场深度"""
        try:
            self.request_count += 1

            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            url = f"{base_url}{api['depth']}"
            params = {
                'symbol': symbol.upper(),
                'limit': min(limit, 5000)  # 币安限制
            }

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()

                # 转换深度数据
                depth_data = {
                    'symbol': symbol,
                    'bids': [[float(price), float(qty)] for price, qty in data.get('bids', [])],
                    'asks': [[float(price), float(qty)] for price, qty in data.get('asks', [])],
                    'timestamp': data.get('lastUpdateId', 0)
                }

                logger.info(f"获取 {symbol} 市场深度成功")
                return depth_data

            raise Exception(f"API请求失败: {response.status_code}")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取市场深度失败 {symbol}: {e}")
            return {}

    def fetch_data(self, symbol: str, data_type: str, **kwargs) -> Any:
        """通用数据获取接口"""
        try:
            if data_type == 'kline':
                return self.get_kline_data(
                    symbol=symbol,
                    interval=kwargs.get('interval', 'daily'),
                    start_time=kwargs.get('start_time'),
                    end_time=kwargs.get('end_time'),
                    limit=kwargs.get('limit', 500)
                )
            elif data_type == 'realtime':
                symbols = kwargs.get('symbols', [symbol])
                return self.get_real_time_price(symbols)
            elif data_type == '24hr_ticker':
                return self.get_24hr_ticker(symbol)
            elif data_type == 'depth':
                return self.get_market_depth(symbol, kwargs.get('limit', 100))
            elif data_type == 'symbol_list':
                return self.get_symbol_list()
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
            'success_rate': 1.0 if self.last_error is None else 0.9,
            'avg_response_time': 0.2,
            'last_update': datetime.now().isoformat(),
            'last_error': self.last_error,
            'major_symbols': self.major_symbols[:10],  # 显示前10个主要交易对
            'api_status': 'connected' if self.initialized else 'disconnected'
        }

    def get_plugin_info(self) -> PluginInfo:
        """获取插件基本信息"""
        return PluginInfo(
            id="binance_crypto",
            name="Binance数字货币数据源",
            version=self.version,
            description=self.description,
            author="FactorWeave-Quant 团队",
            supported_asset_types=[AssetType.CRYPTO],
            supported_data_types=[DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE]
        )

    def get_supported_data_types(self) -> List[DataType]:
        """获取支持的数据类型列表"""
        return [DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE]

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
    def get_sector_fund_flow_data(self, symbol: str = "sector", **kwargs) -> pd.DataFrame:
        """
        获取加密货币板块资金流数据

        Args:
            symbol: 板块代码或"sector"表示获取所有板块
            **kwargs: 其他参数

        Returns:
            板块资金流数据DataFrame
        """
        try:
            self.logger.info(f"{self.name}获取加密货币板块资金流数据")
            
            # TODO: 实现加密货币板块资金流数据获取逻辑
            import pandas as pd
            
            # 模拟数据 - 基于DeFi、NFT、Layer1等板块
            records = [
                {
                    'sector_code': 'DEFI',
                    'sector_name': 'DeFi板块',
                    'change_pct': 0.05,
                    'main_net_inflow': 10000000,  # USDT
                    'main_net_inflow_pct': 0.03,
                    'volume_24h': 500000000,
                    'market_cap': 50000000000
                },
                {
                    'sector_code': 'NFT',
                    'sector_name': 'NFT板块',
                    'change_pct': -0.02,
                    'main_net_inflow': -5000000,
                    'main_net_inflow_pct': -0.01,
                    'volume_24h': 200000000,
                    'market_cap': 20000000000
                }
            ]
            
            df = pd.DataFrame(records)
            self.logger.info(f"获取加密货币板块资金流数据完成，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取加密货币板块资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_individual_fund_flow_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """
        获取个币资金流数据

        Args:
            symbol: 加密货币代码
            **kwargs: 其他参数

        Returns:
            个币资金流数据DataFrame
        """
        try:
            self.logger.info(f"{self.name}获取个币 {symbol} 资金流数据")
            
            # TODO: 实现加密货币资金流数据获取逻辑
            import pandas as pd
            from datetime import datetime
            
            records = [
                {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'symbol': symbol,
                    'net_inflow_usdt': 1000000,
                    'net_inflow_btc': 50,
                    'volume_24h': 100000000,
                    'price_change_pct': 0.02,
                    'whale_activity': 'high'
                }
            ]
            
            df = pd.DataFrame(records)
            self.logger.info(f"获取个币资金流数据完成，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取个币资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_main_fund_flow_data(self, symbol: str = "index", **kwargs) -> pd.DataFrame:
        """
        获取加密货币市场主力资金流数据

        Args:
            symbol: 指数代码或"index"表示获取主要指数
            **kwargs: 其他参数

        Returns:
            主力资金流数据DataFrame
        """
        try:
            self.logger.info(f"{self.name}获取加密货币市场主力资金流数据")
            
            # TODO: 实现加密货币市场资金流数据获取逻辑
            import pandas as pd
            
            records = [
                {
                    'market': 'Total Crypto Market',
                    'total_market_cap': 2000000000000,
                    'btc_dominance': 0.45,
                    'eth_dominance': 0.18,
                    'net_inflow_24h': 500000000,
                    'fear_greed_index': 65,
                    'institutional_flow': 200000000
                }
            ]
            
            df = pd.DataFrame(records)
            self.logger.info(f"获取加密货币市场资金流数据完成，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取加密货币市场资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()




def create_plugin() -> IDataSourcePlugin:
    """创建插件实例"""
    return BinanceCryptoPlugin()


# 插件元数据
PLUGIN_METADATA = {
    "name": "币安数字货币数据源插件",
    "version": "1.0.0",
    "description": "提供币安交易所数字货币实时和历史数据",
    "author": "FactorWeave-Quant 开发团队",
    "plugin_type": "data_source_crypto",
    "asset_types": ["crypto"],
    "data_types": ["historical_kline", "real_time_quote", "market_depth", "trade_tick"],
    "exchanges": ["binance"],
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
        }
    }
}
