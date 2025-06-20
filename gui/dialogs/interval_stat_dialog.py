import pandas as pd
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import sys
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QHBoxLayout, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QFrame, QProgressBar, QComboBox
from PyQt5.QtCore import Qt
import matplotlib
from .interval_stat_settings_dialog import IntervalStatSettingsDialog, load_settings
matplotlib.use('Agg')


class IntervalStatDialog(QDialog):
    """
    区间统计弹窗，支持多Tab和专业可视化
    """

    def __init__(self, sub_df: pd.DataFrame, stat: dict, parent=None, theme='light', custom_rules=None, multi_period_stats=None):
        super().__init__(parent)
        self.setWindowTitle("区间统计分析")
        self.setMinimumSize(900, 650)
        self.theme = theme
        self.sub_df = sub_df
        self.stat = stat
        self.custom_rules = custom_rules or {}
        self.multi_period_stats = multi_period_stats or {}
        self.current_period = list(self.multi_period_stats.keys())[
            0] if self.multi_period_stats else None
        self.score_weights = None
        self.init_ui()

    def init_ui(self):
        # 全局QSS美化
        self.setStyleSheet('''
            QProgressBar {
                border-radius: 2px;
                background: #e3f2fd;
                height: 14px;
                font-size: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 2px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #43a047, stop:1 #81c784);
            }
            QProgressBar[risk="true"]::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d32f2f, stop:1 #ff8a65);
            }
        ''')
        layout = QVBoxLayout(self)
        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.setFixedWidth(40)
        settings_btn.setFixedHeight(25)
        settings_btn.clicked.connect(self.open_settings)
        top_hbox = QHBoxLayout()
        top_hbox.addStretch()
        top_hbox.addWidget(settings_btn)
        layout.addLayout(top_hbox)
        # 多周期切换
        settings = load_settings()
        self.custom_rules = {
            'strong_bull': settings['strong_bull'],
            'strong_bear': settings['strong_bear'],
            'extreme_volatility': settings['extreme_volatility'],
            'max_drawdown': settings['max_drawdown']
        }
        self.score_weights = settings['score_weights']
        periods = settings['periods']
        if self.multi_period_stats:
            period_layout = QHBoxLayout()
            period_label = QLabel("选择周期：")
            self.period_combo = QComboBox()
            self.period_combo.addItems([str(p) for p in periods])
            self.period_combo.currentTextChanged.connect(
                self.on_period_changed)
            period_layout.addWidget(period_label)
            period_layout.addWidget(self.period_combo)
            period_layout.addStretch()
            layout.addLayout(period_layout)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)
        # Tab1: 统计总览
        self.tabs.addTab(self.create_overview_tab(), "统计总览")
        # Tab2: 区间K线小图
        self.tabs.addTab(self.create_kline_tab(), "区间K线")
        # Tab3: 涨跌分布
        self.tabs.addTab(self.create_updown_tab(), "涨跌分布")
        # Tab4: 收益率分布
        self.tabs.addTab(self.create_return_hist_tab(), "收益率分布")
        # Tab5: 成交量分布
        self.tabs.addTab(self.create_volume_hist_tab(), "成交量分布")
        # 导出按钮
        btn_layout = QHBoxLayout()
        export_img_btn = QPushButton("导出当前图为图片")
        export_img_btn.clicked.connect(self.export_current_tab_img)
        export_data_btn = QPushButton("导出区间数据")
        export_data_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(export_img_btn)
        btn_layout.addWidget(export_data_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def on_period_changed(self, period):
        self.current_period = period
        self.stat = self.multi_period_stats[period]['stat']
        self.sub_df = self.multi_period_stats[period]['df']
        # 刷新统计总览Tab
        self.tabs.removeTab(0)
        self.tabs.insertTab(0, self.create_overview_tab(), "统计总览")
        # 可选：刷新其它Tab

    def create_overview_tab(self):
        tab = QWidget()
        main_layout = QHBoxLayout(tab)
        main_layout.setSpacing(18)
        # 左侧：统计表格+多因子评分
        left_card = QFrame()
        left_card.setObjectName("leftCard")
        left_layout = QVBoxLayout(left_card)
        table = QTableWidget(len(self.stat), 2)
        table.setHorizontalHeaderLabels(["指标", "数值"])
        table.horizontalHeader().setFixedHeight(25)
        for i, (k, v) in enumerate(self.stat.items()):
            table.setItem(i, 0, QTableWidgetItem(str(k)))
            table.setItem(i, 1, QTableWidgetItem(
                f"{v:.4f}" if isinstance(v, float) else str(v)))
        table.resizeColumnsToContents()
        table.setFixedHeight(min(38*len(self.stat)+38, 320))
        left_layout.addWidget(table)
        # 多因子评分
        score, risk = self.calculate_scores()
        score_label = QLabel(f"多头强度评分：")
        score_bar = QProgressBar()
        score_bar.setValue(int(score))
        score_bar.setFormat(f"{int(score)}%")
        score_bar.setAlignment(Qt.AlignCenter)
        score_bar.setFixedHeight(28)
        risk_label = QLabel(f"风险评分：")
        risk_bar = QProgressBar()
        risk_bar.setValue(int(risk))
        risk_bar.setFormat(f"{int(risk)}%")
        risk_bar.setAlignment(Qt.AlignCenter)
        risk_bar.setFixedHeight(28)
        risk_bar.setProperty("risk", True)
        left_layout.addWidget(score_label)
        left_layout.addWidget(score_bar)
        left_layout.addWidget(risk_label)
        left_layout.addWidget(risk_bar)
        # 历史对比
        hist_label = QLabel(self.generate_history_compare())
        hist_label.setWordWrap(True)
        left_layout.addWidget(hist_label)
        left_layout.addStretch()
        main_layout.addWidget(left_card, 2)
        # 右侧：智能建议分组卡片
        right_card = QFrame()
        right_card.setObjectName("rightCard")
        right_card.setStyleSheet(
            "QFrame#rightCard{background:#fafdff;border-radius:12px;border:1.5px solid #90caf9;padding:18px 18px 12px 18px;}")
        advice_layout = QVBoxLayout(right_card)
        advice_title = QLabel("投资建议与风险提示")
        advice_title.setProperty("adviceTitle", True)
        advice_layout.addWidget(advice_title)
        advices = self.generate_advice()
        for group, items in advices.items():
            group_title = QLabel(group)
            group_title.setProperty("groupTitle", True)
            group_title.setStyleSheet(
                f"color:{'#388e3c' if group=='操作建议' else '#d32f2f'};")
            advice_layout.addWidget(group_title)
            for text, color, icon, bg in items:
                frame = QFrame()
                frame.setProperty("adviceCard", True)
                frame.setStyleSheet(
                    f"background:{bg};border-radius:8px;border:1.5px solid {color};padding:8px 12px;margin-bottom:10px;")
                hbox = QHBoxLayout(frame)
                icon_lbl = QLabel(icon)
                icon_lbl.setStyleSheet(
                    f"font-size:18px;margin-right:10px;color:{color};")
                hbox.addWidget(icon_lbl)
                txt_lbl = QLabel(text)
                txt_lbl.setFixedWidth(700)
                txt_lbl.setWordWrap(True)
                txt_lbl.setStyleSheet(
                    f"color:{color};font-size:15px;font-weight:bold;")
                hbox.addWidget(txt_lbl)
                hbox.addStretch()
                advice_layout.addWidget(frame)
        advice_layout.addStretch()
        main_layout.addWidget(right_card, 3)
        return tab

    def calculate_scores(self):
        stat = self.stat
        w = self.score_weights if hasattr(self, 'score_weights') else {
            'ret': 0.4, 'up_ratio': 0.2, 'mdd': 0.2, 'vol': 0.2}
        score = 50
        risk = 50
        # 涨跌幅
        ret = stat.get('涨跌幅(%)', 0)
        if ret > 0:
            score += min(ret, 20)*w['ret']
        else:
            risk += min(abs(ret), 20)*w['ret']
        # 阳线比例
        up_ratio = stat.get('阳线比例(%)', 50)
        score += (up_ratio-50)*0.5*w['up_ratio']
        # 最大回撤
        mdd = stat.get('最大回撤(%)', 0)
        risk += min(abs(mdd), 20)*w['mdd']
        # 波动率
        vol = stat.get('区间波动率(年化%)', 0)
        risk += min(vol/2, 20)*w['vol']
        # 极端波动
        max_up = stat.get('最大单日涨幅(%)', 0)
        max_down = stat.get('最大单日跌幅(%)', 0)
        if max_up > self.custom_rules.get('extreme_volatility', 9) or abs(max_down) > self.custom_rules.get('extreme_volatility', 9):
            risk += 10
        # 主力异动
        vol_mean = stat.get('成交量均值', 0)
        vol_max = stat.get('最大成交量', 0)
        if vol_max > 2 * vol_mean and vol_mean > 0:
            score += 10
        score = max(0, min(100, score))
        risk = max(0, min(100, risk))
        return score, risk

    def generate_history_compare(self):
        # 历史对比分析
        stat = self.stat
        ret = stat.get('涨跌幅(%)', 0)
        mdd = stat.get('最大回撤(%)', 0)
        vol = stat.get('区间波动率(年化%)', 0)
        # 假设有历史极值（可扩展为传入历史数据）
        hist_max_ret = 30
        hist_min_ret = -30
        hist_max_mdd = -40
        hist_max_vol = 60
        msg = ""
        if ret > hist_max_ret*0.8:
            msg += "本区间涨幅接近历史极值，行情极端，注意回调风险。"
        elif ret < hist_min_ret*0.8:
            msg += "本区间跌幅接近历史极值，空头极强，谨慎操作。"
        if abs(mdd) > abs(hist_max_mdd)*0.8:
            msg += " 最大回撤接近历史极值，风险较高。"
        if vol > hist_max_vol*0.8:
            msg += " 波动率极高，短线机会多但风险大。"
        if not msg:
            msg = "本区间各项指标处于历史常规区间。"
        return msg

    def generate_advice(self):
        """更智能的投资建议和风险提示，分组返回，支持自定义规则和多周期联动"""
        stat = self.stat
        rules = self.custom_rules or {}
        advices = {"操作建议": [], "风险提示": []}
        # --- 趋势强度 ---
        ret = stat.get('涨跌幅(%)', 0)
        up_ratio = stat.get('阳线比例(%)', 50)
        max_up_seq = stat.get('最大连续阳线', 0)
        max_down_seq = stat.get('最大连续阴线', 0)
        strong_bull = rules.get('strong_bull', 15)
        strong_bear = rules.get('strong_bear', -15)
        if ret > strong_bull and up_ratio > 65 and max_up_seq >= 4:
            advices["操作建议"].append(
                ("多头极强，顺势做多为主，关注回调低吸机会。", "#388e3c", "↑", "#e8f5e9"))
        elif ret < strong_bear and up_ratio < 35 and max_down_seq >= 4:
            advices["风险提示"].append(
                ("空头极强，谨慎抄底，防止持续下跌。", "#d32f2f", "↓", "#ffebee"))
        elif abs(ret) < 3 and abs(up_ratio-50) < 10:
            advices["操作建议"].append(
                ("区间震荡，观望为主，短线高抛低吸。", "#1976d2", "🔄", "#e3f2fd"))
        # --- 极端波动 ---
        max_up = stat.get('最大单日涨幅(%)', 0)
        max_down = stat.get('最大单日跌幅(%)', 0)
        extreme_vol = rules.get('extreme_volatility', 9)
        if max_up > extreme_vol or abs(max_down) > extreme_vol:
            advices["风险提示"].append(
                ("区间内有极端行情，注意追涨杀跌风险。", "#f57c00", "⚠️", "#fff3e0"))
        # --- 波动率与短线/长线 ---
        vol = stat.get('区间波动率(年化%)', 0)
        if vol > 40:
            advices["操作建议"].append(
                ("波动率高，短线机会多，适合快进快出。", "#fbc02d", "⚡", "#fffde7"))
        elif vol < 15:
            advices["操作建议"].append(
                ("波动率低，行情平淡，适合长线持有或等待突破。", "#616161", "⏳", "#f5f5f5"))
        # --- 最大回撤 ---
        mdd = stat.get('最大回撤(%)', 0)
        if mdd < rules.get('max_drawdown', -15):
            advices["风险提示"].append(
                ("最大回撤较大，风险高，建议严格风控。", "#c62828", "❗️", "#ffebee"))
        # --- 量价背离 ---
        vol_mean = stat.get('成交量均值', 0)
        vol_max = stat.get('最大成交量', 0)
        if ret > 5 and vol_mean > 0 and vol_max < 1.1 * vol_mean:
            advices["风险提示"].append(
                ("价格上涨但量能未放大，警惕假突破。", "#f57c00", "⚠️", "#fff3e0"))
        if ret < -5 and vol_mean > 0 and vol_max < 1.1 * vol_mean:
            advices["风险提示"].append(
                ("价格下跌但量能未放大，空头动能有限。", "#1976d2", "ℹ️", "#e3f2fd"))
        # --- 创新高/新低 ---
        close_new_high = stat.get('收盘创新高次数', 0)
        close_new_low = stat.get('收盘新低次数', 0)
        total_days = len(self.sub_df)
        if close_new_high > total_days * 0.3:
            advices["操作建议"].append(
                ("区间内多次创新高，多头突破，关注追涨机会。", "#388e3c", "🚀", "#e8f5e9"))
        if close_new_low > total_days * 0.3:
            advices["风险提示"].append(
                ("区间内多次新低，空头主导，谨慎操作。", "#d32f2f", "↓", "#ffebee"))
        # --- 主力异动 ---
        if vol_max > 2 * vol_mean and vol_mean > 0:
            advices["操作建议"].append(
                ("区间内有主力异动，关注资金流向和异动K线。", "#1976d2", "💰", "#e3f2fd"))
        # --- 多周期联动 ---
        if self.multi_period_stats and self.current_period:
            periods = list(self.multi_period_stats.keys())
            idx = periods.index(self.current_period)
            if idx > 0:
                prev_stat = self.multi_period_stats[periods[idx-1]]['stat']
                prev_ret = prev_stat.get('涨跌幅(%)', 0)
                if (ret > 0 and prev_ret > 0) or (ret < 0 and prev_ret < 0):
                    advices["操作建议"].append(
                        (f"本周期与上一级周期趋势一致（{'多头' if ret>0 else '空头'}共振），信号更强。", "#388e3c", "🔗", "#e8f5e9"))
                else:
                    advices["风险提示"].append(
                        ("本周期与上一级周期趋势背离，注意反转风险。", "#f57c00", "⚠️", "#fff3e0"))
        if not advices["操作建议"]:
            advices["操作建议"].append(
                ("暂无特别操作建议，建议结合其他周期和指标综合判断。", "#1976d2", "ℹ️", "#e3f2fd"))
        if not advices["风险提示"]:
            advices["风险提示"].append(
                ("暂无明显风险，注意仓位管理和止损。", "#388e3c", "✅", "#e8f5e9"))
        return advices

    def create_kline_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        fig, ax = plt.subplots(figsize=(7, 3))
        df = self.sub_df
        if not df.empty:
            x = np.arange(len(df))
            ax.plot(x, df['close'], label='收盘价', color='#1976d2')
            ax.fill_between(x, df['low'], df['high'],
                            color='#90caf9', alpha=0.3, label='高-低区间')
            ax.set_title('区间K线走势')
            ax.set_xlabel('序号')
            ax.set_ylabel('价格')
            # 检查是否有带标签的对象才创建图例
            handles, labels = ax.get_legend_handles_labels()
            if handles and labels:
                ax.legend()
            # 顶部显示收盘价最大/最小/均值
            close_max = df['close'].max()
            close_min = df['close'].min()
            close_mean = df['close'].mean()
            ax.text(0.5, 0.95, f"最高: {close_max:.3f}  最低: {close_min:.3f}  均值: {close_mean:.3f}",
                    transform=ax.transAxes, ha='center', va='bottom', fontsize=11, color='#1976d2')
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        return tab

    def create_updown_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        df = self.sub_df
        up = (df['close'] > df['open']).sum()
        down = (df['close'] < df['open']).sum()
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.bar(['阳线', '阴线'], [up, down], color=['#e53935', '#43a047'])
        ax.set_title('涨跌天数分布')
        # 顶部显示阳线和阴线数量
        ax.text(0.5, 0.95, f"阳线: {up} 天  阴线: {down} 天", transform=ax.transAxes, ha='center', va='bottom', fontsize=11, color='#333')
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        return tab

    def create_return_hist_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        df = self.sub_df
        returns = df['close'].pct_change().dropna() * 100
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.hist(returns, bins=20, color='#1976d2', alpha=0.7)
        ax.set_title('日收益率分布(%)')
        ax.set_xlabel('收益率(%)')
        ax.set_ylabel('天数')
        # 顶部显示最大/最小/均值
        if not returns.empty:
            ret_max = returns.max()
            ret_min = returns.min()
            ret_mean = returns.mean()
            ax.text(0.5, 0.95, f"最大: {ret_max:.3f}%  最小: {ret_min:.3f}%  均值: {ret_mean:.3f}%",
                    transform=ax.transAxes, ha='center', va='bottom', fontsize=11, color='#1976d2')
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        return tab

    def create_volume_hist_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        df = self.sub_df
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.hist(df['volume'], bins=20, color='#ffa726', alpha=0.7)
        ax.set_title('成交量分布')
        ax.set_xlabel('成交量')
        ax.set_ylabel('天数')
        # 顶部显示最大/最小/均值
        if not df['volume'].empty:
            vol_max = df['volume'].max()
            vol_min = df['volume'].min()
            vol_mean = df['volume'].mean()
            ax.text(0.5, 0.95, f"最大: {vol_max:.0f}  最小: {vol_min:.0f}  均值: {vol_mean:.0f}",
                    transform=ax.transAxes, ha='center', va='bottom', fontsize=11, color='#ffa726')
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        return tab

    def export_current_tab_img(self):
        idx = self.tabs.currentIndex()
        tab = self.tabs.widget(idx)
        # 查找FigureCanvas
        canvas = tab.findChild(FigureCanvas)
        if canvas:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存图片", "", "PNG Files (*.png)")
            if file_path:
                canvas.figure.savefig(file_path)
                QMessageBox.information(self, "导出成功", f"图片已保存到: {file_path}")
        else:
            QMessageBox.warning(self, "未找到图表", "当前Tab无可导出的图表")

    def export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出区间数据", "", "CSV Files (*.csv)")
        if file_path:
            self.sub_df.to_csv(file_path)
            QMessageBox.information(self, "导出成功", f"数据已保存到: {file_path}")

    def open_settings(self):
        dlg = IntervalStatSettingsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            # 重新加载设置并刷新界面
            settings = load_settings()
            self.custom_rules = {
                'strong_bull': settings['strong_bull'],
                'strong_bear': settings['strong_bear'],
                'extreme_volatility': settings['extreme_volatility'],
                'max_drawdown': settings['max_drawdown']
            }
            self.score_weights = settings['score_weights']
            periods = settings['periods']
            if self.multi_period_stats:
                self.period_combo.clear()
                self.period_combo.addItems([str(p) for p in periods])
            self.tabs.removeTab(0)
            self.tabs.insertTab(0, self.create_overview_tab(), "统计总览")
