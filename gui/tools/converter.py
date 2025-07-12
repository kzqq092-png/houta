"""
单位转换器工具

提供各种单位之间的转换功能。
"""

import logging
from typing import Optional, Dict, Callable, Union
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
    QDoubleSpinBox, QLineEdit, QLabel, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class Converter(QDialog):
    """单位转换器对话框"""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化转换器

        Args:
            parent: 父窗口组件
        """
        super().__init__(parent)
        self.setWindowTitle("单位转换器")
        self.setFixedSize(400, 200)

        # 转换系数配置
        self._conversion_factors = self._setup_conversion_factors()

        # 设置样式
        self._setup_styles()

        # 创建UI
        self._create_widgets()

        # 连接信号
        self._connect_signals()

        # 初始化
        self._update_units()

    def _setup_styles(self) -> None:
        """设置样式表"""
        self.setStyleSheet("""
            QDialog {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                background-color: #f0f0f0;
            }
            QComboBox, QDoubleSpinBox, QLineEdit {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 14px;
                padding: 8px;
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 5px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 20px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QLabel {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 14px;
                color: #333333;
                font-weight: bold;
            }
            QLineEdit:read-only {
                background-color: #f8f9fa;
                color: #495057;
            }
        """)

    def _create_widgets(self) -> None:
        """创建UI组件"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 转换类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("转换类型:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["长度", "重量", "面积", "体积", "温度"])
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        main_layout.addLayout(type_layout)

        # 输入区域
        input_layout = QHBoxLayout()
        input_label = QLabel("输入:")
        self.input_value = QDoubleSpinBox()
        self.input_value.setRange(-1000000, 1000000)
        self.input_value.setDecimals(6)
        self.input_value.setValue(1.0)
        self.input_unit = QComboBox()
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_value)
        input_layout.addWidget(self.input_unit)
        main_layout.addLayout(input_layout)

        # 输出区域
        output_layout = QHBoxLayout()
        output_label = QLabel("输出:")
        self.output_value = QLineEdit()
        self.output_value.setReadOnly(True)
        self.output_unit = QComboBox()
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_value)
        output_layout.addWidget(self.output_unit)
        main_layout.addLayout(output_layout)

    def _connect_signals(self) -> None:
        """连接信号"""
        self.type_combo.currentTextChanged.connect(self._update_units)
        self.input_value.valueChanged.connect(self._convert)
        self.input_unit.currentTextChanged.connect(self._convert)
        self.output_unit.currentTextChanged.connect(self._convert)

    def _setup_conversion_factors(self) -> Dict[str, Dict[str, Union[float, Callable]]]:
        """设置转换系数"""
        return {
            "长度": {
                "米": 1.0,
                "千米": 1000.0,
                "厘米": 0.01,
                "毫米": 0.001,
                "英寸": 0.0254,
                "英尺": 0.3048,
                "码": 0.9144,
                "英里": 1609.344
            },
            "重量": {
                "克": 1.0,
                "千克": 1000.0,
                "吨": 1000000.0,
                "磅": 453.59237,
                "盎司": 28.349523125
            },
            "面积": {
                "平方米": 1.0,
                "平方千米": 1000000.0,
                "公顷": 10000.0,
                "亩": 666.666667,
                "平方英尺": 0.09290304,
                "平方英里": 2589988.11
            },
            "体积": {
                "立方米": 1.0,
                "升": 0.001,
                "毫升": 0.000001,
                "加仑": 0.00378541,
                "品脱": 0.000473176,
                "夸脱": 0.000946353
            },
            "温度": {
                "摄氏度": lambda x: x,
                "华氏度": lambda x: (x * 9/5) + 32,
                "开尔文": lambda x: x + 273.15
            }
        }

    def _update_units(self) -> None:
        """更新单位列表"""
        try:
            current_type = self.type_combo.currentText()
            if current_type in self._conversion_factors:
                units = list(self._conversion_factors[current_type].keys())

                # 更新输入单位下拉框
                self.input_unit.clear()
                self.input_unit.addItems(units)

                # 更新输出单位下拉框
                self.output_unit.clear()
                self.output_unit.addItems(units)

                # 设置默认值
                if len(units) > 1:
                    self.output_unit.setCurrentIndex(1)

                # 执行转换
                self._convert()

        except Exception as e:
            logger.error(f"更新单位列表失败: {e}")

    def _convert(self) -> None:
        """执行单位转换"""
        try:
            value = self.input_value.value()
            current_type = self.type_combo.currentText()
            from_unit = self.input_unit.currentText()
            to_unit = self.output_unit.currentText()

            if not all([current_type, from_unit, to_unit]):
                return

            factors = self._conversion_factors.get(current_type, {})

            if current_type == "温度":
                # 温度转换需要特殊处理
                result = self._convert_temperature(value, from_unit, to_unit)
            else:
                # 其他单位的标准转换
                from_factor = factors.get(from_unit, 1.0)
                to_factor = factors.get(to_unit, 1.0)

                if isinstance(from_factor, (int, float)) and isinstance(to_factor, (int, float)):
                    result = value * from_factor / to_factor
                else:
                    result = 0.0

            # 格式化结果
            if abs(result) >= 1000000 or (abs(result) < 0.001 and result != 0):
                # 使用科学记数法
                self.output_value.setText(f"{result:.6e}")
            else:
                # 使用普通格式，最多6位小数
                self.output_value.setText(
                    f"{result:.6f}".rstrip('0').rstrip('.'))

        except Exception as e:
            logger.error(f"单位转换失败: {e}")
            self.output_value.setText("转换错误")

    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """温度转换"""
        # 先转换为摄氏度
        if from_unit == "华氏度":
            celsius = (value - 32) * 5/9
        elif from_unit == "开尔文":
            celsius = value - 273.15
        else:  # 摄氏度
            celsius = value

        # 从摄氏度转换为目标单位
        if to_unit == "华氏度":
            return celsius * 9/5 + 32
        elif to_unit == "开尔文":
            return celsius + 273.15
        else:  # 摄氏度
            return celsius

    @staticmethod
    def show_converter(parent: Optional[QWidget] = None) -> None:
        """显示转换器对话框"""
        converter = Converter(parent)
        converter.exec_()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    Converter.show_converter()
    sys.exit(app.exec_())
