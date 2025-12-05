from loguru import logger
#!/usr/bin/env python3
"""
增强版异步插件发现服务

在原有异步插件发现基础上添加：
- 批量处理优化
- 缓存机制
- 并发控制
- 性能监控
"""

import threading
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

class PluginCache:
    """插件缓存管理器"""

    def __init__(self, cache_dir: str = "cache/plugins"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "plugin_discovery_cache.json"
        self.cache_data = self._load_cache()

    def _load_cache(self) -> dict:
        """加载缓存数据"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载插件缓存失败: {e}")
        return {}

    def _save_cache(self):
        """保存缓存数据"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存插件缓存失败: {e}")

    def get_plugin_hash(self, plugin_path: Path) -> str:
        """计算插件文件哈希"""
        try:
            with open(plugin_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.warning(f"计算插件哈希失败 {plugin_path}: {e}")
            return ""

    def is_plugin_cached(self, plugin_path: Path) -> bool:
        """检查插件是否已缓存且未修改"""
        try:
            plugin_key = str(plugin_path)
            if plugin_key not in self.cache_data:
                return False

            cached_info = self.cache_data[plugin_key]
            current_hash = self.get_plugin_hash(plugin_path)
            cached_hash = cached_info.get('hash', '')

            return current_hash == cached_hash and current_hash != ""
        except Exception as e:
            logger.warning(f"检查插件缓存失败 {plugin_path}: {e}")
            return False

    def get_cached_plugin_info(self, plugin_path: Path) -> Optional[dict]:
        """获取缓存的插件信息"""
        try:
            plugin_key = str(plugin_path)
            if self.is_plugin_cached(plugin_path):
                return self.cache_data[plugin_key].get('info')
        except Exception as e:
            logger.warning(f"获取缓存插件信息失败 {plugin_path}: {e}")
        return None

    def cache_plugin_info(self, plugin_path: Path, plugin_info: dict):
        """缓存插件信息"""
        try:
            plugin_key = str(plugin_path)
            plugin_hash = self.get_plugin_hash(plugin_path)

            self.cache_data[plugin_key] = {
                'hash': plugin_hash,
                'info': plugin_info,
                'cached_at': datetime.now().isoformat(),
                'access_count': self.cache_data.get(plugin_key, {}).get('access_count', 0) + 1
            }

            # 定期保存缓存
            if len(self.cache_data) % 10 == 0:
                self._save_cache()

        except Exception as e:
            logger.error(f"缓存插件信息失败 {plugin_path}: {e}")

    def cleanup_old_cache(self, days: int = 7):
        """清理过期缓存"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            keys_to_remove = []

            for key, info in self.cache_data.items():
                cached_at = datetime.fromisoformat(info.get('cached_at', '1970-01-01'))
                if cached_at < cutoff_date:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self.cache_data[key]

            if keys_to_remove:
                self._save_cache()
                logger.info(f"清理了 {len(keys_to_remove)} 个过期缓存项")

        except Exception as e:
            logger.error(f"清理缓存失败: {e}")

class BatchPluginProcessor:
    """批量插件处理器"""

    def __init__(self, max_workers: int = 4, batch_size: int = 10):
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def process_plugins_batch(self, plugin_files: List[tuple], plugin_manager, cache: PluginCache) -> List[dict]:
        """批量处理插件"""
        results = []

        # 将插件分批处理
        for i in range(0, len(plugin_files), self.batch_size):
            batch = plugin_files[i:i + self.batch_size]
            batch_results = self._process_single_batch(batch, plugin_manager, cache)
            results.extend(batch_results)

            # 给UI更新时间
            time.sleep(0.01)

        return results

    def _process_single_batch(self, batch: List[tuple], plugin_manager, cache: PluginCache) -> List[dict]:
        """处理单个批次"""
        futures = []

        for plugin_name, plugin_path in batch:
            future = self.executor.submit(
                self._process_single_plugin,
                plugin_name,
                plugin_path,
                plugin_manager,
                cache
            )
            futures.append((future, plugin_name, plugin_path))

        results = []
        for future, plugin_name, plugin_path in futures:
            try:
                result = future.result(timeout=30)  # 30秒超时
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"批量处理插件失败 {plugin_name}: {e}")
                results.append({
                    'name': plugin_name,
                    'path': str(plugin_path),
                    'status': 'failed',
                    'error': str(e)
                })

        return results

    def _process_single_plugin(self, plugin_name: str, plugin_path: Path, plugin_manager, cache: PluginCache) -> Optional[dict]:
        """处理单个插件"""
        try:
            # 检查缓存
            cached_info = cache.get_cached_plugin_info(plugin_path)
            if cached_info:
                logger.debug(f"使用缓存的插件信息: {plugin_name}")
                return {
                    'name': plugin_name,
                    'path': str(plugin_path),
                    'status': 'cached',
                    'info': cached_info
                }

            # 加载插件
            success = plugin_manager.load_plugin(plugin_name, plugin_path)

            plugin_info = {
                'name': plugin_name,
                'path': str(plugin_path),
                'status': 'loaded' if success else 'failed',
                'loaded_at': datetime.now().isoformat()
            }

            # 缓存插件信息
            if success:
                cache.cache_plugin_info(plugin_path, plugin_info)

            return plugin_info

        except Exception as e:
            logger.warning(f"处理插件失败 {plugin_name}: {e}")
            return {
                'name': plugin_name,
                'path': str(plugin_path),
                'status': 'failed',
                'error': str(e)
            }

    def cleanup(self):
        """清理资源"""
        self.executor.shutdown(wait=True)

class EnhancedAsyncPluginDiscoveryWorker(QThread):
    """增强版异步插件发现工作线程"""

    # 信号定义
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 状态消息
    plugin_discovered = pyqtSignal(str, dict)  # 插件名称, 插件信息
    batch_completed = pyqtSignal(int, int)  # 已完成批次, 总批次
    discovery_completed = pyqtSignal(dict)  # 发现结果统计
    discovery_failed = pyqtSignal(str)  # 错误消息
    performance_stats = pyqtSignal(dict)  # 性能统计

    def __init__(self, plugin_manager, data_standardizer, config: dict = None, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.data_standardizer = data_standardizer
        self._stop_requested = False

        # 配置参数
        self.config = config or {}
        self.max_workers = self.config.get('max_workers', 4)
        self.batch_size = self.config.get('batch_size', 10)
        self.enable_cache = self.config.get('enable_cache', True)

        # 组件初始化
        self.cache = PluginCache() if self.enable_cache else None
        self.batch_processor = BatchPluginProcessor(self.max_workers, self.batch_size)

        # 性能统计
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_plugins': 0,
            'cached_plugins': 0,
            'loaded_plugins': 0,
            'failed_plugins': 0,
            'batches_processed': 0
        }

    def run(self):
        """执行增强版插件发现过程"""
        try:
            self.stats['start_time'] = time.time()
            logger.info("开始增强版异步插件发现...")
            self.progress_updated.emit(0, "初始化增强版插件发现...")

            # 清理过期缓存
            if self.cache:
                self.cache.cleanup_old_cache()

            # 1. 插件管理器插件发现 (0-50%)
            self.progress_updated.emit(10, "扫描插件目录...")
            self._discover_plugins_enhanced()

            if self._stop_requested:
                return

            # 2. 数据源插件发现 (50-100%)
            self.progress_updated.emit(50, "注册数据源插件...")
            self._discover_data_source_plugins_async()

            if self._stop_requested:
                return

            # 完成统计
            self.stats['end_time'] = time.time()
            self._emit_performance_stats()

            # 完成
            self.progress_updated.emit(100, "增强版插件发现完成")
            self.discovery_completed.emit({
                'status': 'success',
                'message': '增强版插件发现和注册完成',
                'stats': self.stats
            })

        except Exception as e:
            logger.error(f"增强版异步插件发现失败: {e}")
            self.discovery_failed.emit(str(e))
        finally:
            self.batch_processor.cleanup()

    def _discover_plugins_enhanced(self):
        """增强版插件发现"""
        try:
            if not self.plugin_manager:
                return

            # 扫描插件目录
            self.progress_updated.emit(15, "扫描插件文件...")
            plugin_files = self._scan_plugin_files()

            if not plugin_files:
                self.progress_updated.emit(40, "未发现插件文件")
                return

            self.stats['total_plugins'] = len(plugin_files)

            # 批量处理插件
            self.progress_updated.emit(20, f"开始批量处理 {len(plugin_files)} 个插件...")

            total_batches = (len(plugin_files) + self.batch_size - 1) // self.batch_size

            for i in range(0, len(plugin_files), self.batch_size):
                if self._stop_requested:
                    break

                batch = plugin_files[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1

                progress = 20 + (20 * batch_num // total_batches)
                self.progress_updated.emit(progress, f"处理批次 {batch_num}/{total_batches}")

                # 处理批次
                batch_results = self.batch_processor._process_single_batch(
                    batch, self.plugin_manager, self.cache
                )

                # 统计结果
                for result in batch_results:
                    status = result.get('status', 'unknown')
                    if status == 'cached':
                        self.stats['cached_plugins'] += 1
                    elif status == 'loaded':
                        self.stats['loaded_plugins'] += 1
                    else:
                        self.stats['failed_plugins'] += 1

                    self.plugin_discovered.emit(result['name'], result)

                self.stats['batches_processed'] += 1
                self.batch_completed.emit(batch_num, total_batches)

                # 避免过快执行，给UI更新时间
                self.msleep(50)

            self.progress_updated.emit(40, f"插件批量处理完成")

        except Exception as e:
            logger.error(f"增强版插件发现失败: {e}")
            raise

    def _discover_data_source_plugins_async(self):
        """异步发现数据源插件"""
        try:
            if not self.data_standardizer:
                self.progress_updated.emit(90, "数据标准化器未就绪，跳过插件发现")
                return

            self.progress_updated.emit(60, "注册数据源插件...")

            # 数据标准化器模式下跳过插件发现过程
            self.progress_updated.emit(90, "数据源插件注册完成（数据标准化器模式）")

        except Exception as e:
            logger.error(f"数据源插件发现失败: {e}")
            raise

    def _scan_plugin_files(self) -> List[tuple]:
        """扫描插件文件"""
        plugin_files = []

        try:
            plugin_dir = self.plugin_manager.plugin_dir
            if not plugin_dir.exists():
                return plugin_files

            excluded_files = ["plugin_interface.py", "plugin_market.py", "__init__.py"]

            # 扫描主插件目录
            for plugin_path in plugin_dir.glob("*.py"):
                if plugin_path.name not in excluded_files and not plugin_path.name.startswith("__"):
                    plugin_files.append((plugin_path.stem, plugin_path))

            # 扫描子目录
            for subdir in ["examples", "sentiment_data_sources", "data_sources", "strategies"]:
                sub_path = plugin_dir / subdir
                if sub_path.exists():
                    for plugin_path in sub_path.glob("*.py"):
                        if plugin_path.name not in excluded_files and not plugin_path.name.startswith("__"):
                            plugin_name = f"{subdir}.{plugin_path.stem}"
                            plugin_files.append((plugin_name, plugin_path))

        except Exception as e:
            logger.error(f"扫描插件文件失败: {e}")

        return plugin_files

    def _emit_performance_stats(self):
        """发送性能统计"""
        try:
            duration = self.stats['end_time'] - self.stats['start_time']

            performance_data = {
                'duration_seconds': duration,
                'total_plugins': self.stats['total_plugins'],
                'cached_plugins': self.stats['cached_plugins'],
                'loaded_plugins': self.stats['loaded_plugins'],
                'failed_plugins': self.stats['failed_plugins'],
                'batches_processed': self.stats['batches_processed'],
                'plugins_per_second': self.stats['total_plugins'] / duration if duration > 0 else 0,
                'cache_hit_rate': self.stats['cached_plugins'] / self.stats['total_plugins'] if self.stats['total_plugins'] > 0 else 0
            }

            self.performance_stats.emit(performance_data)
            logger.info(f"插件发现性能统计: {performance_data}")

        except Exception as e:
            logger.error(f"发送性能统计失败: {e}")

    def stop(self):
        """停止插件发现"""
        self._stop_requested = True
        self.batch_processor.cleanup()
        self.quit()
        self.wait(5000)  # 等待最多5秒

class EnhancedAsyncPluginDiscoveryService(QObject):
    """增强版异步插件发现服务"""

    # 信号定义
    discovery_started = pyqtSignal()
    progress_updated = pyqtSignal(int, str)
    plugin_discovered = pyqtSignal(str, dict)
    batch_completed = pyqtSignal(int, int)
    discovery_completed = pyqtSignal(dict)
    discovery_failed = pyqtSignal(str)
    performance_stats = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.is_discovering = False

        # 默认配置
        self.config = {
            'max_workers': 4,
            'batch_size': 10,
            'enable_cache': True,
            'cache_cleanup_days': 7
        }

    def configure(self, config: dict):
        """配置服务参数"""
        self.config.update(config)

    def start_discovery(self, plugin_manager, data_standardizer):
        """开始增强版异步插件发现"""
        if self.is_discovering:
            logger.warning("增强版插件发现已在进行中")
            return

        try:
            logger.info("启动增强版异步插件发现服务...")

            # 创建工作线程
            self.worker = EnhancedAsyncPluginDiscoveryWorker(
                plugin_manager, data_standardizer, self.config
            )

            # 连接信号
            self.worker.progress_updated.connect(self.progress_updated.emit)
            self.worker.plugin_discovered.connect(self.plugin_discovered.emit)
            self.worker.batch_completed.connect(self.batch_completed.emit)
            self.worker.discovery_completed.connect(self._on_discovery_completed)
            self.worker.discovery_failed.connect(self._on_discovery_failed)
            self.worker.performance_stats.connect(self.performance_stats.emit)

            # 启动工作线程
            self.worker.start()
            self.is_discovering = True
            self.discovery_started.emit()

            logger.info("增强版异步插件发现服务已启动")

        except Exception as e:
            logger.error(f"启动增强版异步插件发现失败: {e}")
            self.discovery_failed.emit(str(e))

    def stop_discovery(self):
        """停止插件发现"""
        if self.worker and self.is_discovering:
            logger.info("停止增强版异步插件发现...")
            self.worker.stop()
            self.worker = None
            self.is_discovering = False

    def _on_discovery_completed(self, result: dict):
        """插件发现完成"""
        self.is_discovering = False
        self.discovery_completed.emit(result)
        logger.info("增强版异步插件发现完成")

    def _on_discovery_failed(self, error_msg: str):
        """插件发现失败"""
        self.is_discovering = False
        self.discovery_failed.emit(error_msg)
        logger.error(f"增强版异步插件发现失败: {error_msg}")

# 全局服务实例
_enhanced_async_plugin_discovery_service = None

def get_enhanced_async_plugin_discovery_service() -> EnhancedAsyncPluginDiscoveryService:
    """获取增强版异步插件发现服务实例"""
    global _enhanced_async_plugin_discovery_service
    if _enhanced_async_plugin_discovery_service is None:
        _enhanced_async_plugin_discovery_service = EnhancedAsyncPluginDiscoveryService()
    return _enhanced_async_plugin_discovery_service
