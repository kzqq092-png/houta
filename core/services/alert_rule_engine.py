from loguru import logger
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警规则执行引擎

提供完整的告警规则监控、执行和管理功能
支持异步运行、热加载和实时同步
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass
from enum import Enum
import threading

from ..events import EventBus
from .base_service import BaseService
from .alert_deduplication_service import AlertMessage, AlertLevel, get_alert_deduplication_service
from db.models.alert_config_models import get_alert_config_database, AlertRule, AlertHistory

logger = logger


class RuleStatus(Enum):
    """规则状态枚举"""
    ACTIVE = "active"          # 活跃运行中
    INACTIVE = "inactive"      # 未激活
    ERROR = "error"           # 错误状态
    LOADING = "loading"       # 加载中


@dataclass
class RuleExecutionContext:
    """规则执行上下文"""
    rule_id: int
    rule: AlertRule
    current_metrics: Dict[str, Any]
    execution_time: datetime
    last_trigger_time: Optional[datetime] = None
    trigger_count: int = 0
    consecutive_triggers: int = 0
    is_silenced: bool = False


@dataclass
class MetricValue:
    """指标值数据类"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    source: str = "system"


class AlertRuleEngine(BaseService):
    """
    告警规则执行引擎

    功能特性：
    1. 异步规则监控和执行
    2. 热加载机制（配置变更时自动重载）
    3. 实时告警历史同步
    4. 规则执行状态管理
    5. 智能静默和去重
    6. 性能优化和资源管理
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        super().__init__()

        # 核心组件
        self.db = get_alert_config_database()
        self.alert_service = get_alert_deduplication_service()

        # 运行时状态
        self._running = False
        self._rules_cache: Dict[int, AlertRule] = {}
        self._rule_contexts: Dict[int, RuleExecutionContext] = {}
        self._rule_status: Dict[int, RuleStatus] = {}
        self._metrics_cache: Dict[str, MetricValue] = {}

        # 异步组件
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._reload_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # 配置参数
        self.check_interval = 10.0  # 规则检查间隔（秒）
        self.reload_check_interval = 30.0  # 热加载检查间隔（秒）
        self.cleanup_interval = 300.0  # 清理间隔（秒）
        self.max_history_age_days = 30  # 历史记录保留天数

        # 性能统计
        self.stats = {
            'total_checks': 0,
            'triggered_alerts': 0,
            'suppressed_alerts': 0,
            'rule_reloads': 0,
            'execution_errors': 0,
            'average_check_time': 0.0
        }

        # 线程安全锁
        self._lock = threading.RLock()

        logger.info("告警规则执行引擎初始化完成")

    def _do_initialize(self) -> None:
        """初始化服务"""
        try:
            # 加载初始规则
            self._load_rules()

            # 初始化指标数据源连接
            self._setup_metric_sources()

            logger.info("告警规则执行引擎初始化成功")

        except Exception as e:
            logger.error(f"告警规则执行引擎初始化失败: {e}")
            raise

    def start(self) -> None:
        """启动引擎"""
        if self._running:
            logger.warning("告警规则引擎已在运行")
            return

        try:
            self._running = True
            logger.info("告警引擎启动中...")

            # 检查是否有运行的事件循环
            try:
                self._loop = asyncio.get_running_loop()
                # 异步模式：启动后台任务
                self._start_async_tasks()
                logger.info(" 告警规则引擎已启动 - 异步模式")

            except RuntimeError:
                # 同步模式：在新线程中运行事件循环
                self._start_sync_mode()
                logger.info(" 告警规则引擎已启动 - 同步模式")

            logger.info("告警引擎运行中")

        except Exception as e:
            self._running = False
            logger.error("告警引擎启动失败")
            logger.error(f"启动告警规则引擎失败: {e}")
            raise

    def stop(self) -> None:
        """停止引擎"""
        if not self._running:
            return

        try:
            self._running = False
            logger.info("告警引擎停止中...")

            # 取消所有任务
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
            if self._reload_task and not self._reload_task.done():
                self._reload_task.cancel()
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()

            logger.info("告警规则引擎已停止")
            logger.info("告警引擎已停止")

        except Exception as e:
            logger.error(f"停止告警规则引擎失败: {e}")

    def _start_async_tasks(self) -> None:
        """启动异步任务"""
        if self._loop:
            self._monitor_task = self._loop.create_task(self._monitor_rules_loop())
            self._reload_task = self._loop.create_task(self._hot_reload_loop())
            self._cleanup_task = self._loop.create_task(self._cleanup_loop())
            logger.info(" 异步监控任务已启动")

    def _start_sync_mode(self) -> None:
        """启动同步模式（新线程运行事件循环）"""
        import time

        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._start_async_tasks()
                self._loop.run_forever()
            except Exception as e:
                logger.error(f"事件循环运行失败: {e}")
            finally:
                self._loop.close()

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()

        # 等待事件循环启动
        time.sleep(0.2)

    async def _monitor_rules_loop(self) -> None:
        """规则监控循环"""
        logger.info("开始告警规则监控循环")

        while self._running:
            try:
                start_time = time.time()

                # 收集当前指标数据
                await self._collect_metrics()

                # 执行所有活跃规则
                await self._execute_rules()

                # 更新统计信息
                execution_time = time.time() - start_time
                self._update_stats(execution_time)

                # 等待下一个检查周期
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.info("规则监控循环被取消")
                break
            except Exception as e:
                logger.error(f"规则监控循环异常: {e}")
                self.stats['execution_errors'] += 1
                await asyncio.sleep(5)  # 错误后短暂等待

    async def _hot_reload_loop(self) -> None:
        """热加载循环"""
        logger.info("开始热加载监控循环")
        last_reload_time = datetime.now()

        while self._running:
            try:
                # 检查数据库中规则的更新时间
                if await self._check_rules_updated(last_reload_time):
                    logger.info("检测到规则配置变更，执行热加载")
                    await self._reload_rules()
                    last_reload_time = datetime.now()
                    self.stats['rule_reloads'] += 1

                await asyncio.sleep(self.reload_check_interval)

            except asyncio.CancelledError:
                logger.info("热加载循环被取消")
                break
            except Exception as e:
                logger.error(f"热加载循环异常: {e}")
                await asyncio.sleep(10)

    async def _cleanup_loop(self) -> None:
        """清理循环"""
        logger.info("开始清理任务循环")

        while self._running:
            try:
                # 清理过期的告警历史
                await self._cleanup_old_history()

                # 清理过期的指标缓存
                await self._cleanup_metrics_cache()

                # 清理规则执行上下文
                await self._cleanup_rule_contexts()

                await asyncio.sleep(self.cleanup_interval)

            except asyncio.CancelledError:
                logger.info("清理循环被取消")
                break
            except Exception as e:
                logger.error(f"清理循环异常: {e}")
                await asyncio.sleep(30)

    async def _collect_metrics(self) -> None:
        """收集当前指标数据"""
        try:
            current_time = datetime.now()

            # 收集系统资源指标
            system_metrics = await self._collect_system_metrics()

            # 收集应用指标
            app_metrics = await self._collect_application_metrics()

            # 更新指标缓存
            with self._lock:
                self._metrics_cache.update(system_metrics)
                self._metrics_cache.update(app_metrics)

            # 发送指标更新信号
            metrics_data = {name: metric.value for name, metric in self._metrics_cache.items()}
            logger.debug(f"指标数据已更新: {list(metrics_data.keys())}")

        except Exception as e:
            logger.error(f"收集指标数据失败: {e}")

    async def _collect_system_metrics(self) -> Dict[str, MetricValue]:
        """收集系统指标"""
        metrics = {}
        current_time = datetime.now()

        try:
            import psutil

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            metrics['cpu_usage'] = MetricValue(
                name='cpu_usage',
                value=cpu_percent,
                unit='%',
                timestamp=current_time,
                source='system'
            )

            # 内存使用率
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = MetricValue(
                name='memory_usage',
                value=memory.percent,
                unit='%',
                timestamp=current_time,
                source='system'
            )

            # 磁盘使用率
            import os
            try:
                if os.name == 'nt':  # Windows系统
                    try:
                        disk = psutil.disk_usage('C:\\')
                    except (OSError, ValueError):
                        # 如果C盘不可用，尝试获取当前工作目录所在磁盘
                        from pathlib import Path
                        current_drive = Path.cwd().anchor
                        disk = psutil.disk_usage(current_drive)
                else:  # Unix/Linux系统
                    disk = psutil.disk_usage('/')

                metrics['disk_usage'] = MetricValue(
                    name='disk_usage',
                    value=disk.percent,
                    unit='%',
                    timestamp=current_time,
                    source='system'
                )
            except Exception as disk_error:
                # 如果磁盘监控失败，记录调试信息但不中断整个指标收集
                logger.debug(f"磁盘使用率监控失败: {str(disk_error)}")
                # 提供默认值
                metrics['disk_usage'] = MetricValue(
                    name='disk_usage',
                    value=0.0,
                    unit='%',
                    timestamp=current_time,
                    source='system'
                )

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")

        return metrics

    async def _collect_application_metrics(self) -> Dict[str, MetricValue]:
        """收集应用指标"""
        metrics = {}
        current_time = datetime.now()

        try:
            # 从指标聚合服务获取应用指标
            from core.containers import get_service_container
            service_container = get_service_container()

            try:
                aggregation_service = service_container.resolve_by_name('MetricsAggregationService')
                if aggregation_service:
                    recent_metrics = aggregation_service.get_recent_metrics()

                    for metric_name, metric_data in recent_metrics.items():
                        if isinstance(metric_data, (int, float)):
                            metrics[f'app_{metric_name}'] = MetricValue(
                                name=f'app_{metric_name}',
                                value=float(metric_data),
                                unit='ms' if 'time' in metric_name else 'count',
                                timestamp=current_time,
                                source='application'
                            )
            except Exception as e:
                logger.debug(f"获取应用指标失败: {e}")

        except Exception as e:
            logger.error(f"收集应用指标失败: {e}")

        return metrics

    async def _execute_rules(self) -> None:
        """执行所有规则"""
        with self._lock:
            active_rules = [rule for rule in self._rules_cache.values() if rule.enabled]

        for rule in active_rules:
            try:
                await self._execute_single_rule(rule)

            except Exception as e:
                logger.error(f"执行规则 {rule.id} 失败: {e}")
                self._update_rule_status(rule.id, RuleStatus.ERROR)

    async def _execute_single_rule(self, rule: AlertRule) -> None:
        """执行单个规则"""
        rule_id = rule.id
        current_time = datetime.now()

        # 获取或创建规则执行上下文
        context = self._get_rule_context(rule_id, rule)

        # 检查静默期
        if self._is_rule_silenced(rule, context, current_time):
            return

        # 获取指标值
        metric_value = self._get_metric_value(rule.metric_name)
        if metric_value is None:
            logger.debug(f"规则 {rule_id} 的指标 {rule.metric_name} 无数据")
            return

        # 评估规则条件
        triggered = self._evaluate_rule_condition(rule, metric_value.value)

        if triggered:
            # 检查持续时间要求
            if self._check_duration_requirement(context, current_time, rule.duration):
                await self._trigger_alert(rule, metric_value, context)
                context.consecutive_triggers += 1
                context.last_trigger_time = current_time
                context.trigger_count += 1
            else:
                context.consecutive_triggers += 1
        else:
            # 重置连续触发计数
            context.consecutive_triggers = 0

        # 更新上下文
        context.execution_time = current_time
        context.current_metrics = {rule.metric_name: metric_value.value}

    def _get_rule_context(self, rule_id: int, rule: AlertRule) -> RuleExecutionContext:
        """获取或创建规则执行上下文"""
        if rule_id not in self._rule_contexts:
            self._rule_contexts[rule_id] = RuleExecutionContext(
                rule_id=rule_id,
                rule=rule,
                current_metrics={},
                execution_time=datetime.now()
            )
        return self._rule_contexts[rule_id]

    def _is_rule_silenced(self, rule: AlertRule, context: RuleExecutionContext, current_time: datetime) -> bool:
        """检查规则是否在静默期内"""
        if not context.last_trigger_time:
            return False

        # 使用规则配置的静默期
        silence_duration = timedelta(seconds=getattr(rule, 'silence_period', 300))
        return current_time - context.last_trigger_time < silence_duration

    def _get_metric_value(self, metric_name: str) -> Optional[MetricValue]:
        """获取指标值"""
        # 首先尝试从缓存获取
        with self._lock:
            cached_value = self._metrics_cache.get(metric_name)
            # 如果缓存数据较新（1分钟内），直接返回
            if cached_value and (datetime.now() - cached_value.timestamp).total_seconds() < 60:
                return cached_value

        # 缓存没有或过期，从指标服务获取实时数据
        current_value = self._fetch_realtime_metric(metric_name)
        if current_value is not None:
            metric_value = MetricValue(
                name=metric_name,
                value=current_value,
                timestamp=datetime.now(),
                unit=self._get_metric_unit(metric_name)
            )

            # 更新缓存
            with self._lock:
                self._metrics_cache[metric_name] = metric_value

            return metric_value

        return None

    def _fetch_realtime_metric(self, metric_name: str) -> Optional[float]:
        """从指标服务获取实时指标值"""
        try:
            metric_name_lower = metric_name.lower()

            # 系统资源服务只负责采集，不提供直接查询接口
            # 所以我们主要依赖指标聚合服务

            # 如果有指标聚合服务，尝试使用
            if self.metrics_service:
                try:
                    # 从指标聚合服务获取最新数据
                    if hasattr(self.metrics_service, 'resource_metrics'):
                        # CPU使用率
                        if 'cpu' in metric_name_lower and self.metrics_service.resource_metrics.get('cpu'):
                            return self._get_latest_metric_value(self.metrics_service.resource_metrics['cpu'])
                        # 内存使用率
                        elif 'memory' in metric_name_lower and self.metrics_service.resource_metrics.get('memory'):
                            return self._get_latest_metric_value(self.metrics_service.resource_metrics['memory'])
                        # 磁盘使用率
                        elif 'disk' in metric_name_lower and self.metrics_service.resource_metrics.get('disk'):
                            return self._get_latest_metric_value(self.metrics_service.resource_metrics['disk'])

                    # 从应用指标获取其他类型数据
                    if hasattr(self.metrics_service, 'app_metrics'):
                        # 响应时间
                        if 'response_time' in metric_name_lower or '响应时间' in metric_name:
                            response_metrics = self.metrics_service.app_metrics.get('response_time', [])
                            return self._get_latest_metric_value(response_metrics)
                        # 错误率
                        elif 'error_rate' in metric_name_lower or '错误率' in metric_name:
                            error_metrics = self.metrics_service.app_metrics.get('error_rate', [])
                            return self._get_latest_metric_value(error_metrics)
                        # 吞吐量
                        elif 'throughput' in metric_name_lower or '吞吐量' in metric_name:
                            throughput_metrics = self.metrics_service.app_metrics.get('throughput', [])
                            return self._get_latest_metric_value(throughput_metrics)
                        # 连接数
                        elif 'connection' in metric_name_lower or '连接数' in metric_name:
                            connection_metrics = self.metrics_service.app_metrics.get('connections', [])
                            return self._get_latest_metric_value(connection_metrics)
                        # 网络流量
                        elif 'network' in metric_name_lower or '网络流量' in metric_name:
                            network_metrics = self.metrics_service.app_metrics.get('network_traffic', [])
                            return self._get_latest_metric_value(network_metrics)

                except Exception as e:
                    logger.debug(f"从指标聚合服务获取 {metric_name} 失败: {e}")

                    # 没有指标服务时，返回None
            logger.debug(f"无法获取指标 {metric_name}: 没有可用的指标服务")
            return None

        except Exception as e:
            logger.error(f"获取指标 {metric_name} 失败: {e}")
            return None

    def _get_latest_metric_value(self, metrics_list: List) -> Optional[float]:
        """从指标列表中获取最新值"""
        if not metrics_list:
            return None

        latest_metric = metrics_list[-1]
        if isinstance(latest_metric, dict):
            return latest_metric.get('value', 0.0)
        else:
            return float(latest_metric)

    def _get_metric_unit(self, metric_name: str) -> str:
        """获取指标单位"""
        metric_name_lower = metric_name.lower()

        # 百分比类指标
        if any(word in metric_name_lower for word in ['cpu', 'memory', 'disk', 'usage', 'percent', '使用率', '错误率']):
            return '%'
        # 时间类指标
        elif any(word in metric_name_lower for word in ['time', 'duration', 'latency', 'response', '响应时间']):
            return 'ms'
        # 流量类指标
        elif any(word in metric_name_lower for word in ['network', 'traffic', 'throughput', '网络流量', '吞吐量']):
            return 'MB/s'
        # 计数类指标
        elif any(word in metric_name_lower for word in ['count', 'number', 'total', 'connection', '连接数', '次/秒']):
            return 'count'
        # 内存大小类指标
        elif any(word in metric_name_lower for word in ['memory_size', 'buffer', 'cache']):
            return 'MB'
        else:
            return 'unit'

    def _evaluate_rule_condition(self, rule: AlertRule, current_value: float) -> bool:
        """评估规则条件"""
        threshold = rule.threshold_value
        operator = rule.operator

        if operator == '>':
            return current_value > threshold
        elif operator == '>=':
            return current_value >= threshold
        elif operator == '<':
            return current_value < threshold
        elif operator == '<=':
            return current_value <= threshold
        elif operator == '==':
            return abs(current_value - threshold) < 0.001
        elif operator == '!=':
            return abs(current_value - threshold) >= 0.001
        else:
            logger.warning(f"未知的比较操作符: {operator}")
            return False

    def _check_duration_requirement(self, context: RuleExecutionContext,
                                    current_time: datetime, duration_seconds: int) -> bool:
        """检查持续时间要求"""
        if duration_seconds <= 0:
            return True

        # 简化实现：检查连续触发次数
        # 实际应该根据检查间隔和持续时间计算
        required_triggers = max(1, duration_seconds // int(self.check_interval))
        return context.consecutive_triggers >= required_triggers

    async def _trigger_alert(self, rule: AlertRule, metric_value: MetricValue,
                             context: RuleExecutionContext) -> None:
        """触发告警"""
        try:
            # 创建告警消息
            alert = AlertMessage(
                id=f"rule_{rule.id}_{int(time.time())}",
                timestamp=datetime.now(),
                level=self._get_alert_level(rule, metric_value.value),
                category=rule.rule_type,
                metric_name=rule.metric_name,
                message=self._generate_alert_message(rule, metric_value),
                current_value=metric_value.value,
                threshold_value=rule.threshold_value
            )

            # 通过去重服务处理
            should_send = self.alert_service.process_alert(alert)

            if should_send:
                # 保存到数据库
                await self._save_alert_history(alert, rule)

                # 发送信号更新UI
                alert_data = {
                    'rule_id': rule.id,
                    'message': alert.message,
                    'level': alert.level.value,
                    'timestamp': alert.timestamp.isoformat(),
                    'current_value': alert.current_value,
                    'threshold_value': alert.threshold_value
                }

                logger.info(f"告警触发事件: 规则ID {rule.id}, 消息: {alert_data.get('message', '')}")
                logger.debug("告警历史已更新")

                self.stats['triggered_alerts'] += 1
                logger.info(f"触发告警: {alert.message}")
            else:
                self.stats['suppressed_alerts'] += 1
                logger.debug(f"告警被抑制: {alert.message}")

        except Exception as e:
            logger.error(f"触发告警失败: {e}")

    def _get_alert_level(self, rule: AlertRule, current_value: float) -> AlertLevel:
        """根据规则优先级和超出程度确定告警级别"""
        try:
            threshold = rule.threshold_value
            exceed_ratio = abs(current_value - threshold) / threshold if threshold != 0 else 1

            if rule.priority == "高" or exceed_ratio >= 0.5:
                return AlertLevel.ERROR
            elif rule.priority == "中" or exceed_ratio >= 0.2:
                return AlertLevel.WARNING
            else:
                return AlertLevel.INFO

        except:
            return AlertLevel.WARNING

    def _generate_alert_message(self, rule: AlertRule, metric_value: MetricValue) -> str:
        """生成告警消息"""
        template = rule.message_template
        if template:
            try:
                return template.format(
                    rule_name=rule.name,
                    metric_name=rule.metric_name,
                    current_value=metric_value.value,
                    threshold_value=rule.threshold_value,
                    operator=rule.operator,
                    unit=rule.threshold_unit
                )
            except:
                pass

        # 默认消息模板
        return (f"告警规则 '{rule.name}' 触发: "
                f"{rule.metric_name} {rule.operator} {rule.threshold_value}{rule.threshold_unit}, "
                f"当前值: {metric_value.value}{rule.threshold_unit}")

    async def _save_alert_history(self, alert: AlertMessage, rule: AlertRule) -> None:
        """保存告警历史到数据库"""
        try:
            history = AlertHistory(
                timestamp=alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                level=alert.level.value,
                category=alert.category,
                message=alert.message,
                status='已触发',
                rule_id=rule.id,
                metric_name=alert.metric_name,
                current_value=alert.current_value,
                threshold_value=alert.threshold_value,
                recommendation=self._generate_recommendation(rule, alert)
            )

            history_id = self.db.save_alert_history(history)
            if history_id:
                logger.debug(f"告警历史已保存，ID: {history_id}")
            else:
                logger.warning("保存告警历史失败")

        except Exception as e:
            logger.error(f"保存告警历史失败: {e}")

    def _generate_recommendation(self, rule: AlertRule, alert: AlertMessage) -> str:
        """生成处理建议"""
        metric_name = rule.metric_name.lower()

        if 'cpu' in metric_name:
            return "建议检查CPU密集型进程，优化算法复杂度，或增加计算资源"
        elif 'memory' in metric_name:
            return "建议检查内存泄漏，优化数据结构，或清理不必要的缓存"
        elif 'disk' in metric_name:
            return "建议清理临时文件，归档历史数据，或扩展存储空间"
        else:
            return f"请检查 {rule.metric_name} 相关配置和系统状态"

    def _load_rules(self) -> None:
        """加载规则"""
        try:
            rules = self.db.load_alert_rules()
            with self._lock:
                self._rules_cache.clear()
                for rule in rules:
                    self._rules_cache[rule.id] = rule
                    self._update_rule_status(rule.id,
                                             RuleStatus.ACTIVE if rule.enabled else RuleStatus.INACTIVE)

            logger.info(f"已加载 {len(rules)} 个告警规则")

        except Exception as e:
            logger.error(f"加载告警规则失败: {e}")

    async def _reload_rules(self) -> None:
        """重新加载规则"""
        logger.info("执行规则热加载")
        self._load_rules()

    async def _check_rules_updated(self, last_check: datetime) -> bool:
        """检查规则是否有更新"""
        try:
            # 简化实现：检查数据库中是否有新的规则或更新时间
            rules = self.db.load_alert_rules()
            current_rule_count = len(rules)
            cached_rule_count = len(self._rules_cache)

            # 如果规则数量变化，说明有更新
            if current_rule_count != cached_rule_count:
                return True

            # 检查规则内容是否变化
            for rule in rules:
                cached_rule = self._rules_cache.get(rule.id)
                if not cached_rule or self._rule_changed(cached_rule, rule):
                    return True

            return False

        except Exception as e:
            logger.error(f"检查规则更新失败: {e}")
            return False

    def _rule_changed(self, old_rule: AlertRule, new_rule: AlertRule) -> bool:
        """检查规则是否变化"""
        # 比较关键字段
        return (old_rule.name != new_rule.name or
                old_rule.enabled != new_rule.enabled or
                old_rule.metric_name != new_rule.metric_name or
                old_rule.operator != new_rule.operator or
                old_rule.threshold_value != new_rule.threshold_value or
                old_rule.threshold_unit != new_rule.threshold_unit)

    def _setup_metric_sources(self) -> None:
        """设置指标数据源"""
        try:
            # 获取指标聚合服务实例
            from core.containers import get_service_container
            service_container = get_service_container()

            try:
                self.metrics_service = service_container.resolve_by_name('MetricsAggregationService')
                logger.info(" 已连接到指标聚合服务")
            except:
                self.metrics_service = None
                logger.warning(" 无法连接到指标聚合服务")

            # 获取系统资源服务
            try:
                self.resource_service = service_container.resolve_by_name('SystemResourceService')
                logger.info(" 已连接到系统资源服务")
            except:
                self.resource_service = None
                logger.warning(" 无法连接到系统资源服务")

            logger.info("设置指标数据源连接")

        except Exception as e:
            logger.error(f"设置指标数据源失败: {e}")
            self.metrics_service = None
            self.resource_service = None

    def _update_rule_status(self, rule_id: int, status: RuleStatus) -> None:
        """更新规则状态"""
        with self._lock:
            self._rule_status[rule_id] = status

        logger.debug(f"规则状态变更: ID {rule_id}, 状态: {status.value}")

    def _update_stats(self, execution_time: float) -> None:
        """更新统计信息"""
        self.stats['total_checks'] += 1

        # 更新平均执行时间
        current_avg = self.stats['average_check_time']
        total_checks = self.stats['total_checks']
        self.stats['average_check_time'] = (current_avg * (total_checks - 1) + execution_time) / total_checks

    async def _cleanup_old_history(self) -> None:
        """清理过期的告警历史"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_history_age_days)
            # 这里应该调用数据库的清理方法
            logger.debug(f"清理 {cutoff_date} 之前的告警历史")

        except Exception as e:
            logger.error(f"清理告警历史失败: {e}")

    async def _cleanup_metrics_cache(self) -> None:
        """清理过期的指标缓存"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(minutes=10)

            with self._lock:
                expired_keys = [
                    key for key, metric in self._metrics_cache.items()
                    if metric.timestamp < cutoff_time
                ]
                for key in expired_keys:
                    del self._metrics_cache[key]

            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期指标")

        except Exception as e:
            logger.error(f"清理指标缓存失败: {e}")

    async def _cleanup_rule_contexts(self) -> None:
        """清理规则执行上下文"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=1)

            with self._lock:
                # 清理长时间未执行的规则上下文
                inactive_rule_ids = [
                    rule_id for rule_id, context in self._rule_contexts.items()
                    if context.execution_time < cutoff_time
                ]
                for rule_id in inactive_rule_ids:
                    del self._rule_contexts[rule_id]

            if inactive_rule_ids:
                logger.debug(f"清理了 {len(inactive_rule_ids)} 个不活跃的规则上下文")

        except Exception as e:
            logger.error(f"清理规则上下文失败: {e}")

    # 公共API方法

    def reload_rules_sync(self) -> None:
        """同步重新加载规则（供外部调用）"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._reload_rules(), self._loop)
        else:
            self._load_rules()

    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            'running': self._running,
            'rules_count': len(self._rules_cache),
            'active_rules': len([r for r in self._rules_cache.values() if r.enabled]),
            'metrics_count': len(self._metrics_cache),
            'stats': self.stats.copy(),
            'rule_status': {rule_id: status.value for rule_id, status in self._rule_status.items()}
        }

    def get_rule_status(self, rule_id: int) -> Optional[str]:
        """获取特定规则的状态"""
        status = self._rule_status.get(rule_id)
        return status.value if status else None

    def force_rule_check(self, rule_id: Optional[int] = None) -> None:
        """强制执行规则检查"""
        if self._loop and self._loop.is_running():
            if rule_id:
                rule = self._rules_cache.get(rule_id)
                if rule:
                    asyncio.run_coroutine_threadsafe(
                        self._execute_single_rule(rule), self._loop
                    )
            else:
                asyncio.run_coroutine_threadsafe(self._execute_rules(), self._loop)

    def get_active_rules(self) -> Dict[int, AlertRule]:
        """获取活跃规则"""
        with self._lock:
            return self._rules_cache.copy()

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats['active_rules_count'] = len(self._rules_cache)
        stats['total_rules_count'] = len(self._rules_cache)
        return stats


# 全局引擎实例
_alert_rule_engine: Optional[AlertRuleEngine] = None


def get_alert_rule_engine() -> AlertRuleEngine:
    """获取告警规则引擎实例"""
    global _alert_rule_engine
    if _alert_rule_engine is None:
        _alert_rule_engine = AlertRuleEngine()
    return _alert_rule_engine


def initialize_alert_rule_engine(event_bus: Optional[EventBus] = None) -> AlertRuleEngine:
    """初始化告警规则引擎"""
    global _alert_rule_engine
    if _alert_rule_engine is None:
        _alert_rule_engine = AlertRuleEngine(event_bus)
        _alert_rule_engine.initialize()
    return _alert_rule_engine
