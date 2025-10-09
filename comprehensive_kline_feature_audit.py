#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面K线功能审计工具

深度分析整个项目中的K线相关功能，包括：
- 技术指标模块
- 可视化组件
- 数据导入导出
- 图表渲染
- 实时数据功能
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple
import re
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class KLineFeatureAuditor:
    """K线功能审计器"""

    def __init__(self):
        self.project_root = Path(".")
        self.feature_modules = {
            'technical_indicators': [],
            'chart_rendering': [],
            'data_import_export': [],
            'ui_components': [],
            'visualization': [],
            'real_time_features': [],
            'data_validation': [],
            'analysis_tools': []
        }

    def audit_all_kline_features(self):
        """审计所有K线相关功能"""
        logger.info("=== 全面K线功能审计开始 ===")

        # 1. 扫描所有相关文件
        relevant_files = self._find_kline_related_files()
        logger.info(f"📁 发现K线相关文件: {len(relevant_files)} 个")

        # 2. 分析各类功能模块
        feature_analysis = self._analyze_feature_modules(relevant_files)

        # 3. 检查UI集成状态
        ui_integration = self._check_ui_integration()

        # 4. 生成功能完整性报告
        self._generate_comprehensive_report(feature_analysis, ui_integration)

        return {
            'files': relevant_files,
            'features': feature_analysis,
            'ui_integration': ui_integration
        }

    def _find_kline_related_files(self) -> List[Path]:
        """查找所有K线相关文件"""
        patterns = [
            r'.*kline.*\.py$',
            r'.*chart.*\.py$',
            r'.*indicator.*\.py$',
            r'.*technical.*\.py$',
            r'.*candlestick.*\.py$',
            r'.*ohlc.*\.py$',
            r'.*analysis.*\.py$'
        ]

        relevant_files = []

        # 搜索所有Python文件
        for py_file in self.project_root.glob("**/*.py"):
            if any(re.match(pattern, str(py_file), re.IGNORECASE) for pattern in patterns):
                relevant_files.append(py_file)
                continue

            # 检查文件内容是否包含K线相关关键字
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                kline_keywords = [
                    'kline', 'candlestick', 'ohlc', 'technical.*indicator',
                    'ma|ema|macd|rsi|bollinger|kdj', 'chart.*render',
                    'data.*import.*kline', 'price.*visualization'
                ]

                if any(re.search(keyword, content, re.IGNORECASE) for keyword in kline_keywords):
                    relevant_files.append(py_file)

            except Exception as e:
                continue

        return relevant_files

    def _analyze_feature_modules(self, files: List[Path]) -> Dict[str, Any]:
        """分析功能模块"""
        feature_analysis = {
            'technical_indicators': self._analyze_technical_indicators(files),
            'chart_rendering': self._analyze_chart_rendering(files),
            'data_processing': self._analyze_data_processing(files),
            'ui_components': self._analyze_ui_components(files),
            'visualization': self._analyze_visualization(files),
            'real_time_features': self._analyze_real_time_features(files),
            'export_features': self._analyze_export_features(files),
            'advanced_analysis': self._analyze_advanced_analysis(files)
        }

        return feature_analysis

    def _analyze_technical_indicators(self, files: List[Path]) -> Dict[str, Any]:
        """分析技术指标功能"""
        indicators = {
            'MA': [], 'EMA': [], 'MACD': [], 'RSI': [],
            'Bollinger': [], 'KDJ': [], 'Volume': [], 'BOLL': [],
            'STOCH': [], 'Williams': [], 'CCI': [], 'ATR': []
        }

        implementations = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 检查每个指标
                for indicator in indicators.keys():
                    patterns = [
                        rf'def.*{indicator.lower()}.*\(',
                        rf'class.*{indicator}.*:',
                        rf'{indicator.upper()}.*=',
                        rf'calculate.*{indicator.lower()}'
                    ]

                    for pattern in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            indicators[indicator].append({
                                'file': str(file_path),
                                'type': 'implementation'
                            })
                            break

                # 查找技术指标实现
                impl_patterns = [
                    r'def\s+calculate_(\w+)',
                    r'class\s+(\w+Indicator)',
                    r'def\s+(\w+_indicator)'
                ]

                for pattern in impl_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        implementations.append({
                            'name': match,
                            'file': str(file_path)
                        })

            except Exception:
                continue

        return {
            'supported_indicators': indicators,
            'implementations': implementations,
            'total_indicators': len([ind for ind, files in indicators.items() if files]),
            'total_implementations': len(implementations)
        }

    def _analyze_chart_rendering(self, files: List[Path]) -> Dict[str, Any]:
        """分析图表渲染功能"""
        chart_types = {
            'Candlestick': [],
            'OHLC': [],
            'Line': [],
            'Area': [],
            'Volume': []
        }

        renderers = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 检查图表类型
                for chart_type in chart_types.keys():
                    patterns = [
                        rf'render.*{chart_type.lower()}',
                        rf'{chart_type}.*chart',
                        rf'plot.*{chart_type.lower()}'
                    ]

                    for pattern in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            chart_types[chart_type].append(str(file_path))
                            break

                # 查找渲染器
                renderer_patterns = [
                    r'class\s+(\w+Renderer)',
                    r'def\s+render_(\w+)',
                    r'class\s+(\w+Chart)'
                ]

                for pattern in renderer_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        renderers.append({
                            'name': match,
                            'file': str(file_path)
                        })

            except Exception:
                continue

        return {
            'chart_types': chart_types,
            'renderers': renderers,
            'supported_charts': len([ct for ct, files in chart_types.items() if files]),
            'total_renderers': len(renderers)
        }

    def _analyze_data_processing(self, files: List[Path]) -> Dict[str, Any]:
        """分析数据处理功能"""
        data_formats = {
            'CSV': [], 'Excel': [], 'JSON': [], 'Parquet': [], 'HDF5': [], 'Feather': []
        }

        processors = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 检查数据格式支持
                for format_name in data_formats.keys():
                    patterns = [
                        rf'\.to_{format_name.lower()}\(',
                        rf'read_{format_name.lower()}\(',
                        rf'{format_name.lower()}.*import',
                        rf'export.*{format_name.lower()}'
                    ]

                    for pattern in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            data_formats[format_name].append(str(file_path))
                            break

                # 查找数据处理器
                processor_patterns = [
                    r'class\s+(\w+Processor)',
                    r'def\s+process_(\w+)',
                    r'class\s+(\w+Importer)'
                ]

                for pattern in processor_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        processors.append({
                            'name': match,
                            'file': str(file_path)
                        })

            except Exception:
                continue

        return {
            'data_formats': data_formats,
            'processors': processors,
            'supported_formats': len([fmt for fmt, files in data_formats.items() if files]),
            'total_processors': len(processors)
        }

    def _analyze_ui_components(self, files: List[Path]) -> Dict[str, Any]:
        """分析UI组件"""
        ui_components = {
            'Dialogs': [],
            'Widgets': [],
            'Charts': [],
            'Panels': [],
            'Tabs': []
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 检查UI组件类型
                if 'QDialog' in content or 'dialog' in str(file_path).lower():
                    ui_components['Dialogs'].append(str(file_path))

                if 'QWidget' in content or 'widget' in str(file_path).lower():
                    ui_components['Widgets'].append(str(file_path))

                if any(chart_word in content.lower() for chart_word in ['chart', 'plot', 'graph']):
                    ui_components['Charts'].append(str(file_path))

                if 'panel' in str(file_path).lower() or 'QFrame' in content:
                    ui_components['Panels'].append(str(file_path))

                if 'QTabWidget' in content or 'tab' in str(file_path).lower():
                    ui_components['Tabs'].append(str(file_path))

            except Exception:
                continue

        return {
            'components': ui_components,
            'total_components': sum(len(files) for files in ui_components.values())
        }

    def _analyze_visualization(self, files: List[Path]) -> Dict[str, Any]:
        """分析可视化功能"""
        viz_libraries = {
            'Matplotlib': [], 'PyQt5': [], 'Plotly': [], 'Bokeh': [], 'WebGL': []
        }

        viz_features = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 检查可视化库
                for lib in viz_libraries.keys():
                    if lib.lower() in content.lower():
                        viz_libraries[lib].append(str(file_path))

                # 查找可视化特性
                viz_patterns = [
                    r'def\s+plot_(\w+)',
                    r'def\s+draw_(\w+)',
                    r'def\s+render_(\w+)',
                    r'class\s+(\w+Visualizer)'
                ]

                for pattern in viz_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        viz_features.append({
                            'name': match,
                            'file': str(file_path)
                        })

            except Exception:
                continue

        return {
            'libraries': viz_libraries,
            'features': viz_features,
            'supported_libraries': len([lib for lib, files in viz_libraries.items() if files]),
            'total_features': len(viz_features)
        }

    def _analyze_real_time_features(self, files: List[Path]) -> Dict[str, Any]:
        """分析实时功能"""
        realtime_keywords = [
            'real.*time', 'live.*data', 'streaming', 'websocket',
            'update.*timer', 'auto.*refresh', 'real.*time.*update'
        ]

        realtime_files = []
        features = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for keyword in realtime_keywords:
                    if re.search(keyword, content, re.IGNORECASE):
                        realtime_files.append(str(file_path))

                        # 提取具体功能
                        feature_patterns = [
                            r'def\s+(\w*update\w*)',
                            r'def\s+(\w*refresh\w*)',
                            r'class\s+(\w*Timer\w*)',
                            r'QTimer'
                        ]

                        for pattern in feature_patterns:
                            matches = re.findall(pattern, content)
                            for match in matches:
                                if match:  # 排除空匹配
                                    features.append({
                                        'name': match,
                                        'file': str(file_path)
                                    })
                        break

            except Exception:
                continue

        return {
            'realtime_files': list(set(realtime_files)),
            'features': features,
            'total_files': len(set(realtime_files)),
            'total_features': len(features)
        }

    def _analyze_export_features(self, files: List[Path]) -> Dict[str, Any]:
        """分析导出功能"""
        export_formats = {
            'PDF': [], 'PNG': [], 'SVG': [], 'CSV': [], 'Excel': []
        }

        export_functions = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 检查导出格式
                for format_name in export_formats.keys():
                    patterns = [
                        rf'export.*{format_name.lower()}',
                        rf'save.*{format_name.lower()}',
                        rf'\.{format_name.lower()}\(',
                        rf'to_{format_name.lower()}'
                    ]

                    for pattern in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            export_formats[format_name].append(str(file_path))
                            break

                # 查找导出函数
                export_patterns = [
                    r'def\s+(export_\w+)',
                    r'def\s+(save_\w+)',
                    r'class\s+(\w+Exporter)'
                ]

                for pattern in export_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        export_functions.append({
                            'name': match,
                            'file': str(file_path)
                        })

            except Exception:
                continue

        return {
            'formats': export_formats,
            'functions': export_functions,
            'supported_formats': len([fmt for fmt, files in export_formats.items() if files]),
            'total_functions': len(export_functions)
        }

    def _analyze_advanced_analysis(self, files: List[Path]) -> Dict[str, Any]:
        """分析高级分析功能"""
        analysis_features = {
            'Pattern Recognition': [],
            'Trend Analysis': [],
            'Support/Resistance': [],
            'Fibonacci': [],
            'Volume Analysis': []
        }

        analysis_tools = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 检查分析功能
                for feature in analysis_features.keys():
                    keywords = feature.lower().split('/')
                    if any(re.search(keyword.strip(), content, re.IGNORECASE) for keyword in keywords):
                        analysis_features[feature].append(str(file_path))

                # 查找分析工具
                tool_patterns = [
                    r'def\s+(analyze_\w+)',
                    r'def\s+(detect_\w+)',
                    r'class\s+(\w+Analyzer)',
                    r'class\s+(\w+Detector)'
                ]

                for pattern in tool_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        analysis_tools.append({
                            'name': match,
                            'file': str(file_path)
                        })

            except Exception:
                continue

        return {
            'features': analysis_features,
            'tools': analysis_tools,
            'supported_features': len([feat for feat, files in analysis_features.items() if files]),
            'total_tools': len(analysis_tools)
        }

    def _check_ui_integration(self) -> Dict[str, Any]:
        """检查UI集成状态"""
        main_ui_files = [
            "gui/dialogs/unified_duckdb_import_dialog.py",
            "gui/widgets/data_import_dashboard.py"
        ]

        integration_status = {}

        for ui_file in main_ui_files:
            ui_path = Path(ui_file)
            if ui_path.exists():
                try:
                    with open(ui_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    integration_status[ui_file] = {
                        'has_chart_import': 'Chart' in content,
                        'has_indicator_import': any(ind in content for ind in ['MA', 'EMA', 'MACD', 'RSI']),
                        'has_visualization': any(viz in content for viz in ['plot', 'render', 'draw']),
                        'has_export_functions': any(exp in content for exp in ['export', 'save']),
                        'has_realtime_features': any(rt in content for rt in ['timer', 'update', 'refresh']),
                        'imports_count': len(re.findall(r'^from .* import', content, re.MULTILINE)),
                        'classes_count': len(re.findall(r'^class ', content, re.MULTILINE)),
                        'methods_count': len(re.findall(r'def ', content))
                    }
                except Exception as e:
                    integration_status[ui_file] = {'error': str(e)}
            else:
                integration_status[ui_file] = {'error': 'File not found'}

        return integration_status

    def _generate_comprehensive_report(self, feature_analysis: Dict[str, Any], ui_integration: Dict[str, Any]):
        """生成综合报告"""
        logger.info("\n" + "=" * 80)
        logger.info("📋 K线功能全面审计报告")
        logger.info("=" * 80)

        # 技术指标分析
        indicators = feature_analysis['technical_indicators']
        logger.info(f"\n🔧 技术指标功能:")
        logger.info(f"  📊 支持的指标: {indicators['total_indicators']}/12")
        logger.info(f"  🔨 实现模块: {indicators['total_implementations']} 个")

        supported_indicators = [ind for ind, files in indicators['supported_indicators'].items() if files]
        if supported_indicators:
            logger.info(f"  ✅ 已支持: {', '.join(supported_indicators)}")

        # 图表渲染分析
        charts = feature_analysis['chart_rendering']
        logger.info(f"\n📈 图表渲染功能:")
        logger.info(f"  📊 支持的图表类型: {charts['supported_charts']}/5")
        logger.info(f"  🎨 渲染器: {charts['total_renderers']} 个")

        # 数据处理分析
        data_proc = feature_analysis['data_processing']
        logger.info(f"\n💾 数据处理功能:")
        logger.info(f"  📊 支持的格式: {data_proc['supported_formats']}/6")
        logger.info(f"  处理器: {data_proc['total_processors']} 个")

        # UI组件分析
        ui_comp = feature_analysis['ui_components']
        logger.info(f"\n🖥️ UI组件:")
        logger.info(f"  📊 总组件数: {ui_comp['total_components']}")
        for comp_type, files in ui_comp['components'].items():
            logger.info(f"    • {comp_type}: {len(files)} 个")

        # 可视化分析
        viz = feature_analysis['visualization']
        logger.info(f"\n🎨 可视化功能:")
        logger.info(f"  📊 支持的库: {viz['supported_libraries']}/5")
        logger.info(f"  🔧 可视化功能: {viz['total_features']} 个")

        # 实时功能分析
        realtime = feature_analysis['real_time_features']
        logger.info(f"\n⚡ 实时功能:")
        logger.info(f"  📊 相关文件: {realtime['total_files']} 个")
        logger.info(f"  🔧 实时功能: {realtime['total_features']} 个")

        # 导出功能分析
        export = feature_analysis['export_features']
        logger.info(f"\n📤 导出功能:")
        logger.info(f"  📊 支持的格式: {export['supported_formats']}/5")
        logger.info(f"  🔧 导出功能: {export['total_functions']} 个")

        # 高级分析功能
        advanced = feature_analysis['advanced_analysis']
        logger.info(f"\n🧠 高级分析功能:")
        logger.info(f"  📊 支持的功能: {advanced['supported_features']}/5")
        logger.info(f"  🔧 分析工具: {advanced['total_tools']} 个")

        # UI集成状态
        logger.info(f"\n🔗 UI集成状态:")
        for ui_file, status in ui_integration.items():
            logger.info(f"  📄 {ui_file}:")
            if 'error' in status:
                logger.error(f"    ❌ 错误: {status['error']}")
            else:
                for feature, has_feature in status.items():
                    if isinstance(has_feature, bool):
                        status_icon = "✅" if has_feature else "❌"
                        logger.info(f"    {status_icon} {feature}: {has_feature}")
                    elif isinstance(has_feature, int):
                        logger.info(f"    📊 {feature}: {has_feature}")

        # 总体评分
        self._calculate_overall_score(feature_analysis, ui_integration)

    def _calculate_overall_score(self, feature_analysis: Dict[str, Any], ui_integration: Dict[str, Any]):
        """计算总体评分"""
        logger.info(f"\n🎯 总体功能评分:")

        # 计算各模块得分
        scores = {}

        # 技术指标得分 (满分25分)
        indicators = feature_analysis['technical_indicators']
        scores['indicators'] = (indicators['total_indicators'] / 12) * 25

        # 图表渲染得分 (满分20分)
        charts = feature_analysis['chart_rendering']
        scores['charts'] = (charts['supported_charts'] / 5) * 20

        # 数据处理得分 (满分15分)
        data_proc = feature_analysis['data_processing']
        scores['data_processing'] = (data_proc['supported_formats'] / 6) * 15

        # 可视化得分 (满分15分)
        viz = feature_analysis['visualization']
        scores['visualization'] = (viz['supported_libraries'] / 5) * 15

        # 实时功能得分 (满分10分)
        realtime = feature_analysis['real_time_features']
        scores['realtime'] = min((realtime['total_files'] / 5) * 10, 10)

        # 导出功能得分 (满分10分)
        export = feature_analysis['export_features']
        scores['export'] = (export['supported_formats'] / 5) * 10

        # 高级分析得分 (满分5分)
        advanced = feature_analysis['advanced_analysis']
        scores['advanced'] = (advanced['supported_features'] / 5) * 5

        # 显示得分
        total_score = sum(scores.values())
        for module, score in scores.items():
            logger.info(f"  📊 {module}: {score:.1f}分")

        logger.info(f"\n🏆 总分: {total_score:.1f}/100")

        if total_score >= 80:
            logger.info("✅ 功能完善度: 优秀")
        elif total_score >= 60:
            logger.info("📈 功能完善度: 良好")
        elif total_score >= 40:
            logger.info("⚠️ 功能完善度: 中等，需要改进")
        else:
            logger.warning("🚨 功能完善度: 较低，需要重点改进")


def main():
    """主函数"""
    logger.info("K线功能全面审计工具启动")

    auditor = KLineFeatureAuditor()
    results = auditor.audit_all_kline_features()

    logger.info("\n✅ 审计完成！")


if __name__ == "__main__":
    main()
