import numpy as np
import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QColor, QPalette, QPainter, QMovie
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
import time
from typing import Dict, Any, Optional, List, Union
from core.data_manager import DataManager
from core.logger import LogManager, LogLevel
from datetime import datetime
import ptvsd
from gui.ui_components import BaseAnalysisPanel
import traceback


class DataUpdateThread(QThread):
    """数据更新线程"""
    data_updated = pyqtSignal(dict)  # 数据更新信号
    error_occurred = pyqtSignal(str)  # 错误信号
    status_changed = pyqtSignal(str)  # 状态信号

    def __init__(self, data_manager: DataManager, log_manager: Optional[LogManager] = None):
        super().__init__()
        self.data_manager = data_manager
        self.log_manager = log_manager or LogManager()
        self.running = False
        self.update_interval = 60  # 更新间隔（秒）
        self.retry_interval = 5    # 重试间隔（秒）
        self.max_retries = 3       # 最大重试次数

    def run(self):
        """运行更新线程"""
        self.running = True
        retry_count = 0

        while self.running:
            try:
                # 获取最新数据
                self.log_manager.log("[线程] 正在更新数据...", LogLevel.DEBUG)
                self.status_changed.emit("正在更新数据...")
                sentiment_data = self.data_manager.get_market_sentiment()

                if sentiment_data:
                    # 发送信号更新UI
                    self.data_updated.emit(sentiment_data)
                    self.log_manager.log("[线程] 数据更新成功", LogLevel.DEBUG)
                    self.status_changed.emit("数据更新成功")
                    retry_count = 0  # 重置重试计数
                else:
                    raise ValueError("获取数据为空")

            except Exception as e:
                retry_count += 1
                error_msg = f"更新市场情绪数据失败 ({retry_count}/{self.max_retries}): {str(e)}"
                self.log_manager.log(error_msg, LogLevel.ERROR)
                self.error_occurred.emit(error_msg)
                self.log_manager.log("[线程] 更新失败，准备重试...", LogLevel.WARNING)
                self.status_changed.emit("更新失败，准备重试...")

                if retry_count >= self.max_retries:
                    self.log_manager.log(
                        "[线程] 达到最大重试次数，等待下一轮更新", LogLevel.WARNING)
                    self.status_changed.emit("达到最大重试次数，等待下一轮更新")
                    retry_count = 0
                    time.sleep(self.update_interval)
                else:
                    time.sleep(self.retry_interval)
                continue

            # 正常更新后的等待
            for _ in range(self.update_interval):
                if not self.running:
                    break
                time.sleep(1)

        self.log_manager.log("[线程] 已停止更新", LogLevel.INFO)
        self.status_changed.emit("已停止更新")

    def stop(self):
        """停止更新线程"""
        self.running = False
        self.status_changed.emit("已停止更新")


class MarketSentimentWidget(BaseAnalysisPanel):
    """市场情绪分析组件，继承统一分析面板基类"""

    def __init__(self, parent=None, data_manager=None, log_manager=None, chart_widget=None):
        """初始化市场情绪组件

        Args:
            parent: 父窗口
            data_manager: 数据管理器实例
            log_manager: 日志管理器实例
            chart_widget: 主图表控件实例
        """
        super().__init__(parent, log_manager=log_manager)
        self.data_manager = data_manager
        self.chart_widget = chart_widget
        self.template_manager = TemplateManager(
            template_dir="templates/market_sentiment")
        # 修复：初始化数据缓存，防止未定义报错
        self._data_cache = {}
        self._cache_time = {}
        self._custom_indicators = {}
        self._alerts = {}
        self._sentiment_cache = {}
        self._sentiment_cache_time = {}

        self.init_ui()

        # 示例：增加情绪阈值参数输入
        self.sentiment_threshold = QSpinBox()
        self.sentiment_threshold.setRange(0, 100)
        self.sentiment_threshold.setValue(50)
        self.add_param_widget("情绪阈值", self.sentiment_threshold)

        # 启动数据更新线程
        if self.data_manager:
            self.update_thread = DataUpdateThread(
                data_manager=self.data_manager,
                log_manager=self.log_manager
            )
            self.update_thread.data_updated.connect(self.update_sentiment_data)
            self.update_thread.error_occurred.connect(self.handle_error)
            self.update_thread.status_changed.connect(
                self.handle_status_change)
            self.update_thread.start()

            # 主动拉取一次数据，确保初始有数据展示
            if hasattr(self.data_manager, 'get_market_sentiment'):
                try:
                    data = self.data_manager.get_market_sentiment()
                    if data:
                        self.update_sentiment_data(data)
                except Exception as e:
                    self.handle_error(f"初始化拉取市场情绪数据失败: {str(e)}")

    def init_ui(self):
        """初始化UI"""
        self.main_layout = self.layout()

        # 创建情绪分数显示
        score_layout = QHBoxLayout()
        score_label = QLabel("市场情绪分数:")
        self.sentiment_score_label = QLabel("0.00")
        self.sentiment_score_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #1976d2; padding: 4px 12px; border-radius: 8px; background: #e3f2fd;")
        score_layout.addWidget(score_label)
        score_layout.addWidget(self.sentiment_score_label)
        score_layout.addStretch()
        self.main_layout.addLayout(score_layout)
        import akshare as ak
        df = ak.index_news_sentiment_scope()
        print(df)
        # 只保留情绪指数走势图表
        self.create_sentiment_chart(self.main_layout)

        # 创建市场热度指示器
        self.create_market_heat_indicator(self.main_layout)

        # 创建状态栏
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("状态:"))
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666666;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.main_layout.addLayout(status_layout)

        # 控制按钮区（分析、导出、模板管理、自定义指标）
        button_layout = QHBoxLayout()
        self.analyze_button = QPushButton("市场情绪分析")
        self.analyze_button.setStyleSheet(
            "background: #1976d2; color: white; font-weight: bold; border-radius: 8px; padding: 6px 18px;")
        self.analyze_button.setToolTip("点击进行市场情绪分析")
        self.analyze_button.clicked.connect(self.on_analyze)
        button_layout.addWidget(self.analyze_button)

        self.export_button = QPushButton("导出结果")
        self.export_button.setStyleSheet(
            "background: #43a047; color: white; font-weight: bold; border-radius: 8px; padding: 6px 18px;")
        self.export_button.setToolTip("导出分析结果为图片")
        self.export_button.clicked.connect(self.export_data)
        button_layout.addWidget(self.export_button)

        self.template_button = QPushButton("模板管理")
        self.template_button.setStyleSheet(
            "background: #ffa000; color: white; font-weight: bold; border-radius: 8px; padding: 6px 18px;")
        self.template_button.setToolTip("管理情绪分析参数模板")
        self.template_button.clicked.connect(self.show_template_manager_dialog)
        button_layout.addWidget(self.template_button)

        self.main_layout.addLayout(button_layout)

    def create_sentiment_chart(self, layout=None):
        """创建市场情绪图表

        Args:
            layout: 可选的布局对象，如果提供则将图表添加到该布局中

        Returns:
            QChartView: 图表视图对象
        """
        try:
            # 创建图表
            chart = QChart()
            chart.setTitle("市场情绪")
            chart.setAnimationOptions(QChart.SeriesAnimations)

            # 创建数据系列
            self.sentiment_series = QLineSeries()
            self.sentiment_series.setName("情绪指数")

            # 创建X轴
            self.sentiment_axis_x = QValueAxis()
            self.sentiment_axis_x.setTitleText("时间")
            self.sentiment_axis_x.setLabelFormat("%d")

            # 创建Y轴
            self.sentiment_axis_y = QValueAxis()
            self.sentiment_axis_y.setTitleText("情绪值")
            self.sentiment_axis_y.setRange(0, 100)  # 使用整数范围
            self.sentiment_axis_y.setLabelFormat("%d")

            # 添加系列和轴到图表
            chart.addSeries(self.sentiment_series)
            chart.addAxis(self.sentiment_axis_x, Qt.AlignBottom)
            chart.addAxis(self.sentiment_axis_y, Qt.AlignLeft)

            # 关联系列和轴
            self.sentiment_series.attachAxis(self.sentiment_axis_x)
            self.sentiment_series.attachAxis(self.sentiment_axis_y)

            # 创建图表视图
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.Antialiasing)

            # 设置图表视图的大小策略
            chart_view.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
            chart_view.setMinimumHeight(300)

            # 保存图表相关对象的引用
            self.sentiment_chart = chart
            self.sentiment_chart_view = chart_view

            # 如果提供了布局，添加图表视图
            if layout is not None:
                layout.addWidget(chart_view)

            self.log_manager.info("市场情绪图表创建成功")
            return chart_view

        except Exception as e:
            self.log_manager.error(f"创建市场情绪图表失败: {str(e)}")
            return None

    def create_market_heat_indicator(self, layout):
        """美化市场热度指示器"""
        heat_layout = QHBoxLayout()
        heat_layout.addWidget(QLabel("市场热度:"))
        self.heat_progress = QProgressBar()
        self.heat_progress.setRange(0, 100)
        self.heat_progress.setTextVisible(True)
        self.heat_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #90caf9;
                border-radius: 12px;
                text-align: center;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e3f2fd, stop:1 #bbdefb);
                height: 28px;
                font-size: 16px;
                color: #1976d2;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #43a047, stop:1 #1976d2);
                border-radius: 12px;
            }
        """)
        heat_layout.addWidget(self.heat_progress)
        layout.addLayout(heat_layout)

    def set_heat_progress(self, value):
        value = max(0, min(100, int(value)))
        self.heat_progress.setValue(value)

    def set_heat_progress_error(self, message="分析失败"):
        self.heat_progress.setStyleSheet(
            "QProgressBar::chunk {background-color: #FF0000;}")
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #FF5252;")

    def create_control_buttons(self, layout):
        """创建控制按钮"""
        button_layout = QHBoxLayout()

        # 导出数据按钮
        export_button = QPushButton("导出数据")
        export_button.clicked.connect(self.export_data)
        button_layout.addWidget(export_button)

        # 设置预警按钮
        alert_button = QPushButton("设置预警")
        alert_button.clicked.connect(self.show_alert_dialog)
        button_layout.addWidget(alert_button)

        layout.addLayout(button_layout)

    def _get_cached_data(self, key, max_age=60):
        """获取缓存数据"""
        if key in self._data_cache:
            if time.time() - self._cache_time[key] < max_age:
                return self._data_cache[key]
        return None

    def add_custom_indicator(self, name, calculator):
        """添加自定义指标"""
        self._custom_indicators[name] = calculator
        self._refresh_indicators()

    def set_alert(self, indicator, threshold, callback):
        """设置指标预警"""
        self._alerts[indicator] = {
            'threshold': threshold,
            'callback': callback
        }

    def export_data(self):
        """增强导出功能，支持导出表格和图表，操作写日志"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出分析结果",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv);;PNG Files (*.png)"
            )
            if file_path:
                if file_path.endswith('.xlsx') or file_path.endswith('.csv'):
                    # 导出表格
                    import pandas as pd
                    data = []
                    for row in range(self.sentiment_table.rowCount()):
                        row_data = []
                        for col in range(self.sentiment_table.columnCount()):
                            item = self.sentiment_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        data.append(row_data)
                    df = pd.DataFrame(data, columns=[self.sentiment_table.horizontalHeaderItem(
                        i).text() for i in range(self.sentiment_table.columnCount())])
                    if file_path.endswith('.xlsx'):
                        df.to_excel(file_path, index=False)
                    else:
                        df.to_csv(file_path, index=False, encoding='utf-8-sig')
                    self.log_manager.info(f"表格已导出到: {file_path}")
                    QMessageBox.information(
                        self, "导出成功", f"表格已导出到: {file_path}")
                elif file_path.endswith('.png'):
                    # 导出图表
                    if hasattr(self, 'sentiment_chart_view'):
                        pixmap = self.sentiment_chart_view.grab()
                        pixmap.save(file_path)
                        self.log_manager.info(f"图表已导出到: {file_path}")
                        QMessageBox.information(
                            self, "导出成功", f"图表已导出到: {file_path}")
                    else:
                        self.log_manager.warning("未找到图表控件，无法导出图表")
                        QMessageBox.warning(self, "导出失败", "未找到图表控件，无法导出图表")
        except Exception as e:
            self.log_manager.error(f"导出失败: {str(e)}")
            QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")

    def show_alert_dialog(self):
        """显示预警设置对话框"""
        # TODO: 实现预警设置对话框
        pass

    def get_cached_sentiment(self) -> dict:
        """获取缓存的市场情绪数据，智能动态失效"""
        now = datetime.now()
        if hasattr(self, '_sentiment_cache') and hasattr(self, '_sentiment_cache_time'):
            # 智能缓存时长：数据越新缓存越久，最短30秒，最长300秒
            cache_data = self._sentiment_cache
            ts = cache_data.get('timestamp')
            if ts and isinstance(ts, datetime):
                age = (now - ts).total_seconds()
                if age < 60:
                    max_age = 300  # 5分钟
                elif age < 300:
                    max_age = 120  # 2分钟
                else:
                    max_age = 30   # 30秒
            else:
                max_age = 60
            if (now - self._sentiment_cache_time).total_seconds() < max_age:
                return self._sentiment_cache
        return None

    def show_loading_skeleton(self):
        """显示骨架屏动画（增强版）"""
        if not hasattr(self, '_skeleton_label'):
            self._skeleton_label = QLabel("加载中...", self)
            self._skeleton_label.setAlignment(Qt.AlignCenter)
            self._skeleton_label.setStyleSheet(
                "font-size: 22px; color: #cccccc; background: #f7f9fa; border-radius: 12px; padding: 32px 0; border: 2px dashed #90caf9; box-shadow: 0 4px 24px rgba(33,150,243,0.10);")
            try:
                self._movie = QMovie("resources/images/loading.gif")
                if self._movie.isValid():
                    self._skeleton_label.setMovie(self._movie)
                    self._movie.start()
            except Exception:
                pass
            self.main_layout.addWidget(self._skeleton_label)
        self._skeleton_label.show()
        self._skeleton_label.raise_()

    def hide_loading_skeleton(self):
        if hasattr(self, '_skeleton_label'):
            self._skeleton_label.hide()

    def update_sentiment_data(self, data: dict):
        """只更新情绪分数和多市场走势"""
        try:
            self.log_manager.info(f"收到市场情绪数据: {data}")
            # 1. 情绪分数
            score = data.get('sentiment_index')
            if isinstance(score, (int, float)):
                self.sentiment_score_label.setText(f"{score:.2f}")
                self.sentiment_score_label.setStyleSheet(
                    "font-size: 20px; font-weight: bold; color: #1976d2; padding: 4px 12px; border-radius: 8px; background: #e3f2fd;")
                self.log_manager.info(f"市场情绪分数显示: {score:.2f}")
            else:
                self.sentiment_score_label.setText("暂无数据")
                self.sentiment_score_label.setStyleSheet(
                    "font-size: 20px; color: #999999; font-weight: bold;")
                self.log_manager.warning("市场情绪分数字段缺失或为None")

            # 2. 多市场情绪指数走势
            if hasattr(self.data_manager, 'get_market_sentiment_history'):
                all_history = self.data_manager.get_market_sentiment_history(
                    days=60)
                self._update_sentiment_chart_multi(all_history)
            else:
                self._update_sentiment_chart_multi([])

            # 3. 热度指示器
            if hasattr(self, 'heat_progress'):
                heat = data.get('market_heat')
                if heat is not None:
                    try:
                        heat = float(heat)
                        self.heat_progress.setValue(int(heat))
                        self.log_manager.info(f"市场热度显示: {heat}")
                    except Exception:
                        self.heat_progress.setValue(0)
                        self.log_manager.warning("市场热度字段格式异常")
                else:
                    self.heat_progress.setValue(0)
                    self.log_manager.warning("市场热度字段缺失")
        except Exception as e:
            self.log_manager.error(f"更新市场情绪数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _update_sentiment_chart_multi(self, all_history):
        """多市场情绪走势曲线"""
        try:
            if not hasattr(self, 'sentiment_chart'):
                return
            self.sentiment_chart.removeAllSeries()
            has_data = False
            for market_data in all_history:
                market = market_data.get('market', '未知')
                history = market_data.get('history', [])
                if not history:
                    continue
                series = QLineSeries()
                series.setName(market)
                for i, item in enumerate(history):
                    v = item.get('sentiment_index')
                    if v is not None:
                        series.append(i, float(v))
                if series.count() > 0:
                    self.sentiment_chart.addSeries(series)
                    series.attachAxis(self.sentiment_axis_x)
                    series.attachAxis(self.sentiment_axis_y)
                    has_data = True
            # X轴范围
            self.sentiment_axis_x.setRange(0, 59)
            self.sentiment_axis_x.setTitleText("最近60天")
            # Y轴范围自适应
            self.sentiment_axis_y.setRange(0, 2)
            self.sentiment_axis_y.setTitleText("情绪指数/收盘价")
            if not has_data:
                self.sentiment_chart.setTitle("暂无数据")
            else:
                self.sentiment_chart.setTitle("市场情绪走势（近60天）")
            if hasattr(self, 'sentiment_chart_view'):
                self.sentiment_chart_view.update()
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"多市场情绪走势渲染失败: {str(e)}")

    def _update_ui_safely(self, data: dict):
        """在主线程中安全地更新UI，数据缺失时所有UI区域显示暂无数据，并写日志"""
        try:
            if not data or data.get('sentiment_index') is None:
                self.sentiment_score_label.setText("暂无市场情绪数据")
                self.sentiment_score_label.setStyleSheet(
                    "font-size: 20px; color: #999999; font-weight: bold;")
                if hasattr(self, 'sentiment_table'):
                    self.sentiment_table.clearContents()
                    for row in range(self.sentiment_table.rowCount()):
                        for col in range(self.sentiment_table.columnCount()):
                            self.sentiment_table.setItem(
                                row, col, QTableWidgetItem("暂无数据"))
                if hasattr(self, 'sentiment_series'):
                    self.sentiment_series.clear()
                if hasattr(self, 'heat_progress'):
                    self.heat_progress.setValue(0)
                self.log_manager.warning("UI刷新时市场情绪数据缺失，所有UI区域已置为暂无数据")
                return
            self._data_cache.update(data)
            self._cache_time[datetime.now()] = data
            self._update_sentiment_index(data)
            self._update_heat_indicator(data)
            self._update_charts(data)
            self._check_alerts(data)
        except Exception as e:
            self.log_manager.error(f"更新UI失败: {e}")

    def _update_sentiment_index(self, data: dict):
        """
        更新情绪分数标签
        Args:
            data: 市场情绪数据字典
        """
        try:
            sentiment_index = data.get('sentiment_index', 0)
            if hasattr(self, 'sentiment_score_label'):
                self.sentiment_score_label.setText(f"{sentiment_index:.2f}")
                # 设置颜色
                if sentiment_index >= 70:
                    self.sentiment_score_label.setStyleSheet(
                        "font-size: 16px; font-weight: bold; color: #ff4d4f;")
                elif sentiment_index >= 50:
                    self.sentiment_score_label.setStyleSheet(
                        "font-size: 16px; font-weight: bold; color: #faad14;")
                else:
                    self.sentiment_score_label.setStyleSheet(
                        "font-size: 16px; font-weight: bold; color: #52c41a;")
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.log(f"更新情绪分数标签失败: {e}", LogLevel.ERROR)

    def _update_sentiment_chart(self, data):
        """更新情绪图表

        Args:
            data: 市场情绪数据
        """
        try:
            if not hasattr(self, 'sentiment_chart') or not hasattr(self, 'sentiment_series'):
                if hasattr(self, 'log_manager'):
                    self.log_manager.warning("情绪图表未初始化")
                return
            # 清除现有数据
            self.sentiment_series.clear()
            # 添加数据点
            sentiment_data = data.get('sentiment_index', {})
            if isinstance(sentiment_data, dict):
                for i, (date, value) in enumerate(sentiment_data.items()):
                    if isinstance(value, (int, float)):
                        self.sentiment_series.append(i, int(value))
            elif isinstance(sentiment_data, (list, tuple)):
                for i, value in enumerate(sentiment_data):
                    if isinstance(value, (int, float)):
                        self.sentiment_series.append(i, int(value))
            elif isinstance(sentiment_data, (int, float)):
                self.sentiment_series.append(0, int(sentiment_data))
            # 更新X轴范围
            points_count = self.sentiment_series.count()
            if points_count > 0:
                self.sentiment_axis_x.setRange(0, points_count - 1)
            # 更新Y轴范围（保持0-100的整数范围）
            self.sentiment_axis_y.setRange(0, 100)
            # 更新图表
            if hasattr(self, 'sentiment_chart_view'):
                self.sentiment_chart_view.update()
            if hasattr(self, 'log_manager'):
                self.log_manager.info("情绪图表更新成功")
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"更新情绪图表失败: {str(e)}")

    def _update_heat_indicator(self, data):
        """更新热度指示器"""
        try:
            heat_value = data.get('market_heat', 0)
            if isinstance(heat_value, (int, float)):
                self.heat_progress.setValue(int(heat_value))
                self._update_heat_color(float(heat_value))
            else:
                self.log_manager.log(f"无效的热度值: {heat_value}", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"更新热度指示器失败: {e}", LogLevel.ERROR)

    def _check_alerts(self, data):
        """检查预警条件"""
        for indicator, alert in self._alerts.items():
            value = data.get(indicator, 0)
            if value >= alert['threshold']:
                alert['callback'](indicator, value)

    def closeEvent(self, event):
        """关闭事件处理"""
        if hasattr(self, 'update_thread'):
            self.update_thread.stop()
            self.update_thread.wait()
        super().closeEvent(event)

    def _get_status(self, name: str, value: float) -> str:
        """获取指标状态

        Args:
            name: 指标名称
            value: 指标值

        Returns:
            str: 状态描述
        """
        if name == '情绪指数':
            if value > 50:
                return '乐观'
            elif value < -50:
                return '悲观'
            else:
                return '中性'
        elif name == "成交量比":
            if value > 1.5:
                return "活跃"
            elif value < 0.5:
                return "低迷"
            else:
                return "正常"
        elif name == "上涨家数":
            if value > 2000:
                return "强势"
            elif value < 500:
                return "弱势"
            else:
                return "中性"
        elif name == "下跌家数":
            if value > 2000:
                return "弱势"
            elif value < 500:
                return "强势"
            else:
                return "中性"
        return "未知"

    def _get_status_color(self, status):
        """获取状态颜色"""
        color_map = {
            "极度悲观": "#FF1744",
            "悲观": "#FF5252",
            "中性": "#757575",
            "乐观": "#69F0AE",
            "极度乐观": "#00C853",
            "极度看空": "#FF1744",
            "看空": "#FF5252",
            "看多": "#69F0AE",
            "极度看多": "#00C853",
            "低迷": "#FF1744",
            "偏低": "#FF5252",
            "正常": "#757575",
            "活跃": "#69F0AE",
            "热络": "#00C853",
            "过热": "#FF1744",
            "大幅流出": "#FF1744",
            "流出": "#FF5252",
            "平衡": "#757575",
            "流入": "#69F0AE",
            "大幅流入": "#00C853"
        }
        return QColor(color_map.get(status, "#757575"))

    def _update_heat_color(self, value):
        """更新热度指示器颜色"""
        if value < 20:
            color = "#FF1744"  # 深红
        elif value < 40:
            color = "#FF5252"  # 红
        elif value < 60:
            color = "#757575"  # 灰
        elif value < 80:
            color = "#69F0AE"  # 浅绿
        else:
            color = "#00C853"  # 深绿

        self.heat_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)

    def handle_error(self, error_msg: str):
        """处理错误信息

        Args:
            error_msg: 错误信息
        """
        self.log_manager.log(error_msg, LogLevel.ERROR)
        if hasattr(self, 'status_label'):
            self.status_label.setText(error_msg)
            self.status_label.setStyleSheet("color: #FF5252;")  # 红色

    def handle_status_change(self, status: str):
        """处理状态变化

        Args:
            status: 状态信息
        """
        if hasattr(self, 'log_manager') and self.log_manager:
            self.log_manager.log(f"[状态变更] {status}", LogLevel.INFO)
        if hasattr(self, 'status_label'):
            self.status_label.setText(status)
            self.status_label.setStyleSheet("color: #666666;")  # 灰色

    def on_analyze(self):
        """分析前校验参数并强制拉取最新数据"""
        valid, msg = self.validate_params()
        if not valid:
            self.set_status_message(msg, error=True)
            self.sentiment_threshold.setToolTip(msg)
            return
        self.set_status_message("参数校验通过，正在分析...", error=False)
        self.sentiment_threshold.setToolTip("")
        try:
            self.log_manager.info("分析按钮被点击，强制拉取最新市场情绪数据")
            if hasattr(self.data_manager, 'get_market_sentiment'):
                data = self.data_manager.get_market_sentiment()
                if data:
                    self.update_sentiment_data(data)
                    self.set_status_message("分析完成", error=False)
                else:
                    self.set_status_message("未获取到市场情绪数据", error=True)
                    self.log_manager.warning("分析未获取到数据")
            else:
                self.set_status_message(
                    "数据管理器未实现get_market_sentiment", error=True)
                self.log_manager.error("数据管理器未实现get_market_sentiment")
        except Exception as e:
            self.log_manager.error(f"分析失败: {str(e)}")
            self.set_status_message(f"分析失败: {str(e)}", error=True)
            QMessageBox.critical(self, "分析错误", f"分析失败: {str(e)}")

    def show_template_manager_dialog(self):
        """显示模板管理对话框，支持模板的增删改查，详细日志"""
        try:
            from components.template_manager import TemplateManagerDialog
            dialog = TemplateManagerDialog(
                template_dir="templates/market_sentiment",
                log_manager=self.log_manager,
                parent=self
            )
            if dialog.exec_() == QDialog.Accepted:
                template = dialog.get_current_template()
                if template:
                    # TODO: 回填参数到主面板（如有参数结构）
                    self.log_manager.info(f"已应用模板: {template.get('name', '')}")
                    # self.apply_template_params(template.get('params', {}))
        except Exception as e:
            self.log_manager.error(f"模板管理对话框弹出失败: {str(e)}")
            QMessageBox.critical(self, "模板管理错误", f"模板管理对话框弹出失败: {str(e)}")

    def _update_charts(self, data: dict):
        """
        更新市场情绪相关图表（兼容入口）
        Args:
            data: 市场情绪数据
        """
        self._update_sentiment_chart(data)

    def update_auto_refresh_interval(self):
        """更新自动刷新间隔"""
        interval = self.auto_refresh_spin.value()
        if hasattr(self, 'update_thread'):
            self.update_thread.update_interval = interval
        self.log_manager.info(f"自动刷新间隔已设置为{interval}秒")

    def show_custom_indicator_dialog(self):
        """显示自定义指标管理对话框，支持自定义指标的增删改查，详细日志"""
        try:
            from components.custom_indicator_manager import CustomIndicatorManagerDialog
            dialog = CustomIndicatorManagerDialog(
                indicator_file="config/custom_indicators.json",
                log_manager=self.log_manager,
                parent=self
            )
            dialog.exec_()
        except Exception as e:
            self.log_manager.error(f"自定义指标对话框弹出失败: {str(e)}")
            QMessageBox.critical(self, "自定义指标错误", f"自定义指标对话框弹出失败: {str(e)}")

    def _run_analysis_async(self, button, analysis_func, *args, **kwargs):
        button.setEnabled(False)
        self.show_progress("分析中，请稍候...")

        def task():
            try:
                result = analysis_func(*args, **kwargs)
                return result
            except Exception as e:
                if hasattr(self, 'log_manager'):
                    self.log_manager.error(f"分析异常: {str(e)}")
                return None

        def on_done(future):
            button.setEnabled(True)
            self.hide_progress()
            res = future.result()
        from concurrent.futures import ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(task)
        future.add_done_callback(
            lambda f: QTimer.singleShot(0, lambda: on_done(f)))

    def analyze_sentiment(self):
        self._run_analysis_async(
            self.analyze_button, self._analyze_sentiment_impl)

    def export_data(self):
        self._run_analysis_async(self.export_button, self._export_data_impl)

    def refresh_data(self):
        self._run_analysis_async(self.refresh_button, self._refresh_data_impl)
    # ... 其余耗时分析按钮同理 ...
