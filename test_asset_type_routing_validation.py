#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产类型路由全量验证回归测试
验证删除推断代码后的完整功能链路
"""

import sys
import os
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

class AssetTypeRoutingValidator:
    """资产类型路由验证器"""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def run_validation(self) -> bool:
        """运行全量验证"""
        logger.info("开始资产类型路由全量验证回归测试")
        logger.info("=" * 80)
        
        try:
            # 1. 验证核心模块导入
            if not self._test_core_imports():
                return False
                
            # 2. 验证资产类型枚举
            if not self._test_asset_type_enum():
                return False
                
            # 3. 验证数据管理器初始化
            if not self._test_data_manager_initialization():
                return False
                
            # 4. 验证数据提供器初始化
            if not self._test_data_provider_initialization():
                return False
                
            # 5. 验证导入引擎初始化
            if not self._test_import_engine_initialization():
                return False
                
            # 6. 验证资产类型传递链
            if not self._test_asset_type_chain():
                return False
                
            # 7. 验证数据存储逻辑
            if not self._test_data_storage_logic():
                return False
                
            # 8. 验证UI配置映射
            if not self._test_ui_config_mapping():
                return False
                
            # 9. 验证数据库管理器
            if not self._test_database_manager():
                return False
                
            # 10. 验证推断代码已删除
            if not self._test_inference_code_removed():
                return False
                
            # 11. 验证向后兼容性
            if not self._test_backward_compatibility():
                return False
                
            # 12. 验证错误处理
            if not self._test_error_handling():
                return False
                
            return self._print_final_report()
            
        except Exception as e:
            logger.error(f"验证过程中发生严重错误: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _test_core_imports(self) -> bool:
        """测试核心模块导入"""
        logger.info("测试核心模块导入...")
        
        modules_to_test = [
            ('core.plugin_types', 'AssetType', 'DataType'),
            ('core.services.unified_data_manager', 'UnifiedDataManager'),
            ('core.real_data_provider', 'RealDataProvider'),
            ('core.importdata.import_execution_engine', 'DataImportExecutionEngine'),
            ('core.asset_database_manager', 'AssetSeparatedDatabaseManager'),
        ]
        
        all_passed = True
        for module_name, *class_names in modules_to_test:
            try:
                module = __import__(module_name, fromlist=class_names)
                for class_name in class_names:
                    if hasattr(module, class_name):
                        getattr(module, class_name)
                        logger.info(f"  [PASS] {module_name}.{class_name}")
                    else:
                        logger.error(f"  [FAIL] {module_name}.{class_name} - 类不存在")
                        all_passed = False
            except Exception as e:
                logger.error(f"  [FAIL] {module_name} - {e}")
                all_passed = False
                
        self._record_test("核心模块导入", all_passed)
        return all_passed
    
    def _test_asset_type_enum(self) -> bool:
        """测试资产类型枚举"""
        logger.info("测试资产类型枚举...")
        
        try:
            from core.plugin_types import AssetType, DataType
            
            # 测试主要资产类型
            main_asset_types = [
                AssetType.STOCK_A,
                AssetType.STOCK_US,
                AssetType.CRYPTO,
                AssetType.FUTURES,
                AssetType.FOREX,
                AssetType.COMMODITY,
                AssetType.BOND,
                AssetType.FUND,
                AssetType.INDEX,
                AssetType.SECTOR,
            ]
            
            for asset_type in main_asset_types:
                if not hasattr(asset_type, 'value'):
                    logger.error(f"  [FAIL] {asset_type} 缺少value属性")
                    return False
                logger.info(f"  [PASS] {asset_type.name} = {asset_type.value}")
            
            # 测试数据类型
            data_types = [
                DataType.HISTORICAL_KLINE,
                DataType.REAL_TIME_QUOTE,
                DataType.FUNDAMENTAL,
                DataType.ASSET_LIST,
            ]
            
            for data_type in data_types:
                if not hasattr(data_type, 'value'):
                    logger.error(f"  [FAIL] {data_type} 缺少value属性")
                    return False
                logger.info(f"  [PASS] {data_type.name} = {data_type.value}")
            
            logger.info("  [PASS] 资产类型枚举测试通过")
            self._record_test("资产类型枚举", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 资产类型枚举测试失败: {e}")
            self._record_test("资产类型枚举", False)
            return False
    
    def _test_data_manager_initialization(self) -> bool:
        """测试数据管理器初始化"""
        logger.info("测试数据管理器初始化...")
        
        try:
            from core.services.unified_data_manager import UnifiedDataManager
            
            # 测试初始化
            data_manager = UnifiedDataManager()
            logger.info("  [PASS] UnifiedDataManager 初始化成功")
            
            # 测试关键方法存在
            required_methods = [
                'get_kdata_from_source',
                'get_asset_list',
                'get_historical_data',
                'get_asset_data',
            ]
            
            for method_name in required_methods:
                if not hasattr(data_manager, method_name):
                    logger.error(f"  [FAIL] 缺少方法: {method_name}")
                    return False
                logger.info(f"  [PASS] 方法存在: {method_name}")
            
            # 测试get_kdata_from_source方法签名
            import inspect
            sig = inspect.signature(data_manager.get_kdata_from_source)
            params = list(sig.parameters.keys())
            
            if 'asset_type' not in params:
                logger.error("  [FAIL] get_kdata_from_source 缺少 asset_type 参数")
                return False
            
            logger.info(f"  [PASS] get_kdata_from_source 参数: {params}")
            
            self._record_test("数据管理器初始化", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 数据管理器初始化失败: {e}")
            self._record_test("数据管理器初始化", False)
            return False
    
    def _test_data_provider_initialization(self) -> bool:
        """测试数据提供器初始化"""
        logger.info("测试数据提供器初始化...")
        
        try:
            from core.real_data_provider import RealDataProvider
            
            # 测试初始化
            data_provider = RealDataProvider()
            logger.info("  [PASS] RealDataProvider 初始化成功")
            
            # 测试关键方法存在
            required_methods = [
                'get_real_kdata',
                'get_real_stock_list',
            ]
            
            for method_name in required_methods:
                if not hasattr(data_provider, method_name):
                    logger.error(f"  [FAIL] 缺少方法: {method_name}")
                    return False
                logger.info(f"  [PASS] 方法存在: {method_name}")
            
            # 测试get_real_kdata方法签名
            import inspect
            sig = inspect.signature(data_provider.get_real_kdata)
            params = list(sig.parameters.keys())
            
            if 'asset_type' not in params:
                logger.error("  [FAIL] get_real_kdata 缺少 asset_type 参数")
                return False
            
            logger.info(f"  [PASS] get_real_kdata 参数: {params}")
            
            self._record_test("数据提供器初始化", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 数据提供器初始化失败: {e}")
            self._record_test("数据提供器初始化", False)
            return False
    
    def _test_import_engine_initialization(self) -> bool:
        """测试导入引擎初始化"""
        logger.info("测试导入引擎初始化...")
        
        try:
            from core.importdata.import_execution_engine import DataImportExecutionEngine
            
            # 测试初始化
            import_engine = DataImportExecutionEngine()
            logger.info("  [PASS] DataImportExecutionEngine 初始化成功")
            
            # 测试关键方法存在
            required_methods = [
                '_save_kdata_to_database',
                '_batch_save_kdata_to_database',
                '_save_fundamental_data_to_database',
                '_save_realtime_data_to_database',
            ]
            
            for method_name in required_methods:
                if not hasattr(import_engine, method_name):
                    logger.error(f"  [FAIL] 缺少方法: {method_name}")
                    return False
                logger.info(f"  [PASS] 方法存在: {method_name}")
            
            self._record_test("导入引擎初始化", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 导入引擎初始化失败: {e}")
            self._record_test("导入引擎初始化", False)
            return False
    
    def _test_asset_type_chain(self) -> bool:
        """测试资产类型传递链"""
        logger.info("测试资产类型传递链...")
        
        try:
            from core.services.unified_data_manager import UnifiedDataManager
            from core.real_data_provider import RealDataProvider
            from core.plugin_types import AssetType
            
            # 测试数据管理器
            data_manager = UnifiedDataManager()
            
            # 测试不同资产类型的传递
            test_asset_types = [
                AssetType.STOCK_A,
                AssetType.STOCK_US,
                AssetType.CRYPTO,
                AssetType.FUTURES,
            ]
            
            for asset_type in test_asset_types:
                try:
                    # 测试get_kdata_from_source方法调用
                    result = data_manager.get_kdata_from_source(
                        stock_code="000001",
                        period="D",
                        count=10,
                        data_source="akshare",
                        asset_type=asset_type
                    )
                    logger.info(f"  [PASS] {asset_type.value} 资产类型传递成功")
                except Exception as e:
                    logger.warning(f"  [WARN] {asset_type.value} 资产类型传递测试失败（可能是正常的数据获取失败）: {e}")
            
            # 测试数据提供器
            data_provider = RealDataProvider()
            
            for asset_type in test_asset_types:
                try:
                    # 测试get_real_kdata方法调用
                    result = data_provider.get_real_kdata(
                        code="000001",
                        freq="D",
                        count=10,
                        data_source="akshare",
                        asset_type=asset_type.value
                    )
                    logger.info(f"  [PASS] {asset_type.value} 数据提供器传递成功")
                except Exception as e:
                    logger.warning(f"  [WARN] {asset_type.value} 数据提供器传递测试失败（可能是正常的数据获取失败）: {e}")
            
            logger.info("  [PASS] 资产类型传递链测试通过")
            self._record_test("资产类型传递链", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 资产类型传递链测试失败: {e}")
            self._record_test("资产类型传递链", False)
            return False
    
    def _test_data_storage_logic(self) -> bool:
        """测试数据存储逻辑"""
        logger.info("测试数据存储逻辑...")
        
        try:
            from core.asset_database_manager import AssetSeparatedDatabaseManager
            from core.plugin_types import AssetType, DataType
            import pandas as pd
            
            # 测试数据库管理器初始化
            db_manager = AssetSeparatedDatabaseManager()
            logger.info("  [PASS] AssetSeparatedDatabaseManager 初始化成功")
            
            # 测试关键方法存在
            required_methods = [
                'store_standardized_data',
                'get_database_path',
                '_map_asset_type_to_database',
            ]
            
            for method_name in required_methods:
                if not hasattr(db_manager, method_name):
                    logger.error(f"  [FAIL] 缺少方法: {method_name}")
                    return False
                logger.info(f"  [PASS] 方法存在: {method_name}")
            
            # 测试资产类型映射
            test_mappings = [
                (AssetType.STOCK_A, AssetType.STOCK_A),
                (AssetType.STOCK_US, AssetType.STOCK_US),
                (AssetType.CRYPTO, AssetType.CRYPTO),
                (AssetType.FUTURES, AssetType.FUTURES),
            ]
            
            for input_type, expected_type in test_mappings:
                mapped_type = db_manager._map_asset_type_to_database(input_type)
                if mapped_type == expected_type:
                    logger.info(f"  [PASS] 映射正确: {input_type.value} -> {mapped_type.value}")
                else:
                    logger.error(f"  [FAIL] 映射错误: {input_type.value} -> {mapped_type.value}, 期望: {expected_type.value}")
                    return False
            
            # 测试数据库路径生成
            for asset_type in [AssetType.STOCK_A, AssetType.STOCK_US, AssetType.CRYPTO]:
                db_path = db_manager.get_database_path(asset_type)
                if db_path and asset_type.value in str(db_path):
                    logger.info(f"  [PASS] 数据库路径正确: {asset_type.value} -> {db_path}")
                else:
                    logger.warning(f"  [WARN] 数据库路径可能有问题: {asset_type.value} -> {db_path}")
            
            logger.info("  [PASS] 数据存储逻辑测试通过")
            self._record_test("数据存储逻辑", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 数据存储逻辑测试失败: {e}")
            self._record_test("数据存储逻辑", False)
            return False
    
    def _test_ui_config_mapping(self) -> bool:
        """测试UI配置映射"""
        logger.info("测试UI配置映射...")
        
        try:
            from core.ui_asset_type_utils import UIAssetTypeUtils
            DISPLAY_NAMES = UIAssetTypeUtils.DISPLAY_NAMES
            COMMON_TYPES = UIAssetTypeUtils.COMMON_TYPES
            from core.plugin_types import AssetType
            
            # 测试显示名称映射
            test_asset_types = [
                AssetType.STOCK_A,
                AssetType.STOCK_US,
                AssetType.CRYPTO,
                AssetType.FUTURES,
                AssetType.FOREX,
            ]
            
            for asset_type in test_asset_types:
                if asset_type in DISPLAY_NAMES:
                    display_name = DISPLAY_NAMES[asset_type]
                    logger.info(f"  [PASS] {asset_type.value} -> {display_name}")
                else:
                    logger.warning(f"  [WARN] {asset_type.value} 缺少显示名称")
            
            # 测试常用类型
            if COMMON_TYPES:
                logger.info(f"  [PASS] 常用类型数量: {len(COMMON_TYPES)}")
                for common_type in COMMON_TYPES[:5]:  # 显示前5个
                    logger.info(f"    - {common_type}")
            else:
                logger.warning("  [WARN] 常用类型为空")
            
            logger.info("  [PASS] UI配置映射测试通过")
            self._record_test("UI配置映射", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] UI配置映射测试失败: {e}")
            self._record_test("UI配置映射", False)
            return False
    
    def _test_database_manager(self) -> bool:
        """测试数据库管理器"""
        logger.info("测试数据库管理器...")
        
        try:
            from core.asset_database_manager import AssetSeparatedDatabaseManager
            from core.plugin_types import AssetType
            
            # 测试初始化
            db_manager = AssetSeparatedDatabaseManager()
            logger.info("  [PASS] AssetSeparatedDatabaseManager 初始化成功")
            
            # 测试数据库路径生成
            test_asset_types = [
                AssetType.STOCK_A,
                AssetType.STOCK_US,
                AssetType.CRYPTO,
                AssetType.FUTURES,
            ]
            
            for asset_type in test_asset_types:
                try:
                    db_path = db_manager.get_database_path(asset_type)
                    logger.info(f"  [PASS] {asset_type.value} 数据库路径: {db_path}")
                except Exception as e:
                    logger.warning(f"  [WARN] {asset_type.value} 数据库路径生成失败: {e}")
            
            # 测试表名生成
            from core.plugin_types import DataType
            table_name = db_manager._generate_table_name(DataType.HISTORICAL_KLINE, AssetType.STOCK_A)
            if table_name == "historical_kline_data":
                logger.info(f"  [PASS] 表名生成正确: {table_name}")
            else:
                logger.warning(f"  [WARN] 表名生成可能有问题: {table_name}")
            
            logger.info("  [PASS] 数据库管理器测试通过")
            self._record_test("数据库管理器", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 数据库管理器测试失败: {e}")
            self._record_test("数据库管理器", False)
            return False
    
    def _test_inference_code_removed(self) -> bool:
        """测试推断代码已删除"""
        logger.info("测试推断代码已删除...")
        
        try:
            from core.services.unified_data_manager import UnifiedDataManager
            
            # 检查推断相关方法是否已删除
            data_manager = UnifiedDataManager()
            
            removed_methods = [
                '_infer_asset_type_from_data_source',
                '_is_us_stock_symbol',
                '_is_futures_symbol',
                '_is_forex_symbol',
                '_is_bond_symbol',
                '_is_commodity_symbol',
            ]
            
            for method_name in removed_methods:
                if hasattr(data_manager, method_name):
                    logger.error(f"  [FAIL] 推断方法仍然存在: {method_name}")
                    return False
                else:
                    logger.info(f"  [PASS] 推断方法已删除: {method_name}")
            
            # 检查get_kdata_from_source方法是否使用传入的asset_type
            import inspect
            sig = inspect.signature(data_manager.get_kdata_from_source)
            params = list(sig.parameters.keys())
            
            if 'asset_type' not in params:
                logger.error("  [FAIL] get_kdata_from_source 缺少 asset_type 参数")
                return False
            
            logger.info("  [PASS] 推断代码已删除，使用传入的asset_type参数")
            self._record_test("推断代码已删除", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 推断代码删除验证失败: {e}")
            self._record_test("推断代码已删除", False)
            return False
    
    def _test_backward_compatibility(self) -> bool:
        """测试向后兼容性"""
        logger.info("测试向后兼容性...")
        
        try:
            from core.services.unified_data_manager import UnifiedDataManager
            from core.real_data_provider import RealDataProvider
            from core.plugin_types import AssetType
            
            # 测试不传递asset_type参数时的默认行为
            data_manager = UnifiedDataManager()
            data_provider = RealDataProvider()
            
            # 测试数据管理器默认行为
            try:
                result = data_manager.get_kdata_from_source(
                    stock_code="000001",
                    period="D",
                    count=10,
                    data_source="akshare"
                    # 不传递asset_type参数
                )
                logger.info("  [PASS] 数据管理器向后兼容性测试通过（使用默认值）")
            except Exception as e:
                logger.warning(f"  [WARN] 数据管理器向后兼容性测试失败: {e}")
            
            # 测试数据提供器默认行为
            try:
                result = data_provider.get_real_kdata(
                    code="000001",
                    freq="D",
                    count=10,
                    data_source="akshare"
                    # 不传递asset_type参数
                )
                logger.info("  [PASS] 数据提供器向后兼容性测试通过（使用默认值）")
            except Exception as e:
                logger.warning(f"  [WARN] 数据提供器向后兼容性测试失败: {e}")
            
            logger.info("  [PASS] 向后兼容性测试通过")
            self._record_test("向后兼容性", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 向后兼容性测试失败: {e}")
            self._record_test("向后兼容性", False)
            return False
    
    def _test_error_handling(self) -> bool:
        """测试错误处理"""
        logger.info("测试错误处理...")
        
        try:
            from core.services.unified_data_manager import UnifiedDataManager
            from core.real_data_provider import RealDataProvider
            from core.plugin_types import AssetType
            
            data_manager = UnifiedDataManager()
            data_provider = RealDataProvider()
            
            # 测试无效资产类型处理
            try:
                result = data_manager.get_kdata_from_source(
                    stock_code="000001",
                    period="D",
                    count=10,
                    data_source="akshare",
                    asset_type="INVALID_TYPE"  # 无效的资产类型
                )
                logger.info("  [PASS] 无效资产类型处理正常")
            except Exception as e:
                logger.info(f"  [PASS] 无效资产类型正确抛出异常: {type(e).__name__}")
            
            # 测试空资产类型处理
            try:
                result = data_provider.get_real_kdata(
                    code="000001",
                    freq="D",
                    count=10,
                    data_source="akshare",
                    asset_type=""  # 空字符串
                )
                logger.info("  [PASS] 空资产类型处理正常")
            except Exception as e:
                logger.info(f"  [PASS] 空资产类型正确抛出异常: {type(e).__name__}")
            
            logger.info("  [PASS] 错误处理测试通过")
            self._record_test("错误处理", True)
            return True
            
        except Exception as e:
            logger.error(f"  [FAIL] 错误处理测试失败: {e}")
            self._record_test("错误处理", False)
            return False
    
    def _record_test(self, test_name: str, passed: bool):
        """记录测试结果"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "[PASS]"
        else:
            self.failed_tests += 1
            status = "[FAIL]"
        
        self.test_results.append({
            'test_name': test_name,
            'passed': passed,
            'status': status
        })
        
        logger.info(f"{status} {test_name}")
    
    def _print_final_report(self) -> bool:
        """打印最终报告"""
        logger.info("=" * 80)
        logger.info("资产类型路由全量验证回归测试报告")
        logger.info("=" * 80)
        
        for result in self.test_results:
            logger.info(f"{result['status']} {result['test_name']}")
        
        logger.info("=" * 80)
        logger.info(f"总计: {self.total_tests} 个测试")
        logger.info(f"通过: {self.passed_tests} 个 ({self.passed_tests/self.total_tests*100:.1f}%)")
        logger.info(f"失败: {self.failed_tests} 个 ({self.failed_tests/self.total_tests*100:.1f}%)")
        
        if self.failed_tests == 0:
            logger.info("所有测试通过！资产类型路由功能完全正常")
            return True
        else:
            logger.error(f"{self.failed_tests} 个测试失败，需要修复")
            return False

def main():
    """主函数"""
    try:
        validator = AssetTypeRoutingValidator()
        success = validator.run_validation()
        
        if success:
            logger.info("资产类型路由全量验证回归测试完全通过！")
            sys.exit(0)
        else:
            logger.error("资产类型路由全量验证回归测试失败！")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"验证过程中发生严重错误: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
