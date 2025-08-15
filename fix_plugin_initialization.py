#!/usr/bin/env python3
"""
批量修复插件初始化问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def fix_plugin_initialization(plugin_file: Path):
    """修复插件的初始化问题"""
    try:
        with open(plugin_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有initialize方法
        if 'def initialize(self, config: Dict[str, Any]) -> bool:' not in content:
            print(f"⚠️ {plugin_file.name}: 没有标准initialize方法")
            return False

        # 检查是否已经设置了initialized = True
        if 'self.initialized = True' in content:
            print(f"✅ {plugin_file.name}: 已正确设置initialized")
            return True

        # 查找需要修复的模式
        patterns_to_fix = [
            # 模式1: 简单的返回True但没有设置initialized
            {
                'old': '''            # 可以在这里处理配置参数
            if hasattr(self, 'configure_api') and 'api_key' in config:
                self.configure_api(config.get('api_key', ''))
            return True''',
                'new': '''            # 可以在这里处理配置参数
            if hasattr(self, 'configure_api') and 'api_key' in config:
                self.configure_api(config.get('api_key', ''))
            
            # 设置初始化状态
            self.initialized = True
            return True'''
            },
            # 模式2: 其他类似的模式
            {
                'old': '''            # 初始化完成
            return True''',
                'new': '''            # 初始化完成
            self.initialized = True
            return True'''
            },
            # 模式3: 直接返回True的情况
            {
                'old': '''        try:
            return True
        except Exception as e:''',
                'new': '''        try:
            self.initialized = True
            return True
        except Exception as e:'''
            }
        ]

        modified = False
        for pattern in patterns_to_fix:
            if pattern['old'] in content:
                content = content.replace(pattern['old'], pattern['new'])
                modified = True
                break

        # 特殊处理：如果initialize方法很简单，直接在return True前添加
        if not modified and 'return True' in content and 'def initialize(' in content:
            # 查找initialize方法中的return True
            lines = content.split('\n')
            new_lines = []
            in_initialize = False

            for i, line in enumerate(lines):
                if 'def initialize(self, config: Dict[str, Any]) -> bool:' in line:
                    in_initialize = True
                elif in_initialize and line.strip().startswith('def ') and 'initialize' not in line:
                    in_initialize = False

                if in_initialize and 'return True' in line and 'self.initialized = True' not in lines[max(0, i-3):i]:
                    # 在return True前添加self.initialized = True
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + 'self.initialized = True')
                    modified = True

                new_lines.append(line)

            if modified:
                content = '\n'.join(new_lines)

        if modified:
            with open(plugin_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ {plugin_file.name}: 已修复初始化问题")
            return True
        else:
            print(f"⚠️ {plugin_file.name}: 未找到需要修复的模式")
            return False

    except Exception as e:
        print(f"❌ {plugin_file.name}: 修复失败 - {e}")
        return False


def main():
    """主函数"""
    print("🔧 批量修复插件初始化问题...")

    plugin_dir = Path('plugins/examples')

    # 需要修复的插件列表（基于测试结果）
    problem_plugins = [
        'okx_crypto_plugin.py',
        'coinbase_crypto_plugin.py',
        'custom_data_plugin.py',
        # 其他可能需要修复的插件
    ]

    success_count = 0
    for plugin_name in problem_plugins:
        plugin_file = plugin_dir / plugin_name
        if plugin_file.exists():
            if fix_plugin_initialization(plugin_file):
                success_count += 1
        else:
            print(f"❌ {plugin_name}: 文件不存在")

    print(f"\n📊 修复完成: {success_count}/{len(problem_plugins)} 个插件")

    return success_count


if __name__ == "__main__":
    success_count = main()
    print(f"\n🎉 成功修复 {success_count} 个插件的初始化问题！")
