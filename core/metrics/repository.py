# core/metrics/repository.py
import sqlite3
import threading
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import datetime
import logging
import json
import time
from threading import Lock

logger = logging.getLogger(__name__)

# 获取项目根目录的绝对路径
# 在大多数情况下，这个脚本会在项目的某个子目录中运行
# 我们假设项目根目录是当前文件路径的第五级父目录
# D:/DevelopTool/FreeCode/YS-Quant‌/YS-Quant‌/core/metrics/repository.py
# 根目录是 YS-Quant‌
try:
    # This logic assumes a fixed directory structure.
    # A more robust solution might involve environment variables or a configuration file
    # that specifies the project root.
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
except IndexError:
    # Fallback for different execution environments
    PROJECT_ROOT = Path.cwd()

DB_FILE = PROJECT_ROOT / "db" / "metrics.db"
DB_FILE.parent.mkdir(parents=True, exist_ok=True)


class MetricsRepository:
    """
    指标数据仓储

    负责存储和检索系统性能指标数据，支持内存缓存和数据库持久化。
    """

    def __init__(self, db_path: str = "db/metrics.db", cache_size: int = 1000):
        """
        初始化指标数据仓储

        Args:
            db_path: 数据库文件路径
            cache_size: 内存缓存大小
        """
        self.db_path = db_path
        self.cache_size = cache_size
        self.cache = {}
        self.cache_lock = Lock()
        self._initialize_db()

    def _initialize_db(self) -> None:
        """初始化数据库结构"""
        try:
            # 确保数据库目录存在
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            # 创建数据库连接
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建指标表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                category TEXT NOT NULL,
                tags TEXT
            )
            ''')

            # 创建索引
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics (metric_name)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics (timestamp)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_metrics_category ON metrics (category)')

            # 创建聚合指标表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS aggregated_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                min_value REAL,
                max_value REAL,
                avg_value REAL,
                count INTEGER,
                period TEXT NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL
            )
            ''')

            # 创建兼容旧版本的表结构
            cursor.execute('''
                    CREATE TABLE IF NOT EXISTS resource_metrics_summary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        t_stamp DATETIME NOT NULL,
                        cpu REAL NOT NULL,
                        mem REAL NOT NULL,
                        disk REAL NOT NULL
                    )
            ''')

            cursor.execute('''
                    CREATE TABLE IF NOT EXISTS app_metrics_summary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        t_stamp DATETIME NOT NULL,
                        operation TEXT NOT NULL,
                        avg_duration REAL NOT NULL,
                        max_duration REAL NOT NULL,
                        call_count INTEGER NOT NULL,
                        error_count INTEGER NOT NULL,
                        UNIQUE(t_stamp, operation)
                    )
            ''')

            conn.commit()
            conn.close()

            logger.info("指标数据库初始化完成")

        except Exception as e:
            logger.error(f"初始化指标数据库失败: {e}")

    def store_metric(self,
                     metric_name: str,
                     metric_value: Any,
                     category: str = "system",
                     tags: Dict[str, str] = None) -> bool:
        """
        存储指标数据

        Args:
            metric_name: 指标名称
            metric_value: 指标值
            category: 指标类别
            tags: 标签字典

        Returns:
            是否成功
        """
        try:
            timestamp = int(time.time())

            # 序列化值和标签
            if not isinstance(metric_value, (int, float, str, bool)):
                metric_value = json.dumps(metric_value)

            tags_json = json.dumps(tags) if tags else None

            # 添加到内存缓存
            with self.cache_lock:
                cache_key = f"{metric_name}:{category}"
                if cache_key not in self.cache:
                    self.cache[cache_key] = []

                self.cache[cache_key].append({
                    "value": metric_value,
                    "timestamp": timestamp,
                    "tags": tags_json
                })

                # 如果缓存过大，写入数据库
                if len(self.cache[cache_key]) >= self.cache_size:
                    self._flush_cache(cache_key)

            return True

        except Exception as e:
            logger.error(f"存储指标失败 {metric_name}: {e}")
            return False

    def _flush_cache(self, cache_key: str) -> None:
        """
        将缓存写入数据库

        Args:
            cache_key: 缓存键
        """
        try:
            if cache_key not in self.cache or not self.cache[cache_key]:
                return

            metric_name, category = cache_key.split(":", 1)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 批量插入
            data = []
            for item in self.cache[cache_key]:
                data.append((
                    metric_name,
                    item["value"],
                    item["timestamp"],
                    category,
                    item["tags"]
                ))

                cursor.executemany(
                    "INSERT INTO metrics (metric_name, metric_value, timestamp, category, tags) VALUES (?, ?, ?, ?, ?)",
                    data
                )

            conn.commit()
            conn.close()

            # 清空缓存
            self.cache[cache_key] = []

        except Exception as e:
            logger.error(f"将缓存写入数据库失败 {cache_key}: {e}")

    def query_metrics(self,
                      metric_name: str,
                      start_time: Optional[int] = None,
                      end_time: Optional[int] = None,
                      category: Optional[str] = None,
                      limit: int = 1000) -> List[Dict[str, Any]]:
        """
        查询指标数据

        Args:
            metric_name: 指标名称
            start_time: 开始时间戳
            end_time: 结束时间戳
            category: 指标类别
            limit: 返回结果限制

        Returns:
            指标数据列表
        """
        try:
            # 构建查询
            query = "SELECT metric_name, metric_value, timestamp, category, tags FROM metrics WHERE metric_name = ?"
            params = [metric_name]

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            # 执行查询
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # 处理结果
            results = []
            for row in rows:
                value = row["metric_value"]

                # 尝试解析JSON值
                try:
                    if value.startswith('{') or value.startswith('['):
                        value = json.loads(value)
                except (json.JSONDecodeError, AttributeError):
                    pass

                # 解析标签
                tags = None
                if row["tags"]:
                    try:
                        tags = json.loads(row["tags"])
                    except json.JSONDecodeError:
                        pass

                results.append({
                    "name": row["metric_name"],
                    "value": value,
                    "timestamp": row["timestamp"],
                    "category": row["category"],
                    "tags": tags
                })

            conn.close()
            return results

        except Exception as e:
            logger.error(f"查询指标失败 {metric_name}: {e}")
            return []

    def get_latest_metric(self,
                          metric_name: str,
                          category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取最新的指标值

        Args:
            metric_name: 指标名称
            category: 指标类别

        Returns:
            最新的指标值或None
        """
        results = self.query_metrics(
            metric_name=metric_name,
            category=category,
            limit=1
        )

        return results[0] if results else None

    def aggregate_metrics(self,
                          metric_name: str,
                          period: str = "hour",
                          start_time: Optional[int] = None,
                          end_time: Optional[int] = None) -> Dict[str, Any]:
        """
        聚合指标数据

        Args:
            metric_name: 指标名称
            period: 聚合周期 (minute, hour, day, week, month)
            start_time: 开始时间戳
            end_time: 结束时间戳

        Returns:
            聚合结果
        """
        try:
            # 设置默认时间范围
            if not end_time:
                end_time = int(time.time())

            if not start_time:
                # 根据周期设置默认开始时间
                if period == "minute":
                    start_time = end_time - 60 * 60  # 1小时前
                elif period == "hour":
                    start_time = end_time - 24 * 60 * 60  # 1天前
                elif period == "day":
                    start_time = end_time - 7 * 24 * 60 * 60  # 1周前
                elif period == "week":
                    start_time = end_time - 4 * 7 * 24 * 60 * 60  # 4周前
                else:  # month
                    start_time = end_time - 12 * 30 * 24 * 60 * 60  # 12个月前

            # 查询数据
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    MIN(CASE WHEN metric_value GLOB '*[0-9]*' AND metric_value NOT GLOB '*[a-zA-Z]*' THEN CAST(metric_value AS REAL) ELSE NULL END) as min_value,
                    MAX(CASE WHEN metric_value GLOB '*[0-9]*' AND metric_value NOT GLOB '*[a-zA-Z]*' THEN CAST(metric_value AS REAL) ELSE NULL END) as max_value,
                    AVG(CASE WHEN metric_value GLOB '*[0-9]*' AND metric_value NOT GLOB '*[a-zA-Z]*' THEN CAST(metric_value AS REAL) ELSE NULL END) as avg_value,
                    COUNT(*) as count
                FROM metrics
                WHERE metric_name = ? AND timestamp >= ? AND timestamp <= ?
                """,
                (metric_name, start_time, end_time)
            )

            row = cursor.fetchone()

            # 保存聚合结果
            cursor.execute(
                """
                INSERT INTO aggregated_metrics 
                (metric_name, min_value, max_value, avg_value, count, period, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (metric_name, row[0], row[1], row[2],
                 row[3], period, start_time, end_time)
            )

            conn.commit()
            conn.close()

            return {
                "metric_name": metric_name,
                "min": row[0],
                "max": row[1],
                "avg": row[2],
                "count": row[3],
                "period": period,
                "start_time": start_time,
                "end_time": end_time
            }

        except Exception as e:
            logger.error(f"聚合指标失败 {metric_name}: {e}")
            return {
                "metric_name": metric_name,
                "error": str(e)
            }

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        清理旧数据

        Args:
            days: 保留天数

        Returns:
            删除的记录数
        """
        try:
            # 计算截止时间戳
            cutoff_time = int(time.time()) - (days * 24 * 60 * 60)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 删除旧数据
            cursor.execute(
                "DELETE FROM metrics WHERE timestamp < ?", (cutoff_time,))
            deleted_count = cursor.rowcount

            conn.commit()
            conn.close()

            logger.info(f"已清理 {deleted_count} 条旧指标数据")
            return deleted_count

        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return 0

    def flush_all_cache(self) -> None:
        """将所有缓存写入数据库"""
        with self.cache_lock:
            for cache_key in list(self.cache.keys()):
                self._flush_cache(cache_key)

    def dispose(self) -> None:
        """释放资源"""
        self.flush_all_cache()

    def query_historical_data(self,
                              start_time: datetime,
                              end_time: datetime,
                              table: str = "resource_metrics_summary",
                              operation_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查询指定时间范围内的历史指标数据

        Args:
            start_time: 查询开始时间
            end_time: 查询结束时间
            table: 要查询的表 ('resource_metrics_summary' or 'app_metrics_summary')
            operation_name: (仅用于app_metrics_summary) 要筛选的操作名称

        Returns:
            包含查询结果的字典列表
        """
        try:
            if table not in ["resource_metrics_summary", "app_metrics_summary"]:
                raise ValueError("无效的表名")

            # 将新格式的数据转换为旧格式
            if table == "resource_metrics_summary":
                # 查询系统资源指标
                start_timestamp = int(start_time.timestamp())
                end_timestamp = int(end_time.timestamp())

                # 从新表中查询数据
                cpu_data = self.query_metrics(
                    "cpu_usage", start_timestamp, end_timestamp, "system")
                memory_data = self.query_metrics(
                    "memory_usage", start_timestamp, end_timestamp, "system")
                disk_data = self.query_metrics(
                    "disk_usage", start_timestamp, end_timestamp, "system")

                # 如果没有任何数据，返回空列表
                if not cpu_data and not memory_data and not disk_data:
                    logger.info(f"没有找到时间范围内的资源指标数据: {start_time} - {end_time}")
                    return []

                # 合并数据
                result = []
                timestamps = set()

                # 收集所有时间戳
                for item in cpu_data + memory_data + disk_data:
                    timestamps.add(item["timestamp"])

                # 按时间戳组织数据
                for ts in sorted(timestamps):
                    cpu_value = next(
                        (float(item["value"]) for item in cpu_data if item["timestamp"] == ts), 0)
                    memory_value = next(
                        (float(item["value"]) for item in memory_data if item["timestamp"] == ts), 0)
                    disk_value = next(
                        (float(item["value"]) for item in disk_data if item["timestamp"] == ts), 0)

                    result.append({
                        "id": len(result) + 1,
                        "t_stamp": datetime.datetime.fromtimestamp(ts).isoformat(),
                        "cpu": cpu_value,
                        "mem": memory_value,
                        "disk": disk_value
                    })

                return result

            elif table == "app_metrics_summary":
                # 查询应用性能指标
                start_timestamp = int(start_time.timestamp())
                end_timestamp = int(end_time.timestamp())

                # 构建查询条件
                category = "application"

                # 从新表中查询数据
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = """
                SELECT metric_name, metric_value, timestamp, tags
                FROM metrics 
                WHERE category = ? AND timestamp >= ? AND timestamp <= ? AND metric_name LIKE 'operation.%'
                """
                params = [category, start_timestamp, end_timestamp]

                if operation_name:
                    query += " AND metric_name = ?"
                    params.append(f"operation.{operation_name}")

                cursor.execute(query, params)
                rows = cursor.fetchall()

                # 如果没有任何数据，返回空列表
                if not rows:
                    logger.info(f"没有找到时间范围内的应用指标数据: {start_time} - {end_time}")
                    conn.close()
                    return []

                # 处理结果
                result = []
                operation_data = {}

                for row in rows:
                    metric_name = row["metric_name"]
                    op_name = metric_name.replace("operation.", "")
                    timestamp = row["timestamp"]

                    # 安全地转换值
                    try:
                        duration = float(row["metric_value"])
                    except (ValueError, TypeError):
                        duration = 0.0

                    # 解析标签
                    success = True
                    if row["tags"]:
                        try:
                            tags = json.loads(row["tags"])
                            success = tags.get(
                                "success", "true").lower() == "true"
                        except json.JSONDecodeError:
                            pass

                    # 按操作名和小时聚合
                    hour_ts = timestamp - (timestamp % 3600)  # 向下取整到小时
                    key = f"{op_name}:{hour_ts}"

                    if key not in operation_data:
                        operation_data[key] = {
                            "operation": op_name,
                            "t_stamp": datetime.datetime.fromtimestamp(hour_ts).isoformat(),
                            "durations": [],
                            "error_count": 0
                        }

                    operation_data[key]["durations"].append(duration)
                    if not success:
                        operation_data[key]["error_count"] += 1

                # 计算聚合指标
                for i, (key, data) in enumerate(operation_data.items()):
                    durations = data["durations"]
                    if not durations:
                        continue

                    result.append({
                        "id": i + 1,
                        "t_stamp": data["t_stamp"],
                        "operation": data["operation"],
                        "avg_duration": sum(durations) / len(durations),
                        "max_duration": max(durations),
                        "call_count": len(durations),
                        "error_count": data["error_count"]
                    })

                conn.close()
                return result

        except Exception as e:
            logger.error(f"查询历史数据失败: {e}")
            return []
