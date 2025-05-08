from PyQt5.QtCore import QObject, pyqtSignal, QThread
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from indicators_algo import *


class AsyncDataProcessor(QObject):
    """异步数据处理器，处理大数据量的计算和渲染"""

    # 定义信号
    calculation_progress = pyqtSignal(int, str)  # 进度信号
    calculation_complete = pyqtSignal(dict)  # 计算完成信号
    calculation_error = pyqtSignal(str)  # 错误信号

    def __init__(self, max_workers: int = 4):
        super().__init__()
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._chunk_size = 1000  # 数据分块大小
        self._cache = {}  # 计算结果缓存

    def process_data(self, data: pd.DataFrame, indicators: List[str], params: Dict[str, Any]):
        """异步处理数据和计算指标

        Args:
            data: K线数据
            indicators: 需要计算的指标列表
            params: 指标参数
        """
        try:
            # 将数据分块
            chunks = self._split_data(data)
            total_chunks = len(chunks)

            # 创建异步任务
            futures = []
            for i, chunk in enumerate(chunks):
                future = self.thread_pool.submit(
                    self._process_chunk,
                    chunk,
                    indicators,
                    params,
                    i,
                    total_chunks
                )
                futures.append(future)

            # 收集结果
            results = {}
            for future in as_completed(futures):
                chunk_result = future.result()
                results.update(chunk_result)

            # 合并结果
            final_results = self._merge_results(results, data.index)
            self.calculation_complete.emit(final_results)

        except Exception as e:
            self.calculation_error.emit(str(e))

    def _split_data(self, data: pd.DataFrame) -> List[pd.DataFrame]:
        """将数据分块处理

        Args:
            data: 原始数据

        Returns:
            数据块列表
        """
        if len(data) <= self._chunk_size:
            return [data]

        chunks = []
        for i in range(0, len(data), self._chunk_size):
            chunk = data.iloc[i:i + self._chunk_size].copy()
            chunks.append(chunk)
        return chunks

    def _process_chunk(self, chunk: pd.DataFrame, indicators: List[str],
                       params: Dict[str, Any], chunk_idx: int, total_chunks: int) -> Dict[str, pd.Series]:
        """处理数据块

        Args:
            chunk: 数据块
            indicators: 指标列表
            params: 参数字典
            chunk_idx: 块索引
            total_chunks: 总块数

        Returns:
            计算结果字典
        """
        try:
            results = {}

            # 计算进度
            progress = int((chunk_idx + 1) / total_chunks * 100)
            self.calculation_progress.emit(
                progress, f"正在处理第 {chunk_idx + 1}/{total_chunks} 块数据...")

            # 并行计算多个指标
            with ThreadPoolExecutor() as indicator_pool:
                futures = []
                for indicator in indicators:
                    future = indicator_pool.submit(
                        self._calculate_indicator,
                        chunk,
                        indicator,
                        params.get(indicator, {})
                    )
                    futures.append((indicator, future))

                # 收集结果
                for indicator, future in futures:
                    try:
                        result = future.result()
                        if isinstance(result, tuple):
                            for i, name in enumerate([f"{indicator}_{i}" for i in range(len(result))]):
                                results[name] = result[i]
                        else:
                            results[indicator] = result
                    except Exception as e:
                        self.calculation_error.emit(
                            f"计算指标 {indicator} 失败: {str(e)}")

            return results

        except Exception as e:
            self.calculation_error.emit(f"处理数据块失败: {str(e)}")
            return {}

    def _calculate_indicator(self, data: pd.DataFrame, indicator: str, params: Dict[str, Any]) -> Any:
        """计算单个指标

        Args:
            data: K线数据
            indicator: 指标名称
            params: 指标参数

        Returns:
            计算结果
        """
        # 生成缓存键
        cache_key = f"{indicator}_{hash(str(data.index[0]))}"

        # 检查缓存
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 计算指标
        result = None
        if indicator == 'MA':
            result = calc_ma(data['close'], params.get('period', 20))
        elif indicator == 'MACD':
            result = calc_macd(data['close'],
                               params.get('fast', 12),
                               params.get('slow', 26),
                               params.get('signal', 9))
        elif indicator == 'RSI':
            result = calc_rsi(data['close'], params.get('period', 14))
        elif indicator == 'KDJ':
            result = calc_kdj(data,
                              params.get('n', 9),
                              params.get('m1', 3),
                              params.get('m2', 3))
        elif indicator == 'BOLL':
            result = calc_boll(data['close'],
                               params.get('n', 20),
                               params.get('p', 2))
        elif indicator == 'ATR':
            result = calc_atr(data, params.get('n', 14))
        elif indicator == 'OBV':
            result = calc_obv(data)
        elif indicator == 'CCI':
            result = calc_cci(data, params.get('n', 14))

        # 缓存结果
        if result is not None:
            self._cache[cache_key] = result

        return result

    def _merge_results(self, results: Dict[str, Dict[str, pd.Series]],
                       original_index: pd.Index) -> Dict[str, pd.Series]:
        """合并计算结果

        Args:
            results: 分块计算结果
            original_index: 原始数据索引

        Returns:
            合并后的结果
        """
        merged = {}
        for indicator in results:
            if isinstance(results[indicator], pd.Series):
                merged[indicator] = results[indicator].reindex(original_index)
            elif isinstance(results[indicator], tuple):
                merged[indicator] = tuple(
                    series.reindex(original_index) for series in results[indicator]
                )
        return merged

    def clear_cache(self):
        """清除计算缓存"""
        self._cache.clear()
