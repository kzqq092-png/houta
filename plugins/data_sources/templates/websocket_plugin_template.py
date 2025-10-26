"""
WebSocket插件模板

提供基于WebSocket的实时数据源插件标准实现，包括：
- WebSocket连接池管理
- 自动重连机制
- 心跳保持
- 订阅管理
- 消息路由

适用于需要实时推送的数据源（如交易所实时行情、Level-2数据等）
"""

from typing import Dict, List, Optional, Any, Callable
from abc import abstractmethod
import asyncio
import json
import time
from datetime import datetime
from enum import Enum
import threading
from queue import Queue
from loguru import logger

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("websocket-client 库未安装，WebSocket功能不可用")

from .base_plugin_template import BasePluginTemplate
from core.plugin_types import AssetType, DataType


class WebSocketState(Enum):
    """WebSocket连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class WebSocketConnection:
    """单个WebSocket连接管理"""

    def __init__(
        self,
        url: str,
        on_message: Callable,
        on_error: Callable,
        on_close: Callable,
        on_open: Callable = None,
        heartbeat_interval: int = 30,
        heartbeat_message: str = None
    ):
        self.url = url
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.on_open = on_open
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_message = heartbeat_message

        self.ws = None
        self.state = WebSocketState.DISCONNECTED
        self.thread = None
        self.heartbeat_thread = None
        self.should_reconnect = True
        self.reconnect_delay = 1  # 初始重连延迟（秒）
        self.max_reconnect_delay = 60  # 最大重连延迟

        self.last_message_time = 0
        self.message_count = 0

    def connect(self):
        """建立WebSocket连接"""
        if self.state != WebSocketState.DISCONNECTED:
            return

        self.state = WebSocketState.CONNECTING
        self.should_reconnect = True

        def run():
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_message=self._on_message_wrapper,
                    on_error=self._on_error_wrapper,
                    on_close=self._on_close_wrapper,
                    on_open=self._on_open_wrapper
                )

                self.ws.run_forever()

            except Exception as e:
                logger.error(f"WebSocket连接异常: {e}")
                self.state = WebSocketState.FAILED

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def _on_open_wrapper(self, ws):
        """连接建立回调"""
        self.state = WebSocketState.CONNECTED
        self.reconnect_delay = 1  # 重置重连延迟
        logger.info(f"WebSocket已连接: {self.url}")

        # 启动心跳
        if self.heartbeat_interval and self.heartbeat_message:
            self._start_heartbeat()

        # 调用用户回调
        if self.on_open:
            self.on_open(ws)

    def _on_message_wrapper(self, ws, message):
        """消息接收回调"""
        self.last_message_time = time.time()
        self.message_count += 1

        # 调用用户回调
        self.on_message(ws, message)

    def _on_error_wrapper(self, ws, error):
        """错误回调"""
        logger.error(f"WebSocket错误: {error}")
        self.state = WebSocketState.FAILED

        # 调用用户回调
        self.on_error(ws, error)

    def _on_close_wrapper(self, ws, close_status_code, close_msg):
        """连接关闭回调"""
        logger.warning(f"WebSocket已关闭: {close_status_code} - {close_msg}")
        self.state = WebSocketState.DISCONNECTED

        # 停止心跳
        self._stop_heartbeat()

        # 调用用户回调
        self.on_close(ws, close_status_code, close_msg)

        # 自动重连
        if self.should_reconnect:
            self._reconnect()

    def _reconnect(self):
        """重新连接"""
        if not self.should_reconnect:
            return

        self.state = WebSocketState.RECONNECTING
        logger.info(f"将在 {self.reconnect_delay} 秒后重连...")

        time.sleep(self.reconnect_delay)

        # 指数退避
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

        # 重新建立连接
        self.state = WebSocketState.DISCONNECTED
        self.connect()

    def _start_heartbeat(self):
        """启动心跳"""
        def heartbeat():
            while self.state == WebSocketState.CONNECTED:
                try:
                    if self.ws:
                        self.ws.send(self.heartbeat_message)
                        logger.debug("发送心跳")
                    time.sleep(self.heartbeat_interval)
                except Exception as e:
                    logger.error(f"心跳发送失败: {e}")
                    break

        self.heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        self.heartbeat_thread.start()

    def _stop_heartbeat(self):
        """停止心跳"""
        if self.heartbeat_thread:
            self.heartbeat_thread = None

    def send(self, message: str):
        """发送消息"""
        if self.ws and self.state == WebSocketState.CONNECTED:
            self.ws.send(message)
        else:
            logger.warning("WebSocket未连接，无法发送消息")

    def close(self):
        """关闭连接"""
        self.should_reconnect = False

        if self.ws:
            self.ws.close()

        self._stop_heartbeat()

        if self.thread:
            self.thread.join(timeout=5)


class WebSocketPluginTemplate(BasePluginTemplate):
    """
    WebSocket插件模板

    提供基于WebSocket的实时数据推送标准实现
    """

    def __init__(self):
        """初始化WebSocket插件"""
        super().__init__()

        # WebSocket连接池
        self.connections: Dict[str, WebSocketConnection] = {}

        # 订阅管理
        self.subscriptions: Dict[str, List[str]] = {}  # channel -> [symbols]

        # 消息队列
        self.message_queue = Queue()

        # 回调注册
        self.callbacks: Dict[str, List[Callable]] = {}  # channel -> [callbacks]

        # 默认配置
        self.DEFAULT_WS_CONFIG = {
            'ws_url': '',
            'heartbeat_interval': 30,
            'heartbeat_message': 'ping',
            'max_connections': 5,
            'auto_reconnect': True,
            'reconnect_delay': 1,
            'max_reconnect_delay': 60,
        }

        # 合并配置
        self.DEFAULT_CONFIG.update(self.DEFAULT_WS_CONFIG)

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        config = super()._get_default_config()
        config.update(self.DEFAULT_WS_CONFIG)
        return config

    def _check_dependencies(self) -> bool:
        """检查依赖"""
        if not WEBSOCKET_AVAILABLE:
            self.logger.error("websocket-client 库未安装，请安装: pip install websocket-client")
            return False
        return True

    def _validate_config(self) -> bool:
        """验证配置"""
        if not super()._validate_config():
            return False

        # 验证WebSocket URL
        if not self.config.get('ws_url'):
            self.logger.error("ws_url 未配置")
            return False

        return True

    def _establish_connection(self) -> bool:
        """建立WebSocket连接"""
        try:
            # 创建主连接
            main_connection = self._create_connection(
                url=self.config['ws_url'],
                connection_id='main'
            )

            # 等待连接建立（最多10秒）
            timeout = 10
            start_time = time.time()
            while main_connection.state != WebSocketState.CONNECTED:
                if time.time() - start_time > timeout:
                    raise TimeoutError("WebSocket连接超时")
                time.sleep(0.1)

            return True

        except Exception as e:
            self.logger.error(f"建立WebSocket连接失败: {e}")
            return False

    def _create_connection(
        self,
        url: str,
        connection_id: str
    ) -> WebSocketConnection:
        """
        创建WebSocket连接

        Args:
            url: WebSocket URL
            connection_id: 连接ID

        Returns:
            WebSocketConnection: 连接对象
        """
        connection = WebSocketConnection(
            url=url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
            heartbeat_interval=self.config.get('heartbeat_interval', 30),
            heartbeat_message=self.config.get('heartbeat_message', 'ping')
        )

        self.connections[connection_id] = connection
        connection.connect()

        return connection

    def _on_open(self, ws):
        """连接建立回调"""
        self.logger.info("WebSocket连接已建立")

        # 恢复订阅
        self._restore_subscriptions(ws)

        # 子类可以覆盖此方法执行额外的初始化
        self._on_ws_open(ws)

    @abstractmethod
    def _on_ws_open(self, ws):
        """
        WebSocket连接建立回调

        子类可以实现此方法执行特定的初始化逻辑

        Args:
            ws: WebSocket对象
        """
        pass

    def _on_message(self, ws, message):
        """消息接收回调"""
        try:
            # 解析消息
            data = json.loads(message)

            # 路由消息
            self._route_message(data)

        except json.JSONDecodeError:
            self.logger.warning(f"无法解析消息: {message}")
        except Exception as e:
            self.logger.error(f"处理消息异常: {e}")

    @abstractmethod
    def _route_message(self, data: Dict):
        """
        路由消息到对应的回调

        子类必须实现此方法，根据消息内容路由到不同的处理函数

        Args:
            data: 解析后的消息数据
        """
        pass

    def _on_error(self, ws, error):
        """错误回调"""
        self.logger.error(f"WebSocket错误: {error}")
        self._health_score = max(0.0, self._health_score - 0.2)

    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭回调"""
        self.logger.warning(f"WebSocket连接已关闭: {close_status_code} - {close_msg}")

    def _restore_subscriptions(self, ws):
        """恢复订阅"""
        for channel, symbols in self.subscriptions.items():
            for symbol in symbols:
                self.subscribe(channel, symbol)

    def subscribe(self, channel: str, symbol: str, callback: Callable = None):
        """
        订阅数据

        Args:
            channel: 频道（如'kline', 'ticker'等）
            symbol: 交易对
            callback: 数据回调函数
        """
        # 记录订阅
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []

        if symbol not in self.subscriptions[channel]:
            self.subscriptions[channel].append(symbol)

        # 注册回调
        if callback:
            if channel not in self.callbacks:
                self.callbacks[channel] = []
            self.callbacks[channel].append(callback)

        # 发送订阅消息
        subscribe_message = self._build_subscribe_message(channel, symbol)
        if subscribe_message:
            self._send_to_connection('main', subscribe_message)

    @abstractmethod
    def _build_subscribe_message(self, channel: str, symbol: str) -> Optional[str]:
        """
        构建订阅消息

        子类必须实现此方法，根据特定API的格式构建订阅消息

        Args:
            channel: 频道
            symbol: 交易对

        Returns:
            Optional[str]: 订阅消息JSON字符串，None表示不需要发送
        """
        return None

    def unsubscribe(self, channel: str, symbol: str):
        """
        取消订阅

        Args:
            channel: 频道
            symbol: 交易对
        """
        # 移除订阅记录
        if channel in self.subscriptions and symbol in self.subscriptions[channel]:
            self.subscriptions[channel].remove(symbol)

        # 发送取消订阅消息
        unsubscribe_message = self._build_unsubscribe_message(channel, symbol)
        if unsubscribe_message:
            self._send_to_connection('main', unsubscribe_message)

    @abstractmethod
    def _build_unsubscribe_message(self, channel: str, symbol: str) -> Optional[str]:
        """
        构建取消订阅消息

        子类应实现此方法

        Args:
            channel: 频道
            symbol: 交易对

        Returns:
            Optional[str]: 取消订阅消息JSON字符串
        """
        return None

    def _send_to_connection(self, connection_id: str, message: str):
        """发送消息到指定连接"""
        if connection_id in self.connections:
            self.connections[connection_id].send(message)
        else:
            self.logger.warning(f"连接不存在: {connection_id}")

    def _perform_health_check(self) -> bool:
        """执行健康检查"""
        # 检查主连接状态
        if 'main' not in self.connections:
            return False

        main_conn = self.connections['main']

        # 检查连接状态
        if main_conn.state != WebSocketState.CONNECTED:
            return False

        # 检查是否有消息接收（最近60秒内）
        if main_conn.last_message_time > 0:
            if time.time() - main_conn.last_message_time > 60:
                self.logger.warning("长时间未收到消息")
                return False

        return True

    def _cleanup(self):
        """清理资源"""
        # 关闭所有WebSocket连接
        for connection_id, connection in list(self.connections.items()):
            connection.close()

        self.connections.clear()
        self.subscriptions.clear()
        self.callbacks.clear()


# 使用示例
if __name__ == "__main__":
    # 子类应继承并实现抽象方法
    pass
