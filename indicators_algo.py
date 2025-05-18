import numpy as np
import pandas as pd
from functools import lru_cache
import importlib
try:
    talib = importlib.import_module('talib')
except ImportError:
    talib = None

# --- MA ---


def calc_ma(close: pd.Series, n: int) -> pd.Series:
    """计算移动平均线（用ta-lib MA）"""
    if talib is None:
        raise ImportError('ta-lib库未安装')
    return pd.Series(talib.MA(close.values, timeperiod=n), index=close.index, name=f"MA{n}")

# --- MACD ---


def calc_macd(close: pd.Series, fast=12, slow=26, signal=9):
    """计算MACD指标（用ta-lib MACD）"""
    if talib is None:
        raise ImportError('ta-lib库未安装')
    macd, macdsignal, macdhist = talib.MACD(
        close.values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
    return (pd.Series(macd, index=close.index, name="MACD"),
            pd.Series(macdsignal, index=close.index, name="MACD_signal"),
            pd.Series(macdhist, index=close.index, name="MACD_hist"))

# --- RSI ---


def calc_rsi(close: pd.Series, n=14):
    """计算RSI指标（用ta-lib RSI）"""
    if talib is None:
        raise ImportError('ta-lib库未安装')
    return pd.Series(talib.RSI(close.values, timeperiod=n), index=close.index, name=f"RSI{n}")

# --- KDJ ---


def calc_kdj(df: pd.DataFrame, n=9, m1=3, m2=3):
    """计算KDJ指标（用ta-lib STOCH）"""
    if talib is None:
        raise ImportError('ta-lib库未安装')
    k, d = talib.STOCH(df['high'].values, df['low'].values, df['close'].values,
                       fastk_period=n, slowk_period=m1, slowd_period=m2)
    j = 3 * k - 2 * d
    return (pd.Series(k, index=df.index, name="K"),
            pd.Series(d, index=df.index, name="D"),
            pd.Series(j, index=df.index, name="J"))

# --- BOLL ---


def calc_boll(close: pd.Series, n=20, p=2):
    """计算布林带（用ta-lib BBANDS）"""
    if talib is None:
        raise ImportError('ta-lib库未安装')
    upper, mid, lower = talib.BBANDS(
        close.values, timeperiod=n, nbdevup=p, nbdevdn=p)
    return (pd.Series(mid, index=close.index, name="BOLL_mid"),
            pd.Series(upper, index=close.index, name="BOLL_upper"),
            pd.Series(lower, index=close.index, name="BOLL_lower"))

# --- ATR ---


def calc_atr(df: pd.DataFrame, n=14):
    """计算ATR指标（用ta-lib ATR）"""
    if talib is None:
        raise ImportError('ta-lib库未安装')
    atr = talib.ATR(df['high'].values, df['low'].values,
                    df['close'].values, timeperiod=n)
    return pd.Series(atr, index=df.index, name=f"ATR{n}")

# --- OBV ---


def calc_obv(df: pd.DataFrame):
    """计算OBV指标（用ta-lib OBV）"""
    if talib is None:
        raise ImportError('ta-lib库未安装')
    obv = talib.OBV(df['close'].values, df['volume'].values)
    return pd.Series(obv, index=df.index, name="OBV")

# --- CCI ---


def calc_cci(df: pd.DataFrame, n=14):
    """计算CCI指标（用ta-lib CCI）"""
    if talib is None:
        raise ImportError('ta-lib库未安装')
    cci = talib.CCI(df['high'].values, df['low'].values,
                    df['close'].values, timeperiod=n)
    return pd.Series(cci, index=df.index, name=f"CCI{n}")

# 可选：加lru_cache缓存装饰器提升性能


def get_talib_indicator_list() -> list:
    """获取所有ta-lib支持的指标名称列表，返回全部大写字符串，增强健壮性"""
    if talib is None:
        print("【错误】未检测到talib库，请先安装 ta-lib C库和 Python 包！")
        return []
    try:
        names = []
        if hasattr(talib, 'get_functions'):
            try:
                names = talib.get_functions()
            except Exception as e:
                print(f"【异常】talib.get_functions() 调用失败: {e}")
                names = []
        if not names:
            names = [n for n in dir(talib) if n.isupper(
            ) and callable(getattr(talib, n, None))]
        exclude = {"VERSION", "MA_Type"}
        names = [str(n).upper() for n in names if n not in exclude]
        if not names:
            print("【错误】未检测到任何ta-lib指标，请检查 ta-lib C库和 Python 包是否都已正确安装！")
        return sorted(names)
    except Exception as e:
        print(f"【异常】获取ta-lib指标失败: {e}")
        return []


def calc_talib_indicator(name: str, df: pd.DataFrame, **params):
    """通用调用ta-lib指标，自动适配参数，返回结果Series或DataFrame"""
    if talib is None:
        raise ImportError('ta-lib库未安装')
    name = name.upper()
    if not hasattr(talib, name):
        raise ValueError(f'不支持的ta-lib指标: {name}')
    func = getattr(talib, name)
    # 自动适配参数
    import inspect
    sig = inspect.signature(func)
    call_args = {}
    for k in sig.parameters:
        if k in df.columns:
            call_args[k] = df[k].values
        elif k in params:
            call_args[k] = params[k]
        elif sig.parameters[k].default is not inspect.Parameter.empty:
            call_args[k] = sig.parameters[k].default
        else:
            # 尝试用close
            if 'close' in df.columns:
                call_args[k] = df['close'].values
    result = func(**call_args)
    # 结果处理
    if isinstance(result, tuple):
        # 多输出，转DataFrame
        cols = [f"{name}_{i+1}" for i in range(len(result))]
        return pd.DataFrame({col: v for col, v in zip(cols, result)}, index=df.index)
    else:
        return pd.Series(result, index=df.index, name=name)


# --- ta-lib指标分类映射表 ---
TA_LIB_CATEGORY_MAP = {
    # 重叠指标
    "MA": "趋势类", "EMA": "趋势类", "SMA": "趋势类", "WMA": "趋势类", "BBANDS": "趋势类", "DEMA": "趋势类", "TEMA": "趋势类", "TRIMA": "趋势类", "KAMA": "趋势类", "MAMA": "趋势类", "MIDPOINT": "趋势类", "MIDPRICE": "趋势类", "SAR": "趋势类", "SAREXT": "趋势类", "T3": "趋势类",
    # 动量指标
    "MACD": "震荡类", "MACDEXT": "震荡类", "MACDFIX": "震荡类", "RSI": "震荡类", "STOCH": "震荡类", "STOCHF": "震荡类", "STOCHRSI": "震荡类", "CCI": "震荡类", "CMO": "震荡类", "DX": "震荡类", "ADX": "震荡类", "ADXR": "震荡类", "MFI": "震荡类", "MOM": "震荡类", "ROC": "震荡类", "ROCP": "震荡类", "ROCR": "震荡类", "ROCR100": "震荡类", "TRIX": "震荡类", "ULTOSC": "震荡类", "WILLR": "震荡类", "BOP": "震荡类", "APO": "震荡类", "PPO": "震荡类", "MINUS_DI": "震荡类", "MINUS_DM": "震荡类", "PLUS_DI": "震荡类", "PLUS_DM": "震荡类",
    # 成交量指标
    "OBV": "成交量类", "AD": "成交量类", "ADOSC": "成交量类", "VOL": "成交量类",
    # 波动性指标
    "ATR": "波动性类", "NATR": "波动性类", "TRANGE": "波动性类",
    # 价格变换
    "AVGPRICE": "其他", "MEDPRICE": "其他", "TYPPRICE": "其他", "WCLPRICE": "其他",
    # 形态识别统一用CDL开头判断
}


def get_talib_category(name: str) -> str:
    """根据ta-lib指标名返回专业分类"""
    if name.upper().startswith("CDL"):
        return "形态识别"
    return TA_LIB_CATEGORY_MAP.get(name.upper(), "其他")


def get_all_indicators_by_category() -> dict:
    """
    返回所有ta-lib指标的分类字典，确保每个分类下有指标，分类名和主界面一致，类型为str
    Returns:
        dict: {分类名: [指标名, ...]}
    """
    if talib is None:
        return {}
    all_names = get_talib_indicator_list()
    categories = {}
    for name in all_names:
        cat = get_talib_category(name)
        if not cat:
            cat = "其他"
        cat = str(cat)  # 强制类型为str，防止前端类型对比异常
        categories.setdefault(cat, []).append(str(name))
    # 只保留有指标的分类
    return {cat: names for cat, names in categories.items() if names}


__all__ = [
    'calc_ma', 'calc_macd', 'calc_rsi', 'calc_kdj', 'calc_boll', 'calc_atr', 'calc_obv', 'calc_cci',
    'get_talib_indicator_list', 'calc_talib_indicator', 'get_talib_category', 'get_all_indicators_by_category'
]
