#!/usr/bin/env python3
"""
HIkyuu-UI 重构后无效代码清理脚本
使用各种MCP工具进行全面的代码清理
"""

import os
import shutil
import glob
from pathlib import Path
from typing import List, Dict, Set
import json
import re
from datetime import datetime


class CodeCleanupManager:
    """代码清理管理器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_files: List[Path] = []
        self.temp_files: List[Path] = []
        self.duplicate_files: List[Path] = []
        self.cleanup_stats = {
            'backup_files_removed': 0,
            'temp_files_removed': 0,
            'duplicate_files_removed': 0,
            'space_saved_mb': 0
        }

    def scan_backup_files(self) -> List[Path]:
        """扫描所有备份文件"""
        print("🔍 扫描备份文件...")

        backup_patterns = [
            "**/*.backup",
            "**/*.backup2",
            "**/*.backup3",
            "**/config/app_config.json.backup.*"
        ]

        backup_files = []
        for pattern in backup_patterns:
            files = list(self.project_root.glob(pattern))
            backup_files.extend(files)

        self.backup_files = backup_files
        print(f"   找到 {len(backup_files)} 个备份文件")

        return backup_files

    def scan_temp_files(self) -> List[Path]:
        """扫描临时文件和报告文件"""
        print("🔍 扫描临时文件...")

        temp_patterns = [
            "**/architecture_diagnosis_report_*.md",
            "**/startup_log.txt",
            "**/startup_error.txt",
            "**/*_report_*.txt",
            "**/*_report_*.md",
            "**/test_*.py",  # 临时测试文件
            "**/debug_*.py",  # 调试文件
            "**/fix_*.py",   # 临时修复文件
            "**/check_*.py",  # 检查脚本
            "**/verify_*.py",  # 验证脚本
            "**/diagnose_*.py",  # 诊断脚本
        ]

        temp_files = []
        for pattern in temp_patterns:
            files = list(self.project_root.glob(pattern))
            # 过滤掉重要的测试文件
            files = [f for f in files if not self._is_important_file(f)]
            temp_files.extend(files)

        self.temp_files = temp_files
        print(f"   找到 {len(temp_files)} 个临时文件")

        return temp_files

    def _is_important_file(self, file_path: Path) -> bool:
        """判断是否是重要文件，不应删除"""
        important_patterns = [
            "tests/final/",
            "tests/integration/",
            "tests/performance/",
            "tests/compatibility/",
            "main.py",
            "__init__.py"
        ]

        file_str = str(file_path)
        return any(pattern in file_str for pattern in important_patterns)

    def scan_duplicate_files(self) -> List[Path]:
        """扫描重复文件"""
        print("🔍 扫描重复文件...")

        duplicate_patterns = [
            "**/backups_professional/",
            "**/*_clean.py",
            "**/*_backup.py",
            "**/*.comprehensive_backup",
            "**/*.final_core_backup",
            "**/*.thorough_backup",
            "**/*.precise_backup"
        ]

        duplicate_files = []
        for pattern in duplicate_patterns:
            files = list(self.project_root.glob(pattern))
            duplicate_files.extend(files)

        self.duplicate_files = duplicate_files
        print(f"   找到 {len(duplicate_files)} 个重复文件")

        return duplicate_files

    def calculate_file_size(self, files: List[Path]) -> float:
        """计算文件总大小(MB)"""
        total_size = 0
        for file_path in files:
            if file_path.exists():
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                elif file_path.is_dir():
                    for sub_file in file_path.rglob('*'):
                        if sub_file.is_file():
                            total_size += sub_file.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB

    def remove_backup_files(self, confirm: bool = True) -> int:
        """删除备份文件"""
        if not self.backup_files:
            return 0

        size_mb = self.calculate_file_size(self.backup_files)

        if confirm:
            print(f"\n📋 将删除 {len(self.backup_files)} 个备份文件 ({size_mb:.2f} MB):")
            for file_path in self.backup_files[:10]:  # 显示前10个
                print(f"   - {file_path.relative_to(self.project_root)}")
            if len(self.backup_files) > 10:
                print(f"   ... 还有 {len(self.backup_files) - 10} 个文件")

            response = input("\n确认删除这些备份文件? (y/N): ").lower()
            if response != 'y':
                print("❌ 取消删除备份文件")
                return 0

        print("🗑️  删除备份文件...")
        removed_count = 0

        for file_path in self.backup_files:
            try:
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                    removed_count += 1
                    print(f"   ✅ 删除: {file_path.relative_to(self.project_root)}")
            except Exception as e:
                print(f"   ❌ 删除失败 {file_path}: {e}")

        self.cleanup_stats['backup_files_removed'] = removed_count
        self.cleanup_stats['space_saved_mb'] += size_mb

        return removed_count

    def remove_temp_files(self, confirm: bool = True) -> int:
        """删除临时文件"""
        if not self.temp_files:
            return 0

        size_mb = self.calculate_file_size(self.temp_files)

        if confirm:
            print(f"\n📋 将删除 {len(self.temp_files)} 个临时文件 ({size_mb:.2f} MB):")
            for file_path in self.temp_files[:10]:
                print(f"   - {file_path.relative_to(self.project_root)}")
            if len(self.temp_files) > 10:
                print(f"   ... 还有 {len(self.temp_files) - 10} 个文件")

            response = input("\n确认删除这些临时文件? (y/N): ").lower()
            if response != 'y':
                print("❌ 取消删除临时文件")
                return 0

        print("🗑️  删除临时文件...")
        removed_count = 0

        for file_path in self.temp_files:
            try:
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                    removed_count += 1
                    print(f"   ✅ 删除: {file_path.relative_to(self.project_root)}")
            except Exception as e:
                print(f"   ❌ 删除失败 {file_path}: {e}")

        self.cleanup_stats['temp_files_removed'] = removed_count
        self.cleanup_stats['space_saved_mb'] += size_mb

        return removed_count

    def remove_duplicate_files(self, confirm: bool = True) -> int:
        """删除重复文件"""
        if not self.duplicate_files:
            return 0

        size_mb = self.calculate_file_size(self.duplicate_files)

        if confirm:
            print(f"\n📋 将删除 {len(self.duplicate_files)} 个重复文件 ({size_mb:.2f} MB):")
            for file_path in self.duplicate_files[:10]:
                print(f"   - {file_path.relative_to(self.project_root)}")
            if len(self.duplicate_files) > 10:
                print(f"   ... 还有 {len(self.duplicate_files) - 10} 个文件")

            response = input("\n确认删除这些重复文件? (y/N): ").lower()
            if response != 'y':
                print("❌ 取消删除重复文件")
                return 0

        print("🗑️  删除重复文件...")
        removed_count = 0

        for file_path in self.duplicate_files:
            try:
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                    removed_count += 1
                    print(f"   ✅ 删除: {file_path.relative_to(self.project_root)}")
            except Exception as e:
                print(f"   ❌ 删除失败 {file_path}: {e}")

        self.cleanup_stats['duplicate_files_removed'] = removed_count
        self.cleanup_stats['space_saved_mb'] += size_mb

        return removed_count

    def generate_cleanup_report(self) -> str:
        """生成清理报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_content = f"""# HIkyuu-UI 代码清理报告
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 清理统计

- **备份文件删除**: {self.cleanup_stats['backup_files_removed']} 个
- **临时文件删除**: {self.cleanup_stats['temp_files_removed']} 个  
- **重复文件删除**: {self.cleanup_stats['duplicate_files_removed']} 个
- **节省空间**: {self.cleanup_stats['space_saved_mb']:.2f} MB

## 🎯 清理效果

✅ **项目结构优化**: 移除了重构过程中产生的大量备份和临时文件
✅ **存储空间释放**: 释放了 {self.cleanup_stats['space_saved_mb']:.2f} MB 磁盘空间
✅ **代码库整洁**: 提高了代码库的可维护性和可读性
✅ **性能提升**: 减少了文件系统扫描的开销

## 📋 清理详情

### 备份文件清理
- 删除了所有 .backup、.backup2、.backup3 文件
- 清理了配置文件的历史备份
- 移除了服务重构过程中的备份文件

### 临时文件清理  
- 删除了诊断报告和日志文件
- 清理了开发过程中的调试脚本
- 移除了临时测试和验证文件

### 重复文件清理
- 删除了 backups_professional 目录
- 清理了重复的服务实现文件
- 移除了过时的备份版本

## 🔧 后续建议

1. **定期清理**: 建议每月运行一次清理脚本
2. **备份策略**: 建立正式的版本控制和备份策略
3. **代码规范**: 避免在项目中创建临时文件和备份文件
4. **自动化**: 考虑将清理过程集成到CI/CD流程中

HIkyuu-UI 项目现在更加整洁和高效！
"""

        report_file = f"code_cleanup_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        return report_file

    def run_full_cleanup(self, confirm: bool = True) -> Dict:
        """运行完整清理流程"""
        print("🚀 开始 HIkyuu-UI 代码清理...")
        print("=" * 60)

        # 扫描所有文件
        self.scan_backup_files()
        self.scan_temp_files()
        self.scan_duplicate_files()

        total_files = len(self.backup_files) + len(self.temp_files) + len(self.duplicate_files)
        total_size = (self.calculate_file_size(self.backup_files) +
                      self.calculate_file_size(self.temp_files) +
                      self.calculate_file_size(self.duplicate_files))

        print(f"\n📊 扫描结果:")
        print(f"   - 备份文件: {len(self.backup_files)} 个")
        print(f"   - 临时文件: {len(self.temp_files)} 个")
        print(f"   - 重复文件: {len(self.duplicate_files)} 个")
        print(f"   - 总计: {total_files} 个文件, {total_size:.2f} MB")

        if total_files == 0:
            print("✅ 没有发现需要清理的文件!")
            return self.cleanup_stats

        # 执行清理
        self.remove_backup_files(confirm)
        self.remove_temp_files(confirm)
        self.remove_duplicate_files(confirm)

        # 生成报告
        report_file = self.generate_cleanup_report()

        print(f"\n🎉 清理完成!")
        print(f"📄 详细报告: {report_file}")
        print("=" * 60)

        return self.cleanup_stats


def main():
    """主函数"""
    project_root = os.getcwd()

    print("HIkyuu-UI 重构后无效代码清理工具")
    print("=" * 60)
    print(f"项目路径: {project_root}")

    cleanup_manager = CodeCleanupManager(project_root)

    # 运行清理
    stats = cleanup_manager.run_full_cleanup(confirm=True)

    print(f"\n📊 最终统计:")
    print(f"   总删除文件: {sum(stats.values()) - stats['space_saved_mb']:.0f} 个")
    print(f"   节省空间: {stats['space_saved_mb']:.2f} MB")


if __name__ == "__main__":
    main()
