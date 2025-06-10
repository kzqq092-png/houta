"""
Pattern Recognition Module for Trading System
Provides various chart pattern recognition tools
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pandas as pd
from hikyuu import Datetime, Query, KData, MA
from core.data_manager import data_manager


class PatternRecognizer:
    """Pattern recognition tools for trading system, now supports extensive candlestick and multi-bar patterns with parameter customization."""

    DEFAULT_PARAMS = {
        # 单根K线
        'hammer_shadow_ratio': 2.0,
        'shooting_star_shadow_ratio': 2.0,
        'doji_body_ratio': 0.1,
        'marubozu_body_ratio': 0.9,
        'long_line_body_ratio': 0.7,
        'spinning_top_body_ratio': 0.3,
        # 双根
        'engulfing_min_body_ratio': 0.7,
        'piercing_darkcloud_ratio': 0.5,
        # 三根
        'star_gap_ratio': 0.2,
        # 通用
        'min_pattern_size': 5,
        'max_pattern_size': 60,
        'threshold': 0.02,
    }

    def __init__(self, params: Optional[dict] = None):
        self.cache = {}
        self.params = self.DEFAULT_PARAMS.copy()
        if params:
            self.params.update(params)

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
                if 'code' not in kdata.columns:
                    raise Exception(
                        "find_head_shoulders: DataFrame 缺少 code 字段，请补全后再调用！建议补全 code 字段，或通过 main.py/core/trading_system.py/analysis_widget.py 自动补全。")
                kdata = data_manager.df_to_kdata(kdata)
            if not kdata or len(kdata) < 20:
                print("[PatternRecognizer] find_head_shoulders: kdata为空或不足20条，跳过识别")
                return []

            closes = np.array([float(k.close) for k in kdata])
            patterns = []
            min_pattern_size = 20
            max_pattern_size = 60

            for i in range(min_pattern_size, len(closes)-min_pattern_size):
                left_shoulder = np.max(closes[i-min_pattern_size:i])
                left_shoulder_idx = i - min_pattern_size + np.argmax(closes[i-min_pattern_size:i])
                head = np.max(closes[i:i+min_pattern_size])
                head_idx = i + np.argmax(closes[i:i+min_pattern_size])
                right_shoulder = np.max(closes[head_idx:head_idx+min_pattern_size])
                right_shoulder_idx = head_idx + np.argmax(closes[head_idx:head_idx+min_pattern_size])
                if (head > left_shoulder and head > right_shoulder and abs(left_shoulder - right_shoulder) < threshold * head):
                    neckline = min(closes[left_shoulder_idx:right_shoulder_idx+1])
                    diffs = np.array([left_shoulder, head, right_shoulder])
                    mean_abs_diffs = np.mean(np.abs(diffs))
                    symmetry = 0.0 if mean_abs_diffs == 0 or np.isnan(mean_abs_diffs) else 1 - np.std(diffs) / mean_abs_diffs
                    # 统一字段
                    patterns.append(self._make_pattern_dict(
                        pat_type='head_shoulders_top',
                        signal='sell',
                        confidence=self._calculate_pattern_confidence([left_shoulder, head, right_shoulder], neckline),
                        index=head_idx,
                        datetime_val=str(kdata[head_idx].datetime) if hasattr(kdata[head_idx], 'datetime') else None,
                        price=head,
                        extra={
                            'left_shoulder': (left_shoulder_idx, left_shoulder),
                            'head': (head_idx, head),
                            'right_shoulder': (right_shoulder_idx, right_shoulder),
                            'neckline': neckline,
                            'symmetry': symmetry
                        }
                    ))
                left_shoulder = np.min(closes[i-min_pattern_size:i])
                left_shoulder_idx = i - min_pattern_size + np.argmin(closes[i-min_pattern_size:i])
                head = np.min(closes[i:i+min_pattern_size])
                head_idx = i + np.argmin(closes[i:i+min_pattern_size])
                right_shoulder = np.min(closes[head_idx:head_idx+min_pattern_size])
                right_shoulder_idx = head_idx + np.argmin(closes[head_idx:head_idx+min_pattern_size])
                if (head < left_shoulder and head < right_shoulder and abs(left_shoulder - right_shoulder) < threshold * abs(head)):
                    neckline = max(closes[left_shoulder_idx:right_shoulder_idx+1])
                    diffs = np.array([left_shoulder, head, right_shoulder])
                    mean_abs_diffs = np.mean(np.abs(diffs))
                    symmetry = 0.0 if mean_abs_diffs == 0 or np.isnan(mean_abs_diffs) else 1 - np.std(diffs) / mean_abs_diffs
                    patterns.append(self._make_pattern_dict(
                        pat_type='head_shoulders_bottom',
                        signal='buy',
                        confidence=self._calculate_pattern_confidence([left_shoulder, head, right_shoulder], neckline),
                        index=head_idx,
                        datetime_val=str(kdata[head_idx].datetime) if hasattr(kdata[head_idx], 'datetime') else None,
                        price=head,
                        extra={
                            'left_shoulder': (left_shoulder_idx, left_shoulder),
                            'head': (head_idx, head),
                            'right_shoulder': (right_shoulder_idx, right_shoulder),
                            'neckline': neckline,
                            'symmetry': symmetry
                        }
                    ))
            if not patterns:
                print(f"[PatternRecognizer] find_head_shoulders: 未识别到任何形态，建议调整参数或更换股票。")
            return patterns
        except Exception as e:
            raise Exception(f"Head and shoulders pattern recognition failed: {str(e)}")

    def find_double_tops_bottoms(self, kdata, threshold: float = 0.02) -> List[Dict]:
        """Find double top and bottom patterns
        Args:
            kdata: KData对象或DataFrame
            threshold: Price difference threshold
        Returns:
            List of identified patterns
        """
        try:
            # 类型安全转换：DataFrame转list
            if isinstance(kdata, pd.DataFrame):
                if 'code' not in kdata.columns:
                    raise Exception(
                        "find_double_tops_bottoms: DataFrame 缺少 code 字段，请补全后再调用！建议补全 code 字段，或通过 main.py/core/trading_system.py/analysis_widget.py 自动补全。")
                # 转为list对象，兼容后续索引
                kdata = list(kdata.itertuples(index=False))
            if not kdata or len(kdata) < 10:
                print(
                    "[PatternRecognizer] find_double_tops_bottoms: kdata为空或不足10条，跳过识别")
                return []

            closes = np.array([float(getattr(k, 'close', k.close) if hasattr(k, 'close') else k[4]) for k in kdata])
            patterns = []
            min_pattern_size = 10
            max_pattern_size = 40

            for i in range(min_pattern_size, len(closes)-min_pattern_size):
                peak1 = np.max(closes[i-min_pattern_size:i])
                peak1_idx = i - min_pattern_size + np.argmax(closes[i-min_pattern_size:i])
                peak2 = np.max(closes[i:i+min_pattern_size])
                peak2_idx = i + np.argmax(closes[i:i+min_pattern_size])
                if abs(peak1 - peak2) < threshold * peak1:
                    neckline = min(closes[peak1_idx:peak2_idx+1])
                    patterns.append(self._make_pattern_dict(
                        pat_type='double_top',
                        signal='sell',
                        confidence=self._calculate_pattern_confidence([peak1, peak2], neckline),
                        index=int(peak2_idx),
                        datetime_val=str(getattr(kdata[peak2_idx], 'datetime', None)),
                        price=peak2,
                        extra={
                            'peak1': (int(peak1_idx), peak1),
                            'peak2': (int(peak2_idx), peak2),
                            'neckline': neckline
                        }
                    ))
                trough1 = np.min(closes[i-min_pattern_size:i])
                trough1_idx = i - min_pattern_size + np.argmin(closes[i-min_pattern_size:i])
                trough2 = np.min(closes[i:i+min_pattern_size])
                trough2_idx = i + np.argmin(closes[i:i+min_pattern_size])
                if abs(trough1 - trough2) < threshold * trough1:
                    neckline = max(closes[trough1_idx:trough2_idx+1])
                    patterns.append(self._make_pattern_dict(
                        pat_type='double_bottom',
                        signal='buy',
                        confidence=self._calculate_pattern_confidence([trough1, trough2], neckline),
                        index=int(trough2_idx),
                        datetime_val=str(getattr(kdata[trough2_idx], 'datetime', None)),
                        price=trough2,
                        extra={
                            'trough1': (int(trough1_idx), trough1),
                            'trough2': (int(trough2_idx), trough2),
                            'neckline': neckline
                        }
                    ))
            return patterns
        except Exception as e:
            raise Exception(f"Double tops/bottoms pattern recognition failed: {str(e)}")

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
                if 'code' not in kdata.columns:
                    raise Exception(
                        "find_triangles: DataFrame 缺少 code 字段，请补全后再调用！建议补全 code 字段，或通过 main.py/core/trading_system.py/analysis_widget.py 自动补全。")
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

            if not patterns:
                print(f"[PatternRecognizer] find_triangles: 未识别到任何形态，建议调整参数或更换股票。")
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
            mean_points = np.mean(points)
            if mean_points == 0 or np.isnan(mean_points):
                volatility = 0
            else:
                volatility = np.std(points) / mean_points

            # Calculate price deviation from reference
            if reference == 0 or np.isnan(reference):
                deviation = 0
            else:
                deviation = np.mean(
                    [abs(p - reference) / reference for p in points])

            # Calculate pattern symmetry
            diffs = np.diff(points)
            mean_abs_diffs = np.mean(np.abs(diffs))
            if mean_abs_diffs == 0 or np.isnan(mean_abs_diffs):
                symmetry = 0
            else:
                symmetry = 1 - np.std(diffs) / mean_abs_diffs

            # Combine factors
            confidence = (0.4 * (1 - volatility) +
                          0.4 * (1 - deviation) +
                          0.2 * symmetry)

            return max(0, min(1, confidence))

        except Exception as e:
            raise Exception(f"Pattern confidence calculation failed: {str(e)}")

    def get_pattern_signals(self, kdata, pattern_types: Optional[list] = None, params: Optional[dict] = None) -> List[Dict]:
        """Get trading signals based on selected pattern types and parameters.
        Args:
            kdata: KData or DataFrame
            pattern_types: List of pattern type names (e.g. ['hammer', 'engulfing'])
            params: Optional parameter overrides
        Returns:
            List of pattern signal dicts
        """
        import pandas as pd
        from datetime import datetime
        # --- 新增：datetime字段健壮性检查 ---
        if isinstance(kdata, pd.DataFrame):
            if 'datetime' not in kdata.columns:
                print("[PatternRecognizer] K线数据缺少datetime字段，自动补全为当前时间")
                kdata['datetime'] = pd.to_datetime(datetime.now()).strftime('%Y-%m-%d')
            # 检查并修正datetime字段

            def fix_datetime(val, prev):
                try:
                    if pd.isna(val) or val is None:
                        return prev if prev else datetime.now().strftime('%Y-%m-%d')
                    # 尝试标准化格式
                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                except Exception as e:
                    print(f"[PatternRecognizer] 修正datetime异常: {val}, 错误: {str(e)}")
                    return prev if prev else datetime.now().strftime('%Y-%m-%d')
            prev_dt = None
            dt_list = []
            for v in kdata['datetime']:
                fixed = fix_datetime(v, prev_dt)
                dt_list.append(fixed)
                prev_dt = fixed
            kdata['datetime'] = dt_list
            # 过滤掉仍为None或空字符串的行
            before = len(kdata)
            kdata = kdata[kdata['datetime'].notna() & (kdata['datetime'] != '')]
            after = len(kdata)
            if after < before:
                print(f"[PatternRecognizer] 已过滤{before-after}行无效datetime数据")
        if params:
            self.params.update(params)
        all_patterns = {
            # 单根
            'hammer': self.find_hammer,
            'shooting_star': self.find_shooting_star,
            'doji': self.find_doji,
            'marubozu': self.find_marubozu,
            'spinning_top': self.find_spinning_top,
            # 双根
            'engulfing': self.find_engulfing,
            'piercing': self.find_piercing,
            'dark_cloud_cover': self.find_dark_cloud_cover,
            # 三根
            'morning_star': self.find_morning_star,
            'evening_star': self.find_evening_star,
            'three_white_soldiers': self.find_three_white_soldiers,
            'three_black_crows': self.find_three_black_crows,
            # 组合
            'head_shoulders': self.find_head_shoulders,
            'double_tops_bottoms': self.find_double_tops_bottoms,
            'triangles': self.find_triangles,
        }
        if pattern_types is None:
            pattern_types = list(all_patterns.keys())
        signals = []
        for pt in pattern_types:
            if pt in all_patterns:
                try:
                    signals.extend(all_patterns[pt](kdata))
                except Exception as e:
                    print(f"[PatternRecognizer] {pt} 识别异常: {e}")
        return signals

    # --- 单根K线形态 ---
    def find_hammer(self, kdata) -> List[Dict]:
        """识别锤头线（Hammer）"""
        # ...实现...
        return []

    def find_shooting_star(self, kdata) -> List[Dict]:
        """识别射击之星（Shooting Star）"""
        # ...实现...
        return []

    def find_doji(self, kdata) -> List[Dict]:
        """识别十字星（Doji）"""
        # ...实现...
        return []

    def find_marubozu(self, kdata) -> List[Dict]:
        """识别光头光脚线（Marubozu）"""
        # ...实现...
        return []

    def find_spinning_top(self, kdata) -> List[Dict]:
        """识别纺锤线（Spinning Top）"""
        # ...实现...
        return []
    # --- 双根形态 ---

    def find_engulfing(self, kdata) -> List[Dict]:
        """识别吞没形态（Engulfing）"""
        # ...实现...
        return []

    def find_piercing(self, kdata) -> List[Dict]:
        """识别刺透形态（Piercing Pattern）"""
        # ...实现...
        return []

    def find_dark_cloud_cover(self, kdata) -> List[Dict]:
        """识别乌云盖顶（Dark Cloud Cover）"""
        # ...实现...
        return []
    # --- 三根形态 ---

    def find_morning_star(self, kdata) -> List[Dict]:
        """识别早晨之星（Morning Star）"""
        # ...实现...
        return []

    def find_evening_star(self, kdata) -> List[Dict]:
        """识别黄昏之星（Evening Star）"""
        # ...实现...
        return []

    def find_three_white_soldiers(self, kdata) -> List[Dict]:
        """识别三白兵（Three White Soldiers）"""
        # ...实现...
        return []

    def find_three_black_crows(self, kdata) -> List[Dict]:
        """识别三只乌鸦（Three Black Crows）"""
        # ...实现...
        return []

    def find_inverted_hammer(self, kdata) -> List[Dict]:
        """识别倒锤头形态"""
        # TODO: 实现倒锤头识别逻辑
        return []

    def find_shooting_star(self, kdata) -> List[Dict]:
        """识别流星线形态"""
        # TODO: 实现流星线识别逻辑
        return []

    def find_tower_top(self, kdata) -> List[Dict]:
        """识别塔形顶形态"""
        # TODO: 实现塔形顶识别逻辑
        return []

    def find_tower_bottom(self, kdata) -> List[Dict]:
        """识别塔形底形态"""
        # TODO: 实现塔形底识别逻辑
        return []

    def find_flag(self, kdata) -> List[Dict]:
        """识别旗形形态"""
        # TODO: 实现旗形识别逻辑
        return []

    def find_wedge(self, kdata) -> List[Dict]:
        """识别楔形形态"""
        # TODO: 实现楔形识别逻辑
        return []

    def find_rectangle(self, kdata) -> List[Dict]:
        """识别矩形整理形态"""
        # TODO: 实现矩形整理识别逻辑
        return []

    def find_channel(self, kdata) -> List[Dict]:
        """识别上升/下降通道形态"""
        # TODO: 实现通道识别逻辑
        return []

    def get_pattern_statistics(self, kdata, pattern_types: Optional[list] = None, params: Optional[dict] = None) -> Dict:
        """
        统计分析：返回各形态出现次数、胜率、平均涨跌幅等统计信息
        Args:
            kdata: K线数据
            pattern_types: 形态类型列表
            params: 参数
        Returns:
            dict: {pattern: {count, win_rate, avg_return, ...}}
        """
        # TODO: 实现统计分析逻辑
        return {}

    def _make_pattern_dict(self, pat_type, signal, confidence, index, datetime_val, price, extra=None):
        """统一生成形态信号字典，增加详细字段和置信度分级"""
        if confidence >= 0.8:
            confidence_level = '高'
        elif confidence >= 0.5:
            confidence_level = '中'
        else:
            confidence_level = '低'
        d = {
            'type': pat_type,
            'signal': signal,
            'confidence': confidence,
            'confidence_level': confidence_level,
            'index': index,
            'datetime': datetime_val,
            'price': price
        }
        if extra:
            d.update(extra)
        return d
