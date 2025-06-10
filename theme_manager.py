"""
theme_manager.py
主题管理模块，支持自定义主题、切换、导入导出等

用法示例：
    tm = ThemeManager()
    tm.add_theme('light', '{"bg": "#fff"}')
    tm.set_theme('light')
    print(tm.get_theme())
    tm.export_theme('light', 'light.json')
    tm.import_theme('dark.json')
"""
from typing import List, Dict, Optional


class ThemeManager:
    """
    主题管理主类

    属性:
        themes: 主题名到内容的映射
        current_theme: 当前主题名
    """

    def __init__(self):
        self.themes: Dict[str, str] = {}
        self.current_theme: Optional[str] = None

    def add_theme(self, name: str, content: str) -> None:
        """
        添加新主题
        :param name: 主题名
        :param content: 主题内容（QSS或JSON字符串）
        """
        self.themes[name] = content

    def set_theme(self, name: str) -> None:
        """
        切换主题
        :param name: 主题名
        """
        if name in self.themes:
            self.current_theme = name

    def get_theme(self) -> Optional[str]:
        """
        获取当前主题内容
        :return: 当前主题内容字符串
        """
        if self.current_theme:
            return self.themes[self.current_theme]
        return None

    def list_themes(self) -> List[str]:
        """
        返回所有主题名
        :return: 主题名列表
        """
        return list(self.themes.keys())

    def export_theme(self, name: str, path: str) -> None:
        """
        导出主题到文件
        :param name: 主题名
        :param path: 导出路径
        """
        if name in self.themes:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.themes[name])

    def import_theme(self, path: str) -> None:
        """
        从文件导入主题
        :param path: 文件路径
        """
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        name = path.split('/')[-1].split('.')[0]
        self.add_theme(name, content)

# 后续可扩展：主题类型（QSS/JSON）、主题预览、主题市场等
