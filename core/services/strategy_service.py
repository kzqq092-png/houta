"""
策略服务

提供策略管理、回测、优化等功能。
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .base_service import BaseService

logger = logging.getLogger(__name__)


class StrategyService(BaseService):
    """策略服务"""

    def __init__(self):
        """初始化策略服务"""
        super().__init__()
        self.strategies = {}
        self.backtest_results = {}
        self.optimization_results = {}
        self._load_strategies()

    def _load_strategies(self) -> None:
        """加载策略"""
        try:
            # 这里应该从文件或数据库加载策略
            # 暂时使用示例数据
            self.strategies = {
                'ma_cross': {
                    'name': '双均线策略',
                    'type': '趋势跟踪',
                    'description': '基于短期和长期移动平均线的交叉信号进行交易',
                    'parameters': {
                        'short_period': 5,
                        'long_period': 20,
                        'stop_loss': 0.05,
                        'take_profit': 0.10
                    },
                    'code': '''
def strategy_logic(data, params):
    signals = {'buy': [], 'sell': [], 'hold': []}
    
    if len(data) > params['long_period']:
        ma_short = data['close'].rolling(params['short_period']).mean()
        ma_long = data['close'].rolling(params['long_period']).mean()
        
        # 金叉买入
        if ma_short.iloc[-1] > ma_long.iloc[-1] and ma_short.iloc[-2] <= ma_long.iloc[-2]:
            signals['buy'].append({
                'price': data['close'].iloc[-1],
                'volume': 100,
                'reason': '金叉买入'
            })
        # 死叉卖出
        elif ma_short.iloc[-1] < ma_long.iloc[-1] and ma_short.iloc[-2] >= ma_long.iloc[-2]:
            signals['sell'].append({
                'price': data['close'].iloc[-1],
                'volume': 100,
                'reason': '死叉卖出'
            })
    
    return signals
                    ''',
                    'created_date': '2024-01-01',
                    'status': '活跃'
                },
                'rsi_reversal': {
                    'name': 'RSI反转策略',
                    'type': '均值回归',
                    'description': '利用RSI超买超卖信号进行反向交易',
                    'parameters': {
                        'rsi_period': 14,
                        'oversold_threshold': 30,
                        'overbought_threshold': 70,
                        'stop_loss': 0.03,
                        'take_profit': 0.08
                    },
                    'code': '''
def strategy_logic(data, params):
    signals = {'buy': [], 'sell': [], 'hold': []}
    
    if len(data) > params['rsi_period']:
        # 计算RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=params['rsi_period']).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        
        # RSI超卖买入
        if current_rsi < params['oversold_threshold']:
            signals['buy'].append({
                'price': data['close'].iloc[-1],
                'volume': 100,
                'reason': f'RSI超卖买入 ({current_rsi:.1f})'
            })
        # RSI超买卖出
        elif current_rsi > params['overbought_threshold']:
            signals['sell'].append({
                'price': data['close'].iloc[-1],
                'volume': 100,
                'reason': f'RSI超买卖出 ({current_rsi:.1f})'
            })
    
    return signals
                    ''',
                    'created_date': '2024-01-15',
                    'status': '测试中'
                }
            }

            logger.info(f"已加载 {len(self.strategies)} 个策略")

        except Exception as e:
            logger.error(f"加载策略失败: {e}")

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """获取所有策略"""
        try:
            return list(self.strategies.values())
        except Exception as e:
            logger.error(f"获取策略列表失败: {e}")
            return []

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取指定策略"""
        try:
            return self.strategies.get(strategy_id)
        except Exception as e:
            logger.error(f"获取策略失败: {e}")
            return None

    def save_strategy(self, strategy_data: Dict[str, Any]) -> bool:
        """保存策略"""
        try:
            strategy_id = strategy_data.get(
                'name', '').lower().replace(' ', '_')
            if not strategy_id:
                logger.error("策略名称不能为空")
                return False

            self.strategies[strategy_id] = strategy_data

            # 这里应该保存到文件或数据库
            # 暂时只保存在内存中

            logger.info(f"策略已保存: {strategy_data.get('name')}")
            return True

        except Exception as e:
            logger.error(f"保存策略失败: {e}")
            return False

    def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略"""
        try:
            if strategy_id in self.strategies:
                del self.strategies[strategy_id]
                logger.info(f"策略已删除: {strategy_id}")
                return True
            else:
                logger.warning(f"策略不存在: {strategy_id}")
                return False

        except Exception as e:
            logger.error(f"删除策略失败: {e}")
            return False

    def clone_strategy(self, strategy_id: str, new_name: str) -> bool:
        """克隆策略"""
        try:
            if strategy_id not in self.strategies:
                logger.error(f"源策略不存在: {strategy_id}")
                return False

            # 复制策略数据
            source_strategy = self.strategies[strategy_id].copy()
            source_strategy['name'] = new_name
            source_strategy['created_date'] = datetime.now().strftime(
                '%Y-%m-%d')
            source_strategy['status'] = '新建'

            # 保存克隆的策略
            new_strategy_id = new_name.lower().replace(' ', '_')
            self.strategies[new_strategy_id] = source_strategy

            logger.info(f"策略已克隆: {strategy_id} -> {new_strategy_id}")
            return True

        except Exception as e:
            logger.error(f"克隆策略失败: {e}")
            return False

    def run_backtest(self, strategy_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """运行回测"""
        try:
            if strategy_id not in self.strategies:
                logger.error(f"策略不存在: {strategy_id}")
                return {}

            strategy = self.strategies[strategy_id]

            # 模拟回测结果
            backtest_result = {
                'strategy_id': strategy_id,
                'strategy_name': strategy['name'],
                'start_date': params.get('start_date', '2023-01-01'),
                'end_date': params.get('end_date', '2024-01-01'),
                'initial_capital': params.get('initial_capital', 100000),
                'final_capital': 115600,  # 模拟结果
                'total_return': 0.156,
                'annual_return': 0.123,
                'max_drawdown': -0.082,
                'sharpe_ratio': 1.45,
                'win_rate': 0.625,
                'profit_loss_ratio': 1.8,
                'total_trades': 48,
                'winning_trades': 30,
                'losing_trades': 18,
                'avg_profit': 1250.5,
                'avg_loss': -695.8,
                'max_profit': 3200.0,
                'max_loss': -1850.0,
                'backtest_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # 保存回测结果
            result_id = f"{strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.backtest_results[result_id] = backtest_result

            logger.info(f"回测完成: {strategy['name']}")
            return backtest_result

        except Exception as e:
            logger.error(f"运行回测失败: {e}")
            return {}

    def optimize_strategy(self, strategy_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """优化策略"""
        try:
            if strategy_id not in self.strategies:
                logger.error(f"策略不存在: {strategy_id}")
                return {}

            strategy = self.strategies[strategy_id]

            # 模拟优化结果
            optimization_result = {
                'strategy_id': strategy_id,
                'strategy_name': strategy['name'],
                'optimization_target': params.get('target', '总收益率'),
                'optimization_algorithm': params.get('algorithm', '网格搜索'),
                'iterations': params.get('iterations', 100),
                'best_parameters': {
                    'short_period': 5,
                    'long_period': 20,
                    'stop_loss': 0.035,
                    'take_profit': 0.082
                },
                'best_performance': {
                    'total_return': 0.189,
                    'max_drawdown': -0.061,
                    'sharpe_ratio': 1.67,
                    'win_rate': 0.68
                },
                'improvement': {
                    'total_return': 0.033,
                    'max_drawdown': 0.021,
                    'sharpe_ratio': 0.22,
                    'win_rate': 0.055
                },
                'optimization_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # 保存优化结果
            result_id = f"{strategy_id}_opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.optimization_results[result_id] = optimization_result

            logger.info(f"策略优化完成: {strategy['name']}")
            return optimization_result

        except Exception as e:
            logger.error(f"策略优化失败: {e}")
            return {}

    def get_backtest_results(self, strategy_id: str = None) -> List[Dict[str, Any]]:
        """获取回测结果"""
        try:
            if strategy_id:
                return [result for result in self.backtest_results.values()
                        if result.get('strategy_id') == strategy_id]
            else:
                return list(self.backtest_results.values())

        except Exception as e:
            logger.error(f"获取回测结果失败: {e}")
            return []

    def get_optimization_results(self, strategy_id: str = None) -> List[Dict[str, Any]]:
        """获取优化结果"""
        try:
            if strategy_id:
                return [result for result in self.optimization_results.values()
                        if result.get('strategy_id') == strategy_id]
            else:
                return list(self.optimization_results.values())

        except Exception as e:
            logger.error(f"获取优化结果失败: {e}")
            return []

    def export_strategy(self, strategy_id: str, file_path: str) -> bool:
        """导出策略"""
        try:
            if strategy_id not in self.strategies:
                logger.error(f"策略不存在: {strategy_id}")
                return False

            strategy = self.strategies[strategy_id]

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(strategy, f, ensure_ascii=False, indent=2)

            logger.info(f"策略已导出: {file_path}")
            return True

        except Exception as e:
            logger.error(f"导出策略失败: {e}")
            return False

    def import_strategy(self, file_path: str) -> bool:
        """导入策略"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                strategy_data = json.load(f)

            # 验证策略数据
            required_fields = ['name', 'type', 'description', 'code']
            if not all(field in strategy_data for field in required_fields):
                logger.error("策略数据格式不正确")
                return False

            # 保存策略
            return self.save_strategy(strategy_data)

        except Exception as e:
            logger.error(f"导入策略失败: {e}")
            return False

    def validate_strategy_code(self, code: str) -> Dict[str, Any]:
        """验证策略代码"""
        try:
            # 简单的代码验证
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }

            # 检查必要的函数
            if 'strategy_logic' not in code:
                validation_result['valid'] = False
                validation_result['errors'].append("缺少strategy_logic函数")

            # 检查语法
            try:
                compile(code, '<string>', 'exec')
            except SyntaxError as e:
                validation_result['valid'] = False
                validation_result['errors'].append(f"语法错误: {e}")

            # 检查潜在问题
            if 'import os' in code or 'import sys' in code:
                validation_result['warnings'].append("策略代码包含系统模块导入，请谨慎使用")

            return validation_result

        except Exception as e:
            logger.error(f"验证策略代码失败: {e}")
            return {'valid': False, 'errors': [str(e)], 'warnings': []}

    def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """获取策略性能统计"""
        try:
            if strategy_id not in self.strategies:
                return {}

            # 获取该策略的所有回测结果
            backtest_results = self.get_backtest_results(strategy_id)
            if not backtest_results:
                return {}

            # 计算性能统计
            total_returns = [result['total_return']
                             for result in backtest_results]
            sharpe_ratios = [result['sharpe_ratio']
                             for result in backtest_results]
            max_drawdowns = [result['max_drawdown']
                             for result in backtest_results]

            performance = {
                'total_backtests': len(backtest_results),
                'avg_return': sum(total_returns) / len(total_returns),
                'best_return': max(total_returns),
                'worst_return': min(total_returns),
                'avg_sharpe_ratio': sum(sharpe_ratios) / len(sharpe_ratios),
                'avg_max_drawdown': sum(max_drawdowns) / len(max_drawdowns),
                'consistency_score': 1 - (max(total_returns) - min(total_returns)) / max(total_returns) if total_returns else 0
            }

            return performance

        except Exception as e:
            logger.error(f"获取策略性能失败: {e}")
            return {}

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'service_name': 'StrategyService',
            'status': 'running',
            'strategies_count': len(self.strategies),
            'backtest_results_count': len(self.backtest_results),
            'optimization_results_count': len(self.optimization_results),
            'last_update': datetime.now().isoformat()
        }
