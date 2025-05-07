"""
Theme Management Module

This module provides a unified theme management solution with support for
multiple themes, dynamic theme switching, and theme customization.
"""

import json
import os
from typing import Dict, Any, Optional, Union
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication, QStyleFactory, QMainWindow, QWidget
from .config_manager import ConfigManager
from .theme_types import Theme
from .config_types import ThemeConfig
from core.base_logger import BaseLogManager
# Global theme manager instance
_theme_manager_instance: Optional['ThemeManager'] = None


class ThemeManager(QObject):
    """Enhanced theme manager with dynamic theme switching and customization

    Features:
    - Multiple built-in themes
    - Custom theme support
    - Dynamic theme switching
    - Theme customization
    - Theme persistence
    - Theme validation
    """

    theme_changed = pyqtSignal(Theme)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__()
        self.log_manager = BaseLogManager()
        self.log_manager.info("初始化主题管理器")
        self.config_manager = config_manager or ConfigManager()
        self.log_manager.info("初始化主题配置")

        # 从配置加载主题，如果配置中没有则使用默认主题
        try:
            theme_str = self.config_manager.theme.name.lower()
            self._current_theme = Theme.from_str(theme_str)
        except (ValueError, AttributeError) as e:
            self.log_manager.error(f"加载主题配置失败: {str(e)}")
            self._current_theme = Theme.LIGHT
            self.config_manager.theme.name = self._current_theme.name.lower()

        self.log_manager.info("加载默认主题色")
        self._themes = {
            Theme.LIGHT: {
                'background': '#FFFFFF',
                'foreground': '#000000',
                'primary': '#007ACC',
                'secondary': '#5C6BC0',
                'success': '#4CAF50',
                'warning': '#FFC107',
                'error': '#F44336',
                'border': '#E0E0E0',
                'hover': '#F5F5F5',
                'selected': '#E3F2FD',
                'text': '#212121',
                'text_secondary': '#757575',
                'chart_background': '#FFFFFF',
                'chart_grid': '#E0E0E0',
                'chart_text': '#212121',
                'chart_line': '#2196F3'
            },
            Theme.DARK: {
                'background': '#1E1E1E',
                'foreground': '#FFFFFF',
                'primary': '#0078D4',
                'secondary': '#3F51B5',
                'success': '#4CAF50',
                'warning': '#FFC107',
                'error': '#F44336',
                'border': '#424242',
                'hover': '#2D2D2D',
                'selected': '#094771',
                'text': '#FFFFFF',
                'text_secondary': '#BDBDBD',
                'chart_background': '#1E1E1E',
                'chart_grid': '#424242',
                'chart_text': '#FFFFFF',
                'chart_line': '#2196F3'
            },
            Theme.BLUE: {
                'background': '#F5F9FC',
                'foreground': '#1A1A1A',
                'primary': '#1976D2',
                'secondary': '#303F9F',
                'success': '#43A047',
                'warning': '#FFA000',
                'error': '#E53935',
                'border': '#BBDEFB',
                'hover': '#E3F2FD',
                'selected': '#BBDEFB',
                'text': '#1A1A1A',
                'text_secondary': '#616161',
                'chart_background': '#F5F9FC',
                'chart_grid': '#BBDEFB',
                'chart_text': '#1A1A1A',
                'chart_line': '#1976D2'
            },
            Theme.SYSTEM: {
                'background': '#FFFFFF',
                'foreground': '#000000',
                'primary': '#007ACC',
                'secondary': '#5C6BC0',
                'success': '#4CAF50',
                'warning': '#FFC107',
                'error': '#F44336',
                'border': '#E0E0E0',
                'hover': '#F5F5F5',
                'selected': '#E3F2FD',
                'text': '#212121',
                'text_secondary': '#757575',
                'chart_background': '#FFFFFF',
                'chart_grid': '#E0E0E0',
                'chart_text': '#212121',
                'chart_line': '#2196F3'
            },
            Theme.CUSTOM: {
                'background': '#FFFFFF',
                'foreground': '#000000',
                'primary': '#007ACC',
                'secondary': '#5C6BC0',
                'success': '#4CAF50',
                'warning': '#FFC107',
                'error': '#F44336',
                'border': '#E0E0E0',
                'hover': '#F5F5F5',
                'selected': '#E3F2FD',
                'text': '#212121',
                'text_secondary': '#757575',
                'chart_background': '#FFFFFF',
                'chart_grid': '#E0E0E0',
                'chart_text': '#212121',
                'chart_line': '#2196F3'
            }
        }
        self.log_manager.info("加载颜色主题结束")

        # 加载自定义主题颜色
        self._custom_colors = self.config_manager.theme.custom_colors
        self.log_manager.info("加载自定义颜色主题结束")

        # 如果当前主题是自定义主题，但没有自定义颜色配置，则切换到默认主题
        if self._current_theme == Theme.CUSTOM and not self._custom_colors:
            self.log_manager.info("未找到自定义主题配置，切换到默认主题")
            self._current_theme = Theme.LIGHT
            self.config_manager.theme.name = self._current_theme.name.lower()

    @property
    def current_theme(self) -> Theme:
        """Get current theme"""
        return self._current_theme

    @current_theme.setter
    def current_theme(self, theme: Theme):
        """Set current theme"""
        if theme not in Theme:
            raise ValueError(f"不支持的主题: {theme}")

        if theme != self._current_theme:
            self._current_theme = theme
            # 更新配置
            self.config_manager.theme.name = theme.name.lower()
            # 如果是自定义主题，同时更新自定义颜色配置
            if theme == Theme.CUSTOM:
                self.config_manager.theme.custom_colors = self._custom_colors
            self.theme_changed.emit(theme)

    def set_theme(self, theme: Theme):
        """Set current theme

        Args:
            theme: Theme to set
        """
        try:
            self.current_theme = theme
            self.log_manager.info(f"主题切换成功: {theme.name}")
        except Exception as e:
            self.log_manager.error(f"主题切换失败: {str(e)}")

    def get_theme_colors(self, theme: Optional[Theme] = None) -> Dict[str, str]:
        """Get theme colors

        Args:
            theme: Theme to get colors for, defaults to current theme

        Returns:
            Dictionary containing theme colors
        """
        if theme is None:
            theme = self.current_theme

        if theme == Theme.CUSTOM and self._custom_colors:
            return self._custom_colors.copy()

        if theme not in self._themes:
            self.log_manager.info(f"未找到主题配置: {theme.name}，使用默认主题")
            theme = Theme.LIGHT

        return self._themes[theme].copy()

    def set_custom_colors(self, colors: Dict[str, str]) -> None:
        """Set custom theme colors

        Args:
            colors: Dictionary containing custom colors
        """
        if not colors:
            return

        self._custom_colors = colors.copy()
        # 更新配置
        self.config_manager.theme.custom_colors = self._custom_colors
        if self.current_theme == Theme.CUSTOM:
            self.theme_changed.emit(Theme.CUSTOM)

    def get_custom_colors(self) -> Dict[str, str]:
        """Get custom theme colors

        Returns:
            Dictionary containing custom colors
        """
        return self._custom_colors.copy() if self._custom_colors else {}

    def apply_theme(self, widget: QWidget, theme: Optional[Theme] = None) -> None:
        """Apply theme to widget

        Args:
            widget: Widget to apply theme to
            theme: Theme to apply, defaults to current theme
        """
        try:
            if widget is None:
                return

            if theme is None:
                theme = self.current_theme

            # 获取主题颜色
            colors = self.get_theme_colors(theme)

            # 创建调色板
            palette = widget.palette()

            # 设置基本颜色
            palette.setColor(QPalette.Window, QColor(colors['background']))
            palette.setColor(QPalette.WindowText, QColor(colors['text']))
            palette.setColor(QPalette.Base, QColor(colors['background']))
            palette.setColor(QPalette.AlternateBase, QColor(colors['hover']))
            palette.setColor(QPalette.ToolTipBase,
                             QColor(colors['background']))
            palette.setColor(QPalette.ToolTipText, QColor(colors['text']))
            palette.setColor(QPalette.Text, QColor(colors['text']))
            palette.setColor(QPalette.Button, QColor(colors['background']))
            palette.setColor(QPalette.ButtonText, QColor(colors['text']))
            palette.setColor(QPalette.Link, QColor(colors['primary']))
            palette.setColor(QPalette.Highlight, QColor(colors['selected']))
            palette.setColor(QPalette.HighlightedText, QColor(colors['text']))

            # 应用调色板
            widget.setPalette(palette)

            # 设置样式表
            widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                }}
                
                QPushButton {{
                    background-color: {colors['primary']};
                    color: {colors['background']};
                    border: none;
                    padding: 5px;
                    border-radius: 3px;
                }}
                
                QPushButton:hover {{
                    background-color: {colors['hover']};
                }}
                
                QLineEdit {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    padding: 5px;
                    border-radius: 3px;
                }}
                
                QComboBox {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    padding: 5px;
                    border-radius: 3px;
                }}
                
                QComboBox:hover {{
                    border: 1px solid {colors['primary']};
                }}
                
                QComboBox::drop-down {{
                    border: none;
                }}
                
                QComboBox::down-arrow {{
                    image: url(icons/down_arrow.png);
                    width: 12px;
                    height: 12px;
                }}
                
                QScrollBar:vertical {{
                    border: none;
                    background: {colors['background']};
                    width: 10px;
                    margin: 0px 0px 0px 0px;
                }}
                
                QScrollBar::handle:vertical {{
                    background: {colors['border']};
                    min-height: 20px;
                    border-radius: 5px;
                }}
                
                QScrollBar::add-line:vertical {{
                    height: 0px;
                }}
                
                QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                
                QScrollBar:horizontal {{
                    border: none;
                    background: {colors['background']};
                    height: 10px;
                    margin: 0px 0px 0px 0px;
                }}
                
                QScrollBar::handle:horizontal {{
                    background: {colors['border']};
                    min-width: 20px;
                    border-radius: 5px;
                }}
                
                QScrollBar::add-line:horizontal {{
                    width: 0px;
                }}
                
                QScrollBar::sub-line:horizontal {{
                    width: 0px;
                }}
            """)

            # 递归应用主题到子部件
            for child in widget.findChildren(QWidget):
                try:
                    if child is not None and child.parent() is widget:
                        self.apply_theme(child, theme)
                except Exception as e:
                    self.log_manager.error(f"应用主题到子部件失败: {str(e)}")
                    continue

        except Exception as e:
            self.log_manager.error(f"应用主题失败: {str(e)}")
            raise

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
            figure.set_facecolor(colors['chart_background'])

            # Set axes colors
            for ax in figure.get_axes():
                ax.set_facecolor(colors['chart_background'])
                ax.tick_params(colors=colors['chart_text'])
                ax.spines['bottom'].set_color(colors['chart_grid'])
                ax.spines['top'].set_color(colors['chart_grid'])
                ax.spines['right'].set_color(colors['chart_grid'])
                ax.spines['left'].set_color(colors['chart_grid'])
                ax.title.set_color(colors['chart_text'])
                ax.xaxis.label.set_color(colors['chart_text'])
                ax.yaxis.label.set_color(colors['chart_text'])

                # Set grid color
                ax.grid(True, color=colors['chart_grid'], alpha=0.3)

                # Set tick colors
                for tick in ax.get_xticklabels():
                    tick.set_color(colors['chart_text'])
                for tick in ax.get_yticklabels():
                    tick.set_color(colors['chart_text'])

            # Draw figure
            figure.canvas.draw()

        except Exception as e:
            self.log_manager.error(f"应用图表主题失败: {str(e)}")

    def get_color(self, name: str, default: str = None) -> str:
        """Get color by name

        Args:
            name: Color name
            default: Default color if not found

        Returns:
            Color value
        """
        colors = self.get_theme_colors()
        return colors.get(name, default)

    def is_dark_theme(self) -> bool:
        """Check if current theme is dark

        Returns:
            True if current theme is dark
        """
        return self.current_theme in [Theme.DARK]


def get_theme_manager(config_manager: Optional[ConfigManager] = None) -> ThemeManager:
    """Get theme manager instance

    Args:
        config_manager: Optional ConfigManager instance to use

    Returns:
        ThemeManager instance
    """
    global _theme_manager_instance
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager(config_manager)
    return _theme_manager_instance
