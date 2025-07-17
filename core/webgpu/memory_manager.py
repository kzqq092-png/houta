"""
WebGPU内存管理优化器

提供高效的GPU内存管理：
- GPU内存池管理和预分配
- 智能资源回收机制
- 内存使用监控和优化建议
- 内存泄漏检测和防护
"""

import logging
import threading
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set
import gc
import psutil

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """GPU内存类型"""
    VERTEX_BUFFER = "vertex_buffer"
    INDEX_BUFFER = "index_buffer"
    UNIFORM_BUFFER = "uniform_buffer"
    TEXTURE = "texture"
    RENDER_TARGET = "render_target"
    STORAGE_BUFFER = "storage_buffer"


class MemoryPriority(Enum):
    """内存优先级"""
    CRITICAL = 0  # 关键资源，不能释放
    HIGH = 1      # 高优先级，优先保留
    NORMAL = 2    # 正常优先级
    LOW = 3       # 低优先级，优先释放
    DISPOSABLE = 4  # 可随时释放


@dataclass
class MemoryBlock:
    """内存块信息"""
    block_id: str
    memory_type: MemoryType
    size: int
    priority: MemoryPriority
    created_time: float
    last_access_time: float
    access_count: int
    is_allocated: bool = True
    resource_ref: Optional[weakref.ref] = None


@dataclass
class MemoryPool:
    """内存池"""
    memory_type: MemoryType
    total_size: int
    used_size: int
    block_size: int
    max_blocks: int
    blocks: List[MemoryBlock]
    free_blocks: deque

    def __post_init__(self):
        self.blocks = []
        self.free_blocks = deque()


@dataclass
class MemoryStats:
    """内存统计信息"""
    total_allocated: int = 0
    total_used: int = 0
    total_free: int = 0
    pools: Dict[MemoryType, Dict[str, int]] = None
    peak_usage: int = 0
    allocation_count: int = 0
    deallocation_count: int = 0
    cache_hit_rate: float = 0.0
    fragmentation_rate: float = 0.0

    def __post_init__(self):
        if self.pools is None:
            self.pools = {}


class WebGPUMemoryManager:
    """
    WebGPU内存管理器

    提供高效的GPU内存管理功能：
    - 预分配内存池减少动态分配开销
    - LRU缓存机制提高资源重用率
    - 智能垃圾回收避免内存泄漏
    - 实时监控和性能优化建议
    """

    def __init__(self,
                 max_gpu_memory: int = 256 * 1024 * 1024,  # 256MB
                 enable_preallocation: bool = True,
                 gc_threshold: float = 0.8,  # 80%使用率触发GC
                 enable_monitoring: bool = True):
        """
        初始化WebGPU内存管理器

        Args:
            max_gpu_memory: 最大GPU内存使用量(字节)
            enable_preallocation: 是否启用内存预分配
            gc_threshold: 垃圾回收阈值
            enable_monitoring: 是否启用内存监控
        """
        self.max_gpu_memory = max_gpu_memory
        self.enable_preallocation = enable_preallocation
        self.gc_threshold = gc_threshold
        self.enable_monitoring = enable_monitoring

        # 内存池
        self.memory_pools: Dict[MemoryType, MemoryPool] = {}

        # 分配的内存块
        self.allocated_blocks: Dict[str, MemoryBlock] = {}

        # LRU缓存
        self.lru_cache: Dict[str, MemoryBlock] = {}
        self.cache_access_order = deque()
        self.max_cache_size = 100

        # 统计信息
        self.stats = MemoryStats()
        self.peak_memory_usage = 0

        # 线程安全
        self.lock = threading.RLock()

        # 监控线程
        self.monitoring_thread = None
        self.monitoring_enabled = False

        # 初始化
        self._initialize_memory_pools()

        if self.enable_monitoring:
            self._start_monitoring()

        logger.info(f"WebGPU内存管理器初始化完成 - 最大内存: {max_gpu_memory//1024//1024}MB")

    def _initialize_memory_pools(self):
        """初始化内存池"""
        try:
            with self.lock:
                # 定义各类型内存池配置
                pool_configs = {
                    MemoryType.VERTEX_BUFFER: {
                        'total_size': self.max_gpu_memory // 4,  # 25%
                        'block_size': 64 * 1024,  # 64KB
                        'max_blocks': 100
                    },
                    MemoryType.INDEX_BUFFER: {
                        'total_size': self.max_gpu_memory // 8,  # 12.5%
                        'block_size': 32 * 1024,  # 32KB
                        'max_blocks': 50
                    },
                    MemoryType.UNIFORM_BUFFER: {
                        'total_size': self.max_gpu_memory // 16,  # 6.25%
                        'block_size': 16 * 1024,  # 16KB
                        'max_blocks': 25
                    },
                    MemoryType.TEXTURE: {
                        'total_size': self.max_gpu_memory // 2,  # 50%
                        'block_size': 256 * 1024,  # 256KB
                        'max_blocks': 200
                    },
                    MemoryType.RENDER_TARGET: {
                        'total_size': self.max_gpu_memory // 16,  # 6.25%
                        'block_size': 128 * 1024,  # 128KB
                        'max_blocks': 10
                    }
                }

                # 创建内存池
                for memory_type, config in pool_configs.items():
                    pool = MemoryPool(
                        memory_type=memory_type,
                        total_size=config['total_size'],
                        used_size=0,
                        block_size=config['block_size'],
                        max_blocks=config['max_blocks'],
                        blocks=[],
                        free_blocks=deque()
                    )

                    # 预分配内存块
                    if self.enable_preallocation:
                        self._preallocate_blocks(pool, config['max_blocks'] // 4)

                    self.memory_pools[memory_type] = pool

                logger.info(f"初始化了{len(self.memory_pools)}个内存池")

        except Exception as e:
            logger.error(f"内存池初始化失败: {e}")
            raise

    def _preallocate_blocks(self, pool: MemoryPool, count: int):
        """预分配内存块"""
        try:
            for i in range(count):
                block_id = f"{pool.memory_type.value}_{len(pool.blocks):04d}"

                block = MemoryBlock(
                    block_id=block_id,
                    memory_type=pool.memory_type,
                    size=pool.block_size,
                    priority=MemoryPriority.NORMAL,
                    created_time=time.time(),
                    last_access_time=time.time(),
                    access_count=0,
                    is_allocated=False
                )

                pool.blocks.append(block)
                pool.free_blocks.append(block)

            logger.debug(f"预分配了{count}个{pool.memory_type.value}内存块")

        except Exception as e:
            logger.error(f"内存块预分配失败: {e}")

    def allocate_memory(self,
                        memory_type: MemoryType,
                        size: int,
                        priority: MemoryPriority = MemoryPriority.NORMAL,
                        resource_ref: Optional[Any] = None) -> Optional[str]:
        """
        分配GPU内存

        Args:
            memory_type: 内存类型
            size: 所需内存大小
            priority: 内存优先级
            resource_ref: 资源引用（用于弱引用）

        Returns:
            内存块ID，失败返回None
        """
        try:
            with self.lock:
                pool = self.memory_pools.get(memory_type)
                if not pool:
                    logger.error(f"不支持的内存类型: {memory_type}")
                    return None

                # 检查是否需要垃圾回收
                if self._should_trigger_gc():
                    self._garbage_collect()

                # 尝试从缓存获取
                cached_block = self._get_from_cache(memory_type, size)
                if cached_block:
                    self._update_cache_access(cached_block.block_id)
                    cached_block.last_access_time = time.time()
                    cached_block.access_count += 1
                    cached_block.priority = priority
                    self.allocated_blocks[cached_block.block_id] = cached_block
                    self.stats.cache_hit_rate = len(self.lru_cache) / max(1, self.stats.allocation_count)
                    logger.debug(f"从缓存分配内存: {cached_block.block_id}")
                    return cached_block.block_id

                # 尝试从空闲块分配
                block = self._allocate_from_pool(pool, size, priority, resource_ref)
                if block:
                    self.allocated_blocks[block.block_id] = block
                    self.stats.allocation_count += 1
                    self._update_stats()
                    logger.debug(f"分配内存成功: {block.block_id}, 大小: {size}")
                    return block.block_id

                # 尝试扩展池
                if self._expand_pool(pool, size):
                    block = self._allocate_from_pool(pool, size, priority, resource_ref)
                    if block:
                        self.allocated_blocks[block.block_id] = block
                        self.stats.allocation_count += 1
                        self._update_stats()
                        logger.debug(f"扩展池后分配内存成功: {block.block_id}")
                        return block.block_id

                logger.warning(f"内存分配失败: {memory_type}, 大小: {size}")
                return None

        except Exception as e:
            logger.error(f"内存分配异常: {e}")
            return None

    def deallocate_memory(self, block_id: str, cache: bool = True) -> bool:
        """
        释放GPU内存

        Args:
            block_id: 内存块ID
            cache: 是否缓存到LRU

        Returns:
            是否成功释放
        """
        try:
            with self.lock:
                block = self.allocated_blocks.get(block_id)
                if not block:
                    logger.warning(f"内存块不存在: {block_id}")
                    return False

                # 从分配列表中移除
                del self.allocated_blocks[block_id]

                # 更新池使用量
                pool = self.memory_pools.get(block.memory_type)
                if pool:
                    pool.used_size -= block.size

                # 决定是否缓存
                if cache and block.priority != MemoryPriority.DISPOSABLE:
                    self._add_to_cache(block)
                else:
                    # 直接释放
                    block.is_allocated = False
                    if pool:
                        pool.free_blocks.append(block)

                self.stats.deallocation_count += 1
                self._update_stats()

                logger.debug(f"释放内存成功: {block_id}, 缓存: {cache}")
                return True

        except Exception as e:
            logger.error(f"内存释放异常: {e}")
            return False

    def _allocate_from_pool(self,
                            pool: MemoryPool,
                            size: int,
                            priority: MemoryPriority,
                            resource_ref: Optional[Any]) -> Optional[MemoryBlock]:
        """从内存池分配内存块"""
        try:
            # 检查可用内存
            if pool.used_size + size > pool.total_size:
                return None

            # 寻找合适的空闲块
            suitable_block = None

            # 优先使用大小匹配的块
            for i, block in enumerate(pool.free_blocks):
                if block.size >= size:
                    suitable_block = pool.free_blocks.popleft() if i == 0 else pool.free_blocks.remove(block)
                    break

            # 如果没有找到，创建新块
            if not suitable_block:
                if len(pool.blocks) >= pool.max_blocks:
                    return None

                block_id = f"{pool.memory_type.value}_{len(pool.blocks):04d}_{int(time.time())}"
                suitable_block = MemoryBlock(
                    block_id=block_id,
                    memory_type=pool.memory_type,
                    size=max(size, pool.block_size),
                    priority=priority,
                    created_time=time.time(),
                    last_access_time=time.time(),
                    access_count=0,
                    is_allocated=True
                )

                # 设置弱引用
                if resource_ref:
                    suitable_block.resource_ref = weakref.ref(resource_ref)

                pool.blocks.append(suitable_block)
            else:
                suitable_block.is_allocated = True
                suitable_block.priority = priority
                suitable_block.last_access_time = time.time()
                suitable_block.access_count += 1

                if resource_ref:
                    suitable_block.resource_ref = weakref.ref(resource_ref)

            pool.used_size += suitable_block.size
            return suitable_block

        except Exception as e:
            logger.error(f"从池分配内存失败: {e}")
            return None

    def _expand_pool(self, pool: MemoryPool, required_size: int) -> bool:
        """扩展内存池"""
        try:
            # 检查是否可以扩展
            new_total = pool.total_size + required_size * 2
            current_total = sum(p.total_size for p in self.memory_pools.values())

            if current_total + required_size * 2 > self.max_gpu_memory:
                return False

            pool.total_size = new_total
            logger.debug(f"扩展{pool.memory_type.value}池到{new_total//1024}KB")
            return True

        except Exception as e:
            logger.error(f"内存池扩展失败: {e}")
            return False

    def _get_from_cache(self, memory_type: MemoryType, size: int) -> Optional[MemoryBlock]:
        """从LRU缓存获取内存块"""
        try:
            # 查找匹配的缓存块
            for cache_key, block in self.lru_cache.items():
                if (block.memory_type == memory_type and
                    block.size >= size and
                        not block.is_allocated):

                    # 从缓存中移除
                    del self.lru_cache[cache_key]
                    if cache_key in self.cache_access_order:
                        self.cache_access_order.remove(cache_key)

                    block.is_allocated = True
                    return block

            return None

        except Exception as e:
            logger.error(f"缓存获取失败: {e}")
            return None

    def _add_to_cache(self, block: MemoryBlock):
        """添加到LRU缓存"""
        try:
            # 检查缓存大小限制
            while len(self.lru_cache) >= self.max_cache_size:
                # 移除最久未使用的块
                oldest_key = self.cache_access_order.popleft()
                oldest_block = self.lru_cache.pop(oldest_key, None)
                if oldest_block:
                    # 真正释放内存
                    pool = self.memory_pools.get(oldest_block.memory_type)
                    if pool:
                        pool.free_blocks.append(oldest_block)

            # 添加到缓存
            cache_key = f"{block.block_id}_{block.memory_type.value}"
            self.lru_cache[cache_key] = block
            self.cache_access_order.append(cache_key)

            block.is_allocated = False

        except Exception as e:
            logger.error(f"缓存添加失败: {e}")

    def _update_cache_access(self, block_id: str):
        """更新缓存访问顺序"""
        try:
            # 查找匹配的缓存键
            matching_key = None
            for key in self.cache_access_order:
                if key.startswith(block_id):
                    matching_key = key
                    break

            if matching_key:
                self.cache_access_order.remove(matching_key)
                self.cache_access_order.append(matching_key)

        except Exception as e:
            logger.error(f"缓存访问更新失败: {e}")

    def _should_trigger_gc(self) -> bool:
        """判断是否应该触发垃圾回收"""
        try:
            total_used = sum(pool.used_size for pool in self.memory_pools.values())
            total_available = sum(pool.total_size for pool in self.memory_pools.values())

            usage_ratio = total_used / max(1, total_available)
            return usage_ratio > self.gc_threshold

        except Exception as e:
            logger.error(f"GC触发检查失败: {e}")
            return False

    def _garbage_collect(self):
        """执行垃圾回收"""
        try:
            logger.debug("开始WebGPU内存垃圾回收...")

            gc_start = time.time()
            freed_count = 0
            freed_size = 0

            # 清理已失效的弱引用
            invalid_blocks = []
            for block_id, block in self.allocated_blocks.items():
                if block.resource_ref and block.resource_ref() is None:
                    invalid_blocks.append(block_id)

            for block_id in invalid_blocks:
                block = self.allocated_blocks[block_id]
                if self.deallocate_memory(block_id, cache=False):
                    freed_count += 1
                    freed_size += block.size

            # 清理低优先级的缓存
            low_priority_keys = []
            for key, block in self.lru_cache.items():
                if block.priority in [MemoryPriority.LOW, MemoryPriority.DISPOSABLE]:
                    low_priority_keys.append(key)

            for key in low_priority_keys[:len(low_priority_keys)//2]:  # 只清理一半
                block = self.lru_cache.pop(key, None)
                if block and key in self.cache_access_order:
                    self.cache_access_order.remove(key)
                    freed_count += 1
                    freed_size += block.size

            # 执行Python垃圾回收
            gc.collect()

            gc_time = time.time() - gc_start
            logger.info(f"WebGPU垃圾回收完成 - 释放{freed_count}个块, "
                        f"共{freed_size//1024}KB, 耗时{gc_time*1000:.1f}ms")

        except Exception as e:
            logger.error(f"垃圾回收失败: {e}")

    def _update_stats(self):
        """更新统计信息"""
        try:
            total_allocated = sum(len(pool.blocks) * pool.block_size for pool in self.memory_pools.values())
            total_used = sum(pool.used_size for pool in self.memory_pools.values())
            total_free = total_allocated - total_used

            self.stats.total_allocated = total_allocated
            self.stats.total_used = total_used
            self.stats.total_free = total_free

            if total_used > self.stats.peak_usage:
                self.stats.peak_usage = total_used

            # 计算碎片率
            if total_allocated > 0:
                self.stats.fragmentation_rate = (total_allocated - total_used) / total_allocated

            # 更新池统计
            self.stats.pools = {}
            for memory_type, pool in self.memory_pools.items():
                self.stats.pools[memory_type] = {
                    'total_size': pool.total_size,
                    'used_size': pool.used_size,
                    'free_size': pool.total_size - pool.used_size,
                    'block_count': len(pool.blocks),
                    'free_blocks': len(pool.free_blocks)
                }

        except Exception as e:
            logger.error(f"统计更新失败: {e}")

    def _start_monitoring(self):
        """启动内存监控线程"""
        try:
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                return

            self.monitoring_enabled = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="WebGPU-MemoryMonitor"
            )
            self.monitoring_thread.start()

            logger.info("WebGPU内存监控线程已启动")

        except Exception as e:
            logger.error(f"内存监控启动失败: {e}")

    def _monitoring_loop(self):
        """内存监控循环"""
        try:
            while self.monitoring_enabled:
                try:
                    self._update_stats()

                    # 检查内存使用异常
                    self._check_memory_health()

                    time.sleep(5)  # 每5秒检查一次

                except Exception as e:
                    logger.error(f"内存监控循环异常: {e}")
                    time.sleep(1)

        except Exception as e:
            logger.error(f"内存监控线程异常: {e}")

    def _check_memory_health(self):
        """检查内存健康状况"""
        try:
            # 检查内存使用率
            usage_ratio = self.stats.total_used / max(1, self.stats.total_allocated)
            if usage_ratio > 0.9:
                logger.warning(f"WebGPU内存使用率过高: {usage_ratio:.1%}")

            # 检查碎片率
            if self.stats.fragmentation_rate > 0.3:
                logger.warning(f"WebGPU内存碎片率过高: {self.stats.fragmentation_rate:.1%}")

            # 检查长时间未访问的内存块
            current_time = time.time()
            stale_blocks = []

            for block_id, block in self.allocated_blocks.items():
                if current_time - block.last_access_time > 300:  # 5分钟未访问
                    stale_blocks.append(block_id)

            if stale_blocks:
                logger.info(f"发现{len(stale_blocks)}个长时间未访问的内存块")

        except Exception as e:
            logger.error(f"内存健康检查失败: {e}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        try:
            with self.lock:
                self._update_stats()

                return {
                    'total_allocated': self.stats.total_allocated,
                    'total_used': self.stats.total_used,
                    'total_free': self.stats.total_free,
                    'peak_usage': self.stats.peak_usage,
                    'allocation_count': self.stats.allocation_count,
                    'deallocation_count': self.stats.deallocation_count,
                    'cache_hit_rate': self.stats.cache_hit_rate,
                    'fragmentation_rate': self.stats.fragmentation_rate,
                    'cache_size': len(self.lru_cache),
                    'allocated_blocks': len(self.allocated_blocks),
                    'pools': dict(self.stats.pools),
                    'system_memory': self._get_system_memory_info()
                }

        except Exception as e:
            logger.error(f"获取内存统计失败: {e}")
            return {}

    def _get_system_memory_info(self) -> Dict[str, Any]:
        """获取系统内存信息"""
        try:
            memory = psutil.virtual_memory()
            return {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free
            }
        except Exception as e:
            logger.error(f"获取系统内存信息失败: {e}")
            return {}

    def get_optimization_recommendations(self) -> List[str]:
        """获取内存优化建议"""
        try:
            recommendations = []

            with self.lock:
                self._update_stats()

                # 高内存使用率建议
                usage_ratio = self.stats.total_used / max(1, self.stats.total_allocated)
                if usage_ratio > 0.8:
                    recommendations.append("内存使用率过高，建议增加内存池大小或清理未使用的资源")

                # 高碎片率建议
                if self.stats.fragmentation_rate > 0.25:
                    recommendations.append("内存碎片率过高，建议执行内存整理或调整分配策略")

                # 缓存命中率建议
                if self.stats.cache_hit_rate < 0.3:
                    recommendations.append("缓存命中率较低，建议增加缓存大小或优化资源重用")

                # 频繁分配建议
                if len(self.allocated_blocks) > 500:
                    recommendations.append("活跃内存块过多，建议使用对象池模式减少分配频率")

                # 系统内存建议
                system_info = self._get_system_memory_info()
                if system_info.get('percent', 0) > 80:
                    recommendations.append("系统内存使用率过高，建议减少GPU内存池大小")

                if not recommendations:
                    recommendations.append("内存使用状况良好，无需特殊优化")

                return recommendations

        except Exception as e:
            logger.error(f"获取优化建议失败: {e}")
            return ["无法获取优化建议"]

    def force_garbage_collect(self) -> Dict[str, Any]:
        """强制执行垃圾回收"""
        try:
            before_stats = self.get_memory_stats()
            self._garbage_collect()
            after_stats = self.get_memory_stats()

            return {
                'before': before_stats,
                'after': after_stats,
                'freed_memory': before_stats['total_used'] - after_stats['total_used'],
                'freed_blocks': before_stats['allocated_blocks'] - after_stats['allocated_blocks']
            }

        except Exception as e:
            logger.error(f"强制垃圾回收失败: {e}")
            return {}

    def clear_cache(self):
        """清空LRU缓存"""
        try:
            with self.lock:
                cleared_count = len(self.lru_cache)

                # 将缓存的块返回到空闲池
                for block in self.lru_cache.values():
                    pool = self.memory_pools.get(block.memory_type)
                    if pool:
                        pool.free_blocks.append(block)

                self.lru_cache.clear()
                self.cache_access_order.clear()

                logger.info(f"清空了{cleared_count}个缓存块")

        except Exception as e:
            logger.error(f"清空缓存失败: {e}")

    def shutdown(self):
        """关闭内存管理器"""
        try:
            logger.info("正在关闭WebGPU内存管理器...")

            # 停止监控
            self.monitoring_enabled = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2)

            # 释放所有内存
            with self.lock:
                self.allocated_blocks.clear()
                self.lru_cache.clear()
                self.cache_access_order.clear()

                for pool in self.memory_pools.values():
                    pool.blocks.clear()
                    pool.free_blocks.clear()

                self.memory_pools.clear()

            logger.info("WebGPU内存管理器已关闭")

        except Exception as e:
            logger.error(f"内存管理器关闭失败: {e}")


# 全局内存管理器实例
_memory_manager: Optional[WebGPUMemoryManager] = None
_manager_lock = threading.Lock()


def get_webgpu_memory_manager(**kwargs) -> WebGPUMemoryManager:
    """获取WebGPU内存管理器实例（单例模式）"""
    global _memory_manager

    with _manager_lock:
        if _memory_manager is None:
            _memory_manager = WebGPUMemoryManager(**kwargs)
        return _memory_manager


def shutdown_webgpu_memory_manager():
    """关闭WebGPU内存管理器"""
    global _memory_manager

    with _manager_lock:
        if _memory_manager:
            _memory_manager.shutdown()
            _memory_manager = None
