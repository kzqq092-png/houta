from loguru import logger
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线数据集成情绪分析器
基于实时K线数据计算技术指标和市场情绪的综合分析系统
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
import time
from concurrent.futures import ThreadPoolExecutor
import os

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    talib = None


@dataclass
class TechnicalIndicator:
    """技术指标数据结构"""
    name: str
    value: float
    signal: str  # "BUY", "SELL", "HOLD"
    strength: float  # 0-1之间的信号强度
    timestamp: datetime
    description: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KLineSentimentResult:
    """K线情绪分析结果"""
    symbol: str
    timestamp: datetime
    price_data: Dict[str, float]  # OHLCV数据
    technical_indicators: List[TechnicalIndicator]
    sentiment_score: float  # -1到1之间
    market_mood: str  # "BULLISH", "BEARISH", "NEUTRAL"
    confidence: float  # 0-1之间
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    recommendations: List[str]
    market_strength: float  # 市场强度 0-1
    volatility_indicator: float  # 波动率指标
    composite_score: float  # 综合评分


class KLineSentimentAnalyzer:
    """K线数据集成情绪分析器"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logger

        # 默认配置
        self.default_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMZN"]
        self.update_interval = self.config.get('update_interval', 300)  # 5分钟
        self.cache_ttl = self.config.get('cache_ttl', 900)  # 15分钟

        # 数据缓存
        self.data_cache = {}
        self.last_update = {}

        # 线程池
        self.executor = ThreadPoolExecutor(os.cpu_count() * 2)

        # 检查依赖
        self.check_dependencies()

    def check_dependencies(self):
        """检查必要依赖"""
        if not YFINANCE_AVAILABLE:
            self.logger.warning("yfinance not available, using simulated data")
        if not TALIB_AVAILABLE:
            self.logger.warning("talib not available, using basic technical indicators")

    def get_kline_data(self, symbol: str, period: str = "1d", interval: str = "1h") -> pd.DataFrame:
        """获取K线数据"""
        try:
            if not YFINANCE_AVAILABLE:
                return self._generate_simulated_kline_data(symbol)

            # 检查缓存
            cache_key = f"{symbol}_{period}_{interval}"
            if cache_key in self.data_cache:
                cache_time, data = self.data_cache[cache_key]
                if time.time() - cache_time < self.cache_ttl:
                    return data

            # 获取真实数据
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)

            if data.empty:
                self.logger.warning(f"No data for {symbol}, using simulated data")
                return self._generate_simulated_kline_data(symbol)

            # 缓存数据
            self.data_cache[cache_key] = (time.time(), data)

            return data

        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            return self._generate_simulated_kline_data(symbol)

    def _generate_simulated_kline_data(self, symbol: str) -> pd.DataFrame:
        """生成模拟K线数据"""
        # 生成24小时的小时级数据
        dates = pd.date_range(end=datetime.now(), periods=24, freq='h')

        # 基础价格（根据symbol设定）
        base_prices = {
            "AAPL": 150.0,
            "MSFT": 300.0,
            "GOOGL": 2500.0,
            "TSLA": 200.0,
            "NVDA": 400.0,
            "AMZN": 150.0
        }
        base_price = base_prices.get(symbol, 100.0)

        # 生成随机价格数据
        np.random.seed(hash(symbol) % 2**32)
        price_changes = np.random.normal(0, 0.02, len(dates))  # 2%标准差

        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []

        current_price = base_price

        for i, change in enumerate(price_changes):
            open_price = current_price
            close_price = open_price * (1 + change)

            # 计算高低价
            daily_range = abs(change) * 2 + 0.01
            high_price = max(open_price, close_price) * (1 + daily_range/2)
            low_price = min(open_price, close_price) * (1 - daily_range/2)

            opens.append(open_price)
            highs.append(high_price)
            lows.append(low_price)
            closes.append(close_price)
            volumes.append(np.random.randint(1000000, 10000000))

            current_price = close_price

        data = pd.DataFrame({
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes
        }, index=dates)

        return data

    def calculate_technical_indicators(self, data: pd.DataFrame) -> List[TechnicalIndicator]:
        """计算技术指标"""
        indicators = []

        if data.empty or len(data) < 14:
            return indicators

        try:
            # RSI 指标
            rsi = self._calculate_rsi(data['Close'])
            if not np.isnan(rsi):
                rsi_signal = "BUY" if rsi < 30 else "SELL" if rsi > 70 else "HOLD"
                rsi_strength = abs(rsi - 50) / 50
                indicators.append(TechnicalIndicator(
                    name="RSI",
                    value=rsi,
                    signal=rsi_signal,
                    strength=rsi_strength,
                    timestamp=datetime.now(),
                    description=f"相对强弱指数: {rsi:.2f}"
                ))

            # MACD 指标
            macd_line, signal_line, histogram = self._calculate_macd(data['Close'])
            if not np.isnan(macd_line):
                macd_signal = "BUY" if macd_line > signal_line else "SELL"
                macd_strength = abs(histogram) / (abs(macd_line) + 0.001)
                indicators.append(TechnicalIndicator(
                    name="MACD",
                    value=macd_line,
                    signal=macd_signal,
                    strength=min(macd_strength, 1.0),
                    timestamp=datetime.now(),
                    description=f"MACD: {macd_line:.4f}, 信号线: {signal_line:.4f}"
                ))

            # 布林带指标
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(data['Close'])
            current_price = data['Close'].iloc[-1]
            if not np.isnan(bb_upper):
                if current_price > bb_upper:
                    bb_signal = "SELL"
                    bb_strength = (current_price - bb_upper) / bb_upper
                elif current_price < bb_lower:
                    bb_signal = "BUY"
                    bb_strength = (bb_lower - current_price) / bb_lower
                else:
                    bb_signal = "HOLD"
                    bb_strength = abs(current_price - bb_middle) / (bb_upper - bb_middle)

                indicators.append(TechnicalIndicator(
                    name="Bollinger Bands",
                    value=current_price,
                    signal=bb_signal,
                    strength=min(bb_strength, 1.0),
                    timestamp=datetime.now(),
                    description=f"布林带: 上轨{bb_upper:.2f}, 中轨{bb_middle:.2f}, 下轨{bb_lower:.2f}"
                ))

            # 移动平均线
            ma_5 = data['Close'].rolling(window=5).mean().iloc[-1]
            ma_20 = data['Close'].rolling(window=min(20, len(data))).mean().iloc[-1]

            if not np.isnan(ma_5) and not np.isnan(ma_20):
                ma_signal = "BUY" if ma_5 > ma_20 else "SELL"
                ma_strength = abs(ma_5 - ma_20) / ma_20
                indicators.append(TechnicalIndicator(
                    name="Moving Average",
                    value=ma_5,
                    signal=ma_signal,
                    strength=min(ma_strength, 1.0),
                    timestamp=datetime.now(),
                    description=f"MA5: {ma_5:.2f}, MA20: {ma_20:.2f}"
                ))

            # 成交量指标
            volume_ma = data['Volume'].rolling(window=5).mean().iloc[-1]
            current_volume = data['Volume'].iloc[-1]
            volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1.0

            if volume_ratio > 1.5:
                volume_signal = "BUY" if current_price > data['Close'].iloc[-2] else "SELL"
                volume_strength = min((volume_ratio - 1) / 2, 1.0)
            else:
                volume_signal = "HOLD"
                volume_strength = 0.3

            indicators.append(TechnicalIndicator(
                name="Volume",
                value=current_volume,
                signal=volume_signal,
                strength=volume_strength,
                timestamp=datetime.now(),
                description=f"成交量: {current_volume:,.0f}, 平均: {volume_ma:,.0f}"
            ))

            # 波动率指标
            volatility = data['Close'].pct_change().std() * np.sqrt(24)  # 年化波动率
            vol_signal = "HOLD"
            vol_strength = min(volatility / 0.5, 1.0)  # 正常化到0-1

            indicators.append(TechnicalIndicator(
                name="Volatility",
                value=volatility,
                signal=vol_signal,
                strength=vol_strength,
                timestamp=datetime.now(),
                description=f"年化波动率: {volatility:.2%}"
            ))

        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {e}")

        return indicators

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return np.nan

        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1] if not rsi.empty else np.nan

    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """计算MACD指标"""
        if len(prices) < slow + signal:
            return np.nan, np.nan, np.nan

        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line

        return (
            macd_line.iloc[-1] if not macd_line.empty else np.nan,
            signal_line.iloc[-1] if not signal_line.empty else np.nan,
            histogram.iloc[-1] if not histogram.empty else np.nan
        )

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std: float = 2.0) -> Tuple[float, float, float]:
        """计算布林带指标"""
        if len(prices) < period:
            return np.nan, np.nan, np.nan

        rolling_mean = prices.rolling(window=period).mean()
        rolling_std = prices.rolling(window=period).std()

        upper_band = rolling_mean + (rolling_std * std)
        lower_band = rolling_mean - (rolling_std * std)

        return (
            upper_band.iloc[-1] if not upper_band.empty else np.nan,
            rolling_mean.iloc[-1] if not rolling_mean.empty else np.nan,
            lower_band.iloc[-1] if not lower_band.empty else np.nan
        )

    def calculate_sentiment_score(self, indicators: List[TechnicalIndicator]) -> Tuple[float, str, float]:
        """计算综合情绪得分"""
        if not indicators:
            return 0.0, "NEUTRAL", 0.5

        # 权重配置
        weights = {
            "RSI": 0.25,
            "MACD": 0.25,
            "Bollinger Bands": 0.20,
            "Moving Average": 0.15,
            "Volume": 0.10,
            "Volatility": 0.05
        }

        total_score = 0.0
        total_weight = 0.0
        confidence_scores = []

        for indicator in indicators:
            weight = weights.get(indicator.name, 0.1)

            # 信号转换为分数
            if indicator.signal == "BUY":
                signal_score = 1.0
            elif indicator.signal == "SELL":
                signal_score = -1.0
            else:
                signal_score = 0.0

            # 加权计算
            weighted_score = signal_score * indicator.strength * weight
            total_score += weighted_score
            total_weight += weight

            confidence_scores.append(indicator.strength)

        # 归一化得分
        if total_weight > 0:
            sentiment_score = total_score / total_weight
        else:
            sentiment_score = 0.0

        # 确定市场情绪
        if sentiment_score > 0.3:
            market_mood = "BULLISH"
        elif sentiment_score < -0.3:
            market_mood = "BEARISH"
        else:
            market_mood = "NEUTRAL"

        # 计算置信度
        confidence = np.mean(confidence_scores) if confidence_scores else 0.5

        return sentiment_score, market_mood, confidence

    def generate_recommendations(self, result: KLineSentimentResult) -> List[str]:
        """生成交易建议"""
        recommendations = []

        # 基于市场情绪的建议
        if result.market_mood == "BULLISH" and result.confidence > 0.7:
            recommendations.append("市场情绪积极，考虑逢低买入")
            if result.risk_level == "LOW":
                recommendations.append("风险较低，可以考虑增加仓位")
        elif result.market_mood == "BEARISH" and result.confidence > 0.7:
            recommendations.append("市场情绪悲观，建议减仓或观望")
            if result.risk_level == "HIGH":
                recommendations.append("高风险信号，建议设置止损")
        else:
            recommendations.append("市场中性，建议保持当前仓位")

        # 基于波动率的建议
        if result.volatility_indicator > 0.8:
            recommendations.append("高波动率环境，注意风险控制")
        elif result.volatility_indicator < 0.3:
            recommendations.append("低波动率，可能出现突破机会")

        # 基于技术指标的建议
        rsi_indicator = next((ind for ind in result.technical_indicators if ind.name == "RSI"), None)
        if rsi_indicator:
            if rsi_indicator.value < 30:
                recommendations.append("RSI超卖，可能反弹机会")
            elif rsi_indicator.value > 70:
                recommendations.append("RSI超买，注意回调风险")

        # 基于成交量的建议
        volume_indicator = next((ind for ind in result.technical_indicators if ind.name == "Volume"), None)
        if volume_indicator and volume_indicator.signal == "BUY":
            recommendations.append("成交量放大，趋势可能延续")

        if not recommendations:
            recommendations.append("当前无明确信号，建议继续观察")

        return recommendations

    def analyze_symbol(self, symbol: str) -> KLineSentimentResult:
        """分析单个股票的K线情绪"""
        try:
            # 获取K线数据
            kline_data = self.get_kline_data(symbol)

            if kline_data.empty:
                raise ValueError(f"No data available for {symbol}")

            # 计算技术指标
            indicators = self.calculate_technical_indicators(kline_data)

            # 计算情绪得分
            sentiment_score, market_mood, confidence = self.calculate_sentiment_score(indicators)

            # 获取最新价格数据
            latest_data = kline_data.iloc[-1]
            price_data = {
                'open': float(latest_data['Open']),
                'high': float(latest_data['High']),
                'low': float(latest_data['Low']),
                'close': float(latest_data['Close']),
                'volume': float(latest_data['Volume'])
            }

            # 计算风险级别
            volatility = kline_data['Close'].pct_change().std() * np.sqrt(24)
            if volatility > 0.4:
                risk_level = "HIGH"
            elif volatility > 0.2:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            # 计算市场强度
            market_strength = min(confidence * (1 + abs(sentiment_score)), 1.0)

            # 计算综合评分
            composite_score = (sentiment_score + 1) / 2  # 转换到0-1范围

            # 创建结果对象
            result = KLineSentimentResult(
                symbol=symbol,
                timestamp=datetime.now(),
                price_data=price_data,
                technical_indicators=indicators,
                sentiment_score=sentiment_score,
                market_mood=market_mood,
                confidence=confidence,
                risk_level=risk_level,
                recommendations=[],
                market_strength=market_strength,
                volatility_indicator=min(volatility / 0.5, 1.0),
                composite_score=composite_score
            )

            # 生成建议
            result.recommendations = self.generate_recommendations(result)

            return result

        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {e}")

            # 返回默认结果
            return KLineSentimentResult(
                symbol=symbol,
                timestamp=datetime.now(),
                price_data={'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0},
                technical_indicators=[],
                sentiment_score=0.0,
                market_mood="NEUTRAL",
                confidence=0.0,
                risk_level="UNKNOWN",
                recommendations=[" 数据获取失败，无法分析"],
                market_strength=0.0,
                volatility_indicator=0.0,
                composite_score=0.5
            )

    async def analyze_multiple_symbols(self, symbols: List[str] = None) -> Dict[str, KLineSentimentResult]:
        """异步分析多个股票"""
        if symbols is None:
            symbols = self.default_symbols

        # 使用线程池并行处理
        loop = asyncio.get_event_loop()
        tasks = []

        for symbol in symbols:
            task = loop.run_in_executor(self.executor, self.analyze_symbol, symbol)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 整理结果
        symbol_results = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                self.logger.error(f"Error analyzing {symbol}: {result}")
                continue
            symbol_results[symbol] = result

        return symbol_results

    def get_market_overview(self, results: Dict[str, KLineSentimentResult]) -> Dict[str, Any]:
        """获取市场总览"""
        if not results:
            return {
                'total_symbols': 0,
                'bullish_count': 0,
                'bearish_count': 0,
                'neutral_count': 0,
                'average_sentiment': 0.0,
                'market_strength': 0.0,
                'overall_mood': 'UNKNOWN'
            }

        sentiment_scores = [r.sentiment_score for r in results.values()]
        market_moods = [r.market_mood for r in results.values()]

        bullish_count = market_moods.count('BULLISH')
        bearish_count = market_moods.count('BEARISH')
        neutral_count = market_moods.count('NEUTRAL')

        average_sentiment = np.mean(sentiment_scores)
        market_strength = np.mean([r.market_strength for r in results.values()])

        # 确定整体市场情绪
        if bullish_count > bearish_count and average_sentiment > 0.2:
            overall_mood = 'BULLISH'
        elif bearish_count > bullish_count and average_sentiment < -0.2:
            overall_mood = 'BEARISH'
        else:
            overall_mood = 'NEUTRAL'

        return {
            'total_symbols': len(results),
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
            'average_sentiment': average_sentiment,
            'market_strength': market_strength,
            'overall_mood': overall_mood,
            'timestamp': datetime.now()
        }


# 单例实例
_kline_analyzer_instance = None


def get_kline_sentiment_analyzer(config: Dict[str, Any] = None) -> KLineSentimentAnalyzer:
    """获取K线情绪分析器单例"""
    global _kline_analyzer_instance
    if _kline_analyzer_instance is None:
        _kline_analyzer_instance = KLineSentimentAnalyzer(config)
    return _kline_analyzer_instance
