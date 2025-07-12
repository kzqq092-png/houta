#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试数据生成器 - 为指标系统重构提供标准测试数据集
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def generate_ohlcv_data(n_days=100, filename='stock_data.csv', volatility=0.015):
    """
    生成模拟的股票OHLCV数据

    参数:
        n_days (int): 生成的天数
        filename (str): 保存的文件名
        volatility (float): 价格波动率

    返回:
        pandas.DataFrame: 生成的数据
    """
    # 设置随机种子以确保可重复性
    np.random.seed(42)

    # 生成日期序列
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=n_days + 30)  # 额外30天是为了排除周末和假日
    dates = pd.date_range(start=start_date, end=end_date,
                          freq='B')[:n_days]  # 'B'表示工作日

    # 生成初始价格和成交量
    initial_price = 100.0
    price = initial_price
    prices = []

    # 生成价格序列
    for _ in range(n_days):
        change = np.random.normal(0, volatility)
        price *= (1 + change)
        prices.append(price)

    # 生成OHLCV数据
    data = []
    for i, date in enumerate(dates):
        price = prices[i]

        # 生成当天的开盘、最高、最低和收盘价
        open_price = price * (1 + np.random.normal(0, volatility * 0.5))
        high_price = max(open_price, price) * \
            (1 + abs(np.random.normal(0, volatility * 0.5)))
        low_price = min(open_price, price) * \
            (1 - abs(np.random.normal(0, volatility * 0.5)))
        close_price = price

        # 生成成交量，与价格变动相关
        volume = int(np.random.gamma(shape=2.0, scale=50000)
                     * (1 + abs(change) * 10))

        data.append({
            'date': date,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })

    # 创建DataFrame
    df = pd.DataFrame(data)

    # 保存到CSV
    output_path = os.path.join(os.path.dirname(__file__), filename)
    df.to_csv(output_path, index=False)
    print(f"测试数据已保存到: {output_path}")

    return df


def generate_all_test_data():
    """生成所有测试数据集"""
    # 生成标准测试数据 - 100天
    standard_data = generate_ohlcv_data(
        n_days=100, filename='stock_data_100d.csv')

    # 生成长期测试数据 - 500天
    long_term_data = generate_ohlcv_data(
        n_days=500, filename='stock_data_500d.csv')

    # 生成高波动测试数据 - 100天
    volatile_data = generate_ohlcv_data(
        n_days=100, filename='stock_data_volatile.csv', volatility=0.03)

    return {
        'standard': standard_data,
        'long_term': long_term_data,
        'volatile': volatile_data
    }


if __name__ == "__main__":
    generate_all_test_data()
