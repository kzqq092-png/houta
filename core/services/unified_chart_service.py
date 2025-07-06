"""
统一图表服务

基于ChartWidget的高性能图表渲染服务，为所有组件提供统一的图表API。
替换系统中分散的matplotlib实现，提供更好的性能和一致的用户体验。
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from gui.widgets.chart_widget import ChartWidget
from utils.config_manager import ConfigManager
from utils.theme import get_theme_manager
from core.logger import LogManager
# Cache将在需要时动态导入

logger = logging.getLogger(__name__)


class ChartDataLoader(QThread):
    """异步图表数据加载器"""

    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)

    def __init__(self, data_source, stock_code, period, indicators=None):
        super().__init__()
        self.data_source = data_source
        self.stock_code = stock_code
        self.period = period
        self.indicators = indicators or []
        self._should_stop = False

    def run(self):
        """加载图表数据"""
        try:
            # 验证data_source是否有get_kdata方法
            if not self.data_source:
                error_msg = "Data source is None"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return

            if not hasattr(self.data_source, 'get_kdata'):
                error_msg = f"Data source {type(self.data_source)} has no get_kdata method"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return

            self.progress_updated.emit(10, "正在获取K线数据...")

            # 获取K线数据
            try:
                kline_data = self.data_source.get_kdata(self.stock_code, self.period)
            except AttributeError as e:
                error_msg = f"AttributeError calling get_kdata: {e}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return
            except Exception as e:
                error_msg = f"Error calling get_kdata: {e}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return

            if self._should_stop:
                return

            self.progress_updated.emit(50, "正在计算技术指标...")

            # 计算技术指标
            indicators_data = {}
            for indicator in self.indicators:
                if self._should_stop:
                    return
                try:
                    indicator_data = self._calculate_indicator(kline_data, indicator)
                    indicators_data[indicator] = indicator_data
                except Exception as e:
                    logger.warning(f"计算指标 {indicator} 失败: {e}")

            self.progress_updated.emit(90, "正在准备图表数据...")

            # 准备图表数据
            chart_data = {
                'stock_code': self.stock_code,
                'period': self.period,
                'kline_data': kline_data,
                'indicators_data': indicators_data
            }

            self.progress_updated.emit(100, "数据加载完成")
            self.data_loaded.emit(chart_data)

        except Exception as e:
            logger.error(f"加载图表数据失败: {e}")
            self.error_occurred.emit(str(e))

    def stop(self):
        """停止加载"""
        self._should_stop = True
        self.quit()
        self.wait(3000)  # 等待3秒
        if self.isRunning():
            self.terminate()

    def _calculate_indicator(self, kline_data, indicator_name):
        """计算技术指标"""
        try:
            if kline_data is None or len(kline_data) == 0:
                return []

            # 尝试导入分析服务
            try:
                from core.services.analysis_service import AnalysisService
                analysis_service = AnalysisService()
                logger.debug(f"开始计算指标: {indicator_name}")

                # 根据指标名称计算不同指标
                if indicator_name.upper() == 'MA':
                    # 计算多种周期的移动平均线
                    result = {}
                    for period in [5, 10, 20, 60]:
                        try:
                            logger.debug(f"计算 MA{period}")
                            ma_data = analysis_service.calculate_ma(kline_data, period)
                            if ma_data is not None and len(ma_data) > 0:
                                result[str(period)] = ma_data.tolist() if hasattr(ma_data, 'tolist') else ma_data
                                logger.debug(f"MA{period} 计算完成，数据长度: {len(ma_data) if ma_data is not None else 0}")
                            else:
                                logger.warning(f"MA{period} 计算结果为空")
                        except Exception as e:
                            logger.error(f"计算MA{period}失败: {e}")
                    return result

                elif indicator_name.upper() == 'MACD':
                    # 计算MACD指标
                    try:
                        logger.debug(f"计算 MACD")
                        macd_data = analysis_service.calculate_macd(kline_data)
                        if macd_data is not None:
                            # 确保键名与返回值匹配
                            result = {
                                'DIF': macd_data.get('MACD', []).tolist() if hasattr(macd_data.get('MACD', []), 'tolist') else macd_data.get('MACD', []),
                                'DEA': macd_data.get('Signal', []).tolist() if hasattr(macd_data.get('Signal', []), 'tolist') else macd_data.get('Signal', []),
                                'MACD': macd_data.get('Histogram', []).tolist() if hasattr(macd_data.get('Histogram', []), 'tolist') else macd_data.get('Histogram', [])
                            }
                            logger.debug(f"MACD 计算完成，数据长度: {len(result['DIF']) if 'DIF' in result and result['DIF'] is not None else 0}")
                            return result
                        else:
                            logger.warning("MACD 计算结果为空")
                    except Exception as e:
                        logger.error(f"计算MACD失败: {e}")
                    return {}

                elif indicator_name.upper() == 'BOLL':
                    # 计算布林带
                    try:
                        logger.debug(f"计算 BOLL")
                        boll_data = analysis_service.calculate_bollinger_bands(kline_data)
                        if boll_data is not None:
                            result = {
                                'UPPER': boll_data.get('Upper', []).tolist() if hasattr(boll_data.get('Upper', []), 'tolist') else boll_data.get('Upper', []),
                                'MID': boll_data.get('Middle', []).tolist() if hasattr(boll_data.get('Middle', []), 'tolist') else boll_data.get('Middle', []),
                                'LOWER': boll_data.get('Lower', []).tolist() if hasattr(boll_data.get('Lower', []), 'tolist') else boll_data.get('Lower', [])
                            }
                            logger.debug(f"BOLL 计算完成，数据长度: {len(result['MID']) if 'MID' in result and result['MID'] is not None else 0}")
                            return result
                        else:
                            logger.warning("BOLL 计算结果为空")
                    except Exception as e:
                        logger.error(f"计算BOLL失败: {e}")
                    return {}

                elif indicator_name.upper() == 'RSI':
                    # 计算RSI
                    try:
                        logger.debug(f"计算 RSI")
                        rsi_data = analysis_service.calculate_rsi(kline_data)
                        result = rsi_data.tolist() if hasattr(rsi_data, 'tolist') else rsi_data
                        logger.debug(f"RSI 计算完成，数据长度: {len(result) if result is not None else 0}")
                        return result
                    except Exception as e:
                        logger.error(f"计算RSI失败: {e}")
                    return []

                elif indicator_name.upper() == 'KDJ':
                    # 计算KDJ，使用公共接口
                    try:
                        logger.debug(f"计算 KDJ")
                        # 检查是否有公共接口
                        if hasattr(analysis_service, 'calculate_kdj'):
                            kdj_data = analysis_service.calculate_kdj(kline_data)
                        else:
                            # 如果没有公共接口，使用私有方法
                            logger.warning("使用私有方法计算KDJ，建议添加公共接口")
                            kdj_data = analysis_service._calculate_kdj(kline_data)

                        if kdj_data is not None:
                            result = {
                                'K': kdj_data.get('K', []).tolist() if hasattr(kdj_data.get('K', []), 'tolist') else kdj_data.get('K', []),
                                'D': kdj_data.get('D', []).tolist() if hasattr(kdj_data.get('D', []), 'tolist') else kdj_data.get('D', []),
                                'J': kdj_data.get('J', []).tolist() if hasattr(kdj_data.get('J', []), 'tolist') else kdj_data.get('J', [])
                            }
                            logger.debug(f"KDJ 计算完成，数据长度: {len(result['K']) if 'K' in result and result['K'] is not None else 0}")
                            return result
                        else:
                            logger.warning("KDJ 计算结果为空")
                    except Exception as e:
                        logger.error(f"计算KDJ失败: {e}")
                    return {}

                elif indicator_name.upper() == 'ACOS':
                    # 尝试计算ACOS指标，若不存在则返回空字典
                    try:
                        logger.debug(f"尝试计算 ACOS")
                        # 检查是否存在calculate_acos方法
                        if hasattr(analysis_service, 'calculate_acos'):
                            acos_data = analysis_service.calculate_acos(kline_data)
                            if acos_data is not None:
                                if isinstance(acos_data, dict):
                                    result = {}
                                    for key, value in acos_data.items():
                                        result[key] = value.tolist() if hasattr(value, 'tolist') else value
                                else:
                                    result = acos_data.tolist() if hasattr(acos_data, 'tolist') else acos_data
                                logger.debug(f"ACOS 计算完成")
                                return result
                            else:
                                logger.warning("ACOS 计算结果为空")
                        else:
                            logger.warning(f"分析服务中不存在calculate_acos方法，无法计算ACOS指标")
                            # 添加系统内置指标支持信息
                            logger.info("系统目前支持的内置指标: MA, MACD, BOLL, RSI, KDJ")
                    except Exception as e:
                        logger.error(f"计算ACOS失败: {e}")
                    return {}

                # 如果没有匹配的指标，尝试通用计算方法
                try:
                    # 检查是否有通用指标计算方法
                    if hasattr(analysis_service, 'calculate_indicator'):
                        logger.info(f"尝试使用通用方法计算指标: {indicator_name}")
                        indicator_data = analysis_service.calculate_indicator(kline_data, indicator_name)
                        if indicator_data is not None:
                            if isinstance(indicator_data, dict):
                                result = {}
                                for key, value in indicator_data.items():
                                    result[key] = value.tolist() if hasattr(value, 'tolist') else value
                                return result
                            else:
                                return indicator_data.tolist() if hasattr(indicator_data, 'tolist') else indicator_data
                except Exception as e:
                    logger.error(f"通用计算指标 {indicator_name} 失败: {e}")

                # 如果所有方法都失败，返回空字典并记录警告
                logger.warning(f"未知指标: {indicator_name}")
                # 返回空字典而不是空列表，以保持返回类型一致性
                return {}

            except ImportError as e:
                logger.error(f"导入分析服务失败: {e}")
                return {}

        except Exception as e:
            logger.error(f"计算指标 {indicator_name} 失败: {e}")
            return {}


class UnifiedChartService(QObject):
    """统一图表服务

    提供统一的图表API，基于ChartWidget的高性能实现。
    支持：
    - 高性能K线图渲染
    - 技术指标计算和显示
    - 异步数据加载
    - 缓存机制
    - 主题支持
    - 交互功能
    """

    # 信号定义
    chart_updated = pyqtSignal(str, dict)  # 股票代码, 图表数据
    error_occurred = pyqtSignal(str)  # 错误信息
    loading_progress = pyqtSignal(int, str)  # 进度, 消息

    def __init__(self, config_manager=None, theme_manager=None, data_source=None):
        super().__init__()

        # 初始化管理器
        self.config_manager = config_manager or ConfigManager()
        self.theme_manager = theme_manager or get_theme_manager(self.config_manager)
        self.log_manager = LogManager()
        self.data_source = data_source

        # 初始化缓存
        try:
            from utils.cache import Cache
            self.cache = Cache(max_size=100)  # 缓存100个图表数据
        except (ImportError, TypeError):
            # 如果Cache不可用或参数不匹配，创建简单的字典缓存
            self.cache = {}

        # 数据加载器
        self.data_loader = None

        # 活跃的图表控件
        self._chart_widgets = {}  # chart_id -> ChartWidget

        logger.info("统一图表服务初始化完成")

    def create_chart_widget(self, parent=None, chart_id=None) -> ChartWidget:
        """创建图表控件

        Args:
            parent: 父控件
            chart_id: 图表ID，用于管理多个图表

        Returns:
            ChartWidget实例
        """
        try:
            # 创建图表控件
            chart_widget = ChartWidget(
                parent=parent,
                config_manager=self.config_manager,
                theme_manager=self.theme_manager,
                log_manager=self.log_manager,
                data_manager=self.data_source
            )

            # 连接信号
            chart_widget.error_occurred.connect(self.error_occurred.emit)
            chart_widget.chart_updated.connect(self._on_chart_updated)

            # 注册图表
            if chart_id:
                self._chart_widgets[chart_id] = chart_widget

            return chart_widget

        except Exception as e:
            logger.error(f"创建图表控件失败: {e}")
            self.error_occurred.emit(f"创建图表控件失败: {e}")
            return None

    def create_simple_chart_container(self, parent=None, chart_id=None) -> QWidget:
        """创建简单的图表容器

        为需要简单图表功能的组件提供便捷接口

        Args:
            parent: 父控件
            chart_id: 图表ID

        Returns:
            包含ChartWidget的容器控件
        """
        try:
            # 创建容器
            container = QWidget(parent)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)

            # 创建图表控件
            chart_widget = self.create_chart_widget(container, chart_id)
            if chart_widget:
                layout.addWidget(chart_widget)

            return container

        except Exception as e:
            logger.error(f"创建图表容器失败: {e}")
            self.error_occurred.emit(f"创建图表容器失败: {e}")
            return None

    def load_chart_data(self, stock_code: str, period: str = 'D',
                        indicators: List[str] = None, chart_id: str = None) -> None:
        """异步加载图表数据

        Args:
            stock_code: 股票代码
            period: 周期
            indicators: 技术指标列表
            chart_id: 图表ID
        """
        try:
            # 记录详细日志
            logger.info(f"开始加载图表数据: 股票={stock_code}, 周期={period}, 图表ID={chart_id}")
            logger.info(f"请求的指标列表: {indicators}")

            if not indicators:
                logger.warning(f"指标列表为空，将使用默认指标 ['MA']")
                indicators = ['MA']

            # 检查缓存
            cache_key = f"{stock_code}_{period}_{'-'.join(indicators or [])}"
            if isinstance(self.cache, dict):
                cached_data = self.cache.get(cache_key)
            elif hasattr(self.cache, 'get'):
                cached_data = self.cache.get(cache_key)
            else:
                cached_data = None
            if cached_data:
                logger.debug(f"从缓存获取图表数据: {stock_code}")
                self.chart_updated.emit(stock_code, cached_data)
                return

            # 停止之前的加载
            if self.data_loader and self.data_loader.isRunning():
                logger.debug("停止之前的数据加载线程")
                self.data_loader.stop()

            # 创建新的数据加载器
            self.data_loader = ChartDataLoader(
                self.data_source, stock_code, period, indicators
            )

            # 连接信号
            self.data_loader.data_loaded.connect(
                lambda data: self._on_data_loaded(data, cache_key, chart_id)
            )
            self.data_loader.error_occurred.connect(self.error_occurred.emit)
            self.data_loader.progress_updated.connect(self.loading_progress.emit)

            # 开始加载
            logger.debug(f"启动数据加载线程: 股票={stock_code}, 指标={indicators}")
            self.data_loader.start()

        except Exception as e:
            logger.error(f"加载图表数据失败: {e}", exc_info=True)
            self.error_occurred.emit(f"加载图表数据失败: {e}")

    def update_chart(self, chart_id: str, data: Dict[str, Any]) -> None:
        """更新指定图表的数据

        Args:
            chart_id: 图表ID
            data: 图表数据
        """
        try:
            if chart_id in self._chart_widgets:
                chart_widget = self._chart_widgets[chart_id]
                chart_widget.update_chart(data)
            else:
                logger.warning(f"图表 {chart_id} 不存在")

        except Exception as e:
            logger.error(f"更新图表失败: {e}")
            self.error_occurred.emit(f"更新图表失败: {e}")

    def set_chart_theme(self, theme_name: str) -> None:
        """设置图表主题

        Args:
            theme_name: 主题名称
        """
        try:
            # 更新主题管理器
            self.theme_manager.set_theme(theme_name)

            # 更新所有活跃图表
            for chart_widget in self._chart_widgets.values():
                chart_widget.apply_theme()

        except Exception as e:
            logger.error(f"设置图表主题失败: {e}")
            self.error_occurred.emit(f"设置图表主题失败: {e}")

    def get_chart_widget(self, chart_id: str) -> Optional[ChartWidget]:
        """获取图表控件

        Args:
            chart_id: 图表ID

        Returns:
            ChartWidget实例或None
        """
        return self._chart_widgets.get(chart_id)

    def remove_chart(self, chart_id: str) -> None:
        """移除图表

        Args:
            chart_id: 图表ID
        """
        try:
            if chart_id in self._chart_widgets:
                chart_widget = self._chart_widgets[chart_id]
                chart_widget.deleteLater()
                del self._chart_widgets[chart_id]
                logger.debug(f"移除图表: {chart_id}")

        except Exception as e:
            logger.error(f"移除图表失败: {e}")

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        logger.info("图表缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            if isinstance(self.cache, dict):
                return {
                    'size': len(self.cache),
                    'max_size': 'unlimited',
                    'hits': 0,
                    'misses': 0,
                    'type': 'dict'
                }
            elif hasattr(self.cache, '_cache'):
                return {
                    'size': len(self.cache._cache),
                    'max_size': getattr(self.cache, 'max_size', 'unknown'),
                    'hits': getattr(self.cache, 'hits', 0),
                    'misses': getattr(self.cache, 'misses', 0),
                    'type': type(self.cache).__name__
                }
            else:
                return {
                    'size': len(self.cache) if hasattr(self.cache, '__len__') else 0,
                    'max_size': 'unknown',
                    'hits': 0,
                    'misses': 0,
                    'type': type(self.cache).__name__
                }
        except Exception as e:
            return {
                'error': str(e),
                'type': type(self.cache).__name__
            }

    @pyqtSlot(dict)
    def _on_data_loaded(self, data: Dict[str, Any], cache_key: str = None, chart_id: str = None) -> None:
        """处理数据加载完成"""
        try:
            stock_code = data.get('stock_code', '')
            logger.info(f"图表数据加载完成: {stock_code}, 指标数量: {len(data.get('indicators_data', {}))}")

            # 记录指标数据详情
            indicators_data = data.get('indicators_data', {})
            if not indicators_data:
                logger.warning(f"指标数据为空! 请检查指标计算过程。股票代码: {stock_code}")

            for indicator_name, indicator_data in indicators_data.items():
                if isinstance(indicator_data, dict):
                    logger.debug(f"指标 {indicator_name} 包含子项: {list(indicator_data.keys())}")
                    for sub_name, sub_data in indicator_data.items():
                        data_len = len(sub_data) if hasattr(sub_data, '__len__') else 0
                        logger.debug(f"指标 {indicator_name}.{sub_name} 数据长度: {data_len}")
                else:
                    data_len = len(indicator_data) if hasattr(indicator_data, '__len__') else 0
                    logger.debug(f"指标 {indicator_name} 数据长度: {data_len}")

            # 缓存数据
            if cache_key and self.cache is not None:
                if isinstance(self.cache, dict):
                    self.cache[cache_key] = data
                elif hasattr(self.cache, 'put'):
                    self.cache.put(cache_key, data)

            # 更新图表
            self.chart_updated.emit(stock_code, data)

            # 如果指定了图表ID，更新特定图表
            if chart_id and hasattr(self, '_chart_widgets'):
                if chart_id in self._chart_widgets:
                    chart_widget = self._chart_widgets[chart_id]
                    if chart_widget:
                        # 确保图表数据包含必要的字段
                        if 'kline_data' not in data or data['kline_data'] is None:
                            logger.warning(f"图表数据缺少K线数据，无法更新图表 {chart_id}")
                            return

                        # 为图表组件准备格式化的数据
                        chart_data = {
                            'kdata': data.get('kline_data'),
                            'stock_code': stock_code,
                            'indicators_data': indicators_data,  # 确保指标数据被传递
                            'title': data.get('stock_name', stock_code)
                        }

                        logger.debug(f"更新图表 {chart_id}，数据包含指标: {list(indicators_data.keys())}")
                        chart_widget.update_chart(chart_data)
                        logger.debug(f"已更新图表 {chart_id}")
                    else:
                        logger.warning(f"图表 {chart_id} 不存在")
                else:
                    logger.warning(f"找不到指定的图表ID: {chart_id}，可用图表: {list(self._chart_widgets.keys()) if hasattr(self, '_chart_widgets') else []}")

        except Exception as e:
            logger.error(f"处理图表数据失败: {e}", exc_info=True)
            self.error_occurred.emit(f"处理图表数据失败: {e}")

    @pyqtSlot(dict)
    def _on_chart_updated(self, data: Dict[str, Any]):
        """图表更新处理"""
        try:
            stock_code = data.get('stock_code', '')
            self.chart_updated.emit(stock_code, data)

        except Exception as e:
            logger.error(f"处理图表更新失败: {e}")

    def dispose(self) -> None:
        """释放资源"""
        try:
            # 停止数据加载器
            if self.data_loader and self.data_loader.isRunning():
                self.data_loader.stop()

            # 清理所有图表
            for chart_id in list(self._chart_widgets.keys()):
                self.remove_chart(chart_id)

            # 清空缓存
            self.clear_cache()

            logger.info("统一图表服务资源已释放")

        except Exception as e:
            logger.error(f"释放图表服务资源失败: {e}")


# 全局统一图表服务实例
_unified_chart_service = None


def get_unified_chart_service(config_manager=None, theme_manager=None, data_source=None) -> UnifiedChartService:
    """获取统一图表服务实例

    Args:
        config_manager: 配置管理器
        theme_manager: 主题管理器
        data_source: 数据源

    Returns:
        UnifiedChartService实例
    """
    global _unified_chart_service

    if _unified_chart_service is None:
        _unified_chart_service = UnifiedChartService(
            config_manager=config_manager,
            theme_manager=theme_manager,
            data_source=data_source
        )

    return _unified_chart_service


def create_chart_widget(parent=None, chart_id=None, **kwargs) -> ChartWidget:
    """便捷函数：创建图表控件

    Args:
        parent: 父控件
        chart_id: 图表ID
        **kwargs: 其他参数

    Returns:
        ChartWidget实例
    """
    service = get_unified_chart_service(**kwargs)
    return service.create_chart_widget(parent, chart_id)


def create_simple_chart(parent=None, chart_id=None, **kwargs) -> QWidget:
    """便捷函数：创建简单图表容器

    Args:
        parent: 父控件
        chart_id: 图表ID
        **kwargs: 其他参数

    Returns:
        包含ChartWidget的容器控件
    """
    service = get_unified_chart_service(**kwargs)
    return service.create_simple_chart_container(parent, chart_id)
