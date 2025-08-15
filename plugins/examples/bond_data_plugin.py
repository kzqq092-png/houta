"""
债券数据插件
提供国债、企业债、可转债等债券市场数据
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


class BondDataPlugin(IDataSourcePlugin):
    """债券数据源插件"""

    def __init__(self):
        self.name = "债券数据源"
        self.version = "1.0.0"
        self.description = "债券市场数据源"
        self.plugin_type = PluginType.DATA_SOURCE_BOND
        self.supported_asset_types = [AssetType.BOND]
        self.logger = logging.getLogger(__name__)

        # API配置
        self.api_config = {
            'api_key': '',
            'data_provider': 'wind',  # wind, bloomberg, choice
            'authenticated': False
        }

        # 支持的债券品种
        self.bonds = {
            # 国债
            '019645': {'name': '21国债11', 'type': '国债', 'term': '30年', 'coupon': 4.08, 'maturity': '2051-10-19'},
            '019649': {'name': '21国债15', 'type': '国债', 'term': '10年', 'coupon': 3.13, 'maturity': '2031-11-15'},
            '019651': {'name': '21国债17', 'type': '国债', 'term': '5年', 'coupon': 2.68, 'maturity': '2026-11-15'},
            '019655': {'name': '22国债05', 'type': '国债', 'term': '7年', 'coupon': 2.85, 'maturity': '2029-05-19'},
            '019659': {'name': '22国债09', 'type': '国债', 'term': '3年', 'coupon': 2.44, 'maturity': '2025-08-16'},

            # 政策性金融债
            '200205': {'name': '20国开05', 'type': '政策性金融债', 'term': '10年', 'coupon': 3.27, 'maturity': '2030-03-18'},
            '200210': {'name': '20国开10', 'type': '政策性金融债', 'term': '5年', 'coupon': 2.94, 'maturity': '2025-06-24'},
            '210205': {'name': '21国开05', 'type': '政策性金融债', 'term': '10年', 'coupon': 3.57, 'maturity': '2031-04-20'},
            '210401': {'name': '21进出01', 'type': '政策性金融债', 'term': '3年', 'coupon': 3.15, 'maturity': '2024-03-17'},
            '210208': {'name': '21农发08', 'type': '政策性金融债', 'term': '7年', 'coupon': 3.47, 'maturity': '2028-06-21'},

            # 企业债
            '122909': {'name': '20浦建01', 'type': '企业债', 'term': '3年', 'coupon': 4.20, 'maturity': '2023-08-11'},
            '122980': {'name': '20蓉交投', 'type': '企业债', 'term': '5年', 'coupon': 4.69, 'maturity': '2025-10-20'},
            '123015': {'name': '20苏交控', 'type': '企业债', 'term': '7年', 'coupon': 4.65, 'maturity': '2027-11-23'},
            '136895': {'name': '20华发02', 'type': '企业债', 'term': '5年', 'coupon': 5.80, 'maturity': '2025-09-14'},

            # 可转债
            '113011': {'name': '光大转债', 'type': '可转债', 'term': '6年', 'coupon': 0.20, 'maturity': '2025-08-23'},
            '113525': {'name': '浦发转债', 'type': '可转债', 'term': '6年', 'coupon': 0.20, 'maturity': '2026-07-07'},
            '113616': {'name': '韦尔转债', 'type': '可转债', 'term': '6年', 'coupon': 0.30, 'maturity': '2026-09-14'},
            '113618': {'name': '江丰转债', 'type': '可转债', 'term': '6年', 'coupon': 0.40, 'maturity': '2026-09-25'},
            '127019': {'name': '招路转债', 'type': '可转债', 'term': '6年', 'coupon': 0.50, 'maturity': '2027-03-25'},

            # 同业存单
            'CD001': {'name': '同业存单1M', 'type': '同业存单', 'term': '1个月', 'coupon': 2.20, 'maturity': '2024-01-15'},
            'CD003': {'name': '同业存单3M', 'type': '同业存单', 'term': '3个月', 'coupon': 2.35, 'maturity': '2024-03-15'},
            'CD006': {'name': '同业存单6M', 'type': '同业存单', 'term': '6个月', 'coupon': 2.50, 'maturity': '2024-06-15'},
            'CD012': {'name': '同业存单1Y', 'type': '同业存单', 'term': '1年', 'coupon': 2.65, 'maturity': '2024-12-15'},

            # 信用债
            '131810007': {'name': '18万科01', 'type': '信用债', 'term': '3年', 'coupon': 4.95, 'maturity': '2021-07-19'},
            '131820008': {'name': '18恒大01', 'type': '信用债', 'term': '2年', 'coupon': 6.98, 'maturity': '2020-06-19'},
            '131810015': {'name': '18碧桂园', 'type': '信用债', 'term': '3年', 'coupon': 5.85, 'maturity': '2021-12-05'}
        }

        # 债券的典型价格范围（净价）
        self.price_ranges = {
            '国债': (98.0, 102.0),
            '政策性金融债': (97.5, 102.5),
            '企业债': (95.0, 105.0),
            '可转债': (80.0, 180.0),  # 可转债波动较大
            '同业存单': (99.0, 101.0),
            '信用债': (90.0, 110.0)
        }

        self.initialized = False  # 插件初始化状态

    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return self.supported_asset_types

    def configure_api(self, api_key: str, data_provider: str = 'wind'):
        """配置API认证信息"""
        self.api_config.update({
            'api_key': api_key,
            'data_provider': data_provider
        })

    def _authenticate(self) -> bool:
        """API认证"""
        try:
            # 实际应用中这里会进行真实的API认证
            if self.api_config['api_key']:
                self.api_config['authenticated'] = True
                self.logger.info("债券数据API认证成功（模拟）")
                return True
            else:
                self.logger.warning("债券数据API密钥未配置")
                return False
        except Exception as e:
            self.logger.error(f"债券数据API认证失败: {e}")
            return False

    def _make_api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """发送API请求（模拟）"""
        try:
            if not self.api_config['authenticated']:
                if not self._authenticate():
                    return None

            # 实际应用中这里会发送真实的HTTP请求
            self.logger.info(f"模拟调用债券数据API: {endpoint}")

            # 模拟API响应
            return {
                'status': 'success',
                'code': 200,
                'data': {}
            }

        except Exception as e:
            self.logger.error(f"债券数据API请求失败: {e}")
            return None

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取债券基本信息"""
        try:
            bond_info = self.bonds.get(symbol)
            if not bond_info:
                return self._get_fallback_stock_info(symbol)

            return StockInfo(
                code=symbol,
                name=bond_info['name'],
                market='银行间' if bond_info['type'] in ['国债', '政策性金融债', '同业存单'] else '交易所',
                currency='CNY',
                sector='债券',
                industry=bond_info['type'],
                list_date=None,
                extra_info={
                    'bond_type': bond_info['type'],
                    'term': bond_info['term'],
                    'coupon_rate': bond_info['coupon'],
                    'maturity_date': bond_info['maturity'],
                    'data_source': 'Bond',
                    'interest_payment': '年付' if bond_info['type'] != '可转债' else '半年付'
                }
            )

        except Exception as e:
            self.logger.error(f"获取 {symbol} 债券信息失败: {e}")
            return self._get_fallback_stock_info(symbol)

    def _get_fallback_stock_info(self, symbol: str) -> StockInfo:
        """获取备用债券信息"""
        return StockInfo(
            code=symbol,
            name=f"{symbol} 债券",
            market='未知',
            currency='CNY',
            sector='债券',
            industry='未分类债券',
            list_date=None,
            extra_info={'data_source': 'Bond', 'fallback': True}
        )

    def get_kline_data(self, symbol: str, start_date: datetime,
                       end_date: datetime, frequency: str = "1d") -> List[KlineData]:
        """获取债券价格K线数据"""
        try:
            # 调用API获取历史价格数据（模拟）
            api_response = self._make_api_request(f'/bond/history/{symbol}', {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'frequency': frequency
            })

            if not api_response:
                return self._get_simulated_kline_data(symbol, start_date, end_date, frequency)

            # 实际应用中这里会解析真实的API响应
            return self._get_simulated_kline_data(symbol, start_date, end_date, frequency)

        except Exception as e:
            self.logger.error(f"获取 {symbol} 债券价格数据失败: {e}")
            return self._get_simulated_kline_data(symbol, start_date, end_date, frequency)

    def _get_simulated_kline_data(self, symbol: str, start_date: datetime,
                                  end_date: datetime, frequency: str) -> List[KlineData]:
        """生成模拟K线数据"""
        import random

        kline_list = []
        current_date = start_date

        # 根据债券类型设置基础价格
        bond_info = self.bonds.get(symbol, {})
        bond_type = bond_info.get('type', '国债')
        price_range = self.price_ranges.get(bond_type, (95.0, 105.0))
        base_price = (price_range[0] + price_range[1]) / 2

        # 可转债价格可能偏离面值较多
        if bond_type == '可转债':
            # 可转债特殊处理逻辑
            pass

    def is_connected(self) -> bool:
        """检查连接状态"""
        return getattr(self, 'initialized', False)

    def _generate_bond_data(self, bond_code: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """生成债券数据"""
        base_price = random.uniform(100.0, 140.0)

        while current_date <= end_date:
            # 债券价格波动相对较小（除了可转债）
            if bond_type == '可转债':
                price_change = random.uniform(-0.03, 0.03)  # 可转债波动较大
            else:
                price_change = random.uniform(-0.005, 0.005)  # 普通债券波动小

            open_price = base_price * (1 + price_change)
            close_price = open_price * (1 + random.uniform(-0.002, 0.002))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.001))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.001))

            # 债券成交量相对较小
            if bond_type == '可转债':
                volume = random.uniform(10000, 100000)
            else:
                volume = random.uniform(1000, 50000)

            kline_data = KlineData(
                symbol=symbol,
                timestamp=current_date,
                open=round(open_price, 3),
                high=round(high_price, 3),
                low=round(low_price, 3),
                close=round(close_price, 3),
                volume=int(volume),
                frequency=frequency,
                extra_info={
                    'bond_type': bond_type,
                    'data_source': 'Bond',
                    'price_type': 'net_price',  # 净价
                    'accrued_interest': round(random.uniform(0.5, 3.0), 3),  # 应计利息
                    'simulated': True
                }
            )
            kline_list.append(kline_data)

            # 增加时间间隔（债券市场工作日交易）
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
        """获取实时债券市场数据"""
        try:
            # 调用API获取实时价格（模拟）
            api_response = self._make_api_request(f'/bond/realtime/{symbol}')

            if not api_response:
                return self._get_simulated_market_data(symbol)

            # 实际应用中这里会解析真实的API响应
            return self._get_simulated_market_data(symbol)

        except Exception as e:
            self.logger.error(f"获取 {symbol} 实时债券数据失败: {e}")
            return self._get_simulated_market_data(symbol)

    def _get_simulated_market_data(self, symbol: str) -> MarketData:
        """生成模拟市场数据"""

        bond_info = self.bonds.get(symbol, {})
        bond_type = bond_info.get('type', '国债')
        price_range = self.price_ranges.get(bond_type, (95.0, 105.0))

        # 设置基础价格
        if bond_type == '可转债':
            base_price = random.uniform(100.0, 140.0)
        else:
            base_price = (price_range[0] + price_range[1]) / 2

        current_price = base_price * (1 + random.uniform(-0.01, 0.01))
        open_price = current_price * (1 + random.uniform(-0.005, 0.005))

        # 成交量
        if bond_type == '可转债':
            volume = random.randint(20000, 150000)
        else:
            volume = random.randint(5000, 80000)

        # 计算到期收益率（简化计算）
        coupon_rate = bond_info.get('coupon', 3.0)
        ytm = coupon_rate + random.uniform(-0.5, 0.5)  # 到期收益率

        return MarketData(
            symbol=symbol,
            current_price=round(current_price, 3),
            open_price=round(open_price, 3),
            high_price=round(current_price * 1.005, 3),
            low_price=round(current_price * 0.995, 3),
            volume=volume,
            timestamp=datetime.now(),
            change_amount=round(current_price - open_price, 3),
            change_percent=round((current_price - open_price) / open_price * 100, 2),
            extra_info={
                'bond_type': bond_type,
                'data_source': 'Bond',
                'price_type': 'net_price',
                'accrued_interest': round(random.uniform(0.5, 3.0), 3),
                'full_price': round(current_price + random.uniform(0.5, 3.0), 3),  # 全价
                'ytm': round(ytm, 3),  # 到期收益率
                'duration': round(random.uniform(1.0, 8.0), 2),  # 久期
                'convexity': round(random.uniform(0.1, 2.0), 2),  # 凸性
                'bid': round(current_price - 0.05, 3),
                'ask': round(current_price + 0.05, 3),
                'simulated': True
            }
        )

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        try:
            # 检查API配置和认证状态
            if not self.api_config['authenticated']:
                if self._authenticate():
                    return HealthCheckResult(
                        is_healthy=True,
                        message="债券数据 API 连接正常（模拟）",
                        response_time=100,
                        extra_info={
                            'authenticated': True,
                            'data_provider': self.api_config['data_provider'],
                            'bonds_count': len(self.bonds),
                            'bond_types': list(set(v['type'] for v in self.bonds.values()))
                        }
                    )
                else:
                    return HealthCheckResult(
                        is_healthy=False,
                        message="债券数据 API 认证失败",
                        response_time=0,
                        extra_info={
                            'authenticated': False,
                            'api_key_configured': bool(self.api_config['api_key'])
                        }
                    )
            else:
                return HealthCheckResult(
                    is_healthy=True,
                    message="债券数据 API 连接正常",
                    response_time=80,
                    extra_info={
                        'authenticated': True,
                        'bonds_count': len(self.bonds)
                    }
                )

        except Exception as e:
            self.logger.error(f"债券数据健康检查失败: {e}")
            return HealthCheckResult(
                is_healthy=False,
                message=f"健康检查异常: {str(e)}",
                response_time=0,
                extra_info={'error': str(e)}
            )

    def get_plugin_info(self) -> PluginInfo:
        """获取插件基本信息"""
        return PluginInfo(
            id="bond_data",
            name="债券数据源",
            version=self.version,
            description=self.description,
            author="FactorWeave-Quant 团队",
            supported_asset_types=[AssetType.BOND],
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
