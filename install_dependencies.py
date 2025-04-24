#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
合适的买卖点交易系统 - 依赖安装脚本

此脚本用于安装系统所需的所有依赖包，包括：
- 基础依赖 (在requirements.txt中)
- 可视化依赖 (seaborn, PyQt5, PyQtWebEngine)
"""

import sys
import subprocess
import os
from pathlib import Path

def install_package(package_name):
    """安装指定的包"""
    print(f"正在安装 {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"{package_name} 安装成功！")
        return True
    except subprocess.CalledProcessError:
        print(f"{package_name} 安装失败，请手动安装。")
        return False

def install_from_requirements(requirements_file):
    """从requirements.txt文件安装依赖"""
    if not os.path.exists(requirements_file):
        print(f"错误：{requirements_file} 文件不存在！")
        return False
    
    print(f"正在从 {requirements_file} 安装依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print("requirements.txt 中的依赖安装成功！")
        return True
    except subprocess.CalledProcessError:
        print("requirements.txt 中的依赖安装失败，请手动安装。")
        return False

def main():
    """主函数"""
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent
    requirements_file = current_dir / "requirements.txt"
    
    print("========== 合适的买卖点交易系统 - 依赖安装 ==========")
    print("将要安装以下依赖：")
    print("1. requirements.txt 中的基础依赖")
    print("2. seaborn (用于可视化)")
    print("3. PyQt5 (用于GUI界面)")
    print("4. PyQtWebEngine (用于GUI中的Web内容)")
    
    choice = input("是否继续安装？(y/n): ")
    if choice.lower() != 'y':
        print("安装已取消")
        return
    
    # 安装基础依赖
    install_from_requirements(requirements_file)
    
    # 安装额外依赖
    extra_packages = ["seaborn", "PyQt5", "PyQtWebEngine"]
    for package in extra_packages:
        install_package(package)
    
    print("\n所有依赖安装完成！")
    print("现在您可以运行 run_trading_gui.py 启动系统了。")

if __name__ == "__main__":
    main() 