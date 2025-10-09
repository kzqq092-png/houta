#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易执行基准计算模块
实现TWAP、VWAP等基准价格计算逻辑
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

class ExecutionBenchmarks:
    """交易执行基准计算器"""

    def __init__(self):
        self.logger = logger

    def calculate_twap(self, kdata: pd.DataFrame, start_time: datetime,
                       end_time: datetime) -> float:
        """
        计算时间加权平均价格 (TWAP)

        Args:
            kdata: K线数据，包含时间、开高低收等字段
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            float: TWAP价格
        """
        try:
            if kdata.empty:
                return 0.0

            # 确保数据按时间排序
            if 'datetime' in kdata.columns:
                kdata = kdata.sort_values('datetime')
                time_col = 'datetime'
            elif 'date' in kdata.columns:
                kdata = kdata.sort_values('date')
                time_col = 'date'
            else:
                self.logger.warning("K线数据缺少时间字段")
                return 0.0

            # 筛选时间范围内的数据
            mask = (kdata[time_col] >= start_time) & (kdata[time_col] <= end_time)
            filtered_data = kdata[mask].copy()

            if filtered_data.empty:
                return 0.0

            # 计算每个时间段的典型价格 (High + Low + Close) / 3
            if all(col in filtered_data.columns for col in ['high', 'low', 'close']):
                typical_prices = (filtered_data['high'] + filtered_data['low'] + filtered_data['close']) / 3
            elif 'close' in filtered_data.columns:
                typical_prices = filtered_data['close']
            else:
                self.logger.warning("K线数据缺少价格字段")
                return 0.0

            # 计算时间权重（假设每个K线时间段相等）
            twap = typical_prices.mean()

            self.logger.debug(f"TWAP计算完成: {twap:.4f}, 数据点数: {len(filtered_data)}")
            return float(twap)

        except Exception as e:
            self.logger.error(f"TWAP计算失败: {e}")
            return 0.0

    def calculate_vwap(self, kdata: pd.DataFrame, start_time: datetime,
                       end_time: datetime) -> float:
        """
        计算成交量加权平均价格 (VWAP)

        Args:
            kdata: K线数据，包含时间、价格、成交量等字段
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            float: VWAP价格
        """
        try:
            if kdata.empty:
                return 0.0

            # 确保数据按时间排序
            if 'datetime' in kdata.columns:
                kdata = kdata.sort_values('datetime')
                time_col = 'datetime'
            elif 'date' in kdata.columns:
                kdata = kdata.sort_values('date')
                time_col = 'date'
            else:
                self.logger.warning("K线数据缺少时间字段")
                return 0.0

            # 筛选时间范围内的数据
            mask = (kdata[time_col] >= start_time) & (kdata[time_col] <= end_time)
            filtered_data = kdata[mask].copy()

            if filtered_data.empty:
                return 0.0

            # 检查必要字段
            if 'volume' not in filtered_data.columns:
                self.logger.warning("K线数据缺少成交量字段，使用TWAP替代")
                return self.calculate_twap(kdata, start_time, end_time)

            # 计算典型价格
            if all(col in filtered_data.columns for col in ['high', 'low', 'close']):
                typical_prices = (filtered_data['high'] + filtered_data['low'] + filtered_data['close']) / 3
            elif 'close' in filtered_data.columns:
                typical_prices = filtered_data['close']
            else:
                self.logger.warning("K线数据缺少价格字段")
                return 0.0

            # 计算VWAP = Σ(典型价格 × 成交量) / Σ(成交量)
            volumes = filtered_data['volume']

            # 过滤零成交量的数据
            valid_mask = volumes > 0
            if not valid_mask.any():
                self.logger.warning("所有数据成交量为零，使用TWAP替代")
                return self.calculate_twap(kdata, start_time, end_time)

            valid_prices = typical_prices[valid_mask]
            valid_volumes = volumes[valid_mask]

            # 计算VWAP
            total_value = (valid_prices * valid_volumes).sum()
            total_volume = valid_volumes.sum()

            if total_volume == 0:
                return 0.0

            vwap = total_value / total_volume

            self.logger.debug(f"VWAP计算完成: {vwap:.4f}, 总成交量: {total_volume}")
            return float(vwap)

        except Exception as e:
            self.logger.error(f"VWAP计算失败: {e}")
            return 0.0

    def calculate_execution_deviation(self, execution_price: float,
                                      benchmark_price: float) -> float:
        """
        计算执行偏差

        Args:
            execution_price: 实际执行价格
            benchmark_price: 基准价格

        Returns:
            float: 执行偏差（百分比）
        """
        try:
            if benchmark_price == 0:
                return 0.0

            deviation = ((execution_price - benchmark_price) / benchmark_price) * 100
            return float(deviation)

        except Exception as e:
            self.logger.error(f"执行偏差计算失败: {e}")
            return 0.0

    def calculate_implementation_shortfall(self, decision_price: float,
                                           execution_price: float,
                                           shares: int) -> Dict[str, float]:
        """
        计算实施缺口 (Implementation Shortfall)

        Args:
            decision_price: 决策价格
            execution_price: 执行价格
            shares: 股数

        Returns:
            Dict[str, float]: 实施缺口分析结果
        """
        try:
            if decision_price == 0 or shares == 0:
                return {
                    'implementation_shortfall': 0.0,
                    'shortfall_bps': 0.0,
                    'shortfall_amount': 0.0
                }

            # 计算实施缺口
            shortfall_per_share = execution_price - decision_price
            total_shortfall = shortfall_per_share * shares

            # 转换为基点 (basis points)
            shortfall_bps = (shortfall_per_share / decision_price) * 10000

            # 计算百分比
            shortfall_pct = (shortfall_per_share / decision_price) * 100

            result = {
                'implementation_shortfall': float(shortfall_pct),
                'shortfall_bps': float(shortfall_bps),
                'shortfall_amount': float(total_shortfall)
            }

            self.logger.debug(f"实施缺口计算完成: {shortfall_pct:.4f}%")
            return result

        except Exception as e:
            self.logger.error(f"实施缺口计算失败: {e}")
            return {
                'implementation_shortfall': 0.0,
                'shortfall_bps': 0.0,
                'shortfall_amount': 0.0
            }

    def calculate_market_impact(self, pre_trade_price: float,
                                post_trade_price: float,
                                trade_volume: int,
                                avg_daily_volume: int) -> Dict[str, float]:
        """
        计算市场冲击

        Args:
            pre_trade_price: 交易前价格
            post_trade_price: 交易后价格
            trade_volume: 交易量
            avg_daily_volume: 平均日成交量

        Returns:
            Dict[str, float]: 市场冲击分析结果
        """
        try:
            if pre_trade_price == 0 or avg_daily_volume == 0:
                return {
                    'market_impact': 0.0,
                    'impact_bps': 0.0,
                    'participation_rate': 0.0
                }

            # 计算价格冲击
            price_impact = ((post_trade_price - pre_trade_price) / pre_trade_price) * 100

            # 转换为基点
            impact_bps = price_impact * 100

            # 计算参与率
            participation_rate = (trade_volume / avg_daily_volume) * 100 if avg_daily_volume > 0 else 0

            result = {
                'market_impact': float(price_impact),
                'impact_bps': float(impact_bps),
                'participation_rate': float(participation_rate)
            }

            self.logger.debug(f"市场冲击计算完成: {price_impact:.4f}%")
            return result

        except Exception as e:
            self.logger.error(f"市场冲击计算失败: {e}")
            return {
                'market_impact': 0.0,
                'impact_bps': 0.0,
                'participation_rate': 0.0
            }

    def get_benchmark_prices(self, symbol: str, start_time: datetime,
                             end_time: datetime) -> Dict[str, float]:
        """
        获取指定时间段的基准价格

        Args:
            symbol: 股票代码
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            Dict[str, float]: 基准价格字典
        """
        try:
            # 尝试从数据管理器获取K线数据
            from core.services.unified_data_manager import UnifiedDataManager, get_unified_data_manager

            data_manager = get_unified_data_manager()
            kdata = data_manager.get_kdata(
                symbol=symbol,
                start_date=start_time.strftime('%Y-%m-%d'),
                end_date=end_time.strftime('%Y-%m-%d'),
                period='1m'  # 使用1分钟数据计算更精确的基准
            )

            if kdata is None or kdata.empty:
                self.logger.warning(f"无法获取{symbol}的K线数据")
                return {
                    'twap': 0.0,
                    'vwap': 0.0,
                    'open': 0.0,
                    'close': 0.0,
                    'high': 0.0,
                    'low': 0.0
                }

            # 计算各种基准价格
            twap = self.calculate_twap(kdata, start_time, end_time)
            vwap = self.calculate_vwap(kdata, start_time, end_time)

            # 获取开高低收价格
            first_row = kdata.iloc[0] if len(kdata) > 0 else None
            last_row = kdata.iloc[-1] if len(kdata) > 0 else None

            open_price = float(first_row['open']) if first_row is not None and 'open' in first_row else 0.0
            close_price = float(last_row['close']) if last_row is not None and 'close' in last_row else 0.0
            high_price = float(kdata['high'].max()) if 'high' in kdata.columns else 0.0
            low_price = float(kdata['low'].min()) if 'low' in kdata.columns else 0.0

            result = {
                'twap': twap,
                'vwap': vwap,
                'open': open_price,
                'close': close_price,
                'high': high_price,
                'low': low_price
            }

            self.logger.info(f"基准价格计算完成: {symbol}, TWAP={twap:.4f}, VWAP={vwap:.4f}")
            return result

        except Exception as e:
            self.logger.error(f"基准价格获取失败: {e}")
            return {
                'twap': 0.0,
                'vwap': 0.0,
                'open': 0.0,
                'close': 0.0,
                'high': 0.0,
                'low': 0.0
            }

# 全局实例
_execution_benchmarks = None

def get_execution_benchmarks() -> ExecutionBenchmarks:
    """获取执行基准计算器实例"""
    global _execution_benchmarks
    if _execution_benchmarks is None:
        _execution_benchmarks = ExecutionBenchmarks()
    return _execution_benchmarks
