from loguru import logger
"""
Theme Management Module

This module provides a unified theme management solution with support for
multiple themes, dynamic theme switching, and theme customization.
"""

from enum import Enum
import json
import os
import re
import glob
from typing import Dict, Any, Optional, Union
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from .config_manager import ConfigManager
from .theme_types import Theme
from .config_types import ThemeConfig
from core.base_logger import BaseLogManager
from utils.theme_utils import load_theme_json_with_comments
import sqlite3
from datetime import datetime
from PyQt5.QtGui import *

# Global theme manager instance
_theme_manager_instance: Optional['ThemeManager'] = None

DB_PATH = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'db', 'factorweave_system.sqlite')

def safe_read_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='latin1') as f:
                return f.read()

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

class ThemeType(Enum):
    JSON = 'json'
    QSS = 'qss'

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
        self._init_db()
        self._load_theme_json()
        self.qss_theme_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'QSSTheme')
        self._import_themes_to_db()
        self._current_theme_type = ThemeType.JSON
        self._current_qss_file = None

    def _init_db(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.execute('''CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            type TEXT,
            content TEXT,
            origin TEXT,
            created_at TEXT,
            updated_at TEXT
        )''')
        self.conn.commit()

    def _import_themes_to_db(self):
        # 导入QSS主题
        for qss_file in glob.glob(os.path.join(self.qss_theme_dir, '*.qss')):
            name = self._extract_qss_theme_name(
                qss_file) or os.path.splitext(os.path.basename(qss_file))[0]
            content = safe_read_file(qss_file)
            # 跳过已存在的主题
            cur = self.conn.cursor()
            cur.execute('SELECT id FROM themes WHERE name=?', (name,))
            if cur.fetchone():
                continue
            self._upsert_theme(name, 'qss', content, 'file')
        # 导入JSON主题
        for t in self._theme_data.keys():
            name = t.capitalize()
            content = json.dumps(self._theme_data[t], ensure_ascii=False)
            cur = self.conn.cursor()
            cur.execute('SELECT id FROM themes WHERE name=?', (name,))
            if cur.fetchone():
                continue
            self._upsert_theme(name, 'json', content, 'file')

    def _upsert_theme(self, name, type_, content, origin):
        now = datetime.now().isoformat()
        cur = self.conn.cursor()
        cur.execute('SELECT id FROM themes WHERE name=?', (name,))
        if cur.fetchone():
            cur.execute('UPDATE themes SET type=?, content=?, origin=?, updated_at=? WHERE name=?',
                        (type_, content, origin, now, name))
        else:
            cur.execute('INSERT INTO themes (name, type, content, origin, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (name, type_, content, origin, now, now))
        self.conn.commit()

    def _get_all_themes_from_db(self):
        cur = self.conn.cursor()
        cur.execute('SELECT name, type FROM themes ORDER BY id')
        return cur.fetchall()

    def _get_theme_content(self, name):
        cur = self.conn.cursor()
        cur.execute('SELECT type, content FROM themes WHERE name=?', (name,))
        return cur.fetchone()

    def _load_theme_json(self):
        """加载主题配置文件"""
        try:
            self._theme_data = load_theme_json_with_comments(
                self._theme_json_path)
        except Exception as e:
            logger.info(f"加载theme.json失败: {str(e)}")
            self._theme_data = {}

    @property
    def current_theme(self) -> Theme:
        """获取当前主题"""
        return self._current_theme

    def set_theme(self, theme_name: str):
        row = self._get_theme_content(theme_name)
        if not row:
            return
        type_, content = row
        if type_ == 'qss':
            self._current_theme_type = ThemeType.QSS
            self.apply_qss_theme_content(content)
            # QSS主题也应emit当前Theme，保证UI联动
            # 尝试根据name映射Theme枚举，否则默认LIGHT
            theme_enum = None
            for t in Theme:
                if t.name.lower() == theme_name.lower():
                    theme_enum = t
                    break
            if theme_enum is None:
                theme_enum = Theme.LIGHT
            self._current_theme = theme_enum
            self.theme_changed.emit(self._current_theme)
        else:
            self._current_theme_type = ThemeType.JSON
            theme_dict = json.loads(content)
            for t in Theme:
                if t.name.lower() == theme_name.lower():
                    self._current_theme = t
                    break
            self._theme_cache[theme_name.lower()] = theme_dict
            # 只持久化主题名到config表
            theme_cfg = self.config_manager.get('theme', {})
            theme_cfg['theme_name'] = theme_name
            self.config_manager.set('theme', theme_cfg)
            self.theme_changed.emit(self._current_theme)

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
            logger.info(f"应用图表主题失败: {str(e)}")

    def is_dark_theme(self) -> bool:
        """Check if current theme is dark

        Returns:
            True if current theme is dark
        """
        return self.current_theme.is_dark

    def _scan_qss_themes(self):
        themes = {}
        for qss_file in glob.glob(os.path.join(self.qss_theme_dir, '*.qss')):
            name = self._extract_qss_theme_name(qss_file)
            if not name:
                name = os.path.splitext(os.path.basename(qss_file))[0]
            themes[name] = qss_file
        return themes

    def _extract_qss_theme_name(self, qss_file):
        try:
            with open(qss_file, 'r', encoding='utf-8') as f:
                for _ in range(10):
                    line = f.readline()
                    if 'Style Sheet' in line or 'StyleSheet' in line:
                        return line.strip('/*').strip().replace('Style Sheet for QT Applications', '').replace('StyleSheet for QT Applications', '').replace('Style Sheet', '').replace('for QT Applications', '').strip()
        except Exception:
            pass
        return None

    def get_all_themes(self):
        # 返回所有主题名称（数据库）
        return [row[0] for row in self._get_all_themes_from_db()]

    def get_available_themes(self):
        """获取可用主题列表（兼容性方法）

        Returns:
            dict: 主题名称到主题信息的映射
        """
        try:
            themes = {}
            # 获取数据库中的主题
            db_themes = self._get_all_themes_from_db()
            for name, type_, content, origin, created_at, updated_at in db_themes:
                themes[name] = {
                    'name': name,
                    'type': type_,
                    'origin': origin,
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'description': f'{type_.upper()}主题' if type_ else '未知类型主题'
                }

            # 添加内置主题
            builtin_themes = {
                'default': {
                    'name': 'default',
                    'type': 'builtin',
                    'origin': 'system',
                    'description': '默认主题'
                },
                'dark': {
                    'name': 'dark',
                    'type': 'builtin',
                    'origin': 'system',
                    'description': '深色主题'
                },
                'light': {
                    'name': 'light',
                    'type': 'builtin',
                    'origin': 'system',
                    'description': '浅色主题'
                }
            }

            # 合并主题，数据库主题优先
            for name, info in builtin_themes.items():
                if name not in themes:
                    themes[name] = info

            return themes

        except Exception as e:
            # 如果出错，返回基本的内置主题
            return {
                'default': {'name': 'default', 'type': 'builtin', 'description': '默认主题'},
                'dark': {'name': 'dark', 'type': 'builtin', 'description': '深色主题'},
                'light': {'name': 'light', 'type': 'builtin', 'description': '浅色主题'}
            }

    def apply_qss_theme_content(self, qss):
        # 全局滚动条样式
        scrollbar_qss = '''
            QScrollBar:vertical {
                width: 5px;
                background: #f0f0f0;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar:horizontal {
                height: 5px;
                background: #f0f0f0;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #b0b0b0;
                min-height: 20px;
                min-width: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        '''
        QApplication.instance().setStyleSheet(qss + '\n' + scrollbar_qss)

    def clear_qss_theme(self):
        QApplication.instance().setStyleSheet('')

    def is_qss_theme(self):
        return self._current_theme_type == ThemeType.QSS

    # 主题增删改查接口（预留）
    def add_theme(self, name, type_, content, origin='user'):
        self._upsert_theme(name, type_, content, origin)

    def delete_theme(self, name):
        self.conn.execute('DELETE FROM themes WHERE name=?', (name,))
        self.conn.commit()

    def update_theme(self, name, content):
        now = datetime.now().isoformat()
        self.conn.execute(
            'UPDATE themes SET content=?, updated_at=? WHERE name=?', (content, now, name))
        self.conn.commit()

    def edit_theme(self, name: str, new_content: str) -> bool:
        """
        编辑QSS主题内容并保存到数据库，仅支持QSS类型主题。
        Args:
            name: 主题名称
            new_content: 新的QSS内容
        Returns:
            True: 编辑成功
            False: 编辑失败（主题不存在或不是QSS类型）
        """
        row = self._get_theme_content(name)
        if not row:
            return False
        type_, _ = row
        if type_ != 'qss':
            return False
        self.update_theme(name, new_content)
        # 编辑后自动应用新主题
        self.set_theme(name)
        # 不再重复emit，set_theme已emit
        return True

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
