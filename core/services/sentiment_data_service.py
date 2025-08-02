"""
情绪数据服务管理器

此模块提供情绪数据的统一访问接口，协调多个情绪数据源插件，
实现数据聚合、缓存、故障处理等功能。

主要功能：
- 管理注册的情绪数据源插件
- 聚合来自多个插件的情绪数据
- 提供统一的数据访问接口
- 处理插件故障和数据质量控制
- 实现数据缓存和性能优化
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from ..base_logger import LogManager
from plugins.sentiment_data_source_interface import (
    ISentimentDataSource,
    SentimentData,
    SentimentResponse,
    SentimentStatus,
    TradingSignal
)


@dataclass
class SentimentDataServiceConfig:
    """情绪数据服务配置"""
    cache_duration_minutes: int = 5  # 缓存持续时间（分钟）
    auto_refresh_interval_minutes: int = 10  # 自动刷新间隔（分钟）
    max_concurrent_fetches: int = 3  # 最大并发获取数量
    plugin_timeout_seconds: int = 30  # 插件超时时间（秒）
    min_data_quality_threshold: str = 'fair'  # 最低数据质量要求
    enable_fallback: bool = True  # 启用回退机制
    enable_auto_refresh: bool = True  # 启用自动刷新


class SentimentDataService(QObject):
    """情绪数据服务管理器"""

    # 信号定义
    data_updated = pyqtSignal(object)  # 数据更新信号
    plugin_error = pyqtSignal(str, str)  # 插件错误信号
    service_status_changed = pyqtSignal(str)  # 服务状态变更信号

    def __init__(self,
                 plugin_manager=None,
                 config: Optional[SentimentDataServiceConfig] = None,
                 log_manager: Optional[LogManager] = None):
        """
        初始化情绪数据服务

        Args:
            plugin_manager: 插件管理器
            config: 服务配置
            log_manager: 日志管理器
        """
        super().__init__()

        self.plugin_manager = plugin_manager
        self.config = config or SentimentDataServiceConfig()
        self.log_manager = log_manager or logging.getLogger(__name__)

        # 注册的情绪数据源插件
        self._registered_plugins: Dict[str, ISentimentDataSource] = {}
        self._plugin_priorities: Dict[str, int] = {}  # 插件优先级
        self._plugin_weights: Dict[str, float] = {}  # 插件权重

        # 数据缓存
        self._cached_response: Optional[SentimentResponse] = None
        self._cache_timestamp: Optional[datetime] = None

        # 异步执行器
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_fetches)

        # 自动刷新定时器
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._auto_refresh)

        # 服务状态
        self._is_initialized = False
        self._is_running = False

    def initialize(self) -> bool:
        """初始化情绪数据服务"""
        try:
            self.log_manager.info("🚀 初始化情绪数据服务...")

            # 发现并注册情绪数据源插件
            self._discover_sentiment_plugins()

            # 启动自动刷新（如果启用）
            if self.config.enable_auto_refresh:
                self._start_auto_refresh()

            self._is_initialized = True
            self._is_running = True

            self.log_manager.info(f"✅ 情绪数据服务初始化完成，已注册 {len(self._registered_plugins)} 个插件")
            self.service_status_changed.emit("running")

            return True

        except Exception as e:
            self.log_manager.error(f"❌ 情绪数据服务初始化失败: {e}")
            return False

    def cleanup(self) -> None:
        """清理服务资源"""
        try:
            self.log_manager.info("🧹 清理情绪数据服务...")

            # 停止自动刷新
            self._refresh_timer.stop()

            # 清理插件
            for plugin in self._registered_plugins.values():
                try:
                    if hasattr(plugin, 'cleanup'):
                        plugin.cleanup()
                except Exception as e:
                    self.log_manager.warning(f"⚠️ 清理插件失败: {e}")

            # 关闭执行器
            self._executor.shutdown(wait=True)

            self._is_running = False
            self.service_status_changed.emit("stopped")
            self.log_manager.info("✅ 情绪数据服务清理完成")

        except Exception as e:
            self.log_manager.error(f"❌ 清理情绪数据服务失败: {e}")

    def register_plugin(self,
                        name: str,
                        plugin: ISentimentDataSource,
                        priority: int = 100,
                        weight: float = 1.0) -> bool:
        """
        注册情绪数据源插件

        Args:
            name: 插件名称
            plugin: 插件实例
            priority: 优先级（数值越小优先级越高）
            weight: 权重（用于数据聚合）

        Returns:
            bool: 是否注册成功
        """
        try:
            if not isinstance(plugin, ISentimentDataSource):
                self.log_manager.error(f"❌ 插件 {name} 不是有效的情绪数据源插件")
                return False

            # 初始化插件
            if hasattr(plugin, 'initialize'):
                if not plugin.initialize():
                    self.log_manager.error(f"❌ 插件 {name} 初始化失败")
                    return False

            self._registered_plugins[name] = plugin
            self._plugin_priorities[name] = priority
            self._plugin_weights[name] = weight

            self.log_manager.info(f"✅ 成功注册情绪数据源插件: {name}")
            return True

        except Exception as e:
            self.log_manager.error(f"❌ 注册插件 {name} 失败: {e}")
            return False

    def unregister_plugin(self, name: str) -> bool:
        """
        注销情绪数据源插件

        Args:
            name: 插件名称

        Returns:
            bool: 是否注销成功
        """
        try:
            if name not in self._registered_plugins:
                self.log_manager.warning(f"⚠️ 插件 {name} 未注册")
                return False

            # 清理插件
            plugin = self._registered_plugins[name]
            if hasattr(plugin, 'cleanup'):
                plugin.cleanup()

            # 移除插件
            del self._registered_plugins[name]
            del self._plugin_priorities[name]
            del self._plugin_weights[name]

            self.log_manager.info(f"✅ 成功注销情绪数据源插件: {name}")
            return True

        except Exception as e:
            self.log_manager.error(f"❌ 注销插件 {name} 失败: {e}")
            return False

    def get_sentiment_data(self, force_refresh: bool = False) -> SentimentResponse:
        """
        获取聚合的情绪数据

        Args:
            force_refresh: 是否强制刷新（忽略缓存）

        Returns:
            SentimentResponse: 聚合的情绪数据响应
        """
        try:
            # 检查缓存
            if not force_refresh and self._is_cache_valid():
                self.log_manager.info("📋 使用缓存的情绪数据")
                cached_response = self._cached_response
                cached_response.cache_used = True
                return cached_response

            self.log_manager.info("🔄 开始获取最新情绪数据...")

            # 并发获取各插件数据
            plugin_responses = self._fetch_from_all_plugins()

            # 聚合数据
            aggregated_response = self._aggregate_responses(plugin_responses)

            # 更新缓存
            self._cached_response = aggregated_response
            self._cache_timestamp = datetime.now()

            # 发送数据更新信号
            self.data_updated.emit(aggregated_response)

            self.log_manager.info(f"✅ 情绪数据获取完成，共 {len(aggregated_response.data)} 个指标")
            return aggregated_response

        except Exception as e:
            self.log_manager.error(f"❌ 获取情绪数据失败: {e}")
            return SentimentResponse(
                success=False,
                error_message=f"获取情绪数据失败: {str(e)}",
                update_time=datetime.now()
            )

    def get_available_plugins(self) -> List[str]:
        """获取已注册的插件列表"""
        return list(self._registered_plugins.keys())

    def get_plugin_status(self, name: str) -> Dict[str, Any]:
        """
        获取插件状态

        Args:
            name: 插件名称

        Returns:
            Dict[str, Any]: 插件状态信息
        """
        if name not in self._registered_plugins:
            return {"status": "not_registered"}

        plugin = self._registered_plugins[name]

        return {
            "status": "registered",
            "priority": self._plugin_priorities.get(name, 100),
            "weight": self._plugin_weights.get(name, 1.0),
            "available_indicators": plugin.get_available_indicators() if hasattr(plugin, 'get_available_indicators') else []
        }

    def _discover_sentiment_plugins(self) -> None:
        """发现并注册情绪数据源插件"""
        try:
            if not self.plugin_manager:
                self.log_manager.warning("⚠️ 插件管理器未设置，跳过自动发现")
                return

            # 从插件管理器获取情绪数据源插件
            from plugins.plugin_interface import PluginType

            sentiment_plugins = self.plugin_manager.get_plugins_by_type(PluginType.DATA_SOURCE)

            for plugin_name, plugin_instance in sentiment_plugins.items():
                if isinstance(plugin_instance, ISentimentDataSource):
                    # 设置默认优先级和权重
                    priority = 100
                    weight = 1.0

                    # 为特定插件设置特殊权重
                    if 'akshare' in plugin_name.lower():
                        priority = 10  # 高优先级
                        weight = 1.0

                    self.register_plugin(plugin_name, plugin_instance, priority, weight)

        except Exception as e:
            self.log_manager.error(f"❌ 发现情绪数据源插件失败: {e}")

    def _fetch_from_all_plugins(self) -> Dict[str, SentimentResponse]:
        """并发从所有插件获取数据"""
        plugin_responses = {}

        # 按优先级排序插件
        sorted_plugins = sorted(
            self._registered_plugins.items(),
            key=lambda x: self._plugin_priorities.get(x[0], 100)
        )

        # 提交并发任务
        future_to_plugin = {}
        for plugin_name, plugin in sorted_plugins:
            future = self._executor.submit(self._fetch_from_plugin, plugin_name, plugin)
            future_to_plugin[future] = plugin_name

        # 收集结果
        for future in as_completed(future_to_plugin, timeout=self.config.plugin_timeout_seconds):
            plugin_name = future_to_plugin[future]
            try:
                response = future.result()
                plugin_responses[plugin_name] = response

                if response.success:
                    self.log_manager.info(f"✅ 从插件 {plugin_name} 获取数据成功")
                else:
                    self.log_manager.warning(f"⚠️ 插件 {plugin_name} 返回错误: {response.error_message}")

            except Exception as e:
                self.log_manager.error(f"❌ 从插件 {plugin_name} 获取数据失败: {e}")
                self.plugin_error.emit(plugin_name, str(e))

        return plugin_responses

    def _fetch_from_plugin(self, plugin_name: str, plugin: ISentimentDataSource) -> SentimentResponse:
        """从单个插件获取数据"""
        try:
            response = plugin.fetch_sentiment_data()

            # 验证数据质量
            if response.success and response.data:
                quality = plugin.validate_data_quality(response.data)
                response.data_quality = quality

                # 检查是否满足最低质量要求
                quality_levels = ['poor', 'fair', 'good', 'excellent']
                min_level_index = quality_levels.index(self.config.min_data_quality_threshold)
                current_level_index = quality_levels.index(quality) if quality in quality_levels else 0

                if current_level_index < min_level_index:
                    self.log_manager.warning(f"⚠️ 插件 {plugin_name} 数据质量不满足要求: {quality}")

            return response

        except Exception as e:
            return SentimentResponse(
                success=False,
                error_message=f"插件 {plugin_name} 执行失败: {str(e)}",
                update_time=datetime.now()
            )

    def _aggregate_responses(self, plugin_responses: Dict[str, SentimentResponse]) -> SentimentResponse:
        """聚合多个插件的响应数据"""
        try:
            # 收集成功的响应
            successful_responses = {
                name: response for name, response in plugin_responses.items()
                if response.success and response.data
            }

            if not successful_responses:
                return SentimentResponse(
                    success=False,
                    error_message="所有插件均无法提供有效数据",
                    update_time=datetime.now()
                )

            # 聚合所有数据
            all_sentiment_data = []
            data_sources = []

            for plugin_name, response in successful_responses.items():
                # 为每个数据点添加来源信息
                for sentiment_data in response.data:
                    sentiment_data.source = f"{sentiment_data.source} (via {plugin_name})"
                    all_sentiment_data.append(sentiment_data)

                data_sources.append(plugin_name)

            # 计算加权综合评分
            weighted_scores = []
            total_weight = 0.0

            for plugin_name, response in successful_responses.items():
                plugin_weight = self._plugin_weights.get(plugin_name, 1.0)
                weighted_score = response.composite_score * plugin_weight
                weighted_scores.append(weighted_score)
                total_weight += plugin_weight

            composite_score = sum(weighted_scores) / total_weight if total_weight > 0 else 0.0

            # 确定整体数据质量
            quality_scores = {'excellent': 4, 'good': 3, 'fair': 2, 'poor': 1}
            avg_quality_score = sum(
                quality_scores.get(response.data_quality, 1)
                for response in successful_responses.values()
            ) / len(successful_responses)

            if avg_quality_score >= 3.5:
                overall_quality = 'excellent'
            elif avg_quality_score >= 2.5:
                overall_quality = 'good'
            elif avg_quality_score >= 1.5:
                overall_quality = 'fair'
            else:
                overall_quality = 'poor'

            return SentimentResponse(
                success=True,
                data=all_sentiment_data,
                composite_score=composite_score,
                data_quality=overall_quality,
                update_time=datetime.now(),
                cache_used=False
            )

        except Exception as e:
            self.log_manager.error(f"❌ 聚合情绪数据失败: {e}")
            return SentimentResponse(
                success=False,
                error_message=f"聚合数据失败: {str(e)}",
                update_time=datetime.now()
            )

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cached_response or not self._cache_timestamp:
            return False

        cache_duration = timedelta(minutes=self.config.cache_duration_minutes)
        return datetime.now() - self._cache_timestamp < cache_duration

    def _start_auto_refresh(self) -> None:
        """启动自动刷新"""
        if self.config.auto_refresh_interval_minutes > 0:
            interval_ms = self.config.auto_refresh_interval_minutes * 60 * 1000
            self._refresh_timer.start(interval_ms)
            self.log_manager.info(f"🔄 启动自动刷新，间隔 {self.config.auto_refresh_interval_minutes} 分钟")

    def _auto_refresh(self) -> None:
        """自动刷新数据"""
        try:
            self.log_manager.info("⏰ 执行自动刷新...")
            self.get_sentiment_data(force_refresh=True)
        except Exception as e:
            self.log_manager.error(f"❌ 自动刷新失败: {e}")

    def update_config(self, config: SentimentDataServiceConfig) -> None:
        """更新服务配置"""
        self.config = config

        # 重新配置自动刷新
        if self.config.enable_auto_refresh:
            self._refresh_timer.stop()
            self._start_auto_refresh()
        else:
            self._refresh_timer.stop()

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'is_initialized': self._is_initialized,
            'is_running': self._is_running,
            'registered_plugins': len(self._registered_plugins),
            'cache_valid': self._is_cache_valid(),
            'last_update': self._cache_timestamp.isoformat() if self._cache_timestamp else None,
            'auto_refresh_enabled': self.config.enable_auto_refresh,
            'auto_refresh_interval': self.config.auto_refresh_interval_minutes
        }
