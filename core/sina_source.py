import re
import time
import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import threading
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from .data_source import DataSource, DataSourceType, DataFrequency, MarketDataType


class SinaDataSource(DataSource):
    """新浪财经数据源"""

    def __init__(self):
        super().__init__(DataSourceType.SINA)
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self._subscribed_symbols = set()
        self._update_thread = None
        self._running = False
        self._thread_pool = ThreadPoolExecutor(os.cpu_count() * 2)

    def _get_market_prefix(self, symbol: str) -> str:
        """获取市场前缀

        Args:
            symbol: 股票代码

        Returns:
            str: 市场前缀(sh/sz/bj)
        """
        if symbol.startswith(('600', '601', '603', '605', '688', '689')):
            return 'sh'
        elif symbol.startswith(('000', '001', '002', '003', '300', '301')):
            return 'sz'
        elif symbol.startswith(('4', '8', '43')):
            return 'bj'
        else:
            raise ValueError(f"不支持的股票代码: {symbol}")

    def connect(self) -> bool:
        """连接到数据源"""
        try:
            # 测试连接
            response = self._session.get(
                'http://hq.sinajs.cn/list=sh000001', timeout=5)
            if response.status_code == 200:
                self.logger.info("成功连接到新浪财经数据源")
                return True
            else:
                self.logger.error(f"连接新浪财经数据源失败: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"连接新浪财经数据源出错: {str(e)}")
            return False

    def disconnect(self) -> None:
        """断开数据源连接"""
        self._running = False
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join()
        self._session.close()
        self._thread_pool.shutdown()
        self.logger.info("已断开新浪财经数据源连接")

    def subscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        """订阅数据"""
        try:
            for symbol in symbols:
                self._subscribed_symbols.add(symbol)

            if not self._running:
                self._running = True
                self._update_thread = threading.Thread(
                    target=self._update_loop)
                self._update_thread.daemon = True
                self._update_thread.start()

            return True
        except Exception as e:
            self.logger.error(f"订阅数据失败: {str(e)}")
            return False

    def unsubscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        """取消订阅"""
        try:
            for symbol in symbols:
                self._subscribed_symbols.discard(symbol)
            return True
        except Exception as e:
            self.logger.error(f"取消订阅失败: {str(e)}")
            return False

    def get_kdata(self, symbol: str, freq: DataFrequency,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """获取K线数据"""
        try:
            market = self._get_market_prefix(symbol)
            symbol_with_market = f"{market}{symbol}"

            if freq == DataFrequency.DAY:
                url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol_with_market}"
                if start_date:
                    url += f"&start={start_date.strftime('%Y-%m-%d')}"
                if end_date:
                    url += f"&end={end_date.strftime('%Y-%m-%d')}"

                response = self._session.get(url, timeout=10)
                data = json.loads(response.text)

                df = pd.DataFrame(data)
                df['datetime'] = pd.to_datetime(df['day'])
                df = df.rename(columns={
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                })
                df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
                return df

            elif freq == DataFrequency.MIN5:
                url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol_with_market}&scale=5"
                if start_date:
                    url += f"&start={start_date.strftime('%Y-%m-%d %H:%M:%S')}"
                if end_date:
                    url += f"&end={end_date.strftime('%Y-%m-%d %H:%M:%S')}"

                response = self._session.get(url, timeout=10)
                data = json.loads(response.text)

                df = pd.DataFrame(data)
                df['datetime'] = pd.to_datetime(df['day'])
                df = df.rename(columns={
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                })
                df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
                return df
            else:
                raise ValueError(f"不支持的数据频率: {freq}")

        except Exception as e:
            self.logger.error(f"获取K线数据失败: {str(e)}")
            return pd.DataFrame()

    def get_real_time_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        try:
            symbol_list = []
            for symbol in symbols:
                market = self._get_market_prefix(symbol)
                symbol_list.append(f"{market}{symbol}")

            url = f"http://hq.sinajs.cn/list=" + ",".join(symbol_list)
            response = self._session.get(url, timeout=5)

            # 解析响应数据
            pattern = r'var hq_str_(?:sh|sz|bj)(\d+)="([^"]+)"'
            matches = re.findall(pattern, response.text)

            data = []
            for symbol, quote_str in matches:
                fields = quote_str.split(',')
                if len(fields) >= 32:
                    data.append({
                        'symbol': symbol,
                        'name': fields[0],
                        'open': float(fields[1]),
                        'close_prev': float(fields[2]),
                        'price': float(fields[3]),
                        'high': float(fields[4]),
                        'low': float(fields[5]),
                        'volume': float(fields[8]),
                        'amount': float(fields[9]),
                        'datetime': pd.to_datetime(f"{fields[30]} {fields[31]}")
                    })

            return pd.DataFrame(data)

        except Exception as e:
            self.logger.error(f"获取实时行情失败: {str(e)}")
            return pd.DataFrame()

    def _update_loop(self):
        """数据更新循环"""
        while self._running:
            try:
                if self._subscribed_symbols:
                    quotes = self.get_real_time_quotes(
                        list(self._subscribed_symbols))
                    if not quotes.empty:
                        self._notify_subscribers({
                            'type': 'quotes',
                            'data': quotes.to_dict('records')
                        })
            except Exception as e:
                self.logger.error(f"更新数据失败: {str(e)}")

            time.sleep(3)  # 3秒更新一次
