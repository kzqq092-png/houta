"""
主布局管理器 - 统一管理主窗口布局

负责管理左侧面板、中间面板、右侧面板的布局和交互
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QTabWidget, QLabel, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from typing import Optional, Dict, Any
from core.logger import LogManager
from gui.panels.stock_panel import StockManagementPanel
from gui.panels.chart_panel import ChartAnalysisPanel
from gui.panels.analysis_tools_panel import AnalysisToolsPanel


class MainLayout(QWidget):
    """主布局管理器"""

    # 定义信号
    layout_changed = pyqtSignal(str)  # 布局变化信号
    panel_resized = pyqtSignal(str, int)  # 面板大小变化信号
    data_flow = pyqtSignal(str, dict)  # 数据流信号

    def __init__(self, parent=None, log_manager: Optional[LogManager] = None):
        super().__init__(parent)
        self.log_manager = log_manager or LogManager()
        self.parent_gui = parent

        # 面板引用
        self.left_panel = None
        self.middle_panel = None
        self.right_panel = None
        self.bottom_panel = None

        # 布局组件
        self.main_splitter = None
        self.vertical_splitter = None

        # 布局状态
        self.current_layout = "standard"  # standard, compact, full_chart
        self.panel_sizes = {}

        # 初始化布局
        self.init_layout()
        self.init_signals()

    def init_layout(self):
        """初始化主布局"""
        try:
            # 创建主布局
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # 创建主分割器（水平）
            self.main_splitter = QSplitter(Qt.Horizontal)
            main_layout.addWidget(self.main_splitter)

            # 创建面板
            self.create_panels()

            # 设置默认布局
            self.setup_standard_layout()

        except Exception as e:
            self.log_manager.error(f"主布局初始化失败: {str(e)}")

    def create_panels(self):
        """创建各个面板"""
        try:
            # 创建左侧面板（股票管理面板）
            self.left_panel = StockManagementPanel(self.parent_gui, self.log_manager)

            # 创建中间面板容器（包含图表和底部信息）
            self.middle_container = QWidget()
            middle_layout = QVBoxLayout(self.middle_container)
            middle_layout.setContentsMargins(0, 0, 0, 0)

            # 创建中间面板
            self.middle_panel = ChartAnalysisPanel(self.parent_gui, self.log_manager)
            middle_layout.addWidget(self.middle_panel)

            # 创建底部面板（日志和状态信息）
            self.bottom_panel = self.create_bottom_panel()
            middle_layout.addWidget(self.bottom_panel)

            # 创建右侧面板
            self.right_panel = AnalysisToolsPanel(self.parent_gui)

        except Exception as e:
            self.log_manager.error(f"创建面板失败: {str(e)}")

    def create_bottom_panel(self):
        """创建底部面板"""
        bottom_panel = QTabWidget()
        bottom_panel.setMaximumHeight(200)

        # 日志标签页
        log_widget = QLabel("日志信息将在这里显示...")
        log_widget.setStyleSheet("background-color: #f0f0f0; padding: 10px;")
        bottom_panel.addTab(log_widget, "系统日志")

        # 状态标签页
        status_widget = QLabel("系统状态信息...")
        status_widget.setStyleSheet("background-color: #f0f0f0; padding: 10px;")
        bottom_panel.addTab(status_widget, "系统状态")

        # 性能标签页
        performance_widget = QLabel("性能监控信息...")
        performance_widget.setStyleSheet("background-color: #f0f0f0; padding: 10px;")
        bottom_panel.addTab(performance_widget, "性能监控")

        return bottom_panel

    def setup_standard_layout(self):
        """设置标准布局"""
        try:
            # 清空分割器
            self.clear_splitter()

            # 添加面板到主分割器
            self.main_splitter.addWidget(self.left_panel)
            self.main_splitter.addWidget(self.middle_container)
            self.main_splitter.addWidget(self.right_panel)

            # 设置分割器比例 (左:中:右 = 2:5:3)
            self.main_splitter.setSizes([300, 800, 400])

            # 设置分割器属性
            self.main_splitter.setChildrenCollapsible(False)
            self.main_splitter.setHandleWidth(3)

            self.current_layout = "standard"
            self.layout_changed.emit("standard")

        except Exception as e:
            self.log_manager.error(f"设置标准布局失败: {str(e)}")

    def setup_compact_layout(self):
        """设置紧凑布局"""
        try:
            # 清空分割器
            self.clear_splitter()

            # 隐藏底部面板
            self.bottom_panel.setVisible(False)

            # 添加面板到主分割器
            self.main_splitter.addWidget(self.left_panel)
            self.main_splitter.addWidget(self.middle_panel)
            self.main_splitter.addWidget(self.right_panel)

            # 设置分割器比例 (左:中:右 = 2:6:2)
            self.main_splitter.setSizes([250, 900, 350])

            self.current_layout = "compact"
            self.layout_changed.emit("compact")

        except Exception as e:
            self.log_manager.error(f"设置紧凑布局失败: {str(e)}")

    def setup_full_chart_layout(self):
        """设置全图表布局"""
        try:
            # 清空分割器
            self.clear_splitter()

            # 隐藏左侧和右侧面板
            self.left_panel.setVisible(False)
            self.right_panel.setVisible(False)
            self.bottom_panel.setVisible(False)

            # 只显示中间面板
            self.main_splitter.addWidget(self.middle_panel)

            self.current_layout = "full_chart"
            self.layout_changed.emit("full_chart")

        except Exception as e:
            self.log_manager.error(f"设置全图表布局失败: {str(e)}")

    def clear_splitter(self):
        """清空分割器"""
        try:
            # 移除所有子控件但不删除
            while self.main_splitter.count() > 0:
                child = self.main_splitter.widget(0)
                child.setParent(None)

            # 确保所有面板可见
            if self.left_panel:
                self.left_panel.setVisible(True)
            if self.middle_panel:
                self.middle_panel.setVisible(True)
            if self.right_panel:
                self.right_panel.setVisible(True)
            if self.bottom_panel:
                self.bottom_panel.setVisible(True)

        except Exception as e:
            self.log_manager.error(f"清空分割器失败: {str(e)}")

    def init_signals(self):
        """初始化信号连接"""
        try:
            # 连接左侧面板信号
            if self.left_panel:
                self.left_panel.stock_selected.connect(self.on_stock_selected)
                self.left_panel.stock_double_clicked.connect(self.on_stock_double_clicked)
                self.left_panel.filter_changed.connect(self.on_filter_changed)

            # 连接中间面板信号
            if self.middle_panel:
                self.middle_panel.chart_updated.connect(self.on_chart_updated)
                self.middle_panel.indicator_changed.connect(self.on_indicator_changed)
                self.middle_panel.timeframe_changed.connect(self.on_timeframe_changed)

            # 连接右侧面板信号
            if self.right_panel:
                self.right_panel.analysis_completed.connect(self.on_analysis_completed)
                self.right_panel.data_requested.connect(self.on_data_requested)
                self.right_panel.error_occurred.connect(self.on_error_occurred)

            # 连接分割器信号
            if self.main_splitter:
                self.main_splitter.splitterMoved.connect(self.on_splitter_moved)

            self.log_manager.info("主布局信号连接完成")

        except Exception as e:
            self.log_manager.error(f"初始化信号连接失败: {str(e)}")

    def on_stock_selected(self, stock_code: str):
        """处理股票选择事件"""
        try:
            # 更新中间面板显示
            if self.middle_panel:
                self.middle_panel.set_stock_code(stock_code)

            # 更新右侧面板分析
            if self.right_panel:
                self.right_panel.set_stock_code(stock_code)

            # 发送数据流信号
            self.data_flow.emit("stock_selected", {"stock_code": stock_code})

            self.log_manager.info(f"股票选择: {stock_code}")

        except Exception as e:
            self.log_manager.error(f"处理股票选择事件失败: {str(e)}")

    def on_stock_double_clicked(self, stock_code: str):
        """处理股票双击事件"""
        try:
            # 切换到全图表布局
            self.switch_layout("full_chart")

            # 更新图表显示
            if self.middle_panel:
                self.middle_panel.set_stock_code(stock_code)
                self.middle_panel.focus_chart()

            self.log_manager.info(f"股票双击: {stock_code}")

        except Exception as e:
            self.log_manager.error(f"处理股票双击事件失败: {str(e)}")

    def on_filter_changed(self, filter_text: str):
        """处理筛选变化事件"""
        self.data_flow.emit("filter_changed", {"filter_text": filter_text})

    def on_chart_updated(self, chart_info: Dict[str, Any]):
        """处理图表更新事件"""
        self.data_flow.emit("chart_updated", chart_info)

    def on_indicator_changed(self, indicators: list):
        """处理指标变化事件"""
        self.data_flow.emit("indicator_changed", {"indicators": indicators})

    def on_timeframe_changed(self, timeframe: str):
        """处理时间周期变化事件"""
        try:
            # 更新所有相关面板
            if self.middle_panel:
                self.middle_panel.set_timeframe(timeframe)

            if self.right_panel:
                self.right_panel.set_timeframe(timeframe)

            self.data_flow.emit("timeframe_changed", {"timeframe": timeframe})

        except Exception as e:
            self.log_manager.error(f"处理时间周期变化失败: {str(e)}")

    def on_analysis_completed(self, results: Dict[str, Any]):
        """处理分析完成事件"""
        self.data_flow.emit("analysis_completed", results)

    def on_data_requested(self, request: Dict[str, Any]):
        """处理数据请求事件"""
        self.data_flow.emit("data_requested", request)

    def on_error_occurred(self, error_msg: str):
        """处理错误事件"""
        self.log_manager.error(f"面板错误: {error_msg}")

    def on_splitter_moved(self, pos: int, index: int):
        """处理分割器移动事件"""
        try:
            sizes = self.main_splitter.sizes()
            self.panel_sizes[self.current_layout] = sizes
            self.panel_resized.emit(self.current_layout, pos)

        except Exception as e:
            self.log_manager.error(f"处理分割器移动失败: {str(e)}")

    def switch_layout(self, layout_type: str):
        """切换布局类型"""
        try:
            if layout_type == "standard":
                self.setup_standard_layout()
            elif layout_type == "compact":
                self.setup_compact_layout()
            elif layout_type == "full_chart":
                self.setup_full_chart_layout()
            else:
                self.log_manager.warning(f"未知的布局类型: {layout_type}")

        except Exception as e:
            self.log_manager.error(f"切换布局失败: {str(e)}")

    def toggle_panel_visibility(self, panel_name: str, visible: bool = None):
        """切换面板可见性"""
        try:
            panel = getattr(self, f"{panel_name}_panel", None)
            if panel:
                if visible is None:
                    visible = not panel.isVisible()
                panel.setVisible(visible)
                self.log_manager.info(f"面板 {panel_name} 可见性: {visible}")
            else:
                self.log_manager.warning(f"未找到面板: {panel_name}")

        except Exception as e:
            self.log_manager.error(f"切换面板可见性失败: {str(e)}")

    def get_panel_sizes(self) -> Dict[str, list]:
        """获取面板大小配置"""
        return self.panel_sizes

    def set_panel_sizes(self, layout_type: str, sizes: list):
        """设置面板大小"""
        try:
            self.panel_sizes[layout_type] = sizes
            if layout_type == self.current_layout and self.main_splitter:
                self.main_splitter.setSizes(sizes)

        except Exception as e:
            self.log_manager.error(f"设置面板大小失败: {str(e)}")

    def save_layout_config(self) -> Dict[str, Any]:
        """保存布局配置"""
        try:
            config = {
                "current_layout": self.current_layout,
                "panel_sizes": self.panel_sizes,
                "panel_visibility": {
                    "left": self.left_panel.isVisible() if self.left_panel else True,
                    "middle": self.middle_panel.isVisible() if self.middle_panel else True,
                    "right": self.right_panel.isVisible() if self.right_panel else True,
                    "bottom": self.bottom_panel.isVisible() if self.bottom_panel else True,
                }
            }
            return config

        except Exception as e:
            self.log_manager.error(f"保存布局配置失败: {str(e)}")
            return {}

    def load_layout_config(self, config: Dict[str, Any]):
        """加载布局配置"""
        try:
            # 恢复布局类型
            layout_type = config.get("current_layout", "standard")
            self.switch_layout(layout_type)

            # 恢复面板大小
            panel_sizes = config.get("panel_sizes", {})
            for layout, sizes in panel_sizes.items():
                self.set_panel_sizes(layout, sizes)

            # 恢复面板可见性
            panel_visibility = config.get("panel_visibility", {})
            for panel_name, visible in panel_visibility.items():
                self.toggle_panel_visibility(panel_name, visible)

            self.log_manager.info("布局配置加载完成")

        except Exception as e:
            self.log_manager.error(f"加载布局配置失败: {str(e)}")

    def get_current_layout(self) -> str:
        """获取当前布局类型"""
        return self.current_layout

    def get_left_panel(self) -> Optional[StockManagementPanel]:
        """获取左侧面板"""
        return self.left_panel

    def get_middle_panel(self) -> Optional[ChartAnalysisPanel]:
        """获取中间面板"""
        return self.middle_panel

    def get_right_panel(self) -> Optional[AnalysisToolsPanel]:
        """获取右侧面板"""
        return self.right_panel

    def get_bottom_panel(self) -> Optional[QTabWidget]:
        """获取底部面板"""
        return self.bottom_panel

    def set_bottom_panel(self, bottom_panel):
        """设置底部面板"""
        try:
            if self.bottom_panel:
                # 移除旧的底部面板
                self.bottom_panel.setParent(None)

            self.bottom_panel = bottom_panel

            # 添加到中间容器
            if self.middle_container:
                layout = self.middle_container.layout()
                if layout:
                    layout.addWidget(self.bottom_panel)

        except Exception as e:
            self.log_manager.error(f"设置底部面板失败: {str(e)}")

    def get_all_panels(self) -> Dict[str, QWidget]:
        """获取所有面板"""
        return {
            "left": self.left_panel,
            "middle": self.middle_panel,
            "right": self.right_panel,
            "bottom": self.bottom_panel
        }
