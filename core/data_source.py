from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
import pandas as pd
from datetime import datetime
import threading
import queue
import logging
from enum import Enum, auto
import hikyuu as hku

class DataFrequency(Enum):
    """数据频率"""
    TICK = auto()      # 逐笔
    MIN1 = auto()      # 1分钟
    MIN5 = auto()      # 5分钟
    MIN15 = auto()     # 15分钟
    MIN30 = auto()     # 30分钟
    HOUR = auto()      # 1小时
    DAY = auto()       # 日线
    WEEK = auto()      # 周线
    MONTH = auto()     # 月线

class DataSourceType(Enum):
    """数据源类型"""
    SINA = auto()
    EASTMONEY = auto()
    TUSHARE = auto()
    LOCAL = auto()
    HIKYUU = auto()  # 添加Hikyuu数据源类型

class MarketDataType(Enum):
    """市场数据类型"""
    TICK = auto()      # 逐笔成交
    KLINE = auto()     # K线数据
    DEPTH = auto()     # 深度数据
    TRANSACTION = auto() # 逐笔委托

class DataSource(ABC):
    """数据源基类"""
    
    def __init__(self, source_type: DataSourceType):
        self.source_type = source_type
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._subscribers = []
        self._running = False
        self._thread = None
        self._data_queue = queue.Queue()

    @abstractmethod
    def connect(self) -> bool:
        """连接到数据源
        
        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据源连接"""
        pass

    @abstractmethod
    def subscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        """订阅数据
        
        Args:
            symbols: 股票代码列表
            data_types: 数据类型列表
            
        Returns:
            bool: 订阅是否成功
        """
        pass

    @abstractmethod
    def unsubscribe(self, symbols: List[str], data_types: List[MarketDataType]) -> bool:
        """取消订阅
        
        Args:
            symbols: 股票代码列表
            data_types: 数据类型列表
            
        Returns:
            bool: 取消订阅是否成功
        """
        pass

    @abstractmethod
    def get_kdata(self, symbol: str, freq: DataFrequency,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """获取K线数据
        
        Args:
            symbol: 股票代码
            freq: 数据频率
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            pd.DataFrame: K线数据，包含以下列:
                - datetime: 时间
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                - amount: 成交额(可选)
        """
        pass

    @abstractmethod
    def get_real_time_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """获取实时行情
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            pd.DataFrame: 实时行情数据，包含以下列:
                - symbol: 股票代码
                - name: 股票名称
                - price: 最新价
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close_prev: 昨收价
                - volume: 成交量
                - amount: 成交额
                - datetime: 时间
        """
        pass

    def add_subscriber(self, callback):
        """添加订阅者
        
        Args:
            callback: 回调函数，接收数据更新通知
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def remove_subscriber(self, callback):
        """移除订阅者
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify_subscribers(self, data: Dict[str, Any]):
        """通知所有订阅者
        
        Args:
            data: 要发送的数据
        """
        for subscriber in self._subscribers:
            try:
                subscriber(data)
            except Exception as e:
                self.logger.error(f"通知订阅者失败: {str(e)}")

class DataSourceManager:
    """数据源管理器"""
    
    def __init__(self):
        self._sources: Dict[DataSourceType, DataSource] = {}
        self._active_source = None
        self.logger = logging.getLogger("DataSourceManager")

    def add_source(self, source: DataSource) -> None:
        """添加数据源"""
        self._sources[source.source_type] = source

    def remove_source(self, source_type: DataSourceType) -> None:
        """移除数据源"""
        if source_type in self._sources:
            source = self._sources[source_type]
            source.disconnect()
            del self._sources[source_type]

    def set_active_source(self, source_type: DataSourceType) -> bool:
        """设置活动数据源"""
        if source_type not in self._sources:
            self.logger.error(f"数据源 {source_type.value} 不存在")
            return False
        
        if self._active_source:
            self._active_source.disconnect()
        
        self._active_source = self._sources[source_type]
        return self._active_source.connect()

    def get_kdata(self, symbol: str, freq: DataFrequency,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """获取K线数据"""
        if not self._active_source:
            raise RuntimeError("没有设置活动数据源")
        return self._active_source.get_kdata(symbol, freq, start_date, end_date)

    def get_real_time_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        if not self._active_source:
            raise RuntimeError("没有设置活动数据源")
        return self._active_source.get_real_time_quotes(symbols)

    def subscribe(self, symbols: List[str], data_types: List[MarketDataType],
                 callback) -> bool:
        """订阅数据"""
        if not self._active_source:
            raise RuntimeError("没有设置活动数据源")
        self._active_source.add_subscriber(callback)
        return self._active_source.subscribe(symbols, data_types)

    def unsubscribe(self, symbols: List[str], data_types: List[MarketDataType],
                    callback) -> bool:
        """取消订阅"""
        if not self._active_source:
            raise RuntimeError("没有设置活动数据源")
        self._active_source.remove_subscriber(callback)
        return self._active_source.unsubscribe(symbols, data_types)

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
                start_date = stock.startDatetime
            if not end_date:
                end_date = stock.lastDatetime
                
            query = hku.Query(start_date, end_date, ktype)
            kdata = stock.getKData(query)
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
            DataFrequency.MIN1: hku.Query.MIN,
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