from loguru import logger
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号检测器基础框架
支持扩展的多数据源信号检测
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime

from ..signal_aggregator import TradingSignal, SignalType, SignalStrength

class ISignalDetector(ABC):
    """信号检测器接口"""

    @abstractmethod
    def detect_signals(self, data: Dict[str, Any]) -> List[TradingSignal]:
        """检测交易信号"""
        pass

    @abstractmethod
    def get_detector_info(self) -> Dict[str, Any]:
        """获取检测器信息"""
        pass

    @property
    @abstractmethod
    def signal_type(self) -> SignalType:
        """信号类型"""
        pass

class BaseSignalDetector(ISignalDetector):
    """信号检测器基类"""

    def __init__(self, name: str, signal_type: SignalType, weight: float = 1.0):
        self.name = name
        self._signal_type = signal_type
        self.weight = weight
        self.enabled = True
        self.last_detection_time = None

        # 检测参数
        self.detection_params = {}

        # 信号历史
        self.signal_history: List[TradingSignal] = []

    @property
    def signal_type(self) -> SignalType:
        return self._signal_type

    def get_detector_info(self) -> Dict[str, Any]:
        """获取检测器信息"""
        return {
            "name": self.name,
            "type": self.signal_type.value,
            "weight": self.weight,
            "enabled": self.enabled,
            "last_detection": self.last_detection_time.isoformat() if self.last_detection_time else None,
            "signal_count": len(self.signal_history),
            "parameters": self.detection_params
        }

    def update_parameters(self, params: Dict[str, Any]):
        """更新检测参数"""
        self.detection_params.update(params)

    def enable(self):
        """启用检测器"""
        self.enabled = True

    def disable(self):
        """禁用检测器"""
        self.enabled = False

    def detect_signals(self, data: Dict[str, Any]) -> List[TradingSignal]:
        """检测交易信号"""
        if not self.enabled:
            return []

        try:
            signals = self._internal_detect(data)
            self.last_detection_time = datetime.now()
            self.signal_history.extend(signals)

            # 限制历史记录数量
            if len(self.signal_history) > 100:
                self.signal_history = self.signal_history[-100:]

            return signals

        except Exception as e:
            logger.info(f"信号检测器 {self.name} 错误: {e}")
            return []

    @abstractmethod
    def _internal_detect(self, data: Dict[str, Any]) -> List[TradingSignal]:
        """内部检测实现"""
        pass

class FundamentalSignalDetector(BaseSignalDetector):
    """基本面信号检测器"""

    def __init__(self):
        super().__init__("基本面分析", SignalType.FUNDAMENTAL, weight=0.6)

        # 基本面检测参数
        self.detection_params = {
            "pe_threshold_high": 30,    # PE高估阈值
            "pe_threshold_low": 15,     # PE低估阈值
            "pb_threshold_high": 3,     # PB高估阈值
            "pb_threshold_low": 1,      # PB低估阈值
            "roe_threshold": 15,        # ROE阈值
            "debt_ratio_threshold": 60  # 负债率阈值
        }

    def _internal_detect(self, data: Dict[str, Any]) -> List[TradingSignal]:
        """检测基本面信号"""
        signals = []
        current_time = datetime.now()

        try:
            fundamental_data = data.get('fundamental', {})

            # PE比率信号
            if 'pe_ratio' in fundamental_data:
                pe_signal = self._detect_pe_signal(fundamental_data['pe_ratio'], current_time)
                if pe_signal:
                    signals.append(pe_signal)

            # PB比率信号
            if 'pb_ratio' in fundamental_data:
                pb_signal = self._detect_pb_signal(fundamental_data['pb_ratio'], current_time)
                if pb_signal:
                    signals.append(pb_signal)

            # ROE信号
            if 'roe' in fundamental_data:
                roe_signal = self._detect_roe_signal(fundamental_data['roe'], current_time)
                if roe_signal:
                    signals.append(roe_signal)

            # 盈利增长信号
            if 'earnings_growth' in fundamental_data:
                growth_signal = self._detect_earnings_growth_signal(
                    fundamental_data['earnings_growth'], current_time
                )
                if growth_signal:
                    signals.append(growth_signal)

        except Exception as e:
            logger.info(f"基本面信号检测错误: {e}")

        return signals

    def _detect_pe_signal(self, pe_ratio: float, timestamp: datetime) -> Optional[TradingSignal]:
        """检测PE比率信号"""
        pe_high = self.detection_params['pe_threshold_high']
        pe_low = self.detection_params['pe_threshold_low']

        if pe_ratio > pe_high:
            return TradingSignal(
                signal_id=f"pe_overvalued_{timestamp.timestamp()}",
                signal_type=self.signal_type,
                direction="sell",
                strength=SignalStrength.MODERATE,
                confidence=min(0.8, (pe_ratio - pe_high) / pe_high),
                message=f"PE比率过高 ({pe_ratio:.1f})",
                details={"pe_ratio": pe_ratio, "threshold": pe_high},
                timestamp=timestamp,
                source_data={"indicator": "pe_ratio", "value": pe_ratio}
            )
        elif pe_ratio < pe_low:
            return TradingSignal(
                signal_id=f"pe_undervalued_{timestamp.timestamp()}",
                signal_type=self.signal_type,
                direction="buy",
                strength=SignalStrength.MODERATE,
                confidence=min(0.8, (pe_low - pe_ratio) / pe_low),
                message=f"PE比率偏低 ({pe_ratio:.1f})",
                details={"pe_ratio": pe_ratio, "threshold": pe_low},
                timestamp=timestamp,
                source_data={"indicator": "pe_ratio", "value": pe_ratio}
            )
        return None

    def _detect_pb_signal(self, pb_ratio: float, timestamp: datetime) -> Optional[TradingSignal]:
        """检测PB比率信号"""
        pb_high = self.detection_params['pb_threshold_high']
        pb_low = self.detection_params['pb_threshold_low']

        if pb_ratio > pb_high:
            return TradingSignal(
                signal_id=f"pb_overvalued_{timestamp.timestamp()}",
                signal_type=self.signal_type,
                direction="sell",
                strength=SignalStrength.WEAK,
                confidence=0.6,
                message=f"PB比率过高 ({pb_ratio:.2f})",
                details={"pb_ratio": pb_ratio, "threshold": pb_high},
                timestamp=timestamp,
                source_data={"indicator": "pb_ratio", "value": pb_ratio}
            )
        elif pb_ratio < pb_low:
            return TradingSignal(
                signal_id=f"pb_undervalued_{timestamp.timestamp()}",
                signal_type=self.signal_type,
                direction="buy",
                strength=SignalStrength.MODERATE,
                confidence=0.7,
                message=f"PB比率偏低 ({pb_ratio:.2f})",
                details={"pb_ratio": pb_ratio, "threshold": pb_low},
                timestamp=timestamp,
                source_data={"indicator": "pb_ratio", "value": pb_ratio}
            )
        return None

    def _detect_roe_signal(self, roe: float, timestamp: datetime) -> Optional[TradingSignal]:
        """检测ROE信号"""
        roe_threshold = self.detection_params['roe_threshold']

        if roe > roe_threshold:
            return TradingSignal(
                signal_id=f"roe_strong_{timestamp.timestamp()}",
                signal_type=self.signal_type,
                direction="buy",
                strength=SignalStrength.MODERATE,
                confidence=min(0.8, roe / 30),  # 30%ROE为满分
                message=f"ROE表现强劲 ({roe:.1f}%)",
                details={"roe": roe, "threshold": roe_threshold},
                timestamp=timestamp,
                source_data={"indicator": "roe", "value": roe}
            )
        return None

    def _detect_earnings_growth_signal(self, growth_rate: float, timestamp: datetime) -> Optional[TradingSignal]:
        """检测盈利增长信号"""
        if growth_rate > 20:  # 增长超过20%
            return TradingSignal(
                signal_id=f"earnings_growth_strong_{timestamp.timestamp()}",
                signal_type=self.signal_type,
                direction="buy",
                strength=SignalStrength.STRONG,
                confidence=min(0.9, growth_rate / 50),
                message=f"盈利增长强劲 ({growth_rate:.1f}%)",
                details={"growth_rate": growth_rate},
                timestamp=timestamp,
                source_data={"indicator": "earnings_growth", "value": growth_rate}
            )
        elif growth_rate < -10:  # 盈利下降超过10%
            return TradingSignal(
                signal_id=f"earnings_decline_{timestamp.timestamp()}",
                signal_type=self.signal_type,
                direction="sell",
                strength=SignalStrength.MODERATE,
                confidence=min(0.8, abs(growth_rate) / 30),
                message=f"盈利大幅下降 ({growth_rate:.1f}%)",
                details={"growth_rate": growth_rate},
                timestamp=timestamp,
                source_data={"indicator": "earnings_growth", "value": growth_rate}
            )
        return None

class VolumeSignalDetector(BaseSignalDetector):
    """成交量信号检测器"""

    def __init__(self):
        super().__init__("成交量分析", SignalType.VOLUME, weight=0.3)

        self.detection_params = {
            "volume_surge_ratio": 2.0,    # 成交量激增比例
            "price_volume_divergence": 0.1,  # 价量背离阈值
            "avg_volume_days": 20          # 平均成交量计算天数
        }

    def _internal_detect(self, data: Dict[str, Any]) -> List[TradingSignal]:
        """检测成交量信号"""
        signals = []
        current_time = datetime.now()

        try:
            kdata = data.get('kdata')
            if kdata is None or len(kdata) < 20:
                return signals

            # 成交量异常信号
            volume_signal = self._detect_volume_anomaly(kdata, current_time)
            if volume_signal:
                signals.append(volume_signal)

            # 价量背离信号
            divergence_signal = self._detect_price_volume_divergence(kdata, current_time)
            if divergence_signal:
                signals.append(divergence_signal)

        except Exception as e:
            logger.info(f"成交量信号检测错误: {e}")

        return signals

    def _detect_volume_anomaly(self, kdata: pd.DataFrame, timestamp: datetime) -> Optional[TradingSignal]:
        """检测成交量异常"""
        avg_days = self.detection_params['avg_volume_days']
        surge_ratio = self.detection_params['volume_surge_ratio']

        if len(kdata) < avg_days + 1:
            return None

        recent_volume = float(kdata.iloc[-1]['volume'])
        avg_volume = float(kdata.iloc[-avg_days:-1]['volume'].mean())

        if recent_volume > avg_volume * surge_ratio:
            # 判断是否伴随价格上涨
            price_change = (float(kdata.iloc[-1]['close']) - float(kdata.iloc[-2]['close'])) / float(kdata.iloc[-2]['close'])

            direction = "buy" if price_change > 0 else "sell"
            strength = SignalStrength.STRONG if recent_volume > avg_volume * 3 else SignalStrength.MODERATE

            return TradingSignal(
                signal_id=f"volume_surge_{timestamp.timestamp()}",
                signal_type=self.signal_type,
                direction=direction,
                strength=strength,
                confidence=min(0.9, recent_volume / (avg_volume * 2)),
                message=f"成交量异常放大 ({recent_volume/avg_volume:.1f}倍)",
                details={
                    "current_volume": recent_volume,
                    "avg_volume": avg_volume,
                    "ratio": recent_volume/avg_volume,
                    "price_change": price_change
                },
                timestamp=timestamp,
                source_data={"indicator": "volume_surge", "ratio": recent_volume/avg_volume}
            )

        return None

    def _detect_price_volume_divergence(self, kdata: pd.DataFrame, timestamp: datetime) -> Optional[TradingSignal]:
        """检测价量背离"""
        if len(kdata) < 10:
            return None

        try:
            # 计算最近10天的价格和成交量趋势
            recent_data = kdata.tail(10)

            # 价格趋势（简单线性回归斜率）
            prices = recent_data['close'].values
            price_trend = (prices[-1] - prices[0]) / len(prices)

            # 成交量趋势
            volumes = recent_data['volume'].values
            volume_trend = (volumes[-1] - volumes[0]) / len(volumes)

            # 检测背离：价格上涨但成交量下降，或价格下跌但成交量上升
            divergence_threshold = self.detection_params['price_volume_divergence']

            if price_trend > divergence_threshold and volume_trend < -divergence_threshold:
                return TradingSignal(
                    signal_id=f"price_volume_divergence_bearish_{timestamp.timestamp()}",
                    signal_type=self.signal_type,
                    direction="sell",
                    strength=SignalStrength.MODERATE,
                    confidence=0.7,
                    message="价涨量缩，趋势可能反转",
                    details={
                        "price_trend": price_trend,
                        "volume_trend": volume_trend
                    },
                    timestamp=timestamp,
                    source_data={"indicator": "price_volume_divergence", "type": "bearish"}
                )
            elif price_trend < -divergence_threshold and volume_trend > divergence_threshold:
                return TradingSignal(
                    signal_id=f"price_volume_divergence_bullish_{timestamp.timestamp()}",
                    signal_type=self.signal_type,
                    direction="buy",
                    strength=SignalStrength.MODERATE,
                    confidence=0.7,
                    message="价跌量增，可能见底反弹",
                    details={
                        "price_trend": price_trend,
                        "volume_trend": volume_trend
                    },
                    timestamp=timestamp,
                    source_data={"indicator": "price_volume_divergence", "type": "bullish"}
                )

        except Exception as e:
            logger.info(f"价量背离检测错误: {e}")

        return None

class SignalDetectorRegistry:
    """信号检测器注册中心"""

    def __init__(self):
        self.detectors: Dict[str, ISignalDetector] = {}
        self.register_default_detectors()

    def register_default_detectors(self):
        """注册默认检测器"""
        # 注册基本面检测器
        self.register_detector("fundamental", FundamentalSignalDetector())

        # 注册成交量检测器
        self.register_detector("volume", VolumeSignalDetector())

    def register_detector(self, name: str, detector: ISignalDetector):
        """注册检测器"""
        self.detectors[name] = detector
        logger.info(f"已注册信号检测器: {name}")

    def unregister_detector(self, name: str):
        """注销检测器"""
        if name in self.detectors:
            del self.detectors[name]
            logger.info(f"已注销信号检测器: {name}")

    def get_detector(self, name: str) -> Optional[ISignalDetector]:
        """获取检测器"""
        return self.detectors.get(name)

    def get_all_detectors(self) -> Dict[str, ISignalDetector]:
        """获取所有检测器"""
        return self.detectors.copy()

    def detect_all_signals(self, data: Dict[str, Any]) -> Dict[str, List[TradingSignal]]:
        """使用所有检测器检测信号"""
        all_signals = {}

        for name, detector in self.detectors.items():
            try:
                signals = detector.detect_signals(data)
                all_signals[name] = signals
            except Exception as e:
                logger.info(f"检测器 {name} 执行失败: {e}")
                all_signals[name] = []

        return all_signals

    def get_registry_info(self) -> Dict[str, Any]:
        """获取注册中心信息"""
        return {
            "total_detectors": len(self.detectors),
            "detectors": {
                name: detector.get_detector_info()
                for name, detector in self.detectors.items()
            }
        }
