"""
UI资产类型工具类

提供资产类型的中文显示名称和UI组件支持
"""

from typing import List, Dict
from .plugin_types import AssetType


class UIAssetTypeUtils:
    """UI资产类型工具类"""

    # 资产类型中文显示名称映射
    DISPLAY_NAMES: Dict[AssetType, str] = {
        # 股票类
        AssetType.STOCK: "股票（通用）",
        AssetType.STOCK_US: "美股",
        AssetType.STOCK_A: "A股",
        AssetType.STOCK_B: "B股",
        AssetType.STOCK_H: "H股",
        AssetType.STOCK_HK: "港股",

        # 衍生品
        AssetType.FUTURES: "期货",
        AssetType.OPTION: "期权",
        AssetType.WARRANT: "权证",

        # 基金债券
        AssetType.FUND: "基金",
        AssetType.BOND: "债券",

        # 指数
        AssetType.INDEX: "指数",

        # 板块
        AssetType.SECTOR: "板块（通用）",
        AssetType.INDUSTRY_SECTOR: "行业板块",
        AssetType.CONCEPT_SECTOR: "概念板块",
        AssetType.STYLE_SECTOR: "风格板块",
        AssetType.THEME_SECTOR: "主题板块",

        # 其他
        AssetType.CRYPTO: "加密货币",
        AssetType.FOREX: "外汇",
        AssetType.COMMODITY: "商品",
        AssetType.MACRO: "宏观经济",
    }

    # 反向映射：中文 → AssetType
    REVERSE_MAPPING: Dict[str, AssetType] = {
        v: k for k, v in DISPLAY_NAMES.items()
    }

    # 常用资产类型（用于下拉框等）
    COMMON_TYPES: List[AssetType] = [
        AssetType.STOCK_A,      # A股
        AssetType.STOCK_US,     # 美股
        AssetType.STOCK_HK,     # 港股
        AssetType.FUTURES,      # 期货
        AssetType.FUND,         # 基金
        AssetType.BOND,         # 债券
        AssetType.INDEX,        # 指数
        AssetType.CRYPTO,       # 加密货币
    ]

    # 按类别分组
    GROUPED_TYPES = {
        "股票": [
            AssetType.STOCK_A,
            AssetType.STOCK_US,
            AssetType.STOCK_HK,
            AssetType.STOCK_B,
            AssetType.STOCK_H,
        ],
        "衍生品": [
            AssetType.FUTURES,
            AssetType.OPTION,
            AssetType.WARRANT,
        ],
        "基金债券": [
            AssetType.FUND,
            AssetType.BOND,
        ],
        "指数板块": [
            AssetType.INDEX,
            AssetType.SECTOR,
            AssetType.INDUSTRY_SECTOR,
            AssetType.CONCEPT_SECTOR,
        ],
        "其他": [
            AssetType.CRYPTO,
            AssetType.FOREX,
            AssetType.COMMODITY,
        ]
    }

    @classmethod
    def get_display_name(cls, asset_type: AssetType) -> str:
        """获取资产类型的中文显示名称"""
        return cls.DISPLAY_NAMES.get(asset_type, asset_type.value)

    @classmethod
    def get_asset_type(cls, display_name: str) -> AssetType:
        """根据中文显示名称获取AssetType"""
        return cls.REVERSE_MAPPING.get(display_name, AssetType.STOCK)

    @classmethod
    def get_common_display_names(cls) -> List[str]:
        """获取常用资产类型的中文显示名称列表（用于下拉框）"""
        return [cls.get_display_name(t) for t in cls.COMMON_TYPES]

    @classmethod
    def get_all_display_names(cls) -> List[str]:
        """获取所有资产类型的中文显示名称列表"""
        return [cls.get_display_name(t) for t in AssetType]

    @classmethod
    def get_grouped_display_names(cls) -> Dict[str, List[str]]:
        """获取按类别分组的资产类型显示名称"""
        return {
            category: [cls.get_display_name(t) for t in types]
            for category, types in cls.GROUPED_TYPES.items()
        }

    @classmethod
    def format_for_ui(cls, asset_type: AssetType, show_code: bool = False) -> str:
        """
        格式化资产类型用于UI显示

        Args:
            asset_type: 资产类型
            show_code: 是否显示代码（例如：A股 [stock_a]）

        Returns:
            格式化后的字符串
        """
        display_name = cls.get_display_name(asset_type)
        if show_code:
            return f"{display_name} [{asset_type.value}]"
        return display_name


# 便捷函数
def get_asset_type_combo_items(include_all: bool = False, grouped: bool = False) -> List[str]:
    """
    获取资产类型下拉框选项

    Args:
        include_all: 是否包含所有资产类型（默认只返回常用类型）
        grouped: 是否需要分组格式（暂不支持，预留）

    Returns:
        资产类型显示名称列表
    """
    if include_all:
        return UIAssetTypeUtils.get_all_display_names()
    return UIAssetTypeUtils.get_common_display_names()


def parse_asset_type_from_combo(display_name: str) -> AssetType:
    """
    从下拉框选择的显示名称解析AssetType

    Args:
        display_name: 显示名称（如"A股"）

    Returns:
        对应的AssetType
    """
    return UIAssetTypeUtils.get_asset_type(display_name)
