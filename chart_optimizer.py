"""
图表优化器 - 统一图表服务的扩展工具
提供高级图表优化功能，基于统一图表服务架构
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# 导入统一图表服务
try:
    from core.services.unified_chart_service import get_unified_chart_service
    from gui.widgets.chart_widget import ChartWidget
    UNIFIED_CHART_AVAILABLE = True
except ImportError:
    UNIFIED_CHART_AVAILABLE = False
    print("警告: 统一图表服务不可用，图表优化功能将受限")

# 导入核心服务
try:
    from core.services.technical_analysis_service import get_technical_analysis_service
    TECHNICAL_ANALYSIS_AVAILABLE = True
except ImportError:
    TECHNICAL_ANALYSIS_AVAILABLE = False

# 导入日志管理器
try:
    from core.logger import LogManager
    logger = LogManager()
except ImportError:
    class SimpleLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    logger = SimpleLogger()


class UnifiedChartOptimizer:
    """统一图表优化器 - 基于统一图表服务的高级优化工具"""

    def __init__(self):
        """初始化图表优化器"""
        self.chart_service = None
        self.technical_service = None

        if UNIFIED_CHART_AVAILABLE:
            try:
                self.chart_service = get_unified_chart_service()
                logger.info("统一图表服务已连接")
            except Exception as e:
                logger.error(f"无法连接统一图表服务: {e}")

        if TECHNICAL_ANALYSIS_AVAILABLE:
            try:
                self.technical_service = get_technical_analysis_service()
                logger.info("技术分析服务已连接")
            except Exception as e:
                logger.error(f"无法连接技术分析服务: {e}")

    def optimize_chart_widget(self, chart_widget: 'ChartWidget', optimization_level: str = 'standard') -> bool:
        """
        优化图表控件性能

        Args:
            chart_widget: 图表控件实例
            optimization_level: 优化级别 ('basic', 'standard', 'advanced')

        Returns:
            bool: 优化是否成功
        """
        if not UNIFIED_CHART_AVAILABLE or not self.chart_service:
            logger.warning("统一图表服务不可用，无法进行优化")
            return False

        try:
            # 根据优化级别应用不同的优化策略
            if optimization_level == 'basic':
                self._apply_basic_optimization(chart_widget)
            elif optimization_level == 'standard':
                self._apply_standard_optimization(chart_widget)
            elif optimization_level == 'advanced':
                self._apply_advanced_optimization(chart_widget)
            else:
                logger.warning(f"未知的优化级别: {optimization_level}")
                return False

            logger.info(f"图表优化完成 - 级别: {optimization_level}")
            return True

        except Exception as e:
            logger.error(f"图表优化失败: {e}")
            return False

    def _apply_basic_optimization(self, chart_widget: 'ChartWidget'):
        """应用基础优化"""
        # 启用缓存
        chart_widget.enable_cache(True)

        # 设置合理的渲染参数
        chart_widget.set_render_quality('medium')

        # 启用数据压缩
        chart_widget.enable_data_compression(True)

    def _apply_standard_optimization(self, chart_widget: 'ChartWidget'):
        """应用标准优化"""
        # 应用基础优化
        self._apply_basic_optimization(chart_widget)

        # 启用异步渲染
        chart_widget.enable_async_rendering(True)

        # 设置智能重绘
        chart_widget.enable_smart_redraw(True)

        # 优化内存使用
        chart_widget.optimize_memory_usage()

    def _apply_advanced_optimization(self, chart_widget: 'ChartWidget'):
        """应用高级优化"""
        # 应用标准优化
        self._apply_standard_optimization(chart_widget)

        # 启用GPU加速（如果可用）
        chart_widget.enable_gpu_acceleration(True)

        # 设置高级缓存策略
        chart_widget.set_cache_strategy('intelligent')

        # 启用预测性加载
        chart_widget.enable_predictive_loading(True)

    def create_optimized_multi_chart(self, data_dict: Dict[str, pd.DataFrame],
                                     chart_types: Dict[str, str] = None) -> Optional['ChartWidget']:
        """
        创建优化的多图表组合

        Args:
            data_dict: 数据字典，键为图表名称，值为数据
            chart_types: 图表类型字典，键为图表名称，值为图表类型

        Returns:
            ChartWidget: 优化的图表控件或None
        """
        if not UNIFIED_CHART_AVAILABLE or not self.chart_service:
            logger.warning("统一图表服务不可用，无法创建多图表")
            return None

        try:
            # 创建图表控件
            chart_widget = ChartWidget()

            # 设置多面板模式
            chart_widget.set_chart_type('multi_panel')

            # 配置子图表
            for name, data in data_dict.items():
                chart_type = chart_types.get(name, 'candlestick') if chart_types else 'candlestick'

                # 添加子图表
                chart_widget.add_sub_chart(name, data, chart_type)

            # 应用高级优化
            self.optimize_chart_widget(chart_widget, 'advanced')

            logger.info(f"成功创建优化的多图表，包含 {len(data_dict)} 个子图表")
            return chart_widget

        except Exception as e:
            logger.error(f"创建多图表失败: {e}")
            return None

    def add_technical_indicators(self, chart_widget: 'ChartWidget',
                                 indicators: List[Dict[str, Any]]) -> bool:
        """
        添加技术指标到图表

        Args:
            chart_widget: 图表控件
            indicators: 指标配置列表

        Returns:
            bool: 是否成功添加
        """
        if not UNIFIED_CHART_AVAILABLE or not self.technical_service:
            logger.warning("服务不可用，无法添加技术指标")
            return False

        try:
            for indicator_config in indicators:
                indicator_type = indicator_config.get('type')
                params = indicator_config.get('params', {})

                # 计算指标
                if self.technical_service:
                    indicator_data = self.technical_service.calculate_indicator(
                        indicator_type, chart_widget.get_data(), **params
                    )

                    # 添加到图表
                    chart_widget.add_indicator(indicator_type, indicator_data, params)

            logger.info(f"成功添加 {len(indicators)} 个技术指标")
            return True

        except Exception as e:
            logger.error(f"添加技术指标失败: {e}")
            return False

    def create_performance_dashboard(self, performance_data: Dict[str, Any]) -> Optional['ChartWidget']:
        """
        创建性能仪表板

        Args:
            performance_data: 性能数据

        Returns:
            ChartWidget: 性能仪表板图表或None
        """
        if not UNIFIED_CHART_AVAILABLE:
            logger.warning("统一图表服务不可用，无法创建性能仪表板")
            return None

        try:
            # 创建仪表板图表
            dashboard = ChartWidget()
            dashboard.set_chart_type('dashboard')

            # 添加各种性能图表
            if 'returns' in performance_data:
                dashboard.add_returns_chart(performance_data['returns'])

            if 'drawdown' in performance_data:
                dashboard.add_drawdown_chart(performance_data['drawdown'])

            if 'metrics' in performance_data:
                dashboard.add_metrics_panel(performance_data['metrics'])

            # 应用优化
            self.optimize_chart_widget(dashboard, 'advanced')

            logger.info("性能仪表板创建成功")
            return dashboard

        except Exception as e:
            logger.error(f"创建性能仪表板失败: {e}")
            return None

    def apply_theme_optimization(self, chart_widget: 'ChartWidget',
                                 theme: str = 'dark', custom_colors: Dict[str, str] = None) -> bool:
        """
        应用主题优化

        Args:
            chart_widget: 图表控件
            theme: 主题名称
            custom_colors: 自定义颜色配置

        Returns:
            bool: 是否成功应用主题
        """
        if not UNIFIED_CHART_AVAILABLE or not self.chart_service:
            logger.warning("图表服务不可用，无法应用主题")
            return False

        try:
            # 应用基础主题
            self.chart_service.apply_theme(chart_widget, theme)

            # 应用自定义颜色
            if custom_colors:
                chart_widget.set_custom_colors(custom_colors)

            # 优化主题性能
            chart_widget.optimize_theme_rendering()

            logger.info(f"主题 '{theme}' 应用成功")
            return True

        except Exception as e:
            logger.error(f"应用主题失败: {e}")
            return False

    def create_realtime_monitor(self, data_source: Any, update_interval: int = 1000) -> Optional['ChartWidget']:
        """
        创建实时监控图表

        Args:
            data_source: 数据源
            update_interval: 更新间隔（毫秒）

        Returns:
            ChartWidget: 实时监控图表或None
        """
        if not UNIFIED_CHART_AVAILABLE:
            logger.warning("统一图表服务不可用，无法创建实时监控")
            return None

        try:
            # 创建实时图表
            monitor = ChartWidget()
            monitor.set_chart_type('realtime')

            # 设置数据源
            monitor.set_data_source(data_source)

            # 配置更新间隔
            monitor.set_update_interval(update_interval)

            # 启用实时优化
            monitor.enable_realtime_optimization(True)

            # 应用高级优化
            self.optimize_chart_widget(monitor, 'advanced')

            logger.info("实时监控图表创建成功")
            return monitor

        except Exception as e:
            logger.error(f"创建实时监控失败: {e}")
            return None

    def get_optimization_report(self, chart_widget: 'ChartWidget') -> Dict[str, Any]:
        """
        获取优化报告

        Args:
            chart_widget: 图表控件

        Returns:
            Dict: 优化报告
        """
        try:
            report = {
                'optimization_level': chart_widget.get_optimization_level(),
                'cache_enabled': chart_widget.is_cache_enabled(),
                'memory_usage': chart_widget.get_memory_usage(),
                'render_performance': chart_widget.get_render_performance(),
                'data_compression': chart_widget.get_compression_ratio(),
                'gpu_acceleration': chart_widget.is_gpu_acceleration_enabled(),
                'timestamp': datetime.now().isoformat()
            }

            return report

        except Exception as e:
            logger.error(f"获取优化报告失败: {e}")
            return {}


# 全局优化器实例
_chart_optimizer = None


def get_chart_optimizer() -> UnifiedChartOptimizer:
    """获取全局图表优化器实例"""
    global _chart_optimizer
    if _chart_optimizer is None:
        _chart_optimizer = UnifiedChartOptimizer()
    return _chart_optimizer


# 便捷函数
def optimize_chart(chart_widget: 'ChartWidget', level: str = 'standard') -> bool:
    """优化图表控件的便捷函数"""
    optimizer = get_chart_optimizer()
    return optimizer.optimize_chart_widget(chart_widget, level)


def create_multi_chart(data_dict: Dict[str, pd.DataFrame],
                       chart_types: Dict[str, str] = None) -> Optional['ChartWidget']:
    """创建多图表的便捷函数"""
    optimizer = get_chart_optimizer()
    return optimizer.create_optimized_multi_chart(data_dict, chart_types)


def add_indicators(chart_widget: 'ChartWidget', indicators: List[Dict[str, Any]]) -> bool:
    """添加技术指标的便捷函数"""
    optimizer = get_chart_optimizer()
    return optimizer.add_technical_indicators(chart_widget, indicators)


# 向后兼容的ChartOptimizer类（已废弃）
class ChartOptimizer:
    """
    已废弃的ChartOptimizer类
    请使用UnifiedChartOptimizer替代
    """

    def __init__(self):
        logger.warning("ChartOptimizer已废弃，请使用UnifiedChartOptimizer")
        self.unified_optimizer = get_chart_optimizer()

    def __getattr__(self, name):
        # 重定向到统一优化器
        if hasattr(self.unified_optimizer, name):
            return getattr(self.unified_optimizer, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
