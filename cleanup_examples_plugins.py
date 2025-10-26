"""
自动清理 plugins/examples/ 目录

安全措施：
1. 创建完整备份
2. 验证依赖引用
3. 生成清理报告
"""
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def check_active_references():
    """检查是否有活跃的代码引用"""
    print("\n检查代码引用...")

    # 检查核心代码中的引用（排除废弃代码、测试、文档）
    result = os.popen(
        'grep -r "from plugins.examples\\|import plugins.examples" '
        '--include="*.py" core/ plugins/data_sources/ main.py 2>/dev/null '
        '| grep -v "DEPRECATED\\|废弃\\|test\\|Test"'
    ).read()

    if result.strip():
        print("  [WARNING] 发现活跃引用:")
        print(result)
        return False
    else:
        print("  [OK] 未发现活跃引用")
        return True


def create_backup():
    """创建备份"""
    examples_dir = Path("plugins/examples")

    if not examples_dir.exists():
        print("  [INFO] plugins/examples/ 目录不存在，无需备份")
        return None

    backup_name = f"plugins_examples_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
    print(f"\n创建备份: {backup_name}")

    try:
        import tarfile
        with tarfile.open(backup_name, "w:gz") as tar:
            tar.add(examples_dir, arcname="plugins/examples")

        backup_path = os.path.abspath(backup_name)
        backup_size = os.path.getsize(backup_name) / 1024  # KB
        print(f"  [OK] 备份成功: {backup_path} ({backup_size:.1f} KB)")
        return backup_path

    except Exception as e:
        print(f"  [ERROR] 备份失败: {e}")
        return None


def list_files_to_delete():
    """列出将要删除的文件"""
    examples_dir = Path("plugins/examples")

    if not examples_dir.exists():
        return []

    files = []
    for item in examples_dir.rglob("*"):
        if item.is_file():
            files.append(item)

    return files


def delete_examples_directory():
    """删除 plugins/examples/ 目录"""
    examples_dir = Path("plugins/examples")

    if not examples_dir.exists():
        print("  [INFO] plugins/examples/ 目录不存在")
        return True

    try:
        shutil.rmtree(examples_dir)
        print(f"  [OK] 已删除: {examples_dir}")
        return True
    except Exception as e:
        print(f"  [ERROR] 删除失败: {e}")
        return False


def generate_cleanup_report(backup_path, deleted_files):
    """生成清理报告"""
    report_name = f"examples_cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    with open(report_name, 'w', encoding='utf-8') as f:
        f.write("# Examples 目录清理报告\n\n")
        f.write(f"**清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 备份信息\n\n")
        if backup_path:
            f.write(f"- 备份文件: `{backup_path}`\n")
            f.write(f"- 备份大小: {os.path.getsize(backup_path) / 1024:.1f} KB\n\n")
        else:
            f.write("- 未创建备份（目录不存在）\n\n")

        f.write("## 删除的文件\n\n")
        f.write(f"共删除 {len(deleted_files)} 个文件：\n\n")
        for file in sorted(deleted_files):
            f.write(f"- `{file}`\n")

        f.write("\n## 验证步骤\n\n")
        f.write("请执行以下命令验证系统正常：\n\n")
        f.write("```bash\n")
        f.write("# 1. 启动系统\n")
        f.write("python main.py\n\n")
        f.write("# 2. 检查日志\n")
        f.write("tail -f logs/latest.log\n\n")
        f.write("# 3. 验证插件加载\n")
        f.write("python check_plugin_initialized_attribute.py\n")
        f.write("```\n\n")

        f.write("## 回滚方法\n\n")
        if backup_path:
            f.write("如果需要恢复，执行：\n\n")
            f.write("```bash\n")
            f.write(f"tar -xzf {os.path.basename(backup_path)}\n")
            f.write("```\n")

    print(f"\n清理报告已生成: {report_name}")


def main():
    print("=" * 80)
    print("Examples 插件目录清理脚本")
    print("=" * 80)

    # 检查目录是否存在
    examples_dir = Path("plugins/examples")
    if not examples_dir.exists():
        print("\n[INFO] plugins/examples/ 目录不存在，无需清理")
        return 0

    # 列出将要删除的文件
    files_to_delete = list_files_to_delete()
    print(f"\n将要删除 {len(files_to_delete)} 个文件")
    print("\n部分文件列表（前10个）:")
    for f in files_to_delete[:10]:
        print(f"  - {f.relative_to('plugins/examples')}")
    if len(files_to_delete) > 10:
        print(f"  ... 还有 {len(files_to_delete) - 10} 个文件")

    # 检查引用
    print("\n" + "=" * 80)
    print("步骤 1: 检查代码引用")
    print("=" * 80)

    safe_to_delete = check_active_references()

    if not safe_to_delete:
        print("\n[WARNING] 发现活跃引用，建议先检查这些引用是否可以删除")
        confirm = input("\n是否仍要继续？(yes/no): ")
        if confirm.lower() != "yes":
            print("\n[CANCELLED] 已取消清理")
            return 1

    # 创建备份
    print("\n" + "=" * 80)
    print("步骤 2: 创建备份")
    print("=" * 80)

    backup_path = create_backup()

    if not backup_path:
        print("\n[ERROR] 备份失败，终止清理")
        return 1

    # 最终确认
    print("\n" + "=" * 80)
    print("步骤 3: 删除目录")
    print("=" * 80)

    print(f"\n即将删除: plugins/examples/")
    print(f"备份位置: {backup_path}")

    confirm = input("\n确认删除？(yes/no): ")

    if confirm.lower() != "yes":
        print("\n[CANCELLED] 已取消清理")
        return 1

    # 删除目录
    success = delete_examples_directory()

    if not success:
        print("\n[ERROR] 删除失败")
        return 1

    # 生成报告
    print("\n" + "=" * 80)
    print("步骤 4: 生成报告")
    print("=" * 80)

    generate_cleanup_report(backup_path, files_to_delete)

    # 完成
    print("\n" + "=" * 80)
    print("[SUCCESS] 清理完成!")
    print("=" * 80)

    print("\n下一步建议:")
    print("1. 重启应用: python main.py")
    print("2. 观察日志: tail -f logs/latest.log")
    print("3. 验证插件: python check_plugin_initialized_attribute.py")
    print(f"4. 如需回滚: tar -xzf {os.path.basename(backup_path)}")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] 发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
