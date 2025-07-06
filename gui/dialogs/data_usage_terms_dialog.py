"""
数据使用条款对话框模块
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataUsageTermsDialog(QDialog):
    """数据使用条款对话框"""

    def __init__(self, parent=None, show_agreement=False):
        super().__init__(parent)
        self.show_agreement = show_agreement
        self.user_agreed = False
        self.setWindowTitle("数据使用条款")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.load_terms()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("HIkyuu-UI 数据使用条款")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #007bff;
                padding: 10px;
                text-align: center;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 条款内容显示区域
        self.terms_text = QTextEdit()
        self.terms_text.setReadOnly(True)
        self.terms_text.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(self.terms_text)

        # 如果需要显示同意选项
        if self.show_agreement:
            # 同意复选框
            self.agree_checkbox = QCheckBox("我已阅读并同意上述数据使用条款")
            self.agree_checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 12px;
                    font-weight: bold;
                    padding: 10px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)
            layout.addWidget(self.agree_checkbox)

            # 按钮布局
            button_layout = QHBoxLayout()

            self.agree_button = QPushButton("同意并继续")
            self.agree_button.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                }
            """)
            self.agree_button.setEnabled(False)

            self.disagree_button = QPushButton("不同意")
            self.disagree_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)

            button_layout.addStretch()
            button_layout.addWidget(self.disagree_button)
            button_layout.addWidget(self.agree_button)
            layout.addLayout(button_layout)

            # 连接信号
            self.agree_checkbox.toggled.connect(self.on_checkbox_toggled)
            self.agree_button.clicked.connect(self.on_agree_clicked)
            self.disagree_button.clicked.connect(self.on_disagree_clicked)

        else:
            # 只显示关闭按钮
            button_layout = QHBoxLayout()
            close_button = QPushButton("关闭")
            close_button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            layout.addLayout(button_layout)

            close_button.clicked.connect(self.accept)

    def load_terms(self):
        """加载使用条款内容"""
        try:
            # 查找条款文件
            terms_file = Path(__file__).parent.parent.parent / "DATA_USAGE_TERMS.md"

            if terms_file.exists():
                with open(terms_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 转换Markdown为HTML显示
                html_content = self.markdown_to_html(content)
                self.terms_text.setHtml(html_content)
            else:
                # 如果文件不存在，显示默认条款
                self.terms_text.setHtml(self.get_default_terms())

        except Exception as e:
            logger.error(f"加载使用条款失败: {str(e)}")
            self.terms_text.setHtml(self.get_default_terms())

    def markdown_to_html(self, markdown_text: str) -> str:
        """简单的Markdown到HTML转换"""
        html = markdown_text

        # 转换标题
        html = html.replace('# ', '<h1>').replace('\n', '</h1>\n', 1)
        html = html.replace('## ', '<h2>').replace('\n', '</h2>\n')
        html = html.replace('### ', '<h3>').replace('\n', '</h3>\n')
        html = html.replace('#### ', '<h4>').replace('\n', '</h4>\n')

        # 转换粗体
        import re
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)

        # 转换代码块
        html = re.sub(r'```python\n(.*?)\n```',
                      r'<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;"><code>\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'```\n(.*?)\n```', r'<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;"><code>\1</code></pre>', html, flags=re.DOTALL)

        # 转换列表
        html = re.sub(r'^- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)

        # 转换段落
        paragraphs = html.split('\n\n')
        html_paragraphs = []
        for p in paragraphs:
            if p.strip() and not p.startswith('<'):
                html_paragraphs.append(f'<p>{p.strip()}</p>')
            else:
                html_paragraphs.append(p)

        html = '\n\n'.join(html_paragraphs)

        # 添加样式
        styled_html = f"""
        <style>
            body {{ font-family: 'Microsoft YaHei', sans-serif; line-height: 1.6; font-size:15px;}}
            h1 {{ color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
            h2 {{ color: #0056b3; margin-top: 30px; }}
            h3 {{ color: #17a2b8; margin-top: 20px; }}
            h4 {{ color: #28a745; margin-top: 15px; }}
            ul {{ margin: 10px 0; padding-left: 20px; }}
            li {{ margin: 5px 0; }}
            code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px; }}
            pre {{ margin: 15px 0; }}
            .highlight {{ background-color: #fff3cd; padding: 5px; border-radius: 3px; }}
        </style>
        {html}
        """

        return styled_html

    def get_default_terms(self) -> str:
        """获取默认使用条款"""
        return """
        <h1>HIkyuu-UI 数据使用条款</h1>
        
        <h2>数据使用声明</h2>
        
        <h3>1. 使用目的限制</h3>
        <p><strong>允许的使用目的：</strong></p>
        <ul>
            <li>个人投资研究：用于个人投资决策分析和研究</li>
            <li>学术研究：用于金融量化相关的学术研究</li>
            <li>教育学习：用于量化交易技术的学习和教育</li>
            <li>非商业分析：用于非营利性的数据分析和回测</li>
        </ul>
        
        <p><strong>禁止的使用目的：</strong></p>
        <ul>
            <li>商业转售：禁止将获取的数据进行商业转售</li>
            <li>大规模爬取：禁止进行大规模、高频率的数据爬取</li>
            <li>恶意使用：禁止用于任何可能损害数据提供方利益的行为</li>
            <li>版权侵犯：禁止侵犯数据提供方的知识产权</li>
        </ul>
        
        <h3>2. 用户责任</h3>
        <ul>
            <li>遵守法律法规：用户应遵守所在国家和地区的相关法律法规</li>
            <li>遵守网站条款：用户应遵守各数据提供方的网站使用条款</li>
            <li>合理使用频率：用户应控制数据请求频率，避免对数据提供方造成负担</li>
            <li>数据准确性：用户应理解数据可能存在延迟或错误，需自行验证</li>
        </ul>
        
        <h3>3. 免责声明</h3>
        <ul>
            <li>HIkyuu-UI不保证所提供数据的准确性、完整性或时效性</li>
            <li>HIkyuu-UI仅为数据分析工具，不构成投资建议</li>
            <li>用户的投资决策应基于自己的判断，并承担相应风险</li>
        </ul>
        
        <p><strong>重要提醒：</strong>使用HIkyuu-UI即表示您已阅读、理解并同意遵守本使用条款。</p>
        """

    def on_checkbox_toggled(self, checked: bool):
        """复选框状态改变时的处理"""
        self.agree_button.setEnabled(checked)

    def on_agree_clicked(self):
        """用户点击同意按钮"""
        if self.agree_checkbox.isChecked():
            self.user_agreed = True
            self.accept()
        else:
            QMessageBox.warning(self, "提示", "请先勾选同意条款")

    def on_disagree_clicked(self):
        """用户点击不同意按钮"""
        self.user_agreed = False
        self.reject()

    def is_agreed(self) -> bool:
        """检查用户是否同意条款"""
        return self.user_agreed

    @staticmethod
    def show_terms(parent=None) -> None:
        """显示使用条款（仅查看）"""
        dialog = DataUsageTermsDialog(parent, show_agreement=False)
        dialog.exec_()

    @staticmethod
    def request_agreement(parent=None) -> bool:
        """请求用户同意条款"""
        dialog = DataUsageTermsDialog(parent, show_agreement=True)
        result = dialog.exec_()
        return result == QDialog.Accepted and dialog.is_agreed()


class DataUsageManager:
    """数据使用管理器"""

    def __init__(self):
        self.settings = QSettings("HIkyuu", "DataUsage")

    def has_agreed_to_terms(self) -> bool:
        """检查用户是否已同意条款"""
        return self.settings.value("terms_agreed", False, type=bool)

    def set_terms_agreed(self, agreed: bool):
        """设置用户同意条款状态"""
        self.settings.setValue("terms_agreed", agreed)
        self.settings.setValue("terms_agreed_time", QDateTime.currentDateTime())

    def get_agreement_time(self) -> QDateTime:
        """获取用户同意条款的时间"""
        return self.settings.value("terms_agreed_time", QDateTime(), type=QDateTime)

    def check_and_request_agreement(self, parent=None) -> bool:
        """检查并请求用户同意条款"""
        if not self.has_agreed_to_terms():
            # 显示条款并请求同意
            agreed = DataUsageTermsDialog.request_agreement(parent)
            if agreed:
                self.set_terms_agreed(True)
                return True
            else:
                return False
        return True

    def show_terms_dialog(self, parent=None):
        """显示条款对话框"""
        DataUsageTermsDialog.show_terms(parent)
