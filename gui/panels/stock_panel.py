"""
股票管理面板模块

提供完整的股票管理功能，包括：
- 股票列表管理和搜索
- 收藏夹功能
- 右键菜单操作
- 高级搜索功能
- 数据导出功能
- 指标管理
- 数据缓存机制
- 数据源切换支持
"""

import pandas as pd
import traceback
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from core.data_manager import data_manager
# from gui.widgets.stock_list_widget import StockListWidget
from gui.components.custom_widgets import add_shadow, safe_strftime
from core.adapters import get_logger
from gui.dialogs.advanced_search_dialog import AdvancedSearchDialog
from core.services.indicator_ui_adapter import IndicatorUIAdapter
from core.indicator_manager import get_indicator_manager  # 兼容层

# 使用新的指标服务架构
_use_new_architecture = True


class StockManagementPanel(QWidget):
    """股票管理面板 - 整合了数据处理和UI功能"""

    # 定义信号
    stock_selected = pyqtSignal(str)  # 股票选择信号
    stock_favorites_changed = pyqtSignal()  # 收藏夹变更信号
    indicator_changed = pyqtSignal(str, dict)  # 指标变更信号
    export_completed = pyqtSignal(str)  # 导出完成信号
    data_loaded = pyqtSignal(dict)  # 数据加载信号
    data_error = pyqtSignal(str)  # 数据错误信号

    def __init__(self, parent=None, log_manager=None):
        super().__init__(parent)
        self.log_manager = log_manager or get_logger(__name__)
        self.data_manager = data_manager
        self.parent_gui = parent

        # 初始化数据缓存
        self.data_cache = {}
        self.cache_manager = getattr(parent, 'cache_manager', None)
        self.max_cache_size = 100

        # 初始化指标服务架构
        self.indicator_adapter = IndicatorUIAdapter()
        self.log_manager.info("股票面板使用新的指标服务架构")

        # 初始化数据
        self.market_block_mapping = {}
        self.industry_mapping = {}
        self.current_stock = None
        self.favorites = []

        # 初始化UI
        self.init_ui()
        self.init_data()
        self.setup_connections()

    def init_ui(self):
        """初始化UI界面"""
        try:
            # 创建主布局
            self.main_layout = QVBoxLayout(self)
            # 增加顶部边距，避免与菜单栏重叠
            self.main_layout.setContentsMargins(8, 10, 8, 8)  # 增加顶部边距到10px
            self.main_layout.setSpacing(8)  # 增加间距到8px

            # 创建股票列表组并添加到主布局
            stock_group = self.create_stock_list_group()
            self.main_layout.addWidget(stock_group)

            # 创建指标列表组
            self.create_indicator_list_group()

            # 设置面板样式，确保不会覆盖其他组件
            self.setFixedWidth(220)  # 稍微增加宽度
            self.setStyleSheet("""
                StockManagementPanel {
                    background-color: #ffffff;
                    border-right: 1px solid #e9ecef;
                    margin-top: 0px;  /* 确保没有负边距 */
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 5px;
                    background-color: #ffffff;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 8px 0 8px;
                    color: #495057;
                    background-color: #ffffff;
                }
            """)
            add_shadow(self)

            self.log_manager.info("股票管理面板创建完成")

        except Exception as e:
            self.log_manager.error(f"创建股票管理面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def create_stock_list_group(self):
        """创建股票列表组"""
        group_box = QGroupBox("股票管理")
        layout = QVBoxLayout(group_box)

        # 创建筛选区域
        self.create_filter_section(layout)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入股票代码或名称...")
        self.search_edit.textChanged.connect(self.filter_stock_list)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # 股票列表头部信息和控制按钮
        header_layout = QHBoxLayout()
        self.stock_count_label = QLabel("股票数量: 0")
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setMaximumWidth(60)
        self.refresh_button.clicked.connect(self.refresh_stock_list)
        header_layout.addWidget(self.stock_count_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        layout.addLayout(header_layout)

        # 股票列表
        self.stock_list = QListWidget()
        self.stock_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.stock_list.customContextMenuRequested.connect(self.show_stock_list_context_menu)
        self.stock_list.itemClicked.connect(self.on_stock_selected)
        self.stock_list.itemDoubleClicked.connect(self.on_stock_double_clicked)
        layout.addWidget(self.stock_list)

        # 控制按钮区域
        self.create_control_buttons(layout)

        return group_box

    def create_filter_section(self, parent_layout):
        """创建高级筛选区域"""
        filter_group = QGroupBox("高级筛选")
        filter_layout = QVBoxLayout(filter_group)

        # 市场筛选
        market_layout = QHBoxLayout()
        market_layout.addWidget(QLabel("市场:"))
        self.market_combo = QComboBox()
        self.market_combo.addItems(["全部", "沪市", "深市", "创业板", "科创板", "北交所"])
        self.market_combo.currentTextChanged.connect(self.on_market_changed)
        market_layout.addWidget(self.market_combo)
        filter_layout.addLayout(market_layout)

        # 行业筛选
        industry_layout = QHBoxLayout()
        industry_layout.addWidget(QLabel("行业:"))
        self.industry_combo = QComboBox()
        self.industry_combo.addItem("全部")
        self.industry_combo.currentTextChanged.connect(self.on_industry_changed)
        industry_layout.addWidget(self.industry_combo)
        filter_layout.addLayout(industry_layout)

        # 筛选选项
        options_layout = QHBoxLayout()
        self.show_favorites_only = QCheckBox("仅显示收藏")
        self.show_active_only = QCheckBox("仅显示活跃股票")
        self.show_favorites_only.toggled.connect(self.on_filter_options_changed)
        self.show_active_only.toggled.connect(self.on_filter_options_changed)
        options_layout.addWidget(self.show_favorites_only)
        options_layout.addWidget(self.show_active_only)
        filter_layout.addLayout(options_layout)

        parent_layout.addWidget(filter_group)

    def create_control_buttons(self, parent_layout):
        """创建控制按钮区域"""
        button_layout = QHBoxLayout()

        self.add_favorite_btn = QPushButton("添加收藏")
        self.remove_favorite_btn = QPushButton("移除收藏")
        self.export_btn = QPushButton("导出列表")

        self.add_favorite_btn.clicked.connect(self.add_to_favorites)
        self.remove_favorite_btn.clicked.connect(self.remove_from_favorites)
        self.export_btn.clicked.connect(self.export_stock_list)

        button_layout.addWidget(self.add_favorite_btn)
        button_layout.addWidget(self.remove_favorite_btn)
        button_layout.addWidget(self.export_btn)

        parent_layout.addLayout(button_layout)

    def create_indicator_list_group(self):
        """创建指标列表组"""
        indicator_group = QGroupBox("指标列表")
        indicator_layout = QVBoxLayout(indicator_group)
        indicator_layout.setContentsMargins(5, 15, 5, 5)
        indicator_layout.setSpacing(5)

        # 创建指标搜索框
        self.indicator_search = QLineEdit()
        self.indicator_search.setPlaceholderText("搜索指标...")
        indicator_layout.addWidget(self.indicator_search)

        # 创建指标列表控件
        self.indicator_list = QListWidget()
        self.indicator_list.setSelectionMode(QAbstractItemView.MultiSelection)
        indicator_layout.addWidget(self.indicator_list)

        # 初始化指标数据
        self.init_indicator_data()

        # 添加到主布局
        self.main_layout.addWidget(indicator_group)

    def init_indicator_data(self):
        """初始化指标数据 - 使用系统现有的指标分类"""
        try:
            # 导入系统指标算法模块
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

            try:
                # 移除旧的indicators_algo导入，使用统一指标管理器

                # 使用新的指标服务架构获取系统指标分类
                try:
                    from core.services.indicator_ui_adapter import get_indicator_ui_adapter
                    ui_adapter = get_indicator_ui_adapter()
                    indicators_by_category = ui_adapter.get_indicators_by_category(use_chinese=True)
                except ImportError:
                    # 向后兼容：使用统一指标管理器
                    indicators_by_category = get_indicators_by_category(use_chinese=True)

                # 清空现有数据
                self.indicator_list.clear()

                # 添加指标分类和指标
                for category, indicators in indicators_by_category.items():
                    if not indicators:  # 跳过空分类
                        continue

                    # 添加分类标题
                    category_item = QListWidgetItem(f"📊 {category}")
                    category_item.setFlags(Qt.ItemIsEnabled)  # 不可选择
                    category_item.setBackground(QColor(240, 240, 240))
                    category_item.setForeground(QColor(80, 80, 80))
                    font = category_item.font()
                    font.setBold(True)
                    category_item.setFont(font)
                    self.indicator_list.addItem(category_item)

                    # 添加该分类下的指标
                    for indicator in indicators:
                        # 使用新的指标服务架构获取中文名称
                        try:
                            from core.services.indicator_ui_adapter import get_indicator_ui_adapter
                            ui_adapter = get_indicator_ui_adapter()
                            indicators_list = ui_adapter.get_indicator_list_for_ui()

                            # 查找指标信息
                            chinese_name = indicator
                            for ind_info in indicators_list:
                                if isinstance(ind_info, dict) and ind_info.get('id') == indicator:
                                    chinese_name = ind_info.get('name', indicator)
                                    break
                                elif hasattr(ind_info, 'id') and ind_info.id == indicator:
                                    chinese_name = ind_info.name
                                    break
                        except ImportError:
                            # 使用指标适配器获取中文名称
                            indicator_info = self.indicator_adapter.get_indicator_info(indicator)
                            chinese_name = indicator_info.get('chinese_name', indicator) if indicator_info else indicator

                        if chinese_name == indicator:
                            # 如果没有中文名称，使用英文名称
                            display_name = indicator
                        else:
                            # 显示格式：中文名称 (英文名称)
                            display_name = f"{chinese_name} ({indicator})"

                        indicator_item = QListWidgetItem(display_name)
                        indicator_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

                        # 设置指标数据
                        indicator_data = {
                            'name': indicator,
                            'chinese_name': chinese_name,
                            'display_name': display_name,
                            'category': category,
                            'type': 'talib'
                        }
                        indicator_item.setData(Qt.UserRole, indicator_data)

                        self.indicator_list.addItem(indicator_item)

                self.log_manager.info(f"成功加载 {len(indicators_by_category)} 个指标分类")

            except ImportError as e:
                self.log_manager.warning(f"导入指标算法模块失败: {str(e)}，使用内置指标列表")
                self._init_builtin_indicators()

        except Exception as e:
            self.log_manager.error(f"初始化指标数据失败: {str(e)}")
            self._init_builtin_indicators()

    def _init_builtin_indicators(self):
        """初始化内置指标列表（备用方案）"""
        try:
            # 内置指标分类
            builtin_indicators = {
                "趋势类": [
                    ("移动平均线", "MA"),
                    ("指数移动平均", "EMA"),
                    ("简单移动平均", "SMA"),
                    ("加权移动平均", "WMA"),
                    ("布林带", "BOLL"),
                    ("抛物线转向", "SAR")
                ],
                "震荡类": [
                    ("MACD指标", "MACD"),
                    ("相对强弱指标", "RSI"),
                    ("随机指标", "KDJ"),
                    ("商品通道指标", "CCI"),
                    ("威廉指标", "WILLR"),
                    ("动量指标", "MOM"),
                    ("变动率指标", "ROC"),
                    ("平均方向性指标", "ADX")
                ],
                "成交量类": [
                    ("能量潮指标", "OBV"),
                    ("累积/派发线", "AD"),
                    ("资金流量指标", "MFI")
                ],
                "波动性类": [
                    ("平均真实波幅", "ATR"),
                    ("标准化平均真实波幅", "NATR"),
                    ("真实波幅", "TRANGE")
                ]
            }

            # 清空现有数据
            self.indicator_list.clear()

            # 添加指标分类和指标
            for category, indicators in builtin_indicators.items():
                # 添加分类标题
                category_item = QListWidgetItem(f"📊 {category}")
                category_item.setFlags(Qt.ItemIsEnabled)  # 不可选择
                category_item.setBackground(QColor(240, 240, 240))
                category_item.setForeground(QColor(80, 80, 80))
                font = category_item.font()
                font.setBold(True)
                category_item.setFont(font)
                self.indicator_list.addItem(category_item)

                # 添加该分类下的指标
                for chinese_name, english_name in indicators:
                    display_name = f"{chinese_name} ({english_name})"

                    indicator_item = QListWidgetItem(display_name)
                    indicator_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

                    # 设置指标数据
                    indicator_data = {
                        'name': english_name,
                        'chinese_name': chinese_name,
                        'display_name': display_name,
                        'category': category,
                        'type': 'builtin'
                    }
                    indicator_item.setData(Qt.UserRole, indicator_data)

                    self.indicator_list.addItem(indicator_item)

            self.log_manager.info("使用内置指标列表初始化完成")

        except Exception as e:
            self.log_manager.error(f"初始化内置指标列表失败: {str(e)}")

    def setup_connections(self):
        """设置信号连接"""
        # 股票列表相关
        self.stock_list.itemSelectionChanged.connect(self.on_stock_selected)
        self.search_edit.textChanged.connect(self.filter_stock_list)

        # 指标列表相关
        self.indicator_list.itemSelectionChanged.connect(self.on_indicators_changed)
        self.indicator_search.textChanged.connect(self.filter_indicator_list)

    def init_data(self):
        """初始化数据"""
        try:
            # 加载收藏夹
            self.load_favorites()

            # 更新股票列表
            self.update_stock_list()

        except Exception as e:
            self.log_manager.error(f"初始化数据失败: {str(e)}")

    def update_stock_list(self):
        """更新股票列表"""
        try:
            # 获取股票列表
            stock_df = self.data_manager.get_stock_list()

            # 清空列表
            self.stock_list.clear()

            if stock_df.empty:
                self.stock_count_label.setText("当前显示 0 只股票")
                return

            # 添加股票到列表
            for _, stock in stock_df.iterrows():
                # 添加市场前缀到股票代码显示
                code = stock['code']
                market_prefix = stock['market'].casefold()
                display_code = f"{market_prefix}{code}" if market_prefix else code

                # 检查是否在收藏夹中
                is_favorite = display_code in self.favorites
                star_prefix = "★ " if is_favorite else ""

                item_text = f"{star_prefix}{display_code} {stock['name']}"
                item = QListWidgetItem(item_text)

                # 设置股票数据
                stock_data = {
                    'code': code,  # 保持原始代码用于数据处理
                    'display_code': display_code,  # 显示用代码（带前缀）
                    'name': stock['name'],
                    'market': stock.get('market', ''),
                    'industry': stock.get('industry', ''),
                    'type': stock.get('type', ''),
                    'valid': stock.get('valid', True),
                    'is_favorite': is_favorite
                }
                item.setData(Qt.UserRole, stock_data)

                # 设置工具提示
                tooltip = (
                    f"代码: {display_code}\n"
                    f"名称: {stock['name']}\n"
                    f"市场: {stock.get('market', '未知')}\n"
                    f"行业: {stock.get('industry', '未知')}\n"
                    f"收藏: {'是' if is_favorite else '否'}"
                )
                item.setToolTip(tooltip)

                # 如果是收藏股票，设置特殊样式
                if is_favorite:
                    item.setForeground(QColor("#ff6b35"))  # 橙色显示收藏股票
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                self.stock_list.addItem(item)

            # 更新计数
            self.stock_count_label.setText(f"当前显示 {len(stock_df)} 只股票")

        except Exception as e:
            self.log_manager.error(f"更新股票列表失败: {str(e)}")

    def _get_market_prefix(self, code: str) -> str:
        """根据股票代码获取市场前缀"""
        try:
            if not code:
                return ""

            # 根据代码规则判断市场
            if code.startswith('0') or code.startswith('3'):
                return "sz"  # 深市
            elif code.startswith('6'):
                return "sh"  # 沪市
            elif code.startswith('8') or code.startswith('4'):
                return "bj"  # 北交所
            elif code.startswith('9'):
                return "sh"  # 沪市B股
            elif code.startswith('2'):
                return "sz"  # 深市B股
            else:
                return ""  # 其他情况不添加前缀

        except Exception as e:
            self.log_manager.warning(f"获取市场前缀失败: {str(e)}")
            return ""

    def filter_stock_list(self, text: str = ""):
        """过滤股票列表 - 增强版本，支持多种筛选条件"""
        try:
            search_text = text or (self.search_edit.text() if hasattr(self, 'search_edit') else "")
            visible_count = 0

            # 获取筛选条件
            current_market = getattr(self, 'current_market', '全部')
            current_industry = getattr(self, 'current_industry', '全部')
            show_favorites_only = getattr(self, 'show_favorites_only', None)
            show_active_only = getattr(self, 'show_active_only', None)

            for i in range(self.stock_list.count()):
                item = self.stock_list.item(i)
                if not item:
                    continue

                stock_data = item.data(Qt.UserRole)
                if not stock_data:
                    continue

                stock_code = stock_data.get('display_code', '')
                stock_name = stock_data.get('name', '')

                # 基础文本搜索
                text_match = True
                if search_text:
                    text_match = (
                        search_text.lower() in stock_code.lower() or
                        search_text.lower() in stock_name.lower()
                    )

                # 市场筛选
                market_match = True
                if current_market != '全部':
                    stock_market = self.get_market_type_from_code(stock_code)
                    market_match = (stock_market == current_market)

                # 行业筛选
                industry_match = True
                if current_industry != '全部':
                    stock_industry = stock_data.get('industry', '')
                    industry_match = (stock_industry == current_industry)

                # 收藏筛选
                favorites_match = True
                if show_favorites_only and show_favorites_only.isChecked():
                    favorites_match = stock_code in self.favorites

                # 活跃股票筛选（这里可以根据成交量或其他指标判断）
                active_match = True
                if show_active_only and show_active_only.isChecked():
                    # 简单判断：有价格变动的股票认为是活跃的
                    price = stock_data.get('price', 0)
                    active_match = price > 0

                # 综合判断是否显示
                should_show = text_match and market_match and industry_match and favorites_match and active_match

                item.setHidden(not should_show)
                if should_show:
                    visible_count += 1

            # 更新股票数量显示
            if hasattr(self, 'stock_count_label'):
                self.stock_count_label.setText(f"股票数量: {visible_count}")

            self.log_manager.info(f"筛选完成，显示 {visible_count} 只股票")

        except Exception as e:
            self.log_manager.error(f"筛选股票列表失败: {str(e)}")

    def get_market_type_from_code(self, code: str) -> str:
        """根据股票代码获取市场类型"""
        try:
            # 移除前缀获取纯数字代码
            clean_code = code.replace('sh', '').replace('sz', '').replace('bj', '')

            if clean_code.startswith('6'):
                return '沪市'
            elif clean_code.startswith('0'):
                return '深市'
            elif clean_code.startswith('3'):
                return '创业板'
            elif clean_code.startswith('688'):
                return '科创板'
            elif clean_code.startswith('8') or clean_code.startswith('4'):
                return '北交所'
            else:
                return '其他'
        except:
            return '未知'

    def add_to_favorites(self):
        """添加当前选中股票到收藏"""
        try:
            current_item = self.stock_list.currentItem()
            if current_item:
                stock_data = current_item.data(Qt.UserRole)
                if stock_data:
                    stock_code = stock_data['display_code']
                    if stock_code not in self.favorites:
                        self.toggle_favorite(current_item)
                    else:
                        QMessageBox.information(self, "提示", "该股票已在收藏夹中")
                else:
                    QMessageBox.warning(self, "警告", "无法获取股票数据")
            else:
                QMessageBox.information(self, "提示", "请先选择一只股票")
        except Exception as e:
            self.log_manager.error(f"添加收藏失败: {str(e)}")

    def remove_from_favorites(self):
        """从收藏中移除当前选中股票"""
        try:
            current_item = self.stock_list.currentItem()
            if current_item:
                stock_data = current_item.data(Qt.UserRole)
                if stock_data:
                    stock_code = stock_data['display_code']
                    if stock_code in self.favorites:
                        self.toggle_favorite(current_item)
                    else:
                        QMessageBox.information(self, "提示", "当前股票不在收藏夹中")
                else:
                    QMessageBox.warning(self, "警告", "无法获取股票数据")
            else:
                QMessageBox.information(self, "提示", "请先选择一只股票")
        except Exception as e:
            self.log_manager.error(f"移除收藏失败: {str(e)}")

    def filter_indicator_list(self, text: str):
        """过滤指标列表"""
        try:
            for i in range(self.indicator_list.count()):
                item = self.indicator_list.item(i)
                indicator_name = item.text()

                # 文本搜索
                text_match = True
                if text:
                    text_match = text.lower() in indicator_name.lower()

                # 显示/隐藏项目
                item.setHidden(not text_match)

        except Exception as e:
            self.log_manager.error(f"过滤指标列表失败: {str(e)}")

    def on_stock_selected(self):
        """股票选择事件"""
        try:
            current_item = self.stock_list.currentItem()
            if current_item:
                stock_data = current_item.data(Qt.UserRole)
                stock_code = stock_data['display_code']
                self.current_stock = stock_code

                # 发送股票选择信号
                self.stock_selected.emit(stock_code)

                self.log_manager.info(f"选择股票: {stock_code}")

        except Exception as e:
            self.log_manager.error(f"处理股票选择失败: {str(e)}")

    def on_indicators_changed(self):
        """指标选择变化事件 - 修复版本，避免重复处理，只通过信号传递"""
        try:
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                # 如果没有选中指标，发送清除信号
                self.indicator_changed.emit("clear_all", {})
                return

            # 提取选中的指标信息
            selected_indicators = []
            for item in selected_items:
                # 跳过分组标题
                if not item.flags() & Qt.ItemIsSelectable:
                    continue

                indicator_data = item.data(Qt.UserRole)
                if indicator_data and isinstance(indicator_data, dict):
                    indicator_name = indicator_data.get('name', '')
                    indicator_type = indicator_data.get('type', 'builtin')
                    chinese_name = indicator_data.get('chinese_name', indicator_name)

                    # 构建指标信息
                    indicator_info = {
                        'name': indicator_name,
                        'chinese_name': chinese_name,
                        'type': indicator_type,
                        'display_name': indicator_data.get('display_name', chinese_name),
                        'params': self._get_default_indicator_params(indicator_name)
                    }
                    selected_indicators.append(indicator_info)

            if selected_indicators:
                # 只发送指标变化信号给主窗口，不直接调用图表控件
                self.indicator_changed.emit("multiple", {"indicators": selected_indicators})

                indicator_names = [ind['chinese_name'] for ind in selected_indicators]
                self.log_manager.info(f"已选择指标: {', '.join(indicator_names)}")

        except Exception as e:
            self.log_manager.error(f"处理指标变化失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _get_default_indicator_params(self, indicator_name: str) -> dict:
        """获取指标的默认参数 - 使用系统现有的指标配置"""
        try:
            # 导入系统指标算法模块
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

            try:
                # 移除旧的indicators_algo导入，使用统一指标管理器

                # 优先使用新的指标服务架构
                try:
                    from core.services import get_indicator_ui_adapter
                    adapter = get_indicator_ui_adapter()
                    indicator_info = adapter.get_indicator_info(indicator_name)
                    if indicator_info and indicator_info.parameters:
                        return indicator_info.parameters
                except ImportError:
                    pass

                # 使用指标适配器获取参数
                indicator_info = self.indicator_adapter.get_indicator_info(indicator_name)
                if indicator_info and indicator_info.get('parameters'):
                    return indicator_info['parameters']

            except ImportError as e:
                self.log_manager.warning(f"导入指标算法模块失败: {str(e)}")

            # 如果系统配置失败，使用内置的默认参数
            default_params = {
                'MA': {'period': 20},
                'SMA': {'period': 20},
                'EMA': {'period': 12},
                'WMA': {'period': 20},
                'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
                'BOLL': {'period': 20, 'std_dev': 2},
                'BBANDS': {'period': 20, 'std_dev': 2},
                'RSI': {'period': 14},
                'KDJ': {'k_period': 9, 'd_period': 3, 'j_period': 3},
                'STOCH': {'k_period': 14, 'd_period': 3},
                'CCI': {'period': 14},
                'OBV': {},
                'ATR': {'period': 14},
                'ADX': {'period': 14},
                'WILLR': {'period': 14},
                'MOM': {'period': 10},
                'ROC': {'period': 12},
                'TRIX': {'period': 14},
                'DMA': {'short': 10, 'long': 50},
                'DMI': {'period': 14},
                'AROON': {'period': 14},
                'SAR': {'af': 0.02, 'max_af': 0.2},
                'MFI': {'period': 14},
                'CMO': {'period': 14},
                'ULTOSC': {'period1': 7, 'period2': 14, 'period3': 28},
                'BOP': {},
                'APO': {'fast': 12, 'slow': 26},
                'PPO': {'fast': 12, 'slow': 26},
                'PLUS_DI': {'period': 14},
                'PLUS_DM': {'period': 14},
                'MINUS_DI': {'period': 14},
                'MINUS_DM': {'period': 14},
                'NATR': {'period': 14},
                'TRANGE': {},
                'AVGPRICE': {},
                'MEDPRICE': {},
                'TYPPRICE': {},
                'WCLPRICE': {},
                'AD': {},
                'ADOSC': {'fast': 3, 'slow': 10}
            }

            return default_params.get(indicator_name.upper(), {})

        except Exception as e:
            self.log_manager.warning(f"获取指标默认参数失败: {str(e)}")
            return {}

    def show_stock_list_context_menu(self, position):
        """显示股票列表右键菜单"""
        try:
            item = self.stock_list.itemAt(position)
            if not item:
                return

            stock_data = item.data(Qt.UserRole)
            if not stock_data:
                return

            menu = QMenu(self)
            stock_code = stock_data['display_code']
            stock_name = stock_data['name']
            is_favorite = stock_data.get('is_favorite', False)

            # 查看详情
            view_details_action = menu.addAction("📊 查看详情")
            view_details_action.triggered.connect(lambda: self._view_stock_details(stock_code))

            menu.addSeparator()

            # 收藏相关操作
            if is_favorite:
                remove_favorite_action = menu.addAction("💔 取消收藏")
                remove_favorite_action.triggered.connect(lambda: self.remove_from_favorites())
            else:
                add_favorite_action = menu.addAction("❤️ 添加收藏")
                add_favorite_action.triggered.connect(lambda: self.add_to_favorites())

            menu.addSeparator()

            # 分析功能
            analyze_action = menu.addAction("📈 技术分析")
            analyze_action.triggered.connect(lambda: self._analyze_stock(stock_code))

            # 导出数据
            export_action = menu.addAction("💾 导出数据")
            export_action.triggered.connect(lambda: self._export_stock_data(stock_code))

            menu.addSeparator()

            # 复制代码
            copy_code_action = menu.addAction("📋 复制代码")
            copy_code_action.triggered.connect(lambda: self._copy_stock_code(stock_code))

            # 复制名称
            copy_name_action = menu.addAction("📋 复制名称")
            copy_name_action.triggered.connect(lambda: self._copy_stock_name(stock_name))

            # 显示菜单
            menu.exec_(self.stock_list.mapToGlobal(position))

        except Exception as e:
            self.log_manager.error(f"显示右键菜单失败: {str(e)}")

    def _view_stock_details(self, stock_code: str):
        """查看股票详情"""
        try:
            # 发送股票选择信号，让主窗口处理
            self.stock_selected.emit(stock_code)
            self.log_manager.info(f"查看股票详情: {stock_code}")
        except Exception as e:
            self.log_manager.error(f"查看股票详情失败: {str(e)}")

    def _analyze_stock(self, stock_code: str):
        """分析股票"""
        try:
            # 发送股票选择信号，让主窗口处理分析
            self.stock_selected.emit(stock_code)
            self.log_manager.info(f"开始分析股票: {stock_code}")

            # 如果主窗口有分析方法，调用它
            if hasattr(self.parent(), 'on_stock_selected_from_panel'):
                self.parent().on_stock_selected_from_panel(stock_code)
        except Exception as e:
            self.log_manager.error(f"分析股票失败: {str(e)}")

    def _export_stock_data(self, stock_code: str):
        """导出股票数据"""
        try:
            # 获取股票数据
            kdata = self.get_kdata(stock_code)
            if kdata.empty:
                QMessageBox.warning(self, "警告", f"无法获取股票 {stock_code} 的数据")
                return

            # 选择保存文件
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                f"导出股票数据 - {stock_code}",
                f"{stock_code}_data.csv",
                "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json)"
            )

            if not file_path:
                return

            # 保存文件
            if file_path.endswith('.xlsx'):
                kdata.to_excel(file_path, index=True, engine='openpyxl')
            elif file_path.endswith('.json'):
                kdata.to_json(file_path, orient='index', date_format='iso', indent=2)
            else:  # CSV
                kdata.to_csv(file_path, index=True, encoding='utf-8-sig')

            QMessageBox.information(
                self,
                "导出成功",
                f"股票数据已导出到: {file_path}\n共导出 {len(kdata)} 条记录"
            )

            self.log_manager.info(f"股票数据导出成功: {file_path}")
            self.export_completed.emit(file_path)

        except Exception as e:
            error_msg = f"导出股票数据失败: {str(e)}"
            self.log_manager.error(error_msg)
            QMessageBox.critical(self, "导出失败", error_msg)

    def _copy_stock_code(self, stock_code: str):
        """复制股票代码到剪贴板"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(stock_code)
            self.log_manager.info(f"已复制股票代码: {stock_code}")

            # 显示临时提示
            QToolTip.showText(QCursor.pos(), f"已复制: {stock_code}", self, QRect(), 2000)
        except Exception as e:
            self.log_manager.error(f"复制股票代码失败: {str(e)}")

    def _copy_stock_name(self, stock_name: str):
        """复制股票名称到剪贴板"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(stock_name)
            self.log_manager.info(f"已复制股票名称: {stock_name}")

            # 显示临时提示
            QToolTip.showText(QCursor.pos(), f"已复制: {stock_name}", self, QRect(), 2000)
        except Exception as e:
            self.log_manager.error(f"复制股票名称失败: {str(e)}")

    def toggle_favorite(self, item=None):
        """切换收藏状态"""
        try:
            # 参数类型检查和处理
            if item is None or isinstance(item, bool):
                # 如果参数为None或bool类型，获取当前选中的项
                item = self.stock_list.currentItem()

            if item is None:
                self.log_manager.warning("没有选中的股票项目")
                return

            # 确保item是QListWidgetItem类型
            if not hasattr(item, 'data'):
                self.log_manager.warning(f"无效的股票项目类型: {type(item)}")
                return

            stock_data = item.data(Qt.UserRole)
            if not stock_data:
                self.log_manager.warning("股票项目没有关联数据")
                return

            stock_code = stock_data['display_code']
            stock_name = stock_data['name']

            # 检查是否已收藏
            is_favorite = stock_code in self.favorites

            if is_favorite:
                # 从收藏中移除
                self.favorites.remove(stock_code)
                self.log_manager.info(f"从收藏中移除: {stock_name}({stock_code})")
                new_favorite_status = False
            else:
                # 添加到收藏
                self.favorites.append(stock_code)
                self.log_manager.info(f"添加到收藏: {stock_name}({stock_code})")
                new_favorite_status = True

            # 保存收藏夹
            self.save_favorites()

            # 立即更新当前项的显示（不重建整个列表）
            self._update_single_item_favorite_status(item, new_favorite_status)

            # 发送收藏变化信号
            self.stock_favorites_changed.emit()

        except Exception as e:
            self.log_manager.error(f"切换收藏状态失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _update_single_item_favorite_status(self, item, is_favorite):
        """更新单个列表项的收藏状态显示"""
        try:
            stock_data = item.data(Qt.UserRole)
            if not stock_data:
                return

            stock_code = stock_data['display_code']
            stock_name = stock_data['name']

            # 构建新的显示文本
            if is_favorite:
                display_text = f"★ {stock_code} {stock_name}"
                # 设置收藏样式
                item.setForeground(QColor("#ff6b35"))  # 橙色显示收藏股票
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            else:
                display_text = f"{stock_code} {stock_name}"
                # 恢复默认样式
                item.setForeground(QColor("#000000"))  # 黑色默认文字
                font = item.font()
                font.setBold(False)
                item.setFont(font)

            # 更新列表项文本
            item.setText(display_text)

            # 更新股票数据中的收藏状态
            stock_data['is_favorite'] = is_favorite
            item.setData(Qt.UserRole, stock_data)

            # 更新工具提示
            tooltip = (
                f"代码: {stock_code}\n"
                f"名称: {stock_name}\n"
                f"市场: {stock_data.get('market', '未知')}\n"
                f"行业: {stock_data.get('industry', '未知')}\n"
                f"收藏: {'是' if is_favorite else '否'}"
            )
            item.setToolTip(tooltip)

            # 强制刷新当前项
            self.stock_list.update()

        except Exception as e:
            self.log_manager.error(f"更新列表项收藏状态失败: {str(e)}")

    def load_favorites(self):
        """加载收藏夹 - 增强版本，自动修复空文件或损坏文件"""
        try:
            # 收藏夹文件路径 - 使用更好的路径处理
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'config')
            os.makedirs(config_dir, exist_ok=True)
            favorites_file = os.path.join(config_dir, 'stock_favorites.json')

            if os.path.exists(favorites_file):
                try:
                    with open(favorites_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content:
                            self.favorites = []
                            self.log_manager.warning("收藏列表文件为空，已自动初始化为空列表")
                        else:
                            favorites_data = json.loads(content)
                            # 确保是列表格式
                            if isinstance(favorites_data, list):
                                self.favorites = favorites_data
                            else:
                                self.favorites = []
                                self.log_manager.warning("收藏列表格式错误，已重置为空列表")
                            self.log_manager.info(f"已加载 {len(self.favorites)} 个收藏股票")
                except json.JSONDecodeError as e:
                    self.favorites = []
                    self.log_manager.warning(f"收藏列表JSON格式错误，已自动重置: {str(e)}")
                    # 自动修复文件
                    with open(favorites_file, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                except Exception as e:
                    self.favorites = []
                    self.log_manager.warning(f"收藏列表文件损坏，已重置: {str(e)}")
                    # 备份损坏的文件
                    backup_file = f"{favorites_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    try:
                        os.rename(favorites_file, backup_file)
                        self.log_manager.info(f"损坏的收藏列表已备份到: {backup_file}")
                    except:
                        pass
                    # 创建新的空文件
                    with open(favorites_file, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
            else:
                self.favorites = []
                self.log_manager.info("未找到收藏夹文件，创建新的收藏列表")

        except Exception as e:
            self.log_manager.error(f"加载收藏夹失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            self.favorites = []

    def save_favorites(self):
        """保存收藏夹 - 增强版本，确保文件内容为合法JSON数组"""
        try:
            # 收藏夹文件路径
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'config')
            os.makedirs(config_dir, exist_ok=True)
            favorites_file = os.path.join(config_dir, 'stock_favorites.json')

            # 确保favorites为列表类型
            if not isinstance(self.favorites, list):
                self.favorites = list(self.favorites) if self.favorites else []

            # 去重并排序
            self.favorites = sorted(list(set(self.favorites)))

            # 先写入临时文件，再重命名，确保原子性操作
            temp_file = f"{favorites_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, ensure_ascii=False, indent=2)

            # 验证写入的文件
            with open(temp_file, 'r', encoding='utf-8') as f:
                json.load(f)  # 验证JSON格式

            # 原子性替换
            if os.path.exists(favorites_file):
                backup_file = f"{favorites_file}.bak"
                os.replace(favorites_file, backup_file)
            os.replace(temp_file, favorites_file)

            self.log_manager.info(f"已保存 {len(self.favorites)} 个收藏股票")

        except Exception as e:
            self.log_manager.error(f"保存收藏夹失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            # 清理临时文件
            temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'config', 'stock_favorites.json.tmp')
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def show_advanced_search_dialog(self):
        """显示高级搜索对话框"""
        try:
            # 创建高级搜索对话框
            dialog = AdvancedSearchDialog(
                parent=self,
                data_manager=self.parent().data_manager if hasattr(self.parent(), 'data_manager') else None,
                log_manager=self.log_manager
            )

            # 连接搜索完成信号
            dialog.search_completed.connect(self.update_search_results)

            # 显示对话框
            dialog.exec_()

        except Exception as e:
            self.log_manager.error(f"显示高级搜索对话框失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"显示高级搜索对话框失败: {str(e)}")

    def update_search_results(self, filtered_stocks):
        """更新搜索结果"""
        try:
            # 清空当前列表
            self.stock_list.clear()

            # 添加搜索结果
            for stock in filtered_stocks:
                self.add_stock_to_list(stock)

            self.log_manager.info(f"搜索完成，找到 {len(filtered_stocks)} 只符合条件的股票")

        except Exception as e:
            self.log_manager.error(f"更新搜索结果失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def add_stock_to_list(self, stock_data):
        """将股票添加到列表"""
        try:
            # 创建列表项
            display_text = f"{stock_data['display_code']} {stock_data['name']}"

            # 如果在收藏中，添加星号（统一使用★）
            if stock_data['display_code'] in self.favorites:
                display_text = f"★ {display_text}"

            item = QListWidgetItem(display_text)

            # 设置股票数据
            item.setData(Qt.UserRole, stock_data)

            # 设置工具提示
            tooltip = (
                f"代码: {stock_data['display_code']}\n"
                f"名称: {stock_data['name']}\n"
                f"市场: {stock_data.get('market', '未知')}\n"
                f"行业: {stock_data.get('industry', '未知')}"
            )
            item.setToolTip(tooltip)

            # 添加到列表
            self.stock_list.addItem(item)

        except Exception as e:
            self.log_manager.error(f"添加股票到列表失败: {str(e)}")

    def get_current_stock(self) -> Optional[str]:
        """获取当前选中的股票代码"""
        return self.current_stock

    def get_selected_indicators(self) -> List[str]:
        """获取选中的指标列表"""
        try:
            selected_items = self.indicator_list.selectedItems()
            return [item.text() for item in selected_items]
        except Exception as e:
            self.log_manager.error(f"获取选中指标失败: {str(e)}")
            return []

    def set_current_stock(self, stock_code: str):
        """设置当前股票"""
        try:
            self.current_stock = stock_code

            # 在列表中选中对应的股票
            for i in range(self.stock_list.count()):
                item = self.stock_list.item(i)
                if item is not None:
                    stock_data = item.data(Qt.UserRole)
                    if stock_data and stock_data.get('code') == stock_code:
                        self.stock_list.setCurrentItem(item)
                        break

        except Exception as e:
            self.log_manager.error(f"设置当前股票失败: {str(e)}")

    def update_stock_list_display(self):
        """更新股票列表显示 - 增强版本，确保收藏状态正确显示"""
        try:
            if not hasattr(self, 'stock_list'):
                return

            # 遍历所有列表项，更新显示文本
            for i in range(self.stock_list.count()):
                item = self.stock_list.item(i)
                if item:
                    stock_data = item.data(Qt.UserRole)
                    if stock_data:
                        stock_code = stock_data.get('display_code', '')
                        is_favorite = stock_code in self.favorites
                        self._update_single_item_favorite_status(item, is_favorite)

            # 强制刷新UI
            self.stock_list.update()
            self.stock_list.repaint()

        except Exception as e:
            self.log_manager.error(f"更新股票列表显示失败: {str(e)}")

    def refresh_stock_list(self):
        """刷新股票列表"""
        try:
            self.update_stock_list()

        except Exception as e:
            self.log_manager.error(f"刷新股票列表失败: {str(e)}")

    def export_stock_list(self):
        """导出股票列表 - 增强版本，支持多种格式"""
        try:
            # 选择保存文件
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出股票列表",
                "stock_list.csv",
                "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json)"
            )

            if not file_path:
                return

            # 获取股票列表数据
            stock_df = self.data_manager.get_stock_list()
            if stock_df.empty:
                QMessageBox.warning(self, "警告", "没有股票数据可以导出")
                return

            # 构建导出数据
            export_data = []
            for _, stock in stock_df.iterrows():
                code = stock['code']
                market_prefix = self._get_market_prefix(code)
                display_code = f"{market_prefix}{code}" if market_prefix else code

                export_data.append({
                    '股票代码': display_code,
                    '股票名称': stock['name'],
                    '市场': stock.get('market', ''),
                    '行业': stock.get('industry', ''),
                    '类型': stock.get('type', ''),
                    '是否有效': stock.get('valid', True),
                    '是否收藏': code in self.favorites,
                    '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            # 根据文件扩展名保存
            if file_path.endswith('.xlsx'):
                df = pd.DataFrame(export_data)
                df.to_excel(file_path, index=False, engine='openpyxl')
            elif file_path.endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            else:  # CSV
                df = pd.DataFrame(export_data)
                df.to_csv(file_path, index=False, encoding='utf-8-sig')

            QMessageBox.information(
                self,
                "导出成功",
                f"股票列表已导出到: {file_path}\n共导出 {len(export_data)} 只股票"
            )

            self.log_manager.info(f"股票列表导出成功: {file_path}, 共 {len(export_data)} 只股票")
            self.export_completed.emit(file_path)

        except Exception as e:
            error_msg = f"导出股票列表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "导出失败", error_msg)

    def get_kdata(self, code: str, use_cache: bool = True) -> pd.DataFrame:
        """获取K线数据 - 带缓存机制"""
        try:
            if not code:
                return pd.DataFrame()

            # 检查缓存
            current_period = getattr(self.parent_gui, 'current_period', 'D')
            cache_key = f"kdata_{code}_{current_period}"

            if use_cache and cache_key in self.data_cache:
                return self.data_cache[cache_key]

            # 从数据管理器获取数据
            kdata = self.data_manager.get_k_data(code)

            # 缓存数据
            if not kdata.empty and len(self.data_cache) < self.max_cache_size:
                self.data_cache[cache_key] = kdata

            return kdata

        except Exception as e:
            error_msg = f"获取K线数据失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.data_error.emit(error_msg)
            return pd.DataFrame()

    def clear_cache(self):
        """清空数据缓存"""
        try:
            self.data_cache.clear()
            self.log_manager.info("数据缓存已清空")
        except Exception as e:
            self.log_manager.error(f"清空缓存失败: {str(e)}")

    def handle_data_request(self, request_data: Dict[str, Any]):
        """处理数据请求"""
        try:
            if self.data_manager:
                response_data = self.data_manager.get_data(request_data)
                self.data_loaded.emit(response_data)
        except Exception as e:
            error_msg = f"处理数据请求失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.data_error.emit(error_msg)

    def preload_data(self):
        """预加载数据"""
        try:
            self.log_manager.info("开始预加载数据...")

            # 预加载股票列表
            self._preload_stock_list()

            # 预加载行业数据
            self._preload_industry_data()

            self.log_manager.info("数据预加载完成")

        except Exception as e:
            error_msg = f"预加载数据失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())

    def _preload_stock_list(self):
        """预加载股票列表"""
        try:
            stock_df = self.data_manager.get_stock_list()
            if not stock_df.empty:
                # 缓存股票列表
                self.data_cache["stock_list"] = stock_df
                self.log_manager.info(f"预加载股票列表完成，共 {len(stock_df)} 只股票")
        except Exception as e:
            self.log_manager.error(f"预加载股票列表失败: {str(e)}")

    def _preload_industry_data(self):
        """预加载行业数据"""
        try:
            if hasattr(self.parent_gui, 'industry_manager') and self.parent_gui.industry_manager:
                # 触发行业数据更新
                self.parent_gui.industry_manager.update_industry_data()
                self.log_manager.info("预加载行业数据完成")
        except Exception as e:
            self.log_manager.error(f"预加载行业数据失败: {str(e)}")

    def init_market_industry_mapping(self):
        """初始化市场和行业映射"""
        try:
            stock_df = self.data_manager.get_stock_list()
            if stock_df.empty:
                return

            # 构建市场映射
            market_mapping = {}
            industry_mapping = {}

            for _, stock in stock_df.iterrows():
                try:
                    code = stock['code']
                    market = stock.get('market', '')

                    # 市场映射
                    if market and market not in market_mapping:
                        market_mapping[market] = []
                    if market:
                        market_mapping[market].append(code)

                    # 行业映射
                    industry = stock.get('industry', '')
                    if industry and industry not in industry_mapping:
                        industry_mapping[industry] = []
                    if industry:
                        industry_mapping[industry].append(code)

                except Exception as e:
                    continue

            # 更新映射
            self.market_block_mapping = market_mapping
            self.industry_mapping = industry_mapping

            self.log_manager.info(f"市场和行业映射初始化完成，市场数: {len(market_mapping)}, 行业数: {len(industry_mapping)}")

        except Exception as e:
            error_msg = f"初始化市场和行业映射失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())

    def on_data_source_changed(self, source: str):
        """数据源变更处理"""
        try:
            self.log_manager.info(f"数据源变更为: {source}")

            # 清除相关缓存
            self.clear_cache()

            # 重新预加载数据
            self.preload_data()

            # 刷新UI
            self.update_stock_list()

        except Exception as e:
            error_msg = f"处理数据源变更失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.data_error.emit(error_msg)

    def show_indicator_params_dialog(self):
        """显示指标参数设置对话框"""
        try:
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选择指标")
                return

            from gui.dialogs import IndicatorParamsDialog

            indicators = [(item.text(), item.data(Qt.UserRole)) for item in selected_items]
            dialog = IndicatorParamsDialog(indicators, self)
            dialog.params_updated.connect(self._handle_indicator_params_update)
            dialog.exec_()
        except Exception as e:
            self.log_manager.error(f"显示指标参数设置对话框失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"显示指标参数设置对话框失败: {str(e)}")

    def _handle_indicator_params_update(self, params_dict):
        """处理指标参数更新"""
        try:
            # 更新参数控件字典
            if not hasattr(self, 'param_controls'):
                self.param_controls = {}

            self.param_controls.update(params_dict)

            # 发送指标变化信号，让主窗口更新图表
            self.indicator_changed.emit("params_updated", params_dict)

            self.log_manager.info("指标参数已更新")
        except Exception as e:
            self.log_manager.error(f"处理指标参数更新失败: {str(e)}")

    def on_market_changed(self, market: str):
        """市场筛选变化"""
        self.current_market = getattr(self, 'current_market', '全部')
        self.current_market = market
        self.apply_filters()

    def on_industry_changed(self, industry: str):
        """行业筛选变化"""
        self.current_industry = getattr(self, 'current_industry', '全部')
        self.current_industry = industry
        self.apply_filters()

    def on_filter_options_changed(self):
        """筛选选项变化"""
        self.apply_filters()

    def apply_filters(self):
        """应用筛选条件"""
        try:
            # 获取当前的搜索文本
            search_text = getattr(self, 'search_edit', None)
            if search_text:
                search_text = search_text.text()
            else:
                search_text = ""

            # 应用综合筛选
            self.filter_stock_list(search_text)

        except Exception as e:
            self.log_manager.error(f"应用筛选条件失败: {str(e)}")

    def on_stock_double_clicked(self, item):
        """股票双击事件"""
        try:
            if item:
                stock_data = item.data(Qt.UserRole)
                if stock_data:
                    stock_code = stock_data['display_code']
                    self._view_stock_details(stock_code)
        except Exception as e:
            self.log_manager.error(f"处理股票双击事件失败: {str(e)}")
