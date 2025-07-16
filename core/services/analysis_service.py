"""
分析服务模块

负责技术分析、策略分析和数据分析。
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import asyncio
import time  # Added for time.time()

from .base_service import CacheableService, ConfigurableService
from ..events import AnalysisCompleteEvent, StockSelectedEvent, EventBus
from .unified_data_manager import UnifiedDataManager


logger = logging.getLogger(__name__)


class AnalysisService(CacheableService, ConfigurableService):
    """
    分析服务

    负责技术分析、策略分析和数据分析。
    """

    def __init__(self,
                 unified_data_manager: UnifiedDataManager,
                 event_bus: EventBus,
                 config: Optional[Dict[str, Any]] = None,
                 cache_size: int = 100,
                 **kwargs):
        """
        初始化分析服务

        Args:
            unified_data_manager: 统一数据管理器
            event_bus: 事件总线
            config: 服务配置
            cache_size: 缓存大小
            **kwargs: 其他参数
        """
        # 初始化各个基类
        super().__init__(**kwargs)
        ConfigurableService.__init__(self, config=config, **kwargs)

        self.data_manager = unified_data_manager

        self._current_stock_code = None
        self._analysis_results = {}
        self._strategies = {}

        # 新增：请求管理
        self.active_requests: Dict[str, asyncio.Task] = {}
        self.request_lock = asyncio.Lock()

    def _do_initialize(self) -> None:
        """初始化分析服务"""
        try:
            # 初始化分析策略
            self._load_analysis_strategies()

            logger.info("Analysis service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize analysis service: {e}")
            raise

    async def calculate_technical_indicators(self, stock_code: str,
                                             indicators: List[str] = None,
                                             kline_data: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        异步计算技术指标

        Args:
            stock_code: 股票代码
            indicators: 指标列表
            kline_data: 预先加载的K线数据.
        """
        self._ensure_initialized()

        if kline_data is None or kline_data.empty:
            logger.warning(f"无法为 {stock_code} 提供K线数据，无法计算技术指标")
            return None

        stock_data = kline_data
        indicators = indicators or ['MA5', 'MA10', 'MA20', 'MACD', 'RSI']

        try:
            results = {}
            # 计算各种技术指标
            for indicator in indicators:
                if indicator.startswith('MA') and not indicator.startswith('MACD'):
                    try:
                        period_num = int(indicator[2:])
                        results[indicator] = self._calculate_ma(
                            stock_data, period_num)
                    except ValueError:
                        logger.warning(
                            f"Cannot parse period from indicator: {indicator}")
                        continue
                elif indicator == 'MACD':
                    results['MACD'] = self._calculate_macd(stock_data)
                elif indicator == 'RSI':
                    results['RSI'] = self._calculate_rsi(stock_data)
                elif indicator == 'KDJ':
                    results['KDJ'] = self._calculate_kdj(stock_data)
                elif indicator == 'BOLL':
                    results['BOLL'] = self._calculate_bollinger_bands(
                        stock_data)
                elif indicator == 'VOL':
                    results['VOL'] = self._calculate_volume_indicators(
                        stock_data)
                elif indicator == 'BIAS':
                    results['BIAS'] = self._calculate_bias(stock_data)
                elif indicator == 'WR':
                    results['WR'] = self._calculate_wr(stock_data)
                elif indicator == 'CCI':
                    results['CCI'] = self._calculate_cci(stock_data)
            return results
        except Exception as e:
            logger.error(
                f"Failed to calculate technical indicators for {stock_code}: {e}")
            return None

    async def analyze_trend(self, stock_code: str, kline_data: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        异步趋势分析

        Args:
            stock_code: 股票代码
            kline_data: 预先加载的K线数据.
        """
        self._ensure_initialized()

        if kline_data is None or kline_data.empty:
            logger.error(f"Failed to get k-line data for {stock_code} for trend analysis")
            return None

        stock_data = kline_data

        try:
            # 计算趋势指标
            ma5 = self._calculate_ma(stock_data, 5)
            ma20 = self._calculate_ma(stock_data, 20)
            ma60 = self._calculate_ma(stock_data, 60)

            current_price = stock_data['close'].iloc[-1]

            # 趋势判断
            trend_short = self._judge_trend(current_price, ma5.iloc[-1])
            trend_medium = self._judge_trend(current_price, ma20.iloc[-1])
            trend_long = self._judge_trend(current_price, ma60.iloc[-1])

            # 多空排列
            ma_arrangement = self._analyze_ma_arrangement(
                ma5.iloc[-1], ma20.iloc[-1], ma60.iloc[-1])

            # 趋势强度
            trend_strength = self._calculate_trend_strength(stock_data)

            result = {
                'stock_code': stock_code,
                'current_price': current_price,
                'trend_short': trend_short,
                'trend_medium': trend_medium,
                'trend_long': trend_long,
                'ma_arrangement': ma_arrangement,
                'trend_strength': trend_strength,
                'analysis_time': datetime.now().isoformat()
            }
            return result
        except Exception as e:
            logger.error(f"Failed to analyze trend for {stock_code}: {e}")
            return None

    async def cancel_previous_requests(self):
        """取消先前的所有分析请求"""
        async with self.request_lock:
            if not self.active_requests:
                return

            logger.info(f"正在取消 {len(self.active_requests)} 个活动的分析任务...")
            for task_id, task in list(self.active_requests.items()):
                if not task.done():
                    task.cancel()
                    logger.debug(f"已取消分析任务: {task_id}")
            self.active_requests.clear()

    async def analyze_support_resistance(self, stock_code: str, kline_data: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        异步支撑阻力分析

        Args:
            stock_code: 股票代码
            kline_data: 预先加载的K线数据.
        """
        self._ensure_initialized()

        if kline_data is None or kline_data.empty:
            logger.error(f"Failed to get k-line data for {stock_code} for support/resistance analysis")
            return None

        stock_data = kline_data

        try:
            # 计算支撑位和阻力位
            support_levels = self._find_support_levels(stock_data)
            resistance_levels = self._find_resistance_levels(stock_data)

            # 获取当前价格
            current_price = stock_data['close'].iloc[-1]

            # 分析价格位置
            position_analysis = self._analyze_price_position(
                current_price, support_levels, resistance_levels)

            # 构建结果
            result = {
                'stock_code': stock_code,
                'current_price': current_price,
                'support_levels': support_levels[:3],  # 最多返回3个支撑位
                'resistance_levels': resistance_levels[:3],  # 最多返回3个阻力位
                'position_analysis': position_analysis,
                'analysis_time': datetime.now().isoformat()
            }
            return result
        except Exception as e:
            logger.error(f"Failed to analyze support/resistance for {stock_code}: {e}")
            return None

    async def run_strategy_analysis(self, stock_code: str, strategy_name: str,
                                    parameters: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        异步运行策略分析

        Args:
            stock_code: 股票代码
            strategy_name: 策略名称
            parameters: 策略参数

        Returns:
            策略分析结果
        """
        self._ensure_initialized()

        if strategy_name not in self._strategies:
            logger.error(f"Strategy not found: {strategy_name}")
            return None

        # 这是一个示例，实际策略可能需要不同的数据
        time_range = parameters.get('time_range', 365)

        # 异步获取数据
        kdata = await self.data_manager.request_data(
            data_type='kdata',
            stock_code=stock_code,
            period='D',
            parameters={'indicators': ()}
        )
        if kdata is None or kdata.empty:
            logger.warning(
                f"No data for {stock_code} to run strategy {strategy_name}")
            return None

        stock_data = kdata.get('kline_data')
        if stock_data is None or stock_data.empty:
            logger.warning(
                f"No data for {stock_code} to run strategy {strategy_name} from package")
            return None

        # 运行策略
        try:
            strategy_func = self._strategies[strategy_name]
            # 策略函数现在是异步的
            result = await strategy_func(stock_code, parameters or {})

            if result:
                # 缓存结果
                cache_key = f"strategy_{strategy_name}_{stock_code}_{hash(str(parameters))}"
                self.put_to_cache(cache_key, result)

                # 发布分析完成事件
                event = AnalysisCompleteEvent(
                    analysis_type='strategy',
                    stock_code=stock_code
                )
                event.data.update({
                    'strategy_name': strategy_name,
                    'result': result
                })
                self.event_bus.publish(event)

            return result

        except Exception as e:
            logger.error(
                f"Failed to run strategy {strategy_name} for {stock_code}: {e}")
            return None

    def get_available_strategies(self) -> List[str]:
        """
        获取可用的策略列表

        Returns:
            策略名称列表
        """
        return list(self._strategies.keys())

    def get_analysis_history(self, stock_code: str = None,
                             analysis_type: str = None) -> List[Dict[str, Any]]:
        """
        获取分析历史

        Args:
            stock_code: 股票代码（可选）
            analysis_type: 分析类型（可选）

        Returns:
            分析历史列表
        """
        results = []

        for key, value in self._analysis_results.items():
            if stock_code and stock_code not in key:
                continue
            if analysis_type and analysis_type not in key:
                continue

            results.append({
                'key': key,
                'result': value,
                'timestamp': getattr(value, 'analysis_time', None)
            })

        # 按时间排序
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return results

    def _on_analysis_data_received(self, data, error=None):
        """
        异步数据接收回调
        """
        try:
            if error:
                logger.error(f"Analysis data request failed: {error}")
                return

            if data is not None:
                # 发布分析完成事件
                from ..events import AnalysisCompleteEvent
                event = AnalysisCompleteEvent(
                    stock_code=self._current_stock_code,
                    analysis_type='comprehensive'
                )
                event.data.update(data)
                self.event_bus.publish(event)

                logger.debug(
                    f"Analysis data received and published for {self._current_stock_code}")
            else:
                logger.warning(
                    f"No analysis data received for {self._current_stock_code}")

        except Exception as e:
            logger.error(f"Error processing analysis data: {e}")

    async def _fallback_analysis(self, stock_code: str):
        """降级分析，直接请求数据并运行"""
        try:
            # 异步请求分析数据，优先级设为中等
            await self.data_manager.request_data(
                stock_code=stock_code,
                data_type='analysis',
                priority='medium'
            )
            logger.info(f"Fallback analysis requested for {stock_code}")
        except Exception as e:
            logger.error(f"Fallback analysis failed for {stock_code}: {e}")

    def _run_auto_analysis_async(self, stock_code: str) -> None:
        """异步运行自动分析"""
        try:
            # 使用QTimer延迟执行，避免阻塞UI
            from PyQt5.QtCore import QTimer
            timer = QTimer()
            timer.timeout.connect(lambda: self._run_auto_analysis(stock_code))
            timer.setSingleShot(True)
            timer.start(100)  # 100ms后执行

        except Exception as e:
            logger.error(f"Failed to schedule auto analysis: {e}")

    def _run_auto_analysis(self, stock_code: str) -> None:
        """自动执行一系列分析"""
        async def analysis_coroutine():
            try:
                logger.info(f"开始为 {stock_code} 自动执行异步分析...")
                # 并发执行所有分析任务
                tasks = [
                    self.calculate_technical_indicators(stock_code),
                    self.analyze_trend(stock_code),
                    self.analyze_support_resistance(stock_code)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                final_result = {'stock_code': stock_code}
                for res in results:
                    if isinstance(res, dict):
                        final_result.update(res)
                    elif isinstance(res, Exception):
                        logger.error(f"分析任务失败: {res}")

                self._on_analysis_data_received(final_result)
                logger.info(f"为 {stock_code} 完成自动异步分析。")

            except Exception as e:
                logger.error(f"自动分析协程失败: {e}", exc_info=True)
                self._on_analysis_data_received(None, error=str(e))

        asyncio.create_task(analysis_coroutine())

    def _get_stock_service(self):
        raise NotImplementedError(
            "_get_stock_service is deprecated. Use self.data_manager instead.")

    def _get_stock_data(self, stock_code: str, period: str, time_range: int) -> Optional[pd.DataFrame]:
        raise NotImplementedError(
            "_get_stock_data is deprecated. Use self.data_manager instead.")

    def _calculate_ma(self, data: pd.DataFrame, period: int) -> pd.Series:
        """计算移动平均线"""
        return data['close'].rolling(window=period).mean()

    def _calculate_macd(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算MACD"""
        close = data['close']
        ema_fast = close.ewm(span=12).mean()
        ema_slow = close.ewm(span=26).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line

        return {
            'MACD': macd_line,
            'Signal': signal_line,
            'Histogram': histogram
        }

    def _calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI"""
        close = data['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_kdj(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算KDJ指标"""
        high = data['high']
        low = data['low']
        close = data['close']

        lowest_low = low.rolling(window=9).min()
        highest_high = high.rolling(window=9).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        k = rsv.ewm(alpha=1/3).mean()
        d = k.ewm(alpha=1/3).mean()
        j = 3 * k - 2 * d

        return {'K': k, 'D': d, 'J': j}

    def _calculate_bollinger_bands(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算布林带"""
        close = data['close']
        middle = close.rolling(window=20).mean()
        std = close.rolling(window=20).std()
        upper = middle + (std * 2)
        lower = middle - (std * 2)

        return {
            'Upper': upper,
            'Middle': middle,
            'Lower': lower
        }

    def _calculate_volume_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """计算成交量指标"""
        volume = data['volume']
        vol_ma5 = volume.rolling(window=5).mean()
        vol_ma10 = volume.rolling(window=10).mean()

        return {
            'Volume': volume,
            'Vol_MA5': vol_ma5,
            'Vol_MA10': vol_ma10
        }

    def _calculate_bias(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算乖离率"""
        close = data['close']
        ma6 = close.rolling(window=6).mean()
        ma12 = close.rolling(window=12).mean()
        ma24 = close.rolling(window=24).mean()

        bias6 = (close - ma6) / ma6 * 100
        bias12 = (close - ma12) / ma12 * 100
        bias24 = (close - ma24) / ma24 * 100

        return {
            'BIAS6': bias6,
            'BIAS12': bias12,
            'BIAS24': bias24
        }

    def _calculate_wr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算威廉指标"""
        high = data['high']
        low = data['low']
        close = data['close']

        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        wr = (highest_high - close) / (highest_high - lowest_low) * -100

        return wr

    def _calculate_cci(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算顺势指标"""
        high = data['high']
        low = data['low']
        close = data['close']

        tp = (high + low + close) / 3
        ma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean())))
        cci = (tp - ma_tp) / (0.015 * mad)

        return cci

    def _judge_trend(self, current_price: float, ma_price: float) -> str:
        """判断趋势"""
        if current_price > ma_price * 1.02:
            return '上涨'
        elif current_price < ma_price * 0.98:
            return '下跌'
        else:
            return '震荡'

    def _analyze_ma_arrangement(self, ma5: float, ma20: float, ma60: float) -> str:
        """分析均线排列"""
        if ma5 > ma20 > ma60:
            return '多头排列'
        elif ma5 < ma20 < ma60:
            return '空头排列'
        else:
            return '混乱排列'

    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """计算趋势强度"""
        # 使用价格变化的标准差来衡量趋势强度
        returns = data['close'].pct_change().dropna()
        return float(returns.std() * 100) if len(returns) > 0 else 0.0

    def _find_support_levels(self, data: pd.DataFrame, window: int = 20) -> List[float]:
        """寻找支撑位"""
        low_prices = data['low']

        # 寻找局部最小值
        support_levels = []
        for i in range(window, len(low_prices) - window):
            if low_prices.iloc[i] == low_prices.iloc[i-window:i+window+1].min():
                support_levels.append(float(low_prices.iloc[i]))

        # 去重并排序
        support_levels = sorted(list(set(support_levels)))

        # 返回最近的几个支撑位
        return support_levels[-5:] if len(support_levels) > 5 else support_levels

    def _find_resistance_levels(self, data: pd.DataFrame, window: int = 20) -> List[float]:
        """寻找阻力位"""
        high_prices = data['high']

        # 寻找局部最大值
        resistance_levels = []
        for i in range(window, len(high_prices) - window):
            if high_prices.iloc[i] == high_prices.iloc[i-window:i+window+1].max():
                resistance_levels.append(float(high_prices.iloc[i]))

        # 去重并排序
        resistance_levels = sorted(list(set(resistance_levels)), reverse=True)

        # 返回最近的几个阻力位
        return resistance_levels[:5] if len(resistance_levels) > 5 else resistance_levels

    def _analyze_price_position(self, current_price: float,
                                support_levels: List[float],
                                resistance_levels: List[float]) -> Dict[str, Any]:
        """分析价格相对位置"""
        # 找到最近的支撑位和阻力位
        nearest_support = None
        nearest_resistance = None

        for support in support_levels:
            if support < current_price:
                nearest_support = support
                break

        for resistance in resistance_levels:
            if resistance > current_price:
                nearest_resistance = resistance
                break

        return {
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'support_distance': (current_price - nearest_support) / current_price * 100 if nearest_support else None,
            'resistance_distance': (nearest_resistance - current_price) / current_price * 100 if nearest_resistance else None
        }

    def _load_analysis_strategies(self) -> None:
        """加载分析策略"""
        self._strategies = {
            'golden_cross': self._golden_cross_strategy,
            'death_cross': self._death_cross_strategy,
            'rsi_oversold': self._rsi_oversold_strategy,
            'rsi_overbought': self._rsi_overbought_strategy,
            'bollinger_squeeze': self._bollinger_squeeze_strategy
        }

    async def _golden_cross_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """金叉策略"""
        short_ma = parameters.get('short_ma', 5)
        long_ma = parameters.get('long_ma', 20)

        kdata = await self.data_manager.request_data(
            data_type='kdata',
            stock_code=stock_code,
            period='D',
            parameters={'indicators': ()}
        )
        if kdata is None or kdata.empty:
            return None

        ma_short = self._calculate_ma(kdata, short_ma)
        ma_long = self._calculate_ma(kdata, long_ma)

        if ma_short.iloc[-2] < ma_long.iloc[-2] and ma_short.iloc[-1] > ma_long.iloc[-1]:
            return {'signal': 'buy', 'desc': f'金叉: MA{short_ma}上穿MA{long_ma}'}
        return None

    async def _death_cross_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """死叉策略"""
        short_ma = parameters.get('short_ma', 5)
        long_ma = parameters.get('long_ma', 20)

        kdata = await self.data_manager.request_data(
            data_type='kdata',
            stock_code=stock_code,
            period='D',
            parameters={'indicators': ()}
        )
        if kdata is None or kdata.empty:
            return None

        ma_short = self._calculate_ma(kdata, short_ma)
        ma_long = self._calculate_ma(kdata, long_ma)

        if ma_short.iloc[-2] > ma_long.iloc[-2] and ma_short.iloc[-1] < ma_long.iloc[-1]:
            return {'signal': 'sell', 'desc': f'死叉: MA{short_ma}下穿MA{long_ma}'}
        return None

    async def _rsi_oversold_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """RSI超卖策略"""
        period = parameters.get('period', 14)
        threshold = parameters.get('threshold', 30)

        kdata = await self.data_manager.request_data(
            data_type='kdata',
            stock_code=stock_code,
            period='D',
            parameters={'indicators': ()}
        )
        if kdata is None or kdata.empty:
            return None

        rsi = self._calculate_rsi(kdata, period)
        if rsi.iloc[-1] < threshold:
            return {'signal': 'buy', 'desc': f'RSI({period})进入超卖区: {rsi.iloc[-1]:.2f}'}
        return None

    async def _rsi_overbought_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """RSI超买策略"""
        period = parameters.get('period', 14)
        threshold = parameters.get('threshold', 70)

        kdata = await self.data_manager.request_data(
            data_type='kdata',
            stock_code=stock_code,
            period='D',
            parameters={'indicators': ()}
        )
        if kdata is None or kdata.empty:
            return None

        rsi = self._calculate_rsi(kdata, period)
        if rsi.iloc[-1] > threshold:
            return {'signal': 'sell', 'desc': f'RSI({period})进入超买区: {rsi.iloc[-1]:.2f}'}
        return None

    async def _bollinger_squeeze_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """布林带挤压策略"""
        period = parameters.get('period', 20)

        kdata = await self.data_manager.request_data(
            data_type='kdata',
            stock_code=stock_code,
            period='D',
            parameters={'indicators': ()}
        )
        if kdata is None or kdata.empty:
            return None

        boll = self._calculate_bollinger_bands(kdata)
        band_width = (boll['Upper'] - boll['Lower']) / boll['Middle']

        if band_width.iloc[-1] < 0.1:  # 示例阈值
            return {'signal': 'observe', 'desc': f'布林带收窄，可能预示变盘'}
        return None

    async def start_technical_analysis(self, stock_code: str = None) -> bool:
        """
        异步启动技术分析

        Args:
            stock_code: 股票代码，如果为None则使用当前选择的股票

        Returns:
            是否成功启动分析
        """
        # 确定要分析的股票代码
        target_stock_code = stock_code or self._current_stock_code
        if not target_stock_code:
            logger.warning("No stock selected for technical analysis")
            return False

        logger.info(f"开始技术分析: {target_stock_code}")

        # 运行完整的技术分析
        analysis_results = {}

        # 1. 计算技术指标
        indicators_result = await self.calculate_technical_indicators(
            target_stock_code,
            indicators=['MA', 'MACD', 'RSI', 'KDJ', 'BOLL']
        )
        if indicators_result:
            analysis_results['technical_indicators'] = indicators_result

        # 2. 趋势分析
        trend_result = await self.analyze_trend(target_stock_code)
        if trend_result:
            analysis_results['trend_analysis'] = trend_result

        # 3. 支撑阻力分析
        support_resistance_result = await self.analyze_support_resistance(target_stock_code)
        if support_resistance_result:
            analysis_results['support_resistance'] = support_resistance_result

        # 4. 运行策略分析
        strategy_results = {}
        for strategy_name in self.get_available_strategies():
            strategy_result = await self.run_strategy_analysis(target_stock_code, strategy_name)
            if strategy_result:
                strategy_results[strategy_name] = strategy_result

        if strategy_results:
            analysis_results['strategy_analysis'] = strategy_results

        # 发布分析完成事件
        if analysis_results:
            event = AnalysisCompleteEvent(
                analysis_type='technical',
                stock_code=target_stock_code
            )
            event.data.update({
                'comprehensive_analysis': True,
                'results': analysis_results,
                'analysis_time': datetime.now().isoformat()
            })
            self.event_bus.publish(event)

            logger.info(f"技术分析完成: {target_stock_code}")
            return True
        else:
            logger.warning(f"技术分析未产生结果: {target_stock_code}")
            return False

    def _do_dispose(self) -> None:
        """清理资源"""
        self._current_stock_code = None
        self._analysis_results.clear()
        self._strategies.clear()
        # 确保在退出时也取消所有任务
        try:
            # 不能在非异步方法中直接await，所以我们创建一个临时任务来运行它
            asyncio.run(self.cancel_previous_requests())
        except RuntimeError:
            # 如果没有正在运行的事件循环，则可能无需清理
            pass
        super()._do_dispose()

    async def analyze_stock(self, stock_code: str, analysis_type: str = 'comprehensive', kline_data: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        对指定股票进行全面异步分析。

        Args:
            stock_code (str): 股票代码.
            analysis_type (str, optional): 分析类型. Defaults to 'comprehensive'.
            kline_data (pd.DataFrame, optional): 预先加载的K线数据. Defaults to None.

        Returns:
            Optional[Dict[str, Any]]: 分析结果字典.
        """
        self._ensure_initialized()

        request_id = f"analyze_{stock_code}_{analysis_type}_{int(time.time())}"

        # 使用asyncio.create_task来创建任务，以便我们可以跟踪它
        task = asyncio.create_task(self._perform_comprehensive_analysis(stock_code, kline_data=kline_data))

        async with self.request_lock:
            self.active_requests[request_id] = task

        try:
            # 等待任务完成并获取结果
            result = await task
            return result
        except asyncio.CancelledError:
            logger.info(f"分析任务 {request_id} 已被取消。")
            return None
        except Exception as e:
            logger.error(f"执行股票分析任务 {request_id} 时发生错误: {e}", exc_info=True)
            return None
        finally:
            # 任务完成后，从活动字典中移除
            async with self.request_lock:
                self.active_requests.pop(request_id, None)

    async def _perform_comprehensive_analysis(self, stock_code: str, kline_data: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """执行实际的全面分析"""
        cache_key = f"analysis_{stock_code}_comprehensive"
        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            # 如果没有提供K线数据，则通过数据管理器获取
            if kline_data is None:
                kdata_response = await self.data_manager.request_data(stock_code=stock_code, data_type='kdata')

                # 处理数据结构
                if isinstance(kdata_response, dict):
                    kline_data = kdata_response.get('kline_data')
                else:
                    kline_data = kdata_response

            # 检查数据有效性
            if kline_data is None or kline_data.empty:
                logger.warning(f"无法为 {stock_code} 获取K线数据，分析中止。")
                return None

            # 并行执行所有分析任务
            tasks = {
                "technical_analysis": self.calculate_technical_indicators(stock_code, kline_data=kline_data),
                "trend_analysis": self.analyze_trend(stock_code, kline_data=kline_data),
                "support_resistance": self.analyze_support_resistance(stock_code, kline_data=kline_data),
            }

            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            final_result = {}
            for task_name, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"分析任务 '{task_name}' for {stock_code} 失败: {result}")
                    final_result[task_name] = {"error": str(result)}
                else:
                    final_result[task_name] = result

            self.put_to_cache(cache_key, final_result)
            return final_result

        except Exception as e:
            logger.error(f"为 {stock_code} 执行全面分析时发生意外错误: {e}", exc_info=True)
            return {"error": str(e)}

    def calculate_ma(self, data: pd.DataFrame, period: int) -> pd.Series:
        """计算移动平均线"""
        return self._calculate_ma(data, period)

    def calculate_macd(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算MACD的公共接口"""
        return self._calculate_macd(data)

    def calculate_bollinger_bands(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算布林带的公共接口"""
        return self._calculate_bollinger_bands(data)

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI的公共接口"""
        return self._calculate_rsi(data, period)

    def calculate_boll(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算布林带的公共接口 (别名)"""
        return self._calculate_bollinger_bands(data)

    def calculate_kdj(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算KDJ指标的公共接口"""
        return self._calculate_kdj(data)

    def calculate_indicator(self, data: pd.DataFrame, indicator_name: str) -> Optional[Union[Dict[str, Any], pd.Series, List]]:
        """
        通用指标计算方法，根据指标名称动态调用相应的计算函数

        Args:
            data: 股票数据
            indicator_name: 指标名称

        Returns:
            指标计算结果，可能是字典、Series或列表，如果指标不存在则返回None
        """
        try:
            indicator_name = indicator_name.upper()

            # 检查是否有直接匹配的计算方法
            method_name = f"calculate_{indicator_name.lower()}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                return method(data)

            # 检查是否为MA类型指标
            if indicator_name.startswith('MA') and len(indicator_name) > 2:
                try:
                    period = int(indicator_name[2:])
                    return self.calculate_ma(data, period)
                except ValueError:
                    logger.warning(f"无法从指标名称解析周期: {indicator_name}")

            # 其他常见指标的映射
            indicator_map = {
                'BOLL': 'calculate_bollinger_bands',
                'RSI': 'calculate_rsi',
                'KDJ': 'calculate_kdj',
                'MACD': 'calculate_macd'
            }

            if indicator_name in indicator_map and hasattr(self, indicator_map[indicator_name]):
                method = getattr(self, indicator_map[indicator_name])
                return method(data)

            # 记录找不到的指标
            logger.warning(f"找不到指标计算方法: {indicator_name}")
            return None

        except Exception as e:
            logger.error(f"计算指标 {indicator_name} 时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
