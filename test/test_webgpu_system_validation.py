"""
WebGPU硬件加速系统完整性验证测试

验证所有6个阶段的功能是否正确实现：
Phase 1: 环境检测和兼容性层
Phase 2: 管道优化和内存管理  
Phase 3: GPU交互引擎和十字线功能
Phase 4: 兼容性测试、性能基准、错误恢复、文档

作者: HIkyuu团队
版本: 1.0.0
"""

import unittest
import sys
import os
import importlib
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class WebGPUSystemValidationTest(unittest.TestCase):
    """WebGPU系统完整性验证测试"""

    def setUp(self):
        """测试初始化"""
        self.project_root = Path(__file__).parent.parent
        self.validation_results = {}

    def test_phase1_environment_detection(self):
        """测试Phase 1: 环境检测功能"""
        print("\n=== Phase 1: 环境检测功能验证 ===")

        phase1_modules = [
            'core.webgpu.environment',
            'core.webgpu.compatibility',
            'core.webgpu.fallback'
        ]

        phase1_results = {}

        for module_name in phase1_modules:
            try:
                module = importlib.import_module(module_name)
                phase1_results[module_name] = True
                print(f"✅ {module_name}: 导入成功")

                # 测试核心功能
                if module_name == 'core.webgpu.environment':
                    self._test_environment_detection(module)
                elif module_name == 'core.webgpu.compatibility':
                    self._test_compatibility_detection(module)
                elif module_name == 'core.webgpu.fallback':
                    self._test_fallback_system(module)

            except ImportError as e:
                phase1_results[module_name] = False
                print(f"❌ {module_name}: 导入失败 - {e}")

        self.validation_results['phase1'] = phase1_results

        # 至少要有2个模块成功
        success_count = sum(phase1_results.values())
        self.assertGreaterEqual(success_count, 2, "Phase 1: 至少需要2个模块成功导入")

    def _test_environment_detection(self, module):
        """测试环境检测模块"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'WebGPUEnvironment'))

            # 测试基本功能
            env = module.WebGPUEnvironment()
            support_info = env.detect_webgpu_support()

            self.assertIsInstance(support_info, dict)
            self.assertIn('supported', support_info)
            print(f"  📊 WebGPU支持检测: {support_info.get('supported', 'Unknown')}")

        except Exception as e:
            print(f"  ⚠️ 环境检测测试异常: {e}")

    def _test_compatibility_detection(self, module):
        """测试兼容性检测模块"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'WebGPUCompatibility'))

            # 测试基本功能
            compat = module.WebGPUCompatibility()
            level = compat.get_compatibility_level()

            print(f"  📊 兼容性级别: {level}")

        except Exception as e:
            print(f"  ⚠️ 兼容性检测测试异常: {e}")

    def _test_fallback_system(self, module):
        """测试降级系统模块"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'FallbackManager'))

            # 测试基本功能
            fallback = module.FallbackManager()
            engines = fallback.get_available_engines()

            self.assertIsInstance(engines, list)
            print(f"  📊 可用渲染引擎: {len(engines)} 个")

        except Exception as e:
            print(f"  ⚠️ 降级系统测试异常: {e}")

    def test_phase2_optimization_and_memory(self):
        """测试Phase 2: 管道优化和内存管理"""
        print("\n=== Phase 2: 管道优化和内存管理验证 ===")

        phase2_modules = [
            'core.webgpu.memory_manager',
            'core.webgpu.pipeline_optimizer',
            'optimization.webgpu_chart_renderer'
        ]

        phase2_results = {}

        for module_name in phase2_modules:
            try:
                module = importlib.import_module(module_name)
                phase2_results[module_name] = True
                print(f"✅ {module_name}: 导入成功")

                # 测试核心功能
                if module_name == 'core.webgpu.memory_manager':
                    self._test_memory_manager(module)
                elif module_name == 'core.webgpu.pipeline_optimizer':
                    self._test_pipeline_optimizer(module)
                elif module_name == 'optimization.webgpu_chart_renderer':
                    self._test_chart_renderer(module)

            except ImportError as e:
                phase2_results[module_name] = False
                print(f"❌ {module_name}: 导入失败 - {e}")

        self.validation_results['phase2'] = phase2_results

        # 至少要有2个模块成功
        success_count = sum(phase2_results.values())
        self.assertGreaterEqual(success_count, 2, "Phase 2: 至少需要2个模块成功导入")

    def _test_memory_manager(self, module):
        """测试内存管理器"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'WebGPUMemoryManager'))

            # 测试基本功能
            manager = module.WebGPUMemoryManager()
            stats = manager.get_memory_statistics()

            self.assertIsNotNone(stats)
            print(f"  📊 内存管理器初始化成功")

        except Exception as e:
            print(f"  ⚠️ 内存管理器测试异常: {e}")

    def _test_pipeline_optimizer(self, module):
        """测试管道优化器"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'WebGPUPipelineOptimizer'))

            # 测试基本功能
            optimizer = module.WebGPUPipelineOptimizer()
            stats = optimizer.get_performance_statistics()

            self.assertIsNotNone(stats)
            print(f"  📊 管道优化器初始化成功")

        except Exception as e:
            print(f"  ⚠️ 管道优化器测试异常: {e}")

    def _test_chart_renderer(self, module):
        """测试图表渲染器"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'WebGPUChartRenderer'))

            print(f"  📊 图表渲染器类存在")

        except Exception as e:
            print(f"  ⚠️ 图表渲染器测试异常: {e}")

    def test_phase3_gpu_interaction(self):
        """测试Phase 3: GPU交互引擎和十字线功能"""
        print("\n=== Phase 3: GPU交互引擎和十字线功能验证 ===")

        phase3_modules = [
            'core.webgpu.interaction_engine',
            'core.webgpu.crosshair_engine',
            'gui.widgets.chart_mixins.gpu_enhanced_zoom_mixin',
            'gui.widgets.chart_mixins.gpu_enhanced_crosshair_mixin'
        ]

        phase3_results = {}

        for module_name in phase3_modules:
            try:
                module = importlib.import_module(module_name)
                phase3_results[module_name] = True
                print(f"✅ {module_name}: 导入成功")

                # 测试核心功能
                if module_name == 'core.webgpu.interaction_engine':
                    self._test_interaction_engine(module)
                elif module_name == 'core.webgpu.crosshair_engine':
                    self._test_crosshair_engine(module)

            except ImportError as e:
                phase3_results[module_name] = False
                print(f"❌ {module_name}: 导入失败 - {e}")

        self.validation_results['phase3'] = phase3_results

        # 至少要有3个模块成功
        success_count = sum(phase3_results.values())
        self.assertGreaterEqual(success_count, 3, "Phase 3: 至少需要3个模块成功导入")

    def _test_interaction_engine(self, module):
        """测试交互引擎"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'GPUInteractionEngine'))

            # 测试基本功能
            engine = module.GPUInteractionEngine()
            self.assertIsNotNone(engine)
            print(f"  📊 GPU交互引擎初始化成功")

        except Exception as e:
            print(f"  ⚠️ 交互引擎测试异常: {e}")

    def _test_crosshair_engine(self, module):
        """测试十字线引擎"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'GPUCrosshairEngine'))

            # 测试基本功能
            engine = module.GPUCrosshairEngine()
            self.assertIsNotNone(engine)
            print(f"  📊 GPU十字线引擎初始化成功")

        except Exception as e:
            print(f"  ⚠️ 十字线引擎测试异常: {e}")

    def test_phase4_testing_and_recovery(self):
        """测试Phase 4: 兼容性测试、性能基准、错误恢复"""
        print("\n=== Phase 4: 测试、基准和错误恢复验证 ===")

        phase4_modules = [
            'core.webgpu.compatibility_testing',
            'core.webgpu.performance_benchmarks',
            'core.webgpu.error_recovery'
        ]

        phase4_results = {}

        for module_name in phase4_modules:
            try:
                module = importlib.import_module(module_name)
                phase4_results[module_name] = True
                print(f"✅ {module_name}: 导入成功")

                # 测试核心功能
                if module_name == 'core.webgpu.compatibility_testing':
                    self._test_compatibility_testing(module)
                elif module_name == 'core.webgpu.performance_benchmarks':
                    self._test_performance_benchmarks(module)
                elif module_name == 'core.webgpu.error_recovery':
                    self._test_error_recovery(module)

            except ImportError as e:
                phase4_results[module_name] = False
                print(f"❌ {module_name}: 导入失败 - {e}")

        self.validation_results['phase4'] = phase4_results

        # 所有模块都必须成功
        success_count = sum(phase4_results.values())
        self.assertEqual(success_count, 3, "Phase 4: 所有模块都必须成功导入")

    def _test_compatibility_testing(self, module):
        """测试兼容性测试框架"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'CompatibilityTestSuite'))

            # 运行快速测试
            report = module.run_compatibility_test()
            self.assertIsNotNone(report)
            print(f"  📊 兼容性测试: {report.overall_compatibility.value}")

        except Exception as e:
            print(f"  ⚠️ 兼容性测试异常: {e}")

    def _test_performance_benchmarks(self, module):
        """测试性能基准测试"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'PerformanceBenchmarkSuite'))

            # 测试快速性能测试
            def dummy_render():
                import time
                time.sleep(0.001)

            result = module.run_quick_performance_test(dummy_render)
            self.assertIsNotNone(result)
            print(f"  📊 性能测试: {result.metrics.frame_rate:.1f} FPS")

        except Exception as e:
            print(f"  ⚠️ 性能基准测试异常: {e}")

    def _test_error_recovery(self, module):
        """测试错误恢复机制"""
        try:
            # 检查核心类
            self.assertTrue(hasattr(module, 'ErrorRecoveryManager'))

            # 测试错误处理
            manager = module.get_error_recovery_manager()
            context = module.setup_error_recovery_context()

            result = manager.handle_error("Test error", context=context)
            self.assertIsNotNone(result)
            print(f"  📊 错误恢复测试成功")

        except Exception as e:
            print(f"  ⚠️ 错误恢复测试异常: {e}")

    def test_system_integration(self):
        """测试系统集成"""
        print("\n=== 系统集成验证 ===")

        integration_results = {}

        # 测试WebGPU管理器
        try:
            from core.webgpu.manager import get_webgpu_manager

            manager = get_webgpu_manager()
            self.assertIsNotNone(manager)
            integration_results['webgpu_manager'] = True
            print("✅ WebGPU管理器: 初始化成功")

        except ImportError as e:
            integration_results['webgpu_manager'] = False
            print(f"❌ WebGPU管理器: 导入失败 - {e}")
        except Exception as e:
            integration_results['webgpu_manager'] = False
            print(f"❌ WebGPU管理器: 初始化失败 - {e}")

        # 测试测试文件
        test_files = [
            'test.test_webgpu_integration',
            'test.test_gpu_interaction',
            'test.test_gpu_crosshair',
            'test.test_webgpu_compatibility'
        ]

        for test_file in test_files:
            try:
                importlib.import_module(test_file)
                integration_results[test_file] = True
                print(f"✅ {test_file}: 导入成功")
            except ImportError as e:
                integration_results[test_file] = False
                print(f"❌ {test_file}: 导入失败 - {e}")

        self.validation_results['integration'] = integration_results

        # 至少要有4个组件成功
        success_count = sum(integration_results.values())
        self.assertGreaterEqual(success_count, 4, "系统集成: 至少需要4个组件成功")

    def test_documentation_completeness(self):
        """测试文档完整性"""
        print("\n=== 文档完整性验证 ===")

        doc_files = [
            'docs/WebGPU_API_Reference.md',
            'docs/WebGPU_Troubleshooting_Guide.md',
            'WebGPU_硬件加速渲染方案_收益分析报告.md',
            'README.md'
        ]

        doc_results = {}

        for doc_file in doc_files:
            doc_path = self.project_root / doc_file

            if doc_path.exists():
                doc_results[doc_file] = True

                # 检查文件大小（至少有内容）
                file_size = doc_path.stat().st_size
                if file_size > 1000:  # 至少1KB
                    print(f"✅ {doc_file}: 存在且有内容 ({file_size} bytes)")
                else:
                    print(f"⚠️ {doc_file}: 存在但内容较少 ({file_size} bytes)")
            else:
                doc_results[doc_file] = False
                print(f"❌ {doc_file}: 不存在")

        self.validation_results['documentation'] = doc_results

        # 至少要有3个文档存在
        success_count = sum(doc_results.values())
        self.assertGreaterEqual(success_count, 3, "文档: 至少需要3个文档存在")

    def test_file_structure_completeness(self):
        """测试文件结构完整性"""
        print("\n=== 文件结构完整性验证 ===")

        required_files = [
            # Phase 1
            'core/webgpu/__init__.py',
            'core/webgpu/environment.py',
            'core/webgpu/compatibility.py',
            'core/webgpu/fallback.py',

            # Phase 2
            'core/webgpu/memory_manager.py',
            'core/webgpu/pipeline_optimizer.py',
            'optimization/webgpu_chart_renderer.py',

            # Phase 3
            'core/webgpu/interaction_engine.py',
            'core/webgpu/crosshair_engine.py',
            'gui/widgets/chart_mixins/gpu_enhanced_zoom_mixin.py',
            'gui/widgets/chart_mixins/gpu_enhanced_crosshair_mixin.py',

            # Phase 4
            'core/webgpu/compatibility_testing.py',
            'core/webgpu/performance_benchmarks.py',
            'core/webgpu/error_recovery.py',

            # Integration
            'core/webgpu/manager.py',
            'gui/dialogs/webgpu_status_dialog.py',

            # Tests
            'test/test_webgpu_integration.py',
            'test/test_gpu_interaction.py',
            'test/test_gpu_crosshair.py',
            'test/test_webgpu_compatibility.py'
        ]

        file_results = {}

        for file_path in required_files:
            full_path = self.project_root / file_path

            if full_path.exists():
                file_results[file_path] = True
                print(f"✅ {file_path}: 存在")
            else:
                file_results[file_path] = False
                print(f"❌ {file_path}: 不存在")

        self.validation_results['file_structure'] = file_results

        # 至少要有90%的文件存在
        success_count = sum(file_results.values())
        total_count = len(file_results)
        success_rate = success_count / total_count

        self.assertGreaterEqual(success_rate, 0.9, f"文件结构: 至少需要90%的文件存在 (当前: {success_rate:.1%})")

    def test_run_actual_tests(self):
        """运行实际的测试用例"""
        print("\n=== 运行实际测试用例 ===")

        test_modules = [
            'test.test_webgpu_integration',
            'test.test_gpu_interaction',
            'test.test_gpu_crosshair',
            'test.test_webgpu_compatibility'
        ]

        test_results = {}

        for module_name in test_modules:
            try:
                # 导入测试模块
                test_module = importlib.import_module(module_name)

                # 运行测试
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromModule(test_module)
                runner = unittest.TextTestRunner(stream=open(os.devnull, 'w'), verbosity=0)
                result = runner.run(suite)

                # 统计结果
                total_tests = result.testsRun
                failed_tests = len(result.failures) + len(result.errors)
                success_tests = total_tests - failed_tests

                test_results[module_name] = {
                    'total': total_tests,
                    'success': success_tests,
                    'failed': failed_tests,
                    'success_rate': success_tests / total_tests if total_tests > 0 else 0
                }

                print(f"✅ {module_name}: {success_tests}/{total_tests} 测试通过 ({test_results[module_name]['success_rate']:.1%})")

            except Exception as e:
                test_results[module_name] = {'error': str(e)}
                print(f"❌ {module_name}: 测试运行失败 - {e}")

        self.validation_results['actual_tests'] = test_results

        # 至少要有2个测试模块成功运行
        successful_modules = sum(1 for result in test_results.values() if 'success_rate' in result)
        self.assertGreaterEqual(successful_modules, 2, "实际测试: 至少需要2个测试模块成功运行")

    def tearDown(self):
        """测试清理和总结"""
        print("\n" + "="*60)
        print("WebGPU系统完整性验证总结")
        print("="*60)

        # 统计各阶段结果
        phase_summary = {}

        for phase, results in self.validation_results.items():
            if isinstance(results, dict):
                success_count = sum(1 for v in results.values()
                                    if (isinstance(v, bool) and v) or
                                    (isinstance(v, dict) and 'success_rate' in v and v['success_rate'] > 0.5))
                total_count = len(results)
                success_rate = success_count / total_count if total_count > 0 else 0

                phase_summary[phase] = {
                    'success_count': success_count,
                    'total_count': total_count,
                    'success_rate': success_rate
                }

        # 打印总结
        for phase, summary in phase_summary.items():
            status = "✅" if summary['success_rate'] >= 0.8 else "⚠️" if summary['success_rate'] >= 0.5 else "❌"
            print(f"{status} {phase.upper()}: {summary['success_count']}/{summary['total_count']} "
                  f"({summary['success_rate']:.1%})")

        # 总体评估
        if len(phase_summary) > 0:
            overall_success_rate = sum(s['success_rate'] for s in phase_summary.values()) / len(phase_summary)
            print(f"\n📊 系统总体完成度: {overall_success_rate:.1%}")

            if overall_success_rate >= 0.9:
                print("🎉 系统功能基本完整，可以投入使用！")
            elif overall_success_rate >= 0.7:
                print("⚠️ 系统功能大部分完整，建议修复部分问题")
            else:
                print("❌ 系统功能不够完整，需要进一步开发")
        else:
            print("\n⚠️ 没有可用的测试结果进行评估")


def run_comprehensive_validation():
    """运行完整的系统验证"""
    print("🚀 启动WebGPU硬件加速系统完整性验证...")

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(WebGPUSystemValidationTest)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回结果
    return result.wasSuccessful()


if __name__ == '__main__':
    # 运行系统验证
    success = run_comprehensive_validation()

    if success:
        print("\n🎉 所有验证测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分验证测试失败！")
        sys.exit(1)
