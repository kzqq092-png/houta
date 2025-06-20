"""
indicators_algo.py
技术指标算法模块

用法示例：
    from core.indicators_algo import TechnicalIndicators
    
    indicators = TechnicalIndicators()
    macd = indicators.calculate_macd(data)
    rsi = indicators.calculate_rsi(data)
    bollinger = indicators.calculate_bollinger_bands(data)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class TechnicalIndicators:
    """
    技术指标计算类
    提供各种常用技术指标的计算方法
    """

    def __init__(self):
        """初始化技术指标计算器"""
        self.cache = {}

    def calculate_sma(self, data: pd.Series, period: int = 20) -> pd.Series:
        """
        计算简单移动平均线 (Simple Moving Average)
        :param data: 价格数据序列
        :param period: 周期
        :return: SMA序列
        """
        return data.rolling(window=period).mean()

    def calculate_ema(self, data: pd.Series, period: int = 20) -> pd.Series:
        """
        计算指数移动平均线 (Exponential Moving Average)
        :param data: 价格数据序列
        :param period: 周期
        :return: EMA序列
        """
        return data.ewm(span=period).mean()

    def calculate_macd(self, data: pd.Series,
                       fast_period: int = 12,
                       slow_period: int = 26,
                       signal_period: int = 9) -> Dict[str, pd.Series]:
        """
        计算MACD指标
        :param data: 价格数据序列
        :param fast_period: 快线周期
        :param slow_period: 慢线周期
        :param signal_period: 信号线周期
        :return: 包含MACD线、信号线和柱状图的字典
        """
        ema_fast = self.calculate_ema(data, fast_period)
        ema_slow = self.calculate_ema(data, slow_period)

        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal_period)
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        计算相对强弱指数 (Relative Strength Index)
        :param data: 价格数据序列
        :param period: 周期
        :return: RSI序列
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_bollinger_bands(self, data: pd.Series,
                                  period: int = 20,
                                  std_dev: float = 2) -> Dict[str, pd.Series]:
        """
        计算布林带
        :param data: 价格数据序列
        :param period: 周期
        :param std_dev: 标准差倍数
        :return: 包含上轨、中轨、下轨的字典
        """
        sma = self.calculate_sma(data, period)
        std = data.rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }

    def calculate_stochastic(self, high: pd.Series,
                             low: pd.Series,
                             close: pd.Series,
                             k_period: int = 14,
                             d_period: int = 3) -> Dict[str, pd.Series]:
        """
        计算随机指标 (Stochastic Oscillator)
        :param high: 最高价序列
        :param low: 最低价序列
        :param close: 收盘价序列
        :param k_period: %K周期
        :param d_period: %D周期
        :return: 包含%K和%D的字典
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()

        return {
            'k': k_percent,
            'd': d_percent
        }

    def calculate_williams_r(self, high: pd.Series,
                             low: pd.Series,
                             close: pd.Series,
                             period: int = 14) -> pd.Series:
        """
        计算威廉指标 (Williams %R)
        :param high: 最高价序列
        :param low: 最低价序列
        :param close: 收盘价序列
        :param period: 周期
        :return: Williams %R序列
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        williams_r = -100 * ((highest_high - close) / (highest_high - lowest_low))

        return williams_r

    def calculate_atr(self, high: pd.Series,
                      low: pd.Series,
                      close: pd.Series,
                      period: int = 14) -> pd.Series:
        """
        计算平均真实波幅 (Average True Range)
        :param high: 最高价序列
        :param low: 最低价序列
        :param close: 收盘价序列
        :param period: 周期
        :return: ATR序列
        """
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return atr

    def calculate_cci(self, high: pd.Series,
                      low: pd.Series,
                      close: pd.Series,
                      period: int = 20) -> pd.Series:
        """
        计算商品通道指数 (Commodity Channel Index)
        :param high: 最高价序列
        :param low: 最低价序列
        :param close: 收盘价序列
        :param period: 周期
        :return: CCI序列
        """
        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        )

        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)

        return cci

    def calculate_adx(self, high: pd.Series,
                      low: pd.Series,
                      close: pd.Series,
                      period: int = 14) -> Dict[str, pd.Series]:
        """
        计算平均趋向指数 (Average Directional Index)
        :param high: 最高价序列
        :param low: 最低价序列
        :param close: 收盘价序列
        :param period: 周期
        :return: 包含ADX、+DI、-DI的字典
        """
        # 计算真实波幅
        atr = self.calculate_atr(high, low, close, period)

        # 计算方向移动
        up_move = high - high.shift()
        down_move = low.shift() - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_dm = pd.Series(plus_dm, index=high.index)
        minus_dm = pd.Series(minus_dm, index=high.index)

        # 计算方向指标
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # 计算ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return {
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        }

    def calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        计算能量潮指标 (On-Balance Volume)
        :param close: 收盘价序列
        :param volume: 成交量序列
        :return: OBV序列
        """
        obv = np.where(close > close.shift(), volume,
                       np.where(close < close.shift(), -volume, 0))
        obv = pd.Series(obv, index=close.index).cumsum()

        return obv

    def calculate_vwap(self, high: pd.Series,
                       low: pd.Series,
                       close: pd.Series,
                       volume: pd.Series) -> pd.Series:
        """
        计算成交量加权平均价 (Volume Weighted Average Price)
        :param high: 最高价序列
        :param low: 最低价序列
        :param close: 收盘价序列
        :param volume: 成交量序列
        :return: VWAP序列
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()

        return vwap

    def calculate_momentum(self, data: pd.Series, period: int = 10) -> pd.Series:
        """
        计算动量指标 (Momentum)
        :param data: 价格数据序列
        :param period: 周期
        :return: 动量序列
        """
        return data - data.shift(period)

    def calculate_roc(self, data: pd.Series, period: int = 10) -> pd.Series:
        """
        计算变化率指标 (Rate of Change)
        :param data: 价格数据序列
        :param period: 周期
        :return: ROC序列
        """
        return ((data - data.shift(period)) / data.shift(period)) * 100

    def calculate_trix(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        计算TRIX指标
        :param data: 价格数据序列
        :param period: 周期
        :return: TRIX序列
        """
        ema1 = self.calculate_ema(data, period)
        ema2 = self.calculate_ema(ema1, period)
        ema3 = self.calculate_ema(ema2, period)

        trix = ((ema3 - ema3.shift()) / ema3.shift()) * 10000

        return trix

    def calculate_ppo(self, data: pd.Series,
                      fast_period: int = 12,
                      slow_period: int = 26) -> pd.Series:
        """
        计算价格震荡百分比 (Percentage Price Oscillator)
        :param data: 价格数据序列
        :param fast_period: 快线周期
        :param slow_period: 慢线周期
        :return: PPO序列
        """
        ema_fast = self.calculate_ema(data, fast_period)
        ema_slow = self.calculate_ema(data, slow_period)

        ppo = ((ema_fast - ema_slow) / ema_slow) * 100

        return ppo

    def calculate_ultimate_oscillator(self, high: pd.Series,
                                      low: pd.Series,
                                      close: pd.Series,
                                      period1: int = 7,
                                      period2: int = 14,
                                      period3: int = 28) -> pd.Series:
        """
        计算终极震荡指标 (Ultimate Oscillator)
        :param high: 最高价序列
        :param low: 最低价序列
        :param close: 收盘价序列
        :param period1: 第一个周期
        :param period2: 第二个周期
        :param period3: 第三个周期
        :return: Ultimate Oscillator序列
        """
        # 计算买压和真实波幅
        buying_pressure = close - np.minimum(low, close.shift())
        true_range = np.maximum(high, close.shift()) - np.minimum(low, close.shift())

        # 计算不同周期的平均值
        bp1 = buying_pressure.rolling(window=period1).sum()
        tr1 = true_range.rolling(window=period1).sum()

        bp2 = buying_pressure.rolling(window=period2).sum()
        tr2 = true_range.rolling(window=period2).sum()

        bp3 = buying_pressure.rolling(window=period3).sum()
        tr3 = true_range.rolling(window=period3).sum()

        # 计算终极震荡指标
        uo = 100 * ((4 * bp1/tr1) + (2 * bp2/tr2) + (bp3/tr3)) / (4 + 2 + 1)

        return uo

    def calculate_all_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算所有技术指标
        :param data: 包含OHLCV数据的DataFrame
        :return: 所有指标的字典
        """
        required_columns = ['open', 'high', 'low', 'close']
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"数据必须包含列: {required_columns}")

        indicators = {}

        # 价格相关指标
        indicators['sma_20'] = self.calculate_sma(data['close'], 20)
        indicators['ema_20'] = self.calculate_ema(data['close'], 20)
        indicators['macd'] = self.calculate_macd(data['close'])
        indicators['rsi'] = self.calculate_rsi(data['close'])
        indicators['bollinger'] = self.calculate_bollinger_bands(data['close'])
        indicators['stochastic'] = self.calculate_stochastic(
            data['high'], data['low'], data['close']
        )
        indicators['williams_r'] = self.calculate_williams_r(
            data['high'], data['low'], data['close']
        )
        indicators['atr'] = self.calculate_atr(
            data['high'], data['low'], data['close']
        )
        indicators['cci'] = self.calculate_cci(
            data['high'], data['low'], data['close']
        )
        indicators['adx'] = self.calculate_adx(
            data['high'], data['low'], data['close']
        )
        indicators['momentum'] = self.calculate_momentum(data['close'])
        indicators['roc'] = self.calculate_roc(data['close'])
        indicators['trix'] = self.calculate_trix(data['close'])
        indicators['ppo'] = self.calculate_ppo(data['close'])
        indicators['ultimate_oscillator'] = self.calculate_ultimate_oscillator(
            data['high'], data['low'], data['close']
        )

        # 成交量相关指标（如果有成交量数据）
        if 'volume' in data.columns:
            indicators['obv'] = self.calculate_obv(data['close'], data['volume'])
            indicators['vwap'] = self.calculate_vwap(
                data['high'], data['low'], data['close'], data['volume']
            )

        return indicators

    def get_signal_summary(self, indicators: Dict[str, Any]) -> Dict[str, str]:
        """
        根据指标值生成交易信号摘要
        :param indicators: 指标字典
        :return: 信号摘要
        """
        signals = {}

        # RSI信号
        if 'rsi' in indicators:
            rsi_value = indicators['rsi'].iloc[-1] if not indicators['rsi'].empty else 50
            if rsi_value < 30:
                signals['rsi'] = 'BUY'
            elif rsi_value > 70:
                signals['rsi'] = 'SELL'
            else:
                signals['rsi'] = 'HOLD'

        # MACD信号
        if 'macd' in indicators:
            macd_data = indicators['macd']
            if len(macd_data['histogram']) >= 2:
                current_hist = macd_data['histogram'].iloc[-1]
                prev_hist = macd_data['histogram'].iloc[-2]

                if current_hist > 0 and prev_hist <= 0:
                    signals['macd'] = 'BUY'
                elif current_hist < 0 and prev_hist >= 0:
                    signals['macd'] = 'SELL'
                else:
                    signals['macd'] = 'HOLD'

        # 布林带信号
        if 'bollinger' in indicators:
            bb_data = indicators['bollinger']
            if not bb_data['upper'].empty and not bb_data['lower'].empty:
                current_price = bb_data['middle'].iloc[-1]  # 使用中轨作为当前价格参考
                upper_band = bb_data['upper'].iloc[-1]
                lower_band = bb_data['lower'].iloc[-1]

                if current_price < lower_band:
                    signals['bollinger'] = 'BUY'
                elif current_price > upper_band:
                    signals['bollinger'] = 'SELL'
                else:
                    signals['bollinger'] = 'HOLD'

        return signals


# 使用示例
if __name__ == "__main__":
    # 创建示例数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    data = pd.DataFrame({
        'open': 100 + np.random.randn(100).cumsum(),
        'high': 102 + np.random.randn(100).cumsum(),
        'low': 98 + np.random.randn(100).cumsum(),
        'close': 100 + np.random.randn(100).cumsum(),
        'volume': np.random.randint(1000000, 10000000, 100)
    }, index=dates)

    # 初始化指标计算器
    indicators = TechnicalIndicators()

    # 计算所有指标
    all_indicators = indicators.calculate_all_indicators(data)

    # 获取信号摘要
    signals = indicators.get_signal_summary(all_indicators)

    print("技术指标信号摘要:")
    for indicator, signal in signals.items():
        print(f"{indicator}: {signal}")

    # 打印一些具体指标值
    print(f"\n当前RSI值: {all_indicators['rsi'].iloc[-1]:.2f}")
    print(f"当前MACD柱状图: {all_indicators['macd']['histogram'].iloc[-1]:.4f}")
    print(f"当前布林带位置: 上轨={all_indicators['bollinger']['upper'].iloc[-1]:.2f}, "
          f"下轨={all_indicators['bollinger']['lower'].iloc[-1]:.2f}")


# 兼容性函数 - 为了支持直接函数调用
_indicator_instance = TechnicalIndicators()


def calc_ma(data, period=20):
    """计算移动平均线"""
    if isinstance(data, pd.DataFrame):
        return _indicator_instance.calculate_sma(data['close'], period)
    return _indicator_instance.calculate_sma(data, period)


def calc_macd(data, fast_period=12, slow_period=26, signal_period=9):
    """计算MACD"""
    if isinstance(data, pd.DataFrame):
        return _indicator_instance.calculate_macd(data['close'], fast_period, slow_period, signal_period)
    return _indicator_instance.calculate_macd(data, fast_period, slow_period, signal_period)


def calc_rsi(data, period=14):
    """计算RSI"""
    if isinstance(data, pd.DataFrame):
        return _indicator_instance.calculate_rsi(data['close'], period)
    return _indicator_instance.calculate_rsi(data, period)


def calc_kdj(data, k_period=14, d_period=3):
    """计算KDJ（随机指标）"""
    if isinstance(data, pd.DataFrame):
        return _indicator_instance.calculate_stochastic(data['high'], data['low'], data['close'], k_period, d_period)
    else:
        raise ValueError("KDJ计算需要OHLC数据框")


def calc_boll(data, period=20, std_dev=2):
    """计算布林带"""
    if isinstance(data, pd.DataFrame):
        return _indicator_instance.calculate_bollinger_bands(data['close'], period, std_dev)
    return _indicator_instance.calculate_bollinger_bands(data, period, std_dev)


def calc_atr(data, period=14):
    """计算ATR"""
    if isinstance(data, pd.DataFrame):
        return _indicator_instance.calculate_atr(data['high'], data['low'], data['close'], period)
    else:
        raise ValueError("ATR计算需要OHLC数据框")


def calc_obv(data):
    """计算OBV"""
    if isinstance(data, pd.DataFrame):
        return _indicator_instance.calculate_obv(data['close'], data['volume'])
    else:
        raise ValueError("OBV计算需要价格和成交量数据")


def calc_cci(data, period=20):
    """计算CCI"""
    if isinstance(data, pd.DataFrame):
        return _indicator_instance.calculate_cci(data['high'], data['low'], data['close'], period)
    else:
        raise ValueError("CCI计算需要OHLC数据框")


def get_talib_indicator_list():
    """获取可用的技术指标列表"""
    return [
        'SMA', 'EMA', 'MACD', 'RSI', 'BOLL', 'KDJ', 'ATR', 'OBV', 'CCI',
        'STOCH', 'WILLR', 'ADX', 'MOMENTUM', 'ROC', 'TRIX', 'PPO'
    ]


def get_talib_category():
    """获取指标分类"""
    return {
        'Overlap Studies': ['SMA', 'EMA', 'BOLL'],
        'Momentum Indicators': ['MACD', 'RSI', 'STOCH', 'WILLR', 'MOMENTUM', 'ROC'],
        'Volume Indicators': ['OBV'],
        'Volatility Indicators': ['ATR'],
        'Price Transform': ['TRIX'],
        'Cycle Indicators': ['ADX'],
        'Pattern Recognition': ['CCI']
    }


def get_all_indicators_by_category(use_chinese=False):
    """获取按分类组织的所有指标

    Args:
        use_chinese (bool): 是否使用中文名称，默认False

    Returns:
        dict: 按分类组织的指标字典
    """
    categories = get_talib_category()

    if use_chinese:
        # 转换为中文分类名称和指标名称
        chinese_categories = {}
        category_name_map = {
            'Overlap Studies': '重叠研究',
            'Momentum Indicators': '动量指标',
            'Volume Indicators': '成交量指标',
            'Volatility Indicators': '波动率指标',
            'Price Transform': '价格变换',
            'Cycle Indicators': '周期指标',
            'Pattern Recognition': '形态识别',
            'Statistic Functions': '统计函数',
            'Math Transform': '数学变换',
            'Math Operators': '数学运算'
        }

        for category, indicators in categories.items():
            chinese_category = category_name_map.get(category, category)
            chinese_indicators = []
            for indicator in indicators:
                chinese_name = get_talib_chinese_name(indicator)
                chinese_indicators.append(chinese_name)
            chinese_categories[chinese_category] = chinese_indicators

        return chinese_categories
    else:
        return categories


def calc_talib_indicator(name, data, **kwargs):
    """计算talib指标的通用方法"""
    try:
        import talib
        if hasattr(talib, name.upper()):
            func = getattr(talib, name.upper())
            if isinstance(data, pd.DataFrame):
                if 'close' in data.columns:
                    return func(data['close'], **kwargs)
                elif 'Close' in data.columns:
                    return func(data['Close'], **kwargs)
            elif isinstance(data, pd.Series):
                return func(data, **kwargs)
        return None
    except ImportError:
        return None


# 新增：缺失的函数定义
def get_talib_chinese_name(indicator_name: str) -> str:
    """获取指标的中文名称"""
    chinese_names = {
        'SMA': '简单移动平均',
        'EMA': '指数移动平均',
        'WMA': '加权移动平均',
        'DEMA': '双指数移动平均',
        'TEMA': '三指数移动平均',
        'TRIMA': '三角移动平均',
        'KAMA': '考夫曼自适应移动平均',
        'MAMA': '自适应移动平均',
        'T3': 'T3移动平均',
        'MACD': 'MACD',
        'MACDEXT': 'MACD扩展',
        'MACDFIX': 'MACD固定',
        'APO': '绝对价格振荡器',
        'PPO': '百分比价格振荡器',
        'RSI': '相对强弱指数',
        'STOCH': '随机指标',
        'STOCHF': '快速随机指标',
        'STOCHRSI': '随机RSI',
        'WILLR': '威廉指标',
        'ADX': '平均趋向指标',
        'ADXR': 'ADX评估',
        'APO': '绝对价格振荡器',
        'AROON': '阿隆指标',
        'AROONOSC': '阿隆振荡器',
        'BOP': '均势指标',
        'CCI': '顺势指标',
        'CMO': '钱德动量振荡器',
        'DX': '趋向指标',
        'MFI': '资金流量指标',
        'MINUS_DI': '负趋向指标',
        'MINUS_DM': '负动向指标',
        'MOM': '动量指标',
        'PLUS_DI': '正趋向指标',
        'PLUS_DM': '正动向指标',
        'ROC': '变动率指标',
        'ROCP': '变动率百分比',
        'ROCR': '变动率比率',
        'ROCR100': '变动率比率100',
        'TRIX': 'TRIX指标',
        'ULTOSC': '终极振荡器',
        'BBANDS': '布林带',
        'DEMA': '双指数移动平均',
        'HT_TRENDLINE': '希尔伯特变换趋势线',
        'KAMA': '考夫曼自适应移动平均',
        'MA': '移动平均',
        'MIDPOINT': '中点价',
        'MIDPRICE': '中间价',
        'SAR': '抛物线SAR',
        'SAREXT': '抛物线SAR扩展',
        'T3': 'T3移动平均',
        'TEMA': '三指数移动平均',
        'TRIMA': '三角移动平均',
        'WMA': '加权移动平均',
        'CDL2CROWS': '两只乌鸦',
        'CDL3BLACKCROWS': '三只黑乌鸦',
        'CDL3INSIDE': '三内部',
        'CDL3LINESTRIKE': '三线打击',
        'CDL3OUTSIDE': '三外部',
        'CDL3STARSINSOUTH': '南方三星',
        'CDL3WHITESOLDIERS': '三个白兵',
        'CDLABANDONEDBABY': '弃婴',
        'CDLADVANCEBLOCK': '前进阻挡',
        'CDLBELTHOLD': '捉腰带',
        'CDLBREAKAWAY': '脱离',
        'CDLCLOSINGMARUBOZU': '收盘光头光脚',
        'CDLCONCEALBABYSWALL': '藏婴吞没',
        'CDLCOUNTERATTACK': '反击',
        'CDLDARKCLOUDCOVER': '乌云盖顶',
        'CDLDOJI': '十字星',
        'CDLDOJISTAR': '十字星',
        'CDLDRAGONFLYDOJI': '蜻蜓十字',
        'CDLENGULFING': '吞没',
        'CDLEVENINGDOJISTAR': '黄昏十字星',
        'CDLEVENINGSTAR': '黄昏星',
        'CDLGAPSIDESIDEWHITE': '向上跳空并列白线',
        'CDLGRAVESTONEDOJI': '墓碑十字',
        'CDLHAMMER': '锤子',
        'CDLHANGINGMAN': '上吊',
        'CDLHARAMI': '孕线',
        'CDLHARAMICROSS': '十字孕线',
        'CDLHIGHWAVE': '长脚十字',
        'CDLHIKKAKE': 'Hikkake',
        'CDLHIKKAKEMOD': 'Hikkake修正',
        'CDLHOMINGPIGEON': '信鸽',
        'CDLIDENTICAL3CROWS': '相同三乌鸦',
        'CDLINNECK': '颈内线',
        'CDLINVERTEDHAMMER': '倒锤子',
        'CDLKICKING': '踢腿',
        'CDLKICKINGBYLENGTH': '长踢腿',
        'CDLLADDERBOTTOM': '梯底',
        'CDLLONGLEGGEDDOJI': '长腿十字',
        'CDLLONGLINE': '长线',
        'CDLMARUBOZU': '光头光脚',
        'CDLMATCHINGLOW': '相同低价',
        'CDLMATHOLD': '垫脚石',
        'CDLMORNINGDOJISTAR': '早晨十字星',
        'CDLMORNINGSTAR': '早晨星',
        'CDLONNECK': '颈上线',
        'CDLPIERCING': '刺透',
        'CDLRICKSHAWMAN': '人力车夫',
        'CDLRISEFALL3METHODS': '上升/下降三法',
        'CDLSEPARATINGLINES': '分离线',
        'CDLSHOOTINGSTAR': '流星',
        'CDLSHORTLINE': '短线',
        'CDLSPINNINGTOP': '纺锤',
        'CDLSTALLEDPATTERN': '停顿形态',
        'CDLSTICKSANDWICH': '条形三明治',
        'CDLTAKURI': 'Takuri',
        'CDLTASUKIGAP': 'Tasuki跳空',
        'CDLTHRUSTING': '插入',
        'CDLTRISTAR': '三星',
        'CDLUNIQUE3RIVER': '奇特三河',
        'CDLUPSIDEGAP2CROWS': '向上跳空两乌鸦',
        'CDLXSIDEGAP3METHODS': '跳空三法',
        'AD': '累积/派发线',
        'ADOSC': 'A/D振荡器',
        'OBV': '能量潮',
        'HT_DCPERIOD': '希尔伯特变换主导周期',
        'HT_DCPHASE': '希尔伯特变换主导周期相位',
        'HT_PHASOR': '希尔伯特变换相量',
        'HT_SINE': '希尔伯特变换正弦波',
        'HT_TRENDMODE': '希尔伯特变换趋势模式',
        'AVGPRICE': '平均价格',
        'MEDPRICE': '中位价格',
        'TYPPRICE': '典型价格',
        'WCLPRICE': '加权收盘价',
        'ATR': '真实波动幅度',
        'NATR': '标准化ATR',
        'TRANGE': '真实范围',
        'BETA': 'Beta系数',
        'CORREL': '相关系数',
        'LINEARREG': '线性回归',
        'LINEARREG_ANGLE': '线性回归角度',
        'LINEARREG_INTERCEPT': '线性回归截距',
        'LINEARREG_SLOPE': '线性回归斜率',
        'STDDEV': '标准差',
        'TSF': '时间序列预测',
        'VAR': '方差'
    }
    return chinese_names.get(indicator_name.upper(), indicator_name)


def get_indicator_english_name(chinese_name: str) -> str:
    """根据中文名称获取英文指标名称"""
    chinese_to_english = {
        '简单移动平均': 'SMA',
        '指数移动平均': 'EMA',
        '加权移动平均': 'WMA',
        '双指数移动平均': 'DEMA',
        '三指数移动平均': 'TEMA',
        '三角移动平均': 'TRIMA',
        '考夫曼自适应移动平均': 'KAMA',
        '自适应移动平均': 'MAMA',
        'T3移动平均': 'T3',
        'MACD': 'MACD',
        'MACD扩展': 'MACDEXT',
        'MACD固定': 'MACDFIX',
        '绝对价格振荡器': 'APO',
        '百分比价格振荡器': 'PPO',
        '相对强弱指数': 'RSI',
        '随机指标': 'STOCH',
        '快速随机指标': 'STOCHF',
        '随机RSI': 'STOCHRSI',
        '威廉指标': 'WILLR',
        '平均趋向指标': 'ADX',
        'ADX评估': 'ADXR',
        '阿隆指标': 'AROON',
        '阿隆振荡器': 'AROONOSC',
        '均势指标': 'BOP',
        '顺势指标': 'CCI',
        '钱德动量振荡器': 'CMO',
        '趋向指标': 'DX',
        '资金流量指标': 'MFI',
        '负趋向指标': 'MINUS_DI',
        '负动向指标': 'MINUS_DM',
        '动量指标': 'MOM',
        '正趋向指标': 'PLUS_DI',
        '正动向指标': 'PLUS_DM',
        '变动率指标': 'ROC',
        '变动率百分比': 'ROCP',
        '变动率比率': 'ROCR',
        '变动率比率100': 'ROCR100',
        'TRIX指标': 'TRIX',
        '终极振荡器': 'ULTOSC',
        '布林带': 'BBANDS',
        '希尔伯特变换趋势线': 'HT_TRENDLINE',
        '移动平均': 'MA',
        '中点价': 'MIDPOINT',
        '中间价': 'MIDPRICE',
        '抛物线SAR': 'SAR',
        '抛物线SAR扩展': 'SAREXT',
        '累积/派发线': 'AD',
        'A/D振荡器': 'ADOSC',
        '能量潮': 'OBV',
        '平均价格': 'AVGPRICE',
        '中位价格': 'MEDPRICE',
        '典型价格': 'TYPPRICE',
        '加权收盘价': 'WCLPRICE',
        '真实波动幅度': 'ATR',
        '标准化ATR': 'NATR',
        '真实范围': 'TRANGE',
        'Beta系数': 'BETA',
        '相关系数': 'CORREL',
        '线性回归': 'LINEARREG',
        '线性回归角度': 'LINEARREG_ANGLE',
        '线性回归截距': 'LINEARREG_INTERCEPT',
        '线性回归斜率': 'LINEARREG_SLOPE',
        '标准差': 'STDDEV',
        '时间序列预测': 'TSF',
        '方差': 'VAR'
    }
    return chinese_to_english.get(chinese_name, chinese_name)


def get_indicator_params_config(indicator_name: str) -> Dict[str, Any]:
    """获取指标的参数配置"""
    params_config = {
        'SMA': {'timeperiod': {'type': 'int', 'default': 30, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'EMA': {'timeperiod': {'type': 'int', 'default': 30, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'WMA': {'timeperiod': {'type': 'int', 'default': 30, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'DEMA': {'timeperiod': {'type': 'int', 'default': 30, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'TEMA': {'timeperiod': {'type': 'int', 'default': 30, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'TRIMA': {'timeperiod': {'type': 'int', 'default': 30, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'KAMA': {'timeperiod': {'type': 'int', 'default': 30, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'T3': {'timeperiod': {'type': 'int', 'default': 5, 'min': 2, 'max': 100, 'description': '时间周期'}, 'vfactor': {'type': 'float', 'default': 0.7, 'min': 0, 'max': 1, 'description': '体积因子'}},
        'MACD': {
            'fastperiod': {'type': 'int', 'default': 12, 'min': 2, 'max': 100, 'description': '快速周期'},
            'slowperiod': {'type': 'int', 'default': 26, 'min': 2, 'max': 200, 'description': '慢速周期'},
            'signalperiod': {'type': 'int', 'default': 9, 'min': 1, 'max': 100, 'description': '信号周期'}
        },
        'RSI': {'timeperiod': {'type': 'int', 'default': 14, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'STOCH': {
            'fastk_period': {'type': 'int', 'default': 5, 'min': 1, 'max': 100, 'description': '快速K周期'},
            'slowk_period': {'type': 'int', 'default': 3, 'min': 1, 'max': 100, 'description': '慢速K周期'},
            'slowd_period': {'type': 'int', 'default': 3, 'min': 1, 'max': 100, 'description': '慢速D周期'},
            'slowk_matype': {'type': 'int', 'default': 0, 'min': 0, 'max': 8, 'description': '慢速K平均类型'},
            'slowd_matype': {'type': 'int', 'default': 0, 'min': 0, 'max': 8, 'description': '慢速D平均类型'}
        },
        'WILLR': {'timeperiod': {'type': 'int', 'default': 14, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'ADX': {'timeperiod': {'type': 'int', 'default': 14, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'CCI': {'timeperiod': {'type': 'int', 'default': 14, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'MFI': {'timeperiod': {'type': 'int', 'default': 14, 'min': 2, 'max': 200, 'description': '时间周期'}},
        'MOM': {'timeperiod': {'type': 'int', 'default': 10, 'min': 1, 'max': 200, 'description': '时间周期'}},
        'ROC': {'timeperiod': {'type': 'int', 'default': 10, 'min': 1, 'max': 200, 'description': '时间周期'}},
        'TRIX': {'timeperiod': {'type': 'int', 'default': 30, 'min': 1, 'max': 200, 'description': '时间周期'}},
        'ULTOSC': {
            'timeperiod1': {'type': 'int', 'default': 7, 'min': 1, 'max': 100, 'description': '第一时间周期'},
            'timeperiod2': {'type': 'int', 'default': 14, 'min': 1, 'max': 100, 'description': '第二时间周期'},
            'timeperiod3': {'type': 'int', 'default': 28, 'min': 1, 'max': 100, 'description': '第三时间周期'}
        },
        'BBANDS': {
            'timeperiod': {'type': 'int', 'default': 5, 'min': 2, 'max': 200, 'description': '时间周期'},
            'nbdevup': {'type': 'float', 'default': 2, 'min': 0.1, 'max': 5, 'description': '上轨标准差倍数'},
            'nbdevdn': {'type': 'float', 'default': 2, 'min': 0.1, 'max': 5, 'description': '下轨标准差倍数'},
            'matype': {'type': 'int', 'default': 0, 'min': 0, 'max': 8, 'description': '移动平均类型'}
        },
        'ATR': {'timeperiod': {'type': 'int', 'default': 14, 'min': 1, 'max': 200, 'description': '时间周期'}},
        'OBV': {},  # OBV没有参数
        'SAR': {
            'acceleration': {'type': 'float', 'default': 0.02, 'min': 0.01, 'max': 1, 'description': '加速因子'},
            'maximum': {'type': 'float', 'default': 0.2, 'min': 0.01, 'max': 1, 'description': '最大加速因子'}
        }
    }
    return params_config.get(indicator_name.upper(), {})


def get_indicator_default_params(indicator_name: str) -> Dict[str, Any]:
    """获取指标的默认参数"""
    config = get_indicator_params_config(indicator_name)
    defaults = {}
    for param_name, param_config in config.items():
        if 'default' in param_config:
            defaults[param_name] = param_config['default']
    return defaults


def get_indicator_inputs(indicator_name: str) -> List[str]:
    """获取指标需要的输入数据类型"""
    input_requirements = {
        # 只需要收盘价的指标
        'SMA': ['close'],
        'EMA': ['close'],
        'WMA': ['close'],
        'DEMA': ['close'],
        'TEMA': ['close'],
        'TRIMA': ['close'],
        'KAMA': ['close'],
        'T3': ['close'],
        'RSI': ['close'],
        'MOM': ['close'],
        'ROC': ['close'],
        'TRIX': ['close'],
        'LINEARREG': ['close'],
        'STDDEV': ['close'],
        'TSF': ['close'],
        'VAR': ['close'],

        # 需要高低收盘价的指标
        'STOCH': ['high', 'low', 'close'],
        'STOCHF': ['high', 'low', 'close'],
        'WILLR': ['high', 'low', 'close'],
        'ADX': ['high', 'low', 'close'],
        'ADXR': ['high', 'low', 'close'],
        'AROON': ['high', 'low'],
        'AROONOSC': ['high', 'low'],
        'BOP': ['open', 'high', 'low', 'close'],
        'CCI': ['high', 'low', 'close'],
        'DX': ['high', 'low', 'close'],
        'MINUS_DI': ['high', 'low', 'close'],
        'MINUS_DM': ['high', 'low'],
        'PLUS_DI': ['high', 'low', 'close'],
        'PLUS_DM': ['high', 'low'],
        'ULTOSC': ['high', 'low', 'close'],
        'BBANDS': ['close'],
        'ATR': ['high', 'low', 'close'],
        'NATR': ['high', 'low', 'close'],
        'TRANGE': ['high', 'low', 'close'],
        'SAR': ['high', 'low'],
        'SAREXT': ['high', 'low'],

        # 需要成交量的指标
        'OBV': ['close', 'volume'],
        'AD': ['high', 'low', 'close', 'volume'],
        'ADOSC': ['high', 'low', 'close', 'volume'],
        'MFI': ['high', 'low', 'close', 'volume'],

        # MACD系列
        'MACD': ['close'],
        'MACDEXT': ['close'],
        'MACDFIX': ['close'],
        'APO': ['close'],
        'PPO': ['close'],

        # 价格相关
        'AVGPRICE': ['open', 'high', 'low', 'close'],
        'MEDPRICE': ['high', 'low'],
        'TYPPRICE': ['high', 'low', 'close'],
        'WCLPRICE': ['high', 'low', 'close'],

        # 希尔伯特变换系列
        'HT_DCPERIOD': ['close'],
        'HT_DCPHASE': ['close'],
        'HT_PHASOR': ['close'],
        'HT_SINE': ['close'],
        'HT_TRENDLINE': ['close'],
        'HT_TRENDMODE': ['close'],

        # 统计函数
        'BETA': ['high', 'low'],
        'CORREL': ['high', 'low'],
        'LINEARREG_ANGLE': ['close'],
        'LINEARREG_INTERCEPT': ['close'],
        'LINEARREG_SLOPE': ['close'],

        # K线形态（需要OHLC）
        'CDL2CROWS': ['open', 'high', 'low', 'close'],
        'CDL3BLACKCROWS': ['open', 'high', 'low', 'close'],
        'CDL3INSIDE': ['open', 'high', 'low', 'close'],
        'CDL3LINESTRIKE': ['open', 'high', 'low', 'close'],
        'CDL3OUTSIDE': ['open', 'high', 'low', 'close'],
        'CDL3STARSINSOUTH': ['open', 'high', 'low', 'close'],
        'CDL3WHITESOLDIERS': ['open', 'high', 'low', 'close'],
        'CDLABANDONEDBABY': ['open', 'high', 'low', 'close'],
        'CDLADVANCEBLOCK': ['open', 'high', 'low', 'close'],
        'CDLBELTHOLD': ['open', 'high', 'low', 'close'],
        'CDLBREAKAWAY': ['open', 'high', 'low', 'close'],
        'CDLCLOSINGMARUBOZU': ['open', 'high', 'low', 'close'],
        'CDLCONCEALBABYSWALL': ['open', 'high', 'low', 'close'],
        'CDLCOUNTERATTACK': ['open', 'high', 'low', 'close'],
        'CDLDARKCLOUDCOVER': ['open', 'high', 'low', 'close'],
        'CDLDOJI': ['open', 'high', 'low', 'close'],
        'CDLDOJISTAR': ['open', 'high', 'low', 'close'],
        'CDLDRAGONFLYDOJI': ['open', 'high', 'low', 'close'],
        'CDLENGULFING': ['open', 'high', 'low', 'close'],
        'CDLEVENINGDOJISTAR': ['open', 'high', 'low', 'close'],
        'CDLEVENINGSTAR': ['open', 'high', 'low', 'close'],
        'CDLGAPSIDESIDEWHITE': ['open', 'high', 'low', 'close'],
        'CDLGRAVESTONEDOJI': ['open', 'high', 'low', 'close'],
        'CDLHAMMER': ['open', 'high', 'low', 'close'],
        'CDLHANGINGMAN': ['open', 'high', 'low', 'close'],
        'CDLHARAMI': ['open', 'high', 'low', 'close'],
        'CDLHARAMICROSS': ['open', 'high', 'low', 'close'],
        'CDLHIGHWAVE': ['open', 'high', 'low', 'close'],
        'CDLHIKKAKE': ['open', 'high', 'low', 'close'],
        'CDLHIKKAKEMOD': ['open', 'high', 'low', 'close'],
        'CDLHOMINGPIGEON': ['open', 'high', 'low', 'close'],
        'CDLIDENTICAL3CROWS': ['open', 'high', 'low', 'close'],
        'CDLINNECK': ['open', 'high', 'low', 'close'],
        'CDLINVERTEDHAMMER': ['open', 'high', 'low', 'close'],
        'CDLKICKING': ['open', 'high', 'low', 'close'],
        'CDLKICKINGBYLENGTH': ['open', 'high', 'low', 'close'],
        'CDLLADDERBOTTOM': ['open', 'high', 'low', 'close'],
        'CDLLONGLEGGEDDOJI': ['open', 'high', 'low', 'close'],
        'CDLLONGLINE': ['open', 'high', 'low', 'close'],
        'CDLMARUBOZU': ['open', 'high', 'low', 'close'],
        'CDLMATCHINGLOW': ['open', 'high', 'low', 'close'],
        'CDLMATHOLD': ['open', 'high', 'low', 'close'],
        'CDLMORNINGDOJISTAR': ['open', 'high', 'low', 'close'],
        'CDLMORNINGSTAR': ['open', 'high', 'low', 'close'],
        'CDLONNECK': ['open', 'high', 'low', 'close'],
        'CDLPIERCING': ['open', 'high', 'low', 'close'],
        'CDLRICKSHAWMAN': ['open', 'high', 'low', 'close'],
        'CDLRISEFALL3METHODS': ['open', 'high', 'low', 'close'],
        'CDLSEPARATINGLINES': ['open', 'high', 'low', 'close'],
        'CDLSHOOTINGSTAR': ['open', 'high', 'low', 'close'],
        'CDLSHORTLINE': ['open', 'high', 'low', 'close'],
        'CDLSPINNINGTOP': ['open', 'high', 'low', 'close'],
        'CDLSTALLEDPATTERN': ['open', 'high', 'low', 'close'],
        'CDLSTICKSANDWICH': ['open', 'high', 'low', 'close'],
        'CDLTAKURI': ['open', 'high', 'low', 'close'],
        'CDLTASUKIGAP': ['open', 'high', 'low', 'close'],
        'CDLTHRUSTING': ['open', 'high', 'low', 'close'],
        'CDLTRISTAR': ['open', 'high', 'low', 'close'],
        'CDLUNIQUE3RIVER': ['open', 'high', 'low', 'close'],
        'CDLUPSIDEGAP2CROWS': ['open', 'high', 'low', 'close'],
        'CDLXSIDEGAP3METHODS': ['open', 'high', 'low', 'close']
    }
    return input_requirements.get(indicator_name.upper(), ['close'])
