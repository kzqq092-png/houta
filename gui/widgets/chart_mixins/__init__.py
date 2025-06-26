"""
图表控件Mixin模块

该模块将ChartWidget的功能按逻辑分组到不同的Mixin类中，
通过多重继承组合成完整的ChartWidget功能。

每个Mixin专注于特定的功能领域：
- BaseMixin: 基础初始化和配置管理
- UIMixin: UI初始化和布局管理
- RenderingMixin: 图表渲染相关功能
- IndicatorMixin: 技术指标计算和显示
- CrosshairMixin: 十字光标功能
- InteractionMixin: 用户交互功能
- ZoomMixin: 缩放和平移功能
- SignalMixin: 交易信号处理
- ExportMixin: 导出功能
- UtilityMixin: 工具方法
"""

from .base_mixin import BaseMixin
from .ui_mixin import UIMixin
from .rendering_mixin import RenderingMixin
from .indicator_mixin import IndicatorMixin
from .crosshair_mixin import CrosshairMixin
from .interaction_mixin import InteractionMixin
from .zoom_mixin import ZoomMixin
from .signal_mixin import SignalMixin
from .export_mixin import ExportMixin
from .utility_mixin import UtilityMixin

__all__ = [
    'BaseMixin',
    'UIMixin',
    'RenderingMixin',
    'IndicatorMixin',
    'CrosshairMixin',
    'InteractionMixin',
    'ZoomMixin',
    'SignalMixin',
    'ExportMixin',
    'UtilityMixin'
]

__version__ = '1.0.0'
__author__ = '20年Python量化架构师'
__description__ = 'ChartWidget功能拆分Mixin模块'
