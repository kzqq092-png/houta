#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件工具类
提供插件相关的辅助功能，包括类型映射、显示工具等
"""

from typing import Dict, Any, Optional
from core.plugin_types import PluginType, PluginCategory


class PluginDisplayUtils:
    """插件显示工具类"""

    # 插件类型中文映射
    PLUGIN_TYPE_MAP = {
        PluginType.INDICATOR.value: "技术指标",
        PluginType.STRATEGY.value: "交易策略",
        PluginType.DATA_SOURCE.value: "数据源",
        PluginType.ANALYSIS.value: "分析工具",
        PluginType.UI_COMPONENT.value: "界面组件",
        PluginType.EXPORT.value: "导出工具",
        PluginType.NOTIFICATION.value: "消息通知",
        PluginType.CHART_TOOL.value: "图表工具",
        "unknown": "未知类型"
    }

    # 插件分类中文映射
    PLUGIN_CATEGORY_MAP = {
        PluginCategory.CORE.value: "核心插件",
        PluginCategory.COMMUNITY.value: "社区插件",
        PluginCategory.COMMERCIAL.value: "商业插件",
        PluginCategory.EXPERIMENTAL.value: "实验插件",
        "unknown": "未知分类"
    }

    # 插件状态中文映射
    PLUGIN_STATUS_MAP = {
        "enabled": "已启用",
        "disabled": "已禁用",
        "loaded": "已加载",
        "unloaded": "未加载",
        "error": "错误",
        "installed": "已安装",
        "uninstalled": "未安装"
    }

    # 插件类型图标映射
    PLUGIN_TYPE_ICONS = {
        PluginType.INDICATOR.value: "📊",
        PluginType.STRATEGY.value: "🎯",
        PluginType.DATA_SOURCE.value: "📡",
        PluginType.ANALYSIS.value: "🔍",
        PluginType.UI_COMPONENT.value: "🖥️",
        PluginType.EXPORT.value: "📤",
        PluginType.NOTIFICATION.value: "🔔",
        PluginType.CHART_TOOL.value: "📈",
        "unknown": "❓"
    }

    # 插件分类颜色映射
    PLUGIN_CATEGORY_COLORS = {
        PluginCategory.CORE.value: "#007bff",       # 蓝色 - 核心
        PluginCategory.COMMUNITY.value: "#28a745",  # 绿色 - 社区
        PluginCategory.COMMERCIAL.value: "#ffc107",  # 黄色 - 商业
        PluginCategory.EXPERIMENTAL.value: "#6f42c1",  # 紫色 - 实验
        "unknown": "#6c757d"                        # 灰色 - 未知
    }

    @classmethod
    def get_plugin_type_display(cls, plugin_type: str) -> str:
        """
        获取插件类型的中文显示名称

        Args:
            plugin_type: 插件类型（英文）

        Returns:
            中文显示名称
        """
        return cls.PLUGIN_TYPE_MAP.get(plugin_type, cls.PLUGIN_TYPE_MAP["unknown"])

    @classmethod
    def get_plugin_category_display(cls, category: str) -> str:
        """
        获取插件分类的中文显示名称

        Args:
            category: 插件分类（英文）

        Returns:
            中文显示名称
        """
        return cls.PLUGIN_CATEGORY_MAP.get(category, cls.PLUGIN_CATEGORY_MAP["unknown"])

    @classmethod
    def get_plugin_status_display(cls, status: str) -> str:
        """
        获取插件状态的中文显示名称

        Args:
            status: 插件状态（英文）

        Returns:
            中文显示名称
        """
        return cls.PLUGIN_STATUS_MAP.get(status, status)

    @classmethod
    def get_plugin_type_icon(cls, plugin_type: str) -> str:
        """
        获取插件类型对应的图标

        Args:
            plugin_type: 插件类型（英文）

        Returns:
            图标字符
        """
        return cls.PLUGIN_TYPE_ICONS.get(plugin_type, cls.PLUGIN_TYPE_ICONS["unknown"])

    @classmethod
    def get_plugin_category_color(cls, category: str) -> str:
        """
        获取插件分类对应的颜色

        Args:
            category: 插件分类（英文）

        Returns:
            颜色代码
        """
        return cls.PLUGIN_CATEGORY_COLORS.get(category, cls.PLUGIN_CATEGORY_COLORS["unknown"])

    @classmethod
    def format_plugin_info(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化插件信息，添加中文显示

        Args:
            metadata: 原始插件元数据

        Returns:
            格式化后的插件信息
        """
        plugin_type = metadata.get('plugin_type', 'unknown')
        category = metadata.get('category', 'unknown')

        return {
            **metadata,
            'type_display': cls.get_plugin_type_display(plugin_type),
            'category_display': cls.get_plugin_category_display(category),
            'type_icon': cls.get_plugin_type_icon(plugin_type),
            'category_color': cls.get_plugin_category_color(category),
            'tags_display': ', '.join(metadata.get('tags', [])) if metadata.get('tags') else '无标签'
        }

    @classmethod
    def get_plugin_summary(cls, metadata: Dict[str, Any]) -> str:
        """
        获取插件摘要信息

        Args:
            metadata: 插件元数据

        Returns:
            插件摘要字符串
        """
        name = metadata.get('name', '未知插件')
        version = metadata.get('version', '1.0.0')
        plugin_type = cls.get_plugin_type_display(metadata.get('plugin_type', 'unknown'))
        author = metadata.get('author', '未知作者')

        return f"{name} v{version} - {plugin_type} (by {author})"

    @classmethod
    def validate_plugin_metadata(cls, metadata: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证插件元数据的完整性

        Args:
            metadata: 插件元数据

        Returns:
            (是否有效, 错误信息)
        """
        required_fields = ['name', 'version', 'description', 'author']
        missing_fields = []

        for field in required_fields:
            if not metadata.get(field):
                missing_fields.append(field)

        if missing_fields:
            return False, f"缺少必填字段: {', '.join(missing_fields)}"

        return True, ""


# 便捷函数
def get_plugin_display_name(plugin_type: str) -> str:
    """获取插件类型显示名称的便捷函数"""
    return PluginDisplayUtils.get_plugin_type_display(plugin_type)


def format_plugin_for_ui(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """为UI显示格式化插件信息的便捷函数"""
    return PluginDisplayUtils.format_plugin_info(metadata)
