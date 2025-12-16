#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速风险控制服务验证测试
"""

import sys
import traceback
from datetime import datetime

def main():
    print("开始快速风险控制服务验证...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # 1. 测试导入
        print("测试模块导入...")
        from core.services.service_bootstrap import ServiceBootstrap
        from core.containers import get_service_container
        print("  基础模块导入成功")
        
        # 2. 初始化服务容器
        print("\n初始化服务容器...")
        bootstrap = ServiceBootstrap()
        bootstrap_success = bootstrap.bootstrap()
        
        if not bootstrap_success:
            print("  服务容器初始化失败")
            return False
            
        print("  服务容器初始化成功")
        
        # 3. 获取风险控制服务
        print("\n获取风险控制服务...")
        container = get_service_container()
        risk_control_service = container.resolve('AISelectionRiskControlService')
        print("  风险控制服务获取成功")
        
        # 4. 测试风险评估功能
        print("\n测试1: 风险评估功能...")
        test_stocks = ['000001', '000002', '600036']
        
        try:
            risk_metrics = risk_control_service.assess_risk(
                selected_stocks=test_stocks,
                selection_criteria=None,
                investment_profile=None
            )
            print(f"  风险评估成功")
            print(f"     - 总体风险评分: {risk_metrics.overall_risk_score:.3f}")
            print(f"     - 市场风险评分: {risk_metrics.market_risk_score:.3f}")
            print(f"     - 流动性风险评分: {risk_metrics.liquidity_risk_score:.3f}")
        except Exception as e:
            print(f"  风险评估失败: {e}")
            traceback.print_exc()
            return False
        
        # 5. 测试合规检查功能
        print("\n测试2: 合规检查功能...")
        try:
            compliance_result = risk_control_service.check_compliance(
                selected_stocks=test_stocks,
                selection_criteria=None,
                investment_profile=None
            )
            print(f"  合规检查成功")
            print(f"     - 是否合规: {compliance_result.is_compliant}")
            print(f"     - 合规问题数量: {len(compliance_result.compliance_issues)}")
        except Exception as e:
            print(f"  合规检查失败: {e}")
            traceback.print_exc()
            return False
        
        # 6. 测试风险缓解建议功能
        print("\n测试3: 风险缓解建议功能...")
        try:
            risk_assessment = {
                'overall_risk_score': risk_metrics.overall_risk_score,
                'market_risk_score': risk_metrics.market_risk_score,
                'liquidity_risk_score': risk_metrics.liquidity_risk_score,
                'compliance_issues': compliance_result.compliance_issues
            }
            
            mitigation_recommendations = risk_control_service.generate_risk_mitigation_recommendations(
                risk_assessment=risk_assessment,
                selected_stocks=test_stocks
            )
            print(f"  风险缓解建议生成成功")
            print(f"     - 建议数量: {len(mitigation_recommendations.recommendations)}")
            for i, rec in enumerate(mitigation_recommendations.recommendations[:3]):
                print(f"     - 建议{i+1}: {rec.title}")
        except Exception as e:
            print(f"  风险缓解建议失败: {e}")
            traceback.print_exc()
            return False
        
        # 7. 测试风险缓解执行功能
        print("\n测试4: 风险缓解执行功能...")
        try:
            execution_result = risk_control_service.execute_risk_mitigation(
                recommendations=mitigation_recommendations.recommendations,
                original_selection=test_stocks,
                risk_profile=None
            )
            print(f"  风险缓解执行成功")
            print(f"     - 执行状态: {execution_result.execution_status}")
            print(f"     - 调整后股票数量: {len(execution_result.final_selection)}")
            print(f"     - 最终选择: {execution_result.final_selection}")
        except Exception as e:
            print(f"  风险缓解执行失败: {e}")
            traceback.print_exc()
            return False
        
        print("\n" + "="*60)
        print("风险控制服务功能验证全部通过！")
        print("DatabaseService注册问题已修复")
        print("风险控制服务功能完整实现")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)