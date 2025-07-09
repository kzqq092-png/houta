#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指标系统重构进度检查脚本
用于检查指标系统重构的进度，并生成详细的报告
"""

import os
import sys
import re
import logging
import argparse
from typing import List, Dict, Tuple, Set, Optional
import json
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='refactor_progress_report.txt',
    filemode='w'
)

# 添加控制台处理器
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logger = logging.getLogger('refactor_progress')

# 重构计划中的任务
REFACTOR_TASKS = {
    "phase0": {
        "name": "准备工作",
        "tasks": [
            {"id": "test_fixture", "name": "创建测试数据夹具", "files": ["test/fixtures/stock_data_100d.csv", "test/fixtures/stock_data_500d.csv"]},
            {"id": "test_cases", "name": "编写测试用例", "files": ["test/test_indicators_system.py", "test/test_new_indicator_system.py"]}
        ]
    },
    "phase1": {
        "name": "基础设施构建",
        "tasks": [
            {"id": "db_init", "name": "创建并初始化数据库", "files": ["db/indicators.db", "db/initialize_indicators.py", "db/models/indicator_models.py"]},
            {"id": "indicator_lib", "name": "创建统一指标算法库", "files": ["core/indicators/library/trends.py", "core/indicators/library/oscillators.py",
                                                                   "core/indicators/library/volumes.py", "core/indicators/library/volatility.py", "core/indicators/library/patterns.py"]},
            {"id": "indicator_service", "name": "开发核心服务", "files": ["core/indicator_service.py"]},
            {"id": "indicator_adapter", "name": "开发指标适配器", "files": ["core/indicator_adapter.py"]},
            {"id": "example_code", "name": "创建示例代码", "files": ["examples/indicator_system_demo.py"]},
            {"id": "refactor_summary", "name": "编写重构总结", "files": ["INDICATOR_REFACTOR_SUMMARY.md"]}
        ]
    },
    "phase2": {
        "name": "增量替换与集成",
        "tasks": [
            {"id": "ui_refactor", "name": "重构UI层", "files": ["gui/widgets/analysis_widget.py"],
                "pattern": "from\\s+core\\.indicator_service\\s+import"},
            {"id": "core_refactor", "name": "重构核心逻辑层", "files": ["core/stock_screener.py"], "pattern": "from\\s+core\\.indicator_service\\s+import"}
        ]
    },
    "phase3": {
        "name": "清理与收尾",
        "tasks": [
            {"id": "delete_files", "name": "删除冗余文件", "files": [
                "indicators_algo.py", "features/basic_indicators.py", "features/advanced_indicators.py"], "check_not_exists": True},
            {"id": "update_docs", "name": "更新文档", "files": ["README.md"], "pattern": "技术指标系统"}
        ]
    },
    "phase4": {
        "name": "插件系统实现",
        "tasks": [
            {"id": "plugin_manager", "name": "完善PluginManager", "files": ["core/plugin_manager.py"], "pattern": "register_indicators"},
            {"id": "example_plugin", "name": "创建示例插件", "files": [
                "plugins/examples/my_custom_indicator/plugin_info.py", "plugins/examples/my_custom_indicator/indicators.py"]}
        ]
    }
}

# 自动化脚本文件
AUTOMATION_SCRIPTS = [
    {"name": "UI层迁移脚本", "file": "update_ui_indicator_references.py"},
    {"name": "核心逻辑层迁移脚本", "file": "update_core_indicator_references.py"},
    {"name": "依赖检查和清理脚本", "file": "check_dependencies_and_cleanup.py"},
    {"name": "执行指南", "file": "INDICATOR_REFACTOR_EXECUTION_GUIDE.md"}
]


def check_file_exists(file_path: str) -> bool:
    """
    检查文件是否存在

    参数:
        file_path: 文件路径

    返回:
        bool: 文件是否存在
    """
    return os.path.exists(file_path)


def check_pattern_in_file(file_path: str, pattern: str) -> bool:
    """
    检查文件中是否包含指定模式

    参数:
        file_path: 文件路径
        pattern: 正则表达式模式

    返回:
        bool: 文件中是否包含指定模式
    """
    if not os.path.exists(file_path):
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return bool(re.search(pattern, content))
    except Exception as e:
        logger.error(f"检查文件 {file_path} 时发生错误: {str(e)}")
        return False


def check_task_status(task: Dict) -> bool:
    """
    检查任务状态

    参数:
        task: 任务字典

    返回:
        bool: 任务是否完成
    """
    # 如果任务需要检查文件不存在
    if task.get("check_not_exists", False):
        return all(not check_file_exists(file) for file in task["files"])

    # 检查文件是否存在
    files_exist = all(check_file_exists(file) for file in task["files"])

    # 如果有模式需要检查
    if "pattern" in task:
        return files_exist and any(check_pattern_in_file(file, task["pattern"]) for file in task["files"])

    return files_exist


def check_phase_status(phase: Dict) -> Tuple[int, int]:
    """
    检查阶段状态

    参数:
        phase: 阶段字典

    返回:
        Tuple[int, int]: 已完成任务数和总任务数
    """
    completed_tasks = 0
    total_tasks = len(phase["tasks"])

    for task in phase["tasks"]:
        if check_task_status(task):
            completed_tasks += 1

    return completed_tasks, total_tasks


def check_automation_scripts() -> Tuple[int, int]:
    """
    检查自动化脚本

    返回:
        Tuple[int, int]: 已完成脚本数和总脚本数
    """
    completed_scripts = 0
    total_scripts = len(AUTOMATION_SCRIPTS)

    for script in AUTOMATION_SCRIPTS:
        if check_file_exists(script["file"]):
            completed_scripts += 1

    return completed_scripts, total_scripts


def generate_progress_report() -> Dict:
    """
    生成进度报告

    返回:
        Dict: 进度报告字典
    """
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "phases": {},
        "automation_scripts": {},
        "overall_progress": 0.0
    }

    total_completed_tasks = 0
    total_tasks = 0

    # 检查每个阶段的状态
    for phase_id, phase in REFACTOR_TASKS.items():
        completed_tasks, phase_total_tasks = check_phase_status(phase)
        total_completed_tasks += completed_tasks
        total_tasks += phase_total_tasks

        phase_progress = completed_tasks / phase_total_tasks if phase_total_tasks > 0 else 0.0

        report["phases"][phase_id] = {
            "name": phase["name"],
            "completed_tasks": completed_tasks,
            "total_tasks": phase_total_tasks,
            "progress": phase_progress,
            "tasks": []
        }

        # 检查每个任务的状态
        for task in phase["tasks"]:
            task_status = check_task_status(task)
            report["phases"][phase_id]["tasks"].append({
                "id": task["id"],
                "name": task["name"],
                "status": "completed" if task_status else "pending"
            })

    # 检查自动化脚本
    completed_scripts, total_scripts = check_automation_scripts()
    report["automation_scripts"] = {
        "completed_scripts": completed_scripts,
        "total_scripts": total_scripts,
        "progress": completed_scripts / total_scripts if total_scripts > 0 else 0.0,
        "scripts": []
    }

    for script in AUTOMATION_SCRIPTS:
        script_status = check_file_exists(script["file"])
        report["automation_scripts"]["scripts"].append({
            "name": script["name"],
            "file": script["file"],
            "status": "completed" if script_status else "pending"
        })

    # 计算总体进度
    report["overall_progress"] = total_completed_tasks / total_tasks if total_tasks > 0 else 0.0

    return report


def print_progress_report(report: Dict) -> None:
    """
    打印进度报告

    参数:
        report: 进度报告字典
    """
    logger.info(f"=== 指标系统重构进度报告 ({report['timestamp']}) ===\n")

    logger.info(f"总体进度: {report['overall_progress']:.1%}\n")

    logger.info("阶段进度:")
    for phase_id, phase in report["phases"].items():
        logger.info(f"  {phase['name']}: {phase['progress']:.1%} ({phase['completed_tasks']}/{phase['total_tasks']})")

    logger.info("\n任务详情:")
    for phase_id, phase in report["phases"].items():
        logger.info(f"  {phase['name']}:")
        for task in phase["tasks"]:
            status_symbol = "✅" if task["status"] == "completed" else "❌"
            logger.info(f"    {status_symbol} {task['name']}")

    logger.info("\n自动化脚本:")
    for script in report["automation_scripts"]["scripts"]:
        status_symbol = "✅" if script["status"] == "completed" else "❌"
        logger.info(f"  {status_symbol} {script['name']} ({script['file']})")

    logger.info("\n=== 报告结束 ===")


def save_report_to_file(report: Dict, output_file: str) -> None:
    """
    将报告保存到文件

    参数:
        report: 进度报告字典
        output_file: 输出文件路径
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        logger.info(f"报告已保存到 {output_file}")
    except Exception as e:
        logger.error(f"保存报告时发生错误: {str(e)}")


def generate_next_steps(report: Dict) -> List[str]:
    """
    生成下一步建议

    参数:
        report: 进度报告字典

    返回:
        List[str]: 下一步建议列表
    """
    next_steps = []

    # 检查每个阶段
    for phase_id, phase in report["phases"].items():
        if phase["progress"] < 1.0:
            # 找出该阶段中未完成的任务
            pending_tasks = [task for task in phase["tasks"] if task["status"] == "pending"]

            if pending_tasks:
                next_steps.append(f"完成{phase['name']}阶段的以下任务:")
                for task in pending_tasks:
                    next_steps.append(f"  - {task['name']}")

                # 只关注第一个未完成的阶段
                break

    # 检查自动化脚本
    pending_scripts = [script for script in report["automation_scripts"]["scripts"] if script["status"] == "pending"]
    if pending_scripts:
        next_steps.append("创建以下自动化脚本:")
        for script in pending_scripts:
            next_steps.append(f"  - {script['name']} ({script['file']})")

    # 如果所有任务都已完成
    if not next_steps:
        next_steps.append("恭喜！所有指标系统重构任务已完成。")
        next_steps.append("建议进行以下工作:")
        next_steps.append("  - 运行全面测试，确保所有功能正常")
        next_steps.append("  - 更新用户文档，反映新的指标系统")
        next_steps.append("  - 考虑添加更多自定义指标")

    return next_steps


def print_next_steps(next_steps: List[str]) -> None:
    """
    打印下一步建议

    参数:
        next_steps: 下一步建议列表
    """
    logger.info("\n=== 下一步建议 ===\n")

    for step in next_steps:
        logger.info(step)

    logger.info("\n=== 建议结束 ===")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='检查指标系统重构的进度，并生成详细的报告')
    parser.add_argument('--output', default='refactor_progress.json', help='输出文件路径，默认为refactor_progress.json')
    parser.add_argument('--no-save', action='store_true', help='不保存报告到文件')
    args = parser.parse_args()

    # 生成进度报告
    report = generate_progress_report()

    # 打印进度报告
    print_progress_report(report)

    # 生成下一步建议
    next_steps = generate_next_steps(report)

    # 打印下一步建议
    print_next_steps(next_steps)

    # 保存报告到文件
    if not args.no_save:
        save_report_to_file(report, args.output)


if __name__ == '__main__':
    main()
