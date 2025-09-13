from loguru import logger
"""
Qt类型注册模块

负责注册自定义Qt类型，解决信号槽中的类型注册问题。
"""

from PyQt5.QtCore import QMetaType, qRegisterMetaType, QObject, pyqtSignal, pyqtProperty, QVariant, QMetaObject, Qt, Q_ARG
from PyQt5.QtGui import QTextCursor, QFont, QColor, QPen, QBrush, QTextCharFormat
from PyQt5.QtWidgets import QWidget
from typing import Dict, Any, List

logger = logger


def init_qt_types():
    """
    集中注册所有需要跨线程使用的自定义信号和复杂数据类型。
    这个函数应该在应用程序启动时尽早调用。
    """
    logger.info("Initializing Qt type registration...")

    types_to_register = {
        "QTextCursor": QTextCursor,
        "QTextCharFormat": QTextCharFormat,
        "QFont": QFont,
        "QColor": QColor,
        "QPen": QPen,
        "QBrush": QBrush
    }

    for name, type_class in types_to_register.items():
        try:
            # 使用正确的语法注册元类型
            type_id = qRegisterMetaType(name)
            logger.debug(f"Successfully registered {name}, type ID: {type_id}")
        except Exception as e:
            logger.error(f"Failed to register {name}: {e}")

    # 动态导入并注册自定义事件类型
    try:
        from .events import UIDataReadyEvent, StockSelectedEvent, IndicatorChangedEvent
        qRegisterMetaType(UIDataReadyEvent)
        qRegisterMetaType(StockSelectedEvent)
        qRegisterMetaType(IndicatorChangedEvent)
        logger.debug("Successfully registered custom event types.")
    except Exception as e:
        logger.error(f"Failed to register custom event types: {e}")

    logger.info("Qt type registration completed.")


# 确保类型注册在模块导入时就执行
init_qt_types()
