#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略适配器 - 将20字段标准策略适配到现有策略框架

功能：
1. 将简单策略接口适配到IStrategyPlugin接口
2. 使现有策略管理器可以使用新的20字段标准策略
3. 保持代码复用，避免重复开发

作者：FactorWeave-Quant Team
版本：V2.0.4
日期：2025-10-12
"""

from examples.strategies.vwap_mean_reversion_strategy import VWAPMeanReversionStrategy as OriginalVWAPStrategy
from examples.strategies.adj_price_momentum_strategy import AdjPriceMomentumStrategy as OriginalAdjMomentum
from core.strategy_extensions import (
    IStrategyPlugin, StrategyInfo, ParameterDef,
    StrategyContext, StandardMarketData,
    StrategyType, AssetType, TimeFrame, RiskLevel
)
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入现有策略框架

# 导入新的20字段标准策略


class AdjMomentumPlugin(IStrategyPlugin):
    """
    复权价格动量策略插件（适配器）

    将简单的AdjPriceMomentumStrategy适配到IStrategyPlugin接口，
    使其可以被现有的策略管理系统使用。
    """

    def __init__(self):
        """初始化策略插件"""
        self.original_strategy = OriginalAdjMomentum()
        self.context = None
        logger.info("初始化复权价格动量策略插件")

    def get_strategy_info(self) -> StrategyInfo:
        """
        返回策略信息

        Returns:
            策略信息对象
        """
        return StrategyInfo(
            name="复权价格动量策略",
            description="使用复权价格计算真实动量，选择动量最强的股票。基于20字段标准K线数据。",
            version="2.0.4",
            author="FactorWeave-Quant Team",
            strategy_type=StrategyType.TREND_FOLLOWING,
            asset_types=[AssetType.STOCK_A],
            timeframes=[TimeFrame.DAILY],
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                ParameterDef(
                    name="lookback_period",
                    display_name="动量回溯周期",
                    type=int,
                    default_value=20,
                    min_value=5,
                    max_value=100,
                    description="计算动量的回溯天数（建议：10-60天）"
                ),
                ParameterDef(
                    name="top_n",
                    display_name="选择数量",
                    type=int,
                    default_value=10,
                    min_value=1,
                    max_value=50,
                    description="选择动量最强的前N只股票"
                )
            ],
            required_data_fields=['adj_close', 'adj_factor', 'close', 'datetime', 'symbol'],
            metadata={
                'category': '20字段标准策略',
                'uses_adj_close': True,
                'uses_vwap': False,
                'uses_turnover_rate': False,
                'data_source': 'any'
            }
        )

    def initialize(self, context: StrategyContext) -> None:
        """
        初始化策略

        Args:
            context: 策略上下文
        """
        self.context = context

        # 设置原始策略的参数
        lookback_period = context.parameters.get('lookback_period', 20)
        top_n = context.parameters.get('top_n', 10)

        self.original_strategy.set_parameters(
            lookback_period=lookback_period,
            top_n=top_n
        )

        logger.info(f"策略初始化完成，参数: lookback_period={lookback_period}, top_n={top_n}")

    def on_data(self, context: StrategyContext) -> None:
        """
        数据更新回调

        Args:
            context: 策略上下文
        """
        try:
            # 获取K线数据
            data = context.get_bar_data()

            if data is None or data.empty:
                logger.warning("未获取到K线数据")
                return

            # 验证数据
            if not self.original_strategy.validate_data(data):
                logger.warning("数据验证失败")
                return

            # 计算动量
            momentum = self.original_strategy.calculate_momentum(data)

            if momentum.empty or len(momentum) == 0:
                logger.warning("动量计算失败")
                return

            # 获取最新动量值
            latest_momentum = momentum.iloc[-1]

            # 生成交易信号
            # 正动量：买入
            if latest_momentum > 0:
                logger.info(f"生成买入信号: {context.symbol}, 动量={latest_momentum:.2%}")
                context.buy(context.symbol, 100)  # 买入100股

            # 负动量：卖出（如果有持仓）
            elif latest_momentum < -0.05:  # 动量下跌超过5%
                current_position = context.get_position(context.symbol)
                if current_position and current_position.volume > 0:
                    logger.info(f"生成卖出信号: {context.symbol}, 动量={latest_momentum:.2%}")
                    context.sell(context.symbol, current_position.volume)

        except Exception as e:
            logger.error(f"策略执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def on_trade(self, context: StrategyContext, trade) -> None:
        """
        交易执行回调

        Args:
            context: 策略上下文
            trade: 交易结果
        """
        logger.info(f"交易执行: {trade}")

    def on_order(self, context: StrategyContext, order) -> None:
        """
        订单状态回调

        Args:
            context: 策略上下文
            order: 订单对象
        """
        logger.info(f"订单状态: {order}")

    def finalize(self, context: StrategyContext) -> None:
        """
        策略结束回调

        Args:
            context: 策略上下文
        """
        logger.info("策略执行结束")


class VWAPReversionPlugin(IStrategyPlugin):
    """
    VWAP均值回归策略插件（适配器）

    将简单的VWAPMeanReversionStrategy适配到IStrategyPlugin接口。
    """

    def __init__(self):
        """初始化策略插件"""
        self.original_strategy = OriginalVWAPStrategy()
        self.context = None
        self.position_day_count = 0  # 持仓天数计数
        logger.info("初始化VWAP均值回归策略插件")

    def get_strategy_info(self) -> StrategyInfo:
        """
        返回策略信息

        Returns:
            策略信息对象
        """
        return StrategyInfo(
            name="VWAP均值回归策略",
            description="当价格偏离VWAP超过阈值时进行反向交易，期待价格回归。基于20字段标准K线数据。",
            version="2.0.4",
            author="FactorWeave-Quant Team",
            strategy_type=StrategyType.MEAN_REVERSION,
            asset_types=[AssetType.STOCK_A],
            timeframes=[TimeFrame.DAILY, TimeFrame.INTRADAY],
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                ParameterDef(
                    name="deviation_threshold",
                    display_name="偏离阈值",
                    type=float,
                    default_value=0.02,
                    min_value=0.005,
                    max_value=0.10,
                    description="触发交易的VWAP偏离度（2%=0.02）"
                ),
                ParameterDef(
                    name="hold_period",
                    display_name="持有周期",
                    type=int,
                    default_value=3,
                    min_value=1,
                    max_value=20,
                    description="最大持有天数"
                ),
                ParameterDef(
                    name="min_turnover_rate",
                    display_name="最小换手率",
                    type=float,
                    default_value=0.5,
                    min_value=0.1,
                    max_value=10.0,
                    description="流动性过滤阈值（%）"
                )
            ],
            required_data_fields=['vwap', 'close', 'turnover_rate', 'datetime', 'symbol', 'high', 'low'],
            metadata={
                'category': '20字段标准策略',
                'uses_adj_close': False,
                'uses_vwap': True,
                'uses_turnover_rate': True,
                'data_source': 'any'
            }
        )

    def initialize(self, context: StrategyContext) -> None:
        """
        初始化策略

        Args:
            context: 策略上下文
        """
        self.context = context

        # 设置原始策略的参数
        deviation_threshold = context.parameters.get('deviation_threshold', 0.02)
        hold_period = context.parameters.get('hold_period', 3)
        min_turnover_rate = context.parameters.get('min_turnover_rate', 0.5)

        self.original_strategy.set_parameters(
            deviation_threshold=deviation_threshold,
            hold_period=hold_period,
            use_turnover_filter=True,
            min_turnover_rate=min_turnover_rate
        )

        self.position_day_count = 0

        logger.info(f"策略初始化完成，参数: deviation={deviation_threshold:.1%}, " +
                    f"hold_period={hold_period}, min_turnover={min_turnover_rate}%")

    def on_data(self, context: StrategyContext) -> None:
        """
        数据更新回调

        Args:
            context: 策略上下文
        """
        try:
            # 获取K线数据
            data = context.get_bar_data()

            if data is None or data.empty:
                logger.warning("未获取到K线数据")
                return

            # 验证数据
            if not self.original_strategy.validate_vwap_data(data):
                logger.warning("VWAP数据验证失败")
                return

            # 计算偏离度
            deviation = self.original_strategy.calculate_vwap_deviation(data)

            if deviation.empty:
                logger.warning("偏离度计算失败")
                return

            # 获取最新数据
            latest_data = data.iloc[-1]
            latest_deviation = deviation.iloc[-1]
            latest_turnover_rate = latest_data.get('turnover_rate', 0)

            # 流动性检查
            if latest_turnover_rate < self.original_strategy.min_turnover_rate:
                logger.debug(f"流动性不足: {latest_turnover_rate}% < {self.original_strategy.min_turnover_rate}%")
                return

            # 获取当前持仓
            current_position = context.get_position(context.symbol)
            has_position = current_position and current_position.volume > 0

            # 持仓管理
            if has_position:
                self.position_day_count += 1

                # 达到持有周期或回归VWAP，平仓
                if (self.position_day_count >= self.original_strategy.hold_period or
                        abs(latest_deviation) < 0.005):  # 回归到VWAP附近
                    logger.info(f"平仓: 持有{self.position_day_count}天, 偏离度={latest_deviation:.2%}")
                    context.sell(context.symbol, current_position.volume)
                    self.position_day_count = 0

            # 开仓逻辑
            else:
                threshold = self.original_strategy.deviation_threshold

                # 买入信号：价格低于VWAP
                if latest_deviation < -threshold:
                    logger.info(f"生成买入信号: {context.symbol}, " +
                                f"偏离度={latest_deviation:.2%}, " +
                                f"换手率={latest_turnover_rate:.2f}%")
                    context.buy(context.symbol, 100)
                    self.position_day_count = 0

                # 卖空信号（如果支持）：价格高于VWAP
                elif latest_deviation > threshold:
                    logger.info(f"生成卖出信号: {context.symbol}, " +
                                f"偏离度={latest_deviation:.2%}")
                    # 注意：这里假设可以卖空，实际需要检查账户是否支持
                    # context.sell(context.symbol, 100)

        except Exception as e:
            logger.error(f"策略执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def on_trade(self, context: StrategyContext, trade) -> None:
        """
        交易执行回调

        Args:
            context: 策略上下文
            trade: 交易结果
        """
        logger.info(f"交易执行: {trade}")

    def on_order(self, context: StrategyContext, order) -> None:
        """
        订单状态回调

        Args:
            context: 策略上下文
            order: 订单对象
        """
        logger.info(f"订单状态: {order}")

    def finalize(self, context: StrategyContext) -> None:
        """
        策略结束回调

        Args:
            context: 策略上下文
        """
        logger.info("策略执行结束")


# 策略注册工厂函数
def register_20field_strategies(strategy_service):
    """
    注册20字段标准策略到策略服务

    Args:
        strategy_service: 策略服务实例
    """
    try:
        # 注册复权动量策略
        strategy_service.register_strategy_plugin(
            'adj_momentum_v2',
            AdjMomentumPlugin
        )
        logger.info("✅ 已注册: 复权价格动量策略 (adj_momentum_v2)")

        # 注册VWAP均值回归策略
        strategy_service.register_strategy_plugin(
            'vwap_reversion_v2',
            VWAPReversionPlugin
        )
        logger.info("✅ 已注册: VWAP均值回归策略 (vwap_reversion_v2)")

        logger.success("✅ 20字段标准策略注册完成！")

    except Exception as e:
        logger.error(f"注册20字段策略失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


# 使用示例
if __name__ == "__main__":
    print("策略适配器模块")
    print("=" * 60)

    # 显示策略信息
    print("\n1. 复权价格动量策略:")
    adj_plugin = AdjMomentumPlugin()
    adj_info = adj_plugin.get_strategy_info()
    print(f"   名称: {adj_info.name}")
    print(f"   描述: {adj_info.description}")
    print(f"   类型: {adj_info.strategy_type}")
    print(f"   参数数量: {len(adj_info.parameters)}")

    print("\n2. VWAP均值回归策略:")
    vwap_plugin = VWAPReversionPlugin()
    vwap_info = vwap_plugin.get_strategy_info()
    print(f"   名称: {vwap_info.name}")
    print(f"   描述: {vwap_info.description}")
    print(f"   类型: {vwap_info.strategy_type}")
    print(f"   参数数量: {len(vwap_info.parameters)}")

    print("\n" + "=" * 60)
    print("✅ 策略适配器加载成功")
