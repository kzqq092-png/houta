#!/usr/bin/env python3
"""
主窗口模块

使用Mixin模式组合各种功能模块，实现模块化的主窗口
"""

import sys
import traceback
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QStatusBar, QApplication, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSlot

# 导入mixin模块
from .mixins import (
    StockManagementMixin,
    ChartAnalysisMixin,
    StrategyBacktestMixin,
    SettingsToolsMixin,
    OptimizationFeaturesMixin
)

# 使用系统统一组件
from core.adapters import get_logger, get_config, get_data_manager


class TradingMainWindow(
    QMainWindow,
    StockManagementMixin,
    ChartAnalysisMixin,
    StrategyBacktestMixin,
    SettingsToolsMixin,
    OptimizationFeaturesMixin
):
    """
    主交易窗口类

    通过多重继承组合各种功能mixin，实现模块化设计
    """

    def __init__(self):
        """初始化主窗口"""
        try:
            # 初始化所有父类
            QMainWindow.__init__(self)
            StockManagementMixin.__init__(self)
            ChartAnalysisMixin.__init__(self)
            StrategyBacktestMixin.__init__(self)
            SettingsToolsMixin.__init__(self)
            OptimizationFeaturesMixin.__init__(self)

            # 获取系统组件
            self.logger = get_logger(__name__)
            self.config = get_config()
            self.data_manager = get_data_manager()

            self.logger.info("开始初始化主窗口")

            # 窗口基本设置
            self.setWindowTitle("HIkyuu量化交易系统 v2.5.6")
            self.setGeometry(100, 100, 1400, 900)

            # 初始化UI
            self.init_ui()

            # 初始化数据
            self.init_data()

            # 连接信号
            self.connect_signals()

            self.logger.info("主窗口初始化完成")

        except Exception as e:
            error_msg = f"主窗口初始化失败: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            QMessageBox.critical(None, "初始化错误", error_msg)
            sys.exit(1)

    def init_ui(self):
        """初始化用户界面"""
        try:
            self.logger.info("初始化用户界面")

            # 创建中央控件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            # 创建主布局
            main_layout = QHBoxLayout(central_widget)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(5)

            # 创建分割器
            main_splitter = QSplitter(Qt.Horizontal)
            main_layout.addWidget(main_splitter)

            # 创建左侧面板（股票管理）
            left_panel = self.create_left_panel()
            left_panel.setMaximumWidth(350)
            left_panel.setMinimumWidth(250)
            main_splitter.addWidget(left_panel)

            # 创建中间面板（图表分析）
            middle_panel = self.create_middle_panel()
            main_splitter.addWidget(middle_panel)

            # 创建右侧面板（策略回测）
            right_panel = self.create_right_panel()
            right_panel.setMaximumWidth(400)
            right_panel.setMinimumWidth(300)
            main_splitter.addWidget(right_panel)

            # 设置分割器比例
            main_splitter.setSizes([300, 700, 350])

            # 创建菜单栏
            self.create_menu_bar()

            # 创建状态栏
            self.create_status_bar()

            self.logger.info("用户界面初始化完成")

        except Exception as e:
            self.logger.error(f"初始化用户界面失败: {str(e)}")
            self.logger.error(traceback.format_exc())

    def create_right_panel(self) -> QWidget:
        """创建右侧策略面板"""
        try:
            self.logger.info("创建右侧策略面板")

            right_panel = QWidget()
            right_layout = QVBoxLayout(right_panel)
            right_layout.setContentsMargins(5, 5, 5, 5)
            right_layout.setSpacing(5)

            # 创建策略控制区域
            self.create_strategy_controls(right_layout)

            # 添加分析结果显示区域
            from PyQt5.QtWidgets import QTextEdit
            self.analysis_results = QTextEdit()
            self.analysis_results.setReadOnly(True)
            self.analysis_results.setPlaceholderText("分析结果将显示在这里...")
            right_layout.addWidget(self.analysis_results)

            return right_panel

        except Exception as e:
            self.logger.error(f"创建右侧策略面板失败: {str(e)}")
            return QWidget()

    def create_menu_bar(self):
        """创建菜单栏"""
        try:
            self.logger.info("创建菜单栏")

            menubar = self.menuBar()

            # 文件菜单
            file_menu = menubar.addMenu('文件')

            # 新建
            new_action = file_menu.addAction('新建')
            new_action.setShortcut('Ctrl+N')
            new_action.triggered.connect(self.new_file)

            # 打开
            open_action = file_menu.addAction('打开')
            open_action.setShortcut('Ctrl+O')
            open_action.triggered.connect(self.open_file)

            # 保存
            save_action = file_menu.addAction('保存')
            save_action.setShortcut('Ctrl+S')
            save_action.triggered.connect(self.save_file)

            file_menu.addSeparator()

            # 退出
            exit_action = file_menu.addAction('退出')
            exit_action.setShortcut('Ctrl+Q')
            exit_action.triggered.connect(self.close)

            # 数据菜单
            data_menu = menubar.addMenu('数据')

            # 更新股票列表
            update_stocks_action = data_menu.addAction('更新股票列表')
            update_stocks_action.triggered.connect(self.update_stock_list)

            # 导出股票列表
            export_stocks_action = data_menu.addAction('导出股票列表')
            export_stocks_action.triggered.connect(self.export_stock_list)

            # 策略菜单
            strategy_menu = menubar.addMenu('策略')

            # 刷新策略
            refresh_strategies_action = strategy_menu.addAction('刷新策略列表')
            refresh_strategies_action.triggered.connect(self.refresh_strategy_list)

            # 导出回测结果
            export_backtest_action = strategy_menu.addAction('导出回测结果')
            export_backtest_action.triggered.connect(self.export_backtest_results)

            # 工具菜单
            tools_menu = menubar.addMenu('工具')

            # 计算器
            calculator_action = tools_menu.addAction('计算器')
            calculator_action.triggered.connect(self.show_calculator)

            # 单位转换器
            converter_action = tools_menu.addAction('单位转换器')
            converter_action.triggered.connect(self.show_converter)

            tools_menu.addSeparator()

            # 性能优化
            optimize_action = tools_menu.addAction('性能优化')
            optimize_action.triggered.connect(self.optimize_performance)

            # 系统诊断
            diagnostics_action = tools_menu.addAction('系统诊断')
            diagnostics_action.triggered.connect(self.run_diagnostics)

            # 设置菜单
            settings_menu = menubar.addMenu('设置')

            # 系统设置
            settings_action = settings_menu.addAction('系统设置')
            settings_action.triggered.connect(self.show_settings_dialog)

            # 导入设置
            import_settings_action = settings_menu.addAction('导入设置')
            import_settings_action.triggered.connect(self.import_settings)

            # 导出设置
            export_settings_action = settings_menu.addAction('导出设置')
            export_settings_action.triggered.connect(self.export_settings)

            settings_menu.addSeparator()

            # 重置设置
            reset_settings_action = settings_menu.addAction('重置设置')
            reset_settings_action.triggered.connect(self.reset_settings)

            # 帮助菜单
            help_menu = menubar.addMenu('帮助')

            # 系统信息
            system_info_action = help_menu.addAction('系统信息')
            system_info_action.triggered.connect(self.show_system_info)

            # 导出日志
            export_logs_action = help_menu.addAction('导出日志')
            export_logs_action.triggered.connect(self.export_logs)

            help_menu.addSeparator()

            # 关于
            about_action = help_menu.addAction('关于')
            about_action.triggered.connect(self.show_about_dialog)

        except Exception as e:
            self.logger.error(f"创建菜单栏失败: {str(e)}")

    def create_status_bar(self):
        """创建状态栏"""
        try:
            self.logger.info("创建状态栏")

            self.status_bar = self.statusBar()
            self.status_bar.showMessage("就绪")

        except Exception as e:
            self.logger.error(f"创建状态栏失败: {str(e)}")

    def init_data(self):
        """初始化数据"""
        try:
            self.logger.info("初始化数据")

            # 加载收藏股票
            self.load_favorites()

            # 预加载股票数据
            self.preload_data()

        except Exception as e:
            self.logger.error(f"初始化数据失败: {str(e)}")

    def preload_data(self):
        """预加载数据"""
        try:
            self.logger.info("预加载数据")

            # 更新股票列表
            self.update_stock_list()

        except Exception as e:
            self.logger.error(f"预加载数据失败: {str(e)}")

    def connect_signals(self):
        """连接信号"""
        try:
            self.logger.info("连接信号")

            # 这里可以连接各种信号

        except Exception as e:
            self.logger.error(f"连接信号失败: {str(e)}")

    def new_file(self):
        """新建文件"""
        try:
            self.logger.info("新建文件")
            # 实现新建文件逻辑

        except Exception as e:
            self.logger.error(f"新建文件失败: {str(e)}")

    def open_file(self):
        """打开文件"""
        try:
            self.logger.info("打开文件")
            # 实现打开文件逻辑

        except Exception as e:
            self.logger.error(f"打开文件失败: {str(e)}")

    def save_file(self):
        """保存文件"""
        try:
            self.logger.info("保存文件")
            # 实现保存文件逻辑

        except Exception as e:
            self.logger.error(f"保存文件失败: {str(e)}")

    def get_kdata(self, stock_code: str):
        """获取股票K线数据"""
        try:
            self.logger.debug(f"获取股票K线数据: {stock_code}")

            # 这里应该调用数据管理器获取真实数据
            if hasattr(self.data_manager, 'get_kdata'):
                return self.data_manager.get_kdata(stock_code)
            else:
                # 返回模拟数据
                import pandas as pd
                import numpy as np

                dates = pd.date_range('2023-01-01', periods=100, freq='D')
                data = {
                    'open': np.random.randn(100).cumsum() + 100,
                    'high': np.random.randn(100).cumsum() + 105,
                    'low': np.random.randn(100).cumsum() + 95,
                    'close': np.random.randn(100).cumsum() + 100,
                    'volume': np.random.randint(1000, 10000, 100)
                }

                return pd.DataFrame(data, index=dates)

        except Exception as e:
            self.logger.error(f"获取股票K线数据失败: {str(e)}")
            return None

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            self.logger.info("窗口关闭事件")

            # 保存设置
            self.save_favorites()

            # 清理资源
            self.cleanup_memory()

            event.accept()

        except Exception as e:
            self.logger.error(f"窗口关闭处理失败: {str(e)}")
            event.accept()


def main():
    """主函数"""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("HIkyuu量化交易系统")
        app.setApplicationVersion("2.5.6")

        # 创建主窗口
        window = TradingMainWindow()
        window.show()

        # 运行应用
        sys.exit(app.exec_())

    except Exception as e:
        print(f"应用启动失败: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
