"""
系统健康检查器
统一检查系统中的各种问题，包括重复功能、循环依赖、性能问题等
"""

import os
import ast
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class SystemHealthChecker:
    """系统健康检查器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = {
            'circular_imports': [],
            'duplicate_functions': [],
            'deprecated_usage': [],
            'performance_issues': [],
            'code_quality_issues': [],
            'compatibility_issues': []
        }

    def run_comprehensive_check(self) -> Dict[str, Any]:
        """运行全面的系统健康检查"""
        logger.info("开始系统健康检查...")

        # 检查循环导入
        self.check_circular_imports()

        # 检查重复函数定义
        self.check_duplicate_functions()

        # 检查弃用功能使用
        self.check_deprecated_usage()

        # 检查性能问题
        self.check_performance_issues()

        # 检查代码质量
        self.check_code_quality()

        # 生成健康报告
        return self.generate_health_report()

    def check_circular_imports(self):
        """检查循环导入"""
        import_graph = defaultdict(set)

        for py_file in self.project_root.rglob('*.py'):
            if self._should_ignore_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                file_module = self._get_module_name(py_file)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_graph[file_module].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            import_graph[file_module].add(node.module)

            except Exception as e:
                logger.warning(f"解析文件失败 {py_file}: {e}")

        # 检测循环依赖
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in import_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    self.issues['circular_imports'].append({
                        'modules': [node, neighbor],
                        'type': 'circular_dependency'
                    })
                    return True

            rec_stack.remove(node)
            return False

        for module in import_graph:
            if module not in visited:
                has_cycle(module)

    def check_duplicate_functions(self):
        """检查重复函数定义"""
        function_definitions = defaultdict(list)

        for py_file in self.project_root.rglob('*.py'):
            if self._should_ignore_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_signature = self._get_function_signature(node)
                        function_definitions[node.name].append({
                            'file': str(py_file),
                            'line': node.lineno,
                            'signature': func_signature
                        })

            except Exception as e:
                logger.warning(f"解析函数定义失败 {py_file}: {e}")

        # 找出重复的函数
        for func_name, definitions in function_definitions.items():
            if len(definitions) > 1:
                # 检查是否真的是重复（签名相似度）
                similar_definitions = []
                for i, def1 in enumerate(definitions):
                    for j, def2 in enumerate(definitions[i+1:], i+1):
                        if self._are_functions_similar(def1['signature'], def2['signature']):
                            similar_definitions.append((def1, def2))

                if similar_definitions:
                    self.issues['duplicate_functions'].append({
                        'function_name': func_name,
                        'definitions': definitions,
                        'similar_pairs': similar_definitions
                    })

    def check_deprecated_usage(self):
        """检查弃用功能的使用"""
        deprecated_patterns = [
            ('monitor_performance', 'utils.performance_monitor'),
            ('performance_monitor', 'core.performance_optimizer'),
            ('PerformanceMonitor', 'utils.performance_monitor'),
            ('ProfessionalPerformanceOptimizer', 'core.performance_optimizer')
        ]

        for py_file in self.project_root.rglob('*.py'):
            if self._should_ignore_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern, module in deprecated_patterns:
                    if pattern in content:
                        # 进一步分析是否真的在使用
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if pattern in line and not line.strip().startswith('#'):
                                self.issues['deprecated_usage'].append({
                                    'file': str(py_file),
                                    'line': i,
                                    'pattern': pattern,
                                    'module': module,
                                    'code': line.strip()
                                })

            except Exception as e:
                logger.warning(f"检查弃用功能失败 {py_file}: {e}")

    def check_performance_issues(self):
        """检查性能问题"""
        performance_patterns = [
            ('pd.DataFrame.iterrows()', 'avoid_iterrows'),
            ('time.sleep(', 'blocking_sleep'),
            ('for.*range(len(', 'inefficient_loop'),
            ('import.*\\*', 'wildcard_import')
        ]

        for py_file in self.project_root.rglob('*.py'):
            if self._should_ignore_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    for pattern, issue_type in performance_patterns:
                        import re
                        if re.search(pattern, line):
                            self.issues['performance_issues'].append({
                                'file': str(py_file),
                                'line': i,
                                'issue_type': issue_type,
                                'code': line.strip(),
                                'suggestion': self._get_performance_suggestion(issue_type)
                            })

            except Exception as e:
                logger.warning(f"检查性能问题失败 {py_file}: {e}")

    def check_code_quality(self):
        """检查代码质量问题"""
        for py_file in self.project_root.rglob('*.py'):
            if self._should_ignore_file(py_file):
                continue

            try:
                file_size = py_file.stat().st_size

                # 检查文件大小
                if file_size > 50 * 1024:  # 大于50KB
                    self.issues['code_quality_issues'].append({
                        'file': str(py_file),
                        'issue_type': 'large_file',
                        'size_kb': file_size / 1024,
                        'suggestion': '考虑拆分大文件'
                    })

                # 检查函数复杂度
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        complexity = self._calculate_complexity(node)
                        if complexity > 10:  # 复杂度阈值
                            self.issues['code_quality_issues'].append({
                                'file': str(py_file),
                                'function': node.name,
                                'line': node.lineno,
                                'issue_type': 'high_complexity',
                                'complexity': complexity,
                                'suggestion': '考虑重构复杂函数'
                            })

            except Exception as e:
                logger.warning(f"检查代码质量失败 {py_file}: {e}")

    def generate_health_report(self) -> Dict[str, Any]:
        """生成健康报告"""
        total_issues = sum(len(issues) for issues in self.issues.values())

        severity_map = {
            'circular_imports': 'critical',
            'duplicate_functions': 'high',
            'deprecated_usage': 'medium',
            'performance_issues': 'medium',
            'code_quality_issues': 'low',
            'compatibility_issues': 'medium'
        }

        health_score = max(0, 100 - total_issues * 2)  # 简单的评分算法

        report = {
            'overall_health': {
                'score': health_score,
                'status': 'healthy' if health_score >= 80 else 'needs_attention',
                'total_issues': total_issues
            },
            'issues_by_category': {
                category: {
                    'count': len(issues),
                    'severity': severity_map.get(category, 'medium'),
                    'issues': issues
                }
                for category, issues in self.issues.items()
            },
            'recommendations': self._generate_recommendations()
        }

        return report

    def _should_ignore_file(self, file_path: Path) -> bool:
        """判断是否应该忽略文件"""
        ignore_patterns = [
            '__pycache__', '.git', '.pytest_cache', 'node_modules',
            'test_', '_test', '.cache', 'migrations'
        ]

        return any(pattern in str(file_path) for pattern in ignore_patterns)

    def _get_module_name(self, file_path: Path) -> str:
        """获取模块名"""
        relative_path = file_path.relative_to(self.project_root)
        return str(relative_path).replace('/', '.').replace('\\', '.').replace('.py', '')

    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """获取函数签名"""
        args = [arg.arg for arg in node.args.args]
        return f"{node.name}({', '.join(args)})"

    def _are_functions_similar(self, sig1: str, sig2: str) -> bool:
        """判断两个函数是否相似"""
        # 简单的相似度判断，可以根据需要增强
        return sig1 == sig2

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """计算函数复杂度（简化的圈复杂度）"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _get_performance_suggestion(self, issue_type: str) -> str:
        """获取性能建议"""
        suggestions = {
            'avoid_iterrows': '使用向量化操作替代iterrows()',
            'blocking_sleep': '考虑使用异步操作或QTimer',
            'inefficient_loop': '使用enumerate()或直接迭代',
            'wildcard_import': '使用具体的导入语句'
        }
        return suggestions.get(issue_type, '请参考性能最佳实践')

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if self.issues['circular_imports']:
            recommendations.append("解决循环导入问题，重构模块依赖关系")

        if self.issues['duplicate_functions']:
            recommendations.append("合并重复的函数定义，保留功能最完整的版本")

        if self.issues['deprecated_usage']:
            recommendations.append("更新代码使用统一的性能管理器")

        if self.issues['performance_issues']:
            recommendations.append("优化性能热点，使用更高效的算法和数据结构")

        if not recommendations:
            recommendations.append("系统健康状况良好，继续保持")

        return recommendations


def run_system_health_check(project_root: str = '.') -> Dict[str, Any]:
    """运行系统健康检查"""
    checker = SystemHealthChecker(project_root)
    return checker.run_comprehensive_check()


if __name__ == '__main__':
    # 运行健康检查
    report = run_system_health_check()

    print("=" * 50)
    print("系统健康检查报告")
    print("=" * 50)
    print(f"总体健康评分: {report['overall_health']['score']}/100")
    print(f"状态: {report['overall_health']['status']}")
    print(f"总问题数: {report['overall_health']['total_issues']}")
    print()

    for category, info in report['issues_by_category'].items():
        if info['count'] > 0:
            print(f"{category}: {info['count']} 个问题 (严重程度: {info['severity']})")

    print("\n改进建议:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")
