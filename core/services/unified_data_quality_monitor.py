#!/usr/bin/env python3
"""
统一数据质量监控器

整合所有现有的DataQualityMonitor实现，提供统一的数据质量检测、评估和监控服务
对标Bloomberg Terminal、Wind万得等专业软件的数据质量标准
"""

import sqlite3
import pandas as pd
import numpy as np
import threading
import time
import json
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from pathlib import Path
from enum import Enum
from loguru import logger

# 导入相关模块
from ..data.unified_quality_models import (
    DataQuality, QualityDimension, QualityCheckStatus, QualityIssueLevel,
    UnifiedDataQualityMetrics, QualityIssue, QualityDimensionScore,
    QualityProfile, get_default_quality_profiles
)
from ..data_validator import ValidationLevel, ValidationResult
from ..importdata.task_status_manager import TaskStatus, get_task_status_manager


# 使用统一模型中的枚举
QualityCheckType = QualityDimension  # 兼容性别名


# 使用统一模型中的数据结构
@dataclass
class QualityCheckResult:
    """质量检查结果"""
    check_type: QualityCheckType
    score: float                      # 0.0-1.0
    passed: bool
    issues: List[QualityIssue] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


# 使用统一质量报告
UnifiedQualityReport = UnifiedDataQualityMetrics


class QualityRuleEngine:
    """质量规则引擎"""

    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {}
        self._load_default_rules()

    def _load_default_rules(self):
        """加载默认质量规则"""
        # K线数据规则
        self.rules['kline'] = {
            'required_columns': ['open', 'high', 'low', 'close', 'volume'],
            'numeric_columns': ['open', 'high', 'low', 'close', 'volume', 'amount'],
            'price_range': {'min': 0.01, 'max': 10000},
            'volume_range': {'min': 0, 'max': 1e12},
            'ohlc_logic': True,  # open <= high, low <= close等逻辑检查
            'date_format': '%Y-%m-%d',
            'completeness_threshold': 0.95,
            'accuracy_threshold': 0.90
        }

        # 基本面数据规则
        self.rules['fundamental'] = {
            'required_columns': ['symbol', 'report_date', 'total_revenue'],
            'numeric_columns': ['total_revenue', 'net_income', 'total_assets'],
            'date_columns': ['report_date', 'announce_date'],
            'completeness_threshold': 0.85,
            'accuracy_threshold': 0.90
        }

        # 实时行情规则
        self.rules['realtime'] = {
            'required_columns': ['symbol', 'price', 'volume', 'timestamp'],
            'numeric_columns': ['price', 'volume', 'change', 'change_pct'],
            'timeliness_threshold': 300,  # 5分钟内
            'completeness_threshold': 0.98,
            'accuracy_threshold': 0.95
        }

    def get_rules(self, data_type: str) -> Dict[str, Any]:
        """获取数据类型对应的规则"""
        return self.rules.get(data_type, self.rules.get('kline', {}))

    def add_custom_rule(self, data_type: str, rule_name: str, rule_config: Dict[str, Any]):
        """添加自定义规则"""
        if data_type not in self.rules:
            self.rules[data_type] = {}
        self.rules[data_type][rule_name] = rule_config


class UnifiedDataQualityMonitor:
    """
    统一数据质量监控器

    功能特性：
    1. 统一的质量检测标准和评估指标
    2. 多维度数据质量检查（完整性、准确性、一致性、及时性等）
    3. 智能质量规则引擎
    4. 实时质量监控和告警
    5. 质量趋势分析和报告
    6. 自动质量修复建议
    7. 与专业软件对标的质量标准
    """

    def __init__(self, db_path: Optional[str] = None, enable_persistence: bool = True,
                 enable_real_time_monitoring: bool = True):
        """
        初始化统一数据质量监控器

        Args:
            db_path: 数据库路径
            enable_persistence: 是否启用持久化
            enable_real_time_monitoring: 是否启用实时监控
        """
        # 数据库配置
        self.db_path = Path(db_path or "data/unified_quality_monitor.sqlite")
        self.enable_persistence = enable_persistence
        self._db_lock = threading.Lock()

        # 质量规则引擎
        self.rule_engine = QualityRuleEngine()

        # 监控配置
        self.enable_real_time_monitoring = enable_real_time_monitoring
        self._monitoring_active = False
        self._monitoring_thread = None
        self._monitoring_lock = threading.Lock()

        # 质量检查器注册表
        self._quality_checkers: Dict[QualityCheckType, Callable] = {
            QualityCheckType.COMPLETENESS: self._check_completeness,
            QualityCheckType.ACCURACY: self._check_accuracy,
            QualityCheckType.CONSISTENCY: self._check_consistency,
            QualityCheckType.TIMELINESS: self._check_timeliness,
            QualityCheckType.VALIDITY: self._check_validity,
            QualityCheckType.UNIQUENESS: self._check_uniqueness,
            QualityCheckType.INTEGRITY: self._check_integrity,
            QualityCheckType.CONFORMITY: self._check_conformity
        }

        # 质量监听器
        self._quality_listeners: List[Callable[[UnifiedQualityReport], None]] = []
        self._listener_lock = threading.Lock()

        # 质量缓存
        self._quality_cache: Dict[str, UnifiedQualityReport] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 300  # 5分钟缓存

        # 统计信息
        self._stats = {
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0,
            'critical_issues_found': 0,
            'average_score': 0.0
        }

        # 初始化数据库
        if self.enable_persistence:
            self._init_database()

        # 获取任务状态管理器
        self.task_status_manager = get_task_status_manager()

        logger.info(f"统一数据质量监控器初始化完成 - 持久化: {'启用' if enable_persistence else '禁用'}")

    def _init_database(self):
        """初始化数据库"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                # 质量报告表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS quality_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_source TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        check_timestamp TIMESTAMP NOT NULL,
                        total_records INTEGER NOT NULL,
                        overall_score REAL NOT NULL,
                        quality_level TEXT NOT NULL,
                        null_records INTEGER DEFAULT 0,
                        duplicate_records INTEGER DEFAULT 0,
                        invalid_records INTEGER DEFAULT 0,
                        critical_issues INTEGER DEFAULT 0,
                        high_issues INTEGER DEFAULT 0,
                        medium_issues INTEGER DEFAULT 0,
                        low_issues INTEGER DEFAULT 0,
                        check_results TEXT,  -- JSON格式存储检查结果
                        recommendations TEXT,  -- JSON格式存储建议
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 质量问题表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS quality_issues (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_id INTEGER NOT NULL,
                        check_type TEXT NOT NULL,
                        issue_level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        field_name TEXT,
                        record_count INTEGER DEFAULT 0,
                        percentage REAL DEFAULT 0.0,
                        recommendation TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (report_id) REFERENCES quality_reports (id)
                    )
                """)

                # 质量趋势表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS quality_trends (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_source TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        metric_date DATE NOT NULL,
                        avg_score REAL NOT NULL,
                        check_count INTEGER NOT NULL,
                        issue_count INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(data_source, table_name, metric_date)
                    )
                """)

                # 创建索引
                conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_source_table ON quality_reports(data_source, table_name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_timestamp ON quality_reports(check_timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_report ON quality_issues(report_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trends_source_date ON quality_trends(data_source, metric_date)")

                conn.commit()

            logger.info(f"质量监控数据库初始化完成: {self.db_path}")

        except Exception as e:
            logger.error(f"初始化质量监控数据库失败: {e}")
            self.enable_persistence = False

    def check_data_quality(self, data: pd.DataFrame, data_source: str,
                           table_name: str, data_type: str = "kline",
                           custom_rules: Optional[Dict[str, Any]] = None) -> UnifiedDataQualityMetrics:
        """
        执行完整的数据质量检查

        Args:
            data: 待检查的数据
            data_source: 数据源名称
            table_name: 表名
            data_type: 数据类型
            custom_rules: 自定义规则

        Returns:
            UnifiedQualityReport: 统一质量报告
        """
        start_time = time.time()

        try:
            logger.info(f"开始数据质量检查: {data_source}.{table_name} ({len(data)} 条记录)")

            # 创建质量报告
            report = UnifiedDataQualityMetrics(
                data_source=data_source,
                table_name=table_name,
                check_timestamp=datetime.now(),
                total_records=len(data)
            )

            # 获取质量规则
            rules = self.rule_engine.get_rules(data_type)
            if custom_rules:
                rules.update(custom_rules)

            # 执行各项质量检查
            for check_type, checker_func in self._quality_checkers.items():
                try:
                    check_result = checker_func(data, rules, data_type)
                    report.check_results[check_type] = check_result

                    # 添加问题到报告
                    for issue in check_result.issues:
                        report.add_issue(issue)

                except Exception as e:
                    logger.error(f"质量检查失败 {check_type.value}: {e}")
                    # 创建错误检查结果
                    error_issue = QualityIssue(
                        issue_id=f"error_{check_type.value}_{int(time.time())}",
                        dimension=check_type,
                        level=QualityIssueLevel.CRITICAL,
                        title="质量检查错误",
                        description=f"检查过程出错: {str(e)}"
                    )

                    error_result = QualityCheckResult(
                        check_type=check_type,
                        score=0.0,
                        passed=False,
                        issues=[error_issue]
                    )
                    report.check_results[check_type] = error_result
                    report.add_issue(error_issue)

            # 添加维度评分到报告
            for check_type, result in report.check_results.items():
                report.add_dimension_score(
                    dimension=check_type,
                    score=result.score,
                    message=f"{check_type.value}检查完成",
                    details=result.details
                )

            # 统计基础信息
            report.null_records = data.isnull().sum().sum()
            report.duplicate_records = data.duplicated().sum()

            # 生成建议
            report.recommendations = self._generate_recommendations(report)

            # 更新统计
            self._update_stats(report)

            # 保存报告
            if self.enable_persistence:
                self._save_quality_report(report)

            # 缓存报告
            cache_key = f"{data_source}_{table_name}_{int(time.time() // self._cache_ttl)}"
            with self._cache_lock:
                self._quality_cache[cache_key] = report

            # 通知监听器
            self._notify_quality_listeners(report)

            execution_time = time.time() - start_time
            logger.info(f"数据质量检查完成: {data_source}.{table_name}, "
                        f"评分: {report.overall_score:.3f}, "
                        f"等级: {report.quality_level.value}, "
                        f"耗时: {execution_time:.2f}s")

            return report

        except Exception as e:
            logger.error(f"数据质量检查失败: {e}")
            # 返回错误报告
            error_report = UnifiedDataQualityMetrics(
                data_source=data_source,
                table_name=table_name,
                check_timestamp=datetime.now(),
                total_records=len(data) if data is not None else 0
            )
            error_report.recommendations = [f"质量检查过程出错: {str(e)}"]
            return error_report

    # ==================== 质量检查器实现 ====================

    def _check_completeness(self, data: pd.DataFrame, rules: Dict[str, Any],
                            data_type: str) -> QualityCheckResult:
        """检查数据完整性"""
        issues = []
        details = {}

        if data.empty:
            return QualityCheckResult(
                check_type=QualityCheckType.COMPLETENESS,
                score=0.0,
                passed=False,
                issues=[QualityIssue(
                    check_type=QualityCheckType.COMPLETENESS,
                    level=QualityIssueLevel.CRITICAL,
                    message="数据集为空"
                )]
            )

        total_cells = data.size
        null_cells = data.isnull().sum().sum()
        completeness_score = (total_cells - null_cells) / total_cells

        details['total_cells'] = total_cells
        details['null_cells'] = null_cells
        details['completeness_rate'] = completeness_score

        # 检查必需列
        required_columns = rules.get('required_columns', [])
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            issues.append(QualityIssue(
                issue_id=f"missing_cols_{int(time.time())}",
                dimension=QualityCheckType.COMPLETENESS,
                level=QualityIssueLevel.CRITICAL,
                title="缺少必需列",
                description=f"缺少必需列: {', '.join(missing_columns)}",
                recommendation="检查数据源配置和字段映射"
            ))

        # 检查列完整性
        threshold = rules.get('completeness_threshold', 0.95)
        for column in data.columns:
            null_count = data[column].isnull().sum()
            null_rate = null_count / len(data)

            if null_rate > (1 - threshold):
                level = QualityIssueLevel.CRITICAL if null_rate > 0.5 else QualityIssueLevel.HIGH
                issues.append(QualityIssue(
                    issue_id=f"null_rate_{column}_{int(time.time())}",
                    dimension=QualityCheckType.COMPLETENESS,
                    level=level,
                    title="空值率过高",
                    description=f"列 '{column}' 空值率过高: {null_rate:.2%}",
                    field_name=column,
                    record_count=null_count,
                    percentage=null_rate * 100,
                    recommendation=f"检查 '{column}' 列的数据采集和处理逻辑"
                ))

        passed = completeness_score >= threshold and not missing_columns

        return QualityCheckResult(
            check_type=QualityCheckType.COMPLETENESS,
            score=completeness_score,
            passed=passed,
            issues=issues,
            details=details
        )

    def _check_accuracy(self, data: pd.DataFrame, rules: Dict[str, Any],
                        data_type: str) -> QualityCheckResult:
        """检查数据准确性"""
        issues = []
        details = {}
        accuracy_scores = []

        # 数值范围检查
        numeric_columns = rules.get('numeric_columns', [])
        for column in numeric_columns:
            if column not in data.columns:
                continue

            numeric_data = pd.to_numeric(data[column], errors='coerce')
            invalid_count = numeric_data.isnull().sum() - data[column].isnull().sum()

            if invalid_count > 0:
                invalid_rate = invalid_count / len(data)
                issues.append(QualityIssue(
                    check_type=QualityCheckType.ACCURACY,
                    level=QualityIssueLevel.HIGH,
                    message=f"列 '{column}' 包含非数值数据: {invalid_count} 条",
                    field_name=column,
                    record_count=invalid_count,
                    percentage=invalid_rate * 100,
                    recommendation=f"检查 '{column}' 列的数据格式和转换逻辑"
                ))

            # 范围检查
            if data_type == 'kline' and column in ['open', 'high', 'low', 'close']:
                price_range = rules.get('price_range', {})
                min_price = price_range.get('min', 0.01)
                max_price = price_range.get('max', 10000)

                out_of_range = ((numeric_data < min_price) | (numeric_data > max_price)).sum()
                if out_of_range > 0:
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.ACCURACY,
                        level=QualityIssueLevel.MEDIUM,
                        message=f"列 '{column}' 价格超出合理范围: {out_of_range} 条",
                        field_name=column,
                        record_count=out_of_range,
                        recommendation="检查价格数据的单位和精度"
                    ))

            # 计算准确性得分
            valid_rate = (len(data) - invalid_count - out_of_range) / len(data) if 'out_of_range' in locals() else (len(data) - invalid_count) / len(data)
            accuracy_scores.append(valid_rate)

        # OHLC逻辑检查（针对K线数据）
        if data_type == 'kline' and rules.get('ohlc_logic', False):
            ohlc_columns = ['open', 'high', 'low', 'close']
            if all(col in data.columns for col in ohlc_columns):
                # 检查 high >= max(open, close) 和 low <= min(open, close)
                invalid_high = (data['high'] < data[['open', 'close']].max(axis=1)).sum()
                invalid_low = (data['low'] > data[['open', 'close']].min(axis=1)).sum()

                if invalid_high > 0:
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.ACCURACY,
                        level=QualityIssueLevel.HIGH,
                        message=f"最高价逻辑错误: {invalid_high} 条记录",
                        recommendation="检查OHLC数据的逻辑一致性"
                    ))

                if invalid_low > 0:
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.ACCURACY,
                        level=QualityIssueLevel.HIGH,
                        message=f"最低价逻辑错误: {invalid_low} 条记录",
                        recommendation="检查OHLC数据的逻辑一致性"
                    ))

        # 计算总体准确性得分
        overall_accuracy = np.mean(accuracy_scores) if accuracy_scores else 1.0
        threshold = rules.get('accuracy_threshold', 0.90)
        passed = overall_accuracy >= threshold

        details['accuracy_scores'] = accuracy_scores
        details['overall_accuracy'] = overall_accuracy

        return QualityCheckResult(
            check_type=QualityCheckType.ACCURACY,
            score=overall_accuracy,
            passed=passed,
            issues=issues,
            details=details
        )

    def _check_consistency(self, data: pd.DataFrame, rules: Dict[str, Any],
                           data_type: str) -> QualityCheckResult:
        """检查数据一致性"""
        issues = []
        details = {}
        consistency_score = 1.0

        # 检查数据类型一致性
        for column in data.columns:
            if data[column].dtype == 'object':
                # 检查字符串列的格式一致性
                unique_patterns = data[column].dropna().astype(str).str.len().nunique()
                if unique_patterns > len(data) * 0.1:  # 如果长度变化太大
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.CONSISTENCY,
                        level=QualityIssueLevel.LOW,
                        message=f"列 '{column}' 格式不一致",
                        field_name=column,
                        recommendation=f"标准化 '{column}' 列的数据格式"
                    ))

        # 时间序列一致性检查
        if 'date' in data.columns or 'timestamp' in data.columns:
            date_column = 'date' if 'date' in data.columns else 'timestamp'
            try:
                dates = pd.to_datetime(data[date_column])
                # 检查时间序列是否有序
                if not dates.is_monotonic_increasing:
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.CONSISTENCY,
                        level=QualityIssueLevel.MEDIUM,
                        message="时间序列不是单调递增的",
                        field_name=date_column,
                        recommendation="对数据按时间排序"
                    ))

                # 检查时间间隔一致性
                if len(dates) > 1:
                    intervals = dates.diff().dropna()
                    if intervals.nunique() > len(intervals) * 0.1:
                        issues.append(QualityIssue(
                            check_type=QualityCheckType.CONSISTENCY,
                            level=QualityIssueLevel.LOW,
                            message="时间间隔不一致",
                            field_name=date_column,
                            recommendation="检查数据采集频率的一致性"
                        ))
            except:
                pass

        # 计算一致性得分
        if issues:
            consistency_score = max(0.0, 1.0 - len(issues) * 0.1)

        passed = consistency_score >= 0.8
        details['consistency_score'] = consistency_score

        return QualityCheckResult(
            check_type=QualityCheckType.CONSISTENCY,
            score=consistency_score,
            passed=passed,
            issues=issues,
            details=details
        )

    def _check_timeliness(self, data: pd.DataFrame, rules: Dict[str, Any],
                          data_type: str) -> QualityCheckResult:
        """检查数据及时性"""
        issues = []
        details = {}
        timeliness_score = 1.0

        # 查找时间列
        time_columns = [col for col in data.columns
                        if 'time' in col.lower() or 'date' in col.lower()]

        if not time_columns:
            return QualityCheckResult(
                check_type=QualityCheckType.TIMELINESS,
                score=1.0,
                passed=True,
                issues=[],
                details={'message': '未找到时间列，跳过及时性检查'}
            )

        time_column = time_columns[0]

        try:
            timestamps = pd.to_datetime(data[time_column])
            latest_time = timestamps.max()
            current_time = datetime.now()

            # 计算数据延迟
            if pd.notna(latest_time):
                delay_minutes = (current_time - latest_time).total_seconds() / 60
                threshold_minutes = rules.get('timeliness_threshold', 1440)  # 默认24小时

                details['latest_data_time'] = latest_time.isoformat()
                details['delay_minutes'] = delay_minutes
                details['threshold_minutes'] = threshold_minutes

                if delay_minutes > threshold_minutes:
                    level = QualityIssueLevel.HIGH if delay_minutes > threshold_minutes * 2 else QualityIssueLevel.MEDIUM
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.TIMELINESS,
                        level=level,
                        message=f"数据延迟 {delay_minutes:.1f} 分钟",
                        field_name=time_column,
                        recommendation="检查数据更新频率和采集流程"
                    ))

                    timeliness_score = max(0.0, 1.0 - (delay_minutes - threshold_minutes) / threshold_minutes)

        except Exception as e:
            issues.append(QualityIssue(
                check_type=QualityCheckType.TIMELINESS,
                level=QualityIssueLevel.MEDIUM,
                message=f"时间格式解析失败: {str(e)}",
                field_name=time_column,
                recommendation="检查时间格式的标准化"
            ))
            timeliness_score = 0.5

        passed = timeliness_score >= 0.8

        return QualityCheckResult(
            check_type=QualityCheckType.TIMELINESS,
            score=timeliness_score,
            passed=passed,
            issues=issues,
            details=details
        )

    def _check_validity(self, data: pd.DataFrame, rules: Dict[str, Any],
                        data_type: str) -> QualityCheckResult:
        """检查数据有效性"""
        issues = []
        details = {}
        validity_scores = []

        # 检查每列的有效性
        for column in data.columns:
            column_data = data[column]
            valid_count = len(column_data) - column_data.isnull().sum()

            # 基本有效性检查
            if column_data.dtype in ['int64', 'float64']:
                # 检查无穷大和NaN
                inf_count = np.isinf(column_data).sum()
                if inf_count > 0:
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.VALIDITY,
                        level=QualityIssueLevel.HIGH,
                        message=f"列 '{column}' 包含无穷大值: {inf_count} 条",
                        field_name=column,
                        record_count=inf_count,
                        recommendation=f"处理 '{column}' 列的无穷大值"
                    ))
                    valid_count -= inf_count

            # 计算列有效性得分
            validity_rate = valid_count / len(column_data) if len(column_data) > 0 else 0
            validity_scores.append(validity_rate)

        # 计算总体有效性得分
        overall_validity = np.mean(validity_scores) if validity_scores else 0.0
        passed = overall_validity >= 0.9

        details['validity_scores'] = validity_scores
        details['overall_validity'] = overall_validity

        return QualityCheckResult(
            check_type=QualityCheckType.VALIDITY,
            score=overall_validity,
            passed=passed,
            issues=issues,
            details=details
        )

    def _check_uniqueness(self, data: pd.DataFrame, rules: Dict[str, Any],
                          data_type: str) -> QualityCheckResult:
        """检查数据唯一性"""
        issues = []
        details = {}

        # 检查重复记录
        duplicate_count = data.duplicated().sum()
        duplicate_rate = duplicate_count / len(data) if len(data) > 0 else 0

        details['duplicate_count'] = duplicate_count
        details['duplicate_rate'] = duplicate_rate

        if duplicate_count > 0:
            level = QualityIssueLevel.HIGH if duplicate_rate > 0.05 else QualityIssueLevel.MEDIUM
            issues.append(QualityIssue(
                check_type=QualityCheckType.UNIQUENESS,
                level=level,
                message=f"发现重复记录: {duplicate_count} 条 ({duplicate_rate:.2%})",
                record_count=duplicate_count,
                percentage=duplicate_rate * 100,
                recommendation="去除或合并重复记录"
            ))

        # 检查关键字段唯一性
        key_columns = rules.get('unique_columns', [])
        for column in key_columns:
            if column in data.columns:
                unique_count = data[column].nunique()
                total_count = len(data) - data[column].isnull().sum()

                if unique_count < total_count:
                    duplicate_keys = total_count - unique_count
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.UNIQUENESS,
                        level=QualityIssueLevel.HIGH,
                        message=f"关键字段 '{column}' 存在重复: {duplicate_keys} 条",
                        field_name=column,
                        record_count=duplicate_keys,
                        recommendation=f"确保 '{column}' 字段的唯一性"
                    ))

        uniqueness_score = 1.0 - duplicate_rate
        passed = uniqueness_score >= 0.95

        return QualityCheckResult(
            check_type=QualityCheckType.UNIQUENESS,
            score=uniqueness_score,
            passed=passed,
            issues=issues,
            details=details
        )

    def _check_integrity(self, data: pd.DataFrame, rules: Dict[str, Any],
                         data_type: str) -> QualityCheckResult:
        """检查数据完整性（引用完整性等）"""
        issues = []
        details = {}
        integrity_score = 1.0

        # 检查外键完整性（如果定义了外键关系）
        foreign_keys = rules.get('foreign_keys', {})
        for fk_column, reference_info in foreign_keys.items():
            if fk_column in data.columns:
                # 这里可以添加外键完整性检查逻辑
                pass

        # 检查业务规则完整性
        business_rules = rules.get('business_rules', [])
        for rule in business_rules:
            # 这里可以添加业务规则检查逻辑
            pass

        passed = integrity_score >= 0.9
        details['integrity_score'] = integrity_score

        return QualityCheckResult(
            check_type=QualityCheckType.INTEGRITY,
            score=integrity_score,
            passed=passed,
            issues=issues,
            details=details
        )

    def _check_conformity(self, data: pd.DataFrame, rules: Dict[str, Any],
                          data_type: str) -> QualityCheckResult:
        """检查数据符合性（格式、标准等）"""
        issues = []
        details = {}
        conformity_scores = []

        # 检查日期格式符合性
        date_columns = rules.get('date_columns', [])
        date_format = rules.get('date_format', '%Y-%m-%d')

        for column in date_columns:
            if column in data.columns:
                try:
                    pd.to_datetime(data[column], format=date_format, errors='raise')
                    conformity_scores.append(1.0)
                except:
                    # 计算格式错误率
                    valid_dates = pd.to_datetime(data[column], errors='coerce').notna().sum()
                    total_dates = len(data) - data[column].isnull().sum()
                    conformity_rate = valid_dates / total_dates if total_dates > 0 else 0
                    conformity_scores.append(conformity_rate)

                    if conformity_rate < 0.9:
                        issues.append(QualityIssue(
                            check_type=QualityCheckType.CONFORMITY,
                            level=QualityIssueLevel.MEDIUM,
                            message=f"列 '{column}' 日期格式不符合标准: {(1-conformity_rate):.2%}",
                            field_name=column,
                            recommendation=f"标准化 '{column}' 列的日期格式为 {date_format}"
                        ))

        # 检查数值精度符合性
        precision_rules = rules.get('precision_rules', {})
        for column, precision in precision_rules.items():
            if column in data.columns and data[column].dtype in ['float64']:
                # 检查小数位数是否符合要求
                decimal_places = data[column].astype(str).str.split('.').str[1].str.len()
                over_precision = (decimal_places > precision).sum()

                if over_precision > 0:
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.CONFORMITY,
                        level=QualityIssueLevel.LOW,
                        message=f"列 '{column}' 精度超出标准: {over_precision} 条",
                        field_name=column,
                        recommendation=f"调整 '{column}' 列的精度为 {precision} 位小数"
                    ))

        # 计算总体符合性得分
        overall_conformity = np.mean(conformity_scores) if conformity_scores else 1.0
        passed = overall_conformity >= 0.9

        details['conformity_scores'] = conformity_scores
        details['overall_conformity'] = overall_conformity

        return QualityCheckResult(
            check_type=QualityCheckType.CONFORMITY,
            score=overall_conformity,
            passed=passed,
            issues=issues,
            details=details
        )

    # ==================== 辅助方法 ====================

    def _calculate_overall_score(self, check_results: Dict[QualityCheckType, QualityCheckResult]) -> float:
        """计算综合质量评分"""
        if not check_results:
            return 0.0

        # 权重配置（可根据业务需求调整）
        weights = {
            QualityCheckType.COMPLETENESS: 0.25,
            QualityCheckType.ACCURACY: 0.25,
            QualityCheckType.CONSISTENCY: 0.15,
            QualityCheckType.TIMELINESS: 0.15,
            QualityCheckType.VALIDITY: 0.10,
            QualityCheckType.UNIQUENESS: 0.05,
            QualityCheckType.INTEGRITY: 0.03,
            QualityCheckType.CONFORMITY: 0.02
        }

        weighted_score = 0.0
        total_weight = 0.0

        for check_type, result in check_results.items():
            weight = weights.get(check_type, 0.1)
            weighted_score += result.score * weight
            total_weight += weight

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _determine_quality_level(self, score: float) -> DataQuality:
        """确定质量等级"""
        if score >= 0.95:
            return DataQuality.EXCELLENT
        elif score >= 0.85:
            return DataQuality.GOOD
        elif score >= 0.70:
            return DataQuality.FAIR
        else:
            return DataQuality.POOR

    def _generate_recommendations(self, report: UnifiedQualityReport) -> List[str]:
        """生成质量改进建议"""
        recommendations = []

        # 基于问题级别生成建议
        if report.critical_issues > 0:
            recommendations.append("立即处理严重质量问题，这些问题可能影响数据的基本可用性")

        if report.high_issues > 0:
            recommendations.append("优先处理高级质量问题，以提升数据准确性和可靠性")

        if report.overall_score < 0.7:
            recommendations.append("数据质量较差，建议全面检查数据采集和处理流程")

        # 基于具体检查结果生成建议
        for check_result in report.check_results.values():
            for issue in check_result.issues:
                if issue.recommendation and issue.recommendation not in recommendations:
                    recommendations.append(issue.recommendation)

        # 通用建议
        if report.null_records > report.total_records * 0.1:
            recommendations.append("空值率较高，建议完善数据采集逻辑或增加数据验证")

        if report.duplicate_records > 0:
            recommendations.append("存在重复数据，建议实施数据去重策略")

        return recommendations[:10]  # 限制建议数量

    def _update_stats(self, report: UnifiedQualityReport):
        """更新统计信息"""
        self._stats['total_checks'] += 1

        if report.overall_score >= 0.8:
            self._stats['passed_checks'] += 1
        else:
            self._stats['failed_checks'] += 1

        self._stats['critical_issues_found'] += report.critical_issues

        # 更新平均分
        total_checks = self._stats['total_checks']
        current_avg = self._stats['average_score']
        self._stats['average_score'] = (current_avg * (total_checks - 1) + report.overall_score) / total_checks

    def _save_quality_report(self, report: UnifiedQualityReport):
        """保存质量报告到数据库"""
        if not self.enable_persistence:
            return

        try:
            with self._db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    # 保存主报告
                    cursor = conn.execute("""
                        INSERT INTO quality_reports (
                            data_source, table_name, check_timestamp, total_records,
                            overall_score, quality_level, null_records, duplicate_records,
                            invalid_records, critical_issues, high_issues, medium_issues,
                            low_issues, check_results, recommendations
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        report.data_source, report.table_name, report.check_timestamp,
                        report.total_records, report.overall_score, report.quality_level.value,
                        report.null_records, report.duplicate_records, report.invalid_records,
                        report.critical_issues, report.high_issues, report.medium_issues,
                        report.low_issues, json.dumps({k.value: asdict(v) for k, v in report.check_results.items()}),
                        json.dumps(report.recommendations)
                    ])

                    report_id = cursor.lastrowid

                    # 保存质量问题
                    for check_result in report.check_results.values():
                        for issue in check_result.issues:
                            conn.execute("""
                                INSERT INTO quality_issues (
                                    report_id, check_type, issue_level, message,
                                    field_name, record_count, percentage, recommendation
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, [
                                report_id, issue.check_type.value, issue.level.value,
                                issue.message, issue.field_name, issue.record_count,
                                issue.percentage, issue.recommendation
                            ])

                    conn.commit()

        except Exception as e:
            logger.error(f"保存质量报告失败: {e}")

    def _notify_quality_listeners(self, report: UnifiedQualityReport):
        """通知质量监听器"""
        with self._listener_lock:
            for listener in self._quality_listeners:
                try:
                    listener(report)
                except Exception as e:
                    logger.error(f"质量监听器执行失败: {e}")

    # ==================== 公共API方法 ====================

    def add_quality_listener(self, listener: Callable[[UnifiedQualityReport], None]):
        """添加质量监听器"""
        with self._listener_lock:
            self._quality_listeners.append(listener)

    def remove_quality_listener(self, listener: Callable[[UnifiedQualityReport], None]):
        """移除质量监听器"""
        with self._listener_lock:
            if listener in self._quality_listeners:
                self._quality_listeners.remove(listener)

    def get_quality_history(self, data_source: str, table_name: str,
                            days: int = 30) -> List[Dict[str, Any]]:
        """获取质量历史记录"""
        if not self.enable_persistence:
            return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                cursor = conn.execute("""
                    SELECT * FROM quality_reports 
                    WHERE data_source = ? AND table_name = ?
                    AND check_timestamp >= datetime('now', '-{} days')
                    ORDER BY check_timestamp DESC
                """.format(days), [data_source, table_name])

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"获取质量历史失败: {e}")
            return []

    def get_quality_trends(self, data_source: str, table_name: str,
                           days: int = 30) -> Dict[str, Any]:
        """获取质量趋势分析"""
        history = self.get_quality_history(data_source, table_name, days)

        if not history:
            return {}

        scores = [record['overall_score'] for record in history]
        timestamps = [record['check_timestamp'] for record in history]

        return {
            'data_source': data_source,
            'table_name': table_name,
            'period_days': days,
            'check_count': len(history),
            'average_score': np.mean(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'score_trend': 'improving' if len(scores) > 1 and scores[0] > scores[-1] else 'declining' if len(scores) > 1 and scores[0] < scores[-1] else 'stable',
            'latest_score': scores[0] if scores else 0,
            'timestamps': timestamps,
            'scores': scores
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        return self._stats.copy()

    def start_real_time_monitoring(self, interval_seconds: int = 300):
        """启动实时质量监控"""
        if not self.enable_real_time_monitoring:
            logger.warning("实时监控未启用")
            return False

        with self._monitoring_lock:
            if self._monitoring_active:
                logger.warning("实时监控已在运行")
                return False

            self._monitoring_active = True
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                args=(interval_seconds,),
                daemon=True,
                name="QualityMonitor"
            )
            self._monitoring_thread.start()

        logger.info(f"实时质量监控已启动，检查间隔: {interval_seconds}秒")
        return True

    def stop_real_time_monitoring(self):
        """停止实时质量监控"""
        with self._monitoring_lock:
            if not self._monitoring_active:
                return False

            self._monitoring_active = False

            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=5)

        logger.info("实时质量监控已停止")
        return True

    def _monitoring_loop(self, interval_seconds: int):
        """监控循环"""
        while self._monitoring_active:
            try:
                # 这里可以添加自动质量检查逻辑
                # 例如：检查最近更新的数据表
                time.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"质量监控循环出错: {e}")
                time.sleep(60)  # 出错后等待1分钟再继续

    def shutdown(self):
        """关闭监控器"""
        try:
            logger.info("关闭统一数据质量监控器...")

            # 停止实时监控
            self.stop_real_time_monitoring()

            # 清理监听器
            with self._listener_lock:
                self._quality_listeners.clear()

            # 清理缓存
            with self._cache_lock:
                self._quality_cache.clear()

            logger.info("统一数据质量监控器已关闭")

        except Exception as e:
            logger.error(f"关闭质量监控器失败: {e}")


# 全局单例实例
_unified_quality_monitor: Optional[UnifiedDataQualityMonitor] = None
_monitor_lock = threading.Lock()


def get_unified_quality_monitor() -> UnifiedDataQualityMonitor:
    """获取全局统一质量监控器实例"""
    global _unified_quality_monitor

    if _unified_quality_monitor is None:
        with _monitor_lock:
            if _unified_quality_monitor is None:
                _unified_quality_monitor = UnifiedDataQualityMonitor()

    return _unified_quality_monitor


def initialize_unified_quality_monitor(db_path: Optional[str] = None,
                                       enable_persistence: bool = True,
                                       enable_real_time_monitoring: bool = True) -> UnifiedDataQualityMonitor:
    """初始化全局统一质量监控器"""
    global _unified_quality_monitor

    with _monitor_lock:
        if _unified_quality_monitor is not None:
            _unified_quality_monitor.shutdown()

        _unified_quality_monitor = UnifiedDataQualityMonitor(
            db_path=db_path,
            enable_persistence=enable_persistence,
            enable_real_time_monitoring=enable_real_time_monitoring
        )

    return _unified_quality_monitor
