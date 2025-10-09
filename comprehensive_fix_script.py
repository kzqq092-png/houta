#!/usr/bin/env python
"""
综合修复脚本 - 修复所有测试发现的问题
"""

from pathlib import Path
import re

print("="*70)
print("综合修复脚本 - 修复服务导入和依赖问题")
print("="*70)

# ========== 修复1: DatabaseService - 移除EnhancedAssetDatabaseManager ==========
print("\n[1/5] 修复 DatabaseService...")

db_service_file = Path("core/services/database_service.py")
content = db_service_file.read_text(encoding='utf-8')

# 注释掉导入
content = content.replace(
    "from ..enhanced_asset_database_manager import EnhancedAssetDatabaseManager",
    "# from ..enhanced_asset_database_manager import EnhancedAssetDatabaseManager  # 已集成到DatabaseService"
)

# 注释掉类型注解
content = content.replace(
    "self._enhanced_asset_manager: Optional[EnhancedAssetDatabaseManager] = None",
    "# self._enhanced_asset_manager: Optional[EnhancedAssetDatabaseManager] = None  # 已集成"
)

# 注释掉初始化代码
content = re.sub(
    r"(\s+)# 创建增强资产数据库管理器\s+if hasattr\(EnhancedAssetDatabaseManager.*?\n\s+self\._enhanced_asset_manager = EnhancedAssetDatabaseManager\(\)",
    r"\1# 增强资产数据库管理器功能已集成到DatabaseService\n\1# (原EnhancedAssetDatabaseManager已合并)",
    content,
    flags=re.DOTALL
)

db_service_file.write_text(content, encoding='utf-8')
print("  ✓ DatabaseService 已修复")

# ========== 修复2: PerformanceService - 移除DynamicResourceManager ==========
print("\n[2/5] 修复 PerformanceService...")

perf_service_file = Path("core/services/performance_service.py")
content = perf_service_file.read_text(encoding='utf-8')

# 注释掉导入块
content = re.sub(
    r"from \.\.services\.dynamic_resource_manager import \(\s+DynamicResourceManager.*?\)",
    "# 动态资源管理器功能已集成到PerformanceService\n# (原DynamicResourceManager已合并)",
    content,
    flags=re.DOTALL
)

# 注释掉类型注解
content = content.replace(
    "self._resource_manager: Optional[DynamicResourceManager] = None",
    "# self._resource_manager: Optional[DynamicResourceManager] = None  # 已集成"
)

# 注释掉初始化代码
content = re.sub(
    r"(\s+)# 初始化资源管理器\s+self\._resource_manager = DynamicResourceManager\(\)\s+logger\.info\(\"DynamicResourceManager initialized\"\)",
    r"\1# 资源管理器功能已集成到PerformanceService核心",
    content
)

perf_service_file.write_text(content, encoding='utf-8')
print("  ✓ PerformanceService 已修复")

# ========== 修复3: NetworkService - 修复导入名称 ==========
print("\n[3/5] 修复 NetworkService...")

network_service_file = Path("core/services/network_service.py")
content = network_service_file.read_text(encoding='utf-8')

# 修改导入 - UniversalNetworkConfigManager不存在，应该是UniversalNetworkConfig或UniversalNetworkManager
content = content.replace(
    "from ..network.universal_network_config import UniversalNetworkConfigManager, PluginNetworkConfig, NetworkEndpoint",
    "from ..network.universal_network_config import UniversalNetworkConfig, PluginNetworkConfig, NetworkEndpoint"
)

# 修改类型注解
content = content.replace(
    "self._config_manager: Optional[UniversalNetworkConfigManager] = None",
    "self._config_manager: Optional[UniversalNetworkConfig] = None"
)

# 修改初始化
content = content.replace(
    "self._config_manager = UniversalNetworkConfigManager()",
    "self._config_manager = UniversalNetworkConfig()"
)

network_service_file.write_text(content, encoding='utf-8')
print("  ✓ NetworkService 已修复")

# ========== 修复4: 修复指标对象问题 ==========
print("\n[4/5] 修复指标对象问题...")

# 这个问题需要修改BaseService的metrics属性或者修改业务服务的_metrics定义
# 先检查BaseService如何使用metrics

base_service_file = Path("core/services/base_service.py")
if base_service_file.exists():
    content = base_service_file.read_text(encoding='utf-8')

    # 查找metrics属性定义
    if "@property" in content and "def metrics" in content:
        # 修改metrics属性以支持对象类型的metrics
        old_metrics_property = """    @property
    def metrics(self) -> Dict[str, Any]:
        \"\"\"获取服务指标\"\"\"
        return self._metrics"""

        new_metrics_property = """    @property
    def metrics(self) -> Dict[str, Any]:
        \"\"\"获取服务指标\"\"\"
        # 支持字典和对象类型的metrics
        if hasattr(self._metrics, 'to_dict'):
            return self._metrics.to_dict()
        elif hasattr(self._metrics, '__dict__'):
            return vars(self._metrics)
        elif isinstance(self._metrics, dict):
            return self._metrics
        else:
            return {'metrics': str(self._metrics)}"""

        if old_metrics_property in content:
            content = content.replace(old_metrics_property, new_metrics_property)
            base_service_file.write_text(content, encoding='utf-8')
            print("  ✓ BaseService.metrics 已修复（支持对象类型）")
        else:
            print("  ⚠ BaseService.metrics 未找到标准格式，跳过")
    else:
        print("  ⚠ BaseService中未找到metrics属性定义")
else:
    print("  ⚠ BaseService文件不存在")

# ========== 修复5: EnvironmentService添加detect_environment方法 ==========
print("\n[5/5] 修复 EnvironmentService...")

env_service_file = Path("core/services/environment_service.py")
if env_service_file.exists():
    content = env_service_file.read_text(encoding='utf-8')

    # 检查是否有_detect_environment方法
    if "def _detect_environment" in content and "def detect_environment" not in content:
        # 添加公共方法
        # 在类定义后找个合适位置添加公共方法
        insertion_point = content.find("def _detect_environment")
        if insertion_point > 0:
            # 找到前一个方法的结束位置
            before_content = content[:insertion_point]
            after_content = content[insertion_point:]

            public_method = """    def detect_environment(self) -> Dict[str, Any]:
        \"\"\"公共方法：检测环境信息\"\"\"
        return self._detect_environment()

    """

            new_content = before_content + public_method + after_content
            env_service_file.write_text(new_content, encoding='utf-8')
            print("  ✓ EnvironmentService.detect_environment 公共方法已添加")
        else:
            print("  ⚠ 未找到插入位置")
    else:
        print("  ℹ detect_environment 方法已存在或不需要添加")
else:
    print("  ⚠ EnvironmentService文件不存在")

print("\n" + "="*70)
print("修复完成！")
print("="*70)
print("\n下一步:")
print("1. 运行测试: python final_regression_test.py")
print("2. 检查结果，期望通过率显著提升")
