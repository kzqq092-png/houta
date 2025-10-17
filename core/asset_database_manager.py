"""
资产分数据库管理器

提供按资产类型分数据库的管理功能，包括：
- 资产类型自动识别和路由
- 多数据库连接管理
- 数据库自动创建和初始化
- 统一的查询接口
- 跨资产类型数据查询

作者: FactorWeave-Quant团队
版本: 1.0
"""

import threading
import os
from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import json
import pandas as pd

from loguru import logger
from core.database.duckdb_manager import DuckDBConnectionManager, DuckDBConfig
from core.asset_type_identifier import AssetTypeIdentifier, get_asset_type_identifier
from core.plugin_types import AssetType, DataType

logger = logger.bind(module=__name__)


@dataclass
class AssetDatabaseConfig:
    """资产数据库配置"""
    base_path: str = "db/databases"
    pool_size: int = 10
    auto_create: bool = True
    enable_wal: bool = True
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    compression: str = "zstd"
    memory_limit: str = "8GB"
    threads: str = "auto"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'base_path': self.base_path,
            'pool_size': self.pool_size,
            'auto_create': self.auto_create,
            'enable_wal': self.enable_wal,
            'backup_enabled': self.backup_enabled,
            'backup_interval_hours': self.backup_interval_hours,
            'compression': self.compression,
            'memory_limit': self.memory_limit,
            'threads': self.threads
        }


@dataclass
class AssetDatabaseInfo:
    """资产数据库信息"""
    asset_type: AssetType
    database_path: str
    created_at: datetime
    last_accessed: datetime
    size_mb: float = 0.0
    table_count: int = 0
    record_count: int = 0
    health_status: str = "unknown"
    supported_data_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'asset_type': self.asset_type.value,
            'database_path': self.database_path,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'size_mb': self.size_mb,
            'table_count': self.table_count,
            'record_count': self.record_count,
            'health_status': self.health_status,
            'supported_data_sources': self.supported_data_sources
        }


class AssetSeparatedDatabaseManager:
    """
    资产分数据库管理器

    按资产类型分离数据库存储，每种资产类型使用独立的DuckDB数据库文件。
    支持自动识别资产类型、路由到对应数据库、统一查询接口等功能。
    """

    _instance: Optional['AssetSeparatedDatabaseManager'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls, config: Optional[AssetDatabaseConfig] = None) -> 'AssetSeparatedDatabaseManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    def __init__(self, config: Optional[AssetDatabaseConfig] = None):
        """
        初始化资产分数据库管理器

        Args:
            config: 资产数据库配置
        """
        if self._initialized:
            return

        self.config = config or AssetDatabaseConfig()

        # 核心组件
        self.asset_identifier = get_asset_type_identifier()
        self.duckdb_manager = DuckDBConnectionManager()

        # 数据库映射和信息
        self._asset_databases: Dict[AssetType, str] = {}
        self._database_info: Dict[AssetType, AssetDatabaseInfo] = {}

        # 线程锁
        self._db_lock = threading.RLock()

        # 标准表结构定义
        self._table_schemas = self._initialize_table_schemas()

        # 初始化
        self._initialize_directories()
        self._load_existing_databases()

        self._initialized = True
        logger.info("AssetSeparatedDatabaseManager 初始化完成")

    def _initialize_directories(self):
        """初始化目录结构"""
        base_path = Path(self.config.base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # 创建各种资产类型的目录
        for asset_type in AssetType:
            asset_dir = base_path / asset_type.value.lower()
            asset_dir.mkdir(exist_ok=True)

        logger.debug(f"目录结构初始化完成: {base_path}")

    def _initialize_table_schemas(self) -> Dict[str, str]:
        """初始化标准表结构定义"""
        return {
            # K线数据表（通用）
            'historical_kline_data': """
                CREATE TABLE IF NOT EXISTS historical_kline_data (
                    symbol VARCHAR NOT NULL,
                    data_source VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    open DECIMAL(18,6) NOT NULL,
                    high DECIMAL(18,6) NOT NULL,
                    low DECIMAL(18,6) NOT NULL,
                    close DECIMAL(18,6) NOT NULL,
                    volume BIGINT DEFAULT 0,
                    amount DECIMAL(18,6) DEFAULT 0,
                    frequency VARCHAR NOT NULL DEFAULT '1d',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, data_source, timestamp, frequency)
                )
            """,

            # 数据源记录表
            'data_source_records': """
                CREATE TABLE IF NOT EXISTS data_source_records (
                    record_id VARCHAR PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    data_source VARCHAR NOT NULL,
                    data_type VARCHAR NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    record_count INTEGER,
                    file_size_bytes BIGINT,
                    checksum VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,

            # 数据质量监控表
            'data_quality_monitor': """
                CREATE TABLE IF NOT EXISTS data_quality_monitor (
                    monitor_id VARCHAR PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    data_source VARCHAR NOT NULL,
                    check_date DATE NOT NULL,
                    quality_score DECIMAL(5,2),
                    anomaly_count INTEGER DEFAULT 0,
                    missing_count INTEGER DEFAULT 0,
                    outlier_count INTEGER DEFAULT 0,
                    consistency_score DECIMAL(5,2),
                    completeness_score DECIMAL(5,2),
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,

            # 统一视图 - 最优质量K线数据
            'unified_best_quality_kline': """
                CREATE VIEW IF NOT EXISTS unified_best_quality_kline AS
                WITH ranked_data AS (
                    SELECT 
                        hkd.*,
                        dqm.quality_score,
                        ROW_NUMBER() OVER (
                            PARTITION BY hkd.symbol, hkd.timestamp, hkd.frequency 
                            ORDER BY COALESCE(dqm.quality_score, 50) DESC, hkd.updated_at DESC
                        ) as quality_rank
                    FROM historical_kline_data hkd
                    LEFT JOIN data_quality_monitor dqm ON (
                        hkd.symbol = dqm.symbol 
                        AND hkd.data_source = dqm.data_source 
                        AND DATE(hkd.timestamp) = dqm.check_date
                    )
                )
                SELECT * FROM ranked_data WHERE quality_rank = 1
            """,

            # 元数据表
            'metadata': """
                CREATE TABLE IF NOT EXISTS metadata (
                    key VARCHAR PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        }

    def _load_existing_databases(self):
        """加载现有数据库"""
        base_path = Path(self.config.base_path)

        for asset_type in AssetType:
            db_path = self._get_database_path(asset_type)

            if Path(db_path).exists():
                self._asset_databases[asset_type] = db_path

                # 获取数据库信息
                info = self._collect_database_info(asset_type, db_path)
                self._database_info[asset_type] = info

                logger.debug(f"加载现有数据库: {asset_type.value} -> {db_path}")

    def _get_database_path(self, asset_type: AssetType) -> str:
        """获取资产类型对应的数据库路径"""
        # 别名映射：STOCK → STOCK_US（通用股票默认为美股）
        if asset_type == AssetType.STOCK:
            asset_type = AssetType.STOCK_US

        base_path = Path(self.config.base_path)
        asset_dir = base_path / asset_type.value.lower()
        db_file = asset_dir / f"{asset_type.value.lower()}_data.duckdb"
        return str(db_file)

    def get_database_path(self, asset_type: AssetType) -> str:
        """获取资产类型对应的数据库路径 (公共方法)"""
        return self._get_database_path(asset_type)

    def _collect_database_info(self, asset_type: AssetType, db_path: str) -> AssetDatabaseInfo:
        """收集数据库信息"""
        try:
            # 获取文件信息
            file_stat = Path(db_path).stat()
            size_mb = file_stat.st_size / (1024 * 1024)

            # 获取数据库内部信息
            with self.duckdb_manager.get_connection(db_path) as conn:
                # 获取表数量 - 使用duckdb_tables()更高效
                tables_result = conn.execute("""
                    SELECT COUNT(*) as table_count 
                    FROM duckdb_tables() 
                    WHERE schema_name = 'main'
                """).fetchone()
                table_count = tables_result[0] if tables_result else 0

                # 获取记录总数（仅查询historical_kline_data表）
                record_count = 0
                try:
                    record_result = conn.execute("""
                        SELECT COUNT(*) as record_count 
                        FROM historical_kline_data
                    """).fetchone()
                    record_count = record_result[0] if record_result else 0
                except:
                    pass  # 表可能不存在

                # 获取支持的数据源
                supported_sources = []
                try:
                    sources_result = conn.execute("""
                        SELECT DISTINCT data_source 
                        FROM historical_kline_data
                    """).fetchall()
                    supported_sources = [row[0] for row in sources_result]
                except:
                    pass  # 表可能不存在

            return AssetDatabaseInfo(
                asset_type=asset_type,
                database_path=db_path,
                created_at=datetime.fromtimestamp(file_stat.st_ctime),
                last_accessed=datetime.fromtimestamp(file_stat.st_atime),
                size_mb=size_mb,
                table_count=table_count,
                record_count=record_count,
                health_status="healthy",
                supported_data_sources=supported_sources
            )

        except Exception as e:
            logger.error(f"收集数据库信息失败 {asset_type.value}: {e}")
            return AssetDatabaseInfo(
                asset_type=asset_type,
                database_path=db_path,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                health_status="error"
            )

    def get_database_for_asset_type(self, asset_type: AssetType, auto_create: bool = True) -> str:
        """
        获取资产类型对应的数据库路径

        Args:
            asset_type: 资产类型
            auto_create: 是否自动创建数据库

        Returns:
            数据库文件路径
        """
        with self._db_lock:
            if asset_type not in self._asset_databases:
                db_path = self._get_database_path(asset_type)

                if auto_create and self.config.auto_create:
                    self._create_asset_database(asset_type, db_path)

                self._asset_databases[asset_type] = db_path

            return self._asset_databases[asset_type]

    def _ensure_database_exists(self, asset_type: AssetType) -> str:
        """
        确保数据库存在并返回数据库路径

        Args:
            asset_type: 资产类型

        Returns:
            str: 数据库文件路径
        """
        return self.get_database_for_asset_type(asset_type, auto_create=True)

    def get_database_for_symbol(self, symbol: str, auto_create: bool = True) -> Tuple[str, AssetType]:
        """
        根据交易符号获取对应的数据库路径和资产类型

        Args:
            symbol: 交易符号
            auto_create: 是否自动创建数据库

        Returns:
            (数据库路径, 资产类型)
        """
        asset_type = self.asset_identifier.identify_asset_type_by_symbol(symbol)
        db_path = self.get_database_for_asset_type(asset_type, auto_create)
        return db_path, asset_type

    def _create_asset_database(self, asset_type: AssetType, db_path: str):
        """创建资产数据库"""
        try:
            # 确保目录存在
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

            # 创建数据库并初始化表结构
            duckdb_config = DuckDBConfig(
                memory_limit=self.config.memory_limit,
                threads=self.config.threads,
                compression=self.config.compression
            )

            with self.duckdb_manager.get_connection(db_path, config=duckdb_config) as conn:
                # 创建标准表结构，跳过视图
                for table_name, schema_sql in self._table_schemas.items():
                    if table_name == 'unified_best_quality_kline':
                        continue  # 先跳过视图创建，待基础表创建完成后再创建
                    try:
                        conn.execute(schema_sql)
                        logger.debug(f"创建表 {table_name} 成功")
                    except Exception as e:
                        logger.error(f"创建表 {table_name} 失败: {e}")
                        raise

                # 创建视图（在表创建完成后）
                if 'unified_best_quality_kline' in self._table_schemas:
                    try:
                        # 获取实际的K线表名
                        actual_kline_table = f"{asset_type.value.lower()}_kline"

                        # 替换视图SQL中的表名引用
                        view_sql = self._table_schemas['unified_best_quality_kline']
                        view_sql = view_sql.replace('historical_kline_data', actual_kline_table)

                        conn.execute(view_sql)
                        logger.debug(f"创建视图 unified_best_quality_kline 成功（引用表: {actual_kline_table}）")
                    except Exception as e:
                        logger.warning(f"创建视图失败: {e}")

                # 插入元数据
                conn.execute("""
                    INSERT OR REPLACE INTO metadata (key, value) 
                    VALUES ('asset_type', ?), ('created_at', ?), ('version', '1.0')
                """, [asset_type.value, datetime.now().isoformat()])

            # 更新数据库信息
            info = self._collect_database_info(asset_type, db_path)
            self._database_info[asset_type] = info

            logger.info(f"创建资产数据库: {asset_type.value} -> {db_path}")

        except Exception as e:
            logger.error(f"创建资产数据库失败 {asset_type.value}: {e}")
            raise

    def get_connection(self, asset_type: AssetType, auto_create: bool = True):
        """
        获取资产类型对应的数据库连接

        Args:
            asset_type: 资产类型
            auto_create: 是否自动创建数据库

        Returns:
            数据库连接上下文管理器
        """
        db_path = self.get_database_for_asset_type(asset_type, auto_create)
        return self.duckdb_manager.get_connection(db_path, pool_size=self.config.pool_size)

    def get_connection_by_symbol(self, symbol: str, auto_create: bool = True):
        """
        根据交易符号获取对应的数据库连接

        Args:
            symbol: 交易符号
            auto_create: 是否自动创建数据库

        Returns:
            数据库连接上下文管理器
        """
        db_path, asset_type = self.get_database_for_symbol(symbol, auto_create)
        return self.duckdb_manager.get_connection(db_path, pool_size=self.config.pool_size)

    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """检查所有资产数据库的健康状态"""
        results = {}

        with self._db_lock:
            for asset_type, db_path in self._asset_databases.items():
                try:
                    # 基础连接测试
                    with self.get_connection(asset_type) as conn:
                        test_result = conn.execute("SELECT 1 as test").fetchone()

                        # 更新数据库信息
                        info = self._collect_database_info(asset_type, db_path)
                        self._database_info[asset_type] = info

                        results[asset_type.value] = {
                            'status': 'healthy',
                            'database_info': info.to_dict(),
                            'test_query_result': test_result
                        }

                except Exception as e:
                    logger.error(f"健康检查失败 {asset_type.value}: {e}")
                    results[asset_type.value] = {
                        'status': 'unhealthy',
                        'error': str(e),
                        'database_path': db_path
                    }

        return results

    def get_all_database_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有数据库信息"""
        results = {}

        with self._db_lock:
            for asset_type, info in self._database_info.items():
                results[asset_type.value] = info.to_dict()

        return results

    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型列表"""
        with self._db_lock:
            return list(self._asset_databases.keys())

    def get_database_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {
            'total_databases': len(self._asset_databases),
            'total_size_mb': 0.0,
            'total_records': 0,
            'asset_breakdown': {}
        }

        with self._db_lock:
            for asset_type, info in self._database_info.items():
                stats['total_size_mb'] += info.size_mb
                stats['total_records'] += info.record_count

                stats['asset_breakdown'][asset_type.value] = {
                    'size_mb': info.size_mb,
                    'record_count': info.record_count,
                    'table_count': info.table_count,
                    'data_sources': len(info.supported_data_sources),
                    'health_status': info.health_status
                }

        return stats

    def backup_database(self, asset_type: AssetType, backup_path: Optional[str] = None) -> str:
        """
        备份指定资产类型的数据库

        Args:
            asset_type: 资产类型
            backup_path: 备份路径（可选）

        Returns:
            备份文件路径
        """
        if asset_type not in self._asset_databases:
            raise ValueError(f"资产类型 {asset_type.value} 的数据库不存在")

        source_path = self._asset_databases[asset_type]

        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(self.config.base_path) / "backups"
            backup_dir.mkdir(exist_ok=True)
            backup_path = str(backup_dir / f"{asset_type.value.lower()}_backup_{timestamp}.duckdb")

        try:
            import shutil
            import time

            # 确保所有连接都已关闭（防止文件锁定）
            self.duckdb_manager.remove_pool(source_path)
            time.sleep(0.1)  # 给一点时间让文件句柄完全释放

            shutil.copy2(source_path, backup_path)
            logger.info(f"数据库备份完成: {asset_type.value} -> {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"数据库备份失败 {asset_type.value}: {e}")
            raise

    def restore_database(self, asset_type: AssetType, backup_path: str, force: bool = False):
        """
        从备份恢复数据库

        Args:
            asset_type: 资产类型
            backup_path: 备份文件路径
            force: 是否强制覆盖现有数据库
        """
        if not Path(backup_path).exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        target_path = self._get_database_path(asset_type)

        if Path(target_path).exists() and not force:
            raise ValueError(f"目标数据库已存在，使用 force=True 强制覆盖: {target_path}")

        try:
            import shutil

            # 如果目标数据库存在，先备份
            if Path(target_path).exists():
                backup_existing = f"{target_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(target_path, backup_existing)
                logger.info(f"现有数据库已备份: {backup_existing}")

            # 恢复数据库
            shutil.copy2(backup_path, target_path)

            # 更新内部记录
            self._asset_databases[asset_type] = target_path
            info = self._collect_database_info(asset_type, target_path)
            self._database_info[asset_type] = info

            logger.info(f"数据库恢复完成: {asset_type.value} <- {backup_path}")

        except Exception as e:
            logger.error(f"数据库恢复失败 {asset_type.value}: {e}")
            raise

    def cleanup_old_backups(self, days_to_keep: int = 30):
        """清理旧备份文件"""
        backup_dir = Path(self.config.base_path) / "backups"

        if not backup_dir.exists():
            return

        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
        cleaned_count = 0

        try:
            for backup_file in backup_dir.glob("*_backup_*.duckdb"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    cleaned_count += 1
                    logger.debug(f"删除旧备份: {backup_file}")

            logger.info(f"清理完成，删除了 {cleaned_count} 个旧备份文件")

        except Exception as e:
            logger.error(f"清理备份文件失败: {e}")

    def store_standardized_data(self, data: pd.DataFrame, asset_type: AssetType,
                                data_type: DataType, table_name: Optional[str] = None) -> bool:
        """
        存储标准化数据到指定资产类型数据库

        Args:
            data: 标准化后的数据
            asset_type: 资产类型
            data_type: 数据类型
            table_name: 表名（可选，默认根据数据类型生成）

        Returns:
            bool: 存储是否成功
        """
        if data.empty:
            logger.warning("数据为空，跳过存储")
            return False

        try:
            # 确保数据库存在
            db_path = self._ensure_database_exists(asset_type)

            # 生成表名
            if not table_name:
                table_name = self._generate_table_name(data_type, asset_type)

            # 获取数据库连接并存储数据
            with self.duckdb_manager.get_connection(db_path) as conn:
                # 创建表结构（如果不存在）
                self._ensure_table_exists(conn, table_name, data, data_type)

                # 插入数据（使用upsert逻辑）
                rows_affected = self._upsert_data(conn, table_name, data, data_type)

                logger.info(f"成功存储 {rows_affected} 行数据到 {asset_type.value}/{table_name}")
                return True

        except Exception as e:
            logger.error(f"存储标准化数据失败: {e}")
            return False

    def _generate_table_name(self, data_type: DataType, asset_type: AssetType) -> str:
        """生成表名"""
        type_mapping = {
            DataType.HISTORICAL_KLINE: "kline",
            DataType.REAL_TIME_QUOTE: "quotes",
            DataType.FUNDAMENTAL: "fundamentals",
            DataType.ASSET_LIST: "assets",
            DataType.SECTOR_FUND_FLOW: "sector_fund_flow"
        }

        base_name = type_mapping.get(data_type, data_type.value.lower())
        return f"{asset_type.value}_{base_name}"

    def _ensure_table_exists(self, conn, table_name: str, data: pd.DataFrame, data_type: DataType):
        """确保表存在，如果不存在则创建"""
        try:
            # 检查表是否存在 - 使用duckdb_tables()更高效
            table_exists = conn.execute(f"""
                SELECT COUNT(*) 
                FROM duckdb_tables() 
                WHERE table_name = '{table_name}'
            """).fetchone()[0] > 0

            if not table_exists:
                # 根据数据类型创建表结构
                create_sql = self._generate_create_table_sql(table_name, data, data_type)
                conn.execute(create_sql)
                logger.info(f"创建表: {table_name}")

                # 创建索引
                self._create_table_indexes(conn, table_name, data_type)

        except Exception as e:
            logger.error(f"创建表 {table_name} 失败: {e}")
            raise

    def _generate_create_table_sql(self, table_name: str, data: pd.DataFrame, data_type: DataType) -> str:
        """生成创建表的SQL"""
        # 根据数据类型定义标准表结构
        if data_type == DataType.HISTORICAL_KLINE:
            return f"""
                CREATE TABLE {table_name} (
                    symbol VARCHAR,
                    market VARCHAR,
                    datetime TIMESTAMP,
                    frequency VARCHAR NOT NULL DEFAULT '1d',
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE,
                    amount DOUBLE,
                    turnover DOUBLE,
                    adj_close DOUBLE,
                    adj_factor DOUBLE DEFAULT 1.0,
                    turnover_rate DOUBLE,
                    vwap DOUBLE,
                    data_source VARCHAR DEFAULT 'unknown',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, datetime, frequency)
                )
            """
        elif data_type == DataType.REAL_TIME_QUOTE:
            return f"""
                CREATE TABLE {table_name} (
                    symbol VARCHAR,
                    name VARCHAR,
                    market VARCHAR,
                    current_price DOUBLE,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE,
                    amount DOUBLE,
                    change DOUBLE,
                    change_percent DOUBLE,
                    timestamp TIMESTAMP,
                    bid_price DOUBLE,
                    ask_price DOUBLE,
                    bid_volume DOUBLE,
                    ask_volume DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, timestamp)
                )
            """
        elif data_type == DataType.FUNDAMENTAL:
            return f"""
                CREATE TABLE {table_name} (
                    symbol VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    market VARCHAR,
                    industry VARCHAR,
                    sector VARCHAR,
                    list_date DATE,
                    total_shares DOUBLE,
                    float_shares DOUBLE,
                    market_cap DOUBLE,
                    status VARCHAR,
                    currency VARCHAR,
                    is_st BOOLEAN,
                    updated_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        elif data_type == DataType.ASSET_LIST:
            return f"""
                CREATE TABLE {table_name} (
                    symbol VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    market VARCHAR,
                    asset_type VARCHAR,
                    status VARCHAR,
                    category VARCHAR,
                    updated_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        elif data_type == DataType.SECTOR_FUND_FLOW:
            return f"""
                CREATE TABLE {table_name} (
                    sector_code VARCHAR,
                    sector_name VARCHAR,
                    date DATE,
                    main_inflow DOUBLE,
                    main_outflow DOUBLE,
                    main_net_flow DOUBLE,
                    retail_inflow DOUBLE,
                    retail_outflow DOUBLE,
                    retail_net_flow DOUBLE,
                    total_volume DOUBLE,
                    total_amount DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (sector_code, date)
                )
            """
        else:
            # 通用表结构，根据DataFrame列推断
            columns = []
            for col in data.columns:
                if data[col].dtype == 'object':
                    columns.append(f"{col} VARCHAR")
                elif data[col].dtype in ['int64', 'int32']:
                    columns.append(f"{col} INTEGER")
                elif data[col].dtype in ['float64', 'float32']:
                    columns.append(f"{col} DOUBLE")
                elif 'datetime' in str(data[col].dtype):
                    columns.append(f"{col} TIMESTAMP")
                else:
                    columns.append(f"{col} VARCHAR")

            columns.append("created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            return f"CREATE TABLE {table_name} ({', '.join(columns)})"

    def _create_table_indexes(self, conn, table_name: str, data_type: DataType):
        """创建表索引"""
        try:
            if data_type == DataType.HISTORICAL_KLINE:
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol ON {table_name}(symbol)")
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_datetime ON {table_name}(datetime)")
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol_datetime ON {table_name}(symbol, datetime)")
            elif data_type == DataType.REAL_TIME_QUOTE:
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol ON {table_name}(symbol)")
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp)")
            elif data_type == DataType.FUNDAMENTAL:
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol ON {table_name}(symbol)")
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_market ON {table_name}(market)")
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_industry ON {table_name}(industry)")
            # 其他数据类型的索引...
        except Exception as e:
            logger.warning(f"创建索引失败: {e}")

    def _get_table_columns(self, conn, table_name: str) -> list:
        """获取表的列名"""
        try:
            result = conn.execute(f"""
                SELECT column_name 
                FROM duckdb_columns() 
                WHERE table_name = '{table_name}'
            """).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"获取表列名失败 {table_name}: {e}")
            return []

    def _filter_dataframe_columns(self, data: pd.DataFrame, table_columns: list) -> pd.DataFrame:
        """过滤DataFrame，只保留表中存在的列"""
        # 找出data中存在但表中不存在的列
        extra_columns = [col for col in data.columns if col not in table_columns]

        if extra_columns:
            logger.debug(f"过滤掉不在表中的列: {extra_columns}")
            # 只保留表中存在的列
            valid_columns = [col for col in data.columns if col in table_columns]
            filtered_data = data[valid_columns].copy()

            # 检查关键字段是否存在
            logger.debug(f"过滤后的列: {filtered_data.columns.tolist()}")
            if 'datetime' not in filtered_data.columns:
                logger.warning(f"过滤后缺少datetime字段！原始列: {data.columns.tolist()}, 表列: {table_columns}")

            return filtered_data

        return data

    def _upsert_data(self, conn, table_name: str, data: pd.DataFrame, data_type: DataType) -> int:
        """插入或更新数据"""
        try:
            # 调试：检查输入数据
            logger.debug(f"准备插入数据到 {table_name}，输入列: {data.columns.tolist()}")
            if 'datetime' in data.columns:
                logger.debug(f"datetime字段存在，非空记录数: {data['datetime'].notna().sum()}/{len(data)}")
            else:
                logger.warning(f"输入数据缺少datetime字段！")

            # 获取表的实际列名
            table_columns = self._get_table_columns(conn, table_name)
            if not table_columns:
                logger.error(f"无法获取表 {table_name} 的列信息")
                return 0

            logger.debug(f"表 {table_name} 的列: {table_columns}")

            # 过滤数据，只保留表中存在的列
            filtered_data = self._filter_dataframe_columns(data, table_columns)

            if filtered_data.empty or len(filtered_data.columns) == 0:
                logger.warning(f"过滤后没有有效数据可插入")
                return 0

            # 使用DuckDB的INSERT ... ON CONFLICT语法
            placeholders = ', '.join(['?' for _ in filtered_data.columns])
            columns = ', '.join(filtered_data.columns)

            if data_type == DataType.HISTORICAL_KLINE:
                # K线数据使用symbol、datetime和frequency作为唯一键
                update_fields = []
                # 基础OHLCV + 扩展字段（包括新增的复权数据等）
                for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover',
                            'adj_close', 'adj_factor', 'turnover_rate', 'vwap']:
                    if col in filtered_data.columns:
                        update_fields.append(f"{col} = EXCLUDED.{col}")

                update_clause = ', '.join(update_fields) if update_fields else "open = EXCLUDED.open"

                sql = f"""
                    INSERT INTO {table_name} ({columns}) 
                    VALUES ({placeholders})
                    ON CONFLICT (symbol, datetime, frequency) DO UPDATE SET
                    {update_clause}
                """
            elif data_type == DataType.REAL_TIME_QUOTE:
                # 实时行情使用symbol和timestamp作为唯一键
                sql = f"""
                    INSERT INTO {table_name} ({columns}) 
                    VALUES ({placeholders})
                    ON CONFLICT (symbol, timestamp) DO UPDATE SET
                    current_price = EXCLUDED.current_price,
                    volume = EXCLUDED.volume,
                    amount = EXCLUDED.amount
                """
            else:
                # 其他数据类型的简单插入
                sql = f"""
                    INSERT OR REPLACE INTO {table_name} ({columns}) 
                    VALUES ({placeholders})
                """

            # 批量插入数据
            data_tuples = [tuple(row) for row in filtered_data.values]
            conn.executemany(sql, data_tuples)

            return len(filtered_data)

        except Exception as e:
            logger.error(f"插入数据失败: {e}")
            raise

    def check_database_health(self, asset_type: AssetType) -> Dict[str, Any]:
        """检查指定资产类型数据库的健康状态"""
        try:
            db_path = self._get_database_path(asset_type)

            # 检查数据库文件是否存在
            if not Path(db_path).exists():
                return {
                    "status": "unhealthy",
                    "reason": "database_file_not_found",
                    "path": db_path
                }

            # 检查数据库连接
            try:
                with self.duckdb_manager.get_connection(db_path) as conn:
                    # 执行简单查询测试连接
                    result = conn.execute("SELECT 1").fetchone()
                    if result and result[0] == 1:
                        # 获取表数量 - 使用duckdb_tables()更高效
                        table_count = conn.execute("""
                            SELECT COUNT(*) as table_count 
                            FROM duckdb_tables() 
                            WHERE schema_name = 'main'
                        """).fetchone()[0]

                        return {
                            "status": "healthy",
                            "path": db_path,
                            "table_count": table_count,
                            "connection_test": "passed"
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "reason": "connection_test_failed",
                            "path": db_path
                        }
            except Exception as conn_error:
                return {
                    "status": "unhealthy",
                    "reason": "connection_error",
                    "path": db_path,
                    "error": str(conn_error)
                }

        except Exception as e:
            logger.error(f"检查数据库健康状态失败 {asset_type.value}: {e}")
            return {
                "status": "error",
                "reason": "health_check_failed",
                "error": str(e)
            }

    def close_all_connections(self):
        """关闭所有数据库连接"""
        try:
            self.duckdb_manager.close_all_pools()
            logger.info("所有资产数据库连接已关闭")

        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")


# 全局实例
_asset_db_manager: Optional[AssetSeparatedDatabaseManager] = None
_manager_lock = threading.Lock()


def get_asset_database_manager(config: Optional[AssetDatabaseConfig] = None) -> AssetSeparatedDatabaseManager:
    """获取全局资产数据库管理器实例"""
    global _asset_db_manager

    with _manager_lock:
        if _asset_db_manager is None:
            _asset_db_manager = AssetSeparatedDatabaseManager(config)

        return _asset_db_manager


def initialize_asset_database_manager(config: Optional[AssetDatabaseConfig] = None) -> AssetSeparatedDatabaseManager:
    """初始化资产数据库管理器"""
    global _asset_db_manager

    with _manager_lock:
        if _asset_db_manager is not None:
            _asset_db_manager.close_all_connections()

        _asset_db_manager = AssetSeparatedDatabaseManager(config)
        logger.info("AssetSeparatedDatabaseManager 已初始化")

        return _asset_db_manager


def cleanup_asset_database_manager():
    """清理资产数据库管理器"""
    global _asset_db_manager

    with _manager_lock:
        if _asset_db_manager is not None:
            _asset_db_manager.close_all_connections()
            _asset_db_manager = None
            logger.info("AssetSeparatedDatabaseManager 已清理")


def get_asset_separated_database_manager() -> AssetSeparatedDatabaseManager:
    """获取资产分数据库管理器实例（便捷函数）"""
    return AssetSeparatedDatabaseManager.get_instance()
