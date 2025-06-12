#!/usr/bin/env python3
"""
趋势跟踪策略模块

实现多种趋势跟踪策略，包括：
- 移动平均趋势策略
- 突破策略
- 动量策略
- 自适应趋势策略
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


class TrendDirection(Enum):
    """趋势方向"""
    UP = "up"           # 上升趋势
    DOWN = "down"       # 下降趋势
    SIDEWAYS = "sideways"  # 横盘趋势


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"         # 买入信号
    SELL = "sell"       # 卖出信号
    HOLD = "hold"       # 持有信号


@dataclass
class TradingSignal:
    """交易信号数据类"""
    timestamp: datetime
    signal_type: SignalType
    price: float
    confidence: float
    strategy_name: str
    reason: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class MovingAverageTrendStrategy:
    """移动平均趋势策略"""

    def __init__(self,
                 short_period: int = 20,
                 long_period: int = 50,
                 signal_period: int = 10):
        """
        初始化移动平均趋势策略

        Args:
            short_period: 短期移动平均周期
            long_period: 长期移动平均周期
            signal_period: 信号确认周期
        """
        self.short_period = short_period
        self.long_period = long_period
        self.signal_period = signal_period
        self.name = "MovingAverageTrend"

    def generate_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """
        生成交易信号

        Args:
            data: 包含OHLCV数据的DataFrame

        Returns:
            交易信号列表
        """
        signals = []

        if len(data) < self.long_period:
            return signals

        # 计算移动平均线
        data['MA_short'] = data['close'].rolling(window=self.short_period).mean()
        data['MA_long'] = data['close'].rolling(window=self.long_period).mean()

        # 计算信号
        data['signal'] = 0
        data.loc[data['MA_short'] > data['MA_long'], 'signal'] = 1
        data.loc[data['MA_short'] < data['MA_long'], 'signal'] = -1

        # 信号变化点
        data['signal_change'] = data['signal'].diff()

        for i in range(self.long_period, len(data)):
            if data.iloc[i]['signal_change'] == 2:  # 从-1变为1，买入信号
                confidence = self._calculate_confidence(data.iloc[i-self.signal_period:i+1])

                signals.append(TradingSignal(
                    timestamp=data.index[i],
                    signal_type=SignalType.BUY,
                    price=data.iloc[i]['close'],
                    confidence=confidence,
                    strategy_name=self.name,
                    reason=f"短期MA({self.short_period})上穿长期MA({self.long_period})",
                    stop_loss=data.iloc[i]['close'] * 0.95,
                    take_profit=data.iloc[i]['close'] * 1.1
                ))

            elif data.iloc[i]['signal_change'] == -2:  # 从1变为-1，卖出信号
                confidence = self._calculate_confidence(data.iloc[i-self.signal_period:i+1])

                signals.append(TradingSignal(
                    timestamp=data.index[i],
                    signal_type=SignalType.SELL,
                    price=data.iloc[i]['close'],
                    confidence=confidence,
                    strategy_name=self.name,
                    reason=f"短期MA({self.short_period})下穿长期MA({self.long_period})",
                    stop_loss=data.iloc[i]['close'] * 1.05,
                    take_profit=data.iloc[i]['close'] * 0.9
                ))

        return signals

    def _calculate_confidence(self, recent_data: pd.DataFrame) -> float:
        """计算信号置信度"""
        if len(recent_data) < 2:
            return 0.5

        # 基于价格趋势强度计算置信度
        price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        volatility = recent_data['close'].std() / recent_data['close'].mean()

        # 趋势强度
        trend_strength = abs(price_change) / (volatility + 0.01)
        confidence = min(0.9, max(0.1, trend_strength / 2))

        return confidence


class BreakoutStrategy:
    """突破策略"""

    def __init__(self,
                 lookback_period: int = 20,
                 volume_threshold: float = 1.5,
                 min_breakout_pct: float = 0.02):
        """
        初始化突破策略

        Args:
            lookback_period: 回看周期
            volume_threshold: 成交量阈值倍数
            min_breakout_pct: 最小突破幅度
        """
        self.lookback_period = lookback_period
        self.volume_threshold = volume_threshold
        self.min_breakout_pct = min_breakout_pct
        self.name = "Breakout"

    def generate_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """生成突破信号"""
        signals = []

        if len(data) < self.lookback_period:
            return signals

        # 计算支撑阻力位
        data['resistance'] = data['high'].rolling(window=self.lookback_period).max()
        data['support'] = data['low'].rolling(window=self.lookback_period).min()
        data['avg_volume'] = data['volume'].rolling(window=self.lookback_period).mean()

        for i in range(self.lookback_period, len(data)):
            current = data.iloc[i]
            prev = data.iloc[i-1]

            # 向上突破
            if (current['close'] > prev['resistance'] and
                (current['close'] - prev['resistance']) / prev['resistance'] > self.min_breakout_pct and
                    current['volume'] > prev['avg_volume'] * self.volume_threshold):

                confidence = self._calculate_breakout_confidence(data.iloc[i-5:i+1], 'up')

                signals.append(TradingSignal(
                    timestamp=data.index[i],
                    signal_type=SignalType.BUY,
                    price=current['close'],
                    confidence=confidence,
                    strategy_name=self.name,
                    reason=f"向上突破阻力位{prev['resistance']:.3f}，成交量放大",
                    stop_loss=prev['resistance'] * 0.98,
                    take_profit=current['close'] * 1.15
                ))

            # 向下突破
            elif (current['close'] < prev['support'] and
                  (prev['support'] - current['close']) / prev['support'] > self.min_breakout_pct and
                  current['volume'] > prev['avg_volume'] * self.volume_threshold):

                confidence = self._calculate_breakout_confidence(data.iloc[i-5:i+1], 'down')

                signals.append(TradingSignal(
                    timestamp=data.index[i],
                    signal_type=SignalType.SELL,
                    price=current['close'],
                    confidence=confidence,
                    strategy_name=self.name,
                    reason=f"向下突破支撑位{prev['support']:.3f}，成交量放大",
                    stop_loss=prev['support'] * 1.02,
                    take_profit=current['close'] * 0.85
                ))

        return signals

    def _calculate_breakout_confidence(self, recent_data: pd.DataFrame, direction: str) -> float:
        """计算突破信号置信度"""
        if len(recent_data) < 2:
            return 0.5

        # 成交量确认
        volume_ratio = recent_data['volume'].iloc[-1] / recent_data['volume'].mean()
        volume_score = min(1.0, volume_ratio / 3.0)

        # 价格动量
        price_momentum = abs(recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        momentum_score = min(1.0, price_momentum * 10)

        confidence = (volume_score + momentum_score) / 2
        return max(0.1, min(0.9, confidence))


class MomentumStrategy:
    """动量策略"""

    def __init__(self,
                 momentum_period: int = 14,
                 rsi_period: int = 14,
                 rsi_oversold: float = 30,
                 rsi_overbought: float = 70):
        """
        初始化动量策略

        Args:
            momentum_period: 动量计算周期
            rsi_period: RSI计算周期
            rsi_oversold: RSI超卖阈值
            rsi_overbought: RSI超买阈值
        """
        self.momentum_period = momentum_period
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.name = "Momentum"

    def generate_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """生成动量信号"""
        signals = []

        if len(data) < max(self.momentum_period, self.rsi_period):
            return signals

        # 计算动量指标
        data['momentum'] = data['close'].pct_change(self.momentum_period)
        data['rsi'] = self._calculate_rsi(data['close'], self.rsi_period)

        # 计算移动平均
        data['ma_momentum'] = data['momentum'].rolling(window=5).mean()

        for i in range(max(self.momentum_period, self.rsi_period), len(data)):
            current = data.iloc[i]
            prev = data.iloc[i-1]

            # 买入信号：动量转正且RSI从超卖区域回升
            if (current['momentum'] > 0 and prev['momentum'] <= 0 and
                    current['rsi'] > self.rsi_oversold and prev['rsi'] <= self.rsi_oversold):

                confidence = self._calculate_momentum_confidence(data.iloc[i-10:i+1])

                signals.append(TradingSignal(
                    timestamp=data.index[i],
                    signal_type=SignalType.BUY,
                    price=current['close'],
                    confidence=confidence,
                    strategy_name=self.name,
                    reason=f"动量转正({current['momentum']:.3f})，RSI脱离超卖区({current['rsi']:.1f})",
                    stop_loss=current['close'] * 0.95,
                    take_profit=current['close'] * 1.12
                ))

            # 卖出信号：动量转负且RSI从超买区域回落
            elif (current['momentum'] < 0 and prev['momentum'] >= 0 and
                  current['rsi'] < self.rsi_overbought and prev['rsi'] >= self.rsi_overbought):

                confidence = self._calculate_momentum_confidence(data.iloc[i-10:i+1])

                signals.append(TradingSignal(
                    timestamp=data.index[i],
                    signal_type=SignalType.SELL,
                    price=current['close'],
                    confidence=confidence,
                    strategy_name=self.name,
                    reason=f"动量转负({current['momentum']:.3f})，RSI脱离超买区({current['rsi']:.1f})",
                    stop_loss=current['close'] * 1.05,
                    take_profit=current['close'] * 0.88
                ))

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_momentum_confidence(self, recent_data: pd.DataFrame) -> float:
        """计算动量信号置信度"""
        if len(recent_data) < 5:
            return 0.5

        # RSI趋势一致性
        rsi_trend = recent_data['rsi'].diff().mean()
        rsi_score = min(1.0, abs(rsi_trend) / 5.0)

        # 动量强度
        momentum_strength = abs(recent_data['momentum'].iloc[-1])
        momentum_score = min(1.0, momentum_strength * 20)

        confidence = (rsi_score + momentum_score) / 2
        return max(0.1, min(0.9, confidence))


class AdaptiveTrendStrategy:
    """自适应趋势策略"""

    def __init__(self,
                 volatility_period: int = 20,
                 trend_strength_period: int = 14):
        """
        初始化自适应趋势策略

        Args:
            volatility_period: 波动率计算周期
            trend_strength_period: 趋势强度计算周期
        """
        self.volatility_period = volatility_period
        self.trend_strength_period = trend_strength_period
        self.name = "AdaptiveTrend"

    def generate_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """生成自适应趋势信号"""
        signals = []

        if len(data) < max(self.volatility_period, self.trend_strength_period):
            return signals

        # 计算自适应指标
        data['volatility'] = data['close'].rolling(window=self.volatility_period).std()
        data['trend_strength'] = self._calculate_trend_strength(data)
        data['adaptive_ma'] = self._calculate_adaptive_ma(data)

        # 计算信号
        for i in range(max(self.volatility_period, self.trend_strength_period), len(data)):
            current = data.iloc[i]
            prev = data.iloc[i-1]

            # 趋势确认
            trend_direction = self._identify_trend(data.iloc[i-10:i+1])

            if trend_direction == TrendDirection.UP and current['close'] > current['adaptive_ma']:
                confidence = self._calculate_adaptive_confidence(data.iloc[i-5:i+1], trend_direction)

                signals.append(TradingSignal(
                    timestamp=data.index[i],
                    signal_type=SignalType.BUY,
                    price=current['close'],
                    confidence=confidence,
                    strategy_name=self.name,
                    reason=f"上升趋势确认，价格突破自适应均线({current['adaptive_ma']:.3f})",
                    stop_loss=current['adaptive_ma'] * 0.98,
                    take_profit=current['close'] * 1.1
                ))

            elif trend_direction == TrendDirection.DOWN and current['close'] < current['adaptive_ma']:
                confidence = self._calculate_adaptive_confidence(data.iloc[i-5:i+1], trend_direction)

                signals.append(TradingSignal(
                    timestamp=data.index[i],
                    signal_type=SignalType.SELL,
                    price=current['close'],
                    confidence=confidence,
                    strategy_name=self.name,
                    reason=f"下降趋势确认，价格跌破自适应均线({current['adaptive_ma']:.3f})",
                    stop_loss=current['adaptive_ma'] * 1.02,
                    take_profit=current['close'] * 0.9
                ))

        return signals

    def _calculate_trend_strength(self, data: pd.DataFrame) -> pd.Series:
        """计算趋势强度"""
        price_change = data['close'].pct_change(self.trend_strength_period)
        volatility = data['close'].rolling(window=self.trend_strength_period).std()
        trend_strength = abs(price_change) / (volatility / data['close'] + 0.001)
        return trend_strength

    def _calculate_adaptive_ma(self, data: pd.DataFrame) -> pd.Series:
        """计算自适应移动平均"""
        # 基于波动率调整移动平均周期
        base_period = 20
        volatility_ratio = data['volatility'] / data['volatility'].rolling(window=50).mean()
        adaptive_period = base_period * (1 + volatility_ratio.fillna(1))
        adaptive_period = adaptive_period.clip(10, 50).round().astype(int)

        # 计算自适应移动平均
        adaptive_ma = pd.Series(index=data.index, dtype=float)
        for i in range(len(data)):
            period = adaptive_period.iloc[i] if not pd.isna(adaptive_period.iloc[i]) else base_period
            start_idx = max(0, i - period + 1)
            adaptive_ma.iloc[i] = data['close'].iloc[start_idx:i+1].mean()

        return adaptive_ma

    def _identify_trend(self, recent_data: pd.DataFrame) -> TrendDirection:
        """识别趋势方向"""
        if len(recent_data) < 5:
            return TrendDirection.SIDEWAYS

        # 线性回归斜率
        x = np.arange(len(recent_data))
        y = recent_data['close'].values
        slope = np.polyfit(x, y, 1)[0]

        # 趋势强度
        price_range = recent_data['close'].max() - recent_data['close'].min()
        avg_price = recent_data['close'].mean()
        trend_strength = price_range / avg_price

        if slope > 0 and trend_strength > 0.02:
            return TrendDirection.UP
        elif slope < 0 and trend_strength > 0.02:
            return TrendDirection.DOWN
        else:
            return TrendDirection.SIDEWAYS

    def _calculate_adaptive_confidence(self, recent_data: pd.DataFrame, trend_direction: TrendDirection) -> float:
        """计算自适应信号置信度"""
        if len(recent_data) < 3:
            return 0.5

        # 趋势一致性
        trend_consistency = self._calculate_trend_consistency(recent_data)

        # 波动率稳定性
        volatility_stability = 1 / (1 + recent_data['volatility'].std())

        # 趋势强度
        trend_strength = recent_data['trend_strength'].iloc[-1] if 'trend_strength' in recent_data.columns else 0.5

        confidence = (trend_consistency + volatility_stability + min(1.0, trend_strength)) / 3
        return max(0.1, min(0.9, confidence))

    def _calculate_trend_consistency(self, data: pd.DataFrame) -> float:
        """计算趋势一致性"""
        if len(data) < 3:
            return 0.5

        price_changes = data['close'].diff().dropna()
        if len(price_changes) == 0:
            return 0.5

        # 计算同向变化的比例
        positive_changes = (price_changes > 0).sum()
        negative_changes = (price_changes < 0).sum()
        total_changes = len(price_changes)

        consistency = max(positive_changes, negative_changes) / total_changes
        return consistency


class TrendFollowingManager:
    """趋势跟踪策略管理器"""

    def __init__(self):
        """初始化策略管理器"""
        self.strategies = {
            'ma_trend': MovingAverageTrendStrategy(),
            'breakout': BreakoutStrategy(),
            'momentum': MomentumStrategy(),
            'adaptive': AdaptiveTrendStrategy()
        }

    def generate_all_signals(self, data: pd.DataFrame) -> Dict[str, List[TradingSignal]]:
        """生成所有策略的信号"""
        all_signals = {}

        for name, strategy in self.strategies.items():
            try:
                signals = strategy.generate_signals(data.copy())
                all_signals[name] = signals
            except Exception as e:
                print(f"策略 {name} 生成信号失败: {e}")
                all_signals[name] = []

        return all_signals

    def get_consensus_signals(self, data: pd.DataFrame, min_agreement: int = 2) -> List[TradingSignal]:
        """获取一致性信号"""
        all_signals = self.generate_all_signals(data)
        consensus_signals = []

        # 按时间戳分组信号
        timestamp_signals = {}
        for strategy_name, signals in all_signals.items():
            for signal in signals:
                timestamp = signal.timestamp
                if timestamp not in timestamp_signals:
                    timestamp_signals[timestamp] = []
                timestamp_signals[timestamp].append(signal)

        # 寻找一致性信号
        for timestamp, signals in timestamp_signals.items():
            if len(signals) >= min_agreement:
                # 检查信号类型一致性
                signal_types = [s.signal_type for s in signals]
                if len(set(signal_types)) == 1:  # 所有信号类型相同
                    # 创建一致性信号
                    avg_confidence = np.mean([s.confidence for s in signals])
                    avg_price = np.mean([s.price for s in signals])

                    consensus_signal = TradingSignal(
                        timestamp=timestamp,
                        signal_type=signals[0].signal_type,
                        price=avg_price,
                        confidence=min(0.9, avg_confidence * 1.2),  # 一致性加成
                        strategy_name="Consensus",
                        reason=f"多策略一致性信号({len(signals)}个策略同意)",
                        stop_loss=np.mean([s.stop_loss for s in signals if s.stop_loss]),
                        take_profit=np.mean([s.take_profit for s in signals if s.take_profit])
                    )

                    consensus_signals.append(consensus_signal)

        return consensus_signals


def create_trend_following_manager() -> TrendFollowingManager:
    """
    创建趋势跟踪策略管理器

    Returns:
        策略管理器实例
    """
    return TrendFollowingManager()


if __name__ == "__main__":
    # 测试代码
    import matplotlib.pyplot as plt

    # 生成模拟数据
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    np.random.seed(42)

    # 模拟价格数据（带趋势）
    trend = np.linspace(100, 120, 200)
    noise = np.random.normal(0, 2, 200)
    prices = trend + noise + np.sin(np.arange(200) * 0.1) * 3

    data = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.lognormal(10, 0.5, 200)
    }, index=dates)

    # 创建策略管理器
    manager = create_trend_following_manager()

    # 生成信号
    all_signals = manager.generate_all_signals(data)
    consensus_signals = manager.get_consensus_signals(data)

    print("趋势跟踪策略测试结果:")
    print("=" * 50)

    for strategy_name, signals in all_signals.items():
        print(f"{strategy_name}: {len(signals)} 个信号")
        if signals:
            avg_confidence = np.mean([s.confidence for s in signals])
            print(f"  平均置信度: {avg_confidence:.3f}")

    print(f"\n一致性信号: {len(consensus_signals)} 个")
    if consensus_signals:
        avg_confidence = np.mean([s.confidence for s in consensus_signals])
        print(f"平均置信度: {avg_confidence:.3f}")

        print("\n一致性信号详情:")
        for signal in consensus_signals[:5]:  # 显示前5个信号
            print(f"  {signal.timestamp.date()}: {signal.signal_type.value} @ {signal.price:.3f} (置信度: {signal.confidence:.3f})")
