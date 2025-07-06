"""
MACD指标插件示例

展示如何开发技术指标插件的完整示例。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpinBox, QDoubleSpinBox, QFormLayout

from ..plugin_interface import (
    IIndicatorPlugin, PluginMetadata, PluginType, PluginCategory,
    plugin_metadata, register_plugin, PluginContext
)


@plugin_metadata(
    name="MACD指标",
    version="1.0.0",
    description="移动平均收敛发散指标(MACD)，用于分析股价趋势和买卖信号",
    author="HIkyuu团队",
    email="support@hikyuu.org",
    website="https://hikyuu.org",
    license="MIT",
    plugin_type=PluginType.INDICATOR,
    category=PluginCategory.CORE,
    dependencies=["numpy", "pandas"],
    min_hikyuu_version="2.0.0",
    max_hikyuu_version="3.0.0",
    tags=["技术指标", "趋势分析", "MACD"],
    icon_path="icons/macd.png"
)
@register_plugin(PluginType.INDICATOR)
class MACDIndicatorPlugin(IIndicatorPlugin):
    """MACD指标插件"""

    def __init__(self):
        """初始化插件"""
        self._context: Optional[PluginContext] = None
        self._config = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9
        }

    @property
    def metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        return self._plugin_metadata

    def initialize(self, context: PluginContext) -> bool:
        """
        初始化插件

        Args:
            context: 插件上下文

        Returns:
            bool: 初始化是否成功
        """
        try:
            self._context = context

            # 加载配置
            config = context.get_plugin_config(self.metadata.name)
            if config:
                self._config.update(config)

            # 注册事件处理器
            context.register_event_handler("data_updated", self._on_data_updated)

            context.log_manager.info(f"MACD指标插件初始化成功")
            return True

        except Exception as e:
            if context:
                context.log_manager.error(f"MACD指标插件初始化失败: {e}")
            return False

    def cleanup(self) -> None:
        """清理插件资源"""
        if self._context:
            self._context.log_manager.info("MACD指标插件清理完成")

    def get_indicator_name(self) -> str:
        """获取指标名称"""
        return "MACD"

    def get_indicator_parameters(self) -> Dict[str, Any]:
        """获取指标参数定义"""
        return {
            'fast_period': {
                'type': 'int',
                'default': 12,
                'min': 1,
                'max': 100,
                'description': '快速EMA周期'
            },
            'slow_period': {
                'type': 'int',
                'default': 26,
                'min': 1,
                'max': 200,
                'description': '慢速EMA周期'
            },
            'signal_period': {
                'type': 'int',
                'default': 9,
                'min': 1,
                'max': 50,
                'description': '信号线EMA周期'
            }
        }

    def calculate(self, data: pd.DataFrame, **params) -> Dict[str, pd.Series]:
        """
        计算MACD指标

        Args:
            data: 价格数据，包含close列
            **params: 参数

        Returns:
            包含MACD、信号线和柱状图的字典
        """
        # 获取参数
        fast_period = params.get('fast_period', self._config['fast_period'])
        slow_period = params.get('slow_period', self._config['slow_period'])
        signal_period = params.get('signal_period', self._config['signal_period'])

        # 验证参数
        if fast_period >= slow_period:
            raise ValueError("快速周期必须小于慢速周期")

        if len(data) < slow_period:
            raise ValueError(f"数据长度不足，需要至少{slow_period}个数据点")

        # 计算EMA
        close_prices = data['close']
        ema_fast = self._calculate_ema(close_prices, fast_period)
        ema_slow = self._calculate_ema(close_prices, slow_period)

        # 计算MACD线
        macd_line = ema_fast - ema_slow

        # 计算信号线
        signal_line = self._calculate_ema(macd_line, signal_period)

        # 计算柱状图
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def get_plot_config(self) -> Dict[str, Any]:
        """
        获取绘图配置

        Returns:
            绘图配置
        """
        return {
            'subplot': True,  # 在子图中显示
            'subplot_title': 'MACD',
            'lines': [
                {
                    'name': 'MACD',
                    'data_key': 'macd',
                    'color': '#FF6B6B',
                    'width': 2
                },
                {
                    'name': '信号线',
                    'data_key': 'signal',
                    'color': '#4ECDC4',
                    'width': 2
                }
            ],
            'histograms': [
                {
                    'name': '柱状图',
                    'data_key': 'histogram',
                    'positive_color': '#FF6B6B',
                    'negative_color': '#4ECDC4'
                }
            ],
            'zero_line': True,  # 显示零轴线
            'legend': True
        }

    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式"""
        return {
            'type': 'object',
            'properties': {
                'fast_period': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 100,
                    'default': 12,
                    'title': '快速EMA周期'
                },
                'slow_period': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 200,
                    'default': 26,
                    'title': '慢速EMA周期'
                },
                'signal_period': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 50,
                    'default': 9,
                    'title': '信号线EMA周期'
                }
            },
            'required': ['fast_period', 'slow_period', 'signal_period']
        }

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return self._config.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证配置

        Args:
            config: 配置字典

        Returns:
            bool: 配置是否有效
        """
        try:
            fast_period = config.get('fast_period', 12)
            slow_period = config.get('slow_period', 26)
            signal_period = config.get('signal_period', 9)

            # 验证参数范围
            if not (1 <= fast_period <= 100):
                return False
            if not (1 <= slow_period <= 200):
                return False
            if not (1 <= signal_period <= 50):
                return False

            # 验证参数关系
            if fast_period >= slow_period:
                return False

            return True

        except Exception:
            return False

    def on_event(self, event_name: str, *args, **kwargs) -> None:
        """
        处理事件

        Args:
            event_name: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        if event_name == "config_changed":
            # 配置变更时重新加载配置
            if self._context:
                config = self._context.get_plugin_config(self.metadata.name)
                if config and self.validate_config(config):
                    self._config.update(config)
                    self._context.log_manager.info("MACD指标配置已更新")

    def _calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """
        计算指数移动平均线

        Args:
            prices: 价格序列
            period: 周期

        Returns:
            EMA序列
        """
        alpha = 2.0 / (period + 1)
        ema = pd.Series(index=prices.index, dtype=float)

        # 初始值使用简单移动平均
        ema.iloc[period-1] = prices.iloc[:period].mean()

        # 计算EMA
        for i in range(period, len(prices)):
            ema.iloc[i] = alpha * prices.iloc[i] + (1 - alpha) * ema.iloc[i-1]

        return ema

    def _on_data_updated(self, symbol: str, data: pd.DataFrame) -> None:
        """
        数据更新事件处理器

        Args:
            symbol: 股票代码
            data: 更新的数据
        """
        if self._context:
            self._context.log_manager.debug(f"收到数据更新事件: {symbol}")

    def get_signals(self, data: pd.DataFrame, **params) -> Dict[str, pd.Series]:
        """
        获取交易信号

        Args:
            data: 价格数据
            **params: 参数

        Returns:
            交易信号
        """
        # 计算MACD
        macd_data = self.calculate(data, **params)

        macd_line = macd_data['macd']
        signal_line = macd_data['signal']
        histogram = macd_data['histogram']

        # 生成交易信号
        buy_signals = pd.Series(False, index=data.index)
        sell_signals = pd.Series(False, index=data.index)

        # MACD上穿信号线为买入信号
        for i in range(1, len(macd_line)):
            if (macd_line.iloc[i] > signal_line.iloc[i] and
                    macd_line.iloc[i-1] <= signal_line.iloc[i-1]):
                buy_signals.iloc[i] = True
            elif (macd_line.iloc[i] < signal_line.iloc[i] and
                  macd_line.iloc[i-1] >= signal_line.iloc[i-1]):
                sell_signals.iloc[i] = True

        return {
            'buy': buy_signals,
            'sell': sell_signals
        }

    def create_config_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """
        创建配置组件

        Args:
            parent: 父组件

        Returns:
            配置组件
        """
        widget = QWidget(parent)
        layout = QFormLayout(widget)

        # 快速周期
        fast_spin = QSpinBox()
        fast_spin.setRange(1, 100)
        fast_spin.setValue(self._config['fast_period'])
        layout.addRow("快速EMA周期:", fast_spin)

        # 慢速周期
        slow_spin = QSpinBox()
        slow_spin.setRange(1, 200)
        slow_spin.setValue(self._config['slow_period'])
        layout.addRow("慢速EMA周期:", slow_spin)

        # 信号周期
        signal_spin = QSpinBox()
        signal_spin.setRange(1, 50)
        signal_spin.setValue(self._config['signal_period'])
        layout.addRow("信号线EMA周期:", signal_spin)

        # 连接信号
        def on_config_changed():
            new_config = {
                'fast_period': fast_spin.value(),
                'slow_period': slow_spin.value(),
                'signal_period': signal_spin.value()
            }

            if self.validate_config(new_config):
                self._config.update(new_config)
                if self._context:
                    self._context.save_plugin_config(self.metadata.name, new_config)
                    self._context.emit_event("config_changed", self.metadata.name, new_config)

        fast_spin.valueChanged.connect(on_config_changed)
        slow_spin.valueChanged.connect(on_config_changed)
        signal_spin.valueChanged.connect(on_config_changed)

        return widget
