#!/usr/bin/env python3
"""
模板管理器

提供模板的保存、加载、删除等功能
"""

import os
import json
from typing import Dict, List, Any


class TemplateManager:
    """模板管理器类"""

    def __init__(self, template_dir: str = "templates"):
        """初始化模板管理器

        Args:
            template_dir: 模板存储目录
        """
        self.template_dir = template_dir
        self._ensure_template_dir()

    def _ensure_template_dir(self):
        """确保模板目录存在"""
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir, exist_ok=True)

    def save_template(self, name: str, data: Dict[str, Any]) -> bool:
        """保存模板

        Args:
            name: 模板名称
            data: 模板数据

        Returns:
            是否保存成功
        """
        try:
            template_path = os.path.join(self.template_dir, f"{name}.json")
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存模板失败: {str(e)}")
            return False

    def load_template(self, name: str) -> Dict[str, Any]:
        """加载模板

        Args:
            name: 模板名称

        Returns:
            模板数据
        """
        try:
            template_path = os.path.join(self.template_dir, f"{name}.json")
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载模板失败: {str(e)}")
            return {}

    def list_templates(self) -> List[str]:
        """列出所有模板

        Returns:
            模板名称列表
        """
        try:
            if not os.path.exists(self.template_dir):
                return []

            templates = []
            for file in os.listdir(self.template_dir):
                if file.endswith('.json'):
                    templates.append(file[:-5])  # 去掉.json后缀
            return templates
        except Exception as e:
            print(f"列出模板失败: {str(e)}")
            return []

    def delete_templates(self, names: List[str]) -> bool:
        """删除模板

        Args:
            names: 要删除的模板名称列表

        Returns:
            是否删除成功
        """
        try:
            for name in names:
                template_path = os.path.join(self.template_dir, f"{name}.json")
                if os.path.exists(template_path):
                    os.remove(template_path)
            return True
        except Exception as e:
            print(f"删除模板失败: {str(e)}")
            return False

    def import_templates(self, file_paths: List[str]) -> bool:
        """导入模板

        Args:
            file_paths: 模板文件路径列表

        Returns:
            是否导入成功
        """
        try:
            for file_path in file_paths:
                if os.path.exists(file_path) and file_path.endswith('.json'):
                    filename = os.path.basename(file_path)
                    target_path = os.path.join(self.template_dir, filename)

                    # 读取并验证模板文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # 保存到模板目录
                    with open(target_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导入模板失败: {str(e)}")
            return False

    def export_templates(self, names: List[str], target_dir: str) -> bool:
        """导出模板

        Args:
            names: 要导出的模板名称列表
            target_dir: 目标目录

        Returns:
            是否导出成功
        """
        try:
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            for name in names:
                source_path = os.path.join(self.template_dir, f"{name}.json")
                target_path = os.path.join(target_dir, f"{name}.json")

                if os.path.exists(source_path):
                    with open(source_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    with open(target_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出模板失败: {str(e)}")
            return False
