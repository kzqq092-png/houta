#!/usr/bin/env python3
"""
并发安全性和资源管理分析器
========================

分析回测系统的并发安全性、线程安全、内存管理和资源泄漏问题
"""

import sys
import ast
import re
from loguru import logger
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Loguru配置在core.loguru_config中统一管理
logger = logger


@dataclass
class ConcurrencyIssue:
    """并发问题"""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str
    method_name: str
    file_path: str
    line_number: int
    issue_type: str
    description: str
    code_snippet: str
    recommendation: str


@dataclass
class ResourceIssue:
    """资源问题"""
    severity: str
    category: str
    method_name: str
    file_path: str
    line_number: int
    resource_type: str
    description: str
    recommendation: str


class ConcurrencyResourceAnalyzer:
    """并发和资源分析器"""

    def __init__(self):
        self.concurrency_issues = []
        self.resource_issues = []
        self.thread_safety_analysis = {}
        self.resource_usage_analysis = {}

    def analyze_concurrency_and_resources(self) -> Dict[str, Any]:
        """分析并发安全性和资源管理"""
        logger.info("开始分析并发安全性和资源管理...")

        results = {
            'thread_safety_analysis': {},
            'resource_management_analysis': {},
            'concurrency_issues': [],
            'resource_leaks': [],
            'memory_management_issues': [],
            'performance_impact': {},
            'safety_recommendations': []
        }

        try:
            # 1. 分析线程安全性
            logger.info("分析线程安全性...")
            results['thread_safety_analysis'] = self._analyze_thread_safety()

            # 2. 分析资源管理
            logger.info("分析资源管理...")
            results['resource_management_analysis'] = self._analyze_resource_management()

            # 3. 检测并发问题
            logger.info("检测并发问题...")
            results['concurrency_issues'] = self._detect_concurrency_issues()

            # 4. 检测资源泄漏
            logger.info("检测资源泄漏...")
            results['resource_leaks'] = self._detect_resource_leaks()

            # 5. 分析内存管理
            logger.info("分析内存管理...")
            results['memory_management_issues'] = self._analyze_memory_management()

            # 6. 评估性能影响
            logger.info("评估性能影响...")
            results['performance_impact'] = self._assess_performance_impact()

            # 7. 生成安全建议
            logger.info("生成安全建议...")
            results['safety_recommendations'] = self._generate_safety_recommendations()

            logger.info("并发和资源分析完成")
            return results

        except Exception as e:
            logger.error(f"并发和资源分析失败: {e}")
            import traceback
            traceback.print_exc()
            return results

    def _analyze_thread_safety(self) -> Dict[str, Any]:
        """分析线程安全性"""
        thread_safety = {
            'shared_variables': [],
            'thread_unsafe_operations': [],
            'synchronization_mechanisms': [],
            'race_condition_risks': [],
            'thread_safety_score': 0
        }

        # 分析主要文件
        target_files = [
            'backtest/unified_backtest_engine.py',
            'backtest/real_time_backtest_monitor.py',
            'core/metrics/repository.py',
            'gui/widgets/backtest_widget.py'
        ]

        for file_path in target_files:
            full_path = project_root / file_path
            if full_path.exists():
                file_analysis = self._analyze_file_thread_safety(full_path)
                thread_safety['shared_variables'].extend(file_analysis['shared_vars'])
                thread_safety['thread_unsafe_operations'].extend(file_analysis['unsafe_ops'])
                thread_safety['synchronization_mechanisms'].extend(file_analysis['sync_mechanisms'])
                thread_safety['race_condition_risks'].extend(file_analysis['race_risks'])

        # 计算线程安全评分
        total_issues = (len(thread_safety['thread_unsafe_operations']) +
                        len(thread_safety['race_condition_risks']))
        sync_mechanisms = len(thread_safety['synchronization_mechanisms'])

        if total_issues == 0:
            thread_safety['thread_safety_score'] = 100
        else:
            # 基础分数减去问题分数，加上同步机制分数
            thread_safety['thread_safety_score'] = max(0, 100 - (total_issues * 10) + (sync_mechanisms * 5))

        return thread_safety

    def _analyze_file_thread_safety(self, file_path: Path) -> Dict[str, Any]:
        """分析文件的线程安全性"""
        analysis = {
            'shared_vars': [],
            'unsafe_ops': [],
            'sync_mechanisms': [],
            'race_risks': []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.splitlines()

            # 检查共享变量
            class_vars = []
            in_class = False
            current_class = ""

            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()

                # 检测类定义
                if line_stripped.startswith('class '):
                    in_class = True
                    current_class = line_stripped.split()[1].split('(')[0]
                elif line_stripped.startswith('def ') and in_class:
                    in_class = False

                # 检测共享变量
                if in_class and '=' in line_stripped and not line_stripped.startswith('def'):
                    if not line_stripped.startswith('#'):
                        var_name = line_stripped.split('=')[0].strip()
                        if not var_name.startswith('_'):  # 公共变量
                            analysis['shared_vars'].append({
                                'variable': var_name,
                                'class': current_class,
                                'file': str(file_path),
                                'line': i
                            })

                # 检测线程不安全操作
                unsafe_patterns = [
                    'append(', 'extend(', 'pop(', 'remove(',  # 列表操作
                    '+=', '-=', '*=', '/=',  # 原地操作
                    'dict[', 'dict.update(',  # 字典操作
                    'global ', 'nonlocal '  # 全局变量
                ]

                for pattern in unsafe_patterns:
                    if pattern in line_stripped:
                        analysis['unsafe_ops'].append({
                            'operation': pattern,
                            'file': str(file_path),
                            'line': i,
                            'code': line_stripped
                        })

                # 检测同步机制
                sync_patterns = [
                    'threading.Lock()', 'threading.RLock()',
                    'threading.Semaphore()', 'threading.Event()',
                    'with.*lock:', 'acquire()', 'release()',
                    'queue.Queue()', 'multiprocessing.'
                ]

                for pattern in sync_patterns:
                    if re.search(pattern, line_stripped, re.IGNORECASE):
                        analysis['sync_mechanisms'].append({
                            'mechanism': pattern,
                            'file': str(file_path),
                            'line': i,
                            'code': line_stripped
                        })

                # 检测竞态条件风险
                race_patterns = [
                    r'if.*len\(.*\).*:',  # 检查长度后操作
                    r'if.*in.*:',  # 检查存在后操作
                    r'if.*is None:',  # 检查None后操作
                ]

                for pattern in race_patterns:
                    if re.search(pattern, line_stripped):
                        # 检查下一行是否有修改操作
                        if i < len(lines):
                            next_line = lines[i].strip()
                            if any(op in next_line for op in ['=', 'append', 'pop', 'del ']):
                                analysis['race_risks'].append({
                                    'risk_type': 'check_then_act',
                                    'file': str(file_path),
                                    'line': i,
                                    'code': f"{line_stripped} -> {next_line}"
                                })

        except Exception as e:
            logger.error(f"分析文件线程安全性失败 {file_path}: {e}")

        return analysis

    def _analyze_resource_management(self) -> Dict[str, Any]:
        """分析资源管理"""
        resource_analysis = {
            'file_operations': [],
            'database_connections': [],
            'memory_allocations': [],
            'network_connections': [],
            'resource_cleanup': [],
            'context_managers': [],
            'resource_management_score': 0
        }

        # 分析资源管理相关文件
        target_files = [
            'backtest/unified_backtest_engine.py',
            'core/metrics/repository.py',
            'core/database/factorweave_analytics_db.py',
            'gui/widgets/backtest_widget.py'
        ]

        for file_path in target_files:
            full_path = project_root / file_path
            if full_path.exists():
                file_analysis = self._analyze_file_resources(full_path)
                resource_analysis['file_operations'].extend(file_analysis['file_ops'])
                resource_analysis['database_connections'].extend(file_analysis['db_connections'])
                resource_analysis['memory_allocations'].extend(file_analysis['memory_allocs'])
                resource_analysis['resource_cleanup'].extend(file_analysis['cleanup'])
                resource_analysis['context_managers'].extend(file_analysis['context_mgrs'])

        # 计算资源管理评分
        total_resources = (len(resource_analysis['file_operations']) +
                           len(resource_analysis['database_connections']) +
                           len(resource_analysis['memory_allocations']))

        cleanup_mechanisms = (len(resource_analysis['resource_cleanup']) +
                              len(resource_analysis['context_managers']))

        if total_resources == 0:
            resource_analysis['resource_management_score'] = 100
        else:
            # 清理机制覆盖率
            coverage = min(100, (cleanup_mechanisms / total_resources) * 100)
            resource_analysis['resource_management_score'] = int(coverage)

        return resource_analysis

    def _analyze_file_resources(self, file_path: Path) -> Dict[str, Any]:
        """分析文件的资源使用"""
        analysis = {
            'file_ops': [],
            'db_connections': [],
            'memory_allocs': [],
            'cleanup': [],
            'context_mgrs': []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()

                # 检测文件操作
                file_patterns = ['open(', 'file(', 'codecs.open(', 'io.open(']
                for pattern in file_patterns:
                    if pattern in line_stripped:
                        analysis['file_ops'].append({
                            'operation': pattern,
                            'file': str(file_path),
                            'line': i,
                            'code': line_stripped
                        })

                # 检测数据库连接
                db_patterns = ['connect(', 'sqlite3.', 'duckdb.', 'cursor()', 'execute(']
                for pattern in db_patterns:
                    if pattern in line_stripped:
                        analysis['db_connections'].append({
                            'operation': pattern,
                            'file': str(file_path),
                            'line': i,
                            'code': line_stripped
                        })

                # 检测大内存分配
                memory_patterns = ['pandas.', 'numpy.', 'DataFrame(', 'array(', 'zeros(', 'ones(']
                for pattern in memory_patterns:
                    if pattern in line_stripped:
                        analysis['memory_allocs'].append({
                            'operation': pattern,
                            'file': str(file_path),
                            'line': i,
                            'code': line_stripped
                        })

                # 检测资源清理
                cleanup_patterns = ['close()', 'commit()', 'rollback()', 'finally:', 'del ', '__del__']
                for pattern in cleanup_patterns:
                    if pattern in line_stripped:
                        analysis['cleanup'].append({
                            'cleanup_type': pattern,
                            'file': str(file_path),
                            'line': i,
                            'code': line_stripped
                        })

                # 检测上下文管理器
                if 'with ' in line_stripped and ':' in line_stripped:
                    analysis['context_mgrs'].append({
                        'context_manager': 'with statement',
                        'file': str(file_path),
                        'line': i,
                        'code': line_stripped
                    })

        except Exception as e:
            logger.error(f"分析文件资源使用失败 {file_path}: {e}")

        return analysis

    def _detect_concurrency_issues(self) -> List[Dict[str, Any]]:
        """检测并发问题"""
        issues = []

        # 基于线程安全分析结果检测问题
        thread_analysis = self.thread_safety_analysis

        # 检测共享变量无保护访问
        for var in thread_analysis.get('shared_variables', []):
            issues.append({
                'severity': 'HIGH',
                'category': '线程安全',
                'issue_type': 'unprotected_shared_variable',
                'description': f"共享变量 {var['variable']} 可能存在并发访问风险",
                'file': var['file'],
                'line': var['line'],
                'recommendation': '使用锁或其他同步机制保护共享变量访问'
            })

        # 检测线程不安全操作
        for op in thread_analysis.get('thread_unsafe_operations', []):
            issues.append({
                'severity': 'MEDIUM',
                'category': '线程安全',
                'issue_type': 'thread_unsafe_operation',
                'description': f"线程不安全操作: {op['operation']}",
                'file': op['file'],
                'line': op['line'],
                'code': op['code'],
                'recommendation': '在多线程环境中使用线程安全的替代方案'
            })

        # 检测竞态条件
        for risk in thread_analysis.get('race_condition_risks', []):
            issues.append({
                'severity': 'HIGH',
                'category': '竞态条件',
                'issue_type': 'race_condition',
                'description': f"潜在竞态条件: {risk['risk_type']}",
                'file': risk['file'],
                'line': risk['line'],
                'code': risk['code'],
                'recommendation': '使用原子操作或适当的同步机制'
            })

        return issues

    def _detect_resource_leaks(self) -> List[Dict[str, Any]]:
        """检测资源泄漏"""
        leaks = []

        resource_analysis = self.resource_usage_analysis

        # 检测文件未关闭
        file_ops = resource_analysis.get('file_operations', [])
        cleanup_ops = resource_analysis.get('resource_cleanup', [])

        file_lines = {op['line'] for op in file_ops}
        close_lines = {op['line'] for op in cleanup_ops if 'close' in op.get('cleanup_type', '')}

        for file_op in file_ops:
            # 简单检查：如果文件操作附近没有close操作
            nearby_closes = any(abs(file_op['line'] - close_line) < 20 for close_line in close_lines)
            if not nearby_closes:
                leaks.append({
                    'severity': 'MEDIUM',
                    'category': '资源泄漏',
                    'resource_type': 'file',
                    'description': '文件可能未正确关闭',
                    'file': file_op['file'],
                    'line': file_op['line'],
                    'recommendation': '使用 with 语句或确保在 finally 块中关闭文件'
                })

        # 检测数据库连接未关闭
        db_connections = resource_analysis.get('database_connections', [])
        for db_op in db_connections:
            if 'connect' in db_op['operation']:
                # 检查是否有对应的关闭操作
                nearby_closes = any(abs(db_op['line'] - close_line) < 30 for close_line in close_lines)
                if not nearby_closes:
                    leaks.append({
                        'severity': 'HIGH',
                        'category': '资源泄漏',
                        'resource_type': 'database_connection',
                        'description': '数据库连接可能未正确关闭',
                        'file': db_op['file'],
                        'line': db_op['line'],
                        'recommendation': '使用上下文管理器或确保连接在使用后关闭'
                    })

        return leaks

    def _analyze_memory_management(self) -> List[Dict[str, Any]]:
        """分析内存管理问题"""
        memory_issues = []

        # 分析大对象创建和内存使用
        target_files = [
            'backtest/unified_backtest_engine.py',
            'core/metrics/repository.py'
        ]

        for file_path in target_files:
            full_path = project_root / file_path
            if full_path.exists():
                file_issues = self._analyze_file_memory(full_path)
                memory_issues.extend(file_issues)

        return memory_issues

    def _analyze_file_memory(self, file_path: Path) -> List[Dict[str, Any]]:
        """分析文件的内存使用"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()

                # 检测大数据结构创建
                large_data_patterns = [
                    'pd.DataFrame(',
                    'np.array(',
                    'np.zeros(',
                    'np.ones(',
                    'list(' + '.*' + 'range(',
                    'dict(' + '.*' + 'zip('
                ]

                for pattern in large_data_patterns:
                    if re.search(pattern, line_stripped):
                        issues.append({
                            'severity': 'MEDIUM',
                            'category': '内存管理',
                            'issue_type': 'large_object_creation',
                            'description': f'创建大数据结构: {pattern}',
                            'file': str(file_path),
                            'line': i,
                            'recommendation': '考虑使用生成器或分批处理大数据'
                        })

                # 检测内存泄漏风险
                if 'global ' in line_stripped or 'self.' in line_stripped:
                    if any(keyword in line_stripped for keyword in ['list', 'dict', 'DataFrame']):
                        issues.append({
                            'severity': 'LOW',
                            'category': '内存管理',
                            'issue_type': 'potential_memory_leak',
                            'description': '全局或实例变量可能导致内存泄漏',
                            'file': str(file_path),
                            'line': i,
                            'recommendation': '定期清理不需要的数据，使用弱引用'
                        })

        except Exception as e:
            logger.error(f"分析文件内存使用失败 {file_path}: {e}")

        return issues

    def _assess_performance_impact(self) -> Dict[str, Any]:
        """评估性能影响"""
        impact = {
            'thread_safety_impact': 'LOW',
            'resource_management_impact': 'MEDIUM',
            'memory_impact': 'MEDIUM',
            'overall_impact': 'MEDIUM',
            'bottleneck_areas': []
        }

        # 基于发现的问题评估影响
        concurrency_issues = len(self.concurrency_issues)
        resource_leaks = len(self.resource_issues)

        if concurrency_issues > 10:
            impact['thread_safety_impact'] = 'HIGH'
        elif concurrency_issues > 5:
            impact['thread_safety_impact'] = 'MEDIUM'

        if resource_leaks > 5:
            impact['resource_management_impact'] = 'HIGH'
        elif resource_leaks > 2:
            impact['resource_management_impact'] = 'MEDIUM'

        # 识别瓶颈区域
        if concurrency_issues > 0:
            impact['bottleneck_areas'].append('并发控制')

        if resource_leaks > 0:
            impact['bottleneck_areas'].append('资源管理')

        # 计算总体影响
        high_impacts = sum(1 for imp in [impact['thread_safety_impact'],
                                         impact['resource_management_impact'],
                                         impact['memory_impact']] if imp == 'HIGH')

        if high_impacts >= 2:
            impact['overall_impact'] = 'HIGH'
        elif high_impacts >= 1:
            impact['overall_impact'] = 'MEDIUM'
        else:
            impact['overall_impact'] = 'LOW'

        return impact

    def _generate_safety_recommendations(self) -> List[Dict[str, Any]]:
        """生成安全建议"""
        recommendations = [
            {
                'category': '线程安全',
                'priority': 'HIGH',
                'title': '实现线程安全机制',
                'description': '为共享资源添加适当的同步机制',
                'implementation': [
                    '识别所有共享变量和资源',
                    '使用 threading.Lock() 保护关键区域',
                    '考虑使用线程安全的数据结构',
                    '实现原子操作避免竞态条件'
                ],
                'benefits': ['避免数据竞争', '确保数据一致性', '提高系统稳定性']
            },
            {
                'category': '资源管理',
                'priority': 'HIGH',
                'title': '完善资源清理机制',
                'description': '确保所有资源都能正确释放',
                'implementation': [
                    '使用上下文管理器 (with 语句)',
                    '在 finally 块中释放资源',
                    '实现 __del__ 方法作为备用清理',
                    '定期检查资源使用情况'
                ],
                'benefits': ['防止资源泄漏', '提高系统性能', '避免系统崩溃']
            },
            {
                'category': '内存管理',
                'priority': 'MEDIUM',
                'title': '优化内存使用',
                'description': '减少内存占用和避免内存泄漏',
                'implementation': [
                    '使用生成器处理大数据集',
                    '及时清理不需要的变量',
                    '使用弱引用避免循环引用',
                    '监控内存使用情况'
                ],
                'benefits': ['降低内存占用', '提高运行效率', '避免内存溢出']
            },
            {
                'category': '并发控制',
                'priority': 'MEDIUM',
                'title': '改进并发设计',
                'description': '优化多线程和异步处理',
                'implementation': [
                    '使用线程池管理线程',
                    '实现异步I/O操作',
                    '避免过度并发',
                    '使用队列进行线程间通信'
                ],
                'benefits': ['提高并发性能', '减少资源竞争', '提高响应速度']
            }
        ]

        return recommendations

    def generate_concurrency_resource_report(self, results: Dict[str, Any]) -> str:
        """生成并发和资源分析报告"""
        report = []
        report.append("# 并发安全性和资源管理分析报告")
        report.append("=" * 80)

        # 执行摘要
        report.append(f"\n##  执行摘要")

        thread_safety = results.get('thread_safety_analysis', {})
        resource_mgmt = results.get('resource_management_analysis', {})
        concurrency_issues = results.get('concurrency_issues', [])
        resource_leaks = results.get('resource_leaks', [])
        memory_issues = results.get('memory_management_issues', [])
        performance_impact = results.get('performance_impact', {})

        report.append(f"- 线程安全评分: {thread_safety.get('thread_safety_score', 0)}/100")
        report.append(f"- 资源管理评分: {resource_mgmt.get('resource_management_score', 0)}/100")
        report.append(f"- 并发问题数量: {len(concurrency_issues)}")
        report.append(f"- 资源泄漏风险: {len(resource_leaks)}")
        report.append(f"- 内存管理问题: {len(memory_issues)}")
        report.append(f"- 总体性能影响: {performance_impact.get('overall_impact', 'UNKNOWN')}")

        # 线程安全分析
        if thread_safety:
            report.append(f"\n##  线程安全分析")

            shared_vars = thread_safety.get('shared_variables', [])
            if shared_vars:
                report.append(f"\n### 共享变量 ({len(shared_vars)} 个)")
                for i, var in enumerate(shared_vars[:10], 1):
                    report.append(f"{i}. **{var['variable']}** (类: {var['class']})")
                    report.append(f"   - 文件: {Path(var['file']).name}:{var['line']}")

            unsafe_ops = thread_safety.get('thread_unsafe_operations', [])
            if unsafe_ops:
                report.append(f"\n### 线程不安全操作 ({len(unsafe_ops)} 个)")
                for i, op in enumerate(unsafe_ops[:10], 1):
                    report.append(f"{i}. **{op['operation']}** ({Path(op['file']).name}:{op['line']})")
                    report.append(f"   - 代码: `{op['code']}`")

            sync_mechanisms = thread_safety.get('synchronization_mechanisms', [])
            if sync_mechanisms:
                report.append(f"\n### 同步机制 ({len(sync_mechanisms)} 个)")
                for i, sync in enumerate(sync_mechanisms[:5], 1):
                    report.append(f"{i}. **{sync['mechanism']}** ({Path(sync['file']).name}:{sync['line']})")

        # 资源管理分析
        if resource_mgmt:
            report.append(f"\n##  资源管理分析")

            file_ops = resource_mgmt.get('file_operations', [])
            if file_ops:
                report.append(f"\n### 文件操作 ({len(file_ops)} 个)")
                for i, op in enumerate(file_ops[:5], 1):
                    report.append(f"{i}. **{op['operation']}** ({Path(op['file']).name}:{op['line']})")

            db_connections = resource_mgmt.get('database_connections', [])
            if db_connections:
                report.append(f"\n### 数据库连接 ({len(db_connections)} 个)")
                for i, conn in enumerate(db_connections[:5], 1):
                    report.append(f"{i}. **{conn['operation']}** ({Path(conn['file']).name}:{conn['line']})")

            context_mgrs = resource_mgmt.get('context_managers', [])
            if context_mgrs:
                report.append(f"\n### 上下文管理器 ({len(context_mgrs)} 个)")
                report.append(f" 发现 {len(context_mgrs)} 个上下文管理器，有助于资源管理")

        # 并发问题
        if concurrency_issues:
            report.append(f"\n##  并发问题")

            # 按严重程度分组
            high_issues = [issue for issue in concurrency_issues if issue.get('severity') == 'HIGH']
            medium_issues = [issue for issue in concurrency_issues if issue.get('severity') == 'MEDIUM']

            if high_issues:
                report.append(f"\n###  高严重性问题")
                for i, issue in enumerate(high_issues[:10], 1):
                    report.append(f"{i}. **{issue['issue_type']}** ({Path(issue['file']).name}:{issue['line']})")
                    report.append(f"   - 描述: {issue['description']}")
                    report.append(f"   - 建议: {issue['recommendation']}")

            if medium_issues:
                report.append(f"\n###  中严重性问题")
                for i, issue in enumerate(medium_issues[:5], 1):
                    report.append(f"{i}. **{issue['issue_type']}** ({Path(issue['file']).name}:{issue['line']})")
                    report.append(f"   - 描述: {issue['description']}")

        # 资源泄漏
        if resource_leaks:
            report.append(f"\n##  资源泄漏风险")

            for i, leak in enumerate(resource_leaks[:10], 1):
                report.append(f"{i}. **{leak['resource_type']}** ({Path(leak['file']).name}:{leak['line']})")
                report.append(f"   - 描述: {leak['description']}")
                report.append(f"   - 建议: {leak['recommendation']}")

        # 内存管理问题
        if memory_issues:
            report.append(f"\n##  内存管理问题")

            for i, issue in enumerate(memory_issues[:10], 1):
                report.append(f"{i}. **{issue['issue_type']}** ({Path(issue['file']).name}:{issue['line']})")
                report.append(f"   - 描述: {issue['description']}")
                report.append(f"   - 建议: {issue['recommendation']}")

        # 性能影响评估
        if performance_impact:
            report.append(f"\n##  性能影响评估")
            report.append(f"- 线程安全影响: {performance_impact.get('thread_safety_impact', 'UNKNOWN')}")
            report.append(f"- 资源管理影响: {performance_impact.get('resource_management_impact', 'UNKNOWN')}")
            report.append(f"- 内存影响: {performance_impact.get('memory_impact', 'UNKNOWN')}")
            report.append(f"- 总体影响: {performance_impact.get('overall_impact', 'UNKNOWN')}")

            bottlenecks = performance_impact.get('bottleneck_areas', [])
            if bottlenecks:
                report.append(f"\n### 瓶颈区域")
                for bottleneck in bottlenecks:
                    report.append(f"- {bottleneck}")

        # 安全建议
        safety_recommendations = results.get('safety_recommendations', [])
        if safety_recommendations:
            report.append(f"\n##  安全建议")

            for rec in safety_recommendations:
                report.append(f"\n### {rec['priority']} - {rec['title']}")
                report.append(f"**类别**: {rec['category']}")
                report.append(f"**描述**: {rec['description']}")

                if rec.get('implementation'):
                    report.append("**实施步骤**:")
                    for step in rec['implementation']:
                        report.append(f"- {step}")

                if rec.get('benefits'):
                    report.append("**预期收益**:")
                    for benefit in rec['benefits']:
                        report.append(f"- {benefit}")

        return "\n".join(report)

    def run_analysis_and_save_report(self):
        """运行分析并保存报告"""
        try:
            # 运行并发和资源分析
            results = self.analyze_concurrency_and_resources()

            # 保存分析结果到实例变量
            self.thread_safety_analysis = results.get('thread_safety_analysis', {})
            self.resource_usage_analysis = results.get('resource_management_analysis', {})
            self.concurrency_issues = results.get('concurrency_issues', [])
            self.resource_issues = results.get('resource_leaks', [])

            # 生成报告
            report = self.generate_concurrency_resource_report(results)

            # 保存报告
            with open('concurrency_resource_analysis.md', 'w', encoding='utf-8') as f:
                f.write(report)

            # 保存原始数据
            with open('concurrency_resource_data.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

            # 显示摘要
            logger.info("\n" + "="*80)
            logger.info("并发安全性和资源管理分析结果")
            logger.info("="*80)

            thread_safety = results.get('thread_safety_analysis', {})
            resource_mgmt = results.get('resource_management_analysis', {})
            concurrency_issues = results.get('concurrency_issues', [])
            resource_leaks = results.get('resource_leaks', [])
            memory_issues = results.get('memory_management_issues', [])
            performance_impact = results.get('performance_impact', {})

            logger.info(f" 分析结果:")
            logger.info(f"   线程安全评分: {thread_safety.get('thread_safety_score', 0)}/100")
            logger.info(f"   资源管理评分: {resource_mgmt.get('resource_management_score', 0)}/100")
            logger.info(f"   并发问题: {len(concurrency_issues)} 个")
            logger.info(f"   资源泄漏风险: {len(resource_leaks)} 个")
            logger.info(f"   内存管理问题: {len(memory_issues)} 个")

            logger.info(f"\n 性能影响: {performance_impact.get('overall_impact', 'UNKNOWN')}")

            bottlenecks = performance_impact.get('bottleneck_areas', [])
            if bottlenecks:
                logger.info(f"\n 瓶颈区域:")
                for bottleneck in bottlenecks:
                    logger.info(f"   - {bottleneck}")

            logger.info("并发和资源分析报告已保存到 concurrency_resource_analysis.md")
            logger.info("原始分析数据已保存到 concurrency_resource_data.json")

            return results

        except Exception as e:
            logger.error(f"并发和资源分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """主函数"""
    analyzer = ConcurrencyResourceAnalyzer()
    return analyzer.run_analysis_and_save_report()


if __name__ == "__main__":
    main()
