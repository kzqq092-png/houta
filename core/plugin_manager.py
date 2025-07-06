"""
HIkyuu-UI 增强插件管理器

提供插件的加载、管理、生命周期控制和生态系统集成功能。
"""

import logging
import os
import sys
import json
import importlib
import importlib.util
from typing import Dict, List, Any, Optional, Type, Callable
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """插件状态"""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


class PluginType(Enum):
    """插件类型"""
    INDICATOR = "indicator"
    STRATEGY = "strategy"
    DATA_SOURCE = "data_source"
    ANALYSIS = "analysis"
    UI_COMPONENT = "ui_component"
    EXPORT = "export"
    NOTIFICATION = "notification"
    CHART_TOOL = "chart_tool"


class PluginCategory(Enum):
    """插件分类"""
    CORE = "core"
    COMMUNITY = "community"
    COMMERCIAL = "commercial"
    EXPERIMENTAL = "experimental"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    path: str
    status: PluginStatus
    config: Dict[str, Any]
    dependencies: List[str]
    plugin_type: Optional[PluginType] = None
    category: Optional[PluginCategory] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['status'] = self.status.value
        if self.plugin_type:
            result['plugin_type'] = self.plugin_type.value
        if self.category:
            result['category'] = self.category.value
        return result


class PluginManager(QObject):
    """增强插件管理器"""

    # 信号定义
    plugin_loaded = pyqtSignal(str)  # 插件加载
    plugin_enabled = pyqtSignal(str)  # 插件启用
    plugin_disabled = pyqtSignal(str)  # 插件禁用
    plugin_error = pyqtSignal(str, str)  # 插件错误

    def __init__(self,
                 plugin_dir: str = "plugins",
                 main_window=None,
                 data_manager=None,
                 config_manager=None,
                 log_manager=None):
        """
        初始化增强插件管理器

        Args:
            plugin_dir: 插件目录路径
            main_window: 主窗口
            data_manager: 数据管理器
            config_manager: 配置管理器
            log_manager: 日志管理器
        """
        super().__init__()

        self.plugin_dir = Path(plugin_dir)
        self.loaded_plugins = {}
        self.plugin_instances = {}
        self.plugin_metadata = {}
        self.plugin_hooks: Dict[str, List[Callable]] = {}
        self.enhanced_plugins: Dict[str, PluginInfo] = {}

        # 插件生态系统组件
        self.main_window = main_window
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.log_manager = log_manager or logger

        # 按类型分类插件
        self.plugins_by_type: Dict[PluginType, List[str]] = {
            plugin_type: [] for plugin_type in PluginType
        }

    def initialize(self) -> None:
        """初始化插件管理器"""
        try:
            # 确保插件目录存在
            if not self.plugin_dir.exists():
                self.plugin_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建插件目录: {self.plugin_dir}")

            # 加载所有插件
            self.load_all_plugins()

            logger.info("插件管理器初始化完成")

        except Exception as e:
            logger.error(f"插件管理器初始化失败: {e}")

    def load_all_plugins(self) -> None:
        """加载所有插件"""
        try:
            if not self.plugin_dir.exists():
                logger.warning(f"插件目录不存在: {self.plugin_dir}")
                return

            # 扫描插件目录
            for plugin_path in self.plugin_dir.glob("*.py"):
                if plugin_path.name.startswith("__"):
                    continue

                plugin_name = plugin_path.stem
                self.load_plugin(plugin_name, plugin_path)

            logger.info(f"已加载 {len(self.loaded_plugins)} 个插件")

        except Exception as e:
            logger.error(f"加载插件失败: {e}")

    def load_plugin(self, plugin_name: str, plugin_path: Path) -> bool:
        """
        加载指定插件

        Args:
            plugin_name: 插件名称
            plugin_path: 插件文件路径

        Returns:
            bool: 是否加载成功
        """
        try:
            # 检查插件是否已加载
            if plugin_name in self.loaded_plugins:
                logger.warning(f"插件已加载: {plugin_name}")
                return True

            # 加载插件模块
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None or spec.loader is None:
                logger.error(f"无法创建插件规范: {plugin_name}")
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找插件类
            plugin_class = self._find_plugin_class(module)
            if plugin_class is None:
                logger.error(f"未找到插件类: {plugin_name}")
                return False

            # 获取插件元数据
            metadata = self._get_plugin_metadata(plugin_class)

            # 创建插件实例
            plugin_instance = plugin_class()

            # 保存插件信息
            self.loaded_plugins[plugin_name] = module
            self.plugin_instances[plugin_name] = plugin_instance
            self.plugin_metadata[plugin_name] = metadata

            # 初始化插件
            if hasattr(plugin_instance, 'initialize'):
                plugin_instance.initialize()

            logger.info(f"插件加载成功: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"加载插件失败 {plugin_name}: {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载指定插件

        Args:
            plugin_name: 插件名称

        Returns:
            bool: 是否卸载成功
        """
        try:
            if plugin_name not in self.loaded_plugins:
                logger.warning(f"插件未加载: {plugin_name}")
                return True

            # 清理插件实例
            if plugin_name in self.plugin_instances:
                plugin_instance = self.plugin_instances[plugin_name]
                if hasattr(plugin_instance, 'cleanup'):
                    plugin_instance.cleanup()

            # 移除插件信息
            self.loaded_plugins.pop(plugin_name, None)
            self.plugin_instances.pop(plugin_name, None)
            self.plugin_metadata.pop(plugin_name, None)

            logger.info(f"插件卸载成功: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"卸载插件失败 {plugin_name}: {e}")
            return False

    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """
        获取插件实例

        Args:
            plugin_name: 插件名称

        Returns:
            插件实例或None
        """
        return self.plugin_instances.get(plugin_name)

    def get_all_plugins(self) -> Dict[str, Any]:
        """获取所有插件实例"""
        return self.plugin_instances.copy()

    def get_plugin_metadata(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        获取插件元数据

        Args:
            plugin_name: 插件名称

        Returns:
            插件元数据或None
        """
        return self.plugin_metadata.get(plugin_name)

    def get_all_plugin_metadata(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件元数据"""
        return self.plugin_metadata.copy()

    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """
        检查插件是否已加载

        Args:
            plugin_name: 插件名称

        Returns:
            bool: 是否已加载
        """
        return plugin_name in self.loaded_plugins

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        重新加载插件

        Args:
            plugin_name: 插件名称

        Returns:
            bool: 是否重新加载成功
        """
        try:
            # 先卸载插件
            if not self.unload_plugin(plugin_name):
                return False

            # 重新加载插件
            plugin_path = self.plugin_dir / f"{plugin_name}.py"
            return self.load_plugin(plugin_name, plugin_path)

        except Exception as e:
            logger.error(f"重新加载插件失败 {plugin_name}: {e}")
            return False

    def _find_plugin_class(self, module) -> Optional[Type]:
        """
        在模块中查找插件类

        Args:
            module: 插件模块

        Returns:
            插件类或None
        """
        try:
            # 查找继承自BasePlugin的类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    hasattr(attr, '__bases__') and
                        any(base.__name__ == 'BasePlugin' for base in attr.__bases__)):
                    return attr

            # 如果没有找到BasePlugin子类，查找包含特定方法的类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    hasattr(attr, 'initialize') and
                        hasattr(attr, 'get_name')):
                    return attr

            return None

        except Exception as e:
            logger.error(f"查找插件类失败: {e}")
            return None

    def _get_plugin_metadata(self, plugin_class: Type) -> Dict[str, Any]:
        """
        获取插件元数据

        Args:
            plugin_class: 插件类

        Returns:
            插件元数据
        """
        try:
            metadata = {
                'name': getattr(plugin_class, 'name', plugin_class.__name__),
                'version': getattr(plugin_class, 'version', '1.0.0'),
                'description': getattr(plugin_class, 'description', ''),
                'author': getattr(plugin_class, 'author', ''),
                'dependencies': getattr(plugin_class, 'dependencies', []),
                'class_name': plugin_class.__name__
            }

            return metadata

        except Exception as e:
            logger.error(f"获取插件元数据失败: {e}")
            return {}

    def call_plugin_method(self, plugin_name: str, method_name: str, *args, **kwargs) -> Any:
        """
        调用插件方法

        Args:
            plugin_name: 插件名称
            method_name: 方法名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            方法返回值
        """
        try:
            plugin = self.get_plugin(plugin_name)
            if plugin is None:
                logger.error(f"插件未找到: {plugin_name}")
                return None

            if not hasattr(plugin, method_name):
                logger.error(f"插件方法未找到: {plugin_name}.{method_name}")
                return None

            method = getattr(plugin, method_name)
            return method(*args, **kwargs)

        except Exception as e:
            logger.error(f"调用插件方法失败 {plugin_name}.{method_name}: {e}")
            return None

    def broadcast_event(self, event_name: str, *args, **kwargs) -> None:
        """
        向所有插件广播事件

        Args:
            event_name: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        try:
            for plugin_name, plugin in self.plugin_instances.items():
                try:
                    if hasattr(plugin, 'on_event'):
                        plugin.on_event(event_name, *args, **kwargs)

                    # 检查是否有特定的事件处理方法
                    event_method_name = f'on_{event_name}'
                    if hasattr(plugin, event_method_name):
                        method = getattr(plugin, event_method_name)
                        method(*args, **kwargs)

                except Exception as e:
                    logger.error(f"插件事件处理失败 {plugin_name}.{event_name}: {e}")

        except Exception as e:
            logger.error(f"广播事件失败 {event_name}: {e}")

    def get_plugins_by_type(self, plugin_type: str) -> List[Any]:
        """
        根据类型获取插件

        Args:
            plugin_type: 插件类型

        Returns:
            插件实例列表
        """
        try:
            matching_plugins = []

            for plugin_name, plugin in self.plugin_instances.items():
                metadata = self.plugin_metadata.get(plugin_name, {})
                if metadata.get('type') == plugin_type:
                    matching_plugins.append(plugin)

            return matching_plugins

        except Exception as e:
            logger.error(f"获取插件失败 {plugin_type}: {e}")
            return []

    def cleanup(self) -> None:
        """清理资源"""
        try:
            for plugin_name, plugin_instance in self.plugin_instances.items():
                if hasattr(plugin_instance, 'cleanup'):
                    plugin_instance.cleanup()

            self.loaded_plugins.clear()
            self.plugin_instances.clear()
            self.plugin_metadata.clear()

            logger.info("插件管理器清理完成")

        except Exception as e:
            logger.error(f"插件管理器清理失败: {e}")

    def enable_plugin(self, plugin_name: str) -> bool:
        """
        启用插件

        Args:
            plugin_name: 插件名称

        Returns:
            bool: 是否启用成功
        """
        try:
            if plugin_name not in self.plugin_instances:
                logger.error(f"插件未加载: {plugin_name}")
                return False

            plugin_instance = self.plugin_instances[plugin_name]

            # 调用插件的启用方法
            if hasattr(plugin_instance, 'enable'):
                plugin_instance.enable()

            # 更新插件状态
            if plugin_name in self.enhanced_plugins:
                self.enhanced_plugins[plugin_name].status = PluginStatus.ENABLED

            # 发送启用信号
            self.plugin_enabled.emit(plugin_name)

            logger.info(f"插件已启用: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"启用插件失败 {plugin_name}: {e}")
            self.plugin_error.emit(plugin_name, str(e))
            return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """
        禁用插件

        Args:
            plugin_name: 插件名称

        Returns:
            bool: 是否禁用成功
        """
        try:
            if plugin_name not in self.plugin_instances:
                logger.error(f"插件未加载: {plugin_name}")
                return False

            plugin_instance = self.plugin_instances[plugin_name]

            # 调用插件的禁用方法
            if hasattr(plugin_instance, 'disable'):
                plugin_instance.disable()

            # 更新插件状态
            if plugin_name in self.enhanced_plugins:
                self.enhanced_plugins[plugin_name].status = PluginStatus.DISABLED

            # 发送禁用信号
            self.plugin_disabled.emit(plugin_name)

            logger.info(f"插件已禁用: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"禁用插件失败 {plugin_name}: {e}")
            self.plugin_error.emit(plugin_name, str(e))
            return False

    def update_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """
        更新插件配置

        Args:
            plugin_name: 插件名称
            config: 新配置

        Returns:
            bool: 是否更新成功
        """
        try:
            if plugin_name not in self.plugin_instances:
                logger.error(f"插件未加载: {plugin_name}")
                return False

            plugin_instance = self.plugin_instances[plugin_name]

            # 更新插件实例的配置
            if hasattr(plugin_instance, 'update_config'):
                plugin_instance.update_config(config)

            # 更新元数据中的配置
            if plugin_name in self.plugin_metadata:
                self.plugin_metadata[plugin_name]['config'] = config

            # 更新增强插件信息中的配置
            if plugin_name in self.enhanced_plugins:
                self.enhanced_plugins[plugin_name].config.update(config)

            logger.info(f"插件配置已更新: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"更新插件配置失败 {plugin_name}: {e}")
            return False

    def get_plugin_status(self, plugin_name: str) -> Optional[PluginStatus]:
        """
        获取插件状态

        Args:
            plugin_name: 插件名称

        Returns:
            PluginStatus: 插件状态
        """
        if plugin_name in self.enhanced_plugins:
            return self.enhanced_plugins[plugin_name].status
        elif plugin_name in self.plugin_instances:
            return PluginStatus.LOADED
        else:
            return PluginStatus.UNLOADED

    def get_plugin_performance_stats(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件性能统计

        Args:
            plugin_name: 插件名称

        Returns:
            Dict: 性能统计数据
        """
        try:
            if plugin_name not in self.plugin_instances:
                return {}

            plugin_instance = self.plugin_instances[plugin_name]

            # 获取插件性能统计
            if hasattr(plugin_instance, 'get_performance_stats'):
                return plugin_instance.get_performance_stats()

            # 返回基本统计信息
            return {
                'status': self.get_plugin_status(plugin_name).value,
                'memory_usage': 0,  # 可以通过系统监控获取
                'cpu_usage': 0,
                'response_time': 0,
                'error_count': 0
            }

        except Exception as e:
            logger.error(f"获取插件性能统计失败 {plugin_name}: {e}")
            return {}

    def check_plugin_dependencies(self, plugin_name: str) -> bool:
        """
        检查插件依赖

        Args:
            plugin_name: 插件名称

        Returns:
            bool: 依赖是否满足
        """
        try:
            if plugin_name not in self.plugin_metadata:
                return False

            metadata = self.plugin_metadata[plugin_name]
            dependencies = metadata.get('dependencies', [])

            for dep in dependencies:
                if not self.is_plugin_loaded(dep):
                    logger.warning(f"插件 {plugin_name} 依赖 {dep} 未满足")
                    return False

            return True

        except Exception as e:
            logger.error(f"检查插件依赖失败 {plugin_name}: {e}")
            return False

    def get_system_stats(self) -> Dict[str, Any]:
        """
        获取插件系统统计信息

        Returns:
            Dict: 系统统计信息
        """
        try:
            total_plugins = len(self.enhanced_plugins)
            enabled_plugins = sum(1 for p in self.enhanced_plugins.values()
                                  if p.status == PluginStatus.ENABLED)
            disabled_plugins = sum(1 for p in self.enhanced_plugins.values()
                                   if p.status == PluginStatus.DISABLED)
            error_plugins = sum(1 for p in self.enhanced_plugins.values()
                                if p.status == PluginStatus.ERROR)

            return {
                'total_plugins': total_plugins,
                'enabled_plugins': enabled_plugins,
                'disabled_plugins': disabled_plugins,
                'error_plugins': error_plugins,
                'loaded_plugins': len(self.plugin_instances),
                'plugin_types': {
                    plugin_type.value: len(plugins)
                    for plugin_type, plugins in self.plugins_by_type.items()
                }
            }

        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {}

    def discover_enhanced_plugins(self) -> List[PluginInfo]:
        """
        发现增强插件（支持plugin.json配置）

        Returns:
            发现的插件列表
        """
        discovered = []

        for plugin_dir in self.plugin_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith('.'):
                plugin_json = plugin_dir / "plugin.json"
                if plugin_json.exists():
                    try:
                        with open(plugin_json, 'r', encoding='utf-8') as f:
                            config = json.load(f)

                        # 解析插件类型和分类
                        plugin_type = None
                        category = None

                        if 'plugin_type' in config:
                            try:
                                plugin_type = PluginType(config['plugin_type'])
                            except ValueError:
                                logger.warning(f"未知插件类型: {config['plugin_type']}")

                        if 'category' in config:
                            try:
                                category = PluginCategory(config['category'])
                            except ValueError:
                                logger.warning(f"未知插件分类: {config['category']}")

                        plugin_info = PluginInfo(
                            name=config.get('name', plugin_dir.name),
                            version=config.get('version', '1.0.0'),
                            description=config.get('description', ''),
                            author=config.get('author', ''),
                            path=str(plugin_dir),
                            status=PluginStatus.UNLOADED,
                            config=config,
                            dependencies=config.get('dependencies', []),
                            plugin_type=plugin_type,
                            category=category
                        )

                        discovered.append(plugin_info)
                        self.enhanced_plugins[plugin_info.name] = plugin_info

                        # 按类型分类
                        if plugin_type:
                            self.plugins_by_type[plugin_type].append(plugin_info.name)

                    except Exception as e:
                        logger.error(f"发现插件失败 {plugin_dir}: {e}")

        return discovered

    def get_plugins_by_type_enhanced(self, plugin_type: PluginType) -> List[PluginInfo]:
        """
        按类型获取插件

        Args:
            plugin_type: 插件类型

        Returns:
            指定类型的插件列表
        """
        plugin_names = self.plugins_by_type.get(plugin_type, [])
        return [self.enhanced_plugins[name] for name in plugin_names if name in self.enhanced_plugins]

    def call_plugin_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        调用插件钩子

        Args:
            hook_name: 钩子名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            钩子返回值列表
        """
        results = []

        if hook_name in self.plugin_hooks:
            for callback in self.plugin_hooks[hook_name]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"调用插件钩子失败 {hook_name}: {e}")

        return results

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """
        注册钩子

        Args:
            hook_name: 钩子名称
            callback: 回调函数
        """
        if hook_name not in self.plugin_hooks:
            self.plugin_hooks[hook_name] = []

        self.plugin_hooks[hook_name].append(callback)


class BasePlugin:
    """插件基类"""

    name = "BasePlugin"
    version = "1.0.0"
    description = "基础插件类"
    author = ""
    dependencies = []

    def __init__(self):
        """初始化插件"""
        self.logger = logging.getLogger(self.__class__.__name__)

    def initialize(self) -> None:
        """初始化插件"""
        self.logger.info(f"插件初始化: {self.name}")

    def cleanup(self) -> None:
        """清理插件"""
        self.logger.info(f"插件清理: {self.name}")

    def get_name(self) -> str:
        """获取插件名称"""
        return self.name

    def get_version(self) -> str:
        """获取插件版本"""
        return self.version

    def get_description(self) -> str:
        """获取插件描述"""
        return self.description

    def on_event(self, event_name: str, *args, **kwargs) -> None:
        """处理事件"""
        pass
