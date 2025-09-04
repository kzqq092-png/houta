#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警配置标签页
现代化告警配置和管理界面
"""

import json
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QTreeWidget, QTreeWidgetItem, QFormLayout, QCheckBox, QComboBox,
    QLineEdit, QSpinBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QMessageBox, QInputDialog, QFileDialog, QMenu, QLabel
)
from PyQt5.QtCore import QThreadPool, pyqtSlot, Qt
from PyQt5.QtGui import QColor
from gui.widgets.performance.workers.async_workers import AlertHistoryWorker
# 🔧 新增：导入数据库模型
from db.models.alert_config_models import (
    get_alert_config_database, NotificationConfig, AlertRule, AlertHistory
)
# 🔧 新增：导入告警服务
from core.services.alert_rule_engine import get_alert_rule_engine, initialize_alert_rule_engine
from core.services.alert_rule_hot_loader import get_alert_rule_hot_loader, initialize_alert_rule_hot_loader

logger = logging.getLogger(__name__)


class ModernAlertConfigTab(QWidget):
    """现代化告警配置标签页"""

    def __init__(self):
        super().__init__()
        # 🔧 新增：初始化数据库
        self.db = get_alert_config_database()
        self.alert_history = []  # 缓存告警历史数据
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 告警规则配置
        rules_group = QGroupBox("🚨 告警规则配置")
        rules_layout = QVBoxLayout()

        # 规则列表
        self.rules_tree = QTreeWidget()
        self.rules_tree.setHeaderLabels(["规则名称", "类型", "阈值", "状态"])
        # 🔧 新增：启用右键菜单
        self.rules_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.rules_tree.customContextMenuRequested.connect(self.show_rules_context_menu)
        rules_layout.addWidget(self.rules_tree)

        # 🔧 移除：删除原有的规则操作按钮
        # rules_buttons_layout = QHBoxLayout()
        # self.add_rule_btn = QPushButton("➕ 添加规则")
        # self.edit_rule_btn = QPushButton("✏️ 编辑规则")
        # self.delete_rule_btn = QPushButton("🗑️ 删除规则")
        #
        # rules_buttons_layout.addWidget(self.add_rule_btn)
        # rules_buttons_layout.addWidget(self.edit_rule_btn)
        # rules_buttons_layout.addWidget(self.delete_rule_btn)
        # rules_buttons_layout.addStretch()
        #
        # rules_layout.addLayout(rules_buttons_layout)

        rules_group.setLayout(rules_layout)
        layout.addWidget(rules_group)

        # 邮件通知配置 + 短信通知配置水平布局
        notifications_row_layout = QHBoxLayout()

        # 邮件通知设置
        email_group = QGroupBox("📧 邮件通知配置")
        email_layout = QFormLayout()

        self.email_enabled = QCheckBox("启用邮件通知")
        email_layout.addRow(self.email_enabled)

        # 邮件服务商选择
        self.email_provider = QComboBox()
        self.email_provider.addItems(["SMTP", "Mailgun", "SendGrid", "Brevo", "AhaSend"])
        email_layout.addRow("邮件服务商:", self.email_provider)

        # 发件人配置
        self.sender_email = QLineEdit()
        self.sender_email.setPlaceholderText("发件人邮箱")
        email_layout.addRow("发件人邮箱:", self.sender_email)

        self.sender_name = QLineEdit()
        self.sender_name.setText("FactorWeave-Quant 系统")
        email_layout.addRow("发件人名称:", self.sender_name)

        # API配置
        self.email_api_key = QLineEdit()
        self.email_api_key.setPlaceholderText("API Key 或邮箱密码")
        self.email_api_key.setEchoMode(QLineEdit.Password)
        email_layout.addRow("API Key:", self.email_api_key)

        # SMTP配置
        self.smtp_host = QLineEdit()
        self.smtp_host.setPlaceholderText("SMTP服务器地址")
        email_layout.addRow("SMTP服务器:", self.smtp_host)

        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        email_layout.addRow("SMTP端口:", self.smtp_port)

        # 收件人配置
        self.email_address = QLineEdit()
        self.email_address.setPlaceholderText("多个邮箱用逗号分隔")
        email_layout.addRow("收件人:", self.email_address)

        # 邮件测试按钮
        email_test_layout = QHBoxLayout()
        self.test_email_btn = QPushButton("📤 测试邮件")
        self.test_email_btn.clicked.connect(self.test_email_config)
        email_test_layout.addWidget(self.test_email_btn)
        email_test_layout.addStretch()
        email_layout.addRow("", email_test_layout)

        email_group.setLayout(email_layout)
        notifications_row_layout.addWidget(email_group)

        # 短信通知设置
        sms_group = QGroupBox("📱 短信通知配置")
        sms_layout = QVBoxLayout()

        # 短信配置表单
        sms_form_layout = QFormLayout()

        self.sms_enabled = QCheckBox("启用短信通知")
        sms_form_layout.addRow(self.sms_enabled)

        # 短信服务商选择
        self.sms_provider = QComboBox()
        self.sms_provider.addItems(["云片", "互亿无线", "Twilio", "YCloud", "SMSDove"])
        sms_form_layout.addRow("短信服务商:", self.sms_provider)

        # API配置
        self.sms_api_key = QLineEdit()
        self.sms_api_key.setPlaceholderText("短信API Key")
        self.sms_api_key.setEchoMode(QLineEdit.Password)
        sms_form_layout.addRow("API Key:", self.sms_api_key)

        self.sms_api_secret = QLineEdit()
        self.sms_api_secret.setPlaceholderText("API Secret (如需要)")
        self.sms_api_secret.setEchoMode(QLineEdit.Password)
        sms_form_layout.addRow("API Secret:", self.sms_api_secret)

        # 收件人配置
        self.phone_number = QLineEdit()
        self.phone_number.setPlaceholderText("多个手机号用逗号分隔")
        sms_form_layout.addRow("收件人:", self.phone_number)

        # 短信测试按钮
        sms_test_layout = QHBoxLayout()
        self.test_sms_btn = QPushButton("📲 测试短信")
        self.test_sms_btn.clicked.connect(self.test_sms_config)
        sms_test_layout.addWidget(self.test_sms_btn)
        sms_test_layout.addStretch()
        sms_form_layout.addRow("", sms_test_layout)

        sms_layout.addLayout(sms_form_layout)

        # 免费API服务说明（合并到短信通知配置中）
        info_text = QTextEdit()
        info_text.setMaximumHeight(120)
        info_text.setReadOnly(True)
        info_text.setHtml("""
        <b>💡 免费API服务说明：</b><br>
        <b>邮件服务商：</b><br>
        • <b>Mailgun</b>: 每月100封免费邮件    
        • <b>SendGrid</b>: 每天100封免费邮件    
        • <b>Brevo</b>: 每天300封免费邮件    
        • <b>AhaSend</b>: 每月1000封免费邮件<br><br>
        <b>短信服务商：</b><br>
        • <b>云片</b>: 注册送免费短信    
        • <b>互亿无线</b>: 注册送免费短信    
        • <b>Twilio</b>: 试用账户免费额度
        """)
        sms_layout.addWidget(info_text)

        sms_group.setLayout(sms_layout)
        notifications_row_layout.addWidget(sms_group)

        layout.addLayout(notifications_row_layout)

        # 告警历史
        history_group = QGroupBox("📜 告警历史")
        history_layout = QVBoxLayout()

        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["时间", "级别", "类型", "消息", "状态"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setMaximumHeight(200)
        history_layout.addWidget(self.history_table)

        # 历史操作按钮
        history_buttons_layout = QHBoxLayout()
        self.refresh_history_btn = QPushButton("🔄 刷新历史")
        self.clear_history_btn = QPushButton("🗑️ 清空历史")
        self.export_history_btn = QPushButton("📤 导出历史")

        history_buttons_layout.addWidget(self.refresh_history_btn)
        history_buttons_layout.addWidget(self.clear_history_btn)
        history_buttons_layout.addWidget(self.export_history_btn)
        history_buttons_layout.addStretch()

        history_layout.addLayout(history_buttons_layout)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

        # 添加监控状态面板
        status_panel = self.create_monitoring_status_panel()
        layout.addWidget(status_panel)

        # 应用样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e74c3c;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)

        # 连接信号
        self.refresh_history_btn.clicked.connect(self.manual_refresh_alert_history)
        self.clear_history_btn.clicked.connect(self.clear_alert_history)
        self.export_history_btn.clicked.connect(self.export_alert_history)
        # 🔧 移除：删除原有按钮的信号连接
        # self.add_rule_btn.clicked.connect(self.add_alert_rule)
        # self.edit_rule_btn.clicked.connect(self.edit_alert_rule)
        # self.delete_rule_btn.clicked.connect(self.delete_alert_rule)

        # 连接服务商选择变化事件
        self.email_provider.currentTextChanged.connect(self.on_email_provider_changed)
        self.sms_provider.currentTextChanged.connect(self.on_sms_provider_changed)

        # 🔧 新增：连接所有配置项的变化事件，实现实时保存
        self._connect_auto_save_signals()

        # 🔧 修改：从数据库加载配置和数据
        self.load_config_from_database()
        self.load_rules_from_database()
        self.load_alert_history()

        # 启动时检查告警历史生成状态
        self.check_alert_history_generation()

        # 🔧 新增：初始化告警服务
        self.initialize_alert_services()

    def check_alert_history_generation(self):
        """检查告警历史生成状态并提供诊断信息"""
        try:
            # 检查数据库中的告警历史记录数量
            history_list = self.db.load_alert_history(limit=1000, hours=24*7)  # 检查近7天
            db_count = len(history_list)

            # 检查内存中的告警历史
            memory_count = len(self.alert_history)

            logger.info(f"告警历史检查 - 数据库: {db_count}条, 内存: {memory_count}条")

            # 如果历史记录很少，创建一个启动告警记录
            if db_count == 0:
                self.create_startup_alert_record()
            elif db_count == 1:
                # 检查是否只有启动记录
                first_record = history_list[0]
                if "启动" in first_record.message or "系统启动" in first_record.message:
                    logger.info("检测到只有系统启动告警记录，这可能表示告警监控服务未正常工作")
                    # 在监控状态面板显示提示
                    if hasattr(self, 'monitoring_status_label'):
                        self.monitoring_status_label.setText("🟡 只有启动记录，监控可能未激活")
                        self.monitoring_status_label.setStyleSheet("color: orange;")

        except Exception as e:
            logger.error(f"检查告警历史生成状态失败: {e}")

    def create_startup_alert_record(self):
        """创建系统启动告警记录"""
        try:
            from db.models.alert_config_models import AlertHistory

            startup_history = AlertHistory(
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                level='INFO',
                category='系统启动',
                message='HIkyuu-UI 系统启动，告警监控已初始化',
                status='正常',
                metric_name='system_startup',
                current_value=1.0,
                threshold_value=1.0,
                recommendation='系统正常启动，告警监控功能已激活'
            )

            history_id = self.db.save_alert_history(startup_history)
            if history_id:
                logger.info(f"创建系统启动告警记录成功，ID: {history_id}")
                # 自动刷新告警历史显示
                self.auto_refresh_alert_history()
            else:
                logger.warning("创建系统启动告警记录失败")

        except Exception as e:
            logger.error(f"创建系统启动告警记录失败: {e}")

    def auto_refresh_alert_history(self):
        """自动刷新告警历史记录显示"""
        try:
            # 重新从数据库加载最新数据
            self.load_alert_history_from_database()
            # 刷新UI显示
            self.refresh_alert_history()
            # 更新监控状态面板
            if hasattr(self, 'refresh_monitoring_status'):
                self.refresh_monitoring_status()
            logger.debug("告警历史记录已自动刷新")
        except Exception as e:
            logger.error(f"自动刷新告警历史失败: {e}")

    def initialize_alert_services(self):
        """初始化告警引擎和热加载服务"""
        try:
            logger.info("🚀 初始化告警服务...")

            # 初始化告警规则引擎
            self.alert_engine = initialize_alert_rule_engine()
            if self.alert_engine:
                self.alert_engine.start()
                logger.info("✅ 告警规则引擎已启动")

            # 初始化热加载服务
            self.hot_loader = initialize_alert_rule_hot_loader(check_interval=3)
            if self.hot_loader:
                self.hot_loader.start()
                logger.info("✅ 告警规则热加载服务已启动")

                # 将引擎作为更新回调添加到热加载服务
                if self.alert_engine:
                    self.hot_loader.add_update_callback(self.alert_engine.reload_rules_sync)

            logger.info("🎯 告警服务初始化完成")

        except Exception as e:
            logger.error(f"❌ 初始化告警服务失败: {e}")
            import traceback
            traceback.print_exc()

    def _on_alert_triggered(self, alert_data: dict):
        """当告警触发时的处理"""
        try:
            logger.info(f"收到告警触发信号: {alert_data.get('message', '未知告警')}")

            # 自动刷新告警历史显示
            self.auto_refresh_alert_history()

            # 更新监控状态面板
            if hasattr(self, 'refresh_monitoring_status'):
                self.refresh_monitoring_status()

            logger.debug("告警触发处理完成")

        except Exception as e:
            logger.error(f"处理告警触发失败: {e}")

    def _on_rules_updated(self, rules):
        """当规则批量更新时的处理"""
        try:
            logger.info(f"规则已更新，共 {len(rules)} 条规则")
            # 可以在这里添加UI更新逻辑
        except Exception as e:
            logger.error(f"处理规则更新失败: {e}")

    def _on_rule_added(self, rule_data: dict):
        """当规则添加时的处理"""
        try:
            logger.info(f"检测到新规则添加: {rule_data.get('name', '未知规则')}")
            # 规则已通过热加载自动加载到引擎，这里只需要记录
        except Exception as e:
            logger.error(f"处理规则添加失败: {e}")

    def _on_rule_modified(self, rule_data: dict):
        """当规则修改时的处理"""
        try:
            logger.info(f"检测到规则修改: {rule_data.get('name', '未知规则')}")
            # 规则已通过热加载自动更新到引擎
        except Exception as e:
            logger.error(f"处理规则修改失败: {e}")

    def _on_rule_deleted(self, rule_id: int):
        """当规则删除时的处理"""
        try:
            logger.info(f"检测到规则删除: ID {rule_id}")
            # 规则已通过热加载自动从引擎删除
        except Exception as e:
            logger.error(f"处理规则删除失败: {e}")

    def show_rules_context_menu(self, position):
        """显示规则树的右键菜单"""
        try:
            # 获取当前选中的项目
            item = self.rules_tree.itemAt(position)

            # 创建右键菜单
            context_menu = QMenu(self)

            # 添加规则选项（总是可用）
            add_action = context_menu.addAction("➕ 添加规则")
            add_action.triggered.connect(self.add_alert_rule)

            # 如果选中了项目，添加更多选项
            if item:
                context_menu.addSeparator()

                # 编辑规则
                edit_action = context_menu.addAction("✏️ 编辑规则")
                edit_action.triggered.connect(self.edit_alert_rule)

                # 复制规则
                copy_action = context_menu.addAction("📋 复制规则")
                copy_action.triggered.connect(self.copy_alert_rule)

                context_menu.addSeparator()

                # 启用/禁用规则
                current_status = item.text(3)
                if current_status == "启用":
                    toggle_action = context_menu.addAction("⏸️ 禁用规则")
                    toggle_action.triggered.connect(self.toggle_rule_status)
                else:
                    toggle_action = context_menu.addAction("▶️ 启用规则")
                    toggle_action.triggered.connect(self.toggle_rule_status)

                context_menu.addSeparator()

                # 删除规则
                delete_action = context_menu.addAction("🗑️ 删除规则")
                delete_action.triggered.connect(self.delete_alert_rule)

            # 在鼠标位置显示菜单
            context_menu.exec_(self.rules_tree.mapToGlobal(position))

        except Exception as e:
            logger.error(f"显示右键菜单失败: {e}")

    def copy_alert_rule(self):
        """复制告警规则"""
        current_item = self.rules_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请选择要复制的规则")
            return

        try:
            from gui.dialogs.alert_rule_dialog import AlertRuleDialog

            # 获取原规则数据
            rule_id = current_item.data(0, Qt.UserRole)
            if rule_id:
                # 从数据库加载完整规则数据
                rules = self.db.load_alert_rules()
                rule_data = None
                for rule in rules:
                    if rule.id == rule_id:
                        rule_data = {
                            'name': f"{rule.name} - 副本",  # 添加"副本"后缀
                            'type': rule.rule_type,
                            'priority': rule.priority,
                            'enabled': rule.enabled,
                            'description': rule.description,
                            'tags': '',
                            'conditions': {
                                'metric_type': rule.metric_name,
                                'operator': rule.operator,
                                'threshold_value': rule.threshold_value,
                                'threshold_unit': rule.threshold_unit,
                                'duration': rule.duration,
                                'check_interval': 60,
                                'silence_period': 300,
                                'max_alerts': 10
                            },
                            'notifications': {
                                'email_notify': rule.email_notification,
                                'sms_notify': rule.sms_notification,
                                'desktop_notify': rule.desktop_notification,
                                'sound_notify': rule.sound_notification,
                                'email_recipients': '',
                                'sms_recipients': '',
                                'message_template': rule.message_template
                            }
                        }
                        break

                if rule_data:
                    dialog = AlertRuleDialog(self, rule_data)
                    dialog.rule_saved.connect(self.on_rule_saved)
                    dialog.exec_()
                else:
                    QMessageBox.warning(self, "复制失败", "无法获取规则数据")
            else:
                # 旧数据，使用简单复制
                rule_name = f"{current_item.text(0)} - 副本"
                new_rule = AlertRule(
                    name=rule_name,
                    rule_type=current_item.text(1),
                    description="复制的规则",
                    metric_name="custom_metric",
                    threshold_value=0.0
                )
                rule_id = self.db.save_alert_rule(new_rule)
                if rule_id:
                    item = QTreeWidgetItem([rule_name, current_item.text(1), current_item.text(2), "启用"])
                    item.setData(0, Qt.UserRole, rule_id)
                    self.rules_tree.addTopLevelItem(item)
                    QMessageBox.information(self, "复制成功", f"规则 '{rule_name}' 已复制")

        except Exception as e:
            logger.error(f"复制规则失败: {e}")
            QMessageBox.critical(self, "复制失败", f"复制规则失败: {e}")

    def toggle_rule_status(self):
        """切换规则启用/禁用状态"""
        current_item = self.rules_tree.currentItem()
        if not current_item:
            return

        try:
            rule_id = current_item.data(0, Qt.UserRole)
            if rule_id:
                # 从数据库获取规则
                rules = self.db.load_alert_rules()
                for rule in rules:
                    if rule.id == rule_id:
                        # 切换状态
                        rule.enabled = not rule.enabled

                        # 保存到数据库
                        if self.db.save_alert_rule(rule):
                            # 更新UI显示
                            new_status = "启用" if rule.enabled else "禁用"
                            current_item.setText(3, new_status)

                            status_text = "启用" if rule.enabled else "禁用"
                            QMessageBox.information(self, "状态更改", f"规则 '{rule.name}' 已{status_text}")
                        else:
                            QMessageBox.critical(self, "更新失败", "保存规则状态失败")
                        break
            else:
                # 旧数据，只更新UI
                current_status = current_item.text(3)
                new_status = "禁用" if current_status == "启用" else "启用"
                current_item.setText(3, new_status)
                QMessageBox.information(self, "状态更改", f"规则状态已更改为{new_status}")

        except Exception as e:
            logger.error(f"切换规则状态失败: {e}")
            QMessageBox.critical(self, "状态更改失败", f"切换规则状态失败: {e}")

    def load_config_from_database(self):
        """从数据库加载通知配置"""
        try:
            config = self.db.load_notification_config()
            if config:
                # 加载邮件配置
                self.email_enabled.setChecked(config.email_enabled)
                self.email_provider.setCurrentText(config.email_provider)
                self.sender_email.setText(config.sender_email)
                self.sender_name.setText(config.sender_name)
                self.email_api_key.setText(config.email_api_key)
                self.smtp_host.setText(config.smtp_host)
                self.smtp_port.setValue(config.smtp_port)
                self.email_address.setText(config.email_address)

                # 加载短信配置
                self.sms_enabled.setChecked(config.sms_enabled)
                self.sms_provider.setCurrentText(config.sms_provider)
                self.sms_api_key.setText(config.sms_api_key)
                self.sms_api_secret.setText(config.sms_api_secret)
                self.phone_number.setText(config.phone_number)

                logger.info("通知配置从数据库加载成功")
            else:
                logger.info("使用默认通知配置")
        except Exception as e:
            logger.error(f"从数据库加载通知配置失败: {e}")

    def load_rules_from_database(self):
        """从数据库加载告警规则"""
        try:
            self.rules_tree.clear()
            rules = self.db.load_alert_rules()

            for rule in rules:
                threshold_text = f"{rule.operator} {rule.threshold_value}{rule.threshold_unit}"
                status_text = "启用" if rule.enabled else "禁用"

                item = QTreeWidgetItem([rule.name, rule.rule_type, threshold_text, status_text])
                item.setData(0, Qt.UserRole, rule.id)  # 存储规则ID
                self.rules_tree.addTopLevelItem(item)

            logger.info(f"从数据库加载了 {len(rules)} 条告警规则")

            # 如果没有规则，加载默认规则
            if not rules:
                self._load_default_rules()

        except Exception as e:
            logger.error(f"从数据库加载告警规则失败: {e}")
            # 加载默认规则作为备用
            self._load_default_rules()

    def _load_default_rules(self):
        """加载默认告警规则到数据库"""
        default_rules = [
            AlertRule(
                name="CPU使用率过高",
                rule_type="系统资源",
                metric_name="cpu_usage",
                operator=">",
                threshold_value=80.0,
                threshold_unit="%",
                description="CPU使用率超过80%时触发告警"
            ),
            AlertRule(
                name="内存使用率过高",
                rule_type="系统资源",
                metric_name="memory_usage",
                operator=">",
                threshold_value=85.0,
                threshold_unit="%",
                description="内存使用率超过85%时触发告警"
            ),
            AlertRule(
                name="磁盘使用率过高",
                rule_type="系统资源",
                metric_name="disk_usage",
                operator=">",
                threshold_value=90.0,
                threshold_unit="%",
                description="磁盘使用率超过90%时触发告警"
            ),
            AlertRule(
                name="响应时间过长",
                rule_type="性能指标",
                metric_name="response_time",
                operator=">",
                threshold_value=3.0,
                threshold_unit="秒",
                description="响应时间超过3秒时触发告警"
            ),
            AlertRule(
                name="错误率过高",
                rule_type="业务逻辑",
                metric_name="error_rate",
                operator=">",
                threshold_value=5.0,
                threshold_unit="%",
                description="错误率超过5%时触发告警"
            )
        ]

        for rule in default_rules:
            rule_id = self.db.save_alert_rule(rule)
            if rule_id:
                threshold_text = f"{rule.operator} {rule.threshold_value}{rule.threshold_unit}"
                status_text = "启用" if rule.enabled else "禁用"

                item = QTreeWidgetItem([rule.name, rule.rule_type, threshold_text, status_text])
                item.setData(0, Qt.UserRole, rule_id)
                self.rules_tree.addTopLevelItem(item)

        logger.info("默认告警规则已加载到数据库")

    def _connect_auto_save_signals(self):
        """连接所有配置项的变化信号，实现实时保存"""
        try:
            # 邮件配置变化信号
            self.email_enabled.toggled.connect(self._auto_save_config)
            self.email_provider.currentTextChanged.connect(self._auto_save_config)
            self.sender_email.textChanged.connect(self._auto_save_config)
            self.sender_name.textChanged.connect(self._auto_save_config)
            self.email_api_key.textChanged.connect(self._auto_save_config)
            self.smtp_host.textChanged.connect(self._auto_save_config)
            self.smtp_port.valueChanged.connect(self._auto_save_config)
            self.email_address.textChanged.connect(self._auto_save_config)

            # 短信配置变化信号
            self.sms_enabled.toggled.connect(self._auto_save_config)
            self.sms_provider.currentTextChanged.connect(self._auto_save_config)
            self.sms_api_key.textChanged.connect(self._auto_save_config)
            self.sms_api_secret.textChanged.connect(self._auto_save_config)
            self.phone_number.textChanged.connect(self._auto_save_config)

            logger.info("✅ 实时保存信号连接完成")

        except Exception as e:
            logger.error(f"连接实时保存信号失败: {e}")

    def _auto_save_config(self):
        """自动保存配置到数据库"""
        try:
            # 🔧 新增：实时保存通知配置到数据库
            notification_config = NotificationConfig(
                email_enabled=self.email_enabled.isChecked(),
                email_provider=self.email_provider.currentText(),
                sender_email=self.sender_email.text(),
                sender_name=self.sender_name.text(),
                email_api_key=self.email_api_key.text(),
                smtp_host=self.smtp_host.text(),
                smtp_port=self.smtp_port.value(),
                email_address=self.email_address.text(),
                sms_enabled=self.sms_enabled.isChecked(),
                sms_provider=self.sms_provider.currentText(),
                sms_api_key=self.sms_api_key.text(),
                sms_api_secret=self.sms_api_secret.text(),
                phone_number=self.phone_number.text()
            )

            # 保存通知配置
            if self.db.save_notification_config(notification_config):
                logger.debug("✅ 配置已实时保存到数据库")
            else:
                logger.warning("⚠️ 实时保存配置失败")

        except Exception as e:
            logger.error(f"实时保存配置失败: {e}")

    def save_config(self):
        """手动保存告警配置到数据库"""
        try:
            # 🔧 修改：使用实时保存方法
            self._auto_save_config()

            # 保存告警规则（规则通过单独的添加/编辑操作保存）

            QMessageBox.information(self, "保存成功", "告警配置已保存到数据库")
            logger.info("手动保存告警配置完成")

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存告警配置失败: {e}")
            logger.error(f"保存告警配置失败: {e}")

    def reset_config(self):
        """重置配置到默认值"""
        reply = QMessageBox.question(self, "确认重置", "确定要重置所有配置到默认值吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 重置邮件通知设置
            self.email_enabled.setChecked(False)
            self.email_provider.setCurrentIndex(0)
            self.sender_email.clear()
            self.sender_name.setText("FactorWeave-Quant 系统")
            self.email_api_key.clear()
            self.smtp_host.clear()
            self.smtp_port.setValue(587)
            self.email_address.clear()

            # 重置短信通知设置
            self.sms_enabled.setChecked(False)
            self.sms_provider.setCurrentIndex(0)
            self.sms_api_key.clear()
            self.sms_api_secret.clear()
            self.phone_number.clear()

            # 重置规则
            self.rules_tree.clear()
            self._load_default_rules()

            QMessageBox.information(self, "重置完成", "配置已重置到默认值")

    def test_alerts(self):
        """增强的测试告警功能"""
        try:
            # 先检查监控服务状态
            status_check = self.check_monitoring_status()
            if status_check["status"] != "ok":
                QMessageBox.warning(self, "服务状态警告",
                                    f"监控服务状态异常：{status_check['message']}\n"
                                    f"仍将尝试生成测试告警...")

            # 生成真实的告警事件
            from core.services.alert_deduplication_service import AlertMessage, AlertLevel

            test_alert = AlertMessage(
                id="test_alert_" + datetime.now().strftime('%Y%m%d_%H%M%S'),
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                category="测试告警",
                metric_name="test_metric",
                message="这是一个系统测试告警 - 验证告警流程完整性",
                current_value=85.0,
                threshold_value=80.0
            )

            # 通过告警去重服务处理
            try:
                from core.services.alert_deduplication_service import get_alert_deduplication_service
                alert_service = get_alert_deduplication_service()
                should_send = alert_service.process_alert(test_alert)

                logger.info(f"告警去重服务处理结果: {should_send}")
            except Exception as e:
                logger.warning(f"告警去重服务处理失败: {e}")
                should_send = True  # 默认发送

                # 保存到数据库
            try:
                from db.models.alert_config_models import AlertHistory
                history = AlertHistory(
                    timestamp=test_alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    level=test_alert.level.value,
                    category=test_alert.category,
                    message=test_alert.message,
                    status='已处理',
                    metric_name=test_alert.metric_name,
                    current_value=test_alert.current_value,
                    threshold_value=test_alert.threshold_value,
                    recommendation="这是一个测试告警，无需处理"
                )

                history_id = self.db.save_alert_history(history)
                if history_id:
                    logger.info(f"测试告警已保存到数据库，ID: {history_id}")
                else:
                    logger.warning("测试告警保存到数据库失败")

            except Exception as e:
                logger.error(f"保存测试告警到数据库失败: {e}")

            # 也添加到内存中的历史记录（兼容原有逻辑）
            test_alert_dict = {
                'timestamp': test_alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'level': test_alert.level.value,
                'type': test_alert.category,
                'message': test_alert.message,
                'status': '已处理'
            }
            self.alert_history.append(test_alert_dict)

            # 自动刷新告警历史显示
            self.auto_refresh_alert_history()

            # 显示详细的测试结果
            result_message = (
                f"🎯 测试告警生成完成！\n\n"
                f"📋 告警详情：\n"
                f"  • ID: {test_alert.id}\n"
                f"  • 级别: {test_alert.level.value}\n"
                f"  • 分类: {test_alert.category}\n"
                f"  • 处理状态: {'已发送' if should_send else '已去重'}\n\n"
                f"📧 通知状态：\n"
                f"  • 邮件通知: {'已启用' if self.email_enabled.isChecked() and self.email_address.text() else '未启用'}\n"
                f"  • 短信通知: {'已启用' if self.sms_enabled.isChecked() and self.phone_number.text() else '未启用'}\n\n"
                f"💡 请检查告警历史记录确认显示是否正常。"
            )

            if self.email_enabled.isChecked() and self.email_address.text():
                result_message += f"\n📨 邮件将发送至: {self.email_address.text()}"

            QMessageBox.information(self, "测试结果", result_message)

        except Exception as e:
            logger.error(f"增强测试告警失败: {e}")
            QMessageBox.critical(self, "测试失败", f"告警测试失败: {e}")

    def check_monitoring_status(self):
        """检查监控服务状态"""
        try:
            from core.containers import get_service_container
            service_container = get_service_container()

            # 检查指标聚合服务
            try:
                # 🔧 修复：通过名称解析服务而不是字符串类型
                aggregation_service = service_container.resolve_by_name('MetricsAggregationService')
                if not aggregation_service:
                    logger.warning("指标聚合服务未找到")
                    return {"status": "error", "message": "指标聚合服务未找到"}

                # 检查服务是否有运行状态方法
                if hasattr(aggregation_service, 'is_running'):
                    if not aggregation_service.is_running():
                        logger.warning("指标聚合服务未运行")
                        return {"status": "warning", "message": "指标聚合服务未运行"}
                else:
                    logger.debug("指标聚合服务无is_running方法，假设运行正常")

            except Exception as e:
                logger.error(f"指标聚合服务检查失败: {e}")
                return {"status": "error", "message": f"指标聚合服务检查失败: {e}"}

            # 检查事件总线
            try:
                # 🔧 修复：通过名称解析服务
                event_bus = service_container.resolve_by_name('EventBus')
                if not event_bus:
                    logger.warning("事件总线未初始化")
                    return {"status": "warning", "message": "事件总线未初始化"}
            except Exception as e:
                logger.warning(f"事件总线检查失败: {e}")
                return {"status": "warning", "message": f"事件总线检查失败: {e}"}

            # 检查告警去重服务
            try:
                from core.services.alert_deduplication_service import get_alert_deduplication_service
                alert_service = get_alert_deduplication_service()
                if not alert_service:
                    logger.warning("告警去重服务未初始化")
                    return {"status": "warning", "message": "告警去重服务未初始化"}
            except Exception as e:
                logger.warning(f"告警去重服务检查失败: {e}")
                return {"status": "warning", "message": f"告警去重服务检查失败: {e}"}

            logger.info("监控服务状态检查完成，所有服务正常")
            return {"status": "ok", "message": "监控服务运行正常"}

        except Exception as e:
            logger.error(f"服务检查失败: {e}")
            return {"status": "error", "message": f"服务检查失败: {e}"}

    def create_monitoring_status_panel(self):
        """创建监控状态面板"""
        status_group = QGroupBox("🔍 监控状态")
        status_layout = QHBoxLayout()

        # 状态指示器
        self.monitoring_status_label = QLabel("检查中...")
        self.alert_count_label = QLabel("告警计数: 0")
        self.last_alert_label = QLabel("最后告警: 无")

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新状态")
        refresh_btn.clicked.connect(self.refresh_monitoring_status)
        refresh_btn.setToolTip("检查监控服务状态和告警统计信息")

        # 状态信息布局
        info_layout = QVBoxLayout()
        info_layout.addWidget(self.monitoring_status_label)
        info_layout.addWidget(self.alert_count_label)
        info_layout.addWidget(self.last_alert_label)

        status_layout.addLayout(info_layout)
        status_layout.addStretch()
        status_layout.addWidget(refresh_btn)

        status_group.setLayout(status_layout)

        # 初始状态检查
        self.refresh_monitoring_status()

        return status_group

    def refresh_monitoring_status(self):
        """刷新监控状态"""
        try:
            # 检查服务状态
            status_check = self.check_monitoring_status()

            # 更新状态显示
            if status_check["status"] == "ok":
                self.monitoring_status_label.setText("🟢 监控服务正常")
                self.monitoring_status_label.setStyleSheet("color: green;")
            elif status_check["status"] == "warning":
                self.monitoring_status_label.setText(f"🟡 {status_check['message']}")
                self.monitoring_status_label.setStyleSheet("color: orange;")
            else:
                self.monitoring_status_label.setText(f"🔴 {status_check['message']}")
                self.monitoring_status_label.setStyleSheet("color: red;")

            # 更新告警统计
            alert_count = len(self.alert_history)
            self.alert_count_label.setText(f"告警计数: {alert_count}")

            # 获取最后一个告警
            if self.alert_history:
                last_alert = self.alert_history[-1]
                last_alert_time = last_alert.get('timestamp', '未知时间')
                last_alert_level = last_alert.get('level', '未知级别')
                self.last_alert_label.setText(f"最后告警: {last_alert_time} ({last_alert_level})")
            else:
                self.last_alert_label.setText("最后告警: 无")

            # 检查告警去重服务统计
            try:
                from core.services.alert_deduplication_service import get_alert_deduplication_service
                alert_service = get_alert_deduplication_service()
                stats = alert_service.stats

                total_alerts = stats.get('total_alerts', 0)
                suppressed_alerts = stats.get('suppressed_alerts', 0)
                active_alerts = stats.get('active_alerts', 0)

                self.alert_count_label.setText(
                    f"告警统计: 总数{total_alerts} | 活跃{active_alerts} | 抑制{suppressed_alerts}"
                )

            except Exception as e:
                logger.debug(f"获取告警统计失败: {e}")

        except Exception as e:
            logger.error(f"刷新监控状态失败: {e}")
            self.monitoring_status_label.setText(f"🔴 状态检查失败")
            self.monitoring_status_label.setStyleSheet("color: red;")

    def apply_config(self):
        """应用配置到系统"""
        try:
            # 获取当前配置
            config = {
                'email_enabled': self.email_enabled.isChecked(),
                'email_provider': self.email_provider.currentText(),
                'sender_email': self.sender_email.text(),
                'sms_enabled': self.sms_enabled.isChecked(),
                'sms_provider': self.sms_provider.currentText()
            }

            # 应用告警规则到系统
            try:
                from core.containers import get_service_container

                service_container = get_service_container()
                aggregation_service = service_container.resolve_by_name('MetricsAggregationService')

                if aggregation_service:
                    # 从告警规则中提取阈值并应用
                    rules = self._get_alert_rules()

                    # 设置默认阈值
                    default_thresholds = {
                        'cpu': 80.0,
                        'memory': 85.0,
                        'disk': 90.0,
                        'operation_time': 3.0,
                        'error_rate': 0.1
                    }

                    # 从规则中提取阈值
                    for rule in rules:
                        rule_name = rule.get('name', '').lower()
                        conditions = rule.get('conditions', {})
                        threshold_value = conditions.get('threshold_value', 0)

                        if 'cpu' in rule_name and threshold_value > 0:
                            default_thresholds['cpu'] = threshold_value
                        elif ('memory' in rule_name or '内存' in rule_name) and threshold_value > 0:
                            default_thresholds['memory'] = threshold_value
                        elif ('disk' in rule_name or '磁盘' in rule_name) and threshold_value > 0:
                            default_thresholds['disk'] = threshold_value
                        elif ('response' in rule_name or '响应' in rule_name) and threshold_value > 0:
                            default_thresholds['operation_time'] = threshold_value
                        elif ('error' in rule_name or '错误' in rule_name) and threshold_value > 0:
                            default_thresholds['error_rate'] = threshold_value / 100.0  # 转换为小数

                    # 应用阈值到聚合服务
                    for metric_name, threshold in default_thresholds.items():
                        aggregation_service.set_alert_threshold(metric_name, threshold)

                    logger.info(f"告警阈值已应用: {default_thresholds}")

                # 注册告警事件处理器
                try:
                    # 🔧 修复：正确获取事件总线
                    from core.events import get_event_bus
                    event_bus = get_event_bus()

                    from core.services.alert_event_handler import register_alert_handlers
                    register_alert_handlers(event_bus)
                    logger.info("✅ 告警事件处理器已注册")

                except Exception as e:
                    logger.error(f"注册告警事件处理器失败: {e}")
                    # 备用方案：尝试从服务容器获取
                    try:
                        event_bus = service_container.resolve_by_name('EventBus')
                        if event_bus:
                            from core.services.alert_event_handler import register_alert_handlers
                            register_alert_handlers(event_bus)
                            logger.info("✅ 告警事件处理器已注册（备用方案）")
                    except Exception as e2:
                        logger.error(f"备用方案也失败: {e2}")

            except Exception as e:
                logger.warning(f"无法应用告警配置到监控服务: {e}")

            # 应用通知服务配置
            try:
                from core.services.notification_service import notification_service, NotificationConfig, NotificationProvider

                # 配置邮件服务
                if config['email_enabled'] and self.sender_email.text():
                    # 🔧 修复：正确的枚举映射
                    email_provider_map = {
                        "SMTP": NotificationProvider.SMTP,
                        "Mailgun": NotificationProvider.MAILGUN,
                        "SendGrid": NotificationProvider.SENDGRID,
                        "Brevo": NotificationProvider.BREVO,
                        "AhaSend": NotificationProvider.AHASEND
                    }
                    email_provider = email_provider_map.get(config['email_provider'])
                    if email_provider:
                        email_config = NotificationConfig(
                            provider=email_provider,
                            api_key=self.email_api_key.text(),
                            sender_email=self.sender_email.text(),
                            sender_name=self.sender_name.text(),
                            smtp_host=self.smtp_host.text(),
                            smtp_port=self.smtp_port.value()
                        )
                        notification_service.configure_email_provider(email_provider, email_config)
                        logger.info(f"✅ 邮件服务配置成功: {config['email_provider']}")
                    else:
                        logger.warning(f"⚠️ 不支持的邮件服务商: {config['email_provider']}")

                # 配置短信服务
                if config['sms_enabled'] and self.sms_api_key.text():
                    # 🔧 修复：正确的枚举映射
                    sms_provider_map = {
                        "云片": NotificationProvider.YUNPIAN,
                        "互亿无线": NotificationProvider.IHUYI,
                        "Twilio": NotificationProvider.TWILIO,
                        "YCloud": NotificationProvider.YCLOUD,
                        "SMSDove": NotificationProvider.SMSDOVE
                    }
                    sms_provider = sms_provider_map.get(config['sms_provider'])
                    if sms_provider:
                        # 设置正确的base_url
                        base_url = None
                        if sms_provider == NotificationProvider.YUNPIAN:
                            base_url = "https://sms.yunpian.com/v2/sms/single_send.json"
                        elif sms_provider == NotificationProvider.IHUYI:
                            base_url = "https://106.ihuyi.com/webservice/sms.php?method=Submit"
                        elif sms_provider == NotificationProvider.TWILIO:
                            base_url = "https://api.twilio.com"
                        elif sms_provider == NotificationProvider.YCLOUD:
                            base_url = "https://api.ycloud.com/v2/sms"
                        elif sms_provider == NotificationProvider.SMSDOVE:
                            base_url = "https://api.smsdove.com/v1/sms/send"

                        sms_config = NotificationConfig(
                            provider=sms_provider,
                            api_key=self.sms_api_key.text(),
                            api_secret=self.sms_api_secret.text(),
                            base_url=base_url
                        )
                        notification_service.configure_sms_provider(sms_provider, sms_config)
                        logger.info(f"✅ 短信服务配置成功: {config['sms_provider']}")
                    else:
                        logger.warning(f"⚠️ 不支持的短信服务商: {config['sms_provider']}")

                logger.info("通知服务配置已应用")
            except Exception as e:
                logger.warning(f"无法应用配置到通知服务: {e}")

            QMessageBox.information(self, "应用成功", "告警配置已应用到系统，阈值监控已启用")

        except Exception as e:
            QMessageBox.critical(self, "应用失败", f"应用配置失败: {e}")

    def refresh_alert_history(self):
        """刷新告警历史 - 支持手动刷新和异步加载"""
        try:
            # 如果是手动刷新，重新异步加载数据
            if hasattr(self, '_manual_refresh') and self._manual_refresh:
                self._manual_refresh = False
                self.load_alert_history()
                return

            # 更新表格显示
            self.history_table.setRowCount(len(self.alert_history))

            for row, alert in enumerate(self.alert_history):
                self.history_table.setItem(row, 0, QTableWidgetItem(alert.get('timestamp', '')))

                # 级别项目设置颜色
                level_item = QTableWidgetItem(alert.get('level', ''))
                level = alert.get('level', '').lower()
                if level in ['critical', '严重', '紧急']:
                    level_item.setBackground(QColor('#e74c3c'))
                    level_item.setForeground(QColor('#ffffff'))
                elif level in ['warning', '警告', '注意']:
                    level_item.setBackground(QColor('#f39c12'))
                    level_item.setForeground(QColor('#ffffff'))
                elif level in ['error', '错误']:
                    level_item.setBackground(QColor('#e67e22'))
                    level_item.setForeground(QColor('#ffffff'))
                elif level in ['info', '信息']:
                    level_item.setBackground(QColor('#3498db'))
                    level_item.setForeground(QColor('#ffffff'))

                self.history_table.setItem(row, 1, level_item)
                self.history_table.setItem(row, 2, QTableWidgetItem(alert.get('type', '')))
                self.history_table.setItem(row, 3, QTableWidgetItem(alert.get('message', '')))

                # 状态项目设置颜色
                status_item = QTableWidgetItem(alert.get('status', ''))
                status = alert.get('status', '').lower()
                if status in ['已解决', '已处理', 'resolved']:
                    status_item.setForeground(QColor('#27ae60'))
                elif status in ['活跃', 'active']:
                    status_item.setForeground(QColor('#e74c3c'))

                self.history_table.setItem(row, 4, status_item)

            # 自动调整列宽
            self.history_table.resizeColumnsToContents()

        except Exception as e:
            logger.error(f"刷新告警历史失败: {e}")

    def manual_refresh_alert_history(self):
        """手动刷新告警历史"""
        self._manual_refresh = True
        self.refresh_alert_history()

    def clear_alert_history(self):
        """清空告警历史"""
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有告警历史吗？\n这将从数据库中删除所有历史记录。",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # 🔧 修改：从数据库清空历史
                if self.db.clear_alert_history():
                    # 清空UI显示的历史
                    self.alert_history.clear()
                    self.history_table.setRowCount(0)
                    QMessageBox.information(self, "清空完成", "告警历史已从数据库清空")
                else:
                    QMessageBox.critical(self, "清空失败", "从数据库清空告警历史失败")

            except Exception as e:
                logger.error(f"清空告警历史失败: {e}")
                QMessageBox.critical(self, "清空失败", f"清空告警历史失败: {e}")

    def export_alert_history(self):
        """导出告警历史"""
        try:
            if not self.alert_history:
                QMessageBox.information(self, "导出提示", "没有告警历史可导出")
                return

            filename, _ = QFileDialog.getSaveFileName(
                self, "导出告警历史",
                f"alert_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV files (*.csv);;All files (*.*)"
            )

            if filename:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['时间', '级别', '类型', '消息', '状态'])
                    for alert in self.alert_history:
                        writer.writerow([
                            alert.get('timestamp', ''),
                            alert.get('level', ''),
                            alert.get('type', ''),
                            alert.get('message', ''),
                            alert.get('status', '')
                        ])

                QMessageBox.information(self, "导出成功", f"告警历史已导出到: {filename}")

        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出告警历史失败: {e}")

    def add_alert_rule(self):
        """添加告警规则"""
        try:
            from gui.dialogs.alert_rule_dialog import AlertRuleDialog
            dialog = AlertRuleDialog(self)
            dialog.rule_saved.connect(self.on_rule_saved)
            dialog.exec_()
        except Exception as e:
            logger.error(f"打开添加规则对话框失败: {e}")
            # 降级到简单输入框
            rule_name, ok = QInputDialog.getText(self, "添加规则", "请输入规则名称:")
            if ok and rule_name:
                # 🔧 修改：保存到数据库
                new_rule = AlertRule(
                    name=rule_name,
                    rule_type="自定义",
                    description="通过简单输入创建的规则",
                    metric_name="custom_metric",
                    threshold_value=0.0
                )
                rule_id = self.db.save_alert_rule(new_rule)
                if rule_id:
                    item = QTreeWidgetItem([rule_name, "自定义", "待配置", "启用"])
                    item.setData(0, Qt.UserRole, rule_id)
                    self.rules_tree.addTopLevelItem(item)

    def edit_alert_rule(self):
        """编辑告警规则"""
        current_item = self.rules_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请选择要编辑的规则")
            return

        try:
            from gui.dialogs.alert_rule_dialog import AlertRuleDialog

            # 🔧 修改：从数据库获取完整规则数据
            rule_id = current_item.data(0, Qt.UserRole)
            if rule_id:
                # 从数据库加载完整规则数据
                rules = self.db.load_alert_rules()
                rule_data = None
                for rule in rules:
                    if rule.id == rule_id:
                        rule_data = {
                            'id': rule.id,
                            'name': rule.name,
                            'type': rule.rule_type,
                            'priority': rule.priority,
                            'enabled': rule.enabled,
                            'description': rule.description,
                            'tags': '',  # 数据库中暂无此字段，使用默认值
                            'conditions': {
                                'metric_type': rule.metric_name,  # 🔧 修复：字段名映射
                                'operator': rule.operator,
                                'threshold_value': rule.threshold_value,
                                'threshold_unit': rule.threshold_unit,
                                'duration': rule.duration,
                                'check_interval': 60,  # 数据库中暂无此字段，使用默认值
                                'silence_period': 300,  # 数据库中暂无此字段，使用默认值
                                'max_alerts': 10  # 数据库中暂无此字段，使用默认值
                            },
                            'notifications': {
                                'email_notify': rule.email_notification,  # 🔧 修复：字段名映射
                                'sms_notify': rule.sms_notification,  # 🔧 修复：字段名映射
                                'desktop_notify': rule.desktop_notification,  # 🔧 修复：字段名映射
                                'sound_notify': rule.sound_notification,  # 🔧 修复：字段名映射
                                'email_recipients': '',  # 数据库中暂无此字段，使用默认值
                                'sms_recipients': '',  # 数据库中暂无此字段，使用默认值
                                'message_template': rule.message_template
                            }
                        }
                        break

                if not rule_data:
                    # 如果数据库中没有找到，使用UI数据作为备用
                    rule_data = {
                        'name': current_item.text(0),
                        'type': current_item.text(1),
                        'threshold': current_item.text(2),
                        'enabled': current_item.text(3) == "启用"
                    }
            else:
                # 旧数据，没有ID
                rule_data = {
                    'name': current_item.text(0),
                    'type': current_item.text(1),
                    'threshold': current_item.text(2),
                    'enabled': current_item.text(3) == "启用"
                }

            dialog = AlertRuleDialog(self, rule_data)
            dialog.rule_saved.connect(self.on_rule_updated)
            dialog.exec_()
        except Exception as e:
            logger.error(f"打开编辑规则对话框失败: {e}")
            # 降级到简单输入框
            rule_name, ok = QInputDialog.getText(self, "编辑规则", "请输入新的规则名称:",
                                                 text=current_item.text(0))
            if ok and rule_name:
                current_item.setText(0, rule_name)

    def delete_alert_rule(self):
        """删除告警规则"""
        current_item = self.rules_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请选择要删除的规则")
            return

        reply = QMessageBox.question(self, "确认删除", f"确定要删除规则 '{current_item.text(0)}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 🔧 修改：从数据库删除规则
            rule_id = current_item.data(0, Qt.UserRole)
            if rule_id:
                if self.db.delete_alert_rule(rule_id):
                    self.rules_tree.takeTopLevelItem(self.rules_tree.indexOfTopLevelItem(current_item))
                    QMessageBox.information(self, "删除成功", "告警规则已从数据库删除")
                else:
                    QMessageBox.critical(self, "删除失败", "从数据库删除规则失败")
            else:
                # 旧数据，只从UI删除
                self.rules_tree.takeTopLevelItem(self.rules_tree.indexOfTopLevelItem(current_item))
                QMessageBox.information(self, "删除成功", "告警规则已删除")

    def on_rule_saved(self, rule_data: dict):
        """新规则保存处理"""
        try:
            # 🔧 修改：保存到数据库
            conditions = rule_data.get('conditions', {})
            notifications = rule_data.get('notifications', {})

            new_rule = AlertRule(
                name=rule_data.get('name', '未命名规则'),
                rule_type=rule_data.get('type', '自定义'),
                priority=rule_data.get('priority', '中等'),
                enabled=rule_data.get('enabled', True),
                description=rule_data.get('description', ''),
                metric_name=conditions.get('metric_type', ''),  # 🔧 修复：正确的字段名
                operator=conditions.get('operator', '>'),
                threshold_value=float(conditions.get('threshold_value', 0.0)),  # 🔧 确保类型正确
                threshold_unit=conditions.get('threshold_unit', '%'),
                duration=conditions.get('duration', 60),
                email_notification=notifications.get('email_notify', True),  # 🔧 修复：正确的字段名
                sms_notification=notifications.get('sms_notify', False),  # 🔧 修复：正确的字段名
                desktop_notification=notifications.get('desktop_notify', True),  # 🔧 修复：正确的字段名
                sound_notification=notifications.get('sound_notify', True),  # 🔧 修复：正确的字段名
                message_template=notifications.get('message_template', '')
            )

            rule_id = self.db.save_alert_rule(new_rule)
            if rule_id:
                # 🔧 修复：从数据库实际保存的值构建显示文本
                threshold_text = f"{new_rule.operator} {new_rule.threshold_value}{new_rule.threshold_unit}"

                item = QTreeWidgetItem([
                    new_rule.name,
                    new_rule.rule_type,
                    threshold_text,
                    "启用" if new_rule.enabled else "禁用"
                ])
                item.setData(0, Qt.UserRole, rule_id)
                self.rules_tree.addTopLevelItem(item)

                # 自动刷新告警历史显示
                self.auto_refresh_alert_history()

                QMessageBox.information(self, "添加成功", f"告警规则 '{new_rule.name}' 已添加到数据库")
            else:
                QMessageBox.critical(self, "保存失败", "保存规则到数据库失败")
        except Exception as e:
            logger.error(f"保存新规则失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存新规则失败: {e}")

    def on_rule_updated(self, rule_data: dict):
        """规则更新处理"""
        try:
            current_item = self.rules_tree.currentItem()
            if current_item:
                # 🔧 修复：将更新的数据保存到数据库
                rule_id = current_item.data(0, Qt.UserRole)
                if rule_id:
                    # 从数据库加载现有规则
                    rules = self.db.load_alert_rules()
                    existing_rule = None
                    for rule in rules:
                        if rule.id == rule_id:
                            existing_rule = rule
                            break

                    if existing_rule:
                        # 更新规则数据
                        conditions = rule_data.get('conditions', {})
                        notifications = rule_data.get('notifications', {})

                        existing_rule.name = rule_data.get('name', existing_rule.name)
                        existing_rule.rule_type = rule_data.get('type', existing_rule.rule_type)
                        existing_rule.priority = rule_data.get('priority', existing_rule.priority)
                        existing_rule.enabled = rule_data.get('enabled', existing_rule.enabled)
                        existing_rule.description = rule_data.get('description', existing_rule.description)

                        # 更新条件
                        existing_rule.metric_name = conditions.get('metric_type', existing_rule.metric_name)  # 🔧 修复：字段名映射
                        existing_rule.operator = conditions.get('operator', existing_rule.operator)
                        existing_rule.threshold_value = float(conditions.get('threshold_value', existing_rule.threshold_value))  # 🔧 确保类型正确
                        existing_rule.threshold_unit = conditions.get('threshold_unit', existing_rule.threshold_unit)
                        existing_rule.duration = conditions.get('duration', existing_rule.duration)

                        # 更新通知设置
                        existing_rule.email_notification = notifications.get('email_notify', existing_rule.email_notification)  # 🔧 修复：字段名映射
                        existing_rule.sms_notification = notifications.get('sms_notify', existing_rule.sms_notification)  # 🔧 修复：字段名映射
                        existing_rule.desktop_notification = notifications.get('desktop_notify', existing_rule.desktop_notification)  # 🔧 修复：字段名映射
                        existing_rule.sound_notification = notifications.get('sound_notify', existing_rule.sound_notification)  # 🔧 修复：字段名映射
                        existing_rule.message_template = notifications.get('message_template', existing_rule.message_template)

                        # 保存到数据库
                        updated_rule_id = self.db.save_alert_rule(existing_rule)
                        if updated_rule_id:
                            logger.info(f"✅ 告警规则已更新到数据库，ID: {updated_rule_id}")

                            # 🔧 修复：更新UI显示，使用数据库实际保存的值
                            threshold_text = f"{existing_rule.operator} {existing_rule.threshold_value}{existing_rule.threshold_unit}"
                            current_item.setText(0, existing_rule.name)
                            current_item.setText(1, existing_rule.rule_type)
                            current_item.setText(2, threshold_text)
                            current_item.setText(3, "启用" if existing_rule.enabled else "禁用")

                            # 自动刷新告警历史显示
                            self.auto_refresh_alert_history()

                            QMessageBox.information(self, "更新成功", f"告警规则 '{existing_rule.name}' 已更新并保存到数据库")
                        else:
                            logger.error("❌ 保存更新的规则到数据库失败")
                            QMessageBox.critical(self, "更新失败", "保存更新的规则到数据库失败")
                    else:
                        logger.error(f"❌ 未找到ID为 {rule_id} 的规则")
                        QMessageBox.critical(self, "更新失败", f"未找到ID为 {rule_id} 的规则")
                else:
                    # 旧数据，没有ID，只更新UI
                    conditions = rule_data.get('conditions', {})
                    threshold_text = f"{conditions.get('threshold_value', 0)}{conditions.get('threshold_unit', '%')}"

                    current_item.setText(0, rule_data.get('name', '未命名规则'))
                    current_item.setText(1, rule_data.get('type', '自定义'))
                    current_item.setText(2, threshold_text)
                    current_item.setText(3, "启用" if rule_data.get('enabled', True) else "禁用")

                    QMessageBox.information(self, "更新成功", f"告警规则 '{rule_data.get('name')}' 已更新（仅UI显示）")

        except Exception as e:
            logger.error(f"更新规则失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            QMessageBox.critical(self, "更新失败", f"更新规则失败: {e}")

    def load_alert_history(self):
        """加载告警历史"""
        # 🔧 修改：直接从数据库加载，不再使用异步工作线程
        self.load_alert_history_from_database()

    @pyqtSlot(list)
    def on_alert_history_loaded(self, history_data: list):
        """告警历史加载完成回调"""
        try:
            self.alert_history.clear()
            self.alert_history.extend(history_data)
            self.refresh_alert_history()
            logger.info(f"成功加载 {len(history_data)} 条告警历史记录")
        except Exception as e:
            logger.error(f"处理告警历史数据失败: {e}")

    @pyqtSlot(str)
    def on_alert_history_error(self, error_msg: str):
        """告警历史加载错误回调"""
        logger.error(f"加载告警历史失败: {error_msg}")
        # 显示空的历史记录
        self.alert_history.clear()
        self.refresh_alert_history()

    def load_alert_history_from_database(self):
        """从数据库加载告警历史"""
        try:
            history_list = self.db.load_alert_history(limit=100, hours=24)

            # 转换为UI显示格式
            self.alert_history = []
            for history in history_list:
                history_item = {
                    'timestamp': history.timestamp,
                    'level': history.level,
                    'type': history.category,
                    'message': history.message,
                    'status': history.status
                }
                self.alert_history.append(history_item)

            self.refresh_alert_history()
            logger.info(f"从数据库加载了 {len(history_list)} 条告警历史记录")

        except Exception as e:
            logger.error(f"从数据库加载告警历史失败: {e}")
            self.alert_history = []
            self.refresh_alert_history()

    def _get_alert_rules(self):
        """获取当前的告警规则"""
        rules = []
        for i in range(self.rules_tree.topLevelItemCount()):
            item = self.rules_tree.topLevelItem(i)
            rule = {
                'name': item.text(0),
                'type': item.text(1),
                'threshold': item.text(2),
                'status': item.text(3)
            }
            rules.append(rule)
        return rules

    def test_email_config(self):
        """异步测试邮件配置"""
        try:
            if not self.email_enabled.isChecked():
                QMessageBox.information(self, "提示", "请先启用邮件通知")
                return

            if not self.email_address.text():
                QMessageBox.warning(self, "警告", "请输入收件人邮箱地址")
                return

            if not self.sender_email.text().strip():
                QMessageBox.warning(self, "警告", "请输入发送邮箱地址")
                return

            # 🔧 新增：导入异步工作线程
            from gui.widgets.performance.workers.async_workers import EmailTestWorker

            # 禁用测试按钮，防止重复点击
            self.test_email_btn.setEnabled(False)
            self.test_email_btn.setText("📤 发送中...")

            # 准备配置数据
            config_data = {
                'provider': self.email_provider.currentText(),
                'api_key': self.email_api_key.text(),
                'sender_email': self.sender_email.text(),
                'sender_name': self.sender_name.text(),
                'smtp_host': self.smtp_host.text(),
                'smtp_port': self.smtp_port.value(),
                'recipient': self.email_address.text().split(',')[0].strip()
            }

            # 创建异步工作线程
            worker = EmailTestWorker(config_data)
            worker.signals.success.connect(self._on_email_test_success)
            worker.signals.error.connect(self._on_email_test_error)
            worker.signals.finished.connect(self._on_email_test_finished)

            # 启动异步任务
            QThreadPool.globalInstance().start(worker)
            logger.info("🚀 启动异步邮件测试任务")

        except Exception as e:
            self._on_email_test_error(f"启动邮件测试失败: {e}")
            logger.error(f"启动邮件测试失败: {e}")

    @pyqtSlot(str)
    def _on_email_test_success(self, message):
        """邮件测试成功回调"""
        QMessageBox.information(self, "测试成功", message)
        logger.info("✅ 邮件测试成功")

    @pyqtSlot(str)
    def _on_email_test_error(self, error_message):
        """邮件测试失败回调"""
        QMessageBox.warning(self, "测试失败", error_message)
        logger.error(f"❌ 邮件测试失败: {error_message}")

    @pyqtSlot()
    def _on_email_test_finished(self):
        """邮件测试完成回调"""
        self.test_email_btn.setEnabled(True)
        self.test_email_btn.setText("📧 测试邮件")

    def test_sms_config(self):
        """异步测试短信配置"""
        try:
            if not self.sms_enabled.isChecked():
                QMessageBox.information(self, "提示", "请先启用短信通知")
                return

            if not self.phone_number.text():
                QMessageBox.warning(self, "警告", "请输入收件人手机号码")
                return

            if not self.sms_api_key.text().strip():
                QMessageBox.warning(self, "警告", "请输入短信API密钥")
                return

            # 🔧 新增：导入异步工作线程
            from gui.widgets.performance.workers.async_workers import SMSTestWorker

            # 禁用测试按钮，防止重复点击
            self.test_sms_btn.setEnabled(False)
            self.test_sms_btn.setText("📱 发送中...")

            # 准备配置数据
            config_data = {
                'provider': self.sms_provider.currentText(),
                'api_key': self.sms_api_key.text(),
                'api_secret': self.sms_api_secret.text(),
                'recipient': self.phone_number.text().split(',')[0].strip()
            }

            # 创建异步工作线程
            worker = SMSTestWorker(config_data)
            worker.signals.success.connect(self._on_sms_test_success)
            worker.signals.error.connect(self._on_sms_test_error)
            worker.signals.finished.connect(self._on_sms_test_finished)

            # 启动异步任务
            QThreadPool.globalInstance().start(worker)
            logger.info("🚀 启动异步短信测试任务")

        except Exception as e:
            self._on_sms_test_error(f"启动短信测试失败: {e}")
            logger.error(f"启动短信测试失败: {e}")

    @pyqtSlot(str)
    def _on_sms_test_success(self, message):
        """短信测试成功回调"""
        QMessageBox.information(self, "测试成功", message)
        logger.info("✅ 短信测试成功")

    @pyqtSlot(str)
    def _on_sms_test_error(self, error_message):
        """短信测试失败回调"""
        QMessageBox.warning(self, "测试失败", error_message)
        logger.error(f"❌ 短信测试失败: {error_message}")

    @pyqtSlot()
    def _on_sms_test_finished(self):
        """短信测试完成回调"""
        self.test_sms_btn.setEnabled(True)
        self.test_sms_btn.setText("📱 测试短信")

    def on_email_provider_changed(self, provider_name):
        """邮件服务商选择变化"""
        try:
            # 根据服务商显示/隐藏相关配置
            is_smtp = provider_name == "SMTP"

            # SMTP配置只在选择SMTP时显示
            self.smtp_host.setVisible(is_smtp)
            self.smtp_port.setVisible(is_smtp)

            # 设置默认值
            if provider_name == "SMTP":
                self.smtp_host.setPlaceholderText("如: smtp.qq.com")
                self.email_api_key.setPlaceholderText("邮箱密码或授权码")
            elif provider_name == "Mailgun":
                self.email_api_key.setPlaceholderText("Mailgun API Key")
                self.sender_email.setPlaceholderText("noreply@sandbox-xxx.mailgun.org")
            elif provider_name == "SendGrid":
                self.email_api_key.setPlaceholderText("SendGrid API Key")
            elif provider_name == "Brevo":
                self.email_api_key.setPlaceholderText("Brevo API Key")
            elif provider_name == "AhaSend":
                self.email_api_key.setPlaceholderText("AhaSend API Key")

        except Exception as e:
            logger.error(f"邮件服务商选择变化处理失败: {e}")

    def on_sms_provider_changed(self, provider_name):
        """短信服务商选择变化"""
        try:
            # 根据服务商设置提示文本
            if provider_name == "云片":
                self.sms_api_key.setPlaceholderText("云片 API Key")
                self.sms_api_secret.setPlaceholderText("不需要")
            elif provider_name == "互亿无线":
                self.sms_api_key.setPlaceholderText("互亿无线账号")
                self.sms_api_secret.setPlaceholderText("互亿无线密码")
            elif provider_name == "Twilio":
                self.sms_api_key.setPlaceholderText("Twilio Account SID")
                self.sms_api_secret.setPlaceholderText("Twilio Auth Token")
            elif provider_name == "YCloud":
                self.sms_api_key.setPlaceholderText("YCloud API Key")
                self.sms_api_secret.setPlaceholderText("不需要")
            elif provider_name == "SMSDove":
                self.sms_api_key.setPlaceholderText("SMSDove API Key")
                self.sms_api_secret.setPlaceholderText("设备ID")

        except Exception as e:
            logger.error(f"短信服务商选择变化处理失败: {e}")
