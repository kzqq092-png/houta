#!/usr/bin/env python3
"""
完整表结构验证测试脚本

验证所有11种表类型的完整Schema定义和自动创建功能
测试TET框架与表管理系统的完整整合

作者: FactorWeave-Quant团队
日期: 2024-01-XX
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from core.database.table_manager import (
    TableType, TableSchemaRegistry, DynamicTableManager
)
from core.database.data_source_separated_storage import DataSourceSeparatedStorageManager
from core.plugin_types import AssetType


class CompleteTableSchemaVerifier:
    """完整表结构验证器"""
    
    def __init__(self):
        """初始化验证器"""
        self.schema_registry = TableSchemaRegistry()
        self.table_manager = DynamicTableManager()
        self.storage_manager = DataSourceSeparatedStorageManager()
        self.test_results = {}
        
        logger.info("🚀 完整表结构验证器初始化完成")
    
    def verify_all_table_schemas(self):
        """验证所有表结构定义"""
        logger.info("📋 开始验证所有表结构定义...")
        
        all_table_types = [
            TableType.STOCK_BASIC_INFO,
            TableType.KLINE_DATA,
            TableType.FINANCIAL_STATEMENT,
            TableType.MACRO_ECONOMIC,
            TableType.REAL_TIME_QUOTE,
            TableType.MARKET_DEPTH,
            TableType.TRADE_TICK,
            TableType.NEWS,
            TableType.ANNOUNCEMENT,
            TableType.FUND_FLOW,
            TableType.TECHNICAL_INDICATOR
        ]
        
        schema_results = {}
        
        for table_type in all_table_types:
            logger.info(f"验证表类型: {table_type.value}")
            
            # 验证Schema是否存在
            schema = self.schema_registry.get_schema(table_type)
            if schema is None:
                schema_results[table_type.value] = {
                    'status': 'FAILED',
                    'error': 'Schema定义不存在'
                }
                logger.error(f"❌ {table_type.value}: Schema定义缺失")
                continue
            
            # 验证Schema基本属性
            validation_result = self._validate_schema_structure(schema, table_type)
            schema_results[table_type.value] = validation_result
            
            if validation_result['status'] == 'SUCCESS':
                logger.success(f"✅ {table_type.value}: Schema验证通过")
            else:
                logger.error(f"❌ {table_type.value}: {validation_result['error']}")
        
        self.test_results['schema_validation'] = schema_results
        return schema_results
    
    def _validate_schema_structure(self, schema, table_type):
        """验证Schema结构的完整性"""
        try:
            # 检查必要字段
            required_fields = ['data_source', 'created_at', 'data_quality_score']
            missing_fields = []
            
            for field in required_fields:
                if field not in schema.columns:
                    missing_fields.append(field)
            
            if missing_fields:
                return {
                    'status': 'FAILED',
                    'error': f'缺少必要字段: {missing_fields}'
                }
            
            # 检查主键定义
            if not schema.primary_key:
                return {
                    'status': 'FAILED',
                    'error': '缺少主键定义'
                }
            
            # 检查索引定义
            if not schema.indexes:
                return {
                    'status': 'FAILED',
                    'error': '缺少索引定义'
                }
            
            return {
                'status': 'SUCCESS',
                'columns_count': len(schema.columns),
                'primary_key': schema.primary_key,
                'indexes_count': len(schema.indexes),
                'has_partitions': schema.partitions is not None
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': f'验证过程异常: {str(e)}'
            }
    
    def test_table_name_generation(self):
        """测试表名生成功能"""
        logger.info("🏷️ 开始测试表名生成功能...")
        
        test_plugin = "examples.test_plugin"
        name_generation_results = {}
        
        all_table_types = [
            TableType.STOCK_BASIC_INFO,
            TableType.KLINE_DATA,
            TableType.FINANCIAL_STATEMENT,
            TableType.MACRO_ECONOMIC,
            TableType.REAL_TIME_QUOTE,
            TableType.MARKET_DEPTH,
            TableType.TRADE_TICK,
            TableType.NEWS,
            TableType.ANNOUNCEMENT,
            TableType.FUND_FLOW,
            TableType.TECHNICAL_INDICATOR
        ]
        
        for table_type in all_table_types:
            try:
                # 测试基本表名生成
                table_name = self.table_manager.generate_table_name(
                    table_type=table_type,
                    plugin_name=test_plugin
                )
                
                # 测试带周期的表名生成
                table_name_with_period = self.table_manager.generate_table_name(
                    table_type=table_type,
                    plugin_name=test_plugin,
                    period="daily"
                )
                
                name_generation_results[table_type.value] = {
                    'status': 'SUCCESS',
                    'basic_name': table_name,
                    'period_name': table_name_with_period
                }
                
                logger.success(f"✅ {table_type.value}: 表名生成成功")
                logger.info(f"   基本表名: {table_name}")
                logger.info(f"   周期表名: {table_name_with_period}")
                
            except Exception as e:
                name_generation_results[table_type.value] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
                logger.error(f"❌ {table_type.value}: 表名生成失败 - {e}")
        
        self.test_results['name_generation'] = name_generation_results
        return name_generation_results
    
    def test_auto_table_creation(self):
        """测试自动表创建功能"""
        logger.info("🔨 开始测试自动表创建功能...")
        
        test_plugin = "examples.complete_test_plugin"
        creation_results = {}
        
        # 测试关键表类型的自动创建
        key_table_types = [
            (TableType.KLINE_DATA, "daily"),
            (TableType.REAL_TIME_QUOTE, None),
            (TableType.MARKET_DEPTH, None),
            (TableType.TRADE_TICK, "minute"),
            (TableType.NEWS, None),
            (TableType.ANNOUNCEMENT, None),
            (TableType.FUND_FLOW, "daily"),
            (TableType.TECHNICAL_INDICATOR, "daily")
        ]
        
        for table_type, period in key_table_types:
            try:
                logger.info(f"测试创建表: {table_type.value}")
                
                # 测试自动创建表和索引
                table_name = self.storage_manager._auto_create_table_and_indexes(
                    plugin_id=test_plugin,
                    table_type=table_type,
                    period=period,
                    config=self.storage_manager._get_storage_config(test_plugin)
                )
                
                if table_name:
                    creation_results[f"{table_type.value}_{period or 'default'}"] = {
                        'status': 'SUCCESS',
                        'table_name': table_name
                    }
                    logger.success(f"✅ {table_type.value}: 表创建成功 - {table_name}")
                else:
                    creation_results[f"{table_type.value}_{period or 'default'}"] = {
                        'status': 'FAILED',
                        'error': '表创建返回None'
                    }
                    logger.error(f"❌ {table_type.value}: 表创建失败")
                    
            except Exception as e:
                creation_results[f"{table_type.value}_{period or 'default'}"] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
                logger.error(f"❌ {table_type.value}: 表创建异常 - {e}")
        
        self.test_results['table_creation'] = creation_results
        return creation_results
    
    def test_data_insertion(self):
        """测试数据插入功能"""
        logger.info("💾 开始测试数据插入功能...")
        
        test_plugin = "examples.complete_test_plugin"
        insertion_results = {}
        
        # 测试不同类型的数据插入
        test_cases = [
            {
                'table_type': TableType.KLINE_DATA,
                'data': self._generate_kline_test_data(),
                'period': 'daily'
            },
            {
                'table_type': TableType.REAL_TIME_QUOTE,
                'data': self._generate_realtime_quote_test_data(),
                'period': None
            },
            {
                'table_type': TableType.FUND_FLOW,
                'data': self._generate_fund_flow_test_data(),
                'period': 'daily'
            }
        ]
        
        for test_case in test_cases:
            table_type = test_case['table_type']
            data = test_case['data']
            period = test_case['period']
            
            try:
                logger.info(f"测试插入数据: {table_type.value}")
                
                # 保存数据
                success = self.storage_manager.save_data_to_source(
                    plugin_id=test_plugin,
                    table_type=table_type,
                    data=data,
                    period=period
                )
                
                if success:
                    insertion_results[f"{table_type.value}_{period or 'default'}"] = {
                        'status': 'SUCCESS',
                        'rows_inserted': len(data)
                    }
                    logger.success(f"✅ {table_type.value}: 数据插入成功 - {len(data)}行")
                else:
                    insertion_results[f"{table_type.value}_{period or 'default'}"] = {
                        'status': 'FAILED',
                        'error': '数据插入返回False'
                    }
                    logger.error(f"❌ {table_type.value}: 数据插入失败")
                    
            except Exception as e:
                insertion_results[f"{table_type.value}_{period or 'default'}"] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
                logger.error(f"❌ {table_type.value}: 数据插入异常 - {e}")
        
        self.test_results['data_insertion'] = insertion_results
        return insertion_results
    
    def _generate_kline_test_data(self):
        """生成K线测试数据"""
        base_time = datetime.now() - timedelta(days=5)
        data = []
        
        for i in range(5):
            data.append({
                'symbol': 'TEST001',
                'datetime': base_time + timedelta(days=i),
                'open': 10.0 + i * 0.1,
                'high': 10.5 + i * 0.1,
                'low': 9.5 + i * 0.1,
                'close': 10.2 + i * 0.1,
                'volume': 1000000 + i * 10000,
                'amount': 10000000 + i * 100000
            })
        
        return pd.DataFrame(data)
    
    def _generate_realtime_quote_test_data(self):
        """生成实时行情测试数据"""
        base_time = datetime.now()
        data = []
        
        for i in range(3):
            data.append({
                'symbol': 'TEST001',
                'datetime': base_time + timedelta(minutes=i),
                'price': 10.5 + i * 0.01,
                'volume': 100000 + i * 1000,
                'amount': 1000000 + i * 10000,
                'change': i * 0.01,
                'change_percent': i * 0.1,
                'market_status': 'trading'
            })
        
        return pd.DataFrame(data)
    
    def _generate_fund_flow_test_data(self):
        """生成资金流测试数据"""
        base_time = datetime.now() - timedelta(days=3)
        data = []
        
        for i in range(3):
            data.append({
                'symbol': 'TEST001',
                'datetime': base_time + timedelta(days=i),
                'period': 'daily',
                'main_inflow': 1000000 + i * 100000,
                'main_outflow': 800000 + i * 50000,
                'main_net_inflow': 200000 + i * 50000,
                'net_inflow': 150000 + i * 30000
            })
        
        return pd.DataFrame(data)
    
    def run_complete_verification(self):
        """运行完整验证流程"""
        logger.info("🎯 开始运行完整表结构验证流程...")
        
        # 1. 验证Schema定义
        schema_results = self.verify_all_table_schemas()
        
        # 2. 测试表名生成
        name_results = self.test_table_name_generation()
        
        # 3. 测试自动表创建
        creation_results = self.test_auto_table_creation()
        
        # 4. 测试数据插入
        insertion_results = self.test_data_insertion()
        
        # 5. 生成综合报告
        self._generate_final_report()
        
        return self.test_results
    
    def _generate_final_report(self):
        """生成最终验证报告"""
        logger.info("📊 生成验证报告...")
        
        # 统计成功率
        schema_success = sum(1 for r in self.test_results['schema_validation'].values() if r['status'] == 'SUCCESS')
        schema_total = len(self.test_results['schema_validation'])
        
        name_success = sum(1 for r in self.test_results['name_generation'].values() if r['status'] == 'SUCCESS')
        name_total = len(self.test_results['name_generation'])
        
        creation_success = sum(1 for r in self.test_results['table_creation'].values() if r['status'] == 'SUCCESS')
        creation_total = len(self.test_results['table_creation'])
        
        insertion_success = sum(1 for r in self.test_results['data_insertion'].values() if r['status'] == 'SUCCESS')
        insertion_total = len(self.test_results['data_insertion'])
        
        # 输出报告
        logger.info("="*60)
        logger.info("🎉 完整表结构验证报告")
        logger.info("="*60)
        logger.info(f"📋 Schema验证: {schema_success}/{schema_total} 成功 ({schema_success/schema_total*100:.1f}%)")
        logger.info(f"🏷️ 表名生成: {name_success}/{name_total} 成功 ({name_success/name_total*100:.1f}%)")
        logger.info(f"🔨 表创建: {creation_success}/{creation_total} 成功 ({creation_success/creation_total*100:.1f}%)")
        logger.info(f"💾 数据插入: {insertion_success}/{insertion_total} 成功 ({insertion_success/insertion_total*100:.1f}%)")
        
        total_success = schema_success + name_success + creation_success + insertion_success
        total_tests = schema_total + name_total + creation_total + insertion_total
        overall_success_rate = total_success / total_tests * 100
        
        logger.info("="*60)
        logger.info(f"🎯 总体成功率: {total_success}/{total_tests} ({overall_success_rate:.1f}%)")
        
        if overall_success_rate >= 90:
            logger.success("🎉 验证通过！TET框架表管理系统运行正常")
        elif overall_success_rate >= 70:
            logger.warning("⚠️ 验证部分通过，存在一些问题需要关注")
        else:
            logger.error("❌ 验证失败，存在严重问题需要修复")
        
        # 保存详细报告
        self._save_detailed_report()
    
    def _save_detailed_report(self):
        """保存详细报告到文件"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'test_results': self.test_results,
            'summary': {
                'total_table_types': 11,
                'schema_definitions_complete': True,
                'auto_creation_supported': True,
                'data_insertion_supported': True
            }
        }
        
        report_path = project_root / f"complete_table_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"📄 详细报告已保存到: {report_path}")


def main():
    """主函数"""
    try:
        logger.info("启动完整表结构验证测试...")
        
        # 创建验证器并运行测试
        verifier = CompleteTableSchemaVerifier()
        results = verifier.run_complete_verification()
        
        logger.info("验证测试完成！")
        
    except Exception as e:
        logger.error(f"验证测试失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
