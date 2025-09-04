"""
告警事件处理器

监听系统告警事件，将其转换为告警历史记录
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import asdict

from core.services.alert_deduplication_service import (
    get_alert_deduplication_service, AlertMessage, AlertLevel
)

logger = logging.getLogger(__name__)


class AlertEventHandler:
    """告警事件处理器"""

    def __init__(self):
        self.alert_service = get_alert_deduplication_service()
        self.alert_history_file = None
        self._init_history_file()

    def _init_history_file(self):
        """初始化告警历史文件"""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'config')
            os.makedirs(config_dir, exist_ok=True)
            self.alert_history_file = os.path.join(config_dir, 'alert_history.json')
        except Exception as e:
            logger.error(f"初始化告警历史文件失败: {e}")

    def handle_resource_alert(self, event_data):
        """处理资源告警事件"""
        try:
            # 🔧 修复：支持新的ResourceAlert事件对象
            from core.events.events import ResourceAlert

            if isinstance(event_data, ResourceAlert):
                # 新的事件对象格式
                alert_event = event_data
                timestamp = alert_event.timestamp

                # 直接保存到数据库
                from db.models.alert_config_models import get_alert_config_database, AlertHistory
                db = get_alert_config_database()

                alert_history = AlertHistory(
                    timestamp=timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    level=alert_event.level.value,
                    category=alert_event.category,
                    message=alert_event.message,
                    status='活跃'
                )

                history_id = db.save_alert_history(alert_history)
                if history_id:
                    logger.info(f"✅ 资源告警已保存到数据库，ID: {history_id}")
                else:
                    logger.error("❌ 保存资源告警到数据库失败")

            else:
                # 兼容旧的字典格式
                alerts = event_data.get('alerts', [])
                timestamp = datetime.fromtimestamp(event_data.get('timestamp', datetime.now().timestamp()))

                for alert_msg in alerts:
                    # 解析告警消息
                    alert_info = self._parse_resource_alert(alert_msg)
                    if alert_info:
                        # 创建告警消息
                        alert = AlertMessage(
                            id=f"resource_{timestamp.strftime('%Y%m%d_%H%M%S')}_{hash(alert_msg) % 10000}",
                            timestamp=timestamp,
                            level=self._determine_alert_level(alert_info['current_value'], alert_info['threshold_value']),
                            category="系统资源",
                            message=alert_msg,
                            metric_name=alert_info['metric_name'],
                            current_value=alert_info['current_value'],
                            threshold_value=alert_info['threshold_value'],
                            recommendation=self._get_resource_recommendation(alert_info['metric_name'])
                        )

                        # 处理告警（去重等）
                        if self.alert_service.process_alert(alert):
                            # 保存到文件
                            self._save_alert_to_file(alert)
                            logger.info(f"处理资源告警: {alert_msg}")

        except Exception as e:
            logger.error(f"处理资源告警事件失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def handle_application_alert(self, event_data):
        """处理应用告警事件"""
        try:
            # 🔧 修复：支持新的ApplicationAlert事件对象
            from core.events.events import ApplicationAlert

            if isinstance(event_data, ApplicationAlert):
                # 新的事件对象格式
                alert_event = event_data
                timestamp = alert_event.timestamp

                # 直接保存到数据库
                from db.models.alert_config_models import get_alert_config_database, AlertHistory
                db = get_alert_config_database()

                alert_history = AlertHistory(
                    timestamp=timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    level=alert_event.level.value,
                    category=alert_event.category,
                    message=alert_event.message,
                    status='活跃'
                )

                history_id = db.save_alert_history(alert_history)
                if history_id:
                    logger.info(f"✅ 应用告警已保存到数据库，ID: {history_id}")
                else:
                    logger.error("❌ 保存应用告警到数据库失败")

            else:
                # 兼容旧的字典格式
                alerts = event_data.get('alerts', [])
                operation = event_data.get('operation', 'unknown')
                timestamp = datetime.fromtimestamp(event_data.get('timestamp', datetime.now().timestamp()))

                for alert_msg in alerts:
                    # 解析告警消息
                    alert_info = self._parse_application_alert(alert_msg, operation)
                    if alert_info:
                        # 创建告警消息
                        alert = AlertMessage(
                            id=f"app_{timestamp.strftime('%Y%m%d_%H%M%S')}_{hash(alert_msg) % 10000}",
                            timestamp=timestamp,
                            level=self._determine_alert_level(alert_info['current_value'], alert_info['threshold_value']),
                            category="应用性能",
                            message=alert_msg,
                            metric_name=alert_info['metric_name'],
                            current_value=alert_info['current_value'],
                            threshold_value=alert_info['threshold_value'],
                            recommendation=self._get_application_recommendation(alert_info['metric_name'])
                        )

                        # 处理告警（去重等）
                        if self.alert_service.process_alert(alert):
                            # 保存到文件
                            self._save_alert_to_file(alert)
                            logger.info(f"处理应用告警: {alert_msg}")

        except Exception as e:
            logger.error(f"处理应用告警事件失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _parse_resource_alert(self, alert_msg: str) -> Dict[str, Any]:
        """解析资源告警消息"""
        try:
            # 解析格式如: "CPU使用率 (85.5%) 超过阈值 (80%)"
            if "CPU使用率" in alert_msg:
                metric_name = "cpu_usage"
            elif "内存使用率" in alert_msg:
                metric_name = "memory_usage"
            elif "磁盘使用率" in alert_msg:
                metric_name = "disk_usage"
            else:
                return None

            # 提取数值
            import re
            pattern = r'\((\d+\.?\d*)%?\)'
            matches = re.findall(pattern, alert_msg)

            if len(matches) >= 2:
                current_value = float(matches[0])
                threshold_value = float(matches[1])

                return {
                    'metric_name': metric_name,
                    'current_value': current_value,
                    'threshold_value': threshold_value
                }

        except Exception as e:
            logger.warning(f"解析资源告警消息失败: {e}")

        return None

    def _parse_application_alert(self, alert_msg: str, operation: str) -> Dict[str, Any]:
        """解析应用告警消息"""
        try:
            if "响应时间" in alert_msg:
                metric_name = "response_time"
                # 解析格式如: "操作 'query_data' 响应时间 (3.25秒) 超过阈值 (2秒)"
                import re
                pattern = r'\((\d+\.?\d*)秒?\)'
                matches = re.findall(pattern, alert_msg)

                if len(matches) >= 2:
                    current_value = float(matches[0])
                    threshold_value = float(matches[1])

                    return {
                        'metric_name': metric_name,
                        'current_value': current_value,
                        'threshold_value': threshold_value
                    }

            elif "错误率" in alert_msg:
                metric_name = "error_rate"
                # 解析格式如: "操作 'query_data' 错误率 (15%) 超过阈值 (10%)"
                import re
                pattern = r'\((\d+\.?\d*)%?\)'
                matches = re.findall(pattern, alert_msg)

                if len(matches) >= 2:
                    current_value = float(matches[0])
                    threshold_value = float(matches[1])

                    return {
                        'metric_name': metric_name,
                        'current_value': current_value,
                        'threshold_value': threshold_value
                    }

        except Exception as e:
            logger.warning(f"解析应用告警消息失败: {e}")

        return None

    def _determine_alert_level(self, current_value: float, threshold_value: float) -> AlertLevel:
        """确定告警级别"""
        ratio = current_value / threshold_value if threshold_value > 0 else 1

        if ratio >= 2.0:
            return AlertLevel.CRITICAL
        elif ratio >= 1.5:
            return AlertLevel.ERROR
        elif ratio >= 1.2:
            return AlertLevel.WARNING
        else:
            return AlertLevel.INFO

    def _get_resource_recommendation(self, metric_name: str) -> str:
        """获取资源告警建议"""
        recommendations = {
            'cpu_usage': "检查CPU密集型进程，优化算法复杂度，考虑增加计算资源",
            'memory_usage': "检查内存泄漏，优化数据结构，清理不必要的缓存",
            'disk_usage': "清理临时文件，归档历史数据，扩展存储空间"
        }
        return recommendations.get(metric_name, "监控相关指标，分析具体原因")

    def _get_application_recommendation(self, metric_name: str) -> str:
        """获取应用告警建议"""
        recommendations = {
            'response_time': "优化数据库查询，减少网络延迟，使用缓存机制",
            'error_rate': "检查错误日志，增强错误处理，提高系统容错性"
        }
        return recommendations.get(metric_name, "分析应用日志，优化相关功能")

    def _save_alert_to_file(self, alert: AlertMessage):
        """保存告警到文件"""
        if not self.alert_history_file:
            return

        try:
            # 读取现有历史
            history_data = {'history': []}
            if os.path.exists(self.alert_history_file):
                with open(self.alert_history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)

            # 转换告警为字典格式
            alert_dict = {
                'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'level': self._convert_level_to_chinese(alert.level),
                'type': alert.category,
                'message': alert.message,
                'status': '已解决' if alert.is_resolved else '活跃'
            }

            # 添加新告警
            history_data['history'].append(alert_dict)

            # 保持最近1000条记录
            if len(history_data['history']) > 1000:
                history_data['history'] = history_data['history'][-1000:]

            # 保存到文件
            with open(self.alert_history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存告警到文件失败: {e}")

    def _convert_level_to_chinese(self, level: AlertLevel) -> str:
        """转换告警级别为中文"""
        level_mapping = {
            AlertLevel.INFO: '信息',
            AlertLevel.WARNING: '警告',
            AlertLevel.ERROR: '错误',
            AlertLevel.CRITICAL: '严重'
        }
        return level_mapping.get(level, '未知')


# 全局处理器实例
_alert_event_handler = None


def get_alert_event_handler() -> AlertEventHandler:
    """获取告警事件处理器实例"""
    global _alert_event_handler
    if _alert_event_handler is None:
        _alert_event_handler = AlertEventHandler()
    return _alert_event_handler


def register_alert_handlers(event_bus):
    """注册告警事件处理器到事件总线"""
    try:
        handler = get_alert_event_handler()

        # 注册资源告警处理器
        event_bus.subscribe("ResourceAlert", handler.handle_resource_alert)

        # 注册应用告警处理器
        event_bus.subscribe("ApplicationAlert", handler.handle_application_alert)

        logger.info("告警事件处理器已注册到事件总线")

    except Exception as e:
        logger.error(f"注册告警事件处理器失败: {e}")
