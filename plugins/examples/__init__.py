"""
插件示例包

包含各种类型的插件示例，用于演示如何开发YS-Quant‌插件。
"""

# 导出所有示例插件
from pathlib import Path
import importlib
import sys

# 获取当前目录下的所有Python文件
current_dir = Path(__file__).parent
for file_path in current_dir.glob("*.py"):
    if file_path.name == "__init__.py":
        continue

    # 导入模块
    module_name = file_path.stem
    try:
        # 动态导入
        module = importlib.import_module(f".{module_name}", package=__name__)
        # 将模块添加到当前命名空间
        globals()[module_name] = module
    except ImportError as e:
        print(f"无法导入示例插件 {module_name}: {e}")
