"""
统一表名生成器

该模块提供统一的数据库表名生成功能，确保整个系统中表名命名规范的一致性。
支持多数据源、多周期、多市场的表名生成。

作者: HIkyuu-UI系统
创建时间: 2024-01-20
"""

import re
import hashlib
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
from loguru import logger
from core.plugin_types import DataType, AssetType


class TableNamePattern(Enum):
    """表名模式枚举"""
    STANDARD = "{data_type}_{plugin_name}_{period}_{market}"
    SIMPLE = "{data_type}_{plugin_name}_{period}"
    MINIMAL = "{data_type}_{plugin_name}"


@dataclass
class TableNameComponents:
    """表名组件"""
    data_type: str
    plugin_name: str
    period: Optional[str] = None
    market: Optional[str] = None
    asset_type: Optional[str] = None
    suffix: Optional[str] = None


class UnifiedTableNameGenerator:
    """
    统一表名生成器

    提供标准化的数据库表名生成功能，确保整个系统中表名的一致性。
    支持多种表名模式和自定义组件。

    特性:
    - 统一的命名规范
    - 多数据源支持
    - 灵活的组件组合
    - 名称清理和验证
    - 缓存机制提升性能
    """

    # 表名长度限制
    MAX_TABLE_NAME_LENGTH = 63  # PostgreSQL/DuckDB限制

    # 缓存生成的表名
    _cache: Dict[str, str] = {}

    # 默认值配置
    DEFAULT_VALUES = {
        'period': 'default',
        'market': 'all',
        'asset_type': 'stock'
    }

    # 名称映射表（用于标准化常见名称）
    NAME_MAPPINGS = {
        'data_type': {
            'historical_kline': 'kline_data',
            'realtime_quote': 'realtime_data',
            'fundamental': 'fundamental_data'
        },
        'plugin_name': {
            'examples.akshare_stock_plugin': 'examples_akshare_stock_plugin',
            'data_sources.eastmoney_plugin': 'data_sources_eastmoney_plugin',
            'examples.sina_stock_plugin': 'examples_sina_stock_plugin',
            'examples.tongdaxin_stock_plugin': 'examples_tongdaxin_stock_plugin'
        },
        'period': {
            'd': 'daily',
            'daily': 'daily',
            '1m': 'minute',
            'minute': 'minute',
            '1h': 'hourly',
            'hourly': 'hourly',
            'w': 'weekly',
            'weekly': 'weekly',
            'm': 'monthly',
            'monthly': 'monthly'
        },
        'market': {
            'shanghai': 'sh',
            'shenzhen': 'sz',
            'beijing': 'bj'
        }
    }

    @classmethod
    def generate(cls,
                 data_type: DataType,
                 plugin_name: str,
                 period: Optional[str] = None,
                 market: Optional[str] = None,
                 asset_type: Optional[AssetType] = None,
                 pattern: TableNamePattern = TableNamePattern.STANDARD,
                 suffix: Optional[str] = None,
                 use_cache: bool = True) -> str:
        """
        生成统一格式的表名

        Args:
            data_type: 数据类型枚举
            plugin_name: 插件名称
            period: 数据周期 (可选)
            market: 市场代码 (可选)
            asset_type: 资产类型 (可选)
            pattern: 表名模式
            suffix: 表名后缀 (可选)
            use_cache: 是否使用缓存

        Returns:
            标准化的表名

        Examples:
            >>> generator = UnifiedTableNameGenerator()
            >>> generator.generate(
            ...     DataType.HISTORICAL_KLINE,
            ...     'akshare',
            ...     period='d',
            ...     market='sz'
            ... )
            'kline_data_akshare_d_sz'
        """

        # 生成缓存键
        cache_key = cls._generate_cache_key(
            data_type, plugin_name, period, market, asset_type, pattern, suffix
        )

        # 检查缓存
        if use_cache and cache_key in cls._cache:
            return cls._cache[cache_key]

        # 标准化组件
        components = cls._standardize_components(
            data_type, plugin_name, period, market, asset_type, suffix
        )

        # 生成表名
        table_name = cls._build_table_name(components, pattern)

        # 验证表名
        table_name = cls._validate_and_fix_table_name(table_name)

        # 缓存结果
        if use_cache:
            cls._cache[cache_key] = table_name

        return table_name

    @classmethod
    def generate_from_components(cls, components: TableNameComponents,
                                 pattern: TableNamePattern = TableNamePattern.STANDARD) -> str:
        """
        从组件生成表名

        Args:
            components: 表名组件
            pattern: 表名模式

        Returns:
            生成的表名
        """
        return cls._build_table_name(components, pattern)

    @classmethod
    def parse_table_name(cls, table_name: str) -> Optional[TableNameComponents]:
        """
        解析表名获取组件信息

        Args:
            table_name: 表名

        Returns:
            表名组件信息，解析失败返回None
        """
        try:
            # 尝试不同的模式解析
            patterns = [
                r'^(\w+)_(\w+)_(\w+)_(\w+)(?:_(\w+))?$',  # STANDARD
                r'^(\w+)_(\w+)_(\w+)$',                    # SIMPLE
                r'^(\w+)_(\w+)$'                           # MINIMAL
            ]

            for pattern in patterns:
                match = re.match(pattern, table_name)
                if match:
                    groups = match.groups()
                    return TableNameComponents(
                        data_type=groups[0],
                        plugin_name=groups[1],
                        period=groups[2] if len(groups) > 2 else None,
                        market=groups[3] if len(groups) > 3 else None,
                        asset_type=groups[4] if len(groups) > 4 else None
                    )

            return None

        except Exception as e:
            logger.error(f"解析表名失败: {table_name}, 错误: {e}")
            return None

    @classmethod
    def _standardize_components(cls,
                                data_type: DataType,
                                plugin_name: str,
                                period: Optional[str],
                                market: Optional[str],
                                asset_type: Optional[AssetType],
                                suffix: Optional[str]) -> TableNameComponents:
        """标准化表名组件"""

        # 标准化数据类型
        clean_data_type = cls._apply_mapping('data_type', data_type.value.lower())
        clean_data_type = cls._clean_name(clean_data_type)

        # 标准化插件名称
        clean_plugin_name = cls._apply_mapping('plugin_name', plugin_name.lower())
        clean_plugin_name = cls._clean_name(clean_plugin_name)

        # 标准化周期
        clean_period = None
        if period:
            clean_period = cls._apply_mapping('period', period.lower())
            clean_period = cls._clean_name(clean_period)

        # 标准化市场
        clean_market = None
        if market:
            clean_market = cls._apply_mapping('market', market.lower())
            clean_market = cls._clean_name(clean_market)

        # 标准化资产类型
        clean_asset_type = None
        if asset_type and asset_type != AssetType.STOCK_A:
            clean_asset_type = cls._clean_name(asset_type.value.lower())

        # 清理后缀
        clean_suffix = None
        if suffix:
            clean_suffix = cls._clean_name(suffix)

        return TableNameComponents(
            data_type=clean_data_type,
            plugin_name=clean_plugin_name,
            period=clean_period,
            market=clean_market,
            asset_type=clean_asset_type,
            suffix=clean_suffix
        )

    @classmethod
    def _build_table_name(cls, components: TableNameComponents,
                          pattern: TableNamePattern) -> str:
        """构建表名"""

        # 准备组件字典
        parts = {
            'data_type': components.data_type,
            'plugin_name': components.plugin_name,
            'period': components.period or cls.DEFAULT_VALUES['period'],
            'market': components.market or cls.DEFAULT_VALUES['market']
        }

        # 根据模式生成基础表名
        if pattern == TableNamePattern.STANDARD:
            base_name = pattern.value.format(**parts)
        elif pattern == TableNamePattern.SIMPLE:
            base_name = pattern.value.format(
                data_type=parts['data_type'],
                plugin_name=parts['plugin_name'],
                period=parts['period']
            )
        else:  # MINIMAL
            base_name = pattern.value.format(
                data_type=parts['data_type'],
                plugin_name=parts['plugin_name']
            )

        # 添加资产类型后缀
        if components.asset_type:
            base_name += f"_{components.asset_type}"

        # 添加自定义后缀
        if components.suffix:
            base_name += f"_{components.suffix}"

        return base_name

    @classmethod
    def _apply_mapping(cls, component_type: str, value: str) -> str:
        """应用名称映射"""
        mappings = cls.NAME_MAPPINGS.get(component_type, {})
        return mappings.get(value, value)

    @classmethod
    def _clean_name(cls, name: str) -> str:
        """
        清理名称中的特殊字符

        Args:
            name: 原始名称

        Returns:
            清理后的名称
        """
        if not name:
            return 'unknown'

        # 移除特殊字符，只保留字母、数字和下划线
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).lower())

        # 移除连续的下划线
        cleaned = re.sub(r'_+', '_', cleaned)

        # 移除开头和结尾的下划线
        cleaned = cleaned.strip('_')

        # 确保不为空
        if not cleaned:
            return 'unknown'

        # 确保以字母开头
        if cleaned[0].isdigit():
            cleaned = f"t_{cleaned}"

        return cleaned

    @classmethod
    def _validate_and_fix_table_name(cls, table_name: str) -> str:
        """
        验证并修复表名

        Args:
            table_name: 原始表名

        Returns:
            验证后的表名
        """
        # 检查长度
        if len(table_name) > cls.MAX_TABLE_NAME_LENGTH:
            # 生成哈希后缀
            hash_suffix = hashlib.md5(table_name.encode()).hexdigest()[:8]
            max_prefix_length = cls.MAX_TABLE_NAME_LENGTH - len(hash_suffix) - 1
            table_name = f"{table_name[:max_prefix_length]}_{hash_suffix}"

        # 确保表名有效
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', table_name):
            # 如果表名无效，使用哈希值
            hash_name = hashlib.md5(table_name.encode()).hexdigest()
            table_name = f"table_{hash_name[:16]}"

        return table_name

    @classmethod
    def _generate_cache_key(cls, *args) -> str:
        """生成缓存键"""
        key_parts = [str(arg) for arg in args if arg is not None]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    @classmethod
    def clear_cache(cls):
        """清空缓存"""
        cls._cache.clear()

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'cache_size': len(cls._cache),
            'cache_keys': list(cls._cache.keys())
        }


# 便捷函数
def generate_table_name(data_type: DataType,
                        plugin_name: str,
                        period: Optional[str] = None,
                        market: Optional[str] = None,
                        asset_type: Optional[AssetType] = None) -> str:
    """
    便捷的表名生成函数

    Args:
        data_type: 数据类型
        plugin_name: 插件名称
        period: 数据周期
        market: 市场代码
        asset_type: 资产类型

    Returns:
        生成的表名
    """
    return UnifiedTableNameGenerator.generate(
        data_type=data_type,
        plugin_name=plugin_name,
        period=period,
        market=market,
        asset_type=asset_type
    )


def parse_table_name(table_name: str) -> Optional[TableNameComponents]:
    """
    便捷的表名解析函数

    Args:
        table_name: 表名

    Returns:
        表名组件
    """
    return UnifiedTableNameGenerator.parse_table_name(table_name)


if __name__ == "__main__":
    # 测试代码
    from core.plugin_types import DataType, AssetType

    # 测试表名生成
    table_name = generate_table_name(
        data_type=DataType.HISTORICAL_KLINE,
        plugin_name="examples.akshare_stock_plugin",
        period="daily",
        market="shenzhen"
    )
    logger.info(f"生成的表名: {table_name}")

    # 测试表名解析
    components = parse_table_name(table_name)
    if components:
        logger.info(f"解析结果: {components}")
    else:
        logger.error("解析失败")

    # 测试缓存
    logger.info(f"缓存统计: {UnifiedTableNameGenerator.get_cache_stats()}")
