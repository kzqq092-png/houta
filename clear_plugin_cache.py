"""清理插件数据库缓存

此脚本用于清理插件管理器的数据库缓存，解决以下问题：
1. 插件名称显示为空或"未命名插件"
2. 插件元数据过时
3. orphan插件记录（examples目录下已移除的插件）

使用方法:
    python clear_plugin_cache.py
    
然后重启应用程序:
    python main.py
"""
import sqlite3
import sys
from pathlib import Path


def clear_plugin_cache():
    """清理插件缓存"""
    db_path = Path("data/factorweave_system.sqlite")

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    try:
        print("=" * 80)
        print("清理插件数据库缓存")
        print("=" * 80)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 1. 统计当前记录
        print("\n📊 清理前统计:")
        cursor.execute("SELECT COUNT(*) FROM plugin_status")
        status_count = cursor.fetchone()[0]
        print(f"   plugin_status 记录数: {status_count}")

        cursor.execute("SELECT COUNT(*) FROM plugin_metadata")
        metadata_count = cursor.fetchone()[0]
        print(f"   plugin_metadata 记录数: {metadata_count}")

        # 2. 清理 examples 目录的 orphan 记录
        print("\n🗑️  清理 orphan 插件记录...")
        cursor.execute("""
            DELETE FROM plugin_status 
            WHERE plugin_id LIKE 'examples.%'
        """)
        orphan_status = cursor.rowcount
        print(f"   从 plugin_status 删除: {orphan_status} 条")

        cursor.execute("""
            DELETE FROM plugin_metadata 
            WHERE plugin_id LIKE 'examples.%'
        """)
        orphan_metadata = cursor.rowcount
        print(f"   从 plugin_metadata 删除: {orphan_metadata} 条")

        # 3. 可选：清理所有插件状态（强制重新加载）
        print("\n⚠️  是否清理所有插件缓存？（这会强制重新加载所有插件）")
        print("   输入 'yes' 确认，或按 Enter 跳过")
        response = input("   > ").strip().lower()

        if response == 'yes':
            cursor.execute("DELETE FROM plugin_status")
            all_status = cursor.rowcount
            print(f"   从 plugin_status 删除: {all_status} 条")

            cursor.execute("DELETE FROM plugin_metadata")
            all_metadata = cursor.rowcount
            print(f"   从 plugin_metadata 删除: {all_metadata} 条")
        else:
            print("   跳过全量清理")

        # 4. 提交更改
        conn.commit()

        # 5. 统计清理后记录
        print("\n📊 清理后统计:")
        cursor.execute("SELECT COUNT(*) FROM plugin_status")
        status_count_after = cursor.fetchone()[0]
        print(f"   plugin_status 记录数: {status_count_after}")

        cursor.execute("SELECT COUNT(*) FROM plugin_metadata")
        metadata_count_after = cursor.fetchone()[0]
        print(f"   plugin_metadata 记录数: {metadata_count_after}")

        conn.close()

        print("\n" + "=" * 80)
        print("✅ 插件缓存清理完成")
        print("=" * 80)
        print("\n下一步:")
        print("  1. 重启应用程序: python main.py")
        print("  2. 打开插件管理器验证插件名称是否正常")
        print()

        return True

    except Exception as e:
        print(f"\n❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = clear_plugin_cache()
    sys.exit(0 if success else 1)
