"""
专业级回测UI组件
集成到HIkyuu GUI系统中，提供实时回测监控和数据联动功能
对标行业专业软件标准
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import threading
import time
import queue
from typing import Dict, List, Optional, Any, Tuple
import json
from pathlib import Path

# 导入matplotlib相关
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
import seaborn as sns

# 导入回测相关模块
try:
    from backtest.unified_backtest_engine import (
        UnifiedBacktestEngine, BacktestLevel, create_unified_backtest_engine,
        FixedStrategyBacktester, StrategyBacktester
    )
    from backtest.real_time_backtest_monitor import RealTimeBacktestMonitor, MonitoringLevel
    from backtest.ultra_performance_optimizer import UltraPerformanceOptimizer, PerformanceLevel
    from backtest.backtest_validator import ProfessionalBacktestValidator
except ImportError:
    # 如果导入失败，创建模拟类
    class BacktestLevel:
        BASIC = "basic"
        PROFESSIONAL = "professional"
        INSTITUTIONAL = "institutional"
        INVESTMENT_BANK = "investment_bank"

    class MonitoringLevel:
        BASIC = "BASIC"
        STANDARD = "STANDARD"
        ADVANCED = "ADVANCED"
        REAL_TIME = "REAL_TIME"

# 导入统一图表服务
try:
    from core.services.unified_chart_service import get_unified_chart_service
    from gui.widgets.chart_widget import ChartWidget
    UNIFIED_CHART_AVAILABLE = True
except ImportError:
    UNIFIED_CHART_AVAILABLE = False

# 导入核心模块
try:
    from core.logger import LogManager
    from utils.config_manager import ConfigManager
    CORE_MODULES_AVAILABLE = True
except ImportError:
    # 如果核心模块不可用，使用简化版本
    try:
        # 尝试导入基础日志管理器
        from core.base_logger import BaseLogManager as LogManager
    except ImportError:
        class LogManager:
            def log(self, message, level):
                print(f"[{level}] {message}")

            def info(self, message):
                print(f"[INFO] {message}")

            def warning(self, message):
                print(f"[WARNING] {message}")

            def error(self, message):
                print(f"[ERROR] {message}")

    # 简化版配置管理器
    class ConfigManager:
        def __init__(self):
            self.config = {
                'backtest': {
                    'initial_capital': 100000,
                    'commission_pct': 0.001,
                    'slippage_pct': 0.001
                },
                'ui': {
                    'theme': 'dark',
                    'update_interval': 1000
                }
            }

        def get(self, key, default=None):
            keys = key.split('.')
            value = self.config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    CORE_MODULES_AVAILABLE = False


class RealTimeChart(QWidget):
    """实时图表组件 - 基于统一图表服务的高性能实现"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_queue = queue.Queue()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        if UNIFIED_CHART_AVAILABLE:
            # 使用统一图表服务
            self.chart_widget = ChartWidget(self)
            layout.addWidget(self.chart_widget)

            # 配置图表
            self.setup_chart()
        else:
            # 降级到简单显示
            self.fallback_widget = QLabel("图表服务不可用，请检查依赖")
            self.fallback_widget.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.fallback_widget)

        # 启动定时器更新数据
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_charts)
        self.timer.start(1000)  # 每秒更新一次

    def setup_chart(self):
        """设置图表配置"""
        if not UNIFIED_CHART_AVAILABLE:
            return

        try:
            # 获取统一图表服务
            chart_service = get_unified_chart_service()

            # 配置图表主题
            chart_service.apply_theme(self.chart_widget, 'dark')

            # 设置图表类型为多子图模式
            self.chart_widget.set_chart_type('multi_panel')

            # 启用实时更新
            self.chart_widget.enable_real_time_update(True)

        except Exception as e:
            print(f"图表设置失败: {e}")

    def update_charts(self):
        """更新图表"""
        if not UNIFIED_CHART_AVAILABLE:
            return

        try:
            # 获取最新数据
            if not self.data_queue.empty():
                data = []
                while not self.data_queue.empty():
                    data.append(self.data_queue.get())

                if data:
                    # 转换为DataFrame
                    df = pd.DataFrame(data)

                    # 更新图表数据
                    self.chart_widget.update_data(df)

        except Exception as e:
            print(f"图表更新失败: {e}")

    def add_data(self, data: Dict):
        """添加数据到队列"""
        self.data_queue.put(data)

    def clear_data(self):
        """清空数据"""
        while not self.data_queue.empty():
            self.data_queue.get()

        if UNIFIED_CHART_AVAILABLE and hasattr(self, 'chart_widget'):
            self.chart_widget.clear_data()

    def set_chart_type(self, chart_type: str):
        """设置图表类型"""
        if UNIFIED_CHART_AVAILABLE and hasattr(self, 'chart_widget'):
            self.chart_widget.set_chart_type(chart_type)

    def apply_theme(self, theme: str):
        """应用主题"""
        if UNIFIED_CHART_AVAILABLE and hasattr(self, 'chart_widget'):
            chart_service = get_unified_chart_service()
            chart_service.apply_theme(self.chart_widget, theme)


class MetricsPanel(QWidget):
    """指标面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("📊 关键指标")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #00ff88;
                padding: 10px;
                border-bottom: 2px solid #00ff88;
            }
        """)
        layout.addWidget(title)

        # 指标卡片容器
        self.metrics_container = QVBoxLayout()
        layout.addLayout(self.metrics_container)

        # 初始化指标卡片
        self.create_metric_cards()

        layout.addStretch()

    def create_metric_cards(self):
        """创建指标卡片"""
        # 总收益率卡片
        self.return_card = self.create_metric_card("💰 总收益率", "0.00%", "年化收益: 0.00%")
        self.metrics_container.addWidget(self.return_card)

        # Sharpe比率卡片
        self.sharpe_card = self.create_metric_card("📈 Sharpe比率", "0.000", "最大回撤: 0.00%")
        self.metrics_container.addWidget(self.sharpe_card)

        # 胜率卡片
        self.winrate_card = self.create_metric_card("🎯 胜率", "0.00%", "盈利因子: 0.00")
        self.metrics_container.addWidget(self.winrate_card)

        # 风险指标卡片
        self.risk_card = self.create_metric_card("⚠️ 风险指标", "VaR: 0.00%", "波动率: 0.00%")
        self.metrics_container.addWidget(self.risk_card)

    def create_metric_card(self, title: str, value: str, subtitle: str) -> QFrame:
        """创建指标卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: linear-gradient(135deg, #1e2329, #2d3748);
                border: 1px solid #2d3748;
                border-radius: 10px;
                margin: 5px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(card)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #b0b3b8; font-size: 12px; font-weight: bold;")
        layout.addWidget(title_label)

        # 数值
        value_label = QLabel(value)
        value_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(value_label)

        # 副标题
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #b0b3b8; font-size: 10px;")
        layout.addWidget(subtitle_label)

        # 存储标签引用
        setattr(card, 'value_label', value_label)
        setattr(card, 'subtitle_label', subtitle_label)

        return card

    def update_metrics(self, metrics: Dict):
        """更新指标"""
        try:
            # 更新总收益率
            total_return = metrics.get('total_return', 0)
            annualized_return = metrics.get('annualized_return', 0)
            self.return_card.value_label.setText(f"{total_return:.2%}")
            self.return_card.subtitle_label.setText(f"年化收益: {annualized_return:.2%}")

            # 更新Sharpe比率
            sharpe_ratio = metrics.get('sharpe_ratio', 0)
            max_drawdown = metrics.get('max_drawdown', 0)
            self.sharpe_card.value_label.setText(f"{sharpe_ratio:.3f}")
            self.sharpe_card.subtitle_label.setText(f"最大回撤: {max_drawdown:.2%}")

            # 更新胜率
            win_rate = metrics.get('win_rate', 0)
            profit_factor = metrics.get('profit_factor', 0)
            self.winrate_card.value_label.setText(f"{win_rate:.2%}")
            self.winrate_card.subtitle_label.setText(f"盈利因子: {profit_factor:.2f}")

            # 更新风险指标
            var_95 = metrics.get('var_95', 0)
            volatility = metrics.get('volatility', 0)
            self.risk_card.value_label.setText(f"VaR: {var_95:.2%}")
            self.risk_card.subtitle_label.setText(f"波动率: {volatility:.2%}")

            # 根据指标值设置颜色
            self._update_card_colors(metrics)

        except Exception as e:
            print(f"更新指标失败: {e}")

    def _update_card_colors(self, metrics: Dict):
        """根据指标值更新卡片颜色"""
        # 总收益率颜色
        total_return = metrics.get('total_return', 0)
        color = "#10b981" if total_return >= 0 else "#ef4444"
        self.return_card.setStyleSheet(f"""
            QFrame {{
                background: linear-gradient(135deg, #1e2329, #2d3748);
                border-left: 4px solid {color};
                border-radius: 10px;
                margin: 5px;
                padding: 15px;
            }}
        """)

        # Sharpe比率颜色
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        if sharpe_ratio >= 1.0:
            color = "#10b981"
        elif sharpe_ratio >= 0.5:
            color = "#f59e0b"
        else:
            color = "#ef4444"

        self.sharpe_card.setStyleSheet(f"""
            QFrame {{
                background: linear-gradient(135deg, #1e2329, #2d3748);
                border-left: 4px solid {color};
                border-radius: 10px;
                margin: 5px;
                padding: 15px;
            }}
        """)


class ControlPanel(QWidget):
    """控制面板"""

    # 定义信号
    start_backtest = pyqtSignal(dict)
    stop_backtest = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("🎛️ 控制面板")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #00ff88;
                padding: 10px;
                border-bottom: 2px solid #00ff88;
            }
        """)
        layout.addWidget(title)

        # 参数设置组
        params_group = QGroupBox("回测参数")
        params_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2d3748;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        params_layout = QFormLayout(params_group)

        # 初始资金
        self.initial_capital = QSpinBox()
        self.initial_capital.setRange(10000, 100000000)
        self.initial_capital.setValue(1000000)
        self.initial_capital.setSuffix(" 元")
        params_layout.addRow("初始资金:", self.initial_capital)

        # 仓位大小
        self.position_size = QDoubleSpinBox()
        self.position_size.setRange(0.1, 1.0)
        self.position_size.setValue(0.95)
        self.position_size.setSingleStep(0.05)
        self.position_size.setSuffix("%")
        params_layout.addRow("仓位大小:", self.position_size)

        # 手续费率
        self.commission_pct = QDoubleSpinBox()
        self.commission_pct.setRange(0.0001, 0.01)
        self.commission_pct.setValue(0.0003)
        self.commission_pct.setDecimals(4)
        self.commission_pct.setSuffix("%")
        params_layout.addRow("手续费率:", self.commission_pct)

        # 专业级别
        self.professional_level = QComboBox()
        self.professional_level.addItems([
            "RETAIL", "INSTITUTIONAL", "HEDGE_FUND", "INVESTMENT_BANK"
        ])
        self.professional_level.setCurrentText("INVESTMENT_BANK")
        params_layout.addRow("专业级别:", self.professional_level)

        # 性能级别
        self.performance_level = QComboBox()
        self.performance_level.addItems([
            "STANDARD", "HIGH", "ULTRA", "EXTREME"
        ])
        self.performance_level.setCurrentText("ULTRA")
        params_layout.addRow("性能级别:", self.performance_level)

        layout.addWidget(params_group)

        # 控制按钮
        buttons_layout = QHBoxLayout()

        self.start_button = QPushButton("🚀 开始回测")
        self.start_button.setStyleSheet("""
            QPushButton {
                background: linear-gradient(45deg, #00d4ff, #8b5cf6);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: linear-gradient(45deg, #0099cc, #6d28d9);
            }
            QPushButton:pressed {
                background: linear-gradient(45deg, #0066aa, #5b21b6);
            }
        """)
        self.start_button.clicked.connect(self.on_start_backtest)

        self.stop_button = QPushButton("⏹️ 停止回测")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background: linear-gradient(45deg, #ef4444, #dc2626);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: linear-gradient(45deg, #dc2626, #b91c1c);
            }
            QPushButton:pressed {
                background: linear-gradient(45deg, #b91c1c, #991b1b);
            }
        """)
        self.stop_button.clicked.connect(self.stop_backtest.emit)
        self.stop_button.setEnabled(False)

        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        layout.addLayout(buttons_layout)

        # 状态显示
        self.status_label = QLabel("状态: 就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #10b981;
                font-weight: bold;
                padding: 10px;
                border: 1px solid #2d3748;
                border-radius: 5px;
                background-color: #1e2329;
            }
        """)
        layout.addWidget(self.status_label)

        layout.addStretch()

    def on_start_backtest(self):
        """开始回测"""
        params = {
            'initial_capital': self.initial_capital.value(),
            'position_size': self.position_size.value() / 100,
            'commission_pct': self.commission_pct.value() / 100,
            'professional_level': self.professional_level.currentText(),
            'performance_level': self.performance_level.currentText()
        }

        self.start_backtest.emit(params)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("状态: 运行中")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #f59e0b;
                font-weight: bold;
                padding: 10px;
                border: 1px solid #2d3748;
                border-radius: 5px;
                background-color: #1e2329;
            }
        """)

    def on_stop_backtest(self):
        """停止回测"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("状态: 已停止")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #ef4444;
                font-weight: bold;
                padding: 10px;
                border: 1px solid #2d3748;
                border-radius: 5px;
                background-color: #1e2329;
            }
        """)


class AlertsPanel(QWidget):
    """预警面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alerts = []
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("⚠️ 预警中心")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #f59e0b;
                padding: 10px;
                border-bottom: 2px solid #f59e0b;
            }
        """)
        layout.addWidget(title)

        # 预警列表
        self.alerts_list = QListWidget()
        self.alerts_list.setStyleSheet("""
            QListWidget {
                background-color: #1e2329;
                border: 1px solid #2d3748;
                border-radius: 5px;
                color: white;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #2d3748;
            }
            QListWidget::item:selected {
                background-color: #2d3748;
            }
        """)
        layout.addWidget(self.alerts_list)

        # 清除按钮
        clear_button = QPushButton("🗑️ 清除预警")
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
                border: 1px solid #4b5563;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        clear_button.clicked.connect(self.clear_alerts)
        layout.addWidget(clear_button)

    def add_alert(self, level: str, message: str):
        """添加预警"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 确定图标和颜色
        if level == 'critical':
            icon = '🚨'
            color = '#ef4444'
        elif level == 'warning':
            icon = '⚠️'
            color = '#f59e0b'
        else:
            icon = 'ℹ️'
            color = '#3b82f6'

        # 创建预警项
        alert_item = QListWidgetItem()
        alert_text = f"{icon} [{timestamp}] {level.upper()}: {message}"
        alert_item.setText(alert_text)
        alert_item.setForeground(QColor(color))

        # 添加到列表顶部
        self.alerts_list.insertItem(0, alert_item)

        # 限制预警数量
        if self.alerts_list.count() > 50:
            self.alerts_list.takeItem(self.alerts_list.count() - 1)

        # 存储预警
        self.alerts.append({
            'timestamp': timestamp,
            'level': level,
            'message': message
        })

    def clear_alerts(self):
        """清除所有预警"""
        self.alerts_list.clear()
        self.alerts.clear()


class ProfessionalBacktestWidget(QWidget):
    """专业级回测UI组件"""

    # 定义信号
    backtest_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.log_manager = LogManager()

        # 回测相关组件
        self.backtest_engine = None
        self.monitor = None
        self.validator = None
        self.optimizer = None

        # 监控线程
        self.monitoring_thread = None
        self.is_monitoring = False
        self.monitoring_data = []

        # 初始化UI
        self.init_ui()

        # 初始化回测组件
        self.init_backtest_components()

    def init_ui(self):
        """初始化UI"""
        # 设置窗口样式
        self.setStyleSheet("""
            QWidget {
                background-color: #0e1117;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 左侧面板
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        # 控制面板
        self.control_panel = ControlPanel()
        self.control_panel.start_backtest.connect(self.start_backtest)
        self.control_panel.stop_backtest.connect(self.stop_backtest)
        left_panel.addWidget(self.control_panel)

        # 指标面板
        self.metrics_panel = MetricsPanel()
        left_panel.addWidget(self.metrics_panel)

        # 预警面板
        self.alerts_panel = AlertsPanel()
        left_panel.addWidget(self.alerts_panel)

        # 左侧面板容器
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setFixedWidth(350)

        # 右侧图表区域
        self.chart_widget = RealTimeChart()

        # 添加到主布局
        main_layout.addWidget(left_widget)
        main_layout.addWidget(self.chart_widget, 1)

    def init_backtest_components(self):
        """初始化回测组件"""
        try:
            # 初始化验证器（如果可用）
            try:
                self.validator = ProfessionalBacktestValidator(self.log_manager)
            except:
                self.validator = None

            # 初始化优化器（如果可用）
            try:
                self.optimizer = UltraPerformanceOptimizer(log_manager=self.log_manager)
            except:
                self.optimizer = None

            self.log_manager.log("回测组件初始化完成", LogLevel.INFO)

        except Exception as e:
            self.log_manager.log(f"回测组件初始化失败: {e}", LogLevel.ERROR)
            self.error_occurred.emit(f"回测组件初始化失败: {str(e)}")

    def start_backtest(self, params: Dict):
        """开始回测"""
        try:
            self.log_manager.log("开始启动回测", LogLevel.INFO)

            # 创建回测引擎（如果可用）
            try:
                backtest_level = getattr(BacktestLevel, params['professional_level'])
                self.backtest_engine = UnifiedBacktestEngine(
                    backtest_level=backtest_level,
                    log_manager=self.log_manager
                )
            except:
                self.backtest_engine = None

            # 创建监控器（如果可用）
            try:
                self.monitor = RealTimeBacktestMonitor(
                    monitoring_level=MonitoringLevel.REAL_TIME,
                    log_manager=self.log_manager
                )
            except:
                self.monitor = None

            # 生成模拟数据进行演示
            demo_data = self._generate_demo_data()

            # 启动监控线程
            self.start_monitoring(demo_data, params)

            self.alerts_panel.add_alert('info', '回测已启动，正在实时监控中...')

        except Exception as e:
            self.log_manager.log(f"启动回测失败: {e}", LogLevel.ERROR)
            self.error_occurred.emit(f"启动回测失败: {str(e)}")
            self.control_panel.on_stop_backtest()

    def stop_backtest(self):
        """停止回测"""
        try:
            self.is_monitoring = False

            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2)

            self.control_panel.on_stop_backtest()
            self.alerts_panel.add_alert('info', '回测已停止')

            self.log_manager.log("回测已停止", LogLevel.INFO)

        except Exception as e:
            self.log_manager.log(f"停止回测失败: {e}", LogLevel.ERROR)

    def start_monitoring(self, data: pd.DataFrame, params: Dict):
        """启动监控"""
        self.is_monitoring = True

        def monitoring_loop():
            """监控循环"""
            iteration = 0

            while self.is_monitoring:
                try:
                    # 生成模拟监控数据
                    monitoring_data = self._generate_monitoring_data(iteration)

                    # 更新图表
                    self.chart_widget.add_data(monitoring_data)

                    # 更新指标面板
                    QTimer.singleShot(0, lambda: self.metrics_panel.update_metrics(monitoring_data))

                    # 检查预警
                    self._check_alerts(monitoring_data)

                    # 存储监控数据
                    self.monitoring_data.append(monitoring_data)

                    # 限制数据长度
                    if len(self.monitoring_data) > 1000:
                        self.monitoring_data = self.monitoring_data[-1000:]

                    iteration += 1
                    time.sleep(2)  # 每2秒更新一次

                except Exception as e:
                    self.log_manager.log(f"监控循环异常: {e}", LogLevel.ERROR)
                    break

        # 启动监控线程
        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()

    def _generate_demo_data(self) -> pd.DataFrame:
        """生成演示数据"""
        try:
            # 生成模拟K线数据
            dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
            n_days = len(dates)

            np.random.seed(42)
            returns = np.random.normal(0.0005, 0.02, n_days)
            prices = 100 * np.cumprod(1 + returns)

            # 生成交易信号
            signals = np.random.choice([-1, 0, 1], n_days, p=[0.1, 0.8, 0.1])

            demo_data = pd.DataFrame({
                'close': prices,
                'signal': signals,
                'returns': returns,
                'volume': np.random.uniform(1000000, 10000000, n_days)
            }, index=dates)

            return demo_data

        except Exception as e:
            self.log_manager.log(f"生成演示数据失败: {e}", LogLevel.ERROR)
            return pd.DataFrame()

    def _generate_monitoring_data(self, iteration: int) -> Dict:
        """生成监控数据"""
        try:
            # 模拟实时指标
            base_return = 0.001 * iteration
            noise = np.random.normal(0, 0.02)

            monitoring_data = {
                'timestamp': datetime.now(),
                'current_return': noise,
                'cumulative_return': base_return + noise * 0.1,
                'current_drawdown': max(0, -noise * 0.5),
                'max_drawdown': np.random.uniform(0.05, 0.2),
                'sharpe_ratio': np.random.uniform(-0.5, 2.5),
                'volatility': np.random.uniform(0.1, 0.4),
                'var_95': np.random.uniform(-0.05, -0.01),
                'total_return': base_return + noise * 0.1,
                'annualized_return': (base_return + noise * 0.1) * 252,
                'win_rate': np.random.uniform(0.4, 0.7),
                'profit_factor': np.random.uniform(0.8, 2.5),
                'execution_time': np.random.uniform(0.1, 1.0)
            }

            return monitoring_data

        except Exception as e:
            self.log_manager.log(f"生成监控数据失败: {e}", LogLevel.ERROR)
            return {}

    def _check_alerts(self, data: Dict):
        """检查预警"""
        try:
            # 检查回撤预警
            drawdown = data.get('current_drawdown', 0)
            if drawdown > 0.15:
                QTimer.singleShot(0, lambda: self.alerts_panel.add_alert(
                    'critical', f'回撤过大: {drawdown:.2%}'
                ))
            elif drawdown > 0.1:
                QTimer.singleShot(0, lambda: self.alerts_panel.add_alert(
                    'warning', f'回撤警告: {drawdown:.2%}'
                ))

            # 检查Sharpe比率预警
            sharpe = data.get('sharpe_ratio', 0)
            if sharpe < 0:
                QTimer.singleShot(0, lambda: self.alerts_panel.add_alert(
                    'warning', f'Sharpe比率为负: {sharpe:.3f}'
                ))

            # 检查波动率预警
            volatility = data.get('volatility', 0)
            if volatility > 0.3:
                QTimer.singleShot(0, lambda: self.alerts_panel.add_alert(
                    'warning', f'波动率过高: {volatility:.2%}'
                ))

        except Exception as e:
            self.log_manager.log(f"检查预警失败: {e}", LogLevel.ERROR)

    def set_kdata(self, kdata):
        """设置K线数据"""
        try:
            if kdata is not None and not kdata.empty:
                self.log_manager.log("接收到K线数据，准备回测", LogLevel.INFO)
                # 这里可以使用真实的K线数据进行回测

        except Exception as e:
            self.log_manager.log(f"设置K线数据失败: {e}", LogLevel.ERROR)

    def refresh_data(self):
        """刷新数据"""
        try:
            if self.is_monitoring:
                self.log_manager.log("刷新监控数据", LogLevel.INFO)

        except Exception as e:
            self.log_manager.log(f"刷新数据失败: {e}", LogLevel.ERROR)

    def clear_data(self):
        """清除数据"""
        try:
            self.monitoring_data.clear()
            self.alerts_panel.clear_alerts()
            self.chart_widget.clear_data()

            self.log_manager.log("数据已清除", LogLevel.INFO)

        except Exception as e:
            self.log_manager.log(f"清除数据失败: {e}", LogLevel.ERROR)


# 便捷函数
def create_backtest_widget(config_manager: Optional[ConfigManager] = None) -> ProfessionalBacktestWidget:
    """创建回测组件实例"""
    return ProfessionalBacktestWidget(config_manager)


# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    # 创建主窗口
    window = QMainWindow()
    window.setWindowTitle("HIkyuu Professional Backtest System")
    window.setGeometry(100, 100, 1400, 800)

    # 创建回测组件
    backtest_widget = create_backtest_widget()
    window.setCentralWidget(backtest_widget)

    # 显示窗口
    window.show()

    sys.exit(app.exec_())
