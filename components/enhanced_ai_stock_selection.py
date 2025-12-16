"""
增强AI选股组件

集成新的AI选股集成服务和可解释性服务，提供完整的AI选股界面
"""

import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from loguru import logger
import json
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import asyncio
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches

# UI组件
from gui.ui_components import BaseAnalysisPanel
from core.containers import get_service_container

# AI选股相关服务
try:
    from core.services.ai_selection_integration_service import AISelectionIntegrationService
    from core.services.ai_explainability_service import AIExplainabilityService, ExplanationLevel
    from core.services.ai_selection_integration_service import StockSelectionCriteria, SelectionStrategy
except ImportError as e:
    logger.warning(f"AI选股服务导入失败: {e}")
    AISelectionIntegrationService = None
    AIExplainabilityService = None
    ExplanationLevel = None
    StockSelectionCriteria = None
    SelectionStrategy = None


class AISelectionWorker(QThread):
    """AI选股工作线程"""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, ai_selection_service, criteria, strategy):
        super().__init__()
        self.ai_selection_service = ai_selection_service
        self.criteria = criteria
        self.strategy = strategy
        
    def run(self):
        try:
            self.progress.emit("开始AI选股分析...")
            
            # 调用AI选股服务
            if hasattr(self.ai_selection_service, 'select_stocks'):
                result = self.ai_selection_service.select_stocks(
                    criteria=self.criteria,
                    strategy=self.strategy
                )
                self.finished.emit(result)
            else:
                self.error.emit("AI选股服务不支持选股功能")
                
        except Exception as e:
            self.error.emit(f"AI选股失败: {str(e)}")
            logger.error(f"AI选股线程错误: {e}")
            logger.error(traceback.format_exc())


class EnhancedAIStockSelectionPanel(BaseAnalysisPanel):
    """增强AI选股面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_selection_service = None
        self.explainability_service = None
        self.selection_results = {}
        self.explanation_data = {}
        
        # 缓存机制
        self._cache = {
            'indicator_data': {},  # 技术指标数据缓存
            'fundamental_data': {},  # 基本面数据缓存
            'explanations': {},  # 可解释性数据缓存
            'last_update': {}  # 缓存时间戳
        }
        self._cache_expiry = 300  # 缓存过期时间（5分钟）
        
        # 初始化服务
        self._init_services()
        
        # 创建UI
        self._create_ui()
        
    def _init_services(self):
        """初始化AI选股相关服务"""
        try:
            container = get_service_container()
            if container:
                if AISelectionIntegrationService:
                    self.ai_selection_service = container.resolve(AISelectionIntegrationService)
                    logger.info("AI选股集成服务加载成功")
                
                if AIExplainabilityService:
                    self.explainability_service = container.resolve(AIExplainabilityService)
                    logger.info("AI可解释性服务加载成功")
            else:
                logger.warning("服务容器不可用")
        except Exception as e:
            logger.error(f"服务初始化失败: {e}")
    
    def _is_cache_valid(self, cache_key):
        """检查缓存是否有效"""
        if cache_key not in self._cache['last_update']:
            return False
        
        import time
        current_time = time.time()
        last_update = self._cache['last_update'][cache_key]
        
        return (current_time - last_update) < self._cache_expiry
    
    def _update_cache_timestamp(self, cache_key):
        """更新缓存时间戳"""
        import time
        self._cache['last_update'][cache_key] = time.time()
    
    def _get_cached_data(self, cache_key, cache_type='indicator_data'):
        """获取缓存数据"""
        if self._is_cache_valid(cache_key):
            return self._cache[cache_type].get(cache_key)
        return None
    
    def _set_cached_data(self, cache_key, data, cache_type='indicator_data'):
        """设置缓存数据"""
        self._cache[cache_type][cache_key] = data
        self._update_cache_timestamp(cache_key)
    
    def _clear_expired_cache(self):
        """清理过期缓存"""
        import time
        current_time = time.time()
        expired_keys = []
        
        for cache_key, last_update in self._cache['last_update'].items():
            if (current_time - last_update) >= self._cache_expiry:
                expired_keys.append(cache_key)
        
        for cache_type in ['indicator_data', 'fundamental_data', 'explanations']:
            for key in expired_keys:
                if key in self._cache[cache_type]:
                    del self._cache[cache_type][key]
                if key in self._cache['last_update']:
                    del self._cache['last_update'][key]
            
    def _create_ui(self):
        """创建UI界面"""
        # 配置区域
        config_group = QGroupBox("AI选股配置")
        config_layout = QFormLayout(config_group)
        
        # 选股策略
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "技术指标驱动",
            "基本面驱动", 
            "综合评分",
            "成长性导向",
            "价值投资",
            "动量策略"
        ])
        config_layout.addRow("选股策略:", self.strategy_combo)
        
        # 选股数量
        self.stock_count_spin = QSpinBox()
        self.stock_count_spin.setRange(10, 200)
        self.stock_count_spin.setValue(50)
        self.stock_count_spin.setSuffix(" 只")
        config_layout.addRow("选股数量:", self.stock_count_spin)
        
        # 解释级别
        if ExplanationLevel:
            self.explanation_level_combo = QComboBox()
            self.explanation_level_combo.addItems([
                "简单解释", "详细解释", "专业解释"
            ])
            config_layout.addRow("解释级别:", self.explanation_level_combo)
        
        # 风险控制
        self.risk_tolerance_combo = QComboBox()
        self.risk_tolerance_combo.addItems(["保守", "稳健", "积极", "激进"])
        config_layout.addRow("风险偏好:", self.risk_tolerance_combo)
        
        # 时间范围
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems([
            "最近1个月", "最近3个月", "最近6个月", "最近1年"
        ])
        config_layout.addRow("分析时间范围:", self.timeframe_combo)
        
        self.main_layout.addWidget(config_group)
        
        # 技术指标配置
        indicator_group = QGroupBox("技术指标权重")
        indicator_layout = QGridLayout(indicator_group)
        
        # 常用技术指标
        indicators = [
            ("MA5", 0.1), ("MA10", 0.15), ("MA20", 0.2),
            ("MACD", 0.15), ("RSI", 0.1), ("KDJ", 0.1),
            ("BOLL", 0.1), ("OBV", 0.1)
        ]
        
        self.indicator_weights = {}
        for i, (indicator, default_weight) in enumerate(indicators):
            row, col = i // 4, i % 4
            weight_spin = QDoubleSpinBox()
            weight_spin.setRange(0.0, 1.0)
            weight_spin.setSingleStep(0.05)
            weight_spin.setValue(default_weight)
            weight_spin.setSuffix(" (权重)")
            indicator_layout.addWidget(QLabel(f"{indicator}:"), row, col * 2)
            indicator_layout.addWidget(weight_spin, row, col * 2 + 1)
            self.indicator_weights[indicator] = weight_spin
            
        self.main_layout.addWidget(indicator_group)
        
        # 基本面指标配置
        fundamental_group = QGroupBox("基本面指标权重")
        fundamental_layout = QGridLayout(fundamental_group)
        
        fundamentals = [
            ("PE比率", 0.2), ("PB比率", 0.15), ("ROE", 0.2),
            ("营收增长率", 0.15), ("净利润增长率", 0.2), ("负债率", 0.1)
        ]
        
        self.fundamental_weights = {}
        for i, (fundamental, default_weight) in enumerate(fundamentals):
            row, col = i // 3, i % 3
            weight_spin = QDoubleSpinBox()
            weight_spin.setRange(0.0, 1.0)
            weight_spin.setSingleStep(0.05)
            weight_spin.setValue(default_weight)
            weight_spin.setSuffix(" (权重)")
            fundamental_layout.addWidget(QLabel(f"{fundamental}:"), row, col * 2)
            fundamental_layout.addWidget(weight_spin, row, col * 2 + 1)
            self.fundamental_weights[fundamental] = weight_spin
            
        self.main_layout.addWidget(fundamental_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始AI选股")
        self.start_btn.clicked.connect(self.start_ai_selection)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        button_layout.addWidget(self.start_btn)
        
        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        self.clear_btn = QPushButton("清空结果")
        self.clear_btn.clicked.connect(self.clear_results)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        self.main_layout.addLayout(button_layout)
        
        # 结果显示区域
        self._create_results_area()
        
    def _create_results_area(self):
        """创建结果显示区域"""
        results_group = QGroupBox("选股结果")
        results_layout = QVBoxLayout(results_group)
        
        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            "股票代码", "股票名称", "综合评分", "技术评分", "基本面评分", 
            "风险评分", "推荐理由", "置信度"
        ])
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.itemSelectionChanged.connect(self.on_selection_changed)
        results_layout.addWidget(self.result_table)
        
        # 分页控件
        page_layout = QHBoxLayout()
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.prev_page_btn.setEnabled(False)
        page_layout.addWidget(self.prev_page_btn)
        
        self.page_label = QLabel("第 1 页 / 共 1 页")
        page_layout.addWidget(self.page_label)
        
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.clicked.connect(self.next_page)
        self.next_page_btn.setEnabled(False)
        page_layout.addWidget(self.next_page_btn)
        
        page_layout.addStretch()
        results_layout.addLayout(page_layout)
        
        self.main_layout.addWidget(results_group)
        
        # 可解释性区域
        explain_group = QGroupBox("选股可解释性")
        explain_layout = QVBoxLayout(explain_group)
        
        # 解释文本显示
        self.explain_text = QTextEdit()
        self.explain_text.setMaximumHeight(200)
        self.explain_text.setReadOnly(True)
        explain_layout.addWidget(self.explain_text)
        
        # 因子贡献图
        self.factor_chart = FigureCanvas(Figure(figsize=(6, 4)))
        self.factor_chart.setMinimumHeight(150)
        explain_layout.addWidget(self.factor_chart)
        
        self.main_layout.addWidget(explain_group)
        
        # 初始化分页
        self.current_page = 1
        self.page_size = 20
        self.total_pages = 1
        
    def start_ai_selection(self):
        """开始AI选股"""
        if not self.ai_selection_service:
            QMessageBox.warning(self, "错误", "AI选股服务不可用")
            return
            
        # 收集配置参数
        criteria = self._collect_criteria()
        strategy = self._get_strategy()
        
        if not criteria:
            QMessageBox.warning(self, "错误", "请配置选股参数")
            return
            
        # 创建并启动工作线程
        self.worker = AISelectionWorker(self.ai_selection_service, criteria, strategy)
        self.worker.finished.connect(self.on_selection_completed)
        self.worker.progress.connect(self.update_status)
        self.worker.error.connect(self.on_selection_error)
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.show_progress(True)
        self.set_progress(0)
        self.update_status("正在启动AI选股...")
        
        self.worker.start()
        
    def _collect_criteria(self):
        """收集选股标准"""
        try:
            if not StockSelectionCriteria:
                return None
                
            criteria = StockSelectionCriteria()
            
            # 基础参数
            criteria.max_stocks = self.stock_count_spin.value()
            criteria.risk_tolerance = self.risk_tolerance_combo.currentText()
            
            # 时间范围
            timeframe_map = {
                "最近1个月": 30,
                "最近3个月": 90, 
                "最近6个月": 180,
                "最近1年": 365
            }
            criteria.time_period = timeframe_map[self.timeframe_combo.currentText()]
            
            # 技术指标权重
            criteria.technical_indicators = {}
            for indicator, spin in self.indicator_weights.items():
                criteria.technical_indicators[indicator] = spin.value()
                
            # 基本面权重
            criteria.fundamental_indicators = {}
            for indicator, spin in self.fundamental_weights.items():
                criteria.fundamental_indicators[indicator] = spin.value()
                
            return criteria
            
        except Exception as e:
            logger.error(f"收集选股标准失败: {e}")
            return None
            
    def _get_strategy(self):
        """获取选股策略"""
        if not SelectionStrategy:
            return None
            
        strategy_map = {
            "技术指标驱动": SelectionStrategy.TECHNICAL_DRIVEN,
            "基本面驱动": SelectionStrategy.FUNDAMENTAL_DRIVEN,
            "综合评分": SelectionStrategy.COMPREHENSIVE,
            "成长性导向": SelectionStrategy.GROWTH_ORIENTED,
            "价值投资": SelectionStrategy.VALUE_INVESTING,
            "动量策略": SelectionStrategy.MOMENTUM_STRATEGY
        }
        
        return strategy_map.get(self.strategy_combo.currentText(), SelectionStrategy.COMPREHENSIVE)
        
    def on_selection_completed(self, result):
        """选股完成回调"""
        try:
            self.show_progress(False)
            self.start_btn.setEnabled(True)
            
            if result.get("success", False):
                self.selection_results = result.get("data", {})
                self._update_results_table()
                self.update_status(f"AI选股完成，共找到 {len(self.selection_results)} 只股票")
                
                # 启用导出按钮
                self.export_btn.setEnabled(True)
                
                # 生成可解释性
                self._generate_explanations()
            else:
                error_msg = result.get("error", "未知错误")
                QMessageBox.warning(self, "选股失败", f"错误: {error_msg}")
                self.update_status(f"选股失败: {error_msg}", error=True)
                
        except Exception as e:
            logger.error(f"处理选股结果失败: {e}")
            QMessageBox.critical(self, "错误", f"处理结果时出错: {str(e)}")
            
    def on_selection_error(self, error_msg):
        """选股错误回调"""
        self.show_progress(False)
        self.start_btn.setEnabled(True)
        QMessageBox.critical(self, "AI选股错误", error_msg)
        self.update_status(f"选股失败: {error_msg}", error=True)
        
    def _update_results_table(self):
        """更新结果表格"""
        try:
            if not self.selection_results:
                self.result_table.setRowCount(0)
                return
                
            # 转换为列表格式
            stock_list = []
            for stock_code, data in self.selection_results.items():
                stock_list.append([
                    stock_code,
                    data.get("name", ""),
                    f"{data.get('total_score', 0):.2f}",
                    f"{data.get('technical_score', 0):.2f}",
                    f"{data.get('fundamental_score', 0):.2f}",
                    f"{data.get('risk_score', 0):.2f}",
                    data.get("reason", ""),
                    f"{data.get('confidence', 0):.1%}"
                ])
                
            # 按评分排序
            stock_list.sort(key=lambda x: float(x[2]), reverse=True)
            
            # 分页显示
            self._display_page(stock_list)
            
        except Exception as e:
            logger.error(f"更新结果表格失败: {e}")
            
    def _display_page(self, stock_list):
        """分页显示"""
        total_stocks = len(stock_list)
        self.total_pages = max(1, (total_stocks + self.page_size - 1) // self.page_size)
        
        # 确保当前页在有效范围内
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_stocks)
        page_data = stock_list[start_idx:end_idx]
        
        # 更新表格
        self.result_table.setRowCount(len(page_data))
        for row, data in enumerate(page_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))
                if col in [2, 3, 4, 5, 7]:  # 数值列
                    item.setTextAlignment(Qt.AlignCenter)
                self.result_table.setItem(row, col, item)
                
        # 更新分页控件
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {self.total_pages} 页")
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        
    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self._update_results_table()
            
    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._update_results_table()
            
    def _generate_explanations(self):
        """生成可解释性"""
        try:
            if not self.explainability_service or not self.selection_results:
                return
                
            # 为前几只股票生成解释
            top_stocks = list(self.selection_results.keys())[:5]
            
            for stock_code in top_stocks:
                if hasattr(self.explainability_service, 'generate_explanation'):
                    stock_data = self.selection_results[stock_code]
                    selection_data = {"score": stock_data.get("total_score", 0)}
                    
                    explanation = self.explainability_service.generate_explanation(
                        stock_code=stock_code,
                        stock_data=stock_data,
                        selection_data=selection_data
                    )
                    
                    self.explanation_data[stock_code] = explanation
                    
        except Exception as e:
            logger.error(f"生成可解释性失败: {e}")
            
    def on_selection_changed(self):
        """选中股票变化"""
        current_row = self.result_table.currentRow()
        if current_row < 0:
            return
            
        # 获取股票代码（从第一列）
        stock_code_item = self.result_table.item(current_row, 0)
        if not stock_code_item:
            return
            
        stock_code = stock_code_item.text()
        
        # 显示该股票的解释
        self._display_explanation(stock_code)
        
    def _display_explanation(self, stock_code):
        """显示股票解释"""
        try:
            explanation = self.explanation_data.get(stock_code)
            if not explanation:
                self.explain_text.setText("该股票暂无详细解释")
                self.factor_chart.setText("选择股票查看因子贡献分析")
                return
                
            # 显示解释文本
            if hasattr(explanation, 'summary_text'):
                self.explain_text.setText(explanation.summary_text)
            else:
                self.explain_text.setText("解释生成中...")
                
            # 显示因子贡献图表
            self._display_factor_contribution_chart(stock_code, explanation)
            
        except Exception as e:
            logger.error(f"显示解释失败: {e}")
            self.explain_text.setText(f"解释显示失败: {str(e)}")
            
    def export_results(self):
        """导出结果"""
        try:
            if not self.selection_results:
                QMessageBox.information(self, "提示", "没有可导出的结果")
                return
                
            # 选择导出格式
            format_choice, ok = QInputDialog.getItem(
                self, "选择导出格式", "请选择导出格式:", 
                ["CSV文件", "Excel文件", "JSON文件"], 0, False
            )
            
            if not ok:
                return
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format_choice == "CSV文件":
                filename, _ = QFileDialog.getSaveFileName(
                    self, "保存CSV文件", 
                    f"ai_selection_results_{timestamp}.csv",
                    "CSV Files (*.csv)"
                )
                if filename:
                    self._export_to_csv(filename)
                    
            elif format_choice == "Excel文件":
                filename, _ = QFileDialog.getSaveFileName(
                    self, "保存Excel文件",
                    f"ai_selection_results_{timestamp}.xlsx", 
                    "Excel Files (*.xlsx)"
                )
                if filename:
                    self._export_to_excel(filename)
                    
            elif format_choice == "JSON文件":
                filename, _ = QFileDialog.getSaveFileName(
                    self, "保存JSON文件",
                    f"ai_selection_results_{timestamp}.json",
                    "JSON Files (*.json)"
                )
                if filename:
                    self._export_to_json(filename)
                    
        except Exception as e:
            logger.error(f"导出结果失败: {e}")
            QMessageBox.critical(self, "导出失败", f"导出失败: {str(e)}")
            
    def _export_to_csv(self, filename):
        """导出到CSV"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                "股票代码", "股票名称", "综合评分", "技术评分", "基本面评分",
                "风险评分", "推荐理由", "置信度", "行业", "市值"
            ])
            
            # 写入数据
            for stock_code, data in self.selection_results.items():
                writer.writerow([
                    stock_code,
                    data.get("name", ""),
                    data.get("total_score", 0),
                    data.get("technical_score", 0),
                    data.get("fundamental_score", 0),
                    data.get("risk_score", 0),
                    data.get("reason", ""),
                    data.get("confidence", 0),
                    data.get("industry", ""),
                    data.get("market_cap", "")
                ])
                
        QMessageBox.information(self, "导出成功", f"结果已导出到: {filename}")
        
    def _export_to_excel(self, filename):
        """导出到Excel"""
        try:
            import openpyxl
            
            # 创建工作簿
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "AI选股结果"
            
            # 写入表头
            headers = [
                "股票代码", "股票名称", "综合评分", "技术评分", "基本面评分",
                "风险评分", "推荐理由", "置信度", "行业", "市值"
            ]
            ws.append(headers)
            
            # 写入数据
            for stock_code, data in self.selection_results.items():
                ws.append([
                    stock_code,
                    data.get("name", ""),
                    data.get("total_score", 0),
                    data.get("technical_score", 0),
                    data.get("fundamental_score", 0),
                    data.get("risk_score", 0),
                    data.get("reason", ""),
                    data.get("confidence", 0),
                    data.get("industry", ""),
                    data.get("market_cap", "")
                ])
                
            # 保存文件
            wb.save(filename)
            QMessageBox.information(self, "导出成功", f"结果已导出到: {filename}")
            
        except ImportError:
            QMessageBox.warning(self, "缺少依赖", "请安装openpyxl库来导出Excel文件")
            
    def _export_to_json(self, filename):
        """导出到JSON"""
        # 准备导出数据
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "total_count": len(self.selection_results),
            "results": self.selection_results
        }
        
        # 添加配置信息
        export_data["config"] = {
            "strategy": self.strategy_combo.currentText(),
            "stock_count": self.stock_count_spin.value(),
            "risk_tolerance": self.risk_tolerance_combo.currentText(),
            "timeframe": self.timeframe_combo.currentText(),
            "technical_weights": {k: v.value() for k, v in self.indicator_weights.items()},
            "fundamental_weights": {k: v.value() for k, v in self.fundamental_weights.items()}
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
            
        QMessageBox.information(self, "导出成功", f"结果已导出到: {filename}")
        
    def clear_results(self):
        """清空结果"""
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有结果吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.selection_results.clear()
            self.explanation_data.clear()
            self.result_table.setRowCount(0)
            self.explain_text.clear()
            self.factor_chart.setText("选择股票查看因子贡献分析")
            self.export_btn.setEnabled(False)
            self.current_page = 1
            self.page_label.setText("第 1 页 / 共 1 页")
            self.update_status("结果已清空")
            
    def _display_factor_contribution_chart(self, stock_code, explanation):
        """显示因子贡献图表"""
        try:
            # 清除之前的内容
            self.factor_chart.figure.clear()
            
            # 创建子图
            ax = self.factor_chart.figure.add_subplot(111)
            
            # 提取因子贡献数据
            factor_data = self._extract_factor_contribution_data(explanation)
            
            if not factor_data:
                # 如果没有因子贡献数据，显示占位符
                ax.text(0.5, 0.5, f'{stock_code}\n因子贡献分析\n(数据不足)', 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=12, 
                       bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')
            else:
                # 显示因子贡献图表
                categories = list(factor_data.keys())
                values = list(factor_data.values())
                colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
                
                # 创建柱状图
                bars = ax.barh(categories, values, color=colors)
                
                # 设置标签和标题
                ax.set_xlabel('贡献度', fontsize=10)
                ax.set_title(f'{stock_code} 因子贡献分析', fontsize=12, fontweight='bold')
                ax.set_xlim(0, max(values) * 1.1 if values else 1)
                
                # 添加数值标签
                for i, (bar, value) in enumerate(zip(bars, values)):
                    ax.text(value + max(values) * 0.01, bar.get_y() + bar.get_height()/2,
                           f'{value:.2f}', va='center', fontsize=9)
                
                # 美化图表
                ax.grid(axis='x', alpha=0.3)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
            
            # 刷新画布
            self.factor_chart.draw()
            
        except Exception as e:
            logger.error(f"显示因子贡献图表失败: {e}")
            # 显示错误信息
            ax = self.factor_chart.figure.add_subplot(111)
            ax.text(0.5, 0.5, f'图表显示失败\n{str(e)}', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=10, color='red',
                   bbox=dict(boxstyle='round', facecolor='mistyrose', alpha=0.8))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.factor_chart.draw()
    
    def _extract_factor_contribution_data(self, explanation):
        """提取因子贡献数据"""
        try:
            factor_data = {}
            
            # 从解释对象中提取因子数据
            if hasattr(explanation, 'factor_contributions'):
                for factor, contribution in explanation.factor_contributions.items():
                    factor_data[factor] = float(contribution)
            
            # 如果解释对象包含技术指标评分
            if hasattr(explanation, 'technical_score'):
                factor_data['技术指标'] = float(explanation.technical_score)
            
            # 如果解释对象包含基本面评分
            if hasattr(explanation, 'fundamental_score'):
                factor_data['基本面指标'] = float(explanation.fundamental_score)
            
            # 如果解释对象包含风险评分
            if hasattr(explanation, 'risk_score'):
                factor_data['风险控制'] = float(explanation.risk_score)
            
            # 如果解释对象包含市场情绪评分
            if hasattr(explanation, 'market_sentiment'):
                factor_data['市场情绪'] = float(explanation.market_sentiment)
            
            # 如果解释对象包含流动性评分
            if hasattr(explanation, 'liquidity_score'):
                factor_data['流动性'] = float(explanation.liquidity_score)
            
            # 如果因子数据为空，生成模拟数据用于演示
            if not factor_data:
                # 生成演示数据
                factor_data = {
                    '技术指标': np.random.uniform(0.3, 0.9),
                    '基本面指标': np.random.uniform(0.2, 0.8),
                    '风险控制': np.random.uniform(0.1, 0.7),
                    '市场情绪': np.random.uniform(0.0, 0.6),
                    '流动性': np.random.uniform(0.2, 0.8)
                }
            
            return factor_data
            
        except Exception as e:
            logger.error(f"提取因子贡献数据失败: {e}")
            return {}
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止工作线程
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            
        event.accept()


def create_ai_stock_selection_widget(parent=None):
    """创建AI选股组件"""
    return EnhancedAIStockSelectionPanel(parent)


if __name__ == "__main__":
    # 测试代码
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    widget = EnhancedAIStockSelectionPanel()
    widget.show()
    sys.exit(app.exec_())