"""
交易服务模块

负责实际的交易执行、持仓管理和订单管理。
适配新架构的服务容器和事件总线模式。
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import asyncio
import pandas as pd
from dataclasses import dataclass, field

from .base_service import BaseService
from ..events import EventBus, StockSelectedEvent, TradeExecutedEvent, PositionUpdatedEvent
from ..containers import ServiceContainer
from ..logger import LogManager

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """交易记录数据类"""
    trade_id: str
    timestamp: datetime
    stock_code: str
    stock_name: str
    action: str  # 'BUY' or 'SELL'
    price: float
    quantity: int
    amount: float
    commission: float
    status: str = 'pending'  # 'pending', 'executed', 'cancelled'
    notes: str = ''


@dataclass
class Position:
    """持仓数据类"""
    stock_code: str
    stock_name: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    profit_loss: float
    profit_loss_pct: float
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class Portfolio:
    """投资组合数据类"""
    total_assets: float
    available_cash: float
    market_value: float
    total_profit_loss: float
    total_profit_loss_pct: float
    positions: List[Position] = field(default_factory=list)
    trade_history: List[TradeRecord] = field(default_factory=list)


class TradingService(BaseService):
    """
    交易服务

    负责：
    1. 交易执行（买入、卖出、撤单）
    2. 持仓管理
    3. 订单队列管理
    4. 投资组合管理
    5. 交易记录管理
    """

    def __init__(self,
                 event_bus: EventBus,
                 config: Optional[Dict[str, Any]] = None,
                 **kwargs):
        """
        初始化交易服务

        Args:
            event_bus: 事件总线
            config: 服务配置
            **kwargs: 其他参数
        """
        super().__init__(event_bus=event_bus, **kwargs)
        self._config = config or {}

        # 交易状态
        self._current_stock_code: Optional[str] = None
        self._current_stock_name: Optional[str] = None

        # 投资组合
        self._portfolio = Portfolio(
            total_assets=100000.0,  # 默认10万初始资金
            available_cash=100000.0,
            market_value=0.0,
            total_profit_loss=0.0,
            total_profit_loss_pct=0.0
        )

        # 订单队列
        self._pending_orders: List[TradeRecord] = []
        self._order_counter = 0

        # 交易配置
        self._trading_config = {
            'commission_rate': 0.0003,  # 手续费率
            'min_commission': 5.0,      # 最低手续费
            'slippage': 0.0001,         # 滑点
            'max_position_pct': 0.3,    # 单只股票最大持仓比例
        }

        # 风险控制
        self._risk_limits = {
            'max_daily_loss': 0.05,     # 最大日损失5%
            'max_single_trade': 0.1,    # 单次交易最大10%
            'max_positions': 10,        # 最大持仓数量
        }

    def _do_initialize(self) -> None:
        """初始化交易服务"""
        try:
            # 订阅股票选择事件
            self.event_bus.subscribe(StockSelectedEvent, self._on_stock_selected)

            # 加载交易配置
            self._load_trading_config()

            # 加载持仓数据
            self._load_portfolio()

            logger.info("Trading service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize trading service: {e}")
            raise

    def _on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件"""
        self._current_stock_code = event.stock_code
        self._current_stock_name = event.stock_name
        logger.debug(f"Trading service: stock selected {event.stock_code}")

    async def execute_buy_order(self,
                                stock_code: str,
                                stock_name: str,
                                quantity: int,
                                price: Optional[float] = None) -> TradeRecord:
        """
        执行买入订单

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            quantity: 买入数量
            price: 买入价格（None为市价）

        Returns:
            交易记录
        """
        try:
            # 获取当前价格
            if price is None:
                price = await self._get_current_price(stock_code)
                if price is None:
                    raise ValueError(f"无法获取股票 {stock_code} 的当前价格")

            # 风险检查
            self._check_buy_risk(stock_code, quantity, price)

            # 创建交易记录
            trade_record = self._create_trade_record(
                stock_code, stock_name, 'BUY', quantity, price)

            # 模拟交易执行（实际环境中这里会调用券商API）
            success = await self._simulate_trade_execution(trade_record)

            if success:
                # 更新持仓
                self._update_position_after_buy(trade_record)

                # 更新资金
                self._update_cash_after_trade(trade_record)

                # 添加到交易历史
                self._portfolio.trade_history.append(trade_record)

                # 发布交易事件
                self.event_bus.publish(TradeExecutedEvent(
                    source="TradingService",
                    trade_record=trade_record
                ))

                logger.info(f"买入订单执行成功: {stock_code} {quantity}股 @{price:.2f}")
            else:
                trade_record.status = 'failed'
                logger.error(f"买入订单执行失败: {stock_code}")

            return trade_record

        except Exception as e:
            logger.error(f"Execute buy order failed: {e}")
            raise

    async def execute_sell_order(self,
                                 stock_code: str,
                                 stock_name: str,
                                 quantity: int,
                                 price: Optional[float] = None) -> TradeRecord:
        """
        执行卖出订单

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            quantity: 卖出数量
            price: 卖出价格（None为市价）

        Returns:
            交易记录
        """
        try:
            # 获取当前价格
            if price is None:
                price = await self._get_current_price(stock_code)
                if price is None:
                    raise ValueError(f"无法获取股票 {stock_code} 的当前价格")

            # 检查持仓
            position = self.get_position(stock_code)
            if not position or position.quantity < quantity:
                raise ValueError(f"持仓不足，无法卖出 {quantity} 股 {stock_code}")

            # 创建交易记录
            trade_record = self._create_trade_record(
                stock_code, stock_name, 'SELL', quantity, price)

            # 模拟交易执行
            success = await self._simulate_trade_execution(trade_record)

            if success:
                # 更新持仓
                self._update_position_after_sell(trade_record)

                # 更新资金
                self._update_cash_after_trade(trade_record)

                # 添加到交易历史
                self._portfolio.trade_history.append(trade_record)

                # 发布交易事件
                self.event_bus.publish(TradeExecutedEvent(
                    source="TradingService",
                    trade_record=trade_record
                ))

                logger.info(f"卖出订单执行成功: {stock_code} {quantity}股 @{price:.2f}")
            else:
                trade_record.status = 'failed'
                logger.error(f"卖出订单执行失败: {stock_code}")

            return trade_record

        except Exception as e:
            logger.error(f"Execute sell order failed: {e}")
            raise

    def get_portfolio(self) -> Portfolio:
        """获取投资组合信息"""
        # 更新市值和盈亏
        self._update_portfolio_values()
        return self._portfolio

    def get_position(self, stock_code: str) -> Optional[Position]:
        """获取指定股票的持仓信息"""
        for position in self._portfolio.positions:
            if position.stock_code == stock_code:
                return position
        return None

    def get_available_cash(self) -> float:
        """获取可用资金"""
        return self._portfolio.available_cash

    def get_trade_history(self, limit: int = 100) -> List[TradeRecord]:
        """获取交易历史"""
        return self._portfolio.trade_history[-limit:]

    def _create_trade_record(self,
                             stock_code: str,
                             stock_name: str,
                             action: str,
                             quantity: int,
                             price: float) -> TradeRecord:
        """创建交易记录"""
        self._order_counter += 1
        trade_id = f"T{datetime.now().strftime('%Y%m%d')}_{self._order_counter:06d}"

        amount = quantity * price
        commission = max(amount * self._trading_config['commission_rate'],
                         self._trading_config['min_commission'])

        return TradeRecord(
            trade_id=trade_id,
            timestamp=datetime.now(),
            stock_code=stock_code,
            stock_name=stock_name,
            action=action,
            price=price,
            quantity=quantity,
            amount=amount,
            commission=commission,
            status='pending'
        )

    async def _get_current_price(self, stock_code: str) -> Optional[float]:
        """获取当前股票价格"""
        try:
            # 这里应该调用数据服务获取实时价格
            # 暂时使用模拟价格
            import random
            base_price = 10.0 + hash(stock_code) % 100
            fluctuation = random.uniform(-0.05, 0.05)
            return base_price * (1 + fluctuation)

        except Exception as e:
            logger.error(f"Failed to get current price for {stock_code}: {e}")
            return None

    async def _simulate_trade_execution(self, trade_record: TradeRecord) -> bool:
        """模拟交易执行"""
        try:
            # 模拟网络延迟
            await asyncio.sleep(0.1)

            # 模拟成功率（95%）
            import random
            success = random.random() > 0.05

            if success:
                trade_record.status = 'executed'
                return True
            else:
                trade_record.status = 'failed'
                return False

        except Exception as e:
            logger.error(f"Trade execution simulation failed: {e}")
            return False

    def _check_buy_risk(self, stock_code: str, quantity: int, price: float) -> None:
        """检查买入风险"""
        # 检查资金是否充足
        total_cost = quantity * price * (1 + self._trading_config['commission_rate'])
        if total_cost > self._portfolio.available_cash:
            raise ValueError(f"资金不足，需要 {total_cost:.2f}，可用 {self._portfolio.available_cash:.2f}")

        # 检查单次交易限制
        max_single_trade = self._portfolio.total_assets * self._risk_limits['max_single_trade']
        if total_cost > max_single_trade:
            raise ValueError(f"单次交易金额超限，最大允许 {max_single_trade:.2f}")

        # 检查持仓数量限制
        if len(self._portfolio.positions) >= self._risk_limits['max_positions']:
            existing_position = self.get_position(stock_code)
            if not existing_position:
                raise ValueError(f"持仓数量超限，最大允许 {self._risk_limits['max_positions']} 只")

    def _update_position_after_buy(self, trade_record: TradeRecord) -> None:
        """买入后更新持仓"""
        position = self.get_position(trade_record.stock_code)

        if position:
            # 更新现有持仓
            total_quantity = position.quantity + trade_record.quantity
            total_cost = (position.quantity * position.avg_cost +
                          trade_record.quantity * trade_record.price)
            position.avg_cost = total_cost / total_quantity
            position.quantity = total_quantity
        else:
            # 创建新持仓
            new_position = Position(
                stock_code=trade_record.stock_code,
                stock_name=trade_record.stock_name,
                quantity=trade_record.quantity,
                avg_cost=trade_record.price,
                current_price=trade_record.price,
                market_value=trade_record.amount,
                profit_loss=0.0,
                profit_loss_pct=0.0
            )
            self._portfolio.positions.append(new_position)

    def _update_position_after_sell(self, trade_record: TradeRecord) -> None:
        """卖出后更新持仓"""
        position = self.get_position(trade_record.stock_code)
        if position:
            position.quantity -= trade_record.quantity
            if position.quantity <= 0:
                # 清仓，移除持仓
                self._portfolio.positions.remove(position)

    def _update_cash_after_trade(self, trade_record: TradeRecord) -> None:
        """交易后更新现金"""
        if trade_record.action == 'BUY':
            self._portfolio.available_cash -= (trade_record.amount + trade_record.commission)
        else:  # SELL
            self._portfolio.available_cash += (trade_record.amount - trade_record.commission)

    def _update_portfolio_values(self) -> None:
        """更新投资组合市值和盈亏"""
        total_market_value = 0.0

        for position in self._portfolio.positions:
            # 这里应该获取实时价格，暂时使用平均成本
            position.current_price = position.avg_cost  # 简化处理
            position.market_value = position.quantity * position.current_price
            position.profit_loss = position.market_value - (position.quantity * position.avg_cost)
            position.profit_loss_pct = (position.profit_loss / (position.quantity * position.avg_cost)) * 100

            total_market_value += position.market_value

        self._portfolio.market_value = total_market_value
        self._portfolio.total_assets = self._portfolio.available_cash + total_market_value

        # 计算总盈亏（简化计算）
        initial_assets = 100000.0  # 初始资金
        self._portfolio.total_profit_loss = self._portfolio.total_assets - initial_assets
        self._portfolio.total_profit_loss_pct = (self._portfolio.total_profit_loss / initial_assets) * 100

    def _load_trading_config(self) -> None:
        """加载交易配置"""
        # 从配置文件或数据库加载交易参数
        # 这里使用默认配置
        pass

    def _load_portfolio(self) -> None:
        """加载持仓数据"""
        # 从数据库或文件加载持仓数据
        # 这里使用空的初始状态
        pass

    def _do_dispose(self) -> None:
        """清理资源"""
        try:
            # 取消订阅事件
            self.event_bus.unsubscribe(StockSelectedEvent, self._on_stock_selected)

            # 保存持仓数据
            self._save_portfolio()

            super()._do_dispose()
            logger.info("Trading service disposed")

        except Exception as e:
            logger.error(f"Failed to dispose trading service: {e}")

    def _save_portfolio(self) -> None:
        """保存持仓数据"""
        # 保存到数据库或文件
        # 这里暂时跳过
        pass
