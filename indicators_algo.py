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
    """计算移动平均线，优先用ta-lib，自动回退pandas实现，增加类型检查和异常捕获。"""
    try:
        if not isinstance(close, pd.Series):
            raise TypeError("calc_ma: close参数必须为pd.Series类型")
        if talib is not None:
            return pd.Series(talib.MA(close.values, timeperiod=n), index=close.index, name=f"MA{n}")
        else:
            return close.rolling(window=n).mean().rename(f"MA{n}")
    except Exception as e:
        # 返回全NaN，防止异常中断
        return pd.Series([float('nan')] * len(close), index=close.index, name=f"MA{n}")

# --- MACD ---


def calc_macd(close: pd.Series, fast=12, slow=26, signal=9):
    """计算MACD指标（用ta-lib MACD）"""
    try:
        if talib is None:
            raise ImportError('ta-lib库未安装')
        if not isinstance(close, pd.Series):
            raise TypeError("calc_macd: close参数必须为pd.Series类型")
        macd, macdsignal, macdhist = talib.MACD(
            close.values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
        idx = close.index
        return (pd.Series(macd, index=idx, name="MACD"),
                pd.Series(macdsignal, index=idx, name="MACD_signal"),
                pd.Series(macdhist, index=idx, name="MACD_hist"))
    except Exception as e:
        idx = close.index if isinstance(close, pd.Series) else None
        return (
            pd.Series([float('nan')] * len(close), index=idx, name="MACD") if idx is not None else None,
            pd.Series([float('nan')] * len(close), index=idx, name="MACD_signal") if idx is not None else None,
            pd.Series([float('nan')] * len(close), index=idx, name="MACD_hist") if idx is not None else None
        )

# --- RSI ---


def calc_rsi(close: pd.Series, n=14):
    """计算RSI指标（用ta-lib RSI）"""
    try:
        if talib is None:
            raise ImportError('ta-lib库未安装')
        if not isinstance(close, pd.Series):
            raise TypeError("calc_rsi: close参数必须为pd.Series类型")
        return pd.Series(talib.RSI(close.values, timeperiod=n), index=close.index, name=f"RSI{n}")
    except Exception as e:
        idx = close.index if isinstance(close, pd.Series) else None
        return pd.Series([float('nan')] * len(close), index=idx, name=f"RSI{n}") if idx is not None else None

# --- KDJ ---


def calc_kdj(df: pd.DataFrame, n=9, m1=3, m2=3):
    """计算KDJ指标（用ta-lib STOCH）"""
    try:
        if talib is None:
            raise ImportError('ta-lib库未安装')
        for col in ['high', 'low', 'close']:
            if col not in df.columns:
                raise ValueError(f"calc_kdj: 缺少{col}列")
        k, d = talib.STOCH(df['high'].values, df['low'].values, df['close'].values,
                           fastk_period=n, slowk_period=m1, slowd_period=m2)
        j = 3 * k - 2 * d
        idx = df.index
        return (pd.Series(k, index=idx, name="K"),
                pd.Series(d, index=idx, name="D"),
                pd.Series(j, index=idx, name="J"))
    except Exception as e:
        idx = df.index if isinstance(df, pd.DataFrame) else None
        def nan_series(name): return pd.Series([float('nan')] * len(df), index=idx, name=name) if idx is not None else None
        return (nan_series("K"), nan_series("D"), nan_series("J"))

# --- BOLL ---


def calc_boll(close: pd.Series, n=20, p=2):
    """计算布林带（用ta-lib BBANDS）"""
    try:
        if talib is None:
            raise ImportError('ta-lib库未安装')
        if not isinstance(close, pd.Series):
            raise TypeError("calc_boll: close参数必须为pd.Series类型")
        upper, mid, lower = talib.BBANDS(
            close.values, timeperiod=n, nbdevup=p, nbdevdn=p)
        idx = close.index
        return (pd.Series(mid, index=idx, name="BOLL_mid"),
                pd.Series(upper, index=idx, name="BOLL_upper"),
                pd.Series(lower, index=idx, name="BOLL_lower"))
    except Exception as e:
        idx = close.index if isinstance(close, pd.Series) else None
        def nan_series(name): return pd.Series([float('nan')] * len(close), index=idx, name=name) if idx is not None else None
        return (nan_series("BOLL_mid"), nan_series("BOLL_upper"), nan_series("BOLL_lower"))

# --- ATR ---


def calc_atr(df: pd.DataFrame, n=14):
    """计算ATR指标（用ta-lib ATR）"""
    try:
        if talib is None:
            raise ImportError('ta-lib库未安装')
        for col in ['high', 'low', 'close']:
            if col not in df.columns:
                raise ValueError(f"calc_atr: 缺少{col}列")
        atr = talib.ATR(df['high'].values, df['low'].values,
                        df['close'].values, timeperiod=n)
        return pd.Series(atr, index=df.index, name=f"ATR{n}")
    except Exception as e:
        idx = df.index if isinstance(df, pd.DataFrame) else None
        return pd.Series([float('nan')] * len(df), index=idx, name=f"ATR{n}") if idx is not None else None

# --- OBV ---


def calc_obv(df: pd.DataFrame):
    """计算OBV指标（用ta-lib OBV）"""
    try:
        if talib is None:
            raise ImportError('ta-lib库未安装')
        for col in ['close', 'volume']:
            if col not in df.columns:
                raise ValueError(f"calc_obv: 缺少{col}列")
        obv = talib.OBV(df['close'].values, df['volume'].values)
        return pd.Series(obv, index=df.index, name="OBV")
    except Exception as e:
        idx = df.index if isinstance(df, pd.DataFrame) else None
        return pd.Series([float('nan')] * len(df), index=idx, name="OBV") if idx is not None else None

# --- CCI ---


def calc_cci(df: pd.DataFrame, n=14):
    """计算CCI指标（用ta-lib CCI）"""
    try:
        if talib is None:
            raise ImportError('ta-lib库未安装')
        for col in ['high', 'low', 'close']:
            if col not in df.columns:
                raise ValueError(f"calc_cci: 缺少{col}列")
        cci = talib.CCI(df['high'].values, df['low'].values,
                        df['close'].values, timeperiod=n)
        return pd.Series(cci, index=df.index, name=f"CCI{n}")
    except Exception as e:
        idx = df.index if isinstance(df, pd.DataFrame) else None
        return pd.Series([float('nan')] * len(df), index=idx, name=f"CCI{n}") if idx is not None else None

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
    """通用调用ta-lib指标，自动适配参数，返回结果Series或DataFrame，异常时返回空DataFrame/Series"""
    try:
        if talib is None:
            raise ImportError('ta-lib库未安装')
        name = name.upper()
        if not hasattr(talib, name):
            raise ValueError(f'不支持的ta-lib指标: {name}')
        func = getattr(talib, name)
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
                if 'close' in df.columns:
                    call_args[k] = df['close'].values
        result = func(**call_args)
        if isinstance(result, tuple):
            cols = [f"{name}_{i+1}" for i in range(len(result))]
            return pd.DataFrame({col: v for col, v in zip(cols, result)}, index=df.index)
        else:
            return pd.Series(result, index=df.index, name=name)
    except Exception as e:
        if isinstance(df, pd.DataFrame):
            idx = df.index
            n = len(df)
        else:
            idx = None
            n = 0
        # 返回空DataFrame或全NaN
        return pd.DataFrame(index=idx) if idx is not None else pd.DataFrame()


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
