"""
GPU兼容性检查器模块

负责：
1. 硬件兼容性检测
2. 驱动程序版本检查
3. 已知问题识别
4. 自动降级决策
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from .environment import GPUSupportLevel, GPUCapabilities

logger = logging.getLogger(__name__)


class CompatibilityLevel(Enum):
    """兼容性级别"""
    EXCELLENT = "excellent"     # 完全兼容，推荐使用
    GOOD = "good"              # 兼容性良好
    FAIR = "fair"              # 兼容性一般，可能有小问题
    POOR = "poor"              # 兼容性差，不推荐
    INCOMPATIBLE = "incompatible"  # 不兼容


@dataclass
class CompatibilityIssue:
    """兼容性问题"""
    issue_type: str
    severity: str  # critical, warning, info
    description: str
    workaround: Optional[str] = None
    affects_performance: bool = False


@dataclass
class CompatibilityReport:
    """兼容性报告"""
    level: CompatibilityLevel
    recommended_backend: GPUSupportLevel
    issues: List[CompatibilityIssue]
    performance_score: float  # 0-100
    recommendations: List[str]


class GPUCompatibilityChecker:
    """GPU兼容性检查器"""

    def __init__(self):
        # 已知问题数据库
        self.known_issues = self._load_known_issues()

        # GPU黑名单
        self.gpu_blacklist = {
            "Intel(R) HD Graphics 3000",
            "Intel(R) HD Graphics 2000",
            "AMD Radeon HD 5000",  # 系列
        }

        # 驱动版本要求
        self.driver_requirements = {
            "nvidia": {
                "min_version": "450.0",
                "recommended_version": "470.0"
            },
            "amd": {
                "min_version": "21.0",
                "recommended_version": "22.0"
            },
            "intel": {
                "min_version": "27.0",
                "recommended_version": "30.0"
            }
        }

    def _load_known_issues(self) -> Dict[str, List[CompatibilityIssue]]:
        """加载已知问题数据库"""
        return {
            "intel_hd": [
                CompatibilityIssue(
                    issue_type="driver",
                    severity="warning",
                    description="Intel集成显卡在某些驱动版本下可能出现渲染问题",
                    workaround="更新到最新驱动或使用OpenGL后备",
                    affects_performance=True
                )
            ],
            "amd_gcn1": [
                CompatibilityIssue(
                    issue_type="hardware",
                    severity="critical",
                    description="第一代GCN架构显卡不支持某些WebGPU特性",
                    workaround="自动降级到WebGL",
                    affects_performance=True
                )
            ],
            "nvidia_kepler": [
                CompatibilityIssue(
                    issue_type="performance",
                    severity="warning",
                    description="Kepler架构显卡性能可能不佳",
                    workaround="降低渲染质量设置",
                    affects_performance=True
                )
            ]
        }

    def check_compatibility(self, capabilities: GPUCapabilities, support_level: GPUSupportLevel) -> CompatibilityReport:
        """
        检查兼容性

        Args:
            capabilities: GPU能力信息
            support_level: 支持级别

        Returns:
            兼容性报告
        """
        logger.info(f"开始兼容性检查: {capabilities.adapter_name}")

        issues = []
        performance_score = 100.0
        recommendations = []

        # 1. 检查GPU型号兼容性
        gpu_issues, gpu_score = self._check_gpu_model(capabilities)
        issues.extend(gpu_issues)
        performance_score = min(performance_score, gpu_score)

        # 2. 检查内存容量
        memory_issues, memory_score = self._check_memory_capacity(capabilities)
        issues.extend(memory_issues)
        performance_score = min(performance_score, memory_score)

        # 3. 检查纹理支持
        texture_issues, texture_score = self._check_texture_support(capabilities)
        issues.extend(texture_issues)
        performance_score = min(performance_score, texture_score)

        # 4. 检查驱动版本
        driver_issues, driver_score = self._check_driver_version(capabilities)
        issues.extend(driver_issues)
        performance_score = min(performance_score, driver_score)

        # 5. 确定兼容性级别
        compatibility_level = self._determine_compatibility_level(
            issues, performance_score, support_level)

        # 6. 推荐后端
        recommended_backend = self._recommend_backend(
            compatibility_level, support_level, issues)

        # 7. 生成建议
        recommendations = self._generate_recommendations(
            issues, capabilities, support_level)

        report = CompatibilityReport(
            level=compatibility_level,
            recommended_backend=recommended_backend,
            issues=issues,
            performance_score=performance_score,
            recommendations=recommendations
        )

        logger.info(f"兼容性检查完成: {compatibility_level.value}, 性能评分: {performance_score:.1f}")
        return report

    def _check_gpu_model(self, capabilities: GPUCapabilities) -> Tuple[List[CompatibilityIssue], float]:
        """检查GPU型号"""
        issues = []
        score = 100.0

        adapter_name = capabilities.adapter_name.lower()

        # 检查黑名单
        for blacklisted_gpu in self.gpu_blacklist:
            if blacklisted_gpu.lower() in adapter_name:
                issues.append(CompatibilityIssue(
                    issue_type="hardware",
                    severity="critical",
                    description=f"GPU型号 {capabilities.adapter_name} 已知存在兼容性问题",
                    workaround="建议使用软件渲染",
                    affects_performance=True
                ))
                score = 20.0
                break

        # 检查已知问题
        if "intel" in adapter_name and "hd" in adapter_name:
            if "intel_hd" in self.known_issues:
                issues.extend(self.known_issues["intel_hd"])
                score = min(score, 70.0)

        elif "amd" in adapter_name or "radeon" in adapter_name:
            # 检查AMD GCN架构
            if any(gcn1_gpu in adapter_name for gcn1_gpu in ["hd 7000", "hd 6000", "r9 200"]):
                if "amd_gcn1" in self.known_issues:
                    issues.extend(self.known_issues["amd_gcn1"])
                    score = min(score, 60.0)

        elif "nvidia" in adapter_name or "geforce" in adapter_name:
            # 检查Kepler架构
            if any(kepler_gpu in adapter_name for kepler_gpu in ["gtx 600", "gtx 700", "gt 600"]):
                if "nvidia_kepler" in self.known_issues:
                    issues.extend(self.known_issues["nvidia_kepler"])
                    score = min(score, 80.0)

        return issues, score

    def _check_memory_capacity(self, capabilities: GPUCapabilities) -> Tuple[List[CompatibilityIssue], float]:
        """检查内存容量"""
        issues = []
        score = 100.0

        memory_mb = capabilities.memory_mb

        if memory_mb < 256:
            issues.append(CompatibilityIssue(
                issue_type="memory",
                severity="critical",
                description=f"GPU内存容量过低: {memory_mb}MB",
                workaround="降低渲染质量或使用软件渲染",
                affects_performance=True
            ))
            score = 30.0
        elif memory_mb < 512:
            issues.append(CompatibilityIssue(
                issue_type="memory",
                severity="warning",
                description=f"GPU内存容量较低: {memory_mb}MB",
                workaround="限制最大数据点数量",
                affects_performance=True
            ))
            score = 60.0
        elif memory_mb < 1024:
            score = 80.0

        return issues, score

    def _check_texture_support(self, capabilities: GPUCapabilities) -> Tuple[List[CompatibilityIssue], float]:
        """检查纹理支持"""
        issues = []
        score = 100.0

        max_texture_size = capabilities.max_texture_size

        if max_texture_size < 2048:
            issues.append(CompatibilityIssue(
                issue_type="texture",
                severity="critical",
                description=f"纹理大小支持不足: {max_texture_size}",
                workaround="使用图块渲染",
                affects_performance=True
            ))
            score = 40.0
        elif max_texture_size < 4096:
            issues.append(CompatibilityIssue(
                issue_type="texture",
                severity="warning",
                description=f"纹理大小支持有限: {max_texture_size}",
                workaround="限制图表尺寸",
                affects_performance=False
            ))
            score = 70.0

        return issues, score

    def _check_driver_version(self, capabilities: GPUCapabilities) -> Tuple[List[CompatibilityIssue], float]:
        """检查驱动版本"""
        issues = []
        score = 100.0

        # 这里需要实际的驱动版本检测逻辑
        # 目前使用模拟数据

        vendor = capabilities.vendor.lower()
        if "nvidia" in vendor:
            # 模拟NVIDIA驱动版本检查
            issues.append(CompatibilityIssue(
                issue_type="driver",
                severity="info",
                description="建议更新到最新NVIDIA驱动以获得最佳性能",
                workaround="访问NVIDIA官网下载最新驱动",
                affects_performance=False
            ))
        elif "amd" in vendor or "advanced micro devices" in vendor:
            # 模拟AMD驱动版本检查
            pass
        elif "intel" in vendor:
            # 模拟Intel驱动版本检查
            pass

        return issues, score

    def _determine_compatibility_level(self, issues: List[CompatibilityIssue],
                                       performance_score: float,
                                       support_level: GPUSupportLevel) -> CompatibilityLevel:
        """确定兼容性级别"""

        # 检查是否有关键问题
        has_critical_issues = any(issue.severity == "critical" for issue in issues)

        if has_critical_issues:
            return CompatibilityLevel.INCOMPATIBLE

        if support_level == GPUSupportLevel.NONE:
            return CompatibilityLevel.INCOMPATIBLE

        # 根据性能评分确定级别
        if performance_score >= 90:
            return CompatibilityLevel.EXCELLENT
        elif performance_score >= 75:
            return CompatibilityLevel.GOOD
        elif performance_score >= 60:
            return CompatibilityLevel.FAIR
        else:
            return CompatibilityLevel.POOR

    def _recommend_backend(self, compatibility_level: CompatibilityLevel,
                           current_support: GPUSupportLevel,
                           issues: List[CompatibilityIssue]) -> GPUSupportLevel:
        """推荐后端"""

        if compatibility_level == CompatibilityLevel.INCOMPATIBLE:
            return GPUSupportLevel.BASIC

        # 检查是否有特定的降级建议
        for issue in issues:
            if "降级到WebGL" in issue.workaround:
                return GPUSupportLevel.WEBGL
            elif "软件渲染" in issue.workaround:
                return GPUSupportLevel.BASIC

        # 根据兼容性级别推荐
        if compatibility_level in [CompatibilityLevel.EXCELLENT, CompatibilityLevel.GOOD]:
            return current_support  # 使用当前最佳支持级别
        elif compatibility_level == CompatibilityLevel.FAIR:
            # 如果当前是WebGPU但兼容性一般，降级到WebGL
            if current_support == GPUSupportLevel.WEBGPU:
                return GPUSupportLevel.WEBGL
            return current_support
        else:  # POOR
            return GPUSupportLevel.BASIC

    def _generate_recommendations(self, issues: List[CompatibilityIssue],
                                  capabilities: GPUCapabilities,
                                  support_level: GPUSupportLevel) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 基于问题生成建议
        for issue in issues:
            if issue.workaround:
                recommendations.append(issue.workaround)

        # 基于硬件能力生成建议
        if capabilities.memory_mb < 1024:
            recommendations.append("建议限制同时显示的数据点数量以节省内存")

        if capabilities.max_texture_size < 4096:
            recommendations.append("建议使用较小的图表尺寸以避免纹理限制")

        if not capabilities.supports_compute:
            recommendations.append("设备不支持计算着色器，某些高级功能可能不可用")

        # 通用优化建议
        if support_level == GPUSupportLevel.WEBGL:
            recommendations.append("使用WebGL后备，考虑启用降采样以提高性能")
        elif support_level == GPUSupportLevel.BASIC:
            recommendations.append("使用软件渲染，建议减少数据复杂度")

        # 去重
        return list(set(recommendations))

    def get_fallback_chain(self, report: CompatibilityReport) -> List[GPUSupportLevel]:
        """获取降级链"""
        chain = []

        if report.level in [CompatibilityLevel.EXCELLENT, CompatibilityLevel.GOOD]:
            # 高兼容性：首选推荐后端
            chain = [report.recommended_backend]
        else:
            # 低兼容性：提供完整降级链
            chain = [GPUSupportLevel.WEBGPU, GPUSupportLevel.WEBGL,
                     GPUSupportLevel.NATIVE, GPUSupportLevel.BASIC]

        # 根据具体问题调整降级链
        has_hardware_issues = any(issue.issue_type == "hardware" for issue in report.issues)
        if has_hardware_issues:
            # 硬件问题：跳过GPU渲染
            chain = [GPUSupportLevel.BASIC]

        return chain

    def should_auto_fallback(self, report: CompatibilityReport) -> bool:
        """是否应该自动降级"""
        return (report.level in [CompatibilityLevel.POOR, CompatibilityLevel.INCOMPATIBLE] or
                any(issue.severity == "critical" for issue in report.issues))

    def get_performance_settings(self, report: CompatibilityReport) -> Dict[str, Any]:
        """获取性能优化设置"""
        settings = {
            'max_points_per_batch': 10000,
            'enable_anti_aliasing': True,
            'enable_transparency': True,
            'texture_quality': 'high',
            'animation_fps': 60
        }

        # 根据兼容性级别调整
        if report.level == CompatibilityLevel.POOR:
            settings.update({
                'max_points_per_batch': 5000,
                'enable_anti_aliasing': False,
                'texture_quality': 'medium',
                'animation_fps': 30
            })
        elif report.level == CompatibilityLevel.FAIR:
            settings.update({
                'max_points_per_batch': 7500,
                'texture_quality': 'medium',
                'animation_fps': 45
            })

        # 根据内存容量调整
        if report.performance_score < 60:
            settings.update({
                'max_points_per_batch': settings['max_points_per_batch'] // 2,
                'enable_transparency': False
            })

        return settings
