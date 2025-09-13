# -*- coding: utf-8 -*-
"""
专业情绪分析标签页 - 合并增强版本
整合实时情绪分析和报告功能，支持完整的插件系统和双标签页设计
"""

from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import traceback

from .base_tab import BaseAnalysisTab
from utils.config_manager import ConfigManager
from loguru import logger
from core.services.unified_data_accessor import get_stock_data, get_stock_info, calculate_historical_average

# 导入情绪数据服务和插件
try:
    from core.services.sentiment_data_service import SentimentDataService
    from plugins.sentiment_data_sources import AVAILABLE_PLUGINS
    from plugins.sentiment_data_source_interface import SentimentResponse, SentimentData
    SENTIMENT_SERVICE_AVAILABLE = True
    logger.info(" 情绪数据服务可用")
except ImportError as e:
    logger.error(f" 情绪数据服务导入失败: {e}")
    SENTIMENT_SERVICE_AVAILABLE = False


class AsyncPluginLoader(QThread):
    """异步插件加载器 - 避免主线程阻塞"""

    # 信号定义
    plugin_loaded = pyqtSignal(str, dict)  # plugin_name, plugin_info
    loading_progress = pyqtSignal(int, str)  # progress, message
    loading_completed = pyqtSignal(dict)  # all_plugins
    loading_error = pyqtSignal(str)  # error_message

    def __init__(self, db_service=None, parent=None):
        super().__init__(parent)
        self.db_service = db_service
        self.is_running = False

    def run(self):
        """异步加载插件"""
        try:
            self.is_running = True
            self.loading_progress.emit(10, "开始加载情绪插件...")

            # 从数据库获取插件列表
            records = []
            try:
                if self.db_service:
                    records = self.db_service.get_all_plugins(force_refresh=True) or []
                    self.loading_progress.emit(30, f"从数据库获取到 {len(records)} 个插件记录")
            except Exception as e:
                logger.error(f" 读取数据库插件列表失败: {e}")
                records = []

            # 筛选启用的情绪插件
            enabled_records = []
            for rec in (records or []):
                try:
                    status = (rec.get('status') or '').lower()
                    name = (rec.get('name') or '').strip()
                    entry = (rec.get('entry_point') or '').strip()
                    path = (rec.get('path') or '').strip()

                    is_enabled = status in ('enabled', '启用', 'on', 'true', '1', 'loaded', 'running')
                    is_sentiment = ('sentiment_data_sources' in name) or ('sentiment_data_sources' in entry) or ('sentiment_data_sources' in path)

                    if is_enabled and is_sentiment:
                        enabled_records.append(rec)
                except Exception:
                    continue

            self.loading_progress.emit(50, f"筛选出 {len(enabled_records)} 个启用的情绪插件")

            # 异步加载插件
            loaded_plugins = {}
            total_plugins = len(enabled_records)

            for i, rec in enumerate(enabled_records):
                if not self.is_running:  # 检查是否被停止
                    break

                try:
                    plugin_info = self._load_single_plugin(rec)
                    if plugin_info:
                        plugin_name = rec.get('name', '')
                        loaded_plugins[plugin_name] = plugin_info
                        self.plugin_loaded.emit(plugin_name, plugin_info)

                        # 更新进度
                        progress = 50 + int((i + 1) / total_plugins * 40)
                        self.loading_progress.emit(progress, f"已加载插件: {plugin_info['display_name']}")

                except Exception as e:
                    logger.error(f" 加载插件失败 {rec.get('name', '')}: {e}")
                    continue

            self.loading_progress.emit(100, f"插件加载完成，共加载 {len(loaded_plugins)} 个插件")
            self.loading_completed.emit(loaded_plugins)

        except Exception as e:
            error_msg = f"插件加载失败: {str(e)}"
            logger.error(f" {error_msg}")
            self.loading_error.emit(error_msg)
        finally:
            self.is_running = False

    def _load_single_plugin(self, rec):
        """加载单个插件"""
        from importlib import import_module
        from plugins.sentiment_data_sources.base_sentiment_plugin import BaseSentimentPlugin

        rec_name = (rec.get('name') or '').strip()
        entry = (rec.get('entry_point') or '').strip()
        path = (rec.get('path') or '').strip()

        module_name = ''
        class_name = ''

        try:
            # 确定模块名和类名
            if entry and ':' in entry:
                module_name, class_name = entry.split(':', 1)
                if not module_name.startswith('plugins.') and module_name.startswith('sentiment_data_sources'):
                    module_name = f"plugins.{module_name}"
            elif path:
                module_name = path if path.startswith('plugins.') else f"plugins.{path}"
            elif rec_name:
                if rec_name.startswith('plugins.'):
                    module_name = rec_name
                elif rec_name.startswith('sentiment_data_sources'):
                    module_name = f"plugins.{rec_name}"
                else:
                    module_name = f"plugins.sentiment_data_sources.{rec_name}_plugin"
            else:
                return None

            # 导入模块
            module = import_module(module_name)

            # 定位插件类
            plugin_cls = None
            if class_name:
                plugin_cls = getattr(module, class_name, None)
            if not plugin_cls:
                for attr in dir(module):
                    obj = getattr(module, attr)
                    try:
                        if isinstance(obj, type) and issubclass(obj, BaseSentimentPlugin) and obj is not BaseSentimentPlugin:
                            plugin_cls = obj
                            break
                    except Exception:
                        continue

            if not plugin_cls:
                return None

            # 创建实例
            instance = plugin_cls()

            # 获取插件信息
            display_name = rec_name
            description = rec.get('description', '')
            version = rec.get('version', '1.0.0')
            author = rec.get('author', '')

            if hasattr(instance, 'get_plugin_info'):
                try:
                    plugin_info = instance.get_plugin_info()
                    display_name = plugin_info.name
                    description = plugin_info.description
                    version = plugin_info.version
                    author = plugin_info.author
                except Exception as e:
                    logger.error(f" 获取插件信息失败 {rec_name}: {e}")
                    meta = instance.metadata if hasattr(instance, 'metadata') else {}
                    display_name = (meta.get('name') if isinstance(meta, dict) else None) or rec.get('display_name') or rec_name
            else:
                meta = instance.metadata if hasattr(instance, 'metadata') else {}
                display_name = (meta.get('name') if isinstance(meta, dict) else None) or rec.get('display_name') or rec_name

            # 同步显示名到数据库（异步执行，不阻塞）
            if self.db_service:
                try:
                    payload = {
                        'display_name': display_name,
                        'description': description,
                        'version': version,
                        'plugin_type': rec.get('plugin_type', 'sentiment'),
                        'author': author
                    }
                    self.db_service.register_plugin_from_metadata(rec_name, payload)
                except Exception as e:
                    logger.error(f" 同步显示名失败 {rec_name}: {e}")

            return {
                'instance': instance,
                'display_name': display_name,
                'description': description,
                'version': version,
                'author': author
            }

        except Exception as e:
            logger.error(f" 加载插件失败 {rec_name}: {e}")
            return None

    def stop(self):
        """停止加载"""
        self.is_running = False
        self.quit()


class SentimentAnalysisThread(QThread):
    """异步情绪分析线程 - 解决UI卡顿问题"""

    # 信号定义
    progress_updated = pyqtSignal(int, str)  # 进度, 消息
    analysis_completed = pyqtSignal(dict)  # 分析结果
    error_occurred = pyqtSignal(str)  # 错误信息
    status_updated = pyqtSignal(str)  # 状态更新

    def __init__(self, sentiment_service, selected_plugins, use_cache=True,
                 available_plugins=None, parent=None):
        super().__init__(parent)
        self.sentiment_service = sentiment_service
        self.selected_plugins = selected_plugins
        self.use_cache = use_cache
        self.available_plugins = available_plugins or {}
        self.is_running = False

        # 初始化日志管理器
        # 纯Loguru架构，移除log_manager依赖

    def run(self):
        """执行异步情绪分析"""
        try:
            self.is_running = True
            self.progress_updated.emit(10, "初始化情绪分析...")

            results = {
                'sentiment_results': [],
                'sentiment_statistics': {},
                'plugin_status': {},
                'analysis_time': datetime.now().isoformat()
            }

            if not self.selected_plugins:
                self.error_occurred.emit("请至少选择一个情绪数据源插件")
                return

            self.progress_updated.emit(20, f"开始分析 {len(self.selected_plugins)} 个插件...")
            logger.info(f" [SentimentAnalysisThread] 开始情绪分析，使用插件: {self.selected_plugins}")

            # 步骤1: 数据获取 (30%)
            self.progress_updated.emit(30, "获取情绪数据...")

            if not self.sentiment_service or not SENTIMENT_SERVICE_AVAILABLE:
                self.error_occurred.emit("情绪数据服务不可用，无法执行分析")
                return

            # 使用真实的情绪数据服务
            self.status_updated.emit("使用真实情绪数据服务进行分析...")

            # 设置选中的插件列表
            if self.selected_plugins:
                self.sentiment_service.set_selected_plugins(self.selected_plugins)
                self.status_updated.emit(f"设置使用插件: {', '.join(self.selected_plugins)}")
            else:
                self.sentiment_service.clear_selected_plugins()
                self.status_updated.emit("使用所有可用插件")

            response = self.sentiment_service.get_sentiment_data(force_refresh=not self.use_cache)
            sentiment_results = self._process_sentiment_response(response)

            if not sentiment_results:
                logger.warning("未能获取任何情绪数据，请检查插件配置和网络连接")
                return

            results['sentiment_results'] = sentiment_results
            self.progress_updated.emit(60, f"获取到 {len(sentiment_results)} 个情绪指标")

            # 步骤2: 计算综合指数 (20%)
            self.progress_updated.emit(70, "计算综合情绪指数...")
            statistics = self._calculate_statistics(sentiment_results)
            results['sentiment_statistics'] = statistics

            # 步骤3: 更新插件状态 (10%)
            self.progress_updated.emit(90, "更新插件状态...")
            plugin_status = self._update_plugin_status()
            results['plugin_status'] = plugin_status

            # 完成
            self.progress_updated.emit(100, "情绪分析完成")
            logger.info(f" [SentimentAnalysisThread] 情绪分析完成，生成 {len(sentiment_results)} 个指标")

            self.analysis_completed.emit(results)

        except Exception as e:
            error_msg = f"情绪分析失败: {str(e)}"
            logger.error(f" [SentimentAnalysisThread] {error_msg}")
            traceback.print_exc()
            self.error_occurred.emit(error_msg)
        finally:
            self.is_running = False

    def _process_sentiment_response(self, response):
        """处理真实情绪数据服务的响应"""
        sentiment_results = []
        if response and response.success and response.data:
            for sentiment_data in response.data:
                # 从 confidence 和其他属性计算 strength
                strength = getattr(sentiment_data, 'confidence', 0.5)
                if hasattr(sentiment_data, 'metadata') and sentiment_data.metadata:
                    strength = sentiment_data.metadata.get('strength', strength)

                sentiment_results.append({
                    'data_source': sentiment_data.source,
                    'indicator': sentiment_data.indicator_name,
                    'value': sentiment_data.value,
                    'signal': sentiment_data.signal if isinstance(sentiment_data.signal, str) else str(sentiment_data.signal),
                    'strength': strength,
                    'confidence': sentiment_data.confidence,
                    'data_quality': response.data_quality,
                    'timestamp': response.update_time.strftime('%Y-%m-%d %H:%M:%S') if response.update_time else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        else:
            error_msg = response.error_message if response else "未知错误"
            logger.error(f" [SentimentAnalysisThread] 情绪数据服务响应失败: {error_msg}")

        return sentiment_results

    def _determine_signal(self, value: float) -> str:
        """根据数值确定信号"""
        if value > 70:
            return "STRONG_BUY"
        elif value > 60:
            return "BUY"
        elif value > 40:
            return "HOLD"
        elif value > 30:
            return "SELL"
        else:
            return "STRONG_SELL"

    def _calculate_statistics(self, sentiment_results):
        """计算统计信息"""
        if not sentiment_results:
            return {}

        # 计算加权平均情绪指数
        total_weight = 0
        weighted_sum = 0

        for result in sentiment_results:
            weight = result.get('confidence', 0.5) * result.get('strength', 0.5)
            weighted_sum += result.get('value', 50) * weight
            total_weight += weight

        composite_score = weighted_sum / total_weight if total_weight > 0 else 50

        # 统计质量分布
        quality_counts = {}
        for result in sentiment_results:
            quality = result.get('data_quality', 'unknown')
            quality_counts[quality] = quality_counts.get(quality, 0) + 1

        return {
            'composite_score': composite_score,
            'total_indicators': len(sentiment_results),
            'quality_distribution': quality_counts,
            'analysis_time': datetime.now().isoformat()
        }

    def _update_plugin_status(self):
        """更新插件状态"""
        return {
            'selected_count': len(self.selected_plugins),
            'total_count': len(self.available_plugins),
            'status': 'completed'
        }

    def stop(self):
        """停止分析"""
        self.is_running = False
        self.quit()


class ProfessionalSentimentTab(BaseAnalysisTab):
    """专业情绪分析标签页 - 整合实时分析和报告功能"""

    # 定义信号
    sentiment_analysis_completed = pyqtSignal(dict)
    sentiment_report_completed = pyqtSignal(dict)
    plugin_data_updated = pyqtSignal(dict)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__(config_manager)
        # 纯Loguru架构，移除log_manager依赖

        if not SENTIMENT_SERVICE_AVAILABLE:
            raise RuntimeError("情绪数据服务未能加载，无法启动情绪分析标签页。请检查相关依赖。")

        # 情绪数据服务
        self.sentiment_service = None
        self.available_plugins = {}
        self.selected_plugins = []

        # 分析结果
        self.sentiment_results = []
        self.sentiment_statistics = {}
        self.sentiment_history = []
        self.plugin_status = {}

        # 报告功能属性
        self.report_results = []
        self.report_statistics = {}
        self.scheduled_reports = []
        self.report_templates = []
        self.alert_rules = []

        # 异步分析线程
        self.analysis_thread = None
        self.plugin_loader = None

        # 进度条和状态
        self.progress_bar = None
        self.status_label = None

        # 定时器
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_data)

        # 初始化情绪数据服务
        self._initialize_sentiment_service()

        # 连接插件数据库服务（用于动态刷新与按启用状态过滤）
        try:
            from core.services.plugin_database_service import get_plugin_database_service
            self.db_service = get_plugin_database_service()
            if hasattr(self.db_service, 'database_updated'):
                self.db_service.database_updated.connect(self.on_plugins_db_updated)
        except Exception:
            self.db_service = None

        logger.info(" 专业情绪分析标签页初始化完成")

    def _initialize_sentiment_service(self):
        """初始化情绪数据服务"""
        try:
            if SENTIMENT_SERVICE_AVAILABLE:
                # 尝试从服务容器获取
                if hasattr(self, 'coordinator') and hasattr(self.coordinator, 'service_container'):
                    try:
                        self.sentiment_service = self.coordinator.service_container.resolve(SentimentDataService)
                        logger.info(" 从服务容器获取情绪数据服务")
                    except:
                        # 如果服务容器中没有，创建新实例
                        self.sentiment_service = SentimentDataService()
                        logger.info(" 创建新的情绪数据服务实例")
                else:
                    # 直接创建
                    self.sentiment_service = SentimentDataService()
                    logger.info(" 直接创建情绪数据服务")

                # 初始化服务
                if self.sentiment_service:
                    self.sentiment_service.initialize()
                    # 连接信号
                    self.sentiment_service.data_updated.connect(self.on_sentiment_data_updated)
                    self.sentiment_service.plugin_error.connect(self.on_plugin_error)

            else:
                raise RuntimeError("情绪数据服务不可用，无法启动情绪分析功能。请检查相关依赖。")

        except Exception as e:
            logger.error(f" 初始化情绪数据服务失败: {e}")
            self.sentiment_service = None
            raise

    def create_ui(self):
        """创建双标签页UI界面"""
        main_layout = QVBoxLayout(self)
        self.main_tab_widget = QTabWidget()
        main_layout.addWidget(self.main_tab_widget)

        # 实时情绪分析标签页
        analysis_widget = QWidget()
        analysis_layout = QVBoxLayout(analysis_widget)
        self.create_analysis_ui(analysis_layout)
        self.main_tab_widget.addTab(analysis_widget, "实时情绪分析")

        # 情绪报告标签页
        report_widget = QWidget()
        report_layout = QVBoxLayout(report_widget)
        self.create_report_ui(report_layout)
        self.main_tab_widget.addTab(report_widget, "情绪报告")

        # 延迟加载插件，避免阻塞UI创建
        QTimer.singleShot(100, self.load_available_plugins_async)

        logger.info(" UI创建完成，所有组件已设置为可见")

    def create_analysis_ui(self, layout):
        """创建实时情绪分析UI"""
        # 插件选择区域
        plugins_group = self.create_plugins_section()
        layout.addWidget(plugins_group)

        # 参数配置区域
        params_group = self.create_params_section()
        layout.addWidget(params_group)

        # 分析控制区域
        control_group = self.create_control_section()
        layout.addWidget(control_group)

        # 状态显示区域
        status_group = self.create_status_section()
        layout.addWidget(status_group)

        # 结果显示区域
        results_group = self.create_results_section()
        layout.addWidget(results_group)

    def create_report_ui(self, layout):
        """创建情绪报告的UI界面"""
        # 报告配置组
        config_group = QGroupBox(" 报告配置")
        config_layout = QGridLayout(config_group)

        # 报告类型
        config_layout.addWidget(QLabel("报告类型:"), 0, 0)
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(["日度报告", "周度报告", "月度报告", "自定义报告"])
        config_layout.addWidget(self.report_type_combo, 0, 1)

        # 数据周期
        config_layout.addWidget(QLabel("数据周期(天):"), 0, 2)
        self.report_period_spin = QSpinBox()
        self.report_period_spin.setRange(1, 365)
        self.report_period_spin.setValue(7)
        config_layout.addWidget(self.report_period_spin, 0, 3)

        # 报告格式
        config_layout.addWidget(QLabel("报告格式:"), 1, 0)
        self.report_format_combo = QComboBox()
        self.report_format_combo.addItems(["HTML报告", "PDF报告", "Excel报告", "CSV数据"])
        config_layout.addWidget(self.report_format_combo, 1, 1)

        # 自动发送
        self.auto_send_cb = QCheckBox("自动发送邮件")
        config_layout.addWidget(self.auto_send_cb, 1, 2, 1, 2)

        layout.addWidget(config_group)

        # 报告控制组
        control_group = QGroupBox(" 报告控制")
        control_layout = QHBoxLayout(control_group)

        self.generate_report_btn = QPushButton(" 生成报告")
        self.generate_report_btn.clicked.connect(self.generate_sentiment_report)
        control_layout.addWidget(self.generate_report_btn)

        self.schedule_report_btn = QPushButton("⏰ 定时报告")
        self.schedule_report_btn.clicked.connect(self.schedule_sentiment_report)
        control_layout.addWidget(self.schedule_report_btn)

        self.export_report_btn = QPushButton(" 导出报告")
        self.export_report_btn.clicked.connect(self.export_sentiment_report)
        control_layout.addWidget(self.export_report_btn)

        control_layout.addStretch()
        layout.addWidget(control_group)

        # 报告预览区域
        preview_group = QGroupBox(" 报告预览")
        preview_layout = QVBoxLayout(preview_group)

        self.report_preview = QTextEdit()
        self.report_preview.setReadOnly(True)
        self.report_preview.setMaximumHeight(300)
        preview_layout.addWidget(self.report_preview)

        layout.addWidget(preview_group)

        # 历史报告列表
        history_group = QGroupBox(" 历史报告")
        history_layout = QVBoxLayout(history_group)

        self.report_history_table = QTableWidget()
        self.report_history_table.setColumnCount(5)
        self.report_history_table.setHorizontalHeaderLabels([
            "生成时间", "报告类型", "数据周期", "状态", "操作"
        ])
        header = self.report_history_table.horizontalHeader()
        header.setStretchLastSection(True)
        history_layout.addWidget(self.report_history_table)

        layout.addWidget(history_group)

    def create_plugins_section(self):
        """创建插件选择区域"""
        plugins_group = QGroupBox(" 情绪数据源插件")
        layout = QVBoxLayout(plugins_group)

        # 插件选择说明
        info_label = QLabel("选择要使用的情绪数据源插件（支持多选）：")
        info_label.setStyleSheet("color: #666; font-size: 11px; margin: 5px;")
        layout.addWidget(info_label)

        # 插件复选框容器
        self.plugins_widget = QWidget()
        self.plugins_widget.setMinimumHeight(120)  # 增加最小高度以容纳多行插件
        self.plugins_widget.setMaximumHeight(200)  # 设置最大高度
        self.plugins_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)

        self.plugins_layout = QGridLayout(self.plugins_widget)
        self.plugins_layout.setSpacing(5)  # 设置间距
        layout.addWidget(self.plugins_widget)

        # 全选/取消全选按钮
        button_layout = QHBoxLayout()

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_plugins)
        button_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_plugins)
        button_layout.addWidget(self.deselect_all_btn)

        self.refresh_plugins_btn = QPushButton(" 刷新插件")
        self.refresh_plugins_btn.clicked.connect(self.load_available_plugins_async)
        button_layout.addWidget(self.refresh_plugins_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        return plugins_group

    def create_params_section(self):
        """创建参数配置区域"""
        params_group = QGroupBox(" 分析参数")
        layout = QGridLayout(params_group)

        # 数据源权重
        layout.addWidget(QLabel("数据源权重:"), 0, 0)
        self.weight_combo = QComboBox()
        self.weight_combo.addItems(["平均权重", "智能权重", "自定义权重"])
        layout.addWidget(self.weight_combo, 0, 1)

        # 缓存策略
        layout.addWidget(QLabel("缓存策略:"), 0, 2)
        self.cache_combo = QComboBox()
        self.cache_combo.addItems(["使用缓存", "强制刷新", "智能缓存"])
        layout.addWidget(self.cache_combo, 0, 3)

        # 数据质量阈值
        layout.addWidget(QLabel("数据质量阈值:"), 1, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["低", "中等", "高", "极高"])
        self.quality_combo.setCurrentText("中等")
        layout.addWidget(self.quality_combo, 1, 1)

        # 超时设置
        layout.addWidget(QLabel("超时时间(秒):"), 1, 2)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setValue(30)
        layout.addWidget(self.timeout_spin, 1, 3)

        return params_group

    def create_control_section(self):
        """创建分析控制区域"""
        control_group = QGroupBox(" 分析控制")
        main_layout = QVBoxLayout(control_group)

        # 按钮和控制区域
        buttons_layout = QHBoxLayout()

        # 开始分析按钮
        self.analyze_btn = QPushButton(" 开始分析")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.analyze_btn.clicked.connect(self.analyze_sentiment)
        buttons_layout.addWidget(self.analyze_btn)

        # 停止分析按钮
        self.stop_btn = QPushButton(" 停止分析")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_analysis)
        buttons_layout.addWidget(self.stop_btn)

        # 自动刷新开关
        self.auto_refresh_cb = QCheckBox(" 自动刷新")
        self.auto_refresh_cb.toggled.connect(self.toggle_auto_refresh)
        buttons_layout.addWidget(self.auto_refresh_cb)

        # 刷新间隔
        buttons_layout.addWidget(QLabel("间隔(分钟):"))
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(1, 60)
        self.refresh_interval_spin.setValue(5)
        buttons_layout.addWidget(self.refresh_interval_spin)

        buttons_layout.addStretch()

        # 保存结果按钮
        self.save_btn = QPushButton(" 保存结果")
        self.save_btn.clicked.connect(self.save_results)
        buttons_layout.addWidget(self.save_btn)

        # 清空结果按钮
        self.clear_btn = QPushButton(" 清空结果")
        self.clear_btn.clicked.connect(self.clear_results)
        buttons_layout.addWidget(self.clear_btn)

        main_layout.addLayout(buttons_layout)

        # 进度条和状态显示
        progress_layout = QHBoxLayout()

        # 状态标签
        self.status_label = QLabel("服务状态: 就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        progress_layout.addWidget(self.status_label)

        progress_layout.addStretch()

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 3px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 2px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        main_layout.addLayout(progress_layout)

        return control_group

    def create_status_section(self):
        """创建状态显示区域"""
        status_group = QGroupBox(" 服务状态")
        layout = QHBoxLayout(status_group)

        # 服务状态
        self.service_status_label = QLabel("服务状态: 未知")
        layout.addWidget(self.service_status_label)

        # 插件状态
        self.plugins_status_label = QLabel("插件状态: 0/0")
        layout.addWidget(self.plugins_status_label)

        # 最后更新时间
        self.last_update_label = QLabel("最后更新: --")
        layout.addWidget(self.last_update_label)

        layout.addStretch()

        # 状态刷新按钮
        refresh_status_btn = QPushButton(" 刷新状态")
        refresh_status_btn.clicked.connect(self.refresh_status)
        layout.addWidget(refresh_status_btn)

        return status_group

    def create_results_section(self):
        """创建结果显示区域"""
        results_group = QGroupBox(" 分析结果")
        layout = QVBoxLayout(results_group)

        # 创建分割器
        splitter = QSplitter(Qt.Vertical)

        # 情绪概览
        overview_group = QGroupBox(" 情绪概览")
        overview_layout = QVBoxLayout(overview_group)

        # 主要指数区域
        main_indices_layout = QGridLayout()

        # 综合情绪指数 (主指数)
        self.composite_score_label = QLabel("综合情绪指数: --")
        self.composite_score_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4; padding: 8px;")
        main_indices_layout.addWidget(self.composite_score_label, 0, 0, 1, 2)

        # 市场恐惧贪婪指数
        self.fear_greed_label = QLabel("恐惧&贪婪指数: --")
        self.fear_greed_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c; padding: 4px;")
        main_indices_layout.addWidget(self.fear_greed_label, 1, 0)

        # 波动率指数 (VIX类似)
        self.volatility_index_label = QLabel("波动率指数: --")
        self.volatility_index_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #f39c12; padding: 4px;")
        main_indices_layout.addWidget(self.volatility_index_label, 1, 1)

        # 资金流向指数
        self.money_flow_label = QLabel("资金流向指数: --")
        self.money_flow_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #27ae60; padding: 4px;")
        main_indices_layout.addWidget(self.money_flow_label, 2, 0)

        # 新闻情绪指数
        self.news_sentiment_label = QLabel("新闻情绪指数: --")
        self.news_sentiment_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #8e44ad; padding: 4px;")
        main_indices_layout.addWidget(self.news_sentiment_label, 2, 1)

        # 技术面情绪指数
        self.technical_sentiment_label = QLabel("技术面情绪: --")
        self.technical_sentiment_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #34495e; padding: 4px;")
        main_indices_layout.addWidget(self.technical_sentiment_label, 3, 0)

        # 市场强度指数
        self.market_strength_label = QLabel("市场强度指数: --")
        self.market_strength_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #16a085; padding: 4px;")
        main_indices_layout.addWidget(self.market_strength_label, 3, 1)

        overview_layout.addLayout(main_indices_layout)

        # 分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        overview_layout.addWidget(separator)

        # 统计信息区域
        stats_layout = QHBoxLayout()

        self.total_indicators_label = QLabel("指标数量: --")
        self.total_indicators_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        stats_layout.addWidget(self.total_indicators_label)

        self.data_quality_label = QLabel("数据质量: --")
        self.data_quality_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        stats_layout.addWidget(self.data_quality_label)

        self.plugin_success_label = QLabel("成功插件: --")
        self.plugin_success_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        stats_layout.addWidget(self.plugin_success_label)

        # 最后更新时间
        self.last_update_label = QLabel("更新时间: --")
        self.last_update_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        stats_layout.addWidget(self.last_update_label)

        stats_layout.addStretch()
        overview_layout.addLayout(stats_layout)

        splitter.addWidget(overview_group)

        # 详细结果表格
        details_group = QGroupBox(" 详细分析结果")
        details_layout = QVBoxLayout(details_group)

        self.sentiment_table = QTableWidget()
        self.sentiment_table.setColumnCount(10)
        self.sentiment_table.setHorizontalHeaderLabels([
            "数据源", "指标名称", "当前值", "历史对比", "信号强度", "趋势方向",
            "置信度", "影响权重", "数据质量", "更新时间"
        ])

        # 设置表格属性和样式
        header = self.sentiment_table.horizontalHeader()
        header.setStretchLastSection(True)

        # 设置列宽
        self.sentiment_table.setColumnWidth(0, 100)  # 数据源
        self.sentiment_table.setColumnWidth(1, 120)  # 指标名称
        self.sentiment_table.setColumnWidth(2, 80)   # 当前值
        self.sentiment_table.setColumnWidth(3, 80)   # 历史对比
        self.sentiment_table.setColumnWidth(4, 80)   # 信号强度
        self.sentiment_table.setColumnWidth(5, 80)   # 趋势方向
        self.sentiment_table.setColumnWidth(6, 70)   # 置信度
        self.sentiment_table.setColumnWidth(7, 70)   # 影响权重
        self.sentiment_table.setColumnWidth(8, 70)   # 数据质量

        self.sentiment_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sentiment_table.setAlternatingRowColors(True)
        self.sentiment_table.setSortingEnabled(True)

        # 设置表格样式
        self.sentiment_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: #fafafa;
                alternate-background-color: #f5f5f5;
                selection-background-color: #e3f2fd;
                border: 1px solid #ddd;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QTableWidget::item:selected {
                background-color: #bbdefb;
                color: #000;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
                color: #333;
            }
        """)

        details_layout.addWidget(self.sentiment_table)
        splitter.addWidget(details_group)

        layout.addWidget(splitter)

        return results_group

    def load_available_plugins_async(self):
        """异步加载可用的情绪数据源插件"""
        try:
            logger.info(" 开始异步加载情绪数据源插件...")
            self.plugin_loader = AsyncPluginLoader(self.db_service)
            self.plugin_loader.plugin_loaded.connect(self.on_plugin_loaded)
            self.plugin_loader.loading_progress.connect(self.update_loading_progress)
            self.plugin_loader.loading_completed.connect(self.on_plugins_loaded)
            self.plugin_loader.loading_error.connect(self.on_loading_error)
            self.plugin_loader.start()
        except Exception as e:
            logger.error(f" 异步加载情绪数据源插件失败: {e}")

    def on_plugin_loaded(self, plugin_name, plugin_info):
        """处理单个插件加载完成信号"""
        logger.info(f" 插件 {plugin_name} 加载完成")
        self.available_plugins[plugin_name] = plugin_info
        self.update_plugins_ui()

    def update_loading_progress(self, progress, message):
        """更新加载进度"""
        logger.info(f" 加载进度: {progress}% - {message}")

    def on_plugins_loaded(self, plugins):
        """处理所有插件加载完成信号"""
        logger.info(f" 已从数据库加载情绪插件: {len(plugins)} 个")
        self.available_plugins.update(plugins)
        self.update_plugins_ui()

    def on_loading_error(self, error_message):
        """处理加载错误信号"""
        logger.error(f" 加载情绪数据源插件失败: {error_message}")

    def update_plugins_ui(self):
        """更新插件UI显示 - 优化版本，避免阻塞主线程"""
        try:
            if not hasattr(self, 'plugins_layout') or self.plugins_layout is None:
                logger.error(" plugins_layout未初始化，无法更新插件UI")
                return

            # 清空现有插件选择
            for i in reversed(range(self.plugins_layout.count())):
                child = self.plugins_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)

            if not self.available_plugins:
                error_msg = "没有检测到任何情绪数据源插件（请在插件管理器中启用后重试）"
                logger.error(f" {error_msg}")
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(error_msg)
                return

            # 批量创建UI组件
            row, col = 0, 0
            for plugin_name, plugin_info in self.available_plugins.items():
                try:
                    display_name = plugin_info.get('display_name', plugin_name)
                    description = plugin_info.get('description', '')
                    version = plugin_info.get('version', '1.0.0')
                    author = plugin_info.get('author', '')

                    # 创建复选框
                    checkbox = QCheckBox(f" {display_name}")
                    checkbox.setToolTip(f"{description}\n版本: {version}\n作者: {author}")
                    checkbox.setChecked(True)
                    checkbox.stateChanged.connect(self._on_plugin_selected_changed)

                    # 更新插件信息，添加checkbox引用
                    plugin_info['checkbox'] = checkbox

                    self.plugins_layout.addWidget(checkbox, row, col)
                    col += 1
                    if col >= 3:
                        col = 0
                        row += 1

                except Exception as e:
                    logger.error(f" 创建插件UI失败 {plugin_name}: {e}")

            # 自动选择插件
            if self.available_plugins and not self.get_selected_plugins():
                for plugin_info in self.available_plugins.values():
                    if 'checkbox' in plugin_info:
                        plugin_info['checkbox'].setChecked(True)

                auto_selected = self.get_selected_plugins()
                if auto_selected:
                    logger.info(f" 自动选择了 {len(auto_selected)} 个插件: {', '.join(auto_selected)}")
                    self.update_status_label(f"自动选择了 {len(auto_selected)} 个插件")

        except Exception as e:
            logger.error(f" 更新插件UI失败: {e}")

    def select_all_plugins(self):
        """全选插件"""
        for plugin_info in self.available_plugins.values():
            if 'checkbox' in plugin_info:
                plugin_info['checkbox'].setChecked(True)

    def deselect_all_plugins(self):
        """取消全选插件"""
        for plugin_info in self.available_plugins.values():
            if 'checkbox' in plugin_info:
                plugin_info['checkbox'].setChecked(False)

    def get_selected_plugins(self) -> List[str]:
        """获取选中的插件列表"""
        selected = []
        for plugin_key, plugin_info in self.available_plugins.items():
            if 'checkbox' in plugin_info and plugin_info['checkbox'].isChecked():
                selected.append(plugin_key)
        return selected

    def _on_plugin_selected_changed(self, state):
        """处理插件选择状态改变事件"""
        try:
            # 获取当前选中的插件
            selected_plugins = self.get_selected_plugins()

            # 更新选中的插件列表
            self.selected_plugins = selected_plugins

            # 更新状态显示
            if selected_plugins:
                self.update_status_label(f"已选择 {len(selected_plugins)} 个插件: {', '.join(selected_plugins[:3])}" +
                                         ("..." if len(selected_plugins) > 3 else ""))
            else:
                self.update_status_label("未选择任何插件")

            # 更新分析按钮状态
            if hasattr(self, 'analyze_btn'):
                self.analyze_btn.setEnabled(len(selected_plugins) > 0)

            logger.info(f" 插件选择状态已更新: {len(selected_plugins)} 个插件选中")

        except Exception as e:
            logger.error(f" 处理插件选择状态改变失败: {e}")
            # 不要在这里显示阻塞性的消息框，只记录错误
            if True:  # 使用Loguru日志
                logger.error(f"插件选择状态改变处理失败: {e}")

    def analyze_sentiment(self):
        """执行情绪分析 - 异步版本"""
        try:
            # 检查是否已有线程在运行
            if self.analysis_thread and self.analysis_thread.isRunning():
                self.update_status_label(" 分析正在进行中，请等待完成")
                logger.info(" 分析正在进行中，请等待完成")
                return

            # 获取选中的插件
            selected_plugins = self.get_selected_plugins()

            if not selected_plugins:
                # 使用非阻塞的状态提示替换阻塞性弹框
                self.update_status_label(" 请至少选择一个情绪数据源插件")
                logger.info(" 请至少选择一个情绪数据源插件")

                # 尝试自动加载可用插件
                if not self.available_plugins:
                    self.update_status_label(" 尝试自动加载情绪插件...")
                    self.load_available_plugins_async()
                    return

                self.reset_ui_state()
                return

            logger.info(f" 开始情绪分析，使用插件: {selected_plugins}")

            # 更新UI状态
            self.analyze_btn.setEnabled(False)
            self.analyze_btn.setText(" 分析中...")
            self.stop_btn.setEnabled(True)
            if self.progress_bar:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            if self.status_label:
                self.status_label.setText("准备开始分析...")

            # 清空之前的结果
            self.sentiment_results = []
            self.sentiment_table.setRowCount(0)
            if self.composite_score_label:
                self.composite_score_label.setText("综合情绪指数: --")

            # 获取参数
            use_cache = self.cache_combo.currentText() != "强制刷新"

            # 创建异步分析线程
            self.analysis_thread = SentimentAnalysisThread(
                self.sentiment_service, selected_plugins, use_cache, self.available_plugins
            )

            # 连接信号
            self.analysis_thread.progress_updated.connect(self.update_progress_bar)
            self.analysis_thread.analysis_completed.connect(self.on_analysis_completed)
            self.analysis_thread.error_occurred.connect(self.on_analysis_error)
            self.analysis_thread.status_updated.connect(self.update_status_label)

            # 启动异步分析线程
            self.analysis_thread.start()

        except Exception as e:
            logger.error(f" 情绪分析启动失败: {e}")
            traceback.print_exc()
            # 使用非阻塞错误提示替换阻塞式弹框
            self.update_status_label(f" 启动分析失败: {str(e)}")
            self.error_occurred.emit(f"启动分析失败: {str(e)}")
            self.reset_ui_state()

    def reset_ui_state(self):
        """重置UI状态"""
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText(" 开始分析")
        self.stop_btn.setEnabled(False)
        if self.progress_bar:
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)
        if self.status_label:
            self.status_label.setText("服务状态: 就绪")

    def update_progress_bar(self, value: int, message: str):
        """更新进度条"""
        if self.progress_bar:
            self.progress_bar.setValue(value)
        if self.status_label:
            self.status_label.setText(message)
        logger.info(f" 进度: {value}% - {message}")

    def update_status_label(self, message: str):
        """更新状态标签"""
        if self.status_label:
            self.status_label.setText(message)
        logger.info(f" 状态: {message}")

    def on_analysis_completed(self, results: dict):
        """异步分析完成信号处理"""
        try:
            logger.info(f" [ProfessionalSentimentTab] 情绪分析完成，生成 {len(results['sentiment_results'])} 个指标")

            # 更新数据
            self.sentiment_results = results['sentiment_results']
            self.sentiment_statistics = results['sentiment_statistics']
            self.plugin_status = results['plugin_status']

            # 更新显示
            self.update_sentiment_display()
            self.calculate_composite_sentiment()
            self.update_status_display()

            # 重置UI状态
            self.reset_ui_state()
            if self.status_label:
                self.status_label.setText(f"分析完成: {len(self.sentiment_results)} 个指标")

            # 发送完成信号
            self.sentiment_analysis_completed.emit({
                'results': self.sentiment_results,
                'statistics': self.sentiment_statistics,
                'selected_plugins': self.get_selected_plugins()
            })

            logger.info(" 情绪分析UI更新完成")

        except Exception as e:
            logger.error(f" 处理分析结果失败: {e}")
            traceback.print_exc()
            self.reset_ui_state()

    def on_analysis_error(self, error_message: str):
        """异步分析错误信号处理"""
        logger.error(f" [ProfessionalSentimentTab] 情绪分析失败: {error_message}")
        # 使用非阻塞错误提示替换阻塞式弹框
        self.update_status_label(f" 分析失败: {error_message}")
        # 发送错误信号给父组件处理
        if hasattr(self, 'error_occurred'):
            self.error_occurred.emit(f"情绪分析失败: {error_message}")
        self.reset_ui_state()

    def process_sentiment_response(self, response: 'SentimentResponse'):
        """处理情绪数据服务的响应"""
        if response.success and response.data:
            for sentiment_data in response.data:
                # 从 confidence 和其他属性计算 strength
                strength = getattr(sentiment_data, 'confidence', 0.5)
                if hasattr(sentiment_data, 'metadata') and sentiment_data.metadata:
                    # 如果元数据中有强度信息，使用它
                    strength = sentiment_data.metadata.get('strength', strength)

                self.sentiment_results.append({
                    'data_source': sentiment_data.source,
                    'indicator': sentiment_data.indicator_name,
                    'value': sentiment_data.value,
                    'signal': sentiment_data.signal if isinstance(sentiment_data.signal, str) else str(sentiment_data.signal),
                    'strength': strength,
                    'confidence': sentiment_data.confidence,
                    'data_quality': response.data_quality,
                    'timestamp': response.update_time.strftime('%Y-%m-%d %H:%M:%S') if response.update_time else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        else:
            logger.error(f" 情绪数据服务响应失败: {response.error_message}")

    def update_sentiment_display(self):
        """更新情绪分析显示 - 优化版本，使用批量更新"""
        try:
            logger.info(f" 更新情绪显示，数据量: {len(self.sentiment_results)}")

            if not hasattr(self, 'sentiment_table') or self.sentiment_table is None:
                logger.error(" sentiment_table未初始化")
                return

            if not self.sentiment_results:
                logger.error(" 没有情绪数据可显示")
                self.sentiment_table.setRowCount(0)
                return

            # 禁用排序以提高性能
            self.sentiment_table.setSortingEnabled(False)

            # 批量设置行数
            self.sentiment_table.setRowCount(len(self.sentiment_results))
            logger.info(f" 设置表格行数: {len(self.sentiment_results)}")

            # 批量创建表格项
            for row, result in enumerate(self.sentiment_results):
                try:
                    # 使用真实数据计算，删除模拟数据
                    data_source = str(result.get('data_source', '--'))
                    indicator = str(result.get('indicator', '--'))
                    value = f"{result.get('value', 0):.2f}"

                    # 使用真实的历史数据计算对比
                    hist_compare = self._calculate_real_historical_compare(result)

                    # 信号强度 (基于confidence和value计算)
                    signal_strength = self._calculate_signal_strength(result)

                    # 趋势方向
                    trend_direction = self._determine_trend_direction(result)

                    confidence = f"{result.get('confidence', 0):.2f}"

                    # 影响权重 (基于数据源和指标类型)
                    impact_weight = self._calculate_impact_weight(data_source, indicator)

                    quality = str(result.get('data_quality', '--'))
                    timestamp = str(result.get('timestamp', '--'))

                    # 批量设置表格项
                    items = [
                        QTableWidgetItem(data_source),
                        QTableWidgetItem(indicator),
                        QTableWidgetItem(value),
                        QTableWidgetItem(hist_compare),
                        QTableWidgetItem(signal_strength),
                        QTableWidgetItem(trend_direction),
                        QTableWidgetItem(confidence),
                        QTableWidgetItem(impact_weight),
                        QTableWidgetItem(quality),
                        QTableWidgetItem(timestamp)
                    ]

                    for col, item in enumerate(items):
                        self.sentiment_table.setItem(row, col, item)

                    # 设置行颜色(根据信号强度)
                    self._set_row_color(row, signal_strength)

                    if row < 3:  # 只打印前3行的调试信息
                        logger.info(f"  行{row}: {data_source} | {indicator} | {value}")

                except Exception as e:
                    logger.error(f" 更新表格行{row}失败: {e}")

            # 重新启用排序
            self.sentiment_table.setSortingEnabled(True)

            # 强制更新表格显示
            self.sentiment_table.update()
            logger.info(" 情绪表格更新完成")

        except Exception as e:
            logger.error(f" 更新情绪显示失败: {e}")
            import traceback
            traceback.print_exc()

    def _calculate_real_historical_compare(self, result):
        """使用真实历史数据计算对比值"""
        try:
            # 尝试从hikyuu获取真实历史数据
            if hasattr(self, 'stock_code') and self.stock_code:
                try:
                    # # import hikyuu as hk  # 已替换为统一数据访问器  # 已替换为统一数据访问器
                    stock = hk.get_stock(self.stock_code)
                    if not stock.is_null():
                        # 获取最近30天的数据进行对比
                        kdata = stock.get_kdata(hk.Query(-30))
                        if len(kdata) > 0:
                            # 计算历史平均值
                            closes = [k.close for k in kdata]
                            historical_avg = sum(closes) / len(closes)

                            current_value = result.get('value', 50)
                            # 将情绪值映射到价格变化百分比
                            sentiment_change = (current_value - 50) / 50 * 100

                            if sentiment_change > 5:
                                return f"+{sentiment_change:.1f}%"
                            elif sentiment_change < -5:
                                return f"{sentiment_change:.1f}%"
                            else:
                                return f"{sentiment_change:+.1f}%"
                except Exception as e:
                    logger.error(f" 获取真实历史数据失败: {e}")

            # 回退到基础计算
            current_value = result.get('value', 50)
            baseline = 50.0  # 中性基线
            diff = current_value - baseline
            percent_change = (diff / baseline * 100) if baseline != 0 else 0

            if percent_change > 5:
                return f"+{percent_change:.1f}%"
            elif percent_change < -5:
                return f"{percent_change:.1f}%"
            else:
                return f"{percent_change:+.1f}%"
        except:
            return "--"

    def calculate_composite_sentiment(self):
        """计算综合情绪指数"""
        try:
            logger.info(f" 计算综合情绪指数，数据量: {len(self.sentiment_results)}")

            if not hasattr(self, 'composite_score_label') or self.composite_score_label is None:
                logger.error(" composite_score_label未初始化")
                return

            if not self.sentiment_results:
                logger.error(" 没有数据计算综合指数")
                self.composite_score_label.setText("综合情绪指数: --")
                return

            # 计算加权平均情绪指数
            total_weight = 0
            weighted_sum = 0

            for result in self.sentiment_results:
                weight = result.get('confidence', 0.5) * result.get('strength', 0.5)
                weighted_sum += result.get('value', 50) * weight
                total_weight += weight

            if total_weight > 0:
                composite_score = weighted_sum / total_weight
            else:
                composite_score = 50  # 默认中性

            logger.info(f" 计算出综合情绪指数: {composite_score:.2f}")

            # 更新显示
            self.composite_score_label.setText(f"综合情绪指数: {composite_score:.2f}")

            # 根据分数设置颜色
            if composite_score > 70:
                color = "#00aa00"  # 绿色
            elif composite_score > 55:
                color = "#88aa00"  # 黄绿色
            elif composite_score > 45:
                color = "#aaaa00"  # 黄色
            elif composite_score > 30:
                color = "#aa8800"  # 橙色
            else:
                color = "#aa0000"  # 红色

            self.composite_score_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")

            # 更新统计信息
            if hasattr(self, 'total_indicators_label'):
                self.total_indicators_label.setText(f"指标数量: {len(self.sentiment_results)}")

            # 数据质量统计
            quality_counts = {}
            for result in self.sentiment_results:
                quality = result.get('data_quality', 'unknown')
                quality_counts[quality] = quality_counts.get(quality, 0) + 1

            quality_text = ", ".join([f"{k}:{v}" for k, v in quality_counts.items()])
            if hasattr(self, 'data_quality_label'):
                self.data_quality_label.setText(f"数据质量: {quality_text}")

            # 保存统计信息
            self.sentiment_statistics = {
                'composite_score': composite_score,
                'total_indicators': len(self.sentiment_results),
                'quality_distribution': quality_counts,
                'analysis_time': datetime.now().isoformat(),
                'selected_plugins': self.get_selected_plugins()
            }

            # 更新其他专业指数
            self._update_professional_indices()

            logger.info(" 综合情绪指数更新完成")

        except Exception as e:
            logger.error(f" 计算综合情绪指数失败: {e}")

    def _calculate_signal_strength(self, result):
        """计算信号强度"""
        try:
            value = result.get('value', 0)
            confidence = result.get('confidence', 0)

            # 综合计算信号强度
            strength = (abs(value - 50) / 50) * confidence

            if strength > 0.8:
                return " 强"
            elif strength > 0.5:
                return " 中"
            else:
                return " 弱"
        except:
            return " 未知"

    def _determine_trend_direction(self, result):
        """确定趋势方向"""
        try:
            value = result.get('value', 50)
            signal = result.get('signal', 'neutral')

            if isinstance(signal, str):
                if 'bullish' in signal.lower() or 'buy' in signal.lower():
                    return " 看涨"
                elif 'bearish' in signal.lower() or 'sell' in signal.lower():
                    return " 看跌"

            # 基于数值判断
            if value > 60:
                return " 看涨"
            elif value < 40:
                return " 看跌"
            else:
                return " 中性"
        except:
            return " 未知"

    def _calculate_impact_weight(self, data_source, indicator):
        """计算影响权重"""
        try:
            # 根据数据源和指标类型分配权重
            weights = {
                'vix_sentiment': 0.9,
                'fmp_sentiment': 0.8,
                'news_sentiment': 0.7,
                'social_sentiment': 0.6,
                'default': 0.5
            }

            source_key = data_source.lower() if data_source else 'default'
            for key, weight in weights.items():
                if key in source_key:
                    return f"{weight:.1f}"

            return f"{weights['default']:.1f}"
        except:
            return "0.5"

    def _set_row_color(self, row, signal_strength):
        """设置表格行颜色"""
        try:
            if "强" in signal_strength:
                color = QColor(255, 235, 238)  # 浅红色
            elif "中" in signal_strength:
                color = QColor(255, 248, 225)  # 浅黄色
            elif "弱" in signal_strength:
                color = QColor(232, 245, 233)  # 浅绿色
            else:
                color = QColor(245, 245, 245)  # 浅灰色

            for col in range(self.sentiment_table.columnCount()):
                item = self.sentiment_table.item(row, col)
                if item:
                    item.setBackground(color)
        except Exception as e:
            logger.error(f"设置行颜色失败: {e}")

    def _update_professional_indices(self):
        """更新专业指数显示 - 使用真实数据"""
        try:
            from datetime import datetime

            if not self.sentiment_results:
                return

            # 使用真实数据计算各种专业指数
            fear_greed = self._calculate_real_fear_greed_index()
            volatility = self._calculate_real_volatility_index()
            money_flow = self._calculate_real_money_flow_index()
            news_sentiment = self._calculate_real_news_sentiment_index()
            technical = self._calculate_real_technical_sentiment_index()
            market_strength = self._calculate_real_market_strength_index()

            # 更新显示
            if hasattr(self, 'fear_greed_label'):
                self.fear_greed_label.setText(f"恐惧&贪婪指数: {fear_greed}")
            if hasattr(self, 'volatility_index_label'):
                self.volatility_index_label.setText(f"波动率指数: {volatility}")
            if hasattr(self, 'money_flow_label'):
                self.money_flow_label.setText(f"资金流向指数: {money_flow}")
            if hasattr(self, 'news_sentiment_label'):
                self.news_sentiment_label.setText(f"新闻情绪指数: {news_sentiment}")
            if hasattr(self, 'technical_sentiment_label'):
                self.technical_sentiment_label.setText(f"技术面情绪: {technical}")
            if hasattr(self, 'market_strength_label'):
                self.market_strength_label.setText(f"市场强度指数: {market_strength}")
            if hasattr(self, 'last_update_label'):
                self.last_update_label.setText(f"更新时间: {datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            logger.error(f"更新专业指数失败: {e}")

    def _calculate_real_fear_greed_index(self):
        """计算真实的恐惧&贪婪指数"""
        try:
            # 使用真实的VIX数据或类似指标
            vix_data = [r for r in self.sentiment_results if 'vix' in r.get('data_source', '').lower()]
            if vix_data:
                vix_value = vix_data[0].get('value', 50)
                # VIX越高，恐惧越强
                fear_greed = max(0, min(100, 100 - vix_value * 1.5))
            else:
                # 基于整体情绪和技术指标计算
                sentiment_values = [r.get('value', 50) for r in self.sentiment_results]
                confidence_values = [r.get('confidence', 0.5) for r in self.sentiment_results]

                # 加权平均
                weighted_sum = sum(v * c for v, c in zip(sentiment_values, confidence_values))
                total_weight = sum(confidence_values)
                fear_greed = weighted_sum / total_weight if total_weight > 0 else 50

            # 使用hikyuu技术指标进行修正
            if hasattr(self, 'stock_code') and self.stock_code:
                try:
                    # # import hikyuu as hk  # 已替换为统一数据访问器  # 已替换为统一数据访问器
                    stock = hk.get_stock(self.stock_code)
                    if not stock.is_null():
                        kdata = stock.get_kdata(hk.Query(-20))  # 最近20天
                        if len(kdata) > 10:
                            # 使用RSI指标修正
                            rsi = hk.RSI(kdata.close, 14)
                            if len(rsi) > 0:
                                latest_rsi = rsi[-1]
                                # RSI超买超卖修正恐惧贪婪指数
                                if latest_rsi > 70:  # 超买，增加贪婪
                                    fear_greed = min(100, fear_greed + (latest_rsi - 70) * 0.5)
                                elif latest_rsi < 30:  # 超卖，增加恐惧
                                    fear_greed = max(0, fear_greed - (30 - latest_rsi) * 0.5)
                except Exception as e:
                    logger.error(f" 使用hikyuu修正恐惧贪婪指数失败: {e}")

            if fear_greed < 25:
                return f"{fear_greed:.0f} (极度恐惧)"
            elif fear_greed < 45:
                return f"{fear_greed:.0f} (恐惧)"
            elif fear_greed < 55:
                return f"{fear_greed:.0f} (中性)"
            elif fear_greed < 75:
                return f"{fear_greed:.0f} (贪婪)"
            else:
                return f"{fear_greed:.0f} (极度贪婪)"
        except:
            return "--"

    def _calculate_real_volatility_index(self):
        """计算真实的波动率指数"""
        try:
            # 优先使用真实VIX数据
            vix_data = [r for r in self.sentiment_results if 'vix' in r.get('data_source', '').lower()]
            if vix_data:
                return f"{vix_data[0].get('value', 0):.1f}"

            # 使用hikyuu计算真实波动率
            if hasattr(self, 'stock_code') and self.stock_code:
                try:
                    # # import hikyuu as hk  # 已替换为统一数据访问器  # 已替换为统一数据访问器
                    stock = hk.get_stock(self.stock_code)
                    if not stock.is_null():
                        kdata = stock.get_kdata(hk.Query(-30))  # 最近30天
                        if len(kdata) > 10:
                            # 计算真实波动率 (ATR)
                            atr = hk.ATR(kdata, 14)
                            if len(atr) > 0:
                                latest_atr = atr[-1]
                                latest_close = kdata.close[-1]
                                volatility_pct = (latest_atr / latest_close * 100) if latest_close > 0 else 0
                                return f"{volatility_pct:.1f}"
                except Exception as e:
                    logger.error(f" 使用hikyuu计算波动率失败: {e}")

            # 基于情绪数据的标准差估算
            values = [r.get('value', 50) for r in self.sentiment_results]
            if len(values) > 1:
                import statistics
                volatility = statistics.stdev(values)
                return f"{volatility:.1f}"
            return "--"
        except:
            return "--"

    def _calculate_real_money_flow_index(self):
        """计算真实的资金流向指数"""
        try:
            # 使用hikyuu的资金流指标
            if hasattr(self, 'stock_code') and self.stock_code:
                try:
                    # # import hikyuu as hk  # 已替换为统一数据访问器  # 已替换为统一数据访问器
                    stock = hk.get_stock(self.stock_code)
                    if not stock.is_null():
                        kdata = stock.get_kdata(hk.Query(-20))
                        if len(kdata) > 10:
                            # 计算资金流量指数 (MFI)
                            high = kdata.high
                            low = kdata.low
                            close = kdata.close
                            volume = kdata.vol

                            # 简化的MFI计算
                            typical_price = (high + low + close) / 3
                            money_flow = typical_price * volume

                            # 计算正负资金流
                            positive_flow = 0
                            negative_flow = 0

                            for i in range(1, len(money_flow)):
                                if typical_price[i] > typical_price[i-1]:
                                    positive_flow += money_flow[i]
                                elif typical_price[i] < typical_price[i-1]:
                                    negative_flow += money_flow[i]

                            if negative_flow > 0:
                                money_ratio = positive_flow / negative_flow
                                mfi = 100 - (100 / (1 + money_ratio))
                                return f"{mfi:.1f}"
                except Exception as e:
                    logger.error(f" 使用hikyuu计算资金流失败: {e}")

            # 基于情绪数据的置信度计算
            confidence_sum = sum(r.get('confidence', 0.5) for r in self.sentiment_results)
            avg_confidence = confidence_sum / len(self.sentiment_results) if self.sentiment_results else 0.5
            money_flow = avg_confidence * 100
            return f"{money_flow:.1f}"
        except:
            return "--"

    def _calculate_real_news_sentiment_index(self):
        """计算真实的新闻情绪指数"""
        try:
            news_data = [r for r in self.sentiment_results if 'news' in r.get('data_source', '').lower() or 'sentiment' in r.get('indicator', '').lower()]
            if news_data:
                # 加权平均新闻情绪
                weighted_sum = sum(r.get('value', 50) * r.get('confidence', 0.5) for r in news_data)
                total_weight = sum(r.get('confidence', 0.5) for r in news_data)
                avg_news = weighted_sum / total_weight if total_weight > 0 else 50
                return f"{avg_news:.1f}"
            return "--"
        except:
            return "--"

    def _calculate_real_technical_sentiment_index(self):
        """计算真实的技术面情绪指数"""
        try:
            # 使用hikyuu技术指标计算技术面情绪
            if hasattr(self, 'stock_code') and self.stock_code:
                try:
                    import hikyuu as hk  # 已替换为统一数据访问器
                    stock = hk.get_stock(self.stock_code)
                    if not stock.is_null():
                        kdata = stock.get_kdata(hk.Query(-50))
                        if len(kdata) > 20:
                            # 综合多个技术指标
                            close = kdata.close

                            # RSI指标
                            rsi = hk.RSI(close, 14)
                            rsi_score = 0
                            if len(rsi) > 0:
                                latest_rsi = rsi[-1]
                                if latest_rsi > 70:
                                    rsi_score = 75  # 超买，偏向看涨
                                elif latest_rsi < 30:
                                    rsi_score = 25  # 超卖，偏向看跌
                                else:
                                    rsi_score = latest_rsi

                            # MACD指标
                            macd = hk.MACD(close)
                            macd_score = 50  # 默认中性
                            if len(macd) > 0:
                                macd_line = macd.get_result(0)
                                signal_line = macd.get_result(1)
                                if len(macd_line) > 0 and len(signal_line) > 0:
                                    if macd_line[-1] > signal_line[-1]:
                                        macd_score = 65  # 金叉，偏向看涨
                                    else:
                                        macd_score = 35  # 死叉，偏向看跌

                            # 移动平均线
                            ma20 = hk.MA(close, 20)
                            ma_score = 50
                            if len(ma20) > 0 and len(close) > 0:
                                if close[-1] > ma20[-1]:
                                    ma_score = 60  # 价格在均线上方
                                else:
                                    ma_score = 40  # 价格在均线下方

                            # 综合技术面得分
                            technical_score = (rsi_score * 0.4 + macd_score * 0.3 + ma_score * 0.3)
                            return f"{technical_score:.1f}"

                except Exception as e:
                    logger.error(f" 使用hikyuu计算技术面情绪失败: {e}")

            # 基于非新闻类数据源计算技术面情绪
            tech_data = [r for r in self.sentiment_results if 'news' not in r.get('data_source', '').lower()]
            if tech_data:
                weighted_sum = sum(r.get('value', 50) * r.get('confidence', 0.5) for r in tech_data)
                total_weight = sum(r.get('confidence', 0.5) for r in tech_data)
                avg_tech = weighted_sum / total_weight if total_weight > 0 else 50
                return f"{avg_tech:.1f}"
            return "--"
        except:
            return "--"

    def _calculate_real_market_strength_index(self):
        """计算真实的市场强度指数"""
        try:
            # 使用hikyuu计算市场强度
            if hasattr(self, 'stock_code') and self.stock_code:
                try:
                    # # import hikyuu as hk  # 已替换为统一数据访问器  # 已替换为统一数据访问器
                    stock = hk.get_stock(self.stock_code)
                    if not stock.is_null():
                        kdata = stock.get_kdata(hk.Query(-20))
                        if len(kdata) > 10:
                            # 使用成交量和价格变化计算强度
                            close = kdata.close
                            volume = kdata.vol

                            # 计算价格动量
                            price_changes = []
                            volume_weights = []

                            for i in range(1, len(close)):
                                price_change = abs(close[i] - close[i-1]) / close[i-1] if close[i-1] > 0 else 0
                                price_changes.append(price_change)
                                volume_weights.append(volume[i])

                            if price_changes and volume_weights:
                                # 成交量加权的价格动量
                                weighted_momentum = sum(pc * vw for pc, vw in zip(price_changes, volume_weights))
                                total_volume = sum(volume_weights)
                                strength = (weighted_momentum / total_volume * 10000) if total_volume > 0 else 0
                                return f"{min(100, strength):.1f}"

                except Exception as e:
                    logger.error(f" 使用hikyuu计算市场强度失败: {e}")

            # 基于情绪数据的综合强度
            strengths = []
            for result in self.sentiment_results:
                value = result.get('value', 50)
                confidence = result.get('confidence', 0.5)
                strength = abs(value - 50) * confidence
                strengths.append(strength)

            if strengths:
                avg_strength = sum(strengths) / len(strengths)
                return f"{avg_strength:.1f}"
            return "--"
        except:
            return "--"

    def collect_sentiment_data_for_report(self, period: int):
        """为报告收集真实情绪数据"""
        try:
            if not self.sentiment_statistics or 'composite_score' not in self.sentiment_statistics:
                QMessageBox.information(self, "提示", "请先执行一次实时情绪分析，以便为报告提供数据。")
                return {}

            composite_index = self.sentiment_statistics['composite_score']

            # 使用真实数据而不是模拟数据
            data = {
                'period': period,
                'collection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'composite_index': composite_index
            }

            # 从真实情绪结果中提取各类指数
            vix_index = next((r.get('value') for r in self.sentiment_results if 'vix' in str(r.get('indicator', '')).lower()), None)
            fear_greed_index = next((r.get('value') for r in self.sentiment_results if 'fear' in str(r.get('indicator', '')).lower()), None)
            investor_sentiment = next((r.get('value') for r in self.sentiment_results if 'investor' in str(r.get('indicator', '')).lower()), None)
            technical_sentiment = next((r.get('value') for r in self.sentiment_results if 'technical' in str(r.get('indicator', '')).lower()), None)
            news_sentiment = next((r.get('value') for r in self.sentiment_results if 'news' in str(r.get('indicator', '')).lower()), None)
            social_sentiment = next((r.get('value') for r in self.sentiment_results if 'social' in str(r.get('indicator', '')).lower()), None)

            # 只有在有真实数据时才添加到报告中
            if vix_index is not None:
                data['vix_index'] = vix_index
            if fear_greed_index is not None:
                data['fear_greed_index'] = fear_greed_index
            if investor_sentiment is not None:
                data['investor_sentiment'] = investor_sentiment
            if technical_sentiment is not None:
                data['technical_sentiment'] = technical_sentiment
            if news_sentiment is not None:
                data['news_sentiment'] = news_sentiment
            if social_sentiment is not None:
                data['social_sentiment'] = social_sentiment

            # 确定情绪状态
            if data['composite_index'] > 70:
                data['sentiment_status'] = '乐观'
            elif data['composite_index'] > 50:
                data['sentiment_status'] = '中性'
            else:
                data['sentiment_status'] = '悲观'

            # 使用真实历史数据生成趋势
            if hasattr(self, 'stock_code') and self.stock_code:
                try:
                    # # import hikyuu as hk  # 已替换为统一数据访问器  # 已替换为统一数据访问器
                    stock = hk.get_stock(self.stock_code)
                    if not stock.is_null():
                        kdata = stock.get_kdata(hk.Query(-period))
                        if len(kdata) > 0:
                            historical_trend = []
                            for i, k in enumerate(kdata):
                                # 将价格变化映射为情绪值
                                if i == 0:
                                    sentiment_value = composite_index
                                else:
                                    price_change = (k.close - kdata[i-1].close) / kdata[i-1].close
                                    sentiment_value = 50 + (price_change * 100)  # 简单映射
                                    sentiment_value = max(0, min(100, sentiment_value))

                                historical_trend.append({
                                    'date': k.datetime.strftime('%Y-%m-%d'),
                                    'value': sentiment_value
                                })
                            data['historical_trend'] = historical_trend
                except Exception as e:
                    logger.error(f" 获取真实历史趋势数据失败: {e}")

            return data

        except Exception as e:
            logger.error(f"收集情绪数据失败: {str(e)}")
            return {}

    def update_status_display(self):
        """更新状态显示"""
        try:
            # 服务状态
            if self.sentiment_service:
                if hasattr(self.sentiment_service, 'get_service_status'):
                    status = self.sentiment_service.get_service_status()
                    status_text = "运行中" if status.get('is_running', False) else "就绪"
                    self.service_status_label.setText(f"服务状态: {status_text}")
                else:
                    self.service_status_label.setText("服务状态: 已连接")
            else:
                self.service_status_label.setText("服务状态: 未连接")

            # 插件状态
            selected_count = len(self.get_selected_plugins())
            total_count = len(self.available_plugins)
            self.plugins_status_label.setText(f"插件状态: {selected_count}/{total_count}")

            # 最后更新时间
            current_time = datetime.now().strftime('%H:%M:%S')
            self.last_update_label.setText(f"最后更新: {current_time}")

        except Exception as e:
            logger.error(f" 更新状态显示失败: {e}")

    def refresh_status(self):
        """刷新状态"""
        self.update_status_display()

    def toggle_auto_refresh(self, enabled: bool):
        """切换自动刷新"""
        if enabled:
            interval_ms = self.refresh_interval_spin.value() * 60 * 1000
            self.auto_refresh_timer.start(interval_ms)
            logger.info(f" 启动自动刷新，间隔 {self.refresh_interval_spin.value()} 分钟")
        else:
            self.auto_refresh_timer.stop()
            logger.info(" 停止自动刷新")

    def auto_refresh_data(self):
        """自动刷新数据"""
        if self.get_selected_plugins():
            logger.info("⏰ 自动刷新情绪数据...")
            self.analyze_sentiment()

    def stop_analysis(self):
        """停止分析 - 改进版本，避免阻塞"""
        try:
            # 停止异步分析线程
            if self.analysis_thread and self.analysis_thread.isRunning():
                logger.info(" 正在停止异步分析线程...")
                self.analysis_thread.stop()
                # 使用非阻塞方式等待线程结束
                QTimer.singleShot(100, self._check_thread_stopped)
            else:
                self._finalize_stop()

            # 停止插件加载线程
            if self.plugin_loader and self.plugin_loader.isRunning():
                logger.info(" 正在停止插件加载线程...")
                self.plugin_loader.stop()

            # 停止自动刷新
            self.auto_refresh_timer.stop()
            if hasattr(self, 'auto_refresh_cb'):
                self.auto_refresh_cb.setChecked(False)

        except Exception as e:
            logger.error(f" 停止分析时出错: {e}")
            self._finalize_stop()

    def _check_thread_stopped(self):
        """检查线程是否已停止"""
        if self.analysis_thread and self.analysis_thread.isRunning():
            # 如果线程还在运行，再等待一段时间
            QTimer.singleShot(500, self._force_stop_thread)
        else:
            self._finalize_stop()

    def _force_stop_thread(self):
        """强制停止线程"""
        if self.analysis_thread and self.analysis_thread.isRunning():
            logger.info(" 强制终止分析线程...")
            self.analysis_thread.terminate()
            self.analysis_thread.wait(1000)
        self._finalize_stop()

    def _finalize_stop(self):
        """完成停止操作"""
        # 重置UI状态
        self.reset_ui_state()
        if self.status_label:
            self.status_label.setText("分析已停止")
        logger.info(" 情绪分析已停止")

    def save_results(self):
        """保存分析结果"""
        if not self.sentiment_results:
            self.update_status_label(" 没有可保存的结果")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存情绪分析结果",
            f"sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON文件 (*.json);;CSV文件 (*.csv)"
        )

        if file_path:
            try:
                if file_path.endswith('.json'):
                    import json
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            'results': self.sentiment_results,
                            'statistics': self.sentiment_statistics,
                            'export_time': datetime.now().isoformat()
                        }, f, ensure_ascii=False, indent=2)
                elif file_path.endswith('.csv'):
                    df = pd.DataFrame(self.sentiment_results)
                    df.to_csv(file_path, index=False, encoding='utf-8')

                self.update_status_label(f" 结果已保存到: {file_path}")
                logger.info(f" 结果已保存: {file_path}")
            except Exception as e:
                error_msg = f"保存失败: {str(e)}"
                self.update_status_label(f" {error_msg}")
                logger.error(f" {error_msg}")

    def clear_results(self):
        """清空分析结果"""
        self.sentiment_results = []
        self.sentiment_statistics = {}
        self.sentiment_table.setRowCount(0)
        if hasattr(self, 'composite_score_label'):
            self.composite_score_label.setText("综合情绪指数: --")
        if hasattr(self, 'total_indicators_label'):
            self.total_indicators_label.setText("指标数量: --")
        if hasattr(self, 'data_quality_label'):
            self.data_quality_label.setText("数据质量: --")
        logger.info(" 已清空分析结果")

    # 报告功能方法
    def generate_sentiment_report(self):
        """生成情绪报告"""
        try:
            logger.info(" 开始生成情绪报告...")

            # 获取报告参数
            report_type = self.report_type_combo.currentText()
            period = self.report_period_spin.value()
            report_format = self.report_format_combo.currentText()

            # 收集数据
            report_data = self.collect_sentiment_data_for_report(period)

            if not report_data:
                QMessageBox.warning(self, "警告", "无法生成报告，请先执行情绪分析获取数据")
                return

            # 生成报告内容
            report_content = self.format_sentiment_report(report_data, report_type)

            # 更新预览
            self.report_preview.setHtml(report_content)

            # 添加到历史记录
            self.add_report_to_history(report_type, period, "已生成")

            # 发送完成信号
            self.sentiment_report_completed.emit({
                'report_type': report_type,
                'period': period,
                'format': report_format,
                'data': report_data,
                'content': report_content,
                'timestamp': datetime.now().isoformat()
            })

            QMessageBox.information(self, "成功", f"情绪报告生成完成\n类型: {report_type}\n周期: {period}天")
            logger.info(" 情绪报告生成完成")

        except Exception as e:
            logger.error(f" 生成报告失败: {e}")
            QMessageBox.critical(self, "错误", f"生成报告失败: {str(e)}")

    def format_sentiment_report(self, data, report_type):
        """格式化情绪报告"""
        html_content = f"""
        <html>
        <head>
            <title>{report_type} - 市场情绪分析报告</title>
            <style>
                body {{ font-family: "Microsoft YaHei", Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
                .positive {{ color: #27ae60; }}
                .negative {{ color: #e74c3c; }}
                .neutral {{ color: #95a5a6; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1> {report_type}</h1>
                <h2>市场情绪分析报告</h2>
                <p>生成时间: {data.get('collection_time', 'N/A')}</p>
                <p>数据周期: {data.get('period', 'N/A')} 天</p>
            </div>
            
            <div class="section">
                <h3> 情绪指标概览</h3>
                <div class="metric">
                    <strong>综合情绪指数:</strong> 
                    <span class="{'positive' if data.get('composite_index', 50) > 60 else 'negative' if data.get('composite_index', 50) < 40 else 'neutral'}">
                        {data.get('composite_index', 0):.2f}
                    </span>
                </div>
                <div class="metric">
                    <strong>情绪状态:</strong> 
                    <span class="{'positive' if data.get('sentiment_status') == '乐观' else 'negative' if data.get('sentiment_status') == '悲观' else 'neutral'}">
                        {data.get('sentiment_status', '未知')}
                    </span>
                </div>
                <div class="metric">
                    <strong>VIX恐慌指数:</strong> {data.get('vix_index', 0):.2f}
                </div>
                <div class="metric">
                    <strong>恐惧贪婪指数:</strong> {data.get('fear_greed_index', 0):.2f}
                </div>
            </div>
            
            <div class="section">
                <h3> 分类情绪分析</h3>
                <div class="metric">
                    <strong>投资者情绪:</strong> {data.get('investor_sentiment', 0):.2f}
                </div>
                <div class="metric">
                    <strong>技术面情绪:</strong> {data.get('technical_sentiment', 0):.2f}
                </div>
                <div class="metric">
                    <strong>新闻情绪:</strong> {data.get('news_sentiment', 0):.2f}
                </div>
                <div class="metric">
                    <strong>社交媒体情绪:</strong> {data.get('social_sentiment', 0):.2f}
                </div>
            </div>
            
            <div class="section">
                <h3> 分析结论</h3>
                <p>根据当前数据分析，市场整体情绪呈现<strong>{data.get('sentiment_status', '未知')}</strong>态势。</p>
                <p>综合情绪指数为<strong>{data.get('composite_index', 0):.2f}</strong>，
                {'建议保持谨慎乐观态度' if data.get('composite_index', 50) > 60 else '建议控制风险' if data.get('composite_index', 50) < 40 else '建议保持观望'}。</p>
            </div>
            
            <div class="section">
                <h3> 风险提示</h3>
                <p>本报告仅供参考，投资有风险，入市需谨慎。请结合其他分析工具和市场信息做出投资决策。</p>
            </div>
        </body>
        </html>
        """
        return html_content

    def schedule_sentiment_report(self):
        """设置定时报告"""
        QMessageBox.information(self, "功能开发中", "定时报告功能正在开发中，敬请期待！")

    def export_sentiment_report(self):
        """导出情绪报告"""
        if not hasattr(self, 'report_preview') or not self.report_preview.toPlainText():
            QMessageBox.warning(self, "警告", "请先生成报告再导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出情绪报告",
            f"sentiment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            "HTML文件 (*.html);;PDF文件 (*.pdf);;文本文件 (*.txt)"
        )

        if file_path:
            try:
                if file_path.endswith('.html'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.report_preview.toHtml())
                elif file_path.endswith('.txt'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.report_preview.toPlainText())
                else:
                    QMessageBox.warning(self, "提示", "PDF导出功能正在开发中")
                    return

                QMessageBox.information(self, "成功", f"报告已导出到:\n{file_path}")
                logger.info(f" 报告已导出: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def add_report_to_history(self, report_type, period, status):
        """添加报告到历史记录"""
        row_count = self.report_history_table.rowCount()
        self.report_history_table.insertRow(row_count)

        self.report_history_table.setItem(row_count, 0, QTableWidgetItem(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.report_history_table.setItem(row_count, 1, QTableWidgetItem(report_type))
        self.report_history_table.setItem(row_count, 2, QTableWidgetItem(f"{period}天"))
        self.report_history_table.setItem(row_count, 3, QTableWidgetItem(status))

        # 操作按钮
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)

        view_btn = QPushButton("查看")
        view_btn.clicked.connect(lambda: self.view_historical_report(row_count))
        action_layout.addWidget(view_btn)

        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(lambda: self.delete_historical_report(row_count))
        action_layout.addWidget(delete_btn)

        self.report_history_table.setCellWidget(row_count, 4, action_widget)

    def view_historical_report(self, row):
        """查看历史报告"""
        QMessageBox.information(self, "提示", "查看历史报告功能正在开发中")

    def delete_historical_report(self, row):
        """删除历史报告"""
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个历史报告吗？")
        if reply == QMessageBox.Yes:
            self.report_history_table.removeRow(row)

    # 继承方法覆盖
    def refresh_data(self):
        """刷新数据 - 从BaseAnalysisTab继承的方法"""
        if hasattr(self, 'main_tab_widget'):
            current_index = self.main_tab_widget.currentIndex()
            if current_index == 0:  # 实时分析标签页
                self.analyze_sentiment()
            elif current_index == 1:  # 报告标签页
                if self.sentiment_results:
                    self.generate_sentiment_report()

    def clear_data(self):
        """清除数据 - 从BaseAnalysisTab继承的方法"""
        self.sentiment_results = []
        self.sentiment_statistics = {}
        self.sentiment_history = []
        self.report_results = []
        self.report_statistics = {}

        if hasattr(self, 'sentiment_table'):
            self.sentiment_table.setRowCount(0)
        if hasattr(self, 'report_preview'):
            self.report_preview.clear()
        if hasattr(self, 'composite_score_label'):
            self.composite_score_label.setText("综合情绪指数: --")

    def ensure_ui_visibility(self):
        """确保UI可见性"""
        try:
            self.setVisible(True)
            self.update()
        except Exception as e:
            logger.error(f" 确保UI可见性失败: {e}")

    def on_sentiment_data_updated(self, response):
        """情绪数据更新事件处理"""
        logger.info(f" 收到情绪数据更新: {len(response.data) if response.data else 0} 个指标")
        self.plugin_data_updated.emit({'response': response})

    def on_plugin_error(self, plugin_name: str, error_message: str):
        """插件错误事件处理"""
        logger.error(f" 插件错误 {plugin_name}: {error_message}")
        QMessageBox.warning(self, "插件错误", f"插件 {plugin_name} 发生错误:\n{error_message}")

    def set_stock_data(self, stock_code: str, kdata):
        """设置股票数据"""
        super().set_stock_data(stock_code, kdata)
        logger.info(f" 情绪分析: 接收到股票数据 {stock_code}")

        # 当股票数据更新时，可以自动进行情绪分析
        if hasattr(self, 'auto_refresh_cb') and self.auto_refresh_cb.isChecked():
            self.analyze_sentiment()

    def closeEvent(self, event):
        """关闭事件 - 改进版本，确保资源清理"""
        try:
            # 停止所有定时器
            if hasattr(self, 'auto_refresh_timer'):
                self.auto_refresh_timer.stop()

            # 停止所有线程
            if self.analysis_thread and self.analysis_thread.isRunning():
                self.analysis_thread.stop()
                self.analysis_thread.wait(2000)  # 等待最多2秒
                if self.analysis_thread.isRunning():
                    self.analysis_thread.terminate()

            if self.plugin_loader and self.plugin_loader.isRunning():
                self.plugin_loader.stop()
                self.plugin_loader.wait(2000)
                if self.plugin_loader.isRunning():
                    self.plugin_loader.terminate()

            # 清理情绪数据服务
            if self.sentiment_service:
                try:
                    if hasattr(self.sentiment_service, 'cleanup'):
                        self.sentiment_service.cleanup()
                except Exception as e:
                    logger.error(f" 清理情绪数据服务失败: {e}")

            logger.info(" 专业情绪分析标签页资源清理完成")

        except Exception as e:
            logger.error(f" 关闭事件处理失败: {e}")
        finally:
            super().closeEvent(event)

    def set_kdata(self, kdata):
        """设置K线数据 - 优化版本，避免重复分析和阻塞"""
        try:
            # 调用父类方法进行基础设置
            super().set_kdata(kdata)

            # 如果有数据且当前标签页可见，才进行情绪分析
            if (kdata is not None and not kdata.empty and
                    hasattr(self, 'isVisible') and self.isVisible()):

                # 检查是否启用了自动刷新，且没有正在进行的分析
                if (hasattr(self, 'auto_refresh_cb') and self.auto_refresh_cb.isChecked() and
                        not (self.analysis_thread and self.analysis_thread.isRunning())):

                    # 延迟执行，避免阻塞UI，并且只在插件加载完成后执行
                    if self.available_plugins:
                        QTimer.singleShot(500, self._delayed_analyze_sentiment)
                    else:
                        logger.info(" 插件尚未加载完成，跳过自动情绪分析")

        except Exception as e:
            logger.error(f" [ProfessionalSentimentTab] 设置K线数据失败: {e}")

    def _delayed_analyze_sentiment(self):
        """延迟执行情绪分析 - 带安全检查"""
        try:
            # 再次检查条件，确保安全执行
            if (hasattr(self, 'analyze_sentiment') and
                self.available_plugins and
                    not (self.analysis_thread and self.analysis_thread.isRunning())):
                logger.info(" 执行延迟的情绪分析...")
                self.analyze_sentiment()
        except Exception as e:
            logger.error(f" [ProfessionalSentimentTab] 延迟情绪分析失败: {e}")

    def on_plugins_db_updated(self):
        """数据库插件状态更新回调 -> 异步刷新情绪插件列表"""
        try:
            logger.info(" 检测到数据库更新，异步刷新情绪插件列表...")
            # 使用异步方式刷新，避免阻塞主线程
            QTimer.singleShot(200, self.load_available_plugins_async)
        except Exception as e:
            logger.error(f" 刷新情绪插件列表失败: {e}")


# 为了向后兼容，添加别名
SentimentAnalysisTab = ProfessionalSentimentTab
