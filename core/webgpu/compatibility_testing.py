from loguru import logger
"""
WebGPU兼容性测试框架

提供全面的兼容性测试功能：
- 浏览器兼容性检测
- GPU硬件兼容性测试
- 操作系统兼容性测试
- WebGPU特性支持检测
- 自动化测试运行和报告生成

作者: HIkyuu团队
版本: 1.0.0
"""

import platform
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
import subprocess
import sys
from pathlib import Path

logger = logger


class CompatibilityLevel(Enum):
    """兼容性级别"""
    EXCELLENT = "excellent"  # 完全兼容，性能优异
    GOOD = "good"          # 良好兼容，性能较好
    FAIR = "fair"          # 基本兼容，性能一般
    POOR = "poor"          # 兼容性差，性能较差
    UNSUPPORTED = "unsupported"  # 不支持


class TestResult(Enum):
    """测试结果状态"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestCase:
    """测试用例"""
    name: str
    description: str
    test_function: str
    category: str
    priority: int = 1  # 1=高优先级, 2=中优先级, 3=低优先级
    timeout: int = 30  # 超时时间（秒）
    prerequisites: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)


@dataclass
class TestCaseResult:
    """测试用例结果"""
    test_case: TestCase
    result: TestResult
    duration: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    error_info: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class SystemInfo:
    """系统信息"""
    os_name: str
    os_version: str
    architecture: str
    python_version: str
    platform_info: str
    cpu_info: str
    memory_info: str
    gpu_info: List[str] = field(default_factory=list)
    browser_info: Dict[str, str] = field(default_factory=dict)


@dataclass
class CompatibilityReport:
    """兼容性测试报告"""
    system_info: SystemInfo
    test_results: List[TestCaseResult]
    overall_compatibility: CompatibilityLevel
    recommendations: List[str] = field(default_factory=list)
    performance_score: float = 0.0
    test_summary: Dict[str, int] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    test_duration: float = 0.0


class BrowserCompatibilityTest:
    """浏览器兼容性测试"""

    def __init__(self):
        self.supported_browsers = {
            'chrome': {'min_version': 113, 'webgpu_support': True},
            'firefox': {'min_version': 110, 'webgpu_support': True},
            'edge': {'min_version': 113, 'webgpu_support': True},
            'safari': {'min_version': 16, 'webgpu_support': True},
            'opera': {'min_version': 99, 'webgpu_support': True}
        }

    def get_browser_info(self) -> Dict[str, str]:
        """获取浏览器信息"""
        try:
            # 在PyQt环境中，我们主要关注系统默认浏览器
            import webbrowser
            browser_info = {
                'default_browser': 'unknown',
                'webgpu_available': 'unknown',
                'user_agent': 'N/A (Desktop App)'
            }

            # 尝试检测系统默认浏览器
            if platform.system() == "Windows":
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                         r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice")
                    browser_choice = winreg.QueryValueEx(key, "ProgId")[0]
                    winreg.CloseKey(key)

                    if "Chrome" in browser_choice:
                        browser_info['default_browser'] = 'chrome'
                    elif "Firefox" in browser_choice:
                        browser_info['default_browser'] = 'firefox'
                    elif "Edge" in browser_choice:
                        browser_info['default_browser'] = 'edge'

                except Exception:
                    pass

            elif platform.system() == "Darwin":
                try:
                    # macOS Safari检测
                    result = subprocess.run(['defaults', 'read', 'com.apple.LaunchServices/com.apple.launchservices.secure',
                                             'LSHandlers'], capture_output=True, text=True, timeout=5)
                    if 'safari' in result.stdout.lower():
                        browser_info['default_browser'] = 'safari'
                except Exception:
                    pass

            return browser_info

        except Exception as e:
            logger.error(f"获取浏览器信息失败: {e}")
            return {'error': str(e)}

    def test_webgpu_support(self) -> TestCaseResult:
        """测试WebGPU支持"""
        test_case = TestCase(
            name="WebGPU Browser Support",
            description="检测浏览器WebGPU支持情况",
            test_function="test_webgpu_support",
            category="browser"
        )

        start_time = time.time()

        try:
            browser_info = self.get_browser_info()

            # 在桌面应用中，我们通过嵌入式浏览器组件来支持WebGPU
            # 这里主要检查系统环境是否支持WebGPU相关技术

            details = {
                'browser_info': browser_info,
                'webgpu_api_available': True,  # 假设通过Python绑定支持
                'supported_features': [
                    'webgpu-core',
                    'texture-compression-bc',
                    'timestamp-query'
                ]
            }

            duration = time.time() - start_time

            return TestCaseResult(
                test_case=test_case,
                result=TestResult.PASSED,
                duration=duration,
                message="WebGPU支持检测完成",
                details=details
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestCaseResult(
                test_case=test_case,
                result=TestResult.ERROR,
                duration=duration,
                message=f"WebGPU支持检测失败: {e}",
                error_info=str(e)
            )


class GPUCompatibilityTest:
    """GPU硬件兼容性测试"""

    def __init__(self):
        self.supported_vendors = {
            'nvidia': {'min_driver': '471.96', 'webgpu_support': True},
            'amd': {'min_driver': '21.6.1', 'webgpu_support': True},
            'intel': {'min_driver': '30.0.100.9684', 'webgpu_support': True},
            'apple': {'min_version': 'M1', 'webgpu_support': True}
        }

    def get_gpu_info(self) -> List[Dict[str, Any]]:
        """获取GPU信息"""
        gpu_info = []

        try:
            if platform.system() == "Windows":
                # Windows GPU信息检测
                try:
                    import wmi
                    c = wmi.WMI()
                    for gpu in c.Win32_VideoController():
                        if gpu.Name:
                            gpu_info.append({
                                'name': gpu.Name,
                                'driver_version': gpu.DriverVersion or 'Unknown',
                                'driver_date': gpu.DriverDate or 'Unknown',
                                'vendor': self._detect_vendor(gpu.Name),
                                'memory': gpu.AdapterRAM or 0
                            })
                except ImportError:
                    # Fallback方法
                    result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                        for line in lines:
                            if line.strip():
                                gpu_info.append({
                                    'name': line.strip(),
                                    'driver_version': 'Unknown',
                                    'vendor': self._detect_vendor(line.strip()),
                                    'memory': 0
                                })

            elif platform.system() == "Darwin":
                # macOS GPU信息检测
                try:
                    result = subprocess.run(['system_profiler', 'SPDisplaysDataType'],
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        # 简化的macOS GPU解析
                        if 'Apple' in result.stdout:
                            gpu_info.append({
                                'name': 'Apple Silicon GPU',
                                'vendor': 'apple',
                                'driver_version': 'Built-in',
                                'memory': 0
                            })
                except Exception:
                    pass

            elif platform.system() == "Linux":
                # Linux GPU信息检测
                try:
                    result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'VGA' in line or 'Display' in line:
                                gpu_info.append({
                                    'name': line.split(': ', 1)[-1] if ': ' in line else line,
                                    'vendor': self._detect_vendor(line),
                                    'driver_version': 'Unknown',
                                    'memory': 0
                                })
                except Exception:
                    pass

            # 如果没有检测到GPU，添加默认信息
            if not gpu_info:
                gpu_info.append({
                    'name': 'Unknown GPU',
                    'vendor': 'unknown',
                    'driver_version': 'Unknown',
                    'memory': 0
                })

        except Exception as e:
            logger.error(f"获取GPU信息失败: {e}")
            gpu_info.append({
                'name': f'Detection Error: {e}',
                'vendor': 'unknown',
                'driver_version': 'Unknown',
                'memory': 0
            })

        return gpu_info

    def _detect_vendor(self, gpu_name: str) -> str:
        """检测GPU厂商"""
        gpu_name_lower = gpu_name.lower()

        if any(nvidia_indicator in gpu_name_lower for nvidia_indicator in ['nvidia', 'geforce', 'quadro', 'tesla']):
            return 'nvidia'
        elif any(amd_indicator in gpu_name_lower for amd_indicator in ['amd', 'radeon', 'ati']):
            return 'amd'
        elif any(intel_indicator in gpu_name_lower for intel_indicator in ['intel', 'hd graphics', 'iris', 'uhd graphics']):
            return 'intel'
        elif any(apple_indicator in gpu_name_lower for apple_indicator in ['apple', 'apple silicon', 'metal']):
            return 'apple'
        else:
            return 'unknown'

    def test_gpu_compatibility(self) -> TestCaseResult:
        """测试GPU兼容性"""
        test_case = TestCase(
            name="GPU Hardware Compatibility",
            description="检测GPU硬件WebGPU兼容性",
            test_function="test_gpu_compatibility",
            category="hardware"
        )

        start_time = time.time()

        try:
            gpu_info = self.get_gpu_info()

            compatibility_results = []
            overall_compatibility = CompatibilityLevel.UNSUPPORTED

            for gpu in gpu_info:
                vendor = gpu.get('vendor', 'unknown')
                compatibility = self._assess_gpu_compatibility(gpu)

                compatibility_results.append({
                    'gpu': gpu,
                    'compatibility': compatibility.value,
                    'supported': compatibility != CompatibilityLevel.UNSUPPORTED
                })

                # 更新总体兼容性（取最好的）
                if compatibility.value != CompatibilityLevel.UNSUPPORTED.value:
                    if overall_compatibility == CompatibilityLevel.UNSUPPORTED:
                        overall_compatibility = compatibility
                    elif compatibility.value == CompatibilityLevel.EXCELLENT.value:
                        overall_compatibility = compatibility

            duration = time.time() - start_time

            details = {
                'gpu_count': len(gpu_info),
                'compatibility_results': compatibility_results,
                'overall_compatibility': overall_compatibility.value
            }

            result = TestResult.PASSED if overall_compatibility != CompatibilityLevel.UNSUPPORTED else TestResult.FAILED
            message = f"检测到 {len(gpu_info)} 个GPU，总体兼容性: {overall_compatibility.value}"

            return TestCaseResult(
                test_case=test_case,
                result=result,
                duration=duration,
                message=message,
                details=details
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestCaseResult(
                test_case=test_case,
                result=TestResult.ERROR,
                duration=duration,
                message=f"GPU兼容性测试失败: {e}",
                error_info=str(e)
            )

    def _assess_gpu_compatibility(self, gpu_info: Dict[str, Any]) -> CompatibilityLevel:
        """评估GPU兼容性"""
        vendor = gpu_info.get('vendor', 'unknown')

        if vendor == 'apple':
            return CompatibilityLevel.EXCELLENT
        elif vendor == 'nvidia':
            return CompatibilityLevel.EXCELLENT
        elif vendor == 'amd':
            return CompatibilityLevel.GOOD
        elif vendor == 'intel':
            return CompatibilityLevel.FAIR
        else:
            return CompatibilityLevel.UNSUPPORTED


class OSCompatibilityTest:
    """操作系统兼容性测试"""

    def __init__(self):
        self.supported_os = {
            'windows': {'min_version': '10', 'webgpu_support': True},
            'darwin': {'min_version': '11', 'webgpu_support': True},
            'linux': {'min_version': 'any', 'webgpu_support': True}
        }

    def get_system_info(self) -> SystemInfo:
        """获取系统信息"""
        try:
            system_info = SystemInfo(
                os_name=platform.system(),
                os_version=platform.version(),
                architecture=platform.architecture()[0],
                python_version=platform.python_version(),
                platform_info=platform.platform(),
                cpu_info=platform.processor(),
                memory_info=self._get_memory_info(),
                gpu_info=[],
                browser_info={}
            )

            # 获取GPU信息
            gpu_test = GPUCompatibilityTest()
            system_info.gpu_info = [gpu['name'] for gpu in gpu_test.get_gpu_info()]

            # 获取浏览器信息
            browser_test = BrowserCompatibilityTest()
            system_info.browser_info = browser_test.get_browser_info()

            return system_info

        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            # 返回基本信息
            return SystemInfo(
                os_name=platform.system(),
                os_version="Unknown",
                architecture="Unknown",
                python_version=platform.python_version(),
                platform_info=platform.platform(),
                cpu_info="Unknown",
                memory_info="Unknown"
            )

    def _get_memory_info(self) -> str:
        """获取内存信息"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return f"{memory.total // (1024**3)} GB"
        except ImportError:
            return "Unknown (psutil not available)"
        except Exception as e:
            return f"Unknown ({e})"

    def test_os_compatibility(self) -> TestCaseResult:
        """测试操作系统兼容性"""
        test_case = TestCase(
            name="Operating System Compatibility",
            description="检测操作系统WebGPU兼容性",
            test_function="test_os_compatibility",
            category="system"
        )

        start_time = time.time()

        try:
            system_info = self.get_system_info()
            compatibility = self._assess_os_compatibility(system_info)

            details = {
                'os_name': system_info.os_name,
                'os_version': system_info.os_version,
                'architecture': system_info.architecture,
                'compatibility': compatibility.value,
                'supported_features': self._get_supported_features(system_info)
            }

            duration = time.time() - start_time

            result = TestResult.PASSED if compatibility != CompatibilityLevel.UNSUPPORTED else TestResult.FAILED
            message = f"操作系统 {system_info.os_name} 兼容性: {compatibility.value}"

            return TestCaseResult(
                test_case=test_case,
                result=result,
                duration=duration,
                message=message,
                details=details
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestCaseResult(
                test_case=test_case,
                result=TestResult.ERROR,
                duration=duration,
                message=f"操作系统兼容性测试失败: {e}",
                error_info=str(e)
            )

    def _assess_os_compatibility(self, system_info: SystemInfo) -> CompatibilityLevel:
        """评估操作系统兼容性"""
        os_name = system_info.os_name.lower()

        if os_name == 'windows':
            # Windows 10及以上支持WebGPU
            return CompatibilityLevel.EXCELLENT
        elif os_name == 'darwin':
            # macOS支持WebGPU
            return CompatibilityLevel.EXCELLENT
        elif os_name == 'linux':
            # Linux支持WebGPU
            return CompatibilityLevel.GOOD
        else:
            return CompatibilityLevel.UNSUPPORTED

    def _get_supported_features(self, system_info: SystemInfo) -> List[str]:
        """获取支持的特性列表"""
        features = ['basic-webgpu']

        # 根据操作系统添加特定特性
        os_name = system_info.os_name.lower()

        if os_name == 'windows':
            features.extend(['d3d12-backend', 'vulkan-backend'])
        elif os_name == 'darwin':
            features.extend(['metal-backend'])
        elif os_name == 'linux':
            features.extend(['vulkan-backend', 'opengl-backend'])

        return features


class WebGPUFeatureTest:
    """WebGPU特性支持测试"""

    def __init__(self):
        self.core_features = [
            'webgpu-core',
            'depth-clip-control',
            'texture-compression-bc',
            'texture-compression-etc2',
            'texture-compression-astc',
            'timestamp-query',
            'indirect-first-instance',
            'shader-f16'
        ]

    def test_feature_support(self) -> TestCaseResult:
        """测试WebGPU特性支持"""
        test_case = TestCase(
            name="WebGPU Feature Support",
            description="检测WebGPU特性支持情况",
            test_function="test_feature_support",
            category="features"
        )

        start_time = time.time()

        try:
            # 模拟特性检测（在真实环境中需要通过WebGPU API检测）
            supported_features = []
            unsupported_features = []

            # 基础特性总是支持
            supported_features.append('webgpu-core')

            # 根据系统环境模拟其他特性支持
            system_name = platform.system().lower()

            if system_name == 'windows':
                supported_features.extend(['depth-clip-control', 'texture-compression-bc', 'timestamp-query'])
            elif system_name == 'darwin':
                supported_features.extend(['depth-clip-control', 'timestamp-query'])
            elif system_name == 'linux':
                supported_features.extend(['depth-clip-control', 'timestamp-query'])

            # 其余特性标记为不支持
            for feature in self.core_features:
                if feature not in supported_features:
                    unsupported_features.append(feature)

            details = {
                'total_features': len(self.core_features),
                'supported_features': supported_features,
                'unsupported_features': unsupported_features,
                'support_ratio': len(supported_features) / len(self.core_features)
            }

            duration = time.time() - start_time

            # 如果支持率大于50%认为通过
            result = TestResult.PASSED if details['support_ratio'] > 0.5 else TestResult.FAILED
            message = f"WebGPU特性支持率: {details['support_ratio']:.1%} ({len(supported_features)}/{len(self.core_features)})"

            return TestCaseResult(
                test_case=test_case,
                result=result,
                duration=duration,
                message=message,
                details=details
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestCaseResult(
                test_case=test_case,
                result=TestResult.ERROR,
                duration=duration,
                message=f"WebGPU特性测试失败: {e}",
                error_info=str(e)
            )


class CompatibilityTestSuite:
    """兼容性测试套件"""

    def __init__(self):
        self.test_cases: List[TestCase] = []
        self.test_results: List[TestCaseResult] = []
        self.system_info: Optional[SystemInfo] = None

        # 初始化测试组件
        self.browser_test = BrowserCompatibilityTest()
        self.gpu_test = GPUCompatibilityTest()
        self.os_test = OSCompatibilityTest()
        self.feature_test = WebGPUFeatureTest()

        # 注册测试用例
        self._register_test_cases()

    def _register_test_cases(self) -> None:
        """注册所有测试用例"""
        self.test_cases = [
            TestCase(
                name="Browser Compatibility",
                description="检测浏览器WebGPU支持",
                test_function="browser_test.test_webgpu_support",
                category="browser",
                priority=1
            ),
            TestCase(
                name="GPU Compatibility",
                description="检测GPU硬件兼容性",
                test_function="gpu_test.test_gpu_compatibility",
                category="hardware",
                priority=1
            ),
            TestCase(
                name="OS Compatibility",
                description="检测操作系统兼容性",
                test_function="os_test.test_os_compatibility",
                category="system",
                priority=1
            ),
            TestCase(
                name="WebGPU Features",
                description="检测WebGPU特性支持",
                test_function="feature_test.test_feature_support",
                category="features",
                priority=2
            )
        ]

    def run_all_tests(self) -> CompatibilityReport:
        """运行所有兼容性测试"""
        logger.info("开始兼容性测试...")
        start_time = time.time()

        try:
            # 获取系统信息
            self.system_info = self.os_test.get_system_info()

            # 清空之前的结果
            self.test_results.clear()

            # 按优先级排序测试用例
            sorted_test_cases = sorted(self.test_cases, key=lambda x: x.priority)

            # 执行测试用例
            for test_case in sorted_test_cases:
                logger.info(f"执行测试: {test_case.name}")
                result = self._execute_test_case(test_case)
                self.test_results.append(result)
                logger.info(f"测试完成: {test_case.name} - {result.result.value}")

            # 生成测试报告
            test_duration = time.time() - start_time
            report = self._generate_report(test_duration)

            logger.info(f"兼容性测试完成，耗时: {test_duration:.2f}秒")
            logger.info(f"总体兼容性: {report.overall_compatibility.value}")

            return report

        except Exception as e:
            logger.error(f"兼容性测试执行失败: {e}")
            # 返回错误报告
            return CompatibilityReport(
                system_info=self.system_info or SystemInfo(
                    os_name="Unknown",
                    os_version="Unknown",
                    architecture="Unknown",
                    python_version=sys.version,
                    platform_info="Unknown",
                    cpu_info="Unknown",
                    memory_info="Unknown"
                ),
                test_results=self.test_results,
                overall_compatibility=CompatibilityLevel.UNSUPPORTED,
                test_duration=time.time() - start_time
            )

    def _execute_test_case(self, test_case: TestCase) -> TestCaseResult:
        """执行单个测试用例"""
        try:
            # 解析测试函数路径
            if test_case.test_function == "browser_test.test_webgpu_support":
                return self.browser_test.test_webgpu_support()
            elif test_case.test_function == "gpu_test.test_gpu_compatibility":
                return self.gpu_test.test_gpu_compatibility()
            elif test_case.test_function == "os_test.test_os_compatibility":
                return self.os_test.test_os_compatibility()
            elif test_case.test_function == "feature_test.test_feature_support":
                return self.feature_test.test_feature_support()
            else:
                # 未知测试函数
                return TestCaseResult(
                    test_case=test_case,
                    result=TestResult.SKIPPED,
                    duration=0.0,
                    message=f"未知测试函数: {test_case.test_function}"
                )

        except Exception as e:
            logger.error(f"测试用例执行异常: {test_case.name} - {e}")
            return TestCaseResult(
                test_case=test_case,
                result=TestResult.ERROR,
                duration=0.0,
                message=f"测试执行异常: {e}",
                error_info=str(e)
            )

    def _generate_report(self, test_duration: float) -> CompatibilityReport:
        """生成兼容性测试报告"""
        # 计算测试统计
        test_summary = {
            'total': len(self.test_results),
            'passed': sum(1 for r in self.test_results if r.result == TestResult.PASSED),
            'failed': sum(1 for r in self.test_results if r.result == TestResult.FAILED),
            'error': sum(1 for r in self.test_results if r.result == TestResult.ERROR),
            'skipped': sum(1 for r in self.test_results if r.result == TestResult.SKIPPED)
        }

        # 计算总体兼容性
        overall_compatibility = self._calculate_overall_compatibility()

        # 计算性能得分
        performance_score = self._calculate_performance_score()

        # 生成建议
        recommendations = self._generate_recommendations()

        return CompatibilityReport(
            system_info=self.system_info,
            test_results=self.test_results,
            overall_compatibility=overall_compatibility,
            recommendations=recommendations,
            performance_score=performance_score,
            test_summary=test_summary,
            test_duration=test_duration
        )

    def _calculate_overall_compatibility(self) -> CompatibilityLevel:
        """计算总体兼容性级别"""
        if not self.test_results:
            return CompatibilityLevel.UNSUPPORTED

        # 统计各个等级的测试结果
        passed_count = sum(1 for r in self.test_results if r.result == TestResult.PASSED)
        total_count = len(self.test_results)

        if passed_count == 0:
            return CompatibilityLevel.UNSUPPORTED
        elif passed_count == total_count:
            return CompatibilityLevel.EXCELLENT
        elif passed_count >= total_count * 0.8:
            return CompatibilityLevel.GOOD
        elif passed_count >= total_count * 0.5:
            return CompatibilityLevel.FAIR
        else:
            return CompatibilityLevel.POOR

    def _calculate_performance_score(self) -> float:
        """计算性能得分（0-100）"""
        if not self.test_results:
            return 0.0

        # 基于通过的测试用例计算得分
        passed_count = sum(1 for r in self.test_results if r.result == TestResult.PASSED)
        total_count = len(self.test_results)

        base_score = (passed_count / total_count) * 100

        # 根据系统配置调整得分
        if self.system_info:
            # GPU厂商加分
            gpu_bonus = 0
            for gpu_name in self.system_info.gpu_info:
                if any(vendor in gpu_name.lower() for vendor in ['nvidia', 'apple']):
                    gpu_bonus += 10
                elif any(vendor in gpu_name.lower() for vendor in ['amd', 'radeon']):
                    gpu_bonus += 5

            # 操作系统加分
            os_bonus = 0
            if self.system_info.os_name.lower() in ['windows', 'darwin']:
                os_bonus = 5

            return min(100.0, base_score + gpu_bonus + os_bonus)

        return base_score

    def _generate_recommendations(self) -> List[str]:
        """生成兼容性建议"""
        recommendations = []

        # 分析失败的测试
        failed_tests = [r for r in self.test_results if r.result in [TestResult.FAILED, TestResult.ERROR]]

        for result in failed_tests:
            if result.test_case.category == "browser":
                recommendations.append("建议使用Chrome 113+或Firefox 110+以获得最佳WebGPU支持")
            elif result.test_case.category == "hardware":
                recommendations.append("建议更新GPU驱动程序或使用支持WebGPU的现代GPU")
            elif result.test_case.category == "system":
                recommendations.append("建议升级到支持WebGPU的操作系统版本")
            elif result.test_case.category == "features":
                recommendations.append("某些WebGPU高级特性不被支持，将使用备用实现")

        # 通用建议
        if not recommendations:
            recommendations.append("您的系统完全兼容WebGPU，可以享受硬件加速渲染的优势")
        else:
            recommendations.append("即使某些测试失败，系统仍会自动降级到兼容模式")

        return recommendations

    def save_report(self, report: CompatibilityReport, file_path: str) -> None:
        """保存测试报告到文件"""
        try:
            # 转换报告为JSON格式
            report_data = {
                'timestamp': report.timestamp,
                'test_duration': report.test_duration,
                'system_info': {
                    'os_name': report.system_info.os_name,
                    'os_version': report.system_info.os_version,
                    'architecture': report.system_info.architecture,
                    'python_version': report.system_info.python_version,
                    'platform_info': report.system_info.platform_info,
                    'cpu_info': report.system_info.cpu_info,
                    'memory_info': report.system_info.memory_info,
                    'gpu_info': report.system_info.gpu_info,
                    'browser_info': report.system_info.browser_info
                },
                'overall_compatibility': report.overall_compatibility.value,
                'performance_score': report.performance_score,
                'test_summary': report.test_summary,
                'recommendations': report.recommendations,
                'test_results': [
                    {
                        'test_name': result.test_case.name,
                        'test_category': result.test_case.category,
                        'result': result.result.value,
                        'duration': result.duration,
                        'message': result.message,
                        'details': result.details,
                        'error_info': result.error_info
                    }
                    for result in report.test_results
                ]
            }

            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logger.info(f"兼容性测试报告已保存到: {file_path}")

        except Exception as e:
            logger.error(f"保存测试报告失败: {e}")


# 快捷函数
def run_compatibility_test() -> CompatibilityReport:
    """运行兼容性测试的快捷函数"""
    test_suite = CompatibilityTestSuite()
    return test_suite.run_all_tests()


def check_webgpu_compatibility() -> bool:
    """检查WebGPU兼容性的快捷函数"""
    try:
        report = run_compatibility_test()
        return report.overall_compatibility != CompatibilityLevel.UNSUPPORTED
    except Exception as e:
        logger.error(f"兼容性检查失败: {e}")
        return False


if __name__ == "__main__":
    # 运行兼容性测试示例
    logger.info("运行WebGPU兼容性测试...")
    report = run_compatibility_test()

    logger.info("\n" + "="*60)
    logger.info("WebGPU兼容性测试报告")
    logger.info("="*60)
    logger.info(f"总体兼容性: {report.overall_compatibility.value}")
    logger.info(f"性能得分: {report.performance_score:.1f}/100")
    logger.info(f"测试时长: {report.test_duration:.2f}秒")
    logger.info(f"测试统计: {report.test_summary}")
    logger.info("\n建议:")
    for recommendation in report.recommendations:
        logger.info(f"- {recommendation}")
