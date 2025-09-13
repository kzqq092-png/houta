#!/usr/bin/env python3
"""
测试深度分析UI功能
验证修复后的深度分析tab是否能正常显示数据
"""

import sys
import time
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from loguru import logger

# 导入深度分析相关组件
from gui.widgets.performance.tabs.deep_analysis_tab import ModernDeepAnalysisTab
from core.services.deep_analysis_service import get_deep_analysis_service
from core.services.performance_data_bridge import get_performance_bridge, initialize_performance_bridge


class DeepAnalysisTestWindow(QMainWindow):
    """深度分析测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("深度分析功能测试")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 添加控制按钮
        self.create_control_panel(layout)
        
        # 创建深度分析tab
        self.deep_analysis_tab = ModernDeepAnalysisTab()
        layout.addWidget(self.deep_analysis_tab)
        
        # 初始化数据收集
        self.initialize_data_collection()
        
        logger.info("深度分析测试窗口初始化完成")
    
    def create_control_panel(self, layout):
        """创建控制面板"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # 状态显示
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        control_layout.addWidget(self.status_text)
        
        # 控制按钮
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)
        
        # 刷新数据按钮
        refresh_btn = QPushButton("刷新性能数据")
        refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(refresh_btn)
        
        # 注入测试数据按钮
        inject_btn = QPushButton("注入测试数据")
        inject_btn.clicked.connect(self.inject_test_data)
        button_layout.addWidget(inject_btn)
        
        # 显示状态按钮
        status_btn = QPushButton("显示系统状态")
        status_btn.clicked.connect(self.show_status)
        button_layout.addWidget(status_btn)
        
        control_layout.addWidget(button_widget)
        layout.addWidget(control_widget)
        
        # 定时器更新状态
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)  # 每5秒更新一次
    
    def initialize_data_collection(self):
        """初始化数据收集"""
        try:
            # 确保性能数据桥接器已启动
            self.bridge = get_performance_bridge()
            if not hasattr(self.bridge, '_running') or not self.bridge._running:
                self.bridge = initialize_performance_bridge(auto_start=True)
            
            # 获取深度分析服务
            self.analysis_service = get_deep_analysis_service()
            
            self.log_status("✅ 数据收集组件初始化完成")
            
        except Exception as e:
            self.log_status(f"❌ 数据收集初始化失败: {e}")
    
    def refresh_data(self):
        """刷新性能数据"""
        try:
            # 手动触发数据收集
            if hasattr(self.bridge, '_collect_system_metrics'):
                self.bridge._collect_system_metrics()
                self.bridge._collect_application_metrics()
            
            # 显示当前数据状态
            metrics_count = len(self.analysis_service.metrics_history)
            operations_count = sum(len(timings) for timings in self.analysis_service.operation_timings.values())
            
            self.log_status(f"🔄 数据已刷新: 指标 {metrics_count} 条, 操作 {operations_count} 条")
            
        except Exception as e:
            self.log_status(f"❌ 数据刷新失败: {e}")
    
    def inject_test_data(self):
        """注入测试数据"""
        try:
            self.bridge.inject_sample_data(100)
            
            # 显示注入后的数据状态
            metrics_count = len(self.analysis_service.metrics_history)
            operations_count = sum(len(timings) for timings in self.analysis_service.operation_timings.values())
            
            self.log_status(f"💉 测试数据已注入: 指标 {metrics_count} 条, 操作 {operations_count} 条")
            
        except Exception as e:
            self.log_status(f"❌ 测试数据注入失败: {e}")
    
    def show_status(self):
        """显示系统状态"""
        try:
            # 获取桥接器状态
            bridge_status = self.bridge.get_status()
            
            # 获取分析结果
            bottlenecks = self.analysis_service.analyze_bottlenecks()
            ranking = self.analysis_service.get_operation_ranking()
            anomalies = self.analysis_service.detect_anomalies(hours=1)
            
            status_text = f"""
📊 系统状态报告 ({time.strftime('%H:%M:%S')})

🔗 性能数据桥接器:
   - 运行状态: {'✅ 运行中' if bridge_status['running'] else '❌ 已停止'}
   - 指标数量: {bridge_status['metrics_count']}
   - 操作数量: {bridge_status['operations_count']}
   - 收集间隔: {bridge_status['collection_interval']}秒

📈 深度分析结果:
   - 性能瓶颈: {len(bottlenecks)} 个
   - 操作排行: {len(ranking)} 个
   - 异常检测: {len(anomalies)} 个

💡 UI分析工具状态:
   - 瓶颈分析: {'✅ 有数据' if bottlenecks else '⚠️ 无数据'}
   - 操作排行: {'✅ 有数据' if ranking else '⚠️ 无数据'}
   - 异常检测: {'✅ 有数据' if anomalies else '⚠️ 无数据'}
"""
            
            self.log_status(status_text)
            
        except Exception as e:
            self.log_status(f"❌ 获取状态失败: {e}")
    
    def update_status(self):
        """定时更新状态"""
        try:
            metrics_count = len(self.analysis_service.metrics_history)
            operations_count = sum(len(timings) for timings in self.analysis_service.operation_timings.values())
            
            self.setWindowTitle(f"深度分析功能测试 - 指标:{metrics_count} 操作:{operations_count}")
            
        except Exception as e:
            logger.error(f"状态更新失败: {e}")
    
    def log_status(self, message):
        """记录状态信息"""
        timestamp = time.strftime('%H:%M:%S')
        self.status_text.append(f"[{timestamp}] {message}")
        logger.info(message)


def main():
    """主函数"""
    print("🚀 启动深度分析UI测试...")
    
    app = QApplication(sys.argv)
    
    # 初始化Loguru
    from core.loguru_config import initialize_loguru
    initialize_loguru()
    
    # 创建测试窗口
    window = DeepAnalysisTestWindow()
    window.show()
    
    logger.info("深度分析UI测试应用启动完成")
    
    # 显示使用说明
    print("""
📋 测试说明:
1. 点击"注入测试数据"按钮添加模拟性能数据
2. 点击深度分析tab中的各个分析工具按钮
3. 观察是否能正常显示分析结果
4. 点击"显示系统状态"查看数据收集状态

🎯 预期结果:
- 所有分析工具应该能显示数据而不是"暂无数据"
- 图表标签页应该能显示性能图表
- 数据标签页应该能显示操作排行
- 报告标签页应该能显示分析报告
""")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()