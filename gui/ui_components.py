"""
UI components for the trading system

This module contains reusable UI components for the trading system.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QProgressBar, QTextEdit,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QStatusBar, QToolBar, QMenuBar, QMenu, QAction,
    QFileDialog, QMessageBox, QSplitter, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
import pandas as pd
import psutil
from datetime import datetime

class AnalysisToolsPanel(QWidget):
    """Analysis tools panel for the right side of the main window"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Strategy selection
        strategy_group = QGroupBox("策略选择")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "均线策略", "MACD策略", "RSI策略", "布林带策略",
            "自适应策略", "多因子策略", "机器学习策略", "深度学习策略"
        ])
        strategy_layout.addWidget(self.strategy_combo)
        
        layout.addWidget(strategy_group)
        
        # Parameter settings
        params_group = QGroupBox("参数设置")
        params_layout = QFormLayout(params_group)
        
        self.param_controls = {}
        params = {
            "均线周期": (10, 100, 20),
            "MACD快线": (5, 50, 12),
            "MACD慢线": (10, 100, 26),
            "MACD信号线": (2, 20, 9),
            "RSI周期": (5, 30, 14),
            "布林带周期": (10, 100, 20),
            "布林带标准差": (1, 3, 2),
            "自适应周期": (5, 50, 20),
            "自适应阈值": (0.1, 1.0, 0.5),
            "多因子数量": (3, 20, 5),
            "机器学习模型": ["随机森林", "XGBoost", "LightGBM", "SVM"],
            "深度学习模型": ["LSTM", "GRU", "Transformer", "CNN"],
            "训练集比例": (0.5, 0.9, 0.7),
            "预测周期": (1, 30, 5)
        }
        
        for name, value in params.items():
            if isinstance(value, tuple):
                spinbox = QSpinBox()
                spinbox.setRange(value[0], value[1])
                spinbox.setValue(value[2])
                params_layout.addRow(name + ":", spinbox)
                self.param_controls[name] = spinbox
            else:
                combo = QComboBox()
                combo.addItems(value)
                params_layout.addRow(name + ":", combo)
                self.param_controls[name] = combo
                
        layout.addWidget(params_group)
        
        # Backtest settings
        backtest_group = QGroupBox("回测设置")
        backtest_layout = QFormLayout(backtest_group)
        
        self.initial_capital = QDoubleSpinBox()
        self.initial_capital.setDecimals(2)
        self.initial_capital.setRange(1000.0, 1000000.0)
        self.initial_capital.setValue(100000.0)
        self.initial_capital.setSuffix(" 元")
        backtest_layout.addRow("初始资金:", self.initial_capital)
        
        self.commission_rate = QDoubleSpinBox()
        self.commission_rate.setDecimals(4)
        self.commission_rate.setRange(0.0, 0.01)
        self.commission_rate.setValue(0.0003)
        self.commission_rate.setSuffix(" %")
        backtest_layout.addRow("佣金率:", self.commission_rate)
        
        self.slippage = QDoubleSpinBox()
        self.slippage.setDecimals(4)
        self.slippage.setRange(0.0, 0.01)
        self.slippage.setValue(0.0001)
        self.slippage.setSuffix(" %")
        backtest_layout.addRow("滑点:", self.slippage)
        
        layout.addWidget(backtest_group)
        
        # Risk management
        risk_group = QGroupBox("风险管理")
        risk_layout = QFormLayout(risk_group)
        
        self.stop_loss = QDoubleSpinBox()
        self.stop_loss.setDecimals(3)
        self.stop_loss.setRange(0.0, 0.1)
        self.stop_loss.setValue(0.05)
        self.stop_loss.setSuffix(" %")
        risk_layout.addRow("止损比例:", self.stop_loss)
        
        self.take_profit = QDoubleSpinBox()
        self.take_profit.setDecimals(3)
        self.take_profit.setRange(0.0, 0.2)
        self.take_profit.setValue(0.1)
        self.take_profit.setSuffix(" %")
        risk_layout.addRow("止盈比例:", self.take_profit)
        
        self.max_drawdown = QDoubleSpinBox()
        self.max_drawdown.setDecimals(3)
        self.max_drawdown.setRange(0.0, 0.3)
        self.max_drawdown.setValue(0.15)
        self.max_drawdown.setSuffix(" %")
        risk_layout.addRow("最大回撤:", self.max_drawdown)
        
        layout.addWidget(risk_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        analyze_button = QPushButton("分析")
        analyze_button.clicked.connect(self.analyze)
        buttons_layout.addWidget(analyze_button)
        
        backtest_button = QPushButton("回测")
        backtest_button.clicked.connect(self.backtest)
        buttons_layout.addWidget(backtest_button)
        
        optimize_button = QPushButton("优化")
        optimize_button.clicked.connect(self.optimize)
        buttons_layout.addWidget(optimize_button)
        
        export_button = QPushButton("导出")
        export_button.clicked.connect(self.export_analysis)
        buttons_layout.addWidget(export_button)
        
        layout.addLayout(buttons_layout)
        
        # Performance metrics
        metrics_group = QGroupBox("性能指标")
        metrics_layout = QFormLayout(metrics_group)
        
        self.metric_labels = {
            "年化收益率": QLabel("--"),
            "最大回撤": QLabel("--"),
            "夏普比率": QLabel("--"),
            "胜率": QLabel("--"),
            "盈亏比": QLabel("--"),
            "波动率": QLabel("--"),
            "信息比率": QLabel("--"),
            "索提诺比率": QLabel("--"),
            "卡玛比率": QLabel("--"),
            "Alpha": QLabel("--"),
            "Beta": QLabel("--"),
            "跟踪误差": QLabel("--"),
            "换手率": QLabel("--"),
            "最大连续亏损": QLabel("--"),
            "平均持仓时间": QLabel("--")
        }
        
        for name, label in self.metric_labels.items():
            metrics_layout.addRow(name + ":", label)
            
        layout.addWidget(metrics_group)
        
        self.setLayout(layout)
        
    def analyze(self):
        """Perform analysis"""
        # TODO: Implement analysis logic
        pass
        
    def backtest(self):
        """Run backtest"""
        # TODO: Implement backtest logic
        pass
        
    def optimize(self):
        """Optimize parameters"""
        # TODO: Implement optimization logic
        pass
        
    def export_analysis(self):
        """Export analysis results"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出分析结果",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )
            
            if file_path:
                results = {
                    'strategy': self.strategy_combo.currentText(),
                    'parameters': {name: control.value() for name, control in self.param_controls.items()},
                    'metrics': {name: label.text() for name, label in self.metric_labels.items()}
                }
                
                if file_path.endswith('.xlsx'):
                    df = pd.DataFrame(results)
                    df.to_excel(file_path, index=False)
                else:
                    df = pd.DataFrame(results)
                    df.to_csv(file_path, index=False)
                    
                QMessageBox.information(self, "成功", "分析结果已导出")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

class LogPanel(QWidget):
    """Log panel for displaying system logs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Log controls
        controls_layout = QHBoxLayout()
        
        # Log level filter
        log_level_label = QLabel("日志级别:")
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["全部", "信息", "警告", "错误"])
        self.log_level_combo.currentTextChanged.connect(self.filter_logs)
        controls_layout.addWidget(log_level_label)
        controls_layout.addWidget(self.log_level_combo)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索日志...")
        self.search_box.textChanged.connect(self.search_logs)
        controls_layout.addWidget(self.search_box)
        
        # Clear button
        clear_button = QPushButton("清除")
        clear_button.clicked.connect(self.clear_logs)
        controls_layout.addWidget(clear_button)
        
        # Export button
        export_button = QPushButton("导出")
        export_button.clicked.connect(self.export_logs)
        controls_layout.addWidget(export_button)
        
        layout.addLayout(controls_layout)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
        
    def log_message(self, message, level="info"):
        """Add a log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level.upper()}] {message}"
        self.log_text.append(formatted_message)
        
    def filter_logs(self, level):
        """Filter logs by level"""
        # TODO: Implement log filtering
        pass
        
    def search_logs(self, text):
        """Search logs"""
        # TODO: Implement log searching
        pass
        
    def clear_logs(self):
        """Clear all logs"""
        self.log_text.clear()
        
    def export_logs(self):
        """Export logs to file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志",
                "",
                "Text Files (*.txt);;Log Files (*.log)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                    
                QMessageBox.information(self, "成功", "日志已导出")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

class StatusBar(QStatusBar):
    """Custom status bar with system information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        # Status message
        self.status_label = QLabel("就绪")
        self.addWidget(self.status_label)
        
        # CPU usage
        self.cpu_label = QLabel("CPU: 0%")
        self.addPermanentWidget(self.cpu_label)
        
        # Memory usage
        self.memory_label = QLabel("内存: 0%")
        self.addPermanentWidget(self.memory_label)
        
        # Time
        self.time_label = QLabel("时间: 00:00:00")
        self.addPermanentWidget(self.time_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.addPermanentWidget(self.progress_bar)
        
        # Start update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)  # Update every second
        
    def update_status(self):
        """Update status information"""
        # Update CPU usage
        cpu_percent = psutil.cpu_percent()
        self.cpu_label.setText(f"CPU: {cpu_percent}%")
        
        # Update memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        self.memory_label.setText(f"内存: {memory_percent}%")
        
        # Update time
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(f"时间: {current_time}")
        
    def show_progress(self, visible=True):
        """Show or hide progress bar"""
        self.progress_bar.setVisible(visible)
        
    def set_progress(self, value):
        """Set progress bar value"""
        self.progress_bar.setValue(value)
        
    def set_status(self, message):
        """Set status message"""
        self.status_label.setText(message)

class MainToolBar(QToolBar):
    """Main toolbar with common actions"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        self.setMovable(False)
        
        # File actions
        self.addAction("打开", self.open_file)
        self.addAction("保存", self.save_file)
        self.addSeparator()
        
        # Edit actions
        self.addAction("复制", self.copy_data)
        self.addAction("粘贴", self.paste_data)
        self.addSeparator()
        
        # Analysis actions
        self.addAction("分析", self.analyze)
        self.addAction("回测", self.backtest)
        self.addAction("优化", self.optimize)
        self.addSeparator()
        
        # View actions
        self.addAction("重置视图", self.reset_view)
        self.addAction("保存图表", self.save_chart)
        self.addSeparator()
        
        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色", "深色", "系统"])
        self.addWidget(self.theme_combo)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索...")
        self.search_box.setMaximumWidth(200)
        self.addWidget(self.search_box)
        
    def open_file(self):
        """Open file"""
        # TODO: Implement file opening
        pass
        
    def save_file(self):
        """Save file"""
        # TODO: Implement file saving
        pass
        
    def copy_data(self):
        """Copy data"""
        # TODO: Implement data copying
        pass
        
    def paste_data(self):
        """Paste data"""
        # TODO: Implement data pasting
        pass
        
    def analyze(self):
        """Perform analysis"""
        # TODO: Implement analysis
        pass
        
    def backtest(self):
        """Run backtest"""
        # TODO: Implement backtest
        pass
        
    def optimize(self):
        """Optimize parameters"""
        # TODO: Implement optimization
        pass
        
    def reset_view(self):
        """Reset view"""
        # TODO: Implement view reset
        pass
        
    def save_chart(self):
        """Save chart"""
        # TODO: Implement chart saving
        pass 