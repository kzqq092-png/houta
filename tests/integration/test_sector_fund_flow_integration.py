#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
板块资金流功能集成测试

此测试套件验证板块资金流功能的端到端工作流程，包括：
1. API→服务→数据库→缓存的完整数据流
2. SectorDataService与TET管道的集成
3. 缓存系统的集成测试
4. 数据库存储和查询功能
5. API端点的完整响应测试
6. 错误处理和故障恢复

测试覆盖范围：
- 板块资金流排行榜查询
- 板块历史趋势数据获取
- 板块分时资金流数据查询
- 历史数据导入功能
- 缓存命中和失效机制
- 数据库表结构和索引
- API响应格式和错误处理
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import threading
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
from fastapi.testclient import TestClient
from fastapi import HTTPException

# 导入待测试的组件
from core.services.unified_data_manager import UnifiedDataManager, get_unified_data_manager
from core.services.sector_data_service import SectorDataService, SectorCacheKeys, get_sector_data_service
from core.performance.cache_manager import MultiLevelCacheManager
from core.tet_data_pipeline import TETDataPipeline, StandardQuery, StandardData
from core.plugin_types import AssetType, DataType
from core.database.table_manager import TableType, get_table_manager
from core.database.duckdb_manager import initialize_duckdb_manager
from api_server import app  # 导入FastAPI应用


class TestSectorFundFlowIntegration(unittest.TestCase):
    """板块资金流功能集成测试类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.test_data_dir = tempfile.mkdtemp(prefix='sector_test_')
        cls.test_client = TestClient(app)

        # 创建模拟的测试数据
        cls.sample_sector_data = pd.DataFrame({
            'sector_id': ['BK0001', 'BK0002', 'BK0003'],
            'sector_name': ['房地产', '银行', '钢铁'],
            'main_net_inflow': [1000000, 800000, -500000],
            'super_large_inflow': [500000, 400000, -200000],
            'super_large_outflow': [300000, 200000, -300000],
            'large_inflow': [300000, 250000, -150000],
            'large_outflow': [200000, 150000, -200000],
            'medium_inflow': [150000, 100000, -100000],
            'medium_outflow': [100000, 80000, -150000],
            'small_inflow': [50000, 50000, -50000],
            'small_outflow': [30000, 20000, -80000],
            'stock_count': [25, 30, 15],
            'avg_change_percent': [2.5, 1.8, -3.2],
            'turnover_rate': [0.05, 0.03, 0.02],
            'ranking': [1, 2, 3],
            'trade_date': ['2024-01-01', '2024-01-01', '2024-01-01']
        })

        cls.sample_intraday_data = pd.DataFrame({
            'sector_id': ['BK0001'] * 5,
            'sector_name': ['房地产'] * 5,
            'trade_date': ['2024-01-01'] * 5,
            'trade_time': ['09:30:00', '10:00:00', '10:30:00', '11:00:00', '11:30:00'],
            'net_inflow': [100000, 150000, 120000, 80000, 200000],
            'cumulative_inflow': [100000, 250000, 370000, 450000, 650000]
        })

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        import shutil
        if os.path.exists(cls.test_data_dir):
            shutil.rmtree(cls.test_data_dir)

    def setUp(self):
        """每个测试方法的初始化"""
        self.mock_cache_manager = Mock(spec=MultiLevelCacheManager)
        self.mock_tet_pipeline = Mock(spec=TETDataPipeline)
        self.mock_db_connector = Mock()
        self.mock_table_manager = Mock()

        # 重置模拟对象
        self.mock_cache_manager.reset_mock()
        self.mock_tet_pipeline.reset_mock()
        self.mock_db_connector.reset_mock()
        self.mock_table_manager.reset_mock()

    def tearDown(self):
        """每个测试方法的清理"""
        pass

    def test_sector_data_service_initialization(self):
        """测试板块数据服务初始化"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.initialize_duckdb_manager', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            self.assertIsNotNone(service)
            self.assertEqual(service.cache_manager, self.mock_cache_manager)
            self.assertEqual(service.tet_pipeline, self.mock_tet_pipeline)
            self.assertEqual(service.db_connector, self.mock_db_connector)
            self.assertEqual(service.table_manager, self.mock_table_manager)

    def test_sector_fund_flow_ranking_with_cache_hit(self):
        """测试板块资金流排行榜查询 - 缓存命中"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.initialize_duckdb_manager', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟缓存命中
            cache_key = SectorCacheKeys.get_ranking_key(datetime.now().strftime("%Y-%m-%d"), "main_net_inflow")
            self.mock_cache_manager.get.return_value = self.sample_sector_data

            result = service.get_sector_fund_flow_ranking(date_range="today", sort_by="main_net_inflow")

            # 验证缓存被调用
            self.mock_cache_manager.get.assert_called_once_with(cache_key)
            # 验证TET管道没有被调用（因为缓存命中）
            self.mock_tet_pipeline.process.assert_not_called()
            # 验证返回的数据
            pd.testing.assert_frame_equal(result, self.sample_sector_data)

    def test_sector_fund_flow_ranking_with_cache_miss(self):
        """测试板块资金流排行榜查询 - 缓存未命中，通过TET管道获取"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.initialize_duckdb_manager', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟缓存未命中
            self.mock_cache_manager.get.return_value = None

            # 模拟TET管道返回数据
            mock_standard_data = Mock(spec=StandardData)
            mock_standard_data.data = self.sample_sector_data
            self.mock_tet_pipeline.process.return_value = mock_standard_data

            result = service.get_sector_fund_flow_ranking(date_range="today", sort_by="main_net_inflow")

            # 验证缓存被查询
            self.mock_cache_manager.get.assert_called_once()
            # 验证TET管道被调用
            self.mock_tet_pipeline.process.assert_called_once()
            # 验证数据被缓存
            self.mock_cache_manager.set.assert_called_once()
            # 验证返回的数据
            pd.testing.assert_frame_equal(result, self.sample_sector_data)

    def test_sector_fund_flow_ranking_with_tet_failure_fallback_to_db(self):
        """测试板块资金流排行榜查询 - TET管道失败，回退到数据库查询"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.initialize_duckdb_manager', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟缓存未命中
            self.mock_cache_manager.get.return_value = None

            # 模拟TET管道失败
            self.mock_tet_pipeline.process.side_effect = Exception("TET pipeline error")

            # 模拟表结构存在
            mock_table_schema = Mock()
            mock_table_schema.table_type.value = "sector_fund_flow_daily"
            self.mock_table_manager.get_schema.return_value = mock_table_schema

            # 模拟数据库查询返回数据
            self.mock_db_connector.query_dataframe.return_value = self.sample_sector_data

            result = service.get_sector_fund_flow_ranking(date_range="today", sort_by="main_net_inflow")

            # 验证TET管道被调用并失败
            self.mock_tet_pipeline.process.assert_called_once()
            # 验证数据库查询被调用
            self.mock_db_connector.query_dataframe.assert_called_once()
            # 验证返回的数据
            pd.testing.assert_frame_equal(result, self.sample_sector_data)

    def test_sector_historical_trend_query(self):
        """测试板块历史趋势数据查询"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.initialize_duckdb_manager', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟缓存未命中
            self.mock_cache_manager.get.return_value = None

            # 模拟TET管道返回历史数据
            historical_data = self.sample_sector_data[self.sample_sector_data['sector_id'] == 'BK0001'].copy()
            mock_standard_data = Mock(spec=StandardData)
            mock_standard_data.data = historical_data
            self.mock_tet_pipeline.process.return_value = mock_standard_data

            result = service.get_sector_historical_trend(sector_id="BK0001", period=30)

            # 验证TET管道被调用
            self.mock_tet_pipeline.process.assert_called_once()
            call_args = self.mock_tet_pipeline.process.call_args[0][0]
            self.assertEqual(call_args.symbol, "BK0001")
            self.assertEqual(call_args.asset_type, AssetType.SECTOR)
            self.assertEqual(call_args.data_type, DataType.SECTOR_FUND_FLOW)

            # 验证缓存被设置
            self.mock_cache_manager.set.assert_called_once()

            # 验证返回数据
            pd.testing.assert_frame_equal(result, historical_data)

    def test_sector_intraday_flow_query(self):
        """测试板块分时资金流数据查询"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.initialize_duckdb_manager', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟缓存未命中
            self.mock_cache_manager.get.return_value = None

            # 模拟TET管道返回分时数据
            mock_standard_data = Mock(spec=StandardData)
            mock_standard_data.data = self.sample_intraday_data
            self.mock_tet_pipeline.process.return_value = mock_standard_data

            result = service.get_sector_intraday_flow(sector_id="BK0001", date="2024-01-01")

            # 验证TET管道被调用
            self.mock_tet_pipeline.process.assert_called_once()
            call_args = self.mock_tet_pipeline.process.call_args[0][0]
            self.assertEqual(call_args.symbol, "BK0001")
            self.assertEqual(call_args.start_date, "2024-01-01")
            self.assertEqual(call_args.end_date, "2024-01-01")
            self.assertEqual(call_args.period, "1m")

            # 验证返回数据
            pd.testing.assert_frame_equal(result, self.sample_intraday_data)

    def test_import_sector_historical_data_success(self):
        """测试板块历史数据导入成功"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.initialize_duckdb_manager', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟TET管道返回导入数据
            mock_standard_data = Mock(spec=StandardData)
            mock_standard_data.data = self.sample_sector_data
            self.mock_tet_pipeline.process.return_value = mock_standard_data

            # 模拟表结构存在
            mock_table_schema = Mock()
            mock_table_schema.table_type.value = "sector_fund_flow_daily"
            self.mock_table_manager.get_schema.return_value = mock_table_schema

            # 模拟数据库插入成功
            self.mock_db_connector.insert_dataframe.return_value = len(self.sample_sector_data)

            result = service.import_sector_historical_data(
                source="akshare",
                start_date="2024-01-01",
                end_date="2024-01-31"
            )

            # 验证TET管道被调用
            self.mock_tet_pipeline.process.assert_called_once()
            # 验证数据库插入被调用
            self.mock_db_connector.insert_dataframe.assert_called_once()
            # 验证缓存被清理
            self.mock_cache_manager.delete_pattern.assert_called()
            # 验证返回结果
            self.assertTrue(result['success'])
            self.assertEqual(result['processed_count'], len(self.sample_sector_data))

    def test_import_sector_historical_data_failure(self):
        """测试板块历史数据导入失败"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.initialize_duckdb_manager', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟TET管道失败
            self.mock_tet_pipeline.process.side_effect = Exception("Import error")

            result = service.import_sector_historical_data(
                source="akshare",
                start_date="2024-01-01",
                end_date="2024-01-31"
            )

            # 验证TET管道被调用
            self.mock_tet_pipeline.process.assert_called_once()
            # 验证返回结果
            self.assertFalse(result['success'])
            self.assertEqual(result['processed_count'], 0)
            self.assertIn('error', result)

    @patch('api_server.data_manager')
    def test_api_sector_fund_flow_ranking_success(self, mock_data_manager):
        """测试板块资金流排行榜API成功响应"""
        # 模拟SectorDataService
        mock_sector_service = Mock(spec=SectorDataService)
        mock_sector_service.get_sector_fund_flow_ranking.return_value = self.sample_sector_data
        mock_data_manager.get_sector_fund_flow_service.return_value = mock_sector_service

        # 调用API
        response = self.test_client.get("/api/sector/fund-flow/ranking?date_range=today&sort_by=main_net_inflow")

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['count'], len(self.sample_sector_data))
        self.assertIn('data', data)
        self.assertEqual(len(data['data']), len(self.sample_sector_data))

    @patch('api_server.data_manager')
    def test_api_sector_fund_flow_ranking_service_unavailable(self, mock_data_manager):
        """测试板块资金流排行榜API服务不可用"""
        # 模拟服务不可用
        mock_data_manager.get_sector_fund_flow_service.return_value = None

        # 调用API
        response = self.test_client.get("/api/sector/fund-flow/ranking")

        # 验证响应
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertIn("板块数据服务不可用", data['detail'])

    @patch('api_server.data_manager')
    def test_api_sector_historical_trend_success(self, mock_data_manager):
        """测试板块历史趋势API成功响应"""
        # 模拟SectorDataService
        mock_sector_service = Mock(spec=SectorDataService)
        trend_data = self.sample_sector_data[self.sample_sector_data['sector_id'] == 'BK0001']
        mock_sector_service.get_sector_historical_trend.return_value = trend_data
        mock_data_manager.get_sector_fund_flow_service.return_value = mock_sector_service

        # 调用API
        response = self.test_client.get("/api/sector/fund-flow/trend/BK0001?period=30")

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertEqual(data['params']['sector_id'], 'BK0001')
        self.assertEqual(data['params']['period'], 30)

    @patch('api_server.data_manager')
    def test_api_sector_intraday_flow_success(self, mock_data_manager):
        """测试板块分时资金流API成功响应"""
        # 模拟SectorDataService
        mock_sector_service = Mock(spec=SectorDataService)
        mock_sector_service.get_sector_intraday_flow.return_value = self.sample_intraday_data
        mock_data_manager.get_sector_fund_flow_service.return_value = mock_sector_service

        # 调用API
        response = self.test_client.get("/api/sector/fund-flow/intraday/BK0001?date=2024-01-01")

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertEqual(data['params']['sector_id'], 'BK0001')
        self.assertEqual(data['params']['date'], '2024-01-01')

    @patch('api_server.data_manager')
    def test_api_sector_intraday_flow_invalid_date_format(self, mock_data_manager):
        """测试板块分时资金流API无效日期格式"""
        # 调用API with invalid date
        response = self.test_client.get("/api/sector/fund-flow/intraday/BK0001?date=invalid-date")

        # 验证响应
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("日期格式错误", data['detail'])

    @patch('api_server.data_manager')
    def test_api_import_sector_historical_data_success(self, mock_data_manager):
        """测试板块历史数据导入API成功"""
        # 模拟SectorDataService
        mock_sector_service = Mock(spec=SectorDataService)
        mock_sector_service.import_sector_historical_data.return_value = {
            'success': True,
            'processed_count': 100,
            'message': '导入成功'
        }
        mock_data_manager.get_sector_fund_flow_service.return_value = mock_sector_service

        # 调用API
        payload = {
            'source': 'akshare',
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        response = self.test_client.post("/api/sector/fund-flow/import", json=payload)

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['processed_count'], 100)

    @patch('api_server.data_manager')
    def test_api_import_sector_historical_data_missing_params(self, mock_data_manager):
        """测试板块历史数据导入API缺少参数"""
        # 调用API with missing parameters
        payload = {
            'source': 'akshare'
            # missing start_date and end_date
        }
        response = self.test_client.post("/api/sector/fund-flow/import", json=payload)

        # 验证响应
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("缺少必要参数", data['detail'])

    @patch('api_server.data_manager')
    def test_api_sector_service_status_available(self, mock_data_manager):
        """测试板块服务状态API - 服务可用"""
        # 模拟服务可用
        mock_sector_service = Mock(spec=SectorDataService)
        mock_data_manager.get_sector_fund_flow_service.return_value = mock_sector_service

        # 调用API
        response = self.test_client.get("/api/sector/fund-flow/status")

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'available')
        self.assertEqual(data['service_type'], 'SectorDataService')

    @patch('api_server.data_manager')
    def test_api_sector_service_status_unavailable(self, mock_data_manager):
        """测试板块服务状态API - 服务不可用"""
        # 模拟服务不可用
        mock_data_manager.get_sector_fund_flow_service.return_value = None

        # 调用API
        response = self.test_client.get("/api/sector/fund-flow/status")

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'unavailable')
        self.assertIn("板块数据服务不可用", data['message'])

    def test_cache_key_generation(self):
        """测试缓存键生成的一致性"""
        # 测试排行榜缓存键
        key1 = SectorCacheKeys.get_ranking_key("2024-01-01", "main_net_inflow")
        key2 = SectorCacheKeys.get_ranking_key("2024-01-01", "main_net_inflow")
        self.assertEqual(key1, key2)

        # 测试趋势缓存键
        trend_key1 = SectorCacheKeys.get_trend_key("BK0001", 30)
        trend_key2 = SectorCacheKeys.get_trend_key("BK0001", 30)
        self.assertEqual(trend_key1, trend_key2)

        # 测试分时缓存键
        intraday_key1 = SectorCacheKeys.get_intraday_key("BK0001", "2024-01-01")
        intraday_key2 = SectorCacheKeys.get_intraday_key("BK0001", "2024-01-01")
        self.assertEqual(intraday_key1, intraday_key2)

        # 测试不同参数生成不同键
        key_different = SectorCacheKeys.get_ranking_key("2024-01-02", "main_net_inflow")
        self.assertNotEqual(key1, key_different)

    def test_end_to_end_workflow(self):
        """测试端到端工作流程"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.initialize_duckdb_manager', return_value=self.mock_db_connector), \
                patch('api_server.data_manager') as mock_data_manager:

            # 创建真实的SectorDataService实例
            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)
            mock_data_manager.get_sector_fund_flow_service.return_value = service

            # 设置模拟数据
            self.mock_cache_manager.get.return_value = None  # 缓存未命中
            mock_standard_data = Mock(spec=StandardData)
            mock_standard_data.data = self.sample_sector_data
            self.mock_tet_pipeline.process.return_value = mock_standard_data

            # 执行端到端测试：API调用 → 服务 → TET管道 → 缓存设置
            response = self.test_client.get("/api/sector/fund-flow/ranking?date_range=today&sort_by=main_net_inflow")

            # 验证响应正确
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['count'], len(self.sample_sector_data))

            # 验证完整的调用链
            self.mock_cache_manager.get.assert_called_once()  # 缓存查询
            self.mock_tet_pipeline.process.assert_called_once()  # TET管道处理
            self.mock_cache_manager.set.assert_called_once()  # 缓存设置


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
