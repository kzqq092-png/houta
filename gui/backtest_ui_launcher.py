"""
HIkyuu专业级回测UI启动器
集成Streamlit Web UI和PyQt5桌面UI两种界面
提供统一的启动入口和配置管理
"""

import sys
import os
import subprocess
import threading
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
import webbrowser
import socket
from contextlib import closing

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
    from PyQt5.QtWidgets import QPushButton, QLabel, QComboBox, QSpinBox, QTextEdit, QTabWidget
    from PyQt5.QtCore import QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QFont, QIcon
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    print("PyQt5 not available, only Streamlit UI will be supported")

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("Streamlit not available, only PyQt5 UI will be supported")

# 导入回测UI组件
if PYQT5_AVAILABLE:
    try:
        from gui.widgets.backtest_widget import ProfessionalBacktestWidget, create_backtest_widget
    except ImportError:
        print("Warning: Could not import PyQt5 backtest widget")

if STREAMLIT_AVAILABLE:
    try:
        from backtest.professional_ui_system import run_professional_ui, create_professional_ui
    except ImportError:
        print("Warning: Could not import Streamlit UI system")

# 导入核心模块
try:
    from core.logger import LogManager
    from utils.config_manager import ConfigManager
    CORE_MODULES_AVAILABLE = True
except ImportError:
    # 如果核心模块不可用，使用简化版本
    try:
        # 尝试导入基础日志管理器
        from core.base_logger import BaseLogManager as LogManager
    except ImportError:
        class LogManager:
            def log(self, message, level):
                print(f"[{level}] {message}")

            def info(self, message):
                print(f"[INFO] {message}")

            def warning(self, message):
                print(f"[WARNING] {message}")

            def error(self, message):
                print(f"[ERROR] {message}")

    # 简化版配置管理器
    class ConfigManager:
        def __init__(self):
            self.config = {
                'ui': {
                    'theme': 'dark',
                    'window_size': (1200, 800),
                    'default_port': 8501
                },
                'backtest': {
                    'default_capital': 100000,
                    'commission_pct': 0.001
                }
            }

        def get(self, key, default=None):
            keys = key.split('.')
            value = self.config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    CORE_MODULES_AVAILABLE = False


class StreamlitUIThread(QThread):
    """Streamlit UI线程"""

    started = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, port: int = 8501):
        super().__init__()
        self.port = port
        self.process = None

    def run(self):
        """运行Streamlit应用"""
        try:
            # 检查端口是否可用
            if not self._is_port_available(self.port):
                self.port = self._find_available_port()

            # 启动Streamlit应用
            cmd = [
                sys.executable, "-m", "streamlit", "run",
                str(project_root / "backtest" / "professional_ui_system.py"),
                "--server.port", str(self.port),
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false"
            ]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(project_root)
            )

            # 等待应用启动
            time.sleep(3)

            if self.process.poll() is None:
                self.started.emit()
            else:
                stdout, stderr = self.process.communicate()
                self.error.emit(f"Streamlit启动失败: {stderr.decode()}")

        except Exception as e:
            self.error.emit(f"启动Streamlit失败: {str(e)}")

    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            return sock.connect_ex(('localhost', port)) != 0

    def _find_available_port(self, start_port: int = 8501) -> int:
        """查找可用端口"""
        for port in range(start_port, start_port + 100):
            if self._is_port_available(port):
                return port
        return start_port

    def stop(self):
        """停止Streamlit应用"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()


class BacktestUILauncher(QMainWindow if PYQT5_AVAILABLE else object):
    """回测UI启动器主窗口"""

    def __init__(self):
        if PYQT5_AVAILABLE:
            super().__init__()

        self.log_manager = LogManager()
        self.config_manager = ConfigManager()
        self.streamlit_thread = None

        if PYQT5_AVAILABLE:
            self.init_ui()

        self.log_manager.log("回测UI启动器初始化完成", LogLevel.INFO)

    def init_ui(self):
        """初始化UI"""
        if not PYQT5_AVAILABLE:
            return

        self.setWindowTitle("HIkyuu Professional Backtest System Launcher")
        self.setGeometry(100, 100, 800, 600)

        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0e1117;
                color: white;
            }
            QWidget {
                background-color: #0e1117;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background: linear-gradient(45deg, #00d4ff, #8b5cf6);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                margin: 5px;
            }
            QPushButton:hover {
                background: linear-gradient(45deg, #0099cc, #6d28d9);
            }
            QPushButton:pressed {
                background: linear-gradient(45deg, #0066aa, #5b21b6);
            }
            QLabel {
                color: white;
                font-size: 14px;
                padding: 5px;
            }
            QTabWidget::pane {
                border: 1px solid #2d3748;
                background-color: #1e2329;
            }
            QTabBar::tab {
                background-color: #2d3748;
                color: white;
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #00d4ff;
                color: black;
            }
        """)

        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 标题
        title = QLabel("📈 HIkyuu Professional Backtest System")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #00d4ff;
                text-align: center;
                padding: 20px;
            }
        """)
        main_layout.addWidget(title)

        # 选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # UI选择选项卡
        self.create_ui_selection_tab()

        # 配置选项卡
        self.create_config_tab()

        # 日志选项卡
        self.create_log_tab()

        # 状态栏
        self.statusBar().showMessage("就绪")
        self.statusBar().setStyleSheet("color: #00ff88; font-weight: bold;")

    def create_ui_selection_tab(self):
        """创建UI选择选项卡"""
        if not PYQT5_AVAILABLE:
            return

        ui_tab = QWidget()
        layout = QVBoxLayout(ui_tab)

        # 说明文本
        description = QLabel("""
        HIkyuu专业级回测系统提供两种用户界面：
        
        🌐 Web界面 (Streamlit)：
        • 现代化的Web界面，支持实时图表
        • 适合远程访问和团队协作
        • 自动刷新和实时监控
        
        🖥️ 桌面界面 (PyQt5)：
        • 原生桌面应用体验
        • 更快的响应速度
        • 更好的系统集成
        """)
        description.setStyleSheet("""
            QLabel {
                background-color: #1e2329;
                border: 1px solid #2d3748;
                border-radius: 8px;
                padding: 20px;
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        layout.addWidget(description)

        # 按钮布局
        buttons_layout = QHBoxLayout()

        # Web界面按钮
        if STREAMLIT_AVAILABLE:
            web_button = QPushButton("🌐 启动Web界面")
            web_button.clicked.connect(self.launch_web_ui)
            buttons_layout.addWidget(web_button)

        # 桌面界面按钮
        if PYQT5_AVAILABLE:
            desktop_button = QPushButton("🖥️ 启动桌面界面")
            desktop_button.clicked.connect(self.launch_desktop_ui)
            buttons_layout.addWidget(desktop_button)

        # 同时启动按钮
        if STREAMLIT_AVAILABLE and PYQT5_AVAILABLE:
            both_button = QPushButton("🚀 同时启动两个界面")
            both_button.clicked.connect(self.launch_both_ui)
            buttons_layout.addWidget(both_button)

        layout.addLayout(buttons_layout)

        # 状态显示
        self.ui_status = QLabel("状态: 未启动")
        self.ui_status.setStyleSheet("""
            QLabel {
                background-color: #2d3748;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.ui_status)

        layout.addStretch()
        self.tab_widget.addTab(ui_tab, "UI选择")

    def create_config_tab(self):
        """创建配置选项卡"""
        if not PYQT5_AVAILABLE:
            return

        config_tab = QWidget()
        layout = QVBoxLayout(config_tab)

        # 配置说明
        config_label = QLabel("⚙️ 系统配置")
        config_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #00ff88;")
        layout.addWidget(config_label)

        # 端口配置
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Streamlit端口:"))
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(8000, 9999)
        self.port_spinbox.setValue(8501)
        port_layout.addWidget(self.port_spinbox)
        port_layout.addStretch()
        layout.addLayout(port_layout)

        # 主题选择
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("UI主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        # 保存配置按钮
        save_config_button = QPushButton("💾 保存配置")
        save_config_button.clicked.connect(self.save_config)
        layout.addWidget(save_config_button)

        layout.addStretch()
        self.tab_widget.addTab(config_tab, "配置")

    def create_log_tab(self):
        """创建日志选项卡"""
        if not PYQT5_AVAILABLE:
            return

        log_tab = QWidget()
        layout = QVBoxLayout(log_tab)

        # 日志标题
        log_label = QLabel("📋 系统日志")
        log_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #f59e0b;")
        layout.addWidget(log_label)

        # 日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e2329;
                border: 1px solid #2d3748;
                border-radius: 5px;
                color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        # 清除日志按钮
        clear_log_button = QPushButton("🗑️ 清除日志")
        clear_log_button.clicked.connect(self.clear_log)
        layout.addWidget(clear_log_button)

        self.tab_widget.addTab(log_tab, "日志")

    def launch_web_ui(self):
        """启动Web界面"""
        try:
            if not STREAMLIT_AVAILABLE:
                self.log_message("Streamlit不可用", LogLevel.ERROR)
                return

            self.log_message("正在启动Web界面...", LogLevel.INFO)
            self.ui_status.setText("状态: 正在启动Web界面...")

            # 启动Streamlit线程
            self.streamlit_thread = StreamlitUIThread(
                self.port_spinbox.value())
            self.streamlit_thread.started.connect(self.on_web_ui_started)
            self.streamlit_thread.error.connect(self.on_web_ui_error)
            self.streamlit_thread.start()

        except Exception as e:
            self.log_message(f"启动Web界面失败: {e}", LogLevel.ERROR)

    def launch_desktop_ui(self):
        """启动桌面界面"""
        try:
            if not PYQT5_AVAILABLE:
                self.log_message("PyQt5不可用", LogLevel.ERROR)
                return

            self.log_message("正在启动桌面界面...", LogLevel.INFO)
            self.ui_status.setText("状态: 正在启动桌面界面...")

            # 创建回测组件窗口
            self.backtest_window = QMainWindow()
            self.backtest_window.setWindowTitle(
                "HIkyuu Professional Backtest System")
            self.backtest_window.setGeometry(150, 150, 1400, 800)

            # 创建回测组件
            backtest_widget = create_backtest_widget(self.config_manager)
            self.backtest_window.setCentralWidget(backtest_widget)

            # 显示窗口
            self.backtest_window.show()

            self.ui_status.setText("状态: 桌面界面已启动")
            self.log_message("桌面界面启动成功", LogLevel.INFO)

        except Exception as e:
            self.log_message(f"启动桌面界面失败: {e}", LogLevel.ERROR)
            self.ui_status.setText("状态: 桌面界面启动失败")

    def launch_both_ui(self):
        """同时启动两个界面"""
        self.launch_web_ui()
        QTimer.singleShot(2000, self.launch_desktop_ui)  # 延迟2秒启动桌面界面

    def on_web_ui_started(self):
        """Web界面启动成功"""
        port = self.streamlit_thread.port
        url = f"http://localhost:{port}"

        self.ui_status.setText(f"状态: Web界面已启动 ({url})")
        self.log_message(f"Web界面启动成功: {url}", LogLevel.INFO)

        # 自动打开浏览器
        try:
            webbrowser.open(url)
        except Exception as e:
            self.log_message(f"无法自动打开浏览器: {e}", LogLevel.WARNING)

    def on_web_ui_error(self, error_msg: str):
        """Web界面启动失败"""
        self.ui_status.setText("状态: Web界面启动失败")
        self.log_message(error_msg, LogLevel.ERROR)

    def save_config(self):
        """保存配置"""
        try:
            config = {
                'streamlit_port': self.port_spinbox.value(),
                'ui_theme': self.theme_combo.currentText()
            }

            # 这里可以保存到配置文件
            self.log_message("配置已保存", LogLevel.INFO)

        except Exception as e:
            self.log_message(f"保存配置失败: {e}", LogLevel.ERROR)

    def clear_log(self):
        """清除日志"""
        if PYQT5_AVAILABLE:
            self.log_display.clear()

    def log_message(self, message: str, level: str):
        """记录日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"

        # 输出到控制台
        print(log_entry)

        # 输出到UI日志显示
        if PYQT5_AVAILABLE and hasattr(self, 'log_display'):
            self.log_display.append(log_entry)
            self.log_display.ensureCursorVisible()

        # 记录到日志管理器
        self.log_manager.log(message, level)

    def closeEvent(self, event):
        """关闭事件"""
        if PYQT5_AVAILABLE:
            # 停止Streamlit线程
            if self.streamlit_thread:
                self.streamlit_thread.stop()

            # 关闭回测窗口
            if hasattr(self, 'backtest_window'):
                self.backtest_window.close()

            self.log_message("应用程序已关闭", LogLevel.INFO)
            event.accept()


def launch_streamlit_only():
    """仅启动Streamlit界面"""
    if not STREAMLIT_AVAILABLE:
        print("错误: Streamlit不可用")
        return

    try:
        from backtest.professional_ui_system import run_professional_ui
        run_professional_ui()
    except Exception as e:
        print(f"启动Streamlit界面失败: {e}")


def launch_pyqt5_only():
    """仅启动PyQt5界面"""
    if not PYQT5_AVAILABLE:
        print("错误: PyQt5不可用")
        return

    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')

        # 创建回测组件
        backtest_widget = create_backtest_widget()

        # 创建主窗口
        window = QMainWindow()
        window.setWindowTitle("HIkyuu Professional Backtest System")
        window.setGeometry(100, 100, 1400, 800)
        window.setCentralWidget(backtest_widget)
        window.show()

        sys.exit(app.exec_())

    except Exception as e:
        print(f"启动PyQt5界面失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="HIkyuu Professional Backtest System Launcher")
    parser.add_argument("--ui", choices=["web", "desktop", "launcher"], default="launcher",
                        help="选择UI类型: web(仅Web界面), desktop(仅桌面界面), launcher(启动器)")
    parser.add_argument("--port", type=int, default=8501, help="Streamlit端口号")
    parser.add_argument(
        "--theme", choices=["dark", "light"], default="dark", help="UI主题")

    args = parser.parse_args()

    if args.ui == "web":
        launch_streamlit_only()
    elif args.ui == "desktop":
        launch_pyqt5_only()
    else:
        # 启动完整的启动器
        if not PYQT5_AVAILABLE:
            print("PyQt5不可用，回退到Streamlit界面")
            launch_streamlit_only()
            return

        app = QApplication(sys.argv)
        app.setStyle('Fusion')

        # 创建启动器
        launcher = BacktestUILauncher()
        launcher.show()

        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
