"""
UI组件模块 - 重构后版本

这个模块现在只包含必要的导入和工具函数。
主要的UI组件已经拆分到专门的模块中：
- 面板组件：gui.panels
- 处理器组件：gui.handlers  
- 核心组件：gui.core
- 布局组件：gui.layouts
- 功能组件：gui.features
"""

# 导入重构后的模块
from .panels.base_analysis_panel import BaseAnalysisPanel
from .panels.analysis_tools_panel import AnalysisToolsPanel
from gui.panels import ChartAnalysisPanel
from .panels.bottom_panel import BottomPanel

from .handlers import (
    MenuHandler,
    EventHandler,
    ChartHandler
)

from .core import (
    BaseTradingGUI,
    TradingGUICore
)

from .layouts import (
    MainLayout
)

from .features import (
    OptimizationFeatures
)

from .components import (
    StatusBar,
    StockListWidget,
    GlobalExceptionHandler,
    safe_strftime,
    add_shadow
)

# 为了向后兼容，保留一些常用的导入
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QProgressBar, QTextEdit,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QStatusBar, QToolBar, QMenuBar, QMenu, QAction,
    QFileDialog, QMessageBox, QSplitter, QTabWidget,
    QGridLayout, QToolTip, QListWidget, QTableWidget,
    QTableWidgetItem, QListWidgetItem, QDialog, QCheckBox,
    QHeaderView, QInputDialog, QAbstractItemView,
    QTreeWidget, QTreeWidgetItem, QCompleter
)

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QObject, QPointF
from PyQt5.QtGui import QIcon, QColor, QBrush

# 导入面板组件
from .panels.stock_panel import StockManagementPanel
from .panels.analysis_panel import AnalysisPanel

# 导出所有重要的类和函数
__all__ = [
    # 面板组件
    'BaseAnalysisPanel',
    'AnalysisToolsPanel',
    'ChartAnalysisPanel',
    'BottomPanel',
    'StockManagementPanel',
    'AnalysisPanel',

    # 处理器组件
    'MenuHandler',
    'EventHandler',
    'ChartHandler',

    # 核心组件
    'BaseTradingGUI',
    'TradingGUICore',

    # 布局组件
    'MainLayout',

    # 功能组件
    'OptimizationFeatures',

    # 基础组件
    'StatusBar',
    'StockListWidget',
    'GlobalExceptionHandler',

    # 工具函数
    'safe_strftime',
    'add_shadow'
]


def get_available_components():
    """获取所有可用的UI组件列表"""
    return {
        'panels': [
            'BaseAnalysisPanel',
            'AnalysisToolsPanel',
            'ChartAnalysisPanel',
            'BottomPanel',
            'StockManagementPanel',
            'AnalysisPanel'
        ],
        'handlers': [
            'MenuHandler',
            'EventHandler',
            'ChartHandler'
        ],
        'core': [
            'BaseTradingGUI',
            'TradingGUICore'
        ],
        'layouts': [
            'MainLayout'
        ],
        'features': [
            'OptimizationFeatures'
        ],
        'components': [
            'StatusBar',
            'StockListWidget',
            'GlobalExceptionHandler'
        ]
    }


def create_component(component_type: str, component_name: str, *args, **kwargs):
    """
    工厂函数：根据类型和名称创建组件实例

    Args:
        component_type: 组件类型 ('panels', 'handlers', 'core', 'layouts', 'features', 'components')
        component_name: 组件名称
        *args, **kwargs: 传递给组件构造函数的参数

    Returns:
        组件实例
    """
    available_components = get_available_components()

    if component_type not in available_components:
        raise ValueError(f"不支持的组件类型: {component_type}")

    if component_name not in available_components[component_type]:
        raise ValueError(f"不支持的组件名称: {component_name}")

    # 获取组件类
    component_class = globals().get(component_name)
    if not component_class:
        raise ValueError(f"找不到组件类: {component_name}")

    # 创建实例
    return component_class(*args, **kwargs)


def get_component_info(component_name: str) -> dict:
    """
    获取组件信息

    Args:
        component_name: 组件名称

    Returns:
        包含组件信息的字典
    """
    component_class = globals().get(component_name)
    if not component_class:
        return {}

    return {
        'name': component_name,
        'module': component_class.__module__,
        'doc': component_class.__doc__ or '',
        'methods': [method for method in dir(component_class)
                    if not method.startswith('_') and callable(getattr(component_class, method))]
    }


# 向后兼容性支持
def create_analysis_tools_panel(*args, **kwargs):
    """创建分析工具面板（向后兼容）"""
    return AnalysisToolsPanel(*args, **kwargs)


def create_status_bar(*args, **kwargs):
    """创建状态栏（向后兼容）"""
    return StatusBar(*args, **kwargs)


def create_left_panel(*args, **kwargs):
    """创建左侧面板（向后兼容）"""
    return LeftPanel(*args, **kwargs)


def create_middle_panel(*args, **kwargs):
    """创建中间面板（向后兼容）"""
    return ChartAnalysisPanel(*args, **kwargs)


def create_bottom_panel(*args, **kwargs):
    """创建底部面板（向后兼容）"""
    return BottomPanel(*args, **kwargs)


# 模块信息
MODULE_INFO = {
    'name': 'ui_components',
    'version': '2.0.0',
    'description': '重构后的UI组件模块，采用模块化设计',
    'refactored_date': '2025-01-15',
    'total_components': len(__all__)
}


def print_module_info():
    """打印模块信息"""
    print("=" * 50)
    print(f"模块名称: {MODULE_INFO['name']}")
    print(f"版本: {MODULE_INFO['version']}")
    print(f"描述: {MODULE_INFO['description']}")
    print(f"重构日期: {MODULE_INFO['refactored_date']}")
    print(f"组件总数: {MODULE_INFO['total_components']}")
    print("=" * 50)

    print("\n可用组件:")
    components = get_available_components()
    for category, items in components.items():
        print(f"\n{category.upper()}:")
        for item in items:
            print(f"  - {item}")


if __name__ == "__main__":
    print_module_info()
