"""
分布式节点监控对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel, QGroupBox,
                             QHeaderView, QMessageBox, QLineEdit, QSpinBox,
                             QFormLayout, QDialogButtonBox, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QColor
from loguru import logger
from datetime import datetime
from typing import List, Dict, Any


class NodeStatsWorker(QThread):
    """后台节点状态获取线程"""
    stats_ready = pyqtSignal(list)  # 发送节点状态列表

    def __init__(self, distributed_service, parent=None):
        super().__init__(parent)
        self.distributed_service = distributed_service
        self._running = True

    def run(self):
        """在后台线程中获取节点状态"""
        try:
            if self._running:
                nodes = self.distributed_service.get_all_nodes_status()
                self.stats_ready.emit(nodes)
        except Exception as e:
            logger.error(f"后台获取节点状态失败: {e}")

    def stop(self):
        """停止线程"""
        self._running = False


class AddNodeDialog(QDialog):
    """添加节点对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加分布式节点")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()

        # 节点ID
        self.node_id_input = QLineEdit()
        self.node_id_input.setPlaceholderText("worker-1")
        layout.addRow("节点ID:", self.node_id_input)

        # 主机地址
        self.host_input = QLineEdit()
        self.host_input.setText("127.0.0.1")
        layout.addRow("主机地址:", self.host_input)

        # 端口
        self.port_input = QSpinBox()
        self.port_input.setRange(5000, 65535)
        self.port_input.setValue(8000)
        layout.addRow("端口:", self.port_input)

        # 节点类型
        self.node_type_input = QLineEdit()
        self.node_type_input.setText("worker")
        layout.addRow("节点类型:", self.node_type_input)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def get_node_config(self) -> Dict[str, Any]:
        """获取节点配置"""
        return {
            "node_id": self.node_id_input.text().strip(),
            "host": self.host_input.text().strip(),
            "port": self.port_input.value(),
            "node_type": self.node_type_input.text().strip()
        }


class DistributedNodeMonitorDialog(QDialog):
    """分布式节点监控对话框"""

    node_status_updated = pyqtSignal(list)  # 节点状态更新信号

    def __init__(self, distributed_service, parent=None):
        super().__init__(parent)
        self.distributed_service = distributed_service
        self.setWindowTitle("分布式节点监控")
        self.setMinimumSize(1000, 600)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_nodes)

        # 后台工作线程（用于异步获取节点状态）
        self.stats_worker = None

        self.init_ui()
        self.refresh_nodes()

        # 每5秒自动刷新
        self.update_timer.start(5000)

    def init_ui(self):
        layout = QVBoxLayout()

        # 标题和统计信息
        header_layout = QHBoxLayout()
        self.title_label = QLabel("<h2>分布式节点监控</h2>")
        self.stats_label = QLabel("总节点: 0 | 活跃: 0 | 忙碌: 0 | 离线: 0")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.stats_label)
        layout.addLayout(header_layout)

        # 操作按钮组
        button_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.refresh_nodes)
        button_layout.addWidget(self.refresh_btn)

        self.add_node_btn = QPushButton("➕ 添加节点")
        self.add_node_btn.clicked.connect(self.add_node)
        button_layout.addWidget(self.add_node_btn)

        self.remove_node_btn = QPushButton("➖ 移除节点")
        self.remove_node_btn.clicked.connect(self.remove_node)
        button_layout.addWidget(self.remove_node_btn)

        self.test_node_btn = QPushButton("🧪 测试节点")
        self.test_node_btn.clicked.connect(self.test_node)
        button_layout.addWidget(self.test_node_btn)

        button_layout.addStretch()

        self.auto_refresh_btn = QPushButton("⏸️ 暂停刷新")
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.clicked.connect(self.toggle_auto_refresh)
        button_layout.addWidget(self.auto_refresh_btn)

        layout.addLayout(button_layout)

        # 节点列表表格
        self.nodes_table = QTableWidget()
        self.nodes_table.setColumnCount(10)
        self.nodes_table.setHorizontalHeaderLabels([
            "节点ID", "地址", "状态", "类型", "CPU使用率",
            "内存使用率", "当前任务", "运行时间", "最后心跳", "功能支持"
        ])
        self.nodes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.nodes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.nodes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.nodes_table)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

        # 连接行选择信号
        # self.nodes_table.itemSelectionChanged.connect(self.on_node_selected)

    def refresh_nodes(self):
        """刷新节点列表（异步版本）"""
        try:
            # 检查是否有工作线程且正在运行
            if self.stats_worker is not None:
                try:
                    if self.stats_worker.isRunning():
                        return  # 跳过本次刷新，等待上次完成
                except RuntimeError:
                    # 对象已被删除，清空引用
                    self.stats_worker = None

            # 创建新的工作线程
            self.stats_worker = NodeStatsWorker(self.distributed_service, self)
            self.stats_worker.stats_ready.connect(self._update_nodes_table)
            # 线程完成后清空引用，但不立即删除
            self.stats_worker.finished.connect(self._on_worker_finished)
            self.stats_worker.start()
        except Exception as e:
            logger.error(f"刷新节点失败: {e}")

    def _on_worker_finished(self):
        """工作线程完成回调"""
        # 延迟删除，避免过早释放
        if self.stats_worker:
            self.stats_worker.deleteLater()
            self.stats_worker = None

    @pyqtSlot(list)
    def _update_nodes_table(self, nodes):
        """更新节点表格（在主线程中执行）"""
        try:
            # 更新统计信息
            total = len(nodes)
            active = sum(1 for n in nodes if n.get('status') == 'active')
            busy = sum(1 for n in nodes if n.get('status') == 'busy')
            offline = sum(1 for n in nodes if n.get('status') == 'offline')

            self.stats_label.setText(
                f"总节点: {total} | 活跃: {active} | 忙碌: {busy} | 离线: {offline}"
            )

            # 更新表格
            self.nodes_table.setRowCount(len(nodes))

            for row, node in enumerate(nodes):
                # 节点ID
                self.nodes_table.setItem(row, 0, QTableWidgetItem(node.get('node_id', 'N/A')))

                # 地址
                address = f"{node.get('host', 'N/A')}:{node.get('port', 'N/A')}"
                self.nodes_table.setItem(row, 1, QTableWidgetItem(address))

                # 状态（带颜色）
                status_item = QTableWidgetItem(node.get('status', 'unknown'))
                status = node.get('status', 'unknown')
                if status == 'active':
                    status_item.setBackground(QColor(144, 238, 144))  # 绿色
                elif status == 'busy':
                    status_item.setBackground(QColor(255, 255, 0))  # 黄色
                elif status == 'offline':
                    status_item.setBackground(QColor(255, 182, 193))  # 红色
                self.nodes_table.setItem(row, 2, status_item)

                # 类型
                self.nodes_table.setItem(row, 3, QTableWidgetItem(node.get('node_type', 'N/A')))

                # CPU使用率
                cpu_usage = node.get('cpu_usage_percent', 0)
                self.nodes_table.setItem(row, 4, QTableWidgetItem(f"{cpu_usage:.1f}%"))

                # 内存使用率
                mem_usage = node.get('memory_usage_percent', 0)
                self.nodes_table.setItem(row, 5, QTableWidgetItem(f"{mem_usage:.1f}%"))

                # 当前任务数
                current_tasks = node.get('current_tasks', 0)
                self.nodes_table.setItem(row, 6, QTableWidgetItem(str(current_tasks)))

                # 运行时间
                uptime = node.get('uptime_seconds', 0)
                uptime_str = self._format_uptime(uptime)
                self.nodes_table.setItem(row, 7, QTableWidgetItem(uptime_str))

                # 最后心跳
                last_heartbeat = node.get('last_heartbeat')
                if last_heartbeat:
                    if isinstance(last_heartbeat, datetime):
                        heartbeat_str = last_heartbeat.strftime("%H:%M:%S")
                    else:
                        heartbeat_str = str(last_heartbeat)
                else:
                    heartbeat_str = "N/A"
                self.nodes_table.setItem(row, 8, QTableWidgetItem(heartbeat_str))

                # 功能支持
                capabilities = node.get('capabilities', [])
                self.nodes_table.setItem(row, 9, QTableWidgetItem(', '.join(capabilities)))

            # 发送信号
            self.node_status_updated.emit(nodes)

        except Exception as e:
            logger.error(f"刷新节点列表失败: {e}")
            QMessageBox.warning(self, "错误", f"刷新节点列表失败: {e}")

    def _format_uptime(self, seconds: int) -> str:
        """格式化运行时间"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        elif seconds < 86400:
            return f"{seconds // 3600}小时"
        else:
            return f"{seconds // 86400}天"

    def add_node(self):
        """添加节点"""
        dialog = AddNodeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_node_config()

            if not config['node_id'] or not config['host']:
                QMessageBox.warning(self, "警告", "节点ID和主机地址不能为空")
                return

            try:
                # 添加节点到服务
                success = self.distributed_service.add_node(
                    node_id=config['node_id'],
                    host=config['host'],
                    port=config['port'],
                    node_type=config['node_type']
                )

                if success:
                    QMessageBox.information(self, "成功", f"节点 {config['node_id']} 已添加")
                    self.refresh_nodes()
                else:
                    # 添加失败，可能是节点已存在
                    QMessageBox.warning(
                        self, "失败",
                        f"添加节点失败：节点 '{config['node_id']}' 可能已存在，请使用不同的节点ID"
                    )

            except Exception as e:
                logger.error(f"添加节点失败: {e}")
                QMessageBox.critical(self, "错误", f"添加节点失败: {e}")

    def remove_node(self):
        """移除节点"""
        selected_rows = self.nodes_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要移除的节点")
            return

        row = selected_rows[0].row()
        node_id = self.nodes_table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "确认", f"确定要移除节点 {node_id} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                success = self.distributed_service.remove_node(node_id)
                if success:
                    QMessageBox.information(self, "成功", f"节点 {node_id} 已移除")
                    self.refresh_nodes()
                else:
                    QMessageBox.warning(self, "失败", "移除节点失败")
            except Exception as e:
                logger.error(f"移除节点失败: {e}")
                QMessageBox.critical(self, "错误", f"移除节点失败: {e}")

    def test_node(self):
        """测试节点连接"""
        selected_rows = self.nodes_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要测试的节点")
            return

        row = selected_rows[0].row()
        node_id = self.nodes_table.item(row, 0).text()

        try:
            # 测试节点连接
            result = self.distributed_service.test_node_connection(node_id)

            if result and result.get('success'):
                response_time = result.get('response_time', 'N/A')
                capabilities = result.get('capabilities', [])
                capabilities_str = ', '.join(capabilities) if capabilities else '未知'

                message = f"节点 {node_id} 连接正常\n响应时间: {response_time}ms\n支持功能: {capabilities_str}"
                QMessageBox.information(self, "测试成功", message)

                # 刷新节点列表以更新状态
                self.refresh_nodes()
            else:
                error_msg = result.get('error', '未知错误') if result else '无响应'
                QMessageBox.warning(
                    self, "测试失败",
                    f"节点 {node_id} 无法连接\n错误: {error_msg}"
                )
                # 刷新节点列表以更新状态
                self.refresh_nodes()

        except Exception as e:
            logger.error(f"测试节点失败: {e}")
            QMessageBox.critical(self, "错误", f"测试节点失败: {e}")

    def toggle_auto_refresh(self):
        """切换自动刷新"""
        if self.auto_refresh_btn.isChecked():
            self.update_timer.stop()
            self.auto_refresh_btn.setText("▶️ 继续刷新")
        else:
            self.update_timer.start(5000)
            self.auto_refresh_btn.setText("⏸️ 暂停刷新")

    def closeEvent(self, event):
        """关闭事件"""
        self.update_timer.stop()

        # 停止并等待工作线程完成
        if self.stats_worker is not None:
            try:
                if self.stats_worker.isRunning():
                    self.stats_worker.stop()
                    self.stats_worker.wait(1000)  # 最多等待1秒
            except RuntimeError:
                # 对象已被删除，忽略
                pass

        event.accept()
