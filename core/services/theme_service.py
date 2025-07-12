"""
主题服务模块

负责应用主题的管理和切换。
"""

import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from .base_service import ConfigurableService
from ..events import ThemeChangedEvent


logger = logging.getLogger(__name__)


class ThemeService(ConfigurableService):
    """
    主题服务

    负责应用主题的管理和切换。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        初始化主题服务

        Args:
            config: 服务配置
            **kwargs: 其他参数
        """
        super().__init__(config=config, **kwargs)
        self._current_theme = 'default'
        self._themes = {}
        self._theme_files_path = None

    def _do_initialize(self) -> None:
        """初始化主题服务"""
        try:
            # 设置主题文件路径
            self._theme_files_path = Path(
                self.get_config_value('theme_files_path', 'themes'))

            # 加载内置主题
            self._load_builtin_themes()

            # 加载外部主题文件
            self._load_external_themes()

            # 设置当前主题
            self._current_theme = self.get_config_value(
                'current_theme', 'default')

            if self._current_theme not in self._themes:
                logger.warning(
                    f"Theme '{self._current_theme}' not found, using default")
                self._current_theme = 'default'

            logger.info(
                f"Theme service initialized with theme: {self._current_theme}")

        except Exception as e:
            logger.error(f"Failed to initialize theme service: {e}")
            raise

    def get_current_theme(self) -> str:
        """
        获取当前主题名称

        Returns:
            当前主题名称
        """
        self._ensure_initialized()
        return self._current_theme

    def get_theme_config(self, theme_name: str = None) -> Optional[Dict[str, Any]]:
        """
        获取主题配置

        Args:
            theme_name: 主题名称，如果为None则获取当前主题

        Returns:
            主题配置
        """
        self._ensure_initialized()

        theme_name = theme_name or self._current_theme
        return self._themes.get(theme_name)

    def set_theme(self, theme_name: str) -> bool:
        """
        设置主题

        Args:
            theme_name: 主题名称

        Returns:
            是否成功设置
        """
        self._ensure_initialized()

        if theme_name not in self._themes:
            logger.warning(f"Theme '{theme_name}' not found")
            return False

        try:
            old_theme = self._current_theme
            self._current_theme = theme_name

            # 更新配置
            self.update_config({'current_theme': theme_name})

            # 发布主题变更事件
            event = ThemeChangedEvent(
                theme_name=theme_name,
                theme_config=self._themes[theme_name]
            )
            event.data.update({
                'old_theme': old_theme,
                'new_theme': theme_name
            })
            self.event_bus.publish(event)

            logger.info(f"Theme changed from '{old_theme}' to '{theme_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to set theme '{theme_name}': {e}")
            return False

    def get_available_themes(self) -> List[str]:
        """
        获取可用的主题列表

        Returns:
            主题名称列表
        """
        self._ensure_initialized()
        return list(self._themes.keys())

    def get_theme_info(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """
        获取主题信息

        Args:
            theme_name: 主题名称

        Returns:
            主题信息
        """
        self._ensure_initialized()

        theme_config = self._themes.get(theme_name)
        if not theme_config:
            return None

        return {
            'name': theme_name,
            'display_name': theme_config.get('display_name', theme_name),
            'description': theme_config.get('description', ''),
            'author': theme_config.get('author', ''),
            'version': theme_config.get('version', '1.0'),
            'preview_image': theme_config.get('preview_image', ''),
            'colors': theme_config.get('colors', {}),
            'fonts': theme_config.get('fonts', {}),
            'styles': theme_config.get('styles', {})
        }

    def create_custom_theme(self, theme_name: str, base_theme: str = 'default',
                            customizations: Dict[str, Any] = None) -> bool:
        """
        创建自定义主题

        Args:
            theme_name: 新主题名称
            base_theme: 基础主题
            customizations: 自定义配置

        Returns:
            是否成功创建
        """
        self._ensure_initialized()

        if theme_name in self._themes:
            logger.warning(f"Theme '{theme_name}' already exists")
            return False

        if base_theme not in self._themes:
            logger.warning(f"Base theme '{base_theme}' not found")
            return False

        try:
            # 基于基础主题创建新主题
            base_config = self._themes[base_theme].copy()

            # 应用自定义配置
            if customizations:
                self._apply_customizations(base_config, customizations)

            # 设置主题元信息
            base_config.update({
                'display_name': theme_name,
                'description': f'Custom theme based on {base_theme}',
                'author': 'User',
                'version': '1.0',
                'is_custom': True
            })

            # 添加到主题列表
            self._themes[theme_name] = base_config

            # 保存到文件
            self._save_custom_theme(theme_name, base_config)

            logger.info(
                f"Created custom theme '{theme_name}' based on '{base_theme}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create custom theme '{theme_name}': {e}")
            return False

    def delete_custom_theme(self, theme_name: str) -> bool:
        """
        删除自定义主题

        Args:
            theme_name: 主题名称

        Returns:
            是否成功删除
        """
        self._ensure_initialized()

        if theme_name not in self._themes:
            logger.warning(f"Theme '{theme_name}' not found")
            return False

        theme_config = self._themes[theme_name]
        if not theme_config.get('is_custom', False):
            logger.warning(f"Cannot delete built-in theme '{theme_name}'")
            return False

        try:
            # 如果是当前主题，切换到默认主题
            if self._current_theme == theme_name:
                self.set_theme('default')

            # 从主题列表中移除
            del self._themes[theme_name]

            # 删除主题文件
            theme_file = self._theme_files_path / f"{theme_name}.json"
            if theme_file.exists():
                theme_file.unlink()

            logger.info(f"Deleted custom theme '{theme_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to delete custom theme '{theme_name}': {e}")
            return False

    def export_theme(self, theme_name: str, export_path: str) -> bool:
        """
        导出主题

        Args:
            theme_name: 主题名称
            export_path: 导出路径

        Returns:
            是否成功导出
        """
        self._ensure_initialized()

        if theme_name not in self._themes:
            logger.warning(f"Theme '{theme_name}' not found")
            return False

        try:
            theme_config = self._themes[theme_name]
            export_file = Path(export_path)

            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(theme_config, f, ensure_ascii=False, indent=2)

            logger.info(f"Exported theme '{theme_name}' to '{export_path}'")
            return True

        except Exception as e:
            logger.error(f"Failed to export theme '{theme_name}': {e}")
            return False

    def import_theme(self, import_path: str) -> Optional[str]:
        """
        导入主题

        Args:
            import_path: 导入路径

        Returns:
            导入的主题名称，失败返回None
        """
        self._ensure_initialized()

        try:
            import_file = Path(import_path)
            if not import_file.exists():
                logger.warning(f"Theme file '{import_path}' not found")
                return None

            with open(import_file, 'r', encoding='utf-8') as f:
                theme_config = json.load(f)

            # 验证主题配置
            if not self._validate_theme_config(theme_config):
                logger.warning(
                    f"Invalid theme configuration in '{import_path}'")
                return None

            # 获取主题名称
            theme_name = theme_config.get('name', import_file.stem)

            # 如果主题已存在，添加后缀
            original_name = theme_name
            counter = 1
            while theme_name in self._themes:
                theme_name = f"{original_name}_{counter}"
                counter += 1

            # 添加到主题列表
            theme_config['name'] = theme_name
            theme_config['is_custom'] = True
            self._themes[theme_name] = theme_config

            # 保存主题文件
            self._save_custom_theme(theme_name, theme_config)

            logger.info(f"Imported theme '{theme_name}' from '{import_path}'")
            return theme_name

        except Exception as e:
            logger.error(f"Failed to import theme from '{import_path}': {e}")
            return None

    def _load_builtin_themes(self) -> None:
        """加载内置主题"""
        # 默认浅色主题
        self._themes['default'] = {
            'name': 'default',
            'display_name': '默认主题',
            'description': '默认浅色主题',
            'author': 'HIkyuu',
            'version': '1.0',
            'is_custom': False,
            'colors': {
                'primary': '#1976d2',
                'secondary': '#dc004e',
                'background': '#ffffff',
                'surface': '#f5f5f5',
                'text_primary': '#212121',
                'text_secondary': '#757575',
                'border': '#e0e0e0',
                'success': '#4caf50',
                'warning': '#ff9800',
                'error': '#f44336',
                'info': '#2196f3'
            },
            'chart_colors': {
                'up_color': '#f44336',
                'down_color': '#4caf50',
                'ma_colors': ['#ff6600', '#0066ff', '#ff00ff', '#00ffff'],
                'volume_color': '#9e9e9e',
                'grid_color': '#e0e0e0',
                'axis_color': '#757575'
            },
            'fonts': {
                'family': 'Microsoft YaHei, Arial, sans-serif',
                'size_small': 10,
                'size_normal': 12,
                'size_large': 14,
                'size_title': 16
            },
            'styles': {
                'border_radius': 4,
                'shadow': '0 2px 4px rgba(0,0,0,0.1)',
                'animation_duration': 200
            }
        }

        # 深色主题
        self._themes['dark'] = {
            'name': 'dark',
            'display_name': '深色主题',
            'description': '深色护眼主题',
            'author': 'HIkyuu',
            'version': '1.0',
            'is_custom': False,
            'colors': {
                'primary': '#90caf9',
                'secondary': '#f48fb1',
                'background': '#121212',
                'surface': '#1e1e1e',
                'text_primary': '#ffffff',
                'text_secondary': '#b0b0b0',
                'border': '#404040',
                'success': '#81c784',
                'warning': '#ffb74d',
                'error': '#e57373',
                'info': '#64b5f6'
            },
            'chart_colors': {
                'up_color': '#e57373',
                'down_color': '#81c784',
                'ma_colors': ['#ff8a65', '#42a5f5', '#ba68c8', '#4dd0e1'],
                'volume_color': '#757575',
                'grid_color': '#404040',
                'axis_color': '#b0b0b0'
            },
            'fonts': {
                'family': 'Microsoft YaHei, Arial, sans-serif',
                'size_small': 10,
                'size_normal': 12,
                'size_large': 14,
                'size_title': 16
            },
            'styles': {
                'border_radius': 4,
                'shadow': '0 2px 8px rgba(0,0,0,0.3)',
                'animation_duration': 200
            }
        }

        # 护眼主题
        self._themes['eye_care'] = {
            'name': 'eye_care',
            'display_name': '护眼主题',
            'description': '绿色护眼主题',
            'author': 'HIkyuu',
            'version': '1.0',
            'is_custom': False,
            'colors': {
                'primary': '#689f38',
                'secondary': '#ff7043',
                'background': '#f1f8e9',
                'surface': '#e8f5e8',
                'text_primary': '#2e7d32',
                'text_secondary': '#558b2f',
                'border': '#c8e6c9',
                'success': '#4caf50',
                'warning': '#ff9800',
                'error': '#f44336',
                'info': '#2196f3'
            },
            'chart_colors': {
                'up_color': '#d32f2f',
                'down_color': '#388e3c',
                'ma_colors': ['#f57c00', '#1976d2', '#7b1fa2', '#0097a7'],
                'volume_color': '#795548',
                'grid_color': '#c8e6c9',
                'axis_color': '#558b2f'
            },
            'fonts': {
                'family': 'Microsoft YaHei, Arial, sans-serif',
                'size_small': 10,
                'size_normal': 12,
                'size_large': 14,
                'size_title': 16
            },
            'styles': {
                'border_radius': 6,
                'shadow': '0 2px 4px rgba(0,0,0,0.1)',
                'animation_duration': 150
            }
        }

    def _load_external_themes(self) -> None:
        """加载外部主题文件"""
        if not self._theme_files_path.exists():
            self._theme_files_path.mkdir(parents=True, exist_ok=True)
            return

        for theme_file in self._theme_files_path.glob('*.json'):
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    theme_config = json.load(f)

                if self._validate_theme_config(theme_config):
                    theme_name = theme_config.get('name', theme_file.stem)
                    theme_config['is_custom'] = True
                    self._themes[theme_name] = theme_config
                    logger.debug(f"Loaded external theme: {theme_name}")
                else:
                    logger.warning(
                        f"Invalid theme configuration in {theme_file}")

            except Exception as e:
                logger.error(f"Failed to load theme from {theme_file}: {e}")

    def _validate_theme_config(self, config: Dict[str, Any]) -> bool:
        """验证主题配置"""
        required_keys = ['colors', 'chart_colors', 'fonts']

        for key in required_keys:
            if key not in config:
                return False

        # 验证必要的颜色配置
        required_colors = ['primary', 'background', 'text_primary']
        colors = config.get('colors', {})
        for color_key in required_colors:
            if color_key not in colors:
                return False

        return True

    def _apply_customizations(self, base_config: Dict[str, Any],
                              customizations: Dict[str, Any]) -> None:
        """应用自定义配置"""
        for key, value in customizations.items():
            if isinstance(value, dict) and key in base_config:
                if isinstance(base_config[key], dict):
                    base_config[key].update(value)
                else:
                    base_config[key] = value
            else:
                base_config[key] = value

    def _save_custom_theme(self, theme_name: str, theme_config: Dict[str, Any]) -> None:
        """保存自定义主题到文件"""
        if not self._theme_files_path.exists():
            self._theme_files_path.mkdir(parents=True, exist_ok=True)

        theme_file = self._theme_files_path / f"{theme_name}.json"
        with open(theme_file, 'w', encoding='utf-8') as f:
            json.dump(theme_config, f, ensure_ascii=False, indent=2)

    def _do_dispose(self) -> None:
        """清理资源"""
        self._themes.clear()
        super()._do_dispose()
