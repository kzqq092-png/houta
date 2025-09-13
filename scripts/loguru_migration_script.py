#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯Loguru迁移脚本
批量替换print语句和logging调用为纯Loguru接口
"""

import os
import re
import ast
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Set
import shutil
from datetime import datetime

class LoguruMigrationTool:
    """Loguru迁移工具"""
    
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.backup_dir = self.project_root / "backup_loguru_migration"
        
        # 统计信息
        self.stats = {
            "files_processed": 0,
            "print_statements_found": 0,
            "print_statements_replaced": 0,
            "logging_calls_found": 0,
            "logging_calls_replaced": 0,
            "imports_added": 0,
            "errors": []
        }
        
        # 需要替换的模式
        self.print_patterns = [
            r'\bprint\s*\(',
            r'print\s*\(',
        ]
        
        self.logging_patterns = [
            r'logging\.getLogger\s*\(',
            r'logger\s*=\s*logging\.getLogger',
            r'\.info\s*\(',
            r'\.debug\s*\(',
            r'\.warning\s*\(',
            r'\.warn\s*\(',
            r'\.error\s*\(',
            r'\.critical\s*\(',
            r'\.exception\s*\(',
        ]
        
        # 排除的文件和目录
        self.exclude_patterns = [
            '__pycache__',
            '.git',
            '.vscode',
            'node_modules',
            'backup_*',
            '*.pyc',
            '*.pyo',
            'logs',
            'cache',
            'temp',
            'scripts/loguru_migration_script.py'  # 排除自己
        ]
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """检查是否应该排除文件"""
        file_str = str(file_path)
        
        for pattern in self.exclude_patterns:
            if pattern in file_str:
                return True
        
        return False
    
    def find_python_files(self) -> List[Path]:
        """查找所有Python文件"""
        python_files = []
        
        for file_path in self.project_root.rglob("*.py"):
            if not self.should_exclude_file(file_path):
                python_files.append(file_path)
        
        return python_files
    
    def backup_file(self, file_path: Path):
        """备份文件"""
        if not self.dry_run:
            relative_path = file_path.relative_to(self.project_root)
            backup_path = self.backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
    
    def analyze_file(self, file_path: Path) -> Dict[str, any]:
        """分析文件中的print和logging使用情况"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                "file_path": file_path,
                "print_statements": [],
                "logging_calls": [],
                "has_logging_import": False,
                "has_loguru_import": False,
                "needs_migration": False
            }
            
            lines = content.split('\n')
            
            # 查找print语句
            for i, line in enumerate(lines, 1):
                for pattern in self.print_patterns:
                    if re.search(pattern, line):
                        analysis["print_statements"].append({
                            "line_number": i,
                            "content": line.strip(),
                            "pattern": pattern
                        })
                        self.stats["print_statements_found"] += 1
            
            # 查找logging调用
            for i, line in enumerate(lines, 1):
                for pattern in self.logging_patterns:
                    if re.search(pattern, line):
                        analysis["logging_calls"].append({
                            "line_number": i,
                            "content": line.strip(),
                            "pattern": pattern
                        })
                        self.stats["logging_calls_found"] += 1
            
            # 检查导入
            if re.search(r'import logging', content) or re.search(r'from logging', content):
                analysis["has_logging_import"] = True
            
            if re.search(r'from loguru import', content) or re.search(r'import loguru', content):
                analysis["has_loguru_import"] = True
            
            # 判断是否需要迁移
            if (analysis["print_statements"] or 
                analysis["logging_calls"] or 
                analysis["has_logging_import"]):
                analysis["needs_migration"] = True
            
            return analysis
            
        except Exception as e:
            self.stats["errors"].append(f"分析文件失败 {file_path}: {e}")
            return None
    
    def replace_print_statements(self, content: str) -> str:
        """替换print语句"""
        
        # 简单的print()替换
        content = re.sub(
            r'\bprint\s*\(\s*\)',
            'logger.info("")',
            content
        )
        
        # logger.info(message)替换
        content = re.sub(
            r'\bprint\s*\(\s*([^,)]+)\s*\)',
            r'logger.info(\1)',
            content
        )
        
        # logger.info(f"{message message2 ...}")替换
        content = re.sub(
            r'\bprint\s*\(\s*([^)]+)\s*\)',
            lambda m: f'logger.info({self._convert_print_args(m.group(1))})',
            content
        )
        
        return content
    
    def _convert_print_args(self, args_str: str) -> str:
        """转换print参数"""
        # 简单处理：将多个参数用f-string或字符串连接
        args = [arg.strip() for arg in args_str.split(',')]
        
        if len(args) == 1:
            return args[0]
        
        # 尝试创建f-string
        if all(not arg.startswith('"') and not arg.startswith("'") for arg in args):
            return f'f"{{{" ".join(args)}}}"'
        else:
            return f'" ".join([str({arg}) for arg in [{args_str}]])'
    
    def replace_logging_calls(self, content: str) -> str:
        """替换logging调用"""
        
        # 替换logger
        content = re.sub(
            r'logging\.getLogger\s*\([^)]*\)',
            'logger',
            content
        )
        
        # 替换logger = logger
        content = re.sub(
            r'(\w+)\s*=\s*logging\.getLogger\s*\([^)]*\)',
            r'\1 = logger',
            content
        )
        
        # 替换日志级别调用（保持不变，只是从标准logging转为loguru）
        # logger.info() -> logger.info() (loguru的logger)
        
        return content
    
    def add_loguru_import(self, content: str) -> str:
        """添加Loguru导入"""
        lines = content.split('\n')
        
        # 查找合适的导入位置
        import_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                import_index = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                break
        
        # 检查是否已有loguru导入
        has_loguru = any('from loguru import logger' in line for line in lines)
        
        if not has_loguru:
            lines.insert(import_index, loguru_import)
            self.stats["imports_added"] += 1
        
        return '\n'.join(lines)
    
    def remove_logging_imports(self, content: str) -> str:
        """移除logging导入"""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 跳过标准logging导入
            if (stripped.startswith('import logging') or
                stripped.startswith('from logging import') or
                stripped == 'import logging'):
                continue
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def migrate_file(self, file_path: Path, analysis: Dict[str, any]) -> bool:
        """迁移单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            
            # 备份原文件
            self.backup_file(file_path)
            
            # 添加Loguru导入
            content = self.add_loguru_import(content)
            
            # 替换print语句
            if analysis["print_statements"]:
                content = self.replace_print_statements(content)
                self.stats["print_statements_replaced"] += len(analysis["print_statements"])
            
            # 替换logging调用
            if analysis["logging_calls"]:
                content = self.replace_logging_calls(content)
                self.stats["logging_calls_replaced"] += len(analysis["logging_calls"])
            
            # 移除logging导入
            if analysis["has_logging_import"]:
                content = self.remove_logging_imports(content)
            
            # 写入修改后的内容
            if not self.dry_run and content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return True
            
        except Exception as e:
            self.stats["errors"].append(f"迁移文件失败 {file_path}: {e}")
            return False
    
    def run_migration(self):
        """运行迁移"""
        logger.info("开始纯Loguru迁移...")
        logger.info(f"项目目录: {self.project_root}")
        logger.info(f"模式: {'预览模式' if self.dry_run else '实际迁移模式'}")
        logger.info("")
        
        # 创建备份目录
        if not self.dry_run:
            self.backup_dir.mkdir(exist_ok=True)
            logger.info(f"备份目录: {self.backup_dir}")
        
        # 查找Python文件
        python_files = self.find_python_files()
        logger.info(f"找到 {len(python_files)} 个Python文件")
        logger.info("")
        
        # 分析和迁移文件
        for file_path in python_files:
            logger.info(f"分析: {file_path.relative_to(self.project_root)}")
            
            analysis = self.analyze_file(file_path)
            if not analysis:
                continue
            
            self.stats["files_processed"] += 1
            
            if analysis["needs_migration"]:
                logger.info(f"  需要迁移:")
                if analysis["print_statements"]:
                    logger.info(f"     Print语句: {len(analysis['print_statements'])}个")
                if analysis["logging_calls"]:
                    logger.info(f"     Logging调用: {len(analysis['logging_calls'])}个")
                
                if not self.dry_run:
                    success = self.migrate_file(file_path, analysis)
                    if success:
                        logger.info(f"  迁移完成")
                    else:
                        logger.info(f"  迁移失败")
                else:
                    logger.info(f"  预览模式 - 未实际修改")
            else:
                logger.info(f"  无需迁移")
            
            logger.info("")
    
    def print_summary(self):
        """打印迁移摘要"""
        logger.info("=" * 60)
        logger.info("迁移摘要")
        logger.info("=" * 60)
        logger.info(f"处理文件数: {self.stats['files_processed']}")
        logger.info(f"找到Print语句: {self.stats['print_statements_found']}")
        logger.info(f"替换Print语句: {self.stats['print_statements_replaced']}")
        logger.info(f"找到Logging调用: {self.stats['logging_calls_found']}")
        logger.info(f"替换Logging调用: {self.stats['logging_calls_replaced']}")
        logger.info(f"添加导入: {self.stats['imports_added']}")
        
        if self.stats["errors"]:
            logger.info(f"错误数: {len(self.stats['errors'])}")
            for error in self.stats["errors"]:
                logger.info(f"   {error}")
        
        logger.info("")
        if self.dry_run:
            logger.info("这是预览模式，没有实际修改文件")
            logger.info("要执行实际迁移，请使用 --execute 参数")
        else:
            logger.info("迁移完成!")
            logger.info(f"备份文件保存在: {self.backup_dir}")

def main():
    parser = argparse.ArgumentParser(description="纯Loguru迁移脚本")
    parser.add_argument("--project-root", "-p", default=".", help="项目根目录")
    parser.add_argument("--execute", "-e", action="store_true", help="执行实际迁移（默认为预览模式）")
    parser.add_argument("--backup-dir", "-b", help="备份目录（可选）")
    
    args = parser.parse_args()
    
    # 初始化迁移工具
    migration_tool = LoguruMigrationTool(
        project_root=args.project_root,
        dry_run=not args.execute
    )
    
    if args.backup_dir:
        migration_tool.backup_dir = Path(args.backup_dir)
    
    # 运行迁移
    try:
        migration_tool.run_migration()
        migration_tool.print_summary()
    except KeyboardInterrupt:
        logger.info("\n迁移已取消")
    except Exception as e:
        logger.info(f"\n迁移过程中发生错误: {e}")

if __name__ == "__main__":
    main()