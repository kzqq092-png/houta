#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HIkyuu-UI 2.0 系统快速启动器
提供GUI和命令行两种启动模式，集成所有系统功能

版本: 2.0 (重构版本)
作者: HIkyuu-UI Team
"""

from analysis.pattern_manager import PatternManager
from optimization.version_manager import VersionManager
from optimization.performance_evaluator import PerformanceEvaluator
from optimization.auto_tuner import AutoTuner
from optimization.main_controller import OptimizationController
from core.services import (
    ConfigService, ThemeService, StockService,
    ChartService, AnalysisService
)
from core.events import EventBus, get_event_bus
from core.containers import ServiceContainer, get_service_container
import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 核心架构导入

# 优化系统导入

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HIkyuuQuickStart:
    """
    HIkyuu-UI 2.0 快速启动器

    提供两种启动模式：
    1. GUI模式：启动完整的HIkyuu-UI 2.0图形界面
    2. 命令行模式：提供菜单式的命令行界面
    """

    def __init__(self, mode: str = "menu"):
        """
        初始化启动器

        Args:
            mode: 启动模式 ("gui", "menu", "command")
        """
        self.mode = mode
        self.service_container = None
        self.event_bus = None
        self.optimization_controller = None
        self.auto_tuner = None
        self.pattern_manager = None
        self.version_manager = None
        self.performance_evaluator = None

        # 初始化核心组件
        self._initialize_core_components()

    def _initialize_core_components(self):
        """初始化核心组件"""
        try:
            # 获取全局服务容器和事件总线
            self.service_container = get_service_container()
            self.event_bus = get_event_bus()

            # 初始化优化系统组件
            self.optimization_controller = OptimizationController(debug_mode=False)
            self.auto_tuner = AutoTuner(debug_mode=False)
            self.pattern_manager = PatternManager()
            self.version_manager = VersionManager()
            self.performance_evaluator = PerformanceEvaluator(debug_mode=False)

            logger.info("核心组件初始化完成")

        except Exception as e:
            logger.error(f"核心组件初始化失败: {e}")
            raise

    def run(self):
        """运行启动器"""
        try:
            if self.mode == "gui":
                self._run_gui_mode()
            elif self.mode == "menu":
                self._run_menu_mode()
            elif self.mode == "command":
                self._run_command_mode()
            else:
                raise ValueError(f"未知的启动模式: {self.mode}")

        except KeyboardInterrupt:
            print("\n\n⚠️  操作被用户中断")
            return 0
        except Exception as e:
            logger.error(f"启动器运行失败: {e}")
            print(f"❌ 启动失败: {e}")
            return 1

    def _run_gui_mode(self):
        """运行GUI模式"""
        print("🚀 启动 HIkyuu-UI 2.0 图形界面...")

        try:
            # 导入主应用程序
            from main import HIkyuuUIApplication

            # 创建并运行应用程序
            app = HIkyuuUIApplication()
            exit_code = app.run()

            return exit_code

        except Exception as e:
            logger.error(f"GUI模式启动失败: {e}")
            print(f"❌ GUI启动失败: {e}")
            print("💡 尝试使用命令行模式: python quick_start.py --mode menu")
            return 1

    def _run_menu_mode(self):
        """运行菜单模式"""
        self._show_banner()

        # 主循环
        while True:
            try:
                self._show_main_menu()
                choice = input("请选择操作 (0-8): ").strip()

                if choice == "1":
                    self._system_management_menu()
                elif choice == "2":
                    self._performance_evaluation_menu()
                elif choice == "3":
                    self._algorithm_optimization_menu()
                elif choice == "4":
                    self._version_management_menu()
                elif choice == "5":
                    self._data_management_menu()
                elif choice == "6":
                    self._gui_launcher_menu()
                elif choice == "7":
                    self._plugin_management_menu()
                elif choice == "8":
                    self._help_menu()
                elif choice == "0":
                    print("\n👋 感谢使用 HIkyuu-UI 2.0 系统！")
                    break
                else:
                    print("❌ 无效选择，请重试")

            except KeyboardInterrupt:
                print("\n\n⚠️  操作被用户中断")
                confirm = input("确认退出？(y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    break
            except Exception as e:
                logger.error(f"菜单操作失败: {e}")
                print(f"\n❌ 发生错误: {e}")
                input("按回车键继续...")

    def _run_command_mode(self):
        """运行命令模式（用于命令行参数）"""
        # 这个方法用于处理命令行参数
        pass

    def _show_banner(self):
        """显示启动横幅"""
        print("=" * 80)
        print("🚀 HIkyuu-UI 2.0 系统快速启动器")
        print("=" * 80)
        print("专业级股票分析与量化交易平台")
        print("✨ 完整UI界面 | 🧠 智能优化 | 📊 技术分析 | 🔌 插件生态")
        print("=" * 80)
        print()

    def _show_main_menu(self):
        """显示主菜单"""
        print("📋 主菜单")
        print("-" * 50)
        print("1. 🔧 系统管理")
        print("2. 📊 性能评估")
        print("3. 🚀 算法优化")
        print("4. 📋 版本管理")
        print("5. 💾 数据管理")
        print("6. 🖥️  图形界面")
        print("7. 🔌 插件管理")
        print("8. 📚 帮助文档")
        print("0. 🚪 退出系统")
        print("-" * 50)

    def _system_management_menu(self):
        """系统管理菜单"""
        while True:
            print("\n🔧 系统管理")
            print("-" * 40)
            print("1. 初始化系统")
            print("2. 查看系统状态")
            print("3. 列出所有形态")
            print("4. 系统诊断")
            print("5. 清理缓存")
            print("6. 系统配置")
            print("0. 返回主菜单")
            print("-" * 40)

            choice = input("请选择操作 (0-6): ").strip()

            if choice == "1":
                print("\n🔧 正在初始化系统...")
                self.optimization_controller.initialize_system()
                input("\n按回车键继续...")

            elif choice == "2":
                print("\n📊 系统状态:")
                self.optimization_controller.show_system_status()
                input("\n按回车键继续...")

            elif choice == "3":
                print("\n📋 形态列表:")
                self.optimization_controller.list_patterns()
                input("\n按回车键继续...")

            elif choice == "4":
                print("\n🔍 运行系统诊断...")
                self._run_system_diagnosis()
                input("\n按回车键继续...")

            elif choice == "5":
                print("\n🧹 清理系统缓存...")
                self._clean_system_cache()
                input("\n按回车键继续...")

            elif choice == "6":
                print("\n⚙️  系统配置管理...")
                self._system_configuration_menu()

            elif choice == "0":
                break
            else:
                print("❌ 无效选择，请重试")

    def _performance_evaluation_menu(self):
        """性能评估菜单"""
        while True:
            print("\n📊 性能评估")
            print("-" * 40)
            print("1. 评估单个形态")
            print("2. 评估所有形态")
            print("3. 性能对比分析")
            print("4. 生成评估报告")
            print("5. 历史性能查看")
            print("0. 返回主菜单")
            print("-" * 40)

            choice = input("请选择操作 (0-5): ").strip()

            if choice == "1":
                pattern_name = input("请输入形态名称 (如: hammer): ").strip()
                if pattern_name:
                    dataset_count = input("测试数据集数量 (默认3): ").strip()
                    dataset_count = int(dataset_count) if dataset_count.isdigit() else 3

                    print(f"\n📊 评估形态: {pattern_name}")
                    self.optimization_controller.evaluate_pattern(pattern_name, dataset_count)
                else:
                    print("❌ 形态名称不能为空")
                input("\n按回车键继续...")

            elif choice == "2":
                print("\n📊 评估所有形态...")
                print("⚠️  这可能需要较长时间，请耐心等待")
                confirm = input("确认继续？(y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    self._batch_evaluate_patterns()
                input("\n按回车键继续...")

            elif choice == "3":
                print("\n📈 性能对比分析...")
                self._performance_comparison_analysis()
                input("\n按回车键继续...")

            elif choice == "4":
                print("\n📄 生成评估报告...")
                self._generate_evaluation_report()
                input("\n按回车键继续...")

            elif choice == "5":
                print("\n📋 历史性能查看...")
                self._view_performance_history()
                input("\n按回车键继续...")

            elif choice == "0":
                break
            else:
                print("❌ 无效选择，请重试")

    def _algorithm_optimization_menu(self):
        """算法优化菜单"""
        while True:
            print("\n🚀 算法优化")
            print("-" * 40)
            print("1. 优化单个形态")
            print("2. 批量优化")
            print("3. 智能优化")
            print("4. 一键优化")
            print("5. 自定义优化")
            print("6. 查看优化历史")
            print("0. 返回主菜单")
            print("-" * 40)

            choice = input("请选择操作 (0-6): ").strip()

            if choice == "1":
                pattern_name = input("请输入形态名称 (如: hammer): ").strip()
                if pattern_name:
                    print("\n优化方法:")
                    print("1. genetic (遗传算法)")
                    print("2. bayesian (贝叶斯优化)")
                    print("3. random (随机搜索)")
                    print("4. gradient (梯度优化)")

                    method_choice = input("选择优化方法 (1-4, 默认1): ").strip()
                    methods = {"1": "genetic", "2": "bayesian", "3": "random", "4": "gradient"}
                    method = methods.get(method_choice, "genetic")

                    iterations = input("最大迭代次数 (默认30): ").strip()
                    iterations = int(iterations) if iterations.isdigit() else 30

                    print(f"\n🚀 优化形态: {pattern_name}")
                    print(f"优化方法: {method}")
                    print(f"最大迭代: {iterations}")

                    self.optimization_controller.optimize_pattern(pattern_name, method, iterations)
                else:
                    print("❌ 形态名称不能为空")
                input("\n按回车键继续...")

            elif choice == "2":
                print("\n🚀 批量优化所有形态...")
                print("⚠️  这可能需要很长时间，建议在空闲时运行")

                method_choice = input("选择优化方法 (1-4, 默认1): ").strip()
                methods = {"1": "genetic", "2": "bayesian", "3": "random", "4": "gradient"}
                method = methods.get(method_choice, "genetic")

                iterations = input("最大迭代次数 (默认20): ").strip()
                iterations = int(iterations) if iterations.isdigit() else 20

                confirm = input("确认开始批量优化？(y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    self.optimization_controller.batch_optimize(method, iterations)
                input("\n按回车键继续...")

            elif choice == "3":
                print("\n🧠 智能优化...")
                threshold = input("性能阈值 (0-1, 默认0.7): ").strip()
                threshold = float(threshold) if threshold else 0.7

                target = input("改进目标 (0-1, 默认0.1): ").strip()
                target = float(target) if target else 0.1

                self.optimization_controller.smart_optimize(threshold, target)
                input("\n按回车键继续...")

            elif choice == "4":
                print("\n⚡ 一键优化...")
                print("将自动选择最优参数进行优化")
                confirm = input("确认开始一键优化？(y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    self._run_one_click_optimization()
                input("\n按回车键继续...")

            elif choice == "5":
                print("\n⚙️  自定义优化...")
                self._custom_optimization_menu()

            elif choice == "6":
                print("\n📋 优化历史...")
                self._view_optimization_history()
                input("\n按回车键继续...")

            elif choice == "0":
                break
            else:
                print("❌ 无效选择，请重试")

    def _version_management_menu(self):
        """版本管理菜单"""
        while True:
            print("\n📋 版本管理")
            print("-" * 40)
            print("1. 查看形态版本")
            print("2. 激活指定版本")
            print("3. 版本对比")
            print("4. 删除版本")
            print("5. 版本统计")
            print("6. 版本回滚")
            print("0. 返回主菜单")
            print("-" * 40)

            choice = input("请选择操作 (0-6): ").strip()

            if choice == "1":
                pattern_name = input("请输入形态名称 (如: hammer): ").strip()
                if pattern_name:
                    self.optimization_controller.show_versions(pattern_name)
                else:
                    print("❌ 形态名称不能为空")
                input("\n按回车键继续...")

            elif choice == "2":
                pattern_name = input("请输入形态名称: ").strip()
                version_num = input("请输入版本号: ").strip()
                if pattern_name and version_num.isdigit():
                    self.optimization_controller.activate_version(pattern_name, int(version_num))
                else:
                    print("❌ 请输入有效的形态名称和版本号")
                input("\n按回车键继续...")

            elif choice == "3":
                print("\n📊 版本对比...")
                self._version_comparison()
                input("\n按回车键继续...")

            elif choice == "4":
                print("\n🗑️  删除版本...")
                self._delete_version()
                input("\n按回车键继续...")

            elif choice == "5":
                print("\n📈 版本统计...")
                self._version_statistics()
                input("\n按回车键继续...")

            elif choice == "6":
                print("\n↩️  版本回滚...")
                self._version_rollback()
                input("\n按回车键继续...")

            elif choice == "0":
                break
            else:
                print("❌ 无效选择，请重试")

    def _data_management_menu(self):
        """数据管理菜单"""
        while True:
            print("\n💾 数据管理")
            print("-" * 40)
            print("1. 导出优化数据")
            print("2. 导入优化数据")
            print("3. 清理历史数据")
            print("4. 数据备份")
            print("5. 数据统计")
            print("6. 数据质量检查")
            print("0. 返回主菜单")
            print("-" * 40)

            choice = input("请选择操作 (0-6): ").strip()

            if choice == "1":
                pattern_name = input("形态名称 (留空导出所有): ").strip()
                pattern_name = pattern_name if pattern_name else None

                output_path = input("输出路径 (留空自动生成): ").strip()
                output_path = output_path if output_path else None

                self.optimization_controller.export_data(pattern_name, output_path)
                input("\n按回车键继续...")

            elif choice == "2":
                print("\n📥 导入优化数据...")
                self._import_optimization_data()
                input("\n按回车键继续...")

            elif choice == "3":
                print("\n🧹 清理历史数据...")
                self._clean_historical_data()
                input("\n按回车键继续...")

            elif choice == "4":
                print("\n💾 数据备份...")
                self._backup_data()
                input("\n按回车键继续...")

            elif choice == "5":
                print("\n📊 数据统计...")
                self._data_statistics()
                input("\n按回车键继续...")

            elif choice == "6":
                print("\n🔍 数据质量检查...")
                self._data_quality_check()
                input("\n按回车键继续...")

            elif choice == "0":
                break
            else:
                print("❌ 无效选择，请重试")

    def _gui_launcher_menu(self):
        """图形界面启动菜单"""
        while True:
            print("\n🖥️  图形界面")
            print("-" * 40)
            print("1. 启动完整GUI界面")
            print("2. 启动优化仪表板")
            print("3. 启动性能监控")
            print("4. 启动版本管理器")
            print("5. 启动数据可视化")
            print("6. 启动插件市场")
            print("0. 返回主菜单")
            print("-" * 40)

            choice = input("请选择操作 (0-6): ").strip()

            if choice == "1":
                print("\n🚀 启动完整GUI界面...")
                self._launch_full_gui()
                input("\n按回车键继续...")

            elif choice == "2":
                print("\n🖥️  启动优化仪表板...")
                self._launch_optimization_dashboard()
                input("\n按回车键继续...")

            elif choice == "3":
                print("\n📊 启动性能监控...")
                self._launch_performance_monitor()
                input("\n按回车键继续...")

            elif choice == "4":
                print("\n📋 启动版本管理器...")
                self._launch_version_manager()
                input("\n按回车键继续...")

            elif choice == "5":
                print("\n📈 启动数据可视化...")
                self._launch_data_visualization()
                input("\n按回车键继续...")

            elif choice == "6":
                print("\n🔌 启动插件市场...")
                self._launch_plugin_market()
                input("\n按回车键继续...")

            elif choice == "0":
                break
            else:
                print("❌ 无效选择，请重试")

    def _plugin_management_menu(self):
        """插件管理菜单"""
        while True:
            print("\n🔌 插件管理")
            print("-" * 40)
            print("1. 列出已安装插件")
            print("2. 安装新插件")
            print("3. 卸载插件")
            print("4. 启用/禁用插件")
            print("5. 更新插件")
            print("6. 插件市场")
            print("0. 返回主菜单")
            print("-" * 40)

            choice = input("请选择操作 (0-6): ").strip()

            if choice == "1":
                print("\n📋 已安装插件:")
                self._list_installed_plugins()
                input("\n按回车键继续...")

            elif choice == "2":
                print("\n📦 安装新插件...")
                self._install_plugin()
                input("\n按回车键继续...")

            elif choice == "3":
                print("\n🗑️  卸载插件...")
                self._uninstall_plugin()
                input("\n按回车键继续...")

            elif choice == "4":
                print("\n⚙️  启用/禁用插件...")
                self._toggle_plugin()
                input("\n按回车键继续...")

            elif choice == "5":
                print("\n🔄 更新插件...")
                self._update_plugin()
                input("\n按回车键继续...")

            elif choice == "6":
                print("\n🏪 插件市场...")
                self._launch_plugin_market()
                input("\n按回车键继续...")

            elif choice == "0":
                break
            else:
                print("❌ 无效选择，请重试")

    def _help_menu(self):
        """帮助菜单"""
        while True:
            print("\n📚 帮助文档")
            print("-" * 40)
            print("1. 快速入门指南")
            print("2. 功能说明")
            print("3. 常见问题")
            print("4. 命令行参考")
            print("5. 示例代码")
            print("6. 系统要求")
            print("7. 联系支持")
            print("0. 返回主菜单")
            print("-" * 40)

            choice = input("请选择操作 (0-7): ").strip()

            if choice == "1":
                self._show_quick_start_guide()
                input("\n按回车键继续...")

            elif choice == "2":
                self._show_feature_description()
                input("\n按回车键继续...")

            elif choice == "3":
                self._show_faq()
                input("\n按回车键继续...")

            elif choice == "4":
                self._show_command_reference()
                input("\n按回车键继续...")

            elif choice == "5":
                self._show_example_code()
                input("\n按回车键继续...")

            elif choice == "6":
                self._show_system_requirements()
                input("\n按回车键继续...")

            elif choice == "7":
                self._show_contact_support()
                input("\n按回车键继续...")

            elif choice == "0":
                break
            else:
                print("❌ 无效选择，请重试")

    # 辅助方法实现
    def _run_system_diagnosis(self):
        """运行系统诊断"""
        try:
            print("🔍 正在进行系统诊断...")

            # 检查Python版本
            print(f"Python版本: {sys.version}")

            # 检查必要模块
            required_modules = [
                'PyQt5', 'pandas', 'numpy', 'matplotlib',
                'hikyuu', 'scikit-learn', 'sqlite3'
            ]

            for module in required_modules:
                try:
                    __import__(module)
                    print(f"✓ {module}: 已安装")
                except ImportError:
                    print(f"❌ {module}: 未安装")

            # 检查数据库连接
            try:
                from optimization.database_schema import OptimizationDatabaseManager
                db_manager = OptimizationDatabaseManager()
                print("✓ 数据库连接: 正常")
            except Exception as e:
                print(f"❌ 数据库连接: 失败 - {e}")

            # 检查形态算法
            try:
                patterns = self.pattern_manager.get_all_patterns()
                print(f"✓ 形态算法: {len(patterns)} 个")
            except Exception as e:
                print(f"❌ 形态算法: 失败 - {e}")

            print("\n✅ 系统诊断完成")

        except Exception as e:
            print(f"❌ 系统诊断失败: {e}")

    def _clean_system_cache(self):
        """清理系统缓存"""
        try:
            print("🧹 正在清理系统缓存...")

            # 清理临时文件
            import tempfile
            import shutil
            temp_dir = tempfile.gettempdir()
            hikyuu_temp = os.path.join(temp_dir, "hikyuu_*")

            # 清理日志文件
            log_dir = project_root / "logs"
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                        log_file.unlink()
                        print(f"✓ 清理日志文件: {log_file.name}")

            # 清理缓存目录
            cache_dir = project_root / "cache"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cache_dir.mkdir()
                print("✓ 清理缓存目录")

            print("✅ 系统缓存清理完成")

        except Exception as e:
            print(f"❌ 清理缓存失败: {e}")

    def _system_configuration_menu(self):
        """系统配置菜单"""
        while True:
            print("\n⚙️  系统配置")
            print("-" * 30)
            print("1. 查看当前配置")
            print("2. 修改配置")
            print("3. 重置配置")
            print("4. 导出配置")
            print("5. 导入配置")
            print("0. 返回上级菜单")
            print("-" * 30)

            choice = input("请选择操作 (0-5): ").strip()

            if choice == "1":
                self._show_current_config()
            elif choice == "2":
                self._modify_config()
            elif choice == "3":
                self._reset_config()
            elif choice == "4":
                self._export_config()
            elif choice == "5":
                self._import_config()
            elif choice == "0":
                break
            else:
                print("❌ 无效选择，请重试")

    def _launch_full_gui(self):
        """启动完整GUI界面"""
        try:
            print("🚀 正在启动HIkyuu-UI 2.0完整界面...")

            # 创建新的启动器实例以GUI模式运行
            gui_launcher = HIkyuuQuickStart(mode="gui")
            return gui_launcher.run()

        except Exception as e:
            print(f"❌ GUI启动失败: {e}")
            logger.error(f"GUI启动失败: {e}")

    def _launch_optimization_dashboard(self):
        """启动优化仪表板"""
        try:
            print("🖥️  正在启动优化仪表板...")
            self.optimization_controller.launch_dashboard()

        except Exception as e:
            print(f"❌ 优化仪表板启动失败: {e}")

    def _run_one_click_optimization(self):
        """运行一键优化"""
        try:
            print("⚡ 正在执行一键优化...")

            # 使用AutoTuner的一键优化功能
            result = self.auto_tuner.one_click_optimize()

            if result:
                print("✅ 一键优化完成")
                print(f"优化结果: {result}")
            else:
                print("⚠️  一键优化未发现需要优化的项目")

        except Exception as e:
            print(f"❌ 一键优化失败: {e}")
            logger.error(f"一键优化失败: {e}")

    def _show_quick_start_guide(self):
        """显示快速入门指南"""
        print("\n📖 HIkyuu-UI 2.0 快速入门指南")
        print("=" * 50)
        print("1. 首次使用")
        print("   - 运行系统初始化 (菜单 1-1)")
        print("   - 运行系统诊断 (菜单 1-4)")
        print("   - 检查所有组件是否正常")
        print()
        print("2. 基本功能")
        print("   - 启动完整GUI界面 (菜单 6-1)")
        print("   - 查看股票数据和技术分析")
        print("   - 使用形态识别功能")
        print()
        print("3. 高级功能")
        print("   - 算法优化 (菜单 3)")
        print("   - 性能评估 (菜单 2)")
        print("   - 插件管理 (菜单 7)")
        print()
        print("4. 建议流程")
        print("   ① 系统初始化和诊断")
        print("   ② 启动GUI界面体验基本功能")
        print("   ③ 尝试单个形态优化")
        print("   ④ 使用批量优化提升整体性能")
        print("   ⑤ 安装插件扩展功能")

    def _show_feature_description(self):
        """显示功能说明"""
        print("\n⚙️  HIkyuu-UI 2.0 功能说明")
        print("=" * 50)
        print("🔧 系统管理")
        print("   - 系统初始化、状态监控、诊断工具")
        print("   - 缓存管理、配置管理")
        print()
        print("📊 性能评估")
        print("   - 67种形态算法性能评估")
        print("   - 历史性能跟踪、对比分析")
        print()
        print("🚀 算法优化")
        print("   - 遗传算法、贝叶斯优化等多种方法")
        print("   - 智能优化、一键优化")
        print()
        print("📋 版本管理")
        print("   - 算法版本控制、回滚功能")
        print("   - 版本对比、性能跟踪")
        print()
        print("💾 数据管理")
        print("   - 数据导入导出、备份恢复")
        print("   - 数据质量检查、统计分析")
        print()
        print("🖥️  图形界面")
        print("   - 完整的股票分析界面")
        print("   - 实时数据、技术指标、形态识别")
        print()
        print("🔌 插件管理")
        print("   - 插件安装、更新、管理")
        print("   - 插件市场、自定义扩展")

    def _show_faq(self):
        """显示常见问题"""
        print("\n❓ 常见问题解答")
        print("=" * 50)
        print("Q: 首次运行出现错误怎么办？")
        print("A: 请先运行系统初始化(菜单1-1)和系统诊断(菜单1-4)")
        print("   检查是否缺少必要的依赖包")
        print()
        print("Q: 优化需要多长时间？")
        print("A: 单个形态优化通常需要5-30分钟")
        print("   批量优化可能需要几小时到一天")
        print()
        print("Q: 如何查看优化效果？")
        print("A: 可以通过性能评估(菜单2)和版本管理(菜单4)查看")
        print()
        print("Q: 插件如何安装？")
        print("A: 通过插件管理(菜单7)或插件市场安装")
        print()
        print("Q: 数据从哪里获取？")
        print("A: 系统支持多种数据源，包括本地文件和在线数据")
        print()
        print("Q: 如何备份数据？")
        print("A: 使用数据管理(菜单5)中的备份功能")
        print()
        print("Q: 系统支持哪些操作系统？")
        print("A: Windows、Linux、macOS")

    def _show_command_reference(self):
        """显示命令行参考"""
        print("\n💻 命令行参考")
        print("=" * 50)
        print("基本启动:")
        print("  python quick_start.py                    # 菜单模式")
        print("  python quick_start.py --mode gui         # GUI模式")
        print("  python quick_start.py --mode menu        # 菜单模式")
        print()
        print("直接启动GUI:")
        print("  python main.py                           # 启动完整GUI")
        print()
        print("优化系统:")
        print("  python optimization/main_controller.py init")
        print("  python optimization/main_controller.py status")
        print("  python optimization/main_controller.py optimize hammer")
        print("  python optimization/main_controller.py batch_optimize")
        print()
        print("仪表板:")
        print("  python optimization/optimization_dashboard.py")
        print()
        print("帮助:")
        print("  python quick_start.py --help             # 显示帮助")
        print("  python main.py --help                    # GUI帮助")

    def _show_system_requirements(self):
        """显示系统要求"""
        print("\n💻 系统要求")
        print("=" * 50)
        print("操作系统:")
        print("  - Windows 10/11")
        print("  - Linux (Ubuntu 18.04+)")
        print("  - macOS 10.14+")
        print()
        print("Python版本:")
        print("  - Python 3.11+ (推荐)")
        print("  - Python 3.8+ (最低要求)")
        print()
        print("内存要求:")
        print("  - 最低: 4GB RAM")
        print("  - 推荐: 8GB+ RAM")
        print("  - 大数据集: 16GB+ RAM")
        print()
        print("存储空间:")
        print("  - 程序: 1GB")
        print("  - 数据: 5GB+ (取决于数据量)")
        print()
        print("必要依赖:")
        print("  - PyQt5")
        print("  - pandas, numpy")
        print("  - matplotlib")
        print("  - hikyuu")
        print("  - scikit-learn")
        print("  - sqlite3")

    # GUI组件集成方法
    def _batch_evaluate_patterns(self):
        """批量评估形态"""
        print("🔄 启动批量评估界面...")
        try:
            from gui.dialogs.performance_evaluation_dialog import PerformanceEvaluationDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = PerformanceEvaluationDialog(None)
            dialog.start_batch_evaluation()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 批量评估失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _performance_comparison_analysis(self):
        """性能对比分析"""
        print("🔄 启动性能对比分析...")
        try:
            from optimization.optimization_dashboard import OptimizationDashboard
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dashboard = OptimizationDashboard()
            dashboard.show()

        except Exception as e:
            print(f"❌ 性能对比分析失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _generate_evaluation_report(self):
        """生成评估报告"""
        print("🔄 启动评估报告生成...")
        try:
            from gui.dialogs.performance_evaluation_dialog import PerformanceEvaluationDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = PerformanceEvaluationDialog(None)
            dialog.generate_report()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 生成评估报告失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _view_performance_history(self):
        """查看性能历史"""
        print("🔄 启动性能历史查看...")
        try:
            from optimization.optimization_dashboard import OptimizationDashboard
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dashboard = OptimizationDashboard()
            dashboard.show()

        except Exception as e:
            print(f"❌ 查看性能历史失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _custom_optimization_menu(self):
        """自定义优化菜单"""
        print("🔄 启动自定义优化界面...")
        try:
            from gui.dialogs.system_optimizer_dialog import SystemOptimizerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = SystemOptimizerDialog(None)
            dialog.exec_()

        except Exception as e:
            print(f"❌ 自定义优化失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _view_optimization_history(self):
        """查看优化历史"""
        print("🔄 启动优化历史查看...")
        try:
            from optimization.optimization_dashboard import OptimizationDashboard
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dashboard = OptimizationDashboard()
            dashboard.show()

        except Exception as e:
            print(f"❌ 查看优化历史失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _version_comparison(self):
        """版本对比"""
        print("🔄 启动版本对比界面...")
        try:
            from gui.dialogs.version_manager_dialog import VersionManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = VersionManagerDialog(None)
            dialog.show_version_comparison()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 版本对比失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _delete_version(self):
        """删除版本"""
        print("🔄 启动版本删除界面...")
        try:
            from gui.dialogs.version_manager_dialog import VersionManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = VersionManagerDialog(None)
            dialog.exec_()

        except Exception as e:
            print(f"❌ 版本删除失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _version_statistics(self):
        """版本统计"""
        print("🔄 启动版本统计界面...")
        try:
            from gui.dialogs.version_manager_dialog import VersionManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = VersionManagerDialog(None)
            dialog.show_statistics()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 版本统计失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _version_rollback(self):
        """版本回滚"""
        print("🔄 启动版本回滚界面...")
        try:
            from gui.dialogs.version_manager_dialog import VersionManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = VersionManagerDialog(None)
            dialog.exec_()

        except Exception as e:
            print(f"❌ 版本回滚失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _import_optimization_data(self):
        """导入优化数据"""
        print("🔄 启动数据导入界面...")
        try:
            from gui.dialogs.data_export_dialog import DataExportDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = DataExportDialog(None)
            dialog.switch_to_import_mode()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 数据导入失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _clean_historical_data(self):
        """清理历史数据"""
        print("🔄 启动历史数据清理...")
        try:
            from gui.dialogs.data_quality_dialog import DataQualityDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = DataQualityDialog(None)
            dialog.start_data_cleanup()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 历史数据清理失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _backup_data(self):
        """备份数据"""
        print("🔄 启动数据备份界面...")
        try:
            from gui.dialogs.data_export_dialog import DataExportDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = DataExportDialog(None)
            dialog.switch_to_backup_mode()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 数据备份失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _data_statistics(self):
        """数据统计"""
        print("🔄 启动数据统计界面...")
        try:
            from gui.dialogs.data_quality_dialog import DataQualityDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = DataQualityDialog(None)
            dialog.show_statistics()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 数据统计失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _data_quality_check(self):
        """数据质量检查"""
        print("🔄 启动数据质量检查界面...")
        try:
            from gui.dialogs.data_quality_dialog import DataQualityDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = DataQualityDialog(None)
            dialog.exec_()

        except Exception as e:
            print(f"❌ 数据质量检查失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _launch_performance_monitor(self):
        """启动性能监控"""
        print("🔄 启动性能监控界面...")
        try:
            from optimization.optimization_dashboard import OptimizationDashboard
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dashboard = OptimizationDashboard()
            dashboard.start_monitoring()
            dashboard.show()

        except Exception as e:
            print(f"❌ 性能监控启动失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _launch_version_manager(self):
        """启动版本管理器"""
        print("🔄 启动版本管理器...")
        try:
            from gui.dialogs.version_manager_dialog import VersionManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = VersionManagerDialog(None)
            dialog.exec_()

        except Exception as e:
            print(f"❌ 版本管理器启动失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _launch_data_visualization(self):
        """启动数据可视化"""
        print("🔄 启动数据可视化界面...")
        try:
            from gui.widgets.analysis_widget import AnalysisWidget
            from PyQt5.QtWidgets import QApplication, QMainWindow

            if not QApplication.instance():
                app = QApplication([])

            window = QMainWindow()
            widget = AnalysisWidget(window)
            window.setCentralWidget(widget)
            window.setWindowTitle("数据可视化")
            window.show()

        except Exception as e:
            print(f"❌ 数据可视化启动失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _launch_plugin_market(self):
        """启动插件市场"""
        print("🔄 启动插件市场...")
        try:
            from gui.dialogs.enhanced_plugin_market_dialog import EnhancedPluginMarketDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = EnhancedPluginMarketDialog(None)
            dialog.exec_()

        except Exception as e:
            print(f"❌ 插件市场启动失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _list_installed_plugins(self):
        """列出已安装插件"""
        print("🔄 启动插件管理界面...")
        try:
            from gui.dialogs.plugin_manager_dialog import PluginManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = PluginManagerDialog(None)
            dialog.show_installed_plugins()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 插件列表显示失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _install_plugin(self):
        """安装插件"""
        print("🔄 启动插件安装界面...")
        try:
            from gui.dialogs.plugin_manager_dialog import PluginManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = PluginManagerDialog(None)
            dialog.show_plugin_installation()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 插件安装失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _uninstall_plugin(self):
        """卸载插件"""
        print("🔄 启动插件卸载界面...")
        try:
            from gui.dialogs.plugin_manager_dialog import PluginManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = PluginManagerDialog(None)
            dialog.show_plugin_uninstallation()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 插件卸载失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _toggle_plugin(self):
        """切换插件状态"""
        print("🔄 启动插件状态管理...")
        try:
            from gui.dialogs.plugin_manager_dialog import PluginManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = PluginManagerDialog(None)
            dialog.exec_()

        except Exception as e:
            print(f"❌ 插件状态切换失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _update_plugin(self):
        """更新插件"""
        print("🔄 启动插件更新界面...")
        try:
            from gui.dialogs.plugin_manager_dialog import PluginManagerDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = PluginManagerDialog(None)
            dialog.show_plugin_updates()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 插件更新失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _show_current_config(self):
        """显示当前配置"""
        print("🔄 启动配置查看界面...")
        try:
            from gui.dialogs.settings_dialog import SettingsDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = SettingsDialog(None)
            dialog.show_current_config()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 配置查看失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _modify_config(self):
        """修改配置"""
        print("🔄 启动配置修改界面...")
        try:
            from gui.dialogs.settings_dialog import SettingsDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = SettingsDialog(None)
            dialog.exec_()

        except Exception as e:
            print(f"❌ 配置修改失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _reset_config(self):
        """重置配置"""
        print("🔄 启动配置重置界面...")
        try:
            from gui.dialogs.settings_dialog import SettingsDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = SettingsDialog(None)
            dialog.reset_to_defaults()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 配置重置失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _export_config(self):
        """导出配置"""
        print("🔄 启动配置导出界面...")
        try:
            from gui.dialogs.settings_dialog import SettingsDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = SettingsDialog(None)
            dialog.export_config()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 配置导出失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _import_config(self):
        """导入配置"""
        print("🔄 启动配置导入界面...")
        try:
            from gui.dialogs.settings_dialog import SettingsDialog
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication([])

            dialog = SettingsDialog(None)
            dialog.import_config()
            dialog.exec_()

        except Exception as e:
            print(f"❌ 配置导入失败: {e}")
            print("💡 请尝试使用GUI模式: python quick_start.py --gui")

    def _show_example_code(self):
        """显示示例代码"""
        print("\n💻 HIkyuu-UI 示例代码")
        print("=" * 50)
        print("1. 基本使用示例:")
        print("```python")
        print("from hikyuu import *")
        print("from core.services import StockService")
        print()
        print("# 获取股票数据")
        print("stock_service = StockService()")
        print("stock_data = stock_service.get_stock_data('000001')")
        print("print(stock_data.head())")
        print("```")
        print()
        print("2. 技术指标示例:")
        print("```python")
        print("from features.basic_indicators import BasicIndicators")
        print()
        print("# 计算技术指标")
        print("indicators = BasicIndicators()")
        print("ma5 = indicators.ma(stock_data, 5)")
        print("ma20 = indicators.ma(stock_data, 20)")
        print("```")
        print()
        print("3. 形态识别示例:")
        print("```python")
        print("from analysis.pattern_recognition import PatternRecognizer")
        print()
        print("# 识别形态")
        print("recognizer = PatternRecognizer()")
        print("patterns = recognizer.recognize(stock_data)")
        print("print(patterns)")
        print("```")
        print()
        print("4. 策略回测示例:")
        print("```python")
        print("from backtest.unified_backtest_engine import UnifiedBacktestEngine")
        print()
        print("# 创建回测引擎")
        print("engine = UnifiedBacktestEngine()")
        print("result = engine.run_backtest(strategy, stock_data)")
        print("print(result.summary())")
        print("```")

    def _show_contact_support(self):
        """显示联系支持"""
        print("\n📞 联系支持")
        print("=" * 50)
        print("如果您遇到问题或需要帮助，请通过以下方式联系我们:")
        print()
        print("🌐 官方网站:")
        print("   https://hikyuu.org")
        print()
        print("📧 邮箱支持:")
        print("   support@hikyuu.org")
        print()
        print("💬 社区论坛:")
        print("   https://forum.hikyuu.org")
        print()
        print("🐛 问题反馈:")
        print("   https://github.com/fasiondog/hikyuu/issues")
        print()
        print("📚 文档中心:")
        print("   https://docs.hikyuu.org")
        print()
        print("🎥 视频教程:")
        print("   https://www.bilibili.com/hikyuu")
        print()
        print("📱 微信群:")
        print("   请添加微信号: hikyuu-support")
        print()
        print("🔧 常见问题:")
        print("   1. 安装问题: 请检查Python版本和依赖")
        print("   2. 数据问题: 请检查数据源配置")
        print("   3. 性能问题: 请检查系统资源")
        print("   4. 功能问题: 请查看帮助文档")
        print()
        print("📝 提交问题时请包含:")
        print("   - 操作系统版本")
        print("   - Python版本")
        print("   - HIkyuu版本")
        print("   - 错误信息截图")
        print("   - 重现步骤")


def create_argument_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="HIkyuu-UI 2.0 系统快速启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
启动模式:
  gui     启动完整的图形界面
  menu    启动命令行菜单界面 (默认)
  
示例:
  python quick_start.py                    # 菜单模式
  python quick_start.py --mode gui         # GUI模式
  python quick_start.py --mode menu        # 菜单模式
        """
    )

    parser.add_argument(
        "--mode", "-m",
        choices=["gui", "menu", "command"],
        default="menu",
        help="启动模式 (默认: menu)"
    )

    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="启用调试模式"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="HIkyuu-UI 2.0"
    )

    return parser


def main():
    """主函数"""
    try:
        # 解析命令行参数
        parser = create_argument_parser()
        args = parser.parse_args()

        # 设置日志级别
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        # 确保日志目录存在
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        # 创建并运行启动器
        launcher = HIkyuuQuickStart(mode=args.mode)
        exit_code = launcher.run()

        sys.exit(exit_code or 0)

    except KeyboardInterrupt:
        print("\n\n⚠️  程序被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"启动器运行失败: {e}")
        print(f"❌ 程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
