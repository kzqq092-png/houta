from loguru import logger
"""
告警去重服务

防止重复告警，提供智能告警管理
"""

import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logger


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AlertMessage:
    """告警消息"""
    id: str
    timestamp: datetime
    level: AlertLevel
    category: str
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    recommendation: str = ""
    is_resolved: bool = False
    resolved_timestamp: Optional[datetime] = None


class AlertDeduplicationService:
    """告警去重服务"""

    def __init__(self, dedup_window_minutes: int = 5, max_history_size: int = 1000):
        """
        初始化告警去重服务

        Args:
            dedup_window_minutes: 去重时间窗口（分钟）
            max_history_size: 最大历史记录数量
        """
        self.dedup_window = timedelta(minutes=dedup_window_minutes)
        self.max_history_size = max_history_size

        # 告警历史和去重缓存
        self.alert_history: List[AlertMessage] = []
        self.active_alerts: Dict[str, AlertMessage] = {}  # 活跃告警
        self.suppressed_alerts: Set[str] = set()  # 被抑制的告警ID

        # 统计信息
        self.stats = {
            'total_alerts': 0,
            'suppressed_alerts': 0,
            'resolved_alerts': 0,
            'active_alerts': 0
        }

    def process_alert(self, alert: AlertMessage) -> bool:
        """
        处理告警消息，进行去重检查

        Args:
            alert: 告警消息

        Returns:
            是否应该发送告警（True=发送，False=抑制）
        """
        try:
            self.stats['total_alerts'] += 1

            # 生成告警唯一标识
            alert_key = self._generate_alert_key(alert)
            alert.id = alert_key

            # 检查是否在去重窗口内
            if self._is_duplicate_alert(alert_key, alert.timestamp):
                self.stats['suppressed_alerts'] += 1
                self.suppressed_alerts.add(alert_key)
                logger.debug(f"告警被去重抑制: {alert.message}")
                return False

            # 检查是否是告警恢复
            if self._is_alert_recovery(alert):
                self._handle_alert_recovery(alert)
                return True

            # 添加到活跃告警
            self.active_alerts[alert_key] = alert
            self.stats['active_alerts'] = len(self.active_alerts)

            # 添加到历史记录
            self.alert_history.append(alert)
            self._cleanup_old_history()

            logger.info(f"新告警: {alert.level.value} - {alert.message}")
            return True

        except Exception as e:
            logger.error(f"处理告警失败: {e}")
            return True  # 出错时默认发送告警

    def resolve_alert(self, alert_key: str) -> bool:
        """
        解决告警

        Args:
            alert_key: 告警唯一标识

        Returns:
            是否成功解决
        """
        try:
            if alert_key in self.active_alerts:
                alert = self.active_alerts[alert_key]
                alert.is_resolved = True
                alert.resolved_timestamp = datetime.now()

                # 从活跃告警中移除
                del self.active_alerts[alert_key]
                self.stats['resolved_alerts'] += 1
                self.stats['active_alerts'] = len(self.active_alerts)

                logger.info(f"告警已解决: {alert.message}")
                return True

            return False

        except Exception as e:
            logger.error(f"解决告警失败: {e}")
            return False

    def get_active_alerts(self) -> List[AlertMessage]:
        """获取活跃告警列表"""
        return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24) -> List[AlertMessage]:
        """
        获取告警历史

        Args:
            hours: 获取最近多少小时的历史

        Returns:
            告警历史列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]

    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()

    def clear_history(self):
        """清空历史记录"""
        self.alert_history.clear()
        self.suppressed_alerts.clear()
        logger.info("告警历史已清空")

    def _generate_alert_key(self, alert: AlertMessage) -> str:
        """生成告警唯一标识"""
        return f"{alert.category}_{alert.metric_name}_{alert.level.value}"

    def _is_duplicate_alert(self, alert_key: str, timestamp: datetime) -> bool:
        """检查是否是重复告警"""
        if alert_key in self.active_alerts:
            last_alert = self.active_alerts[alert_key]
            time_diff = timestamp - last_alert.timestamp
            return time_diff < self.dedup_window
        return False

    def _is_alert_recovery(self, alert: AlertMessage) -> bool:
        """检查是否是告警恢复"""
        # 如果当前值回到正常范围，认为是恢复
        if alert.level == AlertLevel.INFO and "恢复" in alert.message:
            return True

        # 检查阈值恢复
        alert_key = self._generate_alert_key(alert)
        if alert_key in self.active_alerts:
            if alert.current_value < alert.threshold_value:
                return True

        return False

    def _handle_alert_recovery(self, alert: AlertMessage):
        """处理告警恢复"""
        alert_key = self._generate_alert_key(alert)
        if alert_key in self.active_alerts:
            self.resolve_alert(alert_key)
            logger.info(f"告警已自动恢复: {alert.message}")

    def _cleanup_old_history(self):
        """清理旧的历史记录"""
        if len(self.alert_history) > self.max_history_size:
            # 保留最新的记录
            self.alert_history = self.alert_history[-self.max_history_size:]

        # 清理过期的活跃告警（超过1小时未更新）
        cutoff_time = datetime.now() - timedelta(hours=1)
        expired_keys = [
            key for key, alert in self.active_alerts.items()
            if alert.timestamp < cutoff_time
        ]

        for key in expired_keys:
            del self.active_alerts[key]

        self.stats['active_alerts'] = len(self.active_alerts)


# 全局服务实例
_alert_deduplication_service = None


def get_alert_deduplication_service() -> AlertDeduplicationService:
    """获取告警去重服务实例"""
    global _alert_deduplication_service
    if _alert_deduplication_service is None:
        _alert_deduplication_service = AlertDeduplicationService()
    return _alert_deduplication_service
