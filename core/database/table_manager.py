"""
DuckDB动态表管理器

提供DuckDB数据表的动态管理，包括：
- 按插件名动态创建表
- 表结构版本管理
- 索引自动创建
- 分区策略实施
- 表结构迁移

作者: FactorWeave-Quant团队
版本: 1.0
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json
import re
from datetime import datetime, date

from .duckdb_manager import DuckDBConnectionManager, get_connection_manager
from ..plugin_types import DataType

logger = logging.getLogger(__name__)


class TableType(Enum):
    """表类型枚举"""
    STOCK_BASIC_INFO = "stock_basic_info"
    KLINE_DATA = "kline_data"
    FINANCIAL_STATEMENT = "financial_statement"
    MACRO_ECONOMIC = "macro_economic"
    REAL_TIME_QUOTE = "real_time_quote"
    MARKET_DEPTH = "market_depth"
    TRADE_TICK = "trade_tick"
    NEWS = "news"
    ANNOUNCEMENT = "announcement"
    FUND_FLOW = "fund_flow"
    TECHNICAL_INDICATOR = "technical_indicator"


@dataclass
class TableSchema:
    """表结构定义"""
    table_type: TableType
    columns: Dict[str, str]  # 列名 -> 数据类型
    primary_key: List[str]
    indexes: List[Dict[str, Any]]  # 索引定义
    partitions: Optional[Dict[str, Any]] = None  # 分区定义
    constraints: Optional[List[str]] = None  # 约束条件
    version: str = "1.0"


class TableSchemaRegistry:
    """表结构注册表"""

    def __init__(self):
        """初始化表结构注册表"""
        self._schemas: Dict[TableType, TableSchema] = {}
        self._initialize_default_schemas()

    def _initialize_default_schemas(self):
        """初始化默认表结构"""

        # 股票基础信息表
        self._schemas[TableType.STOCK_BASIC_INFO] = TableSchema(
            table_type=TableType.STOCK_BASIC_INFO,
            columns={
                'symbol': 'VARCHAR NOT NULL',
                'name': 'VARCHAR NOT NULL',
                'market': 'VARCHAR NOT NULL',
                'exchange': 'VARCHAR',
                'industry_l1': 'VARCHAR',
                'industry_l2': 'VARCHAR',
                'industry_l3': 'VARCHAR',
                'concept_plates': 'VARCHAR[]',
                'list_date': 'DATE',
                'delist_date': 'DATE',
                'total_shares': 'BIGINT',
                'float_shares': 'BIGINT',
                'market_cap': 'DECIMAL(20,2)',
                'float_market_cap': 'DECIMAL(20,2)',
                'pe_ratio': 'DECIMAL(10,4)',
                'pb_ratio': 'DECIMAL(10,4)',
                'ps_ratio': 'DECIMAL(10,4)',
                'ev_ebitda': 'DECIMAL(10,4)',
                'beta': 'DECIMAL(10,6)',
                'ma5': 'DECIMAL(10,4)',
                'ma10': 'DECIMAL(10,4)',
                'ma20': 'DECIMAL(10,4)',
                'ma60': 'DECIMAL(10,4)',
                'plugin_specific_data': 'JSON',
                'data_source': 'VARCHAR NOT NULL',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'data_quality_score': 'DECIMAL(3,2)'
            },
            primary_key=['symbol'],
            indexes=[
                {'name': 'idx_market', 'columns': ['market']},
                {'name': 'idx_industry', 'columns': ['industry_l1', 'industry_l2']},
                {'name': 'idx_list_date', 'columns': ['list_date']},
                {'name': 'idx_market_cap', 'columns': ['market_cap']},
                {'name': 'idx_data_source', 'columns': ['data_source']},
                {'name': 'idx_updated_at', 'columns': ['updated_at']}
            ]
        )

        # K线数据表
        self._schemas[TableType.KLINE_DATA] = TableSchema(
            table_type=TableType.KLINE_DATA,
            columns={
                'symbol': 'VARCHAR NOT NULL',
                'datetime': 'TIMESTAMP NOT NULL',
                'open': 'DECIMAL(10,4) NOT NULL',
                'high': 'DECIMAL(10,4) NOT NULL',
                'low': 'DECIMAL(10,4) NOT NULL',
                'close': 'DECIMAL(10,4) NOT NULL',
                'volume': 'BIGINT NOT NULL',
                'amount': 'DECIMAL(20,2)',
                'adj_close': 'DECIMAL(10,4)',
                'adj_factor': 'DECIMAL(10,6)',
                'vwap': 'DECIMAL(10,4)',
                'bid_price': 'DECIMAL(10,4)',
                'ask_price': 'DECIMAL(10,4)',
                'bid_volume': 'BIGINT',
                'ask_volume': 'BIGINT',
                'rsi_14': 'DECIMAL(10,4)',
                'macd_dif': 'DECIMAL(10,4)',
                'macd_dea': 'DECIMAL(10,4)',
                'macd_histogram': 'DECIMAL(10,4)',
                'kdj_k': 'DECIMAL(10,4)',
                'kdj_d': 'DECIMAL(10,4)',
                'kdj_j': 'DECIMAL(10,4)',
                'bollinger_upper': 'DECIMAL(10,4)',
                'bollinger_middle': 'DECIMAL(10,4)',
                'bollinger_lower': 'DECIMAL(10,4)',
                'turnover_rate': 'DECIMAL(10,4)',
                'net_inflow_large': 'DECIMAL(20,2)',
                'net_inflow_medium': 'DECIMAL(20,2)',
                'net_inflow_small': 'DECIMAL(20,2)',
                'plugin_specific_data': 'JSON',
                'data_source': 'VARCHAR NOT NULL',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'data_quality_score': 'DECIMAL(3,2)'
            },
            primary_key=['symbol', 'datetime'],
            indexes=[
                {'name': 'idx_symbol', 'columns': ['symbol']},
                {'name': 'idx_datetime', 'columns': ['datetime']},
                {'name': 'idx_symbol_datetime', 'columns': ['symbol', 'datetime']},
                {'name': 'idx_volume', 'columns': ['volume']},
                {'name': 'idx_amount', 'columns': ['amount']},
                {'name': 'idx_data_source', 'columns': ['data_source']}
            ],
            partitions={
                'type': 'range',
                'column': 'datetime',
                'interval': 'MONTH'
            }
        )

        # 财务报表表
        self._schemas[TableType.FINANCIAL_STATEMENT] = TableSchema(
            table_type=TableType.FINANCIAL_STATEMENT,
            columns={
                'symbol': 'VARCHAR NOT NULL',
                'report_date': 'DATE NOT NULL',
                'report_type': 'VARCHAR NOT NULL',
                'report_period': 'VARCHAR',
                # 资产负债表
                'total_assets': 'DECIMAL(20,2)',
                'current_assets': 'DECIMAL(20,2)',
                'non_current_assets': 'DECIMAL(20,2)',
                'total_liabilities': 'DECIMAL(20,2)',
                'current_liabilities': 'DECIMAL(20,2)',
                'non_current_liabilities': 'DECIMAL(20,2)',
                'shareholders_equity': 'DECIMAL(20,2)',
                'paid_in_capital': 'DECIMAL(20,2)',
                'retained_earnings': 'DECIMAL(20,2)',
                # 利润表
                'operating_revenue': 'DECIMAL(20,2)',
                'operating_costs': 'DECIMAL(20,2)',
                'gross_profit': 'DECIMAL(20,2)',
                'operating_expenses': 'DECIMAL(20,2)',
                'operating_profit': 'DECIMAL(20,2)',
                'net_profit': 'DECIMAL(20,2)',
                'eps': 'DECIMAL(10,4)',
                'diluted_eps': 'DECIMAL(10,4)',
                # 现金流量表
                'operating_cash_flow': 'DECIMAL(20,2)',
                'investing_cash_flow': 'DECIMAL(20,2)',
                'financing_cash_flow': 'DECIMAL(20,2)',
                'net_cash_flow': 'DECIMAL(20,2)',
                # 财务比率
                'roe': 'DECIMAL(10,4)',
                'roa': 'DECIMAL(10,4)',
                'debt_to_equity': 'DECIMAL(10,4)',
                'current_ratio': 'DECIMAL(10,4)',
                'quick_ratio': 'DECIMAL(10,4)',
                'gross_margin': 'DECIMAL(10,4)',
                'net_margin': 'DECIMAL(10,4)',
                # 元数据
                'plugin_specific_data': 'JSON',
                'data_source': 'VARCHAR NOT NULL',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'data_quality_score': 'DECIMAL(3,2)'
            },
            primary_key=['symbol', 'report_date', 'report_type'],
            indexes=[
                {'name': 'idx_symbol', 'columns': ['symbol']},
                {'name': 'idx_report_date', 'columns': ['report_date']},
                {'name': 'idx_report_type', 'columns': ['report_type']},
                {'name': 'idx_symbol_date', 'columns': ['symbol', 'report_date']},
                {'name': 'idx_data_source', 'columns': ['data_source']}
            ]
        )

        # 宏观经济数据表
        self._schemas[TableType.MACRO_ECONOMIC] = TableSchema(
            table_type=TableType.MACRO_ECONOMIC,
            columns={
                'indicator_code': 'VARCHAR NOT NULL',
                'data_date': 'DATE NOT NULL',
                'value': 'DECIMAL(20,6) NOT NULL',
                'indicator_name': 'VARCHAR NOT NULL',
                'frequency': 'VARCHAR NOT NULL',
                'unit': 'VARCHAR',
                'category': 'VARCHAR',
                'subcategory': 'VARCHAR',
                'country': 'VARCHAR DEFAULT \'CN\'',
                'region': 'VARCHAR',
                'seasonally_adjusted': 'BOOLEAN DEFAULT FALSE',
                'data_source': 'VARCHAR NOT NULL',
                'source_code': 'VARCHAR',
                'release_date': 'DATE',
                'revision_date': 'DATE',
                'plugin_specific_data': 'JSON',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'data_quality_score': 'DECIMAL(3,2)'
            },
            primary_key=['indicator_code', 'data_date'],
            indexes=[
                {'name': 'idx_indicator_code', 'columns': ['indicator_code']},
                {'name': 'idx_data_date', 'columns': ['data_date']},
                {'name': 'idx_category', 'columns': ['category', 'subcategory']},
                {'name': 'idx_country', 'columns': ['country', 'region']},
                {'name': 'idx_frequency', 'columns': ['frequency']},
                {'name': 'idx_data_source', 'columns': ['data_source']}
            ]
        )

        logger.info("默认表结构初始化完成")

    def get_schema(self, table_type: TableType) -> Optional[TableSchema]:
        """获取表结构"""
        return self._schemas.get(table_type)

    def register_schema(self, schema: TableSchema):
        """注册表结构"""
        self._schemas[schema.table_type] = schema
        logger.info(f"表结构已注册: {schema.table_type}")

    def get_all_schemas(self) -> Dict[TableType, TableSchema]:
        """获取所有表结构"""
        return self._schemas.copy()


class DynamicTableManager:
    """动态表管理器"""

    def __init__(self, connection_manager: Optional[DuckDBConnectionManager] = None):
        """
        初始化动态表管理器

        Args:
            connection_manager: DuckDB连接管理器
        """
        self.connection_manager = connection_manager or get_connection_manager()
        self.schema_registry = TableSchemaRegistry()

        # 表名缓存
        self._table_cache: Dict[str, bool] = {}

        logger.info("动态表管理器初始化完成")

    def generate_table_name(self, table_type: TableType, plugin_name: str,
                            period: Optional[str] = None) -> str:
        """
        生成动态表名

        Args:
            table_type: 表类型
            plugin_name: 插件名称
            period: 数据周期（可选）

        Returns:
            表名
        """
        # 清理插件名称（移除特殊字符）
        clean_plugin_name = re.sub(r'[^a-zA-Z0-9_]', '_', plugin_name.lower())

        # 基础表名
        base_name = f"{table_type.value}_{clean_plugin_name}"

        # 如果有周期，添加到表名中
        if period:
            clean_period = re.sub(r'[^a-zA-Z0-9_]', '_', period.lower())
            base_name = f"{base_name}_{clean_period}"

        return base_name

    def table_exists(self, database_path: str, table_name: str) -> bool:
        """
        检查表是否存在

        Args:
            database_path: 数据库路径
            table_name: 表名

        Returns:
            表是否存在
        """
        cache_key = f"{database_path}:{table_name}"

        # 检查缓存
        if cache_key in self._table_cache:
            return self._table_cache[cache_key]

        try:
            with self.connection_manager.get_connection(database_path) as conn:
                result = conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                    [table_name]
                ).fetchone()

                exists = result[0] > 0
                self._table_cache[cache_key] = exists
                return exists

        except Exception as e:
            logger.error(f"检查表存在性失败 {table_name}: {e}")
            return False

    def create_table(self, database_path: str, table_type: TableType,
                     plugin_name: str, period: Optional[str] = None,
                     custom_schema: Optional[TableSchema] = None) -> bool:
        """
        创建表

        Args:
            database_path: 数据库路径
            table_type: 表类型
            plugin_name: 插件名称
            period: 数据周期（可选）
            custom_schema: 自定义表结构（可选）

        Returns:
            创建是否成功
        """
        try:
            # 生成表名
            table_name = self.generate_table_name(table_type, plugin_name, period)

            # 检查表是否已存在
            if self.table_exists(database_path, table_name):
                logger.info(f"表已存在: {table_name}")
                return True

            # 获取表结构
            schema = custom_schema or self.schema_registry.get_schema(table_type)
            if not schema:
                logger.error(f"未找到表结构: {table_type}")
                return False

            # 生成CREATE TABLE语句
            create_sql = self._generate_create_table_sql(table_name, schema)

            # 执行创建表
            with self.connection_manager.get_connection(database_path) as conn:
                conn.execute(create_sql)
                logger.info(f"表创建成功: {table_name}")

                # 创建索引
                self._create_indexes(conn, table_name, schema)

                # 创建分区（如果需要）
                if schema.partitions:
                    self._create_partitions(conn, table_name, schema)

            # 更新缓存
            cache_key = f"{database_path}:{table_name}"
            self._table_cache[cache_key] = True

            return True

        except Exception as e:
            logger.error(f"创建表失败 {table_type} {plugin_name}: {e}")
            return False

    def _generate_create_table_sql(self, table_name: str, schema: TableSchema) -> str:
        """生成CREATE TABLE SQL语句"""
        columns_sql = []

        for column_name, column_type in schema.columns.items():
            columns_sql.append(f"    {column_name} {column_type}")

        # 添加主键约束
        if schema.primary_key:
            pk_columns = ', '.join(schema.primary_key)
            columns_sql.append(f"    PRIMARY KEY ({pk_columns})")

        # 添加其他约束
        if schema.constraints:
            for constraint in schema.constraints:
                columns_sql.append(f"    {constraint}")

        # 修复f-string中的反斜杠问题
        columns_joined = ',\n'.join(columns_sql)
        create_sql = f"""
CREATE TABLE {table_name} (
{columns_joined}
)"""

        return create_sql

    def _create_indexes(self, conn, table_name: str, schema: TableSchema):
        """创建索引"""
        try:
            for index_def in schema.indexes:
                index_name = f"{table_name}_{index_def['name']}"
                columns = ', '.join(index_def['columns'])

                # 检查索引类型
                index_type = index_def.get('type', 'BTREE')
                unique = 'UNIQUE ' if index_def.get('unique', False) else ''

                # DuckDB不支持USING子句，直接创建索引
                index_sql = f"CREATE {unique}INDEX {index_name} ON {table_name} ({columns})"

                conn.execute(index_sql)
                logger.debug(f"索引创建成功: {index_name}")

        except Exception as e:
            logger.error(f"创建索引失败 {table_name}: {e}")

    def _create_partitions(self, conn, table_name: str, schema: TableSchema):
        """创建分区（DuckDB暂不完全支持，预留接口）"""
        try:
            partition_info = schema.partitions
            if partition_info['type'] == 'range':
                # DuckDB的分区功能有限，这里主要是预留接口
                logger.info(f"分区配置已记录: {table_name} - {partition_info}")

        except Exception as e:
            logger.error(f"创建分区失败 {table_name}: {e}")

    def drop_table(self, database_path: str, table_type: TableType,
                   plugin_name: str, period: Optional[str] = None) -> bool:
        """
        删除表

        Args:
            database_path: 数据库路径
            table_type: 表类型
            plugin_name: 插件名称
            period: 数据周期（可选）

        Returns:
            删除是否成功
        """
        try:
            table_name = self.generate_table_name(table_type, plugin_name, period)

            if not self.table_exists(database_path, table_name):
                logger.info(f"表不存在: {table_name}")
                return True

            with self.connection_manager.get_connection(database_path) as conn:
                conn.execute(f"DROP TABLE {table_name}")
                logger.info(f"表删除成功: {table_name}")

            # 更新缓存
            cache_key = f"{database_path}:{table_name}"
            self._table_cache[cache_key] = False

            return True

        except Exception as e:
            logger.error(f"删除表失败 {table_type} {plugin_name}: {e}")
            return False

    def get_table_info(self, database_path: str, table_name: str) -> Optional[Dict[str, Any]]:
        """
        获取表信息

        Args:
            database_path: 数据库路径
            table_name: 表名

        Returns:
            表信息
        """
        try:
            with self.connection_manager.get_connection(database_path) as conn:
                # 获取表结构信息
                columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()

                # 获取索引信息（DuckDB使用duckdb_indexes系统表）
                try:
                    indexes_info = conn.execute(
                        "SELECT index_name, column_names, is_unique FROM duckdb_indexes() WHERE table_name = ?",
                        [table_name]
                    ).fetchall()
                except Exception:
                    # 如果系统表不可用，返回空列表
                    indexes_info = []

                # 获取表统计信息
                stats = conn.execute(f"SELECT COUNT(*) as row_count FROM {table_name}").fetchone()

                return {
                    'table_name': table_name,
                    'columns': columns_info,
                    'indexes': indexes_info,
                    'row_count': stats[0] if stats else 0,
                    'database_path': database_path
                }

        except Exception as e:
            logger.error(f"获取表信息失败 {table_name}: {e}")
            return None

    def list_tables(self, database_path: str, plugin_name: Optional[str] = None) -> List[str]:
        """
        列出表

        Args:
            database_path: 数据库路径
            plugin_name: 插件名称过滤（可选）

        Returns:
            表名列表
        """
        try:
            with self.connection_manager.get_connection(database_path) as conn:
                if plugin_name:
                    # 过滤特定插件的表
                    clean_plugin_name = re.sub(r'[^a-zA-Z0-9_]', '_', plugin_name.lower())
                    pattern = f"%_{clean_plugin_name}%"

                    result = conn.execute(
                        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE ?",
                        [pattern]
                    ).fetchall()
                else:
                    # 获取所有表
                    result = conn.execute(
                        "SELECT table_name FROM information_schema.tables"
                    ).fetchall()

                return [row[0] for row in result]

        except Exception as e:
            logger.error(f"列出表失败: {e}")
            return []

    def migrate_table_schema(self, database_path: str, table_name: str,
                             new_schema: TableSchema) -> bool:
        """
        迁移表结构

        Args:
            database_path: 数据库路径
            table_name: 表名
            new_schema: 新的表结构

        Returns:
            迁移是否成功
        """
        try:
            with self.connection_manager.get_connection(database_path) as conn:
                # 获取当前表结构
                current_columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
                current_column_names = {col[0] for col in current_columns}

                # 比较新旧结构，生成迁移SQL
                migration_sqls = []

                for column_name, column_type in new_schema.columns.items():
                    if column_name not in current_column_names:
                        # 添加新列
                        migration_sqls.append(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

                # 执行迁移
                for sql in migration_sqls:
                    conn.execute(sql)
                    logger.debug(f"执行迁移SQL: {sql}")

                logger.info(f"表结构迁移完成: {table_name}")
                return True

        except Exception as e:
            logger.error(f"表结构迁移失败 {table_name}: {e}")
            return False

    def clear_table_cache(self):
        """清理表缓存"""
        self._table_cache.clear()
        logger.info("表缓存已清理")

    def get_table_statistics(self, database_path: str) -> Dict[str, Any]:
        """
        获取数据库表统计信息

        Args:
            database_path: 数据库路径

        Returns:
            统计信息
        """
        try:
            with self.connection_manager.get_connection(database_path) as conn:
                # 获取表数量
                table_count = conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables"
                ).fetchone()[0]

                # 获取各类型表的数量
                type_counts = {}
                for table_type in TableType:
                    pattern = f"{table_type.value}_%"
                    count = conn.execute(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE ?",
                        [pattern]
                    ).fetchone()[0]
                    type_counts[table_type.value] = count

                # 获取数据库大小信息
                db_size = conn.execute("SELECT pg_database_size(current_database())").fetchone()

                return {
                    'database_path': database_path,
                    'total_tables': table_count,
                    'table_type_counts': type_counts,
                    'database_size_bytes': db_size[0] if db_size else 0,
                    'cache_size': len(self._table_cache)
                }

        except Exception as e:
            logger.error(f"获取表统计信息失败: {e}")
            return {
                'database_path': database_path,
                'error': str(e)
            }


# 全局表管理器实例
_table_manager: Optional[DynamicTableManager] = None


def get_table_manager() -> DynamicTableManager:
    """获取全局表管理器实例"""
    global _table_manager

    if _table_manager is None:
        _table_manager = DynamicTableManager()

    return _table_manager
