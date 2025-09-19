#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import tempfile
import os
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.append('.')


def test_performance():
    """快速性能测试"""
    print("开始快速性能测试...")

    try:
        from core.importdata.intelligent_config_manager import IntelligentConfigManager
        from core.importdata.import_config_manager import ImportTaskConfig, DataFrequency, ImportMode
        from core.ai.data_anomaly_detector import DataAnomalyDetector, AnomalyDetectionConfig

        # 创建临时数据库
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()

        try:
            print("1. 测试配置管理器性能...")
            start_time = time.time()

            manager = IntelligentConfigManager(temp_db.name)

            # 批量添加任务
            for i in range(10):
                config = ImportTaskConfig(
                    task_id=f"perf_test_{i}",
                    name=f"性能测试任务{i}",
                    data_source="tongdaxin",
                    asset_type="stock",
                    data_type="kline",
                    symbols=[f"00000{i}"],
                    frequency=DataFrequency.DAILY,
                    mode=ImportMode.BATCH
                )
                manager.add_import_task(config)

                # 记录性能反馈
                manager.record_performance_feedback(
                    config=config,
                    execution_time=60.0 + i * 10,
                    success_rate=0.9 + i * 0.01,
                    error_rate=0.1 - i * 0.01,
                    throughput=1000.0 + i * 100
                )

            config_time = time.time() - start_time
            print(f"   配置管理器测试完成: {config_time:.2f}秒")

            print("2. 测试异常检测性能...")
            start_time = time.time()

            # 创建异常检测器
            detector_config = AnomalyDetectionConfig(
                enable_outlier_detection=True,
                enable_missing_data_detection=True,
                enable_duplicate_detection=True,
                auto_repair_enabled=False  # 关闭自动修复以加快测试
            )

            detector = DataAnomalyDetector(detector_config, temp_db.name)

            # 创建测试数据
            np.random.seed(42)
            test_data = pd.DataFrame({
                'price': np.random.normal(100, 10, 1000),
                'volume': np.random.normal(1000, 200, 1000),
                'timestamp': pd.date_range('2024-01-01', periods=1000, freq='D')
            })

            # 添加一些异常值
            test_data.loc[50:55, 'price'] = np.nan  # 缺失值
            test_data.loc[100:105, 'price'] = 1000  # 异常值

            # 检测异常
            anomalies = detector.detect_anomalies(
                data=test_data,
                data_source="performance_test",
                symbol="PERF001",
                data_type="kline"
            )

            anomaly_time = time.time() - start_time
            print(f"   异常检测测试完成: {anomaly_time:.2f}秒, 检测到异常: {len(anomalies)}个")

            print("3. 测试统计信息性能...")
            start_time = time.time()

            stats = manager.get_intelligent_statistics()
            conflicts = manager.detect_config_conflicts()

            stats_time = time.time() - start_time
            print(f"   统计信息测试完成: {stats_time:.2f}秒")

            print(f"\n=== 性能测试结果 ===")
            print(f"配置管理器: {config_time:.2f}秒")
            print(f"异常检测: {anomaly_time:.2f}秒")
            print(f"统计信息: {stats_time:.2f}秒")
            print(f"总耗时: {config_time + anomaly_time + stats_time:.2f}秒")
            print(f"任务数量: {len(manager._tasks)}")
            print(f"冲突数量: {len(conflicts)}")
            print(f"异常数量: {len(anomalies)}")

            return True

        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass

    except Exception as e:
        print(f"性能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_performance()
    print(f"\n性能测试{'通过' if success else '失败'}！")
    sys.exit(0 if success else 1)
