"""
HIkyuu量化交易系统健康检查器
监控形态识别系统的整体健康状态和性能指标
"""

from analysis.pattern_base import PatternAlgorithmFactory
from analysis.pattern_recognition import (
    EnhancedPatternRecognizer,
    get_performance_monitor,
    get_pattern_cache,
    get_pattern_recognizer_info
)
import os
import sys
import time
import psutil
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class SystemHealthChecker:
    """系统健康检查器 - 全面监控形态识别系统状态"""

    def __init__(self):
        self.check_results = {}
        self.start_time = datetime.now()

    def run_comprehensive_check(self) -> Dict[str, Any]:
        """运行全面的系统健康检查"""
        print("🔍 开始HIkyuu量化交易系统健康检查...")

        health_report = {
            'timestamp': datetime.now().isoformat(),
            'system_info': self._check_system_info(),
            'pattern_recognition': self._check_pattern_recognition(),
            'performance_metrics': self._check_performance_metrics(),
            'cache_system': self._check_cache_system(),
            'memory_usage': self._check_memory_usage(),
            'dependencies': self._check_dependencies(),
            'database_connectivity': self._check_database_connectivity(),
            'ui_components': self._check_ui_components(),
            'overall_health': 'unknown'
        }

        # 计算总体健康状态
        health_report['overall_health'] = self._calculate_overall_health(health_report)

        # 生成建议
        health_report['recommendations'] = self._generate_recommendations(health_report)

        print(f"✅ 系统健康检查完成，总体状态: {health_report['overall_health']}")

        return health_report

    def _check_system_info(self) -> Dict[str, Any]:
        """检查系统基本信息"""
        try:
            info = get_pattern_recognizer_info()
            return {
                'status': 'healthy',
                'version': info.get('version', 'unknown'),
                'supported_patterns': info.get('supported_patterns', 0),
                'features': {
                    'performance_optimized': info.get('performance_optimized', False),
                    'cache_enabled': info.get('cache_enabled', False),
                    'monitoring_enabled': info.get('monitoring_enabled', False),
                    'database_algorithms': info.get('database_algorithms', False),
                    'ml_predictions': info.get('ml_predictions', False)
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'details': traceback.format_exc()
            }

    def _check_pattern_recognition(self) -> Dict[str, Any]:
        """检查形态识别功能"""
        try:
            # 创建测试数据
            test_data = self._generate_test_kdata()

            # 测试识别器创建
            recognizer = EnhancedPatternRecognizer(debug_mode=False)

            # 测试形态识别
            start_time = time.time()
            patterns = recognizer.identify_patterns(test_data, confidence_threshold=0.1)
            processing_time = time.time() - start_time

            return {
                'status': 'healthy',
                'recognizer_created': True,
                'patterns_detected': len(patterns),
                'processing_time': processing_time,
                'test_data_size': len(test_data),
                'average_confidence': np.mean([p.get('confidence', 0) for p in patterns]) if patterns else 0
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'details': traceback.format_exc()
            }

    def _check_performance_metrics(self) -> Dict[str, Any]:
        """检查性能监控系统"""
        try:
            monitor = get_performance_monitor()
            summary = monitor.get_performance_summary()

            return {
                'status': 'healthy',
                'total_recognitions': summary.get('total_recognitions', 0),
                'success_rate': summary.get('success_rate', 0),
                'average_processing_time': summary.get('average_processing_time', 0),
                'cache_hit_rate': summary.get('cache_hit_rate', 0),
                'memory_usage_mb': summary.get('memory_usage_mb', 0),
                'recent_performance': summary.get('recent_performance', {})
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'details': traceback.format_exc()
            }

    def _check_cache_system(self) -> Dict[str, Any]:
        """检查缓存系统"""
        try:
            cache = get_pattern_cache()
            stats = cache.get_stats()

            return {
                'status': 'healthy',
                'cache_size': stats.get('cache_size', 0),
                'max_size': stats.get('max_size', 0),
                'hit_count': stats.get('hit_count', 0),
                'miss_count': stats.get('miss_count', 0),
                'hit_rate': stats.get('hit_rate', 0),
                'memory_usage_estimate': stats.get('memory_usage_estimate', 0),
                'utilization': stats.get('cache_size', 0) / stats.get('max_size', 1)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'details': traceback.format_exc()
            }

    def _check_memory_usage(self) -> Dict[str, Any]:
        """检查内存使用情况"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                'status': 'healthy',
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / 1024 / 1024,
                'total_mb': psutil.virtual_memory().total / 1024 / 1024
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'details': traceback.format_exc()
            }

    def _check_dependencies(self) -> Dict[str, Any]:
        """检查依赖库"""
        dependencies = {
            'pandas': 'pd',
            'numpy': 'np',
            'PyQt5': 'PyQt5',
            'psutil': 'psutil'
        }

        results = {}
        all_available = True

        for name, import_name in dependencies.items():
            try:
                __import__(import_name)
                results[name] = {'status': 'available', 'version': 'unknown'}

                # 尝试获取版本信息
                try:
                    module = sys.modules[import_name]
                    if hasattr(module, '__version__'):
                        results[name]['version'] = module.__version__
                except:
                    pass

            except ImportError as e:
                results[name] = {'status': 'missing', 'error': str(e)}
                all_available = False

        return {
            'status': 'healthy' if all_available else 'warning',
            'dependencies': results,
            'all_available': all_available
        }

    def _check_database_connectivity(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            # 检查数据库文件是否存在
            db_paths = [
                'db/pattern_algorithms.db',
                'db/hikyuu.db',
                'data/stock_data.db'
            ]

            db_status = {}
            for db_path in db_paths:
                if os.path.exists(db_path):
                    db_status[db_path] = {
                        'exists': True,
                        'size_mb': os.path.getsize(db_path) / 1024 / 1024,
                        'modified': datetime.fromtimestamp(os.path.getmtime(db_path)).isoformat()
                    }
                else:
                    db_status[db_path] = {'exists': False}

            return {
                'status': 'healthy',
                'databases': db_status
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'details': traceback.format_exc()
            }

    def _check_ui_components(self) -> Dict[str, Any]:
        """检查UI组件"""
        try:
            # 检查关键UI文件是否存在
            ui_files = [
                'gui/widgets/analysis_tabs/pattern_tab_pro.py',
                'gui/widgets/analysis_tabs/pattern_tab.py',
                'gui/widgets/base_analysis_tab.py'
            ]

            ui_status = {}
            for ui_file in ui_files:
                if os.path.exists(ui_file):
                    ui_status[ui_file] = {
                        'exists': True,
                        'size_kb': os.path.getsize(ui_file) / 1024,
                        'modified': datetime.fromtimestamp(os.path.getmtime(ui_file)).isoformat()
                    }
                else:
                    ui_status[ui_file] = {'exists': False}

            return {
                'status': 'healthy',
                'ui_files': ui_status
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'details': traceback.format_exc()
            }

    def _generate_test_kdata(self) -> pd.DataFrame:
        """生成测试K线数据"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')

        # 生成模拟价格数据
        np.random.seed(42)
        base_price = 100
        price_changes = np.random.normal(0, 2, 100)
        prices = [base_price]

        for change in price_changes[1:]:
            new_price = max(prices[-1] + change, 1)  # 确保价格为正
            prices.append(new_price)

        # 创建OHLC数据
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            high = close + abs(np.random.normal(0, 1))
            low = close - abs(np.random.normal(0, 1))
            open_price = close + np.random.normal(0, 0.5)

            data.append({
                'date': date,
                'open': open_price,
                'high': max(open_price, high, close),
                'low': min(open_price, low, close),
                'close': close,
                'volume': np.random.randint(1000, 10000)
            })

        return pd.DataFrame(data)

    def _calculate_overall_health(self, report: Dict[str, Any]) -> str:
        """计算总体健康状态"""
        error_count = 0
        warning_count = 0
        total_checks = 0

        for key, value in report.items():
            if key in ['timestamp', 'overall_health', 'recommendations']:
                continue

            total_checks += 1
            if isinstance(value, dict) and 'status' in value:
                if value['status'] == 'error':
                    error_count += 1
                elif value['status'] == 'warning':
                    warning_count += 1

        if error_count > 0:
            return 'critical'
        elif warning_count > 0:
            return 'warning'
        else:
            return 'healthy'

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 检查性能指标
        perf = report.get('performance_metrics', {})
        if perf.get('success_rate', 1) < 0.9:
            recommendations.append("形态识别成功率较低，建议检查算法配置和数据质量")

        if perf.get('average_processing_time', 0) > 1.0:
            recommendations.append("处理时间较长，建议优化算法或增加缓存")

        # 检查缓存系统
        cache = report.get('cache_system', {})
        if cache.get('hit_rate', 0) < 0.5:
            recommendations.append("缓存命中率较低，建议调整缓存策略")

        if cache.get('utilization', 0) > 0.9:
            recommendations.append("缓存使用率过高，建议增加缓存大小")

        # 检查内存使用
        memory = report.get('memory_usage', {})
        if memory.get('percent', 0) > 80:
            recommendations.append("内存使用率过高，建议优化内存管理")

        # 检查依赖
        deps = report.get('dependencies', {})
        if not deps.get('all_available', True):
            recommendations.append("存在缺失的依赖库，建议安装完整依赖")

        if not recommendations:
            recommendations.append("系统运行良好，无需特别优化")

        return recommendations

    def generate_health_report(self, report: Dict[str, Any]) -> str:
        """生成可读的健康报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("HIkyuu量化交易系统健康报告")
        lines.append("=" * 60)
        lines.append(f"检查时间: {report['timestamp']}")
        lines.append(f"总体状态: {report['overall_health'].upper()}")
        lines.append("")

        # 系统信息
        sys_info = report.get('system_info', {})
        lines.append("📊 系统信息:")
        lines.append(f"  版本: {sys_info.get('version', 'unknown')}")
        lines.append(f"  支持形态: {sys_info.get('supported_patterns', 0)}种")
        lines.append("")

        # 性能指标
        perf = report.get('performance_metrics', {})
        lines.append("⚡ 性能指标:")
        lines.append(f"  总识别次数: {perf.get('total_recognitions', 0)}")
        lines.append(f"  成功率: {perf.get('success_rate', 0):.2%}")
        lines.append(f"  平均处理时间: {perf.get('average_processing_time', 0):.3f}秒")
        lines.append(f"  缓存命中率: {perf.get('cache_hit_rate', 0):.2%}")
        lines.append("")

        # 内存使用
        memory = report.get('memory_usage', {})
        lines.append("💾 内存使用:")
        lines.append(f"  进程内存: {memory.get('rss_mb', 0):.1f}MB")
        lines.append(f"  内存占用率: {memory.get('percent', 0):.1f}%")
        lines.append("")

        # 建议
        recommendations = report.get('recommendations', [])
        lines.append("💡 优化建议:")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


def main():
    """主函数 - 运行系统健康检查"""
    checker = SystemHealthChecker()
    report = checker.run_comprehensive_check()

    # 打印报告
    print("\n" + checker.generate_health_report(report))

    # 保存报告到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"logs/health_report_{timestamp}.json"

    os.makedirs("logs", exist_ok=True)

    import json
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 详细报告已保存到: {report_file}")

    return report


if __name__ == "__main__":
    main()
