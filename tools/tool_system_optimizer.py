#!/usr/bin/env python3
"""
HIkyuu系统优化器

自动分析和优化系统，清理冗余文件，提升性能
"""

import os
import sys
import gc
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Set
import ast
import importlib.util
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/system_optimizer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SystemOptimizer:
    """系统优化器"""

    def __init__(self, project_root: str = ".."):
        """
        初始化系统优化器

        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)
        self.optimization_report = {
            'start_time': datetime.now(),
            'cleaned_files': [],
            'optimized_files': [],
            'errors': [],
            'warnings': [],
            'statistics': {}
        }

        # 需要忽略的目录和文件
        self.ignore_patterns = {
            '__pycache__',
            '.git',
            '.pytest_cache',
            'node_modules',
            '.vscode',
            '.idea',
            '*.pyc',
            '*.pyo',
            '*.pyd',
            '.DS_Store',
            'Thumbs.db'
        }

        logger.info(f"系统优化器初始化完成，项目根目录: {self.project_root}")

    def analyze_system(self) -> Dict[str, Any]:
        """分析系统状态"""
        logger.info("开始分析系统状态...")

        analysis = {
            'total_files': 0,
            'python_files': 0,
            'duplicate_imports': [],
            'unused_imports': [],
            'large_files': [],
            'empty_files': [],
            'cache_files': [],
            'log_files': [],
            'temp_files': []
        }

        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and not self._should_ignore(file_path):
                analysis['total_files'] += 1

                # 分析Python文件
                if file_path.suffix == '.py':
                    analysis['python_files'] += 1
                    self._analyze_python_file(file_path, analysis)

                # 检查大文件
                file_size = file_path.stat().st_size
                if file_size > 10 * 1024 * 1024:  # 大于10MB
                    analysis['large_files'].append({
                        'path': str(file_path),
                        'size_mb': file_size / (1024 * 1024)
                    })

                # 检查空文件
                if file_size == 0:
                    analysis['empty_files'].append(str(file_path))

                # 检查缓存文件
                if any(pattern in str(file_path) for pattern in ['__pycache__', '.cache', '.pytest_cache']):
                    analysis['cache_files'].append(str(file_path))

                # 检查日志文件
                if file_path.suffix in ['.log', '.out'] or 'log' in file_path.name.lower():
                    analysis['log_files'].append(str(file_path))

                # 检查临时文件
                if file_path.suffix in ['.tmp', '.temp', '.bak'] or file_path.name.startswith('~'):
                    analysis['temp_files'].append(str(file_path))

        self.optimization_report['statistics'] = analysis
        logger.info(f"系统分析完成: {analysis['total_files']}个文件，{analysis['python_files']}个Python文件")
        return analysis

    def _analyze_python_file(self, file_path: Path, analysis: Dict[str, Any]):
        """分析Python文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析AST
            tree = ast.parse(content)

            # 分析导入
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")

            # 检查重复导入
            seen_imports = set()
            for imp in imports:
                if imp in seen_imports:
                    analysis['duplicate_imports'].append({
                        'file': str(file_path),
                        'import': imp
                    })
                seen_imports.add(imp)

        except Exception as e:
            logger.warning(f"分析Python文件失败 {file_path}: {e}")

    def clean_cache_files(self) -> int:
        """清理缓存文件"""
        logger.info("开始清理缓存文件...")

        cleaned_count = 0
        cache_patterns = ['__pycache__', '.pytest_cache', '.cache']

        for pattern in cache_patterns:
            for cache_dir in self.project_root.rglob(pattern):
                if cache_dir.is_dir():
                    try:
                        shutil.rmtree(cache_dir)
                        self.optimization_report['cleaned_files'].append(str(cache_dir))
                        cleaned_count += 1
                        logger.info(f"删除缓存目录: {cache_dir}")
                    except Exception as e:
                        logger.error(f"删除缓存目录失败 {cache_dir}: {e}")
                        self.optimization_report['errors'].append(str(e))

        # 清理.pyc文件
        for pyc_file in self.project_root.rglob('*.pyc'):
            try:
                pyc_file.unlink()
                self.optimization_report['cleaned_files'].append(str(pyc_file))
                cleaned_count += 1
            except Exception as e:
                logger.error(f"删除.pyc文件失败 {pyc_file}: {e}")

        logger.info(f"缓存文件清理完成，删除了 {cleaned_count} 个文件/目录")
        return cleaned_count

    def clean_temp_files(self) -> int:
        """清理临时文件"""
        logger.info("开始清理临时文件...")

        cleaned_count = 0
        temp_patterns = ['*.tmp', '*.temp', '*.bak', '~*']

        for pattern in temp_patterns:
            for temp_file in self.project_root.rglob(pattern):
                if temp_file.is_file():
                    try:
                        temp_file.unlink()
                        self.optimization_report['cleaned_files'].append(str(temp_file))
                        cleaned_count += 1
                        logger.info(f"删除临时文件: {temp_file}")
                    except Exception as e:
                        logger.error(f"删除临时文件失败 {temp_file}: {e}")
                        self.optimization_report['errors'].append(str(e))

        logger.info(f"临时文件清理完成，删除了 {cleaned_count} 个文件")
        return cleaned_count

    def optimize_imports(self) -> int:
        """优化导入语句"""
        logger.info("开始优化导入语句...")

        optimized_count = 0

        # 这里可以添加导入优化逻辑
        # 例如：移除未使用的导入、合并重复导入等

        logger.info(f"导入优化完成，优化了 {optimized_count} 个文件")
        return optimized_count

    def clean_old_logs(self, days: int = 30) -> int:
        """清理旧日志文件"""
        logger.info(f"开始清理 {days} 天前的日志文件...")

        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for log_file in self.project_root.rglob('*.log'):
            if log_file.is_file():
                try:
                    if log_file.stat().st_mtime < cutoff_time:
                        log_file.unlink()
                        self.optimization_report['cleaned_files'].append(str(log_file))
                        cleaned_count += 1
                        logger.info(f"删除旧日志文件: {log_file}")
                except Exception as e:
                    logger.error(f"删除日志文件失败 {log_file}: {e}")
                    self.optimization_report['errors'].append(str(e))

        logger.info(f"日志清理完成，删除了 {cleaned_count} 个文件")
        return cleaned_count

    def optimize_memory(self):
        """优化内存使用"""
        logger.info("开始优化内存使用...")

        # 强制垃圾回收
        collected = gc.collect()
        logger.info(f"垃圾回收完成，回收了 {collected} 个对象")

        # 获取内存使用情况
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        logger.info(f"当前内存使用: {memory_info.rss / 1024 / 1024:.2f} MB")

    def _should_ignore(self, path: Path) -> bool:
        """检查是否应该忽略文件或目录"""
        return any(pattern in str(path) for pattern in self.ignore_patterns)

    def generate_report(self) -> str:
        """生成优化报告"""
        self.optimization_report['end_time'] = datetime.now()
        duration = self.optimization_report['end_time'] - self.optimization_report['start_time']

        report = f"""
# HIkyuu系统优化报告

## 优化概览
- 开始时间: {self.optimization_report['start_time']}
- 结束时间: {self.optimization_report['end_time']}
- 耗时: {duration}

## 清理统计
- 清理文件数: {len(self.optimization_report['cleaned_files'])}
- 优化文件数: {len(self.optimization_report['optimized_files'])}
- 错误数: {len(self.optimization_report['errors'])}
- 警告数: {len(self.optimization_report['warnings'])}

## 系统统计
{self.optimization_report['statistics']}

## 清理的文件
{chr(10).join(self.optimization_report['cleaned_files'])}

## 错误列表
{chr(10).join(self.optimization_report['errors'])}
"""
        return report

    def run_full_optimization(self) -> str:
        """运行完整优化"""
        logger.info("开始完整系统优化...")

        try:
            # 分析系统
            analysis = self.analyze_system()

            # 清理缓存文件
            cache_cleaned = self.clean_cache_files()

            # 清理临时文件
            temp_cleaned = self.clean_temp_files()

            # 清理旧日志
            log_cleaned = self.clean_old_logs()

            # 优化导入
            import_optimized = self.optimize_imports()

            # 优化内存
            self.optimize_memory()

            # 生成报告
            report = self.generate_report()

            logger.info("系统优化完成")
            return report

        except Exception as e:
            logger.error(f"系统优化失败: {e}")
            self.optimization_report['errors'].append(str(e))
            return self.generate_report()


def main():
    """主函数"""
    optimizer = SystemOptimizer()
    report = optimizer.run_full_optimization()

    # 保存报告
    report_file = f"optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"优化完成，报告已保存到: {report_file}")


if __name__ == "__main__":
    main()
