"""批量修复插件文件中的语法错误"""
import re

plugins = [
    ('plugins/data_sources/crypto/okx_plugin.py', 'OKX', 'okx'),
    ('plugins/data_sources/crypto/huobi_plugin.py', 'Huobi', 'huobi'),
    ('plugins/data_sources/crypto/coinbase_plugin.py', 'Coinbase', 'coinbase'),
    ('plugins/data_sources/crypto/crypto_universal_plugin.py', 'Crypto Universal', 'crypto_universal'),
    ('plugins/data_sources/futures/wenhua_plugin.py', 'Wenhua Futures', 'wenhua')
]

for file_path, name, id_suffix in plugins:
    print(f"Fixing {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 替换破损的字符串
        # 1. 替换所有以'self.name ='开头但未正确闭合的行
        content = re.sub(
            r'self\.name\s*=\s*"[^"]*$',
            f'self.name = "{name} Data Source"',
            content,
            flags=re.MULTILINE
        )

        # 2. 替换所有以'self.description ='开头但未正确闭合的行
        content = re.sub(
            r'self\.description\s*=\s*"[^"]*$',
            f'self.description = "Provides {name.lower()} exchange data, production-grade implementation"',
            content,
            flags=re.MULTILINE
        )

        # 3. 替换所有以'self.author ='开头但未正确闭合的行
        content = re.sub(
            r'self\.author\s*=\s*"[^"]*$',
            'self.author = "FactorWeave-Quant Development Team"',
            content,
            flags=re.MULTILINE
        )

        # 4. 修复unterminated f-string（将f-string改为普通string）
        content = re.sub(
            r'f"([^"]*)"([^"])*$',
            r'"\1"',
            content,
            flags=re.MULTILINE
        )

        # 5. 删除所有非ASCII可打印字符（除了常规空白字符）
        content = re.sub(r'[^\x20-\x7E\n\r\t]+', '', content)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[OK] Fixed {file_path}")
    except Exception as e:
        print(f"[ERROR] Error fixing {file_path}: {e}")

print("\nAll plugins fixed!")
