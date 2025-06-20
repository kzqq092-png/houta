"""
指标参数对话框模块

处理技术指标的参数设置功能
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QScrollArea, QWidget,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict, Any, List, Optional
import inspect
import traceback


class IndicatorParamsDialog(QDialog):
    """指标参数设置对话框"""

    params_updated = pyqtSignal(dict)  # 参数更新信号

    def __init__(self, parent=None, indicators=None, log_manager=None):
        super().__init__(parent)
        self.indicators = indicators or []
        self.log_manager = log_manager
        self.param_controls = {}

        self.setWindowTitle("指标参数设置")
        self.setModal(True)
        self.resize(600, 500)

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # 为每个指标创建参数组
        for indicator_info in self.indicators:
            if isinstance(indicator_info, dict):
                indicator_name = indicator_info.get('name', '')
                indicator_type = indicator_info.get('type', 'custom')
            else:
                # 假设是字符串或有text()方法的对象
                indicator_name = str(indicator_info)
                indicator_type = 'custom'

            group = self.create_indicator_group(indicator_name, indicator_type)
            if group:
                scroll_layout.addWidget(group)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # 添加按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept_params)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def create_indicator_group(self, indicator_name: str, indicator_type: str) -> Optional[QGroupBox]:
        """为指标创建参数组"""
        try:
            group = QGroupBox(indicator_name)
            group_layout = QFormLayout(group)

            if indicator_type == "ta-lib":
                self.create_talib_params(indicator_name, group_layout)
            else:
                self.create_custom_params(indicator_name, group_layout)

            return group

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建指标参数组失败: {str(e)}")
            return None

    def create_talib_params(self, indicator_name: str, layout: QFormLayout):
        """创建TA-Lib指标参数"""
        try:
            import talib
            if hasattr(talib, indicator_name):
                func = getattr(talib, indicator_name)
                sig = inspect.signature(func)

                for param_name, param in sig.parameters.items():
                    # 跳过价格数据参数
                    if param_name in ["open", "high", "low", "close", "volume"]:
                        continue

                    if param.default is not inspect.Parameter.empty:
                        if isinstance(param.default, int):
                            control = QSpinBox()
                            control.setRange(1, 1000)
                            control.setValue(param.default)
                        elif isinstance(param.default, float):
                            control = QDoubleSpinBox()
                            control.setRange(0.0, 100.0)
                            control.setValue(param.default)
                            control.setDecimals(2)
                        else:
                            continue

                        layout.addRow(f"{param_name}:", control)
                        self.param_controls[f"{indicator_name}_{param_name}"] = control

        except ImportError:
            if self.log_manager:
                self.log_manager.warning("TA-Lib未安装，跳过TA-Lib指标参数")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建TA-Lib参数失败: {str(e)}")

    def create_custom_params(self, indicator_name: str, layout: QFormLayout):
        """创建自定义指标参数"""
        try:
            # 根据指标名称创建相应的参数控件
            if "MA" in indicator_name.upper():
                self.create_ma_params(indicator_name, layout)
            elif "MACD" in indicator_name.upper():
                self.create_macd_params(indicator_name, layout)
            elif "RSI" in indicator_name.upper():
                self.create_rsi_params(indicator_name, layout)
            elif "BOLL" in indicator_name.upper():
                self.create_boll_params(indicator_name, layout)
            elif "KDJ" in indicator_name.upper():
                self.create_kdj_params(indicator_name, layout)
            else:
                # 默认参数
                self.create_default_params(indicator_name, layout)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建自定义参数失败: {str(e)}")

    def create_ma_params(self, indicator_name: str, layout: QFormLayout):
        """创建移动平均线参数"""
        period_control = QSpinBox()
        period_control.setRange(5, 250)
        period_control.setValue(20)
        layout.addRow("周期:", period_control)
        self.param_controls[f"{indicator_name}_period"] = period_control

    def create_macd_params(self, indicator_name: str, layout: QFormLayout):
        """创建MACD参数"""
        fast_control = QSpinBox()
        fast_control.setRange(5, 50)
        fast_control.setValue(12)
        layout.addRow("快线周期:", fast_control)
        self.param_controls[f"{indicator_name}_fast"] = fast_control

        slow_control = QSpinBox()
        slow_control.setRange(10, 100)
        slow_control.setValue(26)
        layout.addRow("慢线周期:", slow_control)
        self.param_controls[f"{indicator_name}_slow"] = slow_control

        signal_control = QSpinBox()
        signal_control.setRange(2, 20)
        signal_control.setValue(9)
        layout.addRow("信号线周期:", signal_control)
        self.param_controls[f"{indicator_name}_signal"] = signal_control

    def create_rsi_params(self, indicator_name: str, layout: QFormLayout):
        """创建RSI参数"""
        period_control = QSpinBox()
        period_control.setRange(5, 30)
        period_control.setValue(14)
        layout.addRow("周期:", period_control)
        self.param_controls[f"{indicator_name}_period"] = period_control

    def create_boll_params(self, indicator_name: str, layout: QFormLayout):
        """创建布林带参数"""
        period_control = QSpinBox()
        period_control.setRange(10, 100)
        period_control.setValue(20)
        layout.addRow("周期:", period_control)
        self.param_controls[f"{indicator_name}_period"] = period_control

        std_control = QDoubleSpinBox()
        std_control.setRange(1.0, 3.0)
        std_control.setValue(2.0)
        std_control.setDecimals(1)
        layout.addRow("标准差倍数:", std_control)
        self.param_controls[f"{indicator_name}_std"] = std_control

    def create_kdj_params(self, indicator_name: str, layout: QFormLayout):
        """创建KDJ参数"""
        k_period = QSpinBox()
        k_period.setRange(5, 30)
        k_period.setValue(9)
        layout.addRow("K值周期:", k_period)
        self.param_controls[f"{indicator_name}_k_period"] = k_period

        d_period = QSpinBox()
        d_period.setRange(2, 10)
        d_period.setValue(3)
        layout.addRow("D值周期:", d_period)
        self.param_controls[f"{indicator_name}_d_period"] = d_period

        j_period = QSpinBox()
        j_period.setRange(2, 10)
        j_period.setValue(3)
        layout.addRow("J值周期:", j_period)
        self.param_controls[f"{indicator_name}_j_period"] = j_period

    def create_default_params(self, indicator_name: str, layout: QFormLayout):
        """创建默认参数"""
        period_control = QSpinBox()
        period_control.setRange(5, 100)
        period_control.setValue(20)
        layout.addRow("周期:", period_control)
        self.param_controls[f"{indicator_name}_period"] = period_control

    def get_params(self) -> Dict[str, Any]:
        """获取所有参数"""
        params = {}
        for key, control in self.param_controls.items():
            if isinstance(control, QSpinBox):
                params[key] = control.value()
            elif isinstance(control, QDoubleSpinBox):
                params[key] = control.value()
        return params

    def accept_params(self):
        """接受参数设置"""
        try:
            params = self.get_params()
            self.params_updated.emit(params)
            self.accept()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"接受参数设置失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"参数设置失败: {str(e)}")

    def set_indicators(self, indicators: List[Any]):
        """设置指标列表"""
        self.indicators = indicators
        # 重新初始化界面
        self.init_ui()
