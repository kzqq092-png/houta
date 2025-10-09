from loguru import logger
#!/usr/bin/env python3
"""
异步数据导入管理器

提供异步的DuckDB数据导入功能，使用Qt信号机制
避免阻塞主线程，提供实时进度更新。
"""

import threading
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

logger = logger


class AsyncDataImportWorker(QThread):
    """异步数据导入工作线程"""

    # 信号定义
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 状态消息
    import_started = pyqtSignal(str)  # 导入任务ID
    import_completed = pyqtSignal(str, dict)  # 任务ID, 结果统计
    import_failed = pyqtSignal(str, str)  # 任务ID, 错误消息
    data_chunk_imported = pyqtSignal(str, int, int)  # 任务ID, 已导入数量, 总数量

    def __init__(self, import_config: dict, parent=None):
        super().__init__(parent)
        self.import_config = import_config
        self.task_id = import_config.get('task_id', f"import_{int(time.time())}")
        self._stop_requested = False
        self._import_engine = None
        self._config_manager = None  # 保存配置管理器引用

    def run(self):
        """执行数据导入过程"""
        try:
            logger.info(f"开始异步数据导入任务: {self.task_id}")
            self.import_started.emit(self.task_id)
            self.progress_updated.emit(0, "初始化数据导入...")

            # 初始化导入引擎
            logger.info("开始初始化导入引擎...")
            self._initialize_import_engine()
            logger.info("导入引擎初始化完成")

            if self._stop_requested:
                logger.info("任务被请求停止，退出执行")
                return
            else:
                logger.info("任务未被停止，继续执行")

            # 执行数据导入
            logger.info("开始执行数据导入...")
            result = self._execute_import()
            logger.info(f" 数据导入执行完成，结果: {result}")

            if self._stop_requested:
                logger.info("任务在执行后被请求停止")
                return

            # 完成导入
            self.progress_updated.emit(100, "数据导入完成")
            self.import_completed.emit(self.task_id, result)
            logger.info(f" 异步数据导入任务完成: {self.task_id}")

        except Exception as e:
            logger.error(f" 异步数据导入失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self.import_failed.emit(self.task_id, str(e))

    def _initialize_import_engine(self):
        """初始化导入引擎"""
        try:
            self.progress_updated.emit(5, "初始化导入引擎...")

            # 导入数据导入相关模块
            from core.importdata.import_execution_engine import DataImportExecutionEngine
            from core.importdata.import_config_manager import ImportConfigManager

            # 创建配置管理器和执行引擎
            self._config_manager = ImportConfigManager()

            # 尝试从服务容器获取数据管理器，避免重复初始化
            data_manager = None
            try:
                from core.containers import get_service_container
                from core.services.unified_data_manager import UnifiedDataManager

                service_container = get_service_container()
                if service_container.is_registered(UnifiedDataManager):
                    data_manager = service_container.resolve(UnifiedDataManager)
                    logger.info("使用服务容器中的数据管理器")
                else:
                    logger.info("服务容器中未找到数据管理器，将延迟初始化")
            except Exception as e:
                logger.warning(f" 获取数据管理器失败: {e}")

            self._import_engine = DataImportExecutionEngine(self._config_manager, data_manager)

            # 连接进度信号
            self._import_engine.task_progress.connect(self._on_engine_progress)

            self.progress_updated.emit(10, "导入引擎初始化完成")

        except Exception as e:
            logger.error(f"初始化导入引擎失败: {e}")
            raise

    def _execute_import(self) -> dict:
        """执行数据导入"""
        try:
            self.progress_updated.emit(15, "开始数据导入...")

            # 解析导入配置
            import_mode = self.import_config.get('mode', 'incremental')
            data_sources = self.import_config.get('data_sources', [])
            date_range = self.import_config.get('date_range', {})

            result = {
                'task_id': self.task_id,
                'status': 'success',
                'imported_count': 0,
                'failed_count': 0,
                'start_time': datetime.now().isoformat(),
                'data_sources': []
            }

            # 执行真实的数据导入逻辑 - 批量处理股票代码
            if data_sources and len(data_sources) > 1:
                # 批量处理模式：将所有股票代码作为一个批次处理
                logger.info(f" 开始批量处理股票代码，总数: {len(data_sources)}, 股票代码列表: {data_sources[:5]}{'...' if len(data_sources) > 5 else ''}")

                self.progress_updated.emit(20, f"批量导入 {len(data_sources)} 只股票数据")

                # 执行批量导入
                batch_result = self._import_batch_sources(data_sources, self.import_config)
                logger.info(f" 批量处理完成，结果: {batch_result}")

                result['data_sources'].append(batch_result)
                result['imported_count'] += batch_result.get('imported_count', 0)
                result['failed_count'] += batch_result.get('failed_count', 0)
            else:
                # 单股票处理模式（保持原有逻辑）
                total_sources = len(data_sources) if data_sources else 1
                logger.info(f" 开始处理股票代码，总数: {total_sources}, 股票代码列表: {data_sources or ['default']}")

                for i, source in enumerate(data_sources or ['default']):
                    if self._stop_requested:
                        break

                    base_progress = 15 + (70 * i // total_sources)
                    self.progress_updated.emit(base_progress, f"导入股票代码: {source}")
                    logger.info(f" 开始处理股票代码 {i+1}/{total_sources}: {source}")

                    # 执行单个数据源的导入
                    source_result = self._import_single_source(source, base_progress, self.import_config)
                    logger.info(f" 股票代码 {source} 处理完成: {source_result}")
                    result['data_sources'].append(source_result)
                    result['imported_count'] += source_result.get('imported_count', 0)
                    result['failed_count'] += source_result.get('failed_count', 0)

            result['end_time'] = datetime.now().isoformat()
            self.progress_updated.emit(90, "数据导入处理完成")

            return result

        except Exception as e:
            logger.error(f" 执行股票代码导入失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            raise

    def _import_single_source(self, source: str, base_progress: int, import_config: dict) -> dict:
        """导入单个股票代码"""
        try:
            # 调用实际的数据导入引擎
            if self._import_engine:
                # 创建临时任务配置用于导入
                from core.importdata.import_config_manager import ImportTaskConfig, ImportMode, DataFrequency
                from datetime import datetime, timedelta
                import time

                # 创建临时任务ID
                temp_task_id = f"async_import_{source}_{int(time.time())}"

                # 创建任务配置 - 使用原始任务的动态配置参数
                date_range = import_config.get('date_range', {})
                task_config = ImportTaskConfig(
                    task_id=temp_task_id,
                    name=f"异步导入_{source}",
                    data_source=import_config.get('data_source', 'examples.akshare_stock_plugin'),  # 使用原始任务的数据源
                    asset_type=import_config.get('asset_type', '股票'),    # 使用原始任务的资产类型
                    data_type=import_config.get('data_type', 'K线数据'),  # 使用原始任务的数据类型
                    mode=ImportMode.BATCH,  # 修复：使用存在的枚举值
                    symbols=[source],  # 使用实际的股票代码，而不是硬编码的000001
                    frequency=import_config.get('frequency', DataFrequency.DAILY),  # 使用原始任务的频率
                    start_date=date_range.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')),  # 使用原始任务的开始日期
                    end_date=date_range.get('end_date', datetime.now().strftime('%Y-%m-%d')),  # 使用原始任务的结束日期
                    batch_size=import_config.get('batch_size', 50),  # 使用原始任务的批处理大小
                    max_workers=import_config.get('max_workers', 1)   # 使用原始任务的最大工作线程数
                )

                # 不将临时任务添加到配置管理器，避免在任务列表中显示多个任务
                # 直接使用导入引擎执行任务，不持久化临时任务配置
                logger.info(f" 直接执行股票代码导入任务: {temp_task_id}")

                # 检查导入引擎是否可用
                if not self._import_engine:
                    logger.error("导入引擎未初始化")
                    return {
                        'source': source,
                        'imported_count': 0,
                        'failed_count': 1,
                        'status': 'failed',
                        'error': '导入引擎未初始化'
                    }

                # 临时添加任务配置到导入引擎的内存中，不持久化到数据库
                logger.info(f" 临时添加任务配置到内存: {temp_task_id}")
                self._import_engine.config_manager._tasks[temp_task_id] = task_config

                # 启动任务
                logger.info(f" 启动临时股票代码导入任务: {temp_task_id}")
                success = self._import_engine.start_task(temp_task_id)
                logger.info(f" 任务启动结果: {success}")

                if success:
                    # 等待任务完成（简化处理）
                    max_wait = 30  # 最多等待30秒
                    wait_count = 0

                    while wait_count < max_wait:
                        task_result = self._import_engine.get_task_status(temp_task_id)
                        if task_result and task_result.status.name in ['COMPLETED', 'FAILED']:
                            break
                        time.sleep(1)
                        wait_count += 1

                        # 更新进度
                        progress = base_progress + (20 * wait_count // max_wait)
                        self.progress_updated.emit(progress, f"正在导入股票代码 {source}...")

                    # 获取最终结果
                    final_result = self._import_engine.get_task_status(temp_task_id)

                    # 清理临时任务配置（从内存中清理）
                    try:
                        if temp_task_id in self._import_engine.config_manager._tasks:
                            del self._import_engine.config_manager._tasks[temp_task_id]
                        if temp_task_id in self._import_engine.config_manager._progress:
                            del self._import_engine.config_manager._progress[temp_task_id]
                        logger.info(f" 已清理临时股票代码任务配置: {temp_task_id}")
                    except Exception as e:
                        logger.warning(f" 清理临时股票代码任务配置失败: {e}")

                    if final_result:
                        return {
                            'source': source,
                            'imported_count': final_result.processed_records,
                            'failed_count': final_result.failed_records,
                            'status': 'completed' if final_result.status.name == 'COMPLETED' else 'failed'
                        }
                    else:
                        return {
                            'source': source,
                            'imported_count': 0,
                            'failed_count': 1,
                            'status': 'failed',
                            'error': '股票代码执行超时'
                        }
                else:
                    # 任务启动失败，清理临时任务配置
                    try:
                        self._config_manager.remove_import_task(temp_task_id)
                        logger.info(f" 已清理失败的临时股票代码任务配置: {temp_task_id}")
                    except Exception as e:
                        logger.warning(f" 清理失败的临时任务配置失败: {e}")

                    return {
                        'source': source,
                        'imported_count': 0,
                        'failed_count': 1,
                        'status': 'failed',
                        'error': '任务启动失败'
                    }
            else:
                # 没有导入引擎，记录错误
                logger.error(f"导入引擎不可用，无法导入数据源: {source}")
                return {
                    'source': source,
                    'imported_count': 0,
                    'failed_count': 1,
                    'status': 'failed',
                    'error': '导入引擎不可用'
                }

        except Exception as e:
            logger.error(f"导入数据源 {source} 失败: {e}")
            return {
                'source': source,
                'imported_count': 0,
                'failed_count': 1,
                'status': 'failed',
                'error': str(e)
            }

    def _import_batch_sources(self, stock_codes: list, import_config: dict) -> dict:
        """批量导入多个股票代码"""
        try:
            # 调用实际的数据导入引擎 - 批量模式
            if self._import_engine:
                from core.importdata.import_config_manager import ImportTaskConfig, ImportMode, DataFrequency
                from datetime import datetime, timedelta
                import time

                # 创建批量任务ID
                batch_task_id = f"async_batch_import_{int(time.time())}"

                # 创建批量任务配置
                date_range = import_config.get('date_range', {})
                task_config = ImportTaskConfig(
                    task_id=batch_task_id,
                    name=f"异步批量导入_{len(stock_codes)}只股票",
                    data_source=import_config.get('data_source', 'examples.akshare_stock_plugin'),
                    asset_type=import_config.get('asset_type', '股票'),
                    data_type=import_config.get('data_type', 'K线数据'),
                    mode=ImportMode.BATCH,
                    symbols=stock_codes,  # 传递完整的股票代码列表
                    frequency=import_config.get('frequency', DataFrequency.DAILY),
                    start_date=date_range.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')),
                    end_date=date_range.get('end_date', datetime.now().strftime('%Y-%m-%d')),
                    batch_size=import_config.get('batch_size', 50),
                    max_workers=import_config.get('max_workers', 4)  # 使用配置的并发数
                )

                # 临时添加任务配置到导入引擎的内存中
                logger.info(f" 临时添加批量任务配置到内存: {batch_task_id}")
                self._import_engine.config_manager._tasks[batch_task_id] = task_config

                # 启动批量任务
                logger.info(f" 启动批量导入任务: {batch_task_id}")
                success = self._import_engine.start_task(batch_task_id)
                logger.info(f" 批量任务启动结果: {success}")

                if success:
                    # 等待任务完成
                    max_wait = 300  # 批量任务等待5分钟
                    wait_count = 0

                    while wait_count < max_wait:
                        task_result = self._import_engine.get_task_status(batch_task_id)
                        if task_result and task_result.status.name in ['COMPLETED', 'FAILED']:
                            break
                        time.sleep(1)
                        wait_count += 1

                        # 更新进度
                        progress = 20 + (60 * wait_count // max_wait)
                        self.progress_updated.emit(progress, f"正在批量导入 {len(stock_codes)} 只股票...")

                    # 获取最终结果
                    final_result = self._import_engine.get_task_status(batch_task_id)

                    # 清理临时任务配置
                    try:
                        if batch_task_id in self._import_engine.config_manager._tasks:
                            del self._import_engine.config_manager._tasks[batch_task_id]
                        if batch_task_id in self._import_engine.config_manager._progress:
                            del self._import_engine.config_manager._progress[batch_task_id]
                        logger.info(f" 已清理临时批量任务配置: {batch_task_id}")
                    except Exception as e:
                        logger.warning(f" 清理临时批量任务配置失败: {e}")

                    if final_result:
                        return {
                            'source': f"批量导入_{len(stock_codes)}只股票",
                            'imported_count': final_result.processed_records,
                            'failed_count': final_result.failed_records,
                            'status': 'completed' if final_result.status.name == 'COMPLETED' else 'failed'
                        }
                    else:
                        return {
                            'source': f"批量导入_{len(stock_codes)}只股票",
                            'imported_count': 0,
                            'failed_count': len(stock_codes),
                            'status': 'failed',
                            'error': '批量任务执行超时'
                        }
                else:
                    return {
                        'source': f"批量导入_{len(stock_codes)}只股票",
                        'imported_count': 0,
                        'failed_count': len(stock_codes),
                        'status': 'failed',
                        'error': '批量任务启动失败'
                    }
            else:
                logger.error("导入引擎不可用，无法执行批量导入")
                return {
                    'source': f"批量导入_{len(stock_codes)}只股票",
                    'imported_count': 0,
                    'failed_count': len(stock_codes),
                    'status': 'failed',
                    'error': '导入引擎不可用'
                }

        except Exception as e:
            logger.error(f"批量导入失败: {e}")
            return {
                'source': f"批量导入_{len(stock_codes)}只股票",
                'imported_count': 0,
                'failed_count': len(stock_codes),
                'status': 'failed',
                'error': str(e)
            }

    def _on_engine_progress(self, task_id: str, progress: float, message: str):
        """处理导入引擎的进度更新"""
        self.progress_updated.emit(int(progress), message)

    def stop(self):
        """停止数据导入"""
        self._stop_requested = True
        if self._import_engine:
            # 停止导入引擎
            try:
                self._import_engine.stop_all_tasks()
            except Exception as e:
                logger.warning(f"停止导入引擎失败: {e}")

        self.quit()
        self.wait(5000)  # 等待最多5秒


class AsyncDataImportManager(QObject):
    """异步数据导入管理器"""

    # 信号定义
    import_started = pyqtSignal(str)  # 任务ID
    progress_updated = pyqtSignal(int, str)  # 进度, 消息
    import_completed = pyqtSignal(str, dict)  # 任务ID, 结果
    import_failed = pyqtSignal(str, str)  # 任务ID, 错误消息
    data_chunk_imported = pyqtSignal(str, int, int)  # 任务ID, 已导入, 总数

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_workers: Dict[str, AsyncDataImportWorker] = {}
        self.import_history: List[dict] = []

    def start_import(self, import_config: dict) -> str:
        """开始异步数据导入"""
        try:
            task_id = import_config.get('task_id', f"import_{int(time.time())}")

            if task_id in self.active_workers:
                logger.warning(f"导入任务已存在: {task_id}")
                return task_id

            logger.info(f"启动异步数据导入任务: {task_id}")

            # 创建工作线程
            worker = AsyncDataImportWorker(import_config)

            # 连接信号
            worker.import_started.connect(self.import_started.emit)
            worker.progress_updated.connect(self.progress_updated.emit)
            worker.import_completed.connect(self._on_import_completed)
            worker.import_failed.connect(self._on_import_failed)
            worker.data_chunk_imported.connect(self.data_chunk_imported.emit)

            # 启动工作线程
            worker.start()
            self.active_workers[task_id] = worker

            logger.info(f"异步数据导入任务已启动: {task_id}")
            return task_id

        except Exception as e:
            logger.error(f"启动异步数据导入失败: {e}")
            raise

    def stop_import(self, task_id: str) -> bool:
        """停止数据导入任务"""
        if task_id not in self.active_workers:
            logger.warning(f"导入任务不存在: {task_id}")
            return False

        try:
            logger.info(f"停止数据导入任务: {task_id}")
            worker = self.active_workers[task_id]
            worker.stop()
            del self.active_workers[task_id]
            return True

        except Exception as e:
            logger.error(f"停止数据导入任务失败: {e}")
            return False

    def stop_all_imports(self):
        """停止所有导入任务"""
        logger.info("停止所有数据导入任务...")
        for task_id in list(self.active_workers.keys()):
            self.stop_import(task_id)

    def get_active_imports(self) -> List[str]:
        """获取活跃的导入任务列表"""
        return list(self.active_workers.keys())

    def get_import_history(self) -> List[dict]:
        """获取导入历史记录"""
        return self.import_history.copy()

    def _on_import_completed(self, task_id: str, result: dict):
        """导入完成处理"""
        if task_id in self.active_workers:
            del self.active_workers[task_id]

        # 记录到历史
        self.import_history.append({
            'task_id': task_id,
            'status': 'completed',
            'result': result,
            'timestamp': datetime.now().isoformat()
        })

        self.import_completed.emit(task_id, result)
        logger.info(f"数据导入任务完成: {task_id}")

    def _on_import_failed(self, task_id: str, error_msg: str):
        """导入失败处理"""
        if task_id in self.active_workers:
            del self.active_workers[task_id]

        # 记录到历史
        self.import_history.append({
            'task_id': task_id,
            'status': 'failed',
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })

        self.import_failed.emit(task_id, error_msg)
        logger.error(f"数据导入任务失败: {task_id} - {error_msg}")


# 全局服务实例
_async_data_import_manager = None


def get_async_data_import_manager() -> AsyncDataImportManager:
    """获取异步数据导入管理器实例"""
    global _async_data_import_manager
    if _async_data_import_manager is None:
        _async_data_import_manager = AsyncDataImportManager()
    return _async_data_import_manager
