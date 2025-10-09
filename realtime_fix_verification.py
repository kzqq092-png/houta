#!/usr/bin/env python3
"""
实时修复验证脚本
只分析最近启动后的日志，验证修复效果
"""

import os
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import subprocess


class RealtimeFixVerifier:
    """实时修复验证器"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.log_file = self.project_root / "logs" / f"factorweave_{datetime.now().strftime('%Y-%m-%d')}.log"

    def find_latest_startup_time(self) -> datetime:
        """找到最新的系统启动时间"""
        if not self.log_file.exists():
            return datetime.now() - timedelta(minutes=5)

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 从后往前查找最新的系统启动标记
            for line in reversed(lines):
                if '系统启动' in line or 'FactorWeave-Quant 系统启动' in line:
                    # 提取时间戳
                    time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if time_match:
                        time_str = time_match.group(1)
                        return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')

            # 如果没找到启动标记，返回5分钟前
            return datetime.now() - timedelta(minutes=5)

        except Exception as e:
            print(f"⚠️ 查找启动时间失败: {e}")
            return datetime.now() - timedelta(minutes=5)

    def get_logs_since_startup(self) -> str:
        """获取最新启动后的日志"""
        startup_time = self.find_latest_startup_time()
        print(f"📅 最新启动时间: {startup_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.log_file.exists():
            print("❌ 日志文件不存在")
            return ""

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 过滤出启动后的日志
            recent_lines = []
            for line in lines:
                # 提取时间戳
                time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if time_match:
                    line_time = datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S')
                    if line_time >= startup_time:
                        recent_lines.append(line)

            recent_content = ''.join(recent_lines)
            print(f"📊 分析最近 {len(recent_lines)} 行日志")
            return recent_content

        except Exception as e:
            print(f"❌ 读取日志失败: {e}")
            return ""

    def analyze_recent_logs(self) -> Dict[str, int]:
        """分析最近的日志"""
        print("🔍 分析最新启动后的日志...")

        content = self.get_logs_since_startup()
        if not content:
            return {}

        # 分析模式
        patterns = {
            'ai_prediction_warnings': r'不支持的预测类型.*risk_forecast',
            'performance_errors': r'收集系统指标失败.*argument 1.*impossible.*bad format char',
            'service_registrations': r'服务.*注册.*完成',
            'plugin_loads': r'插件.*加载.*成功',
            'unicode_errors': r'UnicodeEncodeError',
            'format_errors': r'bad format char',
            'warning_messages': r'WARNING',
            'error_messages': r'ERROR',
            'info_messages': r'INFO'
        }

        results = {}
        for pattern_name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            results[pattern_name] = len(matches)

        return results

    def verify_fixes_realtime(self) -> Dict[str, any]:
        """实时验证修复效果"""
        print("🚀 开始实时修复验证...")
        print("=" * 50)

        # 分析最新日志
        log_analysis = self.analyze_recent_logs()

        if not log_analysis:
            print("⚠️ 没有找到最新的日志数据")
            return {'status': 'no_data'}

        # 验证结果
        results = {
            'ai_fix_success': log_analysis.get('ai_prediction_warnings', 0) <= 1,  # 允许1个启动时的警告
            'performance_fix_success': log_analysis.get('performance_errors', 0) == 0,
            'unicode_fix_success': log_analysis.get('unicode_errors', 0) == 0,
            'overall_health': 'excellent'
        }

        # 计算总体健康状态
        total_errors = (
            log_analysis.get('ai_prediction_warnings', 0) +
            log_analysis.get('performance_errors', 0) +
            log_analysis.get('unicode_errors', 0)
        )

        if total_errors == 0:
            results['overall_health'] = 'excellent'
        elif total_errors <= 3:
            results['overall_health'] = 'good'
        elif total_errors <= 10:
            results['overall_health'] = 'fair'
        else:
            results['overall_health'] = 'poor'

        # 显示结果
        print("\n📊 实时验证结果:")
        print(f"   AI预测警告: {log_analysis.get('ai_prediction_warnings', 0)} 个 {'✅' if results['ai_fix_success'] else '❌'}")
        print(f"   性能收集错误: {log_analysis.get('performance_errors', 0)} 个 {'✅' if results['performance_fix_success'] else '❌'}")
        print(f"   Unicode错误: {log_analysis.get('unicode_errors', 0)} 个 {'✅' if results['unicode_fix_success'] else '❌'}")
        print(f"   总体健康状态: {results['overall_health'].upper()}")

        print("\n📈 日志统计:")
        print(f"   INFO消息: {log_analysis.get('info_messages', 0)} 个")
        print(f"   WARNING消息: {log_analysis.get('warning_messages', 0)} 个")
        print(f"   ERROR消息: {log_analysis.get('error_messages', 0)} 个")
        print(f"   服务注册: {log_analysis.get('service_registrations', 0)} 个")
        print(f"   插件加载: {log_analysis.get('plugin_loads', 0)} 个")

        results['log_analysis'] = log_analysis
        return results

    def monitor_realtime(self, duration_seconds: int = 60):
        """实时监控修复效果"""
        print(f"🔄 开始实时监控 ({duration_seconds}秒)...")

        start_time = time.time()
        check_interval = 10  # 每10秒检查一次

        while time.time() - start_time < duration_seconds:
            print(f"\n⏰ 监控时间: {int(time.time() - start_time)}秒")

            # 获取最新日志
            content = self.get_logs_since_startup()

            # 检查最近10秒的新日志
            recent_warnings = len(re.findall(r'不支持的预测类型.*risk_forecast', content[-1000:]))  # 检查最后1000字符
            recent_errors = len(re.findall(r'收集系统指标失败.*argument 1', content[-1000:]))

            if recent_warnings > 0:
                print(f"   ⚠️ 发现 {recent_warnings} 个新的AI预测警告")
            if recent_errors > 0:
                print(f"   ❌ 发现 {recent_errors} 个新的性能收集错误")
            if recent_warnings == 0 and recent_errors == 0:
                print(" ✅ 没有发现新的问题")

            time.sleep(check_interval)

        print(f"\n🎉 监控完成! 总监控时间: {duration_seconds}秒")


def main():
    """主函数"""
    print("HIkyuu-UI 实时修复验证工具")
    print("=" * 40)

    verifier = RealtimeFixVerifier()

    try:
        # 进行实时验证
        results = verifier.verify_fixes_realtime()

        if results.get('status') == 'no_data':
            print("⚠️ 无法获取日志数据，请确保程序正在运行")
            return

        # 判断修复是否成功
        all_fixes_success = (
            results['ai_fix_success'] and
            results['performance_fix_success'] and
            results['unicode_fix_success']
        )

        print("\n" + "=" * 50)
        if all_fixes_success:
            print("🎉 修复验证成功！所有问题都已解决！")
        else:
            print("⚠️ 部分修复成功，建议继续监控")

        print(f"系统健康状态: {results['overall_health'].upper()}")

        # 询问是否进行实时监控
        print("\n是否进行60秒实时监控? (y/N): ", end="")
        try:
            response = input().lower()
            if response == 'y':
                verifier.monitor_realtime(60)
        except KeyboardInterrupt:
            print("\n监控已取消")

    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
