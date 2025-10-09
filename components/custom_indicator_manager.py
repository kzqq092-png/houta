import os
import json
from typing import List, Dict, Any
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QPushButton, QLineEdit, QLabel, QMessageBox, QInputDialog)
from loguru import logger
from PyQt5.QtCore import Qt
from datetime import datetime

class CustomIndicatorManagerDialog(QDialog):
    """
    自定义情绪指标管理对话框，支持添加、编辑、删除自定义指标，数据持久化。
    """

    def __init__(self, indicator_file: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义指标管理")
        self.setMinimumSize(420, 320)
        self.indicator_file = indicator_file
        # log_manager已迁移到Loguru
        self.indicators: List[Dict[str, Any]] = []
        self.init_ui()
        self.load_indicators()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("自定义指标列表："))
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.edit_btn = QPushButton("编辑")
        self.delete_btn = QPushButton("删除")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)

        self.add_btn.clicked.connect(self.add_indicator)
        self.edit_btn.clicked.connect(self.edit_indicator)
        self.delete_btn.clicked.connect(self.delete_indicator)

    def load_indicators(self):
        self.list_widget.clear()
        if os.path.exists(self.indicator_file):
            try:
                with open(self.indicator_file, 'r', encoding='utf-8') as f:
                    self.indicators = json.load(f)
            except Exception as e:
                self.indicators = []
                logger.error(f"加载自定义指标失败: {str(e)}")
        else:
            self.indicators = []
        for ind in self.indicators:
            self.list_widget.addItem(ind.get('name', '未命名'))
        logger.info(f"共加载{len(self.indicators)}个自定义指标")

    def save_indicators(self):
        try:
            with open(self.indicator_file, 'w', encoding='utf-8') as f:
                json.dump(self.indicators, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存{len(self.indicators)}个自定义指标")
        except Exception as e:
            logger.error(f"保存自定义指标失败: {str(e)}")

    def add_indicator(self):
        name, ok = QInputDialog.getText(self, "添加指标", "请输入指标名称：")
        if not ok or not name:
            return
        formula, ok = QInputDialog.getText(self, "添加指标", "请输入指标公式（可选）：")
        if not ok:
            return
        indicator = {
            "name": name,
            "formula": formula,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.indicators.append(indicator)
        self.save_indicators()
        self.load_indicators()
        logger.info(f"添加自定义指标: {name}")

    def edit_indicator(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择要编辑的指标")
            return
        idx = self.list_widget.currentRow()
        ind = self.indicators[idx]
        name, ok = QInputDialog.getText(
            self, "编辑指标", "修改指标名称：", text=ind.get('name', ''))
        if not ok or not name:
            return
        formula, ok = QInputDialog.getText(
            self, "编辑指标", "修改指标公式：", text=ind.get('formula', ''))
        if not ok:
            return
        ind['name'] = name
        ind['formula'] = formula
        self.save_indicators()
        self.load_indicators()
        logger.info(f"编辑自定义指标: {name}")

    def delete_indicator(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择要删除的指标")
            return
        idx = self.list_widget.currentRow()
        name = self.indicators[idx].get('name', '')
        if QMessageBox.question(self, "确认删除", f"确定要删除指标\"{name}\"吗？") == QMessageBox.Yes:
            del self.indicators[idx]
            self.save_indicators()
            self.load_indicators()
            logger.info(f"删除自定义指标: {name}")
