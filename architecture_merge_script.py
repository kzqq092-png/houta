#!/usr/bin/env python
"""
架构服务自动化合并脚本

自动执行所有服务版本的合并和引用更新。
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict

# 服务合并配置
SERVICE_MERGE_CONFIG = [
    # (保留文件, 删除文件, 旧类名, 新类名)
    ("data_service.py", "unified_data_service.py", "UnifiedDataService", "DataService"),
    ("database_service.py", "unified_database_service.py", "UnifiedDatabaseService", "DatabaseService"),
    ("cache_service.py", "unified_cache_service.py", "UnifiedCacheService", "CacheService"),
    ("config_service.py", "unified_config_service.py", "UnifiedConfigService", "ConfigService"),
    # ConfigService还有enhanced版本
    ("config_service.py", "enhanced_config_service.py", "EnhancedConfigService", "ConfigService"),
    ("plugin_service.py", "unified_plugin_service.py", "UnifiedPluginService", "PluginService"),
    ("network_service.py", "unified_network_service.py", "UnifiedNetworkService", "NetworkService"),
    ("performance_service.py", "unified_performance_service.py", "UnifiedPerformanceService", "PerformanceService"),
    ("trading_service.py", "unified_trading_service.py", "UnifiedTradingService", "TradingService"),
    ("analysis_service.py", "unified_analysis_service.py", "UnifiedAnalysisService", "AnalysisService"),
]


class ServiceMerger:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.services_dir = self.project_root / "core" / "services"
        self.backup_dir = self.services_dir / ".backup"
        self.merge_log = []

    def ensure_backup_dir(self):
        """确保备份目录存在"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ 备份目录已准备: {self.backup_dir}")

    def backup_file(self, filename: str) -> bool:
        """备份文件"""
        source = self.services_dir / filename
        if not source.exists():
            print(f"⚠ 文件不存在，跳过备份: {filename}")
            return False

        backup = self.backup_dir / f"{filename}.bak"
        shutil.copy2(source, backup)
        print(f"✓ 已备份: {filename} -> .backup/{filename}.bak")
        return True

    def delete_file(self, filename: str) -> bool:
        """删除文件"""
        filepath = self.services_dir / filename
        if not filepath.exists():
            print(f"⚠ 文件不存在，跳过删除: {filename}")
            return False

        filepath.unlink()
        print(f"✓ 已删除: {filename}")
        return True

    def merge_service(self, keep_file: str, delete_file: str, old_class: str, new_class: str) -> bool:
        """合并服务"""
        print(f"\n{'='*60}")
        print(f"合并: {delete_file} ({old_class}) -> {keep_file} ({new_class})")
        print(f"{'='*60}")

        # 备份两个文件
        self.backup_file(keep_file)
        backed_up = self.backup_file(delete_file)

        if not backed_up:
            print(f"⚠ {delete_file} 不存在，可能已合并，跳过")
            self.merge_log.append({
                'keep': keep_file,
                'delete': delete_file,
                'old_class': old_class,
                'new_class': new_class,
                'status': 'skipped'
            })
            return False

        # 删除旧文件
        self.delete_file(delete_file)

        self.merge_log.append({
            'keep': keep_file,
            'delete': delete_file,
            'old_class': old_class,
            'new_class': new_class,
            'status': 'success'
        })

        return True

    def update_imports(self, old_class: str, new_class: str, delete_file: str):
        """更新所有文件中的import语句"""
        print(f"\n更新引用: {old_class} -> {new_class}")

        # 需要更新的模式
        patterns = [
            # import UnifiedXxxService -> import XxxService
            (f"from.*{delete_file.replace('.py', '')} import {old_class}",
             f"from .{delete_file.replace('.py', '').replace('unified_', '').replace('enhanced_', '')} import {new_class}"),
            # UnifiedXxxService() -> XxxService()
            (f"{old_class}\\(", f"{new_class}("),
            # resolve(UnifiedXxxService) -> resolve(XxxService)
            (f"resolve\\({old_class}\\)", f"resolve({new_class})"),
            # register.*UnifiedXxxService -> register.*XxxService
            (f"register\\([^,]*{old_class}", f"register({new_class}"),
        ]

        updated_files = []

        # 遍历所有Python文件
        for py_file in self.project_root.rglob("*.py"):
            if ".backup" in str(py_file) or "venv" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding='utf-8')
                original_content = content

                # 应用所有模式替换
                for pattern, replacement in patterns:
                    content = re.sub(pattern, replacement, content)

                # 如果内容有变化，写回文件
                if content != original_content:
                    py_file.write_text(content, encoding='utf-8')
                    updated_files.append(str(py_file.relative_to(self.project_root)))

            except Exception as e:
                print(f"⚠ 处理文件出错 {py_file}: {e}")

        if updated_files:
            print(f"✓ 已更新 {len(updated_files)} 个文件:")
            for f in updated_files[:10]:  # 只显示前10个
                print(f"  - {f}")
            if len(updated_files) > 10:
                print(f"  ... 还有 {len(updated_files)-10} 个文件")
        else:
            print("ℹ 未发现需要更新的文件")

        return updated_files

    def merge_all_services(self):
        """合并所有服务"""
        print("\n" + "="*60)
        print("开始自动化服务合并")
        print("="*60)

        self.ensure_backup_dir()

        total = len(SERVICE_MERGE_CONFIG)
        success_count = 0

        for i, (keep, delete, old_cls, new_cls) in enumerate(SERVICE_MERGE_CONFIG, 1):
            print(f"\n[{i}/{total}] 处理服务...")

            if self.merge_service(keep, delete, old_cls, new_cls):
                success_count += 1
                # 更新所有引用
                self.update_imports(old_cls, new_cls, delete)

        print("\n" + "="*60)
        print(f"合并完成: {success_count}/{total} 成功")
        print("="*60)

        return success_count

    def generate_report(self):
        """生成合并报告"""
        report_path = self.project_root / "architecture_merge_report.md"

        report = ["# 架构服务合并报告\n"]
        report.append(f"**生成时间**: {pd.Timestamp.now()}\n")
        report.append(f"**项目路径**: {self.project_root}\n\n")

        report.append("## 合并概要\n\n")
        success = sum(1 for item in self.merge_log if item['status'] == 'success')
        skipped = sum(1 for item in self.merge_log if item['status'] == 'skipped')
        report.append(f"- 成功合并: {success}\n")
        report.append(f"- 跳过: {skipped}\n")
        report.append(f"- 总计: {len(self.merge_log)}\n\n")

        report.append("## 详细日志\n\n")
        for item in self.merge_log:
            status_icon = "✓" if item['status'] == 'success' else "⚠"
            report.append(f"### {status_icon} {item['old_class']} -> {item['new_class']}\n\n")
            report.append(f"- **保留文件**: `{item['keep']}`\n")
            report.append(f"- **删除文件**: `{item['delete']}`\n")
            report.append(f"- **状态**: {item['status']}\n\n")

        report_path.write_text("".join(report), encoding='utf-8')
        print(f"\n✓ 合并报告已生成: {report_path}")

        return report_path


def main():
    """主函数"""
    import sys

    # 获取项目根目录
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()

    print(f"项目根目录: {project_root}")

    # 创建合并器并执行
    merger = ServiceMerger(project_root)
    success_count = merger.merge_all_services()

    # 生成报告
    merger.generate_report()

    print("\n" + "="*60)
    print("✓ 所有操作完成！")
    print("="*60)
    print("\n下一步:")
    print("1. 运行测试: pytest tests/phase2/phase2_functional_verification.py")
    print("2. 检查日志: 查看 architecture_merge_report.md")
    print("3. 如有问题: 从 .backup 目录恢复文件")

    return success_count


if __name__ == "__main__":
    import pandas as pd  # 用于时间戳
    main()
