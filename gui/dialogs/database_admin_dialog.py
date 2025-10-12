from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QTableView, QPushButton, QMessageBox, QLineEdit, QLabel, QFileDialog, QStyledItemDelegate, QSpinBox, QDoubleSpinBox, QDateEdit, QCheckBox, QComboBox, QInputDialog, QSplitter, QHeaderView, QWidget, QAbstractItemView, QGroupBox, QTextEdit
from PyQt5.QtSql import QSqlDatabase, QSqlTableModel
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QAbstractTableModel, QVariant
from PyQt5.QtGui import QFont, QColor, QBrush
import os
import csv
import json
import requests
import time
from loguru import logger
import glob
from datetime import datetime


class DatabaseScanThread(QThread):
    """数据库扫描线程"""
    scan_completed = pyqtSignal(dict)
    scan_error = pyqtSignal(str)

    def run(self):
        """执行数据库扫描 - 递归扫描db目录最大5层深度"""
        try:
            databases = {
                'sqlite': [],
                'duckdb': []
            }

            # 扫描db目录
            db_dir = os.path.join(os.getcwd(), 'db')
            if not os.path.exists(db_dir):
                logger.warning(f"数据库目录不存在: {db_dir}")
                self.scan_completed.emit(databases)
                return

            logger.info(f"开始递归扫描数据库目录: {db_dir}")

            # 递归扫描数据库文件，最大深度5层
            self._recursive_scan_databases(db_dir, databases, current_depth=0, max_depth=5)

            logger.info(f"数据库扫描完成: SQLite({len(databases['sqlite'])}个), DuckDB({len(databases['duckdb'])}个)")
            self.scan_completed.emit(databases)

        except Exception as e:
            logger.error(f"数据库扫描失败: {e}")
            self.scan_error.emit(str(e))

    def _recursive_scan_databases(self, directory, databases, current_depth=0, max_depth=5):
        """递归扫描目录中的数据库文件"""
        if current_depth > max_depth:
            logger.debug(f"达到最大扫描深度 {max_depth}，跳过目录: {directory}")
            return

        try:
            logger.debug(f"扫描目录 (深度{current_depth}): {directory}")

            # 扫描当前目录中的文件
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)

                if os.path.isfile(item_path):
                    # 检查是否为数据库文件
                    self._check_database_file(item_path, databases)
                elif os.path.isdir(item_path):
                    # 递归扫描子目录
                    self._recursive_scan_databases(item_path, databases, current_depth + 1, max_depth)

        except PermissionError:
            logger.warning(f"没有权限访问目录: {directory}")
        except Exception as e:
            logger.warning(f"扫描目录失败 {directory}: {e}")

    def _check_database_file(self, file_path, databases):
        """检查文件是否为数据库文件并添加到列表"""
        try:
            # 检查文件扩展名
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.db', '.sqlite', '.sqlite3', '.duckdb']:
                return

            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size < 512:  # 小于512字节的文件可能不是有效数据库
                logger.debug(f"跳过过小的文件: {file_path} ({file_size} bytes)")
                return

            # 获取相对路径（相对于项目根目录）
            relative_path = os.path.relpath(file_path, os.getcwd())

            # 根据扩展名分类检查
            if ext in ['.db', '.sqlite', '.sqlite3']:
                if self._is_sqlite_file(file_path):
                    databases['sqlite'].append({
                        'path': file_path,
                        'relative_path': relative_path,
                        'name': os.path.basename(file_path),
                        'size': self._format_file_size(file_size),
                        'directory': os.path.dirname(relative_path)
                    })
                    logger.debug(f"发现SQLite数据库: {relative_path}")
            elif ext == '.duckdb':
                if self._is_duckdb_file(file_path):
                    databases['duckdb'].append({
                        'path': file_path,
                        'relative_path': relative_path,
                        'name': os.path.basename(file_path),
                        'size': self._format_file_size(file_size),
                        'directory': os.path.dirname(relative_path)
                    })
                    logger.debug(f"发现DuckDB数据库: {relative_path}")

        except Exception as e:
            logger.warning(f"检查文件失败 {file_path}: {e}")

    def _is_sqlite_file(self, file_path):
        """检查文件是否为有效的SQLite数据库"""
        try:
            import sqlite3
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            conn.close()
            return True
        except Exception:
            return False

    def _is_duckdb_file(self, file_path):
        """检查文件是否为有效的DuckDB数据库"""
        try:
            import duckdb
            conn = duckdb.connect(file_path)
            conn.execute("SHOW TABLES;")
            conn.close()
            return True
        except Exception:
            return False

    def _format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class TypeDelegate(QStyledItemDelegate):
    def __init__(self, field_types, parent=None, field_permissions=None, table_name=None):
        super().__init__(parent)
        self.field_types = field_types
        self.field_permissions = field_permissions or {}
        self.table_name = table_name

    def createEditor(self, parent, option, index):
        field = index.model().headerData(index.column(), Qt.Horizontal)
        # 字段级只读限制
        if self.field_permissions.get(self.table_name, {}).get(field) == 'readonly':
            return None
        ftype = self.field_types.get(field, '').lower()
        if 'int' in ftype:
            editor = QSpinBox(parent)
            editor.setMinimum(-2**31)
            editor.setMaximum(2**31-1)
            return editor
        elif 'real' in ftype or 'float' in ftype or 'double' in ftype:
            editor = QDoubleSpinBox(parent)
            editor.setDecimals(6)
            editor.setMinimum(-1e12)
            editor.setMaximum(1e12)
            return editor
        elif 'date' in ftype:
            editor = QDateEdit(parent)
            editor.setCalendarPopup(True)
            editor.setDisplayFormat('yyyy-MM-dd')
            return editor
        elif 'bool' in ftype or 'tinyint(1)' in ftype:
            editor = QCheckBox(parent)
            return editor
        else:
            return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        field = index.model().headerData(index.column(), Qt.Horizontal)
        ftype = self.field_types.get(field, '').lower()
        if isinstance(editor, QSpinBox):
            editor.setValue(int(value) if value not in (None, '') else 0)
        elif isinstance(editor, QDoubleSpinBox):
            editor.setValue(float(value) if value not in (None, '') else 0.0)
        elif isinstance(editor, QDateEdit):
            if value:
                editor.setDate(QDate.fromString(str(value)[:10], 'yyyy-MM-dd'))
            else:
                editor.setDate(QDate.currentDate())
        elif isinstance(editor, QCheckBox):
            editor.setChecked(
                bool(int(value)) if value not in (None, '') else False)
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        field = model.headerData(index.column(), Qt.Horizontal)
        # 字段级只读限制
        if self.field_permissions.get(self.table_name, {}).get(field) == 'readonly':
            return
        ftype = self.field_types.get(field, '').lower()
        if isinstance(editor, QSpinBox):
            model.setData(index, editor.value())
        elif isinstance(editor, QDoubleSpinBox):
            model.setData(index, editor.value())
        elif isinstance(editor, QDateEdit):
            model.setData(index, editor.date().toString('yyyy-MM-dd'))
        elif isinstance(editor, QCheckBox):
            model.setData(index, 1 if editor.isChecked() else 0)
        else:
            super().setModelData(editor, model, index)


class TableDescriptionManager:
    """表描述管理器"""

    def __init__(self, system_db_path="db/factorweave_system.sqlite"):
        self.system_db_path = system_db_path

    def get_description(self, database_path, table_name):
        """获取表描述"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.system_db_path)
            cursor = conn.cursor()

            cursor.execute("""
            SELECT description, tags FROM table_descriptions 
            WHERE database_path = ? AND table_name = ?
            """, (database_path, table_name))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'description': result[0] or '',
                    'tags': result[1] or ''
                }
            else:
                return {'description': '', 'tags': ''}

        except Exception as e:
            logger.error(f"获取表描述失败: {e}")
            return {'description': '', 'tags': ''}

    def save_description(self, database_path, database_type, table_name, description, tags=''):
        """保存表描述"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.system_db_path)
            cursor = conn.cursor()

            cursor.execute("""
            INSERT OR REPLACE INTO table_descriptions 
            (database_path, database_type, table_name, description, tags, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (database_path, database_type, table_name, description, tags))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"保存表描述失败: {e}")
            return False

    def get_all_descriptions(self, database_path):
        """获取指定数据库的所有表描述"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.system_db_path)
            cursor = conn.cursor()

            cursor.execute("""
            SELECT table_name, description, tags FROM table_descriptions 
            WHERE database_path = ?
            """, (database_path,))

            results = cursor.fetchall()
            conn.close()

            return {row[0]: {'description': row[1], 'tags': row[2]} for row in results}

        except Exception as e:
            logger.error(f"获取所有表描述失败: {e}")
            return {}


class DatabaseAdminDialog(QDialog):
    def __init__(self, db_path, parent=None, mode='admin'):
        super().__init__(parent)
        self.field_permissions = {}  # 提前初始化，防止AttributeError
        self.setWindowTitle("数据库管理后台")
        self.resize(1000, 650)
        self.db_path = db_path
        self.mode = mode  # 'readonly', 'write', 'admin'
        self.current_table = None
        self.page_size = 50
        self.current_page = 0
        self.log = []

        # 慢SQL记录功能
        self.slow_query_threshold = 500  # 慢查询阈值(毫秒)
        self.slow_queries = []  # 慢查询记录

        # 数据库文件管理
        self.available_databases = {
            'sqlite': [],
            'duckdb': []
        }
        self.current_db_type = 'sqlite'  # 默认类型
        self.selected_db_path = db_path  # 当前选择的数据库路径

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 数据库连接区域 - 集成到顶部
        self._create_database_connection_panel(main_layout)

        # 功能按钮区域 - 移到顶部，优化布局
        self._create_function_buttons_panel(main_layout)

        # 主要内容区域
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧面板 - 表列表和描述
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 表列表
        self.table_list = QListWidget()
        self.table_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_list.setWordWrap(True)
        self.table_list.itemClicked.connect(self.load_table)
        # self.table_list.setMinimumWidth(140)
        # self.table_list.setMaximumWidth(320)
        # self.table_list.setFixedWidth(180)

        # 表描述面板
        description_panel = self._create_table_description_panel()

        # 添加到左侧布局
        left_layout.addWidget(QLabel("数据库表列表"))
        left_layout.addWidget(self.table_list, 1)  # 表列表占主要空间
        left_layout.addWidget(description_panel, 0)  # 描述面板固定高度

        # 右侧内容区
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)

        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("字段/内容搜索...支持模糊")
        self.search_edit.textChanged.connect(self.apply_search)
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_edit)
        right_layout.addLayout(search_layout)

        # 表格
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.ExtendedSelection)
        self.table_view.setFont(QFont("Consolas", 10))
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(False)
        self.table_view.setShowGrid(True)
        self.table_view.setWordWrap(False)
        self.table_view.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table_view.setVerticalScrollMode(QTableView.ScrollPerPixel)
        right_layout.addWidget(self.table_view, 8)

        # 动态表描述展示区域 - 替换固定的主题介绍
        self.dynamic_table_info = QLabel()
        self.dynamic_table_info.setStyleSheet("""
            QLabel {
                color: #1976D2;
                font-size: 13px;
                background: #E3F2FD;
                border: 1px solid #BBDEFB;
                border-radius: 6px;
                padding: 8px;
                margin: 4px;
            }
        """)
        self.dynamic_table_info.setWordWrap(True)
        self.dynamic_table_info.setVisible(False)
        right_layout.addWidget(self.dynamic_table_info)

        # 分页
        page_layout = QHBoxLayout()
        self.prev_btn = QPushButton("上一页")
        self.next_btn = QPushButton("下一页")
        self.page_label = QLabel()
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        page_layout.addWidget(self.prev_btn)
        page_layout.addWidget(self.page_label)
        page_layout.addWidget(self.next_btn)
        right_layout.addLayout(page_layout)

        # 添加到分割器
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_widget)

        # 设置分割条
        main_splitter.setSizes([180, 820])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)

        main_layout.addWidget(main_splitter, 1)

        # 初始化数据库连接
        self.connection_name = f"dbadmin_{int(time.time() * 1000)}"
        self.db = QSqlDatabase.addDatabase("QSQLITE", self.connection_name)
        self.db.setDatabaseName(self.db_path)
        self.db.open()
        tables = self.db.tables()
        self.table_list.addItems(tables)

        # 自动选择第一个表并显示描述
        if tables:
            first_item = self.table_list.item(0)
            if first_item:
                self.table_list.setCurrentItem(first_item)
                self.load_table(first_item)

    def _create_function_buttons_panel(self, main_layout):
        """创建功能按钮面板 - 优化UI并移到顶部"""
        # 创建按钮面板容器
        buttons_container = QWidget()
        buttons_container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 2px;
                margin: 2px;
            }
        """)
        container_layout = QVBoxLayout(buttons_container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(6)

        # 按钮样式
        button_style = """
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 2px;
                padding: 2px 2px;
                color: #495057;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #e9ecef;
            }
        """

        # 第一行：基础操作
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(4)

        self.add_btn = QPushButton("新增")
        self.del_btn = QPushButton("删除")
        self.edit_btn = QPushButton("编辑")
        self.save_btn = QPushButton("保存修改")
        self.refresh_btn = QPushButton("刷新")

        for btn in [self.add_btn, self.del_btn, self.edit_btn, self.save_btn, self.refresh_btn]:
            btn.setStyleSheet(button_style)
            row1_layout.addWidget(btn)

        row1_layout.addStretch()
        container_layout.addLayout(row1_layout)

        # # 第二行：数据操作
        # row2_layout = QHBoxLayout()
        # row2_layout.setSpacing(4)

        self.import_btn = QPushButton("导入CSV")
        self.export_btn = QPushButton("导出CSV")
        self.batch_btn = QPushButton("批量修改")
        self.perm_btn = QPushButton("字段权限管理")
        self.log_btn = QPushButton("查看权限变更日志")

        for btn in [self.import_btn, self.export_btn, self.batch_btn, self.perm_btn, self.log_btn]:
            btn.setStyleSheet(button_style)
            row1_layout.addWidget(btn)

        # row2_layout.addStretch()
        # container_layout.addLayout(row2_layout)

        # # 第三行：高级功能
        # row3_layout = QHBoxLayout()
        # row3_layout.setSpacing(4)

        self.upload_btn = QPushButton("上传权限到云端")
        self.download_btn = QPushButton("从云端拉取权限")
        self.schema_btn = QPushButton("表结构管理")
        self.stats_btn = QPushButton("数据统计")
        self.slow_sql_btn = QPushButton("慢SQL记录")

        for btn in [self.upload_btn, self.download_btn, self.schema_btn, self.stats_btn, self.slow_sql_btn]:
            btn.setStyleSheet(button_style)
            row1_layout.addWidget(btn)

        # 语言切换
        # self.lang_combo = QComboBox()
        # self.lang_combo.addItems(["中文", "English"])
        # self.lang_combo.currentTextChanged.connect(self.switch_language)
        # self.lang_combo.setStyleSheet("""
        #     QComboBox {
        #         background-color: #ffffff;
        #         border: 1px solid #ced4da;
        #         border-radius: 2px;
        #         padding: 2px 2px;
        #         min-height: 20px;
        #     }
        #     QComboBox:hover {
        #         border-color: #adb5bd;
        #     }
        #     QComboBox::drop-down {
        #         border: none;
        #     }
        #     QComboBox::down-arrow {
        #         width: 12px;
        #         height: 12px;
        #     }
        # """)

        # row3_layout.addStretch()
        # row3_layout.addWidget(QLabel("语言:"))
        # row3_layout.addWidget(self.lang_combo)
        # container_layout.addLayout(row3_layout)

        main_layout.addWidget(buttons_container)

        # 绑定事件
        self.add_btn.clicked.connect(self.add_row)
        self.del_btn.clicked.connect(self.del_row)
        self.edit_btn.clicked.connect(self.toggle_edit_mode)
        self.save_btn.clicked.connect(self.save_changes)
        self.refresh_btn.clicked.connect(self.refresh_table)
        self.import_btn.clicked.connect(self.import_csv)
        self.export_btn.clicked.connect(self.export_csv)
        self.batch_btn.clicked.connect(self.show_batch_modify)
        self.log_btn.clicked.connect(self.show_permission_log)
        self.perm_btn.clicked.connect(self.show_permission_manager)
        self.upload_btn.clicked.connect(self.upload_permissions_to_cloud)
        self.download_btn.clicked.connect(self.download_permissions_from_cloud)
        self.schema_btn.clicked.connect(self.show_schema_manager)
        self.stats_btn.clicked.connect(self.show_table_stats)
        self.slow_sql_btn.clicked.connect(self.show_slow_queries)

    def _create_table_description_panel(self):
        """创建表描述面板"""
        from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                                     QTextEdit, QLabel, QLineEdit, QPushButton)

        # 创建描述面板分组框
        desc_group = QGroupBox("表描述信息")
        desc_group.setFixedHeight(200)
        desc_layout = QVBoxLayout(desc_group)

        # 表名标签
        self.current_table_label = QLabel("当前表: 未选择")
        self.current_table_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        desc_layout.addWidget(self.current_table_label)

        # 标签输入
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(QLabel("标签:"))
        self.table_tags_edit = QLineEdit()
        self.table_tags_edit.setPlaceholderText("输入标签，用逗号分隔...")
        tags_layout.addWidget(self.table_tags_edit)
        desc_layout.addLayout(tags_layout)

        # 描述输入
        desc_layout.addWidget(QLabel("描述:"))
        self.table_description_edit = QTextEdit()
        self.table_description_edit.setPlaceholderText("输入表的详细描述...")
        self.table_description_edit.setMaximumHeight(80)
        desc_layout.addWidget(self.table_description_edit)

        # 按钮布局
        button_layout = QHBoxLayout()

        self.save_desc_btn = QPushButton("保存描述")
        self.save_desc_btn.clicked.connect(self._save_table_description)
        self.save_desc_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)

        self.clear_desc_btn = QPushButton("清空")
        self.clear_desc_btn.clicked.connect(self._clear_table_description)
        self.clear_desc_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        button_layout.addWidget(self.save_desc_btn)
        button_layout.addWidget(self.clear_desc_btn)
        button_layout.addStretch()

        desc_layout.addLayout(button_layout)

        return desc_group

    def _load_table_description(self, table_name):
        """加载表描述"""
        if not hasattr(self, 'description_manager'):
            self.description_manager = TableDescriptionManager()

        # 更新当前表标签
        self.current_table_label.setText(f"当前表: {table_name}")

        # 获取描述信息
        desc_info = self.description_manager.get_description(self.db_path, table_name)

        # 更新界面
        self.table_description_edit.setPlainText(desc_info['description'])
        self.table_tags_edit.setText(desc_info['tags'])

    def _save_table_description(self):
        """保存表描述"""
        if not self.current_table:
            QMessageBox.warning(self, "警告", "请先选择一个表")
            return

        if not hasattr(self, 'description_manager'):
            self.description_manager = TableDescriptionManager()

        description = self.table_description_edit.toPlainText().strip()
        tags = self.table_tags_edit.text().strip()

        # 确定数据库类型
        db_type = self.current_db_type if hasattr(self, 'current_db_type') else 'sqlite'

        if self.description_manager.save_description(
                self.db_path, db_type, self.current_table, description, tags):
            QMessageBox.information(self, "成功", f"表 '{self.current_table}' 的描述已保存")
            # 更新动态显示
            self._update_dynamic_table_info(self.current_table)
        else:
            QMessageBox.critical(self, "错误", "保存表描述失败")

    def _clear_table_description(self):
        """清空表描述"""
        self.table_description_edit.clear()
        self.table_tags_edit.clear()

    def _update_dynamic_table_info(self, table_name):
        """动态更新表描述信息显示"""
        if not hasattr(self, 'description_manager'):
            self.description_manager = TableDescriptionManager()

        # 获取表描述信息
        desc_info = self.description_manager.get_description(self.db_path, table_name)

        if desc_info['description']:
            # 如果有描述，显示描述信息
            info_text = f" 表: {table_name}\n"

            # 添加标签信息
            if desc_info['tags']:
                tags = desc_info['tags'].split(',')
                tag_text = ' '.join([f"#{tag.strip()}" for tag in tags if tag.strip()])
                info_text += f" 标签: {tag_text}\n"

            # 添加描述
            info_text += f" 描述: {desc_info['description']}"

            self.dynamic_table_info.setText(info_text)
            self.dynamic_table_info.setVisible(True)
        else:
            # 如果没有描述，显示默认提示
            default_info = f" 表: {table_name}\n 暂无描述信息，您可以在左侧面板添加表描述来帮助其他用户理解此表的用途。"
            self.dynamic_table_info.setText(default_info)
            self.dynamic_table_info.setVisible(True)

    def load_table(self, item):
        """加载表数据 - 支持 SQLite 和 DuckDB，并加载表描述"""
        if not item:
            return

        table_name = item.text()
        self.current_table = table_name

        # 加载表描述
        self._load_table_description(table_name)

        # 动态显示表描述信息
        self._update_dynamic_table_info(table_name)

        try:
            if self.current_db_type == 'duckdb':
                # DuckDB 处理
                if hasattr(self, '_duckdb_conn'):
                    # 获取表结构
                    schema_result = self._duckdb_conn.execute(f"DESCRIBE {table_name}").fetchall()

                    # 获取数据（分页）
                    offset = self.current_page * self.page_size
                    data_result = self._duckdb_conn.execute(
                        f"SELECT * FROM {table_name} LIMIT {self.page_size} OFFSET {offset}"
                    ).fetchall()

                    # 获取总行数
                    count_result = self._duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                    total_rows = count_result[0] if count_result else 0

                    # 创建自定义模型显示数据
                    self._create_duckdb_table_model(schema_result, data_result, total_rows)

            else:
                # SQLite 处理（原有逻辑）
                if hasattr(self, 'model'):
                    self.model.deleteLater()

                self.model = QSqlTableModel(self, self.db)
                self.model.setTable(table_name)
                self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
                self.model.select()

                self.table_view.setModel(self.model)

                # 更新分页信息
                total_rows = self.model.rowCount()

            # 更新页面信息
            total_pages = (total_rows + self.page_size - 1) // self.page_size
            self.page_label.setText(f"第 {self.current_page + 1} 页，共 {total_pages} 页，总计 {total_rows} 行")

            # 更新按钮状态
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < total_pages - 1)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载表 {table_name} 失败: {str(e)}")

    def refresh_table(self):
        table_name = self.current_table
        if not table_name:
            return
        self.model = QSqlTableModel(self, self.db)
        self.model.setTable(table_name)
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.select()
        # 字段类型与主键信息
        self.field_types = {}
        self.pk_fields = set()
        query = self.db.exec(f"PRAGMA table_info({table_name})")
        while query.next():
            name = query.value(1)
            ftype = query.value(2)
            pk = query.value(5)
            self.field_types[name] = ftype
            if pk:
                self.pk_fields.add(name)
        # 字段级权限适配
        perms = self.field_permissions.get(table_name, {})
        for col in range(self.model.columnCount()):
            name = self.model.headerData(col, Qt.Horizontal)
            if perms.get(name) == 'hidden':
                self.table_view.setColumnHidden(col, True)
            else:
                self.table_view.setColumnHidden(col, False)
        self.table_view.setModel(self.model)
        self.table_view.setItemDelegate(TypeDelegate(
            self.field_types, self.table_view, self.field_permissions, table_name))
        for col in range(self.model.columnCount()):
            name = self.model.headerData(col, Qt.Horizontal)
            if name in self.pk_fields:
                self.table_view.setColumnWidth(col, 120)
        self.apply_search()
        self.update_page_label()
        # 空数据提示
        if self.model.rowCount() == 0:
            label = QLabel("暂无数据", self.table_view)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #90A4AE; font-size: 16px;")
            self.table_view.setIndexWidget(self.model.index(0, 0), label)

    def add_row(self):
        if hasattr(self, 'model'):
            self.model.insertRow(self.model.rowCount())
            self.log.append(f"新增行于表 {self.current_table}")

    def del_row(self):
        if hasattr(self, 'model'):
            idxs = self.table_view.selectionModel().selectedRows()
            if not idxs:
                return
            if QMessageBox.question(self, "确认删除", f"确定要删除选中{len(idxs)}行吗？") == QMessageBox.Yes:
                for idx in sorted(idxs, key=lambda x: -x.row()):
                    self.model.removeRow(idx.row())
                self.log.append(f"批量删除{len(idxs)}行于表 {self.current_table}")

    def save_changes(self):
        if hasattr(self, 'model'):
            if not self.model.submitAll():
                QMessageBox.warning(
                    self, "保存失败", self.model.lastError().text())
            else:
                QMessageBox.information(self, "保存成功", "所有更改已保存！")
                self.log.append(f"保存更改于表 {self.current_table}")

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            for row in reader:
                self.model.insertRow(self.model.rowCount())
                for col, val in enumerate(row):
                    self.model.setData(self.model.index(
                        self.model.rowCount()-1, col), val)
        QMessageBox.information(self, "导入完成", "CSV数据已导入，记得保存！")
        self.log.append(f"导入CSV到表 {self.current_table}")

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出CSV", f"{self.current_table}.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            headers = [self.model.headerData(
                i, Qt.Horizontal) for i in range(self.model.columnCount())]
            writer.writerow(headers)
            for row in range(self.model.rowCount()):
                writer.writerow([self.model.data(self.model.index(row, col))
                                for col in range(self.model.columnCount())])
        QMessageBox.information(self, "导出完成", "CSV数据已导出！")
        self.log.append(f"导出CSV于表 {self.current_table}")

    def apply_search(self):
        if not hasattr(self, 'model') or not self.current_table:
            return
        text = self.search_edit.text().strip()
        if not text:
            self.model.setFilter("")
        else:
            filters = []
            for col in range(self.model.columnCount()):
                name = self.model.headerData(col, Qt.Horizontal)
                filters.append(f"{name} LIKE '%{text}%'")
            self.model.setFilter("OR ".join(filters))
        self.model.select()
        self.update_page_label()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_table()

    def next_page(self):
        self.current_page += 1
        self.refresh_table()

    def update_page_label(self):
        total = self.model.rowCount()
        self.page_label.setText(
            f"第{self.current_page+1}页 / 共{(total-1)//self.page_size+1}页  共{total}行")

    def show_log(self):
        if self.log_window is None:
            self.log_window = QDialog(self)
            self.log_window.setWindowTitle("操作日志")
            vbox = QVBoxLayout(self.log_window)
            self.log_text = QLineEdit()
            self.log_text.setReadOnly(True)
            vbox.addWidget(self.log_text)
            export_btn = QPushButton("导出日志")
            export_btn.clicked.connect(self.export_log)
            vbox.addWidget(export_btn)
            rollback_btn = QPushButton("撤销最近操作")
            rollback_btn.clicked.connect(self.rollback_last)
            vbox.addWidget(rollback_btn)
        self.log_text.setText("\n".join(self.log))
        self.log_window.exec_()

    def export_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "dbadmin_log.txt", "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.log))
            QMessageBox.information(self, "导出完成", "日志已导出！")

    def rollback_last(self):
        # 简单实现：撤销最近一次新增/删除/导入操作（仅内存，未保存前有效）
        if not self.log:
            QMessageBox.information(self, "无操作可撤销", "没有可撤销的操作！")
            return
        last = self.log[-1]
        if "新增行" in last:
            if hasattr(self, 'model'):
                self.model.removeRow(self.model.rowCount()-1)
                self.log.append("撤销："+last)
        elif "批量删除" in last:
            QMessageBox.information(self, "暂不支持批量回滚", "批量删除暂不支持自动回滚，请手动恢复。")
        elif "导入CSV" in last:
            QMessageBox.information(self, "暂不支持导入回滚", "导入操作暂不支持自动回滚，请手动删除。")
        else:
            QMessageBox.information(self, "无法撤销", "该操作无法自动撤销。")

    def show_permission_manager(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("字段权限管理")
        vbox = QVBoxLayout(dlg)
        table_combo = QListWidget()
        table_combo.addItems(self.db.tables())
        vbox.addWidget(QLabel("选择表："))
        vbox.addWidget(table_combo)
        field_list = QListWidget()
        vbox.addWidget(QLabel("字段权限："))
        vbox.addWidget(field_list)
        perm_combo = QComboBox()
        perm_combo.addItems(["可写", "只读", "隐藏"])
        vbox.addWidget(QLabel("设置权限："))
        vbox.addWidget(perm_combo)
        save_btn = QPushButton("保存权限")
        vbox.addWidget(save_btn)

        def load_fields():
            field_list.clear()
            table = table_combo.currentItem().text() if table_combo.currentItem() else None
            if not table:
                return
            model = QSqlTableModel(self, self.db)
            model.setTable(table)
            model.select()
            for col in range(model.columnCount()):
                name = model.headerData(col, Qt.Horizontal)
                field_list.addItem(name)
        table_combo.currentItemChanged.connect(lambda *_: load_fields())

        def set_perm():
            table = table_combo.currentItem().text() if table_combo.currentItem() else None
            perm = perm_combo.currentText()
            for item in field_list.selectedItems():
                field = item.text()
                if table not in self.field_permissions:
                    self.field_permissions[table] = {}
                if perm == "可写":
                    self.field_permissions[table][field] = "write"
                elif perm == "只读":
                    self.field_permissions[table][field] = "readonly"
                elif perm == "隐藏":
                    self.field_permissions[table][field] = "hidden"
            QMessageBox.information(dlg, "权限设置", "权限已设置，记得保存！")
        perm_combo.currentTextChanged.connect(lambda _: set_perm())
        save_btn.clicked.connect(lambda: (
            self.save_field_permissions(), QMessageBox.information(dlg, "保存成功", "权限已保存！")))
        load_fields()
        dlg.exec_()

    def show_batch_modify(self):
        if not hasattr(self, 'model') or not self.current_table:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("批量字段修改/查找替换")
        vbox = QVBoxLayout(dlg)
        # 字段选择
        field_label = QLabel("字段:")
        vbox.addWidget(field_label)
        field_combo = QListWidget()
        for col in range(self.model.columnCount()):
            name = self.model.headerData(col, Qt.Horizontal)
            if self.field_permissions.get(self.current_table, {}).get(name) != 'hidden':
                field_combo.addItem(name)
        vbox.addWidget(field_combo)
        # 填充值
        fill_label = QLabel("填充值:")
        vbox.addWidget(fill_label)
        fill_edit = QLineEdit()
        vbox.addWidget(fill_edit)
        # 查找替换
        find_label = QLabel("查找:")
        vbox.addWidget(find_label)
        find_edit = QLineEdit()
        replace_label = QLabel("替换为:")
        vbox.addWidget(replace_label)
        replace_edit = QLineEdit()
        vbox.addWidget(find_edit)
        vbox.addWidget(replace_edit)
        # 条件筛选
        cond_label = QLabel("条件(如 a=1,b=2,支持正则):")
        vbox.addWidget(cond_label)
        cond_edit = QLineEdit()
        vbox.addWidget(cond_edit)
        # 应用按钮
        apply_btn = QPushButton("应用")
        vbox.addWidget(apply_btn)

        def do_batch():
            import re
            selected_fields = [item.text()
                               for item in field_combo.selectedItems()]
            if not selected_fields:
                QMessageBox.warning(dlg, "请选择字段", "请至少选择一个字段")
                return
            fill_val = fill_edit.text()
            find_val = find_edit.text()
            replace_val = replace_edit.text()
            cond = cond_edit.text().strip()
            # 多条件解析
            conds = []
            if cond:
                for part in cond.split(','):
                    if '=' in part:
                        k, v = part.split('=', 1)
                        conds.append((k.strip(), v.strip()))
            idxs = self.table_view.selectionModel().selectedRows()
            if not idxs:
                idxs = [self.model.index(row, 0)
                        for row in range(self.model.rowCount())]
            for idx in idxs:
                row = idx.row()
                # 多条件判断
                match = True
                for k, v in conds:
                    col_idx = None
                    for col in range(self.model.columnCount()):
                        if self.model.headerData(col, Qt.Horizontal) == k:
                            col_idx = col
                            break
                    if col_idx is not None:
                        cell_val = str(self.model.data(
                            self.model.index(row, col_idx)))
                        # 支持正则
                        try:
                            if not re.fullmatch(v, cell_val):
                                match = False
                                break
                        except Exception:
                            if cell_val != v:
                                match = False
                                break
                if not match:
                    continue
                for col in range(self.model.columnCount()):
                    name = self.model.headerData(col, Qt.Horizontal)
                    # 字段级只读限制
                    if self.field_permissions.get(self.current_table, {}).get(name) == 'readonly':
                        continue
                    if name in selected_fields:
                        if fill_val:
                            self.model.setData(
                                self.model.index(row, col), fill_val)
                        if find_val:
                            val0 = str(self.model.data(
                                self.model.index(row, col)))
                            if find_val in val0:
                                self.model.setData(self.model.index(
                                    row, col), val0.replace(find_val, replace_val))
            self.log.append(
                f"批量修改字段 {selected_fields} 于表 {self.current_table}")
            QMessageBox.information(dlg, "批量修改完成", "批量操作已完成，记得保存！")
            dlg.accept()
        apply_btn.clicked.connect(do_batch)
        dlg.exec_()

    def upload_permissions_to_cloud(self):
        config_path = os.path.join(os.path.dirname(
            __file__), 'db_field_permissions.json')
        url = 'https://your-cloud-api/upload'  # 替换为你的云端API
        try:
            with open(config_path, 'rb') as f:
                files = {'file': ('db_field_permissions.json', f)}
                r = requests.post(url, files=files)
            if r.status_code == 200:
                QMessageBox.information(self, "上传成功", "权限配置已上传到云端！")
            else:
                QMessageBox.warning(self, "上传失败", f"云端返回: {r.text}")
        except Exception as e:
            QMessageBox.warning(self, "上传失败", str(e))

    def download_permissions_from_cloud(self):
        config_path = os.path.join(os.path.dirname(
            __file__), 'db_field_permissions.json')
        url = 'https://your-cloud-api/download'  # 替换为你的云端API
        try:
            r = requests.get(url)
            if r.status_code == 200:
                with open(config_path, 'wb') as f:
                    f.write(r.content)
                self.load_field_permissions()
                QMessageBox.information(self, "下载成功", "权限配置已从云端拉取并生效！")
            else:
                QMessageBox.warning(self, "下载失败", f"云端返回: {r.text}")
        except Exception as e:
            QMessageBox.warning(self, "下载失败", str(e))

    def show_permission_log(self):
        log_path = os.path.join(os.path.dirname(
            __file__), 'db_field_permissions_log.json')
        dlg = QDialog(self)
        dlg.setWindowTitle("权限变更日志")
        vbox = QVBoxLayout(dlg)
        log_list = QListWidget()
        vbox.addWidget(log_list)
        rollback_btn = QPushButton("回滚到选中版本")
        vbox.addWidget(rollback_btn)
        logs = []
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                for i, entry in enumerate(logs):
                    time = entry.get('time', '')
                    for d in entry.get('diff', []):
                        log_list.addItem(
                            f"[{i}] [{time}] {d['table']}.{d['field']}: {d['old']} -> {d['new']}")
            except Exception as e:
                log_list.addItem(f"日志读取失败: {str(e)}")
        else:
            log_list.addItem("暂无日志记录")

        def do_rollback():
            idx = log_list.currentRow()
            if idx < 0 or idx >= len(logs):
                QMessageBox.warning(dlg, "未选择", "请先选择要回滚的版本")
                return
            # 回滚到选中日志之前的权限配置
            config_path = os.path.join(os.path.dirname(
                __file__), 'db_field_permissions.json')
            # 重新构建权限配置
            perms = {}
            for i in range(idx+1):
                for d in logs[i].get('diff', []):
                    table, field, new = d['table'], d['field'], d['new']
                    if table not in perms:
                        perms[table] = {}
                    perms[table][field] = new
            self.field_permissions = perms
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.field_permissions, f,
                          ensure_ascii=False, indent=2)
            self.load_field_permissions()
            QMessageBox.information(dlg, "回滚成功", f"已回滚到第{idx+1}个版本，权限已生效！")
        rollback_btn.clicked.connect(do_rollback)
        dlg.exec_()

    def show_schema_manager(self):
        table = self.current_table
        if not table:
            QMessageBox.warning(self, "未选择表", "请先选择要管理结构的表")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"表结构管理 - {table}")
        vbox = QVBoxLayout(dlg)
        # 字段注释加载
        comment_path = os.path.join(os.path.dirname(
            __file__), 'db_field_comments.json')
        comments = {}
        if os.path.exists(comment_path):
            try:
                with open(comment_path, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
            except Exception:
                comments = {}
        if table not in comments:
            comments[table] = {}
        # 字段列表
        field_list = QListWidget()
        model = QSqlTableModel(self, self.db)
        model.setTable(table)
        model.select()
        for col in range(model.columnCount()):
            name = model.headerData(col, Qt.Horizontal)
            comment = comments[table].get(name, "")
            field_list.addItem(f"{name}  # {comment}" if comment else name)
        vbox.addWidget(QLabel("字段列表："))
        vbox.addWidget(field_list)
        # 字段操作
        add_btn = QPushButton("新增字段")
        del_btn = QPushButton("删除字段")
        type_btn = QPushButton("修改类型")
        comment_btn = QPushButton("编辑注释")
        vbox.addWidget(add_btn)
        vbox.addWidget(del_btn)
        vbox.addWidget(type_btn)
        vbox.addWidget(comment_btn)

        drop_table_btn = QPushButton("删除整表")
        vbox.addWidget(drop_table_btn)

        def add_field():
            name, ok = QInputDialog.getText(dlg, "新增字段", "字段名：")
            if not ok or not name:
                return
            ftype, ok = QInputDialog.getText(
                dlg, "字段类型", "类型(如 TEXT, INTEGER, REAL)：")
            if not ok or not ftype:
                return
            sql = f"ALTER TABLE {table} ADD COLUMN {name} {ftype}"
            try:
                self.db.exec(sql)
                QMessageBox.information(dlg, "成功", f"已添加字段 {name}")
                self.refresh_table()
                field_list.addItem(name)
            except Exception as e:
                QMessageBox.warning(dlg, "失败", str(e))

        def del_field():
            item = field_list.currentItem()
            if not item:
                return
            name = item.text().split('  #')[0]
            QMessageBox.information(
                dlg, "提示", f"SQLite不支持直接删除字段，请用导出-重建表-导入数据方式实现。")

        def change_type():
            item = field_list.currentItem()
            if not item:
                return
            name = item.text().split('  #')[0]
            ftype, ok = QInputDialog.getText(
                dlg, "修改类型", f"字段 {name} 新类型：")
            if not ok or not ftype:
                return
            QMessageBox.information(dlg, "提示", "SQLite不支持直接修改字段类型，请用导出-重建表-导入数据方式实现。")

        def drop_table():
            reply = QMessageBox.question(
                dlg, "确认删除",
                f"确定要删除整张表 {table} 吗？该操作不可恢复！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            try:
                # 关闭可能的外键约束影响
                self.db.exec("PRAGMA foreign_keys = OFF;")
                self.db.exec(f"DROP TABLE IF EXISTS {table};")
                self.db.exec("PRAGMA foreign_keys = ON;")
                QMessageBox.information(dlg, "成功", f"已删除表 {table}")
                self.refresh_table()
                dlg.accept()
            except Exception as e:
                QMessageBox.critical(dlg, "删除失败", str(e))

        def edit_comment():
            item = field_list.currentItem()
            if not item:
                return
            name = item.text().split('  #')[0]
            old_comment = comments[table].get(name, "")
            new_comment, ok = QInputDialog.getText(
                dlg, "编辑注释", f"字段 {name} 注释：", text=old_comment)
            if not ok:
                return
            comments[table][name] = new_comment
            with open(comment_path, 'w', encoding='utf-8') as f:
                json.dump(comments, f, ensure_ascii=False, indent=2)
            # 刷新显示
            field_list.clear()
            for col in range(model.columnCount()):
                fname = model.headerData(col, Qt.Horizontal)
                cmt = comments[table].get(fname, "")
                field_list.addItem(f"{fname}  # {cmt}" if cmt else fname)
        add_btn.clicked.connect(add_field)
        del_btn.clicked.connect(del_field)
        type_btn.clicked.connect(change_type)
        comment_btn.clicked.connect(edit_comment)
        drop_table_btn.clicked.connect(drop_table)

        dlg.exec_()

    def show_table_stats(self):
        table = self.current_table
        if not table:
            QMessageBox.warning(self, "未选择表", "请先选择要统计的表")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"数据统计 - {table}")
        vbox = QVBoxLayout(dlg)
        model = QSqlTableModel(self, self.db)
        model.setTable(table)
        model.select()
        row_count = model.rowCount()
        vbox.addWidget(QLabel(f"行数：{row_count}"))
        for col in range(model.columnCount()):
            name = model.headerData(col, Qt.Horizontal)
            values = set()
            for row in range(row_count):
                values.add(str(model.data(model.index(row, col))))
            vbox.addWidget(QLabel(f"字段 {name} - 唯一值: {len(values)}"))
        dlg.exec_()

    def switch_language(self, lang):
        # 简单实现：按钮、标签、提示等中英文切换
        zh = lang == "中文"
        self.add_btn.setText("新增" if zh else "Add")
        self.del_btn.setText("删除" if zh else "Delete")
        self.save_btn.setText("保存修改" if zh else "Save")
        self.import_btn.setText("导入CSV" if zh else "Import CSV")
        self.export_btn.setText("导出CSV" if zh else "Export CSV")
        self.batch_btn.setText("批量修改" if zh else "Batch Edit")
        self.log_btn.setText("权限变更日志" if zh else "Perm Log")
        self.perm_btn.setText("字段权限管理" if zh else "Field Perm")
        self.upload_btn.setText("传权限到云" if zh else "Upload Perm")
        self.download_btn.setText("云端拉取权" if zh else "Download Perm")
        self.schema_btn.setText("表结构管理" if zh else "Schema")
        self.stats_btn.setText("数据统计" if zh else "Stats")
        self.page_label.setText(self.page_label.text().replace("页", "Page").replace("共", "Total").replace(
            "行", "Rows") if not zh else self.page_label.text().replace("Page", "页").replace("Total", "共").replace("Rows", "行"))

    def _create_database_connection_panel(self, main_layout):
        """创建数据库连接面板 - 专业紧凑的布局"""
        from PyQt5.QtWidgets import QGroupBox, QGridLayout, QFrame

        # 创建紧凑的分组框
        db_group = QGroupBox("数据库连接管理")
        db_group.setFixedHeight(110)
        db_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        # 使用紧凑的网格布局
        db_layout = QGridLayout(db_group)
        db_layout.setSpacing(2)  # 减少间距
        db_layout.setContentsMargins(15, 0, 15, 0)  # 紧凑的边距

        # 第一行：类型选择和连接状态（紧凑布局）
        type_label = QLabel("类型:")
        type_label.setFixedWidth(40)
        db_layout.addWidget(type_label, 0, 0)

        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["SQLite", "DuckDB"])
        self.db_type_combo.setFixedWidth(100)
        self.db_type_combo.currentTextChanged.connect(self._on_database_type_changed)
        db_layout.addWidget(self.db_type_combo, 0, 1)

        # 连接状态指示器
        status_label = QLabel("状态:")
        status_label.setFixedWidth(30)
        db_layout.addWidget(status_label, 0, 2)

        self.current_db_label = QLabel(os.path.basename(self.selected_db_path) if self.selected_db_path else "未连接")
        self.current_db_label.setStyleSheet("""
            QLabel {
                color: #2196F3;
                font-weight: bold;
                padding: 2px 6px;
                border: 1px solid #2196F3;
                border-radius: 3px;
                background-color: #E3F2FD;
            }
        """)
        self.current_db_label.setFixedWidth(180)
        db_layout.addWidget(self.current_db_label, 0, 3)

        # 第二行：文件选择（占用更多空间）
        file_label = QLabel("文件:")
        file_label.setFixedWidth(30)
        db_layout.addWidget(file_label, 0, 4)

        self.db_file_combo = QComboBox()
        self.db_file_combo.setFixedWidth(500)
        self.db_file_combo.setEditable(False)
        self.db_file_combo.setStyleSheet("""
            QComboBox {
                padding: 4px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        db_layout.addWidget(self.db_file_combo, 0, 5)
        # 连接按钮（突出显示）
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setFixedWidth(150)
        self.connect_btn.clicked.connect(self._connect_to_selected_database)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        db_layout.addWidget(self.connect_btn, 0, 6)

        # 第三行：操作按钮（紧凑排列）
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(6)

        # 扫描按钮
        self.scan_btn = QPushButton("扫描")
        self.scan_btn.clicked.connect(self._scan_databases_async)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 8px;
                border: 1px solid #ddd;
                border-radius: 3px;
                background-color: #f8f9fa;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        btn_layout.addWidget(self.scan_btn)

        # 浏览按钮
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_database_file)
        self.browse_btn.setStyleSheet(self.scan_btn.styleSheet())
        btn_layout.addWidget(self.browse_btn)

        # 筛选输入框
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("筛选文件...")
        self.filter_edit.textChanged.connect(self._filter_database_files)
        self.filter_edit.setStyleSheet("""
            QLineEdit {
                padding: 4px;
                border: 1px solid #ddd;
                border-radius: 3px;
                min-width: 120px;
            }
        """)
        btn_layout.addWidget(self.filter_edit)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._scan_databases_async)
        self.refresh_btn.setStyleSheet(self.scan_btn.styleSheet())
        btn_layout.addWidget(self.refresh_btn)

        btn_layout.addStretch()  # 推到左边

        db_layout.addWidget(btn_frame, 2, 0, 1, 4)  # 跨越所有列

        # 设置列的拉伸比例
        db_layout.setColumnStretch(1, 1)  # 文件选择框可拉伸
        db_layout.setColumnStretch(2, 1)  # 状态标签可拉伸

        main_layout.addWidget(db_group)

    def _connect_to_selected_database(self):
        """连接到选择的数据库"""
        selected_path = None

        # 获取选择的路径
        if self.db_file_combo.currentData():
            selected_path = self.db_file_combo.currentData()
        elif self.db_file_combo.currentText():
            # 如果是手动输入的路径
            input_path = self.db_file_combo.currentText()
            if os.path.exists(input_path):
                selected_path = input_path

        if not selected_path:
            QMessageBox.warning(self, "警告", "请选择一个有效的数据库文件")
            return

        try:
            # 验证数据库文件
            if self.current_db_type == 'sqlite':
                if not self._is_sqlite_file(selected_path):
                    QMessageBox.warning(self, "错误", "选择的文件不是有效的SQLite数据库")
                    return
            else:
                if not self._is_duckdb_file(selected_path):
                    QMessageBox.warning(self, "错误", "选择的文件不是有效的DuckDB数据库")
                    return

            # 更新当前连接
            self.selected_db_path = selected_path
            self.db_path = selected_path
            self.current_db_label.setText(os.path.basename(selected_path))

            # 重新连接数据库并加载表列表
            self._reload_database_tables()

            QMessageBox.information(self, "成功", f"已连接到数据库: {os.path.basename(selected_path)}")

        except Exception as e:
            QMessageBox.critical(self, "连接失败", f"连接数据库失败: {str(e)}")

    def _reload_database_tables(self):
        """重新连接数据库并加载表列表 - 支持 SQLite 和 DuckDB"""
        try:
            # 清空当前表列表
            self.table_list.clear()

            if self.current_db_type == 'duckdb':
                # DuckDB 处理
                import duckdb
                conn = duckdb.connect(self.db_path)

                # 获取表列表
                tables_result = conn.execute("SHOW TABLES").fetchall()
                tables = [table[0] for table in tables_result]

                # 存储 DuckDB 连接供后续使用
                self._duckdb_conn = conn

            else:
                # SQLite 处理（原有逻辑）
                # 关闭当前数据库连接
                if hasattr(self, 'db') and self.db.isOpen():
                    self.db.close()

                # 重新连接数据库
                self.db.setDatabaseName(self.db_path)
                if not self.db.open():
                    raise Exception(f"无法打开数据库: {self.db.lastError().text()}")

                # 获取表列表
                tables = self.db.tables()

            # 添加表到列表
            self.table_list.addItems(tables)

            # 如果有表，选择第一个
            if tables:
                self.table_list.setCurrentRow(0)
                first_item = self.table_list.item(0)
                if first_item:
                    self.load_table(first_item)

            # 更新主题提示（仅对 SQLite）
            # 自动选择第一个表
            if tables:
                first_item = self.table_list.item(0)
                if first_item:
                    self.table_list.setCurrentItem(first_item)
                    self.load_table(first_item)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"重新加载数据库表失败: {str(e)}")

    def _create_duckdb_table_model(self, schema_result, data_result, total_rows):
        """为 DuckDB 创建自定义表模型"""

        class DuckDBTableModel(QAbstractTableModel):
            def __init__(self, schema, data, parent=None):
                super().__init__(parent)
                self.schema = schema  # [(column_name, data_type, null, key, default, extra), ...]
                self.data = data
                self.headers = [col[0] for col in schema]

            def rowCount(self, parent=None):
                return len(self.data)

            def columnCount(self, parent=None):
                return len(self.headers)

            def data(self, index, role=Qt.DisplayRole):
                if not index.isValid():
                    return QVariant()

                if role == Qt.DisplayRole:
                    return str(self.data[index.row()][index.column()])

                return QVariant()

            def headerData(self, section, orientation, role=Qt.DisplayRole):
                if role == Qt.DisplayRole and orientation == Qt.Horizontal:
                    return self.headers[section]
                return QVariant()

        # 创建并设置模型
        if hasattr(self, 'model'):
            self.model.deleteLater()

        self.model = DuckDBTableModel(schema_result, data_result)
        self.table_view.setModel(self.model)

    def _filter_database_files(self):
        """筛选数据库文件"""
        filter_text = self.filter_edit.text().lower()

        # 清空当前列表
        self.db_file_combo.clear()

        # 根据筛选条件添加文件
        db_type = self.current_db_type
        if db_type in self.available_databases:
            for db_info in self.available_databases[db_type]:
                if not filter_text or filter_text in db_info['name'].lower():
                    display_text = f"{db_info['name']} ({db_info['size']}) - {os.path.dirname(db_info['path'])}"
                    self.db_file_combo.addItem(display_text, db_info['path'])

    def _scan_databases_async(self):
        """异步扫描db目录中的数据库文件"""
        from PyQt5.QtCore import QThread, pyqtSignal

        # 如果已有扫描线程在运行，先停止
        if hasattr(self, '_scan_thread') and self._scan_thread.isRunning():
            return

        # 禁用扫描按钮
        self.scan_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.scan_btn.setText("扫描中...")

        # 创建扫描线程
        self._scan_thread = DatabaseScanThread()
        self._scan_thread.scan_completed.connect(self._on_scan_completed)
        self._scan_thread.scan_error.connect(self._on_scan_error)
        self._scan_thread.start()

    def _on_scan_completed(self, databases):
        """扫描完成回调"""
        self.available_databases = databases
        self.update_database_file_list()

        # 恢复按钮状态
        self.scan_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.scan_btn.setText("扫描")

        # 显示扫描结果
        sqlite_count = len(databases['sqlite'])
        duckdb_count = len(databases['duckdb'])

        # 统计不同目录下的数据库文件
        all_dirs = set()
        for db_list in databases.values():
            for db_info in db_list:
                all_dirs.add(db_info.get('directory', 'db'))

        dirs_info = f"扫描目录: {', '.join(sorted(all_dirs))}" if len(all_dirs) > 1 else f"扫描目录: {list(all_dirs)[0]}"

        QMessageBox.information(self, "递归扫描完成",
                                f"在db目录中递归扫描完成 (最大深度5层):\n\n"
                                f"SQLite数据库: {sqlite_count} 个\n"
                                f"DuckDB数据库: {duckdb_count} 个\n"
                                f"总计: {sqlite_count + duckdb_count} 个数据库文件\n\n"
                                f"{dirs_info}")

    def _on_scan_error(self, error_msg):
        """扫描错误回调"""
        # 恢复按钮状态
        self.scan_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.scan_btn.setText("扫描")

        QMessageBox.warning(self, "扫描失败", f"扫描数据库文件时出错:\n{error_msg}")

    def scan_system_databases(self):
        """保持向后兼容的同步扫描方法"""
        self._scan_databases_async()

    def _is_sqlite_file(self, file_path):
        """检查文件是否为有效的SQLite数据库"""
        try:
            import sqlite3
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            conn.close()
            return True
        except Exception:
            return False

    def _is_duckdb_file(self, file_path):
        """检查文件是否为有效的DuckDB数据库"""
        try:
            import duckdb
            conn = duckdb.connect(file_path)
            conn.execute("SHOW TABLES;")
            conn.close()
            return True
        except Exception:
            return False

    def _format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def update_database_file_list(self):
        """更新数据库文件列表 - 支持显示完整目录结构"""
        if not hasattr(self, 'db_file_combo'):
            return

        self.db_file_combo.clear()

        # 根据当前选择的数据库类型显示文件
        db_type = self.current_db_type
        if db_type in self.available_databases:
            # 按目录分组显示数据库文件
            databases_by_dir = {}
            for db_info in self.available_databases[db_type]:
                directory = db_info.get('directory', 'db')
                if directory not in databases_by_dir:
                    databases_by_dir[directory] = []
                databases_by_dir[directory].append(db_info)

            # 按目录名排序，优先显示根目录
            sorted_dirs = sorted(databases_by_dir.keys(), key=lambda x: (x != 'db', x))

            for directory in sorted_dirs:
                # 添加目录分隔符（仅当有多个目录时）
                if len(databases_by_dir) > 1:
                    separator_text = f"--- {directory} ---"
                    self.db_file_combo.addItem(separator_text, None)
                    # 设置分隔符样式（如果支持）
                    index = self.db_file_combo.count() - 1
                    try:
                        item = self.db_file_combo.model().item(index)
                        if item:
                            item.setEnabled(False)  # 禁用分隔符项
                    except:
                        pass

                # 添加该目录下的数据库文件
                for db_info in sorted(databases_by_dir[directory], key=lambda x: x['name']):
                    relative_path = db_info.get('relative_path', db_info['path'])
                    if len(databases_by_dir) > 1:
                        # 多目录时显示相对路径
                        display_text = f"  {db_info['name']} ({db_info['size']}) - {relative_path}"
                    else:
                        # 单目录时显示简化格式
                        display_text = f"{db_info['name']} ({db_info['size']}) - {relative_path}"

                    self.db_file_combo.addItem(display_text, db_info['path'])

        # 应用当前的筛选条件
        if hasattr(self, 'filter_edit') and self.filter_edit.text():
            self._filter_database_files()

    def _on_database_type_changed(self, type_text):
        """数据库类型切换处理"""
        self.current_db_type = 'sqlite' if type_text == 'SQLite' else 'duckdb'
        self.update_database_file_list()

    def browse_database_file(self):
        """浏览选择数据库文件"""
        from PyQt5.QtWidgets import QFileDialog

        if self.current_db_type == 'sqlite':
            file_filter = "SQLite数据库 (*.db *.sqlite *.sqlite3);;所有文件 (*.*)"
        else:
            file_filter = "DuckDB数据库 (*.duckdb);;所有文件 (*.*)"

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据库文件", "", file_filter
        )

        if file_path:
            # 添加到对应类型的列表中
            file_size = os.path.getsize(file_path)
            db_info = {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': self._format_file_size(file_size)
            }

            # 检查是否已存在
            existing_paths = [db['path'] for db in self.available_databases[self.current_db_type]]
            if file_path not in existing_paths:
                self.available_databases[self.current_db_type].append(db_info)
                self.update_database_file_list()

            # 选中新添加的文件
            for i in range(self.db_file_combo.count()):
                if self.db_file_combo.itemData(i) == file_path:
                    self.db_file_combo.setCurrentIndex(i)
                    break

    def show_slow_queries(self):
        """显示慢SQL记录"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("慢SQL记录")
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        # 统计信息
        stats_label = QLabel(f"慢查询阈值: {self.slow_query_threshold}ms | 记录数量: {len(self.slow_queries)}")
        layout.addWidget(stats_label)

        # 慢查询列表
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        if not self.slow_queries:
            text_edit.setPlainText("暂无慢查询记录")
        else:
            content = []
            for i, query_info in enumerate(self.slow_queries, 1):
                content.append(f"=== 慢查询 #{i} ===")
                content.append(f"时间: {query_info['timestamp']}")
                content.append(f"耗时: {query_info['duration']}ms")
                content.append(f"SQL: {query_info['sql']}")
                if query_info.get('error'):
                    content.append(f"错误: {query_info['error']}")
                content.append("")

            text_edit.setPlainText("\n".join(content))

        layout.addWidget(text_edit)

        # 按钮区域
        btn_layout = QHBoxLayout()

        clear_btn = QPushButton("清空记录")
        clear_btn.clicked.connect(lambda: self._clear_slow_queries(text_edit, stats_label))
        btn_layout.addWidget(clear_btn)

        export_btn = QPushButton("导出记录")
        export_btn.clicked.connect(lambda: self._export_slow_queries())
        btn_layout.addWidget(export_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        dialog.exec_()

    def toggle_edit_mode(self):
        """切换编辑模式"""
        try:
            if hasattr(self, 'model') and self.model:
                # 检查当前是否处于编辑模式
                current_strategy = self.model.editStrategy()

                if current_strategy == QSqlTableModel.OnManualSubmit:
                    # 当前是手动提交模式，切换到自动提交
                    self.model.setEditStrategy(QSqlTableModel.OnFieldChange)
                    self.edit_btn.setText("锁定编辑")
                    QMessageBox.information(self, "编辑模式", "已启用自动编辑模式")
                else:
                    # 当前是自动提交模式，切换到手动提交
                    self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
                    self.edit_btn.setText("编辑")
                    QMessageBox.information(self, "编辑模式", "已切换到手动提交模式")
            else:
                QMessageBox.warning(self, "警告", "请先选择一个表")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"切换编辑模式失败: {str(e)}")

    def show_batch_modify(self):
        """显示批量修改对话框"""
        if not hasattr(self, 'model') or not self.current_table:
            QMessageBox.warning(self, "警告", "请先选择一个表")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("批量字段修改/查找替换")
        dlg.resize(400, 500)
        vbox = QVBoxLayout(dlg)

        # 字段选择
        field_label = QLabel("选择要修改的字段:")
        vbox.addWidget(field_label)
        field_combo = QListWidget()
        field_combo.setSelectionMode(QListWidget.MultiSelection)

        try:
            for col in range(self.model.columnCount()):
                name = self.model.headerData(col, Qt.Horizontal)
                if hasattr(self, 'field_permissions'):
                    if self.field_permissions.get(self.current_table, {}).get(name) != 'hidden':
                        field_combo.addItem(name)
                else:
                    field_combo.addItem(name)
        except Exception:
            # 如果获取字段失败，添加默认提示
            field_combo.addItem("无可用字段")

        vbox.addWidget(field_combo)

        # 填充值
        fill_label = QLabel("填充值 (将选中字段设置为此值):")
        vbox.addWidget(fill_label)
        fill_edit = QLineEdit()
        fill_edit.setPlaceholderText("输入要填充的值...")
        vbox.addWidget(fill_edit)

        # 查找替换
        find_label = QLabel("查找内容:")
        vbox.addWidget(find_label)
        find_edit = QLineEdit()
        find_edit.setPlaceholderText("要查找的文本...")
        vbox.addWidget(find_edit)

        replace_label = QLabel("替换为:")
        vbox.addWidget(replace_label)
        replace_edit = QLineEdit()
        replace_edit.setPlaceholderText("替换后的文本...")
        vbox.addWidget(replace_edit)

        # 条件筛选
        cond_label = QLabel("筛选条件 (格式: 字段名=值,字段名2=值2):")
        vbox.addWidget(cond_label)
        cond_edit = QLineEdit()
        cond_edit.setPlaceholderText("例: name=test,age=25")
        vbox.addWidget(cond_edit)

        # 按钮
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("应用修改")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        vbox.addLayout(btn_layout)

        def do_batch():
            import re
            selected_fields = [item.text() for item in field_combo.selectedItems()]
            if not selected_fields:
                QMessageBox.warning(dlg, "请选择字段", "请至少选择一个字段")
                return

            fill_val = fill_edit.text().strip()
            find_val = find_edit.text().strip()
            replace_val = replace_edit.text().strip()
            cond = cond_edit.text().strip()

            if not fill_val and not find_val:
                QMessageBox.warning(dlg, "请输入值", "请输入填充值或查找内容")
                return

            try:
                # 解析条件
                conds = []
                if cond:
                    for part in cond.split(','):
                        if '=' in part:
                            k, v = part.split('=', 1)
                            conds.append((k.strip(), v.strip()))

                # 获取要处理的行
                selected_rows = self.table_view.selectionModel().selectedRows()
                if not selected_rows:
                    # 如果没有选中行，处理所有行
                    selected_rows = [self.model.index(row, 0) for row in range(self.model.rowCount())]

                modified_count = 0
                for idx in selected_rows:
                    row = idx.row()

                    # 检查条件
                    match = True
                    for k, v in conds:
                        col_idx = None
                        for col in range(self.model.columnCount()):
                            if self.model.headerData(col, Qt.Horizontal) == k:
                                col_idx = col
                                break
                        if col_idx is not None:
                            cell_val = str(self.model.data(self.model.index(row, col_idx)))
                            if cell_val != v:
                                match = False
                                break

                    if not match:
                        continue

                    # 修改选中的字段
                    for col in range(self.model.columnCount()):
                        name = self.model.headerData(col, Qt.Horizontal)
                        if name in selected_fields:
                            if fill_val:
                                # 填充值
                                self.model.setData(self.model.index(row, col), fill_val)
                                modified_count += 1
                            elif find_val:
                                # 查找替换
                                current_val = str(self.model.data(self.model.index(row, col)))
                                if find_val in current_val:
                                    new_val = current_val.replace(find_val, replace_val)
                                    self.model.setData(self.model.index(row, col), new_val)
                                    modified_count += 1

                if hasattr(self, 'log'):
                    self.log.append(f"批量修改字段 {selected_fields} 于表 {self.current_table}")

                QMessageBox.information(dlg, "批量修改完成",
                                        f"已修改 {modified_count} 个单元格\\n记得点击'保存修改'按钮保存到数据库！")
                dlg.accept()

            except Exception as e:
                QMessageBox.critical(dlg, "错误", f"批量修改失败: {str(e)}")

        apply_btn.clicked.connect(do_batch)
        cancel_btn.clicked.connect(dlg.reject)

        dlg.exec_()

    def _clear_slow_queries(self, text_edit, stats_label):
        """清空慢查询记录"""
        self.slow_queries.clear()
        text_edit.setPlainText("暂无慢查询记录")
        stats_label.setText(f"慢查询阈值: {self.slow_query_threshold}ms | 记录数量: 0")

    def _export_slow_queries(self):
        """导出慢查询记录"""
        from PyQt5.QtWidgets import QFileDialog
        import json

        if not self.slow_queries:
            QMessageBox.information(self, "提示", "暂无慢查询记录可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出慢查询记录", f"slow_queries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON文件 (*.json);;文本文件 (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if file_path.endswith('.json'):
                        json.dump(self.slow_queries, f, ensure_ascii=False, indent=2)
                    else:
                        for i, query_info in enumerate(self.slow_queries, 1):
                            f.write(f"=== 慢查询 #{i} ===\n")
                            f.write(f"时间: {query_info['timestamp']}\n")
                            f.write(f"耗时: {query_info['duration']}ms\n")
                            f.write(f"SQL: {query_info['sql']}\n")
                            if query_info.get('error'):
                                f.write(f"错误: {query_info['error']}\n")
                            f.write("\n")

                QMessageBox.information(self, "成功", f"慢查询记录已导出到: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")

    def record_slow_query(self, sql, duration, error=None):
        """记录慢查询"""
        if duration >= self.slow_query_threshold:
            query_info = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sql': sql,
                'duration': duration,
                'error': error
            }
            self.slow_queries.append(query_info)

            # 限制记录数量，避免内存占用过大
            if len(self.slow_queries) > 1000:
                self.slow_queries = self.slow_queries[-500:]  # 保留最近500条

    def closeEvent(self, event):
        """对话框关闭事件处理"""
        try:
            # 首先清理所有使用数据库连接的对象
            if hasattr(self, 'model') and self.model:
                # 清理模型 - DuckDBTableModel没有clear()方法
                if hasattr(self.model, 'clear'):
                    self.model.clear()
                self.table_view.setModel(None)
                self.model.deleteLater()
                self.model = None

            # 关闭数据库连接
            if hasattr(self, 'db') and self.db and self.db.isOpen():
                self.db.close()

            # 移除数据库连接（使用唯一的连接名称）
            if hasattr(self, 'connection_name') and QSqlDatabase.contains(self.connection_name):
                QSqlDatabase.removeDatabase(self.connection_name)

            logger.info(f"数据库连接 {getattr(self, 'connection_name', 'unknown')} 已正确清理")

        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {e}")

        # 调用父类的关闭事件
        super().closeEvent(event)
