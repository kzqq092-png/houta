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

# --- ta-lib指标中英文映射表 ---
TA_LIB_CHINESE_MAP = {
    # 趋势类指标
    "MA": "移动平均线", "SMA": "简单移动平均", "EMA": "指数移动平均", "WMA": "加权移动平均",
    "DEMA": "双指数移动平均", "TEMA": "三指数移动平均", "TRIMA": "三角移动平均",
    "KAMA": "考夫曼自适应移动平均", "MAMA": "MESA自适应移动平均", "T3": "T3移动平均",
    "BBANDS": "布林带", "SAR": "抛物线转向", "SAREXT": "扩展抛物线转向",
    "MIDPOINT": "中点价", "MIDPRICE": "中间价", "HT_TRENDLINE": "希尔伯特变换趋势线",

    # 震荡类指标
    "MACD": "MACD指标", "MACDEXT": "扩展MACD", "MACDFIX": "固定MACD",
    "RSI": "相对强弱指标", "STOCH": "随机指标", "STOCHF": "快速随机指标", "STOCHRSI": "随机RSI",
    "CCI": "商品通道指标", "CMO": "钱德动量摆动指标", "DX": "方向性指标", "ADX": "平均方向性指标",
    "ADXR": "平均方向性指标评级", "MFI": "资金流量指标", "MOM": "动量指标", "ROC": "变动率指标",
    "ROCP": "变动率百分比", "ROCR": "变动率比率", "ROCR100": "变动率比率100", "TRIX": "三重指数平滑移动平均",
    "ULTOSC": "终极振荡器", "WILLR": "威廉指标", "BOP": "均势指标", "APO": "绝对价格振荡器",
    "PPO": "百分比价格振荡器", "MINUS_DI": "负方向指标", "MINUS_DM": "负方向移动",
    "PLUS_DI": "正方向指标", "PLUS_DM": "正方向移动", "AROON": "阿隆指标", "AROONOSC": "阿隆振荡器",
    "HT_DCPERIOD": "希尔伯特变换主导周期", "HT_DCPHASE": "希尔伯特变换主导周期相位",
    "HT_PHASOR": "希尔伯特变换相量", "HT_SINE": "希尔伯特变换正弦波",

    # 成交量类指标
    "OBV": "能量潮指标", "AD": "累积/派发线", "ADOSC": "累积/派发振荡器",

    # 波动性指标
    "ATR": "平均真实波幅", "NATR": "标准化平均真实波幅", "TRANGE": "真实波幅",

    # 价格变换
    "AVGPRICE": "平均价格", "MEDPRICE": "中位价格", "TYPPRICE": "典型价格", "WCLPRICE": "加权收盘价",

    # 数学变换
    "ACOS": "反余弦", "ASIN": "反正弦", "ATAN": "反正切", "CEIL": "向上取整", "COS": "余弦",
    "COSH": "双曲余弦", "EXP": "指数", "FLOOR": "向下取整", "LN": "自然对数", "LOG10": "常用对数",
    "SIN": "正弦", "SINH": "双曲正弦", "SQRT": "平方根", "TAN": "正切", "TANH": "双曲正切",
    "ADD": "加法", "DIV": "除法", "MAX": "最大值", "MAXINDEX": "最大值索引", "MIN": "最小值",
    "MININDEX": "最小值索引", "MINMAX": "最小最大值", "MINMAXINDEX": "最小最大值索引",
    "MULT": "乘法", "SUB": "减法", "SUM": "求和",

    # 统计函数
    "BETA": "贝塔系数", "CORREL": "皮尔逊相关系数", "LINEARREG": "线性回归", "LINEARREG_ANGLE": "线性回归角度",
    "LINEARREG_INTERCEPT": "线性回归截距", "LINEARREG_SLOPE": "线性回归斜率", "STDDEV": "标准差",
    "TSF": "时间序列预测", "VAR": "方差",

    # 形态识别指标（常用的）
    "CDL2CROWS": "两只乌鸦", "CDL3BLACKCROWS": "三只乌鸦", "CDL3INSIDE": "三内部",
    "CDL3LINESTRIKE": "三线打击", "CDL3OUTSIDE": "三外部", "CDL3STARSINSOUTH": "南方三星",
    "CDL3WHITESOLDIERS": "三白兵", "CDLABANDONEDBABY": "弃婴", "CDLADVANCEBLOCK": "前进阻挡",
    "CDLBELTHOLD": "捉腰带", "CDLBREAKAWAY": "脱离", "CDLCLOSINGMARUBOZU": "收盘缺影线",
    "CDLCONCEALBABYSWALL": "藏婴吞没", "CDLCOUNTERATTACK": "反击", "CDLDARKCLOUDCOVER": "乌云盖顶",
    "CDLDOJI": "十字星", "CDLDOJISTAR": "十字星", "CDLDRAGONFLYDOJI": "蜻蜓十字",
    "CDLENGULFING": "吞没", "CDLEVENINGDOJISTAR": "黄昏十字星", "CDLEVENINGSTAR": "黄昏之星",
    "CDLGAPSIDESIDEWHITE": "向上跳空并列阳线", "CDLGRAVESTONEDOJI": "墓碑十字",
    "CDLHAMMER": "锤头", "CDLHANGINGMAN": "上吊线", "CDLHARAMI": "母子线",
    "CDLHARAMICROSS": "十字母子线", "CDLHIGHWAVE": "长脚十字", "CDLHIKKAKE": "陷阱",
    "CDLHIKKAKEMOD": "修正陷阱", "CDLHOMINGPIGEON": "家鸽", "CDLIDENTICAL3CROWS": "相同三乌鸦",
    "CDLINNECK": "颈内线", "CDLINVERTEDHAMMER": "倒锤头", "CDLKICKING": "踢腿",
    "CDLKICKINGBYLENGTH": "长踢腿", "CDLLADDERBOTTOM": "梯底", "CDLLONGLEGGEDDOJI": "长腿十字",
    "CDLLONGLINE": "长线", "CDLMARUBOZU": "光头光脚", "CDLMATCHINGLOW": "相同低价",
    "CDLMATHOLD": "铺垫", "CDLMORNINGDOJISTAR": "早晨十字星", "CDLMORNINGSTAR": "早晨之星",
    "CDLONNECK": "颈上线", "CDLPIERCING": "刺透", "CDLRICKSHAWMAN": "黄包车夫",
    "CDLRISEFALL3METHODS": "上升/下降三法", "CDLSEPARATINGLINES": "分离线",
    "CDLSHOOTINGSTAR": "流星", "CDLSHORTLINE": "短线", "CDLSPINNINGTOP": "纺锤",
    "CDLSTALLEDPATTERN": "停顿形态", "CDLSTICKSANDWICH": "条形三明治", "CDLTAKURI": "探水竿",
    "CDLTASUKIGAP": "跳空并列阴阳线", "CDLTHRUSTING": "插入", "CDLTRISTAR": "三星",
    "CDLUNIQUE3RIVER": "奇特三河床", "CDLUPSIDEGAP2CROWS": "向上跳空的两只乌鸦",
    "CDLXSIDEGAP3METHODS": "跳空三法", "CDLSPINNINGTOP": "纺锤顶", "CDLHANGINGMAN": "上吊线",
    "CDLHAMMER": "锤子线", "CDLINVERTEDHAMMER": "倒锤子线", "CDLSHOOTINGSTAR": "射击之星",
    "CDLDOJI": "十字线", "CDLDRAGONFLYDOJI": "蜻蜓十字", "CDLGRAVESTONEDOJI": "墓碑十字",
    "CDLLONGLEGGEDDOJI": "长腿十字", "CDLRICKSHAWMAN": "人力车夫", "CDLENGULFING": "吞没形态",
    "CDLHARAMI": "孕线形态", "CDLHARAMICROSS": "十字孕线", "CDLPIERCING": "穿刺形态",
    "CDLDARKCLOUDCOVER": "乌云压顶", "CDLMORNINGSTAR": "启明星", "CDLEVENINGSTAR": "黄昏星",
    "CDLMORNINGDOJISTAR": "启明十字星", "CDLEVENINGDOJISTAR": "黄昏十字星",
    "CDLABANDONEDBABY": "弃婴形态", "CDLBELTHOLD": "腰带线", "CDLBREAKAWAY": "突破形态",
    "CDLCLOSINGMARUBOZU": "收盘光头", "CDLCONCEALBABYSWALL": "隐藏婴儿吞没",
    "CDLCOUNTERATTACK": "反击线", "CDLGAPSIDESIDEWHITE": "跳空并列白色",
    "CDLHIGHWAVE": "高波", "CDLHIKKAKE": "陷阱形态", "CDLHIKKAKEMOD": "修正陷阱",
    "CDLHOMINGPIGEON": "归巢鸽", "CDLIDENTICAL3CROWS": "相同三乌鸦",
    "CDLINNECK": "颈内线", "CDLKICKING": "踢腿形态", "CDLKICKINGBYLENGTH": "长踢腿",
    "CDLLADDERBOTTOM": "梯底", "CDLLONGLINE": "长线", "CDLMARUBOZU": "光头光脚",
    "CDLMATCHINGLOW": "匹配低点", "CDLMATHOLD": "垫子保持", "CDLONNECK": "颈上线",
    "CDLRISEFALL3METHODS": "上升下降三法", "CDLSEPARATINGLINES": "分离线",
    "CDLSHORTLINE": "短线", "CDLSTALLEDPATTERN": "停滞形态", "CDLSTICKSANDWICH": "棒状三明治",
    "CDLTAKURI": "探水竿", "CDLTASUKIGAP": "跳空并列阴阳", "CDLTHRUSTING": "推进线",
    "CDLTRISTAR": "三星", "CDLUNIQUE3RIVER": "独特三河", "CDLUPSIDEGAP2CROWS": "向上跳空两乌鸦",
    "CDLXSIDEGAP3METHODS": "跳空三法", "CDL3INSIDE": "三内部", "CDL3OUTSIDE": "三外部",
    "CDL3STARSINSOUTH": "南方三星", "CDL3WHITESOLDIERS": "三白兵", "CDL3BLACKCROWS": "三黑鸦",
    "CDL3LINESTRIKE": "三线打击", "CDLADVANCEBLOCK": "前进受阻", "CDL2CROWS": "两只乌鸦"
}


def get_talib_category(name: str) -> str:
    """根据ta-lib指标名返回专业分类"""
    if name.upper().startswith("CDL"):
        return "形态识别"
    return TA_LIB_CATEGORY_MAP.get(name.upper(), "其他")


def get_talib_chinese_name(name: str) -> str:
    """获取ta-lib指标的中文名称"""
    return TA_LIB_CHINESE_MAP.get(name.upper(), name)


def get_all_indicators_by_category(use_chinese: bool = True) -> dict:
    """
    返回所有ta-lib指标的分类字典，确保每个分类下有指标，分类名和主界面一致，类型为str
    Args:
        use_chinese: 是否使用中文名称显示指标
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

        # 根据参数决定使用中文名还是英文名
        display_name = get_talib_chinese_name(name) if use_chinese else name
        categories.setdefault(cat, []).append(str(display_name))

    # 只保留有指标的分类
    return {cat: names for cat, names in categories.items() if names}


def get_indicator_english_name(chinese_name: str) -> str:
    """根据中文名称获取英文名称，支持带括号的格式如'相对强弱指标(RSI)'"""
    # 如果包含括号，先尝试提取括号内的英文名称
    if '(' in chinese_name and ')' in chinese_name:
        # 提取括号内的内容
        bracket_content = chinese_name[chinese_name.find('(')+1:chinese_name.find(')')]
        # 如果括号内容是纯英文且在映射表中，直接返回
        if bracket_content.isalpha() and bracket_content.upper() in TA_LIB_CHINESE_MAP:
            return bracket_content.upper()

        # 否则提取括号前的中文部分进行匹配
        pure_chinese = chinese_name[:chinese_name.find('(')].strip()
        for eng_name, chn_name in TA_LIB_CHINESE_MAP.items():
            if chn_name == pure_chinese:
                return eng_name

    # 直接匹配完整名称
    for eng_name, chn_name in TA_LIB_CHINESE_MAP.items():
        if chn_name == chinese_name:
            return eng_name

    # 如果找不到，返回原名称
    return chinese_name


# --- ta-lib指标参数配置表 ---
TA_LIB_PARAMS_CONFIG = {
    # 趋势类指标
    "MA": {
        "params": {"timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "移动平均周期"}},
        "inputs": ["close"]
    },
    "SMA": {
        "params": {"timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "简单移动平均周期"}},
        "inputs": ["close"]
    },
    "EMA": {
        "params": {"timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "指数移动平均周期"}},
        "inputs": ["close"]
    },
    "WMA": {
        "params": {"timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "加权移动平均周期"}},
        "inputs": ["close"]
    },
    "DEMA": {
        "params": {"timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "双指数移动平均周期"}},
        "inputs": ["close"]
    },
    "TEMA": {
        "params": {"timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "三指数移动平均周期"}},
        "inputs": ["close"]
    },
    "TRIMA": {
        "params": {"timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "三角移动平均周期"}},
        "inputs": ["close"]
    },
    "KAMA": {
        "params": {"timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "考夫曼自适应移动平均周期"}},
        "inputs": ["close"]
    },
    "T3": {
        "params": {
            "timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "T3移动平均周期"},
            "vfactor": {"default": 0.7, "min": 0.0, "max": 1.0, "desc": "体积因子"}
        },
        "inputs": ["close"]
    },
    "BBANDS": {
        "params": {
            "timeperiod": {"default": 20, "min": 1, "max": 250, "desc": "布林带周期"},
            "nbdevup": {"default": 2.0, "min": 0.1, "max": 5.0, "desc": "上轨标准差倍数"},
            "nbdevdn": {"default": 2.0, "min": 0.1, "max": 5.0, "desc": "下轨标准差倍数"},
            "matype": {"default": 0, "min": 0, "max": 8, "desc": "移动平均类型"}
        },
        "inputs": ["close"]
    },
    "SAR": {
        "params": {
            "acceleration": {"default": 0.02, "min": 0.01, "max": 0.2, "desc": "加速因子"},
            "maximum": {"default": 0.2, "min": 0.1, "max": 1.0, "desc": "最大加速因子"}
        },
        "inputs": ["high", "low"]
    },
    "SAREXT": {
        "params": {
            "startvalue": {"default": 0.0, "min": 0.0, "max": 1.0, "desc": "起始值"},
            "offsetonreverse": {"default": 0.0, "min": 0.0, "max": 1.0, "desc": "反转偏移"},
            "accelerationinitlong": {"default": 0.02, "min": 0.01, "max": 0.2, "desc": "多头初始加速"},
            "accelerationlong": {"default": 0.02, "min": 0.01, "max": 0.2, "desc": "多头加速"},
            "accelerationmaxlong": {"default": 0.2, "min": 0.1, "max": 1.0, "desc": "多头最大加速"},
            "accelerationinitshort": {"default": 0.02, "min": 0.01, "max": 0.2, "desc": "空头初始加速"},
            "accelerationshort": {"default": 0.02, "min": 0.01, "max": 0.2, "desc": "空头加速"},
            "accelerationmaxshort": {"default": 0.2, "min": 0.1, "max": 1.0, "desc": "空头最大加速"}
        },
        "inputs": ["high", "low"]
    },

    # 震荡类指标
    "MACD": {
        "params": {
            "fastperiod": {"default": 12, "min": 1, "max": 50, "desc": "快线周期"},
            "slowperiod": {"default": 26, "min": 1, "max": 100, "desc": "慢线周期"},
            "signalperiod": {"default": 9, "min": 1, "max": 50, "desc": "信号线周期"}
        },
        "inputs": ["close"]
    },
    "MACDEXT": {
        "params": {
            "fastperiod": {"default": 12, "min": 1, "max": 50, "desc": "快线周期"},
            "fastmatype": {"default": 0, "min": 0, "max": 8, "desc": "快线MA类型"},
            "slowperiod": {"default": 26, "min": 1, "max": 100, "desc": "慢线周期"},
            "slowmatype": {"default": 0, "min": 0, "max": 8, "desc": "慢线MA类型"},
            "signalperiod": {"default": 9, "min": 1, "max": 50, "desc": "信号线周期"},
            "signalmatype": {"default": 0, "min": 0, "max": 8, "desc": "信号线MA类型"}
        },
        "inputs": ["close"]
    },
    "RSI": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "RSI周期"}},
        "inputs": ["close"]
    },
    "STOCH": {
        "params": {
            "fastk_period": {"default": 5, "min": 1, "max": 50, "desc": "快速K周期"},
            "slowk_period": {"default": 3, "min": 1, "max": 30, "desc": "慢速K周期"},
            "slowk_matype": {"default": 0, "min": 0, "max": 8, "desc": "慢速K MA类型"},
            "slowd_period": {"default": 3, "min": 1, "max": 30, "desc": "慢速D周期"},
            "slowd_matype": {"default": 0, "min": 0, "max": 8, "desc": "慢速D MA类型"}
        },
        "inputs": ["high", "low", "close"]
    },
    "STOCHF": {
        "params": {
            "fastk_period": {"default": 5, "min": 1, "max": 50, "desc": "快速K周期"},
            "fastd_period": {"default": 3, "min": 1, "max": 30, "desc": "快速D周期"},
            "fastd_matype": {"default": 0, "min": 0, "max": 8, "desc": "快速D MA类型"}
        },
        "inputs": ["high", "low", "close"]
    },
    "STOCHRSI": {
        "params": {
            "timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "RSI周期"},
            "fastk_period": {"default": 5, "min": 1, "max": 50, "desc": "快速K周期"},
            "fastd_period": {"default": 3, "min": 1, "max": 30, "desc": "快速D周期"},
            "fastd_matype": {"default": 0, "min": 0, "max": 8, "desc": "快速D MA类型"}
        },
        "inputs": ["close"]
    },
    "CCI": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "CCI周期"}},
        "inputs": ["high", "low", "close"]
    },
    "CMO": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "CMO周期"}},
        "inputs": ["close"]
    },
    "DX": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "DX周期"}},
        "inputs": ["high", "low", "close"]
    },
    "ADX": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "ADX周期"}},
        "inputs": ["high", "low", "close"]
    },
    "ADXR": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "ADXR周期"}},
        "inputs": ["high", "low", "close"]
    },
    "MFI": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "MFI周期"}},
        "inputs": ["high", "low", "close", "volume"]
    },
    "MOM": {
        "params": {"timeperiod": {"default": 10, "min": 1, "max": 100, "desc": "动量周期"}},
        "inputs": ["close"]
    },
    "ROC": {
        "params": {"timeperiod": {"default": 10, "min": 1, "max": 100, "desc": "变动率周期"}},
        "inputs": ["close"]
    },
    "ROCP": {
        "params": {"timeperiod": {"default": 10, "min": 1, "max": 100, "desc": "变动率百分比周期"}},
        "inputs": ["close"]
    },
    "ROCR": {
        "params": {"timeperiod": {"default": 10, "min": 1, "max": 100, "desc": "变动率比率周期"}},
        "inputs": ["close"]
    },
    "ROCR100": {
        "params": {"timeperiod": {"default": 10, "min": 1, "max": 100, "desc": "变动率比率100周期"}},
        "inputs": ["close"]
    },
    "TRIX": {
        "params": {"timeperiod": {"default": 30, "min": 1, "max": 100, "desc": "TRIX周期"}},
        "inputs": ["close"]
    },
    "ULTOSC": {
        "params": {
            "timeperiod1": {"default": 7, "min": 1, "max": 50, "desc": "第一周期"},
            "timeperiod2": {"default": 14, "min": 1, "max": 50, "desc": "第二周期"},
            "timeperiod3": {"default": 28, "min": 1, "max": 50, "desc": "第三周期"}
        },
        "inputs": ["high", "low", "close"]
    },
    "WILLR": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "威廉指标周期"}},
        "inputs": ["high", "low", "close"]
    },
    "BOP": {
        "params": {},
        "inputs": ["open", "high", "low", "close"]
    },
    "APO": {
        "params": {
            "fastperiod": {"default": 12, "min": 1, "max": 50, "desc": "快线周期"},
            "slowperiod": {"default": 26, "min": 1, "max": 100, "desc": "慢线周期"},
            "matype": {"default": 0, "min": 0, "max": 8, "desc": "移动平均类型"}
        },
        "inputs": ["close"]
    },
    "PPO": {
        "params": {
            "fastperiod": {"default": 12, "min": 1, "max": 50, "desc": "快线周期"},
            "slowperiod": {"default": 26, "min": 1, "max": 100, "desc": "慢线周期"},
            "matype": {"default": 0, "min": 0, "max": 8, "desc": "移动平均类型"}
        },
        "inputs": ["close"]
    },
    "AROON": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "阿隆指标周期"}},
        "inputs": ["high", "low"]
    },
    "AROONOSC": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "阿隆振荡器周期"}},
        "inputs": ["high", "low"]
    },

    # 成交量类指标
    "OBV": {
        "params": {},
        "inputs": ["close", "volume"]
    },
    "AD": {
        "params": {},
        "inputs": ["high", "low", "close", "volume"]
    },
    "ADOSC": {
        "params": {
            "fastperiod": {"default": 3, "min": 1, "max": 50, "desc": "快线周期"},
            "slowperiod": {"default": 10, "min": 1, "max": 100, "desc": "慢线周期"}
        },
        "inputs": ["high", "low", "close", "volume"]
    },

    # 波动性类指标
    "ATR": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "ATR周期"}},
        "inputs": ["high", "low", "close"]
    },
    "NATR": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "标准化ATR周期"}},
        "inputs": ["high", "low", "close"]
    },
    "TRANGE": {
        "params": {},
        "inputs": ["high", "low", "close"]
    },

    # 价格变换
    "AVGPRICE": {
        "params": {},
        "inputs": ["open", "high", "low", "close"]
    },
    "MEDPRICE": {
        "params": {},
        "inputs": ["high", "low"]
    },
    "TYPPRICE": {
        "params": {},
        "inputs": ["high", "low", "close"]
    },
    "WCLPRICE": {
        "params": {},
        "inputs": ["high", "low", "close"]
    },

    # 周期指标
    "HT_DCPERIOD": {
        "params": {},
        "inputs": ["close"]
    },
    "HT_DCPHASE": {
        "params": {},
        "inputs": ["close"]
    },
    "HT_PHASOR": {
        "params": {},
        "inputs": ["close"]
    },
    "HT_SINE": {
        "params": {},
        "inputs": ["close"]
    },
    "HT_TRENDMODE": {
        "params": {},
        "inputs": ["close"]
    },
    "HT_TRENDLINE": {
        "params": {},
        "inputs": ["close"]
    },

    # 数学变换
    "ACOS": {"params": {}, "inputs": ["close"]},
    "ASIN": {"params": {}, "inputs": ["close"]},
    "ATAN": {"params": {}, "inputs": ["close"]},
    "CEIL": {"params": {}, "inputs": ["close"]},
    "COS": {"params": {}, "inputs": ["close"]},
    "COSH": {"params": {}, "inputs": ["close"]},
    "EXP": {"params": {}, "inputs": ["close"]},
    "FLOOR": {"params": {}, "inputs": ["close"]},
    "LN": {"params": {}, "inputs": ["close"]},
    "LOG10": {"params": {}, "inputs": ["close"]},
    "SIN": {"params": {}, "inputs": ["close"]},
    "SINH": {"params": {}, "inputs": ["close"]},
    "SQRT": {"params": {}, "inputs": ["close"]},
    "TAN": {"params": {}, "inputs": ["close"]},
    "TANH": {"params": {}, "inputs": ["close"]},

    # 数学运算
    "ADD": {"params": {}, "inputs": ["close", "close"]},
    "DIV": {"params": {}, "inputs": ["close", "close"]},
    "MAX": {
        "params": {"timeperiod": {"default": 30, "min": 1, "max": 100, "desc": "最大值周期"}},
        "inputs": ["close"]
    },
    "MAXINDEX": {
        "params": {"timeperiod": {"default": 30, "min": 1, "max": 100, "desc": "最大值索引周期"}},
        "inputs": ["close"]
    },
    "MIN": {
        "params": {"timeperiod": {"default": 30, "min": 1, "max": 100, "desc": "最小值周期"}},
        "inputs": ["close"]
    },
    "MININDEX": {
        "params": {"timeperiod": {"default": 30, "min": 1, "max": 100, "desc": "最小值索引周期"}},
        "inputs": ["close"]
    },
    "MINMAX": {
        "params": {"timeperiod": {"default": 30, "min": 1, "max": 100, "desc": "最小最大值周期"}},
        "inputs": ["close"]
    },
    "MINMAXINDEX": {
        "params": {"timeperiod": {"default": 30, "min": 1, "max": 100, "desc": "最小最大值索引周期"}},
        "inputs": ["close"]
    },
    "MULT": {"params": {}, "inputs": ["close", "close"]},
    "SUB": {"params": {}, "inputs": ["close", "close"]},
    "SUM": {
        "params": {"timeperiod": {"default": 30, "min": 1, "max": 100, "desc": "求和周期"}},
        "inputs": ["close"]
    },

    # 统计函数
    "BETA": {
        "params": {"timeperiod": {"default": 5, "min": 1, "max": 100, "desc": "贝塔系数周期"}},
        "inputs": ["close", "close"]
    },
    "CORREL": {
        "params": {"timeperiod": {"default": 30, "min": 1, "max": 100, "desc": "相关系数周期"}},
        "inputs": ["close", "close"]
    },
    "LINEARREG": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "线性回归周期"}},
        "inputs": ["close"]
    },
    "LINEARREG_ANGLE": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "线性回归角度周期"}},
        "inputs": ["close"]
    },
    "LINEARREG_INTERCEPT": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "线性回归截距周期"}},
        "inputs": ["close"]
    },
    "LINEARREG_SLOPE": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "线性回归斜率周期"}},
        "inputs": ["close"]
    },
    "STDDEV": {
        "params": {
            "timeperiod": {"default": 5, "min": 1, "max": 100, "desc": "标准差周期"},
            "nbdev": {"default": 1.0, "min": 0.1, "max": 5.0, "desc": "标准差倍数"}
        },
        "inputs": ["close"]
    },
    "TSF": {
        "params": {"timeperiod": {"default": 14, "min": 1, "max": 100, "desc": "时间序列预测周期"}},
        "inputs": ["close"]
    },
    "VAR": {
        "params": {
            "timeperiod": {"default": 5, "min": 1, "max": 100, "desc": "方差周期"},
            "nbdev": {"default": 1.0, "min": 0.1, "max": 5.0, "desc": "标准差倍数"}
        },
        "inputs": ["close"]
    }
}

# 形态识别指标（CDL开头的指标）通常只需要penetration参数
CDL_INDICATORS = [
    "CDL2CROWS", "CDL3BLACKCROWS", "CDL3INSIDE", "CDL3LINESTRIKE", "CDL3OUTSIDE",
    "CDL3STARSINSOUTH", "CDL3WHITESOLDIERS", "CDLABANDONEDBABY", "CDLADVANCEBLOCK",
    "CDLBELTHOLD", "CDLBREAKAWAY", "CDLCLOSINGMARUBOZU", "CDLCONCEALBABYSWALL",
    "CDLCOUNTERATTACK", "CDLDARKCLOUDCOVER", "CDLDOJI", "CDLDOJISTAR",
    "CDLDRAGONFLYDOJI", "CDLENGULFING", "CDLEVENINGDOJISTAR", "CDLEVENINGSTAR",
    "CDLGAPSIDESIDEWHITE", "CDLGRAVESTONEDOJI", "CDLHAMMER", "CDLHANGINGMAN",
    "CDLHARAMI", "CDLHARAMICROSS", "CDLHIGHWAVE", "CDLHIKKAKE", "CDLHIKKAKEMOD",
    "CDLHOMINGPIGEON", "CDLIDENTICAL3CROWS", "CDLINNECK", "CDLINVERTEDHAMMER",
    "CDLKICKING", "CDLKICKINGBYLENGTH", "CDLLADDERBOTTOM", "CDLLONGLEGGEDDOJI",
    "CDLLONGLINE", "CDLMARUBOZU", "CDLMATCHINGLOW", "CDLMATHOLD",
    "CDLMORNINGDOJISTAR", "CDLMORNINGSTAR", "CDLONNECK", "CDLPIERCING",
    "CDLRICKSHAWMAN", "CDLRISEFALL3METHODS", "CDLSEPARATINGLINES",
    "CDLSHOOTINGSTAR", "CDLSHORTLINE", "CDLSPINNINGTOP", "CDLSTALLEDPATTERN",
    "CDLSTICKSANDWICH", "CDLTAKURI", "CDLTASUKIGAP", "CDLTHRUSTING",
    "CDLTRISTAR", "CDLUNIQUE3RIVER", "CDLUPSIDEGAP2CROWS", "CDLXSIDEGAP3METHODS"
]

# 为形态识别指标添加配置
for cdl_indicator in CDL_INDICATORS:
    TA_LIB_PARAMS_CONFIG[cdl_indicator] = {
        "params": {"penetration": {"default": 0.3, "min": 0.0, "max": 1.0, "desc": "穿透率"}},
        "inputs": ["open", "high", "low", "close"]
    }


def get_indicator_params_config(indicator_name: str) -> dict:
    """获取指标的参数配置"""
    return TA_LIB_PARAMS_CONFIG.get(indicator_name.upper(), {})


def get_indicator_default_params(indicator_name: str) -> dict:
    """获取指标的默认参数"""
    config = get_indicator_params_config(indicator_name)
    if not config or "params" not in config:
        return {}

    default_params = {}
    for param_name, param_config in config["params"].items():
        default_params[param_name] = param_config["default"]

    return default_params


def get_indicator_inputs(indicator_name: str) -> list:
    """获取指标需要的输入数据类型"""
    config = get_indicator_params_config(indicator_name)
    return config.get("inputs", ["close"])


__all__ = [
    'calc_ma', 'calc_macd', 'calc_rsi', 'calc_kdj', 'calc_boll', 'calc_atr', 'calc_obv', 'calc_cci',
    'get_talib_indicator_list', 'calc_talib_indicator', 'get_talib_category', 'get_all_indicators_by_category',
    'get_indicator_english_name', 'get_talib_chinese_name', 'get_indicator_params_config',
    'get_indicator_default_params', 'get_indicator_inputs', 'TA_LIB_PARAMS_CONFIG'
]
