#!/usr/bin/env python3
"""
快速修复检查脚本
"""

import re
from pathlib import Path
from datetime import datetime, timedelta


def quick_check():
    """快速检查修复效果"""
    log_file = Path("logs") / f"factorweave_{datetime.now().strftime('%Y-%m-%d')}.log"

    if not log_file.exists():
        print("❌ 日志文件不存在")
        return

    print("🔍 快速检查修复效果...")

    # 读取最后1000行日志
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 取最后1000行
        recent_lines = lines[-1000:] if len(lines) > 1000 else lines
        content = ''.join(recent_lines)

        # 检查问题
        ai_warnings = len(re.findall(r'不支持的预测类型.*risk_forecast', content))
        perf_errors = len(re.findall(r'收集系统指标失败.*argument 1', content))
        unicode_errors = len(re.findall(r'UnicodeEncodeError', content))

        print(f"📊 最近1000行日志分析:")
        print(f"   AI预测警告: {ai_warnings} 个")
        print(f"   性能收集错误: {perf_errors} 个")
        print(f"   Unicode错误: {unicode_errors} 个")

        # 判断修复效果
        if ai_warnings == 0 and perf_errors == 0 and unicode_errors == 0:
            print("\n🎉 修复验证成功！没有发现问题！")
        elif ai_warnings <= 2 and perf_errors == 0 and unicode_errors == 0:
            print("\n✅ 修复基本成功！AI预测警告已大幅减少！")
        else:
            print("\n⚠️ 仍有一些问题需要关注")

        # 检查最新的几行日志
        print(f"\n📋 最新5行日志:")
        for line in recent_lines[-5:]:
            if line.strip():
                print(f"   {line.strip()}")

    except Exception as e:
        print(f"❌ 检查失败: {e}")


if __name__ == "__main__":
    quick_check()
