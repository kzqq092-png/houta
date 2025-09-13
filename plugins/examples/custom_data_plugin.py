from loguru import logger
"""
自定义数据源插件模板
用户可以基于此模板创建自己的数据源插件
支持CSV、JSON、数据库、API等多种数据源
"""

import json
import csv
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import requests
import pandas as pd

from core.data_source_extensions import IDataSourcePlugin, HealthCheckResult
from core.plugin_types import AssetType, DataType, PluginType
from core.data_source_extensions import IDataSourcePlugin, PluginInfo, HealthCheckResult
from core.plugin_types import AssetType, DataType
from core.data_source_data_models import QueryParams, StockInfo, KlineData, MarketData


class CustomDataPlugin(IDataSourcePlugin):
    """自定义数据源插件模板"""

    def __init__(self):
        self.plugin_id = "examples.custom_data_plugin"  # 添加plugin_id属性
        self.name = "自定义数据源"
        self.version = "1.0.0"
        self.description = "自定义数据源插件模板"
        self.plugin_type = PluginType.DATA_SOURCE_CUSTOM
        self.supported_asset_types = [AssetType.STOCK, AssetType.FUTURES, AssetType.FOREX]
        self.logger = logger

        # 配置信息
        self.config = {
            'data_source_type': 'csv',  # csv, json, database, api, excel
            'file_path': '',
            'api_url': '',
            'database_path': '',
            'table_name': '',
            'api_key': '',
            'headers': {},
            'authentication': {},
            'field_mapping': {
                'symbol': 'symbol',
                'name': 'name',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'timestamp': 'timestamp'
            }
        }

        # 示例数据，实际使用时从外部数据源获取
        self.sample_instruments = {
            'CUSTOM001': {'name': '自定义股票1', 'type': 'stock', 'market': 'CUSTOM'},
            'CUSTOM002': {'name': '自定义期货1', 'type': 'futures', 'market': 'CUSTOM'},
            'CUSTOM003': {'name': '自定义外汇1', 'type': 'forex', 'market': 'CUSTOM'}
        }

        self.initialized = False  # 插件初始化状态
        # 连接状态属性
        self.connection_time = None
        self.last_activity = None
        self.last_error = None
        self.config = {}


    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return self.supported_asset_types

    def configure(self, config: Dict[str, Any]):
        """配置插件参数"""
        self.config.update(config)
        self.logger.info(f"自定义插件配置更新: {config}")

    def _load_from_csv(self, file_path: str) -> List[Dict]:
        """从CSV文件加载数据"""
        try:
            data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            return data
        except Exception as e:
            self.logger.error(f"加载CSV文件失败: {e}")
            return []

    def _load_from_json(self, file_path: str) -> List[Dict]:
        """从JSON文件加载数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else [data]
        except Exception as e:
            self.logger.error(f"加载JSON文件失败: {e}")
            return []

    def _load_from_database(self, db_path: str, table_name: str, query: str = None) -> List[Dict]:
        """从数据库加载数据"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # 返回字典格式

            if query:
                cursor = conn.execute(query)
            else:
                cursor = conn.execute(f"SELECT * FROM {table_name}")

            data = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return data
        except Exception as e:
            self.logger.error(f"加载数据库数据失败: {e}")
            return []

    def _load_from_api(self, api_url: str, params: Dict = None) -> List[Dict]:
        """从API加载数据"""
        try:
            headers = self.config.get('headers', {})
            if self.config.get('api_key'):
                headers['Authorization'] = f"Bearer {self.config['api_key']}"

            response = requests.get(api_url, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else [data]
            else:
                self.logger.warning(f"API请求失败: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"API请求异常: {e}")
            return []

    def _load_from_excel(self, file_path: str, sheet_name: str = None) -> List[Dict]:
        """从Excel文件加载数据"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"加载Excel文件失败: {e}")
            return []

    def _map_fields(self, data: Dict) -> Dict:
        """字段映射"""
        field_mapping = self.config.get('field_mapping', {})
        mapped_data = {}

        for target_field, source_field in field_mapping.items():
            if source_field in data:
                mapped_data[target_field] = data[source_field]

        return mapped_data

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取证券基本信息"""
        try:
            # 从配置的数据源获取数据
            data_source_type = self.config.get('data_source_type', 'csv')

            if data_source_type == 'csv' and self.config.get('file_path'):
                data_list = self._load_from_csv(self.config['file_path'])
            elif data_source_type == 'json' and self.config.get('file_path'):
                data_list = self._load_from_json(self.config['file_path'])
            elif data_source_type == 'database':
                query = f"SELECT * FROM {self.config.get('table_name', 'instruments')} WHERE symbol = '{symbol}'"
                data_list = self._load_from_database(self.config.get('database_path'),
                                                     self.config.get('table_name'), query)
            elif data_source_type == 'api' and self.config.get('api_url'):
                api_url = f"{self.config['api_url']}/instrument/{symbol}"
                data_list = self._load_from_api(api_url)
            elif data_source_type == 'excel' and self.config.get('file_path'):
                data_list = self._load_from_excel(self.config['file_path'])
            else:
                # 使用示例数据
                instrument_info = self.sample_instruments.get(symbol)
                if not instrument_info:
                    return self._get_fallback_stock_info(symbol)

                return StockInfo(
                    code=symbol,
                    name=instrument_info['name'],
                    market=instrument_info['market'],
                    currency='CNY',
                    sector='自定义',
                    industry=instrument_info['type'],
                    list_date=None,
                    extra_info={
                        'data_source': 'Custom',
                        'instrument_type': instrument_info['type']
                    }
                )

            # 处理从外部数据源获取的数据
            for data in data_list:
                mapped_data = self._map_fields(data)
                if mapped_data.get('symbol') == symbol:
                    return StockInfo(
                        code=symbol,
                        name=mapped_data.get('name', symbol),
                        market=mapped_data.get('market', 'CUSTOM'),
                        currency=mapped_data.get('currency', 'CNY'),
                        sector=mapped_data.get('sector', '自定义'),
                        industry=mapped_data.get('industry', '未分类'),
                        list_date=None,
                        extra_info={
                            'data_source': 'Custom',
                            'source_type': data_source_type,
                            'original_data': data
                        }
                    )

            return self._get_fallback_stock_info(symbol)

        except Exception as e:
            self.logger.error(f"获取 {symbol} 证券信息失败: {e}")
            return self._get_fallback_stock_info(symbol)

    def _get_fallback_stock_info(self, symbol: str) -> StockInfo:
        """获取备用证券信息"""
        return StockInfo(
            code=symbol,
            name=f"{symbol} 自定义证券",
            market='CUSTOM',
            currency='CNY',
            sector='自定义',
            industry='未分类',
            list_date=None,
            extra_info={'data_source': 'Custom', 'fallback': True}
        )

    def get_kline_data(self, symbol: str, start_date: datetime,
                       end_date: datetime, frequency: str = "1d") -> List[KlineData]:
        """获取K线数据"""
        try:
            data_source_type = self.config.get('data_source_type', 'csv')

            if data_source_type == 'csv' and self.config.get('file_path'):
                data_list = self._load_from_csv(self.config['file_path'])
            elif data_source_type == 'json' and self.config.get('file_path'):
                data_list = self._load_from_json(self.config['file_path'])
            elif data_source_type == 'database':
                query = f"""
                SELECT * FROM {self.config.get('table_name', 'kline_data')} 
                WHERE symbol = '{symbol}' 
                AND timestamp BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY timestamp
                """
                data_list = self._load_from_database(self.config.get('database_path'),
                                                     self.config.get('table_name'), query)
            elif data_source_type == 'api' and self.config.get('api_url'):
                api_url = f"{self.config['api_url']}/kline/{symbol}"
                params = {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'frequency': frequency
                }
                data_list = self._load_from_api(api_url, params)
            elif data_source_type == 'excel' and self.config.get('file_path'):
                data_list = self._load_from_excel(self.config['file_path'])
            else:
                # 生成示例数据
                return self._get_simulated_kline_data(symbol, start_date, end_date, frequency)

            # 处理获取的数据
            kline_list = []
            for data in data_list:
                mapped_data = self._map_fields(data)

                # 过滤符合条件的数据
                if mapped_data.get('symbol') != symbol:
                    continue

                # 解析时间戳
                timestamp_str = mapped_data.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d')
                        except:
                            continue

                    if timestamp < start_date or timestamp > end_date:
                        continue
                else:
                    continue

                kline_data = KlineData(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=float(mapped_data.get('open', 0)),
                    high=float(mapped_data.get('high', 0)),
                    low=float(mapped_data.get('low', 0)),
                    close=float(mapped_data.get('close', 0)),
                    volume=float(mapped_data.get('volume', 0)),
                    frequency=frequency,
                    extra_info={
                        'data_source': 'Custom',
                        'source_type': data_source_type,
                        'original_data': data
                    }
                )
                kline_list.append(kline_data)

            # 按时间排序
            kline_list.sort(key=lambda x: x.timestamp)
            return kline_list

        except Exception as e:
            self.logger.error(f"获取 {symbol} K线数据失败: {e}")
            return self._get_simulated_kline_data(symbol, start_date, end_date, frequency)

    def _get_simulated_kline_data(self, symbol: str, start_date: datetime,
                                  end_date: datetime, frequency: str) -> List[KlineData]:
        """生成模拟K线数据"""
        import random

        kline_list = []
        current_date = start_date
        base_price = 100.0

        while current_date <= end_date:
            # 模拟价格波动
            price_change = random.uniform(-0.03, 0.03)
            open_price = base_price * (1 + price_change)
            close_price = open_price * (1 + random.uniform(-0.02, 0.02))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.015))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.015))
            volume = random.uniform(10000, 100000)

            kline_data = KlineData(
                symbol=symbol,
                timestamp=current_date,
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=int(volume),
                frequency=frequency,
                extra_info={
                    'data_source': 'Custom',
                    'simulated': True
                }
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
            data_source_type = self.config.get('data_source_type', 'csv')

            if data_source_type == 'api' and self.config.get('api_url'):
                api_url = f"{self.config['api_url']}/market/{symbol}"
                data_list = self._load_from_api(api_url)

                if data_list:
                    data = data_list[0]
                    mapped_data = self._map_fields(data)

                    current_price = float(mapped_data.get('close', 0))
                    open_price = float(mapped_data.get('open', current_price))

                    return MarketData(
                        symbol=symbol,
                        current_price=current_price,
                        open_price=open_price,
                        high_price=float(mapped_data.get('high', current_price)),
                        low_price=float(mapped_data.get('low', current_price)),
                        volume=float(mapped_data.get('volume', 0)),
                        timestamp=datetime.now(),
                        change_amount=current_price - open_price,
                        change_percent=(current_price - open_price) / open_price * 100 if open_price > 0 else 0,
                        extra_info={
                            'data_source': 'Custom',
                            'source_type': data_source_type,
                            'original_data': data
                        }
                    )

            # 生成模拟数据
            return self._get_simulated_market_data(symbol)

        except Exception as e:
            self.logger.error(f"获取 {symbol} 实时数据失败: {e}")
            return self._get_simulated_market_data(symbol)

    def _get_simulated_market_data(self, symbol: str) -> MarketData:
        """生成模拟市场数据"""

        base_price = 100.0
        current_price = base_price * (1 + random.uniform(-0.02, 0.02))
        open_price = current_price * (1 + random.uniform(-0.01, 0.01))

        return MarketData(
            symbol=symbol,
            current_price=round(current_price, 2),
            open_price=round(open_price, 2),
            high_price=round(current_price * 1.015, 2),
            low_price=round(current_price * 0.985, 2),
            volume=random.randint(10000, 100000),
            timestamp=datetime.now(),
            change_amount=round(current_price - open_price, 2),
            change_percent=round((current_price - open_price) / open_price * 100, 2),
            extra_info={
                'data_source': 'Custom',
                'simulated': True
            }
        )

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        try:
            data_source_type = self.config.get('data_source_type', 'csv')

            # 检查数据源配置
            if data_source_type == 'csv' or data_source_type == 'json' or data_source_type == 'excel':
                file_path = self.config.get('file_path')
                if file_path:
                    import os
                    if os.path.exists(file_path):
                        return HealthCheckResult(
                            is_healthy=True,
                            message=f"自定义数据源 ({data_source_type}) 连接正常",
                            response_time=50,
                            extra_info={
                                'source_type': data_source_type,
                                'file_path': file_path,
                                'instruments_count': len(self.sample_instruments)
                            }
                        )
                    else:
                        return HealthCheckResult(
                            is_healthy=False,
                            message=f"文件不存在: {file_path}",
                            response_time=0,
                            extra_info={'source_type': data_source_type}
                        )
            elif data_source_type == 'database':
                db_path = self.config.get('database_path')
                if db_path:
                    if os.path.exists(db_path):
                        return HealthCheckResult(
                            is_healthy=True,
                            message="自定义数据源 (数据库) 连接正常",
                            response_time=80,
                            extra_info={
                                'source_type': 'database',
                                'database_path': db_path,
                                'table_name': self.config.get('table_name')
                            }
                        )
            elif data_source_type == 'api':
                api_url = self.config.get('api_url')
                if api_url:
                    try:
                        response = requests.get(f"{api_url}/health", timeout=10)
                        if response.status_code == 200:
                            return HealthCheckResult(
                                is_healthy=True,
                                message="自定义数据源 (API) 连接正常",
                                response_time=response.elapsed.total_seconds() * 1000,
                                extra_info={
                                    'source_type': 'api',
                                    'api_url': api_url,
                                    'api_status': response.status_code
                                }
                            )
                    except:
                        pass

            # 默认返回配置状态
            return HealthCheckResult(
                is_healthy=True,
                message="自定义数据源配置正常（使用模拟数据）",
                response_time=30,
                extra_info={
                    'source_type': data_source_type,
                    'config_status': 'simulated',
                    'instruments_count': len(self.sample_instruments)
                }
            )

        except Exception as e:
            self.logger.error(f"自定义数据源健康检查失败: {e}")
            return HealthCheckResult(
                is_healthy=False,
                message=f"健康检查异常: {str(e)}",
                response_time=0,
                extra_info={'error': str(e)}
            )

    def get_plugin_info(self) -> PluginInfo:
        """获取插件基本信息"""
        return PluginInfo(
            id="custom_data",
            name="自定义数据源",
            version=self.version,
            description=self.description,
            author="FactorWeave-Quant 团队",
            supported_asset_types=[AssetType.STOCK, AssetType.FUTURES, AssetType.FOREX],
            supported_data_types=[DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE],
            capabilities={
                "markets": ["custom", "multi"],
                "asset_types": ["stock", "futures", "forex"],
                "frequencies": ["1m", "5m", "15m", "30m", "60m", "D"],
                "real_time_support": True,
                "historical_data": True,
                "custom_formats": True
            }
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

    def is_connected(self) -> bool:
        """检查连接状态"""
        return getattr(self, 'initialized', False)

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
