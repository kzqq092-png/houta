from loguru import logger
"""
统一管理器工厂模块

该模块提供了项目中所有管理器（配置管理器、日志管理器等）的统一创建和管理接口，
实现单例模式，避免重复实例化，提高性能和一致性。

使用方式:
    from utils.manager_factory import get_config_manager
    
    # 获取配置管理器
    config_manager = get_config_manager()
    
    # 日志系统已迁移到Loguru
    # 直接使用: from loguru import logger
"""

import threading
import warnings
import time
from typing import Optional, Dict, Any
from functools import lru_cache
from core.industry_manager import IndustryManager
from core.services.unified_data_manager import UnifiedDataManager, get_unified_data_manager
from utils.theme import ThemeManager
from utils.config_manager import ConfigManager
from core.performance.unified_monitor import UnifiedPerformanceMonitor

# 全局锁，确保线程安全
_factory_lock = threading.Lock()

# 管理器实例缓存
_manager_cache: Dict[str, Any] = {}

class ManagerFactory:
    """管理器工厂类，负责统一创建和管理所有管理器实例"""

    def __init__(self):
        self._instances = {}
        self._lock = threading.Lock()

    def get_config_manager(self, force_new: bool = False) -> 'ConfigManager':
        """
        获取配置管理器实例（单例）

        Args:
            force_new: 是否强制创建新实例

        Returns:
            ConfigManager实例
        """
        cache_key = 'config_manager'

        with self._lock:
            if force_new or cache_key not in self._instances:
                try:
                    self._instances[cache_key] = ConfigManager()
                except ImportError as e:
                    warnings.warn(f"无法导入ConfigManager: {e}")
                    # 创建简化版配置管理器
                    self._instances[cache_key] = self._create_simple_config_manager(
                    )
                except Exception as e:
                    warnings.warn(f"创建ConfigManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_config_manager(
                    )

            return self._instances[cache_key]

    # get_log_manager 已删除 - 使用纯Loguru架构
    # 直接使用: from loguru import logger

    def get_theme_manager(self, config_manager=None, force_new: bool = False) -> 'ThemeManager':
        """
        获取主题管理器实例（单例）

        Args:
            config_manager: 可选的配置管理器
            force_new: 是否强制创建新实例

        Returns:
            ThemeManager实例
        """
        cache_key = f'theme_manager_{id(config_manager) if config_manager else "default"}'

        with self._lock:
            if force_new or cache_key not in self._instances:
                try:
                    if config_manager is None:
                        config_manager = self.get_config_manager()
                    self._instances[cache_key] = ThemeManager(config_manager)
                except ImportError as e:
                    warnings.warn(f"无法导入ThemeManager: {e}")
                    self._instances[cache_key] = self._create_simple_theme_manager(
                    )
                except Exception as e:
                    warnings.warn(f"创建ThemeManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_theme_manager(
                    )

            return self._instances[cache_key]

    def get_data_manager(self, force_new: bool = False) -> 'UnifiedDataManager':
        """
        获取数据管理器实例（单例）

        Args:
            force_new: 是否强制创建新实例

        Returns:
            UnifiedDataManager实例
        """
        cache_key = 'data_manager_singleton'

        with self._lock:
            if force_new or cache_key not in self._instances:
                try:
                    self._instances[cache_key] = get_unified_data_manager()
                except ImportError as e:
                    warnings.warn(f"无法导入UnifiedDataManager: {e}")
                    self._instances[cache_key] = self._create_simple_data_manager()
                except Exception as e:
                    warnings.warn(f"创建UnifiedDataManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_data_manager()

            return self._instances[cache_key]

    def get_industry_manager(self, force_new: bool = False) -> 'IndustryManager':
        """
        获取行业管理器实例（单例）

        Args:
            force_new: 是否强制创建新实例

        Returns:
            IndustryManager实例
        """
        # 统一缓存键策略 - 使用单一实例
        cache_key = 'industry_manager_singleton'

        with self._lock:
            # 记录获取请求
            try:
                # 检查PyQt5环境
                pyqt5_status = self._check_pyqt5_environment()
                logger.info(
                    f"开始获取行业管理器 - 缓存键: {cache_key}, 强制新建: {force_new}, PyQt5状态: {pyqt5_status}")
            except Exception:
                # 如果日志记录失败，不影响主要逻辑
                logger.error("获取行业管理器失败")

            if force_new or cache_key not in self._instances:
                try:
                    # 记录开始创建实例
                    logger.info(f"开始创建行业管理器实例 - 缓存键: {cache_key}")

                    # 创建实例 - 添加额外的错误处理
                    try:
                        self._instances[cache_key] = IndustryManager()

                        # 记录创建成功
                        logger.info(
                            f"行业管理器创建成功 - 类型: {type(self._instances[cache_key]).__name__}")

                    except Exception as creation_error:
                        # 记录创建过程中的具体错误
                        logger.error(
                            f"创建行业管理器失败: {creation_error} (类型: {type(creation_error).__name__})")

                        # 重新抛出原始错误
                        raise creation_error

                except ImportError as e:
                    # 记录导入错误
                    logger.error(f"导入行业管理器失败: {e}")

                    # 创建简化版管理器
                    self._instances[cache_key] = self._create_simple_industry_manager(
                    )

                    # 记录回退操作
                    logger.warning(f"使用简化版行业管理器")

                except Exception as e:
                    # 记录创建错误
                    logger.error(
                        f"创建行业管理器失败: {e} (类型: {type(e).__name__})")

                    # 创建简化版管理器
                    self._instances[cache_key] = self._create_simple_industry_manager(
                    )

                    # 记录回退操作
                    logger.warning(f"使用简化版行业管理器，原因: {e}")
            else:
                # 记录缓存命中
                logger.debug(f"缓存命中 - 缓存键: {cache_key}")

            # 记录获取完成
            logger.info(
                f"行业管理器获取完成 - 类型: {type(self._instances[cache_key]).__name__}")

            return self._instances[cache_key]

    def get_performance_monitor(self, force_new: bool = False) -> 'UnifiedPerformanceMonitor':
        """
        获取统一性能监控器实例（单例）

        Args:
            force_new: 是否强制创建新实例

        Returns:
            UnifiedPerformanceMonitor实例
        """
        cache_key = 'performance_monitor_singleton'

        with self._lock:
            if force_new or cache_key not in self._instances:
                try:
                    self._instances[cache_key] = UnifiedPerformanceMonitor()
                    logger.info("性能监控器实例创建成功")
                except ImportError as e:
                    logger.warning(f"无法导入UnifiedPerformanceMonitor: {e}")
                    self._instances[cache_key] = self._create_simple_performance_monitor()
                except Exception as e:
                    logger.error(f"创建UnifiedPerformanceMonitor失败: {e}")
                    self._instances[cache_key] = self._create_simple_performance_monitor()

            return self._instances[cache_key]

    def _create_simple_performance_monitor(self):
        """创建简化版性能监控器"""
        try:
            logger.info("创建简化版性能监控器")

            class SimplePerformanceMonitor:
                """简化版性能监控器，提供基础功能"""
                def __init__(self):
                    self.stats = {}
                    self.metrics = {}
                    self.start_time = time.time()

                def record_metric(self, name, value, category=None, metric_type=None, description=""):
                    """记录指标"""
                    if name not in self.metrics:
                        self.metrics[name] = []
                    self.metrics[name].append({
                        'value': value,
                        'timestamp': time.time(),
                        'category': category,
                        'description': description
                    })

                def get_metric_history(self, name):
                    """获取指标历史"""
                    return self.metrics.get(name, [])

                def get_system_metrics(self):
                    """获取系统指标"""
                    return {
                        'cpu_usage': 0.0,
                        'memory_usage': 0.0,
                        'disk_usage': 0.0,
                        'network_latency': 0.0
                    }

                def start_monitoring(self):
                    """开始监控"""
                    return True

                def stop_monitoring(self):
                    """停止监控"""
                    return True

                def reset_stats(self):
                    """重置统计"""
                    self.stats = {}
                    self.metrics = {}

                def get_uptime(self):
                    """获取运行时间"""
                    return time.time() - self.start_time

            return SimplePerformanceMonitor()

        except Exception as e:
            logger.error(f"创建简化版性能监控器失败: {e}")
            return None

    def _check_pyqt5_environment(self) -> dict:
        """检查PyQt5环境状态"""
        try:
            status = {
                "pyqt5_importable": False,
                "qapplication_available": False,
                "qapplication_instance": False
            }

            try:
                from PyQt5.QtWidgets import QApplication
                from PyQt5.QtCore import QObject
                status["pyqt5_importable"] = True

                try:
                    app = QApplication.instance()
                    status["qapplication_available"] = True
                    status["qapplication_instance"] = app is not None
                except Exception:
                    pass

            except ImportError:
                pass

            return status

        except Exception:
            return {"error": "failed_to_check"}

    def clear_cache(self, manager_type: Optional[str] = None):
        """
        清除管理器缓存

        Args:
            manager_type: 要清除的管理器类型，None表示清除所有
        """
        with self._lock:
            # 记录清除操作开始
            try:
                logger.info(f"开始清除管理器缓存 - 类型: {manager_type}, 当前缓存大小: {len(self._instances)}")
            except Exception:
                logger.error("记录清除操作开始失败")

            if manager_type:
                # 清除特定类型的管理器
                keys_to_remove = [
                    key for key in self._instances.keys() if key.startswith(manager_type)]
                removed_count = 0

                for key in keys_to_remove:
                    try:
                        logger.debug(f"删除管理器实例: {key} ({type(self._instances[key]).__name__})")
                        del self._instances[key]
                        removed_count += 1
                    except Exception as e:
                        logger.error(f"删除管理器实例失败: {key} - {e}")

                logger.info(f"清除特定类型管理器完成 - 类型: {manager_type}, 删除数量: {removed_count}, 剩余缓存: {len(self._instances)}")
            else:
                # 清除所有管理器
                original_size = len(self._instances)
                logger.debug(f"清除所有管理器实例，共 {original_size} 个")
                self._instances.clear()
                logger.info(f"清除所有管理器完成 - 删除数量: {original_size}")

    def get_manager_info(self) -> Dict[str, Any]:
        """
        获取管理器工厂状态信息

        Returns:
            包含管理器信息的字典
        """
        with self._lock:
            return {
                'cached_managers': list(self._instances.keys()),
                'cache_size': len(self._instances),
                'thread_id': threading.current_thread().ident
            }

    def _create_simple_config_manager(self):
        """创建简化版配置管理器"""
        class SimpleConfigManager:
            def __init__(self):
                self._config = {
                    'theme': {'theme_name': 'light'},
                    'logging': {'level': 'INFO', 'save_to_file': True},
                    'trading': {'initial_capital': 100000},
                    'data': {'auto_save': True},
                    'ui': {'language': 'zh_CN'}
                }

            def get(self, key: str, default=None):
                keys = key.split('.')
                value = self._config
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                return value

            def set(self, key: str, value):
                keys = key.split('.')
                config = self._config
                for k in keys[:-1]:
                    if k not in config:
                        config[k] = {}
                    config = config[k]
                config[keys[-1]] = value

            def get_all(self):
                return self._config.copy()

            @property
            def theme(self):
                return self.get('theme', {})

            @property
            def logging(self):
                return self.get('logging', {})

            @property
            def trading(self):
                return self.get('trading', {})

            @property
            def data(self):
                return self.get('data', {})

            def get_plugin_config(self, plugin_name: str, default=None):
                """获取插件配置"""
                if default is None:
                    default = {}
                plugin_key = f"plugins.{plugin_name}"
                return self.get(plugin_key, default)

            def save_plugin_config(self, plugin_name: str, config):
                """保存插件配置"""
                plugin_key = f"plugins.{plugin_name}"
                self.set(plugin_key, config)

        return SimpleConfigManager()

    # _create_simple_log_manager 已删除 - 使用纯Loguru架构

    def _create_simple_theme_manager(self):
        """创建简化版主题管理器"""
        class SimpleThemeManager:
            def __init__(self):
                self.current_theme = 'light'

            def set_theme(self, theme_name: str):
                self.current_theme = theme_name

            def get_theme(self):
                return self.current_theme

        return SimpleThemeManager()

    def _create_simple_data_manager(self):
        """创建数据管理器 - 重定向到UnifiedDataManager"""
        return get_unified_data_manager()

    def _create_simple_industry_manager(self):
        """创建简化版行业管理器"""
        try:
            logger.info("开始创建简化版行业管理器")

            class SimpleIndustryManager:
                def __init__(self):
                    self.industries = {
                        # 提供基本的行业数据
                        "BK0001": "银行",
                        "BK0002": "保险",
                        "BK0003": "证券",
                        "BK0004": "房地产",
                        "BK0005": "互联网",
                        "BK0006": "软件开发",
                        "BK0007": "电子信息",
                        "BK0008": "生物医药",
                        "BK0009": "新能源",
                        "BK0010": "汽车制造"
                    }

                    # 记录简化版管理器初始化
                    logger.info(
                        f"简化版行业管理器初始化成功 - 行业数量: {len(self.industries)}")

                def get_industry(self, code: str):
                    """获取行业信息"""
                    try:
                        result = self.industries.get(code, '未知行业')
                        logger.debug(
                            f"获取行业信息 - 代码: {code}, 结果: {result}")
                        return result
                    except Exception as e:
                        logger.error(
                            f"获取行业信息失败 - 代码: {code}, 错误: {e}")
                        return '未知行业'

                def update_industry_data(self):
                    """更新行业数据（简化版不执行实际更新）"""
                    logger.info("简化版管理器跳过更新行业数据")
                    return True

                def get_industry_list(self, source: str = "default") -> list:
                    """获取行业列表"""
                    try:
                        result = [{"code": k, "name": v, "source": source}
                                  for k, v in self.industries.items()]
                        logger.debug(f"获取行业列表成功 - 数量: {len(result)}")
                        return result
                    except Exception as e:
                        logger.error(f"获取行业列表失败: {e}")
                        return []

                def get_industry_stocks(self, industry_code: str, source: str = "default") -> list:
                    """获取行业股票（简化版返回示例数据）"""
                    try:
                        # 返回一些示例股票数据
                        example_stocks = [
                            {"code": "000001", "name": "平安银行",
                                "industry": industry_code},
                            {"code": "600036", "name": "招商银行",
                                "industry": industry_code},
                            {"code": "000002", "name": "万科A",
                                "industry": industry_code}
                        ]
                        logger.debug(
                            f"获取行业股票成功 - 行业: {industry_code}, 数量: {len(example_stocks)}")
                        return example_stocks
                    except Exception as e:
                        logger.error(
                            f"获取行业股票失败 - 行业: {industry_code}, 错误: {e}")
                        return []

            simple_manager = SimpleIndustryManager()

            logger.info(f"简化版行业管理器创建成功 - 类型: SimpleIndustryManager")

            return simple_manager

        except Exception as e:
            # 最后的保险措施
            try:
                logger.error(f"创建简化版行业管理器失败: {e}")
            except Exception:
                logger.info(f"创建简化版行业管理器失败: {e}")

            # 返回最基本的管理器
            class MinimalIndustryManager:
                def __init__(self):
                    self.industries = {}

                def get_industry(self, code: str):
                    return '未知行业'

                def update_industry_data(self):
                    return False

                def get_industry_list(self, source: str = "default"):
                    return []

                def get_industry_stocks(self, industry_code: str, source: str = "default"):
                    return []

            return MinimalIndustryManager()

# 全局管理器工厂实例
_factory_instance: Optional[ManagerFactory] = None

def get_manager_factory() -> ManagerFactory:
    """获取管理器工厂实例（单例）"""
    global _factory_instance

    if _factory_instance is None:
        with _factory_lock:
            if _factory_instance is None:
                _factory_instance = ManagerFactory()

    return _factory_instance

# =============================================================================
# 便捷函数
# =============================================================================

@lru_cache(maxsize=1)
def get_config_manager(force_new: bool = False) -> 'ConfigManager':
    """
    获取配置管理器实例

    Args:
        force_new: 是否强制创建新实例

    Returns:
        ConfigManager实例
    """
    return get_manager_factory().get_config_manager(force_new)

# get_log_manager 已删除 - 使用纯Loguru架构
# 直接使用: from loguru import logger

def get_theme_manager(config_manager=None, force_new: bool = False) -> 'ThemeManager':
    """
    获取主题管理器实例

    Args:
        config_manager: 可选的配置管理器
        force_new: 是否强制创建新实例

    Returns:
        ThemeManager实例
    """
    return get_manager_factory().get_theme_manager(config_manager, force_new)

def get_data_manager(force_new: bool = False) -> 'UnifiedDataManager':
    """
    获取数据管理器实例

    Args:
        # log_manager: 已迁移到Loguru日志系统
        force_new: 是否强制创建新实例

    Returns:
        UnifiedDataManager实例
    """
    return get_manager_factory().get_data_manager(force_new)

def get_industry_manager(force_new: bool = False) -> 'IndustryManager':
    """
    获取行业管理器实例

    Args:
        # log_manager: 已迁移到Loguru日志系统
        force_new: 是否强制创建新实例

    Returns:
        IndustryManager实例
    """
    return get_manager_factory().get_industry_manager(force_new)

@lru_cache(maxsize=1)
def get_performance_monitor(force_new: bool = False) -> 'UnifiedPerformanceMonitor':
    """
    获取统一性能监控器实例

    Args:
        force_new: 是否强制创建新实例

    Returns:
        UnifiedPerformanceMonitor实例
    """
    return get_manager_factory().get_performance_monitor(force_new)

def clear_manager_cache(manager_type: Optional[str] = None):
    """
    清除管理器缓存

    Args:
        manager_type: 要清除的管理器类型，None表示清除所有
    """
    get_manager_factory().clear_cache(manager_type)

def get_factory_info() -> Dict[str, Any]:
    """
    获取管理器工厂状态信息

    Returns:
        包含工厂信息的字典
    """
    return get_manager_factory().get_manager_info()

# =============================================================================
# 兼容性函数
# =============================================================================

def ensure_managers_available() -> Dict[str, bool]:
    """
    确保所有管理器可用

    Returns:
        各管理器的可用状态
    """
    status = {}

    try:
        config_manager = get_config_manager()
        status['config_manager'] = config_manager is not None
    except Exception:
        status['config_manager'] = False

    try:
        # 日志系统已迁移到Loguru
        status['log_manager'] = True  # Loguru always available
    except Exception:
        status['log_manager'] = False

    try:
        theme_manager = get_theme_manager()
        status['theme_manager'] = theme_manager is not None
    except Exception:
        status['theme_manager'] = False

    return status

def get_manager_summary() -> str:
    """
    获取管理器状态摘要

    Returns:
        状态摘要字符串
    """
    factory_info = get_factory_info()
    manager_status = ensure_managers_available()

    summary = "=== 管理器工厂状态摘要 ===\n"
    summary += f"缓存的管理器数量: {factory_info['cache_size']}\n"
    summary += f"线程ID: {factory_info['thread_id']}\n"
    summary += "\n=== 管理器可用性 ===\n"

    for manager_type, available in manager_status.items():
        status_text = " 可用" if available else " 不可用"
        summary += f"{manager_type}: {status_text}\n"

    summary += f"\n=== 缓存的管理器 ===\n"
    for manager_name in factory_info['cached_managers']:
        summary += f"- {manager_name}\n"

    return summary

def safe_get_manager(manager_type: str, **kwargs):
    """
    安全获取管理器，带错误处理

    Args:
        manager_type: 管理器类型
        **kwargs: 传递给管理器的参数

    Returns:
        管理器实例或None
    """
    try:
        factory = get_manager_factory()

        if manager_type == 'config':
            return factory.get_config_manager(**kwargs)
        elif manager_type == 'log':
            # log_manager已删除，返回None - 使用纯Loguru架构
            return None
        elif manager_type == 'theme':
            return factory.get_theme_manager(**kwargs)
        elif manager_type == 'data':
            return factory.get_data_manager(**kwargs)
        elif manager_type == 'industry':
            return factory.get_industry_manager(**kwargs)
        else:
            warnings.warn(f"未知的管理器类型: {manager_type}")
            return None

    except Exception as e:
        warnings.warn(f"获取管理器失败 ({manager_type}): {e}")
        return None
