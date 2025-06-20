"""
主窗口辅助工具模块

提供主窗口的辅助功能，减少main.py的代码量
"""

from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QMessageBox, QDialog
from PyQt5.QtCore import QObject


class MainWindowHelper(QObject):
    """主窗口辅助类"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

    def show_message(self, title: str, message: str, msg_type: str = "info"):
        """统一消息显示"""
        try:
            if msg_type == "error":
                QMessageBox.critical(self.parent_window, title, message)
            elif msg_type == "warning":
                QMessageBox.warning(self.parent_window, title, message)
            else:
                QMessageBox.information(self.parent_window, title, message)
        except Exception as e:
            print(f"显示消息失败: {str(e)}")

    def handle_error(self, error_msg: str):
        """统一错误处理"""
        try:
            QMessageBox.critical(self.parent_window, "错误", error_msg)
        except Exception as e:
            print(f"显示错误消息失败: {str(e)}")

    def center_dialog(self, dialog: QDialog, offset_y: int = 50):
        """居中显示对话框"""
        try:
            if self.parent_window:
                parent_geometry = self.parent_window.geometry()
                dialog_size = dialog.sizeHint()

                x = parent_geometry.x() + (parent_geometry.width() - dialog_size.width()) // 2
                y = parent_geometry.y() + (parent_geometry.height() - dialog_size.height()) // 2 + offset_y

                dialog.move(x, y)
        except Exception as e:
            print(f"居中对话框失败: {str(e)}")

    def cleanup_memory(self):
        """清理内存"""
        try:
            import gc
            gc.collect()
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.info("内存清理完成")
        except Exception as e:
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.error(f"内存清理失败: {str(e)}")

    def init_market_industry_mapping(self) -> Dict[str, Any]:
        """初始化市场和行业映射"""
        try:
            # 市场映射
            market_mapping = {
                "沪市": ["sh"],
                "深市": ["sz"],
                "创业板": ["sz"],
                "科创板": ["sh"]
            }

            # 行业映射（示例）
            industry_mapping = {
                "银行": "银行业",
                "证券": "证券业",
                "保险": "保险业",
                "房地产": "房地产业",
                "医药": "医药制造业",
                "汽车": "汽车制造业",
                "电子": "电子信息业",
                "钢铁": "钢铁业",
                "煤炭": "煤炭业",
                "有色": "有色金属业"
            }

            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.info("市场和行业映射初始化完成")

            return {
                'market_mapping': market_mapping,
                'industry_mapping': industry_mapping
            }

        except Exception as e:
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.error(f"初始化市场和行业映射失败: {str(e)}")
            return {}


def create_main_helper(parent=None) -> MainWindowHelper:
    """创建主窗口辅助实例"""
    return MainWindowHelper(parent)
