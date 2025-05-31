"""
Pattern Recognition Module for Trading System
Provides various chart pattern recognition tools
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pandas as pd
from hikyuu import Datetime, Query, KData, MA
from core.data_manager import DataManager as data_manager


class PatternRecognizer:
    """Pattern recognition tools for trading system"""

    def __init__(self):
        self.cache = {}

    def find_head_shoulders(self, kdata, threshold: float = 0.02) -> List[Dict]:
        """Find head and shoulders patterns
        Args:
            kdata: KData对象或DataFrame
            threshold: Price difference threshold
        Returns:
            List of identified patterns
        """
        try:
            if isinstance(kdata, pd.DataFrame):
                kdata = data_manager.df_to_kdata(kdata)
            if not kdata or len(kdata) < 20:
                print("[PatternRecognizer] find_head_shoulders: kdata为空或不足20条，跳过识别")
                return []

            closes = np.array([float(k.close) for k in kdata])
            patterns = []
            min_pattern_size = 20
            max_pattern_size = 60

            for i in range(min_pattern_size, len(closes)-min_pattern_size):
                # Find left shoulder
                left_shoulder = np.max(closes[i-min_pattern_size:i])
                left_shoulder_idx = i - min_pattern_size + \
                    np.argmax(closes[i-min_pattern_size:i])

                # Find head
                head = np.max(closes[i:i+min_pattern_size])
                head_idx = i + np.argmax(closes[i:i+min_pattern_size])

                # Find right shoulder
                right_shoulder = np.max(
                    closes[head_idx:head_idx+min_pattern_size])
                right_shoulder_idx = head_idx + \
                    np.argmax(closes[head_idx:head_idx+min_pattern_size])

                # Validate pattern
                if (head > left_shoulder and head > right_shoulder and
                        abs(left_shoulder - right_shoulder) < threshold * head):

                    # Find neckline
                    neckline = min(
                        closes[left_shoulder_idx:right_shoulder_idx+1]
                    )

                    patterns.append({
                        'type': 'head_shoulders_top',
                        'left_shoulder': (left_shoulder_idx, left_shoulder),
                        'head': (head_idx, head),
                        'right_shoulder': (right_shoulder_idx, right_shoulder),
                        'neckline': neckline,
                        'confidence': self._calculate_pattern_confidence(
                            [left_shoulder, head, right_shoulder],
                            neckline
                        )
                    })

                # Check inverse head and shoulders
                left_shoulder = np.min(closes[i-min_pattern_size:i])
                left_shoulder_idx = i - min_pattern_size + \
                    np.argmin(closes[i-min_pattern_size:i])

                head = np.min(closes[i:i+min_pattern_size])
                head_idx = i + np.argmin(closes[i:i+min_pattern_size])

                right_shoulder = np.min(
                    closes[head_idx:head_idx+min_pattern_size])
                right_shoulder_idx = head_idx + \
                    np.argmin(closes[head_idx:head_idx+min_pattern_size])

                if (head < left_shoulder and head < right_shoulder and
                        abs(left_shoulder - right_shoulder) < threshold * head):

                    neckline = max(
                        closes[left_shoulder_idx:right_shoulder_idx+1]
                    )

                    patterns.append({
                        'type': 'head_shoulders_bottom',
                        'left_shoulder': (left_shoulder_idx, left_shoulder),
                        'head': (head_idx, head),
                        'right_shoulder': (right_shoulder_idx, right_shoulder),
                        'neckline': neckline,
                        'confidence': self._calculate_pattern_confidence(
                            [left_shoulder, head, right_shoulder],
                            neckline
                        )
                    })

            return patterns

        except Exception as e:
            raise Exception(
                f"Head and shoulders pattern recognition failed: {str(e)}")

    def find_double_tops_bottoms(self, kdata, threshold: float = 0.02) -> List[Dict]:
        """Find double top and bottom patterns
        Args:
            kdata: KData对象或DataFrame
            threshold: Price difference threshold
        Returns:
            List of identified patterns
        """
        try:
            if isinstance(kdata, pd.DataFrame):
                kdata = data_manager.df_to_kdata(kdata)
            if not kdata or len(kdata) < 10:
                print(
                    "[PatternRecognizer] find_double_tops_bottoms: kdata为空或不足10条，跳过识别")
                return []

            closes = np.array([float(k.close) for k in kdata])
            patterns = []
            min_pattern_size = 10
            max_pattern_size = 40

            for i in range(min_pattern_size, len(closes)-min_pattern_size):
                # Find first peak
                peak1 = np.max(closes[i-min_pattern_size:i])
                peak1_idx = i - min_pattern_size + \
                    np.argmax(closes[i-min_pattern_size:i])

                # Find second peak
                peak2 = np.max(closes[i:i+min_pattern_size])
                peak2_idx = i + np.argmax(closes[i:i+min_pattern_size])

                # Validate double top
                if abs(peak1 - peak2) < threshold * peak1:
                    # Find neckline
                    neckline = min(closes[peak1_idx:peak2_idx+1])

                    patterns.append({
                        'type': 'double_top',
                        'peak1': (peak1_idx, peak1),
                        'peak2': (peak2_idx, peak2),
                        'neckline': neckline,
                        'confidence': self._calculate_pattern_confidence(
                            [peak1, peak2],
                            neckline
                        )
                    })

                # Find double bottom
                trough1 = np.min(closes[i-min_pattern_size:i])
                trough1_idx = i - min_pattern_size + \
                    np.argmin(closes[i-min_pattern_size:i])

                trough2 = np.min(closes[i:i+min_pattern_size])
                trough2_idx = i + np.argmin(closes[i:i+min_pattern_size])

                if abs(trough1 - trough2) < threshold * trough1:
                    neckline = max(closes[trough1_idx:trough2_idx+1])

                    patterns.append({
                        'type': 'double_bottom',
                        'trough1': (trough1_idx, trough1),
                        'trough2': (trough2_idx, trough2),
                        'neckline': neckline,
                        'confidence': self._calculate_pattern_confidence(
                            [trough1, trough2],
                            neckline
                        )
                    })

            return patterns

        except Exception as e:
            raise Exception(
                f"Double top/bottom pattern recognition failed: {str(e)}")

    def find_triangles(self, kdata, threshold: float = 0.02) -> List[Dict]:
        """Find triangle patterns
        Args:
            kdata: KData对象或DataFrame
            threshold: Price difference threshold
        Returns:
            List of identified patterns
        """
        try:
            if isinstance(kdata, pd.DataFrame):
                kdata = data_manager.df_to_kdata(kdata)
            if not kdata or len(kdata) < 10:
                print("[PatternRecognizer] find_triangles: kdata为空或不足10条，跳过识别")
                return []

            closes = np.array([float(k.close) for k in kdata])
            highs = np.array([float(k.high) for k in kdata])
            lows = np.array([float(k.low) for k in kdata])
            patterns = []
            min_pattern_size = 20

            for i in range(min_pattern_size, len(closes)-min_pattern_size):
                # Get local highs and lows
                local_highs = []
                local_lows = []

                for j in range(i-min_pattern_size, i+min_pattern_size):
                    if j > 0 and j < len(closes)-1:
                        if highs[j] > highs[j-1] and highs[j] > highs[j+1]:
                            local_highs.append((j, highs[j]))
                        if lows[j] < lows[j-1] and lows[j] < lows[j+1]:
                            local_lows.append((j, lows[j]))

                if len(local_highs) >= 2 and len(local_lows) >= 2:
                    # Fit lines to highs and lows
                    high_slope = np.polyfit([x[0] for x in local_highs],
                                            [x[1] for x in local_highs], 1)[0]
                    low_slope = np.polyfit([x[0] for x in local_lows],
                                           [x[1] for x in local_lows], 1)[0]

                    # Identify triangle patterns
                    if abs(high_slope) < 0.1 and abs(low_slope) < 0.1:
                        # Symmetrical triangle
                        if high_slope < 0 and low_slope > 0:
                            patterns.append({
                                'type': 'symmetrical_triangle',
                                'start_idx': i-min_pattern_size,
                                'end_idx': i+min_pattern_size,
                                'highs': local_highs,
                                'lows': local_lows,
                                'confidence': self._calculate_pattern_confidence(
                                    [x[1] for x in local_highs + local_lows],
                                    np.mean([x[1]
                                            for x in local_highs + local_lows])
                                )
                            })
                        # Ascending triangle
                        elif abs(high_slope) < 0.05 and low_slope > 0:
                            patterns.append({
                                'type': 'ascending_triangle',
                                'start_idx': i-min_pattern_size,
                                'end_idx': i+min_pattern_size,
                                'highs': local_highs,
                                'lows': local_lows,
                                'confidence': self._calculate_pattern_confidence(
                                    [x[1] for x in local_highs + local_lows],
                                    np.mean([x[1] for x in local_highs])
                                )
                            })
                        # Descending triangle
                        elif high_slope < 0 and abs(low_slope) < 0.05:
                            patterns.append({
                                'type': 'descending_triangle',
                                'start_idx': i-min_pattern_size,
                                'end_idx': i+min_pattern_size,
                                'highs': local_highs,
                                'lows': local_lows,
                                'confidence': self._calculate_pattern_confidence(
                                    [x[1] for x in local_highs + local_lows],
                                    np.mean([x[1] for x in local_lows])
                                )
                            })

            return patterns

        except Exception as e:
            raise Exception(f"Triangle pattern recognition failed: {str(e)}")

    def _calculate_pattern_confidence(self, points: List[float],
                                      reference: float) -> float:
        """Calculate pattern confidence score

        Args:
            points: List of pattern points
            reference: Reference price level

        Returns:
            Confidence score between 0 and 1
        """
        try:
            # Calculate price volatility
            volatility = np.std(points) / np.mean(points)

            # Calculate price deviation from reference
            deviation = np.mean(
                [abs(p - reference) / reference for p in points])

            # Calculate pattern symmetry
            diffs = np.diff(points)
            symmetry = 1 - np.std(diffs) / np.mean(np.abs(diffs))

            # Combine factors
            confidence = (0.4 * (1 - volatility) +
                          0.4 * (1 - deviation) +
                          0.2 * symmetry)

            return max(0, min(1, confidence))

        except Exception as e:
            raise Exception(f"Pattern confidence calculation failed: {str(e)}")

    def get_pattern_signals(self, kdata: KData) -> List[Dict]:
        """Get trading signals based on pattern recognition

        Args:
            kdata: KData object containing price data

        Returns:
            List of trading signals
        """
        try:
            signals = []

            # Get patterns
            head_shoulders = self.find_head_shoulders(kdata)
            double_patterns = self.find_double_tops_bottoms(kdata)
            triangles = self.find_triangles(kdata)

            # Generate head and shoulders signals
            for pattern in head_shoulders:
                if pattern['type'] == 'head_shoulders_top':
                    signals.append({
                        'type': 'pattern',
                        'pattern': 'head_shoulders_top',
                        'signal': 'sell',
                        'price': pattern['neckline'],
                        'confidence': pattern['confidence'],
                        'index': pattern['right_shoulder'][0]
                    })
                else:  # head_shoulders_bottom
                    signals.append({
                        'type': 'pattern',
                        'pattern': 'head_shoulders_bottom',
                        'signal': 'buy',
                        'price': pattern['neckline'],
                        'confidence': pattern['confidence'],
                        'index': pattern['right_shoulder'][0]
                    })

            # Generate double top/bottom signals
            for pattern in double_patterns:
                if pattern['type'] == 'double_top':
                    signals.append({
                        'type': 'pattern',
                        'pattern': 'double_top',
                        'signal': 'sell',
                        'price': pattern['neckline'],
                        'confidence': pattern['confidence'],
                        'index': pattern['peak2'][0]
                    })
                else:  # double_bottom
                    signals.append({
                        'type': 'pattern',
                        'pattern': 'double_bottom',
                        'signal': 'buy',
                        'price': pattern['neckline'],
                        'confidence': pattern['confidence'],
                        'index': pattern['trough2'][0]
                    })

            # Generate triangle signals
            for pattern in triangles:
                if pattern['type'] == 'ascending_triangle':
                    signals.append({
                        'type': 'pattern',
                        'pattern': 'ascending_triangle',
                        'signal': 'buy',
                        'price': max([h[1] for h in pattern['highs']]),
                        'confidence': pattern['confidence'],
                        'index': pattern['end_idx']
                    })
                elif pattern['type'] == 'descending_triangle':
                    signals.append({
                        'type': 'pattern',
                        'pattern': 'descending_triangle',
                        'signal': 'sell',
                        'price': min([l[1] for l in pattern['lows']]),
                        'confidence': pattern['confidence'],
                        'index': pattern['end_idx']
                    })

            return signals

        except Exception as e:
            raise Exception(f"Pattern signal generation failed: {str(e)}")
