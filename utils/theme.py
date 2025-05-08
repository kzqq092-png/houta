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
    """主题管理器类"""

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

        # 加载主题配置
        self._load_theme_config()

        # 初始化主题颜色映射
        self._init_theme_colors()

        # 初始化主题缓存
        self._theme_cache = {}

    def _load_theme_config(self):
        """加载主题配置"""
        try:
            # 从配置管理器获取主题配置
            theme_config = self.config_manager.theme

            # 设置当前主题
            self._current_theme = theme_config.theme

        except Exception as e:
            print(f"加载主题配置失败: {str(e)}")
            # 使用默认主题
            self._current_theme = Theme.LIGHT

    def _init_theme_colors(self):
        """初始化主题颜色映射"""
        # 浅色主题
        self._light_colors = {
            'background': '#ffffff',
            'text': '#000000',
            'border': '#d0d0d0',
            'chart_background': '#ffffff',
            'chart_grid': '#e0e0e0',
            'chart_text': '#333333',
            'k_up': '#e60000',
            'k_down': '#1dbf60',
            'k_edge': '#2c3140',
            'volume_up': '#e60000',
            'volume_down': '#1dbf60',
            'indicator_1': '#1976d2',
            'indicator_2': '#e53935',
            'indicator_3': '#43a047',
            'indicator_4': '#fb8c00',
            'indicator_5': '#8e24aa',
            'highlight': '#1976d2',
            'warning': '#ff9800',
            'ma5': '#fbc02d',
            'ma10': '#ab47bc',
            'ma20': '#1976d2',
            'ma60': '#43a047',
            'macd_dif': '#1976d2',
            'macd_dea': '#e53935',
            'macd_hist_up': '#e60000',
            'macd_hist_down': '#1dbf60',
        }
        # 专业交易软件深色主题
        self._dark_colors = {
            'background': '#181c24',         # 主背景色
            'text': '#b0b8c1',               # 主文字色
            'border': '#2c3140',             # 分割线/边框
            'chart_background': '#181c24',   # 图表背景
            'chart_grid': '#2c3140',         # 网格线
            'chart_text': '#b0b8c1',         # 图表文字
            'k_up': '#e60000',               # K线阳线/上涨
            'k_down': '#1dbf60',             # K线阴线/下跌
            'k_edge': '#ffffff',             # K线边框
            'volume_up': '#e60000',          # 成交量上涨
            'volume_down': '#1dbf60',        # 成交量下跌
            'macd_dif': '#ffff00',           # MACD DIF线
            'macd_dea': '#ff00ff',           # MACD DEA线
            'macd_hist_up': '#e60000',       # MACD柱状图正
            'macd_hist_down': '#00ffff',     # MACD柱状图负
            'highlight': '#1976d2',          # 选中高亮
            'warning': '#ff9800',            # 警告/提示
            'ma5': '#fbc02d',                # MA5 黄色
            'ma10': '#ab47bc',               # MA10 紫色
            'ma20': '#1976d2',               # MA20 蓝色
            'ma60': '#43a047',               # MA60 绿色
            'indicator_1': '#42a5f5',
            'indicator_2': '#ef5350',
            'indicator_3': '#66bb6a',
            'indicator_4': '#ffa726',
            'indicator_5': '#ab47bc',
        }

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

    def get_theme_colors(self, theme: Optional[Theme] = None) -> Dict[str, str]:
        """获取主题颜色

        Args:
            theme: 可选的主题，默认使用当前主题

        Returns:
            主题颜色字典
        """
        theme = theme or self._current_theme

        # 检查缓存
        if theme in self._theme_cache:
            return self._theme_cache[theme].copy()

        # 获取颜色
        colors = self._light_colors.copy() if theme == Theme.LIGHT else self._dark_colors.copy()

        # 缓存结果
        self._theme_cache[theme] = colors.copy()

        return colors

    def get_widget_style(self, theme: Optional[Theme] = None) -> str:
        """获取部件样式

        Args:
            theme: 可选的主题，默认使用当前主题

        Returns:
            样式表字符串
        """
        theme = theme or self._current_theme
        colors = self.get_theme_colors(theme)

        return f"""
            QWidget {{
                background-color: {colors['background']};
                color: {colors['text']};
            }}
            
            QGroupBox {{
                border: 1px solid {colors['border']};
                border-radius: 6px;
                margin-top: 6px;
                padding: 6px;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 7px;
                padding: 0px 5px 0px 5px;
            }}
            
            QPushButton {{
                background-color: {colors['background']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QPushButton:hover {{
                background-color: {colors['chart_grid']};
            }}
            
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {colors['background']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 2px;
            }}
            
            QComboBox {{
                background-color: {colors['background']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 2px;
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox::down-arrow {{
                image: url(icons/down_arrow_{theme.name.lower()}.png);
                width: 12px;
                height: 12px;
            }}
            
            QScrollBar:vertical {{
                border: none;
                background: {colors['background']};
                width: 10px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background: {colors['border']};
                min-height: 20px;
                border-radius: 5px;
            }}
            
            QScrollBar::add-line:vertical {{
                border: none;
                background: none;
            }}
            
            QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """

    def apply_theme(self, widget: QWidget, theme: Optional[Theme] = None) -> None:
        """应用主题到指定部件

        Args:
            widget: 要应用主题的部件
            theme: 可选的主题，默认使用当前主题
        """
        try:
            # 获取样式表
            style_sheet = self.get_widget_style(theme)

            # 应用样式表
            widget.setStyleSheet(style_sheet)

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
            print(f"应用图表主题失败: {str(e)}")

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
        return self.current_theme in [Theme.DEEPBLUE]


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
