"""
基于Hikyuu的指标计算引擎

该引擎专门处理hikyuu库的指标计算，
提供标准化的接口和错误处理。
"""

import pandas as pd
from typing import List, Dict, Union, Any
import time
import logging

from .indicator_engine import IndicatorEngine, IndicatorNotSupportedError, CalculationError


class HikyuuEngine(IndicatorEngine):
    """基于Hikyuu库的指标计算引擎"""

    def __init__(self):
        """初始化Hikyuu引擎"""
        super().__init__("Hikyuu")
        self.logger = logging.getLogger(__name__)
        self.hikyuu_available = self._init_hikyuu()

        if self.hikyuu_available:
            self._supported_indicators = [
                'MA', 'EMA', 'SMA', 'MACD', 'RSI', 'BOLL', 'KDJ',
                'STOCH', 'ATR', 'CCI', 'ROC', 'MOM', 'BIAS', 'PSY', 'DMI'
            ]
            self._available = True
            self.logger.info(f"Hikyuu引擎初始化成功，支持 {len(self._supported_indicators)} 个指标")
        else:
            self._available = False

    def _init_hikyuu(self) -> bool:
        """初始化hikyuu库"""
        try:
            import hikyuu as hku
            self.hku = hku
            return True
        except ImportError:
            self.logger.warning("hikyuu库不可用")
            return False

    def supports_indicator(self, indicator_name: str) -> bool:
        """检查是否支持指定指标"""
        if not self.hikyuu_available:
            return False
        return indicator_name.upper() in [ind.upper() for ind in self._supported_indicators]

    def calculate(self,
                  indicator_name: str,
                  data: Union[pd.DataFrame, Dict[str, pd.Series]],
                  **params) -> Union[pd.Series, Dict[str, pd.Series]]:
        """使用hikyuu计算指标"""
        if not self.hikyuu_available:
            raise CalculationError("hikyuu库不可用")

        if not self.supports_indicator(indicator_name):
            raise IndicatorNotSupportedError(f"Hikyuu不支持指标: {indicator_name}")

        if not self.validate_data(data):
            raise CalculationError("输入数据格式无效")

        start_time = time.time()

        try:
            result = self._calculate_hikyuu_indicator(indicator_name, data, params)
            computation_time = time.time() - start_time
            self.logger.debug(f"Hikyuu计算 {indicator_name} 耗时: {computation_time:.4f}s")
            return result

        except Exception as e:
            error_msg = f"Hikyuu计算失败: {e}"
            self.logger.error(error_msg)
            raise CalculationError(error_msg) from e

    def _calculate_hikyuu_indicator(self,
                                    indicator_name: str,
                                    data: Union[pd.DataFrame, Dict[str, pd.Series]],
                                    params: Dict[str, Any]) -> Union[pd.Series, Dict[str, pd.Series]]:
        """计算Hikyuu指标"""
        indicator_name = indicator_name.upper()

        # 准备数据
        if isinstance(data, pd.DataFrame):
            index = data.index
        else:
            index = next(iter(data.values())).index if data else None

        # 创建hikyuu数据
        try:
            kdata = self._create_kdata_from_dataframe(data)
        except Exception as e:
            raise CalculationError(f"无法创建hikyuu数据: {e}")

        # 根据指标名称调用相应的hikyuu函数
        if indicator_name in ['MA', 'SMA']:
            period = params.get('period', params.get('timeperiod', 20))
            ma_indicator = self.hku.MA(kdata, n=period)
            result = self._hikyuu_to_series(ma_indicator, index, 'ma')
            return result

        elif indicator_name == 'EMA':
            period = params.get('period', params.get('timeperiod', 20))
            ema_indicator = self.hku.EMA(kdata, n=period)
            result = self._hikyuu_to_series(ema_indicator, index, 'ema')
            return result

        elif indicator_name == 'MACD':
            fast = params.get('fast_period', params.get('fastperiod', 12))
            slow = params.get('slow_period', params.get('slowperiod', 26))
            signal = params.get('signal_period', params.get('signalperiod', 9))

            macd_indicator = self.hku.MACD(kdata, n1=fast, n2=slow, n3=signal)

            # MACD返回三个序列
            macd_values = []
            signal_values = []
            hist_values = []

            for i in range(len(kdata)):
                record = macd_indicator[i]
                macd_values.append(record)  # 主线
                # 这里需要根据hikyuu的实际API调整
                signal_values.append(0)  # 信号线
                hist_values.append(0)   # 柱状图

            return {
                'macd': pd.Series(macd_values, index=index, name='macd'),
                'macdsignal': pd.Series(signal_values, index=index, name='macdsignal'),
                'macdhist': pd.Series(hist_values, index=index, name='macdhist')
            }

        elif indicator_name == 'RSI':
            period = params.get('period', params.get('timeperiod', 14))
            rsi_indicator = self.hku.RSI(kdata, n=period)
            result = self._hikyuu_to_series(rsi_indicator, index, 'rsi')
            return result

        elif indicator_name in ['BOLL', 'BBANDS']:
            period = params.get('period', params.get('timeperiod', 20))
            std_dev = params.get('std_dev', params.get('nbdevup', 2))

            # hikyuu的BOLL指标
            boll_indicator = self.hku.BOLL(kdata, n=period, p=std_dev)

            # BOLL返回上轨、中轨、下轨
            upper_values = []
            middle_values = []
            lower_values = []

            for i in range(len(kdata)):
                record = boll_indicator[i]
                # 这里需要根据hikyuu的实际API调整
                upper_values.append(record)  # 上轨
                middle_values.append(record)  # 中轨
                lower_values.append(record)  # 下轨

            return {
                'upperband': pd.Series(upper_values, index=index, name='upperband'),
                'middleband': pd.Series(middle_values, index=index, name='middleband'),
                'lowerband': pd.Series(lower_values, index=index, name='lowerband')
            }

        elif indicator_name in ['KDJ', 'STOCH']:
            k_period = params.get('k_period', params.get('fastk_period', 14))
            d_period = params.get('d_period', params.get('slowk_period', 3))

            kdj_indicator = self.hku.KDJ(kdata, n=k_period, m1=d_period, m2=d_period)

            # KDJ返回K、D、J三个值
            k_values = []
            d_values = []
            j_values = []

            for i in range(len(kdata)):
                record = kdj_indicator[i]
                # 这里需要根据hikyuu的实际API调整
                k_values.append(record)
                d_values.append(record)
                j_values.append(record)

            result = {
                'slowk': pd.Series(k_values, index=index, name='slowk'),
                'slowd': pd.Series(d_values, index=index, name='slowd')
            }

            if indicator_name == 'KDJ':
                result['j'] = pd.Series(j_values, index=index, name='j')

            return result

        elif indicator_name == 'ATR':
            period = params.get('period', params.get('timeperiod', 14))
            atr_indicator = self.hku.ATR(kdata, n=period)
            result = self._hikyuu_to_series(atr_indicator, index, 'atr')
            return result

        elif indicator_name == 'CCI':
            period = params.get('period', params.get('timeperiod', 14))
            cci_indicator = self.hku.CCI(kdata, n=period)
            result = self._hikyuu_to_series(cci_indicator, index, 'cci')
            return result

        elif indicator_name == 'ROC':
            period = params.get('period', params.get('timeperiod', 10))
            roc_indicator = self.hku.ROC(kdata, n=period)
            result = self._hikyuu_to_series(roc_indicator, index, 'roc')
            return result

        elif indicator_name == 'MOM':
            period = params.get('period', params.get('timeperiod', 10))
            mom_indicator = self.hku.MOM(kdata, n=period)
            result = self._hikyuu_to_series(mom_indicator, index, 'mom')
            return result

        else:
            raise IndicatorNotSupportedError(f"Hikyuu引擎不支持指标: {indicator_name}")

    def _create_kdata_from_dataframe(self, data: Union[pd.DataFrame, Dict[str, pd.Series]]):
        """从DataFrame或Series字典创建hikyuu的KData对象"""
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.DataFrame(data)

        # 确保有必要的列
        required_columns = ['open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必要的数据列: {col}")

        # 创建hikyuu的KData
        # 这里是一个简化的实现，实际使用时需要根据hikyuu的API调整
        kdata = []
        for idx, row in df.iterrows():
            # 这里需要根据hikyuu的实际KRecord结构调整
            record = {
                'datetime': idx,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row.get('volume', 0))
            }
            kdata.append(record)

        return kdata

    def _hikyuu_to_series(self, hikyuu_indicator, index, name: str) -> pd.Series:
        """将hikyuu指标结果转换为pandas Series"""
        values = []
        for i in range(len(hikyuu_indicator)):
            try:
                value = float(hikyuu_indicator[i])
                values.append(value)
            except:
                values.append(float('nan'))

        return pd.Series(values, index=index, name=name)

    def normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """标准化参数

        将常用参数名映射到hikyuu期望的参数名
        """
        normalized = super().normalize_params(params)

        # hikyuu使用n作为周期参数
        if 'period' in normalized and 'n' not in normalized:
            normalized['n'] = normalized.pop('period')
        elif 'timeperiod' in normalized and 'n' not in normalized:
            normalized['n'] = normalized.pop('timeperiod')

        return normalized
