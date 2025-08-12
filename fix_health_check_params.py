#!/usr/bin/env python3
"""
修复HealthCheckResult参数名的脚本
"""

import os
import glob


def fix_file(file_path):
    """修复单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复参数名
        replacements = [
            ('response_time=', 'response_time_ms='),
            ('extra_info=', 'additional_info='),
            # 新增：修复反向参数
            ('response_time_ms=', 'response_time='),
            ('additional_info=', 'extra_info='),
        ]

        modified = False
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                modified = True

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path}")
            return True
        else:
            print(f"⏭️  {file_path} 无需修复")
            return False

    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False


def main():
    """主函数"""
    plugin_files = glob.glob("plugins/examples/*_plugin.py")

    fixed_count = 0
    total_count = len(plugin_files)

    print("开始修复HealthCheckResult参数名...")
    print("=" * 50)

    for file_path in plugin_files:
        if fix_file(file_path):
            fixed_count += 1

    print("=" * 50)
    print(f"修复完成: {fixed_count}/{total_count} 个文件")


if __name__ == "__main__":
    main()
