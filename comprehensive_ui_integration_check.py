#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面UI组件集成检查

检查所有UI组件是否都正确集成到新的K线数据导入UI中
"""

from typing import Dict, List, Set, Any
import re
from loguru import logger
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class UIIntegrationChecker:
    """UI组件集成检查器"""

    def __init__(self):
        self.main_dialog = Path("gui/dialogs/unified_duckdb_import_dialog.py")
        self.dashboard = Path("gui/widgets/data_import_dashboard.py")
        self.backup_suffix = ".backup"

    def check_ui_integration(self):
        """检查UI组件集成情况"""
        logger.info("=== K线数据导入UI组件集成全面检查 ===")

        # 检查主导入对话框
        dialog_analysis = self._analyze_dialog_integration()

        # 检查数据导入仪表板
        dashboard_analysis = self._analyze_dashboard_integration()

        # 检查组件间关系
        integration_analysis = self._analyze_component_relationships()

        # 生成综合报告
        self._generate_integration_report(dialog_analysis, dashboard_analysis, integration_analysis)

    def _analyze_dialog_integration(self):
        """分析主导入对话框的UI组件集成"""
        logger.info("\n🔍 分析主导入对话框 (UnifiedDuckDBImportDialog)")

        if not self.main_dialog.exists():
            logger.error(f"主对话框文件不存在: {self.main_dialog}")
            return {}

        with open(self.main_dialog, 'r', encoding='utf-8') as f:
            content = f.read()

        analysis = {
            'imports': self._extract_imports(content),
            'qt_widgets': self._extract_qt_widgets(content),
            'custom_widgets': self._extract_custom_widgets(content),
            'layout_components': self._extract_layout_components(content),
            'tabs': self._extract_tabs(content),
            'buttons': self._extract_buttons(content),
            'input_components': self._extract_input_components(content),
            'display_components': self._extract_display_components(content),
            'event_handlers': self._extract_event_handlers(content)
        }

        self._print_dialog_analysis(analysis)
        return analysis

    def _analyze_dashboard_integration(self):
        """分析数据导入仪表板的UI组件集成"""
        logger.info("\n🔍 分析数据导入仪表板 (DataImportDashboard)")

        if not self.dashboard.exists():
            logger.error(f"仪表板文件不存在: {self.dashboard}")
            return {}

        with open(self.dashboard, 'r', encoding='utf-8') as f:
            content = f.read()

        analysis = {
            'imports': self._extract_imports(content),
            'qt_widgets': self._extract_qt_widgets(content),
            'custom_widgets': self._extract_custom_widgets(content),
            'chart_components': self._extract_chart_components(content),
            'metric_cards': self._extract_metric_cards(content),
            'progress_bars': self._extract_progress_bars(content),
            'timers': self._extract_timers(content),
            'performance_components': self._extract_performance_components(content)
        }

        self._print_dashboard_analysis(analysis)
        return analysis

    def _analyze_component_relationships(self):
        """分析组件间关系"""
        logger.info("\n🔍 分析组件间集成关系")

        # 检查主对话框中是否正确引用了仪表板
        dialog_content = ""
        dashboard_content = ""

        if self.main_dialog.exists():
            with open(self.main_dialog, 'r', encoding='utf-8') as f:
                dialog_content = f.read()

        if self.dashboard.exists():
            with open(self.dashboard, 'r', encoding='utf-8') as f:
                dashboard_content = f.read()

        relationships = {
            'dashboard_imports_in_dialog': 'DataImportDashboard' in dialog_content,
            'metric_card_usage': 'MetricCard' in dialog_content,
            'performance_chart_usage': 'PerformanceChart' in dialog_content,
            'log_viewer_usage': 'LogViewer' in dialog_content,
            'shared_components': self._find_shared_components(dialog_content, dashboard_content),
            'integration_points': self._find_integration_points(dialog_content)
        }

        self._print_relationship_analysis(relationships)
        return relationships

    def _extract_imports(self, content: str) -> List[str]:
        """提取导入语句"""
        pattern = r'from\s+[\w.]+\s+import\s+([^#\n]+)'
        imports = []
        for match in re.findall(pattern, content):
            imports.extend([item.strip() for item in match.split(',')])
        return imports

    def _extract_qt_widgets(self, content: str) -> Set[str]:
        """提取Qt组件"""
        qt_pattern = r'Q([A-Z][a-zA-Z]*)'
        return set(re.findall(qt_pattern, content))

    def _extract_custom_widgets(self, content: str) -> Set[str]:
        """提取自定义组件"""
        custom_patterns = [
            r'(MetricCard)',
            r'(PerformanceChart)',
            r'(LogViewer)',
            r'(DataImportDashboard)',
            r'(ImportTaskConfigWidget)',
            r'(DataSourceConfigWidget)'
        ]

        custom_widgets = set()
        for pattern in custom_patterns:
            custom_widgets.update(re.findall(pattern, content))

        return custom_widgets

    def _extract_layout_components(self, content: str) -> List[str]:
        """提取布局组件"""
        layout_pattern = r'(\w*Layout)\s*\('
        return list(set(re.findall(layout_pattern, content)))

    def _extract_tabs(self, content: str) -> List[str]:
        """提取标签页"""
        tab_pattern = r'addTab\([^,]+,\s*["\']([^"\']+)["\']'
        return re.findall(tab_pattern, content)

    def _extract_buttons(self, content: str) -> List[str]:
        """提取按钮"""
        button_pattern = r'QPushButton\s*\(\s*["\']([^"\']*)["\']'
        return re.findall(button_pattern, content)

    def _extract_input_components(self, content: str) -> List[str]:
        """提取输入组件"""
        input_patterns = [
            r'QLineEdit',
            r'QSpinBox',
            r'QDoubleSpinBox',
            r'QComboBox',
            r'QCheckBox',
            r'QTextEdit'
        ]

        inputs = []
        for pattern in input_patterns:
            count = len(re.findall(pattern, content))
            if count > 0:
                inputs.append(f"{pattern}: {count}")

        return inputs

    def _extract_display_components(self, content: str) -> List[str]:
        """提取显示组件"""
        display_patterns = [
            r'QLabel',
            r'QProgressBar',
            r'QTableWidget',
            r'QTreeWidget',
            r'QTextEdit'
        ]

        displays = []
        for pattern in display_patterns:
            count = len(re.findall(pattern, content))
            if count > 0:
                displays.append(f"{pattern}: {count}")

        return displays

    def _extract_event_handlers(self, content: str) -> List[str]:
        """提取事件处理器"""
        event_pattern = r'def\s+(on_\w+|_\w+_clicked|_\w+_changed)\s*\('
        return re.findall(event_pattern, content)

    def _extract_chart_components(self, content: str) -> List[str]:
        """提取图表组件"""
        chart_patterns = [
            r'PerformanceChart',
            r'Chart',
            r'Plot',
            r'Graph'
        ]

        charts = []
        for pattern in chart_patterns:
            count = len(re.findall(pattern, content))
            if count > 0:
                charts.append(f"{pattern}: {count}")

        return charts

    def _extract_metric_cards(self, content: str) -> List[str]:
        """提取指标卡片"""
        metric_pattern = r'MetricCard\s*\(\s*["\']([^"\']+)["\']'
        return re.findall(metric_pattern, content)

    def _extract_progress_bars(self, content: str) -> List[str]:
        """提取进度条"""
        progress_pattern = r'QProgressBar'
        count = len(re.findall(progress_pattern, content))
        return [f"QProgressBar: {count}"] if count > 0 else []

    def _extract_timers(self, content: str) -> Dict[str, str]:
        """提取定时器"""
        timer_pattern = r'(\w*[Tt]imer\w*).*?\.start\s*\(\s*(\d+)\s*\)'
        timers = {}
        for timer_name, interval in re.findall(timer_pattern, content):
            timers[timer_name] = f"{interval}ms"
        return timers

    def _extract_performance_components(self, content: str) -> List[str]:
        """提取性能组件"""
        perf_patterns = [
            r'performance',
            r'metrics',
            r'monitoring',
            r'cpu_progress',
            r'memory_progress'
        ]

        components = []
        for pattern in perf_patterns:
            count = len(re.findall(pattern, content, re.IGNORECASE))
            if count > 0:
                components.append(f"{pattern}: {count}")

        return components

    def _find_shared_components(self, dialog_content: str, dashboard_content: str) -> List[str]:
        """查找共享组件"""
        dialog_components = set(re.findall(r'Q[A-Z][a-zA-Z]*', dialog_content))
        dashboard_components = set(re.findall(r'Q[A-Z][a-zA-Z]*', dashboard_content))

        shared = dialog_components.intersection(dashboard_components)
        return list(shared)

    def _find_integration_points(self, content: str) -> List[str]:
        """查找集成点"""
        integration_patterns = [
            r'DataImportDashboard',
            r'self\.dashboard',
            r'dashboard\.',
            r'performance_dashboard',
            r'MetricCard',
            r'PerformanceChart'
        ]

        points = []
        for pattern in integration_patterns:
            matches = re.findall(pattern, content)
            if matches:
                points.append(f"{pattern}: {len(matches)}")

        return points

    def _print_dialog_analysis(self, analysis: Dict[str, Any]):
        """打印对话框分析结果"""
        logger.info("\n📊 主导入对话框组件分析:")

        logger.info(f"  📦 导入组件: {len(analysis['imports'])} 个")
        logger.info(f"  🖼️ Qt组件: {len(analysis['qt_widgets'])} 种类型")
        logger.info(f"  🔧 自定义组件: {len(analysis['custom_widgets'])} 个")
        logger.info(f"  📐 布局组件: {analysis['layout_components']}")

        if analysis['tabs']:
            logger.info(f"  📋 标签页: {analysis['tabs']}")

        if analysis['buttons']:
            logger.info(f"  🔘 按钮: {len(analysis['buttons'])} 个")
            for i, button in enumerate(analysis['buttons'][:5]):  # 显示前5个
                logger.info(f"    • {button}")
            if len(analysis['buttons']) > 5:
                logger.info(f"    ... 还有 {len(analysis['buttons']) - 5} 个按钮")

        if analysis['input_components']:
            logger.info(f"  ⌨️ 输入组件: {analysis['input_components']}")

        if analysis['display_components']:
            logger.info(f"  📺 显示组件: {analysis['display_components']}")

    def _print_dashboard_analysis(self, analysis: Dict[str, Any]):
        """打印仪表板分析结果"""
        logger.info("\n📊 数据导入仪表板组件分析:")

        logger.info(f"  📦 导入组件: {len(analysis['imports'])} 个")
        logger.info(f"  🖼️ Qt组件: {len(analysis['qt_widgets'])} 种类型")
        logger.info(f"  🔧 自定义组件: {len(analysis['custom_widgets'])} 个")

        if analysis['chart_components']:
            logger.info(f"  📈 图表组件: {analysis['chart_components']}")

        if analysis['metric_cards']:
            logger.info(f"  📊 指标卡片: {analysis['metric_cards']}")

        if analysis['progress_bars']:
            logger.info(f"  📊 进度条: {analysis['progress_bars']}")

        if analysis['timers']:
            logger.info(f"  ⏰ 定时器: {analysis['timers']}")

        if analysis['performance_components']:
            logger.info(f"  🚀 性能组件: {analysis['performance_components']}")

    def _print_relationship_analysis(self, relationships: Dict[str, Any]):
        """打印关系分析结果"""
        logger.info("\n🔗 组件集成关系分析:")

        if relationships['dashboard_imports_in_dialog']:
            logger.info("✅ 主对话框正确导入了DataImportDashboard")
        else:
            logger.warning("❌ 主对话框未导入DataImportDashboard")

        if relationships['metric_card_usage']:
            logger.info("✅ 主对话框集成了MetricCard组件")
        else:
            logger.warning("❌ 主对话框未集成MetricCard组件")

        if relationships['performance_chart_usage']:
            logger.info("✅ 主对话框集成了PerformanceChart组件")
        else:
            logger.warning("❌ 主对话框未集成PerformanceChart组件")

        if relationships['log_viewer_usage']:
            logger.info("✅ 主对话框集成了LogViewer组件")
        else:
            logger.warning("❌ 主对话框未集成LogViewer组件")

        if relationships['shared_components']:
            logger.info(f"  🔄 共享Qt组件: {len(relationships['shared_components'])} 个")
            for comp in relationships['shared_components'][:10]:  # 显示前10个
                logger.info(f"    • Q{comp}")

        if relationships['integration_points']:
            logger.info(f"  🔗 集成点: {relationships['integration_points']}")

    def _generate_integration_report(self, dialog_analysis, dashboard_analysis, integration_analysis):
        """生成集成报告"""
        logger.info("\n" + "=" * 80)
        logger.info("📋 K线数据导入UI组件集成综合报告")
        logger.info("=" * 80)

        # 统计总体情况
        total_dialog_components = (
            len(dialog_analysis.get('qt_widgets', [])) +
            len(dialog_analysis.get('custom_widgets', [])) +
            len(dialog_analysis.get('buttons', [])) +
            len(dialog_analysis.get('input_components', [])) +
            len(dialog_analysis.get('display_components', []))
        )

        total_dashboard_components = (
            len(dashboard_analysis.get('qt_widgets', [])) +
            len(dashboard_analysis.get('custom_widgets', [])) +
            len(dashboard_analysis.get('chart_components', [])) +
            len(dashboard_analysis.get('metric_cards', [])) +
            len(dashboard_analysis.get('performance_components', []))
        )

        logger.info(f"\n📊 组件统计:")
        logger.info(f"  🏠 主对话框组件: {total_dialog_components} 个")
        logger.info(f"  📈 仪表板组件: {total_dashboard_components} 个")
        logger.info(f"  🔗 共享组件: {len(integration_analysis.get('shared_components', []))} 个")

        # 集成状态评估
        integration_score = 0
        max_score = 4

        if integration_analysis.get('dashboard_imports_in_dialog'):
            integration_score += 1
        if integration_analysis.get('metric_card_usage'):
            integration_score += 1
        if integration_analysis.get('performance_chart_usage'):
            integration_score += 1
        if integration_analysis.get('log_viewer_usage'):
            integration_score += 1

        integration_percentage = (integration_score / max_score) * 100

        logger.info(f"\n🎯 集成完整性评估:")
        logger.info(f"  📈 集成评分: {integration_score}/{max_score} ({integration_percentage:.1f}%)")

        if integration_percentage >= 100:
            logger.info("✅ 集成状态: 完美 - 所有组件都正确集成")
        elif integration_percentage >= 75:
            logger.info("✅ 集成状态: 良好 - 大部分组件已集成")
        elif integration_percentage >= 50:
            logger.info("⚠️ 集成状态: 一般 - 部分组件需要检查")
        else:
            logger.info("❌ 集成状态: 需要改进 - 多个组件未正确集成")

        # 生成建议
        self._generate_recommendations(dialog_analysis, dashboard_analysis, integration_analysis)

    def _generate_recommendations(self, dialog_analysis, dashboard_analysis, integration_analysis):
        """生成建议"""
        logger.info(f"\n💡 集成建议:")

        if not integration_analysis.get('dashboard_imports_in_dialog'):
            logger.warning("🔧 建议: 在主对话框中导入DataImportDashboard")

        if not integration_analysis.get('metric_card_usage'):
            logger.warning("🔧 建议: 在主对话框中使用MetricCard组件")

        if not integration_analysis.get('performance_chart_usage'):
            logger.warning("🔧 建议: 在主对话框中集成PerformanceChart")

        if not integration_analysis.get('log_viewer_usage'):
            logger.warning("🔧 建议: 在主对话框中集成LogViewer")

        if integration_analysis.get('dashboard_imports_in_dialog') and \
           integration_analysis.get('metric_card_usage') and \
           integration_analysis.get('performance_chart_usage'):
            logger.info("🎉 优秀! 所有主要组件都已正确集成到K线数据导入UI中")
            logger.info("✅ 建议: 当前集成状态完美，可以正常使用")


def main():
    """主函数"""
    logger.info("K线数据导入UI组件集成全面检查工具")
    logger.info("检查所有UI组件是否正确集成到新的K线数据导入UI中")

    checker = UIIntegrationChecker()
    checker.check_ui_integration()

    logger.info("\n📁 检查完成！请查看上述报告了解集成状态。")


if __name__ == "__main__":
    main()
