"""
主题类型定义模块
"""
from enum import Enum, auto
from typing import Dict, Any


class Theme(Enum):
    """主题枚举类型"""
    LIGHT = auto()  # 浅色主题
    DEEPBLUE = auto()   # 深蓝色主题

    @property
    def is_dark(self) -> bool:
        """是否是深色主题"""
        return self == Theme.DEEPBLUE

    @property
    def is_light(self) -> bool:
        """是否是浅色主题"""
        return self == Theme.LIGHT

    @classmethod
    def from_str(cls, theme_str: str) -> 'Theme':
        """从字符串创建主题枚举

        Args:
            theme_str: 主题字符串

        Returns:
            主题枚举值

        Raises:
            ValueError: 无效的主题字符串
        """
        theme_map = {
            'light': Theme.LIGHT,
            'dark': Theme.DEEPBLUE,
            '浅色': Theme.LIGHT,
            '深色': Theme.DEEPBLUE
        }

        theme_str = theme_str.lower()
        if theme_str not in theme_map:
            return Theme.LIGHT  # 默认返回浅色主题

        return theme_map[theme_str]


class ThemeConfig:
    """主题配置类"""

    def __init__(self):
        """初始化主题配置"""
        self.theme: Theme = Theme.LIGHT

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            配置字典
        """
        return {
            'theme': self.theme.name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThemeConfig':
        """从字典创建配置

        Args:
            data: 配置字典

        Returns:
            主题配置实例
        """
        config = cls()
        if 'theme' in data:
            try:
                config.theme = Theme[data['theme']]
            except (KeyError, ValueError):
                config.theme = Theme.LIGHT
        return config
