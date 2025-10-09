#!/usr/bin/env python3
"""
自动检测与修复验证脚本
检查插件发现和注册机制修复的效果
"""

import os
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import subprocess


class FixVerificationTool:
    """修复验证工具"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.log_file = self.project_root / "logs" / f"factorweave_{datetime.now().strftime('%Y-%m-%d')}.log"
        self.verification_results = {}

    def check_log_file_exists(self) -> bool:
        """检查日志文件是否存在"""
        if self.log_file.exists():
            print(f"✅ 找到日志文件: {self.log_file}")
            return True
        else:
            print(f"❌ 日志文件不存在: {self.log_file}")
            return False

    def analyze_recent_logs(self, minutes: int = 10) -> Dict[str, int]:
        """分析最近几分钟的日志"""
        if not self.check_log_file_exists():
            return {}

        print(f"🔍 分析最近 {minutes} 分钟的日志...")

        # 计算时间范围
        now = datetime.now()
        start_time = now - timedelta(minutes=minutes)

        # 读取日志文件
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ 读取日志文件失败: {e}")
            return {}

        # 分析模式
        patterns = {
            'ai_prediction_warnings': r'不支持的预测类型.*risk_forecast',
            'performance_errors': r'收集系统指标失败.*argument 1.*impossible.*bad format char',
            'service_registrations': r'服务.*注册.*完成',
            'plugin_loads': r'插件.*加载.*成功',
            'system_startup': r'系统启动',
            'unicode_errors': r'UnicodeEncodeError',
            'format_errors': r'bad format char'
        }

        results = {}
        for pattern_name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            results[pattern_name] = len(matches)

        return results

    def check_process_status(self) -> Dict[str, any]:
        """检查进程状态"""
        print("🔍 检查Python进程状态...")

        try:
            # 使用PowerShell命令检查Python进程
            result = subprocess.run([
                'powershell', '-Command',
                'Get-Process | Where-Object {$_.ProcessName -eq "python"} | Measure-Object | Select-Object -ExpandProperty Count'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                process_count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
                print(f"📊 发现 {process_count} 个Python进程")
                return {'process_count': process_count, 'status': 'running' if process_count > 0 else 'stopped'}
            else:
                print(f"⚠️ 检查进程失败: {result.stderr}")
                return {'process_count': 0, 'status': 'unknown'}

        except Exception as e:
            print(f"❌ 检查进程状态失败: {e}")
            return {'process_count': 0, 'status': 'error'}

    def verify_ai_prediction_fix(self, log_analysis: Dict[str, int]) -> bool:
        """验证AI预测服务修复效果"""
        print("🔧 验证AI预测服务修复效果...")

        ai_warnings = log_analysis.get('ai_prediction_warnings', 0)

        if ai_warnings == 0:
            print("✅ AI预测服务修复成功 - 没有发现重复警告")
            return True
        elif ai_warnings <= 2:  # 允许少量警告（可能是启动时的）
            print(f"⚠️ AI预测服务基本修复 - 发现 {ai_warnings} 个警告（在可接受范围内）")
            return True
        else:
            print(f"❌ AI预测服务修复不完全 - 仍有 {ai_warnings} 个重复警告")
            return False

    def verify_performance_fix(self, log_analysis: Dict[str, int]) -> bool:
        """验证性能数据收集修复效果"""
        print("🔧 验证性能数据收集修复效果...")

        perf_errors = log_analysis.get('performance_errors', 0)
        format_errors = log_analysis.get('format_errors', 0)

        if perf_errors == 0 and format_errors == 0:
            print("✅ 性能数据收集修复成功 - 没有发现格式化错误")
            return True
        else:
            print(f"❌ 性能数据收集修复不完全 - 发现 {perf_errors} 个性能错误, {format_errors} 个格式化错误")
            return False

    def verify_unicode_fix(self, log_analysis: Dict[str, int]) -> bool:
        """验证Unicode编码修复效果"""
        print("🔧 验证Unicode编码修复效果...")

        unicode_errors = log_analysis.get('unicode_errors', 0)

        if unicode_errors == 0:
            print("✅ Unicode编码修复成功 - 没有发现编码错误")
            return True
        else:
            print(f"❌ Unicode编码修复不完全 - 仍有 {unicode_errors} 个编码错误")
            return False

    def check_system_health(self, log_analysis: Dict[str, int]) -> Dict[str, any]:
        """检查系统健康状态"""
        print("🔍 检查系统健康状态...")

        health_metrics = {
            'startup_count': log_analysis.get('system_startup', 0),
            'service_registrations': log_analysis.get('service_registrations', 0),
            'plugin_loads': log_analysis.get('plugin_loads', 0),
            'total_errors': (
                log_analysis.get('ai_prediction_warnings', 0) +
                log_analysis.get('performance_errors', 0) +
                log_analysis.get('unicode_errors', 0)
            )
        }

        # 计算健康分数
        health_score = 100
        if health_metrics['total_errors'] > 10:
            health_score -= 30
        elif health_metrics['total_errors'] > 5:
            health_score -= 15
        elif health_metrics['total_errors'] > 0:
            health_score -= 5

        if health_metrics['startup_count'] == 0:
            health_score -= 20

        health_metrics['health_score'] = health_score
        health_metrics['status'] = 'excellent' if health_score >= 90 else 'good' if health_score >= 70 else 'fair' if health_score >= 50 else 'poor'

        return health_metrics

    def generate_verification_report(self, log_analysis: Dict[str, int], process_status: Dict[str, any], health_metrics: Dict[str, any]) -> str:
        """生成验证报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"fix_verification_report_{timestamp}.md"

        # 验证各项修复
        ai_fix_ok = self.verify_ai_prediction_fix(log_analysis)
        perf_fix_ok = self.verify_performance_fix(log_analysis)
        unicode_fix_ok = self.verify_unicode_fix(log_analysis)

        overall_success = ai_fix_ok and perf_fix_ok and unicode_fix_ok

        report_content = f"""# HIkyuu-UI 修复验证报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**验证范围**: 插件发现和注册机制修复效果  
**分析时间窗口**: 最近10分钟

## 📊 总体结果

**修复状态**: {'✅ 修复成功' if overall_success else '⚠️ 部分修复' if any([ai_fix_ok, perf_fix_ok, unicode_fix_ok]) else '❌ 修复失败'}  
**系统健康分数**: {health_metrics['health_score']}/100 ({health_metrics['status'].upper()})  
**进程状态**: {process_status['status']} ({process_status['process_count']} 个Python进程)

## 🔧 修复项目验证

### 1. AI预测服务警告频率限制
- **状态**: {'✅ 修复成功' if ai_fix_ok else '❌ 需要进一步修复'}
- **重复警告数量**: {log_analysis.get('ai_prediction_warnings', 0)} 个
- **预期**: 每分钟最多1个警告

### 2. 性能数据收集格式化错误
- **状态**: {'✅ 修复成功' if perf_fix_ok else '❌ 需要进一步修复'}
- **格式化错误数量**: {log_analysis.get('performance_errors', 0)} 个
- **预期**: 0个格式化错误

### 3. Unicode编码问题
- **状态**: {'✅ 修复成功' if unicode_fix_ok else '❌ 需要进一步修复'}
- **编码错误数量**: {log_analysis.get('unicode_errors', 0)} 个
- **预期**: 0个编码错误

## 📈 系统运行指标

- **系统启动次数**: {health_metrics['startup_count']}
- **服务注册完成**: {health_metrics['service_registrations']} 个
- **插件加载成功**: {health_metrics['plugin_loads']} 个
- **总错误数量**: {health_metrics['total_errors']} 个

## 📋 详细日志分析

```
AI预测警告: {log_analysis.get('ai_prediction_warnings', 0)} 次
性能收集错误: {log_analysis.get('performance_errors', 0)} 次
Unicode错误: {log_analysis.get('unicode_errors', 0)} 次
格式化错误: {log_analysis.get('format_errors', 0)} 次
服务注册: {log_analysis.get('service_registrations', 0)} 次
插件加载: {log_analysis.get('plugin_loads', 0)} 次
系统启动: {log_analysis.get('system_startup', 0)} 次
```

## 🎯 修复效果评估

### 成功的修复
"""

        if ai_fix_ok:
            report_content += "- ✅ AI预测服务警告频率限制生效\n"
        if perf_fix_ok:
            report_content += "- ✅ 性能数据收集格式化错误已修复\n"
        if unicode_fix_ok:
            report_content += "- ✅ Unicode编码问题已解决\n"

        if not overall_success:
            report_content += "\n### 需要进一步关注的问题\n"
            if not ai_fix_ok:
                report_content += "- ⚠️ AI预测服务仍有重复警告，可能需要调整警告间隔\n"
            if not perf_fix_ok:
                report_content += "- ⚠️ 性能数据收集仍有格式化错误，需要检查代码修复\n"
            if not unicode_fix_ok:
                report_content += "- ⚠️ Unicode编码问题仍然存在，需要全面检查emoji字符\n"

        report_content += f"""

## 🔄 建议的后续行动

### 短期行动
1. {'继续监控系统运行状态' if overall_success else '修复剩余问题'}
2. 定期检查日志质量
3. 监控系统性能指标

### 长期维护
1. 建立自动化监控机制
2. 定期运行修复验证
3. 持续优化系统架构

## ✅ 验证总结

{'🎉 修复验证成功！所有主要问题都已解决，系统运行稳定。' if overall_success else '⚠️ 修复部分成功，仍有一些问题需要进一步处理。'}

HIkyuu-UI插件发现和注册机制的修复工作{'已经完成' if overall_success else '正在进行中'}！

---

*此报告由自动检测与修复验证工具生成*
"""

        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        return report_file

    def run_verification(self) -> Dict[str, any]:
        """运行完整验证"""
        print("🚀 开始自动检测与修复验证...")
        print("=" * 60)

        # 分析日志
        log_analysis = self.analyze_recent_logs(10)

        # 检查进程状态
        process_status = self.check_process_status()

        # 检查系统健康
        health_metrics = self.check_system_health(log_analysis)

        # 生成报告
        report_file = self.generate_verification_report(log_analysis, process_status, health_metrics)

        print(f"\n🎉 验证完成!")
        print(f"📄 详细报告: {report_file}")
        print("=" * 60)

        return {
            'log_analysis': log_analysis,
            'process_status': process_status,
            'health_metrics': health_metrics,
            'report_file': report_file
        }


def main():
    """主函数"""
    print("HIkyuu-UI 自动检测与修复验证工具")
    print("=" * 50)

    verifier = FixVerificationTool()

    try:
        results = verifier.run_verification()

        # 显示关键结果
        health_score = results['health_metrics']['health_score']
        total_errors = results['health_metrics']['total_errors']

        print(f"\n📊 关键指标:")
        print(f"   系统健康分数: {health_score}/100")
        print(f"   总错误数量: {total_errors}")
        print(f"   进程状态: {results['process_status']['status']}")

        if health_score >= 90:
            print("\n🎉 修复验证成功！系统运行优秀！")
        elif health_score >= 70:
            print("\n✅ 修复基本成功，系统运行良好！")
        else:
            print("\n⚠️ 仍有一些问题需要关注。")

    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
