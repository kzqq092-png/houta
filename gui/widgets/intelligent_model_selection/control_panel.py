"""
智能模型选择控制面板

提供智能模型选择功能的控制界面，包括：
- 系统状态监控
- 配置参数设置
- 快捷操作控制
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QGroupBox, QLabel, QPushButton, QLCDNumber, QDoubleSpinBox, 
    QSpinBox, QScrollArea, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from core.ai.intelligent_selection import IntelligentModelSelector

logger = logging.getLogger(__name__)


class IntelligentModelControlPanel(QWidget):
    """智能模型选择控制面板"""
    
    # 信号定义
    config_changed = pyqtSignal(dict)  # 配置变更信号
    strategy_toggled = pyqtSignal(bool)  # 策略开关信号
    emergency_fallback = pyqtSignal()  # 紧急切换信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.intelligent_selector = None
        self.current_config = {}
        self.status_data = {}
        self.init_ui()
        self.setup_connections()
        self.start_monitoring()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setMinimumSize(400, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. 状态概览区域
        status_area = self._create_status_area()
        layout.addWidget(status_area)
        
        # 2. 配置参数区域
        config_area = self._create_config_area()
        layout.addWidget(config_area)
        
        # 3. 操作控制区域
        control_area = self._create_control_area()
        layout.addWidget(control_area)
        
        # 应用统一样式
        self._apply_unified_styles()
    
    def _create_status_area(self) -> QGroupBox:
        """创建状态概览区域"""
        status_group = QGroupBox("系统状态")
        status_layout = QGridLayout(status_group)
        
        # 系统运行状态
        self.status_label = QLabel("🟢 运行中")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
        """)
        status_layout.addWidget(self.status_label, 0, 0)
        
        # 活跃模型数量
        status_layout.addWidget(QLabel("活跃模型:"), 0, 1)
        self.active_models_lcd = QLCDNumber(2)
        self.active_models_lcd.setStyleSheet("QLCDNumber { background-color: #2c3e50; color: #3498db; }")
        status_layout.addWidget(self.active_models_lcd, 0, 2)
        
        # 今日预测次数
        status_layout.addWidget(QLabel("今日预测:"), 1, 0)
        self.predictions_today_lcd = QLCDNumber(4)
        self.predictions_today_lcd.setStyleSheet("QLCDNumber { background-color: #2c3e50; color: #e74c3c; }")
        status_layout.addWidget(self.predictions_today_lcd, 1, 2)
        
        # 当前策略
        status_layout.addWidget(QLabel("当前策略:"), 1, 1)
        self.strategy_label = QLabel("📊 智能自适应")
        self.strategy_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        status_layout.addWidget(self.strategy_label, 1, 2)
        
        return status_group
    
    def _create_config_area(self) -> QScrollArea:
        """创建配置参数区域"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setSpacing(15)
        
        # 市场检测设置
        market_group = QGroupBox("市场检测设置")
        market_layout = QFormLayout(market_group)
        
        self.high_vol_threshold = QDoubleSpinBox()
        self.high_vol_threshold.setRange(0.0, 1.0)
        self.high_vol_threshold.setSingleStep(0.01)
        self.high_vol_threshold.setValue(0.30)
        self.high_vol_threshold.setSuffix(" (0-1)")
        self.high_vol_threshold.valueChanged.connect(self._on_config_changed)
        market_layout.addRow("高波动率阈值:", self.high_vol_threshold)
        
        self.low_vol_threshold = QDoubleSpinBox()
        self.low_vol_threshold.setRange(0.0, 1.0)
        self.low_vol_threshold.setSingleStep(0.01)
        self.low_vol_threshold.setValue(0.10)
        self.low_vol_threshold.setSuffix(" (0-1)")
        self.low_vol_threshold.valueChanged.connect(self._on_config_changed)
        market_layout.addRow("低波动率阈值:", self.low_vol_threshold)
        
        self.high_trend_threshold = QDoubleSpinBox()
        self.high_trend_threshold.setRange(0.0, 1.0)
        self.high_trend_threshold.setSingleStep(0.01)
        self.high_trend_threshold.setValue(0.70)
        self.high_trend_threshold.setSuffix(" (0-1)")
        self.high_trend_threshold.valueChanged.connect(self._on_config_changed)
        market_layout.addRow("强趋势阈值:", self.high_trend_threshold)
        
        self.low_trend_threshold = QDoubleSpinBox()
        self.low_trend_threshold.setRange(0.0, 1.0)
        self.low_trend_threshold.setSingleStep(0.01)
        self.low_trend_threshold.setValue(0.30)
        self.low_trend_threshold.setSuffix(" (0-1)")
        self.low_trend_threshold.valueChanged.connect(self._on_config_changed)
        market_layout.addRow("弱趋势阈值:", self.low_trend_threshold)
        
        config_layout.addWidget(market_group)
        
        # 性能评估设置
        performance_group = QGroupBox("性能评估设置")
        performance_layout = QFormLayout(performance_group)
        
        self.min_samples = QSpinBox()
        self.min_samples.setRange(10, 1000)
        self.min_samples.setValue(100)
        self.min_samples.valueChanged.connect(self._on_config_changed)
        performance_layout.addRow("最低样本数:", self.min_samples)
        
        # 权重配置
        weights_layout = QGridLayout()
        
        self.accuracy_weight = QSpinBox()
        self.accuracy_weight.setRange(0, 100)
        self.accuracy_weight.setValue(30)
        self.accuracy_weight.valueChanged.connect(self._on_config_changed)
        weights_layout.addWidget(QLabel("准确率权重(%):"), 0, 0)
        weights_layout.addWidget(self.accuracy_weight, 0, 1)
        
        self.speed_weight = QSpinBox()
        self.speed_weight.setRange(0, 100)
        self.speed_weight.setValue(20)
        self.speed_weight.valueChanged.connect(self._on_config_changed)
        weights_layout.addWidget(QLabel("速度权重(%):"), 1, 0)
        weights_layout.addWidget(self.speed_weight, 1, 1)
        
        self.stability_weight = QSpinBox()
        self.stability_weight.setRange(0, 100)
        self.stability_weight.setValue(30)
        self.stability_weight.valueChanged.connect(self._on_config_changed)
        weights_layout.addWidget(QLabel("稳定性权重(%):"), 2, 0)
        weights_layout.addWidget(self.stability_weight, 2, 1)
        
        self.market_match_weight = QSpinBox()
        self.market_match_weight.setRange(0, 100)
        self.market_match_weight.setValue(20)
        self.market_match_weight.valueChanged.connect(self._on_config_changed)
        weights_layout.addWidget(QLabel("市场匹配权重(%):"), 3, 0)
        weights_layout.addWidget(self.market_match_weight, 3, 1)
        
        performance_layout.addRow(weights_layout)
        config_layout.addWidget(performance_group)
        
        # 选择策略设置
        strategy_group = QGroupBox("选择策略设置")
        strategy_layout = QFormLayout(strategy_group)
        
        self.max_models = QSpinBox()
        self.max_models.setRange(1, 10)
        self.max_models.setValue(3)
        self.max_models.valueChanged.connect(self._on_config_changed)
        strategy_layout.addRow("最大模型数:", self.max_models)
        
        self.max_latency = QSpinBox()
        self.max_latency.setRange(100, 10000)
        self.max_latency.setSingleStep(100)
        self.max_latency.setValue(1000)
        self.max_latency.setSuffix(" ms")
        self.max_latency.valueChanged.connect(self._on_config_changed)
        strategy_layout.addRow("延迟要求:", self.max_latency)
        
        self.min_accuracy = QDoubleSpinBox()
        self.min_accuracy.setRange(0.0, 1.0)
        self.min_accuracy.setSingleStep(0.01)
        self.min_accuracy.setValue(0.60)
        self.min_accuracy.setSuffix(" (0-1)")
        self.min_accuracy.valueChanged.connect(self._on_config_changed)
        strategy_layout.addRow("准确率要求:", self.min_accuracy)
        
        self.memory_limit = QSpinBox()
        self.memory_limit.setRange(512, 8192)
        self.memory_limit.setSingleStep(256)
        self.memory_limit.setValue(2048)
        self.memory_limit.setSuffix(" MB")
        self.memory_limit.valueChanged.connect(self._on_config_changed)
        strategy_layout.addRow("内存限制:", self.memory_limit)
        
        config_layout.addWidget(strategy_group)
        
        scroll_area.setWidget(config_widget)
        return scroll_area
    
    def _create_control_area(self) -> QGroupBox:
        """创建操作控制区域"""
        control_group = QGroupBox("快捷控制")
        control_layout = QHBoxLayout(control_group)
        
        # 启用/禁用按钮
        self.enable_button = QPushButton("🟢 启用智能选择")
        self.enable_button.setCheckable(True)
        self.enable_button.setChecked(True)
        self.enable_button.setMinimumHeight(40)
        self.enable_button.toggled.connect(self._on_toggle_selection)
        control_layout.addWidget(self.enable_button)
        
        # 重置配置按钮
        self.reset_button = QPushButton("🔄 重置配置")
        self.reset_button.setMinimumHeight(40)
        self.reset_button.clicked.connect(self._on_reset_config)
        control_layout.addWidget(self.reset_button)
        
        # 紧急切换按钮
        self.emergency_button = QPushButton("⚠️ 紧急切换")
        self.emergency_button.setMinimumHeight(40)
        self.emergency_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.emergency_button.clicked.connect(self.emergency_fallback.emit)
        control_layout.addWidget(self.emergency_button)
        
        control_layout.addStretch()
        
        return control_group
    
    def _apply_unified_styles(self):
        """应用统一样式"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin: 8px 0px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #2c3e50;
                font-weight: bold;
            }
            QSpinBox, QDoubleSpinBox {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #3498db;
            }
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:checked {
                background-color: #27ae60;
            }
            QPushButton:checked:hover {
                background-color: #229954;
            }
        """)
    
    def setup_connections(self):
        """设置信号连接"""
        # 初始化时触发一次配置变更
        self._on_config_changed()
    
    def start_monitoring(self):
        """启动状态监控"""
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._update_status_display)
        self.monitor_timer.start(2000)  # 每2秒更新一次状态
    
    def _on_config_changed(self):
        """配置变更处理"""
        try:
            config = {
                'market_detector': {
                    'high_volatility_threshold': self.high_vol_threshold.value(),
                    'low_volatility_threshold': self.low_vol_threshold.value(),
                    'strong_trend_threshold': self.high_trend_threshold.value(),
                    'weak_trend_threshold': self.low_trend_threshold.value()
                },
                'performance_evaluator': {
                    'min_samples': self.min_samples.value(),
                    'weights': {
                        'accuracy': self.accuracy_weight.value() / 100.0,
                        'speed': self.speed_weight.value() / 100.0,
                        'stability': self.stability_weight.value() / 100.0,
                        'market_match': self.market_match_weight.value() / 100.0
                    }
                },
                'selection_strategy': {
                    'max_models': self.max_models.value(),
                    'max_latency_ms': self.max_latency.value(),
                    'min_accuracy': self.min_accuracy.value(),
                    'memory_limit_mb': self.memory_limit.value()
                }
            }
            
            self.current_config = config
            self.config_changed.emit(config)
            logger.debug(f"配置已更新: {config}")
            
        except Exception as e:
            logger.error(f"配置更新失败: {e}")
    
    def _on_toggle_selection(self, enabled: bool):
        """策略开关处理"""
        try:
            if enabled:
                self.enable_button.setText("🟢 启用智能选择")
                self.enable_button.setStyleSheet("""
                    QPushButton {
                        background-color: #27ae60;
                        color: white;
                        font-weight: bold;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #229954;
                    }
                """)
            else:
                self.enable_button.setText("🔴 禁用智能选择")
                self.enable_button.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: white;
                        font-weight: bold;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                """)
            
            self.strategy_toggled.emit(enabled)
            logger.info(f"智能选择策略{'启用' if enabled else '禁用'}")
            
        except Exception as e:
            logger.error(f"策略开关处理失败: {e}")
    
    def _on_reset_config(self):
        """重置配置"""
        try:
            # 重置为默认值
            self.high_vol_threshold.setValue(0.30)
            self.low_vol_threshold.setValue(0.10)
            self.high_trend_threshold.setValue(0.70)
            self.low_trend_threshold.setValue(0.30)
            
            self.min_samples.setValue(100)
            self.accuracy_weight.setValue(30)
            self.speed_weight.setValue(20)
            self.stability_weight.setValue(30)
            self.market_match_weight.setValue(20)
            
            self.max_models.setValue(3)
            self.max_latency.setValue(1000)
            self.min_accuracy.setValue(0.60)
            self.memory_limit.setValue(2048)
            
            logger.info("配置已重置为默认值")
            
        except Exception as e:
            logger.error(f"配置重置失败: {e}")
    
    def _update_status_display(self):
        """更新状态显示"""
        try:
            # 从智能选择器获取状态数据
            if self.intelligent_selector and hasattr(self.intelligent_selector, 'get_status'):
                status_data = self.intelligent_selector.get_status()
            else:
                # 模拟数据用于演示
                status_data = {
                    'is_running': True,
                    'active_models': 4,
                    'predictions_today': 156,
                    'current_strategy': '智能自适应'
                }
            
            self.status_data = status_data
            self.update_status(status_data)
            
        except Exception as e:
            logger.error(f"更新状态显示失败: {e}")
    
    def update_status(self, status_data: Dict[str, Any]):
        """更新状态显示"""
        try:
            # 更新活跃模型数
            active_models = status_data.get('active_models', 0)
            self.active_models_lcd.display(active_models)
            
            # 更新预测次数
            predictions_today = status_data.get('predictions_today', 0)
            self.predictions_today_lcd.display(predictions_today)
            
            # 更新系统状态
            is_running = status_data.get('is_running', False)
            if is_running:
                self.status_label.setText("🟢 运行中")
                self.status_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        font-weight: bold;
                        padding: 8px 12px;
                        border-radius: 4px;
                        background-color: #d4edda;
                        color: #155724;
                        border: 1px solid #c3e6cb;
                    }
                """)
            else:
                self.status_label.setText("🔴 已停止")
                self.status_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        font-weight: bold;
                        padding: 8px 12px;
                        border-radius: 4px;
                        background-color: #f8d7da;
                        color: #721c24;
                        border: 1px solid #f5c6cb;
                    }
                """)
            
            # 更新当前策略
            current_strategy = status_data.get('current_strategy', '智能自适应')
            strategy_icon = "📊" if "智能" in current_strategy else "⚙️"
            self.strategy_label.setText(f"{strategy_icon} {current_strategy}")
            
        except Exception as e:
            logger.error(f"更新状态显示失败: {e}")
    
    def set_intelligent_selector(self, selector):
        """设置智能选择器引用"""
        self.intelligent_selector = selector
        logger.info("智能选择器引用已设置")
    
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.current_config.copy()
    
    def export_config(self, file_path: str):
        """导出配置到文件"""
        try:
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已导出到: {file_path}")
        except Exception as e:
            logger.error(f"配置导出失败: {e}")
    
    def import_config(self, file_path: str):
        """从文件导入配置"""
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新UI控件
            self._apply_config_to_ui(config)
            
            # 触发配置变更
            self._on_config_changed()
            
            logger.info(f"配置已从文件导入: {file_path}")
            
        except Exception as e:
            logger.error(f"配置导入失败: {e}")
    
    def _apply_config_to_ui(self, config: Dict[str, Any]):
        """将配置应用到UI控件"""
        try:
            market_config = config.get('market_detector', {})
            if market_config:
                self.high_vol_threshold.setValue(market_config.get('high_volatility_threshold', 0.30))
                self.low_vol_threshold.setValue(market_config.get('low_volatility_threshold', 0.10))
                self.high_trend_threshold.setValue(market_config.get('strong_trend_threshold', 0.70))
                self.low_trend_threshold.setValue(market_config.get('weak_trend_threshold', 0.30))
            
            performance_config = config.get('performance_evaluator', {})
            if performance_config:
                self.min_samples.setValue(performance_config.get('min_samples', 100))
                
                weights = performance_config.get('weights', {})
                if weights:
                    self.accuracy_weight.setValue(int(weights.get('accuracy', 0.3) * 100))
                    self.speed_weight.setValue(int(weights.get('speed', 0.2) * 100))
                    self.stability_weight.setValue(int(weights.get('stability', 0.3) * 100))
                    self.market_match_weight.setValue(int(weights.get('market_match', 0.2) * 100))
            
            strategy_config = config.get('selection_strategy', {})
            if strategy_config:
                self.max_models.setValue(strategy_config.get('max_models', 3))
                self.max_latency.setValue(strategy_config.get('max_latency_ms', 1000))
                self.min_accuracy.setValue(strategy_config.get('min_accuracy', 0.60))
                self.memory_limit.setValue(strategy_config.get('memory_limit_mb', 2048))
                
        except Exception as e:
            logger.error(f"应用配置到UI失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止监控定时器
            if hasattr(self, 'monitor_timer'):
                self.monitor_timer.stop()
            
            logger.info("智能模型选择控制面板已关闭")
            event.accept()
            
        except Exception as e:
            logger.error(f"面板关闭处理失败: {e}")
            event.accept()