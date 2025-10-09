"""
数据模式定义

定义标准化数据模式，支持多种资产类型和数据类型的统一格式转换。
提供字段映射、数据类型转换、验证规则等功能。

作者: FactorWeave-Quant团队
版本: 1.0
日期: 2024-09-19
"""

import re
from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, date
import pandas as pd
import numpy as np

from loguru import logger
from .plugin_types import AssetType, DataType

logger = logger.bind(module=__name__)

class SchemaValidationLevel(Enum):
    """数据模式验证级别"""
    STRICT = "strict"      # 严格验证，任何不符合都报错
    RELAXED = "relaxed"    # 宽松验证，尽量修复
    MINIMAL = "minimal"    # 最小验证，只检查必需字段

@dataclass
class FieldMapping:
    """字段映射配置"""
    source_field: str
    target_field: str
    data_type: str = "auto"  # auto, str, int, float, datetime, bool, decimal
    transform_func: Optional[Callable] = None
    default_value: Any = None
    is_required: bool = True
    validation_func: Optional[Callable] = None
    format_pattern: Optional[str] = None  # 用于日期、时间格式等

    def apply_transform(self, value: Any) -> Any:
        """应用字段转换"""
        try:
            # 处理空值
            if pd.isna(value) or value is None or value == "":
                if self.default_value is not None:
                    return self.default_value
                elif self.is_required:
                    raise ValueError(f"必需字段 {self.source_field} 为空")
                else:
                    return None

            # 应用自定义转换函数
            if self.transform_func:
                value = self.transform_func(value)

            # 数据类型转换
            value = self._convert_data_type(value)

            # 应用验证函数
            if self.validation_func and not self.validation_func(value):
                raise ValueError(f"字段 {self.source_field} 验证失败")

            return value

        except Exception as e:
            logger.error(f"字段转换失败: {self.source_field} -> {self.target_field}, {e}")
            if self.is_required:
                raise
            return self.default_value

    def _convert_data_type(self, value: Any) -> Any:
        """数据类型转换"""
        if self.data_type == "auto":
            return value
        elif self.data_type == "str":
            return str(value).strip()
        elif self.data_type == "int":
            return int(float(value))  # 先转float再转int，处理"10.0"这种情况
        elif self.data_type == "float":
            return float(value)
        elif self.data_type == "decimal":
            from decimal import Decimal
            return Decimal(str(value))
        elif self.data_type == "datetime":
            return self._convert_datetime(value)
        elif self.data_type == "bool":
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on', 'y')
            return bool(value)
        else:
            return value

    def _convert_datetime(self, value: Any) -> datetime:
        """转换日期时间"""
        if isinstance(value, datetime):
            return value
        elif isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        elif isinstance(value, str):
            if self.format_pattern:
                return datetime.strptime(value, self.format_pattern)
            else:
                return pd.to_datetime(value)
        elif isinstance(value, (int, float)):
            # 时间戳转换
            if value > 1e10:  # 毫秒时间戳
                return pd.to_datetime(value, unit='ms')
            else:  # 秒时间戳
                return pd.to_datetime(value, unit='s')
        else:
            return pd.to_datetime(value)

@dataclass
class StandardDataSchema:
    """标准数据模式定义"""
    schema_id: str
    name: str
    description: str
    asset_type: AssetType
    data_type: DataType
    version: str = "1.0"

    # 字段定义
    fields: List[FieldMapping] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    unique_keys: List[List[str]] = field(default_factory=list)  # 联合唯一约束
    indexes: List[str] = field(default_factory=list)

    # 验证规则
    validation_level: SchemaValidationLevel = SchemaValidationLevel.RELAXED
    custom_validators: List[Callable] = field(default_factory=list)

    # 预处理和后处理
    preprocessor: Optional[Callable] = None
    postprocessor: Optional[Callable] = None

    def get_field_mapping(self, source_field: str) -> Optional[FieldMapping]:
        """获取源字段的映射配置"""
        for field_map in self.fields:
            if field_map.source_field == source_field:
                return field_map
        return None

    def get_target_fields(self) -> List[str]:
        """获取所有目标字段名"""
        return [field_map.target_field for field_map in self.fields]

    def get_required_fields(self) -> List[str]:
        """获取必需字段"""
        return [field_map.source_field for field_map in self.fields if field_map.is_required]

class StandardDataSchemas:
    """标准数据模式集合"""

    def __init__(self):
        self.schemas: Dict[str, StandardDataSchema] = {}
        self._init_builtin_schemas()

    def _init_builtin_schemas(self):
        """初始化内置数据模式"""
        # K线数据标准模式
        self._create_kline_schema()
        # 实时行情标准模式
        self._create_quote_schema()
        # 股票基本信息标准模式
        self._create_stock_info_schema()
        # 资产列表标准模式
        self._create_asset_list_schema()
        # 板块资金流标准模式
        self._create_sector_fund_flow_schema()

    def _create_kline_schema(self):
        """创建K线数据标准模式"""
        def validate_price(price):
            return price > 0

        def normalize_volume(volume):
            """标准化成交量，确保为正数"""
            return max(0, float(volume) if volume else 0)

        schema = StandardDataSchema(
            schema_id="standard_kline",
            name="标准K线数据",
            description="标准化的K线数据格式，支持所有资产类型",
            asset_type=AssetType.STOCK,  # 默认，运行时会动态设置
            data_type=DataType.HISTORICAL_KLINE,
            fields=[
                FieldMapping("code", "code", "str", is_required=True),
                FieldMapping("name", "name", "str", default_value=""),
                FieldMapping("market", "market", "str", is_required=True),
                FieldMapping("date", "datetime", "datetime", is_required=True),
                FieldMapping("open", "open", "float", validation_func=validate_price, is_required=True),
                FieldMapping("high", "high", "float", validation_func=validate_price, is_required=True),
                FieldMapping("low", "low", "float", validation_func=validate_price, is_required=True),
                FieldMapping("close", "close", "float", validation_func=validate_price, is_required=True),
                FieldMapping("volume", "volume", "float", transform_func=normalize_volume, default_value=0.0),
                FieldMapping("amount", "amount", "float", default_value=0.0),
                FieldMapping("turnover", "turnover", "float", default_value=0.0),
                FieldMapping("period", "period", "str", default_value="1d"),
            ],
            primary_keys=["code", "datetime", "period"],
            unique_keys=[["code", "datetime", "period"]],
            indexes=["code", "datetime", "market"]
        )
        self.schemas["standard_kline"] = schema

    def _create_quote_schema(self):
        """创建实时行情标准模式"""
        def validate_positive(value):
            return value >= 0

        schema = StandardDataSchema(
            schema_id="standard_quote",
            name="标准实时行情",
            description="标准化的实时行情数据格式",
            asset_type=AssetType.STOCK,
            data_type=DataType.REAL_TIME_QUOTE,
            fields=[
                FieldMapping("code", "code", "str", is_required=True),
                FieldMapping("name", "name", "str", default_value=""),
                FieldMapping("market", "market", "str", is_required=True),
                FieldMapping("current_price", "current_price", "float", is_required=True),
                FieldMapping("open", "open", "float", default_value=0.0),
                FieldMapping("high", "high", "float", default_value=0.0),
                FieldMapping("low", "low", "float", default_value=0.0),
                FieldMapping("close", "close", "float", default_value=0.0),
                FieldMapping("volume", "volume", "float", validation_func=validate_positive, default_value=0.0),
                FieldMapping("amount", "amount", "float", validation_func=validate_positive, default_value=0.0),
                FieldMapping("change", "change", "float", default_value=0.0),
                FieldMapping("change_percent", "change_percent", "float", default_value=0.0),
                FieldMapping("timestamp", "timestamp", "datetime", is_required=True),
                FieldMapping("bid_price", "bid_price", "float", default_value=0.0),
                FieldMapping("ask_price", "ask_price", "float", default_value=0.0),
                FieldMapping("bid_volume", "bid_volume", "float", validation_func=validate_positive, default_value=0.0),
                FieldMapping("ask_volume", "ask_volume", "float", validation_func=validate_positive, default_value=0.0),
            ],
            primary_keys=["code", "timestamp"],
            indexes=["code", "timestamp", "market"]
        )
        self.schemas["standard_quote"] = schema

    def _create_stock_info_schema(self):
        """创建股票基本信息标准模式"""
        def validate_stock_code(code):
            """验证股票代码格式"""
            if not code:
                return False
            # 简单的股票代码格式验证
            pattern = r'^[0-9]{6}$|^[A-Z]{1,5}$'
            return bool(re.match(pattern, str(code)))

        schema = StandardDataSchema(
            schema_id="standard_stock_info",
            name="标准股票信息",
            description="标准化的股票基本信息格式",
            asset_type=AssetType.STOCK,
            data_type=DataType.FUNDAMENTAL,
            fields=[
                FieldMapping("code", "code", "str", validation_func=validate_stock_code, is_required=True),
                FieldMapping("name", "name", "str", is_required=True),
                FieldMapping("market", "market", "str", is_required=True),
                FieldMapping("industry", "industry", "str", default_value=""),
                FieldMapping("sector", "sector", "str", default_value=""),
                FieldMapping("list_date", "list_date", "datetime", default_value=None),
                FieldMapping("total_shares", "total_shares", "float", default_value=0.0),
                FieldMapping("float_shares", "float_shares", "float", default_value=0.0),
                FieldMapping("market_cap", "market_cap", "float", default_value=0.0),
                FieldMapping("status", "status", "str", default_value="正常"),
                FieldMapping("currency", "currency", "str", default_value="CNY"),
                FieldMapping("is_st", "is_st", "bool", default_value=False),
                FieldMapping("updated_time", "updated_time", "datetime", default_value=datetime.now),
            ],
            primary_keys=["code"],
            indexes=["code", "market", "industry", "sector"]
        )
        self.schemas["standard_stock_info"] = schema

    def _create_asset_list_schema(self):
        """创建资产列表标准模式"""
        schema = StandardDataSchema(
            schema_id="standard_asset_list",
            name="标准资产列表",
            description="标准化的资产列表格式",
            asset_type=AssetType.STOCK,  # 动态设置
            data_type=DataType.ASSET_LIST,
            fields=[
                FieldMapping("code", "code", "str", is_required=True),
                FieldMapping("name", "name", "str", is_required=True),
                FieldMapping("market", "market", "str", is_required=True),
                FieldMapping("asset_type", "asset_type", "str", default_value="stock"),
                FieldMapping("status", "status", "str", default_value="active"),
                FieldMapping("category", "category", "str", default_value=""),
                FieldMapping("updated_time", "updated_time", "datetime", default_value=datetime.now),
            ],
            primary_keys=["code"],
            indexes=["code", "market", "asset_type", "status"]
        )
        self.schemas["standard_asset_list"] = schema

    def _create_sector_fund_flow_schema(self):
        """创建板块资金流标准模式"""
        def validate_positive_or_zero(value):
            return value >= 0

        schema = StandardDataSchema(
            schema_id="standard_sector_fund_flow",
            name="标准板块资金流",
            description="标准化的板块资金流动数据格式",
            asset_type=AssetType.SECTOR,
            data_type=DataType.SECTOR_FUND_FLOW,
            fields=[
                FieldMapping("sector_code", "sector_code", "str", is_required=True),
                FieldMapping("sector_name", "sector_name", "str", is_required=True),
                FieldMapping("date", "date", "datetime", is_required=True),
                FieldMapping("main_inflow", "main_inflow", "float", default_value=0.0),
                FieldMapping("main_outflow", "main_outflow", "float", validation_func=validate_positive_or_zero, default_value=0.0),
                FieldMapping("main_net_flow", "main_net_flow", "float", default_value=0.0),
                FieldMapping("retail_inflow", "retail_inflow", "float", validation_func=validate_positive_or_zero, default_value=0.0),
                FieldMapping("retail_outflow", "retail_outflow", "float", validation_func=validate_positive_or_zero, default_value=0.0),
                FieldMapping("retail_net_flow", "retail_net_flow", "float", default_value=0.0),
                FieldMapping("total_volume", "total_volume", "float", validation_func=validate_positive_or_zero, default_value=0.0),
                FieldMapping("total_amount", "total_amount", "float", validation_func=validate_positive_or_zero, default_value=0.0),
            ],
            primary_keys=["sector_code", "date"],
            indexes=["sector_code", "date", "sector_name"]
        )
        self.schemas["standard_sector_fund_flow"] = schema

    def get_schema(self, schema_id: str) -> Optional[StandardDataSchema]:
        """获取数据模式"""
        return self.schemas.get(schema_id)

    def get_schema_by_type(self, asset_type: AssetType, data_type: DataType) -> Optional[StandardDataSchema]:
        """根据资产类型和数据类型获取数据模式"""
        for schema in self.schemas.values():
            if schema.data_type == data_type:
                return schema
        return None

    def register_schema(self, schema: StandardDataSchema):
        """注册新的数据模式"""
        self.schemas[schema.schema_id] = schema
        logger.info(f"注册数据模式: {schema.schema_id} - {schema.name}")

    def list_schemas(self) -> List[str]:
        """列出所有可用的数据模式"""
        return list(self.schemas.keys())

    def validate_data(self, data: pd.DataFrame, schema_id: str) -> Tuple[bool, List[str]]:
        """验证数据是否符合指定模式"""
        schema = self.get_schema(schema_id)
        if not schema:
            return False, [f"未找到数据模式: {schema_id}"]

        errors = []

        # 检查必需字段
        required_fields = schema.get_required_fields()
        missing_fields = [field for field in required_fields if field not in data.columns]
        if missing_fields:
            errors.append(f"缺少必需字段: {missing_fields}")

        # 检查数据类型
        for field_map in schema.fields:
            if field_map.source_field in data.columns:
                try:
                    # 尝试转换一行数据验证
                    if len(data) > 0:
                        test_value = data[field_map.source_field].iloc[0]
                        field_map.apply_transform(test_value)
                except Exception as e:
                    errors.append(f"字段 {field_map.source_field} 数据类型错误: {e}")

        # 应用自定义验证器
        for validator in schema.custom_validators:
            try:
                if not validator(data):
                    errors.append("自定义验证失败")
            except Exception as e:
                errors.append(f"自定义验证错误: {e}")

        return len(errors) == 0, errors

# 全局数据模式实例
_global_schemas = StandardDataSchemas()

def get_standard_schemas() -> StandardDataSchemas:
    """获取全局数据模式实例"""
    return _global_schemas

def get_schema(schema_id: str) -> Optional[StandardDataSchema]:
    """获取指定数据模式"""
    return _global_schemas.get_schema(schema_id)

def get_schema_by_type(asset_type: AssetType, data_type: DataType) -> Optional[StandardDataSchema]:
    """根据资产类型和数据类型获取数据模式"""
    return _global_schemas.get_schema_by_type(asset_type, data_type)

