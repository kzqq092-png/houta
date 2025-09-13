#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终的print语句到Loguru迁移工具
"""

import os
import re

def migrate_print_to_loguru():
    """迁移print语句到loguru"""
    
    # 重要业务模块中需要迁移的print模式
    migration_rules = [
        # 错误相关
        ('print(f".*?失败.*?{.*?}")', 'logger.error'),
        ('print(f".*?错误.*?{.*?}")', 'logger.error'),
        ('print(f".*?异常.*?{.*?}")', 'logger.error'),
        ('print(".*?失败.*?")', 'logger.error'),
        ('print(".*?错误.*?")', 'logger.error'),
        
        # 警告相关
        ('print(f?".*?警告.*?")', 'logger.warning'),
        ('print(f?".*?Warning.*?")', 'logger.warning'),
        ('print("WARNING:.*?")', 'logger.warning'),
        
        # 信息相关
        ('print(f?".*?成功.*?")', 'logger.info'),
        ('print(f?".*?完成.*?")', 'logger.info'),
        ('print(f?".*?初始化.*?")', 'logger.info'),
        ('print(f?".*?启动.*?")', 'logger.info'),
        
        # 调试相关
        ('print(f?".*?调试.*?")', 'logger.debug'),
        ('print(f?".*?Debug.*?")', 'logger.debug'),
    ]
    
    # 需要处理的重要文件
    important_files = [
        'core/ui/panels/bottom_panel.py',
        'core/importdata/import_config_manager.py', 
        'utils/cache.py',
        'gui/widgets/log_widget_loguru.py',
        'gui/dialogs/database_admin_dialog.py',
        'gui/dialogs/version_manager_dialog.py',
        'components/fund_flow.py',
        'signals/signal_filters.py'
    ]
    
    for file_path in important_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                changes_made = False
                
                # 确保有loguru导入
                if 'from loguru import logger' not in content and 'import logger' not in content:
                    lines = content.split('\n')
                    # 在适当位置插入导入
                    for i, line in enumerate(lines):
                        if line.startswith('from ') or line.startswith('import '):
                            continue
                        elif line.strip() == '':
                            lines.insert(i, 'from loguru import logger')
                            content = '\n'.join(lines)
                            changes_made = True
                            break
                
                # 简单替换常见模式
                replacements = [
                    ('print(f"UI日志处理错误: {e}")', 'logger.error(f"UI日志处理错误: {e}")'),
                    ('print("WARNING: diskcache 不可用，使用内存缓存")', 'logger.warning("diskcache 不可用，使用内存缓存")'),
                    ('print(f"获取表描述失败: {e}")', 'logger.error(f"获取表描述失败: {e}")'),
                    ('print(f"保存表描述失败: {e}")', 'logger.error(f"保存表描述失败: {e}")'),
                    ('print("警告：版本管理后端系统不可用，将使用模拟数据")', 'logger.warning("版本管理后端系统不可用，将使用模拟数据")'),
                    ('print("统计信息:", json.dumps(stats, ensure_ascii=False, indent=2))', 'logger.info(f"统计信息: {json.dumps(stats, ensure_ascii=False, indent=2)}")'),
                    ('print("警告: 未找到概率列 (buy_prob, sell_prob), 无法按强度过滤信号")', 'logger.warning("未找到概率列 (buy_prob, sell_prob), 无法按强度过滤信号")'),
                ]
                
                for old, new in replacements:
                    if old in content:
                        content = content.replace(old, new)
                        changes_made = True
                
                if changes_made:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ 已更新: {file_path}")
                
            except Exception as e:
                print(f"❌ 处理失败 {file_path}: {e}")

if __name__ == "__main__":
    print("🔧 开始最终的print到Loguru迁移...")
    migrate_print_to_loguru()
    print("✅ 迁移完成！")