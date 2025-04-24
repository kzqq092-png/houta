"""
Data Loader Module

This module provides functionality for loading and managing data.
"""

import numpy as np
import pandas as pd
import logging
from typing import Optional, Dict, Any, List
from functools import lru_cache
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..utils.cache import DataCache

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class DataValidationResult:
    """数据验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class DataLoadError(Exception):
    """数据加载错误"""
    pass

# 创建全局缓存实例
data_cache = DataCache(
    max_memory_size=1000,
    cache_dir=".cache/data",
    expire_minutes=30,
    cleanup_interval=5
)

def retry_on_failure(max_retries: int = 3, delay_seconds: int = 1):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"函数 {func.__name__} 执行失败: {str(e)}")
                        raise
                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败，将重试")
                    time.sleep(delay_seconds * (attempt + 1))
            return None
        return wrapper
    return decorator

@retry_on_failure(max_retries=3)
def fetch_fundamental_data(stock, use_cache: bool = True) -> pd.DataFrame:
    """
    获取基本面数据
    
    参数:
        stock: 股票对象
        use_cache: 是否使用缓存
    
    返回:
        DataFrame: 包含基本面数据的DataFrame
    """
    try:
        # 检查缓存
        cache_key = f"fundamental_{stock.code}"
        if use_cache:
            cached_data = data_cache.get(cache_key)
            if cached_data is not None:
                return cached_data
        
        # 获取数据
        df = create_simulated_fundamental_data()
        
        # 验证数据
        validation = validate_fundamental_data(df)
        if not validation.is_valid:
            raise DataLoadError(f"基本面数据验证失败: {validation.errors}")
            
        # 处理异常值
        df = handle_outliers(df)
        
        # 缓存数据
        if use_cache:
            data_cache.set(cache_key, df)
        
        return df
        
    except Exception as e:
        logger.error(f"获取基本面数据失败: {str(e)}")
        raise DataLoadError(f"获取基本面数据失败: {str(e)}")

def validate_fundamental_data(df: pd.DataFrame) -> DataValidationResult:
    """验证基本面数据"""
    errors = []
    warnings = []
    
    # 检查必需的列
    required_columns = ['revenue', 'net_income', 'assets', 'liabilities']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"缺少必需的列: {', '.join(missing_columns)}")
    
    # 检查数据类型
    for col in df.columns:
        if not np.issubdtype(df[col].dtype, np.number):
            errors.append(f"列 {col} 不是数值类型")
    
    # 检查空值
    null_cols = df.columns[df.isnull().any()].tolist()
    if null_cols:
        warnings.append(f"以下列包含空值: {', '.join(null_cols)}")
    
    # 检查负值
    for col in ['revenue', 'assets']:
        if (df[col] < 0).any():
            errors.append(f"列 {col} 包含负值")
    
    return DataValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def handle_outliers(df: pd.DataFrame, method: str = 'zscore', threshold: float = 3.0) -> pd.DataFrame:
    """
    处理异常值
    
    参数:
        df: 输入数据
        method: 异常值检测方法 ('zscore' 或 'iqr')
        threshold: 异常值阈值
    """
    df_clean = df.copy()
    
    for col in df.select_dtypes(include=[np.number]).columns:
        if method == 'zscore':
            # Z-score方法
            z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
            mask = z_scores > threshold
        else:
            # IQR方法
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            mask = (df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))
        
        if mask.any():
            logger.warning(f"列 {col} 发现 {mask.sum()} 个异常值")
            # 使用中位数替换异常值
            df_clean.loc[mask, col] = df[col].median()
    
    return df_clean

@retry_on_failure(max_retries=3)
def fetch_macroeconomic_data(use_cache: bool = True) -> pd.DataFrame:
    """获取宏观经济数据"""
    try:
        # 检查缓存
        cache_key = "macroeconomic"
        if use_cache:
            cached_data = data_cache.get(cache_key)
            if cached_data is not None:
                return cached_data
        
        # 获取数据
        df = create_simulated_macroeconomic_data()
        
        # 验证数据
        validation = validate_macroeconomic_data(df)
        if not validation.is_valid:
            raise DataLoadError(f"宏观经济数据验证失败: {validation.errors}")
        
        # 处理异常值
        df = handle_outliers(df)
        
        # 缓存数据
        if use_cache:
            data_cache.set(cache_key, df)
        
        return df
        
    except Exception as e:
        logger.error(f"获取宏观经济数据失败: {str(e)}")
        raise DataLoadError(f"获取宏观经济数据失败: {str(e)}")

def validate_macroeconomic_data(df: pd.DataFrame) -> DataValidationResult:
    """验证宏观经济数据"""
    errors = []
    warnings = []
    
    # 检查必需的列
    required_columns = ['gdp_growth', 'inflation', 'unemployment', 'interest_rate']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"缺少必需的列: {', '.join(missing_columns)}")
    
    # 检查数据类型
    for col in df.columns:
        if not np.issubdtype(df[col].dtype, np.number):
            errors.append(f"列 {col} 不是数值类型")
    
    # 检查数据范围
    if 'inflation' in df.columns and ((df['inflation'] < -10) | (df['inflation'] > 30)).any():
        warnings.append("通货膨胀率超出正常范围")
    
    if 'unemployment' in df.columns and ((df['unemployment'] < 0) | (df['unemployment'] > 50)).any():
        warnings.append("失业率超出正常范围")
    
    return DataValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def integrate_multiple_data_sources(df_kdata: pd.DataFrame, 
                                  fundamental_data: pd.DataFrame,
                                  macroeconomic_data: pd.DataFrame,
                                  sentiment_data: Optional[pd.DataFrame] = None,
                                  chunk_size: int = 1000) -> pd.DataFrame:
    """
    整合多源数据
    
    参数:
        df_kdata: K线数据
        fundamental_data: 基本面数据
        macroeconomic_data: 宏观经济数据
        sentiment_data: 市场情绪数据
        chunk_size: 数据分块大小
    """
    try:
        # 验证输入数据
        if df_kdata.empty:
            raise ValueError("K线数据为空")
            
        # 确保索引为日期类型
        if not isinstance(df_kdata.index, pd.DatetimeIndex):
            if 'date' in df_kdata.columns:
                df_kdata = df_kdata.set_index('date')
            else:
                raise ValueError("K线数据缺少日期索引")
        
        # 使用线程池处理数据对齐
        with ThreadPoolExecutor() as executor:
            # 提交数据对齐任务
            fundamental_future = executor.submit(
                align_and_process_data, fundamental_data, 'Q', 'ffill')
            macro_future = executor.submit(
                align_and_process_data, macroeconomic_data, 'M', 'ffill')
            sentiment_future = executor.submit(
                align_and_process_data, sentiment_data, 'D', 'ffill')
            
            # 获取结果
            aligned_fundamental = fundamental_future.result()
            aligned_macro = macro_future.result()
            aligned_sentiment = sentiment_future.result()
        
        # 分块处理数据合并
        result_chunks = []
        for i in range(0, len(df_kdata), chunk_size):
            chunk = df_kdata.iloc[i:i+chunk_size].copy()
            
            # 合并基本面数据
            if aligned_fundamental is not None:
                chunk = merge_chunk_data(chunk, aligned_fundamental, 'fund_')
            
            # 合并宏观数据
            if aligned_macro is not None:
                chunk = merge_chunk_data(chunk, aligned_macro, 'macro_')
            
            # 合并情绪数据
            if aligned_sentiment is not None:
                chunk = merge_chunk_data(chunk, aligned_sentiment, 'sent_')
            
            result_chunks.append(chunk)
        
        # 合并所有分块
        result_df = pd.concat(result_chunks)
        
        # 处理缺失值
        result_df = handle_missing_data(result_df)
        
        return result_df
        
    except Exception as e:
        logger.error(f"整合数据失败: {str(e)}")
        raise DataLoadError(f"整合数据失败: {str(e)}")

def merge_chunk_data(chunk: pd.DataFrame, data: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """合并数据块"""
    # 只保留chunk日期范围内的数据
    filtered_data = data.loc[data.index.isin(chunk.index)]
    
    # 添加前缀并合并
    filtered_data = filtered_data.add_prefix(prefix)
    return chunk.join(filtered_data, how='left')

def handle_missing_data(df: pd.DataFrame) -> pd.DataFrame:
    """处理缺失值"""
    # 记录缺失值情况
    missing_stats = df.isnull().sum()
    if missing_stats.any():
        logger.warning("发现缺失值:\n" + str(missing_stats[missing_stats > 0]))
    
    # 对不同类型的列使用不同的填充方法
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    
    # 对数值列使用前向填充和线性插值
    df[numeric_cols] = df[numeric_cols].fillna(method='ffill')
    df[numeric_cols] = df[numeric_cols].interpolate(method='linear')
    
    # 对分类列使用前向填充
    df[categorical_cols] = df[categorical_cols].fillna(method='ffill')
    
    # 最后的缺失值用0填充
    df = df.fillna(0)
    
    return df

@lru_cache(maxsize=100)
def load_stock_data(file_path: str) -> pd.DataFrame:
    """
    加载股票数据（使用缓存）
    
    参数:
        file_path: 数据文件路径
    """
    try:
        df = pd.read_csv(file_path, parse_dates=['date'], index_col='date')
        
        # 验证数据
        validation = validate_stock_data(df)
        if not validation.is_valid:
            raise DataLoadError(f"股票数据验证失败: {validation.errors}")
        
        # 处理异常值
        df = handle_outliers(df)
        
        return df
        
    except Exception as e:
        logger.error(f"加载股票数据失败: {str(e)}")
        raise DataLoadError(f"加载股票数据失败: {str(e)}")

def validate_stock_data(df: pd.DataFrame) -> DataValidationResult:
    """验证股票数据"""
    errors = []
    warnings = []
    
    # 检查必需的列
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"缺少必需的列: {', '.join(missing_columns)}")
    
    # 检查数据类型
    for col in required_columns:
        if col in df.columns and not np.issubdtype(df[col].dtype, np.number):
            errors.append(f"列 {col} 不是数值类型")
    
    # 检查数据有效性
    if 'close' in df.columns:
        if (df['close'] <= 0).any():
            errors.append("收盘价包含无效值")
    
    if 'volume' in df.columns:
        if (df['volume'] < 0).any():
            errors.append("成交量包含负值")
    
    # 检查OHLC关系
    if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        if (df['high'] < df['low']).any():
            errors.append("最高价小于最低价")
        if ((df['high'] < df['open']) | (df['high'] < df['close'])).any():
            errors.append("最高价小于开盘价或收盘价")
        if ((df['low'] > df['open']) | (df['low'] > df['close'])).any():
            errors.append("最低价大于开盘价或收盘价")
    
    return DataValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def create_simulated_fundamental_data():
    """
    创建模拟的基本面数据
    
    返回:
        DataFrame: 包含模拟基本面数据的DataFrame
    """
    # 创建日期范围
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='Q')
    
    # 创建基本财务指标
    np.random.seed(42)  # 固定随机种子以确保可重复性
    
    # 模拟财务数据
    data = {
        'revenue': np.random.normal(1000, 200, len(dates)) * (1 + np.arange(len(dates)) * 0.05),  # 收入逐渐增长
        'net_income': np.random.normal(100, 30, len(dates)) * (1 + np.arange(len(dates)) * 0.03),  # 净利润逐渐增长
        'assets': np.random.normal(5000, 500, len(dates)) * (1 + np.arange(len(dates)) * 0.02),   # 资产逐渐增长
        'liabilities': np.random.normal(2000, 300, len(dates)) * (1 + np.arange(len(dates)) * 0.01),  # 负债逐渐增长
        'operating_cash_flow': np.random.normal(120, 40, len(dates)) * (1 + np.arange(len(dates)) * 0.04),  # 经营现金流
    }
    
    # 创建DataFrame
    df = pd.DataFrame(data, index=dates)
    
    # 计算衍生指标
    df['equity'] = df['assets'] - df['liabilities']  # 权益
    df['roe'] = df['net_income'] / df['equity']  # 净资产收益率
    df['profit_margin'] = df['net_income'] / df['revenue']  # 利润率
    df['asset_turnover'] = df['revenue'] / df['assets']  # 资产周转率
    df['debt_to_equity'] = df['liabilities'] / df['equity']  # 负债权益比
    
    return df

def create_simulated_macroeconomic_data():
    """
    创建模拟的宏观经济数据
    
    返回:
        DataFrame: 包含模拟宏观经济数据的DataFrame
    """
    # 创建日期范围 - 每月数据
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='M')
    
    # 设置随机种子以确保可重复性
    np.random.seed(42)
    
    # 基础趋势 - 模拟经济周期
    t = np.arange(len(dates))
    cycle1 = 0.2 * np.sin(2 * np.pi * t / 24)  # 2年周期
    cycle2 = 0.1 * np.sin(2 * np.pi * t / 12)  # 1年周期
    trend = 0.02 * t / len(t)  # 微弱的长期上升趋势
    
    # 生成不同经济指标
    gdp_growth = 2.0 + trend * 3 + cycle1 + np.random.normal(0, 0.3, len(dates))
    inflation = 2.5 + cycle2 * 2 + np.random.normal(0, 0.2, len(dates))
    unemployment = 5.0 - trend + cycle1 * 0.5 + np.random.normal(0, 0.1, len(dates))
    interest_rate = 1.5 + cycle1 * 0.8 + cycle2 + np.random.normal(0, 0.05, len(dates))
    consumer_confidence = 100 + cycle1 * 10 + cycle2 * 5 + np.random.normal(0, 2, len(dates))
    
    # 调整合理范围
    unemployment = np.clip(unemployment, 3, 10)
    interest_rate = np.clip(interest_rate, 0, 5)
    inflation = np.clip(inflation, -1, 7)
    
    # 组织数据为DataFrame
    data = {
        'gdp_growth': gdp_growth,
        'inflation': inflation,
        'unemployment': unemployment,
        'interest_rate': interest_rate,
        'consumer_confidence': consumer_confidence,
    }
    
    df = pd.DataFrame(data, index=dates)
    
    # 添加一些衍生指标
    df['real_interest_rate'] = df['interest_rate'] - df['inflation']
    df['economic_health'] = df['gdp_growth'] - df['unemployment'] * 0.5
    
    return df

def align_and_process_data(data, freq='D', method='ffill'):
    """对数据进行对齐处理"""
    if data.empty:
        return None
    
    # 获取K线数据的时间范围
    start_date = df_kdata.index.min()
    end_date = df_kdata.index.max()
    
    # 创建完整的日期范围
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
    
    # 重新索引数据并填充缺失值
    reindexed_data = data.reindex(date_range, method=method)
    
    # 将数据重采样到日频率
    if freq != 'D':
        reindexed_data = reindexed_data.resample('D').asfreq()
        reindexed_data = reindexed_data.fillna(method=method)
    
    return reindexed_data 