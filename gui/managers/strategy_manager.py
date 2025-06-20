"""
策略管理器模块
提供策略的创建、导入、导出、回测、优化等功能
"""

import traceback
from typing import List, Dict, Any, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QFileDialog, QInputDialog
)
from PyQt5.QtCore import QObject, pyqtSignal

from core.strategy import (
    list_available_strategies, get_strategy_info, execute_strategy
)


class StrategyManager(QObject):
    """策略管理器"""

    # 信号定义
    strategy_created = pyqtSignal(str)  # 策略创建信号
    strategy_imported = pyqtSignal(str)  # 策略导入信号
    strategy_exported = pyqtSignal(str)  # 策略导出信号
    backtest_started = pyqtSignal(str)  # 回测开始信号
    optimization_started = pyqtSignal(str)  # 优化开始信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.log_manager = getattr(parent, 'log_manager', None)
        self.available_strategies = []
        self._load_strategies()

    def _load_strategies(self):
        """加载可用策略列表"""
        try:
            self.available_strategies = list_available_strategies()
            if self.log_manager:
                self.log_manager.info(f"加载了 {len(self.available_strategies)} 个策略")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"加载策略列表失败: {str(e)}")
            self.available_strategies = []

    def show_strategy_manager(self):
        """显示策略管理器"""
        try:
            from gui.dialogs.strategy_manager_dialog import StrategyManagerDialog
            dialog = StrategyManagerDialog(self.parent)
            dialog.exec_()
        except ImportError:
            # 如果策略管理器对话框不存在，创建一个简单的策略列表对话框
            self._show_simple_strategy_manager()
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"显示策略管理器失败: {str(e)}")
            self._handle_error(f"无法打开策略管理器: {str(e)}")

    def _show_simple_strategy_manager(self):
        """显示简单的策略管理器"""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("策略管理器")
        dialog.setModal(True)
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        # 策略列表
        strategy_list = QListWidget()
        for strategy_name in self.available_strategies:
            item = QListWidgetItem(strategy_name)
            strategy_list.addItem(item)

        layout.addWidget(QLabel("可用策略:"))
        layout.addWidget(strategy_list)

        # 按钮
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        info_btn = QPushButton("查看详情")
        create_btn = QPushButton("创建策略")
        import_btn = QPushButton("导入策略")
        export_btn = QPushButton("导出策略")
        backtest_btn = QPushButton("回测策略")
        optimize_btn = QPushButton("优化策略")
        close_btn = QPushButton("关闭")

        # 连接信号
        refresh_btn.clicked.connect(lambda: self._refresh_strategy_list(strategy_list))
        info_btn.clicked.connect(lambda: self._show_strategy_info(strategy_list))
        create_btn.clicked.connect(self.create_new_strategy)
        import_btn.clicked.connect(self.import_strategy)
        export_btn.clicked.connect(self.export_strategy)
        backtest_btn.clicked.connect(self.backtest_strategy)
        optimize_btn.clicked.connect(self.optimize_strategy)
        close_btn.clicked.connect(dialog.accept)

        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(info_btn)
        button_layout.addWidget(create_btn)
        button_layout.addWidget(import_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(backtest_btn)
        button_layout.addWidget(optimize_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        dialog.exec_()

    def _refresh_strategy_list(self, strategy_list):
        """刷新策略列表"""
        try:
            strategy_list.clear()
            self._load_strategies()
            for strategy_name in self.available_strategies:
                item = QListWidgetItem(strategy_name)
                strategy_list.addItem(item)
            if self.log_manager:
                self.log_manager.info(f"策略列表已刷新，共 {len(self.available_strategies)} 个策略")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"刷新策略列表失败: {str(e)}")

    def _show_strategy_info(self, strategy_list):
        """显示策略详情"""
        current_item = strategy_list.currentItem()
        if not current_item:
            QMessageBox.information(self.parent, "提示", "请先选择一个策略")
            return

        strategy_name = current_item.text()
        try:
            strategy_info = get_strategy_info(strategy_name)
            if strategy_info:
                info_text = f"""
策略名称: {strategy_info.get('name', strategy_name)}
策略类型: {strategy_info.get('strategy_type', '未知')}
版本: {strategy_info.get('version', '1.0.0')}
作者: {strategy_info.get('author', '未知')}
描述: {strategy_info.get('description', '无描述')}
分类: {strategy_info.get('category', '未分类')}
创建时间: {strategy_info.get('created_at', '未知')}
"""
                QMessageBox.information(self.parent, f"策略详情 - {strategy_name}", info_text)
            else:
                QMessageBox.warning(self.parent, "警告", f"无法获取策略 '{strategy_name}' 的详细信息")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取策略信息失败: {str(e)}")
            QMessageBox.critical(self.parent, "错误", f"获取策略信息失败: {str(e)}")

    def create_new_strategy(self):
        """创建新策略"""
        try:
            # 获取策略名称
            strategy_name, ok = QInputDialog.getText(
                self.parent, "创建新策略", "请输入策略名称:"
            )
            if ok and strategy_name:
                # 这里可以实现策略创建逻辑
                QMessageBox.information(
                    self.parent, "提示",
                    f"策略创建功能正在开发中...\n策略名称: {strategy_name}"
                )
                self.strategy_created.emit(strategy_name)
                if self.log_manager:
                    self.log_manager.info(f"策略创建请求: {strategy_name}")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建策略失败: {str(e)}")
            self._handle_error(f"创建策略失败: {str(e)}")

    def import_strategy(self):
        """导入策略"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent, "导入策略", "",
                "Python文件 (*.py);;JSON文件 (*.json);;所有文件 (*)"
            )
            if file_path:
                # 这里可以实现策略导入逻辑
                QMessageBox.information(
                    self.parent, "提示",
                    f"策略导入功能正在开发中...\n选择的文件: {file_path}"
                )
                self.strategy_imported.emit(file_path)
                if self.log_manager:
                    self.log_manager.info(f"策略导入请求: {file_path}")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"导入策略失败: {str(e)}")
            self._handle_error(f"导入策略失败: {str(e)}")

    def export_strategy(self):
        """导出策略"""
        try:
            if not self.available_strategies:
                QMessageBox.warning(self.parent, "警告", "没有可导出的策略")
                return

            # 选择要导出的策略
            strategy_name, ok = QInputDialog.getItem(
                self.parent, "选择策略", "请选择要导出的策略:",
                self.available_strategies, 0, False
            )
            if ok and strategy_name:
                file_path, _ = QFileDialog.getSaveFileName(
                    self.parent, "导出策略", f"{strategy_name}.json",
                    "JSON文件 (*.json);;所有文件 (*)"
                )
                if file_path:
                    # 这里可以实现策略导出逻辑
                    QMessageBox.information(
                        self.parent, "提示",
                        f"策略导出功能正在开发中...\n导出文件: {file_path}"
                    )
                    self.strategy_exported.emit(strategy_name)
                    if self.log_manager:
                        self.log_manager.info(f"策略导出请求: {strategy_name} -> {file_path}")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"导出策略失败: {str(e)}")
            self._handle_error(f"导出策略失败: {str(e)}")

    def backtest_strategy(self):
        """策略回测"""
        try:
            if not hasattr(self.parent, 'current_stock') or not self.parent.current_stock:
                QMessageBox.warning(self.parent, "警告", "请先选择股票")
                return

            if not self.available_strategies:
                QMessageBox.warning(self.parent, "警告", "没有可用的策略")
                return

            # 选择要回测的策略
            strategy_name, ok = QInputDialog.getItem(
                self.parent, "选择策略", "请选择要回测的策略:",
                self.available_strategies, 0, False
            )
            if ok and strategy_name:
                # 使用现有的回测方法
                if hasattr(self.parent, 'backtest'):
                    self.parent.backtest()
                    self.backtest_started.emit(strategy_name)
                    if self.log_manager:
                        self.log_manager.info(f"策略回测开始: {strategy_name}")
                else:
                    QMessageBox.warning(self.parent, "警告", "回测功能不可用")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"策略回测失败: {str(e)}")
            self._handle_error(f"策略回测失败: {str(e)}")

    def optimize_strategy(self):
        """策略优化"""
        try:
            if not hasattr(self.parent, 'current_stock') or not self.parent.current_stock:
                QMessageBox.warning(self.parent, "警告", "请先选择股票")
                return

            if not self.available_strategies:
                QMessageBox.warning(self.parent, "警告", "没有可用的策略")
                return

            # 选择要优化的策略
            strategy_name, ok = QInputDialog.getItem(
                self.parent, "选择策略", "请选择要优化的策略:",
                self.available_strategies, 0, False
            )
            if ok and strategy_name:
                # 使用现有的优化方法
                if hasattr(self.parent, 'optimize'):
                    self.parent.optimize()
                    self.optimization_started.emit(strategy_name)
                    if self.log_manager:
                        self.log_manager.info(f"策略优化开始: {strategy_name}")
                else:
                    QMessageBox.warning(self.parent, "警告", "优化功能不可用")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"策略优化失败: {str(e)}")
            self._handle_error(f"策略优化失败: {str(e)}")

    def get_available_strategies(self) -> List[str]:
        """获取可用策略列表"""
        return self.available_strategies.copy()

    def get_strategy_info(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """获取策略信息"""
        try:
            return get_strategy_info(strategy_name)
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取策略信息失败: {str(e)}")
            return None

    def _handle_error(self, error_msg: str):
        """处理错误"""
        if hasattr(self.parent, 'handle_error'):
            self.parent.handle_error(error_msg)
        else:
            QMessageBox.critical(self.parent, "错误", error_msg)
