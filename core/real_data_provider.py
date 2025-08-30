#!/usr/bin/env python3
"""
真实数据提供器

提供真实的市场数据，替换项目中的虚假数据和测试数据
使用系统统一组件，确保数据的真实性和可靠性
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import threading
import time

# 使用系统统一组件
from core.adapters import get_logger, get_config, get_data_validator
from core.services.unified_data_manager import UnifiedDataManager


class RealDataProvider:
    """真实数据提供器 - 提供真实的市场数据"""

    def __init__(self):
        """初始化真实数据提供器"""
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.validator = get_data_validator()

        # 初始化数据管理器 - 使用工厂方法
        try:
            from utils.manager_factory import get_manager_factory, get_data_manager
            factory = get_manager_factory()
            self.data_manager = get_data_manager()
        except ImportError:
            from .services.unified_data_manager import get_unified_data_manager
            self.data_manager = get_unified_data_manager()

        # 缓存管理
        self._cache = {}
        self._cache_lock = threading.RLock()
        self._cache_ttl = self.config.get(
            'real_data', {}).get('cache_ttl', 300)  # 5分钟缓存

        # 默认股票池
        self._default_stocks = [
            '000001',  # 平安银行
            '000002',  # 万科A
            '000858',  # 五粮液
            '002415',  # 海康威视
            '600000',  # 浦发银行
            '600036',  # 招商银行
            '600519',  # 贵州茅台
            '600887',  # 伊利股份
            '000858',  # 五粮液
            '002304'   # 洋河股份
        ]

        self.logger.info("真实数据提供器初始化完成")

    def get_real_kdata(self, code: str, freq: str = 'D',
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       count: int = 250) -> pd.DataFrame:
        """获取真实K线数据

        Args:
            code: 股票代码
            freq: 频率 ('D', 'W', 'M', '60', '30', '15', '5', '1')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            count: 数据条数（当未指定日期时使用）

        Returns:
            真实K线数据DataFrame
        """
        try:
            cache_key = f"kdata_{code}_{freq}_{start_date}_{end_date}_{count}"

            # 检查缓存
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                self.logger.debug(f"从缓存获取K线数据: {code}")
                return cached_data

            self.logger.info(f"获取真实K线数据: {code}, 频率: {freq}")

            # 使用数据管理器获取真实数据
            if start_date or end_date:
                kdata = self.data_manager.get_k_data(
                    code=code,
                    freq=freq,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                # 获取最近count条数据
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=count * 2)  # 预留足够天数
                kdata = self.data_manager.get_k_data(
                    code=code,
                    freq=freq,
                    start_date=start_dt.strftime('%Y-%m-%d'),
                    end_date=end_dt.strftime('%Y-%m-%d')
                )

                # 取最后count条
                if len(kdata) > count:
                    kdata = kdata.tail(count)

            # 数据验证
            if kdata.empty:
                self.logger.warning(f"获取到空的K线数据: {code}")
                return pd.DataFrame()

            # 确保数据完整性
            kdata = self._validate_and_clean_kdata(kdata, code)

            # 缓存数据
            self._set_to_cache(cache_key, kdata)

            self.logger.info(f"成功获取真实K线数据: {code}, 数据量: {len(kdata)}")
            return kdata

        except Exception as e:
            self.logger.error(f"获取真实K线数据失败 {code}: {e}")
            return pd.DataFrame()

    def get_multiple_stocks_data(self, codes: List[str], freq: str = 'D',
                                 count: int = 250) -> Dict[str, pd.DataFrame]:
        """批量获取多只股票的真实数据

        Args:
            codes: 股票代码列表
            freq: 频率
            count: 每只股票的数据条数

        Returns:
            股票代码到K线数据的映射
        """
        try:
            self.logger.info(f"批量获取真实数据: {len(codes)} 只股票")

            results = {}
            success_count = 0
            failed_count = 0

            for code in codes:
                try:
                    kdata = self.get_real_kdata(code, freq=freq, count=count)
                    if not kdata.empty:
                        results[code] = kdata
                        success_count += 1
                        self.logger.debug(f"成功获取数据: {code}")
                    else:
                        failed_count += 1
                        self.logger.warning(f"获取数据为空: {code}")
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"获取数据失败 {code}: {e}")

            self.logger.info(f"批量获取完成: 成功 {success_count}, 失败 {failed_count}")
            return results

        except Exception as e:
            self.logger.error(f"批量获取真实数据失败: {e}")
            return {}

    def get_default_test_stocks(self, count: int = 5) -> List[str]:
        """获取默认的测试股票列表

        Args:
            count: 返回股票数量

        Returns:
            股票代码列表
        """
        try:
            # 从股票池中选择活跃的股票
            available_stocks = []

            for code in self._default_stocks:
                try:
                    # 检查股票是否有效
                    test_data = self.get_real_kdata(code, count=5)
                    if not test_data.empty:
                        available_stocks.append(code)
                        if len(available_stocks) >= count:
                            break
                except:
                    continue

            if len(available_stocks) < count:
                self.logger.warning(
                    f"只找到 {len(available_stocks)} 只有效股票，少于请求的 {count} 只")

            self.logger.info(f"获取默认测试股票: {available_stocks}")
            return available_stocks[:count]

        except Exception as e:
            self.logger.error(f"获取默认测试股票失败: {e}")
            return self._default_stocks[:count]

    def create_real_test_datasets(self, pattern_name: str, count: int = 5) -> List[Dict[str, Any]]:
        """创建真实的测试数据集，替换虚假数据

        Args:
            pattern_name: 形态名称
            count: 数据集数量

        Returns:
            真实测试数据集列表
        """
        try:
            self.logger.info(f"创建真实测试数据集: {pattern_name}, 数量: {count}")

            # 获取测试股票
            test_stocks = self.get_default_test_stocks(count)

            datasets = []
            for i, code in enumerate(test_stocks):
                try:
                    # 获取真实K线数据
                    kdata = self.get_real_kdata(code, count=250)

                    if kdata.empty:
                        self.logger.warning(f"股票 {code} 数据为空，跳过")
                        continue

                    # 创建数据集
                    dataset = {
                        'name': f"{pattern_name}_real_dataset_{i+1}",
                        'code': code,
                        'data': kdata,
                        'pattern_name': pattern_name,
                        'data_source': 'real_market',
                        'created_at': datetime.now(),
                        'data_count': len(kdata),
                        'date_range': {
                            'start': kdata.index[0] if len(kdata) > 0 else None,
                            'end': kdata.index[-1] if len(kdata) > 0 else None
                        }
                    }

                    datasets.append(dataset)
                    self.logger.debug(f"创建数据集: {code}, 数据量: {len(kdata)}")

                except Exception as e:
                    self.logger.error(f"创建数据集失败 {code}: {e}")

            self.logger.info(f"成功创建 {len(datasets)} 个真实测试数据集")
            return datasets

        except Exception as e:
            self.logger.error(f"创建真实测试数据集失败: {e}")
            return []

    def get_real_stock_list(self, market: str = 'all', limit: int = 100) -> List[str]:
        """获取真实股票列表

        Args:
            market: 市场类型 ('all', 'sh', 'sz', 'bj')
            limit: 返回数量限制

        Returns:
            股票代码列表
        """
        try:
            self.logger.info(f"获取真实股票列表: 市场={market}, 限制={limit}")

            # 使用数据管理器获取股票列表
            stock_df = self.data_manager.get_stock_list(market=market)

            if stock_df.empty:
                self.logger.warning("获取到空的股票列表")
                return []

            # 提取股票代码
            if 'code' in stock_df.columns:
                codes = stock_df['code'].tolist()
            elif stock_df.index.name == 'code':
                codes = stock_df.index.tolist()
            else:
                codes = stock_df.iloc[:, 0].tolist()  # 假设第一列是代码

            # 限制数量
            if limit > 0:
                codes = codes[:limit]

            self.logger.info(f"获取到 {len(codes)} 只股票")
            return codes

        except Exception as e:
            self.logger.error(f"获取真实股票列表失败: {e}")
            return []

    def _validate_and_clean_kdata(self, kdata: pd.DataFrame, code: str) -> pd.DataFrame:
        """验证和清理K线数据

        Args:
            kdata: K线数据
            code: 股票代码

        Returns:
            清理后的K线数据
        """
        try:
            if kdata.empty:
                return kdata

            # 确保必要的列存在
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [
                col for col in required_columns if col not in kdata.columns]

            if missing_columns:
                self.logger.warning(f"股票 {code} 缺少列: {missing_columns}")
                return pd.DataFrame()

            # 移除无效数据
            kdata = kdata.dropna(subset=required_columns)

            # 确保价格关系正确 (high >= low, high >= open, high >= close, low <= open, low <= close)
            invalid_mask = (
                (kdata['high'] < kdata['low']) |
                (kdata['high'] < kdata['open']) |
                (kdata['high'] < kdata['close']) |
                (kdata['low'] > kdata['open']) |
                (kdata['low'] > kdata['close'])
            )

            if invalid_mask.any():
                invalid_count = invalid_mask.sum()
                self.logger.warning(
                    f"股票 {code} 有 {invalid_count} 条无效价格关系数据，已移除")
                kdata = kdata[~invalid_mask]

            # 确保成交量为正数
            kdata = kdata[kdata['volume'] > 0]

            # 添加code字段（如果不存在）
            if 'code' not in kdata.columns:
                kdata['code'] = code

            # 确保索引为时间类型
            if not isinstance(kdata.index, pd.DatetimeIndex):
                if 'datetime' in kdata.columns:
                    kdata['datetime'] = pd.to_datetime(kdata['datetime'])
                    kdata.set_index('datetime', inplace=True)

            # 按时间排序
            kdata = kdata.sort_index()

            self.logger.debug(f"数据验证完成: {code}, 有效数据量: {len(kdata)}")
            return kdata

        except Exception as e:
            self.logger.error(f"验证和清理K线数据失败 {code}: {e}")
            return pd.DataFrame()

    def _get_from_cache(self, key: str) -> Optional[pd.DataFrame]:
        """从缓存获取数据"""
        with self._cache_lock:
            if key in self._cache:
                data, timestamp = self._cache[key]
                if time.time() - timestamp < self._cache_ttl:
                    return data.copy()
                else:
                    del self._cache[key]
            return None

    def _set_to_cache(self, key: str, data: pd.DataFrame):
        """设置数据到缓存"""
        with self._cache_lock:
            self._cache[key] = (data.copy(), time.time())

    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._cache.clear()
            self.logger.info("真实数据提供器缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._cache_lock:
            current_time = time.time()
            valid_count = 0
            expired_count = 0

            for key, (data, timestamp) in self._cache.items():
                if current_time - timestamp < self._cache_ttl:
                    valid_count += 1
                else:
                    expired_count += 1

            return {
                'total_cached': len(self._cache),
                'valid_cached': valid_count,
                'expired_cached': expired_count,
                'cache_ttl': self._cache_ttl
            }


# 全局真实数据提供器实例
_real_data_provider: Optional[RealDataProvider] = None
_provider_lock = threading.RLock()


def get_real_data_provider() -> RealDataProvider:
    """获取全局真实数据提供器实例

    Returns:
        真实数据提供器实例
    """
    global _real_data_provider

    with _provider_lock:
        if _real_data_provider is None:
            _real_data_provider = RealDataProvider()

        return _real_data_provider


def initialize_real_data_provider() -> RealDataProvider:
    """初始化真实数据提供器

    Returns:
        真实数据提供器实例
    """
    global _real_data_provider

    with _provider_lock:
        _real_data_provider = RealDataProvider()
        return _real_data_provider


# 便捷函数
def get_real_kdata(code: str, **kwargs) -> pd.DataFrame:
    """获取真实K线数据的便捷函数"""
    provider = get_real_data_provider()
    return provider.get_real_kdata(code, **kwargs)


def create_real_test_data(pattern_name: str = "test", count: int = 5) -> List[Dict[str, Any]]:
    """创建真实测试数据的便捷函数"""
    provider = get_real_data_provider()
    return provider.create_real_test_datasets(pattern_name, count)


def get_real_stock_list(**kwargs) -> List[str]:
    """获取真实股票列表的便捷函数"""
    provider = get_real_data_provider()
    return provider.get_real_stock_list(**kwargs)
