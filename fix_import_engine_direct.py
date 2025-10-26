#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

file_path = r'D:\DevelopTool\FreeCode\HIkyuu-UI\hikyuu-ui\core\importdata\unified_data_import_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Total lines:", len(lines))
print("Fixing import_kline issues...")

# Fix line 978
if 'import_kline' in lines[977]:
    print("Fixing line 978")
    lines[977] = '                self._import_kline_data(import_config, result)\n'

# Fix line 985
if 'import_kline' in lines[984]:
    print("Fixing line 985")
    lines[984] = '                self._import_kline_data(import_config, result)\n'

# Fix line 1044
if 'import_kline' in lines[1043]:
    print("Fixing line 1044")
    lines[1043] = '                self._import_kline_data_sync(import_config, result)\n'

# Fix line 1051
if 'import_kline' in lines[1050]:
    print("Fixing line 1051")
    lines[1050] = '                self._import_kline_data_sync(import_config, result)\n'

# Fix line 1172 - this is before a method definition
if 'import_kline' in lines[1171]:
    print("Fixing line 1172")
    lines[1171] = '    def _import_kline_data(self, task_config: ImportTaskConfig, result: UnifiedImportResult):\n'

# Fix line 1228 - this is before a method definition
if 'import_kline' in lines[1227]:
    print("Fixing line 1228")
    lines[1227] = '    def _import_kline_data_sync(self, task_config: ImportTaskConfig, result: UnifiedImportResult):\n'

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("File fixed successfully!")
