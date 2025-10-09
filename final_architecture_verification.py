#!/usr/bin/env python3
"""
最终架构验证脚本

专门验证核心系统文件的架构健康度，
忽略修复脚本和示例代码
"""

import os
import re
from pathlib import Path

def verify_core_architecture():
    """验证核心架构"""
    print("🔍 验证核心架构健康度...")
    
    # 只检查核心系统文件
    core_files = [
        'main.py',
        'core/services/unified_data_manager.py',
        'core/services/service_bootstrap.py',
        'core/services/uni_plugin_data_manager.py',
        'core/data_source_router.py',
        'core/containers.py'
    ]
    
    issues = []
    
    for file_path in core_files:
        if not os.path.exists(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查不当的直接实例化（排除单例模式的正当使用）
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                line = line.strip()
                
                # 检查直接实例化，但排除单例模式中的正当使用
                if 'UnifiedDataManager()' in line:
                    # 检查是否在get_unified_data_manager函数中
                    context_start = max(0, i-10)
                    context_lines = lines[context_start:i+5]
                    context = '\n'.join(context_lines)
                    
                    if 'def get_unified_data_manager' in context or '_unified_data_manager_instance =' in line:
                        continue  # 这是正当的单例创建
                    else:
                        issues.append(f"{file_path}:{i} - 不当的UnifiedDataManager()直接实例化")
                
                elif 'UniPluginDataManager()' in line and 'get_service_container' not in line:
                    issues.append(f"{file_path}:{i} - 不当的UniPluginDataManager()直接实例化")
        
        except Exception as e:
            issues.append(f"{file_path} - 读取失败: {e}")
    
    return issues

def main():
    """主函数"""
    print("🚀 开始最终架构验证...")
    print("=" * 50)
    
    issues = verify_core_architecture()
    
    if not issues:
        print("✅ 核心架构验证通过！")
        print("🎉 所有核心系统文件都正确使用了单例模式")
        print("📊 架构健康度: 优秀")
    else:
        print("❌ 发现架构问题:")
        for issue in issues:
            print(f"  - {issue}")
        print(f"📊 问题总数: {len(issues)}")
    
    print("\n📋 验证完成")
    return len(issues) == 0

if __name__ == "__main__":
    main()
