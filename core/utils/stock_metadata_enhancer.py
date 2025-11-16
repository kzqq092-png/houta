#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票元数据增强器

用于从外部API补充完善股票元数据（行业、板块等信息）
当K线数据中不包含这些信息时，通过专门的API获取并更新

作者: HIkyuu-UI开发团队
版本: 2.0
日期: 2025-01-06
更新: 添加缓存机制，优化性能
"""

import pandas as pd
from typing import Dict, List, Optional, Any
from loguru import logger
import threading
import time

logger = logger.bind(module=__name__)


class StockMetadataEnhancer:
    """
    股票元数据增强器
    
    支持从多个数据源获取股票的行业板块信息：
    - AKShare: stock_info_a_code_name, stock_individual_info_em
    - Tushare: stock_basic (需要token)
    - EastMoney: 股票基本信息
    
    性能优化：
    - 缓存机制：缓存股票基本信息（全部股票列表）和详细信息
    - 线程安全：使用锁保护缓存访问
    - TTL机制：缓存有效期24小时，过期后自动刷新
    """
    
    def __init__(self):
        self.akshare_available = False
        self.tushare_available = False
        
        # ✅ 缓存机制
        self._stock_info_cache: Optional[pd.DataFrame] = None  # 缓存全部股票基本信息
        self._stock_info_cache_time: Optional[float] = None  # 缓存时间戳
        self._detailed_info_cache: Dict[str, Dict[str, Any]] = {}  # 缓存每个股票的详细信息
        self._detailed_info_cache_time: Dict[str, float] = {}  # 每个股票详细信息的缓存时间戳
        self._cache_lock = threading.RLock()  # 线程安全锁
        self._refreshing_stock_info = False  # 防止多个线程同时刷新股票基本信息
        self._refreshing_detailed_info: Dict[str, bool] = {}  # 防止多个线程同时刷新同一股票的详细信息
        self._cache_ttl = 24 * 3600  # 缓存有效期：24小时（秒）
        self._detailed_cache_ttl = 24 * 3600  # 详细信息缓存有效期：24小时（秒）
        
        # 尝试导入AKShare
        try:
            import akshare as ak
            self.ak = ak
            self.akshare_available = True
            logger.info("✅ AKShare可用，将用于补充股票元数据（已启用缓存机制）")
        except ImportError:
            logger.warning("AKShare不可用，无法使用AKShare补充元数据")
        
        # 尝试导入Tushare
        try:
            import tushare as ts
            self.ts = ts
            self.tushare_available = True
            logger.info("✅ Tushare可用，将用于补充股票元数据")
        except ImportError:
            logger.warning("Tushare不可用，无法使用Tushare补充元数据")
    
    def enhance_stock_metadata_batch(self, symbols: List[str], 
                                      source: str = 'akshare') -> Dict[str, Dict[str, Any]]:
        """
        批量增强股票元数据
        
        Args:
            symbols: 股票代码列表 (格式：000001 或 000001.SZ)
            source: 数据源 ('akshare', 'tushare', 'auto')
        
        Returns:
            Dict[symbol, metadata]: 每个股票的元数据字典
        """
        result = {}
        
        if source == 'auto':
            # 自动选择可用数据源
            if self.akshare_available:
                source = 'akshare'
            elif self.tushare_available:
                source = 'tushare'
            else:
                logger.error("没有可用的数据源，无法补充元数据")
                return result
        
        if source == 'akshare' and self.akshare_available:
            result = self._enhance_with_akshare_batch(symbols)
        elif source == 'tushare' and self.tushare_available:
            result = self._enhance_with_tushare_batch(symbols)
        else:
            logger.warning(f"数据源 {source} 不可用")
        
        return result
    
    def _enhance_with_akshare_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        使用AKShare批量获取股票元数据（已优化：使用缓存机制）
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            Dict[symbol, metadata]: 每个股票的元数据字典
        """
        result = {}
        
        try:
            # ✅ 优化：从缓存获取股票基本信息，避免重复请求
            stock_info_df = self._get_stock_info_cached()
            
            if stock_info_df is not None and not stock_info_df.empty:
                # 处理每个查询的股票代码
                for symbol in symbols:
                    # 标准化股票代码（移除市场后缀）
                    clean_code = symbol.split('.')[0]
                    
                    # 在DataFrame中查找
                    match = stock_info_df[stock_info_df['code'] == clean_code]
                    
                    if not match.empty:
                        row = match.iloc[0]
                        metadata = {
                            'code': clean_code,
                            'name': row.get('name', ''),
                        }
                        
                        # AKShare的stock_info_a_code_name可能不含行业信息
                        # ✅ 优化：从缓存获取详细信息，避免重复请求
                        # ✅ 修复：即使详细信息获取失败，也返回基本信息（至少包含股票名称）
                        try:
                            detailed_info = self._get_detailed_info_akshare_cached(clean_code)
                            if detailed_info:
                                metadata.update(detailed_info)
                        except Exception as e:
                            # 详细信息获取失败不影响基本信息返回
                            logger.debug(f"获取股票详细信息失败 {clean_code}: {e}，但基本信息已获取")
                        
                        result[symbol] = metadata
                    else:
                        logger.debug(f"AKShare中未找到股票: {symbol}")
            
            if result:
                logger.info(f"✅ AKShare补充完成，成功获取 {len(result)}/{len(symbols)} 个股票的元数据")
            
        except Exception as e:
            logger.error(f"❌ AKShare批量获取失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return result
    
    def _get_stock_info_cached(self) -> Optional[pd.DataFrame]:
        """
        获取股票基本信息（带缓存机制，支持并发控制）
        
        Returns:
            股票基本信息DataFrame，如果获取失败则返回None
        """
        current_time = time.time()
        
        # 第一次检查：缓存是否有效
        with self._cache_lock:
            if (self._stock_info_cache is not None and 
                self._stock_info_cache_time is not None and
                current_time - self._stock_info_cache_time < self._cache_ttl):
                # 缓存有效，直接返回
                logger.debug(f"✅ 使用缓存的股票基本信息（缓存年龄: {int(current_time - self._stock_info_cache_time)}秒）")
                return self._stock_info_cache.copy()  # 返回副本，避免外部修改
        
        # 缓存无效或不存在，需要刷新
        # 检查是否有其他线程正在刷新
        with self._cache_lock:
            if self._refreshing_stock_info:
                # 有其他线程正在刷新，等待并返回旧缓存（即使过期）
                logger.debug("⏳ 其他线程正在刷新股票基本信息，使用现有缓存")
                if self._stock_info_cache is not None:
                    return self._stock_info_cache.copy()
                # 如果没有旧缓存，等待一下再检查
                return None
            
            # 标记为正在刷新
            self._refreshing_stock_info = True
        
        # 从API获取（不在锁内，避免阻塞其他线程）
        try:
            logger.info("📥 从AKShare获取股票基本信息（缓存未命中，正在刷新）...")
            stock_info_df = self.ak.stock_info_a_code_name()
            
            if stock_info_df is not None and not stock_info_df.empty:
                logger.info(f"✅ 获取到 {len(stock_info_df)} 条股票基本信息，已缓存")
                
                # 更新缓存
                with self._cache_lock:
                    self._stock_info_cache = stock_info_df.copy()
                    self._stock_info_cache_time = time.time()
                    self._refreshing_stock_info = False
                
                return stock_info_df
            else:
                logger.warning("⚠️ 从AKShare获取的股票基本信息为空")
                with self._cache_lock:
                    self._refreshing_stock_info = False
                return None
                
        except Exception as e:
            logger.error(f"❌ 从AKShare获取股票基本信息失败: {e}")
            # 如果获取失败，尝试返回旧缓存（即使过期）
            with self._cache_lock:
                self._refreshing_stock_info = False
                if self._stock_info_cache is not None:
                    logger.warning("⚠️ 使用过期的缓存数据（API获取失败）")
                    return self._stock_info_cache.copy()
            return None
    
    def _get_detailed_info_akshare_cached(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单个股票的详细信息（带缓存机制，支持并发控制）
        
        Args:
            code: 股票代码
            
        Returns:
            股票详细信息字典，如果获取失败则返回None
        """
        current_time = time.time()
        
        # 第一次检查：缓存是否有效
        with self._cache_lock:
            if (code in self._detailed_info_cache and 
                code in self._detailed_info_cache_time and
                current_time - self._detailed_info_cache_time[code] < self._detailed_cache_ttl):
                # 缓存有效，直接返回
                logger.debug(f"✅ 使用缓存的股票详细信息: {code}（缓存年龄: {int(current_time - self._detailed_info_cache_time[code])}秒）")
                return self._detailed_info_cache[code].copy()  # 返回副本，避免外部修改
        
        # 缓存无效或不存在，需要刷新
        # 检查是否有其他线程正在刷新同一个股票
        with self._cache_lock:
            if self._refreshing_detailed_info.get(code, False):
                # 有其他线程正在刷新，等待并返回旧缓存（即使过期）
                logger.debug(f"⏳ 其他线程正在刷新股票详细信息: {code}，使用现有缓存")
                if code in self._detailed_info_cache:
                    return self._detailed_info_cache[code].copy()
                # 如果没有旧缓存，返回None
                return None
            
            # 标记为正在刷新
            self._refreshing_detailed_info[code] = True
        
        # 从API获取（不在锁内，避免阻塞其他线程）
        try:
            # ✅ 优化：添加超时机制，避免API调用阻塞太久
            import threading
            detailed_info = None
            api_error = None
            
            def fetch_detailed_info():
                nonlocal detailed_info, api_error
                try:
                    detailed_info = self._get_detailed_info_akshare(code)
                except Exception as e:
                    api_error = e
            
            # 在单独线程中执行，带超时（最多等待3秒）
            fetch_thread = threading.Thread(target=fetch_detailed_info, daemon=True)
            fetch_thread.start()
            fetch_thread.join(timeout=3.0)
            
            if fetch_thread.is_alive():
                # 超时，返回None（不影响基本信息返回）
                logger.debug(f"获取股票详细信息超时: {code}（不影响基本信息）")
                with self._cache_lock:
                    self._refreshing_detailed_info[code] = False
                    # 如果有旧缓存，返回旧缓存
                    if code in self._detailed_info_cache:
                        logger.debug(f"⚠️ 使用过期的缓存数据（API调用超时）: {code}")
                        return self._detailed_info_cache[code].copy()
                return None
            
            if detailed_info:
                # 更新缓存
                with self._cache_lock:
                    self._detailed_info_cache[code] = detailed_info.copy()
                    self._detailed_info_cache_time[code] = time.time()
                    self._refreshing_detailed_info[code] = False
            else:
                with self._cache_lock:
                    self._refreshing_detailed_info[code] = False
            
            return detailed_info
            
        except Exception as e:
            logger.debug(f"获取股票详细信息失败 {code}: {e}")
            # 如果获取失败，尝试返回旧缓存（即使过期）
            with self._cache_lock:
                self._refreshing_detailed_info[code] = False
                if code in self._detailed_info_cache:
                    logger.debug(f"⚠️ 使用过期的缓存数据（API获取失败）: {code}")
                    return self._detailed_info_cache[code].copy()
            return None
    
    def _get_detailed_info_akshare(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单个股票的详细信息（含行业板块）
        
        使用AKShare的stock_individual_info_em接口
        注意：此方法不包含缓存逻辑，由 _get_detailed_info_akshare_cached 调用
        
        Args:
            code: 股票代码
            
        Returns:
            股票详细信息字典，如果获取失败则返回None
        """
        try:
            # 尝试使用东方财富个股信息接口
            detail_df = self.ak.stock_individual_info_em(symbol=code)
            
            if detail_df is not None and not detail_df.empty:
                # 将DataFrame转换为字典（item -> value）
                info_dict = {}
                for _, row in detail_df.iterrows():
                    item = row.get('item', '')
                    value = row.get('value', '')
                    if item and value:
                        info_dict[item] = value
                
                # 提取行业板块信息
                result = {}
                
                # 行业字段可能的名称
                industry_keys = ['行业', '所属行业', 'industry']
                for key in industry_keys:
                    if key in info_dict:
                        result['industry'] = info_dict[key]
                        break
                
                # 板块字段可能的名称
                sector_keys = ['板块', '所属板块', 'sector', '概念板块']
                for key in sector_keys:
                    if key in info_dict:
                        result['sector'] = info_dict[key]
                        break
                
                # 上市日期
                listing_keys = ['上市时间', '上市日期', 'listing_date']
                for key in listing_keys:
                    if key in info_dict:
                        result['listing_date'] = info_dict[key]
                        break
                
                # 总股本/流通股本
                if '总股本' in info_dict:
                    try:
                        result['total_shares'] = float(info_dict['总股本'])
                    except:
                        pass
                
                if '流通股' in info_dict:
                    try:
                        result['circulating_shares'] = float(info_dict['流通股'])
                    except:
                        pass
                
                logger.debug(f"获取股票详细信息: {code} -> {result}")
                return result
            
        except Exception as e:
            logger.debug(f"获取股票详细信息失败 {code}: {e}")
        
        return None
    
    def clear_cache(self, clear_detailed_info: bool = True):
        """
        清除缓存
        
        Args:
            clear_detailed_info: 是否清除详细信息缓存，默认为True
        """
        with self._cache_lock:
            self._stock_info_cache = None
            self._stock_info_cache_time = None
            self._refreshing_stock_info = False
            if clear_detailed_info:
                self._detailed_info_cache.clear()
                self._detailed_info_cache_time.clear()
                self._refreshing_detailed_info.clear()
            logger.info("✅ 缓存已清除")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        with self._cache_lock:
            current_time = time.time()
            stats = {
                'stock_info_cached': self._stock_info_cache is not None,
                'stock_info_cache_age': None,
                'detailed_info_cache_count': len(self._detailed_info_cache),
                'detailed_info_cache_ages': {}
            }
            
            if self._stock_info_cache_time is not None:
                stats['stock_info_cache_age'] = int(current_time - self._stock_info_cache_time)
            
            for code, cache_time in self._detailed_info_cache_time.items():
                stats['detailed_info_cache_ages'][code] = int(current_time - cache_time)
            
            return stats
    
    def _enhance_with_tushare_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        使用Tushare批量获取股票元数据
        """
        result = {}
        
        try:
            # 需要Tushare token
            # 这里提供接口但需要用户配置
            logger.warning("Tushare补充功能需要配置token，暂未实现")
            # 示例代码：
            # pro = self.ts.pro_api(token='YOUR_TOKEN')
            # df = pro.stock_basic(fields='ts_code,name,industry,area,list_date')
            
        except Exception as e:
            logger.error(f"Tushare批量获取失败: {e}")
        
        return result
    
    def enhance_asset_metadata_table(self, db_manager, asset_type, market: str = 'all'):
        """
        直接增强数据库中的asset_metadata表
        
        Args:
            db_manager: AssetSeparatedDatabaseManager实例
            asset_type: 资产类型
            market: 市场过滤
        """
        try:
            from ..plugin_types import AssetType
            
            logger.info(f"开始增强asset_metadata表的行业信息 (asset_type={asset_type}, market={market})")
            
            # 1. 查询所有缺少行业信息的股票
            db_path = db_manager.get_database_path(asset_type)
            
            query = """
                SELECT symbol, name, market
                FROM asset_metadata
                WHERE (industry IS NULL OR industry = '' OR industry = '未知')
                  AND (sector IS NULL OR sector = '' OR sector = '未知')
                  AND listing_status = 'active'
            """
            
            if market and market != 'all':
                query += f" AND market = '{market.upper()}'"
            
            logger.info(f"查询缺少行业信息的股票...")
            
            from ..duckdb_manager import DuckDBManager
            duckdb_mgr = DuckDBManager()
            
            with duckdb_mgr.get_connection(db_path) as conn:
                result_df = conn.execute(query).fetchdf()
            
            if result_df.empty:
                logger.info("✅ 所有股票都已有行业信息，无需补充")
                return 0
            
            logger.info(f"📊 找到 {len(result_df)} 个股票需要补充行业信息")
            
            # 2. 批量获取元数据
            symbols = result_df['symbol'].tolist()
            enhanced_data = self.enhance_stock_metadata_batch(symbols, source='akshare')
            
            # 3. 更新数据库
            update_count = 0
            for symbol, metadata in enhanced_data.items():
                if 'industry' in metadata or 'sector' in metadata:
                    success = db_manager.upsert_asset_metadata(
                        symbol=symbol,
                        asset_type=asset_type,
                        metadata=metadata
                    )
                    if success:
                        update_count += 1
            
            logger.info(f"✅ 成功补充 {update_count} 个股票的行业信息")
            return update_count
            
        except Exception as e:
            logger.error(f"增强asset_metadata表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0


# 全局单例
_metadata_enhancer: Optional[StockMetadataEnhancer] = None


def get_metadata_enhancer() -> StockMetadataEnhancer:
    """获取元数据增强器单例"""
    global _metadata_enhancer
    if _metadata_enhancer is None:
        _metadata_enhancer = StockMetadataEnhancer()
    return _metadata_enhancer

