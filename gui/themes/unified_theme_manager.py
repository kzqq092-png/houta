"""
统一主题管理系统
建立统一的主题切换和管理机制，支持深色/浅色主题和自定义主题
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QObject, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QPalette, QColor
import threading

logger = logging.getLogger(__name__)

class ThemeType(Enum):
    """主题类型枚举"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"
    HIGH_CONTRAST = "high_contrast"

class ThemeCategory(Enum):
    """主题分类枚举"""
    SYSTEM = "system"
    PROFESSIONAL = "professional"
    CREATIVE = "creative"
    ACCESSIBILITY = "accessibility"
    USER_DEFINED = "user_defined"

@dataclass
class ThemeColors:
    """主题颜色配置数据类"""
    # 主色调
    primary: str = "#2196F3"
    primary_light: str = "#64B5F6"
    primary_dark: str = "#1976D2"
    
    # 辅助色
    secondary: str = "#FF9800"
    secondary_light: str = "#FFB74D"
    secondary_dark: str = "#F57C00"
    
    # 状态色
    success: str = "#4CAF50"
    warning: str = "#FFC107"
    error: str = "#F44336"
    info: str = "#03A9F4"
    
    # 背景色
    background_primary: str = "#FFFFFF"
    background_secondary: str = "#F5F5F5"
    background_tertiary: str = "#EEEEEE"
    
    # 表面色
    surface_primary: str = "#FFFFFF"
    surface_secondary: str = "#FAFAFA"
    surface_tertiary: str = "#F0F0F0"
    
    # 文本色
    text_primary: str = "#212121"
    text_secondary: str = "#757575"
    text_disabled: str = "#BDBDBD"
    text_hint: str = "#9E9E9E"
    
    # 边框色
    border_primary: str = "#E0E0E0"
    border_secondary: str = "#BDBDBD"
    border_focus: str = "#2196F3"
    
    # 阴影色
    shadow_light: str = "rgba(0, 0, 0, 0.12)"
    shadow_medium: str = "rgba(0, 0, 0, 0.16)"
    shadow_heavy: str = "rgba(0, 0, 0, 0.24)"
    
    # 覆盖层
    overlay_light: str = "rgba(255, 255, 255, 0.8)"
    overlay_dark: str = "rgba(0, 0, 0, 0.5)"

@dataclass
class DarkThemeColors(ThemeColors):
    """深色主题颜色配置"""
    # 重写深色主题的颜色
    background_primary: str = "#121212"
    background_secondary: str = "#1E1E1E"
    background_tertiary: str = "#2C2C2C"
    
    surface_primary: str = "#1E1E1E"
    surface_secondary: str = "#2C2C2C"
    surface_tertiary: str = "#383838"
    
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#B0B0B0"
    text_disabled: str = "#6C6C6C"
    text_hint: str = "#8C8C8C"
    
    border_primary: str = "#383838"
    border_secondary: str = "#4C4C4C"
    
    shadow_light: str = "rgba(0, 0, 0, 0.3)"
    shadow_medium: str = "rgba(0, 0, 0, 0.4)"
    shadow_heavy: str = "rgba(0, 0, 0, 0.6)"
    
    overlay_light: str = "rgba(255, 255, 255, 0.1)"
    overlay_dark: str = "rgba(0, 0, 0, 0.7)"

@dataclass
class HighContrastThemeColors(ThemeColors):
    """高对比度主题颜色配置"""
    # 高对比度颜色
    primary: str = "#000000"
    secondary: str = "#FFFFFF"
    
    background_primary: str = "#FFFFFF"
    background_secondary: str = "#FFFFFF"
    background_tertiary: str = "#FFFFFF"
    
    surface_primary: str = "#FFFFFF"
    surface_secondary: str = "#FFFFFF"
    surface_tertiary: str = "#FFFFFF"
    
    text_primary: str = "#000000"
    text_secondary: str = "#000000"
    text_disabled: str = "#666666"
    text_hint: str = "#333333"
    
    border_primary: str = "#000000"
    border_secondary: str = "#000000"
    border_focus: str = "#000000"
    
    success: str = "#008000"
    warning: str = "#FF8000"
    error: str = "#FF0000"
    info: str = "#0000FF"

@dataclass
class ThemeTypography:
    """主题字体配置数据类"""
    font_family_primary: str = "Microsoft YaHei UI"
    font_family_secondary: str = "Arial, sans-serif"
    font_family_monospace: str = "Consolas, Monaco, monospace"
    
    font_size_xs: int = 10
    font_size_sm: int = 12
    font_size_md: int = 14
    font_size_lg: int = 16
    font_size_xl: int = 18
    font_size_xxl: int = 20
    
    font_weight_light: int = 300
    font_weight_normal: int = 400
    font_weight_medium: int = 500
    font_weight_semibold: int = 600
    font_weight_bold: int = 700
    
    line_height_tight: float = 1.2
    line_height_normal: float = 1.4
    line_height_relaxed: float = 1.6

@dataclass
class ThemeSpacing:
    """主题间距配置数据类"""
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48
    
    padding_xs: int = 4
    padding_sm: int = 8
    padding_md: int = 12
    padding_lg: int = 16
    padding_xl: int = 20
    
    margin_xs: int = 4
    margin_sm: int = 8
    margin_md: int = 16
    margin_lg: int = 24
    margin_xl: int = 32

@dataclass
class ThemeEffects:
    """主题效果配置数据类"""
    border_radius_xs: int = 2
    border_radius_sm: int = 4
    border_radius_md: int = 6
    border_radius_lg: int = 8
    border_radius_xl: int = 12
    border_radius_full: str = "50%"
    
    shadow_xs: str = "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
    shadow_sm: str = "0 1px 3px 0 rgba(0, 0, 0, 0.1)"
    shadow_md: str = "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
    shadow_lg: str = "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
    shadow_xl: str = "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
    
    transition_fast: str = "150ms ease"
    transition_normal: str = "300ms ease"
    transition_slow: str = "500ms ease"
    
    opacity_disabled: float = 0.6
    opacity_hover: float = 0.8
    opacity_pressed: float = 0.9

@dataclass
class ThemeConfig:
    """主题配置数据类"""
    name: str
    display_name: str
    theme_type: ThemeType
    category: ThemeCategory
    colors: ThemeColors
    typography: ThemeTypography = field(default_factory=ThemeTypography)
    spacing: ThemeSpacing = field(default_factory=ThemeSpacing)
    effects: ThemeEffects = field(default_factory=ThemeEffects)
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ThemeRegistry:
    """主题注册表"""
    
    def __init__(self):
        self.themes: Dict[str, ThemeConfig] = {}
        self.lock = threading.Lock()
        self._register_builtin_themes()
    
    def _register_builtin_themes(self):
        """注册内置主题"""
        # 浅色主题
        light_theme = ThemeConfig(
            name="light",
            display_name="浅色主题",
            theme_type=ThemeType.LIGHT,
            category=ThemeCategory.SYSTEM,
            colors=ThemeColors(),
            description="默认浅色主题，适合日间使用"
        )
        
        # 深色主题
        dark_theme = ThemeConfig(
            name="dark",
            display_name="深色主题",
            theme_type=ThemeType.DARK,
            category=ThemeCategory.SYSTEM,
            colors=DarkThemeColors(),
            description="深色主题，适合夜间使用，减少眼部疲劳"
        )
        
        # 高对比度主题
        high_contrast_theme = ThemeConfig(
            name="high_contrast",
            display_name="高对比度主题",
            theme_type=ThemeType.HIGH_CONTRAST,
            category=ThemeCategory.ACCESSIBILITY,
            colors=HighContrastThemeColors(),
            description="高对比度主题，提高可访问性"
        )
        
        # 专业蓝色主题
        professional_blue = ThemeConfig(
            name="professional_blue",
            display_name="专业蓝色",
            theme_type=ThemeType.CUSTOM,
            category=ThemeCategory.PROFESSIONAL,
            colors=ThemeColors(
                primary="#1565C0",
                primary_light="#42A5F5",
                primary_dark="#0D47A1",
                secondary="#37474F",
                background_secondary="#F8F9FA"
            ),
            description="专业的蓝色主题，适合商务场景"
        )
        
        # 创意绿色主题
        creative_green = ThemeConfig(
            name="creative_green",
            display_name="创意绿色",
            theme_type=ThemeType.CUSTOM,
            category=ThemeCategory.CREATIVE,
            colors=ThemeColors(
                primary="#2E7D32",
                primary_light="#66BB6A",
                primary_dark="#1B5E20",
                secondary="#FF6F00",
                background_secondary="#F1F8E9"
            ),
            description="充满活力的绿色主题，激发创造力"
        )
        
        # 注册主题
        for theme in [light_theme, dark_theme, high_contrast_theme, professional_blue, creative_green]:
            self.register_theme(theme)
    
    def register_theme(self, theme_config: ThemeConfig) -> bool:
        """注册主题"""
        try:
            with self.lock:
                self.themes[theme_config.name] = theme_config
                logger.debug(f"主题已注册: {theme_config.name}")
                return True
                
        except Exception as e:
            logger.error(f"注册主题失败: {e}")
            return False
    
    def unregister_theme(self, theme_name: str) -> bool:
        """注销主题"""
        try:
            with self.lock:
                if theme_name in self.themes:
                    # 不允许删除系统主题
                    theme = self.themes[theme_name]
                    if theme.category == ThemeCategory.SYSTEM:
                        logger.warning(f"不能删除系统主题: {theme_name}")
                        return False
                    
                    del self.themes[theme_name]
                    logger.debug(f"主题已注销: {theme_name}")
                    return True
                else:
                    logger.warning(f"主题不存在: {theme_name}")
                    return False
                    
        except Exception as e:
            logger.error(f"注销主题失败: {e}")
            return False
    
    def get_theme(self, theme_name: str) -> Optional[ThemeConfig]:
        """获取主题配置"""
        with self.lock:
            return self.themes.get(theme_name)
    
    def get_all_themes(self) -> Dict[str, ThemeConfig]:
        """获取所有主题"""
        with self.lock:
            return self.themes.copy()
    
    def get_themes_by_category(self, category: ThemeCategory) -> List[ThemeConfig]:
        """按分类获取主题"""
        with self.lock:
            return [theme for theme in self.themes.values() if theme.category == category]
    
    def get_themes_by_type(self, theme_type: ThemeType) -> List[ThemeConfig]:
        """按类型获取主题"""
        with self.lock:
            return [theme for theme in self.themes.values() if theme.theme_type == theme_type]

class ThemeStylesheetGenerator:
    """主题样式表生成器"""
    
    def __init__(self):
        self.template_cache: Dict[str, str] = {}
    
    def generate_stylesheet(self, theme_config: ThemeConfig) -> str:
        """生成主题样式表"""
        try:
            colors = theme_config.colors
            typography = theme_config.typography
            spacing = theme_config.spacing
            effects = theme_config.effects
            
            stylesheet = f"""
            /* 全局样式 - {theme_config.display_name} */
            * {{
                font-family: {typography.font_family_primary};
            }}
            
            QWidget {{
                background-color: {colors.background_primary};
                color: {colors.text_primary};
                font-size: {typography.font_size_md}px;
            }}
            
            /* 主窗口 */
            QMainWindow {{
                background-color: {colors.background_primary};
            }}
            
            /* 按钮样式 */
            QPushButton {{
                background-color: {colors.primary};
                color: white;
                border: none;
                border-radius: {effects.border_radius_md}px;
                padding: {spacing.padding_sm}px {spacing.padding_md}px;
                font-size: {typography.font_size_md}px;
                font-weight: {typography.font_weight_medium};
                min-height: 32px;
            }}
            
            QPushButton:hover {{
                background-color: {colors.primary_light};
                opacity: {effects.opacity_hover};
            }}
            
            QPushButton:pressed {{
                background-color: {colors.primary_dark};
                opacity: {effects.opacity_pressed};
            }}
            
            QPushButton:disabled {{
                background-color: {colors.text_disabled};
                opacity: {effects.opacity_disabled};
            }}
            
            /* 次要按钮 */
            QPushButton[class="secondary"] {{
                background-color: {colors.secondary};
                color: white;
            }}
            
            QPushButton[class="secondary"]:hover {{
                background-color: {colors.secondary_light};
            }}
            
            QPushButton[class="secondary"]:pressed {{
                background-color: {colors.secondary_dark};
            }}
            
            /* 轮廓按钮 */
            QPushButton[class="outline"] {{
                background-color: transparent;
                color: {colors.primary};
                border: 1px solid {colors.primary};
            }}
            
            QPushButton[class="outline"]:hover {{
                background-color: {colors.primary};
                color: white;
            }}
            
            /* 输入框样式 */
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {colors.surface_primary};
                color: {colors.text_primary};
                border: 1px solid {colors.border_primary};
                border-radius: {effects.border_radius_sm}px;
                padding: {spacing.padding_sm}px {spacing.padding_md}px;
                font-size: {typography.font_size_md}px;
                min-height: 32px;
            }}
            
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {colors.border_focus};
                outline: none;
            }}
            
            QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
                background-color: {colors.background_tertiary};
                color: {colors.text_disabled};
                border-color: {colors.border_secondary};
            }}
            
            /* 标签页样式 */
            QTabWidget::pane {{
                border: 1px solid {colors.border_primary};
                border-radius: {effects.border_radius_md}px;
                background-color: {colors.surface_primary};
                padding: {spacing.padding_md}px;
            }}
            
            QTabBar::tab {{
                background-color: {colors.background_secondary};
                color: {colors.text_secondary};
                border: 1px solid {colors.border_primary};
                border-bottom: none;
                border-radius: {effects.border_radius_sm}px {effects.border_radius_sm}px 0 0;
                padding: {spacing.padding_sm}px {spacing.padding_lg}px;
                margin-right: 2px;
                font-size: {typography.font_size_md}px;
                font-weight: {typography.font_weight_medium};
                min-height: 32px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {colors.surface_primary};
                color: {colors.text_primary};
                border-bottom: 2px solid {colors.primary};
            }}
            
            QTabBar::tab:hover {{
                background-color: {colors.surface_secondary};
                color: {colors.primary};
            }}
            
            /* 表格样式 */
            QTableWidget {{
                background-color: {colors.surface_primary};
                alternate-background-color: {colors.background_secondary};
                gridline-color: {colors.border_primary};
                border: 1px solid {colors.border_primary};
                border-radius: {effects.border_radius_md}px;
                font-size: {typography.font_size_md}px;
            }}
            
            QTableWidget::item {{
                padding: {spacing.padding_sm}px {spacing.padding_md}px;
                border: none;
            }}
            
            QTableWidget::item:selected {{
                background-color: {colors.primary};
                color: white;
            }}
            
            QHeaderView::section {{
                background-color: {colors.background_secondary};
                color: {colors.text_primary};
                padding: {spacing.padding_sm}px {spacing.padding_md}px;
                border: none;
                border-bottom: 2px solid {colors.border_secondary};
                font-weight: {typography.font_weight_semibold};
            }}
            
            /* 进度条样式 */
            QProgressBar {{
                background-color: {colors.background_secondary};
                border: 1px solid {colors.border_primary};
                border-radius: {effects.border_radius_sm}px;
                text-align: center;
                font-size: {typography.font_size_sm}px;
                font-weight: {typography.font_weight_medium};
            }}
            
            QProgressBar::chunk {{
                background-color: {colors.primary};
                border-radius: {effects.border_radius_sm}px;
            }}
            
            /* 分组框样式 */
            QGroupBox {{
                font-weight: {typography.font_weight_semibold};
                border: 1px solid {colors.border_secondary};
                border-radius: {effects.border_radius_md}px;
                margin-top: {spacing.margin_md}px;
                padding-top: {spacing.padding_md}px;
                color: {colors.text_primary};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {spacing.margin_lg}px;
                padding: 0 {spacing.padding_sm}px;
                color: {colors.text_primary};
            }}
            
            /* 滚动条样式 */
            QScrollBar:vertical {{
                background-color: {colors.background_secondary};
                width: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {colors.border_secondary};
                border-radius: 6px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {colors.text_secondary};
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            
            /* 工具提示样式 */
            QToolTip {{
                background-color: {colors.text_primary};
                color: {colors.background_primary};
                border: none;
                border-radius: {effects.border_radius_sm}px;
                padding: {spacing.padding_xs}px {spacing.padding_sm}px;
                font-size: {typography.font_size_sm}px;
            }}
            
            /* 菜单样式 */
            QMenu {{
                background-color: {colors.surface_primary};
                border: 1px solid {colors.border_primary};
                border-radius: {effects.border_radius_md}px;
                padding: {spacing.padding_xs}px;
            }}
            
            QMenu::item {{
                padding: {spacing.padding_sm}px {spacing.padding_md}px;
                border-radius: {effects.border_radius_sm}px;
                color: {colors.text_primary};
            }}
            
            QMenu::item:selected {{
                background-color: {colors.primary};
                color: white;
            }}
            
            /* 状态栏样式 */
            QStatusBar {{
                background-color: {colors.background_secondary};
                border-top: 1px solid {colors.border_primary};
                padding: {spacing.padding_xs}px {spacing.padding_md}px;
                color: {colors.text_secondary};
            }}
            
            /* 分割器样式 */
            QSplitter::handle {{
                background-color: {colors.border_primary};
            }}
            
            QSplitter::handle:horizontal {{
                width: 2px;
            }}
            
            QSplitter::handle:vertical {{
                height: 2px;
            }}
            
            /* 状态指示器 */
            .status-success {{
                color: {colors.success};
            }}
            
            .status-warning {{
                color: {colors.warning};
            }}
            
            .status-error {{
                color: {colors.error};
            }}
            
            .status-info {{
                color: {colors.info};
            }}
            """
            
            return stylesheet
            
        except Exception as e:
            logger.error(f"生成主题样式表失败: {e}")
            return ""
    
    def generate_component_stylesheet(self, theme_config: ThemeConfig, component_type: str) -> str:
        """生成特定组件的样式表"""
        try:
            colors = theme_config.colors
            
            if component_type == "button":
                return f"""
                QPushButton {{
                    background-color: {colors.primary};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {colors.primary_light};
                }}
                """
            elif component_type == "input":
                return f"""
                QLineEdit {{
                    background-color: {colors.surface_primary};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border_primary};
                    border-radius: 4px;
                    padding: 8px 12px;
                }}
                QLineEdit:focus {{
                    border-color: {colors.border_focus};
                }}
                """
            else:
                return ""
                
        except Exception as e:
            logger.error(f"生成组件样式表失败: {e}")
            return ""

class ThemePersistence:
    """主题持久化管理"""
    
    def __init__(self, themes_dir: str = "themes"):
        self.themes_dir = themes_dir
        self.settings = QSettings("HikyuuUI", "ThemeManager")
        self._ensure_themes_directory()
    
    def _ensure_themes_directory(self):
        """确保主题目录存在"""
        try:
            if not os.path.exists(self.themes_dir):
                os.makedirs(self.themes_dir)
        except Exception as e:
            logger.error(f"创建主题目录失败: {e}")
    
    def save_theme(self, theme_config: ThemeConfig) -> bool:
        """保存主题到文件"""
        try:
            theme_file = os.path.join(self.themes_dir, f"{theme_config.name}.json")
            
            # 转换为字典
            theme_dict = asdict(theme_config)
            
            # 处理datetime对象
            theme_dict['created_at'] = theme_config.created_at.isoformat()
            theme_dict['updated_at'] = theme_config.updated_at.isoformat()
            theme_dict['theme_type'] = theme_config.theme_type.value
            theme_dict['category'] = theme_config.category.value
            
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme_dict, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"主题已保存: {theme_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存主题失败: {e}")
            return False
    
    def load_theme(self, theme_name: str) -> Optional[ThemeConfig]:
        """从文件加载主题"""
        try:
            theme_file = os.path.join(self.themes_dir, f"{theme_name}.json")
            
            if not os.path.exists(theme_file):
                return None
            
            with open(theme_file, 'r', encoding='utf-8') as f:
                theme_dict = json.load(f)
            
            # 处理枚举类型
            theme_dict['theme_type'] = ThemeType(theme_dict['theme_type'])
            theme_dict['category'] = ThemeCategory(theme_dict['category'])
            
            # 处理datetime对象
            theme_dict['created_at'] = datetime.fromisoformat(theme_dict['created_at'])
            theme_dict['updated_at'] = datetime.fromisoformat(theme_dict['updated_at'])
            
            # 重建嵌套对象
            colors_dict = theme_dict.pop('colors')
            typography_dict = theme_dict.pop('typography')
            spacing_dict = theme_dict.pop('spacing')
            effects_dict = theme_dict.pop('effects')
            
            theme_config = ThemeConfig(
                colors=ThemeColors(**colors_dict),
                typography=ThemeTypography(**typography_dict),
                spacing=ThemeSpacing(**spacing_dict),
                effects=ThemeEffects(**effects_dict),
                **theme_dict
            )
            
            logger.debug(f"主题已加载: {theme_file}")
            return theme_config
            
        except Exception as e:
            logger.error(f"加载主题失败: {e}")
            return None
    
    def load_all_themes(self) -> List[ThemeConfig]:
        """加载所有主题文件"""
        themes = []
        try:
            if not os.path.exists(self.themes_dir):
                return themes
            
            for filename in os.listdir(self.themes_dir):
                if filename.endswith('.json'):
                    theme_name = filename[:-5]  # 移除.json后缀
                    theme_config = self.load_theme(theme_name)
                    if theme_config:
                        themes.append(theme_config)
            
            logger.debug(f"已加载 {len(themes)} 个主题文件")
            
        except Exception as e:
            logger.error(f"加载主题文件失败: {e}")
        
        return themes
    
    def delete_theme(self, theme_name: str) -> bool:
        """删除主题文件"""
        try:
            theme_file = os.path.join(self.themes_dir, f"{theme_name}.json")
            
            if os.path.exists(theme_file):
                os.remove(theme_file)
                logger.debug(f"主题文件已删除: {theme_file}")
                return True
            else:
                logger.warning(f"主题文件不存在: {theme_file}")
                return False
                
        except Exception as e:
            logger.error(f"删除主题文件失败: {e}")
            return False
    
    def save_current_theme(self, theme_name: str):
        """保存当前主题设置"""
        self.settings.setValue("current_theme", theme_name)
    
    def get_current_theme(self) -> str:
        """获取当前主题设置"""
        return self.settings.value("current_theme", "light")
    
    def save_theme_preferences(self, preferences: Dict[str, Any]):
        """保存主题偏好设置"""
        for key, value in preferences.items():
            self.settings.setValue(f"theme_pref_{key}", value)
    
    def get_theme_preferences(self) -> Dict[str, Any]:
        """获取主题偏好设置"""
        preferences = {}
        self.settings.beginGroup("theme_pref")
        for key in self.settings.allKeys():
            preferences[key] = self.settings.value(key)
        self.settings.endGroup()
        return preferences

class UnifiedThemeManager(QObject):
    """统一主题管理器主类"""
    
    # 信号定义
    theme_changed = pyqtSignal(str)  # theme_name
    theme_registered = pyqtSignal(str)  # theme_name
    theme_unregistered = pyqtSignal(str)  # theme_name
    
    def __init__(self):
        super().__init__()
        
        # 核心组件
        self.registry = ThemeRegistry()
        self.stylesheet_generator = ThemeStylesheetGenerator()
        self.persistence = ThemePersistence()
        
        # 状态管理
        self.current_theme_name = "light"
        self.current_theme_config: Optional[ThemeConfig] = None
        self.current_stylesheet = ""
        
        # 应用程序引用
        self.application: Optional[QApplication] = None
        self.managed_widgets: List[QWidget] = []
        
        # 主题切换回调
        self.theme_callbacks: List[Callable] = []
        
        # 自动主题检测
        self.auto_theme_timer = QTimer()
        self.auto_theme_timer.timeout.connect(self._check_system_theme)
        
        # 加载用户自定义主题
        self._load_user_themes()
        
        # 设置初始主题
        self._initialize_theme()
        
        logger.info("统一主题管理器已初始化")
    
    def _load_user_themes(self):
        """加载用户自定义主题"""
        try:
            user_themes = self.persistence.load_all_themes()
            for theme_config in user_themes:
                self.registry.register_theme(theme_config)
            
            logger.debug(f"已加载 {len(user_themes)} 个用户主题")
            
        except Exception as e:
            logger.error(f"加载用户主题失败: {e}")
    
    def _initialize_theme(self):
        """初始化主题"""
        try:
            # 获取上次使用的主题
            saved_theme = self.persistence.get_current_theme()
            
            # 应用主题
            if self.set_theme(saved_theme):
                logger.info(f"已恢复上次使用的主题: {saved_theme}")
            else:
                # 回退到默认主题
                self.set_theme("light")
                logger.info("已应用默认主题")
                
        except Exception as e:
            logger.error(f"初始化主题失败: {e}")
    
    def _check_system_theme(self):
        """检查系统主题变化（用于自动主题）"""
        try:
            if self.current_theme_name == "auto":
                # 这里可以实现系统主题检测逻辑
                # 例如检查Windows的深色模式设置
                pass
                
        except Exception as e:
            logger.error(f"检查系统主题失败: {e}")
    
    def set_application(self, app: QApplication):
        """设置应用程序引用"""
        self.application = app
        if self.current_stylesheet:
            app.setStyleSheet(self.current_stylesheet)
    
    def register_widget(self, widget: QWidget):
        """注册需要管理的组件"""
        if widget not in self.managed_widgets:
            self.managed_widgets.append(widget)
            if self.current_stylesheet:
                widget.setStyleSheet(self.current_stylesheet)
    
    def unregister_widget(self, widget: QWidget):
        """注销组件管理"""
        if widget in self.managed_widgets:
            self.managed_widgets.remove(widget)
    
    def add_theme_callback(self, callback: Callable[[str, ThemeConfig], None]):
        """添加主题切换回调"""
        self.theme_callbacks.append(callback)
    
    def register_theme(self, theme_config: ThemeConfig, save_to_file: bool = True) -> bool:
        """注册新主题"""
        try:
            # 注册到注册表
            if not self.registry.register_theme(theme_config):
                return False
            
            # 保存到文件
            if save_to_file and theme_config.category == ThemeCategory.USER_DEFINED:
                self.persistence.save_theme(theme_config)
            
            # 发送信号
            self.theme_registered.emit(theme_config.name)
            
            logger.info(f"主题已注册: {theme_config.name}")
            return True
            
        except Exception as e:
            logger.error(f"注册主题失败: {e}")
            return False
    
    def unregister_theme(self, theme_name: str, delete_file: bool = True) -> bool:
        """注销主题"""
        try:
            theme_config = self.registry.get_theme(theme_name)
            if not theme_config:
                return False
            
            # 注销主题
            if not self.registry.unregister_theme(theme_name):
                return False
            
            # 删除文件
            if delete_file and theme_config.category == ThemeCategory.USER_DEFINED:
                self.persistence.delete_theme(theme_name)
            
            # 如果是当前主题，切换到默认主题
            if self.current_theme_name == theme_name:
                self.set_theme("light")
            
            # 发送信号
            self.theme_unregistered.emit(theme_name)
            
            logger.info(f"主题已注销: {theme_name}")
            return True
            
        except Exception as e:
            logger.error(f"注销主题失败: {e}")
            return False
    
    def set_theme(self, theme_name: str) -> bool:
        """设置当前主题"""
        try:
            # 获取主题配置
            theme_config = self.registry.get_theme(theme_name)
            if not theme_config:
                logger.warning(f"主题不存在: {theme_name}")
                return False
            
            # 生成样式表
            stylesheet = self.stylesheet_generator.generate_stylesheet(theme_config)
            if not stylesheet:
                logger.error(f"生成主题样式表失败: {theme_name}")
                return False
            
            # 更新状态
            self.current_theme_name = theme_name
            self.current_theme_config = theme_config
            self.current_stylesheet = stylesheet
            
            # 应用样式
            self._apply_stylesheet()
            
            # 保存设置
            self.persistence.save_current_theme(theme_name)
            
            # 触发回调
            for callback in self.theme_callbacks:
                try:
                    callback(theme_name, theme_config)
                except Exception as e:
                    logger.error(f"主题回调执行失败: {e}")
            
            # 启动/停止自动主题检测
            if theme_name == "auto":
                self.auto_theme_timer.start(30000)  # 30秒检查一次
            else:
                self.auto_theme_timer.stop()
            
            # 发送信号
            self.theme_changed.emit(theme_name)
            
            logger.info(f"主题已切换: {theme_name}")
            return True
            
        except Exception as e:
            logger.error(f"设置主题失败: {e}")
            return False
    
    def _apply_stylesheet(self):
        """应用样式表"""
        try:
            # 应用到应用程序
            if self.application:
                self.application.setStyleSheet(self.current_stylesheet)
            
            # 应用到管理的组件
            for widget in self.managed_widgets:
                try:
                    widget.setStyleSheet(self.current_stylesheet)
                except Exception as e:
                    logger.error(f"应用组件样式失败: {e}")
            
        except Exception as e:
            logger.error(f"应用样式表失败: {e}")
    
    def get_current_theme(self) -> Optional[ThemeConfig]:
        """获取当前主题配置"""
        return self.current_theme_config
    
    def get_current_theme_name(self) -> str:
        """获取当前主题名称"""
        return self.current_theme_name
    
    def get_available_themes(self) -> Dict[str, ThemeConfig]:
        """获取可用主题列表"""
        return self.registry.get_all_themes()
    
    def get_themes_by_category(self, category: ThemeCategory) -> List[ThemeConfig]:
        """按分类获取主题"""
        return self.registry.get_themes_by_category(category)
    
    def create_custom_theme(self, name: str, display_name: str, base_theme: str = "light", 
                          color_overrides: Dict[str, str] = None) -> Optional[ThemeConfig]:
        """创建自定义主题"""
        try:
            # 获取基础主题
            base_config = self.registry.get_theme(base_theme)
            if not base_config:
                logger.error(f"基础主题不存在: {base_theme}")
                return None
            
            # 复制基础配置
            colors_dict = asdict(base_config.colors)
            
            # 应用颜色覆盖
            if color_overrides:
                colors_dict.update(color_overrides)
            
            # 创建新主题配置
            custom_theme = ThemeConfig(
                name=name,
                display_name=display_name,
                theme_type=ThemeType.CUSTOM,
                category=ThemeCategory.USER_DEFINED,
                colors=ThemeColors(**colors_dict),
                typography=base_config.typography,
                spacing=base_config.spacing,
                effects=base_config.effects,
                description=f"基于 {base_config.display_name} 的自定义主题",
                author="用户自定义"
            )
            
            # 注册主题
            if self.register_theme(custom_theme):
                logger.info(f"自定义主题已创建: {name}")
                return custom_theme
            else:
                return None
                
        except Exception as e:
            logger.error(f"创建自定义主题失败: {e}")
            return None
    
    def export_theme(self, theme_name: str, file_path: str) -> bool:
        """导出主题到文件"""
        try:
            theme_config = self.registry.get_theme(theme_name)
            if not theme_config:
                return False
            
            # 保存到指定文件
            theme_dict = asdict(theme_config)
            theme_dict['created_at'] = theme_config.created_at.isoformat()
            theme_dict['updated_at'] = theme_config.updated_at.isoformat()
            theme_dict['theme_type'] = theme_config.theme_type.value
            theme_dict['category'] = theme_config.category.value
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(theme_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"主题已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出主题失败: {e}")
            return False
    
    def import_theme(self, file_path: str) -> Optional[ThemeConfig]:
        """从文件导入主题"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"主题文件不存在: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_dict = json.load(f)
            
            # 处理枚举和日期
            theme_dict['theme_type'] = ThemeType(theme_dict['theme_type'])
            theme_dict['category'] = ThemeCategory(theme_dict['category'])
            theme_dict['created_at'] = datetime.fromisoformat(theme_dict['created_at'])
            theme_dict['updated_at'] = datetime.fromisoformat(theme_dict['updated_at'])
            
            # 重建对象
            colors_dict = theme_dict.pop('colors')
            typography_dict = theme_dict.pop('typography')
            spacing_dict = theme_dict.pop('spacing')
            effects_dict = theme_dict.pop('effects')
            
            theme_config = ThemeConfig(
                colors=ThemeColors(**colors_dict),
                typography=ThemeTypography(**typography_dict),
                spacing=ThemeSpacing(**spacing_dict),
                effects=ThemeEffects(**effects_dict),
                **theme_dict
            )
            
            # 注册主题
            if self.register_theme(theme_config):
                logger.info(f"主题已导入: {theme_config.name}")
                return theme_config
            else:
                return None
                
        except Exception as e:
            logger.error(f"导入主题失败: {e}")
            return None
    
    def get_theme_preview(self, theme_name: str) -> str:
        """获取主题预览样式"""
        theme_config = self.registry.get_theme(theme_name)
        if not theme_config:
            return ""
        
        return self.stylesheet_generator.generate_component_stylesheet(theme_config, "button")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        try:
            return {
                'current_theme': self.current_theme_name,
                'total_themes': len(self.registry.themes),
                'managed_widgets': len(self.managed_widgets),
                'auto_theme_active': self.auto_theme_timer.isActive(),
                'theme_categories': {
                    category.value: len(self.get_themes_by_category(category))
                    for category in ThemeCategory
                },
                'has_application': self.application is not None,
                'stylesheet_length': len(self.current_stylesheet),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取管理器状态失败: {e}")
            return {'error': str(e)}

# 全局实例
unified_theme_manager = UnifiedThemeManager()

def get_unified_theme_manager() -> UnifiedThemeManager:
    """获取统一主题管理器实例"""
    return unified_theme_manager

def apply_theme(app: QApplication, theme_name: str = "light"):
    """应用主题到应用程序"""
    manager = get_unified_theme_manager()
    manager.set_application(app)
    manager.set_theme(theme_name)
