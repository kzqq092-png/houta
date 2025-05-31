"""
Wave Analysis Module for Trading System
Provides Elliott Wave and Gann analysis tools
"""

import importlib
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pandas as pd
from core.data_manager import DataManager as data_manager
from hikyuu import Datetime, Query, KData
from talib import HT_TRENDLINE, MA
try:
    talib = importlib.import_module('talib')
except ImportError:
    talib = None


class WaveAnalyzer:
    """Wave analysis tools for trading system"""

    def __init__(self):
        self.cache = {}

    def analyze_elliott_waves(self, kdata, period: int = 20,
                              sensitivity: float = 0.01) -> Dict:
        """Analyze Elliott Wave patterns

        Args:
            kdata: KData对象或DataFrame
            period: Period for analysis
            sensitivity: Sensitivity threshold

        Returns:
            Dict containing Elliott Wave analysis results
        """
        try:
            if isinstance(kdata, pd.DataFrame):
                kdata = data_manager.df_to_kdata(kdata)
            closes = np.array([float(k.close) for k in kdata])
            highs = np.array([float(k.high) for k in kdata])
            lows = np.array([float(k.low) for k in kdata])

            # Get trend using HT_TRENDLINE
            trend = talib.HT_TRENDLINE(closes)

            # Find wave turning points
            peaks = []
            troughs = []

            for i in range(period, len(closes)-period):
                # Find peaks
                if all(closes[i] > closes[i-j] for j in range(1, period+1)) and \
                   all(closes[i] > closes[i+j] for j in range(1, period+1)):
                    peaks.append((i, closes[i]))

                # Find troughs
                if all(closes[i] < closes[i-j] for j in range(1, period+1)) and \
                   all(closes[i] < closes[i+j] for j in range(1, period+1)):
                    troughs.append((i, closes[i]))

            # Identify five-wave structures
            waves = []
            if len(peaks) >= 3 and len(troughs) >= 2:
                for i in range(len(peaks)-2):
                    # Check Elliott Wave rules
                    wave1 = peaks[i][1] - troughs[i][1]
                    wave2 = troughs[i+1][1] - peaks[i][1]
                    wave3 = peaks[i+1][1] - troughs[i+1][1]
                    wave4 = troughs[i+2][1] - peaks[i+1][1]
                    wave5 = peaks[i+2][1] - troughs[i+2][1]

                    # Validate wave rules
                    if (wave3 > wave1 and  # Wave 3 is longest
                        wave2 < wave1 and  # Wave 2 retracement
                        wave4 < wave3 and  # Wave 4 smaller than 3
                            wave5 < wave3):    # Wave 5 smaller than 3

                        waves.append({
                            'start_idx': peaks[i][0],
                            'end_idx': peaks[i+2][0],
                            'waves': [wave1, wave2, wave3, wave4, wave5],
                            'points': [peaks[i], troughs[i], peaks[i+1],
                                     troughs[i+1], peaks[i+2]]
                        })

            return {
                'trend': trend,
                'peaks': peaks,
                'troughs': troughs,
                'waves': waves
            }

        except Exception as e:
            raise Exception(f"Elliott Wave analysis failed: {str(e)}")

    def analyze_gann(self, kdata, period: int = 20,
                     sensitivity: float = 0.01) -> Dict:
        """Analyze using Gann methods

        Args:
            kdata: KData对象或DataFrame
            period: Period for analysis
            sensitivity: Sensitivity threshold

        Returns:
            Dict containing Gann analysis results
        """
        try:
            if isinstance(kdata, pd.DataFrame):
                kdata = data_manager.df_to_kdata(kdata)
            closes = np.array([float(k.close) for k in kdata])
            highs = np.array([float(k.high) for k in kdata])
            lows = np.array([float(k.low) for k in kdata])

            # Calculate Gann angles
            angles = [15, 30, 45, 60, 75]  # Main Gann angles
            gann_lines = {}

            # Get starting point
            start_price = closes[0]
            end_price = closes[-1]
            price_range = end_price - start_price

            for angle in angles:
                # Calculate angle lines
                rad = np.radians(angle)
                x = np.arange(len(closes))
                y = start_price + x * np.tan(rad) * sensitivity
                gann_lines[angle] = y

            # Calculate Gann square of nine
            price_levels = []
            time_levels = []

            # Price divisions
            price_min = np.min(lows)
            price_max = np.max(highs)
            price_range = price_max - price_min

            for i in range(9):
                level = price_min + (price_range / 8) * i
                price_levels.append(level)

            # Time divisions
            for i in range(9):
                level = int(len(closes) / 8 * i)
                time_levels.append(level)

            # Find support/resistance levels
            support_resistance = []
            for price in price_levels:
                # Count price touches
                touches = np.sum(np.abs(closes - price) < price_range * 0.01)
                if touches >= 3:  # Minimum 3 touches for valid level
                    support_resistance.append({
                        'price': price,
                        'touches': touches
                    })

            return {
                'gann_lines': gann_lines,
                'price_levels': price_levels,
                'time_levels': time_levels,
                'support_resistance': support_resistance
            }

        except Exception as e:
            raise Exception(f"Gann analysis failed: {str(e)}")

    def get_wave_signals(self, kdata) -> List[Dict]:
        """Get trading signals based on wave analysis

        Args:
            kdata: KData对象或DataFrame

        Returns:
            List of trading signals
        """
        try:
            if isinstance(kdata, pd.DataFrame):
                kdata = data_manager.df_to_kdata(kdata)
            # Get Elliott Wave analysis
            elliott = self.analyze_elliott_waves(kdata)

            # Get Gann analysis
            gann = self.analyze_gann(kdata)

            signals = []

            # Generate Elliott Wave signals
            for wave in elliott['waves']:
                # Buy signal at start of wave 1
                signals.append({
                    'type': 'elliott',
                    'signal': 'buy',
                    'price': wave['points'][0][1],
                    'index': wave['points'][0][0],
                    'strength': 0.8
                })

                # Sell signal at end of wave 5
                signals.append({
                    'type': 'elliott',
                    'signal': 'sell',
                    'price': wave['points'][-1][1],
                    'index': wave['points'][-1][0],
                    'strength': 0.8
                })

            # Generate Gann signals
            for level in gann['support_resistance']:
                if level['touches'] >= 5:  # Strong level
                    signals.append({
                        'type': 'gann',
                        'signal': 'support' if level['price'] < kdata[-1].close else 'resistance',
                        'price': level['price'],
                        'touches': level['touches'],
                        'strength': level['touches'] / 10
                    })

            return signals

        except Exception as e:
            raise Exception(f"Wave signal generation failed: {str(e)}")
