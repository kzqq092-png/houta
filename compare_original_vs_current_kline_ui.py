#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比原始vs当前K线数据导入UI功能

详细对比原始版本和当前版本的K线数据导入UI，
识别缺失的功能和未实现的功能
"""

from typing import Dict, List, Set, Any, Tuple
import re
from loguru import logger
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class KLineUIComparator:
    """K线UI功能对比器"""

    def __init__(self):
        self.main_dialog = Path("gui/dialogs/unified_duckdb_import_dialog.py")
        self.dashboard = Path("gui/widgets/data_import_dashboard.py")
        self.backup_suffix = ".backup"

        # 原始版本文件
        self.original_dialog = self.main_dialog.with_suffix(self.main_dialog.suffix + self.backup_suffix)
        self.original_dashboard = self.dashboard.with_suffix(self.dashboard.suffix + self.backup_suffix)

    def compare_kline_ui_functionality(self):
        """对比K线UI功能"""
        logger.info("=== 原始 vs 当前 K线数据导入UI功能对比 ===")

        # 检查文件是否存在
        self._check_files_existence()

        # 对比主导入对话框
        dialog_comparison = self._compare_dialog_functionality()

        # 对比数据导入仪表板
        dashboard_comparison = self._compare_dashboard_functionality()

        # 对比K线特定功能
        kline_specific_comparison = self._compare_kline_specific_features()

        # 生成详细对比报告
        self._generate_detailed_comparison_report(dialog_comparison, dashboard_comparison, kline_specific_comparison)

        return {
            'dialog': dialog_comparison,
            'dashboard': dashboard_comparison,
            'kline_specific': kline_specific_comparison
        }

    def _check_files_existence(self):
        """检查文件存在性"""
        logger.info("\n📁 检查文件存在性:")

        files_to_check = [
            (self.main_dialog, "当前主对话框"),
            (self.dashboard, "当前仪表板"),
            (self.original_dialog, "原始主对话框"),
            (self.original_dashboard, "原始仪表板")
        ]

        for file_path, description in files_to_check:
            if file_path.exists():
                logger.info(f"  ✅ {description}: {file_path}")
            else:
                logger.error(f"  ❌ {description}: {file_path} - 文件不存在")

    def _compare_dialog_functionality(self) -> Dict[str, Any]:
        """对比主导入对话框功能"""
        logger.info("\n🔍 对比主导入对话框功能")

        if not self.original_dialog.exists() or not self.main_dialog.exists():
            logger.error("原始或当前对话框文件不存在，无法对比")
            return {}

        # 读取文件内容
        with open(self.original_dialog, 'r', encoding='utf-8') as f:
            original_content = f.read()

        with open(self.main_dialog, 'r', encoding='utf-8') as f:
            current_content = f.read()

        # 提取和对比各种功能
        comparison = {
            'classes': self._compare_classes(original_content, current_content),
            'methods': self._compare_methods(original_content, current_content),
            'ui_components': self._compare_ui_components(original_content, current_content),
            'event_handlers': self._compare_event_handlers(original_content, current_content),
            'imports': self._compare_imports(original_content, current_content),
            'tabs': self._compare_tabs(original_content, current_content),
            'buttons': self._compare_buttons(original_content, current_content),
            'configurations': self._compare_configurations(original_content, current_content)
        }

        self._print_dialog_comparison(comparison)
        return comparison

    def _compare_dashboard_functionality(self) -> Dict[str, Any]:
        """对比数据导入仪表板功能"""
        logger.info("\n🔍 对比数据导入仪表板功能")

        if not self.original_dashboard.exists() or not self.dashboard.exists():
            logger.error("原始或当前仪表板文件不存在，无法对比")
            return {}

        # 读取文件内容
        with open(self.original_dashboard, 'r', encoding='utf-8') as f:
            original_content = f.read()

        with open(self.dashboard, 'r', encoding='utf-8') as f:
            current_content = f.read()

        # 提取和对比各种功能
        comparison = {
            'classes': self._compare_classes(original_content, current_content),
            'methods': self._compare_methods(original_content, current_content),
            'charts': self._compare_charts(original_content, current_content),
            'metrics': self._compare_metrics(original_content, current_content),
            'timers': self._compare_timers(original_content, current_content),
            'performance_features': self._compare_performance_features(original_content, current_content)
        }

        self._print_dashboard_comparison(comparison)
        return comparison

    def _compare_kline_specific_features(self) -> Dict[str, Any]:
        """对比K线特定功能"""
        logger.info("\n🔍 对比K线特定功能")

        # 检查K线相关的具体功能
        kline_features = {
            'data_formats': self._check_kline_data_formats(),
            'timeframes': self._check_kline_timeframes(),
            'indicators': self._check_kline_indicators(),
            'visualization': self._check_kline_visualization(),
            'analysis_tools': self._check_kline_analysis_tools(),
            'export_options': self._check_kline_export_options(),
            'real_time_features': self._check_real_time_features(),
            'data_validation': self._check_data_validation_features()
        }

        self._print_kline_specific_comparison(kline_features)
        return kline_features

    def _compare_classes(self, original: str, current: str) -> Dict[str, Any]:
        """对比类"""
        original_classes = set(re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', original))
        current_classes = set(re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', current))

        return {
            'original': original_classes,
            'current': current_classes,
            'missing': original_classes - current_classes,
            'new': current_classes - original_classes,
            'common': original_classes & current_classes
        }

    def _compare_methods(self, original: str, current: str) -> Dict[str, Any]:
        """对比方法"""
        original_methods = set(re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', original))
        current_methods = set(re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', current))

        return {
            'original': original_methods,
            'current': current_methods,
            'missing': original_methods - current_methods,
            'new': current_methods - original_methods,
            'common': original_methods & current_methods
        }

    def _compare_ui_components(self, original: str, current: str) -> Dict[str, Any]:
        """对比UI组件"""
        ui_patterns = [
            r'Q[A-Z][a-zA-Z]*\s*\(',
            r'addTab\s*\(',
            r'addWidget\s*\(',
            r'addLayout\s*\('
        ]

        original_components = set()
        current_components = set()

        for pattern in ui_patterns:
            original_components.update(re.findall(pattern, original))
            current_components.update(re.findall(pattern, current))

        return {
            'original': original_components,
            'current': current_components,
            'missing': original_components - current_components,
            'new': current_components - original_components
        }

    def _compare_event_handlers(self, original: str, current: str) -> Dict[str, Any]:
        """对比事件处理器"""
        event_pattern = r'\.connect\s*\(\s*([^)]+)\s*\)'

        original_handlers = set(re.findall(event_pattern, original))
        current_handlers = set(re.findall(event_pattern, current))

        return {
            'original': original_handlers,
            'current': current_handlers,
            'missing': original_handlers - current_handlers,
            'new': current_handlers - original_handlers
        }

    def _compare_imports(self, original: str, current: str) -> Dict[str, Any]:
        """对比导入语句"""
        import_pattern = r'from\s+[\w.]+\s+import\s+([^#\n]+)'

        original_imports = set()
        current_imports = set()

        for match in re.findall(import_pattern, original):
            original_imports.update([item.strip() for item in match.split(',')])

        for match in re.findall(import_pattern, current):
            current_imports.update([item.strip() for item in match.split(',')])

        return {
            'original': original_imports,
            'current': current_imports,
            'missing': original_imports - current_imports,
            'new': current_imports - original_imports
        }

    def _compare_tabs(self, original: str, current: str) -> Dict[str, Any]:
        """对比标签页"""
        tab_pattern = r'addTab\s*\([^,]+,\s*["\']([^"\']+)["\']'

        original_tabs = set(re.findall(tab_pattern, original))
        current_tabs = set(re.findall(tab_pattern, current))

        return {
            'original': original_tabs,
            'current': current_tabs,
            'missing': original_tabs - current_tabs,
            'new': current_tabs - original_tabs
        }

    def _compare_buttons(self, original: str, current: str) -> Dict[str, Any]:
        """对比按钮"""
        button_pattern = r'QPushButton\s*\(\s*["\']([^"\']*)["\']'

        original_buttons = set(re.findall(button_pattern, original))
        current_buttons = set(re.findall(button_pattern, current))

        return {
            'original': original_buttons,
            'current': current_buttons,
            'missing': original_buttons - current_buttons,
            'new': current_buttons - original_buttons
        }

    def _compare_configurations(self, original: str, current: str) -> Dict[str, Any]:
        """对比配置相关功能"""
        config_patterns = [
            r'config\w*',
            r'setting\w*',
            r'parameter\w*',
            r'option\w*'
        ]

        original_configs = set()
        current_configs = set()

        for pattern in config_patterns:
            original_configs.update(re.findall(pattern, original, re.IGNORECASE))
            current_configs.update(re.findall(pattern, current, re.IGNORECASE))

        return {
            'original': original_configs,
            'current': current_configs,
            'missing': original_configs - current_configs,
            'new': current_configs - original_configs
        }

    def _compare_charts(self, original: str, current: str) -> Dict[str, Any]:
        """对比图表功能"""
        chart_patterns = [
            r'Chart\w*',
            r'Plot\w*',
            r'Graph\w*',
            r'Visualization\w*'
        ]

        original_charts = set()
        current_charts = set()

        for pattern in chart_patterns:
            original_charts.update(re.findall(pattern, original, re.IGNORECASE))
            current_charts.update(re.findall(pattern, current, re.IGNORECASE))

        return {
            'original': original_charts,
            'current': current_charts,
            'missing': original_charts - current_charts,
            'new': current_charts - original_charts
        }

    def _compare_metrics(self, original: str, current: str) -> Dict[str, Any]:
        """对比指标功能"""
        metric_patterns = [
            r'metric\w*',
            r'indicator\w*',
            r'performance\w*',
            r'statistics\w*'
        ]

        original_metrics = set()
        current_metrics = set()

        for pattern in metric_patterns:
            original_metrics.update(re.findall(pattern, original, re.IGNORECASE))
            current_metrics.update(re.findall(pattern, current, re.IGNORECASE))

        return {
            'original': original_metrics,
            'current': current_metrics,
            'missing': original_metrics - current_metrics,
            'new': current_metrics - original_metrics
        }

    def _compare_timers(self, original: str, current: str) -> Dict[str, Any]:
        """对比定时器功能"""
        timer_pattern = r'(\w*[Tt]imer\w*).*?\.start\s*\(\s*(\d+)\s*\)'

        original_timers = {}
        current_timers = {}

        for timer_name, interval in re.findall(timer_pattern, original):
            original_timers[timer_name] = interval

        for timer_name, interval in re.findall(timer_pattern, current):
            current_timers[timer_name] = interval

        return {
            'original': original_timers,
            'current': current_timers,
            'changed': {k: (original_timers.get(k), current_timers.get(k))
                        for k in set(original_timers.keys()) | set(current_timers.keys())
                        if original_timers.get(k) != current_timers.get(k)}
        }

    def _compare_performance_features(self, original: str, current: str) -> Dict[str, Any]:
        """对比性能功能"""
        perf_patterns = [
            r'performance\w*',
            r'monitor\w*',
            r'optimize\w*',
            r'profil\w*'
        ]

        original_perf = set()
        current_perf = set()

        for pattern in perf_patterns:
            original_perf.update(re.findall(pattern, original, re.IGNORECASE))
            current_perf.update(re.findall(pattern, current, re.IGNORECASE))

        return {
            'original': original_perf,
            'current': current_perf,
            'missing': original_perf - current_perf,
            'new': current_perf - original_perf
        }

    def _check_kline_data_formats(self) -> Dict[str, Any]:
        """检查K线数据格式支持"""
        formats_to_check = ['CSV', 'Excel', 'JSON', 'Parquet', 'HDF5', 'Feather']

        found_formats = {}
        for file_path in [self.main_dialog, self.dashboard]:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for format_name in formats_to_check:
                    found_formats[format_name] = format_name.lower() in content.lower()

        return found_formats

    def _check_kline_timeframes(self) -> Dict[str, Any]:
        """检查K线时间框架支持"""
        timeframes_to_check = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']

        found_timeframes = {}
        for file_path in [self.main_dialog, self.dashboard]:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for timeframe in timeframes_to_check:
                    found_timeframes[timeframe] = timeframe in content

        return found_timeframes

    def _check_kline_indicators(self) -> Dict[str, Any]:
        """检查K线技术指标支持"""
        indicators_to_check = ['MA', 'EMA', 'MACD', 'RSI', 'Bollinger', 'KDJ', 'Volume']

        found_indicators = {}
        for file_path in [self.main_dialog, self.dashboard]:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for indicator in indicators_to_check:
                    found_indicators[indicator] = indicator.lower() in content.lower()

        return found_indicators

    def _check_kline_visualization(self) -> Dict[str, Any]:
        """检查K线可视化功能"""
        viz_features = ['Candlestick', 'OHLC', 'Line', 'Area', 'Heikin-Ashi']

        found_viz = {}
        for file_path in [self.main_dialog, self.dashboard]:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for feature in viz_features:
                    found_viz[feature] = feature.lower() in content.lower()

        return found_viz

    def _check_kline_analysis_tools(self) -> Dict[str, Any]:
        """检查K线分析工具"""
        analysis_tools = ['Pattern Recognition', 'Trend Analysis', 'Support/Resistance', 'Fibonacci']

        found_tools = {}
        for file_path in [self.main_dialog, self.dashboard]:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for tool in analysis_tools:
                    found_tools[tool] = any(word.lower() in content.lower() for word in tool.split())

        return found_tools

    def _check_kline_export_options(self) -> Dict[str, Any]:
        """检查K线导出选项"""
        export_options = ['PDF', 'PNG', 'SVG', 'CSV Export', 'Excel Export']

        found_exports = {}
        for file_path in [self.main_dialog, self.dashboard]:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for option in export_options:
                    found_exports[option] = option.lower().replace(' ', '') in content.lower().replace(' ', '')

        return found_exports

    def _check_real_time_features(self) -> Dict[str, Any]:
        """检查实时功能"""
        realtime_features = ['Real-time Update', 'Live Data', 'Streaming', 'WebSocket']

        found_realtime = {}
        for file_path in [self.main_dialog, self.dashboard]:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for feature in realtime_features:
                    found_realtime[feature] = any(word.lower() in content.lower() for word in feature.split())

        return found_realtime

    def _check_data_validation_features(self) -> Dict[str, Any]:
        """检查数据验证功能"""
        validation_features = ['Data Quality', 'Validation', 'Cleaning', 'Outlier Detection']

        found_validation = {}
        for file_path in [self.main_dialog, self.dashboard]:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for feature in validation_features:
                    found_validation[feature] = any(word.lower() in content.lower() for word in feature.split())

        return found_validation

    def _print_dialog_comparison(self, comparison: Dict[str, Any]):
        """打印对话框对比结果"""
        logger.info("\n📊 主导入对话框功能对比结果:")

        for category, data in comparison.items():
            if isinstance(data, dict) and 'missing' in data:
                missing_count = len(data['missing'])
                new_count = len(data['new'])
                common_count = len(data.get('common', []))

                logger.info(f"\n  📂 {category.upper()}:")
                logger.info(f"    ✅ 保留: {common_count} 个")

                if missing_count > 0:
                    logger.warning(f"    ❌ 缺失: {missing_count} 个")
                    for item in list(data['missing'])[:5]:  # 显示前5个
                        logger.warning(f"      • {item}")
                    if missing_count > 5:
                        logger.warning(f"      ... 还有 {missing_count - 5} 个缺失项")

                if new_count > 0:
                    logger.info(f"    🆕 新增: {new_count} 个")
                    for item in list(data['new'])[:3]:  # 显示前3个
                        logger.info(f"      • {item}")

    def _print_dashboard_comparison(self, comparison: Dict[str, Any]):
        """打印仪表板对比结果"""
        logger.info("\n📊 数据导入仪表板功能对比结果:")

        for category, data in comparison.items():
            if isinstance(data, dict):
                if 'missing' in data:
                    missing_count = len(data['missing'])
                    if missing_count > 0:
                        logger.warning(f"  ❌ {category.upper()} 缺失: {missing_count} 个")
                        for item in list(data['missing'])[:3]:
                            logger.warning(f"    • {item}")
                elif 'changed' in data:  # 定时器对比
                    changed_count = len(data['changed'])
                    if changed_count > 0:
                        logger.info(f"  🔄 {category.upper()} 更改: {changed_count} 个")
                        for timer, (old, new) in data['changed'].items():
                            logger.info(f"    • {timer}: {old}ms → {new}ms")

    def _print_kline_specific_comparison(self, kline_features: Dict[str, Any]):
        """打印K线特定功能对比结果"""
        logger.info("\n📊 K线特定功能检查结果:")

        for category, features in kline_features.items():
            logger.info(f"\n  📂 {category.upper().replace('_', ' ')}:")

            if isinstance(features, dict):
                supported = sum(1 for v in features.values() if v)
                total = len(features)

                logger.info(f"    📈 支持率: {supported}/{total} ({supported/total*100:.1f}%)")

                for feature, supported in features.items():
                    status = "✅" if supported else "❌"
                    logger.info(f"    {status} {feature}")

    def _generate_detailed_comparison_report(self, dialog_comparison, dashboard_comparison, kline_specific):
        """生成详细对比报告"""
        logger.info("\n" + "=" * 80)
        logger.info("📋 K线数据导入UI功能对比详细报告")
        logger.info("=" * 80)

        # 统计缺失功能
        total_missing_methods = 0
        total_missing_classes = 0
        total_missing_ui_components = 0

        if dialog_comparison:
            total_missing_methods += len(dialog_comparison.get('methods', {}).get('missing', []))
            total_missing_classes += len(dialog_comparison.get('classes', {}).get('missing', []))
            total_missing_ui_components += len(dialog_comparison.get('ui_components', {}).get('missing', []))

        logger.info(f"\n🎯 功能缺失统计:")
        if total_missing_methods > 0:
            logger.warning(f"  ❌ 缺失方法: {total_missing_methods} 个")
        else:
            logger.info(f"  ✅ 方法完整: 无缺失")

        if total_missing_classes > 0:
            logger.warning(f"  ❌ 缺失类: {total_missing_classes} 个")
        else:
            logger.info(f"  ✅ 类完整: 无缺失")

        if total_missing_ui_components > 0:
            logger.warning(f"  ❌ 缺失UI组件: {total_missing_ui_components} 个")
        else:
            logger.info(f"  ✅ UI组件完整: 无缺失")

        # K线特定功能支持率
        if kline_specific:
            total_kline_features = 0
            supported_kline_features = 0

            for category, features in kline_specific.items():
                if isinstance(features, dict):
                    total_kline_features += len(features)
                    supported_kline_features += sum(1 for v in features.values() if v)

            kline_support_rate = (supported_kline_features / total_kline_features * 100) if total_kline_features > 0 else 0

            logger.info(f"\n🎯 K线特定功能支持:")
            logger.info(f"  📊 支持率: {supported_kline_features}/{total_kline_features} ({kline_support_rate:.1f}%)")

            if kline_support_rate < 50:
                logger.warning(f"  ⚠️ K线功能支持率较低，需要重点改进")
            elif kline_support_rate < 80:
                logger.info(f"  📈 K线功能支持率中等，还有改进空间")
            else:
                logger.info(f"  ✅ K线功能支持率良好")

        # 提供修复建议
        self._provide_fix_recommendations(dialog_comparison, dashboard_comparison, kline_specific)

    def _provide_fix_recommendations(self, dialog_comparison, dashboard_comparison, kline_specific):
        """提供修复建议"""
        logger.info(f"\n💡 修复建议:")

        # 检查是否有严重缺失
        has_major_issues = False

        if dialog_comparison:
            missing_methods = len(dialog_comparison.get('methods', {}).get('missing', []))
            missing_classes = len(dialog_comparison.get('classes', {}).get('missing', []))

            if missing_methods > 5 or missing_classes > 2:
                has_major_issues = True
                logger.warning("🚨 发现严重功能缺失，建议:")
                logger.warning("  1. 检查原始版本备份文件")
                logger.warning("  2. 恢复缺失的关键功能")
                logger.warning("  3. 重新实现缺失的方法和类")

        if kline_specific:
            # 检查K线特定功能
            low_support_categories = []
            for category, features in kline_specific.items():
                if isinstance(features, dict):
                    support_rate = sum(1 for v in features.values() if v) / len(features)
                    if support_rate < 0.3:  # 支持率低于30%
                        low_support_categories.append(category)

            if low_support_categories:
                has_major_issues = True
                logger.warning(f"  📊 K线功能支持不足的领域:")
                for category in low_support_categories:
                    logger.warning(f"    • {category.replace('_', ' ').title()}")

        if not has_major_issues:
            logger.info("✅ 整体功能保持良好，只需微调:")
            logger.info("  1. 完善K线特定功能")
            logger.info("  2. 添加缺失的小功能")
            logger.info("  3. 优化用户体验")
        else:
            logger.warning("🔧 需要重大改进:")
            logger.warning("  1. 从备份恢复缺失功能")
            logger.warning("  2. 重新实现K线专用功能")
            logger.warning("  3. 全面测试功能完整性")


def main():
    """主函数"""
    logger.info("K线数据导入UI功能对比工具")
    logger.info("对比原始版本和当前版本的功能差异")

    comparator = KLineUIComparator()
    results = comparator.compare_kline_ui_functionality()

    logger.info("\n📁 对比完成！请查看上述详细报告。")


if __name__ == "__main__":
    main()
