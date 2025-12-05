from loguru import logger
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警规则热加载服务

监听数据库变化，自动重新加载告警规则，支持实时更新
"""

import asyncio
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Callable, Set, Any
from threading import Timer, Event

from .base_service import BaseService
from db.models.alert_config_models import get_alert_config_database, AlertRule



class AlertRuleHotLoader(BaseService):
    """告警规则热加载服务"""

    def __init__(self, check_interval: int = 5):
        """
        初始化热加载服务

        Args:
            check_interval: 检查间隔（秒）
        """
        super().__init__()

        self.check_interval = check_interval
        self.db = get_alert_config_database()

        # 规则缓存和状态
        self._rules_cache: Dict[int, AlertRule] = {}
        self._rules_hash: Dict[int, str] = {}
        self._last_check_time = time.time()

        # 控制标志
        self._running = False
        self._stop_event = Event()

        # 线程用于定期检查
        self._timer_thread: Optional[Timer] = None

        # 回调函数
        self._update_callbacks: List[Callable[[List[AlertRule]], None]] = []

        logger.info("告警规则热加载服务初始化完成")

    def _do_initialize(self) -> None:
        """初始化服务"""
        try:
            # 加载初始规则
            self._load_initial_rules()
            logger.info("告警规则热加载服务初始化成功")
        except Exception as e:
            logger.error(f" 告警规则热加载服务初始化失败: {e}")
            raise

    def _load_initial_rules(self):
        """加载初始规则"""
        try:
            rules = self.db.load_alert_rules()
            self._update_rules_cache(rules)
            logger.info(f"加载了 {len(rules)} 个告警规则")
        except Exception as e:
            logger.error(f"加载初始规则失败: {e}")
            raise

    def _update_rules_cache(self, rules: List[AlertRule]):
        """更新规则缓存"""
        new_cache = {}
        new_hash = {}

        for rule in rules:
            rule_hash = self._calculate_rule_hash(rule)
            new_cache[rule.id] = rule
            new_hash[rule.id] = rule_hash

        self._rules_cache = new_cache
        self._rules_hash = new_hash

    def _calculate_rule_hash(self, rule: AlertRule) -> str:
        """计算规则哈希值"""
        rule_data = f"{rule.name}_{rule.metric_name}_{rule.operator}_{rule.threshold_value}_{rule.enabled}_{rule.updated_at}"
        return hashlib.md5(rule_data.encode()).hexdigest()

    def start(self):
        """启动热加载服务"""
        if self._running:
            logger.warning("热加载服务已在运行")
            return

        self._running = True
        self._stop_event.clear()

        # 启动定时器线程
        self._schedule_next_check()

        logger.info(f" 告警规则热加载服务已启动，检查间隔: {self.check_interval}秒")

    def stop(self):
        """停止热加载服务"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        # 停止定时器线程
        if self._timer_thread:
            self._timer_thread.cancel()

        logger.info("告警规则热加载服务已停止")

    def _schedule_next_check(self):
        """调度下一次检查"""
        if self._running and not self._stop_event.is_set():
            self._timer_thread = Timer(self.check_interval, self._check_for_changes)
            self._timer_thread.start()

    def _check_for_changes(self):
        """检查规则变化"""
        if not self._running:
            return

        try:
            # 从数据库加载最新规则
            current_rules = self.db.load_alert_rules()

            # 检测变化
            changes = self._detect_changes(current_rules)

            if changes['has_changes']:
                logger.info(f"检测到规则变化: 新增{len(changes['added'])}, 修改{len(changes['modified'])}, 删除{len(changes['deleted'])}")

                # 记录变化
                if changes['added']:
                    for rule in changes['added']:
                        logger.info(f"检测到新增规则: {rule.name}")

                if changes['modified']:
                    for rule in changes['modified']:
                        logger.info(f"检测到修改规则: {rule.name}")

                if changes['deleted']:
                    for rule_id in changes['deleted']:
                        logger.info(f"检测到删除规则: ID {rule_id}")

                # 更新缓存
                self._update_rules_cache(current_rules)

                # 调用回调函数
                for callback in self._update_callbacks:
                    try:
                        callback(current_rules)
                    except Exception as e:
                        logger.error(f"执行规则更新回调失败: {e}")

                        self._last_check_time = time.time()

        except Exception as e:
            logger.error(f"检查规则变化失败: {e}")
        finally:
            # 调度下一次检查
            self._schedule_next_check()

    def _detect_changes(self, current_rules: List[AlertRule]) -> Dict[str, Any]:
        """检测规则变化"""
        changes = {
            'has_changes': False,
            'added': [],
            'modified': [],
            'deleted': []
        }

        # 构建当前规则字典
        current_rules_dict = {rule.id: rule for rule in current_rules}
        current_ids = set(current_rules_dict.keys())
        cached_ids = set(self._rules_cache.keys())

        # 检测新增的规则
        added_ids = current_ids - cached_ids
        for rule_id in added_ids:
            changes['added'].append(current_rules_dict[rule_id])
            changes['has_changes'] = True

        # 检测删除的规则
        deleted_ids = cached_ids - current_ids
        for rule_id in deleted_ids:
            changes['deleted'].append(rule_id)
            changes['has_changes'] = True

        # 检测修改的规则
        common_ids = current_ids & cached_ids
        for rule_id in common_ids:
            current_rule = current_rules_dict[rule_id]
            current_hash = self._calculate_rule_hash(current_rule)
            cached_hash = self._rules_hash.get(rule_id)

            if current_hash != cached_hash:
                changes['modified'].append(current_rule)
                changes['has_changes'] = True

        return changes

    def _rule_to_dict(self, rule: AlertRule) -> Dict[str, Any]:
        """将规则对象转换为字典"""
        return {
            'id': rule.id,
            'name': rule.name,
            'rule_type': rule.rule_type,
            'priority': rule.priority,
            'enabled': rule.enabled,
            'description': rule.description,
            'metric_name': rule.metric_name,
            'operator': rule.operator,
            'threshold_value': rule.threshold_value,
            'threshold_unit': rule.threshold_unit,
            'duration': rule.duration,
            'email_notification': rule.email_notification,
            'sms_notification': rule.sms_notification,
            'desktop_notification': rule.desktop_notification,
            'sound_notification': rule.sound_notification,
            'message_template': rule.message_template,
            'created_at': rule.created_at,
            'updated_at': rule.updated_at
        }

    def add_update_callback(self, callback: Callable[[List[AlertRule]], None]):
        """添加规则更新回调函数"""
        if callback not in self._update_callbacks:
            self._update_callbacks.append(callback)
            logger.debug(f"添加规则更新回调: {callback.__name__}")

    def remove_update_callback(self, callback: Callable[[List[AlertRule]], None]):
        """移除规则更新回调函数"""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)
            logger.debug(f"移除规则更新回调: {callback.__name__}")

    def get_cached_rules(self) -> List[AlertRule]:
        """获取缓存的规则"""
        return list(self._rules_cache.values())

    def get_rule_by_id(self, rule_id: int) -> Optional[AlertRule]:
        """根据ID获取规则"""
        return self._rules_cache.get(rule_id)

    def force_reload(self):
        """强制重新加载规则"""
        try:
            logger.info("强制重新加载告警规则")
            rules = self.db.load_alert_rules()

            # 更新缓存
            self._update_rules_cache(rules)

            # 记录强制重载
            logger.info(f"强制重新加载完成，共 {len(rules)} 个规则")

            # 调用回调函数
            for callback in self._update_callbacks:
                try:
                    callback(rules)
                except Exception as e:
                    logger.error(f"执行强制重载回调失败: {e}")

            logger.info(f" 强制重新加载了 {len(rules)} 个告警规则")

        except Exception as e:
            logger.error(f" 强制重新加载规则失败: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取热加载服务统计信息"""
        return {
            'is_running': self._running,
            'check_interval': self.check_interval,
            'rules_count': len(self._rules_cache),
            'last_check_time': self._last_check_time,
            'active_callbacks': len(self._update_callbacks)
        }

    def dispose(self):
        """释放资源"""
        self.stop()
        self._update_callbacks.clear()
        self._rules_cache.clear()
        self._rules_hash.clear()
        super().dispose()


# 全局热加载服务实例
_hot_loader_instance: Optional[AlertRuleHotLoader] = None


def get_alert_rule_hot_loader() -> AlertRuleHotLoader:
    """获取告警规则热加载服务实例"""
    global _hot_loader_instance
    if _hot_loader_instance is None:
        _hot_loader_instance = AlertRuleHotLoader()
    return _hot_loader_instance


def initialize_alert_rule_hot_loader(check_interval: int = 5) -> AlertRuleHotLoader:
    """初始化告警规则热加载服务"""
    global _hot_loader_instance
    if _hot_loader_instance is None:
        _hot_loader_instance = AlertRuleHotLoader(check_interval)
        _hot_loader_instance.initialize()
    return _hot_loader_instance
