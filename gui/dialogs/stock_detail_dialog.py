"""
股票详情对话框模块
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import traceback
from gui.widgets.log_widget import LogWidget
import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'settings.json')


class ColumnSelectorDialog(QDialog):
    """表格样式动态勾选列对话框，支持字段筛选，5列紧凑排列，仿图片风格"""

    def __init__(self, all_fields, selected_fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择要显示的财务字段")
        self.selected_fields = set(selected_fields)
        self.all_fields = all_fields
        self.filtered_fields = all_fields.copy()
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["", "", "", "", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet('''
            QTableWidget {border: 0.5px solid #b0b0b0;  background: #fff; font-size: 8px;}
            QHeaderView::section {background: #444; color: #fff; height: 15px; padding-left: 2px;}
            QTableWidget::item {border: 0.5px solid #b0b0b0; background: #fff;}
            QTableWidget::item:selected {background: #e3f2fd; color: #1976d2;}
            QTableWidget::item:hover {background: #f5f5f5;}
        ''')
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("筛选字段名...")
        self.search_edit.textChanged.connect(self.apply_filter)
        btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.deselect_all_btn = QPushButton("全不选")
        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        btn_layout.addWidget(self.select_all_btn)
        btn_layout.addWidget(self.deselect_all_btn)
        btn_layout.addStretch()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.search_edit)
        main_layout.addWidget(self.table)
        main_layout.addLayout(btn_layout)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        main_layout.addWidget(ok_btn, alignment=Qt.AlignRight)
        self.refresh_table()

    def refresh_table(self):
        # 5列紧凑排列
        fields = self.filtered_fields
        n = len(fields)
        cols = 5
        rows = (n + cols - 1) // cols
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        for i in range(rows * cols):
            row, col = divmod(i, cols)
            if i < n:
                field = fields[i]
                cb = QCheckBox()
                cb.setChecked(field['key'] in self.selected_fields)
                cb.field_key = field['key']
                cb.stateChanged.connect(self.on_checkbox_changed)
                w = QWidget()
                layout = QHBoxLayout(w)
                layout.setContentsMargins(0, 2, 0, 2)
                layout.setSpacing(0)
                layout.addWidget(cb)
                label = QLabel(field['field'])
                label.setFixedWidth(230)
                label.setStyleSheet("font-size:13px;")
                label.setAlignment(Qt.AlignCenter)
                layout.addWidget(label)
                layout.addStretch()
                w.setLayout(layout)
                self.table.setCellWidget(row, col, w)
                self.table.setRowHeight(row, 18)
            else:
                self.table.setCellWidget(row, col, QWidget())
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def on_checkbox_changed(self, state):
        # 更新选中字段
        self.selected_fields = set()
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                w = self.table.cellWidget(row, col)
                if w:
                    cb = w.findChild(QCheckBox)
                    if cb and cb.isChecked():
                        self.selected_fields.add(cb.field_key)

    def get_selected_keys(self):
        return list(self.selected_fields)

    def select_all(self):
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                w = self.table.cellWidget(row, col)
                if w:
                    cb = w.findChild(QCheckBox)
                    if cb:
                        cb.setChecked(True)
        self.on_checkbox_changed(None)

    def deselect_all(self):
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                w = self.table.cellWidget(row, col)
                if w:
                    cb = w.findChild(QCheckBox)
                    if cb:
                        cb.setChecked(False)
        self.on_checkbox_changed(None)

    def apply_filter(self, text):
        text = text.strip()
        if not text:
            self.filtered_fields = self.all_fields.copy()
        else:
            self.filtered_fields = [
                f for f in self.all_fields if text in f['field'] or text in f['key']]
        self.refresh_table()

# 辅助函数：读写settings.json


def load_selected_fields():
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        return settings.get('finance_selected_fields', None)
    except Exception:
        return None


def save_selected_fields(selected_fields):
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            settings = {}
        settings['finance_selected_fields'] = selected_fields
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class StockDetailDialog(QDialog):
    """股票详情对话框"""

    def __init__(self, stock_data: Dict[str, Any], parent=None):
        """初始化股票详情对话框

        Args:
            stock_data: 股票数据字典
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("股票详情")
        self.setMinimumSize(700, 500)
        self.stock_data = stock_data
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)
        # Tab按钮区
        tab_btn_layout = QHBoxLayout()
        tab_btn_layout.setContentsMargins(0, 0, 0, 0)
        tab_btn_layout.setSpacing(0)
        self.tab_buttons = []
        tab_names = ["基本信息", "财务数据", "历史数据"]
        for i, name in enumerate(tab_names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setAutoExclusive(False)
            btn.setFixedHeight(32)
            btn.setMinimumWidth(110)
            btn.clicked.connect(lambda _, idx=i: self.switch_tab(idx))
            self.tab_buttons.append(btn)
            tab_btn_layout.addWidget(btn)
        tab_btn_widget = QWidget()
        tab_btn_widget.setLayout(tab_btn_layout)
        tab_btn_widget.setStyleSheet('''
QWidget {background: #fff; border-radius: 2px 2px 0 0; padding: 0; margin: 0;}
QPushButton {background: #e3f2fd; border: none; border-radius: 2px 2px 0 0; padding: 6px 16px; margin-right: 2px; font-weight: bold; color: #1976d2;}
QPushButton:checked {background: #1976d2; color: #fff;}
''')
        main_layout.addWidget(tab_btn_widget)
        # 内容区
        self.stacked = QStackedWidget(self)
        self.stacked.addWidget(self.create_basic_info_tab())
        self.stacked.addWidget(self.create_financial_tab())
        self.stacked.addWidget(self.create_history_tab())
        main_layout.addWidget(self.stacked)
        self.tab_buttons[0].setChecked(True)
        self.stacked.setCurrentIndex(0)
        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        export_btn = QPushButton("导出数据")
        export_btn.setFixedHeight(28)
        export_btn.clicked.connect(self.export_data)
        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(28)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)
        self.show()
        LogWidget().center_dialog(self, parent)

    def switch_tab(self, idx: int):
        self.stacked.setCurrentIndex(idx)
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == idx)

    def _set_table_readonly_style(self, table: QTableWidget):
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

    def create_basic_info_tab(self) -> QWidget:
        """创建基本信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        table = QTableWidget()
        table.setColumnCount(2)
        table.setRowCount(8)
        table.setHorizontalHeaderLabels(["项目", "值"])
        table.horizontalHeader().setFixedHeight(36)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setContentsMargins(0, 0, 0, 0)
        table.setStyleSheet('''
QTableWidget {border: 1px solid #e0e0e0; border-radius: 2px; background: #fff;}
QHeaderView::section {background: #e3f2fd; color: #1976d2; font-weight: bold; border: none; border-radius: 2px 2px 0 0; height: 36px; padding-left: 8px;}
QTableWidget::item {border: none; background: #fff;}
''')
        basic_info = [
            ("股票代码", self.stock_data['code']),
            ("股票名称", self.stock_data['name']),
            ("所属市场", self.stock_data['market']),
            ("所属行业", self.stock_data.get('industry', '未知')),
            ("上市日期", self.stock_data.get('list_date', '未知')),
            ("总股本", f"{self.stock_data.get('total_shares', 0):,.0f}"),
            ("流通股本", f"{self.stock_data.get('circulating_shares', 0):,.0f}"),
            ("最新价格", f"{self.stock_data.get('price', 0):,.2f}")
        ]
        for row, (label, value) in enumerate(basic_info):
            table.setItem(row, 0, QTableWidgetItem(label))
            table.setItem(row, 1, QTableWidgetItem(str(value)))
        self._set_table_readonly_style(table)
        layout.addWidget(table)
        return widget

    def create_financial_tab(self) -> QWidget:
        """创建财务数据标签页，支持多期历史财务数据和动态勾选列（表格筛选版）"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            finance_history = self.stock_data.get('finance_history', [])
            all_fields = self.stock_data.get('all_fields', [])
            # 默认主流字段key
            default_keys = [f['key'] for f in all_fields if f['key'] in (
                'date', 'revenue', 'net_profit', 'roe', 'assets', 'liabilities', 'profit_margin', 'debt_to_equity', 'operating_cash_flow', 'equity')]
            # 读取用户上次勾选
            selected_keys = load_selected_fields() or default_keys
            # 生成表头
            headers = [f['field']
                       for f in all_fields if f['key'] in selected_keys]
            keys = [f['key'] for f in all_fields if f['key'] in selected_keys]
            table = QTableWidget()
            table.setColumnCount(len(keys))
            table.setRowCount(len(finance_history))
            table.setHorizontalHeaderLabels(headers)
            table.horizontalHeader().setFixedHeight(28)
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)
            table.setContentsMargins(0, 0, 0, 0)
            table.setStyleSheet('''
QTableWidget {border: 1px solid #e0e0e0; border-radius: 2px; background: #fff;}
QHeaderView::section {background: #e3f2fd; color: #1976d2; font-weight: bold; border: none; border-radius: 2px 2px 0 0; height: 28px; padding-left: 4px;}
QTableWidget::item {border: 1px solid #e0e0e0; background: #fff;}
''')
            for row, item in enumerate(finance_history):
                for col, key in enumerate(keys):
                    val = item.get(key, None)
                    # None、空、nan等统一显示为'-'
                    if val is None or val == '' or (isinstance(val, float) and (pd.isna(val) or str(val) == 'nan')):
                        val_str = '-'
                    elif isinstance(val, (int, float)):
                        val_str = f"{val:.2f}"
                    else:
                        val_str = str(val)
                    table.setItem(row, col, QTableWidgetItem(val_str))
            self._set_table_readonly_style(table)
            layout.addWidget(table)
            # 增加"选择列"按钮
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_select = QPushButton("选择列")
            btn_select.setFixedHeight(24)

            def on_select_columns():
                dialog = ColumnSelectorDialog(all_fields, selected_keys, self)
                if dialog.exec_():
                    new_keys = dialog.get_selected_keys()
                    if new_keys:
                        save_selected_fields(new_keys)
                        # 刷新表格
                        table.setColumnCount(len(new_keys))
                        table.setHorizontalHeaderLabels(
                            [f['field'] for f in all_fields if f['key'] in new_keys])
                        for row, item in enumerate(finance_history):
                            for col, key in enumerate(new_keys):
                                val = item.get(key, None)
                                if val is None or val == '' or (isinstance(val, float) and (pd.isna(val) or str(val) == 'nan')):
                                    val_str = '-'
                                elif isinstance(val, (int, float)):
                                    val_str = f"{val:.2f}"
                                else:
                                    val_str = str(val)
                                table.setItem(
                                    row, col, QTableWidgetItem(val_str))
            btn_select.clicked.connect(on_select_columns)
            btn_layout.addWidget(btn_select)
            layout.addLayout(btn_layout)
            return widget
        except Exception as e:
            print(f"创建财务数据标签页失败: {str(e)}")
            print(traceback.format_exc())
            raise

    def create_history_tab(self) -> QWidget:
        """创建历史数据标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        history = self.stock_data.get('history', [])
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["日期", "开盘", "最高", "最低", "收盘", "成交量"])
        table.setRowCount(len(history))
        table.horizontalHeader().setFixedHeight(36)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setContentsMargins(0, 0, 0, 0)
        table.setStyleSheet('''
QTableWidget {border: 1px solid #e0e0e0; border-radius: 2px; background: #fff;}
QHeaderView::section {background: #e3f2fd; color: #1976d2; font-weight: bold; border: none; border-radius: 2px 2px 0 0; height: 36px; padding-left: 2px;}
QTableWidget::item {border: none; background: #fff;}
''')
        for row, item in enumerate(history):
            table.setItem(row, 0, QTableWidgetItem(item.get('date', '')))
            # 数值字段保留2位小数
            for col, key in enumerate(["open", "high", "low", "close", "volume"], start=1):
                val = item.get(key, '')
                if isinstance(val, (int, float)):
                    val_str = f"{val:.2f}"
                else:
                    val_str = str(val)
                table.setItem(row, col, QTableWidgetItem(val_str))
        self._set_table_readonly_style(table)
        layout.addWidget(table)
        return widget

    def export_data(self):
        """导出股票数据"""
        try:
            # 创建DataFrame
            data = {
                '基本信息': pd.DataFrame([
                    {'项目': '股票代码', '值': self.stock_data['code']},
                    {'项目': '股票名称', '值': self.stock_data['name']},
                    {'项目': '所属市场', '值': self.stock_data['market']},
                    {'项目': '所属行业', '值': self.stock_data.get('industry', '未知')},
                    {'项目': '上市日期', '值': self.stock_data.get(
                        'list_date', '未知')},
                    {'项目': '总股本', '值': self.stock_data.get('total_shares', 0)},
                    {'项目': '流通股本', '值': self.stock_data.get(
                        'circulating_shares', 0)},
                    {'项目': '最新价格', '值': self.stock_data.get('price', 0)}
                ]),
                '财务数据': pd.DataFrame([
                    {'项目': '营业收入', '最新': self.stock_data.get('revenue', 0),
                     '同比': self.stock_data.get('revenue_yoy', 0),
                     '环比': self.stock_data.get('revenue_qoq', 0)},
                    # ... 其他财务数据
                ]),
                '历史数据': pd.DataFrame(self.stock_data.get('history', []))
            }

            # 导出到Excel
            filename = f"stock_{self.stock_data['code']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            with pd.ExcelWriter(filename) as writer:
                for sheet_name, df in data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            print(f"数据已导出到: {filename}")

        except Exception as e:
            print(f"导出数据失败: {str(e)}")
            print(traceback.format_exc())
