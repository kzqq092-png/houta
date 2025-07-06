"""
Yahoo Finance数据源插件示例

展示如何创建外部数据源插件，从Yahoo Finance获取股票数据。
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QFormLayout, QPushButton, QTextEdit

from ..plugin_interface import (
    IDataSourcePlugin, PluginMetadata, PluginType, PluginCategory,
    plugin_metadata, register_plugin, PluginContext
)


@plugin_metadata(
    name="Yahoo Finance数据源",
    version="1.0.0",
    description="从Yahoo Finance获取股票数据的数据源插件",
    author="HIkyuu团队",
    email="support@hikyuu.org",
    website="https://hikyuu.org",
    license="MIT",
    plugin_type=PluginType.DATA_SOURCE,
    category=PluginCategory.CORE,
    dependencies=["pandas", "numpy", "requests"],
    min_hikyuu_version="2.0.0",
    max_hikyuu_version="3.0.0",
    tags=["数据源", "Yahoo Finance", "股票数据"],
    icon_path="icons/yahoo_finance.png"
)
@register_plugin(PluginType.DATA_SOURCE)
class YahooFinanceDataSourcePlugin(IDataSourcePlugin):
    """Yahoo Finance数据源插件"""

    def __init__(self):
        """初始化插件"""
        self._context: Optional[PluginContext] = None
        self._config = {
            'api_timeout': 30,
            'retry_count': 3,
            'cache_enabled': True,
            'cache_duration': 300  # 5分钟缓存
        }
        self._cache = {}

    @property
    def metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        return self._plugin_metadata

    def initialize(self, context: PluginContext) -> bool:
        """
        初始化插件

        Args:
            context: 插件上下文

        Returns:
            bool: 初始化是否成功
        """
        try:
            self._context = context

            # 加载配置
            config = context.get_plugin_config(self.metadata.name)
            if config:
                self._config.update(config)

            # 注册事件处理器
            context.register_event_handler("market_close", self._on_market_close)

            context.log_manager.info(f"Yahoo Finance数据源插件初始化成功")
            return True

        except Exception as e:
            if context:
                context.log_manager.error(f"Yahoo Finance数据源插件初始化失败: {e}")
            return False

    def cleanup(self) -> None:
        """清理插件资源"""
        if self._context:
            self._context.log_manager.info("Yahoo Finance数据源插件清理完成")

    def get_data_source_name(self) -> str:
        """获取数据源名称"""
        return "Yahoo Finance"

    def get_supported_data_types(self) -> List[str]:
        """获取支持的数据类型"""
        return [
            "stock_daily",      # 日线数据
            "stock_intraday",   # 分钟线数据
            "stock_info",       # 股票基本信息
            "market_summary"    # 市场摘要
        ]

    def fetch_data(self, symbol: str, data_type: str, **params) -> pd.DataFrame:
        """
        获取数据

        Args:
            symbol: 股票代码
            data_type: 数据类型
            **params: 其他参数

        Returns:
            股票数据DataFrame
        """
        try:
            # 检查缓存
            cache_key = f"{symbol}_{data_type}_{str(params)}"
            if self._config['cache_enabled'] and cache_key in self._cache:
                cache_time, cached_data = self._cache[cache_key]
                if (datetime.now() - cache_time).seconds < self._config['cache_duration']:
                    if self._context:
                        self._context.log_manager.debug(f"从缓存返回数据: {symbol}")
                    return cached_data

            # 根据数据类型获取数据
            if data_type == "stock_daily":
                data = self._fetch_daily_data(symbol, **params)
            elif data_type == "stock_intraday":
                data = self._fetch_intraday_data(symbol, **params)
            elif data_type == "stock_info":
                data = self._fetch_stock_info(symbol, **params)
            elif data_type == "market_summary":
                data = self._fetch_market_summary(**params)
            else:
                raise ValueError(f"不支持的数据类型: {data_type}")

            # 缓存数据
            if self._config['cache_enabled']:
                self._cache[cache_key] = (datetime.now(), data)

            if self._context:
                self._context.log_manager.info(f"成功获取数据: {symbol} ({data_type})")

            return data

        except Exception as e:
            if self._context:
                self._context.log_manager.error(f"获取数据失败: {symbol} ({data_type}) - {e}")
            raise

    def _fetch_daily_data(self, symbol: str, **params) -> pd.DataFrame:
        """
        获取日线数据

        Args:
            symbol: 股票代码
            **params: 参数（start_date, end_date等）

        Returns:
            日线数据DataFrame
        """
        # 生成模拟数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(hash(symbol) % 2**32)

        base_price = 100 + (hash(symbol) % 100)
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = base_price * np.exp(np.cumsum(returns))

        data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.005, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, len(dates))
        }, index=dates)

        return data

    def _fetch_intraday_data(self, symbol: str, **params) -> pd.DataFrame:
        """
        获取分钟线数据

        Args:
            symbol: 股票代码
            **params: 参数（interval等）

        Returns:
            分钟线数据DataFrame
        """
        interval = params.get('interval', '1m')  # 1m, 5m, 15m, 30m, 1h
        date = params.get('date', datetime.now().date())

        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()

        # 生成分钟级数据
        start_time = datetime.combine(date, datetime.min.time().replace(hour=9, minute=30))
        end_time = datetime.combine(date, datetime.min.time().replace(hour=16, minute=0))

        # 根据间隔生成时间序列
        interval_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60
        }.get(interval, 1)

        times = pd.date_range(start_time, end_time, freq=f'{interval_minutes}min')

        np.random.seed(hash(f"{symbol}_{date}") % 2**32)

        # 生成价格数据
        base_price = 100 + (hash(symbol) % 100)
        returns = np.random.normal(0, 0.001, len(times))
        prices = base_price * (1 + np.cumsum(returns) * 0.01)

        # 生成OHLC数据
        opens = prices * (1 + np.random.normal(0, 0.001, len(times)))
        highs = np.maximum(opens, prices) * (1 + np.abs(np.random.normal(0, 0.002, len(times))))
        lows = np.minimum(opens, prices) * (1 - np.abs(np.random.normal(0, 0.002, len(times))))
        closes = prices
        volumes = np.random.randint(1000, 10000, len(times))

        data = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }, index=times)

        return data

    def _fetch_stock_info(self, symbol: str, **params) -> pd.DataFrame:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码
            **params: 参数

        Returns:
            股票信息DataFrame
        """
        info = {
            'symbol': symbol,
            'name': f"Company {symbol}",
            'sector': 'Technology',
            'market_cap': 1000000000 + (hash(symbol) % 500000000),
            'pe_ratio': 15 + (hash(symbol) % 30),
            'dividend_yield': (hash(symbol) % 500) / 10000
        }

        data = pd.DataFrame([info])
        data.set_index('symbol', inplace=True)

        return data

    def _fetch_market_summary(self, **params) -> pd.DataFrame:
        """
        获取市场摘要

        Args:
            **params: 参数

        Returns:
            市场摘要DataFrame
        """
        # 模拟市场摘要数据
        indices = ['SPY', 'QQQ', 'IWM', 'DIA']

        summary_data = []
        for index in indices:
            summary_data.append({
                'symbol': index,
                'name': f"Index {index}",
                'price': 100 + (hash(index) % 300),
                'change': np.random.normal(0, 2),
                'change_percent': np.random.normal(0, 0.02),
                'volume': np.random.randint(1000000, 10000000),
                'market_cap': np.random.randint(100000000, 1000000000)
            })

        data = pd.DataFrame(summary_data)
        data.set_index('symbol', inplace=True)

        return data

    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式"""
        return {
            'type': 'object',
            'properties': {
                'api_timeout': {
                    'type': 'integer',
                    'minimum': 5,
                    'maximum': 120,
                    'default': 30,
                    'title': 'API超时时间(秒)'
                },
                'retry_count': {
                    'type': 'integer',
                    'minimum': 0,
                    'maximum': 10,
                    'default': 3,
                    'title': '重试次数'
                },
                'cache_enabled': {
                    'type': 'boolean',
                    'default': True,
                    'title': '启用缓存'
                },
                'cache_duration': {
                    'type': 'integer',
                    'minimum': 60,
                    'maximum': 3600,
                    'default': 300,
                    'title': '缓存时长(秒)'
                }
            },
            'required': ['api_timeout', 'retry_count']
        }

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return self._config.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        try:
            timeout = config.get('api_timeout', 30)
            retry_count = config.get('retry_count', 3)

            if not isinstance(timeout, int) or timeout < 5 or timeout > 120:
                return False

            if not isinstance(retry_count, int) or retry_count < 0 or retry_count > 10:
                return False

            return True

        except Exception:
            return False

    def on_event(self, event_name: str, *args, **kwargs) -> None:
        """处理事件"""
        if event_name == "market_close" and self._context:
            # 市场收盘时清理缓存
            self._cache.clear()
            self._context.log_manager.info("Yahoo Finance数据源：市场收盘，清理缓存")

    def _on_market_close(self) -> None:
        """市场收盘事件处理器"""
        if self._context:
            self._context.log_manager.debug("Yahoo Finance数据源：处理市场收盘事件")

    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接

        Returns:
            测试结果
        """
        try:
            # 尝试获取测试数据
            test_data = self.fetch_data("AAPL", "stock_daily")

            return {
                'success': True,
                'message': '连接成功',
                'data_points': len(test_data)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'连接失败: {e}',
                'data_points': 0
            }

    def get_available_symbols(self, **params) -> List[str]:
        """
        获取可用的股票代码列表

        Args:
            **params: 参数（market等）

        Returns:
            股票代码列表
        """
        # 模拟常见股票代码
        symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
            'META', 'NVDA', 'AMD', 'INTC', 'NFLX',
            'ORCL', 'CRM', 'ADBE', 'PYPL', 'UBER',
            'SPOT', 'ZOOM', 'DOCU', 'SNOW', 'PLTR'
        ]

        market = params.get('market', 'US')
        if market == 'US':
            return symbols
        else:
            return []

    def create_config_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """创建配置组件"""
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)

        # 基本配置
        config_form = QFormLayout()

        # API超时
        timeout_edit = QLineEdit(str(self._config['api_timeout']))
        config_form.addRow("API超时(秒):", timeout_edit)

        # 重试次数
        retry_edit = QLineEdit(str(self._config['retry_count']))
        config_form.addRow("重试次数:", retry_edit)

        layout.addLayout(config_form)

        # 测试连接按钮
        test_btn = QPushButton("测试连接")
        layout.addWidget(test_btn)

        # 测试结果显示
        result_text = QTextEdit()
        result_text.setMaximumHeight(100)
        result_text.setReadOnly(True)
        layout.addWidget(result_text)

        def test_connection():
            """测试连接"""
            result = self.test_connection()
            if result['success']:
                result_text.setPlainText(f"✓ {result['message']}")
                result_text.setStyleSheet("color: green;")
            else:
                result_text.setPlainText(f"✗ {result['message']}")
                result_text.setStyleSheet("color: red;")

        def save_config():
            """保存配置"""
            try:
                self._config['api_timeout'] = int(timeout_edit.text())
                self._config['retry_count'] = int(retry_edit.text())

                if self._context:
                    self._context.save_plugin_config(self.metadata.name, self._config)

            except ValueError:
                result_text.setPlainText("✗ 配置格式错误")
                result_text.setStyleSheet("color: red;")

        test_btn.clicked.connect(test_connection)
        timeout_edit.textChanged.connect(save_config)
        retry_edit.textChanged.connect(save_config)

        return widget
