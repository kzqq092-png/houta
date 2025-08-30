"""
AKShare股票数据源插件

提供A股实时和历史数据获取功能，支持：
- A股股票基本信息
- 历史K线数据
- 实时行情数据
- 财务数据
- 行业分类数据

使用AKShare库作为数据源：
- 支持上海、深圳交易所
- 实时数据更新
- 丰富的财务指标

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

from datetime import datetime, timedelta
import time
import traceback
from typing import Any, Dict, List, Optional

import pandas as pd

from core.data_source_data_models import QueryParams
from core.data_source_extensions import IDataSourcePlugin, PluginInfo, HealthCheckResult
from core.logger import get_logger
from core.plugin_types import AssetType, DataType, PluginType

logger = get_logger(__name__)

# 检查AKShare库
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("AKShare 数据源可用")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.error("AKShare 库未安装，插件无法工作")

# 检查必要的库
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.error("requests 库未安装，插件无法工作")


class AKShareStockPlugin(IDataSourcePlugin):
    """AKShare股票数据源插件"""

    def __init__(self):
        self.logger = get_logger(__name__)  # 添加logger属性
        self.initialized = False
        self.DEFAULT_CONFIG = {
            'timeout': 30,
            'max_retries': 3,
            'cache_duration': 3600
        }
        self.config = self.DEFAULT_CONFIG.copy()
        self.request_count = 0
        self.last_error = None

        # 连接状态属性
        self.connection_time = None
        self.last_activity = None

        # 插件基本信息
        self.name = "AKShare股票数据源插件"
        self.version = "1.0.0"
        self.description = "提供A股实时和历史数据，支持上海、深圳交易所"
        self.author = "FactorWeave-Quant 开发团队"

        # 插件类型标识
        self.plugin_type = PluginType.DATA_SOURCE_STOCK

        # 支持的股票市场
        self.supported_markets = {
            'SH': '上海证券交易所',
            'SZ': '深圳证券交易所',
            'BJ': '北京证券交易所'
        }

        # 数据缓存
        self._stock_list_cache = None
        self._cache_timestamp = None
        self._cache_duration = 3600  # 1小时缓存

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id="akshare_stock_plugin",
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            supported_asset_types=[AssetType.STOCK],
            supported_data_types=[
                DataType.HISTORICAL_KLINE,
                DataType.REAL_TIME_QUOTE,
                DataType.FUNDAMENTAL,
                DataType.TRADE_TICK,
                DataType.SECTOR_FUND_FLOW  # 添加板块资金流支持
            ],
            capabilities={
                "markets": ["SH", "SZ", "BJ"],
                "frequencies": ["1m", "5m", "15m", "30m", "60m", "D"],
                "real_time_support": True,
                "historical_data": True
            }
        )

    @property
    def plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id="akshare_stock_plugin",
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            supported_asset_types=[AssetType.STOCK],
            supported_data_types=[
                DataType.HISTORICAL_KLINE,
                DataType.REAL_TIME_QUOTE,
                DataType.FUNDAMENTAL,
                DataType.TRADE_TICK,
                DataType.SECTOR_FUND_FLOW  # 添加板块资金流支持
            ],
            capabilities={
                "markets": ["SH", "SZ", "BJ"],
                "frequencies": ["1m", "5m", "15m", "30m", "60m", "D"],
                "real_time_support": True,
                "historical_data": True
            }
        )

    def connect(self, **kwargs) -> bool:
        """连接数据源"""
        try:
            if not AKSHARE_AVAILABLE:
                self.last_error = "AKShare库未安装"
                self.logger.error("AKShare库未安装")
                return False

            if not REQUESTS_AVAILABLE:
                self.last_error = "requests库未安装"
                self.logger.error("requests库未安装")
                return False

                # 使用线程超时机制（Windows兼容）
            import time
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

            def test_akshare_connection():
                """测试AKShare连接"""
                # 使用更简单的API进行测试，减少网络请求
                return ak.tool_trade_date_hist_sina()  # 获取交易日历，数据量小

                self.logger.info("正在测试AKShare连接...")

            # 使用线程池执行，设置10秒超时
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(test_akshare_connection)
                try:
                    test_data = future.result(timeout=10.0)

                    if test_data is not None and not test_data.empty:
                        self.logger.info("AKShare数据源连接成功")
                        self.connection_time = time.time()
                        self.last_activity = time.time()
                        return True
                    else:
                        self.last_error = "AKShare API返回空数据"
                        self.logger.warning("AKShare API返回空数据")
                        return False

                except FutureTimeoutError:
                    self.last_error = "AKShare API调用超时"
                    self.logger.error("AKShare API调用超时")
                    return False

        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"连接失败: {e}")
            # 如果是网络相关错误，提供更友好的错误信息
            if "Connection" in str(e) or "timeout" in str(e).lower():
                self.last_error = f"网络连接失败: {e}"
                self.logger.error("网络连接失败，请检查网络连接或稍后重试")
            return False

    def disconnect(self) -> bool:
        """断开连接"""
        try:
            # AKShare不需要显式断开连接
            self.logger.info("AKShare数据源断开连接")
            return True
        except Exception as e:
            self.logger.error(f"断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        try:
            if not AKSHARE_AVAILABLE:
                return False
            # 简单测试API是否可用
            test_data = ak.stock_zh_a_spot_em()
            return test_data is not None and not test_data.empty
        except:
            return False

    def get_connection_info(self):
        """获取连接信息"""
        from core.data_source_extensions import ConnectionInfo, HealthCheckResult
        return ConnectionInfo(
            is_connected=self.is_connected(),
            connection_time=self.connection_time,
            last_activity=self.last_activity,
            connection_params={
                "server_info": "AKShare API",
                "timeout": self.config.get('timeout', 30),
                "max_retries": self.config.get('max_retries', 3)
            },
            error_message=self.last_error
        )

    def health_check(self):
        """健康检查"""
        from core.data_source_extensions import HealthCheckResult
        import time

        start_time = time.time()
        try:
            # 测试API是否可用
            test_data = ak.stock_zh_a_spot_em()
            response_time = (time.time() - start_time) * 1000

            if test_data is not None and not test_data.empty:
                return HealthCheckResult(
                    is_healthy=True,
                    status_code=200,
                    message="ok",
                    response_time_ms=response_time,
                    last_check_time=datetime.now()
                )
            else:
                return HealthCheckResult(
                    is_healthy=False,
                    status_code=500,
                    message="API返回空数据",
                    response_time_ms=response_time,
                    last_check_time=datetime.now()
                )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                is_healthy=False,
                status_code=500,
                message=str(e),
                response_time_ms=response_time,
                last_check_time=datetime.now()
            )

    def get_asset_list(self, asset_type: AssetType, market: str = None) -> List[Dict[str, Any]]:
        """获取资产列表"""
        try:
            if asset_type != AssetType.STOCK:
                self.logger.warning(f"不支持的资产类型: {asset_type}")
                return []

            if not AKSHARE_AVAILABLE:
                self.logger.error("AKShare库不可用")
                return []

            # 检查缓存
            cache_key = f"asset_list_{asset_type.value}_{market or 'all'}"
            if self._stock_list_cache and self._cache_timestamp:
                import time
                if time.time() - self._cache_timestamp < self._cache_duration:
                    cached_data = self._stock_list_cache.get(cache_key)
                    if cached_data:
                        self.logger.info(f"从缓存获取资产列表: {len(cached_data)} 只股票")
                        return cached_data

            self.logger.info(f"正在获取A股列表，市场筛选: {market or '全部'}")

            # 使用线程超时机制（Windows兼容）
            import time
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

            def get_akshare_stock_list():
                """获取AKShare股票列表"""
                return ak.stock_zh_a_spot_em()

            # 使用线程池执行，设置15秒超时
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(get_akshare_stock_list)
                try:
                    stock_df = future.result(timeout=15.0)

                    if stock_df is None or stock_df.empty:
                        self.logger.warning("AKShare返回空的股票列表")
                        return self._get_fallback_stock_list(market)

                    # 转换为标准格式
                    asset_list = []
                    processed_count = 0

                    for _, row in stock_df.iterrows():
                        symbol = str(row.get('代码', '')).strip()
                        name = str(row.get('名称', '')).strip()

                        if not symbol or not name:
                            continue

                        # 判断市场
                        if symbol.startswith(('000', '002', '300')):
                            exchange = 'SZ'
                        elif symbol.startswith(('600', '601', '603', '688')):
                            exchange = 'SH'
                        elif symbol.startswith(('8', '4')):
                            exchange = 'BJ'
                        else:
                            exchange = 'Unknown'

                        # 市场筛选
                        if market and exchange.upper() != market.upper():
                            continue

                        asset_info = {
                            "symbol": symbol,
                            "name": name,
                            "market": exchange,
                            "asset_type": asset_type.value,
                            "currency": "CNY",
                            "exchange": exchange
                        }
                        asset_list.append(asset_info)
                        processed_count += 1

                    # 缓存结果
                    if not hasattr(self, '_stock_list_cache') or self._stock_list_cache is None:
                        self._stock_list_cache = {}
                    self._stock_list_cache[cache_key] = asset_list
                    self._cache_timestamp = time.time()

                    self.logger.info(f"成功获取A股列表: {processed_count} 只股票")
                    return asset_list

                except FutureTimeoutError:
                    self.logger.error("获取股票列表超时，使用备用列表")
                    return self._get_fallback_stock_list(market)

        except Exception as e:
            self.logger.error(f"获取资产列表失败: {e}")
            # 网络错误时返回备用列表
            if "Connection" in str(e) or "timeout" in str(e).lower():
                self.logger.info("网络连接问题，使用备用股票列表")
                return self._get_fallback_stock_list(market)
            return []

    def _get_fallback_stock_list(self, market: str = None) -> List[Dict[str, Any]]:
        """获取备用股票列表（离线数据）"""
        fallback_stocks = [
            # 主板蓝筹股
            {"symbol": "000001", "name": "平安银行", "market": "SZ", "asset_type": "stock", "currency": "CNY", "exchange": "SZ"},
            {"symbol": "000002", "name": "万科A", "market": "SZ", "asset_type": "stock", "currency": "CNY", "exchange": "SZ"},
            {"symbol": "000858", "name": "五粮液", "market": "SZ", "asset_type": "stock", "currency": "CNY", "exchange": "SZ"},
            {"symbol": "002415", "name": "海康威视", "market": "SZ", "asset_type": "stock", "currency": "CNY", "exchange": "SZ"},
            {"symbol": "002594", "name": "比亚迪", "market": "SZ", "asset_type": "stock", "currency": "CNY", "exchange": "SZ"},
            {"symbol": "300750", "name": "宁德时代", "market": "SZ", "asset_type": "stock", "currency": "CNY", "exchange": "SZ"},

            {"symbol": "600000", "name": "浦发银行", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},
            {"symbol": "600036", "name": "招商银行", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},
            {"symbol": "600519", "name": "贵州茅台", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},
            {"symbol": "600887", "name": "伊利股份", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},
            {"symbol": "601318", "name": "中国平安", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},
            {"symbol": "601398", "name": "工商银行", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},
            {"symbol": "601939", "name": "建设银行", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},
            {"symbol": "603259", "name": "药明康德", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},

            # 科创板代表
            {"symbol": "688981", "name": "中芯国际", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},
            {"symbol": "688036", "name": "传音控股", "market": "SH", "asset_type": "stock", "currency": "CNY", "exchange": "SH"},
        ]

        # 根据市场筛选
        if market:
            fallback_stocks = [s for s in fallback_stocks if s["market"].upper() == market.upper()]

        self.logger.info(f"返回备用股票列表: {len(fallback_stocks)} 只股票")
        return fallback_stocks

    def get_kdata(self, symbol: str, freq: str = "D", start_date: str = None,
                  end_date: str = None, count: int = None) -> pd.DataFrame:
        """获取K线数据"""
        try:
            # 转换频率参数
            if freq in ["1m", "5m", "15m", "30m", "60m"]:
                # 分钟级数据
                period_map = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60"}
                period = period_map.get(freq, "1")

                # 使用AKShare获取分钟数据
                df = ak.stock_zh_a_hist_min_em(symbol=symbol, period=period,
                                               start_date=start_date, end_date=end_date)
            else:
                # 日线及以上数据
                period_map = {"D": "daily", "W": "weekly", "M": "monthly"}
                period = period_map.get(freq, "daily")

                # 使用AKShare获取日线数据
                df = ak.stock_zh_a_hist(symbol=symbol, period=period,
                                        start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                return pd.DataFrame()

            # 标准化列名
            column_mapping = {
                '日期': 'datetime', '时间': 'datetime',
                '开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close',
                '成交量': 'volume', '成交额': 'amount'
            }

            df = df.rename(columns=column_mapping)

            # 确保有必要的列
            required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = 0.0

            return df[required_columns]

        except Exception as e:
            self.logger.error(f"获取K线数据失败: {e}")
            return pd.DataFrame()

    def get_sector_fund_flow_data(self, symbol: str = "sector", **kwargs) -> pd.DataFrame:
        """
        获取板块资金流数据

        Args:
            symbol: 板块代码或"sector"表示获取所有板块
            **kwargs: 其他参数，如indicator等

        Returns:
            板块资金流数据DataFrame
        """
        try:
            if not AKSHARE_AVAILABLE:
                self.logger.error("AKShare库不可用")
                return pd.DataFrame()

            indicator = kwargs.get('indicator', '今日')

            if symbol == "sector" or symbol is None:
                # 获取板块资金流排行
                self.logger.info(f"获取板块资金流排行数据，指标: {indicator}")
                df = ak.stock_sector_fund_flow_rank(indicator=indicator)
            else:
                # 获取特定板块的资金流汇总
                self.logger.info(f"获取板块 {symbol} 资金流汇总数据，指标: {indicator}")
                df = ak.stock_sector_fund_flow_summary(symbol=symbol, indicator=indicator)

            if df is None or df.empty:
                self.logger.warning(f"未获取到板块资金流数据: symbol={symbol}, indicator={indicator}")
                return pd.DataFrame()

            # 标准化列名（根据实际返回的列名进行映射）
            column_mapping = {
                '板块名称': 'sector_name',
                '板块代码': 'sector_code',
                '涨跌幅': 'change_pct',
                '主力净流入-净额': 'main_net_inflow',
                '主力净流入-净占比': 'main_net_inflow_pct',
                '超大单净流入-净额': 'super_large_net_inflow',
                '超大单净流入-净占比': 'super_large_net_inflow_pct',
                '大单净流入-净额': 'large_net_inflow',
                '大单净流入-净占比': 'large_net_inflow_pct',
                '中单净流入-净额': 'medium_net_inflow',
                '中单净流入-净占比': 'medium_net_inflow_pct',
                '小单净流入-净额': 'small_net_inflow',
                '小单净流入-净占比': 'small_net_inflow_pct'
            }

            # 重命名存在的列
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df = df.rename(columns={old_name: new_name})

            self.logger.info(f"成功获取板块资金流数据，共 {len(df)} 条记录")
            return df

        except Exception as e:
            self.logger.error(f"获取板块资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_individual_fund_flow_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """
        获取个股资金流数据

        Args:
            symbol: 股票代码
            **kwargs: 其他参数

        Returns:
            个股资金流数据DataFrame
        """
        try:
            if not AKSHARE_AVAILABLE:
                self.logger.error("AKShare库不可用")
                return pd.DataFrame()

            # 获取个股资金流数据
            self.logger.info(f"获取个股资金流数据")
            df = ak.stock_individual_fund_flow_rank(indicator="今日")

            if df is None or df.empty:
                self.logger.warning(f"未获取到个股资金流数据: {symbol}")
                return pd.DataFrame()

            # 标准化列名
            column_mapping = {
                '股票代码': 'symbol',
                '股票名称': 'name',
                '涨跌幅': 'change_pct',
                '主力净流入-净额': 'main_net_inflow',
                '主力净流入-净占比': 'main_net_inflow_pct',
                '超大单净流入-净额': 'super_large_net_inflow',
                '超大单净流入-净占比': 'super_large_net_inflow_pct',
                '大单净流入-净额': 'large_net_inflow',
                '大单净流入-净占比': 'large_net_inflow_pct',
                '中单净流入-净额': 'medium_net_inflow',
                '中单净流入-净占比': 'medium_net_inflow_pct',
                '小单净流入-净额': 'small_net_inflow',
                '小单净流入-净占比': 'small_net_inflow_pct'
            }

            # 重命名存在的列
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df = df.rename(columns={old_name: new_name})

            self.logger.info(f"成功获取个股资金流数据，共 {len(df)} 条记录")
            return df

        except Exception as e:
            self.logger.error(f"获取个股资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_main_fund_flow_data(self, symbol: str = "index", **kwargs) -> pd.DataFrame:
        """
        获取主力资金流数据（大盘指数）

        Args:
            symbol: 指数代码或"index"表示获取主要指数
            **kwargs: 其他参数

        Returns:
            主力资金流数据DataFrame
        """
        try:
            if not AKSHARE_AVAILABLE:
                self.logger.error("AKShare库不可用")
                return pd.DataFrame()

            # 获取主力资金流数据
            self.logger.info(f"获取主力资金流数据: {symbol}")
            df = ak.stock_market_fund_flow()

            if df is None or df.empty:
                self.logger.warning("未获取到主力资金流数据")
                return pd.DataFrame()

            # 标准化列名
            column_mapping = {
                '指数名称': 'index_name',
                '指数代码': 'index_code',
                '涨跌幅': 'change_pct',
                '主力净流入-净额': 'main_net_inflow',
                '主力净流入-净占比': 'main_net_inflow_pct',
                '超大单净流入-净额': 'super_large_net_inflow',
                '超大单净流入-净占比': 'super_large_net_inflow_pct',
                '大单净流入-净额': 'large_net_inflow',
                '大单净流入-净占比': 'large_net_inflow_pct'
            }

            # 重命名存在的列
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df = df.rename(columns={old_name: new_name})

            self.logger.info(f"成功获取主力资金流数据，共 {len(df)} 条记录")
            return df

        except Exception as e:
            self.logger.error(f"获取主力资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_real_time_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情"""
        try:
            # 获取实时行情数据
            real_time_df = ak.stock_zh_a_spot_em()
            if real_time_df is None or real_time_df.empty:
                return []

            quotes = []
            for symbol in symbols:
                # 查找对应的股票数据
                stock_data = real_time_df[real_time_df['代码'] == symbol]
                if stock_data.empty:
                    continue

                row = stock_data.iloc[0]
                quote = {
                    "symbol": symbol,
                    "price": float(row.get('最新价', 0.0)),
                    "change": float(row.get('涨跌额', 0.0)),
                    "change_percent": float(row.get('涨跌幅', 0.0)),
                    "volume": int(row.get('成交量', 0)),
                    "timestamp": datetime.now().isoformat()
                }
                quotes.append(quote)

            return quotes
        except Exception as e:
            self.logger.error(f"获取实时行情失败: {e}")
            return []


# 配置Schema
AKSHARE_CONFIG_SCHEMA = {
    "timeout": {
        "type": "integer",
        "default": 30,
        "description": "请求超时时间（秒）"
    },
    "max_retries": {
        "type": "integer",
        "default": 3,
        "description": "最大重试次数"
    },
    "cache_duration": {
        "type": "integer",
        "default": 3600,
        "description": "缓存持续时间（秒）"
    }
}
