"""
Technical Analysis Module for Trading System
Provides various technical analysis tools and indicators
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import pandas as pd
from hikyuu import *
from core.data_manager import data_manager


class TechnicalAnalyzer:
    """Technical analysis tools for trading system"""

    def __init__(self):
        self.cache = {}

    def analyze(self, kdata) -> Dict[str, Any]:
        """
        执行全面的技术分析

        Args:
            kdata: KData对象或DataFrame

        Returns:
            包含所有技术分析结果的字典
        """
        if isinstance(kdata, pd.DataFrame):
            df = kdata
        else:
            df = data_manager.kdata_to_df(kdata)

        trend_analysis = self.analyze_trend(df)
        momentum_analysis = self.analyze_momentum(df)
        support_resistance_analysis = self.analyze_support_resistance(df)

        return {
            **trend_analysis,
            **momentum_analysis,
            **support_resistance_analysis
        }

    def analyze_trend(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析趋势"""
        try:
            # 使用多个移动平均线判断趋势
            ma_short = data['close'].rolling(20).mean()
            ma_medium = data['close'].rolling(50).mean()
            ma_long = data['close'].rolling(200).mean()

            current_price = data['close'].iloc[-1]

            # 趋势方向判断
            if current_price > ma_short.iloc[-1] > ma_medium.iloc[-1] > ma_long.iloc[-1]:
                trend_direction = 'STRONG_UPTREND'
                trend_strength = 0.8
            elif current_price > ma_short.iloc[-1] > ma_medium.iloc[-1]:
                trend_direction = 'UPTREND'
                trend_strength = 0.6
            elif current_price < ma_short.iloc[-1] < ma_medium.iloc[-1] < ma_long.iloc[-1]:
                trend_direction = 'STRONG_DOWNTREND'
                trend_strength = -0.8
            elif current_price < ma_short.iloc[-1] < ma_medium.iloc[-1]:
                trend_direction = 'DOWNTREND'
                trend_strength = -0.6
            else:
                trend_direction = 'SIDEWAYS'
                trend_strength = 0.0

            # ADX趋势强度
            if 'adx' in data.columns:
                adx_value = data['adx'].iloc[-1]
                if adx_value > 25:
                    trend_strength *= (adx_value / 50)

            return {
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'ma_alignment': {
                    'ma20': ma_short.iloc[-1],
                    'ma50': ma_medium.iloc[-1],
                    'ma200': ma_long.iloc[-1]
                }
            }

        except Exception as e:
            # logging.error(f"趋势分析失败: {e}") # 假设没有logger
            return {'trend_direction': 'NEUTRAL', 'trend_strength': 0.0}

    def analyze_support_resistance(self, data: pd.DataFrame, window: int = 20) -> Dict[str, List[float]]:
        """寻找支撑阻力位"""
        try:
            support_levels = []
            resistance_levels = []

            highs = data['high'].rolling(window, center=True).max()
            lows = data['low'].rolling(window, center=True).min()

            for i in range(window, len(data) - window):
                if data['high'].iloc[i] == highs.iloc[i]:
                    resistance_levels.append(data['high'].iloc[i])

            for i in range(window, len(data) - window):
                if data['low'].iloc[i] == lows.iloc[i]:
                    support_levels.append(data['low'].iloc[i])

            support_levels = sorted(list(set(support_levels)))[-5:]
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)[:5]

            return {
                'support_levels': support_levels,
                'resistance_levels': resistance_levels
            }

        except Exception as e:
            # logging.error(f"支撑阻力分析失败: {e}")
            return {'support_levels': [], 'resistance_levels': []}

    def analyze_momentum(self, kdata) -> Dict:
        """Analyze price momentum using various indicators
        Args:
            kdata: KData对象或DataFrame
        Returns:
            Dict containing momentum analysis results
        """
        try:
            if isinstance(kdata, pd.DataFrame):
                closes = kdata['close'].values
                # 已替换为新的导入
                rsi = calc_rsi(kdata['close'], n=14)
                macd, _, _ = calc_macd(kdata['close'], fast=12, slow=26, signal=9)
            else:
                closes = np.array([float(k.close) for k in kdata])
                from hikyuu.indicator import RSI, MACD
                close_ind = CLOSE(kdata)
                rsi = RSI(close_ind, n=14)
                macd = MACD(close_ind)
            roc = np.diff(closes) / closes[:-1] * 100
            return {
                'rsi': rsi,
                'macd': macd,
                'roc': roc,
                'momentum_score': self._calculate_momentum_score(rsi, macd, roc)
            }
        except Exception as e:
            raise Exception(f"Momentum analysis failed: {str(e)}")

    def _calculate_momentum_score(self, rsi, macd, roc) -> float:
        """Calculate overall momentum score

        Args:
            rsi: RSI indicator values
            macd: MACD indicator values
            roc: Rate of change values

        Returns:
            Float value representing momentum score
        """
        try:
            # Normalize indicators
            rsi_norm = (rsi - 50) / 50  # Center around 0
            macd_norm = (macd.macd - np.mean(macd.macd)) / np.std(macd.macd)
            roc_norm = (roc - np.mean(roc)) / np.std(roc)

            # Calculate weighted score
            score = (0.4 * rsi_norm[-1] +
                     0.4 * macd_norm[-1] +
                     0.2 * roc_norm[-1])

            return score

        except Exception as e:
            raise Exception(f"Momentum score calculation failed: {str(e)}")
