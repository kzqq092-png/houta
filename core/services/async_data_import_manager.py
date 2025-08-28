#!/usr/bin/env python3
"""
异步数据导入管理器

提供异步的DuckDB数据导入功能，使用Qt信号机制
避免阻塞主线程，提供实时进度更新。
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)


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

    def run(self):
        """执行数据导入过程"""
        try:
            logger.info(f"开始异步数据导入任务: {self.task_id}")
            self.import_started.emit(self.task_id)
            self.progress_updated.emit(0, "初始化数据导入...")

            # 初始化导入引擎
            self._initialize_import_engine()

            if self._stop_requested:
                return

            # 执行数据导入
            result = self._execute_import()

            if self._stop_requested:
                return

            # 完成导入
            self.progress_updated.emit(100, "数据导入完成")
            self.import_completed.emit(self.task_id, result)

        except Exception as e:
            logger.error(f"异步数据导入失败: {e}")
            self.import_failed.emit(self.task_id, str(e))

    def _initialize_import_engine(self):
        """初始化导入引擎"""
        try:
            self.progress_updated.emit(5, "初始化导入引擎...")

            # 导入数据导入相关模块
            from core.importdata.import_execution_engine import DataImportExecutionEngine
            from core.importdata.import_config_manager import ImportConfigManager

            # 创建配置管理器和执行引擎
            config_manager = ImportConfigManager()
            self._import_engine = DataImportExecutionEngine(config_manager)

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

            # 执行真实的数据导入逻辑
            total_sources = len(data_sources) if data_sources else 1

            for i, source in enumerate(data_sources or ['default']):
                if self._stop_requested:
                    break

                base_progress = 15 + (70 * i // total_sources)
                self.progress_updated.emit(base_progress, f"导入数据源: {source}")

                # 执行单个数据源的导入
                source_result = self._import_single_source(source, base_progress)
                result['data_sources'].append(source_result)
                result['imported_count'] += source_result.get('imported_count', 0)
                result['failed_count'] += source_result.get('failed_count', 0)

            result['end_time'] = datetime.now().isoformat()
            self.progress_updated.emit(90, "数据导入处理完成")

            return result

        except Exception as e:
            logger.error(f"执行数据导入失败: {e}")
            raise

    def _import_single_source(self, source: str, base_progress: int) -> dict:
        """导入单个数据源"""
        try:
            # 调用实际的数据导入引擎
            if self._import_engine:
                # 使用真实的导入引擎执行导入
                import_result = self._import_engine.import_data_source(source)

                return {
                    'source': source,
                    'imported_count': import_result.get('success_count', 0),
                    'failed_count': import_result.get('failed_count', 0),
                    'status': 'completed' if import_result.get('success', False) else 'failed'
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
