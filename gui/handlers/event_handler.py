"""
事件处理器模块

统一处理系统中的各种事件，包括用户交互、数据更新、系统通知等
"""

from typing import Optional, Dict, Any, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMessageBox, QApplication
from core.logger import LogManager
import traceback
from datetime import datetime


class EventHandler(QObject):
    """统一事件处理器"""

    # 定义信号
    event_processed = pyqtSignal(str, dict)  # 事件处理完成信号
    error_occurred = pyqtSignal(str, str)  # 错误发生信号 (event_type, error_msg)
    notification_sent = pyqtSignal(str, str)  # 通知发送信号 (title, message)

    def __init__(self, parent=None, log_manager: Optional[LogManager] = None):
        super().__init__(parent)
        self.log_manager = log_manager or LogManager()

        # 事件处理器注册表
        self.event_handlers: Dict[str, Callable] = {}

        # 事件队列和处理状态
        self.event_queue = []
        self.processing_events = False

        # 错误处理配置
        self.error_handlers: Dict[str, Callable] = {}
        self.max_retry_count = 3
        self.retry_delays = [1000, 2000, 5000]  # 毫秒

        # 初始化定时器
        self.init_timers()

        # 注册默认事件处理器
        self.register_default_handlers()

    def init_timers(self):
        """初始化定时器"""
        try:
            # 事件队列处理定时器
            self.queue_timer = QTimer()
            self.queue_timer.timeout.connect(self.process_event_queue)
            self.queue_timer.start(100)  # 每100ms处理一次队列

            # 系统监控定时器
            self.monitor_timer = QTimer()
            self.monitor_timer.timeout.connect(self.monitor_system_events)
            self.monitor_timer.start(5000)  # 每5秒监控一次

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化定时器失败: {str(e)}")

    def register_default_handlers(self):
        """注册默认事件处理器"""
        try:
            # 用户交互事件
            self.register_handler('user_click', self.handle_user_click)
            self.register_handler('user_input', self.handle_user_input)
            self.register_handler('user_selection', self.handle_user_selection)

            # 数据事件
            self.register_handler('data_loaded', self.handle_data_loaded)
            self.register_handler('data_updated', self.handle_data_updated)
            self.register_handler('data_error', self.handle_data_error)

            # 分析事件
            self.register_handler('analysis_started', self.handle_analysis_started)
            self.register_handler('analysis_completed', self.handle_analysis_completed)
            self.register_handler('analysis_error', self.handle_analysis_error)

            # 系统事件
            self.register_handler('system_startup', self.handle_system_startup)
            self.register_handler('system_shutdown', self.handle_system_shutdown)
            self.register_handler('system_error', self.handle_system_error)

            # 通知事件
            self.register_handler('notification', self.handle_notification)
            self.register_handler('alert', self.handle_alert)
            self.register_handler('warning', self.handle_warning)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"注册默认事件处理器失败: {str(e)}")

    def register_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        try:
            self.event_handlers[event_type] = handler
            if self.log_manager:
                self.log_manager.debug(f"注册事件处理器: {event_type}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"注册事件处理器失败: {str(e)}")

    def unregister_handler(self, event_type: str):
        """注销事件处理器"""
        try:
            if event_type in self.event_handlers:
                del self.event_handlers[event_type]
                if self.log_manager:
                    self.log_manager.debug(f"注销事件处理器: {event_type}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"注销事件处理器失败: {str(e)}")

    def register_error_handler(self, error_type: str, handler: Callable):
        """注册错误处理器"""
        try:
            self.error_handlers[error_type] = handler
            if self.log_manager:
                self.log_manager.debug(f"注册错误处理器: {error_type}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"注册错误处理器失败: {str(e)}")

    def emit_event(self, event_type: str, event_data: Dict[str, Any] = None, priority: int = 0):
        """发送事件"""
        try:
            if event_data is None:
                event_data = {}

            # 添加事件元数据
            event_data.update({
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'priority': priority
            })

            # 添加到事件队列
            self.event_queue.append({
                'type': event_type,
                'data': event_data,
                'priority': priority,
                'retry_count': 0
            })

            # 按优先级排序队列
            self.event_queue.sort(key=lambda x: x['priority'], reverse=True)

            if self.log_manager:
                self.log_manager.debug(f"发送事件: {event_type}, 数据: {event_data}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"发送事件失败: {str(e)}")

    def process_event_queue(self):
        """处理事件队列"""
        try:
            if self.processing_events or not self.event_queue:
                return

            self.processing_events = True

            # 处理队列中的第一个事件
            event = self.event_queue.pop(0)
            self.process_single_event(event)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"处理事件队列失败: {str(e)}")
        finally:
            self.processing_events = False

    def process_single_event(self, event: Dict[str, Any]):
        """处理单个事件"""
        try:
            event_type = event['type']
            event_data = event['data']
            retry_count = event['retry_count']

            # 检查是否有对应的处理器
            if event_type not in self.event_handlers:
                if self.log_manager:
                    self.log_manager.warning(f"未找到事件处理器: {event_type}")
                return

            # 执行事件处理器
            handler = self.event_handlers[event_type]
            result = handler(event_data)

            # 发送处理完成信号
            self.event_processed.emit(event_type, event_data)

            if self.log_manager:
                self.log_manager.debug(f"事件处理完成: {event_type}")

        except Exception as e:
            # 处理错误
            self.handle_event_error(event, str(e))

    def handle_event_error(self, event: Dict[str, Any], error_msg: str):
        """处理事件错误"""
        try:
            event_type = event['type']
            retry_count = event['retry_count']

            if self.log_manager:
                self.log_manager.error(f"事件处理错误: {event_type}, 错误: {error_msg}")

            # 检查是否需要重试
            if retry_count < self.max_retry_count:
                # 增加重试次数
                event['retry_count'] += 1

                # 延迟重试
                delay = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)]
                QTimer.singleShot(delay, lambda: self.retry_event(event) if hasattr(self, 'retry_event') and callable(self.retry_event) else None)

                if self.log_manager:
                    self.log_manager.info(f"事件将在{delay}ms后重试: {event_type}")
            else:
                # 超过最大重试次数，发送错误信号
                self.error_occurred.emit(event_type, error_msg)

                # 调用错误处理器
                if event_type in self.error_handlers:
                    try:
                        self.error_handlers[event_type](event, error_msg)
                    except Exception as handler_error:
                        if self.log_manager:
                            self.log_manager.error(f"错误处理器执行失败: {str(handler_error)}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"处理事件错误失败: {str(e)}")

    def retry_event(self, event: Dict[str, Any]):
        """重试事件"""
        try:
            # 重新添加到队列
            self.event_queue.insert(0, event)

            if self.log_manager:
                self.log_manager.debug(f"重试事件: {event['type']}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"重试事件失败: {str(e)}")

    def monitor_system_events(self):
        """监控系统事件"""
        try:
            # 检查应用程序状态
            app = QApplication.instance()
            if app:
                # 检查内存使用
                import psutil
                process = psutil.Process()
                memory_percent = process.memory_percent()

                if memory_percent > 80:
                    self.emit_event('system_warning', {
                        'type': 'high_memory_usage',
                        'memory_percent': memory_percent
                    })

                # 检查事件队列长度
                if len(self.event_queue) > 100:
                    self.emit_event('system_warning', {
                        'type': 'event_queue_overflow',
                        'queue_length': len(self.event_queue)
                    })

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"监控系统事件失败: {str(e)}")

    # 默认事件处理器实现
    def handle_user_click(self, event_data: Dict[str, Any]):
        """处理用户点击事件"""
        try:
            widget_name = event_data.get('widget_name', 'unknown')
            position = event_data.get('position', (0, 0))

            if self.log_manager:
                self.log_manager.debug(f"用户点击: {widget_name} at {position}")

        except Exception as e:
            raise Exception(f"处理用户点击事件失败: {str(e)}")

    def handle_user_input(self, event_data: Dict[str, Any]):
        """处理用户输入事件"""
        try:
            input_type = event_data.get('input_type', 'text')
            value = event_data.get('value', '')

            if self.log_manager:
                self.log_manager.debug(f"用户输入: {input_type} = {value}")

        except Exception as e:
            raise Exception(f"处理用户输入事件失败: {str(e)}")

    def handle_user_selection(self, event_data: Dict[str, Any]):
        """处理用户选择事件"""
        try:
            selection_type = event_data.get('selection_type', 'item')
            selected_items = event_data.get('selected_items', [])

            if self.log_manager:
                self.log_manager.debug(f"用户选择: {selection_type}, 项目数: {len(selected_items)}")

        except Exception as e:
            raise Exception(f"处理用户选择事件失败: {str(e)}")

    def handle_data_loaded(self, event_data: Dict[str, Any]):
        """处理数据加载事件"""
        try:
            data_type = event_data.get('data_type', 'unknown')
            record_count = event_data.get('record_count', 0)

            if self.log_manager:
                self.log_manager.info(f"数据加载完成: {data_type}, 记录数: {record_count}")

        except Exception as e:
            raise Exception(f"处理数据加载事件失败: {str(e)}")

    def handle_data_updated(self, event_data: Dict[str, Any]):
        """处理数据更新事件"""
        try:
            data_type = event_data.get('data_type', 'unknown')
            update_count = event_data.get('update_count', 0)

            if self.log_manager:
                self.log_manager.info(f"数据更新完成: {data_type}, 更新数: {update_count}")

        except Exception as e:
            raise Exception(f"处理数据更新事件失败: {str(e)}")

    def handle_data_error(self, event_data: Dict[str, Any]):
        """处理数据错误事件"""
        try:
            error_type = event_data.get('error_type', 'unknown')
            error_message = event_data.get('error_message', '')

            if self.log_manager:
                self.log_manager.error(f"数据错误: {error_type}, 消息: {error_message}")

        except Exception as e:
            raise Exception(f"处理数据错误事件失败: {str(e)}")

    def handle_analysis_started(self, event_data: Dict[str, Any]):
        """处理分析开始事件"""
        try:
            analysis_type = event_data.get('analysis_type', 'unknown')
            parameters = event_data.get('parameters', {})

            if self.log_manager:
                self.log_manager.info(f"分析开始: {analysis_type}, 参数: {parameters}")

        except Exception as e:
            raise Exception(f"处理分析开始事件失败: {str(e)}")

    def handle_analysis_completed(self, event_data: Dict[str, Any]):
        """处理分析完成事件"""
        try:
            analysis_type = event_data.get('analysis_type', 'unknown')
            results = event_data.get('results', {})
            duration = event_data.get('duration', 0)

            if self.log_manager:
                self.log_manager.info(f"分析完成: {analysis_type}, 耗时: {duration}秒")

        except Exception as e:
            raise Exception(f"处理分析完成事件失败: {str(e)}")

    def handle_analysis_error(self, event_data: Dict[str, Any]):
        """处理分析错误事件"""
        try:
            analysis_type = event_data.get('analysis_type', 'unknown')
            error_message = event_data.get('error_message', '')

            if self.log_manager:
                self.log_manager.error(f"分析错误: {analysis_type}, 消息: {error_message}")

        except Exception as e:
            raise Exception(f"处理分析错误事件失败: {str(e)}")

    def handle_system_startup(self, event_data: Dict[str, Any]):
        """处理系统启动事件"""
        try:
            startup_time = event_data.get('startup_time', 0)

            if self.log_manager:
                self.log_manager.info(f"系统启动完成, 耗时: {startup_time}秒")

        except Exception as e:
            raise Exception(f"处理系统启动事件失败: {str(e)}")

    def handle_system_shutdown(self, event_data: Dict[str, Any]):
        """处理系统关闭事件"""
        try:
            if self.log_manager:
                self.log_manager.info("系统正在关闭")

        except Exception as e:
            raise Exception(f"处理系统关闭事件失败: {str(e)}")

    def handle_system_error(self, event_data: Dict[str, Any]):
        """处理系统错误事件"""
        try:
            error_type = event_data.get('error_type', 'unknown')
            error_message = event_data.get('error_message', '')

            if self.log_manager:
                self.log_manager.critical(f"系统错误: {error_type}, 消息: {error_message}")

        except Exception as e:
            raise Exception(f"处理系统错误事件失败: {str(e)}")

    def handle_notification(self, event_data: Dict[str, Any]):
        """处理通知事件"""
        try:
            title = event_data.get('title', '通知')
            message = event_data.get('message', '')
            notification_type = event_data.get('type', 'info')

            # 发送通知信号
            self.notification_sent.emit(title, message)

            if self.log_manager:
                self.log_manager.info(f"发送通知: {title} - {message}")

        except Exception as e:
            raise Exception(f"处理通知事件失败: {str(e)}")

    def handle_alert(self, event_data: Dict[str, Any]):
        """处理警报事件"""
        try:
            title = event_data.get('title', '警报')
            message = event_data.get('message', '')

            # 显示警报对话框
            QMessageBox.warning(None, title, message)

            if self.log_manager:
                self.log_manager.warning(f"警报: {title} - {message}")

        except Exception as e:
            raise Exception(f"处理警报事件失败: {str(e)}")

    def handle_warning(self, event_data: Dict[str, Any]):
        """处理警告事件"""
        try:
            message = event_data.get('message', '')

            if self.log_manager:
                self.log_manager.warning(f"警告: {message}")

        except Exception as e:
            raise Exception(f"处理警告事件失败: {str(e)}")

    def get_event_queue_status(self) -> Dict[str, Any]:
        """获取事件队列状态"""
        try:
            return {
                'queue_length': len(self.event_queue),
                'processing': self.processing_events,
                'registered_handlers': len(self.event_handlers),
                'error_handlers': len(self.error_handlers)
            }
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取事件队列状态失败: {str(e)}")
            return {}

    def clear_event_queue(self):
        """清空事件队列"""
        try:
            self.event_queue.clear()
            if self.log_manager:
                self.log_manager.info("事件队列已清空")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清空事件队列失败: {str(e)}")

    def shutdown(self):
        """关闭事件处理器"""
        try:
            # 停止定时器
            if hasattr(self, 'queue_timer'):
                self.queue_timer.stop()
            if hasattr(self, 'monitor_timer'):
                self.monitor_timer.stop()

            # 清空队列
            self.clear_event_queue()

            if self.log_manager:
                self.log_manager.info("事件处理器已关闭")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"关闭事件处理器失败: {str(e)}")
