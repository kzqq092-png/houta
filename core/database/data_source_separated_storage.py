#!/usr/bin/env python3
"""
按数据源分离存储管理器

为每个数据源插件创建独立的数据库文件和表结构，
确保数据源之间的数据隔离，防止数据错乱。

特性：
- 每个数据源使用独立的数据库文件
- 数据导入时只使用指定的数据源
- 提供数据源之间的隔离保护
- 支持数据源级别的备份和恢复

作者: FactorWeave-Quant团队
版本: 1.0
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import sqlite3
import pandas as pd
from datetime import datetime

from .table_manager import TableType, DynamicTableManager, get_table_manager
from .duckdb_manager import DuckDBConnectionManager, get_connection_manager
from ..plugin_types import DataType, AssetType


class DataSourceIsolationLevel(Enum):
    """数据源隔离级别"""
    NONE = "none"           # 不隔离，所有数据源共享
    DATABASE = "database"   # 数据库级别隔离，每个数据源独立数据库
    SCHEMA = "schema"       # 模式级别隔离，同一数据库下不同模式
    TABLE = "table"         # 表级别隔离，表名包含数据源标识


@dataclass
class DataSourceStorageConfig:
    """数据源存储配置"""
    plugin_id: str                          # 插件ID
    plugin_name: str                        # 插件名称
    isolation_level: DataSourceIsolationLevel  # 隔离级别
    database_path: str                      # 数据库路径
    schema_prefix: str = ""                 # 模式前缀
    table_prefix: str = ""                  # 表前缀
    auto_create_tables: bool = True         # 自动创建表
    enable_compression: bool = True         # 启用压缩
    max_database_size_mb: int = 1024        # 最大数据库大小（MB）


class DataSourceSeparatedStorageManager:
    """按数据源分离存储管理器"""

    def __init__(self, base_db_dir: str = "db/datasource_separated"):
        """
        初始化分离存储管理器

        Args:
            base_db_dir: 数据库文件基础目录
        """
        self.base_db_dir = Path(base_db_dir)
        self.base_db_dir.mkdir(parents=True, exist_ok=True)

        # 存储配置
        self._storage_configs: Dict[str, DataSourceStorageConfig] = {}

        # 活跃的数据源连接
        self._active_sources: Set[str] = set()

        # 表管理器和连接管理器
        self.table_manager = get_table_manager()
        self.connection_manager = get_connection_manager()

        # 加载配置
        self._load_storage_configs()

        logger.info(f"数据源分离存储管理器初始化完成: {self.base_db_dir}")

    def register_data_source(self, plugin_id: str, plugin_name: str,
                             isolation_level: DataSourceIsolationLevel = DataSourceIsolationLevel.DATABASE,
                             custom_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        注册数据源存储配置

        Args:
            plugin_id: 插件ID
            plugin_name: 插件名称
            isolation_level: 隔离级别
            custom_config: 自定义配置

        Returns:
            注册是否成功
        """
        try:
            # 清理插件ID中的特殊字符
            clean_plugin_id = self._clean_plugin_id(plugin_id)

            # 生成数据库路径
            if isolation_level == DataSourceIsolationLevel.DATABASE:
                db_path = str(self.base_db_dir / f"{clean_plugin_id}.duckdb")
            else:
                db_path = str(self.base_db_dir / "shared.duckdb")

            # 创建存储配置
            config = DataSourceStorageConfig(
                plugin_id=plugin_id,
                plugin_name=plugin_name,
                isolation_level=isolation_level,
                database_path=db_path,
                schema_prefix=clean_plugin_id if isolation_level == DataSourceIsolationLevel.SCHEMA else "",
                table_prefix=clean_plugin_id if isolation_level == DataSourceIsolationLevel.TABLE else ""
            )

            # 应用自定义配置
            if custom_config:
                for key, value in custom_config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            # 保存配置
            self._storage_configs[plugin_id] = config

            # 创建数据库目录
            db_dir = Path(config.database_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            # 保存配置到文件
            self._save_storage_configs()

            logger.info(f"数据源存储配置注册成功: {plugin_id} -> {config.database_path}")
            return True

        except Exception as e:
            logger.error(f"注册数据源存储配置失败 {plugin_id}: {e}")
            return False

    def get_storage_config(self, plugin_id: str) -> Optional[DataSourceStorageConfig]:
        """获取数据源存储配置"""
        return self._storage_configs.get(plugin_id)

    def get_database_path(self, plugin_id: str) -> Optional[str]:
        """获取数据源的数据库路径"""
        config = self.get_storage_config(plugin_id)
        return config.database_path if config else None

    def create_table_for_data_source(self, plugin_id: str, table_type: TableType,
                                     period: Optional[str] = None,
                                     custom_schema: Optional[Any] = None) -> Optional[str]:
        """
        为指定数据源创建表

        Args:
            plugin_id: 插件ID
            table_type: 表类型
            period: 数据周期
            custom_schema: 自定义表结构

        Returns:
            创建的表名，失败返回None
        """
        try:
            config = self.get_storage_config(plugin_id)
            if not config:
                logger.error(f"未找到数据源存储配置: {plugin_id}")
                return None

            # 使用表管理器生成标准表名，确保一致性
            table_name = self.table_manager.generate_table_name(
                table_type=table_type,
                plugin_name=config.plugin_name,
                period=period
            )

            # 检查表是否已存在
            if self._table_exists(config.database_path, table_name):
                logger.debug(f"表已存在: {table_name}")
                return table_name

            # 创建表
            success = self.table_manager.create_table(
                database_path=config.database_path,
                table_type=table_type,
                plugin_name=config.plugin_name,
                period=period,
                custom_schema=custom_schema
            )

            if success:
                logger.info(f"为数据源 {plugin_id} 创建表成功: {table_name}")
                return table_name
            else:
                logger.error(f"为数据源 {plugin_id} 创建表失败: {table_name}")
                return None

        except Exception as e:
            logger.error(f"创建数据源表失败 {plugin_id}: {e}")
            return None

    def save_data_to_source(self, plugin_id: str, table_type: TableType,
                            data: pd.DataFrame, symbol: str = None,
                            period: Optional[str] = None,
                            upsert: bool = True) -> bool:
        """
        保存数据到指定数据源的表中（自动创建数据库、表结构和索引）

        Args:
            plugin_id: 插件ID
            table_type: 表类型
            data: 要保存的数据
            symbol: 股票代码（如果适用）
            period: 数据周期
            upsert: 是否使用upsert模式

        Returns:
            保存是否成功
        """
        try:
            # 自动注册数据源（如果未注册）
            config = self.get_storage_config(plugin_id)
            if not config:
                logger.info(f"数据源未注册，自动注册: {plugin_id}")
                success = self.register_data_source(
                    plugin_id=plugin_id,
                    plugin_name=plugin_id,
                    isolation_level=DataSourceIsolationLevel.DATABASE
                )
                if not success:
                    logger.error(f"自动注册数据源失败: {plugin_id}")
                    return False
                config = self.get_storage_config(plugin_id)

            # 自动创建数据库目录
            db_dir = Path(config.database_path).parent
            if not db_dir.exists():
                db_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建数据库目录: {db_dir}")

            # 自动创建表结构和索引
            table_name = self._auto_create_table_and_indexes(plugin_id, table_type, period, config)
            if not table_name:
                logger.error(f"无法创建表和索引: {plugin_id}, {table_type}")
                return False

            # 添加数据源标识
            data_with_source = data.copy()
            data_with_source['data_source'] = plugin_id
            data_with_source['created_at'] = datetime.now()

            if symbol:
                data_with_source['symbol'] = symbol

            # 使用DuckDB操作保存数据
            from .duckdb_operations import get_duckdb_operations
            duckdb_ops = get_duckdb_operations()

            if not duckdb_ops:
                logger.error("DuckDB操作实例不可用")
                return False

            # 确定冲突列（基于表的主键）
            conflict_columns = ['symbol', 'datetime'] if 'datetime' in data_with_source.columns else ['symbol']

            # 插入数据
            result = duckdb_ops.insert_dataframe(
                database_path=config.database_path,
                table_name=table_name,
                data=data_with_source,
                upsert=upsert,
                conflict_columns=conflict_columns
            )

            if result.success:
                logger.info(f"数据保存成功: {plugin_id}, {len(data)}条记录 -> {table_name}")
                return True
            else:
                logger.error(f"数据保存失败: {plugin_id}, {result.error_message}")
                return False

        except Exception as e:
            logger.error(f"保存数据到数据源失败 {plugin_id}: {e}")
            return False

    def query_data_from_source(self, plugin_id: str, table_type: TableType,
                               symbol: str = None, start_date: str = None,
                               end_date: str = None, period: Optional[str] = None,
                               limit: int = None) -> Optional[pd.DataFrame]:
        """
        从指定数据源查询数据

        Args:
            plugin_id: 插件ID
            table_type: 表类型
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            limit: 查询限制

        Returns:
            查询结果DataFrame，失败返回None
        """
        try:
            config = self.get_storage_config(plugin_id)
            if not config:
                logger.error(f"数据源未注册: {plugin_id}")
                return None

            # 生成表名
            table_name = self._generate_table_name(config, table_type, period)

            # 检查表是否存在
            if not self._table_exists(config.database_path, table_name):
                logger.warning(f"表不存在: {table_name}")
                return pd.DataFrame()

            # 构建查询SQL
            sql = f"SELECT * FROM {table_name} WHERE data_source = '{plugin_id}'"

            if symbol:
                sql += f" AND symbol = '{symbol}'"

            if start_date:
                sql += f" AND datetime >= '{start_date}'"

            if end_date:
                sql += f" AND datetime <= '{end_date}'"

            sql += " ORDER BY datetime"

            if limit:
                sql += f" LIMIT {limit}"

            # 执行查询
            from .duckdb_operations import get_duckdb_operations
            duckdb_ops = get_duckdb_operations()

            if not duckdb_ops:
                logger.error("DuckDB操作实例不可用")
                return None

            result = duckdb_ops.execute_query(config.database_path, sql)

            if result.success:
                logger.debug(f"从数据源查询数据成功: {plugin_id}, {len(result.data)}条记录")
                return result.data
            else:
                logger.error(f"查询数据失败: {plugin_id}, {result.error_message}")
                return None

        except Exception as e:
            logger.error(f"从数据源查询数据失败 {plugin_id}: {e}")
            return None

    def list_available_data_sources(self) -> List[Dict[str, Any]]:
        """列出所有可用的数据源"""
        sources = []
        for plugin_id, config in self._storage_configs.items():
            sources.append({
                'plugin_id': plugin_id,
                'plugin_name': config.plugin_name,
                'isolation_level': config.isolation_level.value,
                'database_path': config.database_path,
                'is_active': plugin_id in self._active_sources
            })
        return sources

    def get_data_source_statistics(self, plugin_id: str) -> Dict[str, Any]:
        """获取数据源统计信息"""
        try:
            config = self.get_storage_config(plugin_id)
            if not config:
                return {}

            stats = {
                'plugin_id': plugin_id,
                'plugin_name': config.plugin_name,
                'database_path': config.database_path,
                'database_size_mb': 0,
                'table_count': 0,
                'record_count': 0
            }

            # 获取数据库文件大小
            if os.path.exists(config.database_path):
                stats['database_size_mb'] = os.path.getsize(config.database_path) / (1024 * 1024)

            # 获取表统计信息
            from .duckdb_operations import get_duckdb_operations
            duckdb_ops = get_duckdb_operations()

            if duckdb_ops:
                # 查询表数量
                table_result = duckdb_ops.execute_query(
                    config.database_path,
                    "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'main'"
                )
                if table_result.success and not table_result.data.empty:
                    stats['table_count'] = table_result.data.iloc[0]['table_count']

                # 查询记录总数（简单估算）
                record_result = duckdb_ops.execute_query(
                    config.database_path,
                    "SELECT SUM(estimated_size) as total_records FROM duckdb_tables()"
                )
                if record_result.success and not record_result.data.empty:
                    stats['record_count'] = record_result.data.iloc[0]['total_records'] or 0

            return stats

        except Exception as e:
            logger.error(f"获取数据源统计信息失败 {plugin_id}: {e}")
            return {}

    def _clean_plugin_id(self, plugin_id: str) -> str:
        """清理插件ID中的特殊字符"""
        import re
        # 移除或替换特殊字符
        clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', plugin_id)
        # 确保不以数字开头
        if clean_id[0].isdigit():
            clean_id = f"plugin_{clean_id}"
        return clean_id.lower()

    def _generate_table_name(self, config: DataSourceStorageConfig,
                             table_type: TableType, period: Optional[str] = None) -> str:
        """生成表名"""
        base_name = table_type.value

        if period:
            base_name += f"_{period}"

        if config.table_prefix:
            return f"{config.table_prefix}_{base_name}"
        else:
            return base_name

    def _auto_create_table_and_indexes(self, plugin_id: str, table_type: TableType,
                                       period: Optional[str], config: DataSourceStorageConfig) -> Optional[str]:
        """
        自动创建表结构和索引

        Args:
            plugin_id: 插件ID
            table_type: 表类型
            period: 数据周期
            config: 存储配置

        Returns:
            创建的表名，失败返回None
        """
        try:
            # 获取表管理器
            if not self.table_manager:
                logger.error("表管理器不可用")
                return None

            # 使用表管理器生成表名，确保一致性
            table_name = self.table_manager.generate_table_name(
                table_type=table_type,
                plugin_name=config.plugin_name,
                period=period
            )

            # 检查数据库文件是否存在
            if not os.path.exists(config.database_path):
                logger.info(f"数据库文件不存在，将自动创建: {config.database_path}")

            # 检查表是否已存在
            if self._table_exists(config.database_path, table_name):
                logger.debug(f"表已存在: {table_name}")
                return table_name

            # 创建表结构
            logger.info(f"开始创建表: {table_name} (数据源: {plugin_id})")
            success = self.table_manager.create_table(
                database_path=config.database_path,
                table_type=table_type,
                plugin_name=config.plugin_name,
                period=period
            )

            if not success:
                logger.error(f"创建表失败: {table_name}")
                return None

            # 创建数据源特定的索引
            self._create_data_source_specific_indexes(config.database_path, table_name, table_type)

            logger.info(f"表和索引创建成功: {table_name} (数据源: {plugin_id})")
            return table_name

        except Exception as e:
            logger.error(f"自动创建表和索引失败 {plugin_id}: {e}")
            return None

    def _create_data_source_specific_indexes(self, database_path: str, table_name: str, table_type: TableType):
        """创建数据源特定的索引"""
        try:
            from .duckdb_operations import get_duckdb_operations
            duckdb_ops = get_duckdb_operations()

            if not duckdb_ops:
                logger.warning("DuckDB操作实例不可用，跳过索引创建")
                return

            # 基础索引（所有表类型都需要）
            base_indexes = [
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_data_source ON {table_name}(data_source)",
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_import_time ON {table_name}(import_time)"
            ]

            # 根据表类型添加特定索引
            specific_indexes = []
            if table_type == TableType.KLINE_DATA:
                specific_indexes = [
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol ON {table_name}(symbol)",
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_datetime ON {table_name}(datetime)",
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol_datetime ON {table_name}(symbol, datetime)",
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol_data_source ON {table_name}(symbol, data_source)",
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_volume ON {table_name}(volume) WHERE volume IS NOT NULL",
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_close_price ON {table_name}(close) WHERE close IS NOT NULL"
                ]
            elif table_type == TableType.REAL_TIME_QUOTE:
                specific_indexes = [
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol ON {table_name}(symbol)",
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp)",
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol_timestamp ON {table_name}(symbol, timestamp)"
                ]
            elif table_type == TableType.FUNDAMENTAL:
                specific_indexes = [
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol ON {table_name}(symbol)",
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_report_date ON {table_name}(report_date) WHERE report_date IS NOT NULL",
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol_report_date ON {table_name}(symbol, report_date)"
                ]

            # 执行索引创建
            all_indexes = base_indexes + specific_indexes
            for index_sql in all_indexes:
                try:
                    result = duckdb_ops.execute_query(database_path, index_sql)
                    if result.success:
                        logger.debug(f"索引创建成功: {index_sql.split('IF NOT EXISTS')[1].split('ON')[0].strip()}")
                    else:
                        logger.warning(f"索引创建失败: {result.error_message}")
                except Exception as e:
                    logger.warning(f"索引创建异常: {e}")

            logger.info(f"为表 {table_name} 创建了 {len(all_indexes)} 个索引")

        except Exception as e:
            logger.error(f"创建数据源特定索引失败: {e}")

    def _table_exists(self, database_path: str, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            from .duckdb_operations import get_duckdb_operations
            duckdb_ops = get_duckdb_operations()

            if not duckdb_ops:
                return False

            result = duckdb_ops.execute_query(
                database_path,
                f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
            )

            return result.success and not result.data.empty and result.data.iloc[0][0] > 0

        except Exception:
            return False

    def _load_storage_configs(self):
        """加载存储配置"""
        config_file = self.base_db_dir / "storage_configs.json"
        if config_file.exists():
            try:
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for plugin_id, config_data in data.items():
                    config = DataSourceStorageConfig(
                        plugin_id=config_data['plugin_id'],
                        plugin_name=config_data['plugin_name'],
                        isolation_level=DataSourceIsolationLevel(config_data['isolation_level']),
                        database_path=config_data['database_path'],
                        schema_prefix=config_data.get('schema_prefix', ''),
                        table_prefix=config_data.get('table_prefix', ''),
                        auto_create_tables=config_data.get('auto_create_tables', True),
                        enable_compression=config_data.get('enable_compression', True),
                        max_database_size_mb=config_data.get('max_database_size_mb', 1024)
                    )
                    self._storage_configs[plugin_id] = config

                logger.info(f"加载存储配置完成: {len(self._storage_configs)}个数据源")

            except Exception as e:
                logger.error(f"加载存储配置失败: {e}")

    def _save_storage_configs(self):
        """保存存储配置"""
        try:
            config_file = self.base_db_dir / "storage_configs.json"

            data = {}
            for plugin_id, config in self._storage_configs.items():
                data[plugin_id] = {
                    'plugin_id': config.plugin_id,
                    'plugin_name': config.plugin_name,
                    'isolation_level': config.isolation_level.value,
                    'database_path': config.database_path,
                    'schema_prefix': config.schema_prefix,
                    'table_prefix': config.table_prefix,
                    'auto_create_tables': config.auto_create_tables,
                    'enable_compression': config.enable_compression,
                    'max_database_size_mb': config.max_database_size_mb
                }

            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug("存储配置保存完成")

        except Exception as e:
            logger.error(f"保存存储配置失败: {e}")


# 全局实例
_separated_storage_manager: Optional[DataSourceSeparatedStorageManager] = None


def get_separated_storage_manager() -> DataSourceSeparatedStorageManager:
    """获取全局分离存储管理器实例"""
    global _separated_storage_manager
    if _separated_storage_manager is None:
        _separated_storage_manager = DataSourceSeparatedStorageManager()
    return _separated_storage_manager


def initialize_separated_storage(base_db_dir: str = "db/datasource_separated") -> DataSourceSeparatedStorageManager:
    """初始化分离存储管理器"""
    global _separated_storage_manager
    _separated_storage_manager = DataSourceSeparatedStorageManager(base_db_dir)
    return _separated_storage_manager
