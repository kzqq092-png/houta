from loguru import logger
"""
Menu bar for the trading system

This module contains the menu bar implementation for the trading system.
"""

from PyQt5.QtWidgets import (
    QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
    QInputDialog, QShortcut, QDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QIcon
import traceback
from utils.theme import get_theme_manager
# log_structured已替换为直接的logger调用


class MainMenuBar(QMenuBar):
    """主菜单栏"""

    def __init__(self, coordinator=None, parent=None):
        """初始化菜单栏

        Args:
            coordinator: 主窗口协调器实例
            parent: 父窗口
        """
        try:
            super().__init__(parent)

            # 保存coordinator引用
            self.coordinator = coordinator
            # 初始化主题管理器
            self.theme_manager = get_theme_manager()

            # 初始化UI
            self.init_ui()

            logger.info("menu_bar_init", status="success")

        except Exception as e:
            logger.info(f"初始化菜单栏失败: {str(e)}")
            if True:  # 使用Loguru日志
                logger.error(f"初始化菜单栏失败: {str(e)}")
                logger.error(traceback.format_exc())

    def init_ui(self):
        """初始化菜单栏"""
        parent_widget = self.parentWidget()
        if parent_widget:
            parent_widget.setWindowIcon(QIcon("icons/logo.png"))
        # 创建菜单项
        self.file_menu = self.addMenu("文件(&F)")
        self.edit_menu = self.addMenu("编辑(&E)")
        self.view_menu = self.addMenu("视图(&V)")
        self.analysis_menu = self.addMenu("分析(&A)")
        self.strategy_menu = self.addMenu("策略(&S)")
        self.data_menu = self.addMenu("数据(&D)")
        self.tools_menu = self.addMenu("工具(&T)")
        self.performance_menu = self.addMenu("性能监控(&P)")
        self.advanced_menu = self.addMenu("高级功能(&X)")
        self.debug_menu = self.addMenu("调试(&G)")
        self.help_menu = self.addMenu("帮助(&H)")
        self.init_file_menu()
        self.init_edit_menu()
        self.init_view_menu()
        self.init_analysis_menu()
        self.init_strategy_menu()
        self.init_data_menu()
        self.init_tools_menu()
        self.init_performance_menu()
        self.init_advanced_menu()
        self.init_debug_menu()
        self.init_help_menu()

        # 所有菜单创建完成后，统一连接信号
        self.connect_signals()

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

            # 注意：信号连接已在connect_signals方法中统一处理，这里不再重复连接

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化文件菜单失败: {str(e)}")

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

            # 注意：信号连接已在connect_signals方法中统一处理，这里不再重复连接

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化编辑菜单失败: {str(e)}")

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

            # 专业回测面板 - 已合并到分析菜单的专业回测中
            # self.backtest_panel_action = QAction("专业回测面板", self)
            # self.backtest_panel_action.setCheckable(True)
            # self.backtest_panel_action.setChecked(False)
            # self.backtest_panel_action.setStatusTip("显示/隐藏专业回测面板")
            # self.view_menu.addAction(self.backtest_panel_action)

            self.view_menu.addSeparator()

            # 刷新
            self.refresh_action = QAction("刷新", self)
            self.refresh_action.setStatusTip("刷新当前数据")
            self.view_menu.addAction(self.refresh_action)

            self.view_menu.addSeparator()

            # 主题切换子菜单
            self.theme_menu = self.view_menu.addMenu("主题")
            self.default_theme_action = QAction("默认主题", self)
            self.light_theme_action = QAction("浅色主题", self)
            self.dark_theme_action = QAction("深色主题", self)
            self.theme_menu.addAction(self.default_theme_action)
            self.theme_menu.addAction(self.light_theme_action)
            self.theme_menu.addAction(self.dark_theme_action)

            # 性能仪表板已移至顶级性能监控菜单
            # 保留注释以记录移除原因

            # 连接信号到coordinator
            if self.coordinator:
                # 视图菜单和刷新功能的信号连接已移至统一的信号连接处理中，避免重复连接

                # 主题切换信号连接已移至统一的信号连接处理中，避免重复连接

                # 性能仪表板信号连接已移至性能监控菜单
                pass

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化视图菜单失败: {str(e)}")

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

            # 专业回测（合并了专业回测系统和专业回测面板）
            self.professional_backtest_action = QAction(
                QIcon("icons/backtest.png"), "专业回测", self)
            self.professional_backtest_action.setStatusTip("打开专业回测功能（支持面板和窗口模式）")
            self.professional_backtest_action.setShortcut("Ctrl+Shift+B")
            self.analysis_menu.addAction(self.professional_backtest_action)

            # 优化
            self.optimize_action = QAction(
                QIcon("icons/optimize.png"), "优化", self)
            self.optimize_action.setStatusTip("优化策略参数")
            self.analysis_menu.addAction(self.optimize_action)

            self.analysis_menu.addSeparator()

            # 批量/分布式分析
            self.batch_analysis_action = QAction(
                QIcon("icons/batch.png"), "批量/分布式分析", self)
            self.batch_analysis_action.setStatusTip("批量/分布式回测与分析")
            self.analysis_menu.addAction(self.batch_analysis_action)
        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化分析菜单失败: {str(e)}")

    def init_strategy_menu(self):
        """初始化策略菜单"""
        try:
            # 策略管理
            self.strategy_manager_action = QAction(
                QIcon("icons/strategy.png"), "策略管理器", self)
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

            # 策略回测 - 已整合到分析菜单的智能回测中
            # self.strategy_backtest_action = QAction("策略回测", self)
            # self.strategy_backtest_action.setStatusTip("对策略进行历史回测")
            # self.strategy_menu.addAction(self.strategy_backtest_action)

            # 策略优化
            self.strategy_optimize_action = QAction("策略优化", self)
            self.strategy_optimize_action.setStatusTip("优化策略参数")
            self.strategy_menu.addAction(self.strategy_optimize_action)

            self.strategy_menu.addSeparator()

            # 交易监控
            self.trading_monitor_action = QAction(
                QIcon("icons/monitor.png"), "交易监控", self)
            self.trading_monitor_action.setStatusTip("打开交易监控窗口")
            self.strategy_menu.addAction(self.trading_monitor_action)

            # 注意：信号连接已在connect_signals方法中统一处理，这里不再重复连接

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化策略菜单失败: {str(e)}")

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

            self.data_menu.addSeparator()

            # 数据导入子菜单 - 专业级DuckDB导入系统
            self.data_import_menu = self.data_menu.addMenu(" 数据导入")

            # DuckDB专业数据导入（统一入口）
            self.enhanced_import_action = QAction("🚀 DuckDB专业数据导入", self)
            self.enhanced_import_action.setStatusTip("打开DuckDB专业数据导入系统（集成AI智能优化、任务管理、分布式执行、质量监控）")
            self.enhanced_import_action.setShortcut("Ctrl+Shift+I")
            self.data_import_menu.addAction(self.enhanced_import_action)

            # 数据导入监控
            self.import_monitor_action = QAction("导入监控仪表板", self)
            self.import_monitor_action.setStatusTip("实时监控数据导入状态和性能")
            self.import_monitor_action.setShortcut("Ctrl+Shift+M")
            self.data_import_menu.addAction(self.import_monitor_action)

            self.data_import_menu.addSeparator()

            # 定时导入任务
            self.scheduled_import_action = QAction("定时导入任务", self)
            self.scheduled_import_action.setStatusTip("配置和管理定时导入任务")
            self.data_import_menu.addAction(self.scheduled_import_action)

            # 导入历史
            self.import_history_action = QAction("导入历史记录", self)
            self.import_history_action.setStatusTip("查看历史导入记录和统计")
            self.data_import_menu.addAction(self.import_history_action)

            # 传统数据管理
            self.import_data_action = QAction("简单导入数据", self)
            self.import_data_action.setStatusTip("导入外部数据（传统方式）")
            self.data_menu.addAction(self.import_data_action)

            self.export_data_action = QAction("导出数据", self)
            self.export_data_action.setStatusTip("导出数据到文件")
            self.data_menu.addAction(self.export_data_action)

            self.data_menu.addSeparator()

            # 数据库管理
            self.database_admin_action = QAction("数据库管理", self)
            self.database_admin_action.setStatusTip("数据库管理和维护")
            self.data_menu.addAction(self.database_admin_action)

            # 数据质量检查
            self.data_quality_action = QAction("数据质量检查", self)
            self.data_quality_action.setStatusTip("检查数据质量")
            self.data_menu.addAction(self.data_quality_action)

            self.data_menu.addSeparator()

            # 数据管理中心 (新增)
            self.data_management_center_action = QAction("数据管理中心", self)
            self.data_management_center_action.setStatusTip("打开数据管理中心 - 统一的数据源管理、下载任务和质量监控")
            self.data_management_center_action.setShortcut("Ctrl+D")
            self.data_menu.addAction(self.data_management_center_action)

            # 信号连接已移至统一的 _connect_action_signals 方法中
            # 避免重复连接导致方法被调用多次

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化数据菜单失败: {str(e)}")

    def init_tools_menu(self):
        """初始化工具菜单"""
        try:
            # 计算器
            self.calculator_action = QAction("计算器", self)
            self.calculator_action.setStatusTip("打开计算器")
            self.tools_menu.addAction(self.calculator_action)

            # 单位转换器
            self.converter_action = QAction("单位转换器", self)
            self.converter_action.setStatusTip("打开单位转换器")
            self.tools_menu.addAction(self.converter_action)

            self.tools_menu.addSeparator()

            # 系统优化器
            self.system_optimizer_action = QAction("系统优化器", self)
            self.system_optimizer_action.setStatusTip("打开系统优化器")
            self.tools_menu.addAction(self.system_optimizer_action)

            # WebGPU状态
            self.webgpu_status_action = QAction("WebGPU状态", self)
            self.webgpu_status_action.setStatusTip("查看WebGPU硬件加速状态")
            # 信号连接已移至统一的信号连接处理中，避免重复连接
            self.tools_menu.addAction(self.webgpu_status_action)

            self.tools_menu.addSeparator()

            # 插件管理子菜单
            self.plugin_menu = self.tools_menu.addMenu(" 插件管理")

            # 数据源插件管理
            self.data_source_plugin_action = QAction(" 数据源插件", self)
            self.data_source_plugin_action.setStatusTip("管理数据源插件：配置、路由和监控")
            self.data_source_plugin_action.setShortcut("Ctrl+Shift+D")
            # 注意：信号连接将在connect_signals方法中统一处理
            self.plugin_menu.addAction(self.data_source_plugin_action)

            # 通用插件管理
            self.plugin_manager_action = QAction(" 通用插件", self)
            self.plugin_manager_action.setStatusTip("管理所有插件：启用、配置和监控")
            self.plugin_manager_action.setShortcut("Ctrl+Shift+P")
            # 注意：信号连接将在connect_signals方法中统一处理
            self.plugin_menu.addAction(self.plugin_manager_action)

            # 情绪数据插件
            self.sentiment_plugin_action = QAction(" 情绪数据插件", self)
            self.sentiment_plugin_action.setStatusTip("管理情绪分析数据源插件")
            # 注意：信号连接将在connect_signals方法中统一处理
            self.plugin_menu.addAction(self.sentiment_plugin_action)

            self.plugin_menu.addSeparator()

            # 插件市场
            self.plugin_market_action = QAction(" 插件市场", self)
            self.plugin_market_action.setStatusTip("浏览和安装新插件")
            # 注意：信号连接将在connect_signals方法中统一处理
            self.plugin_menu.addAction(self.plugin_market_action)

            self.tools_menu.addSeparator()

            self.tools_menu.addSeparator()

            # 高级搜索
            self.advanced_search_action = QAction("高级搜索", self)
            self.advanced_search_action.setStatusTip("打开高级搜索功能")
            self.tools_menu.addAction(self.advanced_search_action)

            # 数据导出
            self.data_export_action = QAction("数据导出", self)
            self.data_export_action.setStatusTip("导出数据")
            self.tools_menu.addAction(self.data_export_action)

            # 缓存管理子菜单
            self.cache_menu = self.tools_menu.addMenu("缓存管理")
            self.clear_data_cache_action = QAction("清理数据缓存", self)
            self.clear_negative_cache_action = QAction("清理负缓存", self)
            self.clear_all_cache_action = QAction("清理所有缓存", self)
            self.cache_menu.addAction(self.clear_data_cache_action)
            self.cache_menu.addAction(self.clear_negative_cache_action)
            self.cache_menu.addAction(self.clear_all_cache_action)

            self.tools_menu.addSeparator()

            # 设置
            self.settings_action = QAction("设置", self)
            self.settings_action.setShortcut("Ctrl+,")
            self.settings_action.setStatusTip("打开设置")
            self.tools_menu.addAction(self.settings_action)

            # 注意：信号连接已在connect_signals方法中统一处理，这里不再重复连接

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化工具菜单失败: {str(e)}")

    def init_performance_menu(self):
        """初始化性能监控菜单"""
        try:
            # 性能监控中心
            self.performance_center_action = QAction(QIcon("icons/performance.png"), "性能监控中心(&C)", self)
            self.performance_center_action.setShortcut("Ctrl+Shift+M")
            self.performance_center_action.setStatusTip("打开统一性能监控中心")
            self.performance_menu.addAction(self.performance_center_action)

            self.performance_menu.addSeparator()

            # 系统性能
            self.system_performance_action = QAction("系统性能(&S)", self)
            self.system_performance_action.setStatusTip("查看系统CPU、内存、磁盘性能")
            self.performance_menu.addAction(self.system_performance_action)

            # UI性能优化
            self.ui_performance_action = QAction("UI性能优化(&U)", self)
            self.ui_performance_action.setStatusTip("查看和优化用户界面性能")
            self.performance_menu.addAction(self.ui_performance_action)

            # 策略性能
            self.strategy_performance_action = QAction("策略性能(&T)", self)
            self.strategy_performance_action.setStatusTip("查看交易策略性能指标")
            self.performance_menu.addAction(self.strategy_performance_action)

            # 算法性能
            self.algorithm_performance_action = QAction("算法性能(&A)", self)
            self.algorithm_performance_action.setStatusTip("查看算法执行性能")
            self.performance_menu.addAction(self.algorithm_performance_action)

            self.performance_menu.addSeparator()

            # 自动调优
            self.auto_tuning_action = QAction("自动调优(&O)", self)
            self.auto_tuning_action.setStatusTip("启用/配置系统自动性能调优")
            self.performance_menu.addAction(self.auto_tuning_action)

            # 性能报告
            self.performance_report_action = QAction("性能报告(&R)", self)
            self.performance_report_action.setStatusTip("生成和导出性能分析报告")
            self.performance_menu.addAction(self.performance_report_action)

            self.performance_menu.addSeparator()

            # 性能仪表板已删除 - 根据用户要求移除

            # 注意：信号连接将在connect_signals方法中统一处理

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化性能监控菜单失败: {str(e)}")

    def init_advanced_menu(self):
        """初始化高级功能菜单"""
        try:
            # 注意：插件管理已迁移到工具菜单，避免重复

            # 分布式/云API/指标市场/批量分析
            self.node_manager_action = QAction("分布式节点管理", self)
            self.cloud_api_action = QAction("云API管理", self)
            self.indicator_market_action = QAction("指标市场", self)
            self.batch_analysis_action = QAction("批量分析", self)
            self.advanced_menu.addAction(self.node_manager_action)
            self.advanced_menu.addAction(self.cloud_api_action)
            self.advanced_menu.addAction(self.indicator_market_action)
            self.advanced_menu.addAction(self.batch_analysis_action)

            # GPU加速配置
            self.gpu_config_action = QAction(" GPU加速配置", self)
            self.gpu_config_action.setStatusTip("配置GPU加速设置")
            self.advanced_menu.addAction(self.gpu_config_action)

            self.advanced_menu.addSeparator()

            # 形态识别算法优化系统
            self.optimization_menu = self.advanced_menu.addMenu("形态识别优化")

            # 优化仪表板
            self.optimization_dashboard_action = QAction("优化仪表板", self)
            self.optimization_dashboard_action.setStatusTip("打开形态识别算法优化仪表板")
            self.optimization_menu.addAction(
                self.optimization_dashboard_action)

            # 一键优化
            self.one_click_optimize_action = QAction("一键优化所有形态", self)
            self.one_click_optimize_action.setStatusTip("自动优化所有形态识别算法")
            self.optimization_menu.addAction(self.one_click_optimize_action)

            # 智能优化
            self.smart_optimize_action = QAction("智能优化", self)
            self.smart_optimize_action.setStatusTip("智能识别需要优化的形态并自动优化")
            self.optimization_menu.addAction(self.smart_optimize_action)

            self.optimization_menu.addSeparator()

            # 版本管理
            self.version_manager_action = QAction("版本管理", self)
            self.version_manager_action.setStatusTip("管理形态识别算法版本")
            self.optimization_menu.addAction(self.version_manager_action)

            # 性能评估
            self.performance_evaluation_action = QAction("性能评估", self)
            self.performance_evaluation_action.setStatusTip("评估形态识别算法性能")
            self.optimization_menu.addAction(
                self.performance_evaluation_action)

            # 系统状态
            self.optimization_status_action = QAction("系统状态", self)
            self.optimization_status_action.setStatusTip("查看优化系统状态")
            self.optimization_menu.addAction(self.optimization_status_action)

            # 注意：信号连接已在connect_signals方法中统一处理，这里不再重复连接

            # 注意：优化系统菜单的信号连接已在connect_signals方法中统一处理

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化高级功能菜单失败: {str(e)}")

    def init_debug_menu(self):
        """初始化调试菜单，添加显示/隐藏日志菜单项"""
        try:
            self.toggle_log_action = QAction("显示/隐藏日志", self)
            self.toggle_log_action.setStatusTip("显示或隐藏日志输出区")
            # 信号连接已移至统一的信号连接处理中，避免重复连接
            self.debug_menu.addAction(self.toggle_log_action)
        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化调试菜单失败: {str(e)}")

    def init_help_menu(self):
        """初始化帮助菜单"""
        try:
            # 启动向导
            self.startup_guides_action = QAction("启动向导", self)
            self.startup_guides_action.setStatusTip("显示启动向导")
            self.help_menu.addAction(self.startup_guides_action)

            self.help_menu.addSeparator()

            # 帮助文档
            self.help_action = QAction("帮助文档", self)
            self.help_action.setStatusTip("打开帮助文档")
            self.help_menu.addAction(self.help_action)

            # 用户手册
            self.user_manual_action = QAction("用户手册", self)
            self.user_manual_action.setStatusTip("打开用户手册")
            self.help_menu.addAction(self.user_manual_action)

            # 快捷键
            self.shortcuts_action = QAction("快捷键", self)
            self.shortcuts_action.setStatusTip("查看快捷键列表")
            self.help_menu.addAction(self.shortcuts_action)

            self.help_menu.addSeparator()

            # 检查更新
            self.update_action = QAction("检查更新", self)
            self.update_action.setStatusTip("检查新版本")
            self.help_menu.addAction(self.update_action)

            self.help_menu.addSeparator()

            # 数据使用条款
            self.data_usage_terms_action = QAction("数据使用条款", self)
            self.data_usage_terms_action.setStatusTip("查看数据使用条款")
            self.help_menu.addAction(self.data_usage_terms_action)

            self.help_menu.addSeparator()

            # 关于
            self.about_action = QAction("关于", self)
            self.about_action.setStatusTip("关于本程序")
            self.help_menu.addAction(self.about_action)

            # 注意：信号连接已在connect_signals方法中统一处理，这里不再重复连接

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"初始化帮助菜单失败: {str(e)}")

    def log_message(self, message: str, level: str = "info") -> None:
        """记录日志消息，统一调用主窗口或日志管理器"""
        try:
            parent = self.parentWidget()
            if parent and hasattr(parent, 'log_message'):
                parent.log_message(message, level)
            elif True:  # 使用Loguru日志
                # 直接用log_manager
                level = level.upper()
                if level == "ERROR":
                    logger.error(message)
                elif level == "WARNING":
                    logger.warning(message)
                elif level == "DEBUG":
                    logger.debug(message)
                else:
                    logger.info(message)
            else:
                logger.info(f"[LOG][{level}] {message}")
        except Exception as e:
            logger.info(f"记录日志失败: {str(e)}")
            if True:  # 使用Loguru日志
                logger.error(f"记录日志失败: {str(e)}")
                logger.error(traceback.format_exc())

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
        try:
            # 获取主窗口的分析控件
            main_window = self.window()
            if hasattr(main_window, 'trading_widget'):
                main_window.trading_widget.on_analyze()
            else:
                QMessageBox.information(self, "分析", "分析功能已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动分析失败: {str(e)}")

    def backtest(self):
        """Run backtest"""
        try:
            # 获取主窗口的回测控件
            main_window = self.window()
            if hasattr(main_window, 'trading_widget'):
                main_window.trading_widget.run_backtest()
            else:
                QMessageBox.information(self, "回测", "回测功能已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动回测失败: {str(e)}")

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
        """Show calculator"""
        # TODO: Implement calculator
        pass

    def show_converter(self):
        """Show unit converter"""
        # TODO: Implement unit converter
        pass

    def show_system_optimizer(self):
        """Show system optimizer"""
        try:
            from gui.dialogs import show_system_optimizer_dialog
            show_system_optimizer_dialog(self.parent())
        except Exception as e:
            QMessageBox.critical(self.parent(), "错误", f"打开系统优化器失败: {str(e)}")
            if True:  # 使用Loguru日志
                logger.error(f"打开系统优化器失败: {str(e)}")

    def show_webgpu_status(self):
        """Show WebGPU status dialog"""
        try:
            from gui.dialogs.webgpu_status_dialog import WebGPUStatusDialog
            dialog = WebGPUStatusDialog(self.parent())
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self.parent(), "错误", f"打开WebGPU状态对话框失败: {str(e)}")
            if True:  # 使用Loguru日志
                logger.error(f"打开WebGPU状态对话框失败: {str(e)}")

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
        self.setStyleSheet(f'''
            QMenuBar {{
                background: {menu_bg};
                color: {menu_text};
                border-bottom: 1px solid {menu_border};
                font-weight: bold;
                font-size: 12px;
            }}
            QMenuBar::item {{
                background: transparent;
                color: {menu_text};
                padding: 6px 18px;
                border-radius: 6px 6px 0 0;
            }}
            QMenuBar::item:selected {{
                background: {menu_selected};
                color: #ffd600;
            }}
            QMenuBar::item:pressed {{
                background: {menu_selected};
                color: #ffd600;
            }}
            QMenu {{
                background: {menu_bg};
                color: {menu_text};
                border: 1px solid {menu_border};
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background: {menu_selected};
                color: #ffd600;
            }}
            QMenu::item:disabled {{
                color: #888;
            }}
        ''')

    def connect_signals(self):
        """统一连接所有菜单的信号到coordinator"""
        if not self.coordinator:
            return

        try:
            # 连接所有已创建的action的信号
            actions_to_connect = [
                # 文件菜单
                ('new_action', '_on_new_file'),
                ('open_action', '_on_open_file'),
                ('save_action', '_on_save_file'),
                ('exit_action', '_on_exit'),

                # 编辑菜单
                ('undo_action', '_on_undo'),
                ('redo_action', '_on_redo'),
                ('copy_action', '_on_copy'),
                ('paste_action', '_on_paste'),

                # 视图菜单
                ('toolbar_action', '_on_toggle_toolbar'),
                ('statusbar_action', '_on_toggle_statusbar'),
                # ('backtest_panel_action', '_on_toggle_backtest_panel'),  # 已合并到专业回测
                ('refresh_action', '_on_refresh'),

                # 主题相关
                ('default_theme_action', '_on_default_theme'),
                ('light_theme_action', '_on_light_theme'),
                ('dark_theme_action', '_on_dark_theme'),

                # 分析相关
                ('analyze_action', '_on_analyze'),
                ('backtest_action', '_on_backtest'),
                ('professional_backtest_action', '_on_professional_backtest'),
                ('optimize_action', '_on_optimize'),
                ('batch_analysis_action', '_on_batch_analysis'),

                # 策略相关
                ('strategy_manager_action', '_on_strategy_management'),
                ('create_strategy_action', '_on_create_strategy'),
                ('import_strategy_action', '_on_import_strategy'),
                ('export_strategy_action', '_on_export_strategy'),
                # ('strategy_backtest_action', '_on_strategy_backtest'),  # 已整合到智能回测
                ('strategy_optimize_action', '_on_strategy_optimize'),
                ('trading_monitor_action', '_on_trading_monitor'),

                # 数据相关
                ('import_data_action', '_on_import_data'),
                ('export_data_action', '_on_export_data'),
                ('database_admin_action', '_on_database_admin'),
                ('data_quality_action', '_on_data_quality_check'),
                ('data_management_center_action', '_on_data_management_center'),
                ('enhanced_import_action', '_on_enhanced_import'),  # DuckDB专业数据导入（统一入口）
                ('import_monitor_action', '_on_import_monitor'),
                ('scheduled_import_action', '_on_scheduled_import'),
                ('import_history_action', '_on_import_history'),

                # 工具相关
                ('calculator_action', '_on_calculator'),
                ('converter_action', '_on_converter'),
                ('system_optimizer_action', '_on_system_optimizer'),
                ('webgpu_status_action', 'show_webgpu_status'),
                ('advanced_search_action', '_on_advanced_search'),
                ('settings_action', '_on_settings'),

                # 性能监控菜单
                ('performance_center_action', '_on_performance_center'),
                ('system_performance_action', '_on_system_performance'),
                ('ui_performance_action', '_on_ui_performance'),
                ('strategy_performance_action', '_on_strategy_performance'),
                ('algorithm_performance_action', '_on_algorithm_performance'),
                ('auto_tuning_action', '_on_auto_tuning'),
                ('performance_report_action', '_on_performance_report'),
                # 性能仪表板信号连接已删除 - 根据用户要求移除

                # 插件管理功能 - 使用MenuBar中的直接方法
                ('data_source_plugin_action', 'show_data_source_plugin_manager'),
                ('plugin_manager_action', 'show_plugin_manager'),
                ('sentiment_plugin_action', 'show_sentiment_plugin_manager'),
                ('plugin_market_action', 'show_plugin_market'),
                ('optimization_dashboard_action', '_on_optimization_dashboard'),
                ('one_click_optimize_action', '_on_one_click_optimize'),
                ('smart_optimize_action', '_on_smart_optimize'),
                ('version_manager_action', '_on_version_manager'),
                ('performance_evaluation_action', '_on_performance_evaluation'),

                # 调试功能
                ('toggle_log_action', '_toggle_log_panel'),

                # 帮助菜单
                ('help_action', '_on_help'),
                ('user_manual_action', '_on_user_manual'),
                ('shortcuts_action', '_on_shortcuts'),
                ('update_action', '_on_check_update'),
                ('data_usage_terms_action', '_on_data_usage_terms'),
                ('about_action', '_on_about'),
            ]

            for action_name, method_name in actions_to_connect:
                if hasattr(self, action_name):
                    action = getattr(self, action_name)

                    # 优先检查MenuBar本身是否有这个方法（用于插件管理等直接方法）
                    if hasattr(self, method_name):
                        action.triggered.connect(getattr(self, method_name))
                    # 如果MenuBar没有，则检查coordinator
                    elif hasattr(self.coordinator, method_name):
                        action.triggered.connect(getattr(self.coordinator, method_name))
                    else:
                        # 如果都没有对应方法，连接到一个默认的空方法
                        action.triggered.connect(lambda: None)

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"连接菜单信号失败: {str(e)}")
            else:
                logger.info(f"连接菜单信号失败: {str(e)}")

    # ==================== 插件管理方法 ====================

    def show_data_source_plugin_manager(self):
        """显示数据源插件管理器"""
        try:
            # 优先使用coordinator的方法
            if self.coordinator and hasattr(self.coordinator, '_on_plugin_manager'):
                self.coordinator._on_plugin_manager()
                return

            # 如果没有coordinator，直接创建对话框
            self._create_plugin_dialog("数据源插件")

        except Exception as e:
            QMessageBox.critical(
                self.parent(),
                "错误",
                f"打开数据源插件管理器失败:\n{str(e)}"
            )
            if True:  # 使用Loguru日志
                logger.error(f"打开数据源插件管理器失败: {str(e)}")

    def show_plugin_manager(self):
        """显示通用插件管理器"""
        try:
            # 优先使用coordinator的方法
            if self.coordinator and hasattr(self.coordinator, '_on_plugin_manager'):
                self.coordinator._on_plugin_manager()
                return

            # 如果没有coordinator，直接创建对话框
            self._create_plugin_dialog("通用插件")

        except Exception as e:
            QMessageBox.critical(
                self.parent(),
                "错误",
                f"打开插件管理器失败:\n{str(e)}"
            )
            if True:  # 使用Loguru日志
                logger.error(f"打开插件管理器失败: {str(e)}")

    def show_sentiment_plugin_manager(self):
        """显示情绪数据插件管理器"""
        try:
            # 优先使用coordinator的方法
            if self.coordinator and hasattr(self.coordinator, '_on_plugin_manager'):
                self.coordinator._on_plugin_manager()
                return

            # 如果没有coordinator，直接创建对话框
            self._create_plugin_dialog("情绪数据源")

        except Exception as e:
            QMessageBox.critical(
                self.parent(),
                "错误",
                f"打开情绪数据插件管理器失败:\n{str(e)}"
            )
            if True:  # 使用Loguru日志
                logger.error(f"打开情绪数据插件管理器失败: {str(e)}")

    def show_plugin_market(self):
        """显示插件市场"""
        try:
            # 优先使用coordinator的方法
            if self.coordinator and hasattr(self.coordinator, '_on_plugin_manager'):
                self.coordinator._on_plugin_manager()
                return

            # 如果没有coordinator，直接创建对话框
            self._create_plugin_dialog("插件市场")

        except Exception as e:
            QMessageBox.critical(
                self.parent(),
                "错误",
                f"打开插件市场失败:\n{str(e)}"
            )
            if True:  # 使用Loguru日志
                logger.error(f"打开插件市场失败: {str(e)}")

    def _create_plugin_dialog(self, target_tab=None):
        """创建插件对话框的通用方法"""
        try:
            from gui.dialogs.enhanced_plugin_manager_dialog import EnhancedPluginManagerDialog
            from core.containers import get_service_container
            from core.plugin_manager import PluginManager
            from core.services.sentiment_data_service import SentimentDataService

            # 获取服务
            plugin_manager = None
            sentiment_service = None

            container = get_service_container()
            if container:
                # 获取插件管理器
                if container.is_registered(PluginManager):
                    try:
                        plugin_manager = container.resolve(PluginManager)
                    except Exception as e:
                        logger.info(f" 获取插件管理器失败: {e}")

                # 获取情绪数据服务
                if container.is_registered(SentimentDataService):
                    try:
                        sentiment_service = container.resolve(SentimentDataService)
                    except Exception as e:
                        logger.info(f" 获取情绪数据服务失败: {e}")

            # 创建增强版插件管理器对话框
            dialog = EnhancedPluginManagerDialog(
                plugin_manager=plugin_manager,
                sentiment_service=sentiment_service,
                parent=self.parent()
            )

            # 切换到指定标签页
            if target_tab and hasattr(dialog, 'tab_widget'):
                for i in range(dialog.tab_widget.count()):
                    tab_text = dialog.tab_widget.tabText(i)
                    if target_tab in tab_text:
                        dialog.tab_widget.setCurrentIndex(i)
                        break

            dialog.exec_()

        except Exception as e:
            logger.info(f" 创建插件对话框失败: {e}")
            raise

    def _on_enhanced_import(self):
        """处理增强版数据导入菜单点击"""
        try:
            # 导入增强版数据导入UI
            from gui.enhanced_data_import_launcher import EnhancedDataImportMainWindow

            # 创建增强版数据导入窗口
            self.enhanced_import_window = EnhancedDataImportMainWindow()
            self.enhanced_import_window.show()

            logger.info("增强版数据导入系统已启动")

        except ImportError as e:
            QMessageBox.warning(
                self.parent(),
                "功能不可用",
                f"增强版数据导入UI组件加载失败:\n{str(e)}\n\n请确保所有依赖项已正确安装。"
            )
            logger.error(f"增强版数据导入UI组件加载失败: {e}")

        except Exception as e:
            QMessageBox.critical(
                self.parent(),
                "错误",
                f"启动增强版数据导入系统失败:\n{str(e)}"
            )
            logger.error(f"启动增强版数据导入系统失败: {e}")

    def _on_duckdb_import(self):
        """处理DuckDB数据导入菜单点击"""
        try:
            # 这里可以添加原有的DuckDB导入功能
            # 或者重定向到增强版导入
            QMessageBox.information(
                self.parent(),
                "提示",
                "建议使用增强版智能导入系统，它包含了所有DuckDB功能并增加了AI优化功能。"
            )

        except Exception as e:
            QMessageBox.critical(
                self.parent(),
                "错误",
                f"启动DuckDB导入失败:\n{str(e)}"
            )
            logger.error(f"启动DuckDB导入失败: {e}")
