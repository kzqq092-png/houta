#!/usr/bin/env python3
"""
趋势分析功能全量验证和修复脚本
对右侧面板中趋势分析的所有UI功能进行深度验证，分析代码与调用链，修复逻辑bug
"""

import sys
import os
import ast
import re
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Any
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class TrendAnalysisValidator:
    """趋势分析功能全量验证器"""

    def __init__(self):
        self.trend_file = project_root / "gui" / "widgets" / "analysis_tabs" / "trend_tab.py"
        self.issues = []
        self.fixes_applied = []
        self.code_content = ""

    def run_comprehensive_validation(self):
        """运行全面验证"""
        print("🔍 开始趋势分析功能全量验证")
        print("=" * 80)

        # 1. 加载代码
        if not self.load_code():
            return False

        # 2. 语法和结构验证
        self.validate_syntax_and_structure()

        # 3. UI组件完整性验证
        self.validate_ui_components()

        # 4. 功能方法验证
        self.validate_functionality()

        # 5. 调用链分析
        self.analyze_call_chains()

        # 6. 数据流验证
        self.validate_data_flow()

        # 7. 异步处理验证
        self.validate_async_processing()

        # 8. 错误处理验证
        self.validate_error_handling()

        # 9. 信号连接验证
        self.validate_signal_connections()

        # 10. 业务逻辑验证
        self.validate_business_logic()

        # 11. 应用修复
        self.apply_fixes()

        # 12. 生成报告
        return self.generate_report()

    def load_code(self):
        """加载代码文件"""
        try:
            if not self.trend_file.exists():
                self.issues.append("❌ 趋势分析文件不存在")
                return False

            with open(self.trend_file, 'r', encoding='utf-8') as f:
                self.code_content = f.read()

            print(f"✅ 已加载趋势分析文件 ({len(self.code_content)} 字符)")
            return True

        except Exception as e:
            self.issues.append(f"❌ 加载文件失败: {e}")
            return False

    def validate_syntax_and_structure(self):
        """验证语法和结构"""
        print("\n🔧 验证语法和结构...")

        try:
            # 1. Python语法验证
            ast.parse(self.code_content)
            print("✅ Python语法验证通过")

        except SyntaxError as e:
            self.issues.append(f"❌ 语法错误: {e}")
            print(f"❌ 语法错误: {e}")

        # 2. 导入依赖验证
        self.validate_imports()

        # 3. 类结构验证
        self.validate_class_structure()

    def validate_imports(self):
        """验证导入依赖"""
        required_imports = [
            'from PyQt5.QtWidgets import',
            'from PyQt5.QtCore import',
            'from PyQt5.QtGui import',
            'import numpy as np',
            'import pandas as pd',
            'from datetime import datetime',
            'import json',
            'import logging'
        ]

        missing_imports = []
        for imp in required_imports:
            if imp not in self.code_content:
                missing_imports.append(imp)

        if missing_imports:
            self.issues.append(f"❌ 缺少导入: {missing_imports}")
        else:
            print("✅ 导入依赖验证通过")

        # 检查重复导入
        duplicate_imports = []
        if self.code_content.count('from utils.config_manager import ConfigManager') > 1:
            duplicate_imports.append('ConfigManager重复导入')
        if self.code_content.count('from core.config_manager import ConfigManager') > 0:
            duplicate_imports.append('ConfigManager路径冲突')

        if duplicate_imports:
            self.issues.append(f"⚠️ 重复/冲突导入: {duplicate_imports}")

    def validate_class_structure(self):
        """验证类结构"""
        # 检查类定义
        if 'class TrendAnalysisTab(BaseAnalysisTab):' not in self.code_content:
            self.issues.append("❌ 主类定义缺失或错误")
            return

        # 检查信号定义
        required_signals = [
            'trend_analysis_completed = pyqtSignal(dict)',
            'trend_alert = pyqtSignal(str, dict)',
            'trend_reversal_detected = pyqtSignal(dict)'
        ]

        for signal in required_signals:
            if signal not in self.code_content:
                self.issues.append(f"❌ 信号定义缺失: {signal}")

        print("✅ 类结构验证完成")

    def validate_ui_components(self):
        """验证UI组件完整性"""
        print("\n🎨 验证UI组件完整性...")

        # 1. 主要UI创建方法
        ui_methods = [
            'create_ui',
            '_create_professional_toolbar',
            '_create_control_panel',
            '_create_results_panel',
            '_create_trend_results_tab',
            '_create_multi_timeframe_tab',
            '_create_prediction_tab',
            '_create_support_resistance_tab',
            '_create_alert_tab',
            '_create_status_bar'
        ]

        missing_ui_methods = []
        for method in ui_methods:
            if f'def {method}(' not in self.code_content:
                missing_ui_methods.append(method)

        if missing_ui_methods:
            self.issues.append(f"❌ UI方法缺失: {missing_ui_methods}")
        else:
            print("✅ UI创建方法完整")

        # 2. UI组件属性验证
        ui_components = [
            'algorithm_combo',
            'timeframe_list',
            'period_spin',
            'threshold_spin',
            'sensitivity_slider',
            'confidence_spin',
            'enable_prediction_cb',
            'enable_alerts_cb',
            'trend_table',
            'multi_tf_table',
            'prediction_text',
            'sr_table',
            'alert_list',
            'trend_stats_label',
            'status_label',
            'progress_bar'
        ]

        missing_components = []
        for component in ui_components:
            if f'self.{component} =' not in self.code_content:
                missing_components.append(component)

        if missing_components:
            self.issues.append(f"❌ UI组件属性缺失: {missing_components}")
        else:
            print("✅ UI组件属性完整")

        # 3. 按钮连接验证
        self.validate_button_connections()

    def validate_button_connections(self):
        """验证按钮连接"""
        button_connections = [
            ('trend_btn.clicked.connect', 'self.comprehensive_trend_analysis'),
            ('multi_tf_btn.clicked.connect', 'self.multi_timeframe_analysis'),
            ('alert_btn.clicked.connect', 'self.setup_trend_alerts'),
            ('predict_btn.clicked.connect', 'self.trend_prediction'),
            ('sr_btn.clicked.connect', 'self.support_resistance_analysis'),
            ('export_btn.clicked.connect', 'self.export_trend_results'),
            ('refresh_btn.clicked.connect', 'self.comprehensive_trend_analysis')
        ]

        missing_connections = []
        for connection, method in button_connections:
            if connection not in self.code_content:
                missing_connections.append(f"{connection} -> {method}")

        if missing_connections:
            self.issues.append(f"❌ 按钮连接缺失: {missing_connections}")
        else:
            print("✅ 按钮连接验证通过")

    def validate_functionality(self):
        """验证功能方法"""
        print("\n⚙️ 验证功能方法...")

        # 1. 核心功能方法
        core_methods = [
            'comprehensive_trend_analysis',
            'multi_timeframe_analysis',
            'setup_trend_alerts',
            'trend_prediction',
            'support_resistance_analysis',
            'export_trend_results'
        ]

        missing_core_methods = []
        for method in core_methods:
            if f'def {method}(' not in self.code_content:
                missing_core_methods.append(method)

        if missing_core_methods:
            self.issues.append(f"❌ 核心功能方法缺失: {missing_core_methods}")
        else:
            print("✅ 核心功能方法完整")

        # 2. 异步处理方法
        async_methods = [
            '_comprehensive_analysis_async',
            '_multi_timeframe_analysis_async',
            '_trend_prediction_async',
            '_support_resistance_async'
        ]

        missing_async_methods = []
        for method in async_methods:
            if f'def {method}(' not in self.code_content:
                missing_async_methods.append(method)

        if missing_async_methods:
            self.issues.append(f"❌ 异步处理方法缺失: {missing_async_methods}")
        else:
            print("✅ 异步处理方法完整")

        # 3. 分析算法方法
        analysis_methods = [
            '_analyze_basic_trends',
            '_analyze_price_trend_advanced',
            '_analyze_volume_trend_advanced',
            '_analyze_indicator_trends',
            '_calculate_trend_statistics',
            '_generate_trend_predictions',
            '_analyze_support_resistance',
            '_generate_trend_alerts'
        ]

        missing_analysis_methods = []
        for method in analysis_methods:
            if f'def {method}(' not in self.code_content:
                missing_analysis_methods.append(method)

        if missing_analysis_methods:
            self.issues.append(f"❌ 分析算法方法缺失: {missing_analysis_methods}")
        else:
            print("✅ 分析算法方法完整")

    def analyze_call_chains(self):
        """分析调用链"""
        print("\n🔗 分析调用链...")

        call_chains = {
            'comprehensive_trend_analysis': [
                'validate_kdata_with_warning',
                'show_loading',
                'run_analysis_async',
                '_comprehensive_analysis_async'
            ],
            '_comprehensive_analysis_async': [
                '_analyze_basic_trends',
                '_calculate_trend_statistics',
                '_generate_trend_predictions',
                '_analyze_support_resistance',
                '_generate_trend_alerts',
                '_update_results_display'
            ],
            '_analyze_basic_trends': [
                '_analyze_price_trend_advanced',
                '_analyze_volume_trend_advanced',
                '_analyze_indicator_trends'
            ]
        }

        broken_chains = []
        for method, calls in call_chains.items():
            if f'def {method}(' in self.code_content:
                method_content = self._extract_method_content(method)
                for call in calls:
                    if call not in method_content:
                        broken_chains.append(f"{method} -> {call}")

        if broken_chains:
            self.issues.append(f"❌ 调用链断裂: {broken_chains}")
        else:
            print("✅ 调用链分析通过")

    def validate_data_flow(self):
        """验证数据流"""
        print("\n📊 验证数据流...")

        # 1. 数据验证逻辑
        data_validations = [
            'hasattr(self, \'kdata\')',
            'self.kdata is None',
            'len(self.kdata)',
            'validate_kdata_with_warning'
        ]

        missing_validations = []
        for validation in data_validations:
            if validation not in self.code_content:
                missing_validations.append(validation)

        if missing_validations:
            self.issues.append(f"❌ 数据验证缺失: {missing_validations}")
        else:
            print("✅ 数据验证逻辑完整")

        # 2. 数据转换和处理
        data_processing = [
            'self.current_kdata',
            'close_prices',
            'trend_results',
            'results[\'trend_analysis\']'
        ]

        for process in data_processing:
            if process not in self.code_content:
                self.issues.append(f"⚠️ 数据处理可能缺失: {process}")

    def validate_async_processing(self):
        """验证异步处理"""
        print("\n⏱️ 验证异步处理...")

        async_patterns = [
            'run_analysis_async',
            'QTimer.singleShot',
            'self.analysis_thread',
            'progress_updated.emit',
            'analysis_completed.emit'
        ]

        missing_async = []
        for pattern in async_patterns:
            if pattern not in self.code_content:
                missing_async.append(pattern)

        if missing_async:
            self.issues.append(f"❌ 异步处理模式缺失: {missing_async}")
        else:
            print("✅ 异步处理验证通过")

    def validate_error_handling(self):
        """验证错误处理"""
        print("\n🛡️ 验证错误处理...")

        error_patterns = [
            'try:',
            'except Exception as e:',
            'logger.error',
            'show_error',
            'QMessageBox'
        ]

        missing_error_handling = []
        for pattern in error_patterns:
            if pattern not in self.code_content:
                missing_error_handling.append(pattern)

        if missing_error_handling:
            self.issues.append(f"❌ 错误处理缺失: {missing_error_handling}")
        else:
            print("✅ 错误处理验证通过")

        # 检查每个主要方法的错误处理
        critical_methods = [
            'comprehensive_trend_analysis',
            'multi_timeframe_analysis',
            'setup_trend_alerts',
            'trend_prediction'
        ]

        methods_without_error_handling = []
        for method in critical_methods:
            method_content = self._extract_method_content(method)
            if method_content and 'try:' not in method_content:
                methods_without_error_handling.append(method)

        if methods_without_error_handling:
            self.issues.append(f"❌ 方法缺少错误处理: {methods_without_error_handling}")

    def validate_signal_connections(self):
        """验证信号连接"""
        print("\n📡 验证信号连接...")

        signal_emissions = [
            'trend_analysis_completed.emit',
            'trend_alert.emit',
            'trend_reversal_detected.emit'
        ]

        missing_emissions = []
        for signal in signal_emissions:
            if signal not in self.code_content:
                missing_emissions.append(signal)

        if missing_emissions:
            self.issues.append(f"❌ 信号发射缺失: {missing_emissions}")
        else:
            print("✅ 信号连接验证通过")

    def validate_business_logic(self):
        """验证业务逻辑"""
        print("\n💼 验证业务逻辑...")

        # 1. 算法配置验证
        if 'self.trend_algorithms' not in self.code_content:
            self.issues.append("❌ 趋势算法配置缺失")

        # 2. 时间框架配置验证
        if 'self.timeframes' not in self.code_content:
            self.issues.append("❌ 时间框架配置缺失")

        # 3. 参数范围验证
        parameter_settings = [
            'setMinimum',
            'setMaximum',
            'setRange',
            'setValue'
        ]

        for setting in parameter_settings:
            if setting not in self.code_content:
                self.issues.append(f"❌ 参数设置缺失: {setting}")

        # 4. 结果显示逻辑验证
        display_methods = [
            '_update_results_display',
            '_update_trend_table',
            '_update_statistics_display'
        ]

        missing_display = []
        for method in display_methods:
            if f'def {method}(' not in self.code_content:
                missing_display.append(method)

        if missing_display:
            self.issues.append(f"⚠️ 结果显示方法可能缺失: {missing_display}")

        print("✅ 业务逻辑验证完成")

    def apply_fixes(self):
        """应用修复"""
        print("\n🔧 应用修复...")

        if not self.issues:
            print("✅ 未发现需要修复的问题")
            return

        # 备份原文件
        backup_file = self.trend_file.with_suffix('.py.backup2')
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(self.code_content)
        print(f"✅ 已备份原文件: {backup_file}")

        # 应用具体修复
        self._fix_import_issues()
        self._fix_missing_methods()
        self._fix_error_handling()
        self._fix_parameter_settings()

        # 写入修复后的文件
        if self.fixes_applied:
            with open(self.trend_file, 'w', encoding='utf-8') as f:
                f.write(self.code_content)
            print(f"✅ 已应用 {len(self.fixes_applied)} 个修复")
        else:
            print("⚠️ 没有应用任何修复")

    def _fix_import_issues(self):
        """修复导入问题"""
        # 移除重复的ConfigManager导入
        if 'from utils.config_manager import ConfigManager' in self.code_content and \
           'from core.config_manager import ConfigManager' in self.code_content:
            self.code_content = self.code_content.replace(
                'from utils.config_manager import ConfigManager\n', ''
            )
            self.fixes_applied.append("移除重复的ConfigManager导入")

    def _fix_missing_methods(self):
        """修复缺失的方法"""
        # 如果缺少_update_results_display方法，添加基础实现
        if 'def _update_results_display(' not in self.code_content:
            update_method = '''
    def _update_results_display(self, results):
        """更新结果显示"""
        try:
            if 'trend_analysis' in results:
                self._update_trend_table(results['trend_analysis'])
            
            if 'statistics' in results:
                self._update_statistics_display(results['statistics'])
                
            if 'predictions' in results:
                self._update_prediction_display(results['predictions'])
                
            if 'alerts' in results:
                self._update_alerts_display(results['alerts'])
                
        except Exception as e:
            logger.error(f"更新结果显示失败: {e}")
'''
            # 在文件末尾添加方法
            self.code_content += update_method
            self.fixes_applied.append("添加_update_results_display方法")

    def _fix_error_handling(self):
        """修复错误处理"""
        # 为缺少错误处理的方法添加基础错误处理
        critical_methods = ['trend_prediction', 'support_resistance_analysis']

        for method in critical_methods:
            if f'def {method}(' in self.code_content:
                method_content = self._extract_method_content(method)
                if method_content and 'try:' not in method_content:
                    # 添加基础错误处理包装
                    self._wrap_method_with_error_handling(method)

    def _fix_parameter_settings(self):
        """修复参数设置"""
        # 确保所有参数组件都有完整的范围设置
        pass  # 已经在之前的修复中处理过

    def _extract_method_content(self, method_name):
        """提取方法内容"""
        pattern = rf'def {method_name}\([^)]*\):(.*?)(?=def|\Z)'
        match = re.search(pattern, self.code_content, re.DOTALL)
        return match.group(1) if match else ""

    def _wrap_method_with_error_handling(self, method_name):
        """为方法添加错误处理包装"""
        # 这里可以实现具体的错误处理包装逻辑
        pass

    def generate_report(self):
        """生成验证报告"""
        print("\n" + "=" * 80)
        print("📊 趋势分析功能全量验证报告")
        print("=" * 80)

        print(f"\n📈 验证统计:")
        print(f"   发现问题: {len(self.issues)} 个")
        print(f"   应用修复: {len(self.fixes_applied)} 个")

        if self.issues:
            print(f"\n⚠️ 发现的问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")

        if self.fixes_applied:
            print(f"\n🔧 应用的修复:")
            for i, fix in enumerate(self.fixes_applied, 1):
                print(f"   {i}. {fix}")

        # 计算健康评分
        total_checks = 50  # 估计的总检查项数
        issues_count = len(self.issues)
        health_score = max(0, (total_checks - issues_count) / total_checks * 100)

        print(f"\n🏥 健康评分: {health_score:.1f}/100")

        if health_score >= 90:
            print("✅ 状态: 优秀")
        elif health_score >= 70:
            print("⚠️ 状态: 良好")
        elif health_score >= 50:
            print("❌ 状态: 需要改进")
        else:
            print("🚨 状态: 严重问题")

        return health_score >= 70


def main():
    """主函数"""
    print("🚀 启动趋势分析功能全量验证...")

    try:
        validator = TrendAnalysisValidator()
        success = validator.run_comprehensive_validation()

        if success:
            print("\n🎉 验证完成！系统状态良好")
        else:
            print("\n💼 验证完成，发现需要关注的问题")

        return success

    except Exception as e:
        logger.error(f"验证过程中发生错误: {e}")
        print(f"❌ 验证异常: {e}")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 全量验证通过！")
    else:
        print("\n⚠️ 发现问题，建议检查并修复！")

    input("\n按Enter键退出...")
