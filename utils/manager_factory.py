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
from core.industry_manager import IndustryManager
from core.data_manager import DataManager
from core.logger import LogManager
from utils.theme import ThemeManager
from utils.config_manager import ConfigManager


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
                    self._instances[cache_key] = self._create_simple_config_manager(
                    )
                except Exception as e:
                    warnings.warn(f"创建ConfigManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_config_manager(
                    )

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
                        self._instances[cache_key] = self._create_simple_log_manager(
                        )
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
                    self._instances[cache_key] = self._create_simple_theme_manager(
                    )
                except Exception as e:
                    warnings.warn(f"创建ThemeManager失败: {e}")
                    self._instances[cache_key] = self._create_simple_theme_manager(
                    )

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
        # 统一缓存键策略 - 使用单一实例，避免因log_manager不同而创建多个实例
        cache_key = 'industry_manager_singleton'

        # 获取日志管理器用于记录操作日志
        log_manager = log_manager or self.get_log_manager()

        with self._lock:
            # 记录获取请求
            try:
                # 检查PyQt5环境
                pyqt5_status = self._check_pyqt5_environment()
                log_manager.info(
                    f"开始获取行业管理器 - 缓存键: {cache_key}, 强制新建: {force_new}, PyQt5状态: {pyqt5_status}")
            except Exception:
                # 如果日志记录失败，不影响主要逻辑
                log_manager.error("获取行业管理器失败")

            if force_new or cache_key not in self._instances:
                try:
                    # 记录开始创建实例
                    log_manager.info(f"开始创建行业管理器实例 - 缓存键: {cache_key}")

                    from core.industry_manager import IndustryManager

                    # 确保使用统一的日志管理器
                    if log_manager is None:
                        log_manager = self.get_log_manager()

                    # 创建实例 - 添加额外的错误处理
                    try:
                        self._instances[cache_key] = IndustryManager(
                            log_manager=log_manager)

                        # 记录创建成功
                        log_manager.info(
                            f"行业管理器创建成功 - 类型: {type(self._instances[cache_key]).__name__}")

                    except Exception as creation_error:
                        # 记录创建过程中的具体错误
                        log_manager.error(
                            f"创建行业管理器失败: {creation_error} (类型: {type(creation_error).__name__})")

                        # 重新抛出原始错误
                        raise creation_error

                except ImportError as e:
                    # 记录导入错误
                    log_manager.error(f"导入行业管理器失败: {e}")

                    # 创建简化版管理器
                    self._instances[cache_key] = self._create_simple_industry_manager(
                    )

                    # 记录回退操作
                    log_manager.warning(f"使用简化版行业管理器")

                except Exception as e:
                    # 记录创建错误
                    log_manager.error(
                        f"创建行业管理器失败: {e} (类型: {type(e).__name__})")

                    # 创建简化版管理器
                    self._instances[cache_key] = self._create_simple_industry_manager(
                    )

                    # 记录回退操作
                    log_manager.warning(f"使用简化版行业管理器，原因: {e}")
            else:
                # 记录缓存命中
                log_manager.debug(f"缓存命中 - 缓存键: {cache_key}")

            # 记录获取完成
            log_manager.info(
                f"行业管理器获取完成 - 类型: {type(self._instances[cache_key]).__name__}")

            return self._instances[cache_key]

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
            # 获取日志管理器
            try:
                log_manager = self.get_log_manager()
                from utils.log_util import log_structured

                # 记录清除操作开始
                log_structured(log_manager, "clear_manager_cache",
                               level="info", status="start",
                               manager_type=manager_type,
                               current_cache_size=len(self._instances))
            except Exception:
                log_manager.error("记录清除操作开始失败")

            if manager_type:
                # 清除特定类型的管理器
                keys_to_remove = [
                    key for key in self._instances.keys() if key.startswith(manager_type)]
                removed_count = 0

                for key in keys_to_remove:
                    try:
                        # 记录即将删除的实例
                        if log_manager:
                            log_structured(log_manager, "remove_manager_instance",
                                           level="debug", status="start",
                                           cache_key=key,
                                           instance_type=type(self._instances[key]).__name__)

                        del self._instances[key]
                        removed_count += 1

                        # 记录删除成功
                        if log_manager:
                            log_structured(log_manager, "remove_manager_instance",
                                           level="debug", status="success",
                                           cache_key=key)
                    except Exception as e:
                        # 记录删除失败
                        if log_manager:
                            log_structured(log_manager, "remove_manager_instance",
                                           level="error", status="fail",
                                           cache_key=key, error=str(e))

                # 记录清除结果
                if log_manager:
                    log_structured(log_manager, "clear_manager_cache",
                                   level="info", status="success",
                                   manager_type=manager_type,
                                   removed_count=removed_count,
                                   remaining_cache_size=len(self._instances))
            else:
                # 清除所有管理器
                original_size = len(self._instances)

                # 记录所有即将清除的实例
                if log_manager:
                    for key, instance in self._instances.items():
                        log_structured(log_manager, "remove_manager_instance",
                                       level="debug", status="start",
                                       cache_key=key,
                                       instance_type=type(instance).__name__)

                self._instances.clear()

                # 记录清除结果
                if log_manager:
                    log_structured(log_manager, "clear_manager_cache",
                                   level="info", status="success",
                                   manager_type="all",
                                   removed_count=original_size,
                                   remaining_cache_size=0)

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
        try:
            # 获取日志管理器用于记录
            log_manager = self.get_log_manager()

            log_manager.info("开始创建简化版行业管理器")

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
                    self.log_manager = log_manager

                    # 记录简化版管理器初始化
                    self.log_manager.info(
                        f"简化版行业管理器初始化成功 - 行业数量: {len(self.industries)}")

                def get_industry(self, code: str):
                    """获取行业信息"""
                    try:
                        result = self.industries.get(code, '未知行业')
                        self.log_manager.debug(
                            f"获取行业信息 - 代码: {code}, 结果: {result}")
                        return result
                    except Exception as e:
                        self.log_manager.error(
                            f"获取行业信息失败 - 代码: {code}, 错误: {e}")
                        return '未知行业'

                def update_industry_data(self):
                    """更新行业数据（简化版不执行实际更新）"""
                    self.log_manager.info("简化版管理器跳过更新行业数据")
                    return True

                def get_industry_list(self, source: str = "default") -> list:
                    """获取行业列表"""
                    try:
                        result = [{"code": k, "name": v, "source": source}
                                  for k, v in self.industries.items()]
                        self.log_manager.debug(f"获取行业列表成功 - 数量: {len(result)}")
                        return result
                    except Exception as e:
                        self.log_manager.error(f"获取行业列表失败: {e}")
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
                        self.log_manager.debug(
                            f"获取行业股票成功 - 行业: {industry_code}, 数量: {len(example_stocks)}")
                        return example_stocks
                    except Exception as e:
                        self.log_manager.error(
                            f"获取行业股票失败 - 行业: {industry_code}, 错误: {e}")
                        return []

            simple_manager = SimpleIndustryManager()

            log_manager.info(f"简化版行业管理器创建成功 - 类型: SimpleIndustryManager")

            return simple_manager

        except Exception as e:
            # 最后的保险措施
            try:
                log_manager = self.get_log_manager()
                log_manager.error(f"创建简化版行业管理器失败: {e}")
            except Exception:
                print(f"创建简化版行业管理器失败: {e}")

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
