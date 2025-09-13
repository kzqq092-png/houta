#!/usr/bin/env python3
"""
网络配置UI演示脚本
演示通用网络配置系统在插件配置对话框中的集成
"""

from core.network.plugin_auto_register import initialize_plugin_network_configs
from gui.dialogs.data_source_plugin_config_dialog import DataSourcePluginConfigDialog
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


# 导入网络配置相关模块


class NetworkConfigDemo(QMainWindow):
    """网络配置演示主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("通用网络配置系统演示")
        self.setFixedSize(400, 300)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # 标题
        title_label = QLabel("通用网络配置系统演示")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin: 20px;")
        layout.addWidget(title_label)

        # 说明
        info_label = QLabel(
            "这个演示展示了通用网络配置系统如何集成到数据源插件配置对话框中。\n\n"
            "点击下面的按钮可以打开不同插件的配置对话框，其中都包含了"网络配置"标签页。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #34495e; margin: 10px;")
        layout.addWidget(info_label)

        # 插件演示按钮
        plugins_to_demo = [
            ("akshare_stock_plugin", "AkShare股票插件"),
            ("eastmoney_stock_plugin", "东方财富股票插件"),
            ("tongdaxin_stock_plugin", "通达信股票插件"),
            ("sina_stock_plugin", "新浪股票插件"),
            ("tencent_stock_plugin", "腾讯股票插件"),
            ("generic_data_source", "通用数据源插件")
        ]

        for plugin_id, plugin_name in plugins_to_demo:
            btn = QPushButton(f"打开 {plugin_name} 配置")
            btn.clicked.connect(lambda checked, pid=plugin_id, pname=plugin_name: self.open_plugin_config(pid, pname))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 10px;
                    margin: 5px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
            """)
            layout.addWidget(btn)

        layout.addStretch()

        # 初始化网络配置系统
        self.init_network_system()

    def init_network_system(self):
        """初始化网络配置系统"""
        try:
            print("正在初始化网络配置系统...")
            results = initialize_plugin_network_configs()
            print(f"网络配置系统初始化完成，已注册 {len(results)} 个插件")
        except Exception as e:
            print(f"网络配置系统初始化失败: {e}")

    def open_plugin_config(self, plugin_id: str, plugin_name: str):
        """打开插件配置对话框"""
        try:
            print(f"打开插件配置: {plugin_name} ({plugin_id})")

            # 创建插件配置对话框
            dialog = DataSourcePluginConfigDialog(plugin_id, self)
            dialog.setWindowTitle(f"插件配置 - {plugin_name}")

            # 显示对话框
            dialog.exec_()

        except Exception as e:
            print(f"打开插件配置失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"打开插件配置失败:\n{e}")


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #ecf0f1;
        }
        QLabel {
            color: #2c3e50;
        }
    """)

    # 创建主窗口
    demo = NetworkConfigDemo()
    demo.show()

    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
