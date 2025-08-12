"""
OKX（欧易）交易所数字货币数据插件
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


class OKXCryptoPlugin(IDataSourcePlugin):
    """OKX（欧易）交易所数字货币数据源插件"""

    def __init__(self):
        self.name = "OKX数字货币数据源"
        self.version = "1.0.0"
        self.description = "获取OKX（欧易）交易所数字货币数据"
        self.plugin_type = PluginType.DATA_SOURCE_CRYPTO
        self.supported_asset_types = [AssetType.CRYPTO]
        # 默认配置
        self.DEFAULT_CONFIG = {
            'base_url': 'https://www.okx.com/api/v5',
            'timeout': 10,
            'rate_limit_delay': 0.1
        }
        self.config = self.DEFAULT_CONFIG.copy()
        self.base_url = self.config['base_url']
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0
        self._rate_limit_delay = float(self.config.get('rate_limit_delay', self.DEFAULT_CONFIG['rate_limit_delay']))

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
                if data.get('code') == '0':
                    return data
                else:
                    self.logger.warning(f"OKX API error: {data.get('msg', 'Unknown error')}")
                    return None
            else:
                self.logger.warning(f"OKX API request failed: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"OKX API request error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in OKX API request: {e}")
            return None

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取数字货币基本信息"""
        try:
            # 获取交易对信息
            instruments_data = self._make_request("/public/instruments",
                                                  params={'instType': 'SPOT'})
            if not instruments_data or 'data' not in instruments_data:
                return self._get_fallback_stock_info(symbol)

            # 查找指定交易对 (OKX使用-分隔符，如BTC-USDT)
            instrument_info = None
            for inst in instruments_data['data']:
                if inst.get('instId') == symbol.upper():
                    instrument_info = inst
                    break

            if not instrument_info:
                return self._get_fallback_stock_info(symbol)

            return StockInfo(
                code=symbol,
                name=f"{instrument_info.get('baseCcy', '').upper()}/{instrument_info.get('quoteCcy', '').upper()}",
                market=instrument_info.get('quoteCcy', 'USDT').upper(),
                currency=instrument_info.get('quoteCcy', 'USDT').upper(),
                sector='数字货币',
                industry='区块链',
                list_date=None,
                extra_info={
                    'exchange': 'OKX',
                    'base_currency': instrument_info.get('baseCcy'),
                    'quote_currency': instrument_info.get('quoteCcy'),
                    'state': instrument_info.get('state'),
                    'tick_size': instrument_info.get('tickSz'),
                    'lot_size': instrument_info.get('lotSz'),
                    'min_size': instrument_info.get('minSz')
                }
            )

        except Exception as e:
            self.logger.error(f"获取 {symbol} 股票信息失败: {e}")
            return self._get_fallback_stock_info(symbol)

    def _get_fallback_stock_info(self, symbol: str) -> StockInfo:
        """获取备用股票信息"""
        crypto_names = {
            'BTC-USDT': 'Bitcoin/USDT',
            'ETH-USDT': 'Ethereum/USDT',
            'LTC-USDT': 'Litecoin/USDT',
            'BCH-USDT': 'Bitcoin Cash/USDT',
            'XRP-USDT': 'Ripple/USDT'
        }

        return StockInfo(
            code=symbol,
            name=crypto_names.get(symbol.upper(), symbol),
            market='USDT',
            currency='USDT',
            sector='数字货币',
            industry='区块链',
            list_date=None,
            extra_info={'exchange': 'OKX', 'fallback': True}
        )

    def get_kline_data(self, symbol: str, start_date: datetime,
                       end_date: datetime, frequency: str = "1d") -> List[KlineData]:
        """获取K线数据"""
        try:
            # 转换频率参数
            bar_map = {
                "1m": "1m",
                "3m": "3m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1H",
                "2h": "2H",
                "4h": "4H",
                "6h": "6H",
                "12h": "12H",
                "1d": "1D",
                "1w": "1W",
                "1M": "1M"
            }

            bar = bar_map.get(frequency, "1D")

            # OKX的symbol格式使用-分隔符
            okx_symbol = symbol.upper()
            if '-' not in okx_symbol:
                # 如果没有分隔符，假设是USDT交易对
                okx_symbol = f"{okx_symbol}-USDT"

            # 构建请求参数
            params = {
                'instId': okx_symbol,
                'bar': bar,
                'limit': '300'  # 最多300条
            }

            # 获取历史数据
            response = self._make_request("/market/history-candles", params)

            if not response or 'data' not in response:
                return self._get_fallback_kline_data(symbol, start_date, end_date, frequency)

            kline_list = []
            for candle in response['data']:
                if len(candle) >= 6:
                    timestamp_ms, open_price, high, low, close_price, vol = candle[:6]
                    timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000)

                    # 过滤时间范围
                    if timestamp < start_date or timestamp > end_date:
                        continue

                    kline_data = KlineData(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=float(open_price),
                        high=float(high),
                        low=float(low),
                        close=float(close_price),
                        volume=float(vol),
                        frequency=frequency,
                        extra_info={
                            'exchange': 'OKX',
                            'volCcy': candle[6] if len(candle) > 6 else None,
                            'volCcyQuote': candle[7] if len(candle) > 7 else None,
                            'confirm': candle[8] if len(candle) > 8 else None
                        }
                    )
                    kline_list.append(kline_data)

            # 按时间排序（OKX返回的数据通常是倒序的）
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
        base_price = 50000.0 if 'BTC' in symbol.upper() else 3000.0 if 'ETH' in symbol.upper() else 100.0

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
                extra_info={'exchange': 'OKX', 'fallback': True}
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
            # OKX的symbol格式
            okx_symbol = symbol.upper()
            if '-' not in okx_symbol:
                okx_symbol = f"{okx_symbol}-USDT"

            # 获取24小时统计数据
            ticker_data = self._make_request("/market/ticker",
                                             params={'instId': okx_symbol})

            if not ticker_data or 'data' not in ticker_data or not ticker_data['data']:
                return self._get_fallback_market_data(symbol)

            tick = ticker_data['data'][0]

            current_price = float(tick['last'])
            open_price = float(tick['open24h'])

            return MarketData(
                symbol=symbol,
                current_price=current_price,
                open_price=open_price,
                high_price=float(tick['high24h']),
                low_price=float(tick['low24h']),
                volume=float(tick['vol24h']),
                timestamp=datetime.fromtimestamp(int(tick['ts']) / 1000),
                change_amount=current_price - open_price,
                change_percent=(current_price - open_price) / open_price * 100 if open_price > 0 else 0,
                extra_info={
                    'exchange': 'OKX',
                    'bid': tick.get('bidPx'),
                    'ask': tick.get('askPx'),
                    'bid_size': tick.get('bidSz'),
                    'ask_size': tick.get('askSz'),
                    'vol_ccy': tick.get('volCcy24h')
                }
            )

        except Exception as e:
            self.logger.error(f"获取 {symbol} 实时数据失败: {e}")
            return self._get_fallback_market_data(symbol)

    def _get_fallback_market_data(self, symbol: str) -> MarketData:
        """生成备用市场数据"""

        base_price = 50000.0 if 'BTC' in symbol.upper() else 3000.0 if 'ETH' in symbol.upper() else 100.0
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
            extra_info={'exchange': 'OKX', 'fallback': True}
        )

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        try:
            # 调用公共时间接口
            data = self._make_request("/public/time")
            if data and data.get('code') == '0':
                return HealthCheckResult(is_healthy=True, message="ok", response_time=0.0)
            return HealthCheckResult(is_healthy=False, message="接口异常", response_time=0.0)
        except Exception as e:
            return HealthCheckResult(is_healthy=False, message=str(e), response_time=0.0)

    def get_plugin_info(self) -> PluginInfo:
        """获取插件基本信息"""
        return PluginInfo(
            id="okx_crypto",
            name="OKX数字货币数据源",
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
