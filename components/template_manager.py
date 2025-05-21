import os
import json
from typing import Dict, List, Any


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
