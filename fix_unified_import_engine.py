#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix unified_data_import_engine.py syntax errors

Problem: Multiple "import_kline" orphaned statements causing syntax errors
Solution: Replace with correct function calls
"""

import re
import os
import sys

def fix_unified_import_engine():
    """Fix unified_data_import_engine.py"""
    
    file_path = os.path.join(os.path.dirname(__file__), 'core/importdata/unified_data_import_engine.py')
    
    if not os.path.exists(file_path):
        print("File not found: " + file_path)
        return False
    
    print("Fixing file: " + file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = 0
    
    # Fix 1: Replace all "import_kline" statements used as method calls
    # Pattern: Lines containing just "import_kline" (with proper indentation)
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        # Check if line contains just "import_kline" with whitespace
        if re.match(r'^\s*import_kline\s*$', line):
            # Check context to determine proper fix
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * indent
            
            # Look ahead to understand context
            if i + 1 < len(lines) and '"""导入K线数据"""' in lines[i + 1]:
                # This is before a kline method definition
                fixed_lines.append(indent_str + 'def _import_kline_data(self, task_config: ImportTaskConfig, result: UnifiedImportResult):')
                changes += 1
            elif i + 1 < len(lines) and '"""同步导入K线数据' in lines[i + 1]:
                # This is before a sync kline method definition
                fixed_lines.append(indent_str + 'def _import_kline_data_sync(self, task_config: ImportTaskConfig, result: UnifiedImportResult):')
                changes += 1
            elif i > 0 and 'if task_config.data_type == "K线数据":' in lines[i - 1]:
                # This is after an if statement
                fixed_lines.append(indent_str + 'self._import_kline_data(import_config, result)')
                changes += 1
            elif i > 0 and 'def _import_realtime_data_sync' in '\n'.join(lines[max(0, i-10):i]):
                # This is after sync realtime data import, before sync section header
                fixed_lines.append(indent_str + 'self._import_kline_data_sync(import_config, result)')
                changes += 1
            else:
                # Default fix
                if 'sync' in '\n'.join(lines[max(0, i-20):i]).lower():
                    fixed_lines.append(indent_str + 'self._import_kline_data_sync(import_config, result)')
                else:
                    fixed_lines.append(indent_str + 'self._import_kline_data(import_config, result)')
                changes += 1
        else:
            fixed_lines.append(line)
        i += 1
    
    content = '\n'.join(fixed_lines)
    
    # Check if changes were made
    if content == original_content:
        print("No changes needed or already fixed")
        return False
    
    # Write back the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("File fixed successfully with " + str(changes) + " changes")
    return True


if __name__ == '__main__':
    success = fix_unified_import_engine()
    sys.exit(0 if success else 1)
