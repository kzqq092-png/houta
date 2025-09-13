#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试增强版数据导入UI
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_ui():
    """测试UI组件"""
    try:
        from gui.enhanced_data_import_launcher import main
        print("✅ 启动增强版数据导入UI...")
        main()
    except ImportError as e:
        print(f"❌ UI组件导入失败: {e}")
        print("请确保所有依赖项已正确安装")
    except Exception as e:
        print(f"❌ UI启动失败: {e}")


if __name__ == "__main__":
    test_ui()
