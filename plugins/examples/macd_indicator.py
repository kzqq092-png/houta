"""
MACD指标插件示例（V2 接口）

与系统的新插件框架对齐：
- 不再使用旧装饰器/旧接口
- 使用 V2 接口：core.indicator_strategy_extensions.IIndicatorPluginV2
- 配置以 JSON 统一管理
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import QWidget, QFormLayout, QSpinBox

from core.indicator_strategy_extensions import IIndicatorPluginV2
from core.data_source_extensions import PluginInfo
from core.plugin_types import PluginType


class MACDIndicatorPlugin(IIndicatorPluginV2):
    """MACD 指标插件（V2）"""

    def __init__(self):
        self._config: Dict[str, Any] = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9
        }
        self._initialized: bool = False
        self.plugin_type = PluginType.INDICATOR

    def get_plugin_info(self) -> PluginInfo:
        return PluginInfo(
            id="indicator.macd",
            name="MACD指标",
            version="2.0.0",
            description="移动平均收敛发散指标(MACD)，用于分析趋势与信号",
            author="FactorWeave 团队",
            supported_asset_types=[],
            supported_data_types=[]
        )

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'fast_period': {
                    'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 12, 'title': '快速EMA周期'
                },
                'slow_period': {
                    'type': 'integer', 'minimum': 1, 'maximum': 200, 'default': 26, 'title': '慢速EMA周期'
                },
                'signal_period': {
                    'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 9, 'title': '信号线EMA周期'
                }
            },
            'required': ['fast_period', 'slow_period', 'signal_period'],
            'additionalProperties': False
        }

    def validate_config(self, config: Dict[str, Any]) -> bool:
        try:
            fast_period = int(config.get('fast_period', 12))
            slow_period = int(config.get('slow_period', 26))
            signal_period = int(config.get('signal_period', 9))
            if not (1 <= fast_period <= 100):
                return False
            if not (1 <= slow_period <= 200):
                return False
            if not (1 <= signal_period <= 50):
                return False
            if fast_period >= slow_period:
                return False
            return True
        except Exception:
            return False

    def initialize(self, config: Dict[str, Any]) -> bool:
        try:
            merged = {**self._config, **(config or {})}
            if not self.validate_config(merged):
                return False
            self._config = merged
            self._initialized = True
            return True
        except Exception:
            return False

    def shutdown(self) -> None:
        self._initialized = False

    def calculate(self, data: pd.DataFrame, **params) -> Dict[str, pd.Series]:
        if not self._initialized:
            raise RuntimeError("MACD 指标未初始化")
        fast_period = int(params.get('fast_period', self._config['fast_period']))
        slow_period = int(params.get('slow_period', self._config['slow_period']))
        signal_period = int(params.get('signal_period', self._config['signal_period']))
        if fast_period >= slow_period:
            raise ValueError("快速周期必须小于慢速周期")
        if len(data) < slow_period:
            raise ValueError(f"数据长度不足，需要至少{slow_period}个数据点")

        close_prices = data['close']
        ema_fast = self._calculate_ema(close_prices, fast_period)
        ema_slow = self._calculate_ema(close_prices, slow_period)
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal_period)
        histogram = macd_line - signal_line
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def _calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        alpha = 2.0 / (period + 1)
        ema = pd.Series(index=prices.index, dtype=float)
        ema.iloc[period-1] = prices.iloc[:period].mean()
        for i in range(period, len(prices)):
            ema.iloc[i] = alpha * prices.iloc[i] + (1 - alpha) * ema.iloc[i-1]
        return ema

    # 可选：保留示例中的简易配置小部件（不影响新接口）
    def create_config_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        widget = QWidget(parent)
        layout = QFormLayout(widget)
        fast_spin = QSpinBox()
        fast_spin.setRange(1, 100)
        fast_spin.setValue(self._config['fast_period'])
        slow_spin = QSpinBox()
        slow_spin.setRange(1, 200)
        slow_spin.setValue(self._config['slow_period'])
        signal_spin = QSpinBox()
        signal_spin.setRange(1, 50)
        signal_spin.setValue(self._config['signal_period'])
        layout.addRow("快速EMA周期:", fast_spin)
        layout.addRow("慢速EMA周期:", slow_spin)
        layout.addRow("信号线EMA周期:", signal_spin)

        def on_change():
            new_cfg = {
                'fast_period': fast_spin.value(),
                'slow_period': slow_spin.value(),
                'signal_period': signal_spin.value()
            }
            if self.validate_config(new_cfg):
                self._config.update(new_cfg)
        fast_spin.valueChanged.connect(on_change)
        slow_spin.valueChanged.connect(on_change)
        signal_spin.valueChanged.connect(on_change)
        return widget
