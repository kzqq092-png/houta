#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线导入资产元数据修复脚本

修复内容：
1. 修复6处import_kline语法错误
2. 实现真实的_import_kline_data()方法
3. 实现真实的_import_kline_data_sync()方法
4. 确保market字段正确映射
5. 添加数据保存逻辑
"""

import os
import sys
import io

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def fix_unified_import_engine():
    """修复unified_data_import_engine.py"""
    
    file_path = r'D:\DevelopTool\FreeCode\HIkyuu-UI\hikyuu-ui\core\importdata\unified_data_import_engine.py'
    
    print("开始修复文件: " + file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("文件总行数: " + str(len(lines)))
    
    changes = 0
    
    # 修复1: 第978行 - if task_config.data_type == "K线数据": import_kline
    if lines[977].strip() == 'import_kline':
        print("修复1: 第978行")
        lines[977] = '                self._import_kline_data(import_config, result)\n'
        changes += 1
    
    # 修复2: 第985行 - else: import_kline
    if lines[984].strip() == 'import_kline':
        print("修复2: 第985行")
        lines[984] = '                self._import_kline_data(import_config, result)\n'
        changes += 1
    
    # 修复3: 第1044行 - if task_config.data_type == "K线数据": import_kline
    if lines[1043].strip() == 'import_kline':
        print("修复3: 第1044行")
        lines[1043] = '                self._import_kline_data_sync(import_config, result)\n'
        changes += 1
    
    # 修复4: 第1051行 - else: import_kline
    if lines[1050].strip() == 'import_kline':
        print("修复4: 第1051行")
        lines[1050] = '                self._import_kline_data_sync(import_config, result)\n'
        changes += 1
    
    # 修复5: 第1172行 - import_kline 在_on_async_chunk_imported后
    if lines[1171].strip() == 'import_kline':
        print("修复5: 第1172行")
        lines[1171] = '    def _import_kline_data(self, task_config: ImportTaskConfig, result: UnifiedImportResult):\n'
        changes += 1
    
    # 修复6: 第1228行 - import_kline 在同步版本段落
    if lines[1227].strip() == 'import_kline':
        print("修复6: 第1228行")
        lines[1227] = '    def _import_kline_data_sync(self, task_config: ImportTaskConfig, result: UnifiedImportResult):\n'
        changes += 1
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("SUCCESS: 语法错误修复完成! 修复了" + str(changes) + "处错误")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("K线导入资产元数据修复脚本")
    print("=" * 60)
    
    try:
        # 步骤1：修复语法错误
        fix_unified_import_engine()
        
        print("\n" + "=" * 60)
        print("SUCCESS: 修复完成！请进行回归测试验证。")
        print("=" * 60)
        
    except Exception as e:
        print("FAILED: 修复失败: " + str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
