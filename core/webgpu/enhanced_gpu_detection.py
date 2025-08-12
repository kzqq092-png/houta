"""
增强的GPU检测模块 - 支持真实的多GPU环境检测

提供：
1. 真实的GPU硬件信息检测
2. 多GPU适配器枚举
3. 独立显卡优先选择
4. 性能和功耗偏好支持
"""

import logging
import platform
import subprocess
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GPUType(Enum):
    """GPU类型"""
    INTEGRATED = "integrated"    # 集成显卡
    DISCRETE = "discrete"        # 独立显卡
    VIRTUAL = "virtual"          # 虚拟GPU
    UNKNOWN = "unknown"          # 未知类型


class PowerPreference(Enum):
    """电源偏好"""
    LOW_POWER = "low-power"      # 低功耗（集成显卡）
    HIGH_PERFORMANCE = "high-performance"  # 高性能（独立显卡）


@dataclass
class GPUAdapterInfo:
    """GPU适配器信息"""
    adapter_id: str
    name: str
    vendor: str
    device_id: str
    memory_mb: int
    gpu_type: GPUType
    driver_version: str
    is_default: bool
    supports_webgpu: bool
    performance_score: float


class EnhancedGPUDetector:
    """增强的GPU检测器"""

    def __init__(self):
        self.platform = platform.system().lower()
        self._adapters_cache: Optional[List[GPUAdapterInfo]] = None

    def detect_all_adapters(self) -> List[GPUAdapterInfo]:
        """检测所有可用的GPU适配器"""
        if self._adapters_cache is not None:
            return self._adapters_cache

        try:
            if self.platform == "windows":
                adapters = self._detect_windows_adapters()
            elif self.platform == "linux":
                adapters = self._detect_linux_adapters()
            elif self.platform == "darwin":
                adapters = self._detect_macos_adapters()
            else:
                logger.warning(f"不支持的平台: {self.platform}")
                adapters = self._create_fallback_adapter()

            self._adapters_cache = adapters
            return adapters

        except Exception as e:
            logger.error(f"GPU检测失败: {e}")
            return self._create_fallback_adapter()

    def _detect_windows_adapters(self) -> List[GPUAdapterInfo]:
        """检测Windows下的GPU适配器"""
        adapters = []

        try:
            # 使用更简单的wmic命令获取GPU信息
            cmd = [
                "wmic", "path", "win32_VideoController", "get",
                "Name,AdapterRAM,PNPDeviceID,DriverVersion", "/format:list"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning(f"wmic命令执行失败，尝试备用方法: {result.stderr}")
                return self._detect_windows_adapters_backup()

            # 解析list格式的输出
            raw_output = result.stdout.strip()
            logger.debug(f"🔍 wmic原始输出: {raw_output[:500]}...")  # 显示前500字符用于调试

            # 分割每个GPU设备的信息块
            gpu_blocks = []
            current_block = {}

            for line in raw_output.split('\n'):
                line = line.strip()
                if not line:
                    if current_block:
                        gpu_blocks.append(current_block)
                        current_block = {}
                    continue

                if '=' in line:
                    key, value = line.split('=', 1)
                    current_block[key.strip()] = value.strip()

            # 添加最后一个块
            if current_block:
                gpu_blocks.append(current_block)

            logger.info(f"🔍 解析到 {len(gpu_blocks)} 个GPU信息块")

            for i, gpu_info in enumerate(gpu_blocks, 1):
                try:
                    # 提取GPU信息
                    gpu_name = gpu_info.get('Name', '').strip()
                    adapter_ram = gpu_info.get('AdapterRAM', '0').strip()
                    pnp_device_id = gpu_info.get('PNPDeviceID', '').strip()
                    driver_version = gpu_info.get('DriverVersion', '').strip()

                    # 跳过无效的GPU（如Microsoft基础显示适配器）
                    if not gpu_name or 'Microsoft' in gpu_name or 'Basic' in gpu_name:
                        logger.debug(f"跳过无效GPU: {gpu_name}")
                        continue

                    # 计算显存大小
                    try:
                        memory_mb = int(adapter_ram) // (1024 * 1024) if adapter_ram.isdigit() else 0
                        # 修复0MB的问题：对于显存为0的情况，根据GPU名称估算
                        if memory_mb == 0:
                            memory_mb = self._estimate_memory_by_name(gpu_name)
                    except (ValueError, TypeError):
                        memory_mb = self._estimate_memory_by_name(gpu_name)

                    # 提取厂商信息
                    vendor = self._extract_vendor(gpu_name)

                    # 判断GPU类型
                    gpu_type = self._determine_gpu_type_by_name(gpu_name)

                    # 提取设备ID
                    device_id = self._extract_device_id_from_pnp(pnp_device_id)

                    adapter = GPUAdapterInfo(
                        adapter_id=f"adapter_{i}",
                        name=gpu_name,
                        vendor=vendor,
                        device_id=device_id,
                        memory_mb=memory_mb,
                        gpu_type=gpu_type,
                        driver_version=driver_version,
                        is_default=(i == 1),
                        supports_webgpu=True,
                        performance_score=self._calculate_performance_score(gpu_type, memory_mb)
                    )
                    adapters.append(adapter)

                    logger.info(f"✅ 解析GPU {i}: {gpu_name} ({vendor}) - {memory_mb}MB - {gpu_type.value}")

                except Exception as e:
                    logger.warning(f"解析GPU信息失败: {e}, gpu_info: {gpu_info}")

        except Exception as e:
            logger.error(f"Windows GPU检测失败: {e}")

        return adapters if adapters else self._create_fallback_adapter()

    def _detect_windows_adapters_backup(self) -> List[GPUAdapterInfo]:
        """Windows GPU检测的备用方法"""
        adapters = []

        try:
            # 使用PowerShell获取GPU信息
            cmd = [
                "powershell", "-Command",
                "Get-WmiObject -Class Win32_VideoController | Select-Object Name,AdapterRAM,PNPDeviceID,DriverVersion | ConvertTo-Json"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                gpu_data = json.loads(result.stdout)

                # 处理单个GPU的情况
                if isinstance(gpu_data, dict):
                    gpu_data = [gpu_data]

                for i, gpu in enumerate(gpu_data, 1):
                    gpu_name = gpu.get('Name', '').strip()
                    if not gpu_name or 'Microsoft' in gpu_name:
                        continue

                    memory_mb = 0
                    if gpu.get('AdapterRAM'):
                        try:
                            memory_mb = int(gpu['AdapterRAM']) // (1024 * 1024)
                        except:
                            memory_mb = self._estimate_memory_by_name(gpu_name)
                    else:
                        memory_mb = self._estimate_memory_by_name(gpu_name)

                    vendor = self._extract_vendor(gpu_name)
                    gpu_type = self._determine_gpu_type_by_name(gpu_name)
                    device_id = self._extract_device_id_from_pnp(gpu.get('PNPDeviceID', ''))

                    adapter = GPUAdapterInfo(
                        adapter_id=f"adapter_{i}",
                        name=gpu_name,
                        vendor=vendor,
                        device_id=device_id,
                        memory_mb=memory_mb,
                        gpu_type=gpu_type,
                        driver_version=gpu.get('DriverVersion', ''),
                        is_default=(i == 1),
                        supports_webgpu=True,
                        performance_score=self._calculate_performance_score(gpu_type, memory_mb)
                    )
                    adapters.append(adapter)

        except Exception as e:
            logger.warning(f"PowerShell备用方法也失败: {e}")

        return adapters

    def _detect_linux_adapters(self) -> List[GPUAdapterInfo]:
        """检测Linux下的GPU适配器"""
        adapters = []

        try:
            # 尝试使用lspci获取GPU信息
            cmd = ["lspci", "-nn", "-v"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_gpu = None

                for line in lines:
                    if "VGA compatible controller" in line or "3D controller" in line:
                        # 提取GPU信息
                        parts = line.split(': ')
                        if len(parts) >= 2:
                            gpu_name = parts[1].split(' [')[0]
                            vendor = self._extract_vendor(gpu_name)

                            adapter = GPUAdapterInfo(
                                adapter_id=f"adapter_{len(adapters) + 1}",
                                name=gpu_name,
                                vendor=vendor,
                                device_id="",
                                memory_mb=self._estimate_memory_linux(gpu_name),
                                gpu_type=self._determine_gpu_type_linux(gpu_name),
                                driver_version="",
                                is_default=(len(adapters) == 0),
                                supports_webgpu=True,
                                performance_score=self._calculate_performance_score_by_name(gpu_name)
                            )
                            adapters.append(adapter)

        except Exception as e:
            logger.error(f"Linux GPU检测失败: {e}")

        return adapters if adapters else self._create_fallback_adapter()

    def _detect_macos_adapters(self) -> List[GPUAdapterInfo]:
        """检测macOS下的GPU适配器"""
        adapters = []

        try:
            # 使用system_profiler获取GPU信息
            cmd = ["system_profiler", "SPDisplaysDataType", "-json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                displays = data.get("SPDisplaysDataType", [])

                for i, display in enumerate(displays):
                    gpu_name = display.get("sppci_model", "Unknown GPU")
                    vendor = display.get("sppci_vendor", "Unknown")
                    memory_str = display.get("spdisplays_vram", "0 MB")

                    # 解析显存大小
                    memory_mb = self._parse_memory_string(memory_str)

                    adapter = GPUAdapterInfo(
                        adapter_id=f"adapter_{i + 1}",
                        name=gpu_name,
                        vendor=vendor,
                        device_id="",
                        memory_mb=memory_mb,
                        gpu_type=self._determine_gpu_type_macos(gpu_name),
                        driver_version="",
                        is_default=(i == 0),
                        supports_webgpu=True,
                        performance_score=self._calculate_performance_score_by_name(gpu_name)
                    )
                    adapters.append(adapter)

        except Exception as e:
            logger.error(f"macOS GPU检测失败: {e}")

        return adapters if adapters else self._create_fallback_adapter()

    def select_best_adapter(self,
                            power_preference: PowerPreference = PowerPreference.HIGH_PERFORMANCE,
                            require_discrete: bool = False) -> Optional[GPUAdapterInfo]:
        """选择最佳GPU适配器"""
        adapters = self.detect_all_adapters()

        if not adapters:
            return None

        # 过滤条件
        candidates = adapters

        if require_discrete:
            candidates = [a for a in candidates if a.gpu_type == GPUType.DISCRETE]
            if not candidates:
                logger.warning("未找到独立显卡，回退到所有适配器")
                candidates = adapters

        # 根据电源偏好排序
        if power_preference == PowerPreference.HIGH_PERFORMANCE:
            # 优先选择独立显卡和高性能分数
            candidates.sort(key=lambda x: (
                x.gpu_type == GPUType.DISCRETE,
                x.performance_score,
                x.memory_mb
            ), reverse=True)
        else:
            # 优先选择集成显卡和低功耗
            candidates.sort(key=lambda x: (
                x.gpu_type == GPUType.INTEGRATED,
                -x.performance_score,  # 性能分数越低越好（低功耗）
                -x.memory_mb
            ), reverse=True)

        return candidates[0] if candidates else None

    def _create_fallback_adapter(self) -> List[GPUAdapterInfo]:
        """创建回退适配器"""
        return [GPUAdapterInfo(
            adapter_id="fallback_adapter",
            name="Generic GPU Adapter",
            vendor="Unknown",
            device_id="",
            memory_mb=1024,
            gpu_type=GPUType.UNKNOWN,
            driver_version="",
            is_default=True,
            supports_webgpu=True,
            performance_score=50.0
        )]

    def _determine_gpu_type(self, name: str, device_info: str) -> GPUType:
        """确定GPU类型（旧方法，保持兼容性）"""
        return self._determine_gpu_type_by_name(name)

    def _determine_gpu_type_by_name(self, name: str) -> GPUType:
        """根据GPU名称确定GPU类型"""
        name_lower = name.lower()

        # 集成显卡关键词
        integrated_keywords = [
            "intel hd", "intel uhd", "intel iris", "intel graphics",
            "amd radeon graphics", "radeon graphics", "vega",
            "apple m1", "apple m2", "apple m3"
        ]

        # 独立显卡关键词
        discrete_keywords = [
            "geforce", "quadro", "tesla", "titan",
            "radeon rx", "radeon pro", "radeon r9", "radeon r7",
            "arc a", "intel arc"
        ]

        if any(keyword in name_lower for keyword in integrated_keywords):
            return GPUType.INTEGRATED
        elif any(keyword in name_lower for keyword in discrete_keywords):
            return GPUType.DISCRETE
        else:
            return GPUType.UNKNOWN

    def _estimate_memory_by_name(self, name: str) -> int:
        """根据GPU名称估算显存大小"""
        name_lower = name.lower()

        # 高端显卡
        if any(gpu in name_lower for gpu in ["rtx 4090", "titan"]):
            return 24576  # 24GB
        elif any(gpu in name_lower for gpu in ["rtx 4080", "rtx 3080 ti"]):
            return 16384  # 16GB
        elif any(gpu in name_lower for gpu in ["rtx 4070", "rtx 3080", "rx 6800 xt"]):
            return 12288  # 12GB
        elif any(gpu in name_lower for gpu in ["rtx 4060", "rtx 3070", "rx 6700 xt"]):
            return 8192   # 8GB
        elif any(gpu in name_lower for gpu in ["rtx 3060", "gtx 1660", "rx 6600"]):
            return 6144   # 6GB
        elif any(gpu in name_lower for gpu in ["gtx 1650", "rx 580"]):
            return 4096   # 4GB
        elif any(gpu in name_lower for gpu in ["intel hd", "intel uhd"]):
            return 1024   # 1GB（集成显卡）
        else:
            return 2048   # 默认2GB

    def _extract_device_id_from_pnp(self, pnp_id: str) -> str:
        """从PNP设备ID中提取设备ID"""
        try:
            # PNP ID格式：PCI\VEN_10DE&DEV_2786&SUBSYS_...
            if "DEV_" in pnp_id:
                start = pnp_id.find("DEV_") + 4
                end = pnp_id.find("&", start)
                if end == -1:
                    end = len(pnp_id)
                return pnp_id[start:end]
        except:
            pass
        return ""

    def _determine_gpu_type_linux(self, name: str) -> GPUType:
        """Linux下确定GPU类型"""
        name_lower = name.lower()

        if any(keyword in name_lower for keyword in ["intel", "integrated"]):
            return GPUType.INTEGRATED
        elif any(keyword in name_lower for keyword in ["nvidia", "amd", "radeon"]):
            return GPUType.DISCRETE
        else:
            return GPUType.UNKNOWN

    def _determine_gpu_type_macos(self, name: str) -> GPUType:
        """macOS下确定GPU类型"""
        name_lower = name.lower()

        if any(keyword in name_lower for keyword in ["intel", "apple m1", "apple m2"]):
            return GPUType.INTEGRATED
        elif any(keyword in name_lower for keyword in ["amd", "nvidia"]):
            return GPUType.DISCRETE
        else:
            return GPUType.UNKNOWN

    def _extract_vendor(self, name: str) -> str:
        """提取GPU厂商"""
        name_lower = name.lower()

        if "nvidia" in name_lower or "geforce" in name_lower:
            return "NVIDIA"
        elif "amd" in name_lower or "radeon" in name_lower:
            return "AMD"
        elif "intel" in name_lower:
            return "Intel"
        elif "apple" in name_lower:
            return "Apple"
        else:
            return "Unknown"

    def _estimate_memory_linux(self, name: str) -> int:
        """Linux下估算显存大小"""
        name_lower = name.lower()

        # 根据GPU名称估算显存（简化实现）
        if "rtx 4090" in name_lower:
            return 24576
        elif "rtx 4080" in name_lower:
            return 16384
        elif "rtx 4070" in name_lower:
            return 12288
        elif "rtx 3080" in name_lower:
            return 10240
        elif "gtx" in name_lower:
            return 8192
        else:
            return 4096

    def _parse_memory_string(self, memory_str: str) -> int:
        """解析显存字符串"""
        try:
            # 例如: "8 GB" -> 8192
            parts = memory_str.split()
            if len(parts) >= 2:
                value = float(parts[0])
                unit = parts[1].upper()

                if unit.startswith("GB"):
                    return int(value * 1024)
                elif unit.startswith("MB"):
                    return int(value)

        except (ValueError, IndexError):
            pass

        return 1024  # 默认值

    def _calculate_performance_score(self, gpu_type: GPUType, memory_mb: int) -> float:
        """计算性能分数"""
        base_score = 50.0

        # GPU类型加分
        if gpu_type == GPUType.DISCRETE:
            base_score += 30.0
        elif gpu_type == GPUType.INTEGRATED:
            base_score += 10.0

        # 显存大小加分
        memory_score = min(memory_mb / 1024 * 10, 20.0)

        return min(base_score + memory_score, 100.0)

    def _calculate_performance_score_by_name(self, name: str) -> float:
        """根据名称计算性能分数"""
        name_lower = name.lower()

        # 高端GPU
        if any(gpu in name_lower for gpu in ["rtx 4090", "rtx 4080", "rx 7900"]):
            return 95.0
        elif any(gpu in name_lower for gpu in ["rtx 4070", "rtx 3080", "rx 6800"]):
            return 85.0
        elif any(gpu in name_lower for gpu in ["rtx 3070", "gtx 1080", "rx 6600"]):
            return 75.0
        elif any(gpu in name_lower for gpu in ["gtx 1660", "rx 580"]):
            return 65.0
        elif any(gpu in name_lower for gpu in ["intel uhd", "intel hd"]):
            return 35.0
        else:
            return 50.0


# 全局实例
_gpu_detector = None


def get_gpu_detector() -> EnhancedGPUDetector:
    """获取GPU检测器实例"""
    global _gpu_detector
    if _gpu_detector is None:
        _gpu_detector = EnhancedGPUDetector()
    return _gpu_detector
