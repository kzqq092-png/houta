#!/usr/bin/env python3
"""
测试单个形态识别
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def create_hammer_data():
    """创建包含明显锤头线形态的测试数据"""
    data = []
    dates = pd.date_range(start='2023-01-01', periods=10, freq='D')

    for i, date in enumerate(dates):
        if i == 5:  # 第6根K线设计为明显的锤头线
            data.append({
                'datetime': date,
                'open': 100.0,
                'high': 101.0,
                'low': 90.0,    # 长下影线
                'close': 99.0,  # 小实体，接近开盘价
                'volume': 1000000,
                'code': '000001'
            })
        else:
            # 普通K线
            base = 100.0
            data.append({
                'datetime': date,
                'open': base,
                'high': base + 2,
                'low': base - 2,
                'close': base + 1,
                'volume': 1000000,
                'code': '000001'
            })

    return pd.DataFrame(data)


def test_single_pattern():
    """测试单个形态识别"""
    try:
        from analysis.pattern_manager import PatternManager
        from analysis.pattern_base import GenericPatternRecognizer, PatternConfig, SignalType, PatternCategory

        print("测试单个形态识别")
        print("=" * 50)

        # 创建测试数据
        test_data = create_hammer_data()
        print(f"创建测试数据: {len(test_data)} 条K线")
        print("测试数据预览:")
        print(test_data[['datetime', 'open', 'high', 'low', 'close']])

        # 初始化管理器
        manager = PatternManager()

        # 获取hammer形态配置
        hammer_config = manager.get_pattern_by_name('hammer')
        if not hammer_config:
            print("❌ 未找到hammer形态配置")
            return False

        print(f"\n✅ 找到hammer形态配置:")
        print(f"  名称: {hammer_config.name}")
        print(f"  英文名: {hammer_config.english_name}")
        print(f"  类别: {hammer_config.category}")
        print(f"  信号类型: {hammer_config.signal_type}")
        print(f"  算法代码长度: {len(hammer_config.algorithm_code)} 字符")

        # 创建识别器
        recognizer = GenericPatternRecognizer(hammer_config)
        print(f"\n✅ 创建识别器成功")

        # 执行识别
        print(f"\n开始识别hammer形态...")
        results = recognizer.recognize(test_data)

        print(f"✅ 识别完成，发现 {len(results)} 个形态")

        if results:
            for i, result in enumerate(results):
                print(f"\n形态 {i+1}:")
                print(f"  类型: {result.pattern_type}")
                print(f"  名称: {result.pattern_name}")
                print(f"  信号: {result.signal_type.value}")
                print(f"  置信度: {result.confidence:.3f}")
                print(f"  位置: {result.index}")
                print(f"  价格: {result.price}")
                print(f"  时间: {result.datetime_val}")
                if result.extra_data:
                    print(f"  额外数据: {result.extra_data}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_algorithm_execution():
    """直接测试算法代码执行"""
    try:
        import sqlite3

        print("\n" + "=" * 50)
        print("直接测试算法代码执行")
        print("=" * 50)

        # 获取hammer算法代码
        conn = sqlite3.connect('db/hikyuu_system.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT algorithm_code FROM pattern_types WHERE english_name = 'hammer'")
        row = cursor.fetchone()
        conn.close()

        if not row:
            print("❌ 未找到hammer算法代码")
            return False

        algorithm_code = row[0]
        print(f"✅ 获取到算法代码，长度: {len(algorithm_code)} 字符")

        # 创建测试数据
        test_data = create_hammer_data()

        # 创建执行环境
        safe_globals = {
            'np': np,
            'pd': pd,
            'len': len,
            'abs': abs,
            'max': max,
            'min': min,
            'sum': sum,
            'range': range,
            'enumerate': enumerate,
        }

        # 导入必要的类型
        from analysis.pattern_base import SignalType, PatternResult
        safe_globals['SignalType'] = SignalType
        safe_globals['PatternResult'] = PatternResult

        # 模拟create_result函数
        def mock_create_result(pattern_type, signal_type, confidence, index, price, datetime_val=None, extra_data=None):
            return {
                'pattern_type': pattern_type,
                'signal_type': signal_type,
                'confidence': confidence,
                'index': index,
                'price': price,
                'datetime_val': datetime_val,
                'extra_data': extra_data
            }

        safe_locals = {
            'kdata': test_data,
            'results': [],
            'create_result': mock_create_result,
        }

        print("\n开始执行算法代码...")

        # 执行算法代码
        exec(algorithm_code, safe_globals, safe_locals)

        results = safe_locals.get('results', [])
        print(f"✅ 算法执行完成，发现 {len(results)} 个形态")

        if results:
            for i, result in enumerate(results):
                print(f"\n形态 {i+1}: {result}")

        return True

    except Exception as e:
        print(f"❌ 算法执行失败: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("单个形态识别测试")
    print("=" * 80)

    # 测试1: 通过PatternManager
    success1 = test_single_pattern()

    # 测试2: 直接执行算法代码
    success2 = test_algorithm_execution()

    print("\n" + "=" * 80)
    print("测试结果总结")
    print("=" * 80)
    print(f"PatternManager测试: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"算法代码直接执行: {'✅ 通过' if success2 else '❌ 失败'}")

    if success1 and success2:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，需要进一步调试。")
