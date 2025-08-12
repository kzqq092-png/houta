#!/usr/bin/env python3
"""
修复插件导入语句的脚本
将所有插件中的错误导入路径修复为正确的路径
"""

import os
import re


def fix_imports_in_file(file_path):
    """修复单个文件中的导入语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复导入语句
        old_import = "from core.data.data_models import"
        new_import = "from core.data_source_data_models import"

        if old_import in content:
            content = content.replace(old_import, new_import)

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
    plugins_dir = "plugins/examples"

    if not os.path.exists(plugins_dir):
        print(f"❌ 插件目录不存在: {plugins_dir}")
        return

    # 需要修复的插件文件
    plugin_files = [
        "akshare_stock_plugin.py",
        "eastmoney_stock_plugin.py",
        "binance_crypto_plugin.py",
        "coinbase_crypto_plugin.py",
        "huobi_crypto_plugin.py",
        "okx_crypto_plugin.py",
        "ctp_futures_plugin.py",
        "wenhua_data_plugin.py",
        "mysteel_data_plugin.py",
        "forex_data_plugin.py",
        "bond_data_plugin.py",
        "custom_data_plugin.py",
        "wind_data_plugin.py"
    ]

    fixed_count = 0
    total_count = 0

    print("开始修复插件导入语句...")
    print("=" * 50)

    for plugin_file in plugin_files:
        file_path = os.path.join(plugins_dir, plugin_file)
        if os.path.exists(file_path):
            total_count += 1
            if fix_imports_in_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  插件文件不存在: {file_path}")

    print("=" * 50)
    print(f"修复完成: {fixed_count}/{total_count} 个文件")


if __name__ == "__main__":
    main()
