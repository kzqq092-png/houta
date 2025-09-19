#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务依赖关系可视化组件

提供任务依赖关系的图形化展示和编辑功能，包括：
- 依赖关系图形化展示
- 交互式依赖编辑
- 依赖冲突检测和高亮
- 依赖路径分析

作者: FactorWeave-Quant团队
版本: 1.0
"""

import sys
import math
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsProxyWidget, QPushButton, QLabel, QComboBox, QSpinBox,
    QGroupBox, QFormLayout, QListWidget, QListWidgetItem, QTextEdit,
    QSplitter, QFrame, QScrollArea, QToolBar, QAction, QMenu,
    QMessageBox, QDialog, QDialogButtonBox, QCheckBox, QSlider,
    QApplication, QGraphicsRectItem, QGraphicsPathItem
)
from PyQt5.QtCore import (
    Qt, QPointF, QRectF, QSizeF, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup
)
from PyQt5.QtGui import (
    QPen, QBrush, QColor, QPainter, QFont, QFontMetrics, QPainterPath,
    QLinearGradient, QRadialGradient, QPalette, QPixmap, QIcon
)

# 导入核心服务
try:
    from core.services.dependency_resolver import DependencyResolver
    from core.ui_integration.ui_business_logic_adapter import get_ui_adapter
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    CORE_AVAILABLE = False
    logger.warning(f"核心服务不可用: {e}")

logger = logger.bind(module=__name__) if hasattr(logger, 'bind') else logging.getLogger(__name__)


class NodeType(Enum):
    """节点类型"""
    TASK = "task"
    GROUP = "group"
    MILESTONE = "milestone"


class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class EdgeType(Enum):
    """边类型"""
    DEPENDENCY = "dependency"
    CONFLICT = "conflict"
    SUGGESTION = "suggestion"


@dataclass
class TaskNode:
    """任务节点数据"""
    id: str
    name: str
    node_type: NodeType = NodeType.TASK
    status: NodeStatus = NodeStatus.PENDING
    position: QPointF = field(default_factory=lambda: QPointF(0, 0))
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    priority: int = 0
    estimated_duration: int = 0  # 分钟
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyEdge:
    """依赖边数据"""
    from_id: str
    to_id: str
    edge_type: EdgeType = EdgeType.DEPENDENCY
    weight: float = 1.0
    is_critical: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskNodeGraphicsItem(QGraphicsEllipseItem):
    """任务节点图形项"""

    def __init__(self, node: TaskNode, parent=None):
        super().__init__(parent)
        self.node = node
        self.text_item = None
        self.setup_appearance()
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def setup_appearance(self):
        """设置外观"""
        # 节点大小
        size = 60 if self.node.node_type == NodeType.TASK else 80
        self.setRect(-size/2, -size/2, size, size)

        # 根据状态设置颜色
        color_map = {
            NodeStatus.PENDING: QColor(200, 200, 200),
            NodeStatus.RUNNING: QColor(52, 152, 219),
            NodeStatus.COMPLETED: QColor(46, 204, 113),
            NodeStatus.FAILED: QColor(231, 76, 60),
            NodeStatus.BLOCKED: QColor(230, 126, 34)
        }

        base_color = color_map.get(self.node.status, QColor(200, 200, 200))

        # 创建渐变效果
        gradient = QRadialGradient(0, 0, size/2)
        gradient.setColorAt(0, base_color.lighter(120))
        gradient.setColorAt(1, base_color.darker(110))

        self.setBrush(QBrush(gradient))

        # 边框
        pen_color = base_color.darker(150)
        pen = QPen(pen_color, 2)
        if self.isSelected():
            pen.setWidth(3)
            pen.setColor(QColor(255, 165, 0))  # 橙色选中边框

        self.setPen(pen)

        # 添加文本
        if self.text_item:
            self.scene().removeItem(self.text_item)

        self.text_item = QGraphicsTextItem(self.node.name[:8] + "..." if len(self.node.name) > 8 else self.node.name)
        self.text_item.setParentItem(self)

        # 居中文本
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos(-text_rect.width()/2, -text_rect.height()/2)

        # 文本样式
        font = QFont("Arial", 8, QFont.Bold)
        self.text_item.setFont(font)
        self.text_item.setDefaultTextColor(Qt.white if base_color.lightness() < 128 else Qt.black)

    def itemChange(self, change, value):
        """处理项目变更"""
        if change == QGraphicsItem.ItemPositionHasChanged:
            # 更新节点位置
            self.node.position = value
            # 通知场景更新连接线
            if self.scene():
                self.scene().update_edges_for_node(self.node.id)

        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.RightButton:
            # 显示上下文菜单
            self.show_context_menu(event.screenPos())
        else:
            super().mousePressEvent(event)

    def show_context_menu(self, pos):
        """显示上下文菜单"""
        menu = QMenu()

        # 编辑动作
        edit_action = menu.addAction("📝 编辑任务")
        edit_action.triggered.connect(self.edit_task)

        # 删除动作
        delete_action = menu.addAction("🗑️ 删除任务")
        delete_action.triggered.connect(self.delete_task)

        menu.addSeparator()

        # 添加依赖动作
        add_dep_action = menu.addAction("🔗 添加依赖")
        add_dep_action.triggered.connect(self.add_dependency)

        # 查看详情动作
        details_action = menu.addAction("ℹ️ 查看详情")
        details_action.triggered.connect(self.show_details)

        menu.exec_(pos)

    def edit_task(self):
        """编辑任务"""
        # 这里可以打开任务编辑对话框
        pass

    def delete_task(self):
        """删除任务"""
        if self.scene():
            self.scene().remove_node(self.node.id)

    def add_dependency(self):
        """添加依赖"""
        if self.scene():
            self.scene().start_dependency_creation(self.node.id)

    def show_details(self):
        """显示详情"""
        # 这里可以显示任务详情对话框
        pass

    def update_status(self, status: NodeStatus):
        """更新状态"""
        self.node.status = status
        self.setup_appearance()


class DependencyEdgeGraphicsItem(QGraphicsPathItem):
    """依赖边图形项"""

    def __init__(self, edge: DependencyEdge, from_node: TaskNodeGraphicsItem, to_node: TaskNodeGraphicsItem, parent=None):
        super().__init__(parent)
        self.edge = edge
        self.from_node = from_node
        self.to_node = to_node
        self.arrow_head = None
        self.setup_appearance()
        self.update_path()

    def setup_appearance(self):
        """设置外观"""
        # 根据边类型设置颜色
        color_map = {
            EdgeType.DEPENDENCY: QColor(100, 100, 100),
            EdgeType.CONFLICT: QColor(231, 76, 60),
            EdgeType.SUGGESTION: QColor(52, 152, 219)
        }

        color = color_map.get(self.edge.edge_type, QColor(100, 100, 100))

        # 设置画笔
        pen = QPen(color, 2 if self.edge.is_critical else 1)
        if self.edge.edge_type == EdgeType.CONFLICT:
            pen.setStyle(Qt.DashLine)
        elif self.edge.edge_type == EdgeType.SUGGESTION:
            pen.setStyle(Qt.DotLine)

        self.setPen(pen)
        self.setBrush(QBrush(color))

    def update_path(self):
        """更新路径"""
        if not self.from_node or not self.to_node:
            return

        # 获取节点中心点
        from_pos = self.from_node.pos()
        to_pos = self.to_node.pos()

        # 计算连接点（节点边缘）
        from_rect = self.from_node.boundingRect()
        to_rect = self.to_node.boundingRect()

        # 计算方向向量
        dx = to_pos.x() - from_pos.x()
        dy = to_pos.y() - from_pos.y()
        length = math.sqrt(dx*dx + dy*dy)

        if length == 0:
            return

        # 单位向量
        unit_x = dx / length
        unit_y = dy / length

        # 计算起点和终点（在节点边缘）
        from_radius = from_rect.width() / 2
        to_radius = to_rect.width() / 2

        start_point = QPointF(
            from_pos.x() + unit_x * from_radius,
            from_pos.y() + unit_y * from_radius
        )

        end_point = QPointF(
            to_pos.x() - unit_x * to_radius,
            to_pos.y() - unit_y * to_radius
        )

        # 创建路径
        path = QPainterPath()

        # 如果是直线连接
        if abs(dx) > abs(dy):
            # 水平优先的贝塞尔曲线
            control1 = QPointF(start_point.x() + dx * 0.3, start_point.y())
            control2 = QPointF(end_point.x() - dx * 0.3, end_point.y())
        else:
            # 垂直优先的贝塞尔曲线
            control1 = QPointF(start_point.x(), start_point.y() + dy * 0.3)
            control2 = QPointF(end_point.x(), end_point.y() - dy * 0.3)

        path.moveTo(start_point)
        path.cubicTo(control1, control2, end_point)

        # 添加箭头
        arrow_size = 10
        arrow_angle = math.atan2(dy, dx)

        arrow_p1 = QPointF(
            end_point.x() - arrow_size * math.cos(arrow_angle - math.pi/6),
            end_point.y() - arrow_size * math.sin(arrow_angle - math.pi/6)
        )

        arrow_p2 = QPointF(
            end_point.x() - arrow_size * math.cos(arrow_angle + math.pi/6),
            end_point.y() - arrow_size * math.sin(arrow_angle + math.pi/6)
        )

        path.moveTo(end_point)
        path.lineTo(arrow_p1)
        path.moveTo(end_point)
        path.lineTo(arrow_p2)

        self.setPath(path)


class DependencyGraphicsScene(QGraphicsScene):
    """依赖图形场景"""

    node_selected = pyqtSignal(str)  # 节点选中信号
    dependency_created = pyqtSignal(str, str)  # 依赖创建信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes: Dict[str, TaskNodeGraphicsItem] = {}
        self.edges: Dict[Tuple[str, str], DependencyEdgeGraphicsItem] = {}
        self.dependency_resolver = None
        self.creating_dependency = False
        self.dependency_start_node = None

        # 初始化依赖解析器
        if CORE_AVAILABLE:
            try:
                self.dependency_resolver = DependencyResolver()
            except Exception as e:
                logger.warning(f"依赖解析器初始化失败: {e}")

    def add_node(self, node: TaskNode) -> TaskNodeGraphicsItem:
        """添加节点"""
        if node.id in self.nodes:
            return self.nodes[node.id]

        # 创建图形项
        graphics_item = TaskNodeGraphicsItem(node)
        graphics_item.setPos(node.position)

        # 添加到场景
        self.addItem(graphics_item)
        self.nodes[node.id] = graphics_item

        return graphics_item

    def remove_node(self, node_id: str):
        """移除节点"""
        if node_id not in self.nodes:
            return

        # 移除相关的边
        edges_to_remove = []
        for (from_id, to_id), edge_item in self.edges.items():
            if from_id == node_id or to_id == node_id:
                edges_to_remove.append((from_id, to_id))

        for edge_key in edges_to_remove:
            self.remove_edge(edge_key[0], edge_key[1])

        # 移除节点
        node_item = self.nodes[node_id]
        self.removeItem(node_item)
        del self.nodes[node_id]

    def add_edge(self, edge: DependencyEdge) -> DependencyEdgeGraphicsItem:
        """添加边"""
        edge_key = (edge.from_id, edge.to_id)
        if edge_key in self.edges:
            return self.edges[edge_key]

        # 获取节点
        from_node = self.nodes.get(edge.from_id)
        to_node = self.nodes.get(edge.to_id)

        if not from_node or not to_node:
            logger.warning(f"无法创建边：节点不存在 {edge.from_id} -> {edge.to_id}")
            return None

        # 创建图形项
        graphics_item = DependencyEdgeGraphicsItem(edge, from_node, to_node)

        # 添加到场景
        self.addItem(graphics_item)
        self.edges[edge_key] = graphics_item

        # 更新节点依赖关系
        from_node.node.dependents.add(edge.to_id)
        to_node.node.dependencies.add(edge.from_id)

        return graphics_item

    def remove_edge(self, from_id: str, to_id: str):
        """移除边"""
        edge_key = (from_id, to_id)
        if edge_key not in self.edges:
            return

        # 移除图形项
        edge_item = self.edges[edge_key]
        self.removeItem(edge_item)
        del self.edges[edge_key]

        # 更新节点依赖关系
        if from_id in self.nodes:
            self.nodes[from_id].node.dependents.discard(to_id)
        if to_id in self.nodes:
            self.nodes[to_id].node.dependencies.discard(from_id)

    def update_edges_for_node(self, node_id: str):
        """更新节点相关的边"""
        for (from_id, to_id), edge_item in self.edges.items():
            if from_id == node_id or to_id == node_id:
                edge_item.update_path()

    def start_dependency_creation(self, from_node_id: str):
        """开始创建依赖"""
        self.creating_dependency = True
        self.dependency_start_node = from_node_id
        # 可以改变鼠标样式等

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if self.creating_dependency and event.button() == Qt.LeftButton:
            # 检查点击的项目
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if isinstance(item, TaskNodeGraphicsItem):
                to_node_id = item.node.id
                if to_node_id != self.dependency_start_node:
                    # 创建依赖
                    self.dependency_created.emit(self.dependency_start_node, to_node_id)

                # 结束创建模式
                self.creating_dependency = False
                self.dependency_start_node = None

        super().mousePressEvent(event)

    def detect_conflicts(self) -> List[Tuple[str, str, str]]:
        """检测依赖冲突"""
        conflicts = []

        if not self.dependency_resolver:
            return conflicts

        try:
            # 构建依赖图
            dependencies = {}
            for node_id, node_item in self.nodes.items():
                dependencies[node_id] = list(node_item.node.dependencies)

            # 检测循环依赖
            cycles = self.dependency_resolver.detect_cycles(dependencies)
            for cycle in cycles:
                conflicts.append(("cycle", cycle, "循环依赖"))

            # 检测其他冲突
            # 这里可以添加更多冲突检测逻辑

        except Exception as e:
            logger.error(f"依赖冲突检测失败: {e}")

        return conflicts

    def auto_layout(self):
        """自动布局"""
        if not self.nodes:
            return

        # 使用简单的层次布局算法
        try:
            # 计算节点层级
            levels = self._calculate_levels()

            # 按层级排列节点
            level_width = 200
            level_height = 150

            for level, node_ids in levels.items():
                y = level * level_height
                node_count = len(node_ids)

                for i, node_id in enumerate(node_ids):
                    if node_id in self.nodes:
                        x = (i - node_count/2) * level_width
                        self.nodes[node_id].setPos(x, y)

            # 更新所有边
            for edge_item in self.edges.values():
                edge_item.update_path()

        except Exception as e:
            logger.error(f"自动布局失败: {e}")

    def _calculate_levels(self) -> Dict[int, List[str]]:
        """计算节点层级"""
        levels = {}
        visited = set()

        def dfs(node_id, level):
            if node_id in visited:
                return

            visited.add(node_id)

            if level not in levels:
                levels[level] = []
            levels[level].append(node_id)

            # 处理依赖节点
            if node_id in self.nodes:
                for dep_id in self.nodes[node_id].node.dependencies:
                    dfs(dep_id, level - 1)

        # 从没有依赖的节点开始
        for node_id, node_item in self.nodes.items():
            if not node_item.node.dependencies:
                dfs(node_id, 0)

        # 处理剩余节点
        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id, 0)

        return levels


class TaskDependencyVisualizer(QWidget):
    """任务依赖关系可视化组件"""

    def __init__(self, ui_adapter=None, parent=None):
        super().__init__(parent)
        self.ui_adapter = ui_adapter
        self.dependency_resolver = None

        # 初始化适配器
        if CORE_AVAILABLE:
            try:
                if self.ui_adapter is None:
                    self.ui_adapter = get_ui_adapter()
                self.dependency_resolver = DependencyResolver()
            except Exception as e:
                logger.warning(f"适配器初始化失败: {e}")

        self.setup_ui()
        self.setup_connections()
        self.load_sample_data()  # 加载示例数据

    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)

        # 右侧图形视图
        graphics_panel = self.create_graphics_panel()
        splitter.addWidget(graphics_panel)

        # 设置分割比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

    def create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QWidget()
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)

        # 工具栏
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)

        # 任务列表
        tasks_group = QGroupBox("📋 任务列表")
        tasks_layout = QVBoxLayout(tasks_group)

        self.task_list = QListWidget()
        self.task_list.setMaximumHeight(200)
        tasks_layout.addWidget(self.task_list)

        # 添加任务按钮
        add_task_btn = QPushButton("➕ 添加任务")
        add_task_btn.clicked.connect(self.add_new_task)
        tasks_layout.addWidget(add_task_btn)

        layout.addWidget(tasks_group)

        # 依赖信息
        deps_group = QGroupBox("🔗 依赖信息")
        deps_layout = QVBoxLayout(deps_group)

        self.dependency_info = QTextEdit()
        self.dependency_info.setMaximumHeight(150)
        self.dependency_info.setReadOnly(True)
        deps_layout.addWidget(self.dependency_info)

        layout.addWidget(deps_group)

        # 冲突检测
        conflicts_group = QGroupBox("⚠️ 冲突检测")
        conflicts_layout = QVBoxLayout(conflicts_group)

        detect_btn = QPushButton("🔍 检测冲突")
        detect_btn.clicked.connect(self.detect_conflicts)
        conflicts_layout.addWidget(detect_btn)

        self.conflicts_list = QListWidget()
        self.conflicts_list.setMaximumHeight(100)
        conflicts_layout.addWidget(self.conflicts_list)

        layout.addWidget(conflicts_group)

        layout.addStretch()

        return panel

    def create_toolbar(self) -> QWidget:
        """创建工具栏"""
        toolbar = QFrame()
        layout = QHBoxLayout(toolbar)

        # 自动布局按钮
        auto_layout_btn = QPushButton("📐 自动布局")
        auto_layout_btn.clicked.connect(self.auto_layout)
        layout.addWidget(auto_layout_btn)

        # 缩放控制
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(self.zoom_in)
        layout.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(self.zoom_out)
        layout.addWidget(zoom_out_btn)

        return toolbar

    def create_graphics_panel(self) -> QWidget:
        """创建图形面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 创建图形视图和场景
        self.graphics_scene = DependencyGraphicsScene()
        self.graphics_view = QGraphicsView(self.graphics_scene)

        # 设置视图属性
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setDragMode(QGraphicsView.RubberBandDrag)
        self.graphics_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        layout.addWidget(self.graphics_view)

        return panel

    def setup_connections(self):
        """设置信号连接"""
        if self.graphics_scene:
            self.graphics_scene.node_selected.connect(self.on_node_selected)
            self.graphics_scene.dependency_created.connect(self.on_dependency_created)

        if self.task_list:
            self.task_list.itemSelectionChanged.connect(self.on_task_list_selection_changed)

    def load_sample_data(self):
        """加载示例数据"""
        # 创建示例任务节点
        sample_tasks = [
            TaskNode("task1", "数据获取", NodeType.TASK, NodeStatus.COMPLETED, QPointF(-200, 0)),
            TaskNode("task2", "数据清洗", NodeType.TASK, NodeStatus.RUNNING, QPointF(0, 0)),
            TaskNode("task3", "数据分析", NodeType.TASK, NodeStatus.PENDING, QPointF(200, 0)),
            TaskNode("task4", "报告生成", NodeType.TASK, NodeStatus.PENDING, QPointF(400, 0)),
            TaskNode("milestone1", "阶段一完成", NodeType.MILESTONE, NodeStatus.PENDING, QPointF(100, -150))
        ]

        # 添加节点到场景
        for task in sample_tasks:
            self.graphics_scene.add_node(task)

            # 添加到任务列表
            item = QListWidgetItem(f"{task.name} ({task.status.value})")
            item.setData(Qt.UserRole, task.id)
            self.task_list.addItem(item)

        # 创建示例依赖关系
        sample_edges = [
            DependencyEdge("task1", "task2", EdgeType.DEPENDENCY),
            DependencyEdge("task2", "task3", EdgeType.DEPENDENCY),
            DependencyEdge("task3", "task4", EdgeType.DEPENDENCY),
            DependencyEdge("task2", "milestone1", EdgeType.DEPENDENCY)
        ]

        # 添加边到场景
        for edge in sample_edges:
            self.graphics_scene.add_edge(edge)

    def add_new_task(self):
        """添加新任务"""
        # 这里可以打开任务创建对话框
        # 暂时创建一个简单的任务
        task_id = f"task_{len(self.graphics_scene.nodes) + 1}"
        task_name = f"新任务 {len(self.graphics_scene.nodes) + 1}"

        new_task = TaskNode(
            task_id,
            task_name,
            NodeType.TASK,
            NodeStatus.PENDING,
            QPointF(0, 100)
        )

        self.graphics_scene.add_node(new_task)

        # 添加到任务列表
        item = QListWidgetItem(f"{new_task.name} ({new_task.status.value})")
        item.setData(Qt.UserRole, new_task.id)
        self.task_list.addItem(item)

    def on_node_selected(self, node_id: str):
        """处理节点选中"""
        if node_id in self.graphics_scene.nodes:
            node = self.graphics_scene.nodes[node_id].node

            # 更新依赖信息
            info_text = f"任务: {node.name}\n"
            info_text += f"状态: {node.status.value}\n"
            info_text += f"优先级: {node.priority}\n"
            info_text += f"进度: {node.progress:.1%}\n\n"

            if node.dependencies:
                info_text += "依赖任务:\n"
                for dep_id in node.dependencies:
                    if dep_id in self.graphics_scene.nodes:
                        dep_name = self.graphics_scene.nodes[dep_id].node.name
                        info_text += f"  - {dep_name}\n"

            if node.dependents:
                info_text += "\n被依赖任务:\n"
                for dep_id in node.dependents:
                    if dep_id in self.graphics_scene.nodes:
                        dep_name = self.graphics_scene.nodes[dep_id].node.name
                        info_text += f"  - {dep_name}\n"

            self.dependency_info.setText(info_text)

    def on_dependency_created(self, from_id: str, to_id: str):
        """处理依赖创建"""
        # 检查是否会造成循环依赖
        if self.would_create_cycle(from_id, to_id):
            QMessageBox.warning(self, "依赖冲突", "添加此依赖会造成循环依赖！")
            return

        # 创建依赖边
        edge = DependencyEdge(from_id, to_id, EdgeType.DEPENDENCY)
        self.graphics_scene.add_edge(edge)

        # 更新显示
        self.update_task_list()

    def on_task_list_selection_changed(self):
        """处理任务列表选择变更"""
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = current_item.data(Qt.UserRole)
            if task_id in self.graphics_scene.nodes:
                # 选中对应的图形节点
                node_item = self.graphics_scene.nodes[task_id]
                self.graphics_scene.clearSelection()
                node_item.setSelected(True)

                # 居中显示
                self.graphics_view.centerOn(node_item)

    def would_create_cycle(self, from_id: str, to_id: str) -> bool:
        """检查是否会创建循环依赖"""
        if not self.dependency_resolver:
            return False

        try:
            # 构建当前依赖图
            dependencies = {}
            for node_id, node_item in self.graphics_scene.nodes.items():
                dependencies[node_id] = list(node_item.node.dependencies)

            # 添加新依赖
            if to_id not in dependencies:
                dependencies[to_id] = []
            dependencies[to_id].append(from_id)

            # 检测循环
            cycles = self.dependency_resolver.detect_cycles(dependencies)
            return len(cycles) > 0

        except Exception as e:
            logger.error(f"循环依赖检测失败: {e}")
            return False

    def detect_conflicts(self):
        """检测冲突"""
        conflicts = self.graphics_scene.detect_conflicts()

        # 清空冲突列表
        self.conflicts_list.clear()

        # 添加冲突信息
        for conflict_type, conflict_data, description in conflicts:
            item = QListWidgetItem(f"{conflict_type}: {description}")
            item.setData(Qt.UserRole, conflict_data)
            self.conflicts_list.addItem(item)

        if not conflicts:
            item = QListWidgetItem("✅ 未发现冲突")
            self.conflicts_list.addItem(item)

    def auto_layout(self):
        """自动布局"""
        self.graphics_scene.auto_layout()

    def zoom_in(self):
        """放大"""
        self.graphics_view.scale(1.2, 1.2)

    def zoom_out(self):
        """缩小"""
        self.graphics_view.scale(0.8, 0.8)

    def update_task_list(self):
        """更新任务列表"""
        self.task_list.clear()

        for node_id, node_item in self.graphics_scene.nodes.items():
            node = node_item.node
            item = QListWidgetItem(f"{node.name} ({node.status.value})")
            item.setData(Qt.UserRole, node.id)
            self.task_list.addItem(item)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyleSheet("""
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
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 5px 10px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
    """)

    # 创建主窗口
    widget = TaskDependencyVisualizer()
    widget.setWindowTitle("任务依赖关系可视化")
    widget.resize(1200, 800)
    widget.show()

    sys.exit(app.exec_())
