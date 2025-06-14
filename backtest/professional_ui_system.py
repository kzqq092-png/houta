"""
专业级回测UI系统
提供实时图表、交互式仪表板、多维度数据展示
对标Bloomberg Terminal、Wind、TradingView等专业平台UI标准
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import asyncio
import threading
import queue
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from pathlib import Path
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
from core.logger import LogManager, LogLevel
from backtest.real_time_backtest_monitor import RealTimeBacktestMonitor, MonitoringLevel
from backtest.ultra_performance_optimizer import UltraPerformanceOptimizer, PerformanceLevel
from backtest.unified_backtest_engine import UnifiedBacktestEngine, BacktestLevel


class UITheme:
    """UI主题配置"""

    # 专业深色主题（对标Bloomberg）
    PROFESSIONAL_DARK = {
        "background": "#0E1117",
        "secondary_background": "#1E2329",
        "text_primary": "#FFFFFF",
        "text_secondary": "#B0B3B8",
        "accent_blue": "#00D4FF",
        "accent_green": "#00FF88",
        "accent_red": "#FF4B4B",
        "accent_yellow": "#FFD700",
        "accent_purple": "#8B5CF6",
        "border": "#2D3748",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
        "info": "#3B82F6"
    }

    # 专业浅色主题（对标Wind）
    PROFESSIONAL_LIGHT = {
        "background": "#FFFFFF",
        "secondary_background": "#F8F9FA",
        "text_primary": "#1A202C",
        "text_secondary": "#4A5568",
        "accent_blue": "#0066CC",
        "accent_green": "#00AA44",
        "accent_red": "#CC0000",
        "accent_yellow": "#FF8800",
        "accent_purple": "#6B46C1",
        "border": "#E2E8F0",
        "success": "#059669",
        "warning": "#D97706",
        "error": "#DC2626",
        "info": "#2563EB"
    }


class ProfessionalUISystem:
    """
    专业级回测UI系统
    提供Bloomberg Terminal级别的用户体�?
    """

    def __init__(self, theme: str = "dark"):
        """
        初始化专业UI系统

        Args:
            theme: UI主题 ("dark" �?"light")
        """
        self.theme = UITheme.PROFESSIONAL_DARK if theme == "dark" else UITheme.PROFESSIONAL_LIGHT
        self.data_queue = queue.Queue()
        self.update_thread = None
        self.is_running = False
        self.log_manager = LogManager()

        # 配置Streamlit页面
        self._configure_streamlit()

        # 初始化状�?
        if 'backtest_results' not in st.session_state:
            st.session_state.backtest_results = {}
        if 'monitoring_data' not in st.session_state:
            st.session_state.monitoring_data = []
        if 'selected_metrics' not in st.session_state:
            st.session_state.selected_metrics = ['cumulative_return', 'drawdown', 'sharpe_ratio']
        if 'alerts' not in st.session_state:
            st.session_state.alerts = []
        if 'backtest_engine' not in st.session_state:
            st.session_state.backtest_engine = None
        if 'monitor' not in st.session_state:
            st.session_state.monitor = None

    def _configure_streamlit(self):
        """配置Streamlit页面"""
        st.set_page_config(
            page_title="HIkyuu Professional Backtest System",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        # 自定义CSS样式
        self._inject_custom_css()

    def _inject_custom_css(self):
        """注入自定义CSS样式"""
        css = f"""
        <style>
        /* 主题色彩 */
        .stApp {{
            background-color: {self.theme["background"]};
            color: {self.theme["text_primary"]};
        }}
        
        /* 侧边栏样�?*/
        .css-1d391kg {{
            background-color: {self.theme["secondary_background"]};
        }}
        
        /* 指标卡片样式 */
        .metric-card {{
            background: linear-gradient(135deg, {self.theme["secondary_background"]}, {self.theme["border"]});
            padding: 20px;
            border-radius: 10px;
            border: 1px solid {self.theme["border"]};
            margin: 10px 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        /* 成功指标 */
        .metric-success {{
            border-left: 4px solid {self.theme["success"]};
        }}
        
        /* 警告指标 */
        .metric-warning {{
            border-left: 4px solid {self.theme["warning"]};
        }}
        
        /* 错误指标 */
        .metric-error {{
            border-left: 4px solid {self.theme["error"]};
        }}
        
        /* 标题样式 */
        .main-title {{
            color: {self.theme["accent_blue"]};
            font-size: 2.5rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        /* 子标题样�?*/
        .sub-title {{
            color: {self.theme["accent_green"]};
            font-size: 1.5rem;
            font-weight: 600;
            margin: 20px 0 10px 0;
            border-bottom: 2px solid {self.theme["accent_green"]};
            padding-bottom: 5px;
        }}
        
        /* 状态指示器 */
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        
        .status-running {{
            background-color: {self.theme["success"]};
            animation: pulse 2s infinite;
        }}
        
        .status-stopped {{
            background-color: {self.theme["error"]};
        }}
        
        .status-warning {{
            background-color: {self.theme["warning"]};
        }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
            100% {{ opacity: 1; }}
        }}
        
        /* 按钮样式 */
        .stButton > button {{
            background: linear-gradient(45deg, {self.theme["accent_blue"]}, {self.theme["accent_purple"]});
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        
        /* 选择框样�?*/
        .stSelectbox > div > div {{
            background-color: {self.theme["secondary_background"]};
            border: 1px solid {self.theme["border"]};
        }}
        
        /* 数据表格样式 */
        .dataframe {{
            background-color: {self.theme["secondary_background"]};
            border: 1px solid {self.theme["border"]};
        }}
        
        /* 图表容器 */
        .chart-container {{
            background-color: {self.theme["secondary_background"]};
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            border: 1px solid {self.theme["border"]};
        }}
        
        /* 实时数据�?*/
        .real-time-data {{
            background: linear-gradient(90deg, {self.theme["accent_blue"]}22, {self.theme["accent_green"]}22);
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid {self.theme["accent_blue"]};
        }}
        
        /* 预警消息 */
        .alert-critical {{
            background-color: {self.theme["error"]}22;
            border: 1px solid {self.theme["error"]};
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        
        .alert-warning {{
            background-color: {self.theme["warning"]}22;
            border: 1px solid {self.theme["warning"]};
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        
        .alert-info {{
            background-color: {self.theme["info"]}22;
            border: 1px solid {self.theme["info"]};
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        
        /* 滚动条样�?*/
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: {self.theme["secondary_background"]};
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: {self.theme["accent_blue"]};
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: {self.theme["accent_purple"]};
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

    def render_main_dashboard(self):
        """渲染主仪表板"""
        # 主标�?
        st.markdown('<h1 class="main-title">📈 HIkyuu Professional Backtest System</h1>', unsafe_allow_html=True)

        # 顶部状态栏
        self._render_status_bar()

        # 主要内容区域
        col1, col2, col3 = st.columns([2, 3, 2])

        with col1:
            self._render_control_panel()
            self._render_metrics_summary()

        with col2:
            self._render_main_charts()

        with col3:
            self._render_real_time_monitor()
            self._render_alerts_panel()

    def _render_status_bar(self):
        """渲染状态栏"""
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            status = "运行中" if self.is_running else "已停止"
            status_class = "status-running" if self.is_running else "status-stopped"
            st.markdown(
                f'<div class="real-time-data"><span class="status-indicator {status_class}"></span>系统状态: {status}</div>',
                unsafe_allow_html=True
            )

        with col2:
            current_time = datetime.now().strftime("%H:%M:%S")
            st.markdown(f'<div class="real-time-data">⏰ 当前时间: {current_time}</div>', unsafe_allow_html=True)

        with col3:
            if st.session_state.backtest_results:
                latest_result = list(st.session_state.backtest_results.values())[-1]
                risk_metrics = latest_result.get('risk_metrics', {})
                sharpe = getattr(risk_metrics, 'sharpe_ratio', 0) if hasattr(risk_metrics, 'sharpe_ratio') else risk_metrics.get('sharpe_ratio', 0)
                st.markdown(f'<div class="real-time-data">📊 Sharpe比率: {sharpe:.3f}</div>', unsafe_allow_html=True)

        with col4:
            if st.session_state.monitoring_data:
                latest_data = st.session_state.monitoring_data[-1]
                return_rate = latest_data.get('cumulative_return', 0) * 100
                color = self.theme["success"] if return_rate >= 0 else self.theme["error"]
                st.markdown(
                    f'<div class="real-time-data">💰 累积收益: <span style="color:{color}">{return_rate:.2f}%</span></div>',
                    unsafe_allow_html=True
                )

        with col5:
            if st.session_state.monitoring_data:
                latest_data = st.session_state.monitoring_data[-1]
                drawdown = latest_data.get('max_drawdown', 0) * 100
                st.markdown(f'<div class="real-time-data">📉 最大回撤: {drawdown:.2f}%</div>', unsafe_allow_html=True)

    def _render_control_panel(self):
        """渲染控制面板"""
        st.markdown('<h3 class="sub-title">🎛�?控制面板</h3>', unsafe_allow_html=True)

        with st.container():
            # 回测参数设置
            st.subheader("回测参数")

            initial_capital = st.number_input("初始资金", min_value=10000, max_value=10000000, value=1000000, step=10000)
            position_size = st.slider("仓位大小", min_value=0.1, max_value=1.0, value=0.95, step=0.05)
            commission_pct = st.number_input("手续费率", min_value=0.0001, max_value=0.01, value=0.0003, step=0.0001, format="%.4f")

            # 专业级别选择
            professional_level = st.selectbox(
                "专业级别",
                options=["RETAIL", "INSTITUTIONAL", "HEDGE_FUND", "INVESTMENT_BANK"],
                index=3,
                help="选择回测的专业级别，影响计算精度和指标数量"
            )

            # 性能级别选择
            performance_level = st.selectbox(
                "性能级别",
                options=["STANDARD", "HIGH", "ULTRA", "EXTREME"],
                index=2,
                help="选择性能优化级别，影响计算速度"
            )

            # 监控级别选择
            monitoring_level = st.selectbox(
                "监控级别",
                options=["BASIC", "STANDARD", "ADVANCED", "REAL_TIME"],
                index=3,
                help="选择实时监控级别"
            )

            # 控制按钮
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 开始回测", use_container_width=True):
                    self._start_backtest(initial_capital, position_size, commission_pct, professional_level, performance_level)

            with col2:
                if st.button("⏹️ 停止监控", use_container_width=True):
                    self._stop_monitoring()

    def _render_metrics_summary(self):
        """渲染指标摘要"""
        st.markdown('<h3 class="sub-title">📊 关键指标</h3>', unsafe_allow_html=True)

        if st.session_state.backtest_results:
            latest_result = list(st.session_state.backtest_results.values())[-1]
            risk_metrics = latest_result.get('risk_metrics', {})

            # 处理风险指标（可能是对象或字典）
            if hasattr(risk_metrics, '__dict__'):
                # 如果是对象，转换为字�?
                metrics_dict = risk_metrics.__dict__
            else:
                # 如果已经是字�?
                metrics_dict = risk_metrics

            # 收益指标
            total_return = metrics_dict.get('total_return', 0)
            annualized_return = metrics_dict.get('annualized_return', 0)

            metric_class = "metric-success" if total_return >= 0 else "metric-error"
            st.markdown(f'''
            <div class="metric-card {metric_class}">
                <h4>💰 总收益率</h4>
                <h2>{total_return:.2%}</h2>
                <p>年化收益: {annualized_return:.2%}</p>
            </div>
            ''', unsafe_allow_html=True)

            # 风险指标
            sharpe_ratio = metrics_dict.get('sharpe_ratio', 0)
            max_drawdown = metrics_dict.get('max_drawdown', 0)

            metric_class = "metric-success" if sharpe_ratio >= 1.0 else "metric-warning" if sharpe_ratio >= 0.5 else "metric-error"
            st.markdown(f'''
            <div class="metric-card {metric_class}">
                <h4>📈 Sharpe比率</h4>
                <h2>{sharpe_ratio:.3f}</h2>
                <p>最大回撤: {max_drawdown:.2%}</p>
            </div>
            ''', unsafe_allow_html=True)

            # 交易指标
            win_rate = metrics_dict.get('win_rate', 0)
            profit_factor = metrics_dict.get('profit_factor', 0)

            metric_class = "metric-success" if win_rate >= 0.5 else "metric-warning" if win_rate >= 0.4 else "metric-error"
            st.markdown(f'''
            <div class="metric-card {metric_class}">
                <h4>🎯 胜率</h4>
                <h2>{win_rate:.2%}</h2>
                <p>盈利因子: {profit_factor:.2f}</p>
            </div>
            ''', unsafe_allow_html=True)

    def _render_main_charts(self):
        """渲染主要图表"""
        st.markdown('<h3 class="sub-title">📈 实时图表</h3>', unsafe_allow_html=True)

        # 图表选项�?
        tab1, tab2, tab3, tab4 = st.tabs(["📊 收益分析", "⚠️ 风险分析", "💹 交易分析", "🔧 性能分析"])

        with tab1:
            self._render_performance_charts()

        with tab2:
            self._render_risk_charts()

        with tab3:
            self._render_trading_charts()

        with tab4:
            self._render_performance_analysis_charts()

    def _render_performance_charts(self):
        """渲染收益分析图表"""
        if not st.session_state.monitoring_data:
            st.info("暂无监控数据，请先开始回测")
            return

        # 准备数据
        df = pd.DataFrame(st.session_state.monitoring_data)
        if df.empty:
            st.warning("监控数据为空")
            return

        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=["累积收益率", "回撤分析", "收益分布", "滚动Sharpe比率"],
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )

        # 累积收益率
        if 'cumulative_return' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['cumulative_return'] * 100,
                    name="累积收益率",
                    line=dict(color=self.theme["accent_green"], width=2)
                ),
                row=1, col=1
            )

        # 回撤分析
        if 'current_drawdown' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['current_drawdown'] * 100,
                    name="回撤分析",
                    fill='tonexty',
                    line=dict(color=self.theme["accent_red"], width=1)
                ),
                row=1, col=2
            )

        # 收益分布
        if 'current_return' in df.columns:
            fig.add_trace(
                go.Histogram(
                    x=df['current_return'] * 100,
                    name="收益分布",
                    marker_color=self.theme["accent_blue"],
                    opacity=0.7
                ),
                row=2, col=1
            )

        # 滚动Sharpe比率
        if 'sharpe_ratio' in df.columns and len(df) > 20:
            rolling_sharpe = df['sharpe_ratio'].rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=rolling_sharpe,
                    name="滚动Sharpe",
                    line=dict(color=self.theme["accent_purple"], width=2)
                ),
                row=2, col=2
            )

        # 更新布局
        fig.update_layout(
            height=600,
            showlegend=True,
            title_text="收益分析仪表板",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text_primary"]
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_risk_charts(self):
        """渲染风险分析图表"""
        if not st.session_state.monitoring_data:
            st.info("暂无监控数据，请先开始回测")
            return

        df = pd.DataFrame(st.session_state.monitoring_data)
        if df.empty:
            st.warning("监控数据为空")
            return

        # 创建风险分析图表
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=["VaR分析", "波动率分析", "风险调整收益", "回撤持续期"],
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )

        # VaR分析
        if 'var_95' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['var_95'] * 100,
                    name="VaR分析",
                    line=dict(color=self.theme["accent_red"], width=2)
                ),
                row=1, col=1
            )

        # 波动率分析
        if 'volatility' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['volatility'] * 100,
                    name="波动率分析",
                    line=dict(color=self.theme["accent_yellow"], width=2)
                ),
                row=1, col=2
            )

        # 风险调整收益
        if 'sharpe_ratio' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['sharpe_ratio'],
                    name="风险调整收益",
                    line=dict(color=self.theme["accent_blue"], width=2)
                ),
                row=2, col=1
            )

        # 回撤持续期
        if 'current_drawdown' in df.columns:
            drawdown_duration = self._calculate_drawdown_duration(df['current_drawdown'])
            fig.add_trace(
                go.Bar(
                    x=list(range(len(drawdown_duration))),
                    y=drawdown_duration,
                    name="回撤持续期",
                    marker_color=self.theme["accent_purple"]
                ),
                row=2, col=2
            )

        # 更新布局
        fig.update_layout(
            height=600,
            showlegend=True,
            title_text="风险分析仪表板",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text_primary"]
        )

        st.plotly_chart(fig, use_container_width=True)

    def _calculate_drawdown_duration(self, drawdown_series: pd.Series) -> List[int]:
        """计算回撤持续期"""
        try:
            durations = []
            current_duration = 0

            for dd in drawdown_series:
                if dd < 0:
                    current_duration += 1
                else:
                    if current_duration > 0:
                        durations.append(current_duration)
                        current_duration = 0

            # 处理最后一个回撤期
            if current_duration > 0:
                durations.append(current_duration)

            return durations if durations else [0]
        except Exception:
            return [0]

    def _render_trading_charts(self):
        """渲染交易分析图表"""
        if not st.session_state.backtest_results:
            st.info("暂无回测结果，请先开始回测")
            return

        latest_result = list(st.session_state.backtest_results.values())[-1]
        backtest_df = latest_result.get('backtest_result', pd.DataFrame())

        if backtest_df.empty:
            st.warning("回测结果为空")
            return

        # 创建交易分析图表
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=["持仓变化", "交易信号", "资金曲线", "收益分布"],
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )

        # 持仓变化
        if 'position' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['position'],
                    name="持仓变化",
                    line=dict(color=self.theme["accent_green"], width=2)
                ),
                row=1, col=1
            )

        # 交易信号
        if 'trades' in backtest_df.columns:
            buy_signals = backtest_df[backtest_df['trades'] == 1]
            sell_signals = backtest_df[backtest_df['trades'] == -1]

            if not buy_signals.empty:
                fig.add_trace(
                    go.Scatter(
                        x=buy_signals.index,
                        y=[1] * len(buy_signals),
                        mode='markers',
                        name="买入信号",
                        marker=dict(color=self.theme["accent_green"], size=10, symbol='triangle-up')
                    ),
                    row=1, col=2
                )

            if not sell_signals.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sell_signals.index,
                        y=[-1] * len(sell_signals),
                        mode='markers',
                        name="卖出信号",
                        marker=dict(color=self.theme["accent_red"], size=10, symbol='triangle-down')
                    ),
                    row=1, col=2
                )

        # 资金曲线
        if 'capital' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['capital'],
                    name="资金曲线",
                    line=dict(color=self.theme["accent_blue"], width=2)
                ),
                row=2, col=1
            )

        # 收益分布
        if 'returns' in backtest_df.columns:
            returns = backtest_df['returns'].dropna()
            if not returns.empty:
                fig.add_trace(
                    go.Histogram(
                        x=returns * 100,
                        name="收益分布",
                        marker_color=self.theme["accent_purple"],
                        opacity=0.7
                    ),
                    row=2, col=2
                )

        # 更新布局
        fig.update_layout(
            height=600,
            showlegend=True,
            title_text="交易分析仪表板",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text_primary"]
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_performance_analysis_charts(self):
        """渲染性能分析图表"""
        if not st.session_state.backtest_results:
            st.info("暂无回测结果，请先开始回测")
            return

        latest_result = list(st.session_state.backtest_results.values())[-1]
        performance_metrics = latest_result.get('performance_metrics', {})

        # 创建性能分析图表
        col1, col2 = st.columns(2)

        with col1:
            # 执行时间分析
            execution_time = performance_metrics.get('execution_time', 0)
            st.metric("执行时间", f"{execution_time:.3f}秒")

            # 内存使用分析
            memory_usage = performance_metrics.get('memory_usage', 0)
            st.metric("内存使用", f"{memory_usage:.2f}MB")

        with col2:
            # CPU使用?
            cpu_usage = performance_metrics.get('cpu_usage', 0)
            st.metric("CPU使用率", f"{cpu_usage:.1f}%")

            # 向量化比?
            vectorization_ratio = performance_metrics.get('vectorization_ratio', 0)
            st.metric("向量化比率", f"{vectorization_ratio:.2%}")

        # 性能趋势图
        if st.session_state.monitoring_data:
            df = pd.DataFrame(st.session_state.monitoring_data)
            if 'execution_time' in df.columns:
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df['execution_time'],
                        name="执行时间",
                        line=dict(color=self.theme["accent_blue"], width=2)
                    )
                )

                fig.update_layout(
                    title="性能趋势分析",
                    xaxis_title="时间",
                    yaxis_title="执行时间(秒)",
                    plot_bgcolor=self.theme["background"],
                    paper_bgcolor=self.theme["background"],
                    font_color=self.theme["text_primary"]
                )

                st.plotly_chart(fig, use_container_width=True)

    def _render_real_time_monitor(self):
        """渲染实时监控面板"""
        st.markdown('<h3 class="sub-title">📡 实时监控</h3>', unsafe_allow_html=True)

        # 监控状态
        if self.is_running:
            st.success("🟢 实时监控运行中")
        else:
            st.error("🔴 实时监控已停止")

        # 最新指标
        if st.session_state.monitoring_data:
            latest_data = st.session_state.monitoring_data[-1]

            # 实时指标显示
            col1, col2 = st.columns(2)

            with col1:
                current_return = latest_data.get('current_return', 0)
                color = "green" if current_return >= 0 else "red"
                st.markdown(f"**当前收益:** :{color}[{current_return:.2%}]")

                sharpe = latest_data.get('sharpe_ratio', 0)
                st.markdown(f"**Sharpe比率:** {sharpe:.3f}")

            with col2:
                drawdown = latest_data.get('current_drawdown', 0)
                st.markdown(f"**当前回撤:** :red[{drawdown:.2%}]")

                volatility = latest_data.get('volatility', 0)
                st.markdown(f"**波动率:** {volatility:.2%}")

        # 监控历史
        if len(st.session_state.monitoring_data) > 1:
            df = pd.DataFrame(st.session_state.monitoring_data[-20:])  # 显示最近20个数据点

            # 简化的实时图表
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['cumulative_return'] * 100,
                    name="累积收益",
                    line=dict(color=self.theme["accent_green"], width=2)
                )
            )

            fig.update_layout(
                height=300,
                title="实时收益曲线",
                showlegend=False,
                plot_bgcolor=self.theme["background"],
                paper_bgcolor=self.theme["background"],
                font_color=self.theme["text_primary"],
                margin=dict(l=0, r=0, t=30, b=0)
            )

            st.plotly_chart(fig, use_container_width=True)

    def _render_alerts_panel(self):
        """渲染预警面板"""
        st.markdown('<h3 class="sub-title">⚠️ 预警中心</h3>', unsafe_allow_html=True)

        # 获取当前预警
        current_alerts = self._get_current_alerts()

        if not current_alerts:
            st.info("暂无预警信息")
            return

        # 显示预警
        for alert in current_alerts[-5:]:  # 显示最近5个预警
            level = alert.get('level', 'info')
            message = alert.get('message', '')
            timestamp = alert.get('timestamp', datetime.now())

            if level == 'critical':
                alert_class = 'alert-critical'
                icon = '🚨'
            elif level == 'warning':
                alert_class = 'alert-warning'
                icon = '⚠️'
            else:
                alert_class = 'alert-info'
                icon = 'ℹ️'

            st.markdown(f'''
            <div class="{alert_class}">
                <strong>{icon} {level.upper()}</strong><br>
                {message}<br>
                <small>{timestamp.strftime("%H:%M:%S")}</small>
            </div>
            ''', unsafe_allow_html=True)

    def _get_current_alerts(self) -> List[Dict]:
        """获取当前预警信息"""
        alerts = []

        if st.session_state.monitoring_data:
            latest_data = st.session_state.monitoring_data[-1]

            # 检查回撤预警
            drawdown = latest_data.get('current_drawdown', 0)
            if drawdown > 0.1:  # 回撤超过10%
                alerts.append({
                    'level': 'critical' if drawdown > 0.2 else 'warning',
                    'message': f'回撤过大: {drawdown:.2%}',
                    'timestamp': datetime.now()
                })

            # 检查Sharpe比率预警
            sharpe = latest_data.get('sharpe_ratio', 0)
            if sharpe < 0:
                alerts.append({
                    'level': 'warning',
                    'message': f'Sharpe比率为负: {sharpe:.3f}',
                    'timestamp': datetime.now()
                })

            # 检查波动率预警
            volatility = latest_data.get('volatility', 0)
            if volatility > 0.3:  # 波动率超过30%
                alerts.append({
                    'level': 'warning',
                    'message': f'波动率过高: {volatility:.2%}',
                    'timestamp': datetime.now()
                })

        return alerts

    def _start_backtest(self, initial_capital: float, position_size: float,
                        commission_pct: float, professional_level: str, performance_level: str):
        """开始回测"""
        try:
            st.info("正在启动回测...")

            # 生成模拟数据进行演示
            backtest_result = self._generate_mock_backtest_result(initial_capital)

            # 存储结果
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.backtest_results[timestamp] = backtest_result

            # 启动实时监控
            self._start_real_time_monitoring()

            st.success("回测启动成功！")

        except Exception as e:
            st.error(f"回测启动失败: {str(e)}")
            self.log_manager.log(f"回测启动失败: {e}", LogLevel.ERROR)

    def _generate_mock_backtest_result(self, initial_capital: float) -> Dict:
        """生成模拟回测结果用于演示"""
        try:
            # 生成模拟数据
            dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
            n_days = len(dates)

            # 模拟价格数据
            np.random.seed(42)
            returns = np.random.normal(0.0005, 0.02, n_days)  # 日收益率
            prices = 100 * np.cumprod(1 + returns)

            # 模拟交易信号
            signals = np.random.choice([-1, 0, 1], n_days, p=[0.1, 0.8, 0.1])

            # 创建DataFrame
            backtest_df = pd.DataFrame({
                'close': prices,
                'signal': signals,
                'returns': returns,
                'position': np.random.uniform(0, 1000, n_days),
                'capital': initial_capital * np.cumprod(1 + returns),
                'trades': np.random.choice([0, 1, -1], n_days, p=[0.9, 0.05, 0.05])
            }, index=dates)

            # 计算风险指标
            total_return = (backtest_df['capital'].iloc[-1] / initial_capital) - 1
            annualized_return = (1 + total_return) ** (252 / n_days) - 1
            volatility = returns.std() * np.sqrt(252)
            sharpe_ratio = annualized_return / volatility if volatility != 0 else 0

            # 计算最大回撤
            cumulative = backtest_df['capital'] / initial_capital
            running_max = cumulative.cummax()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = abs(drawdown.min())

            # 模拟风险指标对象
            class MockRiskMetrics:
                def __init__(self):
                    self.total_return = total_return
                    self.annualized_return = annualized_return
                    self.volatility = volatility
                    self.sharpe_ratio = sharpe_ratio
                    self.max_drawdown = max_drawdown
                    self.win_rate = 0.55
                    self.profit_factor = 1.2
                    self.var_95 = np.percentile(returns, 5)
                    self.sortino_ratio = sharpe_ratio * 1.2
                    self.calmar_ratio = annualized_return / max_drawdown if max_drawdown != 0 else 0

            return {
                'backtest_result': backtest_df,
                'risk_metrics': MockRiskMetrics(),
                'performance_metrics': {
                    'execution_time': np.random.uniform(0.5, 2.0),
                    'memory_usage': np.random.uniform(50, 200),
                    'cpu_usage': np.random.uniform(20, 80),
                    'vectorization_ratio': np.random.uniform(0.8, 1.0)
                },
                'trade_statistics': {
                    'total_trades': int(np.sum(signals != 0)),
                    'win_rate': 0.55,
                    'profit_factor': 1.2
                }
            }

        except Exception as e:
            self.log_manager.log(f"生成模拟回测结果失败: {e}", LogLevel.ERROR)
            return {}

    def _start_real_time_monitoring(self):
        """启动实时监控"""
        if self.is_running:
            return

        self.is_running = True

        def monitoring_loop():
            """监控循环"""
            while self.is_running:
                try:
                    # 生成模拟监控数据
                    current_time = datetime.now()

                    # 模拟实时指标
                    monitoring_data = {
                        'timestamp': current_time,
                        'current_return': np.random.normal(0.001, 0.02),
                        'cumulative_return': np.random.uniform(-0.1, 0.3),
                        'current_drawdown': np.random.uniform(0, 0.15),
                        'max_drawdown': np.random.uniform(0.05, 0.2),
                        'sharpe_ratio': np.random.uniform(-0.5, 2.5),
                        'volatility': np.random.uniform(0.1, 0.4),
                        'var_95': np.random.uniform(-0.05, -0.01),
                        'execution_time': np.random.uniform(0.1, 1.0)
                    }

                    # 添加到监控数据
                    st.session_state.monitoring_data.append(monitoring_data)

                    # 保持最近1000个数据点
                    if len(st.session_state.monitoring_data) > 1000:
                        st.session_state.monitoring_data = st.session_state.monitoring_data[-1000:]

                    time.sleep(2)  # 每2秒更新一次

                except Exception as e:
                    self.log_manager.log(f"监控循环异常: {e}", LogLevel.ERROR)
                    break

        # 启动监控线程
        self.update_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.update_thread.start()

    def _stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1)

    def run(self):
        """运行UI系统"""
        self.render_main_dashboard()


def create_professional_ui(theme: str = "dark") -> ProfessionalUISystem:
    """创建专业UI系统实例"""
    return ProfessionalUISystem(theme)


def run_professional_ui():
    """运行专业UI系统"""
    ui_system = create_professional_ui()
    ui_system.run()


if __name__ == "__main__":
    run_professional_ui()
