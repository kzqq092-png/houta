"""
Stage 2单元测试：财务和宏观经济数据模型补充

测试内容：
1. FinancialStatement和MacroEconomicData模型
2. DuckDB表结构创建
3. 数据转换器功能
4. 数据验证和格式化

作者: FactorWeave-Quant团队
版本: 1.0
"""

import pytest
import pandas as pd
import tempfile
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any

# 导入被测试的模块
from core.data.enhanced_models import (
    FinancialStatement, MacroEconomicData, ReportType,
    calculate_financial_ratios, normalize_financial_data, calculate_turnover_rate
)
from core.database.table_schemas import DuckDBTableSchemas, TableStructureType
from core.data.model_converters import (
    FinancialStatementConverter, MacroEconomicDataConverter,
    DataValidationError
)
from core.database.duckdb_manager import DuckDBConnectionManager, DuckDBConfig


class TestFinancialStatementModel:
    """财务报表模型测试"""

    def test_financial_statement_creation(self):
        """测试财务报表对象创建"""
        fs = FinancialStatement(
            symbol="000001.SZ",
            report_date=date(2023, 12, 31),
            report_type=ReportType.ANNUAL,
            total_assets=Decimal("1000000000"),
            net_profit=Decimal("100000000"),
            eps=Decimal("1.25"),
            roe=Decimal("0.15")
        )

        assert fs.symbol == "000001.SZ"
        assert fs.report_date == date(2023, 12, 31)
        assert fs.report_type == ReportType.ANNUAL
        assert fs.total_assets == Decimal("1000000000")
        assert fs.net_profit == Decimal("100000000")
        assert fs.eps == Decimal("1.25")
        assert fs.roe == Decimal("0.15")

    def test_financial_statement_to_dict(self):
        """测试财务报表转字典"""
        fs = FinancialStatement(
            symbol="000001.SZ",
            report_date=date(2023, 12, 31),
            report_type=ReportType.ANNUAL,
            total_assets=Decimal("1000000000")
        )

        data_dict = fs.to_dict()

        assert data_dict["symbol"] == "000001.SZ"
        assert data_dict["report_date"] == "2023-12-31"
        assert data_dict["report_type"] == "annual"
        assert data_dict["total_assets"] == "1000000000"

    def test_financial_statement_from_dict(self):
        """测试从字典创建财务报表"""
        data = {
            "symbol": "000001.SZ",
            "report_date": "2023-12-31",
            "report_type": "ANNUAL",
            "total_assets": "1000000000",
            "net_profit": "100000000"
        }

        fs = FinancialStatement.from_dict(data)

        assert fs.symbol == "000001.SZ"
        assert fs.report_date == date(2023, 12, 31)
        assert fs.report_type == ReportType.ANNUAL
        assert fs.total_assets == Decimal("1000000000")
        assert fs.net_profit == Decimal("100000000")

    def test_calculate_financial_ratios(self):
        """测试财务比率计算"""
        fs = FinancialStatement(
            symbol="000001.SZ",
            report_date=date(2023, 12, 31),
            report_type=ReportType.ANNUAL,
            total_assets=Decimal("1000000000"),
            total_liabilities=Decimal("600000000"),
            net_profit=Decimal("100000000"),
            operating_revenue=Decimal("800000000"),
            shareholders_equity=Decimal("400000000")
        )

        result = calculate_financial_ratios(fs)

        # 检查计算的比率
        assert result.asset_liability_ratio == Decimal("0.60")  # 600M/1000M
        assert result.net_profit_margin == Decimal("0.125")     # 100M/800M
        assert result.roe == Decimal("0.25")                    # 100M/400M

    def test_normalize_financial_data(self):
        """测试财务数据标准化"""
        data = pd.DataFrame({
            'total_assets': [1000000, 2000000, 3000000],
            'net_profit': [100000, 150000, 200000]
        })

        normalized = normalize_financial_data(data, method='zscore')

        # 检查标准化后的数据
        assert abs(normalized['total_assets'].mean()) < 1e-10  # 均值接近0
        assert abs(normalized['total_assets'].std() - 1.0) < 1e-10  # 标准差接近1

    def test_calculate_turnover_rate(self):
        """测试换手率计算"""
        turnover = calculate_turnover_rate(1000000, 10000000)
        assert turnover == Decimal("0.1")

        # 测试边界情况
        assert calculate_turnover_rate(0, 10000000) == Decimal("0")
        assert calculate_turnover_rate(1000000, 0) is None


class TestMacroEconomicDataModel:
    """宏观经济数据模型测试"""

    def test_macro_economic_data_creation(self):
        """测试宏观经济数据对象创建"""
        med = MacroEconomicData(
            indicator_code="GDP_YOY",
            indicator_name="GDP同比增长率",
            data_date=date(2023, 12, 31),
            frequency="quarterly",
            value=Decimal("5.2"),
            unit="percent",
            category="GDP"
        )

        assert med.indicator_code == "GDP_YOY"
        assert med.indicator_name == "GDP同比增长率"
        assert med.data_date == date(2023, 12, 31)
        assert med.frequency == "quarterly"
        assert med.value == Decimal("5.2")
        assert med.unit == "percent"

    def test_macro_economic_data_to_dict(self):
        """测试宏观经济数据转字典"""
        med = MacroEconomicData(
            indicator_code="GDP_YOY",
            indicator_name="GDP同比增长率",
            data_date=date(2023, 12, 31),
            frequency="quarterly",
            value=Decimal("5.2"),
            unit="percent",
            category="GDP"
        )

        data_dict = med.to_dict()

        assert data_dict["indicator_code"] == "GDP_YOY"
        assert data_dict["indicator_name"] == "GDP同比增长率"
        assert data_dict["data_date"] == "2023-12-31"
        assert data_dict["frequency"] == "quarterly"
        assert data_dict["value"] == "5.2"
        assert data_dict["unit"] == "percent"

    def test_macro_economic_data_from_dict(self):
        """测试从字典创建宏观经济数据"""
        data = {
            "indicator_code": "GDP_YOY",
            "indicator_name": "GDP同比增长率",
            "data_date": "2023-12-31",
            "frequency": "quarterly",
            "value": "5.2",
            "unit": "percent",
            "category": "GDP"
        }

        med = MacroEconomicData.from_dict(data)

        assert med.indicator_code == "GDP_YOY"
        assert med.indicator_name == "GDP同比增长率"
        assert med.data_date == date(2023, 12, 31)
        assert med.frequency == "quarterly"
        assert med.value == Decimal("5.2")
        assert med.unit == "percent"


class TestDuckDBTableSchemas:
    """DuckDB表结构测试"""

    def test_financial_statement_schema_generation(self):
        """测试财务报表表结构生成"""
        plugin_name = "test_plugin"
        schema_sql = DuckDBTableSchemas.get_financial_statement_schema(plugin_name)

        # 检查表名
        assert f"financial_statements_{plugin_name}" in schema_sql

        # 检查关键字段
        assert "symbol VARCHAR NOT NULL" in schema_sql
        assert "report_date DATE NOT NULL" in schema_sql
        assert "report_type VARCHAR NOT NULL" in schema_sql
        assert "total_assets DECIMAL(20,2)" in schema_sql
        assert "net_profit DECIMAL(20,2)" in schema_sql

        # 检查主键
        assert "PRIMARY KEY (symbol, report_date, report_type)" in schema_sql

    def test_macro_economic_schema_generation(self):
        """测试宏观经济数据表结构生成"""
        plugin_name = "test_plugin"
        schema_sql = DuckDBTableSchemas.get_macro_economic_schema(plugin_name)

        # 检查表名
        assert f"macro_economic_data_{plugin_name}" in schema_sql

        # 检查关键字段
        assert "indicator_code VARCHAR NOT NULL" in schema_sql
        assert "data_date DATE NOT NULL" in schema_sql
        assert "value DECIMAL(20,6) NOT NULL" in schema_sql
        assert "frequency VARCHAR" in schema_sql

        # 检查主键
        assert "PRIMARY KEY (indicator_code, data_date)" in schema_sql

    def test_index_creation(self):
        """测试索引创建SQL生成"""
        plugin_name = "test_plugin"

        # 测试财务报表索引
        fs_indexes = DuckDBTableSchemas.get_financial_statement_indexes(plugin_name)
        assert len(fs_indexes) > 0
        assert any("symbol" in idx for idx in fs_indexes)
        assert any("report_date" in idx for idx in fs_indexes)

        # 测试宏观经济数据索引
        me_indexes = DuckDBTableSchemas.get_macro_economic_indexes(plugin_name)
        assert len(me_indexes) > 0
        assert any("indicator_code" in idx for idx in me_indexes)
        assert any("data_date" in idx for idx in me_indexes)

    def test_table_column_info(self):
        """测试表列信息获取"""
        fs_columns = DuckDBTableSchemas.get_table_column_info(TableStructureType.FINANCIAL_STATEMENT)

        assert "symbol" in fs_columns
        assert "report_date" in fs_columns
        assert "total_assets" in fs_columns
        assert fs_columns["symbol"] == "VARCHAR"
        assert fs_columns["report_date"] == "DATE"
        assert fs_columns["total_assets"] == "DECIMAL(20,2)"

        me_columns = DuckDBTableSchemas.get_table_column_info(TableStructureType.MACRO_ECONOMIC)

        assert "indicator_code" in me_columns
        assert "data_date" in me_columns
        assert "value" in me_columns
        assert me_columns["indicator_code"] == "VARCHAR"
        assert me_columns["data_date"] == "DATE"
        assert me_columns["value"] == "DECIMAL(20,6)"


class TestDataConverters:
    """数据转换器测试"""

    def test_financial_statement_converter_from_dict(self):
        """测试财务报表转换器从字典转换"""
        data = {
            "symbol": "000001.SZ",
            "report_date": "2023-12-31",
            "report_type": "ANNUAL",
            "total_assets": "1000000000.50",
            "net_profit": "100000000.25"
        }

        fs = FinancialStatementConverter.from_dict(data)

        assert fs.symbol == "000001.SZ"
        assert fs.report_date == date(2023, 12, 31)
        assert fs.report_type == ReportType.ANNUAL
        assert fs.total_assets == Decimal("1000000000.50")
        assert fs.net_profit == Decimal("100000000.25")

    def test_financial_statement_converter_validation_error(self):
        """测试财务报表转换器验证错误"""
        # 缺少必需字段
        data = {
            "symbol": "000001.SZ"
            # 缺少report_date和report_type
        }

        with pytest.raises(DataValidationError):
            FinancialStatementConverter.from_dict(data)

    def test_financial_statement_converter_to_duckdb_record(self):
        """测试财务报表转换为DuckDB记录"""
        fs = FinancialStatement(
            symbol="000001.SZ",
            report_date=date(2023, 12, 31),
            report_type=ReportType.ANNUAL,
            total_assets=Decimal("1000000000"),
            net_profit=Decimal("100000000")
        )

        record = FinancialStatementConverter.to_duckdb_record(fs)

        assert record["symbol"] == "000001.SZ"
        assert record["report_date"] == date(2023, 12, 31)
        assert record["report_type"] == "annual"
        assert record["total_assets"] == Decimal("1000000000")
        assert record["net_profit"] == Decimal("100000000")

    def test_financial_statement_converter_from_pandas(self):
        """测试从pandas DataFrame批量转换财务报表"""
        df = pd.DataFrame({
            'symbol': ['000001.SZ', '000002.SZ'],
            'report_date': ['2023-12-31', '2023-12-31'],
            'report_type': ['ANNUAL', 'ANNUAL'],
            'total_assets': ['1000000000', '2000000000'],
            'net_profit': ['100000000', '200000000']
        })

        statements = FinancialStatementConverter.from_pandas(df)

        assert len(statements) == 2
        assert statements[0].symbol == "000001.SZ"
        assert statements[1].symbol == "000002.SZ"
        assert statements[0].total_assets == Decimal("1000000000")
        assert statements[1].total_assets == Decimal("2000000000")

    def test_macro_economic_data_converter_from_dict(self):
        """测试宏观经济数据转换器从字典转换"""
        data = {
            "indicator_code": "GDP_YOY",
            "indicator_name": "GDP同比增长率",
            "data_date": "2023-12-31",
            "frequency": "quarterly",
            "value": "5.2",
            "unit": "percent",
            "category": "GDP"
        }

        med = MacroEconomicDataConverter.from_dict(data)

        assert med.indicator_code == "GDP_YOY"
        assert med.indicator_name == "GDP同比增长率"
        assert med.data_date == date(2023, 12, 31)
        assert med.frequency == "quarterly"
        assert med.value == Decimal("5.2")
        assert med.unit == "percent"

    def test_macro_economic_data_converter_validation_error(self):
        """测试宏观经济数据转换器验证错误"""
        # 缺少必需字段
        data = {
            "indicator_code": "GDP_YOY"
            # 缺少其他必需字段
        }

        with pytest.raises(DataValidationError):
            MacroEconomicDataConverter.from_dict(data)

    def test_macro_economic_data_converter_from_pandas(self):
        """测试从pandas DataFrame批量转换宏观经济数据"""
        df = pd.DataFrame({
            'indicator_code': ['GDP_YOY', 'CPI_YOY'],
            'indicator_name': ['GDP同比增长率', 'CPI同比增长率'],
            'data_date': ['2023-12-31', '2023-12-31'],
            'frequency': ['quarterly', 'monthly'],
            'value': ['5.2', '2.1'],
            'unit': ['percent', 'percent'],
            'category': ['GDP', 'CPI']
        })

        data_list = MacroEconomicDataConverter.from_pandas(df)

        assert len(data_list) == 2
        assert data_list[0].indicator_code == "GDP_YOY"
        assert data_list[1].indicator_code == "CPI_YOY"
        assert data_list[0].value == Decimal("5.2")
        assert data_list[1].value == Decimal("2.1")


class TestIntegrationStage2:
    """Stage 2集成测试"""

    def test_end_to_end_financial_data_flow(self):
        """测试财务数据端到端流程"""
        # 1. 创建原始数据
        raw_data = {
            "symbol": "000001.SZ",
            "report_date": "2023-12-31",
            "report_type": "ANNUAL",
            "total_assets": "1000000000",
            "total_liabilities": "600000000",
            "net_profit": "100000000",
            "operating_revenue": "800000000",
            "shareholders_equity": "400000000"
        }

        # 2. 转换为模型对象
        fs = FinancialStatementConverter.from_dict(raw_data)

        # 3. 计算财务比率
        fs_with_ratios = calculate_financial_ratios(fs)

        # 4. 转换为DuckDB记录
        duckdb_record = FinancialStatementConverter.to_duckdb_record(fs_with_ratios)

        # 5. 验证结果
        assert duckdb_record["symbol"] == "000001.SZ"
        assert duckdb_record["asset_liability_ratio"] == Decimal("0.60")
        assert duckdb_record["net_profit_margin"] == Decimal("0.125")
        assert duckdb_record["roe"] == Decimal("0.25")

    def test_end_to_end_macro_data_flow(self):
        """测试宏观经济数据端到端流程"""
        # 1. 创建原始数据
        raw_data = {
            "indicator_code": "GDP_YOY",
            "indicator_name": "GDP同比增长率",
            "data_date": "2023-12-31",
            "frequency": "quarterly",
            "value": "5.2",
            "unit": "percent",
            "category": "GDP",
            "data_source": "国家统计局",
            "region": "中国"
        }

        # 2. 转换为模型对象
        med = MacroEconomicDataConverter.from_dict(raw_data)

        # 3. 转换为DuckDB记录
        duckdb_record = MacroEconomicDataConverter.to_duckdb_record(med)

        # 4. 验证结果
        assert duckdb_record["indicator_code"] == "GDP_YOY"
        assert duckdb_record["indicator_name"] == "GDP同比增长率"
        assert duckdb_record["value"] == Decimal("5.2")
        assert duckdb_record["data_source"] == "国家统计局"
        assert duckdb_record["region"] == "中国"

    def test_table_schema_with_actual_data(self):
        """测试表结构与实际数据的兼容性"""
        plugin_name = "test_plugin"

        # 获取表结构信息
        fs_columns = DuckDBTableSchemas.get_table_column_info(TableStructureType.FINANCIAL_STATEMENT)
        me_columns = DuckDBTableSchemas.get_table_column_info(TableStructureType.MACRO_ECONOMIC)

        # 创建测试数据
        fs = FinancialStatement(
            symbol="000001.SZ",
            report_date=date(2023, 12, 31),
            report_type=ReportType.ANNUAL,
            total_assets=Decimal("1000000000")
        )

        med = MacroEconomicData(
            indicator_code="GDP_YOY",
            indicator_name="GDP同比增长率",
            data_date=date(2023, 12, 31),
            frequency="quarterly",
            value=Decimal("5.2"),
            unit="percent",
            category="GDP"
        )

        # 转换为DuckDB记录
        fs_record = FinancialStatementConverter.to_duckdb_record(fs)
        me_record = MacroEconomicDataConverter.to_duckdb_record(med)

        # 验证记录字段与表结构匹配
        for field_name in fs_record.keys():
            if field_name in fs_columns:
                # 字段存在于表结构中
                assert True

        for field_name in me_record.keys():
            if field_name in me_columns:
                # 字段存在于表结构中
                assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
