import os
import json
from typing import Dict, List, Any
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QPushButton, QLineEdit, QLabel, QMessageBox, QFileDialog, QInputDialog)
from PyQt5.QtCore import Qt
from datetime import datetime


class TemplateManager:
    """
    通用模板管理器，支持批量保存、加载、删除、导入、导出参数模板。
    模板以JSON文件存储，每个模板为一个字典。
    """

    def __init__(self, template_dir: str):
        self.template_dir = template_dir
        os.makedirs(template_dir, exist_ok=True)

    def list_templates(self) -> List[str]:
        """列出所有模板名称"""
        return [f[:-5] for f in os.listdir(self.template_dir) if f.endswith('.json')]

    def save_template(self, name: str, params: Dict[str, Any]):
        """保存单个模板"""
        path = os.path.join(self.template_dir, f"{name}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=4)

    def load_template(self, name: str) -> Dict[str, Any]:
        """加载单个模板"""
        path = os.path.join(self.template_dir, f"{name}.json")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_templates(self, names: List[str]):
        """批量删除模板"""
        for name in names:
            path = os.path.join(self.template_dir, f"{name}.json")
            if os.path.exists(path):
                os.remove(path)

    def import_templates(self, file_list: List[str]):
        """批量导入模板（从外部json文件）"""
        for file_path in file_list:
            with open(file_path, 'r', encoding='utf-8') as f:
                params = json.load(f)
            name = os.path.splitext(os.path.basename(file_path))[0]
            self.save_template(name, params)

    def export_templates(self, names: List[str], export_dir: str):
        """批量导出模板到指定目录"""
        os.makedirs(export_dir, exist_ok=True)
        for name in names:
            src = os.path.join(self.template_dir, f"{name}.json")
            dst = os.path.join(export_dir, f"{name}.json")
            if os.path.exists(src):
                with open(src, 'r', encoding='utf-8') as fsrc, open(dst, 'w', encoding='utf-8') as fdst:
                    fdst.write(fsrc.read())


class TemplateManagerDialog(QDialog):
    """
    市场情绪模板管理对话框，支持模板的保存、加载、删除、重命名、导入、导出。
    模板数据以JSON格式保存在指定目录。
    """

    def __init__(self, template_dir: str, log_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模板管理")
        self.setMinimumSize(420, 320)
        self.template_dir = template_dir
        self.log_manager = log_manager
        os.makedirs(self.template_dir, exist_ok=True)
        self.templates: List[Dict] = []
        self.current_template = None
        self.init_ui()
        self.load_templates()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("模板列表："))
        layout.addWidget(self.list_widget)

        # 按钮区
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("新建")
        self.rename_btn = QPushButton("重命名")
        self.delete_btn = QPushButton("删除")
        self.import_btn = QPushButton("导入")
        self.export_btn = QPushButton("导出")
        self.apply_btn = QPushButton("应用")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.rename_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.apply_btn)
        layout.addLayout(btn_layout)

        # 事件绑定
        self.add_btn.clicked.connect(self.add_template)
        self.rename_btn.clicked.connect(self.rename_template)
        self.delete_btn.clicked.connect(self.delete_template)
        self.import_btn.clicked.connect(self.import_template)
        self.export_btn.clicked.connect(self.export_template)
        self.apply_btn.clicked.connect(self.apply_template)
        self.list_widget.itemDoubleClicked.connect(self.apply_template)

    def load_templates(self):
        self.list_widget.clear()
        self.templates = []
        for fname in os.listdir(self.template_dir):
            if fname.endswith('.json'):
                path = os.path.join(self.template_dir, fname)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.templates.append(data)
                        self.list_widget.addItem(data.get('name', fname[:-5]))
                except Exception as e:
                    if self.log_manager:
                        self.log_manager.error(f"加载模板失败: {fname}: {str(e)}")
        if self.log_manager:
            self.log_manager.info(f"共加载{len(self.templates)}个模板")

    def add_template(self):
        name, ok = QInputDialog.getText(self, "新建模板", "请输入模板名称：")
        if not ok or not name:
            return
        template = {
            "name": name,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "params": {}
        }
        path = os.path.join(self.template_dir, f"{name}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        self.log_manager and self.log_manager.info(f"新建模板: {name}")
        self.load_templates()

    def rename_template(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择要重命名的模板")
            return
        old_name = item.text()
        new_name, ok = QInputDialog.getText(
            self, "重命名模板", f"将模板\"{old_name}\"重命名为：")
        if not ok or not new_name or new_name == old_name:
            return
        old_path = os.path.join(self.template_dir, f"{old_name}.json")
        new_path = os.path.join(self.template_dir, f"{new_name}.json")
        if os.path.exists(new_path):
            QMessageBox.warning(self, "提示", "新名称已存在")
            return
        os.rename(old_path, new_path)
        self.log_manager and self.log_manager.info(
            f"模板重命名: {old_name} -> {new_name}")
        self.load_templates()

    def delete_template(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择要删除的模板")
            return
        name = item.text()
        path = os.path.join(self.template_dir, f"{name}.json")
        if QMessageBox.question(self, "确认删除", f"确定要删除模板\"{name}\"吗？") == QMessageBox.Yes:
            try:
                os.remove(path)
                self.log_manager and self.log_manager.info(f"删除模板: {name}")
                self.load_templates()
            except Exception as e:
                QMessageBox.critical(self, "删除失败", f"删除模板失败: {str(e)}")
                self.log_manager and self.log_manager.error(
                    f"删除模板失败: {name}: {str(e)}")

    def import_template(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入模板", "", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            name = data.get('name', os.path.basename(file_path)[:-5])
            save_path = os.path.join(self.template_dir, f"{name}.json")
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log_manager and self.log_manager.info(f"导入模板: {name}")
            self.load_templates()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入模板失败: {str(e)}")
            self.log_manager and self.log_manager.error(f"导入模板失败: {str(e)}")

    def export_template(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择要导出的模板")
            return
        name = item.text()
        src_path = os.path.join(self.template_dir, f"{name}.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出模板", f"{name}.json", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(src_path, 'r', encoding='utf-8') as fsrc, open(file_path, 'w', encoding='utf-8') as fdst:
                fdst.write(fsrc.read())
            self.log_manager and self.log_manager.info(
                f"导出模板: {name} -> {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出模板失败: {str(e)}")
            self.log_manager and self.log_manager.error(f"导出模板失败: {str(e)}")

    def apply_template(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择要应用的模板")
            return
        name = item.text()
        path = os.path.join(self.template_dir, f"{name}.json")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.current_template = data
            self.log_manager and self.log_manager.info(f"应用模板: {name}")
            QMessageBox.information(self, "应用模板", f"已应用模板：{name}")
            self.accept()  # 关闭对话框并返回
        except Exception as e:
            QMessageBox.critical(self, "应用失败", f"应用模板失败: {str(e)}")
            self.log_manager and self.log_manager.error(f"应用模板失败: {str(e)}")

    def get_current_template(self):
        return self.current_template
