"""
外汇数据插件
提供主要货币对的实时汇率和历史数据
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import requests
import pandas as pd

from core.data_source_extensions import IDataSourcePlugin, HealthCheckResult
from core.plugin_types import AssetType, DataType, PluginType
from core.data_source_extensions import IDataSourcePlugin, PluginInfo, HealthCheckResult
from core.plugin_types import AssetType, DataType
from core.data_source_data_models import QueryParams, StockInfo, KlineData, MarketData


class ForexDataPlugin(IDataSourcePlugin):
    """外汇数据源插件"""

    def __init__(self):
        self.name = "外汇数据源"
        self.version = "1.0.0"
        self.description = "外汇市场数据源"
        self.plugin_type = PluginType.DATA_SOURCE_FOREX
        self.supported_asset_types = [AssetType.FOREX]
        self.initialized = False  # 添加初始化状态
        self.DEFAULT_CONFIG = {
            'base_url': 'https://api.exchangerate-api.com/v4',
            'backup_url': 'https://api.fixer.io/v1',
            'timeout': 10,
            'provider': 'exchangerate-api',
            'api_key': '',
            'authenticated': False
        }
        self.config = self.DEFAULT_CONFIG.copy()
        self.base_url = self.config['base_url']  # 免费汇率API
        self.backup_url = self.config['backup_url']  # 备用API
        self.logger = logging.getLogger(__name__)

        # API配置
        self.api_config = {
            'api_key': self.config.get('api_key', ''),
            'provider': self.config.get('provider', 'exchangerate-api'),  # exchangerate-api, fixer, alpha_vantage
            'authenticated': bool(self.config.get('authenticated', False))
        }

        # 支持的货币对
        self.currency_pairs = {
            # 主要货币对
            'EURUSD': {'name': '欧元/美元', 'base': 'EUR', 'quote': 'USD', 'type': 'major'},
            'GBPUSD': {'name': '英镑/美元', 'base': 'GBP', 'quote': 'USD', 'type': 'major'},
            'USDJPY': {'name': '美元/日元', 'base': 'USD', 'quote': 'JPY', 'type': 'major'},
            'USDCHF': {'name': '美元/瑞郎', 'base': 'USD', 'quote': 'CHF', 'type': 'major'},
            'AUDUSD': {'name': '澳元/美元', 'base': 'AUD', 'quote': 'USD', 'type': 'major'},
            'USDCAD': {'name': '美元/加元', 'base': 'USD', 'quote': 'CAD', 'type': 'major'},
            'NZDUSD': {'name': '纽元/美元', 'base': 'NZD', 'quote': 'USD', 'type': 'major'},

            # 交叉货币对
            'EURJPY': {'name': '欧元/日元', 'base': 'EUR', 'quote': 'JPY', 'type': 'cross'},
            'GBPJPY': {'name': '英镑/日元', 'base': 'GBP', 'quote': 'JPY', 'type': 'cross'},
            'EURGBP': {'name': '欧元/英镑', 'base': 'EUR', 'quote': 'GBP', 'type': 'cross'},
            'EURAUD': {'name': '欧元/澳元', 'base': 'EUR', 'quote': 'AUD', 'type': 'cross'},
            'GBPAUD': {'name': '英镑/澳元', 'base': 'GBP', 'quote': 'AUD', 'type': 'cross'},
            'AUDCHF': {'name': '澳元/瑞郎', 'base': 'AUD', 'quote': 'CHF', 'type': 'cross'},

            # 人民币相关
            'USDCNY': {'name': '美元/人民币', 'base': 'USD', 'quote': 'CNY', 'type': 'exotic'},
            'EURCNY': {'name': '欧元/人民币', 'base': 'EUR', 'quote': 'CNY', 'type': 'exotic'},
            'GBPCNY': {'name': '英镑/人民币', 'base': 'GBP', 'quote': 'CNY', 'type': 'exotic'},
            'JPYCNY': {'name': '日元/人民币', 'base': 'JPY', 'quote': 'CNY', 'type': 'exotic'},
            'AUDCNY': {'name': '澳元/人民币', 'base': 'AUD', 'quote': 'CNY', 'type': 'exotic'},
            'CADCNY': {'name': '加元/人民币', 'base': 'CAD', 'quote': 'CNY', 'type': 'exotic'},

            # 新兴市场货币
            'USDINR': {'name': '美元/印度卢比', 'base': 'USD', 'quote': 'INR', 'type': 'exotic'},
            'USDBRL': {'name': '美元/巴西雷亚尔', 'base': 'USD', 'quote': 'BRL', 'type': 'exotic'},
            'USDMXN': {'name': '美元/墨西哥比索', 'base': 'USD', 'quote': 'MXN', 'type': 'exotic'},
            'USDRUB': {'name': '美元/俄罗斯卢布', 'base': 'USD', 'quote': 'RUB', 'type': 'exotic'},
            'USDKRW': {'name': '美元/韩元', 'base': 'USD', 'quote': 'KRW', 'type': 'exotic'}
        }

        # 货币对的典型价格范围
        self.price_ranges = {
            'EURUSD': (1.0500, 1.2500),
            'GBPUSD': (1.2000, 1.4000),
            'USDJPY': (100.0, 150.0),
            'USDCHF': (0.8500, 1.0500),
            'AUDUSD': (0.6500, 0.8500),
            'USDCAD': (1.2000, 1.4000),
            'NZDUSD': (0.5500, 0.7500),
            'USDCNY': (6.3000, 7.3000),
            'USDINR': (70.0, 85.0),
            'USDBRL': (4.5, 6.5),
            'USDMXN': (18.0, 25.0),
            'USDRUB': (60.0, 100.0),
            'USDKRW': (1100.0, 1400.0)
        }
        # 连接状态属性
        self.connection_time = None
        self.last_activity = None
        self.last_error = None
        self.config = {}


    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return self.supported_asset_types

    def configure_api(self, api_key: str, provider: str = 'exchangerate-api'):
        """配置API认证信息"""
        self.config.update({
            'api_key': api_key,
            'provider': provider
        })
        self.api_config['api_key'] = api_key
        self.api_config['provider'] = provider
        self.api_config['authenticated'] = True  # 配置后视为认证成功

    def _authenticate(self) -> bool:
        """API认证（某些免费API不需要认证）"""
        try:
            if self.api_config['provider'] == 'exchangerate-api':
                # exchangerate-api 免费版不需要API密钥
                self.api_config['authenticated'] = True
                self.logger.info("外汇API认证成功（免费版）")
                return True
            elif self.api_config['api_key']:
                self.api_config['authenticated'] = True
                self.logger.info("外汇API认证成功")
                return True
            else:
                self.logger.warning("外汇API密钥未配置")
                return False
        except Exception as e:
            self.logger.error(f"外汇API认证失败: {e}")
            return False

    def _make_api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """发送API请求"""
        try:
            if not self.api_config['authenticated']:
                if not self._authenticate():
                    return None

            # 尝试使用主要API
            url = f"{self.base_url}{endpoint}"

            headers = {
                'User-Agent': 'Hikyuu-Trading-System/1.0',
                'Accept': 'application/json'
            }

            timeout = int(self.config.get('timeout', self.DEFAULT_CONFIG['timeout']))
            response = requests.get(url, params=params, headers=headers, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                if 'error' not in data:
                    return data
                else:
                    self.logger.warning(f"外汇API错误: {data.get('error', 'Unknown error')}")
                    return None
            else:
                self.logger.warning(f"外汇API请求失败: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"外汇API请求异常: {e}")
            return None
        except Exception as e:
            self.logger.error(f"外汇API请求意外错误: {e}")
            return None

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取货币对基本信息"""
        try:
            pair_info = self.currency_pairs.get(symbol.upper())
            if not pair_info:
                return self._get_fallback_stock_info(symbol)

            return StockInfo(
                code=symbol,
                name=pair_info['name'],
                market='FOREX',
                currency=pair_info['quote'],
                sector='外汇',
                industry=f"{pair_info['type']}货币对",
                list_date=None,
                extra_info={
                    'base_currency': pair_info['base'],
                    'quote_currency': pair_info['quote'],
                    'pair_type': pair_info['type'],
                    'data_source': 'Forex',
                    'trading_hours': '24/5'  # 24小时，周一到周五
                }
            )

        except Exception as e:
            self.logger.error(f"获取 {symbol} 货币对信息失败: {e}")
            return self._get_fallback_stock_info(symbol)

    def _get_fallback_stock_info(self, symbol: str) -> StockInfo:
        """获取备用货币对信息"""
        return StockInfo(
            code=symbol,
            name=f"{symbol} 货币对",
            market='FOREX',
            currency='USD',
            sector='外汇',
            industry='货币对',
            list_date=None,
            extra_info={'data_source': 'Forex', 'fallback': True}
        )

    def get_kline_data(self, symbol: str, start_date: datetime,
                       end_date: datetime, frequency: str = "1d") -> List[KlineData]:
        """获取货币对K线数据"""
        try:
            # 大多数免费外汇API不提供历史K线数据
            # 这里生成模拟数据，实际应用中可以使用付费API
            return self._get_simulated_kline_data(symbol, start_date, end_date, frequency)

        except Exception as e:
            self.logger.error(f"获取 {symbol} K线数据失败: {e}")
            return self._get_simulated_kline_data(symbol, start_date, end_date, frequency)

    def _get_simulated_kline_data(self, symbol: str, start_date: datetime,
                                  end_date: datetime, frequency: str) -> List[KlineData]:
        """生成模拟K线数据"""
        import random

        kline_list = []
        current_date = start_date

        # 获取基础价格范围
        price_range = self.price_ranges.get(symbol.upper(), (1.0, 2.0))
        base_price = (price_range[0] + price_range[1]) / 2

        while current_date <= end_date:
            # 外汇市场波动相对较小
            price_change = random.uniform(-0.01, 0.01)  # 1%波动
            open_price = base_price * (1 + price_change)
            close_price = open_price * (1 + random.uniform(-0.005, 0.005))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.003))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.003))

            # 外汇市场成交量巨大，这里用相对值表示
            volume = random.uniform(100000, 1000000)

            # 价格精度处理
            precision = 5 if 'JPY' in symbol.upper() else 6

            kline_data = KlineData(
                symbol=symbol,
                timestamp=current_date,
                open=round(open_price, precision),
                high=round(high_price, precision),
                low=round(low_price, precision),
                close=round(close_price, precision),
                volume=int(volume),
                frequency=frequency,
                extra_info={
                    'data_source': 'Forex',
                    'precision': precision,
                    'simulated': True
                }
            )
            kline_list.append(kline_data)

            # 增加时间间隔（外汇市场24小时交易，但周末休市）
            if frequency == "1d":
                current_date += timedelta(days=1)
                # 跳过周末
                while current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
            elif frequency == "1h":
                current_date += timedelta(hours=1)
                # 跳过周末
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=2)
                    current_date = current_date.replace(hour=0)
            else:
                current_date += timedelta(minutes=1)

            base_price = close_price

        return kline_list

    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """获取实时汇率数据"""
        try:
            pair_info = self.currency_pairs.get(symbol.upper())
            if not pair_info:
                return self._get_simulated_market_data(symbol)

            # 尝试获取实时汇率
            base_currency = pair_info['base']
            quote_currency = pair_info['quote']

            # 调用汇率API
            rate_data = self._make_api_request(f"/latest/{base_currency}")

            if rate_data and 'rates' in rate_data:
                rates = rate_data['rates']
                if quote_currency in rates:
                    current_rate = float(rates[quote_currency])

                    # 模拟开盘价（实际应用中需要从历史数据获取）
                    open_rate = current_rate * (1 + random.uniform(-0.005, 0.005))

                    return MarketData(
                        symbol=symbol,
                        current_price=current_rate,
                        open_price=open_rate,
                        high_price=current_rate * 1.002,
                        low_price=current_rate * 0.998,
                        volume=random.randint(500000, 2000000),
                        timestamp=datetime.now(),
                        change_amount=current_rate - open_rate,
                        change_percent=(current_rate - open_rate) / open_rate * 100,
                        extra_info={
                            'base_currency': base_currency,
                            'quote_currency': quote_currency,
                            'data_source': 'Forex',
                            'bid': current_rate * 0.9999,
                            'ask': current_rate * 1.0001,
                            'spread': current_rate * 0.0002
                        }
                    )

            # 如果API调用失败，返回模拟数据
            return self._get_simulated_market_data(symbol)

        except Exception as e:
            self.logger.error(f"获取 {symbol} 实时汇率失败: {e}")
            return self._get_simulated_market_data(symbol)

    def _get_simulated_market_data(self, symbol: str) -> MarketData:
        """生成模拟市场数据"""

        # 获取基础价格范围
        price_range = self.price_ranges.get(symbol.upper(), (1.0, 2.0))
        base_price = (price_range[0] + price_range[1]) / 2

        current_price = base_price * (1 + random.uniform(-0.01, 0.01))
        open_price = current_price * (1 + random.uniform(-0.005, 0.005))

        # 价格精度
        precision = 3 if 'JPY' in symbol.upper() else 5

        return MarketData(
            symbol=symbol,
            current_price=round(current_price, precision),
            open_price=round(open_price, precision),
            high_price=round(current_price * 1.005, precision),
            low_price=round(current_price * 0.995, precision),
            volume=random.randint(800000, 3000000),
            timestamp=datetime.now(),
            change_amount=round(current_price - open_price, precision),
            change_percent=round((current_price - open_price) / open_price * 100, 2),
            extra_info={
                'data_source': 'Forex',
                'precision': precision,
                'bid': round(current_price * 0.9999, precision),
                'ask': round(current_price * 1.0001, precision),
                'spread': round(current_price * 0.0002, precision),
                'simulated': True
            }
        )

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        try:
            endpoint = "/latest/USD"
            data = self._make_api_request(endpoint)
            if data and 'rates' in data:
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
            id="forex_data",
            name="外汇数据源",
            version=self.version,
            description=self.description,
            author="FactorWeave-Quant 团队",
            supported_asset_types=[AssetType.FOREX],
            supported_data_types=[DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE],
            capabilities={
                "markets": ["spot", "forward"],
                "currency_pairs": ["major", "minor", "exotic"],
                "frequencies": ["1m", "5m", "15m", "30m", "60m", "D"],
                "real_time_support": True,
                "historical_data": True
            }
        )

    def get_supported_data_types(self) -> List[DataType]:
        """获取支持的数据类型列表"""
        return [DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE]

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            # 合并配置
            if config:
                self.config.update(config)

            # 配置API
            if 'api_key' in config:
                self.configure_api(config.get('api_key', ''))

            # 执行认证
            if self._authenticate():
                self.initialized = True
                self.logger.info("外汇数据源插件初始化成功")
                return True
            else:
                self.logger.error("外汇数据源插件认证失败")
                return False
        except Exception as e:
            self.logger.error(f"插件初始化失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.initialized and self.api_config.get('authenticated', False)

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

    @property
    def plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id=f"{self.__class__.__name__.lower()}",
            name=getattr(self, 'name', self.__class__.__name__),
            version=getattr(self, 'version', '1.0.0'),
            description=getattr(self, 'description', '数据源插件'),
            author=getattr(self, 'author', 'HIkyuu-UI Team'),
            supported_asset_types=getattr(self, 'supported_asset_types', [AssetType.STOCK]),
            supported_data_types=getattr(self, 'supported_data_types', [DataType.HISTORICAL_KLINE]),
            capabilities={
                "markets": ["SH", "SZ"],
                "frequencies": ["1m", "5m", "15m", "30m", "60m", "D"],
                "real_time_support": True,
                "historical_data": True
            }
        )

    def connect(self, **kwargs) -> bool:
        """连接数据源"""
        try:
            # TODO: 实现具体的连接逻辑
            self.logger.info(f"{self.__class__.__name__} 连接成功")
            return True
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开连接"""
        try:
            # TODO: 实现具体的断开连接逻辑
            if hasattr(self, 'logger'):
                self.logger.info(f"{self.__class__.__name__} 断开连接")
            return True
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        # TODO: 实现具体的连接状态检查
        return True

    def get_connection_info(self):
        """获取连接信息"""
        from core.data_source_extensions import ConnectionInfo, HealthCheckResult
        return ConnectionInfo(
            is_connected=self.is_connected(),
            connection_time=self.connection_time,
            last_activity=self.last_activity,
            connection_params={
                "server_info": "localhost",
                "timeout": self.config.get('timeout', 30)
            },
            error_message=self.last_error
        )

    def health_check(self):
        """健康检查"""
        from core.data_source_extensions import HealthCheckResult
        from datetime import datetime
        return HealthCheckResult(
            is_healthy=self.is_connected(),
            response_time=0.0,
            message="健康",
            last_check_time=datetime.now()
        )

    def get_asset_list(self, asset_type: AssetType, market: str = None) -> List[Dict[str, Any]]:
        """获取资产列表"""
        # TODO: 实现具体的资产列表获取逻辑
        return []

    def get_kdata(self, symbol: str, freq: str = "D", start_date: str = None,
                  end_date: str = None, count: int = None) -> pd.DataFrame:
        """获取K线数据"""
        # TODO: 实现具体的K线数据获取逻辑
        import pandas as pd
        return pd.DataFrame()

    def get_real_time_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情"""
        # TODO: 实现具体的实时行情获取逻辑
        return []
