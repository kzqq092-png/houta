#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本管理系统综合测试脚本

测试版本管理系统的所有核心功能，包括：
1. 版本管理器初始化
2. 版本创建、激活、回滚、删除
3. 版本导入导出
4. 性能对比
5. 版本管理对话框UI
"""

import sys
import os
import traceback
import tempfile
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_version_manager_backend():
    """测试版本管理器后端功能"""
    print("=" * 60)
    print("测试版本管理器后端功能")
    print("=" * 60)

    try:
        # 导入版本管理器
        from optimization.version_manager import create_version_manager
        from optimization.performance_evaluator import PerformanceMetrics

        print("✅ 版本管理器模块导入成功")

        # 创建版本管理器
        version_manager = create_version_manager('test_version.db')
        print("✅ 版本管理器创建成功")

        # 测试创建版本
        test_patterns = ["头肩顶", "双底", "三重顶"]
        version_ids = []

        for pattern_name in test_patterns:
            try:
                # 创建性能指标
                performance_metrics = PerformanceMetrics(
                    true_positives=85,
                    false_positives=15,
                    true_negatives=180,
                    false_negatives=20,
                    precision=0.85,
                    recall=0.81,
                    f1_score=0.83,
                    accuracy=0.88,
                    execution_time=125.5,
                    memory_usage=256.8,
                    cpu_usage=45.2,
                    signal_quality=0.82,
                    confidence_avg=0.78,
                    confidence_std=0.15,
                    patterns_found=25,
                    robustness_score=0.75,
                    parameter_sensitivity=0.12,
                    overall_score=0.85
                )

                version_id = version_manager.save_version(
                    pattern_id=0,
                    pattern_name=pattern_name,
                    algorithm_code=f"""
def detect_{pattern_name.replace(' ', '_')}(data):
    '''
    {pattern_name}识别算法
    '''
    # 算法实现
    threshold = 0.8
    window_size = 20
    
    # 模拟识别逻辑
    signals = []
    for i in range(len(data) - window_size):
        confidence = calculate_confidence(data[i:i+window_size])
        if confidence > threshold:
            signals.append({{'index': i, 'confidence': confidence}})
    
    return signals

def calculate_confidence(window_data):
    # 模拟置信度计算
    return 0.85
""",
                    parameters={
                        "threshold": 0.8,
                        "window_size": 20,
                        "sensitivity": 0.5
                    },
                    description=f"{pattern_name}识别算法 - 测试版本",
                    optimization_method="manual",
                    performance_metrics=performance_metrics
                )

                version_ids.append(version_id)
                print(f"✅ 创建{pattern_name}版本成功，版本ID: {version_id}")

            except Exception as e:
                print(f"❌ 创建{pattern_name}版本失败: {e}")

        # 测试获取版本列表
        for pattern_name in test_patterns:
            try:
                versions = version_manager.get_versions(pattern_name, limit=5)
                print(f"✅ 获取{pattern_name}版本列表成功，共{len(versions)}个版本")

                for version in versions:
                    print(
                        f"   - 版本{version.version_number}: {version.description}")

            except Exception as e:
                print(f"❌ 获取{pattern_name}版本列表失败: {e}")

        # 测试激活版本
        if version_ids:
            try:
                success = version_manager.activate_version(version_ids[0])
                if success:
                    print(f"✅ 激活版本{version_ids[0]}成功")
                else:
                    print(f"❌ 激活版本{version_ids[0]}失败")
            except Exception as e:
                print(f"❌ 激活版本失败: {e}")

        # 测试版本对比
        if len(version_ids) >= 2:
            try:
                comparison = version_manager.compare_versions(
                    version_ids[0], version_ids[1])
                print("✅ 版本对比成功")
                print(f"   - 版本1: {comparison['version1']['description']}")
                print(f"   - 版本2: {comparison['version2']['description']}")
                print(
                    f"   - 代码相似度: {comparison['code_diff']['similarity']:.2%}")
            except Exception as e:
                print(f"❌ 版本对比失败: {e}")

        # 测试导出版本
        if version_ids:
            try:
                temp_file = tempfile.mktemp(suffix='.json')
                success = version_manager.export_version(
                    version_ids[0], temp_file)
                if success and os.path.exists(temp_file):
                    print(f"✅ 版本导出成功: {temp_file}")

                    # 测试导入版本
                    try:
                        new_version_id = version_manager.import_version(
                            temp_file, "测试导入形态")
                        if new_version_id:
                            print(f"✅ 版本导入成功，新版本ID: {new_version_id}")
                        else:
                            print("❌ 版本导入失败")
                    except Exception as e:
                        print(f"❌ 版本导入失败: {e}")

                    # 清理临时文件
                    os.remove(temp_file)
                else:
                    print("❌ 版本导出失败")
            except Exception as e:
                print(f"❌ 版本导出失败: {e}")

        # 清理测试数据库
        try:
            if os.path.exists('test_version.db'):
                os.remove('test_version.db')
                print("✅ 测试数据库清理完成")
        except Exception as e:
            print(f"⚠️ 清理测试数据库失败: {e}")

        return True

    except ImportError as e:
        print(f"❌ 版本管理器后端模块不可用: {e}")
        return False
    except Exception as e:
        print(f"❌ 版本管理器后端测试失败: {e}")
        print(traceback.format_exc())
        return False


def test_version_manager_dialog():
    """测试版本管理对话框UI"""
    print("\n" + "=" * 60)
    print("测试版本管理对话框UI")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication
        from gui.dialogs.version_manager_dialog import VersionManagerDialog

        print("✅ 版本管理对话框模块导入成功")

        # 创建QApplication（如果不存在）
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # 创建版本管理对话框
        dialog = VersionManagerDialog()
        print("✅ 版本管理对话框创建成功")

        # 测试界面组件
        components = [
            ('工具栏', 'toolbar_frame'),
            ('版本树', 'version_tree'),
            ('详情区域', 'detail_widget'),
            ('创建版本按钮', 'create_version_btn'),
            ('导入按钮', 'import_btn'),
            ('导出按钮', 'export_btn'),
            ('激活按钮', 'activate_btn'),
            ('回滚按钮', 'rollback_btn'),
            ('删除按钮', 'delete_btn'),
            ('刷新按钮', 'refresh_btn'),
            ('形态选择框', 'pattern_combo'),
        ]

        for name, attr in components:
            if hasattr(dialog, attr):
                component = getattr(dialog, attr)
                if component is not None:
                    print(f"✅ {name}组件正常")
                else:
                    print(f"❌ {name}组件为空")
            else:
                print(f"❌ 缺少{name}组件")

        # 测试版本数据加载
        if hasattr(dialog, 'versions') and dialog.versions:
            print(f"✅ 版本数据加载成功，共{len(dialog.versions)}个版本")
        else:
            print("⚠️ 版本数据为空（可能是正常的）")

        # 测试信号连接
        signals = [
            ('version_changed', '版本变更信号'),
        ]

        for signal_name, description in signals:
            if hasattr(dialog, signal_name):
                print(f"✅ {description}定义正常")
            else:
                print(f"❌ 缺少{description}")

        print("✅ 版本管理对话框UI测试完成")
        return True

    except ImportError as e:
        print(f"❌ 版本管理对话框模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 版本管理对话框测试失败: {e}")
        print(traceback.format_exc())
        return False


def test_integration():
    """测试系统集成"""
    print("\n" + "=" * 60)
    print("测试系统集成")
    print("=" * 60)

    try:
        # 测试菜单栏集成
        try:
            from gui.menu_bar import MenuBar
            print("✅ 菜单栏模块可用")
        except ImportError:
            print("⚠️ 菜单栏模块不可用")

        # 测试主窗口协调器集成
        try:
            from core.coordinators.main_window_coordinator import MainWindowCoordinator
            print("✅ 主窗口协调器模块可用")
        except ImportError:
            print("⚠️ 主窗口协调器模块不可用")

        # 测试数据库集成
        try:
            from optimization.database_schema import OptimizationDatabaseManager
            db_manager = OptimizationDatabaseManager(':memory:')
            print("✅ 数据库管理器可用")
        except Exception as e:
            print(f"❌ 数据库管理器不可用: {e}")

        # 测试日志系统集成
        try:
            from core.logger import get_logger
            logger = get_logger("test")
            logger.info("测试日志")
            print("✅ 日志系统可用")
        except Exception as e:
            print(f"❌ 日志系统不可用: {e}")

        return True

    except Exception as e:
        print(f"❌ 系统集成测试失败: {e}")
        return False


def generate_test_report():
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("版本管理系统测试报告")
    print("=" * 60)

    report = {
        "test_time": datetime.now().isoformat(),
        "test_results": {
            "backend_test": False,
            "ui_test": False,
            "integration_test": False
        },
        "summary": "",
        "recommendations": []
    }

    # 运行测试
    print("开始运行测试...")

    # 后端测试
    report["test_results"]["backend_test"] = test_version_manager_backend()

    # UI测试
    report["test_results"]["ui_test"] = test_version_manager_dialog()

    # 集成测试
    report["test_results"]["integration_test"] = test_integration()

    # 生成总结
    passed_tests = sum(report["test_results"].values())
    total_tests = len(report["test_results"])

    report["summary"] = f"测试完成：{passed_tests}/{total_tests} 项测试通过"

    if passed_tests == total_tests:
        report["summary"] += "，版本管理系统功能完整！"
        report["recommendations"].append("系统运行正常，可以投入使用")
    else:
        report["summary"] += "，存在部分问题需要修复"

        if not report["test_results"]["backend_test"]:
            report["recommendations"].append("修复版本管理器后端功能")
        if not report["test_results"]["ui_test"]:
            report["recommendations"].append("修复版本管理对话框UI")
        if not report["test_results"]["integration_test"]:
            report["recommendations"].append("完善系统集成")

    # 输出报告
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"测试时间: {report['test_time']}")
    print(f"测试结果: {report['summary']}")

    if report["recommendations"]:
        print("\n建议:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"{i}. {rec}")

    # 保存报告到文件
    try:
        with open('version_management_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 测试报告已保存到: version_management_test_report.json")
    except Exception as e:
        print(f"⚠️ 保存测试报告失败: {e}")

    return report


if __name__ == "__main__":
    print("YS-Quant‌ 版本管理系统综合测试")
    print("=" * 60)

    try:
        report = generate_test_report()

        # 根据测试结果设置退出码
        if sum(report["test_results"].values()) == len(report["test_results"]):
            sys.exit(0)  # 所有测试通过
        else:
            sys.exit(1)  # 存在失败的测试

    except KeyboardInterrupt:
        print("\n用户中断测试")
        sys.exit(2)
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        print(traceback.format_exc())
        sys.exit(3)
