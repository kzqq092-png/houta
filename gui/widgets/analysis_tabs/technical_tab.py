"""
技术分析标签页 - 增强版
"""
import time
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QColor, QKeySequence, QFont
from .base_tab import BaseAnalysisTab
from indicators_algo import (
    get_talib_indicator_list, get_all_indicators_by_category,
    calc_ma, calc_macd, calc_rsi, calc_kdj, calc_boll, calc_atr, calc_obv, calc_cci,
    get_talib_chinese_name, get_indicator_english_name, get_indicator_params_config,
    get_indicator_default_params, get_indicator_inputs, get_talib_category
)
from core.logger import LogLevel
from datetime import datetime
import json


class TechnicalAnalysisTab(BaseAnalysisTab):
    """技术分析标签页 - 增强版"""

    # 新增信号
    indicator_calculated = pyqtSignal(str, dict)  # 指标计算完成信号

    def __init__(self, config_manager=None):
        """初始化技术分析标签页"""
        # 指标缓存
        self.indicator_cache = {}
        self.indicator_results = {}

        # 批量计算配置
        self.batch_indicators = []
        self.auto_calculate = True

        super().__init__(config_manager)

    def create_ui(self):
        """创建用户界面 - 增强版"""
        layout = QVBoxLayout(self)

        # 指标选择和控制区域 - 调整高度和布局
        control_group = QGroupBox("指标控制")
        control_group.setMaximumHeight(220)  # 限制最大高度
        control_layout = QHBoxLayout(control_group)

        # 左侧：指标选择 - 更紧凑的布局
        indicator_card = QFrame()
        indicator_card.setFrameStyle(QFrame.StyledPanel)
        indicator_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 8px; }")
        indicator_layout = QVBoxLayout(indicator_card)
        indicator_layout.setSpacing(2)  # 减少间距
        indicator_layout.setContentsMargins(8, 8, 8, 8)  # 减少边距

        # 指标分类选择 - 紧凑布局
        category_layout = QHBoxLayout()
        category_layout.setSpacing(4)
        category_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        self.category_combo.setMaximumHeight(28)  # 限制高度
        category_indicators = get_all_indicators_by_category(use_chinese=True)
        categories = ["全部"] + list(category_indicators.keys())
        self.category_combo.addItems(categories)
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        category_layout.addWidget(self.category_combo)
        indicator_layout.addLayout(category_layout)

        # 指标选择组合框 - 显示所有ta-lib指标
        self.indicator_combo = QComboBox()
        self.indicator_combo.setMaximumHeight(28)  # 限制高度
        self.indicator_combo.setEditable(True)  # 允许搜索
        self.indicator_combo.setInsertPolicy(QComboBox.NoInsert)
        self.populate_indicators("全部")  # 初始显示所有指标
        self.indicator_combo.currentTextChanged.connect(self.on_indicator_changed)
        self.indicator_combo.setToolTip("选择要计算的技术指标，支持搜索")
        indicator_layout.addWidget(self.indicator_combo)

        # 批量选择 - 水平紧凑布局
        batch_layout = QHBoxLayout()
        batch_layout.setSpacing(8)
        self.batch_checkbox = QCheckBox("批量计算")
        self.batch_checkbox.setToolTip("选择多个指标进行批量计算")
        self.batch_checkbox.stateChanged.connect(self.toggle_batch_mode)

        self.auto_calc_checkbox = QCheckBox("自动计算")
        self.auto_calc_checkbox.setChecked(True)
        self.auto_calc_checkbox.setToolTip("数据更新时自动重新计算指标")
        self.auto_calc_checkbox.stateChanged.connect(self.toggle_auto_calculate)

        batch_layout.addWidget(self.batch_checkbox)
        batch_layout.addWidget(self.auto_calc_checkbox)
        batch_layout.addStretch()
        indicator_layout.addLayout(batch_layout)

        # 计算按钮 - 紧凑布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)

        self.calc_btn = QPushButton("计算指标")  # 保存引用
        self.calc_btn.setStyleSheet("QPushButton { background-color: #007bff; color: white; font-weight: bold; padding: 4px 8px; }")
        self.calc_btn.clicked.connect(self.calculate_indicators)
        self.calc_btn.setToolTip("根据当前设置计算选定的技术指标\n快捷键：Ctrl+Enter")

        clear_indicators_btn = QPushButton("清除")
        clear_indicators_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; font-weight: bold; padding: 4px 8px; }")
        clear_indicators_btn.clicked.connect(self.clear_indicators)
        clear_indicators_btn.setToolTip("清除所有已计算的技术指标")

        # 新增：缓存管理按钮
        cache_btn = QPushButton("清缓存")
        cache_btn.setStyleSheet("QPushButton { background-color: #ffc107; color: black; font-weight: bold; padding: 4px 8px; }")
        cache_btn.clicked.connect(self.clear_cache)
        cache_btn.setToolTip("清除指标计算缓存")

        button_layout.addWidget(self.calc_btn)
        button_layout.addWidget(clear_indicators_btn)
        button_layout.addWidget(cache_btn)
        indicator_layout.addLayout(button_layout)

        control_layout.addWidget(indicator_card, stretch=2)

        # 右侧：动态参数设置 - 根据选择的指标动态变化
        params_card = QFrame()
        params_card.setFrameStyle(QFrame.StyledPanel)
        params_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 8px; }")
        self.params_layout = QVBoxLayout(params_card)
        self.params_layout.setSpacing(2)  # 减少间距

        # 参数预设 - 紧凑布局
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(2)
        preset_layout.addWidget(QLabel("预设:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMaximumHeight(28)
        self.preset_combo.addItems(["自定义", "短期交易", "中期投资", "长期投资"])
        self.preset_combo.currentTextChanged.connect(self.apply_preset_params)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        self.params_layout.addLayout(preset_layout)

        # 动态参数区域
        self.dynamic_params_widget = QWidget()
        self.dynamic_params_layout = QVBoxLayout(self.dynamic_params_widget)
        self.dynamic_params_layout.setSpacing(2)  # 减少间距
        self.params_layout.addWidget(self.dynamic_params_widget)

        # 参数控件字典
        self.param_controls = {}

        # 初始化参数界面 - 确保有默认指标
        if self.indicator_combo.count() > 0:
            # 如果没有选中任何指标，选择第一个
            if not self.indicator_combo.currentText():
                self.indicator_combo.setCurrentIndex(0)
            # 手动触发参数界面更新
            current_indicator = self.indicator_combo.currentText()
            if current_indicator:
                self.update_parameter_interface(current_indicator)
        else:
            self.update_parameter_interface()

        control_layout.addWidget(params_card, stretch=3)
        layout.addWidget(control_group)

        # 结果显示区域
        results_group = QGroupBox("计算结果")
        results_layout = QVBoxLayout(results_group)

        # 统计信息 - 紧凑布局
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        self.stats_label = QLabel("统计信息: 无数据")
        self.stats_label.setStyleSheet("QLabel { font-weight: bold; color: #495057; }")
        stats_layout.addWidget(self.stats_label)

        self.performance_label = QLabel("性能: 无统计")
        self.performance_label.setStyleSheet("QLabel { font-weight: bold; color: #6c757d; }")
        stats_layout.addWidget(self.performance_label)
        stats_layout.addStretch()
        results_layout.addLayout(stats_layout)

        # 结果表格
        self.technical_table = QTableWidget(0, 8)  # 增加列数
        self.technical_table.setHorizontalHeaderLabels([
            '日期', '指标', '数值', '信号', '强度', '趋势', '建议', '备注'
        ])
        self.technical_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.technical_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.technical_table.setAlternatingRowColors(True)
        self.technical_table.setSortingEnabled(True)

        # 设置专业的表格样式
        self.technical_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                font-size: 12px;
                height: 15px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QTableWidget::item:selected {
                background-color: #bbdefb;
                color: #1976d2;
            }
            QHeaderView::section {
                background-color: #37474f;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
                height: 15px;
            }
            QHeaderView::section:hover {
                background-color: #455a64;
            }
        """)

        # 设置列宽 - 修复显示问题
        header = self.technical_table.horizontalHeader()
        header.setStretchLastSection(True)

        # 设置行高
        self.technical_table.verticalHeader().setDefaultSectionSize(35)
        self.technical_table.verticalHeader().setVisible(False)  # 隐藏行号

        results_layout.addWidget(self.technical_table)

        # 导出按钮
        export_group = self.create_export_section()
        results_layout.addWidget(export_group)
        layout.addWidget(results_group)

    def populate_indicators(self, category: str):
        """根据分类填充指标列表"""
        self.indicator_combo.clear()

        if category == "全部":
            # 显示所有指标，按分类组织
            category_indicators = get_all_indicators_by_category(use_chinese=True)
            all_indicators = []
            for cat, indicators in category_indicators.items():
                all_indicators.extend(indicators)

            # 添加常用指标到顶部
            common_indicators = [
                "移动平均线", "MACD指标", "相对强弱指标", "随机指标",
                "布林带", "平均真实波幅", "能量潮指标", "商品通道指标"
            ]

            # 先添加常用指标
            for indicator in common_indicators:
                if indicator in all_indicators:
                    self.indicator_combo.addItem(indicator)

            # 添加分隔符
            self.indicator_combo.insertSeparator(len(common_indicators))

            # 添加其他指标
            for indicator in sorted(all_indicators):
                if indicator not in common_indicators:
                    self.indicator_combo.addItem(indicator)
        else:
            # 显示特定分类的指标
            category_indicators = get_all_indicators_by_category(use_chinese=True)
            if category in category_indicators:
                indicators = sorted(category_indicators[category])
                self.indicator_combo.addItems(indicators)

    def on_category_changed(self, category: str):
        """分类改变时更新指标列表"""
        self.populate_indicators(category)
        if self.indicator_combo.count() > 0:
            self.indicator_combo.setCurrentIndex(0)
            # 手动触发指标变化处理，确保参数界面更新
            current_indicator = self.indicator_combo.currentText()
            if current_indicator:
                self.on_indicator_changed(current_indicator)

    def on_indicator_changed(self, indicator_name: str):
        """指标改变时更新参数界面"""
        if not indicator_name:
            return

        # 更新参数界面
        self.update_parameter_interface(indicator_name)

        # 更新工具提示
        english_name = get_indicator_english_name(indicator_name)
        config = get_indicator_params_config(english_name)
        inputs = config.get("inputs", ["close"])

        tooltip = f"指标: {indicator_name}\n"
        tooltip += f"英文名: {english_name}\n"
        tooltip += f"输入数据: {', '.join(inputs)}\n"

        if config.get("params"):
            tooltip += "参数:\n"
            for param_name, param_config in config["params"].items():
                tooltip += f"  {param_name}: {param_config.get('desc', '')}\n"

        self.indicator_combo.setToolTip(tooltip)

        # 发射信号通知父组件
        try:
            if hasattr(self, 'parent_widget') and self.parent_widget:
                self.parent_widget.indicator_changed.emit(indicator_name)
        except Exception as e:
            self.log_manager.error(f"指标变更处理失败: {e}")

    def update_parameter_interface(self, indicator_name: str = None):
        """更新参数设置界面 - 紧凑专业版"""
        # 清除现有参数控件
        for i in reversed(range(self.dynamic_params_layout.count())):
            child = self.dynamic_params_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        self.param_controls.clear()

        if not indicator_name:
            indicator_name = self.indicator_combo.currentText()

        if not indicator_name:
            return

        # 获取指标的英文名称和参数配置
        english_name = get_indicator_english_name(indicator_name)
        config = get_indicator_params_config(english_name)

        # 显示指标信息 - 紧凑版
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(4, 4, 4, 4)

        # 基本信息 - 单行显示
        basic_info = QLabel(f"指标: {indicator_name} ({english_name})")
        basic_info.setStyleSheet("QLabel { color: #495057; font-weight: bold; font-size: 11px; }")
        info_layout.addWidget(basic_info)

        self.dynamic_params_layout.addWidget(info_widget)

        if not config or not config.get("params"):
            # 如果没有参数，显示简单提示
            no_params_label = QLabel("无需参数设置")
            no_params_label.setStyleSheet("QLabel { color: #6c757d; font-style: italic; text-align: center; font-size: 11px; padding: 10px; }")
            self.dynamic_params_layout.addWidget(no_params_label)
            return

        # 创建参数控件 - 紧凑布局
        for param_name, param_config in config["params"].items():
            param_widget = QWidget()
            param_layout = QHBoxLayout(param_widget)
            param_layout.setSpacing(4)
            param_layout.setContentsMargins(4, 2, 4, 2)

            # 参数标签 - 紧凑
            param_label = QLabel(f"{param_config.get('desc', param_name)}:")
            param_label.setMinimumWidth(80)
            param_label.setMaximumWidth(120)
            param_label.setStyleSheet("QLabel { font-size: 11px; color: #212529; }")
            param_layout.addWidget(param_label)

            # 参数控件 - 紧凑
            if param_name in ["matype", "fastmatype", "slowmatype", "signalmatype", "slowk_matype", "slowd_matype", "fastd_matype"]:
                # MA类型选择
                control = QComboBox()
                control.setMaximumHeight(24)
                ma_types = ["SMA", "EMA", "WMA", "DEMA", "TEMA", "TRIMA", "KAMA", "MAMA", "T3"]
                control.addItems(ma_types)
                control.setCurrentIndex(param_config.get("default", 0))
                control.setStyleSheet("QComboBox { font-size: 11px; padding: 2px; }")
            elif isinstance(param_config.get("default"), float):
                # 浮点数参数
                control = QDoubleSpinBox()
                control.setMaximumHeight(24)
                control.setRange(param_config.get("min", 0.0), param_config.get("max", 100.0))
                control.setValue(param_config.get("default", 1.0))
                control.setSingleStep(0.01)
                control.setDecimals(3)
                control.setStyleSheet("QDoubleSpinBox { font-size: 11px; padding: 2px; }")
            else:
                # 整数参数
                control = QSpinBox()
                control.setMaximumHeight(24)
                control.setRange(param_config.get("min", 1), param_config.get("max", 250))
                control.setValue(param_config.get("default", 20))
                control.setStyleSheet("QSpinBox { font-size: 11px; padding: 2px; }")

            # 设置工具提示
            tooltip = f"{param_config.get('desc', param_name)}\n"
            tooltip += f"默认: {param_config.get('default')}\n"
            tooltip += f"范围: {param_config.get('min', 'N/A')} - {param_config.get('max', 'N/A')}"
            control.setToolTip(tooltip)

            # 参数值变化时的实时反馈
            if isinstance(control, QComboBox):
                control.currentTextChanged.connect(lambda: self.on_param_changed())
            else:
                control.valueChanged.connect(lambda: self.on_param_changed())

            param_layout.addWidget(control)

            # 重置按钮 - 小型
            reset_btn = QPushButton("↺")
            reset_btn.setMaximumSize(20, 20)
            reset_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; font-size: 10px; border-radius: 10px; }")
            reset_btn.setToolTip("重置到默认值")
            reset_btn.clicked.connect(lambda checked, ctrl=control, default=param_config.get("default"): self.reset_param(ctrl, default))
            param_layout.addWidget(reset_btn)

            # 范围信息 - 小字体
            range_label = QLabel(f"[{param_config.get('min', 'N/A')}-{param_config.get('max', 'N/A')}]")
            range_label.setStyleSheet("QLabel { color: #6c757d; font-size: 9px; }")
            range_label.setMaximumWidth(60)
            param_layout.addWidget(range_label)

            self.param_controls[param_name] = control
            self.dynamic_params_layout.addWidget(param_widget)

        # 参数预览 - 紧凑版
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setSpacing(2)
        preview_layout.setContentsMargins(4, 4, 4, 4)

        self.param_preview_label = QLabel("无参数")
        self.param_preview_label.setStyleSheet(
            "QLabel { color: #495057; font-family: monospace; font-size: 12px; background-color: #f8f9fa; padding: 3px; border-radius: 2px; }")
        self.param_preview_label.setWordWrap(True)
        preview_layout.addWidget(self.param_preview_label)

        self.dynamic_params_layout.addWidget(preview_widget)

        # 更新参数预览
        self.update_param_preview()

        # 添加弹性空间
        self.dynamic_params_layout.addStretch()

    def get_current_params(self) -> dict:
        """获取当前设置的参数"""
        params = {}
        for param_name, control in self.param_controls.items():
            if isinstance(control, QComboBox):
                params[param_name] = control.currentIndex()
            elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
                params[param_name] = control.value()
        return params

    def apply_preset_params(self, preset: str):
        """应用参数预设"""
        if preset == "自定义":
            return

        # 根据预设调整参数
        multipliers = {
            "短期交易": 0.5,
            "中期投资": 1.0,
            "长期投资": 2.0
        }

        multiplier = multipliers.get(preset, 1.0)

        for param_name, control in self.param_controls.items():
            if "period" in param_name.lower() and isinstance(control, QSpinBox):
                # 调整周期参数
                default_value = control.value()
                new_value = max(1, int(default_value * multiplier))
                control.setValue(min(new_value, control.maximum()))

    def update_param_preview(self):
        """更新参数预览"""
        try:
            if hasattr(self, 'param_preview_label') and hasattr(self, 'param_controls'):
                current_params = self.get_current_params()
                if current_params:
                    preview_text = "当前参数: " + ", ".join([f"{k}={v}" for k, v in current_params.items()])
                else:
                    preview_text = "当前参数: 无"
                self.param_preview_label.setText(preview_text)
        except Exception as e:
            # 静默处理预览更新错误
            pass

    def on_param_changed(self):
        """参数变化时的回调"""
        try:
            # 更新参数预览
            self.update_param_preview()

            # 如果启用自动计算，延迟计算指标
            if hasattr(self, 'auto_calc_checkbox') and self.auto_calc_checkbox.isChecked():
                # 使用定时器延迟计算，避免频繁计算
                if hasattr(self, '_param_change_timer'):
                    self._param_change_timer.stop()
                else:
                    self._param_change_timer = QTimer()
                    self._param_change_timer.setSingleShot(True)
                    self._param_change_timer.timeout.connect(self.calculate_indicators)

                self._param_change_timer.start(1000)  # 1秒延迟
        except Exception as e:
            # 静默处理参数变化错误
            pass

    def reset_param(self, control, default_value):
        """重置参数到默认值"""
        try:
            if isinstance(control, QComboBox):
                control.setCurrentIndex(default_value if isinstance(default_value, int) else 0)
            elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
                control.setValue(default_value if default_value is not None else 0)
        except Exception as e:
            # 静默处理重置错误
            pass

    def _do_refresh_data(self):
        """实际的数据刷新逻辑"""
        if self.auto_calculate and self.current_kdata is not None:
            self.calculate_indicators()

    def _do_clear_data(self):
        """实际的数据清除逻辑"""
        self.technical_table.setRowCount(0)
        self.indicator_results.clear()
        self.stats_label.setText("统计信息: 无数据")
        self.performance_label.setText("性能: 无统计")

    def toggle_batch_mode(self, state):
        """切换批量计算模式"""
        if state == Qt.Checked:
            # 启用批量模式，显示多选对话框
            self.show_batch_selection_dialog()
        else:
            self.batch_indicators.clear()

    def show_batch_selection_dialog(self):
        """显示批量选择对话框 - 使用表格形式展示ta-lib指标"""
        dialog = QDialog(self)
        dialog.setWindowTitle("批量指标选择")
        dialog.setModal(True)
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        # 顶部筛选区域
        filter_group = QGroupBox("筛选选项")
        filter_layout = QHBoxLayout(filter_group)

        # 分类筛选
        filter_layout.addWidget(QLabel("分类筛选:"))
        self.category_filter_combo = QComboBox()
        categories = ["全部"] + list(get_all_indicators_by_category(use_chinese=True).keys())
        self.category_filter_combo.addItems(categories)
        self.category_filter_combo.currentTextChanged.connect(self.filter_indicators_table)
        filter_layout.addWidget(self.category_filter_combo)

        # 搜索框
        filter_layout.addWidget(QLabel("搜索:"))
        self.search_line_edit = QLineEdit()
        self.search_line_edit.setPlaceholderText("输入指标名称进行搜索...")
        self.search_line_edit.textChanged.connect(self.filter_indicators_table)
        filter_layout.addWidget(self.search_line_edit)

        layout.addWidget(filter_group)

        # 指标表格
        self.indicators_table = QTableWidget()
        self.indicators_table.verticalHeader().setVisible(False)
        self.indicators_table.setColumnCount(4)
        self.indicators_table.setHorizontalHeaderLabels(["选择", "中文名称", "英文名称", "分类"])

        # 设置表格属性
        self.indicators_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.indicators_table.setAlternatingRowColors(True)
        self.indicators_table.setSortingEnabled(True)

        # 设置列宽
        header = self.indicators_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # 选择列固定宽度
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 中文名称自适应
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 英文名称自适应
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 分类列适应内容
        self.indicators_table.setColumnWidth(0, 60)

        # 填充指标数据
        self.populate_indicators_table()

        layout.addWidget(self.indicators_table)

        # 统计信息
        self.selection_stats_label = QLabel("已选择: 0 个指标")
        self.selection_stats_label.setStyleSheet("QLabel { font-weight: bold; color: #007bff; }")
        layout.addWidget(self.selection_stats_label)

        # 按钮区域
        btn_layout = QHBoxLayout()

        # 左侧按钮组
        left_btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        select_all_btn.clicked.connect(lambda: self.select_all_indicators_table(True))

        clear_all_btn = QPushButton("清除")
        clear_all_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; }")
        clear_all_btn.clicked.connect(lambda: self.select_all_indicators_table(False))

        # 常用指标快选
        common_btn = QPushButton("常用指标")
        common_btn.setStyleSheet("QPushButton { background-color: #ffc107; color: black; }")
        common_btn.clicked.connect(self.select_common_indicators)

        left_btn_layout.addWidget(select_all_btn)
        left_btn_layout.addWidget(clear_all_btn)
        left_btn_layout.addWidget(common_btn)
        left_btn_layout.addStretch()

        # 右侧按钮组
        right_btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("QPushButton { background-color: #007bff; color: white; font-weight: bold; }")
        ok_btn.clicked.connect(lambda: self.apply_batch_selection_table(dialog))

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; }")
        cancel_btn.clicked.connect(dialog.reject)

        right_btn_layout.addWidget(ok_btn)
        right_btn_layout.addWidget(cancel_btn)

        btn_layout.addLayout(left_btn_layout)
        btn_layout.addLayout(right_btn_layout)
        layout.addLayout(btn_layout)

        dialog.exec_()

    def populate_indicators_table(self):
        """填充指标表格数据"""
        try:
            # 获取所有ta-lib指标
            all_indicators = get_talib_indicator_list()
            category_map = get_all_indicators_by_category(use_chinese=True)

            if not all_indicators:
                QMessageBox.warning(self, "警告", "未检测到ta-lib指标，请检查ta-lib安装")
                return

            # 创建指标数据列表
            self.indicator_data = []

            for english_name in all_indicators:
                chinese_name = get_talib_chinese_name(english_name)
                category = get_talib_category(english_name)

                self.indicator_data.append({
                    'english_name': english_name,
                    'chinese_name': chinese_name,
                    'category': category,
                    'selected': False
                })

            # 按中文名称排序
            self.indicator_data.sort(key=lambda x: x['chinese_name'])

            # 填充表格
            self.update_indicators_table()

        except Exception as e:
            self.log_manager.error(f"填充指标表格失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"填充指标表格失败: {str(e)}")

    def update_indicators_table(self, filtered_data=None):
        """更新指标表格显示"""
        try:
            data_to_show = filtered_data if filtered_data is not None else self.indicator_data

            self.indicators_table.setRowCount(len(data_to_show))

            for row, indicator in enumerate(data_to_show):
                # 选择列 - 复选框
                checkbox = QCheckBox()
                checkbox.setChecked(indicator['selected'])
                checkbox.stateChanged.connect(self.update_selection_stats)
                # 存储指标数据到复选框
                checkbox.setProperty('indicator_data', indicator)
                self.indicators_table.setCellWidget(row, 0, checkbox)

                # 中文名称
                chinese_item = QTableWidgetItem(indicator['chinese_name'])
                chinese_item.setFlags(chinese_item.flags() & ~Qt.ItemIsEditable)
                self.indicators_table.setItem(row, 1, chinese_item)

                # 英文名称
                english_item = QTableWidgetItem(indicator['english_name'])
                english_item.setFlags(english_item.flags() & ~Qt.ItemIsEditable)
                self.indicators_table.setItem(row, 2, english_item)

                # 分类
                category_item = QTableWidgetItem(indicator['category'])
                category_item.setFlags(category_item.flags() & ~Qt.ItemIsEditable)
                self.indicators_table.setItem(row, 3, category_item)

                # 设置行高
                self.indicators_table.setRowHeight(row, 30)

            # 更新统计信息
            self.update_selection_stats()

        except Exception as e:
            self.log_manager.error(f"更新指标表格失败: {str(e)}")

    def filter_indicators_table(self):
        """根据分类和搜索条件筛选指标表格"""
        try:
            if not hasattr(self, 'indicator_data'):
                return

            category_filter = self.category_filter_combo.currentText()
            search_text = self.search_line_edit.text().lower()

            filtered_data = []

            for indicator in self.indicator_data:
                # 分类筛选
                if category_filter != "全部" and indicator['category'] != category_filter:
                    continue

                # 搜索筛选
                if search_text:
                    if (search_text not in indicator['chinese_name'].lower() and
                            search_text not in indicator['english_name'].lower()):
                        continue

                filtered_data.append(indicator)

            self.update_indicators_table(filtered_data)

        except Exception as e:
            self.log_manager.error(f"筛选指标表格失败: {str(e)}")

    def select_all_indicators_table(self, select: bool):
        """全选/清除表格中的所有指标"""
        try:
            for row in range(self.indicators_table.rowCount()):
                checkbox = self.indicators_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(select)
                    # 更新原始数据
                    indicator_data = checkbox.property('indicator_data')
                    if indicator_data:
                        indicator_data['selected'] = select

            self.update_selection_stats()

        except Exception as e:
            self.log_manager.error(f"全选/清除指标失败: {str(e)}")

    def select_common_indicators(self):
        """选择常用指标"""
        try:
            # 定义常用指标的英文名称
            common_indicators = [
                "MA", "EMA", "MACD", "RSI", "STOCH",
                "BBANDS", "ATR", "OBV", "CCI", "ADX"
            ]

            for row in range(self.indicators_table.rowCount()):
                checkbox = self.indicators_table.cellWidget(row, 0)
                if checkbox:
                    indicator_data = checkbox.property('indicator_data')
                    if indicator_data and indicator_data['english_name'] in common_indicators:
                        checkbox.setChecked(True)
                        indicator_data['selected'] = True

            self.update_selection_stats()

        except Exception as e:
            self.log_manager.error(f"选择常用指标失败: {str(e)}")

    def update_selection_stats(self):
        """更新选择统计信息"""
        try:
            selected_count = 0
            for row in range(self.indicators_table.rowCount()):
                checkbox = self.indicators_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    selected_count += 1

            # 只有在对话框打开时才更新统计标签
            if hasattr(self, 'selection_stats_label'):
                self.selection_stats_label.setText(f"已选择: {selected_count} 个指标")

        except Exception as e:
            self.log_manager.error(f"更新选择统计失败: {str(e)}")

    def apply_batch_selection_table(self, dialog):
        """应用表格中的批量选择"""
        try:
            selected_indicators = []

            for row in range(self.indicators_table.rowCount()):
                checkbox = self.indicators_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    indicator_data = checkbox.property('indicator_data')
                    if indicator_data:
                        # 使用中文名称作为显示名称
                        selected_indicators.append(indicator_data['chinese_name'])

            if not selected_indicators:
                QMessageBox.warning(dialog, "提示", "请至少选择一个指标")
                return

            self.batch_indicators = selected_indicators
            dialog.accept()

            # 显示选择结果
            QMessageBox.information(
                dialog,
                "选择完成",
                f"已选择 {len(selected_indicators)} 个指标进行批量计算:\n" +
                "\n".join(selected_indicators[:10]) +
                (f"\n... 还有 {len(selected_indicators) - 10} 个指标" if len(selected_indicators) > 10 else "")
            )

        except Exception as e:
            self.log_manager.error(f"应用批量选择失败: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"应用选择失败: {str(e)}")

    def select_all_indicators(self, select: bool):
        """全选/清除所有指标 - 保持向后兼容"""
        if hasattr(self, 'batch_checkboxes'):
            # 旧版本的复选框方式
            for checkbox in self.batch_checkboxes.values():
                checkbox.setChecked(select)
        else:
            # 新版本的表格方式
            self.select_all_indicators_table(select)

    def toggle_auto_calculate(self, state):
        """切换自动计算"""
        self.auto_calculate = state == Qt.Checked

    def _validate_kdata(self, kdata) -> bool:
        """验证K线数据的有效性"""
        try:
            if kdata is None:
                self.log_manager.warning("K线数据为空")
                return False

            if not isinstance(kdata, pd.DataFrame):
                self.log_manager.warning("K线数据不是DataFrame格式")
                return False

            if len(kdata) == 0:
                self.log_manager.warning("K线数据长度为0")
                return False

            # 检查必要的列
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in kdata.columns]
            if missing_columns:
                self.log_manager.warning(f"K线数据缺少必要列: {missing_columns}")
                return False

            # 检查数据质量
            for col in required_columns:
                if kdata[col].isna().all():
                    self.log_manager.warning(f"列 {col} 全部为空值")
                    return False

            # 检查OHLC逻辑
            invalid_ohlc = (kdata['high'] < kdata['low']) | \
                (kdata['high'] < kdata['open']) | \
                (kdata['high'] < kdata['close']) | \
                (kdata['low'] > kdata['open']) | \
                (kdata['low'] > kdata['close'])

            if invalid_ohlc.any():
                invalid_count = invalid_ohlc.sum()
                self.log_manager.warning(f"发现 {invalid_count} 行OHLC数据逻辑错误")
                # 不直接返回False，只是警告

            # 检查数据点数量是否足够
            if len(kdata) < 10:
                self.log_manager.warning("K线数据点数量过少，可能影响指标计算准确性")
                return False

            # 检查时间连续性（如果有时间索引）
            if hasattr(kdata.index, 'to_pydatetime'):
                time_diffs = kdata.index.to_series().diff().dropna()
                if len(time_diffs) > 0:
                    max_gap = time_diffs.max()
                    if max_gap > pd.Timedelta(days=30):
                        self.log_manager.warning(f"发现较大时间间隔: {max_gap}")

            self.log_manager.info("K线数据验证通过")
            return True

        except Exception as e:
            self.log_manager.error(f"K线数据验证失败: {str(e)}")
            return False

    def calculate_indicators(self):
        """技术指标分析 - 增强版"""
        try:
            self.log_manager.info("开始计算技术指标...")

            # 验证数据
            if not self._validate_kdata(self.current_kdata):
                self.log_manager.warning("无有效K线数据，无法进行技术分析")
                QMessageBox.warning(self, "提示", "无有效K线数据，无法进行技术分析\n请先加载股票数据")
                return

            self.log_manager.info(f"K线数据验证通过，数据长度: {len(self.current_kdata)}")

            self.show_loading("正在计算技术指标...")
            start_time = time.time()

            # 清空之前的结果
            self.technical_table.setRowCount(0)
            self.indicator_results.clear()
            self.log_manager.info("已清空之前的计算结果")

            # 确定要计算的指标
            indicators_to_calculate = []
            if self.batch_checkbox.isChecked() and self.batch_indicators:
                indicators_to_calculate = self.batch_indicators
                self.log_manager.info(f"批量计算模式，选择了 {len(self.batch_indicators)} 个指标")
            else:
                current_indicator = self.indicator_combo.currentText()
                if current_indicator:
                    indicators_to_calculate = [current_indicator]
                    self.log_manager.info(f"单个指标计算模式，选择指标: {current_indicator}")

            if not indicators_to_calculate:
                self.hide_loading()
                QMessageBox.warning(self, "提示", "请选择要计算的指标")
                return

            self.log_manager.info(f"准备计算 {len(indicators_to_calculate)} 个指标: {indicators_to_calculate}")

            # 批量计算指标
            total_indicators = len(indicators_to_calculate)
            calculated_count = 0
            error_count = 0

            for i, indicator_name in enumerate(indicators_to_calculate):
                try:
                    # 更新进度
                    progress = int((i / total_indicators) * 100)
                    self.update_loading_progress(f"正在计算 {indicator_name}...", progress)
                    self.log_manager.info(f"开始计算指标 {i+1}/{total_indicators}: {indicator_name}")

                    # 计算单个指标
                    result = self._calculate_single_indicator_with_params(indicator_name)
                    if result:
                        self.indicator_results[indicator_name] = result
                        calculated_count += 1
                        self.log_manager.info(f"指标 {indicator_name} 计算成功")

                        # 添加到结果表格
                        self._add_indicator_to_table(indicator_name, result)
                        self.log_manager.info(f"指标 {indicator_name} 已添加到结果表格")
                    else:
                        error_count += 1
                        self.log_manager.warning(f"指标 {indicator_name} 计算失败，结果为空")

                except Exception as e:
                    error_count += 1
                    self.log_manager.error(f"计算指标 {indicator_name} 时出错: {str(e)}")
                    import traceback
                    self.log_manager.error(f"详细错误信息: {traceback.format_exc()}")
                    continue

            # 计算完成
            end_time = time.time()
            calculation_time = end_time - start_time

            # 更新统计信息
            stats_text = f"统计信息: 已计算 {calculated_count}/{total_indicators} 个指标"
            if error_count > 0:
                stats_text += f"，失败 {error_count} 个"

            self.stats_label.setText(stats_text)
            self.stats_label.setStyleSheet("QLabel { font-weight: bold; color: #495057; }")

            self.performance_label.setText(f"性能: 计算耗时 {calculation_time:.2f}秒")

            self.hide_loading()

            # 显示结果统计
            result_message = f"技术指标计算完成！\n"
            result_message += f"成功计算: {calculated_count} 个指标\n"
            result_message += f"计算耗时: {calculation_time:.2f} 秒\n"
            result_message += f"结果表格行数: {self.technical_table.rowCount()}"

            if error_count > 0:
                result_message += f"\n失败: {error_count} 个指标"

            self.log_manager.info(result_message)

            if calculated_count > 0:
                # 发送指标计算完成信号
                self.indicator_calculated.emit("batch", self.indicator_results)

                # 强制刷新表格显示
                self.technical_table.viewport().update()
                self.technical_table.repaint()

                # 自动滚动到表格顶部
                if self.technical_table.rowCount() > 0:
                    self.technical_table.scrollToTop()
                    self.technical_table.selectRow(0)
            else:
                error_msg = "没有成功计算任何指标，请检查：\n"
                error_msg += "1. 数据是否有效\n"
                error_msg += "2. 参数设置是否正确\n"
                error_msg += "3. ta-lib库是否正确安装"
                QMessageBox.warning(self, "计算失败", error_msg)

        except Exception as e:
            self.hide_loading()
            error_msg = f"技术指标计算过程出错: {str(e)}"
            self.log_manager.error(error_msg)
            import traceback
            self.log_manager.error(f"详细错误信息: {traceback.format_exc()}")
            QMessageBox.critical(self, "错误", error_msg)

    def _calculate_single_indicator_with_params(self, indicator_name: str) -> Optional[Dict[str, Any]]:
        """使用动态参数计算单个指标"""
        try:
            # 获取指标的英文名称
            english_name = get_indicator_english_name(indicator_name)
            if not english_name:
                self.log_manager.warning(f"无法找到指标 {indicator_name} 的英文名称")
                return None

            # 获取当前参数设置
            params = self.get_current_params()

            # 获取指标配置
            config = get_indicator_params_config(english_name)
            inputs_needed = config.get("inputs", ["close"])

            # 验证输入数据是否存在
            for input_type in inputs_needed:
                if input_type not in self.current_kdata.columns:
                    self.log_manager.warning(f"缺少输入数据: {input_type}")
                    return None

            # 调用ta-lib计算指标 - 直接传递DataFrame
            from indicators_algo import calc_talib_indicator
            result = calc_talib_indicator(english_name, self.current_kdata, **params)

            if result is None:
                self.log_manager.warning(f"指标 {indicator_name} 计算结果为空")
                return None

            # 处理结果
            processed_result = self._process_indicator_result(indicator_name, result)
            return processed_result

        except Exception as e:
            self.log_manager.error(f"计算指标 {indicator_name} 时出错: {str(e)}")
            import traceback
            self.log_manager.error(f"详细错误信息: {traceback.format_exc()}")
            return None

    def _process_indicator_result(self, indicator_name: str, result: Any) -> Dict[str, Any]:
        """处理指标计算结果"""
        try:
            processed = {
                "name": indicator_name,
                "timestamp": datetime.now(),
                "values": {},
                "signals": [],
                "summary": {}
            }

            # 处理不同类型的结果
            if isinstance(result, pd.DataFrame):
                # DataFrame结果（如MACD、STOCH等多输出指标）
                for col in result.columns:
                    processed["values"][col] = result[col].values
            elif isinstance(result, pd.Series):
                # Series结果（如RSI、MA等单输出指标）
                processed["values"]["main"] = result.values
            elif isinstance(result, tuple):
                # 元组结果（旧版本兼容）
                output_names = self._get_indicator_output_names(indicator_name)
                for i, value in enumerate(result):
                    if i < len(output_names):
                        if isinstance(value, (pd.Series, pd.DataFrame)):
                            processed["values"][output_names[i]] = value.values
                        else:
                            processed["values"][output_names[i]] = value
                    else:
                        processed["values"][f"output_{i}"] = value
            elif isinstance(result, np.ndarray):
                # 数组结果
                processed["values"]["main"] = result
            else:
                # 其他类型
                self.log_manager.warning(f"未知的结果类型: {type(result)}")
                processed["values"]["main"] = result

            # 生成信号分析
            processed["signals"] = self._generate_signals(indicator_name, processed["values"])

            # 生成摘要统计
            processed["summary"] = self._generate_summary(processed["values"])

            return processed

        except Exception as e:
            self.log_manager.error(f"处理指标结果时出错: {str(e)}")
            import traceback
            self.log_manager.error(f"详细错误信息: {traceback.format_exc()}")
            return {"name": indicator_name, "error": str(e)}

    def _get_indicator_output_names(self, indicator_name: str) -> List[str]:
        """获取指标的输出名称"""
        english_name = get_indicator_english_name(indicator_name)

        # 定义常见指标的输出名称
        output_names_map = {
            "MACD": ["macd", "signal", "histogram"],
            "STOCH": ["slowk", "slowd"],
            "STOCHF": ["fastk", "fastd"],
            "STOCHRSI": ["fastk", "fastd"],
            "BBANDS": ["upper", "middle", "lower"],
            "AROON": ["aroondown", "aroonup"],
            "HT_PHASOR": ["inphase", "quadrature"],
            "HT_SINE": ["sine", "leadsine"],
            "MINMAX": ["min", "max"],
            "MINMAXINDEX": ["minidx", "maxidx"],
        }

        return output_names_map.get(english_name, ["main"])

    def _generate_signals(self, indicator_name: str, values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成交易信号"""
        signals = []
        try:
            # 根据指标类型生成不同的信号
            english_name = get_indicator_english_name(indicator_name)

            if english_name == "RSI" and "main" in values:
                rsi_values = values["main"]
                if len(rsi_values) > 0:
                    latest_rsi = rsi_values[-1]
                    if not np.isnan(latest_rsi):
                        if latest_rsi > 70:
                            signals.append({"type": "sell", "strength": "strong", "reason": f"RSI超买({latest_rsi:.2f})"})
                        elif latest_rsi < 30:
                            signals.append({"type": "buy", "strength": "strong", "reason": f"RSI超卖({latest_rsi:.2f})"})
                        elif latest_rsi > 50:
                            signals.append({"type": "neutral", "strength": "weak", "reason": f"RSI偏强({latest_rsi:.2f})"})
                        else:
                            signals.append({"type": "neutral", "strength": "weak", "reason": f"RSI偏弱({latest_rsi:.2f})"})

            elif english_name == "MACD" and all(k in values for k in ["MACD_1", "MACD_2"]):
                macd_line = values["MACD_1"]
                signal_line = values["MACD_2"]
                if len(macd_line) > 1 and len(signal_line) > 1:
                    if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
                        signals.append({"type": "buy", "strength": "medium", "reason": "MACD金叉"})
                    elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
                        signals.append({"type": "sell", "strength": "medium", "reason": "MACD死叉"})
                    elif macd_line[-1] > signal_line[-1]:
                        signals.append({"type": "buy", "strength": "weak", "reason": "MACD多头"})
                    else:
                        signals.append({"type": "sell", "strength": "weak", "reason": "MACD空头"})

            elif english_name == "STOCH" and all(k in values for k in ["STOCH_1", "STOCH_2"]):
                k_values = values["STOCH_1"]
                d_values = values["STOCH_2"]
                if len(k_values) > 0 and len(d_values) > 0:
                    latest_k = k_values[-1]
                    latest_d = d_values[-1]
                    if not np.isnan(latest_k) and not np.isnan(latest_d):
                        if latest_k > 80 and latest_d > 80:
                            signals.append({"type": "sell", "strength": "strong", "reason": f"KDJ超买(K:{latest_k:.1f},D:{latest_d:.1f})"})
                        elif latest_k < 20 and latest_d < 20:
                            signals.append({"type": "buy", "strength": "strong", "reason": f"KDJ超卖(K:{latest_k:.1f},D:{latest_d:.1f})"})
                        elif len(k_values) > 1 and len(d_values) > 1:
                            if k_values[-1] > d_values[-1] and k_values[-2] <= d_values[-2]:
                                signals.append({"type": "buy", "strength": "medium", "reason": "KDJ金叉"})
                            elif k_values[-1] < d_values[-1] and k_values[-2] >= d_values[-2]:
                                signals.append({"type": "sell", "strength": "medium", "reason": "KDJ死叉"})

            elif english_name == "BBANDS" and all(k in values for k in ["BBANDS_1", "BBANDS_2", "BBANDS_3"]):
                upper = values["BBANDS_1"]
                middle = values["BBANDS_2"]
                lower = values["BBANDS_3"]
                if len(upper) > 0 and len(middle) > 0 and len(lower) > 0:
                    # 需要当前价格来判断布林带信号，这里使用中轨作为参考
                    current_price = middle[-1]  # 假设当前价格接近中轨
                    upper_val = upper[-1]
                    lower_val = lower[-1]
                    if not np.isnan(current_price):
                        if current_price >= upper_val:
                            signals.append({"type": "sell", "strength": "medium", "reason": "触及布林上轨"})
                        elif current_price <= lower_val:
                            signals.append({"type": "buy", "strength": "medium", "reason": "触及布林下轨"})
                        else:
                            signals.append({"type": "neutral", "strength": "weak", "reason": "布林带中轨区间"})

            elif english_name == "CCI" and "main" in values:
                cci_values = values["main"]
                if len(cci_values) > 0:
                    latest_cci = cci_values[-1]
                    if not np.isnan(latest_cci):
                        if latest_cci > 100:
                            signals.append({"type": "sell", "strength": "medium", "reason": f"CCI超买({latest_cci:.1f})"})
                        elif latest_cci < -100:
                            signals.append({"type": "buy", "strength": "medium", "reason": f"CCI超卖({latest_cci:.1f})"})
                        else:
                            signals.append({"type": "neutral", "strength": "weak", "reason": f"CCI正常({latest_cci:.1f})"})

            elif english_name == "ADX" and "main" in values:
                adx_values = values["main"]
                if len(adx_values) > 0:
                    latest_adx = adx_values[-1]
                    if not np.isnan(latest_adx):
                        if latest_adx > 25:
                            signals.append({"type": "neutral", "strength": "strong", "reason": f"趋势强劲(ADX:{latest_adx:.1f})"})
                        elif latest_adx > 20:
                            signals.append({"type": "neutral", "strength": "medium", "reason": f"趋势中等(ADX:{latest_adx:.1f})"})
                        else:
                            signals.append({"type": "neutral", "strength": "weak", "reason": f"趋势微弱(ADX:{latest_adx:.1f})"})

            elif english_name in ["MA", "EMA", "SMA"] and "main" in values:
                ma_values = values["main"]
                if len(ma_values) > 1:
                    current_ma = ma_values[-1]
                    prev_ma = ma_values[-2]
                    if not np.isnan(current_ma) and not np.isnan(prev_ma):
                        if current_ma > prev_ma:
                            signals.append({"type": "buy", "strength": "weak", "reason": f"均线上升({current_ma:.2f})"})
                        elif current_ma < prev_ma:
                            signals.append({"type": "sell", "strength": "weak", "reason": f"均线下降({current_ma:.2f})"})
                        else:
                            signals.append({"type": "neutral", "strength": "weak", "reason": f"均线平稳({current_ma:.2f})"})

            elif english_name == "ATR" and "main" in values:
                atr_values = values["main"]
                if len(atr_values) > 0:
                    latest_atr = atr_values[-1]
                    if not np.isnan(latest_atr):
                        # ATR主要用于衡量波动性
                        if len(atr_values) > 20:
                            avg_atr = np.mean(atr_values[-20:])
                            if latest_atr > avg_atr * 1.5:
                                signals.append({"type": "neutral", "strength": "strong", "reason": f"波动性高(ATR:{latest_atr:.3f})"})
                            elif latest_atr < avg_atr * 0.5:
                                signals.append({"type": "neutral", "strength": "weak", "reason": f"波动性低(ATR:{latest_atr:.3f})"})
                            else:
                                signals.append({"type": "neutral", "strength": "medium", "reason": f"波动性正常(ATR:{latest_atr:.3f})"})
                        else:
                            signals.append({"type": "neutral", "strength": "medium", "reason": f"波动性正常(ATR:{latest_atr:.3f})"})

            elif english_name == "OBV" and "main" in values:
                obv_values = values["main"]
                if len(obv_values) > 1:
                    current_obv = obv_values[-1]
                    prev_obv = obv_values[-2]
                    if not np.isnan(current_obv) and not np.isnan(prev_obv):
                        if current_obv > prev_obv:
                            signals.append({"type": "buy", "strength": "weak", "reason": f"成交量上升"})
                        elif current_obv < prev_obv:
                            signals.append({"type": "sell", "strength": "weak", "reason": f"成交量下降"})
                        else:
                            signals.append({"type": "neutral", "strength": "weak", "reason": f"成交量平稳"})

            # 如果没有生成任何信号，提供默认信号
            if not signals:
                signals.append({"type": "neutral", "strength": "weak", "reason": "无明确信号"})

        except Exception as e:
            self.log_manager.error(f"生成信号时出错: {str(e)}")
            signals.append({"type": "neutral", "strength": "weak", "reason": "信号计算错误"})

        return signals

    def _generate_summary(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """生成指标摘要统计"""
        summary = {}
        try:
            for name, data in values.items():
                if isinstance(data, np.ndarray) and len(data) > 0:
                    valid_data = data[~np.isnan(data)]
                    if len(valid_data) > 0:
                        summary[name] = {
                            "current": float(data[-1]) if not np.isnan(data[-1]) else None,
                            "mean": float(np.mean(valid_data)),
                            "std": float(np.std(valid_data)),
                            "min": float(np.min(valid_data)),
                            "max": float(np.max(valid_data)),
                            "count": len(valid_data)
                        }
        except Exception as e:
            self.log_manager.error(f"生成摘要时出错: {str(e)}")

        return summary

    def _add_indicator_to_table(self, indicator_name: str, result: Dict[str, Any]):
        """将指标结果添加到表格"""
        try:
            self.log_manager.info(f"开始添加指标 {indicator_name} 到表格")

            # 临时禁用排序，避免添加数据时的显示问题
            sorting_enabled = self.technical_table.isSortingEnabled()
            self.technical_table.setSortingEnabled(False)

            if "error" in result:
                # 错误情况
                row = self.technical_table.rowCount()
                self.technical_table.insertRow(row)
                self.technical_table.setItem(row, 0, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M")))
                self.technical_table.setItem(row, 1, QTableWidgetItem(indicator_name))
                self.technical_table.setItem(row, 2, QTableWidgetItem("计算错误"))
                self.technical_table.setItem(row, 7, QTableWidgetItem(result["error"]))
                self.log_manager.warning(f"指标 {indicator_name} 计算错误: {result['error']}")
                # 恢复排序设置
                self.technical_table.setSortingEnabled(sorting_enabled)
                return

            # 正常结果
            values = result.get("values", {})
            signals = result.get("signals", [])
            summary = result.get("summary", {})

            self.log_manager.info(f"指标 {indicator_name} 的值: {list(values.keys())}")

            # 为每个输出值创建一行
            rows_added = 0
            for value_name, value_data in values.items():
                self.log_manager.info(
                    f"处理值 {value_name}, 数据类型: {type(value_data)}, 长度: {len(value_data) if hasattr(value_data, '__len__') else 'N/A'}")

                # 处理不同类型的数据
                if isinstance(value_data, np.ndarray):
                    if len(value_data) > 0:
                        current_value = value_data[-1] if not np.isnan(value_data[-1]) else None
                    else:
                        current_value = None
                elif isinstance(value_data, (pd.Series, pd.DataFrame)):
                    if len(value_data) > 0:
                        if isinstance(value_data, pd.Series):
                            current_value = value_data.iloc[-1] if not pd.isna(value_data.iloc[-1]) else None
                        else:
                            current_value = value_data.iloc[-1, 0] if not pd.isna(value_data.iloc[-1, 0]) else None
                    else:
                        current_value = None
                elif isinstance(value_data, (int, float)):
                    current_value = value_data if not np.isnan(value_data) else None
                else:
                    self.log_manager.warning(f"未知的数据类型: {type(value_data)}")
                    current_value = None

                self.log_manager.info(f"当前值: {current_value}")

                if current_value is not None:
                    row = self.technical_table.rowCount()
                    self.technical_table.insertRow(row)

                    # 日期
                    date_item = QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M"))
                    self.technical_table.setItem(row, 0, date_item)

                    # 指标名称 - 改进显示逻辑
                    if value_name == "main":
                        display_name = indicator_name
                    else:
                        # 为多输出指标提供更专业的名称
                        if indicator_name == "MACD指标":
                            name_map = {"MACD_1": "MACD线", "MACD_2": "信号线", "MACD_3": "柱状图"}
                            display_name = f"MACD-{name_map.get(value_name, value_name)}"
                        elif indicator_name == "布林带":
                            name_map = {"BBANDS_1": "上轨", "BBANDS_2": "中轨", "BBANDS_3": "下轨"}
                            display_name = f"布林带-{name_map.get(value_name, value_name)}"
                        elif indicator_name == "随机指标":
                            name_map = {"STOCH_1": "%K线", "STOCH_2": "%D线"}
                            display_name = f"KDJ-{name_map.get(value_name, value_name)}"
                        else:
                            display_name = f"{indicator_name}-{value_name}"

                    indicator_item = QTableWidgetItem(display_name)
                    self.technical_table.setItem(row, 1, indicator_item)

                    # 数值
                    value_item = QTableWidgetItem(f"{current_value:.4f}")
                    self.technical_table.setItem(row, 2, value_item)

                    # 信号
                    signal_text = ""
                    signal_strength = ""
                    signal_trend = ""
                    signal_advice = ""

                    if signals:
                        signal = signals[0]  # 取第一个信号
                        signal_text = signal.get("type", "")
                        signal_strength = signal.get("strength", "")
                        signal_trend = signal.get("reason", "")

                        if signal_text == "buy":
                            signal_advice = "买入"
                        elif signal_text == "sell":
                            signal_advice = "卖出"
                        else:
                            signal_advice = "观望"

                    signal_item = QTableWidgetItem(signal_text)
                    self.technical_table.setItem(row, 3, signal_item)

                    strength_item = QTableWidgetItem(signal_strength)
                    self.technical_table.setItem(row, 4, strength_item)

                    trend_item = QTableWidgetItem(signal_trend)
                    self.technical_table.setItem(row, 5, trend_item)

                    advice_item = QTableWidgetItem(signal_advice)
                    self.technical_table.setItem(row, 6, advice_item)

                    # 根据信号类型设置专业颜色
                    if signal_text == "sell":
                        # 买入信号 - 绿色系
                        signal_color = QColor(34, 139, 34)  # 森林绿
                        advice_color = QColor(0, 128, 0)    # 绿色
                        if signal_strength == "strong":
                            signal_color = QColor(0, 100, 0)  # 深绿
                        elif signal_strength == "medium":
                            signal_color = QColor(34, 139, 34)  # 森林绿
                        else:
                            signal_color = QColor(144, 238, 144)  # 浅绿
                    elif signal_text == "buy":
                        # 卖出信号 - 红色系
                        signal_color = QColor(220, 20, 60)   # 深红
                        advice_color = QColor(255, 0, 0)     # 红色
                        if signal_strength == "strong":
                            signal_color = QColor(139, 0, 0)  # 深红
                        elif signal_strength == "medium":
                            signal_color = QColor(220, 20, 60)  # 深红
                        else:
                            signal_color = QColor(255, 182, 193)  # 浅红
                    else:
                        # 中性信号 - 灰色系
                        signal_color = QColor(128, 128, 128)  # 灰色
                        advice_color = QColor(105, 105, 105)  # 暗灰
                        if signal_strength == "strong":
                            signal_color = QColor(64, 64, 64)  # 深灰
                        elif signal_strength == "medium":
                            signal_color = QColor(128, 128, 128)  # 灰色
                        else:
                            signal_color = QColor(192, 192, 192)  # 浅灰

                    # 设置信号列颜色
                    signal_item.setForeground(signal_color)
                    signal_item.setFont(self._get_bold_font())

                    # 设置强度列颜色
                    strength_item.setForeground(signal_color)

                    # 设置趋势列颜色
                    trend_item.setForeground(signal_color)

                    # 设置建议列颜色和背景
                    advice_item.setForeground(advice_color)
                    advice_item.setFont(self._get_bold_font())

                    # 为建议列设置背景色
                    if signal_text == "sell":
                        advice_item.setBackground(QColor(240, 255, 240))  # 浅绿背景
                    elif signal_text == "buy":
                        advice_item.setBackground(QColor(255, 240, 240))  # 浅红背景
                    else:
                        advice_item.setBackground(QColor(248, 248, 248))  # 浅灰背景

                    # 数值列根据涨跌设置颜色
                    try:
                        numeric_value = float(current_value)
                        if numeric_value > 0:
                            value_item.setForeground(QColor(220, 20, 60))  # 红色（涨）
                        elif numeric_value < 0:
                            value_item.setForeground(QColor(34, 139, 34))  # 绿色（跌）
                        else:
                            value_item.setForeground(QColor(128, 128, 128))  # 灰色（平）
                    except:
                        # 如果不是数值，保持默认颜色
                        pass

                    # 指标名称根据类型设置颜色
                    if "MACD" in display_name:
                        indicator_item.setForeground(QColor(75, 0, 130))  # 靛蓝
                    elif "布林带" in display_name:
                        indicator_item.setForeground(QColor(255, 140, 0))  # 橙色
                    elif "KDJ" in display_name or "随机" in display_name:
                        indicator_item.setForeground(QColor(138, 43, 226))  # 紫色
                    elif "RSI" in display_name or "相对强弱" in display_name:
                        indicator_item.setForeground(QColor(30, 144, 255))  # 蓝色
                    elif "均线" in display_name or "移动平均" in display_name:
                        indicator_item.setForeground(QColor(255, 20, 147))  # 深粉
                    else:
                        indicator_item.setForeground(QColor(47, 79, 79))  # 深灰绿

                    # 备注 - 显示统计信息
                    note_text = ""
                    if value_name in summary:
                        stats = summary[value_name]
                        note_text = f"均值:{stats.get('mean', 0):.4f} 标准差:{stats.get('std', 0):.4f}"

                    note_item = QTableWidgetItem(note_text)
                    self.technical_table.setItem(row, 7, note_item)

                    rows_added += 1
                    self.log_manager.info(f"成功添加行 {row} 到表格")
                else:
                    self.log_manager.warning(f"值 {value_name} 的当前值为空，跳过添加")

            # 恢复排序设置
            self.technical_table.setSortingEnabled(sorting_enabled)

            # 强制刷新表格显示
            self.technical_table.viewport().update()

            self.log_manager.info(f"指标 {indicator_name} 总共添加了 {rows_added} 行到表格")

        except Exception as e:
            # 确保在异常情况下也恢复排序设置
            if hasattr(self, 'technical_table'):
                self.technical_table.setSortingEnabled(True)
            self.log_manager.error(f"添加指标到表格时出错: {str(e)}")
            import traceback
            self.log_manager.error(f"详细错误信息: {traceback.format_exc()}")

    def clear_cache(self):
        """清除缓存"""
        self.indicator_cache.clear()
        self.log_manager.info("指标缓存已清除")
        QMessageBox.information(self, "提示", "指标缓存已清除")

    def clear_indicators(self):
        """清除指标"""
        self._do_clear_data()
        self.log_manager.info("技术指标已清除")

    def _get_export_specific_data(self) -> Optional[Dict[str, Any]]:
        """获取特定的导出数据"""
        return {
            'indicator_results': self.indicator_results,
            'current_parameters': self.get_current_params(),
            'batch_mode': self.batch_checkbox.isChecked(),
            'auto_calculate': self.auto_calculate,
            'cache_size': len(self.indicator_cache),
            'selected_indicator': self.indicator_combo.currentText(),
            'selected_category': self.category_combo.currentText(),
            'batch_indicators': self.batch_indicators
        }

    # 保持原有的导出功能...
    def create_export_section(self):
        """创建导出功能区域"""
        export_group = QGroupBox("数据导出")
        export_layout = QHBoxLayout(export_group)

        # 导出格式选择
        export_layout.addWidget(QLabel("导出格式:"))
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["Excel", "CSV", "JSON"])
        export_layout.addWidget(self.export_format_combo)

        # 导出按钮
        export_btn = QPushButton("导出技术分析结果")
        export_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; }")
        export_btn.clicked.connect(self.export_technical_data)
        export_layout.addWidget(export_btn)

        export_layout.addStretch()
        return export_group

    def export_technical_data(self):
        """导出技术分析数据"""
        try:
            if not hasattr(self, 'technical_table') or self.technical_table.rowCount() == 0:
                QMessageBox.warning(self, "警告", "没有可导出的技术分析数据")
                return

            format_type = self.export_format_combo.currentText()

            # 获取保存文件路径
            from PyQt5.QtWidgets import QFileDialog
            if format_type == "Excel":
                filename, _ = QFileDialog.getSaveFileName(
                    self, "导出技术分析数据", f"technical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    "Excel files (*.xlsx)")
            elif format_type == "CSV":
                filename, _ = QFileDialog.getSaveFileName(
                    self, "导出技术分析数据", f"technical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "CSV files (*.csv)")
            else:  # JSON
                filename, _ = QFileDialog.getSaveFileName(
                    self, "导出技术分析数据", f"technical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    "JSON files (*.json)")

            if not filename:
                return

            # 使用基类的导出功能
            export_data = self.export_data(format_type.lower())
            if export_data:
                if format_type == "JSON":
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                else:
                    # 收集表格数据用于Excel/CSV导出
                    table_data = []
                    headers = []
                    for col in range(self.technical_table.columnCount()):
                        headers.append(self.technical_table.horizontalHeaderItem(col).text())

                    for row in range(self.technical_table.rowCount()):
                        row_data = {}
                        for col in range(self.technical_table.columnCount()):
                            item = self.technical_table.item(row, col)
                            row_data[headers[col]] = item.text() if item else ""
                        table_data.append(row_data)

                    if format_type == "Excel":
                        self._export_to_excel(filename, table_data, headers)
                    else:
                        self._export_to_csv(filename, table_data, headers)

                QMessageBox.information(self, "成功", f"技术分析数据已导出到: {filename}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def _export_to_excel(self, filename, data, headers):
        """导出到Excel文件"""
        try:
            import pandas as pd
            df = pd.DataFrame(data)

            # 添加元数据
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 写入技术分析数据
                df.to_excel(writer, sheet_name='技术分析', index=False)

                # 写入元数据
                metadata = {
                    '导出时间': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    '数据类型': ['技术分析'],
                    '指标数量': [len(data)],
                    '股票代码': [getattr(self.current_kdata, 'stock', {}).get('code', 'N/A') if self.current_kdata else 'N/A']
                }
                meta_df = pd.DataFrame(metadata)
                meta_df.to_excel(writer, sheet_name='元数据', index=False)

        except ImportError:
            # 如果没有pandas，使用基础方法
            import csv
            self._export_to_csv(filename.replace('.xlsx', '.csv'), data, headers)

    def _export_to_csv(self, filename, data, headers):
        """导出到CSV文件"""
        import csv
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

    def apply_batch_selection(self, dialog):
        """应用批量选择 - 保持向后兼容"""
        if hasattr(self, 'batch_checkboxes'):
            # 旧版本的复选框方式
            self.batch_indicators = [
                indicator for indicator, checkbox in self.batch_checkboxes.items()
                if checkbox.isChecked()
            ]
            dialog.accept()
        else:
            # 新版本的表格方式
            self.apply_batch_selection_table(dialog)

    def show_loading(self, message="正在分析..."):
        """显示加载状态 - 本地实现"""
        self.is_loading = True

        # 禁用计算按钮
        if hasattr(self, 'calc_btn'):
            self.calc_btn.setEnabled(False)
            self.calc_btn.setText("计算中...")

        # 更新状态标签
        if hasattr(self, 'stats_label'):
            self.stats_label.setText(f"状态: {message}")
            self.stats_label.setStyleSheet("QLabel { font-weight: bold; color: #007bff; }")

        # 设置鼠标为等待状态
        self.setCursor(Qt.WaitCursor)

        # 强制刷新界面
        QApplication.processEvents()

        self.log_manager.debug(f"{self.__class__.__name__}: {message}")

    def hide_loading(self):
        """隐藏加载状态 - 本地实现"""
        self.is_loading = False

        # 恢复计算按钮
        if hasattr(self, 'calc_btn'):
            self.calc_btn.setEnabled(True)
            self.calc_btn.setText("计算指标")

        # 恢复鼠标状态
        self.setCursor(Qt.ArrowCursor)

        # 强制刷新界面
        QApplication.processEvents()

    def update_loading_progress(self, message: str, progress: int = 0):
        """更新加载进度 - 本地实现"""
        if hasattr(self, 'stats_label'):
            self.stats_label.setText(f"状态: {message} ({progress}%)")

        # 强制刷新界面
        QApplication.processEvents()

    def _get_bold_font(self):
        """获取粗体字体"""
        font = QFont()
        font.setBold(True)
        return font
