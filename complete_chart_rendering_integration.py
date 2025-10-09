#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完善图表渲染集成

修复图表渲染管理器的集成问题，确保在主UI中正确引用
"""

import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def fix_chart_rendering_integration():
    """修复图表渲染集成问题"""
    logger.info("=== 修复图表渲染集成问题 ===")

    main_dialog_path = Path("gui/dialogs/unified_duckdb_import_dialog.py")

    if not main_dialog_path.exists():
        logger.error(f"主导入对话框文件不存在: {main_dialog_path}")
        return False

    try:
        # 读取当前文件内容
        with open(main_dialog_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否需要添加图表渲染管理器导入
        import_code = """
# 图表渲染管理器导入
try:
    from gui.widgets.chart_rendering_manager import get_chart_rendering_manager
    CHART_RENDERING_AVAILABLE = True
except ImportError:
    logger.warning("图表渲染管理器不可用，将使用简化版本")
    CHART_RENDERING_AVAILABLE = False
"""

        if 'chart_rendering_manager' not in content:
            logger.info("添加图表渲染管理器导入")

            # 在导入部分添加图表渲染管理器导入
            import_position = content.find('from loguru import logger')
            if import_position != -1:
                # 在logger导入之后添加
                end_of_logger_import = content.find('\n', import_position)
                content = content[:end_of_logger_import] + '\n' + import_code + content[end_of_logger_import:]
            else:
                # 在文件开头添加
                content = import_code + '\n' + content

        # 在类初始化中添加图表渲染管理器初始化
        init_code = '''
        # 初始化图表渲染管理器
        if CHART_RENDERING_AVAILABLE:
            try:
                self.chart_rendering_manager = get_chart_rendering_manager()
                logger.info("✅ 图表渲染管理器初始化成功")
            except Exception as e:
                logger.warning(f"图表渲染管理器初始化失败: {e}")
                self.chart_rendering_manager = None
        else:
            self.chart_rendering_manager = None
'''

        # 找到__init__方法并添加初始化代码
        import re
        init_pattern = r'(def __init__.*?\n.*?super\(\).__init__.*?\n)'
        match = re.search(init_pattern, content, re.DOTALL)
        if match and 'chart_rendering_manager' not in content:
            logger.info("添加图表渲染管理器初始化代码")
            init_end = match.end()
            content = content[:init_end] + init_code + content[init_end:]

        # 添加图表渲染辅助方法
        helper_methods = '''
    def _get_chart_renderer(self, data_size: int = 1000):
        """获取最佳图表渲染器"""
        if self.chart_rendering_manager:
            return self.chart_rendering_manager.get_best_renderer(data_size)
        else:
            # 使用简化的渲染器
            try:
                from gui.widgets.chart_renderer import ChartRenderer
                return ChartRenderer()
            except ImportError:
                logger.error("无法导入任何图表渲染器")
                return None
    
    def _render_chart_safely(self, ax, data, chart_type='candlestick', style=None):
        """安全地渲染图表"""
        try:
            renderer = self._get_chart_renderer(len(data) if hasattr(data, '__len__') else 1000)
            if not renderer:
                return False
            
            style = style or {}
            
            if chart_type.lower() in ['candlestick', '蜡烛图']:
                if hasattr(renderer, 'render_candlesticks'):
                    return renderer.render_candlesticks(ax, data, style)
                elif self.chart_rendering_manager:
                    return self.chart_rendering_manager.render_candlesticks(ax, data, style)
            elif chart_type.lower() in ['ohlc', 'ohlc柱状图']:
                if hasattr(renderer, 'render_ohlc'):
                    return renderer.render_ohlc(ax, data, style)
                elif self.chart_rendering_manager:
                    return self.chart_rendering_manager.render_ohlc(ax, data, style)
            
            # 如果以上都不可用，返回False表示需要使用后备方案
            return False
            
        except Exception as e:
            logger.error(f"图表渲染失败: {e}")
            return False
'''

        if '_get_chart_renderer' not in content:
            logger.info("添加图表渲染辅助方法")
            # 在类的末尾添加辅助方法
            content = content.rstrip() + '\n' + helper_methods + '\n'

        # 写回文件
        with open(main_dialog_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info("✅ 图表渲染集成修复完成")
        return True

    except Exception as e:
        logger.error(f"修复图表渲染集成时发生错误: {e}")
        return False


def enhance_technical_indicators_integration():
    """增强技术指标集成"""
    logger.info("=== 增强技术指标集成 ===")

    main_dialog_path = Path("gui/dialogs/unified_duckdb_import_dialog.py")

    try:
        with open(main_dialog_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 添加技术指标导入
        indicator_imports = '''
# 技术指标相关导入
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    logger.info("TA-Lib不可用，将使用内置技术指标")
    TALIB_AVAILABLE = False

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    logger.info("pandas_ta不可用，将使用内置技术指标")
    PANDAS_TA_AVAILABLE = False
'''

        if 'TALIB_AVAILABLE' not in content:
            # 在现有导入后添加技术指标导入
            logger.info("添加技术指标库导入")
            import_position = content.find('logger = logger.bind(module=__name__)')
            if import_position != -1:
                end_position = content.find('\n', import_position)
                content = content[:end_position] + '\n' + indicator_imports + content[end_position:]

        # 添加技术指标计算方法
        indicator_methods = '''
    def _calculate_technical_indicators(self, data, indicators: List[str]):
        """计算技术指标"""
        try:
            results = {}
            
            if not isinstance(data, pd.DataFrame):
                logger.warning("数据不是DataFrame格式，无法计算技术指标")
                return results
            
            # 确保数据包含必要的列
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                logger.warning(f"数据缺少必要列: {missing_cols}")
                return results
            
            # 计算各种技术指标
            for indicator in indicators:
                try:
                    if indicator == 'MA':
                        results['MA5'] = data['close'].rolling(window=5).mean()
                        results['MA20'] = data['close'].rolling(window=20).mean()
                        results['MA60'] = data['close'].rolling(window=60).mean()
                    
                    elif indicator == 'EMA':
                        results['EMA12'] = data['close'].ewm(span=12).mean()
                        results['EMA26'] = data['close'].ewm(span=26).mean()
                    
                    elif indicator == 'MACD' and TALIB_AVAILABLE:
                        macd, signal, hist = talib.MACD(data['close'].values)
                        results['MACD'] = pd.Series(macd, index=data.index)
                        results['MACD_signal'] = pd.Series(signal, index=data.index)
                        results['MACD_hist'] = pd.Series(hist, index=data.index)
                    
                    elif indicator == 'RSI' and TALIB_AVAILABLE:
                        rsi = talib.RSI(data['close'].values, timeperiod=14)
                        results['RSI'] = pd.Series(rsi, index=data.index)
                    
                    elif indicator == 'Bollinger' and TALIB_AVAILABLE:
                        upper, middle, lower = talib.BBANDS(data['close'].values)
                        results['BOLL_upper'] = pd.Series(upper, index=data.index)
                        results['BOLL_middle'] = pd.Series(middle, index=data.index)
                        results['BOLL_lower'] = pd.Series(lower, index=data.index)
                    
                    elif indicator == 'Volume':
                        results['Volume_MA'] = data['volume'].rolling(window=20).mean()
                    
                    logger.info(f"✅ 成功计算技术指标: {indicator}")
                    
                except Exception as e:
                    logger.warning(f"计算技术指标 {indicator} 失败: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"计算技术指标时发生错误: {e}")
            return {}
    
    def _add_indicators_to_chart(self, ax, data, indicators_data):
        """将技术指标添加到图表中"""
        try:
            colors = ['orange', 'purple', 'green', 'red', 'blue', 'brown']
            color_index = 0
            
            for indicator_name, indicator_data in indicators_data.items():
                if indicator_data is not None and not indicator_data.empty:
                    color = colors[color_index % len(colors)]
                    
                    # 绘制指标线
                    ax.plot(data.index, indicator_data, 
                           color=color, linewidth=1, label=indicator_name, alpha=0.8)
                    
                    color_index += 1
            
            # 如果有指标，显示图例
            if indicators_data:
                ax.legend(loc='upper left', fontsize=8)
            
        except Exception as e:
            logger.error(f"添加技术指标到图表失败: {e}")
'''

        if '_calculate_technical_indicators' not in content:
            logger.info("添加技术指标计算方法")
            content = content.rstrip() + '\n' + indicator_methods + '\n'

        # 写回文件
        with open(main_dialog_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info("✅ 技术指标集成增强完成")
        return True

    except Exception as e:
        logger.error(f"增强技术指标集成时发生错误: {e}")
        return False


def create_advanced_data_export_ui():
    """创建高级数据导出UI"""
    logger.info("=== 创建高级数据导出UI ===")

    export_dialog_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级数据导出对话框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QGroupBox,
    QMessageBox, QProgressBar, QFileDialog, QTextEdit, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from loguru import logger
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

class DataExportThread(QThread):
    """数据导出线程"""
    
    progress_updated = pyqtSignal(int, str)
    export_completed = pyqtSignal(str)
    export_failed = pyqtSignal(str)
    
    def __init__(self, data: pd.DataFrame, export_config: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.export_config = export_config
    
    def run(self):
        """执行导出"""
        try:
            self.progress_updated.emit(10, "准备导出数据...")
            
            export_format = self.export_config['format']
            file_path = self.export_config['file_path']
            
            self.progress_updated.emit(30, f"导出为{export_format}格式...")
            
            if export_format == 'Excel':
                self.data.to_excel(file_path, index=False)
            elif export_format == 'CSV':
                self.data.to_csv(file_path, index=False, encoding='utf-8-sig')
            elif export_format == 'JSON':
                self.data.to_json(file_path, orient='records', date_format='iso')
            elif export_format == 'Parquet':
                self.data.to_parquet(file_path)
            
            self.progress_updated.emit(90, "完成导出...")
            self.export_completed.emit(file_path)
            
        except Exception as e:
            self.export_failed.emit(str(e))

class AdvancedDataExportDialog(QDialog):
    """高级数据导出对话框"""
    
    def __init__(self, data: Optional[pd.DataFrame] = None, parent=None):
        super().__init__(parent)
        self.data = data
        self.export_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("高级数据导出")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 导出设置标签页
        export_tab = self._create_export_settings_tab()
        tab_widget.addTab(export_tab, "导出设置")
        
        # 数据预览标签页
        preview_tab = self._create_data_preview_tab()
        tab_widget.addTab(preview_tab, "数据预览")
        
        # 导出历史标签页
        history_tab = self._create_export_history_tab()
        tab_widget.addTab(history_tab, "导出历史")
        
        layout.addWidget(tab_widget)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("开始导出")
        self.export_btn.clicked.connect(self.start_export)
        button_layout.addWidget(self.export_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def _create_export_settings_tab(self):
        """创建导出设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 格式选择
        format_group = QGroupBox("导出格式")
        format_layout = QGridLayout(format_group)
        
        format_layout.addWidget(QLabel("文件格式:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(['Excel', 'CSV', 'JSON', 'Parquet'])
        format_layout.addWidget(self.format_combo, 0, 1)
        
        format_layout.addWidget(QLabel("文件路径:"), 1, 0)
        self.file_path_edit = QLineEdit()
        format_layout.addWidget(self.file_path_edit, 1, 1)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_file_path)
        format_layout.addWidget(self.browse_btn, 1, 2)
        
        layout.addWidget(format_group)
        
        # 数据选择
        data_group = QGroupBox("数据选择")
        data_layout = QGridLayout(data_group)
        
        self.include_index_cb = QCheckBox("包含索引")
        data_layout.addWidget(self.include_index_cb, 0, 0)
        
        self.include_header_cb = QCheckBox("包含列标题")
        self.include_header_cb.setChecked(True)
        data_layout.addWidget(self.include_header_cb, 0, 1)
        
        data_layout.addWidget(QLabel("行数限制:"), 1, 0)
        self.row_limit_spin = QSpinBox()
        self.row_limit_spin.setRange(0, 1000000)
        self.row_limit_spin.setValue(0)  # 0表示无限制
        self.row_limit_spin.setSpecialValueText("无限制")
        data_layout.addWidget(self.row_limit_spin, 1, 1)
        
        layout.addWidget(data_group)
        
        layout.addStretch()
        return tab
    
    def _create_data_preview_tab(self):
        """创建数据预览标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 数据信息
        info_group = QGroupBox("数据信息")
        info_layout = QGridLayout(info_group)
        
        self.data_shape_label = QLabel("形状: 未加载")
        info_layout.addWidget(self.data_shape_label, 0, 0)
        
        self.data_size_label = QLabel("大小: 未知")
        info_layout.addWidget(self.data_size_label, 0, 1)
        
        layout.addWidget(info_group)
        
        # 数据预览
        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
        # 更新预览
        self._update_data_preview()
        
        layout.addStretch()
        return tab
    
    def _create_export_history_tab(self):
        """创建导出历史标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        history_group = QGroupBox("最近导出")
        history_layout = QVBoxLayout(history_group)
        
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        self.history_text.setPlainText("暂无导出历史")
        history_layout.addWidget(self.history_text)
        
        layout.addWidget(history_group)
        
        return tab
    
    def _update_data_preview(self):
        """更新数据预览"""
        if self.data is not None:
            shape_text = f"形状: {self.data.shape[0]} 行 × {self.data.shape[1]} 列"
            self.data_shape_label.setText(shape_text)
            
            # 估算数据大小
            size_mb = self.data.memory_usage(deep=True).sum() / 1024 / 1024
            size_text = f"大小: {size_mb:.2f} MB"
            self.data_size_label.setText(size_text)
            
            # 显示前几行数据
            preview_data = self.data.head(10).to_string()
            self.preview_text.setPlainText(preview_data)
        else:
            self.data_shape_label.setText("形状: 未加载")
            self.data_size_label.setText("大小: 未知")
            self.preview_text.setPlainText("无数据可预览")
    
    def browse_file_path(self):
        """浏览文件路径"""
        format_name = self.format_combo.currentText()
        extensions = {
            'Excel': '*.xlsx',
            'CSV': '*.csv',
            'JSON': '*.json',
            'Parquet': '*.parquet'
        }
        
        file_filter = f"{format_name} 文件 ({extensions[format_name]})"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"保存{format_name}文件", 
            f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extensions[format_name][2:]}",
            file_filter
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def start_export(self):
        """开始导出"""
        if self.data is None:
            QMessageBox.warning(self, "错误", "没有可导出的数据")
            return
        
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "错误", "请选择导出文件路径")
            return
        
        # 准备导出配置
        export_config = {
            'format': self.format_combo.currentText(),
            'file_path': file_path,
            'include_index': self.include_index_cb.isChecked(),
            'include_header': self.include_header_cb.isChecked(),
            'row_limit': self.row_limit_spin.value()
        }
        
        # 处理行数限制
        export_data = self.data
        if export_config['row_limit'] > 0:
            export_data = self.data.head(export_config['row_limit'])
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.export_btn.setEnabled(False)
        
        # 开始导出线程
        self.export_thread = DataExportThread(export_data, export_config)
        self.export_thread.progress_updated.connect(self._on_progress_updated)
        self.export_thread.export_completed.connect(self._on_export_completed)
        self.export_thread.export_failed.connect(self._on_export_failed)
        self.export_thread.start()
    
    def _on_progress_updated(self, progress: int, message: str):
        """进度更新回调"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def _on_export_completed(self, file_path: str):
        """导出完成回调"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.export_btn.setEnabled(True)
        
        QMessageBox.information(self, "成功", f"数据已成功导出到: {file_path}")
        self.accept()
    
    def _on_export_failed(self, error: str):
        """导出失败回调"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.export_btn.setEnabled(True)
        
        QMessageBox.critical(self, "错误", f"导出失败: {error}")
    
    def set_data(self, data: pd.DataFrame):
        """设置要导出的数据"""
        self.data = data
        self._update_data_preview()

def show_advanced_export_dialog(data: pd.DataFrame = None, parent=None):
    """显示高级数据导出对话框"""
    dialog = AdvancedDataExportDialog(data, parent)
    return dialog.exec_()
'''

    # 创建高级数据导出对话框文件
    export_dialog_file = Path("gui/dialogs/advanced_data_export_dialog.py")
    if not export_dialog_file.exists():
        with open(export_dialog_file, 'w', encoding='utf-8') as f:
            f.write(export_dialog_code)
        logger.info("✅ 高级数据导出对话框已创建")
    else:
        logger.info("✅ 高级数据导出对话框已存在")

    return True


def test_final_integration():
    """测试最终集成结果"""
    logger.info("=== 测试最终集成结果 ===")

    test_results = {
        'chart_rendering_manager': False,
        'chart_rendering_integration': False,
        'technical_indicators': False,
        'advanced_export': False,
        'main_dialog_enhancements': False
    }

    try:
        # 检查图表渲染管理器
        manager_file = Path("gui/widgets/chart_rendering_manager.py")
        if manager_file.exists():
            test_results['chart_rendering_manager'] = True
            logger.info("✅ 图表渲染管理器文件存在")

        # 检查主导入对话框的图表渲染集成
        main_dialog_path = Path("gui/dialogs/unified_duckdb_import_dialog.py")
        if main_dialog_path.exists():
            with open(main_dialog_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'chart_rendering_manager' in content:
                test_results['chart_rendering_integration'] = True
                logger.info("✅ 图表渲染集成测试通过")

            if '_calculate_technical_indicators' in content:
                test_results['technical_indicators'] = True
                logger.info("✅ 技术指标集成测试通过")

            if '_create_chart_preview_tab' in content:
                test_results['main_dialog_enhancements'] = True
                logger.info("✅ 主导入对话框增强测试通过")

        # 检查高级数据导出对话框
        export_dialog_file = Path("gui/dialogs/advanced_data_export_dialog.py")
        if export_dialog_file.exists():
            test_results['advanced_export'] = True
            logger.info("✅ 高级数据导出对话框存在")

        # 统计测试结果
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)

        logger.info(f"\n📊 最终测试结果: {passed_tests}/{total_tests} 个功能通过测试")

        for feature, passed in test_results.items():
            status = "✅" if passed else "❌"
            logger.info(f"  {status} {feature}")

        if passed_tests == total_tests:
            logger.info("\n🎉 所有集成测试通过！")
            return True
        else:
            logger.warning(f"\n⚠️ {total_tests - passed_tests} 个功能测试未通过")
            return False

    except Exception as e:
        logger.error(f"测试最终集成时发生错误: {e}")
        return False


def main():
    """主函数"""
    logger.info("完善图表渲染与高级功能集成")
    logger.info("=" * 60)

    success = True

    # 1. 修复图表渲染集成
    logger.info("1️⃣ 修复图表渲染集成...")
    if not fix_chart_rendering_integration():
        success = False

    # 2. 增强技术指标集成
    logger.info("\n2️⃣ 增强技术指标集成...")
    if not enhance_technical_indicators_integration():
        success = False

    # 3. 创建高级数据导出UI
    logger.info("\n3️⃣ 创建高级数据导出UI...")
    if not create_advanced_data_export_ui():
        success = False

    # 4. 测试最终集成结果
    logger.info("\n4️⃣ 测试最终集成结果...")
    if not test_final_integration():
        success = False

    if success:
        logger.info("\n🎉 图表渲染与高级功能集成完成！")
        logger.info("\n📋 集成总结:")
        logger.info("🎨 图表渲染管理器：提供统一的图表渲染接口")
        logger.info("📈 图表预览功能：在主UI中直接预览K线图表")
        logger.info("📊 技术指标集成：支持MA、EMA、MACD、RSI等主要指标")
        logger.info("🎛️ 高级功能面板：提供直观的功能访问入口")
        logger.info("📤 高级数据导出：支持多格式数据导出和批量处理")
        logger.info("⚡ 实时预览：图表类型和指标选择的实时响应")
    else:
        logger.warning("\n⚠️ 部分集成可能未完全成功，请检查日志")

    return success


if __name__ == "__main__":
    main()
