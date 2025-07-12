"""
节点管理对话框
用于分布式节点发现、注册和监控
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QLabel, QLineEdit, QTextEdit, QGroupBox,
                             QFormLayout, QSpinBox, QCheckBox, QComboBox,
                             QProgressBar, QMessageBox, QHeaderView,
                             QSplitter, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
import json
import socket
import threading
import time


class NodeManagerDialog(QDialog):
    """节点管理对话框"""

    node_discovered = pyqtSignal(dict)
    node_connected = pyqtSignal(str)
    node_disconnected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("分布式节点管理器")
        self.setModal(True)
        self.resize(1000, 700)

        # 节点数据
        self.nodes = {}
        self.discovery_timer = QTimer()
        self.discovery_timer.timeout.connect(self.discover_nodes)

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("分布式节点管理器")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 创建选项卡
        tab_widget = QTabWidget()

        # 节点发现选项卡
        discovery_tab = self.create_discovery_tab()
        tab_widget.addTab(discovery_tab, "节点发现")

        # 节点监控选项卡
        monitor_tab = self.create_monitor_tab()
        tab_widget.addTab(monitor_tab, "节点监控")

        # 节点配置选项卡
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "节点配置")

        layout.addWidget(tab_widget)

        # 按钮
        button_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("刷新节点")
        self.start_discovery_btn = QPushButton("开始发现")
        self.stop_discovery_btn = QPushButton("停止发现")
        self.stop_discovery_btn.setEnabled(False)
        close_btn = QPushButton("关闭")

        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.start_discovery_btn)
        button_layout.addWidget(self.stop_discovery_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # 连接按钮信号
        self.refresh_btn.clicked.connect(self.refresh_nodes)
        self.start_discovery_btn.clicked.connect(self.start_discovery)
        self.stop_discovery_btn.clicked.connect(self.stop_discovery)
        close_btn.clicked.connect(self.accept)

    def create_discovery_tab(self):
        """创建节点发现选项卡"""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        # 发现设置
        settings_group = QGroupBox("发现设置")
        settings_layout = QFormLayout(settings_group)

        self.discovery_port_spin = QSpinBox()
        self.discovery_port_spin.setRange(1024, 65535)
        self.discovery_port_spin.setValue(8888)
        settings_layout.addRow("发现端口:", self.discovery_port_spin)

        self.discovery_interval_spin = QSpinBox()
        self.discovery_interval_spin.setRange(1, 60)
        self.discovery_interval_spin.setValue(5)
        self.discovery_interval_spin.setSuffix(" 秒")
        settings_layout.addRow("发现间隔:", self.discovery_interval_spin)

        self.auto_connect_check = QCheckBox("自动连接发现的节点")
        settings_layout.addRow(self.auto_connect_check)

        layout.addWidget(settings_group)

        # 发现的节点列表
        nodes_group = QGroupBox("发现的节点")
        nodes_layout = QVBoxLayout(nodes_group)

        self.discovered_table = QTableWidget()
        self.discovered_table.setColumnCount(6)
        self.discovered_table.setHorizontalHeaderLabels([
            "节点ID", "IP地址", "端口", "状态", "类型", "操作"
        ])
        self.discovered_table.horizontalHeader().setStretchLastSection(True)
        nodes_layout.addWidget(self.discovered_table)

        layout.addWidget(nodes_group)

        return widget

    def create_monitor_tab(self):
        """创建节点监控选项卡"""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        # 监控统计
        stats_group = QGroupBox("监控统计")
        stats_layout = QFormLayout(stats_group)

        self.total_nodes_label = QLabel("0")
        self.active_nodes_label = QLabel("0")
        self.inactive_nodes_label = QLabel("0")

        stats_layout.addRow("总节点数:", self.total_nodes_label)
        stats_layout.addRow("活跃节点:", self.active_nodes_label)
        stats_layout.addRow("非活跃节点:", self.inactive_nodes_label)

        layout.addWidget(stats_group)

        # 节点详情
        details_group = QGroupBox("节点详情")
        details_layout = QVBoxLayout(details_group)

        self.node_details_table = QTableWidget()
        self.node_details_table.setColumnCount(8)
        self.node_details_table.setHorizontalHeaderLabels([
            "节点ID", "IP地址", "端口", "状态", "CPU使用率", "内存使用率", "任务数", "最后心跳"
        ])
        self.node_details_table.horizontalHeader().setStretchLastSection(True)
        details_layout.addWidget(self.node_details_table)

        layout.addWidget(details_group)

        return widget

    def create_config_tab(self):
        """创建节点配置选项卡"""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        # 本地节点配置
        local_group = QGroupBox("本地节点配置")
        local_layout = QFormLayout(local_group)

        self.local_port_spin = QSpinBox()
        self.local_port_spin.setRange(1024, 65535)
        self.local_port_spin.setValue(8889)
        local_layout.addRow("监听端口:", self.local_port_spin)

        self.max_connections_spin = QSpinBox()
        self.max_connections_spin.setRange(1, 100)
        self.max_connections_spin.setValue(10)
        local_layout.addRow("最大连接数:", self.max_connections_spin)

        self.enable_ssl_check = QCheckBox("启用SSL加密")
        local_layout.addRow(self.enable_ssl_check)

        layout.addWidget(local_group)

        # 手动添加节点
        manual_group = QGroupBox("手动添加节点")
        manual_layout = QFormLayout(manual_group)

        self.manual_ip_edit = QLineEdit()
        self.manual_ip_edit.setPlaceholderText("192.168.1.100")
        manual_layout.addRow("IP地址:", self.manual_ip_edit)

        self.manual_port_spin = QSpinBox()
        self.manual_port_spin.setRange(1024, 65535)
        self.manual_port_spin.setValue(8889)
        manual_layout.addRow("端口:", self.manual_port_spin)

        add_node_btn = QPushButton("添加节点")
        add_node_btn.clicked.connect(self.add_manual_node)
        manual_layout.addRow(add_node_btn)

        layout.addWidget(manual_group)

        # 配置文件
        config_group = QGroupBox("配置文件")
        config_layout = QVBoxLayout(config_group)

        self.config_text = QTextEdit()
        self.config_text.setPlainText(json.dumps({
            "discovery_port": 8888,
            "listen_port": 8889,
            "max_connections": 10,
            "auto_discovery": True,
            "ssl_enabled": False
        }, indent=2))
        config_layout.addWidget(self.config_text)

        config_button_layout = QHBoxLayout()
        load_config_btn = QPushButton("加载配置")
        save_config_btn = QPushButton("保存配置")

        load_config_btn.clicked.connect(self.load_config)
        save_config_btn.clicked.connect(self.save_config)

        config_button_layout.addWidget(load_config_btn)
        config_button_layout.addWidget(save_config_btn)
        config_layout.addLayout(config_button_layout)

        layout.addWidget(config_group)

        return widget

    def connect_signals(self):
        """连接信号"""
        self.node_discovered.connect(self.on_node_discovered)
        self.node_connected.connect(self.on_node_connected)
        self.node_disconnected.connect(self.on_node_disconnected)

    def start_discovery(self):
        """开始节点发现"""
        try:
            interval = self.discovery_interval_spin.value() * 1000  # 转换为毫秒
            self.discovery_timer.start(interval)

            self.start_discovery_btn.setEnabled(False)
            self.stop_discovery_btn.setEnabled(True)

            # 立即执行一次发现
            self.discover_nodes()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动节点发现失败: {str(e)}")

    def stop_discovery(self):
        """停止节点发现"""
        self.discovery_timer.stop()

        self.start_discovery_btn.setEnabled(True)
        self.stop_discovery_btn.setEnabled(False)

    def discover_nodes(self):
        """发现节点"""
        def discovery_worker():
            try:
                # 模拟节点发现
                import random
                if random.random() > 0.7:  # 30%概率发现新节点
                    node_id = f"node_{random.randint(1000, 9999)}"
                    node_data = {
                        'id': node_id,
                        'ip': f"192.168.1.{random.randint(100, 200)}",
                        'port': random.randint(8880, 8890),
                        'status': 'discovered',
                        'type': random.choice(['worker', 'coordinator', 'storage']),
                        'cpu_usage': random.randint(10, 80),
                        'memory_usage': random.randint(20, 90),
                        'task_count': random.randint(0, 10),
                        'last_heartbeat': time.time()
                    }
                    self.node_discovered.emit(node_data)

            except Exception as e:
                print(f"节点发现错误: {e}")

        # 在后台线程中执行发现
        thread = threading.Thread(target=discovery_worker)
        thread.daemon = True
        thread.start()

    def on_node_discovered(self, node_data):
        """处理发现的节点"""
        node_id = node_data['id']
        self.nodes[node_id] = node_data

        # 更新发现表格
        self.update_discovered_table()

        # 如果启用自动连接
        if self.auto_connect_check.isChecked():
            self.connect_to_node(node_id)

    def on_node_connected(self, node_id):
        """处理节点连接"""
        if node_id in self.nodes:
            self.nodes[node_id]['status'] = 'connected'
            self.update_tables()

    def on_node_disconnected(self, node_id):
        """处理节点断开"""
        if node_id in self.nodes:
            self.nodes[node_id]['status'] = 'disconnected'
            self.update_tables()

    def connect_to_node(self, node_id):
        """连接到节点"""
        if node_id in self.nodes:
            # 模拟连接过程
            self.node_connected.emit(node_id)

    def add_manual_node(self):
        """手动添加节点"""
        ip = self.manual_ip_edit.text().strip()
        port = self.manual_port_spin.value()

        if not ip:
            QMessageBox.warning(self, "警告", "请输入IP地址")
            return

        node_id = f"manual_{ip}_{port}"
        node_data = {
            'id': node_id,
            'ip': ip,
            'port': port,
            'status': 'manual',
            'type': 'worker',
            'cpu_usage': 0,
            'memory_usage': 0,
            'task_count': 0,
            'last_heartbeat': time.time()
        }

        self.nodes[node_id] = node_data
        self.update_tables()

        # 清空输入框
        self.manual_ip_edit.clear()

    def refresh_nodes(self):
        """刷新节点信息"""
        # 模拟刷新过程
        for node_id, node_data in self.nodes.items():
            if node_data['status'] == 'connected':
                import random
                node_data['cpu_usage'] = random.randint(10, 80)
                node_data['memory_usage'] = random.randint(20, 90)
                node_data['task_count'] = random.randint(0, 10)
                node_data['last_heartbeat'] = time.time()

        self.update_tables()

    def update_discovered_table(self):
        """更新发现的节点表格"""
        self.discovered_table.setRowCount(len(self.nodes))

        for row, (node_id, node_data) in enumerate(self.nodes.items()):
            self.discovered_table.setItem(row, 0, QTableWidgetItem(node_id))
            self.discovered_table.setItem(
                row, 1, QTableWidgetItem(node_data['ip']))
            self.discovered_table.setItem(
                row, 2, QTableWidgetItem(str(node_data['port'])))
            self.discovered_table.setItem(
                row, 3, QTableWidgetItem(node_data['status']))
            self.discovered_table.setItem(
                row, 4, QTableWidgetItem(node_data['type']))

            # 操作按钮
            if node_data['status'] == 'discovered':
                connect_btn = QPushButton("连接")
                connect_btn.clicked.connect(
                    lambda checked, nid=node_id: self.connect_to_node(nid))
                self.discovered_table.setCellWidget(row, 5, connect_btn)
            else:
                self.discovered_table.setItem(row, 5, QTableWidgetItem("已连接"))

    def update_monitor_table(self):
        """更新监控表格"""
        self.node_details_table.setRowCount(len(self.nodes))

        active_count = 0
        inactive_count = 0

        for row, (node_id, node_data) in enumerate(self.nodes.items()):
            self.node_details_table.setItem(row, 0, QTableWidgetItem(node_id))
            self.node_details_table.setItem(
                row, 1, QTableWidgetItem(node_data['ip']))
            self.node_details_table.setItem(
                row, 2, QTableWidgetItem(str(node_data['port'])))
            self.node_details_table.setItem(
                row, 3, QTableWidgetItem(node_data['status']))
            self.node_details_table.setItem(
                row, 4, QTableWidgetItem(f"{node_data['cpu_usage']}%"))
            self.node_details_table.setItem(
                row, 5, QTableWidgetItem(f"{node_data['memory_usage']}%"))
            self.node_details_table.setItem(
                row, 6, QTableWidgetItem(str(node_data['task_count'])))

            # 格式化最后心跳时间
            last_heartbeat = time.strftime(
                "%H:%M:%S", time.localtime(node_data['last_heartbeat']))
            self.node_details_table.setItem(
                row, 7, QTableWidgetItem(last_heartbeat))

            # 统计活跃节点
            if node_data['status'] == 'connected':
                active_count += 1
            else:
                inactive_count += 1

        # 更新统计标签
        self.total_nodes_label.setText(str(len(self.nodes)))
        self.active_nodes_label.setText(str(active_count))
        self.inactive_nodes_label.setText(str(inactive_count))

    def update_tables(self):
        """更新所有表格"""
        self.update_discovered_table()
        self.update_monitor_table()

    def load_config(self):
        """加载配置"""
        try:
            config_text = self.config_text.toPlainText()
            config = json.loads(config_text)

            # 应用配置
            self.discovery_port_spin.setValue(
                config.get('discovery_port', 8888))
            self.local_port_spin.setValue(config.get('listen_port', 8889))
            self.max_connections_spin.setValue(
                config.get('max_connections', 10))
            self.enable_ssl_check.setChecked(config.get('ssl_enabled', False))

            QMessageBox.information(self, "成功", "配置加载成功")

        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "错误", f"配置文件格式错误: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")

    def save_config(self):
        """保存配置"""
        try:
            config = {
                "discovery_port": self.discovery_port_spin.value(),
                "listen_port": self.local_port_spin.value(),
                "max_connections": self.max_connections_spin.value(),
                "auto_discovery": True,
                "ssl_enabled": self.enable_ssl_check.isChecked()
            }

            self.config_text.setPlainText(json.dumps(config, indent=2))
            QMessageBox.information(self, "成功", "配置保存成功")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")

    def closeEvent(self, event):
        """关闭事件"""
        # 停止发现定时器
        if self.discovery_timer.isActive():
            self.discovery_timer.stop()
        event.accept()
