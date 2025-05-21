class SimulatedTradeAPI:
    """模拟实盘API接口，可扩展对接真实券商API"""

    def __init__(self):
        self.positions = {}

    def buy(self, code, amount):
        if code not in self.positions:
            self.positions[code] = 0
        self.positions[code] += amount
        return f"买入{amount}股，当前持仓{self.positions[code]}股"

    def sell(self, code, amount):
        if code not in self.positions or self.positions[code] < amount:
            return "持仓不足，无法卖出"
        self.positions[code] -= amount
        return f"卖出{amount}股，当前持仓{self.positions[code]}股"

    def get_positions(self):
        return self.positions.copy()
