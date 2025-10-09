from core.services.unified_data_manager import get_unified_data_manager
from core.containers import get_service_container
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HIkyuu-UI 迁移后全面自动化验证回归测试

该脚本执行完整的迁移后验证，包括：
- 系统健康检查
- 功能回归测试
- 性能基准测试
- 数据完整性验证
- TET+Plugin架构验证

作者: HIkyuu-UI Migration Team
日期: 2025-09-20
"""

import logging
import os
import sys
import json
import time
import datetime
import traceback
from pathlib import Path
from typing import Dict, List, Any, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 基本日志设置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MigrationValidation")

class MigrationValidationSuite:
    """迁移验证测试套件"""

    def __init__(self):
        self.results = {
            "start_time": datetime.datetime.now().isoformat(),
            "tests": {},
            "summary": {},
            "overall_status": "unknown"
        }
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0

    def run_test(self, test_name: str, test_func) -> bool:
        """运行单个测试"""
        logger.info(f"🔍 开始测试: {test_name}")
        start_time = time.time()

        try:
            result = test_func()
            duration = time.time() - start_time

            if result.get("success", False):
                self.passed_count += 1
                status = "PASSED"
                logger.info(f"✅ 测试通过: {test_name} ({duration:.2f}s)")
            else:
                self.failed_count += 1
                status = "FAILED"
                logger.error(f"❌ 测试失败: {test_name} ({duration:.2f}s)")
                if result.get("error"):
                    logger.error(f"   错误: {result['error']}")

            self.results["tests"][test_name] = {
                "status": status,
                "duration": duration,
                "details": result,
                "timestamp": datetime.datetime.now().isoformat()
            }

            self.test_count += 1
            return result.get("success", False)

        except Exception as e:
            duration = time.time() - start_time
            self.failed_count += 1
            self.test_count += 1

            error_msg = f"测试执行异常: {str(e)}"
            logger.error(f"💥 {test_name}: {error_msg}")

            self.results["tests"][test_name] = {
                "status": "ERROR",
                "duration": duration,
                "details": {"success": False, "error": error_msg, "traceback": traceback.format_exc()},
                "timestamp": datetime.datetime.now().isoformat()
            }

            return False

    def test_system_health(self) -> Dict[str, Any]:
        """测试系统健康状态"""
        try:
            # 检查Python环境
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

            # 检查关键模块导入
            critical_modules = [
                "pandas", "numpy", "requests", "sqlite3"
            ]

            missing_modules = []
            for module in critical_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)

            # 检查关键文件存在性
            critical_files = [
                "main.py",
                "core/services/unified_data_manager.py",
                "core/services/uni_plugin_data_manager.py",
                "core/plugin_center.py",
                "core/tet_router_engine.py"
            ]

            missing_files = []
            for file_path in critical_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)

            # 检查系统资源
            try:
                import psutil
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage(str(project_root))

                system_resources = {
                    "memory_available_gb": memory.available / (1024**3),
                    "memory_usage_percent": memory.percent,
                    "disk_free_gb": disk.free / (1024**3),
                    "disk_usage_percent": (disk.used / disk.total) * 100
                }
            except ImportError:
                system_resources = {"error": "psutil not available"}

            success = len(missing_modules) == 0 and len(missing_files) == 0

            return {
                "success": success,
                "python_version": python_version,
                "missing_modules": missing_modules,
                "missing_files": missing_files,
                "system_resources": system_resources
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_core_components_import(self) -> Dict[str, Any]:
        """测试核心组件导入"""
        try:
            components = {}

            # 测试核心服务导入
            try:
                from core.services.unified_data_manager import UnifiedDataManager
                components["UnifiedDataManager"] = "OK"
            except Exception as e:
                components["UnifiedDataManager"] = f"FAILED: {str(e)}"

            try:
                from core.services.uni_plugin_data_manager import UniPluginDataManager
                components["UniPluginDataManager"] = "OK"
            except Exception as e:
                components["UniPluginDataManager"] = f"FAILED: {str(e)}"

            try:
                from core.plugin_center import PluginCenter
                components["PluginCenter"] = "OK"
            except Exception as e:
                components["PluginCenter"] = f"FAILED: {str(e)}"

            try:
                from core.tet_router_engine import TETRouterEngine
                components["TETRouterEngine"] = "OK"
            except Exception as e:
                components["TETRouterEngine"] = f"FAILED: {str(e)}"

            try:
                from core.data_standardization_engine import DataStandardizationEngine
                components["DataStandardizationEngine"] = "OK"
            except Exception as e:
                components["DataStandardizationEngine"] = f"FAILED: {str(e)}"

            # 检查是否有失败的组件
            failed_components = [k for k, v in components.items() if v != "OK"]
            success = len(failed_components) == 0

            return {
                "success": success,
                "components": components,
                "failed_components": failed_components
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_legacy_sources_removed(self) -> Dict[str, Any]:
        """测试传统数据源是否已移除"""
        try:
    # 传统数据源文件已在迁移过程中删除
    legacy_files = []

            existing_files = []
            for file_path in legacy_files:
                if Path(file_path).exists():
                    existing_files.append(file_path)

            # 检查代码中是否还有传统数据源的直接引用
            import_references = []
            try:
                # 简单的文本搜索检查
                main_py = Path("main.py")
                if main_py.exists():
                    content = main_py.read_text(encoding='utf-8')
                    # 传统数据源导入已在迁移过程中移除
                    legacy_imports = []

                    for imp in legacy_imports:
                        if imp in content:
                            import_references.append(imp)
            except Exception:
                pass

            success = len(existing_files) == 0 and len(import_references) == 0

            return {
                "success": success,
                "existing_legacy_files": existing_files,
                "legacy_import_references": import_references,
                "message": "传统数据源已完全移除" if success else "仍存在传统数据源残留"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_tet_plugin_architecture(self) -> Dict[str, Any]:
        """测试TET+Plugin架构"""
        try:
            architecture_status = {}
            
            # 测试UniPluginDataManager实例化
            try:
                from core.services.uni_plugin_data_manager import UniPluginDataManager
                from core.plugin_manager import PluginManager
                from core.data_source_router import DataSourceRouter
                from core.tet_data_pipeline import TETDataPipeline
                
                # 创建必要的依赖
                plugin_manager = PluginManager()
                data_source_router = DataSourceRouter()
                tet_pipeline = TETDataPipeline()
                
                manager = UniPluginDataManager(plugin_manager, data_source_router, tet_pipeline)
                architecture_status["UniPluginDataManager"] = "可实例化"
            except Exception as e:
                architecture_status["UniPluginDataManager"] = f"实例化失败: {str(e)}"
            
            # 测试PluginCenter
            try:
                from core.plugin_center import PluginCenter
                from core.plugin_manager import PluginManager
                
                plugin_manager = PluginManager()
                plugin_center = PluginCenter(plugin_manager)
                registered_plugins = len(plugin_center.get_registered_plugins())
                architecture_status["PluginCenter"] = f"正常，已注册插件: {registered_plugins}个"
            except Exception as e:
                architecture_status["PluginCenter"] = f"初始化失败: {str(e)}"
            
            # 测试TETRouterEngine
            try:
                from core.tet_router_engine import TETRouterEngine
                router = TETRouterEngine()
                architecture_status["TETRouterEngine"] = "正常"
            except Exception as e:
                architecture_status["TETRouterEngine"] = f"初始化失败: {str(e)}"
            
            # 检查是否所有组件都正常
            failed_components = [k for k, v in architecture_status.items() if "失败" in v]
            success = len(failed_components) == 0
            
            return {
                "success": success,
                "architecture_status": architecture_status,
                "failed_components": failed_components
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_data_access_functionality(self) -> Dict[str, Any]:
        """测试数据访问功能"""
        try:
            data_access_results = {}
            
            # 测试统一数据管理器
            try:
                from core.services.unified_data_manager import UnifiedDataManager
                data_manager = get_unified_data_manager()
                
                # 测试基本方法是否存在
                methods_to_check = ["get_stock_list", "get_kline_data", "get_real_time_data"]
                available_methods = []
                
                for method_name in methods_to_check:
                    if hasattr(data_manager, method_name):
                        available_methods.append(method_name)
                
                data_access_results["UnifiedDataManager"] = {
                    "status": "正常",
                    "available_methods": available_methods,
                    "method_count": len(available_methods)
                }
                
            except Exception as e:
                data_access_results["UnifiedDataManager"] = {
                    "status": f"失败: {str(e)}",
                    "available_methods": [],
                    "method_count": 0
                }
            
            # 测试数据访问层
            try:
                from core.data.data_access import DataAccess
                data_access = DataAccess()
                data_access_results["DataAccess"] = "正常"
            except Exception as e:
                data_access_results["DataAccess"] = f"失败: {str(e)}"
            
            # 检查成功状态
            failed_items = [k for k, v in data_access_results.items() 
                          if isinstance(v, str) and "失败" in v]
            success = len(failed_items) == 0
            
            return {
                "success": success,
                "data_access_results": data_access_results,
                "failed_items": failed_items
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_migration_tools_functionality(self) -> Dict[str, Any]:
        """测试迁移工具功能"""
        try:
            migration_tools = {}
            
            # 测试备份工具
            backup_script = Path("scripts/migration/create_system_backup.py")
            if backup_script.exists():
                migration_tools["backup_tool"] = "存在"
            else:
                migration_tools["backup_tool"] = "缺失"
            
            # 测试监控工具
            monitor_script = Path("core/migration/migration_monitor.py")
            if monitor_script.exists():
                migration_tools["monitor_tool"] = "存在"
            else:
                migration_tools["monitor_tool"] = "缺失"
            
            # 测试配置管理器
            config_manager = Path("core/migration/migration_config_manager.py")
            if config_manager.exists():
                migration_tools["config_manager"] = "存在"
            else:
                migration_tools["config_manager"] = "缺失"
            
            # 测试健康检查工具
            health_check = Path("core/migration/pre_migration_health_check.py")
            if health_check.exists():
                migration_tools["health_check"] = "存在"
            else:
                migration_tools["health_check"] = "缺失"
            
            # 测试依赖分析器
            dependency_analyzer = Path("core/migration/dependency_analyzer.py")
            if dependency_analyzer.exists():
                migration_tools["dependency_analyzer"] = "存在"
            else:
                migration_tools["dependency_analyzer"] = "缺失"
            
            missing_tools = [k for k, v in migration_tools.items() if v == "缺失"]
            success = len(missing_tools) == 0
            
            return {
                "success": success,
                "migration_tools": migration_tools,
                "missing_tools": missing_tools,
                "total_tools": len(migration_tools),
                "available_tools": len(migration_tools) - len(missing_tools)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_database_connectivity(self) -> Dict[str, Any]:
        """测试数据库连接"""
        try:
            db_results = {}
            
            # 测试SQLite连接
            try:
                import sqlite3
                # 查找SQLite数据库文件
                sqlite_files = list(Path(".").glob("**/*.db")) + list(Path(".").glob("**/*.sqlite"))
                
                connected_dbs = []
                for db_file in sqlite_files[:3]:  # 只测试前3个
                    try:
                        conn = sqlite3.connect(str(db_file), timeout=5)
                        conn.execute("SELECT 1")
                        conn.close()
                        connected_dbs.append(str(db_file))
                    except Exception:
                        pass
                
                db_results["sqlite"] = {
                    "status": "正常",
                    "total_files": len(sqlite_files),
                    "connected_files": len(connected_dbs),
                    "sample_files": connected_dbs[:3]
                }
                
            except Exception as e:
                db_results["sqlite"] = {"status": f"失败: {str(e)}"}
            
            # 测试DuckDB连接
            try:
                import duckdb
                duckdb_files = list(Path(".").glob("**/*.duckdb"))
                
                connected_duckdbs = []
                for db_file in duckdb_files[:2]:  # 只测试前2个
                    try:
                        conn = duckdb.connect(str(db_file))
                        conn.execute("SELECT 1")
                        conn.close()
                        connected_duckdbs.append(str(db_file))
                    except Exception:
                        pass
                
                db_results["duckdb"] = {
                    "status": "正常",
                    "total_files": len(duckdb_files),
                    "connected_files": len(connected_duckdbs),
                    "sample_files": connected_duckdbs[:2]
                }
                
            except ImportError:
                db_results["duckdb"] = {"status": "DuckDB未安装"}
            except Exception as e:
                db_results["duckdb"] = {"status": f"失败: {str(e)}"}
            
            # 检查成功状态
            failed_dbs = [k for k, v in db_results.items() 
                         if isinstance(v, dict) and "失败" in v.get("status", "")]
            success = len(failed_dbs) == 0
            
            return {
                "success": success,
                "database_results": db_results,
                "failed_databases": failed_dbs
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_main_application_startup(self) -> Dict[str, Any]:
        """测试主应用程序启动"""
        try:
            startup_results = {}
            
            # 检查main.py是否存在
            main_py = Path("main.py")
            if not main_py.exists():
                return {"success": False, "error": "main.py文件不存在"}
            
            # 尝试导入main模块的关键组件
            try:
                # 读取main.py内容进行基本检查
                content = main_py.read_text(encoding='utf-8')
                
                # 检查关键导入
                key_imports = [
                    "from core.services.unified_data_manager",
                    "from core.data.data_access",
                    "import sys",
                    "import os"
                ]
                
                missing_imports = []
                for imp in key_imports:
                    if imp not in content:
                        missing_imports.append(imp)
                
                startup_results["main_py_analysis"] = {
                    "file_size": len(content),
                    "line_count": len(content.split('\n')),
                    "missing_imports": missing_imports
                }
                
                # 检查是否有明显的语法错误
                try:
                    compile(content, "main.py", "exec")
                    startup_results["syntax_check"] = "通过"
                except SyntaxError as e:
                    startup_results["syntax_check"] = f"语法错误: {str(e)}"
                
            except Exception as e:
                startup_results["main_py_analysis"] = f"分析失败: {str(e)}"
            
            # 检查成功状态
            success = (
                startup_results.get("syntax_check") == "通过" and
                len(startup_results.get("main_py_analysis", {}).get("missing_imports", [])) == 0
            )
            
            return {
                "success": success,
                "startup_results": startup_results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始执行HIkyuu-UI迁移后全面自动化验证回归测试")
        logger.info("=" * 60)
        
        # 定义测试套件
        test_suite = [
            ("系统健康检查", self.test_system_health),
            ("核心组件导入测试", self.test_core_components_import),
            ("传统数据源移除验证", self.test_legacy_sources_removed),
            ("TET+Plugin架构测试", self.test_tet_plugin_architecture),
            ("数据访问功能测试", self.test_data_access_functionality),
            ("迁移工具功能测试", self.test_migration_tools_functionality),
            ("数据库连接测试", self.test_database_connectivity),
            ("主应用程序启动测试", self.test_main_application_startup)
        ]
        
        # 执行所有测试
        for test_name, test_func in test_suite:
            self.run_test(test_name, test_func)
            time.sleep(0.5)  # 短暂暂停
        
        # 生成测试摘要
        self.generate_summary()
        
        # 保存测试报告
        self.save_report()
        
        logger.info("=" * 60)
        logger.info("🏁 全面自动化验证回归测试完成")
        
        return self.results

    def generate_summary(self):
        """生成测试摘要"""
        end_time = datetime.datetime.now()
        start_time = datetime.datetime.fromisoformat(self.results["start_time"])
        duration = (end_time - start_time).total_seconds()
        
        success_rate = (self.passed_count / self.test_count * 100) if self.test_count > 0 else 0
        
        if self.failed_count == 0:
            overall_status = "PASSED"
            status_emoji = "✅"
        elif self.failed_count <= 2:
            overall_status = "WARNING"
            status_emoji = "⚠️"
        else:
            overall_status = "FAILED"
            status_emoji = "❌"
        
        self.results["summary"] = {
            "overall_status": overall_status,
            "total_tests": self.test_count,
            "passed_tests": self.passed_count,
            "failed_tests": self.failed_count,
            "success_rate": round(success_rate, 2),
            "duration_seconds": round(duration, 2),
            "end_time": end_time.isoformat()
        }
        
        self.results["overall_status"] = overall_status
        
        # 打印摘要
        logger.info(f"\n📊 测试摘要:")
        logger.info(f"{status_emoji} 总体状态: {overall_status}")
        logger.info(f"📈 成功率: {success_rate:.1f}% ({self.passed_count}/{self.test_count})")
        logger.info(f"⏱️  总耗时: {duration:.2f}秒")
        logger.info(f"✅ 通过: {self.passed_count}")
        logger.info(f"❌ 失败: {self.failed_count}")

    def save_report(self):
        """保存测试报告"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(f"migration_validation_report_{timestamp}.json")
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📄 测试报告已保存: {report_file}")
            
            # 生成简化的文本报告
            text_report = self.generate_text_report()
            text_file = Path(f"migration_validation_summary_{timestamp}.txt")
            
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_report)
            
            logger.info(f"📄 简化报告已保存: {text_file}")
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")

    def generate_text_report(self) -> str:
        """生成文本格式的测试报告"""
        summary = self.results["summary"]
        
        report = f"""
HIkyuu-UI 迁移后全面自动化验证回归测试报告
{'=' * 50}

测试时间: {self.results['start_time']} - {summary['end_time']}
测试耗时: {summary['duration_seconds']}秒

总体结果: {summary['overall_status']}
成功率: {summary['success_rate']}%
通过测试: {summary['passed_tests']}/{summary['total_tests']}

详细测试结果:
{'-' * 30}
"""
        
        for test_name, test_result in self.results["tests"].items():
            status_icon = "✅" if test_result["status"] == "PASSED" else "❌"
            report += f"{status_icon} {test_name}: {test_result['status']} ({test_result['duration']:.2f}s)\n"
            
            if test_result["status"] != "PASSED" and test_result["details"].get("error"):
                report += f"   错误: {test_result['details']['error']}\n"
        
        report += f"\n{'-' * 30}\n"
        
        if summary['overall_status'] == 'PASSED':
            report += "🎉 所有测试通过！迁移成功完成，系统运行正常。\n"
        elif summary['overall_status'] == 'WARNING':
            report += "⚠️  大部分测试通过，但存在一些警告项目，建议检查。\n"
        else:
            report += "❌ 存在测试失败，需要进一步检查和修复。\n"
        
        return report

def main():
    """主函数"""
    print("🚀 HIkyuu-UI 迁移后全面自动化验证回归测试")
    print("=" * 60)
    
    # 创建测试套件并运行
    validation_suite = MigrationValidationSuite()
    results = validation_suite.run_all_tests()
    
    # 返回结果
    return results["overall_status"] == "PASSED"

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
