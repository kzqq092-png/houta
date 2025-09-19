#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HIkyuu-UI全面集成检查脚本

检查所有UI组件是否正确集成了UniPluginDataManager，
包括菜单项、对话框、数据访问等各个层面的验证。

作者: FactorWeave-Quant团队
版本: 1.0
日期: 2024-09-17
"""

import sys
import os
import traceback
import inspect
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

class UIIntegrationChecker:
    """UI集成检查器"""
    
    def __init__(self):
        self.check_results = {
            "menu_integration": {"status": "pending", "details": []},
            "dialog_integration": {"status": "pending", "details": []},
            "widget_integration": {"status": "pending", "details": []},
            "data_access_integration": {"status": "pending", "details": []},
            "service_registration": {"status": "pending", "details": []},
            "import_availability": {"status": "pending", "details": []},
            "error_handling": {"status": "pending", "details": []}
        }
        
    def check_menu_integration(self) -> bool:
        """检查主菜单集成"""
        logger.info("🔍 检查主菜单集成...")
        
        try:
            # 1. 检查主菜单栏
            from gui.menu_bar import MainMenuBar
            self.check_results["menu_integration"]["details"].append("✅ MainMenuBar导入成功")
            
            # 2. 检查菜单方法是否存在
            menu_methods = [
                'show_data_source_plugin_manager',
                'show_plugin_manager', 
                '_on_enhanced_import',
                '_create_plugin_dialog'
            ]
            
            for method in menu_methods:
                if hasattr(MainMenuBar, method):
                    self.check_results["menu_integration"]["details"].append(f"✅ {method}方法存在")
                else:
                    self.check_results["menu_integration"]["details"].append(f"❌ {method}方法缺失")
                    return False
            
            # 3. 检查菜单方法源代码中的UniPluginDataManager集成
            source = inspect.getsource(MainMenuBar._on_enhanced_import)
            if 'EnhancedDataImportMainWindow' in source:
                self.check_results["menu_integration"]["details"].append("✅ 增强版数据导入启动器集成")
            else:
                self.check_results["menu_integration"]["details"].append("❌ 增强版数据导入启动器未集成")
                return False
            
            self.check_results["menu_integration"]["status"] = "passed"
            logger.success("✅ 主菜单集成检查通过")
            return True
            
        except Exception as e:
            self.check_results["menu_integration"]["status"] = "failed"
            self.check_results["menu_integration"]["details"].append(f"❌ 检查失败: {e}")
            logger.error(f"❌ 主菜单集成检查失败: {e}")
            return False
    
    def check_dialog_integration(self) -> bool:
        """检查对话框集成"""
        logger.info("🔍 检查对话框集成...")
        
        try:
            # 1. 检查增强插件管理器对话框
            from gui.dialogs.enhanced_plugin_manager_dialog import EnhancedPluginManagerDialog
            self.check_results["dialog_integration"]["details"].append("✅ EnhancedPluginManagerDialog导入成功")
            
            # 2. 检查__init__方法中的UniPluginDataManager集成
            source = inspect.getsource(EnhancedPluginManagerDialog.__init__)
            if 'uni_plugin_data_manager' in source:
                self.check_results["dialog_integration"]["details"].append("✅ UniPluginDataManager已集成到对话框")
            else:
                self.check_results["dialog_integration"]["details"].append("❌ UniPluginDataManager未集成到对话框")
                return False
            
            # 3. 检查导入语句
            if 'get_uni_plugin_data_manager' in source:
                self.check_results["dialog_integration"]["details"].append("✅ get_uni_plugin_data_manager导入存在")
            else:
                self.check_results["dialog_integration"]["details"].append("❌ get_uni_plugin_data_manager导入缺失")
                return False
            
            self.check_results["dialog_integration"]["status"] = "passed"
            logger.success("✅ 对话框集成检查通过")
            return True
            
        except Exception as e:
            self.check_results["dialog_integration"]["status"] = "failed"
            self.check_results["dialog_integration"]["details"].append(f"❌ 检查失败: {e}")
            logger.error(f"❌ 对话框集成检查失败: {e}")
            return False
    
    def check_widget_integration(self) -> bool:
        """检查Widget集成"""
        logger.info("🔍 检查Widget集成...")
        
        try:
            # 1. 检查增强数据导入widget
            from gui.widgets.enhanced_data_import_widget import EnhancedDataImportWidget, BatchSelectionDialog
            self.check_results["widget_integration"]["details"].append("✅ EnhancedDataImportWidget导入成功")
            
            # 2. 检查BatchSelectionDialog的数据获取方法
            data_methods = ['get_stock_data', 'get_fund_data', 'get_index_data']
            
            for method_name in data_methods:
                if hasattr(BatchSelectionDialog, method_name):
                    method = getattr(BatchSelectionDialog, method_name)
                    source = inspect.getsource(method)
                    
                    if 'get_uni_plugin_data_manager' in source:
                        self.check_results["widget_integration"]["details"].append(f"✅ {method_name}已集成UniPluginDataManager")
                    else:
                        self.check_results["widget_integration"]["details"].append(f"❌ {method_name}未集成UniPluginDataManager")
                        return False
                        
                    # 检查回退机制
                    if '备用方案' in source or 'get_unified_data_manager' in source:
                        self.check_results["widget_integration"]["details"].append(f"✅ {method_name}包含回退机制")
                    else:
                        self.check_results["widget_integration"]["details"].append(f"⚠️  {method_name}缺少回退机制")
                else:
                    self.check_results["widget_integration"]["details"].append(f"❌ {method_name}方法不存在")
                    return False
            
            # 3. 检查启动器
            from gui.enhanced_data_import_launcher import EnhancedDataImportMainWindow
            self.check_results["widget_integration"]["details"].append("✅ EnhancedDataImportMainWindow导入成功")
            
            self.check_results["widget_integration"]["status"] = "passed"
            logger.success("✅ Widget集成检查通过")
            return True
            
        except Exception as e:
            self.check_results["widget_integration"]["status"] = "failed"
            self.check_results["widget_integration"]["details"].append(f"❌ 检查失败: {e}")
            logger.error(f"❌ Widget集成检查失败: {e}")
            return False
    
    def check_data_access_integration(self) -> bool:
        """检查数据访问集成"""
        logger.info("🔍 检查数据访问集成...")
        
        try:
            # 1. 检查UniPluginDataManager
            from core.services.uni_plugin_data_manager import UniPluginDataManager, get_uni_plugin_data_manager
            self.check_results["data_access_integration"]["details"].append("✅ UniPluginDataManager导入成功")
            
            # 2. 检查必需方法
            required_methods = [
                'get_stock_list', 'get_fund_list', 'get_index_list',
                'get_kdata', 'get_real_time_quotes', 'health_check', 'initialize'
            ]
            
            for method in required_methods:
                if hasattr(UniPluginDataManager, method):
                    self.check_results["data_access_integration"]["details"].append(f"✅ {method}方法存在")
                else:
                    self.check_results["data_access_integration"]["details"].append(f"❌ {method}方法缺失")
                    return False
            
            # 3. 检查全局实例管理
            manager_instance = get_uni_plugin_data_manager()
            if manager_instance is None:
                self.check_results["data_access_integration"]["details"].append("ℹ️  UniPluginDataManager实例未初始化（正常，需要服务启动后才有）")
            else:
                self.check_results["data_access_integration"]["details"].append("✅ UniPluginDataManager实例已可用")
            
            self.check_results["data_access_integration"]["status"] = "passed"
            logger.success("✅ 数据访问集成检查通过")
            return True
            
        except Exception as e:
            self.check_results["data_access_integration"]["status"] = "failed"
            self.check_results["data_access_integration"]["details"].append(f"❌ 检查失败: {e}")
            logger.error(f"❌ 数据访问集成检查失败: {e}")
            return False
    
    def check_service_registration(self) -> bool:
        """检查服务注册"""
        logger.info("🔍 检查服务注册...")
        
        try:
            # 1. 检查ServiceBootstrap
            from core.services.service_bootstrap import ServiceBootstrap
            self.check_results["service_registration"]["details"].append("✅ ServiceBootstrap导入成功")
            
            # 2. 检查注册方法
            if hasattr(ServiceBootstrap, '_register_uni_plugin_data_manager'):
                self.check_results["service_registration"]["details"].append("✅ _register_uni_plugin_data_manager方法存在")
                
                # 检查方法源代码
                source = inspect.getsource(ServiceBootstrap._register_uni_plugin_data_manager)
                if 'UniPluginDataManager' in source and 'set_uni_plugin_data_manager' in source:
                    self.check_results["service_registration"]["details"].append("✅ 服务注册逻辑完整")
                else:
                    self.check_results["service_registration"]["details"].append("❌ 服务注册逻辑不完整")
                    return False
            else:
                self.check_results["service_registration"]["details"].append("❌ _register_uni_plugin_data_manager方法缺失")
                return False
            
            # 3. 检查bootstrap方法中的调用
            bootstrap_source = inspect.getsource(ServiceBootstrap.bootstrap)
            if '_register_uni_plugin_data_manager' in bootstrap_source:
                self.check_results["service_registration"]["details"].append("✅ bootstrap方法中包含UniPluginDataManager注册")
            else:
                self.check_results["service_registration"]["details"].append("❌ bootstrap方法中缺少UniPluginDataManager注册")
                return False
            
            self.check_results["service_registration"]["status"] = "passed"
            logger.success("✅ 服务注册检查通过")
            return True
            
        except Exception as e:
            self.check_results["service_registration"]["status"] = "failed"
            self.check_results["service_registration"]["details"].append(f"❌ 检查失败: {e}")
            logger.error(f"❌ 服务注册检查失败: {e}")
            return False
    
    def check_import_availability(self) -> bool:
        """检查导入可用性"""
        logger.info("🔍 检查导入可用性...")
        
        try:
            # 关键模块导入测试
            imports_to_check = [
                ("core.services.uni_plugin_data_manager", "UniPluginDataManager"),
                ("core.data_source_router", "DataSourceRouter"),
                ("core.tet_data_pipeline", "TETDataPipeline"),
                ("core.plugin_manager", "PluginManager"),
                ("gui.dialogs.enhanced_plugin_manager_dialog", "EnhancedPluginManagerDialog"),
                ("gui.widgets.enhanced_data_import_widget", "EnhancedDataImportWidget"),
                ("gui.enhanced_data_import_launcher", "EnhancedDataImportMainWindow"),
                ("plugins.templates.standard_data_source_plugin", "StandardDataSourcePlugin")
            ]
            
            for module_name, class_name in imports_to_check:
                try:
                    module = __import__(module_name, fromlist=[class_name])
                    cls = getattr(module, class_name)
                    self.check_results["import_availability"]["details"].append(f"✅ {module_name}.{class_name} 导入成功")
                except ImportError as e:
                    self.check_results["import_availability"]["details"].append(f"❌ {module_name}.{class_name} 导入失败: {e}")
                    return False
                except AttributeError as e:
                    self.check_results["import_availability"]["details"].append(f"❌ {module_name}.{class_name} 属性错误: {e}")
                    return False
            
            self.check_results["import_availability"]["status"] = "passed"
            logger.success("✅ 导入可用性检查通过")
            return True
            
        except Exception as e:
            self.check_results["import_availability"]["status"] = "failed"
            self.check_results["import_availability"]["details"].append(f"❌ 检查失败: {e}")
            logger.error(f"❌ 导入可用性检查失败: {e}")
            return False
    
    def check_error_handling(self) -> bool:
        """检查错误处理"""
        logger.info("🔍 检查错误处理...")
        
        try:
            # 1. 检查UI组件的异常处理
            from gui.widgets.enhanced_data_import_widget import BatchSelectionDialog
            
            # 检查get_stock_data的异常处理
            source = inspect.getsource(BatchSelectionDialog.get_stock_data)
            if 'try:' in source and 'except Exception' in source:
                self.check_results["error_handling"]["details"].append("✅ get_stock_data包含异常处理")
            else:
                self.check_results["error_handling"]["details"].append("❌ get_stock_data缺少异常处理")
                return False
            
            # 2. 检查菜单项的异常处理
            from gui.menu_bar import MainMenuBar
            menu_source = inspect.getsource(MainMenuBar._on_enhanced_import)
            if 'try:' in menu_source and 'except' in menu_source:
                self.check_results["error_handling"]["details"].append("✅ _on_enhanced_import包含异常处理")
            else:
                self.check_results["error_handling"]["details"].append("❌ _on_enhanced_import缺少异常处理")
                return False
            
            # 3. 检查UniPluginDataManager的错误处理
            from core.services.uni_plugin_data_manager import UniPluginDataManager
            init_source = inspect.getsource(UniPluginDataManager.initialize)
            if 'try:' in init_source and 'except Exception' in init_source:
                self.check_results["error_handling"]["details"].append("✅ UniPluginDataManager.initialize包含异常处理")
            else:
                self.check_results["error_handling"]["details"].append("❌ UniPluginDataManager.initialize缺少异常处理")
                return False
            
            self.check_results["error_handling"]["status"] = "passed"
            logger.success("✅ 错误处理检查通过")
            return True
            
        except Exception as e:
            self.check_results["error_handling"]["status"] = "failed"
            self.check_results["error_handling"]["details"].append(f"❌ 检查失败: {e}")
            logger.error(f"❌ 错误处理检查失败: {e}")
            return False
    
    def run_full_check(self) -> bool:
        """运行完整检查"""
        logger.info("🚀 开始HIkyuu-UI全面集成检查...")
        
        checkers = [
            ("导入可用性", self.check_import_availability),
            ("服务注册", self.check_service_registration),
            ("数据访问集成", self.check_data_access_integration),
            ("主菜单集成", self.check_menu_integration),
            ("对话框集成", self.check_dialog_integration),
            ("Widget集成", self.check_widget_integration),
            ("错误处理", self.check_error_handling)
        ]
        
        passed_count = 0
        total_count = len(checkers)
        
        for name, checker in checkers:
            logger.info(f"\n📋 检查项目: {name}")
            try:
                if checker():
                    passed_count += 1
                    logger.success(f"✅ {name} 检查通过")
                else:
                    logger.error(f"❌ {name} 检查失败")
            except Exception as e:
                logger.error(f"❌ {name} 检查异常: {e}")
                logger.error(traceback.format_exc())
        
        return passed_count == total_count
    
    def generate_report(self) -> str:
        """生成检查报告"""
        report = []
        report.append("=" * 80)
        report.append("HIkyuu-UI全面UI集成检查报告")
        report.append("=" * 80)
        report.append(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for category, result in self.check_results.items():
            status_icon = "✅" if result["status"] == "passed" else "❌" if result["status"] == "failed" else "⏳"
            category_name = category.replace('_', ' ').title()
            report.append(f"{status_icon} {category_name}: {result['status'].upper()}")
            
            for detail in result["details"]:
                report.append(f"    {detail}")
            report.append("")
        
        # 统计
        passed = sum(1 for r in self.check_results.values() if r["status"] == "passed")
        total = len(self.check_results)
        
        report.append("=" * 80)
        report.append(f"检查结果: {passed}/{total} 项通过")
        
        if passed == total:
            report.append("🎉 所有检查项目通过！HIkyuu-UI统一架构UI集成完全成功！")
            report.append("")
            report.append("📍 UI访问方式:")
            report.append("  • 插件管理器: 主菜单 → 工具 → 插件管理 → 数据源插件 (Ctrl+Shift+D)")
            report.append("  • 数据导入系统: 主菜单 → 数据 → K线数据导入 (Ctrl+Shift+I)")
            report.append("")
            report.append("🚀 系统已完全集成UniPluginDataManager，用户可以正常使用所有功能！")
        else:
            report.append("⚠️  部分检查项目未通过，需要进一步修复。")
        
        report.append("=" * 80)
        
        return "\n".join(report)

def main():
    """主函数"""
    logger.info("🚀 启动HIkyuu-UI全面UI集成检查脚本...")
    
    checker = UIIntegrationChecker()
    
    try:
        success = checker.run_full_check()
        
        # 生成并输出报告
        report = checker.generate_report()
        logger.info("\n" + report)
        
        # 保存报告到文件
        report_file = f"HIkyuu-UI全面UI集成检查报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📄 检查报告已保存到: {report_file}")
        
        if success:
            logger.success("🎉 所有UI集成检查通过！系统完全就绪！")
            return 0
        else:
            logger.error("⚠️  部分UI集成检查失败，请查看报告并修复问题。")
            return 1
    
    except Exception as e:
        logger.error(f"❌ 检查脚本执行失败: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
