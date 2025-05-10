"""
股票详情对话框模块
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QTabWidget, QWidget, QScrollArea)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import traceback


class StockDetailDialog(QDialog):
    """股票详情对话框"""

    def __init__(self, stock_data: Dict[str, Any], parent=None):
        """初始化股票详情对话框

        Args:
            stock_data: 股票数据字典
            parent: 父窗口
        """
        super().__init__(parent)
        self.stock_data = stock_data
        self.setWindowTitle(
            f"股票详情 - {stock_data['name']} ({stock_data['code']})")
        self.setMinimumSize(800, 600)

        try:
            # 创建主布局
            layout = QVBoxLayout(self)

            # 创建标签页
            self.tab_widget = QTabWidget()

            # 基本信息标签页
            self.basic_info_tab = self.create_basic_info_tab()
            self.tab_widget.addTab(self.basic_info_tab, "基本信息")

            # 财务数据标签页
            self.financial_tab = self.create_financial_tab()
            self.tab_widget.addTab(self.financial_tab, "财务数据")

            # 历史数据标签页
            self.history_tab = self.create_history_tab()
            self.tab_widget.addTab(self.history_tab, "历史数据")

            # 添加标签页到布局
            layout.addWidget(self.tab_widget)

            # 添加按钮
            button_layout = QHBoxLayout()
            close_button = QPushButton("关闭")
            close_button.clicked.connect(self.close)
            export_button = QPushButton("导出数据")
            export_button.clicked.connect(self.export_data)
            button_layout.addWidget(export_button)
            button_layout.addWidget(close_button)
            layout.addLayout(button_layout)

            # 显示对话框并居中
            self.show()
            self.center_dialog(self, parent)

        except Exception as e:
            print(f"创建股票详情对话框失败: {str(e)}")
            print(traceback.format_exc())
            raise

    def create_basic_info_tab(self) -> QWidget:
        """创建基本信息标签页"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建表格
            table = QTableWidget()
            table.setColumnCount(2)
            table.setRowCount(8)
            table.setHorizontalHeaderLabels(["项目", "值"])
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)

            # 填充数据
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

            layout.addWidget(table)
            return widget

        except Exception as e:
            print(f"创建基本信息标签页失败: {str(e)}")
            print(traceback.format_exc())
            raise

    def create_financial_tab(self) -> QWidget:
        """创建财务数据标签页"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建表格
            table = QTableWidget()
            table.setColumnCount(4)
            table.setRowCount(10)
            table.setHorizontalHeaderLabels(["项目", "最新", "同比", "环比"])
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)

            # 填充数据
            financial_data = [
                ("营业收入", "revenue", "revenue_yoy", "revenue_qoq"),
                ("净利润", "net_profit", "net_profit_yoy", "net_profit_qoq"),
                ("毛利率", "gross_margin", "gross_margin_yoy", "gross_margin_qoq"),
                ("净利率", "net_margin", "net_margin_yoy", "net_margin_qoq"),
                ("ROE", "roe", "roe_yoy", "roe_qoq"),
                ("资产负债率", "debt_ratio", "debt_ratio_yoy", "debt_ratio_qoq"),
                ("每股收益", "eps", "eps_yoy", "eps_qoq"),
                ("每股净资产", "bps", "bps_yoy", "bps_qoq"),
                ("每股现金流", "cfps", "cfps_yoy", "cfps_qoq"),
                ("股息率", "dividend_yield", "dividend_yield_yoy", "dividend_yield_qoq")
            ]

            for row, (label, *fields) in enumerate(financial_data):
                table.setItem(row, 0, QTableWidgetItem(label))
                for col, field in enumerate(fields, 1):
                    value = self.stock_data.get(field, 0)
                    if isinstance(value, (int, float)):
                        value = f"{value:,.2f}"
                    table.setItem(row, col, QTableWidgetItem(str(value)))

            layout.addWidget(table)
            return widget

        except Exception as e:
            print(f"创建财务数据标签页失败: {str(e)}")
            print(traceback.format_exc())
            raise

    def create_history_tab(self) -> QWidget:
        """创建历史数据标签页"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建表格
            table = QTableWidget()
            table.setColumnCount(6)
            table.setRowCount(20)  # 显示最近20个交易日的数据
            table.setHorizontalHeaderLabels(
                ["日期", "开盘", "最高", "最低", "收盘", "成交量"])
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)

            # 获取历史数据
            history_data = self.stock_data.get('history', [])
            for row, data in enumerate(history_data[:20]):
                table.setItem(row, 0, QTableWidgetItem(data['date']))
                table.setItem(row, 1, QTableWidgetItem(f"{data['open']:,.2f}"))
                table.setItem(row, 2, QTableWidgetItem(f"{data['high']:,.2f}"))
                table.setItem(row, 3, QTableWidgetItem(f"{data['low']:,.2f}"))
                table.setItem(row, 4, QTableWidgetItem(
                    f"{data['close']:,.2f}"))
                table.setItem(row, 5, QTableWidgetItem(
                    f"{data['volume']:,.0f}"))

            layout.addWidget(table)
            return widget

        except Exception as e:
            print(f"创建历史数据标签页失败: {str(e)}")
            print(traceback.format_exc())
            raise

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

    def center_dialog(self, dialog, parent=None, offset_y=50):
        """将弹窗居中到父窗口或屏幕，并尽量靠近上部

        Args:
            dialog: 要居中的对话框
            parent: 父窗口，如果为None则使用屏幕
            offset_y: 距离顶部的偏移量
        """
        try:
            if parent and parent.isVisible():
                # 相对于父窗口居中
                parent_geom = parent.geometry()
                dialog_geom = dialog.frameGeometry()
                x = parent_geom.center().x() - dialog_geom.width() // 2
                y = parent_geom.top() + offset_y

                # 确保弹窗不会超出父窗口边界
                x = max(parent_geom.left(), min(
                    x, parent_geom.right() - dialog_geom.width()))
                y = max(parent_geom.top(), min(
                    y, parent_geom.bottom() - dialog_geom.height()))
            else:
                # 相对于屏幕居中
                screen = dialog.screen() or dialog.parentWidget().screen()
                if screen:
                    screen_geom = screen.geometry()
                    dialog_geom = dialog.frameGeometry()
                    x = screen_geom.center().x() - dialog_geom.width() // 2
                    y = screen_geom.top() + offset_y

                    # 确保弹窗不会超出屏幕边界
                    x = max(screen_geom.left(), min(
                        x, screen_geom.right() - dialog_geom.width()))
                    y = max(screen_geom.top(), min(
                        y, screen_geom.bottom() - dialog_geom.height()))

            dialog.move(x, y)
        except Exception as e:
            print(f"设置弹窗位置失败: {str(e)}")
            print(traceback.format_exc())
