"""
数据管理模块

提供数据加载、缓存和管理功能
"""

import pandas as pd
from typing import Dict, Any, Optional, List, Set
from core.base_logger import BaseLogManager

# 安全导入hikyuu模块
try:
    import hikyuu as hku
    from hikyuu.interactive import *
    HIKYUU_AVAILABLE = True
    print("✅ HIkyuu模块导入成功")
except ImportError as e:
    print(f"⚠️ HIkyuu模块导入失败: {e}")
    print("将使用模拟数据模式运行")
    hku = None
    HIKYUU_AVAILABLE = False
import traceback
from datetime import datetime, timedelta
from core.eastmoney_source import EastMoneyDataSource
from core.sina_source import SinaDataSource
from core.tonghuashun_source import TongHuaShunDataSource
import numpy as np
from utils.cache import Cache
import time
import sqlite3
import os
from core.industry_manager import IndustryManager
from utils.log_util import log_structured
import asyncio
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtCore import QObject, pyqtSignal, QThread
# import ptvsd
from utils.performance_monitor import measure_performance

DB_PATH = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'db', 'hikyuu_system.db')


class DataManager:
    """基于sqlite的数据管理器"""

    def __init__(self, log_manager=None):
        self.conn = sqlite3.connect(DB_PATH)
        self.log_manager = log_manager
        self.cache_manager = Cache()  # 兼容原有缓存机制
        self._current_source = 'hikyuu' if HIKYUU_AVAILABLE else 'mock'  # 默认数据源，兼容原有逻辑

        # 安全初始化hikyuu StockManager
        if HIKYUU_AVAILABLE:
            try:
                self.sm = sm  # hikyuu的StockManager实例
            except NameError:
                print("⚠️ hikyuu StockManager不可用，将使用模拟模式")
                self.sm = None
                self._current_source = 'mock'
        else:
            self.sm = None

        self._data_sources = {}  # 兼容多数据源逻辑
        self.industry_manager = IndustryManager(
            log_manager=self.log_manager)  # 行业管理器

        # 添加异步处理支持
        self._async_executor = ThreadPoolExecutor(max_workers=4)
        self._data_loading_queue = asyncio.Queue() if hasattr(asyncio, 'Queue') else None

        # 自动加载和更新行业数据
        try:
            log_structured(self.log_manager, "load_industry_cache",
                           level="info", status="start")
            self.industry_manager.load_cache()
            log_structured(self.log_manager, "load_industry_cache",
                           level="info", status="end")
            log_structured(self.log_manager, "update_industry_data",
                           level="info", status="start")
            self.industry_manager.update_industry_data()
            log_structured(self.log_manager, "update_industry_data",
                           level="info", status="end")
            log_structured(self.log_manager, "industry_init",
                           level="info", status="success")
        except Exception as e:
            if self.log_manager:
                log_structured(self.log_manager, "industry_init",
                               level="warning", status="fail", error=str(e))

    async def get_k_data_async(self, code: str, freq: str = 'D',
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               query: Optional[Any] = None,
                               **kwargs) -> pd.DataFrame:
        """异步获取K线数据，避免阻塞UI线程

        Args:
            code: 股票代码
            freq: 频率
            start_date: 开始日期
            end_date: 结束日期
            query: 查询对象
            **kwargs: 其他参数

        Returns:
            pd.DataFrame: K线数据
        """
        try:
            # 首先检查缓存
            cache_key = f"kdata_{code}_{freq}_{start_date}_{end_date}_{str(query)}"
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None and not cached_data.empty:
                if 'code' not in cached_data.columns:
                    cached_data = cached_data.copy()
                    cached_data['code'] = code
                return cached_data

            # 使用线程池执行同步的数据获取操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._async_executor,
                self.get_k_data,
                code, freq, start_date, end_date, query
            )

            return result

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"异步获取K线数据失败: {str(e)}")
            return pd.DataFrame()

    async def get_stock_list_async(self, market: str = 'all') -> pd.DataFrame:
        """异步获取股票列表

        Args:
            market: 市场类型

        Returns:
            pd.DataFrame: 股票列表
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._async_executor,
                self.get_stock_list,
                market
            )
            return result
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"异步获取股票列表失败: {str(e)}")
            return pd.DataFrame()

    async def get_realtime_quotes_async(self, codes: List[str]) -> pd.DataFrame:
        """异步获取实时行情

        Args:
            codes: 股票代码列表

        Returns:
            pd.DataFrame: 实时行情数据
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._async_executor,
                self.get_realtime_quotes,
                codes
            )
            return result
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"异步获取实时行情失败: {str(e)}")
            return pd.DataFrame()

    def preload_data(self, codes: List[str], freq: str = 'D', priority: int = 1):
        """预加载数据到缓存

        Args:
            codes: 股票代码列表
            freq: 频率
            priority: 优先级 (1=高, 2=中, 3=低)
        """
        try:
            # 创建预加载任务
            for code in codes:
                cache_key = f"kdata_{code}_{freq}_None_None_None"
                if not self.cache_manager.get(cache_key):
                    # 只预加载缓存中没有的数据
                    self._async_executor.submit(
                        self._preload_single_stock,
                        code, freq, priority
                    )
        except Exception as e:
            if self.log_manager:
                self.log_manager.warning(f"预加载数据失败: {str(e)}")

    def _preload_single_stock(self, code: str, freq: str, priority: int):
        """预加载单个股票数据"""
        try:
            # 根据优先级调整处理
            if priority > 2:
                time.sleep(0.1)  # 低优先级任务稍作延迟

            data = self.get_k_data(code, freq)
            if not data.empty:
                if self.log_manager:
                    self.log_manager.debug(f"预加载完成: {code}")
        except Exception as e:
            if self.log_manager:
                self.log_manager.warning(f"预加载股票 {code} 失败: {str(e)}")


class AsyncDataManagerWrapper(QObject):
    """异步数据管理器包装器，提供Qt信号支持"""

    data_loaded = pyqtSignal(str, object)  # code, data
    error_occurred = pyqtSignal(str, str)  # code, error_message
    progress_updated = pyqtSignal(int, str)  # progress, message

    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.data_manager = data_manager
        self._load_tasks = {}  # 跟踪加载任务

    def load_data_async(self, code: str, freq: str = 'D',
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None):
        """异步加载数据并发出信号"""

        class LoadWorker(QThread):
            finished = pyqtSignal(str, object)
            error = pyqtSignal(str, str)
            progress = pyqtSignal(int, str)

            def __init__(self, data_manager, code, freq, start_date, end_date):
                super().__init__()
                self.data_manager = data_manager
                self.code = code
                self.freq = freq
                self.start_date = start_date
                self.end_date = end_date

            @measure_performance("LoadWorker.run")
            def run(self):
                try:
                    self.progress.emit(10, f"开始加载 {self.code} 数据...")

                    data = self.data_manager.get_k_data(
                        self.code, self.freq, self.start_date, self.end_date
                    )

                    self.progress.emit(100, f"加载 {self.code} 完成")
                    self.finished.emit(self.code, data)

                except Exception as e:
                    self.error.emit(self.code, str(e))

        # 创建并启动工作线程
        worker = LoadWorker(self.data_manager, code,
                            freq, start_date, end_date)
        worker.finished.connect(self.data_loaded.emit)
        worker.error.connect(self.error_occurred.emit)
        worker.progress.connect(self.progress_updated.emit)

        # 保存任务引用，防止被垃圾回收
        self._load_tasks[code] = worker
        worker.finished.connect(lambda: self._load_tasks.pop(code, None))
        worker.error.connect(lambda: self._load_tasks.pop(code, None))

        worker.start()

    def cancel_loading(self, code: str):
        """取消加载任务"""
        if code in self._load_tasks:
            worker = self._load_tasks[code]
            if worker.isRunning():
                worker.terminate()
                worker.wait()
            self._load_tasks.pop(code, None)

    def get_config(self, key: str, default=None):
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM config WHERE key=?', (key,))
        row = cursor.fetchone()
        if row:
            import json
            try:
                return json.loads(row[0])
            except Exception:
                return row[0]
        return default

    def set_config(self, key: str, value):
        value_str = json.dumps(value, ensure_ascii=False)
        cursor = self.conn.cursor()
        cursor.execute(
            'REPLACE INTO config (key, value) VALUES (?, ?)', (key, value_str))
        self.conn.commit()

    def get_data_source(self):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT name, type, config, is_active FROM data_source WHERE is_active=1')
        row = cursor.fetchone()
        if row:
            config = json.loads(row[2]) if row[2] else {}
            # 防御性：config必须为dict
            if not isinstance(config, dict):
                config = {}
            return {'name': row[0], 'type': row[1], 'config': config, 'is_active': row[3]}
        return None

    def set_data_source(self, name: str):
        # 类型检查，防止传入非字符串
        if not isinstance(name, str):
            raise TypeError(f"set_data_source期望字符串，实际为{type(name)}")
        cursor = self.conn.cursor()
        cursor.execute('UPDATE data_source SET is_active=0')
        cursor.execute(
            'UPDATE data_source SET is_active=1 WHERE name=?', (name,))
        self.conn.commit()

    def get_stock_list(self):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT code, name, market_code, type, valid, start_date, end_date, industry_id, extra FROM stock')
        rows = cursor.fetchall()
        columns = ['code', 'name', 'market', 'type', 'valid',
                   'start_date', 'end_date', 'industry_id', 'extra']
        return pd.DataFrame(rows, columns=columns)

    def get_industry_list(self):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT id, name, parent_id, level, extra FROM industry')
        rows = cursor.fetchall()
        columns = ['id', 'name', 'parent_id', 'level', 'extra']
        return pd.DataFrame(rows, columns=columns)

    def get_market_list(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, code, region, extra FROM market')
        rows = cursor.fetchall()
        columns = ['id', 'name', 'code', 'region', 'extra']
        return pd.DataFrame(rows, columns=columns)

    def get_concept_list(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT code, name, extra FROM concept')
        rows = cursor.fetchall()
        columns = ['code', 'name', 'extra']
        return pd.DataFrame(rows, columns=columns)

    def get_indicator_list(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT name, category, params, extra FROM indicator')
        rows = cursor.fetchall()
        columns = ['name', 'category', 'params', 'extra']
        return pd.DataFrame(rows, columns=columns)

    def get_favorites(self, user_id: str, fav_type: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT fav_key, fav_value FROM user_favorites WHERE user_id=? AND fav_type=?', (user_id, fav_type))
        rows = cursor.fetchall()
        return rows

    def add_favorite(self, user_id: str, fav_type: str, fav_key: str, fav_value: str):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO user_favorites (user_id, fav_type, fav_key, fav_value) VALUES (?, ?, ?, ?)',
                       (user_id, fav_type, fav_key, fav_value))
        self.conn.commit()

    def remove_favorite(self, user_id: str, fav_type: str, fav_key: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM user_favorites WHERE user_id=? AND fav_type=? AND fav_key=?', (user_id, fav_type, fav_key))
        self.conn.commit()

    def _init_market_industry_data(self):
        """初始化市场和行业数据"""
        try:
            # 初始化市场映射
            market_data = {
                'SH': {'name': '上海证券交易所', 'code': 'SH', 'prefix': ['600', '601', '603', '605', '688']},
                'SZ': {'name': '深圳证券交易所', 'code': 'SZ', 'prefix': ['000', '001', '002', '003', '300']},
                'BJ': {'name': '北京证券交易所', 'code': 'BJ', 'prefix': ['8', '430']},
                'HK': {'name': '港股通', 'code': 'HK', 'prefix': ['9']},
                'US': {'name': '美股', 'code': 'US', 'prefix': ['7']}
            }
            self.cache_manager.set('market_data', market_data)

            # 初始化市场和行业股票集合
            market_stocks = {}
            industry_stocks = {}
            industry_data = {}

            # 遍历所有股票，更新市场和行业数据
            for stock in sm:
                try:
                    if not stock.valid:
                        continue

                    market = stock.market
                    code = stock.code

                    # 更新市场股票集合
                    if market not in market_stocks:
                        market_stocks[market] = set()
                    market_stocks[market].add(code)

                    # 从行业管理器获取行业信息
                    try:
                        industry_info = self.industry_manager.get_industry(
                            code)
                        if industry_info:
                            industry = industry_info.get(
                                'csrc_industry', '') or industry_info.get('exchange_industry', '')
                            if industry:
                                # 处理多级行业
                                industry_levels = industry.split('/')
                                for i, level in enumerate(industry_levels):
                                    level = level.strip()
                                    if level:
                                        # 创建行业层级结构
                                        if i == 0:  # 主行业
                                            if level not in industry_data:
                                                industry_data[level] = {
                                                    'sub_industries': set(),
                                                    'stocks': set()
                                                }
                                            industry_data[level]['stocks'].add(
                                                code)
                                        elif i == 1:  # 子行业
                                            main_industry = industry_levels[0].strip(
                                            )
                                            if main_industry in industry_data:
                                                industry_data[main_industry]['sub_industries'].add(
                                                    level)
                                                if level not in industry_stocks:
                                                    industry_stocks[level] = set(
                                                    )
                                                industry_stocks[level].add(
                                                    code)
                    except Exception as e:
                        log_structured(self.log_manager, "get_industry_info",
                                       level="warning", status="fail", error=str(e))
                        continue

                except Exception as e:
                    log_structured(self.log_manager, "process_stock_data",
                                   level="warning", status="fail", error=f"{code} - {str(e)}")
                    continue

            # 缓存市场和行业数据
            self.cache_manager.set('market_stocks', market_stocks)
            self.cache_manager.set('industry_stocks', industry_stocks)
            self.cache_manager.set('industry_data', industry_data)

            log_structured(self.log_manager, "market_industry_init", level="info", status="success",
                           count=len(market_data), industry_count=len(industry_data))

        except Exception as e:
            log_structured(self.log_manager, "market_industry_init",
                           level="error", status="fail", error=str(e))
            log_structured(self.log_manager, "traceback",
                           level="error", error=traceback.format_exc())

    def get_markets(self) -> Dict[str, Dict]:
        """获取所有市场数据

        Returns:
            市场数据字典
        """
        return self.cache_manager.get('market_data') or {}

    def get_industries(self) -> Dict[str, Dict]:
        """获取所有行业数据

        Returns:
            行业数据字典
        """
        return self.cache_manager.get('industry_data') or {}

    def get_market_stocks(self, market: str) -> Set[str]:
        """获取指定市场的所有股票

        Args:
            market: 市场代码

        Returns:
            股票代码集合
        """
        market_stocks = self.cache_manager.get('market_stocks') or {}
        return market_stocks.get(market, set()).copy()

    def get_industry_stocks(self, industry: str) -> Set[str]:
        """获取指定行业的所有股票

        Args:
            industry: 行业名称

        Returns:
            股票代码集合
        """
        industry_stocks = self.cache_manager.get('industry_stocks') or {}
        return industry_stocks.get(industry, set()).copy()

    def get_sub_industries(self, main_industry: str) -> Set[str]:
        """获取主行业的所有子行业

        Args:
            main_industry: 主行业名称

        Returns:
            子行业名称集合
        """
        industry_data = self.cache_manager.get('industry_data') or {}
        industry_info = industry_data.get(main_industry, {})
        return industry_info.get('sub_industries', set()).copy()

    def _convert_hikyuu_datetime(self, dt) -> str:
        """转换Hikyuu的Datetime对象为标准日期字符串

        Args:
            dt: Hikyuu的Datetime对象

        Returns:
            str: 标准日期字符串，格式：YYYY-MM-DD
        """
        try:
            if hasattr(dt, 'number'):
                n = int(dt.number)
                if n == 0:
                    return None
                s = str(n)
                return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
            elif isinstance(dt, (datetime, pd.Timestamp)):
                return dt.strftime('%Y-%m-%d')
            return str(dt)
        except Exception as e:
            log_structured(self.log_manager, "convert_date",
                           level="warning", error=str(e))
            return None

    def _standardize_kdata_format(self, df: pd.DataFrame, code: str) -> pd.DataFrame:
        """标准化K线数据格式，统一处理所有数据源的返回格式

        Args:
            df: 原始DataFrame
            code: 股票代码

        Returns:
            pd.DataFrame: 标准化后的DataFrame，datetime作为索引
        """
        if df is None or df.empty:
            return df

        df_copy = df.copy()

        # 处理datetime字段
        datetime_col_name = None
        datetime_in_index = False

        # 检查datetime是否在列中
        for col in ['datetime', 'date', 'time', 'timestamp']:
            if col in df_copy.columns:
                datetime_col_name = col
                break

        # 检查datetime是否在索引中
        if datetime_col_name is None and isinstance(df_copy.index, pd.DatetimeIndex):
            datetime_in_index = True
        elif datetime_col_name is None and hasattr(df_copy.index, 'name') and df_copy.index.name in ['datetime', 'date', 'time']:
            datetime_in_index = True

        # 如果datetime既不在列中也不在索引中，尝试从索引推断
        if datetime_col_name is None and not datetime_in_index:
            try:
                # 尝试将索引转换为datetime
                df_copy.index = pd.to_datetime(df_copy.index)
                datetime_in_index = True
            except:
                # 如果无法转换，添加默认datetime列
                self.log_manager.warning(f"股票 {code} 无法推断datetime字段，使用默认日期")
                df_copy['datetime'] = pd.date_range(
                    start='2020-01-01', periods=len(df_copy), freq='D')
                datetime_col_name = 'datetime'

        # 标准化列名映射
        column_mapping = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'vol': 'volume',  # 兼容性映射
            'amount': 'amount',
            'amt': 'amount',  # 兼容性映射
            'turnover': 'amount'  # 兼容性映射
        }

        # 重命名列
        for old_name, new_name in column_mapping.items():
            if old_name in df_copy.columns and old_name != new_name:
                df_copy = df_copy.rename(columns={old_name: new_name})

        # 确保datetime作为索引
        if datetime_col_name and not datetime_in_index:
            # datetime在列中，需要设置为索引
            df_copy[datetime_col_name] = pd.to_datetime(
                df_copy[datetime_col_name])
            df_copy = df_copy.set_index(datetime_col_name)
        elif not datetime_in_index:
            # 既不在列中也不在索引中，这种情况已经在上面处理了
            pass

        # 确保索引名称为datetime
        if df_copy.index.name != 'datetime':
            df_copy.index.name = 'datetime'

        # 确保必要的数值列存在并转换为数值类型
        required_numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_numeric_cols:
            if col not in df_copy.columns:
                if col == 'volume' and 'vol' in df_copy.columns:
                    df_copy[col] = df_copy['vol']
                elif col == 'amount' and 'amt' in df_copy.columns:
                    df_copy[col] = df_copy['amt']
                else:
                    # 为缺失的列填充默认值
                    if col == 'volume':
                        df_copy[col] = 0
                    elif col == 'amount':
                        df_copy[col] = df_copy.get(
                            'close', 0) * df_copy.get('volume', 0)
                    else:
                        df_copy[col] = df_copy.get('close', 0)  # 用收盘价填充其他价格字段

            # 转换为数值类型
            if col in df_copy.columns:
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')

        # 添加amount列（如果不存在）
        if 'amount' not in df_copy.columns:
            df_copy['amount'] = df_copy['close'] * df_copy['volume']

        # 确保code字段存在
        if 'code' not in df_copy.columns:
            df_copy['code'] = code

        # 数据清洗
        df_copy = df_copy.replace([np.inf, -np.inf], np.nan)
        df_copy = df_copy.dropna(subset=['close'])  # 至少要有收盘价

        # 按时间排序
        df_copy = df_copy.sort_index()

        return df_copy

    def get_k_data(self, code: str, freq: str = 'D',
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   query: Optional[Any] = None,
                   **kwargs) -> pd.DataFrame:
        start_time = time.time()
        self.log_manager.info(
            f"[DataManager.get_k_data] 开始: code={code}, freq={freq}, start_date={start_date}, end_date={end_date}")
        try:
            # 检查股票代码格式
            if not code or not isinstance(code, str):
                self.log_manager.error("股票代码不能为空且必须为字符串")
                return pd.DataFrame()

            # 标准化股票代码格式
            if not code.startswith(('sh', 'sz', 'bj')):
                if code.startswith('6'):
                    code = f'sh{code}'
                elif code.startswith(('0', '3')):
                    code = f'sz{code}'
                elif code.startswith('8'):
                    code = f'bj{code}'

            # 生成缓存键
            cache_key = f"kdata_{code}_{freq}_{start_date}_{end_date}_{str(query)}"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                if not cached_data.empty:
                    if 'code' not in cached_data.columns:
                        cached_data = cached_data.copy()
                        cached_data['code'] = code
                    return cached_data
                else:
                    self.log_manager.warning(f"缓存中的K线数据为空: {code}")

            # 根据当前数据源获取数据
            df = pd.DataFrame()

            try:
                if self._current_source == 'hikyuu':
                    if not hasattr(self, 'sm') or self.sm is None:
                        self.log_manager.error("StockManager(sm)未初始化")
                        return pd.DataFrame()
                    stock = self.sm[code]
                    if not stock.valid:
                        self.log_manager.warning(f"股票 {code} 无效")
                        return pd.DataFrame()

                    # 转换周期格式
                    freq_map = {
                        'D': Query.DAY,
                        'W': Query.WEEK,
                        'M': Query.MONTH,
                        '60': Query.MIN60,
                        '30': Query.MIN30,
                        '15': Query.MIN15,
                        '5': Query.MIN5,
                        '1': Query.MIN
                    }
                    ktype = freq_map.get(freq, Query.DAY)

                    # 兼容hikyuu Query对象或负数天数
                    if query is not None:
                        if isinstance(query, int) and query < 0:
                            query_obj = Query(query, ktype=ktype)
                        else:
                            query_obj = query
                    elif start_date and end_date:
                        query_obj = Query(start_date, end_date, ktype)
                    elif start_date:
                        query_obj = Query(
                            start_date, datetime.now().strftime('%Y-%m-%d'), ktype)
                    elif end_date:
                        query_obj = Query(-9999, end_date, ktype)
                    else:
                        query_obj = Query(-365, ktype=ktype)  # 默认获取一年数据

                    kdata = stock.get_kdata(query_obj)
                    if kdata is None or len(kdata) == 0:
                        self.log_manager.warning(f"获取股票 {code} 的K线数据为空")
                        return pd.DataFrame()

                    # 转换Hikyuu的K线数据
                    dates = [self._convert_hikyuu_datetime(
                        k.datetime) for k in kdata]
                    df = pd.DataFrame({
                        'datetime': dates,
                        'open': [float(k.open) for k in kdata],
                        'high': [float(k.high) for k in kdata],
                        'low': [float(k.low) for k in kdata],
                        'close': [float(k.close) for k in kdata],
                        'volume': [float(k.volume) for k in kdata],
                        'amount': [float(k.amount) for k in kdata]
                    })

                    # 移除无效日期
                    df = df.dropna(subset=['datetime'])
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df.set_index('datetime', inplace=True)

                    # 自动补全 code 字段
                    if 'code' not in df.columns:
                        df['code'] = code

                elif self._current_source == 'eastmoney':
                    if 'eastmoney' not in self._data_sources or not hasattr(self._data_sources['eastmoney'], 'get_kdata'):
                        self.log_manager.error("eastmoney数据源未初始化或无get_kdata方法")
                        return pd.DataFrame()
                    df = self._data_sources['eastmoney'].get_kdata(
                        code, freq, start_date, end_date)

                elif self._current_source == 'sina':
                    if 'sina' not in self._data_sources or not hasattr(self._data_sources['sina'], 'get_kdata'):
                        self.log_manager.error("sina数据源未初始化或无get_kdata方法")
                        return pd.DataFrame()
                    df = self._data_sources['sina'].get_kdata(
                        code, freq, start_date, end_date)

                elif self._current_source == 'tonghuashun':
                    if 'tonghuashun' not in self._data_sources or not hasattr(self._data_sources['tonghuashun'], 'get_kdata'):
                        self.log_manager.error(
                            "tonghuashun数据源未初始化或无get_kdata方法")
                        return pd.DataFrame()
                    df = self._data_sources['tonghuashun'].get_kdata(
                        code, freq, start_date, end_date)

                # 验证数据完整性
                if df is None or df.empty:
                    self.log_manager.warning(f"获取股票 {code} 的K线数据为空")
                    return pd.DataFrame()

                # 使用新的标准化函数处理数据格式
                df = self._standardize_kdata_format(df, code)

                # 重新验证标准化后的数据
                if df is None or df.empty:
                    self.log_manager.warning(f"股票 {code} 的K线数据标准化后为空")
                    return pd.DataFrame()

                # 修改验证逻辑：检查datetime是否在索引中或列中
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                has_datetime = False

                # 检查datetime是否存在（在索引中或列中）
                if isinstance(df.index, pd.DatetimeIndex) or (hasattr(df.index, 'name') and df.index.name == 'datetime'):
                    has_datetime = True
                elif 'datetime' in df.columns:
                    has_datetime = True

                if not has_datetime:
                    self.log_manager.warning(f"股票 {code} 的K线数据缺少datetime字段")
                    return pd.DataFrame()

                # 检查其他必要列
                missing_columns = [
                    col for col in required_columns if col not in df.columns]
                if missing_columns:
                    self.log_manager.warning(
                        f"股票 {code} 的K线数据缺少必要列: {missing_columns}")
                    return pd.DataFrame()

                # 数据清洗（已在标准化函数中处理，这里保留兼容性）
                df = df.replace([np.inf, -np.inf], np.nan)
                df = df.dropna(subset=['close'])  # 至少要有收盘价

                # 自动补全 code 字段（已在标准化函数中处理，这里保留兼容性）
                if 'code' not in df.columns:
                    df['code'] = code

                # 缓存数据
                self.cache_manager.set(cache_key, df)

                # 记录数据范围
                if not df.empty:
                    self.log_manager.info(
                        f"成功获取股票 {code} 的K线数据， 时间范围: {df.index[0]} 至 {df.index[-1]}，共 {len(df)} 条记录")

                return df

            except Exception as source_error:
                self.log_manager.error(
                    f"从数据源 {self._current_source} 获取K线数据失败: {str(source_error)}")
                # 尝试切换到备用数据源
                for source in self.get_available_sources():
                    if source != self._current_source:
                        try:
                            self.log_manager.info(f"尝试使用备用数据源 {source}")
                            old_source = self._current_source
                            self._current_source = source
                            df = self.get_k_data(
                                code, freq, start_date, end_date, query=query)
                            if 'code' not in df.columns:
                                df['code'] = code
                            if not df.empty:
                                return df
                            self._current_source = old_source
                        except Exception as e:
                            self.log_manager.error(
                                f"备用数据源 {source} 获取K线数据失败: {str(e)}")
                            continue
                return pd.DataFrame()
        except Exception as e:
            self.log_manager.error(f"获取K线数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return pd.DataFrame()
        finally:
            elapsed = int((time.time() - start_time) * 1000)
            self.log_manager.performance(
                f"[DataManager.get_k_data] 结束，耗时: {elapsed} ms")

    def get_stock_list(self, market: str = 'all') -> pd.DataFrame:
        """获取股票列表

        Args:
            market: 市场类型 ('all', 'sh', 'sz', 'bj')

        Returns:
            pd.DataFrame: 股票列表数据
        """
        try:
            cache_key = f"stock_list_{market}"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                stocks = []
                for stock in sm:
                    if not stock.valid:
                        continue

                    # 根据market参数过滤
                    if market != 'all':
                        if market.lower() != stock.market.lower():
                            continue

                    # 获取行业信息
                    industry = getattr(stock, 'industry', None)
                    if not industry:
                        try:
                            industry_info = self.industry_manager.get_industry(
                                stock.code)
                            if industry_info:
                                industry = (industry_info.get('csrc_industry') or
                                            industry_info.get('exchange_industry') or
                                            industry_info.get('industry'))
                        except Exception as e:
                            self.log_manager.warning(
                                f"获取股票 {stock.code} 行业信息失败: {str(e)}")

                    stock_info = {
                        'code': stock.code,
                        'name': stock.name,
                        'market': stock.market,
                        'type': stock.type,
                        'valid': stock.valid,
                        'start_date': str(stock.start_datetime) if stock.start_datetime else None,
                        'end_date': str(stock.last_datetime) if stock.last_datetime else None,
                        'industry': industry or '其他'
                    }
                    stocks.append(stock_info)

                df = pd.DataFrame(stocks)

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_stock_list(market)
                # 补充行业信息
                if not df.empty and 'code' in df.columns:
                    df['industry'] = df.apply(
                        lambda x: self._get_industry(x['code']), axis=1)

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_stock_list(market)
                # 补充行业信息
                if not df.empty and 'code' in df.columns:
                    df['industry'] = df.apply(
                        lambda x: self._get_industry(x['code']), axis=1)

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_stock_list(market)
                # 补充行业信息
                if not df.empty and 'code' in df.columns:
                    df['industry'] = df.apply(
                        lambda x: self._get_industry(x['code']), axis=1)

            # 确保行业列存在
            if not df.empty and 'industry' not in df.columns:
                df['industry'] = '其他'

            # 缓存数据
            self.cache_manager.set(cache_key, df)

            return df

        except Exception as e:
            self.log_manager.error(f"获取股票列表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return pd.DataFrame()

    def _get_industry(self, code: str) -> str:
        """获取股票行业信息

        Args:
            code: 股票代码

        Returns:
            行业名称
        """
        try:
            industry_info = self.industry_manager.get_industry(code)
            if industry_info:
                return (industry_info.get('csrc_industry') or
                        industry_info.get('exchange_industry') or
                        industry_info.get('industry') or
                        '其他')
            return '其他'
        except Exception as e:
            self.log_manager.warning(f"获取股票 {code} 行业信息失败: {str(e)}")
            return '其他'

    def get_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情

        Args:
            codes: 股票代码列表

        Returns:
            pd.DataFrame: 实时行情数据
        """
        try:
            cache_key = f"realtime_{'_'.join(codes)}"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                quotes = [hku.Stock(code).get_realtime_quote()
                          for code in codes]
                df = pd.DataFrame(quotes)

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_realtime_quotes(codes)

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_realtime_quotes(codes)

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_realtime_quotes(
                    codes)

            # 缓存数据（实时行情缓存时间较短）
            self.cache_manager.set(cache_key, df, ttl=60)  # 60秒缓存

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
            cache_key = "index_list"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                indices = hku.get_index_list()
                df = pd.DataFrame({
                    'code': [i.code for i in indices],
                    'name': [i.name for i in indices]
                })

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_index_list()

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_index_list()

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_index_list()

            # 缓存数据
            self.cache_manager.set(cache_key, df)

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
            cache_key = "industry_list"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                industries = hku.get_industry_list()
                df = pd.DataFrame({
                    'code': [i.code for i in industries],
                    'name': [i.name for i in industries]
                })

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_industry_list()

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_industry_list()

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_industry_list()

            # 缓存数据
            self.cache_manager.set(cache_key, df)

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
            cache_key = "concept_list"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                concepts = hku.get_concept_list()
                df = pd.DataFrame({
                    'code': [c.code for c in concepts],
                    'name': [c.name for c in concepts]
                })

            elif self._current_source == 'eastmoney':
                df = self._data_sources['eastmoney'].get_concept_list()

            elif self._current_source == 'sina':
                df = self._data_sources['sina'].get_concept_list()

            elif self._current_source == 'tonghuashun':
                df = self._data_sources['tonghuashun'].get_concept_list()

            # 缓存数据
            self.cache_manager.set(cache_key, df)

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
            cache_key = f"stock_info_{code}"

            # 尝试从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 根据当前数据源获取数据
            if self._current_source == 'hikyuu':
                stock = sm[code]
                info = {
                    'code': stock.code,
                    'name': stock.name,
                    'market': stock.market,
                    'type': stock.type,
                    'valid': stock.valid,
                    'start_date': stock.start_datetime,
                    'last_date': stock.last_datetime
                }

            elif self._current_source == 'eastmoney':
                info = self._data_sources['eastmoney'].get_stock_info(code)

            elif self._current_source == 'sina':
                info = self._data_sources['sina'].get_stock_info(code)

            elif self._current_source == 'tonghuashun':
                info = self._data_sources['tonghuashun'].get_stock_info(code)

            # 缓存数据
            self.cache_manager.set(cache_key, info)

            return info

        except Exception as e:
            self.log_manager.error(f"获取股票基本信息失败: {str(e)}")
            return {}

    def set_data_source(self, source: str) -> None:
        """设置数据源

        Args:
            source: 数据源名称 ("hikyuu", "eastmoney", "sina", "tonghuashun")
        """
        try:
            self.log_manager.info(f"设置数据源: {source}")

            # 清除缓存
            self.clear_cache()

            # 更新数据源
            self._current_source = source

            # 重新初始化数据源相关配置
            if source == "eastmoney":
                from .eastmoney_source import EastMoneyDataSource
                self._data_sources['eastmoney'] = EastMoneyDataSource()
            elif source == "sina":
                from .sina_source import SinaDataSource
                self._data_sources['sina'] = SinaDataSource()
            elif source == "tonghuashun":
                from .tonghuashun_source import TongHuaShunDataSource
                self._data_sources['tonghuashun'] = TongHuaShunDataSource()
            else:  # 默认使用 Hikyuu
                from .hikyuu_source import HikyuuDataSource
                self._data_sources['hikyuu'] = HikyuuDataSource()

            # 初始化数据源
            self._data_sources[source].init()

            self.log_manager.info(f"数据源设置完成: {source}")

        except Exception as e:
            error_msg = f"设置数据源失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            raise

    def clear_cache(self) -> None:
        """清除所有缓存数据"""
        try:
            self.cache_manager.clear()
            self.log_manager.info("缓存已清除")
        except Exception as e:
            error_msg = f"清除缓存失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            raise

    def get_current_source(self) -> str:
        """获取当前数据源类型"""
        return self._current_source

    def get_available_sources(self) -> List[str]:
        """获取所有可用的数据源类型"""
        try:
            # 检查每个数据源是否可用
            available_sources = []
            for source_type, source in self._data_sources.items():
                try:
                    if source_type == 'hikyuu':
                        if source is not None:
                            test_data = source.Stock(
                                'sh000001').get_kdata(Query(-1))
                            if test_data is not None:
                                available_sources.append(source_type)
                    else:
                        if source is not None:
                            test_data = source.get_stock_list()
                            if test_data is not None:
                                available_sources.append(source_type)
                except:
                    continue
            return available_sources
        except Exception as e:
            self.log_manager.error(f"获取可用数据源失败: {str(e)}")
            return list(self._data_sources.keys())

    def _on_industry_data_updated(self):
        """处理行业数据更新事件"""
        try:
            # 清除缓存
            self.cache_manager.clear()

            # 重新初始化市场和行业数据
            self._init_market_industry_data()

            self.log_manager.info("行业数据更新完成")

        except Exception as e:
            self.log_manager.error(f"处理行业数据更新失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _init_data_sources(self) -> None:
        """初始化所有数据源"""
        try:
            # 初始化 Hikyuu 数据源
            try:
                from core.hikyuu_source import HikyuuDataSource
                self._data_sources['hikyuu'] = HikyuuDataSource()
                self.log_manager.info("Hikyuu数据源初始化成功")
            except Exception as e:
                self.log_manager.warning(f"Hikyuu数据源初始化失败: {str(e)}")

            # 初始化东方财富数据源
            try:
                self._data_sources['eastmoney'] = EastMoneyDataSource()
                self.log_manager.info("东方财富数据源初始化成功")
            except Exception as e:
                self.log_manager.warning(f"东方财富数据源初始化失败: {str(e)}")

            # 初始化新浪数据源
            try:
                self._data_sources['sina'] = SinaDataSource()
                self.log_manager.info("新浪数据源初始化成功")
            except Exception as e:
                self.log_manager.warning(f"新浪数据源初始化失败: {str(e)}")

            # 初始化同花顺数据源
            try:
                self._data_sources['tonghuashun'] = TongHuaShunDataSource()
                self.log_manager.info("同花顺数据源初始化成功")
            except Exception as e:
                self.log_manager.warning(f"同花顺数据源初始化失败: {str(e)}")

            # 初始化Akshare数据源
            try:
                from .akshare_data_source import AkshareDataSource
                self._data_sources['akshare'] = AkshareDataSource()
                self.log_manager.info("Akshare数据源初始化成功")
            except Exception as e:
                self.log_manager.warning(f"Akshare数据源初始化失败: {str(e)}")

        except Exception as e:
            self.log_manager.error(f"初始化数据源失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _test_data_source(self, source_name: str) -> bool:
        """测试数据源是否可用

        Args:
            source_name: 数据源名称

        Returns:
            bool: 数据源是否可用
        """
        try:
            source = self._data_sources.get(source_name)
            if not source:
                return False

            # 尝试获取上证指数数据
            if source_name == 'hikyuu':
                test_data = source.Stock('sh000001').get_kdata(Query(-1))
                return test_data is not None and not test_data.empty
            else:
                test_data = source.get_kdata('sh000001', 'D')
                return test_data is not None and not test_data.empty

        except Exception as e:
            self.log_manager.warning(f"测试数据源 {source_name} 失败: {str(e)}")
            return False

    def _get_backup_source(self) -> Optional[str]:
        """获取备用数据源

        Returns:
            str: 备用数据源名称，如果没有可用的备用数据源则返回 None
        """
        try:
            # 按优先级尝试不同的数据源
            priority_list = ['hikyuu', 'eastmoney', 'sina', 'tonghuashun']
            for source_name in priority_list:
                if source_name != self._current_source and self._test_data_source(source_name):
                    return source_name
            return None

        except Exception as e:
            self.log_manager.error(f"获取备用数据源失败: {str(e)}")
            return None

    def get_custom_stocks(self) -> list:
        """
        获取自选股代码列表（可根据实际存储方式调整）
        Returns:
            list: 自选股代码
        """
        # TODO: 实现自选股存储与读取，这里用演示数据
        return ["000001", "600519", "300750"]

    def get_concept_stocks(self, concept: str) -> list:
        """
        获取指定概念的成分股代码列表
        Args:
            concept: 概念名称
        Returns:
            list: 成分股代码
        """
        try:
            # 优先从缓存获取
            cache_key = f"concept_stocks_{concept}"
            cached = self.cache_manager.get(cache_key)
            if cached is not None:
                return cached
            # 尝试从行业管理器获取
            if hasattr(self, 'industry_manager') and hasattr(self.industry_manager, 'industry_data'):
                result = []
                for code, info in self.industry_manager.industry_data.items():
                    # 概念可能在exchange_industry或sectors/concept
                    if info.get('exchange_industry') and concept in info['exchange_industry']:
                        result.append(code)
                    elif 'sectors' in info and 'concept' in info['sectors'] and concept in info['sectors']['concept']:
                        result.append(code)
                if result:
                    self.cache_manager.set(cache_key, result)
                    return result
            # 兜底：尝试从数据源获取
            if hasattr(self, '_data_sources') and 'eastmoney' in self._data_sources:
                try:
                    em = self._data_sources['eastmoney']
                    if hasattr(em, 'get_concept_members'):
                        result = em.get_concept_members(concept)
                        if result:
                            self.cache_manager.set(cache_key, result)
                            return result
                except Exception:
                    pass
            return []
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.warning(f"获取概念成分股失败: {str(e)}")
            return []

    def get_market_day_info(self, date, code=None, industry=None, concept=None, custom_stocks=None) -> dict:
        """
        获取指定日期的行情摘要（自选股/指数/行业/概念）
        Args:
            date: 日期
            code: 指数代码
            industry: 行业名称
            concept: 概念板块名称
            custom_stocks: 自选股代码列表
        Returns:
            dict: 行情摘要
        """
        try:
            if custom_stocks:
                # 获取自选股当日行情
                result = {}
                for code_ in custom_stocks:
                    df = self.get_k_data(code_, start_date=str(date)[
                                         :10], end_date=str(date)[:10])
                    if not df.empty:
                        row = df.iloc[0]
                        result[code_] = {"close": row["close"], "pct_chg": (
                            row["close"]-row["open"])/row["open"]*100}
                return result
            elif concept:
                # 获取概念成分股当日行情
                stock_list = list(self.get_concept_stocks(concept))
                result = {}
                for code_ in stock_list:
                    df = self.get_k_data(code_, start_date=str(date)[
                                         :10], end_date=str(date)[:10])
                    if not df.empty:
                        row = df.iloc[0]
                        result[code_] = {"close": row["close"], "pct_chg": (
                            row["close"]-row["open"])/row["open"]*100}
                return result
            elif industry:
                stock_list = list(self.get_industry_stocks(industry))
                result = {}
                for code_ in stock_list:
                    df = self.get_k_data(code_, start_date=str(date)[
                                         :10], end_date=str(date)[:10])
                    if not df.empty:
                        row = df.iloc[0]
                        result[code_] = {"close": row["close"], "pct_chg": (
                            row["close"]-row["open"])/row["open"]*100}
                return result
            elif code:
                df = self.get_k_data(code, start_date=str(
                    date)[:10], end_date=str(date)[:10])
                if not df.empty:
                    row = df.iloc[0]
                    return {code: {"close": row["close"], "pct_chg": (row["close"]-row["open"])/row["open"]*100}}
            return {}
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"获取行情摘要失败: {str(e)}")
            return {}

    # 主流财务字段映射，真实字段名→英文key，默认只展示这些
    FINANCE_FIELD_MAPPING = {
        "利润表_营业收入": "revenue",
        "利润表_净利润": "net_profit",
        "资产负债表_资产总计": "assets",
        "资产负债表_负债合计": "liabilities",
        "利润表_营业利润": "operating_profit",
        "利润表_利润总额": "total_profit",
        "利润表_归属于母公司所有者的净利润": "parent_net_profit",
        "资产负债表_归属于母公司股东权益": "equity",
        "资产负债表_所有者权益（或股东权益）合计": "total_equity",
        "盈利能力_净资产收益率": "roe",
        "资本结构_资产负债率": "debt_to_equity",
        "现金流量表_经营活动产生的现金流量净额": "operating_cash_flow",
        "成长能力_营业收入增长率": "revenue_growth_rate",
        "成长能力_净利润增长率": "net_profit_growth_rate",
    }

    def get_finance_data(self, code: str) -> dict:
        """
        获取指定股票的财务数据，优先多期历史，兼容所有hikyuu版本，自动兜底。
        返回格式：
        {
            "finance_history": [  # 多期历史，默认只包含主流字段
                {"date": ..., "revenue": ..., ...},
                ...
            ],
            "all_fields": [  # 所有可用字段，供前端动态勾选
                {"field": "利润表_营业收入", "key": "revenue"},
                ...
            ]
        }
        """
        result = {"finance_history": [], "all_fields": []}
        try:
            stock = self.sm[code]
            # 优先多期历史
            if hasattr(stock, 'get_history_finance'):
                fields = self.sm.get_history_finance_all_fields()
                field_names = [f[1] for f in fields]
                field_idx_map = {f[1]: f[0] for f in fields}
                result["all_fields"] = [
                    {"field": name, "key": self.FINANCE_FIELD_MAPPING.get(name, name)} for name in field_names
                ]
                history_finance = stock.get_history_finance()
                for row in history_finance:
                    if not any(row):
                        continue
                    # 只提取主流字段，缺失自动填 None
                    item = {}
                    # 统一格式化日期
                    item["date"] = self._convert_hikyuu_datetime(row[0])
                    for cn, en in self.FINANCE_FIELD_MAPPING.items():
                        idx = field_idx_map.get(cn)
                        if idx is not None and idx < len(row):
                            item[en] = row[idx]
                        else:
                            item[en] = None
                    result["finance_history"].append(item)
                # 如果批量API无数据，尝试用 get_history_finance_info(date) 兜底
                if not result["finance_history"]:
                    today = datetime.now()
                    dates = []
                    for y in range(today.year, today.year-5, -1):
                        for m in [1231, 930, 630, 331]:
                            dates.append(int(f"{y}{m:04d}0000"))
                    for d in dates:
                        try:
                            info = stock.get_history_finance_info(d)
                            if info:
                                item = {
                                    "date": self._convert_hikyuu_datetime(d)}
                                for cn, en in self.FINANCE_FIELD_MAPPING.items():
                                    idx = field_idx_map.get(cn)
                                    if idx is not None and idx < len(info):
                                        item[en] = info[idx]
                                    else:
                                        item[en] = None
                                result["finance_history"].append(item)
                        except Exception as e:
                            if hasattr(self, 'log_manager') and self.log_manager:
                                self.log_manager.warning(
                                    f"[财务数据兜底API] get_history_finance_info 异常: {str(e)}")
                            else:
                                print(
                                    f"[财务数据兜底API] get_history_finance_info 异常: {str(e)}")
                            continue
            # 兜底：如果还没有数据，可补充akshare等（预留接口）
            if not result["finance_history"]:
                try:
                    from data.data_loader import fetch_fundamental_data_akshare
                    ak_df = fetch_fundamental_data_akshare(code)
                    if ak_df is not None and not ak_df.empty:
                        ak_row = ak_df.iloc[0]
                        item = {"date": ak_row.get("报告期", None)}
                        for cn, en in self.FINANCE_FIELD_MAPPING.items():
                            item[en] = ak_row.get(en, None)
                        result["finance_history"].append(item)
                except Exception:
                    self.log_manager.warning(
                        f"[财务数据兜底API] fetch_fundamental_data_akshare 异常")

        except Exception as e:
            self.log_manager.error(
                f"获取财务数据失败: {code}, 数据长度: {len(result['finance_history'])}")

        self.log_manager.info(
            f"获取财务数据成功: {code}, 数据长度: {len(result['finance_history'])}")
        return result

    def df_to_kdata(self, df, log=True):
        """
        将pandas.DataFrame批量转换为hikyuu.KData对象，自动处理字段映射和类型。
        优先使用DataFrame数据创建KData，而不是从hikyuu数据库获取。
        Args:
            df: DataFrame，需包含datetime、open、high、low、close、amount、volume列
            log: 是否打印日志（默认True）
        Returns:
            KData对象
        """
        try:
            from hikyuu import KData, KRecord, Datetime

            if df is None or df.empty:
                if hasattr(self, 'log_manager') and log:
                    self.log_manager.warning("df_to_kdata收到空DataFrame")
                return KData()

            # 自动补全 code 字段
            code = None
            if 'code' in df.columns:
                code = df['code'].iloc[0]
            elif hasattr(df, 'code'):
                code = df.code
            if not code:
                code = '000001'  # 使用默认代码
                if hasattr(self, 'log_manager') and log:
                    self.log_manager.warning(
                        "df_to_kdata无法推断股票代码，使用默认代码000001")

            # 自动补全 datetime 字段
            df_copy = df.copy()
            if 'datetime' not in df_copy.columns:
                if isinstance(df_copy.index, pd.DatetimeIndex):
                    df_copy['datetime'] = df_copy.index
                else:
                    if hasattr(self, 'log_manager') and log:
                        self.log_manager.error(
                            "df_to_kdata无法推断datetime字段，请确保DataFrame包含'datetime'列或索引")
                    return KData()

            # 检查必要字段
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [
                col for col in required_columns if col not in df_copy.columns]
            if missing_columns:
                if hasattr(self, 'log_manager') and log:
                    self.log_manager.error(
                        f"df_to_kdata缺少必要列: {missing_columns}")
                return KData()

            # 直接从DataFrame数据创建KData
            try:
                # 创建空的KData对象
                kdata = KData()

                # 确保datetime列是datetime类型
                if not pd.api.types.is_datetime64_any_dtype(df_copy['datetime']):
                    df_copy['datetime'] = pd.to_datetime(df_copy['datetime'])

                # 按时间排序
                df_copy = df_copy.sort_values('datetime')

                # 逐行添加K线记录
                for _, row in df_copy.iterrows():
                    try:
                        # 创建Datetime对象
                        dt = Datetime(row['datetime'].strftime(
                            '%Y-%m-%d %H:%M:%S'))

                        # 创建KRecord
                        record = KRecord()
                        record.datetime = dt
                        record.open = float(row['open'])
                        record.high = float(row['high'])
                        record.low = float(row['low'])
                        record.close = float(row['close'])
                        record.volume = float(row['volume'])
                        record.amount = float(
                            row.get('amount', row['volume'] * row['close']))

                        # 添加到KData
                        kdata.append(record)

                    except Exception as e:
                        if hasattr(self, 'log_manager') and log:
                            self.log_manager.warning(f"跳过无效K线记录: {e}")
                        continue

                if hasattr(self, 'log_manager') and log:
                    start_date = df_copy['datetime'].min().strftime('%Y-%m-%d')
                    end_date = df_copy['datetime'].max().strftime('%Y-%m-%d')
                    self.log_manager.info(
                        f"df_to_kdata转换成功: code={code}, start={start_date}, end={end_date}, KData长度={len(kdata)}")

                return kdata

            except Exception as e:
                # 如果直接创建失败，尝试从hikyuu数据库获取（兼容性方案）
                if hasattr(self, 'log_manager') and log:
                    self.log_manager.warning(
                        f"直接创建KData失败，尝试从hikyuu数据库获取: {e}")

                # 自动推断起止日期
                start_date = str(df_copy['datetime'].min())[:10]
                end_date = str(df_copy['datetime'].max())[:10]

                from hikyuu.interactive import sm
                from hikyuu import Query, Datetime

                try:
                    stock = sm[code]
                    if start_date and end_date:
                        query = Query(Datetime(start_date), Datetime(end_date))
                    else:
                        query = Query(-len(df_copy))
                    kdata = stock.get_kdata(query)

                    if hasattr(self, 'log_manager') and log:
                        self.log_manager.info(
                            f"df_to_kdata从hikyuu获取: code={code}, start={start_date}, end={end_date}, KData长度={len(kdata)}")

                    return kdata

                except Exception as e2:
                    if hasattr(self, 'log_manager') and log:
                        self.log_manager.error(f"从hikyuu数据库获取KData也失败: {e2}")
                    return KData()

        except Exception as e:
            if hasattr(self, 'log_manager') and log:
                self.log_manager.error(f'df_to_kdata转换KData失败: {str(e)}')
            from hikyuu import KData
            return KData()

    def kdata_to_df(self, kdata):
        """
        将hikyuu.KData对象批量转换为pandas.DataFrame，自动处理字段映射和类型。
        Args:
            kdata: KData对象
        Returns:
            DataFrame
        """
        if kdata is None or len(kdata) == 0:
            if hasattr(self, 'log_manager'):
                self.log_manager.warning("kdata_to_df收到空KData")
            return pd.DataFrame()
        records = []
        for i in range(len(kdata)):
            rec = kdata[i]
            dt = getattr(rec, 'datetime', None)
            records.append({
                'datetime': str(dt),
                'open': getattr(rec, 'open', None),
                'high': getattr(rec, 'high', None),
                'low': getattr(rec, 'low', None),
                'close': getattr(rec, 'close', None),
                'volume': getattr(rec, 'volume', None),
                'amount': getattr(rec, 'amount', None),
                'code': getattr(rec, 'code', None) if hasattr(rec, 'code') else None
            })
        df = pd.DataFrame(records)
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            df.set_index('datetime', inplace=True)
        return df

    def save_indicator_combination(self, name: str, user_id: str, indicators: list, extra: str = None):
        cursor = self.conn.cursor()
        indicators_json = json.dumps(indicators, ensure_ascii=False)
        cursor.execute('''INSERT INTO indicator_combination (name, user_id, indicators, created_at, extra) VALUES (?, ?, ?, datetime('now'), ?)''',
                       (name, user_id, indicators_json, extra))
        self.conn.commit()

    def get_indicator_combinations(self, user_id: str = None):
        cursor = self.conn.cursor()
        if user_id:
            cursor.execute(
                '''SELECT id, name, user_id, indicators, created_at, extra FROM indicator_combination WHERE user_id=?''', (user_id,))
        else:
            cursor.execute(
                '''SELECT id, name, user_id, indicators, created_at, extra FROM indicator_combination''')
        rows = cursor.fetchall()
        result = []
        for row in rows:
            indicators = json.loads(row[3]) if row[3] else []
            result.append({
                'id': row[0],
                'name': row[1],
                'user_id': row[2],
                'indicators': indicators,
                'created_at': row[4],
                'extra': row[5]
            })
        return result

    def delete_indicator_combination(self, comb_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            '''DELETE FROM indicator_combination WHERE id=?''', (comb_id,))
        self.conn.commit()


# 全局唯一数据管理器实例，供全系统import使用
try:
    data_manager = DataManager(BaseLogManager())
except Exception:
    data_manager = DataManager()
