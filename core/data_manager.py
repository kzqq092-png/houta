"""
数据管理模块

提供数据加载、缓存和管理功能
"""

import pandas as pd
from typing import Dict, Any, Optional, List
import hikyuu as hku
from hikyuu.interactive import *

class DataManager:
    """数据管理器"""
    
    def __init__(self):
        """初始化数据管理器"""
        self.data_cache = {}
        self.stock_list_cache = []
        
    def get_k_data(self, code: str, period: str = 'D') -> pd.DataFrame:
        """获取K线数据
        
        Args:
            code: 股票代码
            period: 周期，如 D=日线，W=周线，M=月线
            
        Returns:
            K线数据DataFrame
        """
        try:
            # 生成缓存键
            cache_key = f"{code}_{period}"
            
            # 检查缓存
            if cache_key in self.data_cache:
                return self.data_cache[cache_key]
                
            # 从hikyuu获取数据
            stock = hku.getStock(code)
            if period == 'D':
                kdata = stock.getKData(hku.KQuery(-1000))  # 获取最近1000条日线数据
            elif period == 'W':
                kdata = stock.getWeekKData(hku.KQuery(-200))  # 获取最近200条周线数据
            elif period == 'M':
                kdata = stock.getMonthKData(hku.KQuery(-100))  # 获取最近100条月线数据
            else:
                raise ValueError(f"不支持的周期类型: {period}")
                
            # 转换为DataFrame
            df = pd.DataFrame({
                'date': kdata.getDatetimeList(),
                'open': kdata.getOpenList(),
                'high': kdata.getHighList(),
                'low': kdata.getLowList(),
                'close': kdata.getCloseList(),
                'volume': kdata.getVolumeList(),
                'amount': kdata.getAmountList()
            })
            
            # 缓存数据
            self.data_cache[cache_key] = df
            
            return df
            
        except Exception as e:
            print(f"获取K线数据失败: {str(e)}")
            return pd.DataFrame()
            
    def get_stock_list(self) -> List[Dict[str, str]]:
        """获取股票列表
        
        Returns:
            List[Dict[str, str]]: 股票列表，每个股票包含代码和名称
        """
        try:
            stocks = []
            for stock in sm.get_stock_list():
                stocks.append({
                    'code': stock['code'],
                    'name': stock['name'],
                    'market': stock['market']
                })
            return stocks
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
            return []
            
    def clear_cache(self):
        """清除缓存"""
        self.data_cache.clear()
        self.stock_list_cache.clear() 