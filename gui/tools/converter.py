"""
增强版单位转换器工具模块

支持多种单位转换：货币、长度、重量、面积、体积、温度
实时汇率获取，多数据源支持，自动更新机制
"""

import requests
from utils.manager_factory import get_log_manager
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import traceback


class CurrencyRateManager(QObject):
    """货币汇率管理器 - 支持多数据源实时获取"""

    # 信号定义
    rates_updated = pyqtSignal(dict)  # 汇率更新信号
    update_failed = pyqtSignal(str)   # 更新失败信号
    status_changed = pyqtSignal(str)  # 状态变化信号

    def __init__(self):
        super().__init__()
        self.log_manager = get_log_manager()
        self.rates = {}
        self.last_update = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.fetch_rates)
        self.is_active = False

        # 多数据源配置
        self.data_sources = [
            {
                'name': 'fawazahmed0',
                'url': 'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json',
                'fallback_url': 'https://latest.currency-api.pages.dev/v1/currencies/usd.json',
                'parser': self._parse_fawaz_response
            },
            {
                'name': 'exchangerate-api',
                'url': 'https://api.exchangerate-api.com/v4/latest/USD',
                'parser': self._parse_exchangerate_response
            },
            {
                'name': 'forexrateapi',
                'url': 'https://api.forexrateapi.com/v1/latest?base=USD',
                'parser': self._parse_forexrate_response
            }
        ]

        # 默认汇率（备用数据）
        self.default_rates = {
            'USD': 1.0, 'EUR': 0.85, 'GBP': 0.73, 'JPY': 110.0, 'CNY': 6.45,
            'HKD': 7.8, 'KRW': 1180.0, 'AUD': 1.35, 'CAD': 1.25, 'SGD': 1.35,
            'CHF': 0.92, 'SEK': 8.5, 'NOK': 8.8, 'DKK': 6.3, 'PLN': 3.9,
            'CZK': 21.5, 'HUF': 295.0, 'RUB': 74.0, 'INR': 74.5, 'BRL': 5.2,
            'ZAR': 14.8, 'MXN': 20.1, 'THB': 31.5, 'TRY': 8.5, 'NZD': 1.42
        }
        self.rates = self.default_rates.copy()

    def start_updates(self):
        """开始自动更新"""
        if not self.is_active:
            self.is_active = True
            self.log_manager.info("启动汇率自动更新（间隔60秒）")
            self.status_changed.emit("正在获取汇率数据...")
            self.fetch_rates()  # 立即获取一次
            self.update_timer.start(60000)  # 1分钟更新一次

    def stop_updates(self):
        """停止自动更新"""
        if self.is_active:
            self.is_active = False
            self.update_timer.stop()
            self.log_manager.info("已停止汇率自动更新")
            self.status_changed.emit("已停止汇率更新")

    def fetch_rates(self):
        """从多数据源获取汇率"""
        if not self.is_active:
            return

        success = False
        for source in self.data_sources:
            try:
                self.log_manager.debug(f"尝试从数据源 '{source['name']}' 获取汇率: {source['url']}")
                self.status_changed.emit(f"正在从 {source['name']} 获取汇率...")

                # 尝试主URL
                response = requests.get(source['url'], timeout=10)
                if response.status_code == 200:
                    rates = source['parser'](response.json())
                    if rates:
                        self.rates.update(rates)
                        self.last_update = datetime.now()
                        self.rates_updated.emit(self.rates)
                        self.log_manager.info(f"从 '{source['name']}' 获取汇率成功")
                        self.status_changed.emit(f"汇率更新成功 - 来源: {source['name']}")
                        success = True
                        break

                # 如果有备用URL，尝试备用URL
                if 'fallback_url' in source:
                    self.log_manager.debug(f"主URL失败，尝试备用URL: {source['fallback_url']}")
                    response = requests.get(source['fallback_url'], timeout=10)
                    if response.status_code == 200:
                        rates = source['parser'](response.json())
                        if rates:
                            self.rates.update(rates)
                            self.last_update = datetime.now()
                            self.rates_updated.emit(self.rates)
                            self.log_manager.info(f"从 '{source['name']}' (备用URL) 获取汇率成功")
                            self.status_changed.emit(f"汇率更新成功 - 来源: {source['name']} (备用)")
                            success = True
                            break

            except Exception as e:
                self.log_manager.warning(f"从数据源 '{source['name']}' 获取汇率失败: {e}")
                continue  # 尝试下一个数据源

        if not success:
            error_msg = "所有汇率数据源均不可用，使用默认汇率"
            self.log_manager.error(error_msg)
            self.update_failed.emit(error_msg)
            self.status_changed.emit(error_msg)

    def _parse_fawaz_response(self, data: dict) -> dict:
        """解析 fawazahmed0 API 响应"""
        try:
            if 'usd' in data:
                rates = {'USD': 1.0}
                for currency, rate in data['usd'].items():
                    if isinstance(rate, (int, float)):
                        rates[currency.upper()] = float(rate)
                return rates
        except Exception as e:
            self.log_manager.error(f"解析fawaz_response失败: {e}", exc_info=True)
        return {}

    def _parse_exchangerate_response(self, data: dict) -> dict:
        """解析 exchangerate-api 响应"""
        try:
            if 'rates' in data:
                rates = {}
                for currency, rate in data['rates'].items():
                    if isinstance(rate, (int, float)):
                        rates[currency.upper()] = float(rate)
                return rates
        except Exception as e:
            self.log_manager.error(f"解析exchangerate_response失败: {e}", exc_info=True)
        return {}

    def _parse_forexrate_response(self, data: dict) -> dict:
        """解析 forexrateapi 响应"""
        try:
            if 'rates' in data:
                rates = {}
                for currency, rate in data['rates'].items():
                    if isinstance(rate, (int, float)):
                        rates[currency.upper()] = float(rate)
                return rates
        except Exception as e:
            self.log_manager.error(f"解析forexrate_response失败: {e}", exc_info=True)
        return {}

    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """获取汇率"""
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return 1.0

        # 通过USD进行转换
        from_rate = self.rates.get(from_currency, 1.0)
        to_rate = self.rates.get(to_currency, 1.0)

        if from_currency == 'USD':
            return to_rate
        elif to_currency == 'USD':
            return 1.0 / from_rate
        else:
            return to_rate / from_rate


class UnitConverter(QDialog):
    """增强版单位转换器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_manager = get_log_manager()
        self.log_manager.info("单位转换器初始化...")
        self.setWindowTitle("单位转换器")
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        # 初始化货币汇率管理器
        self.currency_manager = CurrencyRateManager()
        self.currency_manager.rates_updated.connect(self.on_rates_updated)
        self.currency_manager.update_failed.connect(self.on_update_failed)
        self.currency_manager.status_changed.connect(self.on_status_changed)

        # 单位转换数据
        self.unit_categories = {
            '货币': {
                'USD': 1.0, 'EUR': 0.85, 'GBP': 0.73, 'JPY': 110.0, 'CNY': 6.45,
                'HKD': 7.8, 'KRW': 1180.0, 'AUD': 1.35, 'CAD': 1.25, 'SGD': 1.35,
                'CHF': 0.92, 'SEK': 8.5, 'NOK': 8.8, 'DKK': 6.3, 'PLN': 3.9,
                'CZK': 21.5, 'HUF': 295.0, 'RUB': 74.0, 'INR': 74.5, 'BRL': 5.2,
                'ZAR': 14.8, 'MXN': 20.1, 'THB': 31.5, 'TRY': 8.5, 'NZD': 1.42
            },
            '长度': {
                '米': 1.0, '厘米': 100.0, '毫米': 1000.0, '千米': 0.001,
                '英寸': 39.3701, '英尺': 3.28084, '码': 1.09361, '英里': 0.000621371,
                '海里': 0.000539957, '光年': 1.057e-16
            },
            '重量': {
                '千克': 1.0, '克': 1000.0, '毫克': 1000000.0, '吨': 0.001,
                '磅': 2.20462, '盎司': 35.274, '英石': 0.157473, '斤': 2.0, '两': 20.0
            },
            '面积': {
                '平方米': 1.0, '平方厘米': 10000.0, '平方毫米': 1000000.0,
                '平方千米': 0.000001, '公顷': 0.0001, '亩': 0.0015,
                '平方英寸': 1550.0, '平方英尺': 10.7639, '平方码': 1.19599, '英亩': 0.000247105
            },
            '体积': {
                '立方米': 1.0, '升': 1000.0, '毫升': 1000000.0, '立方厘米': 1000000.0,
                '立方英寸': 61023.7, '立方英尺': 35.3147, '加仑(美)': 264.172,
                '加仑(英)': 219.969, '品脱': 2113.38, '夸脱': 1056.69
            },
            '温度': {
                '摄氏度': {'base': 'celsius'},
                '华氏度': {'base': 'fahrenheit'},
                '开尔文': {'base': 'kelvin'},
                '兰氏度': {'base': 'rankine'}
            }
        }

        self.init_ui()
        self.log_manager.info("单位转换器UI初始化完成")

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel("多功能单位转换器")
        title_label.setFixedHeight(40)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)

        # 类别选择
        category_group = QGroupBox("转换类别")
        category_layout = QHBoxLayout(category_group)

        self.category_combo = QComboBox()
        self.category_combo.addItems(list(self.unit_categories.keys()))
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        category_layout.addWidget(QLabel("类别:"))
        category_layout.addWidget(self.category_combo)

        layout.addWidget(category_group)

        # 转换区域
        convert_widget = QWidget()
        convert_layout = QHBoxLayout(convert_widget)
        convert_layout.setSpacing(20)

        # 输入区域
        input_group = QGroupBox("输入")
        input_layout = QFormLayout(input_group)

        self.input_value = QLineEdit()
        self.input_value.setPlaceholderText("请输入数值")
        self.input_value.setAlignment(Qt.AlignRight)
        self.input_value.textChanged.connect(self.convert)

        self.input_unit = QComboBox()
        self.input_unit.currentTextChanged.connect(self.convert)

        input_layout.addRow("数值:", self.input_value)
        input_layout.addRow("单位:", self.input_unit)

        # 输出区域
        output_group = QGroupBox("输出")
        output_layout = QFormLayout(output_group)

        self.output_value = QLineEdit()
        self.output_value.setReadOnly(True)
        self.output_value.setAlignment(Qt.AlignRight)

        self.output_unit = QComboBox()
        self.output_unit.currentTextChanged.connect(self.convert)

        output_layout.addRow("数值:", self.output_value)
        output_layout.addRow("单位:", self.output_unit)

        convert_layout.addWidget(input_group)
        convert_layout.addWidget(output_group)
        layout.addWidget(convert_widget)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.convert_button = QPushButton("转换")
        self.convert_button.clicked.connect(self.convert)

        self.swap_button = QPushButton("交换单位")
        self.swap_button.clicked.connect(self.swap_units)

        self.clear_button = QPushButton("清除")
        self.clear_button.clicked.connect(self.clear_all)

        button_layout.addWidget(self.convert_button)
        button_layout.addWidget(self.swap_button)
        button_layout.addWidget(self.clear_button)
        layout.addLayout(button_layout)

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666;
                padding: 5px;
                background-color: #f0f0f0;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.status_label)

        # 初始化类别
        self.on_category_changed()

    def on_category_changed(self):
        """类别变化处理"""
        category = self.category_combo.currentText()
        self.log_manager.debug(f"转换类别变更为: '{category}'")
        units = list(self.unit_categories[category].keys())

        # 更新单位选择
        self.input_unit.clear()
        self.output_unit.clear()
        self.input_unit.addItems(units)
        self.output_unit.addItems(units)

        # 设置默认选择
        if len(units) > 1:
            self.output_unit.setCurrentIndex(1)

        # 如果是货币类别，启动汇率更新
        if category == '货币':
            self.currency_manager.start_updates()
        else:
            self.currency_manager.stop_updates()

        self.convert()

    def convert(self):
        """执行转换"""
        try:
            input_text = self.input_value.text().strip()
            if not input_text:
                self.output_value.setText("")
                return

            input_val = float(input_text)
            category = self.category_combo.currentText()
            input_unit = self.input_unit.currentText()
            output_unit = self.output_unit.currentText()

            self.log_manager.debug(f"执行转换: {input_val} {input_unit} -> {output_unit} (类别: {category})")

            if category == '货币':
                result = self.convert_currency(input_val, input_unit, output_unit)
            elif category == '温度':
                result = self.convert_temperature(input_val, input_unit, output_unit)
            else:
                result = self.convert_standard_unit(input_val, input_unit, output_unit, category)

            # 格式化输出
            if result is not None:
                if abs(result) >= 1000000:
                    self.output_value.setText(f"{result:.2e}")
                elif abs(result) >= 1000:
                    self.output_value.setText(f"{result:,.2f}")
                else:
                    self.output_value.setText(f"{result:.6f}".rstrip('0').rstrip('.'))
            else:
                self.output_value.setText("转换失败")

        except ValueError:
            self.log_manager.warning(f"转换失败：无效的输入值 '{self.input_value.text()}'")
            self.output_value.setText("输入格式错误")
        except Exception as e:
            self.log_manager.error(f"执行转换时发生未知错误: {e}", exc_info=True)
            self.output_value.setText("转换失败")
            print(f"转换器错误: {str(e)}")

    def convert_currency(self, value: float, from_currency: str, to_currency: str) -> float:
        """货币转换"""
        rate = self.currency_manager.get_rate(from_currency, to_currency)
        return value * rate

    def convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """温度转换"""
        if from_unit == to_unit:
            return value

        # 先转换为摄氏度
        if from_unit == '华氏度':
            celsius = (value - 32) * 5/9
        elif from_unit == '开尔文':
            celsius = value - 273.15
        elif from_unit == '兰氏度':
            celsius = (value - 491.67) * 5/9
        else:  # 摄氏度
            celsius = value

        # 从摄氏度转换为目标单位
        if to_unit == '华氏度':
            return celsius * 9/5 + 32
        elif to_unit == '开尔文':
            return celsius + 273.15
        elif to_unit == '兰氏度':
            return (celsius + 273.15) * 9/5
        else:  # 摄氏度
            return celsius

    def convert_standard_unit(self, value: float, from_unit: str, to_unit: str, category: str) -> float:
        """标准单位转换"""
        if from_unit == to_unit:
            return value

        units = self.unit_categories[category]
        from_factor = units[from_unit]
        to_factor = units[to_unit]

        # 转换为基本单位，再转换为目标单位
        base_value = value / from_factor
        return base_value * to_factor

    def swap_units(self):
        """交换输入和输出单位"""
        input_index = self.input_unit.currentIndex()
        output_index = self.output_unit.currentIndex()

        self.log_manager.debug(f"交换单位: 从 {self.input_unit.itemText(input_index)} <-> {self.output_unit.itemText(output_index)}")

        self.input_unit.setCurrentIndex(output_index)
        self.output_unit.setCurrentIndex(input_index)

        # 交换数值
        input_value = self.input_value.text()
        output_value = self.output_value.text()

        if output_value and output_value not in ["输入格式错误", "转换失败", ""]:
            self.input_value.setText(output_value)

        self.convert()

    def clear_all(self):
        """清除所有输入"""
        self.log_manager.debug("清除所有输入和输出")
        self.input_value.clear()
        self.output_value.clear()

    def on_rates_updated(self, rates):
        """汇率更新回调"""
        try:
            # 更新汇率数据
            self.currency_rates = rates

            # 如果当前是货币转换，重新计算
            if self.category_combo.currentText() == '货币':
                self.convert()

            # 格式化显示主要汇率信息
            major_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CNY', 'HKD']
            rate_info = []

            for currency in major_currencies:
                if currency in rates and currency != 'USD':  # USD是基准货币
                    rate = rates[currency]
                    if currency == 'JPY':
                        rate_info.append(f"USD/{currency}: {rate:.2f}")
                    elif currency == 'CNY':
                        rate_info.append(f"USD/{currency}: {rate:.4f}")
                    else:
                        rate_info.append(f"USD/{currency}: {rate:.4f}")

            # 显示格式化的汇率信息
            if rate_info:
                rate_display = " | ".join(rate_info[:4])  # 显示前4个主要汇率
                status_text = f"汇率更新成功 ({len(rates)}种货币) - {rate_display}"
                self.log_manager.debug(f"状态栏汇率信息已更新: {status_text}")
            else:
                status_text = f"汇率更新成功 - 获取到 {len(rates)} 种货币汇率"
                self.log_manager.debug("状态栏已更新，但无主要货币汇率信息可显示")

            self.status_label.setText(status_text)
            self.status_label.setStyleSheet("color: green; font-size: 11px; padding: 5px;")
        except Exception as e:
            self.log_manager.error(f"更新汇率显示时出错: {e}", exc_info=True)
            self.status_label.setText(f"汇率显示错误: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-size: 11px; padding: 5px;")

    def on_update_failed(self, error_msg):
        """汇率更新失败回调"""
        self.status_label.setText(f"汇率更新失败: {error_msg}")
        self.status_label.setStyleSheet("color: red; font-size: 11px; padding: 5px;")

    def on_status_changed(self, status):
        """状态变化回调"""
        self.log_manager.debug(f"状态栏状态变更: {status}")
        if "正在获取" in status or "正在从" in status:
            self.status_label.setText(status)
            self.status_label.setStyleSheet("color: blue; font-size: 11px; padding: 5px;")

    def showEvent(self, event):
        """窗口显示事件 - 启动汇率更新"""
        super().showEvent(event)
        self.log_manager.info("单位转换器窗口已显示")
        if self.category_combo.currentText() == '货币':
            self.currency_manager.start_updates()

    def closeEvent(self, event):
        """窗口关闭事件 - 停止汇率更新"""
        self.log_manager.info("单位转换器窗口已关闭，正在停止汇率更新")
        self.currency_manager.stop_updates()
        super().closeEvent(event)

    @staticmethod
    def show_converter(parent=None):
        """显示单位转换器对话框"""
        converter = UnitConverter(parent)
        converter.exec_()
        return converter
