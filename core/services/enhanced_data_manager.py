from loguru import logger
"""
增强数据管理器实现

基于现有UnifiedDataManager扩展，集成多数据源插件数据存储架构，
确保与现有系统无缝集成，避免重复设计。

版本: 2.0
作者: FactorWeave-Quant Team
日期: 2025-01-27
"""

import sqlite3
import pandas as pd
import duckdb
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from pathlib import Path
import json
import threading
from dataclasses import dataclass
from decimal import Decimal

# 导入现有系统组件
from .unified_data_manager import UnifiedDataManager
from ..tet_data_pipeline import TETDataPipeline, StandardQuery, StandardData
from ..plugin_types import AssetType, DataType
from ..data_source_extensions import IDataSourcePlugin
from ..data.enhanced_models import (
    EnhancedStockInfo, EnhancedKlineData, FinancialStatement,
    MacroEconomicData, DataQualityMetrics, generate_table_name
)

logger = logger


@dataclass
class EnhancedStandardQuery(StandardQuery):
    """增强标准查询（扩展现有StandardQuery）"""

    # 新增字段
    data_quality_threshold: float = 0.8      # 数据质量阈值
    enable_cache: bool = True                # 是否启用缓存
    cache_ttl_minutes: int = 5               # 缓存TTL
    enable_validation: bool = True           # 是否启用数据验证
    output_format: str = "pandas"            # 输出格式
    include_metadata: bool = True            # 是否包含元数据

    # 高级查询参数
    aggregation_level: Optional[str] = None  # 聚合级别
    filters: Dict[str, Any] = None           # 过滤条件
    sort_by: Optional[str] = None            # 排序字段
    limit: Optional[int] = None              # 记录限制

    def __post_init__(self):
        super().__post_init__()
        if self.filters is None:
            self.filters = {}


class PluginTableManager:
    """插件表管理器"""

    def __init__(self, duckdb_path: str = "data/factorweave_analytics.duckdb"):
        self.duckdb_path = Path(duckdb_path)
        self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = None

    def get_connection(self):
        """获取DuckDB连接"""
        if self._conn is None:
            self._conn = duckdb.connect(str(self.duckdb_path))
        return self._conn

    def create_plugin_tables(self, plugin: IDataSourcePlugin) -> bool:
        """为插件创建专用数据表"""
        try:
            with self._lock:
                plugin_name = plugin.plugin_info.id
                supported_data_types = plugin.plugin_info.supported_data_types

                conn = self.get_connection()

                for data_type in supported_data_types:
                    if data_type == DataType.HISTORICAL_KLINE:
                        self._create_kline_tables(conn, plugin_name)
                    elif data_type == DataType.FUNDAMENTAL:
                        self._create_fundamental_table(conn, plugin_name)
                    elif data_type == DataType.FINANCIAL_STATEMENT:
                        self._create_financial_table(conn, plugin_name)
                    elif data_type == DataType.MACRO_ECONOMIC:
                        self._create_macro_table(conn, plugin_name)

                logger.info(f" 插件表创建完成: {plugin_name}")
                return True

        except Exception as e:
            logger.error(f" 创建插件表失败: {e}")
            return False

    def _create_kline_tables(self, conn, plugin_name: str):
        """创建K线数据表"""
        periods = ['1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M']

        for period in periods:
            table_name = generate_table_name(plugin_name, "kline_data", period)

            # 检查表是否已存在
            if self._table_exists(conn, table_name):
                continue

            sql = f"""
            CREATE TABLE {table_name} (
                symbol VARCHAR NOT NULL,
                datetime TIMESTAMP NOT NULL,
                
                -- 基础OHLCV
                open DECIMAL(12,4) NOT NULL,
                high DECIMAL(12,4) NOT NULL,
                low DECIMAL(12,4) NOT NULL,
                close DECIMAL(12,4) NOT NULL,
                volume BIGINT NOT NULL,
                amount DECIMAL(20,2),
                
                -- 复权数据（Wind标准）
                adj_close DECIMAL(12,4),
                adj_open DECIMAL(12,4),
                adj_high DECIMAL(12,4),
                adj_low DECIMAL(12,4),
                adj_factor DECIMAL(10,6),
                
                -- 技术指标预计算
                ma5 DECIMAL(12,4),
                ma10 DECIMAL(12,4),
                ma20 DECIMAL(12,4),
                ma60 DECIMAL(12,4),
                rsi_14 DECIMAL(8,4),
                macd_dif DECIMAL(8,4),
                macd_dea DECIMAL(8,4),
                macd_histogram DECIMAL(8,4),
                kdj_k DECIMAL(8,4),
                kdj_d DECIMAL(8,4),
                kdj_j DECIMAL(8,4),
                
                -- 市场微观结构（Bloomberg标准）
                vwap DECIMAL(12,4),
                twap DECIMAL(12,4),
                bid_price DECIMAL(12,4),
                ask_price DECIMAL(12,4),
                bid_volume BIGINT,
                ask_volume BIGINT,
                spread DECIMAL(8,4),
                
                -- 资金流向（东方财富标准）
                net_inflow_large DECIMAL(20,2),
                net_inflow_medium DECIMAL(20,2),
                net_inflow_small DECIMAL(20,2),
                net_inflow_main DECIMAL(20,2),
                
                -- 市场情绪
                turnover_rate DECIMAL(8,4),
                amplitude DECIMAL(8,4),
                change_pct DECIMAL(8,4),
                change_amount DECIMAL(8,4),
                
                -- 扩展字段
                plugin_specific_data JSON,
                
                -- 元数据
                data_source VARCHAR NOT NULL,
                data_quality_score DECIMAL(4,3),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                PRIMARY KEY (symbol, datetime)
            );
            """

            conn.execute(sql)

            # 创建索引
            conn.execute(f"CREATE INDEX idx_{table_name}_symbol_datetime ON {table_name}(symbol, datetime);")
            conn.execute(f"CREATE INDEX idx_{table_name}_datetime ON {table_name}(datetime);")
            conn.execute(f"CREATE INDEX idx_{table_name}_data_source ON {table_name}(data_source);")

            logger.info(f" 创建K线表: {table_name}")

    def _create_fundamental_table(self, conn, plugin_name: str):
        """创建基本面数据表"""
        table_name = generate_table_name(plugin_name, "stock_fundamental")

        if self._table_exists(conn, table_name):
            return

        sql = f"""
        CREATE TABLE {table_name} (
            symbol VARCHAR NOT NULL,
            trade_date DATE NOT NULL,
            
            -- 基本信息
            name VARCHAR,
            market VARCHAR,
            exchange VARCHAR,
            industry_l1 VARCHAR,
            industry_l2 VARCHAR,
            industry_l3 VARCHAR,
            sector VARCHAR,
            concept_plates VARCHAR[],
            
            -- 上市信息
            list_date DATE,
            delist_date DATE,
            list_status VARCHAR,
            
            -- 市值信息
            total_shares BIGINT,
            float_shares BIGINT,
            market_cap DECIMAL(20,2),
            float_market_cap DECIMAL(20,2),
            
            -- 估值指标
            pe_ratio DECIMAL(10,4),
            pb_ratio DECIMAL(10,4),
            ps_ratio DECIMAL(10,4),
            pcf_ratio DECIMAL(10,4),
            ev_ebitda DECIMAL(10,4),
            
            -- 盈利能力
            roe DECIMAL(8,4),
            roa DECIMAL(8,4),
            gross_margin DECIMAL(8,4),
            net_margin DECIMAL(8,4),
            
            -- 风险指标
            beta DECIMAL(8,6),
            volatility_30d DECIMAL(8,6),
            volatility_252d DECIMAL(8,6),
            
            -- 技术指标
            ma5 DECIMAL(10,4),
            ma10 DECIMAL(10,4),
            ma20 DECIMAL(10,4),
            ma60 DECIMAL(10,4),
            
            -- 扩展字段
            plugin_specific_data JSON,
            
            -- 元数据
            data_source VARCHAR NOT NULL,
            data_quality_score DECIMAL(4,3),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            PRIMARY KEY (symbol, trade_date)
        );
        """

        conn.execute(sql)

        # 创建索引
        conn.execute(f"CREATE INDEX idx_{table_name}_symbol_date ON {table_name}(symbol, trade_date);")
        conn.execute(f"CREATE INDEX idx_{table_name}_industry ON {table_name}(industry_l1, industry_l2);")
        conn.execute(f"CREATE INDEX idx_{table_name}_market ON {table_name}(market);")

        logger.info(f" 创建基本面表: {table_name}")

    def _create_financial_table(self, conn, plugin_name: str):
        """创建财务报表数据表"""
        table_name = generate_table_name(plugin_name, "financial_statements")

        if self._table_exists(conn, table_name):
            return

        sql = f"""
        CREATE TABLE {table_name} (
            symbol VARCHAR NOT NULL,
            report_date DATE NOT NULL,
            report_type VARCHAR NOT NULL, -- annual/semi_annual/quarterly/monthly
            
            -- 资产负债表
            total_assets DECIMAL(20,2),
            total_liabilities DECIMAL(20,2),
            shareholders_equity DECIMAL(20,2),
            current_assets DECIMAL(20,2),
            current_liabilities DECIMAL(20,2),
            cash_and_equivalents DECIMAL(20,2),
            
            -- 利润表
            total_revenue DECIMAL(20,2),
            operating_revenue DECIMAL(20,2),
            operating_cost DECIMAL(20,2),
            gross_profit DECIMAL(20,2),
            operating_profit DECIMAL(20,2),
            net_profit DECIMAL(20,2),
            net_profit_parent DECIMAL(20,2),
            
            -- 现金流量表
            operating_cash_flow DECIMAL(20,2),
            investing_cash_flow DECIMAL(20,2),
            financing_cash_flow DECIMAL(20,2),
            free_cash_flow DECIMAL(20,2),
            
            -- 财务比率
            current_ratio DECIMAL(8,4),
            quick_ratio DECIMAL(8,4),
            debt_to_equity DECIMAL(8,4),
            interest_coverage DECIMAL(8,4),
            
            -- 扩展字段
            plugin_specific_data JSON,
            
            -- 元数据
            data_source VARCHAR NOT NULL,
            data_quality_score DECIMAL(4,3),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            PRIMARY KEY (symbol, report_date, report_type)
        );
        """

        conn.execute(sql)

        # 创建索引
        conn.execute(f"CREATE INDEX idx_{table_name}_symbol_date ON {table_name}(symbol, report_date);")
        conn.execute(f"CREATE INDEX idx_{table_name}_report_date ON {table_name}(report_date);")
        conn.execute(f"CREATE INDEX idx_{table_name}_report_type ON {table_name}(report_type);")

        logger.info(f" 创建财务报表表: {table_name}")

    def _create_macro_table(self, conn, plugin_name: str):
        """创建宏观经济数据表"""
        table_name = generate_table_name(plugin_name, "macro_economic")

        if self._table_exists(conn, table_name):
            return

        sql = f"""
        CREATE TABLE {table_name} (
            indicator_code VARCHAR NOT NULL,
            date DATE NOT NULL,
            
            -- 基本信息
            indicator_name VARCHAR NOT NULL,
            value DECIMAL(20,6),
            unit VARCHAR,
            frequency VARCHAR, -- daily/weekly/monthly/quarterly/yearly
            
            -- 分类信息
            category_l1 VARCHAR,
            category_l2 VARCHAR,
            category_l3 VARCHAR,
            
            -- 地区信息
            country VARCHAR,
            region VARCHAR,
            
            -- 数据属性
            is_seasonally_adjusted BOOLEAN DEFAULT FALSE,
            is_preliminary BOOLEAN DEFAULT FALSE,
            revision_count INTEGER DEFAULT 0,
            
            -- 扩展字段
            plugin_specific_data JSON,
            
            -- 元数据
            data_source VARCHAR NOT NULL,
            data_quality_score DECIMAL(4,3),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            PRIMARY KEY (indicator_code, date)
        );
        """

        conn.execute(sql)

        # 创建索引
        conn.execute(f"CREATE INDEX idx_{table_name}_indicator_date ON {table_name}(indicator_code, date);")
        conn.execute(f"CREATE INDEX idx_{table_name}_category ON {table_name}(category_l1, category_l2);")
        conn.execute(f"CREATE INDEX idx_{table_name}_country_region ON {table_name}(country, region);")

        logger.info(f" 创建宏观数据表: {table_name}")

    def _table_exists(self, conn, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                [table_name]
            ).fetchone()
            return result is not None
        except:
            return False


class DataQualityMonitor:
    """数据质量监控器"""

    def __init__(self, sqlite_path: str = "data/factorweave_system.sqlite"):
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self):
        """初始化数据质量监控表"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS data_quality_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plugin_name TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        metric_date DATE NOT NULL,
                        
                        -- 完整性指标
                        total_records INTEGER DEFAULT 0,
                        null_records INTEGER DEFAULT 0,
                        duplicate_records INTEGER DEFAULT 0,
                        completeness_score DECIMAL(5,4) DEFAULT 0,
                        
                        -- 准确性指标
                        validation_errors INTEGER DEFAULT 0,
                        format_errors INTEGER DEFAULT 0,
                        range_errors INTEGER DEFAULT 0,
                        accuracy_score DECIMAL(5,4) DEFAULT 0,
                        
                        -- 及时性指标
                        data_delay_minutes INTEGER DEFAULT 0,
                        timeliness_score DECIMAL(5,4) DEFAULT 0,
                        
                        -- 一致性指标
                        consistency_errors INTEGER DEFAULT 0,
                        consistency_score DECIMAL(5,4) DEFAULT 0,
                        
                        -- 综合评分
                        overall_score DECIMAL(5,4) DEFAULT 0,
                        
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(plugin_name, table_name, metric_date)
                    )
                """)

                logger.info("数据质量监控表初始化完成")

        except Exception as e:
            logger.error(f" 数据质量监控表初始化失败: {e}")

    def start_monitoring(self) -> bool:
        """启动数据质量监控"""
        try:
            logger.info("启动数据质量监控...")
            # 这里可以添加定时监控逻辑
            # 目前只是标记监控已启动
            self._monitoring_active = True
            logger.info("数据质量监控已启动")
            return True
        except Exception as e:
            logger.error(f"启动数据质量监控失败: {e}")
            return False

    def validate_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证数据质量

        Args:
            data: 待验证的数据

        Returns:
            验证结果字典
        """
        try:
            result = {
                'overall_quality': 'good',
                'completeness': 0.95,
                'accuracy': 0.98,
                'consistency': 0.92,
                'timeliness': 0.88,
                'issues': [],
                'recommendations': []
            }

            # 检查数据完整性
            if not data or len(data) == 0:
                result['completeness'] = 0.0
                result['overall_quality'] = 'poor'
                result['issues'].append('数据为空')
                result['recommendations'].append('检查数据源连接')

            # 检查数据准确性
            if 'records' in data:
                records = data['records']
                if isinstance(records, list) and len(records) > 0:
                    # 模拟数据质量检查
                    null_count = sum(1 for record in records if not record)
                    if null_count > len(records) * 0.1:  # 超过10%的空记录
                        result['accuracy'] = max(0.0, 1.0 - (null_count / len(records)))
                        result['issues'].append(f'发现{null_count}条空记录')
                        result['recommendations'].append('清理空记录')

            # 更新总体质量评级
            avg_score = (result['completeness'] + result['accuracy'] +
                         result['consistency'] + result['timeliness']) / 4

            if avg_score >= 0.9:
                result['overall_quality'] = 'excellent'
            elif avg_score >= 0.8:
                result['overall_quality'] = 'good'
            elif avg_score >= 0.6:
                result['overall_quality'] = 'fair'
            else:
                result['overall_quality'] = 'poor'

            return result

        except Exception as e:
            logger.error(f"数据质量验证失败: {e}")
            return {
                'overall_quality': 'error',
                'completeness': 0.0,
                'accuracy': 0.0,
                'consistency': 0.0,
                'timeliness': 0.0,
                'issues': [f'验证过程出错: {str(e)}'],
                'recommendations': ['检查数据格式和验证逻辑']
            }

    def calculate_quality_score(self, data: pd.DataFrame, data_type: str, 
                                data_usage: str = 'general', data_source: str = None) -> float:
        """
        计算数据质量综合评分（智能权重系统）
        
        Args:
            data: 待评估的数据
            data_type: 数据类型
            data_usage: 数据用途 ('historical', 'realtime', 'backtest', 'live_trading', 'general')
            data_source: 数据源名称（用于可靠性调整）
            
        Returns:
            综合质量评分 (0.0-1.0)
        """
        if data is None or data.empty:
            return 0.0

        scores = {}

        # 完整性检查
        scores['completeness'] = self._check_completeness(data)

        # 准确性检查（增强版，包含异常值检测）
        scores['accuracy'] = self._check_accuracy_enhanced(data, data_type)

        # 一致性检查
        scores['consistency'] = self._check_consistency(data, data_type)

        # 及时性检查
        scores['timeliness'] = self._check_timeliness(data)

        # 🎯 智能权重配置：根据数据用途动态调整
        weights = self._get_dynamic_weights(data_usage)
        
        # 计算基础评分
        base_score = sum(scores[key] * weights[key] for key in scores)
        
        # 🌟 数据源可靠性调整（±5%）
        source_adjustment = self._get_source_reliability_adjustment(data_source)
        
        # 最终评分 = 基础评分 × 数据源系数
        final_score = min(1.0, base_score * source_adjustment)

        logger.debug(f"[质量评分] 用途:{data_usage}, 基础:{base_score:.3f}, "
                    f"数据源:{data_source}, 调整系数:{source_adjustment:.2f}, "
                    f"最终:{final_score:.3f}")

        return round(final_score, 4)
    
    def _get_dynamic_weights(self, data_usage: str) -> dict:
        """
        根据数据用途返回智能权重配置
        
        权重策略：
        - 历史分析：准确性>完整性>一致性>及时性
        - 实盘交易：及时性>准确性>完整性>一致性
        - 回测验证：准确性>一致性>完整性>及时性
        - 通用场景：平衡配置
        """
        weight_profiles = {
            # 历史数据分析（回测、研究、学习）
            'historical': {
                'completeness': 0.30,
                'accuracy': 0.40,     # 提高准确性权重
                'consistency': 0.25,   # 提高一致性权重
                'timeliness': 0.05     # 🔽 大幅降低及时性权重
            },
            
            # 回测验证
            'backtest': {
                'completeness': 0.25,
                'accuracy': 0.35,
                'consistency': 0.30,   # 回测需要高一致性
                'timeliness': 0.10
            },
            
            # 实时行情
            'realtime': {
                'completeness': 0.25,
                'accuracy': 0.30,
                'consistency': 0.15,
                'timeliness': 0.30     # 🔼 提高及时性权重
            },
            
            # 实盘交易
            'live_trading': {
                'completeness': 0.20,
                'accuracy': 0.35,
                'consistency': 0.10,
                'timeliness': 0.35     # 🔼 最高及时性权重
            },
            
            # 通用场景（默认）
            'general': {
                'completeness': 0.30,
                'accuracy': 0.30,
                'consistency': 0.20,
                'timeliness': 0.20
            }
        }
        
        weights = weight_profiles.get(data_usage, weight_profiles['general'])
        logger.debug(f"[权重配置] 用途:{data_usage}, 权重:{weights}")
        return weights
    
    def _get_source_reliability_adjustment(self, data_source: str) -> float:
        """
        数据源可靠性系数
        
        基于数据源的历史表现和业界口碑调整评分
        系数范围：0.95-1.05 (±5%)
        """
        if not data_source:
            return 1.0
        
        # 数据源可靠性评级（可根据实际情况调整）
        source_reliability = {
            # 高可靠性数据源 (+3~5%)
            'tushare': 1.05,           # 专业金融数据
            'wind': 1.05,              # Wind万得
            'tongdaxin': 1.03,         # 通达信
            
            # 标准可靠性数据源 (0~2%)
            'akshare': 1.00,           # 开源数据
            'baostock': 1.00,
            'eastmoney': 1.02,         # 东方财富
            
            # 待验证数据源 (-2~0%)
            'unknown': 0.98,
            'test': 0.95,
        }
        
        # 转换为小写进行匹配
        source_lower = data_source.lower()
        
        # 模糊匹配
        for key, coefficient in source_reliability.items():
            if key in source_lower:
                logger.debug(f"[数据源调整] {data_source} -> 系数:{coefficient}")
                return coefficient
        
        # 默认标准系数
        return 1.0

    def _check_completeness(self, data: pd.DataFrame) -> float:
        """检查数据完整性"""
        if data.empty:
            return 0.0

        total_cells = data.size
        null_cells = data.isnull().sum().sum()

        completeness = (total_cells - null_cells) / total_cells
        return completeness

    def _check_accuracy(self, data: pd.DataFrame, data_type: str) -> float:
        """检查数据准确性（保留旧方法以兼容）"""
        return self._check_accuracy_enhanced(data, data_type)
    
    def _check_accuracy_enhanced(self, data: pd.DataFrame, data_type: str) -> float:
        """
        检查数据准确性（增强版）
        
        新增检测项：
        1. OHLC逻辑关系
        2. 成交量合法性
        3. 🆕 价格异常波动检测
        4. 🆕 成交量异常检测
        5. 🆕 零值/重复值检测
        """
        accuracy_score = 1.0
        
        if data_type == "kline" or "kline" in data_type:
            # ============ 原有检查项 ============
            
            # 1. K线数据准确性检查
            required_cols = ['open', 'high', 'low', 'close']
            if all(col in data.columns for col in required_cols):
                # 检查OHLC逻辑关系
                invalid_ohlc = (
                    (data['high'] < data['open']) |
                    (data['high'] < data['close']) |
                    (data['low'] > data['open']) |
                    (data['low'] > data['close']) |
                    (data['high'] < data['low'])  # 新增：最高价<最低价
                )

                if invalid_ohlc.any():
                    error_rate = invalid_ohlc.sum() / len(data)
                    accuracy_score -= error_rate * 0.5
                    logger.debug(f"[准确性] OHLC逻辑错误率: {error_rate:.2%}")

            # 2. 检查成交量是否为负数
            if 'volume' in data.columns:
                negative_volume = (data['volume'] < 0).sum()
                if negative_volume > 0:
                    error_rate = negative_volume / len(data)
                    accuracy_score -= error_rate * 0.3
                    logger.debug(f"[准确性] 负成交量错误率: {error_rate:.2%}")
            
            # ============ 新增检查项 ============
            
            # 3. 🆕 价格异常波动检测（单日涨跌幅超过30%视为异常）
            if 'close' in data.columns and len(data) > 1:
                try:
                    close_pct_change = data['close'].pct_change().abs()
                    extreme_changes = close_pct_change > 0.30  # 30%阈值
                    if extreme_changes.any():
                        # 排除停牌复牌等正常情况（连续多日异常才扣分）
                        extreme_count = extreme_changes.sum()
                        if extreme_count > len(data) * 0.02:  # 超过2%的数据异常
                            error_rate = extreme_count / len(data)
                            accuracy_score -= error_rate * 0.15
                            logger.debug(f"[准确性] 价格异常波动: {extreme_count}条 ({error_rate:.2%})")
                except Exception as e:
                    logger.debug(f"[准确性] 价格波动检测失败: {e}")
            
            # 4. 🆕 成交量异常检测（成交量突增10倍以上）
            if 'volume' in data.columns and len(data) > 5:
                try:
                    volume_mean = data['volume'].rolling(window=5).mean()
                    volume_ratio = data['volume'] / volume_mean
                    extreme_volume = volume_ratio > 10  # 10倍阈值
                    if extreme_volume.any():
                        extreme_count = extreme_volume.sum()
                        if extreme_count > len(data) * 0.01:  # 超过1%
                            error_rate = extreme_count / len(data)
                            accuracy_score -= error_rate * 0.10
                            logger.debug(f"[准确性] 成交量异常: {extreme_count}条 ({error_rate:.2%})")
                except Exception as e:
                    logger.debug(f"[准确性] 成交量异常检测失败: {e}")
            
            # 5. 🆕 零值检测（收盘价为0通常是错误数据）
            if 'close' in data.columns:
                zero_prices = (data['close'] == 0).sum()
                if zero_prices > 0:
                    error_rate = zero_prices / len(data)
                    accuracy_score -= error_rate * 0.4
                    logger.debug(f"[准确性] 零价格数据: {zero_prices}条 ({error_rate:.2%})")
            
            # 6. 🆕 价格相等检测（OHLC全部相等可能是停牌数据）
            if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
                all_equal = (
                    (data['open'] == data['high']) &
                    (data['high'] == data['low']) &
                    (data['low'] == data['close'])
                )
                equal_count = all_equal.sum()
                if equal_count > len(data) * 0.2:  # 超过20%视为异常
                    error_rate = equal_count / len(data) - 0.2  # 允许20%停牌
                    if error_rate > 0:
                        accuracy_score -= error_rate * 0.1
                        logger.debug(f"[准确性] OHLC全相等: {equal_count}条 ({equal_count/len(data):.2%})")

        return max(0.0, accuracy_score)

    def _check_consistency(self, data: pd.DataFrame, data_type: str) -> float:
        """检查数据一致性"""
        consistency_score = 1.0

        # 检查时间序列连续性
        if 'datetime' in data.columns and len(data) > 1:
            data_sorted = data.sort_values('datetime')
            time_diffs = pd.to_datetime(data_sorted['datetime']).diff()

            # 检查是否有异常的时间跳跃
            if len(time_diffs) > 1:
                median_diff = time_diffs.median()
                if pd.notna(median_diff):
                    outliers = time_diffs > median_diff * 3

                    if outliers.any():
                        error_rate = outliers.sum() / len(time_diffs)
                        consistency_score -= error_rate * 0.2

        return consistency_score

    def _check_timeliness(self, data: pd.DataFrame) -> float:
        """检查数据及时性"""
        if 'datetime' in data.columns and not data.empty:
            try:
                latest_time = pd.to_datetime(data['datetime']).max()
                current_time = pd.Timestamp.now()

                # 计算数据延迟（分钟）
                delay_minutes = (current_time - latest_time).total_seconds() / 60

                # 根据延迟时间计算及时性评分
                if delay_minutes <= 5:
                    return 1.0
                elif delay_minutes <= 30:
                    return 0.8
                elif delay_minutes <= 60:
                    return 0.6
                elif delay_minutes <= 1440:  # 1天
                    return 0.4
                else:
                    return 0.2
            except:
                return 1.0

        return 1.0

    def record_quality_metrics(self, plugin_name: str, table_name: str,
                               data: pd.DataFrame, data_type: str,
                               data_usage: str = 'general', data_source: str = None):
        """
        记录数据质量指标（支持智能权重）
        
        Args:
            plugin_name: 插件名称
            table_name: 表名
            data: 数据
            data_type: 数据类型
            data_usage: 数据用途（用于智能权重）
            data_source: 数据源（用于可靠性调整）
        """
        try:
            # 计算各项指标
            completeness = self._check_completeness(data)
            accuracy = self._check_accuracy_enhanced(data, data_type)
            consistency = self._check_consistency(data, data_type)
            timeliness = self._check_timeliness(data)
            
            # 🎯 使用智能权重计算综合评分
            overall_score = self.calculate_quality_score(
                data, data_type, 
                data_usage=data_usage, 
                data_source=data_source
            )

            # 统计信息
            total_records = len(data) if data is not None else 0
            null_records = data.isnull().sum().sum() if data is not None else 0
            duplicate_records = data.duplicated().sum() if data is not None else 0

            # 保存到数据库
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO data_quality_metrics (
                        plugin_name, table_name, metric_date,
                        total_records, null_records, duplicate_records, completeness_score,
                        accuracy_score, timeliness_score, consistency_score, overall_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plugin_name, table_name, date.today(),
                    total_records, null_records, duplicate_records, completeness,
                    accuracy, timeliness, consistency, overall_score
                ))
                
                logger.debug(f"[质量记录] {plugin_name}.{table_name} - "
                           f"用途:{data_usage}, 评分:{overall_score:.3f}")

        except Exception as e:
            logger.error(f" 记录数据质量指标失败: {e}")


class FieldMappingManager:
    """字段映射管理器"""

    def __init__(self, sqlite_path: str = "data/factorweave_system.sqlite"):
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self):
        """初始化字段映射表"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS field_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plugin_name TEXT NOT NULL,
                        data_type TEXT NOT NULL,
                        source_field TEXT NOT NULL,
                        target_field TEXT NOT NULL,
                        field_type TEXT NOT NULL,
                        transform_rule TEXT DEFAULT '{}',
                        validation_rule TEXT DEFAULT '{}',
                        is_required BOOLEAN DEFAULT 0,
                        default_value TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(plugin_name, data_type, source_field)
                    )
                """)

                logger.info("字段映射表初始化完成")

        except Exception as e:
            logger.error(f" 字段映射表初始化失败: {e}")

    def register_plugin_mappings(self, plugin: IDataSourcePlugin) -> bool:
        """注册插件字段映射"""
        try:
            plugin_name = plugin.plugin_info.id

            # 获取插件的字段映射配置
            if hasattr(plugin.plugin_info, 'capabilities') and plugin.plugin_info.capabilities:
                field_mappings = plugin.plugin_info.capabilities.get('field_mappings', {})

                with sqlite3.connect(self.sqlite_path) as conn:
                    for data_type, mappings in field_mappings.items():
                        for source_field, target_field in mappings.items():
                            conn.execute("""
                                INSERT OR REPLACE INTO field_mappings (
                                    plugin_name, data_type, source_field, target_field, field_type
                                ) VALUES (?, ?, ?, ?, ?)
                            """, (plugin_name, data_type, source_field, target_field, 'string'))

                logger.info(f" 插件字段映射注册完成: {plugin_name}")
                return True

        except Exception as e:
            logger.error(f" 注册插件字段映射失败: {e}")
            return False

    def get_field_mapping(self, plugin_name: str, data_type: str) -> Dict[str, str]:
        """获取字段映射"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.execute("""
                    SELECT source_field, target_field FROM field_mappings
                    WHERE plugin_name = ? AND data_type = ?
                """, (plugin_name, data_type))

                mappings = {}
                for row in cursor.fetchall():
                    mappings[row[0]] = row[1]

                return mappings

        except Exception as e:
            logger.error(f" 获取字段映射失败: {e}")
            return {}
