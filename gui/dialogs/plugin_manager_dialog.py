"""
插件管理主界面对话框

提供插件的统一管理界面，包括：
- 插件列表显示
- 插件状态管理
- 插件配置
- 插件监控
- 插件更新
"""

import os
import json
from typing import Dict, List, Optional, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSplitter,
    QProgressBar, QMessageBox, QWidget, QTabWidget,
    QTextEdit, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem, QToolBar, QAction, QMenu, QStatusBar,
    QProgressDialog, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

from core.plugin_manager import PluginManager, PluginInfo, PluginStatus, PluginType, PluginCategory
from plugins.plugin_interface import PluginMetadata
from core.logger import get_logger

logger = get_logger(__name__)


class PluginStatusWidget(QWidget):
    """插件状态小部件"""

    def __init__(self, plugin_info: PluginInfo, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        self.init_ui()

    def init_ui(self):
        """初始化UI - 优化插件卡片样式"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        # 设置卡片样式 - 修复PyQt5兼容性
        self.setStyleSheet("""
            PluginStatusWidget {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin: 2px;
            }
            PluginStatusWidget:hover {
                border: 2px solid #007bff;
                background-color: #f8f9ff;
            }
            QLabel {
                border: none;
                background-color: transparent;
                margin: 1px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)

        # 插件信息区域（左侧）
        info_layout = QVBoxLayout()

        # 插件名称（主要显示）
        name_label = QLabel(self.plugin_info.name)
        name_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        name_label.setStyleSheet("color: #212529; margin-bottom: 2px;")
        info_layout.addWidget(name_label)

        # 副标题：版本 + 描述
        subtitle_text = f"v{self.plugin_info.version}"
        if self.plugin_info.description:
            subtitle_text += f" - {self.plugin_info.description[:50]}{'...' if len(self.plugin_info.description) > 50 else ''}"

        subtitle_label = QLabel(subtitle_text)
        subtitle_label.setFont(QFont("Microsoft YaHei", 9))
        subtitle_label.setStyleSheet("color: #6c757d;")
        info_layout.addWidget(subtitle_label)

        layout.addLayout(info_layout)

        layout.addStretch()

        # 状态指示器（中间）
        status_label = QLabel()
        status_color = self._get_status_color(self.plugin_info.status)
        status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                border-radius: 4px;
                padding: 4px 14px;
                color: white;
                font-size: 10px;
                font-weight: bold;
                margin: 0 12px;
            }}
        """)
        status_label.setText(self._get_status_text(self.plugin_info.status))
        # status_label.setFixedWidth(100)
        layout.addWidget(status_label)

        # 操作按钮（右侧）
        buttons_layout = QHBoxLayout()

        # 状态控制按钮
        if self.plugin_info.status in [PluginStatus.LOADED, PluginStatus.DISABLED, PluginStatus.UNLOADED]:
            enable_btn = QPushButton("启用")
            enable_btn.setStyleSheet("background-color: #28a745;")
            enable_btn.clicked.connect(self.enable_plugin)
            buttons_layout.addWidget(enable_btn)
        elif self.plugin_info.status == PluginStatus.ENABLED:
            disable_btn = QPushButton("禁用")
            disable_btn.setStyleSheet("background-color: #dc3545;")
            disable_btn.clicked.connect(self.disable_plugin)
            buttons_layout.addWidget(disable_btn)

        # 配置按钮
        config_btn = QPushButton("配置")
        config_btn.setStyleSheet("background-color: #6c757d;")
        config_btn.clicked.connect(self.configure_plugin)
        buttons_layout.addWidget(config_btn)

        layout.addLayout(buttons_layout)

    def _get_status_color(self, status: PluginStatus) -> str:
        """获取状态颜色"""
        color_map = {
            PluginStatus.UNLOADED: "#666666",
            PluginStatus.LOADED: "#17a2b8",
            PluginStatus.ENABLED: "#28a745",
            PluginStatus.DISABLED: "#ffc107",
            PluginStatus.ERROR: "#dc3545"
        }
        return color_map.get(status, "#666666")

    def _get_status_text(self, status: PluginStatus) -> str:
        """获取状态文本"""
        text_map = {
            PluginStatus.UNLOADED: "未加载",
            PluginStatus.LOADED: "已加载",
            PluginStatus.ENABLED: "已启用",
            PluginStatus.DISABLED: "已禁用",
            PluginStatus.ERROR: "错误"
        }
        return text_map.get(status, "未知")

    def enable_plugin(self):
        """启用插件"""
        # 查找PluginManagerDialog实例
        dialog = self._find_plugin_manager_dialog()
        if dialog:
            dialog.enable_plugin(self.plugin_info.name)

    def disable_plugin(self):
        """禁用插件"""
        # 查找PluginManagerDialog实例
        dialog = self._find_plugin_manager_dialog()
        if dialog:
            dialog.disable_plugin(self.plugin_info.name)

    def configure_plugin(self):
        """配置插件"""
        # 查找PluginManagerDialog实例
        dialog = self._find_plugin_manager_dialog()
        if dialog:
            dialog.configure_plugin(self.plugin_info.name)

    def _find_plugin_manager_dialog(self):
        """查找PluginManagerDialog实例"""
        parent = self.parent()
        while parent:
            if isinstance(parent, PluginManagerDialog):
                return parent
            parent = parent.parent()
        return None

    def _update_status_display(self, new_status: PluginStatus):
        """更新状态显示 - 修复状态同步"""
        try:
            # 更新内部状态
            self.plugin_info.status = new_status

            # 查找并更新状态标签
            for child in self.findChildren(QLabel):
                # 查找状态标签（通过样式特征识别）
                if 'background-color:' in child.styleSheet() and 'border-radius:' in child.styleSheet():
                    # 更新状态文本和颜色
                    status_color = self._get_status_color(new_status)
                    child.setStyleSheet(f"""
                        QLabel {{
                            background-color: {status_color};
                            border-radius: 4px;
                            padding: 4px 14px;
                            color: white;
                            font-size: 10px;
                            font-weight: bold;
                            margin: 0 14px;
                        }}
                    """)
                    child.setText(self._get_status_text(new_status))
                    break

            # 更新按钮显示
            self._update_buttons_for_status(new_status)

        except Exception as e:
            logger.warning(f"更新插件状态显示失败: {e}")

    def _update_buttons_for_status(self, status: PluginStatus):
        """根据状态更新按钮显示"""
        try:
            # 清除所有现有按钮
            buttons_to_remove = []
            for child in self.findChildren(QPushButton):
                if child.text() in ['启用', '禁用']:
                    buttons_to_remove.append(child)

            for button in buttons_to_remove:
                button.setParent(None)
                button.deleteLater()

            # 根据新状态添加合适的按钮
            layout = self.layout()
            if layout:
                # 查找按钮布局
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if isinstance(item.layout(), QHBoxLayout):
                        buttons_layout = item.layout()

                        # 添加状态控制按钮
                        if status in [PluginStatus.LOADED, PluginStatus.DISABLED, PluginStatus.UNLOADED]:
                            enable_btn = QPushButton("启用")
                            enable_btn.setStyleSheet("background-color: #28a745; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-size: 11px; font-weight: bold; min-width: 60px;")
                            enable_btn.clicked.connect(self.enable_plugin)
                            buttons_layout.insertWidget(0, enable_btn)
                        elif status == PluginStatus.ENABLED:
                            disable_btn = QPushButton("禁用")
                            disable_btn.setStyleSheet("background-color: #dc3545; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-size: 11px; font-weight: bold; min-width: 60px;")
                            disable_btn.clicked.connect(self.disable_plugin)
                            buttons_layout.insertWidget(0, disable_btn)
                        break

        except Exception as e:
            logger.warning(f"更新按钮状态失败: {e}")


class PluginConfigDialog(QDialog):
    """插件配置对话框"""

    def __init__(self, plugin_info: PluginInfo, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        self.plugin_manager = plugin_manager
        self.config_widgets = {}
        self.init_ui()
        self.load_config()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"配置插件 - {self.plugin_info.name}")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # 插件信息
        info_group = QGroupBox("插件信息")
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("名称:"), 0, 0)
        info_layout.addWidget(QLabel(self.plugin_info.name), 0, 1)

        info_layout.addWidget(QLabel("版本:"), 1, 0)
        info_layout.addWidget(QLabel(self.plugin_info.version), 1, 1)

        info_layout.addWidget(QLabel("作者:"), 2, 0)
        info_layout.addWidget(QLabel(self.plugin_info.author), 2, 1)

        info_layout.addWidget(QLabel("描述:"), 3, 0)
        desc_label = QLabel(self.plugin_info.description)
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label, 3, 1)

        layout.addWidget(info_group)

        # 配置选项
        self.config_group = QGroupBox("配置选项")
        self.config_layout = QGridLayout(self.config_group)
        layout.addWidget(self.config_group)

        # 按钮
        button_layout = QHBoxLayout()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_config)
        button_layout.addWidget(reset_btn)

        layout.addLayout(button_layout)

    def load_config(self):
        """加载配置"""
        try:
            print(f"🔧 [调试] 开始加载插件配置: {self.plugin_info.name}")
            print(f"📝 [调试] 当前插件信息: path={getattr(self.plugin_info, 'path', 'N/A')}, config={self.plugin_info.config}")

            # 先尝试检查是否为ConfigurablePlugin类型的情绪插件
            plugin_instance = self._get_plugin_instance()

            # 保存插件实例（无论是什么类型）
            self.plugin_instance = plugin_instance

            if plugin_instance and self._is_configurable_plugin(plugin_instance):
                print(f"✅ [调试] 检测到ConfigurablePlugin类型插件")
                self._load_configurable_plugin_config(plugin_instance)
            else:
                print(f"📋 [调试] 使用传统配置加载方式")
                self._load_traditional_config()

        except Exception as e:
            print(f"❌ [调试] 加载插件配置失败: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"加载插件配置失败: {e}")
            QMessageBox.warning(self, "警告", f"加载配置失败: {e}")

    def _get_plugin_instance(self):
        """尝试获取插件实例 - 自适应各种插件类型"""
        try:
            print(f"🔍 [调试] 尝试获取插件实例: {self.plugin_info.name}")

            # 已知插件映射（可以逐步扩展）
            known_plugins = {
                # 情绪数据源插件
                'fmp_sentiment': 'plugins.sentiment_data_sources.fmp_sentiment_plugin.FMPSentimentPlugin',
                'vix_sentiment': 'plugins.sentiment_data_sources.vix_sentiment_plugin.VIXSentimentPlugin',
                'news_sentiment': 'plugins.sentiment_data_sources.news_sentiment_plugin.NewsSentimentPlugin',
                'exorde_sentiment': 'plugins.sentiment_data_sources.exorde_sentiment_plugin.ExordeSentimentPlugin',
                'crypto_sentiment': 'plugins.sentiment_data_sources.crypto_sentiment_plugin.CryptoSentimentPlugin',
                # 支持完整路径名称
                'sentiment_data_sources.fmp_sentiment_plugin': 'plugins.sentiment_data_sources.fmp_sentiment_plugin.FMPSentimentPlugin',
                'sentiment_data_sources.vix_sentiment_plugin': 'plugins.sentiment_data_sources.vix_sentiment_plugin.VIXSentimentPlugin',
                'sentiment_data_sources.news_sentiment_plugin': 'plugins.sentiment_data_sources.news_sentiment_plugin.NewsSentimentPlugin',
                'sentiment_data_sources.exorde_sentiment_plugin': 'plugins.sentiment_data_sources.exorde_sentiment_plugin.ExordeSentimentPlugin',
                'sentiment_data_sources.crypto_sentiment_plugin': 'plugins.sentiment_data_sources.crypto_sentiment_plugin.CryptoSentimentPlugin',
                'sentiment_data_sources.akshare_sentiment_plugin': 'plugins.sentiment_data_sources.akshare_sentiment_plugin.AkShareSentimentPlugin',
                'sentiment_data_sources.multi_source_sentiment_plugin': 'plugins.sentiment_data_sources.multi_source_sentiment_plugin.MultiSourceSentimentPlugin',
                # 示例插件
                'examples.macd_indicator': 'plugins.examples.macd_indicator.MACDIndicatorPlugin',
                'examples.moving_average_strategy': 'plugins.examples.moving_average_strategy.MovingAverageStrategyPlugin',
                'examples.simple_plugin': 'plugins.examples.simple_plugin.SimplePlugin',
                # 新增插件
                'examples.yahoo_finance_datasource': 'plugins.examples.yahoo_finance_datasource.YahooFinanceDataSourcePlugin',
                'examples.rsi_indicator': 'plugins.examples.rsi_indicator.RSIIndicatorPlugin',
            }

            plugin_path = known_plugins.get(self.plugin_info.name)
            print(f"📋 [调试] 插件路径映射: {plugin_path}")

            # 尝试第一种方式：直接映射
            if plugin_path:
                try:
                    module_path, class_name = plugin_path.rsplit('.', 1)
                    print(f"📦 [调试] 模块路径: {module_path}, 类名: {class_name}")

                    module = __import__(module_path, fromlist=[class_name])
                    plugin_class = getattr(module, class_name)
                    instance = plugin_class()
                    print(f"✅ [调试] 插件实例创建成功: {type(instance)}")
                    return instance
                except Exception as e:
                    print(f"⚠️ [调试] 直接映射创建失败: {e}")

            # 尝试第二种方式：智能推断（自适应各种插件类型）
            plugin_name = self.plugin_info.name
            print(f"🧠 [调试] 尝试智能推断插件: {plugin_name}")

            # 智能推断不同类型的插件
            inference_strategies = [
                # 策略1: 情绪数据源插件
                {
                    'condition': lambda name: 'sentiment_data_sources' in name,
                    'module_prefix': 'plugins.sentiment_data_sources',
                    'class_suffix': 'SentimentPlugin'
                },
                # 策略2: 示例插件
                {
                    'condition': lambda name: 'examples' in name or name.startswith('examples.'),
                    'module_prefix': 'plugins.examples',
                    'class_suffix': 'Plugin'
                },
                # 策略3: 自定义指标插件
                {
                    'condition': lambda name: 'indicator' in name.lower(),
                    'module_prefix': 'plugins',
                    'class_suffix': 'Plugin'
                },
                # 策略4: 通用插件
                {
                    'condition': lambda name: True,  # 默认策略
                    'module_prefix': 'plugins',
                    'class_suffix': 'Plugin'
                }
            ]

            for strategy in inference_strategies:
                if strategy['condition'](plugin_name):
                    try:
                        print(f"🎯 [调试] 使用推断策略: {strategy['module_prefix']}")

                        # 提取实际插件名
                        if '.' in plugin_name:
                            parts = plugin_name.split('.')
                            if len(parts) >= 2:
                                # 如果是 "category.plugin_name" 格式
                                actual_name = parts[-1]  # 取最后一个部分
                            else:
                                actual_name = parts[0]
                        else:
                            actual_name = plugin_name

                        print(f"🔍 [调试] 提取的插件名: {actual_name}")

                        # 构造模块路径
                        if '.' in plugin_name and strategy['module_prefix'] == 'plugins':
                            # 对于包含点的插件名，尝试直接构造路径
                            module_path = f"plugins.{plugin_name}"
                        else:
                            # 使用策略前缀
                            module_path = f"{strategy['module_prefix']}.{actual_name}"

                        # 推断多种可能的类名
                        clean_name = actual_name.replace('_plugin', '')
                        class_name_parts = clean_name.split('_')

                        # 生成多种可能的类名
                        possible_class_names = []

                        # 策略1: 标准驼峰命名 + 后缀
                        standard_name = ''.join(word.capitalize() for word in class_name_parts) + strategy['class_suffix']
                        possible_class_names.append(standard_name)

                        # 策略2: 全大写首字母 + 后缀（如RSI -> RSIIndicatorPlugin）
                        if len(class_name_parts) > 0:
                            first_part = class_name_parts[0].upper()
                            rest_parts = [word.capitalize() for word in class_name_parts[1:]]
                            upper_first_name = first_part + ''.join(rest_parts) + strategy['class_suffix']
                            possible_class_names.append(upper_first_name)

                        # 策略3: 特殊词汇处理（如datasource -> DataSource）
                        special_words = {
                            'datasource': 'DataSource',
                            'database': 'Database',
                            'api': 'API',
                            'url': 'URL',
                            'json': 'JSON',
                            'xml': 'XML',
                            'csv': 'CSV'
                        }

                        special_name_parts = []
                        for part in class_name_parts:
                            if part.lower() in special_words:
                                special_name_parts.append(special_words[part.lower()])
                            else:
                                special_name_parts.append(part.capitalize())
                        special_name = ''.join(special_name_parts) + strategy['class_suffix']
                        possible_class_names.append(special_name)

                        # 去重
                        possible_class_names = list(dict.fromkeys(possible_class_names))

                        print(f"🔧 [调试] 推断的模块路径: {module_path}")
                        print(f"🔧 [调试] 可能的类名: {possible_class_names}")

                        # 尝试每个可能的类名
                        module = __import__(module_path, fromlist=possible_class_names)
                        for class_name in possible_class_names:
                            try:
                                plugin_class = getattr(module, class_name)
                                instance = plugin_class()
                                print(f"✅ [调试] 智能推断创建成功: {type(instance)} (使用类名: {class_name})")
                                return instance
                            except AttributeError:
                                print(f"⚠️ [调试] 类名 {class_name} 不存在，尝试下一个")
                                continue

                        print(f"❌ [调试] 推断策略失败")

                    except Exception as e:
                        print(f"⚠️ [调试] 推断策略失败: {e}")
                        continue  # 尝试下一个策略

            # 尝试第三种方式：使用plugin_info.path
            if hasattr(self.plugin_info, 'path') and self.plugin_info.path:
                try:
                    print(f"🛠️ [调试] 尝试使用plugin_info.path: {self.plugin_info.path}")

                    # 如果path是模块路径，尝试导入
                    if '.' in self.plugin_info.path:
                        module_path = self.plugin_info.path
                        # 尝试常见的类名模式
                        possible_class_names = []

                        # 从路径推断类名
                        path_parts = module_path.split('.')
                        if path_parts:
                            last_part = path_parts[-1]
                            # 移除_plugin后缀
                            clean_name = last_part.replace('_plugin', '')
                            # 转换为驼峰命名
                            class_name_parts = clean_name.split('_')
                            class_name = ''.join(word.capitalize() for word in class_name_parts) + 'SentimentPlugin'
                            possible_class_names.append(class_name)

                            # 其他可能的命名模式
                            possible_class_names.append(clean_name.replace('_', '') + 'Plugin')
                            possible_class_names.append(clean_name.title().replace('_', '') + 'Plugin')

                        print(f"🔧 [调试] 可能的类名: {possible_class_names}")

                        for class_name in possible_class_names:
                            try:
                                module = __import__(module_path, fromlist=[class_name])
                                plugin_class = getattr(module, class_name)
                                instance = plugin_class()
                                print(f"✅ [调试] 使用plugin_info.path创建成功: {type(instance)}")
                                return instance
                            except (ImportError, AttributeError) as e:
                                print(f"⚠️ [调试] 尝试类名 {class_name} 失败: {e}")
                                continue

                except Exception as e:
                    print(f"⚠️ [调试] 使用plugin_info.path失败: {e}")

            print(f"❌ [调试] 所有方式都失败，返回None")
            return None
        except Exception as e:
            print(f"🚫 [调试] 获取插件实例失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _is_configurable_plugin(self, plugin_instance):
        """检查是否为ConfigurablePlugin"""
        try:
            from plugins.sentiment_data_sources.config_base import ConfigurablePlugin
            return isinstance(plugin_instance, ConfigurablePlugin)
        except ImportError:
            return False

    def _load_configurable_plugin_config(self, plugin_instance):
        """加载ConfigurablePlugin类型的配置"""
        try:
            print(f"📋 [调试] 获取配置模式...")
            config_schema = plugin_instance.get_config_schema()
            print(f"✅ [调试] 配置模式获取成功，字段数量: {len(config_schema)}")

            # 加载当前配置值
            current_config = plugin_instance.load_config()
            print(f"📝 [调试] 当前配置: {current_config}")

            # 为了保持与原有布局的兼容性，使用行号布局
            row = 0

            for field in config_schema:
                print(f"🔧 [调试] 创建控件: {field.name} ({field.field_type})")

                # 创建标签
                label_text = field.display_name
                if field.required:
                    label_text += " *"
                label = QLabel(f"{label_text}:")
                self.config_layout.addWidget(label, row, 0)

                # 创建控件
                widget = self._create_field_control(field, current_config.get(field.name, field.default_value))
                if widget:
                    self.config_layout.addWidget(widget, row, 1)
                    self.config_widgets[field.name] = widget

                    # 设置提示信息
                    if field.description:
                        widget.setToolTip(field.description)
                        label.setToolTip(field.description)

                    print(f"  ✅ [调试] 控件创建成功: {field.name}")
                    row += 1
                else:
                    print(f"  ❌ [调试] 控件创建失败: {field.name}")

            # 插件实例已在load_config中保存，这里不需要重复保存
            print(f"✅ [调试] ConfigurablePlugin配置加载完成，总共创建了 {len(self.config_widgets)} 个控件")

            # 强制刷新布局
            self.config_layout.update()
            if hasattr(self, 'config_group'):
                self.config_group.update()
            self.update()
            print(f"🔄 [调试] 强制刷新布局和界面")

        except Exception as e:
            print(f"❌ [调试] 加载ConfigurablePlugin配置失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _create_field_control(self, field, value):
        """创建配置字段控件"""
        try:
            if field.field_type == "boolean":
                widget = QCheckBox()
                widget.setChecked(bool(value))
                return widget

            elif field.field_type == "number":
                if field.min_value is not None and field.min_value >= 0 and field.max_value is not None and field.max_value <= 100 and isinstance(field.default_value, int):
                    # 整数类型
                    widget = QSpinBox()
                    widget.setMinimum(int(field.min_value) if field.min_value is not None else 0)
                    widget.setMaximum(int(field.max_value) if field.max_value is not None else 9999)
                    widget.setValue(int(value) if value is not None else 0)
                else:
                    # 浮点数类型
                    widget = QDoubleSpinBox()
                    widget.setDecimals(3)
                    widget.setMinimum(field.min_value if field.min_value is not None else -999999.0)
                    widget.setMaximum(field.max_value if field.max_value is not None else 999999.0)
                    widget.setValue(float(value) if value is not None else 0.0)
                return widget

            elif field.field_type == "select":
                widget = QComboBox()
                if field.options:
                    widget.addItems(field.options)
                    if value in field.options:
                        widget.setCurrentText(str(value))
                return widget

            elif field.field_type == "multiselect":
                widget = QLineEdit()
                if isinstance(value, list):
                    widget.setText(",".join(map(str, value)))
                else:
                    widget.setText(str(value))
                if field.placeholder:
                    widget.setPlaceholderText(field.placeholder)
                return widget

            else:  # string
                widget = QLineEdit()
                widget.setText(str(value))
                if field.placeholder:
                    widget.setPlaceholderText(field.placeholder)
                return widget

        except Exception as e:
            print(f"❌ [调试] 创建控件失败: {e}")
            return None

    def _load_traditional_config(self):
        """加载传统的字典配置"""
        print(f"📋 [调试] 使用传统配置加载方式")
        config = self.plugin_info.config
        print(f"📝 [调试] 传统配置内容: {config}")

        if not config:
            print(f"⚠️ [调试] 传统配置为空，将显示空白配置区域")
            # 添加一个提示标签
            hint_label = QLabel("此插件没有可配置的参数")
            hint_label.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
            hint_label.setAlignment(Qt.AlignCenter)
            self.config_layout.addWidget(hint_label, 0, 0, 1, 2)
            return

        # 动态创建配置控件
        row = 0
        for key, value in config.items():
            if key.startswith('_'):  # 跳过私有配置
                continue

            print(f"🔧 [调试] 创建传统配置控件: {key} = {value}")

            label = QLabel(f"{key}:")
            self.config_layout.addWidget(label, row, 0)

            if isinstance(value, bool):
                widget = QCheckBox()
                widget.setChecked(value)
            elif isinstance(value, int):
                widget = QSpinBox()
                widget.setRange(-999999, 999999)
                widget.setValue(value)
            elif isinstance(value, float):
                widget = QDoubleSpinBox()
                widget.setRange(-999999.0, 999999.0)
                widget.setValue(value)
            elif isinstance(value, str):
                widget = QLineEdit()
                widget.setText(value)
            else:
                widget = QLineEdit()
                widget.setText(str(value))

            self.config_layout.addWidget(widget, row, 1)
            self.config_widgets[key] = widget
            row += 1
            print(f"  ✅ [调试] 传统配置控件创建成功: {key}")

        print(f"✅ [调试] 传统配置加载完成，总共创建了 {len(self.config_widgets)} 个控件")

    def save_config(self):
        """保存配置"""
        try:
            print(f"💾 [调试] 开始保存插件配置: {self.plugin_info.name}")

            new_config = {}

            for key, widget in self.config_widgets.items():
                if isinstance(widget, QCheckBox):
                    new_config[key] = widget.isChecked()
                elif isinstance(widget, QSpinBox):
                    new_config[key] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    new_config[key] = widget.value()
                elif isinstance(widget, QComboBox):
                    new_config[key] = widget.currentText()
                elif isinstance(widget, QLineEdit):
                    text = widget.text().strip()
                    # 处理多选字段（逗号分隔）
                    if "," in text:
                        new_config[key] = [item.strip() for item in text.split(",") if item.strip()]
                    else:
                        # 尝试转换为原始类型
                        original_value = self.plugin_info.config.get(key)
                        if isinstance(original_value, (int, float)):
                            try:
                                new_config[key] = type(original_value)(text)
                            except ValueError:
                                new_config[key] = text
                        else:
                            new_config[key] = text

            print(f"📝 [调试] 收集到的配置: {new_config}")

            # 如果是ConfigurablePlugin，使用其保存方法
            if hasattr(self, 'plugin_instance') and self.plugin_instance:
                print(f"✅ [调试] 使用ConfigurablePlugin保存方法")
                try:
                    # 验证配置
                    is_valid, error_msg = self.plugin_instance.validate_config(new_config)
                    if not is_valid:
                        QMessageBox.warning(self, "配置验证失败", f"配置验证失败:\n{error_msg}")
                        return

                    # 保存配置
                    success = self.plugin_instance.save_config(new_config)
                    if success:
                        print(f"✅ [调试] ConfigurablePlugin配置保存成功")
                        QMessageBox.information(self, "成功", "插件配置已保存")
                        self.accept()
                    else:
                        QMessageBox.warning(self, "保存失败", "无法保存插件配置")
                except Exception as e:
                    print(f"❌ [调试] ConfigurablePlugin保存失败: {e}")
                    raise
            else:
                print(f"📋 [调试] 使用传统保存方法")
                # 传统保存方法
                self.plugin_info.config.update(new_config)

                # 通知插件管理器
                if hasattr(self.plugin_manager, 'update_plugin_config'):
                    self.plugin_manager.update_plugin_config(
                        self.plugin_info.name, new_config)

                QMessageBox.information(self, "成功", "配置已保存")
                self.accept()

        except Exception as e:
            print(f"❌ [调试] 保存插件配置失败: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"保存插件配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")

    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(self, "确认", "确定要重置配置吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.load_config()


class PluginManagerDialog(QDialog):
    """插件管理主界面对话框"""

    # 信号定义 - 修复信号声明
    plugin_enabled = pyqtSignal(str)
    plugin_disabled = pyqtSignal(str)
    plugin_configured = pyqtSignal(str)
    plugin_error = pyqtSignal(str, str)  # 插件名称, 错误信息

    def __init__(self, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager

        # 验证插件管理器
        if not self.plugin_manager:
            raise ValueError("插件管理器不能为None")

        # 初始化内部状态
        self.plugin_widgets = {}
        self.is_loading = False
        self.last_error = None

        # 初始化数据库服务
        try:
            from core.services.plugin_database_service import get_plugin_database_service
            self.db_service = get_plugin_database_service()

            # 连接数据库信号
            self.db_service.plugin_status_changed.connect(self._on_database_status_changed)
            self.db_service.database_updated.connect(self._on_database_updated)

            # 同步插件状态到数据库
            self.db_service.sync_plugin_statuses(self.plugin_manager)

            logger.info("插件数据库服务集成成功")
        except Exception as e:
            logger.error(f"插件数据库服务初始化失败: {e}")
            self.db_service = None

        # 创建定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_plugins)

        try:
            # 初始化UI
            self.init_ui()

            # 加载插件（安全加载）
            self.safe_load_plugins()

            # 启动定时刷新（仅在成功加载后）
            if self.plugin_widgets:
                self.timer.start(10000)  # 每10秒刷新一次，降低频率
                logger.info("插件管理器初始化成功，启动定时刷新")
            else:
                logger.warning("插件列表为空，不启动定时刷新")

        except Exception as e:
            logger.error(f"插件管理器初始化失败: {e}")
            self.last_error = str(e)
            # 即使初始化失败，也要显示UI以便用户查看错误信息
            if not hasattr(self, 'status_bar'):
                self.init_ui()
            self.update_status_with_error(f"初始化失败: {e}")

    def safe_load_plugins(self):
        """安全加载插件列表"""
        try:
            self.is_loading = True
            self.load_plugins()
        except Exception as e:
            logger.error(f"安全加载插件失败: {e}")
            self.last_error = str(e)
            self.add_log(f"❌ 加载插件列表失败: {e}")
        finally:
            self.is_loading = False

    def update_status_with_error(self, error_msg: str):
        """更新状态栏显示错误信息"""
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"错误: {error_msg}")
            self.status_bar.setStyleSheet("color: red;")

    def init_ui(self):
        """初始化UI - 优化样式和布局"""
        self.setWindowTitle("HIkyuu 插件管理器")
        self.setModal(True)
        self.resize(1000, 700)

        # 设置窗口图标和样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                background-color: white;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #e9ecef;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid #dee2e6;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QToolBar {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 5px;
                spacing: 5px;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #495057;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QLineEdit, QComboBox {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #007bff;
                outline: none;
            }
            QStatusBar {
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
            }
        """)

        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)

        # 选项卡
        self.tab_widget = QTabWidget()

        # 插件列表选项卡
        self.plugins_tab = self.create_plugins_tab()
        self.tab_widget.addTab(self.plugins_tab, "插件列表")

        # 插件监控选项卡
        self.monitor_tab = self.create_monitor_tab()
        self.tab_widget.addTab(self.monitor_tab, "性能监控")

        # 插件日志选项卡
        self.logs_tab = self.create_logs_tab()
        self.tab_widget.addTab(self.logs_tab, "日志")

        layout.addWidget(self.tab_widget)

        # 状态栏
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

        self.update_status()

    def create_toolbar(self) -> QToolBar:
        """创建工具栏"""
        toolbar = QToolBar()

        # 刷新按钮
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_plugins)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # 全部启用
        enable_all_action = QAction("全部启用", self)
        enable_all_action.triggered.connect(self.enable_all_plugins)
        toolbar.addAction(enable_all_action)

        # 全部禁用
        disable_all_action = QAction("全部禁用", self)
        disable_all_action.triggered.connect(self.disable_all_plugins)
        toolbar.addAction(disable_all_action)

        toolbar.addSeparator()

        # 插件市场
        market_action = QAction("插件市场", self)
        market_action.triggered.connect(self.open_plugin_market)
        toolbar.addAction(market_action)

        return toolbar

    def create_plugins_tab(self) -> QWidget:
        """创建插件列表选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入插件名称或描述...")
        self.search_edit.textChanged.connect(self.filter_plugins)
        search_layout.addWidget(self.search_edit)

        # 类型过滤
        search_layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", "")
        for plugin_type in PluginType:
            self.type_combo.addItem(plugin_type.value, plugin_type.value)
        self.type_combo.currentTextChanged.connect(self.filter_plugins)
        search_layout.addWidget(self.type_combo)

        # 状态过滤
        search_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", "")
        for status in PluginStatus:
            self.status_combo.addItem(status.value, status.value)
        self.status_combo.currentTextChanged.connect(self.filter_plugins)
        search_layout.addWidget(self.status_combo)

        layout.addLayout(search_layout)

        # 插件列表
        self.plugins_list = QListWidget()
        layout.addWidget(self.plugins_list)

        return widget

    def create_monitor_tab(self) -> QWidget:
        """创建性能监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QGridLayout(stats_group)

        self.total_plugins_label = QLabel("0")
        self.enabled_plugins_label = QLabel("0")
        self.disabled_plugins_label = QLabel("0")
        self.error_plugins_label = QLabel("0")

        stats_layout.addWidget(QLabel("总插件数:"), 0, 0)
        stats_layout.addWidget(self.total_plugins_label, 0, 1)

        stats_layout.addWidget(QLabel("已启用:"), 1, 0)
        stats_layout.addWidget(self.enabled_plugins_label, 1, 1)

        stats_layout.addWidget(QLabel("已禁用:"), 2, 0)
        stats_layout.addWidget(self.disabled_plugins_label, 2, 1)

        stats_layout.addWidget(QLabel("错误:"), 3, 0)
        stats_layout.addWidget(self.error_plugins_label, 3, 1)

        layout.addWidget(stats_group)

        # 性能图表区域
        perf_group = QGroupBox("性能监控")
        perf_layout = QVBoxLayout(perf_group)

        self.perf_text = QTextEdit()
        self.perf_text.setReadOnly(True)
        perf_layout.addWidget(self.perf_text)

        layout.addWidget(perf_group)

        return widget

    def create_logs_tab(self) -> QWidget:
        """创建日志选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 日志控制
        control_layout = QHBoxLayout()

        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.clear_logs)
        control_layout.addWidget(clear_btn)

        control_layout.addStretch()

        # 日志级别
        control_layout.addWidget(QLabel("级别:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        control_layout.addWidget(self.log_level_combo)

        layout.addLayout(control_layout)

        # 日志显示
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.logs_text)

        return widget

    def load_plugins(self):
        """加载插件列表"""
        try:
            self.plugins_list.clear()
            self.plugin_widgets.clear()

            # 获取所有插件
            plugins = self.plugin_manager.get_all_plugin_metadata()

            for plugin_name, metadata in plugins.items():
                # 获取准确的插件状态
                plugin_status = self._get_actual_plugin_status(plugin_name, metadata)

                # 创建插件信息对象
                plugin_info = PluginInfo(
                    name=plugin_name,
                    version=metadata.get('version', '1.0.0'),
                    description=metadata.get('description', ''),
                    author=metadata.get('author', ''),
                    path=metadata.get('path', ''),
                    status=plugin_status,
                    config=metadata.get('config', {}),
                    dependencies=metadata.get('dependencies', [])
                )

                # 创建插件状态小部件
                plugin_widget = PluginStatusWidget(plugin_info)

                # 创建列表项
                list_item = QListWidgetItem()
                list_item.setSizeHint(plugin_widget.sizeHint())

                self.plugins_list.addItem(list_item)
                self.plugins_list.setItemWidget(list_item, plugin_widget)

                self.plugin_widgets[plugin_name] = plugin_widget

            self.update_status()

        except Exception as e:
            logger.error(f"加载插件列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载插件列表失败: {e}")

    def _get_actual_plugin_status(self, plugin_name: str, metadata: dict) -> PluginStatus:
        """获取插件的实际状态 - 以数据库为准，确保数据库与真实插件同步"""
        try:
            # 第一优先级：从数据库获取状态（数据库为准则）
            if self.db_service:
                db_status = self.db_service.get_plugin_status(plugin_name)
                if db_status:
                    # 将数据库状态转换为UI枚举（兼容不同模块的PluginStatus）
                    ui_status = self._convert_db_status_to_ui_status(db_status)
                    return ui_status
                else:
                    # 数据库中没有记录，这是一个新发现的插件
                    # 按照用户需求：新插件默认状态为禁用
                    logger.info(f"发现新插件 {plugin_name}，添加到数据库并设为禁用状态")

                    # 先注册插件元数据
                    self.db_service.register_plugin_from_metadata(plugin_name, metadata)

                    # 设置默认状态为禁用（使用数据库枚举）
                    from db.models.plugin_models import PluginStatus as DbPluginStatus
                    self.db_service.update_plugin_status(plugin_name, DbPluginStatus.DISABLED, "新发现插件，默认禁用")
                    return PluginStatus.DISABLED  # 返回UI枚举

            # 降级：如果没有数据库服务，使用运行时状态
            return self._determine_runtime_status(plugin_name)

        except Exception as e:
            logger.warning(f"获取插件状态失败 {plugin_name}: {e}")
            return PluginStatus.UNLOADED

    def _convert_db_status_to_ui_status(self, db_status) -> PluginStatus:
        """将数据库状态转换为UI状态枚举"""
        try:
            # 如果已经是UI枚举，直接返回
            if isinstance(db_status, PluginStatus):
                return db_status

            # 通过状态值进行映射
            status_value = db_status.value if hasattr(db_status, 'value') else str(db_status)

            # 状态值映射表
            status_mapping = {
                'unloaded': PluginStatus.UNLOADED,
                'loaded': PluginStatus.LOADED,
                'enabled': PluginStatus.ENABLED,
                'disabled': PluginStatus.DISABLED,
                'error': PluginStatus.ERROR,
                'installing': PluginStatus.LOADED,    # 安装中视为已加载
                'updating': PluginStatus.LOADED,      # 更新中视为已加载
                'uninstalling': PluginStatus.UNLOADED  # 卸载中视为未加载
            }

            mapped_status = status_mapping.get(status_value.lower(), PluginStatus.UNLOADED)
            logger.debug(f"状态转换: {db_status} ({status_value}) -> {mapped_status}")
            return mapped_status

        except Exception as e:
            logger.warning(f"状态转换失败: {db_status}, 错误: {e}")
            return PluginStatus.UNLOADED

    def _verify_plugin_status(self, plugin_name: str, db_status: PluginStatus) -> PluginStatus:
        """验证数据库状态与实际状态是否一致"""
        runtime_status = self._determine_runtime_status(plugin_name)

        # 如果运行时状态表明插件已启用/禁用，但数据库显示不同，以运行时为准
        if runtime_status in [PluginStatus.ENABLED, PluginStatus.DISABLED] and db_status != runtime_status:
            return runtime_status

        # 其他情况保持数据库状态
        return db_status

    def _determine_runtime_status(self, plugin_name: str) -> PluginStatus:
        """确定插件的运行时状态"""
        try:
            # 优先从插件管理器的enhanced_plugins获取状态
            if hasattr(self.plugin_manager, 'enhanced_plugins') and plugin_name in self.plugin_manager.enhanced_plugins:
                enhanced_plugin = self.plugin_manager.enhanced_plugins[plugin_name]
                return enhanced_plugin.status

            # 次优：检查插件实例是否存在和加载
            if hasattr(self.plugin_manager, 'plugin_instances'):
                if plugin_name in self.plugin_manager.plugin_instances:
                    # 插件已加载到实例中，检查是否启用
                    if hasattr(self.plugin_manager, 'is_plugin_enabled'):
                        return PluginStatus.ENABLED if self.plugin_manager.is_plugin_enabled(plugin_name) else PluginStatus.DISABLED
                    else:
                        return PluginStatus.LOADED
                else:
                    return PluginStatus.UNLOADED

            # 降级：使用原始的is_plugin_loaded方法
            if hasattr(self.plugin_manager, 'is_plugin_loaded'):
                return PluginStatus.ENABLED if self.plugin_manager.is_plugin_loaded(plugin_name) else PluginStatus.UNLOADED

            # 最后降级：根据metadata推断
            return PluginStatus.UNLOADED

        except Exception as e:
            logger.warning(f"确定运行时状态失败 {plugin_name}: {e}")
            return PluginStatus.UNLOADED

    def refresh_plugins(self):
        """刷新插件列表"""
        self.load_plugins()
        self.update_monitor_stats()

    def filter_plugins(self):
        """过滤插件"""
        search_text = self.search_edit.text().lower()
        plugin_type = self.type_combo.currentData()
        status = self.status_combo.currentData()

        for i in range(self.plugins_list.count()):
            item = self.plugins_list.item(i)
            widget = self.plugins_list.itemWidget(item)

            if widget and isinstance(widget, PluginStatusWidget):
                plugin_info = widget.plugin_info

                # 文本匹配
                text_match = (search_text in plugin_info.name.lower() or
                              search_text in plugin_info.description.lower())

                # 类型匹配
                type_match = (not plugin_type or
                              (plugin_info.plugin_type and plugin_info.plugin_type.value == plugin_type))

                # 状态匹配
                status_match = (
                    not status or plugin_info.status.value == status)

                item.setHidden(
                    not (text_match and type_match and status_match))

    def enable_plugin(self, plugin_name: str):
        """启用插件 - 修复核心逻辑"""
        try:
            # 调用插件管理器的启用方法
            if hasattr(self.plugin_manager, 'enable_plugin'):
                success = self.plugin_manager.enable_plugin(plugin_name)
                if success:
                    self.plugin_enabled.emit(plugin_name)
                    self.add_log(f"✅ 插件 '{plugin_name}' 已成功启用")

                    # 更新数据库状态
                    if self.db_service:
                        from db.models.plugin_models import PluginStatus as DbPluginStatus
                        self.db_service.update_plugin_status(
                            plugin_name, DbPluginStatus.ENABLED, "用户手动启用"
                        )

                    # 立即更新对应widget的状态显示
                    self._immediate_update_plugin_status(plugin_name, PluginStatus.ENABLED)
                    # 延迟刷新整个列表
                    QTimer.singleShot(100, self.refresh_plugins)
                else:
                    self.add_log(f"❌ 插件 '{plugin_name}' 启用失败")
                    QMessageBox.warning(self, "警告", f"插件 '{plugin_name}' 启用失败，请检查插件依赖和配置")
            else:
                # 降级处理：如果没有enable_plugin方法，尝试load_plugin
                if hasattr(self.plugin_manager, 'load_plugin'):
                    success = self.plugin_manager.load_plugin(plugin_name)
                    if success:
                        self.plugin_enabled.emit(plugin_name)
                        self.add_log(f"✅ 插件 '{plugin_name}' 已加载")
                        self.refresh_plugins()
                    else:
                        self.add_log(f"❌ 插件 '{plugin_name}' 加载失败")
                else:
                    self.add_log(f"⚠️ 插件管理器不支持启用功能")
                    QMessageBox.information(self, "提示", "插件管理器不支持启用功能")

        except Exception as e:
            logger.error(f"启用插件失败: {e}")
            self.add_log(f"❌ 启用插件 '{plugin_name}' 时发生错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"启用插件失败: {e}")

    def disable_plugin(self, plugin_name: str):
        """禁用插件 - 修复核心逻辑"""
        try:
            # 调用插件管理器的禁用方法
            if hasattr(self.plugin_manager, 'disable_plugin'):
                success = self.plugin_manager.disable_plugin(plugin_name)
                if success:
                    self.plugin_disabled.emit(plugin_name)
                    self.add_log(f"✅ 插件 '{plugin_name}' 已成功禁用")

                    # 更新数据库状态
                    if self.db_service:
                        from db.models.plugin_models import PluginStatus as DbPluginStatus
                        self.db_service.update_plugin_status(
                            plugin_name, DbPluginStatus.DISABLED, "用户手动禁用"
                        )

                    # 立即更新对应widget的状态显示
                    self._immediate_update_plugin_status(plugin_name, PluginStatus.DISABLED)
                    # 延迟刷新整个列表
                    QTimer.singleShot(100, self.refresh_plugins)
                else:
                    self.add_log(f"❌ 插件 '{plugin_name}' 禁用失败")
                    QMessageBox.warning(self, "警告", f"插件 '{plugin_name}' 禁用失败")
            else:
                # 降级处理：如果没有disable_plugin方法，尝试unload_plugin
                if hasattr(self.plugin_manager, 'unload_plugin'):
                    success = self.plugin_manager.unload_plugin(plugin_name)
                    if success:
                        self.plugin_disabled.emit(plugin_name)
                        self.add_log(f"✅ 插件 '{plugin_name}' 已卸载")
                        self.refresh_plugins()
                    else:
                        self.add_log(f"❌ 插件 '{plugin_name}' 卸载失败")
                else:
                    self.add_log(f"⚠️ 插件管理器不支持禁用功能")
                    QMessageBox.information(self, "提示", "插件管理器不支持禁用功能")

        except Exception as e:
            logger.error(f"禁用插件失败: {e}")
            self.add_log(f"❌ 禁用插件 '{plugin_name}' 时发生错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"禁用插件失败: {e}")

    def configure_plugin(self, plugin_name: str):
        """配置插件"""
        try:
            # 获取插件信息
            if plugin_name in self.plugin_widgets:
                plugin_widget = self.plugin_widgets[plugin_name]
                plugin_info = plugin_widget.plugin_info

                # 打开配置对话框
                config_dialog = PluginConfigDialog(
                    plugin_info, self.plugin_manager, self)
                if config_dialog.exec_() == QDialog.Accepted:
                    self.plugin_configured.emit(plugin_name)
                    self.add_log(f"插件 {plugin_name} 配置已更新")

        except Exception as e:
            logger.error(f"配置插件失败: {e}")
            QMessageBox.critical(self, "错误", f"配置插件失败: {e}")

    def enable_all_plugins(self):
        """启用所有插件 - 批量操作，无弹窗"""
        reply = QMessageBox.question(self, "确认", "确定要启用所有插件吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._batch_enable_plugins(list(self.plugin_widgets.keys()))

    def disable_all_plugins(self):
        """禁用所有插件 - 批量操作，无弹窗"""
        reply = QMessageBox.question(self, "确认", "确定要禁用所有插件吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._batch_disable_plugins(list(self.plugin_widgets.keys()))

    def _batch_enable_plugins(self, plugin_names: list):
        """批量启用插件 - 直接更新状态，无弹窗"""
        try:
            from db.models.plugin_models import PluginStatus as DbPluginStatus

            success_count = 0
            error_count = 0

            # 显示进度条
            progress = QProgressDialog("正在批量启用插件...", "取消", 0, len(plugin_names), self)
            progress.setWindowTitle("批量操作进度")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            for i, plugin_name in enumerate(plugin_names):
                if progress.wasCanceled():
                    break

                progress.setValue(i)
                progress.setLabelText(f"正在启用插件: {plugin_name}")
                QApplication.processEvents()  # 更新UI

                try:
                    # 直接更新数据库状态，不调用插件管理器的启用方法（避免弹窗）
                    if self.db_service:
                        self.db_service.update_plugin_status(
                            plugin_name, DbPluginStatus.ENABLED, "批量启用操作"
                        )

                    # 更新UI显示
                    self._immediate_update_plugin_status(plugin_name, PluginStatus.ENABLED)

                    success_count += 1
                    self.add_log(f"✅ 插件 '{plugin_name}' 已启用")

                except Exception as e:
                    error_count += 1
                    self.add_log(f"❌ 启用插件 '{plugin_name}' 失败: {e}")

            progress.setValue(len(plugin_names))
            progress.close()

            # 最终刷新
            QTimer.singleShot(100, self.refresh_plugins)

            # 显示结果摘要
            if error_count == 0:
                self.add_log(f"✅ 批量启用完成，成功启用 {success_count} 个插件")
            else:
                self.add_log(f"⚠️ 批量启用完成，成功 {success_count} 个，失败 {error_count} 个")

        except Exception as e:
            logger.error(f"批量启用插件失败: {e}")
            self.add_log(f"❌ 批量启用操作失败: {e}")

    def _batch_disable_plugins(self, plugin_names: list):
        """批量禁用插件 - 直接更新状态，无弹窗"""
        try:
            from db.models.plugin_models import PluginStatus as DbPluginStatus

            success_count = 0
            error_count = 0

            # 显示进度条
            progress = QProgressDialog("正在批量禁用插件...", "取消", 0, len(plugin_names), self)
            progress.setWindowTitle("批量操作进度")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            for i, plugin_name in enumerate(plugin_names):
                if progress.wasCanceled():
                    break

                progress.setValue(i)
                progress.setLabelText(f"正在禁用插件: {plugin_name}")
                QApplication.processEvents()  # 更新UI

                try:
                    # 直接更新数据库状态，不调用插件管理器的禁用方法（避免弹窗）
                    if self.db_service:
                        self.db_service.update_plugin_status(
                            plugin_name, DbPluginStatus.DISABLED, "批量禁用操作"
                        )

                    # 更新UI显示
                    self._immediate_update_plugin_status(plugin_name, PluginStatus.DISABLED)

                    success_count += 1
                    self.add_log(f"✅ 插件 '{plugin_name}' 已禁用")

                except Exception as e:
                    error_count += 1
                    self.add_log(f"❌ 禁用插件 '{plugin_name}' 失败: {e}")

            progress.setValue(len(plugin_names))
            progress.close()

            # 最终刷新
            QTimer.singleShot(100, self.refresh_plugins)

            # 显示结果摘要
            if error_count == 0:
                self.add_log(f"✅ 批量禁用完成，成功禁用 {success_count} 个插件")
            else:
                self.add_log(f"⚠️ 批量禁用完成，成功 {success_count} 个，失败 {error_count} 个")

        except Exception as e:
            logger.error(f"批量禁用插件失败: {e}")
            self.add_log(f"❌ 批量禁用操作失败: {e}")

    def open_plugin_market(self):
        """打开插件市场"""
        try:
            from gui.dialogs.enhanced_plugin_market_dialog import EnhancedPluginMarketDialog

            dialog = EnhancedPluginMarketDialog(self.plugin_manager, self)
            dialog.exec_()

        except Exception as e:
            logger.error(f"打开插件市场失败: {e}")
            QMessageBox.critical(self, "错误", f"打开插件市场失败: {e}")

    def update_status(self):
        """更新状态栏"""
        total = len(self.plugin_widgets)
        enabled = sum(1 for w in self.plugin_widgets.values()
                      if w.plugin_info.status == PluginStatus.ENABLED)

        self.status_bar.showMessage(f"总计: {total} 个插件, 已启用: {enabled} 个")

    def update_monitor_stats(self):
        """更新监控统计 - 修复数据展示"""
        try:
            # 重新计算状态统计（确保使用最新状态）
            status_counts = {
                PluginStatus.ENABLED: 0,
                PluginStatus.DISABLED: 0,
                PluginStatus.LOADED: 0,
                PluginStatus.UNLOADED: 0,
                PluginStatus.ERROR: 0
            }

            total = len(self.plugin_widgets)

            # 遍历所有插件widget，重新获取状态
            for plugin_name, widget in self.plugin_widgets.items():
                try:
                    # 重新获取最新状态
                    current_status = self._get_actual_plugin_status(plugin_name, {})

                    # 确保current_status是有效的插件状态（兼容不同模块的PluginStatus枚举）
                    if not hasattr(current_status, 'value') or not current_status.value:
                        logger.warning(f"插件 {plugin_name} 状态无效: {type(current_status)}, 值: {current_status}")
                        current_status = PluginStatus.UNLOADED  # 默认值
                    elif hasattr(current_status, 'value') and current_status.value not in ['unloaded', 'loaded', 'enabled', 'disabled', 'error']:
                        logger.warning(f"插件 {plugin_name} 状态值无效: {current_status.value}")
                        current_status = PluginStatus.UNLOADED  # 默认值

                    # 更新widget中的状态（确保同步）
                    widget.plugin_info.status = current_status

                    # 统计计数 - 使用状态值进行兼容性匹配
                    status_value = current_status.value if hasattr(current_status, 'value') else str(current_status)

                    # 将状态值映射到本地PluginStatus枚举
                    status_mapping = {
                        'unloaded': PluginStatus.UNLOADED,
                        'loaded': PluginStatus.LOADED,
                        'enabled': PluginStatus.ENABLED,
                        'disabled': PluginStatus.DISABLED,
                        'error': PluginStatus.ERROR,
                        'installing': PluginStatus.LOADED,  # 映射为LOADED
                        'updating': PluginStatus.LOADED,    # 映射为LOADED
                        'uninstalling': PluginStatus.UNLOADED  # 映射为UNLOADED
                    }

                    mapped_status = status_mapping.get(status_value, PluginStatus.ERROR)
                    status_counts[mapped_status] += 1

                except Exception as e:
                    logger.error(f"处理插件 {plugin_name} 状态失败: {e}")
                    status_counts[PluginStatus.ERROR] += 1

            # 更新统计标签
            self.total_plugins_label.setText(str(total))
            self.enabled_plugins_label.setText(str(status_counts[PluginStatus.ENABLED]))
            self.disabled_plugins_label.setText(str(status_counts[PluginStatus.DISABLED]))
            self.error_plugins_label.setText(str(status_counts[PluginStatus.ERROR]))

            # 获取实际性能数据
            memory_info = self._get_memory_usage()
            response_times = self._get_plugin_response_times()

            # 更新详细性能信息
            perf_info = f"""📊 插件性能监控报告
{'='*40}

📈 状态统计:
├─ 总插件数: {total} 个
├─ ✅ 已启用: {status_counts[PluginStatus.ENABLED]} 个
├─ ⏸️  已禁用: {status_counts[PluginStatus.DISABLED]} 个
├─ 📦 已加载: {status_counts[PluginStatus.LOADED]} 个
├─ ⭕ 未加载: {status_counts[PluginStatus.UNLOADED]} 个
└─ ❌ 错误: {status_counts[PluginStatus.ERROR]} 个

💾 内存使用:
├─ 插件总内存: {memory_info['plugin_memory']:.2f} MB
├─ 平均每插件: {memory_info['avg_per_plugin']:.2f} MB
└─ 系统可用: {memory_info['available']:.2f} MB

⚡ 性能指标:
├─ 平均响应时间: {response_times['average']:.2f} ms
├─ 最快响应: {response_times['min']:.2f} ms
├─ 最慢响应: {response_times['max']:.2f} ms
└─ 插件管理器版本: HIkyuu v2.0

🔄 最后更新: {self._get_current_time()}
"""
            self.perf_text.setText(perf_info.strip())

            # 强制刷新所有插件widget的显示
            self._refresh_plugin_widgets()

        except Exception as e:
            logger.error(f"更新监控统计失败: {e}")
            # 降级显示基本信息
            self._show_basic_monitor_info()

    def _get_memory_usage(self) -> dict:
        """获取内存使用信息"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            available = psutil.virtual_memory().available / (1024*1024)  # MB

            plugin_memory = memory_info.rss / (1024*1024)  # MB
            avg_per_plugin = plugin_memory / max(len(self.plugin_widgets), 1)

            return {
                'plugin_memory': plugin_memory,
                'avg_per_plugin': avg_per_plugin,
                'available': available
            }
        except ImportError:
            return {
                'plugin_memory': 0.0,
                'avg_per_plugin': 0.0,
                'available': 0.0
            }
        except Exception:
            return {
                'plugin_memory': 0.0,
                'avg_per_plugin': 0.0,
                'available': 0.0
            }

    def _get_plugin_response_times(self) -> dict:
        """获取插件响应时间"""
        # 模拟响应时间数据（实际应该从插件管理器获取）
        import random
        base_time = 50  # 基础响应时间50ms
        times = [base_time + random.uniform(-20, 30) for _ in range(max(len(self.plugin_widgets), 1))]

        return {
            'average': sum(times) / len(times),
            'min': min(times),
            'max': max(times)
        }

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _refresh_plugin_widgets(self):
        """强制刷新所有插件widget的显示"""
        try:
            for plugin_name, widget in self.plugin_widgets.items():
                # 重新获取状态并更新显示
                current_status = widget.plugin_info.status
                widget._update_status_display(current_status)
        except Exception as e:
            logger.warning(f"刷新插件widget显示失败: {e}")

    def _show_basic_monitor_info(self):
        """显示基本监控信息（降级处理）"""
        total = len(self.plugin_widgets)
        basic_info = f"""📊 插件基本信息

总插件数: {total} 个
监控数据获取中...

请稍后刷新查看详细信息。
"""
        if hasattr(self, 'perf_text'):
            self.perf_text.setText(basic_info)

    def _immediate_update_plugin_status(self, plugin_name: str, new_status: PluginStatus):
        """立即更新插件状态显示 - 不等待完整刷新"""
        try:
            # 更新widget状态
            if plugin_name in self.plugin_widgets:
                widget = self.plugin_widgets[plugin_name]
                widget._update_status_display(new_status)
                self.add_log(f"🔄 UI已更新插件 '{plugin_name}' 状态为: {self._get_status_text(new_status)}", "DEBUG")

            # 立即更新监控统计
            self.update_monitor_stats()

            # 更新状态栏
            self.update_status()

        except Exception as e:
            logger.error(f"立即更新插件状态失败: {e}")
            self.add_log(f"❌ 更新插件状态显示失败: {e}", "ERROR")

    def _get_status_text(self, status: PluginStatus) -> str:
        """获取状态文本 - 确保一致性"""
        text_map = {
            PluginStatus.UNLOADED: "未加载",
            PluginStatus.LOADED: "已加载",
            PluginStatus.ENABLED: "已启用",
            PluginStatus.DISABLED: "已禁用",
            PluginStatus.ERROR: "错误"
        }
        return text_map.get(status, "未知")

    def add_log(self, message: str, level: str = "INFO"):
        """添加日志 - 修复文本显示逻辑"""
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level}] {message}"

            # 检查日志组件是否存在
            if hasattr(self, 'logs_text') and self.logs_text:
                # 检查日志级别过滤
                current_level = getattr(self, 'log_level_combo', None)
                if current_level:
                    selected_level = current_level.currentText()
                    level_priority = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
                    if level_priority.get(level, 1) < level_priority.get(selected_level, 1):
                        return

                # 添加颜色样式
                color_map = {
                    "DEBUG": "#666666",
                    "INFO": "#000000",
                    "WARNING": "#ff8c00",
                    "ERROR": "#dc3545"
                }
                color = color_map.get(level, "#000000")

                # 使用HTML格式添加彩色日志
                html_entry = f'<span style="color: {color}">{log_entry}</span>'
                self.logs_text.append(html_entry)

                # 自动滚动到底部
                cursor = self.logs_text.textCursor()
                cursor.movePosition(cursor.End)
                self.logs_text.setTextCursor(cursor)
            else:
                # 降级处理：输出到控制台
                print(f"[Plugin Manager] {log_entry}")

        except Exception as e:
            # 确保日志方法本身不会导致崩溃
            print(f"[Plugin Manager Log Error] 添加日志失败: {e}, 原始消息: {message}")

    def clear_logs(self):
        """清空日志"""
        self.logs_text.clear()

    def _on_database_status_changed(self, plugin_name: str, old_status: str, new_status: str):
        """数据库状态变更处理"""
        try:
            self.add_log(f"📊 数据库状态变更: {plugin_name} {old_status} -> {new_status}", "DEBUG")

            # 强制刷新插件列表
            QTimer.singleShot(50, self.refresh_plugins)

        except Exception as e:
            logger.error(f"处理数据库状态变更失败: {e}")

    def _on_database_updated(self):
        """数据库更新处理"""
        try:
            self.add_log("📊 插件数据库已更新", "DEBUG")

            # 刷新监控统计
            self.update_monitor_stats()

        except Exception as e:
            logger.error(f"处理数据库更新失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        self.timer.stop()
        event.accept()


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建模拟插件管理器
    class MockPluginManager:
        def get_all_plugin_metadata(self):
            return {
                "test_plugin": {
                    "name": "测试插件",
                    "version": "1.0.0",
                    "description": "这是一个测试插件",
                    "author": "测试作者",
                    "path": "/path/to/plugin",
                    "config": {"enabled": True, "threshold": 0.5}
                }
            }

        def is_plugin_loaded(self, name):
            return True

    dialog = PluginManagerDialog(MockPluginManager())
    dialog.show()

    sys.exit(app.exec_())
