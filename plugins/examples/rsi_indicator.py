"""
RSI指标插件示例

展示相对强弱指标(RSI)的完整插件实现。
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
    name="RSI指标",
    version="1.0.0",
    description="相对强弱指标(RSI)，用于判断股票超买超卖状态",
    author="HIkyuu团队",
    email="support@hikyuu.org",
    website="https://hikyuu.org",
    license="MIT",
    plugin_type=PluginType.INDICATOR,
    category=PluginCategory.CORE,
    dependencies=["numpy", "pandas"],
    min_hikyuu_version="2.0.0",
    max_hikyuu_version="3.0.0",
    tags=["技术指标", "超买超卖", "RSI"],
    icon_path="icons/rsi.png"
)
@register_plugin(PluginType.INDICATOR)
class RSIIndicatorPlugin(IIndicatorPlugin):
    """RSI指标插件"""

    def __init__(self):
        """初始化插件"""
        self._context: Optional[PluginContext] = None
        self._config = {
            'period': 14,
            'overbought_level': 70.0,
            'oversold_level': 30.0
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

            context.log_manager.info(f"RSI指标插件初始化成功")
            return True

        except Exception as e:
            if context:
                context.log_manager.error(f"RSI指标插件初始化失败: {e}")
            return False

    def cleanup(self) -> None:
        """清理插件资源"""
        if self._context:
            self._context.log_manager.info("RSI指标插件清理完成")

    def get_indicator_name(self) -> str:
        """获取指标名称"""
        return "RSI"

    def get_indicator_parameters(self) -> Dict[str, Any]:
        """获取指标参数定义"""
        return {
            'period': {
                'type': 'int',
                'default': 14,
                'min': 2,
                'max': 100,
                'description': 'RSI计算周期'
            },
            'overbought_level': {
                'type': 'float',
                'default': 70.0,
                'min': 50.0,
                'max': 90.0,
                'description': '超买水平线'
            },
            'oversold_level': {
                'type': 'float',
                'default': 30.0,
                'min': 10.0,
                'max': 50.0,
                'description': '超卖水平线'
            }
        }

    def calculate(self, data: pd.DataFrame, **params) -> Dict[str, pd.Series]:
        """
        计算RSI指标

        Args:
            data: 价格数据，包含close列
            **params: 参数

        Returns:
            包含RSI值的字典
        """
        # 获取参数
        period = params.get('period', self._config['period'])

        # 验证参数
        if period < 2:
            raise ValueError("RSI周期必须大于等于2")

        if len(data) < period + 1:
            raise ValueError(f"数据长度不足，需要至少{period + 1}个数据点")

        # 计算价格变化
        close_prices = data['close']
        price_changes = close_prices.diff()

        # 分离上涨和下跌
        gains = price_changes.where(price_changes > 0, 0)
        losses = -price_changes.where(price_changes < 0, 0)

        # 计算平均涨跌幅
        avg_gain = self._calculate_sma(gains, period)
        avg_loss = self._calculate_sma(losses, period)

        # 计算RSI
        rs = avg_gain / avg_loss.replace(0, np.inf)  # 避免除零
        rsi = 100 - (100 / (1 + rs))

        # 处理无效值
        rsi = rsi.fillna(50)  # 用中性值填充NaN

        return {
            'rsi': rsi
        }

    def get_plot_config(self) -> Dict[str, Any]:
        """
        获取绘图配置

        Returns:
            绘图配置
        """
        overbought = self._config['overbought_level']
        oversold = self._config['oversold_level']

        return {
            'subplot': True,  # 在子图中显示
            'subplot_title': 'RSI',
            'y_range': [0, 100],  # Y轴范围
            'lines': [
                {
                    'name': 'RSI',
                    'data_key': 'rsi',
                    'color': '#FF6B6B',
                    'width': 2
                }
            ],
            'horizontal_lines': [
                {
                    'name': '超买线',
                    'value': overbought,
                    'color': '#FF0000',
                    'style': 'dashed',
                    'width': 1
                },
                {
                    'name': '超卖线',
                    'value': oversold,
                    'color': '#00FF00',
                    'style': 'dashed',
                    'width': 1
                },
                {
                    'name': '中轴线',
                    'value': 50,
                    'color': '#808080',
                    'style': 'dotted',
                    'width': 1
                }
            ],
            'legend': True
        }

    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式"""
        return {
            'type': 'object',
            'properties': {
                'period': {
                    'type': 'integer',
                    'minimum': 2,
                    'maximum': 100,
                    'default': 14,
                    'title': 'RSI周期'
                },
                'overbought_level': {
                    'type': 'number',
                    'minimum': 50.0,
                    'maximum': 90.0,
                    'default': 70.0,
                    'title': '超买水平'
                },
                'oversold_level': {
                    'type': 'number',
                    'minimum': 10.0,
                    'maximum': 50.0,
                    'default': 30.0,
                    'title': '超卖水平'
                }
            },
            'required': ['period', 'overbought_level', 'oversold_level']
        }

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return self._config.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        try:
            period = config.get('period', 14)
            overbought = config.get('overbought_level', 70.0)
            oversold = config.get('oversold_level', 30.0)

            # 验证周期
            if not isinstance(period, int) or period < 2 or period > 100:
                return False

            # 验证超买超卖水平
            if not isinstance(overbought, (int, float)) or overbought < 50 or overbought > 90:
                return False

            if not isinstance(oversold, (int, float)) or oversold < 10 or oversold > 50:
                return False

            # 验证超买水平必须大于超卖水平
            if overbought <= oversold:
                return False

            return True

        except Exception:
            return False

    def on_event(self, event_name: str, *args, **kwargs) -> None:
        """处理事件"""
        if event_name == "data_updated" and self._context:
            try:
                symbol = args[0] if args else "unknown"
                self._context.log_manager.info(f"RSI指标接收到数据更新事件: {symbol}")
            except Exception as e:
                self._context.log_manager.error(f"处理数据更新事件失败: {e}")

    def _calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """
        计算简单移动平均

        Args:
            data: 数据序列
            period: 周期

        Returns:
            移动平均序列
        """
        return data.rolling(window=period, min_periods=1).mean()

    def _on_data_updated(self, symbol: str, data: pd.DataFrame) -> None:
        """数据更新事件处理器"""
        if self._context:
            self._context.log_manager.debug(f"RSI指标处理数据更新: {symbol}")

    def get_signals(self, data: pd.DataFrame, **params) -> Dict[str, pd.Series]:
        """
        生成交易信号

        Args:
            data: 价格数据
            **params: 参数

        Returns:
            交易信号
        """
        # 计算RSI
        rsi_result = self.calculate(data, **params)
        rsi = rsi_result['rsi']

        overbought = params.get('overbought_level', self._config['overbought_level'])
        oversold = params.get('oversold_level', self._config['oversold_level'])

        # 生成信号
        buy_signal = pd.Series(False, index=data.index)
        sell_signal = pd.Series(False, index=data.index)

        # 超卖区域买入信号
        buy_signal = (rsi < oversold) & (rsi.shift(1) >= oversold)

        # 超买区域卖出信号
        sell_signal = (rsi > overbought) & (rsi.shift(1) <= overbought)

        return {
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'rsi_overbought': rsi > overbought,
            'rsi_oversold': rsi < oversold
        }

    def create_config_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """创建配置组件"""
        widget = QWidget(parent)
        layout = QFormLayout(widget)

        # RSI周期
        period_spinbox = QSpinBox()
        period_spinbox.setRange(2, 100)
        period_spinbox.setValue(self._config['period'])
        layout.addRow("RSI周期:", period_spinbox)

        # 超买水平
        overbought_spinbox = QDoubleSpinBox()
        overbought_spinbox.setRange(50.0, 90.0)
        overbought_spinbox.setSingleStep(1.0)
        overbought_spinbox.setValue(self._config['overbought_level'])
        layout.addRow("超买水平:", overbought_spinbox)

        # 超卖水平
        oversold_spinbox = QDoubleSpinBox()
        oversold_spinbox.setRange(10.0, 50.0)
        oversold_spinbox.setSingleStep(1.0)
        oversold_spinbox.setValue(self._config['oversold_level'])
        layout.addRow("超卖水平:", oversold_spinbox)

        def on_config_changed():
            """配置变化处理"""
            self._config['period'] = period_spinbox.value()
            self._config['overbought_level'] = overbought_spinbox.value()
            self._config['oversold_level'] = oversold_spinbox.value()

            if self._context:
                self._context.save_plugin_config(self.metadata.name, self._config)

        # 连接信号
        period_spinbox.valueChanged.connect(on_config_changed)
        overbought_spinbox.valueChanged.connect(on_config_changed)
        oversold_spinbox.valueChanged.connect(on_config_changed)

        return widget
