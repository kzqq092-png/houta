"""
东方财富数据源插件

基于HIkyuu-UI标准插件模板实现的东方财富数据源插件，
提供股票、指数、基金等多种资产的实时和历史数据。

作者: FactorWeave-Quant团队
版本: 1.0.0
日期: 2024-09-17
"""

import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode

from loguru import logger
from plugins.templates.standard_data_source_plugin import (
    StandardDataSourcePlugin, PluginConfig, 
    PluginConnectionError, PluginDataQualityError
)
from core.plugin_types import AssetType, DataType


class EastMoneyConfig(PluginConfig):
    """东方财富插件配置"""
    
    def __init__(self):
        super().__init__()
        self.api_endpoint = "http://push2.eastmoney.com/api"
        self.quote_endpoint = "http://push2.eastmoney.com/api/qt/stock/get"
        self.kline_endpoint = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        self.market_overview_endpoint = "http://push2.eastmoney.com/api/qt/ulist.np/get"
        self.fund_flow_endpoint = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        
        # 东方财富特定配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://quote.eastmoney.com/',
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }
        
        # 市场映射
        self.market_map = {
            "SH": "1",   # 上海
            "SZ": "0",   # 深圳  
            "BJ": "2"    # 北京
        }
        
        # 频率映射
        self.frequency_map = {
            "1m": "1",
            "5m": "5", 
            "15m": "15",
            "30m": "30",
            "60m": "60",
            "D": "101",
            "W": "102",
            "M": "103"
        }
        
        # 支持的市场和频率
        self.supported_markets = ["SH", "SZ", "BJ"]
        self.supported_frequencies = ["1m", "5m", "15m", "30m", "60m", "D", "W", "M"]
        
        # 请求限制
        self.rate_limit_requests = 200
        self.rate_limit_period = 60
        self.timeout = 15
        self.retry_count = 3


class EastMoneyPlugin(StandardDataSourcePlugin):
    """
    东方财富数据源插件
    
    提供股票、指数、基金等多种资产的实时和历史数据获取功能
    """
    
    def __init__(self):
        """初始化东方财富插件"""
        config = EastMoneyConfig()
        super().__init__(
            plugin_id="eastmoney",
            plugin_name="东方财富数据源",
            config=config
        )
        
        # 会话管理
        self._session = None
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_reset_time = time.time()
        
        # 符号缓存
        self._symbol_cache = {}
        self._symbol_cache_expire = timedelta(hours=1)
        self._symbol_cache_time = None
        
        self.logger.info("东方财富数据源插件初始化完成")
    
    # 插件基本信息
    def get_version(self) -> str:
        """获取插件版本"""
        return "1.0.0"
    
    def get_description(self) -> str:
        """获取插件描述"""
        return "东方财富数据源插件，提供A股、港股、美股等多市场的实时行情和历史数据"
    
    def get_author(self) -> str:
        """获取插件作者"""
        return "FactorWeave-Quant团队 <factorweave@example.com>"
    
    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return [
            AssetType.STOCK,      # 股票
            AssetType.INDEX,      # 指数
            AssetType.FUND,       # 基金
            AssetType.BOND        # 债券
        ]
    
    def get_supported_data_types(self) -> List[DataType]:
        """获取支持的数据类型"""
        return [
            DataType.HISTORICAL_KLINE,    # 历史K线
            DataType.REAL_TIME_QUOTE,     # 实时行情
            DataType.ASSET_LIST,          # 资产列表
            DataType.FUND_FLOW,           # 资金流
            DataType.MARKET_DEPTH         # 市场深度（有限支持）
        ]
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取插件能力"""
        return {
            "markets": self.config.supported_markets,
            "frequencies": self.config.supported_frequencies,
            "real_time_support": True,
            "historical_data": True,
            "fund_flow_support": True,
            "max_symbols_per_request": 50,
            "max_kline_count": 1000,
            "rate_limit": f"{self.config.rate_limit_requests} requests/{self.config.rate_limit_period}s",
            "data_delay": "实时（少量延迟）",
            "supported_exchanges": ["SSE", "SZSE", "BSE"]  # 上交所、深交所、北交所
        }
    
    def get_priority(self) -> int:
        """获取插件优先级"""
        return 20  # 中等优先级
    
    def get_weight(self) -> float:
        """获取插件权重"""
        return 1.2  # 稍高权重，数据质量较好
    
    # 连接管理
    def _internal_connect(self, **kwargs) -> bool:
        """内部连接实现"""
        try:
            # 创建会话
            self._session = requests.Session()
            self._session.headers.update(self.config.headers)
            
            # 配置重试策略
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            retry_strategy = Retry(
                total=self.config.retry_count,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            
            # 测试连接
            test_url = f"{self.config.api_endpoint}/qt/stock/get"
            test_params = {
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'invt': '2',
                'fltt': '2',
                'fields': 'f43,f44,f45,f46,f47,f60',
                'secid': '1.000001'  # 上证指数
            }
            
            response = self._session.get(
                test_url, 
                params=test_params, 
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    self.logger.info("东方财富数据源连接测试成功")
                    return True
                else:
                    self.logger.error("东方财富数据源连接测试失败：返回数据为空")
                    return False
            else:
                self.logger.error(f"东方财富数据源连接测试失败：HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"东方财富数据源连接失败: {e}")
            return False
    
    def _internal_disconnect(self) -> bool:
        """内部断开连接实现"""
        try:
            if self._session:
                self._session.close()
                self._session = None
            
            # 清理缓存
            self._symbol_cache.clear()
            self._symbol_cache_time = None
            
            self.logger.info("东方财富数据源断开连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"东方财富数据源断开连接失败: {e}")
            return False
    
    # 数据获取实现
    def _internal_get_asset_list(self, asset_type: AssetType, market: str = None) -> List[Dict[str, Any]]:
        """获取资产列表"""
        try:
            # 检查缓存
            cache_key = f"{asset_type.value}_{market or 'all'}"
            if self._is_symbol_cache_valid() and cache_key in self._symbol_cache:
                self.logger.debug(f"从缓存获取资产列表: {cache_key}")
                return self._symbol_cache[cache_key]
            
            asset_list = []
            
            if asset_type == AssetType.STOCK:
                asset_list = self._get_stock_list(market)
            elif asset_type == AssetType.INDEX:
                asset_list = self._get_index_list(market)
            elif asset_type == AssetType.FUND:
                asset_list = self._get_fund_list(market)
            else:
                self.logger.warning(f"不支持的资产类型: {asset_type}")
                return []
            
            # 缓存结果
            self._cache_symbol_list(cache_key, asset_list)
            
            self.logger.info(f"获取资产列表成功: {asset_type.value}, 数量: {len(asset_list)}")
            return asset_list
            
        except Exception as e:
            self.logger.error(f"获取资产列表失败: {e}")
            raise PluginDataQualityError(f"获取{asset_type.value}列表失败: {str(e)}")
    
    def _internal_get_kdata(self, symbol: str, freq: str = "D", 
                           start_date: str = None, end_date: str = None,
                           count: int = None) -> pd.DataFrame:
        """获取K线数据"""
        try:
            # 参数验证
            if not symbol:
                raise ValueError("股票代码不能为空")
            
            if freq not in self.config.frequency_map:
                raise ValueError(f"不支持的频率: {freq}")
            
            # 解析股票代码
            secid = self._parse_symbol_to_secid(symbol)
            if not secid:
                raise ValueError(f"无法解析股票代码: {symbol}")
            
            # 构建请求参数
            params = {
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': self.config.frequency_map[freq],
                'fqt': '1',  # 复权类型：1前复权
                'secid': secid,
                'beg': '0',
                'end': '20500000'
            }
            
            # 处理日期参数
            if start_date:
                params['beg'] = start_date.replace('-', '')
            if end_date:
                params['end'] = end_date.replace('-', '')
                
            # 执行请求
            response = self._make_rate_limited_request(
                self.config.kline_endpoint, 
                params
            )
            
            if response.status_code != 200:
                raise PluginConnectionError(f"API请求失败: HTTP {response.status_code}")
            
            # 解析响应
            data = response.json()
            if 'data' not in data or not data['data']:
                self.logger.warning(f"未获取到{symbol}的K线数据")
                return pd.DataFrame()
            
            klines = data['data']['klines']
            if not klines:
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = self._convert_klines_to_dataframe(klines)
            
            # 应用数量限制
            if count and len(df) > count:
                df = df.tail(count)
            
            self.logger.debug(f"获取K线数据成功: {symbol}, 频率: {freq}, 数量: {len(df)}")
            return df
            
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {symbol} - {e}")
            raise
    
    def _internal_get_real_time_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情"""
        try:
            if not symbols:
                return []
            
            # 限制单次请求的符号数量
            max_symbols = self.get_capabilities()["max_symbols_per_request"]
            if len(symbols) > max_symbols:
                self.logger.warning(f"请求符号数量({len(symbols)})超过限制({max_symbols})，将截取前{max_symbols}个")
                symbols = symbols[:max_symbols]
            
            # 转换符号格式
            secids = []
            for symbol in symbols:
                secid = self._parse_symbol_to_secid(symbol)
                if secid:
                    secids.append(secid)
            
            if not secids:
                raise ValueError("没有有效的股票代码")
            
            # 构建请求参数
            params = {
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'invt': '2',
                'fltt': '2',
                'fields': 'f12,f13,f14,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f33,f34,f35,f36,f37,f38,f39,f40,f19,f43,f57,f58,f59,f152',
                'secids': ','.join(secids)
            }
            
            # 执行请求
            response = self._make_rate_limited_request(
                self.config.quote_endpoint,
                params
            )
            
            if response.status_code != 200:
                raise PluginConnectionError(f"API请求失败: HTTP {response.status_code}")
            
            # 解析响应
            data = response.json()
            if 'data' not in data or not data['data']:
                self.logger.warning("未获取到实时行情数据")
                return []
            
            # 转换为标准格式
            quotes = []
            for item in data['data']:
                if item:
                    quote = self._convert_quote_data(item)
                    quotes.append(quote)
            
            self.logger.debug(f"获取实时行情成功，数量: {len(quotes)}")
            return quotes
            
        except Exception as e:
            self.logger.error(f"获取实时行情失败: {e}")
            raise
    
    # 辅助方法
    def _parse_symbol_to_secid(self, symbol: str) -> str:
        """将股票代码转换为东方财富的secid格式"""
        try:
            if '.' in symbol:
                code, market = symbol.split('.')
                if market.upper() in self.config.market_map:
                    market_id = self.config.market_map[market.upper()]
                    return f"{market_id}.{code}"
            
            # 如果没有市场标识，根据代码规则判断
            if symbol.startswith('00') or symbol.startswith('30'):
                return f"0.{symbol}"  # 深圳
            elif symbol.startswith('60') or symbol.startswith('68'):
                return f"1.{symbol}"  # 上海
            elif symbol.startswith('8') or symbol.startswith('4'):
                return f"2.{symbol}"  # 北京
            else:
                # 默认上海
                return f"1.{symbol}"
                
        except Exception as e:
            self.logger.error(f"解析股票代码失败: {symbol} - {e}")
            return None
    
    def _get_stock_list(self, market: str = None) -> List[Dict[str, Any]]:
        """获取股票列表"""
        stocks = []
        
        try:
            # 获取A股列表
            markets_to_query = [market] if market else ["SH", "SZ"]
            
            for mkt in markets_to_query:
                if mkt not in self.config.market_map:
                    continue
                
                # 构建请求参数
                params = {
                    'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                    'fltt': '2',
                    'invt': '2',
                    'fields': 'f12,f13,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11',
                    'fid': 'f3',
                    'fs': f'm:{self.config.market_map[mkt]}+t:6,m:{self.config.market_map[mkt]}+t:13,m:{self.config.market_map[mkt]}+t:80',
                    'pn': '1',
                    'pz': '5000'
                }
                
                response = self._make_rate_limited_request(
                    self.config.market_overview_endpoint,
                    params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and data['data'] and 'diff' in data['data']:
                        for item in data['data']['diff']:
                            if item:
                                stock = {
                                    'symbol': f"{item['f12']}.{mkt}",
                                    'code': item['f12'],
                                    'name': item['f14'],
                                    'market': mkt,
                                    'asset_type': 'STOCK',
                                    'price': item.get('f2', 0) / 100 if item.get('f2') else None,
                                    'change_pct': item.get('f3', 0) / 100 if item.get('f3') else None
                                }
                                stocks.append(stock)
            
            return stocks
            
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {e}")
            return []
    
    def _get_index_list(self, market: str = None) -> List[Dict[str, Any]]:
        """获取指数列表"""
        indices = []
        
        try:
            # 主要指数代码
            main_indices = [
                {'code': '000001', 'name': '上证指数', 'market': 'SH'},
                {'code': '399001', 'name': '深证成指', 'market': 'SZ'},
                {'code': '399006', 'name': '创业板指', 'market': 'SZ'},
                {'code': '000300', 'name': '沪深300', 'market': 'SH'},
                {'code': '000016', 'name': '上证50', 'market': 'SH'},
                {'code': '000905', 'name': '中证500', 'market': 'SH'},
                {'code': '000852', 'name': '中证1000', 'market': 'SH'}
            ]
            
            for idx in main_indices:
                if market is None or idx['market'] == market:
                    indices.append({
                        'symbol': f"{idx['code']}.{idx['market']}",
                        'code': idx['code'],
                        'name': idx['name'],
                        'market': idx['market'],
                        'asset_type': 'INDEX'
                    })
            
            return indices
            
        except Exception as e:
            self.logger.error(f"获取指数列表失败: {e}")
            return []
    
    def _get_fund_list(self, market: str = None) -> List[Dict[str, Any]]:
        """获取基金列表（简化实现）"""
        return []  # 基金列表获取较为复杂，暂时返回空列表
    
    def _convert_klines_to_dataframe(self, klines: List[str]) -> pd.DataFrame:
        """将K线数据转换为DataFrame"""
        try:
            data = []
            for kline in klines:
                parts = kline.split(',')
                if len(parts) >= 11:
                    data.append({
                        'datetime': pd.to_datetime(parts[0]),
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': int(parts[5]),
                        'amount': float(parts[6]),
                        'amplitude': float(parts[7]) if parts[7] else 0.0,
                        'change_pct': float(parts[8]) if parts[8] else 0.0,
                        'change': float(parts[9]) if parts[9] else 0.0,
                        'turnover': float(parts[10]) if parts[10] else 0.0
                    })
            
            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index('datetime', inplace=True)
                df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"转换K线数据失败: {e}")
            return pd.DataFrame()
    
    def _convert_quote_data(self, item: Dict) -> Dict[str, Any]:
        """转换实时行情数据格式"""
        try:
            return {
                'symbol': f"{item.get('f12', '')}.{self._get_market_from_secid(item.get('f13', '1'))}",
                'code': item.get('f12', ''),
                'name': item.get('f14', ''),
                'price': item.get('f2', 0) / 100 if item.get('f2') else 0.0,
                'change': item.get('f4', 0) / 100 if item.get('f4') else 0.0,
                'change_pct': item.get('f3', 0) / 100 if item.get('f3') else 0.0,
                'volume': item.get('f5', 0),
                'amount': item.get('f6', 0) / 100 if item.get('f6') else 0.0,
                'open': item.get('f17', 0) / 100 if item.get('f17') else 0.0,
                'high': item.get('f15', 0) / 100 if item.get('f15') else 0.0,
                'low': item.get('f16', 0) / 100 if item.get('f16') else 0.0,
                'pre_close': item.get('f18', 0) / 100 if item.get('f18') else 0.0,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'market': self._get_market_from_secid(item.get('f13', '1'))
            }
            
        except Exception as e:
            self.logger.error(f"转换行情数据失败: {e}")
            return {}
    
    def _get_market_from_secid(self, secid: str) -> str:
        """从secid获取市场标识"""
        market_reverse_map = {'1': 'SH', '0': 'SZ', '2': 'BJ'}
        return market_reverse_map.get(str(secid), 'SH')
    
    def _make_rate_limited_request(self, url: str, params: Dict) -> requests.Response:
        """执行频率限制的请求"""
        current_time = time.time()
        
        # 重置频率限制计数器
        if current_time - self._rate_limit_reset_time >= self.config.rate_limit_period:
            self._request_count = 0
            self._rate_limit_reset_time = current_time
        
        # 检查频率限制
        if self._request_count >= self.config.rate_limit_requests:
            sleep_time = self.config.rate_limit_period - (current_time - self._rate_limit_reset_time)
            if sleep_time > 0:
                self.logger.debug(f"达到频率限制，等待 {sleep_time:.1f} 秒")
                time.sleep(sleep_time)
                self._request_count = 0
                self._rate_limit_reset_time = time.time()
        
        # 请求间隔控制
        time_since_last = current_time - self._last_request_time
        if time_since_last < 0.1:  # 最小100ms间隔
            time.sleep(0.1 - time_since_last)
        
        # 执行请求
        try:
            response = self._session.get(url, params=params, timeout=self.config.timeout)
            self._request_count += 1
            self._last_request_time = time.time()
            return response
            
        except requests.RequestException as e:
            self.logger.error(f"请求失败: {url} - {e}")
            raise PluginConnectionError(f"网络请求失败: {str(e)}")
    
    def _is_symbol_cache_valid(self) -> bool:
        """检查符号缓存是否有效"""
        if not self._symbol_cache_time:
            return False
        return datetime.now() - self._symbol_cache_time < self._symbol_cache_expire
    
    def _cache_symbol_list(self, cache_key: str, symbol_list: List[Dict]) -> None:
        """缓存符号列表"""
        self._symbol_cache[cache_key] = symbol_list
        self._symbol_cache_time = datetime.now()


# 插件注册
def create_plugin() -> EastMoneyPlugin:
    """创建插件实例"""
    return EastMoneyPlugin()


# 用于兼容性的别名
EastMoneyDataSourcePlugin = EastMoneyPlugin
