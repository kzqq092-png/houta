#!/usr/bin/env python3
"""
验证策略适配器修复后的功能测试
"""

import sys
import os
import logging
from datetime import datetime
import pandas as pd

# 添加项目路径
sys.path.insert(0, 'd:\\DevelopTool\\FreeCode\\HIkyuu-UI\\hikyuu-ui')

from core.strategy_extensions import (
    StrategyContext, Signal, TradeResult, 
    SignalType, TradeAction, TradeStatus, StandardMarketData, TimeFrame
)
from strategies.strategy_adapters import AdjMomentumPlugin, VWAPReversionPlugin

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_market_data():
    """创建示例市场数据"""
    dates = pd.date_range('2024-01-01', periods=50, freq='D')
    
    # 确保所有Series具有相同的长度（50个）
    data = {
        'open': pd.Series(range(100, 150), index=dates),
        'high': pd.Series(range(105, 155), index=dates),
        'low': pd.Series(range(95, 145), index=dates),
        'close': pd.Series(range(102, 152), index=dates),
        'volume': pd.Series(range(1000, 1050), index=dates),
        'turnover_rate': pd.Series([1.0 + (i % 5) * 0.1 for i in range(50)], index=dates),
        'vwap': pd.Series(range(101, 151), index=dates)  # 添加VWAP数据
    }
    
    df = pd.DataFrame(data)
    return df


def test_adj_momentum_plugin():
    """测试复权动量策略适配器"""
    logger.info("=== 测试复权动量策略适配器 ===")
    
    try:
        # 创建插件实例
        plugin = AdjMomentumPlugin()
        
        # 获取策略信息
        info = plugin.get_strategy_info()
        logger.info(f"策略名称: {info.name}")
        logger.info(f"策略描述: {info.description}")
        
        # 创建市场数据
        df = create_sample_market_data()
        market_data = StandardMarketData.from_dataframe(df, symbol="TEST001")
        
        # 创建上下文
        context = StrategyContext(
            symbol="TEST001",
            timeframe=TimeFrame.DAY_1,
            start_date=pd.Timestamp('2024-01-01'),
            end_date=pd.Timestamp('2024-12-31'),
            commission_rate=0.001
        )
        
        # 测试策略初始化
        parameters = {'momentum_threshold': 0.02, 'volume_filter': 1.0}
        plugin.initialize_strategy(context, parameters)
        logger.info("✅ 策略初始化成功")
        
        # 测试信号生成
        signals = plugin.generate_signals(market_data, context)
        logger.info(f"生成信号数量: {len(signals)}")
        
        if signals:
            signal = signals[0]
            logger.info(f"信号类型: {signal.signal_type.value}")
            logger.info(f"信号强度: {signal.strength:.3f}")
            logger.info(f"信号原因: {signal.reason}")
            
            # 测试交易执行
            trade_result = plugin.execute_trade(signal, context)
            logger.info(f"交易执行结果: {trade_result.trade_id} {trade_result.status}")
        
        logger.info("✅ 复权动量策略适配器测试完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 复权动量策略适配器测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_vwap_reversion_plugin():
    """测试VWAP均值回归策略适配器"""
    logger.info("=== 测试VWAP均值回归策略适配器 ===")
    
    try:
        # 创建插件实例
        plugin = VWAPReversionPlugin()
        
        # 获取策略信息
        info = plugin.get_strategy_info()
        logger.info(f"策略名称: {info.name}")
        logger.info(f"策略描述: {info.description}")
        
        # 创建市场数据
        df = create_sample_market_data()
        market_data = StandardMarketData.from_dataframe(df, symbol="TEST002")
        
        # 创建上下文
        context = StrategyContext(
            symbol="TEST002",
            timeframe=TimeFrame.DAY_1,
            start_date=pd.Timestamp('2024-01-01'),
            end_date=pd.Timestamp('2024-12-31'),
            commission_rate=0.001
        )
        
        # 测试策略初始化
        parameters = {'deviation_threshold': 0.02, 'hold_period': 3}
        plugin.initialize_strategy(context, parameters)
        logger.info("✅ 策略初始化成功")
        
        # 测试信号生成
        signals = plugin.generate_signals(market_data, context)
        logger.info(f"生成信号数量: {len(signals)}")
        
        if signals:
            signal = signals[0]
            logger.info(f"信号类型: {signal.signal_type.value}")
            logger.info(f"信号强度: {signal.strength:.3f}")
            logger.info(f"信号原因: {signal.reason}")
            
            # 测试交易执行
            trade_result = plugin.execute_trade(signal, context)
            logger.info(f"交易执行结果: {trade_result.trade_id} {trade_result.status}")
            
            # 测试回调方法
            plugin.on_trade(trade_result)
            plugin.cleanup()
        
        logger.info("✅ VWAP均值回归策略适配器测试完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ VWAP均值回归策略适配器测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_interface_compatibility():
    """测试接口兼容性"""
    logger.info("=== 测试IStrategyPlugin接口兼容性 ===")
    
    try:
        from core.strategy_extensions import IStrategyPlugin
        
        # 检查AdjMomentumPlugin接口
        adj_plugin = AdjMomentumPlugin()
        required_methods = [
            'plugin_info', 'get_strategy_info', 'initialize_strategy',
            'generate_signals', 'execute_trade', 'on_trade', 'on_order', 'cleanup'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(adj_plugin, method):
                missing_methods.append(method)
        
        if missing_methods:
            logger.error(f"❌ AdjMomentumPlugin缺少接口方法: {missing_methods}")
            return False
        else:
            logger.info("✅ AdjMomentumPlugin接口完整性检查通过")
        
        # 检查VWAPReversionPlugin接口
        vwap_plugin = VWAPReversionPlugin()
        missing_methods = []
        for method in required_methods:
            if not hasattr(vwap_plugin, method):
                missing_methods.append(method)
        
        if missing_methods:
            logger.error(f"❌ VWAPReversionPlugin缺少接口方法: {missing_methods}")
            return False
        else:
            logger.info("✅ VWAPReversionPlugin接口完整性检查通过")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 接口兼容性测试失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.info("🧪 开始策略适配器修复验证测试")
    logger.info("=" * 60)
    
    results = []
    
    # 测试接口兼容性
    results.append(test_interface_compatibility())
    
    # 测试复权动量策略适配器
    results.append(test_adj_momentum_plugin())
    
    # 测试VWAP均值回归策略适配器
    results.append(test_vwap_reversion_plugin())
    
    # 汇总结果
    logger.info("=" * 60)
    logger.info("📊 测试结果汇总:")
    
    test_names = ["接口兼容性", "复权动量策略", "VWAP回归策略"]
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{i+1}. {name}: {status}")
    
    total_passed = sum(results)
    total_tests = len(results)
    
    logger.info(f"总体通过率: {total_passed}/{total_tests} ({total_passed/total_tests*100:.1f}%)")
    
    if total_passed == total_tests:
        logger.info("🎉 所有测试通过！策略适配器修复验证成功！")
        return True
    else:
        logger.error("❌ 部分测试失败，请检查修复实现")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)