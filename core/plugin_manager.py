"""
插件管理器模块
提供插件系统的核心功能：插件加载、卸载、热重载、依赖管理等
"""
import os
import sys
import importlib
import importlib.util
import inspect
import json
import threading
from typing import Dict, List, Any, Optional, Type, Callable
from pathlib import Path
from abc import ABC, abstractmethod
import traceback
from dataclasses import dataclass
from enum import Enum


class PluginStatus(Enum):
    """插件状态枚举"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str]
    min_app_version: str
    max_app_version: str
    entry_point: str
    config_schema: Dict[str, Any]
    permissions: List[str]


class PluginInterface(ABC):
    """插件接口基类"""

    @abstractmethod
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        pass

    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> bool:
        """初始化插件"""
        pass

    @abstractmethod
    def activate(self) -> bool:
        """激活插件"""
        pass

    @abstractmethod
    def deactivate(self) -> bool:
        """停用插件"""
        pass

    @abstractmethod
    def cleanup(self) -> bool:
        """清理插件资源"""
        pass

    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式"""
        return {}

    def on_config_changed(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """配置变化回调"""
        pass


class PluginContext:
    """插件上下文"""

    def __init__(self, app_instance, config_manager, log_manager):
        self.app = app_instance
        self.config = config_manager
        self.logger = log_manager
        self.shared_data = {}
        self._event_handlers = {}

    def register_event_handler(self, event_name: str, handler: Callable):
        """注册事件处理器"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    def unregister_event_handler(self, event_name: str, handler: Callable):
        """取消注册事件处理器"""
        if event_name in self._event_handlers and handler in self._event_handlers[event_name]:
            self._event_handlers[event_name].remove(handler)

    def emit_event(self, event_name: str, *args, **kwargs):
        """触发事件"""
        if event_name in self._event_handlers:
            for handler in self._event_handlers[event_name]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"事件处理器错误 {event_name}: {e}")


class Plugin:
    """插件包装类"""

    def __init__(self, plugin_dir: Path, manifest_data: Dict[str, Any]):
        self.plugin_dir = plugin_dir
        self.manifest_data = manifest_data
        self.name = manifest_data.get("name", plugin_dir.name)
        self.version = manifest_data.get("version", "1.0.0")
        self.status = PluginStatus.UNLOADED
        self.instance = None
        self.module = None
        self.error_message = None
        self.dependencies_resolved = False

    @property
    def info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name=self.manifest_data.get("name", self.name),
            version=self.version,
            description=self.manifest_data.get("description", ""),
            author=self.manifest_data.get("author", ""),
            dependencies=self.manifest_data.get("dependencies", []),
            min_app_version=self.manifest_data.get("min_app_version", "1.0.0"),
            max_app_version=self.manifest_data.get("max_app_version", "999.0.0"),
            entry_point=self.manifest_data.get("entry_point", "main.py"),
            config_schema=self.manifest_data.get("config_schema", {}),
            permissions=self.manifest_data.get("permissions", [])
        )


class PluginManager:
    """插件管理器"""

    def __init__(self, plugin_dir: str = "plugins", config_manager=None, log_manager=None):
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(exist_ok=True)

        self.config_manager = config_manager
        self.log_manager = log_manager
        self.context = None

        # 插件存储
        self.plugins: Dict[str, Plugin] = {}
        self.loaded_plugins: Dict[str, Plugin] = {}
        self.active_plugins: Dict[str, Plugin] = {}

        # 插件配置
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}

        # 线程安全
        self._lock = threading.RLock()

        # 事件回调
        self._callbacks = {
            "plugin_loaded": [],
            "plugin_unloaded": [],
            "plugin_activated": [],
            "plugin_deactivated": [],
            "plugin_error": []
        }

        # 扫描插件
        self.scan_plugins()

    def set_context(self, app_instance, config_manager=None, log_manager=None):
        """设置插件上下文"""
        if config_manager:
            self.config_manager = config_manager
        if log_manager:
            self.log_manager = log_manager

        self.context = PluginContext(app_instance, self.config_manager, self.log_manager)

    def scan_plugins(self):
        """扫描插件目录"""
        try:
            for plugin_path in self.plugin_dir.iterdir():
                if plugin_path.is_dir() and not plugin_path.name.startswith('.'):
                    self._scan_plugin_directory(plugin_path)
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"扫描插件目录失败: {e}")

    def _scan_plugin_directory(self, plugin_path: Path):
        """扫描单个插件目录"""
        try:
            manifest_file = plugin_path / "manifest.json"
            if not manifest_file.exists():
                return

            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            plugin = Plugin(plugin_path, manifest_data)
            self.plugins[plugin.name] = plugin

            if self.log_manager:
                self.log_manager.info(f"发现插件: {plugin.name} v{plugin.version}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"扫描插件目录失败 {plugin_path}: {e}")

    def load_plugin(self, plugin_name: str) -> bool:
        """
        加载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功加载
        """
        with self._lock:
            if plugin_name not in self.plugins:
                if self.log_manager:
                    self.log_manager.error(f"插件不存在: {plugin_name}")
                return False

            plugin = self.plugins[plugin_name]

            if plugin.status == PluginStatus.LOADED:
                return True

            try:
                plugin.status = PluginStatus.LOADING

                # 检查依赖
                if not self._resolve_dependencies(plugin):
                    plugin.status = PluginStatus.ERROR
                    plugin.error_message = "依赖解析失败"
                    return False

                # 加载模块
                if not self._load_plugin_module(plugin):
                    plugin.status = PluginStatus.ERROR
                    return False

                # 创建插件实例
                if not self._create_plugin_instance(plugin):
                    plugin.status = PluginStatus.ERROR
                    return False

                # 初始化插件
                if not self._initialize_plugin(plugin):
                    plugin.status = PluginStatus.ERROR
                    return False

                plugin.status = PluginStatus.LOADED
                self.loaded_plugins[plugin_name] = plugin

                # 触发回调
                self._emit_callback("plugin_loaded", plugin)

                if self.log_manager:
                    self.log_manager.info(f"插件加载成功: {plugin_name}")

                return True

            except Exception as e:
                plugin.status = PluginStatus.ERROR
                plugin.error_message = str(e)
                self._emit_callback("plugin_error", plugin, e)

                if self.log_manager:
                    self.log_manager.error(f"插件加载失败 {plugin_name}: {e}")
                    self.log_manager.error(traceback.format_exc())

                return False

    def _resolve_dependencies(self, plugin: Plugin) -> bool:
        """解析插件依赖"""
        try:
            for dep_name in plugin.info.dependencies:
                if dep_name not in self.loaded_plugins:
                    if dep_name in self.plugins:
                        if not self.load_plugin(dep_name):
                            return False
                    else:
                        if self.log_manager:
                            self.log_manager.error(f"依赖插件不存在: {dep_name}")
                        return False

            plugin.dependencies_resolved = True
            return True

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"解析依赖失败 {plugin.name}: {e}")
            return False

    def _load_plugin_module(self, plugin: Plugin) -> bool:
        """加载插件模块"""
        try:
            entry_point = plugin.plugin_dir / plugin.info.entry_point
            if not entry_point.exists():
                if self.log_manager:
                    self.log_manager.error(f"入口文件不存在: {entry_point}")
                return False

            # 添加插件目录到sys.path
            plugin_dir_str = str(plugin.plugin_dir)
            if plugin_dir_str not in sys.path:
                sys.path.insert(0, plugin_dir_str)

            # 加载模块
            module_name = f"plugin_{plugin.name}_{plugin.version.replace('.', '_')}"
            spec = importlib.util.spec_from_file_location(module_name, entry_point)

            if spec is None or spec.loader is None:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin.module = module
            return True

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"加载模块失败 {plugin.name}: {e}")
            return False

    def _create_plugin_instance(self, plugin: Plugin) -> bool:
        """创建插件实例"""
        try:
            # 查找插件类
            plugin_class = None
            for name, obj in inspect.getmembers(plugin.module):
                if (inspect.isclass(obj) and
                    issubclass(obj, PluginInterface) and
                        obj != PluginInterface):
                    plugin_class = obj
                    break

            if plugin_class is None:
                if self.log_manager:
                    self.log_manager.error(f"未找到插件类: {plugin.name}")
                return False

            # 创建实例
            plugin.instance = plugin_class()
            return True

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建插件实例失败 {plugin.name}: {e}")
            return False

    def _initialize_plugin(self, plugin: Plugin) -> bool:
        """初始化插件"""
        try:
            if self.context is None:
                if self.log_manager:
                    self.log_manager.warning(f"插件上下文未设置: {plugin.name}")
                return False

            # 准备上下文数据
            context_data = {
                "app": self.context.app,
                "config": self.context.config,
                "logger": self.context.logger,
                "plugin_dir": plugin.plugin_dir,
                "plugin_config": self.plugin_configs.get(plugin.name, {}),
                "shared_data": self.context.shared_data
            }

            # 初始化插件
            return plugin.instance.initialize(context_data)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化插件失败 {plugin.name}: {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功卸载
        """
        with self._lock:
            if plugin_name not in self.loaded_plugins:
                return True

            plugin = self.loaded_plugins[plugin_name]

            try:
                # 先停用插件
                if plugin_name in self.active_plugins:
                    self.deactivate_plugin(plugin_name)

                # 清理插件资源
                if plugin.instance:
                    plugin.instance.cleanup()

                # 从加载列表中移除
                del self.loaded_plugins[plugin_name]

                # 更新状态
                plugin.status = PluginStatus.UNLOADED
                plugin.instance = None
                plugin.module = None

                # 触发回调
                self._emit_callback("plugin_unloaded", plugin)

                if self.log_manager:
                    self.log_manager.info(f"插件卸载成功: {plugin_name}")

                return True

            except Exception as e:
                plugin.status = PluginStatus.ERROR
                plugin.error_message = str(e)

                if self.log_manager:
                    self.log_manager.error(f"插件卸载失败 {plugin_name}: {e}")

                return False

    def activate_plugin(self, plugin_name: str) -> bool:
        """
        激活插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功激活
        """
        with self._lock:
            if plugin_name not in self.loaded_plugins:
                if not self.load_plugin(plugin_name):
                    return False

            plugin = self.loaded_plugins[plugin_name]

            if plugin_name in self.active_plugins:
                return True

            try:
                if plugin.instance.activate():
                    plugin.status = PluginStatus.ACTIVE
                    self.active_plugins[plugin_name] = plugin

                    # 触发回调
                    self._emit_callback("plugin_activated", plugin)

                    if self.log_manager:
                        self.log_manager.info(f"插件激活成功: {plugin_name}")

                    return True
                else:
                    return False

            except Exception as e:
                plugin.status = PluginStatus.ERROR
                plugin.error_message = str(e)

                if self.log_manager:
                    self.log_manager.error(f"插件激活失败 {plugin_name}: {e}")

                return False

    def deactivate_plugin(self, plugin_name: str) -> bool:
        """
        停用插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功停用
        """
        with self._lock:
            if plugin_name not in self.active_plugins:
                return True

            plugin = self.active_plugins[plugin_name]

            try:
                if plugin.instance.deactivate():
                    del self.active_plugins[plugin_name]
                    plugin.status = PluginStatus.LOADED

                    # 触发回调
                    self._emit_callback("plugin_deactivated", plugin)

                    if self.log_manager:
                        self.log_manager.info(f"插件停用成功: {plugin_name}")

                    return True
                else:
                    return False

            except Exception as e:
                plugin.status = PluginStatus.ERROR
                plugin.error_message = str(e)

                if self.log_manager:
                    self.log_manager.error(f"插件停用失败 {plugin_name}: {e}")

                return False

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        重新加载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功重新加载
        """
        was_active = plugin_name in self.active_plugins

        # 卸载插件
        if not self.unload_plugin(plugin_name):
            return False

        # 重新扫描插件
        if plugin_name in self.plugins:
            plugin_path = self.plugins[plugin_name].plugin_dir
            self._scan_plugin_directory(plugin_path)

        # 重新加载插件
        if not self.load_plugin(plugin_name):
            return False

        # 如果之前是激活状态，重新激活
        if was_active:
            return self.activate_plugin(plugin_name)

        return True

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name].info
        return None

    def get_plugin_status(self, plugin_name: str) -> Optional[PluginStatus]:
        """获取插件状态"""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name].status
        return None

    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有插件"""
        plugins_list = []
        for plugin_name, plugin in self.plugins.items():
            plugins_list.append({
                "name": plugin_name,
                "version": plugin.version,
                "status": plugin.status.value,
                "description": plugin.info.description,
                "author": plugin.info.author,
                "dependencies": plugin.info.dependencies,
                "error_message": plugin.error_message
            })
        return plugins_list

    def register_callback(self, event_name: str, callback: Callable):
        """注册事件回调"""
        if event_name in self._callbacks:
            self._callbacks[event_name].append(callback)

    def unregister_callback(self, event_name: str, callback: Callable):
        """取消注册事件回调"""
        if event_name in self._callbacks and callback in self._callbacks[event_name]:
            self._callbacks[event_name].remove(callback)

    def _emit_callback(self, event_name: str, *args, **kwargs):
        """触发事件回调"""
        if event_name in self._callbacks:
            for callback in self._callbacks[event_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    if self.log_manager:
                        self.log_manager.error(f"插件回调错误 {event_name}: {e}")

    def load_all_plugins(self):
        """加载所有插件"""
        for plugin_name in self.plugins:
            self.load_plugin(plugin_name)

    def load_plugins(self):
        """加载所有插件（别名方法，兼容main.py调用）"""
        return self.load_all_plugins()

    def activate_all_plugins(self):
        """激活所有已加载的插件"""
        for plugin_name in self.loaded_plugins:
            self.activate_plugin(plugin_name)

    def shutdown(self):
        """关闭插件管理器"""
        # 停用所有插件
        for plugin_name in list(self.active_plugins.keys()):
            self.deactivate_plugin(plugin_name)

        # 卸载所有插件
        for plugin_name in list(self.loaded_plugins.keys()):
            self.unload_plugin(plugin_name)


# 插件装饰器
def plugin_command(name: str, description: str = "", permissions: List[str] = None):
    """插件命令装饰器"""
    def decorator(func):
        func._plugin_command = True
        func._command_name = name
        func._command_description = description
        func._command_permissions = permissions or []
        return func
    return decorator


def plugin_event_handler(event_name: str):
    """插件事件处理器装饰器"""
    def decorator(func):
        func._plugin_event_handler = True
        func._event_name = event_name
        return func
    return decorator


# 示例插件基类
class ExamplePlugin(PluginInterface):
    """示例插件"""

    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="example_plugin",
            version="1.0.0",
            description="示例插件",
            author="HIkyuu Team",
            dependencies=[],
            min_app_version="1.0.0",
            max_app_version="2.0.0",
            entry_point="main.py",
            config_schema={},
            permissions=[]
        )

    def initialize(self, context: Dict[str, Any]) -> bool:
        self.context = context
        self.logger = context.get("logger")
        if self.logger:
            self.logger.info("示例插件初始化")
        return True

    def activate(self) -> bool:
        if self.logger:
            self.logger.info("示例插件激活")
        return True

    def deactivate(self) -> bool:
        if self.logger:
            self.logger.info("示例插件停用")
        return True

    def cleanup(self) -> bool:
        if self.logger:
            self.logger.info("示例插件清理")
        return True
