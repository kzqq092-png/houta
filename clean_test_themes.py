#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理测试主题"""

from utils.config_manager import ConfigManager
from utils.theme import get_theme_manager
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


config_manager = ConfigManager()
theme_manager = get_theme_manager(config_manager)

# 删除测试主题
try:
    theme_manager.delete_theme('test_imported_theme')
    print("✅ 已删除 test_imported_theme")
except Exception as e:
    print(f"删除失败: {e}")

# 显示当前主题列表
themes = theme_manager.get_available_themes()
print(f"\n当前主题数量: {len(themes)}")
print("主题列表:", list(themes.keys()))
