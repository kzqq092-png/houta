from loguru import logger
"""
HIkyuu策略插件

将HIkyuu框架的策略和交易系统功能封装为插件，支持：
- HIkyuu信号系统
- HIkyuu交易系统
- HIkyuu策略组件
- 多种策略模板
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass, field

# HIkyuu相关导入
try:
    import hikyuu as hku
    from hikyuu import *
    from hikyuu.trade_sys import *
    # 尝试导入止损止盈组件，如果失败则使用替代方案
    try:
        from hikyuu.trade_sys import SL_FixedPercent, TP_FixedPercent
    except ImportError:
        # 如果特定组件不可用，尝试使用其他方式
        logger.warning("部分HIkyuu组件不可用，将使用基础功能")
    HIKYUU_AVAILABLE = True
except ImportError as e:
    HIKYUU_AVAILABLE = False
    logger.warning(f"HIkyuu未安装或无法导入，HIkyuu策略插件将无法使用: {e}")

# 项目内部导入
from core.strategy_extensions import (
    IStrategyPlugin, StrategyInfo, ParameterDef, Signal, TradeResult, Position,
    PerformanceMetrics, StandardMarketData, StrategyContext,
    StrategyType, SignalType, TradeAction, TradeStatus, RiskLevel,
    AssetType, TimeFrame
)

logger = logger

class FactorWeaveSignalAdapter:
    """HIkyuu信号适配器"""

    def __init__(self):
        self.signal_cache = {}

    def create_signal_from_hikyuu(self, hku_signal, symbol: str, timestamp: datetime, price: float) -> Signal:
        """从HIkyuu信号创建标准信号"""
        # 判断信号类型
        if hku_signal == 1:  # 买入信号
            signal_type = SignalType.BUY
        elif hku_signal == -1:  # 卖出信号
            signal_type = SignalType.SELL
        else:  # 无信号
            signal_type = SignalType.HOLD

        return Signal(
            symbol=symbol,
            signal_type=signal_type,
            strength=1.0 if signal_type != SignalType.HOLD else 0.0,
            timestamp=timestamp,
            price=price,
            reason=f"HIkyuu信号: {hku_signal}",
            metadata={'hikyuu_signal': hku_signal}
        )

    def convert_dataframe_to_kdata(self, df: pd.DataFrame, symbol: str = "000001") -> 'KData':
        """将DataFrame转换为HIkyuu KData"""
        if not HIKYUU_AVAILABLE:
            raise RuntimeError("HIkyuu未安装，无法转换数据")

        try:
            # 创建临时股票对象
            stock = Stock(Market("SH"), symbol, symbol)

            # 转换数据格式
            records = []
            for idx, row in df.iterrows():
                record = KRecord()
                record.datetime = Datetime(idx)
                record.openPrice = float(row['open'])
                record.highPrice = float(row['high'])
                record.lowPrice = float(row['low'])
                record.closePrice = float(row['close'])
                record.transAmount = float(row.get('amount', 0))
                record.transCount = int(row.get('volume', 0))
                records.append(record)

            # 创建KData
            kdata = KData(records)
            return kdata

        except Exception as e:
            logger.error(f"DataFrame转KData失败: {e}")
            raise

class FactorWeaveTradingSystemAdapter:
    """HIkyuu交易系统适配器"""

    def __init__(self):
        self.trading_system = None
        self.portfolio = None
        self.performance_stats = {}

    def create_trading_system(self, strategy_config: Dict[str, Any]) -> 'System':
        """创建HIkyuu交易系统"""
        if not HIKYUU_AVAILABLE:
            raise RuntimeError("HIkyuu未安装，无法创建交易系统")

        try:
            # 创建基础交易系统
            sys = System("HikyuuStrategy")

            # 配置买入信号
            if 'buy_signal' in strategy_config:
                buy_signal_config = strategy_config['buy_signal']
                if buy_signal_config['type'] == 'MA':
                    # 移动平均信号
                    n1 = buy_signal_config.get('short_period', 5)
                    n2 = buy_signal_config.get('long_period', 20)
                    sys.sg = SG_Cross(MA(n1), MA(n2))
                elif buy_signal_config['type'] == 'MACD':
                    # MACD信号
                    sys.sg = SG_MACD()

            # 配置卖出信号 (通常与买入信号相反)
            # HIkyuu的信号生成器通常同时处理买入和卖出

            # 配置资金管理
            if 'money_manager' in strategy_config:
                mm_config = strategy_config['money_manager']
                if mm_config['type'] == 'FixedCount':
                    sys.mm = MM_FixedCount(mm_config.get('count', 100))
                elif mm_config['type'] == 'FixedPercent':
                    sys.mm = MM_FixedPercent(mm_config.get('percent', 0.1))

            # 配置止损
            if 'stop_loss' in strategy_config:
                sl_config = strategy_config['stop_loss']
                if sl_config['type'] == 'FixedPercent':
                    try:
                        sys.sl = SL_FixedPercent(sl_config.get('percent', 0.03))
                    except NameError:
                        logger.warning("SL_FixedPercent不可用，跳过止损配置")

            # 配置止盈
            if 'take_profit' in strategy_config:
                tp_config = strategy_config['take_profit']
                if tp_config['type'] == 'FixedPercent':
                    try:
                        sys.tp = TP_FixedPercent(tp_config.get('percent', 0.2))
                    except NameError:
                        logger.warning("TP_FixedPercent不可用，跳过止盈配置")

            self.trading_system = sys
            return sys

        except Exception as e:
            logger.error(f"创建HIkyuu交易系统失败: {e}")
            raise

    def run_backtest(self, kdata: 'KData', initial_capital: float = 100000) -> Dict[str, Any]:
        """运行回测"""
        if not self.trading_system or not HIKYUU_AVAILABLE:
            raise RuntimeError("交易系统未初始化或HIkyuu不可用")

        try:
            # 创建投资组合
            self.portfolio = Portfolio()
            self.portfolio.tm = TM_Broker()  # 使用经纪人交易管理

            # 运行回测
            self.trading_system.run(kdata, Query(-100))  # 最近100个交易日

            # 获取交易记录
            trade_list = self.trading_system.tm.getTradeList()

            # 计算性能指标
            performance = self._calculate_performance(trade_list, initial_capital)

            return {
                'trades': [self._convert_trade_record(trade) for trade in trade_list],
                'performance': performance
            }

        except Exception as e:
            logger.error(f"HIkyuu回测运行失败: {e}")
            raise

    def _convert_trade_record(self, hku_trade) -> TradeResult:
        """转换HIkyuu交易记录为标准格式"""
        return TradeResult(
            trade_id=str(hku_trade.datetime),
            symbol=hku_trade.stock.market_code + hku_trade.stock.code,
            action=TradeAction.OPEN_LONG if hku_trade.business == BUSINESS.BUY else TradeAction.CLOSE_LONG,
            quantity=hku_trade.number,
            price=hku_trade.realPrice,
            timestamp=datetime.fromtimestamp(hku_trade.datetime.timestamp()),
            commission=hku_trade.cost.commission,
            status=TradeStatus.FILLED,
            metadata={'hikyuu_trade': True}
        )

    def _calculate_performance(self, trade_list: List, initial_capital: float) -> PerformanceMetrics:
        """计算性能指标"""
        if not trade_list:
            return PerformanceMetrics(
                total_return=0.0, annual_return=0.0, sharpe_ratio=0.0,
                max_drawdown=0.0, win_rate=0.0, profit_factor=0.0,
                total_trades=0, winning_trades=0, losing_trades=0,
                avg_win=0.0, avg_loss=0.0,
                start_date=datetime.now(), end_date=datetime.now()
            )

        # 计算基本统计
        total_trades = len(trade_list)
        profits = []

        for trade in trade_list:
            if hasattr(trade, 'profit'):
                profits.append(trade.profit)

        if not profits:
            profits = [0.0]

        winning_trades = len([p for p in profits if p > 0])
        losing_trades = len([p for p in profits if p < 0])

        total_profit = sum(profits)
        total_return = total_profit / initial_capital

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        avg_win = np.mean([p for p in profits if p > 0]) if winning_trades > 0 else 0.0
        avg_loss = abs(np.mean([p for p in profits if p < 0])) if losing_trades > 0 else 0.0

        profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if avg_loss > 0 else 0.0

        return PerformanceMetrics(
            total_return=total_return,
            annual_return=total_return,  # 简化计算
            sharpe_ratio=0.0,  # 需要更复杂的计算
            max_drawdown=0.0,  # 需要更复杂的计算
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            start_date=datetime.fromtimestamp(trade_list[0].datetime.timestamp()) if trade_list else datetime.now(),
            end_date=datetime.fromtimestamp(trade_list[-1].datetime.timestamp()) if trade_list else datetime.now()
        )

class HikyuuStrategyPlugin(IStrategyPlugin):
    """HIkyuu策略插件"""

    def __init__(self):
        self.signal_adapter = FactorWeaveSignalAdapter()
        self.trading_adapter = FactorWeaveTradingSystemAdapter()
        self.strategy_config = {}
        self.current_positions = {}
        self.trade_history = []

    @property
    def plugin_info(self) -> Dict[str, Any]:
        """获取插件基本信息"""
        return {
            'name': 'HIkyuu Strategy Plugin',
            'version': '1.0.0',
            'author': 'HIkyuu Team',
            'description': 'HIkyuu框架策略插件，提供完整的量化交易功能',
            'hikyuu_available': HIKYUU_AVAILABLE,
            'supported_features': [
                'signal_generation', 'trading_system', 'backtesting',
                'money_management', 'stop_loss', 'take_profit'
            ]
        }

    def get_strategy_info(self) -> StrategyInfo:
        """获取策略信息"""
        return StrategyInfo(
            name="hikyuu_strategy",
            display_name="HIkyuu策略",
            description="基于HIkyuu框架的量化交易策略，支持多种技术指标和交易系统",
            version="1.0.0",
            author="HIkyuu Team",
            strategy_type=StrategyType.QUANTITATIVE,
            parameters=[
                ParameterDef("signal_type", str, "MA", "信号类型", choices=["MA", "MACD", "RSI", "KDJ"]),
                ParameterDef("short_period", int, 5, "短周期", 1, 50),
                ParameterDef("long_period", int, 20, "长周期", 10, 200),
                ParameterDef("money_management", str, "FixedCount", "资金管理", choices=["FixedCount", "FixedPercent"]),
                ParameterDef("position_size", int, 100, "仓位大小", 1, 10000),
                ParameterDef("stop_loss_percent", float, 0.03, "止损百分比", 0.01, 0.2),
                ParameterDef("take_profit_percent", float, 0.2, "止盈百分比", 0.05, 1.0),
            ],
            supported_assets=[AssetType.STOCK, AssetType.INDEX, AssetType.FUND],
            time_frames=[TimeFrame.DAY_1, TimeFrame.WEEK_1, TimeFrame.MONTH_1],
            risk_level=RiskLevel.MEDIUM,
            tags=["hikyuu", "quantitative", "technical_analysis"]
        )

    def initialize_strategy(self, context: StrategyContext, parameters: Dict[str, Any]) -> bool:
        """初始化策略"""
        try:
            if not HIKYUU_AVAILABLE:
                logger.error("HIkyuu未安装，无法初始化策略")
                return False

            # 保存配置
            self.strategy_config = {
                'buy_signal': {
                    'type': parameters.get('signal_type', 'MA'),
                    'short_period': parameters.get('short_period', 5),
                    'long_period': parameters.get('long_period', 20)
                },
                'money_manager': {
                    'type': parameters.get('money_management', 'FixedCount'),
                    'count': parameters.get('position_size', 100),
                    'percent': parameters.get('position_size', 100) / 10000  # 转换为百分比
                },
                'stop_loss': {
                    'type': 'FixedPercent',
                    'percent': parameters.get('stop_loss_percent', 0.03)
                },
                'take_profit': {
                    'type': 'FixedPercent',
                    'percent': parameters.get('take_profit_percent', 0.2)
                }
            }

            # 创建交易系统
            self.trading_adapter.create_trading_system(self.strategy_config)

            logger.info(f"HIkyuu策略初始化成功: {parameters}")
            return True

        except Exception as e:
            logger.error(f"HIkyuu策略初始化失败: {e}")
            return False

    def generate_signals(self, market_data: StandardMarketData, context: StrategyContext) -> List[Signal]:
        """生成交易信号"""
        try:
            if not HIKYUU_AVAILABLE or not self.trading_adapter.trading_system:
                return []

            # 转换数据格式
            df = market_data.to_dataframe()
            kdata = self.signal_adapter.convert_dataframe_to_kdata(df, market_data.symbol)

            # 获取信号生成器
            signal_generator = self.trading_adapter.trading_system.sg

            if signal_generator is None:
                return []

            # 运行信号生成器
            signal_generator.setTO(kdata)
            signal_generator.calculate()

            # 获取最新信号
            signals = []
            if len(kdata) > 0:
                latest_record = kdata[-1]
                latest_datetime = datetime.fromtimestamp(latest_record.datetime.timestamp())
                latest_price = latest_record.closePrice

                # 检查买入信号
                buy_signal = signal_generator.getBuySignal(len(kdata) - 1)
                if buy_signal:
                    signals.append(self.signal_adapter.create_signal_from_hikyuu(
                        1, market_data.symbol, latest_datetime, latest_price
                    ))

                # 检查卖出信号
                sell_signal = signal_generator.getSellSignal(len(kdata) - 1)
                if sell_signal:
                    signals.append(self.signal_adapter.create_signal_from_hikyuu(
                        -1, market_data.symbol, latest_datetime, latest_price
                    ))

            return signals

        except Exception as e:
            logger.error(f"HIkyuu信号生成失败: {e}")
            return []

    def execute_trade(self, signal: Signal, context: StrategyContext) -> TradeResult:
        """执行交易"""
        try:
            # 生成交易ID
            trade_id = f"hikyuu_{signal.symbol}_{int(signal.timestamp.timestamp())}"

            # 确定交易动作
            if signal.signal_type == SignalType.BUY:
                action = TradeAction.OPEN_LONG
            elif signal.signal_type == SignalType.SELL:
                action = TradeAction.CLOSE_LONG
            else:
                action = TradeAction.ADJUST

            # 计算交易数量
            quantity = self.strategy_config.get('money_manager', {}).get('count', 100)

            # 计算手续费
            commission = signal.price * quantity * context.commission_rate

            # 创建交易结果
            trade_result = TradeResult(
                trade_id=trade_id,
                symbol=signal.symbol,
                action=action,
                quantity=quantity,
                price=signal.price,
                timestamp=signal.timestamp,
                commission=commission,
                status=TradeStatus.FILLED,  # 模拟交易，直接成交
                metadata={'signal_strength': signal.strength, 'hikyuu_strategy': True}
            )

            # 记录交易历史
            self.trade_history.append(trade_result)

            logger.info(f"HIkyuu交易执行: {action.value} {signal.symbol} {quantity}@{signal.price}")
            return trade_result

        except Exception as e:
            logger.error(f"HIkyuu交易执行失败: {e}")
            return TradeResult(
                trade_id=f"error_{int(signal.timestamp.timestamp())}",
                symbol=signal.symbol,
                action=TradeAction.OPEN_LONG,
                quantity=0,
                price=signal.price,
                timestamp=signal.timestamp,
                commission=0,
                status=TradeStatus.ERROR,
                error_message=str(e)
            )

    def update_position(self, trade_result: TradeResult, context: StrategyContext) -> Position:
        """更新持仓"""
        symbol = trade_result.symbol

        # 获取当前持仓
        current_position = self.current_positions.get(symbol)

        if current_position is None:
            # 新建持仓
            if trade_result.action in [TradeAction.OPEN_LONG, TradeAction.OPEN_SHORT]:
                quantity = trade_result.quantity
                avg_price = trade_result.price
            else:
                quantity = 0
                avg_price = 0
        else:
            # 更新现有持仓
            if trade_result.action == TradeAction.OPEN_LONG:
                # 加仓
                total_cost = (current_position.quantity * current_position.avg_price +
                              trade_result.quantity * trade_result.price)
                quantity = current_position.quantity + trade_result.quantity
                avg_price = total_cost / quantity if quantity > 0 else 0
            elif trade_result.action == TradeAction.CLOSE_LONG:
                # 减仓
                quantity = max(0, current_position.quantity - trade_result.quantity)
                avg_price = current_position.avg_price
            else:
                quantity = current_position.quantity
                avg_price = current_position.avg_price

        # 计算市值和盈亏
        current_price = trade_result.price
        market_value = quantity * current_price
        unrealized_pnl = (current_price - avg_price) * quantity if quantity > 0 else 0

        # 创建新的持仓对象
        position = Position(
            symbol=symbol,
            quantity=quantity,
            avg_price=avg_price,
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=0.0,  # 简化处理
            timestamp=trade_result.timestamp,
            metadata={'hikyuu_strategy': True}
        )

        # 更新持仓记录
        self.current_positions[symbol] = position

        return position

    def calculate_performance(self, context: StrategyContext) -> PerformanceMetrics:
        """计算策略性能"""
        try:
            if not self.trade_history:
                return PerformanceMetrics(
                    total_return=0.0, annual_return=0.0, sharpe_ratio=0.0,
                    max_drawdown=0.0, win_rate=0.0, profit_factor=0.0,
                    total_trades=0, winning_trades=0, losing_trades=0,
                    avg_win=0.0, avg_loss=0.0,
                    start_date=context.start_date, end_date=context.end_date
                )

            # 计算基本统计
            total_trades = len(self.trade_history)

            # 计算盈亏（简化计算）
            profits = []
            for i in range(0, len(self.trade_history), 2):  # 假设买卖成对
                if i + 1 < len(self.trade_history):
                    buy_trade = self.trade_history[i]
                    sell_trade = self.trade_history[i + 1]
                    if (buy_trade.action == TradeAction.OPEN_LONG and
                            sell_trade.action == TradeAction.CLOSE_LONG):
                        profit = (sell_trade.price - buy_trade.price) * buy_trade.quantity
                        profits.append(profit)

            if not profits:
                profits = [0.0]

            winning_trades = len([p for p in profits if p > 0])
            losing_trades = len([p for p in profits if p < 0])

            total_profit = sum(profits)
            total_return = total_profit / context.initial_capital

            win_rate = winning_trades / len(profits) if profits else 0.0

            avg_win = np.mean([p for p in profits if p > 0]) if winning_trades > 0 else 0.0
            avg_loss = abs(np.mean([p for p in profits if p < 0])) if losing_trades > 0 else 0.0

            profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if avg_loss > 0 else 0.0

            return PerformanceMetrics(
                total_return=total_return,
                annual_return=total_return,  # 简化计算
                sharpe_ratio=0.0,  # 需要更复杂的计算
                max_drawdown=0.0,  # 需要更复杂的计算
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                avg_win=avg_win,
                avg_loss=avg_loss,
                start_date=context.start_date,
                end_date=context.end_date,
                metadata={'hikyuu_strategy': True}
            )

        except Exception as e:
            logger.error(f"HIkyuu性能计算失败: {e}")
            return PerformanceMetrics(
                total_return=0.0, annual_return=0.0, sharpe_ratio=0.0,
                max_drawdown=0.0, win_rate=0.0, profit_factor=0.0,
                total_trades=0, winning_trades=0, losing_trades=0,
                avg_win=0.0, avg_loss=0.0,
                start_date=context.start_date, end_date=context.end_date
            )

    def cleanup(self) -> None:
        """清理资源"""
        try:
            self.current_positions.clear()
            self.trade_history.clear()
            self.strategy_config.clear()

            if hasattr(self.trading_adapter, 'trading_system'):
                self.trading_adapter.trading_system = None

            logger.info("HIkyuu策略资源清理完成")

        except Exception as e:
            logger.error(f"HIkyuu策略清理失败: {e}")

# 策略模板类
class TrendFollowingStrategy(HikyuuStrategyPlugin):
    """趋势跟踪策略模板"""

    def get_strategy_info(self) -> StrategyInfo:
        info = super().get_strategy_info()
        info.name = "hikyuu_trend_following"
        info.display_name = "HIkyuu趋势跟踪策略"
        info.description = "基于移动平均线的趋势跟踪策略"
        info.strategy_type = StrategyType.TREND_FOLLOWING
        info.parameters = [
            ParameterDef("short_ma", int, 5, "短期均线周期", 1, 50),
            ParameterDef("long_ma", int, 20, "长期均线周期", 10, 200),
            ParameterDef("position_size", int, 100, "仓位大小", 1, 10000),
        ]
        return info

class MeanReversionStrategy(HikyuuStrategyPlugin):
    """均值回归策略模板"""

    def get_strategy_info(self) -> StrategyInfo:
        info = super().get_strategy_info()
        info.name = "hikyuu_mean_reversion"
        info.display_name = "HIkyuu均值回归策略"
        info.description = "基于RSI指标的均值回归策略"
        info.strategy_type = StrategyType.MEAN_REVERSION
        info.parameters = [
            ParameterDef("rsi_period", int, 14, "RSI周期", 5, 50),
            ParameterDef("oversold_level", float, 30.0, "超卖水平", 10.0, 40.0),
            ParameterDef("overbought_level", float, 70.0, "超买水平", 60.0, 90.0),
            ParameterDef("position_size", int, 100, "仓位大小", 1, 10000),
        ]
        return info

class MomentumStrategy(HikyuuStrategyPlugin):
    """动量策略模板"""

    def get_strategy_info(self) -> StrategyInfo:
        info = super().get_strategy_info()
        info.name = "hikyuu_momentum"
        info.display_name = "HIkyuu动量策略"
        info.description = "基于MACD指标的动量策略"
        info.strategy_type = StrategyType.MOMENTUM
        info.parameters = [
            ParameterDef("fast_period", int, 12, "快线周期", 5, 30),
            ParameterDef("slow_period", int, 26, "慢线周期", 15, 50),
            ParameterDef("signal_period", int, 9, "信号线周期", 5, 20),
            ParameterDef("position_size", int, 100, "仓位大小", 1, 10000),
        ]
        return info

# 导出的策略类
AVAILABLE_STRATEGIES = {
    'hikyuu_strategy': HikyuuStrategyPlugin,
    'hikyuu_trend_following': TrendFollowingStrategy,
    'hikyuu_mean_reversion': MeanReversionStrategy,
    'hikyuu_momentum': MomentumStrategy,
}

def get_available_strategies() -> Dict[str, type]:
    """获取可用的HIkyuu策略"""
    if not HIKYUU_AVAILABLE:
        return {}
    return AVAILABLE_STRATEGIES

def create_strategy(strategy_name: str) -> Optional[HikyuuStrategyPlugin]:
    """创建策略实例"""
    if strategy_name in AVAILABLE_STRATEGIES and HIKYUU_AVAILABLE:
        return AVAILABLE_STRATEGIES[strategy_name]()
    return None
