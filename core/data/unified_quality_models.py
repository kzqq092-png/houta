#!/usr/bin/env python3
"""
统一数据质量模型定义

整合所有数据质量相关的数据模型和枚举定义，确保质量指标的一致性和完整性
对标Bloomberg Terminal、Wind万得等专业软件的质量标准
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from enum import Enum
import json

class DataQuality(Enum):
    """
    数据质量等级枚举

    对标专业金融软件的质量分级标准：
    - Bloomberg Terminal: AAA/AA/A/BBB/BB/B/CCC等级
    - Wind万得: 优秀/良好/一般/较差等级
    - Refinitiv Eikon: High/Medium/Low质量等级
    """
    EXCELLENT = "excellent"     # 优秀 (>0.95) - 对标AAA级
    GOOD = "good"              # 良好 (0.85-0.95) - 对标AA级
    FAIR = "fair"              # 一般 (0.70-0.85) - 对标A级
    POOR = "poor"              # 较差 (<0.70) - 对标BBB级以下
    UNKNOWN = "unknown"        # 未知 - 未进行质量评估
    ERROR = "error"            # 错误 - 质量检查过程出错

    @classmethod
    def from_score(cls, score: float) -> 'DataQuality':
        """根据评分确定质量等级"""
        if score < 0:
            return cls.ERROR
        elif score >= 0.95:
            return cls.EXCELLENT
        elif score >= 0.85:
            return cls.GOOD
        elif score >= 0.70:
            return cls.FAIR
        else:
            return cls.POOR

    def get_score_range(self) -> tuple:
        """获取质量等级对应的评分范围"""
        ranges = {
            self.EXCELLENT: (0.95, 1.0),
            self.GOOD: (0.85, 0.95),
            self.FAIR: (0.70, 0.85),
            self.POOR: (0.0, 0.70),
            self.UNKNOWN: (0.0, 0.0),
            self.ERROR: (-1.0, -1.0)
        }
        return ranges.get(self, (0.0, 0.0))

    def get_color_code(self) -> str:
        """获取质量等级对应的颜色代码（用于UI显示）"""
        colors = {
            self.EXCELLENT: "#28a745",  # 绿色
            self.GOOD: "#17a2b8",       # 蓝色
            self.FAIR: "#ffc107",       # 黄色
            self.POOR: "#dc3545",       # 红色
            self.UNKNOWN: "#6c757d",    # 灰色
            self.ERROR: "#343a40"       # 深灰色
        }
        return colors.get(self, "#6c757d")

    def get_description(self) -> str:
        """获取质量等级描述"""
        descriptions = {
            self.EXCELLENT: "数据质量优秀，可直接用于关键业务决策",
            self.GOOD: "数据质量良好，适合大多数分析场景",
            self.FAIR: "数据质量一般，建议谨慎使用并进行额外验证",
            self.POOR: "数据质量较差，不建议用于重要分析",
            self.UNKNOWN: "数据质量未知，需要进行质量评估",
            self.ERROR: "质量检查过程出错，无法确定数据质量"
        }
        return descriptions.get(self, "未知质量等级")

class QualityDimension(Enum):
    """质量维度枚举"""
    COMPLETENESS = "completeness"       # 完整性
    ACCURACY = "accuracy"              # 准确性
    CONSISTENCY = "consistency"        # 一致性
    TIMELINESS = "timeliness"         # 及时性
    VALIDITY = "validity"             # 有效性
    UNIQUENESS = "uniqueness"         # 唯一性
    INTEGRITY = "integrity"           # 完整性（引用完整性）
    CONFORMITY = "conformity"         # 符合性

class QualityCheckStatus(Enum):
    """质量检查状态"""
    PENDING = "pending"               # 待检查
    RUNNING = "running"               # 检查中
    COMPLETED = "completed"           # 已完成
    FAILED = "failed"                # 检查失败
    SKIPPED = "skipped"              # 已跳过

class QualityIssueLevel(Enum):
    """质量问题级别"""
    CRITICAL = "critical"             # 严重问题 - 影响数据基本可用性
    HIGH = "high"                    # 高级问题 - 影响数据准确性
    MEDIUM = "medium"                # 中级问题 - 影响数据质量
    LOW = "low"                      # 低级问题 - 轻微影响
    INFO = "info"                    # 信息提示 - 仅供参考

    def get_priority_score(self) -> int:
        """获取优先级评分（用于排序）"""
        scores = {
            self.CRITICAL: 5,
            self.HIGH: 4,
            self.MEDIUM: 3,
            self.LOW: 2,
            self.INFO: 1
        }
        return scores.get(self, 0)

@dataclass
class QualityDimensionScore:
    """质量维度评分"""
    dimension: QualityDimension
    score: float                      # 0.0-1.0
    weight: float = 1.0              # 权重
    status: QualityCheckStatus = QualityCheckStatus.PENDING
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    check_time: datetime = field(default_factory=datetime.now)

    @property
    def weighted_score(self) -> float:
        """加权评分"""
        return self.score * self.weight

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'dimension': self.dimension.value,
            'score': self.score,
            'weight': self.weight,
            'status': self.status.value,
            'message': self.message,
            'details': self.details,
            'check_time': self.check_time.isoformat(),
            'weighted_score': self.weighted_score
        }

@dataclass
class QualityIssue:
    """质量问题详情"""
    issue_id: str
    dimension: QualityDimension
    level: QualityIssueLevel
    title: str
    description: str
    field_name: Optional[str] = None
    record_count: int = 0
    percentage: float = 0.0
    recommendation: Optional[str] = None
    fix_suggestion: Optional[str] = None
    impact_assessment: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    is_resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'issue_id': self.issue_id,
            'dimension': self.dimension.value,
            'level': self.level.value,
            'title': self.title,
            'description': self.description,
            'field_name': self.field_name,
            'record_count': self.record_count,
            'percentage': self.percentage,
            'recommendation': self.recommendation,
            'fix_suggestion': self.fix_suggestion,
            'impact_assessment': self.impact_assessment,
            'created_at': self.created_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'is_resolved': self.is_resolved,
            'priority_score': self.level.get_priority_score()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QualityIssue':
        """从字典创建"""
        return cls(
            issue_id=data['issue_id'],
            dimension=QualityDimension(data['dimension']),
            level=QualityIssueLevel(data['level']),
            title=data['title'],
            description=data['description'],
            field_name=data.get('field_name'),
            record_count=data.get('record_count', 0),
            percentage=data.get('percentage', 0.0),
            recommendation=data.get('recommendation'),
            fix_suggestion=data.get('fix_suggestion'),
            impact_assessment=data.get('impact_assessment'),
            created_at=datetime.fromisoformat(data['created_at']),
            resolved_at=datetime.fromisoformat(data['resolved_at']) if data.get('resolved_at') else None,
            is_resolved=data.get('is_resolved', False)
        )

@dataclass
class UnifiedDataQualityMetrics:
    """
    统一数据质量指标模型

    整合所有质量相关指标，提供完整的质量评估结果
    对标专业金融软件的质量报告格式
    """
    # 基本信息
    data_source: str                    # 数据源名称
    table_name: str                     # 表名
    schema_name: Optional[str] = None   # 模式名
    metric_date: date = field(default_factory=date.today)

    # 数据统计
    total_records: int = 0              # 总记录数
    total_fields: int = 0               # 总字段数
    null_records: int = 0               # 空值记录数
    duplicate_records: int = 0          # 重复记录数
    invalid_records: int = 0            # 无效记录数

    # 维度评分
    dimension_scores: Dict[QualityDimension, QualityDimensionScore] = field(default_factory=dict)

    # 综合评分
    overall_score: Decimal = Decimal('0.0')    # 综合评分 (0.0-1.0)
    quality_level: DataQuality = DataQuality.UNKNOWN

    # 质量问题
    issues: List[QualityIssue] = field(default_factory=list)

    # 统计汇总
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    info_issues: int = 0

    # 趋势信息
    previous_score: Optional[Decimal] = None
    score_trend: Optional[str] = None   # "improving", "declining", "stable"

    # 建议和行动项
    recommendations: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)

    # 元数据
    check_timestamp: datetime = field(default_factory=datetime.now)
    check_duration: float = 0.0         # 检查耗时（秒）
    checker_version: str = "1.0"        # 检查器版本
    rule_version: str = "1.0"           # 规则版本

    def __post_init__(self):
        """后处理初始化"""
        self._update_issue_counts()
        self._calculate_overall_score()
        self._determine_quality_level()
        self._calculate_trend()

    def _update_issue_counts(self):
        """更新问题统计"""
        self.critical_issues = sum(1 for issue in self.issues if issue.level == QualityIssueLevel.CRITICAL)
        self.high_issues = sum(1 for issue in self.issues if issue.level == QualityIssueLevel.HIGH)
        self.medium_issues = sum(1 for issue in self.issues if issue.level == QualityIssueLevel.MEDIUM)
        self.low_issues = sum(1 for issue in self.issues if issue.level == QualityIssueLevel.LOW)
        self.info_issues = sum(1 for issue in self.issues if issue.level == QualityIssueLevel.INFO)

    def _calculate_overall_score(self):
        """计算综合评分"""
        if not self.dimension_scores:
            self.overall_score = Decimal('0.0')
            return

        total_weighted_score = Decimal('0.0')
        total_weight = Decimal('0.0')

        for score_info in self.dimension_scores.values():
            if score_info.status == QualityCheckStatus.COMPLETED:
                total_weighted_score += Decimal(str(score_info.weighted_score))
                total_weight += Decimal(str(score_info.weight))

        if total_weight > 0:
            self.overall_score = total_weighted_score / total_weight
        else:
            self.overall_score = Decimal('0.0')

    def _determine_quality_level(self):
        """确定质量等级"""
        self.quality_level = DataQuality.from_score(float(self.overall_score))

    def _calculate_trend(self):
        """计算趋势"""
        if self.previous_score is not None:
            diff = self.overall_score - self.previous_score
            if abs(diff) < Decimal('0.01'):  # 差异小于1%认为稳定
                self.score_trend = "stable"
            elif diff > 0:
                self.score_trend = "improving"
            else:
                self.score_trend = "declining"

    def add_dimension_score(self, dimension: QualityDimension, score: float,
                            weight: float = 1.0, message: str = "",
                            details: Optional[Dict[str, Any]] = None):
        """添加维度评分"""
        dimension_score = QualityDimensionScore(
            dimension=dimension,
            score=score,
            weight=weight,
            status=QualityCheckStatus.COMPLETED,
            message=message,
            details=details or {}
        )
        self.dimension_scores[dimension] = dimension_score
        self._calculate_overall_score()
        self._determine_quality_level()

    def add_issue(self, issue: QualityIssue):
        """添加质量问题"""
        self.issues.append(issue)
        self._update_issue_counts()

    def get_issues_by_level(self, level: QualityIssueLevel) -> List[QualityIssue]:
        """根据级别获取问题列表"""
        return [issue for issue in self.issues if issue.level == level]

    def get_issues_by_dimension(self, dimension: QualityDimension) -> List[QualityIssue]:
        """根据维度获取问题列表"""
        return [issue for issue in self.issues if issue.dimension == dimension]

    def get_critical_issues(self) -> List[QualityIssue]:
        """获取严重问题列表"""
        return self.get_issues_by_level(QualityIssueLevel.CRITICAL)

    def get_high_priority_issues(self) -> List[QualityIssue]:
        """获取高优先级问题列表"""
        return [issue for issue in self.issues
                if issue.level in [QualityIssueLevel.CRITICAL, QualityIssueLevel.HIGH]]

    def get_unresolved_issues(self) -> List[QualityIssue]:
        """获取未解决问题列表"""
        return [issue for issue in self.issues if not issue.is_resolved]

    def resolve_issue(self, issue_id: str):
        """标记问题为已解决"""
        for issue in self.issues:
            if issue.issue_id == issue_id:
                issue.is_resolved = True
                issue.resolved_at = datetime.now()
                break

    def get_summary(self) -> Dict[str, Any]:
        """获取质量摘要"""
        return {
            'data_source': self.data_source,
            'table_name': self.table_name,
            'total_records': self.total_records,
            'overall_score': float(self.overall_score),
            'quality_level': self.quality_level.value,
            'quality_description': self.quality_level.get_description(),
            'issues_summary': {
                'total': len(self.issues),
                'critical': self.critical_issues,
                'high': self.high_issues,
                'medium': self.medium_issues,
                'low': self.low_issues,
                'info': self.info_issues,
                'unresolved': len(self.get_unresolved_issues())
            },
            'dimension_scores': {
                dim.value: score.score for dim, score in self.dimension_scores.items()
            },
            'trend': self.score_trend,
            'check_timestamp': self.check_timestamp.isoformat(),
            'recommendations_count': len(self.recommendations)
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为完整字典"""
        return {
            'data_source': self.data_source,
            'table_name': self.table_name,
            'schema_name': self.schema_name,
            'metric_date': self.metric_date.isoformat(),
            'total_records': self.total_records,
            'total_fields': self.total_fields,
            'null_records': self.null_records,
            'duplicate_records': self.duplicate_records,
            'invalid_records': self.invalid_records,
            'dimension_scores': {
                dim.value: score.to_dict() for dim, score in self.dimension_scores.items()
            },
            'overall_score': float(self.overall_score),
            'quality_level': self.quality_level.value,
            'issues': [issue.to_dict() for issue in self.issues],
            'critical_issues': self.critical_issues,
            'high_issues': self.high_issues,
            'medium_issues': self.medium_issues,
            'low_issues': self.low_issues,
            'info_issues': self.info_issues,
            'previous_score': float(self.previous_score) if self.previous_score else None,
            'score_trend': self.score_trend,
            'recommendations': self.recommendations,
            'action_items': self.action_items,
            'check_timestamp': self.check_timestamp.isoformat(),
            'check_duration': self.check_duration,
            'checker_version': self.checker_version,
            'rule_version': self.rule_version
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedDataQualityMetrics':
        """从字典创建"""
        # 创建基本对象
        metrics = cls(
            data_source=data['data_source'],
            table_name=data['table_name'],
            schema_name=data.get('schema_name'),
            metric_date=date.fromisoformat(data['metric_date']),
            total_records=data.get('total_records', 0),
            total_fields=data.get('total_fields', 0),
            null_records=data.get('null_records', 0),
            duplicate_records=data.get('duplicate_records', 0),
            invalid_records=data.get('invalid_records', 0),
            overall_score=Decimal(str(data.get('overall_score', 0.0))),
            quality_level=DataQuality(data.get('quality_level', 'unknown')),
            previous_score=Decimal(str(data['previous_score'])) if data.get('previous_score') else None,
            score_trend=data.get('score_trend'),
            recommendations=data.get('recommendations', []),
            action_items=data.get('action_items', []),
            check_timestamp=datetime.fromisoformat(data.get('check_timestamp', datetime.now().isoformat())),
            check_duration=data.get('check_duration', 0.0),
            checker_version=data.get('checker_version', '1.0'),
            rule_version=data.get('rule_version', '1.0')
        )

        # 恢复维度评分
        dimension_scores_data = data.get('dimension_scores', {})
        for dim_name, score_data in dimension_scores_data.items():
            dimension = QualityDimension(dim_name)
            score_info = QualityDimensionScore(
                dimension=dimension,
                score=score_data['score'],
                weight=score_data.get('weight', 1.0),
                status=QualityCheckStatus(score_data.get('status', 'completed')),
                message=score_data.get('message', ''),
                details=score_data.get('details', {}),
                check_time=datetime.fromisoformat(score_data.get('check_time', datetime.now().isoformat()))
            )
            metrics.dimension_scores[dimension] = score_info

        # 恢复问题列表
        issues_data = data.get('issues', [])
        for issue_data in issues_data:
            issue = QualityIssue.from_dict(issue_data)
            metrics.issues.append(issue)

        # 更新统计
        metrics._update_issue_counts()

        return metrics

    @classmethod
    def from_json(cls, json_str: str) -> 'UnifiedDataQualityMetrics':
        """从JSON字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)

@dataclass
class QualityBenchmark:
    """质量基准"""
    name: str
    description: str
    dimension: QualityDimension
    target_score: float             # 目标评分
    minimum_score: float            # 最低评分
    weight: float = 1.0            # 权重
    industry_standard: Optional[str] = None  # 行业标准
    created_at: datetime = field(default_factory=datetime.now)

    def is_met(self, score: float) -> bool:
        """检查是否达到基准"""
        return score >= self.target_score

    def is_acceptable(self, score: float) -> bool:
        """检查是否可接受"""
        return score >= self.minimum_score

@dataclass
class QualityProfile:
    """质量配置文件"""
    profile_name: str
    description: str
    data_type: str                  # 数据类型 (kline, fundamental, etc.)
    benchmarks: List[QualityBenchmark] = field(default_factory=list)
    dimension_weights: Dict[QualityDimension, float] = field(default_factory=dict)
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def get_dimension_weight(self, dimension: QualityDimension) -> float:
        """获取维度权重"""
        return self.dimension_weights.get(dimension, 1.0)

    def add_benchmark(self, benchmark: QualityBenchmark):
        """添加基准"""
        self.benchmarks.append(benchmark)
        self.updated_at = datetime.now()

    def get_benchmarks_by_dimension(self, dimension: QualityDimension) -> List[QualityBenchmark]:
        """根据维度获取基准"""
        return [b for b in self.benchmarks if b.dimension == dimension]

# 预定义质量配置文件
def get_default_quality_profiles() -> Dict[str, QualityProfile]:
    """获取默认质量配置文件"""
    profiles = {}

    # K线数据质量配置
    kline_profile = QualityProfile(
        profile_name="kline_data_quality",
        description="K线数据质量标准配置",
        data_type="kline",
        dimension_weights={
            QualityDimension.COMPLETENESS: 0.25,
            QualityDimension.ACCURACY: 0.25,
            QualityDimension.CONSISTENCY: 0.20,
            QualityDimension.TIMELINESS: 0.15,
            QualityDimension.VALIDITY: 0.10,
            QualityDimension.UNIQUENESS: 0.05
        }
    )

    # 添加K线数据基准
    kline_profile.add_benchmark(QualityBenchmark(
        name="completeness_benchmark",
        description="K线数据完整性基准",
        dimension=QualityDimension.COMPLETENESS,
        target_score=0.95,
        minimum_score=0.90,
        industry_standard="Bloomberg Terminal"
    ))

    kline_profile.add_benchmark(QualityBenchmark(
        name="accuracy_benchmark",
        description="K线数据准确性基准",
        dimension=QualityDimension.ACCURACY,
        target_score=0.98,
        minimum_score=0.95,
        industry_standard="Wind万得"
    ))

    profiles["kline"] = kline_profile

    # 基本面数据质量配置
    fundamental_profile = QualityProfile(
        profile_name="fundamental_data_quality",
        description="基本面数据质量标准配置",
        data_type="fundamental",
        dimension_weights={
            QualityDimension.COMPLETENESS: 0.20,
            QualityDimension.ACCURACY: 0.30,
            QualityDimension.CONSISTENCY: 0.25,
            QualityDimension.TIMELINESS: 0.15,
            QualityDimension.VALIDITY: 0.10
        }
    )

    profiles["fundamental"] = fundamental_profile

    # 实时行情数据质量配置
    realtime_profile = QualityProfile(
        profile_name="realtime_data_quality",
        description="实时行情数据质量标准配置",
        data_type="realtime",
        dimension_weights={
            QualityDimension.TIMELINESS: 0.35,
            QualityDimension.ACCURACY: 0.25,
            QualityDimension.COMPLETENESS: 0.20,
            QualityDimension.VALIDITY: 0.15,
            QualityDimension.CONSISTENCY: 0.05
        }
    )

    profiles["realtime"] = realtime_profile

    return profiles

# 兼容性别名（保持向后兼容）
DataQualityMetrics = UnifiedDataQualityMetrics
