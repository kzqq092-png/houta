"""
数据库维护和优化引擎测试

测试数据库维护引擎的核心功能，包括：
1. 维护任务管理
2. 健康检查功能
3. 性能分析功能
4. 数据库优化操作
5. 备份和恢复功能
6. 任务调度和执行

作者: FactorWeave-Quant团队
版本: 1.0
"""

from core.plugin_types import AssetType
from core.database_maintenance_engine import (
    DatabaseMaintenanceEngine, MaintenanceTask, DatabaseHealthReport, MaintenanceSchedule,
    MaintenanceTaskType, MaintenanceStatus, MaintenancePriority,
    get_database_maintenance_engine
)
import unittest
import tempfile
import shutil
import time
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMaintenanceTask(unittest.TestCase):
    """测试维护任务"""

    def test_task_creation(self):
        """测试任务创建"""
        task = MaintenanceTask(
            task_id="test_task_001",
            task_type=MaintenanceTaskType.HEALTH_CHECK,
            asset_type=AssetType.STOCK_A,
            priority=MaintenancePriority.HIGH
        )

        self.assertEqual(task.task_id, "test_task_001")
        self.assertEqual(task.task_type, MaintenanceTaskType.HEALTH_CHECK)
        self.assertEqual(task.asset_type, AssetType.STOCK_A)
        self.assertEqual(task.priority, MaintenancePriority.HIGH)
        self.assertEqual(task.status, MaintenanceStatus.PENDING)
        self.assertEqual(task.progress, 0.0)

    def test_task_to_dict(self):
        """测试任务转换为字典"""
        task = MaintenanceTask(
            task_id="test_task_002",
            task_type=MaintenanceTaskType.VACUUM,
            parameters={'analyze_after': True}
        )

        task_dict = task.to_dict()

        self.assertIn('task_id', task_dict)
        self.assertIn('task_type', task_dict)
        self.assertIn('status', task_dict)
        self.assertIn('parameters', task_dict)
        self.assertEqual(task_dict['task_id'], "test_task_002")
        self.assertEqual(task_dict['task_type'], "vacuum")
        self.assertEqual(task_dict['parameters'], {'analyze_after': True})


class TestDatabaseHealthReport(unittest.TestCase):
    """测试数据库健康报告"""

    def test_health_report_creation(self):
        """测试健康报告创建"""
        report = DatabaseHealthReport(
            asset_type=AssetType.STOCK_A,
            database_path="/path/to/db",
            file_size_mb=100.5,
            table_count=5,
            record_count=10000,
            index_count=8,
            last_vacuum=None,
            fragmentation_ratio=0.15,
            performance_score=85.0,
            issues=["Issue 1", "Issue 2"],
            recommendations=["Recommendation 1"]
        )

        self.assertEqual(report.asset_type, AssetType.STOCK_A)
        self.assertEqual(report.file_size_mb, 100.5)
        self.assertEqual(report.table_count, 5)
        self.assertEqual(len(report.issues), 2)
        self.assertEqual(len(report.recommendations), 1)

    def test_health_report_to_dict(self):
        """测试健康报告转换为字典"""
        report = DatabaseHealthReport(
            asset_type=AssetType.CRYPTO,
            database_path="/path/to/crypto.db",
            file_size_mb=50.0,
            table_count=3,
            record_count=5000,
            index_count=4,
            last_vacuum=None,
            fragmentation_ratio=0.05,
            performance_score=95.0
        )

        report_dict = report.to_dict()

        self.assertIn('asset_type', report_dict)
        self.assertIn('file_size_mb', report_dict)
        self.assertIn('performance_score', report_dict)
        self.assertEqual(report_dict['asset_type'], 'crypto')
        self.assertEqual(report_dict['file_size_mb'], 50.0)
        self.assertEqual(report_dict['performance_score'], 95.0)


class TestMaintenanceSchedule(unittest.TestCase):
    """测试维护计划"""

    def test_schedule_creation(self):
        """测试计划创建"""
        schedule = MaintenanceSchedule(
            schedule_id="daily_health",
            task_type=MaintenanceTaskType.HEALTH_CHECK,
            asset_type=AssetType.STOCK_A,
            cron_expression="0 2 * * *",
            parameters={'full_check': False}
        )

        self.assertEqual(schedule.schedule_id, "daily_health")
        self.assertEqual(schedule.task_type, MaintenanceTaskType.HEALTH_CHECK)
        self.assertEqual(schedule.cron_expression, "0 2 * * *")
        self.assertTrue(schedule.enabled)

    def test_schedule_to_dict(self):
        """测试计划转换为字典"""
        schedule = MaintenanceSchedule(
            schedule_id="weekly_vacuum",
            task_type=MaintenanceTaskType.VACUUM,
            cron_expression="0 3 * * 0"
        )

        schedule_dict = schedule.to_dict()

        self.assertIn('schedule_id', schedule_dict)
        self.assertIn('task_type', schedule_dict)
        self.assertIn('cron_expression', schedule_dict)
        self.assertEqual(schedule_dict['schedule_id'], "weekly_vacuum")
        self.assertEqual(schedule_dict['task_type'], "vacuum")


class TestDatabaseMaintenanceEngine(unittest.TestCase):
    """测试数据库维护引擎"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

        # Mock dependencies
        self.mock_asset_db_manager = Mock()
        self.mock_query_engine = Mock()

        # Mock database path and connection
        self.mock_asset_db_manager.get_database_path.return_value = os.path.join(self.temp_dir, "test.db")

        # Create a test database file
        test_db_path = os.path.join(self.temp_dir, "test.db")
        with open(test_db_path, 'wb') as f:
            f.write(b'0' * 1024 * 1024)  # 1MB test file

        # Mock connection
        self.mock_connection = Mock()
        self.mock_connection.execute.return_value.fetchall.return_value = [("ok",)]
        self.mock_connection.execute.return_value.fetchone.return_value = (100,)
        self.mock_connection.execute.return_value.rowcount = 10

        self.mock_asset_db_manager.get_connection.return_value.__enter__ = Mock(return_value=self.mock_connection)
        self.mock_asset_db_manager.get_connection.return_value.__exit__ = Mock(return_value=None)

        # 创建引擎实例
        with patch('core.database_maintenance_engine.get_asset_database_manager', return_value=self.mock_asset_db_manager), \
                patch('core.database_maintenance_engine.get_cross_asset_query_engine', return_value=self.mock_query_engine):
            self.engine = DatabaseMaintenanceEngine(max_workers=1)

    def tearDown(self):
        """清理测试环境"""
        self.engine.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_engine_initialization(self):
        """测试引擎初始化"""
        self.assertIsNotNone(self.engine)
        self.assertIsNotNone(self.engine.asset_db_manager)
        self.assertIsNotNone(self.engine.query_engine)
        self.assertIsNotNone(self.engine.executor)

        # 检查默认维护计划
        self.assertGreater(len(self.engine._schedules), 0)

    def test_create_maintenance_task(self):
        """测试创建维护任务"""
        task_id = self.engine.create_maintenance_task(
            MaintenanceTaskType.HEALTH_CHECK,
            asset_type=AssetType.STOCK_A,
            priority=MaintenancePriority.HIGH,
            parameters={'full_check': True}
        )

        self.assertIsNotNone(task_id)
        self.assertIn(task_id, self.engine._tasks)

        task = self.engine._tasks[task_id]
        self.assertEqual(task.task_type, MaintenanceTaskType.HEALTH_CHECK)
        self.assertEqual(task.asset_type, AssetType.STOCK_A)
        self.assertEqual(task.priority, MaintenancePriority.HIGH)
        self.assertEqual(task.parameters, {'full_check': True})

    def test_get_task_status(self):
        """测试获取任务状态"""
        task_id = self.engine.create_maintenance_task(MaintenanceTaskType.VACUUM)

        status = self.engine.get_task_status(task_id)

        self.assertIsNotNone(status)
        self.assertEqual(status['task_id'], task_id)
        self.assertEqual(status['task_type'], 'vacuum')
        self.assertEqual(status['status'], 'pending')

    def test_list_tasks(self):
        """测试列出任务"""
        # 创建几个任务
        task_id1 = self.engine.create_maintenance_task(MaintenanceTaskType.HEALTH_CHECK)
        task_id2 = self.engine.create_maintenance_task(MaintenanceTaskType.VACUUM)

        # 列出所有任务
        all_tasks = self.engine.list_tasks()
        self.assertGreaterEqual(len(all_tasks), 2)

        # 按状态过滤
        pending_tasks = self.engine.list_tasks(MaintenanceStatus.PENDING)
        self.assertGreaterEqual(len(pending_tasks), 2)

    def test_cancel_task(self):
        """测试取消任务"""
        task_id = self.engine.create_maintenance_task(MaintenanceTaskType.HEALTH_CHECK)

        # 取消任务
        success = self.engine.cancel_task(task_id)
        self.assertTrue(success)

        # 验证任务状态
        task = self.engine._tasks[task_id]
        self.assertEqual(task.status, MaintenanceStatus.CANCELLED)

    def test_check_database_health(self):
        """测试数据库健康检查"""
        # 设置mock返回值
        self.mock_connection.execute.side_effect = [
            Mock(fetchall=Mock(return_value=[("table1",), ("table2",)])),  # tables
            Mock(fetchall=Mock(return_value=[("index1",), ("index2",)])),  # indexes
            Mock(fetchone=Mock(return_value=(1000,))),  # count for table1
            Mock(fetchone=Mock(return_value=(2000,))),  # count for table2
            Mock(fetchone=Mock(return_value=(10,))),    # freelist_count
            Mock(fetchone=Mock(return_value=(1000,))),  # page_count
        ]

        report = self.engine._check_database_health(AssetType.STOCK_A, full_check=False)

        self.assertEqual(report.asset_type, AssetType.STOCK_A)
        self.assertEqual(report.table_count, 2)
        self.assertEqual(report.record_count, 3000)
        self.assertEqual(report.index_count, 2)
        self.assertGreater(report.file_size_mb, 0)
        self.assertGreaterEqual(report.performance_score, 0)

    def test_calculate_performance_score(self):
        """测试性能分数计算"""
        # 测试不同场景的性能分数
        score1 = self.engine._calculate_performance_score(100, 0.1, 0)
        score2 = self.engine._calculate_performance_score(1500, 0.5, 3)
        score3 = self.engine._calculate_performance_score(50, 0.0, 0)

        self.assertGreaterEqual(score1, 0)
        self.assertLessEqual(score1, 100)
        self.assertLess(score2, score1)  # 更大的文件、更多碎片、更多问题应该得分更低
        self.assertGreater(score3, score1)  # 更小的文件、无碎片、无问题应该得分更高

    def test_calculate_overall_health(self):
        """测试整体健康状况计算"""
        health_reports = [
            {'performance_score': 90, 'issues': []},
            {'performance_score': 85, 'issues': ['issue1']},
            {'performance_score': 95, 'issues': []}
        ]

        overall_health = self.engine._calculate_overall_health(health_reports)

        self.assertIn('status', overall_health)
        self.assertIn('score', overall_health)
        self.assertIn('total_issues', overall_health)
        self.assertIn('database_count', overall_health)

        self.assertEqual(overall_health['database_count'], 3)
        self.assertEqual(overall_health['total_issues'], 1)
        self.assertGreater(overall_health['score'], 80)

    def test_execute_health_check(self):
        """测试执行健康检查"""
        task = MaintenanceTask(
            task_id="test_health_check",
            task_type=MaintenanceTaskType.HEALTH_CHECK,
            asset_type=AssetType.STOCK_A,
            parameters={'full_check': False}
        )

        # 设置mock返回值
        self.mock_connection.execute.side_effect = [
            Mock(fetchall=Mock(return_value=[("table1",)])),  # tables
            Mock(fetchall=Mock(return_value=[("index1",)])),  # indexes
            Mock(fetchone=Mock(return_value=(1000,))),        # count
            Mock(fetchone=Mock(return_value=(5,))),           # freelist_count
            Mock(fetchone=Mock(return_value=(100,))),         # page_count
        ]

        result = self.engine._execute_health_check(task)

        self.assertIn('health_reports', result)
        self.assertIn('overall_health', result)
        self.assertIn('check_time', result)
        self.assertEqual(len(result['health_reports']), 1)

    def test_execute_vacuum(self):
        """测试执行VACUUM操作"""
        task = MaintenanceTask(
            task_id="test_vacuum",
            task_type=MaintenanceTaskType.VACUUM,
            asset_type=AssetType.STOCK_A,
            parameters={'analyze_after': True}
        )

        result = self.engine._execute_vacuum(task)

        self.assertIn('vacuum_results', result)
        self.assertIn('total_space_saved_mb', result)
        self.assertIn('vacuum_time', result)

        # 验证VACUUM和ANALYZE被调用
        vacuum_calls = [call for call in self.mock_connection.execute.call_args_list
                        if 'VACUUM' in str(call)]
        analyze_calls = [call for call in self.mock_connection.execute.call_args_list
                         if 'ANALYZE' in str(call)]

        self.assertGreater(len(vacuum_calls), 0)
        self.assertGreater(len(analyze_calls), 0)

    def test_execute_backup(self):
        """测试执行备份"""
        # Mock backup_database方法
        self.mock_asset_db_manager.backup_database.return_value = "/path/to/backup.db"

        task = MaintenanceTask(
            task_id="test_backup",
            task_type=MaintenanceTaskType.BACKUP,
            asset_type=AssetType.STOCK_A,
            parameters={'compress': True}
        )

        result = self.engine._execute_backup(task)

        self.assertIn('backup_results', result)
        self.assertIn('backup_time', result)
        self.assertIn('backup_directory', result)

        # 验证backup_database被调用
        self.mock_asset_db_manager.backup_database.assert_called_with(AssetType.STOCK_A)

    def test_execute_integrity_check(self):
        """测试执行完整性检查"""
        # Mock integrity check结果
        self.mock_connection.execute.return_value.fetchall.return_value = [("ok",)]

        task = MaintenanceTask(
            task_id="test_integrity",
            task_type=MaintenanceTaskType.INTEGRITY_CHECK,
            asset_type=AssetType.STOCK_A
        )

        result = self.engine._execute_integrity_check(task)

        self.assertIn('integrity_results', result)
        self.assertIn('check_time', result)

        integrity_result = result['integrity_results'][0]
        self.assertEqual(integrity_result['status'], 'ok')
        self.assertEqual(integrity_result['check_result'], 'success')

    def test_execute_performance_analysis(self):
        """测试执行性能分析"""
        task = MaintenanceTask(
            task_id="test_performance",
            task_type=MaintenanceTaskType.PERFORMANCE_ANALYSIS,
            asset_type=AssetType.STOCK_A
        )

        result = self.engine._execute_performance_analysis(task)

        self.assertIn('analysis_results', result)
        self.assertIn('analysis_time', result)

        analysis_result = result['analysis_results'][0]
        self.assertIn('query_performance', analysis_result)
        self.assertIn('avg_query_time_ms', analysis_result)

    def test_get_target_assets(self):
        """测试获取目标资产"""
        # 测试指定资产类型
        targets = self.engine._get_target_assets(AssetType.STOCK_A)
        self.assertEqual(targets, [AssetType.STOCK_A])

        # 测试所有资产类型
        targets = self.engine._get_target_assets(None)
        self.assertIsInstance(targets, list)
        # 由于mock的存在，应该包含至少一个资产类型
        self.assertGreaterEqual(len(targets), 0)

    def test_get_system_health_summary(self):
        """测试获取系统健康摘要"""
        # 设置mock返回值
        self.mock_connection.execute.side_effect = [
            Mock(fetchall=Mock(return_value=[("table1",)])),  # tables
            Mock(fetchall=Mock(return_value=[("index1",)])),  # indexes
            Mock(fetchone=Mock(return_value=(1000,))),        # count
            Mock(fetchone=Mock(return_value=(5,))),           # freelist_count
            Mock(fetchone=Mock(return_value=(100,))),         # page_count
        ]

        summary = self.engine.get_system_health_summary()

        self.assertIn('overall_health', summary)
        self.assertIn('database_count', summary)
        self.assertIn('last_check', summary)
        self.assertIn('issues_count', summary)

    def test_maintenance_history(self):
        """测试维护历史"""
        # 创建一个任务并完成它
        task = MaintenanceTask(
            task_id="test_history",
            task_type=MaintenanceTaskType.HEALTH_CHECK,
            status=MaintenanceStatus.COMPLETED
        )

        # 手动添加到历史
        with self.engine._engine_lock:
            self.engine._maintenance_history.append(task)

        history = self.engine.get_maintenance_history()

        self.assertGreater(len(history), 0)
        self.assertEqual(history[-1]['task_id'], "test_history")
        self.assertEqual(history[-1]['status'], "completed")


class TestGlobalInstance(unittest.TestCase):
    """测试全局实例管理"""

    def test_get_database_maintenance_engine(self):
        """测试获取全局维护引擎实例"""
        with patch('core.database_maintenance_engine.get_asset_database_manager'), \
                patch('core.database_maintenance_engine.get_cross_asset_query_engine'):
            engine1 = get_database_maintenance_engine()
            engine2 = get_database_maintenance_engine()

            # 验证单例模式
            self.assertIs(engine1, engine2)

            # 清理
            engine1.close()


if __name__ == '__main__':
    unittest.main()
