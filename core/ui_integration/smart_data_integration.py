#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能数据集成接口
提供UI与数据管理系统的智能集成功能
"""

from typing import Dict, List, Optional, Callable, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

try:
    from PyQt5.QtCore import QObject, pyqtSignal, QTimer
    from PyQt5.QtWidgets import QWidget, QApplication
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda *args: None

try:
    from core.plugin_types import AssetType, DataType
    from core.ui_integration.data_missing_manager import DataMissingManager, DataAvailabilityInfo, get_data_missing_manager
    from gui.widgets.data_missing_handler import DataMissingPromptWidget, DataDownloadDialog
    from loguru import logger
except ImportError as e:
    print(f"导入组件失败: {e}")
    logger = None


class IntegrationMode(Enum):
    """集成模式"""
    PASSIVE = "passive"  # 被动模式，仅在请求时检查
    ACTIVE = "active"  # 主动模式，实时监控
    SMART = "smart"  # 智能模式，根据使用模式自适应


@dataclass
class UIIntegrationConfig:
    """UI集成配置"""
    mode: IntegrationMode = IntegrationMode.SMART
    auto_check_interval: int = 300  # 自动检查间隔（秒）
    show_missing_prompt: bool = True  # 显示缺失提示
    auto_suggest_download: bool = True  # 自动建议下载
    max_concurrent_downloads: int = 3  # 最大并发下载数
    cache_duration: int = 300  # 缓存持续时间（秒）
    enable_notifications: bool = True  # 启用通知


class SmartDataIntegration(QObject if PYQT5_AVAILABLE else object):
    """智能数据集成管理器"""

    # 信号定义
    if PYQT5_AVAILABLE:
        data_missing_detected = pyqtSignal(str, str, str, str)  # symbol, asset_type, data_type, error_msg
        download_progress_updated = pyqtSignal(str, float, str)  # task_id, progress, message
        download_completed = pyqtSignal(str, bool, str)  # task_id, success, message
        plugin_status_changed = pyqtSignal(str, bool)  # plugin_name, is_available

    def __init__(self, config: Optional[UIIntegrationConfig] = None):
        if PYQT5_AVAILABLE:
            super().__init__()

        self.config = config or UIIntegrationConfig()
        self.data_missing_manager = get_data_missing_manager()

        # UI组件
        self.missing_prompt_widgets: Dict[str, 'DataMissingPromptWidget'] = {}
        self.active_download_dialogs: Dict[str, 'DataDownloadDialog'] = {}

        # 状态跟踪
        self.monitored_widgets: List[QWidget] = []
        self.last_check_times: Dict[str, datetime] = {}
        self.pending_checks: Dict[str, Any] = {}

        # 定时器
        if PYQT5_AVAILABLE:
            self.check_timer = QTimer()
            self.check_timer.timeout.connect(self._periodic_check)

            if self.config.mode in [IntegrationMode.ACTIVE, IntegrationMode.SMART]:
                self.check_timer.start(self.config.auto_check_interval * 1000)

        # 注册回调
        self.data_missing_manager.register_data_missing_callback(self._on_data_missing_detected)
        self.data_missing_manager.register_download_progress_callback(self._on_download_progress)

        if logger:
            logger.info(f"智能数据集成管理器初始化完成，模式: {self.config.mode.value}")

    def register_widget(self, widget: QWidget, widget_id: str = ""):
        """注册需要监控的UI组件"""
        if not PYQT5_AVAILABLE:
            return

        try:
            if widget not in self.monitored_widgets:
                self.monitored_widgets.append(widget)

                # 创建专用的缺失提示组件
                if widget_id:
                    prompt_widget = DataMissingPromptWidget(widget)
                    prompt_widget.download_requested.connect(self._on_download_requested)
                    prompt_widget.plugin_config_requested.connect(self._on_plugin_config_requested)
                    prompt_widget.data_management_requested.connect(self._on_data_management_requested)

                    self.missing_prompt_widgets[widget_id] = prompt_widget

                if logger:
                    logger.info(f"注册UI组件监控: {widget_id or str(widget)}")

        except Exception as e:
            if logger:
                logger.error(f"注册UI组件失败: {e}")

    def unregister_widget(self, widget: QWidget, widget_id: str = ""):
        """取消注册UI组件"""
        try:
            if widget in self.monitored_widgets:
                self.monitored_widgets.remove(widget)

            if widget_id in self.missing_prompt_widgets:
                self.missing_prompt_widgets[widget_id].close()
                del self.missing_prompt_widgets[widget_id]

            if logger:
                logger.info(f"取消注册UI组件: {widget_id or str(widget)}")

        except Exception as e:
            if logger:
                logger.error(f"取消注册UI组件失败: {e}")

    def check_data_for_widget(self, widget_id: str, symbol: str, data_type: str,
                              date_range: Optional[tuple] = None) -> bool:
        """为特定组件检查数据可用性"""
        try:
            # 转换数据类型
            dt = DataType.HISTORICAL_KLINE if data_type.lower() in ['historical', 'kline'] else DataType.REAL_TIME_QUOTE

            # 转换日期范围
            parsed_date_range = None
            if date_range:
                if isinstance(date_range[0], str):
                    start_date = datetime.strptime(date_range[0], '%Y-%m-%d')
                    end_date = datetime.strptime(date_range[1], '%Y-%m-%d')
                    parsed_date_range = (start_date, end_date)
                else:
                    parsed_date_range = date_range

            # 检查数据可用性
            availability_info = self.data_missing_manager.check_data_availability(
                symbol, dt, parsed_date_range
            )

            # 更新检查时间
            check_key = f"{widget_id}_{symbol}_{data_type}"
            self.last_check_times[check_key] = datetime.now()

            # 如果数据缺失且配置允许显示提示
            if (availability_info.status.value in ['missing', 'partial'] and
                self.config.show_missing_prompt and
                    widget_id in self.missing_prompt_widgets):

                prompt_widget = self.missing_prompt_widgets[widget_id]
                prompt_widget.show_data_missing(
                    symbol,
                    data_type,
                    availability_info.error_message
                )

            return availability_info.status.value == 'available'

        except Exception as e:
            if logger:
                logger.error(f"检查数据可用性失败: {e}")
            return False

    def suggest_data_download(self, symbol: str, data_type: str,
                              parent_widget: Optional[QWidget] = None) -> Optional[str]:
        """建议数据下载"""
        try:
            if not PYQT5_AVAILABLE:
                return None

            # 识别资产类型
            from core.asset_type_identifier import AssetTypeIdentifier
            identifier = AssetTypeIdentifier()
            asset_type = identifier.identify_asset_type(symbol)

            # 转换数据类型
            dt = DataType.HISTORICAL_KLINE if data_type.lower() in ['historical', 'kline'] else DataType.REAL_TIME_QUOTE

            # 创建下载对话框
            dialog = DataDownloadDialog(symbol, asset_type.value, dt.value, parent_widget)
            dialog.download_started.connect(self._on_download_dialog_confirmed)

            # 显示对话框
            if dialog.exec_() == dialog.Accepted:
                return "download_requested"

            return None

        except Exception as e:
            if logger:
                logger.error(f"建议数据下载失败: {e}")
            return None

    def start_data_download(self, symbol: str, asset_type: str, data_type: str,
                            options: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """开始数据下载"""
        try:
            # 转换类型
            at = AssetType(asset_type) if isinstance(asset_type, str) else asset_type
            dt = DataType(data_type) if isinstance(data_type, str) else data_type

            # 解析选项
            options = options or {}
            start_date = datetime.strptime(options.get('start_date', '2023-01-01'), '%Y-%m-%d')
            end_date = datetime.strptime(options.get('end_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')
            plugin_name = options.get('data_source', '')

            # 创建下载任务
            task_id = self.data_missing_manager.create_download_task(
                symbol, at, dt, (start_date, end_date), plugin_name
            )

            if logger:
                logger.info(f"开始数据下载任务: {task_id}")

            return task_id

        except Exception as e:
            if logger:
                logger.error(f"开始数据下载失败: {e}")
            return None

    def get_download_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取下载进度"""
        try:
            task = self.data_missing_manager.get_download_task(task_id)
            if task:
                return {
                    'task_id': task.task_id,
                    'symbol': task.symbol,
                    'status': task.status,
                    'progress': task.progress,
                    'error_message': task.error_message,
                    'created_at': task.created_at.isoformat(),
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                }
            return None
        except Exception as e:
            if logger:
                logger.error(f"获取下载进度失败: {e}")
            return None

    def cancel_download(self, task_id: str) -> bool:
        """取消下载"""
        try:
            return self.data_missing_manager.cancel_download_task(task_id)
        except Exception as e:
            if logger:
                logger.error(f"取消下载失败: {e}")
            return False

    def get_plugin_suggestions(self, symbol: str, data_type: str) -> List[Dict[str, Any]]:
        """获取插件建议"""
        try:
            dt = DataType.HISTORICAL_KLINE if data_type.lower() in ['historical', 'kline'] else DataType.REAL_TIME_QUOTE
            return self.data_missing_manager.suggest_data_sources(symbol, dt)
        except Exception as e:
            if logger:
                logger.error(f"获取插件建议失败: {e}")
            return []

    def _periodic_check(self):
        """定期检查"""
        try:
            if self.config.mode == IntegrationMode.PASSIVE:
                return

            # 清理过期的检查记录
            current_time = datetime.now()
            expired_keys = []

            for key, check_time in self.last_check_times.items():
                if (current_time - check_time).seconds > self.config.cache_duration:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.last_check_times[key]

            # 清理已完成的任务
            self.data_missing_manager.cleanup_completed_tasks()

        except Exception as e:
            if logger:
                logger.error(f"定期检查失败: {e}")

    def _on_data_missing_detected(self, availability_info: DataAvailabilityInfo):
        """数据缺失检测回调"""
        try:
            if PYQT5_AVAILABLE:
                self.data_missing_detected.emit(
                    availability_info.symbol,
                    availability_info.asset_type.value,
                    availability_info.data_type.value,
                    availability_info.error_message
                )
        except Exception as e:
            if logger:
                logger.error(f"数据缺失检测回调失败: {e}")

    def _on_download_progress(self, task_id: str, progress: float, message: str):
        """下载进度回调"""
        try:
            if PYQT5_AVAILABLE:
                self.download_progress_updated.emit(task_id, progress, message)

                # 如果下载完成
                if progress >= 1.0:
                    task = self.data_missing_manager.get_download_task(task_id)
                    if task:
                        success = task.status == "completed"
                        self.download_completed.emit(task_id, success, message)

        except Exception as e:
            if logger:
                logger.error(f"下载进度回调失败: {e}")

    def _on_download_requested(self, symbol: str, asset_type: str, data_type: str):
        """下载请求回调"""
        try:
            # 显示下载对话框
            self.suggest_data_download(symbol, data_type)
        except Exception as e:
            if logger:
                logger.error(f"处理下载请求失败: {e}")

    def _on_plugin_config_requested(self, plugin_name: str):
        """插件配置请求回调"""
        try:
            if logger:
                logger.info(f"请求配置插件: {plugin_name}")
            # 这里应该打开插件配置对话框
            # 由于需要访问主应用的插件管理器，这里只记录日志
        except Exception as e:
            if logger:
                logger.error(f"处理插件配置请求失败: {e}")

    def _on_data_management_requested(self):
        """数据管理请求回调"""
        try:
            if logger:
                logger.info("请求打开数据管理界面")
            # 这里应该打开数据管理界面
        except Exception as e:
            if logger:
                logger.error(f"处理数据管理请求失败: {e}")

    def _on_download_dialog_confirmed(self, symbol: str, asset_type: str, data_type: str, options: Dict[str, Any]):
        """下载对话框确认回调"""
        try:
            task_id = self.start_data_download(symbol, asset_type, data_type, options)
            if task_id and logger:
                logger.info(f"用户确认下载，任务ID: {task_id}")
        except Exception as e:
            if logger:
                logger.error(f"处理下载确认失败: {e}")

    def update_config(self, config: UIIntegrationConfig):
        """更新配置"""
        try:
            self.config = config

            # 更新定时器
            if PYQT5_AVAILABLE and hasattr(self, 'check_timer'):
                if self.config.mode in [IntegrationMode.ACTIVE, IntegrationMode.SMART]:
                    self.check_timer.start(self.config.auto_check_interval * 1000)
                else:
                    self.check_timer.stop()

            if logger:
                logger.info(f"更新集成配置: {config.mode.value}")

        except Exception as e:
            if logger:
                logger.error(f"更新配置失败: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            active_tasks = self.data_missing_manager.get_active_tasks()

            return {
                'monitored_widgets': len(self.monitored_widgets),
                'active_prompt_widgets': len(self.missing_prompt_widgets),
                'active_downloads': len(active_tasks),
                'total_checks': len(self.last_check_times),
                'config_mode': self.config.mode.value,
                'last_update': datetime.now().isoformat()
            }
        except Exception as e:
            if logger:
                logger.error(f"获取统计信息失败: {e}")
            return {}

    def close(self):
        """关闭集成管理器"""
        try:
            # 停止定时器
            if PYQT5_AVAILABLE and hasattr(self, 'check_timer'):
                self.check_timer.stop()

            # 关闭所有提示组件
            for prompt_widget in self.missing_prompt_widgets.values():
                prompt_widget.close()
            self.missing_prompt_widgets.clear()

            # 关闭所有下载对话框
            for dialog in self.active_download_dialogs.values():
                dialog.close()
            self.active_download_dialogs.clear()

            # 清空监控列表
            self.monitored_widgets.clear()

            if logger:
                logger.info("智能数据集成管理器已关闭")

        except Exception as e:
            if logger:
                logger.error(f"关闭集成管理器失败: {e}")


# 全局实例
_smart_data_integration = None


def get_smart_data_integration(config: Optional[UIIntegrationConfig] = None) -> SmartDataIntegration:
    """获取智能数据集成管理器单例"""
    global _smart_data_integration
    if _smart_data_integration is None:
        _smart_data_integration = SmartDataIntegration(config)
    return _smart_data_integration
