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

    def get_stock_sector_fund_flow_rank(self, indicator: str = "今日") -> pd.DataFrame:
        """获取股票板块资金流排行

        Args:
            indicator: 时间周期，支持 "今日", "3日", "5日", "10日", "20日"

        Returns:
            pd.DataFrame: 板块资金流排行数据
        """
        try:
            df = ak.stock_sector_fund_flow_rank(indicator=indicator)
            self.logger.info(f"获取板块资金流排行成功，数据条数: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"获取板块资金流排行失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_sector_fund_flow_summary(self, symbol: str, indicator: str = "今日") -> pd.DataFrame:
        """获取股票板块资金流汇总

        Args:
            symbol: 板块名称
            indicator: 时间周期，支持 "今日", "3日", "5日", "10日", "20日"

        Returns:
            pd.DataFrame: 板块资金流汇总数据
        """
        try:
            df = ak.stock_sector_fund_flow_summary(symbol=symbol, indicator=indicator)
            self.logger.info(f"获取板块资金流汇总成功，数据条数: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"获取板块资金流汇总失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_sector_fund_flow_hist(self, symbol: str, period: str = "近6月") -> pd.DataFrame:
        """获取股票板块历史资金流数据

        Args:
            symbol: 板块名称
            period: 时间周期，支持 "近6月", "近1年", "近2年", "近3年"

        Returns:
            pd.DataFrame: 板块历史资金流数据
        """
        try:
            df = ak.stock_sector_fund_flow_hist(symbol=symbol, period=period)
            self.logger.info(f"获取板块历史资金流成功，数据条数: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"获取板块历史资金流失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_individual_fund_flow_rank(self, indicator: str = "今日") -> pd.DataFrame:
        """获取个股资金流排行

        Args:
            indicator: 时间周期，支持 "今日", "3日", "5日", "10日", "20日"

        Returns:
            pd.DataFrame: 个股资金流排行数据
        """
        try:
            df = ak.stock_individual_fund_flow_rank(indicator=indicator)
            self.logger.info(f"获取个股资金流排行成功，数据条数: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"获取个股资金流排行失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_market_fund_flow(self) -> pd.DataFrame:
        """获取大盘资金流数据

        Returns:
            pd.DataFrame: 大盘资金流数据
        """
        try:
            df = ak.stock_market_fund_flow()
            self.logger.info(f"获取大盘资金流成功，数据条数: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"获取大盘资金流失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_main_fund_flow(self, indicator: str = "今日") -> pd.DataFrame:
        """获取主力资金流入排行

        Args:
            indicator: 时间周期，支持 "今日", "3日", "5日", "10日", "20日"

        Returns:
            pd.DataFrame: 主力资金流入排行数据
        """
        try:
            df = ak.stock_main_fund_flow(indicator=indicator)
            self.logger.info(f"获取主力资金流入排行成功，数据条数: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"获取主力资金流入排行失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_concept_fund_flow_hist(self, symbol: str, period: str = "近6月") -> pd.DataFrame:
        """获取概念历史资金流数据

        Args:
            symbol: 概念名称
            period: 时间周期，支持 "近6月", "近1年", "近2年", "近3年"

        Returns:
            pd.DataFrame: 概念历史资金流数据
        """
        try:
            df = ak.stock_concept_fund_flow_hist(symbol=symbol, period=period)
            self.logger.info(f"获取概念历史资金流成功，数据条数: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"获取概念历史资金流失败: {str(e)}")
            return pd.DataFrame()
