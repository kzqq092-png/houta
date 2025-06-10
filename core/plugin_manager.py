"""
插件管理器：支持AI助手Tab输入/输出/日志/可视化等插件注册、加载、发现。
"""
import os
import importlib
from typing import Dict, Callable, Any


class PluginManager:
    """插件管理器"""

    def __init__(self, plugin_dir: str = 'plugins'):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Any] = {}
        self.hooks: Dict[str, list] = {}
        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir)

    def register_plugin(self, name: str, plugin: Any):
        self.plugins[name] = plugin

    def load_plugins(self):
        """自动加载插件目录下所有插件"""
        for fname in os.listdir(self.plugin_dir):
            if fname.endswith('.py') and not fname.startswith('_'):
                mod_name = fname[:-3]
                mod = importlib.import_module(f'{self.plugin_dir}.{mod_name}')
                if hasattr(mod, 'register'):
                    mod.register(self)

    def register_hook(self, hook_name: str, func: Callable):
        self.hooks.setdefault(hook_name, []).append(func)

    def call_hook(self, hook_name: str, *args, **kwargs):
        results = []
        for func in self.hooks.get(hook_name, []):
            results.append(func(*args, **kwargs))
        return results

    def get_plugin(self, name: str):
        return self.plugins.get(name)
