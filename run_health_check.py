#!/usr/bin/env python3
"""
临时脚本：运行系统健康检查
"""

from utils.system_health_checker import run_system_health_check
import json


def main():
    print('开始运行系统健康检查...')
    try:
        result = run_system_health_check('.')
        print('\n=== 系统健康检查报告 ===')
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 生成简化报告
        print('\n=== 简化报告 ===')
        print(f"循环导入检查: {'通过' if not result.get('circular_imports', {}).get('cycles') else '发现问题'}")
        print(f"重复函数检查: {'通过' if not result.get('duplicate_functions', {}).get('duplicates') else '发现问题'}")
        print(f"弃用功能检查: {'通过' if not result.get('deprecated_usage', {}).get('deprecated_calls') else '发现问题'}")
        print(f"性能问题检查: {'通过' if not result.get('performance_issues', {}).get('issues') else '发现问题'}")
        print(f"代码质量检查: {'通过' if not result.get('code_quality', {}).get('issues') else '发现问题'}")

        # 显示推荐
        recommendations = result.get('recommendations', [])
        if recommendations:
            print('\n=== 改进建议 ===')
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")

    except Exception as e:
        print(f'健康检查失败: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
