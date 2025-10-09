#!/usr/bin/env python
"""
快速修复导入错误脚本

修复测试中发现的缺失模块导入问题。
"""

import re
from pathlib import Path

fixes = [
    {
        'file': 'core/services/database_service.py',
        'old': 'from core.enhanced_asset_database_manager import EnhancedAssetDatabaseManager',
        'new': '# from core.enhanced_asset_database_manager import EnhancedAssetDatabaseManager  # 已合并到DatabaseService',
        'description': 'DatabaseService: 注释掉已合并的Manager导入'
    },
    {
        'file': 'core/services/performance_service.py',
        'old': 'from core.services.dynamic_resource_manager import DynamicResourceManager',
        'new': '# from core.services.dynamic_resource_manager import DynamicResourceManager  # 已集成到PerformanceService',
        'description': 'PerformanceService: 注释掉已集成的Manager导入'
    },
    {
        'file': 'core/services/network_service.py',
        'old': 'from core.network.universal_network_config import UniversalNetworkConfigManager',
        'new': '# from core.network.universal_network_config import UniversalNetworkConfigManager  # 已集成到NetworkService',
        'description': 'NetworkService: 注释掉已集成的Manager导入'
    },
]


def apply_fix(fix_info):
    """应用单个修复"""
    file_path = Path(fix_info['file'])

    if not file_path.exists():
        print(f"⚠ 文件不存在: {file_path}")
        return False

    try:
        content = file_path.read_text(encoding='utf-8')

        if fix_info['old'] not in content:
            print(f"⚠ 未找到待替换内容: {fix_info['description']}")
            return False

        new_content = content.replace(fix_info['old'], fix_info['new'])
        file_path.write_text(new_content, encoding='utf-8')

        print(f"✓ {fix_info['description']}")
        return True

    except Exception as e:
        print(f"✗ 错误: {fix_info['file']} - {e}")
        return False


def main():
    print("="*60)
    print("快速修复导入错误")
    print("="*60)

    success_count = 0
    for fix in fixes:
        if apply_fix(fix):
            success_count += 1

    print("\n" + "="*60)
    print(f"完成: {success_count}/{len(fixes)} 修复成功")
    print("="*60)

    return success_count


if __name__ == "__main__":
    main()
