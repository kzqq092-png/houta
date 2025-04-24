from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

class MainToolBar(QToolBar):
    """主工具栏"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """初始化工具栏UI"""
        # 设置工具栏属性
        self.setMovable(True)
        self.setFloatable(True)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        # 创建分析动作
        self.analyze_action = QAction(QIcon("icons/analyze.png"), "分析", self)
        self.analyze_action.setStatusTip("分析选股结果")
        self.addAction(self.analyze_action)
        
        # 创建回测动作
        self.backtest_action = QAction(QIcon("icons/backtest.png"), "回测", self)
        self.backtest_action.setStatusTip("回测选股策略")
        self.addAction(self.backtest_action)
        
        # 创建优化动作
        self.optimize_action = QAction(QIcon("icons/optimize.png"), "优化", self)
        self.optimize_action.setStatusTip("优化选股策略")
        self.addAction(self.optimize_action)
        
        # 添加分隔符
        self.addSeparator()
        
        # 创建缩放动作
        self.zoom_in_action = QAction(QIcon("icons/zoom_in.png"), "放大", self)
        self.zoom_in_action.setStatusTip("放大图表")
        self.addAction(self.zoom_in_action)
        
        self.zoom_out_action = QAction(QIcon("icons/zoom_out.png"), "缩小", self)
        self.zoom_out_action.setStatusTip("缩小图表")
        self.addAction(self.zoom_out_action)
        
        self.reset_zoom_action = QAction(QIcon("icons/reset_zoom.png"), "重置", self)
        self.reset_zoom_action.setStatusTip("重置图表缩放")
        self.addAction(self.reset_zoom_action)
        
        # 添加分隔符
        self.addSeparator()
        
        # 创建设置动作
        self.settings_action = QAction(QIcon("icons/settings.png"), "设置", self)
        self.settings_action.setStatusTip("打开设置对话框")
        self.addAction(self.settings_action)
        
        # 创建计算器动作
        self.calculator_action = QAction(QIcon("icons/calculator.png"), "计算器", self)
        self.calculator_action.setStatusTip("打开计算器")
        self.addAction(self.calculator_action)
        
        # 创建转换器动作
        self.converter_action = QAction(QIcon("icons/converter.png"), "转换器", self)
        self.converter_action.setStatusTip("打开单位转换器")
        self.addAction(self.converter_action) 