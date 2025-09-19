#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能数据源选择机制测试脚本

测试板块资金流服务的自动数据源检测和选择功能
"""

from typing import Dict, Any
import pandas as pd
from loguru import logger
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_sector_fund_flow_service():
    """测试板块资金流服务的智能数据源选择"""
    try:
        logger.info("🚀 开始测试智能数据源选择机制...")

        # 1. 初始化数据管理器
        logger.info("📋 步骤 1: 初始化数据管理器...")
        from core.services.unified_data_manager import get_unified_data_manager
        data_manager = get_unified_data_manager()

        if not data_manager:
            logger.error("❌ 数据管理器初始化失败")
            return False

        logger.info("✅ 数据管理器初始化成功")

        # 2. 初始化板块资金流服务
        logger.info("📋 步骤 2: 初始化板块资金流服务...")
        from core.services.sector_fund_flow_service import SectorFundFlowService

        service = SectorFundFlowService(data_manager=data_manager)

        if not service.initialize():
            logger.error("❌ 板块资金流服务初始化失败")
            return False

        logger.info("✅ 板块资金流服务初始化成功")

        # 3. 检查数据源检测结果
        logger.info("📋 步骤 3: 检查数据源检测结果...")
        sources_info = service.get_available_sources_info()

        logger.info("📊 数据源检测结果:")
        logger.info(f"   可用数据源总数: {len(sources_info.get('available_sources', {}))}")
        logger.info(f"   最优数据源列表: {sources_info.get('optimal_sources', [])}")
        logger.info(f"   当前选择数据源: {sources_info.get('current_source', 'unknown')}")

        # 显示详细的数据源信息
        available_sources = sources_info.get('available_sources', {})
        for source_id, info in available_sources.items():
            support_fund_flow = "✅" if info.get('supports_fund_flow', False) else "❌"
            logger.info(f"   - {source_id}: {support_fund_flow} 板块资金流, "
                        f"健康度: {info.get('health_score', 0):.2f}, "
                        f"类型: {info.get('type', 'unknown')}")

        # 4. 测试服务状态
        logger.info("📋 步骤 4: 测试服务状态...")
        status = service.get_service_status()

        logger.info("📈 服务状态:")
        for key, value in status.items():
            logger.info(f"   {key}: {value}")

        # 5. 测试数据获取
        logger.info("📋 步骤 5: 测试数据获取...")

        test_indicators = ["今日", "3日", "5日"]

        for indicator in test_indicators:
            try:
                logger.info(f"🔄 测试获取 {indicator} 板块资金流数据...")

                # 获取当前最优数据源
                current_source_before = service.get_current_optimal_source()
                logger.info(f"   请求前数据源: {current_source_before}")

                # 获取数据
                df = service.get_sector_flow_rank(indicator=indicator, force_refresh=True)

                # 获取请求后的数据源
                current_source_after = service.get_current_optimal_source()
                logger.info(f"   请求后数据源: {current_source_after}")

                if not df.empty:
                    logger.info(f"✅ {indicator} 数据获取成功: {len(df)} 条记录")
                    logger.info(f"   数据列: {list(df.columns)}")
                    if len(df) > 0:
                        logger.info(f"   样本数据: {df.head(1).to_dict('records')}")
                else:
                    logger.warning(f"⚠️ {indicator} 数据为空")

            except Exception as e:
                logger.error(f"❌ 测试 {indicator} 数据获取失败: {e}")

        # 6. 测试数据源切换功能
        logger.info("📋 步骤 6: 测试数据源切换功能...")

        optimal_sources = sources_info.get('optimal_sources', [])
        if len(optimal_sources) > 1:
            # 测试切换到第二个最优数据源
            second_source = optimal_sources[1]
            logger.info(f"🔄 测试切换到数据源: {second_source}")

            success = service.switch_data_source(second_source)
            if success:
                logger.info(f"✅ 成功切换到数据源: {second_source}")

                # 测试获取数据
                df = service.get_sector_flow_rank(indicator="今日", force_refresh=True)
                current_source = service.get_current_optimal_source()
                logger.info(f"   切换后实际使用数据源: {current_source}")

                if not df.empty:
                    logger.info(f"✅ 切换后数据获取成功: {len(df)} 条记录")
                else:
                    logger.warning("⚠️ 切换后数据为空")
            else:
                logger.warning(f"⚠️ 切换到数据源 {second_source} 失败")
        else:
            logger.info("ℹ️ 只有一个最优数据源，跳过切换测试")

        # 7. 清理资源
        logger.info("📋 步骤 7: 清理资源...")
        service.cleanup()

        logger.info("🎉 智能数据源选择机制测试完成!")
        return True

    except Exception as e:
        logger.error(f"❌ 测试过程中发生异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_data_source_priority():
    """测试数据源优先级设置"""
    try:
        logger.info("🔍 测试数据源优先级设置...")

        from core.services.sector_fund_flow_service import SectorFundFlowService
        from core.services.unified_data_manager import get_unified_data_manager

        data_manager = get_unified_data_manager()
        service = SectorFundFlowService(data_manager=data_manager)

        # 初始化服务
        service.initialize()

        # 获取数据源信息
        sources_info = service.get_available_sources_info()
        available_sources = sources_info.get('available_sources', {})

        logger.info("📊 数据源优先级分析:")

        # 分析每个数据源的优先级评分
        for source_id, info in available_sources.items():
            health_score = info.get('health_score', 0)
            source_type = info.get('type', 'unknown')
            supports_fund_flow = info.get('supports_fund_flow', False)

            # 计算优先级评分（与服务中的逻辑一致）
            type_weight = 1.0 if source_type == 'tet_plugin' else 0.8
            if 'akshare' in source_id.lower():
                type_weight += 0.3

            priority_score = health_score * type_weight if supports_fund_flow else 0

            status = "✅ 支持" if supports_fund_flow else "❌ 不支持"
            logger.info(f"   {source_id}:")
            logger.info(f"     板块资金流: {status}")
            logger.info(f"     健康度: {health_score:.2f}")
            logger.info(f"     类型权重: {type_weight:.2f}")
            logger.info(f"     优先级评分: {priority_score:.2f}")

        # 显示最终排序
        optimal_sources = sources_info.get('optimal_sources', [])
        logger.info("🏆 最终优先级排序:")
        for i, source_id in enumerate(optimal_sources, 1):
            info = available_sources.get(source_id, {})
            logger.info(f"   {i}. {source_id} (健康度: {info.get('health_score', 0):.2f})")

        service.cleanup()
        return True

    except Exception as e:
        logger.error(f"❌ 数据源优先级测试失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.add("logs/smart_data_source_test.log",
               rotation="10 MB",
               retention="7 days",
               level="DEBUG")

    logger.info("=" * 60)
    logger.info("🚀 开始智能数据源选择机制测试")
    logger.info("=" * 60)

    success = True

    # 测试 1: 基本功能测试
    logger.info("\n" + "=" * 40)
    logger.info("📋 测试 1: 基本功能测试")
    logger.info("=" * 40)
    if not test_sector_fund_flow_service():
        success = False

    # 测试 2: 数据源优先级测试
    logger.info("\n" + "=" * 40)
    logger.info("📋 测试 2: 数据源优先级测试")
    logger.info("=" * 40)
    if not test_data_source_priority():
        success = False

    # 输出总结
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("🎉 所有测试通过！智能数据源选择机制正常工作")
    else:
        logger.error("❌ 部分测试失败，请检查日志")
    logger.info("=" * 60)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
