"""
指标选股筛选对话框

参考同花顺、Wind等专业金融软件的筛选界面设计，
提供更紧凑、高效的筛选条件设置界面。
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSplitter,
    QTabWidget, QWidget, QFormLayout, QScrollArea,
    QSlider, QDateEdit, QListWidget, QListWidgetItem,
    QAbstractItemView, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QDate
from PyQt5.QtGui import QFont, QIcon, QPalette

logger = logging.getLogger(__name__)


class CompactAdvancedFilterDialog(QDialog):
    """批量指标选股筛选对话框"""

    # 定义信号
    filters_applied = pyqtSignal(dict)  # 筛选条件应用信号
    preview_requested = pyqtSignal(dict)  # 预览请求信号

    def __init__(self, parent=None, columns_config=None):
        super().__init__(parent)
        self.setWindowTitle("批量指标选股筛选器")
        self.setModal(True)
        self.resize(900, 650)

        # 筛选配置
        self.columns_config = columns_config or self._get_default_columns_config()
        self.filter_conditions = {}
        self.quick_filters = {}
        self.preview_count = 0

        # 预览定时器
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._update_preview)

        self._create_ui()
        self._setup_styles()
        self._load_quick_filters()

    def _get_default_columns_config(self):
        """获取默认列配置"""
        return {
            '股票代码': {'type': 'text', 'label': '代码'},
            '股票名称': {'type': 'text', 'label': '名称'},
            '指标名称': {'type': 'selection', 'label': '指标', 'options': [
                'MA', 'EMA', 'MACD', 'RSI', 'BOLL', 'KDJ', 'CCI', 'ATR', 'OBV'
            ]},
            '指标数值': {'type': 'numeric', 'label': '数值'},
            '信号类型': {'type': 'selection', 'label': '信号', 'options': [
                '买入', '卖出', '持有', '超买', '超卖', '中性'
            ]},
            '信号强度': {'type': 'selection', 'label': '强度', 'options': [
                '强', '中', '弱'
            ]},
            '趋势方向': {'type': 'selection', 'label': '趋势', 'options': [
                '上升', '下降', '震荡', '突破'
            ]},
            '计算日期': {'type': 'date', 'label': '日期'},
            '涨跌幅': {'type': 'numeric', 'label': '涨跌幅%'},
            '成交量': {'type': 'numeric', 'label': '成交量'},
            '换手率': {'type': 'numeric', 'label': '换手率%'}
        }

    def _create_ui(self):
        """创建用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 创建顶部工具栏
        self._create_toolbar(layout)

        # 创建主要内容区域
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)

        # 左侧：筛选条件设置
        left_panel = self._create_filter_panel()
        main_splitter.addWidget(left_panel)

        # 右侧：预览和结果
        right_panel = self._create_preview_panel()
        main_splitter.addWidget(right_panel)

        # 设置分割比例
        main_splitter.setSizes([550, 350])

        # 底部按钮栏
        self._create_button_bar(layout)

    def _create_toolbar(self, parent_layout):
        """创建顶部工具栏"""
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.StyledPanel)
        toolbar.setMaximumHeight(50)
        parent_layout.addWidget(toolbar)

        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 8, 8, 8)

        # 快速筛选按钮
        quick_label = QLabel("快速筛选:")
        quick_label.setStyleSheet("font-weight: bold; color: #495057;")
        toolbar_layout.addWidget(quick_label)

        self.quick_filter_combo = QComboBox()
        self.quick_filter_combo.setMinimumWidth(150)
        self.quick_filter_combo.currentTextChanged.connect(self._apply_quick_filter)
        toolbar_layout.addWidget(self.quick_filter_combo)

        toolbar_layout.addSpacing(20)

        # 预览开关
        self.preview_checkbox = QCheckBox("实时预览")
        self.preview_checkbox.setChecked(True)
        self.preview_checkbox.toggled.connect(self._toggle_preview)
        toolbar_layout.addWidget(self.preview_checkbox)

        # 预览结果计数
        self.preview_label = QLabel("匹配结果: 0 条")
        self.preview_label.setStyleSheet("color: #28a745; font-weight: bold;")
        toolbar_layout.addWidget(self.preview_label)

        toolbar_layout.addStretch()

        # 保存筛选方案按钮
        save_filter_btn = QPushButton("💾 保存方案")
        save_filter_btn.setToolTip("保存当前筛选条件为快速筛选方案")
        save_filter_btn.clicked.connect(self._save_filter_scheme)
        toolbar_layout.addWidget(save_filter_btn)

    def _create_filter_panel(self):
        """创建筛选条件面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 筛选条件标签页
        self.filter_tabs = QTabWidget()
        layout.addWidget(self.filter_tabs)

        # 基础筛选标签页
        basic_tab = self._create_basic_filter_tab()
        self.filter_tabs.addTab(basic_tab, "📊 基础筛选")

        # 技术指标标签页
        technical_tab = self._create_technical_filter_tab()
        self.filter_tabs.addTab(technical_tab, "📈 技术指标")

        # 高级筛选标签页
        advanced_tab = self._create_advanced_filter_tab()
        self.filter_tabs.addTab(advanced_tab, "⚙️ 高级条件")

        return panel

    def _create_basic_filter_tab(self):
        """创建基础筛选标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 使用紧凑的表单布局
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft)
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(12)

        # 股票代码筛选
        code_layout = QHBoxLayout()
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("如: 000001,000002 或 使用*通配符")
        self.code_edit.textChanged.connect(self._on_filter_changed)
        code_layout.addWidget(self.code_edit)

        self.code_exclude_cb = QCheckBox("排除")
        code_layout.addWidget(self.code_exclude_cb)
        form_layout.addRow("股票代码:", code_layout)

        # 股票名称筛选
        name_layout = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入股票名称关键词")
        self.name_edit.textChanged.connect(self._on_filter_changed)
        name_layout.addWidget(self.name_edit)

        self.name_exclude_cb = QCheckBox("排除")
        name_layout.addWidget(self.name_exclude_cb)
        form_layout.addRow("股票名称:", name_layout)

        # 涨跌幅范围
        range_layout = QHBoxLayout()
        self.change_min_spin = QDoubleSpinBox()
        self.change_min_spin.setRange(-20.0, 20.0)
        self.change_min_spin.setDecimals(2)
        self.change_min_spin.setSuffix("%")
        self.change_min_spin.valueChanged.connect(self._on_filter_changed)
        range_layout.addWidget(self.change_min_spin)

        range_layout.addWidget(QLabel("至"))

        self.change_max_spin = QDoubleSpinBox()
        self.change_max_spin.setRange(-20.0, 20.0)
        self.change_max_spin.setDecimals(2)
        self.change_max_spin.setSuffix("%")
        self.change_max_spin.setValue(10.0)
        self.change_max_spin.valueChanged.connect(self._on_filter_changed)
        range_layout.addWidget(self.change_max_spin)
        form_layout.addRow("涨跌幅范围:", range_layout)

        # 成交量范围
        volume_layout = QHBoxLayout()
        self.volume_min_spin = QSpinBox()
        self.volume_min_spin.setRange(0, 999999999)
        self.volume_min_spin.setSuffix(" 万")
        self.volume_min_spin.valueChanged.connect(self._on_filter_changed)
        volume_layout.addWidget(self.volume_min_spin)

        volume_layout.addWidget(QLabel("至"))

        self.volume_max_spin = QSpinBox()
        self.volume_max_spin.setRange(0, 999999999)
        self.volume_max_spin.setValue(100000)
        self.volume_max_spin.setSuffix(" 万")
        self.volume_max_spin.valueChanged.connect(self._on_filter_changed)
        volume_layout.addWidget(self.volume_max_spin)
        form_layout.addRow("成交量范围:", volume_layout)

        # 日期范围
        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.dateChanged.connect(self._on_filter_changed)
        date_layout.addWidget(self.start_date)

        date_layout.addWidget(QLabel("至"))

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self._on_filter_changed)
        date_layout.addWidget(self.end_date)
        form_layout.addRow("日期范围:", date_layout)

        layout.addLayout(form_layout)
        layout.addStretch()

        return widget

    def _create_technical_filter_tab(self):
        """创建技术指标筛选标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 指标选择区域
        indicator_group = QGroupBox("指标筛选条件")
        indicator_layout = QVBoxLayout(indicator_group)

        # 创建紧凑的指标条件表格
        self.indicator_table = QTableWidget(0, 6)
        self.indicator_table.setHorizontalHeaderLabels([
            "指标", "比较符", "数值", "逻辑", "启用", "操作"
        ])

        # 设置列宽
        header = self.indicator_table.horizontalHeader()
        header.resizeSection(0, 80)   # 指标
        header.resizeSection(1, 70)   # 比较符
        header.resizeSection(2, 80)   # 数值
        header.resizeSection(3, 60)   # 逻辑
        header.resizeSection(4, 50)   # 启用
        header.resizeSection(5, 60)   # 操作

        self.indicator_table.setMaximumHeight(200)
        self.indicator_table.setAlternatingRowColors(True)
        indicator_layout.addWidget(self.indicator_table)

        # 添加指标条件按钮
        add_btn_layout = QHBoxLayout()
        add_indicator_btn = QPushButton("➕ 添加指标条件")
        add_indicator_btn.clicked.connect(self._add_indicator_condition)
        add_btn_layout.addWidget(add_indicator_btn)
        add_btn_layout.addStretch()

        clear_indicators_btn = QPushButton("🗑️ 清空条件")
        clear_indicators_btn.clicked.connect(self._clear_indicator_conditions)
        add_btn_layout.addWidget(clear_indicators_btn)

        indicator_layout.addLayout(add_btn_layout)
        layout.addWidget(indicator_group)

        # 信号筛选区域
        signal_group = QGroupBox("信号筛选")
        signal_layout = QFormLayout(signal_group)

        # 信号类型多选
        self.signal_types = QListWidget()
        self.signal_types.setSelectionMode(QAbstractItemView.MultiSelection)
        self.signal_types.setMaximumHeight(100)
        signal_options = ['买入', '卖出', '持有', '超买', '超卖', '中性']
        for signal in signal_options:
            item = QListWidgetItem(signal)
            self.signal_types.addItem(item)
        self.signal_types.itemSelectionChanged.connect(self._on_filter_changed)
        signal_layout.addRow("信号类型:", self.signal_types)

        # 信号强度
        strength_layout = QHBoxLayout()
        self.strength_combo = QComboBox()
        self.strength_combo.addItems(["全部", "强", "中", "弱"])
        self.strength_combo.currentTextChanged.connect(self._on_filter_changed)
        strength_layout.addWidget(self.strength_combo)

        self.min_strength_cb = QCheckBox("最低强度要求")
        strength_layout.addWidget(self.min_strength_cb)
        signal_layout.addRow("信号强度:", strength_layout)

        layout.addWidget(signal_group)
        layout.addStretch()

        return widget

    def _create_advanced_filter_tab(self):
        """创建高级筛选标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 组合条件设置
        combo_group = QGroupBox("组合条件")
        combo_layout = QFormLayout(combo_group)

        # 条件组合逻辑
        logic_layout = QHBoxLayout()
        self.logic_combo = QComboBox()
        self.logic_combo.addItems(["AND (同时满足)", "OR (满足任一)", "NOT (排除条件)"])
        logic_layout.addWidget(self.logic_combo)
        combo_layout.addRow("条件逻辑:", logic_layout)

        # 自定义表达式
        self.custom_expr_edit = QLineEdit()
        self.custom_expr_edit.setPlaceholderText("如: (RSI > 70 AND MACD > 0) OR Volume > 1000000")
        combo_layout.addRow("自定义表达式:", self.custom_expr_edit)

        layout.addWidget(combo_group)

        # 排序设置
        sort_group = QGroupBox("结果排序")
        sort_layout = QFormLayout(sort_group)

        self.sort_column_combo = QComboBox()
        self.sort_column_combo.addItems(list(self.columns_config.keys()))
        sort_layout.addRow("排序字段:", self.sort_column_combo)

        sort_order_layout = QHBoxLayout()
        self.sort_asc_radio = QCheckBox("升序")
        self.sort_desc_radio = QCheckBox("降序")
        self.sort_desc_radio.setChecked(True)
        sort_order_layout.addWidget(self.sort_asc_radio)
        sort_order_layout.addWidget(self.sort_desc_radio)
        sort_layout.addRow("排序方式:", sort_order_layout)

        # 结果限制
        self.limit_results_cb = QCheckBox("限制结果数量")
        self.limit_count_spin = QSpinBox()
        self.limit_count_spin.setRange(10, 10000)
        self.limit_count_spin.setValue(1000)
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(self.limit_results_cb)
        limit_layout.addWidget(self.limit_count_spin)
        sort_layout.addRow("结果限制:", limit_layout)

        layout.addWidget(sort_group)
        layout.addStretch()

        return widget

    def _create_preview_panel(self):
        """创建预览面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 预览标题
        preview_label = QLabel("筛选预览")
        preview_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #495057;")
        layout.addWidget(preview_label)

        # 统计信息
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.StyledPanel)
        stats_frame.setMaximumHeight(60)
        stats_layout = QGridLayout(stats_frame)

        self.total_count_label = QLabel("总数: 0")
        self.matched_count_label = QLabel("匹配: 0")
        self.filtered_percent_label = QLabel("过滤率: 0%")

        stats_layout.addWidget(QLabel("统计信息:"), 0, 0)
        stats_layout.addWidget(self.total_count_label, 0, 1)
        stats_layout.addWidget(self.matched_count_label, 1, 0)
        stats_layout.addWidget(self.filtered_percent_label, 1, 1)

        layout.addWidget(stats_frame)

        # 预览表格
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMaximumHeight(400)
        layout.addWidget(self.preview_table)

        # 预览进度条
        self.preview_progress = QProgressBar()
        self.preview_progress.setVisible(False)
        self.preview_progress.setMaximumHeight(4)
        layout.addWidget(self.preview_progress)

        return panel

    def _create_button_bar(self, parent_layout):
        """创建底部按钮栏"""
        button_frame = QFrame()
        button_frame.setFrameStyle(QFrame.StyledPanel)
        button_frame.setMaximumHeight(50)
        parent_layout.addWidget(button_frame)

        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(12, 8, 12, 8)

        # 左侧：重置和帮助按钮
        reset_btn = QPushButton("🔄 重置")
        reset_btn.setToolTip("重置所有筛选条件")
        reset_btn.clicked.connect(self._reset_filters)
        button_layout.addWidget(reset_btn)

        help_btn = QPushButton("❓ 帮助")
        help_btn.setToolTip("查看筛选条件设置帮助")
        help_btn.clicked.connect(self._show_help)
        button_layout.addWidget(help_btn)

        button_layout.addStretch()

        # 右侧：确定和取消按钮
        self.apply_btn = QPushButton("✅ 应用筛选")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.apply_btn.clicked.connect(self._apply_filters)
        button_layout.addWidget(self.apply_btn)

        cancel_btn = QPushButton("❌ 取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

    def _setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
                padding: 8px;
            }
            QTabBar::tab {
                background-color: #e9ecef;
                border: 1px solid #dee2e6;
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                background-color: white;
            }
            QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #dee2e6;
                selection-background-color: #e3f2fd;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #007bff;
                outline: none;
            }
        """)

    # 事件处理方法
    def _on_filter_changed(self):
        """筛选条件发生变化"""
        if self.preview_checkbox.isChecked():
            # 延迟更新预览，避免频繁刷新
            self.preview_timer.start(300)

    def _toggle_preview(self, enabled):
        """切换预览开关"""
        if enabled:
            self._update_preview()
        else:
            self.preview_table.setRowCount(0)
            self.preview_label.setText("匹配结果: - 条 (预览已关闭)")

    def _update_preview(self):
        """更新预览结果"""
        try:
            self.preview_progress.setVisible(True)
            filters = self._collect_filter_conditions()
            self.preview_requested.emit(filters)
        except Exception as e:
            logger.error(f"更新预览失败: {e}")
        finally:
            self.preview_progress.setVisible(False)

    def _collect_filter_conditions(self):
        """收集所有筛选条件"""
        conditions = {}

        # 基础筛选条件
        if self.code_edit.text().strip():
            conditions['stock_code'] = {
                'value': self.code_edit.text().strip(),
                'exclude': self.code_exclude_cb.isChecked()
            }

        if self.name_edit.text().strip():
            conditions['stock_name'] = {
                'value': self.name_edit.text().strip(),
                'exclude': self.name_exclude_cb.isChecked()
            }

        # 数值范围条件
        conditions['change_range'] = {
            'min': self.change_min_spin.value(),
            'max': self.change_max_spin.value()
        }

        conditions['volume_range'] = {
            'min': self.volume_min_spin.value() * 10000,  # 转换为实际数值
            'max': self.volume_max_spin.value() * 10000
        }

        # 日期范围
        conditions['date_range'] = {
            'start': self.start_date.date().toPyDate(),
            'end': self.end_date.date().toPyDate()
        }

        # 技术指标条件
        indicator_conditions = []
        for row in range(self.indicator_table.rowCount()):
            enabled_item = self.indicator_table.cellWidget(row, 4)
            if enabled_item and enabled_item.isChecked():
                condition = {
                    'indicator': self.indicator_table.item(row, 0).text(),
                    'operator': self.indicator_table.item(row, 1).text(),
                    'value': float(self.indicator_table.item(row, 2).text()),
                    'logic': self.indicator_table.item(row, 3).text()
                }
                indicator_conditions.append(condition)
        conditions['indicators'] = indicator_conditions

        # 信号筛选条件
        selected_signals = [item.text() for item in self.signal_types.selectedItems()]
        if selected_signals:
            conditions['signals'] = selected_signals

        if self.strength_combo.currentText() != "全部":
            conditions['signal_strength'] = self.strength_combo.currentText()

        return conditions

    def _add_indicator_condition(self):
        """添加指标条件"""
        row = self.indicator_table.rowCount()
        self.indicator_table.insertRow(row)

        # 指标选择
        indicator_combo = QComboBox()
        indicator_combo.addItems(self.columns_config['指标名称']['options'])
        self.indicator_table.setCellWidget(row, 0, indicator_combo)

        # 比较符
        operator_combo = QComboBox()
        operator_combo.addItems(['>', '>=', '<', '<=', '=', '!='])
        self.indicator_table.setCellWidget(row, 1, operator_combo)

        # 数值输入
        value_spin = QDoubleSpinBox()
        value_spin.setRange(-999999, 999999)
        value_spin.setDecimals(2)
        self.indicator_table.setCellWidget(row, 2, value_spin)

        # 逻辑连接
        logic_combo = QComboBox()
        logic_combo.addItems(['AND', 'OR'])
        self.indicator_table.setCellWidget(row, 3, logic_combo)

        # 启用复选框
        enable_cb = QCheckBox()
        enable_cb.setChecked(True)
        self.indicator_table.setCellWidget(row, 4, enable_cb)

        # 删除按钮
        delete_btn = QPushButton("🗑️")
        delete_btn.setMaximumSize(30, 25)
        delete_btn.clicked.connect(lambda: self._remove_indicator_condition(row))
        self.indicator_table.setCellWidget(row, 5, delete_btn)

    def _remove_indicator_condition(self, row):
        """删除指标条件"""
        self.indicator_table.removeRow(row)

    def _clear_indicator_conditions(self):
        """清空所有指标条件"""
        self.indicator_table.setRowCount(0)

    def _load_quick_filters(self):
        """加载快速筛选方案"""
        quick_filters = [
            "自定义筛选",
            "强势股票 (RSI>70 AND 涨跌幅>5%)",
            "超跌反弹 (RSI<30 AND 涨跌幅<-3%)",
            "放量突破 (成交量>平均2倍 AND 涨跌幅>3%)",
            "技术买入 (MACD金叉 AND RSI>50)",
            "价值低估 (PE<15 AND PB<2)",
            "成长性股票 (营收增长>20% AND 净利增长>15%)"
        ]
        self.quick_filter_combo.addItems(quick_filters)

    def _apply_quick_filter(self, filter_name):
        """应用快速筛选方案"""
        if filter_name == "自定义筛选":
            return

        # 这里可以根据不同的快速筛选方案设置对应的筛选条件
        # 实际实现中可以从配置文件或数据库中加载预设方案
        pass

    def _save_filter_scheme(self):
        """保存筛选方案"""
        # 实现保存当前筛选条件为快速方案
        pass

    def _reset_filters(self):
        """重置所有筛选条件"""
        # 重置基础筛选
        self.code_edit.clear()
        self.name_edit.clear()
        self.code_exclude_cb.setChecked(False)
        self.name_exclude_cb.setChecked(False)

        # 重置数值范围
        self.change_min_spin.setValue(0)
        self.change_max_spin.setValue(10)
        self.volume_min_spin.setValue(0)
        self.volume_max_spin.setValue(100000)

        # 重置日期
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())

        # 清空指标条件
        self.indicator_table.setRowCount(0)

        # 重置信号筛选
        self.signal_types.clearSelection()
        self.strength_combo.setCurrentText("全部")

        # 更新预览
        if self.preview_checkbox.isChecked():
            self._update_preview()

    def _show_help(self):
        """显示帮助信息"""
        help_text = """
        <h3>高级筛选器使用说明</h3>
        
        <h4>📊 基础筛选</h4>
        <ul>
        <li><b>股票代码:</b> 支持通配符 * 和多个代码用逗号分隔</li>
        <li><b>股票名称:</b> 支持关键词模糊匹配</li>
        <li><b>涨跌幅:</b> 设置百分比范围</li>
        <li><b>成交量:</b> 单位为万股</li>
        </ul>
        
        <h4>📈 技术指标</h4>
        <ul>
        <li>点击"添加指标条件"创建技术指标筛选规则</li>
        <li>支持多个条件组合，可选择AND/OR逻辑</li>
        <li>取消"启用"复选框可临时禁用某条件</li>
        </ul>
        
        <h4>⚙️ 高级条件</h4>
        <ul>
        <li><b>条件逻辑:</b> 设置多个筛选组之间的逻辑关系</li>
        <li><b>自定义表达式:</b> 支持复杂的条件表达式</li>
        <li><b>结果排序:</b> 按指定字段排序筛选结果</li>
        </ul>
        
        <h4>💡 使用技巧</h4>
        <ul>
        <li>开启"实时预览"可即时查看筛选结果</li>
        <li>使用快速筛选可应用预设的常用筛选方案</li>
        <li>保存筛选方案可重复使用复杂的筛选条件</li>
        </ul>
        """

        QMessageBox.information(self, "筛选器帮助", help_text)

    def _apply_filters(self):
        """应用筛选条件"""
        try:
            filters = self._collect_filter_conditions()
            self.filters_applied.emit(filters)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"应用筛选条件时出错:\n{e}")

    def update_preview_data(self, total_count, matched_count, sample_data):
        """更新预览数据"""
        self.total_count_label.setText(f"总数: {total_count}")
        self.matched_count_label.setText(f"匹配: {matched_count}")

        if total_count > 0:
            percent = (matched_count / total_count) * 100
            self.filtered_percent_label.setText(f"过滤率: {percent:.1f}%")
        else:
            self.filtered_percent_label.setText("过滤率: 0%")

        self.preview_label.setText(f"匹配结果: {matched_count} 条")

        # 更新预览表格
        if sample_data and len(sample_data) > 0:
            df = sample_data.head(50)  # 只显示前50条
            self.preview_table.setRowCount(len(df))
            self.preview_table.setColumnCount(len(df.columns))
            self.preview_table.setHorizontalHeaderLabels(list(df.columns))

            for i, row in enumerate(df.itertuples()):
                for j, value in enumerate(row[1:]):  # 跳过索引
                    item = QTableWidgetItem(str(value))
                    self.preview_table.setItem(i, j, item)

            self.preview_table.resizeColumnsToContents()
        else:
            self.preview_table.setRowCount(0)

    def get_active_filters(self):
        """获取当前激活的筛选条件"""
        try:
            return self._collect_filter_conditions()
        except Exception as e:
            logger.error(f"获取筛选条件失败: {e}")
            return {}

    def get_activate_filters(self):
        """兼容旧方法名，重定向到get_active_filters"""
        return self.get_active_filters()
