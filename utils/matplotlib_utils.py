"""
Matplotlib工具模块

提供matplotlib相关的工具函数，包括安全的布局调整、警告抑制等功能
"""

import warnings
from typing import Optional
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def safe_tight_layout(figure: Figure, **kwargs) -> bool:
    """
    安全地应用tight_layout，如果失败则使用subplots_adjust作为备选

    Args:
        figure: matplotlib Figure对象
        **kwargs: tight_layout的参数

    Returns:
        bool: 是否成功应用tight_layout
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning,
                                    message=".*Tight layout not applied.*")
            warnings.filterwarnings("ignore", category=UserWarning,
                                    message=".*margins cannot be made large enough.*")
            figure.tight_layout(**kwargs)
        return True
    except Exception:
        # 如果tight_layout失败，使用subplots_adjust作为备选
        figure.subplots_adjust(
            left=kwargs.get('pad', 0.02),
            right=1 - kwargs.get('pad', 0.02),
            top=1 - kwargs.get('pad', 0.02),
            bottom=kwargs.get('pad', 0.02),
            hspace=kwargs.get('h_pad', 0.1),
            wspace=kwargs.get('w_pad', 0.1)
        )
        return False


def suppress_matplotlib_warnings():
    """抑制matplotlib相关的警告"""
    warnings.filterwarnings("ignore", category=UserWarning,
                            message=".*Tight layout not applied.*")
    warnings.filterwarnings("ignore", category=UserWarning,
                            message=".*margins cannot be made large enough.*")
    warnings.filterwarnings("ignore", category=UserWarning,
                            message=".*Axes decorations.*")
    warnings.filterwarnings("ignore", category=UserWarning,
                            message=".*cannot be made large enough.*")


def configure_matplotlib_for_gui():
    """为GUI环境配置matplotlib"""
    # 抑制警告
    suppress_matplotlib_warnings()

    # 设置后端（如果需要）
    try:
        plt.switch_backend('Qt5Agg')
    except Exception:
        pass

    # 设置默认样式
    plt.rcParams.update({
        'figure.autolayout': False,  # 禁用自动布局，使用手动控制
        'figure.constrained_layout.use': False,  # 禁用constrained_layout
        'axes.formatter.useoffset': False,  # 禁用科学计数法
        'font.size': 8,  # 设置默认字体大小
    })


def safe_figure_layout(figure: Figure,
                       left: float = 0.02,
                       right: float = 0.98,
                       top: float = 0.98,
                       bottom: float = 0.02,
                       hspace: float = 0.1,
                       wspace: float = 0.1) -> None:
    """
    安全地设置图表布局

    Args:
        figure: matplotlib Figure对象
        left, right, top, bottom: 边距设置
        hspace, wspace: 子图间距设置
    """
    try:
        # 首先尝试使用tight_layout
        if not safe_tight_layout(figure):
            # 如果失败，使用subplots_adjust
            figure.subplots_adjust(
                left=left, right=right,
                top=top, bottom=bottom,
                hspace=hspace, wspace=wspace
            )
    except Exception:
        # 最后的备选方案
        figure.subplots_adjust(
            left=0.05, right=0.95,
            top=0.95, bottom=0.05,
            hspace=0.2, wspace=0.2
        )


# 在模块导入时自动配置
configure_matplotlib_for_gui()
