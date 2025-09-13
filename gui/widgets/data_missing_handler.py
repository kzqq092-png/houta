#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据缺失智能处理UI组件
提供数据缺失时的智能提示和引导功能
"""

import sys
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGroupBox, QProgressBar, QComboBox,
    QTextEdit, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QDialog, QDialogButtonBox,
    QCheckBox, QSpinBox, QDateEdit, QApplication
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QDate, QPropertyAnimation,
    QEasingCurve, QRect, QParallelAnimationGroup
)
from PyQt5.QtGui import (
    QFont, QPixmap, QPainter, QColor, QLinearGradient,
    QPen, QBrush, QIcon, QPalette
)

# 导入核心组件
try:
    from core.plugin_types import AssetType, DataType, PluginType
    from core.asset_type_identifier import AssetTypeIdentifier
    from core.data_router import DataRouter
    from core.services.asset_aware_unified_data_manager import AssetAwareUnifiedDataManager
    from loguru import logger
except ImportError as e:
    print(f"导入核心组件失败: {e}")
    logger = None


class DataMissingReason(Enum):
    """数据缺失原因枚举"""
    NOT_DOWNLOADED = "not_downloaded"  # 数据未下载
    PLUGIN_DISABLED = "plugin_disabled"  # 插件未启用
    NETWORK_ERROR = "network_error"  # 网络错误
    DATA_SOURCE_ERROR = "data_source_error"  # 数据源错误
    PERMISSION_ERROR = "permission_error"  # 权限错误
    UNKNOWN_ERROR = "unknown_error"  # 未知错误


@dataclass
class DataMissingInfo:
    """数据缺失信息"""
    symbol: str
    asset_type: AssetType
    data_type: DataType
    reason: DataMissingReason
    error_message: str
    suggested_plugins: List[str]
    date_range: Optional[tuple] = None
    priority: int = 1  # 1-5, 5最高优先级


class ModernCard(QFrame):
    """现代化卡片组件"""

    def __init__(self, title: str, content: str = "", icon: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.content = content
        self.icon = icon
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            ModernCard {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin: 4px;
            }
            ModernCard:hover {
                border-color: #2196F3;
                box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题行
        title_layout = QHBoxLayout()

        if self.icon:
            icon_label = QLabel(self.icon)
            icon_label.setFont(QFont("Arial", 14))
            title_layout.addWidget(icon_label)

        title_label = QLabel(self.title)
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setStyleSheet("color: #333333;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 内容
        if self.content:
            content_label = QLabel(self.content)
            content_label.setFont(QFont("Arial", 10))
            content_label.setStyleSheet("color: #666666;")
            content_label.setWordWrap(True)
            layout.addWidget(content_label)

    def update_content(self, content: str):
        """更新内容"""
        self.content = content
        # 找到内容标签并更新
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and isinstance(item.widget(), QLabel):
                widget = item.widget()
                if widget.font().pointSize() == 10:  # 内容标签
                    widget.setText(content)
                    break


class DataMissingPromptWidget(QWidget):
    """数据缺失提示组件"""

    # 信号
    download_requested = pyqtSignal(str, str, str)  # symbol, asset_type, data_type
    plugin_config_requested = pyqtSignal(str)  # plugin_name
    data_management_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.missing_data_info: List[DataMissingInfo] = []
        self.asset_identifier = None
        self.data_router = None
        self.data_manager = None

        self.setup_ui()
        self.setup_connections()

        # 初始化核心组件
        QTimer.singleShot(100, self.init_core_components)

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 主容器
        self.main_container = QFrame()
        self.main_container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
        """)

        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)

        # 标题区域
        title_layout = QHBoxLayout()

        self.icon_label = QLabel("⚠️")
        self.icon_label.setFont(QFont("Arial", 16))
        title_layout.addWidget(self.icon_label)

        self.title_label = QLabel("数据缺失提醒")
        self.title_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #495057;")
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #6c757d;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-radius: 12px;
            }
        """)
        self.close_btn.clicked.connect(self.hide)
        title_layout.addWidget(self.close_btn)

        container_layout.addLayout(title_layout)

        # 内容区域
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)

        self.content_area.setWidget(self.content_widget)
        container_layout.addWidget(self.content_area)

        # 操作按钮区域
        button_layout = QHBoxLayout()

        self.data_management_btn = QPushButton("📊 数据管理")
        self.data_management_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.data_management_btn.clicked.connect(self.data_management_requested.emit)

        self.plugin_config_btn = QPushButton("🔧 插件配置")
        self.plugin_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e7e34;
            }
        """)

        button_layout.addWidget(self.data_management_btn)
        button_layout.addWidget(self.plugin_config_btn)
        button_layout.addStretch()

        container_layout.addLayout(button_layout)

        layout.addWidget(self.main_container)

        # 默认隐藏
        self.hide()

    def setup_connections(self):
        """设置信号连接"""
        pass

    def init_core_components(self):
        """初始化核心组件"""
        try:
            self.asset_identifier = AssetTypeIdentifier()
            self.data_router = DataRouter()
            self.data_manager = AssetAwareUnifiedDataManager()

            if logger:
                logger.info("数据缺失处理组件初始化完成")
        except Exception as e:
            if logger:
                logger.error(f"初始化核心组件失败: {e}")

    def show_data_missing(self, symbol: str, data_type: str, error_message: str = ""):
        """显示数据缺失提示"""
        try:
            # 识别资产类型
            asset_type = AssetType.STOCK_A  # 默认值
            if self.asset_identifier:
                asset_type = self.asset_identifier.identify_asset_type(symbol)

            # 分析缺失原因
            reason = self._analyze_missing_reason(error_message)

            # 获取建议的插件
            suggested_plugins = self._get_suggested_plugins(asset_type, data_type)

            # 创建缺失信息
            missing_info = DataMissingInfo(
                symbol=symbol,
                asset_type=asset_type,
                data_type=DataType.HISTORICAL_KLINE if data_type == "historical" else DataType.REAL_TIME_QUOTE,
                reason=reason,
                error_message=error_message,
                suggested_plugins=suggested_plugins
            )

            self.missing_data_info.append(missing_info)
            self._update_display()
            self._show_with_animation()

        except Exception as e:
            if logger:
                logger.error(f"显示数据缺失提示失败: {e}")

    def _analyze_missing_reason(self, error_message: str) -> DataMissingReason:
        """分析数据缺失原因"""
        error_lower = error_message.lower()

        if "not found" in error_lower or "不存在" in error_lower:
            return DataMissingReason.NOT_DOWNLOADED
        elif "plugin" in error_lower or "插件" in error_lower:
            return DataMissingReason.PLUGIN_DISABLED
        elif "network" in error_lower or "网络" in error_lower:
            return DataMissingReason.NETWORK_ERROR
        elif "permission" in error_lower or "权限" in error_lower:
            return DataMissingReason.PERMISSION_ERROR
        else:
            return DataMissingReason.UNKNOWN_ERROR

    def _get_suggested_plugins(self, asset_type: AssetType, data_type: str) -> List[str]:
        """获取建议的插件"""
        suggestions = []

        if asset_type in [AssetType.STOCK_A, AssetType.STOCK_B]:
            suggestions.extend(["tongdaxin_stock_plugin", "eastmoney_stock_plugin"])
        elif asset_type == AssetType.CRYPTO:
            suggestions.extend(["binance_plugin", "coinbase_plugin"])
        elif asset_type == AssetType.STOCK_US:
            suggestions.extend(["yahoo_finance_plugin", "alpha_vantage_plugin"])

        return suggestions

    def _update_display(self):
        """更新显示内容"""
        # 清空现有内容
        for i in reversed(range(self.content_layout.count())):
            child = self.content_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # 按优先级排序
        sorted_info = sorted(self.missing_data_info, key=lambda x: x.priority, reverse=True)

        for info in sorted_info:
            card = self._create_missing_data_card(info)
            self.content_layout.addWidget(card)

        self.content_layout.addStretch()

        # 更新标题
        count = len(self.missing_data_info)
        self.title_label.setText(f"数据缺失提醒 ({count})")

    def _create_missing_data_card(self, info: DataMissingInfo) -> QWidget:
        """创建数据缺失卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dee2e6;
                border-left: 4px solid #dc3545;
                border-radius: 4px;
                margin: 2px 0;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # 标题行
        title_layout = QHBoxLayout()

        symbol_label = QLabel(f"📈 {info.symbol}")
        symbol_label.setFont(QFont("Arial", 11, QFont.Bold))
        symbol_label.setStyleSheet("color: #495057;")
        title_layout.addWidget(symbol_label)

        asset_label = QLabel(f"[{info.asset_type.value}]")
        asset_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        title_layout.addWidget(asset_label)

        title_layout.addStretch()

        # 数据类型标签
        data_type_label = QLabel(info.data_type.value)
        data_type_label.setStyleSheet("""
            background-color: #e9ecef;
            color: #495057;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
        """)
        title_layout.addWidget(data_type_label)

        layout.addLayout(title_layout)

        # 错误信息
        if info.error_message:
            error_label = QLabel(f"错误: {info.error_message}")
            error_label.setStyleSheet("color: #dc3545; font-size: 10px;")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)

        # 建议插件
        if info.suggested_plugins:
            plugins_layout = QHBoxLayout()
            plugins_layout.addWidget(QLabel("建议插件:"))

            for plugin in info.suggested_plugins[:3]:  # 最多显示3个
                plugin_btn = QPushButton(plugin.replace("_plugin", ""))
                plugin_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border: none;
                        padding: 2px 8px;
                        border-radius: 3px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                """)
                plugin_btn.clicked.connect(lambda checked, p=plugin: self.plugin_config_requested.emit(p))
                plugins_layout.addWidget(plugin_btn)

            plugins_layout.addStretch()
            layout.addLayout(plugins_layout)

        # 操作按钮
        action_layout = QHBoxLayout()

        download_btn = QPushButton("📥 下载数据")
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #1e7e34;
            }
        """)
        download_btn.clicked.connect(
            lambda: self.download_requested.emit(
                info.symbol,
                info.asset_type.value,
                info.data_type.value
            )
        )

        ignore_btn = QPushButton("❌ 忽略")
        ignore_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        ignore_btn.clicked.connect(lambda: self._remove_missing_info(info))

        action_layout.addWidget(download_btn)
        action_layout.addWidget(ignore_btn)
        action_layout.addStretch()

        layout.addLayout(action_layout)

        return card

    def _remove_missing_info(self, info: DataMissingInfo):
        """移除缺失信息"""
        if info in self.missing_data_info:
            self.missing_data_info.remove(info)
            self._update_display()

            if not self.missing_data_info:
                self.hide()

    def _show_with_animation(self):
        """带动画显示"""
        if not self.isVisible():
            self.show()

            # 创建淡入动画
            self.animation = QPropertyAnimation(self, b"windowOpacity")
            self.animation.setDuration(300)
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.setEasingCurve(QEasingCurve.OutCubic)
            self.animation.start()

    def clear_all(self):
        """清空所有缺失信息"""
        self.missing_data_info.clear()
        self._update_display()
        self.hide()


class DataDownloadDialog(QDialog):
    """数据下载对话框"""

    download_started = pyqtSignal(str, str, str, dict)  # symbol, asset_type, data_type, options

    def __init__(self, symbol: str, asset_type: str, data_type: str, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.asset_type = asset_type
        self.data_type = data_type

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(f"下载数据 - {self.symbol}")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # 基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QVBoxLayout(info_group)

        info_layout.addWidget(QLabel(f"股票代码: {self.symbol}"))
        info_layout.addWidget(QLabel(f"资产类型: {self.asset_type}"))
        info_layout.addWidget(QLabel(f"数据类型: {self.data_type}"))

        layout.addWidget(info_group)

        # 下载选项
        options_group = QGroupBox("下载选项")
        options_layout = QVBoxLayout(options_group)

        # 日期范围
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("开始日期:"))

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setCalendarPopup(True)
        date_layout.addWidget(self.start_date)

        date_layout.addWidget(QLabel("结束日期:"))

        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_layout.addWidget(self.end_date)

        options_layout.addLayout(date_layout)

        # 数据源选择
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("数据源:"))

        self.source_combo = QComboBox()
        self.source_combo.addItems(["自动选择", "通达信", "东方财富", "新浪财经", "腾讯财经"])
        source_layout.addWidget(self.source_combo)

        options_layout.addLayout(source_layout)

        # 其他选项
        self.overwrite_check = QCheckBox("覆盖已有数据")
        options_layout.addWidget(self.overwrite_check)

        self.validate_check = QCheckBox("数据验证")
        self.validate_check.setChecked(True)
        options_layout.addWidget(self.validate_check)

        layout.addWidget(options_group)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def setup_connections(self):
        """设置信号连接"""
        pass

    def accept(self):
        """确认下载"""
        options = {
            'start_date': self.start_date.date().toString('yyyy-MM-dd'),
            'end_date': self.end_date.date().toString('yyyy-MM-dd'),
            'data_source': self.source_combo.currentText(),
            'overwrite': self.overwrite_check.isChecked(),
            'validate': self.validate_check.isChecked()
        }

        self.download_started.emit(self.symbol, self.asset_type, self.data_type, options)
        super().accept()


# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 创建测试窗口
    widget = DataMissingPromptWidget()
    widget.resize(600, 400)
    widget.show()

    # 模拟数据缺失
    QTimer.singleShot(1000, lambda: widget.show_data_missing("000001", "historical", "数据不存在"))
    QTimer.singleShot(2000, lambda: widget.show_data_missing("600000", "realtime", "插件未启用"))

    sys.exit(app.exec_())
