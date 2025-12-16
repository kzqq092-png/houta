# 智能模型选择机制UI设计方案

## 概述

本文档基于现有系统架构，为智能模型选择机制设计完整的用户界面方案，包括控制面板、市场监控、性能展示和结果展示四大核心UI模块。方案充分整合现有UI框架，确保界面风格一致性和用户体验的连贯性。

## 现有UI框架分析

### 核心UI组件架构

基于现有系统分析，系统具备以下UI框架：

1. **现代UI协调器** (`gui/coordinators/modern_ui_coordinator.py`)
   - 统一的UI组件管理和协调
   - 支持Enhanced和Modern两套UI风格
   - 组件生命周期管理和状态跟踪

2. **统一设计系统** (`gui/styles/unified_design_system.py`)
   - 标准化的颜色、字体、间距等设计元素
   - 主题切换和自适应布局
   - 组件样式标准化

3. **AI功能控制面板** (`gui/widgets/ai_features_control_panel.py`)
   - AI服务状态监控
   - 预测结果展示
   - 用户行为学习控制

4. **智能推荐面板** (`gui/widgets/enhanced_ui/smart_recommendation_panel.py`)
   - 推荐卡片组件设计
   - 用户画像展示
   - 反馈管理机制

5. **性能监控组件** (`gui/widgets/performance/`)
   - 实时性能数据展示
   - 多维度性能指标监控
   - 图表可视化组件

## UI模块设计

### 1. 智能模型选择控制面板 (`IntelligentModelControlPanel`)

#### 核心功能
- 智能选择器参数配置
- 模型选择策略管理
- 实时状态监控
- 快捷操作控制

#### 界面布局设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    智能模型选择控制面板                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   系统状态      │  │   选择策略      │  │   快捷控制      │  │
│  │                 │  │                 │  │                 │  │
│  │ 🟢 运行中       │  │ 📊 智能自适应   │  │ [启用/禁用]     │  │
│  │ 活跃模型: 4     │  │ 融合: 开启      │  │ [重置配置]      │  │
│  │ 今日预测: 156   │  │ 缓存: 开启      │  │ [紧急切换]      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                           配置参数                              │
├─────────────────────────────────────────────────────────────────┤
│  市场检测设置:                                                   │
│  □ 高波动率阈值: [0.30]  □ 低波动率阈值: [0.10]                 │
│  □ 强趋势阈值: [0.70]   □ 弱趋势阈值: [0.30]                    │
│                                                                  │
│  性能评估设置:                                                   │
│  □ 最低样本数: [100]    □ 性能权重配置                          │
│  □ 准确率权重: [30%]    □ 速度权重: [20%]                       │
│  □ 稳定性权重: [30%]    □ 市场匹配权重: [20%]                   │
│                                                                  │
│  选择策略设置:                                                   │
│  □ 最大模型数: [3]      □ 延迟要求: [1000ms]                   │
│  □ 准确率要求: [0.60]   □ 内存限制: [2048MB]                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 核心组件实现

```python
class IntelligentModelControlPanel(QWidget):
    """智能模型选择控制面板"""
    
    # 信号定义
    config_changed = pyqtSignal(dict)
    strategy_toggled = pyqtSignal(bool)
    emergency_fallback = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.intelligent_selector = None
        self.init_ui()
        self.setup_connections()
        self.start_monitoring()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. 状态概览区域
        status_area = self._create_status_area()
        layout.addWidget(status_area)
        
        # 2. 配置参数区域
        config_area = self._create_config_area()
        layout.addWidget(config_area)
        
        # 3. 操作控制区域
        control_area = self._create_control_area()
        layout.addWidget(control_area)
        
        # 应用统一样式
        self._apply_unified_styles()
    
    def _create_status_area(self) -> QGroupBox:
        """创建状态概览区域"""
        status_group = QGroupBox("系统状态")
        status_layout = QGridLayout(status_group)
        
        # 系统运行状态
        self.status_label = QLabel("🟢 运行中")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
        """)
        status_layout.addWidget(self.status_label, 0, 0)
        
        # 活跃模型数量
        status_layout.addWidget(QLabel("活跃模型:"), 0, 1)
        self.active_models_lcd = QLCDNumber(2)
        self.active_models_lcd.setStyleSheet("QLCDNumber { background-color: #2c3e50; color: #3498db; }")
        status_layout.addWidget(self.active_models_lcd, 0, 2)
        
        # 今日预测次数
        status_layout.addWidget(QLabel("今日预测:"), 1, 0)
        self.predictions_today_lcd = QLCDNumber(4)
        self.predictions_today_lcd.setStyleSheet("QLCDNumber { background-color: #2c3e50; color: #e74c3c; }")
        status_layout.addWidget(self.predictions_today_lcd, 1, 2)
        
        # 当前策略
        status_layout.addWidget(QLabel("当前策略:"), 1, 1)
        self.strategy_label = QLabel("📊 智能自适应")
        self.strategy_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        status_layout.addWidget(self.strategy_label, 1, 2)
        
        return status_group
    
    def _create_config_area(self) -> QScrollArea:
        """创建配置参数区域"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        
        # 市场检测设置
        market_group = QGroupBox("市场检测设置")
        market_layout = QFormLayout(market_group)
        
        self.high_vol_threshold = QDoubleSpinBox()
        self.high_vol_threshold.setRange(0.0, 1.0)
        self.high_vol_threshold.setSingleStep(0.01)
        self.high_vol_threshold.setValue(0.30)
        self.high_vol_threshold.valueChanged.connect(self._on_config_changed)
        market_layout.addRow("高波动率阈值:", self.high_vol_threshold)
        
        self.low_vol_threshold = QDoubleSpinBox()
        self.low_vol_threshold.setRange(0.0, 1.0)
        self.low_vol_threshold.setSingleStep(0.01)
        self.low_vol_threshold.setValue(0.10)
        self.low_vol_threshold.valueChanged.connect(self._on_config_changed)
        market_layout.addRow("低波动率阈值:", self.low_vol_threshold)
        
        config_layout.addWidget(market_group)
        
        # 性能评估设置
        performance_group = QGroupBox("性能评估设置")
        performance_layout = QFormLayout(performance_group)
        
        self.min_samples = QSpinBox()
        self.min_samples.setRange(10, 1000)
        self.min_samples.setValue(100)
        self.min_samples.valueChanged.connect(self._on_config_changed)
        performance_layout.addRow("最低样本数:", self.min_samples)
        
        # 权重配置
        weights_layout = QGridLayout()
        
        self.accuracy_weight = QSpinBox()
        self.accuracy_weight.setRange(0, 100)
        self.accuracy_weight.setValue(30)
        self.accuracy_weight.valueChanged.connect(self._on_config_changed)
        weights_layout.addWidget(QLabel("准确率权重(%):"), 0, 0)
        weights_layout.addWidget(self.accuracy_weight, 0, 1)
        
        self.speed_weight = QSpinBox()
        self.speed_weight.setRange(0, 100)
        self.speed_weight.setValue(20)
        self.speed_weight.valueChanged.connect(self._on_config_changed)
        weights_layout.addWidget(QLabel("速度权重(%):"), 1, 0)
        weights_layout.addWidget(self.speed_weight, 1, 1)
        
        self.stability_weight = QSpinBox()
        self.stability_weight.setRange(0, 100)
        self.stability_weight.setValue(30)
        self.stability_weight.valueChanged.connect(self._on_config_changed)
        weights_layout.addWidget(QLabel("稳定性权重(%):"), 2, 0)
        weights_layout.addWidget(self.stability_weight, 2, 1)
        
        performance_layout.addRow(weights_layout)
        config_layout.addWidget(performance_group)
        
        # 选择策略设置
        strategy_group = QGroupBox("选择策略设置")
        strategy_layout = QFormLayout(strategy_group)
        
        self.max_models = QSpinBox()
        self.max_models.setRange(1, 10)
        self.max_models.setValue(3)
        self.max_models.valueChanged.connect(self._on_config_changed)
        strategy_layout.addRow("最大模型数:", self.max_models)
        
        self.max_latency = QSpinBox()
        self.max_latency.setRange(100, 10000)
        self.max_latency.setSingleStep(100)
        self.max_latency.setValue(1000)
        self.max_latency.valueChanged.connect(self._on_config_changed)
        strategy_layout.addRow("延迟要求(ms):", self.max_latency)
        
        self.min_accuracy = QDoubleSpinBox()
        self.min_accuracy.setRange(0.0, 1.0)
        self.min_accuracy.setSingleStep(0.01)
        self.min_accuracy.setValue(0.60)
        self.min_accuracy.valueChanged.connect(self._on_config_changed)
        strategy_layout.addRow("准确率要求:", self.min_accuracy)
        
        config_layout.addWidget(strategy_group)
        
        scroll_area.setWidget(config_widget)
        return scroll_area
    
    def _create_control_area(self) -> QGroupBox:
        """创建操作控制区域"""
        control_group = QGroupBox("快捷控制")
        control_layout = QHBoxLayout(control_group)
        
        # 启用/禁用按钮
        self.enable_button = QPushButton("🟢 启用智能选择")
        self.enable_button.setCheckable(True)
        self.enable_button.setChecked(True)
        self.enable_button.toggled.connect(self._on_toggle_selection)
        control_layout.addWidget(self.enable_button)
        
        # 重置配置按钮
        self.reset_button = QPushButton("🔄 重置配置")
        self.reset_button.clicked.connect(self._on_reset_config)
        control_layout.addWidget(self.reset_button)
        
        # 紧急切换按钮
        self.emergency_button = QPushButton("⚠️ 紧急切换")
        self.emergency_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.emergency_button.clicked.connect(self.emergency_fallback.emit)
        control_layout.addWidget(self.emergency_button)
        
        control_layout.addStretch()
        
        return control_group
    
    def update_status(self, status_data: Dict[str, Any]):
        """更新状态显示"""
        try:
            # 更新活跃模型数
            active_models = status_data.get('active_models', 0)
            self.active_models_lcd.display(active_models)
            
            # 更新预测次数
            predictions_today = status_data.get('predictions_today', 0)
            self.predictions_today_lcd.display(predictions_today)
            
            # 更新系统状态
            is_running = status_data.get('is_running', False)
            if is_running:
                self.status_label.setText("🟢 运行中")
                self.status_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        font-weight: bold;
                        padding: 8px 12px;
                        border-radius: 4px;
                        background-color: #d4edda;
                        color: #155724;
                        border: 1px solid #c3e6cb;
                    }
                """)
            else:
                self.status_label.setText("🔴 已停止")
                self.status_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        font-weight: bold;
                        padding: 8px 12px;
                        border-radius: 4px;
                        background-color: #f8d7da;
                        color: #721c24;
                        border: 1px solid #f5c6cb;
                    }
                """)
                
        except Exception as e:
            logger.error(f"更新状态显示失败: {e}")

class MarketStateMonitor(QWidget):
    """市场状态监控界面"""
    
    # 信号定义
    state_updated = pyqtSignal(dict)
    alert_triggered = pyqtSignal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.market_detector = None
        self.charts = {}
        self.init_ui()
        self.setup_timer()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. 状态卡片区域
        cards_area = self._create_state_cards()
        layout.addWidget(cards_area)
        
        # 2. 流动性评估区域
        liquidity_area = self._create_liquidity_area()
        layout.addWidget(liquidity_area)
        
        # 3. 图表分析区域
        charts_area = self._create_charts_area()
        layout.addWidget(charts_area)
    
    def _create_state_cards(self) -> QWidget:
        """创建状态卡片区域"""
        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setSpacing(20)
        
        # 波动率状态卡片
        self.volatility_card = self._create_state_card(
            "波动率状态", "📊 正常", "0.25", "0.28", "#3498db"
        )
        cards_layout.addWidget(self.volatility_card)
        
        # 趋势强度卡片
        self.trend_card = self._create_state_card(
            "趋势强度", "📈 强趋势", "0.75", "上涨", "#27ae60"
        )
        cards_layout.addWidget(self.trend_card)
        
        # 市场体制卡片
        self.regime_card = self._create_state_card(
            "市场体制", "🐮 牛市", "85%", "45天", "#f39c12"
        )
        cards_layout.addWidget(self.regime_card)
        
        return cards_widget
    
    def _create_state_card(self, title: str, status: str, primary_value: str, 
                          secondary_value: str, color: str) -> QGroupBox:
        """创建状态卡片"""
        card = QGroupBox()
        card.setFixedSize(200, 120)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # 标题
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #7f8c8d;
            }
        """)
        layout.addWidget(title_label)
        
        # 状态
        status_label = QLabel(status)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {color};
                padding: 5px;
            }}
        """)
        layout.addWidget(status_label)
        
        # 主值
        primary_label = QLabel(primary_value)
        primary_label.setAlignment(Qt.AlignCenter)
        primary_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(primary_label)
        
        # 次要值
        secondary_label = QLabel(secondary_value)
        secondary_label.setAlignment(Qt.AlignCenter)
        secondary_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #7f8c8d;
            }
        """)
        layout.addWidget(secondary_label)
        
        return card
    
    def _create_liquidity_area(self) -> QGroupBox:
        """创建流动性评估区域"""
        liquidity_group = QGroupBox("流动性状态评估")
        liquidity_layout = QVBoxLayout(liquidity_group)
        
        # 实时指标
        indicators_layout = QHBoxLayout()
        
        # 成交量
        volume_widget = self._create_indicator("成交量", "2.5B", "#3498db")
        indicators_layout.addWidget(volume_widget)
        
        # 成交额
        amount_widget = self._create_indicator("成交额", "125M", "#e74c3c")
        indicators_layout.addWidget(amount_widget)
        
        # 换手率
        turnover_widget = self._create_indicator("换手率", "3.2%", "#27ae60")
        indicators_layout.addWidget(turnover_widget)
        
        liquidity_layout.addLayout(indicators_layout)
        
        # 详细指标
        details_layout = QGridLayout()
        
        # 市场深度
        depth_label = QLabel("市场深度:")
        self.depth_value = QLabel("良好")
        self.depth_value.setStyleSheet("""
            QLabel {
                color: #27ae60;
                font-weight: bold;
            }
        """)
        details_layout.addWidget(depth_label, 0, 0)
        details_layout.addWidget(self.depth_value, 0, 1)
        
        # 买卖价差
        spread_label = QLabel("买卖价差:")
        self.spread_value = QLabel("0.05%")
        self.spread_value.setStyleSheet("""
            QLabel {
                color: #f39c12;
                font-weight: bold;
            }
        """)
        details_layout.addWidget(spread_label, 0, 2)
        details_layout.addWidget(self.spread_value, 0, 3)
        
        # 流动性评分
        score_label = QLabel("流动性评分:")
        self.liquidity_score = QProgressBar()
        self.liquidity_score.setRange(0, 10)
        self.liquidity_score.setValue(8)
        self.liquidity_score.setFormat("8.2/10")
        self.liquidity_score.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 2px;
            }
        """)
        details_layout.addWidget(score_label, 1, 0)
        details_layout.addWidget(self.liquidity_score, 1, 1, 1, 3)
        
        liquidity_layout.addLayout(details_layout)
        
        return liquidity_group
    
    def _create_indicator(self, name: str, value: str, color: str) -> QWidget:
        """创建指标组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #7f8c8d;
            }
        """)
        
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {color};
            }}
        """)
        
        layout.addWidget(name_label)
        layout.addWidget(value_label)
        
        return widget
    
    def _create_charts_area(self) -> QWidget:
        """创建图表分析区域"""
        charts_widget = QWidget()
        charts_layout = QHBoxLayout(charts_widget)
        charts_layout.setSpacing(15)
        
        # 波动率时间序列图
        volatility_chart = self._create_chart_panel("波动率时间序列", "volatility")
        charts_layout.addWidget(volatility_chart)
        
        # 趋势强度变化图
        trend_chart = self._create_chart_panel("趋势强度变化", "trend")
        charts_layout.addWidget(trend_chart)
        
        # 流动性趋势图
        liquidity_chart = self._create_chart_panel("流动性趋势", "liquidity")
        charts_layout.addWidget(liquidity_chart)
        
        return charts_widget
    
    def _create_chart_panel(self, title: str, chart_type: str) -> QGroupBox:
        """创建图表面板"""
        chart_group = QGroupBox(title)
        chart_layout = QVBoxLayout(chart_group)
        
        # 图表占位符（实际实现中应集成Matplotlib或PyQtGraph）
        chart_placeholder = QLabel(f"[{title}图表]")
        chart_placeholder.setAlignment(Qt.AlignCenter)
        chart_placeholder.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                border-radius: 5px;
                background-color: #ecf0f1;
                color: #7f8c8d;
                font-size: 12px;
                padding: 40px;
            }
        """)
        chart_layout.addWidget(chart_placeholder)
        
        # 保存图表引用
        self.charts[chart_type] = chart_placeholder
        
        return chart_group
    
    def update_market_state(self, market_state: Dict[str, Any]):
        """更新市场状态显示"""
        try:
            # 更新波动率状态
            volatility = market_state.get('volatility', {})
            if volatility:
                self._update_volatility_display(volatility)
            
            # 更新趋势强度
            trend = market_state.get('trend_strength', {})
            if trend:
                self._update_trend_display(trend)
            
            # 更新市场体制
            regime = market_state.get('market_regime', {})
            if regime:
                self._update_regime_display(regime)
            
            # 更新流动性
            liquidity = market_state.get('liquidity', {})
            if liquidity:
                self._update_liquidity_display(liquidity)
            
            # 发射状态更新信号
            self.state_updated.emit(market_state)
            
        except Exception as e:
            logger.error(f"更新市场状态失败: {e}")
    
    def _update_volatility_display(self, volatility: Dict[str, Any]):
        """更新波动率显示"""
        current_vol = volatility.get('current', 0.25)
        historical_vol = volatility.get('historical', 0.25)
        
        # 更新主值和历史值
        status_text = "📊 正常"
        if current_vol > 0.4:
            status_text = "📈 高波动"
        elif current_vol < 0.1:
            status_text = "📉 低波动"
        
        # 这里需要更新卡片显示，简化处理
        logger.info(f"波动率更新: 当前={current_vol:.3f}, 历史={historical_vol:.3f}")
    
    def _update_trend_display(self, trend: Dict[str, Any]):
        """更新趋势显示"""
        strength = trend.get('strength', 0.75)
        direction = trend.get('direction', '上涨')
        
        logger.info(f"趋势更新: 强度={strength:.3f}, 方向={direction}")
    
    def _update_regime_display(self, regime: Dict[str, Any]):
        """更新市场体制显示"""
        regime_type = regime.get('regime_type', '牛市')
        confidence = regime.get('confidence', 0.85)
        
        logger.info(f"市场体制更新: 类型={regime_type}, 置信度={confidence:.2%}")
    
    def _update_liquidity_display(self, liquidity: Dict[str, Any]):
        """更新流动性显示"""
        volume = liquidity.get('volume', '2.5B')
        turnover = liquidity.get('turnover_rate', '3.2%')
        score = liquidity.get('liquidity_score', 8.2)
        
        # 更新流动性评分
        self.liquidity_score.setValue(int(score))
        self.liquidity_score.setFormat(f"{score:.1f}/10")
        
        logger.info(f"流动性更新: 成交量={volume}, 换手率={turnover}, 评分={score:.1f}")

### 3. 模型性能展示界面 (`ModelPerformancePanel`)

#### 核心功能
- 实时模型性能监控
- 多维度性能指标展示
- 性能对比分析
- 趋势分析图表

#### 界面布局设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      模型性能监控面板                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   模型性能概览  │  │   选择统计      │  │   性能趋势      │  │
│  │                 │  │                 │  │                 │  │
│  │ 📈 准确率: 78%  │  │ 🔄 选择次数:156 │  │ 📊 7日平均      │  │
│  │ ⚡ 延迟: 245ms  │  │ ✅ 成功率: 94%  │  │ 📈 稳步上升     │  │
│  │ 💾 内存: 1.2GB  │  │ ⚠️ 降级次数: 9  │  │ 🎯 目标达成     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      模型列表与性能详情                          │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────┬─────────────┬─────────────┬─────────────────────┐ │
│ │   模型类型  │   准确率    │   延迟      │     今日使用次数     │ │
│ ├─────────────┼─────────────┼─────────────┼─────────────────────┤ │
│ │ LSTM        │   82.5%     │   180ms     │        45          │ │
│ │ GRU         │   79.1%     │   165ms     │        38          │ │
│ │ CNN-LSTM    │   85.3%     │   320ms     │        28          │ │
│ │ Transformer │   77.8%     │   280ms     │        22          │ │
│ └─────────────┴─────────────┴─────────────┴─────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      性能对比图表                                │
├─────────────────────────────────────────────────────────────────┤
│ [准确率对比图]    [延迟对比图]    [使用频率图]    [综合评分图]   │
└─────────────────────────────────────────────────────────────────┘
```

#### 核心组件实现

```python
class ModelPerformancePanel(QWidget):
    """模型性能展示界面"""
    
    # 信号定义
    performance_alert = pyqtSignal(str, dict)
    model_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.performance_data = {}
        self.model_list = []
        self.init_ui()
        self.setup_timer()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. 性能概览区域
        overview_area = self._create_overview_area()
        layout.addWidget(overview_area)
        
        # 2. 模型列表区域
        list_area = self._create_model_list_area()
        layout.addWidget(list_area)
        
        # 3. 性能图表区域
        charts_area = self._create_performance_charts()
        layout.addWidget(charts_area)
    
    def _create_overview_area(self) -> QWidget:
        """创建性能概览区域"""
        overview_widget = QWidget()
        overview_layout = QHBoxLayout(overview_widget)
        overview_layout.setSpacing(20)
        
        # 模型性能概览卡片
        performance_card = self._create_overview_card(
            "模型性能概览",
            [("📈 准确率", "78%", "#27ae60"),
             ("⚡ 延迟", "245ms", "#3498db"),
             ("💾 内存", "1.2GB", "#e74c3c")]
        )
        overview_layout.addWidget(performance_card)
        
        # 选择统计卡片
        stats_card = self._create_overview_card(
            "选择统计",
            [("🔄 选择次数", "156", "#9b59b6"),
             ("✅ 成功率", "94%", "#27ae60"),
             ("⚠️ 降级次数", "9", "#f39c12")]
        )
        overview_layout.addWidget(stats_card)
        
        # 性能趋势卡片
        trend_card = self._create_overview_card(
            "性能趋势",
            [("📊 7日平均", "稳定", "#27ae60"),
             ("📈 趋势", "上升", "#3498db"),
             ("🎯 目标", "达成", "#27ae60")]
        )
        overview_layout.addWidget(trend_card)
        
        return overview_widget
    
    def _create_overview_card(self, title: str, metrics: List[Tuple[str, str, str]]) -> QGroupBox:
        """创建概览卡片"""
        card = QGroupBox(title)
        card.setFixedSize(220, 120)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        for metric_name, metric_value, color in metrics:
            metric_layout = QHBoxLayout()
            
            name_label = QLabel(metric_name)
            name_label.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: #7f8c8d;
                }
            """)
            
            value_label = QLabel(metric_value)
            value_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 13px;
                    font-weight: bold;
                    color: {color};
                }}
            """)
            
            metric_layout.addWidget(name_label)
            metric_layout.addStretch()
            metric_layout.addWidget(value_label)
            
            layout.addLayout(metric_layout)
        
        return card
    
    def _create_model_list_area(self) -> QGroupBox:
        """创建模型列表区域"""
        list_group = QGroupBox("模型列表与性能详情")
        list_layout = QVBoxLayout(list_group)
        
        # 创建表格
        self.model_table = QTableWidget()
        self.model_table.setColumnCount(4)
        self.model_table.setHorizontalHeaderLabels(["模型类型", "准确率", "延迟", "今日使用次数"])
        
        # 设置表格样式
        self.model_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                selection-background-color: #3498db;
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # 设置列宽
        header = self.model_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # 连接信号
        self.model_table.itemClicked.connect(self._on_model_selected)
        
        list_layout.addWidget(self.model_table)
        
        return list_group
    
    def _create_performance_charts(self) -> QWidget:
        """创建性能图表区域"""
        charts_widget = QWidget()
        charts_layout = QHBoxLayout(charts_widget)
        charts_layout.setSpacing(15)
        
        # 准确率对比图
        accuracy_chart = self._create_chart_card("准确率对比", "accuracy")
        charts_layout.addWidget(accuracy_chart)
        
        # 延迟对比图
        latency_chart = self._create_chart_card("延迟对比", "latency")
        charts_layout.addWidget(latency_chart)
        
        # 使用频率图
        frequency_chart = self._create_chart_card("使用频率", "frequency")
        charts_layout.addWidget(frequency_chart)
        
        # 综合评分图
        score_chart = self._create_chart_card("综合评分", "score")
        charts_layout.addWidget(score_chart)
        
        return charts_widget
    
    def _create_chart_card(self, title: str, chart_type: str) -> QGroupBox:
        """创建图表卡片"""
        chart_group = QGroupBox(title)
        chart_layout = QVBoxLayout(chart_group)
        
        # 图表占位符
        chart_placeholder = QLabel(f"[{title}图表]")
        chart_placeholder.setAlignment(Qt.AlignCenter)
        chart_placeholder.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                border-radius: 5px;
                background-color: #ecf0f1;
                color: #7f8c8d;
                font-size: 12px;
                padding: 30px;
                min-height: 150px;
            }
        """)
        
        chart_layout.addWidget(chart_placeholder)
        
        return chart_group
    
    def update_performance_data(self, performance_data: Dict[str, Any]):
        """更新性能数据"""
        try:
            self.performance_data = performance_data
            
            # 更新概览数据
            self._update_overview_metrics(performance_data)
            
            # 更新模型列表
            models = performance_data.get('models', [])
            self._update_model_list(models)
            
        except Exception as e:
            logger.error(f"更新性能数据失败: {e}")
    
    def _update_overview_metrics(self, data: Dict[str, Any]):
        """更新概览指标"""
        # 这里可以更新概览卡片的显示
        # 简化处理，只记录日志
        logger.info(f"更新概览指标: {data}")
    
    def _update_model_list(self, models: List[Dict[str, Any]]):
        """更新模型列表"""
        self.model_table.setRowCount(len(models))
        
        for row, model in enumerate(models):
            # 模型类型
            model_type = model.get('type', '')
            type_item = QTableWidgetItem(model_type)
            self.model_table.setItem(row, 0, type_item)
            
            # 准确率
            accuracy = f"{model.get('accuracy', 0):.1%}"
            accuracy_item = QTableWidgetItem(accuracy)
            accuracy_item.setData(Qt.UserRole, model.get('accuracy', 0))
            self.model_table.setItem(row, 1, accuracy_item)
            
            # 延迟
            latency = f"{model.get('latency', 0)}ms"
            latency_item = QTableWidgetItem(latency)
            latency_item.setData(Qt.UserRole, model.get('latency', 0))
            self.model_table.setItem(row, 2, latency_item)
            
            # 使用次数
            usage_count = str(model.get('usage_count', 0))
            usage_item = QTableWidgetItem(usage_count)
            self.model_table.setItem(row, 3, usage_item)
        
        # 设置行高
        self.model_table.resizeRowsToContents()
    
    def _on_model_selected(self, item: QTableWidgetItem):
        """模型选择事件"""
        row = item.row()
        model_type_item = self.model_table.item(row, 0)
        if model_type_item:
            model_type = model_type_item.text()
            self.model_selected.emit(model_type)
            logger.info(f"用户选择模型: {model_type}")

### 4. 预测结果展示界面 (`PredictionResultsPanel`)

#### 核心功能
- 预测结果可视化展示
- 模型选择过程透明化
- 结果可信度评估
- 历史预测对比

#### 界面布局设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      预测结果展示中心                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   最新预测      │  │   选择详情      │  │   置信度评估    │  │
│  │                 │  │                 │  │                 │  │
│  │ 📊 预测类型:    │  │ 🔍 分析模型:    │  │ 🎯 综合置信度:  │  │
│  │    股价预测     │  │    LSTM+GRU     │  │    82.5%        │  │
│  │                 │  │    CNN-LSTM     │  │                 │  │
│  │ 📈 预测结果:    │  │    Transformer  │  │ 📊 各模型置信度:│  │
│  │    上涨 2.3%    │  │    权重: 3:2:1  │  │    LSTM: 85%    │  │
│  │                 │  │                 │  │    GRU: 78%     │  │
│  │ ⏰ 预测时间:    │  │ 💡 选择依据:    │  │    CNN: 82%     │  │
│  │    2024-01-15   │  │    市场状态     │  │    TF: 80%      │  │
│  │    14:30:25     │  │    性能权重     │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      预测结果详细展示                            │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                     预测趋势图表                              │ │
│ │                                                             │ │
│ │        [预测价格走势与实际价格对比图表]                      │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      模型贡献度分析                              │
├─────────────────────────────────────────────────────────────────┤
│  LSTM模型: ████████████████████ 85% (权重: 0.5)                 │
│  GRU模型:  ████████████████ 78% (权重: 0.3)                     │
│  CNN模型:  █████████████████ 82% (权重: 0.2)                    │
├─────────────────────────────────────────────────────────────────┤
│                      预测准确性跟踪                              │
├─────────────────────────────────────────────────────────────────┤
│  近7天预测: 正确 5/7 (71.4%) | 近30天预测: 正确 22/30 (73.3%)   │
│  [预测准确性趋势图]                                           │
└─────────────────────────────────────────────────────────────────┘
```

#### 核心组件实现

```python
class PredictionResultsPanel(QWidget):
    """预测结果展示界面"""
    
    # 信号定义
    result_details_requested = pyqtSignal(dict)
    export_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_result = None
        self.historical_results = []
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. 结果概览区域
        overview_area = self._create_result_overview()
        layout.addWidget(overview_area)
        
        # 2. 详细结果展示区域
        details_area = self._create_result_details()
        layout.addWidget(details_area)
        
        # 3. 模型贡献度分析区域
        contribution_area = self._create_contribution_analysis()
        layout.addWidget(contribution_area)
        
        # 4. 准确性跟踪区域
        accuracy_area = self._create_accuracy_tracking()
        layout.addWidget(accuracy_area)
    
    def _create_result_overview(self) -> QWidget:
        """创建结果概览区域"""
        overview_widget = QWidget()
        overview_layout = QHBoxLayout(overview_widget)
        overview_layout.setSpacing(20)
        
        # 最新预测卡片
        latest_card = self._create_info_card(
            "最新预测",
            [("📊 预测类型", "股价预测"),
             ("📈 预测结果", "上涨 2.3%"),
             ("⏰ 预测时间", "2024-01-15 14:30:25")],
            "#3498db"
        )
        overview_layout.addWidget(latest_card)
        
        # 选择详情卡片
        selection_card = self._create_info_card(
            "选择详情",
            [("🔍 分析模型", "LSTM+GRU"),
             ("🔍 分析模型", "CNN-LSTM"),
             ("🔍 分析模型", "Transformer"),
             ("💡 选择依据", "市场状态+性能权重")],
            "#27ae60"
        )
        overview_layout.addWidget(selection_card)
        
        # 置信度评估卡片
        confidence_card = self._create_info_card(
            "置信度评估",
            [("🎯 综合置信度", "82.5%"),
             ("📊 LSTM", "85%"),
             ("📊 GRU", "78%"),
             ("📊 CNN", "82%"),
             ("📊 TF", "80%")],
            "#f39c12"
        )
        overview_layout.addWidget(confidence_card)
        
        return overview_widget
    
    def _create_info_card(self, title: str, items: List[Tuple[str, str]], color: str) -> QGroupBox:
        """创建信息卡片"""
        card = QGroupBox(title)
        card.setFixedSize(250, 160)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        for item_name, item_value in items:
            item_layout = QHBoxLayout()
            
            name_label = QLabel(item_name)
            name_label.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: #7f8c8d;
                    min-width: 80px;
                }
            """)
            
            value_label = QLabel(item_value)
            value_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 11px;
                    font-weight: bold;
                    color: {color};
                }}
            """)
            
            item_layout.addWidget(name_label)
            item_layout.addStretch()
            item_layout.addWidget(value_label)
            
            layout.addLayout(item_layout)
        
        return card
    
    def _create_result_details(self) -> QGroupBox:
        """创建详细结果展示区域"""
        details_group = QGroupBox("预测结果详细展示")
        details_layout = QVBoxLayout(details_group)
        
        # 预测趋势图表
        chart_placeholder = QLabel("[预测价格走势与实际价格对比图表]")
        chart_placeholder.setAlignment(Qt.AlignCenter)
        chart_placeholder.setStyleSheet("""
            QLabel {
                border: 2px solid #3498db;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #2c3e50;
                font-size: 14px;
                padding: 60px;
                min-height: 200px;
            }
        """)
        
        details_layout.addWidget(chart_placeholder)
        
        return details_group
    
    def _create_contribution_analysis(self) -> QGroupBox:
        """创建模型贡献度分析区域"""
        contribution_group = QGroupBox("模型贡献度分析")
        contribution_layout = QVBoxLayout(contribution_group)
        
        # LSTM贡献度
        lstm_layout = self._create_contribution_bar("LSTM模型", "85%", "0.5", "#3498db")
        contribution_layout.addLayout(lstm_layout)
        
        # GRU贡献度
        gru_layout = self._create_contribution_bar("GRU模型", "78%", "0.3", "#27ae60")
        contribution_layout.addLayout(gru_layout)
        
        # CNN贡献度
        cnn_layout = self._create_contribution_bar("CNN模型", "82%", "0.2", "#e74c3c")
        contribution_layout.addLayout(cnn_layout)
        
        return contribution_group
    
    def _create_contribution_bar(self, model_name: str, confidence: str, 
                                weight: str, color: str) -> QHBoxLayout:
        """创建贡献度进度条"""
        layout = QHBoxLayout()
        
        # 模型名称
        name_label = QLabel(f"{model_name}:")
        name_label.setFixedWidth(100)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        
        # 贡献度进度条
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(confidence.rstrip('%')))
        progress_bar.setFormat(confidence)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                text-align: center;
                font-weight: bold;
                font-size: 11px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        
        # 权重信息
        weight_label = QLabel(f"(权重: {weight})")
        weight_label.setFixedWidth(80)
        weight_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #7f8c8d;
            }
        """)
        
        layout.addWidget(name_label)
        layout.addWidget(progress_bar)
        layout.addWidget(weight_label)
        
        return layout
    
    def _create_accuracy_tracking(self) -> QGroupBox:
        """创建准确性跟踪区域"""
        accuracy_group = QGroupBox("预测准确性跟踪")
        accuracy_layout = QVBoxLayout(accuracy_group)
        
        # 准确性统计
        stats_layout = QHBoxLayout()
        
        # 近7天统计
        week_stats = QLabel("近7天预测: 正确 5/7 (71.4%)")
        week_stats.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #27ae60;
                padding: 5px 10px;
                background-color: #d5f4e6;
                border-radius: 4px;
            }
        """)
        
        # 近30天统计
        month_stats = QLabel("近30天预测: 正确 22/30 (73.3%)")
        month_stats.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #3498db;
                padding: 5px 10px;
                background-color: #d6eaf8;
                border-radius: 4px;
            }
        """)
        
        stats_layout.addWidget(week_stats)
        stats_layout.addWidget(month_stats)
        stats_layout.addStretch()
        
        accuracy_layout.addLayout(stats_layout)
        
        # 准确性趋势图
        trend_chart = QLabel("[预测准确性趋势图]")
        trend_chart.setAlignment(Qt.AlignCenter)
        trend_chart.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                border-radius: 5px;
                background-color: #ecf0f1;
                color: #7f8c8d;
                font-size: 12px;
                padding: 40px;
                min-height: 120px;
            }
        """)
        
        accuracy_layout.addWidget(trend_chart)
        
        return accuracy_group
    
    def display_prediction_result(self, result: Dict[str, Any]):
        """显示预测结果"""
        try:
            self.current_result = result
            
            # 更新结果概览
            self._update_result_overview(result)
            
            # 更新模型贡献度
            selections = result.get('selection_metadata', {}).get('selected_models', [])
            if selections:
                self._update_contribution_analysis(selections, result)
            
            # 添加到历史记录
            self.historical_results.append(result)
            if len(self.historical_results) > 100:  # 保留最近100条记录
                self.historical_results.pop(0)
            
            # 更新准确性跟踪
            self._update_accuracy_tracking()
            
        except Exception as e:
            logger.error(f"显示预测结果失败: {e}")
    
    def _update_result_overview(self, result: Dict[str, Any]):
        """更新结果概览"""
        # 这里应该更新概览卡片的具体内容
        # 简化处理，只记录日志
        logger.info(f"更新预测结果概览: {result}")
    
    def _update_contribution_analysis(self, selections: List[str], result: Dict[str, Any]):
        """更新贡献度分析"""
        # 这里应该更新进度条显示
        # 简化处理，只记录日志
        logger.info(f"更新模型贡献度: {selections}")
    
    def _update_accuracy_tracking(self):
        """更新准确性跟踪"""
        # 这里应该计算并更新准确性统计
        # 简化处理，只记录日志
        logger.info("更新准确性跟踪数据")

## 集成方案

### 1. 与现有系统的集成

智能模型选择机制UI将与以下现有组件无缝集成：

#### 核心服务集成
- **AI预测服务** (`core/services/ai_prediction_service.py`)
  - 通过智能选择器接口获取预测结果
  - 实时接收模型性能数据
  - 订阅市场状态变化通知

#### UI框架集成
- **现代UI协调器** (`gui/coordinators/modern_ui_coordinator.py`)
  - 注册新的UI组件到协调器
  - 遵循统一的组件生命周期管理
  - 支持主题切换和布局自适应

- **统一设计系统** (`gui/styles/unified_design_system.py`)
  - 应用一致的颜色主题和字体规范
  - 响应式布局和组件间距标准
  - 深色/浅色主题切换支持

#### AI功能集成
- **AI功能控制面板** (`gui/widgets/ai_features_control_panel.py`)
  - 添加智能模型选择控制入口
  - 集成状态监控和性能展示
  - 统一AI功能的用户交互体验

### 2. 组件层次结构

```
智能模型选择UI
├── IntelligentModelControlPanel (主控制面板)
│   ├── 状态概览区域
│   ├── 配置参数区域
│   └── 操作控制区域
├── MarketStateMonitor (市场状态监控)
│   ├── 状态卡片区域
│   ├── 流动性评估区域
│   └── 图表分析区域
├── ModelPerformancePanel (模型性能展示)
│   ├── 性能概览区域
│   ├── 模型列表区域
│   └── 性能图表区域
└── PredictionResultsPanel (预测结果展示)
    ├── 结果概览区域
    ├── 详细结果展示区域
    ├── 模型贡献度分析区域
    └── 准确性跟踪区域
```

### 3. 数据流和交互

#### 数据流向
1. **AI预测服务** → **智能选择器** → **UI组件**
2. **市场检测器** → **市场状态监控** → **模型选择策略**
3. **性能评估器** → **性能展示面板** → **用户界面**

#### 事件交互
- **配置变更**: UI → 智能选择器 → 策略更新
- **状态更新**: 智能选择器 → UI → 实时刷新
- **用户操作**: UI → 智能选择器 → 立即执行
- **性能监控**: 性能评估器 → 性能面板 → 数据展示

## 配置管理

### 1. UI配置参数

```python
UI_CONFIG = {
    "intelligent_model_control": {
        "refresh_interval": 1000,  # 毫秒
        "show_advanced_settings": False,
        "auto_save_config": True,
        "theme": "modern",  # modern, classic, dark
    },
    "market_state_monitor": {
        "chart_update_interval": 5000,  # 毫秒
        "show_historical_data": True,
        "max_data_points": 100,
        "enable_alerts": True,
    },
    "model_performance_panel": {
        "table_sort_enabled": True,
        "chart_animation": True,
        "performance_metrics": ["accuracy", "latency", "memory_usage"],
        "export_enabled": True,
    },
    "prediction_results_panel": {
        "show_model_details": True,
        "result_history_size": 50,
        "confidence_threshold": 0.7,
        "enable_comparison": True,
    }
}
```

### 2. 主题配置

#### 现代主题 (Modern Theme)
- 主色调: `#3498db` (蓝色)
- 成功色: `#27ae60` (绿色)
- 警告色: `#f39c12` (橙色)
- 错误色: `#e74c3c` (红色)
- 背景色: `#ffffff` (白色)
- 文字色: `#2c3e50` (深灰蓝)

#### 深色主题 (Dark Theme)
- 主色调: `#5dade2` (浅蓝)
- 成功色: `#58d68d` (浅绿)
- 警告色: `#f8c471` (浅橙)
- 错误色: `#ec7063` (浅红)
- 背景色: `#2c3e50` (深蓝灰)
- 文字色: `#ecf0f1` (浅灰)

## 使用示例

### 1. 基础集成代码

```python
# 在主窗口中集成智能模型选择UI
from gui.widgets.intelligent_model_selection import (
    IntelligentModelControlPanel,
    MarketStateMonitor,
    ModelPerformancePanel,
    PredictionResultsPanel
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel)
        
        # 创建右侧展示面板
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel)
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 智能模型选择控制面板
        self.control_panel = IntelligentModelControlPanel()
        layout.addWidget(self.control_panel)
        
        # 市场状态监控
        self.market_monitor = MarketStateMonitor()
        layout.addWidget(self.market_monitor)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧展示面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 模型性能展示
        self.performance_panel = ModelPerformancePanel()
        layout.addWidget(self.performance_panel)
        
        # 预测结果展示
        self.results_panel = PredictionResultsPanel()
        layout.addWidget(self.results_panel)
        
        return panel
    
    def setup_connections(self):
        """设置信号连接"""
        # 控制面板信号
        self.control_panel.config_changed.connect(self._on_config_changed)
        self.control_panel.strategy_toggled.connect(self._on_strategy_toggled)
        self.control_panel.emergency_fallback.connect(self._on_emergency_fallback)
        
        # 性能面板信号
        self.performance_panel.model_selected.connect(self._on_model_selected)
        self.performance_panel.performance_alert.connect(self._on_performance_alert)
        
        # 结果面板信号
        self.results_panel.result_details_requested.connect(self._on_result_details_requested)
        self.results_panel.export_requested.connect(self._on_export_requested)
    
    def _on_config_changed(self, config: Dict[str, Any]):
        """配置变更处理"""
        logger.info(f"配置变更: {config}")
        # 更新智能选择器配置
        if hasattr(self, 'intelligent_selector'):
            self.intelligent_selector.update_config(config)
    
    def _on_strategy_toggled(self, enabled: bool):
        """策略开关处理"""
        logger.info(f"智能选择策略{'启用' if enabled else '禁用'}")
        # 启用/禁用智能选择器
        if hasattr(self, 'intelligent_selector'):
            if enabled:
                self.intelligent_selector.enable()
            else:
                self.intelligent_selector.disable()
    
    def _on_emergency_fallback(self):
        """紧急切换处理"""
        logger.warning("执行紧急切换策略")
        # 触发紧急切换
        if hasattr(self, 'intelligent_selector'):
            self.intelligent_selector.emergency_fallback()
```

### 2. 配置加载示例

```python
# 配置文件: config/ui_config.json
{
  "intelligent_model_selection": {
    "control_panel": {
      "refresh_interval": 1000,
      "auto_save": true,
      "theme": "modern"
    },
    "market_monitor": {
      "chart_update_interval": 5000,
      "show_alerts": true
    },
    "performance_panel": {
      "table_sortable": true,
      "export_enabled": true
    },
    "results_panel": {
      "show_details": true,
      "history_size": 50
    }
  }
}

# 配置加载代码
import json

def load_ui_config(config_path: str) -> Dict[str, Any]:
    """加载UI配置"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"配置文件未找到: {config_path}，使用默认配置")
        return UI_CONFIG
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {e}")
        return UI_CONFIG

# 使用示例
ui_config = load_ui_config("config/ui_config.json")
control_panel_config = ui_config.get("intelligent_model_selection", {}).get("control_panel", {})
```

## 总结

本UI设计方案为智能模型选择机制提供了完整的用户界面解决方案，包括：

1. **四大核心UI模块**：控制面板、状态监控、性能展示、结果展示
2. **现代化设计风格**：统一的设计语言、响应式布局、主题支持
3. **深度系统集成**：与现有UI框架和AI服务无缝集成
4. **丰富交互功能**：实时数据展示、配置管理、性能监控、结果分析
5. **可扩展架构**：模块化设计、配置化管理、易于维护和扩展

该设计方案充分考虑了用户体验、系统性能和可维护性，为智能模型选择机制提供了专业、直观、易用的操作界面。
```

### 2. 市场状态监控界面 (`MarketStateMonitor`)

#### 核心功能
- 实时市场状态显示
- 波动率趋势图表
- 流动性状态监控
- 市场体制分析

#### 界面布局设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      市场状态监控中心                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   波动率状态    │  │   趋势强度      │  │   市场体制      │  │
│  │                 │  │                 │  │                 │  │
│  │     📊 正常     │  │     📈 强趋势   │  │     🐮 牛市    │  │
│  │    历史: 0.25   │  │    强度: 0.75   │  │    置信度: 85%  │  │
│  │    实现: 0.28   │  │    方向: 上涨   │  │    周期: 45天   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      流动性状态评估                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    实时流动性指标                           │ │
│  │                                                             │ │
│  │  成交量: 2.5B    成交额: 125M    换手率: 3.2%              │ │
│  │  市场深度: 良好   买卖价差: 0.05%  流动性评分: 8.2/10      │ │
│  └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      历史趋势分析图表                            │
├─────────────────────────────────────────────────────────────────┤
│  [波动率时间序列图]    [趋势强度变化图]    [流动性趋势图]        │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

#### 核心组件实现

```python
class MarketStateMonitor(QWidget):
    """市场状态监控界面"""
    
    # 信号定义
    state_updated = pyqtSignal(dict)
    alert_triggered = pyqtSignal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.market_detector = None
        self.charts = {}
        self.init_ui()
        self.setup_timer()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. 状态卡片区域
        cards_area = self._create_state_cards()
        layout.addWidget(cards_area)
        
        # 2. 流动性评估区域
        liquidity_area = self._create_liquidity_area()
        layout.addWidget(liquidity_area)
        
        # 3. 图表分析区域
        charts_area = self._create_charts_area()
        layout.addWidget(charts_area)
    
    def _create_state_cards(self) -> QWidget:
        """创建状态卡片区域"""
        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setSpacing(20)
        
        # 波动率状态卡片
        self.volatility_card = self._create_state_card(
            "波动率状态", "📊", "正常", "#3498db"
        )
        cards_layout.addWidget(self.volatility_card)
        
        # 趋势强度卡片
        self.trend_card = self._create_state_card(
            "趋势强度", "📈", "强趋势", "#e74c3c"
        )
        cards_layout.addWidget(self.trend_card)
        
        # 市场体制卡片
        self.regime_card = self._create_state_card(
            "市场体制", "🐮", "牛市", "#27ae60"
        )
        cards_layout.addWidget(self.regime_card)
        
        return cards_widget
    
    def _create_state_card(self, title: str, icon: str, status: str, color: str) -> QFrame:
        """创建状态卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setFixedSize(200, 120)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # 标题
        title_label = QLabel(f"{icon} {title}")
        title_label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        title_label.setStyleSheet(f"color: {color};")
        layout.addWidget(title_label)
        
        # 状态
        self.status_label = QLabel(status)
        self.status_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 详细信息
        self.detail_labels = {}
        layout.addWidget(QLabel("详细信息:"))
        
        return card
    
    def _create_liquidity_area(self) -> QGroupBox:
        """创建流动性评估区域"""
        liquidity_group = QGroupBox("流动性状态评估")
        liquidity_layout = QVBoxLayout(liquidity_group)
        
        # 实时指标
        metrics_layout = QGridLayout()
        
        # 成交量
        metrics_layout.addWidget(QLabel("成交量:"), 0, 0)
        self.volume_label = QLabel("2.5B")
        self.volume_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        self.volume_label.setStyleSheet("color: #3498db;")
        metrics_layout.addWidget(self.volume_label, 0, 1)
        
        # 成交额
        metrics_layout.addWidget(QLabel("成交额:"), 0, 2)
        self.amount_label = QLabel("125M")
        self.amount_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        self.amount_label.setStyleSheet("color: #e74c3c;")
        metrics_layout.addWidget(self.amount_label, 0, 3)
        
        # 换手率
        metrics_layout.addWidget(QLabel("换手率:"), 1, 0)
        self.turnover_label = QLabel("3.2%")
        self.turnover_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        self.turnover_label.setStyleSheet("color: #f39c12;")
        metrics_layout.addWidget(self.turnover_label, 1, 1)
        
        # 流动性评分
        metrics_layout.addWidget(QLabel("流动性评分:"), 1, 2)
        self.liquidity_score = QLabel("8.2/10")
        self.liquidity_score.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        self.liquidity_score.setStyleSheet("color: #27ae60;")
        metrics_layout.addWidget(self.liquidity_score, 1, 3)
        
        liquidity_layout.addLayout(metrics_layout)
        
        # 流动性趋势图
        self.liquidity_chart = self._create_liquidity_chart()
        liquidity_layout.addWidget(self.liquidity_chart)
        
        return liquidity_group
    
    def _create_liquidity_chart(self) -> FigureCanvas:
        """创建流动性图表"""
        fig = Figure(figsize=(8, 3), dpi=100)
        canvas = FigureCanvas(fig)
        
        # 创建子图
        ax = fig.add_subplot(111)
        
        # 模拟数据
        time_range = pd.date_range(start='2024-01-01', periods=100, freq='H')
        liquidity_data = np.random.normal(8, 1, 100)
        
        ax.plot(time_range, liquidity_data, color='#3498db', linewidth=2)
        ax.fill_between(time_range, liquidity_data, alpha=0.3, color='#3498db')
        ax.set_title('流动性评分趋势', fontsize=10)
        ax.set_ylabel('评分')
        ax.grid(True, alpha=0.3)
        
        canvas.draw()
        return canvas
    
    def update_market_state(self, market_state: Dict[str, Any]):
        """更新市场状态显示"""
        try:
            # 更新波动率状态
            if 'volatility' in market_state:
                vol_state = market_state['volatility']
                self._update_volatility_card(vol_state)
            
            # 更新趋势强度
            if 'trend_strength' in market_state:
                trend_state = market_state['trend_strength']
                self._update_trend_card(trend_state)
            
            # 更新市场体制
            if 'market_regime' in market_state:
                regime_state = market_state['market_regime']
                self._update_regime_card(regime_state)
            
            # 更新流动性指标
            if 'liquidity' in market_state:
                liquidity_state = market_state['liquidity']
                self._update_liquidity_metrics(liquidity_state)
            
            self.state_updated.emit(market_state)
            
        except Exception as e:
            logger.error(f"更新市场状态失败: {e}")
```

### 3. 模型性能展示界面 (`ModelPerformancePanel`)

#### 核心功能
- 实时性能指标监控
- 模型对比分析
- 历史性能趋势
- 性能评分可视化

#### 界面布局设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      模型性能监控面板                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   深度学习模型   │  │   规则基础模型   │  │   统计模型      │  │
│  │                 │  │                 │  │                 │  │
│  │ 准确率: 85.2%   │  │ 准确率: 78.5%   │  │ 准确率: 72.1%   │  │
│  │ 速度: 156ms     │  │ 速度: 45ms      │  │ 速度: 89ms      │  │
│  │ 稳定性: 92.1%   │  │ 稳定性: 95.8%   │  │ 稳定性: 88.3%   │  │
│  │ 综合评分: 8.7   │  │ 综合评分: 8.2   │  │ 综合评分: 7.6   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      性能对比分析图表                            │
├─────────────────────────────────────────────────────────────────┤
│  [准确率对比柱状图]  [速度性能对比]  [稳定性趋势图]              │
│                                                             │
│  当前最优选择: 深度学习模型 (综合评分: 8.7)                    │
│  推荐理由: 在当前市场状态下表现最佳                           │
└─────────────────────────────────────────────────────────────────┘
```

#### 核心组件实现

```python
class ModelPerformancePanel(QWidget):
    """模型性能展示界面"""
    
    # 信号定义
    performance_updated = pyqtSignal(dict)
    model_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.performance_evaluator = None
        self.model_cards = {}
        self.charts = {}
        self.init_ui()
        self.setup_monitoring()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. 模型卡片区域
        cards_area = self._create_model_cards()
        layout.addWidget(cards_area)
        
        # 2. 性能对比图表
        charts_area = self._create_performance_charts()
        layout.addWidget(charts_area)
        
        # 3. 选择建议区域
        recommendation_area = self._create_recommendation_area()
        layout.addWidget(recommendation_area)
    
    def _create_model_cards(self) -> QWidget:
        """创建模型性能卡片"""
        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setSpacing(15)
        
        # 定义模型配置
        model_configs = [
            {'name': '深度学习模型', 'color': '#3498db', 'icon': '🧠'},
            {'name': '规则基础模型', 'color': '#e74c3c', 'icon': '📋'},
            {'name': '统计模型', 'color': '#f39c12', 'icon': '📊'},
            {'name': '情感分析模型', 'color': '#27ae60', 'icon': '💭'}
        ]
        
        for config in model_configs:
            card = self._create_model_card(config)
            cards_layout.addWidget(card)
        
        cards_layout.addStretch()
        return cards_widget
    
    def _create_model_card(self, config: Dict[str, str]) -> QFrame:
        """创建单个模型性能卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setFixedSize(180, 200)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {config['color']};
                border-radius: 8px;
                padding: 8px;
            }}
            QFrame:hover {{
                border-color: {config['color']};
                border-width: 3px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # 模型标题
        title_layout = QHBoxLayout()
        title_label = QLabel(f"{config['icon']} {config['name']}")
        title_label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        title_label.setStyleSheet(f"color: {config['color']};")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 性能指标
        metrics_layout = QGridLayout()
        
        # 准确率
        metrics_layout.addWidget(QLabel("准确率:"), 0, 0)
        self.accuracy_label = QLabel("85.2%")
        self.accuracy_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        self.accuracy_label.setStyleSheet("color: #27ae60;")
        metrics_layout.addWidget(self.accuracy_label, 0, 1)
        
        # 速度
        metrics_layout.addWidget(QLabel("速度:"), 1, 0)
        self.speed_label = QLabel("156ms")
        self.speed_label.setFont(QFont("Microsoft YaHei UI", 9))
        metrics_layout.addWidget(self.speed_label, 1, 1)
        
        # 稳定性
        metrics_layout.addWidget(QLabel("稳定性:"), 2, 0)
        self.stability_label = QLabel("92.1%")
        self.stability_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.stability_label.setStyleSheet("color: #f39c12;")
        metrics_layout.addWidget(self.stability_label, 2, 1)
        
        # 综合评分
        metrics_layout.addWidget(QLabel("综合评分:"), 3, 0)
        self.score_label = QLabel("8.7")
        self.score_label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        self.score_label.setStyleSheet("color: #3498db;")
        metrics_layout.addWidget(self.score_label, 3, 1)
        
        layout.addLayout(metrics_layout)
        
        # 状态指示器
        status_layout = QHBoxLayout()
        self.status_indicator = QLabel("🟢 活跃")
        self.status_indicator.setFont(QFont("Microsoft YaHei UI", 8))
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 8px;
            }
        """)
        status_layout.addWidget(self.status_indicator)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 点击事件
        card.mousePressEvent = lambda event: self.model_selected.emit(config['name'])
        
        return card
    
    def _create_performance_charts(self) -> QGroupBox:
        """创建性能对比图表"""
        charts_group = QGroupBox("性能对比分析图表")
        charts_layout = QVBoxLayout(charts_group)
        
        # 创建图表标签页
        tab_widget = QTabWidget()
        
        # 准确率对比图表
        accuracy_chart = self._create_accuracy_chart()
        tab_widget.addTab(accuracy_chart, "准确率对比")
        
        # 速度性能对比图表
        speed_chart = self._create_speed_chart()
        tab_widget.addTab(speed_chart, "速度性能")
        
        # 稳定性趋势图表
        stability_chart = self._create_stability_chart()
        tab_widget.addTab(stability_chart, "稳定性趋势")
        
        charts_layout.addWidget(tab_widget)
        return charts_group
    
    def _create_accuracy_chart(self) -> FigureCanvas:
        """创建准确率对比图表"""
        fig = Figure(figsize=(8, 4), dpi=100)
        canvas = FigureCanvas(fig)
        
        ax = fig.add_subplot(111)
        
        # 模型数据
        models = ['深度学习', '规则基础', '统计', '情感分析']
        accuracy = [85.2, 78.5, 72.1, 80.3]
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60']
        
        bars = ax.bar(models, accuracy, color=colors, alpha=0.8)
        
        # 添加数值标签
        for bar, acc in zip(bars, accuracy):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{acc}%', ha='center', va='bottom', fontsize=9)
        
        ax.set_title('模型准确率对比', fontsize=12, fontweight='bold')
        ax.set_ylabel('准确率 (%)')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        
        canvas.draw()
        return canvas
    
    def _create_speed_chart(self) -> FigureCanvas:
        """创建速度性能图表"""
        fig = Figure(figsize=(8, 4), dpi=100)
        canvas = FigureCanvas(fig)
        
        ax = fig.add_subplot(111)
        
        # 模型数据
        models = ['深度学习', '规则基础', '统计', '情感分析']
        speed = [156, 45, 89, 123]  # 毫秒
        
        bars = ax.bar(models, speed, color=colors, alpha=0.8)
        
        # 添加数值标签
        for bar, spd in zip(bars, speed):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                   f'{spd}ms', ha='center', va='bottom', fontsize=9)
        
        ax.set_title('模型预测速度对比', fontsize=12, fontweight='bold')
        ax.set_ylabel('响应时间 (ms)')
        ax.grid(True, alpha=0.3)
        
        canvas.draw()
        return canvas
    
    def _create_stability_chart(self) -> FigureCanvas:
        """创建稳定性趋势图表"""
        fig = Figure(figsize=(8, 4), dpi=100)
        canvas = FigureCanvas(fig)
        
        ax = fig.add_subplot(111)
        
        # 时间序列数据
        time_range = pd.date_range(start='2024-01-01', periods=50, freq='D')
        
        # 模拟各模型稳定性数据
        models = ['深度学习', '规则基础', '统计', '情感分析']
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60']
        
        for model, color in zip(models, colors):
            stability_data = np.random.normal(85, 5, 50)
            stability_data = np.clip(stability_data, 70, 100)
            ax.plot(time_range, stability_data, label=model, color=color, linewidth=2)
        
        ax.set_title('模型稳定性趋势', fontsize=12, fontweight='bold')
        ax.set_ylabel('稳定性评分')
        ax.set_xlabel('时间')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        canvas.draw()
        return canvas
    
    def _create_recommendation_area(self) -> QGroupBox:
        """创建选择建议区域"""
        recommendation_group = QGroupBox("智能选择建议")
        recommendation_layout = QVBoxLayout(recommendation_group)
        
        # 建议内容
        self.recommendation_text = QTextEdit()
        self.recommendation_text.setMaximumHeight(100)
        self.recommendation_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background-color: #f9f9f9;
            }
        """)
        self.recommendation_text.setReadOnly(True)
        recommendation_layout.addWidget(self.recommendation_text)
        
        # 执行建议按钮
        button_layout = QHBoxLayout()
        
        self.apply_recommendation_btn = QPushButton("应用推荐配置")
        self.apply_recommendation_btn.clicked.connect(self._apply_recommendation)
        button_layout.addWidget(self.apply_recommendation_btn)
        
        button_layout.addStretch()
        recommendation_layout.addLayout(button_layout)
        
        return recommendation_group
    
    def update_model_performance(self, performance_data: Dict[str, Any]):
        """更新模型性能数据"""
        try:
            for model_name, model_performance in performance_data.items():
                if model_name in self.model_cards:
                    self._update_model_card(model_name, model_performance)
            
            # 更新推荐
            self._update_recommendation(performance_data)
            
            self.performance_updated.emit(performance_data)
            
        except Exception as e:
            logger.error(f"更新模型性能失败: {e}")
    
    def _update_model_card(self, model_name: str, performance: Dict[str, Any]):
        """更新单个模型卡片显示"""
        if model_name not in self.model_cards:
            return
        
        card = self.model_cards[model_name]
        
        # 更新准确率
        accuracy = performance.get('accuracy', 0) * 100
        card.accuracy_label.setText(f"{accuracy:.1f}%")
        
        # 更新速度
        speed = performance.get('speed', 0)
        card.speed_label.setText(f"{speed}ms")
        
        # 更新稳定性
        stability = performance.get('stability', 0) * 100
        card.stability_label.setText(f"{stability:.1f}%")
        
        # 更新综合评分
        score = performance.get('composite_score', 0) * 10
        card.score_label.setText(f"{score:.1f}")
        
        # 更新状态
        is_active = performance.get('is_active', False)
        if is_active:
            card.status_indicator.setText("🟢 活跃")
        else:
            card.status_indicator.setText("🔴 停用")
```

### 4. 预测结果展示界面 (`PredictionResultsPanel`)

#### 核心功能
- 智能选择结果展示
- 选择理由说明
- 多模型融合结果
- 结果可信度分析

#### 界面布局设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      智能预测结果展示                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   预测类型      │  │   选择模型      │  │   处理时间      │  │
│  │                 │  │                 │  │                 │  │
│  │   📊 形态识别   │  │   深度学习+规则 │  │   234ms         │  │
│  │   置信度: 87%   │  │   融合权重: 0.6 │  │   状态: 成功    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      选择理由说明                                │
├─────────────────────────────────────────────────────────────────┤
│  当前市场状态: 正常波动率 + 强上涨趋势                           │
│  选择策略: 在强趋势环境下，深度学习模型表现更优                   │
│  模型评分: 深度学习(8.7) > 规则基础(8.2) > 统计(7.6)           │
│  性能权衡: 准确率优先，兼顾预测速度                             │
├─────────────────────────────────────────────────────────────────┤
│                      详细预测结果                                │
├─────────────────────────────────────────────────────────────────┤
│  形态预测: 上涨三角形 (置信度: 87%)                             │
│  目标价位: 125.80 元 (上涨空间: 8.5%)                          │
│  时间预期: 5-8 个交易日                                         │
│  风险等级: 中等                                                 │
│                                                             │
│  [详细技术分析] [风险评估报告] [历史相似案例]                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 核心组件实现

```python
class PredictionResultsPanel(QWidget):
    """预测结果展示界面"""
    
    # 信号定义
    result_viewed = pyqtSignal(dict)
    detail_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_result = None
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. 结果概览区域
        overview_area = self._create_overview_area()
        layout.addWidget(overview_area)
        
        # 2. 选择理由说明
        reasoning_area = self._create_reasoning_area()
        layout.addWidget(reasoning_area)
        
        # 3. 详细预测结果
        details_area = self._create_details_area()
        layout.addWidget(details_area)
    
    def _create_overview_area(self) -> QWidget:
        """创建结果概览区域"""
        overview_widget = QWidget()
        overview_layout = QHBoxLayout(overview_widget)
        overview_layout.setSpacing(30)
        
        # 预测类型卡片
        self.prediction_type_card = self._create_info_card(
            "预测类型", "📊 形态识别", "#3498db"
        )
        overview_layout.addWidget(self.prediction_type_card)
        
        # 选择模型卡片
        self.selected_models_card = self._create_info_card(
            "选择模型", "深度学习+规则", "#e74c3c"
        )
        overview_layout.addWidget(self.selected_models_card)
        
        # 处理时间卡片
        self.processing_time_card = self._create_info_card(
            "处理时间", "234ms", "#f39c12"
        )
        overview_layout.addWidget(self.processing_time_card)
        
        # 状态卡片
        self.status_card = self._create_info_card(
            "处理状态", "✅ 成功", "#27ae60"
        )
        overview_layout.addWidget(self.status_card)
        
        overview_layout.addStretch()
        return overview_widget
    
    def _create_info_card(self, title: str, content: str, color: str) -> QFrame:
        """创建信息卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setFixedSize(140, 80)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {color};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Microsoft YaHei UI", 8))
        title_label.setStyleSheet(f"color: {color};")
        layout.addWidget(title_label)
        
        # 内容
        content_label = QLabel(content)
        content_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        content_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(content_label)
        
        return card
    
    def _create_reasoning_area(self) -> QGroupBox:
        """创建选择理由说明区域"""
        reasoning_group = QGroupBox("选择理由说明")
        reasoning_layout = QVBoxLayout(reasoning_group)
        
        # 选择理由文本
        self.reasoning_text = QTextEdit()
        self.reasoning_text.setMaximumHeight(120)
        self.reasoning_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei UI';
                font-size: 9px;
                line-height: 1.4;
            }
        """)
        self.reasoning_text.setReadOnly(True)
        reasoning_layout.addWidget(self.reasoning_text)
        
        return reasoning_group
    
    def _create_details_area(self) -> QGroupBox:
        """创建详细预测结果区域"""
        details_group = QGroupBox("详细预测结果")
        details_layout = QVBoxLayout(details_group)
        
        # 结果内容
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(150)
        self.results_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                background-color: #ffffff;
                font-family: 'Microsoft YaHei UI';
                font-size: 9px;
                line-height: 1.5;
            }
        """)
        self.results_text.setReadOnly(True)
        details_layout.addWidget(self.results_text)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.detail_analysis_btn = QPushButton("详细技术分析")
        self.detail_analysis_btn.clicked.connect(
            lambda: self.detail_requested.emit("technical_analysis")
        )
        button_layout.addWidget(self.detail_analysis_btn)
        
        self.risk_report_btn = QPushButton("风险评估报告")
        self.risk_report_btn.clicked.connect(
            lambda: self.detail_requested.emit("risk_assessment")
        )
        button_layout.addWidget(self.risk_report_btn)
        
        self.historical_cases_btn = QPushButton("历史相似案例")
        self.historical_cases_btn.clicked.connect(
            lambda: self.detail_requested.emit("historical_cases")
        )
        button_layout.addWidget(self.historical_cases_btn)
        
        button_layout.addStretch()
        details_layout.addLayout(button_layout)
        
        return details_group
    
    def display_prediction_result(self, result: Dict[str, Any]):
        """显示预测结果"""
        try:
            self.current_result = result
            
            # 更新概览信息
            self._update_overview(result)
            
            # 更新选择理由
            self._update_reasoning(result)
            
            # 更新详细结果
            self._update_details(result)
            
            self.result_viewed.emit(result)
            
        except Exception as e:
            logger.error(f"显示预测结果失败: {e}")
    
    def _update_overview(self, result: Dict[str, Any]):
        """更新概览信息"""
        # 更新预测类型
        prediction_type = result.get('prediction_type', '未知')
        self.prediction_type_card.children()[1].setText(f"📊 {prediction_type}")
        
        # 更新选择模型
        selected_models = result.get('selection_metadata', {}).get('selected_models', [])
        models_text = '+'.join(selected_models[:2])  # 显示前两个模型
        if len(selected_models) > 2:
            models_text += f"(+{len(selected_models)-2})"
        self.selected_models_card.children()[1].setText(models_text)
        
        # 更新处理时间
        processing_time = result.get('selection_metadata', {}).get('processing_time_ms', 0)
        self.processing_time_card.children()[1].setText(f"{processing_time}ms")
        
        # 更新状态
        is_success = result.get('success', True)
        if is_success:
            self.status_card.children()[1].setText("✅ 成功")
        else:
            self.status_card.children()[1].setText("❌ 失败")
    
    def _update_reasoning(self, result: Dict[str, Any]):
        """更新选择理由"""
        metadata = result.get('selection_metadata', {})
        market_state = metadata.get('market_state', {})
        selection_confidence = metadata.get('selection_confidence', 0)
        
        reasoning_parts = []
        
        # 市场状态分析
        if 'volatility' in market_state:
            vol_level = market_state['volatility'].get('level', 'unknown')
            reasoning_parts.append(f"当前市场波动率状态: {vol_level}")
        
        if 'trend_strength' in market_state:
            trend_level = market_state['trend_strength'].get('level', 'unknown')
            trend_direction = market_state['trend_strength'].get('direction', 'unknown')
            reasoning_parts.append(f"当前趋势强度: {trend_level}({trend_direction})")
        
        # 选择策略说明
        selected_models = metadata.get('selected_models', [])
        reasoning_parts.append(f"选择策略: 基于多模型融合，选择最优组合 {', '.join(selected_models)}")
        
        # 置信度说明
        reasoning_parts.append(f"选择置信度: {selection_confidence:.1%}")
        
        # 性能权衡
        data_quality = metadata.get('data_quality', {})
        reasoning_parts.append(f"数据质量评估: {data_quality.get('overall_score', 0):.2f}")
        
        reasoning_text = '\n'.join(f"• {part}" for part in reasoning_parts)
        self.reasoning_text.setPlainText(reasoning_text)
    
    def _update_details(self, result: Dict[str, Any]):
        """更新详细预测结果"""
        # 提取预测内容
        prediction_content = result.get('prediction', {})
        details_parts = []
        
        # 基本预测信息
        if 'pattern' in prediction_content:
            pattern = prediction_content['pattern']
            confidence = prediction_content.get('confidence', 0)
            details_parts.append(f"形态预测: {pattern} (置信度: {confidence:.1%})")
        
        if 'target_price' in prediction_content:
            target_price = prediction_content['target_price']
            upside = prediction_content.get('upside_potential', 0)
            details_parts.append(f"目标价位: {target_price} 元 (上涨空间: {upside:.1%})")
        
        if 'time_horizon' in prediction_content:
            time_horizon = prediction_content['time_horizon']
            details_parts.append(f"时间预期: {time_horizon}")
        
        if 'risk_level' in prediction_content:
            risk_level = prediction_content['risk_level']
            details_parts.append(f"风险等级: {risk_level}")
        
        # 融合信息
        fusion_metadata = result.get('fusion_metadata', {})
        if fusion_metadata:
            strategy = fusion_metadata.get('strategy_used', 'unknown')
            ensemble_size = fusion_metadata.get('ensemble_size', 1)
            details_parts.append(f"融合策略: {strategy} (参与模型: {ensemble_size}个)")
            
            weight_dist = fusion_metadata.get('weight_distribution', [])
            if weight_dist:
                details_parts.append(f"模型权重: {' '.join(f'{w:.2f}' for w in weight_dist)}")
        
        details_text = '\n'.join(details_parts)
        self.results_text.setPlainText(details_text)
```

## 集成方案

### 1. 主界面集成

#### 在性能监控面板中添加智能模型选择标签页
```python
# 修改 gui/widgets/performance/unified_performance_widget.py
def _create_modern_tabs(self):
    """创建现代化标签页"""
    tab_widget = QTabWidget()
    
    # ... 现有标签页 ...
    
    # 添加智能模型选择标签页
    intelligent_selection_tab = self._create_intelligent_selection_tab()
    tab_widget.addTab(intelligent_selection_tab, "🤖 智能模型选择")
    
    return tab_widget

def _create_intelligent_selection_tab(self):
    """创建智能模型选择标签页"""
    tab_widget = QWidget()
    layout = QVBoxLayout(tab_widget)
    
    # 创建标签页
    sub_tabs = QTabWidget()
    
    # 控制面板
    control_panel = IntelligentModelControlPanel()
    sub_tabs.addTab(control_panel, "控制面板")
    
    # 市场监控
    market_monitor = MarketStateMonitor()
    sub_tabs.addTab(market_monitor, "市场监控")
    
    # 性能展示
    performance_panel = ModelPerformancePanel()
    sub_tabs.addTab(performance_panel, "性能展示")
    
    # 结果展示
    results_panel = PredictionResultsPanel()
    sub_tabs.addTab(results_panel, "结果展示")
    
    layout.addWidget(sub_tabs)
    
    return tab_widget
```

### 2. 服务集成

#### 在AI预测服务中集成UI回调
```python
# 修改 core/services/ai_prediction_service.py
class AIPredictionService:
    def __init__(self, config: Dict[str, Any]):
        # ... 现有初始化代码 ...
        
        # UI回调接口
        self.ui_callbacks = {
            'on_selection_update': [],
            'on_performance_update': [],
            'on_result_display': []
        }
    
    def register_ui_callback(self, callback_type: str, callback_func: Callable):
        """注册UI回调函数"""
        if callback_type in self.ui_callbacks:
            self.ui_callbacks[callback_type].append(callback_func)
    
    def _notify_ui_updates(self, callback_type: str, data: Dict[str, Any]):
        """通知UI更新"""
        if callback_type in self.ui_callbacks:
            for callback in self.ui_callbacks[callback_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"UI回调执行失败: {e}")
    
    def intelligent_predict_with_ui(self, prediction_type: str, data: Dict[str, Any]):
        """带UI通知的智能预测"""
        # 执行智能预测
        result = self.intelligent_selector.intelligent_predict(prediction_type, data)
        
        # 通知UI更新
        self._notify_ui_updates('on_result_display', result)
        
        return result
```

### 3. 配置管理

#### 统一配置管理
```python
# 创建 gui/config/intelligent_selection_config.py
class IntelligentSelectionConfig:
    """智能模型选择UI配置"""
    
    DEFAULT_CONFIG = {
        'ui': {
            'theme': 'modern',
            'refresh_interval': 5000,  # 5秒刷新
            'chart_animation': True,
            'show_tooltips': True,
            'auto_hide_inactive': True
        },
        'panels': {
            'control_panel': {
                'show_status_overview': True,
                'config_expanded': True,
                'quick_controls_visible': True
            },
            'market_monitor': {
                'show_volatility_chart': True,
                'show_trend_chart': True,
                'show_liquidity_chart': True,
                'alert_threshold': 0.8
            },
            'performance_panel': {
                'auto_refresh': True,
                'chart_types': ['accuracy', 'speed', 'stability'],
                'show_recommendation': True
            },
            'results_panel': {
                'show_reasoning': True,
                'show_fusion_details': True,
                'enable_detail_requests': True
            }
        },
        'styling': {
            'primary_color': '#3498db',
            'success_color': '#27ae60',
            'warning_color': '#f39c12',
            'error_color': '#e74c3c',
            'font_family': 'Microsoft YaHei UI',
            'font_sizes': {
                'title': 12,
                'subtitle': 10,
                'body': 9,
                'caption': 8
            }
        }
    }
    
    @classmethod
    def get_panel_config(cls, panel_name: str) -> Dict[str, Any]:
        """获取特定面板配置"""
        config = cls.DEFAULT_CONFIG.copy()
        panel_config = config['panels'].get(panel_name, {})
        config.update(panel_config)
        return config
```

## 使用示例

### 完整集成示例
```python
def setup_intelligent_selection_ui():
    """设置智能模型选择UI"""
    
    # 1. 获取AI预测服务
    ai_service = get_ai_prediction_service()
    
    # 2. 创建控制面板
    control_panel = IntelligentModelControlPanel()
    control_panel.intelligent_selector = ai_service.intelligent_selector
    
    # 3. 创建市场监控
    market_monitor = MarketStateMonitor()
    market_monitor.market_detector = ai_service.intelligent_selector.market_detector
    
    # 4. 创建性能展示
    performance_panel = ModelPerformancePanel()
    performance_panel.performance_evaluator = ai_service.intelligent_selector.performance_evaluator
    
    # 5. 创建结果展示
    results_panel = PredictionResultsPanel()
    
    # 6. 建立连接
    def on_selection_update(data):
        market_monitor.update_market_state(data.get('market_state', {}))
        performance_panel.update_model_performance(data.get('model_performance', {}))
    
    def on_performance_update(data):
        performance_panel.update_model_performance(data)
    
    def on_result_display(result):
        results_panel.display_prediction_result(result)
    
    # 7. 注册回调
    ai_service.register_ui_callback('on_selection_update', on_selection_update)
    ai_service.register_ui_callback('on_performance_update', on_performance_update)
    ai_service.register_ui_callback('on_result_display', on_result_display)
    
    return {
        'control_panel': control_panel,
        'market_monitor': market_monitor,
        'performance_panel': performance_panel,
        'results_panel': results_panel
    }
```

## 总结

智能模型选择机制的UI设计方案具备以下特点：

1. **完整的功能覆盖**: 控制面板、监控、结果展示全方位覆盖
2. **一致的视觉风格**: 基于现有统一设计系统
3. **模块化设计**: 各个组件独立，便于维护和扩展
4. **实时交互**: 支持实时数据更新和用户操作反馈
5. **智能建议**: 提供基于数据的智能决策建议
6. **易用性**: 直观的界面设计和操作流程

通过这套UI设计，用户可以全面掌控智能模型选择机制的工作状态，实时监控系统性能，并获得智能化的决策支持。