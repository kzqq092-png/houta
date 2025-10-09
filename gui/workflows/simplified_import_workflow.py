"""
简化导入工作流系统
重新设计和简化数据导入的操作流程，减少用户需要的步骤和学习成本
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QWizard, QWizardPage,
    QLabel, QPushButton, QFrame, QGroupBox, QComboBox, QLineEdit,
    QCheckBox, QRadioButton, QButtonGroup, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QTabWidget,
    QSplitter, QScrollArea, QStackedWidget, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer, QThread, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette, QColor
import threading

logger = logging.getLogger(__name__)


class WorkflowStep(Enum):
    """工作流步骤枚举"""
    WELCOME = "welcome"
    DATA_SOURCE = "data_source"
    QUICK_CONFIG = "quick_config"
    PREVIEW = "preview"
    EXECUTION = "execution"
    COMPLETION = "completion"


class ImportMode(Enum):
    """导入模式枚举"""
    QUICK = "quick"          # 快速导入
    GUIDED = "guided"        # 引导导入
    ADVANCED = "advanced"    # 高级导入
    TEMPLATE = "template"    # 模板导入


class DataSourceType(Enum):
    """数据源类型枚举"""
    CSV_FILE = "csv_file"
    EXCEL_FILE = "excel_file"
    DATABASE = "database"
    API = "api"
    REAL_TIME = "real_time"
    CUSTOM = "custom"


@dataclass
class WorkflowConfig:
    """工作流配置数据类"""
    import_mode: ImportMode = ImportMode.QUICK
    data_source_type: DataSourceType = DataSourceType.CSV_FILE
    auto_detect: bool = True
    skip_preview: bool = False
    auto_start: bool = False
    save_as_template: bool = False
    template_name: str = ""
    user_preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportTemplate:
    """导入模板数据类"""
    template_id: str
    name: str
    description: str
    data_source_type: DataSourceType
    config: Dict[str, Any]
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)


class TemplateManager:
    """模板管理器"""

    def __init__(self):
        self.templates: Dict[str, ImportTemplate] = {}
        self.popular_templates: List[str] = []
        self._load_default_templates()

    def _load_default_templates(self):
        """加载默认模板"""
        # 股票K线数据模板
        stock_kline_template = ImportTemplate(
            template_id="stock_kline",
            name="股票K线数据",
            description="导入股票的OHLC K线数据，包含开盘价、最高价、最低价、收盘价和成交量",
            data_source_type=DataSourceType.CSV_FILE,
            config={
                'columns': ['date', 'open', 'high', 'low', 'close', 'volume'],
                'date_format': '%Y-%m-%d',
                'data_type': 'kline',
                'frequency': 'daily',
                'auto_validation': True
            },
            tags=['股票', 'K线', '日线']
        )

        # 财务数据模板
        financial_template = ImportTemplate(
            template_id="financial_data",
            name="财务报表数据",
            description="导入上市公司的财务报表数据，包含资产负债表、利润表等",
            data_source_type=DataSourceType.EXCEL_FILE,
            config={
                'sheet_name': '财务数据',
                'header_row': 1,
                'data_type': 'financial',
                'auto_validation': True,
                'skip_empty_rows': True
            },
            tags=['财务', '报表', '基本面']
        )

        # 实时行情模板
        realtime_template = ImportTemplate(
            template_id="realtime_quotes",
            name="实时行情数据",
            description="连接实时行情数据源，获取最新的股票价格和交易数据",
            data_source_type=DataSourceType.API,
            config={
                'api_type': 'realtime',
                'update_interval': 1000,
                'data_type': 'tick',
                'auto_start': True
            },
            tags=['实时', '行情', 'API']
        )

        # 注册模板
        for template in [stock_kline_template, financial_template, realtime_template]:
            self.templates[template.template_id] = template
            self.popular_templates.append(template.template_id)

    def get_template(self, template_id: str) -> Optional[ImportTemplate]:
        """获取模板"""
        return self.templates.get(template_id)

    def get_templates_by_type(self, data_source_type: DataSourceType) -> List[ImportTemplate]:
        """按数据源类型获取模板"""
        return [t for t in self.templates.values() if t.data_source_type == data_source_type]

    def get_popular_templates(self, limit: int = 5) -> List[ImportTemplate]:
        """获取热门模板"""
        sorted_templates = sorted(
            self.templates.values(),
            key=lambda t: t.usage_count,
            reverse=True
        )
        return sorted_templates[:limit]

    def use_template(self, template_id: str) -> Optional[ImportTemplate]:
        """使用模板"""
        template = self.get_template(template_id)
        if template:
            template.usage_count += 1
            template.last_used = datetime.now()
        return template

    def save_template(self, template: ImportTemplate) -> bool:
        """保存模板"""
        try:
            self.templates[template.template_id] = template
            logger.info(f"模板已保存: {template.name}")
            return True
        except Exception as e:
            logger.error(f"保存模板失败: {e}")
            return False


class WelcomePage(QWizardPage):
    """欢迎页面"""

    def __init__(self, template_manager: TemplateManager):
        super().__init__()
        self.template_manager = template_manager
        self.setTitle("欢迎使用数据导入向导")
        self.setSubTitle("选择导入模式或使用预设模板快速开始")

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 导入模式选择
        mode_group = QGroupBox("选择导入模式")
        mode_layout = QVBoxLayout(mode_group)

        self.mode_group = QButtonGroup()

        # 快速导入
        self.quick_mode = QRadioButton("快速导入")
        self.quick_mode.setChecked(True)
        self.quick_mode.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        quick_desc = QLabel("适合常见数据格式，自动检测配置，一键导入")
        quick_desc.setStyleSheet("color: #666; margin-left: 20px;")

        # 引导导入
        self.guided_mode = QRadioButton("引导导入")
        self.guided_mode.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        guided_desc = QLabel("逐步引导配置，适合复杂数据源或特殊需求")
        guided_desc.setStyleSheet("color: #666; margin-left: 20px;")

        # 模板导入
        self.template_mode = QRadioButton("模板导入")
        self.template_mode.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        template_desc = QLabel("使用预设模板，快速导入常见数据类型")
        template_desc.setStyleSheet("color: #666; margin-left: 20px;")

        self.mode_group.addButton(self.quick_mode, ImportMode.QUICK.value)
        self.mode_group.addButton(self.guided_mode, ImportMode.GUIDED.value)
        self.mode_group.addButton(self.template_mode, ImportMode.TEMPLATE.value)

        mode_layout.addWidget(self.quick_mode)
        mode_layout.addWidget(quick_desc)
        mode_layout.addSpacing(10)
        mode_layout.addWidget(self.guided_mode)
        mode_layout.addWidget(guided_desc)
        mode_layout.addSpacing(10)
        mode_layout.addWidget(self.template_mode)
        mode_layout.addWidget(template_desc)

        layout.addWidget(mode_group)

        # 热门模板
        template_group = QGroupBox("热门模板")
        template_layout = QVBoxLayout(template_group)

        self.template_list = QListWidget()
        self.template_list.setMaximumHeight(150)

        popular_templates = self.template_manager.get_popular_templates()
        for template in popular_templates:
            item = QListWidgetItem(f" {template.name}")
            item.setToolTip(template.description)
            item.setData(Qt.UserRole, template.template_id)
            self.template_list.addItem(item)

        template_layout.addWidget(self.template_list)
        layout.addWidget(template_group)

        # 连接信号
        self.template_mode.toggled.connect(self._on_template_mode_toggled)
        self.template_list.itemDoubleClicked.connect(self._on_template_selected)

    def _on_template_mode_toggled(self, checked: bool):
        """模板模式切换"""
        self.template_list.setEnabled(checked)

    def _on_template_selected(self, item: QListWidgetItem):
        """模板选择"""
        template_id = item.data(Qt.UserRole)
        self.wizard().setProperty("selected_template", template_id)
        self.wizard().next()

    def get_selected_mode(self) -> ImportMode:
        """获取选择的模式"""
        button_id = self.mode_group.checkedId()
        if button_id == ImportMode.QUICK.value:
            return ImportMode.QUICK
        elif button_id == ImportMode.GUIDED.value:
            return ImportMode.GUIDED
        else:
            return ImportMode.TEMPLATE

    def nextId(self) -> int:
        """下一页ID"""
        mode = self.get_selected_mode()
        if mode == ImportMode.TEMPLATE and self.template_list.currentItem():
            return WorkflowStep.PREVIEW.value
        else:
            return WorkflowStep.DATA_SOURCE.value


class DataSourcePage(QWizardPage):
    """数据源选择页面"""

    def __init__(self):
        super().__init__()
        self.setTitle("选择数据源")
        self.setSubTitle("选择要导入的数据文件或数据源")

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 数据源类型选择
        source_group = QGroupBox("数据源类型")
        source_layout = QGridLayout(source_group)

        self.source_group = QButtonGroup()

        # CSV文件
        self.csv_radio = QRadioButton("CSV文件")
        self.csv_radio.setChecked(True)
        self.csv_radio.setIcon(QIcon("🗄️"))

        # Excel文件
        self.excel_radio = QRadioButton("Excel文件")
        self.excel_radio.setIcon(QIcon(""))

        # 数据库
        self.db_radio = QRadioButton("数据库")
        self.db_radio.setIcon(QIcon("🗄️"))

        # API接口
        self.api_radio = QRadioButton("API接口")
        self.api_radio.setIcon(QIcon(""))

        self.source_group.addButton(self.csv_radio, DataSourceType.CSV_FILE.value)
        self.source_group.addButton(self.excel_radio, DataSourceType.EXCEL_FILE.value)
        self.source_group.addButton(self.db_radio, DataSourceType.DATABASE.value)
        self.source_group.addButton(self.api_radio, DataSourceType.API.value)

        source_layout.addWidget(self.csv_radio, 0, 0)
        source_layout.addWidget(self.excel_radio, 0, 1)
        source_layout.addWidget(self.db_radio, 1, 0)
        source_layout.addWidget(self.api_radio, 1, 1)

        layout.addWidget(source_group)

        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QHBoxLayout(file_group)

        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("请选择数据文件...")

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._browse_file)

        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.browse_btn)

        layout.addWidget(file_group)

        # 快速预览
        preview_group = QGroupBox("快速预览")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(150)
        self.preview_text.setPlaceholderText("选择文件后将显示数据预览...")

        preview_layout.addWidget(self.preview_text)
        layout.addWidget(preview_group)

        # 连接信号
        self.source_group.buttonToggled.connect(self._on_source_type_changed)
        self.file_path.textChanged.connect(self._on_file_path_changed)

    def _browse_file(self):
        """浏览文件"""
        source_type = self.get_selected_source_type()

        if source_type == DataSourceType.CSV_FILE:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择CSV文件", "", "CSV文件 (*.csv);;所有文件 (*)"
            )
        elif source_type == DataSourceType.EXCEL_FILE:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择Excel文件", "", "Excel文件 (*.xlsx *.xls);;所有文件 (*)"
            )
        else:
            return

        if file_path:
            self.file_path.setText(file_path)

    def _on_source_type_changed(self):
        """数据源类型变化"""
        source_type = self.get_selected_source_type()

        # 根据数据源类型调整UI
        is_file_source = source_type in [DataSourceType.CSV_FILE, DataSourceType.EXCEL_FILE]
        self.file_path.setEnabled(is_file_source)
        self.browse_btn.setEnabled(is_file_source)

        if not is_file_source:
            self.file_path.clear()
            self.preview_text.clear()

    def _on_file_path_changed(self, path: str):
        """文件路径变化"""
        if path and path.strip():
            self._load_file_preview(path)

    def _load_file_preview(self, file_path: str):
        """加载文件预览"""
        try:
            # 简单的文件预览
            with open(file_path, 'r', encoding='utf-8') as f:
                preview_lines = []
                for i, line in enumerate(f):
                    if i >= 10:  # 只显示前10行
                        break
                    preview_lines.append(line.strip())

                self.preview_text.setPlainText('\n'.join(preview_lines))

        except Exception as e:
            self.preview_text.setPlainText(f"预览失败: {str(e)}")

    def get_selected_source_type(self) -> DataSourceType:
        """获取选择的数据源类型"""
        button_id = self.source_group.checkedId()
        for source_type in DataSourceType:
            if source_type.value == button_id:
                return source_type
        return DataSourceType.CSV_FILE

    def get_file_path(self) -> str:
        """获取文件路径"""
        return self.file_path.text().strip()

    def isComplete(self) -> bool:
        """页面是否完成"""
        source_type = self.get_selected_source_type()

        if source_type in [DataSourceType.CSV_FILE, DataSourceType.EXCEL_FILE]:
            return bool(self.get_file_path())
        else:
            return True  # 其他类型暂时返回True


class QuickConfigPage(QWizardPage):
    """快速配置页面"""

    def __init__(self):
        super().__init__()
        self.setTitle("快速配置")
        self.setSubTitle("系统已自动检测配置，您可以进行微调")

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 自动检测结果
        detect_group = QGroupBox("自动检测结果")
        detect_layout = QFormLayout(detect_group)

        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["K线数据", "财务数据", "实时行情", "自定义"])

        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["日线", "周线", "月线", "分钟线", "tick"])

        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "GBK", "GB2312", "自动检测"])

        detect_layout.addRow("数据类型:", self.data_type_combo)
        detect_layout.addRow("数据频率:", self.frequency_combo)
        detect_layout.addRow("文件编码:", self.encoding_combo)

        layout.addWidget(detect_group)

        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout(advanced_group)

        self.auto_validation = QCheckBox("启用数据质量自动验证")
        self.auto_validation.setChecked(True)

        self.skip_errors = QCheckBox("跳过错误行继续导入")
        self.skip_errors.setChecked(True)

        self.create_backup = QCheckBox("导入前创建数据备份")

        advanced_layout.addWidget(self.auto_validation)
        advanced_layout.addWidget(self.skip_errors)
        advanced_layout.addWidget(self.create_backup)

        layout.addWidget(advanced_group)

        # 预设配置
        preset_group = QGroupBox("预设配置")
        preset_layout = QHBoxLayout(preset_group)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "默认配置",
            "高质量模式",
            "快速模式",
            "兼容模式"
        ])

        self.save_preset_btn = QPushButton("保存为预设")

        preset_layout.addWidget(QLabel("选择预设:"))
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.save_preset_btn)
        preset_layout.addStretch()

        layout.addWidget(preset_group)

        # 连接信号
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        self.save_preset_btn.clicked.connect(self._save_preset)

    def _on_preset_changed(self, preset_name: str):
        """预设配置变化"""
        if preset_name == "高质量模式":
            self.auto_validation.setChecked(True)
            self.skip_errors.setChecked(False)
            self.create_backup.setChecked(True)
        elif preset_name == "快速模式":
            self.auto_validation.setChecked(False)
            self.skip_errors.setChecked(True)
            self.create_backup.setChecked(False)
        elif preset_name == "兼容模式":
            self.encoding_combo.setCurrentText("自动检测")
            self.skip_errors.setChecked(True)

    def _save_preset(self):
        """保存预设"""
        # 这里可以实现保存用户自定义预设的逻辑
        QMessageBox.information(self, "提示", "预设配置已保存")

    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return {
            'data_type': self.data_type_combo.currentText(),
            'frequency': self.frequency_combo.currentText(),
            'encoding': self.encoding_combo.currentText(),
            'auto_validation': self.auto_validation.isChecked(),
            'skip_errors': self.skip_errors.isChecked(),
            'create_backup': self.create_backup.isChecked(),
            'preset': self.preset_combo.currentText()
        }


class PreviewPage(QWizardPage):
    """预览页面"""

    def __init__(self):
        super().__init__()
        self.setTitle("数据预览")
        self.setSubTitle("预览即将导入的数据，确认无误后开始导入")

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 预览信息
        info_group = QGroupBox("导入信息")
        info_layout = QFormLayout(info_group)

        self.source_label = QLabel()
        self.type_label = QLabel()
        self.records_label = QLabel()
        self.size_label = QLabel()

        info_layout.addRow("数据源:", self.source_label)
        info_layout.addRow("数据类型:", self.type_label)
        info_layout.addRow("记录数:", self.records_label)
        info_layout.addRow("文件大小:", self.size_label)

        layout.addWidget(info_group)

        # 数据预览
        preview_group = QGroupBox("数据预览 (前20行)")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setFont(QFont("Consolas", 9))

        preview_layout.addWidget(self.preview_text)
        layout.addWidget(preview_group)

        # 质量检查结果
        quality_group = QGroupBox("数据质量检查")
        quality_layout = QVBoxLayout(quality_group)

        self.quality_text = QTextEdit()
        self.quality_text.setMaximumHeight(100)

        quality_layout.addWidget(self.quality_text)
        layout.addWidget(quality_group)

    def update_preview(self, source_path: str, config: Dict[str, Any]):
        """更新预览"""
        try:
            # 更新基本信息
            self.source_label.setText(source_path)
            self.type_label.setText(config.get('data_type', '未知'))

            # 模拟数据预览
            self.records_label.setText("1,234 条")
            self.size_label.setText("2.5 MB")

            # 模拟预览内容
            preview_content = """日期,开盘价,最高价,最低价,收盘价,成交量
2024-01-01,100.50,102.30,99.80,101.20,1500000
2024-01-02,101.20,103.50,100.90,102.80,1800000
2024-01-03,102.80,104.20,102.10,103.50,2100000
..."""

            self.preview_text.setPlainText(preview_content)

            # 模拟质量检查结果
            quality_result = """数据完整性: 100%
格式正确性: 99.8%
  发现 3 个异常值
时间序列连续性: 正常"""

            self.quality_text.setPlainText(quality_result)

        except Exception as e:
            logger.error(f"更新预览失败: {e}")


class ExecutionPage(QWizardPage):
    """执行页面"""

    def __init__(self):
        super().__init__()
        self.setTitle("正在导入")
        self.setSubTitle("请稍候，正在导入数据...")

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 进度显示
        progress_group = QGroupBox("导入进度")
        progress_layout = QVBoxLayout(progress_group)

        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)

        self.current_task = QLabel("准备开始...")
        self.current_task.setAlignment(Qt.AlignCenter)

        progress_layout.addWidget(QLabel("总体进度:"))
        progress_layout.addWidget(self.overall_progress)
        progress_layout.addWidget(self.current_task)

        layout.addWidget(progress_group)

        # 详细日志
        log_group = QGroupBox("导入日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 9))

        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        # 控制按钮
        control_layout = QHBoxLayout()

        self.pause_btn = QPushButton("暂停")
        self.cancel_btn = QPushButton("取消")

        control_layout.addStretch()
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.cancel_btn)

        layout.addLayout(control_layout)

    def start_import(self, config: Dict[str, Any]):
        """开始导入"""
        # 模拟导入过程
        self.simulate_import()

    def simulate_import(self):
        """模拟导入过程"""
        # 这里应该调用实际的导入逻辑
        # 为了演示，使用定时器模拟进度
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_progress)
        self.progress = 0
        self.timer.start(100)

    def _update_progress(self):
        """更新进度"""
        self.progress += 2
        self.overall_progress.setValue(self.progress)

        if self.progress <= 20:
            self.current_task.setText("正在验证数据格式...")
        elif self.progress <= 40:
            self.current_task.setText("正在解析数据...")
        elif self.progress <= 60:
            self.current_task.setText("正在执行质量检查...")
        elif self.progress <= 80:
            self.current_task.setText("正在写入数据库...")
        elif self.progress <= 100:
            self.current_task.setText("正在创建索引...")

        # 添加日志
        if self.progress % 10 == 0:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_msg = f"[{timestamp}] 已处理 {self.progress}% 的数据\n"
            self.log_text.append(log_msg)

        if self.progress >= 100:
            self.timer.stop()
            self.current_task.setText("导入完成！")
            self.wizard().next()


class CompletionPage(QWizardPage):
    """完成页面"""

    def __init__(self):
        super().__init__()
        self.setTitle("导入完成")
        self.setSubTitle("数据导入已成功完成")

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 成功图标和消息
        success_layout = QHBoxLayout()

        success_icon = QLabel("[SUCCESS]")
        success_icon.setFont(QFont("Arial", 48))
        success_icon.setAlignment(Qt.AlignCenter)

        success_msg = QLabel("数据导入成功完成！")
        success_msg.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        success_msg.setAlignment(Qt.AlignCenter)

        success_layout.addWidget(success_icon)
        success_layout.addWidget(success_msg)

        layout.addLayout(success_layout)

        # 导入结果
        result_group = QGroupBox("导入结果")
        result_layout = QFormLayout(result_group)

        self.imported_records = QLabel("1,234 条")
        self.failed_records = QLabel("0 条")
        self.import_time = QLabel("2 分 35 秒")
        self.data_quality = QLabel("优秀 (98.5%)")

        result_layout.addRow("成功导入:", self.imported_records)
        result_layout.addRow("失败记录:", self.failed_records)
        result_layout.addRow("导入耗时:", self.import_time)
        result_layout.addRow("数据质量:", self.data_quality)

        layout.addWidget(result_group)

        # 后续操作
        action_group = QGroupBox("后续操作")
        action_layout = QVBoxLayout(action_group)

        self.view_data_btn = QPushButton("查看导入的数据")
        self.quality_report_btn = QPushButton("查看质量报告")
        self.save_template_btn = QPushButton("保存为模板")

        action_layout.addWidget(self.view_data_btn)
        action_layout.addWidget(self.quality_report_btn)
        action_layout.addWidget(self.save_template_btn)

        layout.addWidget(action_group)


class SimplifiedImportWizard(QWizard):
    """简化导入向导"""

    # 信号定义
    import_completed = pyqtSignal(dict)  # 导入完成信号
    import_cancelled = pyqtSignal()      # 导入取消信号

    def __init__(self, parent=None):
        super().__init__(parent)

        self.template_manager = TemplateManager()
        self.workflow_config = WorkflowConfig()

        self.setWindowTitle("数据导入向导")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.HaveHelpButton, False)
        self.setMinimumSize(800, 600)

        self.setup_pages()
        self.setup_connections()

    def setup_pages(self):
        """设置页面"""
        # 添加页面
        self.welcome_page = WelcomePage(self.template_manager)
        self.data_source_page = DataSourcePage()
        self.quick_config_page = QuickConfigPage()
        self.preview_page = PreviewPage()
        self.execution_page = ExecutionPage()
        self.completion_page = CompletionPage()

        # 设置页面ID
        self.setPage(WorkflowStep.WELCOME.value, self.welcome_page)
        self.setPage(WorkflowStep.DATA_SOURCE.value, self.data_source_page)
        self.setPage(WorkflowStep.QUICK_CONFIG.value, self.quick_config_page)
        self.setPage(WorkflowStep.PREVIEW.value, self.preview_page)
        self.setPage(WorkflowStep.EXECUTION.value, self.execution_page)
        self.setPage(WorkflowStep.COMPLETION.value, self.completion_page)

        # 设置起始页面
        self.setStartId(WorkflowStep.WELCOME.value)

    def setup_connections(self):
        """设置连接"""
        self.currentIdChanged.connect(self._on_page_changed)
        self.finished.connect(self._on_wizard_finished)

    def _on_page_changed(self, page_id: int):
        """页面变化处理"""
        try:
            if page_id == WorkflowStep.PREVIEW.value:
                # 更新预览页面
                source_path = self.data_source_page.get_file_path()
                config = self.quick_config_page.get_config()
                self.preview_page.update_preview(source_path, config)

            elif page_id == WorkflowStep.EXECUTION.value:
                # 开始执行导入
                config = self._collect_config()
                self.execution_page.start_import(config)

        except Exception as e:
            logger.error(f"页面变化处理失败: {e}")

    def _collect_config(self) -> Dict[str, Any]:
        """收集配置"""
        config = {
            'import_mode': self.welcome_page.get_selected_mode().value,
            'source_type': self.data_source_page.get_selected_source_type().value,
            'source_path': self.data_source_page.get_file_path(),
            'quick_config': self.quick_config_page.get_config(),
            'timestamp': datetime.now().isoformat()
        }

        # 如果使用模板
        template_id = self.property("selected_template")
        if template_id:
            template = self.template_manager.use_template(template_id)
            if template:
                config['template'] = {
                    'id': template.template_id,
                    'name': template.name,
                    'config': template.config
                }

        return config

    def _on_wizard_finished(self, result: int):
        """向导完成处理"""
        if result == QWizard.Accepted:
            config = self._collect_config()
            self.import_completed.emit(config)
        else:
            self.import_cancelled.emit()


class WorkflowManager(QObject):
    """工作流管理器"""

    # 信号定义
    workflow_started = pyqtSignal(str)  # workflow_type
    workflow_completed = pyqtSignal(dict)  # result
    workflow_cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.template_manager = TemplateManager()
        self.active_workflows: Dict[str, QWizard] = {}
        self.workflow_history: List[Dict[str, Any]] = []

        logger.info("工作流管理器已初始化")

    def start_import_workflow(self, parent=None) -> SimplifiedImportWizard:
        """启动导入工作流"""
        try:
            wizard = SimplifiedImportWizard(parent)

            # 连接信号
            wizard.import_completed.connect(self._on_workflow_completed)
            wizard.import_cancelled.connect(self._on_workflow_cancelled)

            # 记录活跃工作流
            workflow_id = f"import_{len(self.active_workflows)}"
            self.active_workflows[workflow_id] = wizard

            # 显示向导
            wizard.show()

            self.workflow_started.emit("import")
            logger.info("导入工作流已启动")

            return wizard

        except Exception as e:
            logger.error(f"启动导入工作流失败: {e}")
            return None

    def _on_workflow_completed(self, result: Dict[str, Any]):
        """工作流完成处理"""
        try:
            # 记录历史
            self.workflow_history.append({
                'type': 'import',
                'result': result,
                'completed_at': datetime.now(),
                'success': True
            })

            # 清理活跃工作流
            self._cleanup_completed_workflow()

            self.workflow_completed.emit(result)
            logger.info("导入工作流已完成")

        except Exception as e:
            logger.error(f"处理工作流完成失败: {e}")

    def _on_workflow_cancelled(self):
        """工作流取消处理"""
        try:
            # 记录历史
            self.workflow_history.append({
                'type': 'import',
                'result': None,
                'completed_at': datetime.now(),
                'success': False,
                'cancelled': True
            })

            # 清理活跃工作流
            self._cleanup_completed_workflow()

            self.workflow_cancelled.emit()
            logger.info("导入工作流已取消")

        except Exception as e:
            logger.error(f"处理工作流取消失败: {e}")

    def _cleanup_completed_workflow(self):
        """清理已完成的工作流"""
        completed_workflows = []

        for workflow_id, wizard in self.active_workflows.items():
            if not wizard.isVisible():
                completed_workflows.append(workflow_id)

        for workflow_id in completed_workflows:
            del self.active_workflows[workflow_id]

    def get_template_manager(self) -> TemplateManager:
        """获取模板管理器"""
        return self.template_manager

    def get_workflow_statistics(self) -> Dict[str, Any]:
        """获取工作流统计"""
        try:
            total_workflows = len(self.workflow_history)
            successful_workflows = sum(1 for w in self.workflow_history if w.get('success', False))
            cancelled_workflows = sum(1 for w in self.workflow_history if w.get('cancelled', False))

            return {
                'total_workflows': total_workflows,
                'successful_workflows': successful_workflows,
                'cancelled_workflows': cancelled_workflows,
                'success_rate': successful_workflows / total_workflows if total_workflows > 0 else 0,
                'active_workflows': len(self.active_workflows),
                'available_templates': len(self.template_manager.templates)
            }

        except Exception as e:
            logger.error(f"获取工作流统计失败: {e}")
            return {'error': str(e)}


# 全局实例
workflow_manager = WorkflowManager()


def get_workflow_manager() -> WorkflowManager:
    """获取工作流管理器实例"""
    return workflow_manager


def start_simplified_import(parent=None) -> SimplifiedImportWizard:
    """启动简化导入工作流的便捷函数"""
    return get_workflow_manager().start_import_workflow(parent)
