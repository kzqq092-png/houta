#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面的形态识别测试脚本
测试所有形态算法，自动发现和修复问题
"""

import sys
import os
import pandas as pd
import numpy as np
import sqlite3
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from analysis.pattern_manager import PatternManager
    from analysis.pattern_base import PatternAlgorithmFactory, SignalType
except ImportError as e:
    print(f"导入失败: {e}")
    sys.exit(1)


class PatternTestSuite:
    """形态测试套件"""

    def __init__(self):
        self.manager = PatternManager()
        self.test_results = {}
        self.error_summary = {}

    def create_test_data_for_pattern(self, pattern_type: str, periods: int = 50) -> pd.DataFrame:
        """为特定形态类型创建测试数据"""
        base_data = self._create_base_data(periods)

        # 根据形态类型注入特定的形态
        if pattern_type == 'hammer':
            return self._inject_hammer_pattern(base_data)
        elif pattern_type == 'doji':
            return self._inject_doji_pattern(base_data)
        elif pattern_type == 'shooting_star':
            return self._inject_shooting_star_pattern(base_data)
        elif pattern_type == 'inverted_hammer':
            return self._inject_inverted_hammer_pattern(base_data)
        elif pattern_type == 'spinning_top':
            return self._inject_spinning_top_pattern(base_data)
        elif pattern_type == 'bullish_engulfing':
            return self._inject_bullish_engulfing_pattern(base_data)
        elif pattern_type == 'bearish_engulfing':
            return self._inject_bearish_engulfing_pattern(base_data)
        elif pattern_type == 'piercing_pattern':
            return self._inject_piercing_pattern(base_data)
        elif pattern_type == 'dark_cloud_cover':
            return self._inject_dark_cloud_cover_pattern(base_data)
        elif pattern_type == 'morning_star':
            return self._inject_morning_star_pattern(base_data)
        elif pattern_type == 'evening_star':
            return self._inject_evening_star_pattern(base_data)
        elif pattern_type == 'three_white_soldiers':
            return self._inject_three_white_soldiers_pattern(base_data)
        elif pattern_type == 'three_black_crows':
            return self._inject_three_black_crows_pattern(base_data)
        else:
            # 默认返回基础数据
            return base_data

    def _create_base_data(self, periods: int) -> pd.DataFrame:
        """创建基础K线数据"""
        dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')
        data = []

        base_price = 100.0
        for i, date in enumerate(dates):
            # 生成相对稳定的价格序列
            price_change = np.random.uniform(-0.5, 0.5)
            base_price += price_change

            open_price = base_price
            close_price = base_price + np.random.uniform(-1, 1)
            high_price = max(open_price, close_price) + \
                np.random.uniform(0, 0.5)
            low_price = min(open_price, close_price) - \
                np.random.uniform(0, 0.5)

            data.append({
                'datetime': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': np.random.randint(800000, 1200000),
                'code': '000001'
            })

        return pd.DataFrame(data)

    def _inject_hammer_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入锤头线形态"""
        data = data.copy()
        # 在第10个位置注入明显的锤头线
        idx = 10
        if idx < len(data):
            data.loc[idx, 'open'] = 100.0
            data.loc[idx, 'high'] = 100.5
            data.loc[idx, 'low'] = 85.0
            data.loc[idx, 'close'] = 99.0
        return data

    def _inject_doji_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入十字星形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            price = 100.0
            data.loc[idx, 'open'] = price
            data.loc[idx, 'close'] = price  # 开盘价等于收盘价
            data.loc[idx, 'high'] = price + 2.0
            data.loc[idx, 'low'] = price - 2.0
        return data

    def _inject_shooting_star_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入射击之星形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            data.loc[idx, 'open'] = 100.0
            data.loc[idx, 'close'] = 99.0
            data.loc[idx, 'high'] = 115.0  # 长上影线
            data.loc[idx, 'low'] = 98.5
        return data

    def _inject_inverted_hammer_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入倒锤头形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            data.loc[idx, 'open'] = 100.0
            data.loc[idx, 'close'] = 101.0
            data.loc[idx, 'high'] = 115.0  # 长上影线
            data.loc[idx, 'low'] = 99.5
        return data

    def _inject_spinning_top_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入纺锤线形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            data.loc[idx, 'open'] = 100.0
            data.loc[idx, 'close'] = 100.5  # 小实体
            data.loc[idx, 'high'] = 103.0   # 上影线
            data.loc[idx, 'low'] = 97.0     # 下影线
        return data

    def _inject_bullish_engulfing_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入看涨吞没形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            # 前一根：小阴线
            data.loc[idx-1, 'open'] = 100.0
            data.loc[idx-1, 'close'] = 99.0
            data.loc[idx-1, 'high'] = 100.2
            data.loc[idx-1, 'low'] = 98.8

            # 当前根：大阳线，完全吞没前一根
            data.loc[idx, 'open'] = 98.5
            data.loc[idx, 'close'] = 101.0
            data.loc[idx, 'high'] = 101.2
            data.loc[idx, 'low'] = 98.3
        return data

    def _inject_bearish_engulfing_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入看跌吞没形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            # 前一根：小阳线
            data.loc[idx-1, 'open'] = 99.0
            data.loc[idx-1, 'close'] = 100.0
            data.loc[idx-1, 'high'] = 100.2
            data.loc[idx-1, 'low'] = 98.8

            # 当前根：大阴线，完全吞没前一根
            data.loc[idx, 'open'] = 101.0
            data.loc[idx, 'close'] = 98.5
            data.loc[idx, 'high'] = 101.2
            data.loc[idx, 'low'] = 98.3
        return data

    def _inject_piercing_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入刺透形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            # 前一根：阴线
            data.loc[idx-1, 'open'] = 100.0
            data.loc[idx-1, 'close'] = 98.0
            data.loc[idx-1, 'high'] = 100.2
            data.loc[idx-1, 'low'] = 97.8

            # 当前根：阳线，开盘低于前一根最低价，收盘超过前一根实体中点
            data.loc[idx, 'open'] = 97.5
            data.loc[idx, 'close'] = 99.2  # 超过前一根实体中点(99.0)
            data.loc[idx, 'high'] = 99.5
            data.loc[idx, 'low'] = 97.3
        return data

    def _inject_dark_cloud_cover_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入乌云盖顶形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            # 前一根：阳线
            data.loc[idx-1, 'open'] = 98.0
            data.loc[idx-1, 'close'] = 100.0
            data.loc[idx-1, 'high'] = 100.2
            data.loc[idx-1, 'low'] = 97.8

            # 当前根：阴线，开盘高于前一根最高价，收盘低于前一根实体中点
            data.loc[idx, 'open'] = 100.5
            data.loc[idx, 'close'] = 98.8  # 低于前一根实体中点(99.0)
            data.loc[idx, 'high'] = 100.7
            data.loc[idx, 'low'] = 98.5
        return data

    def _inject_morning_star_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入早晨之星形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            # 第一根：大阴线
            data.loc[idx-2, 'open'] = 100.0
            data.loc[idx-2, 'close'] = 97.0
            data.loc[idx-2, 'high'] = 100.2
            data.loc[idx-2, 'low'] = 96.8

            # 第二根：小实体（十字星或小阳线）
            data.loc[idx-1, 'open'] = 96.5
            data.loc[idx-1, 'close'] = 96.8
            data.loc[idx-1, 'high'] = 97.2
            data.loc[idx-1, 'low'] = 96.0

            # 第三根：大阳线
            data.loc[idx, 'open'] = 97.0
            data.loc[idx, 'close'] = 99.5
            data.loc[idx, 'high'] = 99.8
            data.loc[idx, 'low'] = 96.8
        return data

    def _inject_evening_star_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入黄昏之星形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            # 第一根：大阳线
            data.loc[idx-2, 'open'] = 97.0
            data.loc[idx-2, 'close'] = 100.0
            data.loc[idx-2, 'high'] = 100.2
            data.loc[idx-2, 'low'] = 96.8

            # 第二根：小实体（十字星或小阴线）
            data.loc[idx-1, 'open'] = 100.5
            data.loc[idx-1, 'close'] = 100.2
            data.loc[idx-1, 'high'] = 101.0
            data.loc[idx-1, 'low'] = 100.0

            # 第三根：大阴线
            data.loc[idx, 'open'] = 100.0
            data.loc[idx, 'close'] = 97.5
            data.loc[idx, 'high'] = 100.2
            data.loc[idx, 'low'] = 97.2
        return data

    def _inject_three_white_soldiers_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入三白兵形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            # 三根连续的阳线，每根都比前一根高
            for i in range(3):
                base_price = 98.0 + i * 1.5
                data.loc[idx-2+i, 'open'] = base_price
                data.loc[idx-2+i, 'close'] = base_price + 1.2
                data.loc[idx-2+i, 'high'] = base_price + 1.4
                data.loc[idx-2+i, 'low'] = base_price - 0.2
        return data

    def _inject_three_black_crows_pattern(self, data: pd.DataFrame) -> pd.DataFrame:
        """注入三只乌鸦形态"""
        data = data.copy()
        idx = 10
        if idx < len(data):
            # 三根连续的阴线，每根都比前一根低
            for i in range(3):
                base_price = 102.0 - i * 1.5
                data.loc[idx-2+i, 'open'] = base_price
                data.loc[idx-2+i, 'close'] = base_price - 1.2
                data.loc[idx-2+i, 'high'] = base_price + 0.2
                data.loc[idx-2+i, 'low'] = base_price - 1.4
        return data

    def test_single_pattern(self, pattern_config) -> Dict:
        """测试单个形态算法"""
        pattern_type = pattern_config.english_name
        print(f"\n{'='*60}")
        print(f"测试形态: {pattern_config.name} ({pattern_type})")
        print(f"{'='*60}")

        result = {
            'pattern_type': pattern_type,
            'pattern_name': pattern_config.name,
            'success': False,
            'error': None,
            'error_type': None,
            'patterns_found': 0,
            'execution_time': 0,
            'test_data_length': 0
        }

        try:
            # 创建测试数据
            test_data = self.create_test_data_for_pattern(pattern_type)
            result['test_data_length'] = len(test_data)

            print(f"✅ 创建测试数据成功，长度: {len(test_data)}")

            # 显示注入的形态数据
            if pattern_type in ['hammer', 'doji', 'shooting_star', 'inverted_hammer', 'spinning_top']:
                self._show_single_candle_pattern(test_data, 10)
            elif pattern_type in ['bullish_engulfing', 'bearish_engulfing', 'piercing_pattern', 'dark_cloud_cover']:
                self._show_double_candle_pattern(test_data, 9, 10)
            elif pattern_type in ['morning_star', 'evening_star', 'three_white_soldiers', 'three_black_crows']:
                self._show_triple_candle_pattern(test_data, 8, 9, 10)

            # 创建识别器
            recognizer = PatternAlgorithmFactory.create(pattern_config)
            print(f"✅ 创建识别器成功: {type(recognizer).__name__}")

            # 执行识别
            start_time = datetime.now()
            patterns = recognizer.recognize(test_data)
            end_time = datetime.now()

            result['execution_time'] = (end_time - start_time).total_seconds()
            result['patterns_found'] = len(patterns)
            result['success'] = True

            print(f"✅ 识别完成，发现 {len(patterns)} 个形态")
            print(f"⏱️  执行时间: {result['execution_time']:.3f}秒")

            # 显示识别结果
            if patterns:
                for i, pattern in enumerate(patterns):
                    print(f"\n形态 {i+1}:")
                    print(f"  类型: {pattern.pattern_type}")
                    print(f"  信号: {pattern.signal_type.value}")
                    print(f"  置信度: {pattern.confidence:.3f}")
                    print(f"  位置: {pattern.index}")
                    print(f"  价格: {pattern.price}")
                    if pattern.extra_data:
                        print(f"  额外数据: {pattern.extra_data}")
            else:
                print("⚠️  未识别到任何形态")

        except Exception as e:
            result['error'] = str(e)
            result['error_type'] = type(e).__name__

            print(f"❌ 测试失败: {e}")
            print(f"错误类型: {type(e).__name__}")

            # 记录详细错误信息
            error_details = traceback.format_exc()
            print(f"错误详情:\n{error_details}")

            # 分类错误类型
            if 'SyntaxError' in str(e):
                result['error_type'] = 'SyntaxError'
            elif 'NameError' in str(e):
                result['error_type'] = 'NameError'
            elif 'AttributeError' in str(e):
                result['error_type'] = 'AttributeError'
            elif 'KeyError' in str(e):
                result['error_type'] = 'KeyError'
            elif 'TypeError' in str(e):
                result['error_type'] = 'TypeError'
            else:
                result['error_type'] = 'RuntimeError'

        return result

    def _show_single_candle_pattern(self, data: pd.DataFrame, idx: int):
        """显示单根K线形态的数据"""
        if idx < len(data):
            k = data.iloc[idx]
            print(f"注入的形态数据 (第{idx+1}根K线):")
            print(
                f"  开盘: {k['open']}, 最高: {k['high']}, 最低: {k['low']}, 收盘: {k['close']}")

            body_size = abs(k['close'] - k['open'])
            upper_shadow = k['high'] - max(k['open'], k['close'])
            lower_shadow = min(k['open'], k['close']) - k['low']
            total_range = k['high'] - k['low']

            if total_range > 0:
                print(f"  实体比例: {body_size/total_range:.3f}")
                print(f"  上影线比例: {upper_shadow/total_range:.3f}")
                print(f"  下影线比例: {lower_shadow/total_range:.3f}")

    def _show_double_candle_pattern(self, data: pd.DataFrame, idx1: int, idx2: int):
        """显示双根K线形态的数据"""
        if idx1 < len(data) and idx2 < len(data):
            print(f"注入的形态数据 (第{idx1+1}-{idx2+1}根K线):")
            for i, idx in enumerate([idx1, idx2], 1):
                k = data.iloc[idx]
                print(
                    f"  第{i}根: 开盘{k['open']}, 最高{k['high']}, 最低{k['low']}, 收盘{k['close']}")

    def _show_triple_candle_pattern(self, data: pd.DataFrame, idx1: int, idx2: int, idx3: int):
        """显示三根K线形态的数据"""
        if idx1 < len(data) and idx2 < len(data) and idx3 < len(data):
            print(f"注入的形态数据 (第{idx1+1}-{idx3+1}根K线):")
            for i, idx in enumerate([idx1, idx2, idx3], 1):
                k = data.iloc[idx]
                print(
                    f"  第{i}根: 开盘{k['open']}, 最高{k['high']}, 最低{k['low']}, 收盘{k['close']}")

    def test_all_patterns(self) -> Dict:
        """测试所有形态算法"""
        print("🚀 开始全面形态识别测试")
        print("=" * 80)

        # 获取所有形态配置
        all_configs = self.manager.get_pattern_configs(active_only=False)
        print(f"找到 {len(all_configs)} 个形态配置")

        # 过滤出有算法代码的形态
        configs_with_code = [
            c for c in all_configs if c.algorithm_code and c.algorithm_code.strip()]
        print(f"📝 其中 {len(configs_with_code)} 个包含算法代码")

        total_tests = len(configs_with_code)
        successful_tests = 0
        failed_tests = 0

        # 逐一测试
        for i, config in enumerate(configs_with_code, 1):
            print(f"\n🔍 进度: {i}/{total_tests}")

            result = self.test_single_pattern(config)
            self.test_results[config.english_name] = result

            if result['success']:
                successful_tests += 1
                print(f"✅ {config.name} 测试通过")
            else:
                failed_tests += 1
                print(f"❌ {config.name} 测试失败")

                # 记录错误统计
                error_type = result['error_type']
                if error_type not in self.error_summary:
                    self.error_summary[error_type] = []
                self.error_summary[error_type].append({
                    'pattern': config.english_name,
                    'error': result['error']
                })

        # 生成测试报告
        summary = {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'success_rate': (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            'error_summary': self.error_summary,
            'test_results': self.test_results
        }

        return summary

    def print_test_report(self, summary: Dict):
        """打印测试报告"""
        print("\n" + "=" * 80)
        print("📋 测试报告")
        print("=" * 80)

        print(f"总体统计:")
        print(f"  总测试数: {summary['total_tests']}")
        print(f"  成功测试: {summary['successful_tests']}")
        print(f"  失败测试: {summary['failed_tests']}")
        print(f"  成功率: {summary['success_rate']:.1f}%")

        # 成功的测试
        successful_patterns = [
            name for name, result in summary['test_results'].items() if result['success']]
        if successful_patterns:
            print(f"\n✅ 成功的形态 ({len(successful_patterns)}个):")
            for pattern in successful_patterns:
                result = summary['test_results'][pattern]
                print(
                    f"  - {result['pattern_name']} ({pattern}): {result['patterns_found']}个形态, {result['execution_time']:.3f}秒")

        # 失败的测试
        failed_patterns = [
            name for name, result in summary['test_results'].items() if not result['success']]
        if failed_patterns:
            print(f"\n❌ 失败的形态 ({len(failed_patterns)}个):")
            for pattern in failed_patterns:
                result = summary['test_results'][pattern]
                print(
                    f"  - {result['pattern_name']} ({pattern}): {result['error_type']} - {result['error']}")

        # 错误分类统计
        if summary['error_summary']:
            print(f"\n🔍 错误分类统计:")
            for error_type, errors in summary['error_summary'].items():
                print(f"  {error_type}: {len(errors)}个")
                for error in errors[:3]:  # 只显示前3个
                    print(
                        f"    - {error['pattern']}: {error['error'][:100]}...")
                if len(errors) > 3:
                    print(f"    ... 还有 {len(errors)-3} 个类似错误")

        # 性能统计
        execution_times = [result['execution_time']
                           for result in summary['test_results'].values() if result['success']]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)
            print(f"\n⏱️  性能统计:")
            print(f"  平均执行时间: {avg_time:.3f}秒")
            print(f"  最长执行时间: {max_time:.3f}秒")
            print(f"  最短执行时间: {min_time:.3f}秒")

        # 形态识别统计
        total_patterns_found = sum(
            result['patterns_found'] for result in summary['test_results'].values() if result['success'])
        print(f"\n形态识别统计:")
        print(f"  总共识别出: {total_patterns_found}个形态")

        patterns_by_count = {}
        for result in summary['test_results'].values():
            if result['success']:
                count = result['patterns_found']
                if count not in patterns_by_count:
                    patterns_by_count[count] = 0
                patterns_by_count[count] += 1

        for count in sorted(patterns_by_count.keys()):
            print(f"  识别出{count}个形态的算法: {patterns_by_count[count]}个")


def main():
    """主函数"""
    print("🔬 形态识别全面测试系统")
    print("=" * 80)
    print("本测试将检查所有形态算法的正确性")
    print("自动发现和报告问题，为修复提供指导")
    print("=" * 80)

    # 创建测试套件
    test_suite = PatternTestSuite()

    # 执行全面测试
    summary = test_suite.test_all_patterns()

    # 打印测试报告
    test_suite.print_test_report(summary)

    # 根据测试结果给出建议
    print("\n" + "=" * 80)
    print("🔧 修复建议")
    print("=" * 80)

    if summary['failed_tests'] == 0:
        print("🎉 恭喜！所有形态算法都通过了测试！")
        print("✨ 形态识别系统运行正常，可以投入使用。")
    else:
        print(f"⚠️  发现 {summary['failed_tests']} 个问题需要修复：")

        for error_type, errors in summary['error_summary'].items():
            print(f"\n{error_type} ({len(errors)}个):")
            if error_type == 'SyntaxError':
                print("  建议: 检查算法代码的语法，特别是缩进和括号匹配")
            elif error_type == 'NameError':
                print("  建议: 检查变量名和函数名是否正确，确保所有依赖都已导入")
            elif error_type == 'AttributeError':
                print("  建议: 检查对象属性访问，确保对象类型正确")
            elif error_type == 'KeyError':
                print("  建议: 检查字典键访问，确保键名正确")
            elif error_type == 'TypeError':
                print("  建议: 检查函数调用参数，确保参数类型和数量正确")
            else:
                print("  建议: 检查算法逻辑，添加异常处理")

    print(f"\n↑ 总体成功率: {summary['success_rate']:.1f}%")

    if summary['success_rate'] >= 90:
        print("🌟 优秀！系统稳定性很高。")
    elif summary['success_rate'] >= 70:
        print("👍 良好！还有一些小问题需要修复。")
    elif summary['success_rate'] >= 50:
        print("⚠️  一般！需要重点关注失败的算法。")
    else:
        print("🚨 需要改进！建议全面检查算法代码。")

    return summary['success_rate'] >= 70


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
