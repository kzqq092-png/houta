"""
路由规则管理器

提供智能数据路由规则的配置、管理和动态更新功能。
支持复杂规则引擎、条件匹配和实时规则更新。

作者: HIkyuu-UI增强团队
版本: 1.0
日期: 2025-09-21
"""

import asyncio
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import pandas as pd
import re

from loguru import logger
from core.plugin_types import AssetType, DataType
from core.services.intelligent_data_router import RoutingStrategy, RoutingRule
from core.services.config_service import ConfigService

logger = logger.bind(module=__name__)

class RuleOperator(Enum):
    """规则操作符"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex_match"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"

class RuleConditionType(Enum):
    """规则条件类型"""
    DATA_TYPE = "data_type"
    ASSET_TYPE = "asset_type"
    DATA_SOURCE = "data_source"
    SYMBOL = "symbol"
    TIME_RANGE = "time_range"
    QUALITY_SCORE = "quality_score"
    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"
    LOAD_LEVEL = "load_level"
    CUSTOM = "custom"

@dataclass
class RuleCondition:
    """规则条件"""
    condition_type: RuleConditionType
    operator: RuleOperator
    value: Any
    field_name: Optional[str] = None  # 用于自定义字段

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """评估条件是否满足"""
        try:
            # 获取实际值
            if self.condition_type == RuleConditionType.CUSTOM and self.field_name:
                actual_value = context.get(self.field_name)
            else:
                actual_value = context.get(self.condition_type.value)

            if actual_value is None:
                return False

            # 执行比较
            return self._compare_values(actual_value, self.operator, self.value)

        except Exception as e:
            logger.error(f"评估规则条件失败: {e}")
            return False

    def _compare_values(self, actual: Any, operator: RuleOperator, expected: Any) -> bool:
        """比较两个值"""
        try:
            if operator == RuleOperator.EQUALS:
                return actual == expected
            elif operator == RuleOperator.NOT_EQUALS:
                return actual != expected
            elif operator == RuleOperator.GREATER_THAN:
                return float(actual) > float(expected)
            elif operator == RuleOperator.LESS_THAN:
                return float(actual) < float(expected)
            elif operator == RuleOperator.GREATER_EQUAL:
                return float(actual) >= float(expected)
            elif operator == RuleOperator.LESS_EQUAL:
                return float(actual) <= float(expected)
            elif operator == RuleOperator.CONTAINS:
                return str(expected) in str(actual)
            elif operator == RuleOperator.NOT_CONTAINS:
                return str(expected) not in str(actual)
            elif operator == RuleOperator.REGEX_MATCH:
                return bool(re.match(str(expected), str(actual)))
            elif operator == RuleOperator.IN_LIST:
                return actual in expected if isinstance(expected, (list, tuple)) else False
            elif operator == RuleOperator.NOT_IN_LIST:
                return actual not in expected if isinstance(expected, (list, tuple)) else True
            else:
                return False

        except Exception as e:
            logger.error(f"比较值失败: {e}")
            return False

@dataclass
class RoutingRuleConfig:
    """路由规则配置"""
    rule_id: str
    name: str
    description: str
    priority: int = 100  # 优先级，数值越小优先级越高

    # 条件配置
    conditions: List[RuleCondition] = field(default_factory=list)
    condition_logic: str = "AND"  # AND, OR

    # 路由配置
    preferred_sources: List[str] = field(default_factory=list)
    fallback_sources: List[str] = field(default_factory=list)
    strategy: RoutingStrategy = RoutingStrategy.BALANCED

    # 性能要求
    min_quality_score: float = 0.8
    max_response_time: float = 5.0
    min_success_rate: float = 0.95

    # 权重配置
    quality_weight: float = 0.4
    speed_weight: float = 0.3
    availability_weight: float = 0.3

    # 状态配置
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 统计信息
    match_count: int = 0
    success_count: int = 0

    def matches(self, context: Dict[str, Any]) -> bool:
        """检查规则是否匹配给定上下文"""
        try:
            if not self.enabled or not self.conditions:
                return False

            results = []
            for condition in self.conditions:
                result = condition.evaluate(context)
                results.append(result)

            # 根据逻辑组合结果
            if self.condition_logic.upper() == "AND":
                return all(results)
            elif self.condition_logic.upper() == "OR":
                return any(results)
            else:
                return all(results)  # 默认AND逻辑

        except Exception as e:
            logger.error(f"检查规则匹配失败: {e}")
            return False

    def to_routing_rule(self, data_type: DataType, asset_type: AssetType) -> RoutingRule:
        """转换为路由规则对象"""
        return RoutingRule(
            data_type=data_type,
            asset_type=asset_type,
            preferred_sources=self.preferred_sources,
            fallback_sources=self.fallback_sources,
            strategy=self.strategy,
            min_quality_score=self.min_quality_score,
            max_response_time=self.max_response_time,
            min_success_rate=self.min_success_rate,
            quality_weight=self.quality_weight,
            speed_weight=self.speed_weight,
            availability_weight=self.availability_weight
        )

@dataclass
class RuleTemplate:
    """规则模板"""
    template_id: str
    name: str
    description: str
    category: str  # "performance", "quality", "availability", "custom"

    # 模板配置
    conditions_template: List[Dict[str, Any]]
    default_strategy: RoutingStrategy
    default_weights: Dict[str, float]

    # 元数据
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

class RoutingRuleManager:
    """
    路由规则管理器

    提供路由规则的全生命周期管理：
    - 规则创建、编辑、删除
    - 规则模板管理
    - 条件匹配引擎
    - 动态规则更新
    - 规则性能监控
    - 规则导入导出
    """

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service

        # 规则存储
        self.rules: Dict[str, RoutingRuleConfig] = {}
        self.templates: Dict[str, RuleTemplate] = {}

        # 规则缓存
        self._rule_cache: Dict[str, List[RoutingRuleConfig]] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._last_cache_update = datetime.now()

        # 监控配置
        self._monitoring_active = False
        self._monitor_thread = None
        self._lock = threading.RLock()

        # 统计信息
        self.rule_stats = {
            'total_evaluations': 0,
            'successful_matches': 0,
            'failed_evaluations': 0,
            'avg_evaluation_time': 0.0
        }

        # 初始化默认规则和模板
        self._initialize_default_templates()
        self._load_rules_from_config()

        logger.info("路由规则管理器初始化完成")

    def _initialize_default_templates(self):
        """初始化默认规则模板"""
        try:
            # 高质量优先模板
            quality_first_template = RuleTemplate(
                template_id="quality_first",
                name="质量优先",
                description="优先选择数据质量最高的数据源",
                category="quality",
                conditions_template=[
                    {
                        "condition_type": "quality_score",
                        "operator": "greater_equal",
                        "value": 0.9
                    }
                ],
                default_strategy=RoutingStrategy.QUALITY_FIRST,
                default_weights={"quality_weight": 0.7, "speed_weight": 0.2, "availability_weight": 0.1}
            )

            # 高性能优先模板
            performance_first_template = RuleTemplate(
                template_id="performance_first",
                name="性能优先",
                description="优先选择响应速度最快的数据源",
                category="performance",
                conditions_template=[
                    {
                        "condition_type": "response_time",
                        "operator": "less_than",
                        "value": 2.0
                    }
                ],
                default_strategy=RoutingStrategy.SPEED_FIRST,
                default_weights={"quality_weight": 0.2, "speed_weight": 0.6, "availability_weight": 0.2}
            )

            # 高可用性模板
            availability_first_template = RuleTemplate(
                template_id="availability_first",
                name="可用性优先",
                description="优先选择可用性最高的数据源",
                category="availability",
                conditions_template=[
                    {
                        "condition_type": "success_rate",
                        "operator": "greater_equal",
                        "value": 0.99
                    }
                ],
                default_strategy=RoutingStrategy.FAILOVER,
                default_weights={"quality_weight": 0.2, "speed_weight": 0.2, "availability_weight": 0.6}
            )

            # 实时数据模板
            realtime_template = RuleTemplate(
                template_id="realtime_data",
                name="实时数据路由",
                description="针对实时数据的专用路由规则",
                category="custom",
                conditions_template=[
                    {
                        "condition_type": "data_type",
                        "operator": "in_list",
                        "value": ["realtime_quote", "tick_data", "level2_data"]
                    }
                ],
                default_strategy=RoutingStrategy.SPEED_FIRST,
                default_weights={"quality_weight": 0.3, "speed_weight": 0.5, "availability_weight": 0.2}
            )

            self.templates = {
                template.template_id: template
                for template in [quality_first_template, performance_first_template,
                                 availability_first_template, realtime_template]
            }

            logger.info(f"已加载 {len(self.templates)} 个默认规则模板")

        except Exception as e:
            logger.error(f"初始化默认模板失败: {e}")

    def _load_rules_from_config(self):
        """从配置服务加载规则"""
        try:
            config_data = self.config_service.get_config("routing_rules", {})

            for rule_id, rule_data in config_data.items():
                try:
                    # 转换条件
                    conditions = []
                    for cond_data in rule_data.get('conditions', []):
                        condition = RuleCondition(
                            condition_type=RuleConditionType(cond_data['condition_type']),
                            operator=RuleOperator(cond_data['operator']),
                            value=cond_data['value'],
                            field_name=cond_data.get('field_name')
                        )
                        conditions.append(condition)

                    # 创建规则配置
                    rule_config = RoutingRuleConfig(
                        rule_id=rule_id,
                        name=rule_data['name'],
                        description=rule_data['description'],
                        priority=rule_data.get('priority', 100),
                        conditions=conditions,
                        condition_logic=rule_data.get('condition_logic', 'AND'),
                        preferred_sources=rule_data.get('preferred_sources', []),
                        fallback_sources=rule_data.get('fallback_sources', []),
                        strategy=RoutingStrategy(rule_data.get('strategy', 'balanced')),
                        min_quality_score=rule_data.get('min_quality_score', 0.8),
                        max_response_time=rule_data.get('max_response_time', 5.0),
                        min_success_rate=rule_data.get('min_success_rate', 0.95),
                        quality_weight=rule_data.get('quality_weight', 0.4),
                        speed_weight=rule_data.get('speed_weight', 0.3),
                        availability_weight=rule_data.get('availability_weight', 0.3),
                        enabled=rule_data.get('enabled', True)
                    )

                    self.rules[rule_id] = rule_config

                except Exception as e:
                    logger.error(f"加载规则失败 {rule_id}: {e}")

            logger.info(f"从配置加载了 {len(self.rules)} 个路由规则")

        except Exception as e:
            logger.error(f"从配置加载规则失败: {e}")

    def create_rule(self, rule_config: RoutingRuleConfig) -> bool:
        """创建新的路由规则"""
        try:
            with self._lock:
                if rule_config.rule_id in self.rules:
                    logger.warning(f"规则已存在: {rule_config.rule_id}")
                    return False

                rule_config.created_at = datetime.now()
                rule_config.updated_at = datetime.now()

                self.rules[rule_config.rule_id] = rule_config

                # 保存到配置
                self._save_rule_to_config(rule_config)

                # 清除缓存
                self._clear_cache()

                logger.info(f"路由规则已创建: {rule_config.rule_id}")
                return True

        except Exception as e:
            logger.error(f"创建路由规则失败: {e}")
            return False

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """更新路由规则"""
        try:
            with self._lock:
                if rule_id not in self.rules:
                    logger.warning(f"规则不存在: {rule_id}")
                    return False

                rule_config = self.rules[rule_id]

                # 更新字段
                for field, value in updates.items():
                    if hasattr(rule_config, field):
                        setattr(rule_config, field, value)

                rule_config.updated_at = datetime.now()

                # 保存到配置
                self._save_rule_to_config(rule_config)

                # 清除缓存
                self._clear_cache()

                logger.info(f"路由规则已更新: {rule_id}")
                return True

        except Exception as e:
            logger.error(f"更新路由规则失败: {e}")
            return False

    def delete_rule(self, rule_id: str) -> bool:
        """删除路由规则"""
        try:
            with self._lock:
                if rule_id not in self.rules:
                    logger.warning(f"规则不存在: {rule_id}")
                    return False

                del self.rules[rule_id]

                # 从配置中删除
                self._remove_rule_from_config(rule_id)

                # 清除缓存
                self._clear_cache()

                logger.info(f"路由规则已删除: {rule_id}")
                return True

        except Exception as e:
            logger.error(f"删除路由规则失败: {e}")
            return False

    def get_rule(self, rule_id: str) -> Optional[RoutingRuleConfig]:
        """获取指定规则"""
        try:
            return self.rules.get(rule_id)
        except Exception as e:
            logger.error(f"获取规则失败: {e}")
            return None

    def list_rules(self, enabled_only: bool = False) -> List[RoutingRuleConfig]:
        """列出所有规则"""
        try:
            rules = list(self.rules.values())

            if enabled_only:
                rules = [rule for rule in rules if rule.enabled]

            # 按优先级排序
            rules.sort(key=lambda x: x.priority)

            return rules

        except Exception as e:
            logger.error(f"列出规则失败: {e}")
            return []

    def find_matching_rules(self, context: Dict[str, Any]) -> List[RoutingRuleConfig]:
        """查找匹配的规则"""
        try:
            import time
            start_time = time.time()

            # 检查缓存
            cache_key = self._generate_cache_key(context)
            if cache_key in self._rule_cache and self._is_cache_valid():
                return self._rule_cache[cache_key]

            matching_rules = []

            with self._lock:
                for rule in self.rules.values():
                    try:
                        if rule.matches(context):
                            matching_rules.append(rule)
                            rule.match_count += 1
                    except Exception as e:
                        logger.error(f"规则匹配检查失败 {rule.rule_id}: {e}")

            # 按优先级排序
            matching_rules.sort(key=lambda x: x.priority)

            # 更新缓存
            self._rule_cache[cache_key] = matching_rules

            # 更新统计
            evaluation_time = time.time() - start_time
            self._update_evaluation_stats(True, evaluation_time)

            logger.debug(f"找到 {len(matching_rules)} 个匹配规则")
            return matching_rules

        except Exception as e:
            logger.error(f"查找匹配规则失败: {e}")
            self._update_evaluation_stats(False, 0)
            return []

    def create_rule_from_template(self, template_id: str, rule_id: str, name: str,
                                  custom_config: Dict[str, Any] = None) -> Optional[RoutingRuleConfig]:
        """从模板创建规则"""
        try:
            if template_id not in self.templates:
                logger.error(f"模板不存在: {template_id}")
                return None

            template = self.templates[template_id]

            # 创建条件
            conditions = []
            for cond_template in template.conditions_template:
                condition = RuleCondition(
                    condition_type=RuleConditionType(cond_template['condition_type']),
                    operator=RuleOperator(cond_template['operator']),
                    value=cond_template['value'],
                    field_name=cond_template.get('field_name')
                )
                conditions.append(condition)

            # 创建规则配置
            rule_config = RoutingRuleConfig(
                rule_id=rule_id,
                name=name,
                description=f"基于模板 '{template.name}' 创建",
                conditions=conditions,
                strategy=template.default_strategy,
                quality_weight=template.default_weights.get('quality_weight', 0.4),
                speed_weight=template.default_weights.get('speed_weight', 0.3),
                availability_weight=template.default_weights.get('availability_weight', 0.3)
            )

            # 应用自定义配置
            if custom_config:
                for field, value in custom_config.items():
                    if hasattr(rule_config, field):
                        setattr(rule_config, field, value)

            # 创建规则
            if self.create_rule(rule_config):
                template.usage_count += 1
                return rule_config

            return None

        except Exception as e:
            logger.error(f"从模板创建规则失败: {e}")
            return None

    def validate_rule(self, rule_config: RoutingRuleConfig) -> Dict[str, Any]:
        """验证规则配置"""
        try:
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': []
            }

            # 检查基本字段
            if not rule_config.rule_id:
                validation_result['errors'].append("规则ID不能为空")

            if not rule_config.name:
                validation_result['errors'].append("规则名称不能为空")

            # 检查条件
            if not rule_config.conditions:
                validation_result['warnings'].append("规则没有设置条件，将匹配所有请求")

            # 检查数据源
            if not rule_config.preferred_sources and not rule_config.fallback_sources:
                validation_result['errors'].append("必须至少指定一个首选或备用数据源")

            # 检查权重
            total_weight = rule_config.quality_weight + rule_config.speed_weight + rule_config.availability_weight
            if abs(total_weight - 1.0) > 0.01:
                validation_result['warnings'].append(f"权重总和应为1.0，当前为{total_weight:.3f}")

            # 检查阈值
            if rule_config.min_quality_score < 0 or rule_config.min_quality_score > 1:
                validation_result['errors'].append("最小质量分数应在0-1之间")

            if rule_config.max_response_time <= 0:
                validation_result['errors'].append("最大响应时间应大于0")

            if rule_config.min_success_rate < 0 or rule_config.min_success_rate > 1:
                validation_result['errors'].append("最小成功率应在0-1之间")

            # 设置验证结果
            validation_result['is_valid'] = len(validation_result['errors']) == 0

            return validation_result

        except Exception as e:
            logger.error(f"验证规则失败: {e}")
            return {
                'is_valid': False,
                'errors': [f'验证过程异常: {e}'],
                'warnings': []
            }

    def export_rules(self, rule_ids: List[str] = None) -> Dict[str, Any]:
        """导出规则配置"""
        try:
            if rule_ids is None:
                rules_to_export = self.rules
            else:
                rules_to_export = {rid: self.rules[rid] for rid in rule_ids if rid in self.rules}

            export_data = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'rules': {}
            }

            for rule_id, rule_config in rules_to_export.items():
                # 转换为可序列化格式
                rule_dict = asdict(rule_config)

                # 转换枚举值
                for condition in rule_dict['conditions']:
                    condition['condition_type'] = condition['condition_type'].value
                    condition['operator'] = condition['operator'].value

                rule_dict['strategy'] = rule_dict['strategy'].value
                rule_dict['created_at'] = rule_config.created_at.isoformat()
                rule_dict['updated_at'] = rule_config.updated_at.isoformat()

                export_data['rules'][rule_id] = rule_dict

            return export_data

        except Exception as e:
            logger.error(f"导出规则失败: {e}")
            return {}

    def import_rules(self, import_data: Dict[str, Any], overwrite: bool = False) -> Dict[str, Any]:
        """导入规则配置"""
        try:
            import_result = {
                'success_count': 0,
                'error_count': 0,
                'errors': []
            }

            rules_data = import_data.get('rules', {})

            for rule_id, rule_dict in rules_data.items():
                try:
                    # 检查是否已存在
                    if rule_id in self.rules and not overwrite:
                        import_result['errors'].append(f"规则 {rule_id} 已存在，跳过")
                        import_result['error_count'] += 1
                        continue

                    # 转换条件
                    conditions = []
                    for cond_dict in rule_dict.get('conditions', []):
                        condition = RuleCondition(
                            condition_type=RuleConditionType(cond_dict['condition_type']),
                            operator=RuleOperator(cond_dict['operator']),
                            value=cond_dict['value'],
                            field_name=cond_dict.get('field_name')
                        )
                        conditions.append(condition)

                    # 创建规则配置
                    rule_config = RoutingRuleConfig(
                        rule_id=rule_id,
                        name=rule_dict['name'],
                        description=rule_dict['description'],
                        priority=rule_dict.get('priority', 100),
                        conditions=conditions,
                        condition_logic=rule_dict.get('condition_logic', 'AND'),
                        preferred_sources=rule_dict.get('preferred_sources', []),
                        fallback_sources=rule_dict.get('fallback_sources', []),
                        strategy=RoutingStrategy(rule_dict.get('strategy', 'balanced')),
                        min_quality_score=rule_dict.get('min_quality_score', 0.8),
                        max_response_time=rule_dict.get('max_response_time', 5.0),
                        min_success_rate=rule_dict.get('min_success_rate', 0.95),
                        quality_weight=rule_dict.get('quality_weight', 0.4),
                        speed_weight=rule_dict.get('speed_weight', 0.3),
                        availability_weight=rule_dict.get('availability_weight', 0.3),
                        enabled=rule_dict.get('enabled', True)
                    )

                    # 验证规则
                    validation = self.validate_rule(rule_config)
                    if not validation['is_valid']:
                        import_result['errors'].append(f"规则 {rule_id} 验证失败: {validation['errors']}")
                        import_result['error_count'] += 1
                        continue

                    # 创建或更新规则
                    if overwrite and rule_id in self.rules:
                        self.rules[rule_id] = rule_config
                        self._save_rule_to_config(rule_config)
                    else:
                        if self.create_rule(rule_config):
                            import_result['success_count'] += 1
                        else:
                            import_result['error_count'] += 1
                            import_result['errors'].append(f"创建规则 {rule_id} 失败")

                except Exception as e:
                    import_result['errors'].append(f"导入规则 {rule_id} 失败: {e}")
                    import_result['error_count'] += 1

            return import_result

        except Exception as e:
            logger.error(f"导入规则失败: {e}")
            return {
                'success_count': 0,
                'error_count': 1,
                'errors': [f'导入过程异常: {e}']
            }

    def _save_rule_to_config(self, rule_config: RoutingRuleConfig):
        """保存规则到配置服务"""
        try:
            # 获取现有配置
            config_data = self.config_service.get_config("routing_rules", {})

            # 转换为可序列化格式
            rule_dict = asdict(rule_config)

            # 转换枚举和日期
            for condition in rule_dict['conditions']:
                condition['condition_type'] = condition['condition_type'].value
                condition['operator'] = condition['operator'].value

            rule_dict['strategy'] = rule_dict['strategy'].value
            rule_dict['created_at'] = rule_config.created_at.isoformat()
            rule_dict['updated_at'] = rule_config.updated_at.isoformat()

            # 更新配置
            config_data[rule_config.rule_id] = rule_dict

            # 保存配置
            self.config_service.set_config("routing_rules", config_data)

        except Exception as e:
            logger.error(f"保存规则到配置失败: {e}")

    def _remove_rule_from_config(self, rule_id: str):
        """从配置服务中删除规则"""
        try:
            config_data = self.config_service.get_config("routing_rules", {})

            if rule_id in config_data:
                del config_data[rule_id]
                self.config_service.set_config("routing_rules", config_data)

        except Exception as e:
            logger.error(f"从配置删除规则失败: {e}")

    def _generate_cache_key(self, context: Dict[str, Any]) -> str:
        """生成缓存键"""
        try:
            # 使用主要字段生成缓存键
            key_parts = []
            for field in ['data_type', 'asset_type', 'data_source', 'symbol']:
                value = context.get(field, '')
                key_parts.append(f"{field}:{value}")

            return "|".join(key_parts)

        except Exception as e:
            logger.error(f"生成缓存键失败: {e}")
            return "default"

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        return datetime.now() - self._last_cache_update < self._cache_ttl

    def _clear_cache(self):
        """清除缓存"""
        try:
            self._rule_cache.clear()
            self._last_cache_update = datetime.now()
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")

    def _update_evaluation_stats(self, success: bool, evaluation_time: float):
        """更新评估统计"""
        try:
            self.rule_stats['total_evaluations'] += 1

            if success:
                self.rule_stats['successful_matches'] += 1
            else:
                self.rule_stats['failed_evaluations'] += 1

            # 更新平均评估时间
            total_evals = self.rule_stats['total_evaluations']
            current_avg = self.rule_stats['avg_evaluation_time']
            self.rule_stats['avg_evaluation_time'] = (current_avg * (total_evals - 1) + evaluation_time) / total_evals

        except Exception as e:
            logger.error(f"更新评估统计失败: {e}")

    def get_rule_statistics(self) -> Dict[str, Any]:
        """获取规则统计信息"""
        try:
            stats = {
                'total_rules': len(self.rules),
                'enabled_rules': len([r for r in self.rules.values() if r.enabled]),
                'disabled_rules': len([r for r in self.rules.values() if not r.enabled]),
                'evaluation_stats': self.rule_stats.copy(),
                'rule_usage': {}
            }

            # 规则使用统计
            for rule_id, rule in self.rules.items():
                stats['rule_usage'][rule_id] = {
                    'match_count': rule.match_count,
                    'success_count': rule.success_count,
                    'success_rate': rule.success_count / rule.match_count if rule.match_count > 0 else 0.0
                }

            return stats

        except Exception as e:
            logger.error(f"获取规则统计失败: {e}")
            return {}

    def start_monitoring(self):
        """启动规则监控"""
        try:
            if self._monitoring_active:
                return

            self._monitoring_active = True
            self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._monitor_thread.start()

            logger.info("路由规则监控已启动")

        except Exception as e:
            logger.error(f"启动规则监控失败: {e}")

    def stop_monitoring(self):
        """停止规则监控"""
        try:
            self._monitoring_active = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5)

            logger.info("路由规则监控已停止")

        except Exception as e:
            logger.error(f"停止规则监控失败: {e}")

    def _monitoring_loop(self):
        """监控循环"""
        while self._monitoring_active:
            try:
                # 清理过期缓存
                if not self._is_cache_valid():
                    self._clear_cache()

                # 检查规则性能
                self._check_rule_performance()

                # 等待下一轮检查
                threading.Event().wait(300)  # 每5分钟检查一次

            except Exception as e:
                logger.error(f"规则监控循环异常: {e}")
                threading.Event().wait(30)

    def _check_rule_performance(self):
        """检查规则性能"""
        try:
            # 检查低效规则
            for rule_id, rule in self.rules.items():
                if rule.match_count > 100:  # 足够的样本
                    success_rate = rule.success_count / rule.match_count
                    if success_rate < 0.8:  # 成功率低于80%
                        logger.warning(f"规则 {rule_id} 成功率较低: {success_rate:.2%}")

        except Exception as e:
            logger.error(f"检查规则性能失败: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            self.stop_monitoring()
            self._clear_cache()
            logger.info("路由规则管理器资源清理完成")
        except Exception as e:
            logger.error(f"资源清理失败: {e}")
