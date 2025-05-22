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

    def get_market_sentiment(self) -> dict:
        """
        获取A股市场情绪指数（中证市场情绪指数）
        Returns:
            dict: 市场情绪数据，包含sentiment_index、date、csi300等
        """
        try:
            df = ak.index_news_sentiment_scope()
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                sentiment_index = latest.get("市场情绪指数", None)
                date = latest.get("日期", None)
                csi300 = latest.get("沪深300", None)
                return {
                    "sentiment_index": float(sentiment_index) if sentiment_index is not None else None,
                    "date": date,
                    "csi300": float(csi300) if csi300 is not None else None,
                    "timestamp": datetime.now()
                }
            else:
                return self._empty_sentiment()
        except Exception as e:
            self.logger.error(f"Akshare获取市场情绪失败: {str(e)}")
            return self._empty_sentiment()

    def _empty_sentiment(self):
        return {
            "sentiment_index": None,
            "date": None,
            "csi300": None,
            "timestamp": datetime.now()
        }

    def get_market_sentiment_history(self, days: int = 30, code: str = "000001", industry: str = None, concept: str = None, custom_stocks: list = None) -> list:
        """
        获取近N天的市场情绪历史数据（中证市场情绪指数）
        Args:
            days: 天数，默认30天
            code: 指数代码，默认上证指数（此处akshare接口只支持全市场情绪）
            industry: 行业名称，暂不支持
            concept: 概念板块名称，暂不支持
            custom_stocks: 自选股代码列表，暂不支持
        Returns:
            list: 每项为dict，包含date和sentiment_index
        """
        try:
            df = ak.index_news_sentiment_scope()
            if df is not None and not df.empty:
                # 只取最近days天
                df = df.tail(days)
                result = []
                for _, row in df.iterrows():
                    result.append({
                        "date": row.get("日期"),
                        "sentiment_index": float(row.get("市场情绪指数", None)) if row.get("市场情绪指数", None) is not None else None,
                        "csi300": float(row.get("沪深300", None)) if row.get("沪深300", None) is not None else None
                    })
                return result
            else:
                return []
        except Exception as e:
            self.logger.error(f"Akshare获取历史市场情绪失败: {str(e)}")
            return []
