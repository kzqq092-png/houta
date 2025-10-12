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
    
    def backtest_strategy(
        self,
        strategy_id: str,
        symbols: List[str],
        initial_capital: float = 1000000.0,
        **strategy_params
    ) -> Dict[str, Any]:
        """
        策略回测
        
        Args:
            strategy_id: 策略ID
            symbols: 股票代码列表
            initial_capital: 初始资金
            **strategy_params: 策略参数
            
        Returns:
            回测结果
        """
        logger.info(f"开始回测策略: {strategy_id}")
        
        # 执行策略获取信号
        signal_results = self.execute_strategy(
            strategy_id=strategy_id,
            symbols=symbols,
            **strategy_params
        )
        
        if not signal_results:
            logger.error("未生成任何信号，回测终止")
            return {}
        
        # 简单的回测逻辑
        total_return = 0.0
        win_count = 0
        total_trades = 0
        
        for symbol, signal_data in signal_results.items():
            # 这里是简化的回测逻辑
            if 'signal' in signal_data.columns:
                # 计算基于信号的收益
                signal_data['returns'] = signal_data['close'].pct_change()
                signal_data['strategy_returns'] = signal_data['signal'].shift(1) * signal_data['returns']
                
                total_return += signal_data['strategy_returns'].sum()
                win_count += (signal_data['strategy_returns'] > 0).sum()
                total_trades += (signal_data['signal'] == 1).sum()
        
        # 计算回测指标
        backtest_result = {
            'strategy_id': strategy_id,
            'symbols': symbols,
            'initial_capital': initial_capital,
            'total_return': total_return,
            'total_trades': total_trades,
            'win_count': win_count,
            'win_rate': win_count / total_trades if total_trades > 0 else 0,
            'final_capital': initial_capital * (1 + total_return)
        }
        
        logger.success(f"回测完成！总收益: {total_return:.2%}，胜率: {backtest_result['win_rate']:.1%}")
        
        return backtest_result


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

