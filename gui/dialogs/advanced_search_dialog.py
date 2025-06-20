"""
高级搜索对话框模块

处理股票的高级搜索功能
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict, Any, List, Optional
import traceback


class AdvancedSearchDialog(QDialog):
    """高级搜索对话框"""

    search_completed = pyqtSignal(list)  # 搜索完成信号

    def __init__(self, parent=None, data_manager=None, log_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.log_manager = log_manager

        self.setWindowTitle("高级搜索")
        self.setModal(True)
        self.resize(500, 600)

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 创建搜索条件组
        conditions_group = QGroupBox("搜索条件")
        conditions_layout = QFormLayout(conditions_group)

        # 添加搜索条件控件
        self.controls = {}

        # 股票代码
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("输入股票代码")
        conditions_layout.addRow("股票代码:", self.code_edit)
        self.controls["code"] = self.code_edit

        # 股票名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入股票名称")
        conditions_layout.addRow("股票名称:", self.name_edit)
        self.controls["name"] = self.name_edit

        # 市场
        self.market_combo = QComboBox()
        self.market_combo.addItems([
            "全部", "沪市主板", "深市主板", "创业板", "科创板",
            "北交所", "港股通", "美股", "期货", "期权"
        ])
        conditions_layout.addRow("市场:", self.market_combo)
        self.controls["market"] = self.market_combo

        # 行业
        self.industry_combo = QComboBox()
        self.industry_combo.addItems([
            "全部", "金融", "科技", "医药", "消费", "制造",
            "能源", "材料", "通信", "公用事业", "房地产"
        ])
        conditions_layout.addRow("行业:", self.industry_combo)
        self.controls["industry"] = self.industry_combo

        # 价格范围
        price_layout = QHBoxLayout()
        self.min_price = QDoubleSpinBox()
        self.min_price.setRange(0, 10000)
        self.min_price.setSuffix(" 元")
        self.max_price = QDoubleSpinBox()
        self.max_price.setRange(0, 10000)
        self.max_price.setSuffix(" 元")
        price_layout.addWidget(self.min_price)
        price_layout.addWidget(QLabel("至"))
        price_layout.addWidget(self.max_price)
        conditions_layout.addRow("价格范围:", price_layout)
        self.controls["min_price"] = self.min_price
        self.controls["max_price"] = self.max_price

        # 市值范围
        market_cap_layout = QHBoxLayout()
        self.min_cap = QDoubleSpinBox()
        self.min_cap.setRange(0, 1000000)
        self.min_cap.setSuffix(" 亿")
        self.max_cap = QDoubleSpinBox()
        self.max_cap.setRange(0, 1000000)
        self.max_cap.setSuffix(" 亿")
        market_cap_layout.addWidget(self.min_cap)
        market_cap_layout.addWidget(QLabel("至"))
        market_cap_layout.addWidget(self.max_cap)
        conditions_layout.addRow("市值范围:", market_cap_layout)
        self.controls["min_cap"] = self.min_cap
        self.controls["max_cap"] = self.max_cap

        # 成交量范围
        volume_layout = QHBoxLayout()
        self.min_volume = QDoubleSpinBox()
        self.min_volume.setRange(0, 1000000)
        self.min_volume.setSuffix(" 万手")
        self.max_volume = QDoubleSpinBox()
        self.max_volume.setRange(0, 1000000)
        self.max_volume.setSuffix(" 万手")
        volume_layout.addWidget(self.min_volume)
        volume_layout.addWidget(QLabel("至"))
        volume_layout.addWidget(self.max_volume)
        conditions_layout.addRow("成交量范围:", volume_layout)
        self.controls["min_volume"] = self.min_volume
        self.controls["max_volume"] = self.max_volume

        # 换手率范围
        turnover_layout = QHBoxLayout()
        self.min_turnover = QDoubleSpinBox()
        self.min_turnover.setRange(0, 100)
        self.min_turnover.setSuffix(" %")
        self.max_turnover = QDoubleSpinBox()
        self.max_turnover.setRange(0, 100)
        self.max_turnover.setSuffix(" %")
        turnover_layout.addWidget(self.min_turnover)
        turnover_layout.addWidget(QLabel("至"))
        turnover_layout.addWidget(self.max_turnover)
        conditions_layout.addRow("换手率范围:", turnover_layout)
        self.controls["min_turnover"] = self.min_turnover
        self.controls["max_turnover"] = self.max_turnover

        layout.addWidget(conditions_group)

        # 添加按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.perform_search)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_search_conditions(self) -> Dict[str, Any]:
        """获取搜索条件"""
        return {
            "code": self.code_edit.text(),
            "name": self.name_edit.text(),
            "market": self.market_combo.currentText(),
            "industry": self.industry_combo.currentText(),
            "min_price": self.min_price.value(),
            "max_price": self.max_price.value(),
            "min_cap": self.min_cap.value(),
            "max_cap": self.max_cap.value(),
            "min_volume": self.min_volume.value(),
            "max_volume": self.max_volume.value(),
            "min_turnover": self.min_turnover.value(),
            "max_turnover": self.max_turnover.value()
        }

    def perform_search(self):
        """执行搜索"""
        try:
            if not self.data_manager:
                QMessageBox.warning(self, "警告", "数据管理器未初始化")
                return

            conditions = self.get_search_conditions()

            # 获取所有股票
            all_stocks = self.data_manager.get_stock_list()
            filtered_stocks = []

            for stock_info in all_stocks:
                try:
                    # 检查搜索条件
                    if self._check_stock_conditions(stock_info, conditions):
                        filtered_stocks.append(stock_info)

                except Exception as e:
                    if self.log_manager:
                        self.log_manager.warning(f"处理股票 {stock_info.get('code', '未知')} 失败: {str(e)}")
                    continue

            # 发送搜索结果
            self.search_completed.emit(filtered_stocks)

            if self.log_manager:
                self.log_manager.info(f"找到 {len(filtered_stocks)} 只符合条件的股票")

            self.accept()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"执行高级搜索失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"搜索失败: {str(e)}")

    def _check_stock_conditions(self, stock_info: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """检查股票是否符合搜索条件"""
        try:
            # 检查股票代码
            if conditions["code"] and conditions["code"] not in stock_info.get("code", ""):
                return False

            # 检查股票名称
            if conditions["name"] and conditions["name"] not in stock_info.get("name", ""):
                return False

            # 检查市场
            if conditions["market"] != "全部":
                if not self._check_market_condition(stock_info, conditions["market"]):
                    return False

            # 检查行业
            if conditions["industry"] != "全部" and stock_info.get("industry") != conditions["industry"]:
                return False

            # 检查价格范围（需要获取实时数据）
            # 这里简化处理，实际应该获取最新价格

            # 检查市值范围
            market_cap = stock_info.get("market_cap", 0)
            if market_cap < conditions["min_cap"] or market_cap > conditions["max_cap"]:
                return False

            return True

        except Exception as e:
            if self.log_manager:
                self.log_manager.warning(f"检查股票条件失败: {str(e)}")
            return False

    def _check_market_condition(self, stock_info: Dict[str, Any], market: str) -> bool:
        """检查市场条件"""
        code = stock_info.get("code", "")

        market_patterns = {
            "沪市主板": lambda c: c.startswith('60'),
            "深市主板": lambda c: c.startswith('00'),
            "创业板": lambda c: c.startswith('30'),
            "科创板": lambda c: c.startswith('68'),
            "北交所": lambda c: c.startswith('8'),
            "港股通": lambda c: c.startswith('9'),
            "美股": lambda c: c.startswith('7'),
            "期货": lambda c: c.startswith('IC'),
            "期权": lambda c: c.startswith('10')
        }

        pattern_func = market_patterns.get(market)
        return pattern_func(code) if pattern_func else False
