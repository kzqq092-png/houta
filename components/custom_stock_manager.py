import os
import json
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

CUSTOM_STOCKS_FILE = os.path.expanduser("~/.hikyuu_custom_stocks.json")


def load_custom_stocks():
    if os.path.exists(CUSTOM_STOCKS_FILE):
        with open(CUSTOM_STOCKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_custom_stocks(stocks):
    with open(CUSTOM_STOCKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)


class CustomStockManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自选股管理")
        self.setMinimumSize(400, 500)
        self.stocks = load_custom_stocks()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.addItems(self.stocks)
        layout.addWidget(QLabel("自选股代码列表："))
        layout.addWidget(self.list_widget)
        # 添加输入框和按钮
        hbox = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入股票代码")
        hbox.addWidget(self.input_edit)
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self.add_stock)
        hbox.addWidget(btn_add)
        btn_del = QPushButton("删除")
        btn_del.clicked.connect(self.del_stock)
        hbox.addWidget(btn_del)
        layout.addLayout(hbox)
        # 导入导出
        btn_import = QPushButton("导入")
        btn_import.clicked.connect(self.import_stocks)
        btn_export = QPushButton("导出")
        btn_export.clicked.connect(self.export_stocks)
        layout.addWidget(btn_import)
        layout.addWidget(btn_export)
        # 排序
        btn_up = QPushButton("上移")
        btn_up.clicked.connect(self.move_up)
        btn_down = QPushButton("下移")
        btn_down.clicked.connect(self.move_down)
        layout.addWidget(btn_up)
        layout.addWidget(btn_down)
        # 保存
        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

    def add_stock(self):
        code = self.input_edit.text().strip()
        if code and code not in self.stocks:
            self.stocks.append(code)
            self.list_widget.addItem(code)
            self.input_edit.clear()

    def del_stock(self):
        items = self.list_widget.selectedItems()
        for item in items:
            code = item.text()
            self.stocks.remove(code)
            self.list_widget.takeItem(self.list_widget.row(item))

    def import_stocks(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入自选股", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                codes = [line.strip() for line in f if line.strip()]
                for code in codes:
                    if code not in self.stocks:
                        self.stocks.append(code)
                        self.list_widget.addItem(code)

    def export_stocks(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出自选股", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                for code in self.stocks:
                    f.write(code + '\n')
            QMessageBox.information(self, "导出成功", "自选股已导出")

    def move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            self.stocks[row], self.stocks[row -
                                          1] = self.stocks[row-1], self.stocks[row]
            self.list_widget.clear()
            self.list_widget.addItems(self.stocks)
            self.list_widget.setCurrentRow(row-1)

    def move_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.stocks)-1:
            self.stocks[row], self.stocks[row +
                                          1] = self.stocks[row+1], self.stocks[row]
            self.list_widget.clear()
            self.list_widget.addItems(self.stocks)
            self.list_widget.setCurrentRow(row+1)

    def save(self):
        save_custom_stocks(self.stocks)
        QMessageBox.information(self, "保存成功", "自选股已保存")
        self.accept()
