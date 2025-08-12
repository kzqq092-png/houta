"""
双均线策略插件示例（V2 接口）

与系统的新插件框架对齐：
- 不再使用旧装饰器/旧接口
- 使用 V2 接口：core.indicator_strategy_extensions.IStrategyPluginV2
- 配置以 JSON 统一管理
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import QWidget, QFormLayout, QSpinBox, QComboBox

from core.indicator_strategy_extensions import IStrategyPluginV2
from core.data_source_extensions import PluginInfo
from core.plugin_types import PluginType


class MovingAverageStrategyPlugin(IStrategyPluginV2):
    """双均线策略插件（V2）"""

    def __init__(self):
        self._config: Dict[str, Any] = {
            'fast_period': 5,
            'slow_period': 20,
            'ma_type': 'SMA',  # SMA, EMA
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.10
        }
        self._initialized: bool = False
        self.plugin_type = PluginType.STRATEGY

    def get_plugin_info(self) -> PluginInfo:
        return PluginInfo(
            id="strategy.moving_average",
            name="双均线策略",
            version="2.0.0",
            description="经典双均线交叉策略，基于快慢均线生成交易信号",
            author="FactorWeave 团队",
            supported_asset_types=[],
            supported_data_types=[]
        )

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'fast_period': {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 5, 'title': '快速均线周期'},
                'slow_period': {'type': 'integer', 'minimum': 2, 'maximum': 200, 'default': 20, 'title': '慢速均线周期'},
                'ma_type': {'type': 'string', 'enum': ['SMA', 'EMA'], 'default': 'SMA', 'title': '均线类型'},
                'stop_loss_pct': {'type': 'number', 'minimum': 0.0, 'maximum': 0.5, 'default': 0.05, 'title': '止损百分比'},
                'take_profit_pct': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0, 'default': 0.10, 'title': '止盈百分比'}
            },
            'required': ['fast_period', 'slow_period', 'ma_type'],
            'additionalProperties': False
        }

    def validate_config(self, config: Dict[str, Any]) -> bool:
        try:
            fast_period = int(config.get('fast_period', 5))
            slow_period = int(config.get('slow_period', 20))
            ma_type = str(config.get('ma_type', 'SMA'))
            if not (1 <= fast_period <= 50):
                return False
            if not (2 <= slow_period <= 200):
                return False
            if fast_period >= slow_period:
                return False
            if ma_type not in ['SMA', 'EMA']:
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

    def generate_signals(self, data: pd.DataFrame, **params) -> Dict[str, pd.Series]:
        if not self._initialized:
            raise RuntimeError("双均线策略未初始化")
        fast_period = int(params.get('fast_period', self._config['fast_period']))
        slow_period = int(params.get('slow_period', self._config['slow_period']))
        ma_type = str(params.get('ma_type', self._config['ma_type']))
        if fast_period >= slow_period:
            raise ValueError("快速周期必须小于慢速周期")
        if len(data) < slow_period:
            raise ValueError(f"数据长度不足，需要至少{slow_period}个数据点")

        close_prices = data['close']
        if ma_type == 'EMA':
            fast_ma = self._calculate_ema(close_prices, fast_period)
            slow_ma = self._calculate_ema(close_prices, slow_period)
        else:
            fast_ma = self._calculate_sma(close_prices, fast_period)
            slow_ma = self._calculate_sma(close_prices, slow_period)

        buy_signal = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
        sell_signal = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))

        position = pd.Series(0, index=data.index, dtype=int)
        current_position = 0
        for i in range(1, len(data)):
            if buy_signal.iloc[i] and current_position <= 0:
                current_position = 1
            elif sell_signal.iloc[i] and current_position >= 0:
                current_position = -1
            position.iloc[i] = current_position

        return {
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'position': position
        }

    def _calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        return data.rolling(window=period, min_periods=1).mean()

    def _calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        return data.ewm(span=period, adjust=False).mean()

    # 可选：示例配置小部件（不影响新接口）
    def create_config_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        widget = QWidget(parent)
        layout = QFormLayout(widget)
        fast_box = QSpinBox()
        fast_box.setRange(1, 50)
        fast_box.setValue(self._config['fast_period'])
        slow_box = QSpinBox()
        slow_box.setRange(2, 200)
        slow_box.setValue(self._config['slow_period'])
        ma_type_combo = QComboBox()
        ma_type_combo.addItems(['SMA', 'EMA'])
        ma_type_combo.setCurrentText(self._config['ma_type'])
        layout.addRow("快速均线周期:", fast_box)
        layout.addRow("慢速均线周期:", slow_box)
        layout.addRow("均线类型:", ma_type_combo)

        def on_change():
            new_cfg = {
                'fast_period': fast_box.value(),
                'slow_period': slow_box.value(),
                'ma_type': ma_type_combo.currentText()
            }
            if self.validate_config(new_cfg):
                self._config.update(new_cfg)
        fast_box.valueChanged.connect(on_change)
        slow_box.valueChanged.connect(on_change)
        ma_type_combo.currentTextChanged.connect(on_change)
        return widget
