"""
统一数据访问适配器

提供统一的数据访问接口，替代UI层和其他组件的直接HIkyuu调用。
所有数据访问都通过插件系统进行，确保架构一致性。
"""

import logging
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .asset_service import AssetService
from .unified_data_manager import UnifiedDataManager
from ..plugin_types import AssetType, DataType
from ..tet_data_pipeline import StandardQuery

logger = logging.getLogger(__name__)


class UnifiedDataAccessor:
    """
    统一数据访问适配器

    提供简化的数据访问接口，内部通过插件系统获取数据。
    用于替代UI层和其他组件的直接数据源调用。
    """

    def __init__(self, asset_service: AssetService = None, data_manager: UnifiedDataManager = None):
        """
        初始化统一数据访问器

        Args:
            asset_service: 资产服务实例
            data_manager: 统一数据管理器实例
        """
        self.asset_service = asset_service
        self.data_manager = data_manager
        self.logger = logging.getLogger(self.__class__.__name__)

        # 如果没有提供服务，尝试从服务容器获取
        if not self.asset_service or not self.data_manager:
            self._init_services_from_container()

    def _init_services_from_container(self):
        """从服务容器初始化服务"""
        try:
            from ..containers.service_container import get_service_container
            container = get_service_container()

            if container:
                if not self.asset_service:
                    self.asset_service = container.get('AssetService')
                if not self.data_manager:
                    self.data_manager = container.get('UnifiedDataManager')

                self.logger.info("✅ 从服务容器初始化服务成功")
            else:
                self.logger.warning("⚠️ 服务容器不可用")

        except Exception as e:
            self.logger.error(f"❌ 从服务容器初始化服务失败: {e}")

    def get_stock_data(self, stock_code: str, period: str = 'D', count: int = 30) -> Optional[pd.DataFrame]:
        """
        获取股票K线数据

        Args:
            stock_code: 股票代码
            period: 数据周期 ('D', 'W', 'M', '1', '5', '15', '30', '60')
            count: 数据条数

        Returns:
            DataFrame: K线数据，包含open, high, low, close, volume等列
        """
        try:
            self.logger.info(f"📊 获取股票数据: {stock_code}, period={period}, count={count}")

            if self.asset_service:
                # 通过资产服务获取历史数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=count*2)).strftime('%Y-%m-%d')  # 预留更多天数

                df = self.asset_service.get_historical_data(
                    symbol=stock_code,
                    asset_type=AssetType.STOCK,
                    start_date=start_date,
                    end_date=end_date,
                    period=period
                )

                if df is not None and not df.empty:
                    # 限制返回条数
                    if len(df) > count:
                        df = df.tail(count)

                    self.logger.info(f"✅ 通过资产服务获取股票数据成功: {len(df)} 条记录")
                    return df
                else:
                    self.logger.warning("资产服务返回空数据")

            elif self.data_manager:
                # 降级到数据管理器
                df = self.data_manager._get_hikyuu_kdata(stock_code, period, count)
                if df is not None and not df.empty:
                    self.logger.info(f"✅ 通过数据管理器获取股票数据成功: {len(df)} 条记录")
                    return df
                else:
                    self.logger.warning("数据管理器返回空数据")

            self.logger.error("❌ 无可用的数据服务")
            return None

        except Exception as e:
            self.logger.error(f"❌ 获取股票数据失败: {e}")
            return None

    def get_stock_list(self, market: str = 'all') -> List[Dict[str, Any]]:
        """
        获取股票列表

        Args:
            market: 市场代码 ('all', 'sh', 'sz', 'bj')

        Returns:
            List[Dict]: 股票列表
        """
        try:
            self.logger.info(f"📋 获取股票列表: market={market}")

            if self.asset_service:
                # 通过资产服务获取股票列表
                stock_list = self.asset_service.get_asset_list(AssetType.STOCK, market=market)

                if stock_list:
                    self.logger.info(f"✅ 通过资产服务获取股票列表成功: {len(stock_list)} 只股票")
                    return stock_list
                else:
                    self.logger.warning("资产服务返回空股票列表")

            elif self.data_manager:
                # 降级到数据管理器
                df = self.data_manager.get_stock_list(market)
                if df is not None and not df.empty:
                    stock_list = df.to_dict('records')
                    self.logger.info(f"✅ 通过数据管理器获取股票列表成功: {len(stock_list)} 只股票")
                    return stock_list
                else:
                    self.logger.warning("数据管理器返回空股票列表")

            self.logger.error("❌ 无可用的数据服务")
            return []

        except Exception as e:
            self.logger.error(f"❌ 获取股票列表失败: {e}")
            return []

    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 股票基本信息
        """
        try:
            self.logger.info(f"ℹ️ 获取股票信息: {stock_code}")

            # 从股票列表中查找
            stock_list = self.get_stock_list()
            for stock in stock_list:
                if stock.get('code') == stock_code or stock.get('symbol') == stock_code:
                    self.logger.info(f"✅ 找到股票信息: {stock.get('name', 'Unknown')}")
                    return stock

            self.logger.warning(f"⚠️ 未找到股票信息: {stock_code}")
            return None

        except Exception as e:
            self.logger.error(f"❌ 获取股票信息失败: {e}")
            return None

    def is_stock_valid(self, stock_code: str) -> bool:
        """
        检查股票代码是否有效

        Args:
            stock_code: 股票代码

        Returns:
            bool: 是否有效
        """
        try:
            stock_info = self.get_stock_info(stock_code)
            return stock_info is not None

        except Exception as e:
            self.logger.error(f"❌ 检查股票有效性失败: {e}")
            return False

    def calculate_historical_average(self, stock_code: str, days: int = 30, field: str = 'close') -> Optional[float]:
        """
        计算历史平均值

        Args:
            stock_code: 股票代码
            days: 历史天数
            field: 字段名 ('close', 'open', 'high', 'low', 'volume')

        Returns:
            float: 历史平均值
        """
        try:
            df = self.get_stock_data(stock_code, period='D', count=days)
            if df is not None and not df.empty and field in df.columns:
                avg_value = df[field].mean()
                self.logger.info(f"✅ 计算历史平均值成功: {stock_code} {field} {days}天平均 = {avg_value:.2f}")
                return float(avg_value)
            else:
                self.logger.warning(f"⚠️ 无法计算历史平均值: {stock_code} {field}")
                return None

        except Exception as e:
            self.logger.error(f"❌ 计算历史平均值失败: {e}")
            return None


# 全局单例实例
_global_accessor = None


def get_unified_data_accessor() -> UnifiedDataAccessor:
    """
    获取全局统一数据访问器实例

    Returns:
        UnifiedDataAccessor: 统一数据访问器实例
    """
    global _global_accessor
    if _global_accessor is None:
        _global_accessor = UnifiedDataAccessor()
    return _global_accessor


# 便捷函数，用于替代直接HIkyuu调用
def get_stock_data(stock_code: str, period: str = 'D', count: int = 30) -> Optional[pd.DataFrame]:
    """便捷函数：获取股票数据"""
    return get_unified_data_accessor().get_stock_data(stock_code, period, count)


def get_stock_list(market: str = 'all') -> List[Dict[str, Any]]:
    """便捷函数：获取股票列表"""
    return get_unified_data_accessor().get_stock_list(market)


def get_stock_info(stock_code: str) -> Optional[Dict[str, Any]]:
    """便捷函数：获取股票信息"""
    return get_unified_data_accessor().get_stock_info(stock_code)


def is_stock_valid(stock_code: str) -> bool:
    """便捷函数：检查股票有效性"""
    return get_unified_data_accessor().is_stock_valid(stock_code)


def calculate_historical_average(stock_code: str, days: int = 30, field: str = 'close') -> Optional[float]:
    """便捷函数：计算历史平均值"""
    return get_unified_data_accessor().calculate_historical_average(stock_code, days, field)
