"""
Configuration Types Module

This module defines configuration-related data classes and types.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from .theme_types import Theme

@dataclass
class ThemeConfig:
    """Theme configuration settings"""
    theme: Theme = Theme.SYSTEM
    name: str = "light"
    background_color: str = "#FFFFFF"
    text_color: str = "#000000"
    grid_color: str = "#E0E0E0"
    chart_colors: List[str] = field(default_factory=lambda: ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728"])
    custom_colors: Dict[str, str] = field(default_factory=dict)
    font_family: str = "Arial"
    font_size: int = 12

    def __hash__(self):
        """Make ThemeConfig hashable by using theme name as hash"""
        return hash(self.theme.name)
        
    def __eq__(self, other):
        """Compare ThemeConfig objects by their theme"""
        if not isinstance(other, ThemeConfig):
            return NotImplemented
        return self.theme == other.theme

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary
        
        Returns:
            Dictionary representation of config
        """
        return {
            "theme": self.theme.name.lower(),
            "name": self.name,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "grid_color": self.grid_color,
            "chart_colors": self.chart_colors,
            "custom_colors": self.custom_colors,
            "font_family": self.font_family,
            "font_size": self.font_size
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThemeConfig':
        """Create config from dictionary
        
        Args:
            data: Dictionary containing config data
            
        Returns:
            ThemeConfig instance
        """
        return cls(
            theme=Theme.from_str(data.get("theme", "system")),
            name=data.get("name", "light"),
            background_color=data.get("background_color", "#FFFFFF"),
            text_color=data.get("text_color", "#000000"),
            grid_color=data.get("grid_color", "#E0E0E0"),
            chart_colors=data.get("chart_colors", ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728"]),
            custom_colors=data.get("custom_colors", {}),
            font_family=data.get("font_family", "Arial"),
            font_size=data.get("font_size", 12)
        )

@dataclass
class ChartConfig:
    """Chart display configuration"""
    show_grid: bool = True
    show_volume: bool = True
    show_ma: bool = True
    ma_periods: list[int] = field(default_factory=lambda: [5, 10, 20, 60])
    candlestick_width: float = 0.8
    chart_height: int = 600
    chart_width: int = 800
    auto_update: bool = True
    update_interval: int = 5
    default_period: str = "D"
    default_indicators: list[str] = field(default_factory=lambda: ["MA", "MACD", "RSI"])
    font_family: str = "Microsoft YaHei"
    font_size: int = 12

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary
        
        Returns:
            Dictionary representation of config
        """
        return {
            "show_grid": self.show_grid,
            "show_volume": self.show_volume,
            "show_ma": self.show_ma,
            "ma_periods": self.ma_periods,
            "candlestick_width": self.candlestick_width,
            "chart_height": self.chart_height,
            "chart_width": self.chart_width,
            "auto_update": self.auto_update,
            "update_interval": self.update_interval,
            "default_period": self.default_period,
            "default_indicators": self.default_indicators,
            "font_family": self.font_family,
            "font_size": self.font_size
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChartConfig':
        """Create config from dictionary
        
        Args:
            data: Dictionary containing config data
            
        Returns:
            ChartConfig instance
        """
        return cls(
            show_grid=data.get("show_grid", True),
            show_volume=data.get("show_volume", True),
            show_ma=data.get("show_ma", True),
            ma_periods=data.get("ma_periods", [5, 10, 20, 60]),
            candlestick_width=data.get("candlestick_width", 0.8),
            chart_height=data.get("chart_height", 600),
            chart_width=data.get("chart_width", 800),
            auto_update=data.get("auto_update", True),
            update_interval=data.get("update_interval", 5),
            default_period=data.get("default_period", "D"),
            default_indicators=data.get("default_indicators", ["MA", "MACD", "RSI"]),
            font_family=data.get("font_family", "Microsoft YaHei"),
            font_size=data.get("font_size", 12)
        )

@dataclass
class TradingConfig:
    """Trading parameters configuration"""
    default_symbol: str = "000001"
    default_period: str = "1d"
    auto_refresh: bool = True
    refresh_interval: int = 60
    trade_amount: float = 10000.0
    commission_rate: float = 0.0003
    slippage: float = 0.0
    initial_cash: float = 1000000.0
    position_ratio: float = 0.8
    stop_loss: float = 0.05
    trailing_stop: float = 0.1
    time_stop: int = 5

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary
        
        Returns:
            Dictionary representation of config
        """
        return {
            "default_symbol": self.default_symbol,
            "default_period": self.default_period,
            "auto_refresh": self.auto_refresh,
            "refresh_interval": self.refresh_interval,
            "trade_amount": self.trade_amount,
            "commission_rate": self.commission_rate,
            "slippage": self.slippage,
            "initial_cash": self.initial_cash,
            "position_ratio": self.position_ratio,
            "stop_loss": self.stop_loss,
            "trailing_stop": self.trailing_stop,
            "time_stop": self.time_stop
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingConfig':
        """Create config from dictionary
        
        Args:
            data: Dictionary containing config data
            
        Returns:
            TradingConfig instance
        """
        return cls(
            default_symbol=data.get("default_symbol", "000001"),
            default_period=data.get("default_period", "1d"),
            auto_refresh=data.get("auto_refresh", True),
            refresh_interval=data.get("refresh_interval", 60),
            trade_amount=data.get("trade_amount", 10000.0),
            commission_rate=data.get("commission_rate", 0.0003),
            slippage=data.get("slippage", 0.0),
            initial_cash=data.get("initial_cash", 1000000.0),
            position_ratio=data.get("position_ratio", 0.8),
            stop_loss=data.get("stop_loss", 0.05),
            trailing_stop=data.get("trailing_stop", 0.1),
            time_stop=data.get("time_stop", 5)
        )

@dataclass
class PerformanceConfig:
    """Performance monitoring configuration"""
    enable_monitoring: bool = True
    monitor_memory: bool = True
    monitor_cpu: bool = True
    cpu_threshold: float = 80.0
    memory_threshold: float = 80.0
    response_threshold: float = 1.0
    metrics_history_size: int = 1000
    log_to_file: bool = True
    log_file: str = "performance.log"

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary
        
        Returns:
            Dictionary representation of config
        """
        return {
            "enable_monitoring": self.enable_monitoring,
            "monitor_memory": self.monitor_memory,
            "monitor_cpu": self.monitor_cpu,
            "cpu_threshold": self.cpu_threshold,
            "memory_threshold": self.memory_threshold,
            "response_threshold": self.response_threshold,
            "metrics_history_size": self.metrics_history_size,
            "log_to_file": self.log_to_file,
            "log_file": self.log_file
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceConfig':
        """Create config from dictionary
        
        Args:
            data: Dictionary containing config data
            
        Returns:
            PerformanceConfig instance
        """
        return cls(
            enable_monitoring=data.get("enable_monitoring", True),
            monitor_memory=data.get("monitor_memory", True),
            monitor_cpu=data.get("monitor_cpu", True),
            cpu_threshold=data.get("cpu_threshold", 80.0),
            memory_threshold=data.get("memory_threshold", 80.0),
            response_threshold=data.get("response_threshold", 1.0),
            metrics_history_size=data.get("metrics_history_size", 1000),
            log_to_file=data.get("log_to_file", True),
            log_file=data.get("log_file", "performance.log")
        )

@dataclass
class AppConfig:
    """Application configuration container"""
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    chart: ChartConfig = field(default_factory=ChartConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary
        
        Returns:
            Dictionary representation of config
        """
        return {
            "theme": self.theme.to_dict(),
            "chart": self.chart.to_dict(),
            "trading": self.trading.to_dict(),
            "performance": self.performance.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """Create config from dictionary
        
        Args:
            data: Dictionary containing config data
            
        Returns:
            AppConfig instance
        """
        theme_data = data.get("theme", {})
        chart_data = data.get("chart", {})
        trading_data = data.get("trading", {})
        performance_data = data.get("performance", {})
        
        return cls(
            theme=ThemeConfig.from_dict(theme_data),
            chart=ChartConfig.from_dict(chart_data),
            trading=TradingConfig.from_dict(trading_data),
            performance=PerformanceConfig.from_dict(performance_data)
        )

@dataclass
class DataConfig:
    """Data configuration"""
    enable_cache: bool = True
    max_cache_size: int = 1000
    auto_update: bool = True
    update_interval: int = 3600
    data_source: str = 'local'
    backup_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary
        
        Returns:
            Dictionary representation of config
        """
        return {
            "enable_cache": self.enable_cache,
            "max_cache_size": self.max_cache_size,
            "auto_update": self.auto_update,
            "update_interval": self.update_interval,
            "data_source": self.data_source,
            "backup_enabled": self.backup_enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataConfig':
        """Create config from dictionary
        
        Args:
            data: Dictionary containing config data
            
        Returns:
            DataConfig instance
        """
        return cls(
            enable_cache=data.get("enable_cache", True),
            max_cache_size=data.get("max_cache_size", 1000),
            auto_update=data.get("auto_update", True),
            update_interval=data.get("update_interval", 3600),
            data_source=data.get("data_source", 'local'),
            backup_enabled=data.get("backup_enabled", True)
        )

@dataclass
class UIConfig:
    """UI configuration"""
    font_size: int = 12
    language: str = 'zh_CN'
    show_tooltips: bool = True
    confirm_exit: bool = True
    layout: str = 'default'
    window_size: Dict[str, int] = None

    def __post_init__(self):
        if self.window_size is None:
            self.window_size = {'width': 1200, 'height': 800}

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary
        
        Returns:
            Dictionary representation of config
        """
        return {
            "font_size": self.font_size,
            "language": self.language,
            "show_tooltips": self.show_tooltips,
            "confirm_exit": self.confirm_exit,
            "layout": self.layout,
            "window_size": self.window_size
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIConfig':
        """Create config from dictionary
        
        Args:
            data: Dictionary containing config data
            
        Returns:
            UIConfig instance
        """
        return cls(
            font_size=data.get("font_size", 12),
            language=data.get("language", 'zh_CN'),
            show_tooltips=data.get("show_tooltips", True),
            confirm_exit=data.get("confirm_exit", True),
            layout=data.get("layout", 'default'),
            window_size=data.get("window_size", {'width': 1200, 'height': 800})
        )

@dataclass
class LoggingConfig:
    """日志配置类"""
    level: str = "INFO"
    save_to_file: bool = True
    log_file: str = "hikyuu_ui.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    auto_compress: bool = True
    max_logs: int = 1000
    performance_log: bool = True
    performance_log_file: str = "performance.log"
    exception_log: bool = True
    exception_log_file: str = "exceptions.log"
    async_logging: bool = True
    log_queue_size: int = 1000
    worker_threads: int = 2

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary
        
        Returns:
            Dictionary representation of config
        """
        return {
            "level": self.level,
            "save_to_file": self.save_to_file,
            "log_file": self.log_file,
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
            "console_output": self.console_output,
            "auto_compress": self.auto_compress,
            "max_logs": self.max_logs,
            "performance_log": self.performance_log,
            "performance_log_file": self.performance_log_file,
            "exception_log": self.exception_log,
            "exception_log_file": self.exception_log_file,
            "async_logging": self.async_logging,
            "log_queue_size": self.log_queue_size,
            "worker_threads": self.worker_threads
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoggingConfig':
        """Create config from dictionary
        
        Args:
            data: Dictionary containing config data
            
        Returns:
            LoggingConfig instance
        """
        return cls(
            level=data.get("level", "INFO"),
            save_to_file=data.get("save_to_file", True),
            log_file=data.get("log_file", "hikyuu_ui.log"),
            max_bytes=data.get("max_bytes", 10 * 1024 * 1024),
            backup_count=data.get("backup_count", 5),
            console_output=data.get("console_output", True),
            auto_compress=data.get("auto_compress", True),
            max_logs=data.get("max_logs", 1000),
            performance_log=data.get("performance_log", True),
            performance_log_file=data.get("performance_log_file", "performance.log"),
            exception_log=data.get("exception_log", True),
            exception_log_file=data.get("exception_log_file", "exceptions.log"),
            async_logging=data.get("async_logging", True),
            log_queue_size=data.get("log_queue_size", 1000),
            worker_threads=data.get("worker_threads", 2)
        )

class UIStyleConfig:
    """UI样式配置"""
    font_family: str = "Microsoft YaHei"  # 默认使用微软雅黑
    font_size: int = 10
    # ... existing code ... 