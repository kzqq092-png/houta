"""
API数据模型定义

使用Pydantic进行数据验证和序列化
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型"""
    DATA_IMPORT = "data_import"
    ANALYSIS = "analysis"
    BACKTEST = "backtest"
    OPTIMIZATION = "optimization"
    CUSTOM = "custom"


class TaskRequest(BaseModel):
    """任务请求"""
    task_id: str = Field(..., description="任务ID")
    task_type: TaskType = Field(..., description="任务类型")
    task_data: Dict[str, Any] = Field(default_factory=dict, description="任务数据")
    priority: int = Field(default=5, ge=1, le=10, description="任务优先级（1-10）")
    timeout: int = Field(default=300, ge=10, description="任务超时时间（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123456",
                "task_type": "data_import",
                "task_data": {
                    "symbols": ["000001.SZ", "000002.SZ"],
                    "data_source": "tongdaxin"
                },
                "priority": 5,
                "timeout": 300
            }
        }


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: TaskStatus
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123456",
                "status": "running",
                "message": "任务正在执行中",
                "started_at": "2025-10-23T23:00:00",
                "completed_at": None
            }
        }


class TaskResult(BaseModel):
    """任务结果"""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: float = 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123456",
                "status": "completed",
                "result": {"records_imported": 500, "symbols_count": 2},
                "error": None,
                "started_at": "2025-10-23T23:00:00",
                "completed_at": "2025-10-23T23:05:00",
                "execution_time": 300.5
            }
        }


class NodeHealth(BaseModel):
    """节点健康状态"""
    node_id: str
    node_name: str
    status: str = "healthy"  # healthy, busy, overloaded, error
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    uptime_seconds: float = 0.0
    last_heartbeat: datetime = Field(default_factory=datetime.now)
    capabilities: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "node_001",
                "node_name": "Worker Node 1",
                "status": "healthy",
                "cpu_percent": 45.2,
                "memory_percent": 60.5,
                "active_tasks": 2,
                "completed_tasks": 150,
                "failed_tasks": 3,
                "uptime_seconds": 86400.0,
                "last_heartbeat": "2025-10-23T23:20:00"
            }
        }


class NodeRegistration(BaseModel):
    """节点注册信息"""
    node_id: str
    node_name: str
    host: str
    port: int
    capabilities: List[str] = Field(default_factory=list)
    max_workers: int = 4

    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "node_001",
                "node_name": "Worker Node 1",
                "host": "192.168.1.100",
                "port": 8900,
                "capabilities": ["data_import", "analysis", "backtest"],
                "max_workers": 4
            }
        }


class APIResponse(BaseModel):
    """统一API响应"""
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "操作成功",
                "data": {"task_id": "task_123456"},
                "error": None
            }
        }
