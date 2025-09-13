#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用MCP工具进行print语句到Loguru的迁移
"""

import os
import re
from typing import List, Dict, Tuple

class PrintToLoguruMigrator:
    """print语句到Loguru的迁移工具"""
    
    def __init__(self):
        self.business_modules = [
            'core/',
            'components/', 
            'gui/',
            'optimization/',
            'models/',
            'analysis/',
            'signals/',
            'utils/',
            'backtest/',
            'evaluation/'
        ]
        
        self.exclude_patterns = [
            'backup_',
            '.backup',
            'backup2',
            'backup3',
            'examples/',
            'docs/',
            'scripts/',
            'tests/',
            'README.md',
            'quick_start.py',  # 可能需要保留命令行输出
            'plugins/examples/',
            '历史方案文档/'
        ]
        
        self.migration_patterns = [
            # 错误信息 print
            (r'print\(f?"UI日志处理错误: {.*?}"\)', r'logger.error(f"UI日志处理错误: {e}")'),
            (r'print\(f?"错误: {.*?}"\)', r'logger.error(f"错误: {e}")'),
            (r'print\(f?".*?失败.*?{.*?}"\)', r'logger.error(f"\1")'),
            
            # 信息类 print
            (r'print\(f?".*?成功.*?"\)', r'logger.info(f"\1")'),
            (r'print\(f?".*?完成.*?"\)', r'logger.info(f"\1")'),
            (r'print\(f?".*?启动.*?"\)', r'logger.info(f"\1")'),
            (r'print\(f?".*?初始化.*?"\)', r'logger.info(f"\1")'),
            
            # 调试信息 print
            (r'print\(f?"调试.*?"\)', r'logger.debug(f"\1")'),
            (r'print\(f?"Debug.*?"\)', r'logger.debug(f"\1")'),
            (r'print\(f?"测试.*?"\)', r'logger.debug(f"\1")'),
            
            # 警告信息 print
            (r'print\(f?"警告.*?"\)', r'logger.warning(f"\1")'),
            (r'print\(f?"Warning.*?"\)', r'logger.warning(f"\1")'),
            
            # 一般信息 print
            (r'print\(f?"([^"]*?)"\)', r'logger.info(f"\1")'),
            (r"print\(f?'([^']*)'\)", r"logger.info(f'\1')"),
            (r'print\(([^)]+)\)', r'logger.info(\1)'),
        ]
    
    def should_migrate_file(self, file_path: str) -> bool:
        """判断文件是否需要迁移"""
        # 检查是否在业务模块中
        is_business_module = any(file_path.startswith(module) for module in self.business_modules)
        
        # 检查是否在排除列表中
        is_excluded = any(pattern in file_path for pattern in self.exclude_patterns)
        
        return is_business_module and not is_excluded and file_path.endswith('.py')
    
    def find_print_statements(self, file_path: str) -> List[Tuple[int, str]]:
        """查找文件中的print语句"""
        print_statements = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                if 'print(' in line and not line.strip().startswith('#'):
                    print_statements.append((i, line.strip()))
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
        
        return print_statements
    
    def migrate_file(self, file_path: str) -> bool:
        """迁移单个文件的print语句"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 确保导入了loguru
            if 'from loguru import logger' not in content and 'import logger' not in content:
                # 在文件开始添加导入
                lines = content.split('\n')
                insert_index = 0
                
                # 找到合适的插入位置（在其他导入之后）
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        insert_index = i + 1
                    elif line.strip() == '' and insert_index > 0:
                        break
                
                lines.insert(insert_index, 'from loguru import logger')
                content = '\n'.join(lines)
            
            # 应用迁移模式
            for pattern, replacement in self.migration_patterns:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            
            # 特殊处理：UI日志处理错误
            content = content.replace(
                'print(f"UI日志处理错误: {e}")',
                'logger.error(f"UI日志处理错误: {e}")'
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
                
        except Exception as e:
            print(f"迁移文件失败 {file_path}: {e}")
        
        return False
    
    def analyze_print_usage(self) -> Dict[str, List[Tuple[int, str]]]:
        """分析系统中的print使用情况"""
        print_usage = {}
        
        for root, dirs, files in os.walk('.'):
            # 过滤目录
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self.exclude_patterns)]
            
            for file in files:
                file_path = os.path.join(root, file).replace('\\', '/').lstrip('./')
                
                if self.should_migrate_file(file_path):
                    print_statements = self.find_print_statements(file_path)
                    if print_statements:
                        print_usage[file_path] = print_statements
        
        return print_usage
    
    def migrate_all(self) -> Dict[str, int]:
        """迁移所有需要的print语句"""
        results = {
            'analyzed': 0,
            'migrated': 0,
            'failed': 0
        }
        
        print_usage = self.analyze_print_usage()
        results['analyzed'] = len(print_usage)
        
        print("🔍 发现需要迁移的文件和print语句:")
        for file_path, statements in print_usage.items():
            print(f"\n📁 {file_path} ({len(statements)} 个print语句):")
            for line_num, statement in statements[:3]:  # 只显示前3个
                print(f"  L{line_num}: {statement}")
            if len(statements) > 3:
                print(f"  ... 还有 {len(statements) - 3} 个")
        
        print("\n🔧 开始迁移...")
        for file_path in print_usage.keys():
            try:
                if self.migrate_file(file_path):
                    print(f"✅ 迁移成功: {file_path}")
                    results['migrated'] += 1
                else:
                    print(f"⏭️  无需迁移: {file_path}")
            except Exception as e:
                print(f"❌ 迁移失败: {file_path} - {e}")
                results['failed'] += 1
        
        return results

def main():
    """主函数"""
    print("🚀 使用MCP工具进行print到Loguru迁移...")
    
    migrator = PrintToLoguruMigrator()
    results = migrator.migrate_all()
    
    print(f"\n📊 迁移结果:")
    print(f"分析文件数: {results['analyzed']}")
    print(f"成功迁移: {results['migrated']}")
    print(f"失败数量: {results['failed']}")
    
    success_rate = (results['migrated'] / results['analyzed'] * 100) if results['analyzed'] > 0 else 0
    print(f"成功率: {success_rate:.1f}%")
    
    if results['migrated'] > 0:
        print("\n✅ 部分文件已迁移到Loguru日志系统")
    else:
        print("\n🎉 所有重要的print语句都已经迁移到Loguru！")

if __name__ == "__main__":
    main()