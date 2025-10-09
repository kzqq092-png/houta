#!/usr/bin/env python3
"""
HIkyuu-UI 无效代码分析工具 - 仅分析，不删除
生成详细的清理候选文件报告
"""

import os
from pathlib import Path
from typing import List, Dict
import json
from datetime import datetime


class CleanupAnalyzer:
    """清理分析器 - 仅分析，不删除"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def analyze_backup_files(self) -> Dict:
        """分析备份文件"""
        backup_patterns = [
            "**/*.backup",
            "**/*.backup2",
            "**/*.backup3",
            "**/config/app_config.json.backup.*"
        ]

        backup_files = []
        total_size = 0

        for pattern in backup_patterns:
            files = list(self.project_root.glob(pattern))
            for file_path in files:
                if file_path.exists() and file_path.is_file():
                    size = file_path.stat().st_size
                    backup_files.append({
                        'path': str(file_path.relative_to(self.project_root)),
                        'size_bytes': size,
                        'size_mb': size / (1024 * 1024),
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
                    total_size += size

        return {
            'files': backup_files,
            'count': len(backup_files),
            'total_size_mb': total_size / (1024 * 1024)
        }

    def analyze_temp_files(self) -> Dict:
        """分析临时文件"""
        temp_patterns = [
            "**/architecture_diagnosis_report_*.md",
            "**/startup_log.txt",
            "**/startup_error.txt",
            "**/*_report_*.txt",
            "**/*_report_*.md",
            "**/comprehensive_*.py",
            "**/debug_*.py",
            "**/fix_*.py",
            "**/check_*.py",
            "**/verify_*.py",
            "**/diagnose_*.py",
            "**/enhance_*.py",
            "**/optimize_*.py",
            "**/immediate_*.py"
        ]

        temp_files = []
        total_size = 0

        for pattern in temp_patterns:
            files = list(self.project_root.glob(pattern))
            for file_path in files:
                if file_path.exists() and file_path.is_file() and not self._is_important_file(file_path):
                    size = file_path.stat().st_size
                    temp_files.append({
                        'path': str(file_path.relative_to(self.project_root)),
                        'size_bytes': size,
                        'size_mb': size / (1024 * 1024),
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'category': self._categorize_temp_file(file_path)
                    })
                    total_size += size

        return {
            'files': temp_files,
            'count': len(temp_files),
            'total_size_mb': total_size / (1024 * 1024)
        }

    def analyze_duplicate_files(self) -> Dict:
        """分析重复文件"""
        duplicate_patterns = [
            "**/backups_professional/",
            "**/*_clean.py",
            "**/*_backup.py"
        ]

        duplicate_files = []
        total_size = 0

        for pattern in duplicate_patterns:
            files = list(self.project_root.glob(pattern))
            for file_path in files:
                if file_path.exists():
                    if file_path.is_file():
                        size = file_path.stat().st_size
                        duplicate_files.append({
                            'path': str(file_path.relative_to(self.project_root)),
                            'type': 'file',
                            'size_bytes': size,
                            'size_mb': size / (1024 * 1024),
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
                        total_size += size
                    elif file_path.is_dir():
                        dir_size = sum(f.stat().st_size for f in file_path.rglob('*') if f.is_file())
                        duplicate_files.append({
                            'path': str(file_path.relative_to(self.project_root)),
                            'type': 'directory',
                            'size_bytes': dir_size,
                            'size_mb': dir_size / (1024 * 1024),
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
                        total_size += dir_size

        return {
            'files': duplicate_files,
            'count': len(duplicate_files),
            'total_size_mb': total_size / (1024 * 1024)
        }

    def _is_important_file(self, file_path: Path) -> bool:
        """判断是否是重要文件"""
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

    def _categorize_temp_file(self, file_path: Path) -> str:
        """分类临时文件"""
        name = file_path.name.lower()
        if 'report' in name:
            return 'report'
        elif 'debug' in name:
            return 'debug'
        elif 'fix' in name:
            return 'fix'
        elif 'check' in name or 'verify' in name:
            return 'verification'
        elif 'diagnose' in name:
            return 'diagnosis'
        elif 'log' in name or 'error' in name:
            return 'log'
        else:
            return 'other'

    def generate_analysis_report(self) -> str:
        """生成分析报告"""
        print("🔍 分析项目文件...")

        backup_analysis = self.analyze_backup_files()
        temp_analysis = self.analyze_temp_files()
        duplicate_analysis = self.analyze_duplicate_files()

        total_files = backup_analysis['count'] + temp_analysis['count'] + duplicate_analysis['count']
        total_size = backup_analysis['total_size_mb'] + temp_analysis['total_size_mb'] + duplicate_analysis['total_size_mb']

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 生成Markdown报告
        report_content = f"""# HIkyuu-UI 无效代码分析报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**项目路径**: {self.project_root}

## 📊 总体统计

- **总文件数**: {total_files} 个
- **总大小**: {total_size:.2f} MB
- **备份文件**: {backup_analysis['count']} 个 ({backup_analysis['total_size_mb']:.2f} MB)
- **临时文件**: {temp_analysis['count']} 个 ({temp_analysis['total_size_mb']:.2f} MB)
- **重复文件**: {duplicate_analysis['count']} 个 ({duplicate_analysis['total_size_mb']:.2f} MB)

## 🗂️ 备份文件详情 ({backup_analysis['count']} 个)

这些是重构过程中产生的备份文件，现在可以安全删除：

"""

        # 添加备份文件列表
        for file_info in sorted(backup_analysis['files'], key=lambda x: x['size_mb'], reverse=True):
            report_content += f"- `{file_info['path']}` ({file_info['size_mb']:.2f} MB, {file_info['modified']})\n"

        report_content += f"""

## 📄 临时文件详情 ({temp_analysis['count']} 个)

按类别分组的临时文件：

"""

        # 按类别分组临时文件
        temp_by_category = {}
        for file_info in temp_analysis['files']:
            category = file_info['category']
            if category not in temp_by_category:
                temp_by_category[category] = []
            temp_by_category[category].append(file_info)

        for category, files in temp_by_category.items():
            report_content += f"### {category.title()} 文件 ({len(files)} 个)\n\n"
            for file_info in sorted(files, key=lambda x: x['size_mb'], reverse=True):
                report_content += f"- `{file_info['path']}` ({file_info['size_mb']:.2f} MB, {file_info['modified']})\n"
            report_content += "\n"

        report_content += f"""## 🔄 重复文件详情 ({duplicate_analysis['count']} 个)

这些是重复或过时的文件/目录：

"""

        # 添加重复文件列表
        for file_info in sorted(duplicate_analysis['files'], key=lambda x: x['size_mb'], reverse=True):
            file_type = "📁" if file_info['type'] == 'directory' else "📄"
            report_content += f"- {file_type} `{file_info['path']}` ({file_info['size_mb']:.2f} MB, {file_info['modified']})\n"

        report_content += f"""

## 🎯 清理建议

### 🟢 安全清理 (推荐)
可以安全删除以下文件，不会影响系统功能：
- 所有 `.backup` 文件 ({backup_analysis['count']} 个)
- 诊断报告文件 (report 类别)
- 日志文件 (log 类别)
- `backups_professional/` 目录

**预计节省空间**: {backup_analysis['total_size_mb'] + sum(f['size_mb'] for f in temp_analysis['files'] if f['category'] in ['report', 'log']):.2f} MB

### 🟡 谨慎清理
需要仔细检查的文件：
- 调试脚本 (debug 类别) - 可能还有用
- 修复脚本 (fix 类别) - 可能包含重要逻辑
- 验证脚本 (verification 类别) - 可能用于测试

### 🔴 保留文件
建议保留的重要文件：
- `tests/` 目录下的测试文件
- `main.py` 和 `__init__.py` 文件
- 核心功能相关的脚本

## 📋 清理命令

如果您确认要删除这些文件，可以使用以下命令：

```bash
# 删除备份文件
find . -name "*.backup*" -type f -delete

# 删除特定临时文件
rm -f architecture_diagnosis_report_*.md
rm -f startup_log.txt startup_error.txt
rm -f *_report_*.txt *_report_*.md

# 删除重复目录
rm -rf backups_professional/
```

**⚠️ 警告**: 删除前请确保您有完整的项目备份！

## 📈 清理效果预估

清理完成后：
- **文件数量减少**: {total_files} 个
- **存储空间释放**: {total_size:.2f} MB
- **项目结构优化**: 移除冗余文件，提高可维护性
- **构建性能提升**: 减少文件扫描开销

---

*此报告由 HIkyuu-UI 无效代码分析工具生成*
"""

        # 保存报告
        report_file = f"cleanup_analysis_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        # 同时生成JSON格式的详细数据
        json_data = {
            'timestamp': timestamp,
            'summary': {
                'total_files': total_files,
                'total_size_mb': total_size,
                'backup_files': backup_analysis['count'],
                'temp_files': temp_analysis['count'],
                'duplicate_files': duplicate_analysis['count']
            },
            'backup_files': backup_analysis,
            'temp_files': temp_analysis,
            'duplicate_files': duplicate_analysis
        }

        json_file = f"cleanup_analysis_data_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        print(f"📊 分析完成!")
        print(f"📄 详细报告: {report_file}")
        print(f"📋 数据文件: {json_file}")

        return report_file


def main():
    """主函数"""
    project_root = os.getcwd()

    print("HIkyuu-UI 无效代码分析工具")
    print("=" * 50)
    print(f"项目路径: {project_root}")
    print("注意: 此工具仅分析文件，不会删除任何内容")
    print("=" * 50)

    analyzer = CleanupAnalyzer(project_root)
    report_file = analyzer.generate_analysis_report()

    print(f"\n✅ 分析报告已生成: {report_file}")
    print("📖 请查看报告了解详细的清理建议")


if __name__ == "__main__":
    main()
