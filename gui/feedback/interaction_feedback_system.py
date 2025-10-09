"""
界面交互反馈系统
实现丰富的界面交互反馈和状态提示系统，提供清晰的操作确认和进度指示
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QVBoxLayout, QHBoxLayout,
    QProgressBar, QApplication, QGraphicsOpacityEffect, QMessageBox,
    QToolTip, QSystemTrayIcon, QMenu, QAction, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint,
    QParallelAnimationGroup, QSequentialAnimationGroup, pyqtSignal, QObject
)
from PyQt5.QtGui import (
    QFont, QPalette, QColor, QIcon, QPixmap, QPainter, QBrush, QPen,
    QLinearGradient, QMovie, QCursor
)
import threading

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    LOADING = "loading"
    PROGRESS = "progress"


class FeedbackLevel(Enum):
    """反馈级别枚举"""
    SUBTLE = "subtle"        # 微妙反馈
    NORMAL = "normal"        # 正常反馈
    PROMINENT = "prominent"  # 突出反馈
    CRITICAL = "critical"    # 关键反馈


class AnimationType(Enum):
    """动画类型枚举"""
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    SLIDE_IN = "slide_in"
    SLIDE_OUT = "slide_out"
    BOUNCE = "bounce"
    SHAKE = "shake"
    PULSE = "pulse"
    SCALE = "scale"


@dataclass
class FeedbackConfig:
    """反馈配置数据类"""
    feedback_type: FeedbackType
    level: FeedbackLevel = FeedbackLevel.NORMAL
    duration: int = 3000  # 毫秒
    auto_hide: bool = True
    show_icon: bool = True
    show_close_button: bool = False
    animation_type: AnimationType = AnimationType.FADE_IN
    animation_duration: int = 300
    position: str = "top_right"  # top_left, top_right, bottom_left, bottom_right, center
    sound_enabled: bool = False


@dataclass
class ProgressConfig:
    """进度配置数据类"""
    show_percentage: bool = True
    show_time_remaining: bool = True
    show_speed: bool = False
    animated: bool = True
    color_scheme: str = "default"  # default, success, warning, error
    style: str = "modern"  # classic, modern, minimal


class ToastNotification(QFrame):
    """Toast通知组件"""

    # 信号定义
    clicked = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, message: str, config: FeedbackConfig, parent=None):
        super().__init__(parent)

        self.message = message
        self.config = config
        self.is_closing = False

        self.setup_ui()
        self.setup_animations()
        self.setup_timer()

    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setFixedWidth(300)
        self.setMinimumHeight(60)

        # 设置样式
        self._apply_style()

        # 布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # 图标
        if self.config.show_icon:
            self.icon_label = QLabel()
            self.icon_label.setFixedSize(24, 24)
            self.icon_label.setAlignment(Qt.AlignCenter)
            self._set_icon()
            layout.addWidget(self.icon_label)

        # 消息文本
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(QFont("Microsoft YaHei UI", 10))
        layout.addWidget(self.message_label, 1)

        # 关闭按钮
        if self.config.show_close_button:
            self.close_button = QPushButton("×")
            self.close_button.setFixedSize(20, 20)
            self.close_button.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 10px;
                }
            """)
            self.close_button.clicked.connect(self.close_notification)
            layout.addWidget(self.close_button)

    def _apply_style(self):
        """应用样式"""
        colors = {
            FeedbackType.SUCCESS: "#4CAF50",
            FeedbackType.ERROR: "#F44336",
            FeedbackType.WARNING: "#FF9800",
            FeedbackType.INFO: "#2196F3",
            FeedbackType.LOADING: "#9C27B0",
            FeedbackType.PROGRESS: "#607D8B"
        }

        bg_color = colors.get(self.config.feedback_type, "#2196F3")

        if self.config.level == FeedbackLevel.SUBTLE:
            opacity = "0.8"
        elif self.config.level == FeedbackLevel.PROMINENT:
            opacity = "1.0"
        elif self.config.level == FeedbackLevel.CRITICAL:
            opacity = "1.0"
            bg_color = "#F44336"  # 强制使用错误色
        else:
            opacity = "0.9"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: white;
            }}
        """)

        # 设置透明度
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(float(opacity))
        self.setGraphicsEffect(self.opacity_effect)

    def _set_icon(self):
        """设置图标"""
        icons = {
            FeedbackType.SUCCESS: "[SUCCESS]",
            FeedbackType.ERROR: "[ERROR]",
            FeedbackType.WARNING: "",
            FeedbackType.INFO: "ℹ️",
            FeedbackType.LOADING: "⏳",
            FeedbackType.PROGRESS: ""
        }

        icon_text = icons.get(self.config.feedback_type, "ℹ️")
        self.icon_label.setText(icon_text)
        self.icon_label.setFont(QFont("Arial", 16))

    def setup_animations(self):
        """设置动画"""
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(self.config.animation_duration)

        self.geometry_animation = QPropertyAnimation(self, b"geometry")
        self.geometry_animation.setDuration(self.config.animation_duration)
        self.geometry_animation.setEasingCurve(QEasingCurve.OutCubic)

    def setup_timer(self):
        """设置定时器"""
        if self.config.auto_hide and self.config.duration > 0:
            self.hide_timer = QTimer()
            self.hide_timer.setSingleShot(True)
            self.hide_timer.timeout.connect(self.close_notification)
            self.hide_timer.start(self.config.duration)

    def show_notification(self):
        """显示通知"""
        self.show()

        if self.config.animation_type == AnimationType.FADE_IN:
            self.opacity_effect.setOpacity(0.0)
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(0.9)
            self.fade_animation.start()

        elif self.config.animation_type == AnimationType.SLIDE_IN:
            # 从右侧滑入
            start_pos = self.geometry()
            start_pos.moveLeft(start_pos.x() + 300)
            self.setGeometry(start_pos)

            end_pos = self.geometry()
            end_pos.moveLeft(end_pos.x() - 300)

            self.geometry_animation.setStartValue(start_pos)
            self.geometry_animation.setEndValue(end_pos)
            self.geometry_animation.start()

    def close_notification(self):
        """关闭通知"""
        if self.is_closing:
            return

        self.is_closing = True

        if self.config.animation_type == AnimationType.FADE_OUT:
            self.fade_animation.setStartValue(self.opacity_effect.opacity())
            self.fade_animation.setEndValue(0.0)
            self.fade_animation.finished.connect(self._on_close_finished)
            self.fade_animation.start()
        else:
            self._on_close_finished()

    def _on_close_finished(self):
        """关闭完成"""
        self.closed.emit()
        self.deleteLater()

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ProgressIndicator(QWidget):
    """进度指示器"""

    # 信号定义
    cancelled = pyqtSignal()

    def __init__(self, config: ProgressConfig, parent=None):
        super().__init__(parent)

        self.config = config
        self.current_value = 0
        self.maximum_value = 100
        self.start_time = datetime.now()

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(self.config.show_percentage)

        # 应用样式
        self._apply_progress_style()

        layout.addWidget(self.progress_bar)

        # 详细信息
        info_layout = QHBoxLayout()

        if self.config.show_time_remaining:
            self.time_label = QLabel("预计剩余时间: 计算中...")
            self.time_label.setFont(QFont("Microsoft YaHei UI", 9))
            info_layout.addWidget(self.time_label)

        if self.config.show_speed:
            self.speed_label = QLabel("速度: --")
            self.speed_label.setFont(QFont("Microsoft YaHei UI", 9))
            info_layout.addWidget(self.speed_label)

        info_layout.addStretch()

        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMaximumWidth(60)
        self.cancel_button.clicked.connect(self.cancelled.emit)
        info_layout.addWidget(self.cancel_button)

        layout.addLayout(info_layout)

    def _apply_progress_style(self):
        """应用进度条样式"""
        if self.config.style == "modern":
            if self.config.color_scheme == "success":
                color = "#4CAF50"
            elif self.config.color_scheme == "warning":
                color = "#FF9800"
            elif self.config.color_scheme == "error":
                color = "#F44336"
            else:
                color = "#2196F3"

            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid #E0E0E0;
                    border-radius: 8px;
                    text-align: center;
                    font-weight: bold;
                    background-color: #F5F5F5;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {color}, stop:1 {self._lighten_color(color)});
                    border-radius: 6px;
                }}
            """)

        elif self.config.style == "minimal":
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    background-color: #E0E0E0;
                    height: 4px;
                    border-radius: 2px;
                }
                QProgressBar::chunk {
                    background-color: #2196F3;
                    border-radius: 2px;
                }
            """)

    def _lighten_color(self, color: str) -> str:
        """减淡颜色"""
        # 简化实现
        return color.replace("#", "#FF")[:7] + "80"

    def update_progress(self, value: int, message: str = ""):
        """更新进度"""
        self.current_value = value
        self.progress_bar.setValue(value)

        if message:
            self.progress_bar.setFormat(f"{message} - %p%")

        # 更新时间估算
        if self.config.show_time_remaining and value > 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if value < 100:
                remaining = (elapsed / value) * (100 - value)
                self.time_label.setText(f"预计剩余时间: {self._format_time(remaining)}")
            else:
                self.time_label.setText("已完成")

        # 更新速度
        if self.config.show_speed and value > 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            speed = value / elapsed if elapsed > 0 else 0
            self.speed_label.setText(f"速度: {speed:.1f}%/秒")

    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}分{secs}秒"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}小时{minutes}分钟"


class StatusIndicator(QLabel):
    """状态指示器"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_status = ""
        self.status_history: List[Tuple[str, datetime]] = []

        self.setup_ui()
        self.setup_animations()

    def setup_ui(self):
        """设置UI"""
        self.setFixedHeight(24)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setFont(QFont("Microsoft YaHei UI", 9))

        # 默认样式
        self.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                padding: 4px 12px;
                color: #666;
            }
        """)

        self.setText("就绪")

    def setup_animations(self):
        """设置动画"""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)

        # 闪烁动画
        self.blink_animation = QPropertyAnimation(self, b"windowOpacity")
        self.blink_animation.setDuration(500)
        self.blink_animation.setLoopCount(3)

    def set_status(self, status: str, status_type: FeedbackType = FeedbackType.INFO):
        """设置状态"""
        self.current_status = status
        self.status_history.append((status, datetime.now()))

        # 限制历史记录数量
        if len(self.status_history) > 50:
            self.status_history = self.status_history[-50:]

        # 更新显示
        self.setText(status)

        # 应用颜色
        colors = {
            FeedbackType.SUCCESS: "#4CAF50",
            FeedbackType.ERROR: "#F44336",
            FeedbackType.WARNING: "#FF9800",
            FeedbackType.INFO: "#2196F3",
            FeedbackType.LOADING: "#9C27B0"
        }

        color = colors.get(status_type, "#666")

        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color}20;
                border: 1px solid {color};
                border-radius: 12px;
                padding: 4px 12px;
                color: {color};
                font-weight: bold;
            }}
        """)

        # 播放动画
        if status_type in [FeedbackType.ERROR, FeedbackType.WARNING]:
            self._play_blink_animation()

    def _play_blink_animation(self):
        """播放闪烁动画"""
        self.blink_animation.setStartValue(1.0)
        self.blink_animation.setEndValue(0.3)
        self.blink_animation.start()

    def get_status_history(self) -> List[Tuple[str, datetime]]:
        """获取状态历史"""
        return self.status_history.copy()


class LoadingSpinner(QLabel):
    """加载旋转器"""

    def __init__(self, size: int = 32, parent=None):
        super().__init__(parent)

        self.size = size
        self.angle = 0

        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)

        # 创建旋转动画
        self.timer = QTimer()
        self.timer.timeout.connect(self._rotate)

    def start_spinning(self):
        """开始旋转"""
        self.timer.start(50)  # 50ms间隔
        self.show()

    def stop_spinning(self):
        """停止旋转"""
        self.timer.stop()
        self.hide()

    def _rotate(self):
        """旋转"""
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制旋转的圆圈
        center = self.rect().center()
        radius = min(self.width(), self.height()) // 2 - 4

        painter.translate(center)
        painter.rotate(self.angle)

        # 绘制圆弧
        pen = QPen(QColor("#2196F3"), 3)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        painter.drawArc(-radius, -radius, radius * 2, radius * 2, 0, 270 * 16)


class InteractionFeedbackSystem(QObject):
    """交互反馈系统主类"""

    # 信号定义
    feedback_shown = pyqtSignal(str, str)  # message, type
    feedback_hidden = pyqtSignal(str)      # message

    def __init__(self, parent_widget: QWidget = None):
        super().__init__()

        self.parent_widget = parent_widget or QApplication.activeWindow()
        self.active_notifications: List[ToastNotification] = []
        self.notification_positions: Dict[str, QPoint] = {}
        self.status_indicators: Dict[str, StatusIndicator] = {}
        self.progress_indicators: Dict[str, ProgressIndicator] = {}
        self.loading_spinners: Dict[str, LoadingSpinner] = {}

        # 配置
        self.max_notifications = 5
        self.notification_spacing = 10
        self.default_config = FeedbackConfig(FeedbackType.INFO)

        # 系统托盘支持
        self.setup_system_tray()

        logger.info("交互反馈系统已初始化")

    def setup_system_tray(self):
        """设置系统托盘"""
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon = QSystemTrayIcon()
                self.tray_icon.setIcon(QIcon("🔔"))  # 简化图标

                # 创建托盘菜单
                tray_menu = QMenu()
                show_action = QAction("显示主窗口", self)
                quit_action = QAction("退出", self)

                tray_menu.addAction(show_action)
                tray_menu.addSeparator()
                tray_menu.addAction(quit_action)

                self.tray_icon.setContextMenu(tray_menu)

        except Exception as e:
            logger.error(f"设置系统托盘失败: {e}")
            self.tray_icon = None

    def show_notification(self, message: str, feedback_type: FeedbackType = FeedbackType.INFO,
                          config: Optional[FeedbackConfig] = None) -> ToastNotification:
        """显示通知"""
        try:
            # 使用提供的配置或默认配置
            notification_config = config or FeedbackConfig(feedback_type)

            # 创建通知
            notification = ToastNotification(message, notification_config, self.parent_widget)

            # 连接信号
            notification.closed.connect(lambda: self._on_notification_closed(notification))

            # 计算位置
            position = self._calculate_notification_position(notification_config.position)
            notification.move(position)

            # 显示通知
            notification.show_notification()

            # 添加到活跃列表
            self.active_notifications.append(notification)

            # 限制通知数量
            self._limit_notifications()

            # 发送信号
            self.feedback_shown.emit(message, feedback_type.value)

            # 系统托盘通知
            if self.tray_icon and notification_config.level == FeedbackLevel.CRITICAL:
                self.tray_icon.showMessage("系统通知", message, QSystemTrayIcon.Critical, 5000)

            logger.debug(f"通知已显示: {message}")
            return notification

        except Exception as e:
            logger.error(f"显示通知失败: {e}")
            return None

    def show_success(self, message: str, duration: int = 3000) -> ToastNotification:
        """显示成功通知"""
        config = FeedbackConfig(
            feedback_type=FeedbackType.SUCCESS,
            duration=duration,
            level=FeedbackLevel.NORMAL
        )
        return self.show_notification(message, FeedbackType.SUCCESS, config)

    def show_error(self, message: str, duration: int = 5000) -> ToastNotification:
        """显示错误通知"""
        config = FeedbackConfig(
            feedback_type=FeedbackType.ERROR,
            duration=duration,
            level=FeedbackLevel.CRITICAL,
            show_close_button=True
        )
        return self.show_notification(message, FeedbackType.ERROR, config)

    def show_warning(self, message: str, duration: int = 4000) -> ToastNotification:
        """显示警告通知"""
        config = FeedbackConfig(
            feedback_type=FeedbackType.WARNING,
            duration=duration,
            level=FeedbackLevel.PROMINENT
        )
        return self.show_notification(message, FeedbackType.WARNING, config)

    def show_info(self, message: str, duration: int = 3000) -> ToastNotification:
        """显示信息通知"""
        config = FeedbackConfig(
            feedback_type=FeedbackType.INFO,
            duration=duration
        )
        return self.show_notification(message, FeedbackType.INFO, config)

    def create_progress_indicator(self, indicator_id: str, config: Optional[ProgressConfig] = None) -> ProgressIndicator:
        """创建进度指示器"""
        try:
            progress_config = config or ProgressConfig()
            indicator = ProgressIndicator(progress_config, self.parent_widget)

            self.progress_indicators[indicator_id] = indicator

            logger.debug(f"进度指示器已创建: {indicator_id}")
            return indicator

        except Exception as e:
            logger.error(f"创建进度指示器失败: {e}")
            return None

    def update_progress(self, indicator_id: str, value: int, message: str = ""):
        """更新进度"""
        try:
            if indicator_id in self.progress_indicators:
                self.progress_indicators[indicator_id].update_progress(value, message)

        except Exception as e:
            logger.error(f"更新进度失败: {e}")

    def remove_progress_indicator(self, indicator_id: str):
        """移除进度指示器"""
        try:
            if indicator_id in self.progress_indicators:
                indicator = self.progress_indicators[indicator_id]
                indicator.deleteLater()
                del self.progress_indicators[indicator_id]

        except Exception as e:
            logger.error(f"移除进度指示器失败: {e}")

    def create_status_indicator(self, indicator_id: str) -> StatusIndicator:
        """创建状态指示器"""
        try:
            indicator = StatusIndicator(self.parent_widget)
            self.status_indicators[indicator_id] = indicator

            logger.debug(f"状态指示器已创建: {indicator_id}")
            return indicator

        except Exception as e:
            logger.error(f"创建状态指示器失败: {e}")
            return None

    def update_status(self, indicator_id: str, status: str, status_type: FeedbackType = FeedbackType.INFO):
        """更新状态"""
        try:
            if indicator_id in self.status_indicators:
                self.status_indicators[indicator_id].set_status(status, status_type)

        except Exception as e:
            logger.error(f"更新状态失败: {e}")

    def create_loading_spinner(self, spinner_id: str, size: int = 32) -> LoadingSpinner:
        """创建加载旋转器"""
        try:
            spinner = LoadingSpinner(size, self.parent_widget)
            self.loading_spinners[spinner_id] = spinner

            logger.debug(f"加载旋转器已创建: {spinner_id}")
            return spinner

        except Exception as e:
            logger.error(f"创建加载旋转器失败: {e}")
            return None

    def start_loading(self, spinner_id: str):
        """开始加载动画"""
        try:
            if spinner_id in self.loading_spinners:
                self.loading_spinners[spinner_id].start_spinning()

        except Exception as e:
            logger.error(f"启动加载动画失败: {e}")

    def stop_loading(self, spinner_id: str):
        """停止加载动画"""
        try:
            if spinner_id in self.loading_spinners:
                self.loading_spinners[spinner_id].stop_spinning()

        except Exception as e:
            logger.error(f"停止加载动画失败: {e}")

    def _calculate_notification_position(self, position: str) -> QPoint:
        """计算通知位置"""
        try:
            if not self.parent_widget:
                return QPoint(100, 100)

            parent_rect = self.parent_widget.geometry()
            notification_width = 300
            notification_height = 60

            # 计算已有通知的偏移
            offset_y = len(self.active_notifications) * (notification_height + self.notification_spacing)

            if position == "top_right":
                x = parent_rect.right() - notification_width - 20
                y = parent_rect.top() + 20 + offset_y
            elif position == "top_left":
                x = parent_rect.left() + 20
                y = parent_rect.top() + 20 + offset_y
            elif position == "bottom_right":
                x = parent_rect.right() - notification_width - 20
                y = parent_rect.bottom() - notification_height - 20 - offset_y
            elif position == "bottom_left":
                x = parent_rect.left() + 20
                y = parent_rect.bottom() - notification_height - 20 - offset_y
            else:  # center
                x = parent_rect.center().x() - notification_width // 2
                y = parent_rect.center().y() - notification_height // 2

            return QPoint(x, y)

        except Exception as e:
            logger.error(f"计算通知位置失败: {e}")
            return QPoint(100, 100)

    def _limit_notifications(self):
        """限制通知数量"""
        try:
            while len(self.active_notifications) > self.max_notifications:
                oldest_notification = self.active_notifications[0]
                oldest_notification.close_notification()

        except Exception as e:
            logger.error(f"限制通知数量失败: {e}")

    def _on_notification_closed(self, notification: ToastNotification):
        """通知关闭处理"""
        try:
            if notification in self.active_notifications:
                self.active_notifications.remove(notification)

            self.feedback_hidden.emit(notification.message)

        except Exception as e:
            logger.error(f"处理通知关闭失败: {e}")

    def clear_all_notifications(self):
        """清除所有通知"""
        try:
            for notification in self.active_notifications.copy():
                notification.close_notification()

        except Exception as e:
            logger.error(f"清除所有通知失败: {e}")

    def get_feedback_statistics(self) -> Dict[str, Any]:
        """获取反馈统计"""
        try:
            return {
                'active_notifications': len(self.active_notifications),
                'status_indicators': len(self.status_indicators),
                'progress_indicators': len(self.progress_indicators),
                'loading_spinners': len(self.loading_spinners),
                'system_tray_available': self.tray_icon is not None,
                'max_notifications': self.max_notifications
            }

        except Exception as e:
            logger.error(f"获取反馈统计失败: {e}")
            return {'error': str(e)}


# 全局实例
interaction_feedback_system = None


def get_interaction_feedback_system(parent_widget: QWidget = None) -> InteractionFeedbackSystem:
    """获取交互反馈系统实例"""
    global interaction_feedback_system

    if interaction_feedback_system is None:
        interaction_feedback_system = InteractionFeedbackSystem(parent_widget)

    return interaction_feedback_system


def show_success_notification(message: str, duration: int = 3000):
    """显示成功通知的便捷函数"""
    system = get_interaction_feedback_system()
    return system.show_success(message, duration)


def show_error_notification(message: str, duration: int = 5000):
    """显示错误通知的便捷函数"""
    system = get_interaction_feedback_system()
    return system.show_error(message, duration)


def show_info_notification(message: str, duration: int = 3000):
    """显示信息通知的便捷函数"""
    system = get_interaction_feedback_system()
    return system.show_info(message, duration)
