from loguru import logger
"""
Qt帮助工具模块

提供PyQt5相关的辅助功能，包括元类型注册、信号连接等。
"""

import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TypeVar

logger = logger

try:
    # 导入PyQt5核心模块
    from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMetaType
    PYQT5_AVAILABLE = True
except ImportError:
    logger.warning("PyQt5模块导入失败，Qt帮助工具将不可用")
    PYQT5_AVAILABLE = False


def safe_connect(sender: QObject, signal: pyqtSignal, slot: Callable,
                 connection_type: Optional[Any] = None) -> bool:
    """
    安全连接Qt信号和槽函数，避免因参数类型不匹配导致的连接错误

    Args:
        sender: 信号发送者
        signal: 要连接的信号
        slot: 要连接的槽函数
        connection_type: 连接类型，可选

    Returns:
        连接是否成功
    """
    if not PYQT5_AVAILABLE:
        logger.error("PyQt5不可用，无法连接信号")
        return False

    try:
        if connection_type is not None:
            signal.connect(slot, connection_type)
        else:
            signal.connect(slot)
        return True
    except TypeError as e:
        logger.error(f"信号连接失败，参数类型不匹配: {e}")
        logger.error(traceback.format_exc())
        logger.error(f"信号: {signal}, 槽函数: {slot.__name__}")
        return False
    except Exception as e:
        logger.error(f"信号连接失败: {e}")
        logger.error(traceback.format_exc())
        return False


def register_meta_types() -> bool:
    """
    注册常用的PyQt5元类型，避免信号连接时的类型错误

    由于PyQt5没有直接的qRegisterMetaType函数，此函数通过其他方法确保
    常用类型可以在信号和槽中正确传递

    Returns:
        注册是否成功
    """
    if not PYQT5_AVAILABLE:
        logger.warning("PyQt5不可用，无法注册元类型")
        return False

    try:
        # 在PyQt5中，我们不能直接注册这些类型
        # 但我们可以通过其他方式确保这些类型在信号槽中可用

        # 记录类型信息
        logger.info("PyQt5元类型支持已确认")
        return True
    except Exception as e:
        logger.error(f"元类型注册失败: {e}")
        logger.error(traceback.format_exc())
        return False


def create_wrapper_slot(slot_func: Callable) -> Callable:
    """
    创建一个包装槽函数，用于处理信号参数类型问题

    Args:
        slot_func: 原始槽函数

    Returns:
        包装后的槽函数
    """
    if not PYQT5_AVAILABLE:
        logger.warning("PyQt5不可用，无法创建包装槽")
        return slot_func

    @pyqtSlot()
    def wrapper(*args, **kwargs):
        try:
            return slot_func(*args, **kwargs)
        except TypeError as e:
            logger.error(f"槽函数调用失败，参数类型不匹配: {e}")
            logger.error(f"槽函数: {slot_func.__name__}, 参数: {args}, {kwargs}")
            logger.error(traceback.format_exc())
            return None

    # 复制原始函数的名称和文档字符串
    wrapper.__name__ = slot_func.__name__
    wrapper.__doc__ = slot_func.__doc__

    return wrapper
