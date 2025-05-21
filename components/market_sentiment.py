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
from components.template_manager import TemplateManager


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
        # 创建主布局
        self.main_layout = QVBoxLayout(self)

        # 创建情绪分数显示
        score_layout = QHBoxLayout()
        score_label = QLabel("市场情绪分数:")
        self.sentiment_score_label = QLabel("0.00")
        self.sentiment_score_label.setStyleSheet(
            "font-size: 16px; font-weight: bold;")
        score_layout.addWidget(score_label)
        score_layout.addWidget(self.sentiment_score_label)
        score_layout.addStretch()
        self.main_layout.addLayout(score_layout)

        # 创建指标卡片区域
        self.indicator_cards = QGridLayout()
        self.main_layout.addLayout(self.indicator_cards)

        # 创建情绪指标表格
        self.create_sentiment_table(self.main_layout)

        # 创建情绪图表
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

        # 创建控制按钮
        self.create_control_buttons(self.main_layout)

        # 模板管理按钮
        manage_button = QPushButton("模板管理")
        manage_button.clicked.connect(self.show_template_manager_dialog)
        self.main_layout.addWidget(manage_button)

    def create_indicator_cards(self, layout):
        """创建主要指标卡片，增加美化效果"""
        indicators = [
            ("大盘强度", "70%", "强势"),
            ("市场宽度", "65%", "偏强"),
            ("资金趋势", "↑", "流入"),
            ("板块热度", "85", "高热"),
            ("情绪指数", "58.6", "乐观"),
            ("技术评分", "75", "看多"),
            ("主力资金流向", "+12亿", "流入"),
            ("北向资金", "+5亿", "流入")
        ]
        for i, (name, value, status) in enumerate(indicators):
            card = QFrame()
            card.setFrameStyle(QFrame.Box | QFrame.Raised)
            card.setLineWidth(2)
            card.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e3f2fd, stop:1 #bbdefb);
                    border-radius: 18px;
                    border: 1.5px solid #90caf9;
                    box-shadow: 0px 4px 16px rgba(33,150,243,0.08);
                    margin: 12px;
                    padding: 18px 12px 12px 12px;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)
            # 指标名称
            name_label = QLabel(name)
            name_label.setStyleSheet(
                "font-weight: bold; color: #1976d2; font-size: 15px;")
            card_layout.addWidget(name_label)
            # 指标值
            value_label = QLabel(value)
            value_label.setStyleSheet(
                "font-size: 32px; color: #1565c0; font-weight: bold; margin: 6px 0;")
            card_layout.addWidget(value_label)
            # 状态
            status_label = QLabel(status)
            status_color = "#43a047" if "强" in status or "多" in status or "入" in status or "高" in status else "#e53935"
            status_label.setStyleSheet(
                f"background: {status_color}; color: white; border-radius: 10px; padding: 2px 12px; font-size: 13px; font-weight: bold;")
            card_layout.addWidget(status_label)
            self.indicator_cards.addWidget(card, i // 3, i % 3)
        layout.addLayout(self.indicator_cards)

    def create_sentiment_table(self, layout):
        """美化情绪指标表格"""
        self.sentiment_table = QTableWidget()
        self.sentiment_table.setColumnCount(4)
        self.sentiment_table.setRowCount(8)
        self.sentiment_table.setHorizontalHeaderLabels([
            "指标", "数值", "变化", "状态"])
        indicators = [
            "市场情绪指数",
            "涨跌比",
            "成交量比",
            "换手率",
            "北向资金",
            "融资余额",
            "期权PCR",
            "恐慌指数"
        ]
        self.sentiment_table.setVerticalHeaderLabels(indicators)
        self.sentiment_table.setStyleSheet("""
            QTableWidget {
                background: #e3f2fd;
                alternate-background-color: #bbdefb;
                selection-background-color: #90caf9;
                border-radius: 8px;
            }
            QHeaderView::section {
                background: #1976d2;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: 15px;
            }
            QTableWidget::item {
                padding: 6px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.sentiment_table)

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
                border-radius: 8px;
                text-align: center;
                background: #e3f2fd;
                height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #43a047, stop:1 #1976d2);
                border-radius: 8px;
            }
        """)
        heat_layout.addWidget(self.heat_progress)
        layout.addLayout(heat_layout)

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
        """导出市场情绪数据"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出数据", "", "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )
            if filename:
                data = pd.DataFrame(self._data_cache)
                if filename.endswith('.xlsx'):
                    data.to_excel(filename)
                else:
                    data.to_csv(filename)
                self.log_manager.log(f"数据已导出到: {filename}", LogLevel.INFO)
        except Exception as e:
            self.log_manager.log(f"导出数据失败: {e}", LogLevel.ERROR)

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
        """显示骨架屏动画"""
        if not hasattr(self, '_skeleton_label'):
            self._skeleton_label = QLabel("加载中...", self)
            self._skeleton_label.setAlignment(Qt.AlignCenter)
            self._skeleton_label.setStyleSheet(
                "font-size: 18px; color: #cccccc;")
            try:
                self._movie = QMovie("resources/images/loading.gif")
                if self._movie.isValid():
                    self._skeleton_label.setMovie(self._movie)
                    self._movie.start()
            except Exception:
                pass
            self.main_layout.addWidget(self._skeleton_label)
        self._skeleton_label.show()

    def hide_loading_skeleton(self):
        if hasattr(self, '_skeleton_label'):
            self._skeleton_label.hide()

    def update_sentiment_data(self, data: dict):
        """更新市场情绪数据

        Args:
            data: 市场情绪数据字典
        """
        try:
            # 新增：无数据友好提示+骨架屏
            if not data or not data.get('sentiment_index'):
                self.show_loading_skeleton()
                self.sentiment_score_label.setText("暂无市场情绪数据")
                self.sentiment_score_label.setStyleSheet(
                    "font-size: 16px; color: #999999;")
                if hasattr(self, 'sentiment_table'):
                    self.sentiment_table.clearContents()
                return
            self.hide_loading_skeleton()
            # 新增：缓存数据
            self._sentiment_cache = data
            self._sentiment_cache_time = datetime.now()
            # 使用QTimer.singleShot确保在主线程中更新UI
            QTimer.singleShot(0, lambda: self._update_ui_safely(data))

        except Exception as e:
            self.log_manager.log(f"更新市场情绪数据失败: {e}", LogLevel.ERROR)

    def _update_ui_safely(self, data: dict):
        """在主线程中安全地更新UI

        Args:
            data: 市场情绪数据字典
        """
        try:
            # 更新数据缓存
            self._data_cache.update(data)
            self._cache_time[datetime.now()] = data

            # 更新各个指标
            self._update_sentiment_index(data)
            self._update_heat_indicator(data)
            self._update_charts(data)
            self._update_tables(data)

            # 检查预警条件
            self._check_alerts(data)

        except Exception as e:
            self.log_manager.log(f"更新UI失败: {e}", LogLevel.ERROR)

    def _update_sentiment_chart(self, data):
        """更新情绪图表

        Args:
            data: 市场情绪数据
        """
        try:
            if not hasattr(self, 'sentiment_chart') or not hasattr(self, 'sentiment_series'):
                self.log_manager.warning("情绪图表未初始化")
                return

            # 清除现有数据
            self.sentiment_series.clear()

            # 添加数据点
            sentiment_data = data.get('sentiment_index', {})
            if isinstance(sentiment_data, dict):
                for i, (date, value) in enumerate(sentiment_data.items()):
                    if isinstance(value, (int, float)):
                        self.sentiment_series.append(i, int(value))  # 转换为整数
            elif isinstance(sentiment_data, (list, tuple)):
                for i, value in enumerate(sentiment_data):
                    if isinstance(value, (int, float)):
                        self.sentiment_series.append(i, int(value))  # 转换为整数

            # 更新X轴范围
            points_count = self.sentiment_series.count()
            if points_count > 0:
                self.sentiment_axis_x.setRange(0, points_count - 1)

            # 更新Y轴范围（保持0-100的整数范围）
            self.sentiment_axis_y.setRange(0, 100)

            # 更新图表
            if hasattr(self, 'sentiment_chart_view'):
                self.sentiment_chart_view.update()

            self.log_manager.info("情绪图表更新成功")

        except Exception as e:
            self.log_manager.error(f"更新情绪图表失败: {str(e)}")
            raise

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

    def _update_sentiment_table(self, data: Dict[str, Any]) -> None:
        """更新情绪指标表格

        Args:
            data: 市场情绪数据
        """
        try:
            # 获取情绪分数
            sentiment_score = data.get('sentiment_score', 0)

            # 更新情绪分数标签
            if hasattr(self, 'sentiment_score_label'):
                self.sentiment_score_label.setText(f"{sentiment_score:.2f}")

                # 设置情绪分数标签颜色
                if sentiment_score >= 70:
                    self.sentiment_score_label.setStyleSheet(
                        "font-size: 16px; font-weight: bold; color: #ff4d4f;")
                elif sentiment_score >= 50:
                    self.sentiment_score_label.setStyleSheet(
                        "font-size: 16px; font-weight: bold; color: #faad14;")
                else:
                    self.sentiment_score_label.setStyleSheet(
                        "font-size: 16px; font-weight: bold; color: #52c41a;")

            # 获取指数数据
            indices_data = data.get('indices', {})
            if not indices_data:
                indices_data = data.get('statistics', {}).get('indices', {})

            # 更新指数数据
            for code, index_data in indices_data.items():
                try:
                    # 获取指数名称
                    name = index_data.get('name', code)

                    # 获取收盘价
                    close = float(index_data.get('close', 0))

                    # 计算涨跌幅
                    change = float(index_data.get('change', 0))
                    change_pct = float(index_data.get('change_pct', 0))

                    # 更新表格
                    row = self.sentiment_table.rowCount()
                    self.sentiment_table.insertRow(row)

                    # 设置指数名称
                    name_item = QTableWidgetItem(name)
                    name_item.setTextAlignment(Qt.AlignCenter)
                    self.sentiment_table.setItem(row, 0, name_item)

                    # 设置收盘价
                    close_item = QTableWidgetItem(f"{close:.2f}")
                    close_item.setTextAlignment(Qt.AlignCenter)
                    self.sentiment_table.setItem(row, 1, close_item)

                    # 设置涨跌幅
                    change_item = QTableWidgetItem(f"{change:.2f}")
                    change_item.setTextAlignment(Qt.AlignCenter)
                    self.sentiment_table.setItem(row, 2, change_item)

                    # 设置涨跌百分比
                    change_pct_item = QTableWidgetItem(f"{change_pct:.2f}%")
                    change_pct_item.setTextAlignment(Qt.AlignCenter)

                    # 设置涨跌百分比颜色
                    if change_pct > 0:
                        change_pct_item.setForeground(QColor("#ff4d4f"))
                    elif change_pct < 0:
                        change_pct_item.setForeground(QColor("#52c41a"))
                    else:
                        change_pct_item.setForeground(QColor("#000000"))

                    self.sentiment_table.setItem(row, 3, change_pct_item)

                except Exception as e:
                    self.log_manager.log(
                        f"更新指数 {code} 数据失败: {str(e)}", LogLevel.ERROR)
                    continue

            # 调整表格列宽
            self.sentiment_table.resizeColumnsToContents()

        except Exception as e:
            self.log_manager.log(f"更新情绪指标表格失败: {str(e)}", LogLevel.ERROR)
            if hasattr(self, 'sentiment_score_label'):
                self.sentiment_score_label.setText("更新失败")
                self.sentiment_score_label.setStyleSheet(
                    "font-size: 16px; font-weight: bold; color: #ff4d4f;")

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

    def update_indicator_cards(self, data: Dict[str, Any]):
        """更新指标卡片

        Args:
            data: 市场情绪数据
        """
        try:
            # 清除现有卡片
            while self.indicator_cards.count():
                item = self.indicator_cards.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 创建新的指标卡片
            indicators = [
                ('sentiment_score', '情绪指数', '分'),
                ('volume_ratio', '成交量比', '倍'),
                ('advance_decline.advance', '上涨家数', '家'),
                ('advance_decline.decline', '下跌家数', '家')
            ]

            for i, (key, name, unit) in enumerate(indicators):
                card = QFrame()
                card.setFrameStyle(QFrame.Box | QFrame.Raised)
                card.setLineWidth(2)
                card.setStyleSheet("""
                    QFrame {
                        background-color: #ffffff;
                        border-radius: 10px;
                        padding: 10px;
                    }
                """)

                card_layout = QVBoxLayout(card)

                # 指标名称
                name_label = QLabel(name)
                name_label.setStyleSheet("font-weight: bold; color: #333333;")
                card_layout.addWidget(name_label)

                # 获取指标值
                value = data
                for k in key.split('.'):
                    value = value.get(k, 0)

                # 指标值
                value_label = QLabel(f"{value}{unit}")
                value_label.setStyleSheet("font-size: 18px; color: #2196F3;")
                card_layout.addWidget(value_label)

                # 状态
                status = self._get_status(name, value)
                status_label = QLabel(status)
                status_color = "#4CAF50" if "强" in status or "多" in status or "入" in status else "#FF5722"
                status_label.setStyleSheet(f"color: {status_color};")
                card_layout.addWidget(status_label)

                self.indicator_cards.addWidget(card, i // 2, i % 2)

        except Exception as e:
            self.log_manager.log(f"更新指标卡片失败: {str(e)}", LogLevel.ERROR)

    def create_market_heat_chart(self):
        """创建市场热度图表"""
        try:
            self.heat_chart = QChart()
            self.heat_chart.setTitle("市场热度")
            self.heat_chart.setAnimationOptions(QChart.SeriesAnimations)

            self.heat_series = QLineSeries()
            self.heat_series.setName("热度")

            self.axisX = QValueAxis()
            self.axisX.setTitleText("时间")
            self.axisX.setLabelFormat("%d")

            self.axisY = QValueAxis()
            self.axisY.setTitleText("热度")
            self.axisY.setRange(0, 100)  # 修改为整数
            self.axisY.setLabelFormat("%d")

            self.heat_chart.addSeries(self.heat_series)
            self.heat_chart.addAxis(self.axisX, Qt.AlignBottom)
            self.heat_chart.addAxis(self.axisY, Qt.AlignLeft)

            self.heat_series.attachAxis(self.axisX)
            self.heat_series.attachAxis(self.axisY)

            self.heat_chart_view = QChartView(self.heat_chart)
            self.heat_chart_view.setRenderHint(QPainter.Antialiasing)

            self.heat_progress = QProgressBar()
            self.heat_progress.setRange(0, 100)  # 已经是整数
            self.heat_progress.setValue(0)

            self.log_manager.info("市场热度图表创建成功")
        except Exception as e:
            self.log_manager.error(f"创建市场热度图表失败: {str(e)}")

    def update_market_heat_chart(self, data):
        """更新市场热度图表"""
        try:
            if not data:
                self.log_manager.warning("没有市场热度数据")
                return

            self.heat_series.clear()

            # 添加数据点
            for i, value in enumerate(data):
                self.heat_series.append(i, int(value))  # 转换为整数

            # 更新X轴范围
            self.axisX.setRange(0, len(data) - 1)

            # 更新Y轴范围
            self.axisY.setRange(0, 100)  # 修改为整数

            # 更新进度条
            latest_value = int(data[-1])  # 转换为整数
            self.heat_progress.setValue(latest_value)

            self.log_manager.info(f"市场热度图表更新成功，当前热度: {latest_value}")
        except Exception as e:
            self.log_manager.error(f"更新市场热度图表失败: {str(e)}")

    def validate_params(self) -> (bool, str):
        """
        校验情绪阈值参数，范围0-100
        """
        valid, msg = super().validate_params()
        # 可扩展自定义校验
        return valid, msg

    def on_analyze(self):
        """分析前校验参数"""
        valid, msg = self.validate_params()
        if not valid:
            self.set_status_message(msg, error=True)
            self.sentiment_threshold.setToolTip(msg)
            return
        self.set_status_message("参数校验通过", error=False)
        self.sentiment_threshold.setToolTip("")
        # 继续原有分析逻辑
        super().on_analyze()

    def show_template_manager_dialog(self):
        # 复用StockScreenerWidget的模板管理对话框逻辑
        QMessageBox.information(
            self, "模板管理", "此处可集成批量模板管理UI，支持导入、导出、删除、重命名、应用等功能。")
