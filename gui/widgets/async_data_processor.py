"""
异步数据处理器
用于在后台线程中处理数据计算任务
"""

# 使用新的指标服务架构
from core.services.indicator_ui_adapter import IndicatorUIAdapter
from PyQt5.QtCore import QObject, QThread, pyqtSignal
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import traceback


class AsyncDataProcessor(QObject):
    """异步数据处理器"""

    # 信号定义
    data_processed = pyqtSignal(dict)  # 数据处理完成信号
    error_occurred = pyqtSignal(str)   # 错误发生信号
    progress_updated = pyqtSignal(int)  # 进度更新信号

    # 添加缺失的信号定义，与chart_widget.py中的连接保持一致
    calculation_progress = pyqtSignal(int, str)  # 计算进度信号 (进度值, 消息)
    calculation_complete = pyqtSignal(dict)      # 计算完成信号
    calculation_error = pyqtSignal(str)          # 计算错误信号

    def __init__(self, parent=None):
        """初始化异步数据处理器

        Args:
            parent: 父对象
        """
        super().__init__(parent)

        # 使用新的指标服务架构
        self.indicator_adapter = IndicatorUIAdapter()

        # 处理状态
        self.is_processing = False
        self.should_stop = False

    def process_indicators(self, data: pd.DataFrame, indicators: List[Dict[str, Any]]):
        """处理指标计算

        Args:
            data: K线数据
            indicators: 指标配置列表，格式：[{'name': 'MA', 'params': {'period': 20}}, ...]
        """
        try:
            if self.is_processing:
                self.calculation_error.emit("正在处理中，请稍候...")
                return

            self.is_processing = True
            self.should_stop = False

            results = {}
            total_indicators = len(indicators)

            for i, indicator_config in enumerate(indicators):
                if self.should_stop:
                    break

                try:
                    # 更新进度
                    progress = int((i / total_indicators) * 100)
                    indicator_name = indicator_config.get('name', '')
                    self.calculation_progress.emit(progress, f"正在计算 {indicator_name}...")
                    self.progress_updated.emit(progress)

                    # 处理单个指标
                    params = indicator_config.get('params', {})

                    result = self._calculate_single_indicator(data, indicator_name, params)
                    if result is not None:
                        results[indicator_name] = result

                except Exception as e:
                    error_msg = f"计算指标 {indicator_name} 失败: {str(e)}"
                    print(error_msg)
                    self.calculation_error.emit(error_msg)
                    self.error_occurred.emit(error_msg)
                    continue

            # 处理完成
            self.calculation_progress.emit(100, "计算完成")
            self.progress_updated.emit(100)
            self.calculation_complete.emit(results)
            self.data_processed.emit(results)

        except Exception as e:
            error_msg = f"异步处理失败: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            self.calculation_error.emit(error_msg)
            self.error_occurred.emit(error_msg)
        finally:
            self.is_processing = False

    def _calculate_single_indicator(self, data: pd.DataFrame, indicator_name: str,
                                    params: Dict[str, Any]) -> Optional[Any]:
        """计算单个指标

        Args:
            data: K线数据
            indicator_name: 指标名称
            params: 指标参数

        Returns:
            指标计算结果
        """
        try:
            # 使用新的指标服务架构
            response = self.indicator_adapter.calculate_indicator(indicator_name, data, **params)
            if response.success:
                return response.result
            else:
                print(f"计算指标 {indicator_name} 失败: {response.error}")
                return self._calculate_indicator_fallback(data, indicator_name, params)

        except Exception as e:
            print(f"计算指标 {indicator_name} 失败: {str(e)}")
            # 尝试回退计算
            return self._calculate_indicator_fallback(data, indicator_name, params)

    def _calculate_indicator_fallback(self, data: pd.DataFrame, indicator_name: str,
                                      params: Dict[str, Any]) -> Optional[Any]:
        """简单回退计算方法

        Args:
            data: K线数据
            indicator_name: 指标名称
            params: 指标参数

        Returns:
            指标计算结果
        """
        try:
            indicator_lower = indicator_name.lower()

            if indicator_lower in ['ma', 'sma']:
                period = params.get('period', 20)
                return data['close'].rolling(window=period).mean()

            elif indicator_lower == 'ema':
                period = params.get('period', 20)
                return data['close'].ewm(span=period).mean()

            elif indicator_lower == 'rsi':
                period = params.get('period', 14)
                delta = data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                return 100 - (100 / (1 + rs))

            else:
                print(f"回退计算不支持指标: {indicator_name}")
                return None

        except Exception as e:
            print(f"回退计算指标 {indicator_name} 失败: {str(e)}")
            return None

    def process_batch_data(self, stock_data_list: List[Dict[str, Any]],
                           indicators: List[str]):
        """批量处理股票数据

        Args:
            stock_data_list: 股票数据列表
            indicators: 指标列表
        """
        try:
            if self.is_processing:
                self.error_occurred.emit("正在处理中，请稍候...")
                return

            self.is_processing = True
            self.should_stop = False

            results = {}
            total_stocks = len(stock_data_list)

            for i, stock_data in enumerate(stock_data_list):
                if self.should_stop:
                    break

                try:
                    # 更新进度
                    progress = int((i / total_stocks) * 100)
                    self.progress_updated.emit(progress)

                    stock_code = stock_data.get('code', f'stock_{i}')
                    kdata = stock_data.get('data')

                    if kdata is None or kdata.empty:
                        continue

                    # 计算所有指标
                    stock_results = {}
                    for indicator in indicators:
                        try:
                            result = self._calculate_single_indicator(kdata, indicator, {})
                            if result is not None:
                                stock_results[indicator] = result
                        except Exception as e:
                            print(f"股票 {stock_code} 计算指标 {indicator} 失败: {str(e)}")
                            continue

                    if stock_results:
                        results[stock_code] = stock_results

                except Exception as e:
                    print(f"处理股票数据失败: {str(e)}")
                    continue

            # 处理完成
            self.progress_updated.emit(100)
            self.data_processed.emit(results)

        except Exception as e:
            error_msg = f"批量处理失败: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            self.error_occurred.emit(error_msg)
        finally:
            self.is_processing = False

    def stop_processing(self):
        """停止处理"""
        self.should_stop = True

    def is_busy(self) -> bool:
        """检查是否正在处理

        Returns:
            是否正在处理
        """
        return self.is_processing


class DataProcessorThread(QThread):
    """数据处理线程"""

    # 信号定义
    data_processed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, parent=None):
        """初始化数据处理线程

        Args:
            parent: 父对象
        """
        super().__init__(parent)

        # 创建异步数据处理器
        self.processor = AsyncDataProcessor()

        # 连接信号
        self.processor.data_processed.connect(self.data_processed)
        self.processor.error_occurred.connect(self.error_occurred)
        self.processor.progress_updated.connect(self.progress_updated)

        # 任务队列
        self.task_queue = []
        self.current_task = None

    def add_indicator_task(self, data: pd.DataFrame, indicators: List[Dict[str, Any]]):
        """添加指标计算任务

        Args:
            data: K线数据
            indicators: 指标配置列表
        """
        task = {
            'type': 'indicators',
            'data': data,
            'indicators': indicators
        }
        self.task_queue.append(task)

        if not self.isRunning():
            self.start()

    def add_batch_task(self, stock_data_list: List[Dict[str, Any]], indicators: List[str]):
        """添加批量处理任务

        Args:
            stock_data_list: 股票数据列表
            indicators: 指标列表
        """
        task = {
            'type': 'batch',
            'stock_data_list': stock_data_list,
            'indicators': indicators
        }
        self.task_queue.append(task)

        if not self.isRunning():
            self.start()

    def run(self):
        """运行线程"""
        try:
            while self.task_queue:
                self.current_task = self.task_queue.pop(0)

                if self.current_task['type'] == 'indicators':
                    self.processor.process_indicators(
                        self.current_task['data'],
                        self.current_task['indicators']
                    )
                elif self.current_task['type'] == 'batch':
                    self.processor.process_batch_data(
                        self.current_task['stock_data_list'],
                        self.current_task['indicators']
                    )

                # 等待处理完成
                while self.processor.is_busy():
                    self.msleep(100)  # 等待100毫秒

        except Exception as e:
            error_msg = f"数据处理线程运行失败: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def stop_processing(self):
        """停止处理"""
        if self.processor:
            self.processor.stop_processing()

        # 清空任务队列
        self.task_queue.clear()

        # 等待线程结束
        if self.isRunning():
            self.quit()
            self.wait(3000)  # 等待最多3秒


# 便捷函数
def create_async_processor(parent=None) -> AsyncDataProcessor:
    """创建异步数据处理器

    Args:
        parent: 父对象

    Returns:
        AsyncDataProcessor实例
    """
    return AsyncDataProcessor(parent)


def create_processor_thread(parent=None) -> DataProcessorThread:
    """创建数据处理线程

    Args:
        parent: 父对象

    Returns:
        DataProcessorThread实例
    """
    return DataProcessorThread(parent)


# 向后兼容的别名
def get_async_processor(parent=None) -> AsyncDataProcessor:
    """获取异步数据处理器（向后兼容）"""
    return create_async_processor(parent)


def get_processor_thread(parent=None) -> DataProcessorThread:
    """获取数据处理线程（向后兼容）"""
    return create_processor_thread(parent)
