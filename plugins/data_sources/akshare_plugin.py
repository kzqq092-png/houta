#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare数据源插件

基于AKShare库提供板块资金流数据，支持：
- 板块资金流排行
- 主力资金净流入数据
- 超大单、大单、中单、小单资金流数据

使用akshare库作为数据源：
- 支持概念板块和行业板块
- 实时数据更新
- 丰富的资金流指标

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from core.data_source_extensions import IDataSourcePlugin, PluginInfo, HealthCheckResult
from core.plugin_types import PluginType, AssetType, DataType
from plugins.plugin_interface import PluginState
from loguru import logger

# 检查akshare库
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("akshare 数据源可用")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.error("akshare 库未安装，插件无法工作。请安装: pip install akshare")


class AKSharePlugin(IDataSourcePlugin):
    """AKShare数据源插件（异步优化版）"""

    def __init__(self):
        # 调用父类初始化（设置plugin_state等基础属性）
        super().__init__()

        self.logger = logger.bind(module=__name__)
        # initialized 和 last_error 已在父类定义

        # 插件基本信息
        self.plugin_id = "data_sources.akshare_plugin"
        self.name = "AKShare数据源插件"
        self.version = "1.0.0"
        self.description = "基于AKShare库的板块资金流数据源插件"
        self.author = "FactorWeave-Quant 开发团队"

        # 插件类型标识
        self.plugin_type = PluginType.DATA_SOURCE_STOCK

        # 支持的资产类型
        self.supported_asset_types = [AssetType.STOCK, AssetType.SECTOR]

        # 连接状态属性
        self.connection_time = None
        self.last_activity = None
        self.config = {}

        # 缓存设置
        self.cache_duration = 300  # 5分钟缓存
        self.last_cache_time = None
        self.cached_data = None

    def get_version(self) -> str:
        """获取插件版本"""
        return self.version

    def get_description(self) -> str:
        """获取插件描述"""
        return self.description

    def get_author(self) -> str:
        """获取插件作者"""
        return self.author

    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return self.supported_asset_types

    def get_supported_data_types(self) -> List[DataType]:
        """获取支持的数据类型"""
        return [
            DataType.SECTOR_FUND_FLOW,    # 板块资金流数据（主要功能）
            DataType.REAL_TIME_QUOTE,     # 实时行情
            DataType.ASSET_LIST           # 资产列表
        ]

    def get_capabilities(self) -> Dict[str, Any]:
        """获取插件能力"""
        return {
            "markets": ["CN"],  # 中国市场
            "asset_types": ["stock", "sector"],
            "data_types": ["sector_fund_flow", "real_time_quote", "asset_list"],
            "real_time_support": True,
            "historical_data": False,  # 主要提供当日数据
            "sector_fund_flow": True,
            "rate_limit": "无限制",
            "cache_enabled": True,
            "primary_strength": "sector_fund_flow"
        }

    def get_priority(self) -> int:
        """获取插件优先级"""
        return 20  # 中等优先级

    def get_weight(self) -> float:
        """获取插件权重"""
        return 0.8  # 较高权重，数据质量好

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id=self.plugin_id,
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            supported_asset_types=self.supported_asset_types,
            supported_data_types=self.get_supported_data_types(),
            capabilities={
                'real_time': True,
                'historical': False,
                'sector_fund_flow': True,
                'asset_list': True,
                'rate_limit': 0,  # 无限制
                'cache_enabled': True,
                'primary_strength': 'sector_fund_flow'
            }
        )

    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """同步初始化插件（快速，不做网络连接）"""
        try:
            self.plugin_state = PluginState.INITIALIZING

            # 检查 akshare 库是否可用
            if not AKSHARE_AVAILABLE:
                self.last_error = "akshare库未安装"
                self.plugin_state = PluginState.FAILED
                self.logger.error("AkShare插件初始化失败: akshare库未安装")
                self.logger.error("请安装: pip install akshare")
                return False

            # 合并配置
            if config:
                self.config.update(config)

            # 标记初始化完成
            self.initialized = True
            self.plugin_state = PluginState.INITIALIZED
            self.logger.info("AkShare插件同步初始化完成（<10ms）")
            return True

        except Exception as e:
            self.last_error = str(e)
            self.plugin_state = PluginState.FAILED
            self.logger.error(f"AkShare插件初始化失败: {e}")
            return False

    def _do_connect(self) -> bool:
        """实际连接逻辑（在后台线程中执行）"""
        try:
            if not AKSHARE_AVAILABLE:
                self.plugin_state = PluginState.FAILED
                self.logger.error("❌ AkShare库不可用")
                return False

            # 简单测试：获取一条数据
            self.logger.info("AkShare插件测试连接...")
            test_df = ak.stock_sector_fund_flow_rank()

            if test_df is not None and not test_df.empty:
                self.logger.info("✅ AkShare插件连接测试成功")
                self.plugin_state = PluginState.CONNECTED
                self.connection_time = datetime.now()
                self.last_activity = datetime.now()
                return True
            else:
                self.logger.warning("⚠️ AkShare插件测试返回空数据，但仍认为可用")
                self.plugin_state = PluginState.CONNECTED
                self.connection_time = datetime.now()
                self.last_activity = datetime.now()
                return True

        except Exception as e:
            self.last_error = str(e)
            self.plugin_state = PluginState.FAILED
            self.logger.error(f"❌ AkShare插件连接失败: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False

    # 连接管理
    def _internal_connect(self, **kwargs) -> bool:
        """内部连接实现"""
        try:
            if not AKSHARE_AVAILABLE:
                self.last_error = "akshare库未安装"
                return False

            # AKShare不需要显式连接，只需要检查库是否可用
            self.connection_time = datetime.now()
            self.last_activity = datetime.now()
            self.initialized = True

            self.logger.info("AKShare数据源连接成功")
            return True

        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"AKShare数据源连接失败: {e}")
            return False

    def _internal_disconnect(self) -> bool:
        """内部断开连接实现"""
        try:
            self.initialized = False
            self.connection_time = None
            self.last_activity = None
            self.cached_data = None
            self.last_cache_time = None

            self.logger.info("AKShare数据源断开连接")
            return True

        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"AKShare数据源断开连接失败: {e}")
            return False

    def fetch_data(self, symbol: str, data_type: str, **params) -> Any:
        """获取数据的通用接口"""
        try:
            if not self.initialized:
                if not self._internal_connect():
                    return None

            self.last_activity = datetime.now()

            if data_type == "sector_fund_flow":
                return self.get_sector_fund_flow_data(**params)
            else:
                self.logger.warning(f"不支持的数据类型: {data_type}")
                return None

        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"获取数据失败: {e}")
            return None

    def get_sector_fund_flow_data(self, data_type=None, **params) -> pd.DataFrame:
        """获取板块资金流数据

        Args:
            data_type: 数据类型（兼容性参数，可选）
            **params: 查询参数
                - limit: 返回记录数，默认50
                - use_cache: 是否使用缓存，默认True
                - indicator: 指标类型

        Returns:
            pd.DataFrame: 板块资金流数据
        """
        try:
            if not AKSHARE_AVAILABLE:
                self.logger.error("akshare库不可用")
                return pd.DataFrame()

            limit = params.get('limit', 50)
            use_cache = params.get('use_cache', True)

            # 检查缓存
            if use_cache and self._is_cache_valid():
                self.logger.info("使用缓存的板块资金流数据")
                return self.cached_data.head(limit) if self.cached_data is not None else pd.DataFrame()

            self.logger.info("获取AKShare板块资金流数据...")

            # 调用AKShare API
            raw_data = ak.stock_sector_fund_flow_rank()

            if raw_data is None or raw_data.empty:
                self.logger.warning("AKShare未返回板块资金流数据")
                return pd.DataFrame()

            # 数据标准化
            standardized_data = []
            for idx, row in raw_data.iterrows():
                try:
                    sector_info = {
                        'sector_code': f'AK_{idx+1:03d}',
                        'sector_name': str(row.get('名称', '')),
                        'change_percent': self._safe_float(row.get('今日涨跌幅', 0)),
                        'main_net_inflow': self._safe_float(row.get('今日主力净流入-净额', 0)),
                        'main_net_inflow_pct': self._safe_float(row.get('今日主力净流入-净占比', 0)),
                        'super_large_net_inflow': self._safe_float(row.get('今日超大单净流入-净额', 0)),
                        'super_large_net_inflow_pct': self._safe_float(row.get('今日超大单净流入-净占比', 0)),
                        'large_net_inflow': self._safe_float(row.get('今日大单净流入-净额', 0)),
                        'large_net_inflow_pct': self._safe_float(row.get('今日大单净流入-净占比', 0)),
                        'medium_net_inflow': self._safe_float(row.get('今日中单净流入-净额', 0)),
                        'medium_net_inflow_pct': self._safe_float(row.get('今日中单净流入-净占比', 0)),
                        'small_net_inflow': self._safe_float(row.get('今日小单净流入-净额', 0)),
                        'small_net_inflow_pct': self._safe_float(row.get('今日小单净流入-净占比', 0)),
                        'top_stock': str(row.get('今日主力净流入最大股', '')),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'data_source': 'akshare'
                    }
                    standardized_data.append(sector_info)
                except Exception as e:
                    self.logger.warning(f"处理第{idx}行数据时出错: {e}")
                    continue

            if not standardized_data:
                self.logger.warning("没有有效的板块数据")
                return pd.DataFrame()

            df = pd.DataFrame(standardized_data)

            # 更新缓存
            self.cached_data = df
            self.last_cache_time = datetime.now()

            self.logger.info(f"成功获取AKShare板块资金流数据: {len(df)} 条记录")
            return df.head(limit)

        except Exception as e:
            self.logger.error(f"获取AKShare板块资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def _safe_float(self, value) -> float:
        """安全转换为浮点数"""
        try:
            if value is None or value == '':
                return 0.0

            # 处理百分号
            if isinstance(value, str) and '%' in value:
                value = value.replace('%', '')

            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self.cached_data is None or self.last_cache_time is None:
            return False

        cache_age = (datetime.now() - self.last_cache_time).total_seconds()
        return cache_age < self.cache_duration

    # 实现抽象方法
    def connect(self, **kwargs) -> bool:
        """连接数据源"""
        return self._internal_connect(**kwargs)

    def disconnect(self) -> bool:
        """断开连接"""
        return self._internal_disconnect()

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.initialized

    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            'plugin_id': self.plugin_id,
            'name': self.name,
            'connected': self.initialized,
            'connection_time': self.connection_time.isoformat() if self.connection_time else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'last_error': self.last_error,
            'akshare_available': AKSHARE_AVAILABLE
        }

    @property
    def plugin_info(self) -> PluginInfo:
        """获取插件信息（属性形式）"""
        return self.get_plugin_info()

    def health_check(self) -> HealthCheckResult:
        """健康检查（方法形式）"""
        return self.perform_health_check()

    def get_asset_list(self, asset_type: AssetType, market: str = None) -> List[Dict[str, Any]]:
        """获取资产列表"""
        # AKShare插件主要用于板块资金流，暂不实现资产列表
        return []

    def get_kdata(self, symbol: str, freq: str = "D", start_date: str = None,
                  end_date: str = None, count: int = None) -> pd.DataFrame:
        """获取K线数据"""
        # AKShare插件主要用于板块资金流，暂不实现K线数据
        return pd.DataFrame()

    def get_real_time_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情"""
        # AKShare插件主要用于板块资金流，暂不实现实时行情
        return []

    def perform_health_check(self) -> HealthCheckResult:
        """执行健康检查"""
        try:
            if not AKSHARE_AVAILABLE:
                return HealthCheckResult(
                    is_healthy=False,
                    message="akshare库未安装",
                    response_time=0,
                    extra_info={'error': 'akshare library not available'}
                )

            start_time = time.time()

            # 尝试获取少量数据进行健康检查
            test_data = ak.stock_sector_fund_flow_rank()

            response_time = (time.time() - start_time) * 1000  # 转换为毫秒

            if test_data is not None and not test_data.empty:
                return HealthCheckResult(
                    is_healthy=True,
                    message=f"AKShare数据源健康，获取到{len(test_data)}条数据",
                    response_time=response_time,
                    extra_info={
                        'data_count': len(test_data),
                        'cache_status': 'valid' if self._is_cache_valid() else 'expired'
                    }
                )
            else:
                return HealthCheckResult(
                    is_healthy=False,
                    message="AKShare数据源无数据返回",
                    response_time=response_time,
                    extra_info={'error': 'no data returned'}
                )

        except Exception as e:
            return HealthCheckResult(
                is_healthy=False,
                message=f"健康检查异常: {str(e)}",
                response_time=0,
                extra_info={'error': str(e)}
            )


# 插件注册
def create_plugin() -> AKSharePlugin:
    """创建插件实例"""
    return AKSharePlugin()


# 用于兼容性的别名
AKShareDataSourcePlugin = AKSharePlugin
