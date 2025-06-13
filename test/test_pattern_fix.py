#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试形态识别修复
验证kdata变量作用域问题是否已解决
"""

import sys
import os
sys.path.append('.')

try:
    from analysis.pattern_base import GenericPatternRecognizer, PatternConfig, PatternCategory, SignalType
    import pandas as pd
    import numpy as np

    print("=== 形态识别修复测试 ===")

    # 创建测试数据
    test_data = pd.DataFrame({
        'datetime': pd.date_range('2023-01-01', periods=10, freq='D'),
        'open': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        'high': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        'low': [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        'close': [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5],
        'volume': [1000] * 10
    })

    print(f"测试数据创建成功，共 {len(test_data)} 行")

    # 创建测试配置 - 倒锤头形态
    config = PatternConfig(
        id=1,
        name='倒锤头',
        english_name='inverted_hammer',
        category=PatternCategory.SINGLE_CANDLE,
        signal_type=SignalType.BUY,
        description='倒锤头形态',
        min_periods=1,
        max_periods=1,
        confidence_threshold=0.6,
        algorithm_code='''
# 这是导致之前错误的代码：for i in range(len(kdata)):
for i in range(len(kdata)):
    if i > 0:
        current = kdata.iloc[i]
        results.append({
            'pattern_type': 'inverted_hammer',
            'signal_type': 'buy',
            'confidence': 0.8,
            'index': i,
            'price': current['close'],
            'datetime_val': str(current.name) if hasattr(current, 'name') else None
        })
        break
''',
        parameters={},
        is_active=True
    )

    print("测试配置创建成功")

    # 创建识别器并测试
    recognizer = GenericPatternRecognizer(config)
    print("识别器创建成功")

    # 执行识别
    results = recognizer.recognize(test_data)

    print(f'✅ 形态识别测试成功！识别到 {len(results)} 个形态')
    for result in results:
        print(f'  - {result.pattern_name}: {result.signal_type.value}, 置信度: {result.confidence}')

    # 测试更复杂的算法代码
    print("\n=== 测试复杂算法代码 ===")

    complex_config = PatternConfig(
        id=2,
        name='三白兵',
        english_name='three_white_soldiers',
        category=PatternCategory.TRIPLE_CANDLE,
        signal_type=SignalType.BUY,
        description='三白兵形态',
        min_periods=3,
        max_periods=3,
        confidence_threshold=0.7,
        algorithm_code='''
# 测试更复杂的kdata访问
for i in range(2, len(kdata)):
    if i >= 2:
        current = kdata.iloc[i]
        prev1 = kdata.iloc[i-1]
        prev2 = kdata.iloc[i-2]
        
        # 检查三根阳线
        if (current['close'] > current['open'] and
            prev1['close'] > prev1['open'] and
            prev2['close'] > prev2['open'] and
            current['close'] > prev1['close'] and
            prev1['close'] > prev2['close']):
            
            results.append({
                'pattern_type': 'three_white_soldiers',
                'signal_type': 'buy',
                'confidence': 0.9,
                'index': i,
                'price': current['close'],
                'datetime_val': str(current.name) if hasattr(current, 'name') else None,
                'start_index': i-2,
                'end_index': i
            })
''',
        parameters={},
        is_active=True
    )

    complex_recognizer = GenericPatternRecognizer(complex_config)
    complex_results = complex_recognizer.recognize(test_data)

    print(f'✅ 复杂算法测试成功！识别到 {len(complex_results)} 个形态')
    for result in complex_results:
        print(f'  - {result.pattern_name}: {result.signal_type.value}, 置信度: {result.confidence}')

    print("\n🎉 所有测试通过！kdata变量作用域问题已修复")

except Exception as e:
    print(f'❌ 形态识别测试失败: {e}')
    import traceback
    traceback.print_exc()
