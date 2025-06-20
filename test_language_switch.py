#!/usr/bin/env python3
"""
语言切换功能测试脚本
用于验证语言切换修复效果
"""

from utils.language_manager import get_language_switch_manager
from core.logger import LogManager
from utils.config_manager import ConfigManager
from utils.i18n import get_i18n_manager
import sys
import os
import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt5.QtCore import QTimer, pyqtSignal, QObject

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class LanguageSwitchTester(QWidget):
    """语言切换测试器"""

    def __init__(self):
        super().__init__()
        self.init_managers()
        self.init_ui()
        self.test_count = 0

    def init_managers(self):
        """初始化管理器"""
        try:
            # 初始化配置管理器
            self.config_manager = ConfigManager()

            # 初始化日志管理器
            self.log_manager = LogManager(self.config_manager.logging)

            # 初始化国际化管理器
            self.i18n_manager = get_i18n_manager()

            # 初始化语言切换管理器
            self.language_switch_manager = get_language_switch_manager(
                self.i18n_manager, self.config_manager, self.log_manager
            )

            # 连接信号
            self.language_switch_manager.language_switch_started.connect(self.on_switch_started)
            self.language_switch_manager.language_switch_completed.connect(self.on_switch_completed)
            self.language_switch_manager.language_switch_failed.connect(self.on_switch_failed)

            print("管理器初始化完成")

        except Exception as e:
            print(f"初始化管理器失败: {str(e)}")
            raise

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("语言切换测试器")
        self.setGeometry(300, 300, 600, 400)

        layout = QVBoxLayout()

        # 状态标签
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)

        # 当前语言标签
        self.current_lang_label = QLabel(f"当前语言: {self.i18n_manager.get_current_language()}")
        layout.addWidget(self.current_lang_label)

        # 语言切换按钮
        languages = {
            "zh_CN": "切换到简体中文",
            "en_US": "Switch to English",
            "zh_TW": "切換到繁體中文",
            "ja_JP": "日本語に切り替え"
        }

        for lang_code, button_text in languages.items():
            btn = QPushButton(button_text)
            btn.clicked.connect(lambda checked, code=lang_code: self.switch_language(code))
            layout.addWidget(btn)

        # 快速切换测试按钮
        self.rapid_test_btn = QPushButton("快速切换测试（防卡死）")
        self.rapid_test_btn.clicked.connect(self.rapid_switch_test)
        layout.addWidget(self.rapid_test_btn)

        # 日志显示区
        self.log_display = QTextEdit()
        self.log_display.setMaximumHeight(150)
        layout.addWidget(self.log_display)

        self.setLayout(layout)

    def switch_language(self, language_code):
        """切换语言"""
        try:
            self.log(f"请求切换语言到: {language_code}")
            success = self.language_switch_manager.switch_language(language_code)
            if not success:
                self.log("语言切换请求被拒绝")

        except Exception as e:
            self.log(f"切换语言失败: {str(e)}")

    def rapid_switch_test(self):
        """快速切换测试"""
        self.log("开始快速切换测试...")
        self.test_count = 0

        languages = ["zh_CN", "en_US", "zh_TW", "ja_JP"]

        def switch_next():
            if self.test_count < 10:  # 测试10次切换
                lang = languages[self.test_count % len(languages)]
                self.log(f"测试切换 {self.test_count + 1}/10: {lang}")
                self.switch_language(lang)
                self.test_count += 1
                QTimer.singleShot(500, switch_next)  # 500ms后继续下一次
            else:
                self.log("快速切换测试完成")

        switch_next()

    def on_switch_started(self, language_code):
        """语言切换开始"""
        self.status_label.setText(f"正在切换到: {language_code}")
        self.log(f"语言切换开始: {language_code}")

    def on_switch_completed(self, language_code):
        """语言切换完成"""
        self.status_label.setText(f"切换完成: {language_code}")
        self.current_lang_label.setText(f"当前语言: {language_code}")
        self.log(f"语言切换完成: {language_code}")

    def on_switch_failed(self, language_code, error_msg):
        """语言切换失败"""
        self.status_label.setText(f"切换失败: {language_code}")
        self.log(f"语言切换失败: {language_code} - {error_msg}")

    def log(self, message):
        """记录日志到显示区"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_display.append(f"[{timestamp}] {message}")
        print(f"[{timestamp}] {message}")

    def closeEvent(self, event):
        """关闭事件"""
        try:
            self.log("正在清理资源...")
            if hasattr(self, 'language_switch_manager'):
                self.language_switch_manager.cleanup()

            from utils.language_manager import cleanup_language_switch_manager
            cleanup_language_switch_manager()

            self.log("资源清理完成")
            event.accept()

        except Exception as e:
            self.log(f"清理资源失败: {str(e)}")
            event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)

    try:
        tester = LanguageSwitchTester()
        tester.show()

        return app.exec_()

    except Exception as e:
        print(f"测试程序启动失败: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
