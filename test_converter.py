#!/usr/bin/env python3
"""
单位转换器测试脚本

测试增强版单位转换器的功能：
- 多种单位转换（货币、长度、重量、面积、体积、温度）
- 实时汇率获取
- 多数据源支持
- 自动更新机制
"""

from gui.tools.converter import UnitConverter, CurrencyRateManager
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class ConverterTestWindow(QMainWindow):
    """转换器测试窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("单位转换器测试")
        self.setGeometry(100, 100, 400, 300)

        # 创建中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # 标题
        title = QLabel("单位转换器功能测试")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px;")
        layout.addWidget(title)

        # 测试按钮
        test_converter_btn = QPushButton("测试完整转换器")
        test_converter_btn.clicked.connect(self.test_converter)
        layout.addWidget(test_converter_btn)

        test_currency_btn = QPushButton("测试汇率管理器")
        test_currency_btn.clicked.connect(self.test_currency_manager)
        layout.addWidget(test_currency_btn)

        # 状态标签
        self.status_label = QLabel("点击按钮开始测试...")
        self.status_label.setStyleSheet("margin: 20px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(self.status_label)

        # 汇率管理器测试
        self.currency_manager = None

    def test_converter(self):
        """测试完整转换器"""
        try:
            self.status_label.setText("正在启动单位转换器...")
            converter = UnitConverter(self)
            converter.show()
            self.status_label.setText("转换器已启动，请在转换器窗口中测试各种功能")
        except Exception as e:
            self.status_label.setText(f"转换器测试失败: {str(e)}")
            print(f"转换器测试错误: {str(e)}")

    def test_currency_manager(self):
        """测试汇率管理器"""
        try:
            self.status_label.setText("正在测试汇率管理器...")

            if self.currency_manager is None:
                self.currency_manager = CurrencyRateManager()
                self.currency_manager.rates_updated.connect(self.on_rates_updated)
                self.currency_manager.update_failed.connect(self.on_update_failed)
                self.currency_manager.status_changed.connect(self.on_status_changed)

            # 启动汇率更新
            self.currency_manager.start_updates()

        except Exception as e:
            self.status_label.setText(f"汇率管理器测试失败: {str(e)}")
            print(f"汇率管理器测试错误: {str(e)}")

    def on_rates_updated(self, rates):
        """汇率更新回调"""
        rate_count = len(rates)
        sample_rates = list(rates.items())[:5]  # 显示前5个汇率
        sample_text = ", ".join([f"{k}:{v:.4f}" for k, v in sample_rates])
        self.status_label.setText(f"汇率更新成功！获取到 {rate_count} 种货币汇率\n示例: {sample_text}")

    def on_update_failed(self, error_msg):
        """汇率更新失败回调"""
        self.status_label.setText(f"汇率更新失败: {error_msg}")

    def on_status_changed(self, status):
        """状态变化回调"""
        current_text = self.status_label.text()
        self.status_label.setText(f"{current_text}\n状态: {status}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.currency_manager:
            self.currency_manager.stop_updates()
        event.accept()


def test_unit_conversions():
    """测试各种单位转换功能"""
    print("=== 单位转换功能测试 ===")

    # 创建转换器实例
    converter = UnitConverter()

    # 测试长度转换
    print("\n1. 长度转换测试:")
    result = converter.convert_standard_unit(1.0, '米', '厘米', '长度')
    print(f"1 米 = {result} 厘米")

    result = converter.convert_standard_unit(1.0, '英里', '千米', '长度')
    print(f"1 英里 = {result:.4f} 千米")

    # 测试重量转换
    print("\n2. 重量转换测试:")
    result = converter.convert_standard_unit(1.0, '千克', '磅', '重量')
    print(f"1 千克 = {result:.4f} 磅")

    result = converter.convert_standard_unit(1.0, '斤', '克', '重量')
    print(f"1 斤 = {result} 克")

    # 测试温度转换
    print("\n3. 温度转换测试:")
    result = converter.convert_temperature(0, '摄氏度', '华氏度')
    print(f"0 摄氏度 = {result} 华氏度")

    result = converter.convert_temperature(100, '摄氏度', '开尔文')
    print(f"100 摄氏度 = {result} 开尔文")

    # 测试面积转换
    print("\n4. 面积转换测试:")
    result = converter.convert_standard_unit(1.0, '平方米', '平方厘米', '面积')
    print(f"1 平方米 = {result} 平方厘米")

    result = converter.convert_standard_unit(1.0, '亩', '平方米', '面积')
    print(f"1 亩 = {result:.2f} 平方米")

    # 测试体积转换
    print("\n5. 体积转换测试:")
    result = converter.convert_standard_unit(1.0, '立方米', '升', '体积')
    print(f"1 立方米 = {result} 升")

    result = converter.convert_standard_unit(1.0, '加仑(美)', '升', '体积')
    print(f"1 美制加仑 = {result:.4f} 升")


def test_currency_manager():
    """测试汇率管理器"""
    print("\n=== 汇率管理器测试 ===")

    from PyQt5.QtCore import QEventLoop

    # 创建汇率管理器
    manager = CurrencyRateManager()

    # 测试默认汇率
    print(f"USD 到 CNY 汇率: {manager.get_rate('USD', 'CNY'):.4f}")
    print(f"EUR 到 USD 汇率: {manager.get_rate('EUR', 'USD'):.4f}")
    print(f"GBP 到 JPY 汇率: {manager.get_rate('GBP', 'JPY'):.4f}")

    # 测试实时汇率获取（需要网络连接）
    print("\n正在测试实时汇率获取...")

    def on_rates_updated(rates):
        print(f"✓ 汇率更新成功，获取到 {len(rates)} 种货币")
        sample_rates = list(rates.items())[:10]
        for currency, rate in sample_rates:
            print(f"  {currency}: {rate:.4f}")
        loop.quit()

    def on_update_failed(error):
        print(f"✗ 汇率更新失败: {error}")
        loop.quit()

    def on_status_changed(status):
        print(f"状态: {status}")

    # 连接信号
    manager.rates_updated.connect(on_rates_updated)
    manager.update_failed.connect(on_update_failed)
    manager.status_changed.connect(on_status_changed)

    # 启动更新并等待结果
    loop = QEventLoop()
    manager.start_updates()

    # 设置超时
    QTimer.singleShot(15000, loop.quit)  # 15秒超时
    loop.exec_()

    manager.stop_updates()


def main():
    """主函数"""
    app = QApplication(sys.argv)

    print("HIkyuu 单位转换器测试程序")
    print("=" * 50)

    # 命令行测试
    if len(sys.argv) > 1 and sys.argv[1] == '--console':
        test_unit_conversions()
        test_currency_manager()
        return

    # GUI测试
    window = ConverterTestWindow()
    window.show()

    print("GUI测试窗口已启动")
    print("可以通过以下方式测试:")
    print("1. 点击 '测试完整转换器' 按钮测试所有转换功能")
    print("2. 点击 '测试汇率管理器' 按钮测试实时汇率获取")
    print("3. 使用命令行参数 '--console' 进行控制台测试")

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
