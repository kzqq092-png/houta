"""
优化管理器模块
提供优化仪表板、一键优化、智能优化、版本管理等功能
"""

import traceback
import threading
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QMessageBox, QProgressDialog, QInputDialog
)
from PyQt5.QtCore import QObject, pyqtSignal, QThread, Qt


class OptimizationManager(QObject):
    """优化管理器"""

    # 信号定义
    optimization_started = pyqtSignal(str)  # 优化开始信号
    optimization_completed = pyqtSignal(dict)  # 优化完成信号
    optimization_error = pyqtSignal(str)  # 优化错误信号
    dashboard_opened = pyqtSignal()  # 仪表板打开信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.log_manager = getattr(parent, 'log_manager', None)
        self._optimization_dashboard = None
        self.optimization_thread = None

    def show_optimization_dashboard(self):
        """显示优化仪表板"""
        try:
            # 延迟导入，避免启动时阻塞
            from optimization.optimization_dashboard import OptimizationDashboard

            # 检查是否已经打开了仪表板
            if self._optimization_dashboard and self._optimization_dashboard.isVisible():
                self._optimization_dashboard.raise_()
                self._optimization_dashboard.activateWindow()
                return

            # 创建新的仪表板窗口
            self._optimization_dashboard = OptimizationDashboard()
            self._optimization_dashboard.show()

            self.dashboard_opened.emit()
            if self.log_manager:
                self.log_manager.info("已打开形态识别算法优化仪表板")

        except ImportError as e:
            error_msg = f"导入优化仪表板模块失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            QMessageBox.warning(self.parent, "模块缺失", "优化仪表板模块未找到，请检查安装")
        except Exception as e:
            error_msg = f"打开优化仪表板失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            QMessageBox.critical(self.parent, "错误", error_msg)

    def run_one_click_optimization(self):
        """运行一键优化"""
        try:
            # 延迟导入，避免启动时阻塞
            from optimization.auto_tuner import AutoTuner

            # 确认对话框
            reply = QMessageBox.question(
                self.parent, "确认优化",
                "一键优化将对所有形态识别算法进行优化，这可能需要较长时间。\n确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 创建进度对话框
            progress = QProgressDialog("正在优化形态识别算法...", "取消", 0, 100, self.parent)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # 创建优化线程
            class OptimizationThread(QThread):
                finished_signal = pyqtSignal(dict)
                error_signal = pyqtSignal(str)

                def run(self):
                    try:
                        tuner = AutoTuner(max_workers=2, debug_mode=True)
                        result = tuner.one_click_optimize(
                            optimization_method="genetic",
                            max_iterations=20
                        )
                        self.finished_signal.emit(result)
                    except Exception as e:
                        self.error_signal.emit(str(e))

            def on_optimization_finished(result):
                progress.close()
                summary = result.get("summary", {})
                message = f"""
一键优化完成！

总任务数: {summary.get('total_tasks', 0)}
成功任务数: {summary.get('successful_tasks', 0)}
成功率: {summary.get('success_rate', 0):.1f}%
平均改进: {summary.get('average_improvement', 0):.3f}%
最佳改进: {summary.get('best_improvement', 0):.3f}%
最佳形态: {summary.get('best_pattern', 'N/A')}
                """.strip()
                QMessageBox.information(self.parent, "优化完成", message)
                self.optimization_completed.emit(result)
                if self.log_manager:
                    self.log_manager.info("一键优化完成")

            def on_optimization_error(error):
                progress.close()
                QMessageBox.critical(self.parent, "优化失败", f"一键优化失败: {error}")
                self.optimization_error.emit(error)
                if self.log_manager:
                    self.log_manager.error(f"一键优化失败: {error}")

            # 启动优化线程
            self.optimization_thread = OptimizationThread()
            self.optimization_thread.finished_signal.connect(on_optimization_finished)
            self.optimization_thread.error_signal.connect(on_optimization_error)
            self.optimization_thread.start()

            self.optimization_started.emit("one_click")
            if self.log_manager:
                self.log_manager.info("已启动一键优化")

        except Exception as e:
            error_msg = f"启动一键优化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            QMessageBox.critical(self.parent, "错误", error_msg)

    def run_smart_optimization(self):
        """运行智能优化"""
        try:
            # 获取性能阈值
            threshold, ok = QInputDialog.getDouble(
                self.parent, "智能优化设置",
                "请输入性能阈值（0.0-1.0）：\n低于此值的形态将被优化",
                0.7, 0.0, 1.0, 2
            )

            if not ok:
                return

            # 获取改进目标
            target, ok = QInputDialog.getDouble(
                self.parent, "智能优化设置",
                "请输入改进目标（0.0-1.0）：\n期望的性能提升比例",
                0.1, 0.0, 1.0, 2
            )

            if not ok:
                return

            # 创建进度对话框
            progress = QProgressDialog("正在进行智能优化...", "取消", 0, 100, self.parent)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # 在后台线程中执行优化
            def run_optimization():
                try:
                    from optimization.auto_tuner import AutoTuner
                    tuner = AutoTuner(max_workers=2, debug_mode=True)
                    result = tuner.smart_optimize(
                        performance_threshold=threshold,
                        improvement_target=target
                    )

                    progress.close()

                    if result.get("status") == "no_optimization_needed":
                        QMessageBox.information(
                            self.parent, "智能优化",
                            "所有形态性能都达到要求，无需优化"
                        )
                    else:
                        summary = result.get("summary", {})
                        smart_analysis = result.get("smart_analysis", {})

                        message = f"""
智能优化完成！

优化形态数: {summary.get('total_tasks', 0)}
成功任务数: {summary.get('successful_tasks', 0)}
平均改进: {summary.get('average_improvement', 0):.3f}%
达成目标数: {smart_analysis.get('targets_achieved', 0)}
目标达成率: {smart_analysis.get('target_achievement_rate', 0):.1f}%
                        """.strip()
                        QMessageBox.information(self.parent, "智能优化完成", message)

                    self.optimization_completed.emit(result)
                    if self.log_manager:
                        self.log_manager.info("智能优化完成")

                except Exception as e:
                    progress.close()
                    error_msg = f"智能优化失败: {str(e)}"
                    QMessageBox.critical(self.parent, "优化失败", error_msg)
                    self.optimization_error.emit(error_msg)
                    if self.log_manager:
                        self.log_manager.error(error_msg)

            # 启动后台线程
            threading.Thread(target=run_optimization, daemon=True).start()

            self.optimization_started.emit("smart")
            if self.log_manager:
                self.log_manager.info("已启动智能优化")

        except Exception as e:
            error_msg = f"启动智能优化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            QMessageBox.critical(self.parent, "错误", error_msg)

    def show_version_manager(self):
        """显示版本管理器"""
        try:
            from optimization.ui_integration import VersionManagerDialog
            from optimization.version_manager import VersionManager

            # 获取要管理的形态名称
            patterns = self._get_available_patterns()

            if not patterns:
                QMessageBox.information(self.parent, "提示", "没有找到可管理的形态")
                return

            # 选择形态
            pattern_name, ok = QInputDialog.getItem(
                self.parent, "选择形态", "请选择要管理版本的形态：",
                patterns, 0, False
            )

            if not ok or not pattern_name:
                return

            # 创建版本管理器
            version_manager = VersionManager(pattern_name)

            # 显示版本管理对话框
            dialog = VersionManagerDialog(version_manager, self.parent)
            dialog.exec_()

            if self.log_manager:
                self.log_manager.info(f"已打开形态 '{pattern_name}' 的版本管理器")

        except ImportError as e:
            error_msg = f"导入版本管理器模块失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            QMessageBox.warning(self.parent, "模块缺失", "版本管理器模块未找到，请检查安装")
        except Exception as e:
            error_msg = f"显示版本管理器失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            QMessageBox.critical(self.parent, "错误", error_msg)

    def show_optimization_status(self):
        """显示优化状态"""
        try:
            from optimization.ui_integration import OptimizationStatusDialog

            dialog = OptimizationStatusDialog(self.parent)
            dialog.exec_()

            if self.log_manager:
                self.log_manager.info("已打开优化状态对话框")

        except ImportError as e:
            error_msg = f"导入优化状态模块失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            QMessageBox.warning(self.parent, "模块缺失", "优化状态模块未找到，请检查安装")
        except Exception as e:
            error_msg = f"显示优化状态失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            QMessageBox.critical(self.parent, "错误", error_msg)

    def _get_available_patterns(self) -> List[str]:
        """获取可用的形态列表"""
        patterns = []
        try:
            from analysis.pattern_manager import PatternManager
            manager = PatternManager()
            pattern_configs = manager.get_all_patterns()
            patterns = [p.english_name for p in pattern_configs]
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取形态列表失败: {e}")
            # 默认形态
            patterns = ["hammer", "doji", "three_white_soldiers"]

        return patterns

    def stop_optimization(self):
        """停止当前优化"""
        try:
            if self.optimization_thread and self.optimization_thread.isRunning():
                self.optimization_thread.terminate()
                self.optimization_thread.wait()
                if self.log_manager:
                    self.log_manager.info("优化已停止")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"停止优化失败: {str(e)}")

    def is_optimization_running(self) -> bool:
        """检查是否有优化正在运行"""
        return self.optimization_thread and self.optimization_thread.isRunning()

    def cleanup(self):
        """清理资源"""
        try:
            self.stop_optimization()
            if self._optimization_dashboard:
                self._optimization_dashboard.close()
                self._optimization_dashboard = None
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清理优化管理器资源失败: {str(e)}")
