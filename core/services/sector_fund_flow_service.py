from loguru import logger
"""
板块资金流数据服务

此模块提供统一的板块资金流数据访问接口，支持多数据源切换、
数据缓存、异步加载等功能。

主要功能：
- 支持多数据源（AkShare、东方财富等）
- 统一的数据格式和接口
- 数据缓存和性能优化
- 异步数据加载
- 错误处理和降级策略
"""

import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from .unified_data_manager import UnifiedDataManager


@dataclass
class SectorFlowConfig:
    """板块资金流服务配置"""
    cache_duration_minutes: int = 5  # 缓存持续时间（分钟）
    auto_refresh_interval_minutes: int = 10  # 自动刷新间隔（分钟）
    max_concurrent_requests: int = 3  # 最大并发请求数
    request_timeout_seconds: int = 30  # 请求超时时间（秒）
    enable_cache: bool = True  # 启用缓存
    enable_auto_refresh: bool = True  # 启用自动刷新
    fallback_data_source: str = "akshare"  # 降级数据源


class SectorFundFlowService(QObject):
    """板块资金流数据服务"""

    # 信号定义
    data_updated = pyqtSignal(object)  # 数据更新信号
    error_occurred = pyqtSignal(str)  # 错误信号
    source_changed = pyqtSignal(str)  # 数据源变更信号

    def __init__(self, data_manager: Optional[UnifiedDataManager] = None,
                 config: Optional[SectorFlowConfig] = None):
        """
        初始化板块资金流服务

        Args:
            data_manager: 数据管理器实例
            config: 服务配置
            # log_manager: 已迁移到Loguru日志系统
        """
        super().__init__()

        # 使用数据管理器工厂获取正确的DataManager实例
        if data_manager is None:
            try:
                from utils.manager_factory import get_manager_factory, get_data_manager
                factory = get_manager_factory()
                self.data_manager = get_data_manager()
            except ImportError:
                # 降级到直接导入
                from .unified_data_manager import get_unified_data_manager
                self.data_manager = get_unified_data_manager()
        else:
            self.data_manager = data_manager
        self.config = config or SectorFlowConfig()
        # 纯Loguru架构，移除log_manager依赖

        # 缓存管理
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_lock = threading.RLock()

        # 异步执行器
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_requests)

        # 自动刷新定时器
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._auto_refresh)

        self._is_initialized = False
        self._current_source = None

    def initialize(self) -> bool:
        """初始化服务"""
        try:
            logger.info(" 初始化板块资金流服务...")
            import time
            start_time = time.time()

            # 检查数据管理器
            logger.info(" 检查数据管理器状态...")
            if self.data_manager:
                logger.info(" 数据管理器可用")
            else:
                logger.warning(" 数据管理器不可用")

            # 启动自动刷新
            logger.info(" 配置自动刷新设置...")
            if self.config.enable_auto_refresh:
                refresh_start = time.time()
                self._start_auto_refresh()
                refresh_time = time.time()
                logger.info(f" 自动刷新启动完成，耗时: {(refresh_time - refresh_start):.2f}秒")
            else:
                logger.info("ℹ 自动刷新已禁用")

            # 获取当前数据源
            self._current_source = self.data_manager.get_current_source()

            self._is_initialized = True
            logger.info(f" 板块资金流服务初始化完成，当前数据源: {self._current_source}")

            return True

        except Exception as e:
            logger.error(f" 板块资金流服务初始化失败: {e}")
            return False

    def cleanup(self) -> None:
        """清理服务资源"""
        try:
            logger.info(" 清理板块资金流服务...")

            # 停止自动刷新
            self._refresh_timer.stop()

            # 关闭执行器
            self._executor.shutdown(wait=True)

            # 清理缓存
            with self._cache_lock:
                self._cache.clear()
                self._cache_timestamps.clear()

            logger.info(" 板块资金流服务清理完成")

        except Exception as e:
            logger.error(f" 清理板块资金流服务失败: {e}")

    def get_sector_flow_rank(self, indicator: str = "今日", force_refresh: bool = False) -> pd.DataFrame:
        """获取板块资金流排行

        Args:
            indicator: 时间周期（今日、3日、5日、10日、20日）
            force_refresh: 是否强制刷新缓存

        Returns:
            pd.DataFrame: 板块资金流排行数据
        """
        cache_key = f"sector_flow_rank_{indicator}"

        try:
            # 检查缓存
            if not force_refresh and self._is_cache_valid(cache_key):
                logger.info(f" 使用缓存的板块资金流排行数据: {indicator}")
                return self._get_from_cache(cache_key)

            logger.info(f" 获取板块资金流排行数据: {indicator}")

            # 从数据管理器获取数据
            fund_flow_data = self.data_manager.get_fund_flow()

            if fund_flow_data and 'sector_flow_rank' in fund_flow_data:
                df = fund_flow_data['sector_flow_rank']

                # 数据标准化处理
                df = self._standardize_sector_flow_data(df)

                # 更新缓存
                self._update_cache(cache_key, df)

                logger.info(f" 板块资金流排行数据获取成功: {len(df)} 条记录")
                self.data_updated.emit({'type': 'sector_flow_rank', 'data': df})

                return df
            else:
                logger.warning(" 未获取到板块资金流排行数据")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f" 获取板块资金流排行失败: {e}")
            self.error_occurred.emit(f"获取板块资金流排行失败: {str(e)}")
            return pd.DataFrame()

    def get_sector_flow_summary(self, symbol: str, indicator: str = "今日") -> pd.DataFrame:
        """获取板块资金流汇总

        Args:
            symbol: 板块名称
            indicator: 时间周期

        Returns:
            pd.DataFrame: 板块资金流汇总数据
        """
        try:
            df = self.data_manager.get_sector_fund_flow_summary(symbol, indicator)
            logger.info(f" 板块资金流汇总获取成功: {symbol}, {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f" 获取板块资金流汇总失败: {e}")
            return pd.DataFrame()

    def get_sector_flow_history(self, symbol: str, period: str = "近6月") -> pd.DataFrame:
        """获取板块历史资金流

        Args:
            symbol: 板块名称
            period: 时间周期

        Returns:
            pd.DataFrame: 板块历史资金流数据
        """
        try:
            df = self.data_manager.get_sector_fund_flow_hist(symbol, period)
            logger.info(f" 板块历史资金流获取成功: {symbol}, {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f" 获取板块历史资金流失败: {e}")
            return pd.DataFrame()

    def get_concept_flow_history(self, symbol: str, period: str = "近6月") -> pd.DataFrame:
        """获取概念历史资金流

        Args:
            symbol: 概念名称
            period: 时间周期

        Returns:
            pd.DataFrame: 概念历史资金流数据
        """
        try:
            df = self.data_manager.get_concept_fund_flow_hist(symbol, period)
            logger.info(f" 概念历史资金流获取成功: {symbol}, {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f" 获取概念历史资金流失败: {e}")
            return pd.DataFrame()

    def switch_data_source(self, source: str) -> bool:
        """切换数据源

        Args:
            source: 数据源名称

        Returns:
            bool: 是否切换成功
        """
        try:
            logger.info(f" 切换数据源到: {source}")

            # 切换数据管理器的数据源
            self.data_manager.set_data_source(source)
            self._current_source = source

            # 清理缓存
            self._clear_cache()

            logger.info(f" 数据源切换成功: {source}")
            self.source_changed.emit(source)

            return True

        except Exception as e:
            logger.error(f" 数据源切换失败: {e}")
            self.error_occurred.emit(f"数据源切换失败: {str(e)}")
            return False

    def _standardize_sector_flow_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化板块资金流数据格式"""
        try:
            # 标准化列名
            column_mapping = {
                '板块': 'sector_name',
                '今日主力净流入-净额': 'main_net_inflow',
                '今日主力净流入-净占比': 'main_net_inflow_ratio',
                '今日散户净流入-净额': 'retail_net_inflow',
                '今日散户净流入-净占比': 'retail_net_inflow_ratio',
                '今日涨跌幅': 'change_pct'
            }

            # 重命名列
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})

            # 数据类型转换
            numeric_columns = ['main_net_inflow', 'main_net_inflow_ratio',
                               'retail_net_inflow', 'retail_net_inflow_ratio', 'change_pct']

            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            return df

        except Exception as e:
            logger.warning(f" 数据标准化失败: {e}")
            return df

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if not self.config.enable_cache:
            return False

        with self._cache_lock:
            if cache_key not in self._cache_timestamps:
                return False

            cache_time = self._cache_timestamps[cache_key]
            cache_duration = timedelta(minutes=self.config.cache_duration_minutes)

            return datetime.now() - cache_time < cache_duration

    def _get_from_cache(self, cache_key: str) -> Any:
        """从缓存获取数据"""
        with self._cache_lock:
            return self._cache.get(cache_key)

    def _update_cache(self, cache_key: str, data: Any) -> None:
        """更新缓存"""
        if self.config.enable_cache:
            with self._cache_lock:
                self._cache[cache_key] = data
                self._cache_timestamps[cache_key] = datetime.now()

    def _clear_cache(self) -> None:
        """清理缓存"""
        with self._cache_lock:
            self._cache.clear()
            self._cache_timestamps.clear()
        logger.info(" 缓存已清理")

    def _start_auto_refresh(self) -> None:
        """启动自动刷新"""
        if self.config.auto_refresh_interval_minutes > 0:
            interval_ms = self.config.auto_refresh_interval_minutes * 60 * 1000
            self._refresh_timer.start(interval_ms)
            logger.info(f" 启动自动刷新，间隔 {self.config.auto_refresh_interval_minutes} 分钟")

    def _auto_refresh(self) -> None:
        """自动刷新数据（后台线程执行，避免阻塞UI线程）"""
        try:
            logger.info("⏰ 调度自动刷新任务...")
            # 将实际刷新任务放入线程池，避免在Qt定时器回调（主线程）中执行重IO/CPU工作
            self._executor.submit(self._run_auto_refresh_task)
        except Exception as e:
            logger.error(f" 自动刷新调度失败: {e}")

    def _run_auto_refresh_task(self) -> None:
        """实际的自动刷新任务，在线程池中执行"""
        try:
            # 这里直接调用现有方法即可；该方法内部会通过Qt信号通知数据更新
            self.get_sector_flow_rank(force_refresh=True)
        except Exception as e:
            logger.error(f" 自动刷新任务执行失败: {e}")

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'is_initialized': self._is_initialized,
            'current_source': self._current_source,
            'cache_enabled': self.config.enable_cache,
            'auto_refresh_enabled': self.config.enable_auto_refresh,
            'cache_size': len(self._cache) if self.config.enable_cache else 0
        }
