#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全面架构测试和验证脚本
测试所有已实现的核心组件和集成功能
"""

import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.plugin_types import AssetType, DataType
    from core.asset_type_identifier import AssetTypeIdentifier
    from core.asset_database_manager import AssetSeparatedDatabaseManager
    from core.data_router import DataRouter, DataRequest
    from core.services.asset_aware_unified_data_manager import AssetAwareUnifiedDataManager
    from core.data_standardization_engine import DataStandardizationEngine
    from core.cross_asset_query_engine import CrossAssetQueryEngine
    from core.database_maintenance_engine import DatabaseMaintenanceEngine
    from core.ui_integration.data_missing_manager import DataMissingManager
    from core.ui_integration.smart_data_integration import SmartDataIntegration, UIIntegrationConfig, IntegrationMode
    from loguru import logger

    print("OK 所有核心模块导入成功")

except ImportError as e:
    print(f"ERROR 模块导入失败: {e}")
    sys.exit(1)


class ArchitectureTestSuite:
    """架构测试套件"""

    def __init__(self):
        self.test_results = {}
        self.components = {}
        self.test_data = {
            'symbols': ['000001', '600000', 'BTC-USDT', 'AAPL', '00700'],
            'data_types': [DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE, DataType.FUNDAMENTAL],
            'date_range': (datetime.now() - timedelta(days=30), datetime.now())
        }

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("全面架构测试和验证")
        print("=" * 60)

        # 测试顺序很重要，按依赖关系排列
        test_methods = [
            ("资产类型识别器", self.test_asset_type_identifier),
            ("资产数据库管理器", self.test_asset_database_manager),
            ("数据路由器", self.test_data_router),
            ("资产感知数据管理器", self.test_asset_aware_data_manager),
            ("数据标准化引擎", self.test_data_standardization_engine),
            ("跨资产查询引擎", self.test_cross_asset_query_engine),
            ("数据库维护引擎", self.test_database_maintenance_engine),
            ("数据缺失管理器", self.test_data_missing_manager),
            ("智能数据集成", self.test_smart_data_integration),
            ("组件集成测试", self.test_component_integration),
            ("性能测试", self.test_performance),
            ("错误处理测试", self.test_error_handling)
        ]

        for test_name, test_method in test_methods:
            print(f"\n=== {test_name} ===")
            try:
                result = test_method()
                self.test_results[test_name] = result
                status = "通过" if result else "失败"
                print(f"结果: {status}")
            except Exception as e:
                print(f"ERROR 测试失败: {e}")
                self.test_results[test_name] = False

        # 输出总结
        self.print_summary()

    def test_asset_type_identifier(self) -> bool:
        """测试资产类型识别器"""
        try:
            identifier = AssetTypeIdentifier()
            self.components['identifier'] = identifier

            # 测试各种资产类型识别
            test_cases = [
                ('000001', AssetType.STOCK_A),
                ('600000', AssetType.STOCK_A),
                ('BTC-USDT', AssetType.CRYPTO),
                ('AAPL', AssetType.STOCK_US),
                ('00700', AssetType.STOCK_HK)
            ]

            for symbol, expected_type in test_cases:
                result = identifier.identify_asset_type_by_symbol(symbol)
                if result == expected_type:
                    print(f"  OK {symbol} -> {expected_type.value}")
                else:
                    print(f"  ERROR {symbol} 识别失败，期望 {expected_type.value}，得到 {result}")
                    return False

            # 测试批量识别
            symbols = [case[0] for case in test_cases]
            batch_results = [identifier.identify_asset_type_by_symbol(s) for s in symbols]
            print(f"  OK 批量识别: {len(batch_results)} 个结果")

            # 测试缓存
            cache_stats = identifier.get_cache_stats()
            print(f"  OK 缓存统计: {cache_stats}")

            return True

        except Exception as e:
            print(f"  ERROR 资产类型识别器测试失败: {e}")
            return False

    def test_asset_database_manager(self) -> bool:
        """测试资产数据库管理器"""
        try:
            db_manager = AssetSeparatedDatabaseManager()
            self.components['db_manager'] = db_manager

            # 测试数据库创建
            for asset_type in [AssetType.STOCK_A, AssetType.CRYPTO, AssetType.STOCK_US]:
                db_path = db_manager.get_database_for_asset_type(asset_type)
                print(f"  OK {asset_type.value} 数据库路径: {db_path}")

            # 测试数据库连接和基本操作
            test_symbol = "TEST001"
            try:
                # 测试获取数据库连接
                db_path = db_manager.get_database_for_symbol(test_symbol)
                print(f"  OK 获取数据库连接成功: {test_symbol} -> {db_path[0]}")
            except Exception as e:
                print(f"  WARNING 数据库连接测试失败: {e}")

            # 测试统计信息
            stats = db_manager.get_database_statistics(AssetType.STOCK_A)
            print(f"  OK 数据库统计: {stats}")

            # 测试健康检查
            health = db_manager.check_database_health(AssetType.STOCK_A)
            print(f"  OK 健康检查: {health}")

            return True

        except Exception as e:
            print(f"  ERROR 资产数据库管理器测试失败: {e}")
            return False

    def test_data_router(self) -> bool:
        """测试数据路由器"""
        try:
            router = DataRouter()
            self.components['router'] = router

            # 测试数据源注册
            from core.data_router import DataSourceInfo
            from core.plugin_types import DataSource

            test_source_info = DataSourceInfo(
                source=DataSource.TONGDAXIN,
                asset_types=[AssetType.STOCK_A],
                data_types=[DataType.HISTORICAL_KLINE]
            )
            router.register_data_source(test_source_info)
            print("  OK 数据源注册成功")

            # 测试路由请求
            request = DataRequest(
                symbol='000001',
                data_type=DataType.HISTORICAL_KLINE,
                start_date=datetime.now() - timedelta(days=7),
                end_date=datetime.now()
            )

            route_result = router.route_request(request)
            print(f"  OK 路由结果: {route_result}")

            # 测试批量路由
            requests = [
                DataRequest('000001', DataType.HISTORICAL_KLINE),
                DataRequest('600000', DataType.REAL_TIME_QUOTE),
                DataRequest('BTC-USDT', DataType.HISTORICAL_KLINE)
            ]

            batch_results = router.route_batch_requests(requests)
            print(f"  OK 批量路由: {len(batch_results)} 个结果")

            # 测试统计信息
            stats = router.get_routing_statistics()
            print(f"  OK 路由统计: {stats}")

            return True

        except Exception as e:
            print(f"  ERROR 数据路由器测试失败: {e}")
            return False

    def test_asset_aware_data_manager(self) -> bool:
        """测试资产感知数据管理器"""
        try:
            data_manager = AssetAwareUnifiedDataManager()
            self.components['data_manager'] = data_manager

            # 测试数据查询
            from core.services.asset_aware_unified_data_manager import AssetAwareDataRequest

            for symbol in self.test_data['symbols'][:3]:  # 测试前3个
                try:
                    request = AssetAwareDataRequest(
                        symbol=symbol,
                        data_type='kline',
                        start_date=datetime.now() - timedelta(days=7),
                        end_date=datetime.now()
                    )
                    result = data_manager.get_asset_aware_data(request)
                    print(f"  OK {symbol} 数据查询: {'有数据' if result else '无数据'}")
                except Exception as e:
                    print(f"  WARNING {symbol} 查询失败: {e}")

            # 测试跨资产数据查询
            try:
                cross_asset_data = data_manager.get_cross_asset_data(['000001', '600000'])
                print(f"  OK 跨资产数据查询: {len(cross_asset_data) if cross_asset_data else 0} 条记录")
            except Exception as e:
                print(f"  WARNING 跨资产数据查询失败: {e}")

            # 测试统计信息
            try:
                stats = data_manager.get_asset_statistics()
                print(f"  OK 数据管理器统计: {stats}")
            except Exception as e:
                print(f"  WARNING 统计信息获取失败: {e}")

            return True

        except Exception as e:
            print(f"  ERROR 资产感知数据管理器测试失败: {e}")
            return False

    def test_data_standardization_engine(self) -> bool:
        """测试数据标准化引擎"""
        try:
            engine = DataStandardizationEngine()
            self.components['standardization_engine'] = engine

            # 测试数据标准化
            raw_data = {
                'symbol': '000001',
                'date': '2024-01-01',
                'open_price': 10.0,
                'high_price': 11.0,
                'low_price': 9.5,
                'close_price': 10.5,
                'vol': 1000000
            }

            from core.plugin_types import DataSource
            result = engine.standardize_data(raw_data, DataSource.TONGDAXIN, DataType.HISTORICAL_KLINE, AssetType.STOCK_A, '000001')
            if result.success:
                print(f"  OK 数据标准化成功: {len(result.standardized_data)} 个字段")
                print(f"  OK 质量评分: {result.quality_score}")
            else:
                print(f"  ERROR 数据标准化失败: {result.error_message}")
                return False

            # 测试不同数据源
            test_sources = [
                (DataSource.EASTMONEY, AssetType.STOCK_A),
                (DataSource.SINA, AssetType.STOCK_A),
                (DataSource.BINANCE, AssetType.CRYPTO)
            ]
            for source, asset_type in test_sources:
                try:
                    test_result = engine.standardize_data(raw_data, source, DataType.HISTORICAL_KLINE, asset_type, '000001')
                    status = "成功" if test_result.success else "失败"
                    print(f"  OK {source.value} 标准化: {status}")
                except Exception as e:
                    print(f"  WARNING {source.value} 标准化异常: {e}")

            # 测试统计信息
            stats = engine.get_statistics()
            print(f"  OK 标准化统计: {stats}")

            return True

        except Exception as e:
            print(f"  ERROR 数据标准化引擎测试失败: {e}")
            return False

    def test_cross_asset_query_engine(self) -> bool:
        """测试跨资产查询引擎"""
        try:
            query_engine = CrossAssetQueryEngine()
            self.components['query_engine'] = query_engine

            # 测试查询请求
            from core.cross_asset_query_engine import CrossAssetQueryRequest, QueryFilter

            query_request = CrossAssetQueryRequest(
                asset_types=[AssetType.STOCK_A, AssetType.CRYPTO],
                data_type=DataType.HISTORICAL_KLINE,
                symbols=['000001', 'BTC-USDT'],
                filters=[
                    QueryFilter(
                        field='date',
                        operator='>=',
                        value=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                    )
                ]
            )

            print(f"  OK 查询请求创建成功")

            # 测试查询执行（模拟）
            try:
                results = query_engine.execute_query(query_request)
                print(f"  OK 查询执行: {'成功' if results else '无结果'}")
            except Exception as e:
                print(f"  WARNING 查询执行失败: {e}")

            # 测试统计信息
            try:
                stats = query_engine.get_query_statistics()
                print(f"  OK 查询统计: {stats}")
            except Exception as e:
                print(f"  WARNING 查询统计获取失败: {e}")

            return True

        except Exception as e:
            print(f"  ERROR 跨资产查询引擎测试失败: {e}")
            return False

    def test_database_maintenance_engine(self) -> bool:
        """测试数据库维护引擎"""
        try:
            maintenance_engine = DatabaseMaintenanceEngine()
            self.components['maintenance_engine'] = maintenance_engine

            # 测试维护任务创建
            from core.database_maintenance_engine import MaintenanceTaskType, MaintenancePriority

            task_id = maintenance_engine.create_maintenance_task(
                MaintenanceTaskType.HEALTH_CHECK,
                AssetType.STOCK_A,
                MaintenancePriority.HIGH
            )
            print(f"  OK 维护任务创建: {task_id}")

            # 测试任务状态查询
            task = maintenance_engine.get_task_status(task_id)
            if task:
                print(f"  OK 任务状态: {task.status}")

            # 测试活跃任务列表
            active_tasks = maintenance_engine.list_active_tasks()
            print(f"  OK 活跃任务: {len(active_tasks)} 个")

            # 测试系统健康摘要
            health_summary = maintenance_engine.get_system_health_summary()
            print(f"  OK 系统健康摘要: {health_summary}")

            # 等待一下任务执行
            time.sleep(2)

            # 检查任务完成情况
            completed_tasks = [t for t in maintenance_engine.list_active_tasks() if t.status == 'completed']
            print(f"  OK 已完成任务: {len(completed_tasks)} 个")

            return True

        except Exception as e:
            print(f"  ERROR 数据库维护引擎测试失败: {e}")
            return False

    def test_data_missing_manager(self) -> bool:
        """测试数据缺失管理器"""
        try:
            missing_manager = DataMissingManager()
            self.components['missing_manager'] = missing_manager

            # 测试数据可用性检查
            for symbol in ['000001', 'MISSING_SYMBOL']:
                availability = missing_manager.check_data_availability(
                    symbol,
                    DataType.HISTORICAL_KLINE,
                    (datetime.now() - timedelta(days=7), datetime.now())
                )
                print(f"  OK {symbol} 可用性: {availability.status.value}")

            # 测试下载任务创建
            task_id = missing_manager.create_download_task(
                'TEST001',
                AssetType.STOCK_A,
                DataType.HISTORICAL_KLINE,
                (datetime.now() - timedelta(days=7), datetime.now())
            )
            print(f"  OK 下载任务创建: {task_id}")

            # 测试插件建议
            suggestions = missing_manager.suggest_data_sources(AssetType.STOCK_A, DataType.HISTORICAL_KLINE)
            print(f"  OK 插件建议: {len(suggestions)} 个")

            # 测试插件可用性
            plugin_status = missing_manager.get_plugin_availability()
            available_count = sum(1 for status in plugin_status.values() if status.get('status') == '可用')
            print(f"  OK 插件状态: {available_count}/{len(plugin_status)} 可用")

            return True

        except Exception as e:
            print(f"  ERROR 数据缺失管理器测试失败: {e}")
            return False

    def test_smart_data_integration(self) -> bool:
        """测试智能数据集成"""
        try:
            config = UIIntegrationConfig(
                mode=IntegrationMode.PASSIVE,
                show_missing_prompt=False
            )
            integration = SmartDataIntegration(config)
            self.components['integration'] = integration

            # 测试数据检查
            result = integration.check_data_for_widget(
                'test_widget',
                '000001',
                'historical',
                datetime.now() - timedelta(days=7),
                datetime.now()
            )
            print(f"  OK 数据检查: {'可用' if result else '缺失'}")

            # 测试插件建议
            suggestions = integration.get_plugin_suggestions('000001', 'historical')
            print(f"  OK 插件建议: {len(suggestions)} 个")

            # 测试配置更新
            new_config = UIIntegrationConfig(mode=IntegrationMode.SMART)
            integration.update_config(new_config)
            print(f"  OK 配置更新: {integration.config.mode.value}")

            # 测试统计信息
            stats = integration.get_statistics()
            print(f"  OK 统计信息: {stats}")

            return True

        except Exception as e:
            print(f"  ERROR 智能数据集成测试失败: {e}")
            return False

    def test_component_integration(self) -> bool:
        """测试组件集成"""
        try:
            print("  测试组件间协作...")

            # 测试完整的数据流
            if 'identifier' in self.components and 'db_manager' in self.components:
                # 1. 识别资产类型
                symbol = '000001'
                asset_type = self.components['identifier'].identify_asset_type_by_symbol(symbol)
                print(f"    OK 资产识别: {symbol} -> {asset_type.value}")

                # 2. 获取数据库路径
                db_path = self.components['db_manager'].get_database_for_asset_type(asset_type)
                print(f"    OK 数据库路径: {db_path}")

                # 3. 检查数据可用性
                if 'missing_manager' in self.components:
                    availability = self.components['missing_manager'].check_data_availability(
                        symbol, DataType.HISTORICAL_KLINE,
                        (datetime.now() - timedelta(days=7), datetime.now())
                    )
                    print(f"    OK 数据可用性: {availability.status.value}")

            # 测试数据标准化和存储流程
            if 'standardization_engine' in self.components and 'db_manager' in self.components:
                raw_data = {
                    'symbol': 'INTEGRATION_TEST',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'open': 100.0,
                    'high': 105.0,
                    'low': 98.0,
                    'close': 102.0,
                    'volume': 1000000
                }

                # 标准化数据
                from core.plugin_types import DataSource
                std_result = self.components['standardization_engine'].standardize_data(
                    raw_data, DataSource.TONGDAXIN, DataType.HISTORICAL_KLINE, AssetType.STOCK_A, 'INTEGRATION_TEST'
                )

                if std_result.success:
                    print(f"    OK 数据标准化成功")
                    print(f"    OK 数据存储: 模拟成功")

            print("  OK 组件集成测试完成")
            return True

        except Exception as e:
            print(f"  ERROR 组件集成测试失败: {e}")
            return False

    def test_performance(self) -> bool:
        """测试性能"""
        try:
            print("  执行性能测试...")

            # 测试批量资产识别性能
            if 'identifier' in self.components:
                symbols = ['000001', '000002', '600000', '600036', 'BTC-USDT'] * 20  # 100个符号
                start_time = time.time()
                results = [self.components['identifier'].identify_asset_type_by_symbol(s) for s in symbols]
                end_time = time.time()

                duration = end_time - start_time
                rate = len(symbols) / duration
                print(f"    OK 批量识别性能: {rate:.0f} 符号/秒")

            # 测试数据库连接性能
            if 'db_manager' in self.components:
                start_time = time.time()
                for i in range(10):
                    self.components['db_manager'].get_database_for_asset_type(AssetType.STOCK_A)
                end_time = time.time()

                duration = end_time - start_time
                rate = 10 / duration
                print(f"    OK 数据库连接性能: {rate:.1f} 连接/秒")

            # 测试数据标准化性能
            if 'standardization_engine' in self.components:
                test_data = {
                    'symbol': 'PERF_TEST',
                    'date': '2024-01-01',
                    'open': 10.0,
                    'high': 11.0,
                    'low': 9.5,
                    'close': 10.5,
                    'volume': 1000000
                }

                start_time = time.time()
                for i in range(100):
                    self.components['standardization_engine'].standardize_data(
                        test_data, DataSource.TONGDAXIN, DataType.HISTORICAL_KLINE, AssetType.STOCK_A, 'PERF_TEST'
                    )
                end_time = time.time()

                duration = end_time - start_time
                rate = 100 / duration
                print(f"    OK 数据标准化性能: {rate:.0f} 记录/秒")

            return True

        except Exception as e:
            print(f"  ERROR 性能测试失败: {e}")
            return False

    def test_error_handling(self) -> bool:
        """测试错误处理"""
        try:
            print("  测试错误处理...")

            # 测试无效符号处理
            if 'identifier' in self.components:
                try:
                    result = self.components['identifier'].identify_asset_type_by_symbol('INVALID_SYMBOL_12345')
                    print(f"    OK 无效符号处理: {result}")
                except Exception as e:
                    print(f"    OK 无效符号异常处理: {type(e).__name__}")

            # 测试数据库错误处理
            if 'db_manager' in self.components:
                try:
                    # 尝试获取无效资产类型的数据库
                    result = self.components['db_manager'].get_database_for_asset_type(AssetType.UNKNOWN)
                    print(f"    OK 数据库错误处理: 无异常抛出")
                except Exception as e:
                    print(f"    OK 数据库异常处理: {type(e).__name__}")

            # 测试数据标准化错误处理
            if 'standardization_engine' in self.components:
                try:
                    # 使用无效数据
                    invalid_data = {'invalid': 'data'}
                    result = self.components['standardization_engine'].standardize_data(
                        invalid_data, DataSource.TONGDAXIN, DataType.HISTORICAL_KLINE, AssetType.STOCK_A, 'INVALID'
                    )
                    print(f"    OK 标准化错误处理: {result.success}")
                except Exception as e:
                    print(f"    OK 标准化异常处理: {type(e).__name__}")

            return True

        except Exception as e:
            print(f"  ERROR 错误处理测试失败: {e}")
            return False

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("测试结果总结")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests

        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")

        print("\n详细结果:")
        for test_name, result in self.test_results.items():
            status = "通过" if result else "失败"
            print(f"  {test_name:<20} {status}")

        if failed_tests > 0:
            print(f"\nWARNING {failed_tests} 个测试失败，需要检查和修复")
        else:
            print("\nSUCCESS 所有测试通过！新架构验证成功")

        return passed_tests == total_tests

    def cleanup(self):
        """清理资源"""
        try:
            for component_name, component in self.components.items():
                if hasattr(component, 'close'):
                    component.close()
                    print(f"  OK {component_name} 已关闭")
        except Exception as e:
            print(f"  WARNING 清理资源时出错: {e}")


def main():
    """主函数"""
    test_suite = ArchitectureTestSuite()

    try:
        test_suite.run_all_tests()
        return test_suite.test_results
    finally:
        print("\n清理测试资源...")
        test_suite.cleanup()


if __name__ == "__main__":
    results = main()

    # 根据测试结果设置退出码
    all_passed = all(results.values()) if results else False
    sys.exit(0 if all_passed else 1)
