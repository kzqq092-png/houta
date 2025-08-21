"""
交易服务模块

负责实际的交易执行、持仓管理和订单管理。
支持多策略插件并行运行、信号聚合和风险控制。
"""

import logging
from typing import Dict, Any, List, Optional, Union, Set, Callable
from datetime import datetime, timedelta
import asyncio
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict

from .base_service import BaseService
from ..events import EventBus, StockSelectedEvent, TradeExecutedEvent, PositionUpdatedEvent
from ..containers import ServiceContainer
from ..logger import LogManager
from ..strategy_extensions import (
    IStrategyPlugin, Signal, TradeResult, Position, PerformanceMetrics,
    StrategyContext, SignalType, TradeAction, TradeStatus
)
from ..strategy_events import (
    StrategyStartedEvent, StrategyStoppedEvent, SignalGeneratedEvent,
    TradeExecutedEvent as StrategyTradeEvent, PositionUpdatedEvent as StrategyPositionEvent,
    StrategyErrorEvent
)

logger = logging.getLogger(__name__)


class StrategyState(Enum):
    """策略状态枚举"""
    CREATED = "created"
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class SignalPriority(Enum):
    """信号优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class StrategyInstance:
    """策略实例"""
    strategy_id: str
    plugin: IStrategyPlugin
    context: StrategyContext
    parameters: Dict[str, Any]
    state: StrategyState = StrategyState.CREATED
    last_signal_time: Optional[datetime] = None
    performance: Optional[PerformanceMetrics] = None
    error_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class EnhancedSignal:
    """增强信号（包含优先级和来源信息）"""
    signal: Signal
    strategy_id: str
    priority: SignalPriority = SignalPriority.MEDIUM
    received_at: datetime = field(default_factory=datetime.now)
    processed: bool = False


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
    strategy_id: Optional[str] = None
    signal_id: Optional[str] = None
    status: str = 'pending'  # 'pending', 'executed', 'cancelled'
    notes: str = ''
    order_type: Optional[str] = None  # 新增：订单类型


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
    1. 策略插件管理和生命周期
    2. 信号聚合和冲突解决
    3. 交易执行（买入、卖出、撤单）
    4. 持仓管理和风险控制
    5. 订单队列管理
    6. 投资组合管理
    7. 性能监控和统计
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

        # 策略管理
        self._strategy_instances: Dict[str, StrategyInstance] = {}
        self._strategy_signals: Dict[str, List[EnhancedSignal]] = defaultdict(list)
        self._signal_processors: Dict[str, Callable] = {}

        # 信号聚合
        self._pending_signals: List[EnhancedSignal] = []
        self._signal_conflicts: List[List[EnhancedSignal]] = []
        self._signal_filters: List[Callable[[EnhancedSignal], bool]] = []

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

        # 订单管理
        self._pending_orders: List[TradeRecord] = []
        self._order_counter = 0
        self._order_queue = asyncio.Queue()

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
            'max_strategies': 5,        # 最大策略数量
        }

        # 性能监控
        self._performance_stats = {
            'total_signals': 0,
            'processed_signals': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'strategy_errors': 0,
        }

        # 异步任务
        self._signal_processor_task: Optional[asyncio.Task] = None
        self._order_processor_task: Optional[asyncio.Task] = None
        self._running = False

    def _do_initialize(self) -> None:
        """初始化交易服务"""
        try:
            # 订阅股票选择事件
            self.event_bus.subscribe(StockSelectedEvent, self._on_stock_selected)

            # 加载交易配置
            self._load_trading_config()

            # 加载持仓数据
            self._load_portfolio()

            # 启动异步处理任务
            self._start_async_tasks()

            logger.info("Trading service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize trading service: {e}")
            raise

    def _start_async_tasks(self) -> None:
        """
        启动异步处理任务

        智能检测运行环境并选择最佳模式：
        - 异步模式：支持并发处理，性能更好，适合高频交易
        - 同步模式：简单可靠，兼容性好，适合一般交易场景
        """
        self._running = True

        # 检查是否有运行的事件循环
        try:
            loop = asyncio.get_running_loop()
            # 异步模式：启动后台任务处理信号和订单
            self._signal_processor_task = asyncio.create_task(self._process_signals_loop())
            self._order_processor_task = asyncio.create_task(self._process_orders_loop())
            self._async_mode = True

            logger.info("🚀 交易服务已启动 - 异步模式")
            logger.info("📈 异步模式优势：并发处理、高性能、实时响应")

        except RuntimeError:
            # 同步模式：直接处理，无后台任务
            self._signal_processor_task = None
            self._order_processor_task = None
            self._async_mode = False

            logger.info("🚀 交易服务已启动 - 同步模式")
            logger.info("🔒 同步模式优势：简单可靠、兼容性好、易于调试")
            logger.info("💡 提示：在异步环境中运行可获得更好性能")

    async def _process_signals_loop(self) -> None:
        """信号处理循环"""
        while self._running:
            try:
                if self._pending_signals:
                    # 处理待处理信号
                    signals_to_process = self._pending_signals.copy()
                    self._pending_signals.clear()

                    for enhanced_signal in signals_to_process:
                        await self._process_single_signal(enhanced_signal)

                await asyncio.sleep(0.1)  # 避免CPU占用过高

            except Exception as e:
                logger.error(f"Signal processing loop error: {e}")
                await asyncio.sleep(1)

    async def _process_orders_loop(self) -> None:
        """订单处理循环"""
        while self._running:
            try:
                # 从订单队列获取订单
                order = await asyncio.wait_for(self._order_queue.get(), timeout=1.0)
                await self._execute_order(order)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Order processing loop error: {e}")
                await asyncio.sleep(1)

    # 策略管理方法
    def register_strategy(self,
                          strategy_id: str,
                          plugin: IStrategyPlugin,
                          context: StrategyContext,
                          parameters: Dict[str, Any]) -> bool:
        """注册策略插件"""
        try:
            if strategy_id in self._strategy_instances:
                logger.warning(f"Strategy {strategy_id} already registered")
                return False

            if len(self._strategy_instances) >= self._risk_limits['max_strategies']:
                logger.error(f"Maximum strategies limit reached: {self._risk_limits['max_strategies']}")
                return False

            # 创建策略实例
            strategy_instance = StrategyInstance(
                strategy_id=strategy_id,
                plugin=plugin,
                context=context,
                parameters=parameters
            )

            # 初始化策略
            if plugin.initialize_strategy(context, parameters):
                strategy_instance.state = StrategyState.INITIALIZED
                self._strategy_instances[strategy_id] = strategy_instance

                logger.info(f"Strategy registered: {strategy_id}")

                # 发布策略启动事件
                self.event_bus.publish(StrategyStartedEvent(
                    timestamp=datetime.now(),
                    strategy_id=strategy_id,
                    context=context,
                    parameters=parameters
                ))

                return True
            else:
                logger.error(f"Failed to initialize strategy: {strategy_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to register strategy {strategy_id}: {e}")
            return False

    def unregister_strategy(self, strategy_id: str) -> bool:
        """注销策略插件"""
        try:
            if strategy_id not in self._strategy_instances:
                logger.warning(f"Strategy {strategy_id} not found")
                return False

            strategy_instance = self._strategy_instances[strategy_id]

            # 停止策略
            strategy_instance.state = StrategyState.STOPPED

            # 清理策略相关数据
            if strategy_id in self._strategy_signals:
                del self._strategy_signals[strategy_id]

            # 移除策略实例
            del self._strategy_instances[strategy_id]

            logger.info(f"Strategy unregistered: {strategy_id}")

            # 发布策略停止事件
            self.event_bus.publish(StrategyStoppedEvent(
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                reason="Manual unregistration"
            ))

            return True

        except Exception as e:
            logger.error(f"Failed to unregister strategy {strategy_id}: {e}")
            return False

    def start_strategy(self, strategy_id: str) -> bool:
        """启动策略"""
        try:
            if strategy_id not in self._strategy_instances:
                logger.error(f"Strategy {strategy_id} not found")
                return False

            strategy_instance = self._strategy_instances[strategy_id]

            if strategy_instance.state != StrategyState.INITIALIZED:
                logger.error(f"Strategy {strategy_id} not in initialized state")
                return False

            strategy_instance.state = StrategyState.RUNNING
            logger.info(f"Strategy started: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start strategy {strategy_id}: {e}")
            return False

    def stop_strategy(self, strategy_id: str) -> bool:
        """停止策略"""
        try:
            if strategy_id not in self._strategy_instances:
                logger.error(f"Strategy {strategy_id} not found")
                return False

            strategy_instance = self._strategy_instances[strategy_id]
            strategy_instance.state = StrategyState.STOPPED

            logger.info(f"Strategy stopped: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop strategy {strategy_id}: {e}")
            return False

    def get_strategy_status(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取策略状态"""
        if strategy_id not in self._strategy_instances:
            return None

        strategy_instance = self._strategy_instances[strategy_id]
        return {
            'strategy_id': strategy_id,
            'state': strategy_instance.state.value,
            'last_signal_time': strategy_instance.last_signal_time,
            'error_count': strategy_instance.error_count,
            'created_at': strategy_instance.created_at,
            'performance': strategy_instance.performance
        }

    # 信号处理方法
    async def process_signal(self,
                             strategy_id: str,
                             signal: Signal,
                             priority: SignalPriority = SignalPriority.MEDIUM) -> bool:
        """处理策略信号"""
        try:
            if strategy_id not in self._strategy_instances:
                logger.error(f"Strategy {strategy_id} not found")
                return False

            strategy_instance = self._strategy_instances[strategy_id]

            if strategy_instance.state != StrategyState.RUNNING:
                logger.warning(f"Strategy {strategy_id} not running, ignoring signal")
                return False

            # 创建增强信号
            enhanced_signal = EnhancedSignal(
                signal=signal,
                strategy_id=strategy_id,
                priority=priority
            )

            # 添加到待处理队列
            self._pending_signals.append(enhanced_signal)
            self._performance_stats['total_signals'] += 1

            # 更新策略最后信号时间
            strategy_instance.last_signal_time = datetime.now()

            logger.debug(f"Signal received from strategy {strategy_id}: {signal.signal_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to process signal from strategy {strategy_id}: {e}")
            return False

    async def _process_single_signal(self, enhanced_signal: EnhancedSignal) -> None:
        """处理单个信号"""
        try:
            # 应用信号过滤器
            if not self._apply_signal_filters(enhanced_signal):
                logger.debug(f"Signal filtered out: {enhanced_signal.signal.symbol}")
                return

            # 检查信号冲突
            conflicts = self._detect_signal_conflicts(enhanced_signal)
            if conflicts:
                resolved_signal = self._resolve_signal_conflicts([enhanced_signal] + conflicts)
                if resolved_signal != enhanced_signal:
                    logger.debug(f"Signal conflict resolved, using different signal")
                    enhanced_signal = resolved_signal

            # 执行信号
            await self._execute_signal(enhanced_signal)
            enhanced_signal.processed = True
            self._performance_stats['processed_signals'] += 1

            # 发布信号生成事件
            self.event_bus.publish(SignalGeneratedEvent(
                timestamp=datetime.now(),
                strategy_id=enhanced_signal.strategy_id,
                signal=enhanced_signal.signal
            ))

        except Exception as e:
            logger.error(f"Failed to process signal: {e}")
            # 记录策略错误
            if enhanced_signal.strategy_id in self._strategy_instances:
                self._strategy_instances[enhanced_signal.strategy_id].error_count += 1
                self._performance_stats['strategy_errors'] += 1

    def _apply_signal_filters(self, enhanced_signal: EnhancedSignal) -> bool:
        """应用信号过滤器"""
        for filter_func in self._signal_filters:
            if not filter_func(enhanced_signal):
                return False
        return True

    def _detect_signal_conflicts(self, enhanced_signal: EnhancedSignal) -> List[EnhancedSignal]:
        """检测信号冲突"""
        conflicts = []
        for pending_signal in self._pending_signals:
            if (pending_signal != enhanced_signal and
                pending_signal.signal.symbol == enhanced_signal.signal.symbol and
                    not pending_signal.processed):
                conflicts.append(pending_signal)
        return conflicts

    def _resolve_signal_conflicts(self, conflicting_signals: List[EnhancedSignal]) -> EnhancedSignal:
        """解决信号冲突"""
        # 按优先级排序，选择优先级最高的信号
        sorted_signals = sorted(conflicting_signals, key=lambda s: s.priority.value, reverse=True)
        return sorted_signals[0]

    async def _execute_signal(self, enhanced_signal: EnhancedSignal) -> None:
        """执行信号"""
        try:
            signal = enhanced_signal.signal
            strategy_id = enhanced_signal.strategy_id

            # 获取策略实例
            strategy_instance = self._strategy_instances[strategy_id]

            # 执行交易
            trade_result = strategy_instance.plugin.execute_trade(signal, strategy_instance.context)

            # 创建订单并加入队列
            if trade_result.status != TradeStatus.ERROR:
                trade_record = self._create_trade_record_from_result(trade_result, strategy_id, signal)
                await self._order_queue.put(trade_record)

        except Exception as e:
            logger.error(f"Failed to execute signal: {e}")

    def _create_trade_record_from_result(self,
                                         trade_result: TradeResult,
                                         strategy_id: str,
                                         signal: Signal) -> TradeRecord:
        """从交易结果创建交易记录"""
        self._order_counter += 1

        action = 'BUY' if trade_result.action in [TradeAction.OPEN_LONG] else 'SELL'

        return TradeRecord(
            trade_id=trade_result.trade_id,
            timestamp=trade_result.timestamp,
            stock_code=trade_result.symbol,
            stock_name=trade_result.symbol,  # 简化处理
            action=action,
            price=trade_result.price,
            quantity=trade_result.quantity,
            amount=trade_result.price * trade_result.quantity,
            commission=trade_result.commission,
            strategy_id=strategy_id,
            signal_id=getattr(signal, 'signal_id', None),
            status='pending'
        )

    # 原有的交易执行方法保持不变，但增加策略关联
    async def execute_buy_order(self,
                                stock_code: str,
                                stock_name: str,
                                quantity: int,
                                price: Optional[float] = None,
                                strategy_id: Optional[str] = None) -> TradeRecord:
        """
        执行买入订单

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            quantity: 买入数量
            price: 买入价格（None为市价）
            strategy_id: 关联的策略ID

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
                stock_code, stock_name, 'BUY', quantity, price, strategy_id)

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

                self._performance_stats['successful_trades'] += 1
                logger.info(f"买入订单执行成功: {stock_code} {quantity}股 @{price:.2f}")
            else:
                trade_record.status = 'failed'
                self._performance_stats['failed_trades'] += 1
                logger.error(f"买入订单执行失败: {stock_code}")

            return trade_record

        except Exception as e:
            logger.error(f"Execute buy order failed: {e}")
            raise

    async def execute_sell_order(self,
                                 stock_code: str,
                                 stock_name: str,
                                 quantity: int,
                                 price: Optional[float] = None,
                                 strategy_id: Optional[str] = None) -> TradeRecord:
        """
        执行卖出订单

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            quantity: 卖出数量
            price: 卖出价格（None为市价）
            strategy_id: 关联的策略ID

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
                stock_code, stock_name, 'SELL', quantity, price, strategy_id)

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

                self._performance_stats['successful_trades'] += 1
                logger.info(f"卖出订单执行成功: {stock_code} {quantity}股 @{price:.2f}")
            else:
                trade_record.status = 'failed'
                self._performance_stats['failed_trades'] += 1
                logger.error(f"卖出订单执行失败: {stock_code}")

            return trade_record

        except Exception as e:
            logger.error(f"Execute sell order failed: {e}")
            raise

    async def _execute_order(self, trade_record: TradeRecord) -> None:
        """执行订单"""
        try:
            if trade_record.action == 'BUY':
                await self.execute_buy_order(
                    trade_record.stock_code,
                    trade_record.stock_name,
                    trade_record.quantity,
                    trade_record.price,
                    trade_record.strategy_id
                )
            else:  # SELL
                await self.execute_sell_order(
                    trade_record.stock_code,
                    trade_record.stock_name,
                    trade_record.quantity,
                    trade_record.price,
                    trade_record.strategy_id
                )

        except Exception as e:
            logger.error(f"Failed to execute order {trade_record.trade_id}: {e}")

    # 其他方法保持不变，但添加策略ID支持
    def get_portfolio(self) -> Portfolio:
        """获取投资组合信息"""
        # 更新市值和盈亏
        self._update_portfolio_values()
        return self._portfolio

    def get_position(self, stock_code: str) -> Optional[Position]:
        """获取指定股票的持仓信息"""
        for position in self._portfolio.positions:
            if position.symbol == stock_code:
                return position
        return None

    def get_available_cash(self) -> float:
        """获取可用资金"""
        return self._portfolio.available_cash

    def get_trade_history(self, limit: int = 100, strategy_id: Optional[str] = None) -> List[TradeRecord]:
        """获取交易历史"""
        history = self._portfolio.trade_history

        if strategy_id:
            history = [trade for trade in history if trade.strategy_id == strategy_id]

        return history[-limit:]

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            **self._performance_stats,
            'active_strategies': len([s for s in self._strategy_instances.values()
                                      if s.state == StrategyState.RUNNING]),
            'total_strategies': len(self._strategy_instances),
            'pending_signals': len(self._pending_signals),
            'pending_orders': self._order_queue.qsize(),
        }

    def add_signal_filter(self, filter_func: Callable[[EnhancedSignal], bool]) -> None:
        """添加信号过滤器"""
        self._signal_filters.append(filter_func)

    def remove_signal_filter(self, filter_func: Callable[[EnhancedSignal], bool]) -> None:
        """移除信号过滤器"""
        if filter_func in self._signal_filters:
            self._signal_filters.remove(filter_func)

    def _create_trade_record(self,
                             stock_code: str,
                             stock_name: str,
                             action: str,
                             quantity: int,
                             price: float,
                             strategy_id: Optional[str] = None) -> TradeRecord:
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
            strategy_id=strategy_id,
            status='pending'
        )

    def _on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件"""
        self._current_stock_code = event.stock_code
        self._current_stock_name = event.stock_name
        logger.debug(f"Trading service: stock selected {event.stock_code}")

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
            total_cost = (position.quantity * position.avg_price +
                          trade_record.quantity * trade_record.price)
            position.avg_price = total_cost / total_quantity
            position.quantity = total_quantity
        else:
            # 创建新持仓
            new_position = Position(
                symbol=trade_record.stock_code,
                quantity=trade_record.quantity,
                avg_price=trade_record.price,
                current_price=trade_record.price,
                market_value=trade_record.amount,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                timestamp=trade_record.timestamp
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
            position.current_price = position.avg_price  # 简化处理
            position.market_value = position.quantity * position.current_price
            position.unrealized_pnl = position.market_value - (position.quantity * position.avg_price)

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
            # 停止异步任务
            self._running = False

            if self._signal_processor_task:
                self._signal_processor_task.cancel()

            if self._order_processor_task:
                self._order_processor_task.cancel()

            # 停止所有策略
            for strategy_id in list(self._strategy_instances.keys()):
                self.stop_strategy(strategy_id)

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

    # ========== 从TradingManager合并的订单管理功能 ==========

    def place_order(self, stock_code: str, side: str, quantity: int,
                    order_type: str = 'MARKET',
                    price: Optional[float] = None,
                    strategy_id: Optional[str] = None) -> Optional[str]:
        """
        下单 - 合并自TradingManager

        Args:
            stock_code: 股票代码
            side: 买卖方向 ('BUY' or 'SELL')
            quantity: 数量
            order_type: 订单类型 ('MARKET', 'LIMIT', 'STOP')
            price: 价格（限价单时必填）
            strategy_id: 关联的策略ID

        Returns:
            订单ID，如果下单失败返回None
        """
        try:
            # 获取股票信息
            stock_name = self._get_stock_name(stock_code)
            if not stock_name:
                logger.error(f"Stock {stock_code} not found")
                return None

            # 生成订单ID
            order_id = f"ORD{self._order_counter:06d}"
            self._order_counter += 1

            # 创建交易记录
            trade_record = TradeRecord(
                trade_id=order_id,
                stock_code=stock_code,
                stock_name=stock_name,
                action=side,
                quantity=quantity,
                price=price,
                amount=0.0,  # 将在执行时计算
                commission=0.0,  # 将在执行时计算
                timestamp=datetime.now(),
                status='pending',
                strategy_id=strategy_id,
                order_type=order_type
            )

            # 风险检查
            if not self._order_risk_check(trade_record):
                trade_record.status = 'rejected'
                trade_record.notes = "风险检查未通过"
                self._pending_orders.append(trade_record)
                return None

            # 保存订单
            self._pending_orders.append(trade_record)

            # 异步执行订单
            asyncio.create_task(self._process_order(trade_record))

            logger.info(f"Order placed: {order_id} - {side} {quantity} {stock_code}")
            return order_id

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None

    async def _process_order(self, trade_record: TradeRecord):
        """处理订单"""
        try:
            if trade_record.action == 'BUY':
                result = await self.execute_buy_order(
                    trade_record.stock_code,
                    trade_record.stock_name,
                    trade_record.quantity,
                    trade_record.price,
                    trade_record.strategy_id
                )
            else:  # SELL
                result = await self.execute_sell_order(
                    trade_record.stock_code,
                    trade_record.stock_name,
                    trade_record.quantity,
                    trade_record.price,
                    trade_record.strategy_id
                )

            # 更新订单状态
            if result and result.status == 'executed':
                trade_record.status = 'filled'
                trade_record.amount = result.amount
                trade_record.commission = result.commission
            else:
                trade_record.status = 'failed'

        except Exception as e:
            logger.error(f"Order processing failed: {e}")
            trade_record.status = 'failed'
            trade_record.notes = str(e)

    def cancel_order(self, order_id: str) -> bool:
        """
        取消订单

        Args:
            order_id: 订单ID

        Returns:
            是否取消成功
        """
        try:
            for order in self._pending_orders:
                if order.trade_id == order_id:
                    if order.status == 'pending':
                        order.status = 'cancelled'
                        order.notes = "用户取消"
                        logger.info(f"Order cancelled: {order_id}")
                        return True
                    else:
                        logger.error(f"Order {order_id} cannot be cancelled, status: {order.status}")
                        return False

            logger.error(f"Order {order_id} not found")
            return False

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_orders(self, status: Optional[str] = None, days: int = 30) -> List[TradeRecord]:
        """
        获取订单列表

        Args:
            status: 订单状态筛选
            days: 查询天数

        Returns:
            订单列表
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)

            orders = [o for o in self._pending_orders if o.timestamp >= cutoff_date]

            if status:
                orders = [o for o in orders if o.status == status]

            # 按创建时间倒序排列
            orders.sort(key=lambda x: x.timestamp, reverse=True)
            return orders

        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []

    def get_order(self, order_id: str) -> Optional[TradeRecord]:
        """
        获取订单详情

        Args:
            order_id: 订单ID

        Returns:
            订单信息
        """
        for order in self._pending_orders:
            if order.trade_id == order_id:
                return order
        return None

    def get_trade_records(self, stock_code: Optional[str] = None, days: int = 30) -> List[TradeRecord]:
        """
        获取交易记录

        Args:
            stock_code: 股票代码筛选
            days: 查询天数

        Returns:
            交易记录列表
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)

            records = [r for r in self._portfolio.trade_history if r.timestamp >= cutoff_date]

            if stock_code:
                records = [r for r in records if r.stock_code == stock_code]

            # 按交易时间倒序排列
            records.sort(key=lambda x: x.timestamp, reverse=True)
            return records

        except Exception as e:
            logger.error(f"Failed to get trade records: {e}")
            return []

    def get_trading_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        获取交易统计

        Args:
            days: 统计天数

        Returns:
            交易统计信息
        """
        try:
            records = self.get_trade_records(days=days)

            if not records:
                return {
                    'total_trades': 0,
                    'total_volume': 0.0,
                    'total_commission': 0.0,
                    'buy_trades': 0,
                    'sell_trades': 0,
                    'most_traded_stock': None,
                    'average_trade_size': 0.0,
                    'commission_rate': 0.0
                }

            total_trades = len(records)
            total_volume = sum(r.amount for r in records)
            total_commission = sum(r.commission for r in records)
            buy_trades = len([r for r in records if r.action == 'BUY'])
            sell_trades = len([r for r in records if r.action == 'SELL'])

            # 统计最常交易的股票
            stock_counts = {}
            for record in records:
                stock_counts[record.stock_code] = stock_counts.get(record.stock_code, 0) + 1

            most_traded_stock = max(stock_counts.items(), key=lambda x: x[1])[0] if stock_counts else None

            return {
                'total_trades': total_trades,
                'total_volume': float(total_volume),
                'total_commission': float(total_commission),
                'buy_trades': buy_trades,
                'sell_trades': sell_trades,
                'most_traded_stock': most_traded_stock,
                'average_trade_size': float(total_volume / total_trades) if total_trades > 0 else 0,
                'commission_rate': float(total_commission / total_volume) * 100 if total_volume > 0 else 0
            }

        except Exception as e:
            logger.error(f"Failed to get trading statistics: {e}")
            return {}

    def _order_risk_check(self, trade_record: TradeRecord) -> bool:
        """订单风险检查"""
        try:
            # 检查数量是否合理（至少100股，且为100的倍数）
            if trade_record.quantity < 100 or trade_record.quantity % 100 != 0:
                logger.warning(f"Risk check failed: invalid quantity {trade_record.quantity}")
                return False

            # 检查价格是否合理（限价单）
            if trade_record.order_type == 'LIMIT' and trade_record.price:
                # 这里可以添加价格合理性检查
                pass

            # 检查资金是否充足
            if trade_record.action == 'BUY':
                estimated_cost = trade_record.quantity * (trade_record.price or 0) * 1.001  # 加上手续费估算
                if estimated_cost > self._portfolio.available_cash:
                    logger.warning(f"Risk check failed: insufficient cash")
                    return False

            # 检查持仓是否充足
            elif trade_record.action == 'SELL':
                position = self.get_position(trade_record.stock_code)
                if not position or position.quantity < trade_record.quantity:
                    logger.warning(f"Risk check failed: insufficient position")
                    return False

            return True

        except Exception as e:
            logger.error(f"Risk check error: {e}")
            return False

    def _get_stock_name(self, stock_code: str) -> Optional[str]:
        """获取股票名称"""
        try:
            # 通过统一数据管理器获取股票信息
            from .unified_data_manager import get_unified_data_manager
            data_manager = get_unified_data_manager()

            if data_manager:
                stock_list = data_manager.get_stock_list()
                if stock_list is not None and not stock_list.empty:
                    stock_info = stock_list[stock_list['code'] == stock_code]
                    if not stock_info.empty:
                        return stock_info.iloc[0]['name']

            return stock_code  # 降级返回代码

        except Exception as e:
            logger.error(f"Failed to get stock name for {stock_code}: {e}")
            return stock_code

    def set_commission_rate(self, rate: float) -> None:
        """设置手续费率"""
        self._trading_config['commission_rate'] = rate
        logger.info(f"Commission rate set to {rate:.4%}")

    def set_min_commission(self, amount: float) -> None:
        """设置最低手续费"""
        self._trading_config['min_commission'] = amount
        logger.info(f"Minimum commission set to {amount}")

    def clear_history(self) -> None:
        """清除历史记录"""
        # 只保留未完成的订单
        pending_orders = [o for o in self._pending_orders if o.status == 'pending']
        self._pending_orders = pending_orders

        # 清除交易记录
        self._portfolio.trade_history.clear()

        logger.info("Trading history cleared")

    # ========== 回测功能增强 ==========

    def run_backtest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行回测 - 增强版本

        Args:
            params: 回测参数

        Returns:
            回测结果
        """
        try:
            # 获取股票代码
            stock_code = params.get('stock')
            if not stock_code:
                raise ValueError("缺少股票代码参数")

            # 获取数据管理器
            from .unified_data_manager import get_unified_data_manager
            data_manager = get_unified_data_manager()

            if not data_manager:
                raise ValueError("无法获取数据管理器")

            # 获取K线数据
            start_date = params.get('start_date')
            end_date = params.get('end_date')

            kdata = data_manager.get_kdata(
                stock_code,
                start_date=start_date,
                end_date=end_date,
                period='D'
            )

            if kdata is None or kdata.empty:
                raise ValueError("无法获取K线数据")

            # 使用策略插件进行回测
            strategy_name = params.get('strategy', 'MA策略')

            # 这里可以扩展为使用实际的策略插件
            results = self._run_simple_backtest_with_kdata(kdata, params)

            return results

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return {}

    def _run_simple_backtest_with_kdata(self, kdata: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """使用K线数据运行简单回测"""
        try:
            initial_cash = params.get('initial_cash', 100000)
            commission_rate = params.get('commission_rate', 0.0003)

            # 简化的回测逻辑
            cash = initial_cash
            position = 0
            trades = []

            # 计算简单移动平均线信号
            if len(kdata) > 20:
                kdata['ma5'] = kdata['close'].rolling(5).mean()
                kdata['ma20'] = kdata['close'].rolling(20).mean()

                for i in range(20, len(kdata)):
                    current = kdata.iloc[i]
                    prev = kdata.iloc[i-1]

                    # 金叉买入
                    if (prev['ma5'] <= prev['ma20'] and
                        current['ma5'] > current['ma20'] and
                            cash > 0):

                        price = current['close']
                        quantity = int(cash * 0.95 / price / 100) * 100
                        if quantity > 0:
                            cost = quantity * price * (1 + commission_rate)
                            if cost <= cash:
                                cash -= cost
                                position += quantity
                                trades.append({
                                    'time': current.name,
                                    'business': 'BUY',
                                    'stock': params.get('stock', ''),
                                    'price': price,
                                    'quantity': quantity,
                                    'cost': cost,
                                    'cash': cash
                                })

                    # 死叉卖出
                    elif (prev['ma5'] >= prev['ma20'] and
                          current['ma5'] < current['ma20'] and
                          position > 0):

                        price = current['close']
                        quantity = position
                        revenue = quantity * price * (1 - commission_rate)
                        cash += revenue
                        position = 0
                        trades.append({
                            'time': current.name,
                            'business': 'SELL',
                            'stock': params.get('stock', ''),
                            'price': price,
                            'quantity': quantity,
                            'cost': revenue,
                            'cash': cash
                        })

            # 计算最终价值
            final_price = kdata.iloc[-1]['close']
            final_value = cash + position * final_price
            total_return = (final_value - initial_cash) / initial_cash

            return {
                'trades': trades,
                'positions': [{'stock': params.get('stock', ''), 'quantity': position, 'cost': position * final_price}] if position > 0 else [],
                'performance': {
                    'total_return': total_return,
                    'annual_return': total_return,
                    'max_drawdown': 0.0,
                    'win_rate': 0.5,
                    'profit_factor': 1.0 + total_return,
                    'sharpe_ratio': total_return
                },
                'risk': {
                    'alpha': 0.0,
                    'beta': 1.0,
                    'information_ratio': 0.0,
                    'tracking_error': 0.0,
                    'var': 0.0
                }
            }

        except Exception as e:
            logger.error(f"Simple backtest failed: {e}")
            return {}

    # ========== 信号计算功能 ==========

    def calculate_signals(self, stock_code: str, kdata: pd.DataFrame, strategy: str = 'MA策略') -> List[Dict[str, Any]]:
        """
        计算交易信号

        Args:
            stock_code: 股票代码
            kdata: K线数据
            strategy: 策略名称

        Returns:
            信号列表
        """
        try:
            signals = []

            if strategy == 'MA策略' and len(kdata) > 20:
                # 计算移动平均线
                kdata = kdata.copy()
                kdata['ma5'] = kdata['close'].rolling(5).mean()
                kdata['ma20'] = kdata['close'].rolling(20).mean()

                for i in range(20, len(kdata)):
                    current = kdata.iloc[i]
                    prev = kdata.iloc[i-1]

                    # 金叉
                    if prev['ma5'] <= prev['ma20'] and current['ma5'] > current['ma20']:
                        signals.append({
                            'datetime': current.name,
                            'signal': 'BUY',
                            'price': current['close'],
                            'reason': 'MA5上穿MA20'
                        })
                    # 死叉
                    elif prev['ma5'] >= prev['ma20'] and current['ma5'] < current['ma20']:
                        signals.append({
                            'datetime': current.name,
                            'signal': 'SELL',
                            'price': current['close'],
                            'reason': 'MA5下穿MA20'
                        })

            return signals

        except Exception as e:
            logger.error(f"Calculate signals failed: {e}")
            return []
