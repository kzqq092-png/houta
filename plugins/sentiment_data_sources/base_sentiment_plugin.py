"""
情绪数据源插件基类
提供情绪分析数据获取的标准接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass

from plugins.plugin_interface import IPlugin, PluginType, PluginCategory, PluginMetadata


@dataclass
class SentimentData:
    """情绪数据结构"""
    indicator_name: str              # 指标名称
    value: float                     # 指标值
    status: str                      # 情绪状态 (恐慌/中性/贪婪等)
    change: float                    # 变化幅度
    signal: str                      # 交易信号
    suggestion: str                  # 投资建议
    timestamp: datetime              # 时间戳
    source: str                      # 数据源
    confidence: float = 0.8          # 数据置信度
    color: str = "#666666"           # 显示颜色
    metadata: Dict[str, Any] = None  # 扩展元数据


@dataclass
class SentimentResponse:
    """情绪分析响应"""
    success: bool                    # 是否成功
    data: List[SentimentData]        # 情绪数据列表
    composite_score: float           # 综合情绪指数
    error_message: str = ""          # 错误信息
    data_quality: str = "real"       # 数据质量标识
    update_time: datetime = None     # 更新时间
    cache_used: bool = False         # 是否使用缓存


class ISentimentDataSource(IPlugin):
    """情绪数据源插件接口"""

    @abstractmethod
    def fetch_sentiment_data(self, **kwargs) -> SentimentResponse:
        """
        获取情绪数据

        Args:
            **kwargs: 扩展参数

        Returns:
            SentimentResponse: 情绪数据响应
        """
        pass

    @abstractmethod
    def get_available_indicators(self) -> List[Dict[str, Any]]:
        """
        获取可用的情绪指标列表

        Returns:
            List[Dict]: 指标信息列表
        """
        pass

    @abstractmethod
    def validate_data_quality(self, data: List[SentimentData]) -> float:
        """
        验证数据质量

        Args:
            data: 情绪数据列表

        Returns:
            float: 数据质量评分 (0-1)
        """
        pass

    def calculate_composite_sentiment(self, data: List[SentimentData]) -> float:
        """
        计算综合情绪指数

        Args:
            data: 情绪数据列表

        Returns:
            float: 综合情绪指数 (0-100)
        """
        if not data:
            return 50.0  # 中性

        total_score = 0
        total_weight = 0

        # 默认权重映射
        weights = {
            '恐慌指数': 0.25,
            'VIX': 0.25,
            '贪婪指数': 0.20,
            '新闻情绪': 0.15,
            '社交情绪': 0.10,
            '其他': 0.05
        }

        for sentiment in data:
            # 获取指标权重
            weight = weights.get(sentiment.indicator_name, weights['其他'])

            # 标准化指标值到0-100范围
            normalized_value = self._normalize_sentiment_value(sentiment.value, sentiment.indicator_name)

            total_score += normalized_value * weight * sentiment.confidence
            total_weight += weight * sentiment.confidence

        return total_score / total_weight if total_weight > 0 else 50.0

    def _normalize_sentiment_value(self, value: float, indicator_name: str) -> float:
        """
        标准化情绪值到0-100范围

        Args:
            value: 原始值
            indicator_name: 指标名称

        Returns:
            float: 标准化后的值
        """
        # 根据不同指标类型进行标准化
        if 'VIX' in indicator_name or '恐慌' in indicator_name:
            # VIX类指标：值越高，恐慌程度越高，情绪指数越低
            if value <= 10:
                return 90  # 极度乐观
            elif value <= 20:
                return 70  # 乐观
            elif value <= 30:
                return 50  # 中性
            elif value <= 40:
                return 30  # 恐慌
            else:
                return 10  # 极度恐慌

        elif '贪婪' in indicator_name:
            # 贪婪指数：直接对应情绪指数
            return max(0, min(100, value))

        elif '新闻情绪' in indicator_name or '社交情绪' in indicator_name:
            # 新闻/社交情绪：-100到100映射到0-100
            return (value + 100) / 2

        else:
            # 默认处理：假设已经是0-100范围
            return max(0, min(100, value))

    def get_sentiment_status(self, score: float) -> str:
        """
        根据情绪指数获取状态描述

        Args:
            score: 情绪指数 (0-100)

        Returns:
            str: 状态描述
        """
        if score >= 80:
            return "极度贪婪"
        elif score >= 70:
            return "贪婪"
        elif score >= 60:
            return "乐观"
        elif score >= 40:
            return "中性"
        elif score >= 30:
            return "悲观"
        elif score >= 20:
            return "恐慌"
        else:
            return "极度恐慌"

    def get_trading_signal(self, score: float) -> str:
        """
        根据情绪指数获取交易信号

        Args:
            score: 情绪指数 (0-100)

        Returns:
            str: 交易信号
        """
        if score >= 80:
            return "减仓风险"
        elif score >= 70:
            return "谨慎观望"
        elif score >= 60:
            return "正常操作"
        elif score >= 40:
            return "正常操作"
        elif score >= 30:
            return "关注机会"
        elif score >= 20:
            return "买入机会"
        else:
            return "抄底机会"

    def get_investment_suggestion(self, score: float) -> str:
        """
        根据情绪指数获取投资建议

        Args:
            score: 情绪指数 (0-100)

        Returns:
            str: 投资建议
        """
        if score >= 80:
            return "市场过度乐观，建议减仓避险"
        elif score >= 70:
            return "市场情绪较好，注意风险控制"
        elif score >= 60:
            return "市场情绪正常，维持现有仓位"
        elif score >= 40:
            return "市场情绪中性，可正常操作"
        elif score >= 30:
            return "市场情绪偏悲观，可关注优质标的"
        elif score >= 20:
            return "市场恐慌情绪，可考虑逢低买入"
        else:
            return "极度恐慌，优质资产可能被错杀"

    def get_status_color(self, score: float) -> str:
        """
        根据情绪指数获取显示颜色

        Args:
            score: 情绪指数 (0-100)

        Returns:
            str: 颜色代码
        """
        if score >= 80:
            return "#dc3545"  # 红色-危险
        elif score >= 70:
            return "#fd7e14"  # 橙色-警告
        elif score >= 60:
            return "#ffc107"  # 黄色-注意
        elif score >= 40:
            return "#28a745"  # 绿色-正常
        elif score >= 30:
            return "#17a2b8"  # 青色-机会
        elif score >= 20:
            return "#007bff"  # 蓝色-买入
        else:
            return "#6f42c1"  # 紫色-抄底


class BaseSentimentPlugin(ISentimentDataSource):
    """情绪数据源插件基类"""

    def __init__(self):
        self.context = None
        self.cache = {}
        self.cache_timeout = 300  # 5分钟缓存
        self.last_update = None

    def initialize(self, context) -> bool:
        """初始化插件"""
        try:
            self.context = context
            self.log_manager = context.log_manager
            self.config = context.get_plugin_config(self.metadata.name)
            return True
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"插件初始化失败: {e}")
            return False

    def cleanup(self) -> None:
        """清理插件资源"""
        try:
            self.cache.clear()
            self.context = None
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"插件清理失败: {e}")

    def fetch_sentiment_data(self, use_cache: bool = True, **kwargs) -> SentimentResponse:
        """
        获取情绪数据（带缓存）

        Args:
            use_cache: 是否使用缓存
            **kwargs: 扩展参数

        Returns:
            SentimentResponse: 情绪数据响应
        """
        try:
            # 检查缓存
            if use_cache and self._is_cache_valid():
                cached_data = self.cache.get('sentiment_data')
                if cached_data:
                    cached_data.cache_used = True
                    return cached_data

            # 获取新数据
            response = self._fetch_raw_sentiment_data(**kwargs)

            if response.success:
                # 缓存数据
                response.update_time = datetime.now()
                self.cache['sentiment_data'] = response
                self.last_update = datetime.now()

                # 计算综合情绪指数
                response.composite_score = self.calculate_composite_sentiment(response.data)

                if hasattr(self, 'log_manager'):
                    self.log_manager.info(f"成功获取{len(response.data)}个情绪指标，综合指数{response.composite_score:.1f}")

            return response

        except Exception as e:
            error_msg = f"获取情绪数据失败: {str(e)}"
            if hasattr(self, 'log_manager'):
                self.log_manager.error(error_msg)

            return SentimentResponse(
                success=False,
                data=[],
                composite_score=50.0,
                error_message=error_msg,
                data_quality="error"
            )

    @abstractmethod
    def _fetch_raw_sentiment_data(self, **kwargs) -> SentimentResponse:
        """
        获取原始情绪数据（子类实现）

        Args:
            **kwargs: 扩展参数

        Returns:
            SentimentResponse: 情绪数据响应
        """
        pass

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.last_update:
            return False

        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed < self.cache_timeout

    def validate_data_quality(self, data: List[SentimentData]) -> float:
        """验证数据质量"""
        if not data:
            return 0.0

        quality_score = 0.0

        # 检查数据完整性
        complete_data = [d for d in data if d.value is not None and d.timestamp is not None]
        completeness = len(complete_data) / len(data)
        quality_score += completeness * 0.4

        # 检查数据时效性
        current_time = datetime.now()
        recent_data = [d for d in complete_data
                       if (current_time - d.timestamp).total_seconds() < 86400]  # 24小时内
        timeliness = len(recent_data) / len(complete_data) if complete_data else 0
        quality_score += timeliness * 0.3

        # 检查数据置信度
        avg_confidence = sum(d.confidence for d in complete_data) / len(complete_data) if complete_data else 0
        quality_score += avg_confidence * 0.3

        return min(1.0, quality_score)

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "cache_timeout": 300,
            "retry_times": 3,
            "request_timeout": 30,
            "enable_cache": True,
            "data_source_priority": 1.0
        }

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        try:
            required_fields = ["cache_timeout", "retry_times", "request_timeout"]
            return all(field in config for field in required_fields)
        except:
            return False
