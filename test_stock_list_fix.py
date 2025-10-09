#!/usr/bin/env python3
"""
测试股票列表获取修复效果
"""

import sys
import os
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_stock_list_retrieval():
    """测试股票列表获取"""
    print("🧪 测试股票列表获取修复效果")
    print("=" * 50)

    try:
        # 导入必要的模块
        from core.services.unified_data_manager import UnifiedDataManager
        from core.containers import get_service_container

        print("📦 正在获取服务容器...")
        container = get_service_container()

        print("🚀 引导服务...")
        from core.services.service_bootstrap import bootstrap_services
        bootstrap_success = bootstrap_services()
        if not bootstrap_success:
            print("❌ 服务引导失败")
            return False

        print("🔍 正在获取统一数据管理器...")
        data_manager = container.resolve(UnifiedDataManager)

        if not data_manager:
            print("❌ 无法获取统一数据管理器")
            return False

        print("🚀 测试股票列表获取...")

        # 测试获取股票列表
        start_time = time.time()
        stock_list = data_manager.get_stock_list()
        end_time = time.time()

        print(f"⏱️ 获取耗时: {end_time - start_time:.2f}秒")

        if stock_list is not None and not stock_list.empty:
            print(f"✅ 股票列表获取成功!")
            print(f"📊 股票数量: {len(stock_list)}")
            print(f"📋 列名: {list(stock_list.columns)}")
            print("\n前5条记录:")
            print(stock_list.head())
            return True
        else:
            print("❌ 股票列表为空或获取失败")
            return False

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_log_for_improvements():
    """检查日志中的改进情况"""
    print("\n🔍 检查日志中的改进情况")
    print("=" * 50)

    try:
        log_file = f"logs/factorweave_{datetime.now().strftime('%Y-%m-%d')}.log"

        if not os.path.exists(log_file):
            print("❌ 日志文件不存在")
            return

        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键改进指标
        improvements = {
            "DuckDB优先获取": "优先从DuckDB数据库获取股票列表" in content,
            "TET框架回退": "回退到TET框架" in content or "回退到UniPluginDataManager" in content,
            "质量不合格错误": "数据质量不合格: 0.0" in content,
            "TET故障转移失败": "TET故障转移失败" in content,
            "DuckDB获取成功": "DuckDB数据库获取股票列表成功" in content or "DuckDB获取股票列表成功" in content
        }

        print("📊 改进情况统计:")
        for key, found in improvements.items():
            status = "✅ 发现" if found else "❌ 未发现"
            print(f"   {key}: {status}")

        # 统计改进效果
        positive_indicators = ["DuckDB优先获取", "TET框架回退", "DuckDB获取成功"]
        negative_indicators = ["质量不合格错误", "TET故障转移失败"]

        positive_count = sum(1 for key in positive_indicators if improvements.get(key, False))
        negative_count = sum(1 for key in negative_indicators if improvements.get(key, False))

        print(f"\n📈 改进效果评估:")
        print(f"   正面指标: {positive_count}/{len(positive_indicators)}")
        print(f"   负面指标: {negative_count}/{len(negative_indicators)}")

        if positive_count > 0 and negative_count == 0:
            print("🎉 修复效果优秀！")
        elif positive_count > negative_count:
            print("✅ 修复效果良好！")
        elif negative_count == 0:
            print("🔄 修复效果一般，但没有错误")
        else:
            print("⚠️ 仍有问题需要解决")

    except Exception as e:
        print(f"❌ 检查日志时发生错误: {e}")


def main():
    """主函数"""
    print("HIkyuu-UI 股票列表获取修复效果测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 测试股票列表获取
    success = test_stock_list_retrieval()

    # 检查日志改进
    check_log_for_improvements()

    print("\n" + "=" * 60)
    if success:
        print("🎉 股票列表获取修复测试通过！")
        print("✅ 系统现在可以正常获取股票列表")
        print("📈 左侧面板应该能正常显示股票信息")
    else:
        print("⚠️ 股票列表获取仍有问题")
        print("🔧 可能需要进一步调试和修复")

    print("\n建议:")
    print("1. 检查DuckDB数据库是否有股票基础数据")
    print("2. 验证数据下载器是否正常工作")
    print("3. 确认插件质量评估机制是否合理")


if __name__ == "__main__":
    main()
