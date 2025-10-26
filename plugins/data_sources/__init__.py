"""
数据源插件目录

支持按资产类型分类的插件自动发现和加载
"""

from pathlib import Path
from typing import Dict, List
import importlib

# 按资产类型组织的插件目录
PLUGIN_CATEGORIES = {
    'stock': 'A股数据源',
    'stock_international': '国际股票数据源',
    'crypto': '加密货币数据源',
    'futures': '期货数据源',
    'forex': '外汇数据源',
    'bond': '债券数据源',
    'commodity': '大宗商品数据源',
    'custom': '自定义数据源',
    'fundamental': '基本面数据源'
}


def discover_plugins_by_category(category: str) -> List[str]:
    """按分类发现插件"""
    category_path = Path(__file__).parent / category
    if not category_path.exists():
        return []

    plugins = []
    for plugin_file in category_path.glob('*_plugin.py'):
        plugin_name = plugin_file.stem
        plugins.append(f"data_sources.{category}.{plugin_name}")

    return plugins


def get_all_plugins() -> Dict[str, List[str]]:
    """获取所有插件，按分类组织"""
    all_plugins = {}
    for category in PLUGIN_CATEGORIES.keys():
        all_plugins[category] = discover_plugins_by_category(category)
    return all_plugins


# 导出
__all__ = ['PLUGIN_CATEGORIES', 'discover_plugins_by_category', 'get_all_plugins']
