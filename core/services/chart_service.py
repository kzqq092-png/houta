"""
图表服务模块

负责图表的创建、渲染和管理。
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from .base_service import CacheableService, ConfigurableService
from ..events import ChartUpdateEvent, StockSelectedEvent


logger = logging.getLogger(__name__)


class ChartService(CacheableService, ConfigurableService):
    """
    图表服务

    负责图表的创建、渲染和管理。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, cache_size: int = 100, **kwargs):
        """
        初始化图表服务

        Args:
            config: 服务配置
            cache_size: 缓存大小
            **kwargs: 其他参数
        """
        # 初始化各个基类
        CacheableService.__init__(self, cache_size=cache_size, **kwargs)
        ConfigurableService.__init__(self, config=config, **kwargs)
        self._current_chart_type = 'candlestick'
        self._current_period = 'D'
        self._current_indicators = []
        self._current_stock_code = None
        self._chart_themes = {}

    def _do_initialize(self) -> None:
        """初始化图表服务"""
        try:
            # 加载默认配置
            self._current_chart_type = self.get_config_value('default_chart_type', 'candlestick')
            self._current_period = self.get_config_value('default_period', 'D')
            self._current_indicators = self.get_config_value('default_indicators', [])

            # 初始化图表主题
            self._load_chart_themes()

            # 订阅股票选择事件
            self.event_bus.subscribe(StockSelectedEvent, self._on_stock_selected)

            logger.info("Chart service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize chart service: {e}")
            raise

    def create_chart(self, stock_code: str, chart_type: str = None,
                     period: str = None, indicators: List[str] = None,
                     time_range: int = 365) -> Optional[Dict[str, Any]]:
        """
        创建图表

        Args:
            stock_code: 股票代码
            chart_type: 图表类型
            period: 周期
            indicators: 指标列表
            time_range: 时间范围

        Returns:
            图表配置信息
        """
        self._ensure_initialized()

        # 使用默认值
        chart_type = chart_type or self._current_chart_type
        period = period or self._current_period
        indicators = indicators or self._current_indicators

        cache_key = f"chart_{stock_code}_{chart_type}_{period}_{time_range}_{hash(tuple(indicators))}"
        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            # 获取股票服务
            stock_service = self._get_stock_service()
            if not stock_service:
                logger.error("Stock service not available")
                return None

            # 获取股票数据
            stock_data = stock_service.get_stock_data(stock_code, period, time_range)
            if stock_data is None or stock_data.empty:
                logger.warning(f"No data available for {stock_code}")
                return None

            # 创建图表配置
            chart_config = {
                'stock_code': stock_code,
                'chart_type': chart_type,
                'period': period,
                'indicators': indicators,
                'time_range': time_range,
                'data': stock_data,
                'theme': self._get_current_theme(),
                'layout': self._get_chart_layout(chart_type, indicators)
            }

            # 缓存结果
            self.put_to_cache(cache_key, chart_config)

            # 发布图表更新事件
            event = ChartUpdateEvent(
                stock_code=stock_code,
                chart_type=chart_type,
                period=period,
                indicators=indicators,
                time_range=time_range
            )
            event.data.update({
                'chart_config': chart_config
            })
            self.event_bus.publish(event)

            return chart_config

        except Exception as e:
            logger.error(f"Failed to create chart for {stock_code}: {e}")
            return None

    def update_chart_type(self, chart_type: str) -> bool:
        """
        更新图表类型

        Args:
            chart_type: 新的图表类型

        Returns:
            是否成功更新
        """
        self._ensure_initialized()

        try:
            if chart_type in self._get_supported_chart_types():
                self._current_chart_type = chart_type
                self.update_config({'default_chart_type': chart_type})

                # 如果有当前股票，重新创建图表
                if self._current_stock_code:
                    self.create_chart(self._current_stock_code)

                logger.info(f"Updated chart type to {chart_type}")
                return True
            else:
                logger.warning(f"Unsupported chart type: {chart_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to update chart type: {e}")
            return False

    def update_period(self, period: str) -> bool:
        """
        更新周期

        Args:
            period: 新的周期

        Returns:
            是否成功更新
        """
        self._ensure_initialized()

        try:
            if period in self._get_supported_periods():
                self._current_period = period
                self.update_config({'default_period': period})

                # 清除相关缓存
                self._clear_period_cache()

                # 如果有当前股票，重新创建图表
                if self._current_stock_code:
                    self.create_chart(self._current_stock_code)

                logger.info(f"Updated period to {period}")
                return True
            else:
                logger.warning(f"Unsupported period: {period}")
                return False

        except Exception as e:
            logger.error(f"Failed to update period: {e}")
            return False

    def add_indicator(self, indicator: str) -> bool:
        """
        添加指标

        Args:
            indicator: 指标名称

        Returns:
            是否成功添加
        """
        self._ensure_initialized()

        try:
            if indicator not in self._current_indicators:
                self._current_indicators.append(indicator)
                self.update_config({'default_indicators': self._current_indicators})

                # 清除相关缓存
                self._clear_indicator_cache()

                # 如果有当前股票，重新创建图表
                if self._current_stock_code:
                    self.create_chart(self._current_stock_code)

                logger.info(f"Added indicator {indicator}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to add indicator {indicator}: {e}")
            return False

    def remove_indicator(self, indicator: str) -> bool:
        """
        移除指标

        Args:
            indicator: 指标名称

        Returns:
            是否成功移除
        """
        self._ensure_initialized()

        try:
            if indicator in self._current_indicators:
                self._current_indicators.remove(indicator)
                self.update_config({'default_indicators': self._current_indicators})

                # 清除相关缓存
                self._clear_indicator_cache()

                # 如果有当前股票，重新创建图表
                if self._current_stock_code:
                    self.create_chart(self._current_stock_code)

                logger.info(f"Removed indicator {indicator}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to remove indicator {indicator}: {e}")
            return False

    def get_current_chart_config(self) -> Dict[str, Any]:
        """
        获取当前图表配置

        Returns:
            当前图表配置
        """
        return {
            'chart_type': self._current_chart_type,
            'period': self._current_period,
            'indicators': self._current_indicators.copy(),
            'stock_code': self._current_stock_code
        }

    def get_supported_chart_types(self) -> List[str]:
        """
        获取支持的图表类型

        Returns:
            支持的图表类型列表
        """
        return self._get_supported_chart_types()

    def get_supported_periods(self) -> List[str]:
        """
        获取支持的周期

        Returns:
            支持的周期列表
        """
        return self._get_supported_periods()

    def get_available_indicators(self) -> List[str]:
        """
        获取可用的指标

        Returns:
            可用的指标列表
        """
        return [
            'MA5', 'MA10', 'MA20', 'MA60',
            'MACD', 'KDJ', 'RSI', 'BOLL',
            'VOL', 'BIAS', 'WR', 'CCI'
        ]

    def get_chart_data(self, stock_code: str, period: str = None,
                       indicators: List[str] = None, time_range: int = 365) -> Dict[str, Any]:
        """
        获取图表数据（为UI层提供的便捷方法）

        Args:
            stock_code: 股票代码
            period: 周期
            indicators: 指标列表
            time_range: 时间范围

        Returns:
            包含K线数据和指标数据的字典
        """
        self._ensure_initialized()

        try:
            # 获取股票服务
            stock_service = self._get_stock_service()
            if not stock_service:
                logger.error("Stock service not available")
                return {}

            # 使用默认值
            period = period or self._current_period
            indicators = indicators or self._current_indicators

            # 获取股票基本信息
            stock_info = stock_service.get_stock_info(stock_code)
            if not stock_info:
                logger.warning(f"Stock info not found for {stock_code}")
                return {}

            # 获取股票名称（处理不同类型的stock_info）
            if hasattr(stock_info, 'name'):
                stock_name = stock_info.name
            elif hasattr(stock_info, 'get'):
                stock_name = stock_info.get('name', stock_code)
            else:
                stock_name = stock_code

            # 获取K线数据
            kline_data = stock_service.get_stock_data(stock_code, period, time_range)
            if kline_data is None or kline_data.empty:
                logger.warning(f"No kline data available for {stock_code}")
                return {
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'kline_data': [],
                    'indicators': {},
                    'period': period
                }

            # 转换K线数据为列表格式（适合UI显示）
            kline_list = []
            for _, row in kline_data.iterrows():
                # 格式化日期字符串（只保留日期部分，适合日线图显示）
                if hasattr(row.name, 'strftime'):
                    date_str = row.name.strftime('%Y-%m-%d')
                else:
                    date_str = str(row.name)[:10]  # 取前10个字符作为日期

                kline_list.append({
                    'date': date_str,  # 使用'date'字段名，与middle_panel保持一致
                    'datetime': row.name.strftime('%Y-%m-%d %H:%M:%S') if hasattr(row.name, 'strftime') else str(row.name),
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'close': float(row.get('close', 0)),
                    'volume': int(row.get('volume', 0))
                })

            # 计算技术指标（这里是简化版本，实际应该调用专门的指标计算服务）
            indicators_data = self._calculate_indicators(kline_data, indicators)

            return {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'kline_data': kline_list,
                'indicators': indicators_data,
                'period': period,
                'last_update': kline_data.index[-1].strftime('%Y-%m-%d %H:%M:%S') if not kline_data.empty else None
            }

        except Exception as e:
            logger.error(f"Failed to get chart data for {stock_code}: {e}")
            return {}

    def _calculate_indicators(self, kline_data: pd.DataFrame, indicators: List[str]) -> Dict[str, Any]:
        """
        计算技术指标

        Args:
            kline_data: K线数据
            indicators: 指标列表

        Returns:
            指标数据字典
        """
        indicators_data = {}

        if kline_data.empty:
            return indicators_data

        try:
            close_prices = kline_data['close']
            high_prices = kline_data['high']
            low_prices = kline_data['low']
            volume = kline_data['volume']

            for indicator in indicators:
                if indicator.startswith('MA') and not indicator.startswith('MACD'):
                    # 移动平均线
                    try:
                        period = int(indicator[2:]) if len(indicator) > 2 else 5
                        ma_values = close_prices.rolling(window=period).mean()
                        indicators_data[indicator] = ma_values.fillna(0).tolist()
                    except ValueError:
                        # 如果无法解析周期，跳过该指标
                        logger.warning(f"Cannot parse period from indicator: {indicator}")
                        continue

                elif indicator == 'VOL':
                    # 成交量
                    indicators_data[indicator] = volume.tolist()

                elif indicator == 'MACD':
                    # MACD指标（简化计算）
                    ema12 = close_prices.ewm(span=12).mean()
                    ema26 = close_prices.ewm(span=26).mean()
                    dif = ema12 - ema26
                    dea = dif.ewm(span=9).mean()
                    macd = (dif - dea) * 2

                    indicators_data['MACD'] = {
                        'DIF': dif.fillna(0).tolist(),
                        'DEA': dea.fillna(0).tolist(),
                        'MACD': macd.fillna(0).tolist()
                    }

                elif indicator == 'RSI':
                    # RSI指标（简化计算）
                    delta = close_prices.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    indicators_data[indicator] = rsi.fillna(50).tolist()

                elif indicator == 'BOLL':
                    # 布林带
                    ma20 = close_prices.rolling(window=20).mean()
                    std20 = close_prices.rolling(window=20).std()
                    upper = ma20 + (std20 * 2)
                    lower = ma20 - (std20 * 2)

                    indicators_data['BOLL'] = {
                        'UPPER': upper.fillna(0).tolist(),
                        'MID': ma20.fillna(0).tolist(),
                        'LOWER': lower.fillna(0).tolist()
                    }

                # 其他指标可以在这里继续添加...

        except Exception as e:
            logger.error(f"Failed to calculate indicators: {e}")

        return indicators_data

    def export_chart(self, format: str = 'png', **kwargs) -> Optional[str]:
        """
        导出图表

        Args:
            format: 导出格式
            **kwargs: 其他参数

        Returns:
            导出的文件路径
        """
        self._ensure_initialized()

        try:
            if not self._current_stock_code:
                logger.warning("No current stock for chart export")
                return None

            # 这里应该调用具体的图表渲染引擎进行导出
            # 暂时返回模拟路径
            export_path = f"charts/{self._current_stock_code}_{self._current_chart_type}.{format}"

            logger.info(f"Chart exported to {export_path}")
            return export_path

        except Exception as e:
            logger.error(f"Failed to export chart: {e}")
            return None

    def _on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件"""
        try:
            stock_code = event.stock_code

            # 避免重复处理相同股票
            if self._current_stock_code == stock_code:
                logger.debug(f"Chart service already handling {stock_code}, skipping")
                return

            self._current_stock_code = stock_code

            # 获取股票服务
            stock_service = self._get_stock_service()
            if not stock_service:
                logger.warning("Stock service not available for chart update")
                return

            # 快速检查股票是否有数据（只检查1条数据）
            try:
                test_data = stock_service.get_stock_data(stock_code, period='D', count=1)
                if test_data is None or test_data.empty:
                    logger.warning(f"No data available for {stock_code}")
                    return
            except Exception as e:
                logger.warning(f"Failed to check data for {stock_code}: {e}")
                return

            # 创建图表（使用较少的数据量进行初始化）
            self.create_chart(
                stock_code=stock_code,
                chart_type=self._current_chart_type,
                period=self._current_period,
                indicators=self._current_indicators,
                time_range=100  # 减少初始数据量
            )

        except Exception as e:
            logger.error(f"Failed to handle stock selected event: {e}")

    def _get_stock_service(self):
        """获取股票服务"""
        try:
            if hasattr(self, 'service_container') and self.service_container:
                from .stock_service import StockService
                return self.service_container.get_service(StockService)
            else:
                # 通过事件总线获取服务容器
                try:
                    from ..containers import get_service_container
                    from .stock_service import StockService
                    container = get_service_container()
                    return container.try_resolve(StockService)
                except ImportError:
                    # 如果没有服务容器，返回None
                    logger.warning("Service container not available")
                    return None
        except Exception as e:
            logger.error(f"Failed to get stock service: {e}")
        return None

    def _get_supported_chart_types(self) -> List[str]:
        """获取支持的图表类型"""
        return ['candlestick', 'line', 'bar', 'area']

    def _get_supported_periods(self) -> List[str]:
        """获取支持的周期"""
        return ['1min', '5min', '15min', '30min', '60min', 'D', 'W', 'M']

    def _get_current_theme(self) -> Dict[str, Any]:
        """获取当前主题"""
        theme_name = self.get_config_value('theme', 'default')
        return self._chart_themes.get(theme_name, self._get_default_theme())

    def _get_default_theme(self) -> Dict[str, Any]:
        """获取默认主题"""
        return {
            'background_color': '#ffffff',
            'grid_color': '#e0e0e0',
            'text_color': '#333333',
            'up_color': '#ff4444',
            'down_color': '#00aa00',
            'ma_colors': ['#ff6600', '#0066ff', '#ff00ff', '#00ffff']
        }

    def _get_chart_layout(self, chart_type: str, indicators: List[str]) -> Dict[str, Any]:
        """获取图表布局"""
        layout = {
            'main_chart': {
                'type': chart_type,
                'height': 0.7  # 占总高度的70%
            },
            'sub_charts': []
        }

        # 根据指标添加子图表
        volume_indicators = ['VOL']
        oscillator_indicators = ['MACD', 'KDJ', 'RSI', 'WR', 'CCI']

        for indicator in indicators:
            if indicator in volume_indicators:
                layout['sub_charts'].append({
                    'type': 'volume',
                    'indicators': [indicator],
                    'height': 0.15
                })
            elif indicator in oscillator_indicators:
                layout['sub_charts'].append({
                    'type': 'oscillator',
                    'indicators': [indicator],
                    'height': 0.15
                })

        return layout

    def _load_chart_themes(self) -> None:
        """加载图表主题"""
        self._chart_themes = {
            'default': self._get_default_theme(),
            'dark': {
                'background_color': '#1e1e1e',
                'grid_color': '#404040',
                'text_color': '#ffffff',
                'up_color': '#ff4444',
                'down_color': '#00aa00',
                'ma_colors': ['#ff6600', '#0066ff', '#ff00ff', '#00ffff']
            }
        }

    def _clear_period_cache(self) -> None:
        """清除周期相关缓存"""
        keys_to_remove = []
        for key in self._cache.keys():
            if 'chart_' in key and f'_{self._current_period}_' in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

    def _clear_indicator_cache(self) -> None:
        """清除指标相关缓存"""
        # 由于指标列表变化，清除所有图表缓存
        keys_to_remove = []
        for key in self._cache.keys():
            if key.startswith('chart_'):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

    def _do_dispose(self) -> None:
        """清理资源"""
        self._current_stock_code = None
        self._current_indicators.clear()
        self._chart_themes.clear()
        super()._do_dispose()

    def get_kdata(self, stock_code: str, period: str = 'D', count: int = 365) -> pd.DataFrame:
        """
        获取K线数据（兼容性方法，委托给股票服务）

        Args:
            stock_code: 股票代码
            period: 周期
            count: 数据条数

        Returns:
            K线数据DataFrame
        """
        self._ensure_initialized()

        try:
            # 获取股票服务
            stock_service = self._get_stock_service()
            if not stock_service:
                logger.error("Stock service not available for get_kdata")
                return pd.DataFrame()

            # 委托给股票服务获取数据
            kdata = stock_service.get_kdata(stock_code, period, count)
            if kdata is not None:
                return kdata
            else:
                logger.warning(f"No kdata available for {stock_code}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Failed to get kdata for {stock_code}: {e}")
            return pd.DataFrame()
