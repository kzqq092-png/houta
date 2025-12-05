from loguru import logger
"""
FactorWeave-Quant  插件开发工具包(SDK)

提供插件开发的便利工具、模板生成器和测试框架。
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import subprocess
import tempfile

from ..plugin_interface import PluginType, PluginCategory, PluginMetadata


class PluginTemplate:
    """插件模板"""

    INDICATOR_TEMPLATE = '''"""
{description}

{plugin_type}插件实现。
"""

import pandas as pd
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget, QFormLayout

from ..plugin_interface import (
    I{plugin_type}Plugin, PluginMetadata, PluginType, PluginCategory,
    plugin_metadata, register_plugin, PluginContext
)

@plugin_metadata(
    name="{name}",
    version="1.0.0",
    description="{description}",
    author="{author}",
    email="{email}",
    website="{website}",
    license="{license}",
    plugin_type=PluginType.{plugin_type_enum},
    category=PluginCategory.{category_enum},
    dependencies={dependencies},
    min_framework_version="2.0.0",
    max_framework_version="3.0.0",
    tags={tags}
)
@register_plugin(PluginType.{plugin_type_enum})
class {class_name}(I{plugin_type}Plugin):
    """{name}插件"""
    
    def __init__(self):
        """初始化插件"""
        self._context: Optional[PluginContext] = None
        self._config = {config_defaults}
    
    @property
    def metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        return self._plugin_metadata
    
    def initialize(self, context: PluginContext) -> bool:
        """
        初始化插件
        
        Args:
            context: 插件上下文
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            self._context = context
            
            # 加载配置
            config = context.get_plugin_config(self.metadata.name)
            if config:
                self._config.update(config)
            
            context.logger.info(f"{self.metadata.name}插件初始化成功")
            return True
            
        except Exception as e:
            if context:
                context.logger.error(f"{self.metadata.name}插件初始化失败: {{e}}")
            return False
    
    def cleanup(self) -> None:
        """清理插件资源"""
        if self._context:
            self._context.logger.info(f"{self.metadata.name}插件清理完成")
    
    {specific_methods}
'''

    PLUGIN_JSON_TEMPLATE = {
        "name": "{name}",
        "version": "1.0.0",
        "description": "{description}",
        "author": "{author}",
        "email": "{email}",
        "website": "{website}",
        "license": "{license}",
        "plugin_type": "{plugin_type}",
        "category": "{category}",
        "dependencies": [],
        "min_framework_version": "2.0.0",
        "max_framework_version": "3.0.0",
        "tags": [],
        "main_module": "{main_module}",
        "main_class": "{main_class}"
    }

    README_TEMPLATE = '''# {name}

{description}

## 功能特性

- 功能1
- 功能2
- 功能3

## 安装方法

1. 下载插件文件
2. 在FactorWeave-Quant 中打开插件管理器
3. 点击"安装本地插件"
4. 选择插件文件进行安装

## 使用方法

1. 在插件管理器中启用插件
2. 根据插件类型在相应位置使用功能
3. 可在插件设置中调整参数

## 配置参数

{config_docs}

## 更新日志

### v1.0.0
- 初始版本发布

## 许可证

{license}

## 联系方式

- 作者: {author}
- 邮箱: {email}
- 网站: {website}
'''

    SPECIFIC_METHODS = {
        PluginType.INDICATOR: '''
    def get_indicator_name(self) -> str:
        """获取指标名称"""
        return "{name}"
    
    def get_indicator_parameters(self) -> Dict[str, Any]:
        """获取指标参数定义"""
        return {
            # 在这里定义指标参数
        }
    
    def calculate(self, data: pd.DataFrame, **params) -> Dict[str, pd.Series]:
        """
        计算指标值
        
        Args:
            data: 价格数据
            **params: 参数
            
        Returns:
            指标计算结果
        """
        # 在这里实现指标计算逻辑
        pass
    
    def get_plot_config(self) -> Dict[str, Any]:
        """获取绘图配置"""
        return {
            # 在这里定义绘图配置
        }
''',

        PluginType.STRATEGY: '''
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return "{name}"
    
    def get_strategy_parameters(self) -> Dict[str, Any]:
        """获取策略参数定义"""
        return {
            # 在这里定义策略参数
        }
    
    def generate_signals(self, data: pd.DataFrame, **params) -> Any:
        """
        生成交易信号
        
        Args:
            data: 市场数据
            **params: 策略参数
            
        Returns:
            交易信号
        """
        # 在这里实现信号生成逻辑
        pass
''',

        PluginType.DATA_SOURCE: '''
    def get_data_source_name(self) -> str:
        """获取数据源名称"""
        return "{name}"
    
    def get_supported_data_types(self) -> List[str]:
        """获取支持的数据类型"""
        return []
    
    def fetch_data(self, symbol: str, data_type: str, **params) -> Any:
        """
        获取数据
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            **params: 其他参数
            
        Returns:
            数据
        """
        # 在这里实现数据获取逻辑
        pass
''',

        PluginType.ANALYSIS: '''
    def get_analysis_name(self) -> str:
        """获取分析工具名称"""
        return "{name}"
    
    def analyze(self, data: pd.DataFrame, **params) -> Dict[str, Any]:
        """
        执行分析
        
        Args:
            data: 输入数据
            **params: 分析参数
            
        Returns:
            分析结果
        """
        # 在这里实现分析逻辑
        pass
''',

        PluginType.UI_COMPONENT: '''
    def get_component_name(self) -> str:
        """获取组件名称"""
        return "{name}"
    
    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """
        创建组件
        
        Args:
            parent: 父组件
            
        Returns:
            组件实例
        """
        # 在这里实现组件创建逻辑
        pass
''',

        PluginType.EXPORT: '''
    def get_export_name(self) -> str:
        """获取导出器名称"""
        return "{name}"
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式"""
        return []
    
    def export_data(self, data: Any, format_type: str, output_path: str, **params) -> bool:
        """
        导出数据
        
        Args:
            data: 要导出的数据
            format_type: 格式类型
            output_path: 输出路径
            **params: 其他参数
            
        Returns:
            是否导出成功
        """
        # 在这里实现数据导出逻辑
        pass
''',

        PluginType.NOTIFICATION: '''
    def get_notification_name(self) -> str:
        """获取通知器名称"""
        return "{name}"
    
    def send_notification(self, title: str, message: str, **params) -> bool:
        """
        发送通知
        
        Args:
            title: 标题
            message: 消息内容
            **params: 其他参数
            
        Returns:
            是否发送成功
        """
        # 在这里实现通知发送逻辑
        pass
''',

        PluginType.CHART_TOOL: '''
    def get_tool_name(self) -> str:
        """获取工具名称"""
        return "{name}"
    
    def get_tool_icon(self) -> str:
        """获取工具图标路径"""
        return "icons/{name}.png"
    
    def activate_tool(self, chart_widget: QWidget) -> None:
        """
        激活工具
        
        Args:
            chart_widget: 图表组件
        """
        # 在这里实现工具激活逻辑
        pass
    
    def deactivate_tool(self) -> None:
        """停用工具"""
        # 在这里实现工具停用逻辑
        pass
'''
    }


class PluginSDK:
    """插件开发工具包"""

    def __init__(self, workspace_dir: str):
        """
        初始化SDK

        Args:
            workspace_dir: 工作空间目录
        """
        self.workspace_dir = Path(workspace_dir)
        self.templates_dir = self.workspace_dir / "templates"
        self.projects_dir = self.workspace_dir / "projects"

        # 创建必要目录
        self.workspace_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.projects_dir.mkdir(exist_ok=True)

    def create_plugin_project(self,
                              name: str,
                              plugin_type: PluginType,
                              author: str = "Unknown",
                              email: str = "",
                              website: str = "",
                              license: str = "MIT",
                              description: str = "",
                              category: PluginCategory = PluginCategory.COMMUNITY,
                              dependencies: List[str] = None,
                              tags: List[str] = None) -> str:
        """
        创建插件项目

        Args:
            name: 插件名称
            plugin_type: 插件类型
            author: 作者
            email: 邮箱
            website: 网站
            license: 许可证
            description: 描述
            category: 分类
            dependencies: 依赖列表
            tags: 标签列表

        Returns:
            项目目录路径
        """
        if dependencies is None:
            dependencies = []
        if tags is None:
            tags = []

        # 创建项目目录
        project_name = name.lower().replace("", "_")
        project_dir = self.projects_dir / project_name
        project_dir.mkdir(exist_ok=True)

        # 生成类名
        class_name = self._generate_class_name(name, plugin_type)
        main_module = f"{project_name}.py"

        # 准备模板变量
        template_vars = {
            'name': name,
            'description': description or f"{name}插件",
            'author': author,
            'email': email,
            'website': website,
            'license': license,
            'plugin_type': plugin_type.value,
            'plugin_type_enum': plugin_type.name,
            'category': category.value,
            'category_enum': category.name,
            'dependencies': json.dumps(dependencies),
            'tags': json.dumps(tags),
            'class_name': class_name,
            'main_module': main_module.replace('.py', ''),
            'main_class': class_name,
            'config_defaults': "{}",
            'specific_methods': PluginTemplate.SPECIFIC_METHODS.get(plugin_type, "").format(name=name)
        }

        # 生成主模块文件
        main_file = project_dir / main_module
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(PluginTemplate.INDICATOR_TEMPLATE.format(**template_vars))

        # 生成plugin.json
        plugin_json = project_dir / "plugin.json"
        with open(plugin_json, 'w', encoding='utf-8') as f:
            json.dump(PluginTemplate.PLUGIN_JSON_TEMPLATE, f,
                      indent=2, ensure_ascii=False)

        # 替换plugin.json中的占位符
        with open(plugin_json, 'r', encoding='utf-8') as f:
            content = f.read()

        for key, value in template_vars.items():
            content = content.replace(f"{{{key}}}", str(value))

        with open(plugin_json, 'w', encoding='utf-8') as f:
            f.write(content)

        # 生成README.md
        config_docs = "暂无配置参数"
        readme_vars = template_vars.copy()
        readme_vars['config_docs'] = config_docs

        readme_file = project_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(PluginTemplate.README_TEMPLATE.format(**readme_vars))

        # 生成requirements.txt
        requirements_file = project_dir / "requirements.txt"
        with open(requirements_file, 'w', encoding='utf-8') as f:
            for dep in dependencies:
                f.write(f"{dep}\n")

        # 创建测试目录
        test_dir = project_dir / "tests"
        test_dir.mkdir(exist_ok=True)

        # 生成测试文件
        test_file = test_dir / f"test_{project_name}.py"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(self._generate_test_template(template_vars))

        # 创建资源目录
        resources_dir = project_dir / "resources"
        resources_dir.mkdir(exist_ok=True)

        # 创建图标目录
        icons_dir = resources_dir / "icons"
        icons_dir.mkdir(exist_ok=True)

        return str(project_dir)

    def validate_plugin_project(self, project_dir: str) -> Dict[str, Any]:
        """
        验证插件项目

        Args:
            project_dir: 项目目录

        Returns:
            验证结果
        """
        project_path = Path(project_dir)
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # 检查必要文件
        required_files = ['plugin.json']
        for file_name in required_files:
            file_path = project_path / file_name
            if not file_path.exists():
                result['valid'] = False
                result['errors'].append(f"缺少必要文件: {file_name}")

        # 检查plugin.json格式
        plugin_json_path = project_path / "plugin.json"
        if plugin_json_path.exists():
            try:
                with open(plugin_json_path, 'r', encoding='utf-8') as f:
                    plugin_config = json.load(f)

                # 检查必要字段
                required_fields = ['name', 'version',
                                   'main_module', 'main_class']
                for field in required_fields:
                    if field not in plugin_config:
                        result['valid'] = False
                        result['errors'].append(f"plugin.json缺少必要字段: {field}")

                # 检查主模块文件
                main_module = plugin_config.get('main_module')
                if main_module:
                    main_file = project_path / f"{main_module}.py"
                    if not main_file.exists():
                        result['valid'] = False
                        result['errors'].append(f"主模块文件不存在: {main_module}.py")

            except json.JSONDecodeError as e:
                result['valid'] = False
                result['errors'].append(f"plugin.json格式错误: {e}")

        # 检查Python语法
        for py_file in project_path.glob("*.py"):
            if not self._check_python_syntax(py_file):
                result['valid'] = False
                result['errors'].append(f"Python语法错误: {py_file.name}")

        # 检查推荐文件
        recommended_files = ['README.md', 'requirements.txt']
        for file_name in recommended_files:
            file_path = project_path / file_name
            if not file_path.exists():
                result['warnings'].append(f"建议添加文件: {file_name}")

        return result

    def build_plugin(self, project_dir: str, output_dir: str = None) -> str:
        """
        构建插件

        Args:
            project_dir: 项目目录
            output_dir: 输出目录

        Returns:
            构建的插件文件路径
        """
        project_path = Path(project_dir)

        # 验证项目
        validation_result = self.validate_plugin_project(project_dir)
        if not validation_result['valid']:
            raise ValueError(f"项目验证失败: {validation_result['errors']}")

        # 读取插件配置
        with open(project_path / "plugin.json", 'r', encoding='utf-8') as f:
            plugin_config = json.load(f)

        plugin_name = plugin_config['name']
        plugin_version = plugin_config['version']

        # 确定输出目录
        if output_dir is None:
            output_dir = project_path / "dist"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(exist_ok=True)

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 复制项目文件
            for item in project_path.iterdir():
                if item.name in ['.git', '__pycache__', 'dist', 'build']:
                    continue

                if item.is_file():
                    shutil.copy2(item, temp_path / item.name)
                elif item.is_dir():
                    shutil.copytree(item, temp_path / item.name)

            # 创建zip文件
            zip_name = f"{plugin_name.replace(' ', '_')}-{plugin_version}.zip"
            zip_path = output_dir / zip_name

            shutil.make_archive(str(zip_path).replace(
                '.zip', ''), 'zip', temp_dir)

        return str(zip_path)

    def test_plugin(self, project_dir: str) -> Dict[str, Any]:
        """
        测试插件

        Args:
            project_dir: 项目目录

        Returns:
            测试结果
        """
        project_path = Path(project_dir)
        result = {
            'passed': True,
            'tests': [],
            'errors': []
        }

        # 查找测试文件
        test_files = list(project_path.glob("tests/test_*.py"))

        if not test_files:
            result['warnings'] = ["没有找到测试文件"]
            return result

        # 运行测试
        for test_file in test_files:
            try:
                # 使用subprocess运行pytest
                cmd = ["python", "-m", "pytest", str(test_file), "-v"]
                process = subprocess.run(cmd, capture_output=True, text=True,
                                         cwd=str(project_path))

                test_result = {
                    'file': test_file.name,
                    'passed': process.returncode == 0,
                    'output': process.stdout,
                    'errors': process.stderr
                }

                result['tests'].append(test_result)

                if process.returncode != 0:
                    result['passed'] = False
                    result['errors'].append(f"测试失败: {test_file.name}")

            except Exception as e:
                result['passed'] = False
                result['errors'].append(f"运行测试失败: {e}")

        return result

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        列出所有项目

        Returns:
            项目列表
        """
        projects = []

        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                plugin_json_path = project_dir / "plugin.json"
                if plugin_json_path.exists():
                    try:
                        with open(plugin_json_path, 'r', encoding='utf-8') as f:
                            plugin_config = json.load(f)

                        project_info = {
                            'name': plugin_config.get('name', project_dir.name),
                            'version': plugin_config.get('version', '1.0.0'),
                            'description': plugin_config.get('description', ''),
                            'author': plugin_config.get('author', ''),
                            'plugin_type': plugin_config.get('plugin_type', ''),
                            'path': str(project_dir),
                            'last_modified': datetime.fromtimestamp(
                                plugin_json_path.stat().st_mtime
                            ).isoformat()
                        }

                        projects.append(project_info)

                    except json.JSONDecodeError:
                        continue

        return sorted(projects, key=lambda x: x['last_modified'], reverse=True)

    def _generate_class_name(self, name: str, plugin_type: PluginType) -> str:
        """
        生成类名

        Args:
            name: 插件名称
            plugin_type: 插件类型

        Returns:
            类名
        """
        # 移除特殊字符，转换为驼峰命名
        clean_name = ''.join(c for c in name if c.isalnum() or c.isspace())
        words = clean_name.split()
        class_name = ''.join(word.capitalize() for word in words)

        # 添加插件类型后缀
        type_suffix = {
            PluginType.INDICATOR: "Indicator",
            PluginType.STRATEGY: "Strategy",
            PluginType.DATA_SOURCE: "DataSource",
            PluginType.ANALYSIS: "Analysis",
            PluginType.UI_COMPONENT: "Component",
            PluginType.EXPORT: "Export",
            PluginType.NOTIFICATION: "Notification",
            PluginType.CHART_TOOL: "Tool"
        }

        suffix = type_suffix.get(plugin_type, "Plugin")
        if not class_name.endswith(suffix):
            class_name += suffix

        return class_name + "Plugin"

    def _generate_test_template(self, template_vars: Dict[str, Any]) -> str:
        """
        生成测试模板

        Args:
            template_vars: 模板变量

        Returns:
            测试代码
        """
        return f'''"""
{template_vars['name']}插件测试
"""

import unittest
from unittest.mock import Mock

from {template_vars['main_module']} import {template_vars['class_name']}

class Test{template_vars['class_name']}(unittest.TestCase):
    """测试{template_vars['name']}插件"""
    
    def setUp(self):
        """设置测试环境"""
        self.plugin = {template_vars['class_name']}()
        
        # 模拟插件上下文
        self.mock_context = Mock()
        self.mock_context.get_plugin_config.return_value = {{}}
        self.mock_context.# log_manager已迁移到Loguru
    
    def test_initialize(self):
        """测试插件初始化"""
        result = self.plugin.initialize(self.mock_context)
        self.assertTrue(result)
    
    def test_metadata(self):
        """测试插件元数据"""
        metadata = self.plugin.metadata
        self.assertEqual(metadata.name, "{template_vars['name']}")
        self.assertEqual(metadata.version, "1.0.0")
    
    def test_cleanup(self):
        """测试插件清理"""
        self.plugin.initialize(self.mock_context)
        self.plugin.cleanup()
        # 验证清理操作
    
    def tearDown(self):
        """清理测试环境"""
        self.plugin.cleanup()

if __name__ == '__main__':
    unittest.main()
'''

    def _check_python_syntax(self, file_path: Path) -> bool:
        """
        检查Python语法

        Args:
            file_path: 文件路径

        Returns:
            语法是否正确
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            compile(source, str(file_path), 'exec')
            return True

        except SyntaxError:
            return False
        except Exception:
            return False
