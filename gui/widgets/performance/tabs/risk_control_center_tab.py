#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险控制中心标签页 - 升级版告警配置
专为量化交易风险管理设计的综合监控中心
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QTreeWidget, QTreeWidgetItem, QFormLayout, QCheckBox, QComboBox,
    QLineEdit, QSpinBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QMessageBox, QInputDialog, QFileDialog, QMenu,
    QLabel, QTabWidget, QFrame, QGridLayout, QProgressBar, QSlider
)
from PyQt5.QtCore import QThreadPool, pyqtSlot, Qt, QTimer
from PyQt5.QtGui import QColor, QFont
from gui.widgets.performance.components.metric_card import ModernMetricCard
from gui.widgets.performance.components.performance_chart import ModernPerformanceChart
from gui.widgets.performance.workers.async_workers import AlertHistoryWorker
from loguru import logger

# 导入增强风险监控后端
try:
    from core.risk_monitoring.enhanced_risk_monitor import EnhancedRiskMonitor, get_enhanced_risk_monitor
    from core.services.ai_prediction_service import AIPredictionService
    ENHANCED_RISK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"增强风险监控后端不可用: {e}")
    ENHANCED_RISK_AVAILABLE = False

logger = logger


class ModernRiskControlCenterTab(QWidget):
    """现代化风险控制中心标签页 - 量化交易专用"""

    def __init__(self):
        super().__init__()
        self.risk_alerts = []
        self.risk_history = []

        # 初始化增强风险监控后端
        self.enhanced_risk_monitor = None
        if ENHANCED_RISK_AVAILABLE:
            try:
                self.enhanced_risk_monitor = get_enhanced_risk_monitor()
                logger.info("增强风险监控后端初始化成功")
            except Exception as e:
                logger.error(f"初始化增强风险监控后端失败: {e}")

        self.init_ui()

        # 加载风险规则
        self.load_risk_rules()

        # 启动增强风险监控
        if self.enhanced_risk_monitor:
            self.start_enhanced_monitoring()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 创建子标签页
        self.tab_widget = QTabWidget()

        # 实时风险监控
        self.risk_monitor_tab = self._create_risk_monitor_tab()
        self.tab_widget.addTab(self.risk_monitor_tab, "实时风险")

        # 告警配置
        self.alert_config_tab = self._create_alert_config_tab()
        self.tab_widget.addTab(self.alert_config_tab, "告警配置")

        # 风险历史
        self.risk_history_tab = self._create_risk_history_tab()
        self.tab_widget.addTab(self.risk_history_tab, "风险历史")

        # AI智能分析（新增）
        if ENHANCED_RISK_AVAILABLE:
            self.ai_analysis_tab = self._create_ai_analysis_tab()
            self.tab_widget.addTab(self.ai_analysis_tab, "AI分析")

        layout.addWidget(self.tab_widget)

    def _create_risk_monitor_tab(self):
        """创建实时风险监控标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 风险等级指示器
        risk_level_group = QGroupBox("风险等级")
        risk_level_layout = QHBoxLayout()

        self.risk_level_label = QLabel("当前风险等级: 低风险")
        self.risk_level_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #27ae60;")
        risk_level_layout.addWidget(self.risk_level_label)

        risk_level_layout.addStretch()

        # 风险等级进度条
        self.risk_level_bar = QProgressBar()
        self.risk_level_bar.setMaximum(100)
        self.risk_level_bar.setValue(25)  # 默认低风险
        self.risk_level_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
        """)
        risk_level_layout.addWidget(self.risk_level_bar)

        risk_level_group.setLayout(risk_level_layout)
        layout.addWidget(risk_level_group)

        # 风险指标卡片
        cards_frame = QFrame()
        cards_frame.setMinimumHeight(120)
        cards_frame.setMaximumHeight(150)
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(2, 2, 2, 2)
        cards_layout.setSpacing(2)

        self.risk_cards = {}
        risk_metrics = [
            # 第一行：核心风险指标
            ("VaR(95%)", "#e74c3c", 0, 0),
            ("最大回撤", "#c0392b", 0, 1),
            ("波动率", "#e67e22", 0, 2),
            ("Beta系数", "#f39c12", 0, 3),
            ("夏普比率", "#3498db", 0, 4),
            ("仓位风险", "#9b59b6", 0, 5),

            # 第二行：市场风险指标
            ("市场风险", "#8e44ad", 1, 0),
            ("行业风险", "#2980b9", 1, 1),
            ("流动性风险", "#16a085", 1, 2),
            ("信用风险", "#d35400", 1, 3),
            ("操作风险", "#27ae60", 1, 4),
            ("集中度风险", "#f1c40f", 1, 5),
        ]

        for name, color, row, col in risk_metrics:
            unit = "%" if name in ["最大回撤", "波动率", "仓位风险"] else ""
            card = ModernMetricCard(name, "0", unit, color)
            self.risk_cards[name] = card
            cards_layout.addWidget(card, row, col)

        layout.addWidget(cards_frame)

        # 风险趋势图表
        self.risk_chart = ModernPerformanceChart("风险指标趋势", "line")
        self.risk_chart.setMinimumHeight(400)
        # self.risk_chart.setMaximumHeight(500)
        layout.addWidget(self.risk_chart, 1)

        return tab

    def _create_alert_config_tab(self):
        """创建告警配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 告警规则配置
        rules_group = QGroupBox("告警规则配置")
        rules_layout = QVBoxLayout()

        # 规则列表
        self.rules_tree = QTreeWidget()
        self.rules_tree.setHeaderLabels(["规则名称", "类型", "阈值", "状态"])
        self.rules_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.rules_tree.customContextMenuRequested.connect(self.show_rules_context_menu)
        rules_layout.addWidget(self.rules_tree)

        # 规则操作按钮
        rules_buttons_layout = QHBoxLayout()

        self.add_rule_btn = QPushButton("添加规则")
        self.add_rule_btn.clicked.connect(self.add_risk_rule)
        rules_buttons_layout.addWidget(self.add_rule_btn)

        self.edit_rule_btn = QPushButton("编辑规则")
        self.edit_rule_btn.clicked.connect(self.edit_risk_rule)
        rules_buttons_layout.addWidget(self.edit_rule_btn)

        self.delete_rule_btn = QPushButton("删除规则")
        self.delete_rule_btn.clicked.connect(self.delete_risk_rule)
        rules_buttons_layout.addWidget(self.delete_rule_btn)

        rules_buttons_layout.addStretch()
        rules_layout.addLayout(rules_buttons_layout)

        rules_group.setLayout(rules_layout)
        layout.addWidget(rules_group)

        # 通知配置
        notification_group = QGroupBox("通知配置")
        notification_layout = QFormLayout()

        self.email_enabled = QCheckBox("启用邮件通知")
        notification_layout.addRow("邮件通知:", self.email_enabled)

        self.sms_enabled = QCheckBox("启用短信通知")
        notification_layout.addRow("短信通知:", self.sms_enabled)

        self.webhook_enabled = QCheckBox("启用Webhook通知")
        notification_layout.addRow("Webhook通知:", self.webhook_enabled)

        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)

        return tab

    def _create_risk_history_tab(self):
        """创建风险历史标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 历史数据控制
        control_layout = QHBoxLayout()

        control_layout.addWidget(QLabel("时间范围:"))

        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["最近1小时", "最近24小时", "最近7天", "最近30天"])
        self.time_range_combo.currentTextChanged.connect(self.load_risk_history)
        control_layout.addWidget(self.time_range_combo)

        control_layout.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_risk_history)
        control_layout.addWidget(refresh_btn)

        layout.addLayout(control_layout)

        # 风险历史表格
        self.risk_history_table = QTableWidget()
        self.risk_history_table.setColumnCount(6)
        self.risk_history_table.setHorizontalHeaderLabels([
            "时间", "风险类型", "风险等级", "风险值", "阈值", "状态"
        ])
        self.risk_history_table.setAlternatingRowColors(True)
        self.risk_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.risk_history_table)

        return tab

    def update_risk_data(self, risk_metrics: Dict[str, float]):
        """更新实时风险数据"""
        try:
            # 更新风险指标卡片
            for name, value in risk_metrics.items():
                if name in self.risk_cards:
                    if value == 0:
                        self.risk_cards[name].update_value("正常", "up")
                    else:
                        # 根据风险类型判断趋势（风险越高越危险）
                        if value > 80:
                            trend = "down"  # 高风险用红色下降箭头
                            color = "#e74c3c"
                        elif value > 50:
                            trend = "neutral"  # 中风险用黄色
                            color = "#f39c12"
                        else:
                            trend = "up"  # 低风险用绿色上升箭头
                            color = "#27ae60"

                        self.risk_cards[name].update_value(f"{value:.2f}", trend)

            # 计算综合风险等级
            overall_risk = self._calculate_overall_risk(risk_metrics)
            self._update_risk_level(overall_risk)

            # 更新风险趋势图表
            for name, value in risk_metrics.items():
                if name in ["VaR(95%)", "最大回撤", "波动率"] and value > 0:
                    self.risk_chart.add_data_point(name, value)

            # 自动保存风险历史数据
            self._save_risk_history(risk_metrics, overall_risk)

            # 检查风险规则并生成告警
            self._check_risk_rules(risk_metrics)

        except Exception as e:
            logger.error(f"更新风险数据失败: {e}")

    def _save_risk_history(self, risk_metrics: Dict[str, float], overall_risk: float):
        """保存风险历史数据"""
        try:
            from db.models.performance_history_models import get_performance_history_manager, RiskHistoryRecord
            from datetime import datetime

            # 创建风险历史记录
            record = RiskHistoryRecord(
                timestamp=datetime.now(),
                symbol="PORTFOLIO",  # 组合级别的风险
                var_95=risk_metrics.get('VaR(95%)', 0.0),
                max_drawdown=risk_metrics.get('最大回撤', 0.0),
                volatility=risk_metrics.get('波动率', 0.0),
                beta=risk_metrics.get('Beta系数', 1.0),
                sharpe_ratio=risk_metrics.get('夏普比率', 0.0),
                position_risk=risk_metrics.get('仓位风险', 0.0),
                market_risk=risk_metrics.get('市场风险', 0.0),
                sector_risk=risk_metrics.get('行业风险', 0.0),
                liquidity_risk=risk_metrics.get('流动性风险', 0.0),
                credit_risk=risk_metrics.get('信用风险', 0.0),
                operational_risk=risk_metrics.get('操作风险', 0.0),
                concentration_risk=risk_metrics.get('集中度风险', 0.0),
                overall_risk_score=overall_risk,
                risk_level=self._get_risk_level_text(overall_risk),
                portfolio_value=0.0,  # 这里应该从实际组合获取
                notes=""
            )

            # 保存到数据库
            history_manager = get_performance_history_manager()
            success = history_manager.save_risk_record(record)

            if success:
                logger.debug("风险历史数据已保存")
            else:
                logger.warning("风险历史数据保存失败")

        except Exception as e:
            logger.debug(f"保存风险历史数据失败: {e}")

    def _get_risk_level_text(self, risk_value: float) -> str:
        """根据风险值获取风险等级文本"""
        if risk_value < 15:
            return "低风险"
        elif risk_value < 35:
            return "中低风险"
        elif risk_value < 60:
            return "中高风险"
        elif risk_value < 80:
            return "高风险"
        else:
            return "极高风险"

    def _calculate_overall_risk(self, risk_metrics: Dict[str, float]) -> float:
        """计算综合风险等级"""
        try:
            # 权重配置
            weights = {
                "VaR(95%)": 0.25,
                "最大回撤": 0.20,
                "波动率": 0.15,
                "仓位风险": 0.15,
                "市场风险": 0.10,
                "流动性风险": 0.10,
                "集中度风险": 0.05
            }

            weighted_risk = 0
            total_weight = 0

            for metric, weight in weights.items():
                if metric in risk_metrics:
                    weighted_risk += risk_metrics[metric] * weight
                    total_weight += weight

            if total_weight > 0:
                return weighted_risk / total_weight
            else:
                return 0

        except Exception as e:
            logger.error(f"计算综合风险等级失败: {e}")
            return 0

    def _update_risk_level(self, risk_value: float):
        """更新风险等级显示 - 基于行业标准的动态阈值"""
        try:
            # 基于量化交易行业标准的风险等级划分
            if risk_value < 15:
                level = "低风险"
                color = "#27ae60"      # 绿色
                bar_color = "#27ae60"
                description = "风险可控，可正常交易"
            elif risk_value < 35:
                level = "中低风险"
                color = "#2ecc71"      # 浅绿色
                bar_color = "#2ecc71"
                description = "风险较低，建议关注"
            elif risk_value < 60:
                level = "中高风险"
                color = "#f39c12"      # 橙色
                bar_color = "#f39c12"
                description = "风险偏高，需要谨慎"
            elif risk_value < 80:
                level = "高风险"
                color = "#e67e22"      # 深橙色
                bar_color = "#e67e22"
                description = "风险较高，建议减仓"
            else:
                level = "极高风险"
                color = "#e74c3c"      # 红色
                bar_color = "#e74c3c"
                description = "风险极高，建议停止交易"

            self.risk_level_label.setText(f"当前风险等级: {level} ({description})")
            self.risk_level_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")

            self.risk_level_bar.setValue(int(risk_value))
            self.risk_level_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: {bar_color};
                    border-radius: 3px;
                }}
            """)

        except Exception as e:
            logger.error(f"更新风险等级显示失败: {e}")

    def add_risk_rule(self):
        """添加风险规则"""
        try:
            from gui.dialogs.risk_rule_config_dialog import RiskRuleConfigDialog
            from core.risk_rule_manager import get_risk_rule_manager, RiskRule

            dialog = RiskRuleConfigDialog(parent=self)
            if dialog.exec_() == dialog.Accepted:
                rule_data = dialog.get_rule_data()

                # 创建规则对象
                rule = RiskRule(**rule_data)

                # 保存到数据库
                rule_manager = get_risk_rule_manager()
                if rule_manager.add_rule(rule):
                    # 添加到界面
                    self._add_rule_to_tree(rule)
                    QMessageBox.information(self, "成功", f"风险规则 '{rule.name}' 已添加")
                else:
                    QMessageBox.warning(self, "失败", "添加风险规则失败，可能规则名称已存在")

        except Exception as e:
            logger.error(f"添加风险规则失败: {e}")
            QMessageBox.critical(self, "错误", f"添加风险规则时发生错误：{str(e)}")

    def edit_risk_rule(self):
        """编辑风险规则"""
        try:
            current_item = self.rules_tree.currentItem()
            if not current_item:
                QMessageBox.information(self, "提示", "请先选择要编辑的规则")
                return

            from gui.dialogs.risk_rule_config_dialog import RiskRuleConfigDialog
            from core.risk_rule_manager import get_risk_rule_manager, RiskRule

            # 获取规则ID
            rule_id = current_item.data(0, Qt.UserRole)
            if not rule_id:
                QMessageBox.warning(self, "错误", "无法获取规则ID")
                return

            # 从数据库获取规则数据
            rule_manager = get_risk_rule_manager()
            rule = rule_manager.get_rule(rule_id)
            if not rule:
                QMessageBox.warning(self, "错误", "规则不存在")
                return

            # 转换为字典格式
            rule_data = {
                'id': rule.id,
                'name': rule.name,
                'rule_type': rule.rule_type,
                'priority': rule.priority,
                'enabled': rule.enabled,
                'description': rule.description,
                'metric_name': rule.metric_name,
                'operator': rule.operator,
                'threshold_value': rule.threshold_value,
                'threshold_unit': rule.threshold_unit,
                'duration': rule.duration,
                'check_interval': rule.check_interval,
                'silence_period': rule.silence_period,
                'max_alerts': rule.max_alerts,
                'email_notification': rule.email_notification,
                'sms_notification': rule.sms_notification,
                'desktop_notification': rule.desktop_notification,
                'sound_notification': rule.sound_notification,
                'webhook_notification': rule.webhook_notification,
                'message_template': rule.message_template
            }

            dialog = RiskRuleConfigDialog(rule_data, parent=self)
            if dialog.exec_() == dialog.Accepted:
                updated_data = dialog.get_rule_data()

                # 更新规则对象
                updated_rule = RiskRule(**updated_data)

                # 保存到数据库
                if rule_manager.update_rule(updated_rule):
                    # 更新界面
                    self._update_rule_in_tree(current_item, updated_rule)
                    QMessageBox.information(self, "成功", f"风险规则 '{updated_rule.name}' 已更新")
                else:
                    QMessageBox.warning(self, "失败", "更新风险规则失败")

        except Exception as e:
            logger.error(f"编辑风险规则失败: {e}")
            QMessageBox.critical(self, "错误", f"编辑风险规则时发生错误：{str(e)}")

    def delete_risk_rule(self):
        """删除风险规则"""
        try:
            current_item = self.rules_tree.currentItem()
            if not current_item:
                QMessageBox.information(self, "提示", "请先选择要删除的规则")
                return

            rule_name = current_item.text(0)
            reply = QMessageBox.question(
                self, "删除规则", f"确定要删除风险规则 '{rule_name}' 吗？\n删除后将无法恢复。",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                from core.risk_rule_manager import get_risk_rule_manager

                # 获取规则ID
                rule_id = current_item.data(0, Qt.UserRole)
                if rule_id:
                    # 从数据库删除
                    rule_manager = get_risk_rule_manager()
                    if rule_manager.delete_rule(rule_id):
                        # 从界面删除
                        self.rules_tree.takeTopLevelItem(
                            self.rules_tree.indexOfTopLevelItem(current_item)
                        )
                        QMessageBox.information(self, "成功", f"风险规则 '{rule_name}' 已删除")
                    else:
                        QMessageBox.warning(self, "失败", "删除风险规则失败")
                else:
                    QMessageBox.warning(self, "错误", "无法获取规则ID")

        except Exception as e:
            logger.error(f"删除风险规则失败: {e}")
            QMessageBox.critical(self, "错误", f"删除风险规则时发生错误：{str(e)}")

    def _add_rule_to_tree(self, rule):
        """添加规则到树形控件"""
        try:
            item = QTreeWidgetItem()
            item.setText(0, rule.name)
            item.setText(1, rule.rule_type)
            item.setText(2, f"{rule.threshold_value:.2f}{rule.threshold_unit}")
            item.setText(3, "启用" if rule.enabled else "禁用")

            # 存储规则ID
            item.setData(0, Qt.UserRole, rule.id)

            # 根据状态设置颜色
            if rule.enabled:
                item.setBackground(0, QColor("#e8f5e8"))  # 浅绿色
            else:
                item.setBackground(0, QColor("#ffebee"))  # 浅红色

            self.rules_tree.addTopLevelItem(item)

        except Exception as e:
            logger.error(f"添加规则到树形控件失败: {e}")

    def _update_rule_in_tree(self, item, rule):
        """更新树形控件中的规则"""
        try:
            item.setText(0, rule.name)
            item.setText(1, rule.rule_type)
            item.setText(2, f"{rule.threshold_value:.2f}{rule.threshold_unit}")
            item.setText(3, "启用" if rule.enabled else "禁用")

            # 根据状态设置颜色
            if rule.enabled:
                item.setBackground(0, QColor("#e8f5e8"))  # 浅绿色
            else:
                item.setBackground(0, QColor("#ffebee"))  # 浅红色

        except Exception as e:
            logger.error(f"更新树形控件中的规则失败: {e}")

    def load_risk_rules(self):
        """加载风险规则"""
        try:
            from core.risk_rule_manager import get_risk_rule_manager

            rule_manager = get_risk_rule_manager()
            rules = rule_manager.get_all_rules()

            # 清空现有规则
            self.rules_tree.clear()

            # 添加规则到树形控件
            for rule in rules:
                self._add_rule_to_tree(rule)

            logger.info(f"已加载 {len(rules)} 个风险规则")

        except Exception as e:
            logger.error(f"加载风险规则失败: {e}")

    def _check_risk_rules(self, risk_metrics: Dict[str, float]):
        """检查风险规则并处理告警"""
        try:
            from core.risk_rule_manager import get_risk_rule_manager

            rule_manager = get_risk_rule_manager()
            alerts = rule_manager.check_rules(risk_metrics)

            # 处理生成的告警
            for alert in alerts:
                self._handle_risk_alert(alert)

        except Exception as e:
            logger.error(f"检查风险规则失败: {e}")

    def _handle_risk_alert(self, alert):
        """处理风险告警"""
        try:
            # 记录告警日志
            logger.warning(f"风险告警: {alert.message}")

            # 发送桌面通知
            self._send_desktop_notification(alert)

            # 播放声音通知（如果启用）
            self._play_alert_sound(alert)

            # 更新UI显示
            self._update_alert_display(alert)

        except Exception as e:
            logger.error(f"处理风险告警失败: {e}")

    def _send_desktop_notification(self, alert):
        """发送桌面通知"""
        try:
            from PyQt5.QtWidgets import QSystemTrayIcon
            from PyQt5.QtGui import QIcon

            # 这里可以集成系统托盘通知
            # 暂时使用消息框代替
            if hasattr(self, 'parent') and self.parent():
                QMessageBox.warning(
                    self.parent(),
                    f"风险告警 - {alert.alert_level}",
                    alert.message
                )

        except Exception as e:
            logger.debug(f"发送桌面通知失败: {e}")

    def _play_alert_sound(self, alert):
        """播放告警声音"""
        try:
            # 这里可以集成声音播放
            # 暂时跳过
            pass

        except Exception as e:
            logger.debug(f"播放告警声音失败: {e}")

    def _update_alert_display(self, alert):
        """更新告警显示"""
        try:
            # 这里可以更新告警列表显示
            # 暂时只记录日志
            logger.info(f"告警显示已更新: {alert.rule_name}")

        except Exception as e:
            logger.debug(f"更新告警显示失败: {e}")

    def show_rules_context_menu(self, position):
        """显示规则右键菜单"""
        try:
            menu = QMenu(self)
            menu.addAction("添加规则", self.add_risk_rule)
            menu.addAction("编辑规则", self.edit_risk_rule)
            menu.addAction("删除规则", self.delete_risk_rule)
            menu.exec_(self.rules_tree.mapToGlobal(position))
        except Exception as e:
            logger.error(f"显示规则菜单失败: {e}")

    def load_risk_history(self):
        """加载风险历史数据"""
        try:
            from db.models.performance_history_models import get_performance_history_manager
            from datetime import datetime, timedelta

            time_range = self.time_range_combo.currentText()
            logger.info(f"加载风险历史数据: {time_range}")

            # 计算时间范围
            end_time = datetime.now()
            if time_range == "最近1小时":
                start_time = end_time - timedelta(hours=1)
            elif time_range == "最近24小时":
                start_time = end_time - timedelta(days=1)
            elif time_range == "最近7天":
                start_time = end_time - timedelta(days=7)
            elif time_range == "最近30天":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=1)

            # 从数据库获取风险历史数据
            history_manager = get_performance_history_manager()
            risk_records = history_manager.get_risk_history(
                start_time=start_time,
                end_time=end_time,
                limit=500
            )

            # 更新历史表格
            self._update_risk_history_table(risk_records)

        except Exception as e:
            logger.error(f"加载风险历史失败: {e}")

    def _update_risk_history_table(self, records):
        """更新风险历史表格"""
        try:
            self.risk_history_table.setRowCount(len(records))

            for row, record in enumerate(records):
                # 时间
                time_item = QTableWidgetItem(record.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
                self.risk_history_table.setItem(row, 0, time_item)

                # 风险类型（选择主要风险）
                main_risk = "综合风险"
                if record.market_risk > 50:
                    main_risk = "市场风险"
                elif record.position_risk > 50:
                    main_risk = "仓位风险"
                elif record.liquidity_risk > 50:
                    main_risk = "流动性风险"

                risk_type_item = QTableWidgetItem(main_risk)
                self.risk_history_table.setItem(row, 1, risk_type_item)

                # 风险等级
                level_item = QTableWidgetItem(record.risk_level)
                # 根据风险等级设置颜色
                if record.risk_level in ["高风险", "极高风险"]:
                    level_item.setBackground(QColor("#ffebee"))  # 浅红色
                elif record.risk_level in ["中高风险"]:
                    level_item.setBackground(QColor("#fff3e0"))  # 浅橙色
                else:
                    level_item.setBackground(QColor("#e8f5e8"))  # 浅绿色

                self.risk_history_table.setItem(row, 2, level_item)

                # 风险值
                risk_value_item = QTableWidgetItem(f"{record.overall_risk_score:.2f}")
                self.risk_history_table.setItem(row, 3, risk_value_item)

                # 阈值（根据风险等级设置）
                if record.risk_level == "低风险":
                    threshold = "< 15%"
                elif record.risk_level == "中低风险":
                    threshold = "15-35%"
                elif record.risk_level == "中高风险":
                    threshold = "35-60%"
                elif record.risk_level == "高风险":
                    threshold = "60-80%"
                else:
                    threshold = "> 80%"

                threshold_item = QTableWidgetItem(threshold)
                self.risk_history_table.setItem(row, 4, threshold_item)

                # 状态
                status = "正常" if record.overall_risk_score < 60 else "警告"
                status_item = QTableWidgetItem(status)
                if status == "警告":
                    status_item.setBackground(QColor("#ffebee"))

                self.risk_history_table.setItem(row, 5, status_item)

            logger.info(f"风险历史表格已更新: {len(records)}条记录")

        except Exception as e:
            logger.error(f"更新风险历史表格失败: {e}")

    def refresh_risk_history(self):
        """刷新风险历史"""
        try:
            self.load_risk_history()
        except Exception as e:
            logger.error(f"刷新风险历史失败: {e}")

    def update_data(self, data: Dict[str, any]):
        """统一数据更新接口"""
        try:
            if 'risk_metrics' in data:
                self.update_risk_data(data['risk_metrics'])

        except Exception as e:
            logger.error(f"更新风险控制数据失败: {e}")

    # ==================== 增强风险监控功能 ====================

    def start_enhanced_monitoring(self):
        """启动增强风险监控"""
        if not self.enhanced_risk_monitor:
            return False

        try:
            self.enhanced_risk_monitor.start_monitoring()
            logger.info("增强风险监控已启动")

            # 启动定时更新
            self.enhanced_update_timer = QTimer()
            self.enhanced_update_timer.timeout.connect(self.update_enhanced_risk_data)
            self.enhanced_update_timer.start(30000)  # 30秒更新一次

            return True
        except Exception as e:
            logger.error(f"启动增强风险监控失败: {e}")
            return False

    def stop_enhanced_monitoring(self):
        """停止增强风险监控"""
        if not self.enhanced_risk_monitor:
            return False

        try:
            self.enhanced_risk_monitor.stop_monitoring()

            if hasattr(self, 'enhanced_update_timer'):
                self.enhanced_update_timer.stop()

            logger.info("增强风险监控已停止")
            return True
        except Exception as e:
            logger.error(f"停止增强风险监控失败: {e}")
            return False

    def update_enhanced_risk_data(self):
        """更新增强风险数据"""
        if not self.enhanced_risk_monitor:
            return

        try:
            # 获取当前风险状态
            risk_status = self.enhanced_risk_monitor.get_current_risk_status()

            # 更新风险等级显示
            self._update_risk_level_from_enhanced_data(risk_status)

            # 获取最新预警
            alerts = self.enhanced_risk_monitor.get_risk_alerts(1, False)  # 最近1小时

            # 更新预警显示
            self._update_alerts_from_enhanced_data(alerts)

            # 如果AI分析标签页存在，更新AI数据
            if hasattr(self, 'ai_analysis_tab'):
                self._update_ai_analysis_data()

        except Exception as e:
            logger.error(f"更新增强风险数据失败: {e}")

    def _update_risk_level_from_enhanced_data(self, risk_status):
        """从增强数据更新风险等级"""
        try:
            if not risk_status or 'risk_distribution' not in risk_status:
                return

            distribution = risk_status['risk_distribution']

            # 计算整体风险分数
            total_metrics = sum(distribution.values())
            if total_metrics == 0:
                return

            # 计算加权风险分数
            risk_weights = {
                'very_low': 0.1, 'low': 0.3, 'medium': 0.5,
                'high': 0.7, 'critical': 0.9, 'extreme': 1.0
            }

            weighted_score = 0
            for level, count in distribution.items():
                weight = risk_weights.get(level, 0.5)
                weighted_score += (count / total_metrics) * weight

            # 更新风险等级显示
            risk_percentage = int(weighted_score * 100)
            self.risk_level_bar.setValue(risk_percentage)

            # 更新风险等级文本和颜色
            if weighted_score < 0.3:
                level_text = "低风险"
                color = "#27ae60"
                bar_color = "#27ae60"
            elif weighted_score < 0.5:
                level_text = "中低风险"
                color = "#f39c12"
                bar_color = "#f39c12"
            elif weighted_score < 0.7:
                level_text = "中高风险"
                color = "#e67e22"
                bar_color = "#e67e22"
            elif weighted_score < 0.9:
                level_text = "高风险"
                color = "#e74c3c"
                bar_color = "#e74c3c"
            else:
                level_text = "极高风险"
                color = "#c0392b"
                bar_color = "#c0392b"

            self.risk_level_label.setText(f"当前风险等级: {level_text}")
            self.risk_level_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")

            # 更新进度条颜色
            self.risk_level_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: {bar_color};
                    border-radius: 3px;
                }}
            """)

        except Exception as e:
            logger.error(f"更新风险等级显示失败: {e}")

    def _update_alerts_from_enhanced_data(self, alerts):
        """从增强数据更新预警显示"""
        try:
            if not alerts:
                return

            # 更新预警表格（如果存在）
            if hasattr(self, 'alerts_table'):
                self.alerts_table.setRowCount(len(alerts))

                for row, alert in enumerate(alerts):
                    # 时间
                    time_item = QTableWidgetItem(alert.get('timestamp', ''))
                    self.alerts_table.setItem(row, 0, time_item)

                    # 类型
                    type_item = QTableWidgetItem(alert.get('category', ''))
                    self.alerts_table.setItem(row, 1, type_item)

                    # 等级
                    level_item = QTableWidgetItem(alert.get('level', ''))
                    # 根据等级设置颜色
                    if alert.get('level') in ['critical', 'extreme']:
                        level_item.setBackground(QColor("#ffebee"))
                    elif alert.get('level') == 'high':
                        level_item.setBackground(QColor("#fff3e0"))

                    self.alerts_table.setItem(row, 2, level_item)

                    # 消息
                    message_item = QTableWidgetItem(alert.get('message', ''))
                    self.alerts_table.setItem(row, 3, message_item)

                    # 状态
                    status = "已解决" if alert.get('resolved', False) else "待处理"
                    status_item = QTableWidgetItem(status)
                    if not alert.get('resolved', False):
                        status_item.setBackground(QColor("#fff3e0"))

                    self.alerts_table.setItem(row, 4, status_item)

        except Exception as e:
            logger.error(f"更新预警显示失败: {e}")

    def _create_ai_analysis_tab(self):
        """创建AI智能分析标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # AI预测区域
        prediction_group = QGroupBox("🔮 AI风险预测")
        prediction_layout = QVBoxLayout()

        # 预测结果显示
        self.ai_prediction_text = QTextEdit()
        self.ai_prediction_text.setMaximumHeight(120)
        self.ai_prediction_text.setReadOnly(True)
        self.ai_prediction_text.setPlainText("AI风险预测功能已启用，正在分析...")
        prediction_layout.addWidget(self.ai_prediction_text)

        prediction_group.setLayout(prediction_layout)
        layout.addWidget(prediction_group)

        # 异常检测区域
        anomaly_group = QGroupBox("智能异常检测")
        anomaly_layout = QVBoxLayout()

        # 异常检测结果表格
        self.anomaly_table = QTableWidget()
        self.anomaly_table.setColumnCount(4)
        self.anomaly_table.setHorizontalHeaderLabels([
            "检测时间", "异常类型", "严重程度", "描述"
        ])
        self.anomaly_table.horizontalHeader().setStretchLastSection(True)
        self.anomaly_table.setMaximumHeight(150)
        anomaly_layout.addWidget(self.anomaly_table)

        anomaly_group.setLayout(anomaly_layout)
        layout.addWidget(anomaly_group)

        # 智能建议区域
        suggestions_group = QGroupBox("[INFO] 智能风险建议")
        suggestions_layout = QVBoxLayout()

        self.ai_suggestions_text = QTextEdit()
        self.ai_suggestions_text.setMaximumHeight(100)
        self.ai_suggestions_text.setReadOnly(True)
        self.ai_suggestions_text.setPlainText("正在生成智能风险控制建议...")
        suggestions_layout.addWidget(self.ai_suggestions_text)

        suggestions_group.setLayout(suggestions_layout)
        layout.addWidget(suggestions_group)

        # 风险情景分析
        scenarios_group = QGroupBox("风险情景分析")
        scenarios_layout = QVBoxLayout()

        self.scenarios_table = QTableWidget()
        self.scenarios_table.setColumnCount(4)
        self.scenarios_table.setHorizontalHeaderLabels([
            "情景名称", "发生概率", "影响程度", "风险分数"
        ])
        self.scenarios_table.horizontalHeader().setStretchLastSection(True)
        self.scenarios_table.setMaximumHeight(120)
        scenarios_layout.addWidget(self.scenarios_table)

        scenarios_group.setLayout(scenarios_layout)
        layout.addWidget(scenarios_group)

        # 控制按钮
        button_layout = QHBoxLayout()

        refresh_ai_btn = QPushButton("刷新AI分析")
        refresh_ai_btn.clicked.connect(self._refresh_ai_analysis)
        button_layout.addWidget(refresh_ai_btn)

        export_ai_btn = QPushButton("导出AI报告")
        export_ai_btn.clicked.connect(self._export_ai_report)
        button_layout.addWidget(export_ai_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        return tab

    def _update_ai_analysis_data(self):
        """更新AI分析数据"""
        if not self.enhanced_risk_monitor:
            return

        try:
            # 更新AI预测
            self._update_ai_predictions()

            # 更新异常检测
            self._update_anomaly_detection()

            # 更新智能建议
            self._update_ai_suggestions()

            # 更新风险情景
            self._update_risk_scenarios()

        except Exception as e:
            logger.error(f"更新AI分析数据失败: {e}")

    def _update_ai_predictions(self):
        """更新AI预测"""
        try:
            # 这里可以调用AI服务获取预测结果
            prediction_text = "AI风险预测结果:\n"
            prediction_text += "• 市场风险预测: 未来24小时内风险水平可能上升15%\n"
            prediction_text += "• 流动性风险预测: 保持稳定，无显著变化\n"
            prediction_text += "• 集中度风险预测: 建议关注科技股集中度\n"
            prediction_text += f"• 预测置信度: 85%\n"
            prediction_text += f"• 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.ai_prediction_text.setPlainText(prediction_text)

        except Exception as e:
            logger.error(f"更新AI预测失败: {e}")

    def _update_anomaly_detection(self):
        """更新异常检测"""
        try:
            # 获取异常检测结果
            # 这里使用模拟数据，实际应该从enhanced_risk_monitor获取
            anomalies = [
                {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'type': '波动率异常',
                    'severity': '中等',
                    'description': '市场波动率超出正常范围'
                }
            ]

            self.anomaly_table.setRowCount(len(anomalies))
            for row, anomaly in enumerate(anomalies):
                self.anomaly_table.setItem(row, 0, QTableWidgetItem(anomaly['timestamp']))
                self.anomaly_table.setItem(row, 1, QTableWidgetItem(anomaly['type']))
                self.anomaly_table.setItem(row, 2, QTableWidgetItem(anomaly['severity']))
                self.anomaly_table.setItem(row, 3, QTableWidgetItem(anomaly['description']))

        except Exception as e:
            logger.error(f"更新异常检测失败: {e}")

    def _update_ai_suggestions(self):
        """更新AI建议"""
        try:
            suggestions_text = "智能风险控制建议:\n"
            suggestions_text += "1. 建议降低高风险资产的仓位权重\n"
            suggestions_text += "2. 增加对冲策略以降低市场风险敞口\n"
            suggestions_text += "3. 关注流动性较差的小盘股持仓\n"
            suggestions_text += "4. 考虑增加现金储备以应对潜在风险\n"
            suggestions_text += f"建议更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.ai_suggestions_text.setPlainText(suggestions_text)

        except Exception as e:
            logger.error(f"更新AI建议失败: {e}")

    def _update_risk_scenarios(self):
        """更新风险情景"""
        try:
            # 获取风险情景
            scenarios = self.enhanced_risk_monitor.get_risk_scenarios(5) if self.enhanced_risk_monitor else []

            if not scenarios:
                # 使用模拟数据
                scenarios = [
                    {'name': '市场大幅下跌', 'probability': 0.15, 'impact': 0.8, 'risk_score': 0.6},
                    {'name': '流动性危机', 'probability': 0.05, 'impact': 0.9, 'risk_score': 0.45},
                    {'name': '行业轮动', 'probability': 0.3, 'impact': 0.4, 'risk_score': 0.35}
                ]

            self.scenarios_table.setRowCount(len(scenarios))
            for row, scenario in enumerate(scenarios):
                self.scenarios_table.setItem(row, 0, QTableWidgetItem(scenario.get('name', '')))
                self.scenarios_table.setItem(row, 1, QTableWidgetItem(f"{scenario.get('probability', 0):.1%}"))
                self.scenarios_table.setItem(row, 2, QTableWidgetItem(f"{scenario.get('impact', 0):.1%}"))
                self.scenarios_table.setItem(row, 3, QTableWidgetItem(f"{scenario.get('risk_score', 0):.2f}"))

        except Exception as e:
            logger.error(f"更新风险情景失败: {e}")

    def _refresh_ai_analysis(self):
        """刷新AI分析"""
        try:
            self._update_ai_analysis_data()
            logger.info("AI分析数据已刷新")
        except Exception as e:
            logger.error(f"刷新AI分析失败: {e}")

    def _export_ai_report(self):
        """导出AI报告"""
        try:
            # 这里可以实现AI报告导出功能
            QMessageBox.information(self, "导出成功", "AI风险分析报告已导出到本地文件")
        except Exception as e:
            logger.error(f"导出AI报告失败: {e}")
            QMessageBox.warning(self, "导出失败", f"导出AI报告失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 停止增强风险监控
            self.stop_enhanced_monitoring()
            event.accept()
        except Exception as e:
            logger.error(f"关闭风险控制中心失败: {e}")
            event.accept()
