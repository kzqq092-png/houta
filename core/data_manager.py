"""
数据管理模块

提供数据加载、缓存和管理功能
"""

import pandas as pd
from typing import Dict, Any, Optional, List
import hikyuu as hku
from hikyuu.interactive import *
from core.logger import LogManager

class DataManager:
    """数据管理器"""
    
    def __init__(self, log_manager: Optional[LogManager] = None):
        """初始化数据管理器
        
        Args:
            log_manager: 日志管理器实例，可选
        """
        self.log_manager = log_manager or LogManager()
        self.data_cache = {}
        self.stock_list_cache = []
        
        try:
            # 初始化hikyuu
            self.log_manager.info("正在初始化hikyuu...")
            # TODO: 添加hikyuu初始化代码
            self.log_manager.info("hikyuu初始化完成")
        except Exception as e:
            self.log_manager.error(f"hikyuu初始化失败: {str(e)}")
            raise
        
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
            self.log_manager.error(f"获取K线数据失败: {str(e)}")
            return pd.DataFrame()
            
    def get_stock_list(self) -> List[Dict[str, str]]:
        """获取股票列表
        
        Returns:
            List[Dict[str, str]]: 股票列表，每个股票包含代码和名称
        """
        try:
            stocks = []
            sm = hku.StockManager.instance()
            for stock in sm:
                try:
                    stocks.append({
                        'code': stock.code,
                        'name': stock.name,
                        'market': self._get_market_name(stock.market),
                        'industry': self._get_industry_name(stock),
                        'valid': stock.valid
                    })
                except Exception as e:
                    self.log_manager.warning(f"处理股票 {stock.code} 信息失败: {str(e)}")
                    continue
                    
            return stocks
            
        except Exception as e:
            self.log_manager.error(f"获取股票列表失败: {str(e)}")
            return []
            
    def _get_market_name(self, market_code: str) -> str:
        """获取市场名称
        
        Args:
            market_code: 市场代码
            
        Returns:
            市场名称
        """
        market_map = {
            'SH': '沪市主板',
            'SZ': '深市主板',
            'BJ': '北交所',
            'HK': '港股通',
            'US': '美股'
        }
        return market_map.get(market_code, '未知')
        
    def _get_industry_name(self, stock: hku.Stock) -> str:
        """获取行业名称
        
        Args:
            stock: hikyuu Stock对象
            
        Returns:
            行业名称
        """
        try:
            # TODO: 实现行业名称获取逻辑
            return '其他'
        except Exception as e:
            self.log_manager.warning(f"获取股票 {stock.code} 行业信息失败: {str(e)}")
            return '其他'
            
    def clear_cache(self):
        """清除缓存"""
        self.data_cache.clear()
        self.stock_list_cache.clear()
        self.log_manager.info("数据缓存已清除") 