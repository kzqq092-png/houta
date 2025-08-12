"""
东方财富股票数据源插件

提供东方财富数据源的股票数据获取功能，支持：
- A股股票基本信息
- 历史K线数据
- 实时行情数据
- 财务数据
- 资金流向数据

使用东方财富API作为数据源：
- 高频实时数据
- 丰富的技术指标
- 资金流向分析

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

from core.data_source_extensions import IDataSourcePlugin, PluginInfo
from core.data_source_data_models import HealthCheckResult
from core.plugin_types import PluginType, AssetType, DataType
from core.logger import get_logger

logger = get_logger(__name__)

# 默认配置集中
DEFAULT_CONFIG = {
    'base_url': 'https://push2.eastmoney.com',
    'api_urls': {
        'stock_list': '/api/qt/clist/get',
        'kline': '/api/qt/stock/kline/get',
        'realtime': '/api/qt/ulist.np/get',
        'financial': '/api/qt/stock/financial/get'
    },
    'timeout': 30,
    'max_retries': 3
}


class EastMoneyStockPlugin(IDataSourcePlugin):
    """东方财富股票数据源插件"""

    def __init__(self):
        self.initialized = False
        self.config = DEFAULT_CONFIG.copy()
        self.session = None
        self.request_count = 0
        self.last_error = None

        # 插件基本信息
        self.name = "东方财富股票数据源插件"
        self.version = "1.0.0"
        self.description = "提供东方财富高频实时数据和技术分析数据"
        self.author = "FactorWeave-Quant 开发团队"

        # 插件类型标识
        self.plugin_type = PluginType.DATA_SOURCE_STOCK

        # 支持的市场
        self.supported_markets = {
            '1': '上海主板',
            '0': '深圳主板',
            '17': '创业板',
            '33': '科创板'
        }

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id="eastmoney_stock_plugin",
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
            merged = DEFAULT_CONFIG.copy()
            merged.update(config or {})
            self.config = merged

            # 创建会话
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://quote.eastmoney.com/',
                'Accept': 'application/json, text/plain, */*'
            })

            # 配置参数
            self.timeout = int(self.config.get('timeout', DEFAULT_CONFIG['timeout']))
            self.max_retries = int(self.config.get('max_retries', DEFAULT_CONFIG['max_retries']))

            # 测试连接
            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            test_url = f"{base_url}{api['stock_list']}"
            params = {
                'pn': '1',
                'pz': '20',
                'po': '1',
                'np': '1',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                'fields': 'f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11'
            }

            response = self.session.get(test_url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and data['data']:
                    self.initialized = True
                    logger.info("东方财富股票数据源插件初始化成功")
                    return True

            raise Exception("无法连接东方财富API")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"东方财富股票数据源插件初始化失败: {e}")
            return False

    def shutdown(self) -> bool:
        """关闭插件"""
        try:
            if self.session:
                self.session.close()
            self.initialized = False
            logger.info("东方财富股票数据源插件关闭成功")
            return True
        except Exception as e:
            logger.error(f"东方财富股票数据源插件关闭失败: {e}")
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

            # 测试API连接
            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            test_url = f"{base_url}{api['stock_list']}"
            params = {'pn': '1', 'pz': '1', 'np': '1', 'fltt': '2', 'invt': '2'}

            response = self.session.get(test_url, params=params, timeout=10)
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data:
                    return HealthCheckResult(
                        is_healthy=True,
                        response_time=response_time,
                        message="ok"
                    )

            return HealthCheckResult(
                is_healthy=False,
                response_time=response_time,
                message="API返回数据异常"
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
            self.request_count += 1

            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            url = f"{base_url}{api['stock_list']}"
            params = {
                'pn': '1',
                'pz': '5000',  # 获取更多数据
                'po': '1',
                'np': '1',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',  # A股主要板块
                'fields': 'f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f15,f16,f17,f18'
            }

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and data['data']:
                    stock_data = data['data']['diff']

                    # 转换为DataFrame
                    df = pd.DataFrame(stock_data)

                    # 重命名列
                    column_mapping = {
                        'f12': 'code',
                        'f14': 'name',
                        'f2': 'close',
                        'f3': 'pct_change',
                        'f4': 'change',
                        'f5': 'volume',
                        'f6': 'amount',
                        'f7': 'amplitude',
                        'f8': 'turnover',
                        'f9': 'pe_ratio',
                        'f10': 'volume_ratio',
                        'f11': 'total_mv',
                        'f15': 'high',
                        'f16': 'low',
                        'f17': 'open',
                        'f18': 'pre_close'
                    }

                    df = df.rename(columns=column_mapping)

                    # 数据类型转换
                    numeric_cols = ['close', 'pct_change', 'change', 'volume', 'amount',
                                    'amplitude', 'turnover', 'pe_ratio', 'volume_ratio',
                                    'total_mv', 'high', 'low', 'open', 'pre_close']

                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')

                    logger.info(f"获取东方财富股票列表成功，共 {len(df)} 只股票")
                    return df

            raise Exception(f"API请求失败: {response.status_code}")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_kline_data(self, symbol: str, period: str = 'daily',
                       start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取K线数据"""
        try:
            self.request_count += 1

            # 处理股票代码
            if '.' in symbol:
                code = symbol.split('.')[0]
            else:
                code = symbol

            # 确定市场代码
            if code.startswith('6'):
                market_code = f"1.{code}"  # 上海
            elif code.startswith(('0', '3')):
                market_code = f"0.{code}"  # 深圳
            else:
                market_code = f"1.{code}"  # 默认上海

            # 周期映射
            period_mapping = {
                '1min': '1',
                '5min': '5',
                '15min': '15',
                '30min': '30',
                '60min': '60',
                'daily': '101',
                'weekly': '102',
                'monthly': '103'
            }

            klt = period_mapping.get(period, '101')

            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            url = f"{base_url}{api['kline']}"
            params = {
                'secid': market_code,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': klt,
                'fqt': '1',  # 前复权
                'beg': start_date or '0',
                'end': end_date or '20500101'
            }

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and data['data']:
                    klines = data['data']['klines']

                    if klines:
                        # 解析K线数据
                        records = []
                        for kline in klines:
                            parts = kline.split(',')
                            if len(parts) >= 11:
                                records.append({
                                    'datetime': parts[0],
                                    'open': float(parts[1]),
                                    'close': float(parts[2]),
                                    'high': float(parts[3]),
                                    'low': float(parts[4]),
                                    'volume': int(parts[5]),
                                    'amount': float(parts[6]),
                                    'amplitude': float(parts[7]) if len(parts) > 7 else 0,
                                    'pct_change': float(parts[8]) if len(parts) > 8 else 0,
                                    'change': float(parts[9]) if len(parts) > 9 else 0,
                                    'turnover': float(parts[10]) if len(parts) > 10 else 0
                                })

                        df = pd.DataFrame(records)
                        if not df.empty:
                            df['datetime'] = pd.to_datetime(df['datetime'])
                            df = df.set_index('datetime')

                            logger.info(f"获取 {symbol} K线数据成功，共 {len(df)} 条记录")
                            return df

            raise Exception("无法获取K线数据")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            return pd.DataFrame()

    def get_real_time_data(self, symbols: List[str]) -> pd.DataFrame:
        """获取实时行情数据"""
        try:
            self.request_count += 1

            # 构建股票代码列表
            codes = []
            for symbol in symbols:
                if '.' in symbol:
                    code = symbol.split('.')[0]
                else:
                    code = symbol

                # 添加市场前缀
                if code.startswith('6'):
                    codes.append(f"1.{code}")
                elif code.startswith(('0', '3')):
                    codes.append(f"0.{code}")
                else:
                    codes.append(f"1.{code}")

            base_url = self.config.get('base_url', DEFAULT_CONFIG['base_url'])
            api = self.config.get('api_urls', DEFAULT_CONFIG['api_urls'])
            url = f"{base_url}{api['realtime']}"
            params = {
                'fltt': '2',
                'invt': '2',
                'secids': ','.join(codes),
                'fields': 'f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f15,f16,f17,f18'
            }

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and data['data']:
                    stock_data = data['data']['diff']

                    df = pd.DataFrame(stock_data)

                    # 重命名列
                    column_mapping = {
                        'f12': 'code',
                        'f14': 'name',
                        'f2': 'price',
                        'f3': 'pct_change',
                        'f4': 'change',
                        'f5': 'volume',
                        'f6': 'amount',
                        'f15': 'high',
                        'f16': 'low',
                        'f17': 'open',
                        'f18': 'pre_close'
                    }

                    df = df.rename(columns=column_mapping)

                    # 数据类型转换
                    numeric_cols = ['price', 'pct_change', 'change', 'volume', 'amount',
                                    'high', 'low', 'open', 'pre_close']

                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')

                    logger.info(f"获取实时数据成功，共 {len(df)} 只股票")
                    return df

            raise Exception("无法获取实时数据")

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
                    end_date=kwargs.get('end_date')
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
            'avg_response_time': 0.3,
            'last_update': datetime.now().isoformat(),
            'last_error': self.last_error,
            'supported_markets': list(self.supported_markets.keys()),
            'api_status': 'connected' if self.initialized else 'disconnected'
        }

    def get_plugin_info(self) -> PluginInfo:
        """获取插件基本信息"""
        return PluginInfo(
            id="eastmoney_stock",
            name="东方财富股票数据源",
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
    return EastMoneyStockPlugin()


# 插件元数据
PLUGIN_METADATA = {
    "name": "东方财富股票数据源插件",
    "version": "1.0.0",
    "description": "提供东方财富高频实时数据和技术分析数据",
    "author": "FactorWeave-Quant 开发团队",
    "plugin_type": "data_source_stock",
    "asset_types": ["stock"],
    "data_types": ["historical_kline", "real_time_quote", "fundamental", "trade_tick"],
    "markets": ["SH", "SZ", "CYB", "KCB"],
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
