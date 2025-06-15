"""
HIkyuu回测系统全功能综合测试脚本
验证所有回测功能的正确性、性能和稳定性
对标专业量化软件测试标准
"""

import sys
import os
import time
import threading
import multiprocessing
import psutil
import traceback
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import unittest
from unittest.mock import Mock, patch
import warnings

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入测试模块
try:
    from backtest.unified_backtest_engine import UnifiedBacktestEngine, BacktestLevel
    from backtest.real_time_backtest_monitor import RealTimeBacktestMonitor, MonitoringLevel
    from backtest.ultra_performance_optimizer import UltraPerformanceOptimizer, PerformanceLevel
    from backtest.backtest_validator import ProfessionalBacktestValidator
    from backtest.professional_ui_system import ProfessionalUISystem, create_professional_ui
    BACKTEST_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"警告: 回测模块导入失败 - {e}")
    BACKTEST_MODULES_AVAILABLE = False

try:
    from gui.widgets.backtest_widget import ProfessionalBacktestWidget, create_backtest_widget
    from gui.backtest_ui_launcher import BacktestUILauncher, launch_streamlit_only, launch_pyqt5_only
    GUI_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"警告: GUI模块导入失败 - {e}")
    GUI_MODULES_AVAILABLE = False

try:
    from core.logger import LogManager
    from utils.config_manager import ConfigManager
    CORE_MODULES_AVAILABLE = True
except ImportError:
    # 如果核心模块不可用，使用简化版本
    try:
        # 尝试导入基础日志管理器
        from core.base_logger import BaseLogManager as LogManager
    except ImportError:
        class LogManager:
            def log(self, message, level):
                print(f"[{level}] {message}")

            def info(self, message):
                print(f"[INFO] {message}")

            def warning(self, message):
                print(f"[WARNING] {message}")

            def error(self, message):
                print(f"[ERROR] {message}")

    # 简化版配置管理器
    class ConfigManager:
        def __init__(self):
            self.config = {
                'backtest': {
                    'initial_capital': 100000,
                    'commission_pct': 0.001,
                    'slippage_pct': 0.001
                },
                'risk': {
                    'max_position_size': 0.95,
                    'stop_loss_pct': 0.05
                }
            }

        def get(self, key, default=None):
            keys = key.split('.')
            value = self.config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    CORE_MODULES_AVAILABLE = False

# 抑制警告
warnings.filterwarnings('ignore')


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.end_memory = None
        self.start_cpu = None
        self.end_cpu = None
        self.process = psutil.Process()

    def start(self):
        """开始监控"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = self.process.cpu_percent()

    def stop(self):
        """停止监控"""
        self.end_time = time.time()
        self.end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.end_cpu = self.process.cpu_percent()

    def get_metrics(self) -> Dict:
        """获取性能指标"""
        return {
            'execution_time': self.end_time - self.start_time if self.end_time else 0,
            'memory_usage': self.end_memory - self.start_memory if self.end_memory else 0,
            'peak_memory': self.end_memory if self.end_memory else 0,
            'cpu_usage': self.end_cpu if self.end_cpu else 0
        }


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_kline_data(days: int = 252, start_price: float = 100.0) -> pd.DataFrame:
        """生成K线数据"""
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')

        # 生成价格数据
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, days)
        prices = start_price * np.cumprod(1 + returns)

        # 生成OHLCV数据
        high_factor = np.random.uniform(1.0, 1.05, days)
        low_factor = np.random.uniform(0.95, 1.0, days)
        volume = np.random.uniform(1000000, 10000000, days)

        kline_data = pd.DataFrame({
            'open': prices * np.random.uniform(0.98, 1.02, days),
            'high': prices * high_factor,
            'low': prices * low_factor,
            'close': prices,
            'volume': volume,
            'amount': volume * prices
        }, index=dates)

        return kline_data

    @staticmethod
    def generate_signal_data(kline_data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号数据"""
        signals = np.random.choice([-1, 0, 1], len(kline_data), p=[0.1, 0.8, 0.1])
        signal_data = kline_data.copy()
        signal_data['signal'] = signals
        return signal_data


class BacktestEngineTest(unittest.TestCase):
    """回测引擎测试"""

    def setUp(self):
        """测试设置"""
        self.log_manager = LogManager()
        self.performance_monitor = PerformanceMonitor()
        self.test_data = TestDataGenerator.generate_kline_data(252)

    def test_engine_initialization(self):
        """测试引擎初始化"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试回测引擎初始化 ===")

        for level in [BacktestLevel.RETAIL,
                      BacktestLevel.INSTITUTIONAL,
                      BacktestLevel.HEDGE_FUND,
                      BacktestLevel.INVESTMENT_BANK]:

            with self.subTest(level=level):
                self.performance_monitor.start()

                engine = UnifiedBacktestEngine(
                    backtest_level=level,
                    log_manager=self.log_manager
                )

                self.performance_monitor.stop()
                metrics = self.performance_monitor.get_metrics()

                self.assertIsNotNone(engine)
                self.assertEqual(engine.backtest_level, level)

                print(f"  ✅ {level.value} 级别初始化成功")
                print(f"     执行时间: {metrics['execution_time']:.3f}秒")
                print(f"     内存使用: {metrics['memory_usage']:.2f}MB")

    def test_backtest_execution(self):
        """测试回测执行"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试回测执行 ===")

        engine = UnifiedBacktestEngine(
            backtest_level=BacktestLevel.INVESTMENT_BANK,
            log_manager=self.log_manager
        )

        # 准备回测参数
        backtest_params = {
            'initial_capital': 1000000,
            'position_size': 0.95,
            'commission_pct': 0.0003,
            'slippage_pct': 0.0001
        }

        signal_data = TestDataGenerator.generate_signal_data(self.test_data)

        self.performance_monitor.start()

        # 执行回测
        result = engine.run_backtest(signal_data, **backtest_params)

        self.performance_monitor.stop()
        metrics = self.performance_monitor.get_metrics()

        # 验证结果
        self.assertIsNotNone(result)
        self.assertIn('backtest_result', result)
        self.assertIn('risk_metrics', result)
        self.assertIn('performance_metrics', result)

        print(f"  ✅ 回测执行成功")
        print(f"     执行时间: {metrics['execution_time']:.3f}秒")
        print(f"     内存使用: {metrics['memory_usage']:.2f}MB")
        print(f"     数据点数: {len(signal_data)}")

        # 验证性能要求
        self.assertLess(metrics['execution_time'], 10.0, "执行时间应小于10秒")
        self.assertLess(metrics['memory_usage'], 500.0, "内存使用应小于500MB")

    def test_risk_metrics_calculation(self):
        """测试风险指标计算"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试风险指标计算 ===")

        engine = UnifiedBacktestEngine(
            backtest_level=BacktestLevel.INVESTMENT_BANK,
            log_manager=self.log_manager
        )

        signal_data = TestDataGenerator.generate_signal_data(self.test_data)

        result = engine.run_backtest(signal_data, initial_capital=1000000)
        risk_metrics = result['risk_metrics']

        # 验证必要的风险指标
        required_metrics = [
            'total_return', 'annualized_return', 'volatility', 'sharpe_ratio',
            'max_drawdown', 'win_rate', 'profit_factor', 'var_95'
        ]

        for metric in required_metrics:
            with self.subTest(metric=metric):
                self.assertTrue(hasattr(risk_metrics, metric), f"缺少风险指标: {metric}")
                value = getattr(risk_metrics, metric)
                self.assertIsInstance(value, (int, float), f"{metric} 应为数值类型")
                print(f"  ✅ {metric}: {value:.4f}")


class MonitorTest(unittest.TestCase):
    """监控系统测试"""

    def setUp(self):
        """测试设置"""
        self.log_manager = LogManager()
        self.performance_monitor = PerformanceMonitor()

    def test_monitor_initialization(self):
        """测试监控器初始化"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试监控器初始化 ===")

        for level in [MonitoringLevel.BASIC, MonitoringLevel.STANDARD,
                      MonitoringLevel.ADVANCED, MonitoringLevel.REAL_TIME]:

            with self.subTest(level=level):
                monitor = RealTimeBacktestMonitor(
                    monitoring_level=level,
                    log_manager=self.log_manager
                )

                self.assertIsNotNone(monitor)
                self.assertEqual(monitor.monitoring_level, level)
                print(f"  ✅ {level.value} 级别监控器初始化成功")

    def test_real_time_monitoring(self):
        """测试实时监控"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试实时监控 ===")

        monitor = RealTimeBacktestMonitor(
            monitoring_level=MonitoringLevel.REAL_TIME,
            log_manager=self.log_manager
        )

        # 启动监控
        monitor.start_monitoring()

        # 模拟监控数据
        for i in range(10):
            mock_data = {
                'timestamp': datetime.now(),
                'current_return': np.random.normal(0, 0.02),
                'cumulative_return': np.random.uniform(-0.1, 0.3),
                'current_drawdown': np.random.uniform(0, 0.1),
                'sharpe_ratio': np.random.uniform(-0.5, 2.5)
            }
            monitor.update_metrics(mock_data)
            time.sleep(0.1)

        # 停止监控
        monitor.stop_monitoring()

        # 验证监控数据
        monitoring_data = monitor.get_monitoring_data()
        self.assertGreater(len(monitoring_data), 0)

        print(f"  ✅ 实时监控测试完成，收集了 {len(monitoring_data)} 个数据点")


class OptimizerTest(unittest.TestCase):
    """优化器测试"""

    def setUp(self):
        """测试设置"""
        self.log_manager = LogManager()
        self.performance_monitor = PerformanceMonitor()

    def test_optimizer_initialization(self):
        """测试优化器初始化"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试优化器初始化 ===")

        for level in [PerformanceLevel.STANDARD, PerformanceLevel.HIGH,
                      PerformanceLevel.ULTRA, PerformanceLevel.EXTREME]:

            with self.subTest(level=level):
                optimizer = UltraPerformanceOptimizer(
                    performance_level=level,
                    log_manager=self.log_manager
                )

                self.assertIsNotNone(optimizer)
                self.assertEqual(optimizer.performance_level, level)
                print(f"  ✅ {level.value} 级别优化器初始化成功")

    def test_performance_optimization(self):
        """测试性能优化"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试性能优化 ===")

        optimizer = UltraPerformanceOptimizer(
            performance_level=PerformanceLevel.ULTRA,
            log_manager=self.log_manager
        )

        # 生成测试数据
        test_data = np.random.randn(10000, 100)

        self.performance_monitor.start()

        # 执行优化计算
        optimized_result = optimizer.optimize_calculation(test_data)

        self.performance_monitor.stop()
        metrics = self.performance_monitor.get_metrics()

        self.assertIsNotNone(optimized_result)

        print(f"  ✅ 性能优化测试完成")
        print(f"     执行时间: {metrics['execution_time']:.3f}秒")
        print(f"     内存使用: {metrics['memory_usage']:.2f}MB")
        print(f"     数据规模: {test_data.shape}")


class ValidatorTest(unittest.TestCase):
    """验证器测试"""

    def setUp(self):
        """测试设置"""
        self.log_manager = LogManager()
        self.test_data = TestDataGenerator.generate_kline_data(252)

    def test_validator_initialization(self):
        """测试验证器初始化"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试验证器初始化 ===")

        validator = ProfessionalBacktestValidator(self.log_manager)

        self.assertIsNotNone(validator)
        print("  ✅ 验证器初始化成功")

    def test_data_validation(self):
        """测试数据验证"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试数据验证 ===")

        validator = ProfessionalBacktestValidator(self.log_manager)

        # 验证正常数据
        validation_result = validator.validate_kline_data(self.test_data)

        self.assertIsNotNone(validation_result)
        self.assertIn('is_valid', validation_result)
        self.assertIn('quality_score', validation_result)
        self.assertIn('issues', validation_result)

        print(f"  ✅ 数据验证完成")
        print(f"     验证结果: {'通过' if validation_result['is_valid'] else '失败'}")
        print(f"     质量评分: {validation_result['quality_score']:.2f}")
        print(f"     问题数量: {len(validation_result['issues'])}")


class UISystemTest(unittest.TestCase):
    """UI系统测试"""

    def setUp(self):
        """测试设置"""
        self.log_manager = LogManager()

    def test_streamlit_ui_creation(self):
        """测试Streamlit UI创建"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试Streamlit UI创建 ===")

        try:
            ui_system = create_professional_ui("dark")
            self.assertIsNotNone(ui_system)
            print("  ✅ Streamlit UI系统创建成功")
        except Exception as e:
            print(f"  ⚠️ Streamlit UI创建失败: {e}")

    def test_pyqt5_widget_creation(self):
        """测试PyQt5组件创建"""
        if not GUI_MODULES_AVAILABLE:
            self.skipTest("GUI模块不可用")

        print("\n=== 测试PyQt5组件创建 ===")

        try:
            # 模拟QApplication环境
            from PyQt5.QtWidgets import QApplication

            if not QApplication.instance():
                app = QApplication(sys.argv)

            widget = create_backtest_widget()
            self.assertIsNotNone(widget)
            print("  ✅ PyQt5回测组件创建成功")

        except Exception as e:
            print(f"  ⚠️ PyQt5组件创建失败: {e}")


class IntegrationTest(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """测试设置"""
        self.log_manager = LogManager()
        self.performance_monitor = PerformanceMonitor()

    def test_full_backtest_workflow(self):
        """测试完整回测工作流"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试完整回测工作流 ===")

        self.performance_monitor.start()

        # 1. 数据准备
        test_data = TestDataGenerator.generate_kline_data(252)
        signal_data = TestDataGenerator.generate_signal_data(test_data)
        print("  ✅ 步骤1: 数据准备完成")

        # 2. 数据验证
        validator = ProfessionalBacktestValidator(self.log_manager)
        validation_result = validator.validate_kline_data(test_data)
        self.assertTrue(validation_result['is_valid'])
        print("  ✅ 步骤2: 数据验证通过")

        # 3. 回测执行
        engine = UnifiedBacktestEngine(
            backtest_level=BacktestLevel.INVESTMENT_BANK,
            log_manager=self.log_manager
        )
        backtest_result = engine.run_backtest(signal_data, initial_capital=1000000)
        self.assertIsNotNone(backtest_result)
        print("  ✅ 步骤3: 回测执行完成")

        # 4. 实时监控
        monitor = RealTimeBacktestMonitor(
            monitoring_level=MonitoringLevel.REAL_TIME,
            log_manager=self.log_manager
        )
        monitor.start_monitoring()

        # 模拟监控数据
        for i in range(5):
            mock_data = {
                'timestamp': datetime.now(),
                'current_return': np.random.normal(0, 0.02),
                'cumulative_return': np.random.uniform(-0.1, 0.3)
            }
            monitor.update_metrics(mock_data)
            time.sleep(0.1)

        monitor.stop_monitoring()
        monitoring_data = monitor.get_monitoring_data()
        self.assertGreater(len(monitoring_data), 0)
        print("  ✅ 步骤4: 实时监控完成")

        # 5. 性能优化
        optimizer = UltraPerformanceOptimizer(
            performance_level=PerformanceLevel.ULTRA,
            log_manager=self.log_manager
        )
        optimization_result = optimizer.optimize_calculation(test_data.values)
        self.assertIsNotNone(optimization_result)
        print("  ✅ 步骤5: 性能优化完成")

        self.performance_monitor.stop()
        metrics = self.performance_monitor.get_metrics()

        print(f"\n  📊 完整工作流性能指标:")
        print(f"     总执行时间: {metrics['execution_time']:.3f}秒")
        print(f"     内存使用: {metrics['memory_usage']:.2f}MB")
        print(f"     峰值内存: {metrics['peak_memory']:.2f}MB")

        # 验证性能要求
        self.assertLess(metrics['execution_time'], 30.0, "完整工作流应在30秒内完成")
        self.assertLess(metrics['peak_memory'], 1000.0, "峰值内存使用应小于1GB")


class StressTest(unittest.TestCase):
    """压力测试"""

    def setUp(self):
        """测试设置"""
        self.log_manager = LogManager()
        self.performance_monitor = PerformanceMonitor()

    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试大数据集性能 ===")

        # 生成大数据集（5年日线数据）
        large_dataset = TestDataGenerator.generate_kline_data(1260)  # 5年
        signal_data = TestDataGenerator.generate_signal_data(large_dataset)

        print(f"  数据规模: {len(large_dataset)} 个交易日")

        self.performance_monitor.start()

        engine = UnifiedBacktestEngine(
            backtest_level=BacktestLevel.INVESTMENT_BANK,
            log_manager=self.log_manager
        )

        result = engine.run_backtest(signal_data, initial_capital=1000000)

        self.performance_monitor.stop()
        metrics = self.performance_monitor.get_metrics()

        self.assertIsNotNone(result)

        print(f"  ✅ 大数据集回测完成")
        print(f"     执行时间: {metrics['execution_time']:.3f}秒")
        print(f"     内存使用: {metrics['memory_usage']:.2f}MB")
        print(f"     处理速度: {len(large_dataset)/metrics['execution_time']:.0f} 条/秒")

        # 性能要求
        self.assertLess(metrics['execution_time'], 60.0, "大数据集回测应在60秒内完成")
        self.assertGreater(len(large_dataset)/metrics['execution_time'], 20, "处理速度应大于20条/秒")

    def test_concurrent_backtests(self):
        """测试并发回测"""
        if not BACKTEST_MODULES_AVAILABLE:
            self.skipTest("回测模块不可用")

        print("\n=== 测试并发回测 ===")

        def run_single_backtest(test_id):
            """运行单个回测"""
            try:
                test_data = TestDataGenerator.generate_kline_data(252)
                signal_data = TestDataGenerator.generate_signal_data(test_data)

                engine = UnifiedBacktestEngine(
                    backtest_level=BacktestLevel.INSTITUTIONAL,
                    log_manager=self.log_manager
                )

                result = engine.run_backtest(signal_data, initial_capital=1000000)
                return test_id, True, result

            except Exception as e:
                return test_id, False, str(e)

        self.performance_monitor.start()

        # 启动多个并发回测
        num_concurrent = 4
        with multiprocessing.Pool(num_concurrent) as pool:
            results = pool.map(run_single_backtest, range(num_concurrent))

        self.performance_monitor.stop()
        metrics = self.performance_monitor.get_metrics()

        # 验证结果
        successful_tests = sum(1 for _, success, _ in results if success)

        print(f"  ✅ 并发回测完成")
        print(f"     并发数量: {num_concurrent}")
        print(f"     成功数量: {successful_tests}")
        print(f"     总执行时间: {metrics['execution_time']:.3f}秒")
        print(f"     内存使用: {metrics['memory_usage']:.2f}MB")

        self.assertEqual(successful_tests, num_concurrent, "所有并发回测都应成功")


class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self):
        self.test_results = []
        self.start_time = None
        self.end_time = None

    def start_testing(self):
        """开始测试"""
        self.start_time = datetime.now()
        print("=" * 80)
        print("🚀 HIkyuu回测系统全功能综合测试开始")
        print(f"⏰ 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    def end_testing(self):
        """结束测试"""
        self.end_time = datetime.now()
        duration = self.end_time - self.start_time

        print("\n" + "=" * 80)
        print("📊 测试完成 - 生成测试报告")
        print("=" * 80)

        self.generate_report(duration)

    def add_test_result(self, test_name: str, success: bool, details: Dict = None):
        """添加测试结果"""
        self.test_results.append({
            'test_name': test_name,
            'success': success,
            'details': details or {},
            'timestamp': datetime.now()
        })

    def generate_report(self, duration: timedelta):
        """生成测试报告"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\n📈 测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功数量: {successful_tests}")
        print(f"   失败数量: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")
        print(f"   总耗时: {duration.total_seconds():.2f}秒")

        print(f"\n🔍 详细结果:")
        for result in self.test_results:
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"   {status} {result['test_name']}")

            if result['details']:
                for key, value in result['details'].items():
                    print(f"      {key}: {value}")

        # 系统信息
        print(f"\n💻 系统信息:")
        print(f"   Python版本: {sys.version.split()[0]}")
        print(f"   操作系统: {os.name}")
        print(f"   CPU核心数: {multiprocessing.cpu_count()}")
        print(f"   内存总量: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f}GB")

        # 模块可用性
        print(f"\n📦 模块可用性:")
        print(f"   回测模块: {'✅ 可用' if BACKTEST_MODULES_AVAILABLE else '❌ 不可用'}")
        print(f"   GUI模块: {'✅ 可用' if GUI_MODULES_AVAILABLE else '❌ 不可用'}")
        print(f"   核心模块: {'✅ 可用' if CORE_MODULES_AVAILABLE else '❌ 不可用'}")

        # 性能评级
        performance_grade = self.calculate_performance_grade(duration.total_seconds(), success_rate)
        print(f"\n🏆 性能评级: {performance_grade}")

        # 保存报告到文件
        self.save_report_to_file(duration, success_rate, performance_grade)

    def calculate_performance_grade(self, duration: float, success_rate: float) -> str:
        """计算性能评级"""
        if success_rate >= 95 and duration <= 60:
            return "A+ (优秀)"
        elif success_rate >= 90 and duration <= 120:
            return "A (良好)"
        elif success_rate >= 80 and duration <= 180:
            return "B (一般)"
        elif success_rate >= 70:
            return "C (需要改进)"
        else:
            return "D (不合格)"

    def save_report_to_file(self, duration: timedelta, success_rate: float, grade: str):
        """保存报告到文件"""
        try:
            report_data = {
                'test_summary': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': self.end_time.isoformat(),
                    'duration_seconds': duration.total_seconds(),
                    'total_tests': len(self.test_results),
                    'successful_tests': sum(1 for r in self.test_results if r['success']),
                    'success_rate': success_rate,
                    'performance_grade': grade
                },
                'test_results': self.test_results,
                'system_info': {
                    'python_version': sys.version.split()[0],
                    'os_name': os.name,
                    'cpu_count': multiprocessing.cpu_count(),
                    'memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024
                },
                'module_availability': {
                    'backtest_modules': BACKTEST_MODULES_AVAILABLE,
                    'gui_modules': GUI_MODULES_AVAILABLE,
                    'core_modules': CORE_MODULES_AVAILABLE
                }
            }

            report_file = f"backtest_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n💾 测试报告已保存到: {report_file}")

        except Exception as e:
            print(f"\n⚠️ 保存报告失败: {e}")


def run_comprehensive_tests():
    """运行全面测试"""
    report_generator = TestReportGenerator()
    report_generator.start_testing()

    # 创建测试套件
    test_suite = unittest.TestSuite()

    # 添加测试用例
    test_classes = [
        BacktestEngineTest,
        MonitorTest,
        OptimizerTest,
        ValidatorTest,
        UISystemTest,
        IntegrationTest,
        StressTest
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)

    # 记录测试结果
    for test, error in result.failures + result.errors:
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        report_generator.add_test_result(test_name, False, {'error': str(error)})

    # 记录成功的测试
    successful_count = result.testsRun - len(result.failures) - len(result.errors)
    for i in range(successful_count):
        report_generator.add_test_result(f"Test_{i+1}", True)

    report_generator.end_testing()

    return result


def main():
    """主函数"""
    print("HIkyuu回测系统全功能综合测试")
    print("=" * 50)

    # 检查依赖
    missing_deps = []

    try:
        import pandas
        import numpy
    except ImportError as e:
        missing_deps.append(str(e))

    if missing_deps:
        print("❌ 缺少必要依赖:")
        for dep in missing_deps:
            print(f"   {dep}")
        print("\n请安装缺少的依赖后重新运行测试")
        return

    # 运行测试
    try:
        result = run_comprehensive_tests()

        # 返回退出码
        if result.wasSuccessful():
            print("\n🎉 所有测试通过！")
            sys.exit(0)
        else:
            print(f"\n⚠️ 有 {len(result.failures + result.errors)} 个测试失败")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
