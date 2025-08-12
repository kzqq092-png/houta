"""
数据源插件扩展模块

提供标准化的数据源插件接口，支持多种资产类型和数据类型的统一访问。
本模块实现了插件化数据源的核心接口和适配器，确保与现有系统的无缝集成。

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum, auto
import pandas as pd
from datetime import datetime
import threading
import time
import logging
import traceback
from dataclasses import dataclass, field

# 导入现有数据源相关类型
from .data_source import DataSource, DataSourceType, DataFrequency, MarketDataType

# 导入统一的枚举定义（避免重复定义）
from .plugin_types import AssetType, DataType

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """插件状态枚举"""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginInfo:
    """插件信息数据类"""
    id: str
    name: str
    version: str
    description: str
    author: str
    supported_asset_types: List[AssetType]
    supported_data_types: List[DataType]
    config_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    is_healthy: bool
    response_time_ms: float
    error_message: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class IDataSourcePlugin(ABC):
    """
    数据源插件标准接口

    所有数据源插件必须实现此接口，以确保与FactorWeave-Quant 系统的兼容性。
    接口设计遵循开闭原则，支持扩展而不修改现有代码。

    示例:
        class MyDataSourcePlugin(IDataSourcePlugin):
            def get_plugin_info(self) -> PluginInfo:
                return PluginInfo(
                    id="my_data_source",
                    name="My Data Source",
                    version="1.0.0",
                    description="Custom data source implementation",
                    author="Developer",
                    supported_asset_types=[AssetType.STOCK],
                    supported_data_types=[DataType.HISTORICAL_KLINE]
                )

            def initialize(self, config: Dict[str, Any]) -> bool:
                # 初始化逻辑
                return True

            def fetch_data(self, symbol: str, data_type: str, **kwargs) -> pd.DataFrame:
                # 数据获取逻辑
                return pd.DataFrame()
    """

    @abstractmethod
    def get_plugin_info(self) -> PluginInfo:
        """
        获取插件基本信息

        Returns:
            PluginInfo: 包含插件ID、名称、版本、描述等信息
        """
        pass

    @abstractmethod
    def get_supported_asset_types(self) -> List[AssetType]:
        """
        获取支持的资产类型列表

        Returns:
            List[AssetType]: 支持的资产类型列表
        """
        pass

    @abstractmethod
    def get_supported_data_types(self) -> List[DataType]:
        """
        获取支持的数据类型列表

        Returns:
            List[DataType]: 支持的数据类型列表
        """
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化插件

        Args:
            config: 插件配置参数字典

        Returns:
            bool: 初始化是否成功

        Raises:
            PluginInitializationError: 初始化失败时抛出
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        关闭插件，释放资源
        """
        pass

    @abstractmethod
    def fetch_data(self, symbol: str, data_type: str,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   **kwargs) -> pd.DataFrame:
        """
        获取数据

        Args:
            symbol: 标的代码（如股票代码、期货合约等）
            data_type: 数据类型（对应DataType枚举值）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            **kwargs: 其他参数（如频率、数量等）

        Returns:
            pd.DataFrame: 包含请求数据的DataFrame

        Raises:
            DataFetchError: 数据获取失败时抛出
        """
        pass

    @abstractmethod
    def get_real_time_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        获取实时数据

        Args:
            symbols: 标的代码列表

        Returns:
            Dict[str, Any]: 实时数据字典，键为标的代码，值为数据

        Raises:
            RealTimeDataError: 实时数据获取失败时抛出
        """
        pass

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        """
        执行健康检查

        Returns:
            HealthCheckResult: 健康检查结果
        """
        pass

    def get_config_schema(self) -> Dict[str, Any]:
        """
        获取配置模式定义（可选实现）

        Returns:
            Dict[str, Any]: 配置模式定义，用于UI动态生成配置界面
        """
        return {}

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证配置参数（可选实现）

        Args:
            config: 配置参数字典

        Returns:
            bool: 配置是否有效
        """
        return True

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        获取访问频率限制信息（可选实现）

        Returns:
            Dict[str, Any]: 频率限制信息
        """
        return {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "burst_limit": 10
        }


class DataSourcePluginAdapter:
    """
    数据源插件适配器

    将IDataSourcePlugin接口适配到现有的DataSource接口，
    实现新旧系统的无缝桥接。使用适配器模式确保向下兼容。
    """

    def __init__(self, plugin: IDataSourcePlugin, plugin_id: str):
        """
        初始化适配器

        Args:
            plugin: 数据源插件实例
            plugin_id: 插件唯一标识符
        """
        self.plugin = plugin
        self.plugin_id = plugin_id
        self._is_connected = False
        self._lock = threading.RLock()
        self._last_health_check = None
        self._health_check_interval = 300  # 5分钟

        # 适配器状态管理
        self.status = PluginStatus.UNKNOWN
        self.error_count = 0
        self.last_error = None
        self.last_success_time = None

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0
        }

        logger.info(f"DataSourcePluginAdapter创建完成: {plugin_id}")

    def connect(self) -> bool:
        """
        连接到数据源（适配DataSource接口）

        Returns:
            bool: 连接是否成功
        """
        with self._lock:
            try:
                self.status = PluginStatus.INITIALIZING

                # 获取插件默认配置
                config = self._get_default_config()

                # 初始化插件
                if self.plugin.initialize(config):
                    self._is_connected = True
                    self.status = PluginStatus.READY
                    self.last_success_time = datetime.now()
                    logger.info(f"插件连接成功: {self.plugin_id}")
                    return True
                else:
                    self.status = PluginStatus.ERROR
                    self.last_error = "插件初始化失败"
                    logger.error(f"插件连接失败: {self.plugin_id}")
                    return False

            except Exception as e:
                self.status = PluginStatus.ERROR
                self.last_error = str(e)
                self.error_count += 1
                logger.error(f"插件连接异常 {self.plugin_id}: {e}")
                return False

    def disconnect(self) -> None:
        """
        断开数据源连接（适配DataSource接口）
        """
        with self._lock:
            try:
                if self._is_connected:
                    self.plugin.shutdown()
                    self._is_connected = False
                    self.status = PluginStatus.DISABLED
                    logger.info(f"插件断开连接: {self.plugin_id}")

            except Exception as e:
                logger.error(f"插件断开连接失败 {self.plugin_id}: {e}")

    def is_connected(self) -> bool:
        """
        检查连接状态

        Returns:
            bool: 是否已连接
        """
        return self._is_connected and self.status == PluginStatus.READY

    def get_kdata(self, symbol: str, freq: Union[str, DataFrequency],
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  count: Optional[int] = None) -> pd.DataFrame:
        """
        获取K线数据（适配DataSource接口）

        Args:
            symbol: 股票代码
            freq: 数据频率
            start_date: 开始日期
            end_date: 结束日期
            count: 数据条数

        Returns:
            pd.DataFrame: K线数据
        """
        start_time = time.time()

        try:
            with self._lock:
                self.stats["total_requests"] += 1

                if not self.is_connected():
                    raise ConnectionError(f"插件未连接: {self.plugin_id}")

                # 转换频率参数
                data_type = DataType.HISTORICAL_KLINE.value

                # 准备参数
                kwargs = {}
                if count:
                    kwargs['count'] = count
                if isinstance(freq, DataFrequency):
                    kwargs['frequency'] = freq.name
                else:
                    kwargs['frequency'] = str(freq)

                # 调用插件接口
                data = self.plugin.fetch_data(
                    symbol=symbol,
                    data_type=data_type,
                    start_date=start_date,
                    end_date=end_date,
                    **kwargs
                )

                # 更新统计信息
                response_time = (time.time() - start_time) * 1000
                self._update_success_stats(response_time)

                return data

        except Exception as e:
            self._update_error_stats(e)
            logger.error(f"获取K线数据失败 {self.plugin_id}: {e}")
            return pd.DataFrame()  # 返回空DataFrame保持兼容性

    def get_real_time_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取实时行情（适配DataSource接口）

        Args:
            symbols: 股票代码列表

        Returns:
            pd.DataFrame: 实时行情数据
        """
        start_time = time.time()

        try:
            with self._lock:
                self.stats["total_requests"] += 1

                if not self.is_connected():
                    raise ConnectionError(f"插件未连接: {self.plugin_id}")

                # 调用插件接口
                real_time_data = self.plugin.get_real_time_data(symbols)

                # 转换为DataFrame格式
                data = self._convert_real_time_data_to_dataframe(real_time_data)

                # 更新统计信息
                response_time = (time.time() - start_time) * 1000
                self._update_success_stats(response_time)

                return data

        except Exception as e:
            self._update_error_stats(e)
            logger.error(f"获取实时行情失败 {self.plugin_id}: {e}")
            return pd.DataFrame()

    def health_check(self) -> HealthCheckResult:
        """
        执行健康检查

        Returns:
            HealthCheckResult: 健康检查结果
        """
        try:
            # 检查是否需要执行健康检查
            now = datetime.now()
            if (self._last_health_check and
                    (now - self._last_health_check).total_seconds() < self._health_check_interval):
                return self._last_health_check_result

            # 执行健康检查
            raw_result = self.plugin.health_check()
            # 兼容不同实现的返回对象，标准化为本模块的 HealthCheckResult
            try:
                rt_ms = getattr(raw_result, 'response_time_ms', None)
                if rt_ms is None:
                    rt_ms = float(getattr(raw_result, 'response_time', 0.0))
                msg = getattr(raw_result, 'error_message', None)
                if msg is None:
                    msg = getattr(raw_result, 'message', None)
                add_info = getattr(raw_result, 'additional_info', None)
                if add_info is None:
                    add_info = getattr(raw_result, 'extra_info', {})
                result = HealthCheckResult(
                    is_healthy=bool(getattr(raw_result, 'is_healthy', False)),
                    response_time_ms=rt_ms,
                    error_message=msg,
                    additional_info=add_info,
                    timestamp=getattr(raw_result, 'timestamp', datetime.now())
                )
            except Exception:
                # 最小兜底
                result = HealthCheckResult(
                    is_healthy=False,
                    response_time_ms=0.0,
                    error_message="健康检查返回结果不兼容",
                )

            self._last_health_check = now
            self._last_health_check_result = result

            # 更新状态
            if result.is_healthy:
                if self.status == PluginStatus.ERROR:
                    self.status = PluginStatus.READY
                    logger.info(f"插件健康状态恢复: {self.plugin_id}")
            else:
                self.status = PluginStatus.ERROR
                self.last_error = result.error_message
                logger.warning(f"插件健康检查失败 {self.plugin_id}: {result.error_message}")

            return result

        except Exception as e:
            error_result = HealthCheckResult(
                is_healthy=False,
                response_time_ms=0.0,
                error_message=f"健康检查异常: {str(e)}",
                timestamp=datetime.now()
            )
            self.status = PluginStatus.ERROR
            self.last_error = str(e)
            logger.error(f"插件健康检查异常 {self.plugin_id}: {e}")
            return error_result

    def get_plugin_info(self) -> PluginInfo:
        """
        获取插件信息

        Returns:
            PluginInfo: 插件信息
        """
        return self.plugin.get_plugin_info()

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取插件统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        with self._lock:
            success_rate = 0.0
            if self.stats["total_requests"] > 0:
                success_rate = self.stats["successful_requests"] / self.stats["total_requests"]

            return {
                **self.stats,
                "success_rate": success_rate,
                "error_count": self.error_count,
                "last_error": self.last_error,
                "last_success_time": self.last_success_time,
                "status": self.status.value,
                "is_connected": self.is_connected()
            }

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        # 基础默认值
        default_config: Dict[str, Any] = {
            "timeout": 30,
            "retry_count": 3,
            "rate_limit": 100
        }

        # 尝试从数据库读取配置并与默认值合并
        try:
            # 延迟导入以避免循环依赖
            from db.models.plugin_models import get_data_source_config_manager  # type: ignore

            config_manager = get_data_source_config_manager()
            db_entry = config_manager.get_plugin_config(self.plugin_id)

            if db_entry and isinstance(db_entry, dict):
                config_data = db_entry.get("config_data", {}) if isinstance(db_entry.get("config_data", {}), dict) else {}
                # 合并：数据库优先，缺省回退到默认
                merged = {**default_config, **config_data}
                return merged

            # 如无记录则尝试从插件对象推断默认配置，并写入数据库进行初始化
            inferred_defaults: Dict[str, Any] = {}

            try:
                # 优先使用插件声明的 DEFAULT_CONFIG / default_config / config
                if hasattr(self.plugin, "DEFAULT_CONFIG") and isinstance(getattr(self.plugin, "DEFAULT_CONFIG"), dict):
                    inferred_defaults = getattr(self.plugin, "DEFAULT_CONFIG")  # type: ignore
                elif hasattr(self.plugin, "default_config") and isinstance(getattr(self.plugin, "default_config"), dict):
                    inferred_defaults = getattr(self.plugin, "default_config")  # type: ignore
                elif hasattr(self.plugin, "config") and isinstance(getattr(self.plugin, "config"), dict):
                    inferred_defaults = getattr(self.plugin, "config")  # type: ignore
            except Exception:
                inferred_defaults = {}

            seed_config = {**default_config, **(inferred_defaults or {})}

            # 将初始配置写入数据库，优先级/权重采用默认值
            try:
                config_manager.save_plugin_config(
                    plugin_id=self.plugin_id,
                    config_data=seed_config,
                    priority=50,
                    weight=1.0,
                    enabled=True,
                )
            except Exception:
                # 忽略写入失败，仍返回合并后的默认配置
                pass

            return seed_config

        except Exception:
            # 如果数据库不可用或发生错误，则回退基础默认值
            return default_config

    def _update_success_stats(self, response_time_ms: float) -> None:
        """更新成功统计"""
        self.stats["successful_requests"] += 1

        # 更新平均响应时间
        total_success = self.stats["successful_requests"]
        current_avg = self.stats["avg_response_time"]
        self.stats["avg_response_time"] = (
            (current_avg * (total_success - 1) + response_time_ms) / total_success
        )

        self.last_success_time = datetime.now()

    def _update_error_stats(self, error: Exception) -> None:
        """更新错误统计"""
        self.stats["failed_requests"] += 1
        self.error_count += 1
        self.last_error = str(error)
        self.status = PluginStatus.ERROR

    def _convert_real_time_data_to_dataframe(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        将实时数据转换为DataFrame格式

        Args:
            data: 实时数据字典

        Returns:
            pd.DataFrame: 转换后的DataFrame
        """
        try:
            if not data:
                return pd.DataFrame()

            # 转换为标准格式
            records = []
            for symbol, quote_data in data.items():
                if isinstance(quote_data, dict):
                    record = {"symbol": symbol, **quote_data}
                    records.append(record)

            return pd.DataFrame(records)

        except Exception as e:
            logger.error(f"实时数据转换失败: {e}")
            return pd.DataFrame()


class PluginInitializationError(Exception):
    """插件初始化错误"""
    pass


class DataFetchError(Exception):
    """数据获取错误"""
    pass


class RealTimeDataError(Exception):
    """实时数据错误"""
    pass


class PluginValidationError(Exception):
    """插件验证错误"""
    pass


def validate_plugin_interface(plugin: Any) -> bool:
    """
    验证插件是否实现了必要的接口

    Args:
        plugin: 待验证的插件实例

    Returns:
        bool: 是否通过验证

    Raises:
        PluginValidationError: 验证失败时抛出
    """
    try:
        # 检查是否实现了IDataSourcePlugin接口
        if not isinstance(plugin, IDataSourcePlugin):
            raise PluginValidationError("插件必须实现IDataSourcePlugin接口")

        # 检查必要方法是否存在
        required_methods = [
            'get_plugin_info', 'get_supported_asset_types', 'get_supported_data_types',
            'initialize', 'shutdown', 'fetch_data', 'get_real_time_data', 'health_check'
        ]

        for method_name in required_methods:
            if not hasattr(plugin, method_name):
                raise PluginValidationError(f"插件缺少必要方法: {method_name}")

            method = getattr(plugin, method_name)
            if not callable(method):
                raise PluginValidationError(f"插件方法不可调用: {method_name}")

        # 验证插件信息
        try:
            plugin_info = plugin.get_plugin_info()
            if not isinstance(plugin_info, PluginInfo):
                raise PluginValidationError("get_plugin_info必须返回PluginInfo实例")

            # 验证必要字段
            if not plugin_info.id or not plugin_info.name:
                raise PluginValidationError("插件ID和名称不能为空")

        except Exception as e:
            raise PluginValidationError(f"插件信息验证失败: {str(e)}")

        logger.info(f"插件验证成功: {plugin_info.id}")
        return True

    except PluginValidationError:
        raise
    except Exception as e:
        raise PluginValidationError(f"插件验证异常: {str(e)}")


# 导出的公共接口
__all__ = [
    'IDataSourcePlugin',
    'DataSourcePluginAdapter',
    'PluginInfo',
    'HealthCheckResult',
    'AssetType',
    'DataType',
    'PluginStatus',
    'PluginInitializationError',
    'DataFetchError',
    'RealTimeDataError',
    'PluginValidationError',
    'validate_plugin_interface'
]
