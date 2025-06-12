#!/usr/bin/env python3
"""
模式识别诊断测试脚本
用于诊断模式识别返回0个模式的问题
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_database_initialization():
    """测试数据库初始化"""
    print("=" * 50)
    print("1. 测试数据库初始化")
    print("=" * 50)

    # 初始化数据库
    from db.init_db import init_db
    try:
        init_db()
        print("✓ 数据库初始化成功")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        return False

    # 检查pattern_types表
    db_path = os.path.join('db', 'hikyuu_system.db')
    if not os.path.exists(db_path):
        print(f"✗ 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM pattern_types")
        count = cursor.fetchone()[0]
        print(f"✓ pattern_types表存在，包含 {count} 条记录")

        # 显示前几条记录
        cursor.execute("SELECT name, english_name, category, signal_type FROM pattern_types LIMIT 5")
        records = cursor.fetchall()
        print("前5条形态记录:")
        for record in records:
            print(f"  - {record[0]} ({record[1]}) - {record[2]} - {record[3]}")

    except Exception as e:
        print(f"✗ 查询pattern_types表失败: {e}")
        return False
    finally:
        conn.close()

    return True


def test_pattern_manager():
    """测试PatternManager"""
    print("\n" + "=" * 50)
    print("2. 测试PatternManager")
    print("=" * 50)

    try:
        from analysis.pattern_manager import PatternManager
        manager = PatternManager()
        print("✓ PatternManager初始化成功")

        # 测试获取配置
        configs = manager.get_pattern_configs()
        print(f"✓ 加载了 {len(configs)} 个形态配置")

        # 显示各类别统计
        categories = {}
        for config in configs:
            categories[config.category] = categories.get(config.category, 0) + 1

        print("形态类别统计:")
        for category, count in categories.items():
            print(f"  - {category}: {count} 个")

        return True, manager

    except Exception as e:
        print(f"✗ PatternManager测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def create_test_kdata():
    """创建测试K线数据"""
    print("\n" + "=" * 50)
    print("3. 创建测试K线数据")
    print("=" * 50)

    # 创建365天的模拟K线数据
    dates = pd.date_range(start='2023-01-01', periods=365, freq='D')

    # 生成模拟价格数据，包含一些明显的形态
    np.random.seed(42)  # 确保可重复

    base_price = 100
    prices = [base_price]

    # 生成有趋势的价格数据
    for i in range(1, 365):
        # 添加一些趋势和波动
        if i < 50:  # 上升趋势
            change = np.random.normal(0.5, 2)
        elif i < 100:  # 下降趋势
            change = np.random.normal(-0.3, 2)
        elif i < 150:  # 横盘整理
            change = np.random.normal(0, 1)
        elif i < 200:  # 再次上升
            change = np.random.normal(0.8, 2)
        else:  # 波动
            change = np.random.normal(0, 2)

        new_price = max(prices[-1] + change, 10)  # 价格不能为负
        prices.append(new_price)

    # 创建OHLC数据
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        # 生成开高低价
        volatility = abs(np.random.normal(0, 1))
        high = close + volatility
        low = close - volatility

        if i == 0:
            open_price = close
        else:
            open_price = prices[i-1] + np.random.normal(0, 0.5)

        # 确保价格关系正确
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        volume = np.random.randint(1000000, 10000000)
        amount = volume * close

        data.append({
            'datetime': date,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume,
            'amount': amount,
            'code': '000001'  # 添加code字段
        })

    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)

    print(f"✓ 创建了 {len(df)} 条K线数据")
    print(f"价格范围: {df['close'].min():.3f} - {df['close'].max():.3f}")
    print(f"数据时间范围: {df.index[0]} 到 {df.index[-1]}")

    return df


def test_pattern_recognition(manager, kdata):
    """测试模式识别"""
    print("\n" + "=" * 50)
    print("4. 测试模式识别")
    print("=" * 50)

    try:
        # 测试识别所有形态
        print("开始识别形态...")
        patterns = manager.identify_all_patterns(kdata, confidence_threshold=0.3)

        print(f"✓ 识别完成，共找到 {len(patterns)} 个形态")

        if patterns:
            # 统计各类型形态
            type_counts = {}
            signal_counts = {}
            confidence_levels = {'高': 0, '中': 0, '低': 0}

            for pattern in patterns:
                # 统计类型
                pattern_type = pattern.get('type', 'unknown')
                type_counts[pattern_type] = type_counts.get(pattern_type, 0) + 1

                # 统计信号
                signal = pattern.get('signal', 'unknown')
                signal_counts[signal] = signal_counts.get(signal, 0) + 1

                # 统计置信度
                confidence = pattern.get('confidence', 0)
                if confidence >= 0.8:
                    confidence_levels['高'] += 1
                elif confidence >= 0.5:
                    confidence_levels['中'] += 1
                else:
                    confidence_levels['低'] += 1

            print("\n形态类型统计:")
            for ptype, count in sorted(type_counts.items()):
                print(f"  - {ptype}: {count}")

            print("\n信号类型统计:")
            for signal, count in sorted(signal_counts.items()):
                print(f"  - {signal}: {count}")

            print("\n置信度分布:")
            for level, count in confidence_levels.items():
                print(f"  - {level}: {count}")

            # 显示前几个形态详情
            print("\n前5个识别的形态:")
            for i, pattern in enumerate(patterns[:5]):
                print(f"  {i+1}. {pattern.get('type', 'unknown')} - "
                      f"{pattern.get('signal', 'unknown')} - "
                      f"置信度: {pattern.get('confidence', 0):.3f} - "
                      f"位置: {pattern.get('index', 'unknown')}")
        else:
            print("⚠ 未识别到任何形态")

            # 尝试单独测试各个识别方法
            print("\n尝试单独测试识别方法:")

            from analysis.pattern_recognition import PatternRecognizer
            recognizer = PatternRecognizer()

            # 测试双顶双底
            try:
                double_patterns = recognizer.find_double_tops_bottoms(kdata)
                print(f"  - 双顶双底: {len(double_patterns)} 个")
            except Exception as e:
                print(f"  - 双顶双底识别失败: {e}")

            # 测试头肩形态
            try:
                hs_patterns = recognizer.find_head_shoulders(kdata)
                print(f"  - 头肩形态: {len(hs_patterns)} 个")
            except Exception as e:
                print(f"  - 头肩形态识别失败: {e}")

            # 测试三角形
            try:
                triangle_patterns = recognizer.find_triangles(kdata)
                print(f"  - 三角形态: {len(triangle_patterns)} 个")
            except Exception as e:
                print(f"  - 三角形态识别失败: {e}")

        return len(patterns) > 0

    except Exception as e:
        print(f"✗ 模式识别测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pattern_manager_methods(manager):
    """测试PatternManager的其他方法"""
    print("\n" + "=" * 50)
    print("5. 测试PatternManager其他方法")
    print("=" * 50)

    try:
        # 测试获取特定类别的形态
        reversal_patterns = manager.get_pattern_configs(category='反转形态')
        print(f"✓ 反转形态: {len(reversal_patterns)} 个")

        consolidation_patterns = manager.get_pattern_configs(category='整理形态')
        print(f"✓ 整理形态: {len(consolidation_patterns)} 个")

        # 测试获取特定信号类型的形态
        buy_patterns = manager.get_pattern_configs(signal_type='buy')
        sell_patterns = manager.get_pattern_configs(signal_type='sell')
        neutral_patterns = manager.get_pattern_configs(signal_type='neutral')

        print(f"✓ 买入信号形态: {len(buy_patterns)} 个")
        print(f"✓ 卖出信号形态: {len(sell_patterns)} 个")
        print(f"✓ 中性信号形态: {len(neutral_patterns)} 个")

        return True

    except Exception as e:
        print(f"✗ PatternManager方法测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("模式识别诊断测试开始")
    print("=" * 60)

    # 1. 测试数据库初始化
    if not test_database_initialization():
        print("\n❌ 数据库初始化测试失败，停止测试")
        return

    # 2. 测试PatternManager
    success, manager = test_pattern_manager()
    if not success:
        print("\n❌ PatternManager测试失败，停止测试")
        return

    # 3. 创建测试数据
    kdata = create_test_kdata()

    # 4. 测试模式识别
    recognition_success = test_pattern_recognition(manager, kdata)

    # 5. 测试其他方法
    methods_success = test_pattern_manager_methods(manager)

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if recognition_success and methods_success:
        print("✅ 所有测试通过！模式识别功能正常工作")
    else:
        print("❌ 部分测试失败，需要进一步调试")

        if not recognition_success:
            print("  - 模式识别功能存在问题")
        if not methods_success:
            print("  - PatternManager方法存在问题")


if __name__ == '__main__':
    main()
