#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""移除测试文件中的emoji"""

# 读取文件
with open('test_asset_metadata_phase1_4.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换emoji
replacements = {
    '✅': '[OK]',
    '❌': '[FAIL]',
    '⚠️': '[WARN]',
    'ℹ️': '[INFO]',
    '🎉': '[SUCCESS]'
}

for emoji, text in replacements.items():
    content = content.replace(emoji, text)

# 写回文件
with open('test_asset_metadata_phase1_4.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Emoji替换完成！")
