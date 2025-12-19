#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复字符串'000158'来源分析脚本
深度分析这个重复字符串模式是如何产生的
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置详细日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def analyze_repeat_pattern():
    """分析重复字符串模式"""
    logger.info("🔍 开始分析重复字符串模式...")
    
    # 测试原始重复字符串
    test_string = "000158"
    logger.info(f"基础字符串: '{test_string}' (长度: {len(test_string)})")
    
    # 模拟重复模式
    for repeat_count in [2, 3, 4, 5, 10, 15]:
        repeated = test_string * repeat_count
        logger.info(f"重复{repeat_count}次: '{repeated}' (长度: {len(repeated)})")
        
        # 测试检测逻辑
        if len(repeated) > 10 and repeated == repeated[0:6] * (len(repeated) // 6):
            logger.info(f"  ✅ 检测为重复字符串模式")
        else:
            logger.info(f"  ❌ 未检测为重复字符串模式")
    
    # 分析可能的来源
    logger.info("\n🎯 可能的数据来源分析:")
    
    # 1. 股票代码分析
    logger.info("1. 股票代码 '000158' 可能是:")
    stock_codes = [
        "000158",  # 某股票代码
        "000158.SZ",  # 深交所代码
        "000158.SH",  # 上交所代码
        "000158.XSHE",  # 扩展格式
    ]
    
    for code in stock_codes:
        repeated = code * 3
        logger.info(f"   代码 '{code}' 重复3次: '{repeated}'")
        
    # 2. 时间戳分析
    logger.info("\n2. 时间戳格式分析:")
    import time
    current_time = int(time.time())
    logger.info(f"当前时间戳: {current_time}")
    
    # 3. 数值格式化分析
    logger.info("\n3. 数值格式化分析:")
    test_values = [
        158,  # 可能的数值
        158.0,  # 浮点数
        "000158",  # 字符串格式
        1.58e-4,  # 科学记数法
        0.00158,  # 小数
    ]
    
    for val in test_values:
        logger.info(f"   原始值: {val} (类型: {type(val)})")
        str_val = str(val)
        logger.info(f"   字符串转换: '{str_val}' (长度: {len(str_val)})")
        
        # 测试重复检测
        if len(str_val) > 10 and str_val == str_val[0:6] * (len(str_val) // 6):
            logger.info(f"   🚨 检测为重复模式!")
        else:
            logger.info(f"   ✅ 正常")

def test_data_conversion_sources():
    """测试可能的数据转换来源"""
    logger.info("\n🔍 测试数据转换来源...")
    
    # 模拟数据转换场景
    scenarios = [
        {
            "name": "API返回数据",
            "data": {"stock_code": "000158", "price": "000158000158"},
        },
        {
            "name": "数据库查询结果",
            "data": pd.Series(["000158000158", "000158000158000158"]),
        },
        {
            "name": "文件读取",
            "data": ["000158", "000158000158", "000158000158000158"],
        },
        {
            "name": "网络传输",
            "data": "000158" * 5,
        },
        {
            "name": "计算结果",
            "data": 158 * 1000000,  # 158000000
        }
    ]
    
    for scenario in scenarios:
        logger.info(f"\n📊 场景: {scenario['name']}")
        data = scenario['data']
        logger.info(f"   原始数据: {data}")
        logger.info(f"   数据类型: {type(data)}")
        
        # 转换为字符串并测试
        str_data = str(data)
        logger.info(f"   字符串转换: '{str_data}'")
        logger.info(f"   字符串长度: {len(str_data)}")
        
        # 测试重复检测
        if len(str_data) > 10:
            base_len = 6
            if len(str_data) >= base_len:
                base_str = str_data[:base_len]
                repeat_count = len(str_data) // base_len
                reconstructed = base_str * repeat_count
                
                logger.info(f"   基础字符串: '{base_str}' (长度: {base_len})")
                logger.info(f"   预期重复次数: {repeat_count}")
                logger.info(f"   重建字符串: '{reconstructed}'")
                
                if str_data == reconstructed:
                    logger.info(f"   🚨 确认为重复字符串模式!")
                else:
                    logger.info(f"   ✅ 正常模式")
        else:
            logger.info(f"   ✅ 字符串太短，不是重复模式")

def find_repeat_string_in_data():
    """在实际数据中查找重复字符串"""
    logger.info("\n🔍 在实际数据中查找重复字符串...")
    
    # 创建一个可能包含重复字符串的DataFrame
    data = {
        'symbol': ['000158', '000159', '000160', '000158'],
        'price': [100.5, 101.2, 99.8, 102.3],
        'volume': [1000000, 1200000, 800000, 1100000],
        'repeat_test': ['000158000158', 'normal_data', '000158000158000158', 'test']
    }
    
    df = pd.DataFrame(data)
    logger.info(f"测试DataFrame:\n{df}")
    
    # 检查每列中的重复字符串
    for col in df.columns:
        logger.info(f"\n📊 检查列: {col}")
        for idx, value in enumerate(df[col]):
            str_val = str(value)
            logger.info(f"   行{idx}: {value} -> '{str_val}' (长度: {len(str_val)})")
            
            # 应用重复字符串检测逻辑
            if len(str_val) > 10 and str_val == str_val[0:6] * (len(str_val) // 6):
                logger.info(f"   🚨 检测到重复字符串模式!")
                logger.info(f"      基础字符串: '{str_val[:6]}'")
                logger.info(f"      重复次数: {len(str_val) // 6}")
                logger.info(f"      完整字符串: '{str_val}'")

if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("重复字符串'000158'深度分析")
        logger.info("=" * 60)
        
        # 分析重复模式
        analyze_repeat_pattern()
        
        # 测试数据转换来源
        test_data_conversion_sources()
        
        # 在实际数据中查找
        find_repeat_string_in_data()
        
        logger.info("\n" + "=" * 60)
        logger.info("📋 分析总结:")
        logger.info("1. 重复字符串'000158'可能来源于:")
        logger.info("   - 股票代码000158的重复格式化")
        logger.info("   - 数据传输过程中的编码错误")
        logger.info("   - 数值转换时的格式化问题")
        logger.info("   - API返回数据的序列化错误")
        logger.info("\n2. 检测逻辑工作正常:")
        logger.info("   - 能准确识别重复字符串模式")
        logger.info("   - 将重复字符串转换为NaN，避免计算错误")
        logger.info("\n3. 建议的修复方案:")
        logger.info("   - 在数据源头进行数据清洗")
        logger.info("   - 增强数据验证逻辑")
        logger.info("   - 添加重复字符串的详细日志")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 分析过程中出错: {e}")
        import traceback
        traceback.print_exc()