#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
pytest 配置文件

提供全局的测试配置、fixtures和工具函数。
"""

import pytest
import tempfile
import os
import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.WARNING,  # 测试时只显示警告和错误
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 禁用一些第三方库的日志
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)


# ============================================================================
# 全局配置
# ============================================================================

def pytest_configure(config):
    """pytest配置钩子"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers", "unit: 标记为单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "performance: 标记为性能测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记为慢速测试"
    )
    config.addinivalue_line(
        "markers", "network: 标记为需要网络连接的测试"
    )
    config.addinivalue_line(
        "markers", "database: 标记为需要数据库的测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 为没有标记的测试添加默认标记
    for item in items:
        if not any(item.iter_markers()):
            if "test_performance" in item.nodeid or "benchmark" in item.nodeid:
                item.add_marker(pytest.mark.performance)
            elif "test_integration" in item.nodeid or "integration" in item.nodeid:
                item.add_marker(pytest.mark.integration)
            else:
                item.add_marker(pytest.mark.unit)


# ============================================================================
# 基础 Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def temp_dir():
    """临时目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_db():
    """临时数据库文件"""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    yield temp_db.name
    try:
        os.unlink(temp_db.name)
    except:
        pass


@pytest.fixture
def mock_datetime():
    """Mock datetime"""
    with patch('core.importdata.intelligent_config_manager.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield mock_dt


# ============================================================================
# 数据 Fixtures
# ============================================================================

@pytest.fixture
def sample_stock_data():
    """示例股票数据"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': '000001',
        'open': np.random.normal(100, 5, 100),
        'high': np.random.normal(105, 5, 100),
        'low': np.random.normal(95, 5, 100),
        'close': np.random.normal(100, 5, 100),
        'volume': np.random.randint(100000, 1000000, 100),
        'amount': np.random.uniform(1000000, 10000000, 100)
    })
    
    # 确保高低价格的逻辑关系
    data['high'] = np.maximum(data['high'], data[['open', 'close']].max(axis=1))
    data['low'] = np.minimum(data['low'], data[['open', 'close']].min(axis=1))
    
    return data


@pytest.fixture
def anomalous_stock_data():
    """包含异常的股票数据"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': '000001',
        'open': np.random.normal(100, 5, 100),
        'high': np.random.normal(105, 5, 100),
        'low': np.random.normal(95, 5, 100),
        'close': np.random.normal(100, 5, 100),
        'volume': np.random.randint(100000, 1000000, 100)
    })
    
    # 注入异常数据
    data.loc[10:15, 'close'] = np.nan  # 缺失数据
    data.loc[20, 'high'] = 500.0  # 异常高价
    data.loc[25, 'volume'] = 0  # 零交易量
    data.loc[30:32] = data.loc[29]  # 重复数据
    data.loc[40, 'low'] = -10.0  # 负价格
    
    return data


@pytest.fixture
def large_dataset():
    """大型数据集"""
    np.random.seed(42)
    size = 10000
    
    data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=size, freq='min'),
        'symbol': np.random.choice(['000001', '000002', '000300'], size),
        'price': np.concatenate([
            np.random.normal(100, 10, int(size * 0.9)),  # 90% 正常数据
            np.random.normal(200, 20, int(size * 0.05)),  # 5% 异常值
            [np.nan] * int(size * 0.05)  # 5% 缺失数据
        ]),
        'volume': np.random.randint(1000, 100000, size)
    })
    
    return data


# ============================================================================
# 配置 Fixtures
# ============================================================================

@pytest.fixture
def sample_import_config():
    """示例导入配置"""
    from core.importdata.intelligent_config_manager import ImportTaskConfig, DataFrequency, ImportMode
    
    return ImportTaskConfig(
        task_id="test_task_001",
        name="测试任务",
        data_source="tongdaxin",
        asset_type="stock",
        data_type="kline",
        symbols=["000001", "000002"],
        frequency=DataFrequency.DAILY,
        mode=ImportMode.BATCH,
        max_workers=4,
        batch_size=1000
    )


@pytest.fixture
def multiple_import_configs():
    """多个导入配置"""
    from core.importdata.intelligent_config_manager import ImportTaskConfig, DataFrequency, ImportMode
    
    configs = []
    for i in range(5):
        config = ImportTaskConfig(
            task_id=f"test_task_{i:03d}",
            name=f"测试任务{i}",
            data_source="tongdaxin" if i % 2 == 0 else "akshare",
            asset_type="stock",
            data_type="kline",
            symbols=[f"{j:06d}" for j in range(i, i + 3)],
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH,
            max_workers=2 + i,
            batch_size=500 + i * 100
        )
        configs.append(config)
    
    return configs


# ============================================================================
# 组件 Fixtures
# ============================================================================

@pytest.fixture
def config_manager(temp_db):
    """配置管理器"""
    from core.importdata.intelligent_config_manager import IntelligentConfigManager
    return IntelligentConfigManager(temp_db)


@pytest.fixture
def anomaly_detector(temp_db):
    """异常检测器"""
    from core.ai.data_anomaly_detector import DataAnomalyDetector, AnomalyDetectionConfig
    
    config = AnomalyDetectionConfig(
        auto_repair_enabled=True,
        enable_outlier_detection=True,
        enable_missing_data_detection=True,
        enable_duplicate_detection=True
    )
    
    return DataAnomalyDetector(config, temp_db)


@pytest.fixture
def data_integration():
    """数据集成组件"""
    from core.ui_integration.smart_data_integration import SmartDataIntegration, UIIntegrationConfig
    
    config = UIIntegrationConfig(
        enable_caching=True,
        cache_expiry_seconds=300,
        enable_predictive_loading=True,
        enable_adaptive_caching=True
    )
    
    with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor'):
        integration = SmartDataIntegration(config)
    
    yield integration
    
    try:
        integration.close()
    except:
        pass


@pytest.fixture
def recommendation_engine(temp_db):
    """推荐引擎"""
    from core.ai.config_recommendation_engine import ConfigRecommendationEngine
    
    with patch('core.ai.config_recommendation_engine.AIPredictionService'):
        return ConfigRecommendationEngine(temp_db)


@pytest.fixture
def impact_analyzer(temp_db):
    """影响分析器"""
    from core.ai.config_impact_analyzer import ConfigImpactAnalyzer
    
    with patch('core.ai.config_impact_analyzer.AIPredictionService'):
        return ConfigImpactAnalyzer(temp_db)


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_requests():
    """Mock requests"""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'symbol': '000001', 'price': 10.0, 'volume': 1000},
                {'symbol': '000002', 'price': 20.0, 'volume': 2000}
            ]
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_ai_service():
    """Mock AI预测服务"""
    with patch('core.services.ai_prediction_service.AIPredictionService') as mock_service:
        mock_instance = Mock()
        mock_instance.predict.return_value = {
            'execution_time': 60.0,
            'success_rate': 0.95,
            'throughput': 1000.0,
            'confidence': 0.8,
            'recommended_params': {'max_workers': 6, 'batch_size': 1500}
        }
        mock_service.return_value = mock_instance
        yield mock_service


# ============================================================================
# 性能测试 Fixtures
# ============================================================================

@pytest.fixture
def benchmark_config():
    """性能测试配置"""
    return {
        'min_rounds': 3,
        'max_time': 10.0,
        'min_time': 0.1,
        'timer': 'time.perf_counter'
    }


# ============================================================================
# 工具函数
# ============================================================================

def assert_dataframe_equal(df1, df2, check_dtype=True, check_index=True):
    """断言两个DataFrame相等"""
    try:
        pd.testing.assert_frame_equal(df1, df2, check_dtype=check_dtype, check_index=check_index)
    except AssertionError as e:
        pytest.fail(f"DataFrames are not equal: {e}")


def assert_dict_contains(actual, expected):
    """断言字典包含期望的键值对"""
    for key, value in expected.items():
        assert key in actual, f"Key '{key}' not found in actual dict"
        assert actual[key] == value, f"Value mismatch for key '{key}': expected {value}, got {actual[key]}"


def create_test_config(task_id, **kwargs):
    """创建测试配置的工具函数"""
    from core.importdata.intelligent_config_manager import ImportTaskConfig, DataFrequency, ImportMode
    
    defaults = {
        'name': f'测试任务_{task_id}',
        'data_source': 'tongdaxin',
        'asset_type': 'stock',
        'data_type': 'kline',
        'symbols': ['000001'],
        'frequency': DataFrequency.DAILY,
        'mode': ImportMode.BATCH,
        'max_workers': 4,
        'batch_size': 1000
    }
    
    defaults.update(kwargs)
    
    return ImportTaskConfig(task_id=task_id, **defaults)


def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
    """等待条件满足"""
    import time
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    
    return False


# ============================================================================
# 测试标记和跳过条件
# ============================================================================

def skip_if_no_network():
    """如果没有网络连接则跳过测试"""
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return False
    except OSError:
        return True


def skip_if_slow():
    """如果设置了跳过慢速测试则跳过"""
    return os.environ.get('SKIP_SLOW_TESTS', '').lower() in ('1', 'true', 'yes')


# ============================================================================
# 清理函数
# ============================================================================

def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时的清理"""
    # 清理临时文件
    temp_files = [
        'test_*.sqlite',
        'test_*.db',
        '*.tmp'
    ]
    
    import glob
    for pattern in temp_files:
        for file_path in glob.glob(pattern):
            try:
                os.unlink(file_path)
            except:
                pass


# ============================================================================
# 自定义断言
# ============================================================================

class CustomAssertions:
    """自定义断言类"""
    
    @staticmethod
    def assert_performance_within_range(actual_time, expected_time, tolerance=0.5):
        """断言性能在预期范围内"""
        min_time = expected_time * (1 - tolerance)
        max_time = expected_time * (1 + tolerance)
        
        assert min_time <= actual_time <= max_time, \
            f"Performance out of range: {actual_time:.3f}s not in [{min_time:.3f}, {max_time:.3f}]"
    
    @staticmethod
    def assert_memory_usage_reasonable(memory_mb, max_memory_mb=100):
        """断言内存使用合理"""
        assert memory_mb <= max_memory_mb, \
            f"Memory usage too high: {memory_mb:.1f}MB > {max_memory_mb}MB"
    
    @staticmethod
    def assert_anomaly_detection_effective(anomalies, expected_min=1):
        """断言异常检测有效"""
        assert len(anomalies) >= expected_min, \
            f"Anomaly detection ineffective: found {len(anomalies)} anomalies, expected at least {expected_min}"


@pytest.fixture
def custom_assertions():
    """自定义断言fixture"""
    return CustomAssertions()