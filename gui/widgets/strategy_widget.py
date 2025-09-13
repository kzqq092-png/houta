from loguru import logger
"""
策略控件模块

提供策略配置和管理功能
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal
from gui.widgets.log_widget import LogWidget
from utils.theme import get_theme_manager
# log_structured已替换为直接的logger调用

class StrategyWidget(QWidget):
    """策略控件类"""

    # 定义信号
    strategy_changed = pyqtSignal(str, dict)  # 策略名称, 参数
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, parent=None):
        """初始化策略控件

        Args:
            # log_manager: 已迁移到Loguru日志系统
            parent: 父窗口
        """
        try:
            super().__init__(parent)

            # 使用传入的日志管理器或创建新的
            # 纯Loguru架构，移除log_manager依赖

            # 初始化变量
            self.current_strategy = None
            self.param_controls = {}

            # 初始化UI
            self.init_ui()

            # 连接信号
            self.connect_signals()

            # 设置样式
            self.theme_manager = get_theme_manager()

            logger.info("strategy_widget_init", status="success")

        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            logger.error("strategy_widget_init", status="fail", error=error_msg)
            self.error_occurred.emit(error_msg)

    def init_ui(self):
        """初始化UI"""
        try:
            # 创建主布局
            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)

            # 创建策略选择组
            strategy_group = QGroupBox("策略选择")
            strategy_layout = QFormLayout(strategy_group)

            # 策略类型选择
            self.strategy_combo = QComboBox()
            self.strategy_combo.addItems([
                "均线策略", "MACD策略", "RSI策略", "布林带策略",
                "KDJ策略", "自定义策略"
            ])
            strategy_layout.addRow("策略类型:", self.strategy_combo)

            layout.addWidget(strategy_group)

            # 创建参数设置组
            params_group = QGroupBox("参数设置")
            self.params_layout = QFormLayout(params_group)

            # 创建滚动区域
            scroll = QScrollArea()
            scroll.setWidget(params_group)
            scroll.setWidgetResizable(True)
            layout.addWidget(scroll)

            # 创建按钮组
            button_layout = QHBoxLayout()

            # 应用按钮
            self.apply_button = QPushButton("应用")
            button_layout.addWidget(self.apply_button)

            # 重置按钮
            self.reset_button = QPushButton("重置")
            button_layout.addWidget(self.reset_button)

            # 保存按钮
            self.save_button = QPushButton("保存")
            button_layout.addWidget(self.save_button)

            # 加载配置按钮
            self.load_button = QPushButton("加载配置")
            button_layout.addWidget(self.load_button)

            # 配置管理按钮
            self.manage_button = QPushButton("管理配置")
            button_layout.addWidget(self.manage_button)

            layout.addLayout(button_layout)

            logger.info("strategy_widget_ui_init", status="success")

        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            logger.error("strategy_widget_ui_init", status="fail", error=error_msg)
            self.error_occurred.emit(error_msg)

    def connect_signals(self):
        """连接信号"""
        try:
            # 连接策略选择信号
            self.strategy_combo.currentTextChanged.connect(
                self.on_strategy_changed)

            # 连接按钮信号
            self.apply_button.clicked.connect(self.apply_strategy)
            self.reset_button.clicked.connect(self.reset_params)
            self.save_button.clicked.connect(self.save_strategy)
            self.load_button.clicked.connect(self.load_strategy_config)
            self.manage_button.clicked.connect(self.show_config_manager)

            logger.info("signal_connected", status="success")

        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            logger.error("signal_connected", status="fail", error=error_msg)
            self.error_occurred.emit(error_msg)

    def on_strategy_changed(self, strategy: str):
        """处理策略变更事件

        Args:
            strategy: 策略名称
        """
        try:
            self.current_strategy = strategy
            self.update_params()
            logger.info(f"切换到策略: {strategy}")

        except Exception as e:
            error_msg = f"切换策略失败: {str(e)}"
            logger.error(f"切换策略失败: {error_msg}")
            self.error_occurred.emit(error_msg)

    def update_params(self):
        """更新参数控件"""
        try:
            # 清除现有参数控件
            while self.params_layout.count():
                item = self.params_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 清除参数控件字典
            self.param_controls.clear()

            # 根据策略类型添加参数控件
            if self.current_strategy == "均线策略":
                self._add_ma_params()
            elif self.current_strategy == "MACD策略":
                self._add_macd_params()
            elif self.current_strategy == "RSI策略":
                self._add_rsi_params()
            elif self.current_strategy == "布林带策略":
                self._add_boll_params()
            elif self.current_strategy == "KDJ策略":
                self._add_kdj_params()
            elif self.current_strategy == "自定义策略":
                self._add_custom_params()

            logger.info("参数控件更新完成")

        except Exception as e:
            error_msg = f"更新参数控件失败: {str(e)}"
            logger.error(f"更新参数控件失败: {error_msg}")
            self.error_occurred.emit(error_msg)

    def _add_ma_params(self):
        """添加均线策略参数"""
        try:
            # 快线周期
            fast_period = QSpinBox()
            fast_period.setRange(5, 120)
            fast_period.setValue(5)
            self.params_layout.addRow("快线周期:", fast_period)
            self.param_controls["fast_period"] = fast_period

            # 慢线周期
            slow_period = QSpinBox()
            slow_period.setRange(10, 250)
            slow_period.setValue(20)
            self.params_layout.addRow("慢线周期:", slow_period)
            self.param_controls["slow_period"] = slow_period

        except Exception as e:
            logger.error(f"添加均线参数失败: {str(e)}")

    def _add_macd_params(self):
        """添加MACD策略参数"""
        try:
            # 快线周期
            fast_period = QSpinBox()
            fast_period.setRange(5, 50)
            fast_period.setValue(7)
            self.params_layout.addRow("快线周期:", fast_period)
            self.param_controls["fast_period"] = fast_period

            # 慢线周期
            slow_period = QSpinBox()
            slow_period.setRange(10, 100)
            slow_period.setValue(26)
            self.params_layout.addRow("慢线周期:", slow_period)
            self.param_controls["slow_period"] = slow_period

            # 信号周期
            signal_period = QSpinBox()
            signal_period.setRange(2, 20)
            signal_period.setValue(9)
            self.params_layout.addRow("信号周期:", signal_period)
            self.param_controls["signal_period"] = signal_period

        except Exception as e:
            logger.error(f"添加MACD参数失败: {str(e)}")

    def _add_rsi_params(self):
        """添加RSI策略参数"""
        try:
            # RSI周期
            period = QSpinBox()
            period.setRange(5, 30)
            period.setValue(14)
            self.params_layout.addRow("RSI周期:", period)
            self.param_controls["period"] = period

            # 超买阈值
            overbought = QDoubleSpinBox()
            overbought.setRange(50, 90)
            overbought.setValue(70)
            self.params_layout.addRow("超买阈值:", overbought)
            self.param_controls["overbought"] = overbought

            # 超卖阈值
            oversold = QDoubleSpinBox()
            oversold.setRange(10, 50)
            oversold.setValue(30)
            self.params_layout.addRow("超卖阈值:", oversold)
            self.param_controls["oversold"] = oversold

        except Exception as e:
            logger.error(f"添加RSI参数失败: {str(e)}")

    def _add_boll_params(self):
        """添加布林带策略参数"""
        try:
            # 周期
            period = QSpinBox()
            period.setRange(10, 100)
            period.setValue(20)
            self.params_layout.addRow("周期:", period)
            self.param_controls["period"] = period

            # 标准差倍数
            std = QDoubleSpinBox()
            std.setRange(1.0, 3.0)
            std.setValue(2.0)
            std.setSingleStep(0.1)
            self.params_layout.addRow("标准差倍数:", std)
            self.param_controls["std"] = std

        except Exception as e:
            logger.error(f"添加布林带参数失败: {str(e)}")

    def _add_kdj_params(self):
        """添加KDJ策略参数"""
        try:
            # 周期
            period = QSpinBox()
            period.setRange(5, 30)
            period.setValue(9)
            self.params_layout.addRow("周期:", period)
            self.param_controls["period"] = period

            # K值平滑因子
            k_factor = QDoubleSpinBox()
            k_factor.setRange(0.1, 1.0)
            k_factor.setValue(0.33)
            k_factor.setSingleStep(0.01)
            self.params_layout.addRow("K值平滑因子:", k_factor)
            self.param_controls["k_factor"] = k_factor

            # D值平滑因子
            d_factor = QDoubleSpinBox()
            d_factor.setRange(0.1, 1.0)
            d_factor.setValue(0.33)
            d_factor.setSingleStep(0.01)
            self.params_layout.addRow("D值平滑因子:", d_factor)
            self.param_controls["d_factor"] = d_factor

        except Exception as e:
            logger.error(f"添加KDJ参数失败: {str(e)}")

    def _add_custom_params(self):
        """添加自定义策略参数"""
        try:
            # 参数名称
            name = QLineEdit()
            self.params_layout.addRow("参数名称:", name)
            self.param_controls["name"] = name

            # 参数值
            value = QLineEdit()
            self.params_layout.addRow("参数值:", value)
            self.param_controls["value"] = value

        except Exception as e:
            logger.error(f"添加自定义参数失败: {str(e)}")

    def apply_strategy(self):
        """应用策略"""
        try:
            # 获取参数值
            params = {}
            for name, control in self.param_controls.items():
                if isinstance(control, (QSpinBox, QDoubleSpinBox)):
                    params[name] = control.value()
                elif isinstance(control, QLineEdit):
                    params[name] = control.text()

            # 发送策略变更信号
            self.strategy_changed.emit(self.current_strategy, params)

            logger.info(f"应用策略: {self.current_strategy}")

        except Exception as e:
            error_msg = f"应用策略失败: {str(e)}"
            logger.error(f"应用策略失败: {error_msg}")
            self.error_occurred.emit(error_msg)

    def reset_params(self):
        """重置参数"""
        try:
            # 重置所有参数控件
            for control in self.param_controls.values():
                if isinstance(control, QSpinBox):
                    control.setValue(control.minimum())
                elif isinstance(control, QDoubleSpinBox):
                    control.setValue(control.minimum())
                elif isinstance(control, QLineEdit):
                    control.clear()

            logger.info("参数已重置")

        except Exception as e:
            error_msg = f"重置参数失败: {str(e)}"
            logger.error(f"重置参数失败: {error_msg}")
            self.error_occurred.emit(error_msg)

    def save_strategy(self):
        """保存策略"""
        try:
            # 获取参数值
            params = {}
            for name, control in self.param_controls.items():
                if isinstance(control, (QSpinBox, QDoubleSpinBox)):
                    params[name] = control.value()
                elif isinstance(control, QLineEdit):
                    params[name] = control.text()

            # 弹出保存对话框
            save_dialog = QDialog(self)
            save_dialog.setWindowTitle("保存策略配置")
            save_dialog.setModal(True)
            save_dialog.resize(400, 200)

            layout = QVBoxLayout(save_dialog)

            # 策略名称
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("策略名称:"))
            name_edit = QLineEdit()
            name_edit.setText(f"{self.current_strategy}_配置")
            name_layout.addWidget(name_edit)
            layout.addLayout(name_layout)

            # 描述
            desc_layout = QVBoxLayout()
            desc_layout.addWidget(QLabel("策略描述:"))
            desc_edit = QTextEdit()
            desc_edit.setPlainText(f"基于{self.current_strategy}策略的配置")
            desc_layout.addWidget(desc_edit)
            layout.addLayout(desc_layout)

            # 按钮
            button_layout = QHBoxLayout()
            save_btn = QPushButton("保存")
            cancel_btn = QPushButton("取消")
            button_layout.addWidget(save_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)

            def on_save():
                config_name = name_edit.text().strip()
                config_desc = desc_edit.toPlainText().strip()

                if not config_name:
                    QMessageBox.warning(save_dialog, "错误", "请输入策略名称")
                    return

                # 保存策略配置
                self._save_strategy_config(config_name, config_desc, params)
                QMessageBox.information(save_dialog, "成功", "策略配置已保存")
                save_dialog.accept()

            save_btn.clicked.connect(on_save)
            cancel_btn.clicked.connect(save_dialog.reject)

            save_dialog.exec_()

            logger.info(f"保存策略: {self.current_strategy}")

        except Exception as e:
            error_msg = f"保存策略失败: {str(e)}"
            logger.error(f"保存策略失败: {error_msg}")
            self.error_occurred.emit(error_msg)

    def refresh(self) -> None:
        """
        刷新策略控件内容，异常只记录日志不抛出。
        """
        try:
            self.update_params()
        except Exception as e:
            error_msg = f"刷新策略控件失败: {str(e)}"
            logger.error(f"刷新策略控件失败: {error_msg}")
            # 发射异常信号，主窗口可捕获弹窗
            self.error_occurred.emit(error_msg)

    def update(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def reload(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def _save_strategy_config(self, name: str, description: str, params: dict):
        """保存策略配置到文件"""
        try:
            import json
            import os
            from datetime import datetime

            # 创建配置目录
            config_dir = "configs/strategies"
            os.makedirs(config_dir, exist_ok=True)

            # 构建配置数据
            config_data = {
                'name': name,
                'description': description,
                'strategy_type': self.current_strategy,
                'parameters': params,
                'created_time': datetime.now().isoformat(),
                'version': '1.0'
            }

            # 保存到文件
            filename = f"{name.replace(' ', '_')}.json"
            filepath = os.path.join(config_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            logger.info(f"策略配置已保存到: {filepath}")

        except Exception as e:
            logger.error(f"保存策略配置失败: {str(e)}")
            raise

    def _load_strategy_config(self, filepath: str) -> dict:
        """从文件加载策略配置"""
        try:

            with open(filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            logger.info(f"策略配置已加载: {filepath}")
            return config_data

        except Exception as e:
            logger.error(f"加载策略配置失败: {str(e)}")
            raise

    def load_strategy_config(self):
        """加载策略配置"""
        try:
            from PyQt5.QtWidgets import QFileDialog

            # 选择配置文件
            config_dir = "configs/strategies"
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "选择策略配置文件",
                config_dir,
                "JSON文件 (*.json)"
            )

            if not filepath:
                return

            # 加载配置
            config_data = self._load_strategy_config(filepath)

            # 应用配置
            if config_data['strategy_type'] != self.current_strategy:
                # 切换策略类型
                self.current_strategy = config_data['strategy_type']
                self.update_params()

            # 设置参数值
            params = config_data.get('parameters', {})
            for name, value in params.items():
                if name in self.param_controls:
                    control = self.param_controls[name]
                    if isinstance(control, (QSpinBox, QDoubleSpinBox)):
                        control.setValue(value)
                    elif isinstance(control, QLineEdit):
                        control.setText(str(value))

            QMessageBox.information(
                self, "成功", f"策略配置 '{config_data['name']}' 已加载")
            logger.info(f"策略配置已加载: {config_data['name']}")

        except Exception as e:
            error_msg = f"加载策略配置失败: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def get_saved_configs(self) -> list:
        """获取已保存的策略配置列表"""
        try:

            config_dir = "configs/strategies"
            if not os.path.exists(config_dir):
                return []

            configs = []
            for filename in os.listdir(config_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(config_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                        configs.append({
                            'filepath': filepath,
                            'name': config_data.get('name', filename),
                            'description': config_data.get('description', ''),
                            'strategy_type': config_data.get('strategy_type', ''),
                            'created_time': config_data.get('created_time', '')
                        })
                    except Exception as e:
                        log_structured( f"读取配置文件失败 {filename}: {str(e)}", level="warning")
                        continue

            return configs

        except Exception as e:
            logger.error(f"获取配置列表失败: {str(e)}")
            return []

    def show_config_manager(self):
        """显示策略配置管理器"""
        try:
            # 创建配置管理对话框
            manager_dialog = QDialog(self)
            manager_dialog.setWindowTitle("策略配置管理器")
            manager_dialog.setModal(True)
            manager_dialog.resize(600, 400)

            layout = QVBoxLayout(manager_dialog)

            # 配置列表
            config_table = QTableWidget()
            config_table.setColumnCount(4)
            config_table.setHorizontalHeaderLabels(
                ["配置名称", "策略类型", "描述", "创建时间"])

            # 加载配置列表
            configs = self.get_saved_configs()
            config_table.setRowCount(len(configs))

            for i, config in enumerate(configs):
                config_table.setItem(i, 0, QTableWidgetItem(config['name']))
                config_table.setItem(
                    i, 1, QTableWidgetItem(config['strategy_type']))
                config_table.setItem(
                    i, 2, QTableWidgetItem(config['description']))
                config_table.setItem(
                    i, 3, QTableWidgetItem(config['created_time']))

            config_table.resizeColumnsToContents()
            layout.addWidget(config_table)

            # 按钮
            button_layout = QHBoxLayout()
            load_btn = QPushButton("加载配置")
            delete_btn = QPushButton("删除配置")
            close_btn = QPushButton("关闭")
            button_layout.addWidget(load_btn)
            button_layout.addWidget(delete_btn)
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)

            def load_selected():
                current_row = config_table.currentRow()
                if current_row >= 0:
                    config = configs[current_row]
                    try:
                        config_data = self._load_strategy_config(
                            config['filepath'])

                        # 切换策略类型
                        if config_data['strategy_type'] != self.current_strategy:
                            self.current_strategy = config_data['strategy_type']
                            self.update_params()

                        # 设置参数值
                        params = config_data.get('parameters', {})
                        for name, value in params.items():
                            if name in self.param_controls:
                                control = self.param_controls[name]
                                if isinstance(control, (QSpinBox, QDoubleSpinBox)):
                                    control.setValue(value)
                                elif isinstance(control, QLineEdit):
                                    control.setText(str(value))

                        QMessageBox.information(
                            manager_dialog, "成功", f"配置 '{config['name']}' 已加载")
                        manager_dialog.accept()

                    except Exception as e:
                        QMessageBox.critical(
                            manager_dialog, "错误", f"加载配置失败: {str(e)}")
                else:
                    QMessageBox.warning(manager_dialog, "提示", "请选择要加载的配置")

            def delete_selected():
                current_row = config_table.currentRow()
                if current_row >= 0:
                    config = configs[current_row]
                    reply = QMessageBox.question(manager_dialog, "确认删除",
                                                 f"确定要删除配置 '{config['name']}' 吗？",
                                                 QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        try:
                            os.remove(config['filepath'])
                            config_table.removeRow(current_row)
                            configs.pop(current_row)
                            QMessageBox.information(
                                manager_dialog, "成功", "配置已删除")
                        except Exception as e:
                            QMessageBox.critical(
                                manager_dialog, "错误", f"删除配置失败: {str(e)}")
                else:
                    QMessageBox.warning(manager_dialog, "提示", "请选择要删除的配置")

            load_btn.clicked.connect(load_selected)
            delete_btn.clicked.connect(delete_selected)
            close_btn.clicked.connect(manager_dialog.reject)

            manager_dialog.exec_()

        except Exception as e:
            error_msg = f"显示配置管理器失败: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
