"""
同花顺数据源模块
"""
import pandas as pd
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from core.logger import LogManager


class TongHuaShunDataSource:
    """同花顺数据源类"""

    def __init__(self):
        """初始化同花顺数据源"""
        self.log_manager = LogManager()
        self.base_url = "http://d.10jqka.com.cn/v6/time/hs_{}/last"
        self.k_url = "http://d.10jqka.com.cn/v6/time/hs_{}/last"
        self.stock_list_url = "http://q.10jqka.com.cn/api/stock/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://stockpage.10jqka.com.cn/',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'Host': 'd.10jqka.com.cn'
        }

    def get_kdata(self, code: str, freq: str = 'D',
                  start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> pd.DataFrame:
        """获取K线数据

        Args:
            code: 股票代码
            freq: K线周期 ('D':日线, 'W':周线, 'M':月线, '60':60分钟, '30':30分钟, '15':15分钟, '5':5分钟)
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD

        Returns:
            pd.DataFrame: K线数据
        """
        try:
            # 标准化股票代码
            if code.startswith(('sh', 'sz', 'bj')):
                code = code[2:]

            # 转换周期格式
            freq_map = {
                'D': 'day',
                'W': 'week',
                'M': 'month',
                '60': 'min60',
                '30': 'min30',
                '15': 'min15',
                '5': 'min5',
                '1': 'min'
            }
            period = freq_map.get(freq, 'day')

            # 构建URL
            url = self.k_url.format(code)

            # 构建请求参数
            params = {
                'period': period
            }
            if start_date:
                params['start'] = start_date.replace('-', '')
            if end_date:
                params['end'] = end_date.replace('-', '')

            # 发送请求
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            # 解析数据
            try:
                data = response.json()
                if not data or 'data' not in data:
                    self.log_manager.warning(f"获取股票 {code} K线数据为空")
                    return pd.DataFrame()

                # 转换为DataFrame
                df = pd.DataFrame(data['data'])
                if df.empty:
                    return df

                # 重命名列
                df.columns = ['date', 'open', 'high',
                              'low', 'close', 'volume', 'amount']

                # 转换日期列
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)

                # 转换数值列
                numeric_cols = ['open', 'high', 'low',
                                'close', 'volume', 'amount']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # 过滤日期范围
                if start_date:
                    df = df[df.index >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df.index <= pd.to_datetime(end_date)]

                return df

            except ValueError as e:
                self.log_manager.error(f"解析K线数据失败: {str(e)}")
                return pd.DataFrame()

        except Exception as e:
            self.log_manager.error(f"获取股票 {code} K线数据失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_list(self, market: str = 'all') -> pd.DataFrame:
        """获取股票列表

        Args:
            market: 市场类型 ('all', 'sh', 'sz', 'bj')

        Returns:
            pd.DataFrame: 股票列表
        """
        try:
            # 构建请求参数
            params = {
                'market': market if market != 'all' else '',
                'type': 'stock'
            }

            # 设置请求头
            headers = self.headers.copy()
            headers['Host'] = 'q.10jqka.com.cn'

            # 发送请求
            response = requests.get(
                self.stock_list_url,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            # 解析数据
            try:
                data = response.json()
                if not data or 'data' not in data:
                    self.log_manager.warning("获取股票列表数据为空")
                    return pd.DataFrame()

                # 转换为DataFrame
                df = pd.DataFrame(data['data'])
                if df.empty:
                    return df

                # 重命名列
                column_map = {
                    'code': 'code',
                    'name': 'name',
                    'market': 'market',
                    'industry': 'industry'
                }
                df = df.rename(columns=column_map)

                # 确保必要的列存在
                required_cols = ['code', 'name', 'market', 'industry']
                for col in required_cols:
                    if col not in df.columns:
                        df[col] = ''

                # 标准化市场代码
                df['market'] = df['market'].map({
                    'SH': 'sh',
                    'SZ': 'sz',
                    'BJ': 'bj'
                }).fillna('other')

                # 添加完整的股票代码
                df['full_code'] = df.apply(
                    lambda x: f"{x['market']}{x['code']}", axis=1)

                return df

            except ValueError as e:
                self.log_manager.error(f"解析股票列表数据失败: {str(e)}")
                return pd.DataFrame()

        except Exception as e:
            self.log_manager.error(f"获取股票列表失败: {str(e)}")
            return pd.DataFrame()

    def get_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情

        Args:
            codes: 股票代码列表

        Returns:
            pd.DataFrame: 实时行情数据
        """
        try:
            # 构建请求参数
            params = {
                'codes': ','.join(codes)
            }

            # 发送请求
            response = requests.get(
                "http://d.10jqka.com.cn/v6/time/getRealtimeQuotes.php",
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            # 解析数据
            data = response.json()
            if not data or 'data' not in data:
                self.log_manager.error("获取实时行情失败: 数据格式错误")
                return pd.DataFrame()

            # 转换为DataFrame
            df = pd.DataFrame(data['data'])
            df.columns = ['code', 'name', 'price', 'change', 'change_pct',
                          'volume', 'amount', 'open', 'high', 'low', 'pre_close']

            return df

        except Exception as e:
            self.log_manager.error(f"获取实时行情失败: {str(e)}")
            return pd.DataFrame()

    def get_index_list(self) -> pd.DataFrame:
        """获取指数列表

        Returns:
            pd.DataFrame: 指数列表数据
        """
        try:
            # 发送请求
            response = requests.get(
                "http://d.10jqka.com.cn/v6/time/getIndexList.php",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            # 解析数据
            data = response.json()
            if not data or 'data' not in data:
                self.log_manager.error("获取指数列表失败: 数据格式错误")
                return pd.DataFrame()

            # 转换为DataFrame
            df = pd.DataFrame(data['data'])
            df.columns = ['code', 'name']

            return df

        except Exception as e:
            self.log_manager.error(f"获取指数列表失败: {str(e)}")
            return pd.DataFrame()

    def get_industry_list(self) -> pd.DataFrame:
        """获取行业列表

        Returns:
            pd.DataFrame: 行业列表数据
        """
        try:
            # 发送请求
            response = requests.get(
                "http://d.10jqka.com.cn/v6/time/getIndustryList.php",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            # 解析数据
            data = response.json()
            if not data or 'data' not in data:
                self.log_manager.error("获取行业列表失败: 数据格式错误")
                return pd.DataFrame()

            # 转换为DataFrame
            df = pd.DataFrame(data['data'])
            df.columns = ['code', 'name']

            return df

        except Exception as e:
            self.log_manager.error(f"获取行业列表失败: {str(e)}")
            return pd.DataFrame()

    def get_concept_list(self) -> pd.DataFrame:
        """获取概念列表

        Returns:
            pd.DataFrame: 概念列表数据
        """
        try:
            # 发送请求
            response = requests.get(
                "http://d.10jqka.com.cn/v6/time/getConceptList.php",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            # 解析数据
            data = response.json()
            if not data or 'data' not in data:
                self.log_manager.error("获取概念列表失败: 数据格式错误")
                return pd.DataFrame()

            # 转换为DataFrame
            df = pd.DataFrame(data['data'])
            df.columns = ['code', 'name']

            return df

        except Exception as e:
            self.log_manager.error(f"获取概念列表失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_info(self, code: str) -> Dict[str, Any]:
        """获取股票基本信息

        Args:
            code: 股票代码

        Returns:
            Dict[str, Any]: 股票基本信息
        """
        try:
            # 构建请求参数
            params = {
                'code': code
            }

            # 发送请求
            response = requests.get(
                "http://d.10jqka.com.cn/v6/time/getStockInfo.php",
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            # 解析数据
            data = response.json()
            if not data or 'data' not in data:
                self.log_manager.error(f"获取股票 {code} 基本信息失败: 数据格式错误")
                return {}

            return data['data']

        except Exception as e:
            self.log_manager.error(f"获取股票 {code} 基本信息失败: {str(e)}")
            return {}

    def get_market_sentiment(self) -> dict:
        """
        获取当前市场情绪数据，返回dict结构，包含sentiment_index等字段
        Returns:
            dict: 市场情绪数据
        """
        try:
            # 这里只能简单模拟，实际应根据同花顺API获取真实情绪数据
            # 以上证指数近30日涨跌家数比例为例
            code = '000001'
            df = self.get_kdata(code, freq='D')
            if df is None or df.empty or len(df) < 2:
                self.log_manager.warning("[TongHuaShun] 市场情绪K线数据为空或不足")
                return {
                    'sentiment_index': None,
                    'advance_decline': {'advance': None, 'decline': None, 'unchanged': None},
                    'volume_ratio': None,
                    'timestamp': datetime.now()
                }
            closes = df['close'].values[-30:]
            ups = sum([closes[i] > closes[i-1] for i in range(1, len(closes))])
            downs = sum([closes[i] < closes[i-1]
                        for i in range(1, len(closes))])
            total = len(closes) - 1
            sentiment_index = (ups / total) * 100 if total > 0 else 50
            result = {
                'sentiment_index': sentiment_index,
                'advance_decline': {'advance': int(ups), 'decline': int(downs), 'unchanged': int(total - ups - downs)},
                'volume_ratio': 1.0,
                'timestamp': datetime.now()
            }
            if 'sentiment_index' not in result:
                self.log_manager.warning("市场情绪数据无sentiment_index字段，已补None")
                result['sentiment_index'] = None
            return result
        except Exception as e:
            self.log_manager.error(f"TongHuaShun获取市场情绪失败: {str(e)}")
            return {
                'sentiment_index': None,
                'advance_decline': {'advance': None, 'decline': None, 'unchanged': None},
                'volume_ratio': None,
                'timestamp': datetime.now()
            }
