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
import logging

from plugins.plugin_interface import IPlugin, PluginType, PluginCategory, PluginMetadata
from plugins.sentiment_data_source_interface import (
    ISentimentDataSource,
    SentimentData,
    SentimentResponse,
    SentimentStatus,
    TradingSignal
)


# 移除本地重复定义的类，使用统一接口

class BaseSentimentPlugin(ISentimentDataSource):
    """情绪数据源插件基类"""

    def __init__(self):
        self.context = None
        self.cache = {}
        self.cache_timeout = 300  # 5分钟缓存
        self.last_update = None
        # 创建本地logger作为备用
        self._local_logger = logging.getLogger(__name__)

    def _safe_log(self, level: str, message: str):
        """安全的日志记录方法"""
        try:
            if hasattr(self, 'log_manager') and self.log_manager:
                getattr(self.log_manager, level)(message)
            else:
                # 使用本地logger作为备用
                getattr(self._local_logger, level)(message)
        except Exception:
            # 最后的备用方案，直接打印
            print(f"[{level.upper()}] {message}")

    def initialize(self, context) -> bool:
        """初始化插件"""
        try:
            self.context = context

            if context is not None:
                self.log_manager = getattr(context, 'log_manager', None)
                self.config = context.get_plugin_config(self.metadata.name) if hasattr(context, 'get_plugin_config') else {}
            else:
                # 处理context为None的情况，使用默认配置
                self.log_manager = None
                self.config = {}

            return True
        except Exception as e:
            self._safe_log("error", f"插件初始化失败: {e}")
            return False

    def cleanup(self) -> None:
        """清理插件资源"""
        try:
            # 清理缓存
            self.cache.clear()

            # 子类可以重写此方法进行特定的清理操作
            if hasattr(self, '_cleanup_resources'):
                self._cleanup_resources()

        except Exception as e:
            self._safe_log("error", f"插件清理失败: {e}")

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

                self._safe_log("info", f"成功获取{len(response.data)}个情绪指标，综合指数{response.composite_score:.1f}")

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

    def _handle_plugin_error(self, error: Exception, operation: str) -> SentimentResponse:
        """处理插件错误"""
        error_msg = f"插件操作失败 [{operation}]: {str(error)}"
        self._safe_log("error", error_msg)

        return SentimentResponse(
            success=False,
            data=[],
            composite_score=50.0,  # 中性分数
            error_message=error_msg,
            data_quality="error",
            update_time=datetime.now()
        )
