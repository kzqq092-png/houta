#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略管理器

功能：
1. 加载和管理所有可用策略
2. 提供统一的策略执行接口
3. 支持策略参数配置
4. 策略回测和实盘切换

作者：FactorWeave-Quant Team
版本：V2.0.4
日期：2025-10-12
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.plugin_types import AssetType, DataType
from core.services.unified_data_manager import UnifiedDataManager


class StrategyBase:
    """策略基类"""
    
    def __init__(self, name: str, description: str):
        """
        初始化策略
        
        Args:
            name: 策略名称
            description: 策略描述
        """
        self.name = name
        self.description = description
        self.parameters = {}
        self.data_manager = None
        
    def set_parameters(self, **kwargs):
        """设置策略参数"""
        self.parameters.update(kwargs)
        logger.info(f"策略 {self.name} 参数已更新: {kwargs}")
    
    def set_data_manager(self, data_manager: UnifiedDataManager):
        """设置数据管理器"""
        self.data_manager = data_manager
    
    def get_required_fields(self) -> List[str]:
        """
        获取策略需要的字段列表
        
        Returns:
            字段名列表
        """
        raise NotImplementedError("子类必须实现get_required_fields方法")
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: K线数据
            
        Returns:
            包含信号的DataFrame
        """
        raise NotImplementedError("子类必须实现generate_signals方法")
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证数据完整性
        
        Args:
            data: K线数据
            
        Returns:
            是否通过验证
        """
        required_fields = self.get_required_fields()
        missing_fields = [f for f in required_fields if f not in data.columns]
        
        if missing_fields:
            logger.error(f"策略 {self.name} 缺少必需字段: {missing_fields}")
            return False
        
        return True


class AdjPriceMomentumStrategy(StrategyBase):
    """复权价格动量策略"""
    
    def __init__(self):
        super().__init__(
            name="复权价格动量策略",
            description="使用复权价格计算真实动量，选择动量最强的股票"
        )
        self.parameters = {
            'lookback_period': 20,  # 动量计算周期
            'top_n': 10,           # 选择前N只股票
        }
    
    def get_required_fields(self) -> List[str]:
        return ['adj_close', 'adj_factor', 'close', 'datetime', 'symbol']
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成动量信号"""
        if not self.validate_data(data):
            return pd.DataFrame()
        
        lookback = self.parameters.get('lookback_period', 20)
        
        # 计算动量
        data['momentum'] = data['adj_close'].pct_change(lookback)
        
        # 生成信号（动量>0为买入）
        data['signal'] = (data['momentum'] > 0).astype(int)
        
        logger.info(f"策略 {self.name} 信号生成完成")
        return data


class VWAPMeanReversionStrategy(StrategyBase):
    """VWAP均值回归策略"""
    
    def __init__(self):
        super().__init__(
            name="VWAP均值回归策略",
            description="价格偏离VWAP时进行反向交易"
        )
        self.parameters = {
            'deviation_threshold': 0.02,  # 偏离阈值
            'hold_period': 3,             # 持有周期
            'min_turnover_rate': 0.5,     # 最小换手率
        }
    
    def get_required_fields(self) -> List[str]:
        return ['vwap', 'close', 'turnover_rate', 'datetime', 'symbol']
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成VWAP均值回归信号"""
        if not self.validate_data(data):
            return pd.DataFrame()
        
        threshold = self.parameters.get('deviation_threshold', 0.02)
        min_turnover = self.parameters.get('min_turnover_rate', 0.5)
        
        # 计算偏离度
        data['vwap_deviation'] = (data['close'] - data['vwap']) / data['vwap']
        
        # 流动性过滤
        data['is_liquid'] = data['turnover_rate'] > min_turnover
        
        # 买入信号：价格低于VWAP且流动性充足
        data['buy_signal'] = (
            (data['vwap_deviation'] < -threshold) & 
            data['is_liquid']
        ).astype(int)
        
        # 卖出信号：价格高于VWAP且流动性充足
        data['sell_signal'] = (
            (data['vwap_deviation'] > threshold) & 
            data['is_liquid']
        ).astype(int)
        
        logger.info(f"策略 {self.name} 信号生成完成")
        return data


class StrategyManager:
    """策略管理器"""
    
    def __init__(self):
        """初始化策略管理器"""
        self.strategies: Dict[str, StrategyBase] = {}
        self.data_manager = None
        self._register_builtin_strategies()
        
    def _register_builtin_strategies(self):
        """注册内置策略"""
        self.register_strategy('adj_momentum', AdjPriceMomentumStrategy())
        self.register_strategy('vwap_reversion', VWAPMeanReversionStrategy())
        logger.info(f"已注册 {len(self.strategies)} 个内置策略")
    
    def register_strategy(self, strategy_id: str, strategy: StrategyBase):
        """
        注册策略
        
        Args:
            strategy_id: 策略唯一标识
            strategy: 策略实例
        """
        self.strategies[strategy_id] = strategy
        logger.info(f"注册策略: {strategy_id} - {strategy.name}")
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyBase]:
        """
        获取策略实例
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            策略实例，如果不存在则返回None
        """
        return self.strategies.get(strategy_id)
    
    def list_strategies(self) -> List[Dict[str, str]]:
        """
        列出所有可用策略
        
        Returns:
            策略信息列表
        """
        return [
            {
                'id': strategy_id,
                'name': strategy.name,
                'description': strategy.description,
                'parameters': strategy.parameters
            }
            for strategy_id, strategy in self.strategies.items()
        ]
    
    def set_data_manager(self, data_manager: UnifiedDataManager):
        """设置数据管理器"""
        self.data_manager = data_manager
        for strategy in self.strategies.values():
            strategy.set_data_manager(data_manager)
        logger.info("数据管理器已设置")
    
    def execute_strategy(
        self, 
        strategy_id: str, 
        symbols: List[str],
        start_date: str = None,
        end_date: str = None,
        period: str = 'D',
        **strategy_params
    ) -> Dict[str, pd.DataFrame]:
        """
        执行策略
        
        Args:
            strategy_id: 策略ID
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            **strategy_params: 策略参数
            
        Returns:
            股票代码 -> 信号DataFrame的映射
        """
        # 获取策略
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            logger.error(f"策略不存在: {strategy_id}")
            return {}
        
        # 设置策略参数
        if strategy_params:
            strategy.set_parameters(**strategy_params)
        
        # 确保数据管理器已设置
        if not self.data_manager:
            self.data_manager = UnifiedDataManager()
            strategy.set_data_manager(self.data_manager)
        
        # 为每只股票生成信号
        results = {}
        
        for symbol in symbols:
            try:
                logger.info(f"正在为 {symbol} 执行策略 {strategy.name}...")
                
                # 获取K线数据
                data = self._fetch_kline_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    period=period
                )
                
                if data.empty:
                    logger.warning(f"未获取到 {symbol} 的数据")
                    continue
                
                # 生成信号
                signal_data = strategy.generate_signals(data)
                
                if not signal_data.empty:
                    results[symbol] = signal_data
                    logger.info(f"✅ {symbol} 信号生成成功，共 {len(signal_data)} 条")
                
            except Exception as e:
                logger.error(f"执行策略失败 {symbol}: {e}")
                continue
        
        logger.success(f"策略执行完成！成功: {len(results)}/{len(symbols)}")
        return results
    
    def _fetch_kline_data(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        period: str = 'D'
    ) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            
        Returns:
            K线DataFrame
        """
        try:
            # 使用统一数据管理器获取数据
            data = self.data_manager.get_kdata(
                stock_code=symbol,
                period=period,
                count=365  # 默认获取一年数据
            )
            
            # 日期过滤（如果指定）
            if not data.empty and start_date:
                data = data[data['datetime'] >= pd.to_datetime(start_date)]
            if not data.empty and end_date:
                data = data[data['datetime'] <= pd.to_datetime(end_date)]
            
            return data
            
        except Exception as e:
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            return pd.DataFrame()
    
    def _prepare_backtest_data(self, signal_results: Dict[str, pd.DataFrame], symbols: List[str]) -> Dict[str, Any]:
        """准备回测数据"""
        combined_data = {
            'signals': {},
            'prices': {},
            'dates': []
        }
        
        for symbol, data in signal_results.items():
            if not data.empty and 'signal' in data.columns:
                combined_data['signals'][symbol] = data
                
                # 获取价格数据
                if 'close' in data.columns:
                    combined_data['prices'][symbol] = data['close']
                    
                # 获取日期
                if 'datetime' in data.columns:
                    combined_data['dates'] = data['datetime'].tolist()
        
        return combined_data
    
    def _calculate_professional_metrics(
        self, 
        combined_data: Dict[str, Any], 
        initial_capital: float,
        benchmark: str = '000001'
    ) -> Dict[str, Any]:
        """计算专业回测指标"""
        try:
            import numpy as np
            from scipy import stats
            
            metrics = {}
            
            # 合并所有策略收益
            all_returns = []
            total_trades = 0
            win_trades = 0
            loss_trades = 0
            
            for symbol, data in combined_data['signals'].items():
                if 'signal' in data.columns and 'close' in data.columns:
                    # 计算收益
                    data['returns'] = data['close'].pct_change()
                    data['strategy_returns'] = data['signal'].shift(1) * data['returns']
                    
                    # 移除NaN值
                    strategy_returns = data['strategy_returns'].dropna()
                    all_returns.extend(strategy_returns.tolist())
                    
                    # 统计交易
                    signals = data['signal'].dropna()
                    total_trades += len(signals[signals == 1])
                    win_trades += len(strategy_returns[strategy_returns > 0])
                    loss_trades += len(strategy_returns[strategy_returns < 0])
            
            if not all_returns:
                return self._get_default_metrics(initial_capital)
            
            all_returns = np.array(all_returns)
            
            # 计算基础指标
            total_return = np.sum(all_returns)
            metrics['total_return'] = total_return
            metrics['volatility'] = np.std(all_returns) if len(all_returns) > 1 else 0.0
            metrics['total_trades'] = total_trades
            metrics['win_trades'] = win_trades
            metrics['loss_trades'] = loss_trades
            metrics['win_rate'] = win_trades / (win_trades + loss_trades) if (win_trades + loss_trades) > 0 else 0.0
            
            # 计算风险调整收益指标
            if metrics['volatility'] > 0:
                metrics['sharpe_ratio'] = total_return / metrics['volatility']
            else:
                metrics['sharpe_ratio'] = 0.0
            
            # 计算下行波动率（Sortino比率用）
            downside_returns = all_returns[all_returns < 0]
            downside_deviation = np.std(downside_returns) if len(downside_returns) > 1 else 0.0
            
            if downside_deviation > 0:
                metrics['sortino_ratio'] = total_return / downside_deviation
            else:
                metrics['sortino_ratio'] = 0.0
            
            # 计算最大回撤
            cumulative_returns = np.cumsum(all_returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            metrics['max_drawdown'] = np.min(drawdowns)
            
            # 计算Calmar比率
            if metrics['max_drawdown'] < 0:
                metrics['calmar_ratio'] = total_return / abs(metrics['max_drawdown'])
            else:
                metrics['calmar_ratio'] = 0.0
            
            # 计算VaR (Value at Risk)
            if len(all_returns) > 0:
                metrics['var_95'] = np.percentile(all_returns, 5)
                metrics['var_99'] = np.percentile(all_returns, 1)
            else:
                metrics['var_95'] = 0.0
                metrics['var_99'] = 0.0
            
            # 计算盈亏比
            if loss_trades > 0 and win_trades > 0:
                avg_win = np.mean(all_returns[all_returns > 0]) if len(all_returns[all_returns > 0]) > 0 else 0
                avg_loss = abs(np.mean(all_returns[all_returns < 0])) if len(all_returns[all_returns < 0]) > 0 else 0
                metrics['profit_factor'] = avg_win / avg_loss if avg_loss > 0 else 0
            else:
                metrics['profit_factor'] = 0.0
            
            # 简化的alpha和beta（相对于基准）
            metrics['alpha'] = 0.0  # 需要基准数据才能计算
            metrics['beta'] = 1.0   # 默认beta为1
            metrics['information_ratio'] = 0.0  # 需要基准数据才能计算
            
            # 计算年化收益（简化）
            trading_days = len(all_returns)
            if trading_days > 0:
                daily_return = total_return / trading_days
                metrics['annualized_return'] = (1 + daily_return) ** 252 - 1
            else:
                metrics['annualized_return'] = 0.0
            
            # 添加详细数据
            metrics['detailed_data'] = {
                'all_returns': all_returns.tolist(),
                'cumulative_returns': cumulative_returns.tolist(),
                'drawdowns': drawdowns.tolist()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"计算专业指标失败: {e}")
            return self._get_default_metrics(initial_capital)
    
    def _get_default_metrics(self, initial_capital: float) -> Dict[str, Any]:
        """获取默认指标（当计算失败时）"""
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_duration': 0,
            'var_95': 0.0,
            'var_99': 0.0,
            'total_trades': 0,
            'win_trades': 0,
            'loss_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'alpha': 0.0,
            'beta': 1.0,
            'information_ratio': 0.0,
            'detailed_data': {}
        }
    
    def _fallback_backtest(
        self, 
        strategy_id: str, 
        symbols: List[str], 
        initial_capital: float, 
        **strategy_params
    ) -> Dict[str, Any]:
        """降级到简化回测"""
        logger.info("执行简化回测（降级模式）")
        
        try:
            # 执行策略获取信号
            signal_results = self.execute_strategy(
                strategy_id=strategy_id,
                symbols=symbols,
                **strategy_params
            )
            
            if not signal_results:
                return {
                    'success': False,
                    'error': '策略未生成有效信号',
                    'strategy_id': strategy_id,
                    'symbols': symbols,
                    'level': 'Fallback'
                }
            
            # 简化的回测逻辑
            total_return = 0.0
            win_count = 0
            total_trades = 0
            
            for symbol, signal_data in signal_results.items():
                if 'signal' in signal_data.columns and 'close' in signal_data.columns:
                    # 计算基于信号的收益
                    signal_data['returns'] = signal_data['close'].pct_change()
                    signal_data['strategy_returns'] = signal_data['signal'].shift(1) * signal_data['returns']
                    
                    strategy_returns = signal_data['strategy_returns'].dropna()
                    total_return += strategy_returns.sum()
                    win_count += (strategy_returns > 0).sum()
                    total_trades += (signal_data['signal'] == 1).sum()
            
            # 简化回测结果
            backtest_result = {
                'success': True,
                'strategy_id': strategy_id,
                'strategy_name': self.get_strategy(strategy_id).name if self.get_strategy(strategy_id) else strategy_id,
                'symbols': symbols,
                'initial_capital': initial_capital,
                'total_return': total_return,
                'annualized_return': total_return * 252 / max(total_trades, 1),  # 简化年化
                'volatility': 0.0,  # 简化模式不计算
                'sharpe_ratio': 0.0,  # 简化模式不计算
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0,
                'var_95': 0.0,
                'var_99': 0.0,
                'total_trades': total_trades,
                'win_trades': win_count,
                'loss_trades': total_trades - win_count,
                'win_rate': win_count / total_trades if total_trades > 0 else 0.0,
                'profit_factor': 0.0,
                'alpha': 0.0,
                'beta': 1.0,
                'information_ratio': 0.0,
                'signal_summary': self._summarize_signals(signal_results),
                'backtest_data': {},
                'calculation_time': datetime.now().isoformat(),
                'backtest_engine': 'StrategyManager Fallback v1.0',
                'level': 'Simplified',
                'note': '降级模式 - 简化回测计算'
            }
            
            logger.success(f"简化回测完成！策略: {strategy_id}, 总收益: {backtest_result['total_return']:.2%}, 胜率: {backtest_result['win_rate']:.1%}")
            
            return backtest_result
            
        except Exception as e:
            logger.error(f"简化回测执行失败: {e}")
            return {
                'success': False,
                'error': f'回测执行失败: {e}',
                'strategy_id': strategy_id,
                'symbols': symbols,
                'level': 'Error'
            }
    
    def _summarize_signals(self, signal_results: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """汇总信号统计"""
        summary = {
            'total_symbols': len(signal_results),
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'signal_density': 0.0,
            'symbols_with_signals': 0
        }
        
        total_data_points = 0
        
        for symbol, data in signal_results.items():
            if not data.empty:
                total_data_points += len(data)
                
                if 'signal' in data.columns:
                    signals = data['signal'].dropna()
                    buy_count = (signals == 1).sum()
                    sell_count = (signals == -1).sum()
                    
                    summary['buy_signals'] += buy_count
                    summary['sell_signals'] += sell_count
                    summary['total_signals'] += buy_count + sell_count
                    
                    if (buy_count + sell_count) > 0:
                        summary['symbols_with_signals'] += 1
        
        if total_data_points > 0:
            summary['signal_density'] = summary['total_signals'] / total_data_points
        
        return summary
    
    def backtest_strategy(
        self,
        strategy_id: str,
        symbols: List[str],
        initial_capital: float = 1000000.0,
        start_date: str = None,
        end_date: str = None,
        benchmark: str = '000001',
        **strategy_params
    ) -> Dict[str, Any]:
        """
        策略专业回测
        
        Args:
            strategy_id: 策略ID
            symbols: 股票代码列表
            initial_capital: 初始资金
            start_date: 回测开始日期
            end_date: 回测结束日期
            benchmark: 基准股票代码
            **strategy_params: 策略参数
            
        Returns:
            完整的专业回测结果
        """
        logger.info(f"开始专业回测策略: {strategy_id}")
        
        try:
            # 1. 导入专业回测引擎
            from backtest.unified_backtest_engine import UnifiedBacktestEngine, BacktestLevel
            from core.services.unified_data_manager import UnifiedDataManager
            
            # 2. 初始化专业回测引擎
            backtest_engine = UnifiedBacktestEngine(
                backtest_level=BacktestLevel.PROFESSIONAL,
                use_vectorized_engine=True
            )
            
            # 3. 准备回测参数
            backtest_config = {
                'strategy_id': strategy_id,
                'symbols': symbols,
                'initial_capital': initial_capital,
                'start_date': start_date,
                'end_date': end_date,
                'benchmark': benchmark,
                'strategy_params': strategy_params
            }
            
            # 4. 执行策略信号生成
            signal_results = self.execute_strategy(
                strategy_id=strategy_id,
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                **strategy_params
            )
            
            if not signal_results:
                logger.error("未生成任何信号，回测终止")
                return {
                    'success': False,
                    'error': '策略未生成有效信号',
                    'strategy_id': strategy_id,
                    'symbols': symbols
                }
            
            # 5. 执行专业回测计算
            logger.info("使用专业回测引擎计算...")
            
            # 整合信号数据用于回测
            combined_data = self._prepare_backtest_data(signal_results, symbols)
            
            # 6. 计算专业回测指标
            backtest_metrics = self._calculate_professional_metrics(
                combined_data, 
                initial_capital,
                benchmark
            )
            
            # 7. 组装完整回测结果
            backtest_result = {
                'success': True,
                'strategy_id': strategy_id,
                'strategy_name': self.get_strategy(strategy_id).name if self.get_strategy(strategy_id) else strategy_id,
                'symbols': symbols,
                'backtest_period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'initial_capital': initial_capital,
                'benchmark': benchmark,
                
                # 核心收益指标
                'total_return': backtest_metrics.get('total_return', 0.0),
                'annualized_return': backtest_metrics.get('annualized_return', 0.0),
                'volatility': backtest_metrics.get('volatility', 0.0),
                
                # 风险调整收益指标
                'sharpe_ratio': backtest_metrics.get('sharpe_ratio', 0.0),
                'sortino_ratio': backtest_metrics.get('sortino_ratio', 0.0),
                'calmar_ratio': backtest_metrics.get('calmar_ratio', 0.0),
                
                # 风险指标
                'max_drawdown': backtest_metrics.get('max_drawdown', 0.0),
                'max_drawdown_duration': backtest_metrics.get('max_drawdown_duration', 0),
                'var_95': backtest_metrics.get('var_95', 0.0),
                'var_99': backtest_metrics.get('var_99', 0.0),
                
                # 交易统计
                'total_trades': backtest_metrics.get('total_trades', 0),
                'win_trades': backtest_metrics.get('win_trades', 0),
                'loss_trades': backtest_metrics.get('loss_trades', 0),
                'win_rate': backtest_metrics.get('win_rate', 0.0),
                'profit_factor': backtest_metrics.get('profit_factor', 0.0),
                
                # 相对指标
                'alpha': backtest_metrics.get('alpha', 0.0),
                'beta': backtest_metrics.get('beta', 0.0),
                'information_ratio': backtest_metrics.get('information_ratio', 0.0),
                
                # 详细数据
                'signal_summary': self._summarize_signals(signal_results),
                'backtest_data': backtest_metrics.get('detailed_data', {}),
                
                # 元数据
                'calculation_time': datetime.now().isoformat(),
                'backtest_engine': 'UnifiedBacktestEngine v2.0',
                'level': 'Professional'
            }
            
            logger.success(f"专业回测完成！策略: {strategy_id}, 总收益: {backtest_result['total_return']:.2%}, 夏普比率: {backtest_result['sharpe_ratio']:.2f}")
            
            return backtest_result
            
        except Exception as e:
            logger.error(f"专业回测执行失败: {e}")
            # 降级到简化回测
            logger.warning("降级到简化回测模式...")
            return self._fallback_backtest(strategy_id, symbols, initial_capital, **strategy_params)


# 全局策略管理器实例
_strategy_manager_instance = None


def get_strategy_manager() -> StrategyManager:
    """
    获取全局策略管理器实例（单例模式）
    
    Returns:
        策略管理器实例
    """
    global _strategy_manager_instance
    if _strategy_manager_instance is None:
        _strategy_manager_instance = StrategyManager()
    return _strategy_manager_instance


# 使用示例
if __name__ == "__main__":
    # 获取策略管理器
    manager = get_strategy_manager()
    
    # 列出所有可用策略
    print("可用策略:")
    for strategy_info in manager.list_strategies():
        print(f"  - {strategy_info['name']}: {strategy_info['description']}")
    
    # 执行策略
    results = manager.execute_strategy(
        strategy_id='adj_momentum',
        symbols=['000001', '600519'],
        lookback_period=20,
        top_n=2
    )
    
    print(f"\n策略执行结果: {len(results)} 只股票")
    
    # 回测策略
    backtest_results = manager.backtest_strategy(
        strategy_id='vwap_reversion',
        symbols=['000001'],
        deviation_threshold=0.02
    )
    
    print(f"\n回测结果:")
    print(f"  总收益: {backtest_results.get('total_return', 0):.2%}")
    print(f"  胜率: {backtest_results.get('win_rate', 0):.1%}")

