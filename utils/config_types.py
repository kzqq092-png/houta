"""
Configuration Types Module

This module defines configuration-related data classes and types.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from .theme_types import Theme
from PyQt5.QtCore import QObject, pyqtSignal

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

class PerformanceConfig:
    """性能监控配置"""
    
    def __init__(self, **kwargs):
        # 性能监控阈值
        self.cpu_threshold = kwargs.get('cpu_threshold', 80)  # CPU使用率阈值(%)
        self.memory_threshold = kwargs.get('memory_threshold', 80)  # 内存使用率阈值(%)
        self.disk_threshold = kwargs.get('disk_threshold', 90)  # 磁盘使用率阈值(%)
        self.response_threshold = kwargs.get('response_threshold', 1.0)  # 响应时间阈值(秒)
        
        # CPU监控配置
        self.cpu_interval = kwargs.get('cpu_interval', 1.0)  # CPU采样间隔(秒)
        self.cpu_average_window = kwargs.get('cpu_average_window', 5)  # CPU使用率平均窗口大小
        self.cpu_per_core = kwargs.get('cpu_per_core', False)  # 是否按每个核心监控
        
        # 监控配置
        self.update_interval = kwargs.get('update_interval', 1.0)  # 更新间隔(秒)
        self.metrics_history_size = kwargs.get('metrics_history_size', 100)  # 历史数据大小
        self.monitor_cpu = kwargs.get('monitor_cpu', True)  # 是否监控CPU
        self.monitor_memory = kwargs.get('monitor_memory', True)  # 是否监控内存
        self.monitor_disk = kwargs.get('monitor_disk', True)  # 是否监控磁盘
        self.log_to_file = kwargs.get('log_to_file', True)  # 是否记录日志到文件
        
    def get(self, key: str, default=None):
        """获取配置项
        
        Args:
            key: 配置项名称
            default: 默认值
            
        Returns:
            配置项值
        """
        return getattr(self, key, default)
        
    def set(self, key: str, value):
        """设置配置项
        
        Args:
            key: 配置项名称
            value: 配置项值
        """
        setattr(self, key, value)
        
    def to_dict(self) -> dict:
        """转换为字典
        
        Returns:
            配置字典
        """
        return {
            'cpu_threshold': self.cpu_threshold,
            'memory_threshold': self.memory_threshold,
            'disk_threshold': self.disk_threshold,
            'response_threshold': self.response_threshold,
            'cpu_interval': self.cpu_interval,
            'cpu_average_window': self.cpu_average_window,
            'cpu_per_core': self.cpu_per_core,
            'update_interval': self.update_interval,
            'metrics_history_size': self.metrics_history_size,
            'monitor_cpu': self.monitor_cpu,
            'monitor_memory': self.monitor_memory,
            'monitor_disk': self.monitor_disk,
            'log_to_file': self.log_to_file
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'PerformanceConfig':
        """从字典创建配置
        
        Args:
            data: 配置字典
            
        Returns:
            PerformanceConfig实例
        """
        return cls(
            cpu_threshold=data.get('cpu_threshold', 80),
            memory_threshold=data.get('memory_threshold', 80),
            disk_threshold=data.get('disk_threshold', 90),
            response_threshold=data.get('response_threshold', 1.0),
            cpu_interval=data.get('cpu_interval', 1.0),
            cpu_average_window=data.get('cpu_average_window', 5),
            cpu_per_core=data.get('cpu_per_core', False),
            update_interval=data.get('update_interval', 1.0),
            metrics_history_size=data.get('metrics_history_size', 100),
            monitor_cpu=data.get('monitor_cpu', True),
            monitor_memory=data.get('monitor_memory', True),
            monitor_disk=data.get('monitor_disk', True),
            log_to_file=data.get('log_to_file', True)
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
class LoggingConfig(QObject):
    """日志配置类"""
    
    # 定义信号
    config_changed = pyqtSignal(object)  # 配置变更信号
    
    def __init__(self, **kwargs):
        """初始化日志配置
        
        Args:
            **kwargs: 配置参数
        """
        super().__init__()
        
        # 设置默认值
        self.level = kwargs.get("level", "INFO")
        self.save_to_file = kwargs.get("save_to_file", True)
        self.log_file = kwargs.get("log_file", "hikyuu_ui.log")
        self.max_bytes = kwargs.get("max_bytes", 10 * 1024 * 1024)  # 10MB
        self.backup_count = kwargs.get("backup_count", 5)
        self.console_output = kwargs.get("console_output", True)
        self.auto_compress = kwargs.get("auto_compress", True)
        self.max_logs = kwargs.get("max_logs", 1000)
        self.performance_log = kwargs.get("performance_log", True)
        self.performance_log_file = kwargs.get("performance_log_file", "performance.log")
        self.exception_log = kwargs.get("exception_log", True)
        self.exception_log_file = kwargs.get("exception_log_file", "exceptions.log")
        self.async_logging = kwargs.get("async_logging", True)
        self.log_queue_size = kwargs.get("log_queue_size", 1000)
        self.worker_threads = kwargs.get("worker_threads", 2)

    def validate(self) -> tuple[bool, str]:
        """验证配置是否有效
        
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        # 验证日志级别
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level not in valid_levels:
            return False, f"无效的日志级别: {self.level}，必须是 {', '.join(valid_levels)} 之一"
            
        # 验证工作线程数
        if self.worker_threads <= 0:
            return False, "工作线程数必须大于0"
            
        # 验证日志队列大小
        if self.log_queue_size <= 0:
            return False, "日志队列大小必须大于0"
            
        # 验证文件路径
        if self.save_to_file:
            if not self.log_file:
                return False, "日志文件名不能为空"
            if not self.log_file.endswith('.log'):
                return False, "日志文件必须以.log结尾"
                
        # 验证性能日志配置
        if self.performance_log:
            if not self.performance_log_file:
                return False, "性能日志文件名不能为空"
            if not self.performance_log_file.endswith('.log'):
                return False, "性能日志文件必须以.log结尾"
                
        # 验证异常日志配置
        if self.exception_log:
            if not self.exception_log_file:
                return False, "异常日志文件名不能为空"
            if not self.exception_log_file.endswith('.log'):
                return False, "异常日志文件必须以.log结尾"
                
        return True, "配置验证通过"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            配置字典
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
        """从字典创建配置
        
        Args:
            data: 配置字典
            
        Returns:
            LoggingConfig实例
        """
        config = cls()
        
        # 更新配置
        config.level = data.get("level", "INFO")
        config.save_to_file = data.get("save_to_file", True)
        config.log_file = data.get("log_file", "hikyuu_ui.log")
        config.max_bytes = data.get("max_bytes", 10 * 1024 * 1024)
        config.backup_count = data.get("backup_count", 5)
        config.console_output = data.get("console_output", True)
        config.auto_compress = data.get("auto_compress", True)
        config.max_logs = data.get("max_logs", 1000)
        config.performance_log = data.get("performance_log", True)
        config.performance_log_file = data.get("performance_log_file", "performance.log")
        config.exception_log = data.get("exception_log", True)
        config.exception_log_file = data.get("exception_log_file", "exceptions.log")
        config.async_logging = data.get("async_logging", True)
        config.log_queue_size = data.get("log_queue_size", 1000)
        config.worker_threads = data.get("worker_threads", 2)
        
        return config
        
    def update(self, **kwargs):
        """更新配置
        
        Args:
            **kwargs: 要更新的配置项
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
        # 发送配置变更信号
        self.config_changed.emit(self)

class UIStyleConfig:
    """UI样式配置"""
    font_family: str = "Microsoft YaHei"  # 默认使用微软雅黑
    font_size: int = 10
    # ... existing code ... 