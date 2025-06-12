#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锤头线形态识别专项测试
验证锤头线形态识别功能是否正常工作
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from analysis.pattern_manager import PatternManager
    from analysis.pattern_base import PatternAlgorithmFactory
except ImportError as e:
    print(f"导入失败: {e}")
    sys.exit(1)


def create_hammer_test_data():
    """创建包含锤头线形态的测试数据"""
    print("创建锤头线测试数据...")

    # 创建基础数据
    dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
    data = []

    for i, date in enumerate(dates):
        if i == 25:  # 在第25天注入明显的锤头线
            # 锤头线特征：长下影线，小实体，几乎没有上影线
            data.append({
                'datetime': date,
                'open': 100.0,
                'high': 100.5,    # 很小的上影线
                'low': 85.0,      # 长下影线
                'close': 99.0,    # 小实体
                'volume': 1000000
            })
        else:
            # 普通K线
            base_price = 100.0 + np.random.uniform(-2, 2)
            open_price = base_price
            close_price = base_price + np.random.uniform(-1, 1)
            high_price = max(open_price, close_price) + np.random.uniform(0, 0.5)
            low_price = min(open_price, close_price) - np.random.uniform(0, 0.5)

            data.append({
                'datetime': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': np.random.randint(800000, 1200000)
            })

    df = pd.DataFrame(data)
    print(f"✅ 测试数据创建完成，共{len(df)}条记录")
    print(f"↑ 预期锤头线形态位置：第25天")

    # 显示锤头线数据
    hammer_data = df.iloc[25]
    print(f"🔨 锤头线数据: O={hammer_data['open']:.3f} H={hammer_data['high']:.3f} L={hammer_data['low']:.3f} C={hammer_data['close']:.3f}")

    body_size = abs(hammer_data['close'] - hammer_data['open'])
    total_range = hammer_data['high'] - hammer_data['low']
    lower_shadow = min(hammer_data['open'], hammer_data['close']) - hammer_data['low']

    print(f"实体大小: {body_size:.3f}")
    print(f"总区间: {total_range:.3f}")
    print(f"下影线: {lower_shadow:.3f}")
    print(f"下影线比例: {lower_shadow/total_range:.3f}")

    return df


def test_hammer_pattern():
    """测试锤头线形态识别"""
    print("\n🔍 开始锤头线形态识别测试")
    print("=" * 60)

    try:
        # 创建测试数据
        test_data = create_hammer_test_data()

        # 获取形态管理器
        manager = PatternManager()

        # 获取锤头线形态配置
        config = manager.get_pattern_by_name('hammer')
        if not config:
            print("❌ 未找到锤头线形态配置")
            return False

        print(f"✅ 找到锤头线形态配置: {config.name}")
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
        print(f"\n识别结果:")
        print(f"🔢 识别到形态数量: {len(patterns)}")

        if patterns:
            print("\n📋 详细结果:")
            for i, pattern in enumerate(patterns, 1):
                print(f"  {i}. 位置: 第{pattern.index}天")
                print(f"     置信度: {pattern.confidence:.3f}")
                print(f"     信号类型: {pattern.signal_type}")
                print(f"     价格: {pattern.price:.3f}")

                # 显示相关K线数据
                if pattern.index < len(test_data):
                    k_data = test_data.iloc[pattern.index]
                    date_str = k_data['datetime'].strftime('%Y-%m-%d')
                    print(f"     日期: {date_str}")
                    print(f"     K线: O={k_data['open']:.3f} H={k_data['high']:.3f} L={k_data['low']:.3f} C={k_data['close']:.3f}")
                print()
        else:
            print("⚠️  未识别到锤头线形态")

        return len(patterns) > 0

    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 锤头线形态识别专项测试")
    print("=" * 60)

    success = test_hammer_pattern()

    print("\n" + "=" * 60)
    if success:
        print("✅ 测试成功！锤头线形态识别功能正常")
    else:
        print("❌ 测试失败！需要检查锤头线形态识别功能")

    return success


if __name__ == "__main__":
    main()
