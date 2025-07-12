#!/usr/bin/env python3
"""
系统维护工具使用示例

这个示例展示了如何使用系统维护工具进行：
1. 编程方式的系统维护
2. GUI界面的系统维护
"""

from system_optimizer import (
    SystemOptimizerService,
    OptimizationLevel,
    OptimizationConfig
)
import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def example_programmatic_maintenance():
    """编程方式的系统维护示例"""
    print("=== 编程方式的系统维护 ===")

    # 创建系统优化器服务
    service = SystemOptimizerService()

    try:
        # 初始化服务
        await service.initialize_async()
        print("✓ 服务初始化成功")

        # 分析系统状态
        print("\n1. 分析系统状态...")
        analysis = await service.analyze_system()
        print(f"   - 总文件数: {analysis.get('total_files', 0)}")
        print(f"   - Python文件数: {analysis.get('python_files', 0)}")
        print(f"   - 大文件数: {len(analysis.get('large_files', []))}")
        print(f"   - 缓存文件数: {len(analysis.get('cache_files', []))}")
        print(f"   - 临时文件数: {len(analysis.get('temp_files', []))}")

        # 获取维护建议
        print("\n2. 获取维护建议...")
        suggestions = await service.get_optimization_suggestions()
        for i, suggestion in enumerate(suggestions[:5], 1):
            print(f"   {i}. {suggestion}")

        # 执行轻度维护
        print("\n3. 执行轻度维护...")
        result = await service.optimize_system(OptimizationLevel.LIGHT)

        print(f"   - 维护级别: {result.level.value}")
        print(f"   - 清理文件: {result.files_cleaned} 个")
        print(f"   - 优化文件: {result.files_optimized} 个")
        print(f"   - 释放空间: {result.bytes_freed / 1024 / 1024:.2f} MB")
        print(f"   - 耗时: {result.duration.total_seconds():.2f} 秒")
        print(f"   - 成功率: {result.success_rate:.2%}")

    except Exception as e:
        print(f"✗ 维护过程中发生错误: {e}")

    finally:
        # 清理服务
        await service.dispose_async()
        print("\n✓ 服务清理完成")


def example_gui_maintenance():
    """GUI界面的系统维护示例"""
    print("\n=== GUI界面的系统维护 ===")

    try:
        print("GUI界面使用说明：")
        print("1. 选择维护级别（轻度/中度/深度/自定义）")
        print("2. 配置维护选项（如果选择自定义）")
        print("3. 点击'开始维护'按钮")
        print("4. 查看维护进度和结果")
        print("5. 查看维护历史记录")
        print("\n要使用GUI界面，请运行以下代码：")
        print("```python")
        print("from PyQt5.QtWidgets import QApplication")
        print(
            "from gui.dialogs.system_optimizer_dialog import show_system_optimizer_dialog")
        print("app = QApplication([])")
        print("show_system_optimizer_dialog()")
        print("app.exec_()")
        print("```")
        print("✓ GUI界面示例说明完成")

    except Exception as e:
        print(f"✗ GUI示例失败: {e}")


def example_custom_maintenance():
    """自定义维护配置示例"""
    print("\n=== 自定义维护配置 ===")

    # 创建自定义配置
    custom_config = OptimizationConfig(
        level=OptimizationLevel.CUSTOM,
        clean_cache=True,           # 清理缓存文件
        clean_temp_files=True,      # 清理临时文件
        clean_logs=False,           # 不清理日志文件
        optimize_imports=True,      # 优化导入语句
        optimize_memory=True,       # 内存优化
        backup_before_optimize=True,  # 维护前备份
        log_retention_days=30,      # 日志保留30天
        max_file_size_mb=100       # 大文件阈值100MB
    )

    print("自定义配置:")
    print(f"  - 维护级别: {custom_config.level.value}")
    print(f"  - 清理缓存: {custom_config.clean_cache}")
    print(f"  - 清理临时文件: {custom_config.clean_temp_files}")
    print(f"  - 清理日志: {custom_config.clean_logs}")
    print(f"  - 优化导入: {custom_config.optimize_imports}")
    print(f"  - 内存优化: {custom_config.optimize_memory}")
    print(f"  - 维护前备份: {custom_config.backup_before_optimize}")
    print(f"  - 日志保留天数: {custom_config.log_retention_days}")
    print(f"  - 大文件阈值: {custom_config.max_file_size_mb} MB")

    print("\n使用自定义配置进行维护...")
    print("（实际维护过程请使用 example_programmatic_maintenance 函数）")


async def main():
    """主函数"""
    print("系统维护工具使用示例")
    print("=" * 50)

    # 1. 编程方式的系统维护
    await example_programmatic_maintenance()

    # 2. 自定义维护配置
    example_custom_maintenance()

    # 3. GUI界面的系统维护（仅演示，不实际运行）
    example_gui_maintenance()

    print("\n" + "=" * 50)
    print("示例完成！")
    print("\n使用建议：")
    print("1. 日常维护建议使用轻度或中度维护")
    print("2. 定期（如每月）进行一次深度维护")
    print("3. 重要操作前建议开启维护前备份")
    print("4. 可以通过GUI界面进行交互式维护")
    print("5. 可以通过编程方式集成到自动化脚本中")

if __name__ == "__main__":
    asyncio.run(main())
