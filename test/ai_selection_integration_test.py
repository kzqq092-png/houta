"""
AI选股系统集成测试

验证AI选股相关服务的完整集成：
1. AI选股集成服务 (AISelectionIntegrationService)
2. AI选股回测服务 (AISelectionBacktestService)
3. AI选股风险控制服务 (AISelectionRiskControlService)
4. AI可解释性服务 (AIExplainabilityService)
5. 增强指标服务 (EnhancedIndicatorService)
6. 个性化选股引擎 (PersonalizedStockSelectionEngine)

测试内容：
- 服务注册验证
- 依赖注入验证
- 功能集成验证
- 数据流验证
- 错误处理验证
"""

import unittest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from loguru import logger

# 导入核心服务
from core.containers import ServiceContainer, get_service_container
from core.services.service_bootstrap import ServiceBootstrap
from core.services.database_service import DatabaseService
from core.services.unified_data_manager import UnifiedDataManager
from core.services.enhanced_indicator_service import EnhancedIndicatorService

# 导入AI选股相关服务
from core.services.ai_selection_integration_service import (
    AISelectionIntegrationService,
    StockSelectionCriteria,
    SelectionStrategy,
    RiskLevel
)
from core.services.ai_selection_backtest_service import AISelectionBacktestService
from core.services.ai_selection_risk_control_service import AISelectionRiskControlService
from core.services.ai_explainability_service import AIExplainabilityService

# 导入个性化引擎
from core.ai.personalized_stock_selection_engine import PersonalizedStockSelectionEngine


class AISelectionIntegrationTest(unittest.TestCase):
    """AI选股系统集成测试类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化 - 设置全局服务容器"""
        logger.info("开始AI选股系统集成测试...")
        
        # 创建服务容器
        cls.service_container = ServiceContainer()
        
        # 设置为全局容器
        import core.containers.service_container as container_module
        container_module._global_container = cls.service_container
        
        logger.info("服务容器初始化完成")

    def setUp(self):
        """测试方法初始化"""
        self.service_container = get_service_container()
        self.assertIsNotNone(self.service_container, "服务容器未初始化")

    def test_01_service_bootstrap(self):
        """测试服务引导和注册"""
        logger.info("测试服务引导和注册...")
        
        # 创建服务引导器
        bootstrap = ServiceBootstrap(self.service_container)
        
        # 执行服务引导
        result = bootstrap.bootstrap()
        
        # 验证引导结果
        self.assertTrue(result, "服务引导失败")
        logger.info("✅ 服务引导完成")

    def test_02_core_services_registration(self):
        """测试核心服务注册"""
        logger.info("测试核心服务注册...")
        
        # 测试数据库服务注册
        self.assertTrue(
            self.service_container.is_registered(DatabaseService),
            "DatabaseService未注册"
        )
        database_service = self.service_container.resolve(DatabaseService)
        self.assertIsNotNone(database_service, "DatabaseService解析失败")
        logger.info("✅ DatabaseService注册验证通过")
        
        # 测试统一数据管理器注册
        self.assertTrue(
            self.service_container.is_registered(UnifiedDataManager),
            "UnifiedDataManager未注册"
        )
        data_manager = self.service_container.resolve(UnifiedDataManager)
        self.assertIsNotNone(data_manager, "UnifiedDataManager解析失败")
        logger.info("✅ UnifiedDataManager注册验证通过")
        
        # 测试增强指标服务注册
        self.assertTrue(
            self.service_container.is_registered(EnhancedIndicatorService),
            "EnhancedIndicatorService未注册"
        )
        indicator_service = self.service_container.resolve(EnhancedIndicatorService)
        self.assertIsNotNone(indicator_service, "EnhancedIndicatorService解析失败")
        logger.info("✅ EnhancedIndicatorService注册验证通过")

    def test_03_ai_selection_services_registration(self):
        """测试AI选股服务注册"""
        logger.info("测试AI选股服务注册...")
        
        # 测试AI选股集成服务注册
        self.assertTrue(
            self.service_container.is_registered(AISelectionIntegrationService),
            "AISelectionIntegrationService未注册"
        )
        ai_selection_service = self.service_container.resolve(AISelectionIntegrationService)
        self.assertIsNotNone(ai_selection_service, "AISelectionIntegrationService解析失败")
        logger.info("✅ AISelectionIntegrationService注册验证通过")
        
        # 测试AI选股回测服务注册
        self.assertTrue(
            self.service_container.is_registered(AISelectionBacktestService),
            "AISelectionBacktestService未注册"
        )
        ai_backtest_service = self.service_container.resolve(AISelectionBacktestService)
        self.assertIsNotNone(ai_backtest_service, "AISelectionBacktestService解析失败")
        logger.info("✅ AISelectionBacktestService注册验证通过")
        
        # 测试AI选股风险控制服务注册
        self.assertTrue(
            self.service_container.is_registered(AISelectionRiskControlService),
            "AISelectionRiskControlService未注册"
        )
        ai_risk_service = self.service_container.resolve(AISelectionRiskControlService)
        self.assertIsNotNone(ai_risk_service, "AISelectionRiskControlService解析失败")
        logger.info("✅ AISelectionRiskControlService注册验证通过")
        
        # 测试AI可解释性服务注册
        self.assertTrue(
            self.service_container.is_registered(AIExplainabilityService),
            "AIExplainabilityService未注册"
        )
        ai_explain_service = self.service_container.resolve(AIExplainabilityService)
        self.assertIsNotNone(ai_explain_service, "AIExplainabilityService解析失败")
        logger.info("✅ AIExplainabilityService注册验证通过")

    def test_04_service_dependencies(self):
        """测试服务依赖关系"""
        logger.info("测试服务依赖关系...")
        
        # 获取AI选股集成服务
        ai_selection_service = self.service_container.resolve(AISelectionIntegrationService)
        
        # 验证依赖关系
        self.assertIsNotNone(
            ai_selection_service._data_manager,
            "AISelectionIntegrationService缺少UnifiedDataManager依赖"
        )
        self.assertIsNotNone(
            ai_selection_service._indicator_service,
            "AISelectionIntegrationService缺少EnhancedIndicatorService依赖"
        )
        self.assertIsNotNone(
            ai_selection_service._database_service,
            "AISelectionIntegrationService缺少DatabaseService依赖"
        )
        logger.info("✅ AISelectionIntegrationService依赖关系验证通过")
        
        # 获取AI选股回测服务
        ai_backtest_service = self.service_container.resolve(AISelectionBacktestService)
        
        # 验证依赖关系
        self.assertIsNotNone(
            ai_backtest_service._database_service,
            "AISelectionBacktestService缺少DatabaseService依赖"
        )
        self.assertIsNotNone(
            ai_backtest_service._ai_selection_service,
            "AISelectionBacktestService缺少AISelectionIntegrationService依赖"
        )
        logger.info("✅ AISelectionBacktestService依赖关系验证通过")
        
        # 获取AI选股风险控制服务
        ai_risk_service = self.service_container.resolve(AISelectionRiskControlService)
        
        # 验证依赖关系
        self.assertIsNotNone(
            ai_risk_service._database_service,
            "AISelectionRiskControlService缺少DatabaseService依赖"
        )
        self.assertIsNotNone(
            ai_risk_service._ai_selection_service,
            "AISelectionRiskControlService缺少AISelectionIntegrationService依赖"
        )
        self.assertIsNotNone(
            ai_risk_service._ai_backtest_service,
            "AISelectionRiskControlService缺少AISelectionBacktestService依赖"
        )
        self.assertIsNotNone(
            ai_risk_service._indicator_service,
            "AISelectionRiskControlService缺少EnhancedIndicatorService依赖"
        )
        logger.info("✅ AISelectionRiskControlService依赖关系验证通过")

    def test_05_ai_selection_basic_functionality(self):
        """测试AI选股基础功能"""
        logger.info("测试AI选股基础功能...")
        
        ai_selection_service = self.service_container.resolve(AISelectionIntegrationService)
        
        # 创建测试选股标准
        test_criteria = StockSelectionCriteria(
            market_cap_min=100.0,
            market_cap_max=1000.0,
            pe_ratio_min=5.0,
            pe_ratio_max=50.0,
            strategy_type=SelectionStrategy.QUANTITATIVE,
            risk_level=RiskLevel.MODERATE
        )
        
        # 测试选股标准验证
        is_valid = ai_selection_service._validate_criteria(test_criteria)
        self.assertTrue(is_valid, "选股标准验证失败")
        logger.info("✅ 选股标准验证通过")
        
        # 测试策略注册
        strategies = ai_selection_service.get_available_strategies()
        self.assertIsInstance(strategies, list, "策略列表获取失败")
        self.assertGreater(len(strategies), 0, "策略列表为空")
        logger.info(f"✅ 可用策略数量: {len(strategies)}")

    def test_06_enhanced_indicator_integration(self):
        """测试增强指标服务集成"""
        logger.info("测试增强指标服务集成...")
        
        indicator_service = self.service_container.resolve(EnhancedIndicatorService)
        
        # 测试指标计算（使用模拟数据）
        import pandas as pd
        import numpy as np
        
        # 创建模拟股价数据
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        np.random.seed(42)
        close_prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.02)
        
        mock_data = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * (1 + np.random.randn(len(dates)) * 0.01),
            'high': close_prices * (1 + np.abs(np.random.randn(len(dates)) * 0.02)),
            'low': close_prices * (1 - np.abs(np.random.randn(len(dates)) * 0.02)),
            'close': close_prices,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        })
        
        # 测试RSI指标计算
        rsi_result = indicator_service.calculate_indicator(
            indicator_name='RSI',
            data=mock_data,
            parameters={'timeperiod': 14}
        )
        
        self.assertIsNotNone(rsi_result, "RSI指标计算失败")
        self.assertIn('RSI', rsi_result, "RSI结果中缺少RSI列")
        logger.info("✅ RSI指标计算测试通过")
        
        # 测试MACD指标计算
        macd_result = indicator_service.calculate_indicator(
            indicator_name='MACD',
            data=mock_data,
            parameters={}
        )
        
        self.assertIsNotNone(macd_result, "MACD指标计算失败")
        required_macd_cols = ['DIF', 'DEA', 'MACD']
        for col in required_macd_cols:
            self.assertIn(col, macd_result, f"MACD结果中缺少{col}列")
        logger.info("✅ MACD指标计算测试通过")

    def test_07_risk_control_integration(self):
        """测试风险控制服务集成"""
        logger.info("测试风险控制服务集成...")
        
        ai_risk_service = self.service_container.resolve(AISelectionRiskControlService)
        
        # 创建测试选股标准
        test_criteria = StockSelectionCriteria(
            market_cap_min=100.0,
            market_cap_max=1000.0,
            strategy_type=SelectionStrategy.QUANTITATIVE,
            risk_level=RiskLevel.MODERATE
        )
        
        # 创建测试股票列表
        test_stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
        
        # 测试风险评估
        risk_metrics = ai_risk_service.assess_risk(
            user_id='test_user',
            selection_criteria=test_criteria,
            strategy=SelectionStrategy.QUANTITATIVE,
            selected_stocks=test_stocks
        )
        
        self.assertIsNotNone(risk_metrics, "风险评估失败")
        self.assertIsInstance(risk_metrics.overall_risk_score, float, "风险评分类型错误")
        self.assertGreaterEqual(risk_metrics.overall_risk_score, 0, "风险评分不能为负数")
        self.assertLessEqual(risk_metrics.overall_risk_score, 100, "风险评分不能超过100")
        logger.info(f"✅ 风险评估测试通过，总体风险评分: {risk_metrics.overall_risk_score:.2f}")

    def test_08_backtest_service_integration(self):
        """测试回测服务集成"""
        logger.info("测试回测服务集成...")
        
        ai_backtest_service = self.service_container.resolve(AISelectionBacktestService)
        
        # 创建测试选股标准
        test_criteria = StockSelectionCriteria(
            market_cap_min=100.0,
            market_cap_max=1000.0,
            strategy_type=SelectionStrategy.QUANTITATIVE,
            risk_level=RiskLevel.MODERATE
        )
        
        # 设置测试日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # 测试回测配置创建
        backtest_config = ai_backtest_service.create_backtest_config(
            initial_capital=100000.0,
            commission_pct=0.001,
            slippage_pct=0.0005
        )
        
        self.assertIsNotNone(backtest_config, "回测配置创建失败")
        self.assertEqual(backtest_config.initial_capital, 100000.0, "初始资金设置错误")
        logger.info("✅ 回测配置创建测试通过")

    def test_09_explainability_service_integration(self):
        """测试可解释性服务集成"""
        logger.info("测试可解释性服务集成...")
        
        ai_explain_service = self.service_container.resolve(AIExplainabilityService)
        
        # 测试因子解释生成
        factor_explanations = ai_explain_service.generate_factor_explanations(
            stock_code='000001.SZ',
            factors={'RSI': 65.5, 'MACD': 0.85, 'PE_RATIO': 12.3}
        )
        
        self.assertIsNotNone(factor_explanations, "因子解释生成失败")
        self.assertIsInstance(factor_explanations, dict, "因子解释类型错误")
        logger.info("✅ 因子解释生成测试通过")
        
        # 测试可视化数据生成
        visualization_data = ai_explain_service.generate_visualization_data(
            stock_code='000001.SZ',
            explanation_data=factor_explanations
        )
        
        self.assertIsNotNone(visualization_data, "可视化数据生成失败")
        self.assertIsInstance(visualization_data, dict, "可视化数据类型错误")
        logger.info("✅ 可视化数据生成测试通过")

    def test_10_end_to_end_integration(self):
        """端到端集成测试"""
        logger.info("执行端到端集成测试...")
        
        # 获取所有相关服务
        ai_selection_service = self.service_container.resolve(AISelectionIntegrationService)
        ai_backtest_service = self.service_container.resolve(AISelectionBacktestService)
        ai_risk_service = self.service_container.resolve(AISelectionRiskControlService)
        ai_explain_service = self.service_container.resolve(AIExplainabilityService)
        
        # 1. 创建选股标准
        test_criteria = StockSelectionCriteria(
            market_cap_min=100.0,
            market_cap_max=1000.0,
            pe_ratio_min=5.0,
            pe_ratio_max=50.0,
            strategy_type=SelectionStrategy.QUANTITATIVE,
            risk_level=RiskLevel.MODERATE
        )
        
        # 2. 风险评估
        risk_metrics = ai_risk_service.assess_risk(
            user_id='test_user',
            selection_criteria=test_criteria,
            strategy=SelectionStrategy.QUANTITATIVE,
            selected_stocks=['000001.SZ', '000002.SZ']
        )
        
        self.assertIsNotNone(risk_metrics, "端到端测试：风险评估失败")
        
        # 3. 创建回测配置
        backtest_config = ai_backtest_service.create_backtest_config(
            initial_capital=100000.0
        )
        
        self.assertIsNotNone(backtest_config, "端到端测试：回测配置创建失败")
        
        # 4. 生成可解释性数据
        factor_explanations = ai_explain_service.generate_factor_explanations(
            stock_code='000001.SZ',
            factors={'RSI': 65.5, 'MACD': 0.85}
        )
        
        self.assertIsNotNone(factor_explanations, "端到端测试：因子解释生成失败")
        
        logger.info("✅ 端到端集成测试完成")

    def test_11_error_handling(self):
        """测试错误处理机制"""
        logger.info("测试错误处理机制...")
        
        ai_selection_service = self.service_container.resolve(AISelectionIntegrationService)
        ai_risk_service = self.service_container.resolve(AISelectionRiskControlService)
        
        # 测试无效选股标准的错误处理
        invalid_criteria = StockSelectionCriteria(
            market_cap_min=1000.0,  # 最小市值大于最大市值
            market_cap_max=100.0,
            strategy_type=SelectionStrategy.QUANTITATIVE
        )
        
        is_valid = ai_selection_service._validate_criteria(invalid_criteria)
        self.assertFalse(is_valid, "无效选股标准应该被拒绝")
        logger.info("✅ 无效选股标准错误处理测试通过")
        
        # 测试空股票列表的风险评估错误处理
        risk_metrics = ai_risk_service.assess_risk(
            user_id='test_user',
            selection_criteria=test_criteria,
            strategy=SelectionStrategy.QUANTITATIVE,
            selected_stocks=[]  # 空列表
        )
        
        # 应该返回默认风险指标
        self.assertIsNotNone(risk_metrics, "空股票列表风险评估应该返回默认指标")
        logger.info("✅ 空股票列表错误处理测试通过")

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        logger.info("AI选股系统集成测试完成")


def run_integration_tests():
    """运行集成测试"""
    logger.info("开始运行AI选股系统集成测试...")
    
    # 创建测试套件
    test_suite = unittest.TestLoader().loadTestsFromTestCase(AISelectionIntegrationTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        logger.info("🎉 所有集成测试通过！")
        return True
    else:
        logger.error(f"❌ 集成测试失败，错误数量: {len(result.failures)}")
        for failure in result.failures:
            logger.error(f"失败: {failure[0]}")
            logger.error(f"错误信息: {failure[1]}")
        
        if result.errors:
            logger.error(f"错误数量: {len(result.errors)}")
            for error in result.errors:
                logger.error(f"错误: {error[0]}")
                logger.error(f"错误信息: {error[1]}")
        
        return False


if __name__ == '__main__':
    # 配置日志
    logger.add(
        "logs/ai_selection_integration_test.log",
        rotation="1 day",
        retention="30 days",
        level="INFO"
    )
    
    # 运行测试
    success = run_integration_tests()
    
    # 退出码
    sys.exit(0 if success else 1)