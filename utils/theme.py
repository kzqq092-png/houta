"""
Theme Management Module

This module provides a unified theme management solution with support for
multiple themes, dynamic theme switching, and theme customization.
"""

import json
import os
import re
from typing import Dict, Any, Optional, Union
from PyQt5.QtCore import *
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import *
from .config_manager import ConfigManager
from .theme_types import Theme
from .config_types import ThemeConfig
from core.base_logger import BaseLogManager
from utils.theme_utils import load_theme_json_with_comments
# Global theme manager instance
_theme_manager_instance: Optional['ThemeManager'] = None


def load_theme_json_with_comments(path: str) -> dict:
    """读取带注释的JSON文件，自动去除注释"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 去除 // 注释
    content = re.sub(r'//.*', '', content)
    # 去除 /* ... */ 注释（如有）
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # 去除多余空行
    content = '\n'.join(
        [line for line in content.splitlines() if line.strip()])
    return json.loads(content)


class ThemeManager(QObject):
    """主题管理器类，统一从config/theme.json读取所有配色"""

    # 主题变更信号
    theme_changed = pyqtSignal(Theme)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化主题管理器

        Args:
            config_manager: 配置管理器实例
        """
        super().__init__()

        # 初始化配置管理器
        self.config_manager = config_manager or ConfigManager()

        # 初始化主题缓存
        self._theme_cache = {}

        # 加载主题配置
        self._theme_json_path = os.path.join(os.path.dirname(
            os.path.dirname(__file__)), 'config', 'theme.json')
        self._theme_data = {}
        self._current_theme = Theme.LIGHT
        self._load_theme_json()

    def _load_theme_json(self):
        """加载主题配置文件"""
        try:
            self._theme_data = load_theme_json_with_comments(
                self._theme_json_path)
        except Exception as e:
            print(f"加载theme.json失败: {str(e)}")
            self._theme_data = {}

    @property
    def current_theme(self) -> Theme:
        """获取当前主题"""
        return self._current_theme

    def set_theme(self, theme: Theme) -> None:
        """设置主题

        Args:
            theme: 要设置的主题
        """
        if not isinstance(theme, Theme):
            raise ValueError(f"Invalid theme type: {type(theme)}")

        if theme != self._current_theme:
            self._current_theme = theme
            # 保存到配置
            self.config_manager.theme.theme = theme
            self.config_manager.save()
            # 发送主题变更信号
            self.theme_changed.emit(theme)

    def get_theme_colors(self, theme: Optional[Theme] = None) -> Dict[str, Any]:
        """获取主题颜色

        Args:
            theme: 可选的主题，默认使用当前主题

        Returns:
            主题颜色字典
        """
        theme = theme or self._current_theme
        theme_key = theme.name.lower() if hasattr(
            theme, 'name') else str(theme).lower()
        if theme_key in self._theme_cache:
            return self._theme_cache[theme_key].copy()
        colors = self._theme_data.get(theme_key, {})
        self._theme_cache[theme_key] = colors.copy()
        return colors

    def get_color(self, name: str, theme: Optional[Theme] = None, default: str = None) -> Any:
        """Get color by name

        Args:
            name: Color name
            theme: Theme to get color from, defaults to current theme
            default: Default color if not found

        Returns:
            Color value
        """
        colors = self.get_theme_colors(theme)
        return colors.get(name, default)

    def apply_theme(self, widget: QWidget, theme: Optional[Theme] = None) -> None:
        """应用主题到指定部件

        Args:
            widget: 要应用主题的部件
            theme: 可选的主题，默认使用当前主题
        """
        try:
            theme = theme or self._current_theme
            colors = self.get_theme_colors(theme)

            # 基础样式
            style = f"""
                QWidget {{
                    background-color: {colors.get('background', '#f7f9fa')};
                    color: {colors.get('text', '#222b45')};
                }}
                
                QGroupBox {{
                    border: 1px solid {colors.get('border', '#e0e0e0')};
                    border-radius: 6px;
                    margin-top: 6px;
                    padding: 6px;
                }}
                
                QPushButton {{
                    background-color: {colors.get('button_bg', '#e3f2fd')};
                    color: {colors.get('button_text', '#1565c0')};
                    border: 1px solid {colors.get('button_border', '#90caf9')};
                    border-radius: 4px;
                    padding: 4px;
                }}
                
                QPushButton:hover {{
                    background-color: {colors.get('button_hover', '#90caf9')};
                }}
                
                QPushButton:pressed {{
                    background-color: {colors.get('button_pressed', '#64b5f6')};
                }}
                
                QLineEdit, QTextEdit, QPlainTextEdit {{
                    background-color: {colors.get('background', '#f7f9fa')};
                    color: {colors.get('text', '#222b45')};
                    border: 1px solid {colors.get('border', '#e0e0e0')};
                    border-radius: 4px;
                    padding: 2px;
                }}
                
                QComboBox {{
                    background-color: {colors.get('background', '#f7f9fa')};
                    color: {colors.get('text', '#222b45')};
                    border: 1px solid {colors.get('border', '#e0e0e0')};
                    border-radius: 4px;
                    padding: 2px;
                }}
                
                QTableView {{
                    background-color: {colors.get('background', '#f7f9fa')};
                    color: {colors.get('text', '#222b45')};
                    border: 1px solid {colors.get('border', '#e0e0e0')};
                    gridline-color: {colors.get('border', '#e0e0e0')};
                }}
                
                QTableView::item:selected {{
                    background-color: {colors.get('selected_bg', '#E3F2FD')};
                    color: {colors.get('selected_text', '#1976D2')};
                }}
                
                QHeaderView::section {{
                    background-color: {colors.get('table_header_bg', '#2196F3')};
                    color: {colors.get('table_header_text', '#ffffff')};
                    padding: 4px;
                    border: none;
                }}
                
                QScrollBar:vertical {{
                    border: none;
                    background: {colors.get('background', '#f7f9fa')};
                    width: 5px;
                    margin: 0px;
                }}
                
                QScrollBar::handle:vertical {{
                    background: {colors.get('border', '#e0e0e0')};
                    min-height: 5px;
                    border-radius: 5px;
                }}

                QScrollBar:horizontal {{
                    border: none;
                    background: {colors.get('background', '#f7f9fa')};
                    height: 5px;
                    margin: 0px;
                }}

                QScrollBar::handle:horizontal {{
                    background: {colors.get('border', '#e0e0e0')};
                    min-width: 5px;
                    border-radius: 5px;
                }}

                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    background: none;
                    border: none;
                }}
            """

            # 如果是渐变主题,添加渐变背景
            if theme == Theme.GRADIENT:
                style = style.replace(
                    f"background-color: {colors.get('background', '#f7f9fa')};",
                    f"background: {colors.get('background', 'linear-gradient(135deg, #3a8dde 0%, #7b1fa2 100%)')};"
                )

            widget.setStyleSheet(style)

        except Exception as e:
            print(f"应用主题到部件失败: {str(e)}")

    def apply_chart_theme(self, figure, theme: Optional[Theme] = None) -> None:
        """Apply theme to matplotlib figure

        Args:
            figure: Matplotlib figure to apply theme to
            theme: Theme to apply, defaults to current theme
        """
        if theme is None:
            theme = self.current_theme

        try:
            colors = self.get_theme_colors(theme)

            # Set figure facecolor
            figure.set_facecolor(colors.get('chart_background', '#ffffff'))

            # Set axes colors
            for ax in figure.get_axes():
                ax.set_facecolor(colors.get('chart_background', '#ffffff'))
                ax.tick_params(colors=colors.get('chart_text', '#222b45'))
                ax.spines['bottom'].set_color(
                    colors.get('chart_grid', '#e0e0e0'))
                ax.spines['top'].set_color(colors.get('chart_grid', '#e0e0e0'))
                ax.spines['right'].set_color(
                    colors.get('chart_grid', '#e0e0e0'))
                ax.spines['left'].set_color(
                    colors.get('chart_grid', '#e0e0e0'))
                ax.title.set_color(colors.get('chart_text', '#222b45'))
                ax.xaxis.label.set_color(colors.get('chart_text', '#222b45'))
                ax.yaxis.label.set_color(colors.get('chart_text', '#222b45'))

                # Set grid color
                ax.grid(True, color=colors.get(
                    'chart_grid', '#e0e0e0'), alpha=0.3)

                # Set tick colors
                for tick in ax.get_xticklabels():
                    tick.set_color(colors.get('chart_text', '#222b45'))
                for tick in ax.get_yticklabels():
                    tick.set_color(colors.get('chart_text', '#222b45'))

            # Draw figure
            figure.canvas.draw()

        except Exception as e:
            print(f"应用图表主题失败: {str(e)}")

    def is_dark_theme(self) -> bool:
        """Check if current theme is dark

        Returns:
            True if current theme is dark
        """
        return self.current_theme.is_dark


def get_theme_manager(config_manager: Optional[ConfigManager] = None) -> ThemeManager:
    """获取主题管理器实例

    Args:
        config_manager: 可选的配置管理器实例

    Returns:
        主题管理器实例
    """
    global _theme_manager_instance
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager(config_manager)
    return _theme_manager_instance
