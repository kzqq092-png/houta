#!/usr/bin/env python3
"""
策略执行和风险控制逻辑分析器
==========================

深入分析回测系统中的策略执行逻辑、风险控制机制和交易执行流程
"""

import sys
import ast
import inspect
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
import json
import re

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StrategyExecutionIssue:
    """策略执行问题"""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str
    method_name: str
    file_path: str
    line_number: int
    issue_type: str
    description: str
    code_snippet: str
    risk_level: str
    recommendation: str


@dataclass
class RiskControlAnalysis:
    """风险控制分析"""
    method_name: str
    risk_checks: List[str] = field(default_factory=list)
    missing_checks: List[str] = field(default_factory=list)
    potential_issues: List[str] = field(default_factory=list)
    safety_score: int = 0  # 0-100


class StrategyExecutionAnalyzer:
    """策略执行分析器"""

    def __init__(self):
        self.execution_issues = []
        self.risk_analyses = {}
        self.trading_flow_issues = []

    def analyze_strategy_execution(self) -> Dict[str, Any]:
        """分析策略执行逻辑"""
        logger.info("🎯 开始分析策略执行和风险控制逻辑...")

        results = {
            'execution_flow_analysis': {},
            'risk_control_analysis': {},
            'trading_logic_issues': [],
            'data_integrity_issues': [],
            'performance_issues': [],
            'safety_recommendations': [],
            'critical_fixes_needed': []
        }

        try:
            # 1. 分析执行流程
            logger.info("📊 分析执行流程...")
            results['execution_flow_analysis'] = self._analyze_execution_flow()

            # 2. 分析风险控制
            logger.info("🛡️ 分析风险控制机制...")
            results['risk_control_analysis'] = self._analyze_risk_control()

            # 3. 分析交易逻辑
            logger.info("💰 分析交易逻辑...")
            results['trading_logic_issues'] = self._analyze_trading_logic()

            # 4. 分析数据完整性
            logger.info("📋 分析数据完整性...")
            results['data_integrity_issues'] = self._analyze_data_integrity()

            # 5. 分析性能问题
            logger.info("⚡ 分析性能问题...")
            results['performance_issues'] = self._analyze_performance_issues()

            # 6. 生成安全建议
            logger.info("🔒 生成安全建议...")
            results['safety_recommendations'] = self._generate_safety_recommendations()

            # 7. 识别关键修复项
            results['critical_fixes_needed'] = self._identify_critical_fixes(results)

            logger.info("✅ 策略执行分析完成")
            return results

        except Exception as e:
            logger.error(f"策略执行分析失败: {e}")
            import traceback
            traceback.print_exc()
            return results

    def _analyze_execution_flow(self) -> Dict[str, Any]:
        """分析执行流程"""
        flow_analysis = {
            'main_execution_methods': [],
            'execution_order': [],
            'bottleneck_points': [],
            'error_handling_gaps': [],
            'flow_complexity': {}
        }

        # 分析主要执行文件
        main_files = [
            'backtest/unified_backtest_engine.py',
            'plugins/strategies/hikyuu_strategy_plugin.py',
            'plugins/strategies/backtrader_strategy_plugin.py'
        ]

        for file_path in main_files:
            full_path = project_root / file_path
            if full_path.exists():
                file_analysis = self._analyze_execution_file(full_path)
                flow_analysis['main_execution_methods'].extend(file_analysis['execution_methods'])
                flow_analysis['bottleneck_points'].extend(file_analysis['bottlenecks'])
                flow_analysis['error_handling_gaps'].extend(file_analysis['error_gaps'])

        return flow_analysis

    def _analyze_execution_file(self, file_path: Path) -> Dict[str, Any]:
        """分析执行文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            analysis = {
                'execution_methods': [],
                'bottlenecks': [],
                'error_gaps': []
            }

            # 查找关键执行方法
            execution_method_patterns = [
                'run_backtest', 'execute', 'process', 'calculate',
                '_run_core_backtest', '_process_trading_signals',
                '_execute_open_position', '_check_exit_conditions'
            ]

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    method_name = node.name

                    # 检查是否是执行方法
                    if any(pattern in method_name.lower() for pattern in execution_method_patterns):
                        method_info = self._analyze_execution_method(node, file_path)
                        analysis['execution_methods'].append(method_info)

                        # 检查瓶颈
                        if method_info['complexity'] > 15 or method_info['loop_count'] > 3:
                            analysis['bottlenecks'].append({
                                'method': method_name,
                                'file': str(file_path),
                                'reason': f"复杂度 {method_info['complexity']}, 循环 {method_info['loop_count']}"
                            })

                        # 检查错误处理缺陷
                        if method_info['bare_except_count'] > 0:
                            analysis['error_gaps'].append({
                                'method': method_name,
                                'file': str(file_path),
                                'issue': f"裸露异常处理 {method_info['bare_except_count']} 个"
                            })

            return analysis

        except Exception as e:
            logger.error(f"分析执行文件 {file_path} 失败: {e}")
            return {'execution_methods': [], 'bottlenecks': [], 'error_gaps': []}

    def _analyze_execution_method(self, node: ast.FunctionDef, file_path: Path) -> Dict[str, Any]:
        """分析执行方法"""
        method_info = {
            'name': node.name,
            'file': str(file_path),
            'line': node.lineno,
            'complexity': 1,
            'loop_count': 0,
            'condition_count': 0,
            'bare_except_count': 0,
            'database_calls': 0,
            'calculation_calls': 0,
            'potential_issues': []
        }

        # 分析方法体
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                method_info['complexity'] += 1
                if isinstance(child, (ast.While, ast.For)):
                    method_info['loop_count'] += 1
                else:
                    method_info['condition_count'] += 1

            elif isinstance(child, ast.ExceptHandler):
                if child.type is None:
                    method_info['bare_except_count'] += 1

            elif isinstance(child, ast.Call):
                if hasattr(child.func, 'attr'):
                    func_name = child.func.attr.lower()
                    if any(db_word in func_name for db_word in ['query', 'execute', 'fetch', 'commit']):
                        method_info['database_calls'] += 1
                    elif any(calc_word in func_name for calc_word in ['calculate', 'compute', 'sum', 'mean']):
                        method_info['calculation_calls'] += 1

        # 识别潜在问题
        if method_info['bare_except_count'] > 0:
            method_info['potential_issues'].append("裸露异常处理可能隐藏关键错误")

        if method_info['loop_count'] > 2 and method_info['database_calls'] > 0:
            method_info['potential_issues'].append("循环中包含数据库调用，可能影响性能")

        if method_info['complexity'] > 20:
            method_info['potential_issues'].append("方法复杂度过高，难以维护和测试")

        return method_info

    def _analyze_risk_control(self) -> Dict[str, Any]:
        """分析风险控制机制"""
        risk_analysis = {
            'position_management': {},
            'stop_loss_logic': {},
            'take_profit_logic': {},
            'risk_metrics_calculation': {},
            'portfolio_constraints': {},
            'missing_controls': []
        }

        # 分析UnifiedBacktestEngine中的风险控制
        engine_file = project_root / 'backtest/unified_backtest_engine.py'
        if engine_file.exists():
            risk_analysis.update(self._analyze_risk_control_in_file(engine_file))

        return risk_analysis

    def _analyze_risk_control_in_file(self, file_path: Path) -> Dict[str, Any]:
        """分析文件中的风险控制"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            risk_methods = {
                'position_management': [],
                'stop_loss_logic': [],
                'take_profit_logic': [],
                'risk_metrics_calculation': [],
                'portfolio_constraints': [],
                'missing_controls': []
            }

            # 查找风险控制相关方法
            risk_patterns = {
                'position_management': ['position', 'size', 'allocation'],
                'stop_loss_logic': ['stop_loss', 'sl', 'exit', 'loss'],
                'take_profit_logic': ['take_profit', 'tp', 'profit', 'target'],
                'risk_metrics_calculation': ['risk', 'drawdown', 'var', 'volatility'],
                'portfolio_constraints': ['constraint', 'limit', 'max', 'min']
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    method_name = node.name.lower()

                    for category, patterns in risk_patterns.items():
                        if any(pattern in method_name for pattern in patterns):
                            method_analysis = self._analyze_risk_method(node, file_path)
                            risk_methods[category].append(method_analysis)

            # 检查缺失的风险控制
            essential_controls = [
                'position_size_validation',
                'stop_loss_enforcement',
                'portfolio_risk_check',
                'drawdown_protection'
            ]

            found_controls = set()
            for category, methods in risk_methods.items():
                for method in methods:
                    method_name = method['name'].lower()
                    if 'position' in method_name and 'size' in method_name:
                        found_controls.add('position_size_validation')
                    elif 'stop' in method_name and 'loss' in method_name:
                        found_controls.add('stop_loss_enforcement')
                    elif 'portfolio' in method_name and 'risk' in method_name:
                        found_controls.add('portfolio_risk_check')
                    elif 'drawdown' in method_name:
                        found_controls.add('drawdown_protection')

            missing_controls = [control for control in essential_controls if control not in found_controls]
            risk_methods['missing_controls'] = missing_controls

            return risk_methods

        except Exception as e:
            logger.error(f"分析风险控制文件 {file_path} 失败: {e}")
            return {}

    def _analyze_risk_method(self, node: ast.FunctionDef, file_path: Path) -> Dict[str, Any]:
        """分析风险控制方法"""
        method_analysis = {
            'name': node.name,
            'file': str(file_path),
            'line': node.lineno,
            'risk_checks': [],
            'validation_logic': [],
            'error_handling': [],
            'potential_issues': []
        }

        # 分析方法内容
        method_source = ast.get_source_segment(open(file_path, 'r', encoding='utf-8').read(), node)
        if method_source:
            # 检查风险验证逻辑
            if re.search(r'if.*[<>]=?.*:', method_source):
                method_analysis['risk_checks'].append('数值范围检查')

            if re.search(r'assert\s+', method_source):
                method_analysis['validation_logic'].append('断言验证')

            if re.search(r'raise\s+', method_source):
                method_analysis['validation_logic'].append('异常抛出')

            if re.search(r'try:', method_source):
                method_analysis['error_handling'].append('异常处理')

            # 检查潜在问题
            if 'except:' in method_source:
                method_analysis['potential_issues'].append('裸露异常处理')

            if not method_analysis['risk_checks'] and 'risk' in node.name.lower():
                method_analysis['potential_issues'].append('风险方法缺少验证逻辑')

        return method_analysis

    def _analyze_trading_logic(self) -> List[Dict[str, Any]]:
        """分析交易逻辑"""
        trading_issues = []

        # 分析交易执行相关文件
        trading_files = [
            'backtest/unified_backtest_engine.py',
            'plugins/strategies/hikyuu_strategy_plugin.py'
        ]

        for file_path in trading_files:
            full_path = project_root / file_path
            if full_path.exists():
                file_issues = self._analyze_trading_file(full_path)
                trading_issues.extend(file_issues)

        return trading_issues

    def _analyze_trading_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """分析交易文件"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找交易执行方法
            trading_method_patterns = [
                '_execute_open_position',
                '_execute_close_position',
                '_process_trading_signals',
                'buy', 'sell', 'trade'
            ]

            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                line_lower = line.lower().strip()

                # 检查交易逻辑问题
                if any(pattern in line_lower for pattern in trading_method_patterns):
                    # 检查是否有适当的错误处理
                    if 'try:' not in content[max(0, content.find(line)-500):content.find(line)+500]:
                        issues.append({
                            'type': 'missing_error_handling',
                            'file': str(file_path),
                            'line': i,
                            'description': '交易执行缺少错误处理',
                            'severity': 'HIGH',
                            'code': line.strip()
                        })

                # 检查价格计算问题
                if 'price' in line_lower and ('*' in line or '/' in line):
                    if 'round' not in line_lower and 'decimal' not in line_lower:
                        issues.append({
                            'type': 'price_precision',
                            'file': str(file_path),
                            'line': i,
                            'description': '价格计算可能存在精度问题',
                            'severity': 'MEDIUM',
                            'code': line.strip()
                        })

                # 检查数量计算问题
                if 'quantity' in line_lower or 'shares' in line_lower:
                    if 'int(' not in line_lower and 'floor(' not in line_lower:
                        issues.append({
                            'type': 'quantity_precision',
                            'file': str(file_path),
                            'line': i,
                            'description': '股票数量计算可能产生小数',
                            'severity': 'MEDIUM',
                            'code': line.strip()
                        })

        except Exception as e:
            logger.error(f"分析交易文件 {file_path} 失败: {e}")

        return issues

    def _analyze_data_integrity(self) -> List[Dict[str, Any]]:
        """分析数据完整性"""
        integrity_issues = []

        # 检查数据验证逻辑
        data_files = [
            'backtest/unified_backtest_engine.py',
            'core/metrics/repository.py'
        ]

        for file_path in data_files:
            full_path = project_root / file_path
            if full_path.exists():
                file_issues = self._analyze_data_integrity_in_file(full_path)
                integrity_issues.extend(file_issues)

        return integrity_issues

    def _analyze_data_integrity_in_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """分析文件中的数据完整性"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                line_lower = line.lower().strip()

                # 检查数据访问是否有边界检查
                if '[' in line and ']' in line:
                    # 数组/列表访问
                    if 'len(' not in content[max(0, content.find(line)-200):content.find(line)]:
                        issues.append({
                            'type': 'missing_bounds_check',
                            'file': str(file_path),
                            'line': i,
                            'description': '数组访问缺少边界检查',
                            'severity': 'MEDIUM',
                            'code': line.strip()
                        })

                # 检查除法运算是否有零检查
                if '/' in line and 'if' not in line_lower:
                    if '!= 0' not in content[max(0, content.find(line)-100):content.find(line)+100]:
                        issues.append({
                            'type': 'division_by_zero_risk',
                            'file': str(file_path),
                            'line': i,
                            'description': '除法运算可能存在除零风险',
                            'severity': 'HIGH',
                            'code': line.strip()
                        })

                # 检查数据库查询结果是否验证
                if 'query' in line_lower or 'fetch' in line_lower:
                    if 'if' not in content[content.find(line):content.find(line)+200]:
                        issues.append({
                            'type': 'unchecked_query_result',
                            'file': str(file_path),
                            'line': i,
                            'description': '数据库查询结果未验证',
                            'severity': 'MEDIUM',
                            'code': line.strip()
                        })

        except Exception as e:
            logger.error(f"分析数据完整性文件 {file_path} 失败: {e}")

        return issues

    def _analyze_performance_issues(self) -> List[Dict[str, Any]]:
        """分析性能问题"""
        performance_issues = []

        # 基于之前的分析结果
        known_issues = [
            {
                'method': '_run_core_backtest',
                'issue': '核心回测循环可能存在性能瓶颈',
                'recommendation': '考虑向量化操作和并行处理'
            },
            {
                'method': '_process_trading_signals',
                'issue': '信号处理逻辑可能重复计算',
                'recommendation': '实现信号缓存机制'
            },
            {
                'method': 'query_historical_data',
                'issue': '历史数据查询可能频繁访问数据库',
                'recommendation': '实现数据预加载和缓存'
            }
        ]

        for issue in known_issues:
            performance_issues.append({
                'type': 'performance_bottleneck',
                'method': issue['method'],
                'description': issue['issue'],
                'recommendation': issue['recommendation'],
                'severity': 'HIGH'
            })

        return performance_issues

    def _generate_safety_recommendations(self) -> List[Dict[str, Any]]:
        """生成安全建议"""
        recommendations = [
            {
                'category': '异常处理',
                'priority': 'CRITICAL',
                'title': '修复裸露异常处理',
                'description': '将所有 except: 改为具体异常类型',
                'implementation': [
                    '识别所有裸露的 except: 语句',
                    '根据上下文确定具体异常类型',
                    '添加适当的错误日志记录',
                    '实现优雅的错误恢复机制'
                ]
            },
            {
                'category': '数据验证',
                'priority': 'HIGH',
                'title': '加强数据完整性检查',
                'description': '在关键数据操作前添加验证逻辑',
                'implementation': [
                    '添加数组边界检查',
                    '实现除零保护',
                    '验证数据库查询结果',
                    '添加数据类型检查'
                ]
            },
            {
                'category': '风险控制',
                'priority': 'HIGH',
                'title': '完善风险管理机制',
                'description': '实现全面的风险控制体系',
                'implementation': [
                    '添加仓位大小验证',
                    '实现止损止盈强制执行',
                    '添加组合风险监控',
                    '实现最大回撤保护'
                ]
            },
            {
                'category': '性能优化',
                'priority': 'MEDIUM',
                'title': '优化关键性能瓶颈',
                'description': '针对识别的瓶颈进行专项优化',
                'implementation': [
                    '实现数据缓存机制',
                    '使用向量化操作',
                    '考虑并行处理',
                    '优化数据库查询'
                ]
            }
        ]

        return recommendations

    def _identify_critical_fixes(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别关键修复项"""
        critical_fixes = []

        # 基于分析结果识别最关键的问题
        execution_flow = results.get('execution_flow_analysis', {})
        risk_control = results.get('risk_control_analysis', {})
        trading_issues = results.get('trading_logic_issues', [])
        data_issues = results.get('data_integrity_issues', [])

        # 关键修复项1：异常处理
        error_gaps = execution_flow.get('error_handling_gaps', [])
        if error_gaps:
            critical_fixes.append({
                'priority': 1,
                'category': '异常处理',
                'title': '修复异常处理缺陷',
                'affected_methods': [gap['method'] for gap in error_gaps],
                'risk_level': 'CRITICAL',
                'description': '多个关键方法存在裸露异常处理，可能隐藏严重错误'
            })

        # 关键修复项2：数据完整性
        high_severity_data_issues = [issue for issue in data_issues if issue.get('severity') == 'HIGH']
        if high_severity_data_issues:
            critical_fixes.append({
                'priority': 2,
                'category': '数据完整性',
                'title': '修复数据完整性问题',
                'affected_methods': list(set(issue['file'] for issue in high_severity_data_issues)),
                'risk_level': 'HIGH',
                'description': '存在除零风险和数据访问安全问题'
            })

        # 关键修复项3：风险控制缺失
        missing_controls = risk_control.get('missing_controls', [])
        if missing_controls:
            critical_fixes.append({
                'priority': 3,
                'category': '风险控制',
                'title': '实现缺失的风险控制',
                'missing_controls': missing_controls,
                'risk_level': 'HIGH',
                'description': '缺少关键的风险控制机制'
            })

        return critical_fixes

    def generate_strategy_analysis_report(self, results: Dict[str, Any]) -> str:
        """生成策略执行分析报告"""
        report = []
        report.append("# 策略执行和风险控制深度分析报告")
        report.append("=" * 80)

        # 执行摘要
        report.append(f"\n## 📊 执行摘要")

        execution_flow = results.get('execution_flow_analysis', {})
        risk_control = results.get('risk_control_analysis', {})
        trading_issues = results.get('trading_logic_issues', [])
        data_issues = results.get('data_integrity_issues', [])
        performance_issues = results.get('performance_issues', [])

        report.append(f"- 执行方法分析: {len(execution_flow.get('main_execution_methods', []))} 个")
        report.append(f"- 发现瓶颈点: {len(execution_flow.get('bottleneck_points', []))} 个")
        report.append(f"- 交易逻辑问题: {len(trading_issues)} 个")
        report.append(f"- 数据完整性问题: {len(data_issues)} 个")
        report.append(f"- 性能问题: {len(performance_issues)} 个")

        # 关键修复项
        critical_fixes = results.get('critical_fixes_needed', [])
        if critical_fixes:
            report.append(f"\n## 🚨 关键修复项")
            for fix in critical_fixes:
                report.append(f"\n### {fix['priority']}. {fix['title']} ({fix['risk_level']})")
                report.append(f"**类别**: {fix['category']}")
                report.append(f"**描述**: {fix['description']}")

                if 'affected_methods' in fix:
                    methods_str = ", ".join(fix['affected_methods'][:5])
                    if len(fix['affected_methods']) > 5:
                        methods_str += f" 等 {len(fix['affected_methods'])} 个"
                    report.append(f"**影响方法**: {methods_str}")

                if 'missing_controls' in fix:
                    report.append(f"**缺失控制**: {', '.join(fix['missing_controls'])}")

        # 执行流程分析
        if execution_flow:
            report.append(f"\n## 🔄 执行流程分析")

            bottlenecks = execution_flow.get('bottleneck_points', [])
            if bottlenecks:
                report.append(f"\n### 性能瓶颈点")
                for i, bottleneck in enumerate(bottlenecks[:10], 1):
                    report.append(f"{i}. **{bottleneck['method']}** ({Path(bottleneck['file']).name})")
                    report.append(f"   - 原因: {bottleneck['reason']}")

            error_gaps = execution_flow.get('error_handling_gaps', [])
            if error_gaps:
                report.append(f"\n### 错误处理缺陷")
                for i, gap in enumerate(error_gaps[:10], 1):
                    report.append(f"{i}. **{gap['method']}** ({Path(gap['file']).name})")
                    report.append(f"   - 问题: {gap['issue']}")

        # 风险控制分析
        if risk_control:
            report.append(f"\n## 🛡️ 风险控制分析")

            missing_controls = risk_control.get('missing_controls', [])
            if missing_controls:
                report.append(f"\n### 缺失的风险控制")
                for control in missing_controls:
                    report.append(f"- {control}")

            # 分析各类风险控制
            risk_categories = ['position_management', 'stop_loss_logic', 'take_profit_logic', 'risk_metrics_calculation']
            for category in risk_categories:
                methods = risk_control.get(category, [])
                if methods:
                    category_name = category.replace('_', ' ').title()
                    report.append(f"\n### {category_name}")
                    for method in methods[:5]:
                        report.append(f"- **{method['name']}** ({Path(method['file']).name}:{method['line']})")
                        if method.get('potential_issues'):
                            for issue in method['potential_issues']:
                                report.append(f"  ⚠️ {issue}")

        # 交易逻辑问题
        if trading_issues:
            report.append(f"\n## 💰 交易逻辑问题")

            # 按严重程度分组
            high_issues = [issue for issue in trading_issues if issue.get('severity') == 'HIGH']
            medium_issues = [issue for issue in trading_issues if issue.get('severity') == 'MEDIUM']

            if high_issues:
                report.append(f"\n### 🔴 高严重性问题")
                for i, issue in enumerate(high_issues, 1):
                    report.append(f"{i}. **{issue['type']}** ({Path(issue['file']).name}:{issue['line']})")
                    report.append(f"   - 描述: {issue['description']}")
                    report.append(f"   - 代码: `{issue['code']}`")

            if medium_issues:
                report.append(f"\n### 🟡 中严重性问题")
                for i, issue in enumerate(medium_issues[:5], 1):
                    report.append(f"{i}. **{issue['type']}** ({Path(issue['file']).name}:{issue['line']})")
                    report.append(f"   - 描述: {issue['description']}")

        # 数据完整性问题
        if data_issues:
            report.append(f"\n## 📋 数据完整性问题")

            high_data_issues = [issue for issue in data_issues if issue.get('severity') == 'HIGH']
            if high_data_issues:
                report.append(f"\n### 🔴 高风险数据问题")
                for i, issue in enumerate(high_data_issues, 1):
                    report.append(f"{i}. **{issue['type']}** ({Path(issue['file']).name}:{issue['line']})")
                    report.append(f"   - 描述: {issue['description']}")
                    report.append(f"   - 代码: `{issue['code']}`")

        # 安全建议
        safety_recommendations = results.get('safety_recommendations', [])
        if safety_recommendations:
            report.append(f"\n## 🔒 安全建议")

            for rec in safety_recommendations:
                report.append(f"\n### {rec['priority']} - {rec['title']}")
                report.append(f"**类别**: {rec['category']}")
                report.append(f"**描述**: {rec['description']}")

                if rec.get('implementation'):
                    report.append("**实施步骤**:")
                    for step in rec['implementation']:
                        report.append(f"- {step}")

        return "\n".join(report)

    def run_analysis_and_save_report(self):
        """运行分析并保存报告"""
        try:
            # 运行策略执行分析
            results = self.analyze_strategy_execution()

            # 生成报告
            report = self.generate_strategy_analysis_report(results)

            # 保存报告
            with open('strategy_execution_analysis.md', 'w', encoding='utf-8') as f:
                f.write(report)

            # 保存原始数据
            with open('strategy_execution_data.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

            # 显示摘要
            print("\n" + "="*80)
            print("🎯 策略执行和风险控制分析结果")
            print("="*80)

            execution_flow = results.get('execution_flow_analysis', {})
            trading_issues = results.get('trading_logic_issues', [])
            data_issues = results.get('data_integrity_issues', [])
            critical_fixes = results.get('critical_fixes_needed', [])

            print(f"📊 分析结果:")
            print(f"   执行方法: {len(execution_flow.get('main_execution_methods', []))} 个")
            print(f"   瓶颈点: {len(execution_flow.get('bottleneck_points', []))} 个")
            print(f"   交易问题: {len(trading_issues)} 个")
            print(f"   数据问题: {len(data_issues)} 个")

            if critical_fixes:
                print(f"\n🚨 关键修复项:")
                for fix in critical_fixes[:3]:
                    print(f"   - {fix['title']} ({fix['risk_level']})")

            logger.info("📄 策略执行分析报告已保存到 strategy_execution_analysis.md")
            logger.info("📄 原始分析数据已保存到 strategy_execution_data.json")

            return results

        except Exception as e:
            logger.error(f"策略执行分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """主函数"""
    analyzer = StrategyExecutionAnalyzer()
    return analyzer.run_analysis_and_save_report()


if __name__ == "__main__":
    main()
