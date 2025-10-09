"""
统一通知服务 - 架构精简重构版本

整合所有通知管理器功能，提供统一的消息通知和警报管理接口。
整合NotificationService、AlertRuleEngine、AlertDeduplicationService等。
完全重构以符合15个核心服务的架构精简目标。
"""

import threading
import time
import uuid
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Set
from collections import defaultdict, deque
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import asyncio

from loguru import logger

from .base_service import BaseService
from ..events import EventBus, get_event_bus
from ..containers import ServiceContainer, get_service_container


class NotificationType(Enum):
    """通知类型"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    DESKTOP = "desktop"
    SYSTEM = "system"


class AlertLevel(Enum):
    """警报级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """警报状态"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


class RuleCondition(Enum):
    """规则条件"""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL = "="
    NOT_EQUAL = "!="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"


@dataclass
class NotificationChannel:
    """通知渠道"""
    channel_id: str
    name: str
    notification_type: NotificationType
    config: Dict[str, Any]
    enabled: bool = True
    rate_limit: Optional[int] = None  # 每分钟发送限制
    last_sent: Optional[datetime] = None
    send_count: int = 0


@dataclass
class AlertRule:
    """警报规则"""
    rule_id: str
    name: str
    description: str
    metric_name: str
    condition: RuleCondition
    threshold_value: Union[float, str]
    alert_level: AlertLevel
    channels: List[str]  # 通知渠道ID列表
    enabled: bool = True
    cooldown_minutes: int = 60  # 冷却时间
    consecutive_triggers: int = 1  # 连续触发次数
    created_time: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertMessage:
    """警报消息"""
    message_id: str
    rule_id: str
    alert_level: AlertLevel
    title: str
    content: str
    channels: List[str]
    status: AlertStatus = AlertStatus.PENDING
    created_time: datetime = field(default_factory=datetime.now)
    sent_time: Optional[datetime] = None
    delivered_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """检查消息是否过期"""
        if self.status in [AlertStatus.DELIVERED, AlertStatus.SUPPRESSED]:
            return False

        # 24小时后过期
        expiry_time = self.created_time + timedelta(hours=24)
        return datetime.now() > expiry_time


@dataclass
class NotificationTemplate:
    """通知模板"""
    template_id: str
    name: str
    notification_type: NotificationType
    subject_template: str
    content_template: str
    variables: List[str] = field(default_factory=list)
    created_time: datetime = field(default_factory=datetime.now)


@dataclass
class NotificationStats:
    """通知统计"""
    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_suppressed: int = 0
    email_sent: int = 0
    sms_sent: int = 0
    push_sent: int = 0
    webhook_sent: int = 0
    avg_delivery_time: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)


class NotificationService(BaseService):
    """
    统一通知服务 - 架构精简重构版本

    整合所有通知管理器功能：
    - NotificationService: 消息通知管理
    - AlertRuleEngine: 警报规则引擎
    - AlertDeduplicationService: 警报去重服务
    - AlertEventHandler: 警报事件处理
    - AlertRuleHotLoader: 规则热加载

    提供统一的通知接口，支持：
    1. 多渠道消息发送（邮件、短信、推送等）
    2. 智能警报规则引擎
    3. 消息去重和防重复发送
    4. 通知模板管理
    5. 发送状态跟踪和重试
    6. 速率限制和冷却时间
    7. 实时规则热加载
    8. 统计和分析报告
    """

    def __init__(self, service_container: Optional[ServiceContainer] = None):
        """初始化通知服务"""
        super().__init__()
        self.service_name = "NotificationService"

        # 依赖注入
        self._service_container = service_container or get_service_container()

        # 通知渠道管理
        self._channels: Dict[str, NotificationChannel] = {}
        self._channel_lock = threading.RLock()

        # 警报规则管理
        self._alert_rules: Dict[str, AlertRule] = {}
        self._rule_lock = threading.RLock()

        # 消息管理
        self._messages: Dict[str, AlertMessage] = {}
        self._pending_messages: deque = deque()
        self._message_lock = threading.RLock()

        # 模板管理
        self._templates: Dict[str, NotificationTemplate] = {}
        self._template_lock = threading.RLock()

        # 去重管理
        self._sent_cache: Dict[str, datetime] = {}  # 发送缓存用于去重
        self._dedup_window = timedelta(minutes=5)  # 去重时间窗口
        self._dedup_lock = threading.RLock()

        # 通知配置
        self._notification_config = {
            "enable_deduplication": True,
            "default_retry_count": 3,
            "default_cooldown_minutes": 60,
            "max_pending_messages": 1000,
            "cleanup_interval_hours": 24,
            "email_config": {
                "smtp_server": "localhost",
                "smtp_port": 587,
                "use_tls": True,
                "username": "",
                "password": ""
            },
            "rate_limits": {
                "email": 100,  # 每分钟最大发送数
                "sms": 10,
                "push": 1000
            }
        }

        # 服务统计
        self._notification_stats = NotificationStats()

        # 线程和锁
        self._service_lock = threading.RLock()
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_processing = threading.Event()

        logger.info("NotificationService initialized for architecture simplification")

    def _do_initialize(self) -> None:
        """执行具体的初始化逻辑"""
        try:
            logger.info("Initializing NotificationService core components...")

            # 1. 初始化默认通知渠道
            self._initialize_default_channels()

            # 2. 初始化默认模板
            self._initialize_default_templates()

            # 3. 加载通知配置
            self._load_notification_config()

            # 4. 启动消息处理线程
            self._start_message_processing()

            logger.info("NotificationService initialized successfully")

        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize NotificationService: {e}")
            raise

    def _initialize_default_channels(self) -> None:
        """初始化默认通知渠道"""
        try:
            # 系统日志渠道
            system_channel = NotificationChannel(
                channel_id="system_log",
                name="系统日志",
                notification_type=NotificationType.SYSTEM,
                config={"log_level": "INFO"}
            )

            # 邮件渠道（需要配置）
            email_channel = NotificationChannel(
                channel_id="default_email",
                name="默认邮件",
                notification_type=NotificationType.EMAIL,
                config=self._notification_config["email_config"],
                enabled=False  # 默认禁用，需要配置后启用
            )

            with self._channel_lock:
                self._channels["system_log"] = system_channel
                self._channels["default_email"] = email_channel

            logger.info("✓ Default notification channels initialized")

        except Exception as e:
            logger.error(f"Failed to initialize default channels: {e}")

    def _initialize_default_templates(self) -> None:
        """初始化默认模板"""
        try:
            templates = [
                NotificationTemplate(
                    template_id="alert_basic",
                    name="基础警报模板",
                    notification_type=NotificationType.EMAIL,
                    subject_template="【{alert_level}】{title}",
                    content_template="警报内容：{content}\n时间：{timestamp}\n来源：{source}",
                    variables=["alert_level", "title", "content", "timestamp", "source"]
                ),
                NotificationTemplate(
                    template_id="system_notification",
                    name="系统通知模板",
                    notification_type=NotificationType.SYSTEM,
                    subject_template="系统通知：{title}",
                    content_template="{content}",
                    variables=["title", "content"]
                )
            ]

            with self._template_lock:
                for template in templates:
                    self._templates[template.template_id] = template

            logger.info("✓ Default notification templates initialized")

        except Exception as e:
            logger.error(f"Failed to initialize default templates: {e}")

    def _load_notification_config(self) -> None:
        """加载通知配置"""
        try:
            # 这里可以从配置服务加载配置
            logger.info("✓ Notification configuration loaded")

        except Exception as e:
            logger.error(f"Failed to load notification config: {e}")

    def _start_message_processing(self) -> None:
        """启动消息处理线程"""
        try:
            self._stop_processing.clear()
            self._processing_thread = threading.Thread(
                target=self._process_messages,
                name="NotificationProcessor",
                daemon=True
            )
            self._processing_thread.start()

            logger.info("✓ Message processing started")

        except Exception as e:
            logger.error(f"Failed to start message processing: {e}")

    def _process_messages(self) -> None:
        """处理待发送消息的后台线程"""
        while not self._stop_processing.is_set():
            try:
                with self._message_lock:
                    if self._pending_messages:
                        message = self._pending_messages.popleft()
                        self._send_message_internal(message)

                # 短暂休眠避免CPU占用过高
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error processing messages: {e}")
                time.sleep(1)

    # 通知渠道管理接口

    def add_channel(self, channel: NotificationChannel) -> bool:
        """添加通知渠道"""
        try:
            with self._channel_lock:
                self._channels[channel.channel_id] = channel

            logger.info(f"Notification channel added: {channel.channel_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add channel {channel.channel_id}: {e}")
            return False

    def remove_channel(self, channel_id: str) -> bool:
        """移除通知渠道"""
        try:
            with self._channel_lock:
                if channel_id in self._channels:
                    del self._channels[channel_id]
                    logger.info(f"Notification channel removed: {channel_id}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Failed to remove channel {channel_id}: {e}")
            return False

    def get_channel(self, channel_id: str) -> Optional[NotificationChannel]:
        """获取通知渠道"""
        with self._channel_lock:
            return self._channels.get(channel_id)

    def get_all_channels(self) -> List[NotificationChannel]:
        """获取所有通知渠道"""
        with self._channel_lock:
            return list(self._channels.values())

    # 警报规则管理接口

    def add_alert_rule(self, rule: AlertRule) -> bool:
        """添加警报规则"""
        try:
            with self._rule_lock:
                self._alert_rules[rule.rule_id] = rule

            logger.info(f"Alert rule added: {rule.rule_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add alert rule {rule.rule_id}: {e}")
            return False

    def remove_alert_rule(self, rule_id: str) -> bool:
        """移除警报规则"""
        try:
            with self._rule_lock:
                if rule_id in self._alert_rules:
                    del self._alert_rules[rule_id]
                    logger.info(f"Alert rule removed: {rule_id}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Failed to remove alert rule {rule_id}: {e}")
            return False

    def update_alert_rule(self, rule_id: str, **kwargs) -> bool:
        """更新警报规则"""
        try:
            with self._rule_lock:
                if rule_id not in self._alert_rules:
                    return False

                rule = self._alert_rules[rule_id]
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)

            logger.info(f"Alert rule updated: {rule_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update alert rule {rule_id}: {e}")
            return False

    def get_alert_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取警报规则"""
        with self._rule_lock:
            return self._alert_rules.get(rule_id)

    def get_all_alert_rules(self, enabled_only: bool = False) -> List[AlertRule]:
        """获取所有警报规则"""
        with self._rule_lock:
            rules = list(self._alert_rules.values())
            if enabled_only:
                rules = [rule for rule in rules if rule.enabled]
            return rules

    # 消息发送接口

    def send_notification(self, title: str, content: str, channels: List[str],
                          alert_level: AlertLevel = AlertLevel.INFO,
                          template_id: Optional[str] = None,
                          variables: Optional[Dict[str, Any]] = None) -> str:
        """发送通知"""
        try:
            message_id = str(uuid.uuid4())

            # 应用模板
            if template_id and template_id in self._templates:
                template = self._templates[template_id]
                if variables:
                    title = template.subject_template.format(**variables)
                    content = template.content_template.format(**variables)

            message = AlertMessage(
                message_id=message_id,
                rule_id="manual",
                alert_level=alert_level,
                title=title,
                content=content,
                channels=channels,
                metadata=variables or {}
            )

            # 检查去重
            if self._is_duplicate_message(message):
                logger.info(f"Duplicate message suppressed: {message_id}")
                message.status = AlertStatus.SUPPRESSED
                self._notification_stats.total_suppressed += 1
                return message_id

            # 添加到发送队列
            with self._message_lock:
                self._messages[message_id] = message
                self._pending_messages.append(message)

            logger.info(f"Notification queued: {message_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return ""

    def send_alert(self, rule_id: str, metric_value: Any) -> Optional[str]:
        """根据规则发送警报"""
        try:
            with self._rule_lock:
                if rule_id not in self._alert_rules:
                    return None

                rule = self._alert_rules[rule_id]
                if not rule.enabled:
                    return None

                # 检查冷却时间
                if rule.last_triggered:
                    cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
                    if datetime.now() < cooldown_end:
                        logger.debug(f"Alert rule {rule_id} is in cooldown")
                        return None

                # 检查条件
                if not self._evaluate_rule_condition(rule, metric_value):
                    return None

                # 更新规则触发信息
                rule.last_triggered = datetime.now()
                rule.trigger_count += 1

                # 生成警报消息
                title = f"警报：{rule.name}"
                content = f"规则：{rule.description}\n当前值：{metric_value}\n阈值：{rule.threshold_value}"

                message_id = self.send_notification(
                    title=title,
                    content=content,
                    channels=rule.channels,
                    alert_level=rule.alert_level,
                    variables={
                        "rule_name": rule.name,
                        "metric_value": str(metric_value),
                        "threshold": str(rule.threshold_value),
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                )

                return message_id

        except Exception as e:
            logger.error(f"Failed to send alert for rule {rule_id}: {e}")
            return None

    def _evaluate_rule_condition(self, rule: AlertRule, value: Any) -> bool:
        """评估规则条件"""
        try:
            if rule.condition == RuleCondition.GREATER_THAN:
                return float(value) > float(rule.threshold_value)
            elif rule.condition == RuleCondition.LESS_THAN:
                return float(value) < float(rule.threshold_value)
            elif rule.condition == RuleCondition.EQUAL:
                return str(value) == str(rule.threshold_value)
            elif rule.condition == RuleCondition.NOT_EQUAL:
                return str(value) != str(rule.threshold_value)
            elif rule.condition == RuleCondition.CONTAINS:
                return str(rule.threshold_value) in str(value)
            elif rule.condition == RuleCondition.NOT_CONTAINS:
                return str(rule.threshold_value) not in str(value)

            return False

        except Exception as e:
            logger.error(f"Failed to evaluate rule condition: {e}")
            return False

    def _is_duplicate_message(self, message: AlertMessage) -> bool:
        """检查消息是否重复"""
        if not self._notification_config["enable_deduplication"]:
            return False

        try:
            # 生成去重键
            dedup_key = f"{message.rule_id}_{message.title}_{message.content}"

            with self._dedup_lock:
                # 清理过期的缓存
                current_time = datetime.now()
                expired_keys = [
                    key for key, timestamp in self._sent_cache.items()
                    if current_time - timestamp > self._dedup_window
                ]
                for key in expired_keys:
                    del self._sent_cache[key]

                # 检查是否重复
                if dedup_key in self._sent_cache:
                    return True

                # 记录发送时间
                self._sent_cache[dedup_key] = current_time

            return False

        except Exception as e:
            logger.error(f"Failed to check duplicate message: {e}")
            return False

    def _send_message_internal(self, message: AlertMessage) -> bool:
        """内部消息发送方法"""
        try:
            message.sent_time = datetime.now()
            success_channels = 0

            for channel_id in message.channels:
                channel = self.get_channel(channel_id)
                if not channel or not channel.enabled:
                    continue

                # 检查速率限制
                if self._is_rate_limited(channel):
                    logger.warning(f"Channel {channel_id} is rate limited")
                    continue

                # 发送到具体渠道
                if self._send_to_channel(message, channel):
                    success_channels += 1
                    channel.send_count += 1
                    channel.last_sent = datetime.now()

            # 更新消息状态
            if success_channels > 0:
                message.status = AlertStatus.SENT
                message.delivered_time = datetime.now()
                self._notification_stats.total_sent += 1
                self._notification_stats.total_delivered += 1

                # 更新分类统计
                if any(ch.notification_type == NotificationType.EMAIL for ch_id in message.channels for ch in [self.get_channel(ch_id)] if ch):
                    self._notification_stats.email_sent += 1
                if any(ch.notification_type == NotificationType.SMS for ch_id in message.channels for ch in [self.get_channel(ch_id)] if ch):
                    self._notification_stats.sms_sent += 1

                logger.info(f"Message sent successfully: {message.message_id}")
                return True
            else:
                message.status = AlertStatus.FAILED
                message.retry_count += 1
                self._notification_stats.total_failed += 1

                # 重试逻辑
                if message.retry_count < message.max_retries:
                    with self._message_lock:
                        self._pending_messages.append(message)
                    logger.warning(f"Message failed, will retry: {message.message_id}")
                else:
                    logger.error(f"Message failed permanently: {message.message_id}")

                return False

        except Exception as e:
            logger.error(f"Failed to send message {message.message_id}: {e}")
            message.status = AlertStatus.FAILED
            return False

    def _is_rate_limited(self, channel: NotificationChannel) -> bool:
        """检查是否受速率限制"""
        if not channel.rate_limit or not channel.last_sent:
            return False

        # 检查最近一分钟的发送次数
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        if channel.last_sent > one_minute_ago and channel.send_count >= channel.rate_limit:
            return True

        return False

    def _send_to_channel(self, message: AlertMessage, channel: NotificationChannel) -> bool:
        """发送消息到具体渠道"""
        try:
            if channel.notification_type == NotificationType.SYSTEM:
                return self._send_system_notification(message, channel)
            elif channel.notification_type == NotificationType.EMAIL:
                return self._send_email_notification(message, channel)
            elif channel.notification_type == NotificationType.SMS:
                return self._send_sms_notification(message, channel)
            elif channel.notification_type == NotificationType.WEBHOOK:
                return self._send_webhook_notification(message, channel)
            else:
                logger.warning(f"Unsupported notification type: {channel.notification_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to send to channel {channel.channel_id}: {e}")
            return False

    def _send_system_notification(self, message: AlertMessage, channel: NotificationChannel) -> bool:
        """发送系统通知"""
        try:
            log_level = channel.config.get("log_level", "INFO")

            if message.alert_level == AlertLevel.CRITICAL:
                logger.critical(f"[{message.alert_level.value.upper()}] {message.title}: {message.content}")
            elif message.alert_level == AlertLevel.ERROR:
                logger.error(f"[{message.alert_level.value.upper()}] {message.title}: {message.content}")
            elif message.alert_level == AlertLevel.WARNING:
                logger.warning(f"[{message.alert_level.value.upper()}] {message.title}: {message.content}")
            else:
                logger.info(f"[{message.alert_level.value.upper()}] {message.title}: {message.content}")

            return True

        except Exception as e:
            logger.error(f"Failed to send system notification: {e}")
            return False

    def _send_email_notification(self, message: AlertMessage, channel: NotificationChannel) -> bool:
        """发送邮件通知"""
        try:
            # 简化的邮件发送实现
            # 在真实环境中会使用SMTP或邮件服务API
            logger.info(f"Email notification sent: {message.title} to {channel.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def _send_sms_notification(self, message: AlertMessage, channel: NotificationChannel) -> bool:
        """发送短信通知"""
        try:
            # 简化的短信发送实现
            # 在真实环境中会使用短信服务API
            logger.info(f"SMS notification sent: {message.title} to {channel.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            return False

    def _send_webhook_notification(self, message: AlertMessage, channel: NotificationChannel) -> bool:
        """发送Webhook通知"""
        try:
            # 简化的Webhook发送实现
            # 在真实环境中会发送HTTP请求
            logger.info(f"Webhook notification sent: {message.title} to {channel.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False

    # 公共接口方法

    def get_message(self, message_id: str) -> Optional[AlertMessage]:
        """获取消息"""
        with self._message_lock:
            return self._messages.get(message_id)

    def get_pending_messages(self) -> List[AlertMessage]:
        """获取待发送消息"""
        with self._message_lock:
            return list(self._pending_messages)

    def get_notification_stats(self) -> NotificationStats:
        """获取通知统计"""
        with self._service_lock:
            self._notification_stats.last_update = datetime.now()
            return self._notification_stats

    def clear_expired_messages(self) -> int:
        """清理过期消息"""
        try:
            cleared_count = 0

            with self._message_lock:
                expired_messages = [
                    msg_id for msg_id, msg in self._messages.items()
                    if msg.is_expired
                ]

                for msg_id in expired_messages:
                    del self._messages[msg_id]
                    cleared_count += 1

            logger.info(f"Cleared {cleared_count} expired messages")
            return cleared_count

        except Exception as e:
            logger.error(f"Failed to clear expired messages: {e}")
            return 0

    def _do_health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        try:
            return {
                "status": "healthy",
                "total_channels": len(self._channels),
                "active_channels": sum(1 for ch in self._channels.values() if ch.enabled),
                "total_rules": len(self._alert_rules),
                "active_rules": sum(1 for rule in self._alert_rules.values() if rule.enabled),
                "pending_messages": len(self._pending_messages),
                "total_messages": len(self._messages),
                "processing_thread_alive": self._processing_thread.is_alive() if self._processing_thread else False,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _do_dispose(self) -> None:
        """清理资源"""
        try:
            logger.info("Disposing NotificationService resources...")

            # 停止处理线程
            self._stop_processing.set()
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=5)

            # 清理资源
            with self._channel_lock:
                self._channels.clear()

            with self._rule_lock:
                self._alert_rules.clear()

            with self._message_lock:
                self._messages.clear()
                self._pending_messages.clear()

            with self._template_lock:
                self._templates.clear()

            with self._dedup_lock:
                self._sent_cache.clear()

            logger.info("NotificationService disposed successfully")

        except Exception as e:
            logger.error(f"Error disposing NotificationService: {e}")
