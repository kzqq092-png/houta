"""
Technical Analysis Module for Trading System
Provides various technical analysis tools and indicators
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pandas as pd
from hikyuu import Datetime, Query, KData, MA, MACD, RSI, BOLL

class TechnicalAnalyzer:
    """Technical analysis tools for trading system"""
    
    def __init__(self):
        self.cache = {}
        
    def analyze_support_resistance(self, kdata: KData, period: int = 20, 
                                 sensitivity: float = 0.01) -> Dict:
        """Analyze support and resistance levels
        
        Args:
            kdata: KData object containing price data
            period: Period for analysis
            sensitivity: Sensitivity threshold
            
        Returns:
            Dict containing support and resistance levels
        """
        try:
            closes = np.array([float(k.close) for k in kdata])
            highs = np.array([float(k.high) for k in kdata])
            lows = np.array([float(k.low) for k in kdata])
            
            # Find local peaks and troughs
            peaks = []
            troughs = []
            
            for i in range(period, len(closes)-period):
                # Find peaks
                if all(highs[i] >= highs[i-j] for j in range(1, period+1)) and \
                   all(highs[i] >= highs[i+j] for j in range(1, period+1)):
                    peaks.append((i, highs[i]))
                
                # Find troughs
                if all(lows[i] <= lows[i-j] for j in range(1, period+1)) and \
                   all(lows[i] <= lows[i+j] for j in range(1, period+1)):
                    troughs.append((i, lows[i]))
            
            # Cluster nearby levels
            def cluster_levels(levels: List[Tuple], sensitivity: float) -> List[List[Tuple]]:
                if not levels:
                    return []
                    
                clusters = []
                current_cluster = [levels[0]]
                
                for level in levels[1:]:
                    if abs(level[1] - current_cluster[0][1]) < sensitivity:
                        current_cluster.append(level)
                    else:
                        clusters.append(current_cluster)
                        current_cluster = [level]
                
                clusters.append(current_cluster)
                return clusters
            
            # Get resistance and support clusters
            resistance_clusters = cluster_levels(peaks, sensitivity)
            support_clusters = cluster_levels(troughs, sensitivity)
            
            # Calculate level strengths
            resistance_levels = []
            for cluster in resistance_clusters:
                price = np.mean([p[1] for p in cluster])
                strength = len(cluster)
                resistance_levels.append({
                    'price': price,
                    'strength': strength,
                    'touches': cluster
                })
            
            support_levels = []
            for cluster in support_clusters:
                price = np.mean([p[1] for p in cluster])
                strength = len(cluster)
                support_levels.append({
                    'price': price,
                    'strength': strength,
                    'touches': cluster
                })
            
            # Calculate trend lines
            def calculate_trend_lines(points: List[Tuple], is_resistance: bool = True) -> List[Dict]:
                trend_lines = []
                
                for i in range(len(points)-1):
                    for j in range(i+1, len(points)):
                        p1 = points[i]
                        p2 = points[j]
                        
                        slope = (p2[1] - p1[1]) / (p2[0] - p1[0])
                        intercept = p1[1] - slope * p1[0]
                        
                        points_above = sum(1 for k in range(len(closes)) 
                                         if closes[k] > slope * k + intercept)
                        points_below = len(closes) - points_above
                        
                        if (is_resistance and points_below > points_above * 3) or \
                           (not is_resistance and points_above > points_below * 3):
                            trend_lines.append({
                                'slope': slope,
                                'intercept': intercept,
                                'start': p1,
                                'end': p2,
                                'strength': min(points_above, points_below) / max(points_above, points_below)
                            })
                
                return trend_lines
            
            resistance_trends = calculate_trend_lines(peaks, True)
            support_trends = calculate_trend_lines(troughs, False)
            
            return {
                'resistance_levels': resistance_levels,
                'support_levels': support_levels,
                'resistance_trends': resistance_trends,
                'support_trends': support_trends
            }
            
        except Exception as e:
            raise Exception(f"Support/Resistance analysis failed: {str(e)}")
            
    def analyze_momentum(self, kdata: KData) -> Dict:
        """Analyze price momentum using various indicators
        
        Args:
            kdata: KData object containing price data
            
        Returns:
            Dict containing momentum analysis results
        """
        try:
            closes = np.array([float(k.close) for k in kdata])
            
            # Calculate RSI
            rsi = RSI(kdata.close, 14)
            
            # Calculate MACD
            macd = MACD(kdata.close)
            
            # Calculate rate of change
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