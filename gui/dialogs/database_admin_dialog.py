from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QTableView, QPushButton, QMessageBox, QLineEdit, QLabel, QFileDialog, QStyledItemDelegate, QSpinBox, QDoubleSpinBox, QDateEdit, QCheckBox, QComboBox, QInputDialog, QSplitter, QHeaderView, QWidget, QAbstractItemView, QGroupBox, QTextEdit, QProgressDialog
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
        """执行数据库扫描 - 递归扫描data目录最大5层深度"""
        try:
            databases = {
                'sqlite': [],
                'duckdb': []
            }

            # 扫描data目录（数据库统一存储位置）
            db_dir = os.path.join(os.getcwd(), 'data')
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

    def __init__(self, system_db_path="data/factorweave_system.sqlite"):
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
        self.total_rows = 0  # 总行数
        self.total_pages = 0  # 总页数
        self.log = []

        # 性能优化：添加缓存
        self._table_cache = {}  # 表数据缓存 {"table_name": {"data": data, "schema": schema, "timestamp": time}}
        self._cache_ttl = 300  # 缓存有效期（秒）
        self._max_cache_size = 5  # 最大缓存表数量

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

        # 加载字段权限配置
        self.load_field_permissions()

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
        search_layout.addWidget(QLabel("搜索:"))
        
        # 创建搜索框容器
        search_box_layout = QVBoxLayout()
        search_box_layout.setContentsMargins(0, 0, 0, 0)
        search_box_layout.setSpacing(2)
        
        # 主搜索框
        search_input_layout = QHBoxLayout()
        search_input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入搜索条件，支持字段名=值、LIKE模糊搜索、AND/OR组合条件")
        
        # 添加搜索帮助按钮
        self.help_btn = QPushButton("?")
        self.help_btn.setFixedSize(25, 25)
        self.help_btn.setToolTip("点击查看搜索语法帮助")
        self.help_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 12px;
                background-color: #f8f9fa;
                font-size: 12px;
                font-weight: bold;
                color: #6c757d;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                color: #495057;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """)
        self.help_btn.clicked.connect(self.show_search_help)
        
        search_input_layout.addWidget(self.search_edit, 1)
        search_input_layout.addWidget(self.help_btn, 0)
        
        # 搜索示例标签
        self.example_label = QLabel()
        self.example_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
                padding-left: 4px;
            }
        """)
        self.example_label.setText("💡 示例: name=Apple, description LIKE \"%red%\", (category=fruit AND price>5)")
        self.example_label.setVisible(False)  # 默认隐藏，按需显示
        
        search_box_layout.addLayout(search_input_layout)
        search_box_layout.addWidget(self.example_label)
        
        # 将搜索框容器添加到主布局
        search_layout.addLayout(search_box_layout, 1)
        
        # 修改信号连接，只在用户按回车键或编辑结束时触发搜索
        self.search_edit.returnPressed.connect(self.apply_search)
        self.search_edit.editingFinished.connect(self.apply_search)
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        
        # 添加搜索按钮
        self.search_btn = QPushButton("搜索")
        self.search_btn.setEnabled(True)
        self.search_btn.clicked.connect(self.apply_search)
        search_layout.addWidget(self.search_btn)
        
        # 搜索建议下拉框
        self.search_suggestions = QComboBox()
        self.search_suggestions.setVisible(False)
        self.search_suggestions.setEditable(True)
        self.search_suggestions.currentTextChanged.connect(self.on_suggestion_selected)
        search_layout.addWidget(self.search_suggestions)
        
        right_layout.addLayout(search_layout)

        # 过滤信息显示区域
        self.filter_info_label = QLabel()
        self.filter_info_label.setStyleSheet("""
            QLabel {
                background: #F0F8FF;
                border: 1px solid #4A90E2;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                color: #2E5266;
            }
        """)
        self.filter_info_label.setVisible(False)
        right_layout.addWidget(self.filter_info_label)
        
        # 语法验证提示区域
        self.syntax_validation_label = QLabel()
        self.syntax_validation_label.setStyleSheet("""
            QLabel {
                background: #FFF8E1;
                border: 1px solid #FFC107;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                color: #E65100;
            }
        """)
        self.syntax_validation_label.setVisible(False)
        right_layout.addWidget(self.syntax_validation_label)

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
        tables = sorted(self.db.tables())
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

        # 显示加载进度
        self._show_loading_progress(f"正在加载表 {table_name} 的数据...")

        # 开始性能监控
        start_time = time.time()
        
        # 初始化total_rows变量，确保在所有路径中都有定义
        total_rows = 0

        try:
            # 优化查询执行策略
            self._optimize_query_execution(table_name)
            
            if self.current_db_type == 'duckdb':
                # DuckDB 处理
                if hasattr(self, '_duckdb_conn'):
                    # 先尝试从缓存获取数据
                    cached_schema, cached_data, cached_total_rows, from_cache = self._get_cached_data(table_name, self.current_page)
                    
                    if from_cache:
                        # 使用缓存数据
                        total_rows = cached_total_rows
                        self._create_duckdb_table_model(cached_schema, cached_data, cached_total_rows)
                    else:
                        # 缓存未命中，从数据库获取
                        # 获取表结构
                        schema_result = self._duckdb_conn.execute(f"DESCRIBE {table_name}").fetchall()

                        # 获取数据（分页）- 优化版本
                        offset = self.current_page * self.page_size
                        
                        # 先获取总行数
                        count_result = self._duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                        total_rows = count_result[0] if count_result else 0
                        
                        # 检查表大小，提供性能建议
                        self._analyze_table_performance(table_name, total_rows)
                        
                        # 检查索引情况
                        self._check_table_indexes(table_name)
                        
                        # 使用优化的分页查询
                        data_result = self._duckdb_conn.execute(
                            f"SELECT * FROM {table_name} ORDER BY 1 LIMIT {self.page_size} OFFSET {offset}"
                        ).fetchall()

                        # 存储到缓存（如果表不太大）
                        if total_rows < 100000:  # 只有小表才缓存，避免内存占用过大
                            self._set_cached_data(table_name, schema_result, data_result, total_rows)

                        # 创建自定义模型显示数据
                        self._create_duckdb_table_model(schema_result, data_result, total_rows)

            else:
                # SQLite 处理（原有逻辑）
                if hasattr(self, 'model') and self.model is not None:
                    self.model.deleteLater()

                self.model = QSqlTableModel(self, self.db)
                self.model.setTable(table_name)
                self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
                self.model.select()

                self.table_view.setModel(self.model)

                # 更新分页信息
                total_rows = self.model.rowCount()

            # 保存总行数和总页数到实例变量
            self.total_rows = total_rows
            self.total_pages = (total_rows + self.page_size - 1) // self.page_size

            # 更新页面信息
            self.page_label.setText(f"第 {self.current_page + 1} 页，共 {self.total_pages} 页，总计 {self.total_rows} 行")

            # 更新按钮状态
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < self.total_pages - 1)

            # 结束性能监控
            self._monitor_query_performance(start_time, table_name, "SELECT")

            # 隐藏加载进度
            self._hide_loading_progress()

        except Exception as e:
            # 结束性能监控（错误情况）
            self._monitor_query_performance(start_time, table_name, "SELECT (ERROR)")
            # 隐藏加载进度
            self._hide_loading_progress()
            QMessageBox.critical(self, "错误", f"加载表 {table_name} 失败: {str(e)}")

    def refresh_table(self):
        """刷新当前表（保持当前页码）"""
        table_name = self.current_table
        if not table_name:
            return

        # 重新加载当前表数据
        current_item = self.table_list.currentItem()
        if current_item:
            self.load_table(current_item)

    def _show_loading_progress(self, message):
        """显示数据加载进度"""
        try:
            # 创建或更新进度对话框
            if not hasattr(self, '_progress_dialog') or self._progress_dialog is None:
                self._progress_dialog = QProgressDialog(self)
                self._progress_dialog.setWindowTitle("数据加载中")
                self._progress_dialog.setCancelButton(None)
                self._progress_dialog.setWindowModality(Qt.WindowModal)
                self._progress_dialog.setMinimumWidth(300)
                self._progress_dialog.setMinimumHeight(100)
                
            self._progress_dialog.setLabelText(message)
            self._progress_dialog.setRange(0, 0)  # 不确定进度，显示旋转动画
            self._progress_dialog.show()
            self._progress_dialog.raise_()
            self._progress_dialog.activateWindow()
            
            # 强制UI更新
            QApplication.processEvents()
            
        except Exception as e:
            logger.warning(f"显示进度对话框失败: {e}")

    def _hide_loading_progress(self):
        """隐藏数据加载进度"""
        try:
            if hasattr(self, '_progress_dialog') and self._progress_dialog is not None:
                self._progress_dialog.close()
                self._progress_dialog = None
        except Exception as e:
            logger.warning(f"隐藏进度对话框失败: {e}")

    def _analyze_table_performance(self, table_name, total_rows):
        """分析表性能并提供优化建议"""
        try:
            if total_rows > 500000:
                logger.warning(f"大型表检测: {table_name} 包含 {total_rows} 行数据，建议优化查询")
                QMessageBox.information(
                    self, 
                    "性能建议", 
                    f"表 {table_name} 包含 {total_rows:,} 行数据，可能影响查询性能。\n"
                    f"建议：\n"
                    f"• 考虑添加适当的索引\n"
                    f"• 使用更具体的过滤条件\n"
                    f"• 考虑数据分区"
                )
            elif total_rows > 100000:
                logger.info(f"中等大小表: {table_name} 包含 {total_rows} 行数据")
                # 对于中等大小的表，可以在日志中记录性能建议
                self.log.append(f"表 {table_name} 大小: {total_rows:,} 行 (中等大小)")
            else:
                logger.debug(f"小表: {table_name} 包含 {total_rows} 行数据")
                
        except Exception as e:
            logger.warning(f"分析表性能失败: {e}")

    def _check_table_indexes(self, table_name):
        """检查表的索引情况"""
        try:
            if self.current_db_type == 'duckdb':
                # DuckDB 获取索引信息
                index_info = self._duckdb_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                # DuckDB 不直接支持显示索引，我们可以通过表信息推断
                logger.info(f"表 {table_name} 包含 {len(index_info)} 个字段")
                return len(index_info)
            elif self.current_db_type == 'sqlite':
                # SQLite 获取索引信息
                indexes = self.db.executescript(f"PRAGMA index_list({table_name})").fetchall()
                logger.info(f"表 {table_name} 包含 {len(indexes)} 个索引")
                return len(indexes)
        except Exception as e:
            logger.warning(f"检查索引失败: {e}")
            return 0

    def _monitor_query_performance(self, start_time, table_name, query_type="SELECT"):
        """监控查询性能"""
        try:
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 5.0:  # 超过5秒的查询
                logger.warning(f"慢查询检测: {query_type} on {table_name} 耗时 {duration:.2f} 秒")
                self.log.append(f"⚠️  慢查询: {query_type} on {table_name} 耗时 {duration:.2f} 秒")
            elif duration > 2.0:  # 超过2秒的查询
                logger.info(f"中等耗时查询: {query_type} on {table_name} 耗时 {duration:.2f} 秒")
                self.log.append(f"⏱️  查询耗时: {query_type} on {table_name} 耗时 {duration:.2f} 秒")
            else:
                logger.debug(f"快速查询: {query_type} on {table_name} 耗时 {duration:.2f} 秒")
                
        except Exception as e:
            logger.warning(f"性能监控失败: {e}")

    def _optimize_query_execution(self, table_name):
        """优化查询执行策略"""
        try:
            # 检查表大小并调整分页策略
            if self.current_db_type == 'duckdb':
                count_result = self._duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                total_rows = count_result[0] if count_result else 0
                
                # 对于大型表，调整分页大小
                if total_rows > 1000000:
                    self.page_size = 500  # 大表使用较小的分页
                    logger.info(f"大表检测，调整分页大小为 {self.page_size}")
                elif total_rows > 500000:
                    self.page_size = 1000  # 中等表
                else:
                    self.page_size = 2000  # 小表使用较大的分页
                    
        except Exception as e:
            logger.warning(f"优化查询执行失败: {e}")

    def _get_cached_data(self, table_name, page):
        """从缓存获取表数据"""
        try:
            if table_name in self._table_cache:
                cache_entry = self._table_cache[table_name]
                cache_time = cache_entry.get('timestamp', 0)
                current_time = time.time()
                
                # 检查缓存是否过期
                if current_time - cache_time < self._cache_ttl:
                    data = cache_entry.get('data', [])
                    schema = cache_entry.get('schema', [])
                    total_rows = cache_entry.get('total_rows', 0)
                    
                    # 计算当前页的数据范围
                    start_idx = page * self.page_size
                    end_idx = start_idx + self.page_size
                    
                    if start_idx < len(data):
                        page_data = data[start_idx:end_idx]
                        logger.debug(f"使用缓存数据: {table_name} 第{page+1}页")
                        return schema, page_data, total_rows, True  # True表示来自缓存
                        
        except Exception as e:
            logger.warning(f"获取缓存数据失败: {e}")
            
        return None, None, None, False  # 无缓存数据

    def _set_cached_data(self, table_name, schema, data, total_rows):
        """将表数据存入缓存"""
        try:
            # 清理过期缓存
            self._clear_expired_cache()
            
            # 管理缓存大小
            self._manage_cache_size()
            
            # 存储新数据
            self._table_cache[table_name] = {
                'schema': schema,
                'data': data,
                'total_rows': total_rows,
                'timestamp': time.time()
            }
            logger.debug(f"数据已缓存: {table_name}")
            
        except Exception as e:
            logger.warning(f"存储缓存数据失败: {e}")

    def _clear_expired_cache(self):
        """清理过期的缓存数据"""
        try:
            current_time = time.time()
            expired_tables = []
            
            for table_name, cache_entry in self._table_cache.items():
                cache_time = cache_entry.get('timestamp', 0)
                if current_time - cache_time >= self._cache_ttl:
                    expired_tables.append(table_name)
            
            # 清理过期数据
            for table_name in expired_tables:
                del self._table_cache[table_name]
                logger.debug(f"清理过期缓存: {table_name}")
                
        except Exception as e:
            logger.warning(f"清理过期缓存失败: {e}")

    def _manage_cache_size(self):
        """管理缓存大小"""
        try:
            if len(self._table_cache) > self._max_cache_size:
                # 按时间戳排序，删除最旧的缓存
                sorted_cache = sorted(
                    self._table_cache.items(),
                    key=lambda x: x[1].get('timestamp', 0)
                )
                
                # 删除最旧的缓存项
                tables_to_remove = len(self._table_cache) - self._max_cache_size
                for i in range(tables_to_remove):
                    table_name = sorted_cache[i][0]
                    del self._table_cache[table_name]
                    logger.debug(f"清理缓存以节省空间: {table_name}")
                    
        except Exception as e:
            logger.warning(f"管理缓存大小失败: {e}")

    def add_row(self):
        if hasattr(self, 'model') and self.model:
            try:
                self.model.insertRow(self.model.rowCount())
                self.log.append(f"新增行于表 {self.current_table}")
                logger.info(f"新增行到表 {self.current_table}")
            except Exception as e:
                error_msg = f"新增行失败: {str(e)}"
                logger.error(error_msg)
                QMessageBox.warning(self, "错误", error_msg)

    def del_row(self):
        if hasattr(self, 'model') and self.model:
            try:
                idxs = self.table_view.selectionModel().selectedRows()
                if not idxs:
                    QMessageBox.information(self, "提示", "请先选择要删除的行")
                    return

                if QMessageBox.question(self, "确认删除", f"确定要删除选中{len(idxs)}行吗？") == QMessageBox.Yes:
                    for idx in sorted(idxs, key=lambda x: -x.row()):
                        self.model.removeRow(idx.row())
                    self.log.append(f"批量删除{len(idxs)}行于表 {self.current_table}")
                    logger.info(f"批量删除{len(idxs)}行于表 {self.current_table}")
            except Exception as e:
                error_msg = f"删除行失败: {str(e)}"
                logger.error(error_msg)
                QMessageBox.warning(self, "错误", error_msg)

    def save_changes(self):
        if hasattr(self, 'model') and self.model:
            try:
                logger.info(f"开始保存更改到表 {self.current_table}")

                if not self.model.submitAll():
                    error_text = ""
                    if hasattr(self.model, 'lastError'):
                        error_info = self.model.lastError()
                        if hasattr(error_info, 'text'):
                            error_text = error_info.text()

                    error_msg = error_text or "保存失败，请查看日志"
                    logger.error(f"保存失败: {error_msg}")
                    QMessageBox.warning(self, "保存失败", error_msg)
                else:
                    QMessageBox.information(self, "保存成功", "所有更改已保存！")
                    self.log.append(f"保存更改于表 {self.current_table}")
                    logger.info(f"保存更改成功")

                    # 刷新数据显示
                    self.refresh_table()

            except Exception as e:
                error_msg = f"保存更改失败: {str(e)}"
                logger.error(error_msg)
                import traceback
                logger.error(traceback.format_exc())
                QMessageBox.warning(self, "错误", error_msg)

    def import_csv(self):
        if not hasattr(self, 'model') or not self.model:
            QMessageBox.warning(self, "警告", "请先选择一个表")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "导入CSV", "", "CSV Files (*.csv)")
        if not path:
            return

        try:
            logger.info(f"开始导入CSV: {path}")
            with open(path, encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                row_count = 0

                for row in reader:
                    row_index = self.model.rowCount()
                    self.model.insertRow(row_index)
                    for col, val in enumerate(row):
                        if col < len(headers):
                            self.model.setData(self.model.index(row_index, col), val)
                    row_count += 1

            logger.info(f"CSV导入完成，共导入 {row_count} 行")
            QMessageBox.information(self, "导入完成", f"CSV数据已导入 {row_count} 行，记得保存！")
            self.log.append(f"导入CSV到表 {self.current_table}，{row_count} 行")
        except Exception as e:
            error_msg = f"导入CSV失败: {str(e)}"
            logger.error(error_msg)
            QMessageBox.warning(self, "错误", error_msg)

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
            # 使用新的过滤方法
            self.model.setFilter(text)
        self.model.select()
        self.update_page_label()
        self.update_filter_info()
        # 更新搜索建议
        self.update_search_suggestions(text)
        # 验证语法并显示结果
        self.validate_and_display_syntax(text)

    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            current_item = self.table_list.currentItem()
            if current_item:
                self.load_table(current_item)

    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            current_item = self.table_list.currentItem()
            if current_item:
                self.load_table(current_item)

    def update_page_label(self):
        """更新分页标签（使用实例变量）"""
        if self.total_rows > 0:
            self.page_label.setText(
                f"第{self.current_page+1}页 / 共{self.total_pages}页  共{self.total_rows}行")
        else:
            # 兼容旧逻辑（SQLite模式）
            total = self.model.rowCount() if hasattr(self, 'model') else 0
            total_pages = max(1, (total - 1) // self.page_size + 1) if total > 0 else 1
            self.page_label.setText(
                f"第{self.current_page+1}页 / 共{total_pages}页  共{total}行")

    def update_filter_info(self):
        """更新过滤信息显示"""
        try:
            if hasattr(self, 'model') and self.model:
                filter_info = self.model.get_filter_info()
                if filter_info['filter_active']:
                    text = f"🔍 过滤: {filter_info['filtered_rows']}/{filter_info['total_rows']} 行 ({filter_info['match_percentage']:.1f}%)"
                    self.filter_info_label.setText(text)
                    self.filter_info_label.setVisible(True)
                else:
                    self.filter_info_label.setVisible(False)
        except Exception as e:
            print(f"更新过滤信息失败: {e}")
            self.filter_info_label.setVisible(False)
            
    def update_search_suggestions(self, text):
        """更新搜索建议"""
        try:
            if not text or len(text) < 2:  # 至少输入2个字符才显示建议
                self.search_suggestions.setVisible(False)
                return
                
            if hasattr(self, 'model') and self.model:
                # 使用模型中的get_search_suggestions方法
                suggestions = self.model.get_search_suggestions(text, 5)
                self.search_suggestions.clear()
                if suggestions:
                    self.search_suggestions.addItems(suggestions)
                    self.search_suggestions.setVisible(True)
                else:
                    self.search_suggestions.setVisible(False)
        except Exception as e:
            print(f"更新搜索建议失败: {e}")
            self.search_suggestions.setVisible(False)
            
    def validate_and_display_syntax(self, filter_text):
        """验证过滤语法并在UI上显示结果"""
        try:
            if not filter_text.strip():
                # 如果搜索框为空，隐藏语法验证标签
                self.syntax_validation_label.setVisible(False)
                return
                
            if hasattr(self, 'model') and self.model:
                # 使用模型中的validate_filter_syntax方法
                is_valid, message = self.model.validate_filter_syntax(filter_text)
                
                if is_valid:
                    # 语法正确，显示成功消息
                    self.syntax_validation_label.setStyleSheet("""
                        QLabel {
                            background: #E8F5E9;
                            border: 1px solid #4CAF50;
                            border-radius: 4px;
                            padding: 4px 8px;
                            font-size: 11px;
                            color: #1B5E20;
                        }
                    """)
                    self.syntax_validation_label.setText(f"✓ {message}")
                else:
                    # 语法错误，显示错误消息
                    self.syntax_validation_label.setStyleSheet("""
                        QLabel {
                            background: #FFEBEE;
                            border: 1px solid #F44336;
                            border-radius: 4px;
                            padding: 4px 8px;
                            font-size: 11px;
                            color: #B71C1C;
                        }
                    """)
                    self.syntax_validation_label.setText(f"✗ {message}")
                
                self.syntax_validation_label.setVisible(True)
        except Exception as e:
            print(f"语法验证失败: {e}")
            self.syntax_validation_label.setVisible(False)
            
    def on_suggestion_selected(self, suggestion_text):
        """处理用户选择的建议"""
        if suggestion_text:
            # 将选中的建议设置到搜索框
            self.search_edit.setText(suggestion_text)
            # 应用搜索
            self.apply_search()
            # 隐藏建议下拉框
            self.search_suggestions.setVisible(False)
            
    def on_search_text_changed(self, text):
        """处理搜索文本变化，显示友好的提示"""
        try:
            if not text.strip():
                # 空文本时隐藏所有提示
                self.example_label.setVisible(False)
                return
                
            # 如果用户输入了内容，显示搜索示例
            self.example_label.setVisible(True)
            
            # 根据输入的内容动态更新示例
            if "LIKE" in text.upper():
                self.example_label.setText("🔍 正在使用LIKE模糊搜索，支持 % 通配符")
            elif "AND" in text.upper() or "OR" in text.upper():
                self.example_label.setText("🔍 正在使用组合条件搜索")
            elif "=" in text:
                self.example_label.setText("🔍 正在使用精确匹配搜索")
            else:
                self.example_label.setText("💡 提示：可使用 name=值、LIKE模糊搜索、AND/OR组合条件")
                
        except Exception as e:
            print(f"更新搜索提示失败: {e}")
            
    def show_search_help(self):
        """显示搜索语法帮助对话框"""
        try:
            help_dialog = QDialog(self)
            help_dialog.setWindowTitle("搜索语法帮助")
            help_dialog.setModal(True)
            help_dialog.resize(500, 400)
            
            layout = QVBoxLayout(help_dialog)
            
            # 创建帮助内容
            help_text = QTextEdit()
            help_text.setReadOnly(True)
            help_text.setHtml("""
            <h3>🔍 数据库搜索语法帮助</h3>
            
            <h4>1. 基本搜索语法</h4>
            <ul>
                <li><b>精确匹配</b>：<code>字段名=值</code><br>
                    示例：<code>name=Apple</code>, <code>price=5.99</code></li>
                
                <li><b>模糊搜索</b>：<code>字段名 LIKE "模式"</code><br>
                    示例：<code>name LIKE "Apple%"</code> (以Apple开头)<br>
                    示例：<code>description LIKE "%red%"</code> (包含red)<br>
                    示例：<code>name LIKE "%pie"</code> (以pie结尾)</li>
            </ul>
            
            <h4>2. 组合条件搜索</h4>
            <ul>
                <li><b>AND条件</b>：<code>条件1 AND 条件2</code><br>
                    示例：<code>category=fruit AND price>5</code></li>
                
                <li><b>OR条件</b>：<code>条件1 OR 条件2</code><br>
                    示例：<code>name=Apple OR name=Banana</code></li>
                
                <li><b>括号分组</b>：<code>(条件1 OR 条件2) AND 条件3</code><br>
                    示例：<code>(category=fruit AND price>5) OR (category=vegetable AND color=green)</code></li>
            </ul>
            
            <h4>3. 通配符说明</h4>
            <ul>
                <li><code>%</code> - 匹配任意长度的字符（包括零个字符）</li>
                <li><code>_</code> - 匹配单个字符</li>
                <li>不区分大小写搜索</li>
            </ul>
            
            <h4>4. 实用示例</h4>
            <ul>
                <li>搜索所有水果：<code>category=fruit</code></li>
                <li>搜索名称包含"apple"的所有商品：<code>name LIKE "%apple%"</code></li>
                <li>搜索价格大于5元的水果：<code>category=fruit AND price>5</code></li>
                <li>搜索名称以"A"开头的商品：<code>name LIKE "A%"</code></li>
            </ul>
            
            <h4>💡 使用提示</h4>
            <ul>
                <li>搜索不区分大小写</li>
                <li>可以使用比较运算符：=, >, <, >=, <=, !=</li>
                <li>支持数学运算：+, -, *, /</li>
                <li>字段名必须与数据库表中的列名完全匹配</li>
            </ul>
            """)
            
            layout.addWidget(help_text)
            
            # 添加关闭按钮
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(help_dialog.accept)
            layout.addWidget(close_btn)
            
            help_dialog.exec_()
            
        except Exception as e:
            print(f"显示搜索帮助失败: {e}")
            QMessageBox.warning(self, "错误", f"无法显示搜索帮助：{e}")

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

    def save_field_permissions(self):
        """保存字段权限配置到JSON文件"""
        config_path = os.path.join(os.path.dirname(
            __file__), 'db_field_permissions.json')
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            # 保存权限配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.field_permissions, f, ensure_ascii=False, indent=2)

            # 记录到日志
            log_path = os.path.join(os.path.dirname(
                __file__), 'db_field_permissions_log.json')

            # 创建变更日志条目
            log_entry = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'diff': []
            }

            # 尝试加载现有日志
            logs = []
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                except Exception:
                    logs = []

            logs.append(log_entry)

            # 保存日志（限制日志数量）
            if len(logs) > 100:
                logs = logs[-100:]  # 只保留最近100条

            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

            logger.info(f"字段权限配置已保存: {config_path}")
            return True

        except Exception as e:
            logger.error(f"保存字段权限配置失败: {e}")
            return False

    def load_field_permissions(self):
        """从JSON文件加载字段权限配置"""
        config_path = os.path.join(os.path.dirname(
            __file__), 'db_field_permissions.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.field_permissions = json.load(f)
                logger.info(f"字段权限配置已加载: {config_path}")
            else:
                self.field_permissions = {}
                logger.warning(f"字段权限配置文件不存在: {config_path}")
        except Exception as e:
            logger.error(f"加载字段权限配置失败: {e}")
            self.field_permissions = {}

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

        # 检查是否为DuckDB，如果是则只提供删除功能
        if self.current_db_type == 'duckdb':
            self._show_duckdb_schema_manager(table)
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
                logger.info(f"开始删除表: {table}")
                # 关闭可能的外键约束影响
                result = self.db.exec("PRAGMA foreign_keys = OFF;")
                logger.debug(f"PRAGMA foreign_keys = OFF 执行结果: {result}")

                # 执行删除操作
                drop_sql = f"DROP TABLE IF EXISTS {table};"
                logger.info(f"执行SQL: {drop_sql}")
                result = self.db.exec(drop_sql)
                logger.debug(f"DROP TABLE 执行结果: {result}")

                # 检查是否有错误
                if self.db.lastError().isValid():
                    error_msg = self.db.lastError().text()
                    logger.error(f"删除表失败: {error_msg}")
                    raise Exception(error_msg)

                result = self.db.exec("PRAGMA foreign_keys = ON;")
                logger.debug(f"PRAGMA foreign_keys = ON 执行结果: {result}")

                logger.info(f"表 {table} 删除成功")
                QMessageBox.information(dlg, "成功", f"已删除表 {table}")

                # 重新加载表列表
                self._reload_database_tables()
                dlg.accept()
            except Exception as e:
                error_msg = f"删除表失败: {str(e)}"
                logger.error(error_msg)
                QMessageBox.critical(dlg, "删除失败", error_msg)

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

    def _show_duckdb_schema_manager(self, table):
        """DuckDB表结构管理器"""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"表结构管理 - {table} (DuckDB)")
        dlg.resize(500, 400)
        vbox = QVBoxLayout(dlg)

        # 提示信息
        info_label = QLabel("当前为DuckDB数据库")
        info_label.setStyleSheet("color: #2196F3; font-weight: bold; padding: 10px;")
        vbox.addWidget(info_label)

        # 表信息
        try:
            if hasattr(self, '_duckdb_conn'):
                # 获取表结构
                schema_result = self._duckdb_conn.execute(f"DESCRIBE {table}").fetchall()

                field_list = QListWidget()
                for col_info in schema_result:
                    field_name = col_info[0]
                    field_type = col_info[1]
                    field_list.addItem(f"{field_name} ({field_type})")

                vbox.addWidget(QLabel("字段列表（只读）："))
                vbox.addWidget(field_list)
        except Exception as e:
            error_label = QLabel(f"获取表结构失败: {str(e)}")
            error_label.setStyleSheet("color: red;")
            vbox.addWidget(error_label)
            logger.error(f"获取DuckDB表结构失败: {e}")

        # 删除表按钮
        drop_table_btn = QPushButton("删除整表")
        drop_table_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        vbox.addWidget(drop_table_btn)

        def drop_duckdb_table():
            reply = QMessageBox.question(
                dlg, "确认删除",
                f"确定要删除整张表 {table} 吗？该操作不可恢复！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            try:
                logger.info(f"开始删除DuckDB表: {table}")

                if not hasattr(self, '_duckdb_conn'):
                    raise Exception("DuckDB连接不存在")

                # 执行删除操作
                drop_sql = f"DROP TABLE IF EXISTS {table};"
                logger.info(f"执行SQL: {drop_sql}")
                self._duckdb_conn.execute(drop_sql)

                logger.info(f"表 {table} 删除成功")
                QMessageBox.information(dlg, "成功", f"已删除表 {table}")

                # 重新加载表列表
                self._reload_database_tables()
                dlg.accept()

            except Exception as e:
                error_msg = f"删除表失败: {str(e)}"
                logger.error(error_msg)
                QMessageBox.critical(dlg, "删除失败", error_msg)

        drop_table_btn.clicked.connect(drop_duckdb_table)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dlg.accept)
        vbox.addWidget(close_btn)

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
                if hasattr(self, 'data') and self.db.isOpen():
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
        """为 DuckDB 创建可编辑的自定义表模型"""

        class DuckDBTableModel(QAbstractTableModel):
            def __init__(self, schema, data, conn, table_name, parent=None):
                super().__init__(parent)
                self.schema = schema  # [(column_name, data_type, null, key, default, extra), ...]
                self._data = [list(row) for row in data]  # 转换为可修改的列表
                self._original_data = [list(row) for row in data]  # 保存原始数据用于过滤
                self.headers = [col[0] for col in schema]
                self.conn = conn  # DuckDB连接
                self.table_name = table_name
                self._deleted_rows = []  # 记录待删除的行
                self._new_rows = []  # 记录新增的行索引
                self._modified_cells = {}  # 记录修改的单元格 {(row, col): value}
                self._current_filter = ""  # 当前过滤条件
                # 初始化过滤索引为包含所有行的索引列表
                self._filtered_indices = list(range(len(self._data)))  # 过滤后的行索引
                
                # 性能优化：缓存和增量更新
                self._filter_cache = {}  # 缓存过滤结果
                self._last_filter_hash = ""  # 上次过滤条件的哈希
                self._column_types = self._analyze_column_types()  # 分析列类型



            def columnCount(self, parent=None):
                return len(self.headers)

            def data(self, index, role=Qt.DisplayRole):
                if not index.isValid():
                    return QVariant()

                if role == Qt.DisplayRole or role == Qt.EditRole:
                    try:
                        value = self._data[index.row()][index.column()]
                        return str(value) if value is not None else ""
                    except IndexError:
                        return QVariant()

                # 标记修改过的单元格
                if role == Qt.BackgroundRole:
                    if (index.row(), index.column()) in self._modified_cells:
                        return QBrush(QColor(255, 255, 200))  # 浅黄色背景
                    if index.row() in self._new_rows:
                        return QBrush(QColor(200, 255, 200))  # 浅绿色背景

                return QVariant()

            def setData(self, index, value, role=Qt.EditRole):
                """设置数据"""
                if not index.isValid() or role != Qt.EditRole:
                    return False

            # 用户体验增强功能
            def get_filter_info(self):
                """获取过滤信息用于显示"""
                try:
                    total_rows = len(self._data)
                    filtered_rows = len(self._filtered_indices)
                    filter_text = self._current_filter.strip()
                    
                    return {
                        'total_rows': total_rows,
                        'filtered_rows': filtered_rows,
                        'filter_active': bool(filter_text),
                        'filter_text': filter_text,
                        'match_percentage': (filtered_rows / total_rows * 100) if total_rows > 0 else 0
                    }
                except Exception as e:
                    logger.warning(f"获取过滤信息失败: {e}")
                    return {
                        'total_rows': len(self._data),
                        'filtered_rows': len(self._filtered_indices),
                        'filter_active': False,
                        'filter_text': '',
                        'match_percentage': 0
                    }

            def get_search_suggestions(self, partial_text="", max_suggestions=10):
                """获取搜索建议"""
                try:
                    suggestions = set()
                    search_text = partial_text.strip().lower()
                    
                    if not search_text:
                        return list(suggestions)
                    
                    # 从数据中收集建议
                    for row_data in self._data:
                        for cell_value in row_data:
                            if cell_value is not None:
                                cell_str = str(cell_value).lower()
                                if search_text in cell_str and len(cell_str) > len(search_text):
                                    suggestions.add(str(cell_value))
                                    
                                    if len(suggestions) >= max_suggestions:
                                        break
                        if len(suggestions) >= max_suggestions:
                            break
                    
                    return list(suggestions)[:max_suggestions]
                except Exception as e:
                    logger.warning(f"获取搜索建议失败: {e}")
                    return []

            def validate_filter_syntax(self, filter_str):
                """验证过滤条件语法"""
                try:
                    if not filter_str.strip():
                        return True, ""
                    
                    # 基本的语法检查
                    test_conditions = self._parse_filter_conditions(filter_str)
                    if not test_conditions:
                        return False, "无法解析过滤条件"
                    
                    # 测试应用过滤条件（不修改实际数据）
                    original_filter = self._current_filter
                    original_indices = self._filtered_indices.copy()
                    
                    try:
                        self._current_filter = filter_str
                        test_indices = self._execute_filter(test_conditions)
                        
                        # 恢复原始状态
                        self._current_filter = original_filter
                        self._filtered_indices = original_indices
                        
                        return True, f"语法正确，找到 {len(test_indices)} 条匹配记录"
                    except Exception as e:
                        # 恢复原始状态
                        self._current_filter = original_filter
                        self._filtered_indices = original_indices
                        return False, f"过滤执行失败: {str(e)}"
                        
                except Exception as e:
                    return False, f"语法验证失败: {str(e)}"

            def export_filter_results(self, file_path, format_type='csv'):
                """导出过滤结果"""
                try:
                    import csv
                    import os
                    
                    if format_type.lower() == 'csv':
                        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                            writer = csv.writer(csvfile)
                            
                            # 写入表头
                            writer.writerow(self.headers)
                            
                            # 写入过滤后的数据
                            for row_idx in self._filtered_indices:
                                if row_idx < len(self._data):
                                    writer.writerow(self._data[row_idx])
                        
                        logger.info(f"过滤结果已导出到: {file_path}")
                        return True
                    else:
                        return False, f"不支持的导出格式: {format_type}"
                        
                except Exception as e:
                    logger.error(f"导出过滤结果失败: {e}")
                    return False, str(e)

            def get_performance_stats(self):
                """获取性能统计信息"""
                try:
                    stats = {
                        'total_rows': len(self._data),
                        'filtered_rows': len(self._filtered_indices),
                        'memory_usage_mb': 0,  # 简化实现
                        'filter_cache_size': len(getattr(self, '_filter_cache', {}))
                    }
                    
                    # 如果有性能数据，计算过滤速度
                    if hasattr(self, '_last_performance'):
                        stats['last_filter_time_ms'] = self._last_performance.get('filter_time', 0)
                        stats['rows_per_second'] = stats['filtered_rows'] / max(stats['last_filter_time_ms'] / 1000, 0.001)
                    else:
                        stats['last_filter_time_ms'] = 0
                        stats['rows_per_second'] = 0
                    
                    return stats
                except Exception as e:
                    logger.warning(f"获取性能统计失败: {e}")
                    return {
                        'total_rows': len(self._data),
                        'filtered_rows': len(self._filtered_indices),
                        'memory_usage_mb': 0,
                        'filter_cache_size': 0,
                        'last_filter_time_ms': 0,
                        'rows_per_second': 0
                    }

            def clear_filter_cache(self):
                """清空过滤缓存"""
                try:
                    if hasattr(self, '_filter_cache'):
                        self._filter_cache.clear()
                        logger.debug("过滤缓存已清空")
                        return True
                    return False
                except Exception as e:
                    logger.warning(f"清空缓存失败: {e}")
                    return False

                try:
                    row, col = index.row(), index.column()
                    self._data[row][col] = value
                    self._modified_cells[(row, col)] = value
                    self.dataChanged.emit(index, index)
                    return True
                except Exception as e:
                    logger.error(f"设置数据失败: {e}")
                    return False

            def flags(self, index):
                """设置单元格标志（可编辑）"""
                if not index.isValid():
                    return Qt.ItemIsEnabled
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

            def headerData(self, section, orientation, role=Qt.DisplayRole):
                if role == Qt.DisplayRole and orientation == Qt.Horizontal:
                    return self.headers[section]
                return QVariant()

            def insertRow(self, row, parent=None):
                """插入新行"""
                try:
                    self.beginInsertRows(parent or QVariant(), row, row)
                    # 创建空行
                    new_row = [None] * len(self.headers)
                    self._data.insert(row, new_row)
                    self._new_rows.append(row)
                    self.endInsertRows()
                    logger.info(f"新增行: {row}")
                    return True
                except Exception as e:
                    logger.error(f"插入行失败: {e}")
                    return False

            def removeRow(self, row, parent=None):
                """删除行"""
                try:
                    if row < 0 or row >= len(self._data):
                        return False

                    self.beginRemoveRows(parent or QVariant(), row, row)
                    deleted_data = self._data.pop(row)

                    # 如果不是新增的行，记录到待删除列表
                    if row not in self._new_rows:
                        self._deleted_rows.append(deleted_data)
                    else:
                        self._new_rows.remove(row)

                    # 更新修改记录中的行号
                    new_modified = {}
                    for (r, c), v in self._modified_cells.items():
                        if r < row:
                            new_modified[(r, c)] = v
                        elif r > row:
                            new_modified[(r - 1, c)] = v
                    self._modified_cells = new_modified

                    self.endRemoveRows()
                    logger.info(f"删除行: {row}")
                    return True
                except Exception as e:
                    logger.error(f"删除行失败: {e}")
                    return False

            def submitAll(self):
                """提交所有更改到DuckDB"""
                try:
                    logger.info(f"开始提交更改到表: {self.table_name}")

                    # 1. 删除行
                    for row_data in self._deleted_rows:
                        # 构建WHERE条件（使用所有列）
                        conditions = []
                        params = []
                        for i, (header, value) in enumerate(zip(self.headers, row_data)):
                            if value is None:
                                conditions.append(f"{header} IS NULL")
                            else:
                                conditions.append(f"{header} = ?")
                                params.append(value)

                        if conditions:
                            delete_sql = f"DELETE FROM {self.table_name} WHERE {' AND '.join(conditions)}"
                            logger.debug(f"执行删除SQL: {delete_sql}")
                            self.conn.execute(delete_sql, params)

                    # 2. 更新修改的单元格
                    updated_rows = set()
                    for (row, col) in self._modified_cells.keys():
                        if row not in self._new_rows:
                            updated_rows.add(row)

                    for row in updated_rows:
                        # 构建UPDATE语句
                        set_clauses = []
                        set_params = []
                        for col in range(len(self.headers)):
                            if (row, col) in self._modified_cells:
                                set_clauses.append(f"{self.headers[col]} = ?")
                                set_params.append(self._data[row][col])

                        # 构建WHERE条件（使用原始数据）
                        # 这里简化处理：假设有主键或使用所有列匹配
                        where_clauses = []
                        where_params = []
                        for col, header in enumerate(self.headers):
                            if (row, col) not in self._modified_cells:
                                value = self._data[row][col]
                                if value is None:
                                    where_clauses.append(f"{header} IS NULL")
                                else:
                                    where_clauses.append(f"{header} = ?")
                                    where_params.append(value)

                        if set_clauses and where_clauses:
                            update_sql = f"UPDATE {self.table_name} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
                            logger.debug(f"执行更新SQL: {update_sql}")
                            self.conn.execute(update_sql, set_params + where_params)

                    # 3. 插入新行
                    for row in self._new_rows:
                        if row < len(self._data):
                            row_data = self._data[row]
                            placeholders = ', '.join(['?'] * len(row_data))
                            columns = ', '.join(self.headers)
                            insert_sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
                            logger.debug(f"执行插入SQL: {insert_sql}")
                            self.conn.execute(insert_sql, row_data)

                    # 清空修改记录
                    self._deleted_rows.clear()
                    self._new_rows.clear()
                    self._modified_cells.clear()

                    logger.info(f"提交更改成功")
                    return True

                except Exception as e:
                    logger.error(f"提交更改失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return False

            def setFilter(self, filter_str):
                """设置搜索过滤条件"""
                try:
                    import hashlib
                    import time
                    
                    start_time = time.time()
                    
                    # 生成过滤条件的哈希用于缓存检查
                    filter_hash = hashlib.md5(str(self._current_filter + str(len(self._data))).encode()).hexdigest()
                    
                    # 如果数据没有变化且过滤条件相同，使用缓存
                    if (filter_hash == self._last_filter_hash and 
                        len(self._data) == getattr(self, '_last_data_length', 0)):
                        logger.debug(f"使用缓存的过滤结果: {filter_str}")
                        return True
                    
                    self._current_filter = filter_str
                    self._last_filter_hash = filter_hash
                    self._last_data_length = len(self._data)
                    
                    self._apply_filter()
                    
                    # 性能统计
                    elapsed_time = time.time() - start_time
                    
                    # 保存性能数据用于统计
                    self._last_performance = {
                        'filter_time': elapsed_time * 1000,  # 毫秒
                        'rows_processed': len(self._data),
                        'matches_found': len(self._filtered_indices)
                    }
                    
                    logger.debug(f"过滤完成，耗时: {elapsed_time:.3f}s，匹配行数: {len(self._filtered_indices)}")
                    
                    self.layoutChanged.emit()  # 通知视图数据已更改
                    return True
                except Exception as e:
                    logger.error(f"设置过滤条件失败: {e}")
                    return False

            def _apply_filter(self):
                """应用过滤条件到数据"""
                if not self._current_filter.strip():
                    # 如果没有过滤条件，显示所有数据
                    self._filtered_indices = list(range(len(self._data)))
                    return

                # 使用增强的过滤解析器
                try:
                    parsed_conditions = self._parse_filter_conditions(self._current_filter)
                    matched_rows = self._execute_filter(parsed_conditions)
                    self._filtered_indices = matched_rows
                except Exception as e:
                    logger.error(f"应用过滤条件失败: {e}")
                    # 出错时显示所有数据
                    self._filtered_indices = list(range(len(self._data)))

            def _parse_filter_conditions(self, filter_str):
                """解析过滤条件为结构化格式"""
                conditions = []
                try:
                    # 简单的条件解析，支持 OR 和 AND
                    parts = filter_str.split(" OR ")
                    for part in parts:
                        and_parts = part.split(" AND ")
                        and_conditions = []
                        
                        for cond in and_parts:
                            cond = cond.strip()
                            if not cond:
                                continue
                                
                            # 解析不同类型的条件
                            if " LIKE " in cond:
                                # 使用更健壮的方法提取LIKE条件
                                like_index = cond.rfind(" LIKE ")
                                if like_index >= 0:
                                    column_name = cond[:like_index].strip()
                                    # 提取值部分，并正确处理引号
                                    raw_value = cond[like_index + 6:].strip()
                                    # 去掉最外层引号，如果存在
                                    if (raw_value.startswith("'") and raw_value.endswith("'")) or \
                                       (raw_value.startswith('"') and raw_value.endswith('"')):
                                        value = raw_value[1:-1]
                                    else:
                                        value = raw_value
                                    
                                    and_conditions.append({
                                        'type': 'LIKE',
                                        'column': column_name,
                                        'value': value
                                    })
                            elif " = " in cond:
                                column_name, value = cond.split(" = ", 1)
                                and_conditions.append({
                                    'type': 'EQUALS',
                                    'column': column_name.strip(),
                                    'value': value.strip().strip("'\"")
                                })
                            elif " > " in cond:
                                column_name, value = cond.split(" > ", 1)
                                and_conditions.append({
                                    'type': 'GREATER',
                                    'column': column_name.strip(),
                                    'value': value.strip().strip("'\"")
                                })
                            elif " >= " in cond:
                                column_name, value = cond.split(" >= ", 1)
                                and_conditions.append({
                                    'type': 'GREATER_EQUAL',
                                    'column': column_name.strip(),
                                    'value': value.strip().strip("'\"")
                                })
                            elif " <= " in cond:
                                column_name, value = cond.split(" <= ", 1)
                                and_conditions.append({
                                    'type': 'LESS_EQUAL',
                                    'column': column_name.strip(),
                                    'value': value.strip().strip("'\"")
                                })
                            elif " < " in cond:
                                column_name, value = cond.split(" < ", 1)
                                and_conditions.append({
                                    'type': 'LESS',
                                    'column': column_name.strip(),
                                    'value': value.strip().strip("'\"")
                                })
                            # 解析IN条件
                            elif " IN (" in cond and cond.endswith(")"):
                                column_name, values_part = cond.split(" IN ", 1)
                                values = [v.strip().strip("'\"") for v in values_part.strip("()").split(",")]
                                and_conditions.append({
                                    'type': 'IN',
                                    'column': column_name.strip(),
                                    'values': values
                                })
                            # 解析不等于条件
                            elif " != " in cond or " <> " in cond:
                                sep = " != " if " != " in cond else " <> "
                                column_name, value = cond.split(sep, 1)
                                and_conditions.append({
                                    'type': 'NOT_EQUALS',
                                    'column': column_name.strip(),
                                    'value': value.strip().strip("'\"")
                                })
                            # 解析正则表达式
                            elif " REGEXP " in cond or " ~ " in cond:
                                sep = " REGEXP " if " REGEXP " in cond else " ~ "
                                column_name, value = cond.split(sep, 1)
                                and_conditions.append({
                                    'type': 'REGEXP',
                                    'column': column_name.strip(),
                                    'value': value.strip().strip("'\"")
                                })
                            # 解析BETWEEN条件
                            elif " BETWEEN " in cond:
                                parts_between = cond.split(" BETWEEN ")
                                if len(parts_between) == 2:
                                    column_name, range_part = parts_between
                                    range_values = [v.strip().strip("'\"") for v in range_part.split(" AND ")]
                                    if len(range_values) == 2:
                                        and_conditions.append({
                                            'type': 'BETWEEN',
                                            'column': column_name.strip(),
                                            'min': range_values[0],
                                            'max': range_values[1]
                                        })
                            else:
                                # 默认作为LIKE条件处理
                                and_conditions.append({
                                    'type': 'LIKE',
                                    'column': '',  # 匹配所有列
                                    'value': cond.strip()
                                })
                        
                        if and_conditions:
                            conditions.append(and_conditions)
                except Exception as e:
                    logger.warning(f"解析过滤条件失败: {e}")
                    # 解析失败时作为简单的LIKE处理
                    return [[{
                        'type': 'LIKE',
                        'column': '',
                        'value': filter_str.strip()
                    }]]
                
                return conditions

            def _execute_filter(self, conditions):
                """执行过滤逻辑"""
                matched_rows = []
                
                for row_idx, row_data in enumerate(self._data):
                    # 检查当前行是否匹配任何OR条件组
                    for and_conditions in conditions:
                        row_matches = True
                        
                        # 行必须匹配所有AND条件
                        for condition in and_conditions:
                            if not self._check_condition(row_data, condition):
                                row_matches = False
                                break
                        
                        if row_matches:
                            matched_rows.append(row_idx)
                            break
                
                return matched_rows

            def _check_condition(self, row_data, condition):
                """检查单个条件是否匹配"""
                try:
                    condition_type = condition['type']
                    column_name = condition['column']
                    value = condition['value']
                    
                    if condition_type == 'LIKE':
                        if column_name:
                            # 指定列的LIKE匹配
                            if column_name in self.headers:
                                col_idx = self.headers.index(column_name)
                                if col_idx < len(row_data):
                                    cell_value = str(row_data[col_idx]) if row_data[col_idx] is not None else ""
                                    
                                    # 正确处理通配符
                                    if value.startswith('%') and value.endswith('%'):
                                        # 前缀和后缀都有通配符：%pattern%
                                        pattern = value[1:-1]  # 去掉前后的%
                                        return pattern.lower() in cell_value.lower()
                                    elif value.startswith('%'):
                                        # 后缀通配符：%pattern
                                        pattern = value[1:]  # 去掉前面的%
                                        return cell_value.lower().endswith(pattern.lower())
                                    elif value.endswith('%'):
                                        # 前缀通配符：pattern%
                                        pattern = value[:-1]  # 去掉后面的%
                                        return cell_value.lower().startswith(pattern.lower())
                                    else:
                                         # 没有通配符，使用部分匹配（传统SQL LIKE语义）
                                         return value.lower() in cell_value.lower()
                            return False
                        else:
                            # 匹配所有列
                            for cell_value in row_data:
                                cell_str = str(cell_value) if cell_value is not None else ""
                                
                                # 正确处理通配符
                                if value.startswith('%') and value.endswith('%'):
                                    # 前缀和后缀都有通配符：%pattern%
                                    pattern = value[1:-1]  # 去掉前后的%
                                    if pattern.lower() in cell_str.lower():
                                        return True
                                elif value.startswith('%'):
                                    # 后缀通配符：%pattern
                                    pattern = value[1:]  # 去掉前面的%
                                    if cell_str.lower().endswith(pattern.lower()):
                                        return True
                                elif value.endswith('%'):
                                    # 前缀通配符：pattern%
                                    pattern = value[:-1]  # 去掉后面的%
                                    if cell_str.lower().startswith(pattern.lower()):
                                        return True
                                else:
                                     # 没有通配符，使用部分匹配（传统SQL LIKE语义）
                                     if value.lower() in cell_str.lower():
                                         return True
                            return False
                    
                    elif condition_type == 'EQUALS':
                        if column_name and column_name in self.headers:
                            col_idx = self.headers.index(column_name)
                            if col_idx < len(row_data):
                                cell_value = str(row_data[col_idx]) if row_data[col_idx] is not None else ""
                                return cell_value == value
                        return False
                    
                    elif condition_type == 'GREATER':
                        if column_name and column_name in self.headers:
                            col_idx = self.headers.index(column_name)
                            if col_idx < len(row_data):
                                try:
                                    cell_value = float(row_data[col_idx]) if row_data[col_idx] is not None else 0
                                    compare_value = float(value)
                                    return cell_value > compare_value
                                except (ValueError, TypeError):
                                    return False
                        return False
                    
                    elif condition_type == 'GREATER_EQUAL':
                        if column_name and column_name in self.headers:
                            col_idx = self.headers.index(column_name)
                            if col_idx < len(row_data):
                                return self._compare_values(row_data[col_idx], value, '>=')
                        return False
                    
                    elif condition_type == 'LESS_EQUAL':
                        if column_name and column_name in self.headers:
                            col_idx = self.headers.index(column_name)
                            if col_idx < len(row_data):
                                return self._compare_values(row_data[col_idx], value, '<=')
                        return False
                    
                    elif condition_type == 'LESS':
                        if column_name and column_name in self.headers:
                            col_idx = self.headers.index(column_name)
                            if col_idx < len(row_data):
                                return self._compare_values(row_data[col_idx], value, '<')
                        return False
                    
                    elif condition_type == 'NOT_EQUALS':
                        if column_name and column_name in self.headers:
                            col_idx = self.headers.index(column_name)
                            if col_idx < len(row_data):
                                cell_value = str(row_data[col_idx]) if row_data[col_idx] is not None else ""
                                return cell_value != value
                        return False
                    
                    elif condition_type == 'IN':
                        if column_name and column_name in self.headers:
                            col_idx = self.headers.index(column_name)
                            if col_idx < len(row_data):
                                cell_value = str(row_data[col_idx]) if row_data[col_idx] is not None else ""
                                return cell_value in condition['values']
                        return False
                    
                    elif condition_type == 'BETWEEN':
                        if column_name and column_name in self.headers:
                            col_idx = self.headers.index(column_name)
                            if col_idx < len(row_data):
                                try:
                                    cell_value = float(row_data[col_idx]) if row_data[col_idx] is not None else 0
                                    min_val = float(condition['min'])
                                    max_val = float(condition['max'])
                                    return min_val <= cell_value <= max_val
                                except (ValueError, TypeError):
                                    return False
                        return False
                    
                    elif condition_type == 'REGEXP':
                        if column_name:
                            # 指定列的正则匹配
                            if column_name in self.headers:
                                col_idx = self.headers.index(column_name)
                                if col_idx < len(row_data):
                                    import re
                                    try:
                                        cell_value = str(row_data[col_idx]) if row_data[col_idx] is not None else ""
                                        pattern = re.compile(value, re.IGNORECASE)
                                        return bool(pattern.search(cell_value))
                                    except re.error:
                                        return False
                            return False
                        else:
                            # 匹配所有列
                            import re
                            try:
                                pattern = re.compile(value, re.IGNORECASE)
                                for cell_value in row_data:
                                    cell_str = str(cell_value) if cell_value is not None else ""
                                    if pattern.search(cell_str):
                                        return True
                                return False
                            except re.error:
                                return False
                    
                    elif condition_type == 'NOT':
                        # 处理NOT条件
                        not_conditions = condition['conditions']
                        for not_cond in not_conditions:
                            if self._check_condition(row_data, not_cond):
                                return False
                        return True
                    
                    return False
                except Exception as e:
                     logger.warning(f"检查条件时出错: {e}")
                     return False

            def _compare_values(self, cell_value, compare_value, operation):
                """类型感知的值比较"""
                try:
                    # 获取列类型（如果知道）
                    col_type = 'text'  # 默认类型
                    
                    # 如果是数字列，尝试数字比较
                    try:
                        cell_num = float(cell_value) if cell_value is not None else 0
                        compare_num = float(compare_value)
                        
                        if operation == '>':
                            return cell_num > compare_num
                        elif operation == '>=':
                            return cell_num >= compare_num
                        elif operation == '<':
                            return cell_num < compare_num
                        elif operation == '<=':
                            return cell_num <= compare_num
                    except (ValueError, TypeError):
                        # 如果不能转换为数字，使用字符串比较
                        cell_str = str(cell_value) if cell_value is not None else ""
                        compare_str = str(compare_value)
                        
                        if operation == '>':
                            return cell_str > compare_str
                        elif operation == '>=':
                            return cell_str >= compare_str
                        elif operation == '<':
                            return cell_str < compare_str
                        elif operation == '<=':
                            return cell_str <= compare_str
                        
                except Exception as e:
                    logger.warning(f"比较值时出错: {e}")
                    return False
                
                return False

            def rowCount(self, parent=None):
                """返回过滤后的行数"""
                return len(self._filtered_indices)

            def data(self, index, role=Qt.DisplayRole):
                """返回过滤后数据中的对应行数据"""
                if not index.isValid():
                    return QVariant()

                # 获取实际数据行索引
                actual_row = self._filtered_indices[index.row()] if index.row() < len(self._filtered_indices) else -1
                if actual_row == -1:
                    return QVariant()

                if role == Qt.DisplayRole or role == Qt.EditRole:
                    try:
                        value = self._data[actual_row][index.column()]
                        return str(value) if value is not None else ""
                    except IndexError:
                        return QVariant()

                # 标记修改过的单元格
                if role == Qt.BackgroundRole:
                    if (actual_row, index.column()) in self._modified_cells:
                        return QBrush(QColor(255, 255, 200))  # 浅黄色背景
                    if actual_row in self._new_rows:
                        return QBrush(QColor(200, 255, 200))  # 浅绿色背景

                return QVariant()

            def _analyze_column_types(self):
                """分析列的数据类型"""
                column_types = {}
                if not self.schema or not self._data:
                    return column_types

                try:
                    for i, (col_name, data_type, null, key, default, extra) in enumerate(self.schema):
                        # 基于schema信息和数据样本来确定类型
                        if data_type:
                            if 'INT' in data_type.upper() or 'DECIMAL' in data_type.upper():
                                column_types[col_name] = 'numeric'
                            elif 'DATE' in data_type.upper() or 'TIME' in data_type.upper():
                                column_types[col_name] = 'datetime'
                            elif 'BOOL' in data_type.upper():
                                column_types[col_name] = 'boolean'
                            else:
                                column_types[col_name] = 'text'
                        else:
                            # 基于数据样本推断类型
                            sample_values = [row[i] for row in self._data[:10] if row[i] is not None]
                            if sample_values:
                                if all(isinstance(v, (int, float)) for v in sample_values):
                                    column_types[col_name] = 'numeric'
                                elif any(isinstance(v, bool) for v in sample_values):
                                    column_types[col_name] = 'boolean'
                                else:
                                    column_types[col_name] = 'text'
                            else:
                                column_types[col_name] = 'text'
                except Exception as e:
                    logger.warning(f"分析列类型时出错: {e}")
                    # 默认所有列都为文本类型
                    column_types = {col[0]: 'text' for col in self.schema}

                return column_types

            def select(self):
                """重新加载数据并应用当前过滤条件"""
                try:
                    start_time = time.time()
                    # 重新从数据库获取数据
                    query = f"SELECT * FROM {self.table_name}"
                    result = self.conn.execute(query).fetchall()
                    self._data = [list(row) for row in result]
                    self._original_data = [list(row) for row in result]
                    
                    # 重新应用过滤条件
                    self._apply_filter()
                    
                    # 清空修改记录（因为数据已重新加载）
                    self._deleted_rows.clear()
                    self._new_rows.clear()
                    self._modified_cells.clear()
                    
                    logger.info(f"{self.table_name} 加载数据-耗时：{time.time() - start_time:.4f} 秒，行数: {len(self._data)}")
                    return True
                except Exception as e:
                    logger.error(f"重新加载数据失败: {e}")
                    return False

            def lastError(self):
                """返回最后的错误（兼容接口）"""
                class ErrorInfo:
                    def __init__(self):
                        self._text = ""

                    def text(self):
                        return self._text

                    def isValid(self):
                        return bool(self._text)

                    def set_text(self, text):
                        self._text = text

                return ErrorInfo()

        # 创建并设置模型
        if hasattr(self, 'model') and self.model is not None:
            self.model.deleteLater()

        self.model = DuckDBTableModel(
            schema_result,
            data_result,
            self._duckdb_conn,
            self.current_table
        )
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
        """异步扫描data目录中的数据库文件"""
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
                all_dirs.add(db_info.get('directory', 'data'))

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
                directory = db_info.get('directory', 'data')
                if directory not in databases_by_dir:
                    databases_by_dir[directory] = []
                databases_by_dir[directory].append(db_info)

            # 按目录名排序，优先显示根目录
            sorted_dirs = sorted(databases_by_dir.keys(), key=lambda x: (x != 'data', x))

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
        # 保存当前选择
        old_db_type = self.current_db_type
        self.current_db_type = 'sqlite' if type_text == 'SQLite' else 'duckdb'
        
        # 先更新文件列表
        self.update_database_file_list()
        
        # 清理当前模型和视图
        self._cleanup_current_state()
        
        # 根据新类型特殊处理
        if self.current_db_type == 'duckdb' and old_db_type != 'duckdb':
            # 如果从其他类型切换到 DuckDB，需要清理旧连接
            if hasattr(self, '_duckdb_conn') and self._duckdb_conn is not None:
                try:
                    self._duckdb_conn.close()
                except Exception as e:
                    logger.error(f"关闭旧 DuckDB 连接失败: {e}")
                self._duckdb_conn = None
        elif self.current_db_type == 'sqlite' and old_db_type != 'sqlite':
            # 如果从其他类型切换到 SQLite，确保清理旧的数据库连接
            if hasattr(self, 'data') and self.db.isOpen():
                self.db.close()
        
        # 重新加载表列表
        self._reload_database_tables()
    
    def _cleanup_current_state(self):
        """清理当前状态"""
        # 清空当前模型
        if hasattr(self, 'model') and self.model is not None:
            self.model.deleteLater()
            self.model = None
            
        # 清空视图
        self.table_view.setModel(None)
        
        # 清空表列表
        self.table_list.clear()
        
        # 重置当前表
        self.current_table = None

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
                # 检查是否为SQLite模型（只有SQLite模型支持编辑策略）
                if isinstance(self.model, QSqlTableModel):
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
                    # DuckDB模型默认手动提交模式
                    QMessageBox.information(self, "提示", "DuckDB数据库采用手动提交模式，请修改后点击'保存修改'按钮")
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
            if hasattr(self, 'data') and self.db and self.db.isOpen():
                self.db.close()

            # 移除数据库连接（使用唯一的连接名称）
            if hasattr(self, 'connection_name') and QSqlDatabase.contains(self.connection_name):
                QSqlDatabase.removeDatabase(self.connection_name)

            logger.info(f"数据库连接 {getattr(self, 'connection_name', 'unknown')} 已正确清理")

        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {e}")

        # 调用父类的关闭事件
        super().closeEvent(event)
