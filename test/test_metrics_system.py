# New file content
import unittest
import asyncio
from unittest.mock import MagicMock, patch, call
import time
import os
import sqlite3
import datetime
import threading
from typing import List

# This is a new test file for the recently implemented metrics and monitoring system.
# It will contain unit tests for the services and repository in core/metrics.

# Assuming core.metrics.repository and core.metrics.events are in the python path
from core.metrics.repository import MetricsRepository
from core.metrics.events import SystemResourceUpdated, ApplicationMetricRecorded


class TestMetricsRepository(unittest.TestCase):
    """针对 MetricsRepository 的单元测试"""

    @classmethod
    def setUpClass(cls):
        """在所有测试开始前执行一次，创建一个持久的内存数据库连接。"""
        # 使用 file:memdb1?mode=memory&cache=shared URI 来创建一个可跨线程共享的内存数据库
        # 这是 pysqlite 的一个特性，可以让我们在多个连接之间共享一个内存数据库
        cls.db_uri = "file:memdb1?mode=memory&cache=shared"
        # 我们需要保持一个连接打开，以防止内存数据库被销毁
        cls.conn = sqlite3.connect(
            cls.db_uri, uri=True, check_same_thread=False)
        # 初始化一次 schema
        repo = MetricsRepository(db_path=cls.db_uri)
        # 清理一下，以防之前的测试遗留了表
        cursor = cls.conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS resource_metrics_summary")
        cursor.execute("DROP TABLE IF EXISTS app_metrics_summary")
        cls.conn.commit()
        # 重新初始化
        repo._initialize_schema()

    @classmethod
    def tearDownClass(cls):
        """在所有测试结束后执行一次，关闭连接。"""
        cls.conn.close()

    def setUp(self):
        """在每个测试前执行。"""
        # 现在，每个测试都使用同一个共享的内存数据库
        self.repo = MetricsRepository(db_path=self.db_uri)
        # 我们在这里也需要一个锁，用于多线程测试
        self.lock = threading.RLock()
        # 清理数据，确保测试之间是独立的
        with self.repo._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM resource_metrics_summary")
            cursor.execute("DELETE FROM app_metrics_summary")
            conn.commit()

    def tearDown(self):
        """在每个测试后执行，清理资源。"""
        self.repo = None

    def test_initialization_creates_tables(self):
        """测试初始化时是否成功创建了所需的表。"""
        with self.repo._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='resource_metrics_summary'")
            self.assertIsNotNone(
                cursor.fetchone(), "resource_metrics_summary 表未被创建")
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='app_metrics_summary'")
            self.assertIsNotNone(
                cursor.fetchone(), "app_metrics_summary 表未被创建")

    def test_save_and_query_resource_metrics(self):
        """测试保存和查询系统资源指标。"""
        now = datetime.datetime.now()
        resource_data = [
            (now - datetime.timedelta(seconds=10), 50.5, 60.1, 70.3),
            (now, 55.2, 62.5, 71.0)
        ]
        self.repo.save_aggregated_metrics_batch(
            resource_metrics=resource_data, app_metrics=[])

        results = self.repo.query_historical_data(
            start_time=now - datetime.timedelta(minutes=1),
            end_time=now + datetime.timedelta(minutes=1),
            table="resource_metrics_summary"
        )
        self.assertEqual(len(results), 2)
        self.assertAlmostEqual(results[0]['cpu'], 50.5)
        self.assertAlmostEqual(results[1]['mem'], 62.5)

    def test_save_and_query_app_metrics(self):
        """测试保存和查询应用性能指标。"""
        now = datetime.datetime.now()
        app_data = [
            (now - datetime.timedelta(seconds=5), 'test_op_1', 0.1, 0.2, 10, 1),
            (now, 'test_op_2', 0.5, 0.8, 20, 2)
        ]
        self.repo.save_aggregated_metrics_batch(
            resource_metrics=[], app_metrics=app_data)

        # 测试查询所有操作
        all_results = self.repo.query_historical_data(
            start_time=now - datetime.timedelta(minutes=1),
            end_time=now + datetime.timedelta(minutes=1),
            table="app_metrics_summary"
        )
        self.assertEqual(len(all_results), 2)

        # 测试按操作名称查询
        op1_results = self.repo.query_historical_data(
            start_time=now - datetime.timedelta(minutes=1),
            end_time=now + datetime.timedelta(minutes=1),
            table="app_metrics_summary",
            operation_name="test_op_1"
        )
        self.assertEqual(len(op1_results), 1)
        self.assertEqual(op1_results[0]['operation'], 'test_op_1')
        self.assertEqual(op1_results[0]['call_count'], 10)

    def test_query_time_range(self):
        """测试查询是否正确地遵循了时间范围。"""
        now = datetime.datetime.now()
        resource_data = [
            (now - datetime.timedelta(minutes=5), 10.0, 10.0, 10.0),  # 在范围之外
            (now, 20.0, 20.0, 20.0),                               # 在范围之内
            (now + datetime.timedelta(minutes=5), 30.0, 30.0, 30.0),  # 在范围之外
        ]
        self.repo.save_aggregated_metrics_batch(
            resource_metrics=resource_data, app_metrics=[])

        results = self.repo.query_historical_data(
            start_time=now - datetime.timedelta(minutes=1),
            end_time=now + datetime.timedelta(minutes=1),
            table="resource_metrics_summary"
        )
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0]['cpu'], 20.0)

    def test_empty_batch_save(self):
        """测试保存空数据批次时不会引发错误。"""
        try:
            self.repo.save_aggregated_metrics_batch(
                resource_metrics=[], app_metrics=[])
        except Exception as e:
            self.fail(f"保存空批次时引发了异常: {e}")

    def test_concurrency_safety(self):
        """通过多线程写入来简单地测试并发安全性。"""
        now = datetime.datetime.now()
        errors: List[Exception] = []

        def writer_task(data_chunk: List[tuple]):
            try:
                # 在多线程测试中，每个线程都应该获取一个新的 repo 实例
                # 但它们都指向同一个共享的内存数据库 URI
                thread_repo = MetricsRepository(db_path=self.db_uri)
                thread_repo.save_aggregated_metrics_batch(
                    resource_metrics=data_chunk, app_metrics=[])
            except Exception as e:
                errors.append(e)

        threads: List[threading.Thread] = []
        total_records = 100
        for i in range(total_records):
            # 每个线程写入一条记录
            record = [(now + datetime.timedelta(microseconds=i), i, i, i)]
            thread = threading.Thread(target=writer_task, args=(record,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(len(errors), 0, f"并发写入时发生了错误: {errors}")

        # 验证所有数据都已写入
        results = self.repo.query_historical_data(
            start_time=now - datetime.timedelta(seconds=1),
            end_time=now + datetime.timedelta(seconds=1),
            table="resource_metrics_summary"
        )
        self.assertEqual(len(results), total_records)


if __name__ == '__main__':
    unittest.main(verbosity=2)
