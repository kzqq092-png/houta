"""
HIkyuu数据源插件

将HIkyuu框架封装为标准数据源插件，支持：
- 股票、指数、基金等多资产类型
- 历史K线数据、实时行情数据
- 连接管理和健康检查
- 插件生命周期管理
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

# 导入插件接口
from core.data_source_extensions import (
    IDataSourcePlugin, PluginInfo, HealthCheckResult, ConnectionInfo,
    AssetType, DataType
)

logger = logging.getLogger(__name__)


@dataclass
class HikyuuConfig:
    """HIkyuu配置"""
    data_dir: str = "data"
    preload_day_count: int = 100000
    enable_spot_agent: bool = True
    log_level: str = "INFO"
    timeout_seconds: int = 30


class HikyuuDataPlugin(IDataSourcePlugin):
    """HIkyuu数据源插件"""

    def __init__(self, config: Optional[HikyuuConfig] = None):
        """
        初始化HIkyuu数据源插件

        Args:
            config: HIkyuu配置
        """
        self.config = config or HikyuuConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

        # HIkyuu相关
        self._hikyuu_available = False
        self._sm = None  # StockManager
        self._query_class = None
        self._connection_time = None
        self._last_activity = None

        # 统计信息
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "last_request_time": None,
            "uptime": 0.0
        }

        # 缓存
        self._invalid_stocks_cache = set()
        self._valid_stocks_cache = set()

    @property
    def plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id="hikyuu_data_source",
            name="HIkyuu数据源",
            version="1.0.0",
            description="基于HIkyuu框架的高性能量化数据源，支持股票、指数、基金等多资产类型数据获取",
            author="HIkyuu-UI Team",
            supported_asset_types=[
                AssetType.STOCK,
                AssetType.INDEX,
                AssetType.FUND
            ],
            supported_data_types=[
                DataType.HISTORICAL_KLINE,
                DataType.REAL_TIME_QUOTE,
                DataType.FUNDAMENTAL
            ],
            capabilities={
                "markets": ["SH", "SZ", "BJ"],
                "frequencies": ["1m", "5m", "15m", "30m", "60m", "D", "W", "M"],
                "max_history_years": 20,
                "real_time_support": True,
                "fundamental_data": True
            }
        )

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息（方法形式）"""
        return self.plugin_info

    def connect(self, **kwargs) -> bool:
        """
        连接HIkyuu数据源

        Args:
            **kwargs: 连接参数

        Returns:
            bool: 连接是否成功
        """
        try:
            self.logger.info("正在连接HIkyuu数据源...")

            # 导入HIkyuu模块
            try:
                import hikyuu as hku
                from hikyuu.interactive import sm
                from hikyuu import Query

                self._sm = sm
                self._query_class = Query
                self._hikyuu_available = True

                self.logger.info("✅ HIkyuu模块导入成功")

            except ImportError as e:
                self.logger.error(f"❌ HIkyuu模块导入失败: {e}")
                return False

            # 验证HIkyuu是否正常工作
            if self._sm is None:
                self.logger.error("❌ HIkyuu StockManager未初始化")
                return False

            # 测试基本功能
            try:
                # 尝试获取上证指数验证连接
                test_stock = self._sm["sh000001"]
                if test_stock and hasattr(test_stock, 'valid') and test_stock.valid:
                    self.logger.info("✅ HIkyuu连接验证成功")
                else:
                    # 尝试其他测试股票
                    test_stocks = ["sz000001", "sh000300", "sz399001"]
                    found_valid = False
                    for test_code in test_stocks:
                        try:
                            test_stock = self._sm[test_code]
                            if test_stock and hasattr(test_stock, 'valid') and test_stock.valid:
                                self.logger.info(f"✅ HIkyuu连接验证成功（使用 {test_code}）")
                                found_valid = True
                                break
                        except Exception:
                            continue

                    if not found_valid:
                        self.logger.warning("⚠️ 无法找到有效的测试股票，但HIkyuu已加载")

            except Exception as e:
                self.logger.warning(f"⚠️ HIkyuu连接测试异常: {e}")

            # 记录连接时间
            self._connection_time = datetime.now()
            self._last_activity = datetime.now()

            self.logger.info("🎉 HIkyuu数据源连接成功")
            return True

        except Exception as e:
            self.logger.error(f"❌ HIkyuu数据源连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """
        断开HIkyuu数据源连接

        Returns:
            bool: 断开是否成功
        """
        try:
            self.logger.info("正在断开HIkyuu数据源连接...")

            # 清理缓存
            self._invalid_stocks_cache.clear()
            self._valid_stocks_cache.clear()

            # 重置状态
            self._hikyuu_available = False
            self._sm = None
            self._query_class = None
            self._connection_time = None

            self.logger.info("✅ HIkyuu数据源已断开")
            return True

        except Exception as e:
            self.logger.error(f"❌ HIkyuu数据源断开失败: {e}")
            return False

    def is_connected(self) -> bool:
        """
        检查连接状态

        Returns:
            bool: 是否已连接
        """
        return (
            self._hikyuu_available and
            self._sm is not None and
            self._connection_time is not None
        )

    def get_connection_info(self) -> ConnectionInfo:
        """
        获取连接信息

        Returns:
            ConnectionInfo: 连接详细信息
        """
        return ConnectionInfo(
            is_connected=self.is_connected(),
            connection_time=self._connection_time,
            last_activity=self._last_activity,
            connection_params={
                "data_dir": self.config.data_dir,
                "preload_day_count": self.config.preload_day_count,
                "enable_spot_agent": self.config.enable_spot_agent
            },
            error_message=None if self.is_connected() else "HIkyuu未连接"
        )

    def health_check(self) -> HealthCheckResult:
        """
        健康检查

        Returns:
            HealthCheckResult: 健康检查结果
        """
        start_time = datetime.now()

        try:
            if not self.is_connected():
                return HealthCheckResult(
                    is_healthy=False,
                    status_code=503,
                    message="HIkyuu未连接",
                    response_time_ms=0.0,
                    last_check_time=start_time
                )

            # 执行简单的数据查询测试
            try:
                test_stock = self._sm["sh000001"]
                if test_stock.valid:
                    # 尝试获取最近1条数据
                    query = self._query_class(-1, ktype=self._query_class.DAY)
                    kdata = test_stock.get_kdata(query)

                    if kdata and len(kdata) > 0:
                        response_time = (datetime.now() - start_time).total_seconds() * 1000
                        return HealthCheckResult(
                            is_healthy=True,
                            status_code=200,
                            message="HIkyuu运行正常",
                            response_time_ms=response_time,
                            last_check_time=start_time,
                            details={
                                "test_symbol": "sh000001",
                                "data_available": True,
                                "last_data_date": str(kdata[-1].datetime) if kdata else None
                            }
                        )
                    else:
                        return HealthCheckResult(
                            is_healthy=False,
                            status_code=404,
                            message="HIkyuu无法获取测试数据",
                            response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                            last_check_time=start_time
                        )
                else:
                    return HealthCheckResult(
                        is_healthy=False,
                        status_code=404,
                        message="HIkyuu测试股票无效",
                        response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                        last_check_time=start_time
                    )

            except Exception as e:
                return HealthCheckResult(
                    is_healthy=False,
                    status_code=500,
                    message=f"HIkyuu健康检查异常: {str(e)}",
                    response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    last_check_time=start_time
                )

        except Exception as e:
            return HealthCheckResult(
                is_healthy=False,
                status_code=500,
                message=f"健康检查失败: {str(e)}",
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                last_check_time=start_time
            )

    def get_asset_list(self, asset_type: AssetType, market: str = None) -> List[Dict[str, Any]]:
        """
        获取资产列表

        Args:
            asset_type: 资产类型
            market: 市场代码（可选）

        Returns:
            List[Dict[str, Any]]: 资产列表
        """
        try:
            if not self.is_connected():
                self.logger.error("HIkyuu未连接")
                return []

            self.logger.info(f"获取资产列表: {asset_type.value}, market={market}")

            asset_list = []
            total_count = 0
            valid_count = 0

            # 遍历所有股票
            try:
                for stock in self._sm:
                    total_count += 1

                    try:
                        # 只处理有效股票
                        if not stock or not hasattr(stock, 'valid') or not stock.valid:
                            continue

                        # 安全获取股票属性
                        stock_market = getattr(stock, 'market', None)
                        stock_code = getattr(stock, 'code', None)
                        stock_name = getattr(stock, 'name', None)
                        stock_type = getattr(stock, 'type', None)

                        # 检查必要属性是否存在
                        if not stock_market or not stock_code:
                            continue

                        # 转换为字符串并处理None值
                        stock_market = str(stock_market) if stock_market is not None else ''
                        stock_code = str(stock_code) if stock_code is not None else ''
                        stock_name = str(stock_name) if stock_name is not None else stock_code
                        stock_type = int(stock_type) if stock_type is not None else 0

                        # 市场过滤
                        if market and stock_market.lower() != market.lower():
                            continue

                        # 资产类型过滤
                        if asset_type == AssetType.STOCK:
                            # 股票类型过滤逻辑 - 只包含股票，排除指数
                            if stock_type != 1:  # 1=股票
                                # 记录被过滤的指数代码，帮助调试
                                if stock_code in ['980076', '399001', '399006']:
                                    self.logger.info(f"🚫 过滤指数代码: {stock_market.lower()}{stock_code} (type={stock_type}, name={stock_name})")
                                continue
                        elif asset_type == AssetType.INDEX:
                            if stock_type != 2:  # 2=指数
                                continue
                        elif asset_type == AssetType.FUND:
                            if stock_type != 3:  # 3=基金
                                continue

                        # 构建股票代码（市场+代码）
                        market_code = f"{stock_market.lower()}{stock_code}"

                        stock_info = {
                            'symbol': market_code,
                            'name': stock_name,
                            'market': stock_market,
                            'type': stock_type,
                            'asset_type': asset_type.value
                        }

                        asset_list.append(stock_info)
                        valid_count += 1

                    except Exception as e:
                        self.logger.warning(f"处理股票失败 {getattr(stock, 'code', 'unknown')}: {e}")
                        continue

            except Exception as e:
                self.logger.error(f"遍历股票列表失败: {e}")
                return []

            self.logger.info(f"获取资产列表完成: {valid_count}/{total_count} 个有效资产")
            self._update_stats(True)
            return asset_list

        except Exception as e:
            self.logger.error(f"获取资产列表失败: {e}")
            self._update_stats(False)
            return []

    def get_kdata(self, symbol: str, freq: str = "D", start_date: str = None,
                  end_date: str = None, count: int = None) -> pd.DataFrame:
        """
        获取K线数据

        Args:
            symbol: 交易代码
            freq: 频率 (D/W/M/H/30m/15m/5m/1m)
            start_date: 开始日期
            end_date: 结束日期
            count: 数据条数

        Returns:
            pd.DataFrame: K线数据
        """
        start_time = datetime.now()

        try:
            if not self.is_connected():
                self.logger.error("HIkyuu未连接")
                return pd.DataFrame()

            self.logger.debug(f"获取K线数据: {symbol}, freq={freq}, count={count}")

            # 检查缓存，避免重复查询无效股票
            if symbol in self._invalid_stocks_cache:
                self.logger.debug(f"股票在无效缓存中: {symbol}")
                return pd.DataFrame()

            # 标准化股票代码（添加市场前缀）
            normalized_symbol = self.normalize_symbol(symbol)
            self.logger.debug(f"股票代码标准化: {symbol} -> {normalized_symbol}")

            # 获取股票对象
            try:
                stock = self._sm[normalized_symbol]
                if not stock.valid:
                    self.logger.warning(f"股票无效: {symbol}")
                    self._invalid_stocks_cache.add(symbol)
                    return pd.DataFrame()
                else:
                    self._valid_stocks_cache.add(symbol)
            except Exception as e:
                self.logger.warning(f"股票不存在: {symbol} - {e}")
                self._invalid_stocks_cache.add(symbol)
                return pd.DataFrame()

            # 转换周期格式
            ktype = self._convert_frequency(freq)

            # 创建查询对象
            if count:
                query = self._query_class(-count, ktype=ktype)
            elif start_date and end_date:
                # 转换为HIkyuu.Datetime对象
                import hikyuu as hku
                hku_start = hku.Datetime(start_date)
                hku_end = hku.Datetime(end_date)
                query = self._query_class(hku_start, hku_end, ktype)
            elif start_date:
                import hikyuu as hku
                hku_start = hku.Datetime(start_date)
                hku_end = hku.Datetime(datetime.now().strftime('%Y-%m-%d'))
                query = self._query_class(hku_start, hku_end, ktype)
            else:
                query = self._query_class(-365, ktype=ktype)  # 默认获取一年数据

            # 获取K线数据
            try:
                kdata = stock.get_kdata(query)
                if kdata is None or len(kdata) == 0:
                    self.logger.warning(f"K线数据为空: {symbol}")
                    return pd.DataFrame()
            except Exception as e:
                self.logger.error(f"获取K线数据失败: {symbol} - {e}")
                return pd.DataFrame()

            # 转换为DataFrame
            df = self._convert_kdata_to_dataframe(kdata, symbol)

            # 更新活动时间
            self._last_activity = datetime.now()

            self.logger.debug(f"K线数据获取成功: {symbol}, 记录数: {len(df)}")
            self._update_stats(True, start_time)

            return df

        except Exception as e:
            self.logger.error(f"获取K线数据异常: {symbol} - {e}")
            self._update_stats(False, start_time)
            return pd.DataFrame()

    def get_real_time_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取实时行情

        Args:
            symbols: 交易代码列表

        Returns:
            pd.DataFrame: 实时行情数据
        """
        start_time = datetime.now()

        try:
            if not self.is_connected():
                self.logger.error("HIkyuu未连接")
                return pd.DataFrame()

            self.logger.debug(f"获取实时行情: {symbols}")

            quotes = []
            for symbol in symbols:
                try:
                    if symbol in self._invalid_stocks_cache:
                        continue

                    stock = self._sm[symbol]
                    if not stock.valid:
                        self._invalid_stocks_cache.add(symbol)
                        continue

                    # 获取最新K线数据作为实时行情
                    query = self._query_class(-1, ktype=self._query_class.DAY)
                    kdata = stock.get_kdata(query)

                    if kdata and len(kdata) > 0:
                        k = kdata[-1]
                        quote = {
                            'symbol': symbol,
                            'name': stock.name,
                            'current_price': float(k.close),
                            'open_price': float(k.open),
                            'high_price': float(k.high),
                            'low_price': float(k.low),
                            'volume': float(k.volume),
                            'turnover': float(getattr(k, 'amount', 0)),
                            'update_time': self._convert_hikyuu_datetime(k.datetime),
                            'market': stock.market
                        }

                        # 计算涨跌
                        if len(kdata) > 1:
                            prev_close = float(kdata[-2].close)
                            quote['prev_close'] = prev_close
                            quote['change'] = quote['current_price'] - prev_close
                            quote['change_percent'] = (quote['change'] / prev_close * 100) if prev_close > 0 else 0.0
                        else:
                            quote['prev_close'] = quote['current_price']
                            quote['change'] = 0.0
                            quote['change_percent'] = 0.0

                        quotes.append(quote)

                except Exception as e:
                    self.logger.warning(f"获取实时行情失败: {symbol} - {e}")
                    continue

            df = pd.DataFrame(quotes)

            # 更新活动时间
            self._last_activity = datetime.now()

            self.logger.debug(f"实时行情获取成功: {len(df)} 条记录")
            self._update_stats(True, start_time)

            return df

        except Exception as e:
            self.logger.error(f"获取实时行情异常: {e}")
            self._update_stats(False, start_time)
            return pd.DataFrame()

    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """
        获取基本面数据

        Args:
            symbol: 交易代码

        Returns:
            Dict[str, Any]: 基本面数据
        """
        try:
            if not self.is_connected():
                return {}

            stock = self._sm[symbol]
            if not stock.valid:
                return {}

            # 获取基本信息
            fundamental_data = {
                'symbol': symbol,
                'name': stock.name,
                'market': stock.market,
                'type': stock.type,
                'industry': getattr(stock, 'industry', None) or '其他',
                'start_date': str(stock.start_datetime) if stock.start_datetime else None,
                'end_date': str(stock.last_datetime) if stock.last_datetime else None
            }

            # 尝试获取财务数据（如果HIkyuu支持）
            try:
                if hasattr(stock, 'get_finance_info'):
                    finance_info = stock.get_finance_info()
                    if finance_info:
                        fundamental_data['finance'] = finance_info
            except Exception as e:
                self.logger.debug(f"获取财务数据失败: {symbol} - {e}")

            return fundamental_data

        except Exception as e:
            self.logger.error(f"获取基本面数据失败: {symbol} - {e}")
            return {}

    def _convert_frequency(self, freq: str):
        """转换频率格式"""
        freq_map = {
            'D': self._query_class.DAY,
            'W': self._query_class.WEEK,
            'M': self._query_class.MONTH,
            '60m': self._query_class.MIN60,
            '30m': self._query_class.MIN30,
            '15m': self._query_class.MIN15,
            '5m': self._query_class.MIN5,
            '1m': self._query_class.MIN
        }
        return freq_map.get(freq.upper(), self._query_class.DAY)

    def _convert_kdata_to_dataframe(self, kdata, symbol: str) -> pd.DataFrame:
        """将HIkyuu K线数据转换为DataFrame"""
        try:
            if not kdata or len(kdata) == 0:
                return pd.DataFrame()

            # 提取数据
            data_list = []
            for k in kdata:
                try:
                    # 转换日期
                    dt = self._convert_hikyuu_datetime(k.datetime)
                    if dt is None:
                        continue

                    # 构建数据行
                    data_row = {
                        'datetime': dt,
                        'open': float(k.open),
                        'high': float(k.high),
                        'low': float(k.low),
                        'close': float(k.close),
                        'volume': float(k.volume),
                        'amount': float(getattr(k, 'amount', 0))
                    }
                    data_list.append(data_row)

                except Exception as e:
                    self.logger.warning(f"转换K线记录失败: {e}")
                    continue

            if not data_list:
                return pd.DataFrame()

            # 创建DataFrame
            df = pd.DataFrame(data_list)

            # 设置datetime为索引
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)

            # 添加股票代码
            df['code'] = symbol

            # 数据清洗
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.dropna(subset=['close'])

            # 按时间排序
            df = df.sort_index()

            return df

        except Exception as e:
            self.logger.error(f"转换K线数据失败: {e}")
            return pd.DataFrame()

    def _convert_hikyuu_datetime(self, dt) -> Optional[datetime]:
        """转换HIkyuu的Datetime对象为Python datetime"""
        try:
            if hasattr(dt, 'number'):
                n = int(dt.number)
                if n == 0:
                    return None
                s = str(n)
                if len(s) >= 8:
                    year = int(s[:4])
                    month = int(s[4:6])
                    day = int(s[6:8])
                    return datetime(year, month, day)
            elif isinstance(dt, (datetime, pd.Timestamp)):
                return dt
            else:
                # 尝试字符串解析
                return pd.to_datetime(str(dt))
        except Exception as e:
            self.logger.warning(f"转换日期失败 {dt}: {e}")
            return None

    def _update_stats(self, success: bool, start_time: Optional[datetime] = None):
        """更新统计信息"""
        self._stats["total_requests"] += 1

        if success:
            self._stats["successful_requests"] += 1
        else:
            self._stats["failed_requests"] += 1

        if start_time:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            total_success = self._stats["successful_requests"]
            if total_success > 0:
                current_avg = self._stats["average_response_time"]
                self._stats["average_response_time"] = (
                    (current_avg * (total_success - 1) + response_time) / total_success
                )

        self._stats["last_request_time"] = datetime.now()

        if self._connection_time:
            self._stats["uptime"] = (datetime.now() - self._connection_time).total_seconds()

    def get_statistics(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        return {
            **self._stats,
            "cache_stats": {
                "invalid_stocks": len(self._invalid_stocks_cache),
                "valid_stocks": len(self._valid_stocks_cache)
            },
            "connection_info": {
                "is_connected": self.is_connected(),
                "connection_time": self._connection_time.isoformat() if self._connection_time else None,
                "last_activity": self._last_activity.isoformat() if self._last_activity else None
            }
        }

    def get_supported_frequencies(self) -> List[str]:
        """获取支持的频率列表"""
        return ["1m", "5m", "15m", "30m", "60m", "D", "W", "M"]

    def get_supported_markets(self) -> List[str]:
        """获取支持的市场列表"""
        return ["SH", "SZ", "BJ"]

    def validate_symbol(self, symbol: str, asset_type: AssetType = None) -> bool:
        """验证交易代码是否有效"""
        try:
            if not self.is_connected():
                return False

            if symbol in self._invalid_stocks_cache:
                return False

            if symbol in self._valid_stocks_cache:
                return True

            stock = self._sm[symbol]
            is_valid = stock.valid

            if is_valid:
                self._valid_stocks_cache.add(symbol)
            else:
                self._invalid_stocks_cache.add(symbol)

            return is_valid

        except Exception:
            return False

    def normalize_symbol(self, symbol: str, asset_type: AssetType = None) -> str:
        """标准化交易代码"""
        if not symbol:
            return symbol

        # 移除市场前缀（如果存在）
        code = symbol.lower()
        if code.startswith(('sh', 'sz', 'bj')):
            return symbol

        # 根据代码前缀添加市场标识
        if symbol.startswith('6'):
            return f"sh{symbol}"
        elif symbol.startswith(('0', '3')):
            return f"sz{symbol}"
        elif symbol.startswith('8'):
            return f"bj{symbol}"
        else:
            # 默认深圳市场
            return f"sz{symbol}"

    def clear_cache(self) -> None:
        """清理股票缓存"""
        try:
            self._invalid_stocks_cache.clear()
            self._valid_stocks_cache.clear()
            self.logger.info("HIkyuu插件缓存已清理")
        except Exception as e:
            self.logger.error(f"清理缓存失败: {e}")

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            'invalid_stocks': len(self._invalid_stocks_cache),
            'valid_stocks': len(self._valid_stocks_cache)
        }
