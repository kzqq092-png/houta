#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
虚拟滚动优化器

专门针对大数据量图表渲染的虚拟滚动技术，提供高效的数据可视化和交互性能

作者: FactorWeave-Quant团队
版本: 1.0
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QRectF, QPointF, QTimer
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem
from loguru import logger
import time
from collections import deque
import threading

class ViewportState(Enum):
    """视口状态枚举"""
    IDLE = "idle"
    SCROLLING = "scrolling"
    ZOOMING = "zooming"
    LOADING = "loading"

@dataclass
class RenderChunk:
    """渲染块数据结构"""
    start_index: int
    end_index: int
    data_points: np.ndarray
    bounding_rect: QRectF
    render_time: float
    is_visible: bool = True

@dataclass
class VirtualizationConfig:
    """虚拟滚动配置"""
    # 基础配置
    chunk_size: int = 1000  # 每个渲染块的数据点数量
    overlap_size: int = 100  # 块之间的重叠数据点数量
    max_visible_chunks: int = 5  # 最大可见块数量
    
    # 性能配置
    max_render_time_ms: float = 16.67  # 最大渲染时间（60fps）
    memory_threshold_mb: int = 100  # 内存阈值
    cleanup_threshold: float = 0.8  # 清理阈值（80%内存使用）
    
    # 质量配置
    adaptive_quality: bool = True  # 自适应质量
    min_quality: float = 0.3  # 最小质量（0.3-1.0）
    quality_levels: List[int] = None  # 质量级别对应的数据抽样
    
    # 交互配置
    scroll_threshold: int = 50  # 滚动阈值
    preload_distance: int = 200  # 预加载距离
    
    def __post_init__(self):
        if self.quality_levels is None:
            self.quality_levels = [1, 2, 4, 8, 16]  # 抽样级别：1=全部数据，2=抽样一半等

class DataAggregator:
    """数据聚合器"""
    
    def __init__(self, config: VirtualizationConfig):
        self.config = config
        self._lock = threading.Lock()
        
    def aggregate_chunk(self, data: np.ndarray, start_idx: int, end_idx: int, 
                       quality_level: int = 1) -> np.ndarray:
        """聚合数据块"""
        try:
            if quality_level <= 1:
                return data[start_idx:end_idx]
                
            chunk_data = data[start_idx:end_idx]
            chunk_size = len(chunk_data)
            
            # 基于质量级别进行数据聚合
            step = quality_level
            if step >= chunk_size:
                # 如果抽样步长大于块大小，返回平均聚合
                return np.array([np.mean(chunk_data)])
            
            # 重采样聚合
            aggregated = []
            for i in range(0, chunk_size, step):
                end_i = min(i + step, chunk_size)
                window = chunk_data[i:end_i]
                
                # 对于时间序列，使用适当的聚合方法
                if i == 0 and len(window) > 1:
                    # 第一个窗口包含头部数据，需要特殊处理
                    aggregated.append(window[0])  # 头部值
                elif len(window) > 0:
                    # 普通窗口使用平均值
                    aggregated.append(np.mean(window))
            
            return np.array(aggregated)
            
        except Exception as e:
            logger.error(f"数据聚合失败: {e}")
            return data[start_idx:end_idx] if end_idx > start_idx else np.array([])
    
    def adaptive_aggregate(self, data: np.ndarray, start_idx: int, end_idx: int,
                          frame_time_ms: float) -> Tuple[np.ndarray, int]:
        """自适应数据聚合"""
        with self._lock:
            # 根据帧时间动态调整质量级别
            if frame_time_ms > self.config.max_render_time_ms:
                # 渲染时间过长，降低质量
                quality_level = min(8, int(frame_time_ms / self.config.max_render_time_ms) + 1)
            else:
                quality_level = 1
            
            # 聚合数据
            aggregated_data = self.aggregate_chunk(data, start_idx, end_idx, quality_level)
            
            return aggregated_data, quality_level

class ViewportTracker:
    """视口追踪器"""
    
    def __init__(self, config: VirtualizationConfig):
        self.config = config
        self.state = ViewportState.IDLE
        self.last_visible_rect = QRectF()
        self.scroll_velocity = 0.0
        self.last_update_time = time.time()
        
        # 滚动预测
        self._scroll_history = deque(maxlen=10)
        self._last_scroll_event = None
        
    def update_viewport(self, visible_rect: QRectF):
        """更新视口信息"""
        now = time.time()
        dt = now - self.last_update_time
        
        self.last_visible_rect = visible_rect
        self.last_update_time = now
        
        # 计算滚动速度
        if dt > 0:
            self.scroll_velocity = abs(visible_rect.y() - self.last_visible_rect.y()) / dt
        
        # 记录滚动历史
        self._scroll_history.append({
            'time': now,
            'velocity': self.scroll_velocity,
            'rect': visible_rect
        })
        
    def predict_next_position(self) -> QRectF:
        """预测下一帧位置"""
        if len(self._scroll_history) < 2:
            return self.last_visible_rect
            
        # 简单的线性预测
        recent_scrolls = list(self._scroll_history)[-3:]  # 最近3次滚动
        if len(recent_scrolls) < 2:
            return self.last_visible_rect
            
        avg_velocity = sum(s['velocity'] for s in recent_scrolls) / len(recent_scrolls)
        predicted_y = self.last_visible_rect.y() + avg_velocity * 0.016  # 预测下一帧（60fps）
        
        return QRectF(
            self.last_visible_rect.x(),
            predicted_y,
            self.last_visible_rect.width(),
            self.last_visible_rect.height()
        )
    
    def is_scrolling_fast(self) -> bool:
        """判断是否在快速滚动"""
        return self.scroll_velocity > self.config.scroll_threshold

class ChunkRenderer:
    """渲染块管理器"""
    
    def __init__(self, config: VirtualizationConfig, data_aggregator: DataAggregator):
        self.config = config
        self.aggregator = data_aggregator
        self.chunks: Dict[int, RenderChunk] = {}
        self._render_queue = deque()
        self._lock = threading.Lock()
        
    def request_chunk(self, chunk_id: int, data: np.ndarray, 
                     viewport_rect: QRectF) -> Optional[RenderChunk]:
        """请求渲染块"""
        with self._lock:
            # 计算块边界
            chunk_size = self.config.chunk_size
            overlap = self.config.overlap_size
            start_idx = max(0, chunk_id * chunk_size - overlap)
            end_idx = min(len(data), (chunk_id + 1) * chunk_size + overlap)
            
            # 检查是否需要渲染
            if not self._should_render_chunk(chunk_id, viewport_rect):
                return None
            
            # 创建渲染块
            chunk = self._create_render_chunk(chunk_id, data, start_idx, end_idx)
            if chunk:
                self.chunks[chunk_id] = chunk
                
            return chunk
    
    def _should_render_chunk(self, chunk_id: int, viewport_rect: QRectF) -> bool:
        """判断是否需要渲染该块"""
        chunk_y = chunk_id * self.config.chunk_size
        
        # 检查块是否在视口附近
        viewport_top = viewport_rect.y()
        viewport_bottom = viewport_rect.y() + viewport_rect.height()
        
        chunk_top = chunk_y - self.config.preload_distance
        chunk_bottom = chunk_y + self.config.chunk_size + self.config.preload_distance
        
        return not (chunk_bottom < viewport_top or chunk_top > viewport_bottom)
    
    def _create_render_chunk(self, chunk_id: int, data: np.ndarray,
                            start_idx: int, end_idx: int) -> Optional[RenderChunk]:
        """创建渲染块"""
        try:
            # 计算质量级别（基于内存压力）
            memory_usage = self._get_memory_usage()
            if memory_usage > self.config.cleanup_threshold:
                quality_level = min(8, int(memory_usage * 10))
            else:
                quality_level = 1
            
            # 聚合数据
            aggregated_data, actual_quality = self.aggregator.aggregate_chunk(
                data, start_idx, end_idx, quality_level)
            
            # 创建渲染块
            chunk = RenderChunk(
                start_index=start_idx,
                end_index=end_idx,
                data_points=aggregated_data,
                bounding_rect=QRectF(
                    0, chunk_id * self.config.chunk_size,
                    100, len(aggregated_data)
                ),
                render_time=0.0,
                is_visible=True
            )
            
            return chunk
            
        except Exception as e:
            logger.error(f"创建渲染块失败 (chunk_id={chunk_id}): {e}")
            return None
    
    def cleanup_chunks(self, visible_chunks: List[int]):
        """清理不可见的块"""
        with self._lock:
            chunks_to_remove = []
            for chunk_id in self.chunks.keys():
                if chunk_id not in visible_chunks:
                    chunks_to_remove.append(chunk_id)
            
            for chunk_id in chunks_to_remove:
                del self.chunks[chunk_id]
    
    def _get_memory_usage(self) -> float:
        """获取内存使用率（模拟）"""
        # 这里应该集成实际的内存监控
        # 目前返回默认值
        return 0.5

class VirtualScrollRenderer(QObject):
    """虚拟滚动渲染器主类（集成WebGPU加速）"""
    
    # 信号定义
    data_rendered = pyqtSignal(int, object)  # chunk_id, RenderChunk
    rendering_progress = pyqtSignal(float)  # 进度百分比
    performance_warning = pyqtSignal(str, float)  # 警告信息, 数值
    gpu_acceleration_toggled = pyqtSignal(bool)  # GPU加速启用/禁用状态
    
    def __init__(self, config: Optional[VirtualizationConfig] = None):
        super().__init__()
        self.config = config or VirtualizationConfig()
        self.data_source = None  # 数据源（DataFrame或ndarray）
        self.viewport_tracker = ViewportTracker(self.config)
        self.data_aggregator = DataAggregator(self.config)
        self.chunk_renderer = ChunkRenderer(self.config, self.data_aggregator)
        
        # WebGPU渲染器集成
        try:
            from core.webgpu import GPURendererConfig, WebGPURenderer
            self.webgpu_renderer = WebGPURenderer(GPURendererConfig(
                preferred_backend="moderngl"  # 尝试使用ModernGL后端
            ))
            # 尝试初始化WebGPU渲染器
            self.gpu_acceleration_enabled = self.webgpu_renderer.initialize()
            self.gpu_acceleration_toggled.emit(self.gpu_acceleration_enabled)
            
            if self.gpu_acceleration_enabled:
                logger.info("✅ WebGPU渲染器集成成功，将使用GPU加速渲染")
            else:
                logger.warning("⚠️ WebGPU渲染器初始化失败，将使用CPU渲染")
        except Exception as e:
            logger.warning(f"WebGPU渲染器集成失败: {e}")
            self.gpu_acceleration_enabled = False
        
        # 性能监控
        self.render_times = deque(maxlen=100)
        self.frame_times = deque(maxlen=60)  # 最近60帧的渲染时间
        self.last_frame_time = time.time()
        
        # 渲染状态
        self.is_rendering = False
        self.quality_level = 1
        self.adaptive_quality_enabled = True
        
        # WebGPU统计
        self.gpu_performance_stats = {
            'rendered_chunks_count': 0,
            'total_vertices_count': 0,
            'gpu_utilization': 0.0,  # 0.0-1.0
            'batch_processing': False
        }
        
        # 定时器用于渲染循环
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self._render_loop)
        self.render_timer.start(16)  # 60fps渲染
        
    def set_data_source(self, data: Union[np.ndarray, pd.DataFrame]):
        """设置数据源"""
        if isinstance(data, pd.DataFrame):
            # 取第一列作为Y轴数据
            y_data = data.iloc[:, 1].values if len(data.columns) > 1 else data.iloc[:, 0].values
        else:
            y_data = data
        
        self.data_source = y_data
        self.chunk_renderer.chunks.clear()  # 清除缓存
        
        logger.info(f"虚拟滚动数据源已设置，数据点数量: {len(y_data)}")
    
    def update_viewport(self, visible_rect: QRectF):
        """更新视口"""
        self.viewport_tracker.update_viewport(visible_rect)
        
        # 根据滚动状态调整渲染策略
        if self.viewport_tracker.is_scrolling_fast():
            self._set_quality_level(3)  # 快速滚动时降低质量
        else:
            self._set_quality_level(1)  # 静止时最高质量
    
    def _render_loop(self):
        """渲染循环"""
        if not self.data_source is not None:
            return
        
        frame_start_time = time.time()
        
        # 计算当前视口应该渲染的块
        visible_rect = self.viewport_tracker.last_visible_rect
        predicted_rect = self.viewport_tracker.predict_next_position()
        
        # 获取需要渲染的块列表
        chunk_start = max(0, int(predicted_rect.y() / self.config.chunk_size) - 1)
        chunk_end = int((predicted_rect.y() + predicted_rect.height()) / self.config.chunk_size) + 1
        
        visible_chunks = []
        for chunk_id in range(chunk_start, chunk_end + 1):
            chunk = self.chunk_renderer.request_chunk(chunk_id, self.data_source, predicted_rect)
            if chunk:
                visible_chunks.append(chunk_id)
                self.data_rendered.emit(chunk_id, chunk)
        
        # 清理不可见的块
        self.chunk_renderer.cleanup_chunks(visible_chunks)
        
        # 更新性能统计
        frame_time = (time.time() - frame_start_time) * 1000
        self.frame_times.append(frame_time)
        self.render_times.append(frame_time)
        
        # 自适应质量调整
        if self.adaptive_quality_enabled:
            self._adaptive_quality_adjustment()
        
        # 性能监控
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        if avg_frame_time > self.config.max_render_time_ms:
            self.performance_warning.emit(
                f"平均帧时间过长: {avg_frame_time:.1f}ms", avg_frame_time)
    
    def _adaptive_quality_adjustment(self):
        """自适应质量调整"""
        if len(self.frame_times) < 10:  # 至少10帧数据
            return
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        
        if avg_frame_time > self.config.max_render_time_ms * 1.5:
            # 性能严重不达标，大幅降低质量
            self.quality_level = min(16, self.quality_level * 2)
        elif avg_frame_time < self.config.max_render_time_ms * 0.5:
            # 性能很好，可以提升质量
            self.quality_level = max(1, self.quality_level // 2)
    
    def _set_quality_level(self, level: int):
        """设置质量级别"""
        if level != self.quality_level:
            self.quality_level = level
            self.chunk_renderer.cleanup_chunks([])  # 强制重新渲染
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        if not self.render_times:
            return {}
        
        return {
            'avg_render_time_ms': sum(self.render_times) / len(self.render_times),
            'max_render_time_ms': max(self.render_times),
            'min_render_time_ms': min(self.render_times),
            'current_quality_level': self.quality_level,
            'rendered_chunks_count': len(self.chunk_renderer.chunks),
            'adaptive_quality_enabled': self.adaptive_quality_enabled
        }
    
    def enable_adaptive_quality(self, enabled: bool):
        """启用/禁用自适应质量"""
        self.adaptive_quality_enabled = enabled
    
    def cleanup(self):
        """清理资源"""
        self.render_timer.stop()
        self.chunk_renderer.chunks.clear()
        self.render_times.clear()
        self.frame_times.clear()

# 便捷函数
def create_virtual_scroll_renderer(data: Union[np.ndarray, pd.DataFrame],
                                 config: Optional[VirtualizationConfig] = None) -> VirtualScrollRenderer:
    """创建虚拟滚动渲染器"""
    renderer = VirtualScrollRenderer(config)
    renderer.set_data_source(data)
    return renderer

def optimize_for_large_dataset(data_size: int) -> VirtualizationConfig:
    """根据数据集大小优化配置"""
    if data_size > 1_000_000:  # 100万数据点
        return VirtualizationConfig(
            chunk_size=500,
            overlap_size=50,
            max_visible_chunks=3,
            quality_levels=[1, 4, 8, 16, 32]
        )
    elif data_size > 100_000:  # 10万数据点
        return VirtualizationConfig(
            chunk_size=1000,
            overlap_size=100,
            max_visible_chunks=4,
            quality_levels=[1, 2, 4, 8, 16]
        )
    else:
        return VirtualizationConfig()  # 默认配置