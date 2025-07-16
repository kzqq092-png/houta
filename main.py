#!/usr/bin/env python3
"""
YS-Quant‌ 主程序入口

使用重构后的架构：
- 主窗口协调器 (MainWindowCoordinator)
- 服务容器 (ServiceContainer)
- 事件总线 (EventBus)
- 模块化UI面板

版本: 2.0 (重构版本)
作者: YS-Quant‌ Team
"""

from optimization.chart_renderer import initialize_chart_renderer
from utils.exception_handler import setup_exception_handler
from utils.warning_suppressor import suppress_warnings
from core.coordinators import MainWindowCoordinator
from core.events import EventBus, get_event_bus
from core.containers import ServiceContainer, get_service_container
from core.containers.service_registry import ServiceScope
from core.services.service_bootstrap import bootstrap_services
import sys
import asyncio
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
    from qasync import QEventLoop
except ImportError as e:
    print(f"PyQt5导入失败: {e}")
    print("请安装PyQt5: pip install PyQt5")
    QEventLoop = None

# 添加图表渲染器初始化

# 初始化图表渲染器
initialize_chart_renderer(max_workers=4, enable_progressive=True)

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
    YS-Quant‌ 应用程序主类

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
            logger.info("YS-Quant‌ 2.0 (重构版本) 启动中...")
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
            if not self._register_services():
                return False

            # 6. 创建主窗口协调器
            self._create_main_window()

            logger.info("✓ YS-Quant‌ 2.0 初始化完成")
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
        self.app.setApplicationName("YS-Quant‌")
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
            # 注册Qt类型以解决信号槽问题
            # 由于core/qt_types.py已在导入时调用init_qt_types()，这里不需要再次调用
            # 避免重复注册导致的问题
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

    def _register_services(self) -> bool:
        """
        注册服务

        Returns:
            注册是否成功
        """
        logger.info("3. 注册服务...")

        # 使用服务引导器注册所有服务
        if not bootstrap_services():
            logger.error("❌ 服务注册失败")
            return False

        logger.info("✓ 所有服务注册完成")
        return True

    def _create_main_window(self) -> None:
        """创建主窗口协调器"""
        logger.info("5. 创建主窗口...")

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

            logger.info("6. 启动主窗口...")

            # 启动主窗口
            self.main_window_coordinator.run()

            logger.info("7. 事件循环将由外部管理...")
            return 0  # 成功

        except Exception as e:
            logger.error(f"运行时错误: {e}")
            logger.error(traceback.format_exc())
            self._show_error_message("运行时错误", str(e))
            return 1

    def _cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("正在清理资源...")

            if self.main_window_coordinator:
                self.main_window_coordinator.dispose()

            if self.service_container:
                # 清理所有服务
                self.service_container.dispose()
                logger.info("✓ 服务容器已清理")

            # 停止事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.stop()

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
        if QEventLoop is not None:
            app = QApplication(sys.argv)
            event_loop = QEventLoop(app)
            asyncio.set_event_loop(event_loop)

            hikyuu_app = HIkyuuUIApplication()
            hikyuu_app.app = app  # Pass app instance

            # 优雅地退出
            app.aboutToQuit.connect(event_loop.stop)

            if hikyuu_app.run() != 0:
                logger.error("Application setup failed. Exiting.")
                sys.exit(1)

            event_loop.run_forever()  # 运行事件循环

            hikyuu_app._cleanup()
            logger.info("Application shutdown complete.")
            # sys.exit(0) # Let the application exit naturally

        else:
            # Fallback for systems without qasync
            logger.error(
                "qasync is not installed. Please install it with 'pip install qasync'")
            app = HIkyuuUIApplication()
            # This part will likely not work correctly without an event loop manager.
            exit_code = app.run()
            sys.exit(exit_code)

    except Exception as e:
        print(f"程序启动失败: {e}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
