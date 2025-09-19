#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI数据模型定义

定义UI组件使用的数据模型，确保类型安全和数据一致性。

作者: FactorWeave-Quant团队
版本: 1.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


@dataclass
class UIDataModel:
    """UI数据模型基类"""
    timestamp: datetime = field(default_factory=datetime.now)
    source_service: Optional[str] = None
    is_cached: bool = False
    cache_expiry: Optional[datetime] = None


@dataclass
class TaskStatusUIModel(UIDataModel):
    """任务状态UI模型"""
    task_id: str
    name: str
    status: str
    progress: float
    estimated_completion: Optional[datetime] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class AIStatusUIModel(UIDataModel):
    """AI状态UI模型"""
    prediction_accuracy: float
    learning_progress: float = 0.0
    recommendations_count: int = 0
    anomaly_alerts_count: int = 0
    active_models: List[str] = field(default_factory=list)
    last_prediction_time: Optional[datetime] = None

    # 扩展AI状态信息
    core_service_status: str = "未知"
    prediction_service_status: str = "未知"
    learning_service_status: str = "未知"
    anomaly_detection_status: str = "未知"
    recommendation_engine_status: str = "未知"
    prediction_model_status: str = "未知"
    user_behavior_learner_status: str = "未知"
    last_update_time: Optional[datetime] = None
    model_version: str = "未知"
    data_quality_score: float = 0.0


@dataclass
class PerformanceUIModel(UIDataModel):
    """性能指标UI模型"""
    cpu_usage: float
    memory_usage: float
    cache_hit_rate: float
    active_tasks: int
    throughput: float
    response_time: float
    distributed_nodes: int = 0
    node_status: Dict[str, str] = field(default_factory=dict)


@dataclass
class QualityUIModel(UIDataModel):
    """数据质量UI模型"""
    overall_score: float
    completeness: float
    accuracy: float
    consistency: float
    timeliness: float
    anomaly_count: int = 0
    critical_issues: List[str] = field(default_factory=list)


@dataclass
class PredictionResultUIModel(UIDataModel):
    """预测结果UI模型"""
    prediction_id: str
    target: str
    predicted_value: Any
    confidence: float
    model_name: str
    features_used: List[str] = field(default_factory=list)
    explanation: str = ""
    created_at: datetime = field(default_factory=datetime.now)


# 导出的公共接口
__all__ = [
    'UIDataModel',
    'TaskStatusUIModel',
    'AIStatusUIModel',
    'PerformanceUIModel',
    'QualityUIModel',
    'PredictionResultUIModel'
]
