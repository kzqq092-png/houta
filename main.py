#!/usr/bin/env python3
"""
HIkyuu-UI 主程序入口

使用重构后的架构：
- 主窗口协调器 (MainWindowCoordinator)
- 服务容器 (ServiceContainer)
- 事件总线 (EventBus)
- 模块化UI面板

版本: 2.0 (重构版本)
作者: HIkyuu-UI Team
"""

from utils.exception_handler import setup_exception_handler
from utils.warning_suppressor import suppress_warnings
from core.services import (
    ConfigService, ThemeService, StockService,
    ChartService, AnalysisService, IndustryService
)

from core.coordinators import MainWindowCoordinator
from core.events import EventBus, get_event_bus
from core.containers import ServiceContainer, get_service_container
import sys
import logging
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Qt相关导入
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QIcon
except ImportError as e:
    print(f"PyQt5导入失败: {e}")
    print("请安装PyQt5: pip install PyQt5")
    sys.exit(1)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/hikyuu_ui.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class HIkyuuUIApplication:
    """
    HIkyuu-UI 应用程序主类

    负责：
    1. 应用程序初始化
    2. 服务容器配置
    3. 主窗口创建
    4. 生命周期管理
    """

    def __init__(self):
        """初始化应用程序"""
        self.app = None
        self.main_window_coordinator = None
        self.service_container = None
        self.event_bus = None

    def initialize(self) -> bool:
        """
        初始化应用程序

        Returns:
            初始化是否成功
        """
        try:
            logger.info("=" * 60)
            logger.info("HIkyuu-UI 2.0 (重构版本) 启动中...")
            logger.info("=" * 60)

            # 1. 创建Qt应用程序
            self._create_qt_application()

            # 2. 抑制警告
            suppress_warnings()

            # 3. 设置异常处理器
            setup_exception_handler(self.app)

            # 4. 初始化核心组件
            self._initialize_core_components()

            # 5. 注册服务
            self._register_services()

            # 6. 创建主窗口协调器
            self._create_main_window()

            logger.info("✓ HIkyuu-UI 2.0 初始化完成")
            return True

        except Exception as e:
            logger.error(f"❌ 应用程序初始化失败: {e}")
            logger.error(traceback.format_exc())
            self._show_error_message("初始化失败", str(e))
            return False

    def _create_qt_application(self) -> None:
        """创建Qt应用程序"""
        logger.info("1. 创建Qt应用程序...")

        # 设置Qt应用程序属性
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # 创建应用程序实例
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("HIkyuu-UI")
        self.app.setApplicationVersion("2.0")
        self.app.setOrganizationName("HIkyuu Team")

        # 设置应用程序图标
        icon_path = project_root / "icons" / "logo.png"
        if icon_path.exists():
            self.app.setWindowIcon(QIcon(str(icon_path)))

        # 注册Qt元类型
        self._register_qt_meta_types()

        # 设置全局样式
        self._setup_global_styles()

        logger.info("✓ Qt应用程序创建完成")

    def _register_qt_meta_types(self) -> None:
        """注册Qt元类型"""
        try:
            from PyQt5.QtCore import QMetaType
            from utils.qt_helpers import register_meta_types

            # 注册常用的Qt类型 - 修复注册方式
            # 在 PyQt5 中，没有直接的 qRegisterMetaType 函数
            # 而是在 QObject.connect 时自动处理这些类型
            # 使用 QtCore.Q_DECLARE_METATYPE 方式
            logger.info("使用 QMetaType 注册元类型")

            # 使用工具类注册元类型
            success = register_meta_types()
            if success:
                logger.info("使用辅助函数成功注册元类型")

            # 注册完成消息
            logger.info("✓ Qt元类型注册完成")

        except Exception as e:
            logger.warning(f"Qt元类型注册失败: {e}")
            logger.warning(traceback.format_exc())

    def _setup_global_styles(self) -> None:
        """设置全局样式"""
        global_style = '''
            QScrollBar:vertical {
                width: 8px;
                background: #f0f0f0;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar:horizontal {
                height: 8px;
                background: #f0f0f0;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #c0c0c0;
                min-height: 20px;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            
            /* 表格样式 */
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #007bff;
                selection-color: white;
                border: 1px solid #dee2e6;
            }
            QHeaderView::section {
                background-color: #495057;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
                height: 14px
            }
            
            /* 选项卡样式 */
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #007bff;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        '''
        self.app.setStyleSheet(global_style)

    def _initialize_core_components(self) -> None:
        """初始化核心组件"""
        logger.info("2. 初始化核心组件...")

        # 获取全局服务容器和事件总线
        self.service_container = get_service_container()
        self.event_bus = get_event_bus()

        logger.info(f"✓ 服务容器: {type(self.service_container).__name__}")
        logger.info(f"✓ 事件总线: {type(self.event_bus).__name__}")

    def _register_services(self) -> None:
        """注册服务"""
        logger.info("3. 注册服务...")

        # 配置服务（使用单例）
        config_service = ConfigService(config_file='config/config.json')
        config_service.initialize()  # 立即初始化
        self.service_container.register_instance(ConfigService, config_service)
        logger.info("✓ 配置服务注册完成")

        # 主题服务
        self.service_container.register(ThemeService)
        theme_service = self.service_container.resolve(ThemeService)
        theme_service.initialize()  # 立即初始化
        logger.info("✓ 主题服务注册完成")

        # 股票服务
        self.service_container.register(StockService)
        stock_service = self.service_container.resolve(StockService)
        stock_service.initialize()  # 立即初始化
        logger.info("✓ 股票服务注册完成")

        # 图表服务
        self.service_container.register(ChartService)
        chart_service = self.service_container.resolve(ChartService)
        chart_service.initialize()  # 立即初始化
        logger.info("✓ 图表服务注册完成")

        # 分析服务
        self.service_container.register(AnalysisService)
        analysis_service = self.service_container.resolve(AnalysisService)
        analysis_service.initialize()  # 立即初始化
        logger.info("✓ 分析服务注册完成")

        # 行业服务
        logger.info("开始注册行业服务...")
        try:
            self.service_container.register(IndustryService)
            logger.info("行业服务类已注册到容器")

            industry_service = self.service_container.resolve(IndustryService)
            logger.info("行业服务实例已创建")

            industry_service.initialize()  # 立即初始化
            logger.info("✓ 行业服务注册完成")
        except Exception as e:
            logger.error(f"❌ 行业服务注册失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

        # 插件管理器服务
        logger.info("开始注册插件管理器服务...")
        try:
            from core.plugin_manager import PluginManager
            logger.info("插件管理器类已导入")

            self.service_container.register(PluginManager)
            logger.info("插件管理器类已注册到容器")

            plugin_manager = self.service_container.resolve(PluginManager)
            logger.info("插件管理器实例已创建")

            plugin_manager.initialize()  # 立即初始化
            logger.info("✓ 插件管理器服务注册完成")
        except Exception as e:
            logger.error(f"❌ 插件管理器服务注册失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _create_main_window(self) -> None:
        """创建主窗口协调器"""
        logger.info("4. 创建主窗口...")

        try:
            # 创建主窗口协调器
            logger.info("正在创建主窗口协调器实例...")
            self.main_window_coordinator = MainWindowCoordinator(
                service_container=self.service_container,
                event_bus=self.event_bus
            )
            logger.info("主窗口协调器实例创建完成")

            # 初始化协调器
            logger.info("正在初始化主窗口协调器...")
            self.main_window_coordinator.initialize()
            logger.info("主窗口协调器初始化完成")

            logger.info("✓ 主窗口协调器创建完成")
        except Exception as e:
            logger.error(f"❌ 主窗口协调器创建失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def run(self) -> int:
        """
        运行应用程序

        Returns:
            应用程序退出代码
        """
        try:
            if not self.initialize():
                return 1

            logger.info("5. 启动主窗口...")

            # 启动主窗口
            self.main_window_coordinator.run()

            logger.info("6. 进入事件循环...")

            # 进入Qt事件循环
            return self.app.exec_()

        except KeyboardInterrupt:
            logger.info("用户中断程序")
            return 0
        except Exception as e:
            logger.error(f"运行时错误: {e}")
            logger.error(traceback.format_exc())
            self._show_error_message("运行时错误", str(e))
            return 1
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("正在清理资源...")

            if self.main_window_coordinator:
                self.main_window_coordinator.dispose()

            if self.service_container:
                # 清理所有服务
                from core.plugin_manager import PluginManager
                for service_type in [ConfigService, ThemeService, StockService, ChartService, AnalysisService, PluginManager]:
                    try:
                        service = self.service_container.resolve(service_type)
                        if hasattr(service, 'dispose'):
                            service.dispose()
                    except Exception as e:
                        logger.debug(f"Failed to dispose {service_type.__name__}: {e}")
                        pass

            logger.info("✓ 资源清理完成")

        except Exception as e:
            logger.error(f"清理资源时出错: {e}")

    def _show_error_message(self, title: str, message: str) -> None:
        """显示错误消息"""
        if self.app:
            QMessageBox.critical(None, title, message)
        else:
            print(f"错误: {title} - {message}")


def main():
    """主程序入口"""
    try:
        # 确保日志目录存在
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        # 创建并运行应用程序
        app = HIkyuuUIApplication()
        exit_code = app.run()

        logger.info("=" * 60)
        logger.info(f"HIkyuu-UI 2.0 退出，退出代码: {exit_code}")
        logger.info("=" * 60)

        sys.exit(exit_code)

    except Exception as e:
        print(f"程序启动失败: {e}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
