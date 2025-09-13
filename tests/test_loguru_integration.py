"""
Loguru集成测试

验证纯Loguru系统在测试环境中的正确工作。
"""

import pytest
import sys
from pathlib import Path
from loguru import logger

# 添加项目根径到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestLoguruIntegration:
    """测试Loguru集成"""

    def test_basic_logging(self, test_logger):
        """测试基本的日志功能"""
        test_logger.info("这是一条测试日志消息")
        test_logger.debug("这是一条调试消息")
        test_logger.warning("这是一条警告消息")

        # 验证日志功能正常
        assert True  # 如果没有异常，说明日志功能正常

    def test_structured_logging(self, test_context):
        """测试结构化日志"""
        test_context.bind(
            test_id="test_001",
            component="loguru_integration",
            action="structured_log_test"
        ).info("结构化日志测试")

        assert True

    def test_exception_logging(self, test_logger):
        """测试异常日志"""
        try:
            raise ValueError("这是一个测试异常")
        except ValueError:
            test_logger.exception("捕获到测试异常")

        assert True

    def test_log_capture(self, capture_logs, test_context):
        """测试日志捕获功能"""
        test_context.info("这是一条可捕获的日志消息")
        test_context.error("这是一条错误日志")

        logs = capture_logs()
        assert len(logs) >= 2

    def test_performance_logging(self, test_logger):
        """测试性能日志"""
        test_logger.bind(performance=True, operation="test_operation").info(
            "性能测试操作完成"
        )

        assert True

    def test_loguru_with_pytest_fixtures(self, loguru_helper, capture_logs, test_context):
        """测试Loguru与pytest fixture的集成"""
        test_context.info("集成测试消息")
        test_context.warning("集成测试警告")

        logs = capture_logs()

        # 使用辅助工具验证日志
        loguru_helper.assert_log_contains(logs, "集成测试消息", "INFO")
        loguru_helper.assert_log_contains(logs, "集成测试警告", "WARNING")


class TestLoguruConfiguration:
    """测试Loguru配置"""

    def test_logger_available(self):
        """测试logger是否可用"""
        assert logger is not None
        logger.info("Logger可用性测试")

    def test_log_levels(self, test_logger):
        """测试所有日志级别"""
        test_logger.trace("TRACE级别日志")
        test_logger.debug("DEBUG级别日志")
        test_logger.info("INFO级别日志")
        test_logger.success("SUCCESS级别日志")
        test_logger.warning("WARNING级别日志")
        test_logger.error("ERROR级别日志")
        test_logger.critical("CRITICAL级别日志")

        assert True

    def test_context_binding(self, test_logger):
        """测试上下文绑定"""
        context_logger = test_logger.bind(
            module="test_module",
            function="test_function",
            user_id="test_user"
        )

        context_logger.info("带上下文的日志消息")
        assert True


class TestErrorHandling:
    """测试错误处理集成"""

    def test_exception_with_context(self, test_context):
        """测试带上下文的异常处理"""
        try:
            result = 10 / 0
        except ZeroDivisionError as e:
            test_context.bind(
                error_type="ZeroDivisionError",
                operation="division",
                operands=[10, 0]
            ).exception("除零错误测试")

        assert True

    def test_error_recovery_logging(self, test_context):
        """测试错误恢复日志"""
        test_context.bind(recovery=True, action="retry", attempt=1).info(
            "第一次重试操作"
        )

        test_context.bind(recovery=True, action="fallback", success=True).success(
            "回退操作成功"
        )

        assert True


class TestAsyncLogging:
    """测试异步日志功能"""

    @pytest.mark.asyncio
    async def test_async_logging(self, test_logger):
        """测试异步环境下的日志"""
        import asyncio

        test_logger.info("异步测试开始")

        async def async_operation():
            test_logger.debug("执行异步操作")
            await asyncio.sleep(0.01)
            test_logger.success("异步操作完成")

        await async_operation()
        test_logger.info("异步测试结束")

        assert True

# 用于手动运行的测试函数


def run_manual_test():
    """手动运行测试"""
    logger.info(" 开始手动Loguru测试")

    # 基本日志测试
    logger.info("基本日志消息")
    logger.bind(component="manual_test").warning("带组件标记的警告")

    # 异常测试
    try:
        raise RuntimeError("手动测试异常")
    except RuntimeError:
        logger.exception("捕获的手动测试异常")

    logger.success(" 手动测试完成")


if __name__ == "__main__":
    run_manual_test()
