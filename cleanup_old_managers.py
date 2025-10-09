#!/usr/bin/env python
"""
清理旧Manager类脚本

根据架构精简报告，删除已被Service替代的旧Manager类。
所有被删除的文件都会先备份到 cleanup/archive/managers/ 目录。
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# 待删除的Manager类列表（根据架构报告）
MANAGERS_TO_DELETE = {
    # 数据管理类 (已被DataService替代)
    "unified_data_manager.py": "core/services",
    "asset_manager.py": "core/managers",
    "data_quality_risk_manager.py": "core",
    "enhanced_data_manager.py": "core/services",
    "data_source_manager.py": "core",
    "fallback_data_manager.py": "core",
    "minimal_data_manager.py": "core",
    "asset_aware_unified_data_manager.py": "core/services",
    "unified_data_accessor.py": "core/services",

    # 数据库管理类 (已被DatabaseService替代)
    "duckdb_connection_manager.py": "core/database",
    "sqlite_extension_manager.py": "core/database",
    "asset_separated_database_manager.py": "core/database",
    "enhanced_asset_database_manager.py": "core/database",
    "strategy_database_manager.py": "core/database",
    "tdx_server_database_manager.py": "core/database",

    # 缓存管理类 (已被CacheService替代)
    "multi_level_cache_manager.py": "core/cache",
    "intelligent_cache_manager.py": "core/cache",
    "cache_manager.py": "core/cache",
    "memory_manager.py": "core",
    "intelligent_cache_coordinator.py": "core/cache",
    "adaptive_cache_strategy.py": "core/cache",

    # 插件管理类 (已被PluginService替代)
    "plugin_manager.py": "core",
    "plugin_center.py": "core",
    "plugin_config_manager.py": "core",
    "plugin_table_manager.py": "core",

    # 配置管理类 (已被ConfigService替代)
    "config_manager.py": "utils",
    "dynamic_config_manager.py": "core",
    "import_config_manager.py": "core",
    "intelligent_config_manager.py": "core",
    "migration_config_manager.py": "core",

    # 网络管理类 (已被NetworkService替代)
    "network_manager.py": "core/network",
    "universal_network_config_manager.py": "core/network",
    "smart_retry_manager.py": "core/network",
    "retry_manager.py": "core/network",
    "proxy_manager.py": "core/network",

    # 安全管理类 (已被SecurityService替代)
    "security_manager.py": "core/security",
    "circuit_breaker_manager.py": "core/risk",
    "enhanced_circuit_breaker.py": "core/risk",
    "authentication_manager.py": "core/security",
    "authorization_manager.py": "core/security",
    "session_manager.py": "core/security",
    "token_manager.py": "core/security",
    "audit_manager.py": "core/security",
    "threat_detection_manager.py": "core/security",

    # 交易管理类 (已被TradingService替代)
    "trading_manager.py": "core/business",
    "risk_manager.py": "core/business",
    "position_manager.py": "core/business",
    "portfolio_manager.py": "core/business",
    "risk_rule_manager.py": "core/business",
    "order_manager.py": "core/business",
    "signal_manager.py": "core/business",

    # 分析管理类 (已被AnalysisService替代)
    "analysis_manager.py": "core/analysis",
    "indicator_combination_manager.py": "core/analysis",
    "indicator_service.py": "core/services",  # 旧版
    "indicator_dependency_manager.py": "core/services",
    "custom_indicator_manager.py": "core/analysis",

    # 市场管理类 (已被MarketService替代)
    "industry_manager.py": "core",
    "stock_manager.py": "core/business",
    "fallback_industry_manager.py": "core",
    "market_data_manager.py": "core",
    "watchlist_manager.py": "core",
    "quote_manager.py": "core",
    "sector_manager.py": "core",

    # 通知管理类 (已被NotificationService替代)
    "alert_rule_engine.py": "core/services",  # 旧版独立
    "alert_deduplication_service.py": "core/services",  # 旧版独立
    "alert_rule_hot_loader.py": "core/services",  # 旧版独立
    "alert_event_handler.py": "core/services",  # 旧版独立

    # 性能管理类 (已被PerformanceService替代)
    "performance_monitor.py": "core/monitoring",
    "unified_monitor.py": "core/monitoring",
    "resource_manager.py": "core",
    "dynamic_resource_manager.py": "core",
    "gpu_acceleration_manager.py": "core",
    "backpressure_manager.py": "core",

    # 生命周期管理类 (已被LifecycleService替代)
    "task_manager.py": "core",
    "strategy_lifecycle_manager.py": "core",
    "failover_manager.py": "core",
    "fault_tolerance_manager.py": "core/services",

    # 其他管理类
    "system_integration_manager.py": "core/integration",
    "deployment_manager.py": "core",
    "data_source_router.py": "core",
    "routing_rule_manager.py": "core/services",
    "intelligent_data_router.py": "core/services",
}


class ManagerCleaner:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.archive_dir = self.project_root / "cleanup" / "archive" / "managers"
        self.archive_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.deleted_files = []
        self.not_found_files = []
        self.error_files = []

    def ensure_archive_dir(self):
        """确保归档目录存在"""
        archive_path = self.archive_dir / self.archive_timestamp
        archive_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 归档目录已准备: {archive_path}")
        return archive_path

    def find_file(self, filename: str, search_dirs: List[str]) -> Path:
        """在多个目录中查找文件"""
        for directory in search_dirs:
            filepath = self.project_root / directory / filename
            if filepath.exists():
                return filepath
        return None

    def archive_and_delete(self, filename: str, relative_dir: str) -> bool:
        """归档并删除文件"""
        # 在指定目录和常见位置查找文件
        search_dirs = [
            relative_dir,
            "core",
            "core/managers",
            "core/services",
            "core/business",
            "core/analysis",
            "core/database",
            "core/cache",
            "core/network",
            "core/security",
            "core/risk",
            "core/monitoring",
            "core/integration",
            "utils",
        ]

        filepath = self.find_file(filename, search_dirs)

        if not filepath:
            self.not_found_files.append((filename, relative_dir))
            print(f"⚠ 未找到: {filename} (预期位置: {relative_dir})")
            return False

        try:
            # 创建归档目录结构
            archive_path = self.archive_dir / self.archive_timestamp
            relative_to_root = filepath.relative_to(self.project_root)
            archive_file = archive_path / relative_to_root
            archive_file.parent.mkdir(parents=True, exist_ok=True)

            # 复制到归档
            shutil.copy2(filepath, archive_file)

            # 删除原文件
            filepath.unlink()

            self.deleted_files.append(str(relative_to_root))
            print(f"✓ 已删除: {relative_to_root}")
            return True

        except Exception as e:
            self.error_files.append((filename, str(e)))
            print(f"✗ 错误: {filename} - {e}")
            return False

    def clean_all_managers(self):
        """清理所有旧Manager类"""
        print("\n" + "="*60)
        print("开始清理旧Manager类")
        print("="*60)

        self.ensure_archive_dir()

        total = len(MANAGERS_TO_DELETE)
        success_count = 0

        for i, (filename, directory) in enumerate(MANAGERS_TO_DELETE.items(), 1):
            print(f"\n[{i}/{total}] 处理: {filename}")
            if self.archive_and_delete(filename, directory):
                success_count += 1

        print("\n" + "="*60)
        print(f"清理完成")
        print("="*60)
        print(f"✓ 成功删除: {success_count}")
        print(f"⚠ 未找到: {len(self.not_found_files)}")
        print(f"✗ 错误: {len(self.error_files)}")

        return success_count

    def generate_report(self):
        """生成清理报告"""
        report_path = self.project_root / "manager_cleanup_report.md"

        report = ["# 旧Manager类清理报告\n\n"]
        report.append(f"**清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**项目路径**: {self.project_root}\n")
        report.append(f"**归档位置**: {self.archive_dir / self.archive_timestamp}\n\n")

        report.append("## 清理概要\n\n")
        report.append(f"- ✓ 成功删除: {len(self.deleted_files)}\n")
        report.append(f"- ⚠ 未找到: {len(self.not_found_files)}\n")
        report.append(f"- ✗ 处理错误: {len(self.error_files)}\n")
        report.append(f"- 总计: {len(MANAGERS_TO_DELETE)}\n\n")

        if self.deleted_files:
            report.append("## 已删除文件\n\n")
            for filepath in sorted(self.deleted_files):
                report.append(f"- ✓ `{filepath}`\n")
            report.append("\n")

        if self.not_found_files:
            report.append("## 未找到文件\n\n")
            report.append("*这些文件可能已被删除或从未存在*\n\n")
            for filename, expected_dir in sorted(self.not_found_files):
                report.append(f"- ⚠ `{filename}` (预期: {expected_dir})\n")
            report.append("\n")

        if self.error_files:
            report.append("## 处理错误\n\n")
            for filename, error in sorted(self.error_files):
                report.append(f"- ✗ `{filename}`: {error}\n")
            report.append("\n")

        report.append("## 恢复说明\n\n")
        report.append(f"如需恢复文件，所有被删除的文件已备份到:\n")
        report.append(f"```\n{self.archive_dir / self.archive_timestamp}\n```\n\n")
        report.append("恢复方法:\n")
        report.append("```bash\n")
        report.append(f"# 恢复单个文件\n")
        report.append(f"cp {self.archive_dir / self.archive_timestamp}/path/to/file.py ./path/to/\n\n")
        report.append(f"# 恢复所有文件\n")
        report.append(f"cp -r {self.archive_dir / self.archive_timestamp}/* ./\n")
        report.append("```\n")

        report_path.write_text("".join(report), encoding='utf-8')
        print(f"\n✓ 清理报告已生成: {report_path}")

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
    print(f"计划清理Manager数量: {len(MANAGERS_TO_DELETE)}")

    # 确认继续
    response = input("\n是否继续清理? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("清理已取消")
        return 0

    # 创建清理器并执行
    cleaner = ManagerCleaner(project_root)
    success_count = cleaner.clean_all_managers()

    # 生成报告
    cleaner.generate_report()

    print("\n" + "="*60)
    print("✓ 清理操作完成！")
    print("="*60)
    print("\n下一步:")
    print("1. 运行测试验证功能: pytest tests/")
    print("2. 检查清理报告: manager_cleanup_report.md")
    print("3. 如有问题，从归档目录恢复文件")
    print(f"\n归档位置: {cleaner.archive_dir / cleaner.archive_timestamp}")

    return success_count


if __name__ == "__main__":
    main()
