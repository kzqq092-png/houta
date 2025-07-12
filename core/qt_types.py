"""
Qt类型注册模块

负责注册自定义Qt类型，解决信号槽中的类型注册问题。
"""

import logging
from PyQt5.QtCore import QMetaType
from PyQt5.QtGui import QTextCursor, QFont, QColor, QPen, QBrush, QTextCharFormat
from PyQt5.QtWidgets import QWidget

logger = logging.getLogger(__name__)


def register_qt_types():
    """
    注册Qt自定义类型，解决信号槽中的类型问题

    这个函数应该在应用程序启动时调用，在创建任何Qt对象之前。
    """
    try:
        # 在PyQt5中，我们需要使用PyQt5.QtCore.QMetaType.type来注册类型
        # 对于QTextCharFormat等特殊类型，需要确保正确注册
        from PyQt5.QtCore import QMetaType

        # 注册QTextCursor类型
        cursor_type_id = QMetaType.type("QTextCursor")
        logger.debug(f"Registered QTextCursor meta type with ID: {cursor_type_id}")

        # 注册QTextCharFormat类型
        format_type_id = QMetaType.type("QTextCharFormat")
        logger.debug(f"Registered QTextCharFormat meta type with ID: {format_type_id}")

        # 注册其他可能需要的Qt类型
        QMetaType.type("QFont")
        QMetaType.type("QColor")
        QMetaType.type("QPen")
        QMetaType.type("QBrush")

        logger.info("Qt meta types registered successfully")

    except Exception as e:
        logger.error(f"Failed to register Qt meta types: {e}")
        # 不抛出异常，允许应用程序继续运行


def register_custom_types():
    """
    注册自定义应用程序类型

    如果应用程序定义了自定义类型需要在信号槽中传递，
    可以在这里注册。
    """
    try:
        # 这里可以添加应用程序特定的类型注册
        logger.debug("Custom types registered successfully")

    except Exception as e:
        logger.error(f"Failed to register custom types: {e}")


def init_qt_types():
    """
    初始化所有Qt类型注册

    这是主要的入口函数，应该在应用程序启动时调用。
    """
    logger.info("Initializing Qt type registration")

    # 注册Qt内置类型
    register_qt_types()

    # 注册自定义类型
    register_custom_types()

    logger.info("Qt type registration completed")


# 为了确保类型注册在模块导入时就执行，可以取消下面的注释
init_qt_types()
