"""
pytest配置文件 - 配置纯Loguru测试环境

提供测试专用的日志配置和fixture。
"""

import pytest
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """pytest配置钩子 - 设置测试专用的Loguru配置"""
    # 移除默认的Loguru处理器
    logger.remove()

    # 为测试设置控制台日志
    logger.add(
        sys.stdout,
        level="DEBUG",
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>TEST</cyan> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        catch=True
    )

    # 为测试设置文件日志
    test_log_path = Path("logs") / "tests_{time:YYYY-MM-DD}.log"
    test_log_path.parent.mkdir(exist_ok=True)

    logger.add(
        test_log_path,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | TEST | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=False,  # 测试环境使用同步日志确保即时性
        catch=True
    )

    logger.info(" 测试环境Loguru配置已完成")


def pytest_unconfigure(config):
    """pytest清理钩子"""
    logger.info(" 测试环境清理完成")


@pytest.fixture(scope="session")
def test_logger():
    """提供测试专用的logger fixture"""
    return logger.bind(test=True)


@pytest.fixture(scope="function")
def capture_logs():
    """捕获日志输出的fixture"""
    logs = []

    def log_sink(message):
        logs.append(message.record)

    # 添加日志捕获sink
    handler_id = logger.add(log_sink, level="DEBUG", filter=lambda record: "test_capture" in record["extra"])

    yield lambda: logs

    # 清理
    logger.remove(handler_id)


@pytest.fixture(scope="function")
def test_context():
    """提供测试上下文的fixture"""
    return logger.bind(test_capture=True)


class LoguruTestHelper:
    """Loguru测试辅助类"""

    @staticmethod
    def assert_log_contains(logs, message: str, level: str = None):
        """断言日志包含特定消息"""
        for log in logs:
            if message in log["message"]:
                if level is None or log["level"].name == level:
                    return True
        raise AssertionError(f"日志中未找到消息: {message}")

    @staticmethod
    def assert_no_errors(logs):
        """断言日志中没有错误"""
        error_logs = [log for log in logs if log["level"].name in ["ERROR", "CRITICAL"]]
        if error_logs:
            error_messages = [log["message"] for log in error_logs]
            raise AssertionError(f"发现错误日志: {error_messages}")


@pytest.fixture
def loguru_helper():
    """提供Loguru测试辅助工具"""
    return LoguruTestHelper()

# 测试环境专用的日志标记


def pytest_runtest_setup(item):
    """测试设置钩子 - 为每个测试添加标记"""
    test_name = item.nodeid
    logger.bind(test_name=test_name).info(f" 开始测试: {test_name}")


def pytest_runtest_teardown(item):
    """测试清理钩子 - 测试完成后的清理"""
    test_name = item.nodeid
    logger.bind(test_name=test_name).info(f" 测试完成: {test_name}")

# 处理测试异常


def pytest_runtest_call(item):
    """测试调用钩子 - 捕获测试中的异常"""
    try:
        yield
    except Exception as e:
        test_name = item.nodeid
        logger.bind(test_name=test_name, test_error=True).exception(
            f" 测试失败: {test_name} - {e}"
        )
