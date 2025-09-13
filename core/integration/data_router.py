from loguru import logger
"""
数据路由器

智能选择数据存储后端（SQLite vs DuckDB）
基于数据类型、查询模式、数据量等因素进行路由决策
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import pandas as pd

logger = logger


class StorageBackend(Enum):
    """存储后端类型"""
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    AUTO = "auto"


@dataclass
class RoutingRule:
    """路由规则"""
    data_type: str
    backend: StorageBackend
    conditions: Optional[Dict[str, Any]] = None
    priority: int = 0
    description: str = ""


class DataRouter:
    """
    数据路由器

    根据数据类型、查询模式、数据量等因素智能选择存储后端
    """

    def __init__(self):
        self.logger = logger
        self.routing_rules: List[RoutingRule] = []
        self._setup_default_rules()

    def _setup_default_rules(self):
        """设置默认路由规则"""
        self.routing_rules = [
            # 配置和元数据 -> SQLite
            RoutingRule(
                data_type="config",
                backend=StorageBackend.SQLITE,
                priority=10,
                description="系统配置数据使用SQLite"
            ),
            RoutingRule(
                data_type="user_settings",
                backend=StorageBackend.SQLITE,
                priority=10,
                description="用户设置数据使用SQLite"
            ),
            RoutingRule(
                data_type="plugin_metadata",
                backend=StorageBackend.SQLITE,
                priority=10,
                description="插件元数据使用SQLite"
            ),
            RoutingRule(
                data_type="system_logs",
                backend=StorageBackend.SQLITE,
                priority=10,
                description="系统日志使用SQLite"
            ),

            # 大数据分析 -> DuckDB
            RoutingRule(
                data_type="kline_data",
                backend=StorageBackend.DUCKDB,
                conditions={"row_count": {">": 1000}},
                priority=10,
                description="大量K线数据使用DuckDB"
            ),
            RoutingRule(
                data_type="technical_indicators",
                backend=StorageBackend.DUCKDB,
                priority=10,
                description="技术指标数据使用DuckDB"
            ),
            RoutingRule(
                data_type="backtest_results",
                backend=StorageBackend.DUCKDB,
                priority=10,
                description="回测结果使用DuckDB"
            ),
            RoutingRule(
                data_type="financial_statements",
                backend=StorageBackend.DUCKDB,
                priority=10,
                description="财务报表数据使用DuckDB"
            ),
            RoutingRule(
                data_type="macro_economic",
                backend=StorageBackend.DUCKDB,
                priority=10,
                description="宏观经济数据使用DuckDB"
            ),

            # 小数据查询 -> SQLite
            RoutingRule(
                data_type="kline_data",
                backend=StorageBackend.SQLITE,
                conditions={"row_count": {"<=": 1000}},
                priority=5,
                description="少量K线数据使用SQLite"
            ),
            RoutingRule(
                data_type="stock_info",
                backend=StorageBackend.SQLITE,
                priority=8,
                description="股票基本信息使用SQLite"
            ),

            # 实时数据 -> SQLite（快速读写）
            RoutingRule(
                data_type="realtime_data",
                backend=StorageBackend.SQLITE,
                conditions={"is_realtime": True},
                priority=9,
                description="实时数据使用SQLite"
            ),
        ]

    def route(self, data_type: str, **query_params) -> StorageBackend:
        """
        路由决策

        Args:
            data_type: 数据类型
            **query_params: 查询参数

        Returns:
            选择的存储后端
        """
        try:
            # 获取适用的规则
            applicable_rules = [
                rule for rule in self.routing_rules
                if rule.data_type == data_type
            ]

            if not applicable_rules:
                self.logger.warning(f"未找到数据类型 {data_type} 的路由规则，使用默认SQLite")
                return StorageBackend.SQLITE

            # 按优先级排序并检查条件
            for rule in sorted(applicable_rules, key=lambda x: x.priority, reverse=True):
                if self._check_conditions(rule.conditions, query_params):
                    self.logger.debug(f"路由决策: {data_type} -> {rule.backend.value} ({rule.description})")
                    return rule.backend

            # 如果没有规则匹配，使用第一个规则的后端
            default_backend = applicable_rules[0].backend
            self.logger.debug(f"使用默认路由: {data_type} -> {default_backend.value}")
            return default_backend

        except Exception as e:
            self.logger.error(f"路由决策失败: {e}")
            return StorageBackend.SQLITE  # 安全回退

    def _check_conditions(self, conditions: Optional[Dict], params: Dict) -> bool:
        """
        检查路由条件是否满足

        Args:
            conditions: 条件字典
            params: 参数字典

        Returns:
            条件是否满足
        """
        if not conditions:
            return True

        try:
            for key, condition in conditions.items():
                if key not in params:
                    return False

                value = params[key]

                if isinstance(condition, dict):
                    # 支持操作符条件
                    for op, threshold in condition.items():
                        if op == "<" and value >= threshold:
                            return False
                        elif op == "<=" and value > threshold:
                            return False
                        elif op == ">" and value <= threshold:
                            return False
                        elif op == ">=" and value < threshold:
                            return False
                        elif op == "==" and value != threshold:
                            return False
                        elif op == "!=" and value == threshold:
                            return False
                elif isinstance(condition, bool):
                    # 布尔条件
                    if value != condition:
                        return False
                else:
                    # 直接值比较
                    if value != condition:
                        return False

            return True

        except Exception as e:
            self.logger.error(f"条件检查失败: {e}")
            return False

    def add_rule(self, rule: RoutingRule):
        """添加路由规则"""
        self.routing_rules.append(rule)
        self.logger.info(f"添加路由规则: {rule.data_type} -> {rule.backend.value}")

    def remove_rule(self, data_type: str, backend: StorageBackend):
        """移除路由规则"""
        self.routing_rules = [
            rule for rule in self.routing_rules
            if not (rule.data_type == data_type and rule.backend == backend)
        ]
        self.logger.info(f"移除路由规则: {data_type} -> {backend.value}")

    def get_rules(self, data_type: str = None) -> List[RoutingRule]:
        """获取路由规则"""
        if data_type:
            return [rule for rule in self.routing_rules if rule.data_type == data_type]
        return self.routing_rules.copy()

    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        stats = {
            "total_rules": len(self.routing_rules),
            "rules_by_backend": {},
            "rules_by_data_type": {}
        }

        # 按后端统计
        for backend in StorageBackend:
            count = len([rule for rule in self.routing_rules if rule.backend == backend])
            stats["rules_by_backend"][backend.value] = count

        # 按数据类型统计
        data_types = set(rule.data_type for rule in self.routing_rules)
        for data_type in data_types:
            count = len([rule for rule in self.routing_rules if rule.data_type == data_type])
            stats["rules_by_data_type"][data_type] = count

        return stats


class QueryOptimizer:
    """查询优化器 - 基于查询模式优化路由决策"""

    def __init__(self, data_router: DataRouter):
        self.data_router = data_router
        self.query_history: List[Dict[str, Any]] = []
        self.max_history = 1000

    def optimize_query(self, data_type: str, query_params: Dict[str, Any]) -> StorageBackend:
        """
        优化查询路由

        Args:
            data_type: 数据类型
            query_params: 查询参数

        Returns:
            优化后的存储后端选择
        """
        # 记录查询历史
        self._record_query(data_type, query_params)

        # 基础路由决策
        backend = self.data_router.route(data_type, **query_params)

        # 基于历史模式的优化
        optimized_backend = self._optimize_based_on_history(data_type, query_params, backend)

        return optimized_backend

    def _record_query(self, data_type: str, query_params: Dict[str, Any]):
        """记录查询历史"""
        query_record = {
            "timestamp": pd.Timestamp.now(),
            "data_type": data_type,
            "params": query_params.copy()
        }

        self.query_history.append(query_record)

        # 保持历史记录在限制范围内
        if len(self.query_history) > self.max_history:
            self.query_history = self.query_history[-self.max_history:]

    def _optimize_based_on_history(self, data_type: str, query_params: Dict[str, Any],
                                   default_backend: StorageBackend) -> StorageBackend:
        """基于历史模式优化路由决策"""
        try:
            # 分析最近的查询模式
            recent_queries = [
                q for q in self.query_history[-100:]  # 最近100个查询
                if q["data_type"] == data_type
            ]

            if len(recent_queries) < 10:
                return default_backend

            # 分析查询规模趋势
            row_counts = [q["params"].get("row_count", 0) for q in recent_queries]
            avg_row_count = sum(row_counts) / len(row_counts) if row_counts else 0

            # 如果平均查询规模较大，倾向于使用DuckDB
            if avg_row_count > 5000 and default_backend == StorageBackend.SQLITE:
                return StorageBackend.DUCKDB

            # 如果平均查询规模较小，倾向于使用SQLite
            if avg_row_count < 500 and default_backend == StorageBackend.DUCKDB:
                return StorageBackend.SQLITE

            return default_backend

        except Exception as e:
            logger.error(f"基于历史的优化失败: {e}")
            return default_backend

    def get_query_patterns(self) -> Dict[str, Any]:
        """获取查询模式分析"""
        if not self.query_history:
            return {"message": "暂无查询历史"}

        patterns = {
            "total_queries": len(self.query_history),
            "data_types": {},
            "avg_row_counts": {},
            "query_frequency": {}
        }

        # 按数据类型分析
        for query in self.query_history:
            data_type = query["data_type"]

            if data_type not in patterns["data_types"]:
                patterns["data_types"][data_type] = 0
                patterns["avg_row_counts"][data_type] = []

            patterns["data_types"][data_type] += 1

            row_count = query["params"].get("row_count", 0)
            if row_count > 0:
                patterns["avg_row_counts"][data_type].append(row_count)

        # 计算平均行数
        for data_type, row_counts in patterns["avg_row_counts"].items():
            if row_counts:
                patterns["avg_row_counts"][data_type] = sum(row_counts) / len(row_counts)
            else:
                patterns["avg_row_counts"][data_type] = 0

        return patterns
