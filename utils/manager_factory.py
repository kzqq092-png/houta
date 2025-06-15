"""
统一管理器工厂模块

该模块提供了项目中所有管理器（配置管理器、日志管理器等）的统一创建和管理接口，
实现单例模式，避免重复实例化，提高性能和一致性。

使用方式:
    from utils.manager_factory import get_config_manager, get_log_manager
    
    # 获取配置管理器
    config_manager = get_config_manager()
    
    # 获取日志管理器
    log_manager = get_log_manager()
"""

import threading
import warnings
from typing import Optional, Dict, Any
from functools import lru_cache

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
                    from utils.config_manager import ConfigManager
                    self._instances[cache_key] = ConfigManager()
                except ImportError as e:
                    warnings.warn(f"无法导入ConfigManager: {e}")
                    # 创建简化版配置管理器
                    self._instances[cache_key] = self._create_simple_config_manager()
                except Exception as e:
                    warnings.warn(f"创建ConfigManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_config_manager()

            return self._instances[cache_key]

    def get_log_manager(self, config=None, force_new: bool = False) -> 'LogManager':
        """
        获取日志管理器实例（单例）

        Args:
            config: 可选的日志配置
            force_new: 是否强制创建新实例

        Returns:
            LogManager实例
        """
        cache_key = f'log_manager_{id(config) if config else "default"}'

        with self._lock:
            if force_new or cache_key not in self._instances:
                try:
                    from core.logger import LogManager
                    self._instances[cache_key] = LogManager(config)
                except ImportError:
                    try:
                        # 尝试使用基础日志管理器
                        from core.base_logger import BaseLogManager
                        self._instances[cache_key] = BaseLogManager()
                    except ImportError as e:
                        warnings.warn(f"无法导入LogManager: {e}")
                        # 创建简化版日志管理器
                        self._instances[cache_key] = self._create_simple_log_manager()
                except Exception as e:
                    warnings.warn(f"创建LogManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_log_manager()

            return self._instances[cache_key]

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
                    from utils.theme import ThemeManager
                    if config_manager is None:
                        config_manager = self.get_config_manager()
                    self._instances[cache_key] = ThemeManager(config_manager)
                except ImportError as e:
                    warnings.warn(f"无法导入ThemeManager: {e}")
                    self._instances[cache_key] = self._create_simple_theme_manager()
                except Exception as e:
                    warnings.warn(f"创建ThemeManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_theme_manager()

            return self._instances[cache_key]

    def get_data_manager(self, log_manager=None, force_new: bool = False) -> 'DataManager':
        """
        获取数据管理器实例（单例）

        Args:
            log_manager: 可选的日志管理器
            force_new: 是否强制创建新实例

        Returns:
            DataManager实例
        """
        cache_key = f'data_manager_{id(log_manager) if log_manager else "default"}'

        with self._lock:
            if force_new or cache_key not in self._instances:
                try:
                    from core.data_manager import DataManager
                    if log_manager is None:
                        log_manager = self.get_log_manager()
                    self._instances[cache_key] = DataManager(log_manager)
                except ImportError as e:
                    warnings.warn(f"无法导入DataManager: {e}")
                    self._instances[cache_key] = self._create_simple_data_manager()
                except Exception as e:
                    warnings.warn(f"创建DataManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_data_manager()

            return self._instances[cache_key]

    def get_industry_manager(self, log_manager=None, force_new: bool = False) -> 'IndustryManager':
        """
        获取行业管理器实例（单例）

        Args:
            log_manager: 可选的日志管理器
            force_new: 是否强制创建新实例

        Returns:
            IndustryManager实例
        """
        cache_key = f'industry_manager_{id(log_manager) if log_manager else "default"}'

        with self._lock:
            if force_new or cache_key not in self._instances:
                try:
                    from core.industry_manager import IndustryManager
                    if log_manager is None:
                        log_manager = self.get_log_manager()
                    self._instances[cache_key] = IndustryManager(log_manager=log_manager)
                except ImportError as e:
                    warnings.warn(f"无法导入IndustryManager: {e}")
                    self._instances[cache_key] = self._create_simple_industry_manager()
                except Exception as e:
                    warnings.warn(f"创建IndustryManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_industry_manager()

            return self._instances[cache_key]

    def clear_cache(self, manager_type: Optional[str] = None):
        """
        清除管理器缓存

        Args:
            manager_type: 要清除的管理器类型，None表示清除所有
        """
        with self._lock:
            if manager_type:
                # 清除特定类型的管理器
                keys_to_remove = [key for key in self._instances.keys() if key.startswith(manager_type)]
                for key in keys_to_remove:
                    del self._instances[key]
            else:
                # 清除所有管理器
                self._instances.clear()

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

        return SimpleConfigManager()

    def _create_simple_log_manager(self):
        """创建简化版日志管理器"""
        class SimpleLogManager:
            def __init__(self):
                self.level = 'INFO'

            def info(self, message: str):
                print(f"[INFO] {message}")

            def warning(self, message: str):
                print(f"[WARNING] {message}")

            def error(self, message: str):
                print(f"[ERROR] {message}")

            def debug(self, message: str):
                print(f"[DEBUG] {message}")

            def log(self, message: str, level: str = 'INFO'):
                print(f"[{level}] {message}")

        return SimpleLogManager()

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
        """创建简化版数据管理器"""
        class SimpleDataManager:
            def __init__(self):
                self.data = {}

            def get_data(self, key: str):
                return self.data.get(key)

            def set_data(self, key: str, value):
                self.data[key] = value

        return SimpleDataManager()

    def _create_simple_industry_manager(self):
        """创建简化版行业管理器"""
        class SimpleIndustryManager:
            def __init__(self):
                self.industries = {}

            def get_industry(self, code: str):
                return self.industries.get(code, '未知行业')

            def update_industry_data(self):
                pass

        return SimpleIndustryManager()


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


def get_log_manager(config=None, force_new: bool = False) -> 'LogManager':
    """
    获取日志管理器实例

    Args:
        config: 可选的日志配置
        force_new: 是否强制创建新实例

    Returns:
        LogManager实例
    """
    return get_manager_factory().get_log_manager(config, force_new)


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


def get_data_manager(log_manager=None, force_new: bool = False) -> 'DataManager':
    """
    获取数据管理器实例

    Args:
        log_manager: 可选的日志管理器
        force_new: 是否强制创建新实例

    Returns:
        DataManager实例
    """
    return get_manager_factory().get_data_manager(log_manager, force_new)


def get_industry_manager(log_manager=None, force_new: bool = False) -> 'IndustryManager':
    """
    获取行业管理器实例

    Args:
        log_manager: 可选的日志管理器
        force_new: 是否强制创建新实例

    Returns:
        IndustryManager实例
    """
    return get_manager_factory().get_industry_manager(log_manager, force_new)


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
        log_manager = get_log_manager()
        status['log_manager'] = log_manager is not None
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
        status_text = "✓ 可用" if available else "✗ 不可用"
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
            return factory.get_log_manager(**kwargs)
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
