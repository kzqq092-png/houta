#!/usr/bin/env python3
"""
简单的形态分析测试

绕过复杂的UI层，直接测试核心功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_simple_pattern_recognition():
    """测试简单的形态识别"""
    print("🧪 测试简单形态识别...")
    
    try:
        from analysis.pattern_recognition import EnhancedPatternRecognizer
        
        # 创建识别器
        recognizer = EnhancedPatternRecognizer(debug_mode=True)
        
        # 创建简单的K线数据
        dates = pd.date_range(start=datetime.now() - timedelta(days=20), periods=20, freq='D')
        
        # 创建一个明显的锤头线形态
        kdata = pd.DataFrame({
            'datetime': dates,
            'open': [10] * 20,
            'high': [11] * 20,
            'low': [8] * 20,  # 长下影线
            'close': [10.5] * 20,  # 小实体
            'volume': [1000000] * 20
        })
        
        # 在最后一天创建明显的锤头线
        kdata.loc[19, 'open'] = 10.0
        kdata.loc[19, 'high'] = 10.2
        kdata.loc[19, 'low'] = 8.5  # 很长的下影线
        kdata.loc[19, 'close'] = 10.1  # 小实体，接近开盘价
        
        print(f"创建测试数据: {len(kdata)} 条记录")
        print(f"最后一天K线: 开{kdata.iloc[-1]['open']} 高{kdata.iloc[-1]['high']} 低{kdata.iloc[-1]['low']} 收{kdata.iloc[-1]['close']}")
        
        # 执行识别
        patterns = recognizer.identify_patterns(kdata, confidence_threshold=0.1)
        
        print(f"\n识别结果: {len(patterns)} 个形态")
        for i, pattern in enumerate(patterns):
            print(f"  {i+1}. {pattern.get('pattern_type', 'Unknown')}: 置信度 {pattern.get('confidence', 0):.2f}")
            if pattern.get('signal_type'):
                print(f"      信号类型: {pattern.get('signal_type')}")
            if pattern.get('index') is not None:
                print(f"      位置: 第{pattern.get('index')}根K线")
        
        return len(patterns) > 0
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_pattern_recognition()
    if success:
        print("\n✅ 简单形态识别测试通过！")
    else:
        print("\n❌ 简单形态识别测试失败！")
