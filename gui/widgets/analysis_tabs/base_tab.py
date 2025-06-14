"""
分析标签页基类 - 增强版
"""
from typing import Dict, Any, List, Optional, Callable, Union
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QColor, QKeySequence
import pandas as pd
import time
import traceback
from datetime import datetime
from core.logger import LogManager, LogLevel
from utils.config_manager import ConfigManager
from utils.cache import Cache


class BaseAnalysisTab(QWidget):
    """分析标签页基类 - 增强版"""

    # 定义信号
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    data_updated = pyqtSignal(dict)  # 新增：数据更新信号
    progress_updated = pyqtSignal(int, str)  # 新增：进度更新信号

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化基类

        Args:
            config_manager: 配置管理器
        """
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.log_manager = LogManager()
        self.data_cache = Cache(cache_dir=".cache/data", default_ttl=30*60)

        # 数据状态
        self.current_kdata = None
        self.last_update_time = None
        self.data_hash = None  # 用于检测数据变化

        # 运行状态
        self.is_loading = False
        self.is_initialized = False
        self.analysis_count = 0  # 分析次数统计

        # 性能监控
        self.performance_stats = {
            'total_analysis_time': 0.0,
            'avg_analysis_time': 0.0,
            'last_analysis_time': 0.0,
            'error_count': 0
        }

        # 安全初始化UI
        try:
            self.create_ui()
            self.is_initialized = True
            self.log_manager.debug(f"{self.__class__.__name__} 初始化成功")
        except Exception as e:
            self.log_manager.error(f"{self.__class__.__name__} 初始化失败: {e}")
            self.error_occurred.emit(f"初始化失败: {str(e)}")

    def create_ui(self):
        """创建用户界面 - 子类需要重写"""
        raise NotImplementedError("子类必须实现create_ui方法")

    def set_kdata(self, kdata):
        """设置K线数据 - 增强版

        Args:
            kdata: K线数据
        """
        try:
            # 数据验证
            if not self._validate_kdata(kdata):
                self.log_manager.warning(f"{self.__class__.__name__}: 无效的K线数据")
                return

            # 检测数据是否变化
            new_hash = self._calculate_data_hash(kdata)
            if new_hash == self.data_hash:
                self.log_manager.debug(f"{self.__class__.__name__}: 数据未变化，跳过更新")
                return

            # 更新数据
            self.current_kdata = kdata
            self.data_hash = new_hash
            self.last_update_time = datetime.now()

            # 发射数据更新信号
            self.data_updated.emit({
                'timestamp': self.last_update_time.isoformat(),
                'data_length': len(kdata) if hasattr(kdata, '__len__') else 0,
                'data_type': type(kdata).__name__
            })

            # 刷新数据
            self.refresh_data()

        except Exception as e:
            self.log_manager.error(f"{self.__class__.__name__} 设置K线数据失败: {e}")
            self.error_occurred.emit(f"设置K线数据失败: {str(e)}")

    def _validate_kdata(self, kdata) -> bool:
        """验证K线数据有效性"""
        if kdata is None:
            return False

        # 检查pandas DataFrame
        if isinstance(kdata, pd.DataFrame):
            if kdata.empty:
                return False
            # 检查必要的列
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in kdata.columns]
            if missing_columns:
                self.log_manager.warning(f"缺少必要列: {missing_columns}")
                return False
            return True

        # 检查其他数据类型
        if hasattr(kdata, '__len__') and len(kdata) == 0:
            return False

        return True

    def _calculate_data_hash(self, kdata) -> str:
        """计算数据哈希值用于变化检测"""
        try:
            if isinstance(kdata, pd.DataFrame):
                # 使用数据长度和最后几行的哈希
                if len(kdata) > 0:
                    last_rows = kdata.tail(5).to_string()
                    return f"{len(kdata)}_{hash(last_rows)}"
            return str(hash(str(kdata)))
        except Exception:
            return str(time.time())  # fallback

    def refresh_data(self):
        """刷新数据 - 增强版"""
        if not self.is_initialized:
            return

        start_time = time.time()
        try:
            self._do_refresh_data()

            # 更新性能统计
            analysis_time = time.time() - start_time
            self._update_performance_stats(analysis_time)

        except Exception as e:
            self.performance_stats['error_count'] += 1
            self.log_manager.error(f"{self.__class__.__name__} 刷新数据失败: {e}")
            self.error_occurred.emit(f"刷新数据失败: {str(e)}")

    def _do_refresh_data(self):
        """实际的数据刷新逻辑 - 子类可重写"""
        pass

    def _update_performance_stats(self, analysis_time: float):
        """更新性能统计"""
        self.analysis_count += 1
        self.performance_stats['last_analysis_time'] = analysis_time
        self.performance_stats['total_analysis_time'] += analysis_time
        self.performance_stats['avg_analysis_time'] = (
            self.performance_stats['total_analysis_time'] / self.analysis_count
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return {
            **self.performance_stats,
            'analysis_count': self.analysis_count,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'is_loading': self.is_loading,
            'data_length': len(self.current_kdata) if self.current_kdata is not None and hasattr(self.current_kdata, '__len__') else 0
        }

    def clear_data(self):
        """清除数据 - 增强版"""
        try:
            self.current_kdata = None
            self.data_hash = None
            self.last_update_time = None
            self._do_clear_data()
            self.log_manager.debug(f"{self.__class__.__name__} 数据已清除")
        except Exception as e:
            self.log_manager.error(f"{self.__class__.__name__} 清除数据失败: {e}")
            self.error_occurred.emit(f"清除数据失败: {str(e)}")

    def _do_clear_data(self):
        """实际的数据清除逻辑 - 子类可重写"""
        pass

    def show_loading(self, message="正在分析..."):
        """显示加载状态 - 增强版"""
        self.is_loading = True
        if hasattr(self, 'parent_widget') and self.parent_widget:
            self.parent_widget.show_loading(message)
        self.log_manager.debug(f"{self.__class__.__name__}: {message}")

    def hide_loading(self):
        """隐藏加载状态 - 增强版"""
        self.is_loading = False
        if hasattr(self, 'parent_widget') and self.parent_widget:
            self.parent_widget.hide_loading()

    def update_loading_progress(self, value: int, message: Optional[str] = None):
        """更新加载进度 - 增强版"""
        if hasattr(self, 'parent_widget') and self.parent_widget:
            self.parent_widget.update_loading_progress(value, message)

        # 发射进度信号
        self.progress_updated.emit(value, message or "")

    def run_analysis_async(self, analysis_func: Callable, *args, **kwargs):
        """异步运行分析函数 - 增强版"""
        if not self.is_initialized:
            self.error_occurred.emit("组件未初始化")
            return None

        if hasattr(self, 'parent_widget') and self.parent_widget:
            return self.parent_widget.run_button_analysis_async(
                None, analysis_func, *args, **kwargs
            )
        else:
            # 如果没有父组件，直接同步执行
            try:
                result = analysis_func(*args, **kwargs)
                self.analysis_completed.emit(result if isinstance(result, dict) else {"result": result})
                return result
            except Exception as e:
                self.error_occurred.emit(f"分析执行失败: {str(e)}")
                return None

    def _kdata_preprocess(self, kdata, context="分析"):
        """K线数据预处理 - 增强版"""
        if hasattr(self, 'parent_widget') and self.parent_widget:
            return self.parent_widget._kdata_preprocess(kdata, context)

        # 如果没有父组件，提供基本的预处理
        try:
            if not self._validate_kdata(kdata):
                return None
            return kdata
        except Exception as e:
            self.log_manager.error(f"数据预处理失败: {e}")
            return None

    def export_data(self, format_type: str = "json") -> Optional[Dict[str, Any]]:
        """导出数据 - 新增通用方法"""
        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'tab_type': self.__class__.__name__,
                'performance_stats': self.get_performance_stats(),
                'data_info': {
                    'has_data': self.current_kdata is not None,
                    'data_length': len(self.current_kdata) if self.current_kdata is not None and hasattr(self.current_kdata, '__len__') else 0,
                    'last_update': self.last_update_time.isoformat() if self.last_update_time else None
                }
            }

            # 子类可以重写此方法添加特定数据
            specific_data = self._get_export_specific_data()
            if specific_data:
                export_data['specific_data'] = specific_data

            return export_data

        except Exception as e:
            self.log_manager.error(f"导出数据失败: {e}")
            return None

    def _get_export_specific_data(self) -> Optional[Dict[str, Any]]:
        """获取特定的导出数据 - 子类可重写"""
        return None

    def reset_performance_stats(self):
        """重置性能统计"""
        self.performance_stats = {
            'total_analysis_time': 0.0,
            'avg_analysis_time': 0.0,
            'last_analysis_time': 0.0,
            'error_count': 0
        }
        self.analysis_count = 0
        self.log_manager.info(f"{self.__class__.__name__} 性能统计已重置")

    def get_status_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            'class_name': self.__class__.__name__,
            'is_initialized': self.is_initialized,
            'is_loading': self.is_loading,
            'has_data': self.current_kdata is not None,
            'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
            'analysis_count': self.analysis_count,
            'error_count': self.performance_stats['error_count']
        }
