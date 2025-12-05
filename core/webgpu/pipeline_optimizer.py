from loguru import logger
"""
WebGPU渲染管道调优器

提供高效的渲染管道优化：
- 批处理优化减少Draw Call
- 着色器程序缓存和重用
- 渲染队列智能调度
- 渲染状态自动合并
"""

import threading
import time
import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
import weakref

class RenderPriority(Enum):
    """渲染优先级"""
    IMMEDIATE = 0   # 立即渲染
    HIGH = 1        # 高优先级
    NORMAL = 2      # 正常优先级
    LOW = 3         # 低优先级
    BACKGROUND = 4  # 后台渲染

class BatchType(Enum):
    """批处理类型"""
    STATIC_GEOMETRY = "static_geometry"      # 静态几何体
    DYNAMIC_GEOMETRY = "dynamic_geometry"    # 动态几何体
    UI_ELEMENTS = "ui_elements"              # UI元素
    TEXT_RENDERING = "text_rendering"        # 文本渲染
    LINE_RENDERING = "line_rendering"        # 线条渲染
    POINT_RENDERING = "point_rendering"      # 点渲染

@dataclass
class RenderCommand:
    """渲染命令"""
    command_id: str
    batch_type: BatchType
    priority: RenderPriority
    shader_id: str
    vertex_data: Any
    index_data: Any = None
    uniform_data: Dict[str, Any] = field(default_factory=dict)
    texture_bindings: Dict[str, Any] = field(default_factory=dict)
    render_state: Dict[str, Any] = field(default_factory=dict)
    created_time: float = field(default_factory=time.time)
    callback: Optional[Callable] = None

@dataclass
class RenderBatch:
    """渲染批次"""
    batch_id: str
    batch_type: BatchType
    shader_id: str
    commands: List[RenderCommand] = field(default_factory=list)
    vertex_buffer: Optional[Any] = None
    index_buffer: Optional[Any] = None
    uniform_buffer: Optional[Any] = None
    texture_cache: Dict[str, Any] = field(default_factory=dict)
    render_state: Dict[str, Any] = field(default_factory=dict)
    created_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)
    is_dirty: bool = True

@dataclass
class ShaderProgram:
    """着色器程序"""
    shader_id: str
    vertex_shader: str
    fragment_shader: str
    compute_shader: Optional[str] = None
    uniforms: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    compiled_program: Optional[Any] = None
    compilation_time: float = 0.0
    usage_count: int = 0
    last_used_time: float = field(default_factory=time.time)

@dataclass
class PipelineStats:
    """管道统计信息"""
    total_commands: int = 0
    batched_commands: int = 0
    draw_calls: int = 0
    state_changes: int = 0
    shader_switches: int = 0
    batch_efficiency: float = 0.0
    average_batch_size: float = 0.0
    frame_time: float = 0.0
    gpu_utilization: float = 0.0

class WebGPUPipelineOptimizer:
    """
    WebGPU渲染管道优化器

    提供高效的渲染管道优化功能：
    - 智能批处理减少Draw Call开销
    - 着色器缓存避免重复编译
    - 渲染状态合并减少状态切换
    - 渲染队列优化提高GPU利用率
    """

    def __init__(self,
                 max_batch_size: int = 1000,
                 enable_auto_batching: bool = True,
                 enable_shader_cache: bool = True,
                 enable_state_sorting: bool = True,
                 frame_budget_ms: float = 16.67):  # 60 FPS
        """
        初始化渲染管道优化器

        Args:
            max_batch_size: 最大批处理大小
            enable_auto_batching: 是否启用自动批处理
            enable_shader_cache: 是否启用着色器缓存
            enable_state_sorting: 是否启用状态排序
            frame_budget_ms: 帧时间预算(毫秒)
        """
        self.max_batch_size = max_batch_size
        self.enable_auto_batching = enable_auto_batching
        self.enable_shader_cache = enable_shader_cache
        self.enable_state_sorting = enable_state_sorting
        self.frame_budget_ms = frame_budget_ms

        # 渲染队列
        self.render_queues: Dict[RenderPriority, deque] = {
            priority: deque() for priority in RenderPriority
        }

        # 渲染批次
        self.render_batches: Dict[str, RenderBatch] = {}
        self.batch_mapping: Dict[BatchType, List[str]] = defaultdict(list)

        # 着色器缓存
        self.shader_cache: Dict[str, ShaderProgram] = {}
        self.shader_compilation_queue = deque()

        # 渲染状态
        self.current_render_state: Dict[str, Any] = {}
        self.state_change_count = 0

        # 统计信息
        self.stats = PipelineStats()
        self.frame_stats: List[PipelineStats] = []
        self.max_frame_history = 100

        # 线程安全
        self.lock = threading.RLock()

        # 优化参数
        self.optimization_settings = {
            'enable_frustum_culling': True,
            'enable_backface_culling': True,
            'enable_early_z': True,
            'enable_instance_batching': True,
            'max_texture_units': 16,
            'batch_timeout_ms': 5.0
        }

        logger.info("WebGPU渲染管道优化器初始化完成")

    def submit_render_command(self, command: RenderCommand) -> str:
        """
        提交渲染命令

        Args:
            command: 渲染命令

        Returns:
            命令ID
        """
        try:
            with self.lock:
                # 添加到对应优先级队列
                self.render_queues[command.priority].append(command)

                # 尝试批处理
                if self.enable_auto_batching:
                    self._try_batch_command(command)

                self.stats.total_commands += 1

                logger.debug(f"提交渲染命令: {command.command_id}, 优先级: {command.priority.name}")
                return command.command_id

        except Exception as e:
            logger.error(f"提交渲染命令失败: {e}")
            return ""

    def _try_batch_command(self, command: RenderCommand):
        """尝试将命令加入批处理"""
        try:
            # 查找兼容的批次
            compatible_batch = self._find_compatible_batch(command)

            if compatible_batch:
                # 加入现有批次
                compatible_batch.commands.append(command)
                compatible_batch.last_update_time = time.time()
                compatible_batch.is_dirty = True

                logger.debug(f"命令{command.command_id}加入批次{compatible_batch.batch_id}")

            else:
                # 创建新批次
                batch = self._create_new_batch(command)
                self.render_batches[batch.batch_id] = batch
                self.batch_mapping[command.batch_type].append(batch.batch_id)

                logger.debug(f"为命令{command.command_id}创建新批次{batch.batch_id}")

            self.stats.batched_commands += 1

        except Exception as e:
            logger.error(f"批处理失败: {e}")

    def _find_compatible_batch(self, command: RenderCommand) -> Optional[RenderBatch]:
        """查找兼容的渲染批次"""
        try:
            # 获取同类型的批次
            batch_ids = self.batch_mapping.get(command.batch_type, [])

            for batch_id in batch_ids:
                batch = self.render_batches.get(batch_id)
                if not batch or len(batch.commands) >= self.max_batch_size:
                    continue

                # 检查着色器兼容性
                if batch.shader_id != command.shader_id:
                    continue

                # 检查渲染状态兼容性
                if not self._are_states_compatible(batch.render_state, command.render_state):
                    continue

                # 检查纹理兼容性
                if not self._are_textures_compatible(batch.texture_cache, command.texture_bindings):
                    continue

                return batch

            return None

        except Exception as e:
            logger.error(f"查找兼容批次失败: {e}")
            return None

    def _are_states_compatible(self, state1: Dict[str, Any], state2: Dict[str, Any]) -> bool:
        """检查渲染状态是否兼容"""
        try:
            # 关键状态必须完全匹配
            critical_states = ['blend_mode', 'depth_test', 'depth_write', 'cull_mode']

            for state in critical_states:
                if state1.get(state) != state2.get(state):
                    return False

            return True

        except Exception as e:
            logger.error(f"状态兼容性检查失败: {e}")
            return False

    def _are_textures_compatible(self, textures1: Dict[str, Any], textures2: Dict[str, Any]) -> bool:
        """检查纹理绑定是否兼容"""
        try:
            # 检查纹理槽位是否冲突
            for slot in textures2:
                if slot in textures1 and textures1[slot] != textures2[slot]:
                    return False

            # 检查纹理单元数量限制
            total_textures = len(set(textures1.keys()) | set(textures2.keys()))
            return total_textures <= self.optimization_settings['max_texture_units']

        except Exception as e:
            logger.error(f"纹理兼容性检查失败: {e}")
            return False

    def _create_new_batch(self, command: RenderCommand) -> RenderBatch:
        """创建新的渲染批次"""
        try:
            batch_id = f"{command.batch_type.value}_{int(time.time()*1000)}"

            batch = RenderBatch(
                batch_id=batch_id,
                batch_type=command.batch_type,
                shader_id=command.shader_id,
                commands=[command],
                render_state=command.render_state.copy(),
                texture_cache=command.texture_bindings.copy()
            )

            return batch

        except Exception as e:
            logger.error(f"创建新批次失败: {e}")
            raise

    def get_or_create_shader(self,
                             shader_id: str,
                             vertex_shader: str,
                             fragment_shader: str,
                             compute_shader: Optional[str] = None) -> Optional[ShaderProgram]:
        """获取或创建着色器程序"""
        try:
            with self.lock:
                # 检查缓存
                if self.enable_shader_cache and shader_id in self.shader_cache:
                    shader = self.shader_cache[shader_id]
                    shader.usage_count += 1
                    shader.last_used_time = time.time()
                    logger.debug(f"从缓存获取着色器: {shader_id}")
                    return shader

                # 创建新着色器
                shader = ShaderProgram(
                    shader_id=shader_id,
                    vertex_shader=vertex_shader,
                    fragment_shader=fragment_shader,
                    compute_shader=compute_shader
                )

                # 编译着色器
                compile_start = time.time()
                success = self._compile_shader(shader)
                shader.compilation_time = time.time() - compile_start

                if success:
                    if self.enable_shader_cache:
                        self.shader_cache[shader_id] = shader

                    logger.info(f"着色器编译成功: {shader_id}, 耗时: {shader.compilation_time*1000:.1f}ms")
                    return shader
                else:
                    logger.error(f"着色器编译失败: {shader_id}")
                    return None

        except Exception as e:
            logger.error(f"获取着色器失败: {e}")
            return None

    def _compile_shader(self, shader: ShaderProgram) -> bool:
        """编译着色器程序"""
        try:
            # 这里应该调用实际的WebGPU着色器编译
            # 现在只是模拟编译过程

            # 验证着色器代码
            if not shader.vertex_shader or not shader.fragment_shader:
                return False

            # 模拟编译延迟
            time.sleep(0.001)  # 1ms模拟编译时间

            # 创建虚拟的编译程序对象
            shader.compiled_program = {
                'vertex': f"compiled_{shader.shader_id}_vertex",
                'fragment': f"compiled_{shader.shader_id}_fragment",
                'compute': f"compiled_{shader.shader_id}_compute" if shader.compute_shader else None
            }

            return True

        except Exception as e:
            logger.error(f"着色器编译异常: {e}")
            return False

    def process_render_frame(self) -> Dict[str, Any]:
        """处理一帧的渲染"""
        try:
            frame_start = time.time()

            with self.lock:
                # 重置帧统计
                frame_stats = PipelineStats()

                # 按优先级处理渲染队列
                for priority in RenderPriority:
                    while self.render_queues[priority]:
                        if time.time() - frame_start > self.frame_budget_ms / 1000:
                            break  # 超出帧预算

                        command = self.render_queues[priority].popleft()
                        self._execute_render_command(command, frame_stats)

                # 处理批次渲染
                self._process_render_batches(frame_stats)

                # 更新统计
                frame_stats.frame_time = time.time() - frame_start
                self._update_frame_stats(frame_stats)

                logger.debug(f"渲染帧完成 - 命令: {frame_stats.total_commands}, "
                             f"Draw Calls: {frame_stats.draw_calls}, "
                             f"耗时: {frame_stats.frame_time*1000:.1f}ms")

                return {
                    'frame_time': frame_stats.frame_time,
                    'draw_calls': frame_stats.draw_calls,
                    'commands': frame_stats.total_commands,
                    'batch_efficiency': frame_stats.batch_efficiency
                }

        except Exception as e:
            logger.error(f"渲染帧处理失败: {e}")
            return {}

    def _execute_render_command(self, command: RenderCommand, stats: PipelineStats):
        """执行单个渲染命令"""
        try:
            # 获取着色器
            shader = self.shader_cache.get(command.shader_id)
            if not shader:
                logger.warning(f"着色器不存在: {command.shader_id}")
                return

            # 检查状态变化
            state_changed = self._apply_render_state(command.render_state)
            if state_changed:
                stats.state_changes += 1

            # 绑定纹理
            self._bind_textures(command.texture_bindings)

            # 执行渲染（模拟）
            stats.draw_calls += 1
            stats.total_commands += 1

            # 调用回调
            if command.callback:
                command.callback(command)

        except Exception as e:
            logger.error(f"执行渲染命令失败: {e}")

    def _process_render_batches(self, stats: PipelineStats):
        """处理渲染批次"""
        try:
            # 按类型和状态排序批次
            if self.enable_state_sorting:
                sorted_batches = self._sort_batches_by_state()
            else:
                sorted_batches = list(self.render_batches.values())

            current_shader = None

            for batch in sorted_batches:
                if not batch.commands:
                    continue

                # 着色器切换
                if batch.shader_id != current_shader:
                    current_shader = batch.shader_id
                    stats.shader_switches += 1

                # 应用批次状态
                state_changed = self._apply_render_state(batch.render_state)
                if state_changed:
                    stats.state_changes += 1

                # 绑定批次纹理
                self._bind_textures(batch.texture_cache)

                # 渲染批次
                self._render_batch(batch)

                stats.draw_calls += 1
                stats.batched_commands += len(batch.commands)

                # 清空已处理的批次
                batch.commands.clear()
                batch.is_dirty = False

            # 计算批处理效率
            if stats.total_commands > 0:
                stats.batch_efficiency = stats.batched_commands / stats.total_commands
                stats.average_batch_size = stats.batched_commands / max(1, stats.draw_calls)

        except Exception as e:
            logger.error(f"处理渲染批次失败: {e}")

    def _sort_batches_by_state(self) -> List[RenderBatch]:
        """按渲染状态排序批次"""
        try:
            batches = [batch for batch in self.render_batches.values() if batch.commands]

            # 按着色器ID、混合模式、深度测试等排序
            def sort_key(batch):
                state = batch.render_state
                return (
                    batch.shader_id,
                    state.get('blend_mode', 'default'),
                    state.get('depth_test', True),
                    state.get('cull_mode', 'back')
                )

            return sorted(batches, key=sort_key)

        except Exception as e:
            logger.error(f"批次排序失败: {e}")
            return list(self.render_batches.values())

    def _apply_render_state(self, render_state: Dict[str, Any]) -> bool:
        """应用渲染状态"""
        try:
            state_changed = False

            for key, value in render_state.items():
                if self.current_render_state.get(key) != value:
                    self.current_render_state[key] = value
                    state_changed = True

            return state_changed

        except Exception as e:
            logger.error(f"应用渲染状态失败: {e}")
            return False

    def _bind_textures(self, texture_bindings: Dict[str, Any]):
        """绑定纹理"""
        try:
            # 模拟纹理绑定
            for slot, texture in texture_bindings.items():
                pass  # 实际实现中会调用WebGPU纹理绑定API

        except Exception as e:
            logger.error(f"纹理绑定失败: {e}")

    def _render_batch(self, batch: RenderBatch):
        """渲染批次"""
        try:
            # 如果批次是脏的，需要重建缓冲区
            if batch.is_dirty:
                self._rebuild_batch_buffers(batch)

            # 模拟批次渲染
            # 实际实现中会调用WebGPU绘制API

        except Exception as e:
            logger.error(f"批次渲染失败: {e}")

    def _rebuild_batch_buffers(self, batch: RenderBatch):
        """重建批次缓冲区"""
        try:
            # 合并所有命令的顶点数据
            combined_vertices = []
            combined_indices = []
            combined_uniforms = {}

            vertex_offset = 0

            for command in batch.commands:
                # 处理顶点数据
                if command.vertex_data:
                    combined_vertices.extend(command.vertex_data)

                # 处理索引数据
                if command.index_data:
                    adjusted_indices = [idx + vertex_offset for idx in command.index_data]
                    combined_indices.extend(adjusted_indices)
                    vertex_offset += len(command.vertex_data) if command.vertex_data else 0

                # 合并uniform数据
                combined_uniforms.update(command.uniform_data)

            # 创建批次缓冲区（模拟）
            batch.vertex_buffer = f"vertex_buffer_{batch.batch_id}"
            if combined_indices:
                batch.index_buffer = f"index_buffer_{batch.batch_id}"
            if combined_uniforms:
                batch.uniform_buffer = f"uniform_buffer_{batch.batch_id}"

            batch.is_dirty = False

        except Exception as e:
            logger.error(f"重建批次缓冲区失败: {e}")

    def _update_frame_stats(self, frame_stats: PipelineStats):
        """更新帧统计"""
        try:
            # 添加到历史记录
            self.frame_stats.append(frame_stats)

            # 保持历史记录大小限制
            while len(self.frame_stats) > self.max_frame_history:
                self.frame_stats.pop(0)

            # 更新全局统计
            self.stats.total_commands += frame_stats.total_commands
            self.stats.batched_commands += frame_stats.batched_commands
            self.stats.draw_calls += frame_stats.draw_calls
            self.stats.state_changes += frame_stats.state_changes
            self.stats.shader_switches += frame_stats.shader_switches

            # 计算平均值
            if self.frame_stats:
                recent_frames = self.frame_stats[-30:]  # 最近30帧
                self.stats.frame_time = sum(f.frame_time for f in recent_frames) / len(recent_frames)
                self.stats.batch_efficiency = sum(f.batch_efficiency for f in recent_frames) / len(recent_frames)
                self.stats.average_batch_size = sum(f.average_batch_size for f in recent_frames) / len(recent_frames)

        except Exception as e:
            logger.error(f"更新帧统计失败: {e}")

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """获取管道统计信息"""
        try:
            with self.lock:
                return {
                    'total_commands': self.stats.total_commands,
                    'batched_commands': self.stats.batched_commands,
                    'draw_calls': self.stats.draw_calls,
                    'state_changes': self.stats.state_changes,
                    'shader_switches': self.stats.shader_switches,
                    'batch_efficiency': self.stats.batch_efficiency,
                    'average_batch_size': self.stats.average_batch_size,
                    'frame_time': self.stats.frame_time,
                    'fps': 1.0 / max(0.001, self.stats.frame_time),
                    'active_batches': len(self.render_batches),
                    'cached_shaders': len(self.shader_cache),
                    'queue_sizes': {
                        priority.name: len(queue)
                        for priority, queue in self.render_queues.items()
                    },
                    'optimization_settings': self.optimization_settings.copy()
                }

        except Exception as e:
            logger.error(f"获取管道统计失败: {e}")
            return {}

    def get_optimization_recommendations(self) -> List[str]:
        """获取优化建议"""
        try:
            recommendations = []

            # 批处理效率建议
            if self.stats.batch_efficiency < 0.5:
                recommendations.append("批处理效率较低，建议检查渲染状态兼容性或增加批处理大小")

            # 状态切换建议
            if len(self.frame_stats) > 10:
                avg_state_changes = sum(f.state_changes for f in self.frame_stats[-10:]) / 10
                if avg_state_changes > 50:
                    recommendations.append("状态切换过于频繁，建议启用状态排序或合并相似状态")

            # 着色器建议
            if len(self.shader_cache) > 100:
                recommendations.append("着色器缓存过大，建议清理未使用的着色器")

            # 帧时间建议
            if self.stats.frame_time > self.frame_budget_ms / 1000:
                recommendations.append(f"帧时间超过预算，当前: {self.stats.frame_time*1000:.1f}ms, "
                                       f"预算: {self.frame_budget_ms:.1f}ms")

            # 批次大小建议
            if self.stats.average_batch_size < 10:
                recommendations.append("平均批次大小较小，建议优化批处理逻辑")

            if not recommendations:
                recommendations.append("渲染管道运行良好，无需特殊优化")

            return recommendations

        except Exception as e:
            logger.error(f"获取优化建议失败: {e}")
            return ["无法获取优化建议"]

    def update_optimization_settings(self, settings: Dict[str, Any]):
        """更新优化设置"""
        try:
            with self.lock:
                self.optimization_settings.update(settings)
                logger.info(f"优化设置已更新: {settings}")

        except Exception as e:
            logger.error(f"更新优化设置失败: {e}")

    def clear_shader_cache(self):
        """清空着色器缓存"""
        try:
            with self.lock:
                cleared_count = len(self.shader_cache)
                self.shader_cache.clear()
                logger.info(f"清空了{cleared_count}个缓存着色器")

        except Exception as e:
            logger.error(f"清空着色器缓存失败: {e}")

    def flush_render_batches(self):
        """刷新所有渲染批次"""
        try:
            with self.lock:
                flushed_count = 0

                for batch in self.render_batches.values():
                    if batch.commands:
                        batch.commands.clear()
                        batch.is_dirty = False
                        flushed_count += 1

                logger.info(f"刷新了{flushed_count}个渲染批次")

        except Exception as e:
            logger.error(f"刷新渲染批次失败: {e}")

    def cleanup_expired_resources(self, max_age_seconds: float = 300):
        """清理过期资源"""
        try:
            with self.lock:
                current_time = time.time()

                # 清理过期着色器
                expired_shaders = []
                for shader_id, shader in self.shader_cache.items():
                    if current_time - shader.last_used_time > max_age_seconds:
                        expired_shaders.append(shader_id)

                for shader_id in expired_shaders:
                    del self.shader_cache[shader_id]

                # 清理空批次
                empty_batches = []
                for batch_id, batch in self.render_batches.items():
                    if not batch.commands and current_time - batch.last_update_time > max_age_seconds:
                        empty_batches.append(batch_id)

                for batch_id in empty_batches:
                    batch = self.render_batches.pop(batch_id)
                    # 从映射中移除
                    if batch_id in self.batch_mapping[batch.batch_type]:
                        self.batch_mapping[batch.batch_type].remove(batch_id)

                logger.info(f"清理过期资源: {len(expired_shaders)}个着色器, {len(empty_batches)}个批次")

        except Exception as e:
            logger.error(f"清理过期资源失败: {e}")

    def shutdown(self):
        """关闭管道优化器"""
        try:
            logger.info("正在关闭WebGPU渲染管道优化器...")

            with self.lock:
                # 清空所有队列
                for queue in self.render_queues.values():
                    queue.clear()

                # 清空批次
                self.render_batches.clear()
                self.batch_mapping.clear()

                # 清空着色器缓存
                self.shader_cache.clear()

                # 清空统计
                self.frame_stats.clear()

            logger.info("WebGPU渲染管道优化器已关闭")

        except Exception as e:
            logger.error(f"关闭管道优化器失败: {e}")

# 全局管道优化器实例
_pipeline_optimizer: Optional[WebGPUPipelineOptimizer] = None
_optimizer_lock = threading.Lock()

def get_webgpu_pipeline_optimizer(**kwargs) -> WebGPUPipelineOptimizer:
    """获取WebGPU管道优化器实例（单例模式）"""
    global _pipeline_optimizer

    with _optimizer_lock:
        if _pipeline_optimizer is None:
            _pipeline_optimizer = WebGPUPipelineOptimizer(**kwargs)
        return _pipeline_optimizer

def shutdown_webgpu_pipeline_optimizer():
    """关闭WebGPU管道优化器"""
    global _pipeline_optimizer

    with _optimizer_lock:
        if _pipeline_optimizer:
            _pipeline_optimizer.shutdown()
            _pipeline_optimizer = None
