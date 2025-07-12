# test/test_integration_monitoring.py
import unittest
import time
import datetime
from unittest.mock import patch, MagicMock

# 假设的模块路径，需要根据项目结构进行调整
from core.metrics.repository import MetricsRepository
from core.metrics.resource_service import SystemResourceService
from core.metrics.app_metrics_service import ApplicationMetricsService
from core.metrics.aggregation_service import MetricsAggregationService
from core.events.event_bus import EventBus


class TestMonitoringIntegration(unittest.TestCase):
    """监控系统集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.db_uri = "file:memdb_integration?mode=memory&cache=shared"
        # 确保数据库是干净的
        self.repo = MetricsRepository(db_path=self.db_uri)
        with self.repo._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS resource_metrics_summary")
            cursor.execute("DROP TABLE IF EXISTS app_metrics_summary")

        self.event_bus = EventBus()
        self.repo = MetricsRepository(db_path=self.db_uri)  # 重新初始化以创建表

        # 初始化服务
        self.aggregation_service = MetricsAggregationService(
            self.event_bus, self.repo, flush_interval=0.5)
        self.resource_service = SystemResourceService(
            self.event_bus, interval=0.1)
        self.app_service = ApplicationMetricsService(self.event_bus)

    def tearDown(self):
        """清理测试环境"""
        self.resource_service.dispose()
        self.aggregation_service.dispose()

    def test_full_monitoring_flow(self):
        """测试从数据收集到存储的完整流程"""
        # 启动服务
        self.resource_service.start()
        self.aggregation_service.start()

        # 使用 @measure_time 装饰器运行一些模拟函数
        @self.app_service.measure_time("test_operation_success")
        def sample_task_success():
            time.sleep(0.1)
            return "Success"

        @self.app_service.measure_time("test_operation_fail")
        def sample_task_fail():
            time.sleep(0.2)
            raise ValueError("Task Failed")

        # 执行任务
        sample_task_success()
        try:
            sample_task_fail()
        except ValueError:
            pass  # 预期中的失败

        # 等待足够长的时间，让服务收集、发布和聚合数据
        # 至少等待 resource_service 运行几次，以及 aggregation_service 刷新一次
        time.sleep(1)

        # 停止服务
        self.resource_service.dispose()
        self.aggregation_service.dispose()

        # 验证数据是否已写入数据库
        now = datetime.datetime.now()

        # 验证资源指标
        resource_metrics = self.repo.query_historical_data(
            start_time=now - datetime.timedelta(minutes=1),
            end_time=now,
            table="resource_metrics_summary"
        )
        self.assertGreater(len(resource_metrics), 0, "应记录了系统资源指标")
        self.assertIn('cpu', resource_metrics[0])

        # 验证应用指标
        app_metrics = self.repo.query_historical_data(
            start_time=now - datetime.timedelta(minutes=1),
            end_time=now,
            table="app_metrics_summary"
        )
        self.assertEqual(len(app_metrics), 2, "应记录了两个应用操作的指标")

        ops_data = {m['operation']: m for m in app_metrics}
        self.assertIn("test_operation_success", ops_data)
        self.assertIn("test_operation_fail", ops_data)

        self.assertEqual(ops_data["test_operation_success"]['call_count'], 1)
        self.assertEqual(ops_data["test_operation_success"]['error_count'], 0)
        self.assertAlmostEqual(
            ops_data["test_operation_success"]['avg_duration'], 0.1, delta=0.05)

        self.assertEqual(ops_data["test_operation_fail"]['call_count'], 1)
        self.assertEqual(ops_data["test_operation_fail"]['error_count'], 1)
        self.assertAlmostEqual(
            ops_data["test_operation_fail"]['avg_duration'], 0.2, delta=0.05)


if __name__ == '__main__':
    unittest.main(verbosity=2)
