#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HiKyuu 形态识别算法优化系统快速启动脚本
提供简单的菜单界面，方便用户快速使用各种功能
"""

from optimization.main_controller import OptimizationController
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def show_banner():
    """显示启动横幅"""
    print("=" * 70)
    print("🚀 HiKyuu 形态识别算法优化系统")
    print("=" * 70)
    print("专业级股票形态识别与算法优化平台")
    print("✨ 67种形态算法 | 🧠 智能优化 | 性能评估 | 版本管理")
    print("=" * 70)
    print()


def show_main_menu():
    """显示主菜单"""
    print("📋 主菜单")
    print("-" * 40)
    print("1. 🔧 系统管理")
    print("2. 性能评估")
    print("3. 🚀 算法优化")
    print("4. 📋 版本管理")
    print("5. 💾 数据管理")
    print("6. 🖥️  图形界面")
    print("7. 📚 帮助文档")
    print("0. 🚪 退出系统")
    print("-" * 40)


def system_management_menu(controller):
    """系统管理菜单"""
    while True:
        print("\n🔧 系统管理")
        print("-" * 30)
        print("1. 初始化系统")
        print("2. 查看系统状态")
        print("3. 列出所有形态")
        print("4. 系统诊断")
        print("0. 返回主菜单")
        print("-" * 30)

        choice = input("请选择操作 (0-4): ").strip()

        if choice == "1":
            print("\n🔧 正在初始化系统...")
            controller.initialize_system()
            input("\n按回车键继续...")

        elif choice == "2":
            print("\n系统状态:")
            controller.show_system_status()
            input("\n按回车键继续...")

        elif choice == "3":
            print("\n📋 形态列表:")
            controller.list_patterns()
            input("\n按回车键继续...")

        elif choice == "4":
            print("\n🔍 运行系统诊断...")
            os.system("python test_optimization_system.py")
            input("\n按回车键继续...")

        elif choice == "0":
            break
        else:
            print("❌ 无效选择，请重试")


def performance_evaluation_menu(controller):
    """性能评估菜单"""
    while True:
        print("\n性能评估")
        print("-" * 30)
        print("1. 评估单个形态")
        print("2. 评估所有形态")
        print("3. 性能对比分析")
        print("4. 生成评估报告")
        print("0. 返回主菜单")
        print("-" * 30)

        choice = input("请选择操作 (0-4): ").strip()

        if choice == "1":
            pattern_name = input("请输入形态名称 (如: hammer): ").strip()
            if pattern_name:
                dataset_count = input("测试数据集数量 (默认3): ").strip()
                dataset_count = int(dataset_count) if dataset_count.isdigit() else 3

                print(f"\n评估形态: {pattern_name}")
                controller.evaluate_pattern(pattern_name, dataset_count)
            else:
                print("❌ 形态名称不能为空")
            input("\n按回车键继续...")

        elif choice == "2":
            print("\n评估所有形态...")
            print("⚠️  这可能需要较长时间，请耐心等待")
            confirm = input("确认继续？(y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                # 这里可以添加批量评估逻辑
                print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "3":
            print("\n↑ 性能对比分析...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "4":
            print("\n📄 生成评估报告...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "0":
            break
        else:
            print("❌ 无效选择，请重试")


def algorithm_optimization_menu(controller):
    """算法优化菜单"""
    while True:
        print("\n🚀 算法优化")
        print("-" * 30)
        print("1. 优化单个形态")
        print("2. 批量优化")
        print("3. 智能优化")
        print("4. 自定义优化")
        print("5. 查看优化历史")
        print("0. 返回主菜单")
        print("-" * 30)

        choice = input("请选择操作 (0-5): ").strip()

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

                controller.optimize_pattern(pattern_name, method, iterations)
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
                controller.batch_optimize(method, iterations)
            input("\n按回车键继续...")

        elif choice == "3":
            print("\n🧠 智能优化...")
            threshold = input("性能阈值 (0-1, 默认0.7): ").strip()
            threshold = float(threshold) if threshold else 0.7

            target = input("改进目标 (0-1, 默认0.1): ").strip()
            target = float(target) if target else 0.1

            controller.smart_optimize(threshold, target)
            input("\n按回车键继续...")

        elif choice == "4":
            print("\n⚙️  自定义优化...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "5":
            print("\n📋 优化历史...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "0":
            break
        else:
            print("❌ 无效选择，请重试")


def version_management_menu(controller):
    """版本管理菜单"""
    while True:
        print("\n📋 版本管理")
        print("-" * 30)
        print("1. 查看形态版本")
        print("2. 激活指定版本")
        print("3. 版本对比")
        print("4. 删除版本")
        print("5. 版本统计")
        print("0. 返回主菜单")
        print("-" * 30)

        choice = input("请选择操作 (0-5): ").strip()

        if choice == "1":
            pattern_name = input("请输入形态名称 (如: hammer): ").strip()
            if pattern_name:
                controller.show_versions(pattern_name)
            else:
                print("❌ 形态名称不能为空")
            input("\n按回车键继续...")

        elif choice == "2":
            pattern_name = input("请输入形态名称: ").strip()
            version_num = input("请输入版本号: ").strip()
            if pattern_name and version_num.isdigit():
                controller.activate_version(pattern_name, int(version_num))
            else:
                print("❌ 请输入有效的形态名称和版本号")
            input("\n按回车键继续...")

        elif choice == "3":
            print("\n版本对比...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "4":
            print("\n🗑️  删除版本...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "5":
            print("\n↑ 版本统计...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "0":
            break
        else:
            print("❌ 无效选择，请重试")


def data_management_menu(controller):
    """数据管理菜单"""
    while True:
        print("\n💾 数据管理")
        print("-" * 30)
        print("1. 导出优化数据")
        print("2. 导入优化数据")
        print("3. 清理历史数据")
        print("4. 数据备份")
        print("5. 数据统计")
        print("0. 返回主菜单")
        print("-" * 30)

        choice = input("请选择操作 (0-5): ").strip()

        if choice == "1":
            pattern_name = input("形态名称 (留空导出所有): ").strip()
            pattern_name = pattern_name if pattern_name else None

            output_path = input("输出路径 (留空自动生成): ").strip()
            output_path = output_path if output_path else None

            controller.export_data(pattern_name, output_path)
            input("\n按回车键继续...")

        elif choice == "2":
            print("\n📥 导入优化数据...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "3":
            print("\n🧹 清理历史数据...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "4":
            print("\n💾 数据备份...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "5":
            print("\n数据统计...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "0":
            break
        else:
            print("❌ 无效选择，请重试")


def gui_menu():
    """图形界面菜单"""
    while True:
        print("\n🖥️  图形界面")
        print("-" * 30)
        print("1. 启动优化仪表板")
        print("2. 启动性能监控")
        print("3. 启动版本管理器")
        print("4. 启动数据可视化")
        print("0. 返回主菜单")
        print("-" * 30)

        choice = input("请选择操作 (0-4): ").strip()

        if choice == "1":
            print("\n🖥️  启动优化仪表板...")
            try:
                os.system("python optimization/optimization_dashboard.py")
            except Exception as e:
                print(f"❌ 启动失败: {e}")
            input("\n按回车键继续...")

        elif choice == "2":
            print("\n启动性能监控...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "3":
            print("\n📋 启动版本管理器...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "4":
            print("\n↑ 启动数据可视化...")
            print("功能开发中...")
            input("\n按回车键继续...")

        elif choice == "0":
            break
        else:
            print("❌ 无效选择，请重试")


def help_menu():
    """帮助菜单"""
    while True:
        print("\n📚 帮助文档")
        print("-" * 30)
        print("1. 快速入门指南")
        print("2. 功能说明")
        print("3. 常见问题")
        print("4. 命令行参考")
        print("5. 示例代码")
        print("6. 联系支持")
        print("0. 返回主菜单")
        print("-" * 30)

        choice = input("请选择操作 (0-6): ").strip()

        if choice == "1":
            print("\n📖 快速入门指南")
            print("-" * 40)
            print("1. 首次使用请先初始化系统")
            print("2. 建议先运行系统诊断检查环境")
            print("3. 可以从单个形态优化开始体验")
            print("4. 批量优化适合在空闲时运行")
            print("5. 智能优化会自动选择需要优化的形态")
            input("\n按回车键继续...")

        elif choice == "2":
            print("\n⚙️  功能说明")
            print("-" * 40)
            print("• 系统管理: 初始化、状态查看、诊断")
            print("• 性能评估: 单个/批量评估、对比分析")
            print("• 算法优化: 多种优化算法、智能优化")
            print("• 版本管理: 版本切换、对比、统计")
            print("• 数据管理: 导入导出、备份、清理")
            print("• 图形界面: 可视化仪表板和监控")
            input("\n按回车键继续...")

        elif choice == "3":
            print("\n❓ 常见问题")
            print("-" * 40)
            print("Q: 首次运行出错怎么办？")
            print("A: 请先运行系统初始化和诊断")
            print()
            print("Q: 优化需要多长时间？")
            print("A: 单个形态通常几分钟，批量优化可能需要几小时")
            print()
            print("Q: 如何查看优化效果？")
            print("A: 可以通过性能评估和版本对比查看")
            input("\n按回车键继续...")

        elif choice == "4":
            print("\n💻 命令行参考")
            print("-" * 40)
            print("python optimization/main_controller.py init")
            print("python optimization/main_controller.py status")
            print("python optimization/main_controller.py optimize hammer")
            print("python optimization/main_controller.py batch_optimize")
            print("python optimization/main_controller.py dashboard")
            print()
            print("详细参数请运行: python optimization/main_controller.py --help")
            input("\n按回车键继续...")

        elif choice == "5":
            print("\n📝 示例代码")
            print("-" * 40)
            print("运行示例脚本:")
            print("python optimization_example.py")
            print()
            print("查看具体示例:")
            print("python optimization_example.py 1  # 基本使用")
            print("python optimization_example.py 2  # 单个优化")
            input("\n按回车键继续...")

        elif choice == "6":
            print("\n📞 联系支持")
            print("-" * 40)
            print("• GitHub Issues: 提交问题和建议")
            print("• 邮件支持: 发送详细问题描述")
            print("• 文档网站: 查看最新文档")
            print("• 社区论坛: 与其他用户交流")
            input("\n按回车键继续...")

        elif choice == "0":
            break
        else:
            print("❌ 无效选择，请重试")


def main():
    """主函数"""
    show_banner()

    # 创建控制器
    try:
        controller = OptimizationController(debug_mode=False)
        print("✅ 系统初始化成功")
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        print("请检查环境配置或运行系统诊断")
        return

    # 主循环
    while True:
        try:
            show_main_menu()
            choice = input("请选择操作 (0-7): ").strip()

            if choice == "1":
                system_management_menu(controller)
            elif choice == "2":
                performance_evaluation_menu(controller)
            elif choice == "3":
                algorithm_optimization_menu(controller)
            elif choice == "4":
                version_management_menu(controller)
            elif choice == "5":
                data_management_menu(controller)
            elif choice == "6":
                gui_menu()
            elif choice == "7":
                help_menu()
            elif choice == "0":
                print("\n👋 感谢使用 HiKyuu 形态识别算法优化系统！")
                break
            else:
                print("❌ 无效选择，请重试")

        except KeyboardInterrupt:
            print("\n\n⚠️  操作被用户中断")
            confirm = input("确认退出？(y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            input("按回车键继续...")


if __name__ == "__main__":
    main()
