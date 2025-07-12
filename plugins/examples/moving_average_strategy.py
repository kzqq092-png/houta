"""
双均线策略插件示例

展示经典的双均线交叉策略的完整插件实现。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpinBox, QComboBox, QFormLayout

# 修改导入方式，使用绝对导入
from plugins.plugin_interface import (
    IStrategyPlugin, PluginMetadata, PluginType, PluginCategory,
    plugin_metadata, register_plugin, PluginContext
)


@plugin_metadata(
    name="双均线策略",
    version="1.0.0",
    description="经典的双均线交叉策略，通过快慢均线交叉产生买卖信号",
    author="HIkyuu团队",
    email="support@hikyuu.org",
    website="https://hikyuu.org",
    license="MIT",
    plugin_type=PluginType.STRATEGY,
    category=PluginCategory.CORE,
    dependencies=["numpy", "pandas"],
    min_hikyuu_version="2.0.0",
    max_hikyuu_version="3.0.0",
    tags=["交易策略", "均线", "趋势跟踪"],
    icon_path="icons/ma_strategy.png"
)
@register_plugin(PluginType.STRATEGY)
class MovingAverageStrategyPlugin(IStrategyPlugin):
    """双均线策略插件"""

    def __init__(self):
        """初始化插件"""
        self._context: Optional[PluginContext] = None
        self._config = {
            'fast_period': 5,
            'slow_period': 20,
            'ma_type': 'SMA',  # SMA, EMA
            'stop_loss_pct': 0.05,  # 5%止损
            'take_profit_pct': 0.10  # 10%止盈
        }

    @property
    def metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        return self._plugin_metadata

    def initialize(self, context: PluginContext = None) -> bool:
        """
        初始化插件

        Args:
            context: 插件上下文

        Returns:
            bool: 初始化是否成功
        """
        try:
            self._context = context

            # 如果上下文不为空，加载配置和注册事件
            if context:
                # 加载配置
                config = context.get_plugin_config(self.metadata.name)
                if config:
                    self._config.update(config)

                # 注册事件处理器
                context.register_event_handler(
                    "market_open", self._on_market_open)
                context.register_event_handler(
                    "market_close", self._on_market_close)

                context.log_manager.info(f"双均线策略插件初始化成功")
            else:
                print("双均线策略插件初始化成功（无上下文）")

            return True

        except Exception as e:
            if context:
                context.log_manager.error(f"双均线策略插件初始化失败: {e}")
            else:
                print(f"双均线策略插件初始化失败: {e}")
            return False

    def cleanup(self) -> None:
        """清理插件资源"""
        if self._context:
            self._context.log_manager.info("双均线策略插件清理完成")

    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return "双均线策略"

    def get_strategy_parameters(self) -> Dict[str, Any]:
        """获取策略参数定义"""
        return {
            'fast_period': {
                'type': 'int',
                'default': 5,
                'min': 1,
                'max': 50,
                'description': '快速均线周期'
            },
            'slow_period': {
                'type': 'int',
                'default': 20,
                'min': 2,
                'max': 200,
                'description': '慢速均线周期'
            },
            'ma_type': {
                'type': 'str',
                'default': 'SMA',
                'choices': ['SMA', 'EMA'],
                'description': '均线类型'
            },
            'stop_loss_pct': {
                'type': 'float',
                'default': 0.05,
                'min': 0.0,
                'max': 0.5,
                'description': '止损百分比'
            },
            'take_profit_pct': {
                'type': 'float',
                'default': 0.10,
                'min': 0.0,
                'max': 1.0,
                'description': '止盈百分比'
            }
        }

    def generate_signals(self, data: pd.DataFrame, **params) -> Dict[str, pd.Series]:
        """
        生成交易信号

        Args:
            data: 市场数据，包含open, high, low, close, volume列
            **params: 策略参数

        Returns:
            交易信号字典
        """
        # 获取参数
        fast_period = params.get('fast_period', self._config['fast_period'])
        slow_period = params.get('slow_period', self._config['slow_period'])
        ma_type = params.get('ma_type', self._config['ma_type'])

        # 验证参数
        if fast_period >= slow_period:
            raise ValueError("快速周期必须小于慢速周期")

        if len(data) < slow_period:
            raise ValueError(f"数据长度不足，需要至少{slow_period}个数据点")

        # 计算均线
        close_prices = data['close']

        if ma_type == 'EMA':
            fast_ma = self._calculate_ema(close_prices, fast_period)
            slow_ma = self._calculate_ema(close_prices, slow_period)
        else:  # SMA
            fast_ma = self._calculate_sma(close_prices, fast_period)
            slow_ma = self._calculate_sma(close_prices, slow_period)

        # 生成基础信号
        buy_signal = pd.Series(False, index=data.index)
        sell_signal = pd.Series(False, index=data.index)

        # 金叉买入信号：快线上穿慢线
        golden_cross = (fast_ma > slow_ma) & (
            fast_ma.shift(1) <= slow_ma.shift(1))
        buy_signal = golden_cross

        # 死叉卖出信号：快线下穿慢线
        death_cross = (fast_ma < slow_ma) & (
            fast_ma.shift(1) >= slow_ma.shift(1))
        sell_signal = death_cross

        # 计算持仓状态
        position = pd.Series(0, index=data.index, dtype=int)
        current_position = 0

        for i in range(1, len(data)):
            if buy_signal.iloc[i] and current_position <= 0:
                current_position = 1  # 买入
            elif sell_signal.iloc[i] and current_position >= 0:
                current_position = -1  # 卖出

            position.iloc[i] = current_position

        return {
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'position': position,
            'golden_cross': golden_cross,
            'death_cross': death_cross
        }

    def backtest(self, data: pd.DataFrame, **params) -> Dict[str, Any]:
        """
        回测策略

        Args:
            data: 历史数据
            **params: 策略参数

        Returns:
            回测结果
        """
        # 生成信号
        signals = self.generate_signals(data, **params)

        # 获取参数
        stop_loss_pct = params.get(
            'stop_loss_pct', self._config['stop_loss_pct'])
        take_profit_pct = params.get(
            'take_profit_pct', self._config['take_profit_pct'])

        # 模拟交易
        trades = []
        position = 0
        entry_price = 0
        entry_date = None

        for i, (date, row) in enumerate(data.iterrows()):
            current_price = row['close']

            # 检查买入信号
            if signals['buy_signal'].iloc[i] and position == 0:
                position = 1
                entry_price = current_price
                entry_date = date

                trades.append({
                    'type': 'buy',
                    'date': date,
                    'price': current_price,
                    'position': position
                })

            # 检查卖出信号或止损止盈
            elif position > 0:
                should_exit = False
                exit_reason = ""

                # 检查卖出信号
                if signals['sell_signal'].iloc[i]:
                    should_exit = True
                    exit_reason = "信号卖出"

                # 检查止损
                elif stop_loss_pct > 0 and current_price <= entry_price * (1 - stop_loss_pct):
                    should_exit = True
                    exit_reason = "止损"

                # 检查止盈
                elif take_profit_pct > 0 and current_price >= entry_price * (1 + take_profit_pct):
                    should_exit = True
                    exit_reason = "止盈"

                if should_exit:
                    profit_pct = (current_price - entry_price) / entry_price

                    trades.append({
                        'type': 'sell',
                        'date': date,
                        'price': current_price,
                        'position': 0,
                        'entry_price': entry_price,
                        'entry_date': entry_date,
                        'profit_pct': profit_pct,
                        'exit_reason': exit_reason
                    })

                    position = 0
                    entry_price = 0
                    entry_date = None

        # 计算绩效指标
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'trades': []
            }

        # 提取交易对
        trade_pairs = []
        buy_trade = None

        for trade in trades:
            if trade['type'] == 'buy':
                buy_trade = trade
            elif trade['type'] == 'sell' and buy_trade:
                trade_pairs.append({
                    'entry_date': buy_trade['date'],
                    'exit_date': trade['date'],
                    'entry_price': buy_trade['price'],
                    'exit_price': trade['price'],
                    'profit_pct': trade['profit_pct'],
                    'exit_reason': trade['exit_reason']
                })
                buy_trade = None

        if not trade_pairs:
            return {
                'total_trades': len(trades),
                'win_rate': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'trades': trades
            }

        # 计算统计指标
        profits = [tp['profit_pct'] for tp in trade_pairs]
        win_trades = [p for p in profits if p > 0]

        total_return = np.prod([1 + p for p in profits]) - 1
        win_rate = len(win_trades) / len(profits) if profits else 0

        # 计算最大回撤
        cumulative_returns = np.cumprod([1 + p for p in profits])
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0

        return {
            'total_trades': len(trade_pairs),
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': abs(max_drawdown),
            'avg_profit': np.mean(profits) if profits else 0,
            'avg_win': np.mean(win_trades) if win_trades else 0,
            'avg_loss': np.mean([p for p in profits if p < 0]) if profits else 0,
            'trades': trades,
            'trade_pairs': trade_pairs
        }

    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式"""
        return {
            'type': 'object',
            'properties': {
                'fast_period': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 50,
                    'default': 5,
                    'title': '快速均线周期'
                },
                'slow_period': {
                    'type': 'integer',
                    'minimum': 2,
                    'maximum': 200,
                    'default': 20,
                    'title': '慢速均线周期'
                },
                'ma_type': {
                    'type': 'string',
                    'enum': ['SMA', 'EMA'],
                    'default': 'SMA',
                    'title': '均线类型'
                },
                'stop_loss_pct': {
                    'type': 'number',
                    'minimum': 0.0,
                    'maximum': 0.5,
                    'default': 0.05,
                    'title': '止损百分比'
                },
                'take_profit_pct': {
                    'type': 'number',
                    'minimum': 0.0,
                    'maximum': 1.0,
                    'default': 0.10,
                    'title': '止盈百分比'
                }
            },
            'required': ['fast_period', 'slow_period', 'ma_type']
        }

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return self._config.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        try:
            fast_period = config.get('fast_period', 5)
            slow_period = config.get('slow_period', 20)
            ma_type = config.get('ma_type', 'SMA')

            # 验证周期
            if not isinstance(fast_period, int) or fast_period < 1 or fast_period > 50:
                return False

            if not isinstance(slow_period, int) or slow_period < 2 or slow_period > 200:
                return False

            # 验证快慢周期关系
            if fast_period >= slow_period:
                return False

            # 验证均线类型
            if ma_type not in ['SMA', 'EMA']:
                return False

            return True

        except Exception:
            return False

    def on_event(self, event_name: str, *args, **kwargs) -> None:
        """处理事件"""
        if self._context:
            if event_name == "market_open":
                self._context.log_manager.info("双均线策略：市场开盘")
            elif event_name == "market_close":
                self._context.log_manager.info("双均线策略：市场收盘")

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

    def _calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        计算指数移动平均

        Args:
            data: 数据序列
            period: 周期

        Returns:
            指数移动平均序列
        """
        return data.ewm(span=period, adjust=False).mean()

    def _on_market_open(self) -> None:
        """市场开盘事件处理器"""
        if self._context:
            self._context.log_manager.debug("双均线策略：处理市场开盘事件")

    def _on_market_close(self) -> None:
        """市场收盘事件处理器"""
        if self._context:
            self._context.log_manager.debug("双均线策略：处理市场收盘事件")

    def create_config_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """创建配置组件"""
        widget = QWidget(parent)
        layout = QFormLayout(widget)

        # 快速均线周期
        fast_period_spinbox = QSpinBox()
        fast_period_spinbox.setRange(1, 50)
        fast_period_spinbox.setValue(self._config['fast_period'])
        layout.addRow("快速均线周期:", fast_period_spinbox)

        # 慢速均线周期
        slow_period_spinbox = QSpinBox()
        slow_period_spinbox.setRange(2, 200)
        slow_period_spinbox.setValue(self._config['slow_period'])
        layout.addRow("慢速均线周期:", slow_period_spinbox)

        # 均线类型
        ma_type_combo = QComboBox()
        ma_type_combo.addItems(['SMA', 'EMA'])
        ma_type_combo.setCurrentText(self._config['ma_type'])
        layout.addRow("均线类型:", ma_type_combo)

        def on_config_changed():
            """配置变化处理"""
            fast_period = fast_period_spinbox.value()
            slow_period = slow_period_spinbox.value()

            # 确保快速周期小于慢速周期
            if fast_period >= slow_period:
                fast_period_spinbox.setValue(max(1, slow_period - 1))
                return

            self._config['fast_period'] = fast_period_spinbox.value()
            self._config['slow_period'] = slow_period_spinbox.value()
            self._config['ma_type'] = ma_type_combo.currentText()

            if self._context:
                self._context.save_plugin_config(
                    self.metadata.name, self._config)

        # 连接信号
        fast_period_spinbox.valueChanged.connect(on_config_changed)
        slow_period_spinbox.valueChanged.connect(on_config_changed)
        ma_type_combo.currentTextChanged.connect(on_config_changed)

        return widget
