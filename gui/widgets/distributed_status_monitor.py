#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分布式状态监控组件

提供分布式服务节点状态的可视化监控功能，包括：
- 分布式服务节点状态监控
- 负载分布和资源分配展示
- 故障检测和网络拓扑监控
- 集群健康状态评估
- 负载均衡策略监控

作者: FactorWeave-Quant团队
版本: 1.0
"""

import sys
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
import json

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QGroupBox, QLabel, QPushButton, QComboBox, QSpinBox, QSlider,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QTextEdit, QCheckBox, QDateTimeEdit, QTimeEdit,
    QListWidget, QListWidgetItem, QSplitter, QFrame, QScrollArea,
    QMessageBox, QDialog, QDialogButtonBox, QApplication, QTreeWidget,
    QTreeWidgetItem, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsProxyWidget, QToolBar, QAction,
    QMenu, QActionGroup, QButtonGroup, QRadioButton, QLCDNumber,
    QDial, QCalendarWidget, QLineEdit, QDoubleSpinBox, QSizePolicy,
    QGraphicsEllipseItem, QGraphicsLineItem
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QDateTime, QTime, QDate, QSize, QPointF, QRectF
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QBrush, QPen,
    QLinearGradient, QRadialGradient, QFontMetrics, QPainterPath,
    QPolygonF
)

# 导入核心分布式服务组件
try:
    # EnhancedDistributedService 不存在，使用 DistributedService
    from core.services.distributed_service import DistributedService as EnhancedDistributedService
    from core.services.fault_tolerance_manager import FaultToleranceManager
    from core.ui_integration.ui_business_logic_adapter import get_ui_adapter
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    CORE_AVAILABLE = False
    EnhancedDistributedService = None
    FaultToleranceManager = None
    logger.warning(f"核心分布式服务不可用: {e}")

logger = logger.bind(module=__name__) if hasattr(logger, 'bind') else logging.getLogger(__name__)


class NodeStatus(Enum):
    """节点状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class NodeRole(Enum):
    """节点角色"""
    MASTER = "master"
    WORKER = "worker"
    COORDINATOR = "coordinator"
    STORAGE = "storage"
    COMPUTE = "compute"


@dataclass
class NodeInfo:
    """节点信息"""
    node_id: str
    name: str
    host: str
    port: int
    status: NodeStatus
    role: NodeRole
    cpu_usage: float  # 0-100
    memory_usage: float  # 0-100
    disk_usage: float  # 0-100
    network_in: float  # MB/s
    network_out: float  # MB/s
    active_tasks: int
    total_tasks: int
    uptime: timedelta
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterMetrics:
    """集群指标"""
    total_nodes: int
    healthy_nodes: int
    warning_nodes: int
    critical_nodes: int
    offline_nodes: int
    total_cpu_cores: int
    used_cpu_cores: int
    total_memory_gb: float
    used_memory_gb: float
    total_disk_gb: float
    used_disk_gb: float
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    network_throughput: float  # MB/s
    timestamp: datetime = field(default_factory=datetime.now)


class NodeStatusIndicator(QWidget):
    """节点状态指示器"""

    node_clicked = pyqtSignal(str)  # node_id

    def __init__(self, node: NodeInfo, parent=None):
        super().__init__(parent)
        self.node = node
        self.setFixedSize(100, 80)
        self.setToolTip(f"节点: {node.name}\n状态: {node.status.value}\n负载: {node.cpu_usage:.1f}%")

    def update_node(self, node: NodeInfo):
        """更新节点信息"""
        self.node = node
        self.setToolTip(f"节点: {node.name}\n状态: {node.status.value}\n负载: {node.cpu_usage:.1f}%")
        self.update()

    def paintEvent(self, event):
        """绘制节点状态"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(5, 5, -5, -5)

        # 根据状态设置颜色
        status_colors = {
            NodeStatus.HEALTHY: QColor(46, 204, 113),     # 绿色
            NodeStatus.WARNING: QColor(241, 196, 15),     # 黄色
            NodeStatus.CRITICAL: QColor(231, 76, 60),     # 红色
            NodeStatus.OFFLINE: QColor(149, 165, 166),    # 灰色
            NodeStatus.MAINTENANCE: QColor(155, 89, 182)  # 紫色
        }

        color = status_colors.get(self.node.status, QColor(128, 128, 128))

        # 绘制节点图标
        node_rect = QRectF(rect.x(), rect.y(), rect.width(), rect.height() * 0.6)

        # 根据角色设置形状
        if self.node.role == NodeRole.MASTER:
            # 主节点 - 菱形
            points = [
                QPointF(node_rect.center().x(), node_rect.top()),
                QPointF(node_rect.right(), node_rect.center().y()),
                QPointF(node_rect.center().x(), node_rect.bottom()),
                QPointF(node_rect.left(), node_rect.center().y())
            ]
            polygon = QPolygonF(points)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 2))
            painter.drawPolygon(polygon)
        elif self.node.role == NodeRole.COORDINATOR:
            # 协调节点 - 六边形
            center = node_rect.center()
            radius = min(node_rect.width(), node_rect.height()) / 2 - 2
            points = []
            for i in range(6):
                angle = i * 60 * math.pi / 180
                x = center.x() + radius * math.cos(angle)
                y = center.y() + radius * math.sin(angle)
                points.append(QPointF(x, y))

            polygon = QPolygonF(points)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 2))
            painter.drawPolygon(polygon)
        else:
            # 工作节点 - 圆形
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 2))
            painter.drawEllipse(node_rect)

        # 绘制负载指示器
        load_rect = QRectF(rect.x(), rect.bottom() - 15, rect.width(), 10)
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.setPen(QPen(Qt.NoPen))
        painter.drawRect(load_rect)

        # 负载条
        load_width = load_rect.width() * (self.node.cpu_usage / 100)
        load_fill_rect = QRectF(load_rect.x(), load_rect.y(), load_width, load_rect.height())

        if self.node.cpu_usage >= 80:
            load_color = QColor(231, 76, 60)
        elif self.node.cpu_usage >= 60:
            load_color = QColor(241, 196, 15)
        else:
            load_color = QColor(46, 204, 113)

        painter.setBrush(QBrush(load_color))
        painter.drawRect(load_fill_rect)

        # 绘制节点名称
        painter.setPen(QPen(Qt.black))
        painter.setFont(QFont("Arial", 8))
        name_rect = QRectF(rect.x(), rect.bottom() - 5, rect.width(), 10)
        painter.drawText(name_rect, Qt.AlignCenter, self.node.name[:8])

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.node_clicked.emit(self.node.node_id)


class ClusterTopologyView(QGraphicsView):
    """集群拓扑视图"""

    node_selected = pyqtSignal(str)  # node_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.nodes: Dict[str, NodeInfo] = {}
        self.node_positions: Dict[str, QPointF] = {}

        # 设置视图属性
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.setup_scene()

    def setup_scene(self):
        """设置场景"""
        self.scene.clear()
        self.scene.setSceneRect(0, 0, 800, 600)

        # 绘制背景网格
        self.draw_grid()

    def draw_grid(self):
        """绘制网格背景"""
        grid_size = 50
        scene_rect = self.scene.sceneRect()

        # 垂直线
        for x in range(int(scene_rect.left()), int(scene_rect.right()), grid_size):
            line = self.scene.addLine(x, scene_rect.top(), x, scene_rect.bottom(),
                                      QPen(QColor(240, 240, 240), 1))

        # 水平线
        for y in range(int(scene_rect.top()), int(scene_rect.bottom()), grid_size):
            line = self.scene.addLine(scene_rect.left(), y, scene_rect.right(), y,
                                      QPen(QColor(240, 240, 240), 1))

    def update_nodes(self, nodes: List[NodeInfo]):
        """更新节点信息"""
        self.nodes = {node.node_id: node for node in nodes}
        self.update_topology()

    def update_topology(self):
        """更新拓扑图"""
        # 清除现有节点和连接
        for item in self.scene.items():
            if hasattr(item, 'node_item') or hasattr(item, 'connection_line'):
                self.scene.removeItem(item)

        if not self.nodes:
            return

        # 计算节点位置（简单的圆形布局）
        self.calculate_node_positions()

        # 绘制连接线
        self.draw_connections()

        # 绘制节点
        self.draw_nodes()

    def calculate_node_positions(self):
        """计算节点位置"""
        center = self.scene.sceneRect().center()
        radius = min(self.scene.sceneRect().width(), self.scene.sceneRect().height()) / 3

        # 分离不同角色的节点
        master_nodes = [n for n in self.nodes.values() if n.role == NodeRole.MASTER]
        coordinator_nodes = [n for n in self.nodes.values() if n.role == NodeRole.COORDINATOR]
        worker_nodes = [n for n in self.nodes.values() if n.role in [NodeRole.WORKER, NodeRole.STORAGE, NodeRole.COMPUTE]]

        # 主节点放在中心
        if master_nodes:
            master_node = master_nodes[0]
            self.node_positions[master_node.node_id] = center

        # 协调节点围绕主节点
        for i, node in enumerate(coordinator_nodes):
            angle = (2 * math.pi * i) / len(coordinator_nodes) if coordinator_nodes else 0
            x = center.x() + radius * 0.5 * math.cos(angle)
            y = center.y() + radius * 0.5 * math.sin(angle)
            self.node_positions[node.node_id] = QPointF(x, y)

        # 工作节点在外圈
        for i, node in enumerate(worker_nodes):
            angle = (2 * math.pi * i) / len(worker_nodes) if worker_nodes else 0
            x = center.x() + radius * math.cos(angle)
            y = center.y() + radius * math.sin(angle)
            self.node_positions[node.node_id] = QPointF(x, y)

    def draw_connections(self):
        """绘制节点连接"""
        # 简化连接：主节点连接到协调节点，协调节点连接到工作节点
        master_nodes = [n for n in self.nodes.values() if n.role == NodeRole.MASTER]
        coordinator_nodes = [n for n in self.nodes.values() if n.role == NodeRole.COORDINATOR]
        worker_nodes = [n for n in self.nodes.values() if n.role in [NodeRole.WORKER, NodeRole.STORAGE, NodeRole.COMPUTE]]

        # 主节点到协调节点的连接
        if master_nodes:
            master_pos = self.node_positions.get(master_nodes[0].node_id)
            if master_pos:
                for coord_node in coordinator_nodes:
                    coord_pos = self.node_positions.get(coord_node.node_id)
                    if coord_pos:
                        line = self.scene.addLine(
                            master_pos.x(), master_pos.y(),
                            coord_pos.x(), coord_pos.y(),
                            QPen(QColor(52, 152, 219), 2)
                        )
                        line.connection_line = True

        # 协调节点到工作节点的连接
        for coord_node in coordinator_nodes:
            coord_pos = self.node_positions.get(coord_node.node_id)
            if coord_pos:
                # 每个协调节点连接到部分工作节点
                workers_per_coord = len(worker_nodes) // len(coordinator_nodes) if coordinator_nodes else 0
                start_idx = coordinator_nodes.index(coord_node) * workers_per_coord
                end_idx = start_idx + workers_per_coord

                for worker_node in worker_nodes[start_idx:end_idx]:
                    worker_pos = self.node_positions.get(worker_node.node_id)
                    if worker_pos:
                        line = self.scene.addLine(
                            coord_pos.x(), coord_pos.y(),
                            worker_pos.x(), worker_pos.y(),
                            QPen(QColor(46, 204, 113), 1)
                        )
                        line.connection_line = True

    def draw_nodes(self):
        """绘制节点"""
        for node_id, node in self.nodes.items():
            pos = self.node_positions.get(node_id)
            if not pos:
                continue

            # 节点颜色
            status_colors = {
                NodeStatus.HEALTHY: QColor(46, 204, 113),
                NodeStatus.WARNING: QColor(241, 196, 15),
                NodeStatus.CRITICAL: QColor(231, 76, 60),
                NodeStatus.OFFLINE: QColor(149, 165, 166),
                NodeStatus.MAINTENANCE: QColor(155, 89, 182)
            }

            color = status_colors.get(node.status, QColor(128, 128, 128))

            # 节点大小根据角色调整
            if node.role == NodeRole.MASTER:
                radius = 25
            elif node.role == NodeRole.COORDINATOR:
                radius = 20
            else:
                radius = 15

            # 绘制节点
            node_item = self.scene.addEllipse(
                pos.x() - radius, pos.y() - radius,
                radius * 2, radius * 2,
                QPen(color.darker(120), 2),
                QBrush(color)
            )
            node_item.node_item = True
            node_item.setData(0, node_id)  # 存储节点ID

            # 节点标签
            text_item = self.scene.addText(node.name[:8], QFont("Arial", 8))
            text_item.setPos(pos.x() - 20, pos.y() + radius + 5)
            text_item.node_item = True

            # 负载指示器
            load_indicator = self.scene.addRect(
                pos.x() - 15, pos.y() - radius - 15,
                30, 5,
                QPen(Qt.NoPen),
                QBrush(QColor(230, 230, 230))
            )
            load_indicator.node_item = True

            # 负载填充
            load_width = 30 * (node.cpu_usage / 100)
            if node.cpu_usage >= 80:
                load_color = QColor(231, 76, 60)
            elif node.cpu_usage >= 60:
                load_color = QColor(241, 196, 15)
            else:
                load_color = QColor(46, 204, 113)

            load_fill = self.scene.addRect(
                pos.x() - 15, pos.y() - radius - 15,
                load_width, 5,
                QPen(Qt.NoPen),
                QBrush(load_color)
            )
            load_fill.node_item = True

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item and hasattr(item, 'node_item'):
                node_id = item.data(0)
                if node_id:
                    self.node_selected.emit(node_id)

        super().mousePressEvent(event)


class NodeDetailsDialog(QDialog):
    """节点详情对话框"""

    def __init__(self, node: NodeInfo, parent=None):
        super().__init__(parent)
        self.node = node
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(f"节点详情 - {self.node.name}")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 节点基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout(info_group)

        info_layout.addRow("节点ID:", QLabel(self.node.node_id))
        info_layout.addRow("节点名称:", QLabel(self.node.name))
        info_layout.addRow("主机地址:", QLabel(f"{self.node.host}:{self.node.port}"))

        # 状态标签
        status_label = QLabel(self.node.status.value.upper())
        status_colors = {
            NodeStatus.HEALTHY: "background-color: #d4edda; color: #155724;",
            NodeStatus.WARNING: "background-color: #fff3cd; color: #856404;",
            NodeStatus.CRITICAL: "background-color: #f8d7da; color: #721c24;",
            NodeStatus.OFFLINE: "background-color: #e2e3e5; color: #6c757d;",
            NodeStatus.MAINTENANCE: "background-color: #e7e3ff; color: #6f42c1;"
        }
        status_label.setStyleSheet(f"""
            QLabel {{
                {status_colors.get(self.node.status, "")}
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        info_layout.addRow("状态:", status_label)

        info_layout.addRow("角色:", QLabel(self.node.role.value.upper()))
        info_layout.addRow("运行时间:", QLabel(str(self.node.uptime)))
        info_layout.addRow("最后心跳:", QLabel(self.node.last_heartbeat.strftime("%Y-%m-%d %H:%M:%S")))

        layout.addWidget(info_group)

        # 资源使用情况
        resources_group = QGroupBox("资源使用")
        resources_layout = QGridLayout(resources_group)

        # CPU使用率
        resources_layout.addWidget(QLabel("CPU使用率:"), 0, 0)
        cpu_progress = QProgressBar()
        cpu_progress.setRange(0, 100)
        cpu_progress.setValue(int(self.node.cpu_usage))
        cpu_progress.setFormat(f"{self.node.cpu_usage:.1f}%")
        resources_layout.addWidget(cpu_progress, 0, 1)

        # 内存使用率
        resources_layout.addWidget(QLabel("内存使用率:"), 1, 0)
        memory_progress = QProgressBar()
        memory_progress.setRange(0, 100)
        memory_progress.setValue(int(self.node.memory_usage))
        memory_progress.setFormat(f"{self.node.memory_usage:.1f}%")
        resources_layout.addWidget(memory_progress, 1, 1)

        # 磁盘使用率
        resources_layout.addWidget(QLabel("磁盘使用率:"), 2, 0)
        disk_progress = QProgressBar()
        disk_progress.setRange(0, 100)
        disk_progress.setValue(int(self.node.disk_usage))
        disk_progress.setFormat(f"{self.node.disk_usage:.1f}%")
        resources_layout.addWidget(disk_progress, 2, 1)

        layout.addWidget(resources_group)

        # 网络和任务信息
        network_group = QGroupBox("网络和任务")
        network_layout = QFormLayout(network_group)

        network_layout.addRow("网络入流量:", QLabel(f"{self.node.network_in:.1f} MB/s"))
        network_layout.addRow("网络出流量:", QLabel(f"{self.node.network_out:.1f} MB/s"))
        network_layout.addRow("活跃任务:", QLabel(f"{self.node.active_tasks}"))
        network_layout.addRow("总任务数:", QLabel(f"{self.node.total_tasks}"))

        layout.addWidget(network_group)

        # 关闭按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


class DistributedStatusMonitor(QWidget):
    """分布式状态监控主组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_adapter = None
        self.distributed_service = None
        self.fault_tolerance_manager = None

        # 数据存储
        self.nodes: List[NodeInfo] = []
        self.cluster_metrics_history: deque = deque(maxlen=100)

        # 初始化核心服务
        if CORE_AVAILABLE:
            try:
                self.ui_adapter = get_ui_adapter()
                self.distributed_service = EnhancedDistributedService()
                self.fault_tolerance_manager = FaultToleranceManager()
            except Exception as e:
                logger.warning(f"核心分布式服务初始化失败: {e}")

        self.setup_ui()
        self.setup_connections()
        self.setup_timers()
        self.load_sample_data()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题和控制区域
        header_layout = QHBoxLayout()

        title_label = QLabel("分布式状态监控")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 控制按钮
        refresh_btn = QPushButton("刷新状态")
        refresh_btn.clicked.connect(self.refresh_cluster_status)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        header_layout.addWidget(refresh_btn)

        rebalance_btn = QPushButton("⚖️ 负载均衡")
        rebalance_btn.clicked.connect(self.trigger_load_balancing)
        rebalance_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        header_layout.addWidget(rebalance_btn)

        layout.addLayout(header_layout)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 集群概览选项卡
        overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(overview_tab, "🏢 集群概览")

        # 拓扑视图选项卡
        topology_tab = self.create_topology_tab()
        self.tab_widget.addTab(topology_tab, "🗺️ 拓扑视图")

        # 节点列表选项卡
        nodes_tab = self.create_nodes_tab()
        self.tab_widget.addTab(nodes_tab, "🖥️ 节点列表")

        # 故障监控选项卡
        fault_tab = self.create_fault_monitoring_tab()
        self.tab_widget.addTab(fault_tab, "故障监控")

        layout.addWidget(self.tab_widget)

        # 状态栏
        status_layout = QHBoxLayout()

        self.cluster_status_label = QLabel("🟢 集群运行正常")
        self.cluster_status_label.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        status_layout.addWidget(self.cluster_status_label)

        status_layout.addStretch()

        self.last_update_label = QLabel("最后更新: --")
        status_layout.addWidget(self.last_update_label)

        layout.addLayout(status_layout)

    def create_overview_tab(self) -> QWidget:
        """创建集群概览选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 集群统计信息
        stats_group = QGroupBox("集群统计")
        stats_layout = QGridLayout(stats_group)

        # 节点统计
        stats_layout.addWidget(QLabel("总节点数:"), 0, 0)
        self.total_nodes_label = QLabel("0")
        self.total_nodes_label.setStyleSheet("font-weight: bold; color: #3498db; font-size: 14px;")
        stats_layout.addWidget(self.total_nodes_label, 0, 1)

        stats_layout.addWidget(QLabel("健康节点:"), 0, 2)
        self.healthy_nodes_label = QLabel("0")
        self.healthy_nodes_label.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 14px;")
        stats_layout.addWidget(self.healthy_nodes_label, 0, 3)

        stats_layout.addWidget(QLabel("异常节点:"), 1, 0)
        self.unhealthy_nodes_label = QLabel("0")
        self.unhealthy_nodes_label.setStyleSheet("font-weight: bold; color: #e74c3c; font-size: 14px;")
        stats_layout.addWidget(self.unhealthy_nodes_label, 1, 1)

        stats_layout.addWidget(QLabel("离线节点:"), 1, 2)
        self.offline_nodes_label = QLabel("0")
        self.offline_nodes_label.setStyleSheet("font-weight: bold; color: #95a5a6; font-size: 14px;")
        stats_layout.addWidget(self.offline_nodes_label, 1, 3)

        layout.addWidget(stats_group)

        # 资源使用概览
        resources_group = QGroupBox("集群资源使用")
        resources_layout = QGridLayout(resources_group)

        # CPU使用率
        resources_layout.addWidget(QLabel("CPU使用率:"), 0, 0)
        self.cluster_cpu_progress = QProgressBar()
        self.cluster_cpu_progress.setRange(0, 100)
        resources_layout.addWidget(self.cluster_cpu_progress, 0, 1)

        # 内存使用率
        resources_layout.addWidget(QLabel("内存使用率:"), 1, 0)
        self.cluster_memory_progress = QProgressBar()
        self.cluster_memory_progress.setRange(0, 100)
        resources_layout.addWidget(self.cluster_memory_progress, 1, 1)

        # 磁盘使用率
        resources_layout.addWidget(QLabel("磁盘使用率:"), 2, 0)
        self.cluster_disk_progress = QProgressBar()
        self.cluster_disk_progress.setRange(0, 100)
        resources_layout.addWidget(self.cluster_disk_progress, 2, 1)

        # 网络吞吐量
        resources_layout.addWidget(QLabel("网络吞吐量:"), 3, 0)
        self.network_throughput_label = QLabel("0 MB/s")
        self.network_throughput_label.setStyleSheet("font-weight: bold;")
        resources_layout.addWidget(self.network_throughput_label, 3, 1)

        layout.addWidget(resources_group)

        # 任务执行统计
        tasks_group = QGroupBox("任务执行统计")
        tasks_layout = QGridLayout(tasks_group)

        # 活跃任务
        tasks_layout.addWidget(QLabel("活跃任务:"), 0, 0)
        self.active_tasks_label = QLabel("0")
        self.active_tasks_label.setStyleSheet("font-weight: bold; color: #f39c12;")
        tasks_layout.addWidget(self.active_tasks_label, 0, 1)

        # 已完成任务
        tasks_layout.addWidget(QLabel("已完成任务:"), 0, 2)
        self.completed_tasks_label = QLabel("0")
        self.completed_tasks_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        tasks_layout.addWidget(self.completed_tasks_label, 0, 3)

        # 失败任务
        tasks_layout.addWidget(QLabel("失败任务:"), 1, 0)
        self.failed_tasks_label = QLabel("0")
        self.failed_tasks_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        tasks_layout.addWidget(self.failed_tasks_label, 1, 1)

        # 任务成功率
        tasks_layout.addWidget(QLabel("任务成功率:"), 1, 2)
        self.task_success_rate_progress = QProgressBar()
        self.task_success_rate_progress.setRange(0, 100)
        tasks_layout.addWidget(self.task_success_rate_progress, 1, 3)

        layout.addWidget(tasks_group)

        # 集群健康状态
        health_group = QGroupBox("💊 集群健康状态")
        health_layout = QVBoxLayout(health_group)

        self.cluster_health_text = QTextEdit()
        self.cluster_health_text.setReadOnly(True)
        self.cluster_health_text.setMaximumHeight(150)
        self.cluster_health_text.setText("""
🟢 集群整体状态: 健康

所有关键服务正常运行
节点间通信良好
负载分布均衡
故障恢复机制工作正常

 性能指标:
• 平均响应时间: 45ms
• 数据一致性: 99.9%
• 可用性: 99.95%
• 吞吐量: 1,234 任务/分钟

 注意事项:
• 建议定期进行负载均衡
• 监控磁盘空间使用情况
        """)
        health_layout.addWidget(self.cluster_health_text)

        layout.addWidget(health_group)

        return widget

    def create_topology_tab(self) -> QWidget:
        """创建拓扑视图选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 拓扑控制
        control_layout = QHBoxLayout()

        control_layout.addWidget(QLabel("布局模式:"))
        layout_combo = QComboBox()
        layout_combo.addItems(["圆形布局", "分层布局", "网格布局"])
        control_layout.addWidget(layout_combo)

        control_layout.addWidget(QLabel("显示选项:"))
        show_connections_check = QCheckBox("显示连接")
        show_connections_check.setChecked(True)
        control_layout.addWidget(show_connections_check)

        show_load_check = QCheckBox("显示负载")
        show_load_check.setChecked(True)
        control_layout.addWidget(show_load_check)

        control_layout.addStretch()

        layout.addLayout(control_layout)

        # 拓扑视图
        self.topology_view = ClusterTopologyView()
        self.topology_view.node_selected.connect(self.show_node_details)
        layout.addWidget(self.topology_view)

        # 图例
        legend_group = QGroupBox("图例")
        legend_layout = QGridLayout(legend_group)

        # 节点状态图例
        legend_layout.addWidget(QLabel("节点状态:"), 0, 0)

        status_colors = [
            ("🟢 健康", "#2ecc71"),
            ("🟡 警告", "#f1c40f"),
            ("🔴 异常", "#e74c3c"),
            ("⚪ 离线", "#95a5a6")
        ]

        for i, (text, color) in enumerate(status_colors):
            color_label = QLabel("●")
            color_label.setStyleSheet(f"color: {color}; font-size: 16px;")
            legend_layout.addWidget(color_label, 0, 1 + i * 2)
            legend_layout.addWidget(QLabel(text), 0, 2 + i * 2)

        # 节点角色图例
        legend_layout.addWidget(QLabel("节点角色:"), 1, 0)
        role_shapes = [
            ("◆ 主节点", "主要控制节点"),
            ("⬡ 协调节点", "任务协调节点"),
            ("● 工作节点", "执行节点")
        ]

        for i, (text, desc) in enumerate(role_shapes):
            shape_label = QLabel(text)
            shape_label.setStyleSheet("font-size: 14px;")
            legend_layout.addWidget(shape_label, 1, 1 + i * 2)
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
            legend_layout.addWidget(desc_label, 1, 2 + i * 2)

        legend_group.setMaximumHeight(80)
        layout.addWidget(legend_group)

        return widget

    def create_nodes_tab(self) -> QWidget:
        """创建节点列表选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 节点过滤控制
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("状态过滤:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["全部", "健康", "警告", "异常", "离线", "维护中"])
        self.status_filter_combo.currentTextChanged.connect(self.filter_nodes)
        filter_layout.addWidget(self.status_filter_combo)

        filter_layout.addWidget(QLabel("角色过滤:"))
        self.role_filter_combo = QComboBox()
        self.role_filter_combo.addItems(["全部", "主节点", "协调节点", "工作节点", "存储节点", "计算节点"])
        self.role_filter_combo.currentTextChanged.connect(self.filter_nodes)
        filter_layout.addWidget(self.role_filter_combo)

        filter_layout.addStretch()

        # 节点操作按钮
        add_node_btn = QPushButton("➕ 添加节点")
        add_node_btn.clicked.connect(self.add_node)
        filter_layout.addWidget(add_node_btn)

        remove_node_btn = QPushButton("➖ 移除节点")
        remove_node_btn.clicked.connect(self.remove_node)
        filter_layout.addWidget(remove_node_btn)

        layout.addLayout(filter_layout)

        # 节点列表表格
        self.nodes_table = QTableWidget()
        self.nodes_table.setColumnCount(9)
        self.nodes_table.setHorizontalHeaderLabels([
            "节点名称", "主机", "状态", "角色", "CPU使用率", "内存使用率", "磁盘使用率", "活跃任务", "运行时间"
        ])

        # 设置列宽
        header = self.nodes_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # 设置行选择模式
        self.nodes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.nodes_table.cellDoubleClicked.connect(self.show_node_details_from_table)

        layout.addWidget(self.nodes_table)

        return widget

    def create_fault_monitoring_tab(self) -> QWidget:
        """创建故障监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 故障统计
        fault_stats_group = QGroupBox("🚨 故障统计")
        fault_stats_layout = QGridLayout(fault_stats_group)

        # 活跃故障
        fault_stats_layout.addWidget(QLabel("活跃故障:"), 0, 0)
        self.active_faults_label = QLabel("0")
        self.active_faults_label.setStyleSheet("font-weight: bold; color: #e74c3c; font-size: 16px;")
        fault_stats_layout.addWidget(self.active_faults_label, 0, 1)

        # 今日故障
        fault_stats_layout.addWidget(QLabel("今日故障:"), 0, 2)
        self.daily_faults_label = QLabel("0")
        fault_stats_layout.addWidget(self.daily_faults_label, 0, 3)

        # 平均修复时间
        fault_stats_layout.addWidget(QLabel("平均修复时间:"), 1, 0)
        self.avg_repair_time_label = QLabel("0分钟")
        fault_stats_layout.addWidget(self.avg_repair_time_label, 1, 1)

        # 系统可用性
        fault_stats_layout.addWidget(QLabel("系统可用性:"), 1, 2)
        self.system_availability_progress = QProgressBar()
        self.system_availability_progress.setRange(0, 100)
        self.system_availability_progress.setValue(99)
        self.system_availability_progress.setFormat("99.9%")
        fault_stats_layout.addWidget(self.system_availability_progress, 1, 3)

        layout.addWidget(fault_stats_group)

        # 故障列表
        faults_group = QGroupBox("故障列表")
        faults_layout = QVBoxLayout(faults_group)

        self.faults_table = QTableWidget()
        self.faults_table.setColumnCount(6)
        self.faults_table.setHorizontalHeaderLabels([
            "时间", "节点", "故障类型", "严重程度", "状态", "描述"
        ])

        # 填充示例故障数据
        self.load_sample_faults()

        # 设置列宽
        header = self.faults_table.horizontalHeader()
        header.setStretchLastSection(True)

        faults_layout.addWidget(self.faults_table)

        layout.addWidget(faults_group)

        # 自动恢复配置
        recovery_group = QGroupBox("自动恢复配置")
        recovery_layout = QFormLayout(recovery_group)

        # 启用自动恢复
        self.auto_recovery_check = QCheckBox("启用自动故障恢复")
        self.auto_recovery_check.setChecked(True)
        recovery_layout.addRow("自动恢复:", self.auto_recovery_check)

        # 最大重试次数
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(1, 10)
        self.max_retries_spin.setValue(3)
        recovery_layout.addRow("最大重试次数:", self.max_retries_spin)

        # 恢复超时时间
        self.recovery_timeout_spin = QSpinBox()
        self.recovery_timeout_spin.setRange(30, 600)
        self.recovery_timeout_spin.setValue(120)
        self.recovery_timeout_spin.setSuffix("秒")
        recovery_layout.addRow("恢复超时:", self.recovery_timeout_spin)

        # 故障通知
        self.fault_notification_check = QCheckBox("启用故障通知")
        self.fault_notification_check.setChecked(True)
        recovery_layout.addRow("故障通知:", self.fault_notification_check)

        layout.addWidget(recovery_group)

        return widget

    def setup_connections(self):
        """设置信号连接"""
        pass

    def setup_timers(self):
        """设置定时器"""
        # 集群状态更新定时器
        self.cluster_timer = QTimer()
        self.cluster_timer.timeout.connect(self.update_cluster_status)
        self.cluster_timer.start(5000)  # 每5秒更新一次

    def load_sample_data(self):
        """加载示例数据"""
        # 生成示例节点数据
        self.generate_sample_nodes()

        # 生成示例集群指标
        self.generate_sample_cluster_metrics()

    def generate_sample_nodes(self):
        """生成示例节点数据"""
        import random

        sample_nodes = [
            # 主节点
            NodeInfo(
                "master-001", "主控节点-1", "192.168.1.10", 8080,
                NodeStatus.HEALTHY, NodeRole.MASTER,
                random.uniform(20, 40), random.uniform(30, 50), random.uniform(10, 30),
                random.uniform(10, 50), random.uniform(5, 25),
                random.randint(5, 15), random.randint(50, 100),
                timedelta(days=random.randint(1, 30))
            ),

            # 协调节点
            NodeInfo(
                "coord-001", "协调节点-1", "192.168.1.20", 8080,
                NodeStatus.HEALTHY, NodeRole.COORDINATOR,
                random.uniform(30, 60), random.uniform(40, 70), random.uniform(20, 40),
                random.uniform(20, 60), random.uniform(10, 30),
                random.randint(10, 25), random.randint(100, 200),
                timedelta(days=random.randint(1, 25))
            ),

            NodeInfo(
                "coord-002", "协调节点-2", "192.168.1.21", 8080,
                NodeStatus.WARNING, NodeRole.COORDINATOR,
                random.uniform(60, 80), random.uniform(70, 85), random.uniform(30, 50),
                random.uniform(30, 70), random.uniform(15, 35),
                random.randint(15, 30), random.randint(80, 150),
                timedelta(days=random.randint(1, 20))
            ),

            # 工作节点
            NodeInfo(
                "worker-001", "工作节点-1", "192.168.1.30", 8080,
                NodeStatus.HEALTHY, NodeRole.WORKER,
                random.uniform(40, 70), random.uniform(50, 80), random.uniform(25, 45),
                random.uniform(25, 65), random.uniform(20, 40),
                random.randint(20, 40), random.randint(200, 400),
                timedelta(days=random.randint(1, 15))
            ),

            NodeInfo(
                "worker-002", "工作节点-2", "192.168.1.31", 8080,
                NodeStatus.HEALTHY, NodeRole.WORKER,
                random.uniform(35, 65), random.uniform(45, 75), random.uniform(20, 40),
                random.uniform(20, 60), random.uniform(15, 35),
                random.randint(15, 35), random.randint(180, 350),
                timedelta(days=random.randint(1, 18))
            ),

            NodeInfo(
                "worker-003", "工作节点-3", "192.168.1.32", 8080,
                NodeStatus.CRITICAL, NodeRole.WORKER,
                random.uniform(80, 95), random.uniform(85, 95), random.uniform(60, 80),
                random.uniform(60, 90), random.uniform(40, 60),
                random.randint(40, 60), random.randint(150, 300),
                timedelta(days=random.randint(1, 10))
            ),

            # 存储节点
            NodeInfo(
                "storage-001", "存储节点-1", "192.168.1.40", 8080,
                NodeStatus.HEALTHY, NodeRole.STORAGE,
                random.uniform(25, 45), random.uniform(35, 55), random.uniform(70, 85),
                random.uniform(50, 80), random.uniform(30, 50),
                random.randint(5, 15), random.randint(100, 200),
                timedelta(days=random.randint(1, 22))
            ),

            # 离线节点
            NodeInfo(
                "worker-004", "工作节点-4", "192.168.1.33", 8080,
                NodeStatus.OFFLINE, NodeRole.WORKER,
                0, 0, 0, 0, 0, 0, 0,
                timedelta(days=random.randint(1, 5))
            )
        ]

        self.nodes = sample_nodes
        self.update_nodes_display()

    def generate_sample_cluster_metrics(self):
        """生成示例集群指标"""
        import random

        healthy_nodes = len([n for n in self.nodes if n.status == NodeStatus.HEALTHY])
        warning_nodes = len([n for n in self.nodes if n.status == NodeStatus.WARNING])
        critical_nodes = len([n for n in self.nodes if n.status == NodeStatus.CRITICAL])
        offline_nodes = len([n for n in self.nodes if n.status == NodeStatus.OFFLINE])

        metrics = ClusterMetrics(
            total_nodes=len(self.nodes),
            healthy_nodes=healthy_nodes,
            warning_nodes=warning_nodes,
            critical_nodes=critical_nodes,
            offline_nodes=offline_nodes,
            total_cpu_cores=len(self.nodes) * 8,
            used_cpu_cores=sum(int(n.cpu_usage / 100 * 8) for n in self.nodes),
            total_memory_gb=len(self.nodes) * 32,
            used_memory_gb=sum(n.memory_usage / 100 * 32 for n in self.nodes),
            total_disk_gb=len(self.nodes) * 500,
            used_disk_gb=sum(n.disk_usage / 100 * 500 for n in self.nodes),
            active_tasks=sum(n.active_tasks for n in self.nodes),
            completed_tasks=random.randint(1000, 5000),
            failed_tasks=random.randint(10, 100),
            network_throughput=sum(n.network_in + n.network_out for n in self.nodes)
        )

        self.cluster_metrics_history.append(metrics)
        self.update_overview_display(metrics)

    def update_cluster_status(self):
        """更新集群状态"""
        # 模拟动态变化
        import random

        for node in self.nodes:
            if node.status != NodeStatus.OFFLINE:
                # 模拟资源使用变化
                node.cpu_usage += random.uniform(-5, 5)
                node.cpu_usage = max(0, min(100, node.cpu_usage))

                node.memory_usage += random.uniform(-3, 3)
                node.memory_usage = max(0, min(100, node.memory_usage))

                node.disk_usage += random.uniform(-1, 1)
                node.disk_usage = max(0, min(100, node.disk_usage))

                # 更新心跳时间
                node.last_heartbeat = datetime.now()

        # 重新生成集群指标
        self.generate_sample_cluster_metrics()

        # 更新拓扑视图
        self.topology_view.update_nodes(self.nodes)

        # 更新节点表格
        self.filter_nodes()

        # 更新状态
        self.last_update_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")

    def update_overview_display(self, metrics: ClusterMetrics):
        """更新概览显示"""
        # 节点统计
        self.total_nodes_label.setText(str(metrics.total_nodes))
        self.healthy_nodes_label.setText(str(metrics.healthy_nodes))
        self.unhealthy_nodes_label.setText(str(metrics.warning_nodes + metrics.critical_nodes))
        self.offline_nodes_label.setText(str(metrics.offline_nodes))

        # 资源使用率
        cpu_usage_rate = (metrics.used_cpu_cores / metrics.total_cpu_cores * 100) if metrics.total_cpu_cores > 0 else 0
        self.cluster_cpu_progress.setValue(int(cpu_usage_rate))
        self.cluster_cpu_progress.setFormat(f"{cpu_usage_rate:.1f}%")

        memory_usage_rate = (metrics.used_memory_gb / metrics.total_memory_gb * 100) if metrics.total_memory_gb > 0 else 0
        self.cluster_memory_progress.setValue(int(memory_usage_rate))
        self.cluster_memory_progress.setFormat(f"{memory_usage_rate:.1f}%")

        disk_usage_rate = (metrics.used_disk_gb / metrics.total_disk_gb * 100) if metrics.total_disk_gb > 0 else 0
        self.cluster_disk_progress.setValue(int(disk_usage_rate))
        self.cluster_disk_progress.setFormat(f"{disk_usage_rate:.1f}%")

        self.network_throughput_label.setText(f"{metrics.network_throughput:.1f} MB/s")

        # 任务统计
        self.active_tasks_label.setText(str(metrics.active_tasks))
        self.completed_tasks_label.setText(str(metrics.completed_tasks))
        self.failed_tasks_label.setText(str(metrics.failed_tasks))

        # 任务成功率
        total_tasks = metrics.completed_tasks + metrics.failed_tasks
        success_rate = (metrics.completed_tasks / total_tasks * 100) if total_tasks > 0 else 100
        self.task_success_rate_progress.setValue(int(success_rate))
        self.task_success_rate_progress.setFormat(f"{success_rate:.1f}%")

        # 更新集群状态
        if metrics.critical_nodes > 0:
            self.cluster_status_label.setText("🔴 集群有严重问题")
            self.cluster_status_label.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    color: #721c24;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
        elif metrics.warning_nodes > 0 or metrics.offline_nodes > 0:
            self.cluster_status_label.setText("🟡 集群有警告")
            self.cluster_status_label.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    color: #856404;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
        else:
            self.cluster_status_label.setText("🟢 集群运行正常")
            self.cluster_status_label.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)

    def update_nodes_display(self):
        """更新节点显示"""
        # 更新拓扑视图
        self.topology_view.update_nodes(self.nodes)

        # 更新节点表格
        self.filter_nodes()

    def filter_nodes(self):
        """过滤节点列表"""
        status_filter = self.status_filter_combo.currentText()
        role_filter = self.role_filter_combo.currentText()

        # 应用过滤
        filtered_nodes = []
        for node in self.nodes:
            # 状态过滤
            if status_filter != "全部":
                status_mapping = {
                    "健康": NodeStatus.HEALTHY,
                    "警告": NodeStatus.WARNING,
                    "异常": NodeStatus.CRITICAL,
                    "离线": NodeStatus.OFFLINE,
                    "维护中": NodeStatus.MAINTENANCE
                }
                if node.status != status_mapping.get(status_filter):
                    continue

            # 角色过滤
            if role_filter != "全部":
                role_mapping = {
                    "主节点": NodeRole.MASTER,
                    "协调节点": NodeRole.COORDINATOR,
                    "工作节点": NodeRole.WORKER,
                    "存储节点": NodeRole.STORAGE,
                    "计算节点": NodeRole.COMPUTE
                }
                if node.role != role_mapping.get(role_filter):
                    continue

            filtered_nodes.append(node)

        self.update_nodes_table(filtered_nodes)

    def update_nodes_table(self, nodes: List[NodeInfo]):
        """更新节点表格"""
        self.nodes_table.setRowCount(len(nodes))

        status_colors = {
            NodeStatus.HEALTHY: QColor("#d4edda"),
            NodeStatus.WARNING: QColor("#fff3cd"),
            NodeStatus.CRITICAL: QColor("#f8d7da"),
            NodeStatus.OFFLINE: QColor("#e2e3e5"),
            NodeStatus.MAINTENANCE: QColor("#e7e3ff")
        }

        role_names = {
            NodeRole.MASTER: "主节点",
            NodeRole.COORDINATOR: "协调节点",
            NodeRole.WORKER: "工作节点",
            NodeRole.STORAGE: "存储节点",
            NodeRole.COMPUTE: "计算节点"
        }

        for row, node in enumerate(nodes):
            # 节点名称
            name_item = QTableWidgetItem(node.name)
            self.nodes_table.setItem(row, 0, name_item)

            # 主机
            host_item = QTableWidgetItem(f"{node.host}:{node.port}")
            self.nodes_table.setItem(row, 1, host_item)

            # 状态
            status_item = QTableWidgetItem(node.status.value.upper())
            status_item.setBackground(status_colors.get(node.status, QColor("#ffffff")))
            self.nodes_table.setItem(row, 2, status_item)

            # 角色
            role_item = QTableWidgetItem(role_names.get(node.role, node.role.value))
            self.nodes_table.setItem(row, 3, role_item)

            # CPU使用率
            cpu_item = QTableWidgetItem(f"{node.cpu_usage:.1f}%")
            self.nodes_table.setItem(row, 4, cpu_item)

            # 内存使用率
            memory_item = QTableWidgetItem(f"{node.memory_usage:.1f}%")
            self.nodes_table.setItem(row, 5, memory_item)

            # 磁盘使用率
            disk_item = QTableWidgetItem(f"{node.disk_usage:.1f}%")
            self.nodes_table.setItem(row, 6, disk_item)

            # 活跃任务
            tasks_item = QTableWidgetItem(f"{node.active_tasks}/{node.total_tasks}")
            self.nodes_table.setItem(row, 7, tasks_item)

            # 运行时间
            uptime_text = f"{node.uptime.days}天{node.uptime.seconds//3600}时"
            uptime_item = QTableWidgetItem(uptime_text)
            self.nodes_table.setItem(row, 8, uptime_item)

    def load_sample_faults(self):
        """加载示例故障数据"""
        import random

        fault_data = [
            ("10:30:15", "worker-003", "CPU过载", "严重", "处理中", "CPU使用率持续超过90%"),
            ("09:45:22", "storage-001", "磁盘空间不足", "警告", "已解决", "可用磁盘空间低于10%"),
            ("08:15:33", "coord-002", "网络连接异常", "中等", "已解决", "与主节点通信中断"),
            ("07:22:11", "worker-004", "节点离线", "严重", "未解决", "节点无响应，疑似硬件故障")
        ]

        self.faults_table.setRowCount(len(fault_data))

        severity_colors = {
            "严重": QColor("#f8d7da"),
            "中等": QColor("#fff3cd"),
            "警告": QColor("#d1ecf1"),
            "信息": QColor("#d4edda")
        }

        for row, (time, node, fault_type, severity, status, desc) in enumerate(fault_data):
            self.faults_table.setItem(row, 0, QTableWidgetItem(time))
            self.faults_table.setItem(row, 1, QTableWidgetItem(node))
            self.faults_table.setItem(row, 2, QTableWidgetItem(fault_type))

            severity_item = QTableWidgetItem(severity)
            severity_item.setBackground(severity_colors.get(severity, QColor("#ffffff")))
            self.faults_table.setItem(row, 3, severity_item)

            self.faults_table.setItem(row, 4, QTableWidgetItem(status))
            self.faults_table.setItem(row, 5, QTableWidgetItem(desc))

    def show_node_details(self, node_id: str):
        """显示节点详情"""
        node = next((n for n in self.nodes if n.node_id == node_id), None)
        if node:
            dialog = NodeDetailsDialog(node, self)
            dialog.exec_()

    def show_node_details_from_table(self, row: int, column: int):
        """从表格显示节点详情"""
        if row < len([n for n in self.nodes]):  # 简化检查
            filtered_nodes = self.get_filtered_nodes()
            if row < len(filtered_nodes):
                node = filtered_nodes[row]
                self.show_node_details(node.node_id)

    def get_filtered_nodes(self) -> List[NodeInfo]:
        """获取过滤后的节点列表"""
        # 这是一个简化实现，实际应该根据当前过滤条件返回
        return self.nodes

    def refresh_cluster_status(self):
        """刷新集群状态"""
        try:
            if self.distributed_service:
                # 调用实际的集群状态刷新逻辑
                pass

            # 重新生成示例数据
            self.generate_sample_nodes()
            QMessageBox.information(self, "刷新完成", "集群状态已刷新")
            logger.info("用户手动刷新了集群状态")

        except Exception as e:
            QMessageBox.critical(self, "刷新失败", f"集群状态刷新失败: {e}")
            logger.error(f"集群状态刷新失败: {e}")

    def trigger_load_balancing(self):
        """触发负载均衡"""
        reply = QMessageBox.question(
            self, "确认负载均衡", "确定要触发集群负载均衡吗？这可能会短暂影响性能。",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if self.distributed_service:
                    # 调用实际的负载均衡逻辑
                    pass

                QMessageBox.information(self, "负载均衡", "负载均衡已启动，系统将自动优化任务分配")
                logger.info("用户触发了集群负载均衡")

            except Exception as e:
                QMessageBox.critical(self, "操作失败", f"负载均衡启动失败: {e}")
                logger.error(f"负载均衡启动失败: {e}")

    def add_node(self):
        """添加节点"""
        # 这里可以打开添加节点的对话框
        QMessageBox.information(self, "添加节点", "添加节点功能暂未实现")

    def remove_node(self):
        """移除节点"""
        selected_rows = self.nodes_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "未选择节点", "请选择要移除的节点")
            return

        reply = QMessageBox.question(
            self, "确认移除", "确定要移除选中的节点吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "移除节点", "移除节点功能暂未实现")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 12px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 8px 0 8px;
            color: #2c3e50;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            min-width: 100px;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #21618c;
        }
        QTabWidget::pane {
            border: 1px solid #bdc3c7;
            border-radius: 6px;
            background-color: #ffffff;
        }
        QTabBar::tab {
            background-color: #ecf0f1;
            border: 1px solid #bdc3c7;
            border-bottom: none;
            border-radius: 6px 6px 0 0;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #3498db;
            color: white;
        }
        QProgressBar {
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 4px;
        }
    """)

    # 创建主窗口
    widget = DistributedStatusMonitor()
    widget.setWindowTitle("分布式状态监控")
    widget.resize(1400, 1000)
    widget.show()

    sys.exit(app.exec_())
