#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据管理UI测试脚本

测试数据管理界面的各项功能，包括：
- 数据源管理组件
- 下载任务管理组件  
- 数据质量监控组件
- 智能数据缺失提示组件
- 数据管理对话框

作者: FactorWeave-Quant团队
版本: 1.0
"""

from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QMessageBox
import sys
import os
import traceback
from typing import List, Dict, Any
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# 导入要测试的组件
try:
    from gui.widgets.data_management_widget import (
        DataManagementWidget, DataSourceManagementWidget,
        DownloadTaskWidget, DataQualityMonitorWidget
    )
    from gui.widgets.smart_data_missing_widget import (
        SmartDataMissingPrompt, SmartDataMissingIntegration
    )
    from gui.dialogs.data_management_dialog import (
        DataManagementDialog, QuickDataCheckDialog
    )
    UI_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"导入UI组件失败: {e}")
    traceback.print_exc()
    UI_COMPONENTS_AVAILABLE = False

# 导入核心组件
try:
    from core.plugin_types import AssetType, DataType
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    print(f"导入核心组件失败: {e}")
    CORE_AVAILABLE = False
    logger = None

logger = logger.bind(module=__name__) if logger else None


class DataManagementUITestWindow(QMainWindow):
    """数据管理UI测试主窗口"""

    def __init__(self):
        super().__init__()
        self.test_components = {}
        self.setup_ui()
        self.setup_test_data()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("FactorWeave-Quant 数据管理UI测试")
        self.setGeometry(100, 100, 800, 600)

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 标题
        title_label = QLabel("数据管理UI组件测试")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 状态标签
        self.status_label = QLabel("测试系统就绪")
        self.status_label.setStyleSheet("QLabel { padding: 10px; background-color: #f0f0f0; border-radius: 5px; }")
        layout.addWidget(self.status_label)

        # 测试按钮区域
        self.create_test_buttons(layout)

    def create_test_buttons(self, layout):
        """创建测试按钮"""

        # 测试数据管理主界面
        main_widget_btn = QPushButton("测试数据管理主界面")
        main_widget_btn.clicked.connect(self.test_main_widget)
        layout.addWidget(main_widget_btn)

        # 测试数据源管理组件
        source_mgmt_btn = QPushButton("测试数据源管理组件")
        source_mgmt_btn.clicked.connect(self.test_source_management)
        layout.addWidget(source_mgmt_btn)

        # 测试下载任务组件
        task_mgmt_btn = QPushButton("测试下载任务管理组件")
        task_mgmt_btn.clicked.connect(self.test_task_management)
        layout.addWidget(task_mgmt_btn)

        # 测试数据质量监控组件
        quality_btn = QPushButton("测试数据质量监控组件")
        quality_btn.clicked.connect(self.test_quality_monitor)
        layout.addWidget(quality_btn)

        # 测试智能数据缺失提示
        missing_prompt_btn = QPushButton("测试智能数据缺失提示")
        missing_prompt_btn.clicked.connect(self.test_missing_data_prompt)
        layout.addWidget(missing_prompt_btn)

        # 测试数据管理对话框
        dialog_btn = QPushButton("测试数据管理对话框")
        dialog_btn.clicked.connect(self.test_management_dialog)
        layout.addWidget(dialog_btn)

        # 测试快速数据检查
        quick_check_btn = QPushButton("测试快速数据检查")
        quick_check_btn.clicked.connect(self.test_quick_data_check)
        layout.addWidget(quick_check_btn)

        # 综合测试
        comprehensive_btn = QPushButton("运行综合测试")
        comprehensive_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        comprehensive_btn.clicked.connect(self.run_comprehensive_test)
        layout.addWidget(comprehensive_btn)

    def setup_test_data(self):
        """设置测试数据"""
        self.test_symbols = ["000001", "000002", "600000", "600036", "BTC-USDT", "AAPL"]
        self.test_sources = ["tongdaxin", "eastmoney", "sina", "binance", "yahoo"]

    def test_main_widget(self):
        """测试数据管理主界面"""
        if not UI_COMPONENTS_AVAILABLE:
            self.show_error("UI组件不可用")
            return

        try:
            self.status_label.setText("正在测试数据管理主界面...")

            # 创建主界面组件
            main_widget = DataManagementWidget()
            main_widget.setWindowTitle("数据管理主界面测试")
            main_widget.resize(1000, 700)
            main_widget.show()

            # 保存引用
            self.test_components['main_widget'] = main_widget

            self.status_label.setText("数据管理主界面测试完成")

        except Exception as e:
            self.show_error(f"测试数据管理主界面失败: {e}")

    def test_source_management(self):
        """测试数据源管理组件"""
        if not UI_COMPONENTS_AVAILABLE:
            self.show_error("UI组件不可用")
            return

        try:
            self.status_label.setText("正在测试数据源管理组件...")

            # 创建数据源管理组件
            source_widget = DataSourceManagementWidget()
            source_widget.setWindowTitle("数据源管理测试")
            source_widget.resize(800, 600)
            source_widget.show()

            # 连接信号
            source_widget.source_selected.connect(
                lambda name: self.status_label.setText(f"选中数据源: {name}")
            )
            source_widget.source_configured.connect(
                lambda name, config: self.status_label.setText(f"配置数据源: {name}")
            )

            # 保存引用
            self.test_components['source_widget'] = source_widget

            self.status_label.setText("数据源管理组件测试完成")

        except Exception as e:
            self.show_error(f"测试数据源管理组件失败: {e}")

    def test_task_management(self):
        """测试下载任务管理组件"""
        if not UI_COMPONENTS_AVAILABLE:
            self.show_error("UI组件不可用")
            return

        try:
            self.status_label.setText("正在测试下载任务管理组件...")

            # 创建任务管理组件
            task_widget = DownloadTaskWidget()
            task_widget.setWindowTitle("下载任务管理测试")
            task_widget.resize(900, 600)
            task_widget.show()

            # 连接信号
            task_widget.task_started.connect(
                lambda name: self.status_label.setText(f"任务开始: {name}")
            )
            task_widget.task_paused.connect(
                lambda name: self.status_label.setText(f"任务暂停: {name}")
            )
            task_widget.task_stopped.connect(
                lambda name: self.status_label.setText(f"任务停止: {name}")
            )

            # 添加测试任务
            test_task = {
                'name': '测试下载任务',
                'source': 'tongdaxin',
                'asset_type': 'stock_a',
                'data_type': 'historical_kline',
                'symbols': ['000001', '000002'],
                'start_date': datetime.now() - timedelta(days=30),
                'end_date': datetime.now(),
                'status': 'pending',
                'progress': 0,
                'created_at': datetime.now()
            }
            task_widget.add_task(test_task)

            # 保存引用
            self.test_components['task_widget'] = task_widget

            self.status_label.setText("下载任务管理组件测试完成")

        except Exception as e:
            self.show_error(f"测试下载任务管理组件失败: {e}")

    def test_quality_monitor(self):
        """测试数据质量监控组件"""
        if not UI_COMPONENTS_AVAILABLE:
            self.show_error("UI组件不可用")
            return

        try:
            self.status_label.setText("正在测试数据质量监控组件...")

            # 创建质量监控组件
            quality_widget = DataQualityMonitorWidget()
            quality_widget.setWindowTitle("数据质量监控测试")
            quality_widget.resize(800, 600)
            quality_widget.show()

            # 保存引用
            self.test_components['quality_widget'] = quality_widget

            self.status_label.setText("数据质量监控组件测试完成")

        except Exception as e:
            self.show_error(f"测试数据质量监控组件失败: {e}")

    def test_missing_data_prompt(self):
        """测试智能数据缺失提示"""
        if not UI_COMPONENTS_AVAILABLE:
            self.show_error("UI组件不可用")
            return

        try:
            self.status_label.setText("正在测试智能数据缺失提示...")

            # 创建智能数据缺失集成
            integration = SmartDataMissingIntegration()

            # 模拟数据缺失检查
            def simulate_missing_check():
                if not integration.check_data_availability("TEST001"):
                    if CORE_AVAILABLE:
                        integration.trigger_missing_data_prompt(
                            "TEST001",
                            AssetType.STOCK_A,
                            DataType.HISTORICAL_KLINE,
                            "测试数据缺失"
                        )
                    else:
                        # 直接创建提示组件
                        prompt = SmartDataMissingPrompt()
                        prompt.show_missing_data_prompt(
                            "TEST001", None, None, "测试数据缺失"
                        )
                        self.test_components['missing_prompt'] = prompt

            # 延迟执行
            QTimer.singleShot(500, simulate_missing_check)

            # 保存引用
            self.test_components['integration'] = integration

            self.status_label.setText("智能数据缺失提示测试完成")

        except Exception as e:
            self.show_error(f"测试智能数据缺失提示失败: {e}")

    def test_management_dialog(self):
        """测试数据管理对话框"""
        if not UI_COMPONENTS_AVAILABLE:
            self.show_error("UI组件不可用")
            return

        try:
            self.status_label.setText("正在测试数据管理对话框...")

            # 创建数据管理对话框
            dialog = DataManagementDialog(self)

            # 连接信号
            dialog.data_downloaded.connect(
                lambda symbol, source: self.status_label.setText(f"数据下载: {symbol} from {source}")
            )
            dialog.source_configured.connect(
                lambda source, config: self.status_label.setText(f"数据源配置: {source}")
            )

            # 显示对话框
            dialog.show()

            # 保存引用
            self.test_components['management_dialog'] = dialog

            self.status_label.setText("数据管理对话框测试完成")

        except Exception as e:
            self.show_error(f"测试数据管理对话框失败: {e}")

    def test_quick_data_check(self):
        """测试快速数据检查"""
        if not UI_COMPONENTS_AVAILABLE:
            self.show_error("UI组件不可用")
            return

        try:
            self.status_label.setText("正在测试快速数据检查...")

            # 创建快速检查对话框
            quick_dialog = QuickDataCheckDialog(self.test_symbols, self)
            quick_dialog.exec_()

            self.status_label.setText("快速数据检查测试完成")

        except Exception as e:
            self.show_error(f"测试快速数据检查失败: {e}")

    def run_comprehensive_test(self):
        """运行综合测试"""
        self.status_label.setText("开始运行综合测试...")

        test_results = []

        # 测试各个组件
        tests = [
            ("数据管理主界面", self.test_main_widget),
            ("数据源管理组件", self.test_source_management),
            ("下载任务管理组件", self.test_task_management),
            ("数据质量监控组件", self.test_quality_monitor),
            ("智能数据缺失提示", self.test_missing_data_prompt),
            ("数据管理对话框", self.test_management_dialog),
        ]

        for test_name, test_func in tests:
            try:
                test_func()
                test_results.append(f"✅ {test_name}: 通过")
            except Exception as e:
                test_results.append(f"❌ {test_name}: 失败 - {str(e)}")

        # 显示测试结果
        result_message = "综合测试结果:\n\n" + "\n".join(test_results)

        # 计算通过率
        passed_count = len([r for r in test_results if "✅" in r])
        total_count = len(test_results)
        pass_rate = (passed_count / total_count) * 100

        result_message += f"\n\n通过率: {passed_count}/{total_count} ({pass_rate:.1f}%)"

        QMessageBox.information(self, "综合测试结果", result_message)

        self.status_label.setText(f"综合测试完成 - 通过率: {pass_rate:.1f}%")

    def show_error(self, message: str):
        """显示错误消息"""
        QMessageBox.critical(self, "测试错误", message)
        self.status_label.setText(f"测试失败: {message}")

        if logger:
            logger.error(f"UI测试错误: {message}")

    def closeEvent(self, event):
        """关闭事件"""
        # 关闭所有测试组件
        for component in self.test_components.values():
            if hasattr(component, 'close'):
                component.close()

        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    # 设置应用信息
    app.setApplicationName("FactorWeave-Quant 数据管理UI测试")
    app.setApplicationVersion("1.0")

    # 创建测试窗口
    test_window = DataManagementUITestWindow()
    test_window.show()

    # 显示启动信息
    startup_msg = """
FactorWeave-Quant 数据管理UI测试系统

功能说明:
• 测试数据管理主界面的完整功能
• 验证数据源管理组件的交互
• 检查下载任务管理的流程
• 评估数据质量监控的效果
• 测试智能数据缺失提示机制
• 验证数据管理对话框集成

点击相应按钮开始测试各个组件。
"""

    QMessageBox.information(test_window, "欢迎使用", startup_msg)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
