#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TA-Lib指标完整性检查脚本
检查所有TA-Lib指标的输入参数需求，并与现有映射对比
"""

import talib
import inspect
from typing import Dict, List
import pandas as pd
import numpy as np

def get_all_talib_functions() -> List[str]:
    """获取所有TA-Lib函数列表"""
    # 获取talib模块中所有大写字母开头的函数（排除内部函数）
    all_functions = [name for name in dir(talib) if name.isupper() and callable(getattr(talib, name))]
    return sorted(all_functions)

def analyze_function_signature(func_name: str) -> Dict:
    """分析函数签名，获取输入参数需求"""
    try:
        func = getattr(talib, func_name)
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        # 判断需要哪些OHLCV输入
        required_inputs = []
        for param in params:
            param_lower = param.lower()
            # 跳过配置参数（包含period、length等关键词）
            if any(keyword in param_lower for keyword in ['period', 'length', 'time', 'nbdev', 'accel', 'maximum', 'minimum', 'fastk', 'slowk', 'slowd', 'fastd', 'matype']):
                continue

            # 匹配OHLCV数据
            if param_lower in ['real', 'inreal', 'real0', 'real1', 'price', 'prices']:
                if 'close' not in required_inputs:
                    required_inputs.append('close')
            elif 'high' in param_lower and 'high' not in required_inputs:
                required_inputs.append('high')
            elif 'low' in param_lower and 'low' not in required_inputs:
                required_inputs.append('low')
            elif 'close' in param_lower and 'close' not in required_inputs:
                required_inputs.append('close')
            elif 'open' in param_lower and 'open' not in required_inputs:
                required_inputs.append('open')
            elif 'volume' in param_lower and 'volume' not in required_inputs:
                required_inputs.append('volume')

        # 如果没有识别到输入，默认使用close
        if not required_inputs:
            required_inputs = ['close']

        return {
            'name': func_name,
            'required_inputs': required_inputs,
            'all_params': params
        }
    except Exception as e:
        return {
            'name': func_name,
            'required_inputs': ['close'],  # 默认
            'error': str(e)
        }

def get_current_mapping() -> Dict[str, List[str]]:
    """获取当前的input_mapping（从indicator_adapter.py复制）"""
    return {
        # 趋势类指标
        'MA': ['close'],
        'SMA': ['close'],
        'EMA': ['close'],
        'DEMA': ['close'],
        'TEMA': ['close'],
        'WMA': ['close'],
        'TRIMA': ['close'],
        'KAMA': ['close'],
        'MAMA': ['close'],
        'T3': ['close'],
        'MACD': ['close'],
        'MACDEXT': ['close'],
        'MACDFIX': ['close'],
        'SAR': ['high', 'low'],
        'SAREXT': ['high', 'low'],

        # 震荡类指标
        'RSI': ['close'],
        'STOCHRSI': ['close'],
        'STOCH': ['high', 'low', 'close'],
        'STOCHF': ['high', 'low', 'close'],
        'CCI': ['high', 'low', 'close'],
        'CMO': ['close'],
        'WILLR': ['high', 'low', 'close'],
        'ULTOSC': ['high', 'low', 'close'],
        'BOP': ['open', 'high', 'low', 'close'],
        'MOM': ['close'],
        'ROC': ['close'],
        'ROCP': ['close'],
        'ROCR': ['close'],
        'ROCR100': ['close'],
        'APO': ['close'],
        'PPO': ['close'],

        # 方向性指标
        'ADX': ['high', 'low', 'close'],
        'ADXR': ['high', 'low', 'close'],
        'DX': ['high', 'low', 'close'],
        'MINUS_DI': ['high', 'low', 'close'],
        'PLUS_DI': ['high', 'low', 'close'],
        'MINUS_DM': ['high', 'low'],
        'PLUS_DM': ['high', 'low'],

        # Aroon指标系列
        'AROON': ['high', 'low'],
        'AROONOSC': ['high', 'low'],

        # 布林带相关
        'BBANDS': ['close'],
        'BOLL': ['close'],

        # 成交量类指标
        'OBV': ['close', 'volume'],
        'AD': ['high', 'low', 'close', 'volume'],
        'ADOSC': ['high', 'low', 'close', 'volume'],
        'MFI': ['high', 'low', 'close', 'volume'],
        'CMF': ['high', 'low', 'close', 'volume'],

        # 波动性指标
        'ATR': ['high', 'low', 'close'],
        'NATR': ['high', 'low', 'close'],
        'TRANGE': ['high', 'low', 'close'],

        # KDJ随机指标
        'KDJ': ['high', 'low', 'close'],

        # 其他指标
        'TRIX': ['close'],
        'MESA': ['close'],

        # Hilbert Transform系列
        'HT_TRENDLINE': ['close'],
        'HT_SINE': ['close'],
        'HT_PHASOR': ['close'],
        'HT_DCPERIOD': ['close'],
        'HT_DCPHASE': ['close'],
        'HT_TRENDMODE': ['close'],

        # 统计函数
        'BETA': ['close'],
        'CORREL': ['close'],
        'LINEARREG': ['close'],
        'LINEARREG_ANGLE': ['close'],
        'LINEARREG_INTERCEPT': ['close'],
        'LINEARREG_SLOPE': ['close'],
        'STDDEV': ['close'],
        'TSF': ['close'],
        'VAR': ['close'],

        # 价格相关
        'AVGPRICE': ['open', 'high', 'low', 'close'],
        'MEDPRICE': ['high', 'low'],
        'MIDPOINT': ['close'],
        'MIDPRICE': ['high', 'low'],
        'TYPPRICE': ['high', 'low', 'close'],
        'WCLPRICE': ['high', 'low', 'close', 'volume'],
    }

def main():
    """主函数：全面检查TA-Lib指标"""
    print("=" * 80)
    print("TA-Lib指标完整性检查")
    print("=" * 80)

    # 获取所有TA-Lib函数
    all_functions = get_all_talib_functions()
    print(f"\n✅ 找到 {len(all_functions)} 个TA-Lib函数\n")

    # 获取当前映射
    current_mapping = get_current_mapping()
    print(f"✅ 当前input_mapping包含 {len(current_mapping)} 个指标\n")

    # 分析所有函数
    print("🔍 分析所有函数的输入需求...\n")
    analysis_results = {}
    for func_name in all_functions:
        result = analyze_function_signature(func_name)
        analysis_results[func_name] = result

    # 对比检查
    print("=" * 80)
    print("📊 对比结果")
    print("=" * 80)

    missing_indicators = []
    incorrect_mappings = []
    correct_mappings = []

    for func_name, analysis in analysis_results.items():
        if func_name in current_mapping:
            # 检查映射是否正确
            if set(current_mapping[func_name]) == set(analysis['required_inputs']):
                correct_mappings.append(func_name)
            else:
                incorrect_mappings.append({
                    'name': func_name,
                    'current': current_mapping[func_name],
                    'should_be': analysis['required_inputs']
                })
        else:
            missing_indicators.append({
                'name': func_name,
                'required_inputs': analysis['required_inputs']
            })

    # 输出结果
    print(f"\n✅ 映射正确的指标: {len(correct_mappings)} 个")

    if incorrect_mappings:
        print(f"\n⚠️  映射不正确的指标: {len(incorrect_mappings)} 个")
        for item in incorrect_mappings:
            print(f"   - {item['name']}: 当前={item['current']}, 应为={item['should_be']}")

    if missing_indicators:
        print(f"\n❌ 缺失的指标: {len(missing_indicators)} 个")
        print("\n以下指标需要添加到input_mapping:")
        print("-" * 80)

        # 按输入类型分组
        by_inputs = {}
        for item in missing_indicators:
            key = str(item['required_inputs'])
            if key not in by_inputs:
                by_inputs[key] = []
            by_inputs[key].append(item['name'])

        for inputs, names in sorted(by_inputs.items()):
            print(f"\n输入参数: {inputs}")
            for name in sorted(names):
                print(f"        '{name}': {inputs},")

    # 生成完整的映射代码
    if missing_indicators or incorrect_mappings:
        print("\n" + "=" * 80)
        print("📝 完整的input_mapping代码（包含所有指标）")
        print("=" * 80)

        # 合并所有指标
        complete_mapping = current_mapping.copy()
        for item in missing_indicators:
            complete_mapping[item['name']] = item['required_inputs']
        for item in incorrect_mappings:
            complete_mapping[item['name']] = item['should_be']

        # 按输入类型分组输出
        print("\n    input_mapping = {")

        # 分类输出
        categories = {
            '趋势类': [],
            '震荡类': [],
            '成交量类': [],
            '波动性类': [],
            '价格类': [],
            '统计类': [],
            '其他': []
        }

        for name, inputs in sorted(complete_mapping.items()):
            # 简单分类
            if 'volume' in inputs:
                categories['成交量类'].append((name, inputs))
            elif name.startswith(('MA', 'EMA', 'SMA', 'WMA', 'DEMA', 'TEMA', 'TRIMA', 'KAMA', 'T3')):
                categories['趋势类'].append((name, inputs))
            elif name.startswith(('RSI', 'STOCH', 'CCI', 'MOM', 'ROC', 'WILL')):
                categories['震荡类'].append((name, inputs))
            elif name in ['ATR', 'NATR', 'TRANGE']:
                categories['波动性类'].append((name, inputs))
            elif name.startswith(('AVG', 'MED', 'MID', 'TYP', 'WCL')):
                categories['价格类'].append((name, inputs))
            elif name.startswith(('BETA', 'CORREL', 'LINEAR', 'STD', 'VAR', 'TSF')):
                categories['统计类'].append((name, inputs))
            else:
                categories['其他'].append((name, inputs))

        for category, items in categories.items():
            if items:
                print(f"        # {category}")
                for name, inputs in sorted(items):
                    print(f"        '{name}': {inputs},")
                print()

        print("    }")
    else:
        print("\n🎉 所有指标映射都是正确的！")

    print("\n" + "=" * 80)
    print("检查完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()
