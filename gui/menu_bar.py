"""
Menu bar for the trading system

This module contains the menu bar implementation for the trading system.
"""

from PyQt5.QtWidgets import (
    QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
    QInputDialog, QShortcut, QDialog, QActionGroup
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QIcon
import traceback
from utils.theme import get_theme_manager
from utils.log_util import log_structured


class MainMenuBar(QMenuBar):
    """主菜单栏"""

    def __init__(self, parent=None):
        """初始化菜单栏

        Args:
            parent: 父窗口
        """
        try:
            super().__init__(parent)

            # 初始化日志管理器
            if hasattr(parent, 'log_manager'):
                self.log_manager = parent.log_manager
            else:
                from core.logger import LogManager
                self.log_manager = LogManager()

            # 初始化主题管理器
            self.theme_manager = get_theme_manager()

            # 初始化UI
            self.init_ui()

            log_structured(self.log_manager, "menu_bar_init", level="info", status="success")

        except Exception as e:
            print(f"初始化菜单栏失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"初始化菜单栏失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def init_ui(self):
        """初始化菜单栏"""
        self.parent = self.parentWidget()
        self.parent.setWindowIcon(QIcon("icons/logo.png"))
        # 创建菜单项
        self.file_menu = self.addMenu("文件(&F)")
        self.edit_menu = self.addMenu("编辑(&E)")
        self.view_menu = self.addMenu("视图(&V)")
        self.analysis_menu = self.addMenu("分析(&A)")
        self.strategy_menu = self.addMenu("策略(&S)")
        self.data_menu = self.addMenu("数据(&D)")
        self.tools_menu = self.addMenu("工具(&T)")
        self.debug_menu = self.addMenu("调试(&G)")
        self.help_menu = self.addMenu("帮助(&H)")
        self.init_file_menu()
        self.init_edit_menu()
        self.init_view_menu()
        self.init_analysis_menu()
        self.init_strategy_menu()
        self.init_data_menu()
        self.init_tools_menu()
        self.init_debug_menu()
        self.init_help_menu()

    def init_file_menu(self):
        """初始化文件菜单"""
        try:
            # 新建
            self.new_action = QAction(QIcon("icons/new.png"), "新建(&N)", self)
            self.new_action.setShortcut("Ctrl+N")
            self.new_action.setStatusTip("创建新的策略")
            self.file_menu.addAction(self.new_action)

            # 打开
            self.open_action = QAction(QIcon("icons/open.png"), "打开(&O)", self)
            self.open_action.setShortcut("Ctrl+O")
            self.open_action.setStatusTip("打开策略文件")
            self.file_menu.addAction(self.open_action)

            # 保存
            self.save_action = QAction(QIcon("icons/save.png"), "保存(&S)", self)
            self.save_action.setShortcut("Ctrl+S")
            self.save_action.setStatusTip("保存当前策略")
            self.file_menu.addAction(self.save_action)

            self.file_menu.addSeparator()

            # 最近打开的文件
            self.recent_menu = self.file_menu.addMenu("最近打开的文件")

            self.file_menu.addSeparator()

            # 退出
            self.exit_action = QAction("退出(&X)", self)
            self.exit_action.setShortcut("Alt+F4")
            self.exit_action.setStatusTip("退出程序")
            self.file_menu.addAction(self.exit_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化文件菜单失败: {str(e)}")

    def init_edit_menu(self):
        """初始化编辑菜单"""
        try:
            # 撤销
            self.undo_action = QAction(QIcon("icons/undo.png"), "撤销(&U)", self)
            self.undo_action.setShortcut("Ctrl+Z")
            self.edit_menu.addAction(self.undo_action)

            # 重做
            self.redo_action = QAction(QIcon("icons/redo.png"), "重做(&R)", self)
            self.redo_action.setShortcut("Ctrl+Y")
            self.edit_menu.addAction(self.redo_action)

            self.edit_menu.addSeparator()

            # 复制
            self.copy_action = QAction("复制(&C)", self)
            self.copy_action.setShortcut("Ctrl+C")
            self.edit_menu.addAction(self.copy_action)

            # 粘贴
            self.paste_action = QAction("粘贴(&V)", self)
            self.paste_action.setShortcut("Ctrl+V")
            self.edit_menu.addAction(self.paste_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化编辑菜单失败: {str(e)}")

    def init_view_menu(self):
        """初始化视图菜单"""
        try:
            # 工具栏
            self.toolbar_action = QAction("工具栏", self)
            self.toolbar_action.setCheckable(True)
            self.toolbar_action.setChecked(True)
            self.view_menu.addAction(self.toolbar_action)

            # 状态栏
            self.statusbar_action = QAction("状态栏", self)
            self.statusbar_action.setCheckable(True)
            self.statusbar_action.setChecked(True)
            self.view_menu.addAction(self.statusbar_action)

            self.view_menu.addSeparator()

            # 移除主题切换子菜单，合并到设置
            # self.theme_menu = self.view_menu.addMenu("主题")
            # self.light_theme_action = QAction("浅色", self)
            # self.dark_theme_action = QAction("深色", self)
            # self.gradient_theme_action = QAction("渐变", self)
            # self.theme_menu.addAction(self.light_theme_action)
            # self.theme_menu.addAction(self.dark_theme_action)
            # self.theme_menu.addAction(self.gradient_theme_action)
            # self.light_theme_action.triggered.connect(lambda: self.parent.set_theme_by_menu('light'))
            # self.dark_theme_action.triggered.connect(lambda: self.parent.set_theme_by_menu('dark'))
            # self.gradient_theme_action.triggered.connect(lambda: self.parent.set_theme_by_menu('gradient'))

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化视图菜单失败: {str(e)}")

    def init_analysis_menu(self):
        """初始化分析菜单"""
        try:
            # 分析
            self.analyze_action = QAction(
                QIcon("icons/analyze.png"), "分析", self)
            self.analyze_action.setStatusTip("分析当前股票")
            self.analysis_menu.addAction(self.analyze_action)

            # 回测
            self.backtest_action = QAction(
                QIcon("icons/backtest.png"), "回测", self)
            self.backtest_action.setStatusTip("回测当前策略")
            self.analysis_menu.addAction(self.backtest_action)

            # 优化
            self.optimize_action = QAction(
                QIcon("icons/optimize.png"), "优化", self)
            self.optimize_action.setStatusTip("优化策略参数")
            self.analysis_menu.addAction(self.optimize_action)

            self.analysis_menu.addSeparator()

            # 批量/分布式分析
            self.batch_analysis_action = QAction(QIcon("icons/batch.png"), "批量/分布式分析", self)
            self.batch_analysis_action.setStatusTip("批量/分布式回测与分析")
            self.analysis_menu.addAction(self.batch_analysis_action)

            # 节点管理器
            self.node_manager_action = QAction(QIcon("icons/node.png"), "节点管理器", self)
            self.node_manager_action.setStatusTip("管理分布式计算节点")
            self.analysis_menu.addAction(self.node_manager_action)

            # 云API管理器
            self.cloud_api_action = QAction(QIcon("icons/cloud.png"), "云API管理器", self)
            self.cloud_api_action.setStatusTip("管理云端API接口")
            self.analysis_menu.addAction(self.cloud_api_action)

            # 指标市场
            self.indicator_market_action = QAction(QIcon("icons/market.png"), "指标市场", self)
            self.indicator_market_action.setStatusTip("浏览和下载技术指标")
            self.analysis_menu.addAction(self.indicator_market_action)

            self.analysis_menu.addSeparator()

            # 优化相关菜单
            optimization_menu = self.analysis_menu.addMenu("优化系统")

            self.optimization_dashboard_action = QAction(QIcon("icons/dashboard.png"), "优化仪表板", self)
            self.optimization_dashboard_action.setStatusTip("显示优化仪表板")
            optimization_menu.addAction(self.optimization_dashboard_action)

            self.one_click_optimize_action = QAction(QIcon("icons/one_click.png"), "一键优化", self)
            self.one_click_optimize_action.setStatusTip("执行一键优化")
            optimization_menu.addAction(self.one_click_optimize_action)

            self.smart_optimize_action = QAction(QIcon("icons/smart.png"), "智能优化", self)
            self.smart_optimize_action.setStatusTip("执行智能优化")
            optimization_menu.addAction(self.smart_optimize_action)

            self.optimization_status_action = QAction(QIcon("icons/status.png"), "优化状态", self)
            self.optimization_status_action.setStatusTip("查看优化状态")
            optimization_menu.addAction(self.optimization_status_action)

            # 版本管理和性能评估
            self.version_manager_action = QAction(QIcon("icons/version.png"), "版本管理", self)
            self.version_manager_action.setStatusTip("管理策略版本")
            self.analysis_menu.addAction(self.version_manager_action)

            self.performance_evaluation_action = QAction(QIcon("icons/performance.png"), "性能评估", self)
            self.performance_evaluation_action.setStatusTip("评估策略性能")
            self.analysis_menu.addAction(self.performance_evaluation_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化分析菜单失败: {str(e)}")

    def init_strategy_menu(self):
        """初始化策略菜单"""
        try:
            # 策略管理
            self.strategy_manager_action = QAction(QIcon("icons/strategy.png"), "策略管理器", self)
            self.strategy_manager_action.setStatusTip("打开策略管理器")
            self.strategy_menu.addAction(self.strategy_manager_action)

            self.strategy_menu.addSeparator()

            # 策略创建
            self.create_strategy_action = QAction("创建新策略", self)
            self.create_strategy_action.setStatusTip("创建新的交易策略")
            self.strategy_menu.addAction(self.create_strategy_action)

            # 策略导入
            self.import_strategy_action = QAction("导入策略", self)
            self.import_strategy_action.setStatusTip("从文件导入策略")
            self.strategy_menu.addAction(self.import_strategy_action)

            # 策略导出
            self.export_strategy_action = QAction("导出策略", self)
            self.export_strategy_action.setStatusTip("导出策略到文件")
            self.strategy_menu.addAction(self.export_strategy_action)

            self.strategy_menu.addSeparator()

            # 策略回测
            self.strategy_backtest_action = QAction("策略回测", self)
            self.strategy_backtest_action.setStatusTip("对策略进行历史回测")
            self.strategy_menu.addAction(self.strategy_backtest_action)

            # 策略优化
            self.strategy_optimize_action = QAction("策略优化", self)
            self.strategy_optimize_action.setStatusTip("优化策略参数")
            self.strategy_menu.addAction(self.strategy_optimize_action)

            # 连接信号
            if hasattr(self.parent, 'show_strategy_manager'):
                self.strategy_manager_action.triggered.connect(self.parent.show_strategy_manager)
            if hasattr(self.parent, 'create_new_strategy'):
                self.create_strategy_action.triggered.connect(self.parent.create_new_strategy)
            if hasattr(self.parent, 'import_strategy'):
                self.import_strategy_action.triggered.connect(self.parent.import_strategy)
            if hasattr(self.parent, 'export_strategy'):
                self.export_strategy_action.triggered.connect(self.parent.export_strategy)
            if hasattr(self.parent, 'backtest_strategy'):
                self.strategy_backtest_action.triggered.connect(self.parent.backtest_strategy)
            if hasattr(self.parent, 'optimize_strategy'):
                self.strategy_optimize_action.triggered.connect(self.parent.optimize_strategy)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化策略菜单失败: {str(e)}")

    def init_data_menu(self):
        """初始化数据菜单（含数据源切换）"""
        try:
            # 数据源子菜单
            self.data_source_menu = self.data_menu.addMenu("数据源切换")
            self.data_source_hikyuu = QAction("Hikyuu", self)
            self.data_source_eastmoney = QAction("东方财富", self)
            self.data_source_sina = QAction("新浪", self)
            self.data_source_tonghuashun = QAction("同花顺", self)
            self.data_source_menu.addAction(self.data_source_hikyuu)
            self.data_source_menu.addAction(self.data_source_eastmoney)
            self.data_source_menu.addAction(self.data_source_sina)
            self.data_source_menu.addAction(self.data_source_tonghuashun)
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化数据菜单失败: {str(e)}")

    def init_tools_menu(self):
        """初始化工具菜单"""
        try:
            # 计算器
            self.calculator_action = QAction(QIcon("icons/calculator.png"), "计算器", self)
            self.calculator_action.setStatusTip("打开计算器")
            self.tools_menu.addAction(self.calculator_action)

            # 单位转换器
            self.converter_action = QAction(QIcon("icons/converter.png"), "单位转换器", self)
            self.converter_action.setStatusTip("打开单位转换器")
            self.tools_menu.addAction(self.converter_action)

            self.tools_menu.addSeparator()

            # 插件管理器
            self.plugin_manager_action = QAction(QIcon("icons/plugin.png"), "插件管理器", self)
            self.plugin_manager_action.setStatusTip("管理系统插件")
            self.tools_menu.addAction(self.plugin_manager_action)

            self.tools_menu.addSeparator()

            # 语言设置
            self.language_menu = self.tools_menu.addMenu("语言设置")
            self.language_menu.setIcon(QIcon("icons/language.png"))

            # 创建语言动作组，确保互斥选择
            self.language_group = QActionGroup(self)
            self.language_group.setExclusive(True)

            # 添加支持的语言选项
            self.language_actions = {}
            languages = {
                "zh_CN": "简体中文",
                "en_US": "English",
                "zh_TW": "繁體中文",
                "ja_JP": "日本語"
            }

            for lang_code, lang_name in languages.items():
                action = QAction(lang_name, self)
                action.setCheckable(True)
                action.setData(lang_code)

                # 添加到动作组
                self.language_group.addAction(action)
                self.language_menu.addAction(action)
                self.language_actions[lang_code] = action

            self.tools_menu.addSeparator()

            # 设置
            self.settings_action = QAction(QIcon("icons/settings.png"), "设置", self)
            self.settings_action.setStatusTip("打开系统设置")
            self.tools_menu.addAction(self.settings_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化工具菜单失败: {str(e)}")

    def init_debug_menu(self):
        """初始化调试菜单，添加显示/隐藏日志菜单项"""
        try:
            self.toggle_log_action = QAction("显示/隐藏日志", self)
            self.toggle_log_action.setStatusTip("显示或隐藏日志输出区")
            self.toggle_log_action.triggered.connect(
                lambda: self.parent.toggle_log_panel())
            self.debug_menu.addAction(self.toggle_log_action)
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化调试菜单失败: {str(e)}")

    def init_help_menu(self):
        """初始化帮助菜单"""
        try:
            # 帮助文档
            self.help_action = QAction("帮助文档", self)
            self.help_action.setStatusTip("打开帮助文档")
            self.help_menu.addAction(self.help_action)

            # 检查更新
            self.update_action = QAction("检查更新", self)
            self.update_action.setStatusTip("检查新版本")
            self.help_menu.addAction(self.update_action)

            self.help_menu.addSeparator()

            # 关于
            self.about_action = QAction("关于", self)
            self.about_action.setStatusTip("关于本程序")
            self.help_menu.addAction(self.about_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化帮助菜单失败: {str(e)}")

    def log_message(self, message: str, level: str = "info") -> None:
        """记录日志消息，统一调用主窗口或日志管理器"""
        try:
            parent = self.parentWidget()
            if parent and hasattr(parent, 'log_message'):
                parent.log_message(message, level)
            elif hasattr(self, 'log_manager'):
                # 直接用log_manager
                level = level.upper()
                if level == "ERROR":
                    self.log_manager.error(message)
                elif level == "WARNING":
                    self.log_manager.warning(message)
                elif level == "DEBUG":
                    self.log_manager.debug(message)
                else:
                    self.log_manager.info(message)
            else:
                print(f"[LOG][{level}] {message}")
        except Exception as e:
            print(f"记录日志失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"记录日志失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def new_file(self):
        """Create a new file"""
        # TODO: Implement new file creation
        pass

    def open_file(self):
        """Open a file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "打开文件",
                "",
                "All Files (*);;Python Files (*.py);;Text Files (*.txt)"
            )

            if file_path:
                # TODO: Implement file opening
                pass

        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件失败: {str(e)}")

    def save_file(self):
        """Save current file"""
        # TODO: Implement file saving
        pass

    def save_file_as(self):
        """Save current file with new name"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "另存为",
                "",
                "All Files (*);;Python Files (*.py);;Text Files (*.txt)"
            )

            if file_path:
                # TODO: Implement file saving
                pass

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")

    def import_data(self):
        """Import data"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "导入数据",
                "",
                "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
            )

            if file_path:
                # TODO: Implement data import
                pass

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入数据失败: {str(e)}")

    def export_data(self):
        """Export data"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出数据",
                "",
                "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
            )

            if file_path:
                # TODO: Implement data export
                pass

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出数据失败: {str(e)}")

    def undo(self):
        """Undo last action"""
        # TODO: Implement undo
        pass

    def redo(self):
        """Redo last undone action"""
        # TODO: Implement redo
        pass

    def cut(self):
        """Cut selected content"""
        # TODO: Implement cut
        pass

    def copy(self):
        """Copy selected content"""
        # TODO: Implement copy
        pass

    def paste(self):
        """Paste content"""
        # TODO: Implement paste
        pass

    def select_all(self):
        """Select all content"""
        # TODO: Implement select all
        pass

    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.window().isFullScreen():
            self.window().showNormal()
        else:
            self.window().showFullScreen()

    def analyze(self):
        """Perform analysis"""
        # TODO: Implement analysis
        pass

    def backtest(self):
        """Run backtest"""
        # TODO: Implement backtest
        pass

    def optimize(self):
        """Optimize parameters"""
        # TODO: Implement optimization
        pass

    def pattern_recognition(self):
        """Perform pattern recognition"""
        # TODO: Implement pattern recognition
        pass

    def wave_analysis(self):
        """Perform wave analysis"""
        # TODO: Implement wave analysis
        pass

    def risk_analysis(self):
        """Perform risk analysis"""
        # TODO: Implement risk analysis
        pass

    def show_settings(self):
        """Show settings dialog"""
        if hasattr(self.parent(), 'show_settings'):
            self.parent().show_settings()

    def show_calculator(self):
        """Show calculator using the new Calculator tool"""
        try:
            from .tools import Calculator
            Calculator.show_calculator(self)
            self.log_message("打开计算器")
        except Exception as e:
            error_msg = f"显示计算器失败: {str(e)}"
            self.log_message(error_msg, "error")

    def show_converter(self):
        """Show unit converter using the new UnitConverter tool"""
        try:
            from .tools import UnitConverter
            UnitConverter.show_converter(self)
            self.log_message("打开单位转换器")
        except Exception as e:
            error_msg = f"显示单位转换器失败: {str(e)}"
            self.log_message(error_msg, "error")

    def show_documentation(self):
        """Show documentation"""
        # TODO: Implement documentation viewer
        pass

    def apply_theme(self, theme_manager):
        """根据主题优化菜单栏样式"""
        colors = theme_manager.get_theme_colors()
        menu_bg = colors.get('background', '#181c24')
        menu_text = colors.get('text', '#e0e6ed')
        menu_selected = colors.get('highlight', '#1976d2')
        menu_hover = colors.get('hover_bg', '#23293a')
        menu_border = colors.get('border', '#23293a')

        # 优化菜单栏样式，解决重叠问题
        self.setStyleSheet(f'''
            QMenuBar {{
                background: {menu_bg};
                color: {menu_text};
                border-bottom: 1px solid {menu_border};
                font-weight: bold;
                font-size: 12px;
                spacing: 8px;  /* 增加菜单项间距 */
                padding: 4px 8px;  /* 增加内边距 */
                margin: 0px;
                height: 32px;  /* 稍微增加高度 */
                min-height: 32px;  /* 确保最小高度 */
            }}
            QMenuBar::item {{
                background: transparent;
                color: {menu_text};
                padding: 6px 16px;  /* 增加内边距避免重叠 */
                margin: 2px 4px;    /* 增加外边距分隔菜单项 */
                border-radius: 4px;
                min-width: 80px;    /* 增加最小宽度 */
                max-width: 120px;   /* 限制最大宽度 */
                text-align: center;
                border: 1px solid transparent;  /* 添加透明边框 */
            }}
            QMenuBar::item:selected {{
                background: {menu_selected};
                color: white;
                border: 1px solid {menu_selected};
            }}
            QMenuBar::item:pressed {{
                background: {menu_selected};
                color: white;
                border: 1px solid {menu_selected};
            }}
            QMenuBar::item:hover {{
                background: {menu_hover};
                color: white;
                border: 1px solid {menu_hover};
            }}
            QMenu {{
                background: {menu_bg};
                color: {menu_text};
                border: 1px solid {menu_border};
                font-size: 12px;
                padding: 4px;  /* 增加内边距 */
                margin: 1px;
                border-radius: 4px;  /* 添加圆角 */
            }}
            QMenu::item {{
                background: transparent;
                color: {menu_text};
                padding: 8px 24px;  /* 增加内边距 */
                margin: 1px 2px;    /* 增加外边距 */
                border-radius: 3px;
                min-height: 20px;   /* 确保最小高度 */
            }}
            QMenu::item:selected {{
                background: {menu_selected};
                color: white;
            }}
            QMenu::item:disabled {{
                color: #888;
                background: transparent;
            }}
            QMenu::separator {{
                height: 1px;
                background: {menu_border};
                margin: 6px 4px;  /* 增加分隔符边距 */
            }}
        ''')
