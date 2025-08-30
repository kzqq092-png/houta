#!/usr/bin/env python3
"""
数据导入任务执行引擎

负责执行数据导入任务，提供进度监控、状态更新和错误处理
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from .import_config_manager import ImportConfigManager, ImportTaskConfig, ImportProgress, ImportStatus
from ..services.unified_data_manager import UnifiedDataManager
from ..real_data_provider import RealDataProvider

logger = logging.getLogger(__name__)


class TaskExecutionStatus(Enum):
    """任务执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskExecutionResult:
    """任务执行结果"""
    task_id: str
    status: TaskExecutionStatus
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0

    @property
    def progress_percentage(self) -> float:
        """进度百分比"""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100


class DataImportExecutionEngine(QObject):
    """
    数据导入任务执行引擎

    功能：
    1. 执行数据导入任务
    2. 监控任务进度
    3. 提供状态更新
    4. 错误处理和重试
    5. 任务调度和管理
    """

    # Qt信号
    task_started = pyqtSignal(str)  # 任务开始
    task_progress = pyqtSignal(str, float, str)  # 任务进度 (task_id, progress, message)
    task_completed = pyqtSignal(str, object)  # 任务完成 (task_id, result)
    task_failed = pyqtSignal(str, str)  # 任务失败 (task_id, error_message)

    def __init__(self, config_manager: ImportConfigManager = None,
                 data_manager: UnifiedDataManager = None,
                 max_workers: int = 4):
        super().__init__()

        # 配置管理器
        self.config_manager = config_manager or ImportConfigManager()

        # 数据管理器 - 延迟初始化以避免阻塞
        self.data_manager = data_manager
        self._data_manager_initialized = data_manager is not None

        # 真实数据提供器 - 延迟初始化以避免阻塞
        self.real_data_provider = None
        self._real_data_provider_initialized = False

        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers,
                                           thread_name_prefix="ImportEngine")

        # 任务管理
        self._running_tasks: Dict[str, Future] = {}
        self._task_results: Dict[str, TaskExecutionResult] = {}
        self._task_lock = threading.RLock()

        # 进度监控定时器
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        self.progress_timer.start(1000)  # 每秒更新一次进度

        logger.info("数据导入执行引擎初始化完成")

    def _ensure_data_manager(self):
        """确保数据管理器已初始化"""
        if not self._data_manager_initialized:
            try:
                logger.info("🔄 延迟初始化数据管理器...")
                self.data_manager = UnifiedDataManager()
                self._data_manager_initialized = True
                logger.info("✅ 数据管理器延迟初始化完成")
            except Exception as e:
                logger.error(f"❌ 数据管理器初始化失败: {e}")
                # 创建一个最小的数据管理器替代
                self.data_manager = None
                self._data_manager_initialized = False

    def _ensure_real_data_provider(self):
        """确保真实数据提供器已初始化"""
        if not self._real_data_provider_initialized:
            try:
                logger.info("🔄 延迟初始化真实数据提供器...")
                self.real_data_provider = RealDataProvider()
                self._real_data_provider_initialized = True
                logger.info("✅ 真实数据提供器延迟初始化完成")
            except Exception as e:
                logger.error(f"❌ 真实数据提供器初始化失败: {e}")
                # 创建一个最小的替代
                self.real_data_provider = None
                self._real_data_provider_initialized = False

    def start_task(self, task_id: str) -> bool:
        """
        启动任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功启动
        """
        try:
            logger.info(f"🔍 开始启动任务: {task_id}")

            # 获取任务配置
            task_config = self.config_manager.get_import_task(task_id)
            if not task_config:
                logger.error(f"❌ 任务配置不存在: {task_id}")
                return False

            logger.info(f"✅ 找到任务配置: {task_config.name}, 股票代码: {task_config.symbols}")

            # 检查任务是否已在运行
            with self._task_lock:
                if task_id in self._running_tasks:
                    logger.warning(f"任务已在运行: {task_id}")
                    return False

            # 创建任务执行结果
            result = TaskExecutionResult(
                task_id=task_id,
                status=TaskExecutionStatus.PENDING,
                start_time=datetime.now()
            )

            with self._task_lock:
                self._task_results[task_id] = result

            # 提交任务到线程池
            future = self.executor.submit(self._execute_task, task_config, result)

            with self._task_lock:
                self._running_tasks[task_id] = future

            # 发送任务开始信号
            self.task_started.emit(task_id)

            logger.info(f"任务启动成功: {task_id}")
            return True

        except Exception as e:
            logger.error(f"启动任务失败 {task_id}: {e}")
            self.task_failed.emit(task_id, str(e))
            return False

    def stop_task(self, task_id: str) -> bool:
        """
        停止任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功停止
        """
        try:
            with self._task_lock:
                if task_id not in self._running_tasks:
                    logger.warning(f"任务未在运行: {task_id}")
                    return False

                # 取消任务
                future = self._running_tasks[task_id]
                cancelled = future.cancel()

                if cancelled:
                    # 更新任务状态
                    if task_id in self._task_results:
                        self._task_results[task_id].status = TaskExecutionStatus.CANCELLED
                        self._task_results[task_id].end_time = datetime.now()

                    # 移除运行中的任务
                    del self._running_tasks[task_id]

                    logger.info(f"任务停止成功: {task_id}")
                    return True
                else:
                    logger.warning(f"任务无法取消: {task_id}")
                    return False

        except Exception as e:
            logger.error(f"停止任务失败 {task_id}: {e}")
            return False

    def get_task_status(self, task_id: str) -> Optional[TaskExecutionResult]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            TaskExecutionResult: 任务执行结果
        """
        with self._task_lock:
            return self._task_results.get(task_id)

    def get_running_tasks(self) -> List[str]:
        """获取正在运行的任务列表"""
        with self._task_lock:
            return list(self._running_tasks.keys())

    def _execute_task(self, task_config: ImportTaskConfig, result: TaskExecutionResult):
        """
        执行任务的核心逻辑

        Args:
            task_config: 任务配置
            result: 任务执行结果
        """
        try:
            logger.info(f"🚀 开始执行任务: {task_config.task_id}")
            logger.info(f"📊 任务详情: 数据类型={getattr(task_config, 'data_type', 'K线数据')}, 股票={task_config.symbols}")

            # 更新任务状态
            result.status = TaskExecutionStatus.RUNNING

            # 根据任务类型执行不同的导入逻辑
            data_type = getattr(task_config, 'data_type', 'K线数据')  # 默认为K线数据
            logger.info(f"🔄 执行数据类型: {data_type}")

            if data_type == "K线数据":
                logger.info("📈 开始导入K线数据")
                self._import_kline_data(task_config, result)
            elif data_type == "实时行情":
                logger.info("⚡ 开始导入实时行情")
                self._import_realtime_data(task_config, result)
            elif data_type == "基本面数据":
                logger.info("📋 开始导入基本面数据")
                self._import_fundamental_data(task_config, result)
            else:
                logger.warning(f"⚠️ 不支持的数据类型，默认使用K线数据: {data_type}")
                self._import_kline_data(task_config, result)

            # 任务完成
            result.status = TaskExecutionStatus.COMPLETED
            result.end_time = datetime.now()
            result.execution_time = (result.end_time - result.start_time).total_seconds()

            # 更新配置管理器中的进度
            progress = ImportProgress(
                task_id=task_config.task_id,
                status=ImportStatus.COMPLETED,
                total_records=result.total_records,
                processed_records=result.processed_records,
                failed_records=result.failed_records,
                start_time=result.start_time.isoformat(),
                end_time=result.end_time.isoformat(),
                error_message=result.error_message
            )
            self.config_manager.update_progress(progress)

            # 发送完成信号
            self.task_completed.emit(task_config.task_id, result)

            logger.info(f"任务执行完成: {task_config.task_id}")

        except Exception as e:
            logger.error(f"任务执行失败 {task_config.task_id}: {e}")

            # 更新任务状态
            result.status = TaskExecutionStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.now()

            # 发送失败信号
            self.task_failed.emit(task_config.task_id, str(e))

        finally:
            # 清理运行中的任务
            with self._task_lock:
                if task_config.task_id in self._running_tasks:
                    del self._running_tasks[task_config.task_id]

    def _save_kdata_to_database(self, symbol: str, kdata: 'pd.DataFrame', task_config: ImportTaskConfig):
        """保存K线数据到数据库"""
        try:
            # 获取DuckDB操作实例
            from ..database.duckdb_operations import get_duckdb_operations
            from ..database.table_manager import get_table_manager

            duckdb_ops = get_duckdb_operations()
            table_manager = get_table_manager()

            if not duckdb_ops or not table_manager:
                logger.warning("DuckDB操作或表管理器不可用，跳过数据保存")
                return

            # 确定表名
            frequency = task_config.frequency.value if hasattr(task_config, 'frequency') else 'D'
            table_name = f"kline_data_{frequency.lower()}"

            # 确保表存在 - 使用统一的DuckDB数据库
            db_path = "db/kline_stock.duckdb"
            table_manager.ensure_table_exists(db_path, table_name)

            # 添加symbol列
            kdata_with_symbol = kdata.copy()
            kdata_with_symbol['symbol'] = symbol
            kdata_with_symbol['import_time'] = pd.Timestamp.now()

            # 插入数据（使用upsert避免重复）
            result = duckdb_ops.insert_dataframe(
                database_path=db_path,
                table_name=table_name,
                data=kdata_with_symbol,
                upsert=True,
                conflict_columns=['symbol', 'datetime'] if 'datetime' in kdata_with_symbol.columns else ['symbol']
            )

            if result.success:
                logger.info(f"✅ K线数据保存到DuckDB成功: {symbol}, {len(kdata)}条记录")
            else:
                logger.error(f"❌ K线数据保存失败: {symbol}")

        except Exception as e:
            logger.error(f"保存K线数据到数据库失败 {symbol}: {e}")

    def _save_fundamental_data_to_database(self, symbol: str, data: 'pd.DataFrame', data_type: str):
        """保存基本面数据到数据库"""
        try:
            from ..database.duckdb_operations import get_duckdb_operations
            from ..database.table_manager import get_table_manager

            duckdb_ops = get_duckdb_operations()
            table_manager = get_table_manager()

            if not duckdb_ops or not table_manager:
                logger.warning("DuckDB操作或表管理器不可用，跳过数据保存")
                return

            # 确定表名
            table_name = f"fundamental_{data_type.lower().replace(' ', '_')}"

            # 确保表存在 - 使用统一的DuckDB数据库
            db_path = "db/kline_stock.duckdb"
            table_manager.ensure_table_exists(db_path, table_name)

            # 添加symbol列
            data_with_symbol = data.copy()
            data_with_symbol['symbol'] = symbol
            data_with_symbol['import_time'] = pd.Timestamp.now()

            # 插入数据
            result = duckdb_ops.insert_dataframe(
                database_path=db_path,
                table_name=table_name,
                data=data_with_symbol,
                upsert=True,
                conflict_columns=['symbol', 'date'] if 'date' in data_with_symbol.columns else ['symbol']
            )

            if result.success:
                logger.info(f"✅ 基本面数据保存到DuckDB成功: {symbol}, {len(data)}条记录")
            else:
                logger.error(f"❌ 基本面数据保存失败: {symbol}")

        except Exception as e:
            logger.error(f"保存基本面数据到数据库失败 {symbol}: {e}")

    def _save_realtime_data_to_database(self, symbol: str, data: 'pd.DataFrame'):
        """保存实时数据到数据库"""
        try:
            from ..database.duckdb_operations import get_duckdb_operations
            from ..database.table_manager import get_table_manager

            duckdb_ops = get_duckdb_operations()
            table_manager = get_table_manager()

            if not duckdb_ops or not table_manager:
                logger.warning("DuckDB操作或表管理器不可用，跳过数据保存")
                return

            # 确定表名
            table_name = "realtime_data"

            # 确保表存在 - 使用统一的DuckDB数据库
            db_path = "db/kline_stock.duckdb"
            table_manager.ensure_table_exists(db_path, table_name)

            # 添加symbol列
            data_with_symbol = data.copy()
            data_with_symbol['symbol'] = symbol
            data_with_symbol['import_time'] = pd.Timestamp.now()

            # 插入数据（实时数据通常不需要upsert，直接插入）
            result = duckdb_ops.insert_dataframe(
                database_path=db_path,
                table_name=table_name,
                data=data_with_symbol,
                upsert=False
            )

            if result.success:
                logger.info(f"✅ 实时数据保存到DuckDB成功: {symbol}, {len(data)}条记录")
            else:
                logger.error(f"❌ 实时数据保存失败: {symbol}")

        except Exception as e:
            logger.error(f"保存实时数据到数据库失败 {symbol}: {e}")

    def _import_kline_data(self, task_config: ImportTaskConfig, result: TaskExecutionResult):
        """导入K线数据（优化版本：并发下载+批量保存）"""
        try:
            # 确保数据管理器已初始化
            self._ensure_data_manager()

            # 确保真实数据提供器已初始化
            self._ensure_real_data_provider()

            symbols = task_config.symbols
            result.total_records = len(symbols)

            logger.info(f"📈 开始导入K线数据，股票列表: {symbols}")
            logger.info(f"📅 时间范围: {task_config.start_date} 到 {task_config.end_date}")
            logger.info(f"📊 频率: {task_config.frequency}")
            logger.info(f"🚀 使用并发下载模式，最大工作线程: {task_config.max_workers}")

            # 使用并发下载优化性能
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading

            # 用于收集所有下载的数据
            all_kdata_list = []
            download_lock = threading.Lock()

            # 进度跟踪
            completed_count = 0
            progress_lock = threading.Lock()

            def download_single_stock(symbol: str) -> dict:
                """下载单只股票的数据"""
                nonlocal completed_count  # 声明必须在函数开头
                try:
                    # 发送进度更新信号
                    self.task_progress.emit(
                        task_config.task_id,
                        (completed_count / len(symbols)) * 100,
                        f"正在下载 {symbol} 的K线数据..."
                    )

                    logger.info(f"🔄 [{completed_count + 1}/{len(symbols)}] 正在获取 {symbol} 的K线数据...")

                    # 使用真实数据提供器获取K线数据
                    kdata = self.real_data_provider.get_real_kdata(
                        code=symbol,
                        freq=task_config.frequency.value,
                        start_date=task_config.start_date,
                        end_date=task_config.end_date
                    )

                    # 更新进度
                    with progress_lock:
                        completed_count += 1

                    if not kdata.empty:
                        # 添加symbol列和时间戳
                        kdata_with_meta = kdata.copy()
                        kdata_with_meta['symbol'] = symbol
                        kdata_with_meta['import_time'] = pd.Timestamp.now()

                        # 线程安全地添加到列表
                        with download_lock:
                            all_kdata_list.append(kdata_with_meta)

                        logger.info(f"✅ [{completed_count}/{len(symbols)}] {symbol} 数据获取成功: {len(kdata)} 条记录")
                        return {'symbol': symbol, 'status': 'success', 'records': len(kdata)}
                    else:
                        logger.warning(f"⚠️ [{completed_count}/{len(symbols)}] 未获取到 {symbol} 的K线数据")
                        return {'symbol': symbol, 'status': 'no_data', 'records': 0}

                except Exception as e:
                    with progress_lock:
                        completed_count += 1
                    logger.error(f"❌ [{completed_count}/{len(symbols)}] 导入 {symbol} K线数据失败: {e}")
                    return {'symbol': symbol, 'status': 'error', 'error': str(e), 'records': 0}

            # 并发下载所有股票数据
            max_workers = min(task_config.max_workers, len(symbols), 8)  # 限制最大并发数
            logger.info(f"🔄 启动 {max_workers} 个并发下载线程...")

            download_results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有下载任务
                future_to_symbol = {executor.submit(download_single_stock, symbol): symbol
                                    for symbol in symbols}

                # 收集结果
                for future in as_completed(future_to_symbol):
                    if result.status == TaskExecutionStatus.CANCELLED:
                        break

                    try:
                        download_result = future.result()
                        download_results.append(download_result)

                        # 更新任务结果统计
                        if download_result['status'] == 'success':
                            result.processed_records += 1
                        else:
                            result.failed_records += 1

                    except Exception as e:
                        symbol = future_to_symbol[future]
                        logger.error(f"下载任务异常 {symbol}: {e}")
                        result.failed_records += 1

            # 批量保存所有数据到数据库
            if all_kdata_list and result.status != TaskExecutionStatus.CANCELLED:
                logger.info(f"📊 开始批量保存数据到DuckDB，共 {len(all_kdata_list)} 只股票的数据...")
                self._batch_save_kdata_to_database(all_kdata_list, task_config)
                logger.info(f"✅ 批量保存完成")

            # 输出统计信息
            success_count = sum(1 for r in download_results if r['status'] == 'success')
            failed_count = sum(1 for r in download_results if r['status'] in ['error', 'no_data'])
            total_records = sum(r.get('records', 0) for r in download_results)

            logger.info(f"📈 K线数据导入完成统计:")
            logger.info(f"  ✅ 成功: {success_count} 只股票")
            logger.info(f"  ❌ 失败: {failed_count} 只股票")
            logger.info(f"  📊 总记录数: {total_records} 条")

        except Exception as e:
            raise Exception(f"K线数据导入失败: {e}")

    def _batch_save_kdata_to_database(self, all_kdata_list: list, task_config: ImportTaskConfig):
        """批量保存K线数据到数据库"""
        try:
            if not all_kdata_list:
                logger.warning("没有数据需要保存")
                return

            # 获取DuckDB操作实例
            from ..database.duckdb_operations import get_duckdb_operations
            from ..database.table_manager import get_table_manager

            duckdb_ops = get_duckdb_operations()
            table_manager = get_table_manager()

            if not duckdb_ops or not table_manager:
                logger.warning("DuckDB操作或表管理器不可用，跳过数据保存")
                return

            # 确定表名
            frequency = task_config.frequency.value if hasattr(task_config, 'frequency') else 'D'
            table_name = f"kline_data_{frequency.lower()}"

            # 确保表存在
            db_path = "db/kline_stock.duckdb"
            table_manager.ensure_table_exists(db_path, table_name)

            # 合并所有数据
            import pandas as pd
            combined_data = pd.concat(all_kdata_list, ignore_index=True)

            logger.info(f"📊 准备批量插入 {len(combined_data)} 条K线数据记录")

            # 批量插入数据（使用upsert避免重复）
            result = duckdb_ops.insert_dataframe(
                database_path=db_path,
                table_name=table_name,
                data=combined_data,
                batch_size=5000,  # 增大批处理大小以提高性能
                upsert=True,
                conflict_columns=['symbol', 'datetime'] if 'datetime' in combined_data.columns else ['symbol']
            )

            if result.success:
                logger.info(f"✅ 批量保存K线数据成功: {result.rows_inserted} 条记录，耗时: {result.execution_time:.2f}秒")
                if result.failed_batches:
                    logger.warning(f"⚠️ 有 {len(result.failed_batches)} 个批次保存失败")
            else:
                logger.error(f"❌ 批量保存K线数据失败: {result.error_message}")

        except Exception as e:
            logger.error(f"批量保存K线数据到数据库失败: {e}")

    def _import_realtime_data(self, task_config: ImportTaskConfig, result: TaskExecutionResult):
        """导入实时行情数据"""
        try:
            symbols = task_config.symbols
            result.total_records = len(symbols)

            for i, symbol in enumerate(symbols):
                if result.status == TaskExecutionStatus.CANCELLED:
                    break

                try:
                    # 获取实时行情数据
                    quote_data = self.real_data_provider.get_real_quote(symbol)

                    if quote_data:
                        # 将实时数据转换为DataFrame并保存
                        if isinstance(quote_data, dict):
                            import pandas as pd
                            quote_df = pd.DataFrame([quote_data])
                            self._save_realtime_data_to_database(symbol, quote_df)
                        logger.info(f"成功导入并保存 {symbol} 的实时行情数据")
                        result.processed_records += 1
                    else:
                        logger.warning(f"未获取到 {symbol} 的实时行情数据")
                        result.failed_records += 1

                except Exception as e:
                    logger.error(f"导入 {symbol} 实时行情失败: {e}")
                    result.failed_records += 1

                time.sleep(0.05)  # 实时数据处理更快

        except Exception as e:
            raise Exception(f"实时行情导入失败: {e}")

    def _import_fundamental_data(self, task_config: ImportTaskConfig, result: TaskExecutionResult):
        """导入基本面数据"""
        try:
            symbols = task_config.symbols
            result.total_records = len(symbols)

            for i, symbol in enumerate(symbols):
                if result.status == TaskExecutionStatus.CANCELLED:
                    break

                try:
                    # 获取基本面数据
                    fundamental_data = self.real_data_provider.get_real_fundamental_data(symbol)

                    if fundamental_data:
                        # 将基本面数据转换为DataFrame并保存
                        if isinstance(fundamental_data, (dict, list)):
                            import pandas as pd
                            if isinstance(fundamental_data, dict):
                                fund_df = pd.DataFrame([fundamental_data])
                            else:
                                fund_df = pd.DataFrame(fundamental_data)
                            self._save_fundamental_data_to_database(symbol, fund_df, "基本面数据")
                        logger.info(f"成功导入并保存 {symbol} 的基本面数据")
                        result.processed_records += 1
                    else:
                        logger.warning(f"未获取到 {symbol} 的基本面数据")
                        result.failed_records += 1

                except Exception as e:
                    logger.error(f"导入 {symbol} 基本面数据失败: {e}")
                    result.failed_records += 1

                time.sleep(0.2)  # 基本面数据处理较慢

        except Exception as e:
            raise Exception(f"基本面数据导入失败: {e}")

    def _update_progress(self):
        """更新任务进度"""
        with self._task_lock:
            for task_id, result in self._task_results.items():
                if result.status == TaskExecutionStatus.RUNNING:
                    progress = result.progress_percentage
                    message = f"已处理 {result.processed_records}/{result.total_records} 条记录"

                    # 发送进度信号
                    self.task_progress.emit(task_id, progress, message)

    def cleanup(self):
        """清理资源"""
        try:
            # 停止进度定时器
            if self.progress_timer.isActive():
                self.progress_timer.stop()

            # 取消所有运行中的任务
            with self._task_lock:
                for task_id in list(self._running_tasks.keys()):
                    self.stop_task(task_id)

            # 关闭线程池
            self.executor.shutdown(wait=True)

            logger.info("数据导入执行引擎清理完成")

        except Exception as e:
            logger.error(f"清理执行引擎失败: {e}")


def main():
    """测试函数"""
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建执行引擎
    engine = DataImportExecutionEngine()

    # 测试任务配置
    from .import_config_manager import ImportTaskConfig, ImportMode, DataFrequency

    task_config = ImportTaskConfig(
        task_id="test_task_001",
        name="测试K线数据导入",
        data_source="HIkyuu",
        asset_type="股票",
        data_type="K线数据",
        symbols=["000001", "000002"],
        frequency=DataFrequency.DAILY,
        mode=ImportMode.MANUAL
    )

    # 添加任务配置
    engine.config_manager.add_import_task(task_config)

    # 启动任务
    success = engine.start_task("test_task_001")
    print(f"任务启动: {'成功' if success else '失败'}")

    # 运行应用
    try:
        app.exec_()
    finally:
        engine.cleanup()


if __name__ == "__main__":
    main()
