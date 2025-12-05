"""
数据标准化器 - 统一数据格式转换
提供统一的数据格式处理，确保所有组件都能处理标准化的pandas DataFrame
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union, List
from loguru import logger


class DataStandardizer:
    """数据标准化器
    
    功能：
    1. 验证和标准化DataFrame格式
    2. 转换为numpy数组供TA-Lib使用
    3. 处理缺失值和数据清洗
    4. 统一时间序列索引
    """
    
    # 标准列名定义
    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'volume']
    STANDARD_COLUMNS = ['open', 'high', 'low', 'close', 'volume', 'amount']
    
    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        """验证并标准化DataFrame格式
        
        Args:
            df: 输入的DataFrame
            
        Returns:
            标准化后的DataFrame
            
        Raises:
            ValueError: 如果数据格式不正确
        """
        if df is None or df.empty:
            raise ValueError("输入DataFrame为空")
            
        # 确保列名存在且为小写
        df = cls._standardize_columns(df)
        
        # 验证必要列
        missing_columns = set(cls.REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            raise ValueError(f"缺少必要列: {missing_columns}")
            
        # 数据类型转换和验证
        df = cls._convert_data_types(df)
        
        # 数据清洗
        df = cls._clean_data(df)
        
        # 时间索引标准化
        df = cls._standardize_index(df)
        
        # 数据验证
        cls._validate_data_integrity(df)
        
        return df
    
    @classmethod
    def to_numpy_arrays(cls, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """转换为numpy数组供TA-Lib使用
        
        Args:
            df: 标准化的DataFrame
            
        Returns:
            包含各列数据的numpy数组字典
        """
        if not isinstance(df, pd.DataFrame):
            raise ValueError("输入必须是pandas DataFrame")
            
        # 确保数据是numpy数组格式
        arrays = {}
        for col in cls.REQUIRED_COLUMNS:
            if col in df.columns:
                arrays[col] = df[col].values.astype(np.float64)
            else:
                logger.warning(f"列 {col} 不存在，使用零数组")
                arrays[col] = np.zeros(len(df))
                
        return arrays
    
    @classmethod
    def to_ohlcv_dict(cls, df: pd.DataFrame) -> Dict[str, List]:
        """转换为OHLCV格式
        
        Args:
            df: 标准化的DataFrame
            
        Returns:
            包含OHLCV数据的字典
        """
        arrays = cls.to_numpy_arrays(df)
        return {
            'open': arrays['open'].tolist(),
            'high': arrays['high'].tolist(),
            'low': arrays['low'].tolist(),
            'close': arrays['close'].tolist(),
            'volume': arrays['volume'].tolist(),
            'timestamps': df.index.tolist()
        }
    
    @classmethod
    def from_kdata_to_dataframe(cls, kdata: Any) -> pd.DataFrame:
        """统一数据格式转换
        Args:
            data: 原始数据对象（支持多种格式）
            
        Returns:
            标准化的DataFrame
        """
        try:
            # 检查是否是KData对象
            if hasattr(kdata, 'to_df') and callable(kdata.to_df):
                df = kdata.to_df()
            elif hasattr(kdata, '__len__') and len(kdata) > 0:
                # 手动转换KData
                data = []
                for k in kdata:
                    if hasattr(k, 'datetime') and hasattr(k, 'open'):
                        data.append({
                            'datetime': k.datetime,
                            'open': float(k.open),
                            'high': float(k.high),
                            'low': float(k.low),
                            'close': float(k.close),
                            'volume': float(k.volume) if hasattr(k, 'volume') else 0,
                            'amount': float(k.amount) if hasattr(k, 'amount') else 0
                        })
                df = pd.DataFrame(data)
                df.set_index('datetime', inplace=True)
            else:
                raise ValueError("不支持的KData格式")
                
            return cls.validate_dataframe(df)
            
        except Exception as e:
            logger.error(f"KData转换失败: {e}")
            raise ValueError(f"无法转换KData为DataFrame: {e}")
    
    @classmethod
    def _standardize_columns(cls, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        # 转换为小写
        df = df.copy()
        df.columns = [col.lower() for col in df.columns]
        
        # 列名映射
        column_mapping = {
            'o': 'open',
            'h': 'high', 
            'l': 'low',
            'c': 'close',
            'v': 'volume',
            'vol': 'volume',
            'amt': 'amount',
            'datetime': 'datetime',
            'date': 'datetime',
            'time': 'datetime'
        }
        
        # 重命名列
        df.rename(columns=column_mapping, inplace=True)
        
        return df
    
    @classmethod
    def _convert_data_types(cls, df: pd.DataFrame) -> pd.DataFrame:
        """转换数据类型"""
        df = df.copy()
        
        # 数值列转换
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        return df
    
    @classmethod
    def _clean_data(cls, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        df = df.copy()
        
        # 处理缺失值
        df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
        
        # 确保价格逻辑正确 (low <= open,close <= high)
        valid_rows = (
            (df['low'] <= df['open']) &
            (df['low'] <= df['close']) &
            (df['high'] >= df['open']) &
            (df['high'] >= df['close']) &
            (df['volume'] >= 0)
        )
        
        df = df[valid_rows]
        
        # 移除异常值（超过3倍标准差）
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns and len(df) > 1:
                mean_val = df[col].mean()
                std_val = df[col].std()
                if std_val > 0:
                    df = df[abs(df[col] - mean_val) <= 3 * std_val]
        
        return df
    
    @classmethod
    def _standardize_index(cls, df: pd.DataFrame) -> pd.DataFrame:
        """标准化时间索引"""
        df = df.copy()
        
        # 如果没有datetime列，创建一个
        if 'datetime' not in df.columns:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
        else:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            
        # 确保索引是时间类型并排序
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        # 去除重复时间
        df = df[~df.index.duplicated(keep='first')]
        
        return df
    
    @classmethod
    def _validate_data_integrity(cls, df: pd.DataFrame):
        """验证数据完整性"""
        if len(df) == 0:
            raise ValueError("数据为空")
            
        # 检查时间序列连续性（可选）
        if len(df) > 1:
            time_diff = df.index.to_series().diff().dropna()
            if time_diff.std() > time_diff.mean() * 2:
                logger.warning("时间序列可能不连续")
                
        # 检查价格异常
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                if (df[col] <= 0).any():
                    logger.warning(f"发现非正价格数据在列 {col}")
                    
        # 检查成交量异常
        if 'volume' in df.columns:
            if (df['volume'] < 0).any():
                logger.warning("发现负成交量数据")


class IndicatorDataPreparer:
    """指标数据准备器
    
    为技术指标计算准备标准化数据
    """
    
    @staticmethod
    def prepare_talib_inputs(df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """准备TA-Lib输入数据"""
        arrays = DataStandardizer.to_numpy_arrays(df)
        
        # 确保数据类型正确
        for key, value in arrays.items():
            arrays[key] = np.array(value, dtype=np.float64)
            
        return arrays
    
    @staticmethod
    def prepare_indicator_series(df: pd.DataFrame, indicators: List[str]) -> Dict[str, np.ndarray]:
        """准备指标计算所需的序列"""
        arrays = IndicatorDataPreparer.prepare_talib_inputs(df)
        prepared = {}
        
        for indicator in indicators:
            if indicator.lower() in ['close', 'c']:
                prepared[indicator] = arrays['close']
            elif indicator.lower() in ['open', 'o']:
                prepared[indicator] = arrays['open']
            elif indicator.lower() in ['high', 'h']:
                prepared[indicator] = arrays['high']
            elif indicator.lower() in ['low', 'l']:
                prepared[indicator] = arrays['low']
            elif indicator.lower() in ['volume', 'v', 'vol']:
                prepared[indicator] = arrays['volume']
            else:
                logger.warning(f"未知指标类型: {indicator}")
                prepared[indicator] = arrays['close']  # 默认使用收盘价
                
        return prepared


class DataValidationError(Exception):
    """数据验证错误"""
    pass


# 便利函数
def validate_and_prepare_data(data: Union[pd.DataFrame, Any]) -> pd.DataFrame:
    """便利函数：验证并准备数据
    
    Args:
        data: 输入数据（DataFrame或KData）
        
    Returns:
        标准化的DataFrame
    """
    if isinstance(data, pd.DataFrame):
        return DataStandardizer.validate_dataframe(data)
    else:
        return DataStandardizer.from_kdata_to_dataframe(data)


def prepare_for_talib(data: Union[pd.DataFrame, Any]) -> Dict[str, np.ndarray]:
    """便利函数：为TA-Lib准备数据
    
    Args:
        data: 输入数据
        
    Returns:
        TA-Lib格式的numpy数组
    """
    df = validate_and_prepare_data(data)
    return IndicatorDataPreparer.prepare_talib_inputs(df)


# 测试代码
if __name__ == "__main__":
    # 创建测试数据
    test_data = pd.DataFrame({
        'Open': [10.0, 11.0, 10.5, 11.5],
        'High': [10.5, 11.5, 11.0, 12.0],
        'Low': [9.5, 10.5, 10.0, 11.0],
        'Close': [10.2, 11.2, 10.8, 11.6],
        'Volume': [1000, 1200, 800, 1500]
    })
    
    # 测试标准化
    try:
        validated_data = DataStandardizer.validate_dataframe(test_data)
        print("数据标准化成功:")
        print(validated_data.head())
        
        # 测试转换为numpy数组
        arrays = DataStandardizer.to_numpy_arrays(validated_data)
        print("\n转换的numpy数组:")
        for key, value in arrays.items():
            print(f"{key}: {value[:3]}...")  # 显示前3个值
            
        # 测试TA-Lib输入准备
        talib_inputs = IndicatorDataPreparer.prepare_talib_inputs(validated_data)
        print("\nTA-Lib输入准备完成")
        
    except Exception as e:
        print(f"测试失败: {e}")