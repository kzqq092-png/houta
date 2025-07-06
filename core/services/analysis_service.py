"""
分析服务模块

负责技术分析、策略分析和数据分析。
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from .base_service import CacheableService, ConfigurableService
from ..events import AnalysisCompleteEvent, StockSelectedEvent


logger = logging.getLogger(__name__)


class AnalysisService(CacheableService, ConfigurableService):
    """
    分析服务

    负责技术分析、策略分析和数据分析。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, cache_size: int = 100, **kwargs):
        """
        初始化分析服务

        Args:
            config: 服务配置
            cache_size: 缓存大小
            **kwargs: 其他参数
        """
        # 初始化各个基类
        CacheableService.__init__(self, cache_size=cache_size, **kwargs)
        ConfigurableService.__init__(self, config=config, **kwargs)
        self._current_stock_code = None
        self._analysis_results = {}
        self._strategies = {}

    def _do_initialize(self) -> None:
        """初始化分析服务"""
        try:
            # 初始化分析策略
            self._load_analysis_strategies()

            # 订阅股票选择事件
            self.event_bus.subscribe(StockSelectedEvent, self._on_stock_selected)

            logger.info("Analysis service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize analysis service: {e}")
            raise

    def calculate_technical_indicators(self, stock_code: str,
                                       indicators: List[str] = None,
                                       period: str = 'D',
                                       time_range: int = 365) -> Optional[Dict[str, Any]]:
        """
        计算技术指标

        Args:
            stock_code: 股票代码
            indicators: 指标列表
            period: 周期
            time_range: 时间范围

        Returns:
            技术指标结果
        """
        self._ensure_initialized()

        indicators = indicators or ['MA5', 'MA10', 'MA20', 'MACD', 'RSI']
        cache_key = f"indicators_{stock_code}_{period}_{time_range}_{hash(tuple(indicators))}"

        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            # 获取股票数据
            stock_data = self._get_stock_data(stock_code, period, time_range)
            if stock_data is None or stock_data.empty:
                logger.warning(f"No data available for {stock_code}")
                return None

            results = {}

            # 计算各种技术指标
            for indicator in indicators:
                if indicator.startswith('MA') and not indicator.startswith('MACD'):
                    try:
                        period_num = int(indicator[2:])
                        results[indicator] = self._calculate_ma(stock_data, period_num)
                    except ValueError:
                        logger.warning(f"Cannot parse period from indicator: {indicator}")
                        continue
                elif indicator == 'MACD':
                    results['MACD'] = self._calculate_macd(stock_data)
                elif indicator == 'RSI':
                    results['RSI'] = self._calculate_rsi(stock_data)
                elif indicator == 'KDJ':
                    results['KDJ'] = self._calculate_kdj(stock_data)
                elif indicator == 'BOLL':
                    results['BOLL'] = self._calculate_bollinger_bands(stock_data)
                elif indicator == 'VOL':
                    results['VOL'] = self._calculate_volume_indicators(stock_data)
                elif indicator == 'BIAS':
                    results['BIAS'] = self._calculate_bias(stock_data)
                elif indicator == 'WR':
                    results['WR'] = self._calculate_wr(stock_data)
                elif indicator == 'CCI':
                    results['CCI'] = self._calculate_cci(stock_data)

            # 缓存结果
            self.put_to_cache(cache_key, results)

            return results

        except Exception as e:
            logger.error(f"Failed to calculate technical indicators for {stock_code}: {e}")
            return None

    def analyze_trend(self, stock_code: str, period: str = 'D',
                      time_range: int = 90) -> Optional[Dict[str, Any]]:
        """
        趋势分析

        Args:
            stock_code: 股票代码
            period: 周期
            time_range: 时间范围

        Returns:
            趋势分析结果
        """
        self._ensure_initialized()

        cache_key = f"trend_{stock_code}_{period}_{time_range}"
        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            stock_data = self._get_stock_data(stock_code, period, time_range)
            if stock_data is None or stock_data.empty:
                return None

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
            ma_arrangement = self._analyze_ma_arrangement(ma5.iloc[-1], ma20.iloc[-1], ma60.iloc[-1])

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

            # 缓存结果
            self.put_to_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Failed to analyze trend for {stock_code}: {e}")
            return None

    def analyze_support_resistance(self, stock_code: str, period: str = 'D',
                                   time_range: int = 180) -> Optional[Dict[str, Any]]:
        """
        支撑阻力分析

        Args:
            stock_code: 股票代码
            period: 周期
            time_range: 时间范围

        Returns:
            支撑阻力分析结果
        """
        self._ensure_initialized()

        cache_key = f"support_resistance_{stock_code}_{period}_{time_range}"
        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            stock_data = self._get_stock_data(stock_code, period, time_range)
            if stock_data is None or stock_data.empty:
                return None

            # 寻找支撑位和阻力位
            support_levels = self._find_support_levels(stock_data)
            resistance_levels = self._find_resistance_levels(stock_data)

            # 当前价格相对位置
            current_price = stock_data['close'].iloc[-1]
            position_analysis = self._analyze_price_position(
                current_price, support_levels, resistance_levels
            )

            result = {
                'stock_code': stock_code,
                'current_price': current_price,
                'support_levels': support_levels,
                'resistance_levels': resistance_levels,
                'position_analysis': position_analysis,
                'analysis_time': datetime.now().isoformat()
            }

            # 缓存结果
            self.put_to_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Failed to analyze support/resistance for {stock_code}: {e}")
            return None

    def run_strategy_analysis(self, stock_code: str, strategy_name: str,
                              parameters: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        运行策略分析

        Args:
            stock_code: 股票代码
            strategy_name: 策略名称
            parameters: 策略参数

        Returns:
            策略分析结果
        """
        self._ensure_initialized()

        if strategy_name not in self._strategies:
            logger.warning(f"Unknown strategy: {strategy_name}")
            return None

        cache_key = f"strategy_{strategy_name}_{stock_code}_{hash(str(parameters))}"
        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            strategy_func = self._strategies[strategy_name]
            result = strategy_func(stock_code, parameters or {})

            if result:
                result['strategy_name'] = strategy_name
                result['analysis_time'] = datetime.now().isoformat()

                # 缓存结果
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
            logger.error(f"Failed to run strategy {strategy_name} for {stock_code}: {e}")
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

    def _on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件"""
        try:
            stock_code = event.stock_code

            # 避免重复处理相同股票
            if self._current_stock_code == stock_code:
                logger.debug(f"Analysis service already handling {stock_code}, skipping")
                return

            self._current_stock_code = stock_code

            # 获取股票服务
            stock_service = self._get_stock_service()
            if not stock_service:
                logger.warning("Stock service not available for analysis")
                return

            # 快速检查股票是否有数据
            try:
                test_data = stock_service.get_stock_data(stock_code, period='D', count=1)
                if test_data is None or test_data.empty:
                    logger.warning(f"No data available for {stock_code}")
                    return
            except Exception as e:
                logger.warning(f"Failed to check data for {stock_code}: {e}")
                return

            # 异步运行自动分析，避免阻塞
            self._run_auto_analysis_async(stock_code)

        except Exception as e:
            logger.error(f"Failed to handle stock selected event: {e}")

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
        """运行自动分析"""
        try:
            # 只进行基础分析，避免过度计算
            logger.info(f"Starting basic analysis for {stock_code}")

            # 计算基础技术指标（减少数据量）
            indicators = self.calculate_technical_indicators(stock_code, time_range=60)

            if indicators:
                # 简单的趋势分析
                trend = self.analyze_trend(stock_code, time_range=30)

                logger.info(f"Basic analysis completed for {stock_code}")
            else:
                logger.warning(f"No indicators calculated for {stock_code}")

        except Exception as e:
            logger.error(f"Failed to run auto analysis for {stock_code}: {e}")

    def _get_stock_service(self):
        """获取股票服务"""
        try:
            if hasattr(self, 'service_container') and self.service_container:
                from . import StockService
                return self.service_container.get_service(StockService)
            else:
                # 通过事件总线获取服务容器
                from ..containers import get_service_container
                from .stock_service import StockService
                container = get_service_container()
                return container.try_resolve(StockService)
        except Exception as e:
            logger.error(f"Failed to get stock service: {e}")
        return None

    def _get_stock_data(self, stock_code: str, period: str, time_range: int) -> Optional[pd.DataFrame]:
        """获取股票数据"""
        try:
            from ..containers import get_service_container
            from .stock_service import StockService
            container = get_service_container()
            stock_service = container.try_resolve(StockService)

            if stock_service:
                return stock_service.get_stock_data(stock_code, period, time_range)
            return None

        except Exception as e:
            logger.error(f"Failed to get stock data: {e}")
            return None

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
        mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
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

    def _golden_cross_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """黄金交叉策略"""
        return {
            'signal': 'BUY',
            'confidence': 0.8,
            'description': '黄金交叉信号'
        }

    def _death_cross_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """死亡交叉策略"""
        return {
            'signal': 'SELL',
            'confidence': 0.8,
            'description': '死亡交叉信号'
        }

    def _rsi_oversold_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """RSI超卖策略"""
        return {
            'signal': 'BUY',
            'confidence': 0.7,
            'description': 'RSI超卖信号'
        }

    def _rsi_overbought_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """RSI超买策略"""
        return {
            'signal': 'SELL',
            'confidence': 0.7,
            'description': 'RSI超买信号'
        }

    def _bollinger_squeeze_strategy(self, stock_code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """布林带收窄策略"""
        return {
            'signal': 'WATCH',
            'confidence': 0.6,
            'description': '布林带收窄信号'
        }

    def start_technical_analysis(self, stock_code: str = None) -> bool:
        """
        启动技术分析

        Args:
            stock_code: 股票代码，如果为None则使用当前选择的股票

        Returns:
            是否成功启动分析
        """
        try:
            # 确定要分析的股票代码
            target_stock_code = stock_code or self._current_stock_code
            if not target_stock_code:
                logger.warning("No stock selected for technical analysis")
                return False

            logger.info(f"开始技术分析: {target_stock_code}")

            # 运行完整的技术分析
            analysis_results = {}

            # 1. 计算技术指标
            indicators_result = self.calculate_technical_indicators(
                target_stock_code,
                indicators=['MA', 'MACD', 'RSI', 'KDJ', 'BOLL']
            )
            if indicators_result:
                analysis_results['technical_indicators'] = indicators_result

            # 2. 趋势分析
            trend_result = self.analyze_trend(target_stock_code)
            if trend_result:
                analysis_results['trend_analysis'] = trend_result

            # 3. 支撑阻力分析
            support_resistance_result = self.analyze_support_resistance(target_stock_code)
            if support_resistance_result:
                analysis_results['support_resistance'] = support_resistance_result

            # 4. 运行策略分析
            strategy_results = {}
            for strategy_name in self.get_available_strategies():
                strategy_result = self.run_strategy_analysis(target_stock_code, strategy_name)
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

        except Exception as e:
            logger.error(f"Failed to start technical analysis: {e}")
            return False

    def _do_dispose(self) -> None:
        """清理资源"""
        self._current_stock_code = None
        self._analysis_results.clear()
        self._strategies.clear()
        super()._do_dispose()

    def analyze_stock(self, stock_code: str, analysis_type: str = 'comprehensive') -> Optional[Dict[str, Any]]:
        """
        综合股票分析

        Args:
            stock_code: 股票代码
            analysis_type: 分析类型 ('comprehensive', 'technical', 'trend', 'support_resistance')

        Returns:
            分析结果
        """
        self._ensure_initialized()

        try:
            logger.info(f"Starting {analysis_type} analysis for {stock_code}")

            if analysis_type == 'comprehensive':
                # 综合分析
                result = {
                    'stock_code': stock_code,
                    'analysis_type': analysis_type,
                    'timestamp': datetime.now().isoformat()
                }

                # 技术指标分析
                technical_result = self.calculate_technical_indicators(stock_code)
                if technical_result:
                    result['technical_indicators'] = technical_result

                # 趋势分析
                trend_result = self.analyze_trend(stock_code)
                if trend_result:
                    result['trend_analysis'] = trend_result

                # 支撑阻力分析
                sr_result = self.analyze_support_resistance(stock_code)
                if sr_result:
                    result['support_resistance'] = sr_result

                return result

            elif analysis_type == 'technical':
                return self.calculate_technical_indicators(stock_code)

            elif analysis_type == 'trend':
                return self.analyze_trend(stock_code)

            elif analysis_type == 'support_resistance':
                return self.analyze_support_resistance(stock_code)

            else:
                logger.warning(f"Unknown analysis type: {analysis_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to analyze stock {stock_code}: {e}")
            return None

    def calculate_ma(self, data: pd.DataFrame, period: int) -> pd.Series:
        """计算移动平均线的公共接口"""
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
