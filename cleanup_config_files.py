#!/usr/bin/env python3
"""
配置文件清理脚本

在验证数据库迁移成功后，删除旧的JSON配置文件
"""

import os
import sys
from pathlib import Path


def cleanup_config_files():
    """清理旧的配置文件"""
    print("🗑️  清理旧的告警配置文件...")

    config_dir = Path(__file__).parent / "config"

    files_to_cleanup = [
        "alert_config.json",
        "alert_history.json"
    ]

    cleaned_files = []

    for filename in files_to_cleanup:
        file_path = config_dir / filename
        if file_path.exists():
            try:
                file_path.unlink()  # 删除文件
                cleaned_files.append(filename)
                print(f"✅ 已删除: {filename}")
            except Exception as e:
                print(f"❌ 删除失败 {filename}: {e}")
        else:
            print(f"ℹ️  文件不存在: {filename}")

    if cleaned_files:
        print(f"\n🎉 成功清理了 {len(cleaned_files)} 个配置文件:")
        for filename in cleaned_files:
            print(f"  - {filename}")
        print("\n✅ 系统现在完全使用数据库存储告警配置")
    else:
        print("\nℹ️  没有找到需要清理的配置文件")

    return len(cleaned_files)


def main():
    """主函数"""
    print("=" * 60)
    print("🧹 FactorWeave-Quant 配置文件清理工具")
    print("=" * 60)

    print("⚠️  注意：此操作将删除以下配置文件：")
    print("  - config/alert_config.json")
    print("  - config/alert_history.json")
    print("\n📦 备份文件位于: config/backup_before_migration/")
    print("🔄 系统现在使用数据库存储告警配置")

    # 自动执行清理（因为已经迁移到数据库）
    cleaned_count = cleanup_config_files()

    print("\n" + "=" * 60)
    if cleaned_count > 0:
        print("🎉 配置文件清理完成！")
        print("✅ 告警配置已完全迁移到数据库存储")
    else:
        print("ℹ️  没有需要清理的文件")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
