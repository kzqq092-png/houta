#!/usr/bin/env python3
"""
总验证脚本 - 运行所有验证和回归测试

执行所有验证脚本，汇总结果
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_script(script_name, timeout=300):
    """运行验证脚本"""
    print(f"\n{'='*80}")
    print(f"运行: {script_name}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / script_name)],
            timeout=timeout,
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"❌ {script_name} 超时")
        return False
    except Exception as e:
        print(f"❌ {script_name} 执行失败: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("实时写入功能 - 总验证脚本")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 定义验证脚本
    scripts = [
        ("verify_integration.py", 300, "快速集成检查"),
        ("auto_validation_regression.py", 600, "自动验证和回归测试"),
    ]
    
    results = []
    
    for script, timeout, desc in scripts:
        print(f"\n[{len(results)+1}/{len(scripts)}] {desc}...")
        success = run_script(script, timeout)
        results.append((script, desc, success))
        
        if not success:
            print(f"\n⚠️  {script} 未通过，建议检查输出信息")
    
    # 汇总结果
    print("\n" + "="*80)
    print("验证结果汇总")
    print("="*80 + "\n")
    
    passed = sum(1 for _, _, result in results if result)
    total = len(results)
    
    for script, desc, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {desc}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n✅ 所有验证通过！")
        print("\n系统已准备好进入 Phase 4 功能测试:")
        print("  1. 小规模导入测试 (5-10 只股票)")
        print("  2. 事件流程验证")
        print("  3. 数据库完整性检查")
        print("  4. 性能测试")
        print("\n参考文档: EXECUTION_STRATEGY_PHASE4_5.md")
        return 0
    else:
        print(f"\n❌ 有 {total - passed} 个验证未通过")
        print("\n建议:")
        print("  1. 查看上面的输出信息")
        print("  2. 逐个脚本运行进行调试")
        print("  3. 参考故障排查指南: PHASE4_IMPLEMENTATION_PLAN.md")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
