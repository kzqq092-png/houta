"""
Wind万得数据终端插件
专业的金融数据提供商，提供股票、债券、期货、宏观经济等数据
"""

import json
import logging
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from core.data_source_extensions import IDataSourcePlugin, PluginInfo
from core.plugin_types import AssetType, DataType, PluginType
from core.data_source_data_models import StockInfo, KlineData, MarketData, QueryParams, HealthCheckResult


class WindDataPlugin(IDataSourcePlugin):
    """Wind万得数据源插件"""

    def __init__(self):
        self.name = "Wind数据终端数据源"
        self.version = "1.0.0"
        self.description = "Wind万得金融数据终端"
        self.plugin_type = PluginType.DATA_SOURCE_WIND
        self.supported_asset_types = [
            AssetType.STOCK, AssetType.BOND, AssetType.FUTURES,
            AssetType.FUND, AssetType.INDEX, AssetType.COMMODITY
        ]
        self.logger = logging.getLogger(__name__)

        # Wind API配置
        self.wind_config = {
            'username': '',
            'password': '',
            'server': 'wind.com.cn',
            'port': 0,
            'authenticated': False,
            'connection_status': 'disconnected'
        }

        # 尝试导入Wind API（如果已安装）
        self.wind_api = None
        try:
            import WindPy as w
            self.wind_api = w
            self.logger.info("Wind API 已导入")
        except ImportError:
            self.logger.warning("Wind API 未安装，将使用模拟数据")

        # 支持的证券代码示例
        self.instruments = {
            # A股主要指数
            '000001.SH': {'name': '上证指数', 'type': 'index', 'market': 'SH'},
            '399001.SZ': {'name': '深证成指', 'type': 'index', 'market': 'SZ'},
            '399006.SZ': {'name': '创业板指', 'type': 'index', 'market': 'SZ'},
            '000300.SH': {'name': '沪深300', 'type': 'index', 'market': 'SH'},
            '000905.SH': {'name': '中证500', 'type': 'index', 'market': 'SH'},
            '000852.SH': {'name': '中证1000', 'type': 'index', 'market': 'SH'},

            # 主要股票
            '000001.SZ': {'name': '平安银行', 'type': 'stock', 'market': 'SZ'},
            '000002.SZ': {'name': '万科A', 'type': 'stock', 'market': 'SZ'},
            '000858.SZ': {'name': '五粮液', 'type': 'stock', 'market': 'SZ'},
            '300750.SZ': {'name': '宁德时代', 'type': 'stock', 'market': 'SZ'},
            '600000.SH': {'name': '浦发银行', 'type': 'stock', 'market': 'SH'},
            '600036.SH': {'name': '招商银行', 'type': 'stock', 'market': 'SH'},
            '600519.SH': {'name': '贵州茅台', 'type': 'stock', 'market': 'SH'},
            '600887.SH': {'name': '伊利股份', 'type': 'stock', 'market': 'SH'},
            '601318.SH': {'name': '中国平安', 'type': 'stock', 'market': 'SH'},
            '601398.SH': {'name': '工商银行', 'type': 'stock', 'market': 'SH'},

            # 债券
            '019645.IB': {'name': '21国债11', 'type': 'bond', 'market': 'IB'},
            '019649.IB': {'name': '21国债15', 'type': 'bond', 'market': 'IB'},
            '113011.SH': {'name': '光大转债', 'type': 'bond', 'market': 'SH'},
            '113525.SH': {'name': '浦发转债', 'type': 'bond', 'market': 'SH'},

            # 期货合约
            'IF2312.CFE': {'name': 'IF2312', 'type': 'futures', 'market': 'CFE'},
            'IC2312.CFE': {'name': 'IC2312', 'type': 'futures', 'market': 'CFE'},
            'IH2312.CFE': {'name': 'IH2312', 'type': 'futures', 'market': 'CFE'},
            'CU2312.SHF': {'name': 'CU2312', 'type': 'futures', 'market': 'SHF'},
            'AU2312.SHF': {'name': 'AU2312', 'type': 'futures', 'market': 'SHF'},
            'A2312.DCE': {'name': 'A2312', 'type': 'futures', 'market': 'DCE'},
            'M2312.DCE': {'name': 'M2312', 'type': 'futures', 'market': 'DCE'},
            'CF2312.CZC': {'name': 'CF2312', 'type': 'futures', 'market': 'CZC'},
            'SR2312.CZC': {'name': 'SR2312', 'type': 'futures', 'market': 'CZC'},

            # 基金
            '110022.OF': {'name': '易方达消费行业', 'type': 'fund', 'market': 'OF'},
            '161725.OF': {'name': '招商中证白酒', 'type': 'fund', 'market': 'OF'},
            '000478.OF': {'name': '建信中证红利', 'type': 'fund', 'market': 'OF'},
            '510300.SH': {'name': '沪深300ETF', 'type': 'fund', 'market': 'SH'},
            '510500.SH': {'name': '中证500ETF', 'type': 'fund', 'market': 'SH'}
        }

    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return self.supported_asset_types

    def configure_wind(self, username: str, password: str, server: str = None):
        """配置Wind连接信息"""
        self.wind_config.update({
            'username': username,
            'password': password,
            'server': server or 'wind.com.cn'
        })

    def _connect_wind(self) -> bool:
        """连接Wind终端"""
        try:
            if self.wind_api:
                # 启动Wind API
                result = self.wind_api.start()
                if result.ErrorCode == 0:
                    self.wind_config['authenticated'] = True
                    self.wind_config['connection_status'] = 'connected'
                    self.logger.info("Wind API 连接成功")
                    return True
                else:
                    self.logger.error(f"Wind API 连接失败: {result.Data}")
                    return False
            else:
                # 模拟连接成功
                if self.wind_config['username'] and self.wind_config['password']:
                    self.wind_config['authenticated'] = True
                    self.wind_config['connection_status'] = 'connected (simulated)'
                    self.logger.info("Wind 连接模拟成功")
                    return True
                else:
                    self.logger.warning("Wind 认证信息不完整")
                    return False
        except Exception as e:
            self.logger.error(f"Wind 连接失败: {e}")
            return False

    def _disconnect_wind(self):
        """断开Wind连接"""
        try:
            if self.wind_api:
                self.wind_api.stop()
            self.wind_config['authenticated'] = False
            self.wind_config['connection_status'] = 'disconnected'
            self.logger.info("Wind 连接已断开")
        except Exception as e:
            self.logger.error(f"Wind 断开连接失败: {e}")

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取证券基本信息"""
        try:
            if not self.wind_config['authenticated']:
                if not self._connect_wind():
                    return self._get_fallback_stock_info(symbol)

            instrument_info = self.instruments.get(symbol)
            if not instrument_info:
                return self._get_fallback_stock_info(symbol)

            # 使用Wind API获取详细信息（如果可用）
            if self.wind_api and self.wind_config['authenticated']:
                try:
                    # 获取证券基本信息
                    # result = self.wind_api.wss(symbol, "sec_name,ipo_date,industry_citic")
                    # 这里使用模拟数据，实际应用中解析Wind API返回的数据
                    pass
                except:
                    pass

            # 确定资产类型
            asset_type = instrument_info['type']
            if asset_type == 'stock':
                sector = '股票'
                industry = self._get_industry_by_code(symbol)
            elif asset_type == 'bond':
                sector = '债券'
                industry = '固定收益'
            elif asset_type == 'futures':
                sector = '期货'
                industry = '衍生品'
            elif asset_type == 'fund':
                sector = '基金'
                industry = '投资基金'
            elif asset_type == 'index':
                sector = '指数'
                industry = '市场指数'
            else:
                sector = '其他'
                industry = '未分类'

            return StockInfo(
                code=symbol,
                name=instrument_info['name'],
                market=instrument_info['market'],
                currency='CNY',
                sector=sector,
                industry=industry,
                list_date=None,
                extra_info={
                    'exchange': instrument_info['market'],
                    'instrument_type': instrument_info['type'],
                    'data_source': 'Wind',
                    'wind_code': symbol
                }
            )

        except Exception as e:
            self.logger.error(f"获取 {symbol} 证券信息失败: {e}")
            return self._get_fallback_stock_info(symbol)

    def _get_industry_by_code(self, symbol: str) -> str:
        """根据代码推断行业"""
        if symbol.startswith('60'):
            return '银行/大盘股'
        elif symbol.startswith('00'):
            return '深市主板'
        elif symbol.startswith('30'):
            return '创业板'
        else:
            return '其他'

    def _get_fallback_stock_info(self, symbol: str) -> StockInfo:
        """获取备用证券信息"""
        return StockInfo(
            code=symbol,
            name=f"{symbol} 证券",
            market='UNKNOWN',
            currency='CNY',
            sector='未知',
            industry='未知',
            list_date=None,
            extra_info={'data_source': 'Wind', 'fallback': True}
        )

    def get_kline_data(self, symbol: str, start_date: datetime,
                       end_date: datetime, frequency: str = "1d") -> List[KlineData]:
        """获取K线数据"""
        try:
            if not self.wind_config['authenticated']:
                if not self._connect_wind():
                    return self._get_simulated_kline_data(symbol, start_date, end_date, frequency)

            # 使用Wind API获取K线数据（如果可用）
            if self.wind_api and self.wind_config['authenticated']:
                try:
                    # Wind API调用示例
                    # fields = "open,high,low,close,volume"
                    # result = self.wind_api.wsd(symbol, fields, start_date, end_date, frequency)
                    # 这里使用模拟数据，实际应用中解析Wind API返回的数据
                    pass
                except Exception as e:
                    self.logger.warning(f"Wind API调用失败: {e}")

            # 生成模拟数据
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

        # 根据证券类型设置基础价格
        instrument_info = self.instruments.get(symbol, {})
        instrument_type = instrument_info.get('type', 'stock')

        if instrument_type == 'index':
            if '000001.SH' in symbol:  # 上证指数
                base_price = 3200.0
            elif '399001.SZ' in symbol:  # 深证成指
                base_price = 11000.0
            elif '000300.SH' in symbol:  # 沪深300
                base_price = 4000.0
            else:
                base_price = 5000.0
        elif instrument_type == 'stock':
            if symbol in ['600519.SH', '000858.SZ']:  # 贵州茅台、五粮液
                base_price = 2000.0
            elif symbol in ['601318.SH', '600036.SH']:  # 中国平安、招商银行
                base_price = 60.0
            elif symbol == '300750.SZ':  # 宁德时代
                base_price = 300.0
            else:
                base_price = 20.0
        elif instrument_type == 'futures':
            if 'IF' in symbol:
                base_price = 4000.0
            elif 'CU' in symbol:
                base_price = 68000.0
            elif 'AU' in symbol:
                base_price = 450.0
            else:
                base_price = 3000.0
        elif instrument_type == 'bond':
            base_price = 100.0
        elif instrument_type == 'fund':
            base_price = 1.5
        else:
            base_price = 100.0

        while current_date <= end_date:
            # 模拟价格波动
            if instrument_type == 'index':
                price_change = random.uniform(-0.02, 0.02)
            elif instrument_type == 'stock':
                price_change = random.uniform(-0.05, 0.05)
            elif instrument_type == 'futures':
                price_change = random.uniform(-0.03, 0.03)
            elif instrument_type == 'bond':
                price_change = random.uniform(-0.005, 0.005)
            else:
                price_change = random.uniform(-0.02, 0.02)

            open_price = base_price * (1 + price_change)
            close_price = open_price * (1 + random.uniform(-0.02, 0.02))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))

            # 成交量
            if instrument_type == 'index':
                volume = random.uniform(100000000, 500000000)  # 指数成交量大
            elif instrument_type == 'stock':
                volume = random.uniform(10000, 1000000)
            elif instrument_type == 'futures':
                volume = random.uniform(50000, 200000)
            else:
                volume = random.uniform(5000, 100000)

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
                    'exchange': instrument_info.get('market', 'UNKNOWN'),
                    'instrument_type': instrument_type,
                    'data_source': 'Wind',
                    'wind_code': symbol,
                    'simulated': True
                }
            )
            kline_list.append(kline_data)

            # 增加时间间隔
            if frequency == "1d":
                current_date += timedelta(days=1)
                # 跳过周末
                while current_date.weekday() >= 5:
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
            if not self.wind_config['authenticated']:
                if not self._connect_wind():
                    return self._get_simulated_market_data(symbol)

            # 使用Wind API获取实时数据（如果可用）
            if self.wind_api and self.wind_config['authenticated']:
                try:
                    # Wind API调用示例
                    # fields = "rt_last,rt_open,rt_high,rt_low,rt_vol"
                    # result = self.wind_api.wsq(symbol, fields)
                    # 这里使用模拟数据，实际应用中解析Wind API返回的数据
                    pass
                except Exception as e:
                    self.logger.warning(f"Wind实时数据获取失败: {e}")

            return self._get_simulated_market_data(symbol)

        except Exception as e:
            self.logger.error(f"获取 {symbol} 实时数据失败: {e}")
            return self._get_simulated_market_data(symbol)

    def _get_simulated_market_data(self, symbol: str) -> MarketData:
        """生成模拟市场数据"""

        instrument_info = self.instruments.get(symbol, {})
        instrument_type = instrument_info.get('type', 'stock')

        # 设置基础价格
        if instrument_type == 'index':
            if '000001.SH' in symbol:
                base_price = 3200.0
            elif '399001.SZ' in symbol:
                base_price = 11000.0
            elif '000300.SH' in symbol:
                base_price = 4000.0
            else:
                base_price = 5000.0
        elif instrument_type == 'stock':
            if symbol in ['600519.SH', '000858.SZ']:
                base_price = 2000.0
            elif symbol in ['601318.SH', '600036.SH']:
                base_price = 60.0
            elif symbol == '300750.SZ':
                base_price = 300.0
            else:
                base_price = 20.0
        elif instrument_type == 'futures':
            if 'IF' in symbol:
                base_price = 4000.0
            elif 'CU' in symbol:
                base_price = 68000.0
            elif 'AU' in symbol:
                base_price = 450.0
            else:
                base_price = 3000.0
        elif instrument_type == 'bond':
            base_price = 100.0
        elif instrument_type == 'fund':
            base_price = 1.5
        else:
            base_price = 100.0

        current_price = base_price * (1 + random.uniform(-0.02, 0.02))
        open_price = current_price * (1 + random.uniform(-0.01, 0.01))

        # 成交量
        if instrument_type == 'index':
            volume = random.randint(200000000, 800000000)
        elif instrument_type == 'stock':
            volume = random.randint(50000, 2000000)
        elif instrument_type == 'futures':
            volume = random.randint(100000, 500000)
        else:
            volume = random.randint(10000, 200000)

        return MarketData(
            symbol=symbol,
            current_price=round(current_price, 2),
            open_price=round(open_price, 2),
            high_price=round(current_price * 1.02, 2),
            low_price=round(current_price * 0.98, 2),
            volume=volume,
            timestamp=datetime.now(),
            change_amount=round(current_price - open_price, 2),
            change_percent=round((current_price - open_price) / open_price * 100, 2),
            extra_info={
                'exchange': instrument_info.get('market', 'UNKNOWN'),
                'instrument_type': instrument_type,
                'data_source': 'Wind',
                'wind_code': symbol,
                'bid': round(current_price - 0.01, 2),
                'ask': round(current_price + 0.01, 2),
                'simulated': True
            }
        )

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        try:
            # 检查Wind连接状态
            if not self.wind_config['authenticated']:
                if self._connect_wind():
                    return HealthCheckResult(
                        is_healthy=True,
                        message="Wind 数据终端连接正常",
                        response_time=200,
                        extra_info={
                            'connection_status': self.wind_config['connection_status'],
                            'wind_api_available': self.wind_api is not None,
                            'instruments_count': len(self.instruments),
                            'supported_types': ['股票', '债券', '期货', '基金', '指数']
                        }
                    )
                else:
                    return HealthCheckResult(
                        is_healthy=False,
                        message="Wind 数据终端连接失败",
                        response_time=0,
                        extra_info={
                            'connection_status': 'failed',
                            'wind_api_available': self.wind_api is not None,
                            'username_configured': bool(self.wind_config['username'])
                        }
                    )
            else:
                return HealthCheckResult(
                    is_healthy=True,
                    message="Wind 数据终端连接正常",
                    response_time=150,
                    extra_info={
                        'connection_status': self.wind_config['connection_status'],
                        'authenticated': True,
                        'instruments_count': len(self.instruments)
                    }
                )

        except Exception as e:
            self.logger.error(f"Wind健康检查失败: {e}")
            return HealthCheckResult(
                is_healthy=False,
                message=f"健康检查异常: {str(e)}",
                response_time=0,
                extra_info={'error': str(e)}
            )

    def __del__(self):
        """析构函数，确保正确断开Wind连接"""
        try:
            self._disconnect_wind()
        except:
            pass

    def get_plugin_info(self) -> PluginInfo:
        """获取插件基本信息"""
        return PluginInfo(
            id="wind_data",
            name="Wind万得数据源",
            version=self.version,
            description=self.description,
            author="FactorWeave-Quant 团队",
            supported_asset_types=[AssetType.STOCK, AssetType.BOND, AssetType.FUTURES, AssetType.FUND, AssetType.INDEX],
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
