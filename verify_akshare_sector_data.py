#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证AKShare板块资金流数据质量
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def verify_akshare_sector_data():
    """验证AKShare板块资金流数据质量"""
    print("🔍 验证AKShare板块资金流数据质量")
    print("=" * 60)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        import akshare as ak
        import pandas as pd

        print("📊 获取AKShare板块资金流数据...")

        # 获取板块资金流排行数据
        data = ak.stock_sector_fund_flow_rank()

        if data is None or data.empty:
            print("❌ 未获取到数据")
            return False

        print(f"✅ 成功获取数据: {len(data)} 条记录")
        print(f"📋 数据列: {list(data.columns)}")
        print()

        # 数据质量检查
        print("🔍 数据质量检查:")

        # 检查必要的列
        required_columns = ['名称', '今日涨跌幅', '今日主力净流入-净额']
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            print(f"❌ 缺少必要列: {missing_columns}")
            return False
        else:
            print("✅ 包含所有必要列")

        # 检查数据完整性
        null_counts = data.isnull().sum()
        if null_counts.sum() > 0:
            print(f"⚠️ 存在空值: {null_counts[null_counts > 0].to_dict()}")
        else:
            print("✅ 数据完整，无空值")

        # 检查数值列的合理性
        numeric_columns = ['今日涨跌幅', '今日主力净流入-净额', '今日主力净流入-净占比']
        for col in numeric_columns:
            if col in data.columns:
                try:
                    # 尝试转换为数值
                    numeric_data = pd.to_numeric(data[col], errors='coerce')
                    valid_count = numeric_data.notna().sum()
                    print(f"✅ {col}: {valid_count}/{len(data)} 条有效数值")
                except Exception as e:
                    print(f"❌ {col}: 数值转换失败 - {e}")

        print()
        print("📋 数据样本:")
        print("-" * 40)

        # 显示前5条数据
        for idx, row in data.head(5).iterrows():
            name = row.get('名称', 'N/A')
            change_pct = row.get('今日涨跌幅', 'N/A')
            net_inflow = row.get('今日主力净流入-净额', 'N/A')
            print(f"{idx+1}. {name}")
            print(f"   涨跌幅: {change_pct}")
            print(f"   主力净流入: {net_inflow}")
            print()

        # 数据标准化测试
        print("🔄 数据标准化测试:")
        try:
            standardized_data = []
            for idx, row in data.iterrows():
                sector_info = {
                    'sector_code': f'AK_{idx+1:03d}',
                    'sector_name': str(row.get('名称', '')),
                    'change_percent': float(str(row.get('今日涨跌幅', 0)).replace('%', '')) if row.get('今日涨跌幅') else 0,
                    'main_net_inflow': float(row.get('今日主力净流入-净额', 0)) if row.get('今日主力净流入-净额') else 0,
                    'main_net_inflow_pct': float(str(row.get('今日主力净流入-净占比', 0)).replace('%', '')) if row.get('今日主力净流入-净占比') else 0,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'data_source': 'akshare'
                }
                standardized_data.append(sector_info)

            standardized_df = pd.DataFrame(standardized_data)
            print(f"✅ 数据标准化成功: {len(standardized_df)} 条记录")
            print(f"📊 标准化后的列: {list(standardized_df.columns)}")

            return True, data, standardized_df

        except Exception as e:
            print(f"❌ 数据标准化失败: {e}")
            return False, data, None

    except ImportError:
        print("❌ akshare库未安装")
        return False, None, None
    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


if __name__ == "__main__":
    success, raw_data, standardized_data = verify_akshare_sector_data()

    if success:
        print("🎉 AKShare板块资金流数据验证成功！")
        print("✅ 数据质量良好，可以创建AKShare插件")
    else:
        print("❌ AKShare板块资金流数据验证失败")

    sys.exit(0 if success else 1)
