#!/usr/bin/env python
"""
形态识别修复验证脚本
测试修复后的形态识别功能是否正常
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback


def create_test_data():
    """创建测试用的K线数据"""
    # 生成日期序列
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')

    # 创建测试数据
    data = {
        'open': np.random.uniform(10, 20, 100),
        'high': np.random.uniform(12, 22, 100),
        'low': np.random.uniform(9, 19, 100),
        'close': np.random.uniform(10, 20, 100),
        'volume': np.random.uniform(1000, 10000, 100)
    }

    # 确保high >= max(open, close)，low <= min(open, close)
    for i in range(100):
        data['high'][i] = max(data['open'][i], data['close'][i], data['high'][i])
        data['low'][i] = min(data['open'][i], data['close'][i], data['low'][i])

    # 创建DataFrame
    df = pd.DataFrame(data, index=dates)

    # 添加常见的形态模式
    # 1. 三白兵 - 连续三根阳线
    for i in range(50, 53):
        df.loc[df.index[i], 'open'] = 15.0
        df.loc[df.index[i], 'close'] = 17.0 + (i - 50) * 0.5
        df.loc[df.index[i], 'high'] = df.loc[df.index[i], 'close'] + 0.3
        df.loc[df.index[i], 'low'] = df.loc[df.index[i], 'open'] - 0.3

    # 2. 锤子线
    df.loc[df.index[60], 'open'] = 16.0
    df.loc[df.index[60], 'close'] = 16.2
    df.loc[df.index[60], 'high'] = 16.3
    df.loc[df.index[60], 'low'] = 14.5

    # 3. 看涨吞没
    df.loc[df.index[70], 'open'] = 17.0
    df.loc[df.index[70], 'close'] = 16.0
    df.loc[df.index[70], 'high'] = 17.2
    df.loc[df.index[70], 'low'] = 15.8

    df.loc[df.index[71], 'open'] = 15.8
    df.loc[df.index[71], 'close'] = 17.3
    df.loc[df.index[71], 'high'] = 17.5
    df.loc[df.index[71], 'low'] = 15.6

    return df


def test_pattern_recognition():
    """测试形态识别功能"""
    print("开始测试形态识别功能...")

    try:
        # 导入形态识别器
        from analysis.pattern_recognition import EnhancedPatternRecognizer

        # 创建测试数据
        test_data = create_test_data()
        print(f"创建了测试数据，长度: {len(test_data)}")

        # 创建形态识别器
        recognizer = EnhancedPatternRecognizer(debug_mode=True)
        print("形态识别器创建成功")

        # 执行形态识别
        patterns = recognizer.identify_patterns(test_data, confidence_threshold=0.3)
        print(f"识别到 {len(patterns)} 个形态")

        # 检查结果
        if not patterns:
            print("警告: 没有识别到形态")
        else:
            # 查看形态类型和数量
            pattern_types = {}
            pattern_indices = set()

            for pattern in patterns:
                # 收集形态类型
                pattern_type = pattern.get('pattern_name', pattern.get('type', 'unknown'))
                pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1

                # 收集索引值
                idx = pattern.get('index', -1)
                pattern_indices.add(idx)

                # 检查必要字段是否存在
                required_fields = ['pattern_name', 'type', 'confidence', 'signal', 'index']
                missing_fields = [f for f in required_fields if f not in pattern or pattern[f] is None]
                if missing_fields:
                    print(f"警告: 形态缺少必要字段 {missing_fields}: {pattern}")

            # 输出形态类型统计
            print("\n形态类型统计:")
            for pattern_type, count in pattern_types.items():
                print(f"  {pattern_type}: {count}个")

            # 检查是否有重复
            if len(pattern_indices) < len(patterns):
                print(f"警告: 检测到重复形态! 索引数: {len(pattern_indices)}, 形态数: {len(patterns)}")

            # 输出示例形态
            print("\n形态示例:")
            for i, pattern in enumerate(patterns[:3]):
                print(f"形态 {i+1}: {pattern}")

        print("\n形态识别测试完成")
        return patterns

    except Exception as e:
        print(f"测试失败: {e}")
        print(traceback.format_exc())
        return []


if __name__ == "__main__":
    # 执行测试
    test_pattern_recognition()
