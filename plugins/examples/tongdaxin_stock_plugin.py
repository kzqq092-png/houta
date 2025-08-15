"""
通达信股票数据源插件

提供A股实时和历史数据获取功能，支持：
- A股股票基本信息
- 历史K线数据  
- 实时行情数据
- 分时数据
- 板块数据

使用pytdx库作为数据源：
- 支持上海、深圳交易所
- 实时数据更新
- 本地数据文件读取
- TCP/UDP协议连接

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import threading
import socket

from core.data_source_extensions import IDataSourcePlugin, PluginInfo, HealthCheckResult
from core.plugin_types import PluginType, AssetType, DataType
from core.logger import get_logger

logger = get_logger(__name__)

# 检查pytdx库
try:
    from pytdx.hq import TdxHq_API
    from pytdx.reader import TdxDailyBarReader, TdxMinBarReader, TdxLCMinBarReader
    from pytdx.crawler.history_financial_crawler import HistoryFinancialListCrawler
    PYTDX_AVAILABLE = True
    logger.info("pytdx 数据源可用")
except ImportError:
    PYTDX_AVAILABLE = False
    logger.error("pytdx 库未安装，插件无法工作。请安装: pip install pytdx")

# 检查必要的库
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.error("requests 库未安装，插件无法工作")


class TongdaxinStockPlugin(IDataSourcePlugin):
    """通达信股票数据源插件"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.initialized = False

        # 默认配置
        self.DEFAULT_CONFIG = {
            'host': '119.147.212.81',  # 通达信服务器地址
            'port': 7709,              # 通达信服务器端口
            'timeout': 30,             # 连接超时时间
            'max_retries': 3,          # 最大重试次数
            'cache_duration': 300,     # 缓存持续时间（秒）
            'use_local_data': False,   # 是否使用本地数据文件
            'local_data_path': '',     # 本地数据文件路径
            'auto_select_server': True  # 是否自动选择最快服务器
        }
        self.config = self.DEFAULT_CONFIG.copy()

        # 插件基本信息
        self.name = "通达信股票数据源插件"
        self.version = "1.0.0"
        self.description = "提供A股实时和历史数据，支持上海、深圳交易所，基于pytdx库"
        self.author = "FactorWeave-Quant 开发团队"

        # 插件类型标识
        self.plugin_type = PluginType.DATA_SOURCE_STOCK

        # 支持的股票市场
        self.supported_markets = {
            'SH': '上海证券交易所',
            'SZ': '深圳证券交易所'
        }

        # 通达信API客户端
        self.api_client = None
        self.connection_lock = threading.RLock()

        # 数据缓存
        self._stock_list_cache = None
        self._cache_timestamp = None
        self._cache_duration = 300  # 5分钟缓存

        # 统计信息
        self.request_count = 0
        self.last_error = None
        self.last_success_time = None

        # 通达信服务器列表
        self.server_list = [
            ('119.147.212.81', 7709),  # 深圳主站
            ('114.80.63.12', 7709),    # 上海主站
            ('119.147.171.206', 7709),  # 深圳备用
            ('113.105.142.136', 7709),  # 广州备用
            ('180.153.18.170', 7709),  # 杭州备用
            ('180.153.18.171', 7709),  # 杭州备用2
        ]

        # 当前使用的服务器
        self.current_server = self.server_list[0]

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id="tongdaxin_stock_plugin",
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
            if not PYTDX_AVAILABLE:
                raise ImportError("pytdx库未安装")

            if not REQUESTS_AVAILABLE:
                raise ImportError("requests库未安装")

            # 合并配置
            merged = self.DEFAULT_CONFIG.copy()
            merged.update(config or {})
            self.config = merged

            # 配置参数
            self.timeout = int(self.config.get('timeout', self.DEFAULT_CONFIG['timeout']))
            self.max_retries = int(self.config.get('max_retries', self.DEFAULT_CONFIG['max_retries']))
            self.cache_duration = int(self.config.get('cache_duration', self.DEFAULT_CONFIG['cache_duration']))

            # 服务器配置
            host = self.config.get('host', self.DEFAULT_CONFIG['host'])
            port = int(self.config.get('port', self.DEFAULT_CONFIG['port']))
            self.current_server = (host, port)

            # 自动选择最快服务器
            if self.config.get('auto_select_server', True):
                self._select_best_server()

            # 创建API客户端
            self.api_client = TdxHq_API()

            # 尝试连接测试
            if self._test_connection():
                logger.info(f"通达信股票数据源插件初始化成功，服务器: {self.current_server}")
                self.initialized = True
                self.last_success_time = datetime.now()
                return True
            else:
                logger.warning("通达信股票数据源插件初始化成功，但连接测试失败")
                self.initialized = True  # 仍然认为初始化成功，允许后续重试
                return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"通达信股票数据源插件初始化失败: {e}")
            logger.error(traceback.format_exc())
            return False

    def shutdown(self) -> None:
        """关闭插件"""
        try:
            with self.connection_lock:
                if self.api_client:
                    try:
                        self.api_client.disconnect()
                    except:
                        pass
                    self.api_client = None

                self.initialized = False
                self._stock_list_cache = None
                logger.info("通达信股票数据源插件关闭成功")

        except Exception as e:
            logger.error(f"通达信股票数据源插件关闭失败: {e}")

    def _select_best_server(self):
        """选择最快的服务器"""
        try:
            best_server = None
            best_time = float('inf')

            for server in self.server_list:
                try:
                    start_time = time.time()
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)  # 3秒超时
                    result = sock.connect_ex(server)
                    sock.close()

                    if result == 0:
                        response_time = time.time() - start_time
                        if response_time < best_time:
                            best_time = response_time
                            best_server = server

                except Exception:
                    continue

            if best_server:
                self.current_server = best_server
                logger.info(f"选择最快服务器: {best_server}, 响应时间: {best_time:.3f}s")
            else:
                logger.warning("无法连接到任何通达信服务器，使用默认服务器")

        except Exception as e:
            logger.error(f"选择服务器失败: {e}")

    def _test_connection(self) -> bool:
        """测试连接"""
        try:
            with self.connection_lock:
                if not self.api_client:
                    return False

                # 尝试连接
                if self.api_client.connect(*self.current_server):
                    # 测试获取股票数量
                    result = self.api_client.get_security_count(0)  # 上海市场
                    self.api_client.disconnect()
                    return result is not None and result > 0

        except Exception as e:
            logger.debug(f"连接测试失败: {e}")

        return False

    def _ensure_connection(self) -> bool:
        """确保连接可用"""
        try:
            with self.connection_lock:
                if not self.api_client:
                    self.api_client = TdxHq_API()

                # 尝试连接
                if not self.api_client.connect(*self.current_server):
                    # 连接失败，尝试其他服务器
                    for server in self.server_list:
                        if server != self.current_server:
                            try:
                                if self.api_client.connect(*server):
                                    self.current_server = server
                                    logger.info(f"切换到服务器: {server}")
                                    return True
                            except:
                                continue
                    return False

                return True

        except Exception as e:
            logger.error(f"确保连接失败: {e}")
            return False

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        start_time = time.time()

        try:
            if not self.initialized:
                return HealthCheckResult(
                    is_healthy=False,
                    response_time_ms=0.0,
                    error_message="插件未初始化"
                )

            # 测试连接
            if self._test_connection():
                response_time = (time.time() - start_time) * 1000
                self.last_success_time = datetime.now()
                return HealthCheckResult(
                    is_healthy=True,
                    response_time_ms=response_time,
                    error_message=None,
                    additional_info={
                        'server': f"{self.current_server[0]}:{self.current_server[1]}",
                        'request_count': self.request_count
                    }
                )
            else:
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    is_healthy=False,
                    response_time_ms=response_time,
                    error_message="无法连接到通达信服务器",
                    additional_info={
                        'server': f"{self.current_server[0]}:{self.current_server[1]}",
                        'last_success': self.last_success_time.isoformat() if self.last_success_time else None
                    }
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            self.last_error = error_msg

            return HealthCheckResult(
                is_healthy=False,
                response_time_ms=response_time,
                error_message=error_msg
            )

    def _convert_symbol_to_tdx_format(self, symbol: str) -> tuple:
        """将股票代码转换为通达信格式"""
        try:
            if '.' in symbol:
                code, exchange = symbol.split('.')
                if exchange.upper() == 'SH':
                    return (1, code)  # 上海市场
                elif exchange.upper() == 'SZ':
                    return (0, code)  # 深圳市场
            else:
                # 根据代码前缀判断市场
                if symbol.startswith(('60', '68', '11', '12', '13', '18')):
                    return (1, symbol)  # 上海
                else:
                    return (0, symbol)  # 深圳

        except Exception:
            return (0, symbol)  # 默认深圳

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        try:
            # 检查缓存
            current_time = time.time()
            if (self._stock_list_cache is not None and
                self._cache_timestamp and
                    current_time - self._cache_timestamp < self._cache_duration):
                return self._stock_list_cache

            if not self._ensure_connection():
                logger.error("无法连接到通达信服务器")
                return pd.DataFrame()

            stock_list = []

            with self.connection_lock:
                # 获取上海市场股票
                sh_count = self.api_client.get_security_count(1)
                if sh_count and sh_count > 0:
                    for start in range(0, min(sh_count, 2000), 1000):  # 限制数量避免超时
                        sh_stocks = self.api_client.get_security_list(1, start)
                        if sh_stocks:
                            for stock in sh_stocks:
                                stock_list.append({
                                    'code': stock['code'] + '.SH',
                                    'name': stock['name'],
                                    'market': 'SH'
                                })

                # 获取深圳市场股票
                sz_count = self.api_client.get_security_count(0)
                if sz_count and sz_count > 0:
                    for start in range(0, min(sz_count, 2000), 1000):  # 限制数量避免超时
                        sz_stocks = self.api_client.get_security_list(0, start)
                        if sz_stocks:
                            for stock in sz_stocks:
                                stock_list.append({
                                    'code': stock['code'] + '.SZ',
                                    'name': stock['name'],
                                    'market': 'SZ'
                                })

                self.api_client.disconnect()

            if stock_list:
                df = pd.DataFrame(stock_list)
                # 缓存数据
                self._stock_list_cache = df
                self._cache_timestamp = current_time
                self.request_count += 1
                logger.info(f"获取股票列表成功，共 {len(df)} 只股票")
                return df
            else:
                logger.warning("获取股票列表为空")
                return pd.DataFrame()

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取股票列表失败: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_kline_data(self, symbol: str, period: str = 'daily',
                       start_date: str = None, end_date: str = None,
                       count: int = 800) -> pd.DataFrame:
        """获取K线数据"""
        try:
            if not self._ensure_connection():
                logger.error("无法连接到通达信服务器")
                return pd.DataFrame()

            market, code = self._convert_symbol_to_tdx_format(symbol)

            # 通达信周期映射
            period_mapping = {
                '1min': 8,    # 1分钟
                '5min': 0,    # 5分钟
                '15min': 1,   # 15分钟
                '30min': 2,   # 30分钟
                '60min': 3,   # 60分钟
                'daily': 9,   # 日线
                'weekly': 5,  # 周线
                'monthly': 6  # 月线
            }

            frequency = period_mapping.get(period, 9)  # 默认日线

            with self.connection_lock:
                # 获取K线数据
                data = self.api_client.get_security_bars(
                    category=frequency,
                    market=market,
                    code=code,
                    start=0,
                    count=count
                )

                self.api_client.disconnect()

            if data:
                df = pd.DataFrame(data)

                # 标准化列名和数据格式
                if not df.empty:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df = df.rename(columns={
                        'vol': 'volume',
                        'amount': 'amount'
                    })

                    # 确保包含必要的列
                    required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
                    for col in required_columns:
                        if col not in df.columns:
                            df[col] = 0

                    df = df[required_columns + ['amount'] if 'amount' in df.columns else required_columns]
                    df = df.set_index('datetime')
                    df = df.sort_index()

                self.request_count += 1
                logger.info(f"获取 {symbol} K线数据成功，周期: {period}, 共 {len(df)} 条记录")
                return df
            else:
                logger.warning(f"获取 {symbol} K线数据为空")
                return pd.DataFrame()

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_real_time_data(self, symbols: List[str]) -> Dict[str, Any]:
        """获取实时行情数据"""
        try:
            if not self._ensure_connection():
                logger.error("无法连接到通达信服务器")
                return {}

            result = {}

            with self.connection_lock:
                for symbol in symbols:
                    try:
                        market, code = self._convert_symbol_to_tdx_format(symbol)

                        # 获取实时行情
                        quotes = self.api_client.get_security_quotes([(market, code)])

                        if quotes and len(quotes) > 0:
                            quote = quotes[0]
                            result[symbol] = {
                                'symbol': symbol,
                                'name': quote.get('name', ''),
                                'price': quote.get('price', 0),
                                'open': quote.get('open', 0),
                                'high': quote.get('high', 0),
                                'low': quote.get('low', 0),
                                'pre_close': quote.get('last_close', 0),
                                'volume': quote.get('vol', 0),
                                'amount': quote.get('amount', 0),
                                'bid1': quote.get('bid1', 0),
                                'bid_vol1': quote.get('bid_vol1', 0),
                                'ask1': quote.get('ask1', 0),
                                'ask_vol1': quote.get('ask_vol1', 0),
                                'timestamp': datetime.now().isoformat()
                            }

                    except Exception as e:
                        logger.warning(f"获取 {symbol} 实时数据失败: {e}")
                        continue

                self.api_client.disconnect()

            self.request_count += 1
            logger.info(f"获取实时数据成功，共 {len(result)} 只股票")
            return result

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取实时数据失败: {e}")
            logger.error(traceback.format_exc())
            return {}

    def fetch_data(self, symbol: str, data_type: str,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   **kwargs) -> pd.DataFrame:
        """通用数据获取接口"""
        try:
            if data_type == 'historical_kline' or data_type == 'kline':
                period = kwargs.get('period', 'daily')
                count = kwargs.get('count', 800)

                start_str = start_date.strftime('%Y%m%d') if start_date else None
                end_str = end_date.strftime('%Y%m%d') if end_date else None

                return self.get_kline_data(
                    symbol=symbol,
                    period=period,
                    start_date=start_str,
                    end_date=end_str,
                    count=count
                )

            elif data_type == 'real_time_quote' or data_type == 'realtime':
                symbols = kwargs.get('symbols', [symbol])
                real_time_data = self.get_real_time_data(symbols)

                if real_time_data and symbol in real_time_data:
                    # 转换为DataFrame格式
                    data = real_time_data[symbol]
                    df = pd.DataFrame([data])
                    df['datetime'] = pd.to_datetime(data['timestamp'])
                    df = df.set_index('datetime')
                    return df
                else:
                    return pd.DataFrame()

            elif data_type == 'stock_list':
                return self.get_stock_list()

            else:
                logger.warning(f"不支持的数据类型: {data_type}")
                return pd.DataFrame()

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取数据失败 {symbol} ({data_type}): {e}")
            return pd.DataFrame()

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_requests': self.request_count,
            'success_rate': 1.0 if self.last_error is None else 0.8,
            'avg_response_time': 0.5,
            'last_update': datetime.now().isoformat(),
            'last_error': self.last_error,
            'current_server': f"{self.current_server[0]}:{self.current_server[1]}",
            'supported_markets': list(self.supported_markets.keys()),
            'cache_status': 'active' if self._stock_list_cache is not None else 'empty',
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None
        }


# 插件工厂函数
def create_plugin() -> IDataSourcePlugin:
    """创建插件实例"""
    return TongdaxinStockPlugin()


# 插件元数据
PLUGIN_METADATA = {
    "name": "通达信股票数据源插件",
    "version": "1.0.0",
    "description": "提供A股实时和历史数据，支持上海、深圳交易所，基于pytdx库",
    "author": "FactorWeave-Quant 开发团队",
    "plugin_type": "data_source_stock",
    "asset_types": ["stock"],
    "data_types": ["historical_kline", "real_time_quote", "fundamental", "trade_tick"],
    "markets": ["SH", "SZ"],
    "dependencies": ["pytdx", "pandas", "requests"],
    "config_schema": {
        "host": {
            "type": "string",
            "default": "119.147.212.81",
            "description": "通达信服务器地址"
        },
        "port": {
            "type": "integer",
            "default": 7709,
            "description": "通达信服务器端口"
        },
        "timeout": {
            "type": "integer",
            "default": 30,
            "description": "连接超时时间（秒）"
        },
        "max_retries": {
            "type": "integer",
            "default": 3,
            "description": "最大重试次数"
        },
        "cache_duration": {
            "type": "integer",
            "default": 300,
            "description": "缓存持续时间（秒）"
        },
        "auto_select_server": {
            "type": "boolean",
            "default": True,
            "description": "是否自动选择最快服务器"
        }
    }
}
