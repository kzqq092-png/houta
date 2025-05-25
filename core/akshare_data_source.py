import akshare as ak
import pandas as pd
from datetime import datetime
from typing import List, Optional
from .data_source import DataSource, DataSourceType, DataFrequency, MarketDataType
import logging


class AkshareDataSource(DataSource):
    """Akshare数据源"""

    def __init__(self):
        super().__init__(DataSourceType.LOCAL)
        self.logger = logging.getLogger("AkshareDataSource")

    def connect(self) -> bool:
        return True

    def disconnect(self) -> None:
        pass

    def subscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        return True

    def unsubscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        return True

    def get_kdata(self, symbol: str, freq: DataFrequency,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        # 这里只实现日线，其他频率可扩展
        try:
            if freq == DataFrequency.DAY:
                start = start_date.strftime(
                    "%Y%m%d") if start_date else "20100101"
                end = end_date.strftime(
                    "%Y%m%d") if end_date else datetime.now().strftime("%Y%m%d")
                df = ak.stock_zh_a_hist(
                    symbol=symbol, period="daily", start_date=start, end_date=end, adjust="")
                df.rename(columns={"日期": "datetime", "开盘": "open", "收盘": "close",
                          "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount"}, inplace=True)
                df["datetime"] = pd.to_datetime(df["datetime"])
                return df[["datetime", "open", "high", "low", "close", "volume", "amount"]]
            else:
                self.logger.warning(f"暂不支持的K线频率: {freq}")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Akshare获取K线数据失败: {str(e)}")
            return pd.DataFrame()

    def get_real_time_quotes(self, symbols: List[str]) -> pd.DataFrame:
        # 这里只做简单实现
        try:
            dfs = []
            for symbol in symbols:
                df = ak.stock_zh_a_spot(symbol=symbol)
                dfs.append(df)
            if dfs:
                return pd.concat(dfs, ignore_index=True)
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Akshare获取实时行情失败: {str(e)}")
            return pd.DataFrame()
