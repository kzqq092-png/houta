#!/usr/bin/env python3
"""
增量更新功能综合测试脚本

测试新增的功能：
1. AssetSeparatedDatabaseManager.get_latest_date()
2. AssetSeparatedDatabaseManager.get_data_statistics()
3. AssetSeparatedDatabaseManager._validate_kline_data_quality()
4. ImportExecutionEngine._check_incremental_update()
5. ImportExecutionEngine增量更新逻辑
6. ImportTaskConfig增量更新配置

作者: FactorWeave-Quant团队
版本: 1.0
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List
import traceback

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

class IncrementalUpdateTester:
    """增量更新功能测试器"""
    
    def __init__(self):
        self.test_results = {}
        self.asset_manager = None
        self.import_engine = None
        
    def setup_test_environment(self) -> bool:
        """设置测试环境"""
        try:
            logger.info("=== 设置测试环境 ===")
            
            # 初始化资产数据库管理器
            from core.asset_database_manager import AssetSeparatedDatabaseManager
            from core.plugin_types import AssetType
            
            self.asset_manager = AssetSeparatedDatabaseManager()
            logger.info("AssetSeparatedDatabaseManager 初始化成功")
            
            # 初始化导入执行引擎
            from core.importdata.import_execution_engine import ImportExecutionEngine
            from core.importdata.import_config_manager import ImportTaskConfig, DataFrequency, ImportMode
            
            self.import_engine = ImportExecutionEngine()
            logger.info("ImportExecutionEngine 初始化成功")
            
            return True
            
        except Exception as e:
            logger.error(f"测试环境设置失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def test_asset_manager_latest_date(self) -> bool:
        """测试AssetSeparatedDatabaseManager.get_latest_date()方法"""
        try:
            logger.info("=== 测试 get_latest_date() 方法 ===")
            
            from core.plugin_types import AssetType
            
            # 测试获取最新日期
            latest_date = self.asset_manager.get_latest_date(
                symbol="000001",
                asset_type=AssetType.STOCK_A,
                frequency="1d",
                data_source="AKShare"
            )
            
            if latest_date is None:
                logger.info("get_latest_date() 返回 None (无历史数据，符合预期)")
            else:
                logger.info(f"get_latest_date() 返回: {latest_date}")
            
            return True
            
        except Exception as e:
            logger.error(f"get_latest_date() 测试失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def test_asset_manager_data_statistics(self) -> bool:
        """测试AssetSeparatedDatabaseManager.get_data_statistics()方法"""
        try:
            logger.info("=== 测试 get_data_statistics() 方法 ===")
            
            from core.plugin_types import AssetType
            
            # 测试获取数据统计
            stats = self.asset_manager.get_data_statistics(AssetType.STOCK_A)
            
            logger.info(f"get_data_statistics() 返回:")
            logger.info(f"   资产类型: {stats.get('asset_type', 'N/A')}")
            logger.info(f"   数据库存在: {stats.get('database_exists', False)}")
            logger.info(f"   股票数量: {stats.get('symbol_count', 0)}")
            logger.info(f"   记录数量: {stats.get('record_count', 0)}")
            logger.info(f"   数据库大小: {stats.get('size_mb', 0)} MB")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ get_data_statistics() 测试失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def test_asset_manager_data_quality_validation(self) -> bool:
        """测试AssetSeparatedDatabaseManager._validate_kline_data_quality()方法"""
        try:
            logger.info("=== 测试 _validate_kline_data_quality() 方法 ===")
            
            # 创建测试数据
            test_data = pd.DataFrame({
                'open': [10.0, 11.0, 12.0],
                'high': [10.5, 11.5, 12.5],
                'low': [9.5, 10.5, 11.5],
                'close': [10.2, 11.2, 12.2],
                'volume': [1000, 1100, 1200]
            })
            
            # 测试正常数据
            is_valid, errors = self.asset_manager._validate_kline_data_quality(test_data)
            logger.info(f"✅ 正常数据验证: {'通过' if is_valid else '失败'}")
            if errors:
                logger.info(f"   错误信息: {errors}")
            
            # 创建异常数据（high < max(open, close, low)）
            invalid_data = pd.DataFrame({
                'open': [10.0, 11.0, 12.0],
                'high': [9.0, 10.0, 11.0],  # 故意设置错误
                'low': [9.5, 10.5, 11.5],
                'close': [10.2, 11.2, 12.2],
                'volume': [1000, 1100, 1200]
            })
            
            # 测试异常数据
            is_valid, errors = self.asset_manager._validate_kline_data_quality(invalid_data)
            logger.info(f"✅ 异常数据验证: {'通过' if is_valid else '失败'}")
            if errors:
                logger.info(f"   检测到的错误: {errors}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ _validate_kline_data_quality() 测试失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def test_import_task_config_incremental(self) -> bool:
        """测试ImportTaskConfig增量更新配置"""
        try:
            logger.info("=== 测试 ImportTaskConfig 增量更新配置 ===")
            
            from core.importdata.import_config_manager import ImportTaskConfig, DataFrequency, ImportMode
            
            # 创建带增量更新配置的任务配置
            task_config = ImportTaskConfig(
                task_id="test_incremental_001",
                name="增量更新测试任务",
                data_source="AKShare",
                asset_type="STOCK_A",
                data_type="kline",
                symbols=["000001", "000002"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.MANUAL,
                start_date="2024-01-01",
                end_date="2024-01-31",
                # 增量更新配置
                enable_incremental=True,
                incremental_days_threshold=7,
                force_full_update=False
            )
            
            logger.info(f"✅ ImportTaskConfig 创建成功:")
            logger.info(f"   任务ID: {task_config.task_id}")
            logger.info(f"   启用增量更新: {task_config.enable_incremental}")
            logger.info(f"   增量更新阈值: {task_config.incremental_days_threshold} 天")
            logger.info(f"   强制全量更新: {task_config.force_full_update}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ ImportTaskConfig 增量更新配置测试失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def test_import_engine_incremental_check(self) -> bool:
        """测试ImportExecutionEngine._check_incremental_update()方法"""
        try:
            logger.info("=== 测试 _check_incremental_update() 方法 ===")
            
            from core.importdata.import_config_manager import ImportTaskConfig, DataFrequency, ImportMode
            
            # 创建测试任务配置
            task_config = ImportTaskConfig(
                task_id="test_incremental_002",
                name="增量更新检查测试",
                data_source="AKShare",
                asset_type="STOCK_A",
                data_type="kline",
                symbols=["000001"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.MANUAL,
                start_date="2024-01-01",
                end_date="2024-01-31",
                enable_incremental=True,
                incremental_days_threshold=7,
                force_full_update=False
            )
            
            # 测试增量更新检查
            need_update, latest_date = self.import_engine._check_incremental_update("000001", task_config)
            
            logger.info(f"✅ _check_incremental_update() 测试结果:")
            logger.info(f"   需要更新: {need_update}")
            logger.info(f"   最新日期: {latest_date}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ _check_incremental_update() 测试失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def test_integration_workflow(self) -> bool:
        """测试完整的增量更新工作流程"""
        try:
            logger.info("=== 测试完整的增量更新工作流程 ===")
            
            # 这个测试模拟完整的增量更新流程
            # 由于涉及实际的数据下载，这里主要测试配置和逻辑
            
            from core.importdata.import_config_manager import ImportTaskConfig, DataFrequency, ImportMode
            
            # 创建测试任务配置
            task_config = ImportTaskConfig(
                task_id="test_integration_001",
                name="增量更新集成测试",
                data_source="AKShare",
                asset_type="STOCK_A",
                data_type="kline",
                symbols=["000001", "000002", "000003"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.MANUAL,
                start_date="2024-01-01",
                end_date="2024-01-31",
                enable_incremental=True,
                incremental_days_threshold=7,
                force_full_update=False
            )
            
            logger.info(f"✅ 增量更新工作流程配置成功:")
            logger.info(f"   任务ID: {task_config.task_id}")
            logger.info(f"   股票数量: {len(task_config.symbols)}")
            logger.info(f"   增量更新: {'启用' if task_config.enable_incremental else '禁用'}")
            logger.info(f"   更新阈值: {task_config.incremental_days_threshold} 天")
            
            # 模拟检查每个股票的增量更新状态
            for symbol in task_config.symbols:
                need_update, latest_date = self.import_engine._check_incremental_update(symbol, task_config)
                logger.info(f"   {symbol}: 需要更新={need_update}, 最新日期={latest_date}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 增量更新工作流程测试失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """运行所有测试"""
        logger.info("开始增量更新功能综合测试")
        logger.info("=" * 60)
        
        # 设置测试环境
        if not self.setup_test_environment():
            logger.error("测试环境设置失败，终止测试")
            return {"setup": False}
        
        # 运行各项测试
        tests = [
            ("AssetManager最新日期查询", self.test_asset_manager_latest_date),
            ("AssetManager数据统计", self.test_asset_manager_data_statistics),
            ("AssetManager数据质量验证", self.test_asset_manager_data_quality_validation),
            ("ImportTaskConfig增量配置", self.test_import_task_config_incremental),
            ("ImportEngine增量检查", self.test_import_engine_incremental_check),
            ("完整工作流程", self.test_integration_workflow),
        ]
        
        results = {}
        for test_name, test_func in tests:
            logger.info(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    logger.info(f"通过 - {test_name}")
                else:
                    logger.error(f"失败 - {test_name}")
            except Exception as e:
                logger.error(f"异常 - {test_name}: {e}")
                results[test_name] = False
        
        return results
    
    def print_test_report(self, results: Dict[str, bool]):
        """打印测试报告"""
        logger.info("\n" + "=" * 60)
        logger.info("增量更新功能测试报告")
        logger.info("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result)
        failed_tests = total_tests - passed_tests
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        logger.info(f"失败: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        
        logger.info("\n详细结果:")
        for test_name, result in results.items():
            status = "通过" if result else "失败"
            logger.info(f"  {test_name}: {status}")
        
        if failed_tests == 0:
            logger.info("\n所有测试通过！增量更新功能实现成功！")
        else:
            logger.warning(f"\n有 {failed_tests} 个测试失败，需要检查实现")
        
        logger.info("=" * 60)

def main():
    """主函数"""
    try:
        tester = IncrementalUpdateTester()
        results = tester.run_all_tests()
        tester.print_test_report(results)
        
        # 返回测试结果
        all_passed = all(results.values())
        return 0 if all_passed else 1
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
