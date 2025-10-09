#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试板块资金流数据获取修复效果
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_sector_fund_flow_fix():
    """测试板块资金流数据获取修复效果"""
    print("HIkyuu-UI 板块资金流数据获取修复测试")
    print("=" * 50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # 1. 初始化日志系统
        print("📝 步骤 1: 初始化日志系统...")
        from core.loguru_config import initialize_loguru
        initialize_loguru()

        # 2. 引导服务
        print("🚀 步骤 2: 引导服务...")
        from core.services.service_bootstrap import bootstrap_services
        bootstrap_success = bootstrap_services()
        if not bootstrap_success:
            print("❌ 服务引导失败")
            return False

        # 3. 获取板块资金流服务
        print("💰 步骤 3: 获取板块资金流服务...")
        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.services.sector_fund_flow_service import SectorFundFlowService

        container = UnifiedServiceContainer()
        sector_service = container.resolve(SectorFundFlowService)

        if not sector_service:
            print("❌ 无法获取SectorFundFlowService")
            return False

        print("✅ SectorFundFlowService获取成功")

        # 4. 测试获取板块资金流数据
        print("\n🧪 步骤 4: 测试获取板块资金流数据...")
        try:
            # 获取今日板块资金流排行
            result = sector_service.get_sector_flow_rank(period="今日")

            if result is not None and not result.empty:
                print(f"✅ 板块资金流数据获取成功！")
                print(f"   数据条数: {len(result)}")
                print(f"   数据列: {list(result.columns)}")

                # 显示前5条数据
                if len(result) > 0:
                    print("\n📊 前5条板块资金流数据:")
                    print(result.head().to_string(index=False))

                return True
            else:
                print("❌ 板块资金流数据为空")
                return False

        except Exception as e:
            print(f"❌ 板块资金流数据获取失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_sector_fund_flow_fix()
    if success:
        print("\n🎉 板块资金流数据获取修复测试成功！")
    else:
        print("\n❌ 板块资金流数据获取修复测试失败")

    sys.exit(0 if success else 1)
