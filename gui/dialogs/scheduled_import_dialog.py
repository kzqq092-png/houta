"""
定时导入任务管理对话框

提供定时导入任务的创建、查看、编辑、删除功能
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from loguru import logger
from typing import List, Dict, Any

from core.importdata.import_config_manager import ImportConfigManager


class ScheduledImportDialog(QDialog):
    """定时导入任务管理对话框"""
    
    task_updated = pyqtSignal()  # 任务更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("定时导入任务管理")
        self.resize(900, 600)
        
        # 获取配置管理器
        try:
            self.config_manager = ImportConfigManager()
        except Exception as e:
            logger.error(f"初始化配置管理器失败: {e}")
            self.config_manager = None
        
        self._setup_ui()
        self._load_tasks()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("📅 定时导入任务管理")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # 任务表格
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels([
            "任务名称", "数据源", "资产类型", "定时规则", "状态", "下次执行", "操作"
        ])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.task_table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._load_tasks)
        button_layout.addWidget(self.refresh_btn)
        
        self.create_btn = QPushButton("➕ 新建任务")
        self.create_btn.clicked.connect(self._create_task)
        button_layout.addWidget(self.create_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # 提示信息
        info_label = QLabel("💡 提示：右键点击任务可以进行编辑、启用/禁用、删除等操作")
        info_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        layout.addWidget(info_label)
    
    def _load_tasks(self):
        """加载定时任务列表"""
        try:
            if not self.config_manager:
                self.task_table.setRowCount(0)
                return
            
            # 获取所有任务
            all_tasks = self.config_manager.get_import_tasks()
            
            # 筛选定时任务（有schedule_cron字段且不为空）
            scheduled_tasks = [
                task for task in all_tasks 
                if hasattr(task, 'schedule_cron') and task.schedule_cron
            ]
            
            # 存储任务映射（行号 -> task_id）
            self._task_map = {}
            
            self.task_table.setRowCount(len(scheduled_tasks))
            
            for row, task in enumerate(scheduled_tasks):
                # 存储task_id用于后续操作
                self._task_map[row] = task.task_id
                
                # 任务名称
                self.task_table.setItem(row, 0, QTableWidgetItem(task.name))
                
                # 数据源
                data_source = getattr(task, 'data_source', '未知')
                self.task_table.setItem(row, 1, QTableWidgetItem(data_source))
                
                # 资产类型
                asset_type = getattr(task, 'asset_type', '未知')
                if hasattr(asset_type, 'value'):
                    asset_type = asset_type.value
                self.task_table.setItem(row, 2, QTableWidgetItem(str(asset_type)))
                
                # 定时规则
                schedule_cron = getattr(task, 'schedule_cron', '')
                self.task_table.setItem(row, 3, QTableWidgetItem(schedule_cron))
                
                # 状态
                status = getattr(task, 'status', 'unknown')
                status_item = QTableWidgetItem(self._format_status(status))
                status_item.setTextAlignment(Qt.AlignCenter)
                self.task_table.setItem(row, 4, status_item)
                
                # 下次执行（需要解析cron表达式）
                next_run = self._calculate_next_run(schedule_cron)
                self.task_table.setItem(row, 5, QTableWidgetItem(next_run))
                
                # 操作按钮
                action_widget = self._create_action_buttons(task)
                self.task_table.setCellWidget(row, 6, action_widget)
            
            logger.info(f"加载定时任务完成: {len(scheduled_tasks)}个")
            
        except Exception as e:
            logger.error(f"加载定时任务失败: {e}")
            QMessageBox.warning(self, "错误", f"加载任务失败: {e}")
    
    def _format_status(self, status: str) -> str:
        """格式化状态显示"""
        status_map = {
            'pending': '⏸️ 待执行',
            'running': '▶️ 运行中',
            'completed': '✅ 已完成',
            'failed': '❌ 失败',
            'paused': '⏸️ 已暂停'
        }
        return status_map.get(status, status)
    
    def _calculate_next_run(self, cron_expr: str) -> str:
        """计算下次执行时间（简化版）"""
        if not cron_expr:
            return "未设置"
        
        # 这里应该使用croniter等库解析cron表达式
        # 简化实现：只显示cron表达式
        return f"按计划: {cron_expr}"
    
    def _create_action_buttons(self, task) -> QLabel:
        """创建操作按钮"""
        widget = QLabel()
        widget.setText("右键操作")
        widget.setAlignment(Qt.AlignCenter)
        widget.setStyleSheet("color: blue; text-decoration: underline; cursor: pointer;")
        return widget
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        row = self.task_table.rowAt(pos.y())
        if row < 0:
            return
        
        menu = QMenu(self)
        
        edit_action = menu.addAction("✏️ 编辑")
        enable_action = menu.addAction("▶️ 启用")
        disable_action = menu.addAction("⏸️ 禁用")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ 删除")
        
        action = menu.exec_(self.task_table.viewport().mapToGlobal(pos))
        
        if action == edit_action:
            self._edit_task(row)
        elif action == enable_action:
            self._enable_task(row)
        elif action == disable_action:
            self._disable_task(row)
        elif action == delete_action:
            self._delete_task(row)
    
    def _create_task(self):
        """创建新任务"""
        QMessageBox.information(
            self, 
            "提示", 
            "请使用主界面的'数据导入'功能创建导入任务，\n"
            "并在任务配置中设置定时规则。"
        )
    
    def _edit_task(self, row: int):
        """编辑任务"""
        if row not in self._task_map:
            QMessageBox.warning(self, "错误", "无法获取任务信息")
            return
        
        task_id = self._task_map[row]
        task_name = self.task_table.item(row, 0).text()
        
        QMessageBox.information(
            self, 
            "提示", 
            f"请使用主界面的'增强版数据导入'功能编辑任务\n"
            f"任务: {task_name}\n"
            f"任务ID: {task_id}"
        )
    
    def _enable_task(self, row: int):
        """启用任务"""
        if row not in self._task_map:
            QMessageBox.warning(self, "错误", "无法获取任务信息")
            return
        
        task_id = self._task_map[row]
        task_name = self.task_table.item(row, 0).text()
        
        try:
            # 更新任务状态为启用
            self.config_manager.update_import_task(task_id, enabled=True)
            logger.info(f"启用任务: {task_name} ({task_id})")
            QMessageBox.information(self, "成功", f"任务 '{task_name}' 已启用")
            self._load_tasks()
            self.task_updated.emit()
        except Exception as e:
            logger.error(f"启用任务失败: {e}")
            QMessageBox.warning(self, "错误", f"启用任务失败: {e}")
    
    def _disable_task(self, row: int):
        """禁用任务"""
        if row not in self._task_map:
            QMessageBox.warning(self, "错误", "无法获取任务信息")
            return
        
        task_id = self._task_map[row]
        task_name = self.task_table.item(row, 0).text()
        
        try:
            # 更新任务状态为禁用
            self.config_manager.update_import_task(task_id, enabled=False)
            logger.info(f"禁用任务: {task_name} ({task_id})")
            QMessageBox.information(self, "成功", f"任务 '{task_name}' 已禁用")
            self._load_tasks()
            self.task_updated.emit()
        except Exception as e:
            logger.error(f"禁用任务失败: {e}")
            QMessageBox.warning(self, "错误", f"禁用任务失败: {e}")
    
    def _delete_task(self, row: int):
        """删除任务"""
        if row not in self._task_map:
            QMessageBox.warning(self, "错误", "无法获取任务信息")
            return
        
        task_id = self._task_map[row]
        task_name = self.task_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除任务 '{task_name}' 吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.config_manager.delete_import_task(task_id)
                logger.info(f"删除任务成功: {task_name} ({task_id})")
                QMessageBox.information(self, "成功", f"任务 '{task_name}' 已删除")
                self._load_tasks()
                self.task_updated.emit()
            except Exception as e:
                logger.error(f"删除任务失败: {e}")
                QMessageBox.warning(self, "错误", f"删除任务失败: {e}")

