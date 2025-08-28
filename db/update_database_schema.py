#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库架构更新脚本

更新现有数据库以支持完整的FactorWeave-Quant功能
"""

import sqlite3
import duckdb
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseSchemaUpdater:
    """数据库架构更新器"""

    def __init__(self):
        self.db_dir = Path(__file__).parent
        self.sqlite_db_path = self.db_dir / "hikyuu_system.db"
        self.factorweave_db_path = self.db_dir / "factorweave_system.db"
        self.duckdb_analytics_path = self.db_dir / "factorweave_analytics.duckdb"

    def update_all_databases(self):
        """更新所有数据库"""
        logger.info("🔄 开始更新FactorWeave-Quant数据库架构")

        try:
            # 1. 更新SQLite数据库
            self.update_sqlite_databases()

            # 2. 更新DuckDB分析数据库
            self.update_duckdb_database()

            # 3. 插入初始数据
            self.insert_initial_data()

            # 4. 验证更新结果
            self.verify_update_results()

            logger.info("✅ 数据库架构更新完成")
            return True

        except Exception as e:
            logger.error(f"❌ 数据库更新失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_sqlite_databases(self):
        """更新SQLite数据库"""
        logger.info("📊 更新SQLite数据库架构...")

        # 确保数据库文件存在
        if not self.sqlite_db_path.exists():
            logger.info("  创建新的SQLite数据库...")
            self._create_sqlite_database()
        else:
            logger.info("  更新现有SQLite数据库...")
            self._update_existing_sqlite_database()

        # 确保FactorWeave系统数据库存在
        if not self.factorweave_db_path.exists():
            logger.info("  创建FactorWeave系统数据库...")
            self._create_factorweave_database()

    def _create_sqlite_database(self):
        """创建新的SQLite数据库"""
        with sqlite3.connect(self.sqlite_db_path) as conn:
            cursor = conn.cursor()

            # 执行完整的表创建
            self._create_all_sqlite_tables(cursor)
            conn.commit()

    def _update_existing_sqlite_database(self):
        """更新现有SQLite数据库"""
        with sqlite3.connect(self.sqlite_db_path) as conn:
            cursor = conn.cursor()

            # 获取现有表列表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}

            # 需要的表定义
            required_tables = {
                'config': self._get_config_table_sql(),
                'data_source': self._get_data_source_table_sql(),
                'user_favorites': self._get_user_favorites_table_sql(),
                'industry': self._get_industry_table_sql(),
                'market': self._get_market_table_sql(),
                'stock': self._get_stock_table_sql(),
                'concept': self._get_concept_table_sql(),
                'indicator': self._get_indicator_table_sql(),
                'user_log': self._get_user_log_table_sql(),
                'history': self._get_history_table_sql(),
                'indicator_combination': self._get_indicator_combination_table_sql(),
                'themes': self._get_themes_table_sql(),
                'pattern_types': self._get_pattern_types_table_sql(),
                'pattern_history': self._get_pattern_history_table_sql(),
                'plugins': self._get_plugins_table_sql(),
                'ai_prediction_config': self._get_ai_prediction_config_table_sql(),
                'ai_config_history': self._get_ai_config_history_table_sql(),
                'duckdb_config_profiles': self._get_duckdb_config_profiles_table_sql(),
                'duckdb_config_history': self._get_duckdb_config_history_table_sql(),
                'data_source_plugin_configs': self._get_data_source_plugin_configs_table_sql(),
                'data_source_routing_configs': self._get_data_source_routing_configs_table_sql(),
                'strategies': self._get_strategies_table_sql(),
                'strategy_parameters': self._get_strategy_parameters_table_sql(),
            }

            # 创建缺失的表
            for table_name, table_sql in required_tables.items():
                if table_name not in existing_tables:
                    logger.info(f"    创建表: {table_name}")
                    cursor.execute(table_sql)
                else:
                    logger.info(f"    表已存在: {table_name}")
                    # 这里可以添加列更新逻辑
                    self._update_table_columns(cursor, table_name)

            conn.commit()

    def _create_factorweave_database(self):
        """创建FactorWeave系统数据库"""
        with sqlite3.connect(self.factorweave_db_path) as conn:
            cursor = conn.cursor()

            # FactorWeave特有的系统配置表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS factorweave_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT NOT NULL,
                config_key TEXT NOT NULL,
                config_value TEXT NOT NULL,
                config_type TEXT DEFAULT 'string',
                description TEXT,
                is_encrypted BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(module, config_key)
            )''')

            # 系统监控配置表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_monitor_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_type TEXT NOT NULL,
                config_data TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                check_interval INTEGER DEFAULT 60,
                alert_threshold TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            conn.commit()

    def update_duckdb_database(self):
        """更新DuckDB分析数据库"""
        logger.info("📈 更新DuckDB分析数据库...")

        conn = duckdb.connect(str(self.duckdb_analytics_path))

        try:
            # 获取现有表
            existing_tables = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
            existing_table_names = {row[0] for row in existing_tables}

            logger.info(f"  现有表: {existing_table_names}")

            # 创建缺失的序列
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
                try:
                    conn.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name}")
                except Exception as e:
                    logger.warning(f"创建序列 {seq_name} 失败: {e}")

            # 需要创建的新表（如果不存在）
            new_tables = {
                'strategy_execution_results': '''
                    CREATE TABLE IF NOT EXISTS strategy_execution_results (
                        id INTEGER PRIMARY KEY DEFAULT nextval('strategy_execution_results_seq'),
                        strategy_name VARCHAR NOT NULL,
                        symbol VARCHAR NOT NULL,
                        execution_time TIMESTAMP NOT NULL,
                        signal_type VARCHAR NOT NULL,
                        price DOUBLE,
                        quantity INTEGER,
                        confidence DOUBLE,
                        reason TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                '''
            }

            # 创建缺失的表
            for table_name, table_sql in new_tables.items():
                if table_name not in existing_table_names:
                    logger.info(f"    创建表: {table_name}")
                    conn.execute(table_sql)
                else:
                    logger.info(f"    表已存在: {table_name}")

            # 更新现有表结构（如果需要）
            self._update_duckdb_table_structures(conn, existing_table_names)

            # 创建或更新索引
            self._create_duckdb_indexes(conn)

            # 检查现有数据（移除智能性能洞察检查）
            logger.info("检查现有缓存数据...")

            # 插入基础测试数据（移除智能性能洞察数据）
            basic_test_data = [
                ("test_basic_analysis", "technical_analysis",
                 '{"indicators": {"RSI": 50.0, "MACD": 0.0}, "timestamp": "2024-08-21T20:00:00"}',
                 "2025-08-22 20:00:00", "2024-08-21 20:00:00"),
            ]

            for data in basic_test_data:
                conn.execute("""
                    INSERT OR IGNORE INTO analysis_cache 
                    (cache_key, cache_type, data, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, data)

            conn.commit()
            logger.info("基础测试数据插入完成")

            conn.commit()

        finally:
            conn.close()

    def _update_duckdb_table_structures(self, conn, existing_tables):
        """更新DuckDB表结构"""

        # 检查pattern_recognition_results表是否需要添加列
        if 'pattern_recognition_results' in existing_tables:
            try:
                # 检查是否有recognition_time列
                columns = conn.execute("DESCRIBE pattern_recognition_results").fetchall()
                column_names = {col[0] for col in columns}

                if 'recognition_time' not in column_names and 'detection_time' in column_names:
                    logger.info("    pattern_recognition_results表使用detection_time列，无需修改")

                # 检查是否缺少其他必要列
                required_columns = {
                    'pattern_type': 'VARCHAR',
                    'timeframe': 'VARCHAR',
                    'signal_type': 'VARCHAR',
                    'start_index': 'INTEGER',
                    'end_index': 'INTEGER',
                    'key_points': 'TEXT'
                }

                for col_name, col_type in required_columns.items():
                    if col_name not in column_names:
                        try:
                            conn.execute(f"ALTER TABLE pattern_recognition_results ADD COLUMN {col_name} {col_type}")
                            logger.info(f"      添加列: {col_name}")
                        except Exception as e:
                            logger.warning(f"      添加列 {col_name} 失败: {e}")

            except Exception as e:
                logger.warning(f"更新pattern_recognition_results表失败: {e}")

    def _create_duckdb_indexes(self, conn):
        """创建DuckDB索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_strategy_execution_symbol ON strategy_execution_results(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_execution_time ON strategy_execution_results(execution_time)",
            "CREATE INDEX IF NOT EXISTS idx_indicator_calculation_symbol ON indicator_calculation_results(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_indicator_calculation_time ON indicator_calculation_results(calculation_time)",
            "CREATE INDEX IF NOT EXISTS idx_pattern_recognition_symbol ON pattern_recognition_results(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_pattern_recognition_detection_time ON pattern_recognition_results(detection_time)",
            "CREATE INDEX IF NOT EXISTS idx_backtest_metrics_timestamp ON backtest_metrics_history(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_backtest_alerts_timestamp ON backtest_alerts_history(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_pattern ON performance_metrics(pattern_name)",
            "CREATE INDEX IF NOT EXISTS idx_optimization_logs_session ON optimization_logs(optimization_session_id)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_cache_type ON analysis_cache(cache_type)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_cache_expires ON analysis_cache(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_cache_key ON analysis_cache(cache_key)",
        ]

        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"创建索引失败: {e}")

    def insert_initial_data(self):
        """插入初始数据"""
        logger.info("📝 插入初始数据...")

        self._insert_sqlite_initial_data()
        self._insert_duckdb_initial_data()

    def _insert_sqlite_initial_data(self):
        """插入SQLite初始数据"""
        with sqlite3.connect(self.sqlite_db_path) as conn:
            cursor = conn.cursor()

            # 插入系统配置（如果不存在）
            config_data = [
                ('system.version', '2.0.0', 'FactorWeave-Quant系统版本'),
                ('system.initialized', 'true', '系统是否已初始化'),
                ('system.theme', 'default', '系统默认主题'),
                ('database.sqlite_path', str(self.sqlite_db_path), 'SQLite数据库路径'),
                ('database.duckdb_path', str(self.duckdb_analytics_path), 'DuckDB数据库路径'),
                ('ui.language', 'zh_CN', '界面语言'),
                ('performance.enable_cache', 'true', '启用缓存'),
            ]

            for key, value, desc in config_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO config (key, value, description) 
                    VALUES (?, ?, ?)
                ''', (key, value, desc))

            # 插入市场数据（如果不存在）
            market_data = [
                ('SH', '上海证券交易所', 'CN', 'Asia/Shanghai', '{}'),
                ('SZ', '深圳证券交易所', 'CN', 'Asia/Shanghai', '{}'),
                ('BJ', '北京证券交易所', 'CN', 'Asia/Shanghai', '{}'),
                ('HK', '香港交易所', 'HK', 'Asia/Hong_Kong', '{}'),
                ('US', '美国股市', 'US', 'America/New_York', '{}'),
            ]

            for code, name, region, timezone, extra in market_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO market (code, name, region, timezone, extra) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (code, name, region, timezone, extra))

            # 插入AI预测配置（如果不存在）
            current_time = datetime.now().isoformat()
            ai_config_data = [
                ('model.pattern.enabled', 'true', 'boolean', '是否启用形态识别模型'),
                ('model.trend.enabled', 'true', 'boolean', '是否启用趋势预测模型'),
                ('prediction.confidence_threshold', '0.7', 'float', '预测置信度阈值'),
            ]

            for key, value, config_type, desc in ai_config_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO ai_prediction_config 
                    (config_key, config_value, config_type, description, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (key, value, config_type, desc, current_time, current_time))

            # 插入默认DuckDB配置（如果不存在）
            cursor.execute('''
                INSERT OR IGNORE INTO duckdb_config_profiles 
                (profile_name, description, workload_type, is_active, is_default)
                VALUES ('default', '默认OLAP配置', 'OLAP', 1, 1)
            ''')

            conn.commit()

    def _insert_duckdb_initial_data(self):
        """插入DuckDB初始数据"""
        conn = duckdb.connect(str(self.duckdb_analytics_path))

        try:
            # 插入基础分析缓存数据（移除智能性能洞察）
            basic_cache_data = [
                ("basic_analysis_1", "technical_analysis",
                 '{"indicators": {"RSI": 45.0, "MACD": -0.1}, "timestamp": "2024-08-21T21:45:00"}',
                 "2025-08-23 20:00:00", "2025-08-21 21:45:00"),
                ("basic_analysis_2", "market_sentiment",
                 '{"sentiment": "neutral", "score": 0.5, "timestamp": "2024-08-21T21:45:00"}',
                 "2025-08-23 20:00:00", "2025-08-21 21:45:00"),
            ]

            for data in basic_cache_data:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO analysis_cache 
                        (cache_key, cache_type, data, expires_at, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, data)
                except Exception as e:
                    logger.warning(f"插入基础分析数据失败: {e}")

            conn.commit()
            logger.info(f"  添加了 {len(basic_cache_data)} 条基础分析数据")

        finally:
            conn.close()

    def verify_update_results(self):
        """验证更新结果"""
        logger.info("🔍 验证数据库更新结果...")

        # 验证SQLite数据库
        with sqlite3.connect(self.sqlite_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            logger.info(f"  SQLite数据库表数量: {table_count}")

        # 验证DuckDB数据库
        conn = duckdb.connect(str(self.duckdb_analytics_path))
        try:
            result = conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'main'").fetchone()
            table_count = result[0] if result else 0
            logger.info(f"  DuckDB数据库表数量: {table_count}")

            # 检查基础分析数据
            cache_count = conn.execute("SELECT COUNT(*) FROM analysis_cache").fetchone()[0]
            logger.info(f"  分析缓存数据: {cache_count} 条")
        finally:
            conn.close()

    def _update_table_columns(self, cursor, table_name):
        """更新表列（如果需要）"""
        # 这里可以添加具体的列更新逻辑
        pass

    # 表定义方法
    def _get_config_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_data_source_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS data_source (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            config TEXT,
            is_active INTEGER DEFAULT 0,
            priority INTEGER DEFAULT 50,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_user_favorites_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS user_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            fav_type TEXT NOT NULL,
            fav_key TEXT NOT NULL,
            fav_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_industry_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS industry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            level INTEGER DEFAULT 1,
            code TEXT UNIQUE,
            extra TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_market_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            region TEXT DEFAULT 'CN',
            timezone TEXT DEFAULT 'Asia/Shanghai',
            extra TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_stock_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            market_code TEXT NOT NULL,
            type TEXT DEFAULT 'stock',
            valid INTEGER DEFAULT 1,
            start_date TEXT,
            end_date TEXT,
            industry_id INTEGER,
            extra TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_concept_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS concept (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            extra TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_indicator_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS indicator (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            params TEXT,
            description TEXT,
            formula TEXT,
            extra TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_user_log_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS user_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_history_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            record_type TEXT NOT NULL,
            record_key TEXT NOT NULL,
            record_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_indicator_combination_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS indicator_combination (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            indicators TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            extra TEXT
        )'''

    def _get_themes_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            origin TEXT DEFAULT 'system',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_pattern_types_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS pattern_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            english_name TEXT,
            category TEXT NOT NULL,
            signal_type TEXT,
            description TEXT,
            min_periods INTEGER DEFAULT 5,
            max_periods INTEGER DEFAULT 60,
            confidence_threshold REAL DEFAULT 0.5,
            algorithm_code TEXT,
            parameters TEXT,
            success_rate REAL DEFAULT 0.7,
            risk_level TEXT DEFAULT 'medium',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_pattern_history_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS pattern_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            trigger_date TEXT NOT NULL,
            trigger_price REAL NOT NULL,
            result_date TEXT,
            result_price REAL,
            return_rate REAL,
            is_successful INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_plugins_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS plugins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            version TEXT NOT NULL,
            plugin_type TEXT NOT NULL,
            category TEXT,
            description TEXT,
            author TEXT,
            status TEXT DEFAULT 'disabled',
            config TEXT,
            metadata TEXT,
            file_path TEXT,
            class_name TEXT,
            priority INTEGER DEFAULT 50,
            last_enabled_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_ai_prediction_config_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS ai_prediction_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            config_type TEXT NOT NULL DEFAULT 'json',
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1
        )'''

    def _get_ai_config_history_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS ai_config_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT DEFAULT 'system',
            changed_at TEXT NOT NULL
        )'''

    def _get_duckdb_config_profiles_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS duckdb_config_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_name TEXT UNIQUE NOT NULL,
            description TEXT,
            workload_type TEXT DEFAULT 'OLAP',
            memory_limit TEXT DEFAULT '4.0GB',
            max_memory TEXT DEFAULT '4.4GB',
            buffer_pool_size TEXT DEFAULT '1GB',
            temp_memory_limit TEXT DEFAULT '2GB',
            threads INTEGER DEFAULT 4,
            io_threads INTEGER DEFAULT 2,
            parallel_tasks INTEGER DEFAULT 4,
            worker_threads INTEGER DEFAULT 3,
            checkpoint_threshold TEXT DEFAULT '512MB',
            wal_autocheckpoint INTEGER DEFAULT 5000,
            temp_directory_size TEXT DEFAULT '20GB',
            enable_fsync BOOLEAN DEFAULT 1,
            enable_mmap BOOLEAN DEFAULT 1,
            enable_optimizer BOOLEAN DEFAULT 1,
            enable_profiling BOOLEAN DEFAULT 0,
            enable_progress_bar BOOLEAN DEFAULT 1,
            enable_object_cache BOOLEAN DEFAULT 1,
            max_expression_depth INTEGER DEFAULT 1000,
            enable_external_access BOOLEAN DEFAULT 1,
            enable_httpfs BOOLEAN DEFAULT 1,
            enable_parquet_statistics BOOLEAN DEFAULT 1,
            preserve_insertion_order BOOLEAN DEFAULT 0,
            enable_verification BOOLEAN DEFAULT 0,
            force_parallelism BOOLEAN DEFAULT 1,
            enable_join_order_optimizer BOOLEAN DEFAULT 1,
            enable_unnest_rewriter BOOLEAN DEFAULT 1,
            enable_object_cache_map BOOLEAN DEFAULT 1,
            enable_auto_analyze BOOLEAN DEFAULT 1,
            auto_analyze_sample_size INTEGER DEFAULT 100000,
            enable_compression BOOLEAN DEFAULT 1,
            compression_level INTEGER DEFAULT 6,
            http_timeout INTEGER DEFAULT 30000,
            http_retries INTEGER DEFAULT 3,
            is_active BOOLEAN DEFAULT 0,
            is_default BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT DEFAULT 'system'
        )'''

    def _get_duckdb_config_history_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS duckdb_config_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_config TEXT,
            new_config TEXT,
            changed_by TEXT DEFAULT 'system',
            changed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )'''

    def _get_data_source_plugin_configs_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS data_source_plugin_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plugin_id TEXT NOT NULL,
            config_data TEXT NOT NULL,
            priority INTEGER DEFAULT 50,
            weight REAL DEFAULT 1.0,
            enabled BOOLEAN DEFAULT 1,
            health_check_interval INTEGER DEFAULT 30,
            timeout_seconds INTEGER DEFAULT 30,
            retry_count INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(plugin_id)
        )'''

    def _get_data_source_routing_configs_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS data_source_routing_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_type TEXT NOT NULL,
            plugin_priorities TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asset_type)
        )'''

    def _get_strategies_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            strategy_type TEXT NOT NULL,
            version TEXT NOT NULL DEFAULT '1.0.0',
            author TEXT DEFAULT '',
            description TEXT DEFAULT '',
            category TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            metadata TEXT DEFAULT '{}',
            class_path TEXT NOT NULL
        )'''

    def _get_strategy_parameters_table_sql(self):
        return '''
        CREATE TABLE IF NOT EXISTS strategy_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            param_name TEXT NOT NULL,
            param_value TEXT NOT NULL,
            param_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            min_value TEXT DEFAULT NULL,
            max_value TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(strategy_id, param_name)
        )'''

    def _create_all_sqlite_tables(self, cursor):
        """创建所有SQLite表"""
        table_methods = [
            self._get_config_table_sql,
            self._get_data_source_table_sql,
            self._get_user_favorites_table_sql,
            self._get_industry_table_sql,
            self._get_market_table_sql,
            self._get_stock_table_sql,
            self._get_concept_table_sql,
            self._get_indicator_table_sql,
            self._get_user_log_table_sql,
            self._get_history_table_sql,
            self._get_indicator_combination_table_sql,
            self._get_themes_table_sql,
            self._get_pattern_types_table_sql,
            self._get_pattern_history_table_sql,
            self._get_plugins_table_sql,
            self._get_ai_prediction_config_table_sql,
            self._get_ai_config_history_table_sql,
            self._get_duckdb_config_profiles_table_sql,
            self._get_duckdb_config_history_table_sql,
            self._get_data_source_plugin_configs_table_sql,
            self._get_data_source_routing_configs_table_sql,
            self._get_strategies_table_sql,
            self._get_strategy_parameters_table_sql,
        ]

        for method in table_methods:
            cursor.execute(method())


def main():
    """主函数"""
    print("=" * 60)
    print("FactorWeave-Quant 数据库架构更新系统")
    print("=" * 60)

    updater = DatabaseSchemaUpdater()

    if updater.update_all_databases():
        print("\n🎉 数据库架构更新成功！")
        print("\n📊 更新内容:")
        print("  ✅ SQLite系统数据库架构")
        print("  ✅ DuckDB分析数据库架构")
        print("  ✅ 缺失表和列的创建")
        print("  ✅ 初始配置和数据")
        print("  ✅ 性能优化索引")

        return True
    else:
        print("\n❌ 数据库架构更新失败！")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
