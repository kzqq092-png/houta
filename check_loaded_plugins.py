"""检查实际加载的插件"""
from core.plugin_manager import PluginManager
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))


pm = PluginManager()
pm.load_all_plugins()
plugins_dict = pm.get_all_plugins()

print(f"Total plugins loaded: {len(plugins_dict)}")
print("\nPlugins with 'crypto' or 'futures' in module:")
print("-" * 80)
for plugin_name, plugin_instance in plugins_dict.items():
    module = str(type(plugin_instance).__module__)
    if 'crypto' in module or 'futures' in module:
        plugin_id = plugin_instance.plugin_id if hasattr(plugin_instance, 'plugin_id') else 'NO ID'
        print(f"  Plugin Name (key): {plugin_name}")
        print(f"    plugin_id attr: {plugin_id}")
        print(f"    Type: {type(plugin_instance).__name__}")
        print(f"    Module: {module}")
        print()
