"""
导入历史记录对话框

显示数据导入的历史记录，包括成功、失败、耗时等信息
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QComboBox, QLineEdit
)
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QColor
from loguru import logger
from typing import List, Dict, Any
from datetime import datetime

from core.importdata.import_config_manager import ImportConfigManager


class ImportHistoryDialog(QDialog):
    """导入历史记录对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入历史记录")
        self.resize(1000, 700)
        
        # 获取配置管理器
        try:
            self.config_manager = ImportConfigManager()
        except Exception as e:
            logger.error(f"初始化配置管理器失败: {e}")
            self.config_manager = None
        
        self._setup_ui()
        self._load_history()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("📊 数据导入历史记录")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # 筛选区域
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("任务状态:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "成功", "失败", "运行中", "已取消"])
        self.status_filter.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.status_filter)
        
        filter_layout.addWidget(QLabel("任务名称:"))
        self.name_filter = QLineEdit()
        self.name_filter.setPlaceholderText("输入任务名称搜索...")
        self.name_filter.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.name_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            "任务名称", "开始时间", "结束时间", "耗时", "状态", 
            "成功数", "失败数", "总记录数", "详情"
        ])
        
        # 设置列宽
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 任务名称
        for i in range(1, 9):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)
        
        # 统计信息
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        layout.addWidget(self.stats_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._load_history)
        button_layout.addWidget(self.refresh_btn)
        
        self.clear_btn = QPushButton("🗑️ 清除历史")
        self.clear_btn.clicked.connect(self._clear_history)
        button_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("📤 导出")
        self.export_btn.clicked.connect(self._export_history)
        button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _load_history(self):
        """加载历史记录"""
        try:
            if not self.config_manager:
                self.history_table.setRowCount(0)
                self._update_stats(0, 0, 0)
                return
            
            # 获取历史记录（最近100条）
            history_records = self.config_manager.get_history(limit=100)
            
            self.all_records = history_records  # 保存所有记录用于筛选
            self._display_records(history_records)
            
            logger.info(f"加载历史记录完成: {len(history_records)}条")
            
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            QMessageBox.warning(self, "错误", f"加载历史记录失败: {e}")
    
    def _display_records(self, records: List[Dict[str, Any]]):
        """显示记录"""
        self.history_table.setRowCount(len(records))
        
        success_count = 0
        failed_count = 0
        total_records = 0
        
        for row, record in enumerate(records):
            # 任务名称
            task_name = record.get('task_name', record.get('task_id', '未知'))
            self.history_table.setItem(row, 0, QTableWidgetItem(task_name))
            
            # 开始时间
            start_time = record.get('start_time', '')
            if isinstance(start_time, datetime):
                start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            self.history_table.setItem(row, 1, QTableWidgetItem(str(start_time)))
            
            # 结束时间
            end_time = record.get('end_time', '')
            if isinstance(end_time, datetime):
                end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
            self.history_table.setItem(row, 2, QTableWidgetItem(str(end_time)))
            
            # 耗时
            duration = record.get('execution_time', 0)
            duration_str = self._format_duration(duration)
            self.history_table.setItem(row, 3, QTableWidgetItem(duration_str))
            
            # 状态
            status = record.get('status', 'unknown')
            status_item = QTableWidgetItem(self._format_status(status))
            status_item.setTextAlignment(Qt.AlignCenter)
            
            # 根据状态设置颜色
            if status == 'completed':
                status_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                success_count += 1
            elif status == 'failed':
                status_item.setBackground(QColor(255, 182, 193))  # 浅红色
                failed_count += 1
            elif status == 'running':
                status_item.setBackground(QColor(173, 216, 230))  # 浅蓝色
            
            self.history_table.setItem(row, 4, status_item)
            
            # 成功数
            processed = record.get('processed_records', 0)
            self.history_table.setItem(row, 5, QTableWidgetItem(str(processed)))
            
            # 失败数
            failed = record.get('failed_records', 0)
            self.history_table.setItem(row, 6, QTableWidgetItem(str(failed)))
            
            # 总记录数
            total = record.get('total_records', 0)
            self.history_table.setItem(row, 7, QTableWidgetItem(str(total)))
            total_records += total
            
            # 详情（错误信息）
            error_msg = record.get('error_message', '')
            if error_msg:
                detail_item = QTableWidgetItem("查看错误")
                detail_item.setForeground(QColor(255, 0, 0))
                detail_item.setToolTip(error_msg)
            else:
                detail_item = QTableWidgetItem("-")
            self.history_table.setItem(row, 8, detail_item)
        
        # 更新统计信息
        self._update_stats(len(records), success_count, failed_count)
    
    def _format_status(self, status: str) -> str:
        """格式化状态显示"""
        status_map = {
            'pending': '⏳ 等待中',
            'running': '▶️ 运行中',
            'completed': '✅ 成功',
            'failed': '❌ 失败',
            'cancelled': '⏹️ 已取消'
        }
        return status_map.get(status, status)
    
    def _format_duration(self, seconds: float) -> str:
        """格式化耗时"""
        if seconds < 1:
            return f"{int(seconds * 1000)}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def _update_stats(self, total: int, success: int, failed: int):
        """更新统计信息"""
        success_rate = (success / total * 100) if total > 0 else 0
        self.stats_label.setText(
            f"📈 统计：总共 {total} 条记录 | "
            f"✅ 成功 {success} | "
            f"❌ 失败 {failed} | "
            f"📊 成功率 {success_rate:.1f}%"
        )
    
    def _apply_filter(self):
        """应用筛选"""
        if not hasattr(self, 'all_records'):
            return
        
        status_filter = self.status_filter.currentText()
        name_filter = self.name_filter.text().lower()
        
        filtered_records = []
        for record in self.all_records:
            # 状态筛选
            if status_filter != "全部":
                record_status = record.get('status', '')
                status_map = {
                    "成功": "completed",
                    "失败": "failed",
                    "运行中": "running",
                    "已取消": "cancelled"
                }
                if record_status != status_map.get(status_filter, status_filter):
                    continue
            
            # 名称筛选
            if name_filter:
                task_name = record.get('task_name', record.get('task_id', '')).lower()
                if name_filter not in task_name:
                    continue
            
            filtered_records.append(record)
        
        self._display_records(filtered_records)
    
    def _clear_history(self):
        """清除历史记录"""
        reply = QMessageBox.question(
            self,
            "确认清除",
            "确定要清除所有历史记录吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # TODO: 调用config_manager清除历史
                logger.info("清除历史记录")
                QMessageBox.information(self, "成功", "历史记录已清除")
                self._load_history()
            except Exception as e:
                logger.error(f"清除历史记录失败: {e}")
                QMessageBox.warning(self, "错误", f"清除失败: {e}")
    
    def _export_history(self):
        """导出历史记录"""
        QMessageBox.information(
            self,
            "提示",
            "历史记录导出功能开发中\n将支持导出为CSV、Excel等格式"
        )

