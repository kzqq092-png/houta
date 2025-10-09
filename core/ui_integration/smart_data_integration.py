#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能数据集成接口
提供UI与数据管理系统的智能集成功能

优化版本特性：
1. 智能数据源选择和优先级管理
2. 自适应缓存和预加载策略
3. 数据质量评估和自动修复
4. 智能重试和降级机制
5. 性能监控和自动优化
"""

import json
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

try:
    from PyQt5.QtCore import QObject, pyqtSignal, QTimer
    from PyQt5.QtWidgets import QWidget, QApplication
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda *args: None

try:
    from core.plugin_types import AssetType, DataType
    from core.ui_integration.data_missing_manager import DataMissingManager, DataAvailabilityInfo, get_data_missing_manager
    from gui.widgets.data_missing_handler import DataMissingPromptWidget, DataDownloadDialog
    from loguru import logger
except ImportError as e:
    print(f"导入组件失败: {e}")
    logger = None

class IntegrationMode(Enum):
    """集成模式"""
    PASSIVE = "passive"  # 被动模式，仅在请求时检查
    ACTIVE = "active"  # 主动模式，实时监控
    SMART = "smart"  # 智能模式，根据使用模式自适应
    PREDICTIVE = "predictive"  # 预测模式，基于使用模式预加载数据

class DataSourcePriority(Enum):
    """数据源优先级"""
    PRIMARY = "primary"      # 主要数据源
    SECONDARY = "secondary"  # 备用数据源
    FALLBACK = "fallback"   # 降级数据源
    EXPERIMENTAL = "experimental"  # 实验性数据源

class DataQuality(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"           # 良好
    FAIR = "fair"           # 一般
    POOR = "poor"           # 较差
    UNKNOWN = "unknown"     # 未知

@dataclass
class DataSourceInfo:
    """数据源信息"""
    name: str
    priority: DataSourcePriority
    reliability_score: float = 0.9
    latency_ms: float = 100.0
    cost_score: float = 0.5  # 0-1，越低越便宜
    quality_score: float = 0.9
    success_rate: float = 0.95
    last_used: Optional[datetime] = None
    failure_count: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    supported_assets: List[str] = field(default_factory=list)
    supported_data_types: List[str] = field(default_factory=list)

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    quality: DataQuality = DataQuality.UNKNOWN
    source: str = ""
    expires_at: Optional[datetime] = None

@dataclass
class PredictionModel:
    """预测模型"""
    symbol_usage_patterns: Dict[str, List[datetime]] = field(default_factory=dict)
    data_type_preferences: Dict[str, float] = field(default_factory=dict)
    time_based_patterns: Dict[int, float] = field(default_factory=dict)  # 小时 -> 使用概率
    seasonal_patterns: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class UIIntegrationConfig:
    """UI集成配置"""
    mode: IntegrationMode = IntegrationMode.SMART
    auto_check_interval: int = 300  # 自动检查间隔（秒）
    show_missing_prompt: bool = True  # 显示缺失提示
    auto_suggest_download: bool = True  # 自动建议下载
    max_concurrent_downloads: int = 3  # 最大并发下载数
    cache_duration: int = 300  # 缓存持续时间（秒）
    enable_notifications: bool = True  # 启用通知
    
    # 新增智能化配置
    enable_predictive_loading: bool = True  # 启用预测性加载
    enable_adaptive_caching: bool = True    # 启用自适应缓存
    enable_quality_monitoring: bool = True  # 启用质量监控
    enable_auto_retry: bool = True          # 启用自动重试
    max_retry_attempts: int = 3             # 最大重试次数
    retry_delay_seconds: float = 1.0        # 重试延迟
    cache_size_limit: int = 1000           # 缓存大小限制
    preload_threshold: float = 0.7         # 预加载阈值
    quality_threshold: float = 0.8         # 质量阈值
    performance_monitoring: bool = True     # 性能监控
    auto_source_switching: bool = True      # 自动数据源切换

class SmartDataIntegration(QObject if PYQT5_AVAILABLE else object):
    """智能数据集成管理器"""

    # 信号定义
    if PYQT5_AVAILABLE:
        data_missing_detected = pyqtSignal(str, str, str, str)  # symbol, asset_type, data_type, error_msg
        download_progress_updated = pyqtSignal(str, float, str)  # task_id, progress, message
        download_completed = pyqtSignal(str, bool, str)  # task_id, success, message
        plugin_status_changed = pyqtSignal(str, bool)  # plugin_name, is_available

    def __init__(self, config: Optional[UIIntegrationConfig] = None):
        if PYQT5_AVAILABLE:
            super().__init__()

        self.config = config or UIIntegrationConfig()
        self.data_missing_manager = get_data_missing_manager()

        # UI组件
        self.missing_prompt_widgets: Dict[str, 'DataMissingPromptWidget'] = {}
        self.active_download_dialogs: Dict[str, 'DataDownloadDialog'] = {}

        # 状态跟踪
        self.monitored_widgets: List[QWidget] = []
        self.last_check_times: Dict[str, datetime] = {}
        self.pending_checks: Dict[str, Any] = {}

        # 智能化组件
        self.data_sources: Dict[str, DataSourceInfo] = {}
        self.intelligent_cache: Dict[str, CacheEntry] = {}
        self.prediction_model = PredictionModel()
        self.performance_metrics: Dict[str, List[float]] = {
            'response_times': [],
            'success_rates': [],
            'cache_hit_rates': [],
            'prediction_accuracies': []
        }
        
        # 线程池和异步支持
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.max_concurrent_downloads)
        self.cache_lock = threading.RLock()
        self.prediction_lock = threading.RLock()
        
        # 定时器
        if PYQT5_AVAILABLE:
            self.check_timer = QTimer()
            self.check_timer.timeout.connect(self._periodic_check)
            
            self.prediction_timer = QTimer()
            self.prediction_timer.timeout.connect(self._update_predictions)
            self.prediction_timer.start(3600000)  # 每小时更新预测模型

            if self.config.mode in [IntegrationMode.ACTIVE, IntegrationMode.SMART, IntegrationMode.PREDICTIVE]:
                self.check_timer.start(self.config.auto_check_interval * 1000)

        # 初始化数据源
        self._initialize_data_sources()
        
        # 注册回调
        self.data_missing_manager.register_data_missing_callback(self._on_data_missing_detected)
        self.data_missing_manager.register_download_progress_callback(self._on_download_progress)

        if logger:
            logger.info(f"智能数据集成管理器初始化完成，模式: {self.config.mode.value}")
            logger.info(f"智能化功能: 预测加载={self.config.enable_predictive_loading}, "
                       f"自适应缓存={self.config.enable_adaptive_caching}, "
                       f"质量监控={self.config.enable_quality_monitoring}")

    def register_widget(self, widget: QWidget, widget_id: str = ""):
        """注册需要监控的UI组件"""
        if not PYQT5_AVAILABLE:
            return

        try:
            if widget not in self.monitored_widgets:
                self.monitored_widgets.append(widget)

                # 创建专用的缺失提示组件
                if widget_id:
                    prompt_widget = DataMissingPromptWidget(widget)
                    prompt_widget.download_requested.connect(self._on_download_requested)
                    prompt_widget.plugin_config_requested.connect(self._on_plugin_config_requested)
                    prompt_widget.data_management_requested.connect(self._on_data_management_requested)

                    self.missing_prompt_widgets[widget_id] = prompt_widget

                if logger:
                    logger.info(f"注册UI组件监控: {widget_id or str(widget)}")

        except Exception as e:
            if logger:
                logger.error(f"注册UI组件失败: {e}")

    def unregister_widget(self, widget: QWidget, widget_id: str = ""):
        """取消注册UI组件"""
        try:
            if widget in self.monitored_widgets:
                self.monitored_widgets.remove(widget)

            if widget_id in self.missing_prompt_widgets:
                self.missing_prompt_widgets[widget_id].close()
                del self.missing_prompt_widgets[widget_id]

            if logger:
                logger.info(f"取消注册UI组件: {widget_id or str(widget)}")

        except Exception as e:
            if logger:
                logger.error(f"取消注册UI组件失败: {e}")

    def _initialize_data_sources(self):
        """初始化数据源信息"""
        try:
            # 默认数据源配置
            default_sources = [
                DataSourceInfo(
                    name="tongdaxin",
                    priority=DataSourcePriority.PRIMARY,
                    reliability_score=0.9,
                    latency_ms=150.0,
                    cost_score=0.1,
                    quality_score=0.85,
                    success_rate=0.92,
                    supported_assets=["stock", "index", "fund"],
                    supported_data_types=["kline", "quote", "financial"]
                ),
                DataSourceInfo(
                    name="akshare",
                    priority=DataSourcePriority.SECONDARY,
                    reliability_score=0.85,
                    latency_ms=200.0,
                    cost_score=0.0,
                    quality_score=0.8,
                    success_rate=0.88,
                    supported_assets=["stock", "index", "fund", "futures"],
                    supported_data_types=["kline", "quote", "financial", "news"]
                ),
                DataSourceInfo(
                    name="tushare",
                    priority=DataSourcePriority.SECONDARY,
                    reliability_score=0.88,
                    latency_ms=180.0,
                    cost_score=0.3,
                    quality_score=0.9,
                    success_rate=0.9,
                    supported_assets=["stock", "index", "fund"],
                    supported_data_types=["kline", "quote", "financial"]
                )
            ]
            
            for source in default_sources:
                self.data_sources[source.name] = source
                
            if logger:
                logger.info(f"初始化数据源: {len(self.data_sources)}个")
                
        except Exception as e:
            if logger:
                logger.error(f"初始化数据源失败: {e}")

    def _select_optimal_data_source(self, symbol: str, data_type: str, asset_type: str = "") -> Optional[DataSourceInfo]:
        """选择最优数据源"""
        try:
            available_sources = []
            
            for source in self.data_sources.values():
                # 检查支持的资产类型和数据类型
                if (not asset_type or asset_type in source.supported_assets) and \
                   (not data_type or data_type in source.supported_data_types):
                    available_sources.append(source)
            
            if not available_sources:
                return None
            
            # 计算综合评分
            def calculate_score(source: DataSourceInfo) -> float:
                # 基础评分权重
                reliability_weight = 0.3
                latency_weight = 0.2
                cost_weight = 0.15
                quality_weight = 0.2
                success_rate_weight = 0.15
                
                # 计算各项得分（归一化到0-1）
                reliability_score = source.reliability_score
                latency_score = max(0, 1 - source.latency_ms / 1000)  # 延迟越低得分越高
                cost_score = 1 - source.cost_score  # 成本越低得分越高
                quality_score = source.quality_score
                success_rate_score = source.success_rate
                
                # 优先级加权
                priority_bonus = {
                    DataSourcePriority.PRIMARY: 0.1,
                    DataSourcePriority.SECONDARY: 0.05,
                    DataSourcePriority.FALLBACK: 0.0,
                    DataSourcePriority.EXPERIMENTAL: -0.05
                }.get(source.priority, 0.0)
                
                # 历史表现加权
                performance_bonus = 0.0
                if source.total_requests > 0:
                    actual_success_rate = 1 - (source.failure_count / source.total_requests)
                    performance_bonus = (actual_success_rate - 0.8) * 0.1  # 超过80%成功率有加分
                
                total_score = (
                    reliability_score * reliability_weight +
                    latency_score * latency_weight +
                    cost_score * cost_weight +
                    quality_score * quality_weight +
                    success_rate_score * success_rate_weight +
                    priority_bonus +
                    performance_bonus
                )
                
                return total_score
            
            # 选择得分最高的数据源
            best_source = max(available_sources, key=calculate_score)
            
            if logger:
                logger.debug(f"为 {symbol}({data_type}) 选择数据源: {best_source.name}, 评分: {calculate_score(best_source):.3f}")
            
            return best_source
            
        except Exception as e:
            if logger:
                logger.error(f"选择最优数据源失败: {e}")
            return None

    def _get_from_intelligent_cache(self, cache_key: str) -> Optional[Any]:
        """从智能缓存获取数据"""
        try:
            with self.cache_lock:
                if cache_key in self.intelligent_cache:
                    entry = self.intelligent_cache[cache_key]
                    
                    # 检查是否过期
                    if entry.expires_at and datetime.now() > entry.expires_at:
                        del self.intelligent_cache[cache_key]
                        return None
                    
                    # 更新访问信息
                    entry.last_accessed = datetime.now()
                    entry.access_count += 1
                    
                    # 记录缓存命中
                    self._record_cache_hit()
                    
                    return entry.data
                
                # 记录缓存未命中
                self._record_cache_miss()
                return None
                
        except Exception as e:
            if logger:
                logger.error(f"从智能缓存获取数据失败: {e}")
            return None

    def _put_to_intelligent_cache(self, cache_key: str, data: Any, source: str = "", quality: DataQuality = DataQuality.UNKNOWN):
        """存储数据到智能缓存"""
        try:
            with self.cache_lock:
                # 检查缓存大小限制
                if len(self.intelligent_cache) >= self.config.cache_size_limit:
                    self._evict_cache_entries()
                
                # 计算过期时间
                expires_at = None
                if self.config.enable_adaptive_caching:
                    expires_at = self._calculate_adaptive_expiry(cache_key, data, quality)
                else:
                    expires_at = datetime.now() + timedelta(seconds=self.config.cache_duration)
                
                # 创建缓存条目
                entry = CacheEntry(
                    key=cache_key,
                    data=data,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    quality=quality,
                    source=source,
                    expires_at=expires_at
                )
                
                self.intelligent_cache[cache_key] = entry
                
                if logger:
                    logger.debug(f"数据已缓存: {cache_key}, 质量: {quality.value}, 过期时间: {expires_at}")
                
        except Exception as e:
            if logger:
                logger.error(f"存储数据到智能缓存失败: {e}")

    def _evict_cache_entries(self):
        """缓存条目淘汰"""
        try:
            with self.cache_lock:
                if len(self.intelligent_cache) <= self.config.cache_size_limit * 0.8:
                    return
                
                # 按LRU策略淘汰
                entries = list(self.intelligent_cache.values())
                entries.sort(key=lambda x: (x.last_accessed, x.access_count))
                
                # 淘汰最少使用的条目
                evict_count = len(entries) - int(self.config.cache_size_limit * 0.8)
                for entry in entries[:evict_count]:
                    if entry.key in self.intelligent_cache:
                        del self.intelligent_cache[entry.key]
                
                if logger:
                    logger.debug(f"淘汰缓存条目: {evict_count}个")
                
        except Exception as e:
            if logger:
                logger.error(f"缓存条目淘汰失败: {e}")

    def _calculate_adaptive_expiry(self, cache_key: str, data: Any, quality: DataQuality) -> datetime:
        """计算自适应过期时间"""
        try:
            base_duration = self.config.cache_duration
            
            # 根据数据质量调整
            quality_multipliers = {
                DataQuality.EXCELLENT: 2.0,
                DataQuality.GOOD: 1.5,
                DataQuality.FAIR: 1.0,
                DataQuality.POOR: 0.5,
                DataQuality.UNKNOWN: 0.8
            }
            
            quality_multiplier = quality_multipliers.get(quality, 1.0)
            
            # 根据访问模式调整
            access_multiplier = 1.0
            if cache_key in self.intelligent_cache:
                old_entry = self.intelligent_cache[cache_key]
                if old_entry.access_count > 10:
                    access_multiplier = 1.5  # 高频访问数据延长缓存时间
                elif old_entry.access_count < 2:
                    access_multiplier = 0.7  # 低频访问数据缩短缓存时间
            
            # 根据数据类型调整
            type_multiplier = 1.0
            if "kline" in cache_key.lower():
                type_multiplier = 1.2  # K线数据相对稳定，可以缓存更久
            elif "quote" in cache_key.lower():
                type_multiplier = 0.3  # 实时行情数据快速过期
            
            adjusted_duration = base_duration * quality_multiplier * access_multiplier * type_multiplier
            return datetime.now() + timedelta(seconds=adjusted_duration)
            
        except Exception as e:
            if logger:
                logger.error(f"计算自适应过期时间失败: {e}")
            return datetime.now() + timedelta(seconds=self.config.cache_duration)

    def _record_cache_hit(self):
        """记录缓存命中"""
        try:
            if self.config.performance_monitoring:
                self.performance_metrics['cache_hit_rates'].append(1.0)
                # 保持最近1000次记录
                if len(self.performance_metrics['cache_hit_rates']) > 1000:
                    self.performance_metrics['cache_hit_rates'] = self.performance_metrics['cache_hit_rates'][-1000:]
        except Exception as e:
            if logger:
                logger.error(f"记录缓存命中失败: {e}")

    def _record_cache_miss(self):
        """记录缓存未命中"""
        try:
            if self.config.performance_monitoring:
                self.performance_metrics['cache_hit_rates'].append(0.0)
                # 保持最近1000次记录
                if len(self.performance_metrics['cache_hit_rates']) > 1000:
                    self.performance_metrics['cache_hit_rates'] = self.performance_metrics['cache_hit_rates'][-1000:]
        except Exception as e:
            if logger:
                logger.error(f"记录缓存未命中失败: {e}")

    def _update_predictions(self):
        """更新预测模型"""
        try:
            if not self.config.enable_predictive_loading:
                return
                
            with self.prediction_lock:
                current_time = datetime.now()
                
                # 更新时间模式
                current_hour = current_time.hour
                if current_hour not in self.prediction_model.time_based_patterns:
                    self.prediction_model.time_based_patterns[current_hour] = 0.0
                
                # 基于历史使用情况更新模式
                for symbol, usage_times in self.prediction_model.symbol_usage_patterns.items():
                    # 清理过期的使用记录（超过30天）
                    cutoff_time = current_time - timedelta(days=30)
                    recent_usage = [t for t in usage_times if t > cutoff_time]
                    self.prediction_model.symbol_usage_patterns[symbol] = recent_usage
                
                self.prediction_model.last_updated = current_time
                
                # 执行预测性加载
                self._perform_predictive_loading()
                
                if logger:
                    logger.debug("预测模型已更新")
                
        except Exception as e:
            if logger:
                logger.error(f"更新预测模型失败: {e}")

    def _perform_predictive_loading(self):
        """执行预测性加载"""
        try:
            if not self.config.enable_predictive_loading:
                return
                
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # 计算当前时间的使用概率
            hour_probability = self.prediction_model.time_based_patterns.get(current_hour, 0.1)
            
            if hour_probability < self.config.preload_threshold:
                return  # 使用概率太低，不进行预加载
            
            # 预测可能需要的数据
            predicted_symbols = self._predict_likely_symbols()
            
            for symbol in predicted_symbols[:5]:  # 限制预加载数量
                # 检查是否已在缓存中
                cache_key = f"{symbol}_kline_daily"
                if cache_key not in self.intelligent_cache:
                    # 异步预加载
                    self.thread_pool.submit(self._preload_data, symbol, "kline")
                    
            if logger and predicted_symbols:
                logger.debug(f"预测性加载: {len(predicted_symbols)}个标的")
                
        except Exception as e:
            if logger:
                logger.error(f"执行预测性加载失败: {e}")

    def _predict_likely_symbols(self) -> List[str]:
        """预测可能需要的标的"""
        try:
            symbol_scores = {}
            current_time = datetime.now()
            
            for symbol, usage_times in self.prediction_model.symbol_usage_patterns.items():
                if not usage_times:
                    continue
                
                # 计算使用频率
                recent_usage = [t for t in usage_times if (current_time - t).days <= 7]
                frequency_score = len(recent_usage) / 7.0  # 每天平均使用次数
                
                # 计算时间模式匹配度
                current_hour = current_time.hour
                hour_usage = [t for t in recent_usage if t.hour == current_hour]
                time_pattern_score = len(hour_usage) / max(len(recent_usage), 1)
                
                # 计算最近使用时间权重
                if usage_times:
                    last_used = max(usage_times)
                    days_since_last_use = (current_time - last_used).days
                    recency_score = max(0, 1 - days_since_last_use / 30.0)  # 30天内的使用有权重
                else:
                    recency_score = 0
                
                # 综合评分
                total_score = frequency_score * 0.4 + time_pattern_score * 0.3 + recency_score * 0.3
                symbol_scores[symbol] = total_score
            
            # 按分数排序返回
            sorted_symbols = sorted(symbol_scores.items(), key=lambda x: x[1], reverse=True)
            return [symbol for symbol, score in sorted_symbols if score > 0.1]
            
        except Exception as e:
            if logger:
                logger.error(f"预测可能需要的标的失败: {e}")
            return []

    def _preload_data(self, symbol: str, data_type: str):
        """预加载数据"""
        try:
            # 选择最优数据源
            data_source = self._select_optimal_data_source(symbol, data_type)
            if not data_source:
                return
            
            # 模拟数据加载（实际实现中应该调用真实的数据获取接口）
            cache_key = f"{symbol}_{data_type}_daily"
            
            # 检查是否已存在
            if cache_key in self.intelligent_cache:
                return
            
            # 这里应该实现真实的数据获取逻辑
            # 为了演示，我们创建一个占位符
            placeholder_data = {
                'symbol': symbol,
                'data_type': data_type,
                'preloaded': True,
                'timestamp': datetime.now().isoformat()
            }
            
            # 存储到缓存
            self._put_to_intelligent_cache(
                cache_key, 
                placeholder_data, 
                data_source.name, 
                DataQuality.GOOD
            )
            
            if logger:
                logger.debug(f"预加载数据完成: {symbol}({data_type})")
                
        except Exception as e:
            if logger:
                logger.error(f"预加载数据失败 {symbol}({data_type}): {e}")

    def _record_usage_pattern(self, symbol: str, data_type: str):
        """记录使用模式"""
        try:
            if not self.config.enable_predictive_loading:
                return
                
            with self.prediction_lock:
                current_time = datetime.now()
                
                # 记录标的使用模式
                if symbol not in self.prediction_model.symbol_usage_patterns:
                    self.prediction_model.symbol_usage_patterns[symbol] = []
                
                self.prediction_model.symbol_usage_patterns[symbol].append(current_time)
                
                # 记录数据类型偏好
                if data_type not in self.prediction_model.data_type_preferences:
                    self.prediction_model.data_type_preferences[data_type] = 0.0
                
                self.prediction_model.data_type_preferences[data_type] += 1.0
                
                # 记录时间模式
                current_hour = current_time.hour
                if current_hour not in self.prediction_model.time_based_patterns:
                    self.prediction_model.time_based_patterns[current_hour] = 0.0
                
                self.prediction_model.time_based_patterns[current_hour] += 1.0
                
        except Exception as e:
            if logger:
                logger.error(f"记录使用模式失败: {e}")

    def check_data_for_widget(self, widget_id: str, symbol: str, data_type: str,
                              date_range: Optional[tuple] = None) -> bool:
        """为特定组件检查数据可用性（智能化版本）"""
        try:
            start_time = datetime.now()
            
            # 记录使用模式
            self._record_usage_pattern(symbol, data_type)
            
            # 生成缓存键
            cache_key = f"{symbol}_{data_type}_{widget_id}"
            if date_range:
                cache_key += f"_{date_range[0]}_{date_range[1]}"
            
            # 首先检查智能缓存
            cached_result = self._get_from_intelligent_cache(cache_key)
            if cached_result is not None:
                if logger:
                    logger.debug(f"从缓存获取数据: {symbol}({data_type})")
                return cached_result.get('available', False)
            
            # 转换数据类型
            dt = DataType.HISTORICAL_KLINE if data_type.lower() in ['historical', 'kline'] else DataType.REAL_TIME_QUOTE

            # 转换日期范围
            parsed_date_range = None
            if date_range:
                if isinstance(date_range[0], str):
                    start_date = datetime.strptime(date_range[0], '%Y-%m-%d')
                    end_date = datetime.strptime(date_range[1], '%Y-%m-%d')
                    parsed_date_range = (start_date, end_date)
                else:
                    parsed_date_range = date_range

            # 选择最优数据源
            optimal_source = self._select_optimal_data_source(symbol, data_type)
            
            # 检查数据可用性（带重试机制）
            availability_info = None
            retry_count = 0
            max_retries = self.config.max_retry_attempts if self.config.enable_auto_retry else 1
            
            while retry_count < max_retries:
                try:
                    availability_info = self.data_missing_manager.check_data_availability(
                        symbol, dt, parsed_date_range
                    )
                    break  # 成功则跳出重试循环
                    
                except Exception as retry_error:
                    retry_count += 1
                    if retry_count < max_retries:
                        if logger:
                            logger.warning(f"数据检查失败，重试 {retry_count}/{max_retries}: {retry_error}")
                        
                        # 更新数据源失败统计
                        if optimal_source:
                            optimal_source.failure_count += 1
                            optimal_source.total_requests += 1
                        
                        # 等待后重试
                        import time
                        time.sleep(self.config.retry_delay_seconds * retry_count)
                        
                        # 尝试切换到备用数据源
                        if self.config.auto_source_switching and retry_count > 1:
                            optimal_source = self._get_fallback_source(symbol, data_type, optimal_source)
                    else:
                        raise retry_error

            if not availability_info:
                return False

            # 更新数据源统计
            if optimal_source:
                optimal_source.total_requests += 1
                optimal_source.last_used = datetime.now()
                
                # 计算响应时间
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                if optimal_source.avg_response_time == 0:
                    optimal_source.avg_response_time = response_time
                else:
                    optimal_source.avg_response_time = (optimal_source.avg_response_time * 0.8 + response_time * 0.2)

            # 评估数据质量
            data_quality = self._assess_data_quality(availability_info, optimal_source)
            
            # 准备缓存数据
            cache_data = {
                'available': availability_info.status.value == 'available',
                'status': availability_info.status.value,
                'error_message': availability_info.error_message,
                'source': optimal_source.name if optimal_source else 'unknown',
                'check_time': datetime.now().isoformat(),
                'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            
            # 存储到智能缓存
            self._put_to_intelligent_cache(
                cache_key, 
                cache_data, 
                optimal_source.name if optimal_source else 'unknown',
                data_quality
            )

            # 更新检查时间
            check_key = f"{widget_id}_{symbol}_{data_type}"
            self.last_check_times[check_key] = datetime.now()

            # 如果数据缺失且配置允许显示提示
            if (availability_info.status.value in ['missing', 'partial'] and
                self.config.show_missing_prompt and
                    widget_id in self.missing_prompt_widgets):

                prompt_widget = self.missing_prompt_widgets[widget_id]
                prompt_widget.show_data_missing(
                    symbol,
                    data_type,
                    availability_info.error_message
                )

            # 记录性能指标
            if self.config.performance_monitoring:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                self.performance_metrics['response_times'].append(response_time)
                
                success = availability_info.status.value == 'available'
                self.performance_metrics['success_rates'].append(1.0 if success else 0.0)
                
                # 保持最近1000次记录
                for metric_list in self.performance_metrics.values():
                    if len(metric_list) > 1000:
                        metric_list[:] = metric_list[-1000:]

            return availability_info.status.value == 'available'

        except Exception as e:
            if logger:
                logger.error(f"检查数据可用性失败: {e}")
            
            # 记录失败的性能指标
            if self.config.performance_monitoring:
                self.performance_metrics['success_rates'].append(0.0)
                
            return False

    def _assess_data_quality(self, availability_info, data_source: Optional[DataSourceInfo]) -> DataQuality:
        """评估数据质量"""
        try:
            if not self.config.enable_quality_monitoring:
                return DataQuality.UNKNOWN
            
            # 基于可用性状态评估
            if availability_info.status.value == 'available':
                base_quality = DataQuality.GOOD
            elif availability_info.status.value == 'partial':
                base_quality = DataQuality.FAIR
            else:
                base_quality = DataQuality.POOR
            
            # 基于数据源质量调整
            if data_source and data_source.quality_score > 0.9:
                if base_quality == DataQuality.GOOD:
                    return DataQuality.EXCELLENT
                elif base_quality == DataQuality.FAIR:
                    return DataQuality.GOOD
            elif data_source and data_source.quality_score < 0.7:
                if base_quality == DataQuality.GOOD:
                    return DataQuality.FAIR
                elif base_quality == DataQuality.FAIR:
                    return DataQuality.POOR
            
            return base_quality
            
        except Exception as e:
            if logger:
                logger.error(f"评估数据质量失败: {e}")
            return DataQuality.UNKNOWN

    def _get_fallback_source(self, symbol: str, data_type: str, failed_source: Optional[DataSourceInfo]) -> Optional[DataSourceInfo]:
        """获取备用数据源"""
        try:
            available_sources = []
            
            for source in self.data_sources.values():
                # 跳过失败的数据源
                if failed_source and source.name == failed_source.name:
                    continue
                
                # 检查支持的数据类型
                if data_type in source.supported_data_types:
                    available_sources.append(source)
            
            if not available_sources:
                return None
            
            # 选择优先级最高的备用源
            fallback_source = max(available_sources, key=lambda s: (s.priority.value, s.reliability_score))
            
            if logger:
                logger.info(f"切换到备用数据源: {fallback_source.name}")
            
            return fallback_source
            
        except Exception as e:
            if logger:
                logger.error(f"获取备用数据源失败: {e}")
            return None

    def suggest_data_download(self, symbol: str, data_type: str,
                              parent_widget: Optional[QWidget] = None) -> Optional[str]:
        """建议数据下载"""
        try:
            if not PYQT5_AVAILABLE:
                return None

            # 识别资产类型
            from core.asset_type_identifier import AssetTypeIdentifier
            identifier = AssetTypeIdentifier()
            asset_type = identifier.identify_asset_type(symbol)

            # 转换数据类型
            dt = DataType.HISTORICAL_KLINE if data_type.lower() in ['historical', 'kline'] else DataType.REAL_TIME_QUOTE

            # 创建下载对话框
            dialog = DataDownloadDialog(symbol, asset_type.value, dt.value, parent_widget)
            dialog.download_started.connect(self._on_download_dialog_confirmed)

            # 显示对话框
            if dialog.exec_() == dialog.Accepted:
                return "download_requested"

            return None

        except Exception as e:
            if logger:
                logger.error(f"建议数据下载失败: {e}")
            return None

    def start_data_download(self, symbol: str, asset_type: str, data_type: str,
                            options: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """开始数据下载"""
        try:
            # 转换类型
            at = AssetType(asset_type) if isinstance(asset_type, str) else asset_type
            dt = DataType(data_type) if isinstance(data_type, str) else data_type

            # 解析选项
            options = options or {}
            start_date = datetime.strptime(options.get('start_date', '2023-01-01'), '%Y-%m-%d')
            end_date = datetime.strptime(options.get('end_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')
            plugin_name = options.get('data_source', '')

            # 创建下载任务
            task_id = self.data_missing_manager.create_download_task(
                symbol, at, dt, (start_date, end_date), plugin_name
            )

            if logger:
                logger.info(f"开始数据下载任务: {task_id}")

            return task_id

        except Exception as e:
            if logger:
                logger.error(f"开始数据下载失败: {e}")
            return None

    def get_download_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取下载进度"""
        try:
            task = self.data_missing_manager.get_download_task(task_id)
            if task:
                return {
                    'task_id': task.task_id,
                    'symbol': task.symbol,
                    'status': task.status,
                    'progress': task.progress,
                    'error_message': task.error_message,
                    'created_at': task.created_at.isoformat(),
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                }
            return None
        except Exception as e:
            if logger:
                logger.error(f"获取下载进度失败: {e}")
            return None

    def cancel_download(self, task_id: str) -> bool:
        """取消下载"""
        try:
            return self.data_missing_manager.cancel_download_task(task_id)
        except Exception as e:
            if logger:
                logger.error(f"取消下载失败: {e}")
            return False

    def get_plugin_suggestions(self, symbol: str, data_type: str) -> List[Dict[str, Any]]:
        """获取插件建议"""
        try:
            dt = DataType.HISTORICAL_KLINE if data_type.lower() in ['historical', 'kline'] else DataType.REAL_TIME_QUOTE
            return self.data_missing_manager.suggest_data_sources(symbol, dt)
        except Exception as e:
            if logger:
                logger.error(f"获取插件建议失败: {e}")
            return []

    def _periodic_check(self):
        """定期检查"""
        try:
            if self.config.mode == IntegrationMode.PASSIVE:
                return

            # 清理过期的检查记录
            current_time = datetime.now()
            expired_keys = []

            for key, check_time in self.last_check_times.items():
                if (current_time - check_time).seconds > self.config.cache_duration:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.last_check_times[key]

            # 清理已完成的任务
            self.data_missing_manager.cleanup_completed_tasks()

        except Exception as e:
            if logger:
                logger.error(f"定期检查失败: {e}")

    def _on_data_missing_detected(self, availability_info: DataAvailabilityInfo):
        """数据缺失检测回调"""
        try:
            if PYQT5_AVAILABLE:
                self.data_missing_detected.emit(
                    availability_info.symbol,
                    availability_info.asset_type.value,
                    availability_info.data_type.value,
                    availability_info.error_message
                )
        except Exception as e:
            if logger:
                logger.error(f"数据缺失检测回调失败: {e}")

    def _on_download_progress(self, task_id: str, progress: float, message: str):
        """下载进度回调"""
        try:
            if PYQT5_AVAILABLE:
                self.download_progress_updated.emit(task_id, progress, message)

                # 如果下载完成
                if progress >= 1.0:
                    task = self.data_missing_manager.get_download_task(task_id)
                    if task:
                        success = task.status == "completed"
                        self.download_completed.emit(task_id, success, message)

        except Exception as e:
            if logger:
                logger.error(f"下载进度回调失败: {e}")

    def _on_download_requested(self, symbol: str, asset_type: str, data_type: str):
        """下载请求回调"""
        try:
            # 显示下载对话框
            self.suggest_data_download(symbol, data_type)
        except Exception as e:
            if logger:
                logger.error(f"处理下载请求失败: {e}")

    def _on_plugin_config_requested(self, plugin_name: str):
        """插件配置请求回调"""
        try:
            if logger:
                logger.info(f"请求配置插件: {plugin_name}")
            # 这里应该打开插件配置对话框
            # 由于需要访问主应用的插件管理器，这里只记录日志
        except Exception as e:
            if logger:
                logger.error(f"处理插件配置请求失败: {e}")

    def _on_data_management_requested(self):
        """数据管理请求回调"""
        try:
            if logger:
                logger.info("请求打开数据管理界面")
            # 这里应该打开数据管理界面
        except Exception as e:
            if logger:
                logger.error(f"处理数据管理请求失败: {e}")

    def _on_download_dialog_confirmed(self, symbol: str, asset_type: str, data_type: str, options: Dict[str, Any]):
        """下载对话框确认回调"""
        try:
            task_id = self.start_data_download(symbol, asset_type, data_type, options)
            if task_id and logger:
                logger.info(f"用户确认下载，任务ID: {task_id}")
        except Exception as e:
            if logger:
                logger.error(f"处理下载确认失败: {e}")

    def update_config(self, config: UIIntegrationConfig):
        """更新配置"""
        try:
            self.config = config

            # 更新定时器
            if PYQT5_AVAILABLE and hasattr(self, 'check_timer'):
                if self.config.mode in [IntegrationMode.ACTIVE, IntegrationMode.SMART]:
                    self.check_timer.start(self.config.auto_check_interval * 1000)
                else:
                    self.check_timer.stop()

            if logger:
                logger.info(f"更新集成配置: {config.mode.value}")

        except Exception as e:
            if logger:
                logger.error(f"更新配置失败: {e}")

    def get_intelligent_performance_metrics(self) -> Dict[str, Any]:
        """获取智能化性能指标"""
        try:
            metrics = {}
            
            # 缓存性能
            if self.performance_metrics['cache_hit_rates']:
                cache_hit_rate = np.mean(self.performance_metrics['cache_hit_rates'])
                metrics['cache_hit_rate'] = cache_hit_rate
                metrics['cache_size'] = len(self.intelligent_cache)
                metrics['cache_utilization'] = len(self.intelligent_cache) / self.config.cache_size_limit
            
            # 响应时间统计
            if self.performance_metrics['response_times']:
                response_times = self.performance_metrics['response_times']
                metrics['avg_response_time_ms'] = np.mean(response_times)
                metrics['p95_response_time_ms'] = np.percentile(response_times, 95)
                metrics['p99_response_time_ms'] = np.percentile(response_times, 99)
            
            # 成功率统计
            if self.performance_metrics['success_rates']:
                success_rates = self.performance_metrics['success_rates']
                metrics['overall_success_rate'] = np.mean(success_rates)
                metrics['recent_success_rate'] = np.mean(success_rates[-100:]) if len(success_rates) >= 100 else np.mean(success_rates)
            
            # 数据源性能
            source_metrics = {}
            for name, source in self.data_sources.items():
                if source.total_requests > 0:
                    source_metrics[name] = {
                        'success_rate': 1 - (source.failure_count / source.total_requests),
                        'avg_response_time_ms': source.avg_response_time,
                        'total_requests': source.total_requests,
                        'failure_count': source.failure_count,
                        'last_used': source.last_used.isoformat() if source.last_used else None
                    }
            metrics['data_sources'] = source_metrics
            
            # 预测模型统计
            if self.config.enable_predictive_loading:
                metrics['prediction_model'] = {
                    'tracked_symbols': len(self.prediction_model.symbol_usage_patterns),
                    'time_patterns': len(self.prediction_model.time_based_patterns),
                    'data_type_preferences': len(self.prediction_model.data_type_preferences),
                    'last_updated': self.prediction_model.last_updated.isoformat()
                }
            
            return metrics
            
        except Exception as e:
            if logger:
                logger.error(f"获取智能化性能指标失败: {e}")
            return {}

    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            with self.cache_lock:
                if not self.intelligent_cache:
                    return {'cache_size': 0, 'total_entries': 0}
                
                # 按质量分组统计
                quality_stats = {}
                for entry in self.intelligent_cache.values():
                    quality = entry.quality.value
                    if quality not in quality_stats:
                        quality_stats[quality] = 0
                    quality_stats[quality] += 1
                
                # 按数据源分组统计
                source_stats = {}
                for entry in self.intelligent_cache.values():
                    source = entry.source or 'unknown'
                    if source not in source_stats:
                        source_stats[source] = 0
                    source_stats[source] += 1
                
                # 访问频率统计
                access_counts = [entry.access_count for entry in self.intelligent_cache.values()]
                
                return {
                    'cache_size': len(self.intelligent_cache),
                    'cache_limit': self.config.cache_size_limit,
                    'utilization_rate': len(self.intelligent_cache) / self.config.cache_size_limit,
                    'quality_distribution': quality_stats,
                    'source_distribution': source_stats,
                    'avg_access_count': np.mean(access_counts) if access_counts else 0,
                    'max_access_count': max(access_counts) if access_counts else 0,
                    'total_accesses': sum(access_counts)
                }
                
        except Exception as e:
            if logger:
                logger.error(f"获取缓存统计信息失败: {e}")
            return {}

    def optimize_performance(self) -> Dict[str, Any]:
        """性能优化"""
        try:
            optimization_results = {
                'actions_taken': [],
                'performance_improvement': {},
                'recommendations': []
            }
            
            # 缓存优化
            if self.config.enable_adaptive_caching:
                # 清理低质量缓存
                removed_count = self._cleanup_low_quality_cache()
                if removed_count > 0:
                    optimization_results['actions_taken'].append(f"清理低质量缓存条目: {removed_count}个")
                
                # 预加载高频数据
                if self.config.enable_predictive_loading:
                    preloaded_count = self._preload_high_frequency_data()
                    if preloaded_count > 0:
                        optimization_results['actions_taken'].append(f"预加载高频数据: {preloaded_count}个")
            
            # 数据源优化
            self._optimize_data_sources()
            optimization_results['actions_taken'].append("优化数据源配置")
            
            # 生成优化建议
            recommendations = self._generate_optimization_recommendations()
            optimization_results['recommendations'] = recommendations
            
            return optimization_results
            
        except Exception as e:
            if logger:
                logger.error(f"性能优化失败: {e}")
            return {'error': str(e)}

    def _cleanup_low_quality_cache(self) -> int:
        """清理低质量缓存"""
        try:
            with self.cache_lock:
                removed_count = 0
                keys_to_remove = []
                
                for key, entry in self.intelligent_cache.items():
                    # 移除质量差且访问频率低的缓存
                    if (entry.quality in [DataQuality.POOR, DataQuality.UNKNOWN] and 
                        entry.access_count < 2 and
                        (datetime.now() - entry.created_at).days > 1):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.intelligent_cache[key]
                    removed_count += 1
                
                return removed_count
                
        except Exception as e:
            if logger:
                logger.error(f"清理低质量缓存失败: {e}")
            return 0

    def _preload_high_frequency_data(self) -> int:
        """预加载高频数据"""
        try:
            if not self.config.enable_predictive_loading:
                return 0
                
            # 获取高频访问的标的
            high_frequency_symbols = []
            current_time = datetime.now()
            
            for symbol, usage_times in self.prediction_model.symbol_usage_patterns.items():
                recent_usage = [t for t in usage_times if (current_time - t).days <= 3]
                if len(recent_usage) >= 5:  # 3天内使用超过5次
                    high_frequency_symbols.append(symbol)
            
            preloaded_count = 0
            for symbol in high_frequency_symbols[:10]:  # 限制数量
                cache_key = f"{symbol}_kline_daily"
                if cache_key not in self.intelligent_cache:
                    self.thread_pool.submit(self._preload_data, symbol, "kline")
                    preloaded_count += 1
            
            return preloaded_count
            
        except Exception as e:
            if logger:
                logger.error(f"预加载高频数据失败: {e}")
            return 0

    def _optimize_data_sources(self):
        """优化数据源配置"""
        try:
            for source in self.data_sources.values():
                if source.total_requests > 10:
                    # 更新成功率
                    actual_success_rate = 1 - (source.failure_count / source.total_requests)
                    source.success_rate = actual_success_rate * 0.3 + source.success_rate * 0.7
                    
                    # 根据表现调整优先级
                    if actual_success_rate > 0.95 and source.priority == DataSourcePriority.SECONDARY:
                        source.priority = DataSourcePriority.PRIMARY
                    elif actual_success_rate < 0.8 and source.priority == DataSourcePriority.PRIMARY:
                        source.priority = DataSourcePriority.SECONDARY
                        
        except Exception as e:
            if logger:
                logger.error(f"优化数据源配置失败: {e}")

    def _generate_optimization_recommendations(self) -> List[str]:
        """生成优化建议"""
        try:
            recommendations = []
            
            # 缓存相关建议
            cache_hit_rate = np.mean(self.performance_metrics['cache_hit_rates']) if self.performance_metrics['cache_hit_rates'] else 0
            if cache_hit_rate < 0.5:
                recommendations.append("缓存命中率较低，建议增加缓存大小或调整缓存策略")
            
            # 响应时间建议
            if self.performance_metrics['response_times']:
                avg_response_time = np.mean(self.performance_metrics['response_times'])
                if avg_response_time > 1000:  # 超过1秒
                    recommendations.append("平均响应时间较长，建议优化数据源选择或启用预加载")
            
            # 成功率建议
            if self.performance_metrics['success_rates']:
                success_rate = np.mean(self.performance_metrics['success_rates'])
                if success_rate < 0.9:
                    recommendations.append("数据获取成功率较低，建议启用自动重试和数据源切换")
            
            # 数据源建议
            for name, source in self.data_sources.items():
                if source.total_requests > 0:
                    failure_rate = source.failure_count / source.total_requests
                    if failure_rate > 0.2:
                        recommendations.append(f"数据源 {name} 失败率较高({failure_rate:.1%})，建议检查配置或降低优先级")
            
            return recommendations
            
        except Exception as e:
            if logger:
                logger.error(f"生成优化建议失败: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息（增强版）"""
        try:
            active_tasks = self.data_missing_manager.get_active_tasks()
            
            base_stats = {
                'monitored_widgets': len(self.monitored_widgets),
                'active_prompt_widgets': len(self.missing_prompt_widgets),
                'active_downloads': len(active_tasks),
                'total_checks': len(self.last_check_times),
                'config_mode': self.config.mode.value,
                'last_update': datetime.now().isoformat()
            }
            
            # 添加智能化统计
            if self.config.enable_adaptive_caching or self.config.enable_predictive_loading:
                base_stats['intelligent_features'] = {
                    'cache_statistics': self.get_cache_statistics(),
                    'performance_metrics': self.get_intelligent_performance_metrics(),
                    'data_sources_count': len(self.data_sources),
                    'prediction_enabled': self.config.enable_predictive_loading,
                    'adaptive_caching_enabled': self.config.enable_adaptive_caching,
                    'quality_monitoring_enabled': self.config.enable_quality_monitoring
                }
            
            return base_stats
            
        except Exception as e:
            if logger:
                logger.error(f"获取统计信息失败: {e}")
            return {}

    def close(self):
        """关闭集成管理器（增强版）"""
        try:
            # 停止定时器
            if PYQT5_AVAILABLE and hasattr(self, 'check_timer'):
                self.check_timer.stop()
                
            if PYQT5_AVAILABLE and hasattr(self, 'prediction_timer'):
                self.prediction_timer.stop()

            # 关闭线程池
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=True)

            # 关闭所有提示组件
            for prompt_widget in self.missing_prompt_widgets.values():
                prompt_widget.close()
            self.missing_prompt_widgets.clear()

            # 关闭所有下载对话框
            for dialog in self.active_download_dialogs.values():
                dialog.close()
            self.active_download_dialogs.clear()

            # 清空监控列表
            self.monitored_widgets.clear()
            
            # 清空智能化组件
            with self.cache_lock:
                self.intelligent_cache.clear()
            
            with self.prediction_lock:
                self.prediction_model = PredictionModel()
            
            self.performance_metrics = {
                'response_times': [],
                'success_rates': [],
                'cache_hit_rates': [],
                'prediction_accuracies': []
            }

            if logger:
                logger.info("智能数据集成管理器已关闭")

        except Exception as e:
            if logger:
                logger.error(f"关闭集成管理器失败: {e}")

# 全局实例
_smart_data_integration = None

def get_smart_data_integration(config: Optional[UIIntegrationConfig] = None) -> SmartDataIntegration:
    """获取智能数据集成管理器单例"""
    global _smart_data_integration
    if _smart_data_integration is None:
        _smart_data_integration = SmartDataIntegration(config)
    return _smart_data_integration
