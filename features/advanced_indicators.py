import pandas as pd
import numpy as np
from scipy import stats

def calculate_advanced_indicators(df):
    """
    计算高级技术指标
    
    参数:
        df: 输入DataFrame，包含OHLCV数据
    
    返回:
        DataFrame: 添加了高级技术指标的DataFrame
    """
    # MACD
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp12 - exp26
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal']
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    df['bb_std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # Stochastic Oscillator
    low_14 = df['low'].rolling(window=14).min()
    high_14 = df['high'].rolling(window=14).max()
    df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
    
    # Chaikin Money Flow
    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
    clv = clv.replace([np.inf, -np.inf], np.nan).fillna(0)
    df['cmf'] = (clv * df['volume']).rolling(window=20).sum() / df['volume'].rolling(window=20).sum()
    
    # OBV (On-Balance Volume)
    df['daily_ret'] = df['close'].pct_change()
    df['direction'] = np.where(df['daily_ret'] > 0, 1, np.where(df['daily_ret'] < 0, -1, 0))
    df['direction_volume'] = df['direction'] * df['volume']
    df['obv'] = df['direction_volume'].cumsum()
    
    # KDJ
    df['kdj_k'] = df['stoch_k']
    df['kdj_d'] = df['stoch_d']
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
    
    # Williams %R
    df['williams_r'] = -100 * (high_14 - df['close']) / (high_14 - low_14)
    
    # TRIX
    ex1 = df['close'].ewm(span=9, adjust=False).mean()
    ex2 = ex1.ewm(span=9, adjust=False).mean()
    ex3 = ex2.ewm(span=9, adjust=False).mean()
    df['trix'] = 100 * (ex3.pct_change(1))
    
    # CCI (Commodity Channel Index)
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    moving_avg = typical_price.rolling(window=20).mean()
    mean_deviation = np.abs(typical_price - moving_avg).rolling(window=20).mean()
    df['cci'] = (typical_price - moving_avg) / (0.015 * mean_deviation)
    
    # ROC (Rate of Change)
    df['roc'] = 100 * ((df['close'] / df['close'].shift(10)) - 1)
    
    # Awesome Oscillator
    median_price = (df['high'] + df['low']) / 2
    ao1 = median_price.rolling(window=5).mean()
    ao2 = median_price.rolling(window=34).mean()
    df['awesome_oscillator'] = ao1 - ao2
    
    # MFI (Money Flow Index)
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    raw_money_flow = typical_price * df['volume']
    
    # 计算Positive和Negative Money Flow
    money_flow_positive = raw_money_flow.where(typical_price > typical_price.shift(1), 0)
    money_flow_negative = raw_money_flow.where(typical_price < typical_price.shift(1), 0)
    
    # 计算14天的money flow ratio
    pos_flow_sum = money_flow_positive.rolling(window=14).sum()
    neg_flow_sum = money_flow_negative.rolling(window=14).sum()
    
    # 防止除零错误
    neg_flow_sum = neg_flow_sum.replace(0, 1e-10)
    money_flow_ratio = pos_flow_sum / neg_flow_sum
    
    # 计算MFI
    df['mfi'] = 100 - (100 / (1 + money_flow_ratio))
    
    return df

def create_pattern_recognition_features(df):
    """
    创建K线形态识别特征
    
    参数:
        df: 输入DataFrame，包含OHLCV数据
    
    返回:
        DataFrame: 添加了K线形态特征的DataFrame
    """
    # 确保有必要的列
    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_cols):
        print("错误: 缺少必要的列 (open, high, low, close)")
        return df
    
    # 复制DataFrame以避免修改原始数据
    df_new = df.copy()
    
    # 计算各部分的大小
    df_new['body_size'] = np.abs(df_new['close'] - df_new['open'])
    df_new['upper_shadow'] = df_new['high'] - np.maximum(df_new['open'], df_new['close'])
    df_new['lower_shadow'] = np.minimum(df_new['open'], df_new['close']) - df_new['low']
    df_new['total_range'] = df_new['high'] - df_new['low']
    
    # 计算相对大小
    df_new['rel_body_size'] = df_new['body_size'] / df_new['total_range']
    df_new['rel_upper_shadow'] = df_new['upper_shadow'] / df_new['total_range']
    df_new['rel_lower_shadow'] = df_new['lower_shadow'] / df_new['total_range']
    
    # 替换可能的NaN（当极差为0时）
    df_new.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_new.fillna(0, inplace=True)
    
    # 锤子线和上吊线 (小实体，几乎没有上影线，长下影线)
    df_new['is_hammer'] = ((df_new['rel_body_size'] < 0.3) & 
                        (df_new['rel_upper_shadow'] < 0.1) & 
                        (df_new['rel_lower_shadow'] > 0.6)).astype(int)
    
    # 十字星 (极小实体，上下影线均存在)
    df_new['is_doji'] = (df_new['rel_body_size'] < 0.1).astype(int)
    
    # 吞没形态 (看跌吞没)
    df_new['bearish_engulfing'] = ((df_new['open'] > df_new['close'].shift(1)) & 
                                (df_new['close'] < df_new['open'].shift(1)) & 
                                (df_new['open'] > df_new['open'].shift(1)) & 
                                (df_new['close'] < df_new['close'].shift(1))).astype(int)
    
    # 吞没形态 (看涨吞没)
    df_new['bullish_engulfing'] = ((df_new['open'] < df_new['close'].shift(1)) & 
                                (df_new['close'] > df_new['open'].shift(1)) & 
                                (df_new['open'] < df_new['open'].shift(1)) & 
                                (df_new['close'] > df_new['close'].shift(1))).astype(int)
    
    # 启明星 (三日看涨反转形态)
    # 简化版，完整实现需要考虑更多条件
    df_new['morning_star'] = ((df_new['close'].shift(2) < df_new['open'].shift(2)) &  # 第一日阴线
                           (np.abs(df_new['close'].shift(1) - df_new['open'].shift(1)) < 
                            df_new['body_size'].shift(2) * 0.3) &  # 第二日小实体
                           (df_new['close'].shift(1) < df_new['close'].shift(2)) &  # 第二日收盘价低于第一日
                           (df_new['close'] > df_new['open']) &  # 第三日阳线
                           (df_new['close'] > (df_new['open'].shift(2) + df_new['close'].shift(2)) / 2)  # 第三日收盘价回补第一日部分
                          ).astype(int)
    
    # 黄昏星 (三日看跌反转形态)
    df_new['evening_star'] = ((df_new['close'].shift(2) > df_new['open'].shift(2)) &  # 第一日阳线
                           (np.abs(df_new['close'].shift(1) - df_new['open'].shift(1)) < 
                            df_new['body_size'].shift(2) * 0.3) &  # 第二日小实体
                           (df_new['close'].shift(1) > df_new['close'].shift(2)) &  # 第二日收盘价高于第一日
                           (df_new['close'] < df_new['open']) &  # 第三日阴线
                           (df_new['close'] < (df_new['open'].shift(2) + df_new['close'].shift(2)) / 2)  # 第三日收盘价回补第一日部分
                          ).astype(int)
    
    # 三白兵 (三日看涨持续形态)
    df_new['three_white_soldiers'] = ((df_new['close'] > df_new['open']) &  # 今日阳线
                                   (df_new['close'].shift(1) > df_new['open'].shift(1)) &  # 昨日阳线
                                   (df_new['close'].shift(2) > df_new['open'].shift(2)) &  # 前日阳线
                                   (df_new['close'] > df_new['close'].shift(1)) &  # 今日收盘价高于昨日
                                   (df_new['close'].shift(1) > df_new['close'].shift(2)) &  # 昨日收盘价高于前日
                                   (df_new['open'] > df_new['open'].shift(1)) &  # 今日开盘价高于昨日
                                   (df_new['open'].shift(1) > df_new['open'].shift(2))  # 昨日开盘价高于前日
                                  ).astype(int)
    
    # 三只乌鸦 (三日看跌持续形态)
    df_new['three_black_crows'] = ((df_new['close'] < df_new['open']) &  # 今日阴线
                                (df_new['close'].shift(1) < df_new['open'].shift(1)) &  # 昨日阴线
                                (df_new['close'].shift(2) < df_new['open'].shift(2)) &  # 前日阴线
                                (df_new['close'] < df_new['close'].shift(1)) &  # 今日收盘价低于昨日
                                (df_new['close'].shift(1) < df_new['close'].shift(2)) &  # 昨日收盘价低于前日
                                (df_new['open'] < df_new['open'].shift(1)) &  # 今日开盘价低于昨日
                                (df_new['open'].shift(1) < df_new['open'].shift(2))  # 昨日开盘价低于前日
                               ).astype(int)
    
    # 星线形态 (小实体，与前一日实体有价格跳空)
    df_new['is_star'] = ((df_new['rel_body_size'] < 0.2) & 
                       ((df_new['open'] > df_new['close'].shift(1)) | 
                        (df_new['close'] < df_new['open'].shift(1)))).astype(int)
    
    # 创建综合形态分数
    df_new['bullish_pattern_score'] = (df_new['bullish_engulfing'] * 1 + 
                                     df_new['morning_star'] * 2 + 
                                     df_new['three_white_soldiers'] * 2 +
                                     (df_new['is_hammer'] & (df_new['close'] < df_new['close'].rolling(window=10).mean())) * 1)
    
    df_new['bearish_pattern_score'] = (df_new['bearish_engulfing'] * 1 + 
                                     df_new['evening_star'] * 2 + 
                                     df_new['three_black_crows'] * 2 +
                                     (df_new['is_hammer'] & (df_new['close'] > df_new['close'].rolling(window=10).mean())) * 1)
    
    # 移除临时列以保持DataFrame整洁
    temp_cols = ['body_size', 'upper_shadow', 'lower_shadow', 'total_range',
                'rel_body_size', 'rel_upper_shadow', 'rel_lower_shadow']
    
    # 如果要保留这些列，请注释下一行
    # df_new.drop(columns=temp_cols, inplace=True)
    
    return df_new

def create_market_regime_features(df):
    """
    创建市场状态识别特征
    
    参数:
        df: 输入DataFrame，包含价格数据和技术指标
    
    返回:
        DataFrame: 添加了市场状态特征的DataFrame
    """
    # 复制DataFrame以避免修改原始数据
    df_new = df.copy()
    
    # 趋势强度指标 (基于移动平均线)
    if 'MA20' in df_new.columns and 'MA60' in df_new.columns:
        # 计算短期和长期MA的差距
        df_new['ma_gap_20_60'] = (df_new['MA20'] - df_new['MA60']) / df_new['MA60']
        
        # 趋势强度 - 基于MA差距的变化
        df_new['trend_strength'] = df_new['ma_gap_20_60'].abs()
        
        # 趋势方向
        df_new['trend_direction'] = np.sign(df_new['ma_gap_20_60'])
    
    # 基于ADX的趋势识别（简化版）
    if 'atr' in df_new.columns:
        # 计算+DI和-DI
        high_diff = df_new['high'] - df_new['high'].shift(1)
        low_diff = df_new['low'].shift(1) - df_new['low']
        
        plus_dm = np.where((high_diff > 0) & (high_diff > low_diff), high_diff, 0)
        minus_dm = np.where((low_diff > 0) & (low_diff > high_diff), low_diff, 0)
        
        # 平滑处理
        alpha = 1/14
        plus_di = 100 * pd.Series(plus_dm).ewm(alpha=alpha, adjust=False).mean() / df_new['atr']
        minus_di = 100 * pd.Series(minus_dm).ewm(alpha=alpha, adjust=False).mean() / df_new['atr']
        
        # 计算DX和ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = pd.Series(dx).ewm(alpha=alpha, adjust=False).mean()
        
        # 保存指标
        df_new['plus_di'] = plus_di
        df_new['minus_di'] = minus_di
        df_new['adx'] = adx
        
        # 定义趋势状态
        df_new['adx_trend'] = 0  # 默认为无趋势
        df_new.loc[df_new['adx'] > 25, 'adx_trend'] = 1  # 趋势存在
        
        # 结合方向
        df_new['adx_bull_trend'] = ((df_new['adx_trend'] == 1) & (df_new['plus_di'] > df_new['minus_di'])).astype(int)
        df_new['adx_bear_trend'] = ((df_new['adx_trend'] == 1) & (df_new['plus_di'] < df_new['minus_di'])).astype(int)
    
    # 基于波动性的市场分类
    if 'volatility_20d' in df_new.columns:
        # 计算长期波动率分位数
        df_new['vol_percentile'] = df_new['volatility_20d'].rolling(window=252).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) > 0 else np.nan
        )
        
        # 基于波动率分位数的市场状态
        df_new['high_vol_regime'] = (df_new['vol_percentile'] > 0.8).astype(int)
        df_new['low_vol_regime'] = (df_new['vol_percentile'] < 0.2).astype(int)
        df_new['normal_vol_regime'] = ((df_new['vol_percentile'] >= 0.2) & 
                                     (df_new['vol_percentile'] <= 0.8)).astype(int)
    
    # 基于RSI的市场超买超卖状态
    if 'rsi' in df_new.columns:
        df_new['overbought'] = (df_new['rsi'] > 70).astype(int)
        df_new['oversold'] = (df_new['rsi'] < 30).astype(int)
        df_new['neutral_rsi'] = ((df_new['rsi'] >= 30) & (df_new['rsi'] <= 70)).astype(int)
    
    # 综合市场状态评分
    df_new['market_regime_score'] = 0
    
    # 添加多个市场状态指标的影响
    if 'adx_bull_trend' in df_new.columns:
        df_new['market_regime_score'] += df_new['adx_bull_trend'] * 1
    if 'adx_bear_trend' in df_new.columns:
        df_new['market_regime_score'] -= df_new['adx_bear_trend'] * 1
    if 'overbought' in df_new.columns:
        df_new['market_regime_score'] -= df_new['overbought'] * 0.5
    if 'oversold' in df_new.columns:
        df_new['market_regime_score'] += df_new['oversold'] * 0.5
    if 'trend_direction' in df_new.columns:
        df_new['market_regime_score'] += df_new['trend_direction'] * 0.5
    if 'high_vol_regime' in df_new.columns:
        df_new['market_regime_score'] -= df_new['high_vol_regime'] * 0.3
    
    # 归一化市场状态评分到[-1, 1]范围
    max_abs_score = max(abs(df_new['market_regime_score'].max()), abs(df_new['market_regime_score'].min()))
    if max_abs_score > 0:
        df_new['market_regime_normalized'] = df_new['market_regime_score'] / max_abs_score
    else:
        df_new['market_regime_normalized'] = 0
    
    # 市场状态分类
    df_new['market_state'] = 0  # 中性市场
    df_new.loc[df_new['market_regime_normalized'] > 0.5, 'market_state'] = 1  # 看涨市场
    df_new.loc[df_new['market_regime_normalized'] < -0.5, 'market_state'] = -1  # 看跌市场
    
    return df_new

def add_advanced_indicators(df):
    """
    添加高级技术指标
    
    参数:
        df: 输入DataFrame，需包含OHLCV数据
        
    返回:
        DataFrame: 添加了高级技术指标的DataFrame
    """
    result = df.copy()
    
    # 计算趋势强度指数 (ADX)
    high = result['high']
    low = result['low']
    close = result['close']
    
    # 计算真实范围 (True Range)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # 平均真实范围 (ATR)
    result['atr'] = tr.rolling(window=14).mean()
    
    # 方向性移动 (Directional Movement)
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # Smoothed Directional Movement
    result['adx'] = 0  # 简化处理
    
    # 计算相对强弱指数 (RSI) - 多周期
    for window in [6, 14, 21]:
        delta = result['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        
        # 避免除以零
        avg_loss = avg_loss.replace(0, 0.00001)
        rs = avg_gain / avg_loss
        
        result[f'rsi_{window}'] = 100 - (100 / (1 + rs))
    
    # 计算枢轴点
    result['pivot_point'] = (result['high'] + result['low'] + result['close']) / 3
    result['pivot_r1'] = 2 * result['pivot_point'] - result['low']  # 阻力位1
    result['pivot_s1'] = 2 * result['pivot_point'] - result['high']  # 支撑位1
    
    # 计算MACD - 如果基本指标中未计算
    if 'macd' not in result.columns:
        result['ema12'] = result['close'].ewm(span=12, adjust=False).mean()
        result['ema26'] = result['close'].ewm(span=26, adjust=False).mean()
        result['macd'] = result['ema12'] - result['ema26']
        result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
        result['macd_hist'] = result['macd'] - result['macd_signal']
    
    # 计算随机指标 (Stochastic)
    window = 14
    low_min = result['low'].rolling(window=window).min()
    high_max = result['high'].rolling(window=window).max()
    
    # 确保分母不为零
    denom = high_max - low_min
    denom = denom.replace(0, 0.00001)
    
    result['stoch_k'] = 100 * ((result['close'] - low_min) / denom)
    result['stoch_d'] = result['stoch_k'].rolling(window=3).mean()
    
    # 计算威廉指标 (Williams %R)
    result['williams_r'] = -100 * (high_max - result['close']) / denom
    
    # 计算布林带
    window = 20
    mid_band = result['close'].rolling(window=window).mean()
    std_dev = result['close'].rolling(window=window).std()
    
    result['bollinger_mid'] = mid_band
    result['bollinger_high'] = mid_band + 2 * std_dev
    result['bollinger_low'] = mid_band - 2 * std_dev
    result['bollinger_width'] = (result['bollinger_high'] - result['bollinger_low']) / result['bollinger_mid']
    
    # 钱德动量摆动指标 (CMO)
    up_sum = gain.rolling(window=14).sum()
    down_sum = loss.rolling(window=14).sum()
    
    result['cmo'] = 100 * (up_sum - down_sum) / (up_sum + down_sum)
    
    # 计算顺势指标 (CCI)
    typical_price = (result['high'] + result['low'] + result['close']) / 3
    mean_deviation = abs(typical_price - typical_price.rolling(window=20).mean()).rolling(window=20).mean()
    
    # 避免除以零
    mean_deviation = mean_deviation.replace(0, 0.00001)
    
    result['cci'] = (typical_price - typical_price.rolling(window=20).mean()) / (0.015 * mean_deviation)
    
    # 计算威廉姆累积/派发线 (Williams A/D)
    result['willad'] = np.nan
    for i in range(1, len(result)):
        if i == 1:
            result['willad'].iloc[0] = 0  # 初始化第一个值
        
        if result['close'].iloc[i] > result['close'].iloc[i-1]:
            # 上涨，累积应等于(收盘价 - 最低价) / (最高价 - 最低价)
            if result['high'].iloc[i] != result['low'].iloc[i]:
                result['willad'].iloc[i] = result['willad'].iloc[i-1] + (result['close'].iloc[i] - result['low'].iloc[i]) / (result['high'].iloc[i] - result['low'].iloc[i])
            else:
                result['willad'].iloc[i] = result['willad'].iloc[i-1]
        else:
            # 下跌，派发应等于(收盘价 - 最高价) / (最高价 - 最低价)
            if result['high'].iloc[i] != result['low'].iloc[i]:
                result['willad'].iloc[i] = result['willad'].iloc[i-1] + (result['close'].iloc[i] - result['high'].iloc[i]) / (result['high'].iloc[i] - result['low'].iloc[i])
            else:
                result['willad'].iloc[i] = result['willad'].iloc[i-1]
    
    # 计算资金流量指标 (MFI)
    if 'volume' in result.columns:
        typical_price = (result['high'] + result['low'] + result['close']) / 3
        money_flow = typical_price * result['volume']
        
        pos_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        neg_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
        
        pos_flow_sum = pos_flow.rolling(window=14).sum()
        neg_flow_sum = neg_flow.rolling(window=14).sum()
        
        # 避免除以零
        neg_flow_sum = neg_flow_sum.replace(0, 0.00001)
        
        money_ratio = pos_flow_sum / neg_flow_sum
        result['mfi'] = 100 - (100 / (1 + money_ratio))
    
    # 计算相对强度指数 (RSI) 的超买超卖信号
    result['rsi_overbought'] = (result['rsi_14'] > 70).astype(int)
    result['rsi_oversold'] = (result['rsi_14'] < 30).astype(int)
    
    # 计算价格动量变化率
    result['roc_change'] = result['close'].pct_change(periods=10).diff()
    
    # 填充缺失值
    result = result.fillna(method='bfill').fillna(method='ffill').fillna(0)
    
    return result 