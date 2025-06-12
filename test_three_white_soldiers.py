#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三白兵形态识别专项测试
验证三白兵形态识别功能是否正常工作
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from analysis.pattern_manager import PatternManager
    from analysis.pattern_base import PatternAlgorithmFactory
except ImportError as e:
    print(f"导入失败: {e}")
    sys.exit(1)


def create_three_white_soldiers_test_data():
    """创建包含三白兵形态的测试数据"""
    print("创建三白兵测试数据...")

    # 创建基础数据
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(42)

    # 初始化数据列表
    data = []
    base_price = 100.0

    for i in range(100):
        date = dates[i]

        if i >= 60 and i <= 62:
            # 第60-62天：构造三白兵形态
            if i == 60:
                # 第一根阳线
                open_price = base_price * 0.98
                close_price = base_price * 1.02
                high_price = close_price * 1.01
                low_price = open_price * 0.99
            elif i == 61:
                # 第二根阳线，开盘价在前一根实体内
                open_price = base_price * 1.01
                close_price = base_price * 1.05
                high_price = close_price * 1.01
                low_price = open_price * 0.99
            else:  # i == 62
                # 第三根阳线，开盘价在前一根实体内
                open_price = base_price * 1.04
                close_price = base_price * 1.08
                high_price = close_price * 1.01
                low_price = open_price * 0.99

            base_price = close_price
        else:
            # 其他时间：随机波动
            change = np.random.normal(0, 0.01)
            price = base_price * (1 + change)
            open_price = price * (1 + np.random.normal(0, 0.005))
            close_price = price * (1 + np.random.normal(0, 0.005))
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))

            base_price = close_price

        # 添加到数据列表
        data.append({
            'datetime': date,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': np.random.randint(1000, 10000)
        })

    # 创建DataFrame
    df = pd.DataFrame(data)

    print(f"✅ 测试数据创建完成，共{len(df)}条记录")
    print(f"↑ 预期三白兵形态位置：第60-62天")

    # 显示三白兵形态数据
    print("\n🔍 三白兵形态数据:")
    for i in range(60, 63):
        row = df.iloc[i]
        date_str = row['datetime'].strftime('%Y-%m-%d')
        is_bullish = row['close'] > row['open']
        body_size = abs(row['close'] - row['open'])
        print(
            f"  第{i+1}天 {date_str}: O={row['open']:.3f} H={row['high']:.3f} L={row['low']:.3f} C={row['close']:.3f} {'↑' if is_bullish else '↓'} 实体={body_size:.3f}")

    return df


def test_three_white_soldiers():
    """测试三白兵形态识别"""
    print("\n🔍 开始三白兵形态识别测试")
    print("=" * 60)

    try:
        # 创建测试数据
        test_data = create_three_white_soldiers_test_data()

        # 获取形态管理器
        manager = PatternManager()

        # 获取三白兵形态配置
        config = manager.get_pattern_by_name('three_white_soldiers')
        if not config:
            print("❌ 未找到三白兵形态配置")
            return False

        print(f"✅ 找到三白兵形态配置: {config.name}")
        print(f"📝 描述: {config.description}")
        print(f"信号类型: {config.signal_type}")
        print(f"置信度阈值: {config.confidence_threshold}")

        # 创建识别器
        recognizer = PatternAlgorithmFactory.create(config)
        if not recognizer:
            print("❌ 创建识别器失败")
            return False

        print("✅ 识别器创建成功")

        # 执行识别
        print("\n🔍 执行形态识别...")
        start_time = datetime.now()
        patterns = recognizer.recognize(test_data)
        end_time = datetime.now()

        execution_time = (end_time - start_time).total_seconds()
        print(f"⏱️  执行时间: {execution_time:.3f}秒")

        # 分析结果
        print(f"\n 识别结果:")
        print(f"🔢 识别到形态数量: {len(patterns)}")

        if patterns:
            print("\n📋 详细结果:")
            for i, pattern in enumerate(patterns, 1):
                print(f"  {i}. 位置: 第{pattern.index}天")
                print(f"     置信度: {pattern.confidence:.3f}")
                print(f"     信号类型: {pattern.signal_type}")
                print(f"     价格: {pattern.price:.3f}")

                # 显示相关K线数据
                if hasattr(pattern, 'start_index') and hasattr(pattern, 'end_index') and pattern.start_index is not None and pattern.end_index is not None:
                    pattern_data = test_data.iloc[pattern.start_index:pattern.end_index+1]
                    print(f"     K线数据:")
                    for idx, row in pattern_data.iterrows():
                        date_str = row['datetime'].strftime('%Y-%m-%d')
                        print(f"       {date_str}: O={row['open']:.3f} H={row['high']:.3f} L={row['low']:.3f} C={row['close']:.3f}")
                else:
                    # 如果没有start_index和end_index，显示单个位置的数据
                    if pattern.index < len(test_data):
                        row = test_data.iloc[pattern.index]
                        date_str = row['datetime'].strftime('%Y-%m-%d')
                        print(f"     K线数据: {date_str}: O={row['open']:.3f} H={row['high']:.3f} L={row['low']:.3f} C={row['close']:.3f}")
                print()
        else:
            print("⚠️  未识别到三白兵形态")

            # 检查预期位置的数据
            print("\n🔍 检查预期位置数据 (第60-62天):")
            expected_data = test_data.iloc[60:63]
            for idx, row in expected_data.iterrows():
                date_str = row['datetime'].strftime('%Y-%m-%d')
                is_bullish = row['close'] > row['open']
                body_size = abs(row['close'] - row['open'])
                print(
                    f"  {date_str}: O={row['open']:.3f} H={row['high']:.3f} L={row['low']:.3f} C={row['close']:.3f} {'↑' if is_bullish else '↓'} 实体={body_size:.3f}")

        return len(patterns) > 0

    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 三白兵形态识别专项测试")
    print("=" * 60)

    success = test_three_white_soldiers()

    print("\n" + "=" * 60)
    if success:
        print("✅ 测试成功！三白兵形态识别功能正常")
    else:
        print("❌ 测试失败！需要检查三白兵形态识别功能")

    return success


if __name__ == "__main__":
    main()
