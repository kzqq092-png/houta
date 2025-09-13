import hikyuu as hku
from typing import Dict, List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from core.data_source import DataSource, DataSourceType, MarketDataType, DataFrequency
from loguru import logger


class HikyuuDataSource(DataSource):
    """Hikyuu数据源"""

    def __init__(self):
        super().__init__(DataSourceType.HIKYUU)
        self._connected = False

    def connect(self) -> bool:
        try:
            if not self._connected:
                # 初始化hikyuu
                hku.init()
                self._connected = True
            return True
        except Exception as e:
            self.logger.error(f"连接Hikyuu失败: {str(e)}")
            return False

    def disconnect(self) -> None:
        self._connected = False

    def subscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        # Hikyuu是本地数据，不需要订阅
        return True

    def unsubscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        return True

    def get_kdata(self, symbol: str, freq: DataFrequency,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """获取K线数据"""
        try:
            stock = hku.getStock(symbol)
            ktype = self._convert_freq_to_ktype(freq)

            if not start_date:
                start_date = stock.start_datetime
            if not end_date:
                end_date = stock.last_datetime

            query = hku.Query(start_date, end_date, ktype)
            kdata = stock.get_kdata(query)
            return self._convert_kdata_to_df(kdata)
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {str(e)}")
            return pd.DataFrame()

    def get_real_time_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """获取实时行情（Hikyuu不支持实时行情）"""
        return pd.DataFrame()

    def _convert_freq_to_ktype(self, freq: DataFrequency) -> int:
        """转换频率到Hikyuu的KType"""
        freq_map = {
            DataFrequency.MIN: hku.Query.MIN,
            DataFrequency.MIN5: hku.Query.MIN5,
            DataFrequency.MIN15: hku.Query.MIN15,
            DataFrequency.MIN30: hku.Query.MIN30,
            DataFrequency.HOUR: hku.Query.MIN60,
            DataFrequency.DAY: hku.Query.DAY,
            DataFrequency.WEEK: hku.Query.WEEK,
            DataFrequency.MONTH: hku.Query.MONTH,
        }
        return freq_map.get(freq, hku.Query.DAY)

    def _convert_kdata_to_df(self, kdata) -> pd.DataFrame:
        """转换Hikyuu的K线数据到DataFrame"""
        data = {
            'datetime': [k.datetime for k in kdata],
            'open': [k.openPrice for k in kdata],
            'high': [k.highPrice for k in kdata],
            'low': [k.lowPrice for k in kdata],
            'close': [k.closePrice for k in kdata],
            'volume': [k.volume for k in kdata],
            'amount': [k.amount for k in kdata],
        }
        return pd.DataFrame(data)
