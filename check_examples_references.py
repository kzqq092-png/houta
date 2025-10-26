"""检查examples插件的引用和使用情况"""
import sqlite3
from pathlib import Path
import os

print("="*80)
print("Examples插件引用检查")
print("="*80)

# 1. 检查数据库中的examples插件
print("\n1. 检查插件数据库中的examples记录")
print("-"*80)

db_path = Path("db/plugins/plugins.db")
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 查询examples插件
    cursor.execute("""
        SELECT plugin_id, name, version, enabled, plugin_type
        FROM plugins
        WHERE plugin_id LIKE '%examples%'
    """)

    examples_plugins = cursor.fetchall()

    if examples_plugins:
        print(f"找到 {len(examples_plugins)} 个examples插件记录:")
        for plugin_id, name, version, enabled, plugin_type in examples_plugins:
            status = "[ENABLED]" if enabled else "[DISABLED]"
            print(f"  {status} {plugin_id}")
            print(f"    名称: {name}")
            print(f"    版本: {version}")
            print(f"    类型: {plugin_type}")
            print()
    else:
        print("  [OK] 数据库中没有examples插件记录")

    conn.close()
else:
    print("  [WARN] 插件数据库不存在")

# 2. 检查代码中的import语句
print("\n2. 检查代码中的examples导入")
print("-"*80)

import_patterns = [
    'from plugins.examples',
    'from examples',
    'import examples',
    'plugins.examples',
]

found_imports = []

for root, dirs, files in os.walk('.'):
    # 跳过某些目录
    if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', '.venv']):
        continue

    for file in files:
        if file.endswith('.py'):
            file_path = Path(root) / file
            try:
                content = file_path.read_text(encoding='utf-8')
                for pattern in import_patterns:
                    if pattern in content:
                        # 排除注释
                        for line_num, line in enumerate(content.split('\n'), 1):
                            if pattern in line and not line.strip().startswith('#'):
                                found_imports.append((str(file_path), line_num, line.strip()))
                                break
            except:
                pass

if found_imports:
    print(f"找到 {len(found_imports)} 处examples导入:")
    for file_path, line_num, line in found_imports[:20]:  # 只显示前20个
        print(f"  {file_path}:{line_num}")
        print(f"    {line[:100]}")
else:
    print("  [OK] 没有找到活跃的examples导入")

# 3. 检查examples目录的大小
print("\n3. Examples目录统计")
print("-"*80)

plugins_examples = Path("plugins/examples")
examples_dir = Path("examples")

if plugins_examples.exists():
    files = list(plugins_examples.glob("**/*.py"))
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    print(f"plugins/examples/:")
    print(f"  文件数: {len(files)}")
    print(f"  总大小: {total_size / 1024:.2f} KB")
    print(f"  文件列表:")
    for f in sorted(files):
        size_kb = f.stat().st_size / 1024
        print(f"    - {f.name} ({size_kb:.2f} KB)")
else:
    print("plugins/examples/ 不存在")

print()

if examples_dir.exists():
    files = list(examples_dir.glob("**/*.py"))
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    print(f"examples/:")
    print(f"  文件数: {len(files)}")
    print(f"  总大小: {total_size / 1024:.2f} KB")
else:
    print("examples/ 不存在")

# 4. 对比examples和data_sources
print("\n4. Examples vs Data_Sources对比")
print("-"*80)

examples_plugins_map = {
    'binance_crypto_plugin.py': 'data_sources/crypto/binance_plugin.py',
    'okx_crypto_plugin.py': 'data_sources/crypto/okx_plugin.py',
    'huobi_crypto_plugin.py': 'data_sources/crypto/huobi_plugin.py',
    'coinbase_crypto_plugin.py': 'data_sources/crypto/coinbase_plugin.py',
    'wenhua_data_plugin.py': 'data_sources/futures/wenhua_plugin.py',
}

print("示例插件 -> 生产插件映射:")
for example, production in examples_plugins_map.items():
    example_path = plugins_examples / example
    production_path = Path("plugins") / production

    example_exists = example_path.exists()
    production_exists = production_path.exists()

    status = ""
    if example_exists and production_exists:
        status = "[BOTH EXIST]"
    elif production_exists:
        status = "[PROD ONLY]"
    elif example_exists:
        status = "[EXAMPLE ONLY]"
    else:
        status = "[NEITHER]"

    print(f"  {status} {example}")
    print(f"    -> {production}")

print("\n" + "="*80)
print("检查完成")
print("="*80)
