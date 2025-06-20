"""
UI工厂模块

负责创建各种UI组件，减少主窗口代码复杂度
"""

from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QGroupBox, QFormLayout, QDateEdit,
    QFrame, QSizePolicy, QSplitter
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont


class UIFactory:
    """UI组件工厂类"""

    @staticmethod
    def create_toolbar_combo(items: list, current_text: str = "", tooltip: str = "") -> QComboBox:
        """创建工具栏下拉框"""
        combo = QComboBox()
        combo.addItems(items)
        if current_text:
            combo.setCurrentText(current_text)
        if tooltip:
            combo.setToolTip(tooltip)
        return combo

    @staticmethod
    def create_date_edit(default_date: QDate = None) -> QDateEdit:
        """创建日期编辑控件"""
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        if default_date:
            date_edit.setDate(default_date)
        else:
            date_edit.setDate(QDate.currentDate())
        return date_edit

    @staticmethod
    def create_toolbar_layout() -> QHBoxLayout:
        """创建标准工具栏布局"""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        return layout

    @staticmethod
    def create_period_controls() -> tuple:
        """创建周期控制组件"""
        period_label = QLabel("周期:")
        period_combo = UIFactory.create_toolbar_combo([
            "分时", "5分钟", "15分钟", "30分钟", "60分钟", "日线", "周线", "月线"
        ], "日线", "选择K线周期")
        return period_label, period_combo

    @staticmethod
    def create_time_range_controls() -> tuple:
        """创建时间范围控制组件"""
        time_range_label = QLabel("时间范围:")
        time_range_combo = UIFactory.create_toolbar_combo([
            "最近7天", "最近30天", "最近90天", "最近180天",
            "最近1年", "最近2年", "最近3年", "最近5年", "全部"
        ], "最近1年", "选择时间范围")
        return time_range_label, time_range_combo

    @staticmethod
    def create_chart_type_controls() -> tuple:
        """创建图表类型控制组件"""
        chart_type_label = QLabel("图表类型:")
        chart_type_combo = UIFactory.create_toolbar_combo([
            "K线图", "分时图", "美国线", "收盘价"
        ], "K线图", "选择图表类型")
        return chart_type_label, chart_type_combo

    @staticmethod
    def create_date_range_controls() -> tuple:
        """创建日期范围控制组件"""
        date_label = QLabel("回测区间:")
        start_date_edit = UIFactory.create_date_edit(QDate.currentDate().addYears(-1))
        end_date_edit = UIFactory.create_date_edit(QDate.currentDate())
        return date_label, start_date_edit, end_date_edit

    @staticmethod
    def create_chart_toolbar() -> tuple:
        """创建完整的图表工具栏"""
        toolbar_layout = UIFactory.create_toolbar_layout()

        # 周期控制
        period_label, period_combo = UIFactory.create_period_controls()
        toolbar_layout.addWidget(period_label)
        toolbar_layout.addWidget(period_combo)

        # 时间范围控制
        time_range_label, time_range_combo = UIFactory.create_time_range_controls()
        toolbar_layout.addWidget(time_range_label)
        toolbar_layout.addWidget(time_range_combo)

        # 日期范围控制
        date_label, start_date_edit, end_date_edit = UIFactory.create_date_range_controls()
        toolbar_layout.addWidget(date_label)
        toolbar_layout.addWidget(start_date_edit)
        toolbar_layout.addWidget(QLabel("至"))
        toolbar_layout.addWidget(end_date_edit)

        # 图表类型控制
        chart_type_label, chart_type_combo = UIFactory.create_chart_type_controls()
        toolbar_layout.addWidget(chart_type_label)
        toolbar_layout.addWidget(chart_type_combo)

        toolbar_layout.addStretch()

        return (toolbar_layout, period_combo, time_range_combo,
                start_date_edit, end_date_edit, chart_type_combo)

    @staticmethod
    def create_splitter(orientation: Qt.Orientation, handle_width: int = 1,
                        collapsible: bool = False) -> QSplitter:
        """创建分割器"""
        splitter = QSplitter(orientation)
        splitter.setHandleWidth(handle_width)
        splitter.setChildrenCollapsible(collapsible)
        return splitter

    @staticmethod
    def create_panel_widget(size_policy: tuple = None, min_width: int = None) -> QWidget:
        """创建面板控件"""
        panel = QWidget()
        if size_policy:
            panel.setSizePolicy(*size_policy)
        if min_width:
            panel.setMinimumWidth(min_width)
        return panel

    @staticmethod
    def create_group_box(title: str, layout_type: str = "vertical") -> tuple:
        """创建分组框和布局"""
        group = QGroupBox(title)
        if layout_type == "vertical":
            layout = QVBoxLayout(group)
        elif layout_type == "horizontal":
            layout = QHBoxLayout(group)
        elif layout_type == "grid":
            layout = QGridLayout(group)
        elif layout_type == "form":
            layout = QFormLayout(group)
        else:
            layout = QVBoxLayout(group)
        return group, layout

    @staticmethod
    def create_line_separator() -> QFrame:
        """创建分割线"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setFixedHeight(2)
        return line

    @staticmethod
    def apply_widget_style(widget: QWidget, styles: Dict[str, Any]):
        """应用控件样式"""
        try:
            if 'background_color' in styles:
                widget.setStyleSheet(f"background-color: {styles['background_color']};")
            if 'font_size' in styles:
                font = widget.font()
                font.setPointSize(styles['font_size'])
                widget.setFont(font)
            if 'font_weight' in styles:
                font = widget.font()
                font.setWeight(styles['font_weight'])
                widget.setFont(font)
        except Exception as e:
            print(f"应用样式失败: {str(e)}")

    @staticmethod
    def create_parameter_controls(params: Dict[str, Any]) -> Dict[str, QWidget]:
        """创建参数控制组件"""
        controls = {}

        for name, config in params.items():
            if isinstance(config, dict):
                control_type = config.get('type', 'spinbox')
                if control_type == 'spinbox':
                    control = QSpinBox()
                    control.setRange(config.get('min', 0), config.get('max', 100))
                    control.setValue(config.get('default', 0))
                elif control_type == 'double_spinbox':
                    control = QDoubleSpinBox()
                    control.setRange(config.get('min', 0.0), config.get('max', 100.0))
                    control.setValue(config.get('default', 0.0))
                    control.setDecimals(config.get('decimals', 2))
                elif control_type == 'combo':
                    control = QComboBox()
                    control.addItems(config.get('items', []))
                    if 'default' in config:
                        control.setCurrentText(config['default'])
                else:
                    control = QSpinBox()  # 默认类型
                controls[name] = control

        return controls

    @staticmethod
    def set_widget_properties(widget: QWidget, properties: Dict[str, Any]):
        """设置控件属性"""
        for prop, value in properties.items():
            if hasattr(widget, prop):
                setattr(widget, prop, value)

    @staticmethod
    def create_standard_parameter_controls() -> Dict[str, QWidget]:
        """创建标准参数控件字典"""
        param_controls = {}
        params = {
            "均线周期": (10, 100, 20),
            "MACD快线": (5, 50, 12),
            "MACD慢线": (10, 100, 26),
            "MACD信号线": (2, 20, 9),
            "RSI周期": (5, 30, 14),
            "布林带周期": (10, 100, 20),
            "布林带标准差": (1.0, 3.0, 2.0),
            "自适应周期": (5, 50, 20),
            "自适应阈值": (0.1, 1.0, 0.5),
            "多因子数量": (3, 20, 5)
        }

        for name, value in params.items():
            if isinstance(value, tuple):
                if any(isinstance(x, float) for x in value):
                    spinbox = QDoubleSpinBox()
                    spinbox.setDecimals(2)
                    spinbox.setRange(float(value[0]), float(value[1]))
                    spinbox.setValue(float(value[2]))
                else:
                    spinbox = QSpinBox()
                    try:
                        v0 = int(value[0]) if str(value[0]).isdigit() else 0
                        v1 = int(value[1]) if str(value[1]).isdigit() else 100
                        v2 = int(value[2]) if str(value[2]).isdigit() else v0
                    except Exception:
                        v0, v1, v2 = 0, 100, 0
                    spinbox.setRange(v0, v1)
                    spinbox.setValue(v2)
                param_controls[name] = spinbox

        return param_controls

    @staticmethod
    def create_backtest_controls() -> QGroupBox:
        """创建回测设置控件组"""
        backtest_group = QGroupBox("回测设置")
        backtest_layout = QFormLayout(backtest_group)

        # 初始资金
        initial_capital = QDoubleSpinBox()
        initial_capital.setDecimals(2)
        initial_capital.setRange(1000.0, 1000000.0)
        initial_capital.setValue(100000.0)
        initial_capital.setSuffix(" 元")
        backtest_layout.addRow("初始资金:", initial_capital)

        # 佣金率
        commission_rate = QDoubleSpinBox()
        commission_rate.setDecimals(4)
        commission_rate.setRange(0.0, 0.01)
        commission_rate.setValue(0.0003)
        commission_rate.setSuffix(" %")
        backtest_layout.addRow("佣金率:", commission_rate)

        # 滑点
        slippage = QDoubleSpinBox()
        slippage.setDecimals(4)
        slippage.setRange(0.0, 0.01)
        slippage.setValue(0.0001)
        slippage.setSuffix(" %")
        backtest_layout.addRow("滑点:", slippage)

        # 仓位管理
        position_combo = QComboBox()
        position_combo.addItems(["固定仓位", "动态仓位", "风险平价", "凯利公式"])
        backtest_layout.addRow("仓位管理:", position_combo)

        # 仓位比例
        position_size = QDoubleSpinBox()
        position_size.setDecimals(2)
        position_size.setRange(0.1, 1.0)
        position_size.setValue(0.5)
        position_size.setSuffix(" %")
        backtest_layout.addRow("仓位比例:", position_size)

        return backtest_group

    @staticmethod
    def create_risk_controls() -> QGroupBox:
        """创建风险管理控件组"""
        risk_group = QGroupBox("风险管理")
        risk_layout = QFormLayout(risk_group)

        # 止损比例
        stop_loss = QDoubleSpinBox()
        stop_loss.setDecimals(3)
        stop_loss.setRange(0.0, 0.1)
        stop_loss.setValue(0.05)
        stop_loss.setSuffix(" %")
        risk_layout.addRow("止损比例:", stop_loss)

        # 止盈比例
        take_profit = QDoubleSpinBox()
        take_profit.setDecimals(3)
        take_profit.setRange(0.0, 0.2)
        take_profit.setValue(0.1)
        take_profit.setSuffix(" %")
        risk_layout.addRow("止盈比例:", take_profit)

        # 最大回撤
        max_drawdown = QDoubleSpinBox()
        max_drawdown.setDecimals(3)
        max_drawdown.setRange(0.0, 0.3)
        max_drawdown.setValue(0.15)
        max_drawdown.setSuffix(" %")
        risk_layout.addRow("最大回撤:", max_drawdown)

        # 无风险利率
        risk_free_rate = QDoubleSpinBox()
        risk_free_rate.setDecimals(3)
        risk_free_rate.setRange(0.0, 0.1)
        risk_free_rate.setValue(0.03)
        risk_free_rate.setSuffix(" %")
        risk_layout.addRow("无风险利率:", risk_free_rate)

        return risk_group
