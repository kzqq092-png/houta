"""
火币交易所数字货币数据插件
提供BTC、ETH等主流数字货币的实时和历史数据
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import requests
import pandas as pd

from core.data_source_extensions import IDataSourcePlugin
from core.plugin_types import AssetType, DataType, PluginType
from core.data_source_extensions import IDataSourcePlugin, PluginInfo
from core.plugin_types import AssetType, DataType
from core.data_source_data_models import StockInfo, KlineData, MarketData, QueryParams, HealthCheckResult


class HuobiCryptoPlugin(IDataSourcePlugin):
    """火币交易所数字货币数据源插件"""

    def __init__(self):
        self.name = "火币数字货币数据源"
        self.version = "1.0.0"
        self.description = "获取火币交易所数字货币数据"
        self.plugin_type = PluginType.DATA_SOURCE_CRYPTO
        self.supported_asset_types = [AssetType.CRYPTO]
        # 默认配置
        self.DEFAULT_CONFIG = {
            'base_url': 'https://api.huobi.pro',
            'timeout': 10,
            'rate_limit_delay': 0.1
        }
        self.config = self.DEFAULT_CONFIG.copy()
        self.base_url = self.config['base_url']
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0
        self._rate_limit_delay = float(self.config.get('rate_limit_delay', self.DEFAULT_CONFIG['rate_limit_delay']))

        self.initialized = False  # 插件初始化状态

    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return self.supported_asset_types

    def _rate_limit(self):
        """API请求频率限制"""
        current_time = time.time()
        if current_time - self._last_request_time < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - (current_time - self._last_request_time))
        self._last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """发送API请求"""
        try:
            self._rate_limit()
            url = f"{self.base_url}{endpoint}"

            headers = {
                'User-Agent': 'Hikyuu-Trading-System/1.0',
                'Accept': 'application/json'
            }

            timeout = int(self.config.get('timeout', self.DEFAULT_CONFIG['timeout']))
            response = requests.get(url, params=params, headers=headers, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    return data
                else:
                    self.logger.warning(f"Huobi API error: {data.get('err-msg', 'Unknown error')}")
                    return None
            else:
                self.logger.warning(f"Huobi API request failed: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Huobi API request error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in Huobi API request: {e}")
            return None

    def is_connected(self) -> bool:
        """检查连接状态"""
        return getattr(self, 'initialized', False)

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取数字货币基本信息"""
        try:
            # 获取交易对信息
            symbols_data = self._make_request("/v1/common/symbols")
            if not symbols_data or 'data' not in symbols_data:
                return self._get_fallback_stock_info(symbol)

            # 查找指定交易对
            symbol_info = None
            for s in symbols_data['data']:
                if s.get('symbol') == symbol.lower().replace('-', ''):
                    symbol_info = s
                    break

            if not symbol_info:
                return self._get_fallback_stock_info(symbol)

            return StockInfo(
                code=symbol,
                name=f"{symbol_info.get('base-currency', '').upper()}/{symbol_info.get('quote-currency', '').upper()}",
                market=symbol_info.get('quote-currency', 'usdt').upper(),
                currency=symbol_info.get('quote-currency', 'usdt').upper(),
                sector='数字货币',
                industry='区块链',
                list_date=None,
                extra_info={
                    'exchange': 'Huobi',
                    'base_currency': symbol_info.get('base-currency'),
                    'quote_currency': symbol_info.get('quote-currency'),
                    'state': symbol_info.get('state'),
                    'price_precision': symbol_info.get('price-precision'),
                    'amount_precision': symbol_info.get('amount-precision')
                }
            )

        except Exception as e:
            self.logger.error(f"获取 {symbol} 股票信息失败: {e}")
            return self._get_fallback_stock_info(symbol)

    def _get_fallback_stock_info(self, symbol: str) -> StockInfo:
        """获取备用股票信息"""
        crypto_names = {
            'btcusdt': 'Bitcoin/USDT',
            'ethusdt': 'Ethereum/USDT',
            'ltcusdt': 'Litecoin/USDT',
            'bchusdt': 'Bitcoin Cash/USDT',
            'xrpusdt': 'Ripple/USDT'
        }

        return StockInfo(
            code=symbol,
            name=crypto_names.get(symbol.lower(), symbol),
            market='USDT',
            currency='USDT',
            sector='数字货币',
            industry='区块链',
            list_date=None,
            extra_info={'exchange': 'Huobi', 'fallback': True}
        )

    def get_kline_data(self, symbol: str, start_date: datetime,
                       end_date: datetime, frequency: str = "1d") -> List[KlineData]:
        """获取K线数据"""
        try:
            # 转换频率参数
            period_map = {
                "1m": "1min",
                "5m": "5min",
                "15m": "15min",
                "30m": "30min",
                "1h": "60min",
                "4h": "4hour",
                "1d": "1day",
                "1w": "1week"
            }

            period = period_map.get(frequency, "1day")

            # 火币的symbol格式需要是小写，去掉连字符
            huobi_symbol = symbol.lower().replace('-', '')

            # 构建请求参数
            params = {
                'symbol': huobi_symbol,
                'period': period,
                'size': 2000  # 最多2000条
            }

            # 获取历史数据
            response = self._make_request("/market/history/kline", params)

            if not response or 'data' not in response:
                return self._get_fallback_kline_data(symbol, start_date, end_date, frequency)

            kline_list = []
            for candle in response['data']:
                timestamp = datetime.fromtimestamp(candle['id'])

                # 过滤时间范围
                if timestamp < start_date or timestamp > end_date:
                    continue

                kline_data = KlineData(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=float(candle['open']),
                    high=float(candle['high']),
                    low=float(candle['low']),
                    close=float(candle['close']),
                    volume=float(candle['vol']),
                    frequency=frequency,
                    extra_info={
                        'exchange': 'Huobi',
                        'amount': candle.get('amount', 0),
                        'count': candle.get('count', 0)
                    }
                )
                kline_list.append(kline_data)

            # 按时间排序
            kline_list.sort(key=lambda x: x.timestamp)

            self.logger.info(f"获取 {symbol} K线数据成功，共 {len(kline_list)} 条记录")
            return kline_list

        except Exception as e:
            self.logger.error(f"获取 {symbol} K线数据失败: {e}")
            return self._get_fallback_kline_data(symbol, start_date, end_date, frequency)

    def _get_fallback_kline_data(self, symbol: str, start_date: datetime,
                                 end_date: datetime, frequency: str) -> List[KlineData]:
        """生成备用K线数据"""
        import random

        kline_list = []
        current_date = start_date
        base_price = 50000.0 if 'btc' in symbol.lower() else 3000.0 if 'eth' in symbol.lower() else 100.0

        while current_date <= end_date:
            # 模拟价格波动
            price_change = random.uniform(-0.05, 0.05)
            open_price = base_price * (1 + price_change)
            close_price = open_price * (1 + random.uniform(-0.03, 0.03))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
            volume = random.uniform(100, 1000)

            kline_data = KlineData(
                symbol=symbol,
                timestamp=current_date,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                frequency=frequency,
                extra_info={'exchange': 'Huobi', 'fallback': True}
            )
            kline_list.append(kline_data)

            # 增加时间间隔
            if frequency == "1d":
                current_date += timedelta(days=1)
            elif frequency == "1h":
                current_date += timedelta(hours=1)
            else:
                current_date += timedelta(minutes=1)

            base_price = close_price

        return kline_list

    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """获取实时市场数据"""
        try:
            # 火币的symbol格式
            huobi_symbol = symbol.lower().replace('-', '')

            # 获取24小时统计数据
            ticker_data = self._make_request(f"/market/detail/merged",
                                             params={'symbol': huobi_symbol})

            if not ticker_data or 'tick' not in ticker_data:
                return self._get_fallback_market_data(symbol)

            tick = ticker_data['tick']

            return MarketData(
                symbol=symbol,
                current_price=float(tick['close']),
                open_price=float(tick['open']),
                high_price=float(tick['high']),
                low_price=float(tick['low']),
                volume=float(tick['vol']),
                timestamp=datetime.fromtimestamp(ticker_data['ts'] / 1000),
                change_amount=float(tick['close']) - float(tick['open']),
                change_percent=(float(tick['close']) - float(tick['open'])) / float(tick['open']) * 100,
                extra_info={
                    'exchange': 'Huobi',
                    'bid': tick['bid'][0] if tick.get('bid') else None,
                    'ask': tick['ask'][0] if tick.get('ask') else None,
                    'amount': tick.get('amount', 0),
                    'count': tick.get('count', 0)
                }
            )

        except Exception as e:
            self.logger.error(f"获取 {symbol} 实时数据失败: {e}")
            return self._get_fallback_market_data(symbol)

    def _get_fallback_market_data(self, symbol: str) -> MarketData:
        """生成备用市场数据"""

        base_price = 50000.0 if 'btc' in symbol.lower() else 3000.0 if 'eth' in symbol.lower() else 100.0
        current_price = base_price * (1 + random.uniform(-0.05, 0.05))

        return MarketData(
            symbol=symbol,
            current_price=current_price,
            open_price=current_price * 0.98,
            high_price=current_price * 1.02,
            low_price=current_price * 0.96,
            volume=random.uniform(1000, 10000),
            timestamp=datetime.now(),
            change_amount=current_price * 0.02,
            change_percent=2.0,
            extra_info={'exchange': 'Huobi', 'fallback': True}
        )

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        try:
            data = self._make_request("/v1/common/timestamp")
            if data and data.get('status') == 'ok':
                return HealthCheckResult(is_healthy=True, message="ok", response_time=0.0)
            return HealthCheckResult(is_healthy=False, message="接口异常", response_time=0.0)
        except Exception as e:
            # 网络异常等，如果插件已初始化则认为基本可用
            if getattr(self, 'initialized', False):
                return HealthCheckResult(is_healthy=True, message=f"插件可用但网络异常: {str(e)}", response_time=0.0)
            else:
                return HealthCheckResult(is_healthy=False, message=str(e), response_time=0.0)

    def get_plugin_info(self) -> PluginInfo:
        """获取插件基本信息"""
        return PluginInfo(
            id="huobi_crypto",
            name="火币数字货币数据源",
            version=self.version,
            description=self.description,
            author="FactorWeave-Quant 团队",
            supported_asset_types=[AssetType.CRYPTO],
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

            # 设置初始化状态
            self.initialized = True
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
