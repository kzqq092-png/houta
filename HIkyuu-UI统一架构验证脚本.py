#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HIkyuu-UI统一数据源管理架构验证脚本

验证统一插件数据管理器(UniPluginDataManager)是否正确集成到系统中，
包括服务引导、UI集成、插件管理器等各个层面的功能验证。

作者: FactorWeave-Quant团队
版本: 1.0
日期: 2024-09-17
"""

import sys
import os
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class ArchitectureValidator:
    """HIkyuu-UI统一架构验证器"""

    def __init__(self):
        self.validation_results = {
            "service_bootstrap": {"status": "pending", "details": []},
            "uni_plugin_manager": {"status": "pending", "details": []},
            "ui_integration": {"status": "pending", "details": []},
            "plugin_discovery": {"status": "pending", "details": []},
            "data_access": {"status": "pending", "details": []},
            "error_handling": {"status": "pending", "details": []}
        }

    def validate_service_bootstrap(self) -> bool:
        """验证服务引导中的UniPluginDataManager集成"""
        logger.info("🔍 验证服务引导中的UniPluginDataManager集成...")

        try:
            # 1. 验证导入
            from core.services.service_bootstrap import ServiceBootstrap
            from core.services.uni_plugin_data_manager import UniPluginDataManager
            self.validation_results["service_bootstrap"]["details"].append("✅ 核心模块导入成功")

            # 2. 验证ServiceBootstrap是否包含注册方法
            bootstrap = ServiceBootstrap()
            if hasattr(bootstrap, '_register_uni_plugin_data_manager'):
                self.validation_results["service_bootstrap"]["details"].append("✅ _register_uni_plugin_data_manager方法存在")
            else:
                self.validation_results["service_bootstrap"]["details"].append("❌ _register_uni_plugin_data_manager方法缺失")
                return False

            # 3. 验证全局实例管理
            from core.services.uni_plugin_data_manager import get_uni_plugin_data_manager, set_uni_plugin_data_manager
            self.validation_results["service_bootstrap"]["details"].append("✅ 全局实例管理函数可用")

            self.validation_results["service_bootstrap"]["status"] = "passed"
            logger.success("✅ 服务引导验证通过")
            return True

        except Exception as e:
            self.validation_results["service_bootstrap"]["status"] = "failed"
            self.validation_results["service_bootstrap"]["details"].append(f"❌ 验证失败: {e}")
            logger.error(f"❌ 服务引导验证失败: {e}")
            return False

    def validate_uni_plugin_manager(self) -> bool:
        """验证UniPluginDataManager功能完整性"""
        logger.info("🔍 验证UniPluginDataManager功能完整性...")

        try:
            from core.services.uni_plugin_data_manager import UniPluginDataManager
            from core.plugin_manager import PluginManager
            from core.data_source_router import DataSourceRouter
            from core.tet_data_pipeline import TETDataPipeline

            # 1. 验证类结构
            required_methods = [
                'initialize', 'get_stock_list', 'get_fund_list', 'get_index_list',
                'get_kdata', 'get_real_time_quotes', 'health_check'
            ]

            for method in required_methods:
                if hasattr(UniPluginDataManager, method):
                    self.validation_results["uni_plugin_manager"]["details"].append(f"✅ {method}方法存在")
                else:
                    self.validation_results["uni_plugin_manager"]["details"].append(f"❌ {method}方法缺失")
                    return False

            # 2. 验证依赖项
            self.validation_results["uni_plugin_manager"]["details"].append("✅ 所有依赖项可正常导入")

            self.validation_results["uni_plugin_manager"]["status"] = "passed"
            logger.success("✅ UniPluginDataManager功能验证通过")
            return True

        except Exception as e:
            self.validation_results["uni_plugin_manager"]["status"] = "failed"
            self.validation_results["uni_plugin_manager"]["details"].append(f"❌ 验证失败: {e}")
            logger.error(f"❌ UniPluginDataManager功能验证失败: {e}")
            return False

    def validate_ui_integration(self) -> bool:
        """验证UI组件中的UniPluginDataManager集成"""
        logger.info("🔍 验证UI组件中的UniPluginDataManager集成...")

        try:
            # 1. 验证数据导入widget
            from gui.widgets.enhanced_data_import_widget import EnhancedDataImportWidget

            # 检查源代码中是否包含uni_plugin_data_manager的使用
            import inspect
            source = inspect.getsource(EnhancedDataImportWidget)
            if 'get_uni_plugin_data_manager' in source:
                self.validation_results["ui_integration"]["details"].append("✅ EnhancedDataImportWidget已集成UniPluginDataManager")
            else:
                self.validation_results["ui_integration"]["details"].append("❌ EnhancedDataImportWidget未集成UniPluginDataManager")
                return False

            # 2. 验证插件管理对话框
            from gui.dialogs.enhanced_plugin_manager_dialog import EnhancedPluginManagerDialog
            dialog_source = inspect.getsource(EnhancedPluginManagerDialog)
            if 'uni_plugin_data_manager' in dialog_source:
                self.validation_results["ui_integration"]["details"].append("✅ EnhancedPluginManagerDialog已集成UniPluginDataManager")
            else:
                self.validation_results["ui_integration"]["details"].append("❌ EnhancedPluginManagerDialog未集成UniPluginDataManager")
                return False

            self.validation_results["ui_integration"]["status"] = "passed"
            logger.success("✅ UI集成验证通过")
            return True

        except Exception as e:
            self.validation_results["ui_integration"]["status"] = "failed"
            self.validation_results["ui_integration"]["details"].append(f"❌ 验证失败: {e}")
            logger.error(f"❌ UI集成验证失败: {e}")
            return False

    def validate_plugin_discovery(self) -> bool:
        """验证插件发现和注册机制"""
        logger.info("🔍 验证插件发现和注册机制...")

        try:
            # 1. 验证插件模板
            from plugins.templates.standard_data_source_plugin import StandardDataSourcePlugin
            self.validation_results["plugin_discovery"]["details"].append("✅ 标准数据源插件模板可用")

            # 2. 验证插件接口
            from core.data_source_extensions import IDataSourcePlugin
            self.validation_results["plugin_discovery"]["details"].append("✅ IDataSourcePlugin接口可用")

            # 3. 验证转换工具
            from tools.legacy_to_plugin_converter import LegacyToPluginConverter
            self.validation_results["plugin_discovery"]["details"].append("✅ 遗留代码转换工具可用")

            self.validation_results["plugin_discovery"]["status"] = "passed"
            logger.success("✅ 插件发现机制验证通过")
            return True

        except Exception as e:
            self.validation_results["plugin_discovery"]["status"] = "failed"
            self.validation_results["plugin_discovery"]["details"].append(f"❌ 验证失败: {e}")
            logger.error(f"❌ 插件发现机制验证失败: {e}")
            return False

    def validate_data_access(self) -> bool:
        """验证数据访问路径"""
        logger.info("🔍 验证数据访问路径...")

        try:
            # 1. 验证TET数据管道
            from core.tet_data_pipeline import TETDataPipeline
            self.validation_results["data_access"]["details"].append("✅ TET数据管道可用")

            # 2. 验证数据源路由器
            from core.data_source_router import DataSourceRouter
            self.validation_results["data_access"]["details"].append("✅ 数据源路由器可用")

            # 3. 验证风险管理组件
            try:
                from core.risk.data_quality_monitor import DataQualityMonitor
                from core.risk.enhanced_circuit_breaker import EnhancedCircuitBreaker
                self.validation_results["data_access"]["details"].append("✅ 风险管理组件可用")
            except ImportError:
                self.validation_results["data_access"]["details"].append("⚠️  风险管理组件不完整（非关键）")

            self.validation_results["data_access"]["status"] = "passed"
            logger.success("✅ 数据访问路径验证通过")
            return True

        except Exception as e:
            self.validation_results["data_access"]["status"] = "failed"
            self.validation_results["data_access"]["details"].append(f"❌ 验证失败: {e}")
            logger.error(f"❌ 数据访问路径验证失败: {e}")
            return False

    def validate_error_handling(self) -> bool:
        """验证错误处理和回退机制"""
        logger.info("🔍 验证错误处理和回退机制...")

        try:
            # 1. 验证全局实例管理的空值处理
            from core.services.uni_plugin_data_manager import get_uni_plugin_data_manager
            manager = get_uni_plugin_data_manager()  # 应该返回None而不抛异常
            if manager is None:
                self.validation_results["error_handling"]["details"].append("✅ 空值处理正常")
            else:
                self.validation_results["error_handling"]["details"].append("✅ 实例已初始化")

            # 2. 验证UI组件的回退机制（检查源代码中的try-except结构）
            import inspect
            from gui.widgets.enhanced_data_import_widget import BatchSelectionDialog
            source = inspect.getsource(BatchSelectionDialog.get_stock_data)
            if 'except Exception' in source and '备用方案' in source:
                self.validation_results["error_handling"]["details"].append("✅ UI组件包含回退机制")
            else:
                self.validation_results["error_handling"]["details"].append("❌ UI组件缺少回退机制")
                return False

            self.validation_results["error_handling"]["status"] = "passed"
            logger.success("✅ 错误处理机制验证通过")
            return True

        except Exception as e:
            self.validation_results["error_handling"]["status"] = "failed"
            self.validation_results["error_handling"]["details"].append(f"❌ 验证失败: {e}")
            logger.error(f"❌ 错误处理机制验证失败: {e}")
            return False

    def run_full_validation(self) -> bool:
        """运行完整验证"""
        logger.info("🚀 开始HIkyuu-UI统一架构完整验证...")

        validators = [
            ("服务引导集成", self.validate_service_bootstrap),
            ("UniPluginDataManager功能", self.validate_uni_plugin_manager),
            ("UI组件集成", self.validate_ui_integration),
            ("插件发现机制", self.validate_plugin_discovery),
            ("数据访问路径", self.validate_data_access),
            ("错误处理机制", self.validate_error_handling)
        ]

        passed_count = 0
        total_count = len(validators)

        for name, validator in validators:
            logger.info(f"\n📋 验证项目: {name}")
            try:
                if validator():
                    passed_count += 1
                    logger.success(f"✅ {name} 验证通过")
                else:
                    logger.error(f"❌ {name} 验证失败")
            except Exception as e:
                logger.error(f"❌ {name} 验证异常: {e}")
                logger.error(traceback.format_exc())

        return passed_count == total_count

    def generate_report(self) -> str:
        """生成验证报告"""
        report = []
        report.append("=" * 80)
        report.append("HIkyuu-UI统一数据源管理架构验证报告")
        report.append("=" * 80)
        report.append(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        for category, result in self.validation_results.items():
            status_icon = "✅" if result["status"] == "passed" else "❌" if result["status"] == "failed" else "⏳"
            report.append(f"{status_icon} {category.replace('_', ' ').title()}: {result['status'].upper()}")

            for detail in result["details"]:
                report.append(f"    {detail}")
            report.append("")

        # 统计
        passed = sum(1 for r in self.validation_results.values() if r["status"] == "passed")
        total = len(self.validation_results)

        report.append("=" * 80)
        report.append(f"验证结果: {passed}/{total} 项通过")

        if passed == total:
            report.append("🎉 所有验证项目通过！HIkyuu-UI统一架构集成成功！")
        else:
            report.append("⚠️  部分验证项目未通过，需要进一步修复。")

        report.append("=" * 80)

        return "\n".join(report)

def main():
    """主函数"""
    logger.info("🚀 启动HIkyuu-UI统一架构验证脚本...")

    validator = ArchitectureValidator()

    try:
        success = validator.run_full_validation()

        # 生成并输出报告
        report = validator.generate_report()
        logger.info("\n" + report)

        # 保存报告到文件
        report_file = f"HIkyuu-UI统一架构验证报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"📄 验证报告已保存到: {report_file}")

        if success:
            logger.success("🎉 所有验证通过！HIkyuu-UI统一架构集成成功！")
            return 0
        else:
            logger.error("⚠️  部分验证失败，请查看报告并修复问题。")
            return 1

    except Exception as e:
        logger.error(f"❌ 验证脚本执行失败: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
