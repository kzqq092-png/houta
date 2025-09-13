from loguru import logger
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FactorWeave-Quant 分析数据库管理器

使用DuckDB存储和管理所有分析相关的数据，包括：
- 策略执行结果
- 技术指标计算结果
- 回测监控数据
- 性能指标
- 优化日志

集成性能优化器，基于2024年最新DuckDB最佳实践自动优化配置
"""

import pandas as pd

# 安全导入DuckDB
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"DuckDB模块不可用: {e}")
    duckdb = None
    DUCKDB_AVAILABLE = False
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import threading

# 导入性能优化器
try:
    from .duckdb_performance_optimizer import (
        DuckDBPerformanceOptimizer,
        WorkloadType,
        get_optimized_duckdb_connection
    )
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False
    logger.warning("DuckDB性能优化器不可用，使用默认配置")

    # 提供备用定义，避免NameError
    from enum import Enum

    class WorkloadType(Enum):
        """备用WorkloadType定义"""
        OLAP = "olap"
        OLTP = "oltp"
        MIXED = "mixed"

    class DuckDBPerformanceOptimizer:
        """备用DuckDBPerformanceOptimizer定义"""

        def __init__(self, db_path: str):
            self.db_path = db_path
            self.current_config = None

        def optimize_for_workload(self, workload_type):
            pass

        def get_connection(self):
            return None

        def get_performance_recommendations(self):
            return []

        def close(self):
            pass

    def get_optimized_duckdb_connection(db_path: str):
        """备用函数定义"""
        return None

logger = logger

class FactorWeaveAnalyticsDB:
    """FactorWeave分析数据库管理器 - 基于DuckDB"""

    _instances = {}  # 改为字典，支持多个数据库实例
    _lock = threading.Lock()

    def __new__(cls, db_path: str = 'db/factorweave_analytics.duckdb'):
        """单例模式实现 - 按数据库路径区分实例"""
        db_path = str(Path(db_path).resolve())  # 标准化路径

        with cls._lock:
            if db_path not in cls._instances:
                cls._instances[db_path] = super().__new__(cls)
                cls._instances[db_path]._initialized = False

        return cls._instances[db_path]

    def __init__(self, db_path: str = 'db/factorweave_analytics.duckdb'):
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = None
        self.optimizer = None

        # 初始化性能优化器
        if OPTIMIZER_AVAILABLE and DUCKDB_AVAILABLE:
            self.optimizer = DuckDBPerformanceOptimizer(str(self.db_path))
            logger.info(" DuckDB性能优化器已启用")
        else:
            self.optimizer = None

        self._connect()
        self._init_tables()

        self._initialized = True
        logger.info(f" FactorWeave分析数据库初始化完成: {self.db_path}")

    def _check_connection(self) -> bool:
        """检查数据库连接是否可用"""
        if not DUCKDB_AVAILABLE:
            logger.warning("DuckDB不可用，操作被跳过")
            return False
        if self.conn is None:
            logger.warning("数据库连接不可用，操作被跳过")
            return False
        return True

    def _connect(self):
        """连接到DuckDB数据库"""
        if not DUCKDB_AVAILABLE:
            logger.warning(" DuckDB不可用，分析数据库功能将被禁用")
            self.conn = None
            return

        try:
            if OPTIMIZER_AVAILABLE and DUCKDB_AVAILABLE and self.optimizer:
                # 使用性能优化的连接
                self.optimizer.optimize_for_workload(WorkloadType.OLAP)
                optimized_conn = self.optimizer.get_connection()

                if optimized_conn is not None:
                    self.conn = optimized_conn
                    logger.info(f" DuckDB连接成功 (性能优化): {self.db_path}")

                    # 显示优化配置
                    if hasattr(self.optimizer, 'current_config') and self.optimizer.current_config:
                        config = self.optimizer.current_config
                        logger.info(f" 优化配置: 内存={config.memory_limit}, 线程={config.threads}")

                    # 显示性能建议
                    recommendations = self.optimizer.get_performance_recommendations()
                    if recommendations:
                        logger.info(" 性能优化建议:")
                        for rec in recommendations[:3]:  # 只显示前3条
                            logger.info(f"  {rec}")
                else:
                    # 优化器返回None，回退到默认连接
                    self.conn = duckdb.connect(str(self.db_path))
                    logger.info(f" DuckDB连接成功 (默认配置-优化器回退): {self.db_path}")
                    self._apply_basic_optimization()
            else:
                # 使用默认连接
                self.conn = duckdb.connect(str(self.db_path))
                logger.info(f" DuckDB连接成功 (默认配置): {self.db_path}")

                # 应用基本优化配置
                self._apply_basic_optimization()

        except Exception as e:
            logger.error(f" DuckDB连接失败: {e}")
            # 即使优化失败，也要尝试基本连接
            try:
                self.conn = duckdb.connect(str(self.db_path))
                logger.info(f" DuckDB基本连接成功: {self.db_path}")
                self._apply_basic_optimization()
            except Exception as e2:
                logger.error(f" DuckDB基本连接也失败: {e2}")
                raise e2

    def _apply_basic_optimization(self):
        """应用基本优化配置（当优化器不可用时）"""
        try:
            # 基本内存和线程配置
            import psutil

            # 获取系统内存和CPU信息
            memory_gb = psutil.virtual_memory().total / (1024**3)
            cpu_cores = psutil.cpu_count(logical=True)

            # 保守的内存配置（使用50%系统内存）
            memory_limit = max(2.0, memory_gb * 0.5)

            # 线程配置（不超过CPU核心数）
            threads = min(cpu_cores, 8)  # 最多8线程

            # 应用配置
            self.conn.execute(f"SET memory_limit = '{memory_limit:.1f}GB'")
            self.conn.execute(f"SET threads = {threads}")
            self.conn.execute("SET enable_object_cache = true")
            self.conn.execute("SET enable_progress_bar = true")

            logger.info(f" 基本优化配置: 内存={memory_limit:.1f}GB, 线程={threads}")

        except Exception as e:
            logger.warning(f"应用基本优化配置失败: {e}")

    def _init_tables(self):
        """初始化分析数据库表结构"""
        try:
            # 创建序列用于自增ID
            sequences = [
                'strategy_execution_results_seq',
                'indicator_calculation_results_seq',
                'pattern_recognition_results_seq',
                'backtest_metrics_history_seq',
                'backtest_alerts_history_seq',
                'performance_metrics_seq',
                'optimization_logs_seq',
                'analysis_cache_seq'
            ]

            for seq_name in sequences:
                self.conn.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name}")

            # 1. 策略执行结果表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_execution_results (
                    id INTEGER PRIMARY KEY DEFAULT nextval('strategy_execution_results_seq'),
                    strategy_name VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    execution_time TIMESTAMP NOT NULL,
                    signal_type VARCHAR NOT NULL,  -- 'buy', 'sell', 'hold'
                    price DOUBLE,
                    quantity INTEGER,
                    confidence DOUBLE,
                    reason TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. 技术指标计算结果表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS indicator_calculation_results (
                    id INTEGER PRIMARY KEY DEFAULT nextval('indicator_calculation_results_seq'),
                    symbol VARCHAR NOT NULL,
                    indicator_name VARCHAR NOT NULL,
                    calculation_time TIMESTAMP NOT NULL,
                    timeframe VARCHAR NOT NULL,  -- '1m', '5m', '1h', '1d', etc.
                    value DOUBLE,
                    parameters TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. 形态识别结果表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_recognition_results (
                    id INTEGER PRIMARY KEY DEFAULT nextval('pattern_recognition_results_seq'),
                    symbol VARCHAR NOT NULL,
                    pattern_name VARCHAR NOT NULL,
                    detection_time TIMESTAMP NOT NULL,
                    confidence DOUBLE,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    pattern_data TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. 回测指标历史表 (从backtest_monitor.db迁移)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_metrics_history (
                    id INTEGER PRIMARY KEY DEFAULT nextval('backtest_metrics_history_seq'),
                    timestamp TIMESTAMP NOT NULL,
                    current_return DOUBLE,
                    cumulative_return DOUBLE,
                    current_drawdown DOUBLE,
                    max_drawdown DOUBLE,
                    sharpe_ratio DOUBLE,
                    volatility DOUBLE,
                    var_95 DOUBLE,
                    position_count INTEGER,
                    trade_count INTEGER,
                    win_rate DOUBLE,
                    profit_factor DOUBLE,
                    execution_time DOUBLE,
                    memory_usage DOUBLE,
                    cpu_usage DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. 回测预警历史表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_alerts_history (
                    id INTEGER PRIMARY KEY DEFAULT nextval('backtest_alerts_history_seq'),
                    timestamp TIMESTAMP NOT NULL,
                    level VARCHAR NOT NULL,
                    category VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    metric_name VARCHAR NOT NULL,
                    current_value DOUBLE,
                    threshold_value DOUBLE,
                    recommendation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. 性能指标表 (从optimization相关迁移)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY DEFAULT nextval('performance_metrics_seq'),
                    version_id INTEGER NOT NULL,
                    pattern_name VARCHAR NOT NULL,
                    test_dataset_id VARCHAR,
                    test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    true_positives INTEGER DEFAULT 0,
                    false_positives INTEGER DEFAULT 0,
                    true_negatives INTEGER DEFAULT 0,
                    false_negatives INTEGER DEFAULT 0,
                    precision DOUBLE,
                    recall DOUBLE,
                    f1_score DOUBLE,
                    accuracy DOUBLE,
                    execution_time DOUBLE,
                    memory_usage DOUBLE,
                    cpu_usage DOUBLE,
                    signal_quality DOUBLE,
                    confidence_avg DOUBLE,
                    confidence_std DOUBLE,
                    patterns_found INTEGER DEFAULT 0,
                    robustness_score DOUBLE,
                    parameter_sensitivity DOUBLE,
                    overall_score DOUBLE,
                    test_conditions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 7. 优化日志表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS optimization_logs (
                    id INTEGER PRIMARY KEY DEFAULT nextval('optimization_logs_seq'),
                    pattern_name VARCHAR NOT NULL,
                    optimization_session_id VARCHAR UNIQUE NOT NULL,
                    optimization_method VARCHAR NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    status VARCHAR DEFAULT 'running',
                    initial_version_id INTEGER,
                    final_version_id INTEGER,
                    iterations INTEGER DEFAULT 0,
                    best_score DOUBLE,
                    improvement_percentage DOUBLE,
                    optimization_config TEXT,
                    optimization_log TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 8. 分析缓存表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    id INTEGER PRIMARY KEY DEFAULT nextval('analysis_cache_seq'),
                    cache_key VARCHAR UNIQUE NOT NULL,
                    cache_type VARCHAR NOT NULL,
                    data TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建性能优化的索引
            self._create_optimized_indexes()

            logger.info(" FactorWeave分析数据库表结构初始化完成")

        except Exception as e:
            logger.error(f" 分析数据库表初始化失败: {e}")
            raise

    def _create_optimized_indexes(self):
        """创建性能优化的索引"""

        # 基于2024年DuckDB最佳实践的索引策略
        indexes = [
            # 策略执行结果索引 - 优化时间范围查询
            "CREATE INDEX IF NOT EXISTS idx_strategy_symbol_time ON strategy_execution_results(symbol, execution_time)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_name_time ON strategy_execution_results(strategy_name, execution_time)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_signal_type ON strategy_execution_results(signal_type, execution_time)",

            # 技术指标结果索引 - 优化指标查询
            "CREATE INDEX IF NOT EXISTS idx_indicator_symbol_time ON indicator_calculation_results(symbol, calculation_time)",
            "CREATE INDEX IF NOT EXISTS idx_indicator_name_time ON indicator_calculation_results(indicator_name, calculation_time)",
            "CREATE INDEX IF NOT EXISTS idx_indicator_timeframe ON indicator_calculation_results(timeframe, calculation_time)",

            # 形态识别结果索引 - 优化模式查询
            "CREATE INDEX IF NOT EXISTS idx_pattern_symbol_time ON pattern_recognition_results(symbol, recognition_time)",
            "CREATE INDEX IF NOT EXISTS idx_pattern_type_time ON pattern_recognition_results(pattern_type, recognition_time)",
            "CREATE INDEX IF NOT EXISTS idx_pattern_confidence ON pattern_recognition_results(confidence DESC, recognition_time)",

            # 回测指标索引 - 优化时序分析
            "CREATE INDEX IF NOT EXISTS idx_backtest_metrics_time ON backtest_metrics_history(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_backtest_metrics_return ON backtest_metrics_history(total_return, created_at)",

            # 回测预警索引 - 优化告警查询
            "CREATE INDEX IF NOT EXISTS idx_backtest_alerts_time ON backtest_alerts_history(alert_time)",
            "CREATE INDEX IF NOT EXISTS idx_backtest_alerts_level ON backtest_alerts_history(severity, alert_time)",
            "CREATE INDEX IF NOT EXISTS idx_backtest_alerts_type ON backtest_alerts_history(alert_type, alert_time)",

            # 性能指标索引 - 优化性能分析
            "CREATE INDEX IF NOT EXISTS idx_performance_pattern_time ON performance_metrics(pattern_name, test_time)",
            "CREATE INDEX IF NOT EXISTS idx_performance_score ON performance_metrics(overall_score DESC, test_time)",

            # 优化日志索引 - 优化优化历史查询
            "CREATE INDEX IF NOT EXISTS idx_optimization_pattern_time ON optimization_logs(pattern_name, start_time)",
            "CREATE INDEX IF NOT EXISTS idx_optimization_status ON optimization_logs(status, start_time)",
            "CREATE INDEX IF NOT EXISTS idx_optimization_session ON optimization_logs(optimization_session_id)",

            # 缓存索引 - 优化缓存访问
            "CREATE INDEX IF NOT EXISTS idx_cache_key ON analysis_cache(cache_key)",
            "CREATE INDEX IF NOT EXISTS idx_cache_type_expires ON analysis_cache(cache_type, expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_cache_expires ON analysis_cache(expires_at)"
        ]

        for index_sql in indexes:
            try:
                self.conn.execute(index_sql)
                logger.debug(f"创建索引: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                logger.warning(f"创建索引失败: {e}")

        logger.info(" 性能优化索引创建完成")

    def execute_query(self, sql: str, params: List = None) -> pd.DataFrame:
        """执行查询并返回DataFrame"""
        if not self._check_connection():
            return pd.DataFrame()  # 返回空DataFrame

        try:
            if params:
                result = self.conn.execute(sql, params).fetchdf()
            else:
                result = self.conn.execute(sql).fetchdf()
            return result
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise

    def execute_command(self, sql: str, params: List = None) -> bool:
        """执行INSERT/UPDATE/DELETE等命令，返回成功状态"""
        if not self._check_connection():
            return False  # 连接不可用时返回False

        try:
            if params:
                self.conn.execute(sql, params)
            else:
                self.conn.execute(sql)
            return True
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            raise

    def insert_dataframe(self, table_name: str, df: pd.DataFrame) -> bool:
        """插入DataFrame数据"""
        if not self._check_connection():
            return False  # 连接不可用时返回False

        try:
            self.conn.register('temp_df', df)
            self.conn.execute(f"INSERT INTO {table_name} SELECT * FROM temp_df")
            self.conn.unregister('temp_df')
            logger.debug(f"成功插入 {len(df)} 条记录到表 {table_name}")
            return True
        except Exception as e:
            logger.error(f"插入数据失败: {e}")
            return False

    def get_strategy_results(self, strategy_name: str = None, symbol: str = None,
                             start_time: datetime = None, end_time: datetime = None) -> pd.DataFrame:
        """获取策略执行结果"""
        sql = "SELECT * FROM strategy_execution_results WHERE 1=1"
        params = []

        if strategy_name:
            sql += " AND strategy_name = ?"
            params.append(strategy_name)
        if symbol:
            sql += " AND symbol = ?"
            params.append(symbol)
        if start_time:
            sql += " AND execution_time >= ?"
            params.append(start_time)
        if end_time:
            sql += " AND execution_time <= ?"
            params.append(end_time)

        sql += " ORDER BY execution_time DESC"
        return self.execute_query(sql, params)

    def get_indicator_results(self, symbol: str = None, indicator_name: str = None,
                              timeframe: str = None, limit: int = 1000) -> pd.DataFrame:
        """获取技术指标计算结果"""
        sql = "SELECT * FROM indicator_calculation_results WHERE 1=1"
        params = []

        if symbol:
            sql += " AND symbol = ?"
            params.append(symbol)
        if indicator_name:
            sql += " AND indicator_name = ?"
            params.append(indicator_name)
        if timeframe:
            sql += " AND timeframe = ?"
            params.append(timeframe)

        sql += " ORDER BY calculation_time DESC LIMIT ?"
        params.append(limit)

        return self.execute_query(sql, params)

    def get_pattern_results(self, symbol: str = None, pattern_name: str = None,
                            min_confidence: float = None, limit: int = 1000) -> pd.DataFrame:
        """获取形态识别结果"""
        sql = "SELECT * FROM pattern_recognition_results WHERE 1=1"
        params = []

        if symbol:
            sql += " AND symbol = ?"
            params.append(symbol)
        if pattern_name:
            sql += " AND pattern_name = ?"
            params.append(pattern_name)
        if min_confidence:
            sql += " AND confidence >= ?"
            params.append(min_confidence)

        sql += " ORDER BY detection_time DESC LIMIT ?"
        params.append(limit)

        return self.execute_query(sql, params)

    def get_backtest_metrics(self, start_time: datetime = None,
                             end_time: datetime = None) -> pd.DataFrame:
        """获取回测指标历史"""
        sql = "SELECT * FROM backtest_metrics_history WHERE 1=1"
        params = []

        if start_time:
            sql += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            sql += " AND timestamp <= ?"
            params.append(end_time)

        sql += " ORDER BY timestamp DESC"
        return self.execute_query(sql, params)

    def cleanup_expired_cache(self):
        """清理过期缓存"""
        try:
            current_time = datetime.now()
            result = self.conn.execute(
                "DELETE FROM analysis_cache WHERE expires_at < ?",
                [current_time]
            )
            deleted_count = result.fetchone()[0] if result else 0
            logger.info(f"清理了 {deleted_count} 条过期缓存记录")
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")

    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            stats = {}

            # 获取各表的记录数
            tables = [
                'strategy_execution_results',
                'indicator_calculation_results',
                'pattern_recognition_results',
                'backtest_metrics_history',
                'backtest_alerts_history',
                'performance_metrics',
                'optimization_logs',
                'analysis_cache'
            ]

            for table in tables:
                try:
                    result = self.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                    stats[table] = result.iloc[0]['count']
                except:
                    stats[table] = 0

            # 获取数据库文件大小
            if self.db_path.exists():
                file_size_bytes = self.db_path.stat().st_size
                stats['file_size_mb'] = file_size_bytes / (1024 * 1024)

            # 获取性能统计
            if OPTIMIZER_AVAILABLE and self.optimizer and self.optimizer.current_config:
                config = self.optimizer.current_config
                stats['memory_limit'] = config.memory_limit
                stats['threads'] = config.threads
                stats['optimization_enabled'] = True
            else:
                stats['optimization_enabled'] = False

            return stats

        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {'error': str(e)}

    def optimize_performance(self, workload_type: WorkloadType = WorkloadType.OLAP) -> bool:
        """重新优化性能配置"""
        if not OPTIMIZER_AVAILABLE or not self.optimizer:
            logger.warning("性能优化器不可用")
            return False

        try:
            # 重新优化配置
            success = self.optimizer.optimize_for_workload(workload_type)

            if success:
                logger.info(f" 性能配置已优化为{workload_type.value}工作负载")

                # 显示新的配置
                if self.optimizer.current_config:
                    config = self.optimizer.current_config
                    logger.info(f" 新配置: 内存={config.memory_limit}, 线程={config.threads}")

            return success

        except Exception as e:
            logger.error(f"性能优化失败: {e}")
            return False

    def benchmark_performance(self) -> Dict[str, Any]:
        """性能基准测试"""
        if not OPTIMIZER_AVAILABLE or not self.optimizer:
            logger.warning("性能优化器不可用，无法进行基准测试")
            return {'error': '性能优化器不可用'}

        # 使用实际的分析查询进行基准测试
        test_queries = [
            "SELECT COUNT(*) FROM strategy_execution_results",
            "SELECT strategy_name, COUNT(*), AVG(confidence) FROM strategy_execution_results GROUP BY strategy_name",
            "SELECT symbol, indicator_name, AVG(value) FROM indicator_calculation_results GROUP BY symbol, indicator_name LIMIT 100",
            "SELECT pattern_name, AVG(confidence), COUNT(*) FROM pattern_recognition_results GROUP BY pattern_name"
        ]

        return self.optimizer.benchmark_configuration(test_queries)

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

        if self.optimizer:
            self.optimizer.close()
            self.optimizer = None

# 全局实例和工厂函数
_analytics_db = None
_db_lock = threading.Lock()

def get_analytics_db(db_path: str = 'db/factorweave_analytics.duckdb') -> FactorWeaveAnalyticsDB:
    """获取分析数据库实例"""
    global _analytics_db

    with _db_lock:
        if _analytics_db is None:
            _analytics_db = FactorWeaveAnalyticsDB(db_path)

    return _analytics_db

def create_optimized_analytics_connection(workload_type: WorkloadType = WorkloadType.OLAP) -> FactorWeaveAnalyticsDB:
    """创建优化的分析数据库连接"""
    db = get_analytics_db()

    # 应用工作负载优化
    if OPTIMIZER_AVAILABLE:
        db.optimize_performance(workload_type)

    return db
