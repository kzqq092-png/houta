"""
质量检查管理器模块
提供数据质量检查、股票质量检查、批量质量检查等功能
"""

import traceback
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QMessageBox, QProgressDialog, QDialog, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import QObject, pyqtSignal, QThread, Qt


class QualityManager(QObject):
    """质量检查管理器"""

    # 信号定义
    quality_check_started = pyqtSignal(str)  # 质量检查开始信号
    quality_check_completed = pyqtSignal(dict)  # 质量检查完成信号
    quality_check_error = pyqtSignal(str)  # 质量检查错误信号
    quality_report_ready = pyqtSignal(dict)  # 质量报告准备就绪信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.log_manager = getattr(parent, 'log_manager', None)
        self.data_manager = getattr(parent, 'data_manager', None)

        self._quality_dialog = None
        self.quality_check_thread = None

    def check_single_stock_quality(self):
        """检查单只股票的数据质量"""
        try:
            # 获取当前选中的股票
            current_stock = self._get_current_stock()
            if not current_stock:
                QMessageBox.warning(self.parent, "警告", "请先选择一只股票")
                return

            self.quality_check_started.emit(current_stock)

            # 获取股票数据
            if self.data_manager:
                stock_data = self.data_manager.get_stock_data(current_stock)
                if stock_data is None or (hasattr(stock_data, 'empty') and stock_data.empty):
                    QMessageBox.warning(self.parent, "警告", f"无法获取股票 {current_stock} 的数据")
                    return

            # 执行质量检查
            quality_result = self._validate_stock_data(stock_data, current_stock)

            # 显示质量报告
            self._show_single_quality_report(current_stock, quality_result)

            self.quality_check_completed.emit({
                'stock_code': current_stock,
                'result': quality_result
            })

        except Exception as e:
            error_msg = f"检查股票质量失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            self.quality_check_error.emit(error_msg)
            QMessageBox.critical(self.parent, "错误", error_msg)

    def check_all_stocks_quality(self):
        """检查所有股票的数据质量"""
        try:
            # 获取所有股票列表
            stock_list = self._get_all_stocks()
            if not stock_list:
                QMessageBox.warning(self.parent, "警告", "没有找到股票数据")
                return

            # 确认是否继续
            reply = QMessageBox.question(
                self.parent, "确认",
                f"即将检查 {len(stock_list)} 只股票的数据质量，这可能需要较长时间。是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            self.quality_check_started.emit("批量质量检查")

            # 创建进度对话框
            progress = QProgressDialog("正在检查股票数据质量...", "取消", 0, len(stock_list), self.parent)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # 执行批量质量检查
            quality_results = {}
            for i, stock_code in enumerate(stock_list):
                if progress.wasCanceled():
                    break

                try:
                    progress.setLabelText(f"正在检查 {stock_code}...")
                    progress.setValue(i)

                    # 获取股票数据
                    if self.data_manager:
                        stock_data = self.data_manager.get_stock_data(stock_code)
                        if stock_data is not None and not (hasattr(stock_data, 'empty') and stock_data.empty):
                            # 执行质量检查
                            result = self._validate_stock_data(stock_data, stock_code)
                            quality_results[stock_code] = result

                except Exception as e:
                    if self.log_manager:
                        self.log_manager.warning(f"检查股票 {stock_code} 质量失败: {str(e)}")
                    continue

            progress.setValue(len(stock_list))
            progress.close()

            if quality_results:
                # 显示批量质量报告
                self._show_batch_quality_report(quality_results)

                self.quality_check_completed.emit({
                    'type': 'batch',
                    'results': quality_results
                })
            else:
                QMessageBox.information(self.parent, "信息", "没有成功检查任何股票的质量")

        except Exception as e:
            error_msg = f"批量检查股票质量失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            self.quality_check_error.emit(error_msg)
            QMessageBox.critical(self.parent, "错误", error_msg)

    def _get_current_stock(self) -> Optional[str]:
        """获取当前选中的股票代码"""
        try:
            if hasattr(self.parent, 'current_stock') and self.parent.current_stock:
                return self.parent.current_stock
            elif hasattr(self.parent, 'stock_panel'):
                return getattr(self.parent.stock_panel, 'current_stock', None)
            elif hasattr(self.parent, 'stock_list'):
                current_item = self.parent.stock_list.currentItem()
                if current_item:
                    stock_data = current_item.data(Qt.UserRole)
                    return stock_data.get('marketCode') if stock_data else None
            return None
        except Exception as e:
            if self.log_manager:
                self.log_manager.warning(f"获取当前股票失败: {str(e)}")
            return None

    def _get_all_stocks(self) -> List[str]:
        """获取所有股票代码列表"""
        try:
            if hasattr(self.parent, 'stock_panel'):
                return getattr(self.parent.stock_panel, 'get_all_stock_codes', lambda: [])()
            elif hasattr(self.parent, 'stock_list_cache'):
                return [stock['marketCode'] for stock in self.parent.stock_list_cache]
            else:
                # 从数据管理器获取
                if self.data_manager:
                    stocks_df = self.data_manager.get_stock_list()
                    if not stocks_df.empty:
                        return [f"{row['market'].lower()}{row['code']}" for _, row in stocks_df.iterrows()]
            return []
        except Exception as e:
            if self.log_manager:
                self.log_manager.warning(f"获取股票列表失败: {str(e)}")
            return []

    def _validate_stock_data(self, stock_data, stock_code: str) -> Dict[str, Any]:
        """验证股票数据质量"""
        try:
            result = {
                'stock_code': stock_code,
                'is_valid': True,
                'quality_score': 100.0,
                'quality_level': 'excellent',
                'errors': [],
                'warnings': [],
                'suggestions': [],
                'data_count': 0,
                'missing_count': 0,
                'duplicate_count': 0
            }

            if stock_data is None:
                result['is_valid'] = False
                result['quality_score'] = 0.0
                result['quality_level'] = 'poor'
                result['errors'].append('股票数据为空')
                return result

            # 检查数据是否为空
            if hasattr(stock_data, 'empty') and stock_data.empty:
                result['is_valid'] = False
                result['quality_score'] = 0.0
                result['quality_level'] = 'poor'
                result['errors'].append('股票数据为空')
                return result

            # 检查数据行数
            if hasattr(stock_data, '__len__'):
                result['data_count'] = len(stock_data)
                if result['data_count'] < 10:
                    result['warnings'].append('数据量过少，可能影响分析准确性')
                    result['quality_score'] -= 10

            # 检查必要字段
            required_fields = ['open', 'high', 'low', 'close', 'volume']
            if hasattr(stock_data, 'columns'):
                missing_fields = [field for field in required_fields if field not in stock_data.columns]
                if missing_fields:
                    result['errors'].extend([f'缺少必要字段: {field}' for field in missing_fields])
                    result['quality_score'] -= len(missing_fields) * 15
                    if len(missing_fields) >= 3:
                        result['is_valid'] = False

            # 检查数据完整性
            if hasattr(stock_data, 'isnull'):
                missing_count = stock_data.isnull().sum().sum()
                result['missing_count'] = missing_count
                if missing_count > 0:
                    result['warnings'].append(f'存在 {missing_count} 个缺失值')
                    result['quality_score'] -= min(missing_count * 0.1, 20)

            # 检查重复数据
            if hasattr(stock_data, 'duplicated'):
                duplicate_count = stock_data.duplicated().sum()
                result['duplicate_count'] = duplicate_count
                if duplicate_count > 0:
                    result['warnings'].append(f'存在 {duplicate_count} 条重复数据')
                    result['quality_score'] -= min(duplicate_count * 0.5, 15)

            # 确定质量等级
            if result['quality_score'] >= 90:
                result['quality_level'] = 'excellent'
            elif result['quality_score'] >= 75:
                result['quality_level'] = 'good'
            elif result['quality_score'] >= 60:
                result['quality_level'] = 'fair'
            else:
                result['quality_level'] = 'poor'
                if result['quality_score'] < 50:
                    result['is_valid'] = False

            return result

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"验证股票数据质量失败: {str(e)}")
            return {
                'stock_code': stock_code,
                'is_valid': False,
                'quality_score': 0.0,
                'quality_level': 'error',
                'errors': [f'验证过程出错: {str(e)}'],
                'warnings': [],
                'suggestions': []
            }

    def _show_single_quality_report(self, stock_code: str, result: Dict[str, Any]):
        """显示单只股票的质量报告"""
        try:
            dialog = QDialog(self.parent)
            dialog.setWindowTitle(f"股票质量报告 - {stock_code}")
            dialog.setModal(True)
            dialog.resize(600, 400)

            layout = QVBoxLayout(dialog)

            # 创建报告表格
            table = QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["项目", "值"])

            # 添加报告数据
            report_data = [
                ("股票代码", stock_code),
                ("数据有效性", "有效" if result.get('is_valid', False) else "无效"),
                ("质量分数", f"{result.get('quality_score', 0):.2f}"),
                ("质量等级", result.get('quality_level', 'unknown')),
                ("数据行数", str(result.get('data_count', 0))),
                ("缺失值数量", str(result.get('missing_count', 0))),
                ("重复数据数量", str(result.get('duplicate_count', 0))),
                ("错误数量", str(len(result.get('errors', [])))),
                ("警告数量", str(len(result.get('warnings', [])))),
            ]

            table.setRowCount(len(report_data))
            for i, (key, value) in enumerate(report_data):
                table.setItem(i, 0, QTableWidgetItem(key))
                table.setItem(i, 1, QTableWidgetItem(str(value)))

            table.resizeColumnsToContents()
            layout.addWidget(table)

            # 添加按钮
            button_layout = QHBoxLayout()
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.close)
            button_layout.addWidget(close_button)

            layout.addLayout(button_layout)

            dialog.exec_()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"显示质量报告失败: {str(e)}")

    def _show_batch_quality_report(self, results: Dict[str, Any]):
        """显示批量质量报告"""
        try:
            dialog = QDialog(self.parent)
            dialog.setWindowTitle("批量质量检查报告")
            dialog.setModal(True)
            dialog.resize(800, 600)

            layout = QVBoxLayout(dialog)

            # 创建报告表格
            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels([
                "股票代码", "质量分数", "质量等级", "有效性", "错误数", "警告数"
            ])

            # 添加报告数据
            table.setRowCount(len(results))
            for i, (stock_code, result) in enumerate(results.items()):
                table.setItem(i, 0, QTableWidgetItem(stock_code))
                table.setItem(i, 1, QTableWidgetItem(f"{result.get('quality_score', 0):.2f}"))
                table.setItem(i, 2, QTableWidgetItem(result.get('quality_level', 'unknown')))
                table.setItem(i, 3, QTableWidgetItem("有效" if result.get('is_valid', False) else "无效"))
                table.setItem(i, 4, QTableWidgetItem(str(len(result.get('errors', [])))))
                table.setItem(i, 5, QTableWidgetItem(str(len(result.get('warnings', [])))))

            table.resizeColumnsToContents()
            table.setSortingEnabled(True)
            layout.addWidget(table)

            # 添加统计信息
            total_stocks = len(results)
            valid_stocks = sum(1 for r in results.values() if r.get('is_valid', False))
            avg_score = sum(r.get('quality_score', 0) for r in results.values()) / total_stocks if total_stocks > 0 else 0

            stats_label = QTableWidgetItem(f"总股票数: {total_stocks}, 有效股票: {valid_stocks}, 平均质量分数: {avg_score:.2f}")
            layout.addWidget(stats_label)

            # 添加按钮
            button_layout = QHBoxLayout()

            export_button = QPushButton("导出报告")
            export_button.clicked.connect(lambda: self._export_quality_report(results))
            button_layout.addWidget(export_button)

            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.close)
            button_layout.addWidget(close_button)

            layout.addLayout(button_layout)

            dialog.exec_()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"显示批量质量报告失败: {str(e)}")

    def _export_quality_report(self, results: Dict[str, Any]):
        """导出质量报告"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            import pandas as pd

            # 选择保存文件
            file_path, _ = QFileDialog.getSaveFileName(
                self.parent, "导出质量报告", "quality_report.csv", "CSV Files (*.csv)"
            )

            if file_path:
                # 准备数据
                report_data = []
                for stock_code, result in results.items():
                    report_data.append({
                        '股票代码': stock_code,
                        '质量分数': result.get('quality_score', 0),
                        '质量等级': result.get('quality_level', 'unknown'),
                        '有效性': '有效' if result.get('is_valid', False) else '无效',
                        '数据行数': result.get('data_count', 0),
                        '缺失值数量': result.get('missing_count', 0),
                        '重复数据数量': result.get('duplicate_count', 0),
                        '错误数': len(result.get('errors', [])),
                        '警告数': len(result.get('warnings', []))
                    })

                # 保存到CSV
                df = pd.DataFrame(report_data)
                df.to_csv(file_path, index=False, encoding='utf-8-sig')

                QMessageBox.information(self.parent, "成功", f"质量报告已导出到: {file_path}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"导出质量报告失败: {str(e)}")
            QMessageBox.critical(self.parent, "错误", f"导出失败: {str(e)}")

    def get_quality_summary(self) -> Dict[str, Any]:
        """获取质量检查摘要"""
        try:
            # 这里可以实现质量检查的摘要统计
            return {
                'total_checks': 0,
                'passed_checks': 0,
                'failed_checks': 0,
                'average_score': 0.0,
                'last_check_time': None
            }
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取质量摘要失败: {str(e)}")
            return {}

    def cleanup(self):
        """清理资源"""
        try:
            if self.quality_check_thread and self.quality_check_thread.isRunning():
                self.quality_check_thread.quit()
                self.quality_check_thread.wait()

            if self._quality_dialog:
                self._quality_dialog.close()
                self._quality_dialog = None

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清理质量管理器资源失败: {str(e)}")
