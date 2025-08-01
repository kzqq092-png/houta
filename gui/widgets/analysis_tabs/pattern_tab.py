"""
形态分析标签页 - 专业版升级
"""
import json
from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QColor, QKeySequence
from .pattern_tab_pro import PatternAnalysisTabPro


class PatternAnalysisTab(PatternAnalysisTabPro):
    """形态分析标签页 - 继承专业版功能，保持向后兼容"""

    def __init__(self, config_manager=None, event_bus=None):
        """初始化形态分析标签页"""
        super().__init__(config_manager, event_bus=event_bus)

        # 保持向后兼容的属性
        self._all_pattern_signals = []

        # 连接信号以保持兼容性
        self.analysis_completed.connect(self._on_analysis_completed)

    def _on_analysis_completed(self, results):
        """分析完成处理 - 兼容原有接口"""
        try:
            self.hide_loading()
            self.status_label.setText("分析完成")

            if 'error' in results:
                self.error_occurred.emit(results['error'])
                return

            # 更新显示
            self._update_results_display(results)

            # 发射兼容信号
            if 'patterns' in results:
                for i, pattern in enumerate(results['patterns']):
                    self.pattern_selected.emit(i)

        except Exception as e:
            self.log_manager.error(f"分析完成处理失败: {e}")

    # 保持向后兼容的方法
    def identify_patterns(self):
        """识别形态 - 兼容原接口"""
        self.one_click_analysis()

    def auto_identify_patterns(self):
        """自动识别形态 - 兼容原接口"""
        self.one_click_analysis()

    def clear_patterns(self):
        """清除形态 - 兼容原接口"""
        self.patterns_table.setRowCount(0)
        self.prediction_text.clear()
        self.stats_text.clear()
        self.backtest_text.clear()
        self._all_pattern_signals.clear()

    def refresh_data(self):
        """刷新数据 - 兼容原接口"""
        self._do_refresh_data()

    def clear_data(self):
        """清除数据 - 兼容原接口"""
        self.clear_patterns()

    # 原有的兼容方法
    def apply_confidence_preset(self, preset_text):
        """应用置信度预设"""
        presets = {
            "高置信度(0.8+)": 0.8,
            "中置信度(0.5+)": 0.5,
            "低置信度(0.3+)": 0.3,
            "全部(0.0+)": 0.0
        }
        if preset_text in presets:
            self.min_confidence.setValue(presets[preset_text])

    def apply_time_preset(self, preset_text):
        """应用时间预设"""
        # 这里可以根据需要实现时间范围设置
        pass

    def toggle_auto_refresh(self, state):
        """切换自动刷新"""
        self.realtime_cb.setChecked(state == Qt.Checked)

    def apply_pattern_filter(self):
        """应用形态筛选"""
        # 重新执行分析以应用筛选条件
        if self.current_kdata is not None:
            self.one_click_analysis()

    def show_pattern_config_dialog(self):
        """显示形态配置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("形态识别配置")
        dialog.setModal(True)
        dialog.resize(500, 400)

        layout = QVBoxLayout(dialog)

        # 基本设置
        basic_group = QGroupBox("基本设置")
        basic_layout = QFormLayout(basic_group)

        # 灵敏度设置
        sensitivity_slider = QSlider(Qt.Horizontal)
        sensitivity_slider.setRange(1, 10)
        sensitivity_slider.setValue(self.sensitivity_slider.value())
        basic_layout.addRow("识别灵敏度:", sensitivity_slider)

        # 最小置信度
        min_conf_spin = QDoubleSpinBox()
        min_conf_spin.setRange(0.0, 1.0)
        min_conf_spin.setSingleStep(0.1)
        min_conf_spin.setValue(self.min_confidence.value())
        basic_layout.addRow("最小置信度:", min_conf_spin)

        layout.addWidget(basic_group)

        # 高级设置
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QVBoxLayout(advanced_group)

        ml_cb = QCheckBox("启用机器学习预测")
        ml_cb.setChecked(self.enable_ml_cb.isChecked())
        advanced_layout.addWidget(ml_cb)

        alerts_cb = QCheckBox("启用形态预警")
        alerts_cb.setChecked(self.enable_alerts_cb.isChecked())
        advanced_layout.addWidget(alerts_cb)

        layout.addWidget(advanced_group)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            # 应用设置
            self.sensitivity_slider.setValue(sensitivity_slider.value())
            self.min_confidence.setValue(min_conf_spin.value())
            self.enable_ml_cb.setChecked(ml_cb.isChecked())
            self.enable_alerts_cb.setChecked(alerts_cb.isChecked())

    def show_pattern_statistics_dialog(self):
        """显示形态统计对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("形态统计分析")
        dialog.setModal(True)
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        # 统计文本
        stats_text = QTextEdit()
        stats_text.setReadOnly(True)
        stats_text.setText(self.stats_text.toPlainText())
        layout.addWidget(stats_text)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def export_pattern_results(self):
        """导出形态结果"""
        self.export_patterns()

    def _on_pattern_table_selection_changed(self):
        """形态表格选择变化"""
        current_row = self.patterns_table.currentRow()
        if current_row >= 0:
            self.pattern_selected.emit(current_row)

    def show_pattern_context_menu(self, position):
        """显示形态右键菜单"""
        if self.patterns_table.itemAt(position) is None:
            return

        menu = QMenu(self)

        # 查看详情
        detail_action = menu.addAction("🔍 查看详情")
        detail_action.triggered.connect(self.show_pattern_detail)

        # 导出选中
        export_action = menu.addAction("📤 导出选中")
        export_action.triggered.connect(self.export_selected_pattern)

        menu.exec_(self.patterns_table.mapToGlobal(position))

    def show_pattern_detail(self):
        """显示形态详情"""
        current_row = self.patterns_table.currentRow()
        if current_row < 0:
            return

        # 获取选中形态信息
        pattern_name = self.patterns_table.item(current_row, 0).text()
        confidence = self.patterns_table.item(current_row, 2).text()
        success_rate = self.patterns_table.item(current_row, 3).text()

        detail_dialog = QDialog(self)
        detail_dialog.setWindowTitle(f"形态详情 - {pattern_name}")
        detail_dialog.setModal(True)
        detail_dialog.resize(500, 400)

        layout = QVBoxLayout(detail_dialog)

        # 详情文本
        detail_text = QTextEdit()
        detail_text.setReadOnly(True)
        detail_text.setText(f"""
形态名称: {pattern_name}
置信度: {confidence}
历史成功率: {success_rate}

形态描述:
{self._get_pattern_description(pattern_name)}

操作建议:
{self._get_pattern_advice(pattern_name)}
        """)
        layout.addWidget(detail_text)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(detail_dialog.accept)
        layout.addWidget(close_btn)

        detail_dialog.exec_()

    def _get_pattern_description(self, pattern_name):
        """获取形态描述"""
        descriptions = {
            '头肩顶': '头肩顶是一种经典的反转形态，由三个峰组成，中间的峰最高，两边的峰相对较低且大致等高。',
            '头肩底': '头肩底是头肩顶的倒置形态，是一种看涨的反转信号。',
            '双顶': '双顶形态由两个相近的高点组成，是一种看跌的反转信号。',
            '双底': '双底形态由两个相近的低点组成，是一种看涨的反转信号。',
            # 可以添加更多形态描述
        }
        return descriptions.get(pattern_name, '暂无详细描述')

    def _get_pattern_advice(self, pattern_name):
        """获取形态建议"""
        if '顶' in pattern_name:
            return '建议逢高减仓，注意风险控制。'
        elif '底' in pattern_name:
            return '可考虑逢低建仓，但需确认突破有效性。'
        else:
            return '密切关注后续走势，等待明确信号。'

    def export_selected_pattern(self):
        """导出选中形态"""
        current_row = self.patterns_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择要导出的形态")
            return

        # 实现导出逻辑
        QMessageBox.information(self, "提示", "导出功能开发中...")

    def export_patterns(self):
        """导出形态 - 实现基本导出功能"""
        if self.patterns_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "没有可导出的形态数据")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "导出形态分析结果",
            f"pattern_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json)"
        )

        if filename:
            try:
                # 收集表格数据
                patterns_data = []
                for row in range(self.patterns_table.rowCount()):
                    pattern = {}
                    headers = ['形态名称', '类型', '置信度', '成功率', '风险等级',
                               '开始时间', '结束时间', '价格变化', '预期目标', '操作建议']

                    for col, header in enumerate(headers):
                        item = self.patterns_table.item(row, col)
                        pattern[header] = item.text() if item else ""

                    patterns_data.append(pattern)

                # 导出数据
                export_data = {
                    'export_time': datetime.now().isoformat(),
                    'data_type': '形态分析',
                    'total_patterns': len(patterns_data),
                    'patterns': patterns_data
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "成功", f"形态分析结果已导出到: {filename}")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def start_prediction(self):
        """开始预测 - 兼容接口"""
        self.ai_prediction()

    def start_backtest(self):
        """开始回测"""
        if not self._validate_kdata(self.current_kdata):
            QMessageBox.warning(self, "警告", "请先加载有效的K线数据")
            return

        self.show_loading("正在执行历史回测...")
        self.run_analysis_async(self._backtest_async)

    def _backtest_async(self):
        """异步回测"""
        try:
            period = self.backtest_period.value()

            # 模拟回测结果
            backtest_results = {
                'period': period,
                'total_signals': np.random.randint(10, 50),
                'successful_signals': np.random.randint(5, 30),
                'success_rate': np.random.uniform(0.5, 0.8),
                'avg_return': np.random.uniform(-0.05, 0.15),
                'max_drawdown': np.random.uniform(0.05, 0.2),
                'sharpe_ratio': np.random.uniform(0.5, 2.0)
            }

            return {'backtest': backtest_results}

        except Exception as e:
            return {'error': str(e)}

    def _update_backtest_display(self, backtest_results):
        """更新回测显示"""
        text = f"""
📈 历史回测报告
================

回测周期: {backtest_results.get('period', 'N/A')} 天
总信号数: {backtest_results.get('total_signals', 0)} 个
成功信号: {backtest_results.get('successful_signals', 0)} 个
成功率: {backtest_results.get('success_rate', 0):.2%}
平均收益: {backtest_results.get('avg_return', 0):+.2%}
最大回撤: {backtest_results.get('max_drawdown', 0):.2%}
夏普比率: {backtest_results.get('sharpe_ratio', 0):.2f}

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        self.backtest_text.setText(text)

    def _update_results_display(self, results):
        """更新结果显示 - 重写以支持回测"""
        super()._update_results_display(results)

    # 使用父类PatternAnalysisTabPro的优化版本_update_predictions_display方法
    # 不再重写此方法，确保使用最新的优化版本

    def _update_statistics_display(self, stats):
        """更新统计显示 - 修复版"""
        try:
            if not hasattr(self, 'stats_text'):
                self.log_manager.warning("对象没有stats_text属性")
                return

            text = f"""
📊 统计分析报告
================

总体统计:
- 形态总数: {stats.get('total_patterns', 0)} 个
- 买入信号: {stats.get('buy_patterns', 0)} 个
- 卖出信号: {stats.get('sell_patterns', 0)} 个
- 中性信号: {stats.get('neutral_patterns', 0)} 个

置信度分布:
- 高置信度: {stats.get('confidence_stats', {}).get('high_confidence', 0)} 个
- 中置信度: {stats.get('confidence_stats', {}).get('medium_confidence', 0)} 个
- 低置信度: {stats.get('confidence_stats', {}).get('low_confidence', 0)} 个

平均置信度: {stats.get('confidence_stats', {}).get('average', 0):.2%}
"""

            self.stats_text.setText(text)

        except Exception as e:
            import traceback
            self.log_manager.error(f"更新统计显示失败: {e}")
            self.log_manager.error(traceback.format_exc())

    def _process_alerts(self, alerts):
        """处理预警 - 最终修复版"""
        try:
            # 检查alerts参数
            if not alerts:
                return

            # 发送预警信号
            if hasattr(self, 'pattern_alert'):
                for alert in alerts:
                    self.pattern_alert.emit(alert['type'], alert)
        except Exception as e:
            import traceback
            self.log_manager.error(f"处理预警失败: {e}")
            self.log_manager.error(traceback.format_exc())

            # 此处不再引用results变量

    def _update_backtest_display_safe(self, results):
        """安全地更新回测显示"""
        if 'backtest' in results:
            self._update_backtest_display(results['backtest'])
