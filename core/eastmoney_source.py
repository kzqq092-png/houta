import json
import time
from datetime import datetime, timedelta
import requests
import pandas as pd
from typing import List, Optional, Dict
import threading

from .data_source import DataSource, DataSourceType, DataFrequency, MarketDataType


class EastMoneyDataSource(DataSource):
    """东方财富数据源"""

    def __init__(self):
        super().__init__(DataSourceType.EASTMONEY)
        self._session = requests.Session()
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self._base_url = "http://push2.eastmoney.com/api"
        self._quote_url = "http://push2.eastmoney.com/api/qt/stock/get"
        self._kline_url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        self._market_overview_url = "http://push2.eastmoney.com/api/qt/ulist.np/get"
        self._fund_flow_url = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"

        self._market_map = {
            "sh": 1,
            "sz": 0,
            "bj": 2
        }

        self._freq_map = {
            DataFrequency.MIN: "1",
            DataFrequency.MIN5: "5",
            DataFrequency.MIN15: "15",
            DataFrequency.MIN30: "30",
            DataFrequency.HOUR: "60",
            DataFrequency.DAY: "101",
            DataFrequency.WEEK: "102",
            DataFrequency.MONTH: "103"
        }

        self._subscribed_symbols = set()
        self._update_thread = None
        self._stop_event = threading.Event()

    def connect(self) -> bool:
        """连接到数据源"""
        try:
            # 测试连接
            response = self._session.get(
                f"{self._quote_url}?secid=1.000001&fields=f1,f2,f3,f4,f5",
                headers=self._headers
            )
            if response.status_code == 200:
                return True
            return False
        except Exception as e:
            self.logger.error(f"连接东方财富失败: {str(e)}")
            return False

    def disconnect(self) -> None:
        """断开数据源连接"""
        if self._update_thread and self._update_thread.is_alive():
            self._stop_event.set()
            self._update_thread.join()
        self._session.close()

    def subscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        """订阅数据"""
        try:
            self._subscribed_symbols.update(symbols)

            if not self._update_thread or not self._update_thread.is_alive():
                self._stop_event.clear()
                self._update_thread = threading.Thread(
                    target=self._update_loop,
                    args=(data_types,)
                )
                self._update_thread.daemon = True
                self._update_thread.start()

            return True
        except Exception as e:
            self.logger.error(f"订阅数据失败: {str(e)}")
            return False

    def unsubscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        """取消订阅"""
        try:
            self._subscribed_symbols.difference_update(symbols)
            return True
        except Exception as e:
            self.logger.error(f"取消订阅失败: {str(e)}")
            return False

    def get_kdata(self, symbol: str, freq: DataFrequency,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """获取K线数据"""
        try:
            market = self._get_market_code(symbol)
            freq_code = self._freq_map.get(freq, "101")

            params = {
                "secid": f"{market}.{symbol}",
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": freq_code,
                "fqt": "1",  # 前复权
                "beg": start_date.strftime("%Y%m%d") if start_date else "0",
                "end": end_date.strftime("%Y%m%d") if end_date else "20500101",
            }

            response = self._session.get(
                self._kline_url,
                params=params,
                headers=self._headers
            )

            if response.status_code != 200:
                self.logger.error(f"获取K线数据失败: HTTP {response.status_code}")
                return pd.DataFrame()

            data = response.json()
            if data["data"] is None:
                return pd.DataFrame()

            klines = data["data"]["klines"]
            records = []

            for line in klines:
                fields = line.split(",")
                records.append({
                    "datetime": pd.to_datetime(fields[0]),
                    "open": float(fields[1]),
                    "close": float(fields[2]),
                    "high": float(fields[3]),
                    "low": float(fields[4]),
                    "volume": float(fields[5]),
                    "amount": float(fields[6]),
                })

            return pd.DataFrame(records)

        except Exception as e:
            self.logger.error(f"获取K线数据失败: {str(e)}")
            return pd.DataFrame()

    def get_real_time_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        try:
            records = []
            for symbol in symbols:
                market = self._get_market_code(symbol)
                params = {
                    "secid": f"{market}.{symbol}",
                    "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
                }

                response = self._session.get(
                    self._quote_url,
                    params=params,
                    headers=self._headers
                )

                if response.status_code != 200:
                    continue

                data = response.json()
                if not data or "data" not in data:
                    continue

                quote = data["data"]
                records.append({
                    "symbol": symbol,
                    "name": quote.get("f58", ""),
                    "price": quote.get("f43", 0),
                    "open": quote.get("f46", 0),
                    "high": quote.get("f44", 0),
                    "low": quote.get("f45", 0),
                    "volume": quote.get("f47", 0),
                    "amount": quote.get("f48", 0),
                    "bid1": quote.get("f49", 0),
                    "ask1": quote.get("f50", 0),
                    "bid1_volume": quote.get("f51", 0),
                    "ask1_volume": quote.get("f52", 0),
                })

            return pd.DataFrame(records)

        except Exception as e:
            self.logger.error(f"获取实时行情失败: {str(e)}")
            return pd.DataFrame()

    def _update_loop(self, data_types: List[MarketDataType]):
        """更新循环"""
        while not self._stop_event.is_set():
            try:
                if MarketDataType.FUND_FLOW in data_types:
                    self._update_fund_flow()

                if self._subscribed_symbols and MarketDataType.TICK in data_types:
                    quotes = self.get_real_time_quotes(
                        list(self._subscribed_symbols))
                    if not quotes.empty:
                        self._notify_subscribers({
                            "type": MarketDataType.TICK,
                            "data": quotes
                        })

                time.sleep(2)  # 控制更新频率

            except Exception as e:
                self.logger.error(f"更新数据失败: {str(e)}")
                time.sleep(5)  # 出错后等待更长时间

    def _update_fund_flow(self):
        """更新资金流向数据"""
        try:
            for symbol in self._subscribed_symbols:
                market = self._get_market_code(symbol)
                params = {
                    "secid": f"{market}.{symbol}",
                    "fields1": "f1,f2,f3,f7",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
                    "klt": "1",
                    "lmt": "20"
                }

                response = self._session.get(
                    self._fund_flow_url,
                    params=params,
                    headers=self._headers
                )

                if response.status_code == 200:
                    data = response.json()
                    if data and "data" in data:
                        flow_data = {
                            "symbol": symbol,
                            # 主力净流入
                            "main_force_net": float(data["data"].get("f62", 0)),
                            # 散户净流入
                            "retail_net": float(data["data"].get("f63", 0)),
                            "timestamp": datetime.now()
                        }

                        self._notify_subscribers({
                            "type": MarketDataType.FUND_FLOW,
                            "data": flow_data
                        })

                time.sleep(0.5)  # 控制请求频率

        except Exception as e:
            self.logger.error(f"更新资金流向数据失败: {str(e)}")

    def _get_market_code(self, symbol: str) -> int:
        """获取市场代码"""
        if symbol.startswith("6"):
            return self._market_map["sh"]
        elif symbol.startswith("0") or symbol.startswith("3"):
            return self._market_map["sz"]
        elif symbol.startswith("8"):
            return self._market_map["bj"]
        else:
            raise ValueError(f"无效的股票代码: {symbol}")
