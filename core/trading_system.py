"""
交易系统核心模块
"""
from typing import *
from datetime import datetime
import hikyuu as hku
from hikyuu.interactive import *
from core.data_manager import data_manager
from utils.performance_monitor import monitor_performance
from core.logger import LogManager, LogLevel


class TradingSystem:
    """交易系统类"""

    def __init__(self):
        """初始化交易系统"""
        self.current_stock = None
        self.current_kdata = None
        self.current_signals = []
        self.current_positions = []

    def set_stock(self, stock_code: str):
        """设置当前股票

        Args:
            stock_code: 股票代码
        """
        try:
            self.current_stock = stock_code
            self.current_kdata = None
            self.current_signals = []
            self.current_positions = []

        except Exception as e:
            LogManager.log(f"设置股票失败: {str(e)}", LogLevel.ERROR)

    def load_kdata(self, start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   ktype: str = 'D'):
        """加载K线数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            ktype: K线类型
        """
        try:
            if not self.current_stock:
                raise ValueError("未设置股票")

            self.current_kdata = data_manager.get_kdata(
                self.current_stock,
                start_date,
                end_date,
                ktype
            )

        except Exception as e:
            LogManager.log(f"加载K线数据失败: {str(e)}", LogLevel.ERROR)

    def calculate_signals(self, strategy: str = 'MA') -> List[Dict[str, Any]]:
        """计算交易信号

        Args:
            strategy: 策略名称

        Returns:
            交易信号列表
        """
        try:
            if not self.current_kdata:
                raise ValueError("未加载K线数据")

            signals = []

            if strategy == 'MA':
                # 计算MA指标
                ma5 = TA_MA(self.current_kdata.close, 5)
                ma10 = TA_MA(self.current_kdata.close, 10)

                # 生成交易信号
                for i in range(1, len(self.current_kdata)):
                    if (ma5[i] > ma10[i] and ma5[i-1] <= ma10[i-1]):
                        signals.append({
                            'time': self.current_kdata[i].datetime.datetime(),
                            'type': 'MA',
                            'signal': 'BUY',
                            'price': float(self.current_kdata[i].close),
                            'strength': abs(ma5[i] - ma10[i])
                        })
                    elif (ma5[i] < ma10[i] and ma5[i-1] >= ma10[i-1]):
                        signals.append({
                            'time': self.current_kdata[i].datetime.datetime(),
                            'type': 'MA',
                            'signal': 'SELL',
                            'price': float(self.current_kdata[i].close),
                            'strength': abs(ma5[i] - ma10[i])
                        })

            elif strategy == 'MACD':
                # 计算MACD指标
                macd = TA_MACD(self.current_kdata.close)

                # 生成交易信号
                for i in range(1, len(self.current_kdata)):
                    if (macd.dif[i] > macd.dea[i] and
                            macd.dif[i-1] <= macd.dea[i-1]):
                        signals.append({
                            'time': self.current_kdata[i].datetime.datetime(),
                            'type': 'MACD',
                            'signal': 'BUY',
                            'price': float(self.current_kdata[i].close),
                            'strength': abs(macd.dif[i] - macd.dea[i])
                        })
                    elif (macd.dif[i] < macd.dea[i] and
                          macd.dif[i-1] >= macd.dea[i-1]):
                        signals.append({
                            'time': self.current_kdata[i].datetime.datetime(),
                            'type': 'MACD',
                            'signal': 'SELL',
                            'price': float(self.current_kdata[i].close),
                            'strength': abs(macd.dif[i] - macd.dea[i])
                        })

            elif strategy == 'KDJ':
                # 计算KDJ指标
                kdj = TA_STOCH(self.current_kdata)

                # 生成交易信号
                for i in range(1, len(self.current_kdata)):
                    if (kdj.k[i] > kdj.d[i] and kdj.k[i-1] <= kdj.d[i-1]):
                        signals.append({
                            'time': self.current_kdata[i].datetime.datetime(),
                            'type': 'KDJ',
                            'signal': 'BUY',
                            'price': float(self.current_kdata[i].close),
                            'strength': abs(kdj.k[i] - kdj.d[i])
                        })
                    elif (kdj.k[i] < kdj.d[i] and kdj.k[i-1] >= kdj.d[i-1]):
                        signals.append({
                            'time': self.current_kdata[i].datetime.datetime(),
                            'type': 'KDJ',
                            'signal': 'SELL',
                            'price': float(self.current_kdata[i].close),
                            'strength': abs(kdj.k[i] - kdj.d[i])
                        })

            self.current_signals = signals
            return signals

        except Exception as e:
            LogManager.log(f"计算交易信号失败: {str(e)}", LogLevel.ERROR)
            return []

    @monitor_performance(name="run_backtest", threshold_ms=5000)
    def run_backtest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """运行回测

        Args:
            params: 回测参数

        Returns:
            回测结果
        """
        try:
            if not self.current_kdata:
                raise ValueError("未加载K线数据")

            # 创建交易管理器
            tm = crtTM(
                init_cash=params.get('initial_cash', 100000),
                commission_ratio=params.get('commission_rate', 0.0003),
                slip=params.get('slippage', 0.0001)
            )

            # 创建信号指示器
            if params.get('strategy') == 'MA':
                sg = SG_Cross(
                    MA(CLOSE(), params.get('ma_short', 5)),
                    MA(CLOSE(), params.get('ma_long', 10))
                )
            elif params.get('strategy') == 'MACD':
                sg = SG_Single(
                    MACD(
                        CLOSE(),
                        params.get('macd_short', 12),
                        params.get('macd_long', 26),
                        params.get('macd_signal', 9)
                    ),
                    filter_n=params.get('filter_n', 10),
                    filter_p=params.get('filter_p', 0.1)
                )
            else:
                raise ValueError(f"不支持的策略: {params.get('strategy')}")

            # 创建止损策略
            if params.get('stop_strategy') == 'FIXED':
                st = ST_FixedPercent(
                    params.get('stop_loss', 0.05),
                    params.get('stop_profit', 0.1)
                )
            elif params.get('stop_strategy') == 'ATR':
                st = ST_ATR(
                    n=params.get('atr_n', 14),
                    multiple=params.get('atr_multiple', 2)
                )
            else:
                st = None

            # 创建资金管理策略
            if params.get('mm_strategy') == 'FIXED':
                mm = MM_FixedCount(params.get('fixed_count', 100))
            elif params.get('mm_strategy') == 'PERCENT':
                mm = MM_FixedPercent(params.get('percent', 0.1))
            else:
                mm = None

            # 创建交易系统
            sys = SYS_Simple(
                tm=tm,
                sg=sg,
                st=st,
                mm=mm
            )

            # 运行回测
            sys.run(self.current_kdata, Query(-1))

            # 获取回测结果
            results = {
                'trades': [],
                'positions': [],
                'performance': {},
                'risk': {}
            }

            # 获取交易记录
            for trade in tm.trade_list:
                results['trades'].append({
                    'time': trade.datetime.datetime(),
                    'business': str(trade.business),
                    'stock': trade.stock.market_code,
                    'price': float(trade.price),
                    'quantity': int(trade.quantity),
                    'cost': float(trade.cost),
                    'stoploss': float(trade.stoploss),
                    'cash': float(trade.cash)
                })

            # 获取持仓记录
            for pos in tm.position_list:
                results['positions'].append({
                    'stock': pos.stock.market_code,
                    'quantity': int(pos.number),
                    'cost': float(pos.total_cost),
                    'profit': float(pos.profit),
                    'stoploss': float(pos.stoploss)
                })

            # 计算绩效指标
            results['performance'].update({
                'total_return': float(tm.profit_percent),
                'annual_return': float(tm.annual_profit),
                'max_drawdown': float(tm.max_drawdown),
                'win_rate': float(tm.win_rate),
                'profit_factor': float(tm.profit_factor),
                'sharpe_ratio': float(tm.sharpe)
            })

            # 计算风险指标
            results['risk'].update({
                'alpha': float(tm.alpha),
                'beta': float(tm.beta),
                'information_ratio': float(tm.information_ratio),
                'tracking_error': float(tm.tracking_error),
                'var': float(tm.var)
            })

            return results

        except Exception as e:
            LogManager.log(f"运行回测失败: {str(e)}", LogLevel.ERROR)
            return {}

    def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览

        Returns:
            市场概览数据
        """
        try:
            # 获取指数数据
            index_data = data_manager.get_index_data()

            # 获取市场统计
            market_stats = data_manager.get_market_statistics()

            # 计算市场情绪
            if market_stats['total'] > 0:
                sentiment = market_stats['up_count'] / market_stats['total']
            else:
                sentiment = 0.5

            return {
                'indices': index_data,
                'statistics': market_stats,
                'sentiment': sentiment
            }

        except Exception as e:
            LogManager.log(f"获取市场概览失败: {str(e)}", LogLevel.ERROR)
            return {}

    def get_fund_flow(self) -> Dict[str, Any]:
        """获取资金流向

        Returns:
            资金流向数据
        """
        try:
            # 获取北向资金数据
            north_flow = self._get_north_flow()

            # 获取行业资金流向
            industry_flow = self._get_industry_flow()

            # 获取概念资金流向
            concept_flow = self._get_concept_flow()

            return {
                'north_flow': north_flow,
                'industry_flow': industry_flow,
                'concept_flow': concept_flow
            }

        except Exception as e:
            LogManager.log(f"获取资金流向失败: {str(e)}", LogLevel.ERROR)
            return {}

    def _get_north_flow(self) -> List[Dict[str, Any]]:
        """获取北向资金数据"""
        try:
            # TODO: 实现北向资金数据获取
            return []
        except Exception as e:
            LogManager.log(f"获取北向资金数据失败: {str(e)}", LogLevel.ERROR)
            return []

    def _get_industry_flow(self) -> List[Dict[str, Any]]:
        """获取行业资金流向数据"""
        try:
            # TODO: 实现行业资金流向数据获取
            return []
        except Exception as e:
            LogManager.log(f"获取行业资金流向数据失败: {str(e)}", LogLevel.ERROR)
            return []

    def _get_concept_flow(self) -> List[Dict[str, Any]]:
        """获取概念资金流向数据"""
        try:
            # TODO: 实现概念资金流向数据获取
            return []
        except Exception as e:
            LogManager.log(f"获取概念资金流向数据失败: {str(e)}", LogLevel.ERROR)
            return []


# 创建全局交易系统实例
trading_system = TradingSystem()
