from loguru import logger
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
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from PyQt5.QtCore import QObject, pyqtSignal, QTimer

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
    plugin_timeout_seconds: int = 15  # 插件超时时间（秒）- 减少超时时间，避免长时间阻塞
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
                 config: Optional[SentimentDataServiceConfig] = None):
        """
        初始化情绪数据服务
        """
        super().__init__()

        self.plugin_manager = plugin_manager
        self.config = config or SentimentDataServiceConfig()
        # 纯Loguru架构，移除log_manager依赖

        self._registered_plugins: Dict[str, ISentimentDataSource] = {}
        self._plugin_priorities: Dict[str, int] = {}
        self._plugin_weights: Dict[str, float] = {}

        # 添加选中插件列表管理
        self._selected_plugins: List[str] = []

        self._cached_response: Optional[SentimentResponse] = None
        self._cache_timestamp: Optional[datetime] = None

        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_fetches)

        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._auto_refresh)

        self._is_initialized = False
        self._is_running = False

        # 手动导入并注册核心插件
        self._manual_register_core_plugins()

        # 自动发现并选中已启用的插件
        self._auto_discover_and_select_enabled_plugins()

    def _manual_register_core_plugins(self):
        """手动导入并注册核心的情绪数据插件，确保关键数据源可用"""
        try:
            from plugins.sentiment_data_sources.akshare_sentiment_plugin import AkShareSentimentPlugin
            akshare_plugin = AkShareSentimentPlugin()
            # 使用与插件管理器一致的全限定键，确保数据库与UI一致
            self.register_plugin('sentiment_data_sources.akshare_sentiment_plugin', akshare_plugin, priority=10, weight=1.0)
        except ImportError:
            logger.warning("未能导入AkShare情绪插件，相关功能将不可用。")
        except Exception as e:
            logger.error(f"注册AkShare情绪插件失败: {e}")

    def _auto_discover_sentiment_plugins(self):
        """从插件管理器自动发现并注册情绪插件"""
        if not self.plugin_manager:
            logger.warning(" 插件管理器不可用，无法自动发现情绪插件")
            return

        try:
            # 获取所有插件实例
            all_plugins = self.plugin_manager.get_all_plugins()
            registered_count = 0

            for plugin_name, plugin_instance in all_plugins.items():
                try:
                    # 检查插件是否是情绪数据源
                    if self._is_sentiment_plugin(plugin_instance):
                        # 如果尚未注册，则注册它
                        if plugin_name not in self._registered_plugins:
                            # 获取插件优先级和权重（可以从插件属性或metadata获取）
                            priority = getattr(plugin_instance, 'priority', 50)
                            weight = getattr(plugin_instance, 'weight', 1.0)

                            success = self.register_plugin(plugin_name, plugin_instance, priority, weight)
                            if success:
                                registered_count += 1
                                logger.info(f" 自动注册情绪插件: {plugin_name}")
                            else:
                                logger.warning(f" 自动注册情绪插件失败: {plugin_name}")
                        else:
                            logger.debug(f"插件 {plugin_name} 已注册，跳过")

                except Exception as e:
                    logger.warning(f" 检查插件 {plugin_name} 失败: {e}")

            if registered_count > 0:
                logger.info(f" 自动发现并注册了 {registered_count} 个情绪插件")
            else:
                logger.info(" 未发现新的情绪插件")

        except Exception as e:
            logger.error(f" 自动发现情绪插件失败: {e}")

    def _is_sentiment_plugin(self, plugin_instance) -> bool:
        """检查插件是否是情绪数据源插件"""
        try:
            # 方法1：检查是否实现了ISentimentDataSource接口
            if isinstance(plugin_instance, ISentimentDataSource):
                return True

            # 方法2：检查是否有必要的方法
            required_methods = ['get_sentiment_data', 'get_name']
            if all(hasattr(plugin_instance, method) for method in required_methods):
                return True

            # 方法3：检查插件类名或模块名是否包含sentiment
            class_name = plugin_instance.__class__.__name__.lower()
            module_name = plugin_instance.__class__.__module__.lower()

            if 'sentiment' in class_name or 'sentiment' in module_name:
                # 进一步检查是否有基本的情绪数据方法
                if hasattr(plugin_instance, 'get_sentiment_data'):
                    return True

            return False

        except Exception as e:
            logger.debug(f"检查插件类型失败: {e}")
            return False

    def initialize(self) -> bool:
        """初始化情绪数据服务"""
        try:
            logger.info(" 初始化情绪数据服务...")

            # 在初始化时从插件管理器自动发现并注册情绪插件
            self._auto_discover_sentiment_plugins()

            # 将已注册的情绪插件元信息（中文名/描述）同步写入数据库（不改动启用状态）
            try:
                self._sync_registered_plugins_to_db()
                # 延迟执行孤儿清理，确保所有插件都有机会注册
                self._fully_initialized = False
            except Exception as e:
                logger.warning(f" 同步情绪插件元信息到数据库失败: {e}")

            if self.config.enable_auto_refresh:
                self._start_auto_refresh()

            self._is_initialized = True
            self._is_running = True

            # 标记完全初始化完成，现在可以安全地进行孤儿清理
            self._fully_initialized = True

            # 在完全初始化后再进行孤儿清理
            try:
                self._remove_orphan_db_records()
            except Exception as e:
                logger.warning(f" 清理孤儿插件记录失败: {e}")

            logger.info(f" 情绪数据服务初始化完成，已注册 {len(self._registered_plugins)} 个插件")
            self.service_status_changed.emit("running")

            return True

        except Exception as e:
            logger.error(f" 情绪数据服务初始化失败: {e}")
            return False

    def _sync_registered_plugins_to_db(self) -> None:
        """将已注册的情绪插件元信息写入数据库（保留原有状态）。"""
        try:
            from .plugin_database_service import get_plugin_database_service
            dbs = get_plugin_database_service()

            for name, instance in self._registered_plugins.items():
                try:
                    meta = {}
                    if hasattr(instance, 'metadata'):
                        meta = instance.metadata if isinstance(instance.metadata, dict) else {}

                    display_name = meta.get('name') if isinstance(meta, dict) else None
                    description = meta.get('description') if isinstance(meta, dict) else None
                    author = meta.get('author') if isinstance(meta, dict) else ''
                    version = meta.get('version') if isinstance(meta, dict) else '1.0.0'
                    license_text = meta.get('license') if isinstance(meta, dict) else ''
                    homepage = meta.get('website') if isinstance(meta, dict) else ''
                    repository = meta.get('repository') if isinstance(meta, dict) else ''
                    tags = meta.get('tags') if isinstance(meta, dict) else []

                    # 入口点：module:Class
                    module_name = instance.__class__.__module__
                    class_name = instance.__class__.__name__
                    entry_point = f"{module_name}:{class_name}"

                    payload = {
                        'display_name': display_name or name,
                        'description': description or getattr(instance, '__doc__', '') or '',
                        'version': version,
                        'plugin_type': 'analysis',  # 情绪插件归类为分析类
                        'author': author,
                        'homepage': homepage,
                        'repository': repository,
                        'license': license_text,
                        'tags': tags,
                        'entry_point': entry_point,
                        'path': module_name,
                    }

                    dbs.register_plugin_from_metadata(name, payload)
                except Exception as e:
                    logger.debug(f"同步插件 {name} 到数据库失败: {e}")
        except Exception as e:
            logger.debug(f"初始化数据库服务失败: {e}")

    def _remove_orphan_db_records(self) -> None:
        """删除数据库中不存在于当前注册集合的情绪插件记录。"""
        try:
            # 只有在服务完全初始化后才进行清理，避免误删
            if not hasattr(self, '_fully_initialized') or not self._fully_initialized:
                logger.debug("服务未完全初始化，跳过孤儿插件清理")
                return

            from .plugin_database_service import get_plugin_database_service
            dbs = get_plugin_database_service()
            records = dbs.get_all_plugins(force_refresh=True)
            registered = set(self._registered_plugins.keys())

            # 检查插件管理器中的所有情绪插件
            plugin_manager_plugins = set()
            try:
                if self.plugin_manager:
                    all_plugins = self.plugin_manager.get_all_plugins()
                    for plugin_name in all_plugins.keys():
                        if 'sentiment_data_sources' in plugin_name:
                            plugin_manager_plugins.add(plugin_name)
            except Exception as e:
                logger.debug(f"获取插件管理器插件列表失败: {e}")

            for rec in records:
                name = rec.get('name') or ''
                entry = rec.get('entry_point') or ''
                # 仅对情绪插件命名空间进行清理
                if ('sentiment_data_sources' in name) or ('sentiment_data_sources' in entry):
                    # 只删除既不在注册集合中，也不在插件管理器中的插件
                    if name not in registered and name not in plugin_manager_plugins:
                        # 额外检查：如果插件文件存在，不要删除
                        plugin_exists = False
                        try:
                            import importlib
                            importlib.import_module(name)
                            plugin_exists = True
                        except ImportError:
                            plugin_exists = False

                        # 再次确认：只删除真正不存在的插件，且状态为error或unloaded的
                        rec_status = rec.get('status', '').lower()
                        should_delete = (not plugin_exists and
                                         rec_status in ('error', 'unloaded', 'failed'))

                        if should_delete:
                            try:
                                dbs.remove_plugin(name)
                                logger.info(f" 已删除不存在的情绪插件记录: {name}")
                            except Exception as e:
                                logger.warning(f" 删除情绪插件记录失败 {name}: {e}")
                        else:
                            logger.debug(f"保留插件记录: {name} (状态: {rec_status}, 模块存在: {plugin_exists})")
        except Exception as e:
            logger.debug(f"情绪插件孤儿清理失败: {e}")

    def get_plugin_metadata(self, name: str) -> Dict[str, Any]:
        """获取指定情绪插件的元信息（用于UI展示）。"""
        try:
            inst = self._registered_plugins.get(name)
            if not inst:
                return {}
            meta = {}
            if hasattr(inst, 'metadata'):
                meta = inst.metadata if isinstance(inst.metadata, dict) else {}
            # 补全必要字段
            module_name = inst.__class__.__module__
            class_name = inst.__class__.__name__
            entry_point = f"{module_name}:{class_name}"
            return {
                'name': meta.get('name') if isinstance(meta, dict) else name,
                'display_name': meta.get('name') if isinstance(meta, dict) else name,
                'description': meta.get('description', '') if isinstance(meta, dict) else '',
                'version': meta.get('version', '1.0.0') if isinstance(meta, dict) else '1.0.0',
                'author': meta.get('author', '') if isinstance(meta, dict) else '',
                'entry_point': entry_point,
            }
        except Exception:
            return {}

    def cleanup(self) -> None:
        """清理服务资源"""
        try:
            logger.info(" 清理情绪数据服务...")

            # 停止自动刷新
            self._refresh_timer.stop()

            # 清理插件
            for plugin in self._registered_plugins.values():
                try:
                    if hasattr(plugin, 'cleanup'):
                        plugin.cleanup()
                except Exception as e:
                    logger.warning(f" 清理插件失败: {e}")

            # 关闭执行器
            self._executor.shutdown(wait=True)

            self._is_running = False
            self.service_status_changed.emit("stopped")
            logger.info(" 情绪数据服务清理完成")

        except Exception as e:
            logger.error(f" 清理情绪数据服务失败: {e}")

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
                logger.error(f" 插件 {name} 不是有效的情绪数据源插件")
                return False

            # 初始化插件
            if hasattr(plugin, 'initialize'):
                # 创建一个简单的context或传递None（插件应该能处理None context）
                try:
                    # 尝试传递None，BaseSentimentPlugin已经修改为能处理None context
                    if not plugin.initialize(None):
                        logger.error(f" 插件 {name} 初始化失败")
                        return False
                except TypeError:
                    # 如果插件不需要context参数，尝试无参数调用
                    try:
                        if not plugin.initialize():
                            logger.error(f" 插件 {name} 初始化失败")
                            return False
                    except Exception as e:
                        logger.error(f" 插件 {name} 初始化失败: {e}")
                        return False

            self._registered_plugins[name] = plugin
            self._plugin_priorities[name] = priority
            self._plugin_weights[name] = weight

            logger.info(f" 成功注册情绪数据源插件: {name}")
            return True

        except Exception as e:
            logger.error(f" 注册插件 {name} 失败: {e}")
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
                logger.warning(f" 插件 {name} 未注册")
                return False

            # 清理插件
            plugin = self._registered_plugins[name]
            if hasattr(plugin, 'cleanup'):
                plugin.cleanup()

            # 移除插件
            del self._registered_plugins[name]
            del self._plugin_priorities[name]
            del self._plugin_weights[name]

            logger.info(f" 成功注销情绪数据源插件: {name}")
            return True

        except Exception as e:
            logger.error(f" 注销插件 {name} 失败: {e}")
            return False

    def get_sentiment_data(self, force_refresh: bool = False) -> SentimentResponse:
        """获取聚合的情绪数据"""
        try:
            if not force_refresh and self._is_cache_valid():
                logger.info(" 使用缓存的情绪数据")
                return self._cached_response

            logger.info(" 开始获取最新情绪数据...")

            if not self._registered_plugins:
                logger.warning("没有注册任何情绪数据插件，无法获取数据。")
                return SentimentResponse(success=False, error_message="没有可用的数据源插件。")

            plugin_responses = self._fetch_from_all_plugins()
            aggregated_response = self._aggregate_responses(plugin_responses)

            self._cached_response = aggregated_response
            self._cache_timestamp = datetime.now()

            self.data_updated.emit(aggregated_response)

            logger.info(f" 情绪数据获取完成，共 {len(aggregated_response.data)} 个指标")
            return aggregated_response

        except Exception as e:
            logger.error(f" 获取情绪数据失败: {e}", exc_info=True)
            return SentimentResponse(
                success=False,
                error_message=f"获取情绪数据失败: {str(e)}",
                update_time=datetime.now()
            )

    def get_sentiment_data_async(self, force_refresh: bool = False, callback=None):
        """异步获取情绪数据 - 避免阻塞主线程"""
        from concurrent.futures import ThreadPoolExecutor

        def async_fetch():
            try:
                result = self.get_sentiment_data(force_refresh)
                if callback:
                    callback(result)
                return result
            except Exception as e:
                error_result = SentimentResponse(
                    success=False,
                    error_message=f"异步获取情绪数据失败: {str(e)}",
                    update_time=datetime.now()
                )
                if callback:
                    callback(error_result)
                return error_result

        # 使用线程池执行异步任务
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(async_fetch)
        return future

    def get_available_plugins(self) -> List[str]:
        """获取已注册的插件列表"""
        return list(self._registered_plugins.keys())

    def get_available_plugins_info(self) -> Dict[str, Dict[str, Any]]:
        """获取已注册插件的详细信息，包括中文名称"""
        plugins_info = {}

        for plugin_name, plugin_instance in self._registered_plugins.items():
            try:
                # 获取插件信息
                plugin_info = {}

                # 尝试使用新的get_plugin_info方法
                if hasattr(plugin_instance, 'get_plugin_info'):
                    try:
                        info_obj = plugin_instance.get_plugin_info()
                        plugin_info = {
                            'name': info_obj.name,  # 中文显示名称
                            'display_name': info_obj.name,
                            'description': info_obj.description,
                            'author': info_obj.author,
                            'version': info_obj.version,
                            'plugin_type': info_obj.plugin_type,
                            'category': info_obj.category,
                            'tags': info_obj.tags
                        }
                    except Exception as e:
                        logger.warning(f"获取插件信息失败 {plugin_name}: {e}")

                # 后备方案：使用metadata属性
                if not plugin_info and hasattr(plugin_instance, 'metadata'):
                    try:
                        metadata = plugin_instance.metadata
                        plugin_info = {
                            'name': metadata.get('name', plugin_name),
                            'display_name': metadata.get('name', plugin_name),
                            'description': metadata.get('description', ''),
                            'author': metadata.get('author', ''),
                            'version': metadata.get('version', '1.0.0'),
                            'plugin_type': metadata.get('plugin_type', 'sentiment'),
                            'category': metadata.get('category', 'core'),
                            'tags': metadata.get('tags', [])
                        }
                    except Exception as e:
                        logger.warning(f"获取插件metadata失败 {plugin_name}: {e}")

                # 最后的后备方案
                if not plugin_info:
                    plugin_info = {
                        'name': plugin_name,
                        'display_name': plugin_name,
                        'description': '情绪数据源插件',
                        'author': '未知',
                        'version': '1.0.0',
                        'plugin_type': 'sentiment',
                        'category': 'core',
                        'tags': [],
                        'priority': 100,
                        'weight': 1.0,
                        'registered': True,
                        'internal_name': plugin_name,
                        'error': 'Unknown error'
                    }

                # 添加状态信息
                plugin_info.update({
                    'priority': self._plugin_priorities.get(plugin_name, 100),
                    'weight': self._plugin_weights.get(plugin_name, 1.0),
                    'registered': True,
                    'internal_name': plugin_name  # 保留内部名称用于操作
                })

                plugins_info[plugin_name] = plugin_info

            except Exception as e:
                logger.error(f"获取插件 {plugin_name} 信息失败: {e}")
                # 提供最基本的信息
                plugins_info[plugin_name] = {
                    'name': plugin_name,
                    'display_name': plugin_name,
                    'description': '插件信息获取失败',
                    'author': '未知',
                    'version': '1.0.0',
                    'plugin_type': 'sentiment',
                    'category': 'core',
                    'tags': [],
                    'priority': 100,
                    'weight': 1.0,
                    'registered': True,
                    'internal_name': plugin_name,
                    'error': str(e)
                }

        return plugins_info

    def test_plugin_connection(self, plugin_name: str) -> bool:
        """测试指定插件的连接状态"""
        try:
            if plugin_name not in self._registered_plugins:
                logger.warning(f"插件 {plugin_name} 未注册")
                return False

            plugin = self._registered_plugins[plugin_name]

            # 方法1：检查插件是否有test_connection方法
            if hasattr(plugin, 'test_connection'):
                try:
                    return plugin.test_connection()
                except Exception as e:
                    logger.error(f"插件 {plugin_name} 连接测试失败: {e}")
                    return False

            # 方法2：检查插件是否有is_connected方法
            if hasattr(plugin, 'is_connected'):
                try:
                    return plugin.is_connected()
                except Exception as e:
                    logger.error(f"插件 {plugin_name} 连接状态检查失败: {e}")
                    return False

            # 方法3：尝试获取测试数据
            if hasattr(plugin, 'get_sentiment_data'):
                try:
                    # 尝试获取一个简单的测试数据
                    test_result = plugin.get_sentiment_data('000001', datetime.now() - timedelta(days=1), datetime.now())
                    return test_result is not None and test_result.success
                except Exception as e:
                    logger.error(f"插件 {plugin_name} 数据获取测试失败: {e}")
                    return False

            # 如果都没有，假设连接正常
            logger.info(f"插件 {plugin_name} 无法测试连接，假设正常")
            return True

        except Exception as e:
            logger.error(f"测试插件 {plugin_name} 连接时发生错误: {e}")
            return False

    def enable_plugin(self, plugin_name: str) -> bool:
        """启用指定的情绪数据源插件"""
        try:
            if plugin_name not in self._registered_plugins:
                logger.warning(f"插件 {plugin_name} 未注册，无法启用")
                return False

            plugin = self._registered_plugins[plugin_name]

            # 检查插件是否有启用方法
            if hasattr(plugin, 'enable'):
                try:
                    result = plugin.enable()
                    if result:
                        logger.info(f"插件 {plugin_name} 已启用")

                        # 更新数据库状态
                        self._update_plugin_status_in_db(plugin_name, "enabled")

                        # 如果插件在选中列表中，确保它在活跃状态
                        if plugin_name in self._selected_plugins:
                            self._selected_plugins.remove(plugin_name)
                        self._selected_plugins.append(plugin_name)

                        return True
                    else:
                        logger.warning(f"插件 {plugin_name} 启用失败")
                        return False
                except Exception as e:
                    logger.error(f"插件 {plugin_name} 启用时发生错误: {e}")
                    return False
            else:
                # 插件没有explicit的enable方法，标记为启用状态
                logger.info(f"插件 {plugin_name} 没有enable方法，标记为启用状态")
                self._update_plugin_status_in_db(plugin_name, "enabled")

                if plugin_name not in self._selected_plugins:
                    self._selected_plugins.append(plugin_name)

                return True

        except Exception as e:
            logger.error(f"启用插件 {plugin_name} 时发生错误: {e}")
            return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用指定的情绪数据源插件"""
        try:
            if plugin_name not in self._registered_plugins:
                logger.warning(f"插件 {plugin_name} 未注册，无法禁用")
                return False

            plugin = self._registered_plugins[plugin_name]

            # 检查插件是否有禁用方法
            if hasattr(plugin, 'disable'):
                try:
                    result = plugin.disable()
                    if result:
                        logger.info(f"插件 {plugin_name} 已禁用")

                        # 更新数据库状态
                        self._update_plugin_status_in_db(plugin_name, "disabled")

                        # 从选中列表中移除
                        if plugin_name in self._selected_plugins:
                            self._selected_plugins.remove(plugin_name)

                        return True
                    else:
                        logger.warning(f"插件 {plugin_name} 禁用失败")
                        return False
                except Exception as e:
                    logger.error(f"插件 {plugin_name} 禁用时发生错误: {e}")
                    return False
            else:
                # 插件没有explicit的disable方法，标记为禁用状态
                logger.info(f"插件 {plugin_name} 没有disable方法，标记为禁用状态")
                self._update_plugin_status_in_db(plugin_name, "disabled")

                if plugin_name in self._selected_plugins:
                    self._selected_plugins.remove(plugin_name)

                return True

        except Exception as e:
            logger.error(f"禁用插件 {plugin_name} 时发生错误: {e}")
            return False

    def set_plugin_enabled(self, plugin_name: str, enabled: bool) -> bool:
        """设置插件的启用状态"""
        if enabled:
            return self.enable_plugin(plugin_name)
        else:
            return self.disable_plugin(plugin_name)

    def _update_plugin_status_in_db(self, plugin_name: str, status: str):
        """更新插件在数据库中的状态"""
        try:
            from core.services.plugin_database_service import get_plugin_database_service
            from db.models.plugin_models import PluginStatus

            db_service = get_plugin_database_service()
            if db_service:
                # 映射状态到数据库枚举
                status_mapping = {
                    'enabled': PluginStatus.ENABLED,
                    'disabled': PluginStatus.DISABLED,
                    'error': PluginStatus.ERROR
                }

                db_status = status_mapping.get(status, PluginStatus.LOADED)
                db_service.update_plugin_status(plugin_name, db_status, f"情绪数据服务{status}")

        except Exception as e:
            logger.warning(f"更新插件 {plugin_name} 数据库状态失败: {e}")

    def get_plugin_status(self, name: str) -> Dict[str, Any]:
        """
        获取插件状态

        Args:
            name: 插件名称

        Returns:
            Dict[str, Any]: 插件状态信息
        """
        if name not in self._registered_plugins:
            return {
                "status": "not_registered",
                "enabled": False,
                "is_connected": False,
                "last_response_time": 0,
                "error_count": 0,
                "last_update": datetime.now(),
                "priority": 100,
                "weight": 1.0
            }

        plugin = self._registered_plugins[name]

        # 检查插件是否启用（在选中列表中）
        is_enabled = name in self._selected_plugins if self._selected_plugins else True

        # 检查连接状态
        is_connected = False
        try:
            if hasattr(plugin, 'is_connected'):
                is_connected = plugin.is_connected()
            elif hasattr(plugin, 'test_connection'):
                is_connected = plugin.test_connection()
            else:
                # 如果没有连接检查方法，假设已连接
                is_connected = True
        except Exception as e:
            logger.debug(f"检查插件 {name} 连接状态失败: {e}")
            is_connected = False

        # 获取响应时间（如果插件支持）
        last_response_time = 0
        try:
            if hasattr(plugin, 'get_last_response_time'):
                last_response_time = plugin.get_last_response_time()
            elif hasattr(plugin, 'response_time'):
                last_response_time = getattr(plugin, 'response_time', 0)
        except:
            pass

        # 获取错误计数（如果插件支持）
        error_count = 0
        try:
            if hasattr(plugin, 'get_error_count'):
                error_count = plugin.get_error_count()
            elif hasattr(plugin, 'error_count'):
                error_count = getattr(plugin, 'error_count', 0)
        except:
            pass

        # 获取最后更新时间
        last_update = datetime.now()
        try:
            if hasattr(plugin, 'get_last_update'):
                last_update = plugin.get_last_update()
            elif hasattr(plugin, 'last_update'):
                last_update = getattr(plugin, 'last_update', datetime.now())
        except:
            pass

        return {
            "status": "registered",
            "enabled": is_enabled,
            "is_connected": is_connected,
            "last_response_time": last_response_time,
            "error_count": error_count,
            "last_update": last_update,
            "priority": self._plugin_priorities.get(name, 100),
            "weight": self._plugin_weights.get(name, 1.0),
            "available_indicators": plugin.get_available_indicators() if hasattr(plugin, 'get_available_indicators') else []
        }

    def set_selected_plugins(self, selected_plugins: List[str]) -> None:
        """
        设置要使用的插件列表

        Args:
            selected_plugins: 选中的插件名称列表
        """
        # 验证插件是否已注册
        valid_plugins = []
        for plugin_name in selected_plugins:
            if plugin_name in self._registered_plugins:
                valid_plugins.append(plugin_name)
            else:
                logger.warning(f" 插件 {plugin_name} 未注册，跳过")

        self._selected_plugins = valid_plugins
        logger.info(f" 设置选中插件: {self._selected_plugins}")

    def get_selected_plugins(self) -> List[str]:
        """
        获取当前选中的插件列表

        Returns:
            List[str]: 选中的插件名称列表
        """
        return self._selected_plugins.copy()

    def clear_selected_plugins(self) -> None:
        """清空选中的插件列表"""
        self._selected_plugins = []
        logger.info(" 已清空选中插件列表")

    def _fetch_from_all_plugins(self) -> Dict[str, SentimentResponse]:
        """并发从被勾选插件获取数据"""
        plugin_responses = {}

        # 确定要使用的插件列表
        plugins_to_use = {}
        if self._selected_plugins:
            # 使用被选中的插件
            for plugin_name in self._selected_plugins:
                if plugin_name in self._registered_plugins:
                    plugins_to_use[plugin_name] = self._registered_plugins[plugin_name]
                else:
                    logger.warning(f" 选中的插件 {plugin_name} 未注册")
            logger.info(f" 使用选中的插件: {list(plugins_to_use.keys())}")
        else:
            # 如果没有设置选中插件，使用所有已注册的插件
            plugins_to_use = self._registered_plugins
            logger.info(f" 未设置选中插件，使用所有已注册插件: {list(plugins_to_use.keys())}")

        if not plugins_to_use:
            logger.warning(" 没有可用的插件进行数据获取")
            return plugin_responses

        # 按优先级排序插件
        sorted_plugins = sorted(
            plugins_to_use.items(),
            key=lambda x: self._plugin_priorities.get(x[0], 100)
        )

        # 提交并发任务
        future_to_plugin = {}
        for plugin_name, plugin in sorted_plugins:
            future = self._executor.submit(self._fetch_from_plugin, plugin_name, plugin)
            future_to_plugin[future] = plugin_name

        # 收集结果 - 改进超时处理，避免阻塞主线程
        completed_futures = set()
        try:
            for future in as_completed(future_to_plugin, timeout=self.config.plugin_timeout_seconds):
                completed_futures.add(future)
                plugin_name = future_to_plugin[future]
                try:
                    response = future.result()
                    plugin_responses[plugin_name] = response

                    if response.success:
                        logger.info(f" 从插件 {plugin_name} 获取数据成功")
                    else:
                        logger.warning(f" 插件 {plugin_name} 返回错误: {response.error_message}")

                except Exception as e:
                    logger.error(f" 从插件 {plugin_name} 获取数据失败: {e}")
                    self.plugin_error.emit(plugin_name, str(e))

        except TimeoutError as e:
            # 处理超时的future，避免完全阻塞
            unfinished_futures = set(future_to_plugin.keys()) - completed_futures
            logger.warning(f" {len(unfinished_futures)} 个插件超时，继续处理已完成的插件")

            # 取消未完成的future
            for future in unfinished_futures:
                plugin_name = future_to_plugin[future]
                logger.warning(f" 插件 {plugin_name} 执行超时，已取消")
                future.cancel()  # 尝试取消未完成的任务
                self.plugin_error.emit(plugin_name, "插件执行超时")

        return plugin_responses

    def _fetch_from_plugin(self, plugin_name: str, plugin: ISentimentDataSource) -> SentimentResponse:
        """从单个插件获取数据"""
        try:
            response = plugin.fetch_sentiment_data()

            # 兼容性保护：插件可能错误地返回了 None
            if response is None:
                return SentimentResponse(
                    success=False,
                    error_message=f"插件 {plugin_name} 返回空结果(None)",
                    update_time=datetime.now()
                )

            # 验证数据质量
            if response.success and response.data:
                quality = plugin.validate_data_quality(response.data)
                response.data_quality = quality

                # 检查是否满足最低质量要求
                quality_levels = ['poor', 'fair', 'good', 'excellent']
                min_level_index = quality_levels.index(self.config.min_data_quality_threshold)
                current_level_index = quality_levels.index(quality) if quality in quality_levels else 0

                if current_level_index < min_level_index:
                    logger.warning(f" 插件 {plugin_name} 数据质量不满足要求: {quality}")

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
            logger.error(f" 聚合情绪数据失败: {e}")
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
            logger.info(f" 启动自动刷新，间隔 {self.config.auto_refresh_interval_minutes} 分钟")

    def _auto_refresh(self) -> None:
        """自动刷新数据"""
        try:
            logger.info("⏰ 执行自动刷新...")
            self.get_sentiment_data(force_refresh=True)
        except Exception as e:
            logger.error(f" 自动刷新失败: {e}")

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

    def _auto_discover_and_select_enabled_plugins(self):
        """自动发现并选中已启用的插件"""
        try:
            # 从数据库获取已启用的情绪插件
            from core.services.plugin_database_service import PluginDatabaseService
            db_service = PluginDatabaseService()
            all_plugins = db_service.get_all_plugins()

            enabled_sentiment_plugins = []
            for plugin_data in all_plugins:
                plugin_name = plugin_data.get('name', '')
                plugin_status = plugin_data.get('status', '')

                if (plugin_status == 'enabled' and
                        'sentiment_data_sources' in plugin_name):
                    enabled_sentiment_plugins.append(plugin_name)

            # 选中所有已启用的情绪插件
            for plugin_name in enabled_sentiment_plugins:
                if plugin_name not in self._selected_plugins:
                    self._selected_plugins.append(plugin_name)
                    logger.info(f" 自动选中已启用的情绪插件: {plugin_name}")

            if enabled_sentiment_plugins:
                logger.info(f" 已选中 {len(enabled_sentiment_plugins)} 个情绪插件")
            else:
                logger.warning(" 没有找到已启用的情绪插件")

        except Exception as e:
            logger.error(f" 自动发现插件失败: {e}")
