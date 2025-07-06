"""
分布式服务模块

提供分布式计算、节点管理、任务分发和结果收集功能。
"""

import json
import socket
import threading
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


@dataclass
class NodeInfo:
    """节点信息"""
    node_id: str
    ip_address: str
    port: int
    status: str = "unknown"  # unknown, active, inactive, busy
    node_type: str = "worker"  # master, worker, hybrid
    cpu_count: int = 0
    memory_total: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    task_count: int = 0
    last_heartbeat: Optional[datetime] = None
    capabilities: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = ["analysis", "backtest", "optimization"]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        if self.last_heartbeat:
            data['last_heartbeat'] = self.last_heartbeat.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeInfo':
        """从字典创建"""
        if 'last_heartbeat' in data and data['last_heartbeat']:
            data['last_heartbeat'] = datetime.fromisoformat(data['last_heartbeat'])
        return cls(**data)


@dataclass
class DistributedTask:
    """分布式任务"""
    task_id: str
    task_type: str
    task_data: Dict[str, Any]
    priority: int = 5  # 1-10，数字越小优先级越高
    status: str = "pending"  # pending, assigned, running, completed, failed
    assigned_node: Optional[str] = None
    created_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        for time_field in ['created_time', 'start_time', 'end_time']:
            if data[time_field]:
                data[time_field] = data[time_field].isoformat()
        return data


class NodeDiscovery:
    """节点发现服务"""

    def __init__(self, discovery_port: int = 8888):
        """
        初始化节点发现服务

        Args:
            discovery_port: 发现服务端口
        """
        self.discovery_port = discovery_port
        self.running = False
        self.discovery_thread = None
        self.discovered_nodes: Dict[str, NodeInfo] = {}
        self.callbacks: List[Callable[[NodeInfo], None]] = []

    def add_discovery_callback(self, callback: Callable[[NodeInfo], None]):
        """添加节点发现回调"""
        self.callbacks.append(callback)

    def start_discovery(self):
        """开始节点发现"""
        if self.running:
            return

        self.running = True
        self.discovery_thread = threading.Thread(target=self._discovery_worker, daemon=True)
        self.discovery_thread.start()
        logger.info(f"节点发现服务已启动，端口: {self.discovery_port}")

    def stop_discovery(self):
        """停止节点发现"""
        self.running = False
        if self.discovery_thread:
            self.discovery_thread.join(timeout=5)
        logger.info("节点发现服务已停止")

    def _discovery_worker(self):
        """发现工作线程"""
        while self.running:
            try:
                # 广播发现消息
                self._broadcast_discovery()

                # 监听响应
                self._listen_for_responses()

                time.sleep(5)  # 每5秒发现一次

            except Exception as e:
                logger.error(f"节点发现错误: {e}")
                time.sleep(5)

    def _broadcast_discovery(self):
        """广播发现消息"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            discovery_message = {
                "type": "discovery",
                "timestamp": datetime.now().isoformat(),
                "sender_port": self.discovery_port
            }

            message = json.dumps(discovery_message).encode()
            sock.sendto(message, ('<broadcast>', self.discovery_port))
            sock.close()

        except Exception as e:
            logger.error(f"广播发现消息失败: {e}")

    def _listen_for_responses(self):
        """监听发现响应"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', self.discovery_port))
            sock.settimeout(3)  # 3秒超时

            while self.running:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = json.loads(data.decode())

                    if message.get('type') == 'node_info':
                        self._process_node_info(message, addr[0])

                except socket.timeout:
                    break
                except Exception as e:
                    logger.error(f"处理发现响应失败: {e}")

            sock.close()

        except Exception as e:
            logger.error(f"监听发现响应失败: {e}")

    def _process_node_info(self, message: Dict[str, Any], ip_address: str):
        """处理节点信息"""
        try:
            node_info = NodeInfo(
                node_id=message.get('node_id', str(uuid.uuid4())),
                ip_address=ip_address,
                port=message.get('port', 8889),
                status="active",
                node_type=message.get('node_type', 'worker'),
                cpu_count=message.get('cpu_count', 0),
                memory_total=message.get('memory_total', 0),
                cpu_usage=message.get('cpu_usage', 0.0),
                memory_usage=message.get('memory_usage', 0.0),
                task_count=message.get('task_count', 0),
                last_heartbeat=datetime.now(),
                capabilities=message.get('capabilities', ["analysis", "backtest"])
            )

            self.discovered_nodes[node_info.node_id] = node_info

            # 触发回调
            for callback in self.callbacks:
                try:
                    callback(node_info)
                except Exception as e:
                    logger.error(f"节点发现回调失败: {e}")

        except Exception as e:
            logger.error(f"处理节点信息失败: {e}")


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        """初始化任务调度器"""
        self.task_queue: List[DistributedTask] = []
        self.running_tasks: Dict[str, DistributedTask] = {}
        self.completed_tasks: List[DistributedTask] = []
        self.nodes: Dict[str, NodeInfo] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)

    def add_node(self, node: NodeInfo):
        """添加节点"""
        self.nodes[node.node_id] = node
        logger.info(f"添加节点: {node.node_id} ({node.ip_address}:{node.port})")

    def remove_node(self, node_id: str):
        """移除节点"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            logger.info(f"移除节点: {node_id}")

    def submit_task(self, task: DistributedTask) -> str:
        """提交任务"""
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority)  # 按优先级排序
        logger.info(f"提交任务: {task.task_id} (类型: {task.task_type})")
        return task.task_id

    def schedule_tasks(self):
        """调度任务"""
        available_nodes = [node for node in self.nodes.values()
                           if node.status == "active" and node.task_count < 5]

        for node in available_nodes:
            if not self.task_queue:
                break

            # 找到适合的任务
            suitable_task = None
            for task in self.task_queue:
                if task.task_type in node.capabilities:
                    suitable_task = task
                    break

            if suitable_task:
                self._assign_task_to_node(suitable_task, node)

    def _assign_task_to_node(self, task: DistributedTask, node: NodeInfo):
        """将任务分配给节点"""
        try:
            task.status = "assigned"
            task.assigned_node = node.node_id
            task.start_time = datetime.now()

            self.task_queue.remove(task)
            self.running_tasks[task.task_id] = task

            # 提交到线程池执行
            future = self.executor.submit(self._execute_task_on_node, task, node)

            logger.info(f"任务 {task.task_id} 已分配给节点 {node.node_id}")

        except Exception as e:
            logger.error(f"分配任务失败: {e}")
            task.status = "failed"
            task.error_message = str(e)

    def _execute_task_on_node(self, task: DistributedTask, node: NodeInfo):
        """在节点上执行任务"""
        try:
            # 模拟任务执行
            time.sleep(2)  # 模拟网络延迟和计算时间

            # 根据任务类型执行不同逻辑
            if task.task_type == "analysis":
                result = self._execute_analysis_task(task, node)
            elif task.task_type == "backtest":
                result = self._execute_backtest_task(task, node)
            elif task.task_type == "optimization":
                result = self._execute_optimization_task(task, node)
            else:
                raise ValueError(f"不支持的任务类型: {task.task_type}")

            # 更新任务状态
            task.status = "completed"
            task.end_time = datetime.now()
            task.result = result

            # 移动到完成列表
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            self.completed_tasks.append(task)

            logger.info(f"任务 {task.task_id} 在节点 {node.node_id} 上执行完成")

        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            task.status = "failed"
            task.error_message = str(e)
            task.end_time = datetime.now()

            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            self.completed_tasks.append(task)

    def _execute_analysis_task(self, task: DistributedTask, node: NodeInfo) -> Dict[str, Any]:
        """执行分析任务"""
        # 模拟技术分析计算
        return {
            "analysis_type": task.task_data.get("analysis_type", "technical"),
            "stock_code": task.task_data.get("stock_code", "000001"),
            "indicators": {
                "ma5": 12.34,
                "ma10": 12.56,
                "rsi": 65.2,
                "macd": 0.123
            },
            "signals": ["buy", "hold"],
            "confidence": 0.85,
            "processed_by": node.node_id
        }

    def _execute_backtest_task(self, task: DistributedTask, node: NodeInfo) -> Dict[str, Any]:
        """执行回测任务"""
        # 模拟回测计算
        return {
            "strategy": task.task_data.get("strategy", "ma_cross"),
            "stock_code": task.task_data.get("stock_code", "000001"),
            "period": task.task_data.get("period", "1y"),
            "total_return": 0.156,
            "sharpe_ratio": 1.23,
            "max_drawdown": -0.08,
            "win_rate": 0.62,
            "processed_by": node.node_id
        }

    def _execute_optimization_task(self, task: DistributedTask, node: NodeInfo) -> Dict[str, Any]:
        """执行优化任务"""
        # 模拟参数优化
        return {
            "pattern": task.task_data.get("pattern", "head_shoulders"),
            "optimization_method": task.task_data.get("method", "genetic"),
            "best_params": {
                "threshold": 0.85,
                "window": 20,
                "sensitivity": 0.75
            },
            "performance_improvement": 0.15,
            "iterations": 100,
            "processed_by": node.node_id
        }


class DistributedService:
    """分布式服务主类"""

    def __init__(self, discovery_port: int = 8888):
        """
        初始化分布式服务

        Args:
            discovery_port: 节点发现端口
        """
        self.discovery_port = discovery_port
        self.node_discovery = NodeDiscovery(discovery_port)
        self.task_scheduler = TaskScheduler()
        self.running = False

        # 连接节点发现和任务调度
        self.node_discovery.add_discovery_callback(self.task_scheduler.add_node)

    def start_service(self):
        """启动分布式服务"""
        if self.running:
            return

        self.running = True
        self.node_discovery.start_discovery()

        # 启动任务调度循环
        self.schedule_thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self.schedule_thread.start()

        logger.info("分布式服务已启动")

    def stop_service(self):
        """停止分布式服务"""
        self.running = False
        self.node_discovery.stop_discovery()

        if hasattr(self, 'schedule_thread'):
            self.schedule_thread.join(timeout=5)

        logger.info("分布式服务已停止")

    def _schedule_loop(self):
        """任务调度循环"""
        while self.running:
            try:
                self.task_scheduler.schedule_tasks()
                time.sleep(1)  # 每秒调度一次
            except Exception as e:
                logger.error(f"任务调度错误: {e}")
                time.sleep(5)

    def submit_analysis_task(self, stock_code: str, analysis_type: str = "technical") -> str:
        """提交分析任务"""
        task = DistributedTask(
            task_id=str(uuid.uuid4()),
            task_type="analysis",
            task_data={
                "stock_code": stock_code,
                "analysis_type": analysis_type
            },
            priority=5
        )
        return self.task_scheduler.submit_task(task)

    def submit_backtest_task(self, stock_code: str, strategy: str, period: str = "1y") -> str:
        """提交回测任务"""
        task = DistributedTask(
            task_id=str(uuid.uuid4()),
            task_type="backtest",
            task_data={
                "stock_code": stock_code,
                "strategy": strategy,
                "period": period
            },
            priority=3
        )
        return self.task_scheduler.submit_task(task)

    def submit_optimization_task(self, pattern: str, method: str = "genetic") -> str:
        """提交优化任务"""
        task = DistributedTask(
            task_id=str(uuid.uuid4()),
            task_type="optimization",
            task_data={
                "pattern": pattern,
                "method": method
            },
            priority=1  # 高优先级
        )
        return self.task_scheduler.submit_task(task)

    def get_task_status(self, task_id: str) -> Optional[DistributedTask]:
        """获取任务状态"""
        # 检查运行中的任务
        if task_id in self.task_scheduler.running_tasks:
            return self.task_scheduler.running_tasks[task_id]

        # 检查已完成的任务
        for task in self.task_scheduler.completed_tasks:
            if task.task_id == task_id:
                return task

        # 检查待处理的任务
        for task in self.task_scheduler.task_queue:
            if task.task_id == task_id:
                return task

        return None

    def get_nodes_info(self) -> List[NodeInfo]:
        """获取所有节点信息"""
        return list(self.task_scheduler.nodes.values())

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "running": self.running,
            "discovery_port": self.discovery_port,
            "total_nodes": len(self.task_scheduler.nodes),
            "active_nodes": len([n for n in self.task_scheduler.nodes.values() if n.status == "active"]),
            "pending_tasks": len(self.task_scheduler.task_queue),
            "running_tasks": len(self.task_scheduler.running_tasks),
            "completed_tasks": len(self.task_scheduler.completed_tasks)
        }
