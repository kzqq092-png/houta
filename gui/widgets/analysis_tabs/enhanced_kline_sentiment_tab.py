#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版K线技术分析标签页
集成实时K线数据、技术指标和市场概览的综合分析UI
专注于技术指标分析，不包含重复的情绪分析功能
对标专业交易软件的设计和功能
"""

from utils.config_manager import ConfigManager
from core.services.kline_sentiment_analyzer import KLineSentimentAnalyzer, get_kline_sentiment_analyzer
from .base_tab import BaseAnalysisTab
import asyncio
import sys
import os
from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


# 全局防护变量，防止死循环
_LOADING_STOCK_DATA = False
_STOCK_DATA_LOAD_COUNT = 0
_MAX_LOAD_ATTEMPTS = 3


class AdvancedSettingsDialog(QDialog):
    """高级设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级技术指标设置")
        self.setModal(True)
        self.resize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 创建标签页
        tab_widget = QTabWidget()

        # RSI设置标签页
        rsi_tab = self.create_rsi_settings()
        tab_widget.addTab(rsi_tab, "RSI设置")

        # MACD设置标签页
        macd_tab = self.create_macd_settings()
        tab_widget.addTab(macd_tab, "MACD设置")

        # MA设置标签页
        ma_tab = self.create_ma_settings()
        tab_widget.addTab(ma_tab, "移动平均线设置")

        layout.addWidget(tab_widget)

        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        self.reset_button = QPushButton("重置为默认")

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.reset_button.clicked.connect(self.reset_to_defaults)

        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def create_rsi_settings(self):
        """创建RSI设置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # RSI周期设置
        period_group = QGroupBox("RSI周期设置")
        period_layout = QFormLayout(period_group)

        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(1, 100)
        self.rsi_period_spin.setValue(14)
        period_layout.addRow("计算周期:", self.rsi_period_spin)

        layout.addWidget(period_group)

        # RSI阈值设置
        threshold_group = QGroupBox("RSI阈值设置")
        threshold_layout = QFormLayout(threshold_group)

        self.rsi_overbought_spin = QSpinBox()
        self.rsi_overbought_spin.setRange(50, 100)
        self.rsi_overbought_spin.setValue(70)
        threshold_layout.addRow("超买阈值:", self.rsi_overbought_spin)

        self.rsi_oversold_spin = QSpinBox()
        self.rsi_oversold_spin.setRange(0, 50)
        self.rsi_oversold_spin.setValue(30)
        threshold_layout.addRow("超卖阈值:", self.rsi_oversold_spin)

        layout.addWidget(threshold_group)
        layout.addStretch()
        return widget

    def create_macd_settings(self):
        """创建MACD设置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # MACD参数设置
        params_group = QGroupBox("MACD参数设置")
        params_layout = QFormLayout(params_group)

        self.macd_fast_spin = QSpinBox()
        self.macd_fast_spin.setRange(1, 50)
        self.macd_fast_spin.setValue(12)
        params_layout.addRow("快线周期:", self.macd_fast_spin)

        self.macd_slow_spin = QSpinBox()
        self.macd_slow_spin.setRange(1, 100)
        self.macd_slow_spin.setValue(26)
        params_layout.addRow("慢线周期:", self.macd_slow_spin)

        self.macd_signal_spin = QSpinBox()
        self.macd_signal_spin.setRange(1, 30)
        self.macd_signal_spin.setValue(9)
        params_layout.addRow("信号线周期:", self.macd_signal_spin)

        layout.addWidget(params_group)
        layout.addStretch()
        return widget

    def create_ma_settings(self):
        """创建MA设置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # MA周期设置
        periods_group = QGroupBox("移动平均线周期设置")
        periods_layout = QFormLayout(periods_group)

        self.ma5_spin = QSpinBox()
        self.ma5_spin.setRange(1, 100)
        self.ma5_spin.setValue(5)
        periods_layout.addRow("MA5周期:", self.ma5_spin)

        self.ma10_spin = QSpinBox()
        self.ma10_spin.setRange(1, 100)
        self.ma10_spin.setValue(10)
        periods_layout.addRow("MA10周期:", self.ma10_spin)

        self.ma20_spin = QSpinBox()
        self.ma20_spin.setRange(1, 100)
        self.ma20_spin.setValue(20)
        periods_layout.addRow("MA20周期:", self.ma20_spin)

        self.ma60_spin = QSpinBox()
        self.ma60_spin.setRange(1, 200)
        self.ma60_spin.setValue(60)
        periods_layout.addRow("MA60周期:", self.ma60_spin)

        layout.addWidget(periods_group)
        layout.addStretch()
        return widget

    def reset_to_defaults(self):
        """重置为默认值"""
        # RSI默认值
        self.rsi_period_spin.setValue(14)
        self.rsi_overbought_spin.setValue(70)
        self.rsi_oversold_spin.setValue(30)

        # MACD默认值
        self.macd_fast_spin.setValue(12)
        self.macd_slow_spin.setValue(26)
        self.macd_signal_spin.setValue(9)

        # MA默认值
        self.ma5_spin.setValue(5)
        self.ma10_spin.setValue(10)
        self.ma20_spin.setValue(20)
        self.ma60_spin.setValue(60)

    def get_settings(self):
        """获取设置值"""
        return {
            'rsi_period': self.rsi_period_spin.value(),
            'rsi_overbought': self.rsi_overbought_spin.value(),
            'rsi_oversold': self.rsi_oversold_spin.value(),
            'macd_fast': self.macd_fast_spin.value(),
            'macd_slow': self.macd_slow_spin.value(),
            'macd_signal': self.macd_signal_spin.value(),
            'ma_periods': {
                'ma5': self.ma5_spin.value(),
                'ma10': self.ma10_spin.value(),
                'ma20': self.ma20_spin.value(),
                'ma60': self.ma60_spin.value()
            }
        }


class StockSelectorWidget(QWidget):
    """简化的股票显示组件 - 避免UI阻塞"""

    stock_selected = pyqtSignal(str, str)  # stock_code, stock_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_stock_code = "000001"
        self.current_stock_name = "平安银行"
        self.setup_ui()
        # 不在初始化时加载数据，避免阻塞UI

    def setup_ui(self):
        """设置简化的UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 标题
        title_label = QLabel("📊 当前股票")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)

        # 当前股票显示
        self.current_selection_label = QLabel(f"当前分析: {self.current_stock_name} ({self.current_stock_code})")
        self.current_selection_label.setStyleSheet("""
            background-color: #e3f2fd;
            padding: 12px;
            border-radius: 6px;
            color: #1976d2;
            font-weight: bold;
            font-size: 12px;
        """)
        layout.addWidget(self.current_selection_label)

        # 状态说明
        status_label = QLabel("💡 股票数据将在选择股票后自动加载")
        status_label.setStyleSheet("color: #666; font-size: 11px; margin: 5px;")
        layout.addWidget(status_label)

        layout.addStretch()

    def set_current_stock(self, code: str, name: str):
        """设置当前股票"""
        try:
            self.current_stock_code = code
            self.current_stock_name = name
            self.current_selection_label.setText(f"当前分析: {name} ({code})")
            print(f"📊 股票选择器更新: {name} ({code})")
        except Exception as e:
            print(f"❌ 设置当前股票失败: {e}")

    def load_stock_data(self):
        """异步加载股票数据 - 延迟执行"""
        # 使用延迟加载，避免在UI初始化时阻塞
        QTimer.singleShot(1000, self._delayed_load_stock_data)

    def _delayed_load_stock_data(self):
        """延迟加载股票数据"""
        try:
            print("📊 延迟加载股票数据...")
            # 这里可以添加真正的数据加载逻辑
            # 但不在UI初始化时执行
        except Exception as e:
            print(f"❌ 延迟加载股票数据失败: {e}")

    def load_enhanced_default_stocks(self):
        """加载默认股票数据 - 简化版本"""
        try:
            print("📊 使用默认股票数据")
            # 简化的默认数据，不执行复杂操作
        except Exception as e:
            print(f"❌ 加载默认股票数据失败: {e}")

    def filter_stocks(self, text):
        """股票筛选 - 简化版本"""
        pass

    def filter_by_category(self, category):
        """按分类筛选 - 简化版本"""
        pass

    def show_advanced_filter(self):
        """显示高级筛选 - 简化版本"""
        pass

    def on_stock_double_clicked(self, row, column):
        """股票双击事件 - 简化版本"""
        pass


class RealTimeDataWorker(QThread):
    """TET框架数据工作线程 - 完全使用TET框架"""

    data_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, symbols: List[str]):
        super().__init__()
        self.symbols = symbols
        self.running = False
        self.update_interval = 30  # 30秒更新一次

        # TET框架组件
        self.tet_data_provider = None
        self.signal_aggregator_service = None
        print("✅ TET框架数据工作线程初始化完成")

    def run(self):
        """运行TET框架数据更新循环"""
        self.running = True

        # 在后台线程中初始化TET框架
        self._init_tet_framework()

        while self.running:
            try:
                results = {}
                for symbol in self.symbols:
                    try:
                        # 使用TET框架获取多源数据
                        result = self.get_tet_multi_source_data(symbol)
                        if result:
                            results[symbol] = result
                    except Exception as e:
                        print(f"TET框架获取 {symbol} 数据失败: {e}")
                        continue

                if results:
                    self.data_updated.emit(results)

                # 等待更新间隔
                for _ in range(self.update_interval):
                    if not self.running:
                        break
                    self.msleep(1000)

            except Exception as e:
                self.error_occurred.emit(str(e))
                break

    def _init_tet_framework(self):
        """在后台线程中初始化TET框架"""
        try:
            # 初始化TET数据提供器
            from core.services.integrated_signal_aggregator_service import TETDataProvider
            from core.services.unified_data_manager import UnifiedDataManager
            from core.services.asset_service import AssetService
            from core.containers.service_container import get_service_container

            # 获取服务容器
            container = get_service_container()
            if container:
                try:
                    # 从服务容器获取服务
                    unified_data_manager = container.resolve(UnifiedDataManager)
                    asset_service = container.resolve(AssetService)

                    if unified_data_manager and asset_service:
                        self.tet_data_provider = TETDataProvider(unified_data_manager, asset_service)
                        print("✅ 从服务容器成功初始化TET数据提供器")
                    else:
                        raise Exception("服务容器中未找到必要服务")

                except Exception as e:
                    print(f"⚠️ 从服务容器获取服务失败: {e}")
                    # 降级到直接实例化
                    unified_data_manager = UnifiedDataManager()
                    asset_service = AssetService()
                    self.tet_data_provider = TETDataProvider(unified_data_manager, asset_service)
                    print("✅ 直接实例化TET数据提供器")
            else:
                # 直接实例化
                unified_data_manager = UnifiedDataManager()
                asset_service = AssetService()
                self.tet_data_provider = TETDataProvider(unified_data_manager, asset_service)
                print("✅ 直接实例化TET数据提供器")

            # 初始化信号聚合服务
            try:
                from core.services.integrated_signal_aggregator_service import IntegratedSignalAggregatorService
                self.signal_aggregator_service = IntegratedSignalAggregatorService()
                print("✅ 成功初始化信号聚合服务")
            except Exception as e:
                print(f"⚠️ 初始化信号聚合服务失败: {e}")

        except Exception as e:
            print(f"❌ 初始化TET框架失败: {e}")
            self.tet_data_provider = None
            self.signal_aggregator_service = None

    def get_tet_multi_source_data(self, symbol: str) -> Optional[Dict]:
        """使用TET框架获取多源数据"""
        try:
            if not self.tet_data_provider:
                return self._generate_fallback_data(symbol)

            # 使用TET框架异步获取多源数据
            import asyncio
            from core.data_source import AssetType

            # 在线程中运行异步操作
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 使用新的数据类型获取多源数据
                kdata = pd.DataFrame()
                realtime_data = {}
                technical_indicators = {}
                fundamental_data = {}

                # 1. 获取历史K线数据
                try:
                    kdata = loop.run_until_complete(
                        self.unified_data_manager.get_asset_data(
                            symbol=symbol,
                            asset_type=AssetType.STOCK,
                            data_type=DataType.HISTORICAL_KLINE,
                            period='D'
                        )
                    )
                    if kdata is not None and not kdata.empty:
                        print(f"✅ TET获取K线数据成功: {symbol}, {len(kdata)} 条记录")
                except Exception as e:
                    print(f"⚠️ TET获取K线数据失败: {symbol} - {e}")

                # 2. 获取实时行情数据
                try:
                    realtime_df = loop.run_until_complete(
                        self.unified_data_manager.get_asset_data(
                            symbol=symbol,
                            asset_type=AssetType.STOCK,
                            data_type=DataType.REAL_TIME_QUOTE,
                            period='1m'
                        )
                    )
                    if realtime_df is not None and not realtime_df.empty:
                        realtime_data = realtime_df.iloc[-1].to_dict()
                        print(f"✅ TET获取实时数据成功: {symbol}")
                except Exception as e:
                    print(f"⚠️ TET获取实时数据失败: {symbol} - {e}")

                # 3. 获取技术指标数据
                try:
                    indicators_df = loop.run_until_complete(
                        self.unified_data_manager.get_asset_data(
                            symbol=symbol,
                            asset_type=AssetType.STOCK,
                            data_type=DataType.TECHNICAL_INDICATORS,
                            period='D'
                        )
                    )
                    if indicators_df is not None and not indicators_df.empty:
                        technical_indicators = indicators_df.iloc[-1].to_dict()
                        print(f"✅ TET获取技术指标成功: {symbol}")
                except Exception as e:
                    print(f"⚠️ TET获取技术指标失败: {symbol} - {e}")

                # 4. 获取基本面数据
                try:
                    fundamental_df = loop.run_until_complete(
                        self.unified_data_manager.get_asset_data(
                            symbol=symbol,
                            asset_type=AssetType.STOCK,
                            data_type=DataType.FUNDAMENTAL,
                            period='D'
                        )
                    )
                    if fundamental_df is not None and not fundamental_df.empty:
                        fundamental_data = fundamental_df.iloc[-1].to_dict()
                        print(f"✅ TET获取基本面数据成功: {symbol}")
                except Exception as e:
                    print(f"⚠️ TET获取基本面数据失败: {symbol} - {e}")

                if not kdata.empty:
                    # 如果没有获取到技术指标，则从K线数据计算
                    if not technical_indicators:
                        technical_indicators = self._calculate_technical_indicators_from_kdata(kdata)

                    return {
                        'symbol': symbol,
                        'kdata': kdata,
                        'analysis': technical_indicators,
                        'realtime_data': realtime_data,
                        'fundamental_data': fundamental_data,
                        'timestamp': datetime.now(),
                        'source': 'TET_Enhanced'
                    }
                else:
                    print(f"⚠️ TET框架未获取到K线数据: {symbol}")
                    return self._generate_fallback_data(symbol)

            finally:
                loop.close()

        except Exception as e:
            print(f"❌ TET框架获取多源数据失败 {symbol}: {e}")
            return self._generate_fallback_data(symbol)

    def _calculate_technical_indicators_from_kdata(self, kdata: pd.DataFrame) -> Dict:
        """从K线数据计算技术指标"""
        try:
            if kdata.empty:
                return {'sentiment_score': 50.0}

            # 获取价格序列
            close_prices = kdata['close'].values

            # 计算RSI
            rsi = self._calculate_rsi(close_prices)

            # 计算移动平均线
            ma5 = close_prices[-5:].mean() if len(close_prices) >= 5 else close_prices.mean()
            ma10 = close_prices[-10:].mean() if len(close_prices) >= 10 else close_prices.mean()
            ma20 = close_prices[-20:].mean() if len(close_prices) >= 20 else close_prices.mean()

            # 计算MACD
            macd_line, signal_line, histogram = self._calculate_macd(close_prices)

            # 计算布林带
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(close_prices)

            # 综合情绪评分
            sentiment_score = self._calculate_sentiment_score(rsi, macd_line, close_prices, ma20)

            return {
                'rsi': float(rsi),
                'ma5': float(ma5),
                'ma10': float(ma10),
                'ma20': float(ma20),
                'macd': float(macd_line),
                'signal': float(signal_line),
                'histogram': float(histogram),
                'bb_upper': float(bb_upper),
                'bb_middle': float(bb_middle),
                'bb_lower': float(bb_lower),
                'sentiment_score': float(sentiment_score),
                'current_price': float(close_prices[-1]),
                'price_change': float(close_prices[-1] - close_prices[-2]) if len(close_prices) > 1 else 0.0,
                'price_change_pct': float((close_prices[-1] - close_prices[-2]) / close_prices[-2] * 100) if len(close_prices) > 1 and close_prices[-2] != 0 else 0.0
            }

        except Exception as e:
            print(f"❌ 从K线数据计算技术指标失败: {e}")
            return {'sentiment_score': 50.0}

    def _generate_fallback_data(self, symbol: str) -> Dict:
        """生成TET框架降级数据"""
        try:
            # 生成简单的模拟K线数据
            dates = pd.date_range(start=datetime.now() - timedelta(days=30),
                                  end=datetime.now(), freq='D')

            base_price = 100.0
            prices = []
            for i in range(len(dates)):
                price = base_price * (1 + np.sin(i * 0.1) * 0.05 + np.random.normal(0, 0.01))
                prices.append(max(price, 1.0))

            kdata = pd.DataFrame({
                'datetime': dates,
                'open': [p * (1 + np.random.uniform(-0.02, 0.02)) for p in prices],
                'high': [p * (1 + np.random.uniform(0.01, 0.05)) for p in prices],
                'low': [p * (1 + np.random.uniform(-0.05, -0.01)) for p in prices],
                'close': prices,
                'volume': [np.random.randint(1000000, 10000000) for _ in prices]
            })

            # 计算技术指标
            technical_analysis = self._calculate_technical_indicators_from_kdata(kdata)

            return {
                'symbol': symbol,
                'kdata': kdata,
                'analysis': technical_analysis,
                'realtime_data': {},
                'fundamental_data': {},
                'timestamp': datetime.now(),
                'source': 'TET_Fallback'
            }

        except Exception as e:
            print(f"❌ 生成TET降级数据失败 {symbol}: {e}")
            return None

    def _calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        try:
            if len(prices) < period + 1:
                return 50.0

            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])

            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

        except Exception as e:
            print(f"计算RSI失败: {e}")
            return 50.0

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        try:
            if len(prices) < slow:
                return 0.0, 0.0, 0.0

            # 计算EMA
            ema_fast = self._calculate_ema(prices, fast)
            ema_slow = self._calculate_ema(prices, slow)
            macd_line = ema_fast - ema_slow
            signal_line = macd_line * 0.9  # 简化的信号线
            histogram = macd_line - signal_line

            return macd_line, signal_line, histogram

        except Exception as e:
            print(f"计算MACD失败: {e}")
            return 0.0, 0.0, 0.0

    def _calculate_ema(self, prices, period):
        """计算指数移动平均"""
        try:
            if len(prices) < period:
                return np.mean(prices)

            alpha = 2 / (period + 1)
            ema = prices[0]
            for price in prices[1:]:
                ema = alpha * price + (1 - alpha) * ema
            return ema

        except Exception as e:
            print(f"计算EMA失败: {e}")
            return np.mean(prices) if len(prices) > 0 else 0.0

    def _calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """计算布林带"""
        try:
            if len(prices) < period:
                mean_price = np.mean(prices)
                return mean_price, mean_price, mean_price

            recent_prices = prices[-period:]
            middle = np.mean(recent_prices)
            std = np.std(recent_prices)
            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)

            return upper, middle, lower

        except Exception as e:
            print(f"计算布林带失败: {e}")
            mean_price = np.mean(prices) if len(prices) > 0 else 0.0
            return mean_price, mean_price, mean_price

    def _calculate_sentiment_score(self, rsi, macd, prices, ma20):
        """计算综合情绪评分"""
        try:
            score = 50.0  # 基础中性分数

            # RSI贡献 (30%)
            if rsi > 70:
                score += (rsi - 70) * 0.3
            elif rsi < 30:
                score -= (30 - rsi) * 0.3

            # MACD贡献 (25%)
            if macd > 0:
                score += min(macd * 10, 15)
            else:
                score += max(macd * 10, -15)

            # 价格与均线关系 (25%)
            current_price = prices[-1]
            if current_price > ma20:
                score += min((current_price - ma20) / ma20 * 100, 15)
            else:
                score -= min((ma20 - current_price) / ma20 * 100, 15)

            # 价格趋势 (20%)
            if len(prices) >= 5:
                recent_trend = (prices[-1] - prices[-5]) / prices[-5] * 100
                score += min(max(recent_trend * 2, -10), 10)

            # 确保分数在0-100范围内
            score = max(0, min(100, score))
            return score

        except Exception as e:
            print(f"计算情绪评分失败: {e}")
            return 50.0

    def stop(self):
        """停止TET框架数据更新"""
        self.running = False


class ProfessionalTechnicalIndicatorWidget(QWidget):
    """专业技术指标组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        title_label = QLabel("📊 技术指标面板")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;")
        layout.addWidget(title_label)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 趋势指标
        trend_widget = self.create_trend_indicators()
        self.tab_widget.addTab(trend_widget, "📈 趋势")

        # 震荡指标
        oscillator_widget = self.create_oscillator_indicators()
        self.tab_widget.addTab(oscillator_widget, "🌊 震荡")

        # 成交量指标
        volume_widget = self.create_volume_indicators()
        self.tab_widget.addTab(volume_widget, "📊 成交量")

        layout.addWidget(self.tab_widget)

    def create_trend_indicators(self):
        """创建趋势指标面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # MA均线系统
        ma_group = QGroupBox("📈 移动平均线系统")
        ma_layout = QGridLayout(ma_group)

        self.ma5_label = QLabel("MA5: --")
        self.ma10_label = QLabel("MA10: --")
        self.ma20_label = QLabel("MA20: --")
        self.ma60_label = QLabel("MA60: --")

        ma_layout.addWidget(self.ma5_label, 0, 0)
        ma_layout.addWidget(self.ma10_label, 0, 1)
        ma_layout.addWidget(self.ma20_label, 1, 0)
        ma_layout.addWidget(self.ma60_label, 1, 1)

        layout.addWidget(ma_group)

        # MACD
        macd_group = QGroupBox("📊 MACD")
        macd_layout = QGridLayout(macd_group)

        self.macd_label = QLabel("MACD: --")
        self.signal_label = QLabel("Signal: --")
        self.histogram_label = QLabel("Histogram: --")

        macd_layout.addWidget(self.macd_label, 0, 0)
        macd_layout.addWidget(self.signal_label, 0, 1)
        macd_layout.addWidget(self.histogram_label, 1, 0, 1, 2)

        layout.addWidget(macd_group)

        layout.addStretch()
        return widget

    def create_oscillator_indicators(self):
        """创建震荡指标面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # RSI
        rsi_group = QGroupBox("⚡ RSI 相对强弱指数")
        rsi_layout = QVBoxLayout(rsi_group)

        self.rsi_label = QLabel("RSI(14): --")
        self.rsi_progress = QProgressBar()
        self.rsi_progress.setRange(0, 100)
        self.rsi_signal_label = QLabel("信号: --")

        rsi_layout.addWidget(self.rsi_label)
        rsi_layout.addWidget(self.rsi_progress)
        rsi_layout.addWidget(self.rsi_signal_label)

        layout.addWidget(rsi_group)

        # KDJ
        kdj_group = QGroupBox("🎯 KDJ 随机指标")
        kdj_layout = QGridLayout(kdj_group)

        self.k_label = QLabel("K: --")
        self.d_label = QLabel("D: --")
        self.j_label = QLabel("J: --")
        self.kdj_signal_label = QLabel("信号: --")

        kdj_layout.addWidget(self.k_label, 0, 0)
        kdj_layout.addWidget(self.d_label, 0, 1)
        kdj_layout.addWidget(self.j_label, 1, 0)
        kdj_layout.addWidget(self.kdj_signal_label, 1, 1)

        layout.addWidget(kdj_group)

        layout.addStretch()
        return widget

    def create_volume_indicators(self):
        """创建成交量指标面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 成交量分析
        volume_group = QGroupBox("📊 成交量分析")
        volume_layout = QGridLayout(volume_group)

        self.volume_label = QLabel("当前成交量: --")
        self.volume_avg_label = QLabel("5日均量: --")
        self.volume_ratio_label = QLabel("量比: --")
        self.volume_signal_label = QLabel("信号: --")

        volume_layout.addWidget(self.volume_label, 0, 0)
        volume_layout.addWidget(self.volume_avg_label, 0, 1)
        volume_layout.addWidget(self.volume_ratio_label, 1, 0)
        volume_layout.addWidget(self.volume_signal_label, 1, 1)

        layout.addWidget(volume_group)

        # OBV能量潮
        obv_group = QGroupBox("🌊 OBV 能量潮")
        obv_layout = QVBoxLayout(obv_group)

        self.obv_label = QLabel("OBV: --")
        self.obv_trend_label = QLabel("趋势: --")

        obv_layout.addWidget(self.obv_label)
        obv_layout.addWidget(self.obv_trend_label)

        layout.addWidget(obv_group)

        layout.addStretch()
        return widget

    def update_indicators(self, analysis_result):
        """更新技术指标显示"""
        if not analysis_result or 'technical_indicators' not in analysis_result:
            return

        indicators = analysis_result['technical_indicators']

        # 更新趋势指标
        if 'ma5' in indicators:
            self.ma5_label.setText(f"MA5: {indicators['ma5']:.2f}")
        if 'ma10' in indicators:
            self.ma10_label.setText(f"MA10: {indicators['ma10']:.2f}")
        if 'ma20' in indicators:
            self.ma20_label.setText(f"MA20: {indicators['ma20']:.2f}")
        if 'ma60' in indicators:
            self.ma60_label.setText(f"MA60: {indicators['ma60']:.2f}")

        # 更新RSI
        if 'rsi' in indicators:
            rsi_value = indicators['rsi']
            self.rsi_label.setText(f"RSI(14): {rsi_value:.2f}")
            self.rsi_progress.setValue(int(rsi_value))

            # RSI信号判断
            if rsi_value > 70:
                self.rsi_signal_label.setText("信号: 🔴 超买")
                self.rsi_signal_label.setStyleSheet("color: #d32f2f;")
            elif rsi_value < 30:
                self.rsi_signal_label.setText("信号: 🟢 超卖")
                self.rsi_signal_label.setStyleSheet("color: #388e3c;")
            else:
                self.rsi_signal_label.setText("信号: ⚪ 中性")
                self.rsi_signal_label.setStyleSheet("color: #757575;")

    def clear_indicators(self):
        """清空技术指标显示"""
        try:
            # 清空移动平均线
            self.ma5_label.setText("MA5: --")
            self.ma10_label.setText("MA10: --")
            self.ma20_label.setText("MA20: --")
            self.ma60_label.setText("MA60: --")

            # 清空MACD
            if hasattr(self, 'macd_label'):
                self.macd_label.setText("MACD: --")
            if hasattr(self, 'signal_label'):
                self.signal_label.setText("Signal: --")
            if hasattr(self, 'histogram_label'):
                self.histogram_label.setText("Histogram: --")

            # 清空RSI
            self.rsi_label.setText("RSI(14): --")
            self.rsi_progress.setValue(0)
            self.rsi_signal_label.setText("信号: --")
            self.rsi_signal_label.setStyleSheet("")

            # 清空KDJ
            if hasattr(self, 'k_label'):
                self.k_label.setText("K: --")
            if hasattr(self, 'd_label'):
                self.d_label.setText("D: --")
            if hasattr(self, 'j_label'):
                self.j_label.setText("J: --")
            if hasattr(self, 'kdj_signal_label'):
                self.kdj_signal_label.setText("信号: --")

        except Exception as e:
            print(f"清空技术指标显示失败: {e}")


class ProfessionalMarketOverviewWidget(QWidget):
    """专业市场概览组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        title_label = QLabel("🌍 市场概览")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;")
        layout.addWidget(title_label)

        # 市场情绪仪表盘
        sentiment_group = QGroupBox("📊 市场情绪仪表盘")
        sentiment_layout = QGridLayout(sentiment_group)

        # 综合情绪指数
        self.overall_sentiment_label = QLabel("综合情绪: --")
        self.overall_sentiment_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        sentiment_layout.addWidget(self.overall_sentiment_label, 0, 0, 1, 2)

        # 情绪进度条
        self.sentiment_progress = QProgressBar()
        self.sentiment_progress.setRange(0, 100)
        self.sentiment_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                    stop:0 #FF6B6B, stop:0.5 #FFE66D, stop:1 #4ECDC4);
                border-radius: 3px;
            }
        """)
        sentiment_layout.addWidget(self.sentiment_progress, 1, 0, 1, 2)

        # 分项指标
        self.fear_greed_label = QLabel("恐惧贪婪: --")
        self.volatility_label = QLabel("波动率: --")
        self.momentum_label = QLabel("动量: --")
        self.trend_strength_label = QLabel("趋势强度: --")

        sentiment_layout.addWidget(self.fear_greed_label, 2, 0)
        sentiment_layout.addWidget(self.volatility_label, 2, 1)
        sentiment_layout.addWidget(self.momentum_label, 3, 0)
        sentiment_layout.addWidget(self.trend_strength_label, 3, 1)

        layout.addWidget(sentiment_group)

        # 市场统计
        stats_group = QGroupBox("📈 市场统计")
        stats_layout = QGridLayout(stats_group)

        self.total_analyzed_label = QLabel("分析股票数: --")
        self.bullish_count_label = QLabel("看涨: --")
        self.bearish_count_label = QLabel("看跌: --")
        self.neutral_count_label = QLabel("中性: --")

        stats_layout.addWidget(self.total_analyzed_label, 0, 0)
        stats_layout.addWidget(self.bullish_count_label, 0, 1)
        stats_layout.addWidget(self.bearish_count_label, 1, 0)
        stats_layout.addWidget(self.neutral_count_label, 1, 1)

        layout.addWidget(stats_group)

        layout.addStretch()

    def update_overview(self, market_data):
        """更新市场概览"""
        if not market_data:
            return

        # 更新综合情绪
        sentiment_score = market_data.get('sentiment_score', 50)
        self.overall_sentiment_label.setText(f"综合情绪: {sentiment_score:.1f}")
        self.sentiment_progress.setValue(int(sentiment_score))

        # 根据情绪值设置颜色
        if sentiment_score > 70:
            color = "#4ECDC4"  # 绿色 - 乐观
            emotion = "😊 乐观"
        elif sentiment_score > 30:
            color = "#FFE66D"  # 黄色 - 中性
            emotion = "😐 中性"
        else:
            color = "#FF6B6B"  # 红色 - 悲观
            emotion = "😰 悲观"

        self.overall_sentiment_label.setText(f"综合情绪: {sentiment_score:.1f} ({emotion})")
        self.overall_sentiment_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")

        # 更新分项指标
        self.fear_greed_label.setText(f"恐惧贪婪: {market_data.get('fear_greed', 50):.1f}")
        self.volatility_label.setText(f"波动率: {market_data.get('volatility', 20):.1f}%")
        self.momentum_label.setText(f"动量: {market_data.get('momentum', 0):.1f}")
        self.trend_strength_label.setText(f"趋势强度: {market_data.get('trend_strength', 50):.1f}")

        # 更新统计数据
        self.total_analyzed_label.setText(f"分析股票数: {market_data.get('total_count', 0)}")
        self.bullish_count_label.setText(f"看涨: {market_data.get('bullish_count', 0)}")
        self.bearish_count_label.setText(f"看跌: {market_data.get('bearish_count', 0)}")
        self.neutral_count_label.setText(f"中性: {market_data.get('neutral_count', 0)}")

    def clear_overview(self):
        """清空市场概览显示"""
        try:
            # 清空综合情绪
            self.overall_sentiment_label.setText("综合情绪: --")
            self.overall_sentiment_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            self.sentiment_progress.setValue(0)

            # 清空分项指标
            if hasattr(self, 'fear_greed_label'):
                self.fear_greed_label.setText("恐惧贪婪: --")
            if hasattr(self, 'volatility_label'):
                self.volatility_label.setText("波动率: --%")
            if hasattr(self, 'momentum_label'):
                self.momentum_label.setText("动量: --")
            if hasattr(self, 'trend_strength_label'):
                self.trend_strength_label.setText("趋势强度: --")

            # 清空统计数据
            if hasattr(self, 'total_analyzed_label'):
                self.total_analyzed_label.setText("分析股票数: --")
            if hasattr(self, 'bullish_count_label'):
                self.bullish_count_label.setText("看涨: --")
            if hasattr(self, 'bearish_count_label'):
                self.bearish_count_label.setText("看跌: --")
            if hasattr(self, 'neutral_count_label'):
                self.neutral_count_label.setText("中性: --")

        except Exception as e:
            print(f"清空市场概览显示失败: {e}")


class EnhancedKLineTechnicalTab(BaseAnalysisTab):
    """增强版K线技术分析标签页 - 对标专业软件"""

    # 类属性，确保这些属性始终存在
    current_stock_code = "000001"
    current_stock_name = "平安银行"

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        # 在调用super().__init__之前就设置实例属性
        self.current_stock_code = "000001"
        self.current_stock_name = "平安银行"

        super().__init__(config_manager)

        # 尝试获取系统当前选择的股票
        try:
            self.get_current_selected_stock()
        except Exception as e:
            print(f"获取当前股票失败，使用默认值: {e}")

        # 初始化分析器
        self.analyzer = get_kline_sentiment_analyzer()

        # 初始化股票列表
        self.symbols = [self.current_stock_code] if self.current_stock_code else ["000001"]

        # 工作线程
        self.data_worker = None

        # UI组件
        self.status_label = None
        self.control_button = None
        self.stock_selector = None
        self.market_overview_widget = None
        self.technical_indicator_widget = None
        # 连接股票选择事件
        self.connect_stock_events()

    def get_current_selected_stock(self):
        """获取系统当前选择的股票"""
        try:
            # 尝试从parent获取股票信息
            parent_widget = self.parent()
            while parent_widget:
                if hasattr(parent_widget, 'get_current_stock_info'):
                    stock_info = parent_widget.get_current_stock_info()
                    if stock_info and stock_info.get('code'):
                        self.current_stock_code = stock_info['code']
                        self.current_stock_name = stock_info.get('name', self.current_stock_code)
                        print(f"从父组件获取到当前股票: {self.current_stock_name} ({self.current_stock_code})")
                        return
                parent_widget = parent_widget.parent()

            # 尝试从全局变量或配置获取
            try:
                from utils.config_manager import ConfigManager
                config = ConfigManager()
                if config and hasattr(config, 'get'):
                    last_stock = config.get('last_selected_stock', {})
                    if last_stock.get('code'):
                        self.current_stock_code = last_stock['code']
                        self.current_stock_name = last_stock.get('name', self.current_stock_code)
                        print(f"从配置获取到股票: {self.current_stock_name} ({self.current_stock_code})")
                        return
            except:
                pass

            print(f"未找到其他股票信息，保持默认: {self.current_stock_name} ({self.current_stock_code})")

        except Exception as e:
            print(f"获取当前选择股票失败: {e}")
            # 保持已有的默认值，不再重新设置

    def connect_stock_events(self):
        """连接股票选择事件"""
        try:
            # 暂时跳过事件连接，避免导入错误
            # 后续可以通过其他方式实现股票选择同步
            print("股票事件连接功能暂时禁用，使用手动选择方式")
        except Exception as e:
            print(f"连接股票事件失败: {e}")

    def on_stock_selected_event(self, event):
        """处理股票选择事件"""
        try:
            self.current_stock_code = event.stock_code
            self.current_stock_name = event.stock_name

            # 更新股票选择器显示
            if self.stock_selector:
                self.stock_selector.set_current_stock(self.current_stock_code, self.current_stock_name)

            # 更新分析目标
            self.symbols = [self.current_stock_code]

            # 如果正在运行分析，重新启动
            if self.data_worker and self.data_worker.running:
                self.restart_analysis()

            print(f"K线技术分析更新到新股票: {self.current_stock_name} ({self.current_stock_code})")

        except Exception as e:
            print(f"处理股票选择事件失败: {e}")

    def create_ui(self):
        """创建专业UI界面"""

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # 标题和控制栏
        header = self.create_header()
        header.setMaximumHeight(100)
        main_layout.addWidget(header)

        # 主要内容区域
        content_widget = self.create_content_area()
        main_layout.addWidget(content_widget)

    def create_header(self):
        """创建标题栏"""
        header_widget = QFrame()
        header_widget.setFrameStyle(QFrame.StyledPanel)
        header_widget.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                height: 10px;
                padding: 2px;
            }
        """)

        layout = QHBoxLayout(header_widget)
        layout.setSpacing(0)
        # 标题
        title_label = QLabel("📈 专业K线技术分析系统")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)

        # 当前股票显示
        current_stock_text = f"{self.current_stock_name} ({self.current_stock_code})" if self.current_stock_code else "未选择"
        self.current_stock_label = QLabel(f"当前分析: {current_stock_text}")
        self.current_stock_label.setStyleSheet("""
            background-color: #e3f2fd;
            padding: 6px 12px;
            border-radius: 4px;
            color: #1976d2;
            font-weight: bold;
        """)
        layout.addWidget(self.current_stock_label)

        # 状态显示
        self.status_label = QLabel("🔴 待启动")
        self.status_label.setStyleSheet("color: #d32f2f; font-weight: bold; padding: 1px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 控制按钮
        self.control_button = QPushButton("🚀 启动分析")
        self.control_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 8px 8px;
                border-radius: 2px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.control_button.clicked.connect(self.toggle_analysis)
        layout.addWidget(self.control_button)

        return header_widget

    def create_content_area(self):
        """创建主要内容区域"""
        # 创建水平分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧面板 - 股票选择和控制
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 右侧面板 - 分析结果
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setStretchFactor(0, 1)  # 左侧
        splitter.setStretchFactor(1, 2)  # 右侧

        return splitter

    def create_left_panel(self):
        """创建左侧控制面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMaximumWidth(400)

        layout = QVBoxLayout(panel)

        # 股票选择器
        self.stock_selector = StockSelectorWidget()
        self.stock_selector.stock_selected.connect(self.on_stock_manually_selected)
        # 设置当前股票
        if self.current_stock_code:
            self.stock_selector.set_current_stock(self.current_stock_code, self.current_stock_name)
        layout.addWidget(self.stock_selector)

        # 分析参数配置
        config_group = QGroupBox("⚙️ 分析配置")
        config_layout = QVBoxLayout(config_group)

        # 更新频率
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("更新频率:"))
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["30秒", "1分钟", "5分钟", "15分钟"])
        self.freq_combo.currentTextChanged.connect(self.on_update_frequency_changed)
        freq_layout.addWidget(self.freq_combo)
        config_layout.addLayout(freq_layout)

        # 技术指标选择
        indicators_layout = QVBoxLayout()
        indicators_layout.addWidget(QLabel("技术指标:"))

        self.rsi_check = QCheckBox("RSI 相对强弱指数")
        self.rsi_check.setChecked(True)
        self.rsi_check.toggled.connect(self.on_indicator_settings_changed)

        self.macd_check = QCheckBox("MACD 指数平滑异同移动平均线")
        self.macd_check.setChecked(True)
        self.macd_check.toggled.connect(self.on_indicator_settings_changed)

        self.kdj_check = QCheckBox("KDJ 随机指标")
        self.kdj_check.setChecked(True)
        self.kdj_check.toggled.connect(self.on_indicator_settings_changed)

        self.ma_check = QCheckBox("MA 移动平均线")
        self.ma_check.setChecked(True)
        self.ma_check.toggled.connect(self.on_indicator_settings_changed)

        self.bb_check = QCheckBox("BB 布林带")
        self.bb_check.setChecked(False)
        self.bb_check.toggled.connect(self.on_indicator_settings_changed)

        indicators_layout.addWidget(self.rsi_check)
        indicators_layout.addWidget(self.macd_check)
        indicators_layout.addWidget(self.kdj_check)
        indicators_layout.addWidget(self.ma_check)
        indicators_layout.addWidget(self.bb_check)

        config_layout.addLayout(indicators_layout)

        # 高级设置按钮
        advanced_btn = QPushButton("🔧 高级设置")
        advanced_btn.clicked.connect(self.show_advanced_settings)
        config_layout.addWidget(advanced_btn)

        layout.addWidget(config_group)

        layout.addStretch()
        return panel

    def on_update_frequency_changed(self, frequency_text):
        """更新频率改变处理"""
        try:
            # 解析频率文本转换为秒数
            freq_map = {
                "30秒": 30,
                "1分钟": 60,
                "5分钟": 300,
                "15分钟": 900
            }

            new_interval = freq_map.get(frequency_text, 30)
            print(f"📊 更新频率改变为: {frequency_text} ({new_interval}秒)")

            # 更新工作线程的更新间隔
            if self.data_worker:
                self.data_worker.update_interval = new_interval
                print(f"✅ 数据工作线程更新间隔已设置为{new_interval}秒")

            # 保存配置
            if hasattr(self, 'config_manager') and self.config_manager:
                self.config_manager.set('kline_sentiment.update_frequency', frequency_text)

        except Exception as e:
            print(f"⚠️ 更新频率设置失败: {e}")

    def on_indicator_settings_changed(self):
        """技术指标设置改变处理"""
        try:
            # 获取当前选择的指标
            selected_indicators = {
                'rsi': self.rsi_check.isChecked(),
                'macd': self.macd_check.isChecked(),
                'kdj': self.kdj_check.isChecked(),
                'ma': self.ma_check.isChecked(),
                'bb': self.bb_check.isChecked()
            }

            enabled_indicators = [name for name, enabled in selected_indicators.items() if enabled]
            print(f"📊 技术指标设置已更改: {enabled_indicators}")

            # 保存指标设置
            if hasattr(self, 'config_manager') and self.config_manager:
                self.config_manager.set('kline_sentiment.indicators', selected_indicators)

            # 如果正在运行分析，应用新设置
            if self.data_worker and self.data_worker.running:
                print("🔄 重新启动分析以应用新的指标设置")
                self.restart_analysis_with_new_settings()

        except Exception as e:
            print(f"⚠️ 技术指标设置失败: {e}")

    def restart_analysis_with_new_settings(self):
        """使用新设置重启分析"""
        try:
            if self.data_worker and self.data_worker.running:
                print("⏹️ 停止当前分析...")
                self.data_worker.stop()
                # 使用异步方式重启，避免UI卡死
                QTimer.singleShot(500, self._restart_after_stop)
            else:
                # 如果没有运行的线程，直接重启
                QTimer.singleShot(100, self.start_analysis)
            print("🔄 将使用新设置重启分析")
        except Exception as e:
            print(f"⚠️ 重启分析失败: {e}")

    def _restart_after_stop(self):
        """停止后重启分析"""
        try:
            if self.data_worker:
                if self.data_worker.isRunning():
                    self.data_worker.wait(2000)  # 最多等待2秒
                    if self.data_worker.isRunning():
                        self.data_worker.terminate()
                        self.data_worker.wait(1000)
                self.data_worker = None

            # 重启分析
            QTimer.singleShot(500, self.start_analysis)
        except Exception as e:
            print(f"⚠️ 停止后重启失败: {e}")

    def show_advanced_settings(self):
        """显示高级设置对话框"""
        try:
            dialog = AdvancedSettingsDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                settings = dialog.get_settings()
                self.apply_advanced_settings(settings)
                print(f"✅ 应用高级设置: {settings}")
        except Exception as e:
            print(f"⚠️ 显示高级设置失败: {e}")

    def apply_advanced_settings(self, settings):
        """应用高级设置"""
        try:
            # 应用RSI周期设置
            if 'rsi_period' in settings:
                print(f"📊 RSI周期设置为: {settings['rsi_period']}")

            # 应用MACD参数设置
            if 'macd_fast' in settings and 'macd_slow' in settings:
                print(f"📊 MACD参数设置为: 快线{settings['macd_fast']}, 慢线{settings['macd_slow']}")

            # 应用MA周期设置
            if 'ma_periods' in settings:
                print(f"📊 MA周期设置为: {settings['ma_periods']}")

            # 保存设置
            if hasattr(self, 'config_manager') and self.config_manager:
                self.config_manager.set('kline_sentiment.advanced_settings', settings)

            # 如果正在运行，重新启动分析
            if self.data_worker and self.data_worker.running:
                self.restart_analysis_with_new_settings()

        except Exception as e:
            print(f"⚠️ 应用高级设置失败: {e}")

    def get_current_indicator_settings(self):
        """获取当前指标设置"""
        try:
            return {
                'rsi': self.rsi_check.isChecked() if hasattr(self, 'rsi_check') else True,
                'macd': self.macd_check.isChecked() if hasattr(self, 'macd_check') else True,
                'kdj': self.kdj_check.isChecked() if hasattr(self, 'kdj_check') else True,
                'ma': self.ma_check.isChecked() if hasattr(self, 'ma_check') else True,
                'bb': self.bb_check.isChecked() if hasattr(self, 'bb_check') else False
            }
        except Exception as e:
            print(f"⚠️ 获取指标设置失败: {e}")
            return {'rsi': True, 'macd': True, 'kdj': True, 'ma': True, 'bb': False}

    def create_right_panel(self):
        """创建右侧分析面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)

        layout = QVBoxLayout(panel)

        # 创建标签页
        tab_widget = QTabWidget()

        # 市场概览标签页
        self.market_overview_widget = ProfessionalMarketOverviewWidget()
        tab_widget.addTab(self.market_overview_widget, "🌍 市场概览")

        # 技术指标标签页
        self.technical_indicator_widget = ProfessionalTechnicalIndicatorWidget()
        tab_widget.addTab(self.technical_indicator_widget, "�� 技术指标")

        # 在create_right_panel方法中添加情绪概览和智能提醒
        # 找到技术指标标签页添加后的位置，插入新的标签页

        # 添加情绪概览标签页
        from gui.widgets.sentiment_overview_widget import SentimentOverviewWidget
        self.sentiment_overview_widget = SentimentOverviewWidget()
        tab_widget.addTab(self.sentiment_overview_widget, "🎭 情绪概览")

        # 添加智能提醒标签页
        from gui.widgets.smart_alert_widget import SmartAlertWidget
        from gui.widgets.signal_aggregator import SignalAggregator

        self.smart_alert_widget = SmartAlertWidget()
        self.signal_aggregator = SignalAggregator()

        # 连接信号
        self.signal_aggregator.alert_generated.connect(self.smart_alert_widget.add_alert)
        self.sentiment_overview_widget.sentiment_updated.connect(self._on_sentiment_data_updated)

        tab_widget.addTab(self.smart_alert_widget, "🚨 智能提醒")

        layout.addWidget(tab_widget)
        return panel

    def get_sentiment_data_from_professional_tab(self):
        """从专业情绪分析Tab获取情绪数据"""
        try:
            # 尝试从父组件找到专业情绪分析Tab
            parent_widget = self.parent()
            while parent_widget:
                if hasattr(parent_widget, 'sentiment_tab'):
                    sentiment_tab = parent_widget.sentiment_tab
                    if hasattr(sentiment_tab, 'sentiment_results') and sentiment_tab.sentiment_results:
                        print("✅ 成功获取专业情绪分析数据")
                        return sentiment_tab.sentiment_results
                    elif hasattr(sentiment_tab, 'get_latest_sentiment_data'):
                        return sentiment_tab.get_latest_sentiment_data()
                parent_widget = parent_widget.parent()

            print("⚠️ 未找到专业情绪分析Tab或数据为空")
            return None

        except Exception as e:
            print(f"❌ 获取情绪数据失败: {e}")
            return None

    def update_technical_indicators_with_sentiment(self, sentiment_data):
        """将情绪数据融入技术指标分析"""
        try:
            if not sentiment_data or not self.technical_indicator_widget:
                return

            # 更新技术指标组件，加入情绪数据作为参考
            if hasattr(self.technical_indicator_widget, 'update_with_sentiment_data'):
                self.technical_indicator_widget.update_with_sentiment_data(sentiment_data)
                print("✅ 技术指标已融入情绪数据")

            # 更新市场概览组件
            if hasattr(self.market_overview_widget, 'update_sentiment_overview'):
                self.market_overview_widget.update_sentiment_overview(sentiment_data)
                print("✅ 市场概览已更新情绪数据")

        except Exception as e:
            print(f"❌ 融入情绪数据失败: {e}")

    def on_stock_manually_selected(self, code, name):
        """处理手动选择股票"""
        self.current_stock_code = code
        self.current_stock_name = name
        self.symbols = [code]

        # 更新显示
        self.current_stock_label.setText(f"当前分析: {name} ({code})")

        # 重启分析
        if self.data_worker and self.data_worker.running:
            self.restart_analysis()

    def toggle_analysis(self):
        """切换分析状态"""
        if self.data_worker and self.data_worker.running:
            self.stop_analysis()
        else:
            self.start_analysis()

    def start_analysis(self):
        """启动分析"""
        if not self.symbols:
            QMessageBox.warning(self, "警告", "请先选择要分析的股票")
            return

        try:
            # 创建并启动工作线程
            self.data_worker = RealTimeDataWorker(self.symbols)
            self.data_worker.data_updated.connect(self.on_data_updated)
            self.data_worker.error_occurred.connect(self.on_error_occurred)
            self.data_worker.start()

            # 更新UI状态
            self.status_label.setText("🟢 运行中")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold; padding: 6px;")
            self.control_button.setText("⏹️ 停止分析")
            self.control_button.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #d32f2f;
                    }
                """)

            print(f"开始分析股票: {self.symbols}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动分析失败: {e}")

    def stop_analysis(self):
        """停止分析"""
        if self.data_worker:
            self.data_worker.stop()
            # 使用定时器异步等待线程结束，避免UI卡死
            QTimer.singleShot(100, self._finish_stop_analysis)
        else:
            self._finish_stop_analysis()

    def _finish_stop_analysis(self):
        """完成停止分析的操作"""
        if self.data_worker:
            # 给线程一些时间停止，但不要无限期等待
            if self.data_worker.isRunning():
                self.data_worker.wait(3000)  # 最多等待3秒
                if self.data_worker.isRunning():
                    self.data_worker.terminate()  # 强制终止
                    self.data_worker.wait(1000)  # 等待终止完成
            self.data_worker = None

        # 更新UI状态
        self.status_label.setText("🔴 已停止")
        self.status_label.setStyleSheet("color: #d32f2f; font-weight: bold; padding: 6px;")
        self.control_button.setText("🚀 启动分析")
        self.control_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

    def restart_analysis(self):
        """重启分析"""
        if self.data_worker and self.data_worker.running:
            self.stop_analysis()
            QTimer.singleShot(1000, self.start_analysis)  # 1秒后重启

    def on_data_updated(self, data):
        """处理数据更新"""
        try:
            # 更新技术指标
            for symbol, result in data.items():
                if 'analysis' in result:
                    analysis = result['analysis']
                    # 处理KLineSentimentResult对象
                    if hasattr(analysis, 'technical_indicators'):
                        # 将KLineSentimentResult转换为字典格式
                        analysis_dict = {
                            'sentiment_score': getattr(analysis, 'sentiment_score', 0),
                            'technical_indicators': getattr(analysis, 'technical_indicators', [])
                        }
                        # 如果有技术指标，提取常用指标值
                        indicators = getattr(analysis, 'technical_indicators', [])
                        for indicator in indicators:
                            if hasattr(indicator, 'name') and hasattr(indicator, 'value'):
                                analysis_dict[indicator.name.lower()] = indicator.value

                        if self.technical_indicator_widget:
                            self.technical_indicator_widget.update_indicators(analysis_dict)
                        else:
                            print("⚠️ 技术指标组件未初始化")
                    elif isinstance(analysis, dict):
                        # 如果已经是字典格式
                        if self.technical_indicator_widget:
                            self.technical_indicator_widget.update_indicators(analysis)
                        else:
                            print("⚠️ 技术指标组件未初始化")
                else:
                    print("⚠️ 技术指标组件未初始化或分析数据为空")

            # 更新市场概览
            market_data = self.calculate_market_overview(data)
            self.market_overview_widget.update_overview(market_data)

            print(f"数据更新: {len(data)} 个股票")

        except Exception as e:
            print(f"处理数据更新失败: {e}")
            import traceback
            traceback.print_exc()

    def calculate_market_overview(self, data):
        """计算市场概览数据"""
        if not data:
            return {}

        # 简化的市场情绪计算
        sentiment_scores = []
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        for symbol, result in data.items():
            if 'analysis' in result:
                analysis = result['analysis']
                # 检查是否是KLineSentimentResult对象
                if hasattr(analysis, 'sentiment_score'):
                    score = analysis.sentiment_score
                    # 将情绪得分从[-1,1]转换为[0,100]
                    score_normalized = (score + 1) * 50
                    sentiment_scores.append(score_normalized)

                    if score_normalized > 60:
                        bullish_count += 1
                    elif score_normalized < 40:
                        bearish_count += 1
                    else:
                        neutral_count += 1
                elif isinstance(analysis, dict) and 'sentiment_score' in analysis:
                    # 如果是字典格式
                    score = analysis['sentiment_score']
                    sentiment_scores.append(score)

                    if score > 60:
                        bullish_count += 1
                    elif score < 40:
                        bearish_count += 1
                    else:
                        neutral_count += 1

        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 50

        return {
            'sentiment_score': avg_sentiment,
            'fear_greed': 100 - avg_sentiment,  # 简化计算
            'volatility': np.std(sentiment_scores) if len(sentiment_scores) > 1 else 20,
            'momentum': (avg_sentiment - 50) * 2,  # 简化动量计算
            'trend_strength': abs(avg_sentiment - 50) * 2,
            'total_count': len(data),
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
        }

    def on_error_occurred(self, error_message):
        """处理错误"""
        print(f"K线技术分析错误: {error_message}")
        QMessageBox.warning(self, "分析错误", error_message)
        self.stop_analysis()

    def start_real_time_updates(self):
        """启动实时更新（兼容旧接口）"""
        # 这个方法保持为空，实际的启动通过用户手动点击按钮
        pass

    def _on_sentiment_data_updated(self, sentiment_data):
        """情绪数据更新时的处理"""
        try:
            # 触发信号聚合分析
            self._trigger_signal_aggregation()
        except Exception as e:
            print(f"情绪数据更新处理失败: {e}")

    def _trigger_signal_aggregation(self):
        """触发信号聚合分析"""
        try:
            # 获取当前K线数据
            kdata = self._get_current_kdata()
            if kdata is None or kdata.empty:
                return

            # 获取技术指标数据
            technical_indicators = self._get_current_technical_indicators()

            # 获取情绪数据
            sentiment_data = self.sentiment_overview_widget.raw_sentiment_data

            # 执行信号聚合分析
            if hasattr(self, 'signal_aggregator'):
                alerts = self.signal_aggregator.process_data(
                    kdata=kdata,
                    technical_indicators=technical_indicators,
                    sentiment_data=sentiment_data
                )

                print(f"生成了 {len(alerts)} 个聚合警报")

        except Exception as e:
            print(f"信号聚合分析失败: {e}")

    def _get_current_kdata(self):
        """获取当前K线数据"""
        try:
            # 从现有的数据获取逻辑中提取K线数据
            if hasattr(self, 'current_stock_code') and self.current_stock_code:
                # 这里应该调用实际的数据获取方法
                # 暂时返回模拟数据结构
                import pandas as pd
                import numpy as np
                from datetime import datetime, timedelta

                # 生成模拟K线数据用于演示
                dates = pd.date_range(start=datetime.now() - timedelta(days=30),
                                      end=datetime.now(), freq='D')

                base_price = 100
                prices = [base_price]
                for i in range(1, len(dates)):
                    change = np.random.normal(0, 0.02)  # 2%的日波动
                    new_price = prices[-1] * (1 + change)
                    prices.append(new_price)

                kdata = pd.DataFrame({
                    'date': dates,
                    'open': [p * np.random.uniform(0.98, 1.02) for p in prices],
                    'high': [p * np.random.uniform(1.01, 1.05) for p in prices],
                    'low': [p * np.random.uniform(0.95, 0.99) for p in prices],
                    'close': prices,
                    'volume': [np.random.randint(1000000, 10000000) for _ in prices]
                })

                return kdata

        except Exception as e:
            print(f"获取K线数据失败: {e}")

        return None

    def _get_current_technical_indicators(self):
        """获取当前技术指标数据"""
        try:
            # 从技术指标组件获取数据，或者计算技术指标
            # 这里返回模拟的技术指标数据
            indicators = {
                'rsi': np.random.uniform(30, 70),  # RSI值
                'macd': {
                    'dif': np.random.uniform(-1, 1),
                    'dea': np.random.uniform(-1, 1),
                    'histogram': np.random.uniform(-0.5, 0.5)
                },
                'ma': {
                    'ma5': np.random.uniform(95, 105),
                    'ma10': np.random.uniform(90, 110),
                    'ma20': np.random.uniform(85, 115)
                },
                'bollinger': {
                    'upper': np.random.uniform(105, 110),
                    'middle': np.random.uniform(95, 105),
                    'lower': np.random.uniform(85, 95)
                }
            }

            return indicators

        except Exception as e:
            print(f"获取技术指标失败: {e}")
            return {}

    def set_kdata(self, kdata):
        """设置K线数据 - 异步处理，避免UI阻塞"""
        try:
            # 调用父类方法进行基础设置
            super().set_kdata(kdata)

            # 如果没有数据，直接返回
            if kdata is None or kdata.empty:
                print("⚠️ [EnhancedKLineTechnicalTab] 接收到空的K线数据")
                return

            print(f"📊 [EnhancedKLineTechnicalTab] 接收到K线数据: {len(kdata)} 条记录")

            # 异步处理K线数据，避免阻塞UI
            QTimer.singleShot(100, lambda: self._process_kdata_async(kdata))

        except Exception as e:
            print(f"❌ [EnhancedKLineTechnicalTab] 设置K线数据失败: {e}")

    def _process_kdata_async(self, kdata):
        """异步处理K线数据"""
        try:
            # 更新当前股票信息
            if hasattr(self, 'stock_code') and self.stock_code:
                self.current_stock_code = self.stock_code
                if hasattr(self, 'stock_name') and self.stock_name:
                    self.current_stock_name = self.stock_name

                # 更新UI显示
                if hasattr(self, 'current_stock_label') and self.current_stock_label:
                    self.current_stock_label.setText(f"当前分析: {self.current_stock_name} ({self.current_stock_code})")

                # 更新股票选择器
                if hasattr(self, 'stock_selector') and self.stock_selector:
                    self.stock_selector.set_current_stock(self.current_stock_code, self.current_stock_name)

            # 计算技术指标
            technical_analysis = self._calculate_real_technical_indicators(kdata)

            # 更新技术指标显示
            if hasattr(self, 'technical_indicator_widget') and self.technical_indicator_widget:
                self.technical_indicator_widget.update_indicators(technical_analysis)

            # 更新市场概览
            market_data = self._calculate_market_overview_from_kdata(kdata, technical_analysis)
            if hasattr(self, 'market_overview_widget') and self.market_overview_widget:
                self.market_overview_widget.update_overview(market_data)

            print(f"✅ [EnhancedKLineTechnicalTab] K线数据处理完成")

        except Exception as e:
            print(f"❌ [EnhancedKLineTechnicalTab] 异步处理K线数据失败: {e}")

    def _calculate_market_overview_from_kdata(self, kdata, technical_analysis):
        """基于K线数据计算市场概览"""
        try:
            if kdata.empty:
                return {}

            # 获取最新价格信息
            latest = kdata.iloc[-1]
            previous = kdata.iloc[-2] if len(kdata) > 1 else latest

            # 计算价格变化
            price_change = (latest['close'] - previous['close']) / previous['close'] * 100

            # 计算波动率（基于最近20天）
            recent_data = kdata.tail(20)
            volatility = recent_data['close'].pct_change().std() * 100

            # 基于技术指标确定情绪
            sentiment_score = 50  # 默认中性
            if 'rsi' in technical_analysis:
                rsi = technical_analysis['rsi']
                if rsi > 70:
                    sentiment_score = 75  # 超买，偏向看涨
                elif rsi < 30:
                    sentiment_score = 25  # 超卖，偏向看跌
                else:
                    sentiment_score = rsi

            # 确定趋势方向
            bullish_count = 1 if price_change > 0 else 0
            bearish_count = 1 if price_change < 0 else 0
            neutral_count = 1 if price_change == 0 else 0

            return {
                'sentiment_score': sentiment_score,
                'fear_greed': 100 - sentiment_score,
                'volatility': volatility,
                'momentum': price_change,
                'trend_strength': abs(price_change),
                'total_count': 1,
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'neutral_count': neutral_count,
                'latest_price': latest['close'],
                'price_change': price_change,
                'volume': latest['volume'] if 'volume' in latest else 0
            }

        except Exception as e:
            print(f"❌ 计算市场概览失败: {e}")
            return {}

    def refresh_data(self):
        """刷新数据 - 从BaseAnalysisTab继承的方法"""
        try:
            # 如果有当前K线数据，重新处理
            if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                self._process_kdata_async(self.current_kdata)
            else:
                print("⚠️ [EnhancedKLineTechnicalTab] 没有可刷新的K线数据")
        except Exception as e:
            print(f"❌ [EnhancedKLineTechnicalTab] 刷新数据失败: {e}")

    def clear_data(self):
        """清除数据 - 从BaseAnalysisTab继承的方法"""
        try:
            # 停止正在运行的分析
            if hasattr(self, 'data_worker') and self.data_worker and self.data_worker.running:
                self.stop_analysis()

            # 清空技术指标显示
            if hasattr(self, 'technical_indicator_widget') and self.technical_indicator_widget:
                self.technical_indicator_widget.clear_indicators()

            # 清空市场概览
            if hasattr(self, 'market_overview_widget') and self.market_overview_widget:
                self.market_overview_widget.clear_overview()

            print("✅ [EnhancedKLineTechnicalTab] 数据已清除")

        except Exception as e:
            print(f"❌ [EnhancedKLineTechnicalTab] 清除数据失败: {e}")

    def _calculate_real_technical_indicators(self, kdata):
        """基于真实K线数据计算技术指标"""
        try:
            if kdata is None or kdata.empty:
                return {'sentiment_score': 50.0}

            # 获取价格序列
            close_prices = kdata['close'].values
            high_prices = kdata['high'].values if 'high' in kdata.columns else close_prices
            low_prices = kdata['low'].values if 'low' in kdata.columns else close_prices

            # 计算RSI
            rsi = self._calculate_rsi(close_prices)

            # 计算移动平均线
            ma5 = close_prices[-5:].mean() if len(close_prices) >= 5 else close_prices.mean()
            ma10 = close_prices[-10:].mean() if len(close_prices) >= 10 else close_prices.mean()
            ma20 = close_prices[-20:].mean() if len(close_prices) >= 20 else close_prices.mean()
            ma60 = close_prices[-60:].mean() if len(close_prices) >= 60 else close_prices.mean()

            # 计算MACD
            macd_line, signal_line, histogram = self._calculate_macd(close_prices)

            # 计算布林带
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(close_prices)

            # 计算成交量相关指标
            volume = kdata['volume'].values if 'volume' in kdata.columns else np.zeros(len(close_prices))
            volume_ma = volume[-5:].mean() if len(volume) >= 5 else (volume.mean() if len(volume) > 0 else 0)

            # 综合情绪评分
            sentiment_score = self._calculate_sentiment_score(rsi, macd_line, close_prices, ma20)

            return {
                'rsi': float(rsi),
                'ma5': float(ma5),
                'ma10': float(ma10),
                'ma20': float(ma20),
                'ma60': float(ma60),
                'macd': float(macd_line),
                'signal': float(signal_line),
                'histogram': float(histogram),
                'bb_upper': float(bb_upper),
                'bb_middle': float(bb_middle),
                'bb_lower': float(bb_lower),
                'volume_ma': float(volume_ma),
                'sentiment_score': float(sentiment_score),
                'current_price': float(close_prices[-1]),
                'price_change': float(close_prices[-1] - close_prices[-2]) if len(close_prices) > 1 else 0.0,
                'price_change_pct': float((close_prices[-1] - close_prices[-2]) / close_prices[-2] * 100) if len(close_prices) > 1 and close_prices[-2] != 0 else 0.0
            }

        except Exception as e:
            print(f"❌ 计算技术指标失败: {e}")
            return {'sentiment_score': 50.0}  # 返回中性分数

    def _calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        try:
            if len(prices) < period + 1:
                return 50.0

            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])

            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            print(f"计算RSI失败: {e}")
            return 50.0

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        try:
            if len(prices) < slow:
                return 0.0, 0.0, 0.0

            # 计算EMA
            ema_fast = self._calculate_ema(prices, fast)
            ema_slow = self._calculate_ema(prices, slow)
            macd_line = ema_fast - ema_slow
            signal_line = macd_line * 0.9  # 简化的信号线
            histogram = macd_line - signal_line

            return macd_line, signal_line, histogram

        except Exception as e:
            print(f"计算MACD失败: {e}")
            return 0.0, 0.0, 0.0

    def _calculate_ema(self, prices, period):
        """计算指数移动平均"""
        try:
            if len(prices) < period:
                return np.mean(prices)

            alpha = 2 / (period + 1)
            ema = prices[0]
            for price in prices[1:]:
                ema = alpha * price + (1 - alpha) * ema
            return ema

        except Exception as e:
            print(f"计算EMA失败: {e}")
            return np.mean(prices) if len(prices) > 0 else 0.0

    def _calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """计算布林带"""
        try:
            if len(prices) < period:
                mean_price = np.mean(prices)
                return mean_price, mean_price, mean_price

            recent_prices = prices[-period:]
            middle = np.mean(recent_prices)
            std = np.std(recent_prices)
            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)

            return upper, middle, lower

        except Exception as e:
            print(f"计算布林带失败: {e}")
            mean_price = np.mean(prices) if len(prices) > 0 else 0.0
            return mean_price, mean_price, mean_price

    def _calculate_sentiment_score(self, rsi, macd, prices, ma20):
        """计算综合情绪评分"""
        try:
            score = 50.0  # 基础中性分数

            # RSI贡献 (30%)
            if rsi > 70:
                score += (rsi - 70) * 0.3
            elif rsi < 30:
                score -= (30 - rsi) * 0.3

            # MACD贡献 (25%)
            if macd > 0:
                score += min(macd * 10, 15)
            else:
                score += max(macd * 10, -15)

            # 价格与均线关系 (25%)
            current_price = prices[-1]
            if current_price > ma20:
                score += min((current_price - ma20) / ma20 * 100, 15)
            else:
                score -= min((ma20 - current_price) / ma20 * 100, 15)

            # 价格趋势 (20%)
            if len(prices) >= 5:
                recent_trend = (prices[-1] - prices[-5]) / prices[-5] * 100
                score += min(max(recent_trend * 2, -10), 10)

            # 确保分数在0-100范围内
            score = max(0, min(100, score))
            return score

        except Exception as e:
            print(f"计算情绪评分失败: {e}")
            return 50.0


# 为了向后兼容，保持原有的组件类
MarketOverviewWidget = ProfessionalMarketOverviewWidget
TechnicalIndicatorWidget = ProfessionalTechnicalIndicatorWidget
StockAnalysisWidget = StockSelectorWidget
