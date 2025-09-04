#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化系统数据库架构
管理算法版本、性能指标、优化日志等数据
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading


class OptimizationDatabaseManager:
    """优化系统数据库管理器 - 单例模式"""

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, db_path: str = 'db/factorweave_system.sqlite'):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = 'db/factorweave_system.sqlite'):
        # 避免重复初始化
        if OptimizationDatabaseManager._initialized:
            return

        self.db_path = db_path
        self.init_tables()
        OptimizationDatabaseManager._initialized = True

    def init_tables(self):
        """初始化数据库表"""
        # 检查是否已经初始化过
        if hasattr(self, '_tables_initialized'):
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 算法版本表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS algorithm_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id INTEGER,
                    pattern_name TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    algorithm_code TEXT NOT NULL,
                    parameters TEXT,  -- JSON格式存储参数
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 0,
                    parent_version_id INTEGER,
                    optimization_method TEXT DEFAULT 'manual',  -- manual, genetic, grid_search, bayesian
                    FOREIGN KEY (parent_version_id) REFERENCES algorithm_versions(id)
                )
            ''')

            # 性能指标表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id INTEGER NOT NULL,
                    pattern_name TEXT NOT NULL,
                    test_dataset_id TEXT,
                    test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    true_positives INTEGER DEFAULT 0,
                    false_positives INTEGER DEFAULT 0,
                    true_negatives INTEGER DEFAULT 0,
                    false_negatives INTEGER DEFAULT 0,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    accuracy REAL,
                    execution_time REAL,  -- 秒
                    memory_usage REAL,    -- MB
                    cpu_usage REAL,       -- 百分比
                    signal_quality REAL,  -- 信号质量评分 0-1
                    confidence_avg REAL,  -- 平均置信度
                    confidence_std REAL,  -- 置信度标准差
                    patterns_found INTEGER DEFAULT 0,  -- 识别的形态数量
                    robustness_score REAL,             -- 鲁棒性评分
                    parameter_sensitivity REAL,        -- 参数敏感性
                    overall_score REAL,                 -- 综合评分
                    test_conditions TEXT,               -- JSON格式存储测试条件
                    FOREIGN KEY (version_id) REFERENCES algorithm_versions(id)
                )
            ''')

            # 优化日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT NOT NULL,
                    optimization_session_id TEXT UNIQUE NOT NULL,
                    optimization_method TEXT NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    status TEXT DEFAULT 'running',  -- running, completed, failed, cancelled
                    initial_version_id INTEGER,
                    final_version_id INTEGER,
                    iterations INTEGER DEFAULT 0,
                    best_score REAL,
                    improvement_percentage REAL,
                    optimization_config TEXT,  -- JSON格式存储优化配置
                    optimization_log TEXT,     -- 详细日志
                    error_message TEXT,
                    FOREIGN KEY (initial_version_id) REFERENCES algorithm_versions(id),
                    FOREIGN KEY (final_version_id) REFERENCES algorithm_versions(id)
                )
            ''')

            # 形态信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pattern_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT UNIQUE NOT NULL,
                    chinese_name TEXT,
                    description TEXT,
                    category TEXT,
                    difficulty_level INTEGER DEFAULT 3,  -- 1-5
                    is_active BOOLEAN DEFAULT 1,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_optimized TIMESTAMP,
                    optimization_count INTEGER DEFAULT 0,
                    best_score REAL DEFAULT 0.0,
                    avg_score REAL DEFAULT 0.0
                )
            ''')

            # 优化任务队列表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    optimization_type TEXT NOT NULL,  -- auto, manual, scheduled
                    optimization_config TEXT,  -- JSON格式存储配置
                    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_time TIMESTAMP,
                    completed_time TIMESTAMP,
                    assigned_worker TEXT,
                    progress REAL DEFAULT 0.0,
                    estimated_duration INTEGER,  -- 预估时间（秒）
                    result_summary TEXT
                )
            ''')

            conn.commit()
            conn.close()

            # 标记表已初始化
            self._tables_initialized = True
            print("✅ 优化系统数据库表初始化完成")

        except sqlite3.OperationalError as e:
            print(f"⚠️ 数据库初始化失败: {e}")
            # 不抛出异常，允许系统继续运行
        except Exception as e:
            print(f"⚠️ 优化系统数据库初始化异常: {e}")
            # 不抛出异常，允许系统继续运行

    def save_algorithm_version(self, pattern_id: int, pattern_name: str,
                               algorithm_code: str, parameters: Dict[str, Any],
                               description: str = "", optimization_method: str = "manual",
                               parent_version_id: Optional[int] = None) -> int:
        """保存算法版本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取下一个版本号
        cursor.execute('''
            SELECT COALESCE(MAX(version_number), 0) + 1 
            FROM algorithm_versions 
            WHERE pattern_id = ?
        ''', (pattern_id,))
        version_number = cursor.fetchone()[0]

        # 插入新版本
        cursor.execute('''
            INSERT INTO algorithm_versions 
            (pattern_id, pattern_name, version_number, algorithm_code, parameters, 
             description, parent_version_id, optimization_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pattern_id, pattern_name, version_number, algorithm_code,
              json.dumps(parameters), description, parent_version_id, optimization_method))

        version_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return version_id

    def get_algorithm_versions(self, pattern_name: str, limit: int = 10) -> List[Dict]:
        """获取算法版本列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, version_number, algorithm_code, parameters, created_time,
                   description, is_active, optimization_method
            FROM algorithm_versions 
            WHERE pattern_name = ?
            ORDER BY version_number DESC
            LIMIT ?
        ''', (pattern_name, limit))

        versions = []
        for row in cursor.fetchall():
            versions.append({
                'id': row[0],
                'version_number': row[1],
                'algorithm_code': row[2],
                'parameters': json.loads(row[3]) if row[3] else {},
                'created_time': row[4],
                'description': row[5],
                'is_active': bool(row[6]),
                'optimization_method': row[7]
            })

        conn.close()
        return versions

    def save_performance_metrics(self, version_id: int, pattern_name: str,
                                 metrics: Dict[str, Any]) -> int:
        """保存性能指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO performance_metrics 
            (version_id, pattern_name, test_dataset_id, true_positives, false_positives,
             true_negatives, false_negatives, precision, recall, f1_score, accuracy,
             execution_time, memory_usage, cpu_usage, signal_quality, confidence_avg,
             confidence_std, patterns_found, robustness_score, parameter_sensitivity,
             overall_score, test_conditions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            version_id, pattern_name, metrics.get('test_dataset_id'),
            metrics.get('true_positives', 0), metrics.get(
                'false_positives', 0),
            metrics.get('true_negatives', 0), metrics.get(
                'false_negatives', 0),
            metrics.get('precision'), metrics.get('recall'),
            metrics.get('f1_score'), metrics.get('accuracy'),
            metrics.get('execution_time'), metrics.get('memory_usage'),
            metrics.get('cpu_usage'), metrics.get('signal_quality'),
            metrics.get('confidence_avg'), metrics.get('confidence_std'),
            metrics.get('patterns_found'), metrics.get('robustness_score'),
            metrics.get('parameter_sensitivity'), metrics.get('overall_score'),
            json.dumps(metrics.get('test_conditions', {}))
        ))

        metric_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return metric_id

    def get_performance_history(self, pattern_name: str, limit: int = 50) -> List[Dict]:
        """获取性能历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT pm.*, av.version_number, av.optimization_method
            FROM performance_metrics pm
            JOIN algorithm_versions av ON pm.version_id = av.id
            WHERE pm.pattern_name = ?
            ORDER BY pm.test_time DESC
            LIMIT ?
        ''', (pattern_name, limit))

        history = []
        columns = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            if record['test_conditions']:
                record['test_conditions'] = json.loads(
                    record['test_conditions'])
            history.append(record)

        conn.close()
        return history

    def start_optimization_log(self, pattern_name: str, optimization_method: str,
                               initial_version_id: int, config: Dict[str, Any]) -> str:
        """开始优化日志记录"""
        import uuid
        session_id = str(uuid.uuid4())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO optimization_logs 
            (pattern_name, optimization_session_id, optimization_method, 
             start_time, status, initial_version_id, optimization_config)
            VALUES (?, ?, ?, ?, 'running', ?, ?)
        ''', (pattern_name, session_id, optimization_method,
              datetime.now(), initial_version_id, json.dumps(config)))

        conn.commit()
        conn.close()

        return session_id

    def update_optimization_log(self, session_id: str, **kwargs):
        """更新优化日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 构建更新语句
        update_fields = []
        values = []

        for key, value in kwargs.items():
            if key in ['status', 'final_version_id', 'iterations', 'best_score',
                       'improvement_percentage', 'optimization_log', 'error_message']:
                update_fields.append(f"{key} = ?")
                values.append(value)

        if 'status' in kwargs and kwargs['status'] in ['completed', 'failed', 'cancelled']:
            update_fields.append("end_time = ?")
            values.append(datetime.now())

        if update_fields:
            values.append(session_id)
            cursor.execute(f'''
                UPDATE optimization_logs 
                SET {', '.join(update_fields)}
                WHERE optimization_session_id = ?
            ''', values)

        conn.commit()
        conn.close()

    def cleanup_old_versions(self, pattern_name: str, keep_count: int = 10):
        """清理旧版本，保留最近的版本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取要删除的版本ID
        cursor.execute('''
            SELECT id FROM algorithm_versions 
            WHERE pattern_name = ? AND is_active = 0
            ORDER BY version_number DESC
            LIMIT -1 OFFSET ?
        ''', (pattern_name, keep_count))

        old_version_ids = [row[0] for row in cursor.fetchall()]

        if old_version_ids:
            # 删除相关的性能指标
            cursor.execute(f'''
                DELETE FROM performance_metrics 
                WHERE version_id IN ({','.join(['?'] * len(old_version_ids))})
            ''', old_version_ids)

            # 删除旧版本
            cursor.execute(f'''
                DELETE FROM algorithm_versions 
                WHERE id IN ({','.join(['?'] * len(old_version_ids))})
            ''', old_version_ids)

            print(f"✅ 清理了 {len(old_version_ids)} 个旧版本")

        conn.commit()
        conn.close()

    def get_optimization_statistics(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # 总版本数
        cursor.execute('SELECT COUNT(*) FROM algorithm_versions')
        stats['total_versions'] = cursor.fetchone()[0]

        # 活跃版本数
        cursor.execute(
            'SELECT COUNT(*) FROM algorithm_versions WHERE is_active = 1')
        stats['active_versions'] = cursor.fetchone()[0]

        # 优化任务统计
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM optimization_logs 
            GROUP BY status
        ''')
        stats['optimization_tasks'] = dict(cursor.fetchall())

        # 平均性能提升
        cursor.execute('''
            SELECT AVG(improvement_percentage) 
            FROM optimization_logs 
            WHERE status = 'completed' AND improvement_percentage IS NOT NULL
        ''')
        result = cursor.fetchone()[0]
        stats['avg_improvement'] = result if result else 0

        # 最佳性能形态
        cursor.execute('''
            SELECT pattern_name, MAX(overall_score) as best_score
            FROM performance_metrics 
            GROUP BY pattern_name 
            ORDER BY best_score DESC 
            LIMIT 10
        ''')
        stats['top_performers'] = [
            {'pattern': row[0], 'score': row[1]}
            for row in cursor.fetchall()
        ]

        conn.close()
        return stats


def create_optimization_database():
    """创建优化系统数据库"""
    manager = OptimizationDatabaseManager()
    print("🚀 优化系统数据库创建完成")
    return manager


if __name__ == "__main__":
    # 测试数据库创建
    create_optimization_database()
