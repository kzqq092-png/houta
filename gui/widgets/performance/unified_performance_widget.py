#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一性能监控组件
现代化统一性能监控界面
"""

import json
import logging
from datetime import datetime
from typing import Dict
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QToolBar, QLabel, QTabWidget, QStatusBar,
    QSizePolicy, QFileDialog, QFrame
)
from PyQt5.QtCore import Qt, QDateTime, QThreadPool, pyqtSlot, QTimer
from PyQt5.QtGui import QIcon
from core.events import EventBus
from core.performance import get_performance_monitor
from gui.widgets.performance.workers.async_workers import (
    AsyncDataWorker, AsyncStrategyWorker, AsyncDataSignals
)
from gui.widgets.performance.tabs.system_monitor_tab import ModernSystemMonitorTab
from gui.widgets.performance.tabs.ui_optimization_tab import ModernUIOptimizationTab
from gui.widgets.performance.tabs.algorithm_performance_tab import ModernAlgorithmPerformanceTab
from gui.widgets.performance.tabs.auto_tuning_tab import ModernAutoTuningTab
from gui.widgets.performance.tabs.system_health_tab import ModernSystemHealthTab
from gui.widgets.performance.tabs.alert_config_tab import ModernAlertConfigTab
from gui.widgets.performance.tabs.deep_analysis_tab import ModernDeepAnalysisTab
from gui.widgets.performance.tabs.strategy_performance_tab import ModernStrategyPerformanceTab

logger = logging.getLogger(__name__)


class ModernUnifiedPerformanceWidget(QWidget):
    """现代化统一性能监控组件 - 专业交易软件风格"""

    def __init__(self, event_bus: EventBus = None, health_checker=None, parent=None):
        super().__init__(parent)

        # 设置窗口标志
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint |
                            Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        self.monitor = get_performance_monitor()
        self._event_bus = event_bus
        self._health_checker = health_checker
        self.current_tab_index = 0  # 添加当前tab跟踪
        self._data_cache = {}  # 添加数据缓存
        self._last_update_time = {}  # 添加更新时间跟踪

        # 性能优化相关变量
        self._is_dragging = False  # 拖动状态检测
        self._update_paused = False  # 更新暂停标志
        self._last_mouse_move_time = 0  # 最后鼠标移动时间
        self._update_counter = 0  # 更新计数器，用于降频

        # 智能性能监控已移除 - 避免功能重叠
        self.performance_integrator = None
        self._has_smart_monitoring = False

        # 初始化性能监控器
        from core.performance.unified_monitor import UnifiedPerformanceMonitor
        self.performance_monitor = UnifiedPerformanceMonitor()
        logger.info("性能监控器初始化完成")
        self.performance_integrator = None
        self._has_smart_monitoring = False

        # 初始化异步数据获取
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # 限制并发线程数
        self._async_signals = AsyncDataSignals()
        self._async_signals.data_ready.connect(self._handle_async_data)
        self._async_signals.error_occurred.connect(self._handle_async_error)

        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 现代化工具栏
        self.toolbar = self._create_modern_toolbar()
        layout.addWidget(self.toolbar)

        # 智能洞察面板（如果可用）
        if self._has_smart_monitoring:
            # 智能性能洞察功能已删除 - 与监控中心功能重叠
            pass

        # 主要内容标签页
        self.tab_widget = self._create_modern_tabs()
        layout.addWidget(self.tab_widget, 1)

        # 现代化状态栏
        self.status_bar = self._create_modern_status_bar()
        layout.addWidget(self.status_bar)

        # 🚨 样式表保护机制
        self._setup_style_protection()

        # 应用现代化样式
        self._apply_modern_styling()

    def _create_modern_toolbar(self):
        """创建现代化工具栏"""
        toolbar = QToolBar()

        # 现代化样式
        toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2c3e50, stop: 1 #34495e);
                border: none;
                border-bottom: 1px solid #1a252f;
                spacing: 0px;
                padding: 0px;
                min-height: 40px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 0px;
                margin: 0px;
                color: #ecf0f1;
                font-weight: 500;
                min-width: 24px;
                min-height: 25px;
            }
            QToolButton:hover {
                background: rgba(52, 152, 219, 0.15);
                border: 1px solid #3498db;
                color: #ffffff;
            }
            QToolButton:pressed {
                background: rgba(52, 152, 219, 0.25);
                border: 1px solid #2e80b9;
            }
        """)

        # 添加现代化按钮
        refresh_action = toolbar.addAction("🔄刷新数据")
        refresh_action.setToolTip("刷新数据 (F5)")
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_data)

        # 🚨 添加UI修复按钮
        fix_ui_action = toolbar.addAction("🎨修复界面")
        fix_ui_action.setToolTip("修复界面显示问题 (Ctrl+R)")
        fix_ui_action.setShortcut("Ctrl+R")
        fix_ui_action.triggered.connect(self.force_refresh_ui)

        export_action = toolbar.addAction("📊导出性能报告")
        export_action.setToolTip("导出性能报告")
        export_action.triggered.connect(self.export_report)

        toolbar.addSeparator()

        # 添加弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        toolbar.setFixedHeight(40)

        # 状态指示器
        self.connection_status = QLabel("🟢 实时连接")
        self.connection_status.setStyleSheet("""
            color: #27ae60; 
            font-weight: bold; 
            font-size: 11px;
            padding: 8px 12px;
            background: rgba(39, 174, 96, 0.1);
            border-radius: 4px;
            margin: 4px;
        """)
        toolbar.addWidget(self.connection_status)

        return toolbar

    def _create_modern_tabs(self):
        """创建现代化标签页"""
        tab_widget = QTabWidget()

        # 添加tab切换监听
        tab_widget.currentChanged.connect(self.on_tab_changed)

        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #34495e;
                background: #2c3e50;
                border-radius: 0px 0px 6px 6px;
            }
            QTabBar::tab {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #34495e, stop: 1 #2c3e50);
                border: 1px solid #34495e;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 80px;
                padding: 12px 20px;
                margin-right: 2px;
                color: #bdc3c7;
                font-weight: 500;
                font-size: 12px;
                height: 12px;
            }
            QTabBar::tab:selected {
                background: #2c3e50;
                border-bottom: 1px solid #3498db;
                color: #ecf0f1;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #2c3e50;
                color: #ecf0f1;
            }
        """)

        # 添加所有性能监控标签页
        self.system_tab = ModernSystemMonitorTab()
        tab_widget.addTab(self.system_tab, "🖥 系统监控")

        self.ui_tab = ModernUIOptimizationTab()
        tab_widget.addTab(self.ui_tab, "🎨 UI优化")

        self.strategy_tab = ModernStrategyPerformanceTab()
        tab_widget.addTab(self.strategy_tab, "📈 策略性能")

        self.algorithm_tab = ModernAlgorithmPerformanceTab()
        tab_widget.addTab(self.algorithm_tab, "🔬 算法性能")

        self.tuning_tab = ModernAutoTuningTab()
        tab_widget.addTab(self.tuning_tab, "⚙️ 自动调优")

        # 新增功能标签页（移除历史数据标签页）
        self.health_tab = ModernSystemHealthTab(self._health_checker)
        tab_widget.addTab(self.health_tab, "🏥 健康检查")

        self.alert_tab = ModernAlertConfigTab()
        tab_widget.addTab(self.alert_tab, "🚨 告警配置")

        self.analysis_tab = ModernDeepAnalysisTab()
        tab_widget.addTab(self.analysis_tab, "🔬 深度分析")

        return tab_widget

    def _create_modern_status_bar(self):
        """创建现代化状态栏"""
        status_bar = QStatusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #34495e, stop: 1 #2c3e50);
                border-top: 1px solid #1a252f;
                color: #bdc3c7;
                font-size: 10px;
                padding: 4px;
            }
            QStatusBar::item {
                border: none;
            }
        """)

        self.status_message = QLabel("就绪")
        status_bar.addWidget(self.status_message)

        status_bar.addPermanentWidget(QLabel("｜"))

        self.data_update_time = QLabel("数据更新: " +
                                       QDateTime.currentDateTime().toString("hh:mm:ss"))
        status_bar.addPermanentWidget(self.data_update_time)

        return status_bar

    def _apply_modern_styling(self):
        """应用现代化样式主题"""
        self.setStyleSheet("""
            QWidget {
                font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
                font-size: 9pt;
                background: #2c3e50;
                color: #ecf0f1;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

    def setup_timer(self):
        """设置定时刷新 - 优化更新策略"""
        self.refresh_timer = QTimer(self)  # 设置父对象
        self.refresh_timer.timeout.connect(self.update_current_tab_data_async)  # 异步更新当前tab
        self.refresh_timer.start(2000)  # 改为2秒刷新一次，减少卡顿

        # 添加拖动检测定时器
        self.drag_detect_timer = QTimer(self)
        self.drag_detect_timer.timeout.connect(self._check_drag_state)
        self.drag_detect_timer.start(100)  # 100ms检测一次拖动状态

    def update_current_tab_data_async(self):
        """异步更新当前显示的tab数据 - 避免阻塞UI"""
        try:
            # 如果正在拖动，跳过更新
            if self._update_paused or self._is_dragging:
                return

            # 使用计数器降频更新
            self._update_counter += 1
            if self._update_counter % 2 != 0:  # 每2次调用才真正更新一次
                return

            current_time = QDateTime.currentDateTime()

            # 根据当前tab索引异步获取对应数据
            if self.current_tab_index == 0:  # 系统监控
                # 使用缓存机制减少频繁数据收集
                cache_key = 'system_metrics'
                if self._should_update_cache(cache_key, 3):  # 3秒缓存
                    try:
                        system_metrics = self.monitor.system_monitor.collect_metrics()
                        if system_metrics:
                            # 数据映射修正
                            mapped_metrics = {
                                "CPU使用率": system_metrics.get('cpu_usage', 0),
                                "内存使用率": system_metrics.get('memory_usage', 0),
                                "磁盘使用率": system_metrics.get('disk_usage', 0),
                                "网络吞吐": system_metrics.get('网络吞吐', 0),
                                "进程数量": system_metrics.get('进程数量', 0),
                                "线程数量": system_metrics.get('线程数量', 0),
                                "句柄数量": system_metrics.get('句柄数量', 0),
                                "响应时间": system_metrics.get('响应时间', 0),
                                # 新增指标
                                "内存可用": system_metrics.get('memory_available', 0),
                                "磁盘可用": system_metrics.get('disk_free', 0),
                                "网络发送": system_metrics.get('network_bytes_sent', 0) / (1024**2),  # MB
                                "网络接收": system_metrics.get('network_bytes_recv', 0) / (1024**2),  # MB
                            }
                            self._data_cache[cache_key] = mapped_metrics
                            self._last_update_time[cache_key] = current_time
                            self.system_tab.update_data(mapped_metrics)
                    except Exception as e:
                        logger.error(f"异步更新系统监控数据失败: {e}")
                else:
                    # 使用缓存数据
                    cached_data = self._data_cache.get(cache_key, {})
                    if cached_data:
                        self.system_tab.update_data(cached_data)

            elif self.current_tab_index == 1:  # UI优化
                cache_key = 'ui_stats'
                if self._should_update_cache(cache_key, 3):  # 3秒缓存
                    # 直接收集UI数据
                    if hasattr(self, 'performance_monitor'):
                        fresh_data = self.performance_monitor.collect_all_metrics()
                        self._data_cache[cache_key] = fresh_data
                        self.ui_tab.update_data(fresh_data)
                        logger.debug(f"UI优化数据已刷新: 帧率={fresh_data.get('渲染帧率', 0):.1f}")
                    self._last_update_time[cache_key] = current_time
                else:
                    # 使用缓存数据
                    cached_data = self._data_cache.get(cache_key, {})
                    if cached_data:
                        self.ui_tab.update_data(cached_data)

            elif self.current_tab_index == 2:  # 策略性能
                # 策略性能使用异步更新避免UI卡顿
                cache_key = 'strategy_performance'
                if self._should_update_cache(cache_key, 5):  # 5秒缓存
                    # 创建异步工作线程处理策略性能计算
                    worker = AsyncStrategyWorker(self.monitor, self.strategy_tab)
                    worker.signals.data_ready.connect(lambda data: self._on_strategy_data_received(data, cache_key, current_time))
                    worker.signals.finished.connect(lambda: self._on_strategy_calculation_finished(cache_key, current_time))
                    worker.signals.error_occurred.connect(self._handle_async_error)
                    self.thread_pool.start(worker)

            elif self.current_tab_index == 3:  # 算法性能
                cache_key = 'algo_stats'
                if self._should_update_cache(cache_key, 5):  # 5秒缓存
                    # 直接收集算法数据
                    if hasattr(self, 'performance_monitor'):
                        fresh_data = self.performance_monitor.collect_all_metrics()
                        self._data_cache[cache_key] = fresh_data
                        self.algorithm_tab.update_data(fresh_data)
                        logger.debug(f"算法性能数据已刷新: 计算速度={fresh_data.get('计算速度', 0):.1f}")
                    self._last_update_time[cache_key] = current_time
                else:
                    # 使用缓存数据
                    cached_data = self._data_cache.get(cache_key, {})
                    if cached_data:
                        self.algorithm_tab.update_data(cached_data)

            elif self.current_tab_index == 4:  # 自动调优
                cache_key = 'tuning_stats'
                if self._should_update_cache(cache_key, 8):  # 8秒缓存
                    worker = AsyncDataWorker(None, None, self.monitor, "tuning")
                    # 🚨 修复：正确连接信号，不要重新赋值signals对象
                    worker.signals.data_ready.connect(self._handle_async_data)
                    worker.signals.error_occurred.connect(self._handle_async_error)
                    self.thread_pool.start(worker)
                    self._last_update_time[cache_key] = current_time
                else:
                    # 使用缓存数据
                    self.tuning_tab.update_data(self._data_cache.get(cache_key, {}))

            # 新增标签页不需要定时更新，它们是按需更新的
            # 健康检查标签页 (index 5) - 按需检查
            # 告警配置标签页 (index 6) - 静态配置
            # 深度分析标签页 (index 7) - 按需分析

            # 更新状态栏时间
            self.data_update_time.setText("数据更新: " + current_time.toString("hh:mm:ss"))

        except Exception as e:
            logger.error(f"异步更新当前tab数据失败: {e}")

    def _on_strategy_data_received(self, data: dict, cache_key: str, current_time):
        """🚨 线程安全修复：在主线程中处理策略数据并更新UI"""
        try:
            if data and 'monitor' in data:
                # 在主线程中安全地更新UI
                monitor = data['monitor']
                if hasattr(self, 'strategy_tab') and self.strategy_tab:
                    # 确保在主线程中调用UI更新
                    self.strategy_tab.update_data(monitor)
                    logger.debug("策略性能UI更新完成（主线程）")
                else:
                    logger.warning("策略标签页不存在，跳过UI更新")
            else:
                logger.debug("收到空的策略数据，跳过UI更新")

            self._last_update_time[cache_key] = current_time

        except Exception as e:
            logger.error(f"处理策略数据失败: {e}")
            # 确保UI状态一致性
            try:
                if hasattr(self, 'strategy_tab') and self.strategy_tab:
                    # 在出错时也要确保UI状态正确
                    pass
            except:
                pass

    def _on_strategy_calculation_finished(self, cache_key: str, current_time):
        """策略计算完成的回调"""
        try:
            logger.debug("策略性能异步计算完成")
        except Exception as e:
            logger.error(f"处理策略计算完成回调失败: {e}")

    def _on_strategy_data_ready(self, cache_key: str, current_time):
        """策略数据异步计算完成的回调（保留兼容性）"""
        try:
            self._last_update_time[cache_key] = current_time
            logger.debug("策略性能数据异步更新完成")
        except Exception as e:
            logger.error(f"处理策略数据完成回调失败: {e}")

    def _check_drag_state(self):
        """检测拖动状态"""
        import time
        current_time = time.time()

        # 如果最近有鼠标移动，认为在拖动
        if current_time - self._last_mouse_move_time < 0.5:  # 500ms内有鼠标移动
            if not self._is_dragging:
                self._is_dragging = True
                self._update_paused = True
                logger.debug("检测到拖动，暂停更新")
        else:
            if self._is_dragging:
                self._is_dragging = False
                self._update_paused = False
                logger.debug("拖动结束，恢复更新")

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 用于检测拖动"""
        import time
        self._last_mouse_move_time = time.time()
        super().mouseMoveEvent(event)

    def resizeEvent(self, event):
        """窗口大小变化事件 - 暂停更新避免卡顿"""
        self._update_paused = True
        # 延迟恢复更新
        QTimer.singleShot(500, self._resume_updates)
        super().resizeEvent(event)

    def _resume_updates(self):
        """恢复更新"""
        self._update_paused = False

    @pyqtSlot(dict)
    def _handle_async_data(self, data):
        """处理异步获取的数据"""
        try:
            if 'system_metrics' in data:
                cache_key = 'system_metrics'
                self._data_cache[cache_key] = data['system_metrics']
                if self.current_tab_index == 0:  # 只在当前显示系统监控tab时更新UI
                    self.system_tab.update_data(data['system_metrics'])

            elif 'ui_stats' in data:
                cache_key = 'ui_stats'
                self._data_cache[cache_key] = data['ui_stats']
                if self.current_tab_index == 1:  # 只在当前显示UI优化tab时更新UI
                    self.ui_tab.update_data(data['ui_stats'])

            elif 'algo_stats' in data:
                cache_key = 'algo_stats'
                self._data_cache[cache_key] = data['algo_stats']
                if self.current_tab_index == 3:  # 只在当前显示算法性能tab时更新UI
                    self.algorithm_tab.update_data(data['algo_stats'])

            elif 'tuning_stats' in data:
                cache_key = 'tuning_stats'
                self._data_cache[cache_key] = data['tuning_stats']
                if self.current_tab_index == 4:  # 只在当前显示自动调优tab时更新UI
                    self.tuning_tab.update_data(data['tuning_stats'])

            logger.debug(f"✅ 异步数据处理完成: {data}")

        except Exception as e:
            logger.error(f"处理异步数据失败 ({data}): {e}")

    @pyqtSlot(str)
    def _handle_async_error(self, error_message):
        """处理异步数据获取错误"""
        logger.warning(f"⚠️ 异步数据获取失败: {error_message}")

    def _should_update_cache(self, cache_key: str, cache_duration_seconds: int) -> bool:
        """检查是否需要更新缓存"""
        if cache_key not in self._last_update_time:
            return True

        last_update = self._last_update_time[cache_key]
        current_time = QDateTime.currentDateTime()

        return last_update.secsTo(current_time) >= cache_duration_seconds

    @pyqtSlot()
    def refresh_data(self):
        """手动刷新数据"""
        self.update_all_data()
        self.status_message.setText("数据已刷新")
        QTimer.singleShot(3000, lambda: self.status_message.setText("就绪"))

    def update_all_data(self):
        """更新所有数据"""
        # 清空缓存强制更新
        self._data_cache.clear()
        self._last_update_time.clear()
        self.update_current_tab_data_async()

    @pyqtSlot()
    def export_report(self):
        """导出报告"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出性能报告", f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON files (*.json)")
            if filename:
                report_data = {"timestamp": datetime.now().isoformat(), "status": "exported"}
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, ensure_ascii=False, indent=2)
                self.status_message.setText("报告已导出")
                QTimer.singleShot(3000, lambda: self.status_message.setText("就绪"))
        except Exception as e:
            logger.error(f"导出报告失败: {e}")

    @pyqtSlot()
    def clear_data(self):
        """清空数据"""
        try:
            if hasattr(self.strategy_tab, 'returns_chart') and self.strategy_tab.returns_chart:
                self.strategy_tab.returns_chart.clear_data()
            if hasattr(self.strategy_tab, 'risk_chart') and self.strategy_tab.risk_chart:
                self.strategy_tab.risk_chart.clear_data()
            self.status_message.setText("数据已清空")
            QTimer.singleShot(3000, lambda: self.status_message.setText("就绪"))
        except Exception as e:
            logger.error(f"清空数据失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        self.refresh_timer.stop()

        # 等待所有异步任务完成
        self.thread_pool.waitForDone(3000)  # 最多等待3秒

        event.accept()

    def on_tab_changed(self, index):
        """tab切换时的处理 - 优化性能"""
        self.current_tab_index = index
        logger.info(f"切换到tab: {index}")

        # 立即异步更新当前tab的数据
        QTimer.singleShot(100, lambda: self.update_current_tab_data_async())

    def force_update_all_data(self):
        """强制更新所有数据 - 忽略缓存"""
        try:
            # 清空缓存
            self._data_cache.clear()
            self._last_update_time.clear()

            # 强制更新当前tab
            self.update_current_tab_data_async()

            logger.info("强制更新所有数据完成")

        except Exception as e:
            logger.error(f"强制更新失败: {e}")

    def _setup_style_protection(self):
        """🚨 设置样式表保护机制，防止界面变白"""
        try:
            # 保存原始样式表
            self._original_stylesheet = self.styleSheet()

            # 设置定时器定期检查样式表
            self._style_check_timer = QTimer(self)
            self._style_check_timer.timeout.connect(self._check_and_restore_styles)
            self._style_check_timer.start(5000)  # 每5秒检查一次

            # 保存关键组件的样式
            self._backup_styles = {}
            if hasattr(self, 'tab_widget'):
                self._backup_styles['tab_widget'] = self.tab_widget.styleSheet()
            if hasattr(self, 'toolbar'):
                self._backup_styles['toolbar'] = self.toolbar.styleSheet()
            if hasattr(self, 'status_bar'):
                self._backup_styles['status_bar'] = self.status_bar.styleSheet()

            logger.debug("样式表保护机制已启动")

        except Exception as e:
            logger.error(f"设置样式表保护失败: {e}")

    def _check_and_restore_styles(self):
        """检查并恢复样式表"""
        try:
            # 检查主窗口样式
            current_style = self.styleSheet()
            if not current_style or len(current_style.strip()) < 100:
                logger.warning("检测到样式表丢失，正在恢复...")
                if self._original_stylesheet:
                    self.setStyleSheet(self._original_stylesheet)
                    logger.info("主窗口样式表已恢复")

            # 检查关键组件样式
            for component_name, backup_style in self._backup_styles.items():
                if hasattr(self, component_name):
                    component = getattr(self, component_name)
                    if component and backup_style:
                        current_component_style = component.styleSheet()
                        if not current_component_style or len(current_component_style.strip()) < 10:
                            component.setStyleSheet(backup_style)
                            logger.info(f"{component_name} 样式表已恢复")

        except Exception as e:
            logger.error(f"检查样式表时出错: {e}")

    def force_refresh_ui(self):
        """🚨 强制刷新UI，解决界面变白问题"""
        try:
            logger.info("开始强制刷新UI...")

            # 1. 恢复样式表
            if hasattr(self, '_original_stylesheet') and self._original_stylesheet:
                self.setStyleSheet(self._original_stylesheet)
                logger.info("已恢复主窗口样式表")

            # 2. 强制重绘所有组件
            self.repaint()
            if hasattr(self, 'tab_widget'):
                self.tab_widget.repaint()
            if hasattr(self, 'toolbar'):
                self.toolbar.repaint()
            if hasattr(self, 'status_bar'):
                self.status_bar.repaint()

            # 3. 更新当前标签页
            if hasattr(self, 'tab_widget'):
                current_index = self.tab_widget.currentIndex()
                current_widget = self.tab_widget.currentWidget()
                if current_widget:
                    current_widget.repaint()
                    # 如果有update方法，调用它
                    if hasattr(current_widget, 'update'):
                        current_widget.update()

            # 4. 强制处理所有待处理的事件
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

            logger.info("UI强制刷新完成")

        except Exception as e:
            logger.error(f"强制刷新UI失败: {e}")

    def start_immediate_update(self):
        """启动立即更新"""
        # 立即执行一次更新
        self.update_current_tab_data_async()

        # 重启定时器
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
            self.refresh_timer.start(3000)
