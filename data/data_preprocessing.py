import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, RobustScaler
from collections import Counter
from scipy import stats
import warnings


def optimize_data_quality(df):
    """
    优化数据质量，处理缺失值和异常值

    参数:
        df: 输入DataFrame

    返回:
        DataFrame: 处理后的DataFrame
    """
    # 复制DataFrame以避免修改原始数据
    df_clean = df.copy()

    # 处理缺失值
    # 对于时间序列数据，通常使用前向填充
    df_clean = df_clean.fillna(method='ffill')

    # 对于仍然存在的缺失值，使用均值填充
    df_clean = df_clean.fillna(df_clean.mean())

    # 对剩余的NaN（如果数据列全为NaN）用0填充
    df_clean = df_clean.fillna(0)

    # 处理异常值
    for col in df_clean.select_dtypes(include=[np.number]).columns:
        if col not in ['open', 'high', 'low', 'close', 'volume']:  # 不处理原始价格数据
            df_clean[col] = detect_and_handle_outliers(df_clean[col])

    return df_clean


def detect_and_handle_outliers(series, n_sigmas=3.0):
    """
    检测并处理异常值

    参数:
        series: 数据Series
        n_sigmas: 标准差倍数阈值

    返回:
        Series: 处理后的Series
    """
    # 计算均值和标准差
    mean = series.mean()
    std = series.std()

    # 定义上下界
    lower_bound = mean - n_sigmas * std
    upper_bound = mean + n_sigmas * std

    # 替换异常值为边界值
    series_clean = series.copy()
    series_clean.loc[series < lower_bound] = lower_bound
    series_clean.loc[series > upper_bound] = upper_bound

    return series_clean


def reduce_noise_with_filtering(df, columns=None, window=5, method='ewm'):
    """
    使用滑动窗口或指数加权移动平均减少噪声

    参数:
        df: 输入DataFrame
        columns: 要处理的列名列表，None表示处理所有数值列
        window: 滑动窗口大小
        method: 滤波方法 ('sma', 'ewm', 'kalman')

    返回:
        DataFrame: 处理后的DataFrame
    """
    # 复制DataFrame以避免修改原始数据
    df_filtered = df.copy()

    # 如果未指定列，则选择所有数值列但排除OHLCV数据
    if columns is None:
        columns = [col for col in df.select_dtypes(include=[np.number]).columns
                   if col not in ['open', 'high', 'low', 'close', 'volume', 'target']]

    # 应用相应的滤波方法
    for col in columns:
        if method == 'sma':  # 简单移动平均
            df_filtered[col] = df[col].rolling(window=window, center=False).mean()
        elif method == 'ewm':  # 指数加权移动平均
            df_filtered[col] = df[col].ewm(span=window, adjust=False).mean()
        elif method == 'kalman':  # 简化的卡尔曼滤波
            df_filtered[col] = simple_kalman_filter(df[col])

    # 对滤波后产生的缺失值进行处理
    df_filtered = df_filtered.fillna(method='bfill')
    df_filtered = df_filtered.fillna(method='ffill')

    return df_filtered


def simple_kalman_filter(series, q=0.01, r=0.1):
    """
    简单的卡尔曼滤波实现

    参数:
        series: 输入数据Series
        q: 过程噪声协方差
        r: 测量噪声协方差

    返回:
        Series: 滤波后的Series
    """
    # 初始化
    n = len(series)
    filtered = np.zeros(n)
    prediction = series.iloc[0]  # 初始预测值
    error_estimate = 1.0  # 初始误差估计

    # 卡尔曼滤波
    for i in range(n):
        # 预测更新
        kalman_gain = error_estimate / (error_estimate + r)
        # 状态更新
        prediction = prediction + kalman_gain * (series.iloc[i] - prediction)
        # 误差更新
        error_estimate = (1 - kalman_gain) * error_estimate + q
        # 保存结果
        filtered[i] = prediction

    return pd.Series(filtered, index=series.index)


def prepare_features_and_labels(df, future_period=5, threshold=0.015):
    """
    准备特征和标签，保留最新数据点

    参数:
        df: 输入DataFrame
        future_period: 未来预测的天数
        threshold: 信号阈值

    返回:
        DataFrame, list: 处理后的DataFrame和特征列表
    """
    # 创建未来收益率
    df['future_return'] = df['close'].shift(-future_period) / df['close'] - 1

    # 定义标签生成函数
    def create_target(x):
        if pd.isna(x):
            return np.nan  # 保留NaN值
        if x > threshold:
            return 1  # 买入信号
        elif x < -threshold:
            return -1  # 卖出信号
        else:
            return 0  # 持有信号

    # 生成目标标签
    df['target'] = df['future_return'].apply(create_target)

    # 创建一个副本保存未处理过的完整数据
    df_complete = df.copy()

    # 对最近的future_period天的数据特殊处理
    latest_dates = df.index[-future_period:]

    # 对最新数据，我们将NaN标签设为0（持有信号）
    if len(latest_dates) > 0:
        df.loc[latest_dates, 'target'] = df.loc[latest_dates, 'target'].fillna(0)

    # 对于预测特征中的NaN值，使用前向填充处理
    df = df.fillna(method='ffill')

    # 对剩余的NaN值使用均值填充
    df = df.fillna(df.mean())

    # 选择特征列，排除标签和原始价格数据
    feature_columns = [col for col in df.columns if col not in ['target', 'future_return', 'date', 'open', 'high', 'low', 'close', 'volume']]

    # 增加一个标记，指示哪些行是最新的数据点（可能没有实际标签）
    df['is_latest'] = False
    if len(latest_dates) > 0:
        df.loc[latest_dates, 'is_latest'] = True

    return df, feature_columns


def preprocess_data(df):
    """
    预处理数据

    参数:
        df: 输入DataFrame

    返回:
        DataFrame: 处理后的DataFrame
    """
    if df.empty:
        return df

    # 创建副本
    result = df.copy()

    # 确保列名小写
    result.columns = [col.lower() for col in result.columns]

    # 基本检查
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in result.columns]
    if missing_cols:
        warnings.warn(f"数据缺少以下列: {missing_cols}")

    # 确保索引是日期类型
    if not isinstance(result.index, pd.DatetimeIndex):
        if 'datetime' in result.columns:
            result['datetime'] = pd.to_datetime(result['datetime'])
            result = result.set_index('datetime')
        elif 'date' in result.columns:
            result['date'] = pd.to_datetime(result['date'])
            result = result.set_index('date')
        else:
            try:
                # 尝试将当前索引转换为日期类型
                result.index = pd.to_datetime(result.index)
            except:
                warnings.warn("无法将索引转换为日期类型")

    # 排序索引
    result = result.sort_index()

    # 确保数据类型
    for col in ['open', 'high', 'low', 'close']:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors='coerce')

    if 'volume' in result.columns:
        result['volume'] = pd.to_numeric(result['volume'], errors='coerce')
        # 确保交易量非负
        result['volume'] = result['volume'].abs()

    # 检查数据一致性
    for i, row in result.iterrows():
        if 'open' in result.columns and 'high' in result.columns and 'low' in result.columns and 'close' in result.columns:
            # 确保high >= low
            if row['high'] < row['low']:
                result.loc[i, 'high'], result.loc[i, 'low'] = row['low'], row['high']

            # 确保high >= open, close
            result.loc[i, 'high'] = max(row['high'], row['open'], row['close'])

            # 确保low <= open, close
            result.loc[i, 'low'] = min(row['low'], row['open'], row['close'])

    # 添加基本计算列
    if 'high' in result.columns and 'low' in result.columns:
        # 计算价格范围
        result['range'] = result['high'] - result['low']

    if 'close' in result.columns:
        # 计算每日收益率
        result['returns'] = result['close'].pct_change()

        # 计算对数收益率
        result['log_returns'] = np.log(result['close'] / result['close'].shift(1))

    if 'volume' in result.columns and 'close' in result.columns:
        # 计算成交额
        result['volume_price'] = result['volume'] * result['close']

    # 异常值检测和处理
    for col in ['returns', 'log_returns']:
        if col in result.columns:
            # Z-score方法检测异常值
            z_scores = stats.zscore(result[col].dropna())
            abs_z_scores = np.abs(z_scores)
            filtered_entries = (abs_z_scores < 3)  # Z-score < 3 认为是正常值
            outliers_indices = result[col].dropna()[~filtered_entries].index

            if len(outliers_indices) > 0:
                warnings.warn(f"检测到 {col} 列中有 {len(outliers_indices)} 个异常值")
                # 使用前后值的平均值替代异常值
                for idx in outliers_indices:
                    idx_pos = result.index.get_loc(idx)
                    if idx_pos > 0 and idx_pos < len(result) - 1:
                        # 使用前后值的平均值
                        prev_val = result[col].iloc[idx_pos - 1]
                        next_val = result[col].iloc[idx_pos + 1]
                        if not pd.isna(prev_val) and not pd.isna(next_val):
                            result.loc[idx, col] = (prev_val + next_val) / 2

    # 如果有调整收盘价，计算调整后的开高低价
    if 'adj_close' in result.columns and 'close' in result.columns:
        # 计算调整因子
        result['adj_factor'] = result['adj_close'] / result['close']

        # 调整其他价格
        for col in ['open', 'high', 'low']:
            if col in result.columns:
                result[f'adj_{col}'] = result[col] * result['adj_factor']

    return result


def create_features_targets(df, target_type='regression', lookahead_periods=5, threshold=0.01):
    """
    创建特征和目标变量

    参数:
        df: 输入DataFrame
        target_type: 目标类型，'regression'或'classification'
        lookahead_periods: 未来预测的周期数
        threshold: 分类目标的阈值

    返回:
        (DataFrame, Series): 特征DataFrame和目标Series
    """
    if df.empty:
        return pd.DataFrame(), pd.Series()

    # 创建特征DataFrame
    features = df.copy()

    # 从features中排除不应该用作特征的列
    cols_to_exclude = ['returns', 'log_returns', 'target', 'signal', 'position']
    feature_cols = [col for col in features.columns if col not in cols_to_exclude]
    features = features[feature_cols]

    # 创建目标变量
    if 'close' in df.columns:
        # 未来收益率
        future_returns = df['close'].pct_change(lookahead_periods).shift(-lookahead_periods)

        if target_type == 'regression':
            # 回归目标 - 直接使用未来收益率
            target = future_returns
        else:
            # 分类目标 - 基于阈值创建三分类目标
            target = pd.Series(0, index=df.index)  # 默认为持有(0)
            target[future_returns > threshold] = 1  # 上涨超过阈值，买入(1)
            target[future_returns < -threshold] = -1  # 下跌超过阈值，卖出(-1)
    else:
        raise ValueError("DataFrame必须包含'close'列")

    # 删除包含NaN的行
    valid_indices = ~(features.isnull().any(axis=1) | target.isnull())
    features = features[valid_indices]
    target = target[valid_indices]

    return features, target


def balance_samples(X, y):
    """
    平衡样本集，处理类别不平衡问题

    参数:
        X: 特征数据
        y: 标签数据

    返回:
        X_resampled, y_resampled: 重采样后的数据
    """
    try:
        # 检查数据
        if len(X) != len(y):
            raise ValueError("特征和标签长度不匹配")

        # 查看标签分布
        class_counts = Counter(y)
        print("原始类别分布:")
        for label, count in class_counts.items():
            print(f"类别 {label}: {count} 样本")

        # 获取最小类别的样本数
        min_samples = min(class_counts.values())

        # 转换为numpy数组便于处理
        X_array = np.array(X)
        y_array = np.array(y)

        # 保存原始索引（如果有）
        original_index = None
        if hasattr(X, 'index'):
            original_index = X.index

        # 分割不同类别的样本
        X_by_class = {}
        y_by_class = {}
        for label in class_counts.keys():
            mask = (y_array == label)
            X_by_class[label] = X_array[mask]
            y_by_class[label] = y_array[mask]

        # 使用时间序列友好的采样方法
        # 将数据分成多个窗口进行采样，保持时间序列特性
        window_size = min(100, min_samples)  # 窗口大小
        n_windows = max(5, X_array.shape[0] // window_size)  # 窗口数量

        # 用于存储重采样结果
        X_resampled_parts = []
        y_resampled_parts = []

        # 在每个窗口内进行采样
        for i in range(n_windows):
            start_idx = i * window_size
            end_idx = min((i + 1) * window_size, X_array.shape[0])

            # 当前窗口的数据
            X_window = X_array[start_idx:end_idx]
            y_window = y_array[start_idx:end_idx]

            # 统计当前窗口内的类别分布
            window_counts = Counter(y_window)

            # 为每个类别收集样本
            X_samples = []
            y_samples = []

            # 对窗口内的每个类别进行均衡
            window_min = min(window_counts.values()) if window_counts else 0
            for label in class_counts.keys():
                if label in window_counts and window_counts[label] > 0:
                    # 获取当前窗口内该类别的索引
                    indices = np.where(y_window == label)[0]

                    # 如果样本数量少于需要的数量，则重复采样
                    if len(indices) < window_min:
                        indices = np.random.choice(indices, window_min, replace=True)
                    # 如果样本数量多于需要的数量，则随机选择
                    elif len(indices) > window_min:
                        indices = np.random.choice(indices, window_min, replace=False)

                    # 收集样本
                    X_samples.append(X_window[indices])
                    y_samples.append(np.full(len(indices), label))

            # 合并当前窗口的均衡样本
            if X_samples and y_samples:
                X_clean = np.vstack(X_samples)
                y_clean = np.concatenate(y_samples)
            else:
                # 如果窗口内没有样本，跳过
                continue

            X_resampled_parts.append(X_clean)
            y_resampled_parts.append(y_clean)

        # 合并所有窗口的结果
        X_resampled = np.vstack(X_resampled_parts)
        y_resampled = np.concatenate(y_resampled_parts)

        # 恢复时序特性
        if original_index is not None:
            # 创建新的时间索引
            new_index = pd.date_range(
                start=original_index[0],
                periods=len(X_resampled),
                freq=pd.infer_freq(original_index)
            )
            X_resampled = pd.DataFrame(X_resampled, index=new_index)

        # 评估采样结果
        resampled_counts = Counter(y_resampled)
        print("\n重采样后的分布:")
        for label, count in resampled_counts.items():
            print(f"类别 {label}: {count} 样本")

        # 计算采样质量指标
        original_dist = np.array([count for count in class_counts.values()])
        resampled_dist = np.array([count for count in resampled_counts.values()])

        # 分布均衡度
        original_entropy = -np.sum((original_dist/sum(original_dist)) * np.log2(original_dist/sum(original_dist)))
        resampled_entropy = -np.sum((resampled_dist/sum(resampled_dist)) * np.log2(resampled_dist/sum(resampled_dist)))

        print("\n采样质量评估:")
        print(f"原始分布熵: {original_entropy:.4f}")
        print(f"重采样分布熵: {resampled_entropy:.4f}")
        print(f"分布改善: {((resampled_entropy - original_entropy) / original_entropy) * 100:.3f}%")

        return X_resampled, y_resampled

    except Exception as e:
        print(f"重采样过程出错: {e}")
        # 发生错误时返回原始数据
        return X, y
