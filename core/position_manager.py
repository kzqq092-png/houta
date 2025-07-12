from utils.performance_monitor import monitor_performance


@monitor_performance(name="get_buy_num", threshold_ms=500)
def _get_buy_num(self, signal: Signal) -> int:
    """
    根据信号计算买入数量

    Args:
        signal (Signal): 交易信号

    Returns:
        int: 买入数量
    """
    if not signal.buy_price or signal.buy_price <= 0:
        return 0

    available_cash = self.account.available_cash
    if available_cash <= 0:
        return 0

    # 计算每手交易成本
    cost_per_lot = signal.buy_price * \
        self.lot_size * (1 + self.commission_rate)

    # 计算最大可买入手数
    max_lots = int(available_cash / cost_per_lot)

    # 如果资金不足买一手，返回0
    if max_lots == 0:
        return 0

    # 如果有仓位限制，取较小值
    if self.position_limit > 0:
        max_lots = min(max_lots, self.position_limit)

    return max_lots * self.lot_size
